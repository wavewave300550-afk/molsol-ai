"""
voxkit - procedural voxel model + texture toolkit for Bedrock entities.

Models are written in Python as bones made of cubes, in *model units* (u).
At export every coordinate is multiplied by ``scale`` so a boss can be built
at half size (1 u = 1/8 block) and exported at full size, while textures keep
``td`` texels per model unit.

Every cube carries a *material*: a function that receives a ``Face`` (texel
size, face name, rng, texture variant ...) and returns a numpy RGBA array.
Alpha 0 marks an emissive texel (material ``entity_emissive_alpha``): those
texels are drawn opaque and full-bright in game.

The kit
  * packs every visible face into one atlas (per-face UV, shelf packing),
  * paints the atlas once per texture *variant* with identical UVs,
  * emits Bedrock geometry JSON (format 1.16.0, per-face UV),
  * renders previews with a numpy z-buffer rasteriser using exactly the same
    rotation conventions as the game, so poses and animations can be checked.

Coordinates follow Bedrock geometry: the model faces -Z, the entity's right
side is -X. Bedrock euler rotations [rx, ry, rz] are converted to a right
handed frame (Blockbench convention: x mirrored, angles (-rx, -ry, rz), order
X then Y then Z).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")
Vec3 = Tuple[float, float, float]


# --------------------------------------------------------------------------- colour helpers

def hx(s: str) -> np.ndarray:
    s = s.lstrip("#")
    return np.array([int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)], dtype=np.float32)


def seeded(*parts) -> np.random.Generator:
    h = hashlib.sha1("|".join(str(p) for p in parts).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


@dataclass
class Face:
    """Everything a material needs to paint one cube face."""
    name: str
    w: int                  # texels
    h: int
    rng: np.random.Generator
    variant: int            # texture variant (0 normal, 1 cracked, 2 awakened ...)
    cube: "Cube"
    key: str                # stable identifier of the face (for seeding)
    cube_key: str = ""      # stable identifier of the cube (same for all its faces)

    def grid(self):
        """Normalised texel centre coordinates (u right, v down) in [0,1]."""
        ys, xs = np.mgrid[0:self.h, 0:self.w]
        return (xs + 0.5) / self.w, (ys + 0.5) / self.h


Material = Callable[[Face], np.ndarray]


def rgba(rgb: np.ndarray, alpha: float = 255) -> np.ndarray:
    out = np.empty(rgb.shape[:-1] + (4,), dtype=np.float32)
    out[..., :3] = rgb
    out[..., 3] = alpha
    return out


# --------------------------------------------------------------------------- model description

@dataclass
class Cube:
    origin: Vec3
    size: Vec3
    mat: Material
    rotation: Optional[Vec3] = None
    pivot: Optional[Vec3] = None
    inflate: float = 0.0
    faces: Optional[Tuple[str, ...]] = None
    face_mats: Dict[str, Material] = field(default_factory=dict)
    tag: str = ""


@dataclass
class Bone:
    name: str
    pivot: Vec3
    parent: Optional[str] = None
    rotation: Optional[Vec3] = None
    cubes: List[Cube] = field(default_factory=list)

    def box(self, origin, size, mat, **kw) -> Cube:
        c = Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mat, **kw)
        self.cubes.append(c)
        return c

    def span(self, a, b, mat, **kw) -> Cube:
        """Cube between two opposite corners."""
        lo = [min(a[i], b[i]) for i in range(3)]
        hi = [max(a[i], b[i]) for i in range(3)]
        return self.box(lo, [hi[i] - lo[i] for i in range(3)], mat, **kw)


class Model:
    def __init__(self, identifier: str, *, scale: float = 1.0, td: float = 1.0, seed: str = "m"):
        self.identifier = identifier
        self.scale = scale          # export multiplier for coordinates
        self.td = td                # texels per model unit
        self.seed = seed
        self.bones: List[Bone] = []
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.size: Tuple[int, int] = (0, 0)

    # ---------------------------------------------------------------- building
    def bone(self, name, pivot, parent=None, rotation=None) -> Bone:
        if any(b.name == name for b in self.bones):
            raise ValueError(f"duplicate bone {name}")
        b = Bone(name, tuple(float(v) for v in pivot), parent, tuple(rotation) if rotation else None)
        self.bones.append(b)
        return b

    def get(self, name) -> Bone:
        for b in self.bones:
            if b.name == name:
                return b
        raise KeyError(name)

    def mirror(self, src: str, dst: str, rename: Callable[[str], str]) -> None:
        """Mirror bone ``src`` and all its descendants across X (right <-> left)."""
        order = [b for b in self.bones]
        mapping = {}

        def descendants(name):
            out = [name]
            for b in order:
                if b.parent == name:
                    out += descendants(b.name)
            return out
        names = descendants(src)
        for n in names:
            mapping[n] = dst if n == src else rename(n)
        for n in names:
            b = self.get(n)
            parent = mapping.get(b.parent, b.parent)
            rot = (b.rotation[0], -b.rotation[1], -b.rotation[2]) if b.rotation else None
            nb = self.bone(mapping[n], (-b.pivot[0], b.pivot[1], b.pivot[2]), parent, rot)
            for c in b.cubes:
                o, s = c.origin, c.size
                fm = {}
                for k, v in c.face_mats.items():
                    fm[{"east": "west", "west": "east"}.get(k, k)] = v
                faces = None
                if c.faces is not None:
                    faces = tuple({"east": "west", "west": "east"}.get(f, f) for f in c.faces)
                nb.cubes.append(Cube(
                    (-(o[0] + s[0]), o[1], o[2]), s, c.mat,
                    rotation=(c.rotation[0], -c.rotation[1], -c.rotation[2]) if c.rotation else None,
                    pivot=(-c.pivot[0], c.pivot[1], c.pivot[2]) if c.pivot else None,
                    inflate=c.inflate, faces=faces, face_mats=fm, tag=c.tag))

    # ---------------------------------------------------------------- packing
    @staticmethod
    def face_dims(c: Cube, face: str):
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

    def pack(self, max_size: int = 1024) -> Tuple[int, int]:
        items = []
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                for face, w, h in self.visible_faces(c):
                    tw = max(1, int(math.ceil(w * self.td - 1e-6)))
                    th = max(1, int(math.ceil(h * self.td - 1e-6)))
                    items.append(((bi, ci, face), tw, th))
        items.sort(key=lambda it: (-it[2], -it[1]))
        area = sum(w * h for _, w, h in items)
        for W in (32, 64, 128, 256, 512, 1024, 2048):
            if W > max_size * 2 or W * W * 2 < area:
                continue
            placed = {}
            x = y = row_h = 0
            ok = True
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
            H = 16
            while H < y + row_h:
                H *= 2
            if H <= W:
                self.uv = placed
                self.size = (W, H)
                return W, H
        raise RuntimeError(f"cannot pack {self.identifier} ({area} texels)")

    # ---------------------------------------------------------------- painting
    def paint(self, variant: int = 0) -> Image.Image:
        if not self.uv:
            self.pack()
        W, H = self.size
        img = np.zeros((H, W, 4), dtype=np.float32)
        for (bi, ci, face), (u, v, w, h) in self.uv.items():
            b = self.bones[bi]
            c = b.cubes[ci]
            mat = c.face_mats.get(face, c.mat)
            key = f"{self.seed}/{b.name}/{ci}/{face}"
            f = Face(face, w, h, seeded(key), variant, c, key, f"{self.seed}/{b.name}/{ci}")
            tile = mat(f)
            assert tile.shape == (h, w, 4), (b.name, face, tile.shape, (h, w))
            img[v:v + h, u:u + w] = tile
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA")

    # ---------------------------------------------------------------- export
    def geometry_json(self, bounds_w: float, bounds_h: float, offset_y: float) -> dict:
        if not self.uv:
            self.pack()
        W, H = self.size
        s = self.scale

        def sc(v):
            return [round(x * s, 4) for x in v]
        bones = []
        for bi, b in enumerate(self.bones):
            jb = {"name": b.name, "pivot": sc(b.pivot)}
            if b.parent:
                jb["parent"] = b.parent
            if b.rotation:
                jb["rotation"] = [round(r, 3) for r in b.rotation]
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc = {"origin": sc(c.origin), "size": sc(c.size)}
                if c.inflate:
                    jc["inflate"] = round(c.inflate * s, 4)
                if c.rotation:
                    jc["pivot"] = sc(c.pivot or c.origin)
                    jc["rotation"] = [round(r, 3) for r in c.rotation]
                uv = {}
                for face in FACES:
                    key = (bi, ci, face)
                    if key in self.uv:
                        u, v, w, h = self.uv[key]
                        if face in ("up", "down"):
                            # Bedrock flips up/down faces: store them reversed so they read naturally
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

    def extent(self, pose: Optional[dict] = None):
        """Axis aligned bounds (model units) of the posed model: (min xyz, max xyz)."""
        pts = []
        for b, c, M, t in self._world_cubes(pose or {}):
            for corner in _corners(c):
                pts.append(M @ np.array(corner) + t)
        a = np.array(pts)
        # convert back from render space (x mirrored) to bedrock space
        a[:, 0] *= -1
        return a.min(0), a.max(0)

    # ---------------------------------------------------------------- render helpers
    def _world_cubes(self, pose: dict):
        """Yield (bone, cube, M, t) where world = M @ p + t in right handed render space."""
        byname = {b.name: b for b in self.bones}
        cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

        def bone_tf(name):
            if name in cache:
                return cache[name]
            b = byname[name]
            rot = list(b.rotation or (0, 0, 0))
            p = pose.get(name, {})
            r2 = p.get("rotation", (0, 0, 0))
            pos = p.get("position", (0, 0, 0))
            scl = p.get("scale", 1.0)
            rot = [rot[i] + r2[i] for i in range(3)]
            piv = _rs(b.pivot)
            R = _rot(rot)
            if isinstance(scl, (int, float)):
                S = np.eye(3) * scl
            else:
                S = np.diag(scl)
            L = R @ S
            # local transform: p -> L (p - piv) + piv + pos   (pos in bedrock units, x mirrored)
            off = piv - L @ piv + np.array([-pos[0], pos[1], pos[2]], dtype=float)
            if b.parent:
                PM, Pt = bone_tf(b.parent)
                M = PM @ L
                t = PM @ off + Pt
            else:
                M, t = L, off
            cache[name] = (M, t)
            return M, t
        for b in self.bones:
            M, t = bone_tf(b.name)
            for c in b.cubes:
                if c.rotation:
                    cp = _rs(c.pivot or c.origin)
                    R = _rot(c.rotation)
                    yield b, c, M @ R, M @ (cp - R @ cp) + t
                else:
                    yield b, c, M, t


def _rs(p) -> np.ndarray:
    """bedrock point -> render space (x mirrored)."""
    return np.array([-p[0], p[1], p[2]], dtype=float)


def _rot(rot) -> np.ndarray:
    rx, ry, rz = (math.radians(-rot[0]), math.radians(-rot[1]), math.radians(rot[2]))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _corners(c: Cube):
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    # render space: x mirrored
    x0, x1 = -(ox + sx) - i, -ox + i
    y0, y1 = oy - i, oy + sy + i
    z0, z1 = oz - i, oz + sz + i
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def _face_frame(c: Cube, face: str):
    """Texture frame of a face in render space: (top-left, +u edge, +v edge, outward normal)."""
    (ox, oy, oz), (sx, sy, sz), i = c.origin, c.size, c.inflate
    # bedrock-space box
    X0, X1 = ox - i, ox + sx + i
    Y0, Y1 = oy - i, oy + sy + i
    Z0, Z1 = oz - i, oz + sz + i
    # Texture frames follow Blockbench (textures read un-mirrored from outside the cube);
    # bedrock "east" is the -x side, "west" the +x side.
    if face == "north":
        tl, ue, ve, n = (X0, Y1, Z0), (X1 - X0, 0, 0), (0, Y0 - Y1, 0), (0, 0, -1)
    elif face == "south":
        tl, ue, ve, n = (X1, Y1, Z1), (X0 - X1, 0, 0), (0, Y0 - Y1, 0), (0, 0, 1)
    elif face == "east":
        tl, ue, ve, n = (X0, Y1, Z1), (0, 0, Z0 - Z1), (0, Y0 - Y1, 0), (-1, 0, 0)
    elif face == "west":
        tl, ue, ve, n = (X1, Y1, Z0), (0, 0, Z1 - Z0), (0, Y0 - Y1, 0), (1, 0, 0)
    elif face == "up":
        tl, ue, ve, n = (X1, Y1, Z0), (X0 - X1, 0, 0), (0, 0, Z1 - Z0), (0, 1, 0)
    else:  # down
        tl, ue, ve, n = (X1, Y0, Z1), (X0 - X1, 0, 0), (0, 0, Z0 - Z1), (0, -1, 0)
    f = lambda v: np.array([-v[0], v[1], v[2]], dtype=float)  # noqa: E731
    return f(tl), f(ue), f(ve), f(n)


# --------------------------------------------------------------------------- renderer

def render(model: Model, textures: Image.Image, *, yaw: float = 0.0, pitch: float = 0.0, size: int = 512,
           pose: Optional[dict] = None, bg=(255, 255, 255), margin: float = 0.06,
           fixed_span: Optional[float] = None, center: Optional[Tuple[float, float]] = None,
           glow: bool = True) -> Image.Image:
    """Orthographic z-buffer render. yaw=0 looks at the model's front (camera on -Z)."""
    tex = np.asarray(textures.convert("RGBA"), dtype=np.float32)
    TH, TW = tex.shape[:2]
    cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    # camera basis in render space. Camera starts at -Z looking +Z; yaw rotates the camera around +Y.
    fwd = np.array([-math.sin(math.radians(yaw)) * cp, -sp, math.cos(math.radians(yaw)) * cp])
    up_world = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up_world)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    light = -fwd * 0.55 + up * 0.75 + right * 0.35     # key light follows the camera (studio turnaround)
    light /= np.linalg.norm(light)

    faces = []
    for b, c, M, t in model._world_cubes(pose or {}):
        for face in FACES:
            key = (model.bones.index(b), b.cubes.index(c), face)
            if key not in model.uv:
                continue
            tl, ue, ve, n = _face_frame(c, face)
            P0 = M @ tl + t
            U = M @ ue
            V = M @ ve
            N = M @ n
            if np.dot(N, fwd) >= -1e-6:
                continue
            faces.append((P0, U, V, N, model.uv[key]))
    if not faces:
        return Image.new("RGB", (size, size), bg)
    # bounds
    pts = []
    for P0, U, V, N, _ in faces:
        for q in (P0, P0 + U, P0 + V, P0 + U + V):
            pts.append((np.dot(q, right), np.dot(q, up)))
    pts = np.array(pts)
    minx, miny = pts.min(0)
    maxx, maxy = pts.max(0)
    span = fixed_span or max(maxx - minx, maxy - miny) * (1 + 2 * margin)
    if center is None:
        cxm, cym = (minx + maxx) / 2, (miny + maxy) / 2
    else:
        cxm, cym = center
    sc = size / span
    color = np.zeros((size, size, 3), dtype=np.float32)
    color[:] = bg
    depth = np.full((size, size), np.inf, dtype=np.float32)
    emis = np.zeros((size, size), dtype=np.float32)
    for P0, U, V, N, (u0, v0, w, h) in faces:
        # screen coords of the parallelogram
        o = np.array([(np.dot(P0, right) - cxm) * sc + size / 2, size / 2 - (np.dot(P0, up) - cym) * sc])
        a = np.array([np.dot(U, right) * sc, -np.dot(U, up) * sc])
        bvec = np.array([np.dot(V, right) * sc, -np.dot(V, up) * sc])
        det = a[0] * bvec[1] - a[1] * bvec[0]
        if abs(det) < 1e-9:
            continue
        corners = np.array([o, o + a, o + bvec, o + a + bvec])
        x0, y0 = np.floor(corners.min(0)).astype(int)
        x1, y1 = np.ceil(corners.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size), min(y1, size)
        if x0 >= x1 or y0 >= y1:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        px = xs + 0.5 - o[0]
        py = ys + 0.5 - o[1]
        s = (px * bvec[1] - py * bvec[0]) / det
        tt = (a[0] * py - a[1] * px) / det
        inside = (s >= 0) & (s < 1) & (tt >= 0) & (tt < 1)
        if not inside.any():
            continue
        d0 = np.dot(P0, fwd)
        dz = d0 + s * np.dot(U, fwd) + tt * np.dot(V, fwd)
        tu = np.clip((u0 + s * w).astype(int), u0, u0 + w - 1)
        tv = np.clip((v0 + tt * h).astype(int), v0, v0 + h - 1)
        texel = tex[tv, tu]
        m = inside & (dz < depth[ys, xs])
        if not m.any():
            continue
        yy, xx = ys[m], xs[m]
        tcol = texel[m]
        lam = 0.55 + 0.45 * max(0.0, float(np.dot(N / np.linalg.norm(N), light)))
        lam += 0.12 * max(0.0, float(np.dot(N / np.linalg.norm(N), -fwd)))
        is_glow = tcol[:, 3] < 250
        shaded = tcol[:, :3] * min(lam, 1.08)
        g = (1 - tcol[:, 3] / 255.0)[:, None]
        shaded = shaded * (1 - g) + tcol[:, :3] * g * 1.08
        color[yy, xx] = shaded
        depth[yy, xx] = dz[m]
        emis[yy, xx] = np.where(is_glow, g[:, 0], 0)
    out = np.clip(color, 0, 255)
    if glow and emis.any():
        im = Image.fromarray((emis * 255).astype(np.uint8), "L")
        from PIL import ImageFilter
        blur = np.asarray(im.filter(ImageFilter.GaussianBlur(radius=size / 90)), dtype=np.float32) / 255.0
        halo = np.array([255, 196, 60], dtype=np.float32)
        out = np.clip(out + blur[..., None] * halo * 0.65, 0, 255)
    return Image.fromarray(out.astype(np.uint8), "RGB")
