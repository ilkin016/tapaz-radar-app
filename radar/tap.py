#!/usr/bin/env python3
"""tap.az client: category feed crawl, ad detail, phone reveal. Portable (stdlib only)."""
import re, json, ssl, time, base64, urllib.request, urllib.error

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
GRAPHQL = "https://tap.az/graphql"

FEED_Q = ("query Feed($filters: AdFilterInput, $first: Int, $after: String, $order: AdOrderEnum){"
          " adSearch(filters:$filters, source:DESKTOP, orderType:$order){"
          " ads(first:$first, after:$after){ nodes{ legacyResourceId title price updatedAt }"
          " pageInfo{ endCursor hasNextPage } } } }")
CREATECALL_Q = ("mutation CreateCall($shopId: ID, $adId: ID, $source: SourceEnum!){"
                " createCall(shopId:$shopId, adId:$adId, source:$source){ entity errors{ message path } } }")


def _post_json(url, payload, tries=4, timeout=40):
    body = json.dumps(payload).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers={
                "User-Agent": UA, "Content-Type": "application/json", "Origin": "https://tap.az"})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e; time.sleep(1.2 * (i + 1))
    raise RuntimeError(f"POST failed: {last}")


def _get(url, tries=4, timeout=30):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "az,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
                return r.read().decode("utf-8", "replace"), r.getcode()
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None, e.code
            last = e; time.sleep(1.2 * (i + 1))
        except Exception as e:
            last = e; time.sleep(1.2 * (i + 1))
    return None, 0


def _next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def category_meta_from_url(url):
    """Resolve category gid + total count from a tap.az category page URL."""
    html, code = _get(url)
    if not html:
        raise RuntimeError(f"category page fetch failed ({code})")
    data = _next_data(html)
    ap = data["props"]["pageProps"]["apolloState"]
    rq = ap.get("ROOT_QUERY", {})
    cat_id = None
    for k, v in rq.items():
        if k.startswith("adSearch") and isinstance(v, dict):
            m = re.search(r'"categoryId":"([^"]+)"', k)
            if m: cat_id = m.group(1)
    # total count: Category:*.count or category({...}).count
    count = None
    for k, v in ap.items():
        if k.startswith("Category:") and isinstance(v, dict) and v.get("count"):
            count = v["count"]
    slug = re.sub(r'^https?://tap\.az/elanlar/', '', url).split('?')[0].strip('/').split('/')[-1]
    return {"category_id": cat_id, "count": count, "slug": slug, "url": url.split('?')[0]}


def _filters(cat_id, f=None):
    f = f or {}
    flt = {"categoryId": cat_id}
    pf, pt = f.get("price_from"), f.get("price_to")
    if pf is not None or pt is not None:
        flt["price"] = {"from": pf, "to": pt}
    if f.get("only_new"):
        flt["propertyOptions"] = {"boolean": [{"id": "769", "value": True}], "collection": [], "range": []}
    return flt


def crawl_category(cat_id, filters=None, first=100, cap=None, sleep=0.25, log=None):
    """Enumerate ALL current ads in a category via cursor pagination.
    Returns list of dicts: {id, title, price, updatedAt}. `cap` limits for testing."""
    out = []
    after = None
    seen_local = set()
    page = 0
    while True:
        r = _post_json(GRAPHQL, {"query": FEED_Q, "variables": {
            "filters": _filters(cat_id, filters), "first": first, "after": after, "order": None}})
        if "errors" in r and not (r.get("data") or {}).get("adSearch"):
            raise RuntimeError("feed error: " + json.dumps(r["errors"])[:300])
        conn = ((r.get("data") or {}).get("adSearch") or {}).get("ads") or {}
        nodes = conn.get("nodes") or []
        pi = conn.get("pageInfo") or {}
        for n in nodes:
            rid = n.get("legacyResourceId")
            if rid and rid not in seen_local:
                seen_local.add(rid)
                out.append({"id": str(rid), "title": n.get("title"),
                            "price": n.get("price"), "updatedAt": n.get("updatedAt")})
        page += 1
        if log: log(f"  feed page {page}: +{len(nodes)} (total {len(out)})")
        if cap and len(out) >= cap:
            return out[:cap]
        if not pi.get("hasNextPage") or not nodes:
            break
        after = pi.get("endCursor")
        time.sleep(sleep)
    return out


