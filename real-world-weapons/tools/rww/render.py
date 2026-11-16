"""
Software rasterizer for Bedrock geometry (z-buffer, perspective-correct UV,
alpha-tested textures, simple directional shading).  Used to render model
sheets, icons, and first/third-person animation previews without the game.

Face vertex / UV layout follows Blockbench (three.js BoxGeometry order), which
matches how Bedrock maps per-face UVs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from .bedrock import Cube, Geo, disp, euler_file_to_matrix, trans

FACES = ("east", "west", "up", "down", "south", "north")


def cube_box(c: Cube):
    """Display-space min/max corners (inflate applied)."""
    ox, oy, oz = c.origin
    sx, sy, sz = c.size
    i = c.inflate or 0.0
    x0, x1 = -(ox + sx) - i, -ox + i
    return np.array([x0, oy - i, oz - i]), np.array([x1, oy + sy + i, oz + sz + i])


def face_quad(face: str, lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    q = {
        "east": ((x1, y1, z1), (x1, y1, z0), (x1, y0, z1), (x1, y0, z0)),
        "west": ((x0, y1, z0), (x0, y1, z1), (x0, y0, z0), (x0, y0, z1)),
        "up": ((x0, y1, z0), (x1, y1, z0), (x0, y1, z1), (x1, y1, z1)),
        "down": ((x0, y0, z1), (x1, y0, z1), (x0, y0, z0), (x1, y0, z0)),
        "south": ((x0, y1, z1), (x1, y1, z1), (x0, y0, z1), (x1, y0, z1)),
        "north": ((x1, y1, z0), (x0, y1, z0), (x1, y0, z0), (x0, y0, z0)),
    }[face]
    return np.array(q, dtype=float)


def box_uv_rects(c: Cube):
    """Blockbench-internal [u0, v0, u1, v1] per face for box UV."""
    u, v = c.uv
    sx, sy, sz = c.size
    fl = {
        "east": ([0, sz], [sz, sy]), "west": ([sz + sx, sz], [sz, sy]),
        "up": ([sz + sx, sz], [-sx, -sz]), "down": ([sz + sx * 2, 0], [-sx, sz]),
        "south": ([sz * 2 + sx, sz], [sx, sy]), "north": ([sz, sz], [sx, sy]),
    }
    if c.mirror:
        fl = {k: ([f[0][0] + f[1][0], f[0][1]], [-f[1][0], f[1][1]]) for k, f in fl.items()}
        fl["east"], fl["west"] = fl["west"], fl["east"]
    return {k: [o[0] + u, o[1] + v, o[0] + s[0] + u, o[1] + s[1] + v] for k, (o, s) in fl.items()}


def face_uv_rect(c: Cube, face: str):
    if c.uv is None:
        return None
    if isinstance(c.uv, (list, tuple)):
        return box_uv_rects(c)[face]
    f = c.uv.get(face)
    if not f:
        return None
    u, v = f["uv"]
    w, h = f.get("uv_size", [0, 0])
    if face in ("up", "down"):
        return [u + w, v + h, u, v]
    return [u, v, u + w, v + h]


@dataclass
class Instance:
    geo: Geo
    texture: np.ndarray              # HxWx4 uint8
    mats: Dict[str, np.ndarray]      # bone -> 4x4 display world matrix
    visible: Optional[Callable[[str], bool]] = None
    tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class Camera:
    eye: Sequence[float]
    target: Sequence[float]
    up: Sequence[float] = (0, 1, 0)
    fov: float = 70.0               # vertical degrees (perspective)
    ortho: Optional[float] = None   # half-height in world units (orthographic)
    near: float = 0.5

    def view(self):
        e, t, u = np.array(self.eye, float), np.array(self.target, float), np.array(self.up, float)
        f = t - e
        f /= np.linalg.norm(f)
        r = np.cross(f, u)
        r /= np.linalg.norm(r)
        uu = np.cross(r, f)
        m = np.eye(4)
        m[0, :3], m[1, :3], m[2, :3] = r, uu, -f
        m[:3, 3] = -m[:3, :3] @ e
        return m


def collect_tris(instances: Iterable[Instance]):
    """Yield (verts 3x3 world, uvs 3x2 pixel, texture index, normal) triangles."""
    tris = []
    textures = []
    for inst in instances:
        ti = len(textures)
        textures.append((inst.texture, inst.tint))
        for bname in inst.geo.order:
            b = inst.geo.bones[bname]
            if b.never_render or not b.cubes:
                continue
            if inst.visible is not None and not inst.visible(bname):
                continue
            M = inst.mats[bname]
            for c in b.cubes:
                lo, hi = cube_box(c)
                CM = np.eye(4)
                if c.rotation and any(abs(r) > 1e-9 for r in c.rotation):
                    piv = disp(c.pivot if c.pivot else c.origin)
                    CM = trans(piv) @ euler_file_to_matrix(c.rotation) @ trans(-piv)
                MM = M @ CM
                for face in FACES:
                    rect = face_uv_rect(c, face)
                    if rect is None:
                        continue
                    q = face_quad(face, lo, hi)
                    qw = (MM @ np.c_[q, np.ones(4)].T).T[:, :3]
                    u0, v0, u1, v1 = rect
                    uv = np.array([[u0, v0], [u1, v0], [u0, v1], [u1, v1]], float)
                    n = np.cross(qw[1] - qw[0], qw[2] - qw[0])
                    nl = np.linalg.norm(n)
                    if nl < 1e-12:
                        continue
                    n /= nl
                    tris.append((qw[[0, 2, 1]], uv[[0, 2, 1]], ti, -n))
                    tris.append((qw[[1, 2, 3]], uv[[1, 2, 3]], ti, -n))
    return tris, textures


def render(instances: Iterable[Instance], camera: Camera, size=(640, 480), bg=(32, 36, 44, 255), ss: int = 2,
           light=(0.35, 1.0, 0.6), ambient=0.48, out_mask: bool = False):
    W, H = size[0] * ss, size[1] * ss
    tris, textures = collect_tris(instances)
    view = camera.view()
    aspect = W / H
    color = np.zeros((H, W, 3), np.float32)
    color[:] = np.array(bg[:3], np.float32)
    alpha = np.zeros((H, W), np.float32)
    zbuf = np.full((H, W), np.inf, np.float32)
    L = np.array(light, float)
    L /= np.linalg.norm(L)
    f = 1.0 / math.tan(math.radians(camera.fov) / 2)

    for verts, uvs, ti, normal in tris:
        vv = (view @ np.c_[verts, np.ones(3)].T).T[:, :3]   # camera space, looking -z
        depth = -vv[:, 2]
        if camera.ortho is None:
            if np.any(depth < camera.near):
                continue
            sx = vv[:, 0] * f / aspect / depth
            sy = vv[:, 1] * f / depth
        else:
            sx = vv[:, 0] / (camera.ortho * aspect)
            sy = vv[:, 1] / camera.ortho
        px = (sx * 0.5 + 0.5) * W
        py = (0.5 - sy * 0.5) * H
        area = (px[1] - px[0]) * (py[2] - py[0]) - (px[2] - px[0]) * (py[1] - py[0])
        if abs(area) < 1e-9:
            continue
        xmin, xmax = int(max(0, math.floor(px.min()))), int(min(W - 1, math.ceil(px.max())))
        ymin, ymax = int(max(0, math.floor(py.min()))), int(min(H - 1, math.ceil(py.max())))
        if xmin > xmax or ymin > ymax:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        w0 = ((px[1] - gx) * (py[2] - gy) - (px[2] - gx) * (py[1] - gy)) / area
        w1 = ((px[2] - gx) * (py[0] - gy) - (px[0] - gx) * (py[2] - gy)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        if camera.ortho is None:
            iz = np.array([1 / depth[0], 1 / depth[1], 1 / depth[2]])
            zi = w0 * iz[0] + w1 * iz[1] + w2 * iz[2]
            z = 1 / np.maximum(zi, 1e-9)
            pu = (w0 * uvs[0, 0] * iz[0] + w1 * uvs[1, 0] * iz[1] + w2 * uvs[2, 0] * iz[2]) * z
            pv = (w0 * uvs[0, 1] * iz[0] + w1 * uvs[1, 1] * iz[1] + w2 * uvs[2, 1] * iz[2]) * z
        else:
            z = w0 * depth[0] + w1 * depth[1] + w2 * depth[2]
            pu = w0 * uvs[0, 0] + w1 * uvs[1, 0] + w2 * uvs[2, 0]
            pv = w0 * uvs[0, 1] + w1 * uvs[1, 1] + w2 * uvs[2, 1]
        tex, tint = textures[ti]
        th, tw = tex.shape[:2]
        tu = np.clip(np.floor(pu - 1e-4 * np.sign(uvs[:, 0].mean() - pu)), 0, tw - 1).astype(int)
        tv = np.clip(np.floor(pv - 1e-4 * np.sign(uvs[:, 1].mean() - pv)), 0, th - 1).astype(int)
        texel = tex[tv, tu]
        sub_z = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        mask = inside & (texel[..., 3] >= 128) & (z < sub_z)
        if not mask.any():
            continue
        shade = ambient + (1 - ambient) * max(0.0, float(np.dot(normal, L)))
        # gentle extra darkening for downward faces, like Minecraft's face shading
        shade *= 0.8 + 0.2 * (0.5 + 0.5 * normal[1])
        rgb = texel[..., :3].astype(np.float32) * shade * np.array(tint, np.float32)
        sub_z[mask] = z[mask]
        sub_c = color[ymin:ymax + 1, xmin:xmax + 1]
        sub_c[mask] = rgb[mask]
        alpha[ymin:ymax + 1, xmin:xmax + 1][mask] = 1.0

    img = np.clip(color, 0, 255).astype(np.uint8)
    rgba = np.dstack([img, (np.maximum(alpha, bg[3] / 255.0) * 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA")
    if ss > 1:
        im = im.resize(size, Image.LANCZOS)
    return im


def texture_array(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGBA"), dtype=np.uint8)
