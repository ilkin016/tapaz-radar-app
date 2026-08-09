#!/usr/bin/env python3
"""Per-subcategory parsers + value metrics for Komponentlər və monitorlar.
Convention: value_score is always 'higher = better'."""
import re
from .specs import norm
from .desktop import gpu_tier_score

CPU_TIER = {  # rough desktop CPU tier for standalone CPU listings
    'i9': 90, 'i7': 78, 'i5': 62, 'i3': 45, 'ryzen 9': 92, 'ryzen 7': 80, 'ryzen 5': 64,
    'ryzen 3': 46, 'pentium': 25, 'celeron': 20, 'xeon': 60,
}


def _gb(text, near=None):
    """Find a capacity in GB/TB. If `near` regex given, prefer numbers near it."""
    t = text
    best = None
    for m in re.finditer(r'(\d{1,4})\s*(tb|gb)\b', t, re.I):
        v = int(m.group(1)) * (1000 if m.group(2).lower() == 'tb' else 1)
        if best is None or v > best:
            best = v
    return best


def parse_storage(name, body):
    t = norm(name + " " + body)
    cap = _gb(t)
    typ = 'SSD' if re.search(r'\bssd\b|nvme|m\.?2', t, re.I) else ('HDD' if re.search(r'\bhdd\b|hard\s*disk', t, re.I) else '')
    label = (f"{cap} GB" if cap and cap < 1000 else f"{cap//1000} TB" if cap else "") + (f" {typ}" if typ else "")
    return {'capacity_gb': cap, 'type': typ, 'label': label.strip()}


def parse_ram(name, body):
    t = norm(name + " " + body)
    cap = None
    m = re.search(r'(\d{1,3})\s*gb', t, re.I)
    if m: cap = int(m.group(1))
    ddr = None
    m = re.search(r'\b(ddr[2345])\b', t, re.I)
    if m: ddr = m.group(1).upper()
    elif re.search(r'\blpddr5', t, re.I): ddr = 'LPDDR5'
    speed = None
    m = re.search(r'(\d{4,5})\s*mhz', t, re.I)
    if m: speed = int(m.group(1))
    label = " ".join(filter(None, [f"{cap} GB" if cap else None, ddr, f"{speed}MHz" if speed else None]))
    return {'capacity_gb': cap, 'ddr': ddr, 'speed': speed, 'label': label}


def parse_monitor(name, body):
    t = norm(name + " " + body)
    size = None
    m = re.search(r'\b(\d{2})(?:[.,]\d)?\s*(?:"|”|inch|düym|d[üu]ym)', t, re.I)
    if m: size = int(m.group(1))
    if not size:
        m = re.search(r'\b(2[0-9]|3[0-9]|1[5-9])\s*(?:lik|lük)\b', t, re.I)
        if m: size = int(m.group(1))
    hz = None
    m = re.search(r'(\d{2,3})\s*hz', t, re.I)
    if m: hz = int(m.group(1))
    res = None
    if re.search(r'\b(4k|3840)\b', t, re.I): res = '4K'
    elif re.search(r'\b(2k|1440p|2560)\b', t, re.I): res = '2K'
    elif re.search(r'\b(full\s*hd|1080p?|1920)\b', t, re.I): res = 'FHD'
    elif re.search(r'\b(hd|1366|1280)\b', t, re.I): res = 'HD'
    panel = None
    for p in ('ips', 'va', 'tn', 'oled', 'qled'):
        if re.search(r'\b' + p + r'\b', t, re.I): panel = p.upper(); break
    curved = bool(re.search(r'curved|əyri', t, re.I))
    label = " · ".join(filter(None, [f'{size}"' if size else None, f"{hz}Hz" if hz else None, res, panel, "Curved" if curved else None]))
    return {'size': size, 'hz': hz, 'res': res, 'panel': panel, 'curved': curved, 'label': label}


def parse_cpu_component(name, body):
    t = norm(name + " " + body).lower()
    tier = 40
    for k, v in CPU_TIER.items():
        if k in t: tier = max(tier, v)
    m = re.search(r'(ryzen\s*[3579]|i[3579])[\s-]*([a-z0-9]{3,6})?', t, re.I)
    label = m.group(0).strip().title() if m else (name or '')[:30]
    return {'tier': tier, 'label': label}