def gid_for_ad(numeric_id):
    return base64.b64encode(f"gid://tap/Ad/{numeric_id}".encode()).decode()


def fetch_detail(numeric_id, sleep=0.1):
    """Fetch a listing page and extract the full Ad record + resolve shop/contact/user."""
    url = f"https://tap.az/elanlar/elektronika/noutbuklar/{numeric_id}"  # any category path works for /<id>
    # tap.az resolves /<id> under any category slug; use a generic canonical if needed
    html, code = _get(url)
    rec = {"id": str(numeric_id), "link": f"https://tap.az/elanlar/elektronika/noutbuklar/{numeric_id}", "fetch_code": code}
    if not html:
        rec["available"] = False; rec["note"] = f"fetch_{code}"; return rec
    data = _next_data(html)
    if not data:
        rec["available"] = False; rec["note"] = "no_next_data"; return rec
    ap = data["props"]["pageProps"]["apolloState"]
    ad = None
    for k, v in ap.items():
        if k.startswith("Ad:") and isinstance(v, dict) and v.get("title"):
            ad = v; break
    if not ad:
        rec["available"] = False; rec["note"] = "no_ad"; return rec
    rec["available"] = True
    rec["name"] = ad.get("title"); rec["price"] = ad.get("price")
    rec["region"] = ad.get("region"); rec["hits"] = ad.get("hits")
    rec["updatedAt"] = ad.get("updatedAt"); rec["body"] = ad.get("body") or ""
    rec["gid"] = ad.get("id"); rec["path"] = ad.get("path")
    props = ad.get("azProperties") or ad.get("properties") or []
    pdict = {(p["name"] or "").strip(): p.get("value") for p in props if isinstance(p, dict) and p.get("name")}
    rec["properties"] = pdict
    rec["brand"] = pdict.get("Marka")
    rec["is_new"] = pdict.get("Yeni?")
    rec["delivery"] = pdict.get("Çatdırılma?")
    # condition (Yeni / İkinci əl) from the "Yeni?" boolean property
    yn = (pdict.get("Yeni?") or "").strip().lower()
    rec["condition"] = "Yeni" if yn.startswith("b") else ("İkinci əl" if yn.startswith("x") else "")
    # sub-category: the ad's own "Məhsul kateqoriyası" (multi-cat), else last breadcrumb category
    subcat = pdict.get("Məhsul kateqoriyası")
    if not subcat:
        cats = re.findall(r'"@type":"ListItem","item":"[^"]*","name":"([^"]+)","position"', html)
        cats = [c for c in cats if c not in ("Mağazalar", "Bütün kateqoriyalar", "Elektronika")]
        subcat = cats[-1] if cats else None
    rec["subcategory"] = (subcat or "").strip() or None
    shop = None
    sref = (ad.get("shop") or {}).get("__ref") if isinstance(ad.get("shop"), dict) else None
    if sref and sref in ap:
        s = ap[sref]
        shop = {"name": s.get("name"), "uri": s.get("uri"), "adsCount": s.get("adsCount")}
    rec["shop"] = shop
    contact = None
    cref = (ad.get("contact") or {}).get("__ref") if isinstance(ad.get("contact"), dict) else None
    if cref and cref in ap:
        c = ap[cref]
        contact = {"name": c.get("name"), "phones_masked": c.get("phones")}
    rec["contact"] = contact
    if shop and shop.get("name"):
        rec["seller_type"] = "Mağaza"; rec["seller"] = shop.get("name")
        rec["shop_url"] = "https://tap.az" + shop["uri"] if shop.get("uri") else None
    else:
        rec["seller_type"] = "Şəxsi"; rec["seller"] = (contact or {}).get("name"); rec["shop_url"] = None
    if not rec["brand"]:
        mb = re.search(r'"brand":\{"@type":"Brand","name":"([^"]+)"', html)
        if mb: rec["brand"] = mb.group(1)
    time.sleep(sleep)
    return rec


def reveal_phones(gid, tries=3):
    for i in range(tries):
        try:
            r = _post_json(GRAPHQL, {"operationName": "CreateCall", "query": CREATECALL_Q,
                                     "variables": {"adId": gid, "shopId": None, "source": "DESKTOP"}})
            ent = (((r.get("data") or {}).get("createCall") or {}) or {}).get("entity")
            return ent or []
        except Exception:
            time.sleep(1.0 * (i + 1))
    return []
