"""Race 004 Xenentoma - attachable animation set (v1.2 redesign).

Motion language: stillness, then quick precise jerks.  Sensory limbs sweep and freeze
(0.08-0.15 s snaps, 0.5-1.5 s holds) with a fine 8 Hz tremble at the tips; the head
ticks between directions; the abdomen breathes as a wave running segment by segment.
It stalks upright on its hind legs with high careful steps; when it sprints with empty
hands it drops onto all six limbs and scuttles in a tripod gait.  The mantis-like
middle limbs fold against the chest whenever they hold nothing.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from anims.core import NS, T
from anims.life import (ATK, FALL, LOOK, MOVE, PH, RISE, S, SPR, STILL, TCOS, KeyLayer, Layer, Rig, arm_swing, body,
                        body_keys, chain_wave, fidget_controller, landing_controller, lin, mul, prod, saccade, stride,
                        wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, grounded, mirror, pre_animation, shake, view_anims

R = "xenentoma"
SEG = 12
RIG = Rig("thorax", (0, 12, 0.5), [("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))])
SCUTTLE = 35.0                                    # extra thorax lean on all six limbs


def _lean_offset(p, deg, hip=(0.0, 12.0, 0.5)):
    """Exact displacement of point p when the body leans `deg` forward about the hip."""
    from kit.geo import rot_matrix
    hip = np.array(hip)
    v = np.array(p, float) - hip
    return tuple(np.round(rot_matrix((deg, 0, 0)) @ v - v, 3))
EMPTY_BOTH = "((q.is_item_equipped(0) || q.is_item_equipped(1)) ? 0 : 1)"
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"
SIX = f"(q.is_sprinting ? {EMPTY_BOTH} : 0)"          # all six limbs on the ground
SLEEP = "q.is_sleeping"


def stagger(model, name: str, frm: str, to: str, length: float, order: Dict[str, tuple]):
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
        st, du = order.get(bn, (0.0, length * 0.8))
        keys = {0.0: 1.0, st: 1.0, st + du * 0.7: -0.08, st + du: 0.0, length: 0.0}
        rot = None if np.allclose(dr, 0, atol=0.01) else {t: list(dr * k) for t, k in keys.items()}
        pos = None if np.allclose(dt, 0, atol=0.01) else {t: list(dt * k) for t, k in keys.items()}
        a.bone(bn, rot=rot, pos=pos)
    return a


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    abd = [f"abd{k}" for k in range(SEG)]

    # ------------------------------------------------------------------ life: sensing in snaps and holds
    life = Layer(r, "life", loop=True)
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        seed = 3.1 if side < 0 else 7.7
        # the sensory limbs sweep to a new bearing every ~1.4 s, snapping there, holding, trembling at the tips
        life.rot(f"{p}_sense0", lin([(1.0, saccade(0.7, 10, seed)), (-60, prod(SLEEP, 1)), (-0.12, LOOK)]), None,
                 lin([(sg * 1.0, saccade(0.55, 8, seed + 1)), (sg * -25, prod(SLEEP, 1))]))
        life.rot(f"{p}_sense1", lin([(1.0, saccade(0.9, 9, seed + 2)), (40, prod(SLEEP, 1))]))
        life.rot(f"{p}_sense2", lin([(1.0, saccade(1.1, 8, seed + 3)), (30, prod(SLEEP, 1))]))
        life.rot(f"{p}_sense3", mul(1.5, S(8.0, 0 if side < 0 else 90)), None, mul(1.2, S(7.3, 40)))
        life.rot(f"{p}_palp0", lin([(1.0, saccade(1.6, 12, seed + 4)), (-6, S(0.5))]))
        life.rot(f"{p}_palp1", mul(10, S(2.3, 0 if side < 0 else 120)))
    life.rot("skull", lin([(1.0, saccade(0.45, 6, 11.0)), (8, prod(SLEEP, 1))]), lin([(1.0, saccade(0.4, 10, 5.0))]), None)
    # breathing: a wave down the abdomen (50 degrees of phase per segment, 0.3 Hz), curling up when asleep
    chain_wave(life, abd, "x", 0.9, 0.3, lag=50.0, falloff=1.06)
    for k, a in enumerate(abd):
        life.rot(a, prod(SLEEP, 6 if k > 2 else 2), None, None)
    for k in range(3):
        life.rot(f"tergite{k}", mul(-1.5, S(0.3, -60 * k)))
    life.scale("thorax", lin([(1, 1), (0.012, S(0.3))]), None, lin([(1, 1), (0.012, S(0.3))]))

    # middle limbs: folded against the chest like a mantis while the hand is empty; reach the hand when holding
    fold = Layer(r, "appendages", loop=True)
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hold = HOLD_R if side < 0 else HOLD_L
        free = f"(1 - {hold})"
        fold.rot(f"{p}_mid0", prod(-38, free), None, prod(sg * 12, free))
        fold.rot(f"{p}_mid1", prod(-118, free), None, None)
        fold.rot(f"{p}_claw", prod(30, free), None, None)
        for k in range(3):
            fold.rot(f"{p}_digit{k}", lin([(-25, f"{hold}"), (8, S(1.3, k * 70))]))   # grip when holding

    # ------------------------------------------------------------------ locomotion: high careful steps; six-legged scuttle
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    walk = prod(f"(1 - {SIX})", s)
    six = prod(SIX, s)
    stride(loco, lin([(0.62, f"(1 - {SIX})"), (0.95, SIX)]))
    arm_swing(loco, 0.0)                         # the vanilla arm swing never reaches the folded limbs
    body(loco, rig, lean=lin([(4, walk)]), roll=lin([(1.5, prod(f"math.sin({PH})", walk))]), twist=lin([(0.1, LOOK)]))
    # the scuttle: the thorax tips forward about the hips; head and limb groups follow exactly
    loco.rot("thorax", lin([(SCUTTLE, six)]))
    for g, piv in (("head_g", (0, 24, 0)), ("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))):
        dx, dy, dz = _lean_offset(piv, SCUTTLE)
        loco.pos(g, prod(dx, six) if dx else None, prod(dy, six), prod(dz, six))
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        swing = f"math.max(0, {sg * -1} * math.sin({PH}))"       # the leg is moving forward (in the air)
        loco.rot(f"{p}_tibia0", lin([(-28, prod(swing, s))]))      # lift the foot high on every step
        loco.rot(f"{p}_femur0", lin([(-10, prod(swing, s))]), None, prod(sg * 4, s))
        loco.rot(f"{p}_foot", lin([(24, prod(swing, s))]))
        # scuttle: forelimbs reach to the ground ahead and cycle with the tripod gait
        ph = 0 if side > 0 else 180                               # front-left moves with hind-right (tripod)
        loco.rot(f"{p}_sense0", lin([(114, six), (22, prod(f"math.sin({PH} + {ph})", six)), (-6, walk)]), None,
                 lin([(-sg * 14, six)]))
        loco.rot(f"{p}_sense1", lin([(-34, six), (16, prod(f"math.cos({PH} + {ph})", six))]))
        loco.rot(f"{p}_sense2", lin([(-22, six)]))
        # middle limbs: unfold and reach the ground too (empty hands only - SIX implies it)
        mph = 180 if side > 0 else 0
        loco.rot(f"{p}_mid0", lin([(38 - 58, six), (24, prod(f"math.sin({PH} + {mph})", six))]), None, prod(-sg * 12, six))
        loco.rot(f"{p}_mid1", lin([(118 + 6, six), (-18, prod(f"math.cos({PH} + {mph})", six))]))
    for k, a in enumerate(abd):
        loco.rot(a, lin([(1.5, prod(f"math.sin({PH} * 2 + {k * 25})", s)), (-3.0 if k < 3 else -1.5, six)]),
                 lin([(1.2 + 0.25 * k, prod(f"math.sin({PH} + {k * 20})", walk))]), None)
    loco.rot("tail_g", lin([(14, six)]))                          # the abdomen lifts in line with the tipped thorax
    loco.rot("skull", lin([(-4, walk), (8, six)]))               # the cone points ahead / down at the ground
    grounded(model, loco, rig, r, harmonics=12)          # six-legged gait: a richer foot floor

    air = Layer(r, "airborne", loop=True)        # legs fold, forelimbs spread, abdomen lifts
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        air.rot(f"{p}_femur0", lin([(-18, RISE), (6, FALL)]), None, prod(sg * 8, RISE))
        air.rot(f"{p}_tibia0", lin([(-30, RISE), (12, FALL)]))
        air.rot(f"{p}_sense0", lin([(-10, RISE), (12, FALL)]), None, lin([(sg * 12, RISE)]))
    for k, a in enumerate(abd):
        air.rot(a, lin([(3, RISE), (-2, FALL)]))

    land = KeyLayer(r, "land", 0.4)
    land_hard = KeyLayer(r, "land_hard", 0.6)
    for kl, g in ((land, 0.6), (land_hard, 1.0)):
        L = kl.length
        body_keys(kl, rig, {0: {"bob": -1.2 * g, "lean": 5 * g}, 0.1: {"bob": -1.6 * g, "lean": 6 * g}, 0.3: {"bob": 0.2}, L: {}})
        for p, side in SIDES:
            kl.rot(f"{p}_tibia0", {0: (14 * g, 0, 0), 0.1: (18 * g, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_sense0", {0: (14 * g, 0, 0), 0.12: (-6 * g, 0, 0), L: (0, 0, 0)})
        for k, a in enumerate(abd):
            kl.rot(a, {0: (-4 * g, 0, 0), 0.15: (3 * g, 0, 0), L: (0, 0, 0)})
    land_hard.particle(0.0, "landdust", "r_step").particle(0.0, "landdust", "l_step")

    atk = Layer(r, "attack", loop=True)          # the stylet stabs out of the cone; the claws snap
    atk.pos("stylet", None, None, prod(-2.75, ATK))
    atk.rot("skull", prod(10, ATK))
    atk.rot("r_mid1", prod(-20, ATK))

    hurt = KeyLayer(r, "hurt", 0.5)              # recoil: forelimbs fold in, abdomen curls, the head jerks
    body_keys(hurt, rig, {0: {}, 0.05: {"lean": -6}, 0.2: {"lean": 2}, 0.5: {}})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.rot(f"{p}_sense0", {0: (0, 0, 0), 0.05: (36, 0, -sg * 14), 0.3: (14, 0, -sg * 5), 0.5: (0, 0, 0)})
        hurt.rot(f"{p}_sense1", {0: (0, 0, 0), 0.05: (30, 0, 0), 0.5: (0, 0, 0)})
    for k, a in enumerate(abd):
        hurt.rot(a, {0: (0, 0, 0), 0.06: (5, 0, 0), 0.3: (-2, 0, 0), 0.5: (0, 0, 0)})
    hurt.rot("skull", {0: (0, 0, 0), 0.05: (-12, 8, 0), 0.25: (3, -3, 0), 0.5: (0, 0, 0)})

    # ------------------------------------------------------------------ idle behaviours
    fid = []
    probe = KeyLayer(r, "fidget_probe", 2.4)     # head down, the stylet tastes the soil twice
    probe.rot("skull", {0: (0, 0, 0), 0.3: (32, 0, 0), 1.9: (32, 0, 0), 2.4: (0, 0, 0)})
    probe.pos("stylet", {0: (0, 0, 0), 0.5: (0, 0, 0), 0.6: (0, 0, -2.5), 0.9: (0, 0, -2.5), 1.0: (0, 0, 0),
                         1.2: (0, 0, 0), 1.3: (0, 0, -2.5), 1.6: (0, 0, -2.5), 1.7: (0, 0, 0)})
    body_keys(probe, rig, {0: {}, 0.3: {"lean": 8}, 1.9: {"lean": 8}, 2.4: {}})
    fid.append(probe)
    groom = KeyLayer(r, "fidget_groom", 3.0)     # draws the right forelimb down through a middle claw
    groom.rot("r_sense0", {0: (0, 0, 0), 0.35: (95, 0, 20), 1.0: (100, 0, 24), 1.3: (70, 0, 14), 1.7: (100, 0, 24), 2.3: (0, 0, 0)})
    groom.rot("r_sense1", {0: (0, 0, 0), 0.35: (-30, 0, 0), 1.7: (-30, 0, 0), 2.3: (0, 0, 0)})
    groom.rot("r_mid0", {0: (0, 0, 0), 0.4: (-12, 0, 0), 1.7: (-12, 0, 0), 2.2: (0, 0, 0)})
    groom.rot("skull", {0: (0, 0, 0), 0.4: (14, 10, 0), 1.7: (14, 10, 0), 2.3: (0, 0, 0)})
    fid.append(groom)
    listen = KeyLayer(r, "fidget_listen", 2.8)   # freezes; both forelimbs snap toward a tremor, hold, snap to another
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        listen.rot(f"{p}_sense0", {0: (0, 0, 0), 0.25: (0, 0, 0), 0.35: (-14, 0, sg * -10), 1.2: (-14, 0, sg * -10),
                                   1.3: (-8, 0, sg * 14), 2.2: (-8, 0, sg * 14), 2.8: (0, 0, 0)})
    listen.rot("skull", {0: (0, 0, 0), 0.35: (6, -22, 0), 1.2: (6, -22, 0), 1.3: (6, 20, 0), 2.2: (6, 20, 0), 2.8: (0, 0, 0)})
    for k, a in enumerate(abd):
        listen.rot(a, {0: (0, 0, 0), 0.3: (-1.5, 0, 0), 2.4: (-1.5, 0, 0), 2.8: (0, 0, 0)})
    listen.particle(0.35, "senseping", "r_sensilla").particle(1.3, "senseping", "l_sensilla")
    fid.append(listen)
    ripple = KeyLayer(r, "fidget_ripple", 2.6)   # an anamorphic flex: the segments telescope out and back, front to rear
    for k, a in enumerate(abd):
        t0 = 0.2 + 0.08 * k
        ripple.scale(a, {0: (1, 1, 1), t0: (1, 1, 1), t0 + 0.15: (1.0, 1.0, 1.25), t0 + 0.45: (1, 1, 1), 2.6: (1, 1, 1)})
        ripple.rot(a, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.15: (3, 0, 0), t0 + 0.45: (0, 0, 0), 2.6: (0, 0, 0)})
    fid.append(ripple)
    picks = [("fidget_probe", "math.mod(math.floor(q.life_time * 1.3), 5) == 0"),
             ("fidget_groom", "math.mod(math.floor(q.life_time * 1.3), 5) == 1 && !q.is_item_equipped(0)"),
             ("fidget_listen", "math.mod(math.floor(q.life_time * 1.3), 5) == 2"),
             ("fidget_ripple", "math.mod(math.floor(q.life_time * 1.3), 5) == 3")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.4),
        "survey": stagger(model, "intro_survey", "base", "survey", 0.35, {}),
        "glide": stagger(model, "intro_glide", "base", "glide", 0.22, {}),
        "teneral": stagger(model, "intro_teneral", "exuvia", "teneral", 1.0, {}),
    }
    for p in ("r", "l"):
        intro["base"].bone(f"{p}_sense0", rot={0.0: [12, 0, 0], 0.12: [-5, 0, 0], 0.4: [0, 0, 0]})
    intro["teneral"].bone("thorax", scale={0.0: [0.88, 0.88, 0.88], 0.6: [1.03, 1.03, 1.03], 1.0: [1, 1, 1]})
    intro["teneral"].particle(0.0, "fluid", "back").particle(0.3, "fluid", "back")
    # surge: the segments slide out one after another (30 ms apart), the abdomen arches over the back,
    # then strikes three times over the shoulder at 0.6 / 0.9 / 1.2 s with a short recoil before each
    surge = stagger(model, "intro_surge", "base", "surge", 1.6, {a: (0.03 * k, 0.24) for k, a in enumerate(abd)})
    for k, a in enumerate(abd):
        if k < 4:
            continue
        amp = 5 + (k - 4) * 2.0
        keys = {0: [0, 0, 0], 0.55: [0, 0, 0]}
        for ts in (0.6, 0.9, 1.2):
            keys[round(ts - 0.06, 3)] = [-amp * 0.5, 0, 0]
            keys[ts] = [amp, 0, 0]
            keys[round(ts + 0.1, 3)] = [-amp * 0.15, 0, 0]
        keys[1.45] = [0, 0, 0]
        prev = surge.bones.get(a, {}).get("rotation")
        if isinstance(prev, dict):
            merged = {}
            times = sorted({float(t) for t in prev} | set(keys))
            for t in times:
                pv = np.array(prev.get(f"{t:.4g}", _interp(prev, t)), float)
                kv = np.array(keys.get(t, _interp_k(keys, t)), float)
                merged[t] = list(pv + kv)
            surge.bone(a, rot=merged)
        else:
            surge.bone(a, rot=keys)
    surge.particle(0.6, "strike", "telson").particle(0.9, "strike", "telson").particle(1.2, "strike", "telson")
    intro["surge"] = surge

    survey_loop = Layer(r, "survey_loop", loop=True)
    for p, side in SIDES:
        survey_loop.rot(f"{p}_sense0", lin([(1.0, saccade(1.2, 8, 2.0 if side < 0 else 4.0))]), None,
                        mirror(side, lin([(1.0, saccade(0.9, 10, 9.0))])))
        survey_loop.rot(f"{p}_sense3", mul(3.0, S(9.0, 0 if side < 0 else 90)))
        survey_loop.scale(f"{p}_sense3", lin([(1, 1), (0.12, S(2.0))]), lin([(1, 1), (0.12, S(2.0))]), lin([(1, 1), (0.12, S(2.0))]))
    survey_loop.rot("skull", None, lin([(1.0, saccade(0.8, 18, 3.3))]), None)
    survey_loop.particle(0.0, "senseping", "r_sensilla")
    survey_loop.kw["length"] = 1.0
    glide_loop = Layer(r, "glide_loop", loop=True)
    for p, side in SIDES:
        glide_loop.rot(f"{p}_tibia0", None, None, mul(10, S(6.0, 0 if side < 0 else 180)))
    chain_wave(glide_loop, abd, "y", 2.5, 3.0, lag=40.0, falloff=1.08)
    ten_loop = Layer(r, "teneral_loop", loop=True)   # soft new cuticle: tremors until it hardens
    for p, side in SIDES:
        ten_loop.rot(f"{p}_sense0", mul(2.5, S(5.1, 0 if side < 0 else 70)))
        ten_loop.rot(f"{p}_sense1", mul(3, S(4.3, 20)))
    for k, a in enumerate(abd):
        ten_loop.rot(a, None, mul(1.0, S(3.7, k * 40)), None)

    fx = {
        "base": A(r, "fx_base", length=3.4).particle(0.0, "motes", "r_sensilla").particle(1.7, "motes", "l_sensilla"),
        "survey": A(r, "fx_survey", length=0.8).particle(0.0, "motes", "r_sensilla").particle(0.4, "motes", "l_sensilla"),
        "glide": A(r, "fx_glide", length=0.2).particle(0.0, "stepdust", "r_step").particle(0.1, "stepdust", "l_step"),
        "surge": A(r, "fx_surge", length=0.8).particle(0.0, "motes", "telson"),
        "teneral": A(r, "fx_teneral", length=0.7).particle(0.0, "fluid", "back"),
    }
    built = [fp, tp, life.anim(), fold.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), survey_loop.anim(), glide_loop.anim(), ten_loop.anim(),
             wait_anim(r, "fidget_wait", 6.0), wait_anim(r, "fidget_rest", 3.0), *[f.anim() for f in fid],
             *intro.values(), *fx.values()]
    controllers = {**landing_controller(r), **fidget_controller(r, picks)}
    loops = {"survey": ("survey_loop", TP), "glide": ("glide_loop", TP), "teneral": ("teneral_loop", TP)}
    animate = {}
    for v in ("base", "survey", "glide", "surge", "teneral"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP), ("appendages", None)]
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


def _interp(chan: dict, t: float):
    """Linear value of a keyframe channel {'t': [x,y,z]} at time t."""
    pts = sorted((float(k), np.array(v, float)) for k, v in chan.items())
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * ((t - t0) / max(t1 - t0, 1e-9))
    return pts[-1][1]


def _interp_k(keys: dict, t: float):
    return _interp({str(k): v for k, v in keys.items()}, t)
