"""Race 004 Xenentoma - attachable animation set (see anims/life.py for the layer system)."""
from __future__ import annotations

from typing import Dict

import numpy as np

from anims.core import NS, osc
from anims.life import (ATK, BUMP, CSTEP, EMPTY_L, EMPTY_R, FALL, LOOK, MOVE, PH, POS, RISE, S, SPR, SQ, STEP,
                        STILL, TCOS, TURN, WALKING, KeyLayer, Layer, Rig, arm_swing, body, body_keys,
                        fidget_controller, landing_controller, lin, mul, prod, stride, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, grounded, mirror, pre_animation, shake, transition, view_anims

R = "xenentoma"
RIG = Rig("thorax", (0, 12, 0.5), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
SEG = 12


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    sleeping = "q.is_sleeping"

    # ------------------------------------------------------------------ life: restless sensing
    life = Layer(r, "life", loop=True)
    br = S(0.42)
    life.scale("thorax", lin([(1, 1), (0.012, br)]), None, lin([(1, 1), (0.02, br)]))
    for k in range(3):
        for p, side in SIDES:
            life.rot(f"tergite_{p}{k}", mul(-2.5, S(0.42, -30 * k)), mirror(side, mul(-2.0, S(0.42, -30 * k))), None)
    body(life, rig, lean=prod(1.2, S(0.08, 40), STILL), roll=prod(1.6, S(0.1), STILL), twist=prod(2.0, S(0.07, 90), STILL))
    life.rot("head_g", prod(lin([(3, SQ(0.21, 30, 5)), (2, S(0.33, 60))]), STILL),
             prod(lin([(7, SQ(0.17, 0, 4)), (3, SQ(0.43, 100, 6))]), STILL),
             prod(lin([(5, SQ(0.11, 200, 4))]), STILL))
    life.pos("stylet", None, None, mul(-1.1, BUMP(4.7, 0.5)))
    for p, side in SIDES:
        f = 1.0 if side < 0 else 1.13          # the two forelimbs never move in step
        ph = 0 if side < 0 else 140
        # sensory forelimbs: constant exploratory sweeps, sharp re-orientations, tarsal tremor
        life.rot(f"{p}_sense0", lin([(9, S(0.37 * f, ph)), (6, SQ(0.23 * f, ph + 60, 5)), (60, prod(sleeping, 1)), (-0.15, LOOK)]),
                 mirror(side, lin([(11, S(0.29 * f, ph + 30)), (-40, prod(sleeping, 1))])) if side < 0 else
                 lin([(-11, S(0.29 * f, ph + 30)), (40, prod(sleeping, 1))]),
                 None)
        life.rot(f"{p}_sense0", None, mul(0.25, LOOK), None)
        life.rot(f"{p}_sense1", lin([(11, S(0.53 * f, ph + 90)), (30, prod(sleeping, 1))]))
        life.rot(f"{p}_sense2", lin([(8, S(0.9 * f, ph + 20)), (3, S(7.0 * f, ph)), (20, prod(sleeping, 1))]))
        life.rot(f"{p}_palp", lin([(9, prod(S(6.0, ph), BUMP(2.3, 0.4, 0.7 * (1 if side < 0 else 2))))]))
        for k in range(3):
            life.rot(f"{p}_digit{k}", lin([(-25, BUMP(5.3, 0.6, k * 0.12 + (0 if side < 0 else 2.4)))]))
    for k in range(SEG):
        life.rot(f"abd{k}", lin([(1.2, S(0.17, -20 * k)), (-5, prod(sleeping, 1))]),
                 lin([(1.5 + 0.45 * k, S(0.21, -25 * k)), (9, prod(sleeping, 1))]), None)
        life.pos(f"abd{k}", None, None, mul(0.06, S(0.42, -35 * k)))

    detail = Layer(r, "detail", loop=True)    # visible in first person too: the gripping claws flex
    for p, side in SIDES:
        detail.rot(f"{p}_claw", osc(0.4, 3, 0 if side < 0 else 90))

    # ------------------------------------------------------------------ locomotion: arthropod gait
    loco = Layer(r, "locomotion", loop=True)
    keep = 0.5
    stride(loco, keep)
    s = MOVE
    ss = prod(SPR, s)
    walk = prod(WALKING, s)
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"
        lift = prod(POS(sw), s)
        loco.rot(f"{p}_femur", prod(-10, lift), None, mirror(side, prod(14, lift)))
        loco.rot(f"{p}_tibia", prod(26, lift))
        loco.rot(f"{p}_tarsus", lin([(1.0, prod(side * keep * 1.4, TCOS)), (-18, lift)]))
        for k in range(2):
            loco.rot(f"{p}_toe{k}", prod(-14, lift))
        # forelimbs tap the ground ahead alternately while walking, fold back when sprinting
        loco.rot(f"{p}_sense0", lin([(-10, s), (-24, ss), (10, prod(f"math.sin({PH} + {0 if side < 0 else 180})", walk))]),
                 mirror(side, lin([(9, prod(f"math.sin({PH} + {0 if side < 0 else 180})", walk)), (18, ss)])), None)
        loco.rot(f"{p}_sense1", lin([(-6, ss)]))
        # empty middle limbs help with the run (they swing harder instead of less)
        e = EMPTY_R if side < 0 else EMPTY_L
        loco.rot(f"{p}_arm_g", prod(side * -1.0, TCOS, e, lin([(-0.2, walk), (0.55, ss)])))
        loco.rot(f"{p}_mid1", prod(-18, ss, e))
    body(loco, rig,
         lean=lin([(6, s), (12, ss)]),
         roll=lin([(2.5, prod(STEP(), s)), (4, prod(TURN, s))]),
         twist=lin([(-4, prod(CSTEP(), s)), (0.1, LOOK)]))
    grounded(model, loco, rig, r)
    loco.rot("head_g", lin([(-3, s), (-6, ss)]), prod(3, CSTEP(), s), None)
    for k in range(SEG):
        loco.rot(f"abd{k}", lin([(2.5, prod(f"math.sin({PH} * 2 - {60 + 25 * k})", s)), (6 if k == 0 else 0, ss)]),
                 lin([(4 + 1.2 * k, prod(CSTEP(-40 - 30 * k), s)), (-2.5 * (1 + 0.3 * k), prod(TURN, s))]), None)

    # ------------------------------------------------------------------ airborne: the abdomen telescopes
    air = Layer(r, "airborne", loop=True)
    for k in range(SEG):
        air.pos(f"abd{k}", None, None, lin([(-0.28, RISE), (0.22, FALL)]))
        air.rot(f"abd{k}", lin([(-3, RISE), (2.5, FALL)]))
    for p, side in SIDES:
        air.rot(f"{p}_femur", prod(-12, RISE), None, mirror(side, lin([(18, RISE), (6, FALL)])))
        air.rot(f"{p}_tibia", lin([(30, RISE), (-6, FALL)]))
        air.rot(f"{p}_sense0", lin([(-26, FALL), (10, RISE)]), mirror(side, mul(16, FALL)), None)
    body(air, rig, lean=lin([(-5, RISE), (6, FALL)]))

    land = KeyLayer(r, "land", 0.45)
    land_hard = KeyLayer(r, "land_hard", 0.65)
    for kl, g in ((land, 1.0), (land_hard, 1.45)):
        L = kl.length
        t1, t2 = 0.08 * g, 0.26 * g
        for p, side in SIDES:
            sg = -1 if side < 0 else 1
            kl.rot(f"{p}_femur", {0: (0, 0, -16 * g * sg), t1: (0, 0, -20 * g * sg), t2: (0, 0, 3 * sg), L: (0, 0, 0)})
            kl.rot(f"{p}_tibia", {0: (14 * g, 0, 0), t1: (18 * g, 0, 0), t2: (-2, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_sense0", {0: (0, 0, 0), t1: (-22 * g, -14 * sg * g, 0), 0.3 * g: (6, 0, 0), L: (0, 0, 0)})
            kl.particle(0.0, "landdust" if g > 1 else "stepdust", f"{p}_step")
        body_keys(kl, rig, {0: {"bob": -1.2 * g, "lean": 7 * g}, t1: {"bob": -1.5 * g, "lean": 9 * g}, t2: {"bob": 0.3, "lean": -2}, L: {}})
        for k in range(SEG):
            kl.rot(f"abd{k}", {0: (-6 * g, 0, 0), 0.12 * g + k * 0.012: (-8 * g, 0, 0), 0.32 * g + k * 0.012: (3, 0, 0), L: (0, 0, 0)})

    # ------------------------------------------------------------------ attack: the stylet stabs
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(7, ATK), twist=prod(-6, ATK))
    atk.rot("head_g", prod(9, ATK))
    atk.pos("stylet", None, None, prod(-3.6, ATK))
    for p, side in SIDES:
        atk.rot(f"{p}_sense0", prod(-18, ATK), mirror(side, prod(16, ATK)), None)
    for k in range(SEG):
        atk.rot(f"abd{k}", prod(3, ATK))

    # ------------------------------------------------------------------ hurt: curl and retract
    hurt = KeyLayer(r, "hurt", 0.55)
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -7, "bob": -0.6}, 0.22: {"lean": 3}, 0.55: {}})
    hurt.rot("head_g", {0: (0, 0, 0), 0.05: (-12, 0, 0), 0.25: (5, 0, 0), 0.55: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.rot(f"{p}_sense0", {0: (0, 0, 0), 0.05: (42, 18 * sg, 0), 0.35: (20, 8 * sg, 0), 0.55: (0, 0, 0)})
        hurt.rot(f"{p}_sense1", {0: (0, 0, 0), 0.05: (35, 0, 0), 0.55: (0, 0, 0)})
        for k in range(3):
            hurt.rot(f"tergite_{p}{k}", {0: (0, 0, 0), 0.06: (0, -14 * sg, 0), 0.3: (0, 0, 0)})
    for k in range(SEG):
        hurt.rot(f"abd{k}", {0: (0, 0, 0), 0.05 + k * 0.01: (-7, 5, 0), 0.3: (-2, -2, 0), 0.55: (0, 0, 0)})

    # ------------------------------------------------------------------ idle behaviours
    fid = []
    probe = KeyLayer(r, "fidget_probe", 2.6)     # pierces the soil with the stylet, tasting for fungus
    probe.rot("head_g", {0: (0, 0, 0), 0.5: (30, 0, 0), 1.9: (30, 0, 0), 2.4: (0, 0, 0), 2.6: (0, 0, 0)})
    body_keys(probe, rig, {0: {}, 0.5: {"lean": 14, "bob": -0.8}, 1.9: {"lean": 14, "bob": -0.8}, 2.4: {}, 2.6: {}})
    probe.pos("stylet", {0: (0, 0, 0), 0.6: (0, 0, 0), 0.8: (0, 0, -3.2), 1.0: (0, 0, -2.4), 1.2: (0, 0, -3.4), 1.4: (0, 0, -2.6),
                         1.6: (0, 0, -3.3), 1.9: (0, 0, 0), 2.6: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        probe.rot(f"{p}_sense0", {0: (0, 0, 0), 0.5: (28, 30 * -sg, 0), 1.9: (28, 30 * -sg, 0), 2.4: (0, 0, 0)})
        probe.rot(f"{p}_sense2", {0: (0, 0, 0), 0.6: (20, 0, 0), 1.8: (20, 0, 0), 2.3: (0, 0, 0)})
    for k in range(SEG):
        probe.rot(f"abd{k}", {0: (0, 0, 0), 0.6: (3, 0, 0), 1.8: (3, 0, 0), 2.4: (0, 0, 0)})
    fid.append(probe)
    groom = KeyLayer(r, "fidget_groom", 3.2)     # draws each forelimb through a middle claw to clean its sensilla
    for p, side, t0 in (("r", -1, 0.2), ("l", 1, 1.6)):
        sg = -1 if side < 0 else 1
        groom.rot(f"{p}_sense0", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.35: (46, -30 * sg, 0), t0 + 1.05: (46, -30 * sg, 0), t0 + 1.4: (0, 0, 0), 3.2: (0, 0, 0)})
        groom.rot(f"{p}_arm_g", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.35: (-62, 0, -22 * sg), t0 + 0.7: (-48, 0, -22 * sg),
                                 t0 + 1.05: (-62, 0, -22 * sg), t0 + 1.4: (0, 0, 0), 3.2: (0, 0, 0)})
        for k in range(3):
            groom.rot(f"{p}_digit{k}", {0: (0, 0, 0), t0 + 0.35: (0, 0, 0), t0 + 0.5: (-30, 0, 0), t0 + 1.0: (-30, 0, 0), t0 + 1.2: (0, 0, 0)})
    groom.rot("head_g", {0: (0, 0, 0), 0.4: (10, 14, 0), 1.5: (10, 14, 0), 1.8: (10, -14, 0), 2.9: (10, -14, 0), 3.2: (0, 0, 0)})
    fid.append(groom)
    listen = KeyLayer(r, "fidget_listen", 2.6)   # freezes, raises both forelimbs toward a tremor, snaps to another
    for p, side in SIDES:
        listen.rot(f"{p}_sense0", {0: (0, 0, 0), 0.25: (-34, 26, 0), 1.1: (-34, 26, 0), 1.3: (-30, -24, 0), 2.1: (-30, -24, 0), 2.6: (0, 0, 0)})
        listen.rot(f"{p}_sense2", {**{round(0.3 + k * 0.05, 3): (3.5 * (-1) ** k, 0, 0) for k in range(34)}, 2.6: (0, 0, 0)})
    listen.rot("head_g", {0: (0, 0, 0), 0.25: (-4, 22, 0), 1.1: (-4, 22, 0), 1.3: (-4, -20, 0), 2.1: (-4, -20, 0), 2.6: (0, 0, 0)})
    body_keys(listen, rig, {0: {}, 0.3: {"lean": -4, "twist": 6}, 1.2: {"lean": -4, "twist": -6}, 2.1: {"lean": -4, "twist": -6}, 2.6: {}})
    fid.append(listen)
    ripple = KeyLayer(r, "fidget_ripple", 2.8)   # an anamorphic flex: segments telescope out and back, front to rear
    for k in range(SEG):
        t0 = 0.15 + k * 0.08
        ripple.pos(f"abd{k}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.25: (0, 0, 0.55), t0 + 0.55: (0, 0, -0.15), t0 + 0.8: (0, 0, 0), 2.8: (0, 0, 0)})
        ripple.rot(f"abd{k}", {0: (0, 0, 0), 1.3: (0, 0, 0), 1.6 + k * 0.03: (0, 10, 0), 1.95 + k * 0.03: (0, -10, 0), 2.3 + k * 0.03: (0, 3, 0), 2.8: (0, 0, 0)})
    for k in range(3):
        for p, side in SIDES:
            ripple.rot(f"tergite_{p}{k}", {0: (0, 0, 0), 0.2 + k * 0.1: (-6, 0, 0), 0.6 + k * 0.1: (0, 0, 0), 2.8: (0, 0, 0)})
    fid.append(ripple)
    picks = [("fidget_probe", "math.mod(math.floor(q.life_time * 1.7), 5) == 0"),
             ("fidget_groom", "math.mod(math.floor(q.life_time * 1.7), 5) == 1 && !q.is_item_equipped(0) && !q.is_item_equipped(1)"),
             ("fidget_listen", "math.mod(math.floor(q.life_time * 1.7), 5) == 2"),
             ("fidget_ripple", "math.mod(math.floor(q.life_time * 1.7), 5) == 3")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.4),
        "survey": transition(model, r, "intro_survey", "base", "survey", 0.45),
        "glide": transition(model, r, "intro_glide", "base", "glide", 0.18),
        "teneral": transition(model, r, "intro_teneral", "exuvia", "teneral", 1.0),
    }
    for p in ("r", "l"):
        intro["base"].bone(f"{p}_sense0", rot={0.0: [10, 0, 0], 0.2: [-6, 0, 0], 0.4: [0, 0, 0]})
    intro["teneral"].bone("thorax", scale={0.0: [0.86, 0.86, 0.86], 0.6: [1.04, 1.04, 1.04], 1.0: [1, 1, 1]})
    intro["teneral"].bone("head_g", scale={0.0: [0.8, 0.8, 0.8], 0.7: [1.03, 1.03, 1.03], 1.0: [1, 1, 1]})
    intro["teneral"].particle(0.0, "fluid", "back").particle(0.3, "fluid", "back")
    surge = KeyLayer(r, "intro_surge", 1.6, loop="hold")
    # 0.0-0.55 s: the segments extend in sequence from the front; strikes at 0.6 / 0.9 / 1.2 s
    for k in range(SEG):
        b = model.bones[f"abd{k}"]
        rest_b = np.array(model.bone_rot(f"abd{k}", "base"), float)
        rest_s = np.array(model.bone_rot(f"abd{k}", "surge"), float)
        d_rot = rest_b - rest_s
        t0 = 0.03 * k
        surge.rot(f"abd{k}", {0: tuple(d_rot), t0: tuple(d_rot), t0 + 0.24: (0, 0, 0)})
        surge.pos(f"abd{k}", {0: (0, 0, -0.9), t0: (0, 0, -0.9), t0 + 0.24: (0, 0, 0)})
        if k >= 4:
            amp = 6 + (k - 4) * 2.5
            keys = {0: (0, 0, 0), 0.55: (0, 0, 0)}
            for ts in (0.6, 0.9, 1.2):
                keys[round(ts - 0.06, 3)] = (-amp * 0.4, 0, 0)
                keys[ts] = (amp, 0, 0)
                keys[round(ts + 0.12, 3)] = (-amp * 0.2, 0, 0)
            keys[1.45] = (0, 0, 0)
            surge.rot(f"abd{k}", keys)
    surge.particle(0.6, "strike", "telson").particle(0.9, "strike", "telson").particle(1.2, "strike", "telson")
    intro["surge"] = surge

    survey_loop = Layer(r, "survey_loop", loop=True)
    for p, side in SIDES:
        survey_loop.rot(f"{p}_sense0", mul(6, S(0.6, 0 if side < 0 else 90)), mirror(side, mul(14, S(0.35, 0 if side < 0 else 60))), None)
        survey_loop.rot(f"{p}_sense2", lin([(5, S(5.5)), (6, S(0.8))]))
    survey_loop.rot("head_g", None, mul(12, SQ(0.3, 0, 3)), None)
    survey_loop.particle(0.0, "senseping", "r_sensilla")
    survey_loop.kw["length"] = 1.0
    glide_loop = Layer(r, "glide_loop", loop=True)
    for p, side in SIDES:
        glide_loop.rot(f"{p}_tibia", mul(16, S(6.0, 0 if side < 0 else 180)))
        glide_loop.rot(f"{p}_femur", mul(10, S(6.0, 90 if side < 0 else 270)))
    for k in range(SEG):
        glide_loop.rot(f"abd{k}", None, mul(3 + 0.6 * k, S(3.0, -40 * k)), None)
    ten_loop = Layer(r, "teneral_loop", loop=True)   # soft new cuticle: tremors until it hardens
    for p, side in SIDES:
        ten_loop.rot(f"{p}_sense0", mul(2.5, S(5.1, 0 if side < 0 else 70)))
        ten_loop.rot(f"{p}_sense1", mul(3, S(4.3, 20)))
    for k in range(SEG):
        ten_loop.rot(f"abd{k}", None, mul(1.2, S(3.7, k * 40)), None)

    fx = {
        "base": A(r, "fx_base", length=3.4).particle(0.0, "motes", "r_sensilla").particle(1.7, "motes", "l_sensilla"),
        "survey": A(r, "fx_survey", length=0.8).particle(0.0, "motes", "r_sensilla").particle(0.4, "motes", "l_sensilla"),
        "glide": A(r, "fx_glide", length=0.2).particle(0.0, "stepdust", "r_step").particle(0.1, "stepdust", "l_step"),
        "surge": A(r, "fx_surge", length=0.8).particle(0.0, "motes", "telson"),
        "teneral": A(r, "fx_teneral", length=0.7).particle(0.0, "fluid", "back"),
    }
    built = [fp, tp, life.anim(), detail.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), survey_loop.anim(), glide_loop.anim(), ten_loop.anim(),
             wait_anim(r, "fidget_wait", 6.0), wait_anim(r, "fidget_rest", 3.0), *[f.anim() for f in fid]]
    for k, a in intro.items():
        built.append(a.anim() if isinstance(a, KeyLayer) else a)
    built += list(fx.values())
    controllers = {**landing_controller(r), **fidget_controller(r, picks)}
    loops = {"survey": ("survey_loop", TP), "glide": ("glide_loop", TP), "teneral": ("teneral_loop", TP)}
    animate = {}
    for v in ("base", "survey", "glide", "surge", "teneral"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP), ("detail", None)]
        if v in ("base", "teneral"):
            lst.append(("fidget", TP))
        if v != "glide":
            lst.append(("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"))
        lst += [("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append(loops[v])
        animate[v] = lst
    particles = {"motes": f"{NS}:sensilla_mote", "senseping": f"{NS}:sensilla_ripple", "fluid": f"{NS}:molt_fluid",
                 "strike": f"{NS}:surge_strike", "stepdust": f"{NS}:step_dust", "landdust": f"{NS}:land_dust"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers, "pre": pre_animation(r)}
