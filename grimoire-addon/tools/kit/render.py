"""Software rasterizer for previewing kit models (bind pose or animated pose).

Not used by the game; it exists so models can be inspected and item icons can be
rendered without launching Minecraft.  Works in the same bb space as geo.py.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image


def _camera(yaw, pitch):
    """Camera looking at the origin. yaw 0 = looking at the model's front (north face),
    positive yaw orbits toward the model's +X (east) side; pitch > 0 looks down."""
    y, p = math.radians(yaw), math.radians(pitch)
    # camera position direction (from target toward camera)
    cam = np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])
    fwd = -cam
    up0 = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up0)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return right, up, fwd


def render(model, pose=None, yaw=30, pitch=20, size=(512, 512), bg=(34, 38, 46, 255), fit=None,
           margin=0.06, light=(0.45, 0.8, -0.55), ambient=0.55, ss=1, skin=None, hide=()):
    """Render model -> PIL RGBA image. fit = (center xyz, half_extent) to lock framing."""
    W, H = size[0] * ss, size[1] * ss
    quads = model.world_quads(pose, hide=hide)
    tex = np.asarray(model.atlases.get(skin or "default", model.atlas), dtype=np.float32) / 255.0
    right, up, fwd = _camera(yaw, pitch)
    allp = np.concatenate([q[0] for q in quads]) if quads else np.zeros((1, 3))
    if fit is None:
        sx, sy = allp @ right, allp @ up
        cx, cy = (sx.min() + sx.max()) / 2, (sy.min() + sy.max()) / 2
        half = max(sx.max() - sx.min(), (sy.max() - sy.min()) * W / H) / 2 * (1 + margin) + 1e-6
    else:
        c = np.array(fit[0], dtype=float)
        cx, cy, half = c @ right, c @ up, fit[1]
    scale = (W / 2) / half
    color = np.zeros((H, W, 3), dtype=np.float32)
    color[:] = np.array(bg[:3], dtype=np.float32) / 255.0
    alpha = np.full((H, W), bg[3] / 255.0, dtype=np.float32)
    depth = np.full((H, W), np.inf, dtype=np.float32)
    L = np.array(light, dtype=float)
    L /= np.linalg.norm(L)

    def project(p):
        x = (p @ right - cx) * scale + W / 2
        y = H / 2 - (p @ up - cy) * scale
        z = p @ fwd
        return x, y, z

    def draw(q, blend):
        verts, (u0, v0, uw, vh), _mode = q
        n = np.cross(verts[1] - verts[0], verts[3] - verts[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            return
        n /= ln
        shade = ambient + (1 - ambient) * abs(float(n @ L))
        x, y, z = project(verts)
        # quad uv corners: TL(0,0) TR(1,0) BR(1,1) BL(0,1)
        quv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
        for tri in ((0, 1, 2), (0, 2, 3)):
            xs, ys, zs = x[list(tri)], y[list(tri)], z[list(tri)]
            minx, maxx = int(max(0, math.floor(xs.min()))), int(min(W - 1, math.ceil(xs.max())))
            miny, maxy = int(max(0, math.floor(ys.min()))), int(min(H - 1, math.ceil(ys.max())))
            if minx > maxx or miny > maxy:
                continue
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9:
                continue
            px, py = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            w0 = ((ys[1] - ys[2]) * (px - xs[2]) + (xs[2] - xs[1]) * (py - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (px - xs[2]) + (xs[0] - xs[2]) * (py - ys[2])) / den
            w2 = 1 - w0 - w1
            eps = -1e-4
            inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
            if not inside.any():
                continue
            zz = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            uu = w0 * quv[tri[0], 0] + w1 * quv[tri[1], 0] + w2 * quv[tri[2], 0]
            vv = w0 * quv[tri[0], 1] + w1 * quv[tri[1], 1] + w2 * quv[tri[2], 1]
            ti = np.clip((uu * uw).astype(int), 0, uw - 1) + u0
            tj = np.clip((vv * vh).astype(int), 0, vh - 1) + v0
            texel = tex[tj, ti]
            sub_d = depth[miny:maxy + 1, minx:maxx + 1]
            sub_c = color[miny:maxy + 1, minx:maxx + 1]
            sub_a = alpha[miny:maxy + 1, minx:maxx + 1]
            if blend:
                m = inside & (zz < sub_d) & (texel[..., 3] > 0.01)
                a = texel[..., 3][m][:, None]
                sub_c[m] = sub_c[m] * (1 - a) + texel[..., :3][m] * shade * a
                sub_a[m] = np.maximum(sub_a[m], a[:, 0])
            else:
                m = inside & (zz < sub_d) & (texel[..., 3] > 0.004)
                glow = np.clip((1.0 - texel[..., 3]) / (250.0 / 255.0), 0, 1)[m][:, None]
                base = texel[..., :3][m]
                sub_c[m] = base * (shade * (1 - glow) + glow * 1.08)
                sub_d[m] = zz[m]
                sub_a[m] = 1.0

    solid = [q for q in quads if q[2] != "blend"]
    blend = [q for q in quads if q[2] == "blend"]
    for q in solid:
        draw(q, False)
    blend.sort(key=lambda q: -float(q[0].mean(axis=0) @ fwd))
    for q in blend:
        draw(q, True)
    out = np.concatenate([np.clip(color, 0, 1), alpha[..., None]], axis=2)
    img = Image.fromarray((out * 255).astype(np.uint8), "RGBA")
    if ss > 1:
        img = img.resize(size, Image.LANCZOS)
    return img


def sheet(model, views=((30, 20), (150, 20), (-90, 10), (0, 85)), poses=None, cell=(384, 384), **kw):
    """Contact sheet: one row per pose, one column per view."""
    poses = poses or [None]
    rows = []
    for pose in poses:
        rows.append([render(model, pose, yaw=y, pitch=p, size=cell, **kw) for (y, p) in views])
    out = Image.new("RGBA", (cell[0] * len(views), cell[1] * len(rows)))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            out.paste(im, (c * cell[0], r * cell[1]))
    return out
