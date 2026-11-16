"""Animation sets for the three race forms (attachable-side) and the player
skeleton poses that scripts trigger with Entity.playAnimation().

Each form runs a stack of layers (see anims/life.py):
  life        breathing, heartbeat, blinking, weight shift, micro head moves (standing)
  detail      small parts that also show in first person (forearm lobes, pebbles)
  locomotion  race-specific gait on top of the player's own walk cycle
  airborne    take-off stretch / fall reach (driven by q.vertical_speed)
  landing     controller: squash on landing (soft / hard), dust
  attack      reaction to the player's melee swing (v.attack_time)
  hurt        keyframed flinch, restarted on every hit
  fidget      controller: idle behaviours after standing still for a while
  + the form's intro transition, state loop and particle loop.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from anims.core import Anim, NS, VSWING, WALK, PHASE, T, osc, n
from anims.life import (ATK, BUMP, C, CSTEP, EMPTY_L, EMPTY_R, FALL, IMPACT, LOOK, MOVE, PH, POS, RISE, S, SPR,
                        SQ, STEP, STILL, TCOS, TURN, WALKING, KeyLayer, Layer, Rig, arm_swing, body, body_keys,
                        fidget_controller, landing_controller, lin, mul, pendulum_bob, prod, stride, wait_anim)
from anims.fit import foot_floor, ground_bob
from models.common import THIRD_PERSON_ONLY, FIRST_PERSON_ONLY

AIR = "!q.is_on_ground && !q.is_in_water"
DAY = "(q.time_of_day > 0.25 && q.time_of_day < 0.75)"
SUN = f"({DAY} ? math.sin((q.time_of_day - 0.25) * 360) : -0.35)"
TP = "!c.is_first_person"
GAIT_OK = "!q.is_riding && !q.is_gliding"   # mounts and elytra pose the legs themselves
SIDES = (("r", -1), ("l", 1))   # prefix, side (-1 = creature's right)


def A(race: str, name: str, **kw) -> Anim:
    return Anim(f"animation.{NS}.{race}.{name}", **kw)


def view_anims(race: str) -> Tuple[Anim, Anim]:
    fp = A(race, "first_person")
    for b in THIRD_PERSON_ONLY:
        fp.bone(b, scale=0)
    tp = A(race, "third_person")
    for b in FIRST_PERSON_ONLY:
        tp.bone(b, scale=0)
    return fp, tp


def transition(model, race: str, name: str, frm: str, to: str, length: float, ease=(0.0, 1.0)) -> Anim:
    """Animate every bone whose rest pose differs between two variants, from the
    `frm` pose into the `to` pose (the geometry of `to` is the rest state)."""
    a = A(race, name, loop="hold", length=length)
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        r_from = np.array(model.bone_rot(bn, frm), float)
        r_to = np.array(model.bone_rot(bn, to), float)
        dr = r_from - r_to
        t_from = _own_offset(model, bn, frm)
        t_to = _own_offset(model, bn, to)
        dt = t_from - t_to
        kf_r = {} if np.allclose(dr, 0, atol=0.01) else {0.0: list(dr), length * 0.6: list(dr * 0.15), length: [0, 0, 0]}
        kf_t = {} if np.allclose(dt, 0, atol=0.01) else {0.0: list(dt), length * 0.6: list(dt * 0.12), length: [0, 0, 0]}
        if kf_r or kf_t:
            a.bone(bn, rot=kf_r or None, pos=kf_t or None)
    return a


def _own_offset(model, bn, variant):
    b = model.bones[bn]
    if variant in b.variant:
        return np.array(b.variant[variant][0], float)
    return np.zeros(3)


FIT_REPORT: List[str] = []
BOB_EXPR: Dict[str, str] = {}
WALK_REF = 0.8   # walking speed the walk fit is made at (modified_move_speed)


def grounded(model, loco: Layer, rig: Rig, race: str, sprint_clearance=None, upper_only=None, harmonics: int = 4) -> None:
    """Add the fitted body bob that keeps the feet on the ground (walk + sprint)."""
    walk = ground_bob(model, [loco.anim()], WALK_REF, False, harmonics=harmonics, report=FIT_REPORT, label=f"{race} walk")
    run = ground_bob(model, [loco.anim()], 1.0, True, harmonics=harmonics, clearance=sprint_clearance, report=FIT_REPORT,
                     label=f"{race} sprint")
    rest = float(foot_floor(model, [loco.anim()], 0.0, False, samples=1)[0])
    FIT_REPORT.append(f"{race} rest foot floor {rest:+.2f}")
    wscale = f"math.clamp(q.modified_move_speed / {WALK_REF}, 0, 1.25)"
    bob = lin([(1.0, prod(WALKING, wscale, f"({walk}) - ({-rest:.3f})")),
               (1.0, prod(SPR, MOVE, f"({run}) - ({-rest:.3f})"))])
    # computed once per frame (pre_animation), referenced by every group it moves
    BOB_EXPR[race] = bob
    body(loco, rig, bob=f"v.plr_bob")


def pre_animation(race: str) -> List[str]:
    """Per-frame shared values for the race's attachables (see life.SHARED)."""
    from anims.life import compact, shared_vars
    return shared_vars() + [f"v.plr_bob = {compact(BOB_EXPR[race])};"]


def blink(period_a: float, period_b: float, dur: float, off: float) -> str:
    return f"math.max({BUMP(period_a, dur)}, {BUMP(period_b, dur, off)})"


def heartbeat(period: float) -> str:
    """lub-dub: a strong pulse followed by a weaker one."""
    return f"({BUMP(period, 0.13)} + 0.6 * {BUMP(period, 0.15, -0.21)})"


def mirror(side: int, e):
    """Value authored for the right side (-1); mirrored (negated) for the left."""
    if e is None:
        return None
    return e if side < 0 else mul(-1.0, e)


def sweep(t0: float, t1: float, v0, v1, steps: int = 3) -> Dict[float, object]:
    """Keys easing from v0 to v1 between t0 and t1 (smoothstep)."""
    out = {}
    for k in range(steps + 1):
        a = k / steps
        e = a * a * (3 - 2 * a)
        out[round(t0 + (t1 - t0) * a, 3)] = np.array(v0, float) * (1 - e) + np.array(v1, float) * e
    return out


def hold(times_vals) -> Dict[float, object]:
    return {round(t, 3): v for t, v in times_vals}


def shake(t0: float, dur: float, amp, freq: float = 7.0, decay: float = 3.5, steps_per: int = 4) -> Dict[float, object]:
    """Damped oscillation keys (a body shake / head shake / wobble)."""
    out = {round(t0, 3): np.zeros(3)}
    n_ = int(dur * freq * steps_per)
    for k in range(1, n_ + 1):
        t = dur * k / n_
        v = np.array(amp, float) * math.sin(2 * math.pi * freq * t) * math.exp(-decay * t)
        out[round(t0 + t, 3)] = v
    out[round(t0 + dur + 0.05, 3)] = np.zeros(3)
    return out


# ============================================================================ salamander

SAL_RIG = Rig("torso", (0, 12, 0), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])


