#!/usr/bin/env python3
"""Techbar sabit-dizayn məhsul kartı — deterministik (PIL, AI YOX). Sadə: ağ fon + çərçivə.
Logo (tək) yuxarı-sol · sol=məhsul (təmiz, kəsilmədən) · sağ=başlıq/model/xüsusiyyət ·
altda incə əlaqə sətri · qıraqlardan mavi çərçivə. Logo faylı varsa (config/techbar_logo.png) real,
yoxsa kodda çəkilir; ölçü sabit."""
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
    w = max(2, r // 6); s = r * 0.72
    if kind == "globe":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=color, width=w)
        d.line([cx - s, cy, cx + s, cy], fill=color, width=max(2, w - 1))
        d.ellipse([cx - s * 0.45, cy - s, cx + s * 0.45, cy + s], outline=color, width=max(2, w - 1))
    elif kind == "phone":
        d.rounded_rectangle([cx - s * 0.55, cy - s, cx + s * 0.55, cy + s], radius=int(s * 0.3), outline=color, width=w)
        d.line([cx - s * 0.16, cy + s * 0.62, cx + s * 0.16, cy + s * 0.62], fill=color, width=w)
    else:
        d.line([cx - s * 0.42, cy + s * 0.02, cx - s * 0.1, cy + s * 0.4], fill=color, width=w)
        d.line([cx - s * 0.1, cy + s * 0.4, cx + s * 0.5, cy - s * 0.35], fill=color, width=w)


def _chip_badge(d, cx, cy, s, color):
    """Mikroçip (IT ikonu) — badge içində. cx,cy mərkəz; s çip yarım-ölçüsü."""
    w = max(3, int(s / 4.5))
    d.rounded_rectangle([cx - s, cy - s, cx + s, cy + s], radius=int(s * 0.28), outline=color, width=w)
    d.rounded_rectangle([cx - s * 0.4, cy - s * 0.4, cx + s * 0.4, cy + s * 0.4], radius=int(s * 0.18),
                        outline=color, width=max(2, w - 1))
    pl = s * 0.45
    for i in (-0.5, 0.0, 0.5):
        off = i * s * 1.4
        d.line([cx + off, cy - s - pl, cx + off, cy - s], fill=color, width=w)
        d.line([cx + off, cy + s, cx + off, cy + s + pl], fill=color, width=w)
        d.line([cx - s - pl, cy + off, cx - s, cy + off], fill=color, width=w)
        d.line([cx + s, cy + off, cx + s + pl, cy + off], fill=color, width=w)


IT_ICONS = ["chip", "monitor", "code", "laptop", "power", "headset", "gear", "cloud"]


def _it_glyph(d, kind, cx, cy, s, color):
    """Yuxarı-sağ badge üçün seçilə bilən IT ikonları (ağ, mavi badge üstündə)."""
    w = max(3, int(s / 4.2))
    if kind == "monitor":
        d.rounded_rectangle([cx - s, cy - s * 0.82, cx + s, cy + s * 0.35], radius=int(s * 0.14), outline=color, width=w)
        d.line([cx - s * 0.42, cy + s * 0.72, cx + s * 0.42, cy + s * 0.72], fill=color, width=w)
        d.line([cx, cy + s * 0.35, cx, cy + s * 0.72], fill=color, width=w)
    elif kind == "code":
        d.line([(cx - s * 0.28, cy - s * 0.55), (cx - s * 0.82, cy), (cx - s * 0.28, cy + s * 0.55)], fill=color, width=w, joint="curve")
        d.line([(cx + s * 0.28, cy - s * 0.55), (cx + s * 0.82, cy), (cx + s * 0.28, cy + s * 0.55)], fill=color, width=w, joint="curve")
        d.line([cx + s * 0.14, cy - s * 0.62, cx - s * 0.14, cy + s * 0.62], fill=color, width=w)
    elif kind == "laptop":
        d.rounded_rectangle([cx - s * 0.62, cy - s * 0.6, cx + s * 0.62, cy + s * 0.18], radius=4, outline=color, width=w)
        d.line([cx - s * 0.92, cy + s * 0.52, cx + s * 0.92, cy + s * 0.52], fill=color, width=w)
        d.line([cx - s * 0.62, cy + s * 0.18, cx - s * 0.92, cy + s * 0.52], fill=color, width=w)
        d.line([cx + s * 0.62, cy + s * 0.18, cx + s * 0.92, cy + s * 0.52], fill=color, width=w)
    elif kind == "power":
        d.arc([cx - s * 0.62, cy - s * 0.52, cx + s * 0.62, cy + s * 0.72], start=305, end=235, fill=color, width=w)
        d.line([cx, cy - s * 0.72, cx, cy - s * 0.02], fill=color, width=w)
    elif kind == "headset":
        d.arc([cx - s * 0.62, cy - s * 0.55, cx + s * 0.62, cy + s * 0.55], start=180, end=360, fill=color, width=w)
        d.rounded_rectangle([cx - s * 0.76, cy - s * 0.02, cx - s * 0.42, cy + s * 0.58], radius=5, fill=color)
        d.rounded_rectangle([cx + s * 0.42, cy - s * 0.02, cx + s * 0.76, cy + s * 0.58], radius=5, fill=color)
    elif kind == "gear":
        import math
        d.ellipse([cx - s * 0.62, cy - s * 0.62, cx + s * 0.62, cy + s * 0.62], outline=color, width=w)
        d.ellipse([cx - s * 0.22, cy - s * 0.22, cx + s * 0.22, cy + s * 0.22], outline=color, width=w)
        for k in range(8):
            a = k * math.pi / 4
            d.line([cx + math.cos(a) * s * 0.62, cy + math.sin(a) * s * 0.62,
                    cx + math.cos(a) * s * 0.92, cy + math.sin(a) * s * 0.92], fill=color, width=w)
    elif kind == "cloud":
        d.ellipse([cx - s * 0.85, cy - s * 0.1, cx - s * 0.2, cy + s * 0.5], outline=color, width=w)
        d.ellipse([cx - s * 0.35, cy - s * 0.55, cx + s * 0.4, cy + s * 0.35], outline=color, width=w)
        d.ellipse([cx + s * 0.15, cy - s * 0.15, cx + s * 0.85, cy + s * 0.5], outline=color, width=w)
        d.rectangle([cx - s * 0.55, cy + s * 0.3, cx + s * 0.55, cy + s * 0.52], fill=color)
    else:  # "chip" (default)
        _chip_badge(d, cx, cy, s, color)


