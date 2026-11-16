"""Race 008 Bathyas, the Sun-Impaled (Unique) - attachable animation set.

Motion language: an exhausted, irritable old man.  Everything is heavy and late: a slow
5 s breath that lifts the whole dorsal hump, gills that flutter on every exhale, lids that
hang half closed and sag further in long sleepy rests, little irritated twitches of the brow
and head, uneven shoulders.  The sun in his chest beats like a heart (lub-dub, ~52 bpm):
both wound shells flare and the hilt knocks once per beat.  He walks heavily and unevenly
(the right step lands harder), the tergites jostle a beat after each footfall and the torn
fins drag behind; sprinting he drops low and predatory, head forward.  With the sword drawn
he goes quiet: lids open, head still, faster shallow breaths, nothing else moves.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from anims.core import NS, T
from anims.life import (ATK, CSTEP, EMPTY_L, EMPTY_R, FALL, LOOK, MOVE, PH, POS, RISE, S, SPR, STEP, STILL, TCOS, TURN,
                        KeyLayer, Layer, Rig, arm_swing, body, body_keys, dart, fidget_controller, landing_controller,
                        lin, mul, prod, shared, stride, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, grounded, heartbeat, mirror, pre_animation, shake, view_anims
from models.bathyas import _D, CROUCH, PLATES

R = "bathyas"
RIG = Rig("trunk", (0, 12, 0), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"
FREE_R = "(q.is_item_equipped(0) ? 0 : 1)"
FREE_L = "(q.is_item_equipped(1) ? 0 : 1)"
NPLATES = len(PLATES)
BEAT = 1.15                                   # s per heartbeat (~52 bpm): old, tired
BEAT_HUNT = 0.78                              # with the sword drawn (~77 bpm)
BREATH = 0.19                                 # Hz: a slow, tired 5 s breath
SLEEP = "q.is_sleeping"
# the swing arriving later down the arm (forearm, fingers) and in the jaw
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.3 - 0.15, 0, 1) * 180)"
# right / left footfall spikes (the right foot lands at phase 180, the left at 0)
STRIKE_R = f"math.pow(math.max(0, -math.cos({PH})), 8)"
STRIKE_L = f"math.pow(math.max(0, math.cos({PH})), 8)"


def _r3(v):
    return [round(float(x), 3) + 0.0 for x in v]


def stagger(model, name: str, frm: str, to: str, length: float, order: Dict[str, tuple], over: float = -0.08):
    """Transition from the `frm` pose into the `to` pose with per-bone timing (start, duration)
    and a small overshoot; bones without an entry move together over 70% of the length."""
    a = A(R, name, loop="hold", length=length)
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        b = model.bones[bn]
        dr = np.array(model.bone_rot(bn, frm), float) - np.array(model.bone_rot(bn, to), float)
        t_from = np.array(b.variant[frm][0], float) if frm in b.variant else np.zeros(3)
        t_to = np.array(b.variant[to][0], float) if to in b.variant else np.zeros(3)
        dt = t_from - t_to
        if np.allclose(dr, 0, atol=0.01) and np.allclose(dt, 0, atol=0.01):
            continue
        st, du = order.get(bn, (0.0, length * 0.7))
        keys = {0.0: 1.0, st: 1.0, st + du * 0.75: over, st + du: 0.0, length: 0.0}
        rot = None if np.allclose(dr, 0, atol=0.01) else {t: _r3(dr * k) for t, k in keys.items()}
        pos = None if np.allclose(dt, 0, atol=0.01) else {t: _r3(dt * k) for t, k in keys.items()}
        a.bone(bn, rot=rot, pos=pos)
    return a


def _merge(anim, bone: str, ch: str, keys: Dict[float, list]):
    """Add keyframes onto a channel that a stagger may already animate (both linear)."""
    prev = anim.bones.get(bone, {}).get(ch)
    if not isinstance(prev, dict):
        anim.bone(bone, **{{"rotation": "rot", "position": "pos", "scale": "scale"}[ch]: keys})
        return
    pts = sorted((float(k), np.array(v, float)) for k, v in prev.items())
    kp = sorted((float(k), np.array(v, float)) for k, v in keys.items())

    def at(seq, t):
        if t <= seq[0][0]:
            return seq[0][1]
        for (t0, v0), (t1, v1) in zip(seq, seq[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * ((t - t0) / max(t1 - t0, 1e-9))
        return seq[-1][1]
    times = sorted({t for t, _ in pts} | {t for t, _ in kp})
    merged = {t: _r3(at(pts, t) + at(kp, t)) for t in times}
    anim.bone(bone, **{{"rotation": "rot", "position": "pos", "scale": "scale"}[ch]: merged})


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    plates = [f"plate{k}" for k in range(NPLATES)]
    hb = heartbeat(BEAT)
    hb_h = heartbeat(BEAT_HUNT)
    br = S(BREATH)                                   # + inhaling
    droop = shared("math.clamp(math.sin(q.life_time * 32.73 + 100) * 3 - 2, 0, 1)", "plr_bl")  # ~3 s sleepy rests / 11 s

    # ------------------------------------------------------------------ life: tired breath, the beating sun, heavy lids
    life = Layer(r, "life", loop=True)
    body(life, rig, lean=shared(f"2 * {droop} * {STILL} - 0.8 * {br}", "plr_bl"),
         roll=shared(f"1.6 + 0.6 * {S(0.07)}", "plr_bl"), twist=shared(f"1.2 * {S(0.05, 40)} * {STILL}", "plr_bl"))
    life.rot("chest", lin([(-1.4, br), (0.5, hb)]))                     # the hump rises with each breath; the beat knocks
    for k, pl in enumerate(plates):                                       # the back expands, a little late plate by plate
        life.pos(pl, None, mul(0.08, S(BREATH, -20 * k)), mul(0.16, S(BREATH, -20 * k)))
    for arm in ("r_arm_g", "l_arm_g"):
        life.pos(arm, None, mul(0.22, S(BREATH, -15)))
    life.pos("head_g", None, lin([(0.12, S(BREATH, -40)), (-0.5, prod(droop, STILL))]))
    # the head: a hunched neck takes a third of the look pitch; slow sour glances; an irritated shake now and then
    shake_h = f"(math.mod({T}, 13.7) < 0.5 ? math.sin(math.mod({T}, 13.7) * 1440) * 4 : 0)"
    life.rot("head_g", lin([(-0.33, "math.clamp(q.target_x_rotation, -50, 60)"), (5.0, prod(droop, STILL)),
                            (1.5, S(0.09, 30))]),
             prod(lin([(1.0, dart(0.11, 9, seed=2.0)), (1.0, shake_h)]), STILL), mul(2.2, S(0.06)))
    life.uscale("core_f", lin([(1, 1), (0.34, hb)]))                    # the light shells beat like a heart
    life.uscale("core_b", lin([(1, 1), (0.28, heartbeat(BEAT).replace(T, f"({T} - 0.06)"))]))
    life.rot("sword", lin([(0.9, hb)]), None, None)                      # the hilt knocks once per beat
    # heavy lids: half closed at rest, sagging in long rests, blinking slowly, shut in sleep
    for p, side in SIDES:
        bl = blink(6.1 if side < 0 else 6.4, 9.7, 0.24, 2.3 if side < 0 else 2.45)
        base = 1.12 if side < 0 else 1.0                               # one lid always lower
        life.scale(f"lid_{p}", None, f"math.min(2.1, {base} + 0.55 * {droop} + math.max({bl}, {SLEEP}))", None)
        sg = -1 if side < 0 else 1
        twitch = f"(math.mod({T} + {1.3 if side < 0 else 0}, 7.3) < 0.3 ? 1 : 0)"
        life.rot(f"brow_{p}", None, None, mirror(side, lin([(7.0, twitch), (2.0, S(0.13, 50))])))
        for k in range(3):                                              # gills flutter on every exhale
            ex = f"math.max(0, -{S(BREATH, -30 - 25 * k)})"
            life.rot(f"gill_{p}{k}", None, mul(sg, lin([(6.0, 1), (10.0, ex), (3.0, S(1.7, k * 70))])), None)
        life.rot(f"{p}_fin", lin([(2.0, S(0.21, 40 if side < 0 else 130))]), None, mirror(side, mul(2.5, S(0.17, 80))))
        for k in range(3):                                              # fingers stir now and then
            life.rot(f"{p}_finger{k}", lin([(3.0, S(0.23, k * 60 + (0 if side < 0 else 90)))]), None, None)
    grumble = f"(math.mod({T} + 4.0, 9.1) < 1.4 ? 1 : 0)"               # an old man muttering to himself
    life.rot("jaw", lin([(1.0, 1), (5.0, prod(grumble, f"math.max(0, {S(2.6)})")), (6.0, prod(droop, STILL))]))
    life.pos("jaws", None, None, mul(-0.25, prod(grumble, f"math.max(0, {S(1.3)})")))

    # with the sword drawn: only breath and the racing heart (lids open, head steady)
    hunt = Layer(r, "life_hunt", loop=True)
    brh = S(0.32)
    hunt.rot("chest", lin([(-0.8, brh), (0.4, hb_h)]))
    for k, pl in enumerate(plates):
        hunt.pos(pl, None, None, mul(0.1, S(0.32, -25 * k)))
    for arm in ("r_arm_g", "l_arm_g"):
        hunt.pos(arm, None, mul(0.15, S(0.32, -15)))
    hunt.rot("head_g", lin([(-0.33, "math.clamp(q.target_x_rotation, -50, 60)")]), None, None)
    hunt.uscale("core_f", lin([(1, 1), (0.42, hb_h)]))
    hunt.uscale("core_b", lin([(1, 1), (0.3, hb_h)]))
    for p, side in SIDES:
        hunt.scale(f"lid_{p}", None, f"math.max(0.3, math.max({blink(5.3, 8.9, 0.12, 2.0)}, {SLEEP}) * 2)", None)
        sg = -1 if side < 0 else 1
        for k in range(3):
            hunt.rot(f"gill_{p}{k}", None, mul(sg, lin([(9.0, 1), (5.0, f"math.max(0, -{S(0.32, -30 * k)})")])), None)
        hunt.rot(f"{p}_fin", lin([(3.0, S(0.3, 40 if side < 0 else 130))]))

    # the hands: fingers close round a held item (also in first person); claws splay with an empty swing
    hands = Layer(r, "appendages", loop=True)
    for p, side in SIDES:
        hold = HOLD_R if side < 0 else HOLD_L
        sg = -1 if side < 0 else 1
        for k in range(3):
            hands.rot(f"{p}_finger{k}", None, None, prod(sg * 72, hold))
        hands.rot(f"{p}_thumb", None, None, prod(sg * 40, hold))

    # ------------------------------------------------------------------ locomotion: heavy, uneven steps
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    keep = lin([(0.5, 1), (0.12, SPR)])                 # short, heavy strides; a little longer when he hunts
    stride(loco, keep)
    arm_swing(loco, 0.38)                               # tired arms: they barely swing, then trail
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"          # + while this leg swings forward
        st = CSTEP() if side < 0 else f"-{CSTEP()}"        # + while this leg pushes off behind
        knee = prod(POS(sw), s, lin([(30, 1), (22, SPR)]))
        loco.rot(f"{p}_shin", knee)
        flat = prod(side * 1.4, keep, TCOS)                # keep the wide sole flat against the stride angle
        loco.rot(f"{p}_foot", lin([(1.0, flat), (-0.75, knee), (12, prod(POS(st), s))]))
        e = EMPTY_R if side < 0 else EMPTY_L
        # heavy arms swing late; the forearms trail; predatory sprint: arms low and a little out
        loco.rot(f"{p}_fore", prod(lin([(-10, f"math.max(0, {CSTEP(-50) if side < 0 else '-' + CSTEP(-50)})"),
                                        (-8, SPR)]), s, e))
        loco.rot(f"{p}_arm_g", prod(-12, ss, e), None, mirror(side, prod(10, ss, e)))
        loco.rot(f"{p}_fin", lin([(10, s), (8, ss), (4, prod(f"math.sin({PH} * 2 - 70)", s))]), None,
                 mirror(side, lin([(6, s), (4, prod(f"math.sin({PH} - 60)", s))])))
    # whole-body sums used by several groups: computed once per frame (pre_animation)
    impact = shared(f"{s} * ({STRIKE_R} + 0.55 * {STRIKE_L})", "plr_bt")      # the right foot lands harder
    lean = shared(f"{s} * (4 + 8 * {SPR})", "plr_bt")
    roll = shared(f"{s} * (2.6 * {STEP()} + {POS(STEP())} + 3 * {TURN})", "plr_bt")
    twist = shared(f"0.12 * {LOOK} - 4 * {CSTEP()} * {s}", "plr_bt")
    body(loco, rig, lean=lean, roll=roll, twist=twist)
    loco.rot("chest", lin([(2.0, s), (5.0, ss), (2.5, impact)]))
    loco.rot("head_g", lin([(-2.0, s), (-14.0, ss), (2.0, prod(f"math.sin({PH} * 2 - 40)", s))]), prod(3.0, CSTEP(-20), s))
    loco.pos("head_g", None, None, prod(-1.2, ss))
    for k, pl in enumerate(plates):                                     # the tergites jostle a beat after each footfall
        lag = 25 + 12 * k
        hit = lin([(1.0, f"math.pow(math.max(0, -math.cos({PH} - {lag})), 6)"),
                   (0.6, f"math.pow(math.max(0, math.cos({PH} - {lag})), 6)")])
        loco.pos(pl, None, prod(-0.3, hit, s), None)
        loco.rot(pl, prod(3.0, hit, s))
    loco.rot("sword", prod(2.0, f"math.sin({PH} * 2 - 30)", s))         # the hilt bobs in the wound
    for p, side in SIDES:
        for k in range(3):
            loco.rot(f"gill_{p}{k}", None, mirror(side, prod(-8, s)), None)
    grounded(model, loco, rig, r, harmonics=8)                          # after every contribution that moves the legs
    for bn in rig.upper():                                              # the trunk settles onto the hips at each footfall
        loco.pos(bn, None, mul(-0.7, impact))

    # footfall dust (heavy steps)
    steps = {}
    for p in ("r", "l"):
        st_ = KeyLayer(r, f"step_{p}", 0.3)
        st_.particle(0.0, "stepdust", f"{p}_step")
        steps[p] = st_
    moving = "q.modified_move_speed > 0.3 && q.is_on_ground && !q.is_in_water && !q.is_riding"
    step_ctrl = {f"controller.animation.{NS}.{r}.steps": {"initial_state": "idle", "states": {
        "idle": {"transitions": [{"r": f"{moving} && math.cos({PH}) < -0.92"}, {"l": f"{moving} && math.cos({PH}) > 0.92"}]},
        "r": {"animations": ["step_r"], "transitions": [{"l": f"{moving} && math.cos({PH}) > 0.92"}, {"idle": f"!({moving})"}]},
        "l": {"animations": ["step_l"], "transitions": [{"r": f"{moving} && math.cos({PH}) < -0.92"}, {"idle": f"!({moving})"}]},
    }}}

    # ------------------------------------------------------------------ airborne
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"{p}_leg_g", lin([(-16, RISE), (-6, FALL)]))
        air.rot(f"{p}_shin", lin([(30, RISE), (8, FALL)]))
        air.rot(f"{p}_foot", lin([(-12, RISE), (10, FALL)]))
        air.rot(f"{p}_arm_g", prod(-8, FALL, e), None, mirror(side, prod(lin([(6, RISE), (14, FALL)]), e)))
        air.rot(f"{p}_fin", lin([(-14, RISE), (18, FALL)]))
        for k in range(3):
            air.rot(f"{p}_finger{k}", prod(-10, FALL, e))
    for k, pl in enumerate(plates):
        air.rot(pl, lin([(-2.5, RISE), (3.5, FALL)]))
    body(air, rig, lean=lin([(-3, RISE), (5, FALL)]))
    air.rot("head_g", lin([(4, RISE), (-4, FALL)]))
    air.rot("jaw", lin([(4, FALL)]))

    def sink(thigh, shin):
        """How far the hips drop when the knees bend this much (thigh 5.25, shin 4.75 long; rest -6 / +14)."""
        a, b = math.radians(-6 + thigh), math.radians(-6 + thigh + 14 + shin)
        rest = 5.25 * (1 - math.cos(math.radians(-6))) + 4.75 * (1 - math.cos(math.radians(8)))
        return 5.25 * (1 - math.cos(a)) + 4.75 * (1 - math.cos(b)) - rest

    land = KeyLayer(r, "land", 0.55)
    land_hard = KeyLayer(r, "land_hard", 0.8)
    for kl, g in ((land, 1.0), (land_hard, 1.5)):
        L = kl.length
        t1, t2 = 0.1 * g, 0.3 * g
        bend = {0: (-22 * g, 40 * g), t1: (-26 * g, 48 * g), t2: (-4, 6), L: (0, 0)}
        for p, side in SIDES:
            kl.rot(f"{p}_leg_g", {t: (th, 0, 0) for t, (th, sh) in bend.items()})
            kl.rot(f"{p}_shin", {t: (sh, 0, 0) for t, (th, sh) in bend.items()})
            kl.rot(f"{p}_foot", {t: (-(th + sh), 0, 0) for t, (th, sh) in bend.items()})     # soles stay flat
            kl.rot(f"{p}_fin", {0: (16 * g, 0, 0), 0.15 * g: (-8, 0, 0), 0.35 * g: (3, 0, 0), L: (0, 0, 0)})
            kl.particle(0.0, "stepdust", f"{p}_step")
        lean = {0: 7 * g, t1: 9 * g, t2: -1.5, L: 0.0}
        body_keys(kl, rig, {t: {"bob": -sink(th, sh), "lean": lean[t]} for t, (th, sh) in bend.items()})
        for k, pl in enumerate(plates):
            d = 0.03 * k
            kl.pos(pl, {0: (0, 0, 0), 0.08 + d: (0, -0.7 * g, 0), 0.24 + d: (0, 0.25 * g, 0), 0.4 + d: (0, 0, 0), L: (0, 0, 0)})
        kl.rot("head_g", {0: (-5 * g, 0, 0), 0.12 * g: (-7 * g, 0, 0), 0.32 * g: (3, 0, 0), L: (0, 0, 0)})
        kl.rot("jaw", {0: (0, 0, 0), 0.08: (10 * g, 0, 0), 0.3: (0, 0, 0), L: (0, 0, 0)})
        kl.scale("core_f", {0: 1, 0.06: 1.35 * g, 0.25: 1, L: 1})
        for p in ("r", "l"):
            kl.scale(f"lid_{p}", {0: 1, 0.04: (1, 1.9, 1), 0.3: (1, 1.9, 1), 0.42: 1, L: 1})

    # ------------------------------------------------------------------ attack: a raking claw (the jaw snaps too)
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(6, ATK), twist=prod(-9, ATK))
    atk.rot("head_g", prod(6, ATK))
    atk.pos("jaws", None, None, prod(-1.6, ATK2))
    atk.rot("jaw", prod(22, ATK))
    atk.rot("r_fore", prod(-24, ATK2, EMPTY_R))
    for k in range(3):                                                 # claws spread, then rake shut
        atk.rot(f"r_finger{k}", prod((k - 1) * 14, ATK, EMPTY_R), None, prod(-36, ATK2, EMPTY_R))
    for p in ("r", "l"):
        atk.rot(f"brow_{p}", None, None, prod(8 if p == "r" else -8, ATK))
        atk.scale(f"lid_{p}", None, lin([(1, 1), (0.5, ATK)]), None)

    # ------------------------------------------------------------------ hurt
    hurt = KeyLayer(r, "hurt", 0.6)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -6, "roll": 3}, 0.2: {"lean": 3, "roll": -1}, 0.42: {"lean": -1}, 0.6: {}})
    hurt.rot("head_g", {0: (0, 0, 0), 0.05: (-10, 6, 0), 0.22: (4, -2, 0), 0.6: (0, 0, 0)})
    hurt.rot("jaw", {0: (0, 0, 0), 0.05: (16, 0, 0), 0.25: (4, 0, 0), 0.6: (0, 0, 0)})
    hurt.pos("jaws", {0: (0, 0, 0), 0.05: (0, 0, -1.2), 0.3: (0, 0, 0), 0.6: (0, 0, 0)})
    hurt.scale("core_f", {0: 1, 0.04: 1.7, 0.2: 1.1, 0.6: 1})
    hurt.rot("sword", {**shake(0.0, 0.45, (4, 3, 0), freq=8, decay=6), 0.6: (0, 0, 0)})
    for k, pl in enumerate(plates):
        hurt.pos(pl, {**shake(0.02 * k, 0.4, (0.25 * ((k % 3) - 1), 0.35, 0.2), freq=9 + k % 3, decay=6), 0.6: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.scale(f"lid_{p}", {0: 1, 0.04: (1, 2.1, 1), 0.3: (1, 2.1, 1), 0.45: 1, 0.6: 1})
        hurt.rot(f"brow_{p}", {0: (0, 0, 0), 0.05: (0, 0, -sg * 12), 0.4: (0, 0, -sg * 6), 0.6: (0, 0, 0)})
        for k in range(3):
            hurt.rot(f"gill_{p}{k}", {0: (0, 0, 0), 0.05: (0, sg * 24, 0), 0.3: (0, sg * 8, 0), 0.6: (0, 0, 0)})
        hurt.rot(f"{p}_fin", {**shake(0.0, 0.5, (8, 0, 6 * sg), freq=6, decay=5), 0.6: (0, 0, 0)})

    # ------------------------------------------------------------------ swimming: an abyssal chimera in its element
    swim = Layer(r, "swim", loop=True)
    wave_f = 0.9                                                       # Hz: a slow lateral undulation, head to legs
    swim.rot("trunk", None, None, mul(5.0, S(wave_f)))
    swim.rot("chest", lin([(-6, 1)]), None, mul(4.0, S(wave_f, 50)))
    for p, side in SIDES:
        swim.rot(f"{p}_leg_g", lin([(10, 1)]), None, mul(12.0, S(wave_f, -70)))      # the legs sweep like a tail
        swim.rot(f"{p}_shin", lin([(14, 1), (8, S(wave_f, -110))]), None, None)
        swim.rot(f"{p}_foot", lin([(30, 1), (14, S(wave_f, -150))]), None, None)     # wide feet as flukes
        e = EMPTY_R if side < 0 else EMPTY_L
        swim.rot(f"{p}_arm_g", prod(lin([(8, 1), (6, S(wave_f, 30))]), e), None, mirror(side, prod(-5, e)))  # arms trail
        swim.rot(f"{p}_fore", prod(lin([(12, 1), (8, S(wave_f, -20))]), e))
        swim.rot(f"{p}_fin", lin([(-20, 1), (12, S(wave_f * 2, 40))]), mirror(side, mul(-14, S(wave_f, -40))), None)
        sg = -1 if side < 0 else 1
        for k in range(3):
            swim.rot(f"{p}_finger{k}", lin([((k - 1) * 10, 1)]), None, mul(sg * -10, 1))  # webbed hands spread
            swim.rot(f"gill_{p}{k}", None, mul(sg, lin([(18, 1), (8, S(1.8, k * 60))])), None)
    for k, pl in enumerate(plates):
        swim.rot(pl, mul(3.0, S(wave_f * 2, -k * 40)), None, mul(2.5, S(wave_f, -k * 25)))
    swim.rot("head_g", lin([(-10, 1)]), mul(-4.0, S(wave_f, 20)), None)
    swim.rot("jaw", lin([(6, 1), (4, S(0.6))]))
    swim.particle(0.0, "bubbles", "gills")
    swim.kw["length"] = 1.6

    # ------------------------------------------------------------------ idle behaviours (an old man, alone with his sun)
    fid = []
    # 1. shields his eyes from his own sword, muttering
    shade = KeyLayer(r, "fidget_shield", 3.6)
    shade.rot("r_arm_g", {0: (0, 0, 0), 0.5: (-74, -34, 0), 2.6: (-72, -32, 0), 3.2: (0, 0, 0), 3.6: (0, 0, 0)})
    shade.rot("r_fore", {0: (0, 0, 0), 0.5: (-78, 18, 0), 2.6: (-76, 18, 0), 3.2: (0, 0, 0)})
    shade.rot("r_hand", {0: (0, 0, 0), 0.6: (10, 0, 70), 2.6: (10, 0, 70), 3.2: (0, 0, 0)})
    for k in range(3):
        shade.rot(f"r_finger{k}", {0: (0, 0, 0), 0.6: ((k - 1) * 9, 0, 10), 2.6: ((k - 1) * 9, 0, 10), 3.2: (0, 0, 0)})
    shade.rot("head_g", {0: (0, 0, 0), 0.5: (10, 12, 4), 1.4: (8, 16, 5), 2.4: (10, 10, 4), 3.2: (0, 0, 0), 3.6: (0, 0, 0)})
    body_keys(shade, rig, {0: {}, 0.5: {"twist": -5, "lean": -2}, 2.6: {"twist": -5, "lean": -2}, 3.2: {}, 3.6: {}})
    for p in ("r", "l"):
        shade.scale(f"lid_{p}", {0: 1, 0.4: (1, 1.85, 1), 2.8: (1, 1.85, 1), 3.2: 1, 3.6: 1})
        shade.rot(f"brow_{p}", {0: (0, 0, 0), 0.4: (0, 0, 10 if p == "r" else -10), 2.8: (0, 0, 10 if p == "r" else -10), 3.2: (0, 0, 0)})
    shade.rot("jaw", {0: (0, 0, 0), 0.8: (0, 0, 0), 0.95: (7, 0, 0), 1.1: (2, 0, 0), 1.25: (8, 0, 0), 1.4: (1, 0, 0),
                      1.6: (6, 0, 0), 1.8: (0, 0, 0), 3.6: (0, 0, 0)})
    shade.scale("core_f", {0: 1, 0.6: 1.25, 2.6: 1.25, 3.2: 1, 3.6: 1})
    fid.append(shade)
    # 2. a long irritated sigh: the hump rises, holds, then everything sags
    sigh = KeyLayer(r, "fidget_sigh", 4.2)
    sigh.rot("chest", {0: (0, 0, 0), 1.2: (-6, 0, 0), 1.7: (-6, 0, 0), 3.0: (5, 0, 0), 3.7: (4, 0, 0), 4.2: (0, 0, 0)})
    for arm in ("r_arm_g", "l_arm_g"):
        sigh.pos(arm, {0: (0, 0, 0), 1.2: (0, 0.7, 0), 1.7: (0, 0.7, 0), 3.0: (0, -0.9, 0), 3.7: (0, -0.8, 0), 4.2: (0, 0, 0)})
    for k, pl in enumerate(plates):
        sigh.pos(pl, {0: (0, 0, 0), 1.2 + 0.03 * k: (0, 0.25, 0.4), 1.7: (0, 0.25, 0.4), 3.0 + 0.04 * k: (0, -0.15, -0.1), 4.2: (0, 0, 0)})
    sigh.rot("head_g", {0: (0, 0, 0), 1.2: (-10, 0, 0), 1.7: (-10, 0, 0), 3.0: (12, 0, 4), 3.7: (11, 0, 4), 4.2: (0, 0, 0)})
    sigh.rot("jaw", {0: (0, 0, 0), 1.7: (0, 0, 0), 2.0: (12, 0, 0), 2.8: (10, 0, 0), 3.1: (0, 0, 0), 4.2: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        sigh.scale(f"lid_{p}", {0: 1, 1.2: (1, 0.6, 1), 1.7: (1, 0.6, 1), 2.6: (1, 1.7, 1), 3.8: (1, 1.6, 1), 4.2: 1})
        for k in range(3):
            sigh.rot(f"gill_{p}{k}", {0: (0, 0, 0), 1.9 + 0.05 * k: (0, sg * 26, 0), 2.9: (0, sg * 20, 0), 3.4: (0, 0, 0), 4.2: (0, 0, 0)})
    sigh.particle(2.0, "bubbles", "maw")
    fid.append(sigh)
    # 3. dozes off on his feet, then jerks awake
    doze = KeyLayer(r, "fidget_doze", 4.6)
    doze.rot("head_g", {0: (0, 0, 0), 1.6: (14, 0, 6), 2.6: (22, 0, 9), 2.75: (-14, 0, -2), 2.95: (-6, 6, 0),
                        3.3: (-4, -10, 0), 3.9: (2, 0, 0), 4.6: (0, 0, 0)})
    body_keys(doze, rig, {0: {}, 1.6: {"lean": 3}, 2.6: {"lean": 6, "bob": -0.5}, 2.75: {"lean": -4, "bob": 0.4},
                          3.1: {"lean": 1}, 4.6: {}})
    doze.rot("jaw", {0: (0, 0, 0), 1.8: (6, 0, 0), 2.6: (14, 0, 0), 2.72: (0, 0, 0), 4.6: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        doze.scale(f"lid_{p}", {0: 1, 1.2: (1, 1.6, 1), 2.0: (1, 2.0, 1), 2.7: (1, 2.0, 1), 2.78: (1, 0.15, 1),
                                3.3: (1, 0.2, 1), 3.8: (1, 1.0, 1), 4.6: 1})
        doze.rot(f"brow_{p}", {0: (0, 0, 0), 2.72: (0, 0, 0), 2.8: (0, 0, -sg * 14), 3.4: (0, 0, -sg * 10), 4.0: (0, 0, 0)})
        doze.rot(f"{p}_arm_g", {0: (0, 0, 0), 2.7: (0, 0, 0), 2.8: (-10, 0, -sg * 8), 3.1: (0, 0, 0), 4.6: (0, 0, 0)})
        for k in range(3):
            doze.rot(f"{p}_finger{k}", {0: (0, 0, 0), 2.7: (0, 0, 0), 2.8: ((k - 1) * 16, 0, -sg * 14), 3.2: (0, 0, 0)})
    doze.scale("core_f", {0: 1, 2.7: 1, 2.8: 1.6, 3.1: 1, 4.6: 1})
    fid.append(doze)
    # 4. pokes at the wound and wiggles the hilt, with a grimace
    poke = KeyLayer(r, "fidget_poke", 4.0)
    poke.rot("l_arm_g", {0: (0, 0, 0), 0.6: (-48, 34, 0), 3.2: (-48, 34, 0), 3.7: (0, 0, 0), 4.0: (0, 0, 0)})
    poke.rot("l_fore", {0: (0, 0, 0), 0.6: (-40, 0, 0), 3.2: (-40, 0, 0), 3.7: (0, 0, 0)})
    for k in range(3):
        poke.rot(f"l_finger{k}", {0: (0, 0, 0), 0.7: (0, 0, 60), 3.1: (0, 0, 60), 3.6: (0, 0, 0)})
    poke.rot("sword", {0: (0, 0, 0), 0.9: (0, 0, 0), 1.1: (5, 4, 0), 1.3: (-3, -4, 0), 1.5: (4, 3, 0), 1.75: (-2, -2, 0),
                       2.0: (0, 0, 0), 2.4: (0, 0, 0), 2.55: (6, 0, 0), 2.8: (0, 0, 0), 4.0: (0, 0, 0)})
    poke.scale("core_f", {0: 1, 1.0: 1, 1.15: 1.7, 1.5: 1.3, 2.55: 1.9, 2.9: 1, 4.0: 1})
    poke.scale("core_b", {0: 1, 1.05: 1, 1.2: 1.5, 1.6: 1.1, 2.6: 1.7, 3.0: 1, 4.0: 1})
    poke.rot("head_g", {0: (0, 0, 0), 0.6: (22, 8, 0), 2.5: (20, 8, 0), 2.6: (8, 4, -6), 3.4: (6, 0, -3), 4.0: (0, 0, 0)})
    body_keys(poke, rig, {0: {}, 0.6: {"lean": 4, "twist": 6}, 2.55: {"lean": 6, "twist": 6}, 2.65: {"lean": 1, "twist": 2},
                          3.6: {}, 4.0: {}})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        poke.scale(f"lid_{p}", {0: 1, 1.1: (1, 1.2, 1), 1.2: (1, 2.1, 1), 1.9: (1, 1.6, 1), 2.55: (1, 2.1, 1), 3.4: (1, 1.3, 1), 4.0: 1})
        poke.rot(f"brow_{p}", {0: (0, 0, 0), 1.15: (0, 0, -sg * 14), 2.0: (0, 0, -sg * 8), 2.6: (0, 0, -sg * 16), 3.5: (0, 0, 0)})
    poke.pos("jaws", {0: (0, 0, 0), 1.15: (0, 0, -0.75), 1.8: (0, 0, -0.5), 2.55: (0, 0, -1.0), 3.2: (0, 0, 0), 4.0: (0, 0, 0)})
    poke.particle(1.15, "sunmotes", "wound").particle(2.55, "sunmotes", "wound")
    fid.append(poke)
    picks = [("fidget_shield", "math.mod(math.floor(q.life_time * 1.3), 5) == 0 && !q.is_item_equipped(0)"),
             ("fidget_sigh", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_doze", "math.mod(math.floor(q.life_time * 1.3), 5) == 2"),
             ("fidget_poke", "math.mod(math.floor(q.life_time * 1.3), 5) == 3 && !q.is_item_equipped(1)")]

    # ------------------------------------------------------------------ forms
    D = np.array(_D, float)
    intro = {}
    # base: the sun settles back into the wound - it slides the last two pixels home, and he flinches
    ib = A(r, "intro_base", loop="hold", length=1.0)
    _merge(ib, "sword", "position", {0.0: _r3(-D * 2.0), 0.18: _r3(-D * 2.0), 0.3: _r3(D * 0.25), 0.42: [0, 0, 0], 1.0: [0, 0, 0]})
    _merge(ib, "chest", "rotation", {0.0: [0, 0, 0], 0.26: [0, 0, 0], 0.32: [7, 0, 0], 0.6: [-1.5, 0, 0], 1.0: [0, 0, 0]})
    _merge(ib, "head_g", "rotation", {0.0: [0, 0, 0], 0.26: [0, 0, 0], 0.32: [-12, 0, 0], 0.65: [3, 0, 0], 1.0: [0, 0, 0]})
    ib.bone("core_f", scale={0.0: 1.0, 0.28: 1.0, 0.34: 1.7, 0.7: 1.0})
    for p in ("r", "l"):
        ib.bone(f"lid_{p}", scale={0.0: [1, 1, 1], 0.28: [1, 1, 1], 0.33: [1, 2.1, 1], 0.8: [1, 2.0, 1], 1.0: [1, 1, 1]})
    ib.particle(0.3, "sunmotes", "wound")
    intro["base"] = ib
    # lure: the sun blazes; he recoils from his own light and screws his eyes shut
    il = stagger(model, "intro_lure", "base", "lure", 0.35, {})
    il.bone("core_f", scale={0.0: 1.0, 0.12: 1.9, 0.35: 1.5})
    il.bone("core_b", scale={0.0: 1.0, 0.15: 1.7, 0.35: 1.35})
    for p in ("r", "l"):
        il.bone(f"lid_{p}", scale={0.0: [1, 1, 1], 0.1: [1, 2.1, 1], 0.35: [1, 2.0, 1]})
    # one hand comes up as a visor over the brow (the off hand, only while it holds nothing)
    fl = FREE_L
    for bn, pose in (("l_arm_g", (-66, 52, 0)), ("l_fore", (-84, -8, 0)), ("l_hand", (10, 0, -72))):
        il.bone(bn, rot={0.0: [0, 0, 0], 0.22: [f"{pose[0] * 1.06:g} * {fl}", f"{pose[1]:g} * {fl}", f"{pose[2]:g} * {fl}"],
                         0.35: [f"{pose[0]:g} * {fl}", f"{pose[1]:g} * {fl}", f"{pose[2]:g} * {fl}"]})
    il.particle(0.0, "glare", "lure_c")
    intro["lure"] = il
    # maw: the jaws shoot out (fast, with a snap)
    intro["maw"] = stagger(model, "intro_maw", "base", "maw", 0.22, {"jaws": (0.0, 0.12), "jaw": (0.04, 0.12)}, over=-0.15)
    intro["maw"].particle(0.0, "bubbles", "maw")
    # bastion: the tergites close from the bottom up, shoulders slide in, the head tucks
    order = {f"plate{k}": (0.04 * (NPLATES - 1 - k), 0.22) for k in range(NPLATES)}
    order.update({"r_pauldron": (0.18, 0.2), "l_pauldron": (0.2, 0.2), "skull": (0.1, 0.3)})
    intro["bastion"] = stagger(model, "intro_bastion", "base", "bastion", 0.55, order)
    intro["bastion"].bone("core_b", scale={0.0: 1.0, 0.3: 1.6, 0.55: 1.0})
    intro["bastion"].particle(0.25, "sunmotes", "back")
    # unshackled: the sun is torn out - the wound flares, he recoils, then drops into the stance
    iu = stagger(model, "intro_unshackled", "base", "unshackled", 0.9, {"chest": (0.25, 0.5), "skull": (0.3, 0.45)})
    iu.bone("core_f", scale={0.0: 1.0, 0.08: 2.0, 0.4: 1.25, 0.9: 1.0})
    iu.bone("core_b", scale={0.0: 1.0, 0.1: 1.8, 0.45: 1.15, 0.9: 1.0})
    _merge(iu, "head_g", "rotation", {0.0: [0, 0, 0], 0.08: [-16, 0, 0], 0.4: [-4, 0, 0], 0.9: [0, 0, 0]})
    for p in ("r", "l"):
        iu.bone(f"lid_{p}", scale={0.0: [1, 1, 1], 0.06: [1, 2.1, 1], 0.4: [1, 2.1, 1], 0.55: [1, 0.3, 1], 0.9: [1, 0.3, 1]})
    iu.particle(0.0, "sunmotes", "wound")
    intro["unshackled"] = iu
    # daybreak: the light rises through him; he strains upward, everything flares open
    order = {f"plate{k}": (0.15 + 0.05 * k, 0.4) for k in range(NPLATES)}
    order.update({"skull": (0.3, 0.5), "chest": (0.2, 0.5)})
    idb = stagger(model, "intro_daybreak", "base", "daybreak", 1.1, order)
    idb.bone("core_f", scale={0.0: 1.0, 0.4: 2.0, 1.1: 1.55})
    idb.bone("core_b", scale={0.0: 1.0, 0.5: 1.8, 1.1: 1.4})
    idb.particle(0.0, "glare", "lure_c").particle(0.4, "sunmotes", "back")
    intro["daybreak"] = idb

    lure_loop = Layer(r, "lure_loop", loop=True)                    # squinting into the blaze, the shielding hand
    lure_loop.uscale("core_f", lin([(1, 1), (0.12, S(7.5)), (0.2, hb)]))
    for p, side in SIDES:
        lure_loop.scale(f"lid_{p}", None, lin([(1, 1), (0.08, S(9.0, 0 if side < 0 else 90))]), None)
    for p, side in SIDES:                                           # claws splay, flinching from the light
        e = FREE_R if side < 0 else FREE_L
        for k in range(3):
            lure_loop.rot(f"{p}_finger{k}", prod((k - 1) * 16, e), None, prod(-side * 16, e))
    lure_loop.rot("head_g", None, mul(-4, S(0.7)), None)

    maw_loop = Layer(r, "maw_loop", loop=True)                      # the jaws snap
    maw_loop.rot("jaw", mul(-14, f"math.max(0, {S(5.0)})"))
    maw_loop.pos("jaws", None, None, mul(-0.5, S(5.0, 60)))
    for p, side in SIDES:
        e = FREE_R if side < 0 else FREE_L
        maw_loop.rot(f"{p}_arm_g", prod(8, e), None, mirror(side, prod(6, e)))         # arms swept back
        for k in range(3):
            maw_loop.rot(f"{p}_finger{k}", prod((k - 1) * 14, e), None, prod(-(-1 if side < 0 else 1) * 10, e))

    bastion_loop = Layer(r, "bastion_loop", loop=True)              # braced: tergites breathe tight, the heart races
    for k, pl in enumerate(plates):
        bastion_loop.pos(pl, None, None, mul(0.08, S(1.4, -k * 35)))
    bastion_loop.uscale("core_f", lin([(1, 1), (0.25, hb_h)]))
    bastion_loop.uscale("core_b", lin([(1, 1), (0.35, hb_h)]))
    body(bastion_loop, rig, roll=mul(0.6, S(3.1)))
    for p, side in SIDES:                                           # forearms folded up across the chest
        e = FREE_R if side < 0 else FREE_L
        bastion_loop.rot(f"{p}_fore", prod(-38, e))
        for k in range(3):
            bastion_loop.rot(f"{p}_finger{k}", None, None, prod(side * -30, e))
    bastion_loop.particle(0.0, "sunmotes", "back")
    bastion_loop.kw["length"] = 1.5

    unshackled_loop = Layer(r, "unshackled_loop", loop=True)        # predatory: low, still, lids open, focused
    for p, side in SIDES:
        e = FREE_R if side < 0 else FREE_L
        unshackled_loop.rot(f"{p}_arm_g", prod(-14, e), None, mirror(side, prod(8, e)))    # empty hands held ready
        unshackled_loop.rot(f"{p}_fore", prod(-12, e))
        for k in range(3):
            unshackled_loop.rot(f"{p}_finger{k}", prod((k - 1) * 12, e), None, prod((-1 if side < 0 else 1) * 22, e))
        for k in range(3):
            unshackled_loop.rot(f"gill_{p}{k}", None, mul(-1 if side < 0 else 1, 6), None)
    unshackled_loop.rot("jaw", 3)

    daybreak_loop = Layer(r, "daybreak_loop", loop=True)            # strained: everything trembles in the light
    daybreak_loop.rot("chest", lin([(1.2, S(11.0)), (0.6, S(7.3, 40))]), None, mul(0.8, S(9.1)))
    daybreak_loop.rot("head_g", lin([(1.5, S(10.3, 20))]), mul(1.2, S(8.7)), None)
    daybreak_loop.rot("jaw", lin([(4, S(6.0)), (3, 1)]))
    daybreak_loop.uscale("core_f", lin([(1, 1), (0.25, S(4.0)), (0.3, hb_h)]))
    daybreak_loop.uscale("core_b", lin([(1, 1), (0.25, S(4.0, 90)), (0.3, hb_h)]))
    for k, pl in enumerate(plates):
        daybreak_loop.rot(pl, mul(1.5, S(9.0 + k, k * 50)))
    for p, side in SIDES:
        e = FREE_R if side < 0 else FREE_L
        daybreak_loop.rot(f"{p}_arm_g", prod(-10, e), None, mirror(side, prod(lin([(16, 1), (2, S(8.0))]), e)))
        for k in range(3):
            daybreak_loop.rot(f"{p}_finger{k}", prod((k - 1) * 18, e), None, prod((-1 if side < 0 else 1) * -16, e))
        daybreak_loop.rot(f"{p}_fin", lin([(3, S(6.0, 0 if side < 0 else 90))]))

    fx = {
        "base": A(r, "fx_base", length=3.4).particle(0.0, "sunmotes", "wound"),
        "lure": A(r, "fx_lure", length=0.75).particle(0.0, "sunmotes", "wound").particle(0.35, "glare", "lure_c"),
        "maw": A(r, "fx_maw", length=0.3).particle(0.0, "bubbles", "maw"),
        "bastion": A(r, "fx_bastion", length=1.5).particle(0.0, "sunmotes", "wound_back"),
        "unshackled": A(r, "fx_unshackled", length=1.6).particle(0.0, "sunmotes", "wound").particle(0.8, "sunmotes", "wound_back"),
        "daybreak": A(r, "fx_daybreak", length=0.6).particle(0.0, "sunmotes", "wound").particle(0.3, "sunmotes", "back"),
    }
    built = [fp, tp, life.anim(), hunt.anim(), hands.anim(), loco.anim(), steps["r"].anim(), steps["l"].anim(), air.anim(),
             land.anim(), land_hard.anim(), atk.anim(), hurt.anim(), swim.anim(), lure_loop.anim(), maw_loop.anim(),
             bastion_loop.anim(), unshackled_loop.anim(), daybreak_loop.anim(),
             wait_anim(r, "fidget_wait", 7.0), wait_anim(r, "fidget_rest", 3.5), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-13.0), **fidget_controller(r, picks), **step_ctrl}
    loops = {"lure": "lure_loop", "maw": "maw_loop", "bastion": "bastion_loop", "unshackled": "unshackled_loop",
             "daybreak": "daybreak_loop"}
    swim_on = f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"
    animate = {}
    for v in ("base", "lure", "maw", "bastion", "unshackled", "daybreak"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("appendages", None),
               ("life_hunt" if v in CROUCH else "life", TP)]
        if v == "base":
            lst.append(("fidget", TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("steps", f"{TP} && {GAIT_OK}"),
                ("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("swim", swim_on), ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"sunmotes": f"{NS}:sun_motes", "bubbles": f"{NS}:abyss_bubbles", "stepdust": f"{NS}:step_dust",
                 "glare": f"{NS}:sun_glare"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers, "pre": pre_animation(r)}
