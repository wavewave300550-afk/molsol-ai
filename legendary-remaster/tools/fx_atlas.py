"""
Paint the particle atlas textures/particle/legends_fx.png in HD (512x512, 128 px per cell) with
the same 4x4 layout the particle JSON uses (UV units stay 128x128, 32 per cell). White/grey
sprites - the particles tint them. Cells:
  row 0: glow, star, magic ring (telegraph outline), magic disc (telegraph fill)
  row 1: spark streak, slash arc, flame, feather
  row 2: petal, rune seal, smoke puff, crystal shard
  row 3: twinkle, crescent, droplet, spiral
"""
import math
import sys

import numpy as np
from PIL import Image

C = 128
N = 4


def grid():
    y, x = np.mgrid[0:C, 0:C].astype(np.float32)
    return (x + 0.5) / C - 0.5, (y + 0.5) / C - 0.5      # -0.5..0.5


def soft(d, w):
    return np.clip(1.0 - d / np.maximum(1e-6, w), 0.0, 1.0)


def noise(seed, scale=8):
    rng = np.random.default_rng(seed)
    acc = np.zeros((C, C), np.float32)
    amp = 1.0
    for o in range(4):
        n = 2 ** o * scale // 8 + 2
        g = rng.random((n, n)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((C, C), Image.BICUBIC)
        acc += np.asarray(img, np.float32) / 255.0 * amp
        amp *= 0.5
    return acc / 1.875


def cell_glow():
    x, y = grid()
    r = np.hypot(x, y) * 2
    a = np.exp(-(r ** 2) * 6.0) * 0.85 + np.exp(-(r ** 2) * 40.0) * 0.6
    return np.clip(a, 0, 1), np.clip(0.75 + np.exp(-(r ** 2) * 30) * 0.25, 0, 1)


def cell_star():
    x, y = grid()
    r = np.hypot(x, y) * 2
    ang = np.arctan2(y, x)
    rays = np.exp(-np.abs(x) * 60) * soft(np.abs(y) * 2, 1.0) + np.exp(-np.abs(y) * 60) * soft(np.abs(x) * 2, 1.0)
    diag = (np.exp(-np.abs(x - y) * 70) + np.exp(-np.abs(x + y) * 70)) * soft(r, 0.6) * 0.5
    core = np.exp(-(r ** 2) * 50)
    halo = np.exp(-(r ** 2) * 8) * 0.35
    return np.clip(rays + diag + core + halo, 0, 1), np.ones_like(r)


def cell_ring():
    x, y = grid()
    r = np.hypot(x, y) * 2
    ang = np.arctan2(y, x)
    outer = np.exp(-((r - 0.9) / 0.035) ** 2)
    inner = np.exp(-((r - 0.78) / 0.018) ** 2) * 0.8
    ticks = (np.abs(np.sin(ang * 12)) > 0.93) * ((r > 0.8) & (r < 0.88)) * 0.9
    glow = np.exp(-((r - 0.9) / 0.12) ** 2) * 0.35
    return np.clip(outer + inner + ticks + glow, 0, 1), np.ones_like(r)


def cell_disc():
    x, y = grid()
    r = np.hypot(x, y) * 2
    ang = np.arctan2(y, x)
    fill = np.clip(r, 0, 1) ** 2 * 0.55 * (r < 0.96)
    rim = np.exp(-((r - 0.93) / 0.04) ** 2)
    band = np.exp(-((r - 0.62) / 0.02) ** 2) * 0.7
    runes = ((r > 0.66) & (r < 0.86)) * (np.abs(np.sin(ang * 8 + np.sin(r * 30))) > 0.82) * 0.55
    star = (np.abs(np.sin(ang * 3)) * 0.55 > np.abs(r - 0.32) * 4) * (r < 0.6) * 0.25
    return np.clip(fill + rim + band + runes + star, 0, 1), np.ones_like(r)


def cell_streak():
    x, y = grid()
    a = np.exp(-(x / 0.035) ** 2) * soft(np.abs(y), 0.48) ** 1.5
    a += np.exp(-(x / 0.012) ** 2) * soft(np.abs(y), 0.4)
    return np.clip(a, 0, 1), np.ones_like(x)


def cell_slash():
    x, y = grid()
    cy = 0.18
    r = np.hypot(x, y - cy) * 2
    ang = np.arctan2(-(y - cy), x)
    t = np.clip(ang / math.pi, 0, 1)
    shape = np.clip(np.sin(t * math.pi), 0, 1)
    thick = 0.02 + 0.1 * shape
    band = np.exp(-((r - 0.74) / thick) ** 2) * (ang > 0)
    core = np.exp(-((r - 0.76) / (0.015 + 0.03 * shape)) ** 2) * (ang > 0) * shape
    return np.clip(band * shape ** 0.5 + core, 0, 1), np.clip(0.8 + core * 0.2, 0, 1)


def cell_flame():
    x, y = grid()
    n = noise(11, 10)
    yy = y + 0.05
    width = 0.32 * np.clip((yy + 0.45) / 0.9, 0, 1) ** 0.6 * np.clip((0.45 - yy) / 0.25, 0, 1) ** 0.4
    wob = x + (n - 0.5) * 0.18 * np.clip(0.45 - yy, 0, 1)
    body = soft(np.abs(wob), np.maximum(width, 1e-3))
    core = soft(np.hypot(wob / 0.12, (yy - 0.2) / 0.22), 1.0)
    a = np.clip(body * (0.55 + n * 0.6) + core * 0.6, 0, 1) * (yy > -0.46)
    return a, np.clip(0.7 + core * 0.3, 0, 1)


def cell_feather():
    x, y = grid()
    yy = y
    half = 0.2 * np.clip(np.sin(np.clip((0.46 - yy) / 0.92, 0, 1) * math.pi), 0, 1) ** 0.8
    vane = soft(np.abs(x), np.maximum(half, 1e-3)) ** 0.3 * (np.abs(x) < half)
    barbs = 0.75 + 0.25 * np.cos((yy * 1.0 + np.abs(x) * 0.7) * 120)
    rachis = np.exp(-(x / 0.012) ** 2) * (yy > -0.48) * (yy < 0.48)
    a = np.clip(vane * barbs + rachis, 0, 1)
    return a, np.clip(0.85 + rachis * 0.15 - np.abs(x) * 0.3, 0, 1)


def cell_petal():
    x, y = grid()
    yy = y * 1.15
    w = 0.3 * np.clip(np.sin(np.clip((yy + 0.45) / 0.9, 0, 1) * math.pi), 0, 1) ** 0.6
    notch = np.exp(-((x / 0.05) ** 2 + ((yy + 0.42) / 0.06) ** 2))
    a = soft(np.abs(x), np.maximum(w, 1e-3)) ** 0.5 * (np.abs(x) < w) * (1 - notch)
    vein = np.exp(-(x / 0.015) ** 2) * 0.25
    return np.clip(a, 0, 1), np.clip(0.95 - vein - np.abs(x), 0.6, 1)


def cell_rune():
    x, y = grid()
    r = np.hypot(x, y) * 2
    ang = np.arctan2(y, x)
    circ = np.exp(-((r - 0.82) / 0.04) ** 2)
    tri = np.zeros_like(r)
    for k in range(3):
        a0 = k * 2 * math.pi / 3 - math.pi / 2
        nx, ny = math.cos(a0), math.sin(a0)
        d = x * nx + y * ny
        tri += np.exp(-((d - (-0.2)) / 0.02) ** 2) * (r < 0.82)
    dots = sum(np.exp(-(((x - 0.36 * math.cos(a)) ** 2 + (y - 0.36 * math.sin(a)) ** 2) / 0.0012)) for a in np.linspace(0, 2 * math.pi, 7)[:-1])
    glyph = np.exp(-(x / 0.018) ** 2) * (np.abs(y) < 0.18) + np.exp(-((y - 0.0) / 0.018) ** 2) * (np.abs(x) < 0.1)
    a = circ + tri * 0.8 + dots + glyph + np.exp(-(r ** 2) * 6) * 0.15
    return np.clip(a, 0, 1), np.ones_like(r)


def cell_smoke():
    x, y = grid()
    n = noise(23, 12)
    r = np.hypot(x, y) * 2
    blob = np.zeros_like(r)
    rng = np.random.default_rng(5)
    for _ in range(9):
        cx, cy, rr = rng.uniform(-0.16, 0.16), rng.uniform(-0.16, 0.16), rng.uniform(0.22, 0.33)
        blob = np.maximum(blob, soft(np.hypot(x - cx, y - cy), rr) ** 0.9)
    a = np.clip(blob * (0.65 + n * 0.55), 0, 1) * soft(r, 1.0) ** 0.5
    return a, np.clip(0.8 + n * 0.2, 0, 1)


def cell_shard():
    x, y = grid()
    pts = [(0.0, -0.46), (0.17, -0.05), (0.08, 0.44), (-0.12, 0.3), (-0.2, -0.1)]
    inside = np.ones_like(x, bool)
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        inside &= ((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) >= 0
    facet = np.where(x > 0.02 * (y + 0.46), 1.0, 0.72)
    edge = np.exp(-(np.abs(x - 0.02 * (y + 0.46)) / 0.01) ** 2) * 0.3
    a = inside.astype(np.float32)
    return a, np.clip(facet + edge, 0, 1)


def cell_twinkle():
    x, y = grid()
    r = np.hypot(x, y) * 2
    rays = np.exp(-np.abs(x) * 90) * soft(np.abs(y) * 2, 0.9) + np.exp(-np.abs(y) * 90) * soft(np.abs(x) * 2, 0.9)
    return np.clip(rays + np.exp(-(r ** 2) * 60) + np.exp(-(r ** 2) * 10) * 0.3, 0, 1), np.ones_like(r)


def cell_crescent():
    x, y = grid()
    r1 = np.hypot(x, y) * 2
    r2 = np.hypot(x - 0.16, y - 0.05) * 2
    a = soft(r1, 0.85) ** 0.3 * (r1 < 0.85) * np.clip((r2 - 0.62) / 0.12, 0, 1)
    glow = np.exp(-((r1 - 0.78) / 0.12) ** 2) * (r2 > 0.6) * 0.4
    return np.clip(a + glow, 0, 1), np.ones_like(x)


def cell_drip():
    x, y = grid()
    yy = y
    w = np.where(yy > 0.12, np.sqrt(np.clip(0.3 ** 2 - (yy - 0.18) ** 2, 0, None)), 0.3 * np.clip((yy + 0.45) / 0.6, 0, 1) ** 1.6)
    a = soft(np.abs(x), np.maximum(w, 1e-3)) ** 0.25 * (np.abs(x) < w)
    hl = np.exp(-(((x + 0.09) / 0.05) ** 2 + ((yy - 0.15) / 0.08) ** 2))
    return np.clip(a, 0, 1), np.clip(0.75 + hl * 0.25 - x * 0.3, 0, 1)


def cell_spiral():
    x, y = grid()
    r = np.hypot(x, y) * 2
    ang = np.arctan2(y, x)
    s = np.mod(r * 3.2 - ang / (2 * math.pi), 1.0)
    arm = np.exp(-((s - 0.5) / 0.08) ** 2) * (r < 0.95) * (r > 0.05)
    return np.clip(arm + np.exp(-(r ** 2) * 30) * 0.6, 0, 1), np.clip(0.7 + (1 - r) * 0.3, 0, 1)


CELLS = [[cell_glow, cell_star, cell_ring, cell_disc],
         [cell_streak, cell_slash, cell_flame, cell_feather],
         [cell_petal, cell_rune, cell_smoke, cell_shard],
         [cell_twinkle, cell_crescent, cell_drip, cell_spiral]]


def paint(path):
    out = np.zeros((C * N, C * N, 4), np.float32)
    for row in range(N):
        for col in range(N):
            a, lum = CELLS[row][col]()
            pad = np.ones_like(a)
            pad[:2, :] = pad[-2:, :] = 0
            pad[:, :2] = pad[:, -2:] = 0        # keep a clear border so neighbours never bleed in
            a = a * pad
            out[row * C:(row + 1) * C, col * C:(col + 1) * C, 0] = lum
            out[row * C:(row + 1) * C, col * C:(col + 1) * C, 1] = lum
            out[row * C:(row + 1) * C, col * C:(col + 1) * C, 2] = lum
            out[row * C:(row + 1) * C, col * C:(col + 1) * C, 3] = a
    img = Image.fromarray((np.clip(np.nan_to_num(out), 0, 1) * 255).astype(np.uint8), "RGBA")
    img.save(path)
    return path


if __name__ == "__main__":
    print(paint(sys.argv[1]))
