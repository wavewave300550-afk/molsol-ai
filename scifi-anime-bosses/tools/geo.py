"""
geo.py - procedural Bedrock geometry kit with trim-sheet texturing.

Conventions (verified against vanilla data, see docs/REPORT.md):
  * units are 1/16 block, the model front faces -Z, model -X is the entity's right side;
  * a bone/cube rotation [rx, ry, rz] (degrees) is the right-handed matrix
        R = Rz(-rz) . Ry(+ry) . Rx(-rx)          (X applied first)
    in Bedrock model space, about the pivot.  (+rx pitches the front down,
    +ry turns the front towards -X = the entity's right.)

A Model holds bones; every cube face is mapped either onto a shared material
swatch of the atlas (trim-sheet style, texel density chosen per face) or onto a
unique atlas region painted by its own painter.  Cubes can be routed to three
render passes: the opaque main pass, an additive "glow" pass and a "shield" pass;
every pass is exported as a separate geometry with the identical skeleton so the
same animations drive all of them.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Vec = Tuple[float, float, float]
FACES = ("north", "south", "east", "west", "up", "down")


# ----------------------------------------------------------------------------- vector math

def v_add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def v_sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def v_mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def v_dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def v_len(a): return math.sqrt(v_dot(a, a))


def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_norm(a):
    l = v_len(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-12 else (0.0, 0.0, 0.0)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def m_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def m_apply(m, p):
    return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
            m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
            m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2])


IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def bedrock_matrix(rot: Optional[Sequence[float]]):
    """Right-handed rotation matrix for a Bedrock [rx, ry, rz] rotation."""
    if not rot or not any(rot):
        return IDENT
    rx, ry, rz = (math.radians(v) for v in rot)
    return m_mul(rot_z(-rz), m_mul(rot_y(ry), rot_x(-rx)))


def bedrock_angles(m) -> Tuple[float, float, float]:
    """Inverse of bedrock_matrix (columns of m are the rotated local axes)."""
    sb = -m[2][0]
    sb = max(-1.0, min(1.0, sb))
    beta = math.asin(sb)
    if abs(math.cos(beta)) > 1e-6:
        alpha = math.atan2(m[2][1], m[2][2])
        gamma = math.atan2(m[1][0], m[0][0])
    else:  # gimbal lock
        alpha = math.atan2(-m[1][2], m[1][1])
        gamma = 0.0
    return (round(-math.degrees(alpha), 4), round(math.degrees(beta), 4), round(-math.degrees(gamma), 4))


def basis_matrix(ex: Vec, ey: Vec, ez: Vec):
    return ((ex[0], ey[0], ez[0]), (ex[1], ey[1], ez[1]), (ex[2], ey[2], ez[2]))


# ----------------------------------------------------------------------------- materials

@dataclass
class Mat:
    """Face material: a swatch name (shared trim sheet) or a unique painter.

    density: texels per model unit.  When the face is larger than the swatch the
    density is lowered so the face still fits (keeps aspect ratio).
    """
    swatch: Optional[str] = None
    density: float = 0.5
    painter: Optional[Callable] = None     # unique: painter(w, h, variant) -> np.ndarray RGBA
    key: Optional[str] = None               # unique region cache key (identical faces share)
    seed: int = 0

    def with_seed(self, seed):
        return Mat(self.swatch, self.density, self.painter, self.key, seed)


def S(name: str, density: float = 0.5) -> Mat:
    return Mat(swatch=name, density=density)


def U(painter: Callable, key: str, density: float = 1.0) -> Mat:
    return Mat(painter=painter, key=key, density=density)


# ----------------------------------------------------------------------------- model description

@dataclass
class Cube:
    origin: Vec
    size: Vec
    mat: Mat
    rotation: Optional[Vec] = None
    pivot: Optional[Vec] = None
    inflate: float = 0.0
    face_mats: Dict[str, Mat] = field(default_factory=dict)
    faces: Optional[Tuple[str, ...]] = None
    layer: str = "main"     # main | glow | shield


@dataclass
class Bone:
    name: str
    pivot: Vec
    parent: Optional[str] = None
    rotation: Optional[Vec] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Vec] = field(default_factory=dict)


class Model:
    def __init__(self, identifier: str, tex_size=(512, 512), glow_tex_size=(128, 128),
                 shield_tex_size=(64, 64)):
        self.identifier = identifier
        self.bones: List[Bone] = []
        self._by_name: Dict[str, Bone] = {}
        self.tex_size = tex_size
        self.glow_tex_size = glow_tex_size
        self.shield_tex_size = shield_tex_size
        self.uv: Dict[Tuple[str, int, str], Tuple[float, float, float, float]] = {}
        self.bounds = (8.0, 8.0, (0.0, 2.0, 0.0))

    # ------------------------------------------------------------ building
    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        if name in self._by_name:
            raise ValueError(f"duplicate bone {name}")
        if parent is not None and parent not in self._by_name:
            raise ValueError(f"bone {name}: unknown parent {parent}")
        b = Bone(name, tuple(float(v) for v in pivot), parent, tuple(rotation) if rotation else None)
        self.bones.append(b)
        self._by_name[name] = b
        return b

    def get(self, name) -> Bone:
        return self._by_name[name]

    def has(self, name) -> bool:
        return name in self._by_name

    def box(self, bone: str, center: Vec, size: Vec, mat: Mat, rotation=None, pivot=None, inflate=0.0,
            layer="main", face_mats=None, faces=None) -> Cube:
        """Axis-aligned (optionally rotated about pivot/center) box given its centre."""
        c = Cube(origin=(center[0] - size[0] / 2, center[1] - size[1] / 2, center[2] - size[2] / 2),
                 size=tuple(size), mat=mat, rotation=tuple(rotation) if rotation else None,
                 pivot=tuple(pivot) if pivot else (tuple(center) if rotation else None), inflate=inflate,
                 face_mats=dict(face_mats or {}), faces=faces, layer=layer)
        self._by_name[bone].cubes.append(c)
        return c

    def obox(self, bone: str, center: Vec, axes: Tuple[Vec, Vec, Vec], size: Vec, mat: Mat, **kw) -> Cube:
        """Oriented box: local x/y/z axes given in model space (orthonormal)."""
        ex, ey, ez = (v_norm(a) for a in axes)
        rot = bedrock_angles(basis_matrix(ex, ey, ez))
        if all(abs(r) < 1e-6 for r in rot):
            rot = None
        return self.box(bone, center, size, mat, rotation=rot, pivot=center, **kw)

    def beam(self, bone: str, p0: Vec, p1: Vec, w: float, h: float, mat: Mat, up: Vec = (0, 1, 0),
             extend: float = 0.0, **kw) -> Cube:
        """Box spanning p0 -> p1 (its local z axis), cross-section w x h."""
        d = v_sub(p1, p0)
        length = v_len(d) + 2 * extend
        ez = v_norm(d)
        ex = v_cross(up, ez)
        if v_len(ex) < 1e-6:
            ex = v_cross((1, 0, 0), ez)
        ex = v_norm(ex)
        ey = v_norm(v_cross(ez, ex))
        center = v_mul(v_add(p0, p1), 0.5)
        return self.obox(bone, center, (ex, ey, ez), (w, h, length), mat, **kw)

    def ring(self, bone: str, center: Vec, radius: float, axis: str, segments: int, radial: float, depth: float,
             mat: Mat, arc=(0.0, 360.0), gap: float = 0.0, phase: float = 0.0, layer="main", face_mats=None,
             every=None) -> List[Cube]:
        """Ring of tangent boxes around `axis` ('x','y','z'). Returns the cubes."""
        cubes = []
        a0, a1 = arc
        span = (a1 - a0) / segments
        seg_len = 2 * math.pi * radius * (span / 360.0) * (1.0 - gap) + radial * 0.35
        for i in range(segments):
            if every is not None and not every(i):
                continue
            th = math.radians(a0 + phase + span * (i + 0.5))
            if axis == "z":
                p = (center[0] + radius * math.cos(th), center[1] + radius * math.sin(th), center[2])
                radial_v = (math.cos(th), math.sin(th), 0.0)
                ax = (0.0, 0.0, 1.0)
            elif axis == "y":
                p = (center[0] + radius * math.cos(th), center[1], center[2] + radius * math.sin(th))
                radial_v = (math.cos(th), 0.0, math.sin(th))
                ax = (0.0, 1.0, 0.0)
            else:
                p = (center[0], center[1] + radius * math.cos(th), center[2] + radius * math.sin(th))
                radial_v = (0.0, math.cos(th), math.sin(th))
                ax = (1.0, 0.0, 0.0)
            tangent = v_norm(v_cross(ax, radial_v))
            # local x = tangent (length), local y = radial (thickness), local z = axis (depth)
            ez = ax
            ex = tangent
            ey = v_cross(ez, ex)
            cubes.append(self.obox(bone, p, (ex, ey, ez), (seg_len, radial, depth), mat, layer=layer,
                                   face_mats=face_mats))
        return cubes

    def locator(self, bone: str, name: str, pos: Vec):
        self._by_name[bone].locators[name] = tuple(pos)

    # ------------------------------------------------------------ uv mapping
    @staticmethod
    def face_dims(c: Cube, face: str) -> Tuple[float, float]:
        sx, sy, sz = (s + 2 * c.inflate for s in c.size)
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def iter_faces(self, layer: str):
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                if c.layer != layer:
                    continue
                for face in FACES:
                    if c.faces is not None and face not in c.faces:
                        continue
                    w, h = self.face_dims(c, face)
                    if w <= 1e-6 or h <= 1e-6:
                        continue
                    yield b, ci, c, face, w, h

    def map_uvs(self, atlas: "AtlasLayout", layer: str):
        """Assign UV rectangles for every face of the layer using the atlas layout."""
        for b, ci, c, face, w, h in self.iter_faces(layer):
            mat = c.face_mats.get(face, c.mat)
            key = (b.name, ci, face)
            seed_src = f"{self.identifier}:{b.name}:{ci}:{face}"
            seed = int(hashlib.md5(seed_src.encode()).hexdigest()[:8], 16)
            if mat.painter is not None:
                tw = max(1, int(round(w * mat.density)))
                th = max(1, int(round(h * mat.density)))
                region = atlas.unique(mat.key or seed_src, tw, th, mat.painter)
                u, v, rw, rh = region
                self.uv[key] = (u, v, rw, rh)
                continue
            sw = atlas.swatch(mat.swatch)
            su, sv, swd, sht = sw
            d = mat.density
            tw, th = w * d, h * d
            scale = min(1.0, swd / tw if tw > 0 else 1.0, sht / th if th > 0 else 1.0)
            tw, th = max(1.0, tw * scale), max(1.0, th * scale)
            tw, th = round(tw * 2) / 2, round(th * 2) / 2      # half-texel quantisation
            tw, th = min(tw, swd), min(th, sht)
            max_u = swd - tw
            max_v = sht - th
            ou = (seed % 997) / 997.0 * max_u
            ov = ((seed // 997) % 991) / 991.0 * max_v
            ou, ov = math.floor(ou), math.floor(ov)
            self.uv[key] = (su + ou, sv + ov, tw, th)

    # ------------------------------------------------------------ export
    def geometry_json(self, layer: str, identifier: Optional[str] = None, tex_size=None) -> dict:
        tw, th = tex_size or (self.tex_size if layer == "main" else
                              self.glow_tex_size if layer == "glow" else self.shield_tex_size)
        bones = []
        for b in self.bones:
            jb = {"name": b.name, "pivot": [round(v, 4) for v in b.pivot]}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation and any(b.rotation):
                jb["rotation"] = [round(v, 4) for v in b.rotation]
            cubes = []
            for ci, c in enumerate(b.cubes):
                if c.layer != layer:
                    continue
                jc = {"origin": [round(v, 4) for v in c.origin], "size": [round(v, 4) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = round(c.inflate, 4)
                if c.rotation and any(c.rotation):
                    jc["pivot"] = [round(v, 4) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [round(v, 4) for v in c.rotation]
                uv = {}
                for face in FACES:
                    k = (b.name, ci, face)
                    if k not in self.uv:
                        continue
                    u, v, w, h = self.uv[k]
                    if face in ("up", "down"):
                        # Bedrock samples up/down faces flipped compared to the side faces
                        uv[face] = {"uv": [round(u + w, 4), round(v + h, 4)], "uv_size": [round(-w, 4), round(-h, 4)]}
                    else:
                        uv[face] = {"uv": [round(u, 4), round(v, 4)], "uv_size": [round(w, 4), round(h, 4)]}
                jc["uv"] = uv
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            if b.locators and layer == "main":
                jb["locators"] = {k: [round(x, 4) for x in p] for k, p in b.locators.items()}
            bones.append(jb)
        bw, bh, boff = self.bounds
        return {
            "format_version": "1.21.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": identifier or (self.identifier if layer == "main" else f"{self.identifier}.{layer}"),
                    "texture_width": tw,
                    "texture_height": th,
                    "visible_bounds_width": bw,
                    "visible_bounds_height": bh,
                    "visible_bounds_offset": list(boff),
                },
                "bones": bones,
            }],
        }

    def stats(self) -> dict:
        out = {"bones": len(self.bones)}
        for layer in ("main", "glow", "shield"):
            out[f"cubes_{layer}"] = sum(1 for b in self.bones for c in b.cubes if c.layer == layer)
        return out

    def layers(self) -> List[str]:
        return [l for l in ("main", "glow", "shield") if any(c.layer == l for b in self.bones for c in b.cubes)]

    # ------------------------------------------------------------ world transforms (for previews/validation)
    def bone_world_matrices(self, pose: Optional[Dict[str, dict]] = None):
        """Return {bone: (R, t)} so that p_model = R @ p_local + t for points authored in model space.

        pose[bone] may carry 'rotation' (added to rest rotation), 'position' (translation in model
        units) and 'scale' (uniform or xyz) like Bedrock animations.
        """
        pose = pose or {}
        out = {}

        def solve(b: Bone):
            if b.name in out:
                return out[b.name]
            p = pose.get(b.name, {})
            rot = list(b.rotation or (0, 0, 0))
            if "rotation" in p:
                rot = [rot[i] + p["rotation"][i] for i in range(3)]
            R = bedrock_matrix(rot)
            sc = p.get("scale", (1, 1, 1))
            if isinstance(sc, (int, float)):
                sc = (sc, sc, sc)
            S_ = ((sc[0], 0, 0), (0, sc[1], 0), (0, 0, sc[2]))
            RS = m_mul(R, S_)
            pos = p.get("position", (0, 0, 0))
            # local transform: x -> pivot + RS (x - pivot) + pos
            t_local = v_add(v_sub(b.pivot, m_apply(RS, b.pivot)), pos)
            if b.parent:
                PR, Pt = solve(self._by_name[b.parent])
                R_w = m_mul(PR, RS)
                t_w = v_add(m_apply(PR, t_local), Pt)
            else:
                R_w, t_w = RS, t_local
            out[b.name] = (R_w, t_w)
            return out[b.name]
        for b in self.bones:
            solve(b)
        return out


# ----------------------------------------------------------------------------- atlas layout

class AtlasLayout:
    """Shelf-packed atlas of named swatches + unique regions."""

    def __init__(self, width: int, height: int):
        self.W, self.H = width, height
        self.swatches: Dict[str, Tuple[int, int, int, int]] = {}
        self.swatch_painters: Dict[str, Callable] = {}
        self.uniques: Dict[str, Tuple[int, int, int, int]] = {}
        self.unique_painters: Dict[str, Callable] = {}
        self._free: List[Tuple[int, int, int, int]] = [(0, 0, width, height)]   # MaxRects free list
        self._next_y = 0

    def _alloc(self, w: int, h: int) -> Tuple[int, int]:
        """MaxRects best-short-side-fit allocation."""
        best = None
        for (fx, fy, fw, fh) in self._free:
            if w <= fw and h <= fh:
                score = (min(fw - w, fh - h), max(fw - w, fh - h), fy, fx)
                if best is None or score < best[0]:
                    best = (score, fx, fy)
        if best is None:
            raise RuntimeError(f"atlas {self.W}x{self.H} full allocating {w}x{h}")
        _, x, y = best
        placed = (x, y, w, h)
        new_free = []
        for fr in self._free:
            new_free.extend(self._split(fr, placed))
        # prune rectangles contained in others
        pruned = []
        for i, a in enumerate(new_free):
            contained = False
            for j, b in enumerate(new_free):
                if i != j and b[0] <= a[0] and b[1] <= a[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]:
                    if a != b or i > j:
                        contained = True
                        break
            if not contained:
                pruned.append(a)
        self._free = pruned
        self._next_y = max(self._next_y, y + h)
        return x, y

    @staticmethod
    def _split(fr, used):
        fx, fy, fw, fh = fr
        ux, uy, uw, uh = used
        if ux >= fx + fw or ux + uw <= fx or uy >= fy + fh or uy + uh <= fy:
            return [fr]
        out = []
        if ux > fx:
            out.append((fx, fy, ux - fx, fh))
        if ux + uw < fx + fw:
            out.append((ux + uw, fy, fx + fw - (ux + uw), fh))
        if uy > fy:
            out.append((fx, fy, fw, uy - fy))
        if uy + uh < fy + fh:
            out.append((fx, uy + uh, fw, fy + fh - (uy + uh)))
        return [r for r in out if r[2] > 0 and r[3] > 0]

    def add_swatch(self, name: str, w: int, h: int, painter: Callable):
        x, y = self._alloc(w, h)
        self.swatches[name] = (x, y, w, h)
        self.swatch_painters[name] = painter

    def swatch(self, name: str):
        if name not in self.swatches:
            raise KeyError(f"unknown swatch {name}")
        return self.swatches[name]

    def unique(self, key: str, w: int, h: int, painter: Callable):
        if key in self.uniques:
            return self.uniques[key]
        x, y = self._alloc(w, h)
        self.uniques[key] = (x, y, w, h)
        self.unique_painters[key] = painter
        return self.uniques[key]

    def used_height(self) -> int:
        return self._next_y

    def render(self, variant: str):
        import numpy as np
        img = np.zeros((self.H, self.W, 4), dtype=np.float32)
        for name, (x, y, w, h) in self.swatches.items():
            img[y:y + h, x:x + w] = self.swatch_painters[name](w, h, variant)
        for key, (x, y, w, h) in self.uniques.items():
            img[y:y + h, x:x + w] = self.unique_painters[key](w, h, variant)
        return img
