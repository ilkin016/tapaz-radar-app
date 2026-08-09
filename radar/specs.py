import re, json
RAMSET = {2,3,4,6,8,12,16,24,32,36,48,64}

def norm(t):
    if not t: return ""
    # Azerbaijani/Turkish dotted-I normalization (İ -> I, ı -> i, strip combining dot)
    t = t.replace('İ','I').replace('ı','i').replace('̇','')
    t = re.sub(r'\((?:tm|r|c)\)',' ',t,flags=re.I)  # strip (TM)/(R)/(C)
    for ch in ['‑','‒','–','—','−']:
        t = t.replace(ch,'-')
    for ch in ['™','®','­','️','​','‌','‍','⁠',' ']:
        t = t.replace(ch,' ')
    return t

def parse_specs(body_raw):
    t = norm(body_raw)
    low = t.lower()
    out = {}
    cpu=None; fam=None
    # Intel Core i-series (i3/i5/i7/i9); model may start with N
    m = re.search(r'core\s*(i[3579])\s*-?\s*(N?\d{3,5}[A-Za-z]{0,2})', t, re.I)
    if not m:
        m = re.search(r'\b(i[3579])\s*-\s*(N?\d{3,5}[A-Za-z]{0,2})\b', t, re.I)
    if not m:
        m = re.search(r'\b(i[3579])\s+(\d{4,5}[A-Za-z]{1,2})\b', t, re.I)
    if m:
        cpu=f"Core {m.group(1).lower()}-{m.group(2).upper()}"; fam=f"Intel Core {m.group(1).lower()}"
    # Intel Core (new Series-1: "Core 3/5/7 100U", "Core 3 N355", "Core Ultra 5 125H")
    if not cpu:
        m = re.search(r'\bcore\s*(?:ultra\s*)*([3579])\s*(?:processor\s*)?(?:u[3579]\s*-\s*)?-?\s*(N?\d{3,4}[A-Za-z]{0,2})\b', t, re.I)
        if m:
            cpu=f"Core {m.group(1)} {m.group(2).upper()}"; fam=f"Intel Core {m.group(1)}"
    # Intel bare new-series: "Intel 3 100U", "Intel Processor 3 100U", "Intel Core 3 Processor 100U"
    if not cpu:
        m = re.search(r'\bintel\b[^\w]{0,3}(?:core[^\w]{0,3})?(?:processor[^\w]{0,3})?([357])[^\w]{0,3}(?:processor[^\w]{0,3})?(N?\d{3,4}[A-Za-z]{0,2})\b', t, re.I)
        if m:
            cpu=f"Core {m.group(1)} {m.group(2).upper()}"; fam=f"Intel Core {m.group(1)}"
    # AMD Ryzen AI (e.g. "Ryzen AI 7 350", "Ryzen AI 9 365")
    if not cpu:
        m = re.search(r'ryzen\s*ai\s*(?:max\s*\+?\s*)?([3579])\s*(\d{3})', t, re.I)
        if m:
            cpu=f"Ryzen AI {m.group(1)} {m.group(2)}"; fam=f"AMD Ryzen AI {m.group(1)}"
    # AMD Ryzen
    if not cpu:
        m = re.search(r'ryzen[^\w]{0,3}([3579])[^\w]{0,3}(\d{3,4}[A-Za-z]{0,2})', t, re.I)
        if m:
            cpu=f"Ryzen {m.group(1)} {m.group(2).upper()}"; fam=f"AMD Ryzen {m.group(1)}"
    if not cpu:
        m = re.search(r'ryzen[^\w]{0,3}([3579])\b', t, re.I)
        if m:
            cpu=f"Ryzen {m.group(1)}"; fam=f"AMD Ryzen {m.group(1)}"
    # AMD bare (e.g. "AMD 3020e", "Athlon Silver 3050U")
    if not cpu:
        m = re.search(r'\bamd\s+(?:athlon\s+silver\s+)?(\d{4}[a-z])\b', t, re.I)
        if m:
            cpu=f"AMD {m.group(1)}"; fam="AMD (other)"
    # Intel N-series standalone
    if not cpu:
        m = re.search(r'\b(N\d{2,3})\b', t)
        if m:
            cpu=f"Intel {m.group(1).upper()}"; fam="Intel N-series"
    # Apple silicon
    if not cpu:
        m = re.search(r'\bapple\s*(m[1234])\b|\b(m[1234])\s*(?:pro|max|chip)', low)
        if m:
            g=(m.group(1) or m.group(2)).upper(); cpu=f"Apple {g}"; fam=f"Apple {g}"
    # Apple M in MacBook context (e.g. "MacBook Air M1 8/256")
    if not cpu and ('macbook' in low or 'apple' in low):
        m = re.search(r'\bm([1234])\b', t, re.I)
        if m:
            g=f"M{m.group(1)}"; cpu=f"Apple {g}"; fam=f"Apple {g}"
    # Intel Core i-series WITHOUT model number ("Core i5 prosessor", "core i5 12th gen")
    if not cpu:
        m = re.search(r'\bcore\s*(i[3579])\b', t, re.I)
        if m:
            cpu=f"Core {m.group(1).lower()}"; fam=f"Intel Core {m.group(1).lower()}"
    # Qualcomm Snapdragon (ARM)
    if not cpu:
        m = re.search(r'snapdragon\s*(x\s*(?:elite|plus))?', t, re.I)
        if m:
            sub=m.group(1)
            cpu='Snapdragon '+(re.sub(r'\s+',' ',sub).title() if sub else 'X'); fam='Qualcomm Snapdragon'
    # Celeron / Pentium / Athlon
    if not cpu:
        for k,f in [('celeron','Intel Celeron'),('pentium','Intel Pentium'),('athlon','AMD Athlon')]:
            if k in low:
                cpu=k.title(); fam=f; break
    # Last resort: Intel new Core with no model ("Core-5", "Core 7")
    if not cpu:
        m = re.search(r'\bcore[\s-]+([3579])\b', t, re.I)
        if m:
            cpu=f"Core {m.group(1)}"; fam=f"Intel Core {m.group(1)}"
    out['CPU']=cpu; out['CPU_family']=fam
    # RAM: collect all "<n> GB" candidates, pick a plausible RAM value
    ram=None
    cands=[]
    for mm in re.finditer(r'(\d{1,3})\s*g\s*b\b', low):
        v=int(mm.group(1)); ctx=low[max(0,mm.start()-16):mm.end()+18]
        cands.append((v,ctx))
    # 1) value in RAMSET with explicit ram/ddr context
    for v,ctx in cands:
        if v in RAMSET and any(x in ctx for x in ['ram','ddr','operativ','lpddr','memory','yaddaş','yaddash']):
            ram=v; break
    # 2) any value in RAMSET (<=64) — first one
    if ram is None:
        for v,ctx in cands:
            if v in RAMSET:
                ram=v; break
    out['RAM_GB']=ram
    # Storage
    stor=None; stype=None
    for pat,ty in [
        (r'(\d)\s*tb\s*(?:ssd|nvme|m\.?2)', 'SSD_TB'),
        (r'(\d{3,4})\s*gb\s*(?:m\.?2|nvme|ssd)', 'SSD_GB'),
        (r'ssd[^0-9]{0,6}(\d{3,4})\s*gb', 'SSD_GB'),
        (r'ssd[^0-9]{0,6}(\d)\s*tb', 'SSD_TB'),
        (r'nvme[^0-9]{0,6}(\d{3,4})\s*gb', 'SSD_GB'),
        (r'(\d)\s*tb\s*(?:hdd|hard)', 'HDD_TB'),
        (r'(\d{3,4})\s*gb\s*(?:hdd|hard)', 'HDD_GB'),
        (r'yaddaş[^0-9]{0,8}(\d{3,4})\s*gb', 'SSD_GB'),
        (r'(?:disk|yaddaş)[^0-9]{0,10}(\d{3,4})\s*gb', 'SSD_GB'),
    ]:
        m=re.search(pat, low)
        if m:
            val=m.group(1)
            stor=f"{val} TB" if ty.endswith('TB') else f"{val} GB"
            stype='SSD' if ty.startswith('SSD') else 'HDD'
            break
    out['Storage']=stor; out['Storage_type']=stype
    # GPU — try clean discrete patterns first, then integrated (avoids marketing junk)
    gpu=None
    m=re.search(r'\b(rtx|gtx)\s*(\d{3,4})\s*(ti)?\b', t, re.I)
    if m: gpu=f"{m.group(1).upper()} {m.group(2)}"+(" Ti" if m.group(3) else "")
    if not gpu:
        m=re.search(r'\bmx\s*(\d{3,4})\b', t, re.I)
        if m: gpu=f"MX{m.group(1)}"
    if not gpu:
        m=re.search(r'\brx\s*(\d{3,4})\s*(m)?\b', t, re.I)
        if m: gpu=f"RX {m.group(1)}"+("M" if m.group(2) else "")
    if not gpu:
        m=re.search(r'\barc\s*(a?\d{3,4}m?)\b', t, re.I)
        if m: gpu=f"Arc {m.group(1).upper()}"
    if not gpu and re.search(r'iris\s*xe', t, re.I): gpu='Iris Xe'
    if not gpu:
        m=re.search(r'radeon\s*(\d{3,4}m)\b', t, re.I)
        if m: gpu=f"Radeon {m.group(1).upper()}"
    if not gpu and re.search(r'radeon\s*graphics', t, re.I): gpu='Radeon Graphics'
    if not gpu and re.search(r'uhd\s*graphics', t, re.I): gpu='UHD Graphics'
    if not gpu and re.search(r'\bhd\s*graphics\b', t, re.I): gpu='HD Graphics'
    # bare GeForce number near a GPU cue (desktops: "Video kart 1050 ti", "VGA 1650")
    if not gpu:
        m=re.search(r'(?:video\s*kart|videokart|vga|geforce|nvidia|gpu|qrafik|ekran kart)[^0-9]{0,14}(\d{3,4})\s*(ti)?', t, re.I)
        if m: gpu=("GTX " if int(m.group(1))<2000 else "RTX ")+m.group(1)+(" Ti" if m.group(2) else "")
    out['GPU']=gpu
    # Screen
    scr=None
    m = re.search(r'\b(1[0-7])[.,](\d)\s*(?:["”″\'′]|inch|inç|d[üu]ym)', t, re.I)
    if m: scr=f"{m.group(1)}.{m.group(2)}"
    if not scr:
        m=re.search(r'\b(1[0-7])[.,](\d)\b', t)
        if m: scr=f"{m.group(1)}.{m.group(2)}"
    if not scr:
        m=re.search(r'\b(1[0-7])\s*(?:["”″]|inch|inç|d[üu]ym)', t)
        if m: scr=m.group(1)
    out['Screen']=scr
    # OS
    osv=None
    if 'windows 11' in low: osv='Windows 11'
    elif 'windows 10' in low: osv='Windows 10'
    elif re.search(r'mac\s?os|sonoma|ventura|sequoia|monterey', low): osv='macOS'
    elif re.search(r'free\s*-?\s*dos|freedos|\bdos\s*\d', low): osv='Free DOS'
    elif re.search(r'\bno\s*os\b|os yoxdur|əməliyyat sistemi yoxdur|without os', low): osv='No OS'
    elif re.search(r'\blinux\b|ubuntu', low): osv='Linux'
    elif re.search(r'\bwindows\b', low): osv='Windows'
    out['OS']=osv
    return out

