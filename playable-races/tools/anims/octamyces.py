"""Race 009 Octamyces Undecimus - attachable animation set (v1.5 premium redesign).

Motion language: graceful, floating, hypnotic.  The body hangs in the air on a slow 3.6 s swell;
the cap lags it and nods a beat late, the skirt pulses like a jellyfish bell with a ripple running
round the rim, and every mycelial group trails and waves in slow travelling waves that stream
behind with speed.  The eye is the personality: eleven rings turning at eleven slow speeds in
alternating directions, the star pupil drifting toward where the player looks, and a blink that
folds the eight petals shut one after another like a flower closing, then opens them again.
Everything is eased; nothing in idle moves faster than about 3 Hz.

Layers (stateless Molang, or keyframed):
  steady      cancels the player's look on the head group (x on head_g, y on `steady`)
  gaze        the cap turns a fraction of the look, the iris tilts and the star drifts toward it;
              the rings and the star turn continuously (never blended, so unbounded angles are safe)
  blink*      the flower blink, folded to each form's own closed pose (pre_animation clocks)
  vigil       controller: `alive` plays life; still for 2 s it settles, plays one idle behaviour
              (fidget_*), watches a moment, and from about 7 s only the eye keeps working (surveil);
              any movement wakes it at once.  vigil_plain: the same without the idle behaviours
  locomotion  leans into its path, the cap lags back and banks, the skirt sweeps back; a sprint
              beats the two fins together into a propulsor (2.2 Hz) with the bell
  airborne / landing / attack (a manipulator lash) / hurt (a flinch, a fold of the petals) / swim
  forms       intro_<form> (with anticipation), fx_<form>, loops for every form but base
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from anims.core import NS, T, n
from anims.life import (ATK, FALL, MOVE, RISE, S, SPR, TURN, KeyLayer, Layer, Rig, arm_swing, body, body_keys,
                        chain_wave, drain_shared, follow_chain, landing_controller, lin, mul, prod, shared_vars,
                        wait_anim)
from anims.races import A, AIR, GAIT_OK, TP, view_anims
from models.octamyces import FLOAT_C, LIDS, LID_OPEN, MYC_PTS, RING_SIDES, RINGS, VARIANTS

R = "octamyces"
RIG = Rig("float", FLOAT_C, [("r_arm_g", MYC_PTS[0][0]), ("l_arm_g", MYC_PTS[1][0])], legs=(), tail=None)
HOVER = 0.28                                                 # Hz: the swell everything follows
BEAT = 2.2                                                   # Hz: the sprint propulsor (<= 2.5)
PITCH = "math.clamp(q.target_x_rotation, -50, 50)"           # + = looking down
YAW = "math.clamp(q.target_y_rotation, -70, 70)"             # + = looking to its right
EMPTY_R = "(q.is_item_equipped(0) ? 0.25 : 1)"
EMPTY_L = "(q.is_item_equipped(1) ? 0.25 : 1)"
OPEN = "(1 - v.oct_blink)"                                   # 0 while a blink holds the petals shut
SS = prod(SPR, MOVE)                                         # sprinting weight
SETTLE, BEHAVIOUR = 2.0, 5.0      # still for SETTLE s: one idle behaviour; surveil at SETTLE + BEHAVIOUR = 7 s
# the swing arriving later down a tendril (a whip)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.3 - 0.15, 0, 1) * 180)"
ATK3 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.5 - 0.3, 0, 1) * 180)"
BUSY = ("q.modified_move_speed > 0.04 || !q.is_on_ground || q.is_in_water || q.hurt_time > 0"
        " || (v.attack_time ?? 0) > 0.01 || q.is_sneaking || q.is_riding || q.is_sleeping || q.is_gliding"
        " || q.is_using_item")
# the rings turn at eleven slow speeds, alternating directions (degrees per second)
SPIN = [11.0, -8.5, 7.0, -5.8, 4.8, -4.0, 3.4, -2.8, 2.3, -1.9, 1.6]
SECTOR = [360.0 / RING_SIDES[k] * (1 if SPIN[k] > 0 else -1) for k in range(RINGS)]
# the flower blink: two eased clocks folded into one 0..1 value per frame (pre_animation)
BLINK_PRE = [
    "v.oct_b1 = math.mod(q.life_time, 8.7);",
    "v.oct_b2 = math.mod(q.life_time + 4.9, 13.3);",
    "v.oct_b1 = math.clamp(v.oct_b1 / 0.2, 0, 1) - math.clamp((v.oct_b1 - 0.27) / 0.3, 0, 1);",
    "v.oct_b2 = math.clamp(v.oct_b2 / 0.2, 0, 1) - math.clamp((v.oct_b2 - 0.27) / 0.3, 0, 1);",
    "v.oct_blink = math.max(math.max(v.oct_b1, v.oct_b2), (q.is_sleeping ? 1 : 0));",
    "v.oct_blink = v.oct_blink * v.oct_blink * (3 - 2 * v.oct_blink);",
]
CLOSE = {"base": -LID_OPEN, "offset": -LID_OPEN, "sporeveil": -LID_OPEN + 18.0, "unstable": -LID_OPEN - 30.0}
# the skirt's quadrants: (axis, sign) of an outward flare, and where each sits round the rim
SKIRT = {"frill_f": (0, -1), "frill_r": (2, 1), "frill_b": (0, 1), "frill_l": (2, -1)}
SKIRT_PH = {"frill_f": 0.0, "frill_r": 90.0, "frill_b": 180.0, "frill_l": 270.0}
SIDES2 = ((0, -1), (1, 1))                                   # manipulator groups by side
FINS = ((2, -1), (3, 1))                                     # fin groups by side


def ch(g: int):
    return [f"myc{g}_{k}" for k in range(3)]


def hover(ly: Layer, lean=None, twist=None, roll=None, bob=None) -> None:
    """Whole-body motion: the torso chain and its twin in the head chain move together; the arm
    groups (manipulators) are carried along by the same small-angle displacement."""
    body(ly, RIG, lean=lean, twist=twist, roll=roll, bob=bob)
    ly.rot("float_h", lean, twist, roll)
    if bob is not None:
        ly.pos("float_h", None, bob, None)


def hover_keys(kl: KeyLayer, keys: Dict[float, dict]) -> None:
    body_keys(kl, RIG, keys)
    kl.rot("float_h", {t: (d.get("lean", 0.0), d.get("twist", 0.0), d.get("roll", 0.0)) for t, d in keys.items()})
    if any(abs(d.get("bob", 0.0)) > 1e-6 for d in keys.values()):
        kl.pos("float_h", {t: (0.0, d.get("bob", 0.0), 0.0) for t, d in keys.items()})


def skirt(ly: Layer, e) -> None:
    """Flare every quadrant of the skirt outward by e (an expression, or a dict per quadrant)."""
    for q_, (ax, sg) in SKIRT.items():
        v = [None, None, None]
        v[ax] = mul(sg, e[q_] if isinstance(e, dict) else e)
        ly.rot(q_, *v)


def skirt_keys(kl: KeyLayer, keys: Dict[float, float], lag: float = 0.0) -> None:
    """Keyed outward flare for every quadrant (each quadrant `lag` s later round the rim)."""
    for i, (q_, (ax, sg)) in enumerate(SKIRT.items()):
        kl.rot(q_, {t + (lag * i if 0 < t < max(keys) else 0.0): tuple(sg * v if a == ax else 0.0 for a in range(3))
                    for t, v in keys.items()})


def ease_keys(t0: float, t1: float, v0, v1, steps: int = 3, over: float = 0.0) -> Dict[float, object]:
    """Keys easing v0 -> v1 between t0 and t1 (smoothstep), optionally overshooting by `over`."""
    out = {}
    v0, v1 = np.asarray(v0, float), np.asarray(v1, float)
    for k in range(steps + 1):
        a = k / steps
        e = a * a * (3 - 2 * a)
        if over and 0 < k < steps:
            e = e * (1 + over * math.sin(a * math.pi))
        out[round(t0 + (t1 - t0) * a, 3)] = tuple(v0 * (1 - e) + v1 * e)
    return out


def wobble(t0: float, dur: float, amp, freq: float = 2.8, decay: float = 4.0, steps: int = 3) -> Dict[float, object]:
    """A damped wobble (eased by the Catmull-Rom keys; <= 3 Hz): knocked out of true, settling."""
    out = {round(t0, 3): (0.0, 0.0, 0.0)}
    k_n = max(2, int(dur * freq * steps))
    for k in range(1, k_n + 1):
        t = dur * k / k_n
        v = np.asarray(amp, float) * math.sin(2 * math.pi * freq * t) * math.exp(-decay * t)
        out[round(t0 + t, 3)] = tuple(v)
    out[round(t0 + dur + 0.04, 3)] = (0.0, 0.0, 0.0)
    return out


def fold(j: int) -> str:
    """0..1 fold of petal j during a blink: the petals close one after another round the eye."""
    d = 0.04 * j
    x = "v.oct_blink" if j == 0 else f"(v.oct_blink - {n(d)})"
    return f"math.clamp({x} * 1.389, 0, 1)"


def form_delta(model, frm: str, to: str):
    """{bone: (rotation delta, translation delta)} that puts the `to` form back in the `frm` pose."""
    out = {}
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        b = model.bones[bn]
        dr = np.array(model.bone_rot(bn, frm), float) - np.array(model.bone_rot(bn, to), float)
        tf = np.array(b.variant[frm][0], float) if frm in b.variant else np.zeros(3)
        tt = np.array(b.variant[to][0], float) if to in b.variant else np.zeros(3)
        dt = tf - tt
        if not (np.allclose(dr, 0, atol=0.01) and np.allclose(dt, 0, atol=0.01)):
            out[bn] = (dr, dt)
    return out


def arrive(kl: KeyLayer, model, frm: str, to: str, start: float, dur: float, stagger=None, over: float = 0.08) -> None:
    """Ease every bone that differs between the forms from the old pose into the new one, with a
    small overshoot (follow-through); stagger: {bone: extra delay}."""
    for bn, (dr, dt) in form_delta(model, frm, to).items():
        s = start + (stagger or {}).get(bn, 0.0)
        keys = {0.0: 1.0, s: 1.0, s + dur * 0.7: -over, s + dur: 0.0, kl.length: 0.0}
        if not np.allclose(dr, 0, atol=0.01):
            kl.rot(bn, {t: tuple(dr * k) for t, k in keys.items()})
        if not np.allclose(dt, 0, atol=0.01):
            kl.pos(bn, {t: tuple(dt * k) for t, k in keys.items()})


# ============================================================================= the set

def anims(model) -> Dict[str, object]:
    r = R
    fp, tp = view_anims(r)
    for g in (0, 1):                     # first person: the vanilla arm is drawn as a tendril sleeve
        fp.bone(f"myc{g}_0", scale=0)

    # ------------------------------------------------------------------ steady / gaze / blink
    steady = Layer(r, "steady", loop=True)
    steady.rot("head_g", "-q.target_x_rotation", None, None)
    steady.rot("steady", None, "-q.target_y_rotation", None)

    gaze = Layer(r, "gaze", loop=True)
    gaze.rot("cap", mul(0.1, PITCH), mul(0.18, YAW), None)
    gaze.rot("iris", "math.clamp(q.target_x_rotation * 0.25, -9, 9)", "math.clamp(q.target_y_rotation * 0.2, -10, 10)", None)
    gaze.pos("star", "math.clamp(q.target_y_rotation * -0.012, -0.6, 0.6)", "math.clamp(q.target_x_rotation * -0.012, -0.5, 0.5)", None)
    for k in range(RINGS):
        gaze.rot(f"ring{k}", None, None, f"{T} * {n(SPIN[k])}")
    gaze.rot("star", None, None, f"{T} * -6")
    gaze.rot("core", None, f"{T} * 14", None)                # the core turns: its spiral seems to rise

    blinks = {}
    for name, amp in (("blink", CLOSE["base"]), ("blink_wide", CLOSE["sporeveil"]), ("blink_wilt", CLOSE["unstable"])):
        b = Layer(r, name, loop=True)
        for j in range(LIDS):
            b.rot(f"lid{j}", mul(amp, fold(j)), None, None)
        b.scale("star", lin([(1, 1), (-0.35, "v.oct_blink")]), lin([(1, 1), (-0.35, "v.oct_blink")]), 1)
        blinks[name] = b

    # ------------------------------------------------------------------ life: the swell
    life = Layer(r, "life", loop=True, length=8.0)
    hover(life, lean=mul(1.0, S(0.11, 30)), roll=mul(1.4, S(0.13)), bob=lin([(0.8, S(HOVER)), (0.18, S(0.71, 40))]))
    life.rot("cap", mul(1.2, S(HOVER, -75)), mul(1.5, S(0.09, 20)), mul(0.9, S(0.13, -60)))   # it nods a beat late
    life.pos("cap", None, mul(0.2, S(HOVER, -70)), None)
    skirt(life, {q_: lin([(3.0, S(HOVER, -110)), (2.2, S(0.42, -SKIRT_PH[q_]))]) for q_ in SKIRT})
    life.scale("gill_ring", lin([(1, 1), (0.03, S(0.2))]), lin([(1, 1), (0.1, S(0.2, -30))]), lin([(1, 1), (0.03, S(0.2))]))
    for j in range(LIDS):                # the crown breathes
        life.rot(f"lid{j}", mul(3.0, S(0.15, j * 45)), None, None)
    life.rot("cap_upper", None, mul(1.2, S(0.07, 40)), None)
    for g, side in SIDES2:               # manipulators drift (less while holding something)
        e = EMPTY_R if side < 0 else EMPTY_L
        f = 1.0 if side < 0 else 1.13
        chain_wave(life, ch(g), "z", 3.0 * -side, 0.31 * f, lag=45, falloff=1.2, phase=0 if side < 0 else 110, gain=e)
        chain_wave(life, ch(g), "x", 2.5, 0.23 * f, lag=40, falloff=1.15, phase=30 if side < 0 else 200, gain=e)
    for g, side in FINS:                 # the fins paddle slowly and trail; at a sprint the wave quickens
        follow_chain(life, ch(g), "y", -side * 4.0, 0.3, lag=50, falloff=1.25, drag=-side * 8.0, run_amp=-side * 3.0,
                     run_freq=0.6, phase=0 if side < 0 else 140)
        follow_chain(life, ch(g), "x", 3.0, 0.37, lag=55, falloff=1.2, phase=-40 if side < 0 else 120)
    follow_chain(life, ch(4), "x", 3.0, 0.21, lag=40, falloff=1.25)                    # the sensor hangs, feeling the air
    follow_chain(life, ch(4), "y", 4.0, 0.15, lag=35, falloff=1.2, phase=70)
    follow_chain(life, ch(5), "z", 4.0, 0.21, lag=45, falloff=1.15)                    # the emitter swings like a censer
    follow_chain(life, ch(5), "x", 2.5, 0.17, lag=40, falloff=1.1, phase=50, drag=10.0)
    follow_chain(life, ch(6), "x", 4.0, 0.35, lag=60, falloff=1.15, drag=12.0, run_amp=6.0, run_freq=0.9)   # the ribbon flows
    follow_chain(life, ch(6), "y", 5.0, 0.23, lag=50, falloff=1.25, phase=30)
    follow_chain(life, ch(7), "x", 2.5, 0.19, lag=30, falloff=1.2, drag=-8.0)          # the antenna sways, streams back
    follow_chain(life, ch(7), "z", 2.0, 0.27, lag=40, falloff=1.2, phase=60)

    # ------------------------------------------------------------------ surveil: everything stops but the eye
    surveil = Layer(r, "surveil", loop=True)
    hover(surveil, bob=mul(0.15, S(0.07)))
    surveil.rot("iris", lin([(4.0, S(0.037, 20)), (2.0, S(0.061, 75))]), lin([(9.0, S(0.05)), (3.0, S(0.083, 40))]), None)
    surveil.pos("star", lin([(-0.35, S(0.05)), (-0.12, S(0.083, 40))]), mul(-0.25, S(0.037, 20)), None)
    for j in range(LIDS):                # the crown narrows to watch (and still folds shut to blink)
        surveil.rot(f"lid{j}", mul(20.0, OPEN), None, None)
    surveil.uscale("star", 0.8)
    skirt(surveil, mul(1.0, S(0.07, 30)))
    for g, side in SIDES2:               # held, a little drooped
        surveil.rot(f"myc{g}_1", 3.0, None, 2.0 * -side)
    for g, side in FINS:
        surveil.rot(f"myc{g}_0", 3.0, None, None)
    surveil.rot("myc4_0", 6.0, None, None)
    surveil.rot("myc6_0", mul(1.0, S(0.05)), None, None)

    # ------------------------------------------------------------------ locomotion: gliding
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    arm_swing(loco, 0.3)
    hover(loco, lean=lin([(6.0, s), (5.0, SS)]), roll=lin([(-6.0, prod(TURN, s))]))
    loco.rot("cap", lin([(-3.0, s), (-3.0, SS)]), None, prod(4.0, TURN, s))           # the cap lags back and banks
    for q_ in SKIRT:                                                                       # the skirt sweeps back
        loco.rot(q_, lin([(5.0, s), (3.0, SS)]), None, None)
    beat = f"(0.5 + 0.5 * math.sin({T} * {n(BEAT * 360)}))"                                # the propulsor
    bell = f"(0.5 + 0.5 * math.sin({T} * {n(BEAT * 360)} - 50))"
    for g, side in FINS:                 # the fins sweep together, the bell contracts a beat later
        loco.rot(f"myc{g}_0", prod(6.0, SS), prod(-side * 22.0, beat, SS), prod(-side * 6.0, beat, SS))
        loco.rot(f"myc{g}_1", None, prod(-side * 10.0, bell, SS), None)
    skirt(loco, prod(-7.0, bell, SS))
    for g, side in SIDES2:               # manipulators trail a little
        e = EMPTY_R if side < 0 else EMPTY_L
        loco.rot(f"myc{g}_0", prod(8.0, s, e), None, None)
        loco.rot(f"myc{g}_1", prod(5.0, s, e), None, None)
    loco.rot("myc4_0", prod(-10.0, s), None, None)                                        # the sensor draws in
    loco.rot("myc5_0", prod(10.0, s), None, None)                                         # the pod swings back

    air = Layer(r, "airborne", loop=True)  # contract on the rise, spread and trail on the fall
    hover(air, lean=lin([(-3.0, RISE), (4.0, FALL)]))
    skirt(air, lin([(-6.0, RISE), (10.0, FALL)]))
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"myc{g}_1", None, None, prod(-side, lin([(-6.0, RISE), (10.0, FALL)]), e))
    for g, side in FINS:
        air.rot(f"myc{g}_0", lin([(-10.0, RISE), (12.0, FALL)]), prod(-side, lin([(10.0, RISE), (-8.0, FALL)])), None)
    air.rot("myc4_0", lin([(-8.0, RISE), (10.0, FALL)]), None, None)
    air.rot("myc5_0", None, None, lin([(6.0, RISE), (-10.0, FALL)]))
    air.rot("myc6_0", lin([(-10.0, RISE), (14.0, FALL)]), None, None)
    air.rot("myc6_1", lin([(-4.0, RISE), (8.0, FALL)]), None, None)
    air.rot("myc7_0", lin([(6.0, RISE), (-8.0, FALL)]), None, None)

    land = KeyLayer(r, "land", 0.6)
    land_hard = KeyLayer(r, "land_hard", 0.85)
    for kl, g in ((land, 1.0), (land_hard, 1.6)):
        L = kl.length
        hover_keys(kl, {0: {"bob": -0.9 * g, "lean": 2 * g}, 0.12: {"bob": -1.3 * g, "lean": 3 * g},
                        0.32: {"bob": 0.35 * g, "lean": -1}, 0.5: {"bob": -0.1}, L: {}})
        skirt_keys(kl, {0: 6 * g, 0.1: 12 * g, 0.3: -4.0, 0.48: 1.0, L: 0.0}, lag=0.02)
        for k in range(RINGS):           # the rings jolt into the socket and settle
            kl.pos(f"ring{k}", {0: (0, 0, 0), 0.06 + 0.012 * k: (0, 0, 0.3 * g), 0.3: (0, 0, -0.05), L: (0, 0, 0)})
        for gr, side in FINS:
            kl.rot(f"myc{gr}_0", {0: (0, 0, 0), 0.08: (14 * g, 0, 0), 0.3: (-6, 0, 0), 0.5: (2, 0, 0), L: (0, 0, 0)})
        for k in range(3):               # the ribbon floats up as the bell squashes, then settles
            kl.rot(f"myc6_{k}", {0: (0, 0, 0), 0.08 + 0.05 * k: (9 * g, 0, 0), 0.3 + 0.05 * k: (-2, 0, 0), L: (0, 0, 0)})
        for gr, side in SIDES2:
            kl.rot(f"myc{gr}_1", {0: (0, 0, 0), 0.1: (0, 0, -side * 10 * g), 0.3: (0, 0, side * 4), L: (0, 0, 0)})
        kl.rot("myc5_0", {0: (0, 0, -10 * g), 0.2: (0, 0, 7 * g), 0.45: (0, 0, -2), L: (0, 0, 0)})
        kl.rot("myc7_0", {0: (10 * g, 0, 0), 0.2: (-8 * g, 0, 0), 0.45: (2, 0, 0), L: (0, 0, 0)})
    land_hard.particle(0.0, "motes", "base_c")

    atk = Layer(r, "attack", loop=True)  # the right manipulator lashes out with the swing, a whip down its length
    atk.rot("myc0_0", prod(-35, ATK), prod(-22, ATK), prod(28, ATK))
    atk.rot("myc0_1", prod(-28, ATK2), None, prod(-20, ATK2))
    atk.rot("myc0_2", prod(-34, ATK3), None, prod(-16, ATK3))
    atk.rot("myc1_0", prod(-8, ATK2), None, prod(-6, ATK2))
    hover(atk, lean=prod(4, ATK), twist=prod(-8, ATK))
    atk.rot("cap", prod(3, ATK), prod(-6, ATK), None)
    for j in range(LIDS):                # the crown narrows: a squint
        atk.rot(f"lid{j}", prod(34, ATK, OPEN), None, None)
    for k in range(RINGS):
        atk.uscale(f"ring{k}", lin([(1, 1), (-0.07, ATK)]))
    skirt(atk, prod(4.0, ATK2))

    hurt = KeyLayer(r, "hurt", 0.7)      # a flinch: the body recoils, the rings are knocked out of true
    hover_keys(hurt, {0: {}, 0.06: {"lean": -8, "roll": 4, "bob": 0.5}, 0.24: {"lean": 3, "roll": -2}, 0.44: {"lean": -1},
                      0.7: {}})
    for k in range(RINGS):
        a = (1 if k % 2 else -1) * (10.0 - 0.5 * k)
        ang = math.radians(k * 137.5)
        hurt.rot(f"ring{k}", {**wobble(0.0, 0.55, (0, 0, a), freq=2.6, decay=4.5), 0.7: (0, 0, 0)})
        hurt.pos(f"ring{k}", {**wobble(0.0, 0.5, (0.3 * math.cos(ang), 0.3 * math.sin(ang), 0.2), freq=2.8, decay=5.0),
                              0.7: (0, 0, 0)})
    skirt_keys(hurt, {0: 0.0, 0.06: 10.0, 0.22: -4.0, 0.4: 1.0, 0.7: 0.0})
    hurt.rot("cap", {0: (0, 0, 0), 0.06: (-5, 0, 3), 0.24: (2, 0, -1), 0.7: (0, 0, 0)})
    for g in range(2, 8):
        sg = 1 if g % 2 else -1
        hurt.rot(f"myc{g}_0", {**wobble(0.02 * (g - 2), 0.5, (7, 5 * sg, 4), freq=2.6, decay=5.0), 0.7: (0, 0, 0)})
    hurt.particle(0.0, "echo", "eye_c")
    hurt_lids = Layer(r, "hurt_lids", loop=True)                 # the petals snap shut and reopen on a hit
    for j in range(LIDS):
        hurt_lids.rot(f"lid{j}", prod(85.0, OPEN, "math.sin(math.clamp((10 - q.hurt_time) * 22, 0, 180))"), None, None)

    swim = Layer(r, "swim", loop=True)   # the bell pulses, the fins and filaments beat with it
    swim.kw["length"] = 1.0
    skirt(swim, lin([(10.0, S(1.0))]))
    swim.scale("gill_ring", 1, lin([(1, 1), (0.15, S(1.0, -60))]), 1)
    for g, side in FINS:
        swim.rot(f"myc{g}_0", mul(8.0, S(1.0, -80)), prod(-side * 20.0, f"(0.5 + 0.5 * {S(1.0, -40)})"), None)
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        swim.rot(f"myc{g}_0", None, None, prod(-side, lin([(-15.0, 1), (10.0, S(1.0, -90))]), e))
    swim.rot("myc4_0", lin([(-15.0, 1), (8.0, S(1.0, -120))]), None, None)
    swim.rot("myc5_0", None, None, lin([(-15.0, 1), (8.0, S(1.0, -90))]))
    follow_chain(swim, ch(6), "x", 10.0, 1.0, lag=60, falloff=1.2)
    swim.particle(0.0, "motes", "gills")

    # ------------------------------------------------------------------ idle behaviours (3-6 s performances)
    fid = {}
    crown = KeyLayer(r, "fidget_crown", BEHAVIOUR)    # the crown folds shut petal by petal and is rebuilt in bloom
    for k in range(RINGS):               # while it is shut the rings sink into the socket, then bloom out
        crown.scale(f"ring{k}", {0: 1, 1.0: 1, 1.6: 0.92, 2.4: 0.92, 2.95 + 0.02 * k: 1.08, 3.4: 1, 4.2: 1})
        crown.pos(f"ring{k}", {0: (0, 0, 0), 1.0: (0, 0, 0), 1.6: (0, 0, 0.3), 2.4: (0, 0, 0.3), 3.0: (0, 0, -0.1),
                               3.4: (0, 0, 0), 4.2: (0, 0, 0)})
    crown.scale("star", {0: 1, 2.6: 1, 3.05: 1.45, 3.5: 1, 4.2: 1})
    crown.rot("cap", {0: (0, 0, 0), 0.8: (-2, 0, 0), 2.4: (-2, 0, 0), 3.2: (1, 0, 0), 4.2: (0, 0, 0)})
    skirt_keys(crown, {0: 0.0, 1.0: -3.0, 2.5: -3.0, 3.1: 5.0, 3.7: 0.0, 4.2: 0.0}, lag=0.05)
    crown.particle(3.0, "motes", "eye_c")
    crown_a = crown.anim()
    for j in range(LIDS):                # (as expressions: a blink on top never folds a petal past shut)
        shut = f"{n(CLOSE['base'])} * {OPEN}"
        a0, r0 = 0.35 + 0.11 * j, 2.3 + 0.1 * (LIDS - 1 - j)
        keys = {0: 0.0, a0: 0.0, a0 + 0.22: shut, a0 + 0.38: shut, r0: shut, r0 + 0.28: -14.0, r0 + 0.5: 3.0,
                r0 + 0.7: 0.0, 4.2: 0.0}
        crown_a.bone(f"lid{j}", rot={t: {"post": [v, 0, 0], "lerp_mode": "catmullrom"} for t, v in keys.items()})
    fid["fidget_crown"] = crown_a

    click = KeyLayer(r, "fidget_click", BEHAVIOUR)    # the rings click round one sector each, inside out, then rewind as one
    for k in range(RINGS):
        c0 = 0.3 + 0.17 * k
        sec = SECTOR[k]
        click.rot(f"ring{k}", {0: (0, 0, 0), c0: (0, 0, 0), c0 + 0.2: (0, 0, sec * 1.06), c0 + 0.34: (0, 0, sec),
                               3.15: (0, 0, sec), 3.3: (0, 0, sec * 1.04), 4.1: (0, 0, 0), 4.6: (0, 0, 0)})
        click.pos(f"ring{k}", {0: (0, 0, 0), c0: (0, 0, 0), c0 + 0.12: (0, 0, -0.22), c0 + 0.32: (0, 0, 0), 4.6: (0, 0, 0)})
        click.scale(f"ring{k}", {0: 1, c0: 1, c0 + 0.14: 1.06, c0 + 0.34: 1, 4.6: 1})
    click.scale("star", {0: 1, 2.1: 1, 2.35: 1.35, 2.7: 1, 4.6: 1})
    click.rot("iris", {0: (0, 0, 0), 0.4: (-3, 0, 0), 2.3: (-3, 0, 0), 2.8: (0, 0, 0), 4.6: (0, 0, 0)})
    click.particle(2.2, "motes", "eye_c")
    fid["fidget_click"] = click.anim()

    gills = KeyLayer(r, "fidget_spores", BEHAVIOUR)   # the gills breathe in, then breathe out a cloud of spores
    skirt_keys(gills, {0: 0.0, 0.9: -10.0, 1.25: 22.0, 1.8: 15.0, 2.5: -3.0, 3.1: 1.0, 3.7: 0.0, 4.6: 0.0}, lag=0.06)
    gills.scale("gill_ring", {0: 1, 0.9: (1, 0.85, 1), 1.25: (1.08, 1.5, 1.08), 1.9: (1.03, 1.25, 1.03), 2.9: 1, 4.6: 1})
    gills.scale("myc5_2", {0: 1, 0.95: 1, 1.15: (1.3, 1.2, 1.3), 1.4: (0.9, 0.95, 0.9), 1.8: 1, 4.6: 1})
    gills.rot("cap", {0: (0, 0, 0), 0.9: (-3, 0, 0), 1.3: (2, 0, 0), 2.2: (0, 0, 0), 4.6: (0, 0, 0)})
    hover_keys(gills, {0: {}, 0.9: {"bob": 0.8, "lean": -2}, 1.3: {"bob": -0.4, "lean": 1}, 2.1: {"bob": 0.15}, 3.0: {}, 4.6: {}})
    for g, t0 in ((2, 1.3), (3, 1.4), (6, 1.5), (4, 1.6)):     # each group stirs as the cloud passes it
        gills.rot(f"myc{g}_0", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.25: (-8, 0, 0), t0 + 0.6: (3, 0, 0), t0 + 0.9: (0, 0, 0),
                                4.6: (0, 0, 0)})
    gills.particle(0.95, "spores", "gills").particle(1.05, "spores", "spores").particle(1.6, "spores", "gills")
    fid["fidget_spores"] = gills.anim()

    probe = KeyLayer(r, "fidget_probe", BEHAVIOUR)    # the sensor reaches into the air, the eye following its tip
    probe.rot("myc4_0", {0: (0, 0, 0), 0.5: (-24, 16, 0), 1.2: (-30, 8, 0), 1.6: (-22, 24, 0), 2.3: (-34, 12, 0),
                         3.0: (-26, 18, 0), 3.9: (0, 0, 0), 5.0: (0, 0, 0)})
    probe.rot("myc4_1", {0: (0, 0, 0), 0.5: (-12, 0, 0), 3.0: (-12, 0, 0), 3.9: (0, 0, 0), 5.0: (0, 0, 0)})
    probe.rot("myc4_2", {0: (0, 0, 0), 1.0: (0, 0, 0), 1.15: (-8, 0, 0), 1.35: (6, 0, 0), 1.55: (0, 0, 0), 2.15: (0, 0, 0),
                         2.3: (-8, 0, 0), 2.5: (6, 0, 0), 2.7: (0, 0, 0), 5.0: (0, 0, 0)})
    probe.rot("iris", {0: (0, 0, 0), 0.65: (6, -7, 0), 1.35: (8, -5, 0), 1.75: (5, -9, 0), 2.45: (9, -6, 0),
                       3.15: (6, -8, 0), 4.05: (0, 0, 0), 5.0: (0, 0, 0)})
    probe.pos("star", {0: (0, 0, 0), 0.65: (0.5, -0.3, 0), 2.45: (0.55, -0.35, 0), 3.15: (0.5, -0.3, 0), 4.05: (0, 0, 0),
                       5.0: (0, 0, 0)})
    probe.rot("cap", {0: (0, 0, 0), 0.6: (2, -5, 0), 3.0: (2, -5, 0), 3.8: (0, 0, 0), 5.0: (0, 0, 0)})
    probe.particle(1.15, "motes", "sensor").particle(2.3, "motes", "sensor")
    fid["fidget_probe"] = probe.anim()
    picks = [(name, f"math.mod(math.floor(q.life_time * 1.7), 4) == {k}") for k, name in enumerate(fid)]

    # ------------------------------------------------------------------ forms
    intro = {}
    ib = KeyLayer(r, "intro_base", 0.9, loop="hold")             # the eye awakens: rings bloom out of the void
    for k in range(RINGS):
        t0 = 0.05 + 0.035 * k
        ib.scale(f"ring{k}", {0: 0.15, t0: 0.15, t0 + 0.28: 1.07, t0 + 0.42: 1.0, 0.9: 1.0})
    ib.scale("star", {0: 0.1, 0.3: 1.4, 0.55: 1.0, 0.9: 1.0})
    ib_a = ib.anim()
    for j in range(LIDS):                # ... and the petals open round them
        t0 = 0.25 + 0.03 * j
        keys = {0: CLOSE["base"], t0: CLOSE["base"], t0 + 0.25: -10.0, t0 + 0.4: 0.0, 0.9: 0.0}
        ib_a.bone(f"lid{j}", rot={t: {"post": [v, 0, 0], "lerp_mode": "catmullrom"} for t, v in keys.items()})
    ib_a.particle(0.0, "motes", "eye_c")
    intro["base"] = ib_a

    isv = KeyLayer(r, "intro_sporeveil", 0.9, loop="hold")       # inhale... then the bell bursts open
    arrive(isv, model, "base", "sporeveil", 0.24, 0.42, over=0.3)
    skirt_keys(isv, {0: 0.0, 0.2: -9.0, 0.24: -9.0, 0.36: 6.0, 0.6: -2.0, 0.9: 0.0})
    hover_keys(isv, {0: {}, 0.2: {"bob": 0.7, "lean": -2}, 0.34: {"bob": -0.5, "lean": 1}, 0.6: {"bob": 0.15}, 0.9: {}})
    isv.scale("gill_ring", {0: 1, 0.2: (1, 0.85, 1), 0.38: (1.08, 1.5, 1.08), 0.6: (1.02, 1.15, 1.02), 0.9: (1.03, 1.2, 1.03)})
    isv.scale("myc5_2", {0: 1, 0.2: 0.9, 0.34: 1.35, 0.55: 0.95, 0.9: 1.1})
    for g in range(2, 8):                # the mycelia shiver outward with the burst
        isv.rot(f"myc{g}_0", {0: (0, 0, 0), 0.24: (0, 0, 0), 0.36: (-9, 0, 0), 0.6: (3, 0, 0), 0.9: (0, 0, 0)})
    isv.particle(0.28, "spores", "spores").particle(0.32, "spores", "gills")
    intro["sporeveil"] = isv.anim()

    ir = KeyLayer(r, "intro_record", 1.3, loop="hold")           # the rings click into alignment, inside out
    for k in range(RINGS):
        t0 = 0.1 + 0.07 * k
        off = (36.0 if k % 2 else -28.0) * (1.0 - k / 14.0)
        ir.rot(f"ring{k}", {0: (0, 0, off), t0: (0, 0, off), t0 + 0.2: (0, 0, -off * 0.08), t0 + 0.32: (0, 0, 0), 1.3: (0, 0, 0)})
        ir.pos(f"ring{k}", {0: (0, 0, 0), t0 + 0.12: (0, 0, 0), t0 + 0.22: (0, 0, -0.2), t0 + 0.36: (0, 0, 0), 1.3: (0, 0, 0)})
    arrive(ir, model, "base", "record", 0.85, 0.35)
    ir.scale("star", {0: 1, 0.85: 1, 1.05: 0.5, 1.3: 0.62})
    ir.particle(0.0, "motes", "eye_c")
    intro["record"] = ir.anim()

    io = KeyLayer(r, "intro_offset", 0.5, loop="hold")           # a compressing beat, then the layers slip
    arrive(io, model, "base", "offset", 0.1, 0.32, stagger={"cap_upper": 0.04}, over=0.12)
    hover_keys(io, {0: {}, 0.08: {"bob": -0.6, "lean": 1}, 0.3: {"bob": 0.2}, 0.5: {}})
    io.particle(0.0, "echo", "cap_top")
    intro["offset"] = io.anim()

    ifr = KeyLayer(r, "intro_frame", 0.4, loop="hold")           # the eye stops dead
    for k in range(RINGS):
        ifr.pos(f"ring{k}", {0: (0, 0, 0), 0.06: (0, 0, 0.35), 0.4: (0, 0, 0)})
    arrive(ifr, model, "base", "frame", 0.05, 0.3)
    ifr.particle(0.0, "echo", "eye_c")
    intro["frame"] = ifr.anim()

    iun = KeyLayer(r, "intro_unstable", 0.6, loop="hold")        # a shudder as the skirt and mycelia go limp
    arrive(iun, model, "base", "unstable", 0.05, 0.45, over=0.05)
    hover_keys(iun, {0: {}, 0.08: {"roll": 5, "bob": -0.6}, 0.22: {"roll": -3}, 0.38: {"roll": 1}, 0.6: {}})
    iun.particle(0.0, "motes", "base_c")
    intro["unstable"] = iun.anim()

    sv_loop = Layer(r, "sporeveil_loop", loop=True)              # the open bell breathes out, the mycelia shiver
    sv_loop.kw["length"] = 1.2
    skirt(sv_loop, mul(3.0, S(0.85)))
    sv_loop.scale("gill_ring", 1, lin([(1, 1), (0.08, S(0.85, -40))]), 1)
    sv_loop.uscale("myc5_2", lin([(1, 1), (0.05, S(0.85, -90))]))
    for g in range(2, 8):
        sv_loop.rot(f"myc{g}_1", mul(1.5, S(2.4, g * 50)), None, mul(1.0, S(2.1, g * 80)))

    rec_loop = Layer(r, "record_loop", loop=True)                 # focused: aligned rings turn as one, tightened
    rec_loop.rot("cap", mul(0.15, PITCH), mul(0.35, YAW), None)
    rec_loop.rot("iris", "math.clamp(q.target_x_rotation * 0.35, -10, 10)", "math.clamp(q.target_y_rotation * 0.3, -12, 12)", None)
    rec_loop.pos("star", "math.clamp(q.target_y_rotation * -0.015, -0.7, 0.7)", "math.clamp(q.target_x_rotation * -0.015, -0.6, 0.6)", None)
    for k in range(RINGS):
        rec_loop.rot(f"ring{k}", None, None, f"{T} * 9")
        rec_loop.uscale(f"ring{k}", 0.88 + 0.004 * k)
    rec_loop.uscale("star", 0.62)
    rec_loop.rot("core", None, f"{T} * 14", None)

    off_loop = Layer(r, "offset_loop", loop=True)                 # the slipped layers hum, the mycelia quiver like fins
    off_loop.rot("cap_mid", None, mul(1.2, S(1.6)), None)
    off_loop.rot("cap_upper", None, mul(-1.5, S(1.3, 40)), None)
    for g in range(2, 8):
        off_loop.rot(f"myc{g}_0", mul(1.5, S(2.2, g * 50)), None, mul(1.0, S(1.9, g * 40)))

    frame = KeyLayer(r, "frame_loop", 3.5, loop=True)            # the Eleventh Frame: a telescope of rings
    for k in range(RINGS):
        t0 = 0.35 + 0.09 * k                                      # inner rings lead
        dz = -(0.5 + 0.8 * (RINGS - 1 - k))                       # an 8.5 px tunnel, a gap between every ring
        sc = 1.0 + 1.6 * ((RINGS - 1 - k) / (RINGS - 1)) ** 1.5   # widening to one bore (scaled across only)
        frame.scale(f"ring{k}", {0: 1, 0.15: (0.9, 0.9, 1), t0: (0.9, 0.9, 1), t0 + 0.32: (sc * 1.04, sc * 1.04, 1),
                                 t0 + 0.45: (sc, sc, 1), 2.95: (sc, sc, 1), 3.15: (0.9, 0.9, 1), 3.3: (1.03, 1.03, 1), 3.5: 1})
        frame.pos(f"ring{k}", {0: (0, 0, 0), 0.15: (0, 0, 0.3), t0: (0, 0, 0.3), t0 + 0.32: (0, 0, dz * 1.05),
                               t0 + 0.45: (0, 0, dz), 1.9 + 0.06 * k: (0, 0, dz * 1.04), 2.2 + 0.06 * k: (0, 0, dz),
                               2.95: (0, 0, dz), 3.15: (0, 0, 0.15), 3.3: (0, 0, 0), 3.5: (0, 0, 0)})
        frame.rot(f"ring{k}", {0: (0, 0, 0), 1.5: (0, 0, 0), 2.95: (0, 0, 24.0 * (1 if k % 2 else -1)), 3.3: (0, 0, 0),
                               3.5: (0, 0, 0)})
    frame.scale("star", {0: 1, 0.15: 0.7, 0.5: 1.5, 2.95: 1.5, 3.15: 0.6, 3.4: 1, 3.5: 1})
    for j in range(LIDS):                # the crown flinches at the collapse and opens again
        frame.rot(f"lid{j}", {0: (0, 0, 0), 0.15: (6, 0, 0), 0.5: (-8, 0, 0), 2.95: (-8, 0, 0), 3.12: (40, 0, 0),
                              3.32: (-4, 0, 0), 3.5: (0, 0, 0)})
    spread = {2: (-25, -30, 10), 3: (-25, 30, -10), 4: (-25, 20, 0), 5: (0, 0, -30), 6: (25, 0, 0), 7: (-15, 0, -12)}
    for g, rot in spread.items():        # the filaments reach out toward the recorded points, then snap back
        frame.rot(f"myc{g}_0", {0: (0, 0, 0), 0.6: (0, 0, 0), 1.3: rot, 2.95: rot,
                                3.2: tuple(-0.15 * v for v in rot), 3.45: (0, 0, 0), 3.5: (0, 0, 0)})
        frame.rot(f"myc{g}_1", {0: (0, 0, 0), 0.7: (0, 0, 0), 1.4: (-8, 0, 0), 2.95: (-8, 0, 0), 3.25: (0, 0, 0), 3.5: (0, 0, 0)})
    hover_keys(frame, {0: {}, 0.15: {"lean": 2, "bob": -0.3}, 0.6: {"lean": -3, "bob": 0.6}, 2.95: {"lean": -3, "bob": 0.6},
                       3.15: {"lean": 2, "bob": -0.4}, 3.4: {}, 3.5: {}})
    skirt_keys(frame, {0: 0.0, 0.15: -4.0, 0.6: 8.0, 2.95: 8.0, 3.15: -6.0, 3.4: 1.0, 3.5: 0.0})
    frame.particle(0.35, "echo", "eye_c").particle(1.5, "motes", "eye_c").particle(3.1, "echo", "eye_c")

    uns = Layer(r, "unstable_loop", loop=True)                    # scorched: low, drooping, an uneven slow tremble
    uns.kw["length"] = 4.0
    hover(uns, roll=lin([(1.5, S(0.9)), (1.0, S(1.7, 50))]), bob=lin([(-0.7, 1), (0.3, S(1.3, 20)), (0.2, S(1.9, 70))]))
    for g in range(2, 8):
        uns.rot(f"myc{g}_0", mul(2.0, S(1.6 + 0.1 * g, g * 40)), None, mul(1.5, S(2.1 + 0.07 * g, g * 70)))
    for k in range(RINGS):
        uns.rot(f"ring{k}", None, None, mul(3.0, S(0.7 + 0.05 * k, k * 33)))
    skirt(uns, mul(-2.0, S(1.1)))

    fx = {
        "base": A(r, "fx_base", length=6.0).particle(0.0, "spores", "spores").particle(3.0, "motes", "eye_c"),
        "sporeveil": A(r, "fx_sporeveil", length=0.5).particle(0.0, "spores", "spores").particle(0.25, "spores", "gills"),
        "record": A(r, "fx_record", length=0.9).particle(0.0, "motes", "eye_c"),
        "offset": A(r, "fx_offset", length=0.8).particle(0.0, "echo", "cap_top"),
        "frame": A(r, "fx_frame", length=0.7).particle(0.0, "echo", "eye_c").particle(0.35, "motes", "cap_top"),
        "unstable": A(r, "fx_unstable", length=1.2).particle(0.0, "motes", "base_c"),
    }

    # ------------------------------------------------------------------ the vigil (idle behaviours, then the surveillance idle)
    def vigil(name, fidgets):
        st = {
            "alive": {"animations": ["life"], "blend_transition": 0.4, "transitions": [{"settle": f"!({BUSY})"}]},
            # life is a looping layer whose 8 s outlast every wait and behaviour, so the first animation to
            # finish is always the wait or the behaviour (robust whether or not a loop counts as finished)
            "settle": {"animations": ["life", "vigil_settle" if fidgets else "vigil_wait"], "blend_transition": 0.6,
                       "transitions": [{"alive": BUSY}]
                       + [{nm: f"q.any_animation_finished && ({cond})"} for nm, cond in (picks if fidgets else [])]
                       + [{"surveil": "q.any_animation_finished"}]},
            "surveil": {"animations": ["surveil"], "blend_transition": 2.0, "transitions": [{"alive": BUSY}]},
        }
        for nm in (fid if fidgets else {}):
            st[nm] = {"animations": ["life", nm], "blend_transition": 0.5,
                      "transitions": [{"alive": BUSY}, {"surveil": "q.any_animation_finished"}]}
        return {f"controller.animation.{NS}.{r}.{name}": {"initial_state": "alive", "states": st}}

    built = [fp, tp, steady.anim(), gaze.anim(), *[b.anim() for b in blinks.values()], life.anim(), surveil.anim(),
             loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(), hurt.anim(), hurt_lids.anim(), swim.anim(),
             sv_loop.anim(), rec_loop.anim(), off_loop.anim(), frame.anim(), uns.anim(),
             wait_anim(r, "vigil_wait", SETTLE + BEHAVIOUR), wait_anim(r, "vigil_settle", SETTLE),
             *fid.values(), *intro.values(), *fx.values()]
    controllers = {**landing_controller(r), **vigil("vigil", True), **vigil("vigil_plain", False)}
    loops = {"sporeveil": "sporeveil_loop", "record": "record_loop", "offset": "offset_loop", "frame": "frame_loop",
             "unstable": "unstable_loop"}
    blink_of = {"base": "blink", "offset": "blink", "sporeveil": "blink_wide", "unstable": "blink_wilt"}
    animate = {}
    for v in VARIANTS:
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("steady", TP),
               ("vigil" if v in ("base", "offset") else "vigil_plain", TP)]
        if v not in ("record", "frame"):
            lst.append(("gaze", TP))
        if v in blink_of:
            lst.append((blink_of[v], TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("swim", f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"),
                ("hurt", f"{TP} && q.hurt_time > 0"), ("hurt_lids", f"{TP} && q.hurt_time > 0"),
                (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"spores": f"{NS}:geo_spores", "motes": f"{NS}:parallax_motes", "echo": f"{NS}:parallax_echo"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": shared_vars() + ["v.plr_bob = 0;"] + BLINK_PRE + drain_shared()}
