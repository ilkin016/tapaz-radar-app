#!/usr/bin/env python3
"""Techbar sabit-dizayn məhsul kartı — deterministik (PIL, AI YOX).
Techbar dizaynı (Electrocomp kopyası DEYİL): yuxarı mavi başlıq zolağı + logo + ad,
sol=məhsul (tam görünən, kəsilmədən), sağ=başlıq+model+xüsusiyyət, alt mavi strip.
Logo kodda çəkilir (mavi split-dairə) — dəqiq, hər ölçüdə təmiz; ölçü sabit."""
import os, io
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_FONT_REG = ["/System/Library/Fonts/Supplemental/Arial.ttf",
             "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/Library/Fonts/Arial.ttf"]
_FONT_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _font(size, bold=False):
    for p in (_FONT_BOLD if bold else _FONT_REG):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _hex(c):
    c = (c or "#2F56E0").lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in (text or "").split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_contain(img, bw, bh):
    img = img.convert("RGBA")
    r = min(bw / img.width, bh / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)


def techbar_mark(D, color=(255, 255, 255, 255)):
    """Techbar logosu — split-dairə (üst+alt boşluqlu halqa, içi boş). Şəffaf RGBA."""
    S = D * 4  # supersample → hamar kənar
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = S / 2
    d.ellipse([0, 0, S, S], fill=color)               # xarici disk
    ih = 0.42 * r                                       # daxili deşik
    d.ellipse([r - ih, r - ih, r + ih, r + ih], fill=(0, 0, 0, 0))
    gw = 0.115 * r                                      # boşluq eni (üst+alt)
    d.rectangle([r - gw, 0, r + gw, r - ih * 0.55], fill=(0, 0, 0, 0))
    d.rectangle([r - gw, r + ih * 0.55, r + gw, S], fill=(0, 0, 0, 0))
    return im.resize((D, D), Image.LANCZOS)


def _icon_kind(text):
    t = (text or "").lower()
    if any(k in t for k in ("ekran", "screen", "display", "hz", "oled", "ips", "\"", "nit")):
        return "screen"
    if any(k in t for k in ("gaming", "oyun", "game", "fps")):
        return "game"
    if any(k in t for k in ("dizayn", "möhkəm", "mohkem", "tuf", "build", "metal", "korpus", "çəki", "yüngül")):
        return "shield"
    if any(k in t for k in ("cpu", "prosessor", "core", "ryzen", "intel", " i5", " i7", " i9", "ultra")):
        return "cpu"
    if any(k in t for k in ("ram", "ddr", "gb ram")):
        return "ram"
    if any(k in t for k in ("ssd", "nvme", "hdd", "yaddaş", "yaddas", "tb", "gb ssd")):
        return "ssd"
    if any(k in t for k in ("gpu", "video", "rtx", "gtx", "grafik", "nvidia", "radeon", "geforce")):
        return "gpu"
    return "check"


