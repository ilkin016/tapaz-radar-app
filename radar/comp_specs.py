#!/usr/bin/env python3
"""Komponent kateqoriya-spesifik filtr sahələrini `name`+`params` mətnindən çıxarır.
Analizə əsaslanır: `params` truncate/misparse ola bilər, ona görə ƏSAS mənbə `name`, `params` fallback.
Hər parser struktur sahələr qaytarır ki, dashboard-da kaskad filtrlər (brend→seriya→model) qurulsun."""
import re

_SMART_Q = "“”‘’"
_TM = "™®©"


def norm(s):
    """AZ İ/ı, ağıllı dırnaq, ™®©, nbsp, çox-boşluq təmizliyi + UPPER."""
    s = (s or "").replace("İ", "I").replace("ı", "i")
    for ch in _SMART_Q:
        s = s.replace(ch, '"')
    for ch in _TM:
        s = s.replace(ch, "")
    s = s.replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().upper()


# ---------------- CPU ----------------
def parse_cpu(name, params):
    t = norm((name or "") + " " + (params or ""))
    brand = series = model = None
    gen = None
    if re.search(r"RYZEN|\bAMD\b|THREADRIPPER|EPYC", t):
        brand = "AMD"
        m = re.search(r"RYZEN\s*([3579])\b", t)
        series = ("Ryzen " + m.group(1)) if m else ("Threadripper" if "THREADRIPPER" in t
                 else "EPYC" if "EPYC" in t else "Ryzen (digər)")
        m = re.search(r"RYZEN\s*[3579]?[\s-]*([0-9]{3,4}\s*(?:X3D|XT|X|G[EX]?|F|H|U)?)", t)
        if m:
            model = re.sub(r"([0-9])\s+([A-Z])", r"\1\2", (series + " " + m.group(1))).strip()
            d = re.search(r"(\d{4})", model)
            if d:
                gen = d.group(1)[0] + "000"
    elif re.search(r"INTEL|CORE\s*I|CORE\s*ULTRA|XEON|PENTIUM|CELERON|\bI[3579][\s-]?[0-9]", t):
        brand = "Intel"
        if re.search(r"ULTRA\s*9", t): series = "Core Ultra 9"
        elif re.search(r"ULTRA\s*7", t): series = "Core Ultra 7"
        elif re.search(r"ULTRA\s*5", t): series = "Core Ultra 5"
        elif "XEON" in t: series = "Xeon"
        elif "PENTIUM" in t: series = "Pentium"
        elif "CELERON" in t: series = "Celeron"
        else:
            m = re.search(r"\bI([3579])\b", t) or re.search(r"CORE\s*I([3579])", t)
            if m: series = "Core i" + m.group(1)
        if "ULTRA" in t:
            m = re.search(r"ULTRA\s*[579][\s-]*([0-9]{3}[A-Z]{0,2})", t)
            if m and series: model = series + " " + m.group(1)
        else:
            m = re.search(r"\bI[3579][\s-]*([0-9]{4,5}[A-Z]{0,2})", t)
            if m and series: model = series.replace("Core ", "") + "-" + m.group(1)
        if model:
            d = re.search(r"(\d{4,5})", model)
            if d:
                gen = int(d.group(1)[:2]) if len(d.group(1)) == 5 else int(d.group(1)[:1])
                gen = str(gen)
    else:
        brand = "Digər"
    return {"c_brand": brand, "c_series": series, "c_model": model, "c_gen": gen}


# ---------------- Ana plata (motherboard) ----------------
_AMD_CHIP = re.compile(r"\b(A320|A520|A620|B350|B450|B550|B650E?|B840|B850|X370|X470|X570|X670E?|X870E?)\b")
_AMD_SOCK = re.compile(r"\bAM[345]\b")
_INTEL_CHIP = re.compile(r"\b(H61|H81|B75|H110|B150|B250|H310|B360|B365|H410|B460|H470|Z490|H510|B560|H570|Z590|H610|B660|H670|Z690|B760|H770|Z790|B860|Z890)\b")
_INTEL_SOCK = re.compile(r"\bLGA\s?(775|1150|1151|1155|1156|1200|1700|1851|2011|2066)\b")


def parse_mobo(name, params):
    t = norm((name or "") + " " + (params or ""))
    if _AMD_CHIP.search(t) or _AMD_SOCK.search(t) or "RYZEN" in t:
        m = _AMD_CHIP.search(t) or _AMD_SOCK.search(t)
        return {"mb_plat": "AMD", "mb_chip": m.group(0) if m else None}
    if _INTEL_CHIP.search(t) or _INTEL_SOCK.search(t) or re.search(r"\bINTEL\b|XEON|PENTIUM|CELERON|CORE\s*I", t):
        m = _INTEL_CHIP.search(t) or _INTEL_SOCK.search(t)
        return {"mb_plat": "Intel", "mb_chip": m.group(0) if m else None}
    return {"mb_plat": "Digər", "mb_chip": None}


