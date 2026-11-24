"""
Animation authoring for Joan of Arc and the minor entities.

Actions are authored as key poses on a 20 fps timeline:
  * body joints in Bedrock euler degrees (see modelkit for the convention)
  * the war banner as a WORLD orientation (pole axis + cloth side), solved
    every frame into the banner bone's local rotation
  * optional two-handed grip: the left hand is IK-solved onto the pole
  * optional root motion (lunges, kneels, hovering)
The cloth (6 bones), the mantle (2 bones) are then simulated as Verlet chains
driven by the animated skeleton plus an assumed travel velocity, and baked.

Output: Bedrock animation JSON, the property-driven action controller, and
src/generated/anims.ts (action ids / lengths shared with the scripts).
"""
from __future__ import annotations

import json
import math
import os
import sys
from typing import Callable, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import models  # noqa: E402
from modelkit import v_norm  # noqa: E402
from rig import Chain, Pose, Rig, set_rot  # noqa: E402

FPS = 20
DT = 1.0 / FPS
BODY = ["root", "hips", "torso", "head", "arm_r", "forearm_r", "hand_r", "arm_l", "forearm_l", "hand_l",
        "leg_r", "shin_r", "leg_l", "shin_l"]
CLOTH = [f"cloth_{i}" for i in range(6)]
CAPE = ["cape", "cape_lower"]

FWD, BACK, RIGHT, LEFT, UP = (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0), (0, 1, 0)


def d(*v):
    return v_norm(tuple(float(x) for x in v))


# =========================================================================== key poses
GUARD = {
    "torso": (3, -10, 0), "head": (-3, 9, 0),
    "arm_r": (-14, 0, 26), "forearm_r": (-60, 0, 0),
    "arm_l": (10, 0, -12), "forearm_l": (-30, 0, 0),
    "leg_r": (-5, 8, 2), "shin_r": (6, 0, 0), "leg_l": (7, -8, -3), "shin_l": (8, 0, 0),
}
GUARD_BANNER = (d(0.05, 1, -0.05), BACK)

GUARD2 = {   # phase II: lower, wider, leaning in
    "root": {"position": (0, -0.8, 0)},
    "hips": (4, 0, 0), "torso": (8, -14, 0), "head": (-8, 12, 0),
    "arm_r": (-30, 0, 28), "forearm_r": (-52, 0, 0),
    "arm_l": (-14, 0, -24), "forearm_l": (-46, 0, 0),
    "leg_r": (-14, 10, 6), "shin_r": (14, 0, 0), "leg_l": (12, -10, -7), "shin_l": (10, 0, 0),
}
GUARD2_BANNER = (d(0.12, 1, -0.32), BACK)


class Key:
    def __init__(self, t: float, body: dict, banner=None, lhand=None, ease: str = "smooth", vel=(0, 0, 0)):
        self.t = t
        self.body = body
        self.banner = banner      # (pole_dir, cloth_dir) or None = keep previous
        self.lhand = lhand        # along-pole distance for a two-handed grip, or None
        self.ease = ease
        self.vel = vel            # assumed travel velocity (blocks/s, model space) for cloth wind


def ease_fn(name: str) -> Callable[[float], float]:
    if name == "linear":
        return lambda x: x
    if name == "in":
        return lambda x: x * x * x
    if name == "out":
        return lambda x: 1 - (1 - x) ** 3
    if name == "snap":      # fast strike: almost all motion in the first third
        return lambda x: 1 - (1 - x) ** 5
    if name == "back":      # overshoot
        return lambda x: 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2
    return lambda x: x * x * (3 - 2 * x)


def _rot(body: dict, bone: str):
    v = body.get(bone, (0, 0, 0))
    if isinstance(v, dict):
        return v.get("rotation", (0, 0, 0))
    return v


def _pos(body: dict, bone: str):
    v = body.get(bone)
    if isinstance(v, dict):
        return v.get("position", (0, 0, 0))
    return (0, 0, 0)


def _lerp3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


class Action:
    def __init__(self, name: str, aid: int, length: float, keys: List[Key], loop: bool = False,
                 breeze=(0.0, 0.0, 1.2), gust: float = 0.6, desc: str = ""):
        self.name, self.id, self.length, self.keys, self.loop = name, aid, length, keys, loop
        self.breeze, self.gust, self.desc = breeze, gust, desc


# =========================================================================== sampling
class Sampler:
    def __init__(self):
        self.model = models.joan()
        self.rig = Rig(self.model)

    def frames(self, act: Action) -> Tuple[List[Pose], List[Tuple[float, float, float]]]:
        n = max(2, int(round(act.length * FPS)) + (0 if act.loop else 1))
        keys = act.keys
        # resolve 'keep previous banner' and IK at keys once
        banners, lh_angles = [], []
        last_banner = GUARD_BANNER
        for k in keys:
            if k.banner is not None:
                last_banner = k.banner
            banners.append(last_banner)
        for i, k in enumerate(keys):
            if k.lhand is None:
                lh_angles.append(None)
                continue
            pose = self.body_pose(k.body)
            self.rig.solve_banner(pose, banners[i][0], banners[i][1])
            target = self.rig.pole_point(pose, k.lhand)
            self.rig.solve_arm(pose, "l", target)
            lh_angles.append((pose["arm_l"]["rotation"], pose["forearm_l"]["rotation"]))
        all_bones = set()
        for k in keys:
            all_bones |= set(k.body)
        all_bones |= {"arm_l", "forearm_l"}
        poses, vels = [], []
        for f in range(n):
            t = f * DT
            if act.loop:
                t = t % act.length
            # find segment
            i = 0
            while i < len(keys) - 1 and keys[i + 1].t <= t:
                i += 1
            a = keys[i]
            b = keys[i + 1] if i < len(keys) - 1 else (keys[0] if act.loop else keys[i])
            tb = b.t if b.t > a.t else act.length
            span = max(1e-6, tb - a.t)
            x = 0.0 if a is b else max(0.0, min(1.0, (t - a.t) / span))
            e = ease_fn(b.ease)(x)
            ib = keys.index(b)
            pose: Pose = {}
            for bone in all_bones:
                r = _lerp3(_rot(a.body, bone), _rot(b.body, bone), e)
                p = _lerp3(_pos(a.body, bone), _pos(b.body, bone), e)
                pose[bone] = {"rotation": r}
                if any(abs(c) > 1e-6 for c in p):
                    pose[bone]["position"] = p
            # left hand IK result interpolation (only when both keys grip the pole)
            la, lb = lh_angles[i], lh_angles[ib]
            if la is not None and lb is not None:
                pose["arm_l"] = {"rotation": _lerp3(la[0], lb[0], e)}
                pose["forearm_l"] = {"rotation": _lerp3(la[1], lb[1], e)}
            elif la is not None and x < 0.5:
                pose["arm_l"] = {"rotation": _lerp3(la[0], _rot(b.body, "arm_l"), e)}
                pose["forearm_l"] = {"rotation": _lerp3(la[1], _rot(b.body, "forearm_l"), e)}
            elif lb is not None:
                pose["arm_l"] = {"rotation": _lerp3(_rot(a.body, "arm_l"), lb[0], e)}
                pose["forearm_l"] = {"rotation": _lerp3(_rot(a.body, "forearm_l"), lb[1], e)}
            pa, pb = banners[i], banners[ib]
            pole = v_norm(_lerp3(pa[0], pb[0], e))
            cloth = v_norm(_lerp3(pa[1], pb[1], e))
            self.rig.solve_banner(pose, pole, cloth)
            poses.append(pose)
            vels.append(tuple(c * 16.0 for c in _lerp3(a.vel, b.vel, e)))
        return poses, vels

    def body_pose(self, body: dict) -> Pose:
        pose: Pose = {}
        for bone in body:
            pose[bone] = {"rotation": _rot(body, bone)}
            p = _pos(body, bone)
            if any(abs(c) > 1e-6 for c in p):
                pose[bone]["position"] = p
        return pose

    def bake(self, act: Action) -> Dict[str, List[dict]]:
        poses, vels = self.frames(act)
        cloth = Chain(self.rig, CLOTH, (0, 0, 1), 5.0, hinge_axis=(0, 1, 0), gravity=70.0, drag=5.5,
                      stiffness=0.22, flutter=420.0, limits=(70.0, 55.0))
        cape = Chain(self.rig, CAPE, (0, -1, 0), 8.6, tip_len=8.3, gravity=160.0, drag=7.0, stiffness=0.35,
                     limits=(80.0, 15.0), angle_mode="hanging")
        breeze = tuple(c * 16.0 for c in act.breeze)
        loops = 3 if act.loop else 1
        # one-shots: pre-roll the first pose so the cloth starts settled
        if not act.loop:
            pre = [poses[0]] * 30
            cl = cloth.simulate(pre + poses, DT, [vels[0]] * 30 + vels, breeze, act.gust, 1, phase=act.id)[30:]
            cp = cape.simulate(pre + poses, DT, [vels[0]] * 30 + vels, breeze, act.gust * 0.5, 1)[30:]
        else:
            cl = cloth.simulate(poses, DT, vels, breeze, act.gust, loops, phase=act.id)
            cp = cape.simulate(poses, DT, vels, breeze, act.gust * 0.5, loops)
        out: Dict[str, List[dict]] = {}
        for f, pose in enumerate(poses):
            full = dict(pose)
            full.update(cl[f])
            full.update(cp[f])
            # skirt pieces follow the legs so they never cut through the thighs
            lr = _rot(pose, "leg_r")[0] if "leg_r" in pose else 0
            ll = _rot(pose, "leg_l")[0] if "leg_l" in pose else 0
            full["tabard_f"] = {"rotation": (min(lr, ll, 0) * 0.85, 0, 0)}
            full["tabard_b"] = {"rotation": (max(lr, ll, 0) * 0.6, 0, 0)}
            full["tasset_r"] = {"rotation": (min(lr, 0) * 0.7, 0, 0)}
            full["tasset_l"] = {"rotation": (min(ll, 0) * 0.7, 0, 0)}
            for bone, ch in full.items():
                out.setdefault(bone, []).append(ch)
        return out