def _promo_badge(d, text, pos, W, H, pad, inl, inr, color):
    """Promo pill (məs '24 ayadək kredit və taksit') — mövqe: top-left/top-center/top-right."""
    f = _font(int(H * 0.026), bold=True)
    padx = int(W * 0.016); h = int(H * 0.052)
    tw = d.textlength(text, font=f); w = int(tw + 2 * padx)
    y = pad + int(H * 0.035)
    x = inr - w if pos == "top-right" else (int((W - w) / 2) if pos == "top-center" else inl)
    d.rounded_rectangle([x, y, x + w, y + h], radius=int(h / 2), fill=color)
    tb = d.textbbox((0, 0), text, font=f)
    d.text((x + padx, y + (h - (tb[3] - tb[1])) / 2 - tb[1]), text, font=f, fill="white")


def build_card(product_img_bytes, title, model="", features=None, brand=None, size=None, category=""):
    """Sadə ağ fon + çərçivə: PCTECH məhsul kartı → JPEG bytes."""
    b = brand or {}
    blue = _hex(b.get("card_color") or (b.get("colors") or {}).get("primary") or "#2F56E0")
    ink = _hex((b.get("colors") or {}).get("text") or "#1A2233")
    W, H = tuple(size or b.get("card_size") or (1600, 1200))
    features = [f for f in (features or []) if f][:5]

    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)

    # ---- qıraqlardan çərçivə ----
    pad = int(W * 0.016)
    d.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(W * 0.018), outline=blue, width=max(4, W // 300))

    inl = pad + int(W * 0.028)   # daxili sol
    inr = W - pad - int(W * 0.028)

    # ---- yuxarı: yüklənmiş logo / IT ikon (card_icon != none) ----
    clogo = b.get("card_logo")
    clogo_path = os.path.join(ROOT, clogo) if clogo else ""
    used_logo = False
    if clogo_path and os.path.exists(clogo_path):
        try:
            lg = _fit_contain(Image.open(clogo_path), int(W * 0.17), int(H * 0.10))
            canvas.paste(lg, (inr - lg.width, pad + int(H * 0.04)), lg); used_logo = True
        except Exception:
            used_logo = False
    icon = b.get("card_icon", "none")
    if not used_logo and icon and icon != "none":
        bsz = int(H * 0.085)
        bx, by = inr - bsz, pad + int(H * 0.045)
        d.rounded_rectangle([bx, by, bx + bsz, by + bsz], radius=int(bsz * 0.24), fill=blue)
        _it_glyph(d, icon, bx + bsz / 2, by + bsz / 2, bsz * 0.26, (255, 255, 255))
    # ---- promo badge (24 ayadək kredit və taksit) — mövqe dəyişilə bilər ----
    promo = b.get("card_badge", ""); ppos = b.get("card_badge_pos", "none")
    if promo and ppos != "none":
        _promo_badge(d, promo, ppos, W, H, pad, inl, inr, blue)

    # ---- sol: məhsul (təmiz ağ fonda, kəsilmədən) ----
    bx0, by0, bx1, by1 = inl, int(H * 0.17), int(W * 0.50), int(H * 0.82)
    try:
        prod = _fit_contain(Image.open(io.BytesIO(product_img_bytes)), bx1 - bx0, by1 - by0)
        canvas.paste(prod, (bx0 + ((bx1 - bx0) - prod.width) // 2, by0 + ((by1 - by0) - prod.height) // 2), prod)
    except Exception:
        pass

    # ---- sağ: kateqoriya + başlıq + model + xüsusiyyət (KOMPAKT, şaquli mərkəz) ----
    rx = int(W * 0.55); rmax = inr - rx
    fnt_title = _font(int(H * 0.05), bold=True)
    tlines = _wrap(d, title, fnt_title, rmax)
    n = max(1, len(features))
    row_h = int(H * 0.086)                       # kompakt sabit aralıq
    ir = int(H * 0.027) if n >= 4 else int(H * 0.030)
    fnt_feat = _font(int(H * 0.027) if n >= 4 else int(H * 0.031), bold=True)
    # blok hündürlüyünü ölç → bütün sağ blok şaquli mərkəzdə
    blk = (int(H * 0.045) if category else 0) + len(tlines) * int(H * 0.058)
    blk += (int(H * 0.004) + int(H * 0.05)) if model else int(H * 0.012)
    blk += int(H * 0.038) + n * row_h
    top_a, bot_a = pad + int(H * 0.07), H - pad - int(H * 0.085)
    y = int(top_a + max(0, (bot_a - top_a - blk) / 2))
    if category:
        d.text((rx, y), category.upper(), font=_font(int(H * 0.024), bold=True), fill=blue); y += int(H * 0.045)
    for ln in tlines:
        d.text((rx, y), ln, font=fnt_title, fill=ink); y += int(H * 0.058)
    if model:
        y += int(H * 0.004)
        d.text((rx, y), model, font=_font(int(H * 0.03), bold=True), fill=(120, 130, 150)); y += int(H * 0.05)
    else:
        y += int(H * 0.012)
    d.line([rx, y, inr, y], fill=(226, 231, 241), width=3); y += int(H * 0.038)
    tx = rx + 2 * ir + int(W * 0.016)
    for i, f in enumerate(features):
        cy = int(y + row_h * i + row_h / 2)
        d.ellipse([rx, cy - ir, rx + 2 * ir, cy + ir], fill=(238, 242, 252))
        _draw_glyph(d, _icon_kind(f), rx + ir, cy, int(ir * 0.82), blue)
        tb = d.textbbox((0, 0), f, font=fnt_feat)
        d.text((tx, cy - (tb[3] - tb[1]) / 2 - tb[1]), f, font=fnt_feat, fill=ink)

    # ---- altda: PCTECH + nömrə + zəmanət (SAYT YOX) ----
    items = [("brand", b.get("name", "PCTECH")), ("phone", b.get("phone", "")), ("check", b.get("guarantee", ""))]
    items = [(k, v) for k, v in items if v]
    if items:
        fnt_c = _font(int(H * 0.028), bold=True)
        fnt_b = _font(int(H * 0.036), bold=True)  # brend adı bir az böyük
        gr = int(H * 0.016); gap = int(W * 0.038); icon_gap = int(W * 0.008)
        def _segw(k, v):
            return d.textlength(v, font=fnt_b) if k == "brand" else 2 * gr + icon_gap + d.textlength(v, font=fnt_c)
        widths = [_segw(k, v) for k, v in items]
        total = sum(widths) + gap * (len(items) - 1)
        x = (W - total) / 2
        cy = H - pad - int(H * 0.045)
        for (k, v), wseg in zip(items, widths):
            if k == "brand":
                tb = d.textbbox((0, 0), v, font=fnt_b)
                d.text((x, cy - (tb[3] - tb[1]) / 2 - tb[1]), v, font=fnt_b, fill=blue)
            else:
                _trust_glyph(d, k, x + gr, cy, gr, blue)
                tb = d.textbbox((0, 0), v, font=fnt_c)
                d.text((x + 2 * gr + icon_gap, cy - (tb[3] - tb[1]) / 2 - tb[1]), v, font=fnt_c, fill=blue)
            x += wseg + gap

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=92)
    return out.getvalue()


if __name__ == "__main__":
    import json
    brand = json.load(open(os.path.join(ROOT, "config", "brand.json"), encoding="utf-8"))
    img = open("/private/tmp/claude-501/-Users-ilkin-Desktop-tapaz-link-/8baf30f2-117b-4934-a896-67bfc37e5cb8/scratchpad/clean_prod.png", "rb").read()
    data = build_card(img, "ASUS ROG Strix G16", "FX608JPR-RV019",
                      ["16\" ekran", "Core i9 prosessor", "RTX 4080"], brand, category="Gaming noutbuk")
    open("/tmp/card_simple.jpg", "wb").write(data)
    print("card_simple.jpg", len(data), "bayt")
