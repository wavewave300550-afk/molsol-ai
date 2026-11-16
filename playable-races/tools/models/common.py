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

from kit.geo import Model, rot_matrix
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


# ----------------------------------------------------------------------------- premium shapes (v1.5)
#
# Helpers for the Marketplace-style bodies of races 007-009: smooth curves instead of stepped
# stacks, fans of individual feathers, overlapping plates, rays.  All sizes snap to whole texels
# (q) so textures never stretch; overlapping boxes are staggered so no two faces are coplanar.

def euler_for(basis) -> tuple:
    """Bedrock cube/bone rotation [rx, ry, rz] whose matrix (kit.geo.rot_matrix) maps the
    local X, Y, Z axes onto the columns of `basis` (an orthonormal 3x3)."""
    M = np.asarray(basis, float)
    ay = math.asin(max(-1.0, min(1.0, -M[2, 0])))
    if abs(math.cos(ay)) > 1e-6:
        ax = math.atan2(M[2, 1], M[2, 2])
        az = math.atan2(M[1, 0], M[0, 0])
    else:  # gimbal lock: put everything in ax
        ax = math.atan2(-M[1, 2], M[1, 1])
        az = 0.0
    return (-math.degrees(ax), math.degrees(ay), -math.degrees(az))


def frame_rot(along, normal) -> tuple:
    """Rotation that points a box's local +Z along `along` and its local +Y along `normal`
    (made orthogonal to `along`); local +X is their cross product."""
    z = np.asarray(along, float)
    z = z / max(np.linalg.norm(z), 1e-9)
    y = np.asarray(normal, float)
    y = y - z * float(y @ z)
    if np.linalg.norm(y) < 1e-6:
        y = np.array([0.0, 1.0, 0.0]) if abs(z[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
        y = y - z * float(y @ z)
    y = y / np.linalg.norm(y)
    x = np.cross(y, z)
    return euler_for(np.column_stack([x, y, z]))


def spline(pts, n: int = 3):
    """Catmull-Rom curve through `pts`: n samples per span, both ends included."""
    P = [np.asarray(p, float) for p in pts]
    if len(P) < 3 or n <= 1:
        return P
    ext = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def taper(w0: float, w1: float, n: int, power: float = 1.0, step: float = 0.5):
    """n sizes easing from w0 to w1 (power > 1 keeps the base thick longer), snapped to texels."""
    return [q(w0 + (w1 - w0) * ((k / max(n - 1, 1)) ** power), step) for k in range(n)]


def sweep(m: Model, parent: str, prefix: str, pts, w0: float, w1: float, mat: str, h0: float = None,
          h1: float = None, n: int = 3, per_bone: int = 1, bones: bool = True, power: float = 1.0,
          normal=None, mats=None, **kw):
    """A smooth tapered form along a Catmull-Rom curve through `pts` (tails, necks, horns,
    crests, tendrils).  Width (local X) eases w0 -> w1, height (local Y) h0 -> h1.
    bones=True: a new bone every `per_bone` spans (pivot at the span start, chained), so the
    form can bend joint by joint; bones=False: every span is a cube of `parent` (rigid).
    normal: orient the cross-section (local +Y) toward this vector (flat crests, blades);
    default lets the box keep its natural roll.  Returns bone names (bones=True) or cubes."""
    P = spline(pts, n)
    k = len(P) - 1
    ws = taper(w0, w1, k, power)
    hs = taper(h0 if h0 is not None else w0, h1 if h1 is not None else w1, k, power)
    names, cubes = [], []
    par = parent
    for i in range(k):
        if bones and i % per_bone == 0:
            name = f"{prefix}{i // per_bone}"
            m.bone(name, par, tuple(P[i]))
            names.append(name)
            par = name
        mt = mats[i] if mats else mat
        if normal is None:
            cubes.append(segment(m, par if bones else parent, P[i], P[i + 1], ws[i], hs[i], mt, **kw))
        else:
            a, b = P[i], P[i + 1]
            ln = q(float(np.linalg.norm(b - a)) + 0.25)
            cubes.append(m.cube(par if bones else parent, (a[0] - ws[i] / 2, a[1] - hs[i] / 2, a[2]),
                                (ws[i], hs[i], ln), mt, pivot=tuple(a), rot=frame_rot(b - a, normal), **kw))
    return names if bones else cubes


def lathe(m: Model, bone: str, center, profile, mat: str, sides: int = 12, skew=(0.0, 0.0), squash=(1.0, 1.0),
          step: float = 0.5, **kw):
    """A smooth solid of revolution around the vertical axis through `center` (domes, caps,
    bulbs, bells, stalks).  profile = [(height, radius), ...] from the bottom up; each band
    between two profile points is a regular polygon prism (8, 12 or 16 sides) built from
    sides/2 crossing strips (edge length x 2 x apothem, rotated 360/sides apart), so the
    outline has flat edges and no star points.  Overlapping strips are staggered by 0.02 so
    their top and bottom faces never coincide (no z-fighting).  squash=(sx, sz) makes it
    elliptical; skew=(dx, dz) shifts each band in proportion to its height (lopsided caps).
    Light it as one surface: soft_shade(ctx, pal, ellipsoid=lathe_proxy(...), up=0, down=0).
    Returns the cubes."""
    if sides not in (8, 12, 16):
        raise ValueError("sides must be 8, 12 or 16")
    cx, cy, cz = center
    y_lo, y_hi = profile[0][0], profile[-1][0]
    H = (y_hi - y_lo) or 1.0
    out = []
    for i in range(len(profile) - 1):
        (y0, r0), (y1, r1) = profile[i], profile[i + 1]
        r = (r0 + r1) / 2
        h = q(y1 - y0, step / 2)
        apo = r * math.cos(math.pi / sides)
        edge = 2 * r * math.sin(math.pi / sides)
        f = ((y0 + y1) / 2 - y_lo) / H
        bx, bz = cx + skew[0] * f, cz + skew[1] * f
        for k in range(sides // 2):
            ang = 360.0 / sides * k
            # strip: `edge` across, 2*apothem along its axis; squash scales the axis lengths
            a_r = math.radians(ang)
            sq = math.hypot(squash[0] * math.sin(a_r), squash[1] * math.cos(a_r))
            sx, sz = q(edge * sq + 0.25, step / 2), q(2 * apo * sq, step / 2)
            e = 0.02 * k
            out.append(m.cube(bone, (bx - sx / 2, cy + y0 - e, bz - sz / 2), (sx, h + 2 * e, sz), mat,
                              pivot=(bx, cy + y0, bz), rot=(0.0, ang, 0.0) if ang else None, **kw))
    return out


def lathe_proxy(center, profile, squash=(1.0, 1.0)):
    """(center, radii) of the ellipsoid that best matches a lathe() outline - pass it to
    kit.pixel.proxy / soft_shade so the bands are lit as one smooth surface."""
    cx, cy, cz = center
    y_lo, y_hi = profile[0][0], profile[-1][0]
    rmax = max(r for _, r in profile)
    ry = max(y_hi - y_lo, 1e-3)
    return (cx, cy + y_lo, cz), (rmax * squash[0], ry, rmax * squash[1])


def _dir_in_plane(angle_deg: float, plane: str):
    a = math.radians(angle_deg)
    if plane in ("back", "front"):      # fan facing backward/forward: XY plane, 0 = up, + = creature's left (+X)
        return np.array([math.sin(a), math.cos(a), 0.0]), np.array([0.0, 0.0, 1.0 if plane == "back" else -1.0])
    if plane == "side":                 # YZ plane (wing panels): 0 = up, + = backward (+Z)
        return np.array([0.0, math.cos(a), math.sin(a)]), np.array([1.0, 0.0, 0.0])
    if plane == "flat":                 # XZ plane (horizontal fans, gill rays): 0 = back (+Z), + = left (+X)
        return np.array([math.sin(a), 0.0, math.cos(a)]), np.array([0.0, 1.0, 0.0])
    raise ValueError(plane)


def feather_fan(m: Model, parent: str, prefix: str, origin, n: int, length, width, mat: str, spread: float = 120.0,
                center: float = 0.0, plane: str = "back", thick: float = 0.25, bones: bool = True, mats=None,
                lift: float = 0.0, **kw):
    """n feathers (thin vanes) radiating from `origin` over `spread` degrees around the
    direction `center` in `plane` ("back" / "front": XY plane, 0 = up, + toward +X;
    "side": YZ plane, + = backward; "flat": XZ plane, 0 = backward).  length / width may be
    lists (one per feather).  Each vane: width across, length along its direction, `thick`
    through the plane; `lift` tilts the vanes out of the plane (degrees) for a cupped fan.
    bones=True: one bone per feather with its pivot at the origin (animate the bones to open
    and close the fan).  Paint vanes with kit.pixel.vane() for the feather shape.
    Returns the bone names (or cubes)."""
    o = np.asarray(origin, float)
    out = []
    for k in range(n):
        f = 0.5 if n == 1 else k / (n - 1)
        ang = center - spread / 2 + spread * f
        d, nrm = _dir_in_plane(ang, plane)
        if lift:
            d = d * math.cos(math.radians(lift)) + nrm * math.sin(math.radians(lift))
        L = length[k] if isinstance(length, (list, tuple)) else length
        W = width[k] if isinstance(width, (list, tuple)) else width
        mt = mats[k] if mats else mat
        rot = frame_rot(d, nrm)
        tgt = parent
        if bones:
            tgt = f"{prefix}{k}"
            m.bone(tgt, parent, tuple(o))
            out.append(tgt)
        c = m.cube(tgt, (o[0] - q(W) / 2, o[1] - thick / 2, o[2]), (q(W), thick, q(L)), mt, pivot=tuple(o), rot=rot, **kw)
        if not bones:
            out.append(c)
    return out


def rays(m: Model, bone: str, center, n: int, r0: float, r1: float, width: float, mat: str, plane: str = "front",
         thick: float = 0.25, phase: float = 0.0, lengths=None, **kw):
    """A full circle of n rays (a corona, gill fins, a crown of petals) around `center` in
    `plane`, each from radius r0 out to r1 (lengths may override r1 per ray).  Returns cubes."""
    c = np.asarray(center, float)
    out = []
    for k in range(n):
        ang = phase + 360.0 * k / n
        d, nrm = _dir_in_plane(ang, plane)
        R1 = r0 + (lengths[k] if lengths is not None else (r1 - r0))
        a = c + d * r0
        out.append(m.cube(bone, (a[0] - q(width) / 2, a[1] - thick / 2, a[2]), (q(width), thick, q(R1 - r0)), mat,
                          pivot=tuple(a), rot=frame_rot(d, nrm), **kw))
    return out


def plate_row(m: Model, bone: str, start, end, n: int, w0: float, w1: float, length: float, thick: float, mat: str,
              normal=(0.0, 1.0, 0.0), overlap: float = 0.35, tilt: float = 10.0, arch: float = 0.0, mats=None, **kw):
    """n overlapping armour plates (isopod tergites, scutes, osteoderms, scales) laid from
    `start` to `end` on a surface facing `normal`: plate k is w (across, easing w0 -> w1) by
    length*(1+overlap) (along the row) by thick (through the surface), its trailing edge lifted
    by `tilt` degrees so it laps over the next; `arch` bows the row outward at the middle.
    Each plate sits `0.02*k` higher than the previous one (no coplanar overlaps).  Returns cubes."""
    a, b = np.asarray(start, float), np.asarray(end, float)
    nrm = np.asarray(normal, float)
    nrm = nrm / max(np.linalg.norm(nrm), 1e-9)
    d = b - a
    L = float(np.linalg.norm(d))
    d = d / max(L, 1e-9)
    out = []
    for k in range(n):
        f = 0.5 if n == 1 else k / (n - 1)
        p = a + (b - a) * f + nrm * (arch * 4 * f * (1 - f) + 0.02 * k)
        w = q(w0 + (w1 - w0) * f)
        ln = q(length * (1 + overlap))
        # tilt: rotate the plate's along-axis toward the normal (trailing edge up)
        t = math.radians(tilt)
        along = d * math.cos(t) - nrm * math.sin(t)
        rot = frame_rot(along, nrm)
        mt = mats[k] if mats else mat
        out.append(m.cube(bone, (p[0] - w / 2, p[1] - thick / 2, p[2] - ln / 2), (w, thick, ln), mt,
                          pivot=tuple(p), rot=rot, **kw))
    return out
