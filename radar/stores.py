#!/usr/bin/env python3
"""tap.az mağazaları (shops): əlavə et, məhsulları LOKAL keşlə (sync), kateqoriyaya görə filtrlə,
birbaşa PCTECH-ə (draft) əlavə et.
Mexanizm: shop(slug){ user{ legacyId } } → adSearch(filters:{userLegacyId}){ ...category ...photo }.
Sync = bütün məhsulları çək → store_products keşinə yaz (kateqoriya + şəkil). Gündəlik + əl ilə."""
import sqlite3, os, re, time
from radar import tap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "radar.db")

_SHOP_Q = "query($s:String!){ shop(slug:$s){ name adsCount uri logo{ url } user{ legacyId } } }"
_ADS_Q = ("query($f:AdFilterInput,$first:Int,$after:String){ adSearch(filters:$f, source:DESKTOP){"
          " ads(first:$first, after:$after){ nodes{ legacyResourceId title price photo{ url }"
          " category{ name legacyResourceId } } pageInfo{ endCursor hasNextPage } } } }")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stores(
  slug TEXT PRIMARY KEY, name TEXT, user_legacy_id TEXT, ads_count INTEGER,
  logo_url TEXT, added_at TEXT, last_sync TEXT);
CREATE TABLE IF NOT EXISTS store_products(
  store_slug TEXT, listing_id TEXT, title TEXT, price REAL, photo TEXT,
  category TEXT, category_id TEXT, synced_at TEXT,
  PRIMARY KEY(store_slug, listing_id));