# =========================================================================== keyframe output
def reduce_channel(times: List[float], vals: List[Sequence[float]], tol: float) -> List[int]:
    """Indices of keyframes needed so linear interpolation stays within tol."""
    keep = [0]
    i = 0
    n = len(vals)
    while i < n - 1:
        j = i + 2
        while j < n:
            ok = True
            for k in range(i + 1, j):
                t = (times[k] - times[i]) / (times[j] - times[i])
                for c in range(3):
                    est = vals[i][c] + (vals[j][c] - vals[i][c]) * t
                    if abs(est - vals[k][c]) > tol:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
            j += 1
        i = j - 1
        keep.append(i)
    if keep[-1] != n - 1:
        keep.append(n - 1)
    return keep


def channel_json(times, vals, tol):
    if all(max(abs(v[c] - vals[0][c]) for v in vals) < tol * 0.5 for c in range(3)):
        return [round(x, 2) for x in vals[0]]
    idx = reduce_channel(times, vals, tol)
    return {f"{times[i]:.2f}": [round(x, 2) for x in vals[i]] for i in idx}


def action_json(act: Action, baked: Dict[str, List[dict]]) -> dict:
    n = len(next(iter(baked.values())))
    times = [f * DT for f in range(n)]
    bones = {}
    for bone, frames in baked.items():
        rots = [fr.get("rotation", (0, 0, 0)) for fr in frames]
        tol = 0.6 if bone.startswith("cloth") or bone.startswith("cape") else 0.35
        ch = {"rotation": channel_json(times, rots, tol)}
        poss = [fr.get("position", (0, 0, 0)) for fr in frames]
        if any(any(abs(c) > 1e-4 for c in p) for p in poss):
            ch["position"] = channel_json(times, poss, 0.05)
        bones[bone] = ch
    a = {"loop": True if act.loop else False, "animation_length": round(act.length, 3),
         "override_previous_animation": True, "bones": bones}
    return a


# =========================================================================== choreography
def P(base: Optional[dict] = None, **kw) -> dict:
    out = dict(base or {})
    for k, v in kw.items():
        out[k] = v
    return out


def root_at(x=0.0, y=0.0, z=0.0, rot=(0, 0, 0)):
    return {"rotation": rot, "position": (x, y, z)}


KNEEL = P(GUARD, root=root_at(0, -5.6, 0.5), hips=(8, 0, 0), torso=(14, -6, 0), head=(18, 4, 0),
          leg_r=(-82, 6, 2), shin_r=(80, 0, 0), leg_l=(2, -4, -2), shin_l=(92, 0, 0))
STRIDE = dict(leg_r=(-22, 6, 3), shin_r=(18, 0, 0), leg_l=(26, -6, -3), shin_l=(14, 0, 0))
CROUCH = P(GUARD, root=root_at(0, -2.4, 0), hips=(10, 0, 0), torso=(22, -4, 0), head=(-18, 0, 0),
           leg_r=(-46, 10, 6), shin_r=(58, 0, 0), leg_l=(18, -10, -6), shin_l=(46, 0, 0))
OVERHEAD = dict(arm_r=(-168, 0, -4), forearm_r=(-12, 0, 0))
BANNER_UP = (d(0, 1, 0.04), BACK)


def spin_keys(t0: float, period: float, body: dict, turns: int = 1, tilt: float = 0.12, steps: int = 8) -> List[Key]:
    keys = []
    for i in range(steps * turns + 1):
        a = i / steps * 2 * math.pi
        keys.append(Key(t0 + i * period / steps, body, banner=(d(math.cos(a), tilt, math.sin(a)), UP), ease="linear"))
    return keys


