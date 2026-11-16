"""
Inventory icons (32x32) rendered from the actual 3D models, then reduced to
pixel art: diagonal orientation like vanilla swords (tip top-right), coverage
aware down-sampling (thin blades survive as 1-px lines), palette snapping and
a dark outline.  Also builds the pack icon.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from PIL import Image

from . import bedrock, render, swords
from .bedrock import rot_x, trans

ICON = 32
SS = 8


def _render_hi(weapon: str, tier: str, size: int = ICON * SS) -> Image.Image:
    m = swords.BUILDERS[weapon]()
    m.layout()
    geo = bedrock.load_geometries(m.geometry_json())[m.identifier]
    tex = render.texture_array(m.paint(swords.painters(weapon, tier)))
    # extent along the blade axis
    ys = [c.origin[1] for b in m.bones for c in b.boxes] + [c.origin[1] + c.size[1] for b in m.bones for c in b.boxes]
    y0, y1 = min(ys), max(ys)
    mid = (y0 + y1) / 2
    root = rot_x(42.0) @ trans((0, -mid, 0))       # tilt the blade toward the top-right corner
    mats = bedrock.world_matrices(geo, bedrock.rest_pose(geo), root=root)
    half = (y1 - y0) / 2 * math.sqrt(2) / 2 * 1.04 + 0.6
    cam = render.Camera(eye=(-200, 0, 0.0), target=(0, 0, 0), ortho=half)
    return render.render([render.Instance(geo, tex, mats)], cam, size=(size, size), bg=(0, 0, 0, 0), ss=1,
                         ambient=0.62, light=(-0.4, 0.8, 0.45))


def _reduce(hi: Image.Image) -> Image.Image:
    a = np.array(hi, dtype=np.float32)
    H, W = a.shape[:2]
    out = np.zeros((ICON, ICON, 4), np.uint8)
    for j in range(ICON):
        for i in range(ICON):
            blk = a[j * SS:(j + 1) * SS, i * SS:(i + 1) * SS]
            cov = (blk[..., 3] > 128)
            frac = cov.mean()
            if frac < 0.16:
                continue
            px = blk[cov][:, :3]
            # pick the median-luminance colour so highlights / edges are kept but not exaggerated
            lum = px @ np.array([0.299, 0.587, 0.114])
            col = px[np.argsort(lum)[len(lum) // 2]]
            out[j, i, :3] = np.clip(col, 0, 255)
            out[j, i, 3] = 255
    return Image.fromarray(out, "RGBA")


def _outline(img: Image.Image) -> Image.Image:
    a = np.array(img)
    alpha = a[..., 3] > 0
    out = a.copy()
    H, W = alpha.shape
    for y in range(H):
        for x in range(W):
            if alpha[y, x]:
                continue
            # dark outline on the lower/right neighbours side, as in vanilla item art
            nb = [(y - 1, x), (y, x - 1), (y + 1, x), (y, x + 1)]
            cols = [a[yy, xx, :3] for yy, xx in nb if 0 <= yy < H and 0 <= xx < W and alpha[yy, xx]]
            if cols:
                c = np.mean(cols, axis=0) * 0.28
                out[y, x, :3] = c.astype(np.uint8)
                out[y, x, 3] = 255
    return Image.fromarray(out, "RGBA")


def icon(weapon: str, tier: str) -> Image.Image:
    return _outline(_reduce(_render_hi(weapon, tier)))


def pack_icon() -> Image.Image:
    """256x256 pack icon: the three iron swords crossed over a parchment-dark field."""
    W = 256
    bg = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    px = bg.load()
    for y in range(W):
        for x in range(W):
            d = math.hypot(x - W / 2, y - W / 2) / (W / 2)
            v = int(48 - 22 * d)
            px[x, y] = (v + 14, v + 8, v, 255)
    for k, (w, tier, angle) in enumerate((("zweihander", "iron", 0), ("rapier", "iron", 1), ("katana", "iron", 2))):
        hi = _render_hi(w, tier, size=W)
        if angle == 1:
            hi = hi.transpose(Image.FLIP_LEFT_RIGHT)
        if angle == 2:
            hi = hi.rotate(0)
            hi = hi.resize((int(W * 0.9), int(W * 0.9)), Image.LANCZOS)
            pad = Image.new("RGBA", (W, W), (0, 0, 0, 0))
            pad.paste(hi, ((W - hi.size[0]) // 2, (W - hi.size[1]) // 2 + 6))
            hi = pad
        bg = Image.alpha_composite(bg, hi)
    # frame
    px = bg.load()
    for i in range(W):
        for t in range(5):
            c = (176, 140, 72, 255)
            px[i, t] = px[i, W - 1 - t] = px[t, i] = px[W - 1 - t, i] = c
    return bg
