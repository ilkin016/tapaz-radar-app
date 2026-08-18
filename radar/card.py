#!/usr/bin/env python3
"""Techbar sabit-dizayn məhsul kartı — deterministik (PIL, AI YOX).
Layout (nümunəyə uyğun): yuxarı=logo+brend adı+ayırıcı xətlər · sol=məhsul şəkli ·
sağ=başlıq+model+xüsusiyyətlər · brend rəngli haşiyə.
Logo dəqiq (real asset), ölçü sabit — AI ilə mümkün olmayan dəqiqlik burada təmin olunur."""
import os, io, math
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_FONT_REG = ["/System/Library/Fonts/Supplemental/Arial.ttf",
             "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
             "/Library/Fonts/Arial.ttf"]
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
    c = (c or "#1FA84A").lstrip("#")
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


def _icon_kind(text):
    t = (text or "").lower()
    if any(k in t for k in ("ekran", "screen", "display", "hz", "oled", "ips", "\"")):
        return "screen"
    if any(k in t for k in ("gaming", "oyun", "game", "fps")):
        return "game"
    if any(k in t for k in ("dizayn", "möhkəm", "mohkem", "tuf", "rog", "build", "metal", "korpus")):
        return "shield"
    if any(k in t for k in ("cpu", "prosessor", "core", "ryzen", "intel", "i5", "i7", "i9")):
        return "cpu"
    if any(k in t for k in ("ram", "yaddaş", "yaddas", "gb ", "ddr")):
        return "ram"
    if any(k in t for k in ("ssd", "nvme", "hdd", "tb")):
        return "ssd"
    if any(k in t for k in ("gpu", "video", "rtx", "gtx", "grafik", "nvidia", "radeon")):
        return "gpu"
    return "check"


