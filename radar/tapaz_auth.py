#!/usr/bin/env python3
"""tap.az posting modulu — M1: Login client (OTP).
Axın: telefon → api.digit-u.id/auth (SMS kod) → /auth/verify (accessToken) →
tap.az GraphQL loginUser(accessToken) → sessiya cookie + csrfToken.

‼️ TƏHLÜKƏSİZLİK: OTP kodu HƏMİŞƏ istifadəçidən canlı alınır (heç yerdə hardcode yox).
Sessiya macOS Keychain-də saxlanır (plaintext fayl yox). Yalnız istifadəçinin ÖZ hesabı üçün.
Arxitektura: Mac-local (Cloudflare residential IP). Bax docs/POSTING-MODULE-analiz.md.

İlk canlı testdə xam cavablar çap olunur ki, digit-u API sahə adları dəqiqləşsin."""
import json, ssl, http.cookiejar, urllib.request, urllib.parse, subprocess, sys

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DIGIT = "https://api.digit-u.id"
GRAPHQL = "https://tap.az/graphql"
ORIGIN = "https://hello.tap.az"

# macOS Keychain (plaintext fayl YOX)
_KC_SERVICE = "tapaz-radar-poster"
_KC_ACCOUNT = "session"


def _kc_set(value):
    subprocess.run(["security", "add-generic-password", "-U", "-a", _KC_ACCOUNT,
                    "-s", _KC_SERVICE, "-w", value], check=True, capture_output=True)


def _kc_get():
    r = subprocess.run(["security", "find-generic-password", "-a", _KC_ACCOUNT,
                        "-s", _KC_SERVICE, "-w"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _kc_del():
    subprocess.run(["security", "delete-generic-password", "-a", _KC_ACCOUNT,
                    "-s", _KC_SERVICE], capture_output=True)


class AuthClient:
    def __init__(self, verbose=True):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=_CTX))
        self.csrf = None
        self.user = None
        self.access_token = None
        self.verbose = verbose

    def _req(self, url, data=None, headers=None, method=None):
        h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Origin": ORIGIN}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=body, headers=h,
                                     method=method or ("POST" if data is not None else "GET"))
        try:
            with self.opener.open(req, timeout=40) as r:
                raw = r.read().decode("utf-8", "ignore")
                code = r.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "ignore")
            code = e.code
        try:
            js = json.loads(raw)
        except Exception:
            js = raw[:800]
        if self.verbose:
            import re as _re
            shown = json.dumps(js, ensure_ascii=False)[:600] if isinstance(js, (dict, list)) else str(js)[:600]
            # token dəyərlərini maskala (struktur/sahə adları görünsün, dəyər yox)
            shown = _re.sub(r'("(?:accessToken|access_token|token|csrfToken|jwt)"\s*:\s*")[^"]+(")', r'\1***\2', shown)
            print(f"  [{method or 'POST'} {url}] → {code}\n  {shown}", flush=True)
        return code, js

    # ---- 1) SMS kod göndər ----  (canlı test: {phone} işləyir)
    def send_code(self, phone):
        """POST /auth {phone} → SMS kod."""
        code, js = self._req(f"{DIGIT}/auth", {"phone": phone.strip()})
        ok = code in (200, 201) and isinstance(js, dict) and not (js.get("error") or js.get("errors"))
        left = js.get("code_requests_left") if isinstance(js, dict) else None
        return {"ok": ok, "code_requests_left": left, "resp": None if ok else js}

    # ---- 2) Kodu təsdiqlə → access_token ----  (canlı test: {phone,code} → access_token)
    def verify_code(self, phone, code_value):
        """POST /auth/verify {phone,code} → access_token."""
        st, js = self._req(f"{DIGIT}/auth/verify", {"phone": phone.strip(), "code": code_value})
        tok = (js.get("access_token") or js.get("accessToken")) if isinstance(js, dict) else None
        if tok:
            self.access_token = tok
            return {"ok": True}
        msg = js.get("message") if isinstance(js, dict) else "kod yanlış"
        return {"ok": False, "note": msg, "resp": js}

    # ---- 3) tap.az sessiyası ----
    def login(self, access_token=None):
        """GraphQL loginUser(accessToken) → sessiya cookie qurur.
        ‼️ Canlı test: loginUser IDMutationResultType qaytarır — entity=skalyar ID, csrfToken YOX.
        User detalları sonra currentUser ilə alınır."""
        tok = access_token or self.access_token
        if not tok:
            return {"ok": False, "note": "accessToken yoxdur"}
        q = "mutation($accessToken:String!){ loginUser(accessToken:$accessToken){ entity } }"
        st, js = self._req(GRAPHQL, {"query": q, "variables": {"accessToken": tok}},
                           headers={"Referer": "https://tap.az/"})
        if not isinstance(js, dict) or js.get("errors"):
            return {"ok": False, "resp": js, "note": "loginUser uğursuz"}
        d = (js.get("data") or {}).get("loginUser")
        if d is None:
            return {"ok": False, "resp": js}
        # sessiya cookie quruldu → user detallarını al
        self.user = self.whoami() or {"id": (d.get("entity") if isinstance(d, dict) else d)}
        self._save()
        return {"ok": True, "user": self.user}

    # ---- sessiya saxlama (Keychain) ----
    def _save(self):
        cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
                   for c in self.jar]
        _kc_set(json.dumps({"cookies": cookies, "csrf": self.csrf, "user": self.user}))

    def load(self):
        raw = _kc_get()
        if not raw:
            return False
        d = json.loads(raw)
        self.csrf = d.get("csrf")
        self.user = d.get("user")
        for c in d.get("cookies", []):
            self.jar.set_cookie(http.cookiejar.Cookie(
                0, c["name"], c["value"], None, False, c["domain"], True,
                c["domain"].startswith("."), c["path"], True, False, None, False, None, None, {}))
        return True

    def whoami(self):
        """currentUser — sessiyanın kimə aid olduğunu yoxla."""
        q = "{ currentUser{ id name email phone } }"
        st, js = self._req(GRAPHQL, {"query": q}, headers={"Referer": "https://tap.az/"})
        return (js or {}).get("data", {}).get("currentUser") if isinstance(js, dict) else None


if __name__ == "__main__":
    import getpass
    c = AuthClient()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"
    if cmd == "login":
        phone = input("Telefon (məs 0XX XXX XX XX): ").strip()
        print("\n1) SMS kod göndərilir…")
        print(c.send_code(phone))
        code = input("\nTelefonuna gələn kodu daxil et: ").strip()
        print("\n2) Kod yoxlanılır…")
        print(c.verify_code(phone, code))
        print("\n3) tap.az sessiyası…")
        print(c.login())
    elif cmd == "whoami":
        c.load()
        print(c.whoami())
    elif cmd == "logout":
        _kc_del()
        print("Sessiya silindi")
