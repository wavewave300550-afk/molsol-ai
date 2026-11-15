"""Shared pieces for race form models.

Every race form is an attachable whose skeleton copies the player's bone
names (root, waist, body, head, rightArm, leftArm, rightLeg, leftLeg).  Those
bones bind to the wearer's animated skeleton, so the creature inherits every
vanilla pose (walking, sneaking, swimming, riding, sleeping, gliding, bow
draw, shield block ...).  All visible cubes hang off *group* bones beneath
them so the add-on's own animations can add race-specific motion (and hide
parts in first person) without fighting the binding.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx, lerp
from kit import noise as nz

# The player's skeleton (pivots from geometry.humanoid.custom).
BOUND = {
    "root": (None, (0, 0, 0)),
    "waist": ("root", (0, 12, 0)),
    "body": ("waist", (0, 24, 0)),
    "head": ("body", (0, 24, 0)),
    "rightArm": ("body", (-5, 22, 0)),
    "leftArm": ("body", (5, 22, 0)),
    "rightLeg": ("root", (-1.9, 12, 0)),
    "leftLeg": ("root", (1.9, 12, 0)),
}

# group bones hidden in first person
THIRD_PERSON_ONLY = ["head_g", "torso_g", "r_leg_g", "l_leg_g", "tail_g"]
FIRST_PERSON_ONLY = ["r_arm_fp", "l_arm_fp"]


def humanoid(m: Model, head_pivot=(0, 24, 0)) -> None:
    for name, (parent, pivot) in BOUND.items():
        m.bone(name, parent, pivot)
    m.bone("head_g", "head", head_pivot)
    m.bone("torso_g", "body", (0, 24, 0))
    m.bone("tail_g", "body", (0, 12, 2))
    m.bone("r_arm_g", "rightArm", (-5, 22, 0))
    m.bone("l_arm_g", "leftArm", (5, 22, 0))
    m.bone("r_arm_fp", "rightArm", (-5, 22, 0))
    m.bone("l_arm_fp", "leftArm", (5, 22, 0))
    m.bone("r_leg_g", "rightLeg", (-1.9, 12, 0))
    m.bone("l_leg_g", "leftLeg", (1.9, 12, 0))


def side_rot(rot: Sequence[float], side: int):
    """Rotation authored for the creature's RIGHT side (side=-1), mirrored for the left (+1)."""
    rx, ry, rz = rot
    return (rx, ry, rz) if side < 0 else (rx, -ry, -rz)


def fp_sleeves(m: Model, mat: str, width: float = 4.7, inflate: float = 0.0) -> None:
    """First-person-only sleeves that envelop the vanilla first-person arm."""
    for side, bone in ((-1, "r_arm_fp"), (1, "l_arm_fp")):
        cx = 6.0 * side
        m.box(bone, (cx, 17.6, 0), (width, 12.8, width), mat, faces={"north", "south", "east", "west", "down"},
              inflate=inflate)


# ----------------------------------------------------------------------------- colour helpers

def clamp01(a):
    return np.clip(a, 0, 1)


def mix3(c1, c2, t):
    return lerp(np.asarray(c1, float), np.asarray(c2, float), clamp01(t))


def desat(rgb, amount):
    g = rgb.mean(axis=1, keepdims=True)
    return rgb * (1 - amount) + g * amount


def ramp(stops, t):
    """Piecewise-linear colour ramp. stops: [(pos, '#hex'), ...]."""
    t = np.clip(t, 0, 1)
    out = np.zeros((len(t), 3))
    pos = [s[0] for s in stops]
    cols = [hx(s[1]) for s in stops]
    for i in range(len(stops) - 1):
        a, b = pos[i], pos[i + 1]
        m = (t >= a) & (t <= b)
        if m.any():
            k = ((t[m] - a) / max(b - a, 1e-9))[:, None]
            out[m] = cols[i] * (1 - k) + cols[i + 1] * k
    out[t < pos[0]] = cols[0]
    out[t > pos[-1]] = cols[-1]
    return out


def bevel(ctx: Ctx, rgb, amount=0.16, width=0.8):
    e = np.clip(ctx.edge / width, 0, 1)
    return rgb * (1 - amount * (1 - e) ** 1.6)[:, None]


