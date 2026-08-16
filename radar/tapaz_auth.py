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
            print(f"  [{method or 'POST'} {url}] → {code}\n  {json.dumps(js, ensure_ascii=False)[:600] if isinstance(js, (dict, list)) else js}")
        return code, js

    # ---- 1) SMS kod göndər ----
    def send_code(self, phone):
        """POST /auth — telefon nömrəsinə SMS kod göndərir. İlk testdə cavab sxemini göstərir."""
        phone = phone.strip()
        # Ən ehtimal sahə adları — ilk canlı testdən sonra dəqiqləşir
        for payload in ({"phone": phone}, {"phoneNumber": phone}, {"msisdn": phone},
                        {"phone": phone, "type": "sms"}):
            code, js = self._req(f"{DIGIT}/auth", payload)
            if code in (200, 201) and isinstance(js, dict) and not (js.get("error") or js.get("errors")):
                return {"ok": True, "sent_payload": payload, "resp": js}
        return {"ok": False, "resp": js, "note": "Sahə adı uyğun gəlmədi — xam cavaba bax"}

    # ---- 2) Kodu təsdiqlə → accessToken ----
    def verify_code(self, phone, code_value):
        """POST /auth/verify — kodu yoxlayır, accessToken qaytarır."""
        phone = phone.strip()
        for payload in ({"phone": phone, "code": code_value}, {"phoneNumber": phone, "code": code_value},
                        {"phone": phone, "otp": code_value}, {"phone": phone, "smsCode": code_value}):
            st, js = self._req(f"{DIGIT}/auth/verify", payload)
            if st in (200, 201) and isinstance(js, dict):
                tok = js.get("accessToken") or js.get("access_token") or js.get("token") \
                    or (js.get("data") or {}).get("accessToken")
                if tok:
                    self.access_token = tok
                    return {"ok": True, "accessToken": tok[:12] + "…", "sent_payload": payload}
        return {"ok": False, "resp": js, "note": "accessToken tapılmadı — xam cavaba bax"}

    # ---- 3) tap.az sessiyası ----
    def login(self, access_token=None):
        """GraphQL loginUser(accessToken) → sessiya cookie + csrfToken + user."""
        tok = access_token or self.access_token
        if not tok:
            return {"ok": False, "note": "accessToken yoxdur"}
        q = ("mutation($accessToken:String!){ loginUser(accessToken:$accessToken){ "
             "entity{ id name email phone } csrfToken } }")
        st, js = self._req(GRAPHQL, {"query": q, "variables": {"accessToken": tok}},
                           headers={"Referer": "https://tap.az/"})
        data = (js or {}).get("data", {}).get("loginUser") if isinstance(js, dict) else None
        if data:
            self.csrf = data.get("csrfToken")
            self.user = data.get("entity")
            self._save()
            return {"ok": True, "user": self.user, "csrf": bool(self.csrf)}
        return {"ok": False, "resp": js, "note": "loginUser uğursuz — xam cavaba bax"}

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
