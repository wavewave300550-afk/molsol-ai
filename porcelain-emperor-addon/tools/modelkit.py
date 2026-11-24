"""
modelkit - a small procedural Bedrock model + texture toolkit.

Models are described in Python as bones made of cubes. Every cube carries a
"material" (a procedural painter) and optional per-face decals. The kit then:

  * packs every visible cube face into a texture atlas (per-face UV),
  * paints the atlas with the procedural materials, once per texture variant
    (the Porcelain Emperor has three: pristine, kintsugi and shattered; all
    variants share one UV layout so the render controller can swap them),
  * emits Bedrock geometry JSON (format 1.16.0, per-face UV),
  * renders software previews (orthographic, painter's algorithm) so the
    models can be inspected without the game.

Glow: textures are used with the `entity_emissive_alpha` material, where a
pixel's emissive strength is proportional to its transparency. Painters mark
glowing texels with `glow(colour, strength)`, which lowers alpha (never to 0).

Coordinate conventions follow Bedrock geometry: units are 1/16 block, the
model faces -Z (north), model -X is the entity's right-hand side and the
"east" face of a cube is its -X face.
Rotation [rx, ry, rz] in degrees is Bedrock style. In geometry space the
right-handed equivalent is (-rx, +ry, -rz), applied X then Y then Z. This was
derived from vanilla data (zombie arms at rx=-90 point forward; the humanoid
idle bob uses +rz on the right arm to swing it outwards, exactly like Java's
zRot; Blockbench exports rotations as [-x, -y, z] in its X-mirrored space).
Consequences used by the animations:
  +rx  tilts forward-pointing parts down, lifts backward-pointing parts,
       swings hanging parts backwards;
  +ry  turns forward-pointing parts towards -X (the entity's right);
  +rz  swings hanging parts towards -X, tilts upright parts towards +X.
Animation position offsets are in geometry space (+x = towards +X).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

RGBA = Tuple[int, int, int, int]
FACES = ("north", "south", "east", "west", "up", "down")
TRANSPARENT: RGBA = (0, 0, 0, 0)


# --------------------------------------------------------------------------- colour

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


GLOW_RANGE = 105   # alpha 255 (no glow) .. 150 (full glow)


def glow(c: RGBA, strength: float) -> RGBA:
    """Mark a texel as emissive. strength 0..1 -> alpha 255..150.

    entity_emissive_alpha makes a pixel glow in proportion to its transparency.
    Alpha never drops below 150 (~0.59) so the pixel survives an alpha-test
    cut-off at 0.5, should the material apply one."""
    s = max(0.0, min(1.0, strength))
    return (c[0], c[1], c[2], int(round(255 - s * GLOW_RANGE)))


def opaque(c: RGBA) -> RGBA:
    return (c[0], c[1], c[2], 255)


# --------------------------------------------------------------------------- palette

PAL = {
    "ivory_hi": hx("fbf6ea"),
    "ivory": hx("f1e8d4"),
    "ivory_mid": hx("e3d6bb"),
    "ivory_lo": hx("cdbb98"),
    "ivory_deep": hx("a8936c"),
    "vein": hx("cfc3ab"),
    "grime": hx("7d6c55"),
    "gold_hi": hx("fff3b8"),
    "gold": hx("f6c64f"),
    "gold_mid": hx("d99a26"),
    "gold_lo": hx("9c6612"),
    "core": hx("ffd86a"),
    "core_hot": hx("fff6d6"),
    "red": hx("c7322a"),
    "red_hi": hx("e65a43"),
    "red_lo": hx("7f1a16"),
    "cobalt": hx("2f4f9f"),
    "cobalt_lo": hx("1d3270"),
    "jade": hx("6fae8c"),
    "jade_lo": hx("3f7a5c"),
    "pearl": hx("f4f0ff"),
    "ink": hx("2a2420"),
}


# --------------------------------------------------------------------------- face context

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
    variant: int = 0
    seed: int = 0          # stable per face (same in every variant)

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


def hash01(*vals: int) -> float:
    """Deterministic hash -> [0,1)."""
    h = 2166136261
    for v in vals:
        h ^= (v + 0x9E3779B9) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
    return (h & 0xFFFFFF) / float(0x1000000)


def vnoise(x: float, y: float, seed: int) -> float:
    """Smooth value noise in [0,1)."""
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)

    def r(ix, iy):
        return hash01(ix, iy, seed)
    a = r(x0, y0) + (r(x0 + 1, y0) - r(x0, y0)) * sx
    b = r(x0, y0 + 1) + (r(x0 + 1, y0 + 1) - r(x0, y0 + 1)) * sx
    return a + (b - a) * sy


def fbm(x: float, y: float, seed: int, octaves: int = 3) -> float:
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += vnoise(x, y, seed + o * 101) * amp
        norm += amp
        x, y, amp = x * 2.03, y * 2.03, amp * 0.5
    return total / norm


# --------------------------------------------------------------------------- crack fields

class CrackField:
    """Per-face crack network. Lines grow with the variant (0 pristine .. 2 shattered).

    Every face gets the same base cracks in every variant; later variants add
    branches and widen seams, so the damage reads as progressive.
    """
    _cache: Dict[Tuple[int, int, int, int], Dict[Tuple[int, int], float]] = {}

    @classmethod
    def get(cls, seed: int, w: int, h: int, variant: int, density: float = 1.0) -> Dict[Tuple[int, int], float]:
        key = (seed, w, h, variant * 1000 + int(density * 100))
        if key in cls._cache:
            return cls._cache[key]
        cells: Dict[Tuple[int, int], float] = {}
        rng = random.Random(seed * 7919 + 17)
        area = w * h
        # base veins (all variants) + extra cracks per variant
        n_lines = [max(0, int(area / 260 * density)), max(1, int(area / 140 * density)),
                   max(2, int(area / 85 * density))]
        total = n_lines[min(variant, 2)]
        for i in range(total):
            lrng = random.Random(seed * 131 + i * 977)
            x, y = lrng.uniform(0, w), lrng.uniform(0, h)
            ang = lrng.uniform(0, math.tau)
            length = lrng.uniform(0.35, 0.9) * (w + h) * 0.5
            strength = 1.0 if i < n_lines[0] else (0.8 if i < n_lines[1] else 0.65)
            steps = int(length)
            for s in range(steps):
                ix, iy = int(x), int(y)
                if 0 <= ix < w and 0 <= iy < h:
                    cells[(ix, iy)] = max(cells.get((ix, iy), 0), strength)
                    if variant >= 2 and lrng.random() < 0.35:
                        nx, ny = ix + lrng.choice((-1, 1)), iy
                        if 0 <= nx < w:
                            cells[(nx, ny)] = max(cells.get((nx, ny), 0), strength * 0.7)
                ang += lrng.uniform(-0.6, 0.6)
                x += math.cos(ang)
                y += math.sin(ang)
                if lrng.random() < 0.05 * (variant + 1):
                    ang += lrng.choice((-1.1, 1.1))
        _ = rng
        cls._cache[key] = cells
        return cells


# --------------------------------------------------------------------------- materials

def m_marble(base: str = "ivory", crack_density: float = 1.0, chip: bool = True) -> Painter:
    """Ivory marble with soft veins and gold (kintsugi) seams that multiply per variant."""
    b = PAL[base]

    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.x * 0.22 + f.seed * 0.37, f.y * 0.22 + f.cube_index, f.seed % 997)
        col = mix(PAL["ivory_hi"], b, n * 1.2)
        col = mix(col, PAL["ivory_mid"], max(0.0, n - 0.55) * 1.6)
        # soft grey-beige veins
        vein = abs(math.sin((f.x * 0.45 + f.y * 0.18) + fbm(f.x * 0.15, f.y * 0.15, f.seed + 7) * 6.0))
        if vein < 0.08:
            col = mix(col, PAL["vein"], 0.55)
        if f.face == "down":
            col = shade(col, -0.12)
        cracks = CrackField.get(f.seed, f.w, f.h, f.variant, crack_density)
        c = cracks.get((f.x, f.y))
        if c:
            if f.variant == 0:
                return glow(mix(PAL["gold_mid"], PAL["gold"], c), 0.25)
            g = mix(PAL["gold"], PAL["gold_hi"], c * 0.6)
            return glow(g, 0.35 + 0.25 * f.variant * c)
        if chip and f.variant >= 2:
            ch = fbm(f.x * 0.3, f.y * 0.3, f.seed + 4242)
            if ch > 0.71:
                # chipped porcelain revealing the inner light
                t = (ch - 0.71) / 0.29
                return glow(mix(PAL["core"], PAL["core_hot"], t), 0.55 + 0.4 * t)
            if ch > 0.66:
                return shade(col, -0.3)
        if f.variant >= 1:
            grime = fbm(f.x * 0.12, f.y * 0.12, f.seed + 99)
            if grime > 0.66:
                col = mix(col, PAL["ivory_lo"], (grime - 0.66) * 1.8)
        if f.edge and min(f.w, f.h) > 3:
            col = shade(col, -0.07)
        return opaque(col)
    return p


def m_gold(glow_amt: float = 0.2) -> Painter:
    def p(f: FaceCtx) -> RGBA:
        t = f.v
        col = mix(PAL["gold_hi"], PAL["gold"], min(1, t * 2.2)) if t < 0.45 else mix(PAL["gold"], PAL["gold_mid"], (t - 0.45) / 0.55)
        n = hash01(f.x, f.y, f.seed)
        if n < 0.06:
            col = PAL["gold_hi"]
        elif n > 0.94:
            col = PAL["gold_lo"]
        if f.edge and min(f.w, f.h) > 2:
            col = shade(col, -0.15) if f.y == f.h - 1 else shade(col, 0.12)
        return glow(col, glow_amt + 0.1 * f.variant)
    return p


def m_core() -> Painter:
    """The inner light of the Mandate: hot gold, strongly emissive, pulsing veins."""
    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.x * 0.35, f.y * 0.35, f.seed + 5)
        col = mix(PAL["core"], PAL["core_hot"], n)
        if hash01(f.x, f.y, f.seed + 3) < 0.08:
            col = PAL["gold_mid"]
        return glow(col, 0.75 + 0.2 * n)
    return p


def m_lacquer(base: str = "red") -> Painter:
    b = PAL[base]

    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.x * 0.3, f.y * 0.3, f.seed)
        col = mix(shade(b, 0.12), PAL[base + "_lo"] if base + "_lo" in PAL else shade(b, -0.3), n)
        if (f.x + f.y) % 7 == 0 and hash01(f.x, f.y, f.seed) < 0.3:
            col = shade(col, 0.15)
        cracks = CrackField.get(f.seed, f.w, f.h, f.variant, 0.6)
        if f.variant >= 1 and cracks.get((f.x, f.y)):
            return glow(PAL["gold"], 0.4)
        return opaque(col)
    return p


def m_jade() -> Painter:
    def p(f: FaceCtx) -> RGBA:
        n = fbm(f.x * 0.4, f.y * 0.4, f.seed + 11)
        col = mix(PAL["jade"], PAL["jade_lo"], n)
        if n < 0.25:
            col = shade(col, 0.25)
        return opaque(col)
    return p


def m_pearl() -> Painter:
    def p(f: FaceCtx) -> RGBA:
        col = mix(PAL["pearl"], hx("d8d0ea"), f.v)
        if f.x == 0 and f.y == 0:
            col = hx("ffffff")
        return glow(col, 0.2)
    return p


def m_solid(base: RGBA, var: float = 0.05, glow_amt: float = 0.0) -> Painter:
    def p(f: FaceCtx) -> RGBA:
        col = shade(base, (hash01(f.x, f.y, f.seed) - 0.5) * 2 * var)
        return glow(col, glow_amt) if glow_amt > 0 else opaque(col)
    return p


def m_ribbon() -> Painter:
    """Gold-leaf calligraphy ribbon (whiskers, mane)."""
    def p(f: FaceCtx) -> RGBA:
        t = (f.x + f.y * 0.5) % 6
        col = PAL["gold_hi"] if t < 1 else (PAL["gold"] if t < 4 else PAL["gold_mid"])
        return glow(col, 0.3 + 0.1 * f.variant)
    return p


def m_claw() -> Painter:
    def p(f: FaceCtx) -> RGBA:
        col = mix(PAL["gold_hi"], PAL["gold_lo"], f.v)
        return glow(col, 0.3)
    return p


def m_tablet(broad: Tuple[str, ...] = ("east", "west")) -> Painter:
    """Edict tablet: ivory slab, gold frame, cobalt edict strokes, red seal on the broad faces."""
    marble = m_marble("ivory", 0.8, chip=False)

    def p(f: FaceCtx) -> RGBA:
        if f.face in broad and f.w >= 5 and f.h >= 8:
            if f.x == 0 or f.x == f.w - 1 or f.y == 0 or f.y == f.h - 1:
                return glow(PAL["gold"], 0.3)
            # red seal near the bottom
            if f.h - 4 <= f.y <= f.h - 2 and 1 <= f.x <= f.w - 2:
                return opaque(PAL["red"] if (f.x + f.y) % 3 else PAL["red_hi"])
            # vertical columns of cobalt "edict" strokes
            col_idx = f.x - 1
            if col_idx % 2 == 0 and 1 <= f.y <= f.h - 6:
                if hash01(col_idx, f.y, f.seed) < 0.62:
                    return opaque(PAL["cobalt"] if hash01(f.y, col_idx, 3) < 0.8 else PAL["cobalt_lo"])
        return marble(f)
    return p


# --------------------------------------------------------------------------- model description

Decal = Callable[[Callable[[int, int, RGBA], None], int, int, int], None]


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

    def box(self, center, size, mat, **kw) -> "Bone":
        """Add a cube by centre instead of min corner."""
        o = tuple(center[i] - size[i] / 2 for i in range(3))
        return self.add(o, size, mat, **kw)


class Model:
    def __init__(self, identifier: str, seed: int = 1):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self.seed = seed
        self.textures: Dict[int, Image.Image] = {}
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.size: Optional[Tuple[int, int]] = None

    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        if any(b.name == name for b in self.bones):
            raise ValueError(f"duplicate bone {name}")
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
        if self.size:
            return self.size
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, w, h in self._visible_faces(c):
                    tw, th = max(1, int(math.ceil(w - 1e-6))), max(1, int(math.ceil(h - 1e-6)))
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (32, 64, 128, 256, 512, 1024):
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

    # ---------------------------------------------------------------- painting
    def paint(self, variant: int = 0) -> Image.Image:
        if variant in self.textures:
            return self.textures[variant]
        W, H = self.pack()
        img = Image.new("RGBA", (W, H), TRANSPARENT)
        px = img.load()
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            c = self.bones[bi].cubes[ci]
            painter = c.face_mats.get(face, c.mat)
            face_seed = (self.seed * 1009 + bi * 131 + ci * 17 + FACES.index(face)) & 0xFFFFF
            rng = random.Random(face_seed)
            for yy in range(h):
                for xx in range(w):
                    px[u + xx, v + yy] = painter(FaceCtx(face, xx, yy, w, h, rng, bi * 31 + ci, variant, face_seed))
            dec = c.decals.get(face)
            if dec:
                def setp(x, y, col, u=u, v=v, w=w, h=h):
                    if 0 <= x < w and 0 <= y < h:
                        px[u + x, v + y] = col
                dec(setp, w, h, variant)
        self.textures[variant] = img
        return img

    # ---------------------------------------------------------------- export
    def geometry_json(self, bounds_w: float = 3, bounds_h: float = 3, offset_y: float = 1.0) -> dict:
        W, H = self.pack()
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
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones), "texture": self.size}


# --------------------------------------------------------------------------- preview renderer

def _rot_matrix(rot):
    if not rot or not any(rot):
        return None
    rx, ry, rz = (math.radians(-rot[0]), math.radians(rot[1]), math.radians(-rot[2]))
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


def render_preview(models: List[Model], path: str, yaw: float = 35, pitch: float = 20,
                   size: int = 512, extra_rot: Dict[str, Tuple[float, float, float]] = None,
                   extra_pos: Dict[str, Tuple[float, float, float]] = None,
                   hidden: Tuple[str, ...] = (), variant: int = 0,
                   bg=(46, 52, 64, 255), title: str = "", supersample: int = 2):
    """Render one or several models into a PNG (orthographic, painter's algorithm)."""
    extra_rot = extra_rot or {}
    extra_pos = extra_pos or {}
    quads = []
    for model in models:
        tex = model.paint(variant)
        px = tex.load()
        byname = {b.name: b for b in model.bones}

        def chain(b: Bone):
            out = []
            while b is not None:
                out.append(b)
                b = byname.get(b.parent) if b.parent else None
            return out

        def is_hidden(b: Bone) -> bool:
            return any(bb.name in hidden for bb in chain(b))
        for bi, b in enumerate(model.bones):
            if is_hidden(b):
                continue
            bones_chain = chain(b)
            for ci, c in enumerate(b.cubes):
                cm = _rot_matrix(c.rotation)
                cpiv = c.pivot or c.origin

                def tf(p, bones_chain=bones_chain, cm=cm, cpiv=cpiv):
                    p = _apply(cm, p, cpiv)
                    for bb in bones_chain:
                        r = bb.rotation
                        er = extra_rot.get(bb.name)
                        if er:
                            r = tuple((r[i] if r else 0) + er[i] for i in range(3))
                        p = _apply(_rot_matrix(r), p, bb.pivot)
                        ep = extra_pos.get(bb.name)
                        if ep:
                            p = (p[0] + ep[0], p[1] + ep[1], p[2] + ep[2])
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
                            if col[3] == 0:
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
        x, y, z = p
        x2 = x * cy - z * sy
        z2 = x * sy + z * cy
        y3 = y * cp + z2 * sp
        z3 = -y * sp + z2 * cp
        # in game, facing the entity's front, its left (+X) is on the viewer's right
        return (x2, y3, z3)
    proj = []
    for pts, col, face in quads:
        vp = [view(p) for p in pts]
        ax, ay = vp[1][0] - vp[0][0], vp[1][1] - vp[0][1]
        bx, by = vp[3][0] - vp[0][0], vp[3][1] - vp[0][1]
        cross = ax * by - ay * bx
        if cross > 0:
            continue
        depth = sum(p[2] for p in vp) / 4
        light = {"up": 1.0, "north": 0.9, "south": 0.75, "east": 0.8, "west": 0.8, "down": 0.55}[face]
        proj.append((depth, vp, col, light))
    if not proj:
        return
    xs = [p[0] for _, vp, _, _ in proj for p in vp]
    ys = [p[1] for _, vp, _, _ in proj for p in vp]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) * 1.08 or 1
    S = size * supersample
    scale = S / span
    cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    img = Image.new("RGBA", (S, S), bg)
    dr = ImageDraw.Draw(img)
    proj.sort(key=lambda q: -q[0])
    for depth, vp, col, light in proj:
        pts = [((p[0] - cxm) * scale + S / 2, S / 2 - (p[1] - cym) * scale) for p in vp]
        g = (255 - col[3]) / float(GLOW_RANGE) if col[3] < 255 else 0.0     # emissive strength
        lit = light + (1.0 - light) * g
        c = tuple(min(255, int(col[i] * lit + 40 * g)) for i in range(3)) + (255,)
        dr.polygon(pts, fill=c)
    if supersample > 1:
        img = img.resize((size, size), Image.LANCZOS)
    if title:
        ImageDraw.Draw(img).text((8, 8), title, fill=(230, 230, 230, 255))
    img.save(path)
    return img
