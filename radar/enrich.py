#!/usr/bin/env python3
"""Turn a raw ad-detail record into a scored, categorized listing."""
import re
from .specs import parse_specs

CPU_SC = {'Intel Core i9': 100, 'AMD Ryzen 9': 100, 'AMD Ryzen AI 9': 98, 'AMD Ryzen AI 7': 90,
          'Apple M4': 100, 'Apple M3': 96, 'Apple M2': 92, 'Apple M1': 88,
          'Intel Core i7': 85, 'AMD Ryzen 7': 85, 'Intel Core i5': 70, 'Intel Core 5': 68,
          'AMD Ryzen 5': 68, 'Intel Core i3': 50, 'Intel Core 3': 48, 'AMD Ryzen 3': 48,
          'Qualcomm Snapdragon': 66, 'Intel N-series': 35, 'Intel Pentium': 30,
          'AMD (other)': 30, 'AMD Athlon': 28, 'Intel Celeron': 25}
RAM_SC = {2: 12, 4: 28, 6: 42, 8: 58, 12: 78, 16: 100, 24: 100, 32: 100, 36: 100, 48: 100, 64: 100}
GAMING_NAME = ['rog', 'nitro', 'legion', 'tuf', 'predator', 'victus', 'katana', 'cyborg', 'pulse',
               'omen', 'ideapad gaming', 'loq', 'zephyrus', 'strix', 'raider', 'stealth', 'vector',
               'crosshair', 'gaming', 'alienware', 'helios', 'triton', 'swift x', 'flow x']
BRAND_FIX = {'Apple Macbook': 'Apple', 'Apple MacBook': 'Apple', 'APPLE': 'Apple'}


def _stor_gb(s):
    if not s: return None
    try: n = float(s.split()[0])
    except Exception: return None
    return n * 1000 if 'TB' in s else n


def _stor_score(gb):
    if gb is None: return 0
    return 100 if gb >= 1000 else 82 if gb >= 512 else 80 if gb >= 480 else 56 if gb >= 256 else 53 if gb >= 240 else 32 if gb >= 128 else 22


def _gpu_score(g):
    if not g: return 0
    g = g.upper()
    return 100 if g.startswith('RTX') else 80 if g.startswith('GTX') else 60 if g.startswith('RX') else 40 if g.startswith('MX') else 0


def usage_label(name, gpu):
    g = (gpu or '').upper(); nm = (name or '').lower()
    if re.search(r'\b(RTX|GTX)\s?\d{3,4}', g) or re.search(r'\bMX\s?\d{3}', g) or re.search(r'\bRX\s?\d{3,4}', g):
        return 'Gaming'
    return 'Gaming' if any(k in nm for k in GAMING_NAME) else 'Ofis / Gündəlik'


