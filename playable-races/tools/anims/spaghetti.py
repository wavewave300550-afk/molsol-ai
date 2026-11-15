"""Race 005 Flying Spaghetti Monster - attachable animation set."""
from __future__ import annotations

from typing import Dict

from anims.core import NS, T, osc
from anims.life import (ATK, BUMP, FALL, LOOK, MOVE, PH, POS, RISE, S, SPR, SQ, STILL, TURN, KeyLayer, Layer, Rig, body,
                        body_keys, fidget_controller, landing_controller, lin, mul, prod, shared_vars, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, mirror, shake, view_anims
from models.spaghetti import CENTER, GROUPS, HANG

R = "spaghetti"
RIG = Rig("mass", CENTER, [("r_arm_g", (-5, 22, 0)), ("l_arm_g", (5, 22, 0))], legs=(), tail=None)
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    sleeping = "q.is_sleeping"

    # ------------------------------------------------------------------ life: hovering, circulating noodles
    life = Layer(r, "life", loop=True)
    hover = lin([(0.8, S(0.45)), (0.3, S(1.1, 40))])
    life.pos("torso_g", None, hover)
    for k in range(GROUPS):
        sgn = 1 if k % 2 == 0 else -1
        life.rot(f"twist{k}", mul(2.0, S(0.13 + 0.03 * k, k * 60)), f"{T} * {sgn * (7 + 2 * k)}", mul(1.5, S(0.17, k * 40)))
    body(life, rig, lean=prod(2, S(0.09, 30), STILL), roll=prod(2.5, S(0.11), STILL))
    for k in range(HANG):
        for j in range(3):
            nm = f"hang{k}" if j == 0 else f"hang{k}_{j}"
            life.rot(nm, mul(5 + 3 * j, S(0.5 + 0.07 * k, k * 50 - j * 40)), None, mul(4 + 2 * j, S(0.37 + 0.05 * k, k * 70 - j * 35)))
    for k in range(4):
        life.rot(f"trail{k}", mul(6, S(0.4, k * 80)), mul(8, S(0.31, k * 50)), None)
    for p, side in SIDES:
        f = 1.0 if side < 0 else 1.17
        # each eye has its own mind: separate saccades, separate blinks
        life.rot(f"eye_{p}", lin([(0.5, "math.clamp(q.target_x_rotation, -50, 50)"), (10, SQ(0.23 * f, 0 if side < 0 else 120, 5)),
                                  (-6, prod(SQ(0.07 * f, 30 if side < 0 else 200, 3), STILL))]),
                 lin([(0.5, LOOK), (14, SQ(0.17 * f, 60 if side < 0 else 10, 5)), (8, SQ(0.41 * f, 90, 6))]), None)
        life.scale(f"lid_{p}", None, lin([(1, 1), (11, f"math.max({blink(3.9 * f, 6.6 * f, 0.18, 1.3 + side)}, {sleeping})")]), None)
        for j in range(3):
            life.rot(f"stalk_{p}{j}", lin([(4, S(0.27 * f, j * 50)), (35 if j == 0 else 10, prod(sleeping, 1))]), None,
                     mirror(side, mul(5, S(0.21 * f, 40 + j * 60))))
        life.rot(f"meatball_{p}", mul(4, S(0.3, 0 if side < 0 else 90)), f"{T} * {14 * side}", None)
        life.pos(f"meatball_{p}", None, mul(0.35, S(0.6, 0 if side < 0 else 150)))
    life.rot("sauce", None, mul(6, S(0.1)), None)
    for k in range(4):
        # sauce sometimes creeps back UP its drip, against gravity
        life.pos(f"drip{k}", None, lin([(0.3, S(0.7, k * 90)), (2.4, BUMP(6.1, 1.8, k * 1.4))]))
        life.scale(f"drip{k}", 1, lin([(1, 1), (0.4, S(0.9, k * 70))]), 1)
    life.uscale("mass", lin([(1, 1), (0.02, S(0.33))]))

    hands = Layer(r, "appendages", loop=True)   # noodle arms form only to hold or strike (first person too)
    hands.uscale("r_appendage", HOLD_R)
    hands.uscale("l_appendage", HOLD_L)
    for p, side in SIDES:
        hands.rot(f"{p}_grip", mul(6, S(0.8, 0 if side < 0 else 90)), mul(10, S(0.6)), None)

    # ------------------------------------------------------------------ locomotion: floating, comet-like at speed
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    body(loco, rig, lean=lin([(9, s), (8, ss)]), roll=lin([(5, prod(TURN, s))]), twist=lin([(0.1, LOOK)]))
    loco.pos("torso_g", None, prod(0.5, f"math.sin({PH} * 2)", s))
    for k in range(GROUPS):
        loco.rot(f"twist{k}", f"{PH} * {0.12 if k % 2 == 0 else -0.09}", None, None)   # the tangle rolls as it travels
    for k in range(HANG):
        for j in range(3):
            nm = f"hang{k}" if j == 0 else f"hang{k}_{j}"
            loco.rot(nm, lin([(18 + 6 * j, s), (16, ss), (6, prod(f"math.sin({PH} * 2 - {k * 40 + j * 50})", s))]))
    for k in range(4):
        loco.scale(f"trail{k}", 1, 1, lin([(1, 1), (1.1, s), (1.2, ss)]))
        loco.rot(f"trail{k}", prod(8, f"math.sin({PH} * 2 - {k * 60})", s), prod(-6, TURN, s), None)
    for p, side in SIDES:
        loco.rot(f"stalk_{p}0", lin([(-10, s), (-14, ss)]))
        loco.rot(f"stalk_{p}1", lin([(-6, s), (-8, ss)]))
    loco.rot("sauce", lin([(-6, s)]))

    air = Layer(r, "airborne", loop=True)
    air.uscale("mass", lin([(1, 1), (-0.14, RISE), (0.1, FALL)]))
    for k in range(HANG):
        air.rot(f"hang{k}", lin([(-20, FALL), (12, RISE)]), None, mirror(-1 if k % 2 else 1, mul(16, FALL)))
    for p, side in SIDES:
        air.rot(f"stalk_{p}0", lin([(-12, RISE), (8, FALL)]), None, mirror(side, mul(-10, FALL)))

    land = KeyLayer(r, "land", 0.5)
    land_hard = KeyLayer(r, "land_hard", 0.75)
    for kl, g in ((land, 1.0), (land_hard, 1.5)):
        L = kl.length
        kl.scale("mass", {0: (1.12 * g, 0.82 / g, 1.12 * g), 0.1: (1.16 * g, 0.78 / g, 1.16 * g), 0.3: (0.95, 1.06, 0.95), L: 1})
        kl.pos("torso_g", {0: (0, -1.4 * g, 0), 0.1: (0, -1.7 * g, 0), 0.32: (0, 0.5, 0), L: (0, 0, 0)})
        for k in range(HANG):
            kl.rot(f"hang{k}", {0: (0, 0, (24 if k % 2 else -24) * g), 0.25: (0, 0, (-6 if k % 2 else 6)), L: (0, 0, 0)})
        for p, side in SIDES:
            kl.pos(f"meatball_{p}", {0: (0, -0.8 * g, 0), 0.15: (0, 0.6 * g, 0), 0.35: (0, -0.2, 0), L: (0, 0, 0)})
            kl.rot(f"stalk_{p}0", {0: (10 * g, 0, 0), 0.2: (-8, 0, 0), 0.4: (3, 0, 0), L: (0, 0, 0)})
        kl.particle(0.0, "splash", "core")

    atk = Layer(r, "attack", loop=True)          # a noodle whip lashes out with the swing
    body(atk, rig, lean=prod(6, ATK), twist=prod(-8, ATK))
    atk.scale("r_appendage", 1, lin([(1, 1), (0.25, ATK)]), 1)
    for p, side in SIDES:
        atk.scale(f"lid_{p}", None, lin([(1, 1), (4, ATK)]), None)

    hurt = KeyLayer(r, "hurt", 0.55)
    hurt.scale("mass", {0: 1, 0.05: (1.12, 0.9, 1.12), 0.2: (0.96, 1.05, 0.96), 0.4: 1, 0.55: 1})
    for k in range(GROUPS):
        hurt.rot(f"twist{k}", {**shake(0.0, 0.45, (8, 10 * (1 if k % 2 else -1), 6), freq=8, decay=6), 0.55: (0, 0, 0)})
    for p, side in SIDES:
        hurt.scale(f"lid_{p}", {0: 1, 0.04: (1, 12, 1), 0.3: (1, 12, 1), 0.42: 1})
        hurt.rot(f"stalk_{p}0", {0: (0, 0, 0), 0.05: (-16, 0, side * 14), 0.3: (5, 0, 0), 0.55: (0, 0, 0)})
        hurt.pos(f"meatball_{p}", {**shake(0.0, 0.4, (0.5 * side, 0.6, 0.3), freq=7, decay=6), 0.55: (0, 0, 0)})
    hurt.particle(0.0, "splash", "core")

    # ------------------------------------------------------------------ idle behaviours
    fid = []
    doodle = KeyLayer(r, "fidget_shape", 2.8)     # a strand tries to make a shape; another drags it back
    doodle.rot("hang0", {0: (0, 0, 0), 0.4: (-150, 0, 10), 1.6: (-150, 0, 10), 2.2: (-60, 0, 0), 2.8: (0, 0, 0)})
    doodle.rot("hang0_1", {0: (0, 0, 0), 0.6: (0, 0, 80), 0.9: (0, 0, 120), 1.2: (0, 0, 70), 1.5: (0, 0, 110), 2.2: (0, 0, 0)})
    doodle.rot("hang0_2", {0: (0, 0, 0), 0.7: (0, 0, 90), 1.0: (0, 0, 130), 1.3: (0, 0, 90), 2.2: (0, 0, 0)})
    doodle.rot("hang1", {0: (0, 0, 0), 1.3: (0, 0, 0), 1.6: (-120, 0, -40), 2.0: (-90, 0, -30), 2.5: (0, 0, 0)})
    doodle.rot("eye_r", {0: (0, 0, 0), 0.5: (30, 30, 0), 1.6: (30, 30, 0), 1.9: (20, 10, 0), 2.6: (0, 0, 0)})
    doodle.rot("eye_l", {0: (0, 0, 0), 1.4: (0, 0, 0), 1.6: (30, -40, 0), 2.4: (30, -40, 0), 2.8: (0, 0, 0)})
    fid.append(doodle)
    eyes = KeyLayer(r, "fidget_eyes", 2.6)        # one eye studies the sky, the other the ground... then each other
    eyes.rot("eye_r", {0: (0, 0, 0), 0.3: (-60, 0, 0), 0.9: (-60, 0, 0), 1.1: (60, 0, 0), 1.6: (60, 0, 0), 1.8: (0, -55, 0), 2.3: (0, -55, 0), 2.6: (0, 0, 0)})
    eyes.rot("eye_l", {0: (0, 0, 0), 0.3: (60, 0, 0), 0.9: (60, 0, 0), 1.1: (-60, 0, 0), 1.6: (-60, 0, 0), 1.8: (0, 55, 0), 2.3: (0, 55, 0), 2.6: (0, 0, 0)})
    eyes.rot("stalk_r0", {0: (0, 0, 0), 0.3: (-12, 0, -10), 1.6: (-12, 0, -10), 1.8: (0, 0, 12), 2.3: (0, 0, 12), 2.6: (0, 0, 0)})
    eyes.rot("stalk_l0", {0: (0, 0, 0), 0.3: (12, 0, 10), 1.6: (12, 0, 10), 1.8: (0, 0, -12), 2.3: (0, 0, -12), 2.6: (0, 0, 0)})
    for p in ("r", "l"):
        eyes.scale(f"lid_{p}", {0: 1, 2.25: 1, 2.32: (1, 12, 1), 2.42: 1, 2.6: 1})
    fid.append(eyes)
    roll = KeyLayer(r, "fidget_meatballs", 2.6)   # the meatballs take a lap around the body
    roll.rot("orbit_r", {0: (0, 0, 0), 0.4: (0, 40, 0), 1.6: (0, 320, 0), 2.1: (0, 360, 0)})
    roll.rot("orbit_l", {0: (0, 0, 0), 0.5: (0, -40, 0), 1.7: (0, -320, 0), 2.2: (0, -360, 0)})
    for p in ("r", "l"):
        roll.rot(f"meatball_{p}", {0: (0, 0, 0), 2.2: (360, 0, 0)})
    roll.scale("mass", {0: 1, 0.6: (1.05, 0.95, 1.05), 1.2: (0.95, 1.05, 0.95), 1.8: (1.05, 0.95, 1.05), 2.4: 1})
    fid.append(roll)
    swirl = KeyLayer(r, "fidget_sauce", 2.4)      # the sauce flows upward in a spiral
    swirl.rot("sauce", {0: (0, 0, 0), 2.0: (0, 360, 0), 2.4: (0, 360, 0)})
    for k in range(4):
        swirl.pos(f"drip{k}", {0: (0, 0, 0), 0.3 + k * 0.1: (0, 0, 0), 0.9 + k * 0.1: (0, 3.0, 0), 1.6: (0, 2.6, 0), 2.1: (0, 0, 0)})
    swirl.particle(0.2, "saucespiral", "top")
    fid.append(swirl)
    picks = [("fidget_shape", "math.mod(math.floor(q.life_time * 1.7), 5) == 0"),
             ("fidget_eyes", "math.mod(math.floor(q.life_time * 1.7), 5) == 1"),
             ("fidget_meatballs", "math.mod(math.floor(q.life_time * 1.7), 5) == 2"),
             ("fidget_sauce", "math.mod(math.floor(q.life_time * 1.7), 5) == 3")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": KeyLayer(r, "intro_base", 0.45, loop="hold"),
        "rigid": KeyLayer(r, "intro_rigid", 0.3, loop="hold"),
        "detached": KeyLayer(r, "intro_detached", 0.4, loop="hold"),
        "revelation": KeyLayer(r, "intro_revelation", 1.0, loop="hold"),
        "brittle": KeyLayer(r, "intro_brittle", 0.3, loop="hold"),
    }
    intro["base"].scale("mass", {0: (1.1, 0.9, 1.1), 0.2: (0.96, 1.04, 0.96), 0.45: 1})
    intro["rigid"].scale("lattice", {0: 0.3, 0.12: 1.08, 0.3: 1})
    intro["rigid"].particle(0.0, "crack", "core")
    intro["detached"].scale("mass", {0: (1.15, 0.88, 1.15), 0.2: (0.95, 1.05, 0.95), 0.4: 1})
    intro["detached"].particle(0.0, "splash", "core")
    for k in range(3):
        intro["revelation"].scale(f"spiral{k}", {0: 0.05, 0.25 + k * 0.15: 0.05, 0.6 + k * 0.15: 1.06, 0.85 + k * 0.05: 1})
        intro["revelation"].rot(f"spiral{k}", {0: (0, -180, 0), 0.85 + k * 0.05: (0, 0, 0)})
    intro["revelation"].particle(0.0, "vortex", "core")
    intro["brittle"].particle(0.0, "steam", "top")

    rigid_loop = Layer(r, "rigid_loop", loop=True)       # tense: everything locked, a faint vibration
    rigid_loop.uscale("lattice", lin([(1, 1), (0.01, S(9))]))
    for p in ("r", "l"):
        rigid_loop.scale(f"lid_{p}", None, 5, None)
    detached_loop = Layer(r, "detached_loop", loop=True)  # the eyes search for the missing meatballs
    for p, side in SIDES:
        detached_loop.rot(f"eye_{p}", mul(14, SQ(0.9, 0 if side < 0 else 60, 6)), mul(30, SQ(0.7, 30 if side < 0 else 90, 6)), None)
    for k in range(HANG):
        detached_loop.rot(f"hang{k}", 6)
    rev_loop = Layer(r, "revelation_loop", loop=True)
    for k, sp in enumerate((80, -60, 45)):
        rev_loop.rot(f"spiral{k}", None, f"{T} * {sp}", None)
    rev_loop.rot("orbit_r", None, f"{T} * 140", None)
    rev_loop.rot("orbit_l", None, f"-{T} * 160", None)
    rev_loop.uscale("mass", lin([(0.82, 1), (0.04, S(2.0))]))
    for p in ("r", "l"):
        rev_loop.rot(f"eye_{p}", 35, None, None)
    rev_loop.particle(0.0, "vortex", "core")
    rev_loop.kw["length"] = 0.5
    brittle_loop = Layer(r, "brittle_loop", loop=True)   # crisp and creaky
    for k in range(GROUPS):
        brittle_loop.rot(f"twist{k}", mul(1.5, S(7.0, k * 50)))
    brittle_loop.particle(0.0, "steam", "top")
    brittle_loop.kw["length"] = 1.2

    fx = {
        "base": A(r, "fx_base", length=3.0).particle(0.0, "drip", "drip"),
        "rigid": A(r, "fx_rigid", length=1.0).particle(0.0, "crack", "core"),
        "detached": A(r, "fx_detached", length=1.4).particle(0.0, "drip", "drip"),
        "revelation": A(r, "fx_revelation", length=0.4).particle(0.0, "saucespiral", "top"),
        "brittle": A(r, "fx_brittle", length=1.0).particle(0.0, "steam", "top"),
    }
    built = [fp, tp, life.anim(), hands.anim(), loco.anim(), air.anim(), land.anim(), land_hard.anim(), atk.anim(),
             hurt.anim(), rigid_loop.anim(), detached_loop.anim(), rev_loop.anim(), brittle_loop.anim(),
             wait_anim(r, "fidget_wait", 6.0), wait_anim(r, "fidget_rest", 3.0), *[f.anim() for f in fid],
             *[a.anim() for a in intro.values()], *fx.values()]
    controllers = {**landing_controller(r), **fidget_controller(r, picks)}
    loops = {"rigid": "rigid_loop", "detached": "detached_loop", "revelation": "revelation_loop", "brittle": "brittle_loop"}
    animate = {}
    for v in ("base", "rigid", "detached", "revelation", "brittle"):
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("life", TP), ("appendages", None)]
        if v in ("base", "brittle", "detached"):
            lst.append(("fidget", TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP), ("hurt", f"{TP} && q.hurt_time > 0"),
                (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"drip": f"{NS}:sauce_drip", "splash": f"{NS}:sauce_splash", "crack": f"{NS}:dente_crack",
                 "vortex": f"{NS}:pasta_vortex", "saucespiral": f"{NS}:sauce_spiral", "steam": f"{NS}:pasta_steam"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": shared_vars() + ["v.plr_bob = 0;"]}
