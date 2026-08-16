#!/usr/bin/env python3
"""Mac-local backend — dashboard + API (auto-refresh + posting).
Cloudflare residential IP tələb etdiyi üçün Mac-də işləyir. VPS-dən çıxış reverse-SSH tunel ilə.

Endpoint-lər:
  GET  /                     → out/dashboard.html
  GET  /api/status           → freshness + login vəziyyəti
  POST /api/refresh          → run.py (arxa fon) başlat
  GET  /api/refresh-status   → skan gedişatı / bitdi
  POST /api/auth/send-code   → {phone}  (OTP SMS)   — kod istifadəçidən
  POST /api/auth/verify      → {phone,code} → loginUser → sessiya
  GET  /api/auth/whoami       → cari sessiya
  POST /api/repost           → {listing_id, contact, dry_run} → DRAFT
  GET  /api/repost-status    → {ad_gid} → moderasiya statusu

Stdlib (http.server) — əlavə asılılıq yox."""
import json, os, threading, subprocess, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
PY = os.environ.get("RADAR_PY", "python3")

# --- lazy imports (auth/poster yalnız lazım olanda) ---
from radar import poster
from radar.tapaz_auth import AuthClient

_AUTH = AuthClient(verbose=False)
_AUTH.load()  # Keychain-dən mövcud sessiya
_REFRESH = {"running": False, "started": None, "done": None, "log": "", "code": None}


def _run_refresh(only=None):
    _REFRESH.update(running=True, started=time.strftime("%H:%M:%S"), done=None, code=None, log="")
    args = [PY, "run.py"] + (["--only", only] if only else [])
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        _REFRESH["log"] = (p.stdout or "")[-4000:] + (p.stderr or "")[-1000:]
        _REFRESH["code"] = p.returncode
    except Exception as e:
        _REFRESH["log"] = f"XƏTA: {e}"; _REFRESH["code"] = 1
    _REFRESH.update(running=False, done=time.strftime("%H:%M:%S"))


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        if path in ("/", "/dashboard.html"):
            f = os.path.join(OUT, "dashboard.html")
            if os.path.exists(f):
                return self._send(200, open(f, "rb").read(), "text/html; charset=utf-8")
            return self._send(404, {"error": "dashboard yoxdur — run.py işlət"})
        if path == "/api/status":
            return self._send(200, {
                "ok": True, "logged_in": bool(_AUTH.user),
                "user": (_AUTH.user or {}).get("name") if _AUTH.user else None,
                "refresh": {k: _REFRESH[k] for k in ("running", "started", "done", "code")},
            })
        if path == "/api/refresh-status":
            return self._send(200, _REFRESH)
        if path == "/api/auth/whoami":
            return self._send(200, {"user": _AUTH.whoami()})
        if path == "/api/repost-status":
            if not _AUTH.user:
                return self._send(401, {"error": "login lazımdır"})
            return self._send(200, poster.check_status(_AUTH, q.get("ad_gid")))
        return self._send(404, {"error": "yol yoxdur"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            data = self._json()
        except Exception:
            data = {}
        if path == "/api/refresh":
            if _REFRESH["running"]:
                return self._send(200, {"ok": True, "note": "artıq gedir"})
            threading.Thread(target=_run_refresh, args=(data.get("only"),), daemon=True).start()
            return self._send(200, {"ok": True, "started": True})
        if path == "/api/auth/send-code":
            return self._send(200, _AUTH.send_code(data.get("phone", "")))
        if path == "/api/auth/verify":
            v = _AUTH.verify_code(data.get("phone", ""), data.get("code", ""))
            if v.get("ok"):
                v["login"] = _AUTH.login()
            return self._send(200, v)
        if path == "/api/auth/logout":
            from radar.tapaz_auth import _kc_del
            _kc_del(); _AUTH.user = None; _AUTH.csrf = None
            return self._send(200, {"ok": True})
        if path == "/api/repost":
            if _REFRESH["running"]:
                return self._send(200, {"stage": "busy", "error": "Skan gedir — bitəndən sonra cəhd et (tap.az throttle)"})
            if not _AUTH.user and not data.get("dry_run"):
                return self._send(401, {"error": "login lazımdır"})
            contact = dict(data.get("contact") or {})
            if _AUTH.user:  # kontaktı sessiya istifadəçisindən doldur (öz elanı)
                contact.setdefault("name", _AUTH.user.get("name") or "")
                contact.setdefault("email", _AUTH.user.get("email") or "")
                contact.setdefault("phone", _AUTH.user.get("phone") or "")
            return self._send(200, poster.repost(_AUTH, data.get("listing_id"),
                                                 contact, dry_run=data.get("dry_run", False)))
        return self._send(404, {"error": "yol yoxdur"})


def serve(port=8091):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Mac-local backend: http://127.0.0.1:{port}/  (login: {bool(_AUTH.user)})")
    srv.serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8091)
