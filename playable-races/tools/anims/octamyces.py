"""Race 009 Octamyces Undecimus - attachable animation set.

Motion language: suspended, deliberate, watchful.  The body hangs in the air on a slow 3 s
swell; the brim flexes a beat behind it like a jellyfish bell; every mycelial group keeps its
own rhythm (the manipulators drift, the fans paddle, the sensor twitches and probes, the
spore emitter swings like a censer, the stabiliser curtain carries a travelling wave, the
antenna hums).  The eye is the personality: its eleven frames turn at eleven speeds in
alternating directions, the iris follows where the player looks and glances on its own, the
crown of plates folds shut in sequence to blink.

Layers (all stateless Molang):
  steady      cancels the player's look on the head group (exactly: x on head_g, y on `steady`)
  gaze        the cap turns a third of the look about the stalk, the iris more; frames, void
              and gill vanes turn continuously (never blended, so unbounded angles are safe)
  glance      dart() glances of the iris and void, the polygonal blink
  vigil       controller: "alive" plays life; after 7 s of stillness the body settles into
              "surveil" over 2 s (the mycelia nearly freeze, the glances and blinks stop, the
              iris scans slowly or stares at an empty spot); any movement wakes it at once
  locomotion  gliding: leans into its path, cap tilts, filaments trail; sprint condenses the
              fans into a beating propulsor
  airborne / landing / attack (a manipulator lash) / hurt (a blink-fold and recoil) / swim
  fidget      controller: blink-fold, frames re-aligning, gills opening, the sensor probing
  forms       intro_<form>, fx_<form>, and loops for sporeveil / record / offset / frame / unstable
"""
from __future__ import annotations

import math
from typing import Dict

from anims.core import NS, T, n
from anims.life import (ATK, BUMP, FALL, MOVE, PH, RISE, S, SPR, STILL, TURN, KeyLayer, Layer, Rig, arm_swing, body,
                        body_keys, chain_wave, dart, drain_shared, fidget_controller, landing_controller, lin, mul, prod,
                        shared_vars, smooth_pulse, wait_anim)
from anims.races import A, AIR, GAIT_OK, TP, mirror, shake, transition, view_anims
from models.octamyces import FLOAT_C, LIDS, MYC_PTS, RING_SIDES, RINGS, SEGS, VARIANTS

R = "octamyces"
RIG = Rig("float", FLOAT_C, [("r_arm_g", MYC_PTS[0][0]), ("l_arm_g", MYC_PTS[1][0])], legs=(), tail=None)
HOVER = 0.32                                                  # Hz: the swell everything follows
PITCH = "math.clamp(q.target_x_rotation, -50, 50)"            # + = looking down
YAW = "math.clamp(q.target_y_rotation, -70, 70)"              # + = looking to its right
EMPTY_R = "(q.is_item_equipped(0) ? 0.25 : 1)"
EMPTY_L = "(q.is_item_equipped(1) ? 0.25 : 1)"
SLEEP = "q.is_sleeping"
# the swing arriving later down a tendril (a whip)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.3 - 0.15, 0, 1) * 180)"
ATK3 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.5 - 0.3, 0, 1) * 180)"
BUSY = ("q.modified_move_speed > 0.04 || !q.is_on_ground || q.is_in_water || q.hurt_time > 0"
        " || (v.attack_time ?? 0) > 0.01 || q.is_sneaking || q.is_riding || q.is_sleeping || q.is_gliding"
        " || q.is_using_item")
# the frames turn at eleven speeds, alternating directions (degrees per second, inner ring fastest)
SPIN = [21.0, -15.0, 12.0, -9.5, 7.5, -6.0, 5.0, -4.0, 3.2, -2.6, 2.0]
SIDES2 = ((0, -1), (1, 1))                                    # manipulator / fan groups by side


def chainb(g: int):
    return [f"myc{g}_{k}" for k in range(SEGS)]


