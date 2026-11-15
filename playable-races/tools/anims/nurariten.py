"""Race 006 Nurariten (Unique) - attachable animation set.

Body language: serene, minimal, imperious.  Motion is slow and deliberate; the halo
fragments and the architecture behind it do the moving; gestures are small and the
effects they produce are large.
"""
from __future__ import annotations

from typing import Dict

from anims.core import NS, T, osc
from anims.life import (ATK, BUMP, CSTEP, EMPTY_L, EMPTY_R, FALL, LOOK, MOVE, PH, POS, RISE, S, SPR, SQ, STEP, STILL,
                        TCOS, TURN, WALKING, KeyLayer, Layer, Rig, arm_swing, body, body_keys, fidget_controller,
                        landing_controller, lin, mul, prod, stride, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, grounded, mirror, pre_animation, shake, transition, view_anims
from models.nurariten import HALO

R = "nurariten"
RIG = Rig("robe", (0, 12, 0), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life: stillness, the halo moves instead
    life = Layer(r, "life", loop=True)
    br = S(0.16)
    life.scale("robe", lin([(1, 1), (0.006, br)]), None, lin([(1, 1), (0.01, br)]))
    life.rot("head_g", prod(lin([(2, SQ(0.05, 40, 2.5))]), STILL), prod(lin([(9, SQ(0.04, 0, 2.5))]), STILL), None)
    life.pos("eyes", mul(0.18, SQ(0.09, 20, 2)), None, None)            # the eyes shift slowly, the face does not
    life.scale("lid", None, lin([(1, 1), (7.5, f"math.max({blink(9.7, 15.1, 0.5, 4.0)}, q.is_sleeping)")]), None)
    for k in range(HALO):
        # every fragment drifts on its own around the ring and breathes in and out
        life.rot(f"halo{k}", None, None, f"{T} * {5 + 1.7 * k} + {osc(0.1 + 0.02 * k, 6, k * 45)}")
        life.pos(f"halo{k}", None, None, mul(0.4, S(0.13 + 0.03 * k, k * 70)))
    life.rot("ring0", None, None, f"{T} * 8")
    life.rot("ring1", None, None, f"-{T} * 6")
    for p, side in SIDES:
        life.rot(f"{p}_sleeve", mul(1.5, S(0.12, 0 if side < 0 else 90)), None, mirror(side, mul(1.2, S(0.09, 30))))
        life.rot(f"{p}_wing", None, None, mirror(side, mul(1.0, S(0.1, 60))))
    for nm in ("skirt_f", "skirt_b"):
        life.rot(nm, mul(1.2, S(0.11, 20)), None, mul(0.8, S(0.07)))

    hands = Layer(r, "appendages", loop=True)    # the hands leave the sleeves only to hold or to strike
    hands.pos("r_hand", None, prod(-4.6, HOLD_R))
    hands.pos("l_hand", None, prod(-4.6, HOLD_L))

    # ------------------------------------------------------------------ locomotion: slow ceremonial steps
    loco = Layer(r, "locomotion", loop=True)
    keep = 0.34
    stride(loco, keep)
    arm_swing(loco, 0.12)                        # arms stay almost still, even at a run
    s = MOVE
    ss = prod(SPR, s)
    body(loco, rig, lean=lin([(2, s), (3, ss)]), roll=lin([(1.2, prod(STEP(), s))]), twist=lin([(0.08, LOOK)]))
    grounded(model, loco, rig, r)
    loco.rot("skirt_f", lin([(-7, s), (-6, ss), (3, prod(f"math.sin({PH} * 2)", s))]))
    loco.rot("skirt_b", lin([(9, s), (10, ss), (3, prod(f"math.sin({PH} * 2 + 60)", s))]))
    for p, side in SIDES:
        loco.rot(f"{p}_sleeve", lin([(6, s), (10, ss)]), None, mirror(side, prod(4, ss)))
        loco.rot(f"{p}_wing", None, None, mirror(side, lin([(-3, s), (4, prod(f"math.sin({PH} * 2)", s))])))
    for k in range(HALO):
        loco.pos(f"halo{k}", None, None, lin([(0.6, s), (0.8, ss)]))
    loco.rot("gate", lin([(-3, ss)]))

    air = Layer(r, "airborne", loop=True)        # a controlled, almost weightless rise
    air.rot("skirt_f", lin([(-10, RISE), (8, FALL)]))
    air.rot("skirt_b", lin([(10, RISE), (-8, FALL)]))
    for p, side in SIDES:
        air.rot(f"{p}_sleeve", None, None, mirror(side, lin([(10, RISE), (16, FALL)])))
    for k in range(HALO):
        air.pos(f"halo{k}", None, lin([(0.8, RISE), (-0.4, FALL)]), None)

    land = KeyLayer(r, "land", 0.5)
    land_hard = KeyLayer(r, "land_hard", 0.7)
    for kl, g in ((land, 0.6), (land_hard, 1.0)):
        L = kl.length
        body_keys(kl, rig, {0: {"lean": 3 * g}, 0.12: {"lean": 4 * g}, 0.35: {}, L: {}})
        kl.rot("skirt_f", {0: (-8 * g, 0, 0), 0.2: (3, 0, 0), L: (0, 0, 0)})
        kl.rot("skirt_b", {0: (8 * g, 0, 0), 0.2: (-3, 0, 0), L: (0, 0, 0)})
        for k in range(HALO):
            kl.pos(f"halo{k}", {0: (0, -0.6 * g, 0), 0.2: (0, 0.3, 0), L: (0, 0, 0)})
    land_hard.particle(0.0, "motes", "feet")

    atk = Layer(r, "attack", loop=True)          # a slight gesture; the halo flares
    atk.rot("r_arm_g", prod(-8, ATK))
    for k in range(HALO):
        atk.pos(f"halo{k}", None, None, prod(-0.8, ATK))
    atk.scale("ring0", lin([(1, 1), (0.12, ATK)]), lin([(1, 1), (0.12, ATK)]), 1)

    hurt = KeyLayer(r, "hurt", 0.95)             # a brief pause, a slow turn toward the offence, a halo disrupted
    hurt.rot("head_g", {0: (0, 0, 0), 0.15: (0, 0, 0), 0.6: (-3, 22, 0), 0.8: (-3, 22, 0), 0.95: (0, 0, 0)})
    body_keys(hurt, rig, {0: {}, 0.15: {}, 0.6: {"twist": 9}, 0.95: {}})
    for k in range(HALO):
        hurt.pos(f"halo{k}", {**shake(0.0, 0.5, (0.6 * ((k % 3) - 1), 0.5, 0.4), freq=10 + k, decay=5), 0.95: (0, 0, 0)})
    hurt.scale("lid", {0: 1, 0.05: (1, 3, 1), 0.2: 1, 0.95: 1})

    # ------------------------------------------------------------------ idle behaviours (regal and few)
    fid = []
    survey = KeyLayer(r, "fidget_survey", 3.4)   # surveys its court as if it owned it
    survey.rot("head_g", {0: (0, 0, 0), 0.8: (-4, 34, 0), 1.4: (-4, 34, 0), 2.3: (-4, -30, 0), 2.8: (-4, -30, 0), 3.4: (0, 0, 0)})
    body_keys(survey, rig, {0: {}, 0.8: {"twist": 6}, 2.3: {"twist": -6}, 3.4: {}})
    fid.append(survey)
    sleeves = KeyLayer(r, "fidget_sleeves", 2.6)  # settles its sleeves with a flick
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        sleeves.rot(f"{p}_arm_g", {0: (0, 0, 0), 0.4: (-12, 0, -8 * sg), 0.8: (-14, 0, 6 * sg), 1.0: (-14, 0, -4 * sg), 1.6: (0, 0, 0), 2.6: (0, 0, 0)})
        sleeves.rot(f"{p}_sleeve", {0: (0, 0, 0), 0.8: (10, 0, 12 * sg), 1.0: (0, 0, -6 * sg), 1.3: (0, 0, 2 * sg), 1.7: (0, 0, 0)})
    fid.append(sleeves)
    glyph = KeyLayer(r, "fidget_glyph", 3.0)     # two fingers emerge and write a glyph in the air
    glyph.pos("r_hand", {0: (0, 0, 0), 0.4: (0, -4.6, 0), 2.4: (0, -4.6, 0), 2.8: (0, 0, 0)})
    glyph.rot("r_arm_g", {0: (0, 0, 0), 0.5: (-60, 10, 0), 1.0: (-64, -6, 0), 1.5: (-58, 12, 0), 2.0: (-62, 0, 0), 2.6: (0, 0, 0)})
    for k in (2, 3):
        glyph.rot(f"r_finger{k}", {0: (0, 0, 0), 0.4: (70, 0, 0), 2.4: (70, 0, 0), 2.8: (0, 0, 0)})
    glyph.pos("halo2", {0: (0, 0, 0), 0.6: (-6, -4, -9), 2.2: (-6, -4, -9), 2.8: (0, 0, 0)})
    glyph.particle(1.0, "decree", "r_fingertip")
    fid.append(glyph)
    still = KeyLayer(r, "fidget_procession", 3.0)  # utterly still - while its shadow becomes a procession
    for k in range(HALO):
        still.rot(f"halo{k}", {0: (0, 0, 0), 2.6: (0, 0, 360), 3.0: (0, 0, 360)})
    still.particle(0.2, "shadow", "feet")
    fid.append(still)
    picks = [("fidget_survey", "math.mod(math.floor(q.life_time * 1.3), 5) == 0"),
             ("fidget_sleeves", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_glyph", "math.mod(math.floor(q.life_time * 1.3), 5) == 2 && !q.is_item_equipped(0)"),
             ("fidget_procession", "math.mod(math.floor(q.life_time * 1.3), 5) == 3 && q.time_of_day > 0.2 && q.time_of_day < 0.8")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.5),
        "nocturne": A(r, "intro_nocturne", loop="hold", length=0.5),
        "edict": transition(model, r, "intro_edict", "base", "edict", 0.3),
        "court": transition(model, r, "intro_court", "base", "court", 0.9),
        "throne": transition(model, r, "intro_throne", "court", "throne", 1.2),
    }
    intro["court"].bone("grand", scale={0.0: [0.2, 0.05, 0.2], 0.6: [1.06, 1.06, 1.06], 0.9: [1, 1, 1]})
    intro["throne"].bone("throne", scale={0.0: [0.3, 0.02, 0.3], 0.8: [1.05, 1.05, 1.05], 1.2: [1, 1, 1]},
                         pos={0.0: [0, -8, 0], 0.8: [0, 0.4, 0], 1.2: [0, 0, 0]})
    intro["court"].particle(0.0, "decree", "chest")
    intro["throne"].particle(0.0, "decree", "chest")
    for k in range(HALO):
        intro["base"].bone(f"halo{k}", pos={0.0: [0, 0.8, 0], 0.5: [0, 0, 0]})

    edict_loop = Layer(r, "edict_loop", loop=True)
    for k in range(HALO):
        edict_loop.rot(f"halo{k}", None, None, f"{T} * 40")
    for k in (2, 3):
        edict_loop.rot(f"r_finger{k}", 70)          # two fingers extended: the decree gesture
        edict_loop.rot(f"l_finger{k}", 70)
    court_loop = Layer(r, "court_loop", loop=True)
    court_loop.rot("ring0", None, None, f"{T} * 22")
    court_loop.rot("ring1", None, None, f"-{T} * 16")
    for p, side in SIDES:
        court_loop.rot(f"{p}_sleeve", mul(3, S(0.4, 0 if side < 0 else 90)))
    throne_loop = Layer(r, "throne_loop", loop=True)
    throne_loop.rot("throne", None, None, mul(0.6, S(0.2)))
    throne_loop.rot("skull", mul(-2, S(0.1)), None, None)
    for k in (1, 2, 3):
        throne_loop.rot(f"r_finger{k}", 75)           # a single finger raised
    noct_loop = Layer(r, "nocturne_loop", loop=True)
    for k in range(HALO):
        noct_loop.pos(f"halo{k}", None, mul(0.3, S(0.3, k * 40)), None)

    fx = {
        "base": A(r, "fx_base", length=4.0).particle(0.0, "motes", "halo"),
        "nocturne": A(r, "fx_nocturne", length=1.2).particle(0.0, "motes", "halo").particle(0.6, "motes", "chest"),
        "edict": A(r, "fx_edict", length=0.5).particle(0.0, "motes", "halo"),
        "court": A(r, "fx_court", length=0.8).particle(0.0, "motes", "chest"),
        "throne": A(r, "fx_throne", length=0.6).particle(0.0, "motes", "halo").particle(0.3, "motes", "chest"),
    }
    built = [fp, tp, life.anim(), hands.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), edict_loop.anim(), court_loop.anim(), throne_loop.anim(), noct_loop.anim(),
             wait_anim(r, "fidget_wait", 8.0), wait_anim(r, "fidget_rest", 4.0), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-14.0), **fidget_controller(r, picks)}
    loops = {"edict": "edict_loop", "court": "court_loop", "throne": "throne_loop", "nocturne": "nocturne_loop"}
    animate = {}
    for v in ("base", "nocturne", "edict", "court", "throne"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP)]
        if v in ("base", "nocturne"):
            lst += [("appendages", None), ("fidget", TP)]
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP), ("hurt", f"{TP} && q.hurt_time > 0"),
                (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"motes": f"{NS}:royal_mote", "decree": f"{NS}:decree_burst", "shadow": f"{NS}:procession_shadow"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers, "pre": pre_animation(r)}
