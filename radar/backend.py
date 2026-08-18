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
import json, os, threading, subprocess, time, urllib.parse, base64, re, io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
PY = os.environ.get("RADAR_PY", "python3")

# --- lazy imports (auth/poster yalnız lazım olanda) ---
from radar import poster
from radar.tapaz_auth import AuthClient
from radar.drafts import DraftStore, MEDIA as DRAFT_MEDIA
from radar.users import Users

_AUTH = AuthClient(verbose=True)  # digit-u xam cavablarını jurnalla (debug)
_AUTH.load()  # Keychain-dən mövcud sessiya
_DRAFTS = DraftStore()  # BİZİM sistemin daxili qaralama qatı
_USERS = Users()  # sistem istifadəçiləri (admin/operator)
_REFRESH = {"running": False, "started": None, "done": None, "log": "", "code": None}
_BULK = {"running": False, "total": 0, "done": 0, "ok": 0, "fail": 0, "skip": 0, "errors": [], "started": None}
_ID_RE = re.compile(r"(\d{6,9})")


def _extract_ids(text):
    """Sərbəst mətndən (link və/və ya kod, hər sətir/vergül) tap.az elan nömrələrini çıxar, təkrarları at."""
    ids, seen = [], set()
    for m in _ID_RE.findall(text or ""):
        if m not in seen:
            seen.add(m); ids.append(m)
    return ids


