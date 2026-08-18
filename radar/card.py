#!/usr/bin/env python3
"""Techbar sabit-dizayn məhsul kartı — deterministik (PIL, AI YOX). Modern/professional.
Dizayn: logo (tək, yazısız) yuxarı-sol · məhsul yumşaq boz panel üzərində (kölgə) · sağ başlıq/model/
xüsusiyyət · altda mavi GÜVƏN zolağı (sayt + nömrə + zəmanət). Logo kodda çəkilir; ölçü sabit."""
import os, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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


def techbar_mark(D, color=(47, 86, 224, 255)):
    """Techbar logosu — split-dairə (üst+alt boşluqlu halqa, içi boş). Şəffaf RGBA."""
    S = D * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = S / 2
    d.ellipse([0, 0, S, S], fill=color)
    ih = 0.42 * r
    d.ellipse([r - ih, r - ih, r + ih, r + ih], fill=(0, 0, 0, 0))
    gw = 0.115 * r
    d.rectangle([r - gw, 0, r + gw, r - ih * 0.55], fill=(0, 0, 0, 0))
    d.rectangle([r - gw, r + ih * 0.55, r + gw, S], fill=(0, 0, 0, 0))
    return im.resize((D, D), Image.LANCZOS)


def _shadow(canvas, box, radius, blur=16, alpha=55, dx=6, dy=12):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy],
                                         radius=radius, fill=(20, 30, 60, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(sh, (0, 0), sh)


def _icon_kind(text):
    t = (text or "").lower()
    if any(k in t for k in ("ekran", "screen", "display", "hz", "oled", "ips", "\"", "nit")):
        return "screen"
    if any(k in t for k in ("gaming", "oyun", "game", "fps")):
        return "game"
    if any(k in t for k in ("dizayn", "möhkəm", "mohkem", "tuf", "metal", "korpus", "çəki", "yüngül")):
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


def _draw_glyph(d, kind, cx, cy, r, color):
    w = max(3, r // 8); s = r * 0.55
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
        d.line([cx - s * 0.32, cy, cx - s * 0.05, cy + s * 0.32], fill=color, width=w)
        d.line([cx - s * 0.05, cy + s * 0.32, cx + s * 0.42, cy - s * 0.28], fill=color, width=w)
    elif kind in ("cpu", "gpu"):
        d.rounded_rectangle([cx - s * 0.66, cy - s * 0.66, cx + s * 0.66, cy + s * 0.66], radius=5, outline=color, width=w)
        d.rounded_rectangle([cx - s * 0.28, cy - s * 0.28, cx + s * 0.28, cy + s * 0.28], radius=3, outline=color, width=w)
        for i in (-0.34, 0.0, 0.34):
            d.line([cx + i * s * 1.9, cy - s * 0.92, cx + i * s * 1.9, cy - s * 0.66], fill=color, width=w)
            d.line([cx + i * s * 1.9, cy + s * 0.66, cx + i * s * 1.9, cy + s * 0.92], fill=color, width=w)
    elif kind in ("ram", "ssd"):
        d.rounded_rectangle([cx - s, cy - s * 0.42, cx + s, cy + s * 0.42], radius=4, outline=color, width=w)
        for i in (-0.6, -0.2, 0.2, 0.6):
            d.line([cx + i * s, cy - s * 0.42, cx + i * s, cy + s * 0.02], fill=color, width=max(2, w - 1))
    else:
        d.line([cx - s * 0.5, cy, cx - s * 0.1, cy + s * 0.42], fill=color, width=w)
        d.line([cx - s * 0.1, cy + s * 0.42, cx + s * 0.6, cy - s * 0.38], fill=color, width=w)


def _trust_glyph(d, kind, cx, cy, r, color):
    w = max(3, r // 7); s = r * 0.72
    if kind == "globe":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=color, width=w)
        d.line([cx - s, cy, cx + s, cy], fill=color, width=max(2, w - 1))
        d.ellipse([cx - s * 0.45, cy - s, cx + s * 0.45, cy + s], outline=color, width=max(2, w - 1))
    elif kind == "phone":
        d.rounded_rectangle([cx - s * 0.55, cy - s, cx + s * 0.55, cy + s], radius=int(s * 0.3), outline=color, width=w)
        d.line([cx - s * 0.18, cy + s * 0.62, cx + s * 0.18, cy + s * 0.62], fill=color, width=w)
    else:  # check
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=color, width=w)
        d.line([cx - s * 0.42, cy + s * 0.02, cx - s * 0.1, cy + s * 0.4], fill=color, width=w)
        d.line([cx - s * 0.1, cy + s * 0.4, cx + s * 0.5, cy - s * 0.35], fill=color, width=w)


def build_card(product_img_bytes, title, model="", features=None, brand=None, size=None, category=""):
    """Sabit-dizayn modern Techbar kartı → JPEG bytes."""
    b = brand or {}
    blue = _hex(b.get("card_color") or (b.get("colors") or {}).get("primary") or "#2F56E0")
    ink = _hex((b.get("colors") or {}).get("text") or "#1A2233")
    W, H = tuple(size or b.get("card_size") or (1600, 1200))
    features = [f for f in (features or []) if f][:3]

    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)

    # ---- logo (tək, yazısız) yuxarı-sol ----
    logo_d = int(H * 0.075)
    lx, ly = int(W * 0.038), int(H * 0.045)
    logo_path = os.path.join(ROOT, b.get("logo_file", "")) if b.get("logo_file") else ""
    placed = False
    if logo_path and os.path.exists(logo_path):
        try:
            lg = _fit_contain(Image.open(logo_path), logo_d, logo_d)
            canvas.paste(lg, (lx, ly), lg); placed = True
        except Exception:
            placed = False
    if not placed:
        mark = techbar_mark(logo_d, blue + (255,))
        canvas.paste(mark, (lx, ly), mark)

    # ---- məhsul: yumşaq boz panel + kölgə ----
    pnl = [int(W * 0.032), int(H * 0.16), int(W * 0.49), int(H * 0.845)]
    _shadow(canvas, pnl, radius=30)
    d.rounded_rectangle(pnl, radius=30, fill=(243, 246, 251))
    pad = int(W * 0.025)
    try:
        prod = _fit_contain(Image.open(io.BytesIO(product_img_bytes)),
                            pnl[2] - pnl[0] - 2 * pad, pnl[3] - pnl[1] - 2 * pad)
        px = pnl[0] + ((pnl[2] - pnl[0]) - prod.width) // 2
        py = pnl[1] + ((pnl[3] - pnl[1]) - prod.height) // 2
        canvas.paste(prod, (px, py), prod)
    except Exception:
        pass

    # ---- sağ: kateqoriya + başlıq + model + xüsusiyyətlər ----
    rx = int(W * 0.535)
    rmax = W - int(W * 0.05) - rx
    y = int(H * 0.17)
    if category:
        d.text((rx, y), category.upper(), font=_font(int(H * 0.024), bold=True), fill=blue)
        y += int(H * 0.045)
    fnt_title = _font(int(H * 0.052), bold=True)
    for ln in _wrap(d, title, fnt_title, rmax):
        d.text((rx, y), ln, font=fnt_title, fill=ink)
        y += int(H * 0.06)
    if model:
        y += int(H * 0.004)
        d.text((rx, y), model, font=_font(int(H * 0.03), bold=True), fill=(120, 130, 150))
        y += int(H * 0.05)
    else:
        y += int(H * 0.012)
    d.line([rx, y, W - int(W * 0.05), y], fill=(225, 230, 240), width=3)
    y += int(H * 0.05)
    fnt_feat = _font(int(H * 0.03), bold=True)
    ir = int(H * 0.03)
    for f in features:
        cy = y + ir
        d.ellipse([rx, cy - ir, rx + 2 * ir, cy + ir], fill=(238, 242, 252))  # yumşaq mavi disk
        _draw_glyph(d, _icon_kind(f), rx + ir, cy, int(ir * 0.82), blue)
        tb = d.textbbox((0, 0), f, font=fnt_feat)
        d.text((rx + 2 * ir + int(W * 0.02), cy - (tb[3] - tb[1]) / 2 - tb[1]), f, font=fnt_feat, fill=ink)
        y += int(H * 0.115)

    # ---- alt: mavi GÜVƏN zolağı (sayt + nömrə + zəmanət) ----
    fb = [int(W * 0.032), int(H * 0.885), int(W * 0.968), int(H * 0.955)]
    _shadow(canvas, fb, radius=22, blur=12, alpha=45, dy=8)
    d.rounded_rectangle(fb, radius=22, fill=blue)
    items = [("globe", b.get("website", "techbar.az")),
             ("phone", b.get("phone", "")),
             ("check", b.get("guarantee", "Rəsmi zəmanət"))]
    items = [(k, v) for k, v in items if v]
    seg = (fb[2] - fb[0]) / len(items)
    cy = (fb[1] + fb[3]) // 2
    fnt_ft = _font(int((fb[3] - fb[1]) * 0.34), bold=True)
    for i, (kind, txt) in enumerate(items):
        segx = fb[0] + seg * i
        tw = d.textlength(txt, font=fnt_ft)
        gr = int((fb[3] - fb[1]) * 0.22)
        total = 2 * gr + int(W * 0.012) + tw
        sx = segx + (seg - total) / 2
        _trust_glyph(d, kind, sx + gr, cy, gr, (255, 255, 255))
        tb = d.textbbox((0, 0), txt, font=fnt_ft)
        d.text((sx + 2 * gr + int(W * 0.012), cy - (tb[3] - tb[1]) / 2 - tb[1]), txt, font=fnt_ft, fill="white")
        if i < len(items) - 1:
            d.line([segx + seg, fb[1] + int((fb[3] - fb[1]) * 0.22), segx + seg, fb[3] - int((fb[3] - fb[1]) * 0.22)],
                   fill=(255, 255, 255, 90), width=2)

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=92)
    return out.getvalue()


if __name__ == "__main__":
    import json
    brand = json.load(open(os.path.join(ROOT, "config", "brand.json"), encoding="utf-8"))
    img = open(os.path.join(ROOT, "out/drafts_media/1/0.jpg"), "rb").read()
    data = build_card(img, "ASUS TUF F16", "FX608JPR-RV019",
                      ["16\" ekran", "Gaming performansı", "Möhkəm TUF dizaynı"], brand,
                      category="Gaming noutbuk")
    open("/tmp/card4.jpg", "wb").write(data)
    print("card4.jpg", len(data), "bayt")