def actions() -> List[Action]:
    A: List[Action] = []
    G, G2 = GUARD, GUARD2
    GB, G2B = GUARD_BANNER, GUARD2_BANNER

    # --- 1/2 spawn ------------------------------------------------------------------------
    surf_down = P(G, root=root_at(0, -1.5, 0), hips=(-6, 0, 0), torso=(-10, -8, 0), head=(12, 6, 0),
                  arm_r=(-150, 0, 8), forearm_r=(-14, 0, 0), arm_l=(-30, 0, -55), forearm_l=(-20, 0, 0),
                  leg_r=(-34, 4, 2), shin_r=(44, 0, 0), leg_l=(28, -4, -2), shin_l=(26, 0, 0))
    A.append(Action("spawn_descend", 1, 1.0, [
        Key(0.0, surf_down, (d(0.05, 1, 0.55), BACK), vel=(0, -9, -3)),
        Key(0.5, P(surf_down, root=root_at(0, -2.3, 0)), (d(0.12, 1, 0.6), BACK), vel=(0, -9, -3)),
    ], loop=True, desc="rides the road of light down from the sky"))
    land_arm = dict(arm_r=(-62, 8, 6), forearm_r=(-48, 0, 0))
    A.append(Action("spawn_land", 2, 3.4, [
        Key(0.0, P(surf_down), (d(0.05, 1, 0.55), BACK)),
        Key(0.18, P(KNEEL, **land_arm, head=(30, 0, 0)), (d(0.02, 1, -0.08), BACK), ease="snap"),
        Key(1.1, P(KNEEL, **land_arm, head=(34, 0, 0)), (d(0.02, 1, -0.06), BACK)),
        Key(1.7, P(KNEEL, **land_arm, head=(-6, 0, 0)), (d(0.02, 1, -0.06), BACK)),
        Key(2.25, P(G, **OVERHEAD, arm_l=(-20, 0, -60), forearm_l=(-10, 0, 0), head=(-20, 0, 0)),
            (d(-0.35, 1, 0.0), BACK), ease="out"),
        Key(2.6, P(G, **OVERHEAD, arm_l=(-20, 0, -60), forearm_l=(-10, 0, 0), head=(-14, 0, 0)),
            (d(0.45, 1, 0.05), BACK)),
        Key(2.95, P(G, **OVERHEAD, head=(-10, 0, 0)), (d(0.0, 1, 0.15), BACK)),
        Key(3.4, G, GB),
    ], desc="lands on one knee, plants the standard, rises and unfurls it overhead"))

    # --- 3/4/5/6/7 melee --------------------------------------------------------------------
    sweep_wind = P(G, hips=(0, 18, 0), torso=(6, 38, 0), head=(-4, -30, 0), arm_r=(-80, 30, 40),
                   forearm_r=(-40, 0, 0), leg_r=(-10, 14, 8), shin_r=(14, 0, 0), leg_l=(16, -14, -10), shin_l=(16, 0, 0))
    sweep_hit = P(G, root=root_at(0, -0.8, -1.5), hips=(4, -22, 0), torso=(10, -44, 0), head=(-6, 30, 0),
                  arm_r=(-88, -40, -10), forearm_r=(-18, 0, 0), leg_r=(18, 14, 6), shin_r=(20, 0, 0),
                  leg_l=(-26, -12, -8), shin_l=(24, 0, 0))
    A.append(Action("melee_sweep", 3, 0.8, [
        Key(0.0, G, GB),
        Key(0.26, sweep_wind, (d(-0.85, 0.42, 0.35), UP), lhand=-9, ease="out"),
        Key(0.42, sweep_hit, (d(0.88, 0.2, -0.42), UP), lhand=-9, ease="snap"),
        Key(0.56, P(sweep_hit, torso=(10, -52, 0)), (d(0.75, 0.28, 0.45), UP), lhand=-9),
        Key(0.8, G, GB),
    ], desc="two-handed horizontal sweep from right to left"))
    back_wind = P(sweep_hit, torso=(8, -56, 0))
    back_hit = P(G, root=root_at(0, -0.6, -1.0), hips=(2, 20, 0), torso=(8, 46, 0), head=(-4, -30, 0),
                 arm_r=(-76, 40, 46), forearm_r=(-22, 0, 0), leg_r=(-20, 14, 8), shin_r=(18, 0, 0),
                 leg_l=(20, -12, -8), shin_l=(18, 0, 0))
    A.append(Action("melee_backsweep", 4, 0.8, [
        Key(0.0, sweep_hit, (d(0.8, 0.25, -0.3), UP), lhand=-9),
        Key(0.2, back_wind, (d(0.6, 0.45, 0.65), UP), lhand=-9, ease="out"),
        Key(0.38, back_hit, (d(-0.92, 0.22, -0.32), UP), ease="snap"),
        Key(0.52, P(back_hit, torso=(8, 54, 0)), (d(-0.7, 0.35, 0.55), UP)),
        Key(0.8, G, GB),
    ], desc="backhand sweep from left to right"))
    thrust_wind = P(G, root=root_at(0, -0.6, 2.0), hips=(-4, 22, 0), torso=(-6, 26, 0), head=(4, -22, 0),
                    arm_r=(-48, 18, 26), forearm_r=(-74, 0, 0), leg_r=(18, 10, 4), shin_r=(26, 0, 0),
                    leg_l=(-16, -8, -4), shin_l=(12, 0, 0))
    thrust_hit = P(G, root=root_at(0, -2.2, -6.0), hips=(8, -6, 0), torso=(18, -10, 0), head=(-14, 8, 0),
                   arm_r=(-92, -6, 6), forearm_r=(-6, 0, 0), leg_r=(40, 6, 4), shin_r=(10, 0, 0),
                   leg_l=(-58, -8, -4), shin_l=(52, 0, 0))
    A.append(Action("melee_thrust", 5, 0.85, [
        Key(0.0, G, GB),
        Key(0.3, thrust_wind, (d(0.02, 0.08, -1), UP), lhand=13, ease="out"),
        Key(0.45, thrust_hit, (d(0.0, 0.02, -1), UP), lhand=13, ease="snap"),
        Key(0.62, thrust_hit, (d(0.0, 0.06, -1), UP), lhand=13),
        Key(0.85, G, GB),
    ], desc="lunging thrust with the butt-capped pole"))
    plant_up = P(G, hips=(-6, 0, 0), torso=(-14, -4, 0), head=(-18, 0, 0), **OVERHEAD,
                 leg_r=(-6, 6, 2), shin_r=(4, 0, 0), leg_l=(8, -6, -2), shin_l=(4, 0, 0))
    plant_hit = P(KNEEL, root=root_at(0, -4.2, -1.5), torso=(34, -4, 0), head=(24, 0, 0),
                  arm_r=(-58, 0, 4), forearm_r=(-34, 0, 0))
    A.append(Action("melee_plant", 6, 1.1, [
        Key(0.0, G, GB),
        Key(0.36, plant_up, (d(0, 1, 0.22), BACK), lhand=-8, ease="out"),
        Key(0.52, plant_hit, (d(0, 1, -0.12), BACK), lhand=12, ease="snap"),
        Key(0.82, plant_hit, (d(0, 1, -0.1), BACK), lhand=12),
        Key(1.1, G, GB),
    ], desc="overhead slam that plants the standard"))
    wrap_wind = P(G2, torso=(-6, 34, 0), head=(4, -26, 0), arm_r=(-120, 30, 30), forearm_r=(-40, 0, 0))
    wrap_whip = P(G2, root=root_at(0, -1.0, -2.0), torso=(26, -22, 0), head=(-14, 16, 0),
                  arm_r=(-96, -10, 2), forearm_r=(-8, 0, 0), arm_l=(-60, 0, -20), forearm_l=(-30, 0, 0))
    A.append(Action("melee_wrap", 7, 1.2, [
        Key(0.0, G2, G2B),
        Key(0.34, wrap_wind, (d(-0.35, 0.62, 0.7), UP), ease="out"),
        Key(0.5, wrap_whip, (d(0.08, 0.55, -0.84), UP), ease="snap"),
        Key(0.78, P(wrap_wind, torso=(-4, 40, 0)), (d(-0.5, 0.72, 0.45), UP), ease="out"),
        Key(1.2, G2, G2B),
    ], desc="Banner Wrap: whips the cloth forward to snare and fling"))

    # --- 8/9 banner trail -----------------------------------------------------------------
    drag_pose = P(CROUCH, arm_r=(26, 0, 22), forearm_r=(-14, 0, 0), arm_l=(-50, 0, -24), forearm_l=(-36, 0, 0))
    A.append(Action("trail_windup", 8, 0.6, [
        Key(0.0, G, GB),
        Key(0.45, drag_pose, (d(-0.28, -0.32, 0.9), UP), ease="out"),
        Key(0.6, drag_pose, (d(-0.3, -0.36, 0.88), UP)),
    ], desc="lowers the standard's tip to the earth, ready to drag it"))
    run_a = P(drag_pose, root=root_at(0, -1.2, 0), torso=(28, -4, 0), leg_r=(-58, 8, 4), shin_r=(30, 0, 0),
              leg_l=(42, -8, -4), shin_l=(58, 0, 0), arm_l=(30, 0, -18), forearm_l=(-50, 0, 0))
    run_b = P(drag_pose, root=root_at(0, -2.0, 0), torso=(28, -4, 0), leg_r=(42, 8, 4), shin_r=(58, 0, 0),
              leg_l=(-58, -8, -4), shin_l=(30, 0, 0), arm_l=(-70, 0, -18), forearm_l=(-30, 0, 0))
    A.append(Action("trail_dash", 9, 0.4, [
        Key(0.0, run_a, (d(-0.22, -0.3, 0.93), UP), vel=(0, 0, -18)),
        Key(0.2, run_b, (d(-0.2, -0.26, 0.94), UP), vel=(0, 0, -18)),
    ], loop=True, desc="sprints dragging the standard, writing a road behind her"))

    # --- 10/11/12 pilgrim's surge ------------------------------------------------------------
    surge_crouch = P(CROUCH, arm_r=(-128, 0, 10), forearm_r=(-22, 0, 0), arm_l=(30, 0, -40), forearm_l=(-20, 0, 0))
    A.append(Action("surge_windup", 10, 0.55, [
        Key(0.0, G, GB),
        Key(0.42, surge_crouch, (d(0.05, 0.75, -0.66), BACK), ease="out"),
        Key(0.55, surge_crouch, (d(0.05, 0.72, -0.69), BACK)),
    ], desc="crouches and levels the standard before leaping onto a road"))
    ride = P(G, root=root_at(0, -2.0, 0), hips=(6, 30, 0), torso=(22, -26, 0), head=(-20, -4, 0),
             arm_r=(-118, -10, 4), forearm_r=(-20, 0, 0), arm_l=(20, 0, -70), forearm_l=(-24, 0, 0),
             leg_r=(26, 0, 6), shin_r=(34, 0, 0), leg_l=(-38, 0, -6), shin_l=(46, 0, 0))
    A.append(Action("surge_ride", 11, 0.5, [
        Key(0.0, ride, (d(0.12, 0.66, -0.74), BACK), vel=(0, 0, -22)),
        Key(0.25, P(ride, root=root_at(0, -2.6, 0), torso=(24, -26, 0)), (d(0.16, 0.62, -0.77), BACK), vel=(0, -2, -22)),
    ], loop=True, desc="surfs a road like a charging standard-bearer"))
    A.append(Action("surge_slam", 12, 0.9, [
        Key(0.0, P(plant_up, root=root_at(0, 1.0, 0)), (d(0, 1, 0.3), BACK), lhand=-8, vel=(0, -12, -6)),
        Key(0.14, plant_hit, (d(0, 1, -0.12), BACK), lhand=12, ease="snap"),
        Key(0.6, plant_hit, (d(0, 1, -0.1), BACK), lhand=12),
        Key(0.9, G, GB),
    ], desc="drops from the road and drives the standard into the earth"))

    # --- 13/14/15 road of orleans -----------------------------------------------------------
    brace = P(KNEEL, root=root_at(0, -5.4, 0.8), torso=(18, 0, 0), head=(-8, 0, 0),
              arm_r=(-64, 6, 4), forearm_r=(-40, 0, 0))
    A.append(Action("orleans_plant", 13, 1.0, [
        Key(0.0, G, GB),
        Key(0.32, plant_up, (d(0, 1, 0.2), BACK), lhand=-8, ease="out"),
        Key(0.5, brace, (d(0, 1, -0.16), BACK), lhand=11, ease="snap"),
        Key(1.0, brace, (d(0, 1, -0.14), BACK), lhand=11),
    ], desc="plants the standard and kneels behind it: the road is laid"))
    A.append(Action("orleans_hold", 14, 1.0, [
        Key(0.0, brace, (d(0, 1, -0.14), BACK), lhand=11, vel=(0, 0, 5)),
        Key(0.5, P(brace, torso=(20, 2, 0)), (d(0.02, 1, -0.16), BACK), lhand=11, vel=(0, 0, 6)),
    ], loop=True, breeze=(0, 0, -3.0), desc="braces against the road's current"))
    A.append(Action("orleans_breaker", 15, 1.0, [
        Key(0.0, brace, (d(0, 1, -0.14), BACK), lhand=11),
        Key(0.3, P(plant_up, root=root_at(0, 0.5, 0)), (d(0, 1, 0.3), BACK), lhand=-8, ease="out"),
        Key(0.46, P(plant_hit, root=root_at(0, -4.2, -3.0), torso=(40, 0, 0)), (d(0, 0.9, -0.42), BACK), lhand=12,
            ease="snap"),
        Key(0.74, P(plant_hit, root=root_at(0, -4.2, -3.0), torso=(40, 0, 0)), (d(0, 0.9, -0.4), BACK), lhand=12),
        Key(1.0, G, GB),
    ], desc="Siege Breaker: rips the standard free and slams the road's head"))

    # --- 16 false salvation -------------------------------------------------------------------
    point = P(G, torso=(2, -16, 0), head=(-4, 12, 0), arm_r=(-96, -4, 6), forearm_r=(-6, 0, 0),
              arm_l=(-30, 0, -64), forearm_l=(-8, 0, 0), leg_r=(-14, 8, 4), shin_r=(8, 0, 0))
    A.append(Action("false_point", 16, 0.9, [
        Key(0.0, G, GB),
        Key(0.3, P(G, **OVERHEAD), (d(0, 1, 0.1), BACK), ease="out"),
        Key(0.55, point, (d(0, 0.38, -0.93), UP), ease="snap"),
        Key(0.9, point, (d(0, 0.4, -0.92), UP)),
    ], desc="levels the standard at her prey: the false salvation is offered"))

    # --- 17/18 convergence ----------------------------------------------------------------
    raised = P(G, **OVERHEAD, head=(-8, 0, 0))
    throw_back = P(raised, arm_l=(36, 0, -46), forearm_l=(-60, 0, 0), torso=(-4, 14, 0))
    throw_fwd = P(raised, arm_l=(-110, -20, -18), forearm_l=(-4, 0, 0), torso=(8, -16, 0))
    throw_side = P(raised, arm_l=(-80, 30, -80), forearm_l=(-6, 0, 0), torso=(4, -30, 0))
    A.append(Action("converge_throw", 17, 1.3, [
        Key(0.0, G, GB),
        Key(0.2, throw_back, BANNER_UP, ease="out"),
        Key(0.34, throw_fwd, BANNER_UP, ease="snap"),
        Key(0.52, throw_back, BANNER_UP),
        Key(0.66, throw_side, BANNER_UP, ease="snap"),
        Key(0.84, throw_back, BANNER_UP),
        Key(0.98, P(throw_fwd, torso=(6, 10, 0), arm_l=(-90, 40, 10)), BANNER_UP, ease="snap"),
        Key(1.3, raised, BANNER_UP),
    ], desc="flings phantom standards from her open hand"))
    beckon_a = P(raised, arm_l=(-70, 0, -20), forearm_l=(-20, 0, 0))
    beckon_b = P(raised, arm_l=(-60, 0, -14), forearm_l=(-95, 0, 0))
    A.append(Action("converge_call", 18, 1.0, [
        Key(0.0, beckon_a, BANNER_UP),
        Key(0.5, beckon_b, (d(0.05, 1, 0.08), BACK)),
    ], loop=True, desc="holds the standard high and beckons every road to her"))

    # --- 19/20 heaven's detour --------------------------------------------------------------
    whirl = P(G, root=root_at(0, -0.5, 0), torso=(-4, 0, 0), head=(-16, 0, 0), arm_r=(-172, 0, 2),
              forearm_r=(-4, 0, 0), arm_l=(-40, 0, -50), forearm_l=(-20, 0, 0),
              leg_r=(-8, 10, 6), shin_r=(8, 0, 0), leg_l=(8, -10, -6), shin_l=(8, 0, 0))
    A.append(Action("detour_spin", 19, 0.6, spin_keys(0.0, 0.6, whirl), loop=True,
                    desc="whirls the standard overhead: the orbit of detours"))
    A.append(Action("detour_release", 20, 0.6, [
        Key(0.0, whirl, (d(0.0, 0.12, 1), UP)),
        Key(0.22, P(whirl, torso=(-10, 10, 0)), (d(0.0, 1, 0.3), BACK), ease="out"),
        Key(0.38, P(point, torso=(16, -8, 0)), (d(0, 0.25, -0.97), UP), ease="snap"),
        Key(0.6, G, GB),
    ], desc="cracks the standard forward, releasing the seraph lights"))

    # --- 21/22 martyr's procession ------------------------------------------------------------
    kneel_raise = P(KNEEL, head=(-24, 0, 0), torso=(-4, 0, 0), **OVERHEAD)
    A.append(Action("procession_raise", 21, 1.2, [
        Key(0.0, G, GB),
        Key(0.5, P(KNEEL, head=(26, 0, 0), arm_r=(-62, 8, 6), forearm_r=(-48, 0, 0)), (d(0, 1, -0.06), BACK)),
        Key(1.0, kneel_raise, (d(0, 1, 0.05), BACK), lhand=-10, ease="out"),
        Key(1.2, kneel_raise, (d(0, 1, 0.05), BACK), lhand=-10),
    ], desc="kneels and lifts the standard: every old road wakes"))
    A.append(Action("procession_hold", 22, 1.2, [
        Key(0.0, kneel_raise, (d(-0.12, 1, 0.05), BACK), lhand=-10),
        Key(0.6, P(kneel_raise, torso=(-6, 4, 0)), (d(0.12, 1, 0.05), BACK), lhand=-10),
    ], loop=True, desc="sways the raised standard while the procession marches"))

    # --- 23/24/25 road to the stake -----------------------------------------------------------
    float_pose = P(G, hips=(-4, 0, 0), torso=(-8, 0, 0), head=(-22, 0, 0), **OVERHEAD,
                   arm_l=(-10, 0, -78), forearm_l=(-6, 0, 0),
                   leg_r=(8, 0, 2), shin_r=(14, 0, 0), leg_l=(14, 0, -2), shin_l=(18, 0, 0))
    A.append(Action("ult_rise", 23, 2.0, [
        Key(0.0, G2, G2B),
        Key(0.5, P(KNEEL, head=(20, 0, 0)), (d(0, 1, -0.05), BACK)),
        Key(1.4, float_pose, (d(0, 1, 0.0), BACK), vel=(0, 4, 0), ease="out"),
        Key(2.0, float_pose, (d(0, 1, 0.0), BACK), vel=(0, 2, 0)),
    ], breeze=(0, 3.0, 0.5), desc="rises above the pyre as the standard catches fire"))
    A.append(Action("ult_channel", 24, 1.6, [
        Key(0.0, float_pose, (d(-0.06, 1, 0.0), BACK)),
        Key(0.8, P(float_pose, root=root_at(0, 1.0, 0), arm_l=(-14, 0, -86)), (d(0.06, 1, 0.0), BACK)),
    ], loop=True, breeze=(0, 3.5, 0.5), desc="hovers, holding the burning standard over every road"))
    bound = P(G, root=root_at(0, 0, 0), torso=(10, 0, 0), head=(30, 0, 0),
              arm_r=(38, -30, -12), forearm_r=(-36, 0, 0), arm_l=(38, 30, 12), forearm_l=(-36, 0, 0),
              leg_r=(2, 0, 2), shin_r=(4, 0, 0), leg_l=(2, 0, -2), shin_l=(4, 0, 0))
    A.append(Action("ult_bound", 25, 1.0, [
        Key(0.0, bound, (d(0.0, -1, 0.25), BACK)),
        Key(0.3, P(bound, torso=(14, 8, 0), head=(18, -14, 0)), (d(0.08, -1, 0.25), BACK), ease="snap"),
        Key(0.6, P(bound, torso=(8, -8, 0), head=(26, 12, 0)), (d(-0.08, -1, 0.25), BACK), ease="snap"),
    ], loop=True, desc="Martyr's Echo: bound to her own stake, struggling"))

    # --- 26/27 phase transition ------------------------------------------------------------
    stag = P(G, torso=(-22, 10, 0), head=(-26, 0, 0), arm_l=(-30, 0, -70), arm_r=(-10, 0, 40), forearm_r=(-40, 0, 0),
             leg_r=(14, 4, 4), shin_r=(10, 0, 0), leg_l=(-10, -4, -4), shin_l=(6, 0, 0))
    planted_side = P(KNEEL, head=(32, 0, 0), arm_r=(-40, 10, 24), forearm_r=(-52, 0, 0),
                     arm_l=(10, 0, -10), forearm_l=(-60, 0, 0))
    A.append(Action("phase_kneel", 26, 2.0, [
        Key(0.0, G, GB),
        Key(0.3, stag, (d(-0.3, 1, 0.2), BACK), ease="out"),
        Key(0.8, planted_side, (d(-0.08, 1, 0.0), BACK), ease="in"),
        Key(2.0, P(planted_side, head=(38, 0, 0)), (d(-0.08, 1, 0.0), BACK)),
    ], desc="the Maiden falls to one knee; the roads begin to burn"))
    A.append(Action("phase_rise", 27, 2.4, [
        Key(0.0, P(planted_side, head=(38, 0, 0)), (d(-0.08, 1, 0.0), BACK)),
        Key(0.6, P(planted_side, head=(-20, 0, 0)), (d(-0.08, 1, 0.0), BACK)),
        Key(1.3, P(G2, **OVERHEAD, head=(-24, 0, 0), arm_l=(-30, 0, -70)), (d(0.0, 1, 0.1), BACK), ease="out"),
        Key(1.8, P(G2, **OVERHEAD, head=(-14, 0, 0), arm_l=(-30, 0, -70)), (d(0.25, 1, 0.1), BACK)),
        Key(2.4, G2, G2B),
    ], breeze=(0, 2.5, 1.0), desc="the Saint rises with the standard aflame"))

    # --- 28..33 reactions & misc -----------------------------------------------------------
    A.append(Action("stagger", 28, 0.8, [
        Key(0.0, G, GB),
        Key(0.16, P(stag, root=root_at(0, -0.5, 2.0)), (d(-0.35, 1, 0.3), BACK), ease="snap"),
        Key(0.8, G, GB),
    ], desc="recoils"))
    listen = P(G, torso=(-6, 0, 0), head=(-30, 12, 10), arm_l=(-150, 0, -24), forearm_l=(-20, 0, 0),
               arm_r=(-16, 4, 8), forearm_r=(-50, 0, 0))
    A.append(Action("listen", 29, 1.5, [
        Key(0.0, listen, (d(0.06, 1, 0.0), BACK)),
        Key(0.75, P(listen, head=(-34, -6, 8)), (d(0.08, 1, 0.0), BACK)),
    ], loop=True, desc="The Voices: she hears the bells of Domremy and looks to the sky"))
    A.append(Action("recover", 30, 1.0, [
        Key(0.0, plant_hit, (d(0, 1, -0.1), BACK), lhand=12),
        Key(0.45, P(G, torso=(10, -8, 0)), (d(0, 1, 0.1), BACK), ease="out"),
        Key(1.0, G, GB),
    ], desc="wrenches the standard free of the ground"))
    salute_dip = P(G, torso=(14, -6, 0), head=(20, 6, 0), arm_r=(-84, 0, 4), forearm_r=(-16, 0, 0))
    A.append(Action("taunt", 31, 1.4, [
        Key(0.0, G, GB),
        Key(0.45, salute_dip, (d(0, 0.5, -0.86), UP), ease="out"),
        Key(0.8, salute_dip, (d(0, 0.48, -0.88), UP)),
        Key(1.4, G, GB),
    ], desc="dips the standard in salute"))
    death_knees = P(G, root=root_at(0, -7.0, 1.0), hips=(6, 0, 0), torso=(16, 0, 0), head=(30, 0, 0),
                    leg_r=(-2, 6, 4), shin_r=(92, 0, 0), leg_l=(-2, -6, -4), shin_l=(92, 0, 0),
                    arm_r=(-40, 10, 20), forearm_r=(-50, 0, 0), arm_l=(12, 0, -14), forearm_l=(-30, 0, 0))
    A.append(Action("death", 32, 6.0, [
        Key(0.0, G2, G2B),
        Key(0.5, P(stag, root=root_at(0, -0.4, 1.0)), (d(-0.3, 1, 0.2), BACK), ease="out"),
        Key(1.4, death_knees, (d(-0.25, 1, 0.12), BACK), ease="in"),
        Key(2.6, P(death_knees, head=(36, 0, 0), torso=(22, 0, 0)), (d(-0.32, 1, 0.12), BACK)),
        Key(4.0, P(death_knees, head=(-28, 0, 0), torso=(-2, 0, 0)), (d(-0.15, 1, 0.08), BACK)),
        Key(5.0, P(death_knees, head=(-34, 0, 0), torso=(-6, 0, 0), arm_l=(-60, 0, -60), forearm_l=(-10, 0, 0),
                   arm_r=(-130, 0, 10), forearm_r=(-10, 0, 0)), (d(0.0, 1, 0.0), BACK)),
        Key(6.0, P(death_knees, head=(-36, 0, 0), torso=(-6, 0, 0), arm_l=(-64, 0, -64), forearm_l=(-10, 0, 0),
                   arm_r=(-134, 0, 10), forearm_r=(-10, 0, 0)), (d(0.0, 1, 0.0), BACK)),
    ], breeze=(0, 2.0, 0.5), desc="falls to her knees, then lifts her face and standard to the sky"))
    A.append(Action("hover", 33, 1.6, [
        Key(0.0, float_pose, (d(-0.04, 1, 0.05), BACK)),
        Key(0.8, P(float_pose, root=root_at(0, 0.8, 0)), (d(0.04, 1, 0.05), BACK)),
    ], loop=True, breeze=(0, 2.5, 0.5), desc="floats"))
    return A


