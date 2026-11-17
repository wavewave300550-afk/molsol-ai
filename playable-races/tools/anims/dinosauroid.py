"""Race 007 The Unknown Dinosauroid - attachable animation set (v1.5 premium redesign).

Motion language: calm, weighty, disturbingly observant.  Everything eases (Catmull-Rom keys,
cosine envelopes); idle motion stays slow (nothing above ~3 Hz) and secondary motion follows
through: the tail counterbalances, the crest sways a beat late, ripples travel along the wing
panels and across the fan, and plumes, sails and feathers stream behind with speed.

Rig: the head sits far ahead of the player's head pivot.  The `look` layer cancels the player's
look on head_g (pitch) and hfix (yaw) - both pivot at (0, 24, 0), so the cancellation is exact -
and re-applies it, clamped, along the neck (neck0, neck1) and the skull, so the head follows the
look and stays attached.  When the body dips, leans or twists the neck absorbs it and the skull
stays level: a smooth, stabilised head (no darts, no jitter).

Gait: an agile theropod stride - contact, down (the stance knee yields), passing, up (push-off
rolls over the toes) - with the hips turning and rolling over the stance leg, the fitted body bob
keeping the feet on the ground (races.grounded), the tail counter-swinging, and the fan, wings,
ruff, tufts and leg feathers trailing with speed.

Morphological drift is driven by world time so the gameplay script reads the same phase:
    phase = math.mod(q.time_of_day * 16, 4)      (75 s each; q.time_of_day: midnight = 0)
    0 Plumed  - tufts, ruff and wing feathers longer and fuller
    1 Webbed  - the hindwing fans open a little at rest
    2 Toothed - jaw dropped, teeth bared, pupils contracted
    3 Fanned  - tail fan spread
Each configuration's weight is  clamp((sin(time_of_day * 1440 + 45 - 90k) - 0.6701) * 13.51, 0, 1)
(the sine is >= 0.7071 exactly inside phase k; the clamp makes a ~5 s crossfade centred on each
phase boundary), eased with 0.5 - 0.5 cos(180 w).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from anims.core import NS, T, canon_tree, n
from anims.life import (ATK, FALL, MOVE, PH, RISE, S, SPR, STILL, TCOS, WALKING, KeyLayer, Layer, Rig, body, body_keys,
                        fidget_controller, follow_chain, landing_controller, lin, mul, prod, shared, stride)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, grounded, mirror, pre_animation, view_anims
from models import dinosauroid as D

R = "dinosauroid"
SHOULDER_R = (-D.SHOULDER[0], D.SHOULDER[1], D.SHOULDER[2])
SHOULDER_L = tuple(D.SHOULDER)
RIG = Rig("trunk", D.TRUNK_PIVOT, [("neck0", D.NECK_BASE), ("r_arm_g", SHOULDER_R), ("l_arm_g", SHOULDER_L)])
TAILB = [f"tail{k}" for k in range(D.TAIL)]
FANB = [f"fan{k}" for k in range(D.FAN)]
FAN_C = [(k - (D.FAN - 1) / 2) / ((D.FAN - 1) / 2) for k in range(D.FAN)]        # -1 (right edge) .. 1 (left edge)
EMPTY_R = "(q.is_item_equipped(0) ? 0 : 1)"       # the creature's arm moves on its own only with an empty hand,
EMPTY_L = "(q.is_item_equipped(1) ? 0 : 1)"       # so a held item always stays in the hand
LX = "q.target_x_rotation"
LY = "q.target_y_rotation"
SLEEP = "q.is_sleeping"
ATK_PRE = "math.sin(math.clamp((v.attack_time ?? 0) * 3, 0, 1) * 180)"           # the wind-up (first third)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.4 - 0.2, 0, 1) * 180)"      # the follow-through (late)
SWIM = "(q.is_swimming ? 1 : 0.35)"
COS = f"math.cos({PH})"
SIN = f"math.sin({PH})"


def drift_w(k: int) -> str:
    """Weight 0..1 of morphological-drift configuration k (see the module doc)."""
    ph = 45 - 90 * k
    ph = ph + 360 if ph <= -180 else ph
    arg = f"q.time_of_day * 1440 + {n(ph)}" if ph >= 0 else f"q.time_of_day * 1440 - {n(-ph)}"
    w = f"math.clamp((math.sin({arg}) - 0.6701) * 13.51, 0, 1)"
    return f"(0.5 - 0.5 * math.cos(180 * {w}))"


def _phase(side: int):
    """(swing, early-stance yield, push-off) envelopes of one leg over the stride phase."""
    if side < 0:     # the right leg is forward at phase 180 (contact) and swings forward over 0..180
        return (f"math.max(0, {SIN})", f"math.max(0, -{SIN}) * math.max(0, -{COS})", f"math.max(0, -{SIN}) * math.max(0, {COS})")
    return (f"math.max(0, -{SIN})", f"math.max(0, {SIN}) * math.max(0, {COS})", f"math.max(0, {SIN}) * math.max(0, -{COS})")


def _wrap(a):
    return (np.asarray(a, float) + 180.0) % 360.0 - 180.0


def unfold(model, kl: KeyLayer, frm: str, to: str, order: Dict[str, tuple], k: float = 1.0, overshoot: float = 0.08,
           antic: float = 0.0, default=None, skip=()):
    """Every bone whose rest pose differs between `frm` and `to` moves from the `frm` pose (scaled by k)
    into the `to` pose: per-bone timing order[b] = (start, duration), an optional anticipation (a
    little further toward `frm` first), an overshoot and a settle, on eased (Catmull-Rom) keys."""
    L = kl.length
    for bn in model.order:
        if bn in skip or not model.bone_in_variant(bn, to):
            continue
        b = model.bones[bn]
        dr = _wrap(np.array(model.bone_rot(bn, frm), float) - np.array(model.bone_rot(bn, to), float)) * k
        t_from = np.array(b.variant[frm][0], float) if frm in b.variant else np.zeros(3)
        t_to = np.array(b.variant[to][0], float) if to in b.variant else np.zeros(3)
        dt = (t_from - t_to) * k
        if np.allclose(dr, 0, atol=0.01) and np.allclose(dt, 0, atol=0.01):
            continue
        st, du = order.get(bn, default or (0.0, L * 0.6))
        keys = {0.0: 1.0, st: 1.0, st + du * 0.22: 1.0 + antic, st + du * 0.72: -overshoot, st + du: 0.0, L: 0.0}
        keys = {round(t, 3): v for t, v in sorted(keys.items())}
        if not np.allclose(dr, 0, atol=0.01):
            kl.rot(bn, {t: dr * v for t, v in keys.items()})
        if not np.allclose(dt, 0, atol=0.01):
            kl.pos(bn, {t: dt * v for t, v in keys.items()})


def grow(kl: KeyLayer, bone: str, st: float, du: float, f0, over: float = 1.06):
    """Geometry that only exists in the new form grows in from a fraction (f0: scalar or xyz)."""
    f0 = np.array(f0 if isinstance(f0, (list, tuple)) else [f0, f0, f0], float)
    o = np.where(f0 < 1, over, 1.0)
    kl.scale(bone, {0.0: f0, st: f0, st + du * 0.75: o, st + du: 1.0, kl.length: 1.0})


def shimmer(kl: KeyLayer, bones, t0: float, dur: float, amp: float, axis: int = 1, freq: float = 2.8, lag: float = 0.04):
    """A ripple travelling across a row of feathers: damped, eased, one bone after another."""
    for i, bn in enumerate(bones):
        keys = {0.0: 0.0}
        s0 = t0 + i * lag
        steps = int(dur * freq * 4)
        keys[round(s0, 3)] = 0.0
        for j in range(1, steps + 1):
            t = dur * j / steps
            keys[round(s0 + t, 3)] = amp * np.sin(2 * np.pi * freq * t) * np.exp(-2.6 * t / dur)
        keys[round(s0 + dur + 0.05, 3)] = 0.0
        keys[kl.length] = 0.0
        kl.rot(bn, {t: tuple(v if a == axis else 0.0 for a in range(3)) for t, v in keys.items()})


def eye_blink(kl: KeyLayer, t0: float, dur: float = 0.36):
    """One soft sideways sweep of both outer nictitating membranes (their own bones: scales from different
    animations multiply, so a timed sweep must never share a bone with the periodic blink of the life layer)."""
    for p in ("r", "l"):
        kl.scale(f"{p}_nictk", {0.0: 1, t0 - 0.2: 1, t0: 1, t0 + dur * 0.15: (1, 1, 3), t0 + dur * 0.45: (1, 1, 21.5),
                                t0 + dur * 0.6: (1, 1, 21.5), t0 + dur * 0.85: (1, 1, 3), t0 + dur: 1, t0 + dur + 0.2: 1,
                                kl.length: 1})


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    PLUMED, WEBBED, TOOTHED, FANNED = (shared(drift_w(k), "plr_dw") for k in range(4))
    fp, tp = view_anims(r)
    for p in ("r", "l"):              # the wing feathers and the styliform spar stay out of the first-person view
        for b in (f"{p}_stylus", f"{p}_sec"):
            fp.bone(b, scale=0)

    # ------------------------------------------------------------------ look: the neck carries the head
    look = Layer(r, "look", loop=True)
    look.rot("head_g", f"-{LX}", None, None)        # cancel the player's look exactly (pitch here, yaw on hfix) ...
    look.rot("hfix", None, f"-{LY}", None)
    lxc = f"math.clamp({LX}, -55, 65)"              # ... and re-apply it, clamped, along the neck and the skull
    look.rot("neck0", mul(0.22, lxc), mul(0.3, LY), None)
    look.rot("neck1", mul(0.22, lxc), mul(0.3, LY), None)
    look.rot("skull", mul(0.4, lxc), mul(0.32, LY), None)

    # ------------------------------------------------------------------ life: breath, eyes, crest, ripples, drift
    life = Layer(r, "life", loop=True)
    br = S(0.22)                                    # slow deep breaths (4.5 s); the pouch fills a beat later
    life.scale("trunk", None, lin([(1, 1), (0.012, br)]), lin([(1, 1), (0.026, br)]))
    life.scale("nape", lin([(1, 1), (0.035, br), (0.12, PLUMED)]), lin([(1, 1), (0.03, br), (0.1, PLUMED)]),
               lin([(1, 1), (0.035, br), (0.12, PLUMED)]))
    br2 = S(0.22, -70)
    life.scale("gular", lin([(1, 1), (0.07, br2)]), lin([(1, 1), (0.13, br2)]), lin([(1, 1), (0.07, br2)]))
    life.rot("neck0", mul(-0.9, br), None, None)
    life.rot("skull", mul(0.6, br), None, None)
    body(life, rig, roll=prod(1.3, S(0.071), STILL), twist=prod(2.0, S(0.053, 90), STILL))      # weight shifts
    # soft nictitating blinks: long unblinking stares; shut while asleep; a reflex sweep when hit
    # (one bone, combined with math.max: bone scales from different animations would multiply)
    flinch = "math.sin(math.clamp((10 - q.hurt_time) * 30, 0, 180))"
    for p in ("r", "l"):
        life.scale(f"{p}_nict", None, None,
                   lin([(1, 1), (23, f"math.max(math.max({blink(9.3, 14.7, 0.4, 5.1)}, {SLEEP}), {flinch})")]))
    life.scale("pupils", None, None, lin([(1, 1), (-0.5, TOOTHED), (0.12, S(0.031))]))
    # the crest sways on a slow clock of its own, its far half a beat late
    life.rot("crest0", mul(1.6, S(0.11)), None, mul(0.9, S(0.083, 40)))
    life.rot("crest1", mul(2.2, S(0.11, -55)), None, mul(1.2, S(0.083, -20)))
    for p, side in SIDES:
        ph = 0 if side < 0 else 160
        life.rot(f"{p}_tuft", mul(3.0, S(0.13, ph)), mirror(side, mul(2.0, S(0.1, ph + 60))), None)
        life.scale(f"{p}_tuft", None, lin([(1, 1), (0.2, PLUMED)]), lin([(1, 1), (0.3, PLUMED)]))
        # feather ripples travelling along each wing panel (0.55 Hz, secondaries -> outer primary)
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            life.rot(b, mul(2.4, S(0.55, ph - 50 * k)), None, None)
            life.scale(b, None, None, lin([(1, 1), (0.14, PLUMED)]))
        life.rot(f"{p}_stylus", None, None, mirror(side, mul(1.5, S(0.31, ph + 30))))
        # Webbed: the folded hindwing fan opens a little
        life.rot(f"{p}_sail", None, None, mirror(side, lin([(16, WEBBED), (1.5, S(0.27, ph))])))
    # the fan: a slow ripple across it; Fanned spreads it
    for k, b in enumerate(FANB):
        life.rot(b, None, lin([(1.3, S(0.4, -32 * k)), (24 * FAN_C[k], FANNED)]), None)
    life.rot("fan", lin([(1.5, S(0.17, 30)), (-6, FANNED)]), None, None)
    # Toothed: the jaw drops a little and the teeth are bared
    life.rot("jaw", lin([(6.5, TOOTHED), (1.0, S(0.09, 70))]), None, None)
    # tail balance: a slow wave travelling to the tip; it droops when asleep
    follow_chain(life, TAILB, "y", 1.5, 0.11, lag=35, falloff=1.22)
    follow_chain(life, TAILB, "x", 0.7, 0.09, lag=40, falloff=1.12, phase=90)
    for k, b in enumerate(TAILB):
        life.rot(b, prod(SLEEP, -5 if k else -9), None, None)

    # ------------------------------------------------------------------ locomotion: an agile theropod stride
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    ws = prod(WALKING, s)
    stride(loco, lin([(0.5, WALKING), (0.66, SPR)]))
    for p, side in SIDES:
        sw, yl, pu = _phase(side)
        knee = lin([(1.0, prod(sw, s, lin([(32, WALKING), (50, SPR)]))), (1.0, prod(yl, s, lin([(12, WALKING), (18, SPR)])))])
        loco.rot(f"{p}_shin", knee)                                      # swing: the knee folds; contact: it yields
        loco.rot(f"{p}_meta", lin([(-0.72, knee), (-12, prod(pu, s))]))  # the ankle keeps the foot level, extends at push-off
        loco.rot(f"{p}_foot", lin([(0.45, knee), (16, prod(pu, s))]))   # the toes curl in the swing, roll off at push-off
        loco.rot(f"{p}_talon", prod(-12, sw, s))                         # the sickle lifts clear in the swing
        # the leg feathers trail with speed and fold up in the swing; while the leg reaches forward they
        # lift so they never brush the ground (they are part of the fit, which must only see the toes)
        fwd = f"math.max(0, {'-' if side < 0 else ''}{COS})"
        loco.rot(f"{p}_sfan", lin([(8, s), (10, prod(sw, s)), (8, prod(fwd, s))]), None, None)
        loco.rot(f"{p}_lfan", lin([(6, s), (16, prod(sw, s)), (22, prod(fwd, s))]), None, None)
    body(loco, rig, lean=lin([(4, s), (8, ss)]), twist=prod(6, COS, s), roll=prod(2.2, SIN, ws))
    grounded(model, loco, rig, r, harmonics=8)
    # the head rides steady: the neck absorbs the dip, a smooth nod with the steps, stretched forward at a run
    loco.rot("neck0", lin([(3.0, "v.plr_bob"), (9, ss)]), None, None)
    loco.rot("neck1", lin([(1.2, prod(f"math.sin({PH} * 2 + 40)", ws)), (4, ss)]), None, None)
    loco.rot("skull", lin([(-1.2, prod(f"math.sin({PH} * 2 + 40)", ws)), (-13, ss), (-4, s)]), None, None)
    loco.pos("skull", None, None, prod(-0.45, f"math.sin({PH} * 2 + 40)", ws))
    loco.rot("crest1", prod(1.4, f"math.sin({PH} * 2 - 80)", s), None, None)
    # arms: barely swing, tucked at a sprint (empty hands only)
    for p, side in SIDES:
        e = EMPTY_R if side < 0 else EMPTY_L
        loco.rot(f"{p}_arm_g", lin([(0.85 * (1 if side < 0 else -1), prod(TCOS, e)), (-14, prod(ss, e))]), None, None)
        sw, yl, pu = _phase(side)
        # feathers stream behind with speed (a dragged chain) and flutter at a sprint
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            loco.rot(b, lin([(5.0 * 1.15 ** k, s), (1.5 * 1.15 ** k, prod(f"math.sin({T} * 864 - {50 * k})", ss))]), None, None)
        loco.rot(f"{p}_tuft", lin([(8, s), (2.5, prod(f"math.sin({T} * 792 + {90 if side < 0 else 0})", ss))]), None, None)
    loco.rot("nape", lin([(6, s), (2, prod(f"math.sin({T} * 720)", ss))]), None, None)
    # the tail counter-swings against the hips, bounces with each step and straightens at a run
    amp = lin([(1.0, 1.0), (-0.4, SPR)])
    for k, b in enumerate(TAILB):
        loco.rot(b, lin([(1.2, prod(f"math.sin({PH} * 2 - {60 + 30 * k})", s)), (-(2.0 + 1.2 * k), ss)]),
                 prod(-(3.0 + 1.8 * k), f"math.cos({PH} - {30 + 35 * k})", s, amp), None)
    for k, b in enumerate(FANB):                                       # the fan folds and trails in line
        loco.rot(b, None, prod(-12 * FAN_C[k], s), None)
    loco.rot("fan", prod(10, s), None, None)
    # running, the folded hindwing fans half open (the folded forms only: in the veer they are already open)
    halfwing = Layer(r, "hindwing_run", loop=True)
    for p, side in SIDES:
        halfwing.rot(f"{p}_sail", prod(3, f"math.sin({T} * 792 + {0 if side < 0 else 120})", ss), None,
                     mirror(side, mul(10, ss)))
        halfwing.rot(f"{p}_sfan", None, None, mirror(side, mul(16, ss)))
        halfwing.rot(f"{p}_lfan", None, None, mirror(side, mul(20, ss)))

    # ------------------------------------------------------------------ airborne: legs tuck, everything spreads to balance
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        air.rot(f"{p}_thigh", lin([(-24, RISE), (-10, FALL)]))
        air.rot(f"{p}_shin", lin([(40, RISE), (12, FALL)]))
        air.rot(f"{p}_meta", lin([(-22, RISE), (-6, FALL)]))
        air.rot(f"{p}_foot", lin([(28, RISE), (-10, FALL)]))
        air.rot(f"{p}_sail", None, None, mirror(side, lin([(12, RISE), (38, FALL)])))
        air.rot(f"{p}_sfan", None, None, mirror(side, lin([(10, RISE), (30, FALL)])))
        air.rot(f"{p}_lfan", None, None, mirror(side, lin([(12, RISE), (36, FALL)])))
        air.rot(f"{p}_stylus", None, None, mirror(side, mul(-10, FALL)))
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            air.rot(b, lin([(-5, RISE), (6 + 2 * k, FALL)]), mirror(side, mul(-6 - 3 * k, FALL)), None)
    for k, b in enumerate(FANB):
        air.rot(b, None, prod(20 * FAN_C[k], FALL), None)
    air.rot("tail0", lin([(-8, RISE), (10, FALL)]))
    air.rot("tail2", lin([(-4, RISE), (5, FALL)]))
    air.rot("nape", lin([(-4, RISE), (8, FALL)]))
    body(air, rig, lean=lin([(-4, RISE), (5, FALL)]))
    air.rot("skull", lin([(4, RISE), (-5, FALL)]))

    land = KeyLayer(r, "land", 0.55)
    land_hard = KeyLayer(r, "land_hard", 0.85)
    for kl, g in ((land, 0.6), (land_hard, 1.0)):
        L = kl.length
        t1, t2 = 0.1 * (1 + g * 0.3), 0.3 + 0.18 * g
        body_keys(kl, rig, {0: {"bob": -1.2 * g, "lean": 7 * g}, t1: {"bob": -1.8 * g, "lean": 9 * g},
                            t2: {"bob": 0.25, "lean": -1.5}, L: {}})
        for p, side in SIDES:
            kl.rot(f"{p}_thigh", {0: (-18 * g, 0, 0), t1: (-24 * g, 0, 0), t2: (-2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_shin", {0: (30 * g, 0, 0), t1: (40 * g, 0, 0), t2: (3, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_meta", {0: (-12 * g, 0, 0), t1: (-16 * g, 0, 0), t2: (-1, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_sail", {0: (0, 0, 0), 0.06: (0, 0, mirror(side, 24 * g)), t2: (0, 0, mirror(side, -3)), L: (0, 0, 0)})
            kl.rot(f"{p}_lfan", {0: (0, 0, 0), 0.08: (-10 * g, 0, mirror(side, 24 * g)), t2: (0, 0, 0), L: (0, 0, 0)})
            for k, b in enumerate((f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
                kl.rot(b, {0: (0, 0, 0), 0.08 + 0.03 * k: (10 * g, 0, 0), t2 + 0.05 * k: (-3, 0, 0), L: (0, 0, 0)})
        kl.rot("tail0", {0: (-12 * g, 0, 0), t1: (-16 * g, 0, 0), t2: (5, 0, 0), L: (0, 0, 0)})
        kl.rot("tail2", {0: (0, 0, 0), t1 + 0.04: (-7 * g, 0, 0), t2 + 0.06: (4, 0, 0), L: (0, 0, 0)})
        kl.rot("tail4", {0: (0, 0, 0), t1 + 0.08: (-8 * g, 0, 0), t2 + 0.12: (5, 0, 0), L: (0, 0, 0)})
        for k, b in enumerate(FANB):
            kl.rot(b, {0: (0, 0, 0), t1: (0, 18 * g * FAN_C[k], 0), t2 + 0.1: (0, -2 * FAN_C[k], 0), L: (0, 0, 0)})
        kl.rot("neck0", {0: (4 * g, 0, 0), t1: (6 * g, 0, 0), t2: (-2, 0, 0), L: (0, 0, 0)})
        kl.rot("skull", {0: (4 * g, 0, 0), t1: (-5 * g, 0, 0), t2: (1.5, 0, 0), L: (0, 0, 0)})
        kl.rot("nape", {0: (0, 0, 0), t1: (10 * g, 0, 0), t2: (-2, 0, 0), L: (0, 0, 0)})
        kl.scale("gular", {0: 1, t1: (1.12, 1.35, 1.12), t2: 1, L: 1})
        kl.particle(0.0, "stepdust", "r_sickle").particle(0.0, "stepdust", "l_sickle")
    land_hard.particle(0.05, "feathers", "chest")

    # ------------------------------------------------------------------ attack: wind-up, a raking lunge, follow-through
    atk = Layer(r, "attack", loop=True)
    # the lean / twist curves are computed once per frame (they reach the arms through a pitch compensation)
    body(atk, rig, lean=shared(lin([(-3, ATK_PRE), (7, ATK)]), "plr_at"), twist=shared(lin([(5, ATK_PRE), (-10, ATK)]), "plr_at"))
    atk.rot("neck0", lin([(-6, ATK_PRE), (9, ATK)]), None, None)
    atk.rot("neck1", lin([(-4, ATK_PRE), (6, ATK)]), None, None)
    atk.rot("skull", lin([(-8, ATK_PRE), (10, ATK)]), prod(-6, ATK), None)
    atk.pos("skull", None, None, lin([(0.6, ATK_PRE), (-1.2, ATK)]))
    atk.rot("jaw", prod(16, ATK))
    atk.rot("nape", prod(8, ATK))
    atk.rot("r_stylus", None, None, prod(24, ATK2))
    atk.rot("r_sec", prod(-8, ATK), None, None)
    for k in range(3):
        atk.rot(f"r_pri{k}", prod(-6 - 3 * k, ATK), prod(-(10 + 6 * k), ATK), None)
    atk.rot("r_talon", prod(-34, ATK))
    atk.rot("l_talon", prod(-20, ATK2))
    atk.rot("tail2", None, prod(9, ATK2), None)
    atk.rot("tail4", None, prod(13, ATK2), None)
    for k, b in enumerate(FANB):
        atk.rot(b, None, prod(12 * FAN_C[k], ATK2), None)

    # ------------------------------------------------------------------ hurt: a recoil, the display flares, then it turns back to look
    hurt = KeyLayer(r, "hurt", 1.0)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -8, "roll": 3}, 0.2: {"lean": -5, "roll": 2}, 0.55: {"lean": -2},
                          0.85: {"lean": 1}, 1.0: {}})
    hurt.rot("neck0", {0: (0, 0, 0), 0.05: (-14, -6, 0), 0.3: (-11, -5, 0), 0.6: (-6, -10, 0), 0.85: (1, -2, 0), 1.0: (0, 0, 0)})
    hurt.rot("skull", {0: (0, 0, 0), 0.05: (-10, -8, -6), 0.3: (-8, -8, -5), 0.6: (-4, -16, -3), 0.85: (1, -3, 0),
                       1.0: (0, 0, 0)})
    hurt.rot("nape", {0: (0, 0, 0), 0.06: (22, 0, 0), 0.45: (16, 0, 0), 0.9: (0, 0, 0), 1.0: (0, 0, 0)})
    hurt.scale("nape", {0: 1, 0.06: 1.14, 0.5: 1.08, 0.9: 1, 1.0: 1})
    hurt.scale("gular", {0: 1, 0.07: (1.25, 1.6, 1.25), 0.4: (1.1, 1.25, 1.1), 0.8: 1, 1.0: 1})
    hurt.scale("pupils", {0: 1, 0.06: (1, 1, 0.45), 0.5: (1, 1, 0.6), 0.85: 1, 1.0: 1})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.rot(f"{p}_tuft", {0: (0, 0, 0), 0.06: (-22, -sg * 16, 0), 0.6: (-14, -sg * 10, 0), 1.0: (0, 0, 0)})
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            hurt.rot(b, {0: (0, 0, 0), 0.06 + 0.02 * k: (-10, sg * 14, 0), 0.5: (-5, sg * 6, 0), 0.9: (0, 0, 0), 1.0: (0, 0, 0)})
    for k, b in enumerate(FANB):
        hurt.rot(b, {0: (0, 0, 0), 0.08: (0, 30 * FAN_C[k], 0), 0.35: (0, 18 * FAN_C[k], 0), 0.7: (0, 0, 0), 1.0: (0, 0, 0)})
    hurt.rot("tail1", {0: (0, 0, 0), 0.06: (6, 14, 0), 0.25: (0, -9, 0), 0.5: (0, 4, 0), 0.8: (0, 0, 0), 1.0: (0, 0, 0)})
    hurt.rot("tail3", {0: (0, 0, 0), 0.1: (4, 10, 0), 0.32: (0, -8, 0), 0.6: (0, 3, 0), 0.9: (0, 0, 0), 1.0: (0, 0, 0)})
    hurt.particle(0.0, "feathers", "chest")

    # ------------------------------------------------------------------ swimming: tail-driven, feathers sleeked
    swim = Layer(r, "swim", loop=True)
    swim.kw["length"] = 2.0
    swim.rot("tail0", prod(-60, SWIM), mul(8, S(0.9)), None)
    for k in range(1, D.TAIL):
        swim.rot(f"tail{k}", None, mul(8 + 4 * k, S(0.9, -45 * k)), None)
    for k, b in enumerate(FANB):
        swim.rot(b, None, -14 * FAN_C[k], None)
    for p, side in SIDES:
        ph = 0 if side < 0 else 180
        swim.rot(f"{p}_thigh", mul(26, S(0.9, ph)), None, None)
        swim.rot(f"{p}_shin", lin([(22, 1), (20, S(0.9, ph + 70))]), None, None)
        swim.rot(f"{p}_meta", mul(-14, S(0.9, ph + 120)), None, None)
        for b in (f"{p}_lfan", f"{p}_sfan"):
            swim.rot(b, 16, None, None)
        for b in (f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2"):
            swim.rot(b, -8, None, None)
        swim.rot(f"{p}_tuft", 14, None, None)
    swim.rot("nape", 12, None, None)
    swim.rot("neck0", -18, None, None)
    swim.rot("skull", 16, None, None)

    # ------------------------------------------------------------------ idle behaviours (each a 3-6 s performance)
    def still_look(name, length, keys):
        kl = KeyLayer(r, name, length)
        kl.rot("skull", {t: v[0] for t, v in keys.items()})
        kl.rot("neck1", {t: v[1] for t, v in keys.items()})
        return kl

    wait = still_look("fidget_wait", 7.0, {0: ((0, 0, 0), (0, 0, 0)), 1.4: ((2, 13, 3), (0, 7, 0)), 3.3: ((2, 13, 3), (0, 7, 0)),
                                           4.8: ((-1, -11, -2), (0, -6, 0)), 6.2: ((-1, -11, -2), (0, -6, 0)),
                                           7.0: ((0, 0, 0), (0, 0, 0))})
    rest = still_look("fidget_rest", 3.5, {0: ((0, 0, 0), (0, 0, 0)), 1.4: ((5, 0, 0), (2, 0, 0)), 2.4: ((5, 0, 0), (2, 0, 0)),
                                           3.5: ((0, 0, 0), (0, 0, 0))})
    fid = []
    # the long stare: the head creeps forward and holds, the pupils narrow to threads, one slow sweep of the membrane
    stare = KeyLayer(r, "fidget_stare", 6.0)
    stare.rot("neck0", {0: (0, 0, 0), 1.2: (5, 0, 0), 5.0: (5, 0, 0), 6.0: (0, 0, 0)})
    stare.rot("neck1", {0: (0, 0, 0), 1.2: (4, 0, 0), 5.0: (4, 0, 0), 6.0: (0, 0, 0)})
    stare.rot("skull", {0: (0, 0, 0), 1.2: (-9, 0, 0), 5.0: (-9, 0, 0), 6.0: (0, 0, 0)})
    stare.pos("skull", {0: (0, 0, 0), 1.4: (0, 0, -0.7), 5.0: (0, 0, -0.7), 6.0: (0, 0, 0)})
    stare.scale("pupils", {0: 1, 0.8: 1, 2.6: (1, 1, 0.25), 4.8: (1, 1, 0.25), 5.7: 1, 6.0: 1})
    stare.rot("crest0", {0: (0, 0, 0), 1.6: (4, 0, 0), 4.8: (4, 0, 0), 6.0: (0, 0, 0)})
    eye_blink(stare, 4.85, 0.7)
    stare.scale("gular", {0: 1, 5.0: 1, 5.4: (0.94, 0.9, 0.94), 6.0: 1})
    body_keys(stare, rig, {0: {}, 1.2: {"lean": 3}, 5.0: {"lean": 3}, 6.0: {}})
    fid.append(stare)
    # the pouch display: a dip, the head rises, three swelling pulses of the pouch, crest and tufts up
    pouch = KeyLayer(r, "fidget_pouch", 4.6)
    pouch.rot("neck0", {0: (0, 0, 0), 0.35: (4, 0, 0), 0.9: (-10, 0, 0), 3.4: (-10, 0, 0), 4.6: (0, 0, 0)})
    pouch.rot("skull", {0: (0, 0, 0), 0.35: (5, 0, 0), 0.9: (-6, 0, 0), 3.4: (-6, 0, 0), 4.6: (0, 0, 0)})
    pouch.scale("gular", {0: 1, 0.35: (0.92, 0.9, 0.92), 1.0: (1.3, 1.7, 1.3), 1.5: (1.12, 1.25, 1.12), 2.1: (1.35, 1.85, 1.35),
                          2.6: (1.15, 1.3, 1.15), 3.2: (1.4, 2.0, 1.4), 4.0: 1, 4.6: 1})
    pouch.rot("crest0", {0: (0, 0, 0), 0.9: (8, 0, 0), 3.4: (8, 0, 0), 4.6: (0, 0, 0)})
    pouch.rot("jaw", {0: (0, 0, 0), 0.9: (5, 0, 0), 3.3: (5, 0, 0), 4.0: (0, 0, 0)})
    pouch.rot("nape", {0: (0, 0, 0), 0.9: (10, 0, 0), 3.4: (10, 0, 0), 4.6: (0, 0, 0)})
    for p, side in SIDES:
        pouch.rot(f"{p}_tuft", {0: (0, 0, 0), 0.9: (14, mirror(side, -8), 0), 3.4: (14, mirror(side, -8), 0), 4.6: (0, 0, 0)})
    pouch.particle(2.1, "displaymotes", "throat").particle(3.2, "displaymotes", "throat")
    fid.append(pouch)
    # preening the fan: the tail curls round to the right, the fan opens, the beak combs through it
    preen = KeyLayer(r, "fidget_preen", 5.2)
    for k, (a, lift) in enumerate(((-8, 2), (-14, 3), (-18, 3), (-20, 2), (-18, 0))):
        preen.rot(f"tail{k}", {0: (0, 0, 0), 1.0: (lift, a, 0), 3.8: (lift, a, 0), 5.0: (0, 0, 0), 5.2: (0, 0, 0)})
    for k, b in enumerate(FANB):
        preen.rot(b, {0: (0, 0, 0), 1.2: (0, 30 * FAN_C[k], 0), 3.6: (0, 30 * FAN_C[k], 0), 4.6: (0, 0, 0), 5.2: (0, 0, 0)})
    preen.rot("neck0", {0: (0, 0, 0), 1.0: (6, -45, 0), 3.8: (6, -45, 0), 4.8: (0, 0, 0), 5.2: (0, 0, 0)})
    preen.rot("neck1", {0: (0, 0, 0), 1.0: (8, -35, 0), 3.8: (8, -35, 0), 4.8: (0, 0, 0), 5.2: (0, 0, 0)})
    nib = {0: (0, 0, 0), 1.0: (18, -30, -8), 1.4: (18, -30, -8)}
    for j in range(8):                                                     # gentle combing strokes, about 2 per second
        nib[round(1.6 + 0.25 * j, 3)] = (24 if j % 2 == 0 else 16, -30, -8)
    nib.update({3.8: (18, -30, -8), 4.8: (0, 0, 0), 5.2: (0, 0, 0)})
    preen.rot("skull", nib)
    jw = {0: (0, 0, 0), 1.5: (0, 0, 0)}
    for j in range(8):
        jw[round(1.6 + 0.25 * j, 3)] = (6 if j % 2 == 0 else 1, 0, 0)
    jw.update({3.7: (0, 0, 0), 5.2: (0, 0, 0)})
    preen.rot("jaw", jw)
    body_keys(preen, rig, {0: {}, 1.0: {"twist": -8}, 3.8: {"twist": -8}, 5.2: {}})
    preen.particle(2.2, "feathers", "tail_fan")
    fid.append(preen)
    # a slow, curious head tilt to one side, then slowly to the other; the pupils widen
    study = KeyLayer(r, "fidget_study", 4.8)
    study.rot("skull", {0: (0, 0, 0), 1.4: (2, 8, 22), 2.4: (2, 8, 22), 3.6: (0, -6, -18), 4.0: (0, -6, -18), 4.8: (0, 0, 0)})
    study.rot("neck1", {0: (0, 0, 0), 1.4: (3, 6, 0), 2.4: (3, 6, 0), 3.6: (3, -4, 0), 4.0: (3, -4, 0), 4.8: (0, 0, 0)})
    study.rot("crest1", {0: (0, 0, 0), 1.6: (0, 0, -4), 2.4: (0, 0, -4), 3.8: (0, 0, 3), 4.8: (0, 0, 0)})
    study.pos("skull", {0: (0, 0, 0), 1.4: (0, 0, -0.5), 4.0: (0, 0, -0.5), 4.8: (0, 0, 0)})
    study.scale("pupils", {0: 1, 1.4: (1, 1, 1.4), 4.0: (1, 1, 1.4), 4.8: 1})
    fid.append(study)
    picks = [("fidget_stare", "math.mod(math.floor(q.life_time * 1.3), 5) == 0"),
             ("fidget_pouch", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_preen", "math.mod(math.floor(q.life_time * 1.3), 5) == 2"),
             ("fidget_study", "math.mod(math.floor(q.life_time * 1.3), 5) == 3")]

    # ------------------------------------------------------------------ forms: intros
    intro = {}
    # base: the feathers settle with one slow rousing shake
    ib = KeyLayer(r, "intro_base", 1.0, loop="hold")
    unfold(model, ib, "display", "base", {}, k=0.22, default=(0.0, 0.55), skip=TAILB + ["fan"] + FANB)
    for b, a in (("nape", (6, 0, 0)), ("r_tuft", (5, 0, 0)), ("l_tuft", (5, 0, 0)), ("tail3", (0, 5, 0)), ("tail4", (0, 7, 0))):
        keys = {0.0: (0, 0, 0)}
        for j in range(1, 9):
            t = 0.1 + 0.08 * j
            keys[round(t, 3)] = tuple(x * np.sin(np.pi * j / 2) * np.exp(-0.35 * j) for x in a)
        keys[0.9] = (0, 0, 0)
        keys[1.0] = (0, 0, 0)
        ib.rot(b, keys)
    intro["base"] = ib
    # night: the display skin wakes - the pouch puffs once, the crest lifts, plumes stir, one slow blink
    iw = KeyLayer(r, "intro_night", 1.4, loop="hold")
    iw.scale("gular", {0: 1, 0.3: (1.2, 1.55, 1.2), 0.7: (1.05, 1.1, 1.05), 1.1: 1, 1.4: 1})
    iw.rot("crest0", {0: (0, 0, 0), 0.35: (7, 0, 0), 1.2: (0, 0, 0), 1.4: (0, 0, 0)})
    iw.rot("nape", {0: (0, 0, 0), 0.3: (9, 0, 0), 1.0: (0, 0, 0), 1.4: (0, 0, 0)})
    eye_blink(iw, 0.5, 0.6)
    iw.particle(0.25, "displaymotes", "throat").particle(0.55, "displaymotes", "crest_tip")
    intro["night"] = iw
    # display: anticipation (a dip, feathers pulled in), then crest, pouch, wings, tail and fan open in a wave,
    # then a shimmer runs across the fans
    idp = KeyLayer(r, "intro_display", 1.5, loop="hold")
    order = {"skull": (0.0, 0.45), "jaw": (0.25, 0.3), "crest0": (0.1, 0.45), "crest1": (0.18, 0.45), "nape": (0.12, 0.4),
             "r_tuft": (0.2, 0.35), "l_tuft": (0.22, 0.35), "fan": (0.42, 0.42)}
    for p in ("r", "l"):
        order.update({f"{p}_sec": (0.28, 0.42), f"{p}_stylus": (0.3, 0.42), f"{p}_pri0": (0.36, 0.42), f"{p}_pri1": (0.4, 0.42),
                      f"{p}_pri2": (0.44, 0.42)})
    for k, b in enumerate(TAILB):
        order[b] = (0.3 + 0.05 * k, 0.4)
    for k, b in enumerate(FANB):
        order[b] = (0.62 + 0.035 * abs(k - 4), 0.32)
    unfold(model, idp, "base", "display", order, antic=0.12, overshoot=0.07)
    grow(idp, "gular", 0.22, 0.45, 0.45)
    body_keys(idp, rig, {0: {}, 0.18: {"lean": 4, "bob": -0.6}, 0.55: {"lean": -3, "bob": 0.3}, 0.9: {}, 1.5: {}})
    shimmer(idp, FANB, 1.0, 0.45, 3.0)
    shimmer(idp, ["r_pri2", "r_pri1", "r_pri0", "r_sec"], 1.02, 0.4, 3.5, axis=0)
    shimmer(idp, ["l_pri2", "l_pri1", "l_pri0", "l_sec"], 1.02, 0.4, 3.5, axis=0)
    idp.particle(0.4, "displaymotes", "throat").particle(0.6, "displaymotes", "crest_tip").particle(1.0, "feathers", "tail_fan")
    intro["display"] = idp
    # veer: crouch, then the hindwing fans snap open, the leg feathers spread, the tail becomes a rudder
    iv = KeyLayer(r, "intro_veer", 0.5, loop="hold")
    order = {"trunk": (0.0, 0.2), "hfix": (0.0, 0.2), "r_arm_g": (0.0, 0.2), "l_arm_g": (0.0, 0.2), "fan": (0.1, 0.22)}
    for p in ("r", "l"):
        order.update({f"{p}_sfan": (0.08, 0.16), f"{p}_lfan": (0.1, 0.16)})
    for k, b in enumerate(TAILB):
        order[b] = (0.04 + 0.03 * k, 0.2)
    for k, b in enumerate(FANB):
        order[b] = (0.12, 0.18)
    unfold(model, iv, "base", "veer", order, antic=0.08, overshoot=0.06)
    for p in ("r", "l"):
        grow(iv, f"{p}_sail", 0.05, 0.16, 0.15, over=1.08)
    body_keys(iv, rig, {0: {"bob": -0.8, "lean": 4}, 0.08: {"bob": -1.0, "lean": 6}, 0.2: {}, 0.5: {}})
    iv.particle(0.06, "feathers", "r_sickle").particle(0.08, "feathers", "l_sickle")
    intro["veer"] = iv
    # overflow: everything opens in a cascade - crest, pouch, wings, tail fan, hindwings - and lights
    io = KeyLayer(r, "intro_overflow", 2.0, loop="hold")
    order = {"skull": (0.15, 0.5), "jaw": (0.35, 0.35), "crest0": (0.2, 0.5), "crest1": (0.28, 0.5), "nape": (0.2, 0.45),
             "r_tuft": (0.3, 0.4), "l_tuft": (0.32, 0.4), "fan": (0.62, 0.45), "trunk": (0.9, 0.3), "hfix": (0.9, 0.3),
             "r_arm_g": (0.9, 0.3), "l_arm_g": (0.9, 0.3)}
    for p in ("r", "l"):
        order.update({f"{p}_sec": (0.45, 0.45), f"{p}_stylus": (0.48, 0.45), f"{p}_pri0": (0.52, 0.45),
                      f"{p}_pri1": (0.56, 0.45), f"{p}_pri2": (0.6, 0.45), f"{p}_sfan": (1.05, 0.25), f"{p}_lfan": (1.1, 0.25)})
    for k, b in enumerate(TAILB):
        order[b] = (0.5 + 0.05 * k, 0.45)
    for k, b in enumerate(FANB):
        order[b] = (0.8 + 0.035 * abs(k - 4), 0.35)
    unfold(model, io, "base", "overflow", order, antic=0.12, overshoot=0.08)
    grow(io, "gular", 0.35, 0.5, 0.45)
    for p in ("r", "l"):
        grow(io, f"{p}_sail", 1.0, 0.2, 0.15, over=1.08)
    body_keys(io, rig, {0: {}, 0.25: {"lean": 5, "bob": -0.8}, 0.7: {"lean": -4, "bob": 0.4}, 1.2: {}, 2.0: {}})
    shimmer(io, FANB, 1.3, 0.5, 3.0)
    io.particle(0.25, "displaymotes", "eyes").particle(0.6, "displaymotes", "throat").particle(1.0, "displaymotes", "crest_tip") \
        .particle(1.25, "feathers", "tail_fan")
    intro["overflow"] = io

    # ------------------------------------------------------------------ forms: loops
    # display: a slow rattle travelling across the fan, the pouch throbbing, the head swaying, high
    disp = Layer(r, "display_loop", loop=True)
    disp.scale("gular", lin([(1, 1), (0.06, S(0.55))]), lin([(1, 1), (0.1, S(0.55))]), lin([(1, 1), (0.06, S(0.55))]))
    for k, b in enumerate(FANB):
        disp.rot(b, mul(0.8, S(2.4, -40 * k)), mul(1.4, S(2.4, -40 * k + 90)), None)
    disp.rot("fan", mul(2.0, S(0.3)), mul(3.5, S(0.21, 40)), None)
    for p, side in SIDES:
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            disp.rot(b, mul(3.0, S(0.42, -45 * k + (0 if side < 0 else 120))), None, None)
    disp.rot("neck0", None, mul(6, S(0.25)), mul(2, S(0.25, 90)))
    disp.rot("crest1", mul(2.0, S(0.6)), None, None)
    disp.rot("nape", mul(2.5, S(0.5, 30)), None, None)
    # veer: the membranes and leg feathers flutter in the airflow, the fan steers as a rudder, a gliding sway
    veer = Layer(r, "veer_loop", loop=True)
    for p, side in SIDES:
        veer.rot(f"{p}_sail", mul(1.5, S(2.6, 0 if side < 0 else 70)), None, mirror(side, mul(2.5, S(1.7, 0 if side < 0 else 50))))
        veer.rot(f"{p}_lfan", None, None, mirror(side, mul(3, S(2.2, 30))))
        veer.rot(f"{p}_sfan", None, None, mirror(side, mul(2.5, S(1.9, 70))))
    veer.rot("fan", None, mul(7, S(0.6)), mul(4, S(0.6, 90)))
    body(veer, rig, roll=mul(3, S(0.5)))
    veer.rot("skull", mul(-3, S(0.5)), None, mul(-3, S(0.5)))
    # overflow: every structure on its own slow clock at once - the four drift configurations together
    over = Layer(r, "overflow_loop", loop=True)
    over.scale("gular", lin([(1, 1), (0.1, S(0.9))]), lin([(1, 1), (0.16, S(0.9))]), lin([(1, 1), (0.1, S(0.9))]))
    over.rot("crest0", mul(4, S(0.31)), None, None)
    over.rot("crest1", mul(4, S(0.47, 60)), None, None)
    over.rot("jaw", lin([(6, 1), (4, S(0.73))]), None, None)
    over.scale("pupils", None, None, lin([(1, 1), (0.45, S(0.66))]))
    for p, side in SIDES:
        over.scale(f"{p}_tuft", None, 1.2, 1.3)
        over.rot(f"{p}_tuft", mul(6, S(0.41, 40)), None, None)
        over.rot(f"{p}_sail", None, None, mirror(side, mul(7, S(0.52, 0 if side < 0 else 30))))
        over.rot(f"{p}_lfan", None, None, mirror(side, mul(6, S(0.44, 50))))
        for k, b in enumerate((f"{p}_sec", f"{p}_pri0", f"{p}_pri1", f"{p}_pri2")):
            over.rot(b, mul(4, S(0.37, -40 * k + (0 if side < 0 else 90))), None, None)
    for k, b in enumerate(FANB):
        over.rot(b, None, mul(8 * FAN_C[k], S(0.4, 10)), None)
    over.rot("nape", mul(5, S(0.8)), None, None)
    over.rot("skull", mul(3, S(0.13)), mul(5, S(0.09, 30)), mul(4, S(0.11)))

    fx = {
        "base": A(r, "fx_base", length=16.0).particle(0.0, "feathers", "tail_fan"),
        "night": A(r, "fx_night", length=5.0).particle(0.0, "displaymotes", "throat").particle(2.5, "displaymotes", "crest_tip"),
        "display": A(r, "fx_display", length=0.8).particle(0.0, "displaymotes", "crest_tip").particle(0.4, "displaymotes", "throat"),
        "veer": A(r, "fx_veer", length=0.3).particle(0.0, "feathers", "r_sickle").particle(0.15, "feathers", "l_sickle"),
        "overflow": A(r, "fx_overflow", length=1.2).particle(0.0, "displaymotes", "eyes").particle(0.4, "displaymotes", "throat")
        .particle(0.8, "displaymotes", "crest_tip"),
    }
    built = [fp, tp, look.anim(), life.anim(), loco.anim(), halfwing.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), swim.anim(), disp.anim(), veer.anim(), over.anim(), wait.anim(), rest.anim(), *[f.anim() for f in fid],
             *[a.anim() for a in intro.values()], *fx.values()]
    controllers = {**landing_controller(r), **fidget_controller(r, picks)}
    loops = {"display": "display_loop", "veer": "veer_loop", "overflow": "overflow_loop"}
    swim_c = f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"
    animate = {}
    for v in D.VARIANTS:
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("look", None), ("life", TP)]
        if v in ("base", "night"):
            lst.append(("fidget", TP))
        lst.append(("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"))
        if v not in D.WINGS:
            lst.append(("hindwing_run", f"{TP} && {GAIT_OK} && !q.is_swimming"))
        lst += [("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP), ("swim", swim_c),
                ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"stepdust": f"{NS}:step_dust", "feathers": f"{NS}:dino_feathers", "displaymotes": f"{NS}:dino_display"}
    for a in built:                               # fold "+ -" / "- -" here too (the build folds them again)
        a.bones = canon_tree(a.bones)
    return {"anims": built, "animate": animate, "particles": particles, "controllers": canon_tree(controllers),
            "pre": canon_tree(pre_animation(r))}
