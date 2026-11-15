"""Software z-buffer renderer for previewing Bedrock geometry (orthographic).

Renders the exact geometry + atlas that ships in the resource pack, using the
Bedrock bone/cube rotation convention from geo.py.  Supports animation poses
(per-bone rotation / position deltas), emissive glow and soft bloom.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

from .geo import Model, face_frame, rot_matrix, NORMALS

Pose = Dict[str, dict]   # bone -> {"rot": (rx,ry,rz), "pos": (x,y,z), "scale": s}


def _affine(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def bone_matrices(model: Model, variant: Optional[str], pose: Optional[Pose] = None) -> Dict[str, np.ndarray]:
    pose = pose or {}
    mats: Dict[str, np.ndarray] = {}
    for bn in model.order:
        b = model.bones[bn]
        off = model.variant_offset(bn, variant)
        piv = np.array(b.pivot) + off
        rest = np.array(model.bone_rot(bn, variant), dtype=float)
        pz = pose.get(bn, {})
        rot = rest + np.array(pz.get("rot", (0, 0, 0)), dtype=float)
        pos = np.array(pz.get("pos", (0, 0, 0)), dtype=float)
        sc = pz.get("scale", 1.0)
        S = np.eye(3) * sc if np.isscalar(sc) else np.diag(sc)
        R = rot_matrix(rot) @ S
        local = _affine(np.eye(3), pos) @ _affine(np.eye(3), piv) @ _affine(R, np.zeros(3)) @ _affine(np.eye(3), -piv)
        parent = mats.get(b.parent) if b.parent else None
        mats[bn] = (parent @ local) if parent is not None else local
    return mats


def collect_quads(model: Model, variant: Optional[str], pose: Optional[Pose] = None,
                  hide: Sequence[str] = (), accents: bool = False):
    """Returns list of (corners (4,3), uvs (4,2), normal (3,), cutout)."""
    mats = bone_matrices(model, variant, pose)
    hidden = set()
    for h in hide:
        if h in model.bones:
            hidden.update(model.subtree(h))
    quads = []
    for bn in model.order:
        if bn in hidden or not model.bone_in_variant(bn, variant):
            continue
        b = model.bones[bn]
        if b.never_render:
            continue
        M = mats[bn]
        off = model.variant_offset(bn, variant)
        for c in b.cubes:
            if not c.in_variant(variant or "base"):
                continue
            if c.accent and not accents:
                continue
            o = np.array(c.origin) + off - c.inflate
            s = np.array(c.size) + 2 * c.inflate
            if c.rot is not None:
                cp = np.array(c.pivot if c.pivot else c.origin) + off
                Rc = rot_matrix(c.rot)
            else:
                cp, Rc = None, None
            for f in c.emitted_faces():
                corner, du, dv, fw, fh = face_frame(f, o, s)
                pts = np.array([corner, corner + du, corner + du + dv, corner + dv])
                nrm = np.array(NORMALS[f], dtype=float)
                if Rc is not None:
                    pts = (pts - cp) @ Rc.T + cp
                    nrm = Rc @ nrm
                ph = np.c_[pts, np.ones(4)] @ M.T
                pts = ph[:, :3]
                nrm = M[:3, :3] @ nrm
                nn = np.linalg.norm(nrm)
                nrm = nrm / nn if nn > 1e-9 else nrm
                u, v, w, h = c.uv[f]
                uvs = np.array([[u, v], [u + w, v], [u + w, v + h], [u, v + h]], dtype=float)
                quads.append((pts, uvs, nrm, c.cutout))
    return quads


def render(model: Model, texture: Image.Image, *, variant: Optional[str] = None,
           pose: Optional[Pose] = None, yaw: float = 0.0, pitch: float = 8.0,
           size: Tuple[int, int] = (512, 640), scale: Optional[float] = None,
           center: Optional[Sequence[float]] = None, ss: int = 2, bg=(232, 230, 226),
           bloom: bool = True, hide: Sequence[str] = (), ground: bool = True, accents: bool = False,
           light_dir=(-0.45, 0.75, -0.55), backdrop=None) -> Image.Image:
    """backdrop(img: PIL.Image, ss) may draw into the (supersampled) background
    before the model is composited over it (ground lines, shadows)."""
    tex = np.asarray(texture.convert("RGBA"), dtype=np.float64) / 255.0
    TH, TW = tex.shape[:2]
    quads = collect_quads(model, variant, pose, hide, accents)
    th, ph_ = math.radians(yaw), math.radians(pitch)
    f = np.array([math.sin(th) * math.cos(ph_), -math.sin(ph_), math.cos(th) * math.cos(ph_)])
    up = np.array([0.0, 1.0, 0.0])
    r = np.cross(up, f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    W, H = size[0] * ss, size[1] * ss
    allp = np.concatenate([q[0] for q in quads]) if quads else np.zeros((1, 3))
    if center is None:
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        center = (lo + hi) / 2
    center = np.array(center, dtype=float)
    sx_all = (allp - center) @ r
    sy_all = (allp - center) @ u
    if scale is None:
        ext = max(np.abs(sx_all).max() / (W * 0.42), np.abs(sy_all).max() / (H * 0.44), 1e-6)
        scale = 1.0 / ext
    else:
        scale = scale * ss
    color = np.zeros((H, W, 3))
    glowbuf = np.zeros((H, W, 3))
    zbuf = np.full((H, W), np.inf)
    L = np.array(light_dir, dtype=float)
    L /= np.linalg.norm(L)
    for pts, uvs, nrm, cutout in quads:
        rel = pts - center
        X = W / 2 + (rel @ r) * scale
        Y = H / 2 - (rel @ u) * scale
        Z = rel @ f
        facing = nrm @ f
        lam = max(0.0, float(nrm @ L))
        shade = 0.52 + 0.55 * lam + 0.08 * max(0.0, nrm[1])
        if cutout:
            shade = 0.55 + 0.45 * abs(float(nrm @ L))
        elif facing > 1e-4:
            continue  # back-face cull for solid cubes
        for tri in ((0, 1, 2), (0, 2, 3)):
            _raster(X[list(tri)], Y[list(tri)], Z[list(tri)], uvs[list(tri)], tex, TW, TH,
                    color, glowbuf, zbuf, shade, cutout)
    covered = np.isfinite(zbuf)
    bgimg = _background(W, H, bg)
    if ground:
        bgimg = _shadow(bgimg, covered)
    if backdrop is not None:
        bimg = Image.fromarray((np.clip(bgimg, 0, 1) * 255).astype(np.uint8))
        backdrop(bimg, ss)
        bgimg = np.asarray(bimg, dtype=np.float64) / 255.0
    out = np.where(covered[..., None], color, bgimg)
    if bloom:
        g = Image.fromarray((np.clip(glowbuf, 0, 1) * 255).astype(np.uint8))
        g = g.filter(ImageFilter.GaussianBlur(radius=6 * ss))
        out = out + np.asarray(g, dtype=np.float64) / 255.0 * 0.9
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    if ss > 1:
        img = img.resize(size, Image.LANCZOS)
    return img


def _raster(X, Y, Z, UV, tex, TW, TH, color, glowbuf, zbuf, shade, cutout):
    H, W = zbuf.shape
    x0, x1 = int(max(0, math.floor(X.min()))), int(min(W - 1, math.ceil(X.max())))
    y0, y1 = int(max(0, math.floor(Y.min()))), int(min(H - 1, math.ceil(Y.max())))
    if x1 < x0 or y1 < y0:
        return
    det = (Y[1] - Y[2]) * (X[0] - X[2]) + (X[2] - X[1]) * (Y[0] - Y[2])
    if abs(det) < 1e-9:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    l0 = ((Y[1] - Y[2]) * (gx - X[2]) + (X[2] - X[1]) * (gy - Y[2])) / det
    l1 = ((Y[2] - Y[0]) * (gx - X[2]) + (X[0] - X[2]) * (gy - Y[2])) / det
    l2 = 1 - l0 - l1
    eps = -1e-4
    m = (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
    if not m.any():
        return
    z = l0 * Z[0] + l1 * Z[1] + l2 * Z[2]
    tu = l0 * UV[0, 0] + l1 * UV[1, 0] + l2 * UV[2, 0]
    tv = l0 * UV[0, 1] + l1 * UV[1, 1] + l2 * UV[2, 1]
    ui = np.clip(np.floor(tu).astype(int), 0, TW - 1)
    vi = np.clip(np.floor(tv).astype(int), 0, TH - 1)
    texel = tex[vi, ui]
    zs = zbuf[y0:y1 + 1, x0:x1 + 1]
    if cutout:
        m &= texel[..., 3] >= 0.5
        glow = np.zeros(z.shape)
    else:
        a = texel[..., 3]
        glow = np.where(a < 0.99, np.clip((1 - a) / 0.92, 0, 1), 0.0)
    m &= z < zs
    if not m.any():
        return
    rgb = texel[..., :3]
    lit = rgb * shade
    final = lit * (1 - glow[..., None]) + rgb * glow[..., None] * 1.25
    cs = color[y0:y1 + 1, x0:x1 + 1]
    gs = glowbuf[y0:y1 + 1, x0:x1 + 1]
    cs[m] = final[m]
    gs[m] = (rgb * glow[..., None])[m]
    gs[m & (glow < 0.01)] = 0
    zs[m] = z[m]


def _background(W, H, bg):
    top = np.array(bg, dtype=float) / 255.0
    bot = top * 0.86
    t = np.linspace(0, 1, H)[:, None, None]
    return np.broadcast_to(top * (1 - t) + bot * t, (H, W, 3)).copy()


def _shadow(bgimg, covered):
    H, W = covered.shape
    rows = np.where(covered.any(axis=1))[0]
    if len(rows) == 0:
        return bgimg
    ybot = rows.max()
    cols = np.where(covered[max(0, ybot - 5):ybot + 1].any(axis=0))[0]
    cx = (cols.min() + cols.max()) / 2 if len(cols) else W / 2
    rx = max(W * 0.18, (cols.max() - cols.min()) * 0.8 if len(cols) else W * 0.2)
    ry = H * 0.025
    yy, xx = np.mgrid[0:H, 0:W]
    d = ((xx - cx) / rx) ** 2 + ((yy - ybot) / ry) ** 2
    k = np.clip(1 - d, 0, 1) * 0.35
    return bgimg * (1 - k[..., None])


def sheet(images, cols: int, labels=None, pad: int = 12, bg=(245, 244, 241), title: Optional[str] = None):
    """Arrange images in a grid (optionally with labels)."""
    from PIL import ImageDraw
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols
    th = 40 if title else 0
    lh = 26 if labels else 0
    out = Image.new("RGB", (cols * w + (cols + 1) * pad, th + rows * (h + lh) + (rows + 1) * pad), bg)
    d = ImageDraw.Draw(out)
    if title:
        d.text((pad, 12), title, fill=(40, 40, 40))
    for k, im in enumerate(images):
        rr, cc = divmod(k, cols)
        x = pad + cc * (w + pad)
        y = th + pad + rr * (h + lh + pad)
        out.paste(im, (x, y))
        if labels:
            d.text((x + 6, y + h + 5), labels[k], fill=(50, 50, 50))
    return out
