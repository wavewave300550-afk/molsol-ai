"""
gait - IK-baked quadruped motion for the Red Dragon.

A leg is driven by a target for its ball-of-foot point (toes pivot) and a foot pitch; the joint
angles (shoulder/hip x+z, elbow/knee, ankle, wrist) are solved with damped least squares on the
real rig, warm-started frame to frame, so feet stay exactly where they are planted while the body
bobs, rolls and twists above them.  Toes counter-rotate to stay flat while the heel lifts.

Foot paths are in model (entity) space: a planted foot slides backwards at exactly the travel
speed of the cycle, i.e. it stands still on the ground once anim_time_update ties playback speed
to q.ground_speed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from anim_kit import ONE, ZERO, Clip, Rig, lm_solve, pose_entry, smooth, smoother, spring_chain, v


@dataclass
class Leg:
    name: str              # fl, fr, hl, hr
    parent: str            # chest / pelvis
    joints: List[Tuple[str, int]]  # (bone, axis) variables
    foot: str
    toes: str
    ball: np.ndarray       # model-space rest position of the toes pivot (ball of foot)
    pref_w: np.ndarray = field(default=None)


def make_legs(rig: Rig) -> Dict[str, Leg]:
    legs = {}
    for side in ("l", "r"):
        legs[f"f{side}"] = Leg(f"f{side}", "chest",
                               [(f"leg_f{side}_upper", 0), (f"leg_f{side}_upper", 2), (f"leg_f{side}_lower", 0),
                                (f"foot_f{side}", 0)],
                               f"foot_f{side}", f"toes_f{side}", rig.pivot[f"toes_f{side}"].copy(),
                               v(0.02, 0.05, 0.02, 0.03))
        legs[f"h{side}"] = Leg(f"h{side}", "pelvis",
                               [(f"leg_h{side}_thigh", 0), (f"leg_h{side}_thigh", 2), (f"leg_h{side}_shin", 0),
                                (f"leg_h{side}_meta", 0), (f"foot_h{side}", 0)],
                               f"foot_h{side}", f"toes_h{side}", rig.pivot[f"toes_h{side}"].copy(),
                               v(0.02, 0.05, 0.06, 0.06, 0.03))
    return legs


class LegSolver:
    def __init__(self, rig: Rig):
        self.rig = rig
        self.legs = make_legs(rig)
        rest = rig.world({})
        self.rest_pitch = {k: rig.pitch_of(rest, l.foot) for k, l in self.legs.items()}
        self.ball_rest = {k: rig.point(rest, l.foot, l.ball) for k, l in self.legs.items()}
        self.warm: Dict[str, np.ndarray] = {}

    def chain(self, leg: Leg, Mpar, pose, x):
        """World matrices of the leg chain for joint deltas x on top of `pose`."""
        rig = self.rig
        local_pose = {}
        for (bone, axis), val in zip(leg.joints, x):
            e = local_pose.setdefault(bone, {"rotation": ZERO.copy(), "position": ZERO.copy(), "scale": ONE.copy()})
            e["rotation"][axis] += val
        mats = {}
        M = Mpar
        seen = []
        for bone, _ in leg.joints:
            if bone in seen:
                continue
            seen.append(bone)
            p = pose.get(bone)
            q = local_pose.get(bone)
            merged = None
            if p or q:
                merged = {"rotation": (p["rotation"] if p else ZERO) + (q["rotation"] if q else ZERO),
                          "position": p["position"] if p else ZERO, "scale": p["scale"] if p else ONE}
            M = M @ rig.local(bone, {bone: merged} if merged else {})
            mats[bone] = M
        return mats

    def solve(self, key, Mpar, pose, ball_target, pitch_delta, w_pitch=0.35):
        leg = self.legs[key]
        x0 = self.warm.get(key, np.zeros(len(leg.joints)))
        target_pitch = self.rest_pitch[key] + pitch_delta

        def residual(x):
            mats = self.chain(leg, Mpar, pose, x)
            Mf = mats[leg.foot]
            ball = (Mf @ np.append(leg.ball, 1.0))[:3]
            f = Mf[:3, :3] @ v(0, 0, -1)
            f /= np.linalg.norm(f)
            pitch = math.degrees(math.asin(-max(-1, min(1, f[1]))))
            return np.concatenate([(ball - ball_target), [(pitch - target_pitch) * w_pitch], leg.pref_w * x])

        x, cost = lm_solve(x0, residual, iters=12)
        self.warm[key] = x
        return x, cost


# ----------------------------------------------------------------------------- foot paths

@dataclass
class Gait:
    stride: float          # blocks travelled per cycle
    duty: float            # fraction of the cycle a foot is planted
    offsets: Dict[str, float]
    lift: float            # swing height (units)
    heel: float = 24.0     # heel lift before toe-off (deg)
    toe_curl: float = 28.0
    reach: float = 10.0    # toes-up angle just before contact (deg)


def foot_path(g: Gait, phase: float, leg: str, direction: float = 1.0):
    """(dz units, lift units, foot pitch delta deg, toe delta deg, planted) for one leg.
    direction -1 walks backwards."""
    p = (phase - g.offsets[leg]) % 1.0
    L = g.duty * g.stride * 16.0  # distance the body travels while this foot is planted
    if p < g.duty:
        u = p / g.duty
        dz = (-0.5 + u) * L
        heel = g.heel * smooth((u - 0.72) / 0.28)
        return dz * direction, 0.0, heel, -heel, True
    u = (p - g.duty) / (1.0 - g.duty)
    dz = (0.5 - smoother(u)) * L
    lift = g.lift * math.sin(math.pi * u) ** 0.85
    # pitch: heel-up after toe-off, then toes reach up just before the strike
    pitch = g.heel * (1 - smooth(u / 0.45)) - g.reach * smooth((u - 0.55) / 0.35) * (1 - smooth((u - 0.92) / 0.08))
    # toes: keep compensating the heel at toe-off, curl only as the foot gains height, open before contact
    toe = -g.heel * (1 - smooth(u / 0.3)) + g.toe_curl * (lift / g.lift) ** 1.5 - 6 * smooth((u - 0.7) / 0.3) * (1 - smooth((u - 0.95) / 0.05))
    return dz * direction, lift, pitch, toe, False


# ----------------------------------------------------------------------------- baking helpers

def apply_rotation(pose, bone, rot):
    pose_entry(pose, bone)["rotation"] = pose_entry(pose, bone)["rotation"] + np.asarray(rot, float)


def apply_position(pose, bone, pos):
    pose_entry(pose, bone)["position"] = pose_entry(pose, bone)["position"] + np.asarray(pos, float)


def stabilise_head(rig: Rig, pose, ref_mats, follow=0.3, keep_yaw=True, w_pos=0.08):
    """Neck/head corrections so the head keeps its reference orientation (eyes level) and only
    follows a fraction of the body's bob.  Returns {bone: rot delta}."""
    names = [("neck_2", 0), ("neck_3", 0), ("neck_4", 0), ("head", 0), ("neck_2", 1), ("neck_4", 1), ("head", 1)]
    ref_pitch = rig.pitch_of(ref_mats, "head")
    ref_yaw = rig.yaw_of(ref_mats, "head")
    ref_pos = rig.point(ref_mats, "head", rig.pivot["head"])
    body_dy = rig.point(rig.world(pose, upto=["chest"]), "chest", rig.pivot["chest"])[1] - \
        rig.point(ref_mats, "chest", rig.pivot["chest"])[1]

    def build(x):
        p = {b: {k: val.copy() for k, val in e.items()} for b, e in pose.items()}
        for (bone, axis), val in zip(names, x):
            e = pose_entry(p, bone)
            e["rotation"] = e["rotation"].copy()
            e["rotation"][axis] += val
        return p

    def residual(x):
        mats = rig.world(build(x), upto=["head"])
        r = [(rig.pitch_of(mats, "head") - ref_pitch) * 1.0]
        if keep_yaw:
            r.append((rig.yaw_of(mats, "head") - ref_yaw) * 0.8)
        hp = rig.point(mats, "head", rig.pivot["head"])
        r.append((hp[1] - (ref_pos[1] + follow * body_dy)) * w_pos * 10)
        return np.concatenate([r, 0.04 * np.asarray(x)])

    x, _ = lm_solve(np.zeros(len(names)), residual, iters=8)
    out = {}
    for (bone, axis), val in zip(names, x):
        out.setdefault(bone, np.zeros(3))[axis] += val
    return out


