"""Item icons, pack icons, HUD glyph page and animated spell-barrier block textures."""
import math
import numpy as np
from PIL import Image
from .art import Art
from . import book as B


def _save(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(path, optimize=True)


def item_icon(school, size=32):
    """A 3/4 view of the closed grimoire with its emblem, drawn as crisp pixel-ish art."""
    a = Art(size, size, ss=6)
    cover = {"pressure": (38, 33, 30), "ice": (22, 52, 150), "blood": (86, 12, 26)}[school]
    trim = {"pressure": (190, 106, 48), "ice": (205, 215, 235), "blood": (70, 70, 82)}[school]
    glowc = {"pressure": (255, 150, 40), "ice": (110, 230, 255), "blood": (255, 40, 55)}[school]
    pages = {"pressure": (240, 226, 190), "ice": (220, 242, 255), "blood": (240, 214, 206)}[school]
    # page block (right side) and cover (front)
    a.poly([(9, 4), (27, 3), (27, 27), (9, 29)], fill=pages)
    for y in range(6, 28, 2):
        a.line([(10, y), (26.5, y - 1)], (200, 180, 150) if school != "ice" else (160, 200, 230), 0.3)
    a.poly([(4, 5), (23, 4), (23, 28), (4, 30)], fill=cover, outline=trim, width=1.2)
    a.poly([(3, 5), (5.5, 4.6), (5.5, 30), (3, 30.5)], fill=tuple(int(c * 0.7) for c in cover))
    for (x, y) in ((4.5, 5.5), (21, 5), (4.5, 27.5), (21, 27)):
        a.rect(x - 1.2, y - 1.2, x + 1.2, y + 1.2, fill=trim)
    cx, cy = 13.5, 17
    if school == "pressure":
        for i, r in enumerate((2.0, 3.4, 4.8, 6.2, 7.6)):
            a.circle(cx, cy, r, outline=glowc if i % 2 == 0 else trim, width=0.8)
        a.circle(cx, cy, 1.4, fill=(255, 240, 200))
    elif school == "ice":
        a.hexagon(cx, cy, 7.4, trim, 0.9)
        a.hexagon(cx, cy, 5.6, glowc, 0.7)
        a.star6(cx, cy, 4.6, (245, 252, 255), 0.9)
    else:
        a.poly(B.heart_pts(cx, cy, 0.32), fill=(225, 25, 40), outline=(160, 160, 176), width=0.6)
        a.poly(B.heart_pts(cx - 1, cy - 1.2, 0.1), fill=(255, 200, 210))
    a.radial_glow(cx, cy, 6, glowc, 0.35)
    out = a.finish(emissive=False, alpha_from_glow=False)
    # transparent background outside the drawn book
    lum = np.asarray(a.base.resize((size, size), Image.LANCZOS), np.float32).max(-1)
    out[..., 3] = np.where(lum > 6, 255, 0)
    return out


def pack_icon(size=256):
    a = Art(size, size, ss=2)
    a.grain((14, 10, 12), 0.3, 6, seed=1)
    cx, cy = size / 2, size / 2
    for i, (school, ang) in enumerate((("pressure", -90), ("ice", 30), ("blood", 150))):
        col = {"pressure": (255, 150, 40), "ice": (110, 220, 255), "blood": (255, 40, 60)}[school]
        x = cx + math.cos(math.radians(ang)) * 62
        y = cy + math.sin(math.radians(ang)) * 62
        a.radial_glow(x, y, 70, col, 0.55)
        a.circle(x, y, 40, outline=col, width=3)
        if school == "pressure":
            for r in (10, 18, 26, 34):
                a.circle(x, y, r, outline=col, width=1.5)
        elif school == "ice":
            a.hexagon(x, y, 32, col, 2)
            a.star6(x, y, 22, (240, 252, 255), 2.2)
        else:
            a.poly(B.heart_pts(x, y + 2, 1.4), fill=(220, 20, 40), outline=(200, 200, 210), width=1.5)
    a.circle(cx, cy, 118, outline=(230, 200, 140), width=2.5)
    a.circle(cx, cy, 110, outline=(120, 100, 80), width=1)
    a.ring_ticks(cx, cy, 110, 118, 90, (230, 200, 140), 0.8)
    out = a.finish(emissive=False, alpha_from_glow=False)
    out[..., 3] = 255
    return out


def glyph_page():
    """textures/font/glyph_E5.png: 16x16 grid of 16px glyphs (U+E500..)."""
    page = np.zeros((256, 256, 4), np.float32)

    def put(i, arr):
        x, y = (i % 16) * 16, (i // 16) * 16
        page[y:y + 16, x:x + 16] = arr

    for i, school in enumerate(("pressure", "ice", "blood")):
        put(i, item_icon(school, 16))
    # bar full / empty
    a = Art(16, 16, ss=6)
    a.rect(1, 4, 14, 12, fill=(255, 255, 255))
    put(3, _mono(a, (255, 255, 255)))
    a = Art(16, 16, ss=6)
    a.rect(1, 4, 14, 12, outline=(140, 140, 140), width=1)
    put(4, _mono(a, (140, 140, 140)))
    a = Art(16, 16, ss=6)  # ready check
    a.line([(2, 8), (6, 12), (14, 3)], (90, 255, 120), 2.2)
    put(5, _mono(a, (90, 255, 120)))
    a = Art(16, 16, ss=6)  # lock / cooldown
    a.rect(3, 7, 13, 15, fill=(255, 90, 80))
    a.circle(8, 6, 4, outline=(255, 90, 80), width=1.6)
    put(6, _mono(a, (255, 90, 80)))
    a = Art(16, 16, ss=6)  # star (empowered)
    pts = []
    for k in range(10):
        r = 7 if k % 2 == 0 else 3
        ang = -math.pi / 2 + k * math.pi / 5
        pts.append((8 + math.cos(ang) * r, 8 + math.sin(ang) * r))
    a.poly(pts, fill=(255, 200, 60))
    put(7, _mono(a, (255, 200, 60)))
    a = Art(16, 16, ss=6)  # hourglass (active)
    a.poly([(3, 1), (13, 1), (8, 8)], fill=(120, 220, 255))
    a.poly([(8, 8), (13, 15), (3, 15)], fill=(120, 220, 255))
    put(8, _mono(a, (120, 220, 255)))
    return page


def _mono(a, color):
    out = a.finish(emissive=False, alpha_from_glow=False)
    lum = np.asarray(a.base.resize((a.w, a.h), Image.LANCZOS), np.float32).max(-1)
    out[..., 3] = np.clip(lum * 1.2, 0, 255)
    out[..., :3] = np.array(color, np.float32)
    return out


def barrier_texture(kind, frames=8):
    """Animated translucent spell-barrier block (vertical flipbook strip)."""
    strip = np.zeros((16 * frames, 16, 4), np.float32)
    y, x = np.mgrid[0:16, 0:16].astype(np.float32)
    for f in range(frames):
        ph = f / frames * 2 * math.pi
        if kind == "pressure_barrier":
            # animated orange geometric pattern (moving hex / isobar lines)
            line = np.abs(np.sin((y / 16 * 2 + x / 32) * math.pi * 2 + ph))
            hexy = np.abs(np.sin((x + y * 0.58) / 16 * math.pi * 4)) * np.abs(np.sin((x - y * 0.58) / 16 * math.pi * 4))
            k = np.clip((0.15 - line) * 6, 0, 1) + np.clip((0.06 - hexy) * 8, 0, 1) * 0.7
            rgb = np.stack([255 * np.ones_like(k), 150 + 90 * k, 40 + 150 * k], -1)
            alpha = 70 + 170 * np.clip(k, 0, 1)
        elif kind == "frost_wall":
            n = np.sin(x * 0.9 + ph) * np.cos(y * 0.7 - ph * 0.5)
            k = np.clip(n * 0.5 + 0.5, 0, 1)
            edge = (np.minimum(np.minimum(x, 15 - x), np.minimum(y, 15 - y)) < 1).astype(np.float32)
            rgb = np.stack([140 + 100 * k, 200 + 50 * k, 255 * np.ones_like(k)], -1)
            alpha = 120 + 60 * k + edge * 70
        else:
            vein = np.abs(np.sin(x / 16 * math.pi * 3 + np.sin(y / 16 * math.pi * 2 + ph) * 1.3))
            k = np.clip((0.2 - vein) * 5, 0, 1)
            rgb = np.stack([120 + 135 * k, 6 + 40 * k, 20 + 30 * k], -1)
            alpha = 150 + 100 * k
        strip[f * 16:(f + 1) * 16, :, :3] = rgb
        strip[f * 16:(f + 1) * 16, :, 3] = np.clip(alpha, 0, 255)
    return strip


def write_icons(rp, bp):
    import os
    os.makedirs(f"{rp}/textures/items", exist_ok=True)
    os.makedirs(f"{rp}/textures/font", exist_ok=True)
    os.makedirs(f"{rp}/textures/blocks/grimoire", exist_ok=True)
    for s in ("pressure", "ice", "blood"):
        _save(item_icon(s, 32), f"{rp}/textures/items/grimoire_{s}.png")
    icon = pack_icon(256)
    _save(icon, f"{rp}/pack_icon.png")
    _save(icon, f"{bp}/pack_icon.png")
    _save(glyph_page(), f"{rp}/textures/font/glyph_E5.png")
    for k in ("pressure_barrier", "frost_wall", "blood_thornwall"):
        _save(barrier_texture(k), f"{rp}/textures/blocks/grimoire/{k}.png")
