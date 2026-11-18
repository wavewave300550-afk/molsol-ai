"""
render.py - software renderer for previews (numpy z-buffer, orthographic).

Renders a geo.Model in its bind pose or any animation pose, with texture,
simple directional lighting, emissive and translucent bone layers, a ground
grid and a player-sized scale figure. Used for turnarounds and animation
previews; it is NOT the game's renderer, and outputs are labelled as such.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

from .geo import FACES, Model, pivot_transform

LIGHT = np.array([-0.45, 0.8, -0.4])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _view_matrix(yaw: float, pitch: float) -> np.ndarray:
    """Display space -> view space. yaw 0 looks at the model's front (from -Z)."""
    y, p = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    # positive pitch raises the camera (far points move up the screen)
    Rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    # camera sits on -Z looking +Z: flip X so that screen-right is the viewer's right
    F = np.diag([-1.0, 1.0, 1.0])
    return F @ Rx @ Ry


def layer_of(bone_name: str) -> str:
    """Render layer by bone-name convention (mirrors the render controllers)."""
    if bone_name.endswith("_glow") or "_glow_" in bone_name:
        return "glow"
    if bone_name.endswith("_glass") or "_glass_" in bone_name:
        return "glass"
    return "solid"


def collect_quads(model: Model, pose: Optional[dict] = None, hidden: Iterable[str] = ()):
    """All visible faces as (tl, u, v, uvrect, layer) in DISPLAY space."""
    if model.texture is None:
        model.paint()
    mats = model.matrices(pose)
    hidden = set(hidden)
    hide = set()
    for h in hidden:
        hide.add(h)
        hide.update(model.descendants(h))
    quads = []
    for bi, b in enumerate(model.bones):
        if b.name in hide:
            continue
        sc = (pose or {}).get(b.name, {}).get("scale")
        layer = layer_of(b.name)
        for ci, c in enumerate(b.cubes):
            M = mats[b.name]
            if c.rotation:
                M = M @ pivot_transform(c.pivot or c.origin, c.rotation)
            for face in FACES:
                r = model.uv.get((bi, ci, face))
                if not r:
                    continue
                pts = np.array([list(p) + [1.0] for p in c.corners(face)]).T      # 4x3
                w = (M @ pts)[:3].T                                               # 3 pts, geo space
                w[:, 0] *= -1                                                     # -> display space
                quads.append((w[0], w[1] - w[0], w[2] - w[0], r, layer))
    return quads


