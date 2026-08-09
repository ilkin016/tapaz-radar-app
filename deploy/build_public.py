#!/usr/bin/env python3
"""Public (phone-free) dashboard → deploy/site/index.html"""
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from radar.store import Store
from radar.report_html import build_html
store=Store(os.path.join(ROOT,"data","radar.db"))
ts=store.last_run_ts() or ""
listings=store.listings(active_only=True)
new_now=store.new_in_run(ts) if ts else []
out=os.path.join(HERE,"site","index.html")
build_html(listings, new_now, ts, out, public=True)
print("public dashboard:", out, round(os.path.getsize(out)/1e6,2),"MB")
