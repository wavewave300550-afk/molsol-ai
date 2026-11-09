"""
Procedural textures for the Jōki Jōki no Mi add-on (everything except the fruit, see fruit_icon.py).

  particle_atlas()  128x128 steam / jet / ring / ember sheet used by every particle
  valve_icon()      32x32 item sprite of the Steam Valve (control item)
  ui_icon(name)     32x32 Steam Console button icons (9 abilities, 3 gears, HUD, guide)

All drawing is deterministic (fixed RNG seeds) so rebuilding gives identical files.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# --------------------------------------------------------------------------- helpers


def _rgba(arr):
    return Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGBA")


def _noise(size, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = 2 ** (o + 2)
        g = rng.random((n + 1, n + 1)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        out += np.asarray(img, np.float32) / 255.0 * amp
        total += amp
        amp *= 0.5
    return out / total


def puff(size, seed, lobes=6, dense=False):
    """Soft cloud blob: a few overlapping gaussian lobes eroded by fractal noise."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / (size - 1) * 2 - 1
    dens = np.zeros((size, size), np.float32)
    for _ in range(lobes):
        cx, cy = rng.uniform(-0.3, 0.3, 2)
        r = rng.uniform(0.5, 0.7) * (1.12 if dense else 1.0)
        dens += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (r * 0.55) ** 2))
    dens /= dens.max()
    n = _noise(size, seed + 99)
    a = np.clip((dens * (0.6 + 0.8 * n) - 0.18) * (1.9 if dense else 1.45), 0, 1)
    edge = np.clip((1 - np.sqrt(xx ** 2 + yy ** 2)) * 1.6, 0, 1) ** 0.8
    a *= edge
    shade = 0.82 + 0.18 * np.clip(1 - (yy + 0.4) * 0.6, 0, 1) * n  # lighter on top, subtle texture
    rgb = np.stack([shade, shade, shade * 1.02], -1)
    return np.dstack([rgb, a])


