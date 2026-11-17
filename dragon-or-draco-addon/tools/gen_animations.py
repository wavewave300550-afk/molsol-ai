#!/usr/bin/env python3
"""
Red Dragon animation set V2  ->  RP animations/red_dragon.animation.json
                                 RP animation_controllers/red_dragon.animation_controllers.json
                                 tools/preview_spec.json (what the motion previews render)

40 distinct animations + death (+ 3 utility layers), authored as continuous motion and baked:

  * Feet are solved with IK on the real rig (tools/gait.py): planted feet never slide, the heel
    rolls off the toes, toes flex in the swing.  Walk/run loops are driven by anim_time_update
    from the real ground speed, so stride length matches travel distance at any speed.
  * Overlapping action: chains (neck, tail, wings) are keyed with staggered timing and strength,
    and the tail gets spring follow-through simulated from the pelvis motion.
  * The head is stabilised against body bob/roll (eyes level) except where a clip moves it.
  * Ease-in/out, overshoot and settle curves are baked into catmull-rom keys (Bedrock has no
    bezier easing), with key reduction checked against Bedrock's catmull-rom formula.

Layers (see controllers): one ABSOLUTE state clip from the move controller (ground clips carry
the folded-wing pose, flight clips the spread pose) + ADDITIVE overlays (living behaviours,
combat, hurt, blink, head tracking, flight banking).
"""
from __future__ import annotations

import json
import math
import os
import sys
from typing import Callable, Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim_kit import (Clip, Keys, ONE, ZERO, Rig, mirror_vec, pose_entry, right_of, smooth, smoother,  # noqa: E402
                      spring_chain, v)
from gait import (Gait, LegSolver, apply_position, apply_rotation, bake_poses, foot_path,  # noqa: E402
                  ground_contact, stabilise_head, tail_follow)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
# entity scale from balance.json: a scaled dragon covers proportionally more/less ground per stride
ENTITY_SCALE = float(json.load(open(os.path.join(ROOT, "balance.json")))["entity"]["scale"])
P = "animation.dod.red_dragon."
TAU = 2 * math.pi

rig = Rig()
S = LegSolver(rig)
CLIPS: Dict[str, Clip] = {}
META: Dict[str, dict] = {}

TAIL = [f"tail_{i}" for i in range(1, 9)]
NECK = ["neck_1", "neck_2", "neck_3", "neck_4", "head"]
LEGS = ("fl", "fr", "hl", "hr")

# folded wing (left side; right is mirrored), relative to the spread rest pose
FOLD = {
    "wing_l_upper": v(-80, -60, 16), "wing_l_fore": v(0, 155, 0), "wing_l_hand": v(0, -152, 0),
    "wing_l_f1": v(0, -12, 0), "wing_l_f2": v(0, 14, 0), "wing_l_f3": v(0, 40, 0), "wing_l_f4": v(0, 62, 0),
}
FOLD_MEM = {"wing_l_mem_a": 0.5, "wing_l_mem_b": 0.06, "wing_l_mem_f1": 0.6, "wing_l_mem_f2": 0.6, "wing_l_mem_f3": 0.6}
FOLD_GROUP = {"wing_l_upper": "upper", "wing_l_fore": "fore", "wing_l_hand": "hand", "wing_l_f1": "hand",
              "wing_l_f2": "hand", "wing_l_f3": "hand", "wing_l_f4": "hand"}
MEM_GROUP = {"wing_l_mem_a": "upper", "wing_l_mem_b": "fore", "wing_l_mem_f1": "hand", "wing_l_mem_f2": "hand",
             "wing_l_mem_f3": "hand"}
# flight carriage
TUCK = {"leg_fl_upper": v(55, 0, 6), "leg_fl_lower": v(-75, 0, 0), "foot_fl": v(40, 0, 0), "toes_fl": v(25, 0, 0),
        "leg_hl_thigh": v(62, 0, 4), "leg_hl_shin": v(-30, 0, 0), "leg_hl_meta": v(30, 0, 0), "foot_hl": v(35, 0, 0),
        "toes_hl": v(20, 0, 0)}
FLY_NECK = {"neck_1": v(30, 0, 0), "neck_2": v(6, 0, 0), "neck_3": v(-6, 0, 0), "neck_4": v(-8, 0, 0), "head": v(-12, 0, 0)}


# ----------------------------------------------------------------------------- helpers

def clip(name, length, loop=False, atu=None, category="", priority=1, desc="", rate=30, kind="absolute",
         preview=None):
    c = Clip(P + name, length, loop, atu, rate=rate)
    CLIPS[name] = c
    META[name] = {"category": category, "priority": priority, "desc": desc, "kind": kind,
                  "preview": preview or {}}
    return c


class Motion:
    """A bag of channel functions applied into a pose dict at time t."""

    def __init__(self):
        self.items: List = []

    def rot(self, bone, keys, mirror=False, ease="inout"):
        self._add(bone, "rotation", keys, mirror)
        return self

    def pos(self, bone, keys, mirror=False):
        self._add(bone, "position", keys, mirror)
        return self

    def scl(self, bone, keys, mirror=False):
        self._add(bone, "scale", keys, mirror)
        return self

    def fn(self, bone, kind, f, mirror=False):
        self.items.append((bone, kind, f))
        if mirror and right_of(bone):
            self.items.append((right_of(bone), kind, (lambda g: (lambda t: mirror_vec(g(t), kind)))(f)))
        return self

    def _add(self, bone, kind, keys, mirror):
        f = keys if callable(keys) else Keys(keys)
        self.fn(bone, kind, f, mirror)

    def cascade(self, bones, keys, delays, gains, kind="rotation", mirror=False):
        """Same key motion down a chain with growing delay and per-bone strength (overlap)."""
        for b, d, g in zip(bones, delays, gains):
            ks = [(k[0] + d, np.asarray(k[1], float) * g) + tuple(k[2:]) for k in keys]
            self._add(b, kind, ks, mirror)
        return self

    def apply(self, pose, t):
        for bone, kind, f in self.items:
            e = pose_entry(pose, bone)
            val = f(t)
            if kind == "scale":
                e["scale"] = e["scale"] * val
            else:
                e[kind] = e[kind] + val


def fold_pose(pose, k_upper, k_fore=None, k_hand=None):
    """Add the folded-wing pose with a fold fraction per wing segment group (1 = folded)."""
    ks = {"upper": k_upper, "fore": k_upper if k_fore is None else k_fore,
          "hand": (k_upper if k_fore is None else k_fore) if k_hand is None else k_hand}
    for b, r in FOLD.items():
        k = ks[FOLD_GROUP[b]]
        apply_rotation(pose, b, r * k)
        apply_rotation(pose, right_of(b), mirror_vec(r * k, "rotation"))
    for b, sf in FOLD_MEM.items():
        k = ks[MEM_GROUP[b]]
        s = 1 + (sf - 1) * k
        for name in (b, right_of(b)):
            e = pose_entry(pose, name)
            e["scale"] = e["scale"] * v(1, 1, s)


def unfold_delta(pose, k_upper, k_fore=None, k_hand=None, side="both"):
    """Additive delta that opens folded wings: fraction 0 = stays folded, 1 = fully spread."""
    ks = {"upper": k_upper, "fore": k_upper if k_fore is None else k_fore,
          "hand": (k_upper if k_fore is None else k_fore) if k_hand is None else k_hand}
    for b, r in FOLD.items():
        k = ks[FOLD_GROUP[b]]
        if side in ("both", "l"):
            apply_rotation(pose, b, -r * k)
        if side in ("both", "r"):
            apply_rotation(pose, right_of(b), mirror_vec(-r * k, "rotation"))
    for b, sf in FOLD_MEM.items():
        k = ks[MEM_GROUP[b]]
        s = (1 + (1 / sf - 1) * k)
        for name, sd in ((b, "l"), (right_of(b), "r")):
            if side in ("both", sd):
                e = pose_entry(pose, name)
                e["scale"] = e["scale"] * v(1, 1, s)


def wing_open(t, a0, a1, c0, c1, amount=1.0, lag=0.08):
    """Fold fractions (upper, fore, hand) for opening then closing folded wings: on the way out the
    shoulder leads and the fingers follow; on the way back the fingers fold first and the shoulder
    last (like a real wing) so the tips never swing down through the ground."""
    ku = amount * window(t, a0, a1, c0 + 2 * lag, c1 + 2 * lag)
    kf = amount * window(t, a0 + lag, a1 + lag, c0 + lag, c1 + lag)
    kh = amount * window(t, a0 + 2 * lag, a1 + 2 * lag, c0, c1)
    return ku, kf, kh


