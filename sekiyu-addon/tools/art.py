"""
Procedural 2D art for the Sekiyu add-on (deterministic).

  particle_atlas()  128x128: glossy oil droplets, black smoke, 4-frame flame flipbook, ember / flash / ring / bubble
  core_icon()       32x32 item sprite of the Crude Core (control item)
  ui_icon(name)     32x32 Oil Console icons (8 abilities + logia / hud / guide)
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CELL = 32
ATLAS = 128
ATLAS_CELLS = {
    "drop0": (0, 0), "drop1": (1, 0), "drop2": (2, 0), "drop3": (3, 0),
    "smoke0": (0, 1), "smoke1": (1, 1), "smoke2": (2, 1), "smoke3": (3, 1),
    "flame0": (0, 2), "flame1": (1, 2), "flame2": (2, 2), "flame3": (3, 2),
    "ember": (0, 3), "flash": (1, 3), "ring": (2, 3), "bubble": (3, 3),
}


def _noise(size, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = 2 ** (o + 2)
        g = Image.fromarray((rng.random((n + 1, n + 1)) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        out += np.asarray(g, np.float32) / 255 * amp
        tot += amp
        amp *= 0.5
    return out / tot


def _grid(size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    return xx / (size - 1) * 2 - 1, yy / (size - 1) * 2 - 1


def droplet(seed):
    """Glossy crude droplet: near-black body, warm amber rim light, white specular dot."""
    rng = np.random.default_rng(seed)
    x, y = _grid(CELL)
    sx, sy = rng.uniform(0.75, 1.0), rng.uniform(0.85, 1.15)
    r = np.sqrt((x / sx) ** 2 + ((y - 0.05) / sy) ** 2 * (1 + 0.35 * (y > 0)))
    a = np.clip((0.82 - r) * 9, 0, 1)
    body = np.stack([0.06 + 0.10 * (1 - r), 0.04 + 0.05 * (1 - r), 0.03 + 0.02 * (1 - r)], -1)
    rim = np.clip(1 - np.abs(r - 0.66) * 9, 0, 1) * np.clip(x * 0.6 + y * 0.8 + 0.3, 0, 1)
    body += rim[..., None] * np.array([0.95, 0.55, 0.12]) * 0.8
    spec = np.exp(-(((x + 0.3) / 0.13) ** 2 + ((y + 0.35) / 0.1) ** 2))
    body += spec[..., None] * 0.9
    return np.dstack([np.clip(body, 0, 1), a])


def smoke(seed):
    rng = np.random.default_rng(seed)
    x, y = _grid(CELL)
    dens = np.zeros_like(x)
    for _ in range(6):
        cx, cy = rng.uniform(-0.3, 0.3, 2)
        rr = rng.uniform(0.45, 0.65)
        dens += np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * (rr * 0.55) ** 2))
    dens /= dens.max()
    n = _noise(CELL, seed + 5)
    a = np.clip((dens * (0.6 + 0.8 * n) - 0.2) * 1.5, 0, 1) * np.clip((1 - np.sqrt(x * x + y * y)) * 1.6, 0, 1)
    shade = 0.16 + 0.12 * n
    return np.dstack([np.stack([shade, shade * 0.95, shade * 0.9], -1), a])


def flame(frame):
    """Flame tongue (white-yellow core -> orange -> red edge), 4 frames of flicker."""
    x, y = _grid(CELL)
    n = _noise(CELL, 100 + frame * 7, 3)
    yy = (y + 1) / 2  # 0 top .. 1 bottom
    width = 0.15 + 0.6 * np.clip(yy, 0, 1) ** 0.8
    xs = x + (n - 0.5) * 0.5 * (1 - yy) + math.sin(frame * 1.7) * 0.08 * (1 - yy)
    d = np.abs(xs) / width
    tip = np.clip((yy - 0.05 - 0.12 * n) * 4, 0, 1)
    base = np.clip((1.0 - yy) * 8, 0, 1)
    a = np.clip(1 - d, 0, 1) ** 0.8 * tip * base
    t = np.clip(1 - d * 1.2, 0, 1) * np.clip(yy * 1.4, 0, 1)
    col = np.stack([np.ones_like(t), 0.25 + 0.7 * t, 0.05 + 0.6 * t ** 2], -1)
    return np.dstack([col, a])


def glow(core, halo, sharp):
    x, y = _grid(CELL)
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - r, 0, 1) ** sharp
    t = np.clip(1 - r * 2.2, 0, 1)[..., None]
    return np.dstack([np.array(halo) * (1 - t) + np.array(core) * t, a])


def ring(width=0.12, color=(0.12, 0.08, 0.05)):
    x, y = _grid(CELL)
    r = np.sqrt(x * x + y * y)
    a = np.exp(-((r - 0.8) ** 2) / (2 * width ** 2))
    return np.dstack([np.ones((CELL, CELL, 3)) * np.array(color), np.clip(a, 0, 1)])


def bubble():
    x, y = _grid(CELL)
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - np.abs(r - 0.72) * 8, 0, 1) * 0.9 + np.clip((0.72 - r) * 3, 0, 1) * 0.35
    col = np.stack([0.12 + 0.6 * (r > 0.6), 0.08 + 0.35 * (r > 0.6), 0.04 + 0.1 * (r > 0.6)], -1)
    spec = np.exp(-(((x + 0.3) / 0.12) ** 2 + ((y + 0.35) / 0.1) ** 2))
    return np.dstack([np.clip(col + spec[..., None], 0, 1), np.clip(a + spec, 0, 1)])


def particle_atlas() -> Image.Image:
    sheet = np.zeros((ATLAS, ATLAS, 4), np.float32)

    def put(name, arr):
        c, r = ATLAS_CELLS[name]
        sheet[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = arr

    for i in range(4):
        put(f"drop{i}", droplet(11 + i * 13))
        put(f"smoke{i}", smoke(51 + i * 9))
        put(f"flame{i}", flame(i))
    put("ember", glow((1, 0.95, 0.7), (1, 0.35, 0.05), 2.6))
    put("flash", glow((1, 1, 0.9), (1, 0.6, 0.2), 1.3))
    put("ring", ring())
    put("bubble", bubble())
    a = sheet[..., 3:4]
    sheet[..., :3] = np.where(a < 1e-3, sheet[..., :3] * 0 + 0.1, sheet[..., :3])
    return Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8), "RGBA")


# --------------------------------------------------------------------------- icons

OIL = (16, 10, 8, 255)
OIL_HI = (70, 40, 22, 255)
AMBER = (250, 165, 40, 255)
FIRE = (255, 90, 20, 255)
OUTLINE = (8, 4, 2, 255)


def core_icon(size=32):
    s = 8
    W = size * s
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = W / 2
    # droplet-shaped orb of crude with glowing fissures and a hanging drip
    d.ellipse([c - 12.5 * s, c - 10 * s, c + 12.5 * s, c + 13 * s], fill=OUTLINE)
    d.polygon([(c, c - 15 * s), (c - 8 * s, c - 4 * s), (c + 8 * s, c - 4 * s)], fill=OUTLINE)
    d.ellipse([c - 11 * s, c - 8.6 * s, c + 11 * s, c + 11.6 * s], fill=OIL)
    d.polygon([(c, c - 13.4 * s), (c - 6.5 * s, c - 4 * s), (c + 6.5 * s, c - 4 * s)], fill=OIL)
    for k, (a0, a1) in enumerate(((200, 300), (20, 120))):
        r = (5.5 + k * 2.5) * s
        d.arc([c - r, c + 1.5 * s - r, c + r, c + 1.5 * s + r], a0, a1, fill=AMBER, width=int(1.4 * s))
    d.line([(c - 4 * s, c + 4 * s), (c, c + 1 * s), (c + 3 * s, c + 5 * s)], fill=FIRE, width=int(1.2 * s))
    d.ellipse([c - 7 * s, c - 5 * s, c - 3 * s, c - 2 * s], fill=(255, 235, 200, 255))
    small = img.resize((size, size), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32) / 255
    arr[..., 3] = (arr[..., 3] > 0.45).astype(np.float32)
    for (x, y) in ((22, 27), (22, 28), (22, 29), (21, 30), (22, 30), (23, 30)):
        arr[y, x] = [0.95, 0.6, 0.15, 1]
    return Image.fromarray((arr * 255).astype(np.uint8), "RGBA")


def _badge(d, W, col):
    d.ellipse([W * 0.04, W * 0.04, W * 0.96, W * 0.96], fill=(14, 8, 6, 255), outline=(200, 120, 30, 255), width=int(W * 0.07))
    # warm amber background so the black oil shapes read clearly on a phone
    d.ellipse([W * 0.14, W * 0.14, W * 0.86, W * 0.86], fill=tuple(int(200 * 0.75 + c * 0.25) for c in col[:3]) + (255,))


UI_COLORS = {"tide": (90, 70, 50), "body": (60, 50, 40), "geyser": (120, 80, 40), "prison": (80, 60, 40), "jet": (140, 100, 50),
             "serpent": (100, 60, 30), "seep": (60, 60, 60), "inferno": (255, 80, 20), "logia": (90, 70, 50), "hud": (120, 200, 255),
             "guide": (255, 220, 140)}
UI_ICONS = list(UI_COLORS)


def ui_icon(name, size=32):
    s = 8
    W = size * s
    u = W / 32
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _badge(d, W, UI_COLORS[name])

    def blob(cx, cy, r, fill=OIL, hi=True):
        d.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], fill=fill)
        if hi:
            d.ellipse([(cx - r * 0.55) * u, (cy - r * 0.6) * u, (cx - r * 0.15) * u, (cy - r * 0.25) * u], fill=(250, 200, 120, 255))

    if name == "tide":
        d.polygon([(6 * u, 24 * u), (9 * u, 14 * u), (15 * u, 8 * u), (23 * u, 8 * u), (26 * u, 12 * u), (20 * u, 12 * u), (17 * u, 16 * u), (16 * u, 24 * u)], fill=OIL)
        d.line([(15 * u, 8 * u), (23 * u, 8 * u), (26 * u, 12 * u)], fill=AMBER, width=int(1.5 * u))
    elif name == "body":
        d.rectangle([12 * u, 7 * u, 20 * u, 15 * u], fill=OIL)
        d.rectangle([11 * u, 15 * u, 21 * u, 25 * u], fill=OIL)
        d.rectangle([13.5 * u, 10 * u, 15 * u, 11 * u], fill=AMBER)
        d.rectangle([17 * u, 10 * u, 18.5 * u, 11 * u], fill=AMBER)
        for x in (12, 16, 20):
            d.rectangle([x * u, 25 * u, (x + 1.2) * u, 27.5 * u], fill=OIL)
    elif name == "geyser":
        d.rectangle([13 * u, 9 * u, 19 * u, 25 * u], fill=OIL)
        for x, y in ((10, 8), (16, 5), (22, 8), (12, 12), (20, 12)):
            blob(x, y, 2.2)
        d.ellipse([7 * u, 23 * u, 25 * u, 27 * u], fill=OIL)
    elif name == "prison":
        for i in range(5):
            x = 8 + i * 4
            d.line([(x * u, 26 * u), ((x + (16 - x) * 0.5) * u, 8 * u)], fill=OIL, width=int(2.6 * u))
        blob(16, 19, 3, fill=(200, 60, 30, 255), hi=False)
    elif name == "jet":
        d.polygon([(8 * u, 13 * u), (20 * u, 10 * u), (26 * u, 16 * u), (20 * u, 22 * u), (8 * u, 19 * u)], fill=OIL)
        for i, y in enumerate((12, 16, 20)):
            d.line([(4 * u, y * u), ((9 - i) * u, y * u)], fill=AMBER, width=int(1.4 * u))
    elif name == "serpent":
        pts = [(8 + i * 1.6, 22 - 7 * math.sin(i * 0.7)) for i in range(10)]
        d.line([(x * u, y * u) for x, y in pts], fill=OIL, width=int(4 * u))
        blob(24, 9, 3.6)
        d.rectangle([23 * u, 7.5 * u, 24.4 * u, 8.7 * u], fill=AMBER)
    elif name == "seep":
        d.ellipse([6 * u, 18 * u, 26 * u, 25 * u], fill=OIL)
        d.ellipse([12 * u, 15 * u, 20 * u, 21 * u], fill=OIL)
        d.rectangle([13.5 * u, 17 * u, 15 * u, 18 * u], fill=AMBER)
        d.rectangle([17 * u, 17 * u, 18.5 * u, 18 * u], fill=AMBER)
    elif name == "inferno":
        for i, x in enumerate((9, 16, 23)):
            h = 14 if i == 1 else 10
            d.polygon([((x - 4) * u, 25 * u), (x * u, (25 - h - 6) * u), ((x + 4) * u, 25 * u)], fill=FIRE)
            d.polygon([((x - 2) * u, 25 * u), (x * u, (25 - h) * u), ((x + 2) * u, 25 * u)], fill=(255, 220, 120, 255))
        d.ellipse([6 * u, 23 * u, 26 * u, 27 * u], fill=OIL)
    elif name == "logia":
        d.ellipse([10 * u, 6 * u, 22 * u, 18 * u], fill=OIL)
        d.polygon([(10 * u, 13 * u), (22 * u, 13 * u), (16 * u, 27 * u)], fill=OIL)
        d.arc([12 * u, 8 * u, 20 * u, 16 * u], 200, 300, fill=AMBER, width=int(1.4 * u))
    elif name == "hud":
        d.rectangle([7 * u, 13 * u, 25 * u, 19 * u], outline=(240, 240, 240, 255), width=int(u))
        d.rectangle([8.5 * u, 14.5 * u, 19 * u, 17.5 * u], fill=AMBER)
    elif name == "guide":
        d.rectangle([9 * u, 7 * u, 23 * u, 25 * u], fill=(235, 220, 180, 255), outline=(90, 55, 25, 255), width=int(u))
        for y in (11, 14, 17, 20):
            d.line([11.5 * u, y * u, 20.5 * u, y * u], fill=(60, 35, 20, 255), width=int(u))
    return img.resize((size, size), Image.LANCZOS).filter(ImageFilter.SHARPEN)