def face_light(ctx: Ctx, rgb, top=0.10, bottom=0.22):
    if ctx.face == "up":
        return rgb * (1 + top)
    if ctx.face == "down":
        return rgb * (1 - bottom)
    k = 1 + top * 0.6 * (0.5 - ctx.t / max(ctx.fh, 1e-6))
    return rgb * k[:, None]


def specks(ctx: Ctx, cell=0.5, density=0.08, seed=0):
    return nz.hash_points(ctx.p, cell, seed) < density


def fk_point(model: Model, bone: str, point, variant=None, pose=None):
    """World position of a model-space point attached to `bone` (forward kinematics)."""
    from kit.render import bone_matrices
    M = bone_matrices(model, variant, pose)[bone]
    p = np.array(list(point) + [1.0])
    return (M @ p)[:3]


def ring_cubes(m: Model, bone: str, center, radius: float, thick: float, axis: str, mat: str,
               segments: int = 8, **kw):
    """Approximate a ring with `segments` rotated bars (rotation about the ring axis)."""
    seg_len = 2 * radius * math.tan(math.pi / segments) + thick * 0.3
    cx, cy, cz = center
    for k in range(segments):
        ang = 360.0 * k / segments
        if axis == "z":      # ring faces forward (lies in the XY plane)
            o = (cx - seg_len / 2, cy + radius - thick / 2, cz - thick / 2)
            size = (seg_len, thick, thick)
            rot = (0, 0, ang)
        elif axis == "y":    # horizontal ring (XZ plane)
            o = (cx - seg_len / 2, cy - thick / 2, cz + radius - thick / 2)
            size = (seg_len, thick, thick)
            rot = (0, ang, 0)
        else:                # axis x: ring in the YZ plane
            o = (cx - thick / 2, cy + radius - thick / 2, cz - seg_len / 2)
            size = (thick, thick, seg_len)
            rot = (ang, 0, 0)
        m.cube(bone, o, size, mat, pivot=center, rot=rot, **kw)


# ----------------------------------------------------------------------------- armour assimilation accents

ARMOR_SLOTS = {"c": "slot.armor.chest", "l": "slot.armor.legs", "f": "slot.armor.feet"}


def accents(m: Model, specs) -> None:
    """specs: [(slot 'c'|'l'|'f', name, parent_bone, center, size), ...]
    Accent plates appear (tinted by armour material) when that armour slot is worn,
    replacing the vanilla armour that would not fit the creature's anatomy."""
    for slot, name, parent, center, size in specs:
        bn = f"acc_{slot}_{name}"
        if bn not in m.bones:
            m.bone(bn, parent, center)
        m.box(bn, center, size, "accent", accent=True)


def mat_accent(ctx: Ctx):
    n = nz.fbm(ctx.p, 1.4, 3, seed=77)
    c = ramp([(0, "#9a9aa4"), (0.6, "#d4d4dc"), (1, "#f4f4f8")], n)
    border = ctx.edge < 0.45
    c = np.where(border[:, None], c * 0.72, c)
    rivet = (np.mod(ctx.s, 2.0) < 0.5) & (ctx.t < 0.6) & (ctx.t > 0.15)
    c = np.where((rivet & (ctx.fh > 1.0))[:, None], np.array([1.0, 1.0, 1.0]), c)
    return bevel(ctx, c, 0.2, 0.4), ctx.ones(), ctx.zeros()


# ----------------------------------------------------------------------------- shape builders (Expansion 01 visual overhaul)

def q(v: float, step: float = 0.5) -> float:
    """Snap a size to whole texels (2 texels per unit) so textures never stretch."""
    return max(step, round(v / step) * step)


def dir_rot(d):
    """Bedrock cube rotation that points a cube's +Z axis along d."""
    d = np.asarray(d, float)
    d = d / max(np.linalg.norm(d), 1e-9)
    rx = math.degrees(math.asin(max(-1.0, min(1.0, d[1]))))
    ry = math.degrees(math.atan2(d[0], d[2]))
    return (rx, ry, 0.0)