ACTION_IDS = None   # filled by build


# =========================================================================== base layers (Molang)
def _guard_static(sampler: Sampler, body: dict, banner) -> Pose:
    pose = sampler.body_pose(body)
    sampler.rig.solve_banner(pose, banner[0], banner[1])
    return pose


def _lerp_expr(a: float, b: float, var: str = "variable.p2") -> str:
    if abs(a - b) < 0.05:
        return f"{a:.2f}"
    return f"math.lerp({a:.2f}, {b:.2f}, {var})"


def base_layers(sampler: Sampler) -> Dict[str, dict]:
    g1 = _guard_static(sampler, GUARD, GUARD_BANNER)
    g2 = _guard_static(sampler, GUARD2, GUARD2_BANNER)
    t = "query.life_time"
    bones: Dict[str, dict] = {}
    for bone in sorted(set(g1) | set(g2)):
        r1 = g1.get(bone, {}).get("rotation", (0, 0, 0))
        r2 = g2.get(bone, {}).get("rotation", (0, 0, 0))
        p1 = g1.get(bone, {}).get("position", (0, 0, 0))
        p2 = g2.get(bone, {}).get("position", (0, 0, 0))
        ch = {"rotation": [_lerp_expr(r1[i], r2[i]) for i in range(3)]}
        if any(abs(c) > 1e-6 for c in p1 + p2):
            ch["position"] = [_lerp_expr(p1[i], p2[i]) for i in range(3)]
        bones[bone] = ch
    # breathing & idle life
    bones["torso"]["rotation"][0] = f"{bones['torso']['rotation'][0]} + math.sin({t} * 75) * 1.2"
    bones["head"]["rotation"][1] = f"{bones['head']['rotation'][1]} + math.sin({t} * 23) * 4"
    bones["arm_l"]["rotation"][2] = f"{bones['arm_l']['rotation'][2]} - math.sin({t} * 75) * 1.5"
    bones["halo"] = {"rotation": [0, 0, f"{t} * 26"], "position": [0, f"math.sin({t} * 60) * 0.35", 0]}
    bones["chain_r"] = {"scale": "variable.p2"}
    bones["chain_l"] = {"scale": "variable.p2"}
    base = {"loop": True, "bones": bones}

    w = "query.modified_distance_moved"
    sp = "query.modified_move_speed"
    leg = f"math.cos({w} * 32.0) * 34.0 * {sp}"
    legi = f"-math.cos({w} * 32.0) * 34.0 * {sp}"
    knee_r = f"math.max(0, -math.sin({w} * 32.0)) * 40.0 * {sp}"
    knee_l = f"math.max(0, math.sin({w} * 32.0)) * 40.0 * {sp}"
    walk = {"loop": True, "bones": {
        "leg_r": {"rotation": [leg, 0, 0]},
        "leg_l": {"rotation": [legi, 0, 0]},
        "shin_r": {"rotation": [knee_r, 0, 0]},
        "shin_l": {"rotation": [knee_l, 0, 0]},
        "arm_l": {"rotation": [f"math.cos({w} * 32.0) * 26.0 * {sp}", 0, 0]},
        "arm_r": {"rotation": [f"-math.cos({w} * 32.0) * 6.0 * {sp}", 0, 0]},
        "torso": {"rotation": [f"3.0 * {sp}", f"math.cos({w} * 32.0) * 5.0 * {sp}", 0]},
        "root": {"position": [0, f"math.abs(math.sin({w} * 32.0)) * 0.7 * {sp}", 0]},
        "tabard_f": {"rotation": [f"-math.abs(math.cos({w} * 32.0)) * 26.0 * {sp}", 0, 0]},
        "tabard_b": {"rotation": [f"math.abs(math.cos({w} * 32.0)) * 18.0 * {sp}", 0, 0]},
        "tasset_r": {"rotation": [f"math.min(0, {leg}) * 0.7", 0, 0]},
        "tasset_l": {"rotation": [f"math.min(0, {legi}) * 0.7", 0, 0]},
        "cape": {"rotation": [f"10.0 * {sp} + math.sin({w} * 64.0) * 3.0 * {sp}", 0, 0]},
        "cape_lower": {"rotation": [f"8.0 * {sp} + math.sin({w} * 64.0 - 40) * 4.0 * {sp}", 0, 0]},
    }}
    run = {"loop": True, "bones": {
        "leg_r": {"rotation": [f"math.cos({w} * 26.0) * 52.0", 0, 0]},
        "leg_l": {"rotation": [f"-math.cos({w} * 26.0) * 52.0", 0, 0]},
        "shin_r": {"rotation": [f"math.max(0, -math.sin({w} * 26.0)) * 70.0", 0, 0]},
        "shin_l": {"rotation": [f"math.max(0, math.sin({w} * 26.0)) * 70.0", 0, 0]},
        "arm_l": {"rotation": [f"math.cos({w} * 26.0) * 50.0 - 10", 0, 0]},
        "forearm_l": {"rotation": [-40, 0, 0]},
        "arm_r": {"rotation": [f"-8.0 - math.cos({w} * 26.0) * 8.0", 0, 0]},
        "torso": {"rotation": [14, f"math.cos({w} * 26.0) * 8.0", 0]},
        "head": {"rotation": [-12, 0, 0]},
        "root": {"position": [0, f"math.abs(math.sin({w} * 26.0)) * 1.4 - 0.6", 0]},
        "tabard_f": {"rotation": [f"-math.abs(math.cos({w} * 26.0)) * 44.0", 0, 0]},
        "tabard_b": {"rotation": [f"20 + math.abs(math.cos({w} * 26.0)) * 20.0", 0, 0]},
        "cape": {"rotation": [f"34 + math.sin({w} * 52.0) * 6.0", 0, 0]},
        "cape_lower": {"rotation": [f"22 + math.sin({w} * 52.0 - 40) * 8.0", 0, 0]},
    }}
    look = {"loop": True, "bones": {
        "head": {"rotation": ["math.clamp(query.target_x_rotation, -35, 30)",
                              "math.clamp(query.target_y_rotation, -60, 60)", 0]},
    }}
    # cloth lags behind turns (deg/s of body yaw); tip lags most
    turn = {"loop": True, "bones": {}}
    for i in range(6):
        k = 0.04 + i * 0.012
        turn["bones"][f"cloth_{i}"] = {"rotation": [0, f"math.clamp(variable.turn * {k:.3f}, -22, 22)", 0]}
    turn["bones"]["cape"] = {"rotation": [0, 0, "math.clamp(variable.turn * 0.04, -18, 18)"]}
    # tatters & streamers: always flutter, faster with speed
    fl = "(1.0 + math.clamp(query.ground_speed * 0.35, 0, 3))"
    flutter = {"loop": True, "bones": {}}
    for k in range(3):
        flutter["bones"][f"tatter_{k}"] = {"rotation": [f"math.sin({t} * 410 + {k * 77}) * 12 * {fl}",
                                                        f"math.sin({t} * 270 + {k * 53}) * 16", 0]}
    for k in range(2):
        flutter["bones"][f"ribbon_{k}"] = {"rotation": [f"25 * math.clamp(query.ground_speed * 0.2, 0, 1) + math.sin({t} * 300 + {k * 90}) * 9 * {fl}",
                                                        0, f"math.sin({t} * 190 + {k * 60}) * 14"]}
        flutter["bones"][f"ribbon_{k}b"] = {"rotation": [f"math.sin({t} * 300 + {k * 90 - 60}) * 16 * {fl}", 0,
                                                         f"math.sin({t} * 190 + {k * 60 - 50}) * 20"]}
    return {
        "animation.joan.base": base,
        "animation.joan.walk": walk,
        "animation.joan.run": run,
        "animation.joan.look": look,
        "animation.joan.cloth_turn": turn,
        "animation.joan.flutter": flutter,
    }


