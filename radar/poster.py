#!/usr/bin/env python3
"""tap.az posting modulu — M2: AdReader (auth tələb ETMİR).
Köhnə elanı nömrəsi ilə oxuyub tam repost payload-a çevirir (kateqoriya, region, başlıq,
təsvir, qiymət, atributlar[legacyId+value], şəkil URL-ləri). Bu, DRAFT yaratmanın girişidir.

Auth/createAd/pond hissələri (M1/M3/M4) AYRICA gəlir — canlı OTP sessiyası tələb edir (istifadəçi icra edir).
Arxitektura: Mac-local (Cloudflare residential IP). Bax docs/POSTING-MODULE-analiz.md."""
import re, json, base64
from radar import tap

# URL kateqoriya slug → tap.az categoryId (gid) — config/categories.json ilə eyni
_CAT_ID = {
    "noutbuklar": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNw",
    "komputerler": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNA",
    "komputer-avadanliqi": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNQ",
    "komputer-aksesuarlari": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxMg",
    "ofis-avadanliqi": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxMw",
}
# Boolean atributların adı → legacyId (formada boolean.769 kimi görünür; analiz: 769 Yeni?, 858 Çatdırılma?)
_BOOL_LEGACY = {"Yeni?": "769", "Çatdırılma?": "858"}


def gid(numeric_id):
    return base64.b64encode(f"gid://tap/Ad/{numeric_id}".encode()).decode()


def _parse_prop_link(link):
    """/elanlar/...?p%5B822%5D=4169 → (legacyId='822', optionId='4169') collection atributları üçün."""
    if not link:
        return None, None
    m = re.search(r"p(?:%5B|\[)(\d+)(?:%5D|\])=([\w-]+)", link)
    return (m.group(1), m.group(2)) if m else (None, None)


def read_ad_for_repost(numeric_id):
    """Köhnə elanı oxu → repost üçün struktur payload. Xəta olarsa {'error': ...}."""
    numeric_id = str(numeric_id).strip()
    # kateqoriya slug-ını tapmaq üçün əvvəl bütün elan URL-i (path apolloState-də var)
    for slug in _CAT_ID:
        url = f"https://tap.az/elanlar/elektronika/{slug}/{numeric_id}"
        html, code = tap._get(url)
        if code == 200 and "__NEXT_DATA__" in html:
            break
    else:
        return {"error": f"Elan {numeric_id} tapılmadı (404 və ya bütün slug-lar uğursuz)"}
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return {"error": "__NEXT_DATA__ tapılmadı"}
    ap = json.loads(m.group(1))["props"]["pageProps"].get("apolloState", {})
    adk = next((k for k in ap if k.startswith("Ad:")), None)
    if not adk:
        return {"error": "Ad obyekti tapılmadı"}
    ad = ap[adk]
    path = ad.get("path", url)
    cat_slug = next((s for s in _CAT_ID if f"/{s}/" in path or f"/{s}" in path), slug)

    # atributları ayır: collection (link-dən legacyId+optionId) və boolean (ad→legacyId, value Bəli/Xeyr)
    coll, boolean = [], []
    for p in ad.get("properties", []):
        name, val, link = p.get("name"), p.get("value"), p.get("link")
        lid, opt = _parse_prop_link(link)
        if lid and opt:
            coll.append({"legacyId": lid, "name": name, "value": opt, "text": val})
        elif name in _BOOL_LEGACY:
            boolean.append({"legacyId": _BOOL_LEGACY[name], "name": name, "value": (val == "Bəli")})
    photos = [x.get("url") for x in (ad.get("photos") or []) if x.get("url")]

    return {
        "numeric_id": numeric_id,
        "gid": ad.get("id") or gid(numeric_id),
        "category_slug": cat_slug,
        "categoryId": _CAT_ID.get(cat_slug),
        "region": ad.get("region"),
        "title": ad.get("title"),
        "body": ad.get("body"),
        "price": ad.get("price"),
        "status": ad.get("status"),
        "is_author": ad.get("isAuthor"),
        "properties": {"collection": coll, "boolean": boolean},
        "photos": photos,
        "n_photos": len(photos),
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(read_ad_for_repost(sys.argv[1] if len(sys.argv) > 1 else "48336921"),
                     ensure_ascii=False, indent=1))