def price_band(p):
    if p is None: return ''
    b = int(p // 100) * 100
    return f"{b}–{b+100}"


def _base_fields(rec, brand):
    return {
        'id': rec['id'], 'name': (rec.get('name') or '').strip(), 'brand': brand,
        'price': rec.get('price'), 'band': price_band(rec.get('price')),
        'condition': rec.get('condition') or '',
        'is_new': rec.get('is_new') or '', 'seller_type': rec.get('seller_type') or '',
        'seller': rec.get('seller') or '', 'phones': "; ".join(rec.get('phones') or []),
        'shop_url': rec.get('shop_url') or '', 'link': rec.get('link') or '',
        'region': rec.get('region') or '', 'hits': rec.get('hits'),
        'updatedAt': rec.get('updatedAt'), 'body': (rec.get('body') or '').strip(),
    }


def _brand_of(rec):
    brand = BRAND_FIX.get(rec.get('brand') or '', rec.get('brand') or '')
    if brand in ('', 'Digər', None):
        for kb in ['Gigabyte', 'MSI', 'Razer', 'Samsung', 'Microsoft', 'Chuwi', 'Kingston', 'Corsair',
                   'ADATA', 'Crucial', 'Samsung', 'WD', 'Seagate', 'AOC', 'LG', 'Dell', 'Asus', 'Acer',
                   'HP', 'Lenovo', 'Team', 'Patriot', 'Zotac', 'Palit', 'Gainward']:
            if kb.lower() in (rec.get('name') or '').lower():
                brand = kb; break
        if brand in ('', None): brand = 'Digər'
    return brand


def enrich_component_rec(rec):
    from .components import enrich_component
    brand = _brand_of(rec)
    c = enrich_component(rec.get('subcategory'), rec.get('name'), rec.get('body'), rec.get('price'))
    d = _base_fields(rec, brand)
    d.update({
        'cpu': '', 'cpu_fam': '', 'ram': None, 'storage': '', 'screen': '', 'gpu': '', 'os': '',
        'params': c['key_spec'], 'spec_score': c['spec_score'], 'value_score': c['value_score'],
        'usage': c['usage'], 'subcategory': c['sub'],
    })
    return d


def enrich(rec, category='noutbuklar'):
    """rec: raw detail from tap.fetch_detail (must be available). Returns normalized listing dict.
    `category` (slug) selects the scoring model (laptop vs desktop vs component)."""
    if category in ('komputer-avadanliqi', 'komputer-aksesuarlari', 'ofis-avadanliqi'):
        return enrich_component_rec(rec)
    s = parse_specs((rec.get('name') or '') + "\n" + (rec.get('body') or ''))
    brand = BRAND_FIX.get(rec.get('brand') or '', rec.get('brand') or '')
    if brand in ('', 'Digər', None):
        for kb in ['Gigabyte', 'MSI', 'Razer', 'Samsung', 'Microsoft', 'Chuwi', 'Realme', 'Xiaomi',
                   'Redmagic', 'Thunderobot', 'Colorful', 'Tecno', 'Infinix', 'LG', 'Fujitsu', 'Toshiba']:
            if kb.lower() in (rec.get('name') or '').lower():
                brand = kb; break
        if brand in ('', None): brand = 'Digər'
    price = rec.get('price')
    cpu = CPU_SC.get(s.get('CPU_family'), 40)
    ram = RAM_SC.get(s.get('RAM_GB'), 20 if s.get('RAM_GB') else 0)
    st = _stor_score(_stor_gb((s.get('Storage') + (f" {s['Storage_type']}" if s.get('Storage_type') else '')) if s.get('Storage') else None))
    is_new_b = (rec.get('is_new') or '').lower().startswith('b')
    has_cpu = bool(s.get('CPU_family'))  # a real computer/laptop has an identified CPU
    if category == 'komputerler':
        from .desktop import gpu_tier_score, score_desktop, form_factor
        gtier = gpu_tier_score(s.get('GPU'))
        spec = score_desktop(cpu, ram, st, gtier, is_new_b)
        usage = 'Gaming' if gtier > 0 else 'Ofis / Gündəlik'
        subcat = 'Masaüstü — ' + form_factor(rec.get('name'), rec.get('body'))
    else:
        gp = _gpu_score(s.get('GPU'))
        spec = round(0.40 * cpu + 0.28 * ram + 0.22 * st + 0.10 * gp, 1)
        if is_new_b:
            spec = round(min(100, spec + 2), 1)
        usage = usage_label(rec.get('name'), s.get('GPU'))
        subcat = rec.get('subcategory') or ''
    # value_score only for a real machine: CPU identified, above a price floor, not a rental.
    # (below-floor / rental listings get astronomically high value and pollute rankings.)
    FLOORS = {'noutbuklar': 130, 'komputerler': 150}
    floor = FLOORS.get(category, 0)
    nm = (rec.get('name') or '').lower()
    rental = ('icar' in nm or 'kiray' in nm)
    ok = bool(price and has_cpu and price >= floor and not rental)
    value = round(spec / price * 1000, 1) if ok else None
    if not ok:
        value = None
    if not has_cpu:
        spec = None
    storage = (s.get('Storage') + (f" {s['Storage_type']}" if s.get('Storage_type') else '')) if s.get('Storage') else ''
    params = " · ".join(filter(None, [
        s.get('CPU'), f"{s['RAM_GB']}GB RAM" if s.get('RAM_GB') else None,
        storage or None, f'{s["Screen"]}"' if s.get('Screen') else None, s.get('GPU'), s.get('OS')]))
    return {
        'id': rec['id'], 'name': (rec.get('name') or '').strip(), 'brand': brand,
        'price': price, 'band': price_band(price),
        'cpu': s.get('CPU') or '', 'cpu_fam': s.get('CPU_family') or '', 'ram': s.get('RAM_GB'),
        'storage': storage, 'screen': s.get('Screen') or '', 'gpu': s.get('GPU') or '', 'os': s.get('OS') or '',
        'params': params, 'spec_score': spec, 'value_score': value,
        'usage': usage,
        'condition': rec.get('condition') or '', 'subcategory': subcat,
        'is_new': rec.get('is_new') or '', 'seller_type': rec.get('seller_type') or '',
        'seller': rec.get('seller') or '', 'phones': "; ".join(rec.get('phones') or []),
        'shop_url': rec.get('shop_url') or '', 'link': rec.get('link') or '',
        'region': rec.get('region') or '', 'hits': rec.get('hits'),
        'updatedAt': rec.get('updatedAt'), 'body': (rec.get('body') or '').strip(),
    }
