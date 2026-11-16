"""Race 005 Flying Spaghetti Monster - attachable animation set (v1.2 redesign).

Motion language: soft, buoyant, unhurried.  The nest floats on a slow 2.5 s swell and
breathes with it; everything that hangs from it follows a beat late (the U-loops and
curls swing behind the hover, the noodly appendages undulate in travelling waves); the
loose loops slide around the nest.  The two eyes have minds of their own: their pupils
dart and hold independently, each lid blinks on its own clock, and the stalks lag
behind every move.  Moving, the whole nest leans and banks into its path while the
appendages stream back; it squashes on landing and the meatballs bounce a beat later.
"""
from __future__ import annotations

from typing import Dict

from anims.core import NS, T
from anims.life import (ATK, C, FALL, LOOK, MOVE, PH, RISE, S, SPR, STILL, TURN, KeyLayer, Layer, chain_wave,
                        drain_shared, fidget_controller, landing_controller, lin, mul, prod, saccade, shared_vars,
                        smooth_pulse, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, blink, mirror, shake, view_anims
from models.spaghetti import APP, DRAPES, GROUPS, HANG

R = "spaghetti"
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"
PITCH = "math.clamp(q.target_x_rotation, -45, 45)"          # head pitch (+ = looking down)
SLEEP = "q.is_sleeping"
HOVER = 0.4                                                 # Hz: the slow swell everything follows
# the swing, and the same swing arriving later down a noodle (a whip)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.3 - 0.15, 0, 1) * 180)"
ATK3 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.5 - 0.3, 0, 1) * 180)"


def _lift(side: int, e):
    """Rotation (z) that raises a noodle sticking out to this side."""
    return e if side < 0 else mul(-1.0, e)


