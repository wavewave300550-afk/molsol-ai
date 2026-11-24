"""
modelkit — procedural Bedrock entity models with HD per-face textures.

Coordinates are Bedrock geometry JSON space (1 unit = 1/16 block, the model
faces north / -Z, the entity's RIGHT side is -X).

Rotation convention (verified against vanilla animations: zombie arms
[-90,0,0] point forward, evoker casting right arm z=+135 raises the arm
OUTWARD, spyglass right arm y=-15 swings the hand INWARD):

    a Bedrock rotation [rx, ry, rz] in JSON space equals the right-handed
    rotation  Rz(-rz) * Ry(+ry) * Rx(-rx)   (X applied first).

Rendering converts JSON space to a proper right-handed space by mirroring X
(the entity's right hand then appears on the viewer's left when viewed from
the front, as it should).

Features
  * per-face UV atlas packing in unit texels, painted at `ppu` texels per unit
    (HD texture; geometry keeps unit texture_width/height so Bedrock scales it)
  * texture variants (e.g. base / burning / ghost / glow layers) painted from
    the same atlas layout, so one geometry serves several render layers
  * painters receive the model-space position + normal of every texel
  * locators, single-sided planes (cloth), cube pivots/rotations
  * forward kinematics + a software renderer for previews and for baking
    cloth simulation into keyframes
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

RGBA = Tuple[int, int, int, int]
Vec = Tuple[float, float, float]
FACES = ("north", "south", "east", "west", "up", "down")
TRANSPARENT: RGBA = (0, 0, 0, 0)


# =========================================================================== colour helpers

def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1: RGBA, c2: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(4))  # type: ignore


def shade(c: RGBA, f: float) -> RGBA:
    """f > 0 lightens towards white, f < 0 darkens towards black (alpha kept)."""
    if f >= 0:
        return mix(c, (255, 255, 255, c[3]), f)
    return mix(c, (0, 0, 0, c[3]), -f)


def with_alpha(c: RGBA, a: int) -> RGBA:
    return (c[0], c[1], c[2], max(0, min(255, int(a))))


def smoothstep(e0: float, e1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0 if e1 != e0 else 1e-9)))
    return t * t * (3 - 2 * t)


def hash01(*k: float) -> float:
    """Deterministic pseudo random in [0,1) from numbers (stable across runs)."""
    h = 2166136261
    for v in k:
        for b in repr(round(float(v), 4)).encode():
            h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def vnoise(x: float, y: float, seed: float = 0.0) -> float:
    """Smooth value noise in [0,1]."""
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a = hash01(xi, yi, seed)
    b = hash01(xi + 1, yi, seed)
    c = hash01(xi, yi + 1, seed)
    d = hash01(xi + 1, yi + 1, seed)
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def fbm(x: float, y: float, seed: float = 0.0, octaves: int = 3) -> float:
    s, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s += vnoise(x * (2 ** o), y * (2 ** o), seed + o * 17.3) * amp
        tot += amp
        amp *= 0.5
    return s / tot


# =========================================================================== vector / rotation math

def v_add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s, a[2] * s)


def v_dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_len(a: Vec) -> float:
    return math.sqrt(v_dot(a, a))


def v_norm(a: Vec) -> Vec:
    l = v_len(a)
    return (0.0, 0.0, 0.0) if l < 1e-12 else (a[0] / l, a[1] / l, a[2] / l)


Mat = Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]
IDENT: Mat = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def m_mul(a: Mat, b: Mat) -> Mat:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))  # type: ignore


def m_apply(m: Mat, p: Vec) -> Vec:
    return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
            m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
            m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2])


def m_transpose(m: Mat) -> Mat:
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))  # type: ignore


def rx_m(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def ry_m(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def rz_m(a: float) -> Mat:
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def bedrock_rot(r: Optional[Sequence[float]]) -> Mat:
    """Bedrock euler degrees [rx, ry, rz] -> rotation matrix in JSON model space."""
    if not r or (abs(r[0]) < 1e-9 and abs(r[1]) < 1e-9 and abs(r[2]) < 1e-9):
        return IDENT
    rx, ry, rz = (math.radians(x) for x in r)
    return m_mul(rz_m(-rz), m_mul(ry_m(ry), rx_m(-rx)))


def bedrock_euler_from_matrix(m: Mat) -> Tuple[float, float, float]:
    """Inverse of bedrock_rot: M = Rz(-c) Ry(b) Rx(-a)  ->  [a, b, c] degrees."""
    # M = Rz(g) Ry(b) Rx(al) with g=-c, al=-a ; standard ZYX decomposition
    sy = -m[2][0]
    sy = max(-1.0, min(1.0, sy))
    b = math.asin(sy)
    if abs(math.cos(b)) > 1e-6:
        al = math.atan2(m[2][1], m[2][2])
        g = math.atan2(m[1][0], m[0][0])
    else:
        al = math.atan2(-m[1][2], m[1][1])
        g = 0.0
    return (math.degrees(-al), math.degrees(b), math.degrees(-g))


# =========================================================================== painters

@dataclass
class FaceCtx:
    face: str
    x: int            # texel within the face slot (HD texels)
    y: int
    w: int            # slot size (HD texels)
    h: int
    rng: random.Random
    cube: "Cube"
    bone: "Bone"
    pos: Vec          # model-space position of the texel centre (bind pose, JSON space)
    nrm: Vec          # face normal in model space (bind pose)
    variant: str
    ppu: int

    @property
    def u(self) -> float:
        return (self.x + 0.5) / self.w

    @property
    def v(self) -> float:
        return (self.y + 0.5) / self.h

    @property
    def edge(self) -> bool:
        return self.x == 0 or self.y == 0 or self.x == self.w - 1 or self.y == self.h - 1

    def edge_dist(self) -> int:
        return min(self.x, self.y, self.w - 1 - self.x, self.h - 1 - self.y)

    @property
    def glow(self) -> bool:
        return self.variant.startswith("glow")


Painter = Callable[[FaceCtx], RGBA]
# decal(setp, w, h, ctx_variant) draws pixel art onto the face after painting
Decal = Callable[[Callable[[int, int, RGBA], None], int, int, str], None]


# =========================================================================== model description

@dataclass
class Cube:
    origin: Vec
    size: Vec
    mat: Painter
    inflate: float = 0.0
    pivot: Optional[Vec] = None
    rotation: Optional[Vec] = None
    faces: Optional[Tuple[str, ...]] = None          # restrict mapped faces
    face_mats: Dict[str, Painter] = field(default_factory=dict)
    decals: Dict[str, List[Decal]] = field(default_factory=dict)
    tag: str = ""                                      # free label for painters


@dataclass
class Bone:
    name: str
    pivot: Vec
    parent: Optional[str] = None
    rotation: Optional[Vec] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Vec] = field(default_factory=dict)

    def add(self, origin, size, mat, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(origin), tuple(size), mat, **kw))
        return self

    def last(self) -> Cube:
        return self.cubes[-1]


class Model:
    def __init__(self, identifier: str, seed: int = 1, ppu: int = 2):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.ppu = ppu
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.size: Tuple[int, int] = (0, 0)
        self.textures: Dict[str, Image.Image] = {}

    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        assert all(b.name != name for b in self.bones), f"duplicate bone {name}"
        b = Bone(name, tuple(pivot), parent, tuple(rotation) if rotation else None)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    def has(self, name) -> bool:
        return any(b.name == name for b in self.bones)

    # ------------------------------------------------------------------ faces
    @staticmethod
    def face_dims(c: Cube, face: str) -> Tuple[float, float]:
        sx, sy, sz = c.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def visible_faces(self, c: Cube):
        for face in FACES:
            if c.faces is not None and face not in c.faces:
                continue
            w, h = self.face_dims(c, face)
            if w <= 1e-6 or h <= 1e-6:
                continue
            yield face, w, h

    @staticmethod
    def face_corners(c: Cube, face: str) -> Tuple[Vec, Vec, Vec]:
        """(top-left, top-right, bottom-left) corners of a face in bone space (before cube rotation)."""
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

    @staticmethod
    def face_normal(face: str) -> Vec:
        return {"north": (0, 0, -1), "south": (0, 0, 1), "east": (-1, 0, 0), "west": (1, 0, 0),
                "up": (0, 1, 0), "down": (0, -1, 0)}[face]

    # ------------------------------------------------------------------ packing (unit texels)
    def pack(self) -> Tuple[int, int]:
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, w, h in self.visible_faces(c):
                    tw, th = max(1, int(math.ceil(w - 1e-6))), max(1, int(math.ceil(h - 1e-6)))
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (16, 32, 64, 128, 256, 512):
            if W * W * 2 < area * 1.08:
                continue
            placed = {}
            x = y = row_h = 0
            ok = True
            for key, w, h in items:
                if w > W:
                    ok = False
                    break
                if x + w > W:
                    x, y = 0, y + row_h
                    row_h = 0
                placed[key] = (x, y, w, h)
                x += w
                row_h = max(row_h, h)
            total_h = y + row_h
            if not ok:
                continue
            H = 16
            while H < total_h:
                H *= 2
            if H <= W * 2:
                self.uv = placed
                self.size = (W, H)
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier}")

    # ------------------------------------------------------------------ painting
    def paint(self, variant: str = "base") -> Image.Image:
        if not self.uv:
            self.pack()
        W, H = self.size
        P = self.ppu
        img = Image.new("RGBA", (W * P, H * P), TRANSPARENT)
        px = img.load()
        rng = random.Random(self.seed)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            b = self.bones[bi]
            c = b.cubes[ci]
            painter = c.face_mats.get(face, c.mat)
            tl, tr, bl = self.face_corners(c, face)
            cm = bedrock_rot(c.rotation)
            cp = c.pivot or c.origin
            nrm = m_apply(cm, self.face_normal(face))
            sw, sh = w * P, h * P
            for yy in range(sh):
                for xx in range(sw):
                    uu, vv = (xx + 0.5) / sw, (yy + 0.5) / sh
                    p = (tl[0] + (tr[0] - tl[0]) * uu + (bl[0] - tl[0]) * vv,
                         tl[1] + (tr[1] - tl[1]) * uu + (bl[1] - tl[1]) * vv,
                         tl[2] + (tr[2] - tl[2]) * uu + (bl[2] - tl[2]) * vv)
                    if c.rotation:
                        p = v_add(m_apply(cm, v_sub(p, cp)), cp)
                    ctx = FaceCtx(face, xx, yy, sw, sh, rng, c, b, p, nrm, variant, P)
                    px[u * P + xx, v * P + yy] = painter(ctx)
            for dec in c.decals.get(face, []):
                def setp(x, y, col, u=u, v=v, sw=sw, sh=sh):
                    if 0 <= x < sw and 0 <= y < sh:
                        px[u * P + x, v * P + y] = col
                dec(setp, sw, sh, variant)
        self.textures[variant] = img
        return img

    # ------------------------------------------------------------------ export
    def geometry_json(self, bounds_w: float = 3, bounds_h: float = 3, offset_y: float = 1.0) -> dict:
        if not self.uv:
            self.pack()
        W, H = self.size
        bones = []
        for bi, b in enumerate(self.bones):
            jb: dict = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation:
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            if b.locators:
                jb["locators"] = {k: [round(x, 4) for x in v] for k, v in b.locators.items()}
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc: dict = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = round(c.inflate, 4)
                if c.rotation:
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 4) for v in c.rotation]
                uv = {}
                for face in FACES:
                    key = (bi, ci, face)
                    if key in self.uv:
                        u, v, w, h = self.uv[key]
                        if face == "down":
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
                    "visible_bounds_width": bounds_w,
                    "visible_bounds_height": bounds_h,
                    "visible_bounds_offset": [0, offset_y, 0],
                },
                "bones": bones,
            }],
        }

    def stats(self) -> dict:
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones),
                "atlas_units": self.size, "png": (self.size[0] * self.ppu, self.size[1] * self.ppu)}


# =========================================================================== forward kinematics

Pose = Dict[str, dict]   # bone -> {"rotation": (x,y,z), "position": (x,y,z), "scale": (x,y,z) | s}


@dataclass
class Xf:
    """Affine transform: p -> R p + t (scale folded into R)."""
    R: Mat
    t: Vec

    def apply(self, p: Vec) -> Vec:
        return v_add(m_apply(self.R, p), self.t)

    def then(self, other: "Xf") -> "Xf":
        """self applied after `other` (self ∘ other)."""
        return Xf(m_mul(self.R, other.R), v_add(m_apply(self.R, other.t), self.t))


def _scale_m(s) -> Mat:
    if s is None:
        return IDENT
    if isinstance(s, (int, float)):
        s = (s, s, s)
    return ((s[0], 0, 0), (0, s[1], 0), (0, 0, s[2]))


def bone_transforms(model: Model, pose: Optional[Pose] = None) -> Dict[str, Xf]:
    """World (model-space) transform of every bone for a pose (Bedrock semantics)."""
    pose = pose or {}
    out: Dict[str, Xf] = {}
    byname = {b.name: b for b in model.bones}

    def solve(name: str) -> Xf:
        if name in out:
            return out[name]
        b = byname[name]
        pr = pose.get(name, {})
        rot = list(b.rotation or (0, 0, 0))
        if "rotation" in pr:
            rot = [rot[i] + pr["rotation"][i] for i in range(3)]
        pos = pr.get("position", (0, 0, 0))
        R = m_mul(bedrock_rot(rot), _scale_m(pr.get("scale")))
        piv = b.pivot
        # local: p -> R (p - piv) + piv + pos
        t = v_add(v_sub(piv, m_apply(R, piv)), pos)
        local = Xf(R, t)
        if b.parent:
            res = solve(b.parent).then(local)
        else:
            res = local
        out[name] = res
        return res

    for b in model.bones:
        solve(b.name)
    return out


def world_point(model: Model, pose: Pose, bone: str, p: Vec) -> Vec:
    return bone_transforms(model, pose)[bone].apply(p)


# =========================================================================== software renderer

def _quads(model: Model, pose: Pose, variant: str, glow_variant: Optional[str]):
    tex = model.textures.get(variant) or model.paint(variant)
    glow = None
    if glow_variant:
        glow = model.textures.get(glow_variant) or model.paint(glow_variant)
    px = tex.load()
    gpx = glow.load() if glow else None
    xfs = bone_transforms(model, pose)
    P = model.ppu
    quads = []
    for bi, b in enumerate(model.bones):
        xf = xfs[b.name]
        for ci, c in enumerate(b.cubes):
            cm = bedrock_rot(c.rotation)
            cp = c.pivot or c.origin
            two_sided = c.faces is not None and len(c.faces) == 1

            def tf(p):
                if c.rotation:
                    p = v_add(m_apply(cm, v_sub(p, cp)), cp)
                return xf.apply(p)
            for face in FACES:
                key = (bi, ci, face)
                if key not in model.uv:
                    continue
                u, v, w, h = model.uv[key]
                tl, tr, bl = (tf(p) for p in Model.face_corners(c, face))
                sw, sh = w * P, h * P
                du = tuple((tr[k] - tl[k]) / sw for k in range(3))
                dv = tuple((bl[k] - tl[k]) / sh for k in range(3))
                n = v_norm(v_cross(du, dv))   # outward normal (JSON space)
                for yy in range(sh):
                    for xx in range(sw):
                        col = px[u * P + xx, v * P + yy]
                        gcol = gpx[u * P + xx, v * P + yy] if gpx else (0, 0, 0, 0)
                        if col[3] < 128 and gcol[3] < 128:
                            continue
                        p0 = tuple(tl[k] + du[k] * xx + dv[k] * yy for k in range(3))
                        p1 = tuple(p0[k] + du[k] for k in range(3))
                        p2 = tuple(p1[k] + dv[k] for k in range(3))
                        p3 = tuple(p0[k] + dv[k] for k in range(3))
                        quads.append(((p0, p1, p2, p3), col, gcol, n, two_sided))
    return quads


def render(models_and_poses: Iterable[Tuple[Model, Pose, str, Optional[str], Vec]], path: str,
           yaw: float = 30, pitch: float = 15, size: int = 512, bg=(40, 44, 54, 255),
           title: str = "", span: Optional[float] = None, center: Optional[Vec] = None,
           ground: bool = True) -> Image.Image:
    """Render posed models. Each entry: (model, pose, variant, glow_variant, offset).

    yaw rotates the camera around the model (0 = looking at the model's front)."""
    quads = []
    for model, pose, variant, glow_variant, off in models_and_poses:
        for (pts, col, gcol, n, two) in _quads(model, pose, variant, glow_variant):
            quads.append((tuple(v_add(p, off) for p in pts), col, gcol, n, two))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        # JSON space -> proper space (mirror X), then camera at -Z looking +Z, orbiting by yaw
        x, y, z = -p[0], p[1], p[2]
        x2 = x * cy + z * sy
        z2 = -x * sy + z * cy
        y3 = y * cp - z2 * sp
        z3 = y * sp + z2 * cp
        # screen x to the right = -X(proper) when looking along +Z
        return (-x2, y3, z3)

    light = v_norm((-0.45, 0.8, -0.55))   # proper-space light from the upper front-left
    proj = []
    for pts, col, gcol, n, two in quads:
        vp = [view(p) for p in pts]
        ax, ay = vp[1][0] - vp[0][0], vp[1][1] - vp[0][1]
        bx, by = vp[3][0] - vp[0][0], vp[3][1] - vp[0][1]
        cross = ax * by - ay * bx
        if cross > 0 and not two:
            continue
        depth = sum(p[2] for p in vp) / 4
        npr = (-n[0], n[1], n[2])
        lam = abs(v_dot(npr, light)) if two else max(0.0, v_dot(npr, light))
        lit = 0.55 + 0.45 * lam
        proj.append((depth, vp, col, gcol, lit))
    img = Image.new("RGBA", (size, size), bg)
    if not proj:
        img.save(path)
        return img
    xs = [p[0] for _, vp, _, _, _ in proj for p in vp]
    ys = [p[1] for _, vp, _, _, _ in proj for p in vp]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sp_ = span or max(maxx - minx, maxy - miny) * 1.1 or 1
    scale = size / sp_
    if center is not None:
        cv = view(center)
        cxm, cym = cv[0], cv[1]
    else:
        cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    dr = ImageDraw.Draw(img)
    if ground:
        gy = size / 2 - (view((0, 0, 0))[1] - cym) * scale
        dr.line([(0, gy), (size, gy)], fill=(70, 76, 90, 255), width=1)
    proj.sort(key=lambda q: -q[0])
    for depth, vp, col, gcol, lit in proj:
        pts = [((p[0] - cxm) * scale + size / 2, size / 2 - (p[1] - cym) * scale) for p in vp]
        if gcol[3] >= 128:
            c = (gcol[0], gcol[1], gcol[2], 255)
        else:
            c = tuple(min(255, int(col[i] * lit)) for i in range(3)) + (255,)
        dr.polygon(pts, fill=c)
    if title:
        dr.text((8, 8), title, fill=(235, 235, 235, 255))
    img.save(path)
    return img


def contact_sheet(paths: List[str], out: str, cols: int = 4, cell: int = 360, bg=(30, 32, 40, 255)):
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), bg)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        sheet.paste(im, ((i % cols) * cell, (i // cols) * cell))
    sheet.save(out)
    return out