# ---------------- RAM ----------------
def parse_ram(name, params):
    t = norm((name or "") + " " + (params or ""))
    if re.search(r"DDR\s?5|\bD5\b|\bPC5\b", t): typ = "DDR5"
    elif re.search(r"DDR\s?4|\bD4\b|\bPC4\b", t): typ = "DDR4"
    elif re.search(r"DDR\s?3L?|\bD3\b|\bPC3L?\b", t): typ = "DDR3"
    elif re.search(r"DDR\s?2|\bPC2\b", t): typ = "DDR2"
    elif re.search(r"\bDDR1?\b|\bPC1\b", t): typ = "DDR/DDR1"
    else: typ = "Digər"
    gb = None
    m = re.search(r"(\d+)\s*GB", (params or ""), re.I) or re.search(r"(\d+)\s*GB", t)
    if m:
        gb = int(m.group(1))
    elif re.search(r"(\d+)\s*MB", t, re.I):
        gb = 0
    if gb is None: bucket = "Naməlum"
    elif gb == 0 or gb <= 1: bucket = "≤1 GB"
    elif gb in (2, 4, 8, 16, 32, 48, 64, 96, 128): bucket = str(gb) + " GB"
    else: bucket = "Digər"
    return {"ram_type": typ, "ram_gb": gb, "ram_bucket": bucket}


# ---------------- Video kart (GPU) ----------------
def parse_gpu(name, params):
    t = norm((name or "") + " " + (params or ""))
    fam = num = tier = None
    # 1. RTX consumer (validasiya whitelist)
    m = re.search(r"\bRTX\s*-?\s*(20[5-9]0|30[5-9]0|40[6-9]0|50[5-9]0)\s*(TI|SUPER)?", t)
    if m: fam, num, tier = "RTX", m.group(1), (m.group(2) or "")
    if not fam:
        m = re.search(r"\bGTX\s*-?\s*(10[1-8]0|16[1-6]0)\s*(TI|SUPER)?", t)
        if m: fam, num, tier = "GTX", m.group(1), (m.group(2) or "")
    if not fam:
        m = re.search(r"\bRX\s*-?\s*(9[01]\d0|7[0-9]00|6[0-9]00|5[5-7]00|5[5-9]0|4[78]0)\s*(XT|XTX)?", t)
        if m: fam, num, tier = "RX", m.group(1), (m.group(2) or "")
    if not fam:
        m = re.search(r"\bGTX\s*-?\s*([2-9][0-9]0)\s*(TI)?", t)
        if m: fam, num, tier = "GTX", m.group(1), (m.group(2) or "")
    if not fam:
        m = re.search(r"\bGT\s*-?\s*(210|220|610|630|710|730|740|1010|1030)\b", t)
        if m: fam, num, tier = "GT", m.group(1), ""
    if not fam:
        m = re.search(r"\bARC\s*-?\s*([AB]\d{3})\b", t)
        if m: fam, num, tier = "Arc", m.group(1), ""
    if not fam:  # bare number fallback
        m = re.search(r"(?<![\w])(30[5-9]0|40[6-9]0|50[5-9]0|16[1-6]0|10[1-8]0)\s*(TI|XT)?(?![\w])", t)
        if m:
            n = m.group(1); tier = m.group(2) or ""
            fam = "RTX" if n[:2] in ("30", "40", "50") else "GTX"
            num = n
    if not fam:
        if re.search(r"\b(CMP|P10[46])\b", t): return {"gpu_fam": "Mining", "gpu_series": "Mining", "gpu_model": "Mining"}
        if re.search(r"QUADRO|TESLA|\bWX\b|RTX\s*(A|PRO)\s*\d000", t): return {"gpu_fam": "Pro", "gpu_series": "Workstation", "gpu_model": "Workstation"}
        return {"gpu_fam": None, "gpu_series": None, "gpu_model": None}
    tier = tier.title() if tier else ""
    # seriya
    if fam in ("RTX", "GTX"):
        series = fam + " " + (num[:2] if len(num) == 4 else num[0] + "00")
    elif fam == "RX":
        series = "RX " + (num[0] + "000" if len(num) == 4 else num[0] + "00")
    elif fam == "Arc":
        series = "Intel Arc " + num[0]
    else:
        series = fam
    model = (fam + " " + num + (" " + tier if tier else "")).strip()
    return {"gpu_fam": fam, "gpu_series": series, "gpu_model": model}


# ---------------- SSD / HDD ----------------
_CAP_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(TB|GB)\b", re.I)