def anims(model) -> Dict[str, object]:
    r = R
    fp, tp = view_anims(r)

    # ------------------------------------------------------------------ life: the slow swell
    life = Layer(r, "life", loop=True)
    life.pos("mass", None, lin([(0.8, S(HOVER)), (0.22, S(1.1, 40))]), None)
    breath = S(HOVER, -60)
    life.scale("mass", lin([(1, 1), (0.016, breath)]), lin([(1, 1), (-0.012, breath)]), lin([(1, 1), (0.016, breath)]))
    life.rot("mass", mul(1.5, S(0.17)), mul(2.5, S(0.09, 20)), prod(2.0, S(0.13, 30), STILL))
    for k in range(GROUPS):                   # the loose loops slide slowly around the nest
        sgn = 1 if k % 2 == 0 else -1
        life.rot(f"twist{k}", mul(1.5, S(0.11 + 0.03 * k, k * 70)), mul(6 * sgn, S(0.07 + 0.02 * k, k * 50)),
                 mul(1.5, S(0.13 + 0.02 * k, k * 40)))
    for k in range(DRAPES):                   # U-loops swing a beat behind the hover
        life.rot(f"drape{k}", lin([(7, S(HOVER, -100 - 25 * k)), (3, S(0.23, k * 80))]), None, mul(5, S(0.31, k * 60)))
    for k in range(HANG):
        bones = [f"hang{k}_{j}" for j in range(3)]
        chain_wave(life, bones, "z", 7, 0.33 + 0.07 * k, lag=55, falloff=1.25, phase=k * 90)
        chain_wave(life, bones, "x", 6, HOVER, lag=50, falloff=1.2, phase=-(100 + k * 30))
    for p, side in SIDES:                     # His Noodly Appendages: slow travelling waves
        bones = [f"{p}_app{j}" for j in range(APP)]
        f = 1.0 if side < 0 else 1.13
        chain_wave(life, bones, "y", 6 * -side, 0.27 * f, lag=45, falloff=1.2, phase=0 if side < 0 else 120)
        chain_wave(life, bones, "z", 5 * -side, 0.21 * f, lag=50, falloff=1.25, phase=30 if side < 0 else 200)
        # meatballs settle into the nest at the bottom of each swell
        sq = S(HOVER, -40)
        life.scale(f"{p}_meatball", lin([(1, 1), (-0.035, sq)]), lin([(1, 1), (0.045, sq)]), lin([(1, 1), (-0.035, sq)]))
        life.rot(f"{p}_meatball", None, mul(6, S(0.2, side * 50)), None)
        # eyes: stalks follow the swell late; each eye has its own mind
        for j in range(3):
            life.rot(f"{p}_stalk{j}", mul(2.0 + j, S(HOVER, -80 - 40 * j)), None, mirror(side, mul(2.5 + j, S(0.19 * f, 40 + j * 60))))
        life.rot(f"{p}_eye", lin([(0.3, PITCH), (3, S(0.23 * f, 20))]), lin([(0.25, LOOK), (5, S(0.17 * f, 60))]), None)
        px_ = f"math.clamp({saccade(0.55 * f, 0.55, seed=3 + side * 1.7)} - {LOOK} * 0.006, -0.75, 0.75)"
        py_ = f"math.clamp({saccade(0.43 * f, 0.4, seed=7 + side * 2.3)} - {PITCH} * 0.01, -0.6, 0.6)"
        life.pos(f"{p}_pupil", px_, py_, None)
        life.rot(f"{p}_lid", f"-90 * math.max({blink(3.7 * f, 6.3 * f, 0.18, 1.1 + side)}, {SLEEP})", None, None)
    life.rot("halo", mul(3, S(0.21)), f"{T} * 22", mul(2, S(0.17, 50)))
    life.pos("halo", None, mul(0.35, S(0.5, 30)), None)
    life.rot("sauce", None, None, mul(1.5, S(0.3)))
    for k in range(4):                        # the drips stretch and recover like thick sauce
        life.scale(f"drip{k}", 1, lin([(1, 1), (0.14, S(0.35 + 0.05 * k, k * 70))]), 1)
    rise = smooth_pulse(7.0, 2.2, 0.8, 0.7)   # the bead creeps UP, waits, then plops back
    life.pos("drip_up", mul(0.2, S(1.3)), mul(1.8, rise), None)
    life.scale("drip_up", None, lin([(1, 1), (0.3, rise)]), None)

    hands = Layer(r, "appendages", loop=True)  # noodle braids form only to hold or strike (first person too)
    hands.uscale("r_braid", HOLD_R)
    hands.uscale("l_braid", HOLD_L)
    for p, side in SIDES:
        hands.rot(f"{p}_braid", mul(3, S(0.6, 0 if side < 0 else 90)), None, mirror(side, mul(3, S(0.45))))

    # ------------------------------------------------------------------ locomotion: floating, leaning into its path
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    loco.rot("mass", lin([(10, s), (8, ss)]), None, lin([(-7, prod(TURN, s))]))
    loco.pos("mass", None, prod(0.5, f"math.sin({PH})", s), None)
    for k in range(GROUPS):
        loco.rot(f"twist{k}", None, prod(4 if k % 2 == 0 else -4, f"math.sin({PH} - {k * 60})", s), None)
    for k in range(DRAPES):                   # swept back, swinging with the stride
        loco.rot(f"drape{k}", lin([(18, s), (10, ss), (6, prod(f"math.sin({PH} - {80 + k * 40})", s))]), None, None)
    for k in range(HANG):
        for j in range(3):
            loco.rot(f"hang{k}_{j}", lin([(14 + 4 * j, s), (8, ss), (5, prod(f"math.sin({PH} - {k * 40 + j * 60})", s))]))
    for p, side in SIDES:                     # appendages stream back in waves driven by the distance flown
        for j in range(APP):
            wave = prod(f"math.sin({PH} - {j * 55 + (0 if side < 0 else 90)})", s)
            loco.rot(f"{p}_app{j}", None, mul(-side, lin([(16 if j == 0 else 4, s), (8 if j == 0 else 0, ss), (5 + 2 * j, wave)])),
                     _lift(side, lin([(4 + 2 * j, wave)])))
        loco.rot(f"{p}_stalk0", lin([(-7, s), (-5, ss)]))
        loco.rot(f"{p}_stalk1", lin([(-4, s), (-3, ss)]))
    loco.rot("halo", lin([(-8, s), (-5, ss)]))
    for k in range(4):
        loco.rot(f"drip{k}", lin([(10, s)]))

    air = Layer(r, "airborne", loop=True)
    air.scale("mass", lin([(1, 1), (-0.04, RISE), (0.03, FALL)]), lin([(1, 1), (0.07, RISE), (-0.05, FALL)]),
              lin([(1, 1), (-0.04, RISE), (0.03, FALL)]))
    for k in range(DRAPES):
        air.rot(f"drape{k}", lin([(20, FALL), (-10, RISE)]))
    for k in range(HANG):
        air.rot(f"hang{k}_1", None, None, mul(25 if k % 2 == 0 else -25, FALL))
        air.rot(f"hang{k}_2", None, None, mul(20 if k % 2 == 0 else -20, FALL))
    for p, side in SIDES:
        for j in range(APP):
            air.rot(f"{p}_app{j}", None, None, _lift(side, lin([(10 + 3 * j, FALL), (-6, RISE)])))
        air.rot(f"{p}_stalk0", lin([(-10, RISE), (6, FALL)]))
        air.rot(f"{p}_stalk1", lin([(-6, RISE), (4, FALL)]))

    land = KeyLayer(r, "land", 0.5)
    land_hard = KeyLayer(r, "land_hard", 0.75)
    for kl, g in ((land, 1.0), (land_hard, 1.5)):
        L = kl.length
        kl.scale("mass", {0: (1 + 0.1 * g, 1 - 0.13 * g, 1 + 0.1 * g), 0.08: (1 + 0.12 * g, 1 - 0.16 * g, 1 + 0.12 * g),
                          0.25: (0.96, 1.05, 0.96), 0.4: (1.01, 0.99, 1.01), L: 1})
        kl.pos("mass", {0: (0, -1.2 * g, 0), 0.1: (0, -1.6 * g, 0), 0.3: (0, 0.4, 0), L: (0, 0, 0)})
        for k in range(DRAPES):
            kl.rot(f"drape{k}", {0: (-25 * g, 0, 0), 0.2: (10 * g, 0, 0), 0.38: (-3, 0, 0), L: (0, 0, 0)})
        for p, side in SIDES:
            kl.pos(f"{p}_meatball", {0: (0, -0.6 * g, 0), 0.12: (0, 0.9 * g, 0), 0.3: (0, -0.2, 0), L: (0, 0, 0)})
            kl.scale(f"{p}_meatball", {0: 1, 0.08: (1.12, 0.84, 1.12), 0.2: (0.94, 1.08, 0.94), 0.34: 1, L: 1})
            kl.rot(f"{p}_stalk0", {0: (8 * g, 0, 0), 0.15: (-10 * g, 0, 0), 0.35: (3, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_lid", {0: (-90, 0, 0), 0.12: (-90, 0, 0), 0.22: (0, 0, 0), L: (0, 0, 0)})
            kl.rot(f"{p}_app0", {0: (0, 0, _side_lift(side, 18 * g)), 0.2: (0, 0, _side_lift(side, -8 * g)), L: (0, 0, 0)})
        kl.particle(0.0, "splash", "core")

    atk = Layer(r, "attack", loop=True)       # a noodle lashes out with the swing
    atk.rot("mass", prod(4, ATK), prod(-10, ATK), None)
    atk.rot("r_app0", None, prod(-75, ATK), prod(20, ATK))
    atk.rot("r_app1", None, prod(-25, ATK2), prod(-10, ATK2))
    atk.rot("r_app2", None, prod(-20, ATK3), None)
    atk.rot("r_app3", None, prod(-25, ATK3), None)
    for p, side in SIDES:
        atk.scale(f"{p}_eye", None, lin([(1, 1), (-0.15, ATK)]), None)      # a determined squint
        atk.pos(f"{p}_pupil", prod(-0.5, ATK), None, None)

    hurt = KeyLayer(r, "hurt", 0.55)
    hurt.scale("mass", {0: 1, 0.05: (1.1, 0.9, 1.1), 0.2: (0.96, 1.05, 0.96), 0.4: 1, 0.55: 1})
    for k in range(GROUPS):
        hurt.rot(f"twist{k}", {**shake(0.0, 0.45, (6, 8 * (1 if k % 2 else -1), 5), freq=8, decay=6), 0.55: (0, 0, 0)})
    for p, side in SIDES:
        hurt.rot(f"{p}_lid", {0: (0, 0, 0), 0.03: (-90, 0, 0), 0.22: (-90, 0, 0), 0.3: (0, 0, 0), 0.55: (0, 0, 0)})
        hurt.scale(f"{p}_pupil", {0: 1, 0.28: 0.6, 0.45: 0.6, 0.55: 1})
        hurt.rot(f"{p}_stalk0", {0: (0, 0, 0), 0.05: (-16, 0, _side_lift(side, -14)), 0.3: (5, 0, 0), 0.55: (0, 0, 0)})
        hurt.pos(f"{p}_meatball", {**shake(0.0, 0.4, (0.5 * side, 0.6, 0.3), freq=7, decay=6), 0.55: (0, 0, 0)})
    hurt.particle(0.0, "splash", "core")

    # ------------------------------------------------------------------ idle behaviours
    fid = []
    twirl = KeyLayer(r, "fidget_shape", 3.0)  # an appendage twirls itself like pasta on a fork
    twirl.rot("r_app0", {0: (0, 0, 0), 0.45: (0, -55, 38), 2.3: (0, -55, 38), 3.0: (0, 0, 0)})
    circle = {0.6: (0, 0, 0), 0.85: (35, 0, 0), 1.1: (0, 0, 35), 1.35: (-35, 0, 0), 1.6: (0, 0, -35),
              1.85: (35, 0, 0), 2.1: (0, 0, 35), 2.35: (0, 0, 0)}
    twirl.rot("r_app1", {0: (0, 0, 0), 0.45: (0, -20, 25), **{t: (v[0], -20 + v[1], 25 + v[2]) for t, v in circle.items()},
                         3.0: (0, 0, 0)})
    twirl.rot("r_app2", {0: (0, 0, 0), 0.5: (0, -10, 35), 1.2: (0, -10, 55), 2.2: (0, -10, 55), 3.0: (0, 0, 0)})
    twirl.rot("r_app3", {0: (0, 0, 0), 0.55: (0, 0, 45), 1.3: (0, 0, 70), 2.2: (0, 0, 70), 3.0: (0, 0, 0)})
    for p in ("r", "l"):
        twirl.pos(f"{p}_pupil", {0: (0, 0, 0), 0.4: (-0.7, -0.1, 0), 2.4: (-0.7, -0.1, 0), 2.8: (0, 0, 0), 3.0: (0, 0, 0)})
    twirl.rot("r_stalk0", {0: (0, 0, 0), 0.5: (-6, 0, 8), 2.3: (-6, 0, 8), 3.0: (0, 0, 0)})
    fid.append(twirl)

    eyes = KeyLayer(r, "fidget_eyes", 2.6)    # one eye studies the sky, the other the ground... then each other
    eyes.pos("r_pupil", {0: (0, 0, 0), 0.15: (0, 0.6, 0), 0.8: (0, 0.6, 0), 0.95: (0, -0.6, 0), 1.5: (0, -0.6, 0),
                         1.65: (0.75, 0, 0), 2.25: (0.75, 0, 0), 2.45: (0, 0, 0), 2.6: (0, 0, 0)})
    eyes.pos("l_pupil", {0: (0, 0, 0), 0.2: (0, -0.6, 0), 0.8: (0, -0.6, 0), 0.95: (0, 0.6, 0), 1.5: (0, 0.6, 0),
                         1.65: (-0.75, 0, 0), 2.25: (-0.75, 0, 0), 2.45: (0, 0, 0), 2.6: (0, 0, 0)})
    eyes.rot("r_eye", {0: (0, 0, 0), 0.2: (-14, 0, 0), 0.8: (-14, 0, 0), 1.0: (12, 0, 0), 1.5: (12, 0, 0), 1.7: (0, -14, 0),
                       2.25: (0, -14, 0), 2.6: (0, 0, 0)})
    eyes.rot("l_eye", {0: (0, 0, 0), 0.25: (12, 0, 0), 0.8: (12, 0, 0), 1.0: (-14, 0, 0), 1.5: (-14, 0, 0), 1.7: (0, 14, 0),
                       2.25: (0, 14, 0), 2.6: (0, 0, 0)})
    eyes.rot("r_stalk0", {0: (0, 0, 0), 0.3: (-6, 0, -6), 1.5: (-6, 0, -6), 1.7: (0, 0, 9), 2.25: (0, 0, 9), 2.6: (0, 0, 0)})
    eyes.rot("l_stalk0", {0: (0, 0, 0), 0.3: (5, 0, 6), 1.5: (5, 0, 6), 1.7: (0, 0, -9), 2.25: (0, 0, -9), 2.6: (0, 0, 0)})
    for p in ("r", "l"):
        eyes.rot(f"{p}_lid", {0: (0, 0, 0), 2.28: (0, 0, 0), 2.34: (-90, 0, 0), 2.42: (0, 0, 0), 2.6: (0, 0, 0)})
    fid.append(eyes)

    lap = KeyLayer(r, "fidget_meatballs", 2.8)  # the meatballs take a lap around the nest
    for p in ("r", "l"):
        lap.rot(f"{p}_orbit", {0: (0, 0, 0), 0.35: (0, 25, 0), 1.9: (0, 335, 0), 2.4: (0, 360, 0), 2.8: (0, 360, 0)})
        lap.rot(f"{p}_meatball", {0: (0, 0, 0), 2.4: (-360, 0, 0), 2.8: (-360, 0, 0)})
        lap.pos(f"{p}_meatball", {0: (0, 0, 0), 0.3: (0, 1.2, 0), 2.1: (0, 1.2, 0), 2.5: (0, 0, 0), 2.8: (0, 0, 0)})
    for p, side in SIDES:                     # the eyes follow them round
        lap.pos(f"{p}_pupil", {0: (0, 0, 0), 0.4: (0.6 * side, -0.2, 0), 1.0: (0, -0.2, 0), 1.4: (-0.6 * side, -0.2, 0),
                               2.2: (-0.6 * side, -0.2, 0), 2.6: (0, 0, 0), 2.8: (0, 0, 0)})
    lap.scale("mass", {0: 1, 0.6: (1.04, 0.96, 1.04), 1.2: (0.97, 1.03, 0.97), 1.8: (1.03, 0.97, 1.03), 2.4: 1, 2.8: 1})
    fid.append(lap)

    swirl = KeyLayer(r, "fidget_sauce", 2.6)  # sauce defies gravity: a bead climbs into the air, the eyes watch
    swirl.pos("drip_up", {0: (0, 0, 0), 0.5: (0.4, 1.5, 0), 1.0: (-0.3, 3.0, 0.3), 1.5: (0.2, 4.2, -0.2), 1.8: (0, 4.4, 0),
                          2.05: (0, 4.4, 0), 2.3: (0, 0, 0), 2.6: (0, 0, 0)})
    swirl.scale("drip_up", {0: 1, 0.5: (0.9, 1.4, 0.9), 1.8: (1.1, 0.95, 1.1), 2.05: (0.9, 1.3, 0.9), 2.3: (1.4, 0.6, 1.4),
                            2.45: 1, 2.6: 1})
    for k in range(4):
        swirl.pos(f"drip{k}", {0: (0, 0, 0), 0.25 + k * 0.1: (0, 0, 0), 0.8 + k * 0.1: (0, 1.2, 0), 1.9: (0, 1.0, 0),
                               2.3: (0, 0, 0), 2.6: (0, 0, 0)})
    for p in ("r", "l"):
        swirl.pos(f"{p}_pupil", {0: (0, 0, 0), 0.4: (0, 0.6, 0), 2.0: (0, 0.6, 0), 2.3: (0, -0.3, 0), 2.6: (0, 0, 0)})
        swirl.rot(f"{p}_eye", {0: (0, 0, 0), 0.5: (-18, 0, 0), 2.0: (-18, 0, 0), 2.3: (6, 0, 0), 2.6: (0, 0, 0)})
    swirl.particle(0.2, "saucespiral", "sauce_top")
    fid.append(swirl)
    picks = [("fidget_shape", "math.mod(math.floor(q.life_time * 1.7), 4) == 0"),
             ("fidget_eyes", "math.mod(math.floor(q.life_time * 1.7), 4) == 1"),
             ("fidget_meatballs", "math.mod(math.floor(q.life_time * 1.7), 4) == 2"),
             ("fidget_sauce", "math.mod(math.floor(q.life_time * 1.7), 4) == 3")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": KeyLayer(r, "intro_base", 0.5, loop="hold"),
        "rigid": KeyLayer(r, "intro_rigid", 0.4, loop="hold"),
        "detached": KeyLayer(r, "intro_detached", 0.45, loop="hold"),
        "revelation": KeyLayer(r, "intro_revelation", 1.1, loop="hold"),
        "brittle": KeyLayer(r, "intro_brittle", 0.4, loop="hold"),
    }
    intro["base"].scale("mass", {0: (1.1, 0.88, 1.1), 0.18: (0.96, 1.05, 0.96), 0.35: (1.01, 0.99, 1.01), 0.5: 1})
    intro["rigid"].scale("lattice", {0: 0.4, 0.12: 1.1, 0.25: 0.97, 0.4: 1})
    intro["rigid"].scale("mass", {0: (0.94, 1.06, 0.94), 0.15: (1.02, 0.98, 1.02), 0.4: 1})
    intro["rigid"].particle(0.0, "crack", "core")
    intro["detached"].scale("mass", {0: (1.15, 0.88, 1.15), 0.2: (0.95, 1.05, 0.95), 0.45: 1})
    intro["detached"].particle(0.0, "splash", "core")
    for k in range(3):
        t0 = 0.2 + k * 0.15
        intro["revelation"].scale(f"spiral{k}", {0: 0.05, t0: 0.05, t0 + 0.35: 1.06, t0 + 0.55: 1, 1.1: 1})
        intro["revelation"].rot(f"spiral{k}", {0: (0, -180, 0), t0 + 0.55: (0, 0, 0), 1.1: (0, 0, 0)})
    for p in ("r", "l"):
        intro["revelation"].scale(f"{p}_pupil", {0: 0.6, 0.3: 1.2, 0.6: 1, 1.1: 1})
    intro["revelation"].particle(0.0, "vortex", "core")
    intro["brittle"].scale("mass", {0: (1.03, 0.97, 1.03), 0.1: (0.98, 1.02, 0.98), 0.2: (1.01, 0.99, 1.01), 0.4: 1})
    intro["brittle"].particle(0.0, "steam", "top")

    rigid_loop = Layer(r, "rigid_loop", loop=True)       # tense: everything locked, a faint vibration
    rigid_loop.uscale("lattice", lin([(1, 1), (0.01, S(9))]))
    for p in ("r", "l"):
        rigid_loop.uscale(f"{p}_pupil", 0.8)
    detached_loop = Layer(r, "detached_loop", loop=True)  # the eyes search for the missing meatballs
    for p, side in SIDES:
        detached_loop.pos(f"{p}_pupil", saccade(1.3, 0.6, seed=11 + side), saccade(1.1, 0.4, seed=17 + side), None)
        detached_loop.rot(f"{p}_stalk0", None, mul(14, S(0.5, 0 if side < 0 else 90)), None)
    rev_loop = Layer(r, "revelation_loop", loop=True)
    for k, sp in enumerate((80, -60, 45)):
        rev_loop.rot(f"spiral{k}", None, f"{T} * {sp}", None)
    for p in ("r", "l"):
        rev_loop.rot(f"{p}_orbit", None, f"{T} * 110", None)
        rev_loop.pos(f"{p}_pupil", None, 0.5, None)
    rev_loop.scale("mass", lin([(1, 1), (0.03, S(1.0))]), lin([(1, 1), (-0.02, S(1.0))]), lin([(1, 1), (0.03, S(1.0))]))
    rev_loop.particle(0.0, "vortex", "core")
    rev_loop.kw["length"] = 0.5
    brittle_loop = Layer(r, "brittle_loop", loop=True)   # crisp and creaky
    for k in range(GROUPS):
        brittle_loop.rot(f"twist{k}", None, None, mul(1.2, S(7.0, k * 50)))
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
            "pre": shared_vars() + ["v.plr_bob = 0;"] + drain_shared()}


def _side_lift(side: int, deg: float) -> float:
    """z-rotation (degrees) that raises a noodle sticking out to this side by `deg`."""
    return deg if side < 0 else -deg