def tail_follow(rig: Rig, poses: List[dict], dt: float, loop: bool, k=55.0, c=8.0, g=0.9, h_vert=0.006, gain=1.0,
                limit=7.0):
    """Spring follow-through for tail_1..8 driven by the pelvis' world yaw/pitch and vertical
    acceleration over a sequence of poses. Returns arrays (T, 8, 3) of rotation deltas."""
    T = len(poses)
    yaw = np.zeros(T)
    pitch = np.zeros(T)
    y = np.zeros(T)
    for i, p in enumerate(poses):
        m = rig.world(p, upto=["pelvis"])
        yaw[i] = rig.yaw_of(m, "pelvis")
        pitch[i] = rig.pitch_of(m, "pelvis")
        y[i] = rig.point(m, "pelvis", rig.pivot["pelvis"])[1]
    acc = np.gradient(np.gradient(y) / dt) / dt
    cycles = 4 if loop else 1
    lat = spring_chain(yaw, np.zeros(T), dt, 8, k=k, c=c, g=g, gain=gain, cycles=cycles)
    ver = spring_chain(-pitch, acc, dt, 8, k=k * 1.2, c=c, g=g * 0.8, h=h_vert, gain=gain, cycles=cycles)
    out = np.zeros((T, 8, 3))
    out[:, :, 0] = np.clip(ver, -limit, limit)
    out[:, :, 1] = np.clip(lat, -limit, limit)
    return out


