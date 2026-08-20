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
from radar.stores import StoreStore

_AUTH = AuthClient(verbose=True)  # digit-u xam cavablarını jurnalla (debug)
_AUTH.load()  # Keychain-dən mövcud sessiya
_DRAFTS = DraftStore()  # BİZİM sistemin daxili qaralama qatı
_USERS = Users()  # sistem istifadəçiləri (admin/operator)
_STORES = StoreStore()  # tap.az mağazaları
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


def _import_one(lid):
    """Bir tap.az elanını PCTECH sisteminə (draft) gətir — şəkilləri endirir."""
    ad = poster.read_ad_for_repost(lid)
    if ad.get("error"):
        return {"error": ad["error"]}
    imgs = []
    for u in ad.get("photos", []):
        try:
            imgs.append(poster.download_photo(u))
        except Exception:
            pass
    return {"ok": True, "draft_id": _DRAFTS.create(lid, ad, imgs)}


def _make_ai_image(d, did, idx, style="card", src_idx=None):
    """Bir şəkli hazırla: style=card (çərçivəli) / white (ağ fon) / original. src_idx: mənbə foto (default idx)."""
    from radar import ai_brand, card
    src = _DRAFTS.photo_bytes(did, idx if src_idx is None else src_idx)
    if not src:
        return {"error": f"#{idx if src_idx is None else src_idx} mənbə şəkli yoxdur"}
    if style == "original":
        _DRAFTS.save_ai_photo(did, idx, src)
        return {"ok": True, "index": idx, "style": "original"}
    white = ai_brand.product_white(src)
    if isinstance(white, dict) and white.get("error"):
        return {"error": "məhsul təmizlənmədi: " + white["error"]}
    if style == "white":
        _DRAFTS.save_ai_photo(did, idx, card.on_white(white))
        return {"ok": True, "index": idx, "style": "white"}
    fields = ai_brand.card_fields(d.get("adapted_title") or d["title"], d.get("adapted_body") or d["body"])
    if isinstance(fields, dict) and fields.get("error"):
        fields = {"title": d.get("adapted_title") or d["title"], "model": "", "features": [], "category": ""}
    try:
        img = card.build_card(white, fields["title"], fields.get("model", ""), fields.get("features", []),
                              ai_brand.load_brand(), category=fields.get("category", ""))
    except Exception as e:
        return {"error": f"kart montajı: {str(e)[:120]}"}
    _DRAFTS.save_ai_photo(did, idx, img)
    return {"ok": True, "index": idx, "style": "card", "fields": fields}


_SYNC = {"running": False, "slug": None, "count": 0, "done": None, "error": None}


def _run_sync(slug):
    _SYNC.update(running=True, slug=slug, count=0, done=None, error=None)
    try:
        r = _STORES.sync(slug)
        _SYNC["count"] = r.get("count", 0); _SYNC["error"] = r.get("error")
    except Exception as e:
        _SYNC["error"] = str(e)[:150]
    _SYNC.update(running=False, done=time.strftime("%H:%M:%S"))


def _store_daemon():
    """Gündəlik sync: last_sync 20 saatdan köhnə olan mağazaları avtomatik yenilə (saatda bir yoxlanır)."""
    import datetime
    while True:
        try:
            for st in _STORES.list():
                if _REFRESH["running"] or _SYNC["running"] or _BULK["running"]:
                    break
                ls, stale = st.get("last_sync"), True
                if ls:
                    try:
                        stale = (datetime.datetime.now() - datetime.datetime.strptime(ls, "%Y-%m-%d %H:%M")).total_seconds() > 20 * 3600
                    except Exception:
                        stale = True
                if stale:
                    _run_sync(st["slug"])
        except Exception:
            pass
        time.sleep(3600)


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


_SAMPLE_SPECS = ["Core i9-14900HX", "RTX 4080", "32GB DDR5", "1TB SSD", "16\" 240Hz"]


