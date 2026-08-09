#!/usr/bin/env python3
"""Desktop-PC specific logic: GPU tier scoring, form-factor, GPU-weighted value."""
import re

# GPU model -> tier score (0-100). Desktops are GPU-centric.
GPU_TIER = {
    5090: 100, 4090: 100, 5080: 95, 4080: 92, 3090: 88, 5070: 85, 4070: 82,
    3080: 80, 2080: 70, 5060: 70, 4060: 68, 3070: 72, 3060: 62, 2070: 62,
    2060: 52, 1660: 45, 3050: 50, 1650: 38, 1060: 40, 1050: 28, 1030: 18, 750: 12,
}


def gpu_tier_score(gpu):
    """Score a parsed GPU string. Handles RTX/GTX + bare GeForce numbers."""
    if not gpu:
        return 0
    g = gpu.upper()
    m = re.search(r'(\d{3,4})', g)
    if not m:
        return 0
    num = int(m.group(1))
    base = GPU_TIER.get(num, 0)
    if base == 0 and 700 <= num <= 5999:
        base = 40  # unknown but plausible discrete GeForce/Radeon
    if 'TI' in g:
        base = min(100, base + 6)
    return base


FORMS = [
    (r'mini\s*pc|usff|\btiny\b|mini kompüter|micro pc', 'Mini PC'),
    (r'all.?in.?one|\baio\b|monoblok|monoblock', 'Monoblok (AIO)'),
    (r'sistem\s*blok|system\s*unit|blok\b(?!.*monitor)', 'Sistem bloku'),
    (r'\bdəst\b|dest\b|monitor.*komplekt|komplekt|\+\s*monitor', 'Dəst (+monitor)'),
]


def form_factor(name, body):
    t = ((name or '') + ' ' + (body or '')).lower()
    for pat, label in FORMS:
        if re.search(pat, t):
            return label
    return 'Masaüstü'


# desktop value: GPU-weighted (0.35 CPU + 0.20 RAM + 0.18 storage + 0.27 GPU)
def score_desktop(cpu_sc, ram_sc, stor_sc, gpu_tier, is_new):
    spec = round(0.35 * cpu_sc + 0.20 * ram_sc + 0.18 * stor_sc + 0.27 * gpu_tier, 1)
    if is_new:
        spec = round(min(100, spec + 2), 1)
    return spec
