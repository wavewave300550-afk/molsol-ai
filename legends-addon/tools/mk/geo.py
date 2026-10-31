"""
Procedural Bedrock geometry + texture atlas builder.

A model is a tree of bones, each holding cubes. Every visible cube face gets its
own region of a packed texture atlas (per-face UV) and is painted by a
"painter" (see paint.py) that receives the texel's position on the face *and*
in model space, so patterns such as scales or bronze motifs flow continuously
across neighbouring faces.

Conventions (verified against vanilla geometry and Blockbench's Bedrock codec):
  * units are 1/16 block; the model's front is -Z ("north"), model -X is the
    creature's RIGHT side.  The "east" face is the -X face, "west" is +X.
  * Bedrock rotation [rx, ry, rz] (degrees) acts in model space as the
    right-handed rotation (-rx about X, +ry about Y, -rz about Z), applied X
    first, then Y, then Z.  So +rx pitches a forward-pointing part DOWN,
    +ry turns it to the creature's RIGHT, +rz lifts the creature's LEFT side.
  * up/down faces are written with negative uv_size (Blockbench style).

Bones whose name starts with ``glow_`` are rendered with the emissive material:
their texels get a low alpha (alpha = emissive strength in entity_emissive_alpha).
Bones starting with ``fx_`` use the alpha-blended material.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image

RGBA = Tuple[int, int, int, int]
FACES = ("north", "south", "east", "west", "up", "down")
GLOW_ALPHA = 24          # emissive texels: alpha ~0.1 -> ~90% self-lit
TRANSPARENT: RGBA = (0, 0, 0, 0)

# outward normal of every face in model space
FACE_NORMAL = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (-1, 0, 0),
               "west": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}


@dataclass
class FaceCtx:
    face: str
    x: int
    y: int
    w: int
    h: int
    rng: random.Random
    cube_index: int
    p: Tuple[float, float, float]        # texel centre in (unrotated) cube/bone space, model units
    bone: str
    cube: "Cube"
    variant: int = 0

    @property
    def u(self) -> float:
        return (self.x + 0.5) / self.w

    @property
    def v(self) -> float:
        return (self.y + 0.5) / self.h

    @property
    def edge(self) -> bool:
        return self.x == 0 or self.y == 0 or self.x == self.w - 1 or self.y == self.h - 1

    @property
    def side(self) -> bool:
        return self.face in ("north", "south", "east", "west")

    @property
    def n(self):
        return FACE_NORMAL[self.face]


Painter = Callable[[FaceCtx], RGBA]
Decal = Callable[[Callable[[int, int, RGBA], None], int, int], None]


@dataclass
class Cube:
    origin: Tuple[float, float, float]
    size: Tuple[float, float, float]
    mat: Painter
    inflate: float = 0.0
    pivot: Optional[Tuple[float, float, float]] = None
    rotation: Optional[Tuple[float, float, float]] = None
    decals: Dict[str, Decal] = field(default_factory=dict)
    faces: Optional[Tuple[str, ...]] = None
    face_mats: Dict[str, Painter] = field(default_factory=dict)
    density: Optional[float] = None
    share: Optional[str] = None           # faces with the same share key + face + size reuse one UV region
    mirror: bool = False                  # paint mirrored horizontally (for left/right twins)


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    def add(self, origin, size, mat, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mat, **kw))
        return self

    def box(self, center, size, mat, **kw) -> "Bone":
        """Add a cube by its centre instead of its min corner."""
        c, s = center, size
        return self.add((c[0] - s[0] / 2, c[1] - s[1] / 2, c[2] - s[2] / 2), s, mat, **kw)

    def loc(self, name, at) -> "Bone":
        self.locators[name] = tuple(float(v) for v in at)
        return self


class Model:
    def __init__(self, identifier: str, seed: int = 1, density: float = 1.0):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.density = density
        self.texture: Optional[Image.Image] = None
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.bounds = (4.0, 4.0, 1.5)   # visible bounds width, height, offset y (blocks)

    # ------------------------------------------------------------ building
    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        if any(b.name == name for b in self.bones):
            raise ValueError(f"{self.identifier}: duplicate bone {name}")
        if parent is not None and not any(b.name == parent for b in self.bones):
            raise ValueError(f"{self.identifier}: bone {name} parent {parent} must be declared first")
        b = Bone(name, tuple(float(v) for v in pivot), parent,
                 tuple(float(v) for v in rotation) if rotation else None)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(f"{self.identifier}: no bone {name}")

    def has(self, name) -> bool:
        return any(b.name == name for b in self.bones)

    # ------------------------------------------------------------ packing
    @staticmethod
    def face_dims(c: Cube, face: str) -> Tuple[float, float]:
        sx, sy, sz = c.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def _tex_dims(self, c: Cube, face: str) -> Tuple[int, int]:
        w, h = self.face_dims(c, face)
        # faces carrying hand-drawn decals keep 1 texel per unit so the pixel art stays legible
        d = c.density if c.density is not None else (1.0 if c.decals else self.density)
        return max(1, int(math.ceil(w * d - 0.25))), max(1, int(math.ceil(h * d - 0.25)))

    def _visible_faces(self, c: Cube):
        sx, sy, sz = c.size
        for face in FACES:
            if c.faces is not None and face not in c.faces:
                continue
            w, h = self.face_dims(c, face)
            if w <= 0 or h <= 0:
                continue
            # a zero-thickness plane only needs its two broad faces
            if face in ("north", "south") and sz == 0 and (sx == 0 or sy == 0):
                continue
            yield face

    def pack(self) -> Tuple[int, int]:
        items, shared = [], {}
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face in self._visible_faces(c):
                    tw, th = self._tex_dims(c, face)
                    key = (bi, ci, face)
                    if c.share:
                        sk = (c.share, face, tw, th)
                        if sk in shared:
                            shared[sk].append(key)
                            continue
                        shared[sk] = [key]
                        items.append((key, tw, th, sk))
                    else:
                        items.append((key, tw, th, None))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h, _ in items)
        for W in (64, 128, 256, 512, 1024):
            if W * W * 2 < area * 1.08:
                continue
            placed = {}
            x = y = row_h = 0
            ok = True
            for key, w, h, sk in items:
                if w > W:
                    ok = False
                    break
                if x + w > W:
                    x, y, row_h = 0, y + row_h, 0
                placed[key] = (x, y, w, h)
                if sk:
                    for k2 in shared[sk][1:]:
                        placed[k2] = (x, y, w, h)
                x += w
                row_h = max(row_h, h)
            if not ok:
                continue
            total_h = y + row_h
            H = 16
            while H < total_h:
                H *= 2
            if H <= W * 2:
                self.uv = placed
                self._primary = {k for k, *_ in items}
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier} (area {area})")

    # ------------------------------------------------------------ painting
    @staticmethod
    def _texel_point(c: Cube, face: str, xx: int, yy: int, w: int, h: int):
        (ox, oy, oz), (sx, sy, sz) = c.origin, c.size
        a, b = (xx + 0.5) / w, (yy + 0.5) / h
        if face == "north":
            return ox + a * sx, oy + sy - b * sy, oz
        if face == "south":
            return ox + sx - a * sx, oy + sy - b * sy, oz + sz
        if face == "east":
            return ox, oy + sy - b * sy, oz + sz - a * sz
        if face == "west":
            return ox + sx, oy + sy - b * sy, oz + a * sz
        if face == "up":
            return ox + a * sx, oy + sy, oz + sz - b * sz
        return ox + a * sx, oy, oz + b * sz

    def paint(self, variant: int = 0) -> Image.Image:
        W, H = self.pack()
        img = Image.new("RGBA", (W, H), TRANSPARENT)
        px = img.load()
        rng = random.Random(self.seed)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            if (bi, ci, face) not in self._primary:
                continue
            bone = self.bones[bi]
            c = bone.cubes[ci]
            painter = c.face_mats.get(face, c.mat)
            glow = bone.name.startswith("glow_")
            for yy in range(h):
                for xx in range(w):
                    sxx = (w - 1 - xx) if c.mirror else xx
                    p = self._texel_point(c, face, sxx, yy, w, h)
                    col = painter(FaceCtx(face, sxx, yy, w, h, rng, bi * 31 + ci, p, bone.name, c, variant))
                    if glow and col[3] > 0:
                        col = (col[0], col[1], col[2], GLOW_ALPHA)
                    px[u + xx, v + yy] = col
            dec = c.decals.get(face)
            if dec:
                def setp(x, y, col, u=u, v=v, w=w, h=h, glow=glow, mir=c.mirror):
                    if mir:
                        x = w - 1 - x
                    if 0 <= x < w and 0 <= y < h:
                        if glow and col[3] > 0:
                            col = (col[0], col[1], col[2], GLOW_ALPHA)
                        px[u + x, v + y] = col
                dec(setp, w, h)
        if variant == 0:
            self.texture = img
        return img

    # ------------------------------------------------------------ export
    def geometry_json(self) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.texture.size
        bw, bh, oy = self.bounds
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation and any(b.rotation):
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            if b.locators:
                jb["locators"] = {k: [round(v, 4) for v in p] for k, p in b.locators.items()}
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = round(c.inflate, 4)
                if c.rotation and any(c.rotation):
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 4) for v in c.rotation]
                uv = {}
                for face in FACES:
                    key = (bi, ci, face)
                    if key in self.uv:
                        u, v, w, h = self.uv[key]
                        if face in ("up", "down"):
                            uv[face] = {"uv": [u + w, v + h], "uv_size": [-w, -h]}
                        else:
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
                    "visible_bounds_width": bw,
                    "visible_bounds_height": bh,
                    "visible_bounds_offset": [0, oy, 0],
                },
                "bones": bones,
            }],
        }

    def stats(self) -> dict:
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones),
                "texture": self.texture.size if self.texture else None}