CREATE INDEX IF NOT EXISTS ix_sp_store ON store_products(store_slug);
CREATE INDEX IF NOT EXISTS ix_sp_cat ON store_products(store_slug, category_id);
"""


def slug_of(url_or_slug):
    s = (url_or_slug or "").strip()
    m = re.search(r"tap\.az/shops/([A-Za-z0-9_\-\.]+)", s)
    return m.group(1) if m else s.strip("/").split("/")[-1]


def resolve_store(slug):
    r = tap._post_json(tap.GRAPHQL, {"query": _SHOP_Q, "variables": {"s": slug}})
    if r.get("errors"):
        return {"error": "mağaza tapılmadı: " + slug}
    sh = (r.get("data") or {}).get("shop")
    if not sh:
        return {"error": "mağaza yoxdur: " + slug}
    return {"slug": slug, "name": sh.get("name"), "ads_count": sh.get("adsCount"),
            "user_legacy_id": (sh.get("user") or {}).get("legacyId"),
            "logo_url": (sh.get("logo") or {}).get("url")}


def _fetch_all(user_legacy_id, cap=None, sleep=0.2, log=None):
    """Mağazanın BÜTÜN məhsulları (kateqoriya + şəkil ilə) — səhifələmə."""
    out, after, seen = [], None, set()
    while True:
        r = tap._post_json(tap.GRAPHQL, {"query": _ADS_Q, "variables": {
            "f": {"userLegacyId": str(user_legacy_id)}, "first": 50, "after": after}})
        if r.get("errors") and not (r.get("data") or {}).get("adSearch"):
            break
        conn = ((r.get("data") or {}).get("adSearch") or {}).get("ads") or {}
        nodes = conn.get("nodes") or []
        for n in nodes:
            rid = str(n.get("legacyResourceId") or "")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            c = n.get("category") or {}
            out.append({"id": rid, "title": n.get("title"), "price": n.get("price"),
                        "photo": (n.get("photo") or {}).get("url"),
                        "category": c.get("name"), "category_id": str(c.get("legacyResourceId") or "")})
        if log:
            log(f"  {len(out)} məhsul…")
        pi = conn.get("pageInfo") or {}
        if cap and len(out) >= cap:
            break
        if not pi.get("hasNextPage") or not nodes:
            break
        after = pi.get("endCursor")
        time.sleep(sleep)
    return out


class StoreStore:
    def __init__(self):
        self.db = sqlite3.connect(DB, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)
        try:  # köhnə stores cədvəlinə last_sync əlavə et
            self.db.execute("ALTER TABLE stores ADD COLUMN last_sync TEXT")
        except sqlite3.OperationalError:
            pass
        self.db.commit()

    def add(self, url_or_slug):
        slug = slug_of(url_or_slug)
        if not slug:
            return {"error": "mağaza linki/slug tapılmadı"}
        meta = resolve_store(slug)
        if meta.get("error"):
            return meta
        if not meta.get("user_legacy_id"):
            return {"error": "mağaza sahibi (user) tapılmadı"}
        self.db.execute("INSERT OR REPLACE INTO stores(slug,name,user_legacy_id,ads_count,logo_url,added_at,last_sync) "
                        "VALUES(?,?,?,?,?,?,COALESCE((SELECT last_sync FROM stores WHERE slug=?),NULL))",
                        (slug, meta["name"], meta["user_legacy_id"], meta["ads_count"], meta["logo_url"],
                         time.strftime("%Y-%m-%d %H:%M"), slug))
        self.db.commit()
        return {"ok": True, "store": meta}

    def list(self):
        out = []
        for r in self.db.execute("SELECT * FROM stores ORDER BY name").fetchall():
            d = dict(r)
            d["cached"] = self.db.execute("SELECT COUNT(*) c FROM store_products WHERE store_slug=?", (d["slug"],)).fetchone()["c"]
            out.append(d)
        return out

    def get(self, slug):
        r = self.db.execute("SELECT * FROM stores WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None

    def remove(self, slug):
        self.db.execute("DELETE FROM stores WHERE slug=?", (slug,))
        self.db.execute("DELETE FROM store_products WHERE store_slug=?", (slug,))
        self.db.commit()
        return {"ok": True}

    def sync(self, slug, log=None):
        """Mağazanın bütün məhsullarını tap.az-dan çək → keşi yenilə."""
        st = self.get(slug)
        if not st:
            return {"error": "mağaza yoxdur"}
        items = _fetch_all(st["user_legacy_id"], log=log)
        now = time.strftime("%Y-%m-%d %H:%M")
        self.db.execute("DELETE FROM store_products WHERE store_slug=?", (slug,))
        self.db.executemany(
            "INSERT OR REPLACE INTO store_products(store_slug,listing_id,title,price,photo,category,category_id,synced_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            [(slug, it["id"], it["title"], it["price"], it["photo"], it["category"], it["category_id"], now) for it in items])
        self.db.execute("UPDATE stores SET last_sync=?, ads_count=? WHERE slug=?", (now, len(items), slug))
        self.db.commit()
        return {"ok": True, "count": len(items), "last_sync": now}

    def cats(self, slug):
        rows = self.db.execute(
            "SELECT category_id, category, COUNT(*) c FROM store_products WHERE store_slug=? "
            "GROUP BY category_id ORDER BY c DESC", (slug,)).fetchall()
        total = self.db.execute("SELECT COUNT(*) c FROM store_products WHERE store_slug=?", (slug,)).fetchone()["c"]
        return {"total": total, "cats": [{"id": r["category_id"], "name": r["category"], "count": r["c"]} for r in rows]}

    def cached(self, slug, category=None, limit=24, offset=0):
        where = "store_slug=?"; args = [slug]
        if category and category != "all":
            where += " AND category_id=?"; args.append(category)
        total = self.db.execute(f"SELECT COUNT(*) c FROM store_products WHERE {where}", args).fetchone()["c"]
        rows = self.db.execute(
            f"SELECT listing_id,title,price,photo,category FROM store_products WHERE {where} "
            "ORDER BY CAST(listing_id AS INTEGER) DESC LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        items = [{"id": r["listing_id"], "title": r["title"], "price": r["price"],
                  "photo": r["photo"], "category": r["category"]} for r in rows]
        return {"items": items, "total": total, "offset": offset, "limit": limit,
                "has_next": offset + len(items) < total}