def render(model: Model, pose: Optional[dict] = None, *, yaw: float = 30, pitch: float = 14,
           size: Tuple[int, int] = (720, 720), bounds=None, hidden: Iterable[str] = (),
           bg=(34, 36, 44), ground: bool = True, scale_figure: bool = True, ss: int = 2,
           extra: Sequence[Tuple[Model, Optional[dict], Tuple[float, float, float]]] = ()) -> Image.Image:
    """Render to a PIL image. `bounds` = (min, max) geo-space box to frame (keeps frames stable)."""
    Wp, Hp = size[0] * ss, size[1] * ss
    V = _view_matrix(yaw, pitch)
    lo, hi = bounds if bounds is not None else model.extent(None)
    lo, hi = np.array(lo, float), np.array(hi, float)
    lo[1] = min(lo[1], 0.0)
    corners = np.array([[(-x), y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    vc = corners @ V.T
    mn, mx = vc.min(0), vc.max(0)
    span = max((mx[0] - mn[0]) / Wp, (mx[1] - mn[1]) / Hp) * 1.12
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2

    color = np.zeros((Hp, Wp, 3), dtype=np.float32)
    color[:] = np.array(bg, dtype=np.float32) / 255
    # soft vertical gradient so silhouettes read
    color *= (1.12 - 0.3 * np.linspace(0, 1, Hp, dtype=np.float32))[:, None, None]
    depth = np.full((Hp, Wp), 1e9, dtype=np.float32)

    def to_screen(p):
        v = p @ V.T
        return np.array([(v[..., 0] - cx) / span + Wp / 2, Hp / 2 - (v[..., 1] - cy) / span, v[..., 2]]).T

    if ground:
        _draw_ground(color, lo, hi, to_screen, Wp, Hp)

    layers: Dict[str, list] = {"solid": [], "glow": [], "glass": []}
    jobs = [(model, pose, (0.0, 0.0, 0.0), hidden)] + [(m, p, off, ()) for m, p, off in extra]
    for mdl, ps, off, hid in jobs:
        tex = np.asarray(mdl.texture if mdl.texture is not None else mdl.paint(), dtype=np.float32) / 255
        for q in collect_quads(mdl, ps, hid):
            o = np.array([-off[0], off[1], off[2]])
            layers[q[4]].append((q[0] + o, q[1], q[2], q[3], tex))
    if scale_figure:
        _figure(layers["solid"], hi)

    for name in ("solid", "glow", "glass"):
        for tl, du, dv, rect, tex in layers[name]:
            _raster(color, depth, tl, du, dv, rect, tex, V, to_screen, name, Wp, Hp)

    img = Image.fromarray((np.clip(color, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    return img.resize(size, Image.LANCZOS) if ss > 1 else img


def _raster(color, depth, tl, du, dv, rect, tex, V, to_screen, layer, Wp, Hp):
    A = to_screen(tl[None, :])[0]
    B = to_screen((tl + du)[None, :])[0]
    C = to_screen((tl + dv)[None, :])[0]
    U2, V2 = B[:2] - A[:2], C[:2] - A[:2]
    det = U2[0] * V2[1] - U2[1] * V2[0]
    if abs(det) < 1e-6:
        return
    D = A[:2] + U2 + V2
    x0 = int(max(0, math.floor(min(A[0], B[0], C[0], D[0]))))
    x1 = int(min(Wp - 1, math.ceil(max(A[0], B[0], C[0], D[0]))))
    y0 = int(max(0, math.floor(min(A[1], B[1], C[1], D[1]))))
    y1 = int(min(Hp - 1, math.ceil(max(A[1], B[1], C[1], D[1]))))
    if x1 < x0 or y1 < y0:
        return
    ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    px, py = xs + 0.5 - A[0], ys + 0.5 - A[1]
    s = (px * V2[1] - py * V2[0]) / det
    t = (py * U2[0] - px * U2[1]) / det
    inside = (s >= 0) & (s < 1) & (t >= 0) & (t < 1)
    if not inside.any():
        return
    z = A[2] + s * (B[2] - A[2]) + t * (C[2] - A[2])
    u, v, w, h = rect
    tx = np.clip((u + s * w).astype(int), u, u + w - 1)
    ty = np.clip((v + t * h).astype(int), v, v + h - 1)
    tx = np.clip(tx, 0, tex.shape[1] - 1)
    ty = np.clip(ty, 0, tex.shape[0] - 1)
    texel = tex[ty, tx]
    n = np.cross(dv, du)                                  # outward normal (display space)
    ln = np.linalg.norm(n)
    n = n / ln if ln > 1e-9 else np.array([0, 1.0, 0])
    if (V @ n)[2] > 1e-6:                                 # faces away from the camera
        return
    lit = 0.5 + 0.5 * max(0.0, float(n @ LIGHT)) + 0.08 * max(0.0, n[1])
    sub_d = depth[y0:y1 + 1, x0:x1 + 1]
    sub_c = color[y0:y1 + 1, x0:x1 + 1]
    if layer == "solid":
        ok = inside & (texel[..., 3] > 0.5) & (z < sub_d)
        sub_c[ok] = texel[ok][:, :3] * lit
        sub_d[ok] = z[ok]
    elif layer == "glow":
        ok = inside & (texel[..., 3] > 0.01) & (z < sub_d)
        e = (1 - texel[ok][:, 3:4])                       # low alpha = emissive
        sub_c[ok] = texel[ok][:, :3] * (lit * (1 - e) + 1.15 * e)
        sub_d[ok] = z[ok]
    else:                                                 # glass: alpha blend, no depth write
        ok = inside & (texel[..., 3] > 0.01) & (z < sub_d)
        a = texel[ok][:, 3:4]
        sub_c[ok] = sub_c[ok] * (1 - a) + texel[ok][:, :3] * lit * a


def _draw_ground(color, lo, hi, to_screen, Wp, Hp):
    """One-block grid on y=0 for scale."""
    img = Image.fromarray((np.clip(color, 0, 1) * 255).astype(np.uint8), "RGB")
    dr = ImageDraw.Draw(img, "RGBA")
    r = max(abs(lo[0]), abs(hi[0]), abs(lo[2]), abs(hi[2])) + 24
    n = int(math.ceil(r / 16))
    for i in range(-n, n + 1):
        for a, b in (((-n * 16, 0, i * 16), (n * 16, 0, i * 16)), ((i * 16, 0, -n * 16), (i * 16, 0, n * 16))):
            pa, pb = to_screen(np.array([a], float))[0], to_screen(np.array([b], float))[0]
            dr.line([(pa[0], pa[1]), (pb[0], pb[1])], fill=(120, 126, 146, 70 if i % 4 else 130), width=2)
    color[:] = np.asarray(img, dtype=np.float32) / 255


_FIG_TEX = None


def _figure(quads: list, hi):
    """A 0.6 x 1.8 block reference figure standing beside the model (display space)."""
    global _FIG_TEX
    if _FIG_TEX is None:
        t = np.zeros((4, 4, 4), dtype=np.float32)
        t[:] = [0.36, 0.62, 0.78, 1.0]
        t[0, :] = [0.86, 0.72, 0.58, 1.0]
        _FIG_TEX = t
    x0 = -(abs(hi[0]) + 22)
    for (ox, oy, oz, sx, sy, sz) in ((x0, 0, -2, 8, 24, 4), (x0, 24, -4, 8, 8, 8)):
        o = np.array([ox, oy, oz], float)
        X, Y, Z = np.array([sx, 0, 0.0]), np.array([0, sy, 0.0]), np.array([0, 0, sz], float)
        rect = (0, 0, 4, 4)
        for tl, du, dv in ((o + Y, X, -Y), (o + Y + Z + X, -X, -Y), (o + Y + Z, -Z, -Y),
                           (o + Y + X, Z, -Y), (o + Y + Z, X, -Z)):
            quads.append((tl, du, dv, rect, _FIG_TEX))


# --------------------------------------------------------------------------- sheets

def label(img: Image.Image, text: str) -> Image.Image:
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, img.width, 20], fill=(18, 19, 24))
    dr.text((8, 4), text, fill=(232, 232, 236))
    return img


def sheet(images: List[Image.Image], cols: int, pad: int = 6, bg=(18, 19, 24)) -> Image.Image:
    rows = int(math.ceil(len(images) / cols))
    w, h = images[0].size
    out = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * h + (rows + 1) * pad), bg)
    for i, im in enumerate(images):
        out.paste(im, (pad + (i % cols) * (w + pad), pad + (i // cols) * (h + pad)))
    return out


def turnaround(model: Model, title: str, pose=None, hidden=(), size=(560, 560), bounds=None) -> Image.Image:
    views = [("front", 0, 8), ("three-quarter", 35, 16), ("side", 90, 8), ("rear", 180, 8)]
    b = bounds if bounds is not None else model.extent(pose)
    ims = [label(render(model, pose, yaw=y, pitch=p, size=size, bounds=b, hidden=hidden), f"{title} - {n}")
           for n, y, p in views]
    return sheet(ims, 4)