def bake_poses(clip: Clip, rig: Rig, poses: List[dict], bones: Optional[Sequence[str]] = None):
    """Store per-sample pose deltas (relative to rest) as pre-baked channel samples."""
    names = bones or sorted({b for p in poses for b in p})
    for bone in names:
        for kind in ("rotation", "position", "scale"):
            arr = np.array([p.get(bone, {}).get(kind, ONE if kind == "scale" else ZERO) for p in poses], float)
            rest = ONE if kind == "scale" else ZERO
            if np.abs(arr - rest).max() > (0.002 if kind == "scale" else 0.03):
                clip.samples[(bone, kind)] = arr


# ----------------------------------------------------------------------------- ground contact

_CUBE_PTS: Dict[str, np.ndarray] = {}


def bone_points(rig: Rig, bone: str) -> np.ndarray:
    """All cube corners of a bone (model space, rest frame, cube rotations applied)."""
    if bone not in _CUBE_PTS:
        import kinematics as K
        pts = []
        for c in rig.bones[bone].get("cubes", []):
            lo, hi = K.cube_corners(c)
            C = np.eye(4)
            if "rotation" in c:
                piv = np.array(c.get("pivot", (lo + hi) / 2), dtype=float)
                C = K.affine(t=piv) @ K.affine(K.brot(c["rotation"])) @ K.affine(t=-piv)
            for x in (lo[0], hi[0]):
                for y in (lo[1], hi[1]):
                    for z in (lo[2], hi[2]):
                        pts.append((C @ np.array([x, y, z, 1.0]))[:3])
        _CUBE_PTS[bone] = np.array(pts) if pts else np.zeros((0, 3))
    return _CUBE_PTS[bone]


def lowest_of(rig: Rig, mats, bone: str) -> float:
    P = bone_points(rig, bone)
    if not len(P):
        return 1e9
    return float(((np.c_[P, np.ones(len(P))]) @ mats[bone].T)[:, 1].min())


def ground_contact(rig: Rig, pose: dict, toes: Sequence[str], tail: Sequence[str], toe_floor=-0.3, tail_floor=1.0):
    """Keep toes and tail above the ground: toes uncurl; for the tail every joint is lifted (from the
    base outwards) until the next segment's thickness clears the ground, so the tail lies and drags
    along the ground instead of passing through it."""
    for bone in toes:
        for _ in range(20):
            mats = rig.world(pose, upto=[bone])
            if lowest_of(rig, mats, bone) >= toe_floor:
                break
            pose_entry(pose, bone)["rotation"][0] -= 2.0
    tail = list(tail)
    for i, bone in enumerate(tail):
        nxt = tail[i + 1] if i + 1 < len(tail) else None
        for _ in range(45):
            mats = rig.world(pose, upto=[nxt or bone])
            if nxt:
                joint = (mats[nxt] @ np.append(rig.pivot[nxt], 1.0))[1]
                pts = bone_points(rig, nxt)
                radius = rig.pivot[nxt][1] - pts[:, 1].min() if len(pts) else 2.0
                ok = joint - radius * 0.9 >= tail_floor and lowest_of(rig, mats, bone) >= tail_floor - 0.5
            else:
                ok = lowest_of(rig, mats, bone) >= tail_floor
            if ok:
                break
            pose_entry(pose, bone)["rotation"][0] += 1.5