def hover(ly: Layer, lean=None, twist=None, roll=None, bob=None) -> None:
    """Whole-body motion: the torso chain and its mirror in the head chain move together, the arm
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


def lid_blink(j: int) -> str:
    """0..1 fold of plate j: two incommensurate blink clocks, the plates following each other."""
    d = 0.03 * j
    return f"math.max({BUMP(7.7, 0.34, d)}, {BUMP(12.9, 0.34, 4.1 + d)})"


def anims(model) -> Dict[str, object]:
    r = R
    fp, tp = view_anims(r)
    for g in (0, 1):                     # first person: the vanilla arm is drawn as a tendril sleeve
        fp.bone(f"myc{g}", scale=0)

    # ------------------------------------------------------------------ steady / gaze / glance
    steady = Layer(r, "steady", loop=True)
    steady.rot("head_g", "-q.target_x_rotation", None, None)
    steady.rot("steady", None, "-q.target_y_rotation", None)

    gaze = Layer(r, "gaze", loop=True)
    gaze.rot("cap", mul(0.12, PITCH), mul(0.3, YAW), None)
    gaze.rot("eye", f"math.clamp(q.target_x_rotation * 0.3, -14, 14)", f"math.clamp(q.target_y_rotation * 0.35, -18, 18)", None)
    for k in range(RINGS):
        gaze.rot(f"ring{k}", None, None, f"{T} * {n(SPIN[k])}")
    gaze.rot("pupil", None, None, f"{T} * -5")
    gaze.rot("gill_spin", None, f"{T} * 7", None)

    glance_x, glance_y = dart(0.37, 6.0, seed=2.1), dart(0.29, 9.0, seed=5.3)
    pup_x, pup_y = dart(0.53, 0.45, seed=8.8), dart(0.41, 0.35, seed=1.7)
    glance = Layer(r, "glance", loop=True)
    glance.rot("eye", glance_x, glance_y, None)
    glance.pos("pupil", pup_x, pup_y, None)
    for j in range(LIDS):
        glance.rot(f"lid{j}", f"125 * math.max({lid_blink(j)}, {SLEEP})", None, None)

    # ------------------------------------------------------------------ life: the swell
    life = Layer(r, "life", loop=True, length=8.0)
    hover(life, lean=mul(1.2, S(0.11, 30)), roll=mul(1.6, S(0.13)),
          bob=lin([(0.75, S(HOVER)), (0.2, S(1.07, 40))]))
    life.rot("brim", mul(1.4, S(HOVER, -70)), None, mul(0.9, S(0.21, 20)))
    life.scale("brim", lin([(1, 1), (0.012, S(HOVER, -100))]), 1, lin([(1, 1), (0.012, S(HOVER, -100))]))
    life.rot("cap_upper", None, mul(0.8, S(0.09, 50)), mul(0.6, S(0.17, 40)))
    life.rot("plate_a", None, None, mul(1.8, S(0.23)))
    life.rot("plate_b", None, None, mul(-1.8, S(0.23)))
    for p, ph in (("r", 0), ("l", 140)):
        life.scale(f"gill_{p}", 1, lin([(1, 1), (0.9, f"math.max(0, {S(0.17, ph)})")]), 1)
    # manipulators drift (less while holding something)
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        f = 1.0 if side < 0 else 1.17
        chain_wave(life, chainb(g), "z", 3.5 * -side, 0.31 * f, lag=40, falloff=1.15, phase=0 if side < 0 else 110, gain=e)
        chain_wave(life, chainb(g), "x", 2.5, 0.23 * f, lag=35, falloff=1.1, phase=30 if side < 0 else 200, gain=e)
    # fans paddle slowly, their fins ripple
    for g, side in ((2, -1), (3, 1)):
        life.rot(f"myc{g}", mul(4.0, S(0.45, 0 if side < 0 else 160)), None, None)
        chain_wave(life, chainb(g), "x", 4.0, 0.45, lag=50, falloff=1.2, phase=-40 if side < 0 else 120)
        life.rot(f"myc{g}_2", None, mul(-side * 6.0, S(1.3, 0 if side < 0 else 70)), None)
    # sensor: small probing glances and a fine tremble at the tip
    life.rot("myc4", dart(0.6, 8.0, seed=3.3), dart(0.47, 10.0, seed=6.1), None)
    life.rot("myc4_2", mul(1.5, S(7.0)), None, mul(1.2, S(5.3, 40)))
    # spore emitter: a censer's pendulum
    chain_wave(life, chainb(5), "z", 4.0, 0.21, lag=45, falloff=1.1)
    life.rot("myc5_2", mul(3.0, S(0.21, -90)), None, None)
    # stabiliser curtain: a travelling wave down the filaments
    chain_wave(life, chainb(6), "x", 5.0, 0.38, lag=55, falloff=1.25)
    chain_wave(life, chainb(6), "z", 2.0, 0.27, lag=40, falloff=1.2, phase=60)
    # resonance antenna: a slow sway and a fine hum
    chain_wave(life, chainb(7), "x", 3.0, 0.19, lag=30)
    life.rot("myc7_2", None, None, lin([(0.8, S(6.5)), (2.0, S(0.23, 70))]))

    # ------------------------------------------------------------------ surveil: everything stops but the eye
    surveil = Layer(r, "surveil", loop=True)
    hover(surveil, bob=mul(0.15, S(0.07)))
    stare = f"math.clamp(math.sin({T} * 19 + 40) * 3 - 2, 0, 1)"    # now and then it fixes on an empty spot
    surveil.rot("eye", lin([(-1.0, glance_x), (4.0, S(0.037, 20)), (5.0, stare)]),
                lin([(-1.0, glance_y), (16.0, S(0.05)), (-12.0, stare)]), None)
    surveil.pos("pupil", mul(-1.0, pup_x), mul(-1.0, pup_y), None)
    for j in range(LIDS):                # the crown narrows and stops blinking
        surveil.rot(f"lid{j}", lin([(-125.0, f"math.max({lid_blink(j)}, {SLEEP})"), (28.0, 1)]), None, None)
    surveil.uscale("pupil", 0.88)
    for g, side in SIDES2:               # held, a little drooped
        surveil.rot(f"myc{g}_1", 3.0, None, mirror(side, 2.0))
    for g in (2, 3):
        surveil.rot(f"myc{g}", 2.0, None, None)
    surveil.rot("myc4", 6.0, None, None)
    surveil.rot("myc6_0", mul(0.6, S(0.05)), None, None)

    # ------------------------------------------------------------------ locomotion: gliding
    loco = Layer(r, "locomotion", loop=True)
    s = MOVE
    ss = prod(SPR, s)
    arm_swing(loco, 0.3)
    hover(loco, lean=lin([(6.0, s), (5.0, ss)]), roll=lin([(-6.0, prod(TURN, s))]),
          bob=prod(0.35, f"math.sin({PH})", s))
    loco.rot("cap", lin([(2.0, s), (7.0, ss)]), None, None)
    loco.rot("brim", lin([(-3.0, s), (-3.0, ss), (1.5, prod(f"math.sin({PH} * 2 - 40)", s))]), None, None)
    for g, side in SIDES2:               # manipulators trail a little
        e = EMPTY_R if side < 0 else EMPTY_L
        for k in range(SEGS):
            loco.rot(f"myc{g}_{k}", prod(lin([(6.0 + 3 * k, s), (3.0 * k, prod(f"math.sin({PH} - {50 + 40 * k})", s))]), e))
    for g, side in ((2, -1), (3, 1)):    # fans: paddle with the glide; sprint folds them into one beating propulsor
        loco.rot(f"myc{g}", lin([(8.0, s), (6.0, prod(f"math.sin({PH} * 2 - {0 if side < 0 else 180})", s))]),
                 mul(side * 18.0, ss), None)
        loco.rot(f"myc{g}_1", lin([(6.0, s), (5.0, prod(f"math.sin({PH} * 2 - {60 if side < 0 else 240})", s))]))
        loco.rot(f"myc{g}_2", lin([(10.0, prod(f"math.sin({PH} * 4 - {90 if side < 0 else 270})", ss))]),
                 mul(side * 12.0, ss), None)
    loco.rot("myc4", lin([(-12.0, s)]), None, None)           # the sensor draws in
    loco.rot("myc5", lin([(10.0, s), (4.0, prod(f"math.sin({PH} - 80)", s))]), None, None)
    for k in range(SEGS):                # the curtain streams back in waves
        loco.rot(f"myc6_{k}", lin([(14.0 if k == 0 else 6.0, s), (8.0 if k == 0 else 4.0, ss),
                                   (4.0 + 2 * k, prod(f"math.sin({PH} - {60 * k})", s))]))
    loco.rot("myc7", lin([(-12.0, s), (-8.0, ss)]), None, None)

    air = Layer(r, "airborne", loop=True)  # contract before the impulse, spread when falling
    hover(air, lean=lin([(-3.0, RISE), (4.0, FALL)]))
    air.rot("brim", lin([(4.0, RISE), (-5.0, FALL)]), None, None)
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"myc{g}_1", None, None, mirror(side, prod(lin([(10.0, RISE), (-16.0, FALL)]), e)))
    for g, side in ((2, -1), (3, 1)):
        air.rot(f"myc{g}", lin([(-12.0, RISE), (10.0, FALL)]), mul(side, lin([(14.0, RISE), (-18.0, FALL)])), None)
    air.rot("myc4", lin([(-10.0, RISE), (12.0, FALL)]), None, None)
    air.rot("myc5", None, None, lin([(8.0, RISE), (-14.0, FALL)]))
    air.rot("myc6", lin([(-8.0, RISE), (16.0, FALL)]), None, None)
    air.rot("myc6_1", lin([(-6.0, RISE), (-10.0, FALL)]), None, None)

    land = KeyLayer(r, "land", 0.6)
    land_hard = KeyLayer(r, "land_hard", 0.85)
    for kl, g in ((land, 1.0), (land_hard, 1.6)):
        L = kl.length
        hover_keys(kl, {0: {"bob": -0.9 * g, "lean": 2 * g}, 0.12: {"bob": -1.3 * g, "lean": 3 * g},
                        0.32: {"bob": 0.35 * g, "lean": -1}, 0.5: {"bob": -0.1}, L: {}})
        kl.rot("brim", {0: (-6 * g, 0, 0), 0.15: (5 * g, 0, 0), 0.32: (-2, 0, 0), L: (0, 0, 0)})
        for gr, side in ((2, -1), (3, 1)):
            kl.rot(f"myc{gr}", {0: (14 * g, 0, 0), 0.18: (-8 * g, 0, 0), 0.4: (2, 0, 0), L: (0, 0, 0)})
        for k in range(SEGS):
            kl.rot(f"myc6_{k}", {0: (0, 0, 0), 0.08 + 0.05 * k: (-14 * g, 0, 0), 0.3 + 0.05 * k: (8, 0, 0), L: (0, 0, 0)})
        kl.rot("myc5", {0: (0, 0, -10 * g), 0.2: (0, 0, 7 * g), 0.45: (0, 0, -2), L: (0, 0, 0)})
        kl.rot("myc7", {0: (10 * g, 0, 0), 0.2: (-8 * g, 0, 0), 0.45: (2, 0, 0), L: (0, 0, 0)})
        for k in range(RINGS):           # the frames jolt toward the eye and settle
            kl.pos(f"ring{k}", {0: (0, 0, 0), 0.06 + 0.012 * k: (0, -0.25 * g, -0.25 * g), 0.3: (0, 0, 0), L: (0, 0, 0)})
    land_hard.particle(0.0, "motes", "base_c")

    atk = Layer(r, "attack", loop=True)  # the right manipulator lashes out with the swing
    atk.rot("myc0", prod(-30, ATK), prod(-20, ATK), prod(25, ATK))
    atk.rot("myc0_1", prod(-25, ATK2), None, prod(-20, ATK2))
    atk.rot("myc0_2", prod(-30, ATK3), None, prod(-15, ATK3))
    hover(atk, lean=prod(4, ATK), twist=prod(-8, ATK))
    atk.rot("cap", prod(3, ATK), prod(-6, ATK), None)
    for j in range(LIDS):                # the crown narrows: a squint
        atk.rot(f"lid{j}", prod(40, ATK), None, None)
    for k in range(RINGS):
        atk.uscale(f"ring{k}", lin([(1, 1), (-0.08, ATK)]))

    hurt = KeyLayer(r, "hurt", 0.65)     # a polygonal blink-fold and a recoil
    hover_keys(hurt, {0: {}, 0.05: {"lean": -8, "roll": 4, "bob": 0.5}, 0.22: {"lean": 3, "roll": -2}, 0.42: {"lean": -1}, 0.65: {}})
    for j in range(LIDS):
        t0 = 0.012 * j
        hurt.rot(f"lid{j}", {0: (0, 0, 0), 0.03 + t0: (125, 0, 0), 0.26 + t0: (125, 0, 0), 0.38 + t0: (-10, 0, 0), 0.48 + t0: (0, 0, 0), 0.65: (0, 0, 0)})
    for k in range(RINGS):               # the frames are knocked out of true
        a = math.radians(k * 137.5)
        hurt.pos(f"ring{k}", {**shake(0.0, 0.5, (0.35 * math.cos(a), 0.35 * math.sin(a), 0.2), freq=8 + k % 3, decay=6), 0.65: (0, 0, 0)})
    hurt.rot("brim", {0: (0, 0, 0), 0.05: (-6, 0, 3), 0.22: (3, 0, -1), 0.65: (0, 0, 0)})
    for g in range(2, 8):
        hurt.rot(f"myc{g}", {**shake(0.02 * g, 0.45, (7, 5 * (1 if g % 2 else -1), 4), freq=6, decay=5), 0.65: (0, 0, 0)})
    hurt.particle(0.0, "echo", "eye_c")

    swim = Layer(r, "swim", loop=True)   # filaments spread like fins and beat together; the brim pulses like a bell
    pulse = S(1.1)
    swim.scale("brim", lin([(1, 1), (0.07, pulse)]), lin([(1, 1), (-0.05, pulse)]), lin([(1, 1), (0.07, pulse)]))
    for g, side in ((2, -1), (3, 1)):
        swim.rot(f"myc{g}", lin([(-20.0, 1), (12.0, S(1.1, -60))]), mul(side * 25.0, 1), None)
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        swim.rot(f"myc{g}_0", None, None, mirror(side, prod(lin([(-25.0, 1), (10.0, S(1.1, -90))]), e)))
    swim.rot("myc4", lin([(-15.0, 1), (10.0, S(1.1, -120))]), None, None)
    swim.rot("myc5", None, None, lin([(-20.0, 1), (10.0, S(1.1, -90))]))
    for k in range(SEGS):
        swim.rot(f"myc6_{k}", lin([(25.0 if k == 0 else 0.0, 1), (8.0 + 4 * k, S(1.1, -60 - 50 * k))]))
    swim.particle(0.0, "motes", "gills")
    swim.kw["length"] = 1.8

    # ------------------------------------------------------------------ idle behaviours
    fid = []
    fold = KeyLayer(r, "fidget_fold", 2.6)   # the crown folds shut plate by plate and is rebuilt in reverse
    for j in range(LIDS):
        a, b = 0.25 + 0.06 * j, 1.35 + 0.06 * (LIDS - 1 - j)
        fold.rot(f"lid{j}", {0: (0, 0, 0), a: (0, 0, 0), a + 0.14: (125, 0, 0), b: (125, 0, 0), b + 0.16: (-12, 0, 0),
                             b + 0.3: (0, 0, 0), 2.6: (0, 0, 0)})
    for k in range(RINGS):
        t0 = 1.75 + 0.035 * k
        fold.scale(f"ring{k}", {0: 1, t0: 1, t0 + 0.15: 1.14, t0 + 0.4: 1, 2.6: 1})
    fold.rot("eye", {0: (0, 0, 0), 0.6: (-5, 0, 0), 1.6: (-5, 0, 0), 2.2: (0, 0, 0), 2.6: (0, 0, 0)})
    fold.particle(1.8, "echo", "eye_c")
    fid.append(fold)

    align = KeyLayer(r, "fidget_align", 2.9)  # the frames click round one sector each, inside out, like a lock
    for k, nside in enumerate(RING_SIDES):
        t0, step = 0.2 + 0.13 * k, 360.0 / nside * (1 if SPIN[k] > 0 else -1)
        align.rot(f"ring{k}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.12: (0, 0, step * 1.08), t0 + 0.24: (0, 0, step),
                               2.9: (0, 0, step)})
        align.pos(f"ring{k}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.08: (0, 0, -0.5), t0 + 0.24: (0, 0, 0), 2.9: (0, 0, 0)})
        align.scale(f"ring{k}", {0: 1, t0: 1, t0 + 0.1: 1.13, t0 + 0.26: 1, 2.9: 1})       # a ripple running outward
    align.scale("pupil", {0: 1, 1.6: 1, 1.75: 1.25, 2.1: 1, 2.9: 1})
    fid.append(align)

    gills = KeyLayer(r, "fidget_gills", 3.0)  # the pores open one pad after the other, the earthstar breathes out
    for p, t0, sz in (("r", 0.2, -3.0), ("l", 0.55, 3.0)):
        gills.scale(f"gill_{p}", {0: 1, t0: 1, t0 + 0.35: (1.1, 3.4, 1.1), 1.9: (1.1, 3.4, 1.1), 2.4: 1, 3.0: 1})
        gills.rot(f"gill_{p}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.35: (0, 0, sz), 1.9: (0, 0, sz), 2.4: (0, 0, 0), 3.0: (0, 0, 0)})
    # the gills open in sequence round the cap: a wave lifts the brim front, right, back, left
    gills.rot("brim", {0: (0, 0, 0), 0.35: (-6, 0, 0), 0.75: (0, 0, 6), 1.15: (6, 0, 0), 1.55: (0, 0, -6), 1.95: (-3, 0, 0),
                       2.4: (0, 0, 0), 3.0: (0, 0, 0)})
    for g, t0 in ((5, 0.5), (2, 0.9), (6, 1.3), (3, 1.7)):      # each group under the lifted edge stirs as it passes
        gills.rot(f"myc{g}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.2: (-10, 0, 0), t0 + 0.5: (3, 0, 0), t0 + 0.7: (0, 0, 0), 3.0: (0, 0, 0)})
    gills.rot("gill_spin", {0: (0, 0, 0), 2.6: (0, 120, 0), 3.0: (0, 120, 0)})
    gills.scale("myc5_2", {0: 1, 0.9: 1, 1.1: (1.18, 0.86, 1.18), 1.3: (0.92, 1.12, 0.92), 1.6: 1, 3.0: 1})
    gills.particle(0.9, "spores", "gills").particle(1.2, "spores", "spores")
    fid.append(gills)

    probe = KeyLayer(r, "fidget_probe", 3.2)  # the sensor reaches into the air; the eye follows its tip
    probe.rot("myc4", {0: (0, 0, 0), 0.45: (-26, 14, 0), 1.0: (-30, 8, 0), 1.35: (-24, 20, 0), 1.75: (-32, 12, 0),
                       2.5: (-26, 14, 0), 3.0: (0, 0, 0), 3.2: (0, 0, 0)})
    probe.rot("myc4_1", {0: (0, 0, 0), 0.45: (-14, 0, 0), 2.5: (-14, 0, 0), 3.0: (0, 0, 0)})
    probe.rot("myc4_2", {0: (0, 0, 0), 0.5: (-10, 0, 0), 1.05: (8, 0, 0), 1.15: (-12, 0, 0), 1.8: (10, 0, 0),
                         1.9: (-10, 0, 0), 2.5: (-10, 0, 0), 3.0: (0, 0, 0), 3.2: (0, 0, 0)})
    probe.rot("eye", {0: (0, 0, 0), 0.5: (10, -16, 0), 1.0: (12, -12, 0), 1.35: (8, -20, 0), 1.75: (12, -14, 0),
                      2.5: (10, -16, 0), 3.0: (0, 0, 0), 3.2: (0, 0, 0)})
    probe.rot("cap", {0: (0, 0, 0), 0.6: (3, -6, 0), 2.5: (3, -6, 0), 3.1: (0, 0, 0)})
    probe.particle(1.05, "motes", "sensor")
    fid.append(probe)
    picks = [("fidget_fold", "math.mod(math.floor(q.life_time * 1.7), 4) == 0"),
             ("fidget_align", "math.mod(math.floor(q.life_time * 1.7), 4) == 1"),
             ("fidget_gills", "math.mod(math.floor(q.life_time * 1.7), 4) == 2"),
             ("fidget_probe", "math.mod(math.floor(q.life_time * 1.7), 4) == 3")]

    # ------------------------------------------------------------------ forms
    intro = {
        "base": KeyLayer(r, "intro_base", 0.8, loop="hold"),
        "sporeveil": None,
        "record": KeyLayer(r, "intro_record", 1.0, loop="hold"),
        "offset": None,
        "frame": KeyLayer(r, "intro_frame", 0.35, loop="hold"),
        "unstable": None,
    }
    ib = intro["base"]                   # the frames bloom out of the void, the crown opens
    for k in range(RINGS):
        t0 = 0.04 * k
        ib.scale(f"ring{k}", {0: 0.2, t0: 0.2, t0 + 0.25: 1.08, t0 + 0.4: 1.0, 0.8: 1.0})
    for j in range(LIDS):
        t0 = 0.25 + 0.03 * j
        ib.rot(f"lid{j}", {0: (125, 0, 0), t0: (125, 0, 0), t0 + 0.22: (-8, 0, 0), t0 + 0.34: (0, 0, 0), 0.8: (0, 0, 0)})
    ib.particle(0.0, "motes", "eye_c")
    # sporeveil: the brim flares and the gill pads hang open (the form's pose), the pores swell, the earthstar opens
    isv = transition(model, r, "intro_sporeveil", "base", "sporeveil", 0.6)
    for p in ("r", "l"):
        isv.bone(f"gill_{p}", scale={0.0: [1, 1, 1], 0.3: [1.2, 2.8, 1.2], 0.6: [1.1, 2.0, 1.1]})
    isv.bone("myc5_2", scale={0.0: [1, 1, 1], 0.2: [1.35, 1.35, 1.35], 0.6: [1.18, 1.18, 1.18]})
    isv.particle(0.05, "spores", "spores").particle(0.1, "spores", "gills")
    intro["sporeveil"] = isv
    ir = intro["record"]                 # the frames click into alignment one by one, from the centre out
    for k in range(RINGS):
        t0 = 0.12 + 0.06 * k
        off = (37.0 if k % 2 else -29.0) * (1.0 - k / 14.0)
        ir.rot(f"ring{k}", {0: (0, 0, off), t0: (0, 0, off), t0 + 0.18: (0, 0, -off * 0.08), t0 + 0.28: (0, 0, 0), 1.0: (0, 0, 0)})
    ir.particle(0.0, "motes", "eye_c")
    intro["offset"] = transition(model, r, "intro_offset", "base", "offset", 0.45)
    intro["offset"].particle(0.0, "echo", "cap_top")
    ifr = intro["frame"]                 # everything halts with a jolt
    for k in range(RINGS):
        ifr.pos(f"ring{k}", {0: (0, 0, 0), 0.06: (0, 0, -0.5), 0.35: (0, 0, 0)})
    ifr.particle(0.0, "echo", "eye_c")
    # unstable: a shudder while the brim sags and the mycelia go limp (the form's pose)
    iun = transition(model, r, "intro_unstable", "base", "unstable", 0.5)
    shudder = KeyLayer(r, "shudder", 0.5)
    hover_keys(shudder, {0: {}, 0.08: {"roll": 5, "bob": -0.6}, 0.2: {"roll": -3}, 0.35: {"roll": 1}, 0.5: {}})
    for bn, ch in shudder.anim().bones.items():
        iun.bones.setdefault(bn, {}).update(ch)
    iun.particle(0.0, "motes", "base_c")
    intro["unstable"] = iun

    sv_loop = Layer(r, "sporeveil_loop", loop=True)   # the mycelia vibrate, the pores pulse
    for g in range(2, 8):
        sv_loop.rot(f"myc{g}", mul(1.6, S(8.0 + 0.7 * g, g * 50)), None, mul(1.2, S(7.1 + 0.5 * g, g * 80)))
    for g, side in SIDES2:
        sv_loop.rot(f"myc{g}_1", mul(1.5, S(7.4, g * 90)), None, None)
    for p in ("r", "l"):
        sv_loop.scale(f"gill_{p}", 1, lin([(1, 1), (0.12, S(3.0, 0 if p == "r" else 90))]), 1)
    sv_loop.rot("brim", mul(0.8, S(3.0)), None, None)
    sv_loop.uscale("myc5_2", lin([(1, 1), (0.05, S(2.0))]))
    sv_loop.kw["length"] = 1.0

    rec_loop = Layer(r, "record_loop", loop=True)     # the eye focuses: frames aligned and tightened, a slow shared turn
    rec_loop.rot("cap", mul(0.15, PITCH), mul(0.35, YAW), None)
    rec_loop.rot("eye", f"math.clamp(q.target_x_rotation * 0.4, -18, 18)", f"math.clamp(q.target_y_rotation * 0.45, -24, 24)", None)
    for k in range(RINGS):
        rec_loop.rot(f"ring{k}", None, None, f"{T} * 9")
        rec_loop.uscale(f"ring{k}", 0.86 + 0.004 * k)
    rec_loop.uscale("pupil", 0.62)
    for j in range(LIDS):
        rec_loop.rot(f"lid{j}", 32.0, None, None)
    rec_loop.rot("gill_spin", None, f"{T} * 3", None)

    off_loop = Layer(r, "offset_loop", loop=True)     # resonant pose: the mycelia spread like fins, the plates hum
    for g in range(2, 8):              # (the fins' spread itself is the form's geometry)
        off_loop.rot(f"myc{g}", mul(3.0, S(0.6, g * 60)), None, mul(2.0, S(0.45, g * 40)))
    for g, side in SIDES2:
        off_loop.rot(f"myc{g}_0", None, None, mirror(side, prod(-18.0, EMPTY_R if side < 0 else EMPTY_L)))
    off_loop.rot("plate_a", None, None, mul(0.6, S(4.0)))
    off_loop.rot("plate_b", None, None, mul(-0.6, S(4.0, 90)))

    frame = KeyLayer(r, "frame_loop", 3.5, loop=True)  # the eleventh frame: the rings open outward one after another
    for k in range(RINGS):
        t0 = 0.2 + 0.11 * k
        sc = 1.22 + 0.055 * k
        dz = -(0.5 + 0.55 * k)
        frame.scale(f"ring{k}", {0: 1, t0: 1, t0 + 0.22: sc * 1.04, t0 + 0.32: sc, 2.55: sc, 2.85 + 0.015 * k: 0.92, 3.1: 1, 3.5: 1})
        frame.pos(f"ring{k}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.22: (0, 0, dz * 1.05), t0 + 0.32: (0, 0, dz),
                               2.55: (0, 0, dz), 2.85 + 0.015 * k: (0, 0, 0.2), 3.1: (0, 0, 0), 3.5: (0, 0, 0)})
    frame.scale("pupil", {0: 1, 0.3: 1.3, 2.6: 1.3, 3.0: 0.85, 3.3: 1, 3.5: 1})
    for j in range(LIDS):
        frame.rot(f"lid{j}", {0: (0, 0, 0), 0.4: (-22, 0, 0), 2.55: (-22, 0, 0), 2.9: (14, 0, 0), 3.2: (0, 0, 0), 3.5: (0, 0, 0)})
    spread = {2: (-25, -30, 10), 3: (-25, 30, -10), 4: (-25, 20, 0), 5: (0, 0, -30), 6: (25, 0, 0), 7: (-15, 0, -12)}
    for g, rot in spread.items():        # the filaments extend outward with the frames, then collapse back
        frame.rot(f"myc{g}", {0: (0, 0, 0), 0.5: rot, 2.55: rot, 3.0: tuple(-0.15 * v for v in rot), 3.3: (0, 0, 0), 3.5: (0, 0, 0)})
        frame.rot(f"myc{g}_1", {0: (0, 0, 0), 0.7: (-8, 0, 0), 2.55: (-8, 0, 0), 3.1: (0, 0, 0), 3.5: (0, 0, 0)})
    hover_keys(frame, {0: {}, 0.4: {"lean": -3, "bob": 0.6}, 2.55: {"lean": -3, "bob": 0.6}, 3.0: {"bob": -0.3}, 3.4: {}, 3.5: {}})
    frame.particle(0.25, "echo", "eye_c").particle(1.4, "motes", "eye_c").particle(2.9, "echo", "eye_c")

    uns = Layer(r, "unstable_loop", loop=True)        # scorched: drooping, twitching, the frames stutter
    hover(uns, roll=mul(1.5, dart(0.9, 2.0, seed=4.4)), bob=lin([(-0.7, 1), (0.25, dart(1.3, 1.0, seed=9.1))]))
    for g, side in SIDES2:
        e = EMPTY_R if side < 0 else EMPTY_L
        uns.rot(f"myc{g}_1", prod(lin([(8.0, 1), (4.0, dart(1.7, 1.0, seed=g + 2.0))]), e), None, None)
    for g in range(2, 8):
        uns.rot(f"myc{g}", mul(5.0, dart(1.1 + 0.13 * g, 1.0, seed=g * 1.9)), None, mul(3.0, dart(1.4 + 0.1 * g, 1.0, seed=g * 3.1)))
    for k in range(RINGS):
        uns.rot(f"ring{k}", None, None, mul(7.0, dart(1.6 + 0.07 * k, 1.0, seed=k * 1.3 + 0.5)))
    for j in range(LIDS):
        uns.rot(f"lid{j}", 18.0, None, None)

    fx = {
        "base": A(r, "fx_base", length=5.0).particle(0.0, "spores", "spores").particle(2.5, "motes", "eye_c"),
        "sporeveil": A(r, "fx_sporeveil", length=0.5).particle(0.0, "spores", "spores").particle(0.25, "spores", "gills"),
        "record": A(r, "fx_record", length=0.9).particle(0.0, "motes", "eye_c"),
        "offset": A(r, "fx_offset", length=0.8).particle(0.0, "echo", "cap_top"),
        "frame": A(r, "fx_frame", length=0.7).particle(0.0, "echo", "eye_c").particle(0.35, "motes", "cap_top"),
        "unstable": A(r, "fx_unstable", length=1.2).particle(0.0, "motes", "base_c"),
    }

    # ------------------------------------------------------------------ the vigil (surveillance idle)
    vigil = {f"controller.animation.{NS}.{r}.vigil": {
        "initial_state": "alive",
        "states": {
            "alive": {"animations": ["life"], "blend_transition": 0.25,
                      "transitions": [{"settle": f"!({BUSY})"}]},
            # life is a looping layer: its length (8 s) outlasts the 7 s wait, so the first
            # animation to finish is always the wait - robust whether or not the engine counts a
            # looped animation as finished
            "settle": {"animations": ["life", "vigil_wait"], "blend_transition": 2.0,
                       "transitions": [{"alive": BUSY}, {"surveil": "q.any_animation_finished"}]},
            "surveil": {"animations": ["surveil"], "blend_transition": 2.0,
                        "transitions": [{"alive": BUSY}]},
        }}}

    built = [fp, tp, steady.anim(), gaze.anim(), glance.anim(), life.anim(), surveil.anim(), loco.anim(), air.anim(),
             land.anim(), land_hard.anim(), atk.anim(), hurt.anim(), swim.anim(), sv_loop.anim(), rec_loop.anim(),
             off_loop.anim(), frame.anim(), uns.anim(),
             wait_anim(r, "vigil_wait", 7.0), wait_anim(r, "fidget_wait", 8.5), wait_anim(r, "fidget_rest", 4.0),
             *[f.anim() for f in fid], *[a.anim() if isinstance(a, KeyLayer) else a for a in intro.values()], *fx.values()]
    controllers = {**landing_controller(r), **fidget_controller(r, picks), **vigil}
    loops = {"sporeveil": "sporeveil_loop", "record": "record_loop", "offset": "offset_loop", "frame": "frame_loop",
             "unstable": "unstable_loop"}
    animate = {}
    for v in VARIANTS:
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("steady", TP), ("vigil", TP)]
        if v not in ("record", "frame"):
            lst += [("gaze", TP), ("glance", TP)]
        if v in ("base", "offset", "unstable"):
            lst.append(("fidget", TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("airborne", f"{TP} && {AIR} && {GAIT_OK}"),
                ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("swim", f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"),
                ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        animate[v] = lst
    particles = {"spores": f"{NS}:geo_spores", "motes": f"{NS}:parallax_motes", "echo": f"{NS}:parallax_echo"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers,
            "pre": shared_vars() + ["v.plr_bob = 0;"] + drain_shared()}
