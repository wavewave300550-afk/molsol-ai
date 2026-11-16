"""
Bedrock geometry + animation evaluation (offline emulation used for previews and checks).

Conventions (verified against Blockbench's Bedrock codec, which the game matches):

* Geometry/animation files use a mirrored X axis.  We convert to a right-handed
  "display" space: x_disp = -x_file, cube origin_x -> -(origin_x + size_x),
  rotations (rx, ry, rz) -> (-rx, -ry, rz), animation positions (px, py, pz) -> (-px, py, pz).
* Euler order is ZYX: M = Rz * Ry * Rx.
* Animation rotations are *added* to the bone's rest Euler angles, positions are
  added, scales multiply.  "override_previous_animation" resets the bone to its
  rest pose before applying the animation (for the bones it animates).
* An attachable bone with a "binding" is parented to the holder bone named by the
  binding; its model-space origin sits at holder_bone_pivot + (0, -24, 0).
* Bone names are case-insensitive.
* Cube faces: Bedrock 'east' is the min-x face in file space (= +x in display
  space), 'west' the max-x face.  Up/down per-face UVs are stored flipped
  (uv + uv_size, negative size), which is how Blockbench exports them.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import molang

Vec3 = Tuple[float, float, float]


def strip_comments(text: str) -> str:
    return re.sub(r"(?<![:\"])//[^\n]*", "", text)


# ----------------------------------------------------------------------------- matrices

def rot_x(d):
    a = math.radians(d)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], dtype=float)


def rot_y(d):
    a = math.radians(d)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=float)


def rot_z(d):
    a = math.radians(d)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)


def trans(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def scale_m(v):
    m = np.eye(4)
    m[0, 0], m[1, 1], m[2, 2] = v
    return m


def euler_file_to_matrix(r: Vec3) -> np.ndarray:
    """Bedrock-file Euler (deg) -> display-space rotation matrix."""
    return rot_z(r[2]) @ rot_y(-r[1]) @ rot_x(-r[0])


def disp(p: Vec3) -> np.ndarray:
    return np.array([-p[0], p[1], p[2]], dtype=float)


# ----------------------------------------------------------------------------- geometry

@dataclass
class Cube:
    origin: Vec3
    size: Vec3
    inflate: float = 0.0
    pivot: Optional[Vec3] = None
    rotation: Optional[Vec3] = None
    uv: object = None          # [u, v] box uv  or  {face: {"uv": [..], "uv_size": [..]}}
    mirror: bool = False


@dataclass
class Bone:
    name: str
    pivot: Vec3
    parent: Optional[str] = None
    rotation: Vec3 = (0.0, 0.0, 0.0)
    binding: Optional[str] = None
    cubes: List[Cube] = field(default_factory=list)
    never_render: bool = False
    mirror: bool = False


@dataclass
class Geo:
    identifier: str
    tex_w: int
    tex_h: int
    bones: Dict[str, Bone]       # key: lower-case name
    order: List[str]

    def bone(self, name: str) -> Bone:
        return self.bones[name.lower()]


def load_geometries(doc: dict) -> Dict[str, Geo]:
    out = {}
    entries = doc.get("minecraft:geometry")
    if entries is None:  # legacy format
        entries = []
        for k, v in doc.items():
            if k.startswith("geometry."):
                e = dict(v)
                e["description"] = {"identifier": k.split(":")[0], "texture_width": v.get("texturewidth", 64),
                                    "texture_height": v.get("textureheight", 64)}
                entries.append(e)
    for g in entries:
        d = g["description"]
        bones: Dict[str, Bone] = {}
        order = []
        for b in g.get("bones", []):
            cubes = []
            for c in b.get("cubes", []) or []:
                cubes.append(Cube(tuple(c["origin"]), tuple(c["size"]), c.get("inflate", b.get("inflate", 0.0)) or 0.0,
                                  tuple(c["pivot"]) if "pivot" in c else None,
                                  tuple(c["rotation"]) if "rotation" in c else None,
                                  c.get("uv"), c.get("mirror", b.get("mirror", False))))
            bn = Bone(b["name"], tuple(b.get("pivot", (0, 0, 0))), b.get("parent"),
                      tuple(b.get("rotation", (0, 0, 0))), b.get("binding"), cubes,
                      b.get("neverRender", False), b.get("mirror", False))
            bones[b["name"].lower()] = bn
            order.append(b["name"].lower())
        out[d["identifier"]] = Geo(d["identifier"], d.get("texture_width", 64), d.get("texture_height", 64), bones, order)
    return out


# ----------------------------------------------------------------------------- animation

@dataclass
class BonePose:
    rot: np.ndarray = field(default_factory=lambda: np.zeros(3))
    pos: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))


def _vec(v, ctx: molang.Context, this=(0.0, 0.0, 0.0)):
    if isinstance(v, (int, float, str)):
        x = molang.evaluate(v, ctx, this[0])
        return np.array([x, x, x], dtype=float)
    return np.array([molang.evaluate(v[i], ctx, this[i]) for i in range(3)], dtype=float)


def _keyframes(chan, ctx, t, this):
    """Evaluate a keyframed channel at time t (linear / catmullrom)."""
    keys = []
    for k, v in chan.items():
        tt = float(k)
        if isinstance(v, dict):
            pre = v.get("pre", v.get("post"))
            post = v.get("post", v.get("pre"))
            mode = v.get("lerp_mode", "linear")
        else:
            pre = post = v
            mode = "linear"
        keys.append((tt, pre, post, mode))
    keys.sort(key=lambda k: k[0])
    if t <= keys[0][0]:
        return _vec(keys[0][1], ctx, this)
    if t >= keys[-1][0]:
        return _vec(keys[-1][2], ctx, this)
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a[0] <= t <= b[0]:
            f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            va, vb = _vec(a[2], ctx, this), _vec(b[1], ctx, this)
            if a[3] == "catmullrom" or b[3] == "catmullrom":
                p0 = _vec(keys[i - 1][2], ctx, this) if i > 0 else va
                p3 = _vec(keys[i + 2][1], ctx, this) if i + 2 < len(keys) else vb
                f2, f3 = f * f, f * f * f
                return 0.5 * ((2 * va) + (-p0 + vb) * f + (2 * p0 - 5 * va + 4 * vb - p3) * f2 + (-p0 + 3 * va - 3 * vb + p3) * f3)
            return va + (vb - va) * f
    return _vec(keys[-1][2], ctx, this)


def eval_channel(chan, ctx, t, this):
    if isinstance(chan, dict) and not ("pre" in chan or "post" in chan):
        return _keyframes(chan, ctx, t, this)
    if isinstance(chan, dict):
        return _vec(chan.get("post", chan.get("pre")), ctx, this)
    return _vec(chan, ctx, this)


def apply_animation(anim: dict, pose: Dict[str, BonePose], rest: Dict[str, BonePose], ctx: molang.Context,
                    anim_time: float, weight: float = 1.0):
    """Apply one animation (bones section) on top of `pose` (in-place)."""
    override = bool(anim.get("override_previous_animation", False))
    length = anim.get("animation_length")
    t = anim_time
    loop = anim.get("loop", False)
    if length and loop is True:
        t = math.fmod(anim_time, length) if length > 0 else 0
    ctx.queries["anim_time"] = t
    for bname, ch in (anim.get("bones") or {}).items():
        key = bname.lower()
        bp = pose.setdefault(key, BonePose())
        if override:
            r = rest.get(key, BonePose())
            bp.rot, bp.pos, bp.scale = r.rot.copy(), r.pos.copy(), r.scale.copy()
        if "rotation" in ch:
            bp.rot = bp.rot + weight * eval_channel(ch["rotation"], ctx, t, tuple(bp.rot))
        if "position" in ch:
            bp.pos = bp.pos + weight * eval_channel(ch["position"], ctx, t, tuple(bp.pos))
        if "scale" in ch:
            s = eval_channel(ch["scale"], ctx, t, tuple(bp.scale))
            bp.scale = bp.scale * (1 + (s - 1) * weight)


def rest_pose(geo: Geo) -> Dict[str, BonePose]:
    return {k: BonePose(np.array(b.rotation, dtype=float), np.zeros(3), np.ones(3)) for k, b in geo.bones.items()}


def world_matrices(geo: Geo, pose: Dict[str, BonePose], holder: Optional[Tuple[Geo, Dict[str, np.ndarray]]] = None,
                   root: np.ndarray = None) -> Dict[str, np.ndarray]:
    """Display-space world matrix of every bone.  `holder` = (holder geo, holder matrices) for bindings."""
    root = np.eye(4) if root is None else root
    out: Dict[str, np.ndarray] = {}

    def local(name):
        b = geo.bones[name]
        bp = pose.get(name) or BonePose(np.array(b.rotation, dtype=float))
        piv = disp(b.pivot)
        p = np.array([-bp.pos[0], bp.pos[1], bp.pos[2]])
        return trans(piv + p) @ euler_file_to_matrix(tuple(bp.rot)) @ scale_m(bp.scale) @ trans(-piv)

    def solve(name, depth=0):
        if name in out:
            return out[name]
        if depth > 64:
            raise RuntimeError("bone cycle in " + geo.identifier)
        b = geo.bones[name]
        parent_m = root
        if b.binding and holder is not None:
            target = _binding_target(b.binding)
            hgeo, hmats = holder
            hb = hgeo.bones.get(target)
            if hb is not None:
                parent_m = hmats[target] @ trans(disp(hb.pivot) + np.array([0, -24.0, 0]))
        elif b.parent:
            pk = b.parent.lower()
            if pk in geo.bones:
                parent_m = solve(pk, depth + 1)
            elif holder is not None and pk in holder[0].bones:
                parent_m = holder[1][pk]
        out[name] = parent_m @ local(name)
        return out[name]

    for n in geo.order:
        solve(n)
    return out


def _binding_target(expr: str) -> str:
    # we only ever bind to the item slot of the main hand
    if "item_slot_to_bone_name" in expr:
        return "rightitem"
    return expr.strip("'\" ").lower()