def segment(m: Model, bone: str, a, b, w: float, h: float, mat: str, overlap: float = 0.25, **kw):
    """A box of cross-section w x h running from point a to point b (rotated about a)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ln = q(float(np.linalg.norm(b - a)) + overlap)
    return m.cube(bone, (a[0] - w / 2, a[1] - h / 2, a[2]), (w, h, ln), mat, pivot=tuple(a), rot=dir_rot(b - a), **kw)


def chain(m: Model, parent: str, prefix: str, pts, widths, mat, heights=None, mats=None, **kw):
    """A tapered limb / strand / segmented body along a polyline.  Every span is its own
    bone (pivot at its start, parented to the previous span) so animations can bend it
    joint by joint.  Returns the bone names, root first."""
    names = []
    par = parent
    pts = [np.asarray(p, float) for p in pts]
    for k in range(len(pts) - 1):
        name = f"{prefix}{k}"
        m.bone(name, par, tuple(pts[k]))
        w = widths[k] if isinstance(widths, (list, tuple)) else widths
        h = (heights[k] if isinstance(heights, (list, tuple)) else heights) if heights is not None else w
        mt = mats[k] if mats else mat
        segment(m, name, pts[k], pts[k + 1], w, h, mt, **kw)
        names.append(name)
        par = name
    return names


def ellipsoid(m: Model, bone: str, center, dims, mat: str, a: float = 0.64, b: float = 0.86, **kw):
    """A rounded voxel ellipsoid from four overlapping boxes (cross + core): reads as round
    from every side, no coplanar overlaps (no z-fighting)."""
    cx, cy, cz = center
    dx, dy, dz = dims
    out = []
    for s in ((dx, q(dy * a), q(dz * a)), (q(dx * a), dy, q(dz * a)), (q(dx * a), q(dy * a), dz), (q(dx * b), q(dy * b), q(dz * b))):
        out.append(m.box(bone, (cx, cy, cz), s, mat, **kw))
    return out


def voxel_ball(m: Model, bone: str, center, d: float, mat: str, **kw):
    return ellipsoid(m, bone, center, (d, d, d), mat, **kw)


def drape(m: Model, parent: str, prefix: str, n: int, center, radii, top: float, length: float, thick: float,
          mat: str, flare: float = 8.0, arc_deg=(0.0, 360.0), widths=None, lengths=None, **kw):
    """Cloth around a body: n thin panels hanging from an ellipse (radii x, z) at height
    `top`, each tilted outward by `flare` degrees and each its own bone (to sway).
    Angles are measured from the front (-Z) toward the creature's right (-X)."""
    cx, _, cz = center
    rx_, rz_ = radii
    a0, a1 = arc_deg
    full = abs((a1 - a0) % 360.0) < 1e-6
    names = []
    for k in range(n):
        f = (k + 0.5) / n if full else (k / max(n - 1, 1))
        phi = math.radians(a0 + (a1 - a0) * f)
        px, pz = cx - math.sin(phi) * rx_, cz - math.cos(phi) * rz_
        # panel width = arc length between neighbours on the ellipse (+ a little overlap)
        if widths is not None:
            w = widths[k]
        else:
            dphi = math.radians((a1 - a0) / (n if full else max(n - 1, 1)))
            w = q(math.hypot(rx_ * math.cos(phi), rz_ * math.sin(phi)) * dphi + 0.6)
        ln = lengths[k] if lengths is not None else length
        name = f"{prefix}{k}"
        m.bone(name, parent, (px, top, pz), (-flare, math.degrees(phi), 0.0))
        m.cube(name, (px - w / 2, top - ln, pz - thick / 2), (w, ln, thick), mat, **kw)
        names.append(name)
    return names


def arc(m: Model, bone: str, center, radius: float, a0: float, a1: float, segments: int, thick: float,
        depth: float, mat: str, **kw):
    """Part of a ring facing forward (in the XY plane): angles in degrees, 0 = top, clockwise
    seen from the front.  Returns the cubes."""
    cx, cy, cz = center
    span = (a1 - a0) / segments
    seg_len = q(2 * radius * math.tan(math.radians(abs(span)) / 2) + thick * 0.4)
    out = []
    for k in range(segments):
        ang = a0 + span * (k + 0.5)
        o = (cx - seg_len / 2, cy + radius - thick / 2, cz - depth / 2)
        out.append(m.cube(bone, o, (seg_len, thick, depth), mat, pivot=(cx, cy, cz), rot=(0, 0, ang), **kw))
    return out
