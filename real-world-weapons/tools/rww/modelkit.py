"""
modelkit — procedural cube models with per-face UV atlases.

A model is a set of bones holding boxes.  Every box carries a `part` name and
free-form `meta`; painters receive, for each texel, the face name and the
texel's position in model space (file coordinates, box rotation not applied),
so textures can follow the real geometry (bevels, fullers, hamon lines, wraps).

All three swords of a type share one geometry/UV layout; each material tier is
just a different painter set, so the 7 textures of a weapon are UV-identical.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

from .render import cube_box, face_quad
from .bedrock import Cube

FACES = ("east", "west", "up", "down", "south", "north")
Vec = Tuple[float, float, float]


@dataclass
class Box:
    origin: Vec
    size: Vec
    part: str
    pivot: Optional[Vec] = None
    rotation: Optional[Vec] = None
    inflate: float = 0.0
    faces: Optional[Sequence[str]] = None
    meta: dict = field(default_factory=dict)


@dataclass
class MBone:
    name: str
    pivot: Vec
    parent: Optional[str] = None
    binding: Optional[str] = None
    rotation: Optional[Vec] = None
    boxes: List[Box] = field(default_factory=list)


@dataclass
class Texel:
    face: str
    x: int
    y: int
    w: int
    h: int
    p: np.ndarray          # model-space (file) position of the texel centre
    fu: float              # 0..1 across the face (u)
    fv: float              # 0..1 down the face (v)
    box: Box


Painter = Callable[[Texel], Tuple[int, int, int, int]]


def face_dims(size: Vec, face: str) -> Tuple[float, float]:
    sx, sy, sz = size
    if face in ("north", "south"):
        return sx, sy
    if face in ("east", "west"):
        return sz, sy
    return sx, sz


class Model:
    def __init__(self, identifier: str, density: float = 8.0):
        self.identifier = identifier
        self.density = density
        self.bones: List[MBone] = []
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.size: Tuple[int, int] = (0, 0)

    def bone(self, name, pivot, parent=None, binding=None, rotation=None) -> MBone:
        b = MBone(name, tuple(pivot), parent, binding, tuple(rotation) if rotation else None)
        self.bones.append(b)
        return b

    @staticmethod
    def add(bone: MBone, origin, size, part, **kw) -> Box:
        bx = Box(tuple(float(v) for v in origin), tuple(float(v) for v in size), part, **kw)
        bone.boxes.append(bx)
        return bx

    # ------------------------------------------------------------------ helpers for curved parts
    def segment(self, bone: MBone, a: Vec, b: Vec, thick: Tuple[float, float], part: str, plane: str = "yz",
                overlap: float = 0.0, **meta) -> Box:
        """A bar from point a to b (file coords) lying in `plane` ('yz' rotates about x, 'xy' about z,
        'xz' about y).  `thick` = (width across the plane normal, depth in-plane)."""
        a, b = np.array(a, float), np.array(b, float)
        mid = (a + b) / 2
        d = b - a
        L = float(np.linalg.norm(d)) + overlap
        # File-space Euler -> display: (rx, ry, rz) -> (-rx, -ry, rz) and x_disp = -x_file.
        if plane == "yz":       # bar along +y, rotated about x so that +y -> d
            ang = math.degrees(math.atan2(d[2], d[1]))
            size = (thick[0], L, thick[1])
            rot = (-ang, 0.0, 0.0)
        elif plane == "xy":     # bar along +y, rotated about z
            ang = math.degrees(math.atan2(d[0], d[1]))
            size = (thick[1], L, thick[0])
            rot = (0.0, 0.0, ang)
        else:                   # 'xz': bar along +z, rotated about y
            ang = math.degrees(math.atan2(d[0], d[2]))
            size = (thick[1], thick[0], L)
            rot = (0.0, ang, 0.0)
        origin = (mid[0] - size[0] / 2, mid[1] - size[1] / 2, mid[2] - size[2] / 2)
        return self.add(bone, origin, size, part, pivot=tuple(mid), rotation=rot, meta=dict(meta))

    def bar(self, bone: MBone, a: Vec, b: Vec, thick: Tuple[float, float], part: str, overlap: float = 0.0,
            **meta) -> Box:
        """A bar from a to b in any direction (file coords).  Uses file Euler (rx, 0, rz):
        display M = Rz(g) * Rx(-rx) maps +y onto the bar direction."""
        a, b = np.array(a, float), np.array(b, float)
        mid = (a + b) / 2
        d = b - a
        L = float(np.linalg.norm(d))
        u = d / L
        rx = -math.degrees(math.asin(max(-1.0, min(1.0, u[2]))))
        rz = math.degrees(math.atan2(u[0], u[1]))
        size = (thick[0], L + overlap, thick[1])
        origin = (mid[0] - size[0] / 2, mid[1] - size[1] / 2, mid[2] - size[2] / 2)
        return self.add(bone, origin, size, part, pivot=tuple(mid), rotation=(rx, 0.0, rz), meta=dict(meta))

    def polyline(self, bone, pts, thick, part, plane="yz", overlap=0.12, **meta):
        out = []
        for i in range(len(pts) - 1):
            if plane == "3d":
                out.append(self.bar(bone, pts[i], pts[i + 1], thick, part, overlap, seg=i, nseg=len(pts) - 1, **meta))
            else:
                out.append(self.segment(bone, pts[i], pts[i + 1], thick, part, plane, overlap, seg=i,
                                        nseg=len(pts) - 1, **meta))
        return out

    def ellipse(self, bone, center, r1, r2, plane, n, thick, part, start=0.0, end=360.0, **meta):
        """Ring/arc approximated by n bars.  plane 'xz' (horizontal), 'yz' or 'xy'."""
        pts = []
        for i in range(n + 1):
            a = math.radians(start + (end - start) * i / n)
            c, s = math.cos(a) * r1, math.sin(a) * r2
            if plane == "xz":
                pts.append((center[0] + c, center[1], center[2] + s))
            elif plane == "yz":
                pts.append((center[0], center[1] + s, center[2] + c))
            else:
                pts.append((center[0] + c, center[1] + s, center[2]))
        return self.polyline(bone, pts, thick, part, plane="3d", overlap=0.1, **meta)

    # ------------------------------------------------------------------ layout
    def layout(self, max_w: int = 512):
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.boxes):
                for face in FACES:
                    if c.faces is not None and face not in c.faces:
                        continue
                    w, h = face_dims(c.size, face)
                    tw = max(1, int(math.ceil(w * self.density - 1e-6)))
                    th = max(1, int(math.ceil(h * self.density - 1e-6)))
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1], it[0]))
        area = sum(w * h for _, w, h in items)
        W = 64
        while W * W < area * 1.25 or any(w > W for _, w, _ in items):
            W *= 2
        while True:
            placed = {}
            x = y = row_h = 0
            for key, w, h in items:
                if x + w > W:
                    x, y = 0, y + row_h
                    row_h = 0
                placed[key] = (x, y, w, h)
                x += w
                row_h = max(row_h, h)
            total = y + row_h
            H = 16
            while H < total:
                H *= 2
            if H <= W * 2 or W >= max_w:
                break
            W *= 2
        self.uv = placed
        self.size = (W, H)
        return W, H

    # ------------------------------------------------------------------ painting
    def paint(self, painters: Dict[str, Painter], default: Optional[Painter] = None) -> Image.Image:
        if not self.uv:
            self.layout()
        W, H = self.size
        arr = np.zeros((H, W, 4), np.uint8)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            box = self.bones[bi].boxes[ci]
            painter = painters.get(box.part, default)
            if painter is None:
                raise KeyError(f"no painter for part {box.part!r}")
            lo, hi = cube_box(Cube(box.origin, box.size, box.inflate))
            q = face_quad(face, lo, hi)   # display space TL, TR, BL, BR
            du, dv = q[1] - q[0], q[2] - q[0]
            for yy in range(h):
                for xx in range(w):
                    fu, fv = (xx + 0.5) / w, (yy + 0.5) / h
                    pd = q[0] + du * fu + dv * fv
                    p = np.array([-pd[0], pd[1], pd[2]])
                    arr[v + yy, u + xx] = painter(Texel(face, xx, yy, w, h, p, fu, fv, box))
        return Image.fromarray(arr, "RGBA")

    # ------------------------------------------------------------------ export
    def geometry_json(self, bounds=(4.0, 4.0), offset=(0.0, 1.5, 0.0)) -> dict:
        if not self.uv:
            self.layout()
        W, H = self.size
        bones = []
        for bi, b in enumerate(self.bones):
            jb: dict = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.binding:
                jb["binding"] = b.binding
            if b.rotation:
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            cubes = []
            for ci, c in enumerate(b.boxes):
                jc: dict = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = round(c.inflate, 4)
                if c.rotation and any(abs(r) > 1e-9 for r in c.rotation):
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 4) for v in c.rotation]
                uv = {}
                for face in FACES:
                    key = (bi, ci, face)
                    if key not in self.uv:
                        continue
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
                    "texture_width": W, "texture_height": H,
                    "visible_bounds_width": bounds[0], "visible_bounds_height": bounds[1],
                    "visible_bounds_offset": list(offset),
                },
                "bones": bones,
            }],
        }

    def stats(self):
        return {"bones": len(self.bones), "cubes": sum(len(b.boxes) for b in self.bones), "texture": self.size}
