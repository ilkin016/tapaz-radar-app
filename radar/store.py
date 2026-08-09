#!/usr/bin/env python3
"""SQLite state: the 'memory' that makes NEW-only detection possible."""
import sqlite3, json, os, datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
  category   TEXT NOT NULL,
  ad_id      TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen  TEXT NOT NULL,
  active     INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (category, ad_id)
);
CREATE TABLE IF NOT EXISTS listings (
  ad_id       TEXT PRIMARY KEY,
  category    TEXT,
  name        TEXT, brand TEXT, price REAL, band TEXT,
  cpu TEXT, cpu_fam TEXT, ram INTEGER, storage TEXT, screen TEXT, gpu TEXT, os TEXT,
  params TEXT, spec_score REAL, value_score REAL, usage TEXT,
  condition TEXT, subcategory TEXT,
  is_new TEXT, seller_type TEXT, seller TEXT, phones TEXT,
  shop_url TEXT, link TEXT, region TEXT, hits INTEGER,
  updated_at TEXT, body TEXT,
  first_seen TEXT, last_seen TEXT, active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS runs (
  run_ts TEXT, category TEXT, crawled INTEGER, new_count INTEGER, delisted INTEGER
);
CREATE INDEX IF NOT EXISTS idx_listings_cat ON listings(category);
CREATE INDEX IF NOT EXISTS idx_listings_first ON listings(first_seen);
"""


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---- seen-set diff (core of NEW detection) ----
    def diff_new(self, category, crawled_items, run_ts):
        """Given crawled [{id,...}], return the list of items whose id is NEW for this category.
        Also updates seen-set (first_seen for new, last_seen/active for all) and marks missing as inactive."""
        cur = self.db.cursor()
        existing = {r["ad_id"] for r in cur.execute(
            "SELECT ad_id FROM seen WHERE category=?", (category,))}
        crawled_ids = {it["id"] for it in crawled_items}
        new_items = [it for it in crawled_items if it["id"] not in existing]
        # upsert seen
        for it in crawled_items:
            if it["id"] in existing:
                cur.execute("UPDATE seen SET last_seen=?, active=1 WHERE category=? AND ad_id=?",
                            (run_ts, category, it["id"]))
            else:
                cur.execute("INSERT INTO seen(category,ad_id,first_seen,last_seen,active) VALUES(?,?,?,?,1)",
                            (category, it["id"], run_ts, run_ts))
        # delisted: previously active, not in this crawl
        delisted = [aid for aid in existing if aid not in crawled_ids]
        for aid in delisted:
            cur.execute("UPDATE seen SET active=0 WHERE category=? AND ad_id=?", (category, aid))
            cur.execute("UPDATE listings SET active=0 WHERE ad_id=?", (aid,))
        self.db.commit()
        return new_items, delisted

    def upsert_listing(self, rec, category, run_ts):
        cols = ["ad_id", "category", "name", "brand", "price", "band", "cpu", "cpu_fam", "ram",
                "storage", "screen", "gpu", "os", "params", "spec_score", "value_score", "usage",
                "condition", "subcategory",
                "is_new", "seller_type", "seller", "phones", "shop_url", "link", "region", "hits",
                "updated_at", "body", "last_seen", "active"]
        row = {c: rec.get(c) for c in cols}
        row["ad_id"] = rec["id"]; row["category"] = category
        row["updated_at"] = rec.get("updatedAt"); row["last_seen"] = run_ts; row["active"] = 1
        cur = self.db.cursor()
        exists = cur.execute("SELECT first_seen FROM listings WHERE ad_id=?", (rec["id"],)).fetchone()
        first_seen = exists["first_seen"] if exists else run_ts
        placeholders = ",".join("?" for _ in cols) + ",?"
        cur.execute(f"INSERT OR REPLACE INTO listings({','.join(cols)},first_seen) VALUES({placeholders})",
                    [row[c] for c in cols] + [first_seen])
        self.db.commit()

    def record_run(self, run_ts, category, crawled, new_count, delisted):
        self.db.execute("INSERT INTO runs(run_ts,category,crawled,new_count,delisted) VALUES(?,?,?,?,?)",
                        (run_ts, category, crawled, new_count, delisted))
        self.db.commit()

    def listings(self, category=None, active_only=True):
        q = "SELECT * FROM listings WHERE 1=1"
        args = []
        if category: q += " AND category=?"; args.append(category)
        if active_only: q += " AND active=1"
        return [dict(r) for r in self.db.execute(q, args)]

    def new_in_run(self, run_ts, category=None):
        q = "SELECT * FROM listings WHERE first_seen=?"
        args = [run_ts]
        if category: q += " AND category=?"; args.append(category)
        return [dict(r) for r in self.db.execute(q, args)]

    def last_run_ts(self):
        r = self.db.execute("SELECT run_ts FROM runs ORDER BY run_ts DESC LIMIT 1").fetchone()
        return r["run_ts"] if r else None

    def stats(self):
        c = self.db.execute("SELECT COUNT(*) n FROM listings WHERE active=1").fetchone()["n"]
        runs = self.db.execute("SELECT COUNT(*) n FROM runs").fetchone()["n"]
        return {"active_listings": c, "runs": runs}
