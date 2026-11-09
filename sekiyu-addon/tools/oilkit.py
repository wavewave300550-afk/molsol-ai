"""
oilkit - procedural Bedrock geometry + texture atlas builder used for every Sekiyu model.

A Model is a list of bones; each cube carries a painter. Painters receive, for every texel of a
face, the texel centre in geometry space (after the cube's own rotation and the bone chain's rest
rotation), the face name and the face-local (u, v) in 0..1, and return RGBA colours. This lets a
model be painted by *projecting* reference art (the fruit), or procedurally (oil, fire, tar).

Faces are packed into one atlas at `tpu` texels per model unit. Geometry is written as format
1.16.0 with per-face UVs (the format that honours bone `binding`, needed for held items).
Face conventions match tools/render_preview.py (Blockbench / Bedrock raw geometry space).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from render_preview import FACES, bedrock_rot

Painter = Callable[[np.ndarray, str, np.ndarray, np.ndarray], np.ndarray]
"""(positions Nx3, face, u N, v N) -> RGBA float array Nx4 in 0..1"""


@dataclass
class Cube:
    origin: Tuple[float, float, float]
    size: Tuple[float, float, float]
    paint: Painter
    rotation: Optional[Tuple[float, float, float]] = None
    pivot: Optional[Tuple[float, float, float]] = None
    inflate: float = 0.0
    faces: Optional[Sequence[str]] = None
    tpu: Optional[float] = None  # per-cube override of texels per unit


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    cubes: List[Cube] = field(default_factory=list)
    binding: Optional[str] = None
    locators: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    def add(self, origin, size, paint, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(map(float, origin)), tuple(map(float, size)), paint, **kw))
        return self


class Model:
    def __init__(self, identifier: str, tpu: float = 2.0, max_tex: int = 512):
        self.identifier = identifier
        self.tpu = tpu
        self.max_tex = max_tex
        self.bones: List[Bone] = []
        self.texture: Optional[Image.Image] = None
        self._uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}

    def bone(self, name, pivot, parent=None, rotation=None, binding=None) -> Bone:
        b = Bone(name, tuple(map(float, pivot)), parent, tuple(rotation) if rotation else None, binding=binding)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        return next(b for b in self.bones if b.name == name)

    # ------------------------------------------------------------------ geometry helpers
    def _bone_world(self):
        byname = {b.name: b for b in self.bones}
        cache = {}

        def world(name):
            if name in cache:
                return cache[name]
            b = byname[name]
            R = bedrock_rot(b.rotation or (0, 0, 0))
            piv = np.array(b.pivot)
            local = lambda v, R=R, piv=piv: (R @ (v - piv).T).T + piv  # noqa: E731
            if b.parent:
                pw = world(b.parent)
                fn = lambda v, pw=pw, local=local: pw(local(v))  # noqa: E731
            else:
                fn = local
            cache[name] = fn
            return fn

        return world

    @staticmethod
    def _face_size(c: Cube, face: str):
        sx, sy, sz = (s + 2 * c.inflate for s in c.size)
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def _faces(self):
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face in FACES:
                    if c.faces is not None and face not in c.faces:
                        continue
                    w, h = self._face_size(c, face)
                    if w <= 1e-6 or h <= 1e-6:
                        continue
                    tpu = c.tpu or self.tpu
                    yield (bi, ci, face), max(1, int(math.ceil(w * tpu - 1e-6))), max(1, int(math.ceil(h * tpu - 1e-6)))

    def pack(self):
        items = sorted(self._faces(), key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        W = 32
        while W <= self.max_tex:
            if W * W >= area * 1.05:
                placed, x, y, row = {}, 0, 0, 0
                ok = True
                for key, w, h in items:
                    if w > W:
                        ok = False
                        break
                    if x + w > W:
                        x, y, row = 0, y + row, 0
                    placed[key] = (x, y, w, h)
                    x += w
                    row = max(row, h)
                if ok and y + row <= W:
                    H = 16
                    while H < y + row:
                        H *= 2
                    self._uv = placed
                    return W, H
            W *= 2
        raise RuntimeError(f"{self.identifier}: texture would exceed {self.max_tex}px")

    def paint(self) -> Image.Image:
        W, H = self.pack()
        tex = np.zeros((H, W, 4), np.float32)
        world = self._bone_world()
        for (bi, ci, face), (u0, v0, w, h) in self._uv.items():
            b = self.bones[bi]
            c = b.cubes[ci]
            o = np.array(c.origin) - c.inflate
            s = np.array(c.size) + 2 * c.inflate
            sel, ua, va, _ = FACES[face]
            tl = np.where(np.array(sel) == 1, o + s, o)
            du = np.array(ua, float) * s
            dv = np.array(va, float) * s
            uu, vv = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
            pts = tl + uu.reshape(-1, 1) * du + vv.reshape(-1, 1) * dv
            if c.rotation:
                piv = np.array(c.pivot if c.pivot else c.origin)
                pts = (bedrock_rot(c.rotation) @ (pts - piv).T).T + piv
            pts = world(b.name)(pts)
            rgba = np.asarray(c.paint(pts, face, uu.reshape(-1), vv.reshape(-1)), np.float32).reshape(h, w, 4)
            tex[v0:v0 + h, u0:u0 + w] = rgba
        self.texture = Image.fromarray((np.clip(tex, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        return self.texture

    def geometry(self, bounds=(3, 3), offset=(0, 1, 0)) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.texture.size
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation:
                jb["rotation"] = [round(v, 3) for v in b.rotation]
            if b.binding:
                jb["binding"] = b.binding
            if b.locators:
                jb["locators"] = {k: [round(x, 4) for x in v] for k, v in b.locators.items()}
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = round(c.inflate, 4)
                if c.rotation:
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 3) for v in c.rotation]
                uv = {}
                for face in FACES:
                    k = (bi, ci, face)
                    if k in self._uv:
                        u, v, w, h = self._uv[k]
                        uv[face] = {"uv": [u, v], "uv_size": [w, h]}
                jc["uv"] = uv
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            bones.append(jb)
        return {
            "format_version": "1.16.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": self.identifier,
                    "texture_width": W,
                    "texture_height": H,
                    "visible_bounds_width": bounds[0],
                    "visible_bounds_height": bounds[1],
                    "visible_bounds_offset": list(offset),
                },
                "bones": bones,
            }],
        }

    def stats(self):
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones),
                "texture": None if self.texture is None else self.texture.size}


# --------------------------------------------------------------------------- painters / noise

def value_noise(p: np.ndarray, scale: float, seed: int = 0) -> np.ndarray:
    """Smooth 3D value noise in 0..1 for points Nx3 (hash-based, deterministic)."""
    q = p / scale
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)

    def h(ix, iy, iz):
        n = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
        n = (n ^ (n >> 13)) * 1274126177
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    ii = i.astype(np.int64)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(ii[:, 0] + dx, ii[:, 1] + dy, ii[:, 2] + dz)
    return out


def fbm(p, scale, seed=0, octaves=4):
    tot, amp, s, norm = 0, 1.0, scale, 0
    for o in range(octaves):
        tot = tot + value_noise(p, s, seed + o * 17) * amp
        norm += amp
        amp *= 0.5
        s *= 0.5
    return tot / norm


def rgb(hexstr):
    h = hexstr.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def solid(hexstr, alpha=1.0) -> Painter:
    c = rgb(hexstr)

    def p(pts, face, u, v):
        out = np.empty((len(pts), 4), np.float32)
        out[:, :3] = c
        out[:, 3] = alpha
        return out
    return p
