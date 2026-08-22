#!/bin/bash
# Mac-local backend (auto-refresh + posting). tap.az əməliyyatları burada icra olunur (Cloudflare residential IP).
# İstifadə:
#   ./run_backend.sh              → Mac-də lokal (http://127.0.0.1:8091/)
#   ./run_backend.sh 8091 --tunnel → əlavə: VPS-ə reverse-SSH tunel ("Mac & VPS" — VPS Caddy /api → Mac)
cd "$(dirname "$0")" || exit 1
PORT="${1:-8091}"
if [ "$2" = "--tunnel" ]; then
  # VPS-də 0.0.0.0:$PORT (public, GatewayPorts clientspecified) → Mac backend. AVTO-YENİDƏN-QOŞULAN loop:
  ( while true; do
      ssh -i "$HOME/.ssh/tapaz_radar_deploy" -o StrictHostKeyChecking=accept-new \
          -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -o TCPKeepAlive=yes \
          -N -R "0.0.0.0:${PORT}:localhost:${PORT}" root@187.127.91.112
      echo "↻ tunel düşdü — 5s sonra yenidən qoşulur…"
      sleep 5
    done ) &
  TUN=$!
  echo "↔ auto-reconnect tunnel: http://187.127.91.112.sslip.io:${PORT}/  (loop pid $TUN)"
  trap "kill $TUN 2>/dev/null; pkill -f '${PORT}:localhost:${PORT}' 2>/dev/null" EXIT
fi
echo "▶ Mac-local backend → http://127.0.0.1:${PORT}/"
exec python3 -m radar.backend "$PORT"
