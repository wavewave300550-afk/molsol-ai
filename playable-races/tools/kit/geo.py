"""Procedural Bedrock geometry with per-face UV atlases.

Conventions (Bedrock JSON space, units of 1/16 block):
  * +Y is up, the model faces -Z (the "north" face is the front),
  * -X is the creature's RIGHT side, +X its LEFT side,
  * a bone/cube rotation [rx, ry, rz] (degrees) is applied X first, then Y,
    then Z.  Expressed as standard right-handed matrices acting on JSON
    coordinates the rotation is  Rz(-rz) . Ry(ry) . Rx(-rx).
    (positive rx pitches the front down, positive ry turns to the creature's
    right, positive rz swings a right arm outward).

Faces and texture orientation (what "u to the right / v down" means on the
model, seen from outside the face):
  north (front, -Z): u runs -X -> +X ; v runs top -> bottom
  south (back,  +Z): u runs +X -> -X
  east  (-X, creature's right): u runs +Z -> -Z
  west  (+X, creature's left) : u runs -Z -> +Z
  up    (+Y): u runs -X -> +X ; v runs +Z (back) -> -Z (front)
  down  (-Y): u runs -X -> +X ; v runs -Z (front) -> +Z (back)
Face naming (east = -X) was confirmed with Minecraft Creator Tools' renderer
(tools/check_conventions.py).  Rotation signs follow Blockbench's Bedrock codec
(x mirrored; [-rx, -ry, rz] right-handed) - Creator Tools' preview does not apply
bone rotations, so it cannot confirm those.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

V3 = Tuple[float, float, float]
FACES = ("north", "south", "east", "west", "up", "down")
NORMALS = {
    "north": (0.0, 0.0, -1.0), "south": (0.0, 0.0, 1.0),
    "east": (-1.0, 0.0, 0.0), "west": (1.0, 0.0, 0.0),
    "up": (0.0, 1.0, 0.0), "down": (0.0, -1.0, 0.0),
}


# --------------------------------------------------------------------------- math

def rot_matrix(r: Sequence[float]) -> np.ndarray:
    """Bedrock rotation [rx, ry, rz] as a 3x3 matrix acting on JSON coords."""
    rx, ry, rz = (math.radians(a) for a in r)
    ax, ay, az = -rx, ry, -rz
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def face_frame(face: str, o: Sequence[float], s: Sequence[float]):
    """Return (corner_u0v0, du_vec, dv_vec, width, height) for a face of a box.

    corner + a*du + b*dv for a,b in [0,1] spans the face, u->right, v->down."""
    x0, y0, z0 = o
    x1, y1, z1 = o[0] + s[0], o[1] + s[1], o[2] + s[2]
    w, h, d = s
    if face == "north":
        return np.array([x0, y1, z0]), np.array([w, 0, 0]), np.array([0, -h, 0]), w, h
    if face == "south":
        return np.array([x1, y1, z1]), np.array([-w, 0, 0]), np.array([0, -h, 0]), w, h
    if face == "east":
        return np.array([x0, y1, z1]), np.array([0, 0, -d]), np.array([0, -h, 0]), d, h
    if face == "west":
        return np.array([x1, y1, z0]), np.array([0, 0, d]), np.array([0, -h, 0]), d, h
    if face == "up":
        return np.array([x0, y1, z1]), np.array([w, 0, 0]), np.array([0, 0, -d]), w, d
    if face == "down":
        return np.array([x0, y0, z0]), np.array([w, 0, 0]), np.array([0, 0, d]), w, d
    raise ValueError(face)


# --------------------------------------------------------------------------- model

@dataclass
class Cube:
    origin: V3
    size: V3
    mat: str
    pivot: Optional[V3] = None
    rot: Optional[V3] = None
    inflate: float = 0.0
    faces: Optional[Set[str]] = None      # restrict emitted faces
    cutout: bool = False                  # rendered in the alpha-test pass
    accent: bool = False                  # armour-assimilation accent pass (tinted per armour material)
    only: Optional[Set[str]] = None       # variants that include this cube (None = all)
    skip: Optional[Set[str]] = None       # variants that exclude this cube
    ppu: Optional[float] = None           # texel density override
    seed: int = 0
    uv: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict)  # face -> (u,v,w,h)

    def emitted_faces(self) -> List[str]:
        out = []
        w, h, d = self.size
        for f in FACES:
            if self.faces is not None and f not in self.faces:
                continue
            fw, fh = {"north": (w, h), "south": (w, h), "east": (d, h), "west": (d, h),
                      "up": (w, d), "down": (w, d)}[f]
            if fw <= 1e-6 or fh <= 1e-6:
                continue
            out.append(f)
        return out

    def in_variant(self, variant: str) -> bool:
        if self.only is not None and variant not in self.only:
            return False
        if self.skip is not None and variant in self.skip:
            return False
        return True


@dataclass
class Bone:
    name: str
    parent: Optional[str]
    pivot: V3
    rot: V3 = (0.0, 0.0, 0.0)
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, V3] = field(default_factory=dict)
    # variant -> (translation applied to the whole subtree, rotation override)
    variant: Dict[str, Tuple[V3, Optional[V3]]] = field(default_factory=dict)
    only: Optional[Set[str]] = None       # variants that include the bone
    never_render: bool = False


class Model:
    def __init__(self, name: str, ppu: float = 2.0, atlas_width: int = 512):
        self.name = name
        self.ppu = ppu
        self.atlas_width = atlas_width
        self.bones: Dict[str, Bone] = {}
        self.order: List[str] = []
        self.tex_w = atlas_width
        self.tex_h = 0

    # -- construction -------------------------------------------------------
    def bone(self, name: str, parent: Optional[str], pivot: Sequence[float],
             rot: Sequence[float] = (0, 0, 0), **kw) -> Bone:
        if name in self.bones:
            raise ValueError(f"duplicate bone {name}")
        if parent is not None and parent not in self.bones:
            raise ValueError(f"bone {name}: unknown parent {parent}")
        b = Bone(name, parent, tuple(float(v) for v in pivot), tuple(float(v) for v in rot), **kw)
        self.bones[name] = b
        self.order.append(name)
        return b

    def cube(self, bone: str, origin: Sequence[float], size: Sequence[float], mat: str, **kw) -> Cube:
        c = Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mat, **kw)
        if c.pivot is not None:
            c.pivot = tuple(float(v) for v in c.pivot)
        if c.rot is not None:
            c.rot = tuple(float(v) for v in c.rot)
        c.seed = len(self.bones[bone].cubes) * 131 + len(self.order) * 7
        self.bones[bone].cubes.append(c)
        return c

    def box(self, bone: str, center: Sequence[float], size: Sequence[float], mat: str, **kw) -> Cube:
        o = [center[i] - size[i] / 2 for i in range(3)]
        return self.cube(bone, o, size, mat, **kw)

    def children(self, name: str) -> List[str]:
        return [b for b in self.order if self.bones[b].parent == name]

    def subtree(self, name: str) -> List[str]:
        out = [name]
        for c in self.children(name):
            out.extend(self.subtree(c))
        return out

    # -- atlas ---------------------------------------------------------------
    def pack(self, pad: int = 0) -> None:
        """Assign a unique texture rectangle to every emitted face (skyline bottom-left packer).
        Tries a 256-wide atlas first (keeps each texture within the 256 KB memory budget)."""
        rects = []
        for bn in self.order:
            for c in self.bones[bn].cubes:
                ppu = c.ppu or self.ppu
                for f in c.emitted_faces():
                    _, _, _, fw, fh = face_frame(f, c.origin, c.size)
                    pw = max(1, int(math.ceil(fw * ppu - 1e-6)))
                    ph = max(1, int(math.ceil(fh * ppu - 1e-6)))
                    rects.append((ph, pw, c, f))
        rects.sort(key=lambda r: (-r[0], -r[1]))
        for W in sorted({256, self.atlas_width, 512, 1024}):
            placed = _skyline(rects, W, pad)
            if placed is not None:
                h = placed[1]
                p2 = 16
                while p2 < h:
                    p2 *= 2
                if p2 <= W or W >= 1024:
                    for (c, f), (x, y, w, hh) in placed[0]:
                        c.uv[f] = (x, y, w, hh)
                    self.tex_w, self.tex_h = W, p2
                    return
        raise RuntimeError("atlas packing failed")

    # -- transforms ------------------------------------------------------------
    def variant_offset(self, bone: str, variant: Optional[str]) -> np.ndarray:
        """Total translation applied to `bone` by variant overrides of itself/ancestors."""
        off = np.zeros(3)
        b: Optional[str] = bone
        while b is not None:
            bb = self.bones[b]
            if variant and variant in bb.variant:
                off += np.array(bb.variant[variant][0], dtype=float)
            b = bb.parent
        return off

    def bone_rot(self, bone: str, variant: Optional[str]) -> V3:
        bb = self.bones[bone]
        if variant and variant in bb.variant and bb.variant[variant][1] is not None:
            return bb.variant[variant][1]  # type: ignore
        return bb.rot

    def bone_in_variant(self, bone: str, variant: Optional[str]) -> bool:
        b: Optional[str] = bone
        while b is not None:
            bb = self.bones[b]
            if variant is not None and bb.only is not None and variant not in bb.only:
                return False
            b = bb.parent
        return True

    # -- export ------------------------------------------------------------------
    def geometry_json(self, identifier: str, *, variant: Optional[str] = None,
                      cutout: Optional[bool] = None, accent: bool = False, inflate_extra: float = 0.0,
                      bounds: Tuple[float, float, Sequence[float]] = (3, 3, (0, 1.5, 0)),
                      include_bone: Optional[Iterable[str]] = None) -> dict:
        """Emit a geometry definition.

        cutout=None -> all cubes; True -> only cutout cubes; False -> only solid cubes.
        Bones are always emitted (keeps the hierarchy identical across passes)."""
        bones_out = []
        allow = set(include_bone) if include_bone is not None else None
        for bn in self.order:
            b = self.bones[bn]
            if not self.bone_in_variant(bn, variant):
                continue
            if allow is not None and bn not in allow:
                continue
            off = self.variant_offset(bn, variant)
            jb: dict = {"name": bn}
            if b.parent:
                jb["parent"] = b.parent
            jb["pivot"] = _r3(np.array(b.pivot) + off)
            rot = self.bone_rot(bn, variant)
            if any(abs(v) > 1e-9 for v in rot):
                jb["rotation"] = _r3(rot)
            if b.never_render:
                jb["neverRender"] = True
            cubes = []
            for c in b.cubes:
                if not c.in_variant(variant or "base"):
                    continue
                if cutout is not None and c.cutout != cutout:
                    continue
                if c.accent != accent:
                    continue
                jc: dict = {"origin": _r3(np.array(c.origin) + off), "size": _r3(c.size)}
                if c.rot is not None and any(abs(v) > 1e-9 for v in c.rot):
                    jc["pivot"] = _r3(np.array(c.pivot if c.pivot else c.origin) + off)
                    jc["rotation"] = _r3(c.rot)
                inf = c.inflate + inflate_extra
                if abs(inf) > 1e-9:
                    jc["inflate"] = round(inf, 4)
                uv = {}
                for f in c.emitted_faces():
                    u, v, w, h = c.uv[f]
                    uv[f] = {"uv": [u, v], "uv_size": [w, h]}
                jc["uv"] = uv
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            if b.locators:
                jb["locators"] = {k: _r3(np.array(v) + off) for k, v in b.locators.items()}
            bones_out.append(jb)
        bw, bh, bo = bounds
        return {
            "description": {
                "identifier": identifier,
                "texture_width": self.tex_w,
                "texture_height": self.tex_h,
                "visible_bounds_width": bw,
                "visible_bounds_height": bh,
                "visible_bounds_offset": list(bo),
            },
            "bones": bones_out,
        }

    def has_layer(self, variant: str, cutout: bool = False, accent: bool = False) -> bool:
        for bn in self.order:
            if not self.bone_in_variant(bn, variant):
                continue
            for c in self.bones[bn].cubes:
                if c.in_variant(variant) and c.cutout == cutout and c.accent == accent:
                    return True
        return False

    def accent_bones(self, variant: str, prefix: str) -> List[str]:
        return [bn for bn in self.order if bn.startswith(prefix) and self.bone_in_variant(bn, variant)]

    def stats(self, variant: Optional[str] = None) -> Tuple[int, int]:
        nb = sum(1 for b in self.order if self.bone_in_variant(b, variant))
        nc = sum(1 for b in self.order if self.bone_in_variant(b, variant)
                 for c in self.bones[b].cubes if c.in_variant(variant or "base"))
        return nb, nc


def _skyline(rects, W: int, pad: int):
    """Skyline bottom-left packing. Returns ([((cube, face), (x, y, w, h)), ...], height) or None."""
    sky = [(0, 0, W)]  # segments (x, y, width)
    out = []
    top = 0
    for ph, pw, c, f in rects:
        w, h = pw + 2 * pad, ph + 2 * pad
        if w > W:
            return None
        best = None
        for i in range(len(sky)):
            x = sky[i][0]
            if x + w > W:
                break
            # height needed across segments covered by [x, x+w)
            y = 0
            span = 0
            j = i
            while span < w and j < len(sky):
                y = max(y, sky[j][1])
                span += sky[j][2] if j > i else sky[j][2] - (x - sky[j][0])
                j += 1
            if span < w:
                continue
            if best is None or y + h < best[1] + best[3] or (y + h == best[1] + best[3] and x < best[0]):
                best = (x, y, w, h)
        if best is None:
            return None
        x, y, w, h = best
        out.append(((c, f), (x + pad, y + pad, pw, ph)))
        top = max(top, y + h)
        # update skyline
        new = []
        for (sx, sy, sw) in sky:
            ex = sx + sw
            if ex <= x or sx >= x + w:
                new.append((sx, sy, sw))
                continue
            if sx < x:
                new.append((sx, sy, x - sx))
            if ex > x + w:
                new.append((x + w, sy, ex - (x + w)))
        new.append((x, y + h, w))
        new.sort()
        merged = []
        for seg in new:
            if merged and merged[-1][1] == seg[1] and merged[-1][0] + merged[-1][2] == seg[0]:
                merged[-1] = (merged[-1][0], seg[1], merged[-1][2] + seg[2])
            else:
                merged.append(seg)
        sky = merged
    return out, top


def _r3(v) -> List[float]:
    return [round(float(x), 4) + 0.0 for x in v]
