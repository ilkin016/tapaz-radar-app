#!/usr/bin/env python3
"""tap.az mağazaları (shops): əlavə et, məhsullarını gətir, birbaşa PCTECH-ə (draft) əlavə et.
Mexanizm: shop(slug){ user{ legacyId } } → adSearch(filters:{userLegacyId}) səhifələmə ilə."""
import sqlite3, os, re, time
from radar import tap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "radar.db")

_SHOP_Q = "query($s:String!){ shop(slug:$s){ name adsCount uri logo{ url } user{ legacyId } } }"
_ADS_Q = ("query($f:AdFilterInput,$first:Int,$after:String){ adSearch(filters:$f, source:DESKTOP){"
          " ads(first:$first, after:$after){ nodes{ legacyResourceId title price photo{ url } }"
          " pageInfo{ endCursor hasNextPage } } } }")

_SCHEMA = """CREATE TABLE IF NOT EXISTS stores(
  slug TEXT PRIMARY KEY, name TEXT, user_legacy_id TEXT, ads_count INTEGER,
  logo_url TEXT, added_at TEXT);"""


def slug_of(url_or_slug):
    s = (url_or_slug or "").strip()
    m = re.search(r"tap\.az/shops/([A-Za-z0-9_\-\.]+)", s)
    if m:
        return m.group(1)
    return s.strip("/").split("/")[-1]


def resolve_store(slug):
    """Mağaza meta + user legacyId (adSearch filtri üçün)."""
    r = tap._post_json(tap.GRAPHQL, {"query": _SHOP_Q, "variables": {"s": slug}})
    if r.get("errors"):
        return {"error": "mağaza tapılmadı: " + slug}
    sh = (r.get("data") or {}).get("shop")
    if not sh:
        return {"error": "mağaza yoxdur: " + slug}
    return {"slug": slug, "name": sh.get("name"), "ads_count": sh.get("adsCount"),
            "user_legacy_id": (sh.get("user") or {}).get("legacyId"),
            "logo_url": (sh.get("logo") or {}).get("url")}


def store_products(user_legacy_id, first=24, after=None):
    """Mağazanın (user-in) məhsulları — bir səhifə."""
    r = tap._post_json(tap.GRAPHQL, {"query": _ADS_Q, "variables": {
        "f": {"userLegacyId": str(user_legacy_id)}, "first": first, "after": after}})
    if r.get("errors") and not (r.get("data") or {}).get("adSearch"):
        return {"error": "elanlar gəlmədi", "items": []}
    conn = ((r.get("data") or {}).get("adSearch") or {}).get("ads") or {}
    items = [{"id": str(n.get("legacyResourceId")), "title": n.get("title"),
              "price": n.get("price"), "photo": (n.get("photo") or {}).get("url")}
             for n in (conn.get("nodes") or []) if n.get("legacyResourceId")]
    pi = conn.get("pageInfo") or {}
    return {"items": items, "next": pi.get("endCursor"), "has_next": bool(pi.get("hasNextPage"))}


class StoreStore:
    def __init__(self):
        self.db = sqlite3.connect(DB, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(_SCHEMA); self.db.commit()

    def add(self, url_or_slug):
        slug = slug_of(url_or_slug)
        if not slug:
            return {"error": "mağaza linki/slug tapılmadı"}
        meta = resolve_store(slug)
        if meta.get("error"):
            return meta
        if not meta.get("user_legacy_id"):
            return {"error": "mağaza sahibi (user) tapılmadı"}
        self.db.execute("INSERT OR REPLACE INTO stores(slug,name,user_legacy_id,ads_count,logo_url,added_at) "
                        "VALUES(?,?,?,?,?,?)", (slug, meta["name"], meta["user_legacy_id"],
                                                meta["ads_count"], meta["logo_url"], time.strftime("%Y-%m-%d %H:%M")))
        self.db.commit()
        return {"ok": True, "store": meta}

    def list(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM stores ORDER BY name").fetchall()]

    def get(self, slug):
        r = self.db.execute("SELECT * FROM stores WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None

    def remove(self, slug):
        self.db.execute("DELETE FROM stores WHERE slug=?", (slug,)); self.db.commit()
        return {"ok": True}