def _capacity_gb(text):
    cands = []
    for m in _CAP_RE.finditer(text):
        after = text[m.end():m.end() + 3].lower()
        if after[:2] in ("/s", "ps") or after.startswith("/с"):
            continue
        num = float(m.group(1).replace(",", "."))
        gb = num * 1000 if m.group(2).lower() == "tb" else num
        if 8 <= gb <= 64000:
            cands.append(gb)
    return max(cands) if cands else None


def _cap_bucket(gb):
    if gb is None: return "Naməlum"
    if gb <= 64: return "≤64 GB"
    if gb <= 130: return "128 GB"
    if gb <= 260: return "256 GB"
    if gb <= 520: return "512 GB"
    if gb <= 1030: return "1 TB"
    if gb <= 2100: return "2 TB"
    if gb <= 4100: return "4 TB"
    if gb <= 8200: return "8 TB"
    if gb <= 16500: return "10-16 TB"
    return "18 TB+"


def parse_ssd(name, params):
    t = norm((name or "") + " " + (params or "")).lower()
    if re.search(r"nvme|m\.?2\b|pci-?e|pcie|gen\s?[345]", t): iface, typ = "M.2 / NVMe", "SSD"
    elif re.search(r"ssd", t) and re.search(r"sata|2\.?5[\"' ]", t): iface, typ = "SATA / 2.5\"", "SSD"
    elif re.search(r"ssd", t): iface, typ = "SSD (interfeys yox)", "SSD"
    elif re.search(r"hdd|hard\s?disk|sərt disk", t): iface, typ = "HDD", "HDD"
    else: iface, typ = "Naməlum", "Naməlum"
    gb = _capacity_gb((name or "") + " " + (params or ""))
    return {"ssd_type": typ, "ssd_iface": iface, "ssd_gb": int(gb) if gb else None, "ssd_bucket": _cap_bucket(gb)}


# ---------------- Monitor ----------------
def _resolution(t):
    if re.search(r"7680|\b8K\b", t): return "8K"
    if re.search(r"5120|\b5K\b", t): return "5K"
    if re.search(r"3840|\bUHD\b|\b4K\b", t): return "4K"
    if re.search(r"\bW?QHD\b|2560|1440|\b2\.?5?K\b|\b3\.?5K\b", t): return "2K"
    if re.search(r"\bF(ULL)?\s*HD\b|FHD|1920|1080", t): return "FHD"
    if re.search(r"\bHD\b|1366|1280", t): return "HD"
    return None


def _size_bucket(sz):
    if sz is None: return None
    if sz <= 19: return "≤19\""
    if sz <= 21: return "20-21\""
    if sz == 22: return "22\""
    if sz <= 24: return "23-24\""
    if sz <= 26: return "25-26\""
    if sz == 27: return "27\""
    if sz <= 30: return "28-30\""
    if sz <= 32: return "31-32\""
    if sz <= 34: return "34\" (UW)"
    if sz < 50: return "35-49\""
    return "≥50\""


def _hz_bucket(hz):
    if hz is None: return None
    if hz <= 60: return "60Hz"
    if hz <= 75: return "75Hz"
    if hz < 120: return "100Hz"
    if hz < 144: return "120Hz"
    if hz < 165: return "144Hz"
    if hz < 180: return "165Hz"
    if hz < 200: return "180Hz"
    if hz < 240: return "200-239Hz"
    if hz < 300: return "240-288Hz"
    return "300Hz+"


def parse_monitor(name, params):
    t = norm((name or "") + " " + (params or ""))
    m = re.search(r"(\d{2}(?:[.,]\d)?)\s*(?:\"|”|INCH|INC\b|DY[ÜU]?M|DYUM)", t)
    size = round(float(m.group(1).replace(",", "."))) if m else None
    hz_all = [int(x) for x in re.findall(r"(\d{2,3})\s*HZ", t)]
    hz = max(hz_all) if hz_all else None
    oled = bool(re.search(r"\b(QD[-\s]?)?OLED\b|\bAMOLED\b", t))
    return {"mon_size": size, "mon_size_b": _size_bucket(size), "mon_res": _resolution(t),
            "mon_hz": hz, "mon_hz_b": _hz_bucket(hz), "mon_oled": 1 if oled else 0}


_DISPATCH = {
    "CPU": parse_cpu,
    "Ana plata": parse_mobo,
    "RAM": parse_ram,
    "Video kart (GPU)": parse_gpu,
    "Sərt disk (SSD/HDD)": parse_ssd,
    "Monitor": parse_monitor,
}


def component_specs(subcategory, name, params):
    fn = _DISPATCH.get(subcategory)
    return fn(name, params) if fn else None