def cloth_loops(sampler: Sampler) -> Dict[str, dict]:
    """Baked idle cloth: a breeze loop and a streaming (moving) loop."""
    out = {}
    for name, vel, breeze, gust, length in (("cloth_breeze", (0, 0, 0), (0.4, 0.2, 2.2), 0.9, 4.0),
                                            ("cloth_stream", (0, 0, -7.5), (0, 0, 0.5), 0.4, 2.0)):
        act = Action(name, -1, length, [Key(0.0, GUARD, GUARD_BANNER, vel=vel), Key(length / 2, GUARD, GUARD_BANNER, vel=vel)],
                     loop=True, breeze=breeze, gust=gust)
        baked = sampler.bake(act)
        cloth_only = {b: v for b, v in baked.items() if b.startswith("cloth_")}
        j = action_json(act, cloth_only)
        j.pop("override_previous_animation")
        out[f"animation.joan.{name}"] = j
    return out


# =========================================================================== controller
def action_controller(acts: List[Action]) -> dict:
    states = {"none": {"transitions": [], "blend_transition": 0.15}}
    for a in acts:
        cond = f"query.property('joan:action') == {a.id} && query.property('joan:seq') != variable.joan_seq"
        states["none"]["transitions"].append({f"a_{a.name}": cond})
        exit_cond = (f"query.property('joan:seq') != variable.joan_seq || query.property('joan:action') != {a.id}")
        if not a.loop:
            exit_cond += " || query.all_animations_finished"
        states[f"a_{a.name}"] = {
            "animations": [a.name],
            "on_entry": ["variable.joan_seq = query.property('joan:seq');"],
            "transitions": [{"none": exit_cond}],
            "blend_transition": 0.1,
        }
    return {"format_version": "1.10.0", "animation_controllers": {
        "controller.animation.joan.action": {"initial_state": "none", "states": states}}}


