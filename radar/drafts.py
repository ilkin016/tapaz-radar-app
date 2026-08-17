#!/usr/bin/env python3
"""Draft store — BİZİM sistemin daxili qaralama qatı (tap.az klonu kimi).
Axın: köhnə elan → oxu + şəkilləri endir → BURADA saxla (pending) → operator BURADA
yoxlayır/redaktə edir → təsdiqləyəndə YALNIZ onda tap.az-a (createAd) göndərilir.

tap.az-a heç nə tap.az-da təsdiq olunana qədər getmir. Şəkillər lokal saxlanır (review üçün)."""
import sqlite3, json, os, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "radar.db")
MEDIA = os.path.join(ROOT, "out", "drafts_media")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT, created_at TEXT, status TEXT DEFAULT 'pending',
  title TEXT, body TEXT, price REAL, category_slug TEXT, category_id TEXT,
  region TEXT, properties TEXT, n_photos INTEGER DEFAULT 0,
  tapaz_ad_id TEXT, tapaz_status TEXT, note TEXT
);"""


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class DraftStore:
    def __init__(self):
        os.makedirs(MEDIA, exist_ok=True)
        self.db = sqlite3.connect(DB, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(_SCHEMA)
        # migration — AI brend-uyğunlaşdırma sahələri
        for col, typ in [("adapted_title", "TEXT"), ("adapted_body", "TEXT"),
                         ("n_ai_photos", "INTEGER DEFAULT 0"), ("ai_status", "TEXT")]:
            try:
                self.db.execute(f"ALTER TABLE drafts ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass
        self.db.commit()

    def save_adapted(self, did, title, body, ai_image_bytes_list):
        """AI-uyğunlaşdırılmış mətn + PCTECH şəkilləri saxla (ai_<i>.jpg)."""
        d = os.path.join(MEDIA, str(did)); os.makedirs(d, exist_ok=True)
        for i, b in enumerate(ai_image_bytes_list or []):
            if isinstance(b, (bytes, bytearray)):
                open(os.path.join(d, f"ai_{i}.jpg"), "wb").write(b)
        self.db.execute("UPDATE drafts SET adapted_title=?, adapted_body=?, n_ai_photos=?, ai_status='done' WHERE id=?",
                        (title, body, len(ai_image_bytes_list or []), did))
        self.db.commit()

    def ai_photo_bytes(self, did, i):
        p = os.path.join(MEDIA, str(did), f"ai_{i}.jpg")
        return open(p, "rb").read() if os.path.exists(p) else None

    def create(self, source_id, data, image_bytes_list):
        """Draft yarat (pending) + şəkilləri lokal saxla. tap.az-a HEÇ NƏ getmir."""
        cur = self.db.execute(
            "INSERT INTO drafts(source_id,created_at,status,title,body,price,category_slug,category_id,region,properties,n_photos)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (str(source_id), _now(), "pending", data.get("title"), data.get("body"),
             data.get("price"), data.get("category_slug"), data.get("categoryId"),
             data.get("region"), json.dumps(data.get("properties", {}), ensure_ascii=False),
             len(image_bytes_list)))
        did = cur.lastrowid
        d = os.path.join(MEDIA, str(did)); os.makedirs(d, exist_ok=True)
        for i, b in enumerate(image_bytes_list):
            if isinstance(b, (bytes, bytearray)):
                open(os.path.join(d, f"{i}.jpg"), "wb").write(b)
        self.db.commit()
        return did

    def list(self, status=None):
        q = "SELECT * FROM drafts"
        args = ()
        if status:
            q += " WHERE status=?"; args = (status,)
        q += " ORDER BY id DESC"
        return [dict(r) for r in self.db.execute(q, args).fetchall()]

    def get(self, did):
        r = self.db.execute("SELECT * FROM drafts WHERE id=?", (did,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["properties"] = json.loads(d.get("properties") or "{}")
        d["photos"] = [f"/drafts_media/{did}/{i}.jpg" for i in range(d.get("n_photos") or 0)]
        d["ai_photos"] = [f"/drafts_media/{did}/ai_{i}.jpg" for i in range(d.get("n_ai_photos") or 0)]
        return d

    def photo_bytes(self, did, i):
        p = os.path.join(MEDIA, str(did), f"{i}.jpg")
        return open(p, "rb").read() if os.path.exists(p) else None

    def update(self, did, fields):
        allowed = {"title", "body", "price", "note"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if sets:
            self.db.execute("UPDATE drafts SET " + ",".join(f"{k}=?" for k in sets) + " WHERE id=?",
                            (*sets.values(), did))
            self.db.commit()
        return self.get(did)

    def set_status(self, did, status, tapaz_ad_id=None, tapaz_status=None):
        self.db.execute("UPDATE drafts SET status=?, tapaz_ad_id=COALESCE(?,tapaz_ad_id), tapaz_status=COALESCE(?,tapaz_status) WHERE id=?",
                        (status, tapaz_ad_id, tapaz_status, did))
        self.db.commit()

    def delete(self, did):
        self.db.execute("DELETE FROM drafts WHERE id=?", (did,))
        self.db.commit()