def _draw_icon(d, kind, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=max(3, r // 9))
    w = max(3, r // 9); s = r * 0.5
    if kind == "screen":
        d.rounded_rectangle([cx - s, cy - s * 0.72, cx + s, cy + s * 0.38], radius=4, outline=color, width=w)
        d.line([cx - s * 0.4, cy + s * 0.62, cx + s * 0.4, cy + s * 0.62], fill=color, width=w)
        d.line([cx, cy + s * 0.38, cx, cy + s * 0.62], fill=color, width=w)
    elif kind == "game":
        d.rounded_rectangle([cx - s, cy - s * 0.5, cx + s, cy + s * 0.5], radius=int(s * 0.5), outline=color, width=w)
        d.line([cx - s * 0.55, cy, cx - s * 0.15, cy], fill=color, width=w)
        d.line([cx - s * 0.35, cy - s * 0.2, cx - s * 0.35, cy + s * 0.2], fill=color, width=w)
        d.ellipse([cx + s * 0.22, cy - s * 0.16, cx + s * 0.44, cy + s * 0.06], fill=color)
        d.ellipse([cx + s * 0.42, cy + s * 0.02, cx + s * 0.64, cy + s * 0.24], fill=color)
    elif kind == "shield":
        d.polygon([(cx, cy - s), (cx + s * 0.85, cy - s * 0.5), (cx + s * 0.85, cy + s * 0.25),
                   (cx, cy + s), (cx - s * 0.85, cy + s * 0.25), (cx - s * 0.85, cy - s * 0.5)],
                  outline=color, width=w)
        d.line([cx - s * 0.35, cy, cx - s * 0.05, cy + s * 0.35], fill=color, width=w)
        d.line([cx - s * 0.05, cy + s * 0.35, cx + s * 0.45, cy - s * 0.3], fill=color, width=w)
    elif kind in ("cpu", "gpu"):
        d.rounded_rectangle([cx - s * 0.68, cy - s * 0.68, cx + s * 0.68, cy + s * 0.68], radius=5, outline=color, width=w)
        d.rounded_rectangle([cx - s * 0.3, cy - s * 0.3, cx + s * 0.3, cy + s * 0.3], radius=3, outline=color, width=w)
        for i in (-0.34, 0.0, 0.34):
            d.line([cx + i * s * 2, cy - s * 0.95, cx + i * s * 2, cy - s * 0.68], fill=color, width=w)
            d.line([cx + i * s * 2, cy + s * 0.68, cx + i * s * 2, cy + s * 0.95], fill=color, width=w)
    elif kind in ("ram", "ssd"):
        d.rounded_rectangle([cx - s, cy - s * 0.45, cx + s, cy + s * 0.45], radius=4, outline=color, width=w)
        for i in (-0.6, -0.2, 0.2, 0.6):
            d.line([cx + i * s, cy - s * 0.45, cx + i * s, cy + s * 0.05], fill=color, width=max(2, w - 1))
    else:
        d.line([cx - s * 0.5, cy, cx - s * 0.1, cy + s * 0.45], fill=color, width=w)
        d.line([cx - s * 0.1, cy + s * 0.45, cx + s * 0.6, cy - s * 0.4], fill=color, width=w)


def build_card(product_img_bytes, title, model="", features=None, brand=None, size=None):
    """Sabit-dizayn Techbar kartı → JPEG bytes."""
    b = brand or {}
    blue = _hex(b.get("card_color") or (b.get("colors") or {}).get("primary") or "#2F56E0")
    ink = _hex((b.get("colors") or {}).get("text") or "#1A2233")
    W, H = tuple(size or b.get("card_size") or (1600, 1200))
    name = b.get("name", "Techbar")
    features = [f for f in (features or []) if f][:3]

    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)

    # ---- yuxarı mavi başlıq zolağı ----
    hb = int(H * 0.13)
    d.rectangle([0, 0, W, hb], fill=blue)
    logo_d = int(hb * 0.62)
    lx, ly = int(W * 0.035), (hb - logo_d) // 2
    logo_path = os.path.join(ROOT, b.get("logo_file", "")) if b.get("logo_file") else ""
    if logo_path and os.path.exists(logo_path):
        try:
            lg = _fit_contain(Image.open(logo_path), logo_d, logo_d)
            canvas.paste(lg, (lx, (hb - lg.height) // 2), lg)
        except Exception:
            logo_path = ""
    if not (logo_path and os.path.exists(logo_path)):
        mark = techbar_mark(logo_d, (255, 255, 255, 255))
        canvas.paste(mark, (lx, ly), mark)
    fnt_brand = _font(int(hb * 0.42), bold=True)
    bbx = lx + logo_d + int(W * 0.02)
    bb = d.textbbox((0, 0), name, font=fnt_brand)
    d.text((bbx, (hb - (bb[3] - bb[1])) // 2 - bb[1]), name, font=fnt_brand, fill="white")
    fnt_tag = _font(int(hb * 0.2))
    tag = b.get("tagline", "")
    if tag:
        tw = d.textlength(tag, font=fnt_tag)
        d.text((W - int(W * 0.035) - tw, (hb - int(hb * 0.2)) // 2 - 2), tag, font=fnt_tag, fill=(235, 240, 255))

    # ---- alt mavi strip ----
    fb = int(H * 0.035)
    d.rectangle([0, H - fb, W, H], fill=blue)
    fnt_ft = _font(int(fb * 0.5), bold=True)
    d.text((int(W * 0.035), H - fb + (fb - int(fb * 0.5)) // 2 - 2), "techbar.az", font=fnt_ft, fill="white")

    # ---- sol: məhsul (TAM görünən, kənarlarda boşluq) ----
    m = int(W * 0.035)
    bx0, by0, bx1, by1 = m, hb + int(H * 0.05), int(W * 0.55), H - fb - int(H * 0.05)
    try:
        prod = _fit_contain(Image.open(io.BytesIO(product_img_bytes)), bx1 - bx0, by1 - by0)
        px = bx0 + ((bx1 - bx0) - prod.width) // 2
        py = by0 + ((by1 - by0) - prod.height) // 2
        canvas.paste(prod, (px, py), prod)
    except Exception:
        pass

    # ---- sağ: başlıq + model + xüsusiyyətlər ----
    rx = int(W * 0.60)
    rmax = W - int(W * 0.05) - rx
    y = hb + int(H * 0.09)
    fnt_title = _font(int(H * 0.05), bold=True)
    for ln in _wrap(d, title, fnt_title, rmax):
        d.text((rx, y), ln, font=fnt_title, fill=ink)
        y += int(H * 0.058)
    if model:
        y += int(H * 0.008)
        d.text((rx, y), model, font=_font(int(H * 0.032), bold=True), fill=blue)
        y += int(H * 0.05)
    d.line([rx, y, W - int(W * 0.05), y], fill=blue, width=max(2, W // 450))
    y += int(H * 0.05)
    fnt_feat = _font(int(H * 0.031), bold=True)
    ir = int(H * 0.032)
    for f in features:
        cy = y + ir
        _draw_icon(d, _icon_kind(f), rx + ir, cy, ir, blue)
        d.line([rx + ir * 2 + 16, cy - ir, rx + ir * 2 + 16, cy + ir], fill=blue, width=max(2, W // 500))
        tb = d.textbbox((0, 0), f, font=fnt_feat)
        d.text((rx + ir * 2 + 38, cy - (tb[3] - tb[1]) / 2 - tb[1]), f, font=fnt_feat, fill=ink)
        y += int(H * 0.12)

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=92)
    return out.getvalue()


if __name__ == "__main__":
    import json
    brand = json.load(open(os.path.join(ROOT, "config", "brand.json"), encoding="utf-8"))
    img = open(os.path.join(ROOT, "out/drafts_media/1/0.jpg"), "rb").read()
    data = build_card(img, "ASUS TUF F16", "FX608JPR-RV019",
                      ["16\" ekran", "Gaming performansı", "Möhkəm TUF dizaynı"], brand)
    open("/tmp/card2.jpg", "wb").write(data)
    print("card2.jpg", len(data), "bayt")
    techbar_mark(400, _hex(brand["card_color"]) + (255,)).save("/tmp/mark.png")