def _brand_preview(overrides):
    """Nümunə kartı cari brend + (query) override-larla render et → JPEG bytes."""
    from radar import ai_brand, card
    b = dict(ai_brand.load_brand())
    for k in ("name", "phone", "guarantee", "card_color", "card_icon", "card_badge", "card_badge_pos"):
        v = (overrides or {}).get(k)
        if v is not None:
            b[k] = v
    sample = os.path.join(ROOT, "config", "sample_product.png")
    img = open(sample, "rb").read() if os.path.exists(sample) else b""
    return card.build_card(img, "ASUS ROG Strix G16", "FX608JPR-RV019", _SAMPLE_SPECS, b, category="Gaming noutbuk")


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
        if path == "/api/brand/get":
            from radar import ai_brand, card
            bb = ai_brand.load_brand()
            return self._send(200, {"name": bb.get("name", "PCTECH"), "phone": bb.get("phone", ""),
                                    "guarantee": bb.get("guarantee", ""), "card_color": bb.get("card_color", "#2F56E0"),
                                    "card_icon": bb.get("card_icon", "none"), "has_logo": bool(bb.get("card_logo")),
                                    "card_badge": bb.get("card_badge", ""), "card_badge_pos": bb.get("card_badge_pos", "none"),
                                    "icons": card.IT_ICONS})
        if path == "/api/brand/preview":
            try:
                return self._send(200, _brand_preview(q), "image/jpeg")
            except Exception as e:
                return self._send(200, {"error": str(e)[:180]})
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
        if path == "/api/stores/list":
            if not self._sysuser():
                return self._send(401, {"error": "giriş lazımdır"})
            return self._send(200, {"stores": _STORES.list()})
        if path == "/api/stores/categories":
            if not self._sysuser():
                return self._send(401, {"error": "giriş lazımdır"})
            return self._send(200, _STORES.cats(q.get("slug", "")))
        if path == "/api/stores/sync-status":
            return self._send(200, _SYNC)
        if path == "/api/stores/products":
            if not self._sysuser():
                return self._send(401, {"error": "giriş lazımdır"})
            st = _STORES.get(q.get("slug", ""))
            if not st:
                return self._send(200, {"error": "mağaza yoxdur", "items": []})
            res = _STORES.cached(q.get("slug"), category=q.get("category"),
                                 limit=int(q.get("limit", 24)), offset=int(q.get("offset", 0)))
            existing = {str(d.get("source_id")) for d in _DRAFTS.list()}
            for it in res.get("items", []):
                it["already"] = it["id"] in existing
            res["store"] = {"name": st["name"], "slug": st["slug"], "ads_count": st.get("ads_count"),
                            "last_sync": st.get("last_sync"), "logo_url": st.get("logo_url")}
            res["need_sync"] = (st.get("last_sync") is None)
            return self._send(200, res)
        if path == "/api/stores/preview":  # bir məhsulun tam tap.az tərkibi (popup)
            if not self._sysuser():
                return self._send(401, {"error": "giriş lazımdır"})
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            ad = poster.read_ad_for_repost(q.get("id", ""))
            if ad.get("error"):
                return self._send(200, ad)
            drafts = {str(x.get("source_id")): x for x in _DRAFTS.list()}
            dr = drafts.get(ad["numeric_id"])
            return self._send(200, {"id": ad["numeric_id"], "title": ad.get("title"), "body": ad.get("body"),
                                    "price": ad.get("price"), "photos": ad.get("photos", []),
                                    "params": ad.get("params", {}), "category_slug": ad.get("category_slug"),
                                    "link": ad.get("link"), "already": bool(dr),
                                    "draft_id": (dr["id"] if dr else None),
                                    "draft_status": (dr.get("status") if dr else None),
                                    "n_ai_photos": ((dr.get("n_ai_photos") or 0) if dr else 0)})
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
        if path == "/api/brand/set":  # kart dizaynı ayarları (ad, nömrə, zəmanət, rəng, ikon)
            if not is_admin:
                return self._send(403, {"error": "yalnız admin"})
            from radar import ai_brand
            return self._send(200, ai_brand.set_brand(data))
        if path == "/api/brand/logo":  # öz logonu yüklə → badge əvəzinə
            if not is_admin:
                return self._send(403, {"error": "yalnız admin"})
            b64 = data.get("b64") or ""
            if not b64[:32].lower().startswith("data:image/"):
                return self._send(200, {"error": "yalnız şəkil (png/jpg)"})
            try:
                raw = base64.b64decode(b64.split(",", 1)[1])
            except Exception as e:
                return self._send(200, {"error": f"oxunmadı: {str(e)[:60]}"})
            open(os.path.join(ROOT, "config", "custom_logo.png"), "wb").write(raw)
            from radar import ai_brand
            ai_brand.set_brand({"card_logo": "config/custom_logo.png"})
            return self._send(200, {"ok": True})
        if path == "/api/brand/logo-clear":  # logonu sil → IT ikonuna qayıt
            if not is_admin:
                return self._send(403, {"error": "yalnız admin"})
            from radar import ai_brand
            ai_brand.set_brand({"card_logo": ""})
            return self._send(200, {"ok": True})
        # rol qapısı — draft/AI əməliyyatları sistem girişi tələb edir (operator+admin)
        if (path.startswith("/api/draft/") or path.startswith("/api/stores/")) and not su:
            return self._send(401, {"error": "sistemə giriş lazımdır (login)"})
        if path == "/api/stores/add":
            r = _STORES.add(data.get("url") or data.get("slug", ""))
            if r.get("ok") and not _SYNC["running"] and not _REFRESH["running"]:
                threading.Thread(target=_run_sync, args=(r["store"]["slug"],), daemon=True).start()
            return self._send(200, r)
        if path == "/api/stores/sync":  # əl ilə: mağazanı İNDİ yenilə (keş)
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            if _SYNC["running"]:
                return self._send(200, {"error": "Sync artıq gedir", "slug": _SYNC["slug"]})
            slug = data.get("slug", "")
            if not _STORES.get(slug):
                return self._send(200, {"error": "mağaza yoxdur"})
            threading.Thread(target=_run_sync, args=(slug,), daemon=True).start()
            return self._send(200, {"ok": True, "started": True})
        if path == "/api/stores/remove":
            return self._send(200, _STORES.remove(data.get("slug", "")))
        if path == "/api/stores/import":  # bir məhsulu PCTECH-ə (draft)
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            return self._send(200, _import_one(data.get("listing_id")))
        if path == "/api/stores/enrich":  # görünən məhsulların əsas parametrlərini detaldan çək + keşlə
            if _REFRESH["running"]:
                return self._send(200, {"specs": {}})
            slug = data.get("slug", "")
            ids = [str(i) for i in (data.get("ids") or [])][:24]
            miss = _STORES.missing_specs(slug, ids)
            from radar.stores import specs_from_ad
            out = {}
            for lid in miss:
                try:
                    ad = poster.read_ad_for_repost(lid)
                    sp = specs_from_ad(ad) if not ad.get("error") else []
                except Exception:
                    sp = []
                _STORES.set_specs(slug, lid, sp)  # boş olsa da yaz (təkrar cəhd etməmək üçün)
                out[lid] = sp
            return self._send(200, {"specs": out})
        if path == "/api/stores/import-bulk":  # seçilmiş məhsulları toplu → draft (arxa fon)
            if _REFRESH["running"]:
                return self._send(200, {"error": "Skan gedir — bitəndən sonra"})
            if _BULK["running"]:
                return self._send(200, {"error": "Toplu import artıq gedir"})
            ids = [str(i) for i in (data.get("ids") or []) if str(i).strip()]
            if not ids:
                return self._send(200, {"error": "seçim yoxdur"})
            threading.Thread(target=_run_bulk, args=(ids,), daemon=True).start()
            return self._send(200, {"ok": True, "total": len(ids)})
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
        if path == "/api/draft/make-card":  # bir şəkil: style=card (çərçivəli) / white (ağ fon) / original
            did = int(data.get("id")); idx = int(data.get("index", 0))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            return self._send(200, _make_ai_image(d, did, idx, data.get("style", "card")))
        if path == "/api/draft/make-set":  # DƏST: 1-ci çərçivəli kart + qalanları ağ fon (2-3 şəkil)
            did = int(data.get("id")); n = int(data.get("n", 3))
            d = _DRAFTS.get(did)
            if not d:
                return self._send(404, {"error": "draft yoxdur"})
            npho = d.get("n_photos") or 0
            if not npho:
                return self._send(200, {"error": "mənbə şəkil yoxdur"})
            # plan: ai_0 = çərçivəli kart(foto0); qalanlar = ağ fon (fərqli fotolardan, yoxdursa eyni fotonun ağ versiyası)
            plan = [(0, "card")]
            if npho == 1:
                plan.append((0, "white"))
            else:
                for j in range(1, npho):
                    plan.append((j, "white"))
            plan = plan[:max(1, n)]
            out = []
            for save_idx, (src_idx, style) in enumerate(plan):
                r = _make_ai_image(d, did, save_idx, style, src_idx=src_idx)
                out.append(r)
                if save_idx == 0 and r.get("error"):
                    return self._send(200, {"error": r["error"]})
            return self._send(200, {"ok": True, "n": len(plan), "results": out})
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
    threading.Thread(target=_store_daemon, daemon=True).start()  # gündəlik mağaza sync
    print(f"Mac-local backend: http://127.0.0.1:{port}/  (login: {bool(_AUTH.user)})")
    srv.serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8091)