def _draw_icon(d, kind, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=max(3, r // 9))
    w = max(3, r // 9)
    s = r * 0.52
    if kind == "screen":
        d.rounded_rectangle([cx - s, cy - s * 0.72, cx + s, cy + s * 0.38], radius=4, outline=color, width=w)
        d.line([cx - s * 0.4, cy + s * 0.62, cx + s * 0.4, cy + s * 0.62], fill=color, width=w)
        d.line([cx, cy + s * 0.38, cx, cy + s * 0.62], fill=color, width=w)
    elif kind == "game":
        d.rounded_rectangle([cx - s, cy - s * 0.5, cx + s, cy + s * 0.5], radius=int(s * 0.5), outline=color, width=w)
        d.line([cx - s * 0.55, cy - s * 0.05, cx - s * 0.15, cy - s * 0.05], fill=color, width=w)
        d.line([cx - s * 0.35, cy - s * 0.25, cx - s * 0.35, cy + s * 0.15], fill=color, width=w)
        d.ellipse([cx + s * 0.2, cy - s * 0.18, cx + s * 0.44, cy + s * 0.06], fill=color)
        d.ellipse([cx + s * 0.42, cy + s * 0.02, cx + s * 0.66, cy + s * 0.26], fill=color)
    elif kind == "shield":
        d.polygon([(cx, cy - s), (cx + s * 0.85, cy - s * 0.5), (cx + s * 0.85, cy + s * 0.25),
                   (cx, cy + s), (cx - s * 0.85, cy + s * 0.25), (cx - s * 0.85, cy - s * 0.5)],
                  outline=color, width=w)
        d.line([cx - s * 0.35, cy, cx - s * 0.05, cy + s * 0.35], fill=color, width=w)
        d.line([cx - s * 0.05, cy + s * 0.35, cx + s * 0.45, cy - s * 0.3], fill=color, width=w)
    elif kind in ("cpu", "gpu"):
        d.rounded_rectangle([cx - s * 0.7, cy - s * 0.7, cx + s * 0.7, cy + s * 0.7], radius=6, outline=color, width=w)
        d.rounded_rectangle([cx - s * 0.32, cy - s * 0.32, cx + s * 0.32, cy + s * 0.32], radius=3, outline=color, width=w)
        for i in (-0.35, 0.0, 0.35):
            d.line([cx + i * s * 2, cy - s * 0.95, cx + i * s * 2, cy - s * 0.7], fill=color, width=w)
            d.line([cx + i * s * 2, cy + s * 0.7, cx + i * s * 2, cy + s * 0.95], fill=color, width=w)
    elif kind in ("ram", "ssd"):
        d.rounded_rectangle([cx - s, cy - s * 0.45, cx + s, cy + s * 0.45], radius=4, outline=color, width=w)
        for i in (-0.6, -0.2, 0.2, 0.6):
            d.line([cx + i * s, cy - s * 0.45, cx + i * s, cy + s * 0.1], fill=color, width=max(2, w - 1))
    else:  # check
        d.line([cx - s * 0.5, cy, cx - s * 0.1, cy + s * 0.45], fill=color, width=w)
        d.line([cx - s * 0.1, cy + s * 0.45, cx + s * 0.6, cy - s * 0.4], fill=color, width=w)


def build_card(product_img_bytes, title, model="", features=None, brand=None, size=None):
    """Sabit-dizayn Techbar kartı → JPEG bytes."""
    b = brand or {}
    accent = _hex(b.get("card_color") or (b.get("colors") or {}).get("primary") or "#1FA84A")
    ink = _hex((b.get("colors") or {}).get("text") or "#1A2233")
    W, H = tuple(size or b.get("card_size") or (1600, 1200))
    name = b.get("name", "Techbar")
    features = [f for f in (features or []) if f][:3]

    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)

    # haşiyə
    pad = int(W * 0.012)
    d.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(W * 0.02), outline=accent, width=max(4, W // 260))

    # ---- başlıq: logo (sol) + brend adı (mərkəz) + ayırıcı xətlər ----
    hy = int(H * 0.085)  # başlıq mərkəzi
    logo_box = int(H * 0.085)
    lx, ly = int(W * 0.045), hy - logo_box // 2
    logo_path = os.path.join(ROOT, b.get("logo_file", "")) if b.get("logo_file") else ""
    if logo_path and os.path.exists(logo_path):
        try:
            lg = _fit_contain(Image.open(logo_path), logo_box, logo_box)
            canvas.paste(lg, (lx, hy - lg.height // 2), lg)
        except Exception:
            logo_path = ""
    if not (logo_path and os.path.exists(logo_path)):
        # placeholder: brend rəngli altıbucaq + baş hərf
        r = logo_box // 2
        cx, cy = lx + r, hy
        pts = [(cx + r * math.cos(a), cy + r * math.sin(a))
               for a in [math.radians(60 * i - 30) for i in range(6)]]
        d.polygon(pts, fill=accent)
        fi = _font(int(logo_box * 0.5), bold=True)
        bb = d.textbbox((0, 0), name[0].upper(), font=fi)
        d.text((cx - (bb[2] - bb[0]) / 2, cy - (bb[3] - bb[1]) / 2 - bb[1]), name[0].upper(), font=fi, fill="white")

    fnt_brand = _font(int(H * 0.055), bold=True)
    bw = d.textlength(name, font=fnt_brand)
    bx = (W - bw) / 2
    bb = d.textbbox((0, 0), name, font=fnt_brand)
    d.text((bx, hy - (bb[3] - bb[1]) / 2 - bb[1]), name, font=fnt_brand, fill=ink)
    lwd = max(2, W // 500)
    d.line([lx + logo_box + int(W * 0.02), hy, bx - int(W * 0.02), hy], fill=accent, width=lwd)
    d.line([bx + bw + int(W * 0.02), hy, W - int(W * 0.05), hy], fill=accent, width=lwd)

    # ---- sol: məhsul şəkli ----
    lm = int(W * 0.03)
    lbx0, lby0, lbx1, lby1 = lm, int(H * 0.17), int(W * 0.57), int(H * 0.93)
    try:
        prod = _fit_contain(Image.open(io.BytesIO(product_img_bytes)), lbx1 - lbx0, lby1 - lby0)
        px = lbx0 + ((lbx1 - lbx0) - prod.width) // 2
        py = lby0 + ((lby1 - lby0) - prod.height) // 2
        canvas.paste(prod, (px, py), prod)
    except Exception:
        pass

    # ---- sağ: başlıq + model + xüsusiyyətlər ----
    rx = int(W * 0.61)
    rmax = W - int(W * 0.05) - rx
    y = int(H * 0.24)
    fnt_title = _font(int(H * 0.052), bold=True)
    for ln in _wrap(d, title, fnt_title, rmax):
        d.text((rx, y), ln, font=fnt_title, fill=ink)
        y += int(H * 0.06)
    if model:
        y += int(H * 0.01)
        fnt_model = _font(int(H * 0.034), bold=True)
        d.text((rx, y), model, font=fnt_model, fill=accent)
        y += int(H * 0.055)
    # ayırıcı
    d.line([rx, y, W - int(W * 0.05), y], fill=accent, width=max(2, W // 450))
    y += int(H * 0.05)
    # xüsusiyyətlər
    fnt_feat = _font(int(H * 0.032), bold=True)
    ir = int(H * 0.033)
    row_h = int(H * 0.12)
    for f in features:
        cy = y + ir
        _draw_icon(d, _icon_kind(f), rx + ir, cy, ir, accent)
        d.line([rx + ir * 2 + 14, cy - ir, rx + ir * 2 + 14, cy + ir], fill=accent, width=max(2, W // 500))
        tb = d.textbbox((0, 0), f, font=fnt_feat)
        d.text((rx + ir * 2 + 36, cy - (tb[3] - tb[1]) / 2 - tb[1]), f, font=fnt_feat, fill=ink)
        y += row_h

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=92)
    return out.getvalue()


if __name__ == "__main__":
    import json
    brand = json.load(open(os.path.join(ROOT, "config", "brand.json"), encoding="utf-8"))
    img = open(os.path.join(ROOT, "out/drafts_media/1/ai_0.jpg"), "rb").read()
    data = build_card(img, "ASUS TUF F16", "FX608JPR-RV019",
                      ["16\" ekran", "Gaming performansı", "Möhkəm TUF dizaynı"], brand)
    open("/tmp/card_sample.jpg", "wb").write(data)
    print("card_sample.jpg", len(data), "bayt")
