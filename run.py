#!/usr/bin/env python3
"""tap.az Radar — daily scan of selected categories, detect ONLY new listings, build dashboards.

Usage:
  python3 run.py                 # run all enabled categories (full)
  python3 run.py --cap 150       # limit crawl per category (for testing)
  python3 run.py --add <url>     # resolve & print a category's id (to add to config)
  python3 run.py --report-only   # regenerate dashboards from existing DB
"""
import os, sys, json, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from radar import tap, enrich as enr
from radar.store import Store, now_iso
from radar.report_html import build_html
from radar.report_excel import build_excel

CFG = os.path.join(HERE, "config", "categories.json")
DB = os.path.join(HERE, "data", "radar.db")
OUT = os.path.join(HERE, "out")


def load_cfg():
    return json.load(open(CFG, encoding="utf-8"))


def cmd_add(url):
    meta = tap.category_meta_from_url(url)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print("\n→ config/categories.json-a bu obyekti əlavə et:")
    print(json.dumps({"name": meta["slug"].title(), "slug": meta["slug"], "url": meta["url"],
                      "category_id": meta["category_id"], "enabled": True,
                      "filters": {"price_from": None, "price_to": None, "only_new": False},
                      "enrich": True}, ensure_ascii=False, indent=2))


def run(cap=None, workers=6, only=None):
    cfg = load_cfg()
    store = Store(DB)
    run_ts = now_iso()
    print(f"=== RADAR RUN {run_ts} ===")
    for cat in cfg["categories"]:
        if not cat.get("enabled"):
            continue
        if only and cat["slug"] != only:
            continue
        slug = cat["slug"]
        try:
            print(f"\n[{slug}] kraler başlayır…")
            crawled = tap.crawl_category(cat["category_id"], cat.get("filters"), first=100,
                                         cap=cap, log=lambda m: print(m))
            print(f"[{slug}] cari elan: {len(crawled)}")
            new_items, delisted = store.diff_new(slug, crawled, run_ts)
            print(f"[{slug}] YENİ: {len(new_items)} · silinən (delisted): {len(delisted)}")
            # enrich new listings
            enriched = 0
            if cat.get("enrich", True) and new_items:
                def work(it):
                    d = tap.fetch_detail(it["id"])
                    if not d.get("available"):
                        return None
                    d["phones"] = tap.reveal_phones(d["gid"]) if d.get("gid") else []
                    return enr.enrich(d, category=slug)
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    futs = {ex.submit(work, it): it for it in new_items}
                    for i, f in enumerate(as_completed(futs), 1):
                        try:
                            rec = f.result()
                        except Exception:
                            rec = None
                        if rec:
                            store.upsert_listing(rec, slug, run_ts)
                            enriched += 1
                        if i % 25 == 0:
                            print(f"  zənginləşdirildi {i}/{len(new_items)}")
            store.record_run(run_ts, slug, len(crawled), len(new_items), len(delisted))
            print(f"[{slug}] tamam: {enriched} yeni elan zənginləşdirildi.")
        except Exception as e:
            print(f"[{slug}] XƏTA — kateqoriya atlanır (hesabat yenə yaranacaq): {e}")
    # reports
    os.makedirs(OUT, exist_ok=True)
    listings = store.listings(active_only=True)
    new_now = store.new_in_run(run_ts)
    print(f"\nHesabat: {len(listings)} aktiv elan, {len(new_now)} bu run-da yeni.")
    html_path = os.path.join(OUT, "dashboard.html")
    xlsx_path = os.path.join(OUT, "tapaz_radar.xlsx")
    build_html(listings, new_now, run_ts, html_path, cat_last=store.cat_last_runs())
    build_excel(listings, {r["ad_id"] for r in new_now}, run_ts, xlsx_path)
    print(f"✓ {html_path}\n✓ {xlsx_path}")
    print("Stats:", store.stats())


def report_only():
    store = Store(DB)
    run_ts = store.last_run_ts() or now_iso()
    listings = store.listings(active_only=True)
    new_now = store.new_in_run(run_ts)
    os.makedirs(OUT, exist_ok=True)
    build_html(listings, new_now, run_ts, os.path.join(OUT, "dashboard.html"), cat_last=store.cat_last_runs())
    build_excel(listings, {r["ad_id"] for r in new_now}, run_ts, os.path.join(OUT, "tapaz_radar.xlsx"))
    print("Reports regenerated from DB.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=None)
    ap.add_argument("--add", type=str, default=None)
    ap.add_argument("--only", type=str, default=None, help="yalnız bir kateqoriya (slug)")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    if a.add:
        cmd_add(a.add)
    elif a.report_only:
        report_only()
    else:
        run(cap=a.cap, only=a.only)
