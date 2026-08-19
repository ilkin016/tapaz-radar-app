#!/usr/bin/env python3
"""tap.az posting engine — köhnə elanı öz hesabından DRAFT kimi yenidən yerləşdirir.

Axın:  read_ad_for_repost(id) → reupload_photos → build_create_ad_params → create_draft
       → elan MODERASİYAYA düşür (dərhal canlı OLMUR) → check_status ilə izlənir.

Auth AuthClient (tapaz_auth.py) ilə — sessiya cookie + csrfToken. Yalnız istifadəçinin ÖZ hesabı.
M0-da təsdiqləndi: createAd işləyir (elan 48443132), /pond→200 (sessiya-cookie). Arxitektura: Mac-local."""
import re, json, base64, ssl, mimetypes, urllib.request, uuid
from radar import tap

_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE
GRAPHQL = "https://tap.az/graphql"
POND = "https://photos.tap.az/pond?lang=az"

_CAT_ID = {
    "noutbuklar": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNw",
    "komputerler": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNA",
    "komputer-avadanliqi": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxNQ",
    "komputer-aksesuarlari": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxMg",
    "ofis-avadanliqi": "Z2lkOi8vdGFwL0NhdGVnb3J5LzYxMw",
}
_BOOL_LEGACY = {"Yeni?": "769", "Çatdırılma?": "858"}
# Bakı region gid (formada default Şəhər=Bakı). resolve_region ilə də təsdiqlənir.
_REGION_BAKI = "Z2lkOi8vdGFwL1JlZ2lvbi8x"


def gid(numeric_id):
    return base64.b64encode(f"gid://tap/Ad/{numeric_id}".encode()).decode()


def _parse_prop_link(link):
    if not link:
        return None, None
    m = re.search(r"p(?:%5B|\[)(\d+)(?:%5D|\])=([\w-]+)", link)
    return (m.group(1), m.group(2)) if m else (None, None)


# ---------------- 1) AdReader ----------------
def read_ad_for_repost(numeric_id):
    numeric_id = str(numeric_id).strip()
    slug = None
    for s in _CAT_ID:
        html, code = tap._get(f"https://tap.az/elanlar/elektronika/{s}/{numeric_id}")
        if code == 200 and "__NEXT_DATA__" in html:
            slug = s
            break
    else:
        return {"error": f"Elan {numeric_id} tapılmadı"}
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return {"error": "__NEXT_DATA__ yoxdur"}
    ap = json.loads(m.group(1))["props"]["pageProps"].get("apolloState", {})
    adk = next((k for k in ap if k.startswith("Ad:")), None)
    if not adk:
        return {"error": "Ad obyekti yoxdur"}
    ad = ap[adk]
    path = ad.get("path", "")
    cat_slug = next((s for s in _CAT_ID if f"/{s}/" in path or f"/{s}" in path), slug)
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
        "numeric_id": numeric_id, "gid": ad.get("id") or gid(numeric_id),
        "category_slug": cat_slug, "categoryId": _CAT_ID.get(cat_slug),
        "region": ad.get("region"), "title": ad.get("title"), "body": ad.get("body"),
        "price": ad.get("price"), "status": ad.get("status"),
        "properties": {"collection": coll, "boolean": boolean},
        "params": {p.get("name"): p.get("value") for p in ad.get("properties", []) if p.get("name")},
        "link": ("https://tap.az" + path) if path else f"https://tap.az/elanlar/elektronika/{cat_slug}/{numeric_id}",
        "photos": photos, "n_photos": len(photos),
    }