def streak(w, h, warm=False):
    """Horizontal jet streak: bright head on the right, fading tail to the left."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / (w - 1)
    v = (yy - (h - 1) / 2) / ((h - 1) / 2)
    thick = 0.12 + 0.45 * u ** 0.7
    head = np.clip((1 - u) / 0.22, 0, 1) ** 0.6  # rounded, soft head
    a = np.clip(1 - (v / thick) ** 2, 0, 1) ** 1.3 * (u ** 1.1) * head
    if warm:
        rgb = np.stack([np.ones_like(u), 0.75 + 0.25 * u, 0.55 + 0.45 * u], -1)
    else:
        rgb = np.stack([0.9 + 0.1 * u, 0.93 + 0.07 * u, np.ones_like(u)], -1)
    return np.dstack([rgb, a])


def ring(size, width=0.12):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / (size - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    a = np.exp(-((r - 0.82) ** 2) / (2 * width ** 2))
    n = _noise(size, 7)
    a *= 0.6 + 0.5 * n
    rgb = np.ones((size, size, 3), np.float32)
    return np.dstack([rgb, np.clip(a, 0, 1)])


def glow(size, core=(1.0, 0.95, 0.8), halo=(1.0, 0.45, 0.1), sharp=2.0):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / (size - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip(1 - r, 0, 1) ** sharp
    t = np.clip(1 - r * 2.2, 0, 1)[..., None]
    rgb = np.array(halo) * (1 - t) + np.array(core) * t
    return np.dstack([rgb, a])


def wisp(size, seed):
    """Thin curling vapour strand (cooling / shimmer)."""
    rng = np.random.default_rng(seed)
    img = Image.new("L", (size * 4, size * 4), 0)
    d = ImageDraw.Draw(img)
    pts = []
    ph = rng.uniform(0, math.tau)
    for i in range(40):
        t = i / 39
        x = size * 2 + math.sin(t * 5 + ph) * size * 0.7 * (0.3 + t)
        y = size * 4 * (1 - t)
        pts.append((x, y))
    d.line(pts, fill=255, width=size // 3)
    img = img.filter(ImageFilter.GaussianBlur(size * 0.18)).resize((size, size), Image.LANCZOS)
    a = np.asarray(img, np.float32) / 255.0
    return np.dstack([np.ones((size, size, 3), np.float32), a * 0.9])


# --------------------------------------------------------------------------- particle atlas

ATLAS = 128
CELL = 32
# name -> (col, row) in 32px cells, used by build.py to compute UVs
ATLAS_CELLS = {
    "puff0": (0, 0), "puff1": (1, 0), "puff2": (2, 0), "puff3": (3, 0),
    "billow0": (0, 1), "billow1": (1, 1), "billow2": (2, 1), "billow3": (3, 1),
    "streak": (0, 2), "ring": (1, 2), "ember": (2, 2), "flash": (3, 2),
    "hot_streak": (0, 3), "wisp0": (1, 3), "wisp1": (2, 3), "shimmer": (3, 3),
}


def particle_atlas():
    sheet = np.zeros((ATLAS, ATLAS, 4), np.float32)

    def put(name, arr):
        c, r = ATLAS_CELLS[name]
        sheet[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = arr

    for i in range(4):
        put(f"puff{i}", puff(CELL, 11 + i * 17, lobes=5 + i))
        put(f"billow{i}", puff(CELL, 301 + i * 23, lobes=7 + i, dense=True))
    put("streak", streak(CELL, CELL))
    put("ring", ring(CELL))
    put("ember", glow(CELL, core=(1.0, 0.95, 0.7), halo=(1.0, 0.35, 0.05), sharp=2.6))
    put("flash", glow(CELL, core=(1.0, 1.0, 1.0), halo=(1.0, 0.75, 0.45), sharp=1.4))
    put("hot_streak", streak(CELL, CELL, warm=True))
    put("wisp0", wisp(CELL, 5))
    put("wisp1", wisp(CELL, 9))
    sh = wisp(CELL, 21)
    sh[..., 0], sh[..., 1], sh[..., 2] = 1.0, 0.55, 0.25
    sh[..., 3] *= 0.6
    put("shimmer", sh)
    # premultiplied-edge cleanup: fully transparent texels get the cell's colour (no dark halos)
    a = sheet[..., 3:4]
    sheet[..., :3] = np.where(a < 1e-3, np.clip(sheet[..., :3] + 0.9, 0, 1), sheet[..., :3])
    return _rgba(sheet)


# --------------------------------------------------------------------------- item: steam valve

BRONZE = (184, 115, 51)
BRONZE_D = (110, 62, 26)
BRONZE_L = (232, 170, 92)
RED = (200, 30, 24)
RED_D = (120, 14, 12)
HOT = (255, 170, 60)
OUTLINE = (34, 14, 8)


def valve_icon(size=32):
    """A bronze hand-wheel valve on a red-hot boiler cap, venting a white jet."""
    s = 8  # supersample
    W = size * s
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = W / 2
    # boiler cap
    d.ellipse([c - 9.5 * s, c - 9.5 * s, c + 9.5 * s, c + 9.5 * s], fill=RED_D + (255,), outline=OUTLINE + (255,), width=s)
    d.ellipse([c - 8 * s, c - 8 * s, c + 8 * s, c + 8 * s], fill=RED + (255,))
    d.ellipse([c - 5 * s, c - 5 * s, c + 5 * s, c + 5 * s], fill=HOT + (255,))
    # wheel rim + spokes
    d.ellipse([c - 13 * s, c - 13 * s, c + 13 * s, c + 13 * s], outline=OUTLINE + (255,), width=int(4.4 * s))
    d.ellipse([c - 12.6 * s, c - 12.6 * s, c + 12.6 * s, c + 12.6 * s], outline=BRONZE + (255,), width=int(3 * s))
    d.arc([c - 12.2 * s, c - 12.2 * s, c + 12.2 * s, c + 12.2 * s], 200, 320, fill=BRONZE_L + (255,), width=int(1.2 * s))
    for k in range(5):
        a = math.radians(k * 72 - 90)
        x0, y0 = c + math.cos(a) * 3.5 * s, c + math.sin(a) * 3.5 * s
        x1, y1 = c + math.cos(a) * 11.5 * s, c + math.sin(a) * 11.5 * s
        d.line([x0, y0, x1, y1], fill=OUTLINE + (255,), width=int(3.2 * s))
        d.line([x0, y0, x1, y1], fill=BRONZE + (255,), width=int(1.8 * s))
    # hub with rivet
    d.ellipse([c - 4 * s, c - 4 * s, c + 4 * s, c + 4 * s], fill=BRONZE_D + (255,), outline=OUTLINE + (255,), width=s)
    d.ellipse([c - 2 * s, c - 2.4 * s, c + 1.2 * s, c + 0.8 * s], fill=BRONZE_L + (255,))
    small = img.resize((size, size), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32) / 255
    arr[..., 3] = (arr[..., 3] > 0.45).astype(np.float32)
    # steam jet escaping top-right
    for i, (x, y) in enumerate([(24, 6), (26, 4), (27, 2), (29, 3), (28, 1), (25, 3)]):
        if 0 <= x < size and 0 <= y < size:
            arr[y, x] = [0.95, 0.96, 1.0, 1.0] if i < 4 else [0.8, 0.82, 0.88, 1.0]
    return _rgba(arr)


# --------------------------------------------------------------------------- UI icons

UI_COLORS = {
    "boost": (255, 170, 60), "dash": (240, 240, 245), "jump": (240, 240, 245), "cannon": (255, 120, 60),
    "scald": (255, 90, 50), "knuckle": (255, 200, 120), "kick": (255, 200, 120), "mist": (220, 225, 235),
    "redline": (255, 40, 30), "mode_1": (170, 170, 170), "mode_2": (255, 165, 40), "mode_3": (240, 60, 40),
    "hud": (120, 220, 255), "guide": (255, 220, 140),
}


def _badge(d, W, col):
    d.ellipse([W * 0.04, W * 0.04, W * 0.96, W * 0.96], fill=(30, 12, 10, 255), outline=(184, 115, 51, 255), width=int(W * 0.07))
    d.ellipse([W * 0.14, W * 0.14, W * 0.86, W * 0.86], fill=tuple(int(c * 0.35) for c in col) + (255,))


def ui_icon(name, size=32):
    s = 8
    W = size * s
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = UI_COLORS[name]
    fg = col + (255,)
    white = (245, 245, 250, 255)
    _badge(d, W, col)
    u = W / 32

    def cloud(cx, cy, r, fill=white):
        for dx, dy, k in ((-0.9, 0.2, 0.8), (0, -0.3, 1.0), (0.9, 0.2, 0.8), (0, 0.4, 0.9)):
            rr = r * k
            d.ellipse([(cx + dx * r - rr) * u, (cy + dy * r - rr) * u, (cx + dx * r + rr) * u, (cy + dy * r + rr) * u], fill=fill)

    if name == "boost":
        d.polygon([(16 * u, 6 * u), (22 * u, 15 * u), (18 * u, 15 * u), (20 * u, 26 * u), (10 * u, 13 * u), (14.5 * u, 13 * u)], fill=fg)
    elif name == "dash":
        for i, y in enumerate((11, 16, 21)):
            d.line([(7 * u + i * u, y * u), (19 * u, y * u)], fill=white, width=int(2.2 * u))
        d.polygon([(19 * u, 9 * u), (26 * u, 16 * u), (19 * u, 23 * u)], fill=(255, 150, 60, 255))
    elif name == "jump":
        d.polygon([(16 * u, 5 * u), (23 * u, 13 * u), (19 * u, 13 * u), (19 * u, 20 * u), (13 * u, 20 * u), (13 * u, 13 * u), (9 * u, 13 * u)], fill=(255, 150, 60, 255))
        cloud(16, 24, 3.2)
    elif name == "cannon":
        d.rectangle([7 * u, 13 * u, 17 * u, 19 * u], fill=(184, 115, 51, 255))
        d.ellipse([15 * u, 11.5 * u, 19 * u, 20.5 * u], fill=(110, 62, 26, 255))
        for i, x in enumerate((19, 22, 25)):
            r = 1.6 + i * 0.7
            d.ellipse([(x - r) * u, (16 - r) * u, (x + r) * u, (16 + r) * u], fill=white)
    elif name == "scald":
        for k in range(12):
            a = k / 12 * math.tau
            d.line([(16 + math.cos(a) * 5) * u, (16 + math.sin(a) * 5) * u, (16 + math.cos(a) * 11) * u, (16 + math.sin(a) * 11) * u],
                   fill=white if k % 2 else fg, width=int(2 * u))
        d.ellipse([12 * u, 12 * u, 20 * u, 20 * u], fill=(255, 210, 120, 255))
    elif name == "knuckle":
        d.rounded_rectangle([9 * u, 10 * u, 21 * u, 22 * u], radius=3 * u, fill=fg, outline=(60, 25, 10, 255), width=int(u))
        for x in (12, 15, 18):
            d.line([x * u, 10.5 * u, x * u, 14 * u], fill=(60, 25, 10, 255), width=int(u))
        cloud(24.5, 12, 2.6)
        cloud(24.5, 20, 2.2)
    elif name == "kick":
        d.polygon([(8 * u, 9 * u), (13 * u, 9 * u), (15 * u, 18 * u), (24 * u, 18 * u), (24 * u, 23 * u), (10 * u, 23 * u)], fill=fg)
        cloud(8, 22, 2.6)
    elif name == "mist":
        cloud(12, 14, 4.0, (200, 205, 215, 255))
        cloud(20, 17, 4.4)
        cloud(14, 21, 3.4, (225, 228, 236, 255))
    elif name == "redline":
        d.pieslice([6 * u, 8 * u, 26 * u, 28 * u], 180, 360, fill=(240, 240, 240, 255))
        d.pieslice([6 * u, 8 * u, 26 * u, 28 * u], 315, 360, fill=(220, 30, 20, 255))
        a = math.radians(-20)
        d.line([16 * u, 18 * u, (16 + math.cos(a) * 9) * u, (18 + math.sin(a) * 9) * u], fill=(20, 20, 20, 255), width=int(1.6 * u))
        d.ellipse([14.5 * u, 16.5 * u, 17.5 * u, 19.5 * u], fill=(40, 40, 40, 255))
    elif name.startswith("mode_"):
        lit = int(name[-1]) - 1  # NORMAL 0 bars lit, HEAT 1, PRESSURE 2
        for i in range(3):
            fill = fg if i < lit else (70, 70, 70, 255)
            d.rectangle([(8 + i * 6) * u, (22 - i * 5) * u, (12 + i * 6) * u, 24 * u], fill=fill)
        if lit == 0:
            cloud(22, 10, 2.6)
    elif name == "hud":
        d.rectangle([7 * u, 13 * u, 25 * u, 19 * u], outline=white, width=int(u))
        d.rectangle([8.5 * u, 14.5 * u, 19 * u, 17.5 * u], fill=(255, 120, 40, 255))
    elif name == "guide":
        d.rectangle([9 * u, 7 * u, 23 * u, 25 * u], fill=(235, 220, 180, 255), outline=(90, 55, 25, 255), width=int(u))
        for y in (11, 14, 17, 20):
            d.line([11.5 * u, y * u, 20.5 * u, y * u], fill=(120, 80, 40, 255), width=int(u))
    return img.resize((size, size), Image.LANCZOS)


UI_ICONS = ["boost", "dash", "jump", "cannon", "scald", "knuckle", "kick", "mist", "redline", "mode_1", "mode_2", "mode_3", "hud", "guide"]
