"""
modelkit - procedural Bedrock geometry, textures and a Bedrock-faithful preview renderer.

Models are bones made of cubes. Every cube face is painted by a "painter": a function
called once per texel with the face name, texel coordinates *and* the texel centre in
model space, so patterns (bamboo nodes, line windings, engraved dots) stay continuous
across faces. The kit then packs every face into a power-of-two atlas (per-face UV),
writes Bedrock geometry (format 1.16.0) and renders previews.

Coordinate conventions (verified against vanilla data, see tools/calibrate.py):
  * Bedrock model space: 1 unit = 1/16 block, the model faces -Z, entity right is -X.
  * Bone rotation [rx, ry, rz] (degrees) equals, in a right-handed frame obtained by
    negating X, Rz(rz) . Ry(-ry) . Rx(-rx)  (X applied first).
  * Animation positions are offsets in the parent bone frame (Bedrock axes).
  * A bone whose "binding" targets another entity's bone S is placed at
    W_S . T(S.pivot - (0, 24, 0)) . local - the -24 "binding quirk" documented by the
    Bedrock Wiki; it reproduces the vanilla trident grip and spyglass-at-eye exactly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RGBA = Tuple[int, int, int, int]
FACES = ("north", "south", "east", "west", "up", "down")
TRANSPARENT: RGBA = (0, 0, 0, 0)


# =========================================================================== colour helpers

def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    if len(s) == 8:
        a = int(s[6:8], 16)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1: Sequence[int], c2: Sequence[int], t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(4))  # type: ignore


def shade(c: Sequence[int], f: float) -> RGBA:
    """f > 0 lightens towards white, f < 0 darkens towards black (alpha kept)."""
    if f >= 0:
        return mix(c, (255, 255, 255, c[3]), f)
    return mix(c, (0, 0, 0, c[3]), -f)


def with_alpha(c: Sequence[int], a: int) -> RGBA:
    return (c[0], c[1], c[2], a)


def ramp(stops: Sequence[Tuple[float, str]], t: float) -> RGBA:
    """Piecewise-linear colour ramp; stops = [(t, hex), ...] sorted by t."""
    t = max(stops[0][0], min(stops[-1][0], t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(hx(c0), hx(c1), 0 if t1 == t0 else (t - t0) / (t1 - t0))
    return hx(stops[-1][1])


def noise2(x: float, y: float, seed: int = 0) -> float:
    """Cheap smooth value noise in [0, 1]."""
    def h(ix, iy):
        n = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = h(x0, y0) + (h(x0 + 1, y0) - h(x0, y0)) * sx
    b = h(x0, y0 + 1) + (h(x0 + 1, y0 + 1) - h(x0, y0 + 1)) * sx
    return a + (b - a) * sy


# =========================================================================== painters

@dataclass
class FaceCtx:
    face: str
    x: int
    y: int
    w: int
    h: int
    pos: Tuple[float, float, float]     # texel centre, model space (before rotations)
    rng: random.Random
    cube: "Cube"

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

    def jitter(self, c: Sequence[int], amount: float) -> RGBA:
        return shade(c, (self.rng.random() - 0.5) * 2 * amount)


Painter = Callable[[FaceCtx], RGBA]


def solid(base: str, var: float = 0.04, edge: float = 0.0) -> Painter:
    c = hx(base)

    def p(f: FaceCtx) -> RGBA:
        col = f.jitter(c, var)
        if edge and f.edge and min(f.w, f.h) > 2:
            col = shade(col, -edge)
        return col
    return p


def flat(base: str) -> Painter:
    c = hx(base)
    return lambda f: c


# =========================================================================== model description

@dataclass
class Cube:
    origin: Tuple[float, float, float]
    size: Tuple[float, float, float]
    paint: Painter
    faces: Optional[Tuple[str, ...]] = None        # restrict visible faces
    face_paint: Dict[str, Painter] = field(default_factory=dict)
    inflate: float = 0.0
    pivot: Optional[Tuple[float, float, float]] = None
    rotation: Optional[Tuple[float, float, float]] = None
    density: Optional[float] = None                 # texels per unit (overrides model density)
    emissive: bool = False                          # preview hint only
    translucent: bool = False                       # preview hint only


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    binding: Optional[str] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)

    def add(self, origin, size, paint: Painter, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), paint, **kw))
        return self


class Model:
    def __init__(self, identifier: str, density: float = 1.0, seed: int = 7):
        self.identifier = identifier
        self.density = density
        self.seed = seed
        self.bones: List[Bone] = []
        self.texture: Optional[Image.Image] = None
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.bounds = (2.0, 2.0, 0.5)

    def bone(self, name, pivot=(0, 0, 0), parent=None, rotation=None, binding=None) -> Bone:
        b = Bone(name, tuple(float(v) for v in pivot), parent,
                 tuple(float(v) for v in rotation) if rotation else None, binding)
        self.bones.append(b)
        return b

    def get(self, name: str) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    # ------------------------------------------------------------------ packing
    @staticmethod
    def face_dims(c: Cube, face: str) -> Tuple[float, float]:
        sx, sy, sz = c.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def _faces(self, c: Cube):
        for face in FACES:
            if c.faces is not None and face not in c.faces:
                continue
            w, h = self.face_dims(c, face)
            if w <= 1e-6 or h <= 1e-6:
                continue
            yield face, w, h

    def texel_dims(self, c: Cube, face: str) -> Tuple[int, int]:
        d = c.density or self.density
        w, h = self.face_dims(c, face)
        return max(1, int(math.ceil(w * d - 1e-6))), max(1, int(math.ceil(h * d - 1e-6)))

    def pack(self) -> Tuple[int, int]:
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, _, _ in self._faces(c):
                    tw, th = self.texel_dims(c, face)
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (16, 32, 64, 128, 256, 512, 1024):
            if W * W * 2 < area * 1.08:
                continue
            placed, x, y, row_h, ok = {}, 0, 0, 0, True
            for key, w, h in items:
                if w > W:
                    ok = False
                    break
                if x + w > W:
                    x, y, row_h = 0, y + row_h, 0
                placed[key] = (x, y, w, h)
                x += w
                row_h = max(row_h, h)
            if not ok:
                continue
            total_h, H = y + row_h, 16
            while H < total_h:
                H *= 2
            if H <= W * 2:
                self.uv = placed
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier}")

    # ------------------------------------------------------------------ painting
    @staticmethod
    def texel_pos(c: Cube, face: str, x: int, y: int, w: int, h: int) -> Tuple[float, float, float]:
        """Texel centre in model space. Orientation matches Bedrock/Blockbench per-face UV:
        north (front, -Z) runs u along +X; 'east' is the -X (entity-right) side."""
        (ox, oy, oz), (sx, sy, sz) = c.origin, c.size
        u, v = (x + 0.5) / w, (y + 0.5) / h
        if face == "north":
            return (ox + sx * u, oy + sy * (1 - v), oz)
        if face == "south":
            return (ox + sx * (1 - u), oy + sy * (1 - v), oz + sz)
        if face == "east":
            return (ox, oy + sy * (1 - v), oz + sz * (1 - u))
        if face == "west":
            return (ox + sx, oy + sy * (1 - v), oz + sz * u)
        if face == "up":
            return (ox + sx * u, oy + sy, oz + sz * (1 - v))
        return (ox + sx * u, oy, oz + sz * v)

    def paint(self) -> Image.Image:
        W, H = self.pack()
        img = Image.new("RGBA", (W, H), TRANSPARENT)
        px = img.load()
        rng = random.Random(self.seed)
        for (bi, ci, face), (u0, v0, w, h) in self.uv.items():
            c = self.bones[bi].cubes[ci]
            painter = c.face_paint.get(face, c.paint)
            for yy in range(h):
                for xx in range(w):
                    pos = self.texel_pos(c, face, xx, yy, w, h)
                    px[u0 + xx, v0 + yy] = painter(FaceCtx(face, xx, yy, w, h, pos, rng, c))
        self.texture = img
        return img

    # ------------------------------------------------------------------ export
    def geometry_json(self) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.texture.size
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.binding:
                jb["binding"] = b.binding
            if b.rotation:
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            if b.locators:
                jb["locators"] = {k: [round(v, 4) for v in p] for k, p in b.locators.items()}
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = c.inflate
                if c.rotation:
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
        bw, bh, oy = self.bounds
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


# =========================================================================== Bedrock transform emulation

def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], float)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], float)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)


def _t(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def _s(k):
    m = np.eye(4)
    if isinstance(k, (list, tuple, np.ndarray)):
        m[0, 0], m[1, 1], m[2, 2] = float(k[0]), float(k[1]), float(k[2])
    else:
        m[0, 0] = m[1, 1] = m[2, 2] = float(k)
    return m


def rh(p) -> np.ndarray:
    """Bedrock model coordinates -> right-handed render frame (negate X)."""
    return np.array([-p[0], p[1], p[2]], float)


def rot_rh(r) -> np.ndarray:
    if not r:
        return np.eye(4)
    rx, ry, rz = (math.radians(v) for v in r)
    return _rz(rz) @ _ry(-ry) @ _rx(-rx)


def bone_local(pivot, rotation=None, anim_pos=None, anim_rot=None, scale=1.0) -> np.ndarray:
    """Local matrix of a bone: T(anim_pos) T(pivot) R S T(-pivot)  (render frame)."""
    rot = [0.0, 0.0, 0.0]
    for r in (rotation, anim_rot):
        if r:
            rot = [rot[i] + r[i] for i in range(3)]
    piv = rh(pivot)
    m = _t(piv) @ rot_rh(rot) @ _s(scale) @ _t(-piv)
    if anim_pos:
        m = _t(rh(anim_pos)) @ m
    return m


class Pose:
    """Static animation pose: bone name (lower-case) -> dict(position, rotation, scale)."""

    def __init__(self, **bones):
        self.bones = {k.lower(): v for k, v in bones.items()}

    def merged(self, other: "Pose") -> "Pose":
        out = Pose()
        out.bones = {k: dict(v) for k, v in self.bones.items()}
        for k, v in other.bones.items():
            cur = out.bones.setdefault(k, {})
            for ch in ("position", "rotation"):
                if ch in v:
                    a = cur.get(ch, [0, 0, 0])
                    cur[ch] = [a[i] + v[ch][i] for i in range(3)]
            if "scale" in v:
                cur["scale"] = v["scale"]
        return out

    def get(self, name: str) -> dict:
        return self.bones.get(name.lower(), {})


def world_matrices(model: "Model", pose: Optional[Pose] = None, root: Optional[np.ndarray] = None,
                   bind: Optional[Dict[str, Tuple[np.ndarray, Tuple[float, float, float]]]] = None) -> Dict[str, np.ndarray]:
    """World matrix per bone. `bind` maps a target bone name to (target world matrix, target pivot);
    bones with a binding expression containing that name are attached with the -24 quirk."""
    pose = pose or Pose()
    root = root if root is not None else np.eye(4)
    by = {b.name: b for b in model.bones}
    out: Dict[str, np.ndarray] = {}

    def resolve(b: Bone) -> np.ndarray:
        if b.name in out:
            return out[b.name]
        a = pose.get(b.name)
        local = bone_local(b.pivot, b.rotation, a.get("position"), a.get("rotation"), a.get("scale", 1.0))
        parent = root
        if b.parent and b.parent in by:
            parent = resolve(by[b.parent])
        elif b.binding and bind:
            for target, (tm, tp) in bind.items():
                if f"'{target}'" in b.binding or b.binding == target:
                    parent = tm @ _t(rh((tp[0], tp[1] - 24.0, tp[2])))
                    break
        out[b.name] = parent @ local
        return out[b.name]

    for b in model.bones:
        resolve(b)
    return out


# =========================================================================== geometry loading (vanilla)

def load_vanilla_geometry(data: dict, identifier: str, texture: Image.Image, density: float = 1.0) -> "Model":
    """Build a Model from a vanilla geometry definition (box or per-face UV) with its texture."""
    geos = {}
    if "minecraft:geometry" in data:
        for g in data["minecraft:geometry"]:
            geos[g["description"]["identifier"]] = g
    else:
        for k, g in data.items():
            if k.startswith("geometry."):
                geos[k.split(":")[0]] = g
                geos[k] = g
    g = geos[identifier]
    bones_src = list(g.get("bones", []))
    # legacy inheritance "geometry.a:geometry.b"
    if not bones_src:
        for k, gv in data.items():
            if k.startswith(identifier + ":"):
                parent_id = k.split(":")[1]
                bones_src = list(geos[parent_id].get("bones", []))
                break
    m = Model(identifier, density)
    px = texture.convert("RGBA").load()
    tw, th = texture.size
    tex_w = g.get("texturewidth") or g.get("description", {}).get("texture_width") or tw
    sc = tw / tex_w
    for jb in bones_src:
        b = m.bone(jb["name"], jb.get("pivot", [0, 0, 0]), jb.get("parent"), jb.get("rotation"), jb.get("binding"))
        for jc in jb.get("cubes", []):
            size = jc["size"]
            uv = jc.get("uv", [0, 0])
            mirror = jc.get("mirror", jb.get("mirror", False))
            rects = {}
            if isinstance(uv, list):
                u, v = uv
                w, h, d = size
                rects = {
                    "up": (u + d, v, w, d), "down": (u + d + w, v, w, d),
                    "north": (u + d, v + d, w, h), "south": (u + d + w + d, v + d, w, h),
                    "east": (u, v + d, d, h), "west": (u + d + w, v + d, d, h),
                }
                if mirror:
                    rects["east"], rects["west"] = rects["west"], rects["east"]
            else:
                for face, fd in uv.items():
                    (u, v), (w, h) = fd["uv"], fd["uv_size"]
                    rects[face] = (u, v, w, h)

            def make(rect, mirror=mirror):
                u, v, w, h = rect

                def p(f: FaceCtx, u=u, v=v, w=w, h=h):
                    fx = f.u if not mirror else 1 - f.u
                    sx = int((u + fx * w) * sc)
                    sy = int((v + f.v * h) * sc)
                    sx = min(max(sx, 0), tw - 1)
                    sy = min(max(sy, 0), th - 1)
                    return px[sx, sy]
                return p
            fp = {face: make(r) for face, r in rects.items()}
            cube = Cube(tuple(jc["origin"]), tuple(size), lambda f: TRANSPARENT, faces=tuple(fp.keys()),
                        face_paint=fp, inflate=jc.get("inflate", 0.0),
                        pivot=tuple(jc["pivot"]) if "pivot" in jc else None,
                        rotation=tuple(jc["rotation"]) if "rotation" in jc else None)
            b.cubes.append(cube)
    return m


# =========================================================================== renderer

@dataclass
class Camera:
    pos: Tuple[float, float, float]      # render frame (already right-handed)
    target: Tuple[float, float, float]
    up: Tuple[float, float, float] = (0, 1, 0)
    fov: float = 70.0                    # vertical, degrees; 0 => orthographic
    ortho_height: float = 32.0


def _look(cam: Camera):
    pos, tgt = np.array(cam.pos, float), np.array(cam.target, float)
    fwd = tgt - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array(cam.up, float))
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return pos, fwd, right, up


class Scene:
    def __init__(self):
        self.quads = []   # (pts[4,3] render frame, rgba, normal, emissive, translucent)

    def add_model(self, model: Model, mats: Dict[str, np.ndarray], hide: Iterable[str] = ()):
        if model.texture is None:
            model.paint()
        hide = {h.lower() for h in hide}
        changed = True
        while changed:   # hiding a bone hides its descendants too
            changed = False
            for b in model.bones:
                if b.parent and b.parent.lower() in hide and b.name.lower() not in hide:
                    hide.add(b.name.lower())
                    changed = True
        px = model.texture.load()
        for bi, b in enumerate(model.bones):
            if b.name.lower() in hide:
                continue
            M = mats[b.name]
            for ci, c in enumerate(b.cubes):
                CM = np.eye(4)
                if c.rotation:
                    piv = rh(c.pivot or c.origin)
                    CM = _t(piv) @ rot_rh(c.rotation) @ _t(-piv)
                T = M @ CM
                for face in FACES:
                    key = (bi, ci, face)
                    if key not in model.uv:
                        continue
                    u0, v0, w, h = model.uv[key]
                    self._face(T, c, face, u0, v0, w, h, px)

    def _face(self, T, c: Cube, face, u0, v0, w, h, px):
        (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
        x0, y0, z0, x1, y1, z1 = ox - i, oy - i, oz - i, ox + sx + i, oy + sy + i, oz + sz + i
        # corners in Bedrock coords: tl, tr, bl  (consistent with Model.texel_pos)
        if face == "north":
            tl, tr, bl = (x0, y1, z0), (x1, y1, z0), (x0, y0, z0)
        elif face == "south":
            tl, tr, bl = (x1, y1, z1), (x0, y1, z1), (x1, y0, z1)
        elif face == "east":
            tl, tr, bl = (x0, y1, z1), (x0, y1, z0), (x0, y0, z1)
        elif face == "west":
            tl, tr, bl = (x1, y1, z0), (x1, y1, z1), (x1, y0, z0)
        elif face == "up":
            tl, tr, bl = (x0, y1, z1), (x1, y1, z1), (x0, y1, z0)
        else:
            tl, tr, bl = (x0, y0, z0), (x1, y0, z0), (x0, y0, z1)
        P = lambda p: (T @ np.append(rh(p), 1.0))[:3]
        a, b_, cc = P(tl), P(tr), P(bl)
        du, dv = (b_ - a) / w, (cc - a) / h
        n = np.cross(du, dv)
        nn = np.linalg.norm(n)
        n = n / nn if nn > 1e-9 else np.array([0, 1.0, 0])
        for yy in range(h):
            for xx in range(w):
                col = px[u0 + xx, v0 + yy]
                if col[3] < 24:
                    continue
                p0 = a + du * xx + dv * yy
                pts = np.array([p0, p0 + du, p0 + du + dv, p0 + dv])
                self.quads.append((pts, col, n, c.emissive, c.translucent or col[3] < 250))

    def render(self, cam: Camera, size=(640, 640), bg=(30, 34, 44, 255), light=(0.35, 0.8, -0.5),
               ambient=0.48, supersample=2, outline=False) -> Image.Image:
        W, H = size[0] * supersample, size[1] * supersample
        pos, fwd, right, up = _look(cam)
        L = np.array(light, float)
        L /= np.linalg.norm(L)
        img = Image.new("RGBA", (W, H), bg)
        draw = ImageDraw.Draw(img)
        buf = img.load()
        proj = []
        f = (H / 2) / math.tan(math.radians(cam.fov) / 2) if cam.fov else None
        for pts, col, n, emissive, translucent in self.quads:
            rel = pts - pos
            zc = rel @ fwd
            if f is not None and np.any(zc < 0.5):
                continue
            xs, ys = rel @ right, rel @ up
            if f is not None:
                sx = W / 2 + f * xs / zc
                sy = H / 2 - f * ys / zc
            else:
                k = H / cam.ortho_height
                sx = W / 2 + xs * k
                sy = H / 2 - ys * k
            # back-face cull (two-sided for translucent)
            cx = (sx[1] - sx[0]) * (sy[3] - sy[0]) - (sy[1] - sy[0]) * (sx[3] - sx[0])
            if cx < 0 and not translucent:
                continue
            depth = float(zc.mean())
            lam = max(0.0, float(np.dot(n, L))) if cx >= 0 else max(0.0, float(np.dot(-n, L)))
            k = 1.0 if emissive else min(1.15, ambient + (1 - ambient) * lam)
            proj.append((depth, list(zip(sx.tolist(), sy.tolist())), col, k, translucent))
        proj.sort(key=lambda q: -q[0])
        for depth, poly, col, k, translucent in proj:
            c = (min(255, int(col[0] * k)), min(255, int(col[1] * k)), min(255, int(col[2] * k)))
            if translucent:
                cxm = int(sum(p[0] for p in poly) / 4)
                cym = int(sum(p[1] for p in poly) / 4)
                if 0 <= cxm < W and 0 <= cym < H:
                    under = buf[cxm, cym]
                    a = col[3] / 255
                    c = tuple(int(c[i] * a + under[i] * (1 - a)) for i in range(3))
            draw.polygon(poly, fill=c + (255,))
        if supersample > 1:
            img = img.resize(size, Image.LANCZOS)
        return img


def orbit_camera(target=(0, 0, 0), dist=40.0, yaw=35.0, pitch=20.0, fov=30.0, ortho_height=None) -> Camera:
    """Camera looking at `target` (render frame) from yaw/pitch degrees; yaw 0 = in front (-Z)."""
    ty, tp = math.radians(yaw), math.radians(pitch)
    off = np.array([math.sin(ty) * math.cos(tp), math.sin(tp), -math.cos(ty) * math.cos(tp)]) * dist
    pos = np.array(target, float) + off
    cam = Camera(tuple(pos), tuple(target), fov=0 if ortho_height else fov)
    if ortho_height:
        cam.ortho_height = ortho_height
    return cam


def glow(img: Image.Image, mask_color_min: int = 235, radius: int = 6, strength: float = 0.8) -> Image.Image:
    """Bloom pass for previews: blur the brightest pixels and add them back."""
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    bright = np.where(arr.max(axis=2, keepdims=True) >= mask_color_min, arr, 0)
    b = Image.fromarray(bright.astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    out = np.clip(arr + np.asarray(b).astype(np.float32) * strength, 0, 255).astype(np.uint8)
    return Image.fromarray(out).convert("RGBA")
