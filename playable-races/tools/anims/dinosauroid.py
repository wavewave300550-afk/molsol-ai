"""Race 007 The Unknown Dinosauroid - attachable animation set (Expansion 02).

Motion language: quiet, analytical, ancient - and wrong in small ways.  The body is calm and
slow (breathing, a tail that balances on its own slow clock, a throat that fills and empties);
the head is a bird's: it darts to a new bearing in a single frame and then holds perfectly
still, for a long time.  Long unblinking stares end in a sideways sweep of the nictitating
membrane.  Membranes twitch on their own.  Walking it is a theropod - long reaching strides,
knees folding, hips and shoulders counter-turning, the head held level and thrust forward
step by step like a pigeon's; running, the tail straightens and the hindwings half open.

Rig: the head sits far ahead of the player's head pivot.  The `look` layer cancels the
player's look on head_g (pitch) and hfix (yaw) - both pivot at (0, 24, 0), so the cancellation
is exact - and re-applies it on the neck (at the real base of the neck) and the skull.

Morphological drift is driven by world time so the gameplay script reads the same phase:
    phase = math.mod(q.time_of_day * 16, 4)      (75 s each; q.time_of_day: midnight = 0)
    0 Plumed  - tufts and arm feathers longer and fuller
    1 Webbed  - hindlimb membranes wider, opened a little at rest
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
from anims.life import (ATK, BUMP, FALL, MOVE, PH, RISE, S, SPR, TURN, WALKING, KeyLayer, Layer, Rig, arm_swing, body,
                        body_keys, chain_wave, dart, fidget_controller, landing_controller, lin, mul, prod, stride)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, grounded, mirror, pre_animation, shake, view_anims
from models import dinosauroid as D

R = "dinosauroid"
SHOULDER_R = (-D.SHOULDER[0], D.SHOULDER[1], D.SHOULDER[2])
RIG = Rig("trunk", D.TRUNK_PIVOT, [("neck", D.NECK_BASE), ("r_arm_g", SHOULDER_R),
                                    ("l_arm_g", (D.SHOULDER[0], D.SHOULDER[1], D.SHOULDER[2]))])
TAILB = [f"tail{k}" for k in range(D.TAIL)]
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
EMPTY_R = "(q.is_item_equipped(0) ? 0 : 1)"
EMPTY_L = "(q.is_item_equipped(1) ? 0 : 1)"
LX = "q.target_x_rotation"
LY = "q.target_y_rotation"
SLEEP = "q.is_sleeping"
# the swing arriving later (a whip down the tail, a flick of the stylus after the rake)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.4 - 0.2, 0, 1) * 180)"
SWIM = "(q.is_swimming ? 1 : 0.35)"
AIRF = "(q.is_on_ground ? 0 : 1)"


def drift_w(k: int) -> str:
    """Weight 0..1 of morphological-drift configuration k (see the module doc)."""
    ph = 45 - 90 * k
    ph = ph + 360 if ph <= -180 else ph
    arg = f"q.time_of_day * 1440 + {n(ph)}" if ph >= 0 else f"q.time_of_day * 1440 - {n(-ph)}"
    w = f"math.clamp((math.sin({arg}) - 0.6701) * 13.51, 0, 1)"
    return f"(0.5 - 0.5 * math.cos(180 * {w}))"


PLUMED, WEBBED, TOOTHED, FANNED = (drift_w(k) for k in range(4))


def unfold(model, name: str, frm: str, to: str, length: float, order: Dict[str, tuple], k: float = 1.0,
           overshoot: float = 0.08, grow: Dict[str, tuple] = None):
    """Transition from the `frm` geometry pose (scaled by k) into the `to` pose with per-bone
    timing (start, duration) and a small overshoot; `grow` bones scale up from a fraction."""
    a = A(R, name, loop="hold", length=length)
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        b = model.bones[bn]
        dr = (np.array(model.bone_rot(bn, frm), float) - np.array(model.bone_rot(bn, to), float)) * k
        t_from = np.array(b.variant[frm][0], float) if frm in b.variant else np.zeros(3)
        t_to = np.array(b.variant[to][0], float) if to in b.variant else np.zeros(3)
        dt = (t_from - t_to) * k
        if np.allclose(dr, 0, atol=0.01) and np.allclose(dt, 0, atol=0.01):
            continue
        st, du = order.get(bn, (0.0, length * 0.75))
        keys = {0.0: 1.0, st: 1.0, st + du * 0.7: -overshoot, st + du: 0.0, length: 0.0}
        rot = None if np.allclose(dr, 0, atol=0.01) else {t: [round(float(x), 3) for x in dr * v] for t, v in keys.items()}
        pos = None if np.allclose(dt, 0, atol=0.01) else {t: [round(float(x), 3) for x in dt * v] for t, v in keys.items()}
        a.bone(bn, rot=rot, pos=pos)
    for bn, (st, du, f0) in (grow or {}).items():
        f0 = list(f0) if isinstance(f0, (list, tuple)) else [f0, f0, f0]
        over = [1.06 if f < 1 else 1.0 for f in f0]
        a.bone(bn, scale={0.0: f0, st: f0, st + du * 0.75: over, st + du: [1, 1, 1], length: [1, 1, 1]})
    return a


def _wake(r):
    """intro_night - the display skin wakes in the dark: the pouch puffs once, the crest lifts,
    the quills shiver, one slow sweep of the nictitating membranes."""
    k = KeyLayer(r, "intro_night", 1.0, loop="hold")
    k.scale("gular", {0: 1, 0.25: (1.2, 1.55, 1.2), 0.6: (1.05, 1.1, 1.05), 1.0: 1})
    k.rot("crest0", {0: (0, 0, 0), 0.3: (7, 0, 0), 1.0: (0, 0, 0)})
    for b in ("quill0", "quill1", "nape"):
        k.rot(b, {**shake(0.1, 0.6, (8, 0, 0), freq=6, decay=4), 1.0: (0, 0, 0)})
    for p in ("r", "l"):
        k.scale(f"{p}_nict", {0: 1, 0.45: 1, 0.6: (1, 1, 20), 0.75: (1, 1, 20), 0.95: 1, 1.0: 1})
    k.particle(0.25, "displaymotes", "throat")
    return k.anim()


def _out(side: int, e):
    """z-rotation that swings a part hanging at this side outward (+ for the right side)."""
    return mirror(side, e)


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    for p in ("r", "l"):                          # the folded wing and the spike stay out of the first-person view
        for b in (f"{p}_plume0", f"{p}_plume1", f"{p}_stylus"):
            fp.bone(b, scale=0)

    # ------------------------------------------------------------------ look: the neck carries the head
    look = Layer(r, "look", loop=True)
    look.rot("head_g", f"-{LX}", None, None)       # cancel the player's look exactly (pitch here, yaw on hfix) ...
    look.rot("hfix", None, f"-{LY}", None)
    look.rot("neck", f"{LX} * 0.42", f"{LY} * 0.55", None)     # ... and re-apply it on the neck and skull
    look.rot("skull", f"{LX} * 0.38", f"{LY} * 0.38", None)

    # ------------------------------------------------------------------ life: breath, throat, membranes, tail, drift
    life = Layer(r, "life", loop=True)
    br = S(0.22)                                   # slow, deep breaths (4.5 s)
    life.scale("trunk", None, lin([(1, 1), (0.012, br)]), lin([(1, 1), (0.022, br)]))
    life.rot("neck", mul(-0.8, br), None, None)
    # the throat fills and empties with the breath, with a fine flutter every few seconds
    flutter = prod(BUMP(6.3, 1.1), f"math.sin({T} * 2700)")
    life.scale("gular", lin([(1, 1), (0.05, S(0.22, -60))]), lin([(1, 1), (0.1, S(0.22, -60)), (0.06, flutter)]),
               lin([(1, 1), (0.06, S(0.22, -60))]))
    # rare sweeps of the nictitating membrane (long unblinking stares), shut while asleep
    for p, side in SIDES:
        life.scale(f"{p}_nict", None, None, lin([(1, 1), (19, f"math.max({blink(13.7, 21.1, 0.32, 6.0)}, {SLEEP})")]))
        life.scale(f"{p}_pupil", None, None, lin([(1, 1), (-0.45, TOOTHED), (0.1, S(0.031, 40))]))
    # membranes twitch on their own clock; the folded strips open a little when Webbed
    for p, side in SIDES:
        sg = 1 if side < 0 else -1
        for j, (per, off) in enumerate(((5.3, 0.0), (7.9, 2.1))):
            tw = BUMP(per, 0.22, off + (0 if side < 0 else 1.3))
            life.rot(f"{p}_sail{j}", mul(4, tw), None, mul(sg, lin([(9, tw), (12, WEBBED)])))
            life.scale(f"{p}_sail{j}", None, None, lin([(1, 1), (0.6, WEBBED)]))
        life.rot(f"{p}_stylus", None, None, mul(sg, mul(6, BUMP(9.1, 0.25, 4.0 + side))))
        # Plumed: tufts and the arm's feathers grow longer and fuller
        life.scale(f"{p}_tuft", None, lin([(1, 1), (0.22, PLUMED)]), lin([(1, 1), (0.35, PLUMED)]))
        life.rot(f"{p}_tuft", mul(3, S(0.13, 30 if side < 0 else 200)), None, None)
        for b in (f"{p}_plume0", f"{p}_plume1"):
            life.scale(b, None, lin([(1, 1), (0.14, PLUMED)]), lin([(1, 1), (0.2, PLUMED)]))
        # Fanned: the tail fan spreads
        life.rot(f"{p}_fan", None, mirror(side, mul(-26, FANNED)), None)
    life.scale("fan", lin([(1, 1), (0.08, FANNED)]), 1, lin([(1, 1), (0.1, FANNED)]))
    # Toothed: the jaw drops a little and the teeth are bared
    life.rot("jaw", lin([(5.5, TOOTHED), (1.0, S(0.09, 70))]), None, None)
    life.pos("teeth", None, mul(-0.3, TOOTHED), None)
    # the crest tilts on a slow clock of its own (90 s)
    life.rot("crest0", mul(3.0, S(1 / 90.0, 20)), None, None)
    # tail balance: a slow independent sway, heavier at the base
    chain_wave(life, TAILB, "y", 2.2, 0.11, lag=35, falloff=1.12)
    chain_wave(life, TAILB, "x", 0.9, 0.07, lag=40, falloff=1.1, phase=90)
    for k, b in enumerate(TAILB):
        life.rot(b, prod(SLEEP, -4 if k else -10), None, None)
    for k in (0, 1):
        life.rot(f"bristle{k}", mul(2.0, S(0.22, -40 - 30 * k)), None, None)

    # ------------------------------------------------------------------ locomotion: a theropod's stride
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    ws = prod(WALKING, s)
    stride(loco, lin([(0.55, WALKING), (0.72, SPR)]))
    arm_swing(loco, 0.18)                         # the arms barely swing
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        sw = f"math.max(0, {-sg} * math.sin({PH}))"             # this leg is swinging forward
        push = f"math.max(0, {sg} * math.sin({PH}))"            # this leg is pushing back
        knee = prod(sw, lin([(34, ws), (52, ss)]))
        loco.rot(f"{p}_shin", knee)
        loco.rot(f"{p}_meta", lin([(-0.7, knee), (-12, prod(push, s))]))
        loco.rot(f"{p}_foot", lin([(0.45, knee), (14, prod(push, s))]))
        loco.rot(f"{p}_talon", prod(-10, sw, s))
        # the metatarsal fan folds up during the swing; half-open hindwings at a sprint
        loco.rot(f"{p}_lfan0", prod(18, sw, s))
        loco.rot(f"{p}_lfan1", prod(14, sw, s))
        loco.rot(f"{p}_sfan", prod(10, sw, s))
        e = EMPTY_R if side < 0 else EMPTY_L
        loco.rot(f"{p}_arm_g", prod(-14, ss, e), None, None)   # running, the empty hands tuck up
        loco.rot(f"{p}_plume1", prod(-6, ss), mirror(side, prod(-10, ss)), None)
    body(loco, rig, lean=lin([(5, s), (11, ss)]), twist=lin([(-6, prod(f"math.cos({PH})", s)), (0.1, LY)]))
    loco.rot("trunk", None, None, prod(2.2, f"math.sin({PH})", ws))      # a little roll toward the stance leg
    # the head stays level while the body leans, and is thrust forward step by step (walking only)
    step = f"math.mod({PH} * 2, 360) / 360"
    bob = f"({step} < 0.22 ? 1 - {step} * 4.545 : ({step} - 0.22) * 1.282)"
    loco.rot("skull", lin([(-5, s), (-11, ss)]), None, None)
    loco.pos("skull", None, None, lin([(1.1, prod(bob, ws)), (-0.55, ws)]))
    loco.rot("neck", lin([(4, ss)]), None, None)
    # the tail counter-swings at a walk and streamlines (straight, raised) at a run
    amp = lin([(1.0, 1.0), (-0.65, SPR)])
    for k, b in enumerate(TAILB):
        loco.rot(b, lin([(5 if k == 0 else -1.5, ss), (1.2, prod(f"math.sin({PH} * 2 - {60 + 30 * k})", s))]),
                 lin([(3.0 + 1.5 * k, prod(f"math.cos({PH} - {50 + 35 * k})", s, amp)), (-4.0 - 1.5 * k, prod(TURN, s))]),
                 None)
    for k in (0, 1):
        loco.rot(f"bristle{k}", lin([(-10, ss)]), None, None)
    for p, side in SIDES:
        loco.rot(f"{p}_fan", None, mirror(side, mul(-14, ss)), None)
        loco.rot(f"{p}_tuft", lin([(-6, s)]), mirror(side, mul(-6, ss)), None)
    grounded(model, loco, rig, r, harmonics=8)
    # running, the folded hindwings half open (the folded forms only: in the veer they are already open)
    halfwing = Layer(r, "hindwing_run", loop=True)
    for p, side in SIDES:
        halfwing.rot(f"{p}_lfan0", None, None, _out(side, mul(26, ss)))
        halfwing.rot(f"{p}_lfan1", None, None, _out(side, mul(36, ss)))
        halfwing.rot(f"{p}_sfan", None, None, _out(side, mul(24, ss)))
        for j in (0, 1):
            halfwing.rot(f"{p}_sail{j}", None, None, _out(side, mul(26, ss)))
            halfwing.scale(f"{p}_sail{j}", None, None, lin([(1, 1), (0.9, ss)]))

    # ------------------------------------------------------------------ airborne: the feathers adjust
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        air.rot(f"{p}_thigh", lin([(-26, RISE), (-12, FALL)]))
        air.rot(f"{p}_shin", lin([(44, RISE), (14, FALL)]))
        air.rot(f"{p}_meta", lin([(-24, RISE), (-6, FALL)]))
        air.rot(f"{p}_foot", lin([(30, RISE), (-8, FALL)]))
        air.rot(f"{p}_lfan0", None, None, _out(side, lin([(14, RISE), (40, FALL)])))
        air.rot(f"{p}_lfan1", None, None, _out(side, lin([(18, RISE), (52, FALL)])))
        air.rot(f"{p}_sfan", None, None, _out(side, lin([(10, RISE), (34, FALL)])))
        for j in (0, 1):
            air.rot(f"{p}_sail{j}", None, None, _out(side, lin([(10, RISE), (30, FALL)])))
        air.rot(f"{p}_plume1", lin([(-8, FALL)]), mirror(side, lin([(-12, RISE), (-30, FALL)])), None)
        air.rot(f"{p}_fan", None, mirror(side, mul(-22, FALL)), None)
    air.rot("tail0", lin([(-8, RISE), (10, FALL)]))
    air.rot("tail2", lin([(-4, RISE), (5, FALL)]))
    body(air, rig, lean=lin([(-4, RISE), (6, FALL)]))
    air.rot("skull", lin([(4, RISE), (-6, FALL)]))

    land = KeyLayer(r, "land", 0.5)
    land_hard = KeyLayer(r, "land_hard", 0.8)
    for kl, g in ((land, 0.6), (land_hard, 1.0)):
        L = kl.length
        t1, t2 = 0.1 * (1 + g * 0.3), 0.3 + 0.2 * g
        body_keys(kl, rig, {0: {"bob": -1.3 * g, "lean": 7 * g}, t1: {"bob": -1.8 * g, "lean": 9 * g},
                            t2: {"bob": 0.2, "lean": -1}, L: {}})
        for p, side in SIDES:
            kl.rot(f"{p}_thigh", {0: (-18 * g, 0, 0), t1: (-24 * g, 0, 0), t2: (-2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_shin", {0: (30 * g, 0, 0), t1: (40 * g, 0, 0), t2: (3, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_meta", {0: (-12 * g, 0, 0), t1: (-16 * g, 0, 0), t2: (-1, 0, 0), L: (0, 0, 0)})
            sg = 1 if side < 0 else -1
            for j in (0, 1):
                kl.rot(f"{p}_sail{j}", {0: (0, 0, 0), 0.06: (0, 0, sg * 22 * g), t2: (0, 0, sg * -3), L: (0, 0, 0)})
            kl.rot(f"{p}_lfan1", {0: (0, 0, 0), 0.08: (-10 * g, 0, sg * 26 * g), t2: (0, 0, 0), L: (0, 0, 0)})
        kl.rot("tail0", {0: (-12 * g, 0, 0), t1: (-16 * g, 0, 0), t2: (5, 0, 0), L: (0, 0, 0)})
        kl.rot("tail3", {0: (0, 0, 0), t1 + 0.05: (-8 * g, 0, 0), t2 + 0.1: (4, 0, 0), L: (0, 0, 0)})
        kl.rot("skull", {0: (6 * g, 0, 0), t1: (-4 * g, 0, 0), t2: (1, 0, 0), L: (0, 0, 0)})
        kl.scale("gular", {0: 1, t1: (1.1, 1.3, 1.1), t2: 1, L: 1})
        kl.particle(0.0, "stepdust", "r_sickle").particle(0.0, "stepdust", "l_sickle")
    land_hard.particle(0.05, "feathers", "chest")

    # ------------------------------------------------------------------ attack: a raking strike, the talon flicks
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(5, ATK), twist=prod(-9, ATK))
    atk.rot("r_hand", prod(-34, ATK))
    atk.rot("r_stylus", None, None, prod(28, ATK2))
    atk.rot("r_plume1", None, prod(-34, ATK), None)
    atk.rot("skull", prod(9, ATK), prod(-6, ATK), None)
    atk.pos("skull", None, None, prod(-1.0, ATK))
    atk.rot("jaw", prod(14, ATK))
    atk.rot("r_talon", prod(-38, ATK))
    atk.rot("tail2", None, prod(10, ATK2), None)
    atk.rot("tail4", None, prod(14, ATK2), None)

    # ------------------------------------------------------------------ hurt: a recoil, a frozen beat, then it turns back to look
    hurt = KeyLayer(r, "hurt", 1.0)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -7, "roll": 3}, 0.2: {"lean": -5, "roll": 2}, 0.55: {"lean": -4},
                          0.85: {"lean": 1}, 1.0: {}})
    hurt.rot("neck", {0: (0, 0, 0), 0.05: (-16, -7, 0), 0.55: (-13, -6, 0), 0.85: (2, 0, 0), 1.0: (0, 0, 0)})
    hurt.rot("skull", {0: (0, 0, 0), 0.05: (-10, -10, -7), 0.55: (-8, -9, -6), 0.85: (3, 1, 0), 1.0: (0, 0, 0)})
    for b, a_ in (("quill0", 46), ("quill1", 40), ("nape", 34), ("bristle0", 30), ("bristle1", 26)):
        hurt.rot(b, {0: (0, 0, 0), 0.06: (a_, 0, 0), 0.5: (a_ * 0.8, 0, 0), 0.9: (0, 0, 0), 1.0: (0, 0, 0)})
    hurt.scale("gular", {0: 1, 0.07: (1.25, 1.6, 1.25), 0.4: (1.1, 1.25, 1.1), 0.8: 1, 1.0: 1})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.scale(f"{p}_nict", {0: 1, 0.04: (1, 1, 20), 0.18: (1, 1, 20), 0.3: 1, 1.0: 1})
        hurt.scale(f"{p}_pupil", {0: 1, 0.6: 1, 0.75: (1, 1, 0.45), 1.0: 1})
        hurt.rot(f"{p}_tuft", {0: (0, 0, 0), 0.06: (-24, -sg * 18, 0), 0.6: (-18, -sg * 12, 0), 1.0: (0, 0, 0)})
        hurt.rot(f"{p}_plume1", {0: (0, 0, 0), 0.06: (-12, sg * 26, 0), 0.5: (-8, sg * 16, 0), 0.9: (0, 0, 0)})
    hurt.rot("tail1", {0: (0, 0, 0), 0.06: (6, 14, 0), 0.25: (0, -9, 0), 0.5: (0, 4, 0), 0.8: (0, 0, 0)})
    hurt.particle(0.0, "feathers", "chest")

    # ------------------------------------------------------------------ swimming: tail-driven, feathers sleeked back
    swim = Layer(r, "swim", loop=True)
    swim.kw["length"] = 2.0
    swim.rot("tail0", prod(-68, SWIM), mul(9, S(0.9)), None)
    for k in range(1, D.TAIL):
        swim.rot(f"tail{k}", None, mul(9 + 4 * k, S(0.9, -45 * k)), None)
    for p, side in SIDES:
        ph = 0 if side < 0 else 180
        swim.rot(f"{p}_thigh", mul(28, S(0.9, ph)), None, None)
        swim.rot(f"{p}_shin", lin([(24, 1), (20, S(0.9, ph + 70))]), None, None)
        swim.rot(f"{p}_meta", mul(-14, S(0.9, ph + 120)), None, None)
        for b in (f"{p}_lfan0", f"{p}_lfan1", f"{p}_sfan"):
            swim.rot(b, 16, None, None)
        swim.rot(f"{p}_plume1", -10, None, None)
        swim.rot(f"{p}_tuft", 14, None, None)
    swim.rot("neck", -18, None, None)
    swim.rot("skull", 16, None, None)

    # ------------------------------------------------------------------ idle behaviours
    def wait(name, length):
        """Waiting between behaviours: the head darts to a new bearing and holds (bird-like)."""
        w = Layer(r, name, loop=False, length=length)
        w.rot("skull", mul(1.0, dart(0.37, 10, seed=3.1)), mul(1.0, dart(0.29, 26, seed=7.3)), mul(1.0, dart(0.21, 9, seed=5.5)))
        w.rot("neck", mul(1.0, dart(0.17, 5, seed=2.2)), mul(1.0, dart(0.13, 12, seed=9.4)), None)
        return w

    fid = []
    stare = KeyLayer(r, "fidget_stare", 6.0)         # a long, unsettling stare: pupils narrow to threads, one sweep of the membrane
    stare.rot("neck", {0: (0, 0, 0), 0.12: (3, 0, 0), 5.3: (4, 0, 0), 6.0: (0, 0, 0)})
    stare.rot("skull", {0: (0, 0, 0), 0.08: (-3, 0, 0), 5.3: (-3, 0, 0), 6.0: (0, 0, 0)})
    stare.pos("skull", {0: (0, 0, 0), 0.5: (0, 0, -0.5), 2.5: (0, 0, -0.8), 5.3: (0, 0, -0.8), 6.0: (0, 0, 0)})
    for p in ("r", "l"):
        stare.scale(f"{p}_pupil", {0: 1, 0.6: 1, 2.6: (1, 1, 0.3), 4.6: (1, 1, 0.3), 5.6: 1, 6.0: 1})
        stare.scale(f"{p}_nict", {0: 1, 4.7: 1, 4.95: (1, 1, 20), 5.15: (1, 1, 20), 5.45: 1, 6.0: 1})
    body_keys(stare, rig, {0: {}, 1.0: {"lean": 3}, 5.3: {"lean": 3}, 6.0: {}})
    fid.append(stare)
    pouch = KeyLayer(r, "fidget_pouch", 3.6)         # three slow pulses of the throat pouch, head raised
    pouch.scale("gular", {0: 1, 0.5: (1.25, 1.7, 1.25), 0.9: (1.08, 1.15, 1.08), 1.4: (1.3, 1.8, 1.3), 1.8: (1.08, 1.15, 1.08),
                          2.4: (1.35, 1.95, 1.35), 3.1: 1, 3.6: 1})
    pouch.rot("neck", {0: (0, 0, 0), 0.4: (-9, 0, 0), 2.8: (-9, 0, 0), 3.4: (0, 0, 0)})
    pouch.rot("skull", {0: (0, 0, 0), 0.4: (-6, 0, 0), 2.8: (-6, 0, 0), 3.4: (0, 0, 0)})
    pouch.rot("crest0", {0: (0, 0, 0), 0.5: (6, 0, 0), 2.8: (6, 0, 0), 3.4: (0, 0, 0)})
    pouch.rot("jaw", {0: (0, 0, 0), 0.5: (5, 0, 0), 2.6: (5, 0, 0), 3.1: (0, 0, 0)})
    for p in ("r", "l"):
        pouch.rot(f"{p}_tuft", {0: (0, 0, 0), 0.5: (10, 0, 0), 2.8: (10, 0, 0), 3.4: (0, 0, 0)})
    pouch.particle(2.4, "displaymotes", "throat")
    fid.append(pouch)
    preen = KeyLayer(r, "fidget_preen", 4.2)         # the tail curls round; the beak combs through the opened fan
    preen.rot("neck", {0: (0, 0, 0), 0.6: (14, 52, 0), 3.3: (14, 52, 0), 4.0: (0, 0, 0)})
    preen.rot("skull", {0: (0, 0, 0), 0.6: (22, 40, -8), 1.2: (30, 40, -8), 1.5: (20, 40, -8), 1.8: (30, 40, -8), 2.1: (20, 40, -8),
                        2.4: (30, 40, -8), 3.3: (22, 40, -8), 4.0: (0, 0, 0)})
    for k, a_ in enumerate((10, 14, 18, 20, 18)):
        preen.rot(f"tail{k}", {0: (0, 0, 0), 0.7: (2, -a_, 0), 3.2: (2, -a_, 0), 4.0: (0, 0, 0)})
    preen.rot("r_fan", {0: (0, 0, 0), 0.9: (0, -36, 0), 3.0: (0, -36, 0), 3.3: (0, 0, 0)})
    preen.rot("l_fan", {0: (0, 0, 0), 0.9: (0, 36, 0), 3.0: (0, 36, 0), 3.3: (0, 0, 0)})
    body_keys(preen, rig, {0: {}, 0.6: {"twist": -8}, 3.3: {"twist": -8}, 4.0: {}})
    preen.particle(1.9, "feathers", "tail_fan")
    fid.append(preen)
    study = KeyLayer(r, "fidget_study", 4.4)         # a slow head tilt, studying ... then a snap to the other side
    study.rot("skull", {0: (0, 0, 0), 1.3: (2, 6, 26), 2.3: (2, 6, 26), 2.38: (0, -4, -20), 3.6: (0, -4, -20), 4.4: (0, 0, 0)})
    study.rot("neck", {0: (0, 0, 0), 1.3: (5, 0, 0), 3.6: (5, 0, 0), 4.4: (0, 0, 0)})
    study.pos("skull", {0: (0, 0, 0), 1.3: (0, 0, -0.6), 3.6: (0, 0, -0.6), 4.4: (0, 0, 0)})
    for p in ("r", "l"):
        study.scale(f"{p}_pupil", {0: 1, 1.3: (1, 1, 1.35), 2.3: (1, 1, 1.35), 2.38: (1, 1, 0.6), 3.6: (1, 1, 0.6), 4.4: 1})
    fid.append(study)
    picks = [("fidget_stare", "math.mod(math.floor(q.life_time * 1.3), 5) == 0"),
             ("fidget_pouch", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_preen", "math.mod(math.floor(q.life_time * 1.3), 5) == 2"),
             ("fidget_study", "math.mod(math.floor(q.life_time * 1.3), 5) == 3")]

    # ------------------------------------------------------------------ forms
    tl = {b: (0.3 + 0.07 * k, 0.4) for k, b in enumerate(TAILB)}
    disp_order = {"quill0": (0.0, 0.22), "quill1": (0.05, 0.22), "nape": (0.0, 0.2), "bristle0": (0.08, 0.22),
                  "bristle1": (0.12, 0.22), "crest0": (0.15, 0.35), "crest1": (0.25, 0.3), "skull": (0.1, 0.3),
                  "r_tuft": (0.2, 0.25), "l_tuft": (0.22, 0.25), "jaw": (0.3, 0.2),
                  "r_plume0": (0.3, 0.35), "l_plume0": (0.32, 0.35), "r_plume1": (0.35, 0.38), "l_plume1": (0.37, 0.38),
                  "r_stylus": (0.42, 0.3), "l_stylus": (0.44, 0.3), "fan": (0.55, 0.3), "r_fan": (0.62, 0.25),
                  "l_fan": (0.62, 0.25), **tl}
    veer_order = {"trunk": (0.0, 0.18), "neck": (0.0, 0.18), "r_arm_g": (0.0, 0.18), "l_arm_g": (0.0, 0.18),
                  "r_sail0": (0.04, 0.16), "l_sail0": (0.04, 0.16), "r_sail1": (0.07, 0.16), "l_sail1": (0.07, 0.16),
                  "r_sfan": (0.08, 0.16), "l_sfan": (0.08, 0.16), "r_lfan0": (0.1, 0.16), "l_lfan0": (0.1, 0.16),
                  "r_lfan1": (0.12, 0.18), "l_lfan1": (0.12, 0.18), "fan": (0.1, 0.18), "r_fan": (0.15, 0.15),
                  "l_fan": (0.15, 0.15)}
    over_order = {b: (st * 1.4, du * 1.6) for b, (st, du) in disp_order.items()}
    over_order.update({b: (0.55 + st * 2.0, du * 2.0) for b, (st, du) in veer_order.items() if b.startswith(("r_s", "l_s", "r_l", "l_l"))})
    intro = {
        "base": unfold(model, "intro_base", "overflow", "base", 0.8, {}, k=0.35),
        "night": _wake(r),
        "display": unfold(model, "intro_display", "base", "display", 1.0, disp_order, grow={"gular": (0.25, 0.45, 0.45)}),
        "veer": unfold(model, "intro_veer", "base", "veer", 0.36, veer_order, overshoot=0.05,
                       grow={f"{p}_sail{j}": (0.04 + 0.03 * j, 0.18, (1, 1, 0.2)) for p in ("r", "l") for j in (0, 1)}),
        "overflow": unfold(model, "intro_overflow", "base", "overflow", 1.6, over_order,
                           grow={"gular": (0.4, 0.6, 0.4),
                                 **{f"{p}_sail{j}": (0.62 + 0.06 * j, 0.36, (1, 1, 0.2)) for p in ("r", "l") for j in (0, 1)}}),
    }
    intro["display"].particle(0.3, "displaymotes", "throat").particle(0.5, "displaymotes", "crest_tip")
    intro["veer"].particle(0.05, "feathers", "tail_fan")
    intro["overflow"].particle(0.2, "displaymotes", "eyes").particle(0.6, "displaymotes", "throat") \
        .particle(1.0, "displaymotes", "crest_tip").particle(1.2, "feathers", "tail_fan")

    # display: the pouch throbs, every fan shivers (a train-rattle), the head sways slowly, high
    disp = Layer(r, "display_loop", loop=True)
    disp.scale("gular", lin([(1, 1), (0.07, S(1.1))]), lin([(1, 1), (0.1, S(1.1))]), lin([(1, 1), (0.07, S(1.1))]))
    rattle = f"math.sin({T} * 6400)"
    for p, side in SIDES:
        disp.rot(f"{p}_plume1", mul(1.6, rattle), None, mul(1.2, rattle))
        disp.rot(f"{p}_plume0", mul(1.2, rattle), None, None)
        disp.rot(f"{p}_stylus", None, None, mirror(side, mul(4, S(0.6, 0 if side < 0 else 90))))
        disp.rot(f"{p}_fan", None, mul(1.5, rattle), None)
    disp.rot("fan", mul(1.5, rattle), None, None)
    disp.rot("neck", None, mul(9, S(0.35)), mul(3, S(0.35, 90)))
    disp.rot("crest1", mul(2, S(1.7)), None, None)
    for b in ("quill0", "quill1", "nape", "bristle0", "bristle1"):
        disp.rot(b, mul(2.5, S(2.3, len(b) * 40)), None, None)

    # veer: membranes flutter in the airflow, the fan steers as a rudder
    veer = Layer(r, "veer_loop", loop=True)
    for p, side in SIDES:
        for j in (0, 1):
            veer.rot(f"{p}_sail{j}", mul(2, S(4.7, j * 60)), None, _out(side, mul(3, S(5.3, j * 90 + (0 if side < 0 else 40)))))
        veer.rot(f"{p}_lfan1", None, None, _out(side, mul(4, S(4.1, 30))))
        veer.rot(f"{p}_sfan", None, None, _out(side, mul(3, S(3.7, 70))))
    veer.rot("fan", None, mul(8, S(0.7)), mul(6, S(0.7, 90)))
    veer.rot("skull", mul(-3, S(0.5)), None, None)

    # overflow: every structure on its own clock at once - the four drift configurations together
    over = Layer(r, "overflow_loop", loop=True)
    over.scale("gular", lin([(1, 1), (0.1, S(0.9))]), lin([(1, 1), (0.16, S(0.9))]), lin([(1, 1), (0.1, S(0.9))]))
    over.rot("crest0", mul(5, S(0.31)), None, None)
    over.rot("crest1", mul(4, S(0.47, 60)), None, None)
    over.rot("jaw", lin([(6, 1), (4, S(0.73))]), None, None)
    over.pos("teeth", None, -0.3, None)
    for p, side in SIDES:
        sg = 1 if side < 0 else -1
        over.scale(f"{p}_pupil", None, None, lin([(1, 1), (0.45, S(0.66, 0 if side < 0 else 110))]))
        over.scale(f"{p}_tuft", None, 1.2, 1.35)
        over.rot(f"{p}_tuft", mul(6, S(0.41, 40)), None, None)
        for j in (0, 1):
            over.rot(f"{p}_sail{j}", None, None, mul(sg, mul(7, S(0.52, j * 70 + (0 if side < 0 else 30)))))
        over.rot(f"{p}_plume1", None, mirror(side, mul(8, S(0.37, 20))), None)
        over.rot(f"{p}_lfan1", None, None, mul(sg, mul(6, S(0.44, 50))))
        over.rot(f"{p}_fan", None, mirror(side, mul(-8, S(0.4, 10))), None)
    for k, b in enumerate(("nape", "quill0", "quill1", "bristle0", "bristle1")):
        over.rot(b, mul(6, S(0.8, -55 * k)), None, None)
    over.rot("skull", mul(4, S(0.13)), mul(1.0, dart(0.5, 14, seed=4.4)), lin([(1.0, dart(0.23, 10, seed=8.1)), (5, S(0.11))]))

    fx = {
        "base": A(r, "fx_base", length=16.0).particle(0.0, "feathers", "tail_fan"),
        "night": A(r, "fx_night", length=5.0).particle(0.0, "displaymotes", "throat").particle(2.5, "displaymotes", "crest_tip"),
        "display": A(r, "fx_display", length=0.8).particle(0.0, "displaymotes", "crest_tip").particle(0.4, "displaymotes", "throat"),
        "veer": A(r, "fx_veer", length=0.3).particle(0.0, "feathers", "r_sickle").particle(0.15, "feathers", "l_sickle"),
        "overflow": A(r, "fx_overflow", length=1.2).particle(0.0, "displaymotes", "eyes").particle(0.4, "displaymotes", "throat")
        .particle(0.8, "displaymotes", "crest_tip"),
    }
    built = [fp, tp, look.anim(), life.anim(), loco.anim(), halfwing.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), swim.anim(), disp.anim(), veer.anim(), over.anim(), wait("fidget_wait", 7.0).anim(),
             wait("fidget_rest", 3.5).anim(), *[f.anim() for f in fid], *intro.values(), *fx.values()]
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
