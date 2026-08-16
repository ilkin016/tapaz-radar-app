#!/bin/bash
# Mac-local backend (auto-refresh + posting). tap.az əməliyyatları burada icra olunur (Cloudflare residential IP).
# İstifadə:
#   ./run_backend.sh              → Mac-də lokal (http://127.0.0.1:8091/)
#   ./run_backend.sh 8091 --tunnel → əlavə: VPS-ə reverse-SSH tunel ("Mac & VPS" — VPS Caddy /api → Mac)
cd "$(dirname "$0")" || exit 1
PORT="${1:-8091}"
if [ "$2" = "--tunnel" ]; then
  # VPS-də localhost:$PORT Mac backend-ə yönəlir; VPS Caddy /api-ni ora proxy edir (SETUP.md-yə bax)
  ssh -i "$HOME/.ssh/tapaz_radar_deploy" -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 \
      -N -R "${PORT}:localhost:${PORT}" root@187.127.91.112 &
  TUN=$!
  echo "↔ reverse tunnel: VPS:${PORT} → Mac:${PORT} (pid $TUN)"
  trap "kill $TUN 2>/dev/null" EXIT
fi
echo "▶ Mac-local backend → http://127.0.0.1:${PORT}/"
exec python3 -m radar.backend "$PORT"
