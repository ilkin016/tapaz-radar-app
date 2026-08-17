#!/usr/bin/env python3
"""Sistem istifadəçiləri + rollar (admin/operator) + sessiya.
Parollar pbkdf2 ilə hash-lənir (plaintext YOX). Sessiya token cookie ilə.
İlk işə salışda default admin yaradılır (parol data/first_admin.txt-də bir dəfə göstərilir)."""
import sqlite3, os, hashlib, secrets, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "radar.db")
ROLES = ("admin", "operator")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  username TEXT PRIMARY KEY, pwhash TEXT, salt TEXT, role TEXT DEFAULT 'operator', created_at TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, username TEXT, expires REAL);
"""


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120000).hex()


class Users:
    def __init__(self):
        self.db = sqlite3.connect(DB, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)
        self.db.commit()
        self._ensure_admin()

    def _ensure_admin(self):
        n = self.db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        if n == 0:
            pw = secrets.token_urlsafe(9)
            self.create("admin", pw, "admin")
            p = os.path.join(ROOT, "data", "first_admin.txt")
            open(p, "w").write(f"admin / {pw}\n(ilk giriş — sonra parolu dəyiş)\n")
            os.chmod(p, 0o600)

    def create(self, username, password, role="operator"):
        username = username.strip().lower()
        if not username or not password:
            return {"error": "username və parol lazımdır"}
        if role not in ROLES:
            role = "operator"
        salt = secrets.token_hex(16)
        try:
            self.db.execute("INSERT INTO users(username,pwhash,salt,role,created_at) VALUES(?,?,?,?,?)",
                            (username, _hash(password, salt), salt, role, time.strftime("%Y-%m-%d %H:%M:%S")))
            self.db.commit()
            return {"ok": True, "username": username, "role": role}
        except sqlite3.IntegrityError:
            return {"error": "bu username artıq var"}

    def verify(self, username, password):
        r = self.db.execute("SELECT * FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
        if r and _hash(password, r["salt"]) == r["pwhash"]:
            return {"username": r["username"], "role": r["role"]}
        return None

    def login(self, username, password):
        u = self.verify(username, password)
        if not u:
            return {"error": "yanlış username və ya parol"}
        tok = secrets.token_urlsafe(24)
        self.db.execute("INSERT INTO sessions(token,username,expires) VALUES(?,?,?)",
                        (tok, u["username"], time.time() + 30 * 86400))
        self.db.commit()
        return {"ok": True, "token": tok, "user": u}

    def user_for_token(self, token):
        if not token:
            return None
        r = self.db.execute("SELECT s.username, u.role FROM sessions s JOIN users u ON u.username=s.username "
                            "WHERE s.token=? AND s.expires>?", (token, time.time())).fetchone()
        return {"username": r["username"], "role": r["role"]} if r else None

    def logout(self, token):
        self.db.execute("DELETE FROM sessions WHERE token=?", (token,)); self.db.commit()

    def set_password(self, username, password):
        salt = secrets.token_hex(16)
        self.db.execute("UPDATE users SET pwhash=?, salt=? WHERE username=?",
                        (_hash(password, salt), salt, username.strip().lower()))
        self.db.commit(); return {"ok": True}

    def list(self):
        return [{"username": r["username"], "role": r["role"], "created_at": r["created_at"]}
                for r in self.db.execute("SELECT username,role,created_at FROM users ORDER BY created_at").fetchall()]

    def delete(self, username):
        self.db.execute("DELETE FROM users WHERE username=?", (username.strip().lower(),))
        self.db.execute("DELETE FROM sessions WHERE username=?", (username.strip().lower(),))
        self.db.commit(); return {"ok": True}
