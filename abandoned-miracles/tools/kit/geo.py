"""
geo.py - procedural Bedrock geometry: bones, cubes, per-face UV atlas, export.

A model is described in Python as bones holding cubes. Every cube names a
material (a painter from paint.py). The kit then

  * packs every cube face into a texture atlas (per-face UV, optional sharing),
  * paints the atlas,
  * writes Bedrock `minecraft:geometry` JSON (format 1.12.0),
  * writes an editable Blockbench `.bbmodel`,
  * provides forward kinematics so tools (renderer, design checks) can pose it.

Coordinate conventions (Bedrock geometry space, "geo"):
  units are 1/16 block; the model faces -Z; geo -X is the creature's RIGHT.
  Geo space is mirrored: the physical ("display") space is (-x, y, z).
  A Bedrock rotation [rx, ry, rz] (degrees) is, in geo coordinates,
      R = Rz(-rz) . Ry(ry) . Rx(-rx)        (standard right-handed matrices)
  which is exactly Blockbench's (x,y negated, ZYX order) seen through the mirror.
"""
from __future__ import annotations

import base64
import io
import math
import uuid
import zlib
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")
Vec = Tuple[float, float, float]


def seed_of(*parts) -> int:
    """Stable 32-bit seed from arbitrary parts (Python's hash() is salted per run)."""
    return zlib.crc32("|".join(str(p) for p in parts).encode())


# --------------------------------------------------------------------------- maths

def rot_matrix(rot: Optional[Iterable[float]]) -> np.ndarray:
    """Bedrock rotation (degrees) -> 3x3 matrix acting on geo coordinates."""
    if rot is None:
        return np.eye(3)
    rx, ry, rz = (math.radians(-rot[0]), math.radians(rot[1]), math.radians(-rot[2]))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def affine(R: np.ndarray, t: Iterable[float]) -> np.ndarray:
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def pivot_transform(pivot: Vec, rot=None, pos=(0, 0, 0), scale=(1, 1, 1)) -> np.ndarray:
    """T(pivot + pos) . R . S . T(-pivot)"""
    R = rot_matrix(rot) @ np.diag(scale)
    p = np.asarray(pivot, float)
    return affine(R, p + np.asarray(pos, float) - R @ p)


# --------------------------------------------------------------------------- description

@dataclass
class Cube:
    origin: Vec
    size: Vec
    mat: object                                  # material name or painter callable
    inflate: float = 0.0
    pivot: Optional[Vec] = None
    rotation: Optional[Vec] = None
    density: Optional[float] = None              # texels per unit (default: model density)
    faces: Optional[Tuple[str, ...]] = None      # restrict emitted faces
    uv_key: Optional[object] = None              # cubes with equal keys share atlas rects
    face_mat: Dict[str, object] = field(default_factory=dict)
    decal: Dict[str, Callable] = field(default_factory=dict)
    tag: str = ""

    def face_dims(self, face: str) -> Tuple[float, float]:
        sx, sy, sz = self.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def corners(self, face: str):
        """(top-left, top-right, bottom-left) of the face's texture rect, geo coordinates,
        as seen from outside the cube. Matches Bedrock per-face UV with positive uv_size."""
        (ox, oy, oz), (sx, sy, sz), i = self.origin, self.size, self.inflate
        x0, y0, z0 = ox - i, oy - i, oz - i
        x1, y1, z1 = ox + sx + i, oy + sy + i, oz + sz + i
        return {
            "north": ((x0, y1, z0), (x1, y1, z0), (x0, y0, z0)),
            "south": ((x1, y1, z1), (x0, y1, z1), (x1, y0, z1)),
            "east": ((x0, y1, z1), (x0, y1, z0), (x0, y0, z1)),    # geo -X side
            "west": ((x1, y1, z0), (x1, y1, z1), (x1, y0, z0)),    # geo +X side
            "up": ((x0, y1, z1), (x1, y1, z1), (x0, y1, z0)),
            "down": ((x0, y0, z0), (x1, y0, z0), (x0, y0, z1)),
        }[face]


@dataclass
class Bone:
    name: str
    pivot: Vec
    parent: Optional[str] = None
    rotation: Optional[Vec] = None
    cubes: List[Cube] = field(default_factory=list)
    locators: Dict[str, Vec] = field(default_factory=dict)

    def box(self, origin, size, mat, **kw) -> Cube:
        c = Cube(tuple(float(v) for v in origin), tuple(float(v) for v in size), mat, **kw)
        self.cubes.append(c)
        return c

    def cbox(self, center, size, mat, **kw) -> Cube:
        """Box given by its centre."""
        o = tuple(center[k] - size[k] / 2 for k in range(3))
        return self.box(o, size, mat, **kw)

    def rod(self, a, b, thick, mat, **kw) -> Cube:
        """Axis-aligned bar between two points that differ along one axis only."""
        lo = [min(a[k], b[k]) for k in range(3)]
        hi = [max(a[k], b[k]) for k in range(3)]
        for k in range(3):
            if hi[k] - lo[k] < 1e-6:
                lo[k] -= thick / 2
                hi[k] += thick / 2
        return self.box(lo, [hi[k] - lo[k] for k in range(3)], mat, **kw)

    def locator(self, name: str, pos) -> None:
        self.locators[name] = tuple(float(v) for v in pos)


