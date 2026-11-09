"""
modelkit — a tiny procedural Bedrock model + texture toolkit.

Models are described in Python as bones made of cubes. Every cube carries a
"material" (a procedural painter) and optional per-face decals. The kit then:

  * packs every visible cube face into a texture atlas (per-face UV),
  * paints the atlas with the procedural materials,
  * emits Bedrock geometry JSON (format 1.16.0, per-face UV),
  * renders software previews (orthographic, painter's algorithm) so the
    models can be inspected without the game.

Coordinate conventions follow Bedrock geometry: units are 1/16 block, the
model faces -Z (north), model -X is the entity's right-hand side.
Rotation [rx, ry, rz] in degrees is Bedrock style; the right-handed
equivalent is (-rx, -ry, rz), applied X then Y then Z.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

RGBA = Tuple[int, int, int, int]
FACES = ("north", "south", "east", "west", "up", "down")


# --------------------------------------------------------------------------- colour

def hx(s: str, a: int = 255) -> RGBA:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


def mix(c1: RGBA, c2: RGBA, t: float) -> RGBA:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(4))  # type: ignore


def shade(c: RGBA, f: float) -> RGBA:
    """f > 0 lightens towards white, f < 0 darkens towards black."""
    if f >= 0:
        return mix(c, (255, 255, 255, c[3]), f)
    return mix(c, (0, 0, 0, c[3]), -f)


TRANSPARENT: RGBA = (0, 0, 0, 0)


# --------------------------------------------------------------------------- materials

@dataclass
class FaceCtx:
    """Information handed to painters for each texel of a face."""
    face: str
    x: int
    y: int
    w: int
    h: int
    rng: random.Random
    cube_index: int

    @property
    def u(self) -> float:
        return (self.x + 0.5) / self.w

    @property
    def v(self) -> float:
        return (self.y + 0.5) / self.h

    @property
    def edge(self) -> bool:
        return self.x == 0 or self.y == 0 or self.x == self.w - 1 or self.y == self.h - 1


Painter = Callable[[FaceCtx], RGBA]


def m_solid(base: str, var: float = 0.06, border: float = 0.12) -> Painter:
    c = hx(base)

    def p(f: FaceCtx) -> RGBA:
        col = shade(c, (f.rng.random() - 0.5) * 2 * var)
        if border and f.edge and min(f.w, f.h) > 2:
            col = shade(col, -border)
        return col
    return p


def m_scales(base: str, dark: str, light: Optional[str] = None, belly: Optional[str] = None) -> Painter:
    """Reptile scales: staggered diamonds with highlight rims. Optional belly on north face."""
    b, d = hx(base), hx(dark)
    l = hx(light) if light else shade(b, 0.25)
    bel = hx(belly) if belly else None

    def p(f: FaceCtx) -> RGBA:
        if bel is not None and f.face == "north":
            stripe = (f.y % 3 == 2)
            col = shade(bel, -0.12) if stripe else bel
            return shade(col, (f.rng.random() - 0.5) * 0.08)
        sx = (f.x + (f.y // 2) % 2) % 2
        sy = f.y % 2
        if sx == 0 and sy == 0:
            col = l
        elif sx == 1 and sy == 1:
            col = d
        else:
            col = b
        col = shade(col, (f.rng.random() - 0.5) * 0.1)
        if f.face == "down":
            col = shade(col, -0.15)
        return col
    return p


def m_stripes(base: str, stripe: str, period: int = 4, width: int = 1, axis: str = "x", var: float = 0.06) -> Painter:
    b, s = hx(base), hx(stripe)

    def p(f: FaceCtx) -> RGBA:
        k = f.x if axis == "x" else f.y
        col = s if (k % period) < width else b
        return shade(col, (f.rng.random() - 0.5) * 2 * var)
    return p


def m_gold(base: str = "e8b923", dark: str = "a8740c", light: str = "fff1a0") -> Painter:
    b, d, l = hx(base), hx(dark), hx(light)

    def p(f: FaceCtx) -> RGBA:
        t = f.v
        col = mix(l, b, min(1, t * 2.2)) if t < 0.45 else mix(b, d, (t - 0.45) / 0.55)
        if f.rng.random() < 0.05:
            col = shade(l, 0.4)
        if f.edge and min(f.w, f.h) > 2:
            col = shade(d, -0.1) if f.y == f.h - 1 else shade(col, 0.15)
        return col
    return p


def m_metal(base: str = "e9edf2", line: str = "9aa5b1", panel: int = 4, var: float = 0.03) -> Painter:
    b, ln = hx(base), hx(line)

    def p(f: FaceCtx) -> RGBA:
        col = shade(b, (f.rng.random() - 0.5) * 2 * var)
        col = shade(col, -0.10 * f.v)               # subtle vertical falloff
        if (f.x % panel == panel - 1 and f.w > panel + 1) or (f.y % panel == panel - 1 and f.h > panel + 1):
            col = mix(col, ln, 0.55)
        if f.edge:
            col = shade(col, -0.18)
        return col
    return p


def m_feather(base: str, tip: str, shaft: str, horizontal_tip: str = "u+") -> Painter:
    """Feather rows; tip colour grows towards one edge ('u+', 'u-', 'v+')."""
    b, t, sh = hx(base), hx(tip), hx(shaft)

    def p(f: FaceCtx) -> RGBA:
        if horizontal_tip == "u+":
            k = f.u
        elif horizontal_tip == "u-":
            k = 1 - f.u
        else:
            k = f.v
        row = f.y // 2 if horizontal_tip.startswith("u") else f.x // 2
        col = mix(b, t, max(0.0, (k - 0.35) / 0.65))
        col = shade(col, ((row % 3) - 1) * 0.07)
        if (f.y % 2 == 1) if horizontal_tip.startswith("u") else (f.x % 2 == 1):
            col = shade(col, -0.12)
        # ragged trailing edge
        if horizontal_tip.startswith("u") and k > 0.92 and (f.y % 2 == 1):
            return TRANSPARENT
        if horizontal_tip == "v+" and f.v > 0.9 and (f.x % 2 == 1):
            return TRANSPARENT
        if f.rng.random() < 0.04:
            col = sh
        return col
    return p


def m_noodle(base: str = "f2cf63", dark: str = "c99a2e", sauce: Optional[str] = None) -> Painter:
    """Strands of spaghetti; with sauce colour peeking between strands."""
    b, d = hx(base), hx(dark)
    s = hx(sauce) if sauce else None

    def p(f: FaceCtx) -> RGBA:
        # wavy horizontal strands
        wave = int(round(math.sin((f.x + f.cube_index * 3) * 0.9) * 1.0))
        k = (f.y + wave) % 3
        if k == 0:
            col = shade(b, 0.18)
        elif k == 1:
            col = b
        else:
            col = d if s is None or f.rng.random() < 0.55 else s
        return shade(col, (f.rng.random() - 0.5) * 0.08)
    return p


def m_meatball(base: str = "7a3e1d", dark: str = "4c230e", herb: str = "3d7a2a", sauce: str = "c0281b") -> Painter:
    b, d, hb, sc = hx(base), hx(dark), hx(herb), hx(sauce)

    def p(f: FaceCtx) -> RGBA:
        r = f.rng.random()
        if r < 0.05:
            col = hb
        elif r < 0.30:
            col = d
        elif r < 0.42:
            col = shade(b, 0.18)
        else:
            col = b
        if f.face == "up" and f.rng.random() < 0.45:
            col = mix(col, sc, 0.75)
        if f.face in ("north", "south", "east", "west") and f.v < 0.25 and f.rng.random() < 0.5:
            col = mix(col, sc, 0.6)
        return col
    return p


def m_glow(base: str, core: str) -> Painter:
    b, c = hx(base), hx(core)

    def p(f: FaceCtx) -> RGBA:
        dx, dy = f.u - 0.5, f.v - 0.5
        t = min(1.0, math.sqrt(dx * dx + dy * dy) * 2)
        return mix(c, b, t)
    return p


def m_flame(core: str = "fff6c8", mid: str = "ffb43b", outer: str = "ff4f1a") -> Painter:
    c, m, o = hx(core), hx(mid), hx(outer)

    def p(f: FaceCtx) -> RGBA:
        t = f.v
        if t < 0.35:
            col = mix(c, m, t / 0.35)
        else:
            col = mix(m, o, (t - 0.35) / 0.65)
        if t > 0.6 and f.rng.random() < (t - 0.6) * 2.2:
            return TRANSPARENT
        return col
    return p


def m_cloth(base: str, trim: str, trim_rows: int = 1, fold: float = 0.06) -> Painter:
    b, tr = hx(base), hx(trim)

    def p(f: FaceCtx) -> RGBA:
        if f.face in ("north", "south", "east", "west") and f.y >= f.h - trim_rows:
            return shade(tr, -0.15 if (f.x % 2) else 0.1)
        col = shade(b, -fold if f.x % 3 == 0 else 0)
        return shade(col, (f.rng.random() - 0.5) * 0.05)
    return p


def m_colander(base: str = "c9ced6", hole: str = "3a3f47") -> Painter:
    b, h = hx(base), hx(hole)

    def p(f: FaceCtx) -> RGBA:
        if f.face != "down" and f.x % 3 == 1 and f.y % 3 == 1:
            return h
        col = shade(b, 0.2 * (1 - f.v) - 0.1)
        if f.rng.random() < 0.04:
            col = shade(col, 0.4)
        return col
    return p


def m_bone(base: str = "f1ead2") -> Painter:
    b = hx(base)

    def p(f: FaceCtx) -> RGBA:
        return shade(b, -0.25 * f.v + (f.rng.random() - 0.5) * 0.05)
    return p


# --------------------------------------------------------------------------- model description

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
    faces: Optional[Tuple[str, ...]] = None      # restrict visible faces
    face_mats: Dict[str, Painter] = field(default_factory=dict)


@dataclass
class Bone:
    name: str
    pivot: Tuple[float, float, float]
    parent: Optional[str] = None
    rotation: Optional[Tuple[float, float, float]] = None
    cubes: List[Cube] = field(default_factory=list)

    def add(self, origin, size, mat, **kw) -> "Bone":
        self.cubes.append(Cube(tuple(origin), tuple(size), mat, **kw))
        return self


class Model:
    def __init__(self, identifier: str, seed: int = 1):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.texture: Optional[Image.Image] = None
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}

    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        b = Bone(name, tuple(pivot), parent, tuple(rotation) if rotation else None)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    # ---------------------------------------------------------------- packing
    @staticmethod
    def face_dims(c: Cube, face: str) -> Tuple[float, float]:
        sx, sy, sz = c.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def _visible_faces(self, c: Cube):
        for face in FACES:
            if c.faces is not None and face not in c.faces:
                continue
            w, h = self.face_dims(c, face)
            if w <= 0 or h <= 0:
                continue
            yield face, w, h

    def pack(self) -> Tuple[int, int]:
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, w, h in self._visible_faces(c):
                    tw, th = max(1, int(math.ceil(w - 1e-6))), max(1, int(math.ceil(h - 1e-6)))
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (32, 64, 128, 256, 512):
            if W * W * 2 < area * 1.15:
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
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier}")

    # ---------------------------------------------------------------- painting
    def paint(self) -> Image.Image:
        W, H = self.pack()
        img = Image.new("RGBA", (W, H), TRANSPARENT)
        px = img.load()
        rng = random.Random(self.seed)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            c = self.bones[bi].cubes[ci]
            painter = c.face_mats.get(face, c.mat)
            for yy in range(h):
                for xx in range(w):
                    px[u + xx, v + yy] = painter(FaceCtx(face, xx, yy, w, h, rng, bi * 31 + ci))
            dec = c.decals.get(face)
            if dec:
                def setp(x, y, col, u=u, v=v, w=w, h=h):
                    if 0 <= x < w and 0 <= y < h:
                        px[u + x, v + y] = col
                dec(setp, w, h)
        self.texture = img
        return img

    # ---------------------------------------------------------------- export
    def geometry_json(self, bounds_w: float = 3, bounds_h: float = 3, offset_y: float = 1.0) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.texture.size
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation:
                jb["rotation"] = list(b.rotation)
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = c.inflate
                if c.rotation:
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = list(c.rotation)
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
                "texture": self.texture.size if self.texture else None}


# --------------------------------------------------------------------------- preview renderer

def _rot_matrix(rot):
    if not rot:
        return None
    rx, ry, rz = (math.radians(-rot[0]), math.radians(-rot[1]), math.radians(rot[2]))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    Ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    Rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mm(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mm(Rz, mm(Ry, Rx))


def _apply(m, p, pivot):
    if m is None:
        return p
    x, y, z = p[0] - pivot[0], p[1] - pivot[1], p[2] - pivot[2]
    return (m[0][0] * x + m[0][1] * y + m[0][2] * z + pivot[0],
            m[1][0] * x + m[1][1] * y + m[1][2] * z + pivot[1],
            m[2][0] * x + m[2][1] * y + m[2][2] * z + pivot[2])


def _face_corners(c: Cube, face: str):
    """Return corners (top-left, top-right, bottom-left) in model space for texture mapping."""
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    x0, y0, z0 = ox - i, oy - i, oz - i
    x1, y1, z1 = ox + sx + i, oy + sy + i, oz + sz + i
    if face == "north":
        return (x0, y1, z0), (x1, y1, z0), (x0, y0, z0)
    if face == "south":
        return (x1, y1, z1), (x0, y1, z1), (x1, y0, z1)
    if face == "east":   # -x side in this kit's preview (mirrored model space)
        return (x0, y1, z1), (x0, y1, z0), (x0, y0, z1)
    if face == "west":
        return (x1, y1, z0), (x1, y1, z1), (x1, y0, z0)
    if face == "up":
        return (x0, y1, z1), (x1, y1, z1), (x0, y1, z0)
    return (x0, y0, z0), (x1, y0, z0), (x0, y0, z1)


def render_preview(models: List["Model"], path: str, yaw: float = 35, pitch: float = 20,
                   size: int = 512, extra_rot: Dict[str, Tuple[float, float, float]] = None,
                   bg=(46, 52, 64, 255), title: str = ""):
    """Render one or several models (sharing bone names) into a PNG."""
    extra_rot = extra_rot or {}
    quads = []
    for model in models:
        if model.texture is None:
            model.paint()
        px = model.texture.load()
        byname = {b.name: b for b in model.bones}

        def chain(b: Bone):
            out = []
            while b is not None:
                out.append(b)
                b = byname.get(b.parent) if b.parent else None
            return out
        for bi, b in enumerate(model.bones):
            bones_chain = chain(b)
            for ci, c in enumerate(b.cubes):
                cm = _rot_matrix(c.rotation)
                cpiv = c.pivot or c.origin

                def tf(p):
                    p = _apply(cm, p, cpiv)
                    for bb in bones_chain:
                        r = bb.rotation
                        er = extra_rot.get(bb.name)
                        if er:
                            r = tuple((r[i] if r else 0) + er[i] for i in range(3))
                        p = _apply(_rot_matrix(r), p, bb.pivot)
                    return p
                for face in FACES:
                    key = (bi, ci, face)
                    if key not in model.uv:
                        continue
                    u, v, w, h = model.uv[key]
                    tl, tr, bl = (tf(p) for p in _face_corners(c, face))
                    du = tuple((tr[k] - tl[k]) / w for k in range(3))
                    dv = tuple((bl[k] - tl[k]) / h for k in range(3))
                    for yy in range(h):
                        for xx in range(w):
                            col = px[u + xx, v + yy]
                            if col[3] < 128:
                                continue
                            p0 = tuple(tl[k] + du[k] * xx + dv[k] * yy for k in range(3))
                            p1 = tuple(p0[k] + du[k] for k in range(3))
                            p2 = tuple(p1[k] + dv[k] for k in range(3))
                            p3 = tuple(p0[k] + dv[k] for k in range(3))
                            quads.append(((p0, p1, p2, p3), col, face))
    if not quads:
        return
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def view(p):
        # look from -z (front) rotated by yaw around y, pitched down
        x, y, z = p
        x2 = x * cy - z * sy
        z2 = x * sy + z * cy
        y3 = y * cp + z2 * sp
        z3 = -y * sp + z2 * cp
        return (-x2, y3, z3)   # mirror x: model -x is entity right, shown on viewer's left
    proj = []
    for pts, col, face in quads:
        vp = [view(p) for p in pts]
        # back-face cull using screen-space winding
        ax, ay = vp[1][0] - vp[0][0], vp[1][1] - vp[0][1]
        bx, by = vp[3][0] - vp[0][0], vp[3][1] - vp[0][1]
        cross = ax * by - ay * bx
        if cross < 0:
            continue
        depth = sum(p[2] for p in vp) / 4
        light = {"up": 1.0, "north": 0.9, "south": 0.75, "east": 0.8, "west": 0.8, "down": 0.55}[face]
        proj.append((depth, vp, col, light))
    xs = [p[0] for _, vp, _, _ in proj for p in vp]
    ys = [p[1] for _, vp, _, _ in proj for p in vp]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) * 1.12 or 1
    scale = size / span
    cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    img = Image.new("RGBA", (size, size), bg)
    dr = ImageDraw.Draw(img)
    proj.sort(key=lambda q: -q[0])
    for depth, vp, col, light in proj:
        pts = [((p[0] - cxm) * scale + size / 2, size / 2 - (p[1] - cym) * scale) for p in vp]
        c = tuple(int(col[i] * light) for i in range(3)) + (255,)
        dr.polygon(pts, fill=c)
    if title:
        dr.text((8, 8), title, fill=(230, 230, 230, 255))
    img.save(path)
