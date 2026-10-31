"""
modelkit v2 - procedural Bedrock models, HD textures, previews and geometry QA.

* Models are bones made of cubes; each cube has a procedural material ("painter").
* Every visible face is packed into an atlas (per-face UV, model units). The PNG is painted at
  `density` pixels per unit (HD texture: Bedrock scales UVs by texture_width/height).
* Painters return base colours; `bake` adds face lighting, vertical ambient occlusion and crisp
  pixel edges so the blocks read well in-game from every angle.
* Cubes flagged `glow=True` are exported to a second geometry rendered with an additive material.
* QA: `zfight_report` finds coplanar, overlapping, *visible* faces (flicker) and `island_report`
  finds cubes that float detached from the rest of their bone chain (unless the bone is declared
  floating by design).
* Preview: software renderer (orthographic, painter's algorithm) with optional pose overrides.

Conventions: Bedrock geometry, 16 units per block, model faces -Z, model -X = entity's right side.
Bedrock rotation [rx, ry, rz] (deg) == right-handed (-rx, -ry, rz), applied X then Y then Z.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

RGBA = Tuple[int, int, int, int]
FACES = ("north", "south", "east", "west", "up", "down")
TRANSPARENT: RGBA = (0, 0, 0, 0)


def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1: RGBA, c2: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(4))  # type: ignore


def shade(c: RGBA, f: float) -> RGBA:
    return mix(c, (255, 255, 255, c[3]), f) if f >= 0 else mix(c, (0, 0, 0, c[3]), -f)


@dataclass
class FaceCtx:
    face: str
    x: int          # pixel inside the face
    y: int
    w: int          # face size in pixels
    h: int
    rng: random.Random
    cube_index: int
    density: int
    size_units: Tuple[float, float]

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
    def ux(self) -> int:
        """x in model units (for patterns that should keep their scale)."""
        return self.x // self.density

    @property
    def uy(self) -> int:
        return self.y // self.density


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
    glow: bool = False
    bake: bool = True


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    cubes: List[Cube] = field(default_factory=list)
    floating: bool = False   # detached from its parent by design (masks, orbiting shards...)

    def add(self, origin, size, mat, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(float(x) for x in origin), tuple(float(x) for x in size), mat, **kw))
        return self


# --------------------------------------------------------------------------- math

def rot_matrix(rot):
    if not rot or not any(rot):
        return None
    rx, ry, rz = (math.radians(-rot[0]), math.radians(-rot[1]), math.radians(rot[2]))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    Ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    Rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mm(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mm(Rz, mm(Ry, Rx))


def apply(m, p, pivot):
    if m is None:
        return p
    x, y, z = p[0] - pivot[0], p[1] - pivot[1], p[2] - pivot[2]
    return (m[0][0] * x + m[0][1] * y + m[0][2] * z + pivot[0],
            m[1][0] * x + m[1][1] * y + m[1][2] * z + pivot[1],
            m[2][0] * x + m[2][1] * y + m[2][2] * z + pivot[2])


def face_corners(c: Cube, face: str):
    """(top-left, top-right, bottom-left) of a face in cube-local model space."""
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    x0, y0, z0, x1, y1, z1 = ox - i, oy - i, oz - i, ox + sx + i, oy + sy + i, oz + sz + i
    return {
        "north": ((x0, y1, z0), (x1, y1, z0), (x0, y0, z0)),
        "south": ((x1, y1, z1), (x0, y1, z1), (x1, y0, z1)),
        "east": ((x0, y1, z1), (x0, y1, z0), (x0, y0, z1)),
        "west": ((x1, y1, z0), (x1, y1, z1), (x1, y0, z0)),
        "up": ((x0, y1, z1), (x1, y1, z1), (x0, y1, z0)),
        "down": ((x0, y0, z0), (x1, y0, z0), (x0, y0, z1)),
    }[face]


# --------------------------------------------------------------------------- model

class Model:
    def __init__(self, identifier: str, seed: int = 1, density: int = 2):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.density = density
        self.texture: Optional[Image.Image] = None
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.atlas: Tuple[int, int] = (0, 0)

    def bone(self, name, pivot, parent=None, rotation=None, floating=False) -> Bone:
        if any(b.name == name for b in self.bones):
            raise ValueError(f"duplicate bone {name}")
        if parent and not any(b.name == parent for b in self.bones):
            raise ValueError(f"bone {name}: parent {parent} must be declared first")
        b = Bone(name, tuple(float(x) for x in pivot), parent, tuple(rotation) if rotation else None, floating=floating)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    @staticmethod
    def face_dims(c: Cube, face: str):
        sx, sy, sz = c.size
        return {"north": (sx, sy), "south": (sx, sy), "east": (sz, sy), "west": (sz, sy), "up": (sx, sz), "down": (sx, sz)}[face]

    def visible_faces(self, c: Cube):
        for face in FACES:
            if c.faces is not None and face not in c.faces:
                continue
            w, h = self.face_dims(c, face)
            if w > 0 and h > 0:
                yield face, w, h

    def pack(self):
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, w, h in self.visible_faces(c):
                    items.append(((bi, ci, face), max(1, math.ceil(w - 1e-6)), max(1, math.ceil(h - 1e-6))))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (32, 64, 128, 256, 512):
            if W * W * 2 < area * 1.12:
                continue
            placed, x, y, row = {}, 0, 0, 0
            for key, w, h in items:
                if x + w > W:
                    x, y, row = 0, y + row, 0
                placed[key] = (x, y, w, h)
                x += w
                row = max(row, h)
            H = 16
            while H < y + row:
                H *= 2
            if H <= W * 2:
                self.uv, self.atlas = placed, (W, H)
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier}")

    # ---------------------------------------------------------------- painting
    def paint(self) -> Image.Image:
        W, H = self.pack()
        d = self.density
        img = Image.new("RGBA", (W * d, H * d), TRANSPARENT)
        px = img.load()
        rng = random.Random(self.seed)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            c = self.bones[bi].cubes[ci]
            painter = c.face_mats.get(face, c.mat)
            pw, ph = w * d, h * d
            dims = self.face_dims(c, face)
            for yy in range(ph):
                for xx in range(pw):
                    f = FaceCtx(face, xx, yy, pw, ph, rng, bi * 131 + ci, d, dims)
                    col = painter(f)
                    if c.bake and col[3] > 0 and not c.glow:
                        col = bake(col, f)
                    px[u * d + xx, v * d + yy] = col
            dec = c.decals.get(face)
            if dec:
                def setp(x, y, col, u=u, v=v, pw=pw, ph=ph):
                    if 0 <= x < pw and 0 <= y < ph:
                        px[u * d + x, v * d + y] = col
                dec(setp, pw, ph)
        self.texture = img
        return img

    # ---------------------------------------------------------------- export
    def geometry_json(self, bounds_w=3.0, bounds_h=3.0, offset_y=1.0, glow: Optional[bool] = None,
                      identifier: Optional[str] = None) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.atlas
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation and any(b.rotation):
                jb["rotation"] = [round(v, 3) for v in b.rotation]
            cubes = []
            for ci, c in enumerate(b.cubes):
                if glow is not None and c.glow != glow:
                    continue
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = c.inflate
                if c.rotation and any(c.rotation):
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 3) for v in c.rotation]
                uv = {}
                for face in FACES:
                    key = (bi, ci, face)
                    if key in self.uv:
                        u, v, w, h = self.uv[key]
                        uv[face] = {"uv": [u + w, v + h], "uv_size": [-w, -h]} if face == "down" else {"uv": [u, v], "uv_size": [w, h]}
                jc["uv"] = uv
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            bones.append(jb)
        return {"format_version": "1.16.0", "minecraft:geometry": [{
            "description": {"identifier": identifier or self.identifier, "texture_width": W, "texture_height": H,
                            "visible_bounds_width": bounds_w, "visible_bounds_height": bounds_h,
                            "visible_bounds_offset": [0, offset_y, 0]},
            "bones": bones}]}

    def stats(self):
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones),
                "glow_cubes": sum(c.glow for b in self.bones for c in b.cubes),
                "atlas_units": self.atlas, "texture_px": self.texture.size if self.texture else None}

    # ---------------------------------------------------------------- posing
    def chain(self, b: Bone) -> List[Bone]:
        by = {x.name: x for x in self.bones}
        out = []
        while b is not None:
            out.append(b)
            b = by.get(b.parent) if b.parent else None
        return out

    def transform(self, b: Bone, c: Cube, pose: Optional[dict] = None):
        """Return f(point) mapping cube-local points to model space under an optional pose
        {bone: {"rot": (x,y,z), "pos": (x,y,z), "scale": s}}."""
        cm = rot_matrix(c.rotation)
        cpiv = c.pivot or c.origin
        chain = self.chain(b)
        pose = pose or {}

        def f(p):
            p = apply(cm, p, cpiv)
            for bb in chain:
                pz = pose.get(bb.name, {})
                r = bb.rotation or (0, 0, 0)
                if "rot" in pz:
                    r = tuple(r[i] + pz["rot"][i] for i in range(3))
                s = pz.get("scale")
                if s:
                    p = tuple(bb.pivot[i] + (p[i] - bb.pivot[i]) * s for i in range(3))
                p = apply(rot_matrix(r), p, bb.pivot)
                if "pos" in pz:
                    p = tuple(p[i] + pz["pos"][i] for i in range(3))
            return p
        return f


# --------------------------------------------------------------------------- baked lighting

LIGHT = {"up": 0.10, "north": 0.0, "south": -0.06, "east": -0.03, "west": -0.03, "down": -0.22}


def bake(col: RGBA, f: FaceCtx) -> RGBA:
    out = shade(col, LIGHT[f.face])
    if f.face in ("north", "south", "east", "west"):
        out = shade(out, 0.06 - 0.16 * f.v)            # light from above, occlusion at the bottom
    if f.edge and min(f.w, f.h) > 3:
        out = shade(out, 0.12 if (f.y == 0 or f.x == 0) else -0.18)   # bevel highlight / shadow line
    return out


# --------------------------------------------------------------------------- QA: z-fighting & islands

def _face_world(model: Model, b: Bone, c: Cube, face: str):
    f = model.transform(b, c)
    tl, tr, bl = (f(p) for p in face_corners(c, face))
    br = (tr[0] + bl[0] - tl[0], tr[1] + bl[1] - tl[1], tr[2] + bl[2] - tl[2])
    return tl, tr, bl, br


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    l = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


def _inside(model: Model, b: Bone, c: Cube, p) -> bool:
    """Is world point p strictly inside cube c (with its transform)?"""
    # invert by sampling: transform cube axes
    f = model.transform(b, c)
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    o = f((ox - i, oy - i, oz - i))
    ax = _sub(f((ox + sx + i, oy - i, oz - i)), o)
    ay = _sub(f((ox - i, oy + sy + i, oz - i)), o)
    az = _sub(f((ox - i, oy - i, oz + sz + i)), o)
    d = _sub(p, o)
    for axis in (ax, ay, az):
        L2 = _dot(axis, axis)
        if L2 < 1e-9:
            return False
        t = _dot(d, axis) / L2
        if t <= 0.002 or t >= 0.998:
            return False
    return True


def _solid_frames(model: Model):
    """Precomputed (cube, origin, axes, |axis|^2) for fast point-in-cube tests."""
    out = []
    for b in model.bones:
        for c in b.cubes:
            if c.glow:
                continue
            f = model.transform(b, c)
            (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
            o = f((ox - i, oy - i, oz - i))
            axes = [_sub(f((ox + sx + i, oy - i, oz - i)), o), _sub(f((ox - i, oy + sy + i, oz - i)), o), _sub(f((ox - i, oy - i, oz + sz + i)), o)]
            lo, hi = _aabb(model, b, c)
            out.append((c, o, axes, [_dot(a, a) for a in axes], lo, hi))
    return out


def _inside_fast(fr, p) -> bool:
    c, o, axes, l2, lo, hi = fr
    if not all(lo[k] <= p[k] <= hi[k] for k in range(3)):
        return False
    d = _sub(p, o)
    for a, L2 in zip(axes, l2):
        if L2 < 1e-9:
            return False
        t = _dot(d, a) / L2
        if t <= 0.002 or t >= 0.998:
            return False
    return True


def zfight_pairs(model: Model, eps=0.004):
    """Coplanar, overlapping, same-facing faces whose overlap is visible (not buried inside another
    cube). Returns [(bone_i, cube_i, face_i, bone_j, cube_j, face_j, area)]."""
    buckets = {}
    frames = _solid_frames(model)
    for b in model.bones:
        for c in b.cubes:
            for face, w, h in model.visible_faces(c):
                q = _face_world(model, b, c, face)
                n = _norm(_cross(_sub(q[2], q[0]), _sub(q[1], q[0])))
                d = _dot(n, q[0])
                key = (round(n[0], 2), round(n[1], 2), round(n[2], 2), round(d / (eps * 4)))
                buckets.setdefault(key, []).append((b, c, face, q, n, d))
    out = []
    keys = list(buckets)
    for key in keys:
        group = list(buckets[key])
        for dk in (1,):
            nb = (key[0], key[1], key[2], key[3] + dk)
            group_n = buckets.get(nb, [])
        cand = group + group_n
        for i in range(len(group)):
            bi, ci, fi, qi, ni, di = group[i]
            for j in range(len(cand)):
                if j <= i and j < len(group):
                    continue
                bj, cj, fj, qj, nj, dj = cand[j]
                if ci is cj or ci.glow != cj.glow or _dot(ni, nj) < 0.999 or abs(di - dj) > eps:
                    continue
                u = _norm(_sub(qi[1], qi[0]))
                v = _norm(_cross(ni, u))

                def rect(q):
                    us = [_dot(_sub(p, qi[0]), u) for p in q]
                    vs = [_dot(_sub(p, qi[0]), v) for p in q]
                    return min(us), max(us), min(vs), max(vs)
                a, bb = rect(qi), rect(qj)
                ou0, ou1, ov0, ov1 = max(a[0], bb[0]), min(a[1], bb[1]), max(a[2], bb[2]), min(a[3], bb[3])
                if ou1 - ou0 < 0.05 or ov1 - ov0 < 0.05:
                    continue
                visible = False
                for su in (0.15, 0.5, 0.85):
                    for sv in (0.15, 0.5, 0.85):
                        uu, vv = ou0 + (ou1 - ou0) * su, ov0 + (ov1 - ov0) * sv
                        base = tuple(qi[0][k] + u[k] * uu + v[k] * vv for k in range(3))
                        for sign in (1, -1):   # either side of the surface may be the visible one
                            p = tuple(base[k] + ni[k] * 0.012 * sign for k in range(3))
                            inside_pair = False
                            buried = False
                            for fr in frames:
                                if _inside_fast(fr, p):
                                    if fr[0] is ci or fr[0] is cj:
                                        inside_pair = True
                                    else:
                                        buried = True
                                    if buried:
                                        break
                            if not buried and not inside_pair:
                                visible = True
                        if visible:
                            break
                    if visible:
                        break
                if visible:
                    out.append((bi, ci, fi, bj, cj, fj, (ou1 - ou0) * (ov1 - ov0)))
    return out


def zfight_report(model: Model, eps=0.004):
    return [f"{bi.name}:{fi}{ci.origin}{ci.size} <-> {bj.name}:{fj}{cj.origin}{cj.size} area {a:.2f}"
            for bi, ci, fi, bj, cj, fj, a in zfight_pairs(model, eps)]


def deflicker(model: Model, step=0.04, passes=8):
    """Resolve flicker by letting the smaller of each coplanar pair protrude a little (inflate)."""
    for _ in range(passes):
        pairs = zfight_pairs(model)
        if not pairs:
            return 0
        touched = set()
        for bi, ci, fi, bj, cj, fj, _a in pairs:
            vi = ci.size[0] * ci.size[1] * ci.size[2]
            vj = cj.size[0] * cj.size[1] * cj.size[2]
            pick = ci if vi <= vj else cj
            if id(ci) in touched or id(cj) in touched:
                continue
            pick.inflate = round(pick.inflate + step, 3)
            touched.add(id(pick))
    return len(zfight_pairs(model))


def _aabb(model: Model, b: Bone, c: Cube):
    f = model.transform(b, c)
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    pts = [f((x, y, z)) for x in (ox - i, ox + sx + i) for y in (oy - i, oy + sy + i) for z in (oz - i, oz + sz + i)]
    return tuple(min(p[k] for p in pts) for k in range(3)), tuple(max(p[k] for p in pts) for k in range(3))


def island_report(model: Model, tol=0.35):
    """Cubes not touching any other cube of the same skeleton branch (excluding bones marked floating)."""
    boxes = [(b, c, _aabb(model, b, c)) for b in model.bones for c in b.cubes]
    floating = set()
    for b in model.bones:
        if any(x.floating for x in model.chain(b)):
            floating.add(b.name)

    def touch(a, bb):
        return all(a[0][k] - tol <= bb[1][k] and bb[0][k] - tol <= a[1][k] for k in range(3))
    # union-find over all non-floating cubes
    idx = [k for k, (b, c, _) in enumerate(boxes) if b.name not in floating]
    parent = {k: k for k in idx}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    for a in range(len(idx)):
        for b2 in range(a + 1, len(idx)):
            if touch(boxes[idx[a]][2], boxes[idx[b2]][2]):
                parent[find(idx[a])] = find(idx[b2])
    groups = {}
    for k in idx:
        groups.setdefault(find(k), []).append(k)
    if not groups:
        return []
    main = max(groups.values(), key=len)
    out = []
    for g in groups.values():
        if g is main:
            continue
        names = sorted({boxes[k][0].name for k in g})
        out.append(f"{len(g)} cube(s) detached in bones {names}")
    return out


# --------------------------------------------------------------------------- preview

def render_preview(models: Sequence[Model], path: str, yaw: float = 35, pitch: float = 20, size: int = 640,
                   pose: Optional[dict] = None, bg=(18, 16, 26, 255), title: str = "", ground: bool = True, step: int = 0):
    quads = []
    for model in models:
        if model.texture is None:
            model.paint()
        px = model.texture.load()
        d = model.density
        st = step or max(1, d // 2) if step else 1
        for bi, b in enumerate(model.bones):
            for ci, c in enumerate(b.cubes):
                f = model.transform(b, c, pose)
                for face in FACES:
                    key = (bi, ci, face)
                    if key not in model.uv:
                        continue
                    u, v, w, h = model.uv[key]
                    tl, tr, bl = (f(p) for p in face_corners(c, face))
                    pw, ph = w * d, h * d
                    du = tuple((tr[k] - tl[k]) / pw for k in range(3))
                    dv = tuple((bl[k] - tl[k]) / ph for k in range(3))
                    for yy in range(0, ph, st):
                        for xx in range(0, pw, st):
                            col = px[u * d + xx, v * d + yy]
                            if col[3] < 128:
                                continue
                            p0 = tuple(tl[k] + du[k] * xx + dv[k] * yy for k in range(3))
                            p1 = tuple(p0[k] + du[k] * st for k in range(3))
                            p2 = tuple(p1[k] + dv[k] * st for k in range(3))
                            p3 = tuple(p0[k] + dv[k] * st for k in range(3))
                            quads.append(((p0, p1, p2, p3), col, c.glow))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        x, y, z = p
        x2, z2 = x * cy - z * sy, x * sy + z * cy
        return (-x2, y * cp + z2 * sp, -y * sp + z2 * cp)
    proj = []
    for pts, col, glow in quads:
        vp = [view(p) for p in pts]
        ax, ay = vp[1][0] - vp[0][0], vp[1][1] - vp[0][1]
        bx, by = vp[3][0] - vp[0][0], vp[3][1] - vp[0][1]
        if ax * by - ay * bx < 0:
            continue
        proj.append((sum(p[2] for p in vp) / 4, vp, col, glow))
    if not proj:
        return
    xs = [p[0] for _, vp, _, _ in proj for p in vp]
    ys = [p[1] for _, vp, _, _ in proj for p in vp]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) * 1.1 or 1
    sc = size / span
    cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    img = Image.new("RGBA", (size, size), bg)
    dr = ImageDraw.Draw(img)
    if ground:
        gy = size / 2 - (view((0, 0, 0))[1] - cym) * sc
        dr.line((0, gy, size, gy), fill=(40, 38, 54, 255))
    proj.sort(key=lambda q: -q[0])
    glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gl = ImageDraw.Draw(glow_layer)
    for depth, vp, col, glow in proj:
        pts = [((p[0] - cxm) * sc + size / 2, size / 2 - (p[1] - cym) * sc) for p in vp]
        if glow:
            gl.polygon(pts, fill=(col[0], col[1], col[2], 255))
            dr.polygon(pts, fill=(min(255, col[0] + 30), min(255, col[1] + 30), min(255, col[2] + 30), 255))
        else:
            dr.polygon(pts, fill=col)
    from PIL import ImageFilter
    halo = glow_layer.filter(ImageFilter.GaussianBlur(size / 90))
    img = Image.alpha_composite(img, Image.blend(Image.new("RGBA", img.size, (0, 0, 0, 0)), halo, 0.55))
    if title:
        ImageDraw.Draw(img).text((8, 8), title, fill=(230, 230, 240, 255))
    img.save(path)