class Model:
    def __init__(self, identifier: str, density: float = 1.0, bounds=(8.0, 8.0, 3.0)):
        self.identifier = identifier                 # e.g. "geometry.abm.vesperra"
        self.density = density
        self.bounds = bounds                         # visible bounds width, height, offset y (blocks)
        self.bones: List[Bone] = []
        self._by: Dict[str, Bone] = {}
        self.materials: Dict[str, Callable] = {}
        self.uv: Dict[Tuple[int, int, str], Tuple[int, int, int, int]] = {}
        self.tex_size: Tuple[int, int] = (0, 0)
        self.texture: Optional[Image.Image] = None

    # ---------------------------------------------------------------- building
    def bone(self, name: str, pivot, parent: Optional[str] = None, rotation=None) -> Bone:
        if name in self._by:
            raise ValueError(f"duplicate bone {name}")
        if parent is not None and parent not in self._by:
            raise ValueError(f"bone {name}: unknown parent {parent}")
        b = Bone(name, tuple(float(v) for v in pivot), parent,
                 tuple(float(v) for v in rotation) if rotation else None)
        self.bones.append(b)
        self._by[name] = b
        return b

    def get(self, name: str) -> Bone:
        return self._by[name]

    def has(self, name: str) -> bool:
        return name in self._by

    def chain(self, name: str) -> List[Bone]:
        out = []
        b: Optional[Bone] = self._by[name]
        while b is not None:
            out.append(b)
            b = self._by[b.parent] if b.parent else None
        return out

    def children(self, name: str) -> List[str]:
        return [b.name for b in self.bones if b.parent == name]

    def descendants(self, name: str) -> List[str]:
        out = []
        for c in self.children(name):
            out.append(c)
            out.extend(self.descendants(c))
        return out

    # ---------------------------------------------------------------- kinematics
    def matrices(self, pose: Optional[dict] = None) -> Dict[str, np.ndarray]:
        """World (geo-space) 4x4 matrix per bone. pose: bone -> {'rot','pos','scale'}."""
        pose = pose or {}
        out: Dict[str, np.ndarray] = {}
        for b in self.bones:                               # parents are always declared first
            p = pose.get(b.name) or {}
            r = list(b.rotation or (0, 0, 0))
            if "rot" in p:
                r = [r[k] + p["rot"][k] for k in range(3)]
            M = pivot_transform(b.pivot, r, p.get("pos", (0, 0, 0)), p.get("scale", (1, 1, 1)))
            out[b.name] = out[b.parent] @ M if b.parent else M
        return out

    def point(self, bone: str, p, pose: Optional[dict] = None, mats=None) -> np.ndarray:
        """Geo-space position of layout point `p` attached to `bone` under `pose`."""
        mats = mats or self.matrices(pose)
        return (mats[bone] @ np.array([p[0], p[1], p[2], 1.0]))[:3]

    def locator_point(self, name: str, pose=None, mats=None) -> np.ndarray:
        for b in self.bones:
            if name in b.locators:
                return self.point(b.name, b.locators[name], pose, mats)
        raise KeyError(name)

    def extent(self, pose=None):
        """Axis-aligned bounds (min, max) of the posed model in geo space."""
        mats = self.matrices(pose)
        lo, hi = np.full(3, 1e9), np.full(3, -1e9)
        for b in self.bones:
            for c in b.cubes:
                Mc = mats[b.name]
                if c.rotation:
                    Mc = Mc @ pivot_transform(c.pivot or c.origin, c.rotation)
                o, s, i = np.array(c.origin), np.array(c.size), c.inflate
                for dx in (0, 1):
                    for dy in (0, 1):
                        for dz in (0, 1):
                            p = o - i + (s + 2 * i) * np.array([dx, dy, dz])
                            w = (Mc @ np.append(p, 1.0))[:3]
                            lo, hi = np.minimum(lo, w), np.maximum(hi, w)
        return lo, hi

    # ---------------------------------------------------------------- atlas
    def _faces(self):
        for bi, b in enumerate(self.bones):
            for ci, c in enumerate(b.cubes):
                d = c.density or self.density
                for face in FACES:
                    if c.faces is not None and face not in c.faces:
                        continue
                    w, h = c.face_dims(face)
                    if w <= 0 or h <= 0:
                        continue
                    yield bi, ci, face, max(1, int(math.ceil(w * d - 1e-6))), max(1, int(math.ceil(h * d - 1e-6)))

    def pack(self, max_size: int = 1024) -> Tuple[int, int]:
        groups: Dict[object, Tuple[int, int]] = {}
        members: Dict[object, List[Tuple[int, int, str]]] = {}
        for bi, ci, face, w, h in self._faces():
            c = self.bones[bi].cubes[ci]
            key = ("s", c.uv_key, face, w, h) if c.uv_key is not None else ("u", bi, ci, face)
            groups[key] = (w, h)
            members.setdefault(key, []).append((bi, ci, face))
        items = sorted(groups.items(), key=lambda kv: (-kv[1][1], -kv[1][0], str(kv[0])))
        area = sum(w * h for _, (w, h) in items)
        sizes = [(w, h) for w in (64, 128, 256, 512, 1024) for h in (w // 2, w) if h >= 32 and w <= max_size]
        for W, H in sorted(sizes, key=lambda s: (s[0] * s[1], s[0])):
            if W * H < area:
                continue
            placed = {}
            x = y = row = 0
            ok = True
            for key, (w, h) in items:
                if w > W:
                    ok = False
                    break
                if x + w > W:
                    x, y, row = 0, y + row, 0
                if y + h > H:
                    ok = False
                    break
                placed[key] = (x, y, w, h)
                x += w
                row = max(row, h)
            if ok:
                self.uv = {m: placed[key] for key in placed for m in members[key]}
                self._rect_owner = {key: members[key][0] for key in placed}
                self.tex_size = (W, H)
                return W, H
        raise RuntimeError(f"{self.identifier}: cannot pack {len(items)} faces ({area} px) into {max_size}^2")

    def paint(self) -> Image.Image:
        from . import paint as P                      # local import: paint needs geo types
        W, H = self.pack()
        img = np.zeros((H, W, 4), dtype=np.float32)
        done = set()
        for (bi, ci, face), (u, v, w, h) in sorted(self.uv.items(), key=lambda kv: (kv[1][1], kv[1][0])):
            if (u, v) in done:
                continue
            done.add((u, v))
            b = self.bones[bi]
            c = b.cubes[ci]
            mat = c.face_mat.get(face, c.mat)
            painter = self.materials[mat] if isinstance(mat, str) else mat
            ctx = P.FaceCtx(self, b, c, face, w, h, seed_of(self.identifier, b.name if c.uv_key is None else c.uv_key,
                                                             ci if c.uv_key is None else "", face))
            px = np.clip(np.asarray(painter(ctx), dtype=np.float32), 0, 1)
            if px.shape != (h, w, 4):
                raise ValueError(f"painter for {b.name}/{face} returned {px.shape}, wanted {(h, w, 4)}")
            dec = c.decal.get(face) or c.decal.get("*")
            if dec:
                px = np.clip(np.asarray(dec(ctx, px), dtype=np.float32), 0, 1)
            img[v:v + h, u:u + w] = px
        self.texture = Image.fromarray((img * 255 + 0.5).astype(np.uint8), "RGBA")
        return self.texture

    # ---------------------------------------------------------------- export
    def geometry_json(self) -> dict:
        if self.texture is None:
            self.paint()
        W, H = self.tex_size
        bones = []
        for bi, b in enumerate(self.bones):
            jb: dict = {"name": b.name}
            if b.parent:
                jb["parent"] = b.parent
            jb["pivot"] = [_r(v) for v in b.pivot]
            if b.rotation and any(abs(v) > 1e-9 for v in b.rotation):
                jb["rotation"] = [_r(v) for v in b.rotation]
            cubes = []
            for ci, c in enumerate(b.cubes):
                jc: dict = {"origin": [_r(v) for v in c.origin], "size": [_r(v) for v in c.size]}
                if c.inflate:
                    jc["inflate"] = _r(c.inflate)
                if c.rotation and any(abs(v) > 1e-9 for v in c.rotation):
                    jc["pivot"] = [_r(v) for v in (c.pivot or c.origin)]
                    jc["rotation"] = [_r(v) for v in c.rotation]
                uv = {}
                for face in FACES:
                    r = self.uv.get((bi, ci, face))
                    if r:
                        uv[face] = {"uv": [r[0], r[1]], "uv_size": [r[2], r[3]]}
                jc["uv"] = uv
                cubes.append(jc)
            if cubes:
                jb["cubes"] = cubes
            if b.locators:
                jb["locators"] = {k: [_r(x) for x in p] for k, p in b.locators.items()}
            bones.append(jb)
        bw, bh, oy = self.bounds
        return {
            "format_version": "1.12.0",
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

    def bbmodel_json(self, name: str) -> dict:
        """Editable Blockbench project (Bedrock entity format, per-face UV, embedded texture)."""
        if self.texture is None:
            self.paint()
        W, H = self.tex_size

        def uid(*parts) -> str:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, "abm/" + self.identifier + "/" + "/".join(str(p) for p in parts)))

        elements = []
        nodes: Dict[str, dict] = {}
        for bi, b in enumerate(self.bones):
            r = b.rotation or (0, 0, 0)
            node = {"name": b.name, "origin": [_r(-b.pivot[0]), _r(b.pivot[1]), _r(b.pivot[2])],
                    "rotation": [_r(-r[0]), _r(-r[1]), _r(r[2])], "color": bi % 8, "uuid": uid("bone", b.name),
                    "export": True, "mirror_uv": False, "isOpen": False, "locked": False, "visibility": True,
                    "autouv": 0, "children": []}
            nodes[b.name] = node
            for ci, c in enumerate(b.cubes):
                (ox, oy, oz), (sx, sy, sz) = c.origin, c.size
                cr = c.rotation or (0, 0, 0)
                cp = c.pivot or c.origin
                faces = {}
                for face in FACES:
                    rct = self.uv.get((bi, ci, face))
                    if not rct:
                        faces[face] = {"uv": [0, 0, 0, 0], "texture": None}
                    elif face in ("up", "down"):          # Blockbench flips these on Bedrock export
                        faces[face] = {"uv": [rct[0] + rct[2], rct[1] + rct[3], rct[0], rct[1]], "texture": 0}
                    else:
                        faces[face] = {"uv": [rct[0], rct[1], rct[0] + rct[2], rct[1] + rct[3]], "texture": 0}
                el = {"name": c.tag or b.name, "box_uv": False, "rescale": False, "locked": False,
                      "render_order": "default", "allow_mirror_modeling": True,
                      "from": [_r(-(ox + sx)), _r(oy), _r(oz)], "to": [_r(-ox), _r(oy + sy), _r(oz + sz)],
                      "autouv": 0, "color": bi % 8, "inflate": _r(c.inflate),
                      "origin": [_r(-cp[0]), _r(cp[1]), _r(cp[2])],
                      "rotation": [_r(-cr[0]), _r(-cr[1]), _r(cr[2])],
                      "faces": faces, "type": "cube", "uuid": uid("cube", b.name, ci)}
                elements.append(el)
                node["children"].append(el["uuid"])
            for lname, lp in b.locators.items():
                el = {"name": lname, "locked": False, "position": [_r(-lp[0]), _r(lp[1]), _r(lp[2])],
                      "rotation": [0, 0, 0], "ignore_inherited_scale": False, "type": "locator",
                      "uuid": uid("locator", lname)}
                elements.append(el)
                node["children"].append(el["uuid"])
        outliner = []
        for b in self.bones:
            (nodes[b.parent]["children"] if b.parent else outliner).append(nodes[b.name])
        buf = io.BytesIO()
        self.texture.save(buf, "PNG")
        tex = {"path": "", "name": f"{name}.png", "folder": "", "namespace": "", "id": "0", "group": "",
               "width": W, "height": H, "uv_width": W, "uv_height": H, "particle": False,
               "use_as_default": False, "layers_enabled": False, "sync_to_project": "",
               "render_mode": "default", "render_sides": "auto", "frame_time": 1,
               "frame_order_type": "loop", "frame_order": "", "frame_interpolate": False,
               "visibility": True, "internal": True, "saved": False, "uuid": uid("texture"),
               "source": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}
        bw, bh, oy = self.bounds
        return {"meta": {"format_version": "4.10", "model_format": "bedrock", "box_uv": False},
                "name": name, "model_identifier": self.identifier.replace("geometry.", ""),
                "visible_box": [bw, bh, oy], "variable_placeholders": "", "variable_placeholder_buttons": [],
                "timeline_setups": [], "unhandled_root_fields": {},
                "resolution": {"width": W, "height": H},
                "elements": elements, "outliner": outliner, "textures": [tex]}

    def stats(self) -> dict:
        return {"bones": len(self.bones), "cubes": sum(len(b.cubes) for b in self.bones),
                "faces": len(self.uv), "texture": self.tex_size,
                "locators": sum(len(b.locators) for b in self.bones)}


def _r(v: float) -> float:
    v = round(float(v), 4)
    return int(v) if v == int(v) else v
