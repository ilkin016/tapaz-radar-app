#!/usr/bin/env python3
"""AI brend-uyğunlaşdırma (PCTECH) — OpenAI ilə.
- adapt_text(): elanı PCTECH brend səsinə yenidən yazır (GPT chat).
- generate_images(): məhsuldan PCTECH brendinə uyğun vahid-dizayn korporativ şəkillər generasiya edir (gpt-image).

Açar: OPENAI_API_KEY env (və ya config/brand.json-da). Açar yoxdursa {"error":...} qaytarır (mock/no-op)."""
import json, os, ssl, base64, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND_PATH = os.path.join(ROOT, "config", "brand.json")
OPENAI = "https://api.openai.com/v1"
_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE


def load_brand():
    try:
        return json.load(open(BRAND_PATH, encoding="utf-8"))
    except Exception:
        return {"name": "PCTECH"}


def _key():
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    try:
        s = json.load(open(os.path.join(ROOT, "data", "secrets.json"), encoding="utf-8"))
        if s.get("openai_api_key"):
            return s["openai_api_key"]
    except Exception:
        pass
    return load_brand().get("openai_api_key")


def set_key(key):
    """OpenAI açarını data/secrets.json-a saxla (gitignore, 0600)."""
    p = os.path.join(ROOT, "data", "secrets.json")
    s = {}
    try:
        s = json.load(open(p, encoding="utf-8"))
    except Exception:
        pass
    s["openai_api_key"] = key
    open(p, "w", encoding="utf-8").write(json.dumps(s))
    os.chmod(p, 0o600)
    return {"ok": True}


def has_key():
    return bool(_key())


def _post(path, payload, timeout=120):
    req = urllib.request.Request(OPENAI + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + _key()}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "ignore") or "{}")


# ---------------- Mətn ----------------
def adapt_text(title, body, brand=None):
    """Elan mətnini PCTECH brendinə uyğunlaşdır → {title, body} və ya {error}."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur — config/brand.json və ya env-ə əlavə et"}
    b = brand or load_brand()
    sys = (f"Sən {b['name']} texnologiya mağazasının kopирайтеridir. "
           f"Səs: {b.get('voice','')}. {b.get('text_instructions','')}")
    user = (f"Orijinal başlıq:\n{title}\n\nOrijinal təsvir:\n{body}\n\n"
            'JSON qaytar: {"title": "...", "body": "..."} — başqa heç nə.')
    st, js = _post("/chat/completions", {
        "model": b.get("text_model", "gpt-4o"),
        "messages": [{"role": "system", "content": sys}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"}, "temperature": 0.7})
    if st != 200:
        return {"error": f"OpenAI text {st}: {json.dumps(js)[:200]}"}
    try:
        out = json.loads(js["choices"][0]["message"]["content"])
        return {"title": out.get("title", title), "body": out.get("body", body)}
    except Exception as e:
        return {"error": f"parse: {e}"}


# ---------------- Şəkil ----------------
def generate_images(title, body, n=None, brand=None):
    """Məhsuldan PCTECH brendinə uyğun vahid-dizayn şəkillər generasiya → [bytes,...] və ya {error}."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur"}
    b = brand or load_brand()
    n = n or b.get("images_per_draft", 3)
    prompt = (f"{b.get('image_style','')}. Product: {title}. "
              f"Details: {(body or '')[:300]}. "
              f"Brand: {b['name']} — consistent unified corporate design across all images.")
    imgs = []
    for i in range(n):  # gpt-image-1: hər çağırışda 1 (vahid dizayn üçün eyni prompt + variasiya)
        st, js = _post("/images/generations", {
            "model": b.get("image_model", "gpt-image-1"), "prompt": prompt,
            "size": b.get("image_size", "1024x1024"), "n": 1})
        if st != 200:
            return {"error": f"OpenAI image {st}: {json.dumps(js)[:200]}", "got": imgs}
        d = js.get("data", [{}])[0]
        if d.get("b64_json"):
            imgs.append(base64.b64decode(d["b64_json"]))
        elif d.get("url"):
            with urllib.request.urlopen(d["url"], timeout=60, context=_CTX) as r:
                imgs.append(r.read())
    return imgs


# ---------------- Şəkil BRENDLƏMƏ (real tap.az şəklindən) ----------------
_BRANDIFY_DEFAULT = (
    "Take the product shown in this photo and present it as a clean professional e-commerce catalog image. "
    "CRITICAL: keep the EXACT same product — identical model, colour, ports, keyboard, screen content, "
    "proportions and viewing angle. Do NOT redraw, replace, restyle or invent any part of the product itself. "
    "Only replace the background and improve the presentation: pure white to soft light-blue gradient background, "
    "gentle realistic soft shadow under the product, clean soft studio lighting, generous empty space, "
    "modern minimal corporate look with subtle deep-blue (#0B3D91) / cyan (#00A3E0) accent. "
    "No text, no watermark, no logos.")