def salamander(model) -> Dict[str, object]:
    r = "salamander"
    rig = SAL_RIG
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life (standing / always, third person)
    life = Layer(r, "life", loop=True)
    br = S(0.3)                                   # slow amphibian breath (3.3 s)
    life.scale("torso", f"1 + 0.012 * {br}", None, f"1 + 0.024 * {br}")
    for arm in ("r_arm_g", "l_arm_g"):
        life.pos(arm, None, mul(0.22, br))
    life.pos("head_g", None, mul(0.16, S(0.3, -40)))
    body(life, rig,
         lean=lin([(1.3, prod(S(0.07, 60), STILL)), (-0.5, br)]),
         roll=prod(1.8, S(0.11), STILL),
         twist=prod(2.2, S(0.09, 120), STILL))
    # head: slow looks, curious tilts, counter-tilt against the weight shift
    life.rot("head_g", prod(lin([(2.0, S(0.17, 10)), (1.4, SQ(0.23, 200, 3))]), STILL),
             prod(lin([(5.0, SQ(0.13, 30, 3)), (2.0, S(0.41, 80))]), STILL),
             prod(lin([(-1.1, S(0.11)), (3.0, SQ(0.071, 140, 2.5))]), STILL))
    # buccal pumping: the throat flutters, with a deep gulp every few seconds
    life.scale("gular", 1.04, lin([(1.0, 1.0), (0.8, f"math.pow({POS(S(1.4))}, 2)"), (1.7, BUMP(5.1, 0.7))]), 1.04)
    life.rot("jaw", lin([(1.5, POS(S(0.3, 30))), (4.0, BUMP(5.1, 0.7))]))
    life.uscale("viscera", lin([(1.0, 1.0), (0.07, heartbeat(0.95))]))
    for p, side in SIDES:
        life.scale(f"{p}_lid", None, lin([(1.0, 1.0), (7.4, f"math.max({blink(4.4, 7.3, 0.2, 2.2)}, q.is_sleeping)")]), None)
        for k in range(3):
            life.rot(f"gill_{p}{k}", lin([(5.0, S(0.45, k * 50)), (2.0, S(1.4, k * 90))]),
                     mirror(side, lin([(8.0, S(0.45, k * 50 + 90)), (3.0, S(1.4, 40 + k * 70))])), None)
        for k in range(4):
            life.rot(f"plate_{p}{k}", None, None,
                     mirror(side, lin([(3.0, S(0.28, k * 45)), (9.0, SUN), (1.0, f"(q.modified_move_speed < 0.05 && {DAY} ? 7 : 0)")])))
        # toes curl and spread now and then
        for k in range(4):
            life.rot(f"{p}_toe{k}", prod(-9, BUMP(6.3, 0.5, k * 0.08 + (0 if side < 0 else 2.9))))
    for k in range(4):
        life.rot(f"tail{k}", lin([(1.5, S(0.25, k * 30)), (2.0, prod(S(0.13, -k * 25), STILL))]),
                 lin([(3.0 + k * 2.5, S(0.22, -k * 40)), (-0.06 * (1 + k * 0.4), LOOK)]), None)
    for k in range(5):
        life.rot(f"petal{k}_l", lin([(4.0, S(0.3, k * 72)), (-6.0, BUMP(7.7, 1.6, 3.0))]))

    detail = Layer(r, "detail", loop=True)      # forearm parts (visible in first person too)
    for p, side in SIDES:
        detail.rot(f"{p}_lobe0", osc(0.6, 2, 30))
        detail.rot(f"{p}_tendril0", osc(0.7, 6, 10), None, osc(0.5, 4))
        detail.rot(f"{p}_tendril1", osc(0.6, 7, 70), None, osc(0.45, 4, 40))

    # ------------------------------------------------------------------ locomotion
    loco = Layer(r, "locomotion", loop=True)
    keep = 0.46
    stride(loco, keep)
    arm_swing(loco, 0.62)
    s = MOVE
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"          # + while this leg swings forward
        st = CSTEP() if side < 0 else f"-{CSTEP()}"        # + while this leg pushes off at the back
        knee = prod(POS(sw), s, lin([(30, 1), (14, SPR)]))
        loco.rot(f"{p}_shin", knee)
        # the sole stays flat on the ground against the stride angle and the knee bend, then rolls off the toes
        flat = prod(side * keep * 1.4, TCOS)
        loco.rot(f"{p}_foot", lin([(1.0, flat), (-0.8, knee), (16, prod(POS(st), s))]))
        for k in range(4):
            loco.rot(f"{p}_toe{k}", prod(-12, POS(sw), s))
        arm_fwd = CSTEP() if side < 0 else f"-{CSTEP()}"   # + while this arm is forward
        loco.rot(f"{p}_fore", prod(-16, POS(arm_fwd), s, EMPTY_R if side < 0 else EMPTY_L))
        loco.rot(f"{p}_arm_g", None, None, mirror(side, prod(9, SPR, s, EMPTY_R if side < 0 else EMPTY_L)))
        for k in range(3):
            loco.rot(f"gill_{p}{k}", prod(-13, s), mirror(side, prod(lin([(6, S(2.6, k * 80))]), s)), None)
        for k in range(4):
            loco.rot(f"plate_{p}{k}", None, None, mirror(side, prod(4, f"math.sin({PH} * 2 - {80 + k * 25})", s)))
        loco.rot(f"{p}_lobe0", prod(6, f"math.sin({PH} * 2 - 50)", s))
        loco.rot(f"{p}_lobe1", prod(-6, f"math.sin({PH} * 2 - 50)", s))
        loco.rot(f"{p}_tendril0", prod(9, f"math.cos({PH} - 60)" if side < 0 else f"-math.cos({PH} - 60)", s))
        loco.rot(f"{p}_tendril1", prod(9, f"math.cos({PH} - 80)" if side < 0 else f"-math.cos({PH} - 80)", s))
    body(loco, rig,
         lean=lin([(5, s), (6, prod(SPR, s))]),
         roll=lin([(3.2, prod(STEP(), s)), (4.0, prod(TURN, s))]),
         twist=lin([(-5.5, prod(CSTEP(), s)), (0.12, LOOK)]))
    loco.rot("head_g", lin([(-2.5, s), (-3, prod(SPR, s)), (1.5, prod(f"math.sin({PH} * 2 - 60)", s))]),
             prod(4.2, CSTEP(), s), prod(-1.6, STEP(-20), s))
    grounded(model, loco, rig, r)
    amp = lin([(1.0, 1.0), (0.5, SPR)])
    for k in range(4):
        a_k = 7 + 2 * k
        loco.rot(f"tail{k}",
                 lin([(3 if k == 0 else 0, s), (8 if k == 0 else 0, prod(SPR, s)), (2.5, prod(f"math.sin({PH} * 2 - {70 + 35 * k})", s))]),
                 lin([(a_k, prod(CSTEP(-40 - 45 * k), s, amp)), (-7.0 * (1 + 0.35 * k), prod(TURN, s))]), None)

    # ------------------------------------------------------------------ airborne
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        air.rot(f"{p}_thigh", lin([(-24, RISE), (-8, FALL)]))
        air.rot(f"{p}_shin", lin([(38, RISE), (10, FALL)]))
        air.rot(f"{p}_foot", lin([(-14, RISE), (12, FALL)]))
        for k in range(4):
            air.rot(f"{p}_toe{k}", None, mirror(side, prod((k - 1.5) * 9, lin([(1, 1), (0.5, FALL)]))), None)
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"{p}_arm_g", prod(-10, FALL, e), None, mirror(side, prod(lin([(5, RISE), (16, FALL)]), e)))
        for k in range(3):
            air.rot(f"gill_{p}{k}", lin([(-10, RISE)]), mirror(side, prod(-14, FALL)), None)
        for k in range(4):
            air.rot(f"plate_{p}{k}", None, None, mirror(side, prod(10, FALL)))
    air.rot("tail0", lin([(-16, RISE), (12, FALL)]))
    for k in range(1, 4):
        air.rot(f"tail{k}", lin([(-5, RISE), (6, FALL)]))
    body(air, rig, lean=lin([(-4, RISE), (5, FALL)]))
    air.rot("head_g", lin([(3, RISE), (-4, FALL)]))

    # ------------------------------------------------------------------ landing (soft / hard)
    land = KeyLayer(r, "land", 0.5)
    land_hard = KeyLayer(r, "land_hard", 0.75)
    for kl, g in ((land, 1.0), (land_hard, 1.45)):
        L = kl.length
        tk = [0.0, 0.1 * g, 0.28 * g, L]
        for p, side in SIDES:
            kl.rot(f"{p}_thigh", {tk[0]: (-38 * g, 0, 0), tk[1]: (-42 * g, 0, 0), tk[2]: (-6, 0, 0), tk[3]: (0, 0, 0)})
            kl.rot(f"{p}_shin", {tk[0]: (66 * g, 0, 0), tk[1]: (72 * g, 0, 0), tk[2]: (10, 0, 0), tk[3]: (0, 0, 0)})
            kl.rot(f"{p}_foot", {tk[0]: (-28 * g, 0, 0), tk[1]: (-30 * g, 0, 0), tk[2]: (-4, 0, 0), tk[3]: (0, 0, 0)})
            for k in range(3):
                kl.rot(f"gill_{p}{k}", {0: (0, 0, 0), tk[1]: (8, -18 * g if side < 0 else 18 * g, 0), tk[3]: (0, 0, 0)})
            for k in range(4):
                kl.rot(f"plate_{p}{k}", {0: (0, 0, 0), tk[1] + 0.03: (0, 0, (12 if side < 0 else -12) * g), tk[3]: (0, 0, 0)})
        drop = min(2.0 * g, 2.6)
        body_keys(kl, rig, {tk[0]: {"bob": -drop * 0.9, "lean": 8 * g}, tk[1]: {"bob": -drop, "lean": 10 * g},
                            tk[2]: {"bob": 0.3, "lean": -2}, tk[3]: {}})
        kl.rot("tail0", {0: (-14 * g, 0, 0), 0.15 * g: (-18 * g, 0, 0), 0.35 * g: (4, 0, 0), L: (0, 0, 0)})
        kl.rot("tail2", {0: (0, 0, 0), 0.2 * g: (-8, 0, 0), 0.4 * g: (3, 0, 0), L: (0, 0, 0)})
        kl.rot("head_g", {0: (-6 * g, 0, 0), 0.12 * g: (-8 * g, 0, 0), 0.3 * g: (3, 0, 0), L: (0, 0, 0)})
        kl.scale("gular", {0: 1, 0.08: (1.05, 2.2, 1.05), 0.3: 1, L: 1})
        kl.particle(0.0, "landdust" if g > 1 else "stepdust", "r_step")
        kl.particle(0.0, "landdust" if g > 1 else "stepdust", "l_step")

    # ------------------------------------------------------------------ attack reaction (stateless)
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(7, ATK), twist=prod(-7, ATK))
    atk.rot("head_g", prod(6, ATK))
    atk.rot("jaw", prod(18, ATK))
    atk.rot("r_lobe0", prod(24, ATK))
    atk.rot("r_lobe1", prod(-24, ATK))
    atk.rot("tail0", None, prod(10, ATK))
    atk.rot("tail2", None, prod(-9, ATK))
    for p, side in SIDES:
        for k in range(3):
            atk.rot(f"gill_{p}{k}", None, mirror(side, prod(-12, ATK)))

    # ------------------------------------------------------------------ hurt
    hurt = KeyLayer(r, "hurt", 0.55)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -9, "roll": 4}, 0.18: {"lean": 4, "roll": -2}, 0.38: {"lean": -1}, 0.55: {}})
    hurt.rot("head_g", {0: (0, 0, 0), 0.05: (-10, 0, 0), 0.2: (5, 0, 0), 0.55: (0, 0, 0)})
    hurt.rot("jaw", {0: (0, 0, 0), 0.05: (18, 0, 0), 0.25: (6, 0, 0), 0.55: (0, 0, 0)})
    hurt.rot("tail0", {0: (0, 0, 0), 0.05: (6, 22, 0), 0.2: (0, -14, 0), 0.38: (0, 6, 0), 0.55: (0, 0, 0)})
    hurt.rot("tail2", {0: (0, 0, 0), 0.08: (0, -18, 0), 0.25: (0, 16, 0), 0.45: (0, -5, 0), 0.55: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.scale(f"{p}_lid", {0: 1, 0.04: (1, 8.4, 1), 0.3: (1, 8.4, 1), 0.42: 1})
        for k in range(3):
            hurt.rot(f"gill_{p}{k}", {0: (0, 0, 0), 0.05: (-12, 26 * sg, 0), 0.3: (0, 8 * sg, 0), 0.55: (0, 0, 0)})
        for k in range(4):
            hurt.rot(f"plate_{p}{k}", {0: (0, 0, 0), 0.05: (0, 0, -14 * sg), 0.55: (0, 0, 0)})
        hurt.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.05: (-14, 0, -10 * sg), 0.3: (0, 0, 0)})

    # ------------------------------------------------------------------ swimming
    swim = A(r, "swim", loop=True, length=1.6)
    # in the vanilla swim pose the body lies horizontal: swing the tail back along the body axis
    swim.bone("tail0", rot=[f"-76 * (q.is_swimming ? 1 : 0.35) + {osc(0.55, 3)}", osc(1.15, 14, 0), 0])
    for k in range(1, 4):
        swim.bone(f"tail{k}", rot=[osc(0.55, 3, -k * 30), osc(1.15, 14 + k * 8, -k * 58), 0])
    swim.bone("torso", rot=[0, osc(1.15, 7, 40), 0])
    for p, side in SIDES:
        swim.bone(f"{p}_thigh", rot=[f"22 + {osc(1.15, 10, 0 if side < 0 else 180)}", 0, f"{-side} * -10"])
        swim.bone(f"{p}_shin", rot=[f"18 + {osc(1.15, 16, 60 if side < 0 else 240)}", 0, 0])
        for k in range(3):
            swim.bone(f"gill_{p}{k}", rot=[-24, f"{osc(1.15, 9, k * 40)}", 0])
        for k in range(4):
            swim.bone(f"plate_{p}{k}", rot=[0, 0, f"-18 * {-side}"])
    swim.bone("gular", scale=[1, f"1 + 0.6 * {POS(S(1.2))}", 1])
    swim.particle(0.0, "bubbles", "mouth")

    # ------------------------------------------------------------------ idle fidgets
    fid = []
    # tastes the air: lifts the head and flicks the sticky tongue twice
    taste = KeyLayer(r, "fidget_taste", 2.3)
    taste.rot("head_g", {0: (0, 0, 0), 0.35: (-12, 0, 0), 1.4: (-12, 0, 0), 1.7: (-6, 0, 9), 2.0: (-4, 0, 9), 2.3: (0, 0, 0)})
    taste.rot("jaw", {0: (0, 0, 0), 0.4: (0, 0, 0), 0.5: (12, 0, 0), 0.75: (9, 0, 0), 1.15: (12, 0, 0), 1.4: (0, 0, 0), 2.3: (0, 0, 0)})
    taste.pos("tongue", {0: (0, 0, 0), 0.5: (0, 0, 0), 0.6: (0, -0.6, -4.8), 0.72: (0, 0, 0), 1.18: (0, 0, 0), 1.28: (0, -0.8, -5.2), 1.4: (0, 0, 0), 2.3: (0, 0, 0)})
    taste.scale("tongue", {0: 1, 0.5: 1, 0.6: (1, 1, 1.7), 0.72: 1, 1.18: 1, 1.28: (1, 1, 1.8), 1.4: 1, 2.3: 1})
    taste.scale("gular", {0: 1, 1.5: 1, 1.75: (1.06, 2.6, 1.06), 2.05: 1, 2.3: 1})
    fid.append(taste)
    # shakes its head; gills slap, spores fly
    shk = KeyLayer(r, "fidget_shake", 1.9)
    shk.rot("head_g", {**shake(0.1, 1.0, (0, 16, 5), freq=4.5, decay=3.0), 1.9: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        for k in range(3):
            shk.rot(f"gill_{p}{k}", {**shake(0.15 + k * 0.03, 1.1, (8, 22 * sg, 0), freq=4.5, decay=2.5), 1.9: (0, 0, 0)})
        for k in range(4):
            shk.rot(f"plate_{p}{k}", {**shake(0.2 + k * 0.04, 0.9, (0, 0, 9 * sg), freq=9, decay=3.5), 1.9: (0, 0, 0)})
    shk.rot("tail2", {**shake(0.3, 1.0, (0, 14, 0), freq=3, decay=2), 1.9: (0, 0, 0)})
    shk.particle(0.3, "spores", "spores").particle(0.25, "drip", "mouth")
    fid.append(shk)
    # tail curl: brings the flower round to look at it, petals open, pollen drifts
    curl = KeyLayer(r, "fidget_tail", 2.8)
    for k, a in enumerate((16, 22, 26, 30)):
        curl.rot(f"tail{k}", {0: (0, 0, 0), 0.6: (6, a, 0), 2.0: (6, a, 0), 2.8: (0, 0, 0)})
    curl.rot("head_g", {0: (0, 0, 0), 0.6: (8, -32, 8), 2.0: (8, -32, 8), 2.4: (0, -6, 0), 2.8: (0, 0, 0)})
    body_keys(curl, rig, {0: {}, 0.6: {"twist": -6}, 2.0: {"twist": -6}, 2.8: {}})
    for k in range(5):
        curl.rot(f"petal{k}_l", {0: (0, 0, 0), 0.9: (0, 0, 0), 1.3: (-24, 0, 0), 1.7: (-20, 0, 0), 2.2: (0, 0, 0), 2.8: (0, 0, 0)})
    curl.particle(1.3, "pollen", "pollen")
    fid.append(curl)
    # big stretch & yawn (hands empty): arms up, jaw wide, plates fan out
    yawn = KeyLayer(r, "fidget_stretch", 3.0)
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        yawn.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.7: (-140, 0, -18 * sg), 1.6: (-152, 0, -22 * sg), 2.3: (-20, 0, -4 * sg), 2.7: (0, 0, 0), 3.0: (0, 0, 0)})
        yawn.rot(f"{p}_fore", {0: (0, 0, 0), 0.7: (-20, 0, 0), 1.6: (-10, 0, 0), 2.3: (0, 0, 0)})
        yawn.scale(f"{p}_lid", {0: 1, 0.8: 1, 1.0: (1, 8.4, 1), 1.6: (1, 8.4, 1), 1.8: 1, 3.0: 1})
        for k in range(4):
            yawn.rot(f"plate_{p}{k}", {0: (0, 0, 0), 0.9: (0, 0, -20 * sg), 1.7: (0, 0, -22 * sg), 2.4: (0, 0, 0)})
        for k in range(3):
            yawn.rot(f"gill_{p}{k}", {0: (0, 0, 0), 0.9: (-14, -20 * sg, 0), 1.7: (-14, -24 * sg, 0), 2.4: (0, 0, 0)})
    yawn.rot("jaw", {0: (0, 0, 0), 0.6: (4, 0, 0), 1.0: (26, 0, 0), 1.6: (26, 0, 0), 1.9: (0, 0, 0), 3.0: (0, 0, 0)})
    yawn.scale("gular", {0: 1, 0.9: (1.08, 2.4, 1.08), 1.6: (1.08, 2.4, 1.08), 1.9: 1, 3.0: 1})
    body_keys(yawn, rig, {0: {}, 0.8: {"lean": -8, "bob": 0.6}, 1.6: {"lean": -10, "bob": 0.8}, 2.3: {"lean": 2}, 3.0: {}})
    yawn.rot("head_g", {0: (0, 0, 0), 0.8: (-14, 0, 0), 1.6: (-16, 0, 0), 2.2: (0, 0, 0)})
    yawn.rot("tail0", {0: (0, 0, 0), 0.9: (14, 0, 0), 1.6: (16, 0, 0), 2.4: (0, 0, 0)})
    fid.append(yawn)
    picks = [("fidget_taste", "math.mod(math.floor(q.life_time * 1.7), 5) == 0"),
             ("fidget_shake", "math.mod(math.floor(q.life_time * 1.7), 5) == 1"),
             ("fidget_tail", "math.mod(math.floor(q.life_time * 1.7), 5) == 2"),
             ("fidget_stretch", "math.mod(math.floor(q.life_time * 1.7), 5) == 3 && !q.is_item_equipped(0) && !q.is_item_equipped(1)")]

    # ------------------------------------------------------------------ state intros / loops
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.6),
        "bloom": transition(model, r, "intro_bloom", "base", "bloom", 1.3),
        "dormant": transition(model, r, "intro_dormant", "base", "dormant", 2.2),
        "predatory": transition(model, r, "intro_predatory", "base", "predatory", 0.3),
        "rooted": transition(model, r, "intro_rooted", "base", "rooted", 1.0),
    }
    for p in ("r", "l"):
        intro["rooted"].bone(f"{p}_roots", scale={0.0: [1, 0.05, 1], 0.7: [1, 1.08, 1], 1.0: [1, 1, 1]})
        intro["predatory"].bone(f"{p}_tendril0x", scale={0.0: [1, 0.1, 1], 0.3: [1, 1, 1]})
        intro["predatory"].bone(f"{p}_tendril1x", scale={0.0: [1, 0.1, 1], 0.3: [1, 1, 1]})
    for p, s_ in SIDES:
        for k in range(4):
            intro["base"].bone(f"plate_{p}{k}", rot={0.0: [0, 0, 0], 0.15: [0, 0, 9 * -s_], 0.35: [0, 0, -4 * -s_], 0.6: [0, 0, 0]})
    intro["rooted"].particle(0.0, "rootburst", "spores")
    intro["bloom"].particle(0.2, "dew", "spores")
    intro["dormant"].particle(0.4, "flakes", "spores")
    intro["predatory"].particle(0.0, "drip", "mouth")

    pred = Layer(r, "predatory_loop", loop=True)          # agitated: quick breaths, lashing tail, twitching jaw
    for p, side in SIDES:
        pred.rot(f"{p}_lobe0", osc(2.2, 5))
        pred.rot(f"{p}_lobe1", osc(2.2, -5, 40))
        pred.rot(f"{p}_tendril0x", osc(1.6, 10), None, osc(1.1, 8))
        pred.rot(f"{p}_tendril1x", osc(1.4, 12, 60), None, osc(1.0, 8, 30))
    pred.rot("jaw", lin([(3, S(1.8)), (5, BUMP(2.9, 0.25))]))
    pred.rot("tail3", None, lin([(10, S(1.6)), (6, S(2.3, 50))]))
    pred.rot("tail2", None, mul(6, S(1.6, -40)))
    pred.scale("gular", 1, lin([(1, 1), (0.5, POS(S(2.6)))]), 1)
    pred.rot("head_g", mul(-3, STILL), prod(lin([(6, SQ(0.35, 0, 6))]), STILL), None)
    dorm = Layer(r, "dormant_loop", loop=True)            # parched: heavy lids, drooping head, slow shallow breaths
    dorm.scale("torso", lin([(1, 1), (0.008, S(0.18))]), 1, 1)
    for p, side in SIDES:
        dorm.scale(f"{p}_lid", None, lin([(4.2, 1), (1.5, S(0.18))]), None)
        for k in range(3):
            dorm.rot(f"gill_{p}{k}", 10, None, None)
    dorm.rot("head_g", lin([(7, 1), (2, S(0.12))]))
    for k in range(4):
        dorm.rot(f"tail{k}", -4 if k == 0 else -2)
    bloom = Layer(r, "bloom_loop", loop=True)             # content: petals breathe, plates sway in the light
    for k in range(5):
        bloom.rot(f"petal{k}_l", mul(7, S(0.24, k * 30)))
    for p, side in SIDES:
        for k in range(4):
            bloom.rot(f"plate_{p}{k}", None, None, mirror(side, mul(5, S(0.19, k * 35 + 20))))
    root = Layer(r, "rooted_loop", loop=True)             # sways like a plant in a breeze
    for p in ("r", "l"):
        for k in range(5):
            root.rot(f"{p}_root{k}", osc(0.4, 2.5, k * 50), None, osc(0.33, 2.5, k * 70))
    body(root, rig, roll=lin([(2.4, S(0.16)), (1.0, S(0.43, 30))]), lean=mul(1.2, S(0.11, 70)))
    for k in range(4):
        root.rot(f"tail{k}", None, mul(4 + 2 * k, S(0.16, -40 - k * 30)))

    fx = {
        "bloom": A(r, "fx_bloom", length=2.4).particle(0.0, "spores", "spores").particle(1.2, "pollen", "pollen"),
        "dormant": A(r, "fx_dormant", length=3.0).particle(0.0, "flakes", "spores"),
        "predatory": A(r, "fx_predatory", length=1.2).particle(0.0, "drip", "mouth"),
        "rooted": A(r, "fx_rooted", length=2.0).particle(0.0, "spores", "spores"),
        "base": A(r, "fx_base", length=4.0).particle(0.0, "drip", "mouth"),
    }
    anims = [fp, tp, life.anim(), detail.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), swim, pred.anim(), dorm.anim(), bloom.anim(), root.anim(),
             wait_anim(r, "fidget_wait", 6.5), wait_anim(r, "fidget_rest", 3.0), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r), **fidget_controller(r, picks)}
    animate = {}
    loops = {"predatory": ("predatory_loop", None), "dormant": ("dormant_loop", TP), "rooted": ("rooted_loop", TP),
             "bloom": ("bloom_loop", TP)}
    for v in ("base", "bloom", "dormant", "predatory", "rooted"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP), ("detail", None)]
        if v != "rooted":   # rooted: planted feet, no gait, no fidgets
            lst += [("fidget", TP), ("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming")]
        lst += [("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("swim", f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"),
                ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append(loops[v])
        animate[v] = lst
    particles = {"spores": f"{NS}:spore_drift", "pollen": f"{NS}:pollen", "dew": f"{NS}:dew_burst",
                 "flakes": f"{NS}:dry_flake", "drip": f"{NS}:sticky_drip", "rootburst": f"{NS}:root_burst",
                 "bubbles": f"{NS}:bubble_trail", "stepdust": f"{NS}:step_dust", "landdust": f"{NS}:land_dust"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": pre_animation(r)}


# ============================================================================ golem

GOL_RIG = Rig("torso_g", (0, 13, 0), [("r_arm_g", (-9.5, 22, 0)), ("l_arm_g", (9.0, 22, 0))], tail=None)
GOL_STONES = ["pelvis", "midriff", "lintel", "pillar_r", "pillar_l", "backwall", "arch", "backmass",
              "r_shoulder", "l_shoulder", "slab_a", "slab_b", "crown"]
GOL_MOVING = "q.modified_move_speed > 0.3 && q.is_on_ground && !q.is_in_water && !q.is_riding"


def golem(model, movable: List[str]) -> Dict[str, object]:
    r = "golem"
    rig = GOL_RIG
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life: slow stone breathing, rune heartbeat
    life = Layer(r, "life", loop=True)
    b = S(0.16)                                   # one breath every ~6 s: the stones part and rejoin
    life.pos("pillar_r", mul(-0.22, b))
    life.pos("pillar_l", mul(0.22, b))
    life.pos("arch", None, mul(0.3, b))
    life.pos("backmass", None, None, mul(0.3, b))
    life.pos("lintel", None, None, mul(-0.12, b))
    life.pos("r_shoulder", mul(-0.15, b), lin([(0.35, S(0.16, -30)), (0.28, S(0.22))]))
    life.pos("l_shoulder", mul(0.15, b), lin([(0.35, S(0.16, -50)), (0.24, S(0.24, 120))]))
    life.pos("crown", None, mul(0.22, S(0.16, -60)))
    life.pos("slab_a", None, lin([(0.4, S(0.31, 30))]), mul(0.25, b))
    life.pos("slab_b", None, lin([(0.4, S(0.28, 200))]), mul(0.25, b))
    life.rot("slab_a", None, None, osc(0.2, 1.4))
    life.rot("slab_b", None, None, osc(0.22, -1.4, 60))
    for arm in ("r_arm_g", "l_arm_g"):
        life.pos(arm, None, mul(0.18, S(0.16, -30)))
    life.pos("r_upper", None, osc(0.4, 0.12))
    life.pos("l_upper", None, osc(0.4, 0.12, 90))
    hb = heartbeat(1.4)
    life.rot("ring_a", None, None, f"{T} * 52")
    life.rot("ring_b", None, f"-{T} * 38", None)
    life.rot("ring_c", f"{T} * 71", None, None)
    life.uscale("ring_a", lin([(1, 1), (0.05, hb)]))
    life.rot("crystal", None, f"{T} * 30", None)
    life.pos("crystal", None, osc(0.45, 0.35))
    life.uscale("crystal", lin([(1, 1), (0.04, S(0.9)), (0.16, hb)]))
    for k in range(4):
        life.pos(f"sat{k}", osc(0.21, 0.3, k * 90), osc(0.3 + k * 0.07, 0.55, k * 80))
        life.rot(f"sat{k}", f"{T} * {14 + k * 6}", f"{T} * {22 + k * 7}", None)
    for p in ("r", "l"):
        life.uscale(f"{p}_foot_rune", "q.is_on_ground ? 0 : 1")
        life.scale(f"{p}_eyelid", None, lin([(1, 1), (6.8, f"math.max({blink(7.1, 11.3, 0.55, 3.0)}, q.is_sleeping)")]), None)
    # the crown follows the player's gaze, with slow deliberate looks when idle
    life.rot("crown", lin([(0.8, "math.clamp(q.target_x_rotation, -50, 50)"), (1.5, prod(S(0.11, 70), STILL))]),
             lin([(1.0, "q.target_y_rotation"), (4.0, prod(SQ(0.09, 0, 3), STILL))]), None)
    body(life, rig, lean=prod(0.6, S(0.05, 50), STILL), roll=prod(0.9, S(0.07), STILL))

    detail = Layer(r, "detail", loop=True)
    detail.rot("r_orbit", None, f"{T} * 75", None)
    detail.rot("l_orbit", None, f"-{T} * 68", None)

    # ------------------------------------------------------------------ locomotion: lumbering, stomping, stones jostle
    loco = Layer(r, "locomotion", loop=True)
    keep = 0.42
    stride(loco, keep)
    arm_swing(loco, 0.55)
    s = MOVE
    ss = prod(SPR, s)
    body(loco, rig,
         lean=lin([(3, s), (7, ss)]),
         roll=lin([(4.0, prod(STEP(), s)), (2.0, prod(STEP(), ss)), (3.0, prod(TURN, s))]),
         twist=lin([(-3.0, prod(CSTEP(), s)), (0.1, LOOK)]),
         sway=prod(0.7, STEP(), s))
    for bone, lag, amp in (("r_shoulder", 25, 0.9), ("l_shoulder", 35, 0.9), ("slab_a", 40, 0.7), ("slab_b", 50, 0.7),
                           ("arch", 15, 0.35), ("backmass", 30, 0.5), ("crown", 30, 0.4), ("pillar_r", 10, 0.25),
                           ("pillar_l", 20, 0.25), ("lintel", 12, 0.2), ("backwall", 18, 0.2)):
        loco.pos(bone, None, prod(-amp, IMPACT(lag), s))
    loco.rot("r_shoulder", None, None, prod(2.5, STEP(-30), s))
    loco.rot("l_shoulder", None, None, prod(2.5, STEP(-40), s))
    loco.rot("crown", prod(2.5, IMPACT(30), s))
    for k in range(4):
        loco.pos(f"sat{k}", None, lin([(-1.2, prod(IMPACT(45 + k * 10), s)), (-1.0, ss)]), prod(3.2, ss))
    loco.uscale("crystal", lin([(1, 1), (0.18, prod(IMPACT(10), s))]))
    loco.rot("r_fist", prod(7, CSTEP(-60), s))
    loco.rot("l_fist", prod(-7, CSTEP(-60), s))
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"
        loco.rot(f"{p}_foot", lin([(1.0, prod(side * keep * 1.4, TCOS)), (-8, prod(POS(sw), s))]))
    grounded(model, loco, rig, r)       # after every contribution that moves the legs
    for bn in rig.upper():              # the trunk settles onto the hips at every footfall
        loco.pos(bn, None, prod(-1.3, IMPACT(), s))
    # sprint: shoulders hunch forward, satellites trail, back slabs fold
    loco.pos("r_shoulder", prod(-1.2, ss), prod(-0.6, ss), prod(1.8, ss))
    loco.pos("l_shoulder", prod(1.2, ss), prod(-0.6, ss), prod(1.8, ss))
    for sl in ("slab_a", "slab_b"):
        loco.pos(sl, None, None, prod(1.4, ss))
        loco.rot(sl, prod(-8, ss))
    steps = {}
    for p in ("r", "l"):
        st = KeyLayer(r, f"step_{p}", 0.3)
        st.particle(0.0, "stepdust", f"{p}_step")
        steps[p] = st

    # ------------------------------------------------------------------ airborne
    air = Layer(r, "airborne", loop=True)
    for k in range(4):
        air.pos(f"sat{k}", None, 1.8)
    for bn, dy in (("r_shoulder", 0.7), ("l_shoulder", 0.7), ("slab_a", 1.1), ("slab_b", 1.1), ("crown", 0.4), ("arch", 0.3)):
        air.pos(bn, None, lin([(dy, 1), (dy * 0.6, FALL)]))
    air.rot("r_arm_g", None, None, prod(12, FALL, EMPTY_R))
    air.rot("l_arm_g", None, None, prod(-12, FALL, EMPTY_L))

    # ------------------------------------------------------------------ landing
    land = KeyLayer(r, "land", 0.6)
    land_hard = KeyLayer(r, "land_hard", 0.85)
    for kl, g in ((land, 1.0), (land_hard, 1.6)):
        L = kl.length
        for bn in ["torso_g", "r_arm_g", "l_arm_g"]:
            kl.pos(bn, {0: (0, -1.0 * g, 0), 0.1: (0, -1.3 * g, 0), 0.32: (0, 0.3, 0), 0.45: (0, -0.1, 0), L: (0, 0, 0)})
        kl.rot("torso_g", {0: (4 * g, 0, 0), 0.12: (5 * g, 0, 0), 0.35: (-1, 0, 0), L: (0, 0, 0)})
        for i, bn in enumerate(GOL_STONES[3:]):
            lag = 0.04 * (i % 4)
            kl.pos(bn, {0: (0, 0, 0), 0.08 + lag: (0, -1.1 * g, 0), 0.28 + lag: (0, 0.45 * g, 0), 0.45 + lag: (0, 0, 0), L: (0, 0, 0)})
        kl.rot("r_leg_g", {0: (0, 0, 4 * g), 0.12: (0, 0, 5 * g), 0.4: (0, 0, 0)})
        kl.rot("l_leg_g", {0: (0, 0, -4 * g), 0.12: (0, 0, -5 * g), 0.4: (0, 0, 0)})
        kl.scale("crystal", {0: 1.25 * g, 0.2: 1.4 * g, 0.5: 1, L: 1})
        for p in ("r", "l"):
            kl.scale(f"{p}_eyelid", {0: (1, 4.5, 1), 0.3: (1, 4.5, 1), 0.48: 1, L: 1})
            kl.particle(0.0, "landdust" if g > 1 else "stepdust", f"{p}_step")
        if g > 1:
            kl.particle(0.05, "pulse", "core")

    # ------------------------------------------------------------------ attack
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(5, ATK), twist=prod(-7, ATK))
    atk.pos("r_shoulder", None, None, prod(-1.6, ATK))
    atk.rot("crown", prod(5, ATK))
    atk.uscale("crystal", lin([(1, 1), (0.15, ATK)]))
    for p in ("r", "l"):
        atk.scale(f"{p}_eyelid", None, lin([(1, 1), (2.5, ATK)]), None)

    # ------------------------------------------------------------------ hurt
    hurt = KeyLayer(r, "hurt", 0.5)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -6, "roll": 3}, 0.22: {"lean": 2, "roll": -1}, 0.5: {}})
    hurt.rot("crown", {0: (0, 0, 0), 0.05: (-8, 0, 3), 0.25: (3, 0, 0), 0.5: (0, 0, 0)})
    for p in ("r", "l"):
        hurt.scale(f"{p}_eyelid", {0: 1, 0.04: (1, 7.8, 1), 0.3: (1, 7.8, 1), 0.42: 1})
    hurt.scale("crystal", {0: 1, 0.05: 1.35, 0.3: 1, 0.5: 1})
    for k, bn in enumerate(GOL_STONES[3:] + ["r_upper", "l_upper"]):
        ang = k * 2.4
        hurt.pos(bn, {**shake(0.0, 0.42, (0.5 * math.cos(ang), 0.45, 0.4 * math.sin(ang)), freq=9 + k % 3, decay=6), 0.5: (0, 0, 0)})

    # ------------------------------------------------------------------ fidgets
    fid = []
    settle = KeyLayer(r, "fidget_settle", 2.6)     # the stones lift and re-seat, bottom to top
    for i, bn in enumerate(GOL_STONES):
        t0 = 0.1 + i * 0.07
        rx, rz = ((i * 37) % 7 - 3) * 0.9, ((i * 53) % 7 - 3) * 0.9
        settle.pos(bn, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.25: (0, 0.9, 0), t0 + 0.5: (0, -0.25, 0), t0 + 0.65: (0, 0.08, 0), t0 + 0.8: (0, 0, 0), 2.6: (0, 0, 0)})
        settle.rot(bn, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.25: (rx, 0, rz), t0 + 0.55: (0, 0, 0), 2.6: (0, 0, 0)})
    settle.scale("crystal", {0: 1, 1.3: 1, 1.5: 1.45, 1.9: 1, 2.6: 1})
    settle.particle(1.4, "motes", "core")
    fid.append(settle)
    crack = KeyLayer(r, "fidget_crack", 2.3)      # turns the crown left and right, grinding
    crack.rot("crown", {0: (0, 0, 0), 0.35: (0, 24, 3), 0.45: (0, 26, 4), 0.75: (0, 26, 4), 1.15: (0, -22, -3), 1.25: (0, -24, -4), 1.55: (0, -24, -4), 1.95: (0, 0, 0), 2.3: (0, 0, 0)})
    for bn, t0 in (("r_shoulder", 0.3), ("l_shoulder", 1.1)):
        crack.pos(bn, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.15: (0, 0.9, 0), t0 + 0.3: (0, -0.2, 0), t0 + 0.4: (0, 0, 0), 2.3: (0, 0, 0)})
    crack.particle(0.45, "sparks", "eyes").particle(1.25, "sparks", "eyes")
    fid.append(crack)
    core = KeyLayer(r, "fidget_core", 2.8)        # the rune core spins up and flares
    core.rot("ring_a", {0: (0, 0, 0), 1.4: (0, 0, 540), 2.8: (0, 0, 720)})
    core.rot("ring_b", {0: (0, 0, 0), 1.4: (0, -400, 0), 2.8: (0, -540, 0)})
    core.rot("ring_c", {0: (0, 0, 0), 1.4: (480, 0, 0), 2.8: (630, 0, 0)})
    core.scale("crystal", {0: 1, 0.8: 1.5, 1.8: 1.5, 2.4: 1, 2.8: 1})
    core.rot("r_arm_g", {0: (0, 0, 0), 0.6: (0, 0, 16), 1.8: (0, 0, 18), 2.5: (0, 0, 0)})
    core.rot("l_arm_g", {0: (0, 0, 0), 0.6: (0, 0, -16), 1.8: (0, 0, -18), 2.5: (0, 0, 0)})
    body_keys(core, rig, {0: {}, 0.7: {"lean": -4}, 1.8: {"lean": -4}, 2.5: {}})
    core.particle(0.8, "burst", "core")
    fid.append(core)
    insp = KeyLayer(r, "fidget_inspect", 3.2)     # raises a fist and turns it over, looking at it
    insp.rot("r_arm_g", {0: (0, 0, 0), 0.7: (-72, 18, 0), 2.4: (-72, 18, 0), 3.0: (0, 0, 0), 3.2: (0, 0, 0)})
    insp.rot("r_fist", {0: (0, 0, 0), 0.9: (0, 0, 0), 1.3: (0, 70, 0), 1.8: (0, -50, 0), 2.2: (0, 0, 0), 3.2: (0, 0, 0)})
    insp.rot("crown", {0: (0, 0, 0), 0.6: (24, 16, 0), 2.4: (24, 16, 0), 3.0: (0, 0, 0), 3.2: (0, 0, 0)})
    for p in ("r", "l"):
        insp.scale(f"{p}_eyelid", {0: 1, 0.9: 1, 1.1: (1, 3.0, 1), 2.0: (1, 3.0, 1), 2.2: 1, 3.2: 1})
    fid.append(insp)
    picks = [("fidget_settle", "math.mod(math.floor(q.life_time * 1.3), 4) == 0"),
             ("fidget_crack", "math.mod(math.floor(q.life_time * 1.3), 4) == 1"),
             ("fidget_core", "math.mod(math.floor(q.life_time * 1.3), 4) == 2 && !q.is_item_equipped(0) && !q.is_item_equipped(1)"),
             ("fidget_inspect", "math.mod(math.floor(q.life_time * 1.3), 4) == 3 && !q.is_item_equipped(0)")]

    # ------------------------------------------------------------------ configurations
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.5),
        "siege": A(r, "intro_siege", loop="hold", length=0.45),
        "bastion": transition(model, r, "intro_bastion", "base", "bastion", 0.35),
        "arcane": transition(model, r, "intro_arcane", "base", "arcane", 0.7),
        "scattered": A(r, "intro_scattered", loop="hold", length=1.0),
        "disrupted": A(r, "intro_disrupted", loop="hold", length=0.6),
    }
    intro["base"].bone("core", scale={0.0: 1.35, 0.25: 0.95, 0.5: 1.0})
    for bn in ("r_shoulder", "l_shoulder", "slab_a", "slab_b"):
        intro["base"].bone(bn, pos={0.0: [0, 1.2, 0], 0.3: [0, -0.2, 0], 0.5: [0, 0, 0]})
    intro["base"].particle(0.0, "pulse", "core")
    intro["siege"].bone("hammer", scale={0.0: 0.15, 0.3: 1.12, 0.45: 1.0})
    intro["siege"].bone("r_fist", scale={0.0: 1.0, 0.2: 1.25, 0.45: 1.0})
    intro["siege"].particle(0.0, "burst", "core")
    intro["arcane"].bone("arcane_ring", scale={0.0: 0.1, 0.5: 1.08, 0.7: 1.0})
    intro["arcane"].particle(0.0, "burst", "core")
    core_c = np.array([0.0, 24.0, 0.0])
    for k, bn in enumerate(movable):
        d = np.array(model.bones[bn].pivot, float) - core_c
        d[1] += 4.0
        nrm = np.linalg.norm(d)
        d = d / nrm if nrm > 1e-6 else np.array([0.0, 1.0, 0.0])
        dist = 7.0 + (k * 37 % 5)
        spin = [(k * 53 % 120) - 60, (k * 97 % 160) - 80, (k * 31 % 90) - 45]
        intro["scattered"].bone(bn, pos={0.0: [0, 0, 0], 0.22: list(d * dist), 0.5: list(d * dist * 1.1),
                                         0.82: list(d * dist * 0.15), 1.0: [0, 0, 0]},
                                rot={0.0: [0, 0, 0], 0.5: spin, 1.0: [0, 0, 0]})
    intro["scattered"].bone("core", scale={0.0: 1.0, 0.3: 1.6, 0.85: 1.4, 1.0: 1.0})
    intro["scattered"].particle(0.0, "burst", "core")
    for k, bn in enumerate(["r_shoulder", "l_shoulder", "slab_a", "slab_b", "crown", "arch"]):
        intro["disrupted"].bone(bn, pos={0.0: [0, 0, 0], 0.15: [round(math.sin(math.radians(k * 50)) * 1.4, 3), -0.8, 0.6], 0.6: [0, 0, 0]})
    intro["disrupted"].particle(0.0, "sparks", "core")

    siege = Layer(r, "siege_loop", loop=True)       # the hammer's weight drags and swings
    siege.rot("hammer", prod(8, CSTEP(-70), MOVE), None, osc(1.5, 1.5))
    body(siege, rig, roll=mul(-1.5, 1), lean=1.0)
    bastion = Layer(r, "bastion_loop", loop=True)
    bastion.pos("slab_a", None, None, osc(2.0, 0.12))
    bastion.pos("slab_b", None, None, osc(2.0, 0.12, 90))
    body(bastion, rig, lean=2.0, bob=-0.6)
    arcane = Layer(r, "arcane_loop", loop=True)
    arcane.rot("arcane_ring", None, f"{T} * 46", None)
    arcane.rot("slab_a", None, f"{T} * 30", None)
    arcane.rot("slab_b", None, f"-{T} * 30", None)
    for k in range(4):
        arcane.pos(f"sat{k}", None, osc(0.6 + k * 0.1, 0.5, k * 70))
    disrupted = Layer(r, "disrupted_loop", loop=True)
    for k, bn in enumerate(["r_shoulder", "l_shoulder", "slab_a", "slab_b", "sat0", "sat1", "sat2", "sat3", "crown"]):
        disrupted.pos(bn, osc(0.7 + k * 0.13, 0.6, k * 40), f"{osc(0.9 + k * 0.1, 0.5, k * 77)} - 0.4", osc(0.5 + k * 0.11, 0.5, k * 13))
        disrupted.rot(bn, osc(0.6, 3, k * 30), osc(0.5, 4, k * 60), osc(0.8, 5, k * 90))
    disrupted.uscale("crystal", "math.mod(q.life_time * 6.3, 1) > 0.35 ? 1 : 0.55")
    disrupted.rot("ring_b", osc(1.7, 9), None, osc(1.3, 6))
    for p in ("r", "l"):
        disrupted.scale(f"{p}_eyelid", None, lin([(1, 1), (3.0, POS(S(1.3, 0 if p == "r" else 120)))]), None)
    body(disrupted, rig, roll=lin([(1.5, S(0.4)), (0.8, S(1.1, 40))]))

    fx = {v: A(r, f"fx_{v}", length=1.6 if v != "base" else 2.6).particle(0.0, "motes", "core")
          for v in ("base", "siege", "bastion", "arcane", "scattered", "disrupted")}
    fx["disrupted"].particle(0.8, "sparks", "core")
    step_ctrl = {f"controller.animation.{NS}.golem.steps": {"initial_state": "idle", "states": {
        "idle": {"transitions": [{"r": f"{GOL_MOVING} && math.cos({PH}) < -0.92"}, {"l": f"{GOL_MOVING} && math.cos({PH}) > 0.92"}]},
        "r": {"animations": ["step_r"], "transitions": [{"l": f"{GOL_MOVING} && math.cos({PH}) > 0.92"}, {"idle": f"!({GOL_MOVING})"}]},
        "l": {"animations": ["step_l"], "transitions": [{"r": f"{GOL_MOVING} && math.cos({PH}) < -0.92"}, {"idle": f"!({GOL_MOVING})"}]},
    }}}
    anims = [fp, tp, life.anim(), detail.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), steps["r"].anim(), steps["l"].anim(), siege.anim(), bastion.anim(), arcane.anim(), disrupted.anim(),
             wait_anim(r, "fidget_wait", 7.5), wait_anim(r, "fidget_rest", 3.5), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-12.0), **fidget_controller(r, picks), **step_ctrl}
    animate = {}
    for v in ("base", "siege", "bastion", "arcane", "scattered", "disrupted"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP), ("detail", None)]
        if v not in ("scattered",):
            lst.append(("fidget", TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK}"), ("steps", f"{TP} && {GAIT_OK}"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in ("siege", "bastion", "arcane", "disrupted"):
            lst.append((f"{v}_loop", None if v != "siege" else TP))
        animate[v] = lst
    particles = {"motes": f"{NS}:rune_mote", "burst": f"{NS}:rune_burst", "pulse": f"{NS}:rune_pulse",
                 "sparks": f"{NS}:rune_spark", "stepdust": f"{NS}:step_dust", "landdust": f"{NS}:land_dust"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": pre_animation(r)}


# ============================================================================ jackalope

JAK_RIG = Rig("torso", (0, 13, 0.6), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
NOSE = "(math.mod(q.life_time, 2.6) < 0.6 ? math.sin(q.life_time * 2400) * 0.12 : 0)"


def JAK_FLIGHT(ph):
    """Extra lift during the bound's flight (stride phase in degrees): the body keeps
    rising after push-off and both feet leave the ground."""
    return 1.6 * np.clip(np.sin(np.radians(ph - 130)), 0, None) ** 1.5


def jackalope(model) -> Dict[str, object]:
    r = "jackalope"
    rig = JAK_RIG
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life: quick breaths, twitching nose, vigilant head
    life = Layer(r, "life", loop=True)
    b = S(1.15)
    life.scale("torso", lin([(1, 1), (0.012, b)]), None, lin([(1, 1), (0.03, b)]))
    for arm in ("r_arm_g", "l_arm_g"):
        life.pos(arm, None, mul(0.08, b))
    life.pos("head_g", None, mul(0.06, S(1.15, -50)))
    body(life, rig, lean=prod(1.0, S(0.09, 60), STILL), roll=prod(1.4, S(0.12), STILL), twist=prod(1.5, S(0.1, 100), STILL))
    life.rot("head_g", prod(lin([(3, SQ(0.31, 40, 6)), (-1.5, S(0.13))]), STILL),
             prod(lin([(8, SQ(0.27, 0, 6)), (4, SQ(0.53, 70, 6))]), STILL),
             prod(4, SQ(0.17, 110, 5), STILL))
    life.pos("nose", None, None, NOSE)
    life.rot("r_whisker", None, None, mul(70, NOSE))
    life.rot("l_whisker", None, None, mul(-70, NOSE))
    chew = BUMP(5.3, 1.8, 0.9)
    life.rot("jaw", prod(5, POS(S(4.0)), chew), prod(4, S(4.0, 90), chew), None)
    tw_r = "(math.mod(q.life_time, 4.3) < 0.2 ? math.sin(math.mod(q.life_time, 4.3) * 1800) * 11 : 0)"
    tw_l = "(math.mod(q.life_time + 1.7, 3.1) < 0.2 ? math.sin(math.mod(q.life_time + 1.7, 3.1) * 1800) * 11 : 0)"
    life.rot("r_ear", mul(3, S(0.23)), lin([(14, SQ(0.19, 0, 4)), (6, SQ(0.43, 80, 4)), (0.2, LOOK)]), lin([(2.5, S(0.31)), (1, tw_r)]))
    life.rot("l_ear", mul(3, S(0.27, 70)), lin([(-14, SQ(0.23, 140, 4)), (-6, SQ(0.37, 30, 4)), (0.2, LOOK)]), lin([(-2.5, S(0.29, 40)), (-1, tw_l)]))
    life.rot("r_ear_tip", mul(5, S(0.41, 30)))
    life.rot("l_ear_tip", mul(5, S(0.37, 110)))
    life.rot("scut", lin([(4, S(0.6)), (1, "(math.mod(q.life_time + 0.8, 3.7) < 0.15 ? 14 : 0)")]))
    for p in ("r", "l"):
        life.scale(f"{p}_lid", None, lin([(1, 1), (5.9, f"math.max({blink(3.7, 5.9, 0.16, 1.4)}, q.is_sleeping)")]), None)
    life.rot("r_fore", mul(3, S(0.3)))
    life.rot("l_fore", mul(3, S(0.3, 60)))
    for k in range(6):
        life.rot(f"dorsal{k}", osc(0.5, 3, k * 30))

    listen = A(r, "listen", loop=True)
    listen.bone("r_ear", rot=[16, 28, 6])
    listen.bone("l_ear", rot=[12, -8, 0])
    listen.bone("skull", rot=[-4, 0, 9])
    listen.bone("scut", rot=[10, 0, 0])

    # ------------------------------------------------------------------ locomotion: springy steps, bounding sprint
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    walk = prod(WALKING, s)
    # sprint = a two-footed hare bound, one bound per player stride (b: 0 contact, 90 push-off,
    # 180 flight, 270 reach for the ground)
    bsin, bcos = f"math.sin({PH} + 25)", f"math.cos({PH} + 25)"
    # walking keeps 45% of the player's stride; the bound replaces it entirely
    loco.rot("r_leg_g", prod(-1.4, TCOS, lin([(0.55, 1), (0.45, SPR)])))
    loco.rot("l_leg_g", prod(1.4, TCOS, lin([(0.55, 1), (0.45, SPR)])))
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"
        lift = prod(POS(sw), walk)
        loco.rot(f"{p}_thigh", lin([(-14, lift), (-4, ss), (18, prod(bsin, ss)), (-12, prod(bcos, ss))]))
        loco.rot(f"{p}_shin", lin([(28, lift), (16, ss), (16, prod(bcos, ss))]))
        loco.rot(f"{p}_foot", lin([(-14, lift), (1.0, prod(side * 0.45 * 1.4, TCOS, WALKING)),
                                   (20, prod(POS(bsin), ss)), (-8, prod(bcos, ss))]))
        loco.rot(f"{p}_ear", lin([(-12, s), (-20, ss), (-6, prod(f"math.sin({PH} - 35)", ss)), (7, prod(f"math.sin({PH} * 2 - 70)", walk))]))
        loco.rot(f"{p}_ear_tip", lin([(10, prod(f"math.sin({PH} * 2 - 120)", walk)), (-8, ss), (-8, prod(f"math.sin({PH} - 80)", ss))]))
        e = EMPTY_R if side < 0 else EMPTY_L
        loco.rot(f"{p}_fore", prod(lin([(-14, 1), (-30, SPR), (8, prod(bsin, SPR))]), s, e))
        loco.rot(f"{p}_arm_g", prod(-26, ss, e))
        loco.rot(f"{p}_arm_g", prod(0.75, TCOS, ss, e) if side < 0 else prod(-0.75, TCOS, ss, e))
    arm_swing(loco, 0.4)
    body(loco, rig,
         lean=lin([(6, s), (4, ss), (-9, prod(bsin, ss))]),
         roll=lin([(2.5, prod(STEP(), walk)), (4.0, prod(TURN, s))]),
         twist=lin([(-4.0, prod(CSTEP(), walk)), (0.12, LOOK)]))
    grounded(model, loco, rig, r, sprint_clearance=JAK_FLIGHT)
    loco.rot("head_g", lin([(-3, s), (6, prod(bsin, ss))]), prod(3.5, CSTEP(), walk), None)
    loco.rot("scut", lin([(10, ss), (12, prod(f"math.sin({PH} - 40)", ss)), (6, prod(f"math.sin({PH} * 2 - 40)", walk))]))

    # ------------------------------------------------------------------ airborne
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"{p}_thigh", lin([(30, RISE), (-14, FALL)]))
        air.rot(f"{p}_shin", lin([(-22, RISE), (10, FALL)]))
        air.rot(f"{p}_foot", lin([(26, RISE)]))
        air.rot(f"{p}_ear", lin([(-26, RISE), (14, FALL)]))
        air.rot(f"{p}_ear_tip", lin([(-10, RISE), (16, FALL)]))
        air.rot(f"{p}_arm_g", prod(-24, FALL, e), None, mirror(side, prod(8, FALL, e)))
        air.rot(f"{p}_fore", prod(-20, FALL, e))
    air.rot("scut", 16)
    body(air, rig, lean=lin([(-6, RISE), (6, FALL)]))

    # ------------------------------------------------------------------ landing
    land = KeyLayer(r, "land", 0.4)
    land_hard = KeyLayer(r, "land_hard", 0.6)
    for kl, g in ((land, 1.0), (land_hard, 1.5)):
        L = kl.length
        t1, t2 = 0.08 * g, 0.25 * g
        for p, side in SIDES:
            kl.rot(f"{p}_thigh", {0: (-26 * g, 0, 0), t1: (-30 * g, 0, 0), t2: (4, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_shin", {0: (40 * g, 0, 0), t1: (46 * g, 0, 0), t2: (-4, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_foot", {0: (-12 * g, 0, 0), t2: (2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_ear", {0: (16 * g, 0, 0), 0.12 * g: (-8, 0, 0), t2: (4, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_ear_tip", {0: (22 * g, 0, 0), 0.15 * g: (-12, 0, 0), 0.3 * g: (5, 0, 0), L: (0, 0, 0)})
            kl.particle(0.0, "landdust" if g > 1 else "stepdust", f"{p}_step")
        body_keys(kl, rig, {0: {"bob": -1.0 * g, "lean": 6 * g}, t1: {"bob": -1.2 * g, "lean": 8 * g}, t2: {"bob": 0.3, "lean": -2}, L: {}})
        kl.rot("scut", {0: (-14, 0, 0), 0.18: (10, 0, 0), L: (0, 0, 0)})

    # ------------------------------------------------------------------ attack: antler thrust
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(8, ATK), twist=prod(-6, ATK))
    atk.rot("head_g", prod(16, ATK))
    for p in ("r", "l"):
        atk.rot(f"{p}_ear", prod(-24, ATK))
    atk.rot("scut", prod(10, ATK))

    # ------------------------------------------------------------------ hurt
    hurt = KeyLayer(r, "hurt", 0.5)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -8, "bob": 0.8}, 0.2: {"lean": 3, "bob": -0.3}, 0.5: {}})
    hurt.rot("head_g", {0: (0, 0, 0), 0.05: (-10, 0, 0), 0.2: (6, 0, 0), 0.5: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.rot(f"{p}_ear", {0: (0, 0, 0), 0.05: (-38, 0, -10 * sg), 0.35: (-30, 0, -8 * sg), 0.5: (0, 0, 0)})
        hurt.scale(f"{p}_lid", {0: 1, 0.04: (1, 6.9, 1), 0.3: (1, 6.9, 1), 0.42: 1})
    hurt.rot("scut", {0: (0, 0, 0), 0.05: (-14, 0, 0), 0.5: (0, 0, 0)})

    # ------------------------------------------------------------------ fidgets
    fid = []
    groom = KeyLayer(r, "fidget_groom", 2.8)      # washes its face and pulls an ear down to clean it
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        groom.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.4: (-95, 0, 22 * sg), 0.9: (-112, 0, 22 * sg), 1.3: (-80, 0, 22 * sg),
                                 1.7: (-112, 0, 22 * sg), 2.1: (-80, 0, 22 * sg), 2.5: (0, 0, 0), 2.8: (0, 0, 0)})
        groom.rot(f"{p}_fore", {0: (0, 0, 0), 0.4: (-50, 0, 0), 2.1: (-50, 0, 0), 2.5: (0, 0, 0)})
        groom.scale(f"{p}_lid", {0: 1, 0.5: 1, 0.7: (1, 4, 1), 2.0: (1, 4, 1), 2.2: 1, 2.8: 1})
    groom.rot("head_g", {0: (0, 0, 0), 0.4: (18, 0, -12), 2.2: (18, 0, -12), 2.6: (0, 0, 0)})
    groom.rot("r_ear", {0: (0, 0, 0), 0.5: (0, 0, 0), 0.8: (36, 0, 8), 1.3: (12, 0, 4), 1.7: (36, 0, 8), 2.1: (12, 0, 4), 2.45: (-6, 0, 0), 2.8: (0, 0, 0)})
    groom.rot("r_ear_tip", {0: (0, 0, 0), 0.8: (18, 0, 0), 1.3: (6, 0, 0), 1.7: (18, 0, 0), 2.1: (6, 0, 0), 2.45: (-10, 0, 0), 2.8: (0, 0, 0)})
    fid.append(groom)
    sent = KeyLayer(r, "fidget_sentinel", 2.6)    # rears up tall and scans the horizon
    body_keys(sent, rig, {0: {}, 0.35: {"lean": -10, "bob": 1.6}, 2.0: {"lean": -10, "bob": 1.6}, 2.5: {}})
    for p, side in SIDES:
        sent.rot(f"{p}_thigh", {0: (0, 0, 0), 0.35: (14, 0, 0), 2.0: (14, 0, 0), 2.5: (0, 0, 0)})
        sent.rot(f"{p}_shin", {0: (0, 0, 0), 0.35: (-26, 0, 0), 2.0: (-26, 0, 0), 2.5: (0, 0, 0)})
        sent.rot(f"{p}_foot", {0: (0, 0, 0), 0.35: (12, 0, 0), 2.0: (12, 0, 0), 2.5: (0, 0, 0)})
        sent.rot(f"{p}_ear", {0: (0, 0, 0), 0.35: (10, 0, 0), 0.6: (10, 20 * (-side), 0), 1.1: (10, -10 * (-side), 0), 1.6: (10, 25 * (-side), 0), 2.2: (0, 0, 0)})
    sent.rot("head_g", {0: (0, 0, 0), 0.4: (-6, 0, 0), 0.6: (-6, 28, 0), 1.0: (-6, 28, 0), 1.15: (-6, -26, 0), 1.7: (-6, -26, 0), 1.85: (-6, 0, 6), 2.2: (-4, 0, 6), 2.5: (0, 0, 0)})
    sent.pos("nose", {**{round(0.4 + k * 0.05, 3): (0, 0, 0.15 * (-1) ** k) for k in range(20)}, 1.45: (0, 0, 0)})
    fid.append(sent)
    thump = KeyLayer(r, "fidget_thump", 1.7)      # stamps a hind foot twice: a warning to the warren
    thump.rot("r_leg_g", {0: (0, 0, 0), 0.25: (-32, 0, 0), 0.35: (4, 0, 0), 0.5: (-30, 0, 0), 0.6: (4, 0, 0), 0.9: (0, 0, 0), 1.7: (0, 0, 0)})
    thump.rot("r_shin", {0: (0, 0, 0), 0.25: (20, 0, 0), 0.35: (0, 0, 0), 0.5: (20, 0, 0), 0.6: (0, 0, 0)})
    for p in ("r", "l"):
        thump.rot(f"{p}_ear", {0: (0, 0, 0), 0.2: (12, 0, 0), 1.3: (12, 0, 0), 1.7: (0, 0, 0)})
    thump.rot("scut", {0: (0, 0, 0), 0.35: (18, 0, 0), 0.45: (4, 0, 0), 0.6: (18, 0, 0), 0.8: (0, 0, 0)})
    body_keys(thump, rig, {0: {}, 0.2: {"lean": 6}, 1.2: {"lean": 6}, 1.7: {}})
    thump.particle(0.35, "stepdust", "r_step").particle(0.6, "stepdust", "r_step")
    fid.append(thump)
    stretch = KeyLayer(r, "fidget_stretch", 2.6)  # front paws forward, long stretch, yawn, then a full-body shake
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        stretch.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.5: (-62, 0, 0), 1.2: (-66, 0, 0), 1.5: (0, 0, 0)})
        stretch.rot(f"{p}_ear", {0: (0, 0, 0), 0.5: (-30, 0, 0), 1.3: (-30, 0, 0), 1.55: (0, 0, 0), **{k: v for k, v in shake(1.6, 0.6, (0, 0, -20 * sg), freq=7, decay=4).items()}, 2.6: (0, 0, 0)})
    body_keys(stretch, rig, {0: {}, 0.5: {"lean": 18, "bob": -0.8}, 1.2: {"lean": 20, "bob": -1.0}, 1.5: {}, 2.6: {}})
    stretch.rot("head_g", {0: (0, 0, 0), 0.5: (10, 0, 0), 1.2: (10, 0, 0), 1.5: (0, 0, 0)})
    stretch.rot("jaw", {0: (0, 0, 0), 0.7: (0, 0, 0), 0.9: (16, 0, 0), 1.25: (16, 0, 0), 1.4: (0, 0, 0)})
    stretch.rot("torso", {**shake(1.55, 0.6, (0, 0, 8), freq=7, decay=4), 2.6: (0, 0, 0)})
    stretch.rot("head_g", {**shake(1.55, 0.6, (0, 12, 0), freq=7, decay=4), 2.6: (0, 0, 0)})
    fid.append(stretch)
    picks = [("fidget_groom", "math.mod(math.floor(q.life_time * 1.9), 4) == 0 && !q.is_item_equipped(0) && !q.is_item_equipped(1)"),
             ("fidget_sentinel", "math.mod(math.floor(q.life_time * 1.9), 4) == 1"),
             ("fidget_thump", "math.mod(math.floor(q.life_time * 1.9), 4) == 2"),
             ("fidget_stretch", "math.mod(math.floor(q.life_time * 1.9), 4) == 3 && !q.is_item_equipped(0) && !q.is_item_equipped(1)")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.4),
        "hunt": transition(model, r, "intro_hunt", "base", "hunt", 0.25),
        "awakened": transition(model, r, "intro_awakened", "base", "awakened", 1.8),
        "awakened_hunt": transition(model, r, "intro_awakened_hunt", "awakened", "awakened_hunt", 0.25),
    }
    intro["base"].bone("r_ear", rot={0.0: [-14, 0, 0], 0.2: [6, 0, 0], 0.4: [0, 0, 0]})
    intro["base"].bone("l_ear", rot={0.0: [-14, 0, 0], 0.25: [6, 0, 0], 0.4: [0, 0, 0]})
    aw = intro["awakened"]
    for p in ("r", "l"):
        for nm, t0, t1 in (("back", 0.35, 0.95), ("low", 0.55, 1.15), ("crown", 0.8, 1.4), ("crown2", 0.95, 1.6)):
            aw.bone(f"{p}_tine_{nm}", scale={0.0: 0.02, t0: 0.02, t1: 1.12, t1 + 0.15: 1.0})
    aw.bone("skull", rot={0.0: [0, 0, 0], 0.45: [-30, 0, 0], 1.3: [-30, 0, 0], 1.8: [0, 0, 0]})
    aw.particle(0.0, "awaken", "antlers")
    aw.particle(0.9, "embers", "antlers")
    intro["hunt"].particle(0.0, "embers", "antlers")

    hunt = Layer(r, "hunt_loop", loop=True)        # coiled: ears trembling back, low and still
    hunt.rot("r_ear", osc(9, 1.4))
    hunt.rot("l_ear", osc(9, 1.4, 90))
    hunt.rot("scut", lin([(6, 1), (5, S(3.1))]))
    body(hunt, rig, lean=prod(4, STILL), bob=prod(-0.5, STILL))
    awake = Layer(r, "awakened_loop", loop=True)   # blood-moon frenzy: faster breath, sharper twitches
    awake.scale("torso", lin([(1, 1), (0.01, S(1.9))]), None, lin([(1, 1), (0.025, S(1.9))]))
    awake.rot("r_ear", None, None, mul(4, SQ(0.7, 0, 6)))
    awake.rot("l_ear", None, None, mul(-4, SQ(0.6, 90, 6)))
    awake.rot("head_g", None, None, prod(3, SQ(0.21, 40, 5), STILL))

    fx = {
        "base": A(r, "fx_base", length=3.2).particle(0.0, "moonmotes", "antlers"),
        "hunt": A(r, "fx_hunt", length=0.5).particle(0.0, "embers", "antlers"),
        "awakened": A(r, "fx_awakened", length=0.9).particle(0.0, "embers", "antlers").particle(0.45, "bloodmist", "tail"),
        "awakened_hunt": A(r, "fx_awakened_hunt", length=0.45).particle(0.0, "embers", "antlers"),
    }
    anims = [fp, tp, life.anim(), listen, loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(), hurt.anim(),
             hunt.anim(), awake.anim(), wait_anim(r, "fidget_wait", 6.0), wait_anim(r, "fidget_rest", 2.5),
             *[f.anim() for f in fid], *intro.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-14.0, soft_speed=-6.0), **fidget_controller(r, picks)}
    animate = {}
    night = "q.time_of_day < 0.23 || q.time_of_day > 0.77"
    for v in ("base", "hunt", "awakened", "awakened_hunt"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP),
               ("listen", f"{TP} && q.is_sneaking && q.modified_move_speed < 0.02"), ("fidget", TP),
               ("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"),
               ("attack", TP), ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None),
               (f"fx_{v}", f"{TP} && ({night})" if v == "base" else TP)]
        if v in ("hunt", "awakened_hunt"):
            lst.append(("hunt_loop", TP))
        if v in ("awakened", "awakened_hunt"):
            lst.append(("awakened_loop", TP))
        animate[v] = lst
    particles = {"moonmotes": f"{NS}:moon_mote", "embers": f"{NS}:blood_ember", "awaken": f"{NS}:awaken_spiral",
                 "bloodmist": f"{NS}:blood_mist", "stepdust": f"{NS}:step_dust", "landdust": f"{NS}:land_dust"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": pre_animation(r)}


# ============================================================================ player poses

FPK_ARM = "(1 - variable.is_first_person * 0.7)"
FPK = "(1 - variable.is_first_person)"


def _pk(vec, k):
    return [f"{v} * {k}" if v != 0 else 0 for v in vec]


def pose(name: str, length: float, loop=False, **bones) -> Anim:
    a = Anim(f"animation.{NS}.pose.{name}", loop=(True if loop else False), length=length)
    for bn, frames in bones.items():
        k = FPK_ARM if bn in ("rightarm", "leftarm") else FPK
        a.bone(bn, rot={t: _pk(v, k) for t, v in frames.items()})
    return a


def poses() -> List[Anim]:
    out = [
        pose("sal_snare", 0.55, rightarm={0: [0, 0, 0], 0.12: [-96, 6, 0], 0.4: [-82, 0, 0], 0.55: [0, 0, 0]},
             body={0: [0, 0, 0], 0.12: [0, -14, 0], 0.55: [0, 0, 0]}),
        pose("sal_embrace", 0.7, rightarm={0: [0, 0, 0], 0.15: [-90, 32, 0], 0.35: [-88, -22, 0], 0.7: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [-90, -32, 0], 0.35: [-88, 22, 0], 0.7: [0, 0, 0]},
             body={0: [0, 0, 0], 0.35: [12, 0, 0], 0.7: [0, 0, 0]}),
        pose("sal_root", 1.0, loop=True, rightarm={0: [-22, 0, 38], 1.0: [-22, 0, 38]},
             leftarm={0: [-22, 0, -38], 1.0: [-22, 0, -38]}, rightleg={0: [0, 0, 7], 1.0: [0, 0, 7]},
             leftleg={0: [0, 0, -7], 1.0: [0, 0, -7]}, head={0: [-16, 0, 0], 1.0: [-16, 0, 0]}),
        pose("sal_jet", 0.5, rightarm={0: [0, 0, 0], 0.1: [42, 0, 12], 0.5: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.1: [42, 0, -12], 0.5: [0, 0, 0]}),
        pose("gol_edict", 1.1, rightarm={0: [0, 0, 0], 0.35: [-172, 0, 8], 0.5: [-176, 0, 8], 0.62: [-34, 0, 0], 1.1: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.35: [-160, 0, -8], 0.5: [-164, 0, -8], 0.62: [-30, 0, 0], 1.1: [0, 0, 0]},
             body={0: [0, 0, 0], 0.5: [-9, 0, 0], 0.62: [18, 0, 0], 1.1: [0, 0, 0]}),
        pose("gol_bastion", 1.0, loop=True, rightarm={0: [-76, -26, 0], 1.0: [-76, -26, 0]},
             leftarm={0: [-76, 26, 0], 1.0: [-76, 26, 0]}, body={0: [6, 0, 0], 1.0: [6, 0, 0]}),
        pose("gol_glyph", 1.2, rightarm={0: [0, 0, 0], 0.3: [-10, 0, 84], 0.6: [-12, 0, 86], 0.8: [-62, 0, 22], 1.2: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.3: [-10, 0, -84], 0.6: [-12, 0, -86], 0.8: [-62, 0, -22], 1.2: [0, 0, 0]},
             head={0: [0, 0, 0], 0.6: [-14, 0, 0], 0.8: [16, 0, 0], 1.2: [0, 0, 0]}),
        pose("gol_reassemble", 1.0, rightarm={0: [0, 0, 0], 0.2: [-40, 0, 60], 0.8: [-40, 0, 60], 1.0: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.2: [-40, 0, -60], 0.8: [-40, 0, -60], 1.0: [0, 0, 0]}),
        pose("jak_bound", 0.45, rightleg={0: [-32, 0, 0], 0.1: [28, 0, 0], 0.45: [0, 0, 0]},
             leftleg={0: [-32, 0, 0], 0.1: [28, 0, 0], 0.45: [0, 0, 0]},
             body={0: [16, 0, 0], 0.1: [-10, 0, 0], 0.45: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.1: [36, 0, 10], 0.45: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.1: [36, 0, -10], 0.45: [0, 0, 0]}),
        pose("jak_brand", 0.7, head={0: [0, 0, 0], 0.15: [32, 0, 0], 0.55: [32, 0, 0], 0.7: [0, 0, 0]},
             body={0: [0, 0, 0], 0.15: [24, 0, 0], 0.55: [20, 0, 0], 0.7: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.15: [42, 0, 14], 0.7: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [42, 0, -14], 0.7: [0, 0, 0]}),
        pose("jak_mirage", 0.5, body={0: [0, 0, 0], 0.15: [-16, 0, 0], 0.5: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.15: [-30, 0, 60], 0.5: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [-30, 0, -60], 0.5: [0, 0, 0]}),
        pose("jak_waltz", 0.5, loop=True, rightarm={0: [-130, 0, 40], 0.25: [-30, 0, 10], 0.5: [-130, 0, 40]},
             leftarm={0: [-30, 0, -10], 0.25: [-130, 0, -40], 0.5: [-30, 0, -10]},
             body={0: [10, -18, 0], 0.25: [10, 18, 0], 0.5: [10, -18, 0]}, head={0: [-8, 0, 6], 0.25: [-8, 0, -6], 0.5: [-8, 0, 6]}),
        pose("jak_howl", 1.6, head={0: [0, 0, 0], 0.4: [-42, 0, 0], 1.2: [-42, 0, 0], 1.6: [0, 0, 0]},
             body={0: [0, 0, 0], 0.4: [-12, 0, 0], 1.2: [-12, 0, 0], 1.6: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.4: [-20, 0, 40], 1.2: [-20, 0, 40], 1.6: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.4: [-20, 0, -40], 1.2: [-20, 0, -40], 1.6: [0, 0, 0]}),
        pose("fsm_touch", 0.6, rightarm={0: [0, 0, 0], 0.12: [-95, -8, 0], 0.32: [-88, 0, 0], 0.6: [0, 0, 0]},
             body={0: [0, 0, 0], 0.12: [0, -12, 0], 0.6: [0, 0, 0]}),
        pose("nur_arrival", 0.6, rightarm={0: [-30, 0, 46], 0.25: [-8, 0, 12], 0.6: [0, 0, 0]},
             leftarm={0: [-30, 0, -46], 0.25: [-8, 0, -12], 0.6: [0, 0, 0]}, body={0: [-6, 0, 0], 0.6: [0, 0, 0]}),
        pose("nur_edict", 0.9, rightarm={0: [0, 0, 0], 0.18: [-84, -10, 0], 0.6: [-86, -6, 0], 0.9: [0, 0, 0]},
             head={0: [0, 0, 0], 0.18: [-8, 0, 0], 0.6: [-8, 0, 0], 0.9: [0, 0, 0]}),
        pose("nur_claim", 1.0, rightarm={0: [0, 0, 0], 0.35: [-24, 0, 52], 0.8: [-24, 0, 52], 1.0: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.35: [-24, 0, -52], 0.8: [-24, 0, -52], 1.0: [0, 0, 0]},
             head={0: [0, 0, 0], 0.35: [-12, 0, 0], 0.8: [-12, 0, 0], 1.0: [0, 0, 0]}),
        pose("nur_point", 0.8, rightarm={0: [0, 0, 0], 0.12: [-96, 4, 0], 0.5: [-92, 0, 0], 0.8: [0, 0, 0]},
             body={0: [0, 0, 0], 0.12: [0, -10, 0], 0.8: [0, 0, 0]}),
        pose("nur_enthrone", 1.0, loop=True, rightarm={0: [-34, 0, 20], 1.0: [-34, 0, 20]},
             leftarm={0: [-34, 0, -20], 1.0: [-34, 0, -20]}, head={0: [-8, 0, 0], 1.0: [-8, 0, 0]}),
        pose("nur_final", 1.3, rightarm={0: [0, 0, 0], 0.3: [-172, 0, -6], 1.05: [-174, 0, -6], 1.3: [0, 0, 0]},
             head={0: [0, 0, 0], 0.3: [-16, 0, 0], 1.05: [-16, 0, 0], 1.3: [0, 0, 0]}),
        pose("rite", 1.8, head={0: [0, 0, 0], 0.5: [-30, 0, 0], 1.3: [-30, 0, 0], 1.8: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.5: [-150, 0, 20], 1.3: [-150, 0, 20], 1.8: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.5: [-150, 0, -20], 1.3: [-150, 0, -20], 1.8: [0, 0, 0]}),
    ]
    return out
