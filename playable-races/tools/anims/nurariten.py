"""Race 006 Nurariten (Unique) - attachable animation set (v1.2 redesign).

Motion language: slow and inevitable.  The sovereign glides (a sliding court step,
no bob, a steady head); cloth and halo do the moving - the hem sways a beat after the
legs, the sleeve pockets (tamoto) a beat after the arms, the halo turns at a stately
6 degrees per second while its seals orbit the other way.  Gestures are small and
quick (a 0.08 s sleeve flick); what they set in motion is large.  In the court form
the six halo beams fly into place one after another and become a torii.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from anims.core import NS, T
from anims.life import (ATK, FALL, LOOK, MOVE, PH, RISE, S, SPR, SQ, STILL, TCOS, KeyLayer, Layer, Rig, arm_swing, body,
                        body_keys, fidget_controller, landing_controller, lin, mul, prod, smooth_pulse, stride, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, grounded, pre_animation, shake, view_anims
from models.nurariten import GRAND, H, HALO, SEALS

R = "nurariten"
RIG = Rig("robe", (0, 12, 0), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"
# the attack swing, delayed: what follows the hand (sleeve pocket, halo) moves a beat later
ATK_LAG = "math.sin(math.clamp((v.attack_time ?? 0) * 220 - 50, 0, 180))"
AIR_ON = "(!q.is_on_ground && !q.is_in_water ? 1 : 0)"


def _beam_dir(k: int):
    a = math.radians(60.0 * k)
    return round(math.sin(a), 4) + 0.0, round(math.cos(a), 4) + 0.0     # no 1e-16 in Molang


def stagger(model, name: str, frm: str, to: str, length: float, order: Dict[str, tuple], grow: Dict[str, tuple]):
    """Transition from the `frm` pose into the `to` pose with per-bone timing
    (start, duration) and a small overshoot; `grow` bones scale in from zero along an axis."""
    a = A(R, name, loop="hold", length=length)
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        b = model.bones[bn]
        r_from = np.array(model.bone_rot(bn, frm), float)
        r_to = np.array(model.bone_rot(bn, to), float)
        t_from = np.array(b.variant[frm][0], float) if frm in b.variant else np.zeros(3)
        t_to = np.array(b.variant[to][0], float) if to in b.variant else np.zeros(3)
        dr, dt = r_from - r_to, t_from - t_to
        if np.allclose(dr, 0, atol=0.01) and np.allclose(dt, 0, atol=0.01):
            continue
        st, du = order.get(bn, (0.0, length * 0.7))
        keys = {0.0: 1.0, st: 1.0, st + du * 0.75: -0.07, st + du: 0.0, length: 0.0}
        rot = None if np.allclose(dr, 0, atol=0.01) else {t: list(dr * k) for t, k in keys.items()}
        pos = None if np.allclose(dt, 0, atol=0.01) else {t: list(dt * k) for t, k in keys.items()}
        a.bone(bn, rot=rot, pos=pos)
    for bn, (st, du, axis) in grow.items():
        z = [1.0, 1.0, 1.0]
        z["xyz".index(axis)] = 0.0
        over = [1.0, 1.0, 1.0]
        over["xyz".index(axis)] = 1.06
        a.bone(bn, scale={0.0: z, st: z, st + du * 0.8: over, st + du: [1, 1, 1], length: [1, 1, 1]})
    return a


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life: stillness; cloth and halo breathe
    life = Layer(r, "life", loop=True)
    life.scale("robe", lin([(1, 1), (0.006, S(0.16))]), None, lin([(1, 1), (0.006, S(0.16))]))
    life.rot("head_g", prod(lin([(1.6, SQ(0.045, 40, 2.5))]), STILL), prod(lin([(6, SQ(0.035, 0, 2.5))]), STILL), None)
    life.scale("lid", None, lin([(1, 1), (7.5, f"math.max({blink(9.7, 12.3, 0.3, 4.0)}, q.is_sleeping)")]), None)
    for p, side in SIDES:
        life.rot(f"{p}_sleeve", mul(1.0, S(0.12, 0 if side < 0 else 90)), None, None)
        life.rot(f"{p}_tamoto", mul(2.0, S(0.12, -50 if side < 0 else 40)), None, mul(side * -0.8, S(0.09, 20)))
        for part, amp in (("hem_f", -1.2), ("hem_b", 1.2), ("hem_s", 0.8)):
            ax = 2 if part == "hem_s" else 0
            v = [None, None, None]
            v[ax] = mul(amp, S(0.1, 30 if side < 0 else 120))
            life.rot(f"{p}_{part}", *v)

    # the halo turns slowly, its seals orbit the other way, each beam breathes outward on its own
    halo = Layer(r, "halo_spin", loop=True)
    halo.rot("seals", None, None, f"-{T} * 16")
    for k in range(HALO):
        dx, dy = _beam_dir(k)
        br = mul(0.35, S(0.2, k * 60))
        flare = prod(1.5, ATK_LAG)                 # a strike makes the beams flare out, then ease back
        halo.pos(f"beam{k}", lin([(dx, br), (dx, flare)]), lin([(dy, br), (dy, flare)]), None)
    halo.rot("halo", lin([(2.0, MOVE), (1.0, prod(SPR, MOVE))]), None, f"{T} * 6")   # lags a touch behind the body
    halo.pos("halo", None, lin([(0.6, f"({RISE}) * ({AIR_ON})"), (-0.4, f"({FALL}) * ({AIR_ON})")]), None)

    hands = Layer(r, "appendages", loop=True)    # the hands leave the sleeves only to hold or to strike
    hands.pos("r_hand", None, prod(-H, HOLD_R))
    hands.pos("l_hand", None, prod(-H, HOLD_L))

    # ------------------------------------------------------------------ locomotion: the sliding court step (suriashi)
    loco = Layer(r, "locomotion", loop=True)
    KEEP = 0.16
    stride(loco, KEEP)                            # 16% of the vanilla leg swing: the feet barely leave the floor
    arm_swing(loco, 0.1)                          # the arms hardly swing
    s = MOVE
    ss = prod(SPR, s)
    body(loco, rig, lean=lin([(1.5, s), (2.5, ss)]), twist=lin([(0.06, LOOK)]))
    grounded(model, loco, rig, r)
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        lag = f"math.cos({PH} - 45) * {sg}"
        # the hem rides on the legs but only follows half their swing, a beat late, trailing a little
        half = prod(0.5 * 1.4 * KEEP * (1 if side < 0 else -1), TCOS)
        loco.rot(f"{p}_hem_f", lin([(-1.0, half), (-2.5, prod(lag, s)), (-3.0, s), (-3.0, ss)]))
        loco.rot(f"{p}_hem_b", lin([(-1.0, half), (-2.5, prod(lag, s)), (5.0, s), (6.0, ss)]))
        loco.rot(f"{p}_hem_s", lin([(-1.0, half)]))
        loco.rot(f"{p}_hem_s", None, None, lin([(-sg * 2.5, prod(f"math.cos({PH} * 2 - 60)", s))]))
        # the sleeve pockets trail behind and swing later than the arms
        loco.rot(f"{p}_tamoto", lin([(9.0, s), (6.0, ss), (4.0, prod(f"math.cos({PH} - 70)", s, -sg))]))
        loco.rot(f"{p}_sleeve", lin([(2.5, s), (3.0, ss)]))
    loco.rot("head_g", lin([(-1.5, s), (-2.5, ss)]))  # the head stays level while the body leans

    air = Layer(r, "airborne", loop=True)         # a controlled, almost weightless rise; cloth lifts
    for p, side in SIDES:
        air.rot(f"{p}_hem_f", lin([(-10.0, RISE), (6.0, FALL)]))
        air.rot(f"{p}_hem_b", lin([(10.0, RISE), (-8.0, FALL)]))
        air.rot(f"{p}_tamoto", lin([(-8.0, RISE), (14.0, FALL)]))

    land = KeyLayer(r, "land", 0.55)
    land_hard = KeyLayer(r, "land_hard", 0.75)
    for kl, g in ((land, 0.6), (land_hard, 1.0)):
        L = kl.length
        body_keys(kl, rig, {0: {"lean": 2 * g}, 0.12: {"lean": 3 * g}, 0.35: {}, L: {}})
        for p, side in SIDES:
            kl.rot(f"{p}_hem_f", {0: (-7 * g, 0, 0), 0.18: (2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_hem_b", {0: (7 * g, 0, 0), 0.18: (-2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_tamoto", {0: (0, 0, 0), 0.1: (10 * g, 0, 0), 0.3: (-4 * g, 0, 0), L: (0, 0, 0)})
    land_hard.particle(0.0, "motes", "feet")

    atk = Layer(r, "attack", loop=True)          # a 0.08 s sleeve flick; the pocket follows (the halo flares, see halo_spin)
    atk.rot("r_sleeve", prod(-10, ATK))
    atk.rot("r_tamoto", prod(16, ATK_LAG))

    hurt = KeyLayer(r, "hurt", 0.95)             # a pause, a slow turn toward the offence, the halo disturbed
    hurt.rot("head_g", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.6: (-3, 20, 0), 0.8: (-3, 20, 0), 0.95: (0, 0, 0)})
    body_keys(hurt, rig, {0: {}, 0.15: {}, 0.6: {"twist": 8}, 0.95: {}})
    for k in range(HALO):
        hurt.pos(f"beam{k}", {**shake(0.0, 0.5, (0.5 * ((k % 3) - 1), 0.45, 0.0), freq=9 + k, decay=5), 0.95: (0, 0, 0)})
    for p, side in SIDES:
        hurt.rot(f"{p}_tamoto", {0: (0, 0, 0), 0.08: (12, 0, 0), 0.4: (-5, 0, 0), 0.95: (0, 0, 0)})
    hurt.scale("lid", {0: 1, 0.05: (1, 3, 1), 0.2: 1, 0.95: 1})

    # ------------------------------------------------------------------ idle behaviours (regal and few)
    fid = []
    survey = KeyLayer(r, "fidget_survey", 3.6)   # surveys its court as if it owned it
    survey.rot("head_g", {0: (0, 0, 0), 0.9: (-4, 32, 0), 1.6: (-4, 32, 0), 2.5: (-4, -28, 0), 3.0: (-4, -28, 0), 3.6: (0, 0, 0)})
    body_keys(survey, rig, {0: {}, 0.9: {"twist": 5}, 2.5: {"twist": -5}, 3.6: {}})
    fid.append(survey)
    sleeves = KeyLayer(r, "fidget_sleeves", 2.4)  # settles its sleeves with a flick; the pockets swing after
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        sleeves.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.35: (-14, 0, -6 * sg), 0.45: (-16, 0, 4 * sg), 1.1: (0, 0, 0), 2.4: (0, 0, 0)})
        sleeves.rot(f"{p}_tamoto", {0: (0, 0, 0), 0.45: (-6, 0, 0), 0.6: (16, 0, 8 * sg), 0.9: (-6, 0, -3 * sg), 1.3: (3, 0, 0), 1.8: (0, 0, 0)})
    fid.append(sleeves)
    glyph = KeyLayer(r, "fidget_glyph", 3.0)     # two fingers emerge and write a glyph in the air
    glyph.pos("r_hand", {0: (0, 0, 0), 0.4: (0, -H, 0), 2.4: (0, -H, 0), 2.8: (0, 0, 0)})
    glyph.rot("r_arm_g", {0: (0, 0, 0), 0.5: (-58, 10, 0), 1.0: (-62, -6, 0), 1.5: (-56, 12, 0), 2.0: (-60, 0, 0), 2.6: (0, 0, 0)})
    glyph.rot("r_tamoto", {0: (0, 0, 0), 0.5: (50, 0, 0), 2.0: (52, 0, 0), 2.7: (0, 0, 0)})   # the pocket keeps hanging down
    for k in (2, 3):
        glyph.rot(f"r_finger{k}", {0: (0, 0, 0), 0.4: (70, 0, 0), 2.4: (70, 0, 0), 2.8: (0, 0, 0)})
    glyph.particle(1.0, "decree", "r_fingertip")
    fid.append(glyph)
    still = KeyLayer(r, "fidget_procession", 3.0)  # utterly still - the halo turns one beam - its shadow becomes a procession
    still.rot("halo", {0: (0, 0, 0), 0.6: (0, 0, 0), 2.4: (0, 0, 60), 3.0: (0, 0, 60)})
    still.particle(0.2, "shadow", "feet")
    fid.append(still)
    picks = [("fidget_survey", "math.mod(math.floor(q.life_time * 1.3), 5) == 0"),
             ("fidget_sleeves", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_glyph", "math.mod(math.floor(q.life_time * 1.3), 5) == 2 && !q.is_item_equipped(0)"),
             ("fidget_procession", "math.mod(math.floor(q.life_time * 1.3), 5) == 3 && q.time_of_day > 0.2 && q.time_of_day < 0.8")]

    # ------------------------------------------------------------------ forms
    seals = [f"seal{k}" for k in range(SEALS)]
    court_order = {"beam2": (0.0, 0.4), "beam4": (0.1, 0.4), "beam3": (0.35, 0.35), "beam0": (0.55, 0.35),
                   "beam1": (0.65, 0.35), "beam5": (0.7, 0.35),
                   **{sn: (0.8 + 0.05 * i, 0.3) for i, sn in enumerate(seals)}}
    court_grow = {"pillar_r": (0.05, 0.45, "y"), "pillar_l": (0.15, 0.45, "y"), "nuki": (0.4, 0.3, "x"), "kasagi": (0.6, 0.35, "x")}
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.6),
        "nocturne": A(r, "intro_nocturne", loop="hold", length=0.6),
        "edict": stagger(model, "intro_edict", "base", "edict", 0.35, {}, {}),
        "court": stagger(model, "intro_court", "base", "court", 1.25, court_order, court_grow),
        "throne": stagger(model, "intro_throne", "court", "throne", 1.2, {},
                          {"throne": (0.0, 0.8, "y"), "banner_r": (0.5, 0.5, "y"), "banner_l": (0.6, 0.5, "y")}),
    }
    for k in range(HALO):
        dx, dy = _beam_dir(k)
        intro["base"].bone(f"beam{k}", pos={0.0: [dx * 1.5, dy * 1.5, 0], 0.45: [dx * -0.1, dy * -0.1, 0], 0.6: [0, 0, 0]})
        intro["nocturne"].bone(f"beam{k}", pos={0.0: [dx * 1.0, dy * 1.0, 0], 0.6: [0, 0, 0]})
    intro["court"].particle(0.0, "decree", "chest")
    intro["throne"].particle(0.0, "decree", "chest")

    edict_loop = Layer(r, "edict_loop", loop=True)
    for k in range(HALO):
        dx, dy = _beam_dir(k)
        pulse = smooth_pulse(1.2, 0.15, 0.2, 0.6, offset=k * 0.05)
        edict_loop.pos(f"beam{k}", prod(0.8 * dx, pulse), prod(0.8 * dy, pulse), None)
    for k in (2, 3):
        edict_loop.rot(f"r_finger{k}", 70)          # two fingers extended: the decree gesture
        edict_loop.rot(f"l_finger{k}", 70)
    court_loop = Layer(r, "court_loop", loop=True)
    for p, side in SIDES:
        court_loop.rot(f"{p}_tamoto", mul(3.0, S(0.25, 0 if side < 0 else 120)))
    throne_loop = Layer(r, "throne_loop", loop=True)
    for p, side in SIDES:
        throne_loop.rot(f"banner_{p}", mul(3.0, S(0.3, 0 if side < 0 else 90)), None, mul(2.0, S(0.21, 40)))
    for k in (1, 2, 3):
        throne_loop.rot(f"r_finger{k}", 75)         # a single finger raised
    noct_loop = Layer(r, "nocturne_loop", loop=True)
    for k in range(HALO):
        dx, dy = _beam_dir(k)
        br = mul(0.3, S(0.28, k * 40))
        noct_loop.pos(f"beam{k}", prod(dx, br), prod(dy, br), None)

    fx = {
        "base": A(r, "fx_base", length=4.0).particle(0.0, "motes", "halo"),
        "nocturne": A(r, "fx_nocturne", length=1.4).particle(0.0, "motes", "halo").particle(0.7, "motes", "chest"),
        "edict": A(r, "fx_edict", length=0.6).particle(0.0, "motes", "halo"),
        "court": A(r, "fx_court", length=0.9).particle(0.0, "motes", "chest"),
        "throne": A(r, "fx_throne", length=0.7).particle(0.0, "motes", "halo").particle(0.35, "motes", "chest"),
    }
    built = [fp, tp, life.anim(), halo.anim(), hands.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(),
             atk.anim(), hurt.anim(), edict_loop.anim(), court_loop.anim(), throne_loop.anim(), noct_loop.anim(),
             wait_anim(r, "fidget_wait", 8.0), wait_anim(r, "fidget_rest", 4.0), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-14.0), **fidget_controller(r, picks)}
    loops = {"edict": "edict_loop", "court": "court_loop", "throne": "throne_loop", "nocturne": "nocturne_loop"}
    animate = {}
    for v in ("base", "nocturne", "edict", "court", "throne"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP)]
        if v not in GRAND:
            lst += [("halo_spin", TP), ("appendages", None), ("fidget", TP)]
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP), ("hurt", f"{TP} && q.hurt_time > 0"),
                (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"motes": f"{NS}:royal_mote", "decree": f"{NS}:decree_burst", "shadow": f"{NS}:procession_shadow"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers, "pre": pre_animation(r)}
