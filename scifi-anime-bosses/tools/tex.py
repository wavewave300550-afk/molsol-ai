"""
tex.py - procedural texture painters (numpy).

Every painter has the signature  painter(w, h, variant) -> float32 array (h, w, 4)
with RGB in 0..1 and A in 0..1.  For the opaque `entity_emissive` pass the alpha
channel is the *emissive mask*: 1.0 = normally lit, lower = glowing (see GLOW()).
Variants: "p1" (Sacred Vessel) and "p2" (False Ascension: cracked, corrupted).
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, Tuple

import numpy as np

# --------------------------------------------------------------------------- colour helpers


def hexc(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def GLOW(g):
    """Alpha value for an emissive amount g in [0, 1] (entity_emissive: low alpha = glow)."""
    return 1.0 - np.clip(g, 0.0, 1.0) * 0.975


def blank(w, h, rgb, a=1.0):
    img = np.zeros((h, w, 4), dtype=np.float32)
    img[..., :3] = rgb
    img[..., 3] = a
    return img


def lerp(a, b, t):
    return a + (b - a) * t


def blend(img, mask, rgb, alpha=None):
    """Blend colour rgb into img where mask (h,w) in 0..1."""
    m = mask[..., None]
    img[..., :3] = img[..., :3] * (1 - m) + np.asarray(rgb, dtype=np.float32) * m
    if alpha is not None:
        img[..., 3] = img[..., 3] * (1 - mask) + alpha * mask
    return img


# --------------------------------------------------------------------------- noise

def _rng(seed):
    return np.random.default_rng(seed)


def value_noise(w, h, cell, seed=0, tile=True):
    """Smooth value noise, optionally tileable, returns (h,w) in 0..1."""
    rng = _rng(seed)
    gw, gh = max(1, int(math.ceil(w / cell))), max(1, int(math.ceil(h / cell)))
    grid = rng.random((gh + 1, gw + 1)).astype(np.float32)
    if tile:
        grid[-1, :] = grid[0, :]
        grid[:, -1] = grid[:, 0]
    ys = (np.arange(h) + 0.5) / cell
    xs = (np.arange(w) + 0.5) / cell
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    fx = xs - x0
    fy = ys - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    x0 = np.clip(x0, 0, gw - 1)
    y0 = np.clip(y0, 0, gh - 1)
    a = grid[y0][:, x0]
    b = grid[y0][:, x0 + 1]
    c = grid[y0 + 1][:, x0]
    d = grid[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def fbm(w, h, base_cell=32, octaves=4, seed=0, gain=0.5):
    total = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    cell = base_cell
    for o in range(octaves):
        total += value_noise(w, h, max(1.0, cell), seed + o * 101) * amp
        norm += amp
        amp *= gain
        cell /= 2.0
    return total / norm


def worley(w, h, n_points, seed=0):
    """Tileable Worley noise: returns (f1, f2) distance fields normalised roughly 0..1."""
    rng = _rng(seed)
    pts = rng.random((n_points, 2)) * np.array([w, h])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    best1 = np.full((h, w), 1e9, dtype=np.float32)
    best2 = np.full((h, w), 1e9, dtype=np.float32)
    for (px, py) in pts:
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                d = np.sqrt((xx - px - ox) ** 2 + (yy - py - oy) ** 2)
                nb2 = np.minimum(best2, np.maximum(best1, d))
                best1 = np.minimum(best1, d)
                best2 = nb2
    scale = math.sqrt(w * h / n_points)
    return best1 / scale, best2 / scale


def draw_line(mask, x0, y0, x1, y1, value=1.0, width=1):
    """Rasterise a line into a float mask (in place)."""
    h, w = mask.shape
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        t = i / max(1, n)
        x = int(round(x0 + (x1 - x0) * t))
        y = int(round(y0 + (y1 - y0) * t))
        for dx in range(-(width // 2), width - width // 2):
            for dy in range(-(width // 2), width - width // 2):
                xx, yy = (x + dx) % w, (y + dy) % h
                mask[yy, xx] = max(mask[yy, xx], value)


def crack_mask(w, h, seed, n_cracks=5, length=40, branch=0.35):
    """Fractal branching cracks (tileable via wrap)."""
    rng = random.Random(seed)
    mask = np.zeros((h, w), dtype=np.float32)

    def grow(x, y, ang, life, depth):
        while life > 0:
            step = rng.uniform(2.0, 4.0)
            nx = x + math.cos(ang) * step
            ny = y + math.sin(ang) * step
            draw_line(mask, x, y, nx, ny, 1.0, 1)
            x, y = nx, ny
            ang += rng.uniform(-0.6, 0.6)
            life -= step
            if depth < 3 and rng.random() < branch * 0.25:
                grow(x, y, ang + rng.choice([-1, 1]) * rng.uniform(0.5, 1.2), life * 0.5, depth + 1)
    for _ in range(n_cracks):
        grow(rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, math.tau), length * rng.uniform(0.6, 1.3), 0)
    return mask


def dilate(mask, r=1):
    out = mask.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            out = np.maximum(out, np.roll(np.roll(mask, dx, axis=1), dy, axis=0) * (1.0 - 0.35 * max(abs(dx), abs(dy))))
    return out


def blur(mask, r=1, passes=1):
    out = mask.astype(np.float32)
    for _ in range(passes):
        acc = np.zeros_like(out)
        n = 0
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                acc += np.roll(np.roll(out, dx, axis=1), dy, axis=0)
                n += 1
        out = acc / n
    return out


# --------------------------------------------------------------------------- glyphs (alien scripture)

def glyph_bitmap(seed: int, gw=5, gh=7) -> np.ndarray:
    """A procedurally generated glyph (strokes on a 5x7 grid)."""
    rng = random.Random(seed)
    g = np.zeros((gh, gw), dtype=np.float32)
    # spine
    if rng.random() < 0.7:
        x = rng.choice([0, gw // 2, gw - 1])
        g[:, x] = 1
    # bars
    for _ in range(rng.randint(1, 3)):
        y = rng.randint(0, gh - 1)
        x0 = rng.randint(0, gw - 2)
        x1 = rng.randint(x0 + 1, gw - 1)
        g[y, x0:x1 + 1] = 1
    # diagonals / dots
    for _ in range(rng.randint(0, 2)):
        x, y = rng.randint(0, gw - 1), rng.randint(0, gh - 1)
        dx = rng.choice([-1, 1])
        for k in range(rng.randint(2, 4)):
            xx, yy = x + dx * k, y + k
            if 0 <= xx < gw and 0 <= yy < gh:
                g[yy, xx] = 1
    if rng.random() < 0.5:
        g[rng.randint(0, gh - 1), rng.randint(0, gw - 1)] = 1
    return g


def glyph_strip_mask(w, h, seed, gw=5, gh=7, spacing=2):
    """Row(s) of glyphs centred vertically; returns (h,w) mask."""
    mask = np.zeros((h, w), dtype=np.float32)
    rows = max(1, (h + 1) // (gh + 3))
    total_h = rows * gh + (rows - 1) * 3
    y0 = (h - total_h) // 2
    k = 0
    for r in range(rows):
        x = 1
        while x + gw <= w:
            g = glyph_bitmap(seed * 977 + k, gw, gh)
            yy = y0 + r * (gh + 3)
            if yy >= 0 and yy + gh <= h:
                mask[yy:yy + gh, x:x + gw] = np.maximum(mask[yy:yy + gh, x:x + gw], g)
            x += gw + spacing
            k += 1
    return mask


# --------------------------------------------------------------------------- palette

PAL = {
    "white": hexc("e7eaef"), "white_hi": hexc("fbfcfe"), "white_lo": hexc("b9c0ca"), "seam": hexc("7d8794"),
    "gold": hexc("e3b341"), "gold_hi": hexc("fff0a8"), "gold_lo": hexc("8a5e12"),
    "cyan": hexc("4fe8ff"), "cyan_hi": hexc("d8fbff"), "cyan_lo": hexc("0f6f8f"),
    "violet": hexc("b35cff"), "violet_hi": hexc("f0d2ff"), "violet_lo": hexc("3c0f5e"),
    "slate": hexc("1f2a33"), "gunmetal": hexc("3b4048"), "black": hexc("0b0d10"),
    "flesh": hexc("2a1028"), "flesh_hi": hexc("6d2a63"), "ivory": hexc("e6dcc4"), "ivory_lo": hexc("a8977a"),
    "crimson": hexc("4a0d1e"), "brass": hexc("c9a14a"),
}


def accent(variant):
    return (PAL["cyan"], PAL["cyan_hi"]) if variant == "p1" else (PAL["violet"], PAL["violet_hi"])


# --------------------------------------------------------------------------- swatch painters

def _panel_layout(w, h, seed, base=16):
    """Irregular panel layout: returns list of rects (x,y,pw,ph) covering the swatch."""
    rng = random.Random(seed)
    rects = []
    occupied = np.zeros((h // base + 1, w // base + 1), dtype=bool)
    for gy in range(h // base):
        for gx in range(w // base):
            if occupied[gy, gx]:
                continue
            pw = rng.choice([1, 1, 2, 2, 3])
            ph = rng.choice([1, 2, 2, 3])
            pw = min(pw, w // base - gx)
            ph = min(ph, h // base - gy)
            while pw > 1 and occupied[gy, gx:gx + pw].any():
                pw -= 1
            ok = True
            for yy in range(gy, gy + ph):
                if occupied[yy, gx:gx + pw].any():
                    ok = False
            if not ok:
                ph = 1
            occupied[gy:gy + ph, gx:gx + pw] = True
            rects.append((gx * base, gy * base, pw * base, ph * base))
    return rects


def armor(seed=11, tint="white", glyph_band=False):
    def painter(w, h, variant):
        rng = random.Random(seed)
        base = PAL["white"] if tint == "white" else PAL["ivory"]
        img = blank(w, h, base)
        n = fbm(w, h, 48, 3, seed)
        img[..., :3] *= (0.95 + 0.07 * n)[..., None]
        seam = np.zeros((h, w), np.float32)
        hi = np.zeros((h, w), np.float32)
        inset = np.zeros((h, w), np.float32)
        gold = np.zeros((h, w), np.float32)
        bolts = np.zeros((h, w), np.float32)
        vents = np.zeros((h, w), np.float32)
        for (x, y, pw, ph) in _panel_layout(w, h, seed):
            seam[y, x:x + pw] = 1
            seam[y:y + ph, x] = 1
            hi[(y + 1) % h, x + 1:x + pw] = 1
            hi[y + 1:y + ph, (x + 1) % w] = 1
            r = rng.random()
            if r < 0.30 and pw >= 32 and ph >= 16:
                # recessed inset panel
                inset[y + 4:y + ph - 3, x + 4:x + pw - 3] = 1
            elif r < 0.45:
                # gold scripture line
                yy = y + ph // 2
                gold[yy, x + 4:x + pw - 4] = 1
                if pw > 24:
                    gold[y + 4:y + ph - 4, x + pw - 6] = 1
            elif r < 0.55 and pw >= 16:
                for k in range(3):
                    yy = y + 5 + k * 3
                    if yy < y + ph - 3:
                        vents[yy, x + 5:x + pw - 5] = 1
            # bolts at corners
            for (bx, by) in ((x + 2, y + 2), (x + pw - 3, y + 2), (x + 2, y + ph - 3), (x + pw - 3, y + ph - 3)):
                if 0 <= bx < w and 0 <= by < h and rng.random() < 0.7:
                    bolts[by, bx] = 1
        ao = blur(seam, 1, 2)
        img[..., :3] *= (1.0 - 0.22 * ao)[..., None]
        img = blend(img, hi * 0.55, PAL["white_hi"])
        inset_edge = np.clip(dilate(inset, 1) - inset, 0, 1)
        img[..., :3] *= (1.0 - 0.10 * inset)[..., None]
        img = blend(img, inset_edge * 0.45, PAL["white_lo"])
        img = blend(img, gold, PAL["gold"])
        img = blend(img, vents, PAL["slate"])
        img = blend(img, bolts, PAL["white_lo"])
        img = blend(img, seam, PAL["seam"])
        if glyph_band:
            band_h = min(11, h // 3)
            y0 = h // 2 - band_h // 2
            img[y0:y0 + band_h, :, :3] = PAL["slate"]
            img[y0, :, :3] = PAL["gold"]
            img[y0 + band_h - 1, :, :3] = PAL["gold_lo"]
            gm = np.zeros((h, w), np.float32)
            gm[y0 + 2:y0 + band_h - 2, :] = glyph_strip_mask(w, band_h - 4, seed + 5)
            c, chi = accent(variant)
            if variant == "p2":
                gm *= (fbm(w, h, 8, 2, seed + 9) > 0.35)
            img = blend(img, gm, c, alpha=GLOW(0.95))
        grime = fbm(w, h, 24, 3, seed + 3)
        img[..., :3] *= (1.0 - 0.10 * np.clip(grime - 0.55, 0, 1) * 2)[..., None]
        if variant == "p2":
            cr = crack_mask(w, h, seed + 77, n_cracks=7, length=60)
            halo = blur(dilate(cr, 2), 1, 2)
            stain = np.clip(halo * 1.4, 0, 1)
            img = blend(img, stain * 0.55, PAL["violet_lo"] * 0.9)
            img = blend(img, np.clip(dilate(cr, 1) - cr, 0, 1), PAL["black"])
            img = blend(img, cr, PAL["violet_hi"], alpha=GLOW(1.0))
            scorch = np.clip(fbm(w, h, 40, 3, seed + 21) - 0.5, 0, 1) * 1.6
            img[..., :3] *= (1.0 - 0.35 * scorch)[..., None]
        return img
    return painter


def glyph_strip(seed=43):
    """Slate inlay with one row of holy scripture (emissive)."""
    def painter(w, h, variant):
        img = blank(w, h, PAL["slate"])
        img[0, :, :3] = PAL["gold"]
        img[-1, :, :3] = PAL["gold_lo"]
        gm = np.zeros((h, w), np.float32)
        gm[2:h - 2, :] = glyph_strip_mask(w, h - 4, seed, gw=3, gh=min(5, h - 4), spacing=2)
        c, chi = accent(variant)
        if variant == "p2":
            gm *= (fbm(w, h, 6, 2, seed + 9) > 0.4)
        img = blend(img, gm, c, alpha=GLOW(1.0))
        return img
    return painter


def gold_trim(seed=3):
    def painter(w, h, variant):
        img = blank(w, h, PAL["gold"])
        ys = (np.arange(h) + 0.5) / h
        grad = np.where(ys < 0.5, 1.0 + 0.25 * (0.5 - ys) * 2, 1.0 - 0.45 * (ys - 0.5) * 2).astype(np.float32)
        img[..., :3] *= grad[:, None, None]
        xs = np.arange(w)
        scroll = np.zeros((h, w), np.float32)
        mid = h / 2
        for x in xs:
            y = mid + math.sin(x / 6.0 * math.pi) * (h * 0.22)
            yi = int(y)
            if 1 <= yi < h - 1:
                scroll[yi, x] = 1
            if x % 12 == 0:
                for a in range(0, 360, 30):
                    cx = x + math.cos(math.radians(a)) * 2.5
                    cy = mid + math.sin(math.radians(a)) * 2.5
                    if 0 <= int(cy) < h:
                        scroll[int(cy), int(cx) % w] = 1
        img = blend(img, scroll * 0.8, PAL["gold_lo"])
        img = blend(img, np.roll(scroll, -1, axis=0) * 0.5, PAL["gold_hi"])
        img[0, :, :3] = PAL["gold_hi"]
        img[-1, :, :3] = PAL["gold_lo"] * 0.8
        speck = (_rng(seed).random((h, w)) < 0.03).astype(np.float32)
        img = blend(img, speck * 0.7, PAL["gold_hi"])
        if variant == "p2":
            tarn = fbm(w, h, 16, 3, seed + 5)
            img[..., :3] *= (0.72 + 0.2 * tarn)[..., None]
            img = blend(img, scroll * 0.35, PAL["violet"] * 0.6)
        return img
    return painter


def flesh(seed=7, glow_amt=0.55):
    def painter(w, h, variant):
        n = fbm(w, h, 32, 4, seed)
        img = blank(w, h, PAL["flesh"])
        img[..., :3] = PAL["flesh"] * (0.65 + 0.7 * n[..., None])
        # muscle striations (diagonal)
        yy, xx = np.mgrid[0:h, 0:w]
        stri = (np.sin((xx * 0.9 + yy * 0.35) * 0.9 + n * 6) * 0.5 + 0.5)
        img[..., :3] *= (0.85 + 0.2 * stri)[..., None]
        f1, f2 = worley(w, h, max(6, w * h // 700), seed + 1)
        vein = np.clip(1.0 - (f2 - f1) * 7.0, 0, 1) ** 2
        vein *= (fbm(w, h, 24, 2, seed + 2) > 0.35)
        c = PAL["violet"] if variant == "p2" else hexc("8f3fd0")
        img = blend(img, vein * 0.9, c, alpha=GLOW(glow_amt))
        core = np.clip(1.0 - (f2 - f1) * 14.0, 0, 1) ** 3
        img = blend(img, core * 0.9, PAL["violet_hi"], alpha=GLOW(glow_amt + 0.3))
        wet = (_rng(seed + 4).random((h, w)) < 0.02).astype(np.float32)
        img = blend(img, wet * 0.6, PAL["flesh_hi"] * 1.6)
        return img
    return painter


def bone_tex(seed=5):
    def painter(w, h, variant):
        n = fbm(w, h, 24, 4, seed)
        img = blank(w, h, PAL["ivory"])
        img[..., :3] *= (0.86 + 0.18 * n)[..., None]
        groove = np.zeros((h, w), np.float32)
        for x in range(0, w, 14):
            groove[:, x] = 1
        groove = np.maximum(groove, np.roll(groove, 1, axis=1) * 0.4)
        img = blend(img, groove * 0.6, PAL["ivory_lo"])
        pores = (_rng(seed + 1).random((h, w)) < 0.04).astype(np.float32)
        img = blend(img, pores * 0.5, PAL["ivory_lo"] * 0.8)
        # gold ring bands
        for x in range(6, w, 42):
            img[:, x:x + 2, :3] = PAL["gold"]
            img[:, x, :3] = PAL["gold_hi"]
        if variant == "p2":
            stain = np.clip(fbm(w, h, 20, 3, seed + 6) - 0.45, 0, 1) * 2
            img = blend(img, stain * 0.5, PAL["violet_lo"])
            img = blend(img, groove * 0.8, PAL["violet"], alpha=GLOW(0.5))
        return img
    return painter


def machine(seed=9):
    def painter(w, h, variant):
        img = blank(w, h, PAL["gunmetal"])
        n = fbm(w, h, 16, 3, seed)
        img[..., :3] *= (0.85 + 0.25 * n)[..., None]
        rng = random.Random(seed)
        y = 0
        while y < h:
            ph = rng.choice([6, 8, 10])
            prof = np.sin(np.linspace(0, math.pi, ph)) ** 0.7
            for k in range(min(ph, h - y)):
                img[y + k, :, :3] *= (0.55 + 0.75 * prof[k])
            y += ph + rng.choice([1, 2, 3])
        for x in range(0, w, 16):
            img[:, x, :3] *= 0.5
        leds = np.zeros((h, w), np.float32)
        for _ in range(w * h // 300):
            lx, ly = rng.randrange(w), rng.randrange(h)
            leds[ly, lx] = 1
        c = PAL["cyan"] if variant == "p1" else hexc("ff3d6e")
        img = blend(img, leds, c, alpha=GLOW(1.0))
        return img
    return painter


def ring_band(seed=13):
    def painter(w, h, variant):
        img = blank(w, h, hexc("efe9dc"))
        ys = (np.arange(h) + 0.5) / h
        edge = np.minimum(ys, 1 - ys)
        img[..., :3] *= (0.85 + 0.3 * np.clip(edge * 4, 0, 1))[:, None, None]
        rim = (edge < 0.14).astype(np.float32)
        img = blend(img, rim[:, None] * np.ones((1, w), np.float32), PAL["gold"])
        img[0, :, :3] = PAL["gold_hi"]
        img[-1, :, :3] = PAL["gold_lo"]
        band = np.zeros((h, w), np.float32)
        gh = max(3, h - 6)
        band[3:3 + gh, :] = glyph_strip_mask(w, gh, seed, gw=3, gh=min(5, gh), spacing=2)
        c, _ = accent(variant)
        img = blend(img, band, c, alpha=GLOW(0.9))
        if variant == "p2":
            cr = crack_mask(w, h, seed + 3, 3, 20)
            img = blend(img, cr, PAL["violet_hi"], alpha=GLOW(1.0))
        return img
    return painter


def eye(seed=1):
    def painter(w, h, variant):
        img = blank(w, h, PAL["black"])
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = (w - 1) / 2, (h - 1) / 2
        r = np.sqrt(((xx - cx) / max(1, w / 2)) ** 2 + ((yy - cy) / max(1, h / 2)) ** 2)
        c, chi = accent(variant)
        iris = np.clip(1.0 - np.abs(r - 0.55) * 3.0, 0, 1)
        img = blend(img, (r < 0.85).astype(np.float32), c * 0.35, alpha=GLOW(0.5))
        img = blend(img, iris, c, alpha=GLOW(1.0))
        img = blend(img, (r < 0.3).astype(np.float32), chi, alpha=GLOW(1.0))
        pupil = ((np.abs(xx - cx) < max(0.6, w * 0.07)) & (r < 0.75)).astype(np.float32)
        img = blend(img, pupil, PAL["black"], alpha=GLOW(0.0) * 0 + 1.0)
        rim = ((r > 0.85) & (r < 1.05)).astype(np.float32)
        img = blend(img, rim, PAL["gold"], alpha=1.0)
        return img
    return painter


def sun(seed=17):
    def painter(w, h, variant):
        f1, f2 = worley(w, h, max(8, w * h // 90), seed)
        cells = np.clip(f1 * 1.3, 0, 1)
        if variant == "p1":
            core = hexc("fffbe6")
            mid = hexc("ffd25a")
            edge = hexc("ff8a1c")
            img = blank(w, h, core)
            img[..., :3] = core[None, None] * (1 - cells[..., None]) + mid[None, None] * cells[..., None]
            border = np.clip(1.0 - (f2 - f1) * 6, 0, 1)
            img = blend(img, border * 0.8, edge)
            img[..., 3] = GLOW(1.0)
        else:
            img = blank(w, h, hexc("060308"))
            border = np.clip(1.0 - (f2 - f1) * 5, 0, 1) ** 1.5
            img = blend(img, border, PAL["violet"], alpha=GLOW(1.0))
            hot = np.clip(1.0 - (f2 - f1) * 12, 0, 1) ** 2
            img = blend(img, hot, PAL["violet_hi"], alpha=GLOW(1.0))
            img[..., 3] = np.minimum(img[..., 3], GLOW(0.6))
        return img
    return painter


def light(color_p1="4fe8ff", color_p2="b35cff"):
    def painter(w, h, variant):
        c = hexc(color_p1) if variant == "p1" else hexc(color_p2)
        img = blank(w, h, c, GLOW(1.0))
        ys = (np.arange(h) + 0.5) / h
        core = 1.0 - np.abs(ys - 0.5) * 2
        img[..., :3] = c * (0.75 + 0.25 * core[:, None, None]) + (1 - c) * (core[:, None, None] ** 4) * 0.7
        return img
    return painter


def maw(seed=19):
    def painter(w, h, variant):
        n = fbm(w, h, 12, 3, seed)
        img = blank(w, h, PAL["crimson"])
        img[..., :3] *= (0.6 + 0.6 * n)[..., None]
        teeth = np.zeros((h, w), np.float32)
        tw = 5
        for x0 in range(0, w, tw):
            th = 5 + (x0 * 7 % 4)
            for k in range(th):
                half = (tw / 2) * (1 - k / th)
                for x in range(int(x0 + tw / 2 - half), int(x0 + tw / 2 + half) + 1):
                    if 0 <= x < w:
                        teeth[min(h - 1, k), x] = 1
                        teeth[max(0, h - 1 - k), x] = 1
        img = blend(img, teeth, PAL["ivory"])
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        c, chi = accent(variant)
        throat = np.clip(1 - r * 1.6, 0, 1)
        img = blend(img, throat, c, alpha=GLOW(1.0))
        img = blend(img, np.clip(1 - r * 3, 0, 1), chi, alpha=GLOW(1.0))
        return img
    return painter


def limb(seed=23):
    """Articulated limb: white armour segments over dark joints with piston rods."""
    def painter(w, h, variant):
        img = blank(w, h, hexc("23262c"))
        n = fbm(w, h, 16, 3, seed)
        rng = random.Random(seed)
        x = 0
        while x < w:
            pw = rng.choice([12, 14, 16])
            gap = 4
            seg = blank(min(pw, w - x), h, PAL["white"])
            ys = (np.arange(h) + 0.5) / h
            seg[..., :3] *= (0.86 + 0.22 * np.sin(ys * math.pi))[:, None, None]
            seg[0, :, :3] = PAL["white_hi"]
            seg[-1, :, :3] = PAL["white_lo"]
            seg[:, 0, :3] = PAL["white_lo"]
            seg[:, -1, :3] = PAL["seam"]
            seg[h // 2, 2:-2, :3] = PAL["gold"]
            img[:, x:x + seg.shape[1]] = seg
            jx = x + pw
            if jx < w:
                g = min(gap, w - jx)
                img[:, jx:jx + g, :3] = hexc("1a1c21")
                img[h // 3, jx:jx + g, :3] = hexc("aab2bd")
                img[2 * h // 3, jx:jx + g, :3] = hexc("aab2bd")
                if variant == "p2":
                    img[h // 2, jx:jx + g, :3] = PAL["violet"]
                    img[h // 2, jx:jx + g, 3] = GLOW(1.0)
            x += pw + gap
        img[..., :3] *= (0.92 + 0.1 * n)[..., None]
        if variant == "p2":
            cr = crack_mask(w, h, seed + 9, 3, 24)
            img = blend(img, cr * 0.9, PAL["violet_hi"], alpha=GLOW(0.8))
        return img
    return painter


def sail(seed=29):
    def painter(w, h, variant):
        img = blank(w, h, hexc("f2f0ea"))
        n = fbm(w, h, 20, 3, seed)
        img[..., :3] *= (0.92 + 0.1 * n)[..., None]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        # hex-ish cell lines
        a = np.abs(((xx / 6.0) + (yy / 10.4)) % 1.0 - 0.5)
        b = np.abs(((xx / 6.0) - (yy / 10.4)) % 1.0 - 0.5)
        lines = ((a < 0.07) | (b < 0.07) | ((yy % 10) < 0.8)).astype(np.float32)
        c, _ = accent(variant)
        img = blend(img, lines * 0.65, c * 0.85, alpha=GLOW(0.45))
        rim = ((xx < 2) | (xx > w - 3) | (yy < 2) | (yy > h - 3)).astype(np.float32)
        img = blend(img, rim, PAL["gold"])
        if variant == "p2":
            tear = crack_mask(w, h, seed + 4, 4, 30)
            img = blend(img, dilate(tear, 1), PAL["black"])
            img = blend(img, tear, PAL["violet_hi"], alpha=GLOW(1.0))
        return img
    return painter


def censer_tex(seed=31):
    def painter(w, h, variant):
        img = gold_trim(seed)(w, h, variant)
        img[..., :3] = img[..., :3] * 0.9 + PAL["brass"] * 0.1
        yy, xx = np.mgrid[0:h, 0:w]
        holes = (((xx % 6) == 3) & ((yy % 6) == 3)) | (((xx % 6) == 0) & ((yy % 6) == 0))
        c = hexc("ffb347") if variant == "p1" else PAL["violet"]
        img = blend(img, holes.astype(np.float32), c, alpha=GLOW(1.0))
        return img
    return painter


def dark(seed=37):
    def painter(w, h, variant):
        img = blank(w, h, hexc("15171c"))
        n = fbm(w, h, 8, 2, seed)
        img[..., :3] *= (0.8 + 0.4 * n)[..., None]
        return img
    return painter


# --------------------------------------------------------------------------- glow / shield passes (additive)

def glow_soft(w, h, variant):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx + 0.5 - w / 2) / (w / 2)) ** 2 + ((yy + 0.5 - h / 2) / (h / 2)) ** 2)
    v = np.clip(1.0 - r, 0, 1) ** 1.6
    img = blank(w, h, (1, 1, 1))
    img[..., :3] = v[..., None]
    img[..., 3] = v
    return img


def glow_strip(w, h, variant):
    ys = (np.arange(h) + 0.5) / h
    v = np.clip(1.0 - np.abs(ys - 0.5) * 2.0, 0, 1) ** 1.3
    img = blank(w, h, (1, 1, 1))
    img[..., :3] = v[:, None, None]
    img[..., 3] = v[:, None]
    return img


def glow_glyph(w, h, variant):
    m = glyph_strip_mask(w, h, 4242, gw=3, gh=min(5, h - 2), spacing=2)
    m = np.maximum(m, blur(m, 1, 1) * 0.6)
    img = blank(w, h, (1, 1, 1))
    img[..., :3] = m[..., None]
    img[..., 3] = m
    return img


def shield_hex(w, h, variant):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.abs(((xx / 8.0) + (yy / 13.86)) % 1.0 - 0.5)
    b = np.abs(((xx / 8.0) - (yy / 13.86)) % 1.0 - 0.5)
    c = np.abs((yy / 6.93) % 1.0 - 0.5)
    lines = np.clip(1.0 - np.minimum(np.minimum(a, b), c * 0.9) * 10, 0, 1)
    sp = (_rng(5).random((h, w)) < 0.02).astype(np.float32)
    v = np.clip(lines * 0.85 + sp, 0, 1)
    img = blank(w, h, (1, 1, 1))
    img[..., :3] = v[..., None]
    img[..., 3] = v
    return img


# --------------------------------------------------------------------------- output

def to_uint8(img: np.ndarray) -> np.ndarray:
    return np.clip(np.round(img * 255.0), 0, 255).astype(np.uint8)


def save_png(img: np.ndarray, path: str):
    from PIL import Image
    Image.fromarray(to_uint8(img), "RGBA").save(path, optimize=True)