def ramp(t, t0, t1, ease=smooth):
    return ease((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t1)


def window(t, t0, t1, t2, t3):
    """0 before t0, eases to 1 over t0..t1, holds, eases back to 0 over t2..t3."""
    return ramp(t, t0, t1) * (1 - ramp(t, t2, t3))


def build(c: Clip, motion: Optional[Motion] = None, head: Optional[Motion] = None,
          legs: Optional[Callable] = None, base: Optional[Callable] = None, extra: Optional[Callable] = None,
          stabilise=0.3, tail=True, tail_gain=1.0, tail_k=55.0, keep_yaw=True, ground=None):
    """Bake a clip: base(pose,t) -> motion -> intended head motion -> leg IK -> head stabilisation
    -> extra(pose,t) -> tail spring follow-through.  legs(key, t) -> (offset, pitch, toe) | None."""
    ts = c.times()
    dt = ts[1] - ts[0]
    poses = []
    S.warm = {}
    for t in ts:
        pose: dict = {}
        if base:
            base(pose, t)
        if motion:
            motion.apply(pose, t)
        ref: dict = {}
        if head:
            head.apply(ref, t)
            head.apply(pose, t)
        if legs:
            mats = rig.world(pose, upto=["chest", "pelvis"])
            for k, leg in S.legs.items():
                spec = legs(k, t)
                if spec is None:
                    continue
                off, pitch, toe = spec
                x, _ = S.solve(k, mats[leg.parent], pose, S.ball_rest[k] + np.asarray(off, float), pitch)
                for (bone, axis), val in zip(leg.joints, x):
                    pose_entry(pose, bone)["rotation"][axis] += val
                pose_entry(pose, leg.toes)["rotation"][0] += toe
        if stabilise is not None and stabilise is not False:
            corr = stabilise_head(rig, pose, rig.world(ref, upto=["head"]), follow=float(stabilise), keep_yaw=keep_yaw)
            for b, r in corr.items():
                apply_rotation(pose, b, r)
        if extra:
            extra(pose, t)
        poses.append(pose)
    if tail:
        tf = tail_follow(rig, poses, dt, loop=(c.loop is True), k=tail_k, gain=tail_gain)
        if c.loop is not True:
            # one-shot clips: the spring must have settled by the last frame, otherwise the tail tip
            # would snap when the clip blends out (or freeze mid-swing on a held last frame)
            settle = min(0.35, 0.3 * c.length)
            for i, t in enumerate(ts):
                tf[i] *= 1.0 - smoother((t - (c.length - settle)) / settle)
        for i, p in enumerate(poses):
            for j, tb in enumerate(TAIL):
                apply_rotation(p, tb, tf[i, j])
    if ground is None:
        ground = not c.name.startswith(tuple(P + x for x in ("flight_", "landing_approach", "launch")))
    if ground:  # toes and tail never pass through the ground
        over = CLIPS.get("idle_breathe") if META.get(c.name[len(P):], {}).get("kind") == "additive" else None
        for t, p in zip(ts, poses):
            if over is None or c.name.endswith("rest_breathe"):
                ground_contact(rig, p, [f"toes_{k}" for k in LEGS], TAIL)
                continue
            # additive overlay: test it on top of the standing base it plays over, keep only the correction
            comb = over.pose(t % over.length)
            for b, e in p.items():
                ce = pose_entry(comb, b)
                ce["rotation"] = ce["rotation"] + e["rotation"]
                ce["position"] = ce["position"] + e["position"]
                ce["scale"] = ce["scale"] * e["scale"]
            before = {b: comb[b]["rotation"].copy() for b in TAIL + [f"toes_{k}" for k in LEGS] if b in comb}
            ground_contact(rig, comb, [f"toes_{k}" for k in LEGS], TAIL)
            for b in TAIL + [f"toes_{k}" for k in LEGS]:
                if b in comb:
                    apply_rotation(p, b, comb[b]["rotation"] - before.get(b, ZERO))
    bake_poses(c, rig, poses)
    return poses


def planted(k, t):
    return (ZERO, 0.0, 0.0)


def ground_base(pose, t):
    fold_pose(pose, 1.0)


# ============================================================================= B. GROUND LOCOMOTION (P1)

WALK = Gait(stride=3.0, duty=0.66, offsets={"hl": 0.0, "fl": 0.24, "hr": 0.5, "fr": 0.74}, lift=7.0, heel=24, toe_curl=26)
WALK_L = 1.6
WALK_V = WALK.stride / WALK_L  # nominal 1.875 blocks/s
RUN = Gait(stride=2.8, duty=0.42, offsets={"hl": 0.0, "hr": 0.1, "fl": 0.47, "fr": 0.57}, lift=11.0, heel=30,
           toe_curl=34, reach=12)
RUN_L = 0.8
RUN_V = RUN.stride / RUN_L  # nominal 3.5 blocks/s


def walk_body(pose, ph, k=1.0):
    apply_position(pose, "body", v(0.55 * math.sin(TAU * ph - 0.5), -0.55 + 0.65 * math.cos(2 * TAU * (ph - 0.12)), 0) * k)
    apply_rotation(pose, "body", v(0.8 * math.sin(2 * TAU * ph + 1.0), 1.0 * math.sin(TAU * ph - 0.2),
                                   2.1 * math.sin(TAU * ph - 0.45)) * k)
    apply_rotation(pose, "chest", v(0.6 * math.sin(2 * TAU * ph + 0.4), 3.2 * math.sin(TAU * (ph - 0.24) - 0.3), 0) * k)
    apply_rotation(pose, "pelvis", v(0, -3.0 * math.sin(TAU * ph - 0.2), -1.0 * math.sin(TAU * ph - 0.4)) * k)
    for side, s in (("l", 1), ("r", -1)):  # folded wings jostle a little with every footfall
        apply_rotation(pose, f"wing_{side}_upper", v(0, 0, s * 1.3 * math.sin(2 * TAU * ph - 1.1)) * k)


def run_body(pose, ph, k=1.0):
    apply_position(pose, "body", v(0, -1.2 + 2.0 * math.sin(TAU * (ph - 0.12)), -1.0 * math.sin(TAU * ph)) * k)
    apply_rotation(pose, "body", v(4.5 * math.sin(TAU * ph + 0.7), 0.8 * math.sin(TAU * ph), 1.2 * math.sin(TAU * ph - 0.6)) * k)
    apply_rotation(pose, "chest", v(4.0 * math.sin(TAU * ph - 0.9), 1.5 * math.sin(TAU * ph - 1.2), 0) * k)
    apply_rotation(pose, "pelvis", v(-4.0 * math.sin(TAU * ph - 0.9), -1.2 * math.sin(TAU * ph - 0.3), 0) * k)
    for side, s in (("l", 1), ("r", -1)):  # elbows held off the body for balance
        apply_rotation(pose, f"wing_{side}_upper", v(0, 0, s * (-7 + 3.5 * math.sin(TAU * ph - 0.8))) * k)
    for i, tb in enumerate(TAIL[:4]):
        apply_rotation(pose, tb, v((6, 4, 2, 1)[i], 0, 0) * k)  # tail carried higher


def gait_legs(g, L, direction=1.0, scale=1.0):
    def f(k, t):
        dz, lift, pitch, toe, _ = foot_path(g, t / L, k, direction)
        return (v(0, lift, dz) * scale, pitch * scale, toe * scale)
    return f


def footfall_times(g, L):
    return {k: (g.offsets[k] * L) % L for k in LEGS}


WALK_HEAD = Motion().rot("neck_1", [(0, v(4, 0, 0))]).rot("head", [(0, v(-4, 0, 0))]) \
    .fn("neck_4", "rotation", lambda t: v(0.8 * math.sin(2 * TAU * t / WALK_L - 0.5), 0, 0)) \
    .fn("jaw", "rotation", lambda t: v(0.6 + 0.6 * math.sin(2 * TAU * t / WALK_L - 1.4), 0, 0))
RUN_HEAD = Motion().rot("neck_1", [(0, v(14, 0, 0))]).rot("neck_2", [(0, v(4, 0, 0))]).rot("head", [(0, v(-16, 0, 0))]) \
    .fn("jaw", "rotation", lambda t: v(6 + 3 * math.sin(2 * TAU * t / RUN_L), 0, 0))

c = clip("walk_loop", WALK_L, loop=True,
         atu=f"q.anim_time + q.delta_time * math.clamp(v.spd / {WALK_V * ENTITY_SCALE:.4f}, 0.3, 2.5)",
         category="B Ground locomotion", priority=1, desc="4-beat lateral-sequence walk, IK-planted feet, stride synced to ground speed",
         preview={"speed": WALK_V})
build(c, base=lambda p, t: (ground_base(p, t), walk_body(p, t / WALK_L)), head=WALK_HEAD,
      legs=gait_legs(WALK, WALK_L), stabilise=0.35)
for k, tf in footfall_times(WALK, WALK_L).items():
    c.sound(tf, "step")
    if k.startswith("h"):
        c.particle(tf, "dust_puff", f"claw_{k}")

c = clip("run_loop", RUN_L, loop=True,
         atu=f"q.anim_time + q.delta_time * math.clamp(v.spd / {RUN_V * ENTITY_SCALE:.4f}, 0.45, 2.2)",
         category="B Ground locomotion", priority=1, desc="transverse gallop: spine flex, pitch rock, IK feet, speed-synced",
         preview={"speed": RUN_V})
build(c, base=lambda p, t: (ground_base(p, t), run_body(p, t / RUN_L)), head=RUN_HEAD,
      legs=gait_legs(RUN, RUN_L), stabilise=0.25, tail_gain=1.2)
for k, tf in footfall_times(RUN, RUN_L).items():
    c.sound(tf, "step")
    c.particle(tf, "dust_puff", f"claw_{k}")


def walk_start_legs(k, t):
    """From a square stance into walk phase 0: hr stays planted, fr then hl step forward,
    fl lifts off at the end; planted feet slide back with the accelerating body."""
    T = 0.6
    travel = WALK_V * 16 * (t * t / (2 * T))  # units travelled (speed ramps 0 -> WALK_V)
    end = {kk: foot_path(WALK, 0.0, kk) for kk in LEGS}
    if k == "hr":
        return (v(0, 0, travel), 0.0, 0.0)
    if k in ("fr", "hl"):
        t0, t1 = (0.05, 0.42) if k == "fr" else (0.2, 0.6)
        u = ramp(t, t0, t1, smoother)
        start_z = travel if t < t0 else WALK_V * 16 * (t0 * t0 / (2 * T))
        dz = start_z + (end[k][0] - start_z) * u
        lift = WALK.lift * math.sin(math.pi * min(1, max(0, (t - t0) / (t1 - t0)))) ** 0.85
        return (v(0, lift, dz), end[k][2] * u, end[k][3] * u)
    # fl: planted, then lifts into its swing at phase 0
    if t < 0.38:
        return (v(0, 0, travel), 24 * smooth((t - 0.25) / 0.13), -24 * smooth((t - 0.25) / 0.13))
    u = ramp(t, 0.38, 0.6)
    dz0 = WALK_V * 16 * (0.38 ** 2 / (2 * T))
    return (v(0, end["fl"][1] * u, dz0 + (end["fl"][0] - dz0) * u), 24 + (end["fl"][2] - 24) * u,
            -24 + (end["fl"][3] + 24) * u)


c = clip("walk_start", 0.6, category="B Ground locomotion", priority=1,
         desc="weight shifts forward, first steps; ends exactly on walk_loop phase 0", preview={"speed": WALK_V * 0.5})
build(c, base=lambda p, t: (ground_base(p, t), walk_body(p, 0.0, ramp(t, 0.1, 0.6)),
                             apply_rotation(p, "body", v(2.2 * math.sin(math.pi * min(1, t / 0.45)), 0, 0))),
      head=Motion().rot("neck_1", [(0, ZERO), (0.25, v(7, 0, 0)), (0.6, v(4, 0, 0))])
      .rot("head", [(0, ZERO), (0.3, v(-6, 0, 0)), (0.6, v(-4, 0, 0))]),
      legs=walk_start_legs, stabilise=0.35)
c.sound(0.42, "step")
c.sound(0.6, "step")


def walk_stop_legs(k, t):
    T = 0.75
    travel = WALK_V * 16 * (t - t * t / (2 * T)) if t < T else WALK_V * 16 * T / 2
    start = {kk: foot_path(WALK, 0.0, kk) for kk in LEGS}
    if k in ("hl", "fr"):  # planted feet: carried back by the decelerating body, then a settling shuffle
        z = start[k][0] + travel
        if k == "fr":
            u = ramp(t, 0.42, 0.72, smoother)
            return (v(0, 5 * math.sin(math.pi * u), z + (0 - z) * u), 0.0, 0.0)
        u = ramp(t, 0.5, 0.85, smoother)
        return (v(0, 5 * math.sin(math.pi * u), z + (0 - z) * u), 0.0, 0.0)
    if k == "fl":  # finishes its swing and lands in the square stance
        u = ramp(t, 0.0, 0.32, smoother)
        z = start[k][0] + (0 - start[k][0]) * u
        return (v(0, start[k][1] * (1 - u), z), start[k][2] * (1 - u), start[k][3] * (1 - u))
    u = ramp(t, 0.12, 0.5, smoother)  # hr steps forward into the stance
    z0 = start[k][0] + WALK_V * 16 * (0.12 - 0.12 ** 2 / (2 * T))
    return (v(0, 6 * math.sin(math.pi * u), z0 * (1 - u)), 18 * math.sin(math.pi * u) * (1 - u), 0.0)


c = clip("walk_stop", 0.95, loop="hold", category="B Ground locomotion", priority=1,
         desc="decelerates over planted feet, last legs step into a square stance, body rocks back and settles")
build(c, base=lambda p, t: (ground_base(p, t), walk_body(p, 0.0, 1 - ramp(t, 0.0, 0.5)),
                             apply_rotation(p, "body", v(-2.4 * math.sin(math.pi * ramp(t, 0.15, 0.7, smooth)) +
                                                         0.8 * math.sin(math.pi * ramp(t, 0.65, 0.95)), 0, 0)),
                             apply_position(p, "body", v(0, -0.9 * math.sin(math.pi * ramp(t, 0.2, 0.75)), 0))),
      head=Motion().rot("neck_1", [(0, v(4, 0, 0)), (0.35, v(-3, 0, 0), "out"), (0.7, v(1, 0, 0)), (0.95, ZERO)])
      .rot("head", [(0, v(-4, 0, 0)), (0.4, v(4, 0, 0), "out"), (0.75, v(-1, 0, 0)), (0.95, ZERO)]),
      legs=walk_stop_legs, stabilise=0.5, tail_gain=1.3)
c.sound(0.32, "step")
c.sound(0.72, "step")


def run_start_legs(k, t):
    """Crouch on planted feet (anticipation), explode forward into run phase 0."""
    end = {kk: foot_path(RUN, 0.0, kk) for kk in LEGS}
    if t < 0.24:
        return (ZERO, 0.0, 0.0)
    u = ramp(t, 0.24, 0.55, smoother)
    e = end[k]
    lift = (RUN.lift * 0.8 * math.sin(math.pi * u)) if k.startswith("f") else e[1] * u
    return (v(0, lift + e[1] * u * 0.0, e[0] * u), e[2] * u, e[3] * u)


c = clip("run_start", 0.55, category="B Ground locomotion", priority=1,
         desc="anticipation crouch on the haunches, explosive push-off into run_loop phase 0", preview={"speed": RUN_V * 0.4})
build(c, base=lambda p, t: (ground_base(p, t), run_body(p, 0.0, ramp(t, 0.24, 0.55)),
                             apply_position(p, "body", v(0, -4.5 * window(t, 0.0, 0.22, 0.26, 0.4), 2.5 * window(t, 0, 0.22, 0.26, 0.4))),
                             apply_rotation(p, "body", v(-4 * window(t, 0.0, 0.2, 0.26, 0.38) + 5 * window(t, 0.3, 0.4, 0.45, 0.55), 0, 0))),
      head=Motion().rot("neck_1", [(0, ZERO), (0.22, v(-4, 0, 0)), (0.42, v(18, 0, 0), "out"), (0.55, v(14, 0, 0))])
      .rot("neck_2", [(0, ZERO), (0.55, v(4, 0, 0))]).rot("head", [(0, ZERO), (0.25, v(4, 0, 0)), (0.55, v(-16, 0, 0))])
      .rot("jaw", [(0, ZERO), (0.3, v(10, 0, 0)), (0.55, v(6, 0, 0))]),
      legs=run_start_legs, stabilise=0.3, tail_gain=1.4)
c.sound(0.3, "growl")
c.particle(0.3, "dust_puff", "claw_hl")
c.particle(0.3, "dust_puff", "claw_hr")


def run_stop_legs(k, t):
    T = 0.5
    travel = RUN_V * 16 * (t - t * t / (2 * T)) if t < T else RUN_V * 16 * T / 2
    start = {kk: foot_path(RUN, 0.0, kk) for kk in LEGS}
    if k.startswith("f"):  # front legs reach forward and brace
        u = ramp(t, 0.0, 0.22, smoother)
        z_plant = -10.0
        if t < 0.22:
            return (v(0, 6 * math.sin(math.pi * u), start[k][0] + (z_plant - start[k][0]) * u), -10 * math.sin(math.pi * u), 0.0)
        z = z_plant + (travel - RUN_V * 16 * (0.22 - 0.22 ** 2 / (2 * T)))
        w = ramp(t, 0.55, 0.85, smoother)
        return (v(0, 5 * math.sin(math.pi * w), z * (1 - w)), 0.0, 0.0)
    # hind legs swing under the body, skid, then settle
    u = ramp(t, 0.05, 0.35, smoother)
    z_plant = -6.0
    z = start[k][0] + (z_plant - start[k][0]) * u + (travel if t > 0.35 else 0) * 0.15
    w = ramp(t, 0.6, 0.9, smoother)
    return (v(0, 8 * math.sin(math.pi * u) * (1 - u * 0.3) * (1 - w) + 4 * math.sin(math.pi * w), z * (1 - w)), 0.0, 0.0)


c = clip("run_stop", 0.95, loop="hold", category="B Ground locomotion", priority=1,
         desc="braking: forelegs plant ahead, weight thrown back on the haunches, head and tail swing up, settle")
build(c, base=lambda p, t: (ground_base(p, t), run_body(p, 0.0, 1 - ramp(t, 0.0, 0.3)),
                             apply_rotation(p, "body", v(-7 * window(t, 0.05, 0.3, 0.45, 0.85) + 1.5 * window(t, 0.75, 0.85, 0.88, 0.95), 0, 0)),
                             apply_position(p, "body", v(0, -3 * window(t, 0.1, 0.3, 0.45, 0.8), 2.5 * window(t, 0.05, 0.3, 0.4, 0.8)))),
      head=Motion().rot("neck_1", [(0, v(14, 0, 0)), (0.3, v(-10, 0, 0), "out"), (0.6, v(-3, 0, 0)), (0.95, ZERO)])
      .rot("neck_2", [(0, v(4, 0, 0)), (0.35, v(-4, 0, 0)), (0.95, ZERO)])
      .rot("head", [(0, v(-16, 0, 0)), (0.35, v(6, 0, 0), "out"), (0.7, v(-1, 0, 0)), (0.95, ZERO)])
      .rot("jaw", [(0, v(6, 0, 0)), (0.3, v(12, 0, 0)), (0.95, ZERO)]),
      legs=run_stop_legs, stabilise=0.4, tail_gain=1.5,
      extra=lambda p, t: [apply_rotation(p, tb, v(10 * window(t, 0.1, 0.35, 0.5, 0.95) * (1 - i * 0.08), 0, 0))
                          for i, tb in enumerate(TAIL)])
c.sound(0.2, "step")
c.sound(0.32, "step")
c.particle(0.25, "dust_ring", "ground")


# turning in place: planted feet rotate about the body centre (opposite to the turn) and step back
TURN_L = 1.2
TURN_RATE = 45.0  # deg/s nominal; anim_time_update scales by the real turn rate
TURN_GAIT = {"fl": 0.0, "hr": 0.08, "fr": 0.5, "hl": 0.58}
TURN_DUTY = 0.68


def turn_legs(direction):
    """direction +1 = turn left.  A world-fixed foot seen from a body turning left drifts right."""
    sweep = math.radians(TURN_RATE * TURN_L * TURN_DUTY)

    def f(k, t):
        p = (t / TURN_L - TURN_GAIT[k]) % 1.0
        x0, _, z0 = S.ball_rest[k]
        if p < TURN_DUTY:
            th = (-0.5 + p / TURN_DUTY) * sweep * direction
            lift = 0.0
            pitch = 0.0
        else:
            u = (p - TURN_DUTY) / (1 - TURN_DUTY)
            th = (0.5 - smoother(u)) * sweep * direction
            lift = 6.0 * math.sin(math.pi * u) ** 0.85
            pitch = 14 * math.sin(math.pi * u)
        # rotate the rest foot position about the body centre (model y axis)
        x = x0 * math.cos(th) + z0 * math.sin(th)
        z = -x0 * math.sin(th) + z0 * math.cos(th)
        return (v(x - x0, lift, z - z0), pitch, -pitch * 0.6)
    return f


for name, d in (("turn_left", 1.0), ("turn_right", -1.0)):
    c = clip(name, TURN_L, loop=True,
             atu=f"q.anim_time + q.delta_time * math.clamp(math.abs(v.turn) / {TURN_RATE}, 0.35, 2.2)",
             category="B Ground locomotion", priority=1,
             desc=f"turn in place {'left' if d > 0 else 'right'}: diagonal stepping around the body centre, chest leads, head looks into the turn, tail swings out")
    yaw_into = -d  # head/chest rotation y toward the turn side (left = negative y)
    build(c, base=lambda p, t, d=d: (ground_base(p, t),
                                     apply_rotation(p, "chest", v(0, -d * (6 + 1.5 * math.sin(TAU * t / TURN_L)), 0)),
                                     apply_rotation(p, "pelvis", v(0, d * (3 + 1.5 * math.sin(TAU * t / TURN_L - 0.8)), 0)),
                                     apply_rotation(p, "body", v(0.6 * math.sin(2 * TAU * t / TURN_L), 0, d * 1.6 * math.sin(TAU * t / TURN_L))),
                                     apply_position(p, "body", v(0, -0.5 + 0.5 * math.cos(2 * TAU * t / TURN_L), 0))),
          head=Motion().rot("neck_2", [(0, v(0, yaw_into * 6, 0))]).rot("neck_3", [(0, v(0, yaw_into * 7, 0))])
          .rot("neck_4", [(0, v(0, yaw_into * 6, 0))]).rot("head", [(0, v(-2, yaw_into * 10, d * 4))]),
          legs=turn_legs(d), stabilise=0.4, keep_yaw=False,
          extra=lambda p, t, d=d: [apply_rotation(p, tb, v(0, d * 2.2 * (1 + i * 0.25), 0)) for i, tb in enumerate(TAIL)])
    for k, off in TURN_GAIT.items():
        c.sound(round((off + 0.0) * TURN_L, 3) % TURN_L or 0.0, "step")


def backstep_legs(k, t):
    """Two backward steps (~1.4 blocks): reverse 2-beat stepping, planted feet slide forward."""
    T = 1.25
    dist = 22.0  # units
    seq = {"hl": (0.0, 0.42), "fr": (0.12, 0.54), "hr": (0.5, 0.92), "fl": (0.62, 1.04)}
    t0, t1 = seq[k]
    prog = smoother(min(1, t / 1.15))
    body_back = dist * prog  # body moved back => planted feet move forward (-z) relative to it
    if t < t0:
        z = -body_back
        return (v(0, 0, z), 0.0, 0.0)
    if t <= t1:
        u = (t - t0) / (t1 - t0)
        z_start = -dist * smoother(min(1, t0 / 1.15))
        z_end = -dist * smoother(min(1, t1 / 1.15)) + dist * 0.5
        z = z_start + (z_end - z_start) * smoother(u)
        return (v(0, 6.5 * math.sin(math.pi * u), z), -10 * math.sin(math.pi * u), 8 * math.sin(math.pi * u))
    z_end = -dist * smoother(min(1, t1 / 1.15)) + dist * 0.5
    return (v(0, 0, z_end - (body_back - dist * smoother(min(1, t1 / 1.15)))), 0.0, 0.0)


c = clip("step_backward", 1.25, loop="hold", category="B Ground locomotion", priority=1,
         desc="two wary backward steps: weight back, head drawn up, wings flare slightly, tail lifts")
build(c, base=lambda p, t: (ground_base(p, t),
                             apply_position(p, "body", v(0, -1.0 * math.sin(math.pi * ramp(t, 0, 1.25)), 1.5 * window(t, 0.05, 0.3, 0.9, 1.25))),
                             apply_rotation(p, "body", v(-3 * window(t, 0.05, 0.3, 0.9, 1.25), 0, 1.8 * math.sin(TAU * t / 1.0))),
                             unfold_delta(p, 0.12 * window(t, 0.1, 0.4, 0.8, 1.2))),
      head=Motion().rot("neck_1", [(0, ZERO), (0.3, v(-12, 0, 0)), (0.95, v(-10, 0, 0)), (1.25, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.35, v(-5, 0, 0)), (1.25, ZERO)])
      .rot("head", [(0, ZERO), (0.3, v(8, 0, 0)), (1.0, v(6, 0, 0)), (1.25, ZERO)])
      .rot("jaw", [(0, ZERO), (0.25, v(8, 0, 0)), (1.0, v(5, 0, 0)), (1.25, ZERO)]),
      legs=backstep_legs, stabilise=0.4,
      extra=lambda p, t: [apply_rotation(p, tb, v(6 * window(t, 0.1, 0.4, 0.9, 1.25), 0, 0)) for tb in TAIL[:5]])
for tt in (0.42, 0.54, 0.92, 1.04):
    c.sound(tt, "step")


# ============================================================================= C. AERIAL MOVEMENT (P1)

TAIL_STRAIGHT = [v(15, 0, 0), v(11, 0, 0), v(5, 0, 0), v(-2, 0, 0), v(-6, 0, 0), v(-7, 0, 0), v(-5, 0, 0), v(-3, 0, 0)]
FLAP_L = 1.05


def elevation(ph, up, down, split=0.4):
    """Wing elevation over a flap: fast power stroke down (0..split), slower recovery up."""
    ph %= 1.0
    if ph < split:
        return up + (down - up) * smoother(ph / split)
    return down + (up - down) * smoother((ph - split) / (1 - split))


def flap_wings(pose, ph, up=-50.0, down=30.0, sweep=10.0, fold=22.0, k=1.0, split=0.4):
    """One wing beat on both wings (left authored, right mirrored).  Root leads, the forearm,
    hand and each finger lag progressively (overlap); the arm half-folds on the recovery stroke."""
    e = elevation(ph, up, down, split)
    rec = math.sin(math.pi * min(1, max(0, (ph % 1 - split) / (1 - split))))  # 0..1 during recovery
    pw = math.sin(math.pi * min(1, (ph % 1) / split)) if ph % 1 < split else 0.0  # during the power stroke
    w = {
        "wing_l_upper": v(6 * pw - 8 * rec, sweep * pw - 0.6 * sweep * rec, e),
        "wing_l_fore": v(0, fold * rec, 0.32 * (elevation(ph - 0.07, up, down, split) - e)),
        "wing_l_hand": v(0, -fold * 0.9 * rec, 0.45 * (elevation(ph - 0.12, up, down, split) - e)),
    }
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        lag = 0.5 * (elevation(ph - 0.15 - 0.025 * i, up, down, split) - e)
        spread = (3, 0, -3, -5)[i] * pw + (-2, 6, 12, 16)[i] * rec
        w[f] = v(0, spread, lag)
    for b, r in w.items():
        apply_rotation(pose, b, r * k)
        apply_rotation(pose, right_of(b), mirror_vec(r * k, "rotation"))
    for b in ("wing_l_mem_f1", "wing_l_mem_f2", "wing_l_mem_f3", "wing_l_mem_b"):
        s = 1 - 0.16 * rec * k
        for n in (b, right_of(b)):
            e2 = pose_entry(pose, n)
            e2["scale"] = e2["scale"] * v(1, 1, s)


def tuck_legs(pose, k=1.0, dangle=0.0, ph=0.0):
    for b, r in TUCK.items():
        d = v(dangle * math.sin(TAU * (ph - 0.35 - 0.08 * ("lower" in b or "shin" in b))), 0, 0)
        apply_rotation(pose, b, r * k + d)
        apply_rotation(pose, right_of(b), mirror_vec(r * k + d, "rotation"))


def fly_neck(pose, k=1.0):
    for b, r in FLY_NECK.items():
        apply_rotation(pose, b, r * k)


def straight_tail(pose, k=1.0, extra=0.0):
    for i, (b, r) in enumerate(zip(TAIL, TAIL_STRAIGHT)):
        apply_rotation(pose, b, r * k + v(extra, 0, 0))


def flap_body(pose, ph, heave=2.6, pitch=2.5, base_pitch=0.0, k=1.0):
    apply_position(pose, "root", v(0, heave * math.sin(TAU * (ph - 0.2)), 0) * k)
    apply_rotation(pose, "body", v(base_pitch - pitch * math.sin(TAU * (ph - 0.15)), 0, 0) * k)


def flap_pose(pose, ph, k=1.0):
    flap_wings(pose, ph, k=k)
    flap_body(pose, ph, k=k)
    tuck_legs(pose, k, dangle=4 * k, ph=ph)
    fly_neck(pose, k)
    straight_tail(pose, k)


c = clip("flight_flap", FLAP_L, loop=True, category="C Aerial movement", priority=1,
         desc="powered flight: fast power stroke, half-folded recovery stroke, wing-tip lag, body heave, steady head",
         preview={"target": (0, 56, 0)})
build(c, base=lambda p, t: flap_pose(p, t / FLAP_L),
      head=Motion().fn("jaw", "rotation", lambda t: v(3 + 2 * math.sin(TAU * t / FLAP_L - 1), 0, 0)),
      stabilise=0.15, tail_gain=1.1)
c.sound(0.1, "flap")

ASC_L = 0.9
c = clip("flight_ascend", ASC_L, loop=True, category="C Aerial movement", priority=1,
         desc="climbing: deeper, faster strokes, body pitched up, legs hanging, tail low as a rudder",
         preview={"target": (0, 56, 0)})
build(c, base=lambda p, t: (flap_wings(p, t / ASC_L, up=-62, down=36, sweep=13, fold=26, split=0.38),
                            flap_body(p, t / ASC_L, heave=3.2, pitch=3, base_pitch=-16),
                            tuck_legs(p, 0.6, dangle=7, ph=t / ASC_L), fly_neck(p, 0.6), straight_tail(p, 1.0, -4)),
      head=Motion().rot("head", [(0, v(-6, 0, 0))]).fn("jaw", "rotation", lambda t: v(7 + 3 * math.sin(TAU * t / ASC_L), 0, 0)),
      stabilise=0.12, tail_gain=1.2)
c.sound(0.08, "flap")

GLIDE_L = 4.0


def glide_pose(pose, t, k=1.0):
    ph = t / GLIDE_L
    wing = {
        "wing_l_upper": v(1.5 * math.sin(TAU * ph + 0.4), 2 * math.sin(TAU * ph + 1.0), -9 + 2.5 * math.sin(TAU * ph)),
        "wing_l_fore": v(0, 0, 3 + 2 * math.sin(TAU * ph - 0.6)),
        "wing_l_hand": v(0, 0, 2 + 2 * math.sin(TAU * ph - 1.1)),
    }
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        wing[f] = v(0, 1.2 * math.sin(TAU * 2 * ph - 0.7 * i), 1.5 * math.sin(TAU * 2 * ph - 0.5 * i))
    for b, r in wing.items():
        apply_rotation(pose, b, r * k)
        apply_rotation(pose, right_of(b), mirror_vec(r * k, "rotation"))
    for i, b in enumerate(("wing_l_mem_f1", "wing_l_mem_f2", "wing_l_mem_f3", "wing_l_mem_b")):
        for n, sgn in ((b, 1), (right_of(b), -1)):
            e = pose_entry(pose, n)
            e["scale"] = e["scale"] * v(1, 1, 1 + 0.025 * k * math.sin(TAU * 3 * ph - i + (0.6 if sgn < 0 else 0)))
    apply_rotation(pose, "root", v(0, 0, 3 * math.sin(TAU * ph + 0.5)) * k)
    apply_position(pose, "root", v(0, 1.2 * math.sin(TAU * ph + 1.6), 0) * k)
    apply_rotation(pose, "body", v(-2, 0, 0) * k)
    tuck_legs(pose, k, dangle=2 * k, ph=ph)
    fly_neck(pose, k)
    straight_tail(pose, k)
    for i, b in enumerate(TAIL):
        apply_rotation(pose, b, v(0, 2.5 * math.sin(TAU * ph - 0.4 * i), 0) * k)


c = clip("flight_glide", GLIDE_L, loop=True, category="C Aerial movement", priority=1,
         desc="soaring: wings held out but never frozen - slow dihedral swell, finger ripple, membrane flutter, head scanning, tail rudder",
         preview={"target": (0, 56, 0)})
build(c, base=glide_pose,
      head=Motion().cascade(["head", "neck_4", "neck_3", "neck_2"],
                            [(0, ZERO), (1.0, v(0, -10, 0)), (2.0, ZERO), (3.0, v(0, 10, 0)), (4.0, ZERO)],
                            [0, 0.15, 0.3, 0.45], [1, 0.5, 0.35, 0.25]),
      stabilise=0.1, keep_yaw=False, tail_gain=0.8)
c.sound(0.0, "glide")

DESC_L = 3.0
c = clip("flight_descend", DESC_L, loop=True, category="C Aerial movement", priority=1,
         desc="descending: wings raised in a V and swept back, tips buffeting, nose down, legs starting to drop, tail up as an air brake",
         preview={"target": (0, 56, 0)})


def descend_pose(pose, t):
    ph = t / DESC_L
    wing = {"wing_l_upper": v(-4, -12 + 2 * math.sin(TAU * ph), -30 + 3 * math.sin(TAU * ph + 0.5)),
            "wing_l_fore": v(0, 14 + 2 * math.sin(TAU * ph - 0.6), 0), "wing_l_hand": v(0, -16, 2 * math.sin(TAU * 4 * ph))}
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        wing[f] = v(0, 4 * i, 2.2 * math.sin(TAU * 4 * ph - i * 0.9))
    for b, r in wing.items():
        apply_rotation(pose, b, r)
        apply_rotation(pose, right_of(b), mirror_vec(r, "rotation"))
    for b in ("wing_l_mem_f1", "wing_l_mem_f2", "wing_l_mem_f3", "wing_l_mem_b"):
        for n in (b, right_of(b)):
            e = pose_entry(pose, n)
            e["scale"] = e["scale"] * v(1, 1, 0.88 + 0.03 * math.sin(TAU * 4 * ph))
    apply_rotation(pose, "body", v(12 + 1.5 * math.sin(TAU * ph), 0, 0))
    apply_rotation(pose, "root", v(0, 0, 2 * math.sin(TAU * ph)))
    tuck_legs(pose, 0.45, dangle=4, ph=ph)
    fly_neck(pose, 1.0)
    straight_tail(pose, 1.0, 5)


build(c, base=descend_pose, head=Motion().rot("head", [(0, v(10, 0, 0))]).rot("jaw", [(0, v(4, 0, 0))]),
      stabilise=0.1, tail_gain=0.9)


def bank_motion(direction):
    """Additive banking layer (direction +1 = left turn)."""
    d = direction
    m = Motion()
    m.fn("root", "rotation", lambda t: v(0, 0, d * (16 + 2 * math.sin(TAU * t / 2.0))))
    m.fn("chest", "rotation", lambda t: v(0, -d * 6, 0))
    m.cascade(["neck_2", "neck_3", "neck_4", "head"], [(0, v(0, -d * 6, 0))], [0, 0, 0, 0], [0.8, 1.0, 0.8, 1.4])
    m.fn("head", "rotation", lambda t: v(0, 0, -d * 10))  # keep the eyes nearer the horizon
    inner, outer = ("l", "r") if d > 0 else ("r", "l")
    sgn = {"l": 1, "r": -1}
    m.fn(f"wing_{inner}_upper", "rotation", lambda t: v(0, -6 * sgn[inner], -4 * sgn[inner]))
    m.fn(f"wing_{inner}_fore", "rotation", lambda t: v(0, 8 * sgn[inner], 0))
    m.fn(f"wing_{outer}_upper", "rotation", lambda t: v(0, 8 * sgn[outer], 2 * sgn[outer] * math.sin(TAU * t / 2.0)))
    for i, b in enumerate(TAIL):
        m.fn(b, "rotation", (lambda i: (lambda t: v(1.5, -d * 2.5 * (1 + 0.15 * i), 0)))(i))
    return m


for name, d in (("flight_bank_left", 1), ("flight_bank_right", -1)):
    c = clip(name, 2.0, loop=True, category="C Aerial movement", priority=1, kind="additive",
             desc=f"banking {'left' if d > 0 else 'right'} (additive, weighted by turn rate): roll into the turn, head looks in and stays level, outer wing reaches, tail trails out",
             preview={"base": "flight_glide", "target": (0, 56, 0)})
    build(c, motion=bank_motion(d), stabilise=None, tail=False)

APP_L = 0.8


def approach_pose(pose, t, k=1.0):
    ph = t / APP_L
    e = -30 + 34 * math.sin(math.pi * min(1, ph / 0.42)) ** 1.2 if ph < 0.42 else -30 + 34 * (1 - smoother((ph - 0.42) / 0.58))
    wing = {"wing_l_upper": v(-6, 26, e), "wing_l_fore": v(0, 10, 0.35 * (-30 - e)), "wing_l_hand": v(0, -6, 0.5 * (-30 - e))}
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        wing[f] = v(0, (2, -1, -4, -6)[i], 0.6 * (-30 - e))
    for b, r in wing.items():
        apply_rotation(pose, b, r * k)
        apply_rotation(pose, right_of(b), mirror_vec(r * k, "rotation"))
    apply_rotation(pose, "body", v(-20 + 2 * math.sin(TAU * ph), 0, 0) * k)
    apply_position(pose, "root", v(0, 1.5 * math.sin(TAU * (ph - 0.25)), 0) * k)
    reach = {"leg_fl_upper": v(-28, 0, -4), "leg_fl_lower": v(12, 0, 0), "foot_fl": v(10, 0, 0), "toes_fl": v(-15, 0, 0),
             "leg_hl_thigh": v(-34, 0, -3), "leg_hl_shin": v(26, 0, 0), "leg_hl_meta": v(-10, 0, 0), "foot_hl": v(6, 0, 0),
             "toes_hl": v(-15, 0, 0)}
    for b, r in reach.items():
        dd = v(2 * math.sin(TAU * (ph - 0.3)), 0, 0)
        apply_rotation(pose, b, (r + dd) * k)
        apply_rotation(pose, right_of(b), mirror_vec((r + dd) * k, "rotation"))
    straight_tail(pose, k * 0.6, -4 * k)


c = clip("landing_approach", APP_L, loop=True, category="C Aerial movement", priority=1,
         desc="flare before touch-down: nose up, braking back-flaps, legs reaching for the ground, tail down, eyes on the spot",
         preview={"target": (0, 50, 0)})
build(c, base=approach_pose,
      head=Motion().rot("neck_1", [(0, v(-12, 0, 0))]).rot("neck_2", [(0, v(-4, 0, 0))]).rot("head", [(0, v(16, 0, 0))])
      .rot("jaw", [(0, v(6, 0, 0))]),
      stabilise=0.2, tail_gain=1.0)
c.sound(0.05, "flap")


def impact_base(pose, t):
    kh = ramp(t, 0.22, 0.8)
    kf = ramp(t, 0.32, 0.95)
    ku = ramp(t, 0.45, 1.15)
    fold_pose(pose, ku, kf, kh)
    up = v(0, 22 * (1 - ramp(t, 0.0, 0.35)), -22 * (1 - ku) - 20 * window(t, 0.02, 0.12, 0.18, 0.45)
           + 2.2 * math.sin(TAU * 6 * t) * window(t, 1.1, 1.18, 1.25, 1.4))
    apply_rotation(pose, "wing_l_upper", up)
    apply_rotation(pose, "wing_r_upper", mirror_vec(up, "rotation"))


c = clip("landing_impact", 1.4, loop="hold", category="C Aerial movement", priority=1,
         desc="touch-down: legs absorb the weight on planted feet, body dips and rebounds, wings snap up then fold shoulder->elbow->fingers, tail slams and settles")
build(c, base=impact_base,
      motion=Motion().pos("body", [(0, ZERO), (0.14, v(0, -7, 0), "out"), (0.42, v(0, 0.8, 0)), (0.75, ZERO)])
      .rot("body", [(0, v(-12, 0, 0)), (0.18, v(5, 0, 0), "out"), (0.45, v(-1, 0, 0)), (0.8, ZERO)])
      .cascade(TAIL, [(0, ZERO), (0.16, v(-6, 0, 0), "out"), (0.45, v(2, 0, 0)), (0.9, ZERO)],
               [0.02 * i for i in range(8)], [1, 0.6, 0.3, 0, -0.3, -0.4, -0.4, -0.3]),
      head=Motion().rot("neck_1", [(0, v(-12, 0, 0)), (0.2, v(9, 0, 0), "out"), (0.52, v(-3, 0, 0)), (0.85, ZERO)])
      .rot("neck_2", [(0, v(-4, 0, 0)), (0.25, v(4, 0, 0)), (0.8, ZERO)])
      .rot("head", [(0, v(16, 0, 0)), (0.22, v(-4, 0, 0)), (0.58, v(2, 0, 0)), (0.9, ZERO)])
      .rot("jaw", [(0, v(6, 0, 0)), (0.12, v(12, 0, 0)), (0.5, ZERO)]),
      legs=planted, stabilise=0.5, tail_gain=1.6)
c.sound(0.0, "land")
c.sound(0.3, "wing_unfold")
c.particle(0.02, "dust_ring", "ground")


def pre_takeoff_base(pose, t):
    fold_pose(pose, 1 - ramp(t, 0.0, 0.32), 1 - ramp(t, 0.06, 0.4), 1 - ramp(t, 0.14, 0.5))
    lift = v(0, -12 * ramp(t, 0.15, 0.55, smooth), -55 * ramp(t, 0.1, 0.55, smoother))
    apply_rotation(pose, "wing_l_upper", lift)
    apply_rotation(pose, "wing_r_upper", mirror_vec(lift, "rotation"))


c = clip("pre_takeoff", 0.55, loop="hold", category="C Aerial movement", priority=1,
         desc="anticipation: crouch on the haunches, wings unfold shoulder first and cock high, head looks up, tail lifts")
build(c, base=pre_takeoff_base,
      motion=Motion().pos("body", [(0, ZERO), (0.5, v(0, -7, 1.5))]).rot("body", [(0, ZERO), (0.5, v(-6, 0, 0))])
      .cascade(TAIL[:5], [(0, ZERO), (0.5, v(8, 0, 0))], [0, 0.03, 0.06, 0.09, 0.12], [1, 0.8, 0.6, 0.4, 0.3]),
      head=Motion().rot("neck_1", [(0, ZERO), (0.5, v(10, 0, 0))]).rot("neck_2", [(0, ZERO), (0.5, v(-6, 0, 0))])
      .rot("head", [(0, ZERO), (0.45, v(-12, 0, 0))]).rot("jaw", [(0, ZERO), (0.3, v(6, 0, 0))]),
      legs=planted, stabilise=0.4, tail_gain=1.0)
c.sound(0.05, "wing_unfold")
c.sound(0.2, "growl")

LAUNCH_L = 1.05
_flap0: dict = {}
flap_pose(_flap0, 0.0)  # launch must end exactly on the first frame of flight_flap


def launch_base(pose, t):
    w_end = ramp(t, 0.82, LAUNCH_L)
    a: dict = {}
    # wings: from the cocked pre-takeoff pose through two climbing strokes
    e = Keys([(0, -55), (0.28, 32, "inout"), (0.62, -48, "inout"), (0.86, 28, "inout"), (1.05, -50, "inout")])(t)[()]
    sw = Keys([(0, -12), (0.14, 12), (0.28, 0), (0.45, -6), (0.62, 0), (0.75, 10), (0.86, 0), (1.05, 0)])(t)[()]
    fold = 22 * window(t, 0.3, 0.45, 0.5, 0.62) + 20 * window(t, 0.88, 0.97, 1.0, 1.05)
    lagE = lambda dtl: Keys([(0, -55), (0.28, 32, "inout"), (0.62, -48, "inout"), (0.86, 28, "inout"),  # noqa: E731
                             (1.05, -50, "inout")])(max(0, t - dtl))[()]
    wing = {"wing_l_upper": v(0, sw, e), "wing_l_fore": v(0, fold, 0.32 * (lagE(0.07) - e)),
            "wing_l_hand": v(0, -fold * 0.9, 0.45 * (lagE(0.12) - e))}
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        wing[f] = v(0, (-2, 6, 12, 16)[i] * fold / 22, 0.5 * (lagE(0.15 + 0.025 * i) - e))
    for b, r in wing.items():
        apply_rotation(a, b, r)
        apply_rotation(a, right_of(b), mirror_vec(r, "rotation"))
    apply_position(a, "body", Keys([(0, v(0, -7, 1.5)), (0.14, v(0, 3, -1), "out"), (0.5, v(0, 1, 0)), (1.05, ZERO)])(t))
    apply_rotation(a, "body", Keys([(0, v(-6, 0, 0)), (0.4, v(-14, 0, 0)), (1.05, v(-2.5 * math.sin(TAU * -0.15), 0, 0))])(t))
    apply_position(a, "root", v(0, 2.5 * math.sin(math.pi * ramp(t, 0.2, 0.5)) - 2 * window(t, 0.55, 0.65, 0.7, 0.8), 0))
    fly_neck(a, ramp(t, 0.1, 0.8))
    straight_tail(a, ramp(t, 0.05, 0.6))
    for i, tb in enumerate(TAIL[:5]):
        apply_rotation(a, tb, v(8 * (1 - ramp(t, 0.0, 0.4)) * (1, 0.8, 0.6, 0.4, 0.3)[i], 0, 0))
    # blend into flap phase 0 over the last 0.23 s
    for b in set(a) | set(_flap0):
        e1 = pose_entry(pose, b)
        pa = a.get(b, {"rotation": ZERO, "position": ZERO, "scale": ONE})
        pb = _flap0.get(b, {"rotation": ZERO, "position": ZERO, "scale": ONE})
        e1["rotation"] = e1["rotation"] + pa["rotation"] * (1 - w_end) + pb["rotation"] * w_end
        e1["position"] = e1["position"] + pa["position"] * (1 - w_end) + pb["position"] * w_end
        e1["scale"] = e1["scale"] * (pa["scale"] * (1 - w_end) + pb["scale"] * w_end)


def launch_legs(k, t):
    if t < 0.14:
        return (ZERO, 0.0, 0.0)  # still pushing off the ground
    return None  # in the air: blended to the tuck in extra()


def launch_extra(pose, t):
    w = ramp(t, 0.1, 0.55)
    for b, r in TUCK.items():
        for n, rr in ((b, r), (right_of(b), mirror_vec(r, "rotation"))):
            e = pose_entry(pose, n)
            held = LAUNCH_HOLD.get(n, ZERO) if t >= 0.14 else e["rotation"]
            e["rotation"] = (held if t >= 0.14 else e["rotation"]) * (1 - w) + rr * w


LAUNCH_HOLD: Dict[str, np.ndarray] = {}


def launch_capture(pose, t):
    if abs(t - 0.1333) < 0.02 or (t < 0.14 and not LAUNCH_HOLD):
        for b in list(TUCK) + [right_of(b) for b in TUCK]:
            LAUNCH_HOLD[b] = pose_entry(pose, b)["rotation"].copy()
    launch_extra(pose, t)


c = clip("launch", LAUNCH_L, loop="hold", category="C Aerial movement", priority=1,
         desc="explosive leg push on planted feet, huge first downstroke, legs trail then tuck, two climbing strokes; ends on flight_flap frame 0")
build(c, base=launch_base, legs=launch_legs, extra=launch_capture, stabilise=0.25, tail_gain=1.5)
c.sound(0.0, "takeoff")
c.sound(0.12, "flap")
c.sound(0.66, "flap")
c.particle(0.02, "dust_ring", "ground")


# ============================================================================= A. LIVING BEHAVIOUR (P2)

BR_L = 4.2


def breath(t):
    return 0.5 - 0.5 * math.cos(TAU * t / BR_L)  # 0 exhaled .. 1 inhaled (peak at L/2)


def breathe_base(pose, t):
    ground_base(pose, t)
    b = breath(t)
    e = pose_entry(pose, "chest")
    e["scale"] = e["scale"] * v(1 + 0.025 * b, 1 + 0.035 * b, 1)
    apply_position(pose, "chest", v(0, 0.35 * b, 0))
    apply_rotation(pose, "body", v(0, 0, 0.7 * math.sin(TAU * t / BR_L - 0.3)))
    apply_position(pose, "body", v(0.4 * math.sin(TAU * t / BR_L - 0.3), 0, 0))
    lift = v(0, 0, -1.3 * b)
    apply_rotation(pose, "wing_l_upper", lift)
    apply_rotation(pose, "wing_r_upper", mirror_vec(lift, "rotation"))


def breathe_tail(pose, t):
    for i, tb in enumerate(TAIL):
        apply_rotation(pose, tb, v(0.6 * math.sin(TAU * 2 * t / BR_L - 0.4 * i), (1.0 + 0.4 * i) * math.sin(TAU * t / BR_L - 0.5 * i), 0))


c = clip("idle_breathe", BR_L, loop=True, category="A Living behaviour", priority=1,
         desc="standing base: chest and flanks breathe, shoulders and wings lift on the inhale, weight drifts side to side on planted feet, tail sways")
build(c, base=breathe_base,
      head=Motion().fn("neck_1", "rotation", lambda t: v(-1.5 * breath(t), 1.2 * math.sin(TAU * t / BR_L + 0.8), 0))
      .fn("head", "rotation", lambda t: v(0.8 * breath(t), -1.5 * math.sin(TAU * t / BR_L + 0.5), 0))
      .fn("jaw", "rotation", lambda t: v(1.5 * (1 - breath(t)), 0, 0)),
      legs=planted, stabilise=0.6, extra=breathe_tail, tail_gain=0.6)
c.particle(3.1, "nostril_smoke", "nostril_l")
c.particle(3.1, "nostril_smoke", "nostril_r")

LOOK_CHAIN = ["head", "neck_4", "neck_3", "neck_2", "neck_1"]

c = clip("idle_look_left", 2.6, category="A Living behaviour", priority=2, kind="additive",
         desc="eyes/head lead a quick glance left, the neck follows segment by segment, a curious tilt and a small re-fixation, head returns first")
build(c, motion=Motion().rot("chest", [(0, ZERO), (0.9, v(0, -3, 0)), (1.8, v(0, -3, 0)), (2.5, ZERO)])
      .rot("body", [(0, ZERO), (0.8, v(0, 0, 1.2)), (1.9, v(0, 0, 1.2)), (2.6, ZERO)])
      .rot("tail_6", [(0, ZERO), (0.85, ZERO), (0.95, v(0, 6, 0), "out"), (1.25, ZERO)])
      .rot("tail_8", [(0, ZERO), (0.9, ZERO), (1.0, v(0, 9, 0), "out"), (1.35, ZERO)]),
      head=Motion().cascade(LOOK_CHAIN, [(0, ZERO), (0.12, v(0, 3, 0), "out"), (0.6, v(0, -26, 0), "out"),
                                         (1.15, v(0, -29, 0)), (1.35, v(0, -24, 0)), (1.75, v(0, -26, 0)),
                                         (2.25, ZERO), (2.6, ZERO)],
                            [0, 0.06, 0.12, 0.18, 0.24], [1, 0.45, 0.35, 0.25, 0.15])
      .rot("head", [(0, ZERO), (0.6, v(0, 0, 6)), (1.6, v(0, 0, 6)), (2.3, ZERO)])
      .rot("neck_1", [(0, ZERO), (0.6, v(-4, 0, 0)), (1.8, v(-4, 0, 0)), (2.4, ZERO)]),
      legs=planted, stabilise=0.6, tail_gain=0.5)

c = clip("idle_look_right", 2.9, category="A Living behaviour", priority=2, kind="additive",
         desc="slow look to the right over the shoulder with the neck raised, a double-take, two sniffs and a tail flick")
build(c, motion=Motion().rot("chest", [(0, ZERO), (1.0, v(0, 4, 0)), (1.9, v(0, 4, 0)), (2.7, ZERO)])
      .rot("body", [(0, ZERO), (0.9, v(0, 0, -1.2)), (2.0, v(0, 0, -1.2)), (2.9, ZERO)])
      .rot("tail_7", [(0, ZERO), (1.38, ZERO), (1.48, v(0, -8, 0), "out"), (1.8, ZERO)])
      .rot("tail_8", [(0, ZERO), (1.42, ZERO), (1.52, v(0, -11, 0), "out"), (1.9, ZERO)]),
      head=Motion().cascade(LOOK_CHAIN, [(0, ZERO), (0.45, v(0, 14, 0), "out"), (0.8, v(0, 16, 0)),
                                         (1.0, v(0, 30, 0), "snap"), (1.6, v(0, 30, 0)), (1.75, v(0, 27, 0)),
                                         (2.45, ZERO), (2.9, ZERO)],
                            [0, 0.08, 0.16, 0.24, 0.32], [1, 0.5, 0.38, 0.25, 0.15])
      .rot("neck_1", [(0, ZERO), (0.7, v(-8, 0, 0)), (2.0, v(-8, 0, 0)), (2.7, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.75, v(-4, 0, 0)), (2.0, v(-4, 0, 0)), (2.75, ZERO)])
      .rot("head", [(0, ZERO), (1.0, v(0, 0, -8)), (1.8, v(0, 0, -8)), (2.5, ZERO)])
      .rot("jaw", [(0, ZERO), (1.25, ZERO), (1.3, v(5, 0, 0)), (1.36, ZERO), (1.45, v(5, 0, 0)), (1.52, ZERO)]),
      legs=planted, stabilise=0.6, tail_gain=0.5)
c.particle(1.3, "nostril_smoke", "nostril_l")
c.particle(1.3, "nostril_smoke", "nostril_r")
c.sound(1.28, "sniff")


def pulses(times, width, amp):
    def f(t):
        return sum(amp * math.sin(math.pi * min(1, max(0, (t - t0) / width))) for t0 in times)
    return f


SNIFF_T = (1.0, 1.35, 1.7, 2.15)
c = clip("idle_sniff", 3.2, category="A Living behaviour", priority=2, kind="additive",
         desc="lowers chest and head to the ground, scans left-right with short sniff pulses and jaw twitches, smoke from the nostrils")
build(c, motion=Motion().rot("body", [(0, ZERO), (0.8, v(4, 0, 0)), (2.6, v(4, 0, 0)), (3.2, ZERO)])
      .pos("body", [(0, ZERO), (0.8, v(0, -1.5, -1)), (2.6, v(0, -1.5, -1)), (3.2, ZERO)]),
      head=Motion().rot("neck_1", [(0, ZERO), (0.7, v(24, 0, 0)), (2.5, v(24, 0, 0)), (3.1, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.75, v(12, 0, 0)), (2.5, v(12, 0, 0)), (3.15, ZERO)])
      .rot("neck_3", [(0, ZERO), (0.8, v(6, 0, 0)), (2.6, v(6, 0, 0)), (3.2, ZERO)])
      .rot("head", [(0, ZERO), (0.8, v(-12, 0, 0)), (1.3, v(-12, -8, 0)), (1.9, v(-12, 8, 0)), (2.4, v(-12, 0, 0)),
                    (2.6, v(-12, 0, 0)), (3.2, ZERO)])
      .fn("head", "rotation", lambda t: v(pulses(SNIFF_T, 0.14, 3.5)(t), 0, 0))
      .fn("jaw", "rotation", lambda t: v(pulses(SNIFF_T, 0.1, 4)(t), 0, 0)),
      legs=planted, stabilise=None, tail_gain=0.5)
for tt in SNIFF_T:
    c.particle(tt + 0.04, "nostril_smoke", "nostril_l")
    c.particle(tt + 0.04, "nostril_smoke", "nostril_r")
c.sound(1.0, "sniff")
c.sound(1.7, "sniff")

c = clip("idle_blink", 0.3, category="A Living behaviour", priority=2, kind="additive",
         desc="eyelids close and open (new eyelid bones, hidden inside the skull at rest); fired at random 2.5-6 s intervals on the client")
c.rot("eyelid_l", [(0, ZERO), (0.08, v(0, 0, -90), "out"), (0.16, v(0, 0, -90)), (0.3, ZERO, "inout")], mirror=True)

SCRATCH_KEYS = [(0, v(0, 0, 0)), (0.35, v(0, 9, -7), "inout"), (0.6, v(0, 1.5, -9)), (0.72, v(0, 0, -9), "in"),
                (0.95, v(0, 0, 4)), (1.1, v(0, 6, -2), "out"), (1.25, v(0, 0, -8), "in"), (1.45, v(0, 0, 4)),
                (1.58, v(0, 6, -2), "out"), (1.7, v(0, 0, -8), "in"), (1.9, v(0, 0, 4)), (2.15, v(0, 7, 0)),
                (2.45, v(0, 0, 0), "in"), (2.8, v(0, 0, 0))]
SCRATCH_PITCH = [(0, 0), (0.35, 20), (0.7, 12), (0.95, 14), (1.1, 22), (1.25, 12), (1.58, 22), (1.7, 12), (2.15, 20), (2.45, 0)]
SCRATCH_TOE = [(0, 0), (0.35, -12), (0.7, 22), (1.0, 26), (1.1, -6), (1.25, 22), (1.58, -6), (1.7, 22), (2.1, -8), (2.45, 0)]
_sk, _sp, _st = Keys(SCRATCH_KEYS), Keys(SCRATCH_PITCH), Keys(SCRATCH_TOE)

c = clip("idle_ground_scratch", 2.8, category="A Living behaviour", priority=2, kind="additive",
         desc="shifts weight onto the left legs, rakes the ground three times with the right fore-claws (claws curl on each stroke), watches the foot")
build(c, motion=Motion().rot("body", [(0, ZERO), (0.35, v(1, 0, 2.5)), (2.2, v(1, 0, 2.5)), (2.7, ZERO)])
      .pos("body", [(0, ZERO), (0.35, v(1.5, 0, 0)), (2.2, v(1.5, 0, 0)), (2.7, ZERO)])
      .fn("chest", "rotation", lambda t: v(0, 2 * math.sin(TAU * (t - 0.7) / 0.48) * window(t, 0.6, 0.75, 1.9, 2.0), 0)),
      head=Motion().rot("neck_1", [(0, ZERO), (0.45, v(8, 0, 0)), (2.1, v(8, 0, 0)), (2.7, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.5, v(0, 6, 0)), (2.1, v(0, 6, 0)), (2.7, ZERO)])
      .rot("neck_3", [(0, ZERO), (0.55, v(0, 4, 0)), (2.1, v(0, 4, 0)), (2.75, ZERO)])
      .rot("head", [(0, ZERO), (0.5, v(-4, 10, 0)), (2.1, v(-4, 10, 0)), (2.8, ZERO)]),
      legs=lambda k, t: (_sk(t), float(_sp(t)), float(_st(t))) if k == "fr" else planted(k, t),
      stabilise=None, tail_gain=0.6,
      extra=lambda p, t: apply_rotation(p, "tail_8", v(0, 7 * math.sin(TAU * t / 0.9) * window(t, 0.5, 0.7, 2.0, 2.4), 0)))
for tt in (0.72, 1.25, 1.7):
    c.particle(tt, "dust_puff", "claw_fr")
    c.sound(tt, "scratch")

c = clip("idle_tail_sway", 3.6, category="A Living behaviour", priority=2, kind="additive",
         desc="slow S-wave travels down the tail (tip lags, grows), hips counter-sway, a glance back along the body")
TS_P = 1.8
_tail_env = lambda t: window(t, 0.0, 0.6, 2.9, 3.6)  # noqa: E731
m = Motion().fn("pelvis", "rotation", lambda t: v(0, -2.5 * math.sin(TAU * t / TS_P + 0.5) * _tail_env(t), 0)) \
    .fn("body", "rotation", lambda t: v(0, 0, 1.0 * math.sin(TAU * t / TS_P) * _tail_env(t)))
for i, tb in enumerate(TAIL):
    m.fn(tb, "rotation", (lambda i: (lambda t: v(1.5 * _tail_env(t) + 1.5 * math.sin(TAU * t / TS_P * 2 - 0.5 * i) * _tail_env(t),
                                               (5 + 1.4 * i) * math.sin(TAU * t / TS_P - 0.75 * i) * _tail_env(t), 0)))(i))
build(c, motion=m,
      head=Motion().cascade(LOOK_CHAIN, [(0, ZERO), (1.3, ZERO), (1.75, v(0, 18, 0), "out"), (2.3, v(0, 16, 0)), (2.9, ZERO)],
                            [0, 0.06, 0.12, 0.18, 0.24], [1, 0.45, 0.35, 0.25, 0.15]),
      legs=planted, stabilise=0.6, tail_gain=0.4)


def wing_adjust_base(pose, t):
    unfold_delta(pose, *wing_open(t, 0.25, 0.75, 1.3, 1.85, 0.45), side="l")
    shake = window(t, 0.85, 0.95, 1.2, 1.4)
    lw = v(0, 0, -10 * window(t, 0.25, 0.75, 1.35, 1.95) + 4 * math.sin(TAU * 7 * t) * shake)
    apply_rotation(pose, "wing_l_upper", lw)
    for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
        apply_rotation(pose, f, v(0, 0, 3 * math.sin(TAU * 9 * t - i) * shake))
    unfold_delta(pose, *wing_open(t, 1.6, 1.85, 2.1, 2.45, 0.15, 0.05), side="r")
    apply_rotation(pose, "wing_r_upper", mirror_vec(v(0, 0, -5 * window(t, 1.6, 1.9, 2.2, 2.6)), "rotation"))


c = clip("idle_wing_adjust", 3.0, category="A Living behaviour", priority=2, kind="additive",
         desc="half-opens the left wing (shoulder, elbow, fingers in turn), shakes it out, refolds, then a small shrug of the right wing")
build(c, base=wing_adjust_base,
      motion=Motion().rot("body", [(0, ZERO), (0.6, v(0, 0, -1.5)), (1.8, v(0, 0, -1.5)), (2.4, ZERO)]),
      head=Motion().rot("neck_2", [(0, ZERO), (0.5, v(0, -6, 0)), (1.6, v(0, -6, 0)), (2.0, v(0, 3, 0)), (2.6, ZERO)])
      .rot("neck_3", [(0, ZERO), (0.55, v(0, -6, 0)), (1.65, v(0, -6, 0)), (2.0, v(0, 3, 0)), (2.65, ZERO)])
      .rot("head", [(0, ZERO), (0.6, v(-4, -14, 0)), (1.7, v(-4, -14, 0)), (2.05, v(0, 6, 0)), (2.7, ZERO)]),
      legs=planted, stabilise=0.6, tail_gain=0.6)
c.sound(0.3, "wing_unfold")
c.sound(0.95, "flap")
c.sound(1.6, "wing_unfold")


def stretch_legs(k, t):
    if k.startswith("h"):
        return planted(k, t)
    slide = -8 * ramp(t, 0.5, 1.1)
    t0, t1 = (2.35, 2.85) if k == "fl" else (2.55, 3.05)
    if t < t0:
        return (v(0, 0, slide), 0.0, 0.0)
    u = ramp(t, t0, t1, smoother)
    return (v(0, 6 * math.sin(math.pi * u), -8 * (1 - u)), 16 * math.sin(math.pi * u), 0.0)


def stretch_base(pose, t):
    w = window(t, 0.9, 1.4, 2.0, 2.6)
    unfold_delta(pose, *wing_open(t, 0.9, 1.4, 1.95, 2.45, 0.35))
    lw = v(0, 0, -16 * w)
    apply_rotation(pose, "wing_l_upper", lw)
    apply_rotation(pose, "wing_r_upper", mirror_vec(lw, "rotation"))
    for i, tb in enumerate(TAIL):
        apply_rotation(pose, tb, TAIL_STRAIGHT[i] * 0.6 * window(t, 0.8, 1.3, 2.1, 2.8)
                       + v(0, 1.5 * math.sin(TAU * 10 * t) * window(t, 1.5, 1.6, 1.9, 2.0), 0))


c = clip("idle_stretch", 3.4, category="A Living behaviour", priority=2, kind="additive",
         desc="cat-like stretch: forelegs reach forward, chest dips while the hips stay up, neck extends, wings lift half open, tail stretches and shivers, then steps back")
build(c, base=stretch_base,
      motion=Motion().rot("body", [(0, ZERO), (1.1, v(8, 0, 0)), (2.2, v(8, 0, 0)), (2.9, ZERO)])
      .pos("body", [(0, ZERO), (1.1, v(0, -3, -2)), (2.2, v(0, -3, -2)), (2.9, ZERO)])
      .rot("pelvis", [(0, ZERO), (1.1, v(-6, 0, 0)), (2.2, v(-6, 0, 0)), (2.9, ZERO)]),
      head=Motion().rot("neck_1", [(0, ZERO), (1.0, v(6, 0, 0)), (2.1, v(6, 0, 0)), (2.8, ZERO)])
      .rot("neck_2", [(0, ZERO), (1.1, v(-6, 0, 0)), (2.1, v(-6, 0, 0)), (2.85, ZERO)])
      .rot("neck_3", [(0, ZERO), (1.15, v(-6, 0, 0)), (2.15, v(-6, 0, 0)), (2.9, ZERO)])
      .rot("head", [(0, ZERO), (1.2, v(-10, 0, 0)), (1.65, v(-10, 0, 4)), (1.8, v(-10, 0, -4)), (2.2, v(-10, 0, 0)), (2.95, ZERO)])
      .rot("jaw", [(0, ZERO), (1.0, v(12, 0, 0)), (2.0, v(12, 0, 0)), (2.4, ZERO)]),
      legs=stretch_legs, stabilise=None, tail_gain=0.5)
c.sound(1.1, "yawn")
c.sound(2.85, "step")
c.sound(3.05, "step")

c = clip("idle_yawn", 2.8, category="A Living behaviour", priority=2, kind="additive",
         desc="inhales, raises the head, jaw opens slowly to 46 deg with the eyes shut, a shudder, the jaw snaps shut, head shake")
build(c, motion=Motion().rot("body", [(0, ZERO), (0.6, v(-2, 0, 0)), (1.6, v(-2, 0, 0)), (2.2, ZERO)])
      .scl("chest", [(0, ONE), (0.85, v(1.05, 1.07, 1)), (1.5, v(1.0, 1.0, 1)), (2.0, v(0.98, 0.98, 1)), (2.8, ONE)])
      .rot("eyelid_l", [(0, ZERO), (0.55, ZERO), (0.8, v(0, 0, -90), "out"), (1.6, v(0, 0, -90)), (1.85, ZERO)], mirror=True),
      head=Motion().rot("neck_1", [(0, ZERO), (0.6, v(-10, 0, 0)), (1.6, v(-10, 0, 0)), (2.2, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.6, v(-6, 0, 0)), (1.6, v(-6, 0, 0)), (2.2, ZERO)])
      .rot("head", [(0, ZERO), (0.7, v(-14, 0, 8)), (1.55, v(-14, 0, 8)), (2.0, v(2, 0, 0)), (2.4, ZERO)])
      .fn("head", "rotation", lambda t: v(0, 5 * math.sin(TAU * 4.5 * t) * window(t, 1.8, 1.9, 2.2, 2.5),
                                          3 * math.sin(TAU * 8 * t) * window(t, 1.15, 1.25, 1.45, 1.6)))
      .rot("jaw", [(0, ZERO), (0.35, v(4, 0, 0)), (1.2, v(46, 0, 0), "in"), (1.55, v(46, 0, 0)), (1.72, ZERO, "snap"), (2.8, ZERO)]),
      legs=planted, stabilise=None, tail_gain=0.5)
c.sound(0.6, "yawn")


# resting: legs fold on IK (feet slide under the body), body lowers to the ground, neck and tail curl to the left
REST_DROP = 18.5
REST_FEET = {"fl": v(0, 0, -6), "fr": v(0, 0, -6), "hl": v(0, 0, -10), "hr": v(0, 0, -10)}
REST_NECK = {"neck_1": v(30, -8, 0), "neck_2": v(10, -14, 0), "neck_3": v(-6, -14, 0), "neck_4": v(-10, -10, 0),
             "head": v(-18, -10, 6), "jaw": v(1, 0, 0)}
REST_TAIL = [v(12, 9, 0), v(8, 10, 0), v(2, 11, 0), v(-2, 12, 0), v(-3, 13, 0), v(-3, 14, 0), v(-2, 14, 0), v(-1, 14, 0)]
REST_WING = v(4, 0, 6)


def rest_pose(pose, k_body, k_front, k_hind, k_neck, k_tail):
    ground_base(pose, 0)
    apply_position(pose, "body", v(0, -REST_DROP * k_body, 0))
    apply_rotation(pose, "body", v(2 * k_body, 0, 0))
    for b, r in REST_NECK.items():
        apply_rotation(pose, b, r * k_neck)
    for b, r in zip(TAIL, REST_TAIL):
        apply_rotation(pose, b, r * k_tail)
    apply_rotation(pose, "wing_l_upper", REST_WING * k_body)
    apply_rotation(pose, "wing_r_upper", mirror_vec(REST_WING * k_body, "rotation"))


def rest_lower_k(t):
    return ramp(t, 0.25, 1.6, smoother), ramp(t, 0.45, 1.5), ramp(t, 0.15, 1.2), ramp(t, 0.6, 2.1), ramp(t, 0.8, 2.2)


c = clip("rest_lower", 2.2, loop="hold", category="A Living behaviour", priority=2,
         desc="lies down: hind legs fold first, then the forelegs, belly settles on the ground, neck and tail curl around to the left")
build(c, base=lambda p, t: rest_pose(p, *rest_lower_k(t)),
      legs=lambda k, t: (REST_FEET[k] * (rest_lower_k(t)[1] if k.startswith("f") else rest_lower_k(t)[2]), 0.0, 0.0),
      stabilise=None, tail=False)
c.sound(1.5, "land")

c = clip("rest_breathe", 5.0, loop=True, category="utility", priority=2, kind="additive",
         desc="(utility layer) slow deep breathing while lying down, a lazy tail-tip twitch")
c.set("chest", "scale", lambda t: v(1 + 0.04 * (0.5 - 0.5 * math.cos(TAU * t / 5)), 1 + 0.05 * (0.5 - 0.5 * math.cos(TAU * t / 5)), 1))
c.set("body", "position", lambda t: v(0, 0.3 * (0.5 - 0.5 * math.cos(TAU * t / 5)), 0))
c.set("head", "rotation", lambda t: v(-1.2 * (0.5 - 0.5 * math.cos(TAU * t / 5)), 0, 0))
c.set("tail_8", "rotation", lambda t: v(0, 9 * math.sin(math.pi * min(1, max(0, (t - 3.0) / 0.4))), 0))
c.set("tail_7", "rotation", lambda t: v(0, 5 * math.sin(math.pi * min(1, max(0, (t - 2.95) / 0.45))), 0))


def rest_rise_k(t):
    # (body, front, hind, neck, tail): neck first, forelegs push the chest up, hind legs follow, tail last
    return (1 - ramp(t, 0.3, 1.45, smoother), 1 - ramp(t, 0.35, 1.15), 1 - ramp(t, 0.65, 1.5), 1 - ramp(t, 0.0, 0.9),
            1 - ramp(t, 0.5, 1.8))


def rest_rise_legs(k, t):
    kb, kf, kh, _, _ = rest_rise_k(t)
    kk = kf if k.startswith("f") else kh
    lift = 5 * math.sin(math.pi * (1 - kk)) if 0 < kk < 1 else 0.0
    return (REST_FEET[k] * kk + v(0, lift, 0), 10 * math.sin(math.pi * (1 - kk)) if 0 < kk < 1 else 0.0, 0.0)


c = clip("rest_rise", 2.0, loop="hold", category="A Living behaviour", priority=2,
         desc="gets up: head lifts and the neck uncurls first, forelegs push the chest up, hind legs follow, tail uncurls last, shakes off")
build(c, base=lambda p, t: (rest_pose(p, *rest_rise_k(t)),
                            apply_rotation(p, "body", v(-6 * window(t, 0.3, 0.7, 0.9, 1.4), 0, 1.5 * math.sin(TAU * 5 * t) * window(t, 1.5, 1.6, 1.75, 2.0))),
                            unfold_delta(p, 0.08 * window(t, 1.5, 1.65, 1.75, 1.95))),
      legs=rest_rise_legs, stabilise=None, tail=False)
c.sound(0.4, "step")
c.sound(1.2, "step")
c.sound(1.6, "wing_unfold")


# ============================================================================= D. COMBAT AND REACTIONS (P3)

def wings_raise(pose, z, y=0.0, x=0.0):
    r = v(x, y, z)
    apply_rotation(pose, "wing_l_upper", r)
    apply_rotation(pose, "wing_r_upper", mirror_vec(r, "rotation"))


c = clip("alert", 1.4, category="D Combat and reactions", priority=3, kind="additive",
         desc="head snaps up toward the intruder, body tenses into a low crouch, shoulders and wings lift off the back, tail rises stiff, low growl")
build(c, base=lambda p, t: wings_raise(p, -8 * window(t, 0.05, 0.3, 1.1, 1.4), 0, -4 * window(t, 0.05, 0.3, 1.1, 1.4)),
      motion=Motion().pos("body", [(0, ZERO), (0.25, v(0, -1.5, 0.5), "out"), (1.1, v(0, -1.3, 0.5)), (1.4, ZERO)])
      .rot("body", [(0, ZERO), (0.25, v(-2, 0, 0), "out"), (1.1, v(-2, 0, 0)), (1.4, ZERO)])
      .cascade(TAIL, [(0, ZERO), (0.3, v(6, 0, 0), "out"), (1.1, v(5, 0, 0)), (1.4, ZERO)], [0.02 * i for i in range(8)],
               [1, 0.6, 0.4, 0.3, 0.3, 0.3, 0.3, 0.3])
      .rot("tail_8", [(0, ZERO), (0.25, ZERO), (0.32, v(0, 7, 0), "out"), (0.4, v(0, -6, 0)), (0.5, ZERO)]),
      head=Motion().rot("neck_1", [(0, ZERO), (0.18, v(-14, 0, 0), "snap"), (1.1, v(-13, 0, 0)), (1.4, ZERO)])
      .rot("neck_2", [(0, ZERO), (0.22, v(-6, 0, 0), "snap"), (1.1, v(-6, 0, 0)), (1.4, ZERO)])
      .rot("head", [(0, ZERO), (0.2, v(-6, 0, 0), "snap"), (0.3, v(-4, 0, 0)), (1.1, v(-5, 0, 0)), (1.4, ZERO)])
      .rot("jaw", [(0, ZERO), (0.2, v(8, 0, 0)), (1.0, v(6, 0, 0)), (1.4, ZERO)]),
      legs=planted, stabilise=None, tail_gain=0.8)
c.sound(0.15, "growl")


def roar_base(pose, t):
    a = wing_open(t, 0.1, 0.55, 1.75, 2.15, 0.45)
    b = wing_open(t, 0.55, 0.8, 1.6, 1.95, 0.35)
    unfold_delta(pose, a[0] + b[0], a[1] + b[1], a[2] + b[2])
    tremble = 2 * math.sin(TAU * 9 * t) * window(t, 0.8, 0.9, 1.6, 1.75)
    wings_raise(pose, -14 * ramp(t, 0.1, 0.55) - 14 * window(t, 0.55, 0.8, 1.7, 2.2) + 14 * ramp(t, 1.7, 2.3) + tremble)


c = clip("roar", 2.4, category="D Combat and reactions", priority=3, kind="additive",
         desc="anticipation: rears back and inhales (chest swells); action: thrusts forward, jaw wide, wings half-spread and trembling, head shake; recovery: settles")
build(c, base=roar_base,
      motion=Motion().rot("body", [(0, ZERO), (0.5, v(-6, 0, 0)), (0.8, v(2, 0, 0), "snap"), (1.7, v(2, 0, 0)), (2.4, ZERO)])
      .pos("body", [(0, ZERO), (0.5, v(0, 1, 2)), (0.8, v(0, 0, -1.5), "snap"), (1.7, v(0, 0, -1.5)), (2.4, ZERO)])
      .scl("chest", [(0, ONE), (0.5, v(1.05, 1.07, 1)), (0.9, ONE), (2.4, ONE)])
      .cascade(TAIL, [(0, ZERO), (0.6, v(5, 0, 0)), (1.2, v(7, 0, 0)), (2.4, ZERO)], [0.03 * i for i in range(8)],
               [1 - 0.08 * i for i in range(8)]),
      head=Motion().cascade(["neck_1", "neck_2", "neck_3"], [(0, ZERO), (0.5, v(-26, 0, 0)), (0.75, v(8, 0, 0), "snap"),
                                                             (1.6, v(6, 0, 0)), (2.3, ZERO)],
                            [0, 0.03, 0.06], [1, 0.4, 0.25])
      .rot("head", [(0, ZERO), (0.5, v(-20, 0, 0)), (0.75, v(-6, 0, 0), "snap"), (1.6, v(-8, 0, 0)), (2.3, ZERO)])
      .fn("neck_4", "rotation", lambda t: v(0, 5 * math.sin(TAU * 6 * t) * window(t, 0.78, 0.9, 1.5, 1.7) * (1.6 - t) / 0.8, 0))
      .rot("jaw", [(0, ZERO), (0.45, v(12, 0, 0)), (0.75, v(44, 0, 0), "snap"), (1.6, v(42, 0, 0)), (1.9, v(8, 0, 0)), (2.4, ZERO)]),
      legs=planted, stabilise=None, tail_gain=1.0)
c.sound(0.5, "roar")
c.sound(0.55, "roar_layer")
c.particle(0.8, "roar_breath", "mouth")

c = clip("bite", 0.95, category="D Combat and reactions", priority=3, kind="additive",
         desc="anticipation: coils the neck back, jaw opens, forelegs brace; action: accelerating lunge; impact 0.45 s: jaws snap with a shake; recovery: pulls back, overshoots, settles")
build(c, motion=Motion().pos("body", [(0, ZERO), (0.3, v(0, 0, 2)), (0.45, v(0, -1, -4), "in"), (0.7, v(0, 0, 0.6)), (0.95, ZERO)])
      .rot("body", [(0, ZERO), (0.3, v(-3, 0, 0)), (0.45, v(4, 0, 0), "in"), (0.7, v(-0.5, 0, 0)), (0.95, ZERO)]),
      head=Motion().cascade(["neck_1", "neck_2", "neck_3", "neck_4"],
                            [(0, ZERO), (0.3, v(-16, 0, 0)), (0.45, v(26, 0, 0), "in"), (0.62, v(22, 0, 0)), (0.75, v(-3, 0, 0)), (0.95, ZERO)],
                            [0, 0.01, 0.02, 0.03], [1, 0.55, 0.4, 0.2])
      .rot("head", [(0, ZERO), (0.3, v(-12, 0, 0)), (0.45, v(-6, 0, 0), "in"), (0.55, v(-2, 4, 0)), (0.62, v(-2, -3, 0)),
                    (0.7, v(-1, 1, 0)), (0.95, ZERO)])
      .rot("jaw", [(0, ZERO), (0.28, v(34, 0, 0), "out"), (0.42, v(30, 0, 0)), (0.47, ZERO, "snap"), (0.6, v(4, 0, 0)), (0.95, ZERO)]),
      legs=planted, stabilise=None, tail_gain=1.0)
c.sound(0.25, "growl")
c.sound(0.45, "bite")

CLAW_KEYS = Keys([(0, v(0, 0, 0)), (0.38, v(-3, 18, 5), "inout"), (0.55, v(5, 6, -11), "in"), (0.72, v(9, 4, -7), "out"),
                  (0.95, v(2, 5, -2)), (1.15, v(0, 0, 0), "inout")])
CLAW_PITCH = Keys([(0, 0), (0.38, -20), (0.55, 12, "in"), (0.75, 6), (1.15, 0)])
CLAW_TOE = Keys([(0, 0), (0.38, -15), (0.55, 14, "snap"), (0.8, 6), (1.15, 0)])
c = clip("claw_swipe", 1.15, category="D Combat and reactions", priority=3, kind="additive",
         desc="anticipation: rears and loads onto the left, right foreleg cocked high; action: raking swipe across; impact 0.55 s; follow-through and twist; recovery: foot replanted")
build(c, motion=Motion().rot("body", [(0, ZERO), (0.38, v(-7, 0, 3)), (0.55, v(2, 0, 1), "in"), (0.75, v(0, 0, 0.5)), (1.15, ZERO)])
      .pos("body", [(0, ZERO), (0.38, v(1.5, 2, 1)), (0.6, v(0.5, 0, -2)), (1.15, ZERO)])
      .rot("chest", [(0, ZERO), (0.38, v(0, 6, 0)), (0.55, v(0, -10, 0), "in"), (0.75, v(0, -8, 0)), (1.15, ZERO)]),
      head=Motion().rot("neck_1", [(0, ZERO), (0.38, v(-8, 6, 0)), (0.55, v(8, -6, 0), "in"), (1.15, ZERO)])
      .rot("head", [(0, ZERO), (0.38, v(-4, 8, 0)), (0.55, v(4, -6, 0), "in"), (1.15, ZERO)])
      .rot("jaw", [(0, ZERO), (0.35, v(14, 0, 0)), (0.6, v(20, 0, 0)), (0.9, v(4, 0, 0)), (1.15, ZERO)]),
      legs=lambda k, t: (CLAW_KEYS(t), float(CLAW_PITCH(t)), float(CLAW_TOE(t))) if k == "fr" else planted(k, t),
      stabilise=None, tail_gain=1.0)
c.sound(0.4, "swipe")
c.particle(0.55, "claw_slash", "claw_fr")


def tail_smash_motion():
    m = Motion()
    m.rot("pelvis", [(0, ZERO), (0.45, v(0, -14, 0)), (0.72, v(0, 18, 0), "in"), (1.0, v(0, 6, 0)), (1.35, ZERO)])
    m.rot("body", [(0, ZERO), (0.45, v(0, -10, 2)), (0.72, v(0, 12, -2), "in"), (1.0, v(0, 4, 0)), (1.35, ZERO)])
    m.rot("chest", [(0, ZERO), (0.45, v(0, 6, 0)), (0.72, v(0, -6, 0)), (1.35, ZERO)])
    for i, tb in enumerate(TAIL):
        wind = 9 + i * 1.5
        sweep = -(18 + i * 2.5)
        d = 0.012 * i  # the tip arrives last: whip
        m.rot(tb, [(0, ZERO), (0.45 + d * 0.5, v(4 + i, wind, 0)), (0.62 + d, v(-2, sweep * 0.6, 0), "in"),
                   (0.72 + d, v(-(5 + i * 0.5), sweep, 0), "in"), (0.86 + d, v(-2, sweep * 1.12, 0), "out"),
                   (1.05 + d, v(0, sweep * 0.55, 0)), (1.35, ZERO, "inout")])
    return m


c = clip("tail_smash", 1.35, category="D Combat and reactions", priority=3, kind="additive",
         desc="anticipation: body winds up and the tail coils high to one side, looks back; action: whip across the rear arc (tip lags the base); impact 0.72 s slam; follow-through overshoot, settle")
build(c, motion=tail_smash_motion(),
      head=Motion().rot("neck_1", [(0, ZERO), (0.45, v(-6, 22, 0)), (0.72, v(-4, 26, 0)), (1.0, v(0, 10, 0)), (1.35, ZERO)])
      .rot("head", [(0, ZERO), (0.45, v(0, 16, 0)), (0.72, v(0, 18, 0)), (1.35, ZERO)])
      .rot("jaw", [(0, ZERO), (0.6, v(10, 0, 0)), (0.75, v(18, 0, 0)), (1.35, ZERO)]),
      legs=planted, stabilise=None, tail=False)
c.sound(0.5, "swipe")
c.sound(0.72, "tail_slam")
c.particle(0.72, "dust_ring", "tail_tip")


def buffet_base(pose, t):
    unfold_delta(pose, *wing_open(t, 0.05, 0.4, 1.02, 1.3, 1.0, 0.06))
    z = Keys([(0, 0), (0.45, -60), (0.7, 10, "in"), (0.85, -30), (1.0, 4, "in"), (1.45, 0)])(t)[()]
    y = Keys([(0, 0), (0.45, -14), (0.7, 38, "in"), (0.85, 20), (1.0, 30), (1.45, 0)])(t)[()]
    wings_raise(pose, z, y)
    lag = Keys([(0, 0), (0.45, 0), (0.62, 18), (0.78, -10), (0.95, 10), (1.1, 0)])(t)[()]
    for b in ("wing_l_fore", "wing_l_hand"):
        apply_rotation(pose, b, v(0, 0, lag * (0.6 if "fore" in b else 1.0)))
        apply_rotation(pose, right_of(b), mirror_vec(v(0, 0, lag * (0.6 if "fore" in b else 1.0)), "rotation"))


BUFFET_FRONT = Keys([(0, v(0, 0, 0)), (0.35, v(0, 14, -2), "out"), (0.9, v(0, 14, -2)), (1.15, v(0, 0, -1), "in"), (1.45, v(0, 0, 0))])
c = clip("wing_buffet", 1.45, category="D Combat and reactions", priority=3, kind="additive",
         desc="anticipation: rears onto the hind legs, wings open fully and cock high and back; action: massive forward sweep; impact 0.7 s gust; second beat; forefeet land, wings fold")
build(c, base=buffet_base,
      motion=Motion().rot("body", [(0, ZERO), (0.45, v(-18, 0, 0)), (0.7, v(-8, 0, 0)), (1.05, v(-10, 0, 0)), (1.2, v(1, 0, 0), "in"), (1.45, ZERO)])
      .pos("body", [(0, ZERO), (0.45, v(0, 6, 2)), (0.7, v(0, 3, 0)), (1.15, v(0, -1.5, 0), "in"), (1.45, ZERO)]),
      head=Motion().rot("neck_1", [(0, ZERO), (0.45, v(-18, 0, 0)), (0.7, v(6, 0, 0), "in"), (1.45, ZERO)])
      .rot("head", [(0, ZERO), (0.45, v(-6, 0, 0)), (0.7, v(10, 0, 0)), (1.45, ZERO)])
      .rot("jaw", [(0, ZERO), (0.6, v(26, 0, 0)), (0.9, v(20, 0, 0)), (1.45, ZERO)]),
      legs=lambda k, t: ((BUFFET_FRONT(t), -12 * window(t, 0.2, 0.4, 0.9, 1.1), 10 * window(t, 0.2, 0.4, 0.9, 1.1))
                         if k.startswith("f") else planted(k, t)),
      stabilise=None, tail_gain=1.2)
c.sound(0.3, "wing_unfold")
c.sound(0.62, "buffet")
c.sound(1.15, "step")
c.particle(0.7, "wind_burst", "chest_front")
c.particle(0.7, "dust_ring", "ground")

CHARGE = {"neck_1": v(-22, 0, 0), "neck_2": v(-10, 0, 0), "neck_3": v(-4, 0, 0), "neck_4": v(2, 0, 0), "head": v(-14, 0, 0)}
c = clip("fire_breath_charge", 1.3, loop="hold", category="D Combat and reactions", priority=3, kind="additive",
         desc="building tension: neck coils into an S, chest swells, jaw cracks open with a glow, head trembles harder and harder, tail lashes")
head = Motion()
for i, (b, r) in enumerate(CHARGE.items()):
    head.rot(b, [(0, ZERO), (0.6 + 0.04 * i, r * 0.8), (1.3, r)])
head.rot("jaw", [(0, ZERO), (0.5, v(6, 0, 0)), (1.3, v(10, 0, 0))])
head.fn("head", "rotation", lambda t: v(0.6 * math.sin(TAU * 18 * t) * ramp(t, 0.4, 1.3), 0.5 * math.sin(TAU * 15 * t) * ramp(t, 0.5, 1.3), 0))
build(c, base=lambda p, t: wings_raise(p, -6 * ramp(t, 0.2, 0.9)),
      motion=Motion().scl("chest", [(0, ONE), (1.3, v(1.07, 1.09, 1.02))]).rot("body", [(0, ZERO), (1.3, v(-4, 0, 0))])
      .pos("body", [(0, ZERO), (1.3, v(0, 0, 1))])
      .fn("tail_6", "rotation", lambda t: v(0, 6 * math.sin(TAU * 1.6 * t) * ramp(t, 0.2, 0.8), 0))
      .fn("tail_8", "rotation", lambda t: v(0, 10 * math.sin(TAU * 1.6 * t - 0.8) * ramp(t, 0.2, 0.8), 0)),
      head=head, legs=planted, stabilise=None, tail_gain=0.8)
c.sound(0.0, "fire_charge")
c.sound(0.1, "fire_charge_layer")
c.particle(0.0, "fire_charge_glow", "mouth")
c.particle(0.0, "fire_charge_core", "mouth")
for tt in (0.15, 0.7):
    c.particle(tt, "nostril_smoke", "nostril_l")
    c.particle(tt, "nostril_smoke", "nostril_r")

# release: neck_2..head stay Molang because the aim (dod:aim, degrees, + = down) is only known at run time
BREATH = {"neck_2": 6.0, "neck_3": 4.0, "neck_4": 2.0, "head": -21.3}
AIM_K = {"neck_2": 0.25, "neck_3": 0.25, "neck_4": 0.2, "head": 0.3}
SWEEP = {"neck_2": 2.5, "neck_3": 2.0, "neck_4": 1.5, "head": 2.0}
AIM = "math.clamp(q.property('dod:aim'), -45, 60)"
BL = 3.2
c = clip("fire_breath_release", BL, loop="hold", category="D Combat and reactions", priority=3, kind="additive",
         desc="the neck whips forward (overshoot), jaw slams open, a sustained jet with recoil shudder and a slow sweep; aim pitch from the server; flame geometry grows out of the mouth")
build(c, base=lambda p, t: wings_raise(p, -10 * ramp(t, 0.0, 0.3), 4 * ramp(t, 0, 0.3)),
      motion=Motion().rot("body", [(0, ZERO), (0.15, v(-3, 0, 0), "out"), (BL, v(-2, 0, 0))])
      .fn("chest", "position", lambda t: v(0, 0, 1.2 * ramp(t, 0, 0.15) + 0.25 * math.sin(TAU * 17 * t) * ramp(t, 0.1, 0.3)))
      .scl("chest", [(0, v(1.07, 1.09, 1.02)), (0.5, v(1.02, 1.03, 1)), (BL, v(0.98, 0.98, 1))])
      .rot("neck_1", [(0, v(-12, 0, 0)), (0.12, v(16, 0, 0), "out"), (0.32, v(10, 0, 0)), (BL, v(10, 0, 0))])
      .rot("jaw", [(0, v(10, 0, 0)), (0.12, v(40, 0, 0), "snap"), (0.4, v(36, 0, 0)), (BL, v(36, 0, 0))]),
      legs=planted, stabilise=None, tail_gain=0.8)
for b in BREATH:
    over = "(q.anim_time < 0.4 ? math.sin(q.anim_time * 450) * 5 * (1 - q.anim_time / 0.4) : 0)"
    c.molang[(b, "rotation")] = [f"{BREATH[b]} + {AIM} * {AIM_K[b]} + {over} * {AIM_K[b] * 3:.2f}",
                                 f"math.sin(q.anim_time * 140) * {SWEEP[b]}", 0]
GROW = "math.min(q.anim_time * 4, 1)"
c.molang[("fire_jet", "scale")] = [f"0.25 + 0.75 * {GROW}", f"0.25 + 0.75 * {GROW}",
                                   f"math.max(0.02, {GROW} * math.clamp(q.property('dod:jet') / 12, 0.08, 1))"]
for i in range(8):
    c.molang[(f"fire_s{i + 1}", "scale")] = [f"1 + math.sin(q.anim_time * {1500 + i * 210} + {i * 57}) * 0.16",
                                             f"1 + math.sin(q.anim_time * {1300 + i * 170} + {i * 91}) * 0.16",
                                             f"1 + math.sin(q.anim_time * {900 + i * 130} + {i * 33}) * 0.08"]
    c.molang[(f"fire_s{i + 1}", "rotation")] = [f"math.sin(q.anim_time * {700 + i * 90}) * {1 + i * 0.5}",
                                                f"math.sin(q.anim_time * {610 + i * 80} + 40) * {1 + i * 0.5}",
                                                f"q.anim_time * {200 + i * 40}"]
c.molang[("fire_mouth", "scale")] = ["1 + math.sin(q.anim_time * 2500) * 0.25"] * 3
for tt in (0.0, 0.8, 1.6, 2.4):
    c.particle(tt, "fire_mouth_burst", "mouth")
c.sound(0.0, "fire_breath")

c = clip("hurt", 0.5, category="D Combat and reactions", priority=3, kind="additive",
         desc="flinch: head jerks away and the body recoils in 0.06 s on planted feet, wings and tail twitch, everything settles back with a damped wobble")
m = Motion().rot("neck_1", [(0, ZERO), (0.06, v(-10, 4, 0), "snap"), (0.5, ZERO, "settle")]) \
    .rot("head", [(0, ZERO), (0.06, v(-8, 8, -6), "snap"), (0.5, ZERO, "settle")]) \
    .rot("jaw", [(0, ZERO), (0.07, v(16, 0, 0), "snap"), (0.3, v(4, 0, 0)), (0.5, ZERO)]) \
    .pos("body", [(0, ZERO), (0.07, v(0, -1.5, 1.5), "snap"), (0.5, ZERO, "settle")]) \
    .rot("body", [(0, ZERO), (0.07, v(-3, 0, 2), "snap"), (0.5, ZERO, "settle")]) \
    .rot("wing_l_upper", [(0, ZERO), (0.09, v(0, 0, -6), "snap"), (0.5, ZERO, "settle")], mirror=True)
for i, tb in enumerate(TAIL[:6]):
    m.rot(tb, [(0, ZERO), (0.08 + 0.02 * i, v(0, 4 + i, 0), "snap"), (0.5, ZERO, "settle")])
build(c, motion=m, legs=planted, stabilise=None, tail=False)


# ----------------------------------------------------------------------------- death (absolute, improved)

def death_base(pose, t):
    ground_base(pose, t)
    kl = 0.55 * ramp(t, 0.5, 1.6) - 0.05 * ramp(t, 1.6, 2.4)   # left wing sprawls open and drapes
    kr = 0.35 * ramp(t, 0.6, 1.5)                             # right wing half open, pinned
    unfold_delta(pose, kl, kl, kl * 0.9, side="l")
    unfold_delta(pose, kr, kr, kr, side="r")
    apply_rotation(pose, "wing_l_upper", v(0, -10 * ramp(t, 0.8, 1.6), -25 * window(t, 0.3, 0.6, 0.8, 1.3) + 34 * ramp(t, 1.3, 2.0)))
    apply_rotation(pose, "wing_r_upper", mirror_vec(v(0, 0, 6 * ramp(t, 1.0, 1.8)), "rotation"))


DEATH_LEGS = {
    "leg_fl_upper": [(0, ZERO), (0.4, v(-8, 0, 0)), (0.9, v(30, 0, -6)), (1.4, v(66, 0, -14)), (3.2, v(70, 0, -16))],
    "leg_fl_lower": [(0, ZERO), (0.9, v(-40, 0, 0)), (1.4, v(-92, 0, 0)), (3.2, v(-95, 0, 0))],
    "foot_fl": [(0, ZERO), (1.4, v(30, 0, 0)), (3.2, v(30, 0, 0))],
    "leg_fr_upper": [(0, ZERO), (0.5, v(14, 0, 4)), (0.75, v(40, 0, 6), "in"), (1.3, v(62, 0, 10)), (3.2, v(66, 0, 12))],
    "leg_fr_lower": [(0, ZERO), (0.5, v(-30, 0, 0)), (0.75, v(-70, 0, 0), "in"), (1.3, v(-95, 0, 0)), (3.2, v(-95, 0, 0))],
    "leg_hl_thigh": [(0, ZERO), (1.0, v(-20, 0, -8)), (1.7, v(-40, 0, -18)), (3.2, v(-42, 0, -18))],
    "leg_hl_shin": [(0, ZERO), (1.7, v(40, 0, 0)), (3.2, v(42, 0, 0))],
    "leg_hl_meta": [(0, ZERO), (1.7, v(-30, 0, 0)), (3.2, v(-30, 0, 0))],
    "leg_hr_thigh": [(0, ZERO), (1.1, v(-16, 0, 6)), (1.8, v(-36, 0, 12)), (3.2, v(-38, 0, 12))],
    "leg_hr_shin": [(0, ZERO), (1.8, v(36, 0, 0)), (3.2, v(38, 0, 0))],
    "leg_hr_meta": [(0, ZERO), (1.8, v(-26, 0, 0)), (3.2, v(-26, 0, 0))],
}
m = Motion()
for b, ks in DEATH_LEGS.items():
    m.rot(b, ks)
m.pos("root", [(0, ZERO), (0.45, v(0, 0.5, 0)), (0.9, v(0, -4, 0)), (1.25, v(0, -9, 0), "in"), (1.7, v(0, -13, 0), "in"),
               (1.85, v(0, -12, 0), "out"), (2.1, v(0, -13, 0)), (3.2, v(0, -13, 0))])
m.rot("root", [(0, ZERO), (0.25, v(0, 0, 4)), (0.5, v(-4, 0, -3)), (0.9, v(4, 0, -2)), (1.4, v(2, 0, -5), "in"),
               (1.75, v(0, 0, -6)), (2.0, v(0, 0, -4.5)), (3.2, v(0, 0, -5))])
m.scl("chest", [(0, ONE), (2.5, ONE), (2.7, v(1.03, 1.04, 1)), (3.1, v(0.97, 0.97, 1)), (3.2, v(0.97, 0.97, 1))])
for i, tb in enumerate(TAIL):
    m.rot(tb, [(0, ZERO), (0.6 + 0.03 * i, v(5, 0, 0)), (1.75 + 0.05 * i, v((12, 10, 4, -2, -6, -6, -4, -2)[i], 5 + i, 0), "in"),
               (2.1 + 0.05 * i, v((12, 10, 4, -2, -6, -6, -4, -2)[i] + 3, 7 + i, 0)), (3.2, v((12, 10, 4, -2, -6, -6, -4, -2)[i], 6 + i, 0))])
c = clip("death", 3.2, loop="hold", category="D Combat and reactions", priority=3,
         desc="(existing, improved) staggers in pain, a foreleg buckles, chest drops, rolls onto the side, wings sprawl, the head hits the ground and bounces, tail flops, last breath")
build(c, base=death_base, motion=m,
      head=Motion().rot("neck_1", [(0, ZERO), (0.4, v(-24, 0, 0)), (0.8, v(-26, 6, 0)), (1.4, v(22, 10, 0), "in"), (1.8, v(30, 12, 0)),
                                   (3.2, v(30, 12, 0))])
      .rot("neck_2", [(0, ZERO), (0.4, v(-10, 0, 0)), (1.4, v(10, 8, 0)), (1.8, v(12, 8, 0)), (3.2, v(12, 8, 0))])
      .rot("neck_3", [(0, ZERO), (1.4, v(2, 8, 0)), (1.8, v(-4, 8, 0)), (3.2, v(-4, 8, 0))])
      .rot("neck_4", [(0, ZERO), (1.8, v(-10, 4, 0)), (3.2, v(-10, 4, 0))])
      .rot("head", [(0, ZERO), (0.4, v(-20, 0, 0)), (1.4, v(-6, 0, 10)), (1.78, v(-22, 0, 20), "in"), (1.9, v(-15, 0, 18), "out"),
                    (2.05, v(-19, 0, 20)), (3.2, v(-18, 0, 20))])
      .rot("jaw", [(0, ZERO), (0.4, v(36, 0, 0)), (1.0, v(30, 0, 0)), (1.8, v(14, 0, 0)), (3.2, v(16, 0, 0))])
      .rot("eyelid_l", [(0, ZERO), (2.6, ZERO), (3.1, v(0, 0, -70))], mirror=True),
      stabilise=None, tail_gain=0.6)
c.sound(0.35, "death")
c.particle(1.75, "dust_ring", "ground")
c.particle(1.8, "death_embers", "chest_front")

# ----------------------------------------------------------------------------- utility: head tracking (Molang, cheap)
LOOK = {"neck_2": 0.22, "neck_3": 0.24, "neck_4": 0.22, "head": 0.32}


# ============================================================================= controllers

F = "q.property('dod:flight')"
A = "q.property('dod:action')"
I = "q.property('dod:idle')"
DEAD = f"{A} == 'death' || !q.is_alive"
AIR = {"pre_takeoff": f"{F} == 'takeoff'", "launch": f"{F} == 'launch'", "fly": f"{F} == 'fly'", "glide": f"{F} == 'glide'",
       "landing": f"{F} == 'landing'", "touchdown": f"{F} == 'touchdown'"}
GROUND = f"{F} == 'ground'"
MOVING = "v.spd > 0.45"
STILL = "v.spd < 0.3"
RUN_ON = "q.property('dod:run')"


def tr(*pairs):
    return [{k: v_} for k, v_ in pairs]


def ground_state(anims, extra, blend):
    return {"animations": anims, "transitions": tr(("dead", DEAD), *AIR.items(), *extra), "blend_transition": blend}


def ctrl_move():
    st = {
        "idle": ground_state(["idle_breathe"], [("rest", f"{I} == 'rest'"), ("step_back", f"{A} == 'step_back'"),
                                                 ("run_start", f"{MOVING} && {RUN_ON}"), ("walk_start", MOVING),
                                                 ("turn_left", "v.turn < -25"), ("turn_right", "v.turn > 25")], 0.3),
        "walk_start": ground_state(["walk_start"], [("walk_stop", STILL), ("run_start", f"{RUN_ON} && v.spd > 1.6"),
                                                    ("walk", "q.all_animations_finished")], 0.2),
        "walk": ground_state(["walk_loop"], [("walk_stop", STILL), ("run_start", f"{RUN_ON} && v.spd > 1.6"),
                                             ("step_back", f"{A} == 'step_back'")], 0.25),
        "walk_stop": ground_state(["walk_stop"], [("walk_start", "v.spd > 0.6"), ("idle", "q.all_animations_finished")], 0.3),
        "run_start": ground_state(["run_start"], [("run_stop", "v.spd < 0.5"), ("run", "q.all_animations_finished")], 0.2),
        "run": ground_state(["run_loop"], [("run_stop", f"v.spd < 0.9 || !{RUN_ON}")], 0.25),
        "run_stop": ground_state(["run_stop"], [("run_start", f"{RUN_ON} && v.spd > 2.0"),
                                                ("walk", f"q.all_animations_finished && v.spd >= 0.45"),
                                                ("idle", "q.all_animations_finished && v.spd < 0.45")], 0.3),
        "turn_left": ground_state(["turn_left"], [("walk_start", "v.spd > 0.6"), ("turn_right", "v.turn > 25"),
                                                  ("idle", "v.turn > -10")], 0.3),
        "turn_right": ground_state(["turn_right"], [("walk_start", "v.spd > 0.6"), ("turn_left", "v.turn < -25"),
                                                    ("idle", "v.turn < 10")], 0.3),
        "step_back": ground_state(["step_backward"], [("idle", f"{A} != 'step_back'")], 0.3),
        "rest": ground_state(["rest_lower", "rest_breathe"], [("rest_rise", f"{I} != 'rest'")], 0.4),
        "rest_rise": ground_state(["rest_rise"], [("rest", f"{I} == 'rest'"), ("idle", "q.all_animations_finished")], 0.35),
        "pre_takeoff": {"animations": ["pre_takeoff"], "transitions": tr(("dead", DEAD), ("launch", AIR["launch"]),
                        ("fly", AIR["fly"]), ("glide", AIR["glide"]), ("idle", GROUND)), "blend_transition": 0.15},
        "launch": {"animations": ["launch"], "transitions": tr(("dead", DEAD), ("fly", AIR["fly"]), ("glide", AIR["glide"]),
                   ("landing", AIR["landing"]), ("idle", GROUND)), "blend_transition": 0.2},
        "fly": {"animations": [{"flight_flap": "1.0 - v.climb"}, {"flight_ascend": "v.climb"},
                               {"flight_bank_left": "v.bank_l"}, {"flight_bank_right": "v.bank_r"}],
                "transitions": tr(("dead", DEAD), ("glide", AIR["glide"]), ("landing", AIR["landing"]),
                                  ("touchdown", AIR["touchdown"]), ("pre_takeoff", AIR["pre_takeoff"]), ("idle", GROUND)),
                "blend_transition": 0.4},
        "glide": {"animations": [{"flight_glide": "1.0 - v.dive"}, {"flight_descend": "v.dive"},
                                 {"flight_bank_left": "v.bank_l"}, {"flight_bank_right": "v.bank_r"}],
                  "transitions": tr(("dead", DEAD), ("fly", AIR["fly"]), ("landing", AIR["landing"]),
                                    ("touchdown", AIR["touchdown"]), ("pre_takeoff", AIR["pre_takeoff"]), ("idle", GROUND)),
                  "blend_transition": 0.5},
        "landing": {"animations": ["landing_approach"], "transitions": tr(("dead", DEAD), ("touchdown", AIR["touchdown"]),
                    ("fly", AIR["fly"]), ("glide", AIR["glide"]), ("idle", GROUND)), "blend_transition": 0.2},
        "touchdown": {"animations": ["landing_impact"], "transitions": tr(("dead", DEAD), ("pre_takeoff", AIR["pre_takeoff"]),
                      ("fly", AIR["fly"]), ("idle", GROUND)), "blend_transition": 0.35},
        "dead": {"animations": ["death"], "transitions": tr(("idle", f"{A} != 'death' && q.is_alive")), "blend_transition": 0.25},
    }
    return {"initial_state": "idle", "states": st}


IDLE_ACTIONS = {"look_left": "idle_look_left", "look_right": "idle_look_right", "sniff": "idle_sniff",
                "scratch": "idle_ground_scratch", "tail_sway": "idle_tail_sway", "wing_adjust": "idle_wing_adjust",
                "stretch": "idle_stretch", "yawn": "idle_yawn"}
COMBAT_ACTIONS = {"alert": "alert", "roar": "roar", "bite": "bite", "claw": "claw_swipe", "tail": "tail_smash",
                  "buffet": "wing_buffet", "fire_charge": "fire_breath_charge", "fire_breath": "fire_breath_release"}


def ctrl_overlay(prop, table, gate, blend):
    states = {"default": {"transitions": [{k: f"{prop} == '{k}' && {gate}"} for k in table], "blend_transition": blend}}
    for k, anim in table.items():
        trs = [{o: f"{prop} == '{o}'"} for o in table if o != k]
        trs.append({"default": f"{prop} != '{k}'"})
        states[k] = {"animations": [anim], "transitions": trs, "blend_transition": blend}
    return {"initial_state": "default", "states": states}


def ctrl_look():
    on = f"({A} == 'none' || {A} == 'alert') && {I} == 'none' && {F} == 'ground' && q.is_alive"
    return {"initial_state": "on", "states": {
        "on": {"animations": ["look_at_target"], "transitions": [{"off": f"!({on})"}], "blend_transition": 0.4},
        "off": {"transitions": [{"on": on}], "blend_transition": 0.4}}}


def ctrl_blink():
    ok = f"v.blink && {I} != 'yawn' && {I} != 'rest' && {I} != 'rise' && q.is_alive"
    return {"initial_state": "open", "states": {
        "open": {"transitions": [{"blink": ok}]},
        "blink": {"animations": ["idle_blink"], "transitions": [{"open": "q.all_animations_finished && !v.blink"}],
                  "blend_transition": 0.05}}}


def ctrl_hurt():
    return {"initial_state": "default", "states": {
        "default": {"transitions": [{"hurt": "q.hurt_time > 0 && q.is_alive"}]},
        "hurt": {"animations": ["hurt"], "transitions": [{"default": "q.all_animations_finished"}], "blend_transition": 0.12}}}


CONTROLLERS = {
    "controller.animation.dod.red_dragon.move": ctrl_move(),
    "controller.animation.dod.red_dragon.idle": ctrl_overlay(I, IDLE_ACTIONS, f"{F} == 'ground'", 0.3),
    "controller.animation.dod.red_dragon.action": ctrl_overlay(A, COMBAT_ACTIONS, "q.is_alive", 0.18),
    "controller.animation.dod.red_dragon.look": ctrl_look(),
    "controller.animation.dod.red_dragon.blink": ctrl_blink(),
    "controller.animation.dod.red_dragon.hurt": ctrl_hurt(),
}

PRE_ANIMATION = [
    "v.spd = math.lerp(v.spd ?? 0.0, q.ground_speed, math.min(1.0, q.delta_time * 8.0));",
    "v.yaw_d = q.body_y_rotation - (v.last_yaw ?? q.body_y_rotation);",
    "v.yaw_d = v.yaw_d > 180 ? v.yaw_d - 360 : (v.yaw_d < -180 ? v.yaw_d + 360 : v.yaw_d);",
    "v.last_yaw = q.body_y_rotation;",
    "v.turn = math.lerp(v.turn ?? 0.0, v.yaw_d / math.max(q.delta_time, 0.016), math.min(1.0, q.delta_time * 6.0));",
    "v.vy = math.lerp(v.vy ?? 0.0, q.vertical_speed, math.min(1.0, q.delta_time * 4.0));",
    "v.climb = math.clamp((v.vy - 1.5) / 3.0, 0.0, 1.0);",
    "v.dive = math.clamp((-v.vy - 1.5) / 4.0, 0.0, 1.0);",
    "v.bank_l = math.clamp(-v.turn / 70.0, 0.0, 1.0);",
    "v.bank_r = math.clamp(v.turn / 70.0, 0.0, 1.0);",
    "v.blink_seed = v.blink_seed ?? math.random(0.0, 10.0);",
    "v.blink = math.mod(q.life_time + v.blink_seed, 4.3) < 0.12 || math.mod(q.life_time * 1.13 + v.blink_seed * 1.7, 6.9) < 0.12;",
]


# ============================================================================= output

def preview_specs():
    specs = []
    order = ["idle_breathe", "idle_look_left", "idle_look_right", "idle_sniff", "idle_blink", "idle_ground_scratch",
             "idle_tail_sway", "idle_wing_adjust", "idle_stretch", "idle_yawn", "rest_lower", "rest_rise",
             "walk_start", "walk_loop", "walk_stop", "run_start", "run_loop", "run_stop", "turn_left", "turn_right",
             "step_backward", "pre_takeoff", "launch", "flight_flap", "flight_glide", "flight_bank_left",
             "flight_bank_right", "flight_ascend", "flight_descend", "landing_approach", "landing_impact",
             "alert", "roar", "bite", "claw_swipe", "tail_smash", "wing_buffet", "fire_breath_charge",
             "fire_breath_release", "hurt", "death", "rest_breathe"]
    for i, n in enumerate(order, start=1):
        meta = META[n]
        pv = dict(meta["preview"])
        layers = [[n, 1.0]]
        if meta["kind"] == "additive":
            layers = [[pv.pop("base", "rest_lower" if n == "rest_breathe" else "idle_breathe"), 1.0], [n, 1.0]]
            if n == "idle_blink":
                pv["target"], pv["scale"] = (0, 58, -100), 4.0
        spec = {"name": n, "title": f"{i if i <= 41 else '-'}. {n}" if n != "rest_breathe" else "utility: rest_breathe",
                "layers": layers, **pv}
        if meta["kind"] == "additive" and n not in ("flight_bank_left", "flight_bank_right"):
            spec["length"] = CLIPS[n].length
        if n in ("flight_bank_left", "flight_bank_right"):
            spec["length"] = 2.0
        if n == "idle_blink":
            spec["length"] = 0.6
        if n == "fire_breath_release":
            spec["fire"] = True
            spec["env"] = {"prop:dod:aim": 0, "prop:dod:jet": 12}
            spec["layers"] = [["idle_breathe", 1.0], ["fire_breath_charge", 0.0], [n, 1.0]]
        if n == "rest_breathe":
            spec["length"] = 5.0
        specs.append(spec)
    return specs


def look_at_target():
    bones = {}
    for b, k in LOOK.items():
        bones[b] = {"rotation": [f"math.clamp(q.target_x_rotation, -45, 45) * {k}",
                                 f"math.clamp(q.target_y_rotation, -70, 70) * {k}", 0]}
    return {"loop": True, "animation_length": 1.0, "bones": bones}


def main():
    anims = {}
    for n, cl in CLIPS.items():
        anims[P + n] = cl.bake()
    anims[P + "look_at_target"] = look_at_target()
    os.makedirs(os.path.join(RP, "animations"), exist_ok=True)
    with open(os.path.join(RP, "animations", "red_dragon.animation.json"), "w") as f:
        json.dump({"format_version": "1.10.0", "animations": anims}, f, separators=(",", ":"))
        f.write("\n")
    with open(os.path.join(RP, "animation_controllers", "red_dragon.animation_controllers.json"), "w") as f:
        json.dump({"format_version": "1.10.0", "animation_controllers": CONTROLLERS}, f, indent=1)
        f.write("\n")
    with open(os.path.join(ROOT, "tools", "preview_spec.json"), "w") as f:
        json.dump(preview_specs(), f, indent=1)
    report = {n: {**{k: x for k, x in META[n].items() if k != "preview"}, "length": CLIPS[n].length,
                  "loop": CLIPS[n].loop, "speed_synced": bool(CLIPS[n].atu)} for n in CLIPS}
    with open(os.path.join(ROOT, "tools", "anim_report.json"), "w") as f:
        json.dump(report, f, indent=1)
    sounds = sorted({snd for cl in CLIPS.values() for snd in cl.sounds.values()})
    parts = sorted({eff for cl in CLIPS.values() for _, eff, _ in cl.particles})
    with open(os.path.join(ROOT, "tools", "anim_manifest.json"), "w") as f:
        json.dump({"animations": sorted(anims), "controllers": sorted(CONTROLLERS), "pre_animation": PRE_ANIMATION,
                   "sound_keys": sounds, "particle_keys": parts,
                   "idle_actions": list(IDLE_ACTIONS), "combat_actions": list(COMBAT_ACTIONS)}, f, indent=1)
    counted = [n for n in CLIPS if META[n]["category"] != "utility"]
    nkeys = sum(len(ch) if isinstance(ch, dict) else 1 for a in anims.values() for b in a["bones"].values() for ch in b.values())
    print(f"{len(counted)} animations (+{len(anims) - len(counted)} utility layers), {nkeys} channels/keys, "
          f"{len(CONTROLLERS)} controllers")


if __name__ == "__main__":
    main()