# ---------------- 2) Photo reupload ----------------
def download_photo(url):
    """tap.azstatic.com public şəkil URL-i → bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": tap.UA if hasattr(tap, "UA") else "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40, context=_CTX) as r:
        return r.read()


def _multipart(field, filename, content, mime="image/jpeg"):
    boundary = "----tapazradar" + uuid.uuid4().hex
    b = boundary.encode()
    body = b"".join([
        b"--", b, b"\r\n",
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {mime}\r\n\r\n".encode(), content, b"\r\n",
        b"--", b, b"--\r\n",
    ])
    return body, "multipart/form-data; boundary=" + boundary


def reupload_photo(auth, img_bytes, filename="photo.jpg"):
    """POST /pond (sessiya-cookie) → photoId (yol/path). auth = AuthClient.
    ‼️ Canlı test: /pond HTML qaytarır (FilePond), JSON yox.
    photoId = <input name="gallery[photo_ids][]" value="YOL"> dəyəri."""
    body, ctype = _multipart("images[]", filename, img_bytes)
    h = {"Content-Type": ctype, "Origin": "https://tap.az", "Referer": "https://tap.az/",
         "User-Agent": getattr(tap, "UA", "Mozilla/5.0")}
    if getattr(auth, "csrf", None):
        h["X-CSRF-Token"] = auth.csrf
    req = urllib.request.Request(POND, data=body, headers=h, method="POST")
    with auth.opener.open(req, timeout=60) as r:
        html = r.read().decode("utf-8", "ignore")
    m = re.search(r'name="gallery\[photo_ids\]\[\]"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None


def reupload_all(auth, photo_urls, limit=10):
    ids = []
    for i, u in enumerate(photo_urls[:limit]):
        try:
            ids.append(reupload_photo(auth, download_photo(u), f"photo{i}.jpg"))
        except Exception as e:
            ids.append({"error": str(e), "url": u})
    return ids


# ---------------- 3) PropertyMapper + createAd params ----------------
def build_property_set(ad_data):
    props = ad_data.get("properties", {})
    return {
        "boolean": [{"legacyId": b["legacyId"], "value": bool(b["value"])} for b in props.get("boolean", [])],
        "collection": [{"legacyId": c["legacyId"], "value": c["value"]} for c in props.get("collection", [])],
        "range": [],
    }


def build_create_ad_params(ad_data, photo_ids, contact, region_id=None):
    """CreateAdAttributes qur. contact={name,email,phone,contactType}."""
    return {
        "categoryId": ad_data["categoryId"],
        "regionId": region_id or _REGION_BAKI,
        "title": ad_data["title"],
        "body": ad_data["body"],
        "price": ad_data.get("price"),
        "photoIds": [p for p in (photo_ids or []) if isinstance(p, str)],
        "propertySet": build_property_set(ad_data),
        "contactAttributes": {
            "contactType": contact.get("contactType", "CALLS_AND_MESSAGES"),
            "name": contact.get("name", ""), "email": contact.get("email", ""),
            "phones": [contact.get("phone", "")],
        },
        "source": "DESKTOP",
    }


# ---------------- 4) createAd (DRAFT → moderasiya) ----------------
_CREATE_AD_Q = ("mutation CreateAd($adParams: CreateAdAttributes!){ createAd(adParams:$adParams){ "
                "entity{ id legacyResourceId status } errors{ message path } } }")
_SUBMISSION_Q = ("mutation CreateAdSubmission($status: AdSubmissionStatusEnum!, $source: SourceEnum!, "
                 "$flowId: ID, $categoryId: ID){ createAdSubmission(status: $status, source: $source, "
                 "flowId: $flowId, categoryId: $categoryId){ entity errors{ message path } } }")


def _auth_headers(auth):
    return {"Referer": "https://tap.az/", **({"X-CSRF-Token": auth.csrf} if getattr(auth, "csrf", None) else {})}


def start_ad_flow(auth, category_id):
    """tap.az yeni elan-axını: START → flowId, sonra CATEGORY_SELECT. flowId qaytarır (və ya {error})."""
    H = _auth_headers(auth)
    st, js = auth._req(GRAPHQL, {"operationName": "CreateAdSubmission", "query": _SUBMISSION_Q,
                                 "variables": {"status": "START", "source": "DESKTOP"}}, headers=H)
    sub = (js or {}).get("data", {}).get("createAdSubmission") if isinstance(js, dict) else None
    if not sub or sub.get("errors") or not sub.get("entity"):
        return {"error": "flow START alınmadı", "resp": (sub or (js if isinstance(js, dict) else str(js)[:200]))}
    flow_id = sub["entity"]
    if category_id:
        st2, js2 = auth._req(GRAPHQL, {"operationName": "CreateAdSubmission", "query": _SUBMISSION_Q,
                                       "variables": {"status": "CATEGORY_SELECT", "source": "DESKTOP",
                                                     "flowId": flow_id, "categoryId": category_id}}, headers=H)
        sub2 = (js2 or {}).get("data", {}).get("createAdSubmission") if isinstance(js2, dict) else None
        if sub2 and sub2.get("errors"):
            return {"error": "CATEGORY_SELECT xəta", "resp": sub2["errors"]}
    return {"ok": True, "flow_id": flow_id}


def create_draft(auth, ad_params, use_flow=True):
    """createAd → elan yaradılır (MODERASİYAYA düşür). tap.az yeni axını: əvvəlcə flow başlat → flowId,
    sonra createAd(flowId). Flow alınmasa flowId-siz davam edir (köhnə üsul fallback)."""
    params = dict(ad_params)
    if use_flow:
        flow = start_ad_flow(auth, params.get("categoryId"))
        if flow.get("ok"):
            params["flowId"] = flow["flow_id"]  # flow uğurlu → flowId əlavə
    st, js = auth._req(GRAPHQL, {"operationName": "CreateAd", "query": _CREATE_AD_Q,
                                 "variables": {"adParams": params}}, headers=_auth_headers(auth))
    d = (js or {}).get("data", {}).get("createAd") if isinstance(js, dict) else None
    if not d:
        return {"ok": False, "resp": js if isinstance(js, dict) else str(js)[:300]}
    if d.get("errors"):
        return {"ok": False, "errors": d["errors"]}
    ent = d.get("entity") or {}
    return {"ok": True, "ad_gid": ent.get("id"), "legacyId": ent.get("legacyResourceId"), "status": ent.get("status")}


# ---------------- 5) Status yoxlaması ----------------
# ‼️ M0 canlı testdə təsdiqləndi: `ad` sorğusu `legacyId` (nömrə) qəbul edir, `id`(gid) YOX.
_AD_STATUS_Q = "query($lid:ID!){ ad(legacyId:$lid){ id status isExpiredManually rejectReason } }"


def check_status(auth, legacy_id):
    """Yaradılmış elanın moderasiya statusu: yoxlanılır / təsdiqləndi / rədd (legacy_id = nömrə)."""
    st, js = auth._req(GRAPHQL, {"query": _AD_STATUS_Q, "variables": {"lid": str(legacy_id)}},
                       headers={"Referer": "https://tap.az/"})
    ad = (js or {}).get("data", {}).get("ad") if isinstance(js, dict) else None
    if not ad:
        return {"ok": False, "resp": js}
    s = ad.get("status")
    label = {"APPROVED": "✅ Təsdiqləndi (canlı)", "PENDING": "🕒 Yoxlanılır",
             "MODERATION": "🕒 Yoxlanılır", "REJECTED": "❌ Rədd edildi (yenidən düzəlt)"}.get(s, s)
    return {"ok": True, "status": s, "label": label, "reject": ad.get("rejectReason")}


# ---------------- 6) Tam repost orkestratoru ----------------
def repost(auth, listing_id, contact, dry_run=False):
    """Köhnə elan → DRAFT. dry_run=True: yalnız payload qur (post etmə)."""
    ad = read_ad_for_repost(listing_id)
    if ad.get("error"):
        return {"stage": "read", "error": ad["error"]}
    if dry_run:
        params = build_create_ad_params(ad, ["<photoId>"] * ad["n_photos"], contact)
        return {"stage": "dry_run", "ad": ad, "params": params}
    photo_ids = reupload_all(auth, ad["photos"])
    params = build_create_ad_params(ad, photo_ids, contact)
    res = create_draft(auth, params)
    if not res.get("ok"):
        return {"stage": "createAd", "params": params, "result": res}
    status = check_status(auth, res.get("legacyId") or res.get("ad_gid"))
    return {"stage": "done", "created": res, "status": status, "source_id": listing_id}


if __name__ == "__main__":
    import sys
    print(json.dumps(read_ad_for_repost(sys.argv[1] if len(sys.argv) > 1 else "48336921"),
                     ensure_ascii=False, indent=1))