def _run_bulk(ids):
    """Arxa fonda: hər nömrə üçün elanı oxu + şəkilləri endir + draft yarat. Mövcud olanları ötür."""
    existing = {str(d.get("source_id")) for d in _DRAFTS.list()}
    _BULK.update(running=True, total=len(ids), done=0, ok=0, fail=0, skip=0, errors=[],
                 started=time.strftime("%H:%M:%S"))
    for lid in ids:
        if _REFRESH["running"]:
            _BULK["errors"].append("Skan başladı — dayandırıldı"); break
        if str(lid) in existing:
            _BULK["skip"] += 1; _BULK["done"] += 1; continue
        try:
            ad = poster.read_ad_for_repost(lid)
            if ad.get("error"):
                _BULK["fail"] += 1; _BULK["errors"].append(f"#{lid}: {ad['error'][:60]}")
            else:
                imgs = []
                for u in ad.get("photos", []):
                    try:
                        imgs.append(poster.download_photo(u))
                    except Exception:
                        pass
                _DRAFTS.create(lid, ad, imgs)
                existing.add(str(lid)); _BULK["ok"] += 1
        except Exception as e:
            _BULK["fail"] += 1; _BULK["errors"].append(f"#{lid}: {str(e)[:60]}")
        _BULK["done"] += 1
    _BULK["running"] = False


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

    def _sysuser(self):
        tok = None
        for part in (self.headers.get("Cookie", "") or "").split(";"):
            if part.strip().startswith("sys_session="):
                tok = part.strip()[len("sys_session="):]
        return _USERS.user_for_token(tok or self.headers.get("X-Sys-Token"))

    def _set_cookie(self, code, body, token):
        b = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", f"sys_session={token}; Path=/; Max-Age=2592000; SameSite=Lax")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

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
            su = self._sysuser()
            from radar import ai_brand
            return self._send(200, {
                "ok": True, "logged_in": bool(_AUTH.user),
                "user": (_AUTH.user or {}).get("name") if _AUTH.user else None,
                "sys": su, "ai_key": ai_brand.has_key(),
                "refresh": {k: _REFRESH[k] for k in ("running", "started", "done", "code")},
            })
        if path == "/api/user/me":
            return self._send(200, {"user": self._sysuser()})
        if path == "/api/user/list":
            if (self._sysuser() or {}).get("role") != "admin":
                return self._send(403, {"error": "yalnız admin"})
            return self._send(200, {"users": _USERS.list()})
        if path == "/api/settings/get":
            from radar import ai_brand
            k = ai_brand._key()
            return self._send(200, {"ai_key_set": bool(k), "ai_key_masked": (k[:6] + "…" + k[-4:]) if k else None,
                                    "brand": ai_brand.load_brand().get("name")})
        if path == "/api/refresh-status":
            return self._send(200, _REFRESH)
        if path == "/api/auth/whoami":
            return self._send(200, {"user": _AUTH.whoami()})
        if path == "/api/repost-status":
            if not _AUTH.user:
                return self._send(401, {"error": "login lazımdır"})
            return self._send(200, poster.check_status(_AUTH, q.get("legacy_id") or q.get("ad_gid")))
        if path == "/api/draft/list":
            return self._send(200, {"drafts": _DRAFTS.list(q.get("status"))})
        if path == "/api/draft/bulk-status":
            return self._send(200, _BULK)
        if path == "/api/draft/get":
            d = _DRAFTS.get(int(q.get("id", 0)))
            return self._send(200, d) if d else self._send(404, {"error": "draft yoxdur"})
        if path.startswith("/drafts_media/"):
            rel = path[len("/drafts_media/"):]
            f = os.path.normpath(os.path.join(DRAFT_MEDIA, rel))
            if f.startswith(DRAFT_MEDIA) and os.path.exists(f):
                return self._send(200, open(f, "rb").read(), "image/jpeg")
            return self._send(404, {"error": "şəkil yoxdur"})
        return self._send(404, {"error": "yol yoxdur"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            data = self._json()
        except Exception:
            data = {}
        # --- Sistem istifadəçi auth ---
        if path == "/api/user/login":
            r = _USERS.login(data.get("username", ""), data.get("password", ""))
            return self._set_cookie(200, {"ok": True, "user": r["user"]}, r["token"]) if r.get("ok") else self._send(401, r)
        if path == "/api/user/logout":
            for part in (self.headers.get("Cookie", "") or "").split(";"):
                if part.strip().startswith("sys_session="):
                    _USERS.logout(part.strip()[len("sys_session="):])
            return self._send(200, {"ok": True})
        su = self._sysuser()
        is_admin = (su or {}).get("role") == "admin"
        if path == "/api/user/create":
            return self._send(200, _USERS.create(data.get("username", ""), data.get("password", ""), data.get("role", "operator"))) if is_admin else self._send(403, {"error": "yalnız admin"})
        if path == "/api/user/delete":
            return self._send(200, _USERS.delete(data.get("username", ""))) if is_admin else self._send(403, {"error": "yalnız admin"})
        if path == "/api/user/set-password":
            target = data.get("username") if (is_admin and data.get("username")) else (su or {}).get("username")
            return self._send(200, _USERS.set_password(target, data.get("password", ""))) if target else self._send(401, {"error": "giriş lazımdır"})
        if path == "/api/settings/set":
            if not is_admin:
                return self._send(403, {"error": "yalnız admin"})
            from radar import ai_brand
            return self._send(200, ai_brand.set_key(data.get("openai_key", "").strip()))
        # rol qapısı — draft/AI əməliyyatları sistem girişi tələb edir (operator+admin)
        if path.startswith("/api/draft/") and not su:
            return self._send(401, {"error": "sistemə giriş lazımdır (login)"})
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
        if path == "/api/repost":  # yalnız ÖNİZLƏMƏ (dry-run) — tap.az-a heç nə getmir
            if _REFRESH["running"]:
                return self._send(200, {"stage": "busy", "error": "Skan gedir — bitəndən sonra"})
            return self._send(200, poster.repost(_AUTH, data.get("listing_id"), {}, dry_run=True))
        # --- Draftlar (BİZİM sistem) ---
        if path == "/api/draft/create":  # köhnə elanı BİZİM sistemə saxla (tap.az-a YOX)
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            ad = poster.read_ad_for_repost(data.get("listing_id"))
            if ad.get("error"):
                return self._send(200, {"error": ad["error"]})
            imgs = []
            for u in ad.get("photos", []):
                try:
                    imgs.append(poster.download_photo(u))
                except Exception:
                    pass
            did = _DRAFTS.create(data.get("listing_id"), ad, imgs)
            return self._send(200, {"ok": True, "draft_id": did})
        if path == "/api/draft/bulk-create":  # toplu: sərbəst mətndən linkləri/kodları çıxar → draftlar
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            if _BULK["running"]:
                return self._send(200, {"error": "Toplu import artıq gedir"})
            ids = _extract_ids(data.get("text", ""))
            if not ids:
                return self._send(200, {"error": "Heç bir elan nömrəsi tapılmadı (6-9 rəqəm)"})
            threading.Thread(target=_run_bulk, args=(ids,), daemon=True).start()
            return self._send(200, {"ok": True, "total": len(ids)})
        if path == "/api/draft/import-excel":  # Excel (.xlsx) → nömrələr → toplu draft
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            if _BULK["running"]:
                return self._send(200, {"error": "Toplu import artıq gedir"})
            try:
                raw = base64.b64decode((data.get("b64") or "").split(",")[-1])
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
                parts = []
                for ws in wb.worksheets:
                    for row in ws.iter_rows(values_only=True):
                        for cell in row:
                            if cell is not None:
                                parts.append(str(cell))
                ids = _extract_ids(" ".join(parts))
            except Exception as e:
                return self._send(200, {"error": f"Excel oxunmadı: {str(e)[:120]}"})
            if not ids:
                return self._send(200, {"error": "Excel-də elan nömrəsi tapılmadı"})
            threading.Thread(target=_run_bulk, args=(ids,), daemon=True).start()
            return self._send(200, {"ok": True, "total": len(ids)})
        if path == "/api/draft/update":
            return self._send(200, _DRAFTS.update(int(data.get("id")), data))
        if path == "/api/draft/reject":
            _DRAFTS.set_status(int(data.get("id")), "rejected"); return self._send(200, {"ok": True})
        if path == "/api/draft/delete":
            _DRAFTS.delete(int(data.get("id"))); return self._send(200, {"ok": True})
        if path == "/api/draft/ai-adapt":  # Techbar MƏTN-uyğunlaşdırma (şəkillər per-şəkil: kart/təmizlə/yüklə)
            did = int(data.get("id"))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            from radar import ai_brand
            txt = ai_brand.adapt_text(d["title"], d["body"])
            if txt.get("error"):
                return self._send(200, {"stage": "text", "error": txt["error"]})
            _DRAFTS.save_text(did, txt["title"], txt["body"])
            return self._send(200, {"ok": True, "adapted_title": txt["title"]})
        if path == "/api/draft/rebrand-one":  # tək brendlənmiş şəkli yenidən yarat (mənbə foto[index]-dən)
            did = int(data.get("id")); idx = int(data.get("index", 0))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            src = _DRAFTS.photo_bytes(did, idx)
            if not src:
                return self._send(200, {"error": f"#{idx} mənbə şəkli yoxdur"})
            from radar import ai_brand
            r = ai_brand.brandify_image(src)
            if isinstance(r, dict) and r.get("error"):
                return self._send(200, {"error": r["error"]})
            _DRAFTS.save_ai_photo(did, idx, r)
            return self._send(200, {"ok": True, "index": idx})
        if path == "/api/draft/make-card":  # sabit-dizayn Techbar kartı yarat (ağ məhsul + logo + xüsusiyyət)
            did = int(data.get("id")); idx = int(data.get("index", 0))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            src = _DRAFTS.photo_bytes(did, idx)
            if not src:
                return self._send(200, {"error": f"#{idx} mənbə şəkli yoxdur"})
            from radar import ai_brand, card
            white = ai_brand.product_white(src)
            if isinstance(white, dict) and white.get("error"):
                return self._send(200, {"error": "məhsul təmizlənmədi: " + white["error"]})
            fields = ai_brand.card_fields(d.get("adapted_title") or d["title"], d.get("adapted_body") or d["body"])
            if isinstance(fields, dict) and fields.get("error"):
                fields = {"title": d.get("adapted_title") or d["title"], "model": "", "features": []}
            try:
                img = card.build_card(white, fields["title"], fields.get("model", ""),
                                      fields.get("features", []), ai_brand.load_brand(),
                                      category=fields.get("category", ""))
            except Exception as e:
                return self._send(200, {"error": f"kart montajı: {str(e)[:120]}"})
            _DRAFTS.save_ai_photo(did, idx, img)
            return self._send(200, {"ok": True, "index": idx, "fields": fields})
        if path == "/api/draft/replace-photo":  # operator ÖZ şəklini yükləyir → ai_<index> əvəz/əlavə
            did = int(data.get("id")); idx = int(data.get("index", 0))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            b64 = data.get("b64") or ""
            if not b64[:32].lower().startswith("data:image/"):
                return self._send(200, {"error": "yalnız şəkil (jpg / png / webp)"})
            try:
                raw = base64.b64decode(b64.split(",", 1)[1])
            except Exception as e:
                return self._send(200, {"error": f"şəkil oxunmadı: {str(e)[:80]}"})
            if len(raw) > 15 * 1024 * 1024:
                return self._send(200, {"error": "şəkil çox böyükdür (15 MB limit)"})
            if idx < 0:
                idx = d.get("n_ai_photos") or 0  # -1 → sona əlavə et
            # istifadəçi şəkli də YENİ DİZAYNA (Techbar kart) salınır — data.raw=true olsa xam saxlanır
            if not data.get("raw"):
                try:
                    from radar import ai_brand, card
                    fields = ai_brand.card_fields(d.get("adapted_title") or d["title"], d.get("adapted_body") or d["body"])
                    if isinstance(fields, dict) and fields.get("error"):
                        fields = {"title": d.get("adapted_title") or d["title"], "model": "", "features": [], "category": ""}
                    raw = card.build_card(raw, fields["title"], fields.get("model", ""), fields.get("features", []),
                                          ai_brand.load_brand(), category=fields.get("category", ""))
                except Exception:
                    pass  # montaj alınmasa xam saxla
            _DRAFTS.save_ai_photo(did, idx, raw)
            return self._send(200, {"ok": True, "index": idx})
        if path == "/api/draft/approve":  # BİZİM təsdiq → İNDİ tap.az-a göndər (createAd)
            if not _AUTH.user:
                return self._send(401, {"error": "login lazımdır"})
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            did = int(data.get("id"))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            title = d.get("adapted_title") or d["title"]
            body = d.get("adapted_body") or d["body"]
            photo_ids = []
            # HƏR ŞƏKİL üzrə: brendli/kart varsa onu, yoxsa orijinalı işlət (operator seçiminə uyğun)
            n = max(d.get("n_photos") or 0, d.get("n_ai_photos") or 0)
            for i in range(n):
                b = _DRAFTS.ai_photo_bytes(did, i) or _DRAFTS.photo_bytes(did, i)
                if b:
                    try:
                        pid = poster.reupload_photo(_AUTH, b, f"{i}.jpg")
                        if pid:
                            photo_ids.append(pid)
                    except Exception:
                        pass
            contact = {"name": _AUTH.user.get("name"), "email": _AUTH.user.get("email"),
                       "phone": _AUTH.user.get("phone")}
            ad_data = {"categoryId": d["category_id"], "title": title, "body": body,
                       "price": d["price"], "properties": d["properties"], "n_photos": len(photo_ids)}
            params = poster.build_create_ad_params(ad_data, photo_ids, contact)
            res = poster.create_draft(_AUTH, params)
            if not res.get("ok"):
                return self._send(200, {"stage": "createAd", "result": res})
            status = poster.check_status(_AUTH, res.get("legacyId"))
            _DRAFTS.set_status(did, "posted", res.get("legacyId"), (status or {}).get("status"))
            return self._send(200, {"ok": True, "created": res, "status": status})
        return self._send(404, {"error": "yol yoxdur"})


def serve(port=8091):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"Mac-local backend: http://127.0.0.1:{port}/  (login: {bool(_AUTH.user)})")
    srv.serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8091)