# =========================================================================== minor entities
def minor_animations() -> Dict[str, dict]:
    t = "query.life_time"
    A: Dict[str, dict] = {}
    # phantom standard: rises from the earth, flutters, fades by collapsing
    st = {"loop": True, "bones": {}}
    for i in range(4):
        st["bones"][f"cloth_{i}"] = {"rotation": [f"-6 + math.sin({t} * 160 - {i * 50}) * {3 + i * 2}",
                                                  f"math.sin({t} * 230 - {i * 70}) * {14 + i * 6}", 0]}
    A["animation.joan.standard.idle"] = st
    A["animation.joan.standard.rise"] = {"loop": False, "animation_length": 0.6, "bones": {
        "root": {"position": {"0.0": [0, -44, 0], "0.45": [0, 1.5, 0], "0.6": [0, 0, 0]},
                 "rotation": {"0.0": [0, 0, 18], "0.6": [0, 0, 0]}}}}
    # stake
    A["animation.joan.stake.rise"] = {"loop": False, "animation_length": 2.0, "bones": {
        "root": {"position": {"0.0": [0, -62, 0], "1.6": [0, 1.0, 0], "2.0": [0, 0, 0]}}}}
    A["animation.joan.stake.idle"] = {"loop": True, "bones": {
        "flames": {"scale": [f"0.35 + query.property('joan:stake') * 0.55 + math.sin({t} * 520) * 0.04",
                             f"0.25 + query.property('joan:stake') * 0.9 + math.sin({t} * 700) * 0.08",
                             f"0.35 + query.property('joan:stake') * 0.55"]},
        "post": {"rotation": [0, 0, f"math.sin({t} * 90) * 0.6"]},
    }}
    A["animation.joan.stake.purified"] = {"loop": True, "bones": {"flames": {"scale": 0.0}}}
    A["animation.joan.stake.sink"] = {"loop": False, "animation_length": 1.5, "bones": {
        "root": {"position": {"0.0": [0, 0, 0], "1.5": [0, -64, 0]}}}}
    # lily waystone: float + spin; flips 180 degrees when its road is reversed
    A["animation.joan.waystone.idle"] = {"loop": True, "bones": {
        "root": {"position": [0, f"math.sin({t} * 120) * 1.2", 0]},
        "lily": {"rotation": [0, f"{t} * 70", 0]},
        "ring": {"rotation": [f"math.sin({t} * 50) * 12", f"-{t} * 140", 0]},
    }}
    A["animation.joan.waystone.turned"] = {"loop": "hold_on_last_frame", "animation_length": 0.5, "bones": {
        "lily": {"rotation": {"0.0": [0, 0, 0], "0.5": [0, 0, 180]}}}}
    # seraph light
    A["animation.joan.seraph.fly"] = {"loop": True, "bones": {
        "wing_r": {"rotation": [0, 0, f"math.sin({t} * 1300) * 35 + 10"]},
        "wing_l": {"rotation": [0, 0, f"-math.sin({t} * 1300) * 35 - 10"]},
        "wing_r2": {"rotation": [0, 0, f"math.sin({t} * 1300 - 40) * 28 + 20"]},
        "wing_l2": {"rotation": [0, 0, f"-math.sin({t} * 1300 - 40) * 28 - 20"]},
        "core": {"rotation": [0, f"{t} * 360", 0]},
    }}
    return A