def enrich_component(subcategory, name, body, price):
    """Return dict: {sub, key_spec, params, spec_score, value_score, usage}."""
    sc = subcategory or ''
    p = price or 0
    out = {'sub': sc, 'key_spec': '', 'spec_score': None, 'value_score': None, 'usage': 'Komponent'}

    if 'Sərt disk' in sc or 'HDD' in sc or 'SSD' in sc:
        d = parse_storage(name, body)
        out['key_spec'] = d['label']
        if d['capacity_gb'] and p:
            # value = GB per 100 AZN (higher = better), SSD bonus
            out['value_score'] = round(d['capacity_gb'] / p * 100 * (1.0 if d['type'] == 'SSD' else 0.7), 1)
            out['spec_score'] = d['capacity_gb']
        out['sub'] = 'Sərt disk (SSD/HDD)'
    elif 'Operativ' in sc or 'RAM' in sc:
        d = parse_ram(name, body)
        out['key_spec'] = d['label']
        if d['capacity_gb'] and p:
            ddr_bonus = {'DDR5': 1.15, 'DDR4': 1.0, 'DDR3': 0.7, 'DDR2': 0.5}.get(d['ddr'], 1.0)
            out['value_score'] = round(d['capacity_gb'] / p * 100 * ddr_bonus, 1)
            out['spec_score'] = d['capacity_gb']
        out['sub'] = 'RAM'
    elif 'Monitor' in sc or 'ekran' in sc.lower():
        d = parse_monitor(name, body)
        out['key_spec'] = d['label']
        if p and (d['size'] or d['hz']):
            res_sc = {'4K': 40, '2K': 28, 'FHD': 18, 'HD': 8}.get(d['res'], 10)
            spec = (d['size'] or 22) * 2 + (d['hz'] or 60) * 0.25 + res_sc + (10 if d['curved'] else 0)
            out['spec_score'] = round(spec, 1)
            out['value_score'] = round(spec / p * 100, 1)
        out['sub'] = 'Monitor'
    elif 'Video' in sc or 'GPU' in sc:
        gt = gpu_tier_score(_extract_gpu(name + " " + body))
        out['key_spec'] = _extract_gpu(name + " " + body) or ''
        if gt and p:
            out['spec_score'] = gt
            out['value_score'] = round(gt / p * 1000, 1)
        out['sub'] = 'Video kart (GPU)'
        out['usage'] = 'Gaming'
    elif 'Prosessor' in sc or 'CPU' in sc:
        d = parse_cpu_component(name, body)
        out['key_spec'] = d['label']
        if p:
            out['spec_score'] = d['tier']
            out['value_score'] = round(d['tier'] / p * 1000, 1)
        out['sub'] = 'CPU'
    elif 'Ana plata' in sc:
        out['sub'] = 'Ana plata'
        m = re.search(r'\b(lga\s*\d{3,4}|am[45]|b\d{3}|z\d{3}|h\d{3}|x\d{3})\b', norm(name + " " + body), re.I)
        out['key_spec'] = (m.group(0).upper() if m else '')
    else:
        out['sub'] = sc or 'Digər komponent'
    # sanity guards: drop implausible values (mis-parse / multi-item listings) + price floors
    FLOOR = {'Sərt disk (SSD/HDD)': 12, 'RAM': 10, 'Monitor': 20, 'Video kart (GPU)': 40, 'CPU': 30}
    VMAX = {'Sərt disk (SSD/HDD)': 1200, 'RAM': 1000, 'Monitor': 300, 'Video kart (GPU)': 700, 'CPU': 400}
    if out['value_score'] is not None:
        if p < FLOOR.get(out['sub'], 8) or out['value_score'] > VMAX.get(out['sub'], 5000):
            out['value_score'] = None
            out['spec_score'] = None
    return out


def _extract_gpu(text):
    t = norm(text)
    m = re.search(r'(rtx|gtx|rx)\s*(\d{3,4})\s*(ti)?', t, re.I)
    if m: return f"{m.group(1).upper()} {m.group(2)}" + (" Ti" if m.group(3) else "")
    m = re.search(r'(?:video\s*kart|geforce|nvidia|radeon)[^0-9]{0,10}(\d{3,4})\s*(ti)?', t, re.I)
    if m: return ("GTX " if int(m.group(1)) < 2000 else "RTX ") + m.group(1) + (" Ti" if m.group(2) else "")
    return None
