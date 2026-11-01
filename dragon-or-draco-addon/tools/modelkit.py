"""
modelkit - procedural Bedrock geometry + texture builder used by gen_model.py.

Coordinates are Bedrock geometry units (16 units = 1 block):
  * +Y up, the model faces -Z (north), Bedrock +X is the creature's LEFT side.
  * Bone pivots and cube origins are absolute (model space, rest frame), exactly as in
    the exported .geo.json.  Rotations are Bedrock degrees [x, y, z]:
      +x pitches the front of a bone down, +y swings a -Z pointing part toward +X... see
      kinematics.py for the matrix convention shared with the preview renderer.

Every cube face gets its own rectangle in the texture atlas (per-face UV, 1 texel per
unit) so that each face can be painted with a material that knows its orientation.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

FACES = ("north", "south", "east", "west", "up", "down")

# texture axes of each face expressed as cube axes (0=x, 1=y, 2=z)
FACE_AXES = {
    "north": (0, 1, 2),
    "south": (0, 1, 2),
    "east": (2, 1, 0),
    "west": (2, 1, 0),
    "up": (0, 2, 1),
    "down": (0, 2, 1),
}


@dataclass
class Cube:
    origin: Tuple[float, float, float]
    size: Tuple[float, float, float]
    mat: object  # str or {face: str, "side": str, "default": str}
    faces: Tuple[str, ...] = FACES
    inflate: float = 0.0
    rotation: Optional[Tuple[float, float, float]] = None
    pivot: Optional[Tuple[float, float, float]] = None
    params: dict = field(default_factory=dict)
    share_updown: bool = False  # up and down faces use the same texture rectangle
    uv: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict)  # face -> (u, v, w, h)

    def mat_for(self, face: str) -> str:
        if isinstance(self.mat, str):
            return self.mat
        m = self.mat
        if face in m:
            return m[face]
        if face in ("north", "south", "east", "west") and "side" in m:
            return m["side"]
        return m["default"]


@dataclass
class Bone:
    name: str
    parent: Optional[str]
    pivot: Tuple[float, float, float]
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, dict] = field(default_factory=dict)


def face_dims(size, face):
    a, b, _ = FACE_AXES[face]
    return size[a], size[b]


class Model:
    def __init__(self, identifier: str):
        self.identifier = identifier
        self.bones: Dict[str, Bone] = {}
        self.order: List[str] = []

    # ------------------------------------------------------------------ building
    def bone(self, name, parent, pivot, rotation=(0, 0, 0)) -> Bone:
        assert name not in self.bones, name
        if parent is not None:
            assert parent in self.bones, f"{name}: parent {parent} undefined"
        b = Bone(name, parent, tuple(float(v) for v in pivot), tuple(float(v) for v in rotation))
        self.bones[name] = b
        self.order.append(name)
        return b

    def cube(self, bone: str, origin, size, mat, faces=FACES, inflate=0.0, rotation=None, pivot=None,
             share_updown=False, **params) -> Cube:
        c = Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mat, tuple(faces), inflate,
                 tuple(float(v) for v in rotation) if rotation else None,
                 tuple(float(v) for v in pivot) if pivot else None, params, share_updown)
        self.bones[bone].cubes.append(c)
        return c

    def box(self, bone, center, size, mat, **kw) -> Cube:
        """Cube given by its centre instead of its min corner."""
        o = [center[i] - size[i] / 2 for i in range(3)]
        return self.cube(bone, o, size, mat, **kw)

    def locator(self, bone, name, offset, rotation=None):
        loc = {"offset": [round(v, 4) for v in offset]}
        if rotation:
            loc["rotation"] = list(rotation)
        self.bones[bone].locators[name] = loc

    # ------------------------------------------------------------------ mirroring
    def mirror(self, src_tag="_l_", dst_tag="_r_"):
        """Create right-side bones from every bone whose name contains src_tag."""
        for name in list(self.order):
            if src_tag not in name:
                continue
            b = self.bones[name]
            nb = name.replace(src_tag, dst_tag)
            parent = b.parent.replace(src_tag, dst_tag) if b.parent else None
            px, py, pz = b.pivot
            rx, ry, rz = b.rotation
            m = self.bone(nb, parent, (-px, py, pz), (rx, -ry, -rz))
            for c in b.cubes:
                ox, oy, oz = c.origin
                sx, sy, sz = c.size
                rot = (c.rotation[0], -c.rotation[1], -c.rotation[2]) if c.rotation else None
                piv = (-c.pivot[0], c.pivot[1], c.pivot[2]) if c.pivot else None
                faces = tuple({"east": "west", "west": "east"}.get(f, f) for f in c.faces)
                mat = c.mat
                if isinstance(mat, dict):
                    mat = {({"east": "west", "west": "east"}.get(k, k)): v for k, v in mat.items()}
                params = dict(c.params)
                params["mirrored"] = True
                m.cubes.append(Cube((-(ox + sx), oy, oz), (sx, sy, sz), mat, faces, c.inflate, rot, piv, params,
                                    c.share_updown))
            for ln, loc in b.locators.items():
                o = loc["offset"]
                nl = {"offset": [-o[0], o[1], o[2]]}
                if "rotation" in loc:
                    r = loc["rotation"]
                    nl["rotation"] = [r[0], -r[1], -r[2]]
                m.locators[ln.replace(src_tag, dst_tag)] = nl

    # ------------------------------------------------------------------ uv packing
    def pack(self, width: int, pad: int = 1, skip=lambda bone, cube: False) -> int:
        """Shelf-pack every face rectangle. Returns the atlas height used."""
        rects = []
        for bn in self.order:
            for c in self.bones[bn].cubes:
                if skip(self.bones[bn], c):
                    continue
                for f in c.faces:
                    if c.share_updown and f == "down" and "up" in c.faces:
                        continue
                    w, h = face_dims(c.size, f)
                    w, h = max(1, int(math.ceil(w - 1e-6))), max(1, int(math.ceil(h - 1e-6)))
                    rects.append((h, w, c, f))
        rects.sort(key=lambda r: (-r[0], -r[1]))
        x = y = shelf_h = 0
        for h, w, c, f in rects:
            if x + w + pad > width:
                x = 0
                y += shelf_h + pad
                shelf_h = 0
            c.uv[f] = (x, y, w, h)
            x += w + pad
            shelf_h = max(shelf_h, h)
        for bn in self.order:
            for c in self.bones[bn].cubes:
                if c.share_updown and "up" in c.uv and "down" in c.faces:
                    c.uv["down"] = c.uv["up"]
        return y + shelf_h

    # ------------------------------------------------------------------ painting
    def paint(self, width, height, painters: Dict[str, Callable], seed=1) -> np.ndarray:
        img = np.zeros((height, width, 4), dtype=np.uint8)
        k = 0
        for bn in self.order:
            b = self.bones[bn]
            for c in b.cubes:
                for f, (u, v, w, h) in c.uv.items():
                    if c.share_updown and f == "down":
                        continue
                    mat = c.mat_for(f)
                    painter = painters[mat]
                    k += 1
                    rng = np.random.default_rng(seed * 100003 + k)
                    tile = painter(FaceCtx(f, w, h, c, b, rng))
                    assert tile.shape == (h, w, 4), (mat, f, tile.shape, (h, w))
                    img[v:v + h, u:u + w] = tile
        return img

    # ------------------------------------------------------------------ export
    def to_json(self, tex_w, tex_h, visible_w, visible_h, visible_off, fmt="1.16.0"):
        bones = []
        for bn in self.order:
            b = self.bones[bn]
            jb = {"name": b.name}
            if b.parent:
                jb["parent"] = b.parent
            jb["pivot"] = [r4(v) for v in b.pivot]
            if any(abs(v) > 1e-9 for v in b.rotation):
                jb["rotation"] = [r4(v) for v in b.rotation]
            if b.cubes:
                cubes = []
                for c in b.cubes:
                    jc = {"origin": [r4(v) for v in c.origin], "size": [r4(v) for v in c.size]}
                    if c.inflate:
                        jc["inflate"] = r4(c.inflate)
                    if c.rotation:
                        jc["pivot"] = [r4(v) for v in (c.pivot or center(c))]
                        jc["rotation"] = [r4(v) for v in c.rotation]
                    jc["uv"] = {f: {"uv": [u, v], "uv_size": [w, h]} for f, (u, v, w, h) in c.uv.items()}
                    cubes.append(jc)
                jb["cubes"] = cubes
            if b.locators:
                jb["locators"] = b.locators
            bones.append(jb)
        return {
            "format_version": fmt,
            "minecraft:geometry": [{
                "description": {
                    "identifier": self.identifier,
                    "texture_width": tex_w,
                    "texture_height": tex_h,
                    "visible_bounds_width": visible_w,
                    "visible_bounds_height": visible_h,
                    "visible_bounds_offset": visible_off,
                },
                "bones": bones,
            }],
        }

    def stats(self):
        cubes = sum(len(b.cubes) for b in self.bones.values())
        return len(self.bones), cubes


def center(c: Cube):
    return tuple(c.origin[i] + c.size[i] / 2 for i in range(3))


def r4(v):
    v = round(float(v), 4)
    return int(v) if v == int(v) else v


@dataclass
class FaceCtx:
    face: str
    w: int
    h: int
    cube: Cube
    bone: Bone
    rng: np.random.Generator

    @property
    def axes(self):
        return FACE_AXES[self.face]

    @property
    def p(self):
        return self.cube.params

    def grid(self):
        """(U, V) arrays of texel centres normalised to 0..1."""
        u = (np.arange(self.w) + 0.5) / self.w
        v = (np.arange(self.h) + 0.5) / self.h
        return np.meshgrid(u, v)

    def long_axis_on_face(self):
        """'u', 'v' or 'n' (normal): which texture axis follows the cube's longest side."""
        s = self.cube.size
        la = int(np.argmax(s))
        a, b, n = FACE_AXES[self.face]
        return "u" if la == a else "v" if la == b else "n"