def echo_march(sampler: Sampler) -> Dict[str, dict]:
    """Procession echoes march with the standard held high."""
    raised = P(GUARD, arm_r=(-150, 0, 10), forearm_r=(-20, 0, 0), head=(-10, 0, 0))
    m1 = P(raised, leg_r=(-30, 0, 0), shin_r=(10, 0, 0), leg_l=(30, 0, 0), shin_l=(30, 0, 0), arm_l=(30, 0, -10))
    m2 = P(raised, leg_r=(30, 0, 0), shin_r=(30, 0, 0), leg_l=(-30, 0, 0), shin_l=(10, 0, 0), arm_l=(-30, 0, -10))
    act = Action("echo_march", -2, 1.0, [Key(0.0, m1, (d(0, 1, 0.1), BACK), vel=(0, 0, -4)),
                                         Key(0.5, m2, (d(0, 1, 0.1), BACK), vel=(0, 0, -4))], loop=True)
    j = action_json(act, sampler.bake(act))
    return {"animation.joan.echo.march": j}


def build(rp_dir: str, ts_path: str) -> Dict[str, object]:
    sampler = Sampler()
    acts = actions()
    ids = [a.id for a in acts]
    assert len(ids) == len(set(ids)), "duplicate action ids"
    anim: Dict[str, dict] = {}
    anim.update(base_layers(sampler))
    anim.update(cloth_loops(sampler))
    meta = []
    for a in acts:
        j = action_json(a, sampler.bake(a))
        if a.name == "death":
            j["bones"].setdefault("root", {})["scale"] = {"0.0": [1, 1, 1], "5.2": [1, 1, 1], "6.0": [0.05, 0.05, 0.05]}
        anim[a.name] = j
        meta.append((a.name, a.id, a.length, a.loop))
    full = {f"animation.joan.{k}" if not k.startswith("animation.") else k: v for k, v in anim.items()}
    os.makedirs(os.path.join(rp_dir, "animations"), exist_ok=True)
    with open(os.path.join(rp_dir, "animations", "joan.animation.json"), "w") as f:
        json.dump({"format_version": "1.8.0", "animations": full}, f, separators=(",", ":"))
    minor = minor_animations()
    minor.update(echo_march(sampler))
    with open(os.path.join(rp_dir, "animations", "joan_minor.animation.json"), "w") as f:
        json.dump({"format_version": "1.8.0", "animations": minor}, f, indent=1)
    os.makedirs(os.path.join(rp_dir, "animation_controllers"), exist_ok=True)
    with open(os.path.join(rp_dir, "animation_controllers", "joan.animation_controllers.json"), "w") as f:
        json.dump(action_controller(acts), f, indent=1)
    # shared ids for the scripts
    os.makedirs(os.path.dirname(ts_path), exist_ok=True)
    lines = ["// GENERATED by tools/anims.py - do not edit.", "/* eslint-disable */",
             "export const ACT = {", "  none: 0,"]
    lines += [f"  {n}: {i}," for n, i, _, _ in meta]
    lines += ["} as const;", "export type ActName = keyof typeof ACT;",
              "/** Length of every action animation in ticks (20 tps). */",
              "export const ACT_TICKS: Record<number, number> = {"]
    lines += [f"  {i}: {int(round(length * 20))}," for _, i, length, _ in meta]
    lines += ["};", "export const ACT_LOOPS: Record<number, boolean> = {"]
    lines += [f"  {i}: {'true' if loop else 'false'}," for _, i, _, loop in meta]
    lines += ["};", ""]
    with open(ts_path, "w") as f:
        f.write("\n".join(lines))
    return {"actions": meta, "animation_names": sorted(full), "minor": sorted(minor)}


if __name__ == "__main__":
    import time
    t0 = time.time()
    res = build(sys.argv[1] if len(sys.argv) > 1 else "build/anim_test", "src/generated/anims.ts")
    print(len(res["actions"]), "actions", round(time.time() - t0, 1), "s")