def _post_multipart(path, fields, files, timeout=180):
    """multipart/form-data POST (stdlib) — images/edits üçün."""
    boundary = "----pctech" + os.urandom(9).hex()
    buf = []
    for k, v in fields.items():
        buf.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for name, filename, data, ctype in files:
        buf.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
                   f"Content-Type: {ctype}\r\n\r\n".encode())
        buf.append(data); buf.append(b"\r\n")
    buf.append(f"--{boundary}--\r\n".encode())
    body = b"".join(buf)
    req = urllib.request.Request(OPENAI + path, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                                          "Authorization": "Bearer " + _key()})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, json.loads(r.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "ignore") or "{}")


def brandify_image(src_bytes, brand=None):
    """Real məhsul şəklini → PCTECH brendinə çevir (məhsul eyni qalır, yalnız fon/təqdimat). bytes və ya {error}."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur"}
    b = brand or load_brand()
    prompt = b.get("brandify_prompt") or _BRANDIFY_DEFAULT
    st, js = _post_multipart("/images/edits", {
        "model": b.get("image_model", "gpt-image-1"), "prompt": prompt,
        "size": b.get("image_size", "1024x1024"), "n": "1"},
        [("image", "product.png", src_bytes, "image/jpeg")])
    if st != 200:
        return {"error": f"OpenAI edit {st}: {json.dumps(js)[:200]}"}
    d = js.get("data", [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        with urllib.request.urlopen(d["url"], timeout=60, context=_CTX) as r:
            return r.read()
    return {"error": "boş cavab"}


_WHITE_PROMPT = (
    "Isolate the exact product from this photo and place it centred on a pure solid white (#FFFFFF) "
    "background. Keep the product IDENTICAL — same model, colour, angle and details. Remove ALL original "
    "background, any text, watermarks, price/credit badges, cards, banners or seller logos. Add only a soft "
    "realistic contact shadow. Clean professional e-commerce cut-out.")


def product_white(src_bytes, brand=None):
    """Real məhsul şəklini → təmiz AĞ fonda (kart montajı üçün). bytes və ya {error}."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur"}
    b = brand or load_brand()
    st, js = _post_multipart("/images/edits", {
        "model": b.get("image_model", "gpt-image-1"), "prompt": _WHITE_PROMPT,
        "size": b.get("image_size", "1024x1024"), "n": "1"},
        [("image", "product.png", src_bytes, "image/jpeg")])
    if st != 200:
        return {"error": f"OpenAI edit {st}: {json.dumps(js)[:200]}"}
    d = js.get("data", [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        with urllib.request.urlopen(d["url"], timeout=60, context=_CTX) as r:
            return r.read()
    return {"error": "boş cavab"}


def card_fields(title, body, brand=None):
    """LLM → {title, model, features[3]} — sabit-dizayn kart üçün (yalnız fakt)."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur"}
    b = brand or load_brand()
    sysmsg = (f"Sən {b['name']} üçün məhsul kartı məlumatı hazırlayırsan. Yalnız verilən mətndəki "
              f"FAKTLARdan istifadə et — heç nə uydurma.")
    user = (f"Məhsul başlığı:\n{title}\n\nTəsvir:\n{body}\n\n"
            'JSON qaytar (başqa heç nə): {"title":"qısa məhsul adı, marka+seriya, max 4 söz", '
            '"model":"model kodu — varsa; yoxsa boş sətir", '
            '"features":["3 qısa xüsusiyyət, hər biri max 3 söz, Azərbaycanca"]}. '
            'Nümunə features: ["16\\" ekran","Gaming performansı","RTX 4070"].')
    st, js = _post("/chat/completions", {
        "model": b.get("text_model", "gpt-4o"),
        "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"}, "temperature": 0.4})
    if st != 200:
        return {"error": f"OpenAI text {st}: {json.dumps(js)[:150]}"}
    try:
        o = json.loads(js["choices"][0]["message"]["content"])
        return {"title": (o.get("title") or title)[:40], "model": (o.get("model") or "")[:30],
                "features": [str(f) for f in (o.get("features") or [])][:3]}
    except Exception as e:
        return {"error": f"parse: {e}"}


def brandify_images(src_list, n=None, brand=None):
    """Real şəkilləri (draft foto bytes) PCTECH brendinə çevir → [bytes,...] və ya {error, got}."""
    if not has_key():
        return {"error": "OPENAI_API_KEY yoxdur"}
    b = brand or load_brand()
    n = n or b.get("images_per_draft", 3)
    out = []
    for src in (src_list or [])[:n]:
        r = brandify_image(src, b)
        if isinstance(r, dict) and r.get("error"):
            return {"error": r["error"], "got": out}
        out.append(r)
    return out


if __name__ == "__main__":
    print("brand:", load_brand()["name"], "| OPENAI key:", has_key())
