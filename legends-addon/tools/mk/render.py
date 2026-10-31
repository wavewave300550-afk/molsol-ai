"""
Software preview renderer (numpy z-buffer, textured, lit) for modelkit models.

It applies the same Bedrock conventions as the exporter (see geo.py) so the
pictures show what the game should show: front = -Z model space, creature's
right on the viewer's left when seen from the front, rotations as in Bedrock.
Poses from animations can be rendered (pose = {bone: {rotation, position, scale}}).
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .geo import Model, FACES


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def bedrock_rot(r) -> np.ndarray:
    """Bedrock [rx, ry, rz] -> right-handed model-space matrix (X applied first)."""
    if r is None:
        return np.eye(3)
    rx, ry, rz = (math.radians(v) for v in r)
    return _rz(-rz) @ _ry(ry) @ _rx(-rx)


def _affine(R=None, t=None):
    M = np.eye(4)
    if R is not None:
        M[:3, :3] = R
    if t is not None:
        M[:3, 3] = t
    return M


def bone_matrices(model: Model, pose: Optional[dict] = None) -> Dict[str, np.ndarray]:
    pose = pose or {}
    mats: Dict[str, np.ndarray] = {}
    for b in model.bones:
        p = pose.get(b.name, {})
        rest = b.rotation or (0, 0, 0)
        ar = p.get("rotation", (0, 0, 0))
        rot = [rest[i] + ar[i] for i in range(3)]
        sc = p.get("scale", (1, 1, 1))
        pos = p.get("position", (0, 0, 0))
        piv = np.array(b.pivot)
        R = bedrock_rot(rot) @ np.diag(sc)
        M = _affine(t=np.array(pos)) @ _affine(t=piv) @ _affine(R) @ _affine(t=-piv)
        if b.parent:
            M = mats[b.parent] @ M
        mats[b.name] = M
    return mats


def _corners(c, face):
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    x0, y0, z0 = ox - i, oy - i, oz - i
    x1, y1, z1 = ox + sx + i, oy + sy + i, oz + sz + i
    if face == "north":
        return (x0, y1, z0), (x1, y1, z0), (x0, y0, z0)
    if face == "south":
        return (x1, y1, z1), (x0, y1, z1), (x1, y0, z1)
    if face == "east":
        return (x0, y1, z1), (x0, y1, z0), (x0, y0, z1)
    if face == "west":
        return (x1, y1, z0), (x1, y1, z1), (x1, y0, z0)
    if face == "up":
        return (x0, y1, z1), (x1, y1, z1), (x0, y1, z0)
    return (x0, y0, z0), (x1, y0, z0), (x0, y0, z1)


def collect_faces(model: Model, pose=None, visible: Optional[Callable[[str], bool]] = None, only=None):
    if model.texture is None:
        model.paint()
    mats = bone_matrices(model, pose)
    hidden = set()
    if visible:
        for b in model.bones:
            if not visible(b.name) or (b.parent and b.parent in hidden):
                hidden.add(b.name)
    faces = []
    for bi, b in enumerate(model.bones):
        if b.name in hidden or (only is not None and b.name not in only):
            continue
        M = mats[b.name]
        kind = "glow" if b.name.startswith("glow_") else ("fx" if b.name.startswith("fx_") else "solid")
        for ci, c in enumerate(b.cubes):
            Rc = bedrock_rot(c.rotation) if c.rotation else None
            cp = np.array(c.pivot or c.origin)
            for face in FACES:
                key = (bi, ci, face)
                if key not in model.uv:
                    continue
                pts = []
                for p in _corners(c, face):
                    q = np.array(p, dtype=float)
                    if Rc is not None:
                        q = Rc @ (q - cp) + cp
                    q = (M @ np.append(q, 1.0))[:3]
                    q[2] = -q[2]          # model space -> world-like (creature faces +Z)
                    pts.append(q)
                faces.append((pts, model.uv[key], kind))
    return faces


def _camera(yaw, pitch):
    a, e = math.radians(yaw), math.radians(pitch)
    # camera orbits: yaw 0 = in front of the creature, 90 = on its right side... (yaw measured toward +X)
    right = np.array([math.cos(a), 0, -math.sin(a)])
    toward = np.array([math.sin(a), 0, math.cos(a)])
    up = np.array([0.0, 1.0, 0.0])
    up2 = up * math.cos(e) - toward * math.sin(e)
    tow2 = up * math.sin(e) + toward * math.cos(e)
    return np.stack([right, up2, tow2])


def render_views(models: Sequence[Tuple[Model, Optional[dict], Optional[Callable]]], views: Sequence[Tuple[float, float]],
                 size: int = 420, ss: int = 2, bg=(38, 42, 54), labels: Optional[Sequence[str]] = None,
                 title: Optional[str] = None, fixed_scale: Optional[float] = None) -> Image.Image:
    """Render several (model, pose, visibility) groups together from several views into one sheet."""
    groups = []
    for grp in models:
        model, pose, vis = grp[:3]
        only = grp[3] if len(grp) > 3 else None
        tex = np.asarray(model.texture if model.texture is not None else model.paint(), dtype=np.uint8)
        groups.append((collect_faces(model, pose, vis, only), tex))
    allpts = np.array([p for faces, _ in groups for f in faces for p in f[0]])
    cams = [_camera(y, p) for y, p in views]
    # common scale so all views share the same size
    span = 1.0
    cx_list = []
    for cam in cams:
        sp = allpts @ cam.T
        lo, hi = sp.min(axis=0), sp.max(axis=0)
        span = max(span, hi[0] - lo[0], hi[1] - lo[1])
        cx_list.append(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2))
    S = size * ss
    scale = fixed_scale * ss if fixed_scale else S / (span * 1.12)
    light = np.array([-0.35, 0.85, 0.45])
    light /= np.linalg.norm(light)
    fill = np.array([0.6, 0.2, -0.75])
    fill /= np.linalg.norm(fill)
    tiles = []
    for vi, cam in enumerate(cams):
        yy = np.linspace(0, 1, S)[:, None]
        color = (np.ones((S, S, 3), dtype=np.float32) * np.array(bg, dtype=np.float32)
                 * (1.12 - 0.35 * yy)[:, :, None])
        zbuf = np.full((S, S), -1e9, dtype=np.float32)
        cxm, cym = cx_list[vi]
        for faces, tex in groups:
            TH, TW = tex.shape[:2]
            for pts, (u0, v0, w, h), kind in faces:
                P = np.array(pts) @ cam.T                      # camera space
                X = (P[:, 0] - cxm) * scale + S / 2
                Y = S / 2 - (P[:, 1] - cym) * scale
                Z = P[:, 2]
                e1 = np.array([X[1] - X[0], Y[1] - Y[0]])
                e2 = np.array([X[2] - X[0], Y[2] - Y[0]])
                det = e1[0] * e2[1] - e1[1] * e2[0]
                if abs(det) < 1e-6:
                    continue
                x4 = [X[0], X[1], X[2], X[1] + X[2] - X[0]]
                y4 = [Y[0], Y[1], Y[2], Y[1] + Y[2] - Y[0]]
                xa, xb = max(0, int(math.floor(min(x4)))), min(S - 1, int(math.ceil(max(x4))))
                ya, yb = max(0, int(math.floor(min(y4)))), min(S - 1, int(math.ceil(max(y4))))
                if xa > xb or ya > yb:
                    continue
                gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
                dx, dy = gx - X[0], gy - Y[0]
                a = (dx * e2[1] - dy * e2[0]) / det
                bb = (e1[0] * dy - e1[1] * dx) / det
                inside = (a >= 0) & (a < 1) & (bb >= 0) & (bb < 1)
                if not inside.any():
                    continue
                depth = Z[0] + a * (Z[1] - Z[0]) + bb * (Z[2] - Z[0])
                tu = np.clip(u0 + (a * w).astype(int), 0, TW - 1)
                tv = np.clip(v0 + (bb * h).astype(int), 0, TH - 1)
                texel = tex[tv, tu]
                alpha = texel[..., 3]
                if kind == "glow":
                    ok = inside & (alpha > 0)
                elif kind == "fx":
                    ok = inside & (alpha > 40)
                else:
                    ok = inside & (alpha >= 128)
                sub = zbuf[ya:yb + 1, xa:xb + 1]
                ok &= depth > sub
                if not ok.any():
                    continue
                w3 = np.array(pts)
                n = np.cross(w3[1] - w3[0], w3[2] - w3[0])
                nn = np.linalg.norm(n)
                n = n / nn if nn > 1e-9 else np.array([0, 1, 0])
                if np.dot(n, cam[2]) < 0:
                    n = -n
                if kind == "glow":
                    lum = 1.15
                else:
                    lum = 0.42 + 0.58 * max(0.0, float(np.dot(n, light))) + 0.18 * max(0.0, float(np.dot(n, fill)))
                rgb = texel[..., :3].astype(np.float32) * lum
                region = color[ya:yb + 1, xa:xb + 1]
                if kind == "fx":
                    al = (alpha.astype(np.float32) / 255.0)[..., None]
                    rgb = region * (1 - al) + rgb * al
                region[ok] = rgb[ok]
                sub[ok] = depth[ok]
        img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), "RGB")
        if ss > 1:
            img = img.resize((size, size), Image.LANCZOS)
        tiles.append(img)
    top = 22 if title else 0
    sheet = Image.new("RGB", (size * len(tiles), size + top), bg)
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * size, top))
    dr = ImageDraw.Draw(sheet)
    if title:
        dr.text((8, 5), title, fill=(235, 235, 235))
    if labels:
        for i, l in enumerate(labels):
            dr.text((i * size + 6, top + 4), l, fill=(200, 200, 210))
    return sheet


def model_scale_for(model: Model, size: int = 420) -> float:
    pts = np.array([p for f in collect_faces(model) for p in f[0]])
    span = max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2]))
    return size / (span * 1.15)
