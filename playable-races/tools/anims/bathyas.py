"""Race 008 Bathyas, the Sun-Impaled (Unique) - attachable animation set (v1.5 premium redesign).

Motion language: heavy, ancient, majestic - and tired.  A titan who has carried a sun through his
heart for longer than he can remember:

  * everything has weight and lands late: a slow rolling walk with the weight carried over each
    stance leg, the arched shell of tergites shifting plate by plate a beat after every footfall,
    the torn fins and the barbels trailing behind (follow_chain drag), the long head swaying low
    and pivoting at the neck (not at the player's head pivot) so it never swings on a stick;
  * a very slow breath (6 s) that lifts the plates one after another, the gills fluttering on the
    exhale; the sword's heartbeat, a lub-dub at 52 bpm, pulsing both coronas and knocking the hilt;
  * an irritable old man: heavy half-closed lids, smooth irritated brow twitches, slow sour
    glances, muttering - never a dart, never anything faster than ~3 Hz at rest;
  * four performed idle behaviours (shield the eyes and grumble, a long sigh with bubbles, doze
    off and jerk awake, poke the wound and wiggle the hilt) and a dramatic entrance for every form.
Every on/off change is eased; keyframed clips are Catmull-Rom with anticipation and overshoot.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from anims.core import NS, n
from anims.life import (ATK, BUMP, CSTEP, EMPTY_L, EMPTY_R, FALL, LOOK, MOVE, PH, POS, RISE, S, SPR, STEP, STILL,
                        TCOS, TURN, KeyLayer, Layer, Rig, arm_swing, body, body_keys, fidget_controller,
                        follow_chain, landing_controller, lin, mul, prod, shared, stride, wait_anim)
from anims.races import A, AIR, GAIT_OK, SIDES, TP, grounded, mirror, pre_animation, shake, view_anims
from models import bathyas as mb
from models.bathyas import CROUCH, PLATES  # noqa: F401  (CROUCH kept for older tooling)

R = "bathyas"
NECK = tuple(float(v) for v in mb._neck("base"))                 # the head pivots here (the base of the neck)
SHOULDER = {s: tuple(float(v) for v in mb._shoulder("base", s)) for s in (-1, 1)}
RIG = Rig("trunk", (0, 12, 0), [("head_g", NECK), ("r_arm_g", SHOULDER[-1]), ("l_arm_g", SHOULDER[1])])
HUNT = {"unshackled", "daybreak"}                                 # drawn: the hunter's breath and heart
NPL = len(PLATES)
PL = [f"plate{k}" for k in range(NPL)]
HOLD_R = "((q.is_item_equipped(0) || (v.attack_time ?? 0) > 0.02) ? 1 : 0)"
HOLD_L = "(q.is_item_equipped(1) ? 1 : 0)"
FREE_R = "(q.is_item_equipped(0) ? 0 : 1)"
FREE_L = "(q.is_item_equipped(1) ? 0 : 1)"
BEAT = 60.0 / 52.0                                                # the sword's heartbeat: 52 bpm
BEAT_HUNT = 60.0 / 76.0                                           # drawn: ~76 bpm
BREATH = 0.16                                                     # Hz: a slow 6 s breath
SLEEP = "q.is_sleeping"
LID = 1.7                                                         # heavy, half-closed old lids (lid scale y)
ATK2 = "math.sin(math.clamp((v.attack_time ?? 0) * 1.3 - 0.15, 0, 1) * 180)"   # the swing, a beat later
STRIKE_R = f"math.pow(math.max(0, -math.cos({PH})), 8)"          # footfalls: right at phase 180, left at 0
STRIKE_L = f"math.pow(math.max(0, math.cos({PH})), 8)"
# solved left-arm gestures (arm group, upper arm, forearm): the hand in front of the eyes; the hand on the hilt
VISOR = {"l_arm_g": (-6.6, 4.3, -35.4), "l_upper": (-79.0, 0.0, 0.0), "l_fore": (-30.6, 0.0, 0.0)}
VISOR_LURE = {"l_arm_g": (-13.6, 25.7, -9.1), "l_upper": (-82.8, 0.0, 0.0), "l_fore": (-29.5, 0.0, 0.0)}
HILT = {"l_arm_g": (-50.7, 51.3, 0.7), "l_upper": (11.8, 0.0, 0.0), "l_fore": (-24.8, 0.0, 0.0)}


def _n(k):
    """Outward normal of plate k in its parent's frame."""
    a = math.radians(PLATES[k][2])
    return np.array([0.0, math.sin(a), math.cos(a)])


def _r3(v):
    return [round(float(x), 3) + 0.0 for x in v]


def heartbeat(period: float, t_off: float = 0.0) -> str:
    """lub-dub: a soft pulse and a weaker one 0.27 s later (eased half-sines, never a spike)."""
    return f"({BUMP(period, 0.24, t_off)} + 0.55 * {BUMP(period, 0.28, t_off - 0.27)})"


def gated_hold(name: str, length: float, t0: float, t1: float, poses: Dict[str, tuple]):
    """A form's held gesture: it eases in between t0 and t1 (with a small overshoot) and then holds;
    every value is gated by its expression (a free hand), so the gesture lets go the moment an item
    is equipped - keyframe values are Molang, re-evaluated every frame."""
    a = A(R, name, loop="hold", length=length)
    for bn, (rot, gate) in poses.items():
        def vec(k):
            return [f"{n(v * k)} * {gate}" if abs(v * k) > 1e-6 else 0 for v in rot]
        span = t1 - t0
        a.bone(bn, rot={0.0: [0, 0, 0], t0: {"post": [0, 0, 0], "lerp_mode": "catmullrom"},
                        t0 + span * 0.55: {"post": vec(0.7), "lerp_mode": "catmullrom"},
                        t0 + span * 0.85: {"post": vec(1.05), "lerp_mode": "catmullrom"},
                        t1: {"post": vec(1.0), "lerp_mode": "catmullrom"}, length: vec(1.0)})
    return a


def pose_keys(kl: KeyLayer, pose: Dict[str, tuple], times):
    """A gesture held between times: {bone: rot} weighted by the given {t: weight} envelope."""
    for bn, rot in pose.items():
        kl.rot(bn, {t: tuple(w * np.array(rot)) for t, w in times.items()})


def stagger(model, name: str, frm: str, to: str, length: float, order: Dict[str, tuple], over: float = -0.1,
            default=None) -> KeyLayer:
    """The entrance of a form: every bone whose rest pose differs between the two forms travels from
    the `frm` pose into the `to` pose with its own (start, duration), eased in and out (Catmull-Rom
    keys) with a small overshoot; bones without an entry share `default` (start, duration)."""
    kl = KeyLayer(R, name, length)
    dflt = default or (0.0, length * 0.7)
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
        st, du = order.get(bn, dflt)
        env = {0.0: 1.0, st: 1.0, st + du * 0.35: 0.72, st + du * 0.75: over, st + du: 0.0, length: 0.0}
        if not np.allclose(dr, 0, atol=0.01):
            kl.rot(bn, {t: tuple(dr * k) for t, k in env.items()})
        if not np.allclose(dt, 0, atol=0.01):
            kl.pos(bn, {t: tuple(dt * k) for t, k in env.items()})
    return kl


def pulse(period: float, rise: float, hold: float, fall: float, off: float, stem: str) -> str:
    """0 -> 1 -> 0 every `period` s: an eased rise, a hold, an eased fall (cosine ease).  The phase and the
    envelope are short pre_animation variables, so no channel expression grows long."""
    ph = shared(f"math.mod(q.life_time + {n(off)}, {n(period)})", stem)
    up = f"math.clamp({ph} / {n(rise)}, 0, 1)"
    dn = f"math.clamp(({ph} - {n(rise + hold)}) / {n(fall)}, 0, 1)"
    return shared(f"0.5 * (math.cos({dn} * 180) - math.cos({up} * 180))", stem)


def neck_pivot(ly: Layer) -> None:
    """The player's head turns about (0, 24, 0); this long head hangs from the neck base far in
    front of it.  Counter-translate head_g so the look rotates the head about NECK instead
    (pos = R^T r - r, R the look rotation, r = NECK - (0, 24, 0)) - and the hunched neck only
    takes 60% of the look pitch."""
    a, b = NECK[1] - 24.0, NECK[2]
    th, ps = "q.target_x_rotation", "q.target_y_rotation"
    ly.pos("head_g",
           f"{n(-b)} * math.sin({ps})",
           f"{n(a)} * math.cos({th}) - {n(b)} * math.cos({ps}) * math.sin({th}) - {n(a)}",
           f"{n(a)} * math.sin({th}) + {n(b)} * math.cos({ps}) * math.cos({th}) - {n(b)}")
    ly.rot("head_g", "-0.4 * math.clamp(q.target_x_rotation, -60, 60)")


def anims(model) -> Dict[str, object]:
    r = R
    rig = RIG
    fp, tp = view_anims(r)
    for p in ("r", "l"):
        fp.bone(f"{p}_delt", scale=0)                             # the deltoids would sit in the first-person view
    hb = shared(heartbeat(BEAT), "plr_hb")
    hb_b = shared(heartbeat(BEAT, -0.06), "plr_hb")
    hb_h = shared(heartbeat(BEAT_HUNT), "plr_hb")
    br = shared(S(BREATH), "plr_br")                              # + inhaling
    ex = shared(f"math.max(0, -{S(BREATH, -25)})", "plr_br")     # the exhale, a little late
    glance = pulse(12.7, 1.1, 1.9, 1.3, 3.0, "plr_gl")           # a slow sour look aside now and then
    mutter = pulse(9.1, 0.4, 1.7, 0.5, 2.0, "plr_mu")            # muttering to himself

    # ------------------------------------------------------------------ the neck: the head turns about its own neck
    neck = Layer(r, "neck", loop=True)
    neck_pivot(neck)

    # ------------------------------------------------------------------ life: breath, the beating sun, an old man's face
    life = Layer(r, "life", loop=True)
    body(life, rig, lean=lin([(-0.8, br), (0.6, prod(glance, STILL))]), roll=mul(0.9, S(0.06, 20)))
    life.rot("chest", lin([(-1.1, br), (0.35, hb)]))             # the hump rises with each breath; the beat knocks
    for k, pl in enumerate(PL):                                   # the plates lift one after another, nape first
        lift = mul(0.17 + 0.01 * k, S(BREATH, -16 * k))
        nn = _n(k)
        life.pos(pl, None, mul(nn[1], lift), mul(nn[2], lift))
        life.rot(pl, mul(-0.8, S(BREATH, -16 * k - 10)))
    for p, side in SIDES:
        life.pos(f"{p}_pauldron", None, mul(0.18, S(BREATH, -30)))
        life.pos(f"{p}_arm_g", None, mul(0.12, S(BREATH, -30)))
    life.pos("head_g", None, mul(0.12, S(BREATH, -45)))
    life.rot("head_g", lin([(1.4, S(0.07)), (3.0, prod(mutter, STILL))]),
             prod(lin([(2.2, S(0.05, 30)), (13.0, glance)]), STILL), mul(1.4, S(0.06, 70)))
    life.uscale("corona_f", lin([(1, 1), (0.08, hb)]))            # the light pulses with the heart
    life.uscale("corona_b", lin([(1, 1), (0.07, hb_b)]))
    life.rot("sword", lin([(0.7, hb)]), None, None)              # the hilt knocks once per beat
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        bl = f"math.max({BUMP(6.3 if side < 0 else 6.6, 0.32)}, {BUMP(10.1, 0.32, 2.4)})"
        life.scale(f"lid_{p}", None, f"{LID} + 1.5 * math.max({bl}, {SLEEP})", None)
        tw = pulse(7.3 if side < 0 else 9.4, 0.35, 0.6, 0.7, 1.1 if side < 0 else 4.2, "plr_tw")   # irritated twitch
        life.rot(f"brow_{p}", mul(5.0, tw), None, mirror(side, mul(-7.0, tw)))
        for k in range(2):                                         # the gills flutter on every exhale
            life.rot(f"gill_{p}{k}", None, mirror(side, lin([(-16.0, ex), (-4.0, prod(ex, S(1.6, 60 * k)))])), None)
        for k in range(3):                                         # fingers stir now and then
            life.rot(f"{p}_finger{k}", None, None, mirror(side, mul(-4.0, S(0.11, 40 * k + (0 if side < 0 else 90)))))
        follow_chain(life, [f"{p}_fin0", f"{p}_fin1"], "x", 2.0, 0.17, lag=45, falloff=1.4, drag=-9.0,
                     drag_falloff=1.3, run_amp=3.0, run_freq=0.9, phase=0 if side < 0 else 60)
        life.rot(f"{p}_fin1", None, mirror(side, mul(5.0, S(0.21, 40 if side < 0 else 120))), None)
        follow_chain(life, [f"barbel_{p}0", f"barbel_{p}1"], "x", 3.0, 0.23, lag=55, falloff=1.35, drag=12.0,
                     drag_falloff=1.3, run_amp=4.0, run_freq=1.1, phase=0 if side < 0 else 80)
    life.rot("jaw", lin([(1.0, 1), (5.0, prod(mutter, POS(S(1.3))))]))
    life.pos("jaws", None, None, mul(-0.2, prod(mutter, POS(S(0.65)))))

    # the drawn forms: a hunter's quick breath and racing heart; lids open, the head steady
    hunt = Layer(r, "life_hunt", loop=True)
    brh = shared(S(0.3), "plr_br")
    hunt.rot("chest", lin([(-0.9, brh), (0.4, hb_h)]))
    for k, pl in enumerate(PL):
        lift = mul(0.12, S(0.3, -22 * k))
        nn = _n(k)
        hunt.pos(pl, None, mul(nn[1], lift), mul(nn[2], lift))
    for p, side in SIDES:
        hunt.pos(f"{p}_arm_g", None, mul(0.1, S(0.3, -30)))
        hunt.scale(f"lid_{p}", None, f"1 + 1.6 * math.max({BUMP(5.3, 0.28)}, {SLEEP})", None)
        for k in range(2):
            hunt.rot(f"gill_{p}{k}", None, mirror(side, lin([(-10.0, 1), (-6.0, f"math.max(0, -{S(0.3, -30)})")])), None)
        follow_chain(hunt, [f"{p}_fin0", f"{p}_fin1"], "x", 1.5, 0.35, lag=40, falloff=1.4, drag=-9.0, run_amp=3.0,
                     run_freq=1.0, phase=0 if side < 0 else 70)
        follow_chain(hunt, [f"barbel_{p}0", f"barbel_{p}1"], "x", 2.0, 0.3, lag=55, falloff=1.35, drag=12.0,
                     run_amp=4.0, run_freq=1.1)
    hunt.rot("head_g", None, mul(1.5, S(0.08)), None)
    hunt.uscale("corona_f", lin([(1, 1), (0.1, hb_h)]))
    hunt.uscale("corona_b", lin([(1, 1), (0.08, hb_h)]))

    # the hands: fingers close round a held item (also in first person); daybreak's sun hides under an off-hand item
    hands = Layer(r, "appendages", loop=True)
    for p, side in SIDES:
        hold = HOLD_R if side < 0 else HOLD_L
        sg = -1 if side < 0 else 1
        for k in range(3):
            hands.rot(f"{p}_finger{k}", None, None, prod(sg * 70, hold))
        hands.rot(f"{p}_thumb", None, None, prod(sg * 38, hold))
    hands.uscale("l_sun", "(q.is_item_equipped(1) ? 0 : 1)")

    # ------------------------------------------------------------------ locomotion: a slow, rolling, lumbering walk
    loco = Layer(r, "locomotion", loop=True)
    s_ = MOVE
    ss = prod(SPR, s_)
    keep = lin([(0.55, 1), (0.15, SPR)])                          # short heavy strides; longer when he hunts
    stride(loco, keep)
    arm_swing(loco, 0.32)                                         # heavy arms barely swing, and late
    for p, side in SIDES:
        sw = STEP() if side < 0 else f"-{STEP()}"                 # + while this leg swings forward
        st = CSTEP() if side < 0 else f"-{CSTEP()}"               # + while this leg pushes off behind
        knee = prod(POS(sw), s_, lin([(34, 1), (20, SPR)]))
        loco.rot(f"{p}_shin", knee)
        flat = prod(side * 1.4, keep, TCOS)                       # the sole stays flat against the stride
        loco.rot(f"{p}_foot", lin([(1.0, flat), (-0.8, knee), (14, prod(POS(st), s_))]))
        e = EMPTY_R if side < 0 else EMPTY_L
        lagg = CSTEP(-55) if side < 0 else f"-{CSTEP(-55)}"
        loco.rot(f"{p}_fore", prod(lin([(-9, f"math.max(0, {lagg})"), (-10, SPR)]), s_, e))   # the forearm trails
        loco.rot(f"{p}_arm_g", prod(-10, ss, e), None, mirror(side, prod(8, ss, e)))         # sprint: arms low and out
        loco.rot(f"{p}_pauldron", None, None, mirror(side, prod(1.6, f"math.sin({PH} * 2 - 60)", s_)))
        for k in range(2):
            loco.rot(f"gill_{p}{k}", None, mirror(side, prod(-10, ss)), None)
    impact = shared(f"{s_} * ({STRIKE_R} + {STRIKE_L})", "plr_bt")
    lean = shared(f"{s_} * (3 + 7 * {SPR})", "plr_bt")
    roll = shared(f"{s_} * (3.2 * {STEP()} + 3 * {TURN})", "plr_bt")      # the weight rolls over each stance leg
    twist = shared(f"0.12 * {LOOK} - 4 * {CSTEP()} * {s_}", "plr_bt")
    body(loco, rig, lean=lean, roll=roll, twist=twist)
    loco.rot("chest", lin([(1.6, s_), (4.0, ss), (1.6, impact)]))
    loco.rot("head_g", lin([(2.5, s_), (-6.0, ss), (2.0, prod(f"math.sin({PH} * 2 - 50)", s_))]),
             prod(2.5, CSTEP(-30), s_), mul(-0.6, roll))          # the head sways low and lags the body
    loco.pos("head_g", None, None, prod(-1.0, ss))
    for k, pl in enumerate(PL):                                   # the plates shift over each other after each footfall
        lag = 30 + 11 * k
        hit = f"math.pow(math.abs(math.cos({PH} - {lag})), 6)"
        nn = _n(k)
        loco.rot(pl, prod(1.8, hit, s_))
        loco.pos(pl, None, prod(-0.14 * nn[1], hit, s_), prod(-0.14 * nn[2], hit, s_))
    loco.rot("sword", prod(1.5, f"math.sin({PH} * 2 - 30)", s_))
    loco.rot("jaw", prod(5.0, ss))                                # panting when he runs
    grounded(model, loco, rig, r, harmonics=8)                    # after every contribution that moves the legs
    for bn in rig.upper():                                        # the trunk settles onto the hips at each footfall
        loco.pos(bn, None, mul(-0.35, impact))

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

    # ------------------------------------------------------------------ airborne: the titan leaves the ground reluctantly
    air = Layer(r, "airborne", loop=True)
    for p, side in SIDES:
        e = EMPTY_R if side < 0 else EMPTY_L
        air.rot(f"{p}_leg_g", lin([(-16, RISE), (-5, FALL)]))
        air.rot(f"{p}_shin", lin([(28, RISE), (8, FALL)]))
        air.rot(f"{p}_foot", lin([(-10, RISE), (12, FALL)]))
        air.rot(f"{p}_arm_g", prod(-9, FALL, e), None, mirror(side, prod(lin([(6, RISE), (15, FALL)]), e)))
        air.rot(f"{p}_fin0", lin([(8, RISE), (-12, FALL)]))
        air.rot(f"barbel_{p}0", lin([(10, RISE), (-18, FALL)]))
        for k in range(3):
            air.rot(f"{p}_finger{k}", None, None, mirror(side, prod(10, FALL, e)))
    for k, pl in enumerate(PL):
        air.rot(pl, lin([(-2.0, RISE), (3.0, FALL)]))
    body(air, rig, lean=lin([(-3, RISE), (5, FALL)]))
    air.rot("head_g", lin([(4, RISE), (-5, FALL)]))
    air.rot("jaw", lin([(6, FALL)]))

    def sink(th, sh, ft):
        """How far the body drops when the legs bend like this (forward kinematics, feet kept on the ground)."""
        from kit.render import bone_matrices
        pose = {}
        for p in ("r", "l"):
            pose[f"{p}_leg_g"] = {"rot": (th, 0, 0)}
            pose[f"{p}_shin"] = {"rot": (sh, 0, 0)}
            pose[f"{p}_foot"] = {"rot": (ft, 0, 0)}
        lo = _lowest(model, pose)
        return lo

    land = KeyLayer(r, "land", 0.6)
    land_hard = KeyLayer(r, "land_hard", 0.9)
    for kl, g in ((land, 1.0), (land_hard, 1.45)):
        L = kl.length
        t1, t2, t3 = 0.08 * g, 0.24 * g, 0.42 * g
        bend = {0.0: (-14 * g, 26 * g), t1: (-18 * g, 34 * g), t2: (-6, 10), t3: (1.5, -2), L: (0, 0)}
        for p, side in SIDES:
            kl.rot(f"{p}_leg_g", {t: (a, 0, 0) for t, (a, b) in bend.items()})
            kl.rot(f"{p}_shin", {t: (b, 0, 0) for t, (a, b) in bend.items()})
            kl.rot(f"{p}_foot", {t: (-(a + b), 0, 0) for t, (a, b) in bend.items()})          # soles stay flat
            kl.rot(f"{p}_fin0", {0: (12 * g, 0, 0), t1 + 0.06: (-8, 0, 0), t3: (3, 0, 0), L: (0, 0, 0)})
            kl.rot(f"barbel_{p}0", {0: (-10, 0, 0), t1 + 0.04: (14 * g, 0, 0), t3: (-4, 0, 0), L: (0, 0, 0)})
            kl.pos(f"{p}_pauldron", {0: (0, 0, 0), t1: (0, -0.5 * g, 0), t2 + 0.05: (0, 0.2, 0), L: (0, 0, 0)})
            kl.particle(0.0, "stepdust", f"{p}_step")
        drops = {t: sink(a, b, -(a + b)) for t, (a, b) in bend.items()}
        lean_k = {0.0: 6 * g, t1: 8 * g, t2: -1.5, t3: 0.5, L: 0.0}
        body_keys(kl, rig, {t: {"bob": -drops[t], "lean": lean_k[t]} for t in bend})
        for k, pl in enumerate(PL):                               # the shell slams down plate by plate, then rebounds
            d = 0.025 * k
            nn = _n(k)
            kl.pos(pl, {0: (0, 0, 0), 0.06 + d: tuple(nn * -0.55 * g), 0.2 + d: tuple(nn * 0.22 * g), 0.36 + d: (0, 0, 0),
                        L: (0, 0, 0)})
        kl.rot("head_g", {0: (-4 * g, 0, 0), 0.1 * g: (8 * g, 0, 0), 0.3 * g: (-2, 0, 0), L: (0, 0, 0)})
        kl.rot("jaw", {0: (0, 0, 0), 0.08: (10 * g, 0, 0), 0.3: (0, 0, 0), L: (0, 0, 0)})
        kl.scale("corona_f", {0: 1, 0.06: 1 + 0.2 * g, 0.25: 1, L: 1})
        for p in ("r", "l"):
            kl.scale(f"lid_{p}", {0: 1, 0.05: (1, 1.7, 1), 0.3: (1, 1.7, 1), 0.45: 1, L: 1})
    land_hard.particle(0.0, "bubbles", "gills")

    # ------------------------------------------------------------------ attack: the whole mass behind a raking claw
    atk = Layer(r, "attack", loop=True)
    body(atk, rig, lean=prod(6, ATK), twist=prod(-9, ATK))
    atk.rot("head_g", prod(5, ATK))
    atk.pos("jaws", None, None, prod(-1.6, ATK2))
    atk.rot("jaw", prod(24, ATK))
    atk.rot("r_fore", prod(-22, ATK2, EMPTY_R))
    for k in range(3):                                            # claws spread, then rake shut
        atk.rot(f"r_finger{k}", prod((k - 1) * 14, ATK, EMPTY_R), None, prod(-34, ATK2, EMPTY_R))
    atk.uscale("corona_f", lin([(1, 1), (0.12, ATK)]))
    for k, pl in enumerate(PL):
        atk.rot(pl, prod(1.5, ATK2))
    for p, side in SIDES:
        atk.rot(f"brow_{p}", prod(4, ATK), None, mirror(side, prod(-8, ATK)))
        atk.scale(f"lid_{p}", None, lin([(1, 1), (0.6, ATK)]), None)
        atk.rot(f"{p}_fin0", prod(-8, ATK2))

    # ------------------------------------------------------------------ hurt: a heavy flinch; the sun in him jolts
    hurt = KeyLayer(r, "hurt", 0.7)
    body_keys(hurt, rig, {0: {}, 0.06: {"lean": -7, "roll": 3}, 0.22: {"lean": 3, "roll": -1}, 0.45: {"lean": -1}, 0.7: {}})
    hurt.rot("head_g", {0: (0, 0, 0), 0.06: (-12, 8, 0), 0.24: (5, -3, 0), 0.45: (-1, 0, 0), 0.7: (0, 0, 0)})
    hurt.rot("jaw", {0: (0, 0, 0), 0.06: (18, 0, 0), 0.28: (5, 0, 0), 0.7: (0, 0, 0)})
    hurt.pos("jaws", {0: (0, 0, 0), 0.06: (0, 0, -1.2), 0.3: (0, 0, 0), 0.7: (0, 0, 0)})
    hurt.scale("corona_f", {0: 1, 0.05: 1.6, 0.22: 1.08, 0.7: 1})
    hurt.scale("corona_b", {0: 1, 0.07: 1.45, 0.25: 1.05, 0.7: 1})
    hurt.rot("sword", {**shake(0.0, 0.5, (4, 3, 0), freq=6, decay=6), 0.7: (0, 0, 0)})
    for k, pl in enumerate(PL):
        hurt.pos(pl, {**shake(0.02 * k, 0.45, tuple(_n(k) * 0.32), freq=6 + k % 3, decay=6), 0.7: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        hurt.scale(f"lid_{p}", {0: 1, 0.05: (1, 1.8, 1), 0.32: (1, 1.8, 1), 0.48: 1, 0.7: 1})
        hurt.rot(f"brow_{p}", {0: (0, 0, 0), 0.05: (6, 0, -sg * 10), 0.4: (3, 0, -sg * 5), 0.7: (0, 0, 0)})
        for k in range(2):
            hurt.rot(f"gill_{p}{k}", {0: (0, 0, 0), 0.06: (0, sg * 22, 0), 0.32: (0, sg * 8, 0), 0.7: (0, 0, 0)})
        hurt.rot(f"{p}_fin0", {**shake(0.0, 0.55, (8, 0, 5 * sg), freq=5, decay=5), 0.7: (0, 0, 0)})
        hurt.pos(f"{p}_pauldron", {0: (0, 0, 0), 0.07: (0, 0.5, 0), 0.25: (0, -0.15, 0), 0.7: (0, 0, 0)})

    # ------------------------------------------------------------------ swimming: an abyssal titan in his element
    swim = Layer(r, "swim", loop=True)
    wf = 0.75                                                     # Hz: a slow, powerful undulation
    swim.rot("trunk", None, None, mul(4.5, S(wf)))
    swim.rot("chest", lin([(-6, 1)]), None, mul(3.5, S(wf, 50)))
    for p, side in SIDES:
        e = EMPTY_R if side < 0 else EMPTY_L
        swim.rot(f"{p}_leg_g", lin([(12, 1), (10, S(wf, -70 if side < 0 else 110))]))     # the legs kick like a tail
        swim.rot(f"{p}_shin", lin([(16, 1), (9, S(wf, -110 if side < 0 else 70))]))
        swim.rot(f"{p}_foot", lin([(28, 1), (12, S(wf, -150 if side < 0 else 30))]))      # wide feet as flukes
        swim.rot(f"{p}_arm_g", prod(lin([(10, 1), (6, S(wf, 30))]), e), None, mirror(side, prod(-6, e)))   # arms trail
        swim.rot(f"{p}_fore", prod(lin([(14, 1), (8, S(wf, -20))]), e))
        swim.rot(f"{p}_fin0", lin([(-14, 1), (8, S(wf * 2, 40))]))
        follow_chain(swim, [f"barbel_{p}0", f"barbel_{p}1"], "x", 8.0, wf, lag=60, falloff=1.4, base=(-20, -10))
        sg = -1 if side < 0 else 1
        for k in range(3):
            swim.rot(f"{p}_finger{k}", lin([((k - 1) * 10, 1)]), None, mul(sg * -10, 1))      # webbed hands spread
        for k in range(2):
            swim.rot(f"gill_{p}{k}", None, mul(sg, lin([(18, 1), (8, S(1.4, k * 60))])), None)
    for k, pl in enumerate(PL):
        swim.rot(pl, mul(2.5, S(wf * 2, -k * 40)), None, mul(2.0, S(wf, -k * 25)))
    swim.rot("head_g", lin([(-10, 1)]), mul(-3.5, S(wf, 20)), None)
    swim.rot("jaw", lin([(6, 1), (4, S(0.5))]))
    swim.particle(0.0, "bubbles", "gills")
    swim.kw["length"] = 1.0 / wf * 2

    # ------------------------------------------------------------------ idle behaviours: an old man, alone with his sun
    fid = []

    # 1. shields his eyes from his own light, grumbling (the off hand comes up as a visor)
    shade = KeyLayer(r, "fidget_shield", 4.8)
    env = {0: 0, 0.35: 0, 0.95: 1.06, 1.15: 1, 3.3: 1, 3.55: 0.92, 4.2: 0, 4.8: 0}
    pose_keys(shade, VISOR, env)
    shade.rot("l_hand", {0: (0, 0, 0), 0.9: (-30, 0, 20), 3.4: (-30, 0, 20), 4.1: (0, 0, 0), 4.8: (0, 0, 0)})
    for k in range(3):
        shade.rot(f"l_finger{k}", {0: (0, 0, 0), 0.9: ((k - 1) * 8, 0, 18), 3.4: ((k - 1) * 8, 0, 18), 4.1: (0, 0, 0)})
    shade.rot("head_g", {0: (0, 0, 0), 0.35: (-4, 0, 0), 0.9: (8, 16, 5), 1.6: (6, 19, 6), 2.3: (8, 13, 4),
                         2.9: (7, 18, 6), 3.5: (6, 15, 4), 4.3: (0, 0, 0), 4.8: (0, 0, 0)})        # turned away, a slow "no"
    body_keys(shade, rig, {0: {}, 0.35: {"lean": -2}, 0.9: {"twist": -6, "lean": -3}, 3.4: {"twist": -6, "lean": -3},
                           4.3: {}, 4.8: {}})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        shade.scale(f"lid_{p}", {0: 1, 0.3: 1, 0.7: (1, 1.75, 1), 3.5: (1, 1.75, 1), 4.2: 1, 4.8: 1})
        shade.rot(f"brow_{p}", {0: (0, 0, 0), 0.6: (6, 0, -sg * 9), 3.5: (6, 0, -sg * 9), 4.2: (0, 0, 0)})
    shade.rot("jaw", {0: (0, 0, 0), 1.1: (0, 0, 0), 1.3: (8, 0, 0), 1.5: (2, 0, 0), 1.75: (9, 0, 0), 2.0: (1, 0, 0),
                      2.3: (6, 0, 0), 2.6: (0, 0, 0), 2.9: (7, 0, 0), 3.2: (0, 0, 0), 4.8: (0, 0, 0)})     # grumbling
    shade.scale("corona_f", {0: 1, 0.6: 1.12, 3.3: 1.12, 4.0: 1, 4.8: 1})
    fid.append(shade)

    # 2. a long, irritated sigh: the hump rises and holds, then everything sags; bubbles leave the gills and jaw
    sigh = KeyLayer(r, "fidget_sigh", 5.2)
    sigh.rot("chest", {0: (0, 0, 0), 1.3: (-6, 0, 0), 1.9: (-6.5, 0, 0), 3.2: (5, 0, 0), 4.2: (4, 0, 0), 5.2: (0, 0, 0)})
    for k, pl in enumerate(PL):
        nn = _n(k)
        sigh.pos(pl, {0: (0, 0, 0), 1.3 + 0.03 * k: tuple(nn * 0.45), 1.9: tuple(nn * 0.45),
                      3.2 + 0.04 * k: tuple(nn * -0.18), 4.4: (0, 0, 0), 5.2: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        sigh.pos(f"{p}_pauldron", {0: (0, 0, 0), 1.3: (0, 0.6, 0), 1.9: (0, 0.6, 0), 3.2: (0, -0.5, 0), 4.4: (0, 0, 0)})
        sigh.pos(f"{p}_arm_g", {0: (0, 0, 0), 1.3: (0, 0.35, 0), 1.9: (0, 0.35, 0), 3.2: (0, -0.4, 0), 4.4: (0, 0, 0)})
        sigh.scale(f"lid_{p}", {0: 1, 1.3: (1, 0.7, 1), 1.9: (1, 0.7, 1), 2.8: (1, 1.75, 1), 4.2: (1, 1.6, 1), 5.2: 1})
        for k in range(2):
            sigh.rot(f"gill_{p}{k}", {0: (0, 0, 0), 2.0 + 0.05 * k: (0, sg * 24, 0), 3.0: (0, sg * 18, 0), 3.6: (0, 0, 0),
                                      5.2: (0, 0, 0)})
        sigh.rot(f"{p}_fin0", {0: (0, 0, 0), 1.3: (-6, 0, 0), 1.9: (-6, 0, 0), 3.3: (5, 0, 0), 4.4: (0, 0, 0)})
    sigh.rot("head_g", {0: (0, 0, 0), 1.3: (-9, 0, 0), 1.9: (-10, 0, 0), 3.2: (12, 0, 4), 4.2: (10, 0, 3), 5.2: (0, 0, 0)})
    sigh.rot("jaw", {0: (0, 0, 0), 1.9: (0, 0, 0), 2.2: (12, 0, 0), 3.0: (9, 0, 0), 3.4: (0, 0, 0), 5.2: (0, 0, 0)})
    sigh.particle(2.1, "bubbles", "maw").particle(2.3, "bubbles", "gills")
    fid.append(sigh)

    # 3. dozes off on his feet, then jerks awake (and pretends he didn't)
    doze = KeyLayer(r, "fidget_doze", 5.6)
    doze.rot("head_g", {0: (0, 0, 0), 1.5: (10, 0, 4), 2.6: (18, 0, 7), 3.5: (24, 0, 9), 3.62: (-14, 0, -2),
                        3.85: (-4, 8, 0), 4.3: (-3, -10, 0), 4.9: (2, 0, 0), 5.6: (0, 0, 0)})
    body_keys(doze, rig, {0: {}, 1.5: {"lean": 3}, 3.5: {"lean": 6, "bob": -0.5}, 3.62: {"lean": -4, "bob": 0.35},
                          3.95: {"lean": 1}, 5.6: {}})
    doze.rot("jaw", {0: (0, 0, 0), 1.8: (6, 0, 0), 3.5: (13, 0, 0), 3.6: (0, 0, 0), 5.6: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        doze.scale(f"lid_{p}", {0: 1, 1.2: (1, 1.5, 1), 2.4: (1, 1.85, 1), 3.55: (1, 1.88, 1), 3.64: (1, 0.35, 1),
                                4.3: (1, 0.45, 1), 4.9: (1, 1.0, 1), 5.6: 1})
        doze.rot(f"brow_{p}", {0: (0, 0, 0), 3.58: (0, 0, 0), 3.68: (-6, 0, sg * 8), 4.4: (-3, 0, sg * 4), 5.0: (0, 0, 0)})
        doze.rot(f"{p}_arm_g", {0: (0, 0, 0), 3.55: (0, 0, 0), 3.66: (-9, 0, -sg * 7), 3.95: (0, 0, 0), 5.6: (0, 0, 0)})
        for k in range(3):
            doze.rot(f"{p}_finger{k}", {0: (0, 0, 0), 3.55: (0, 0, 0), 3.66: ((k - 1) * 16, 0, -sg * 12), 4.1: (0, 0, 0)})
        doze.rot(f"{p}_fin0", {0: (0, 0, 0), 3.5: (4, 0, 0), 3.64: (-14, 0, 0), 4.2: (2, 0, 0), 4.8: (0, 0, 0)})
    doze.scale("corona_f", {0: 1, 2.5: 0.92, 3.55: 0.9, 3.66: 1.45, 4.0: 1, 5.6: 1})
    fid.append(doze)

    # 4. pokes at the wound and wiggles the hilt - and regrets it
    poke = KeyLayer(r, "fidget_poke", 5.2)
    env = {0: 0, 0.25: 0, 0.85: 1.05, 1.0: 1, 3.6: 1, 3.75: 1.03, 4.3: 0, 5.2: 0}
    pose_keys(poke, HILT, env)
    for k in range(3):
        poke.rot(f"l_finger{k}", {0: (0, 0, 0), 0.9: (0, 0, 55), 3.6: (0, 0, 55), 4.1: (0, 0, 0)})
    poke.rot("sword", {0: (0, 0, 0), 1.2: (0, 0, 0), 1.45: (5, 4, 0), 1.7: (-3, -4, 0), 1.95: (4, 3, 0), 2.25: (-1, -1, 0),
                       2.5: (0, 0, 0), 2.95: (0, 0, 0), 3.15: (6, 0, 0), 3.45: (0, 0, 0), 5.2: (0, 0, 0)})
    poke.scale("corona_f", {0: 1, 1.3: 1, 1.48: 1.55, 1.75: 1.2, 2.0: 1.45, 2.4: 1.05, 3.15: 1.8, 3.5: 1, 5.2: 1})
    poke.scale("corona_b", {0: 1, 1.33: 1, 1.52: 1.4, 1.9: 1.05, 3.2: 1.6, 3.55: 1, 5.2: 1})
    poke.rot("head_g", {0: (0, 0, 0), 0.8: (20, 8, 0), 3.05: (19, 8, 0), 3.2: (6, 4, -6), 4.0: (5, 0, -3), 5.2: (0, 0, 0)})
    body_keys(poke, rig, {0: {}, 0.8: {"lean": 4, "twist": 5}, 3.1: {"lean": 6, "twist": 5}, 3.25: {"lean": 0, "twist": 2},
                          4.4: {}, 5.2: {}})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        poke.scale(f"lid_{p}", {0: 1, 1.4: (1, 1.2, 1), 1.5: (1, 1.85, 1), 2.4: (1, 1.5, 1), 3.15: (1, 1.88, 1),
                                3.9: (1, 1.3, 1), 5.2: 1})
        poke.rot(f"brow_{p}", {0: (0, 0, 0), 1.48: (6, 0, -sg * 12), 2.4: (3, 0, -sg * 6), 3.18: (7, 0, -sg * 14),
                               4.2: (0, 0, 0)})
    poke.pos("jaws", {0: (0, 0, 0), 1.48: (0, 0, -0.7), 2.3: (0, 0, -0.4), 3.15: (0, 0, -1.0), 3.9: (0, 0, 0), 5.2: (0, 0, 0)})
    poke.rot("l_hand", {0: (0, 0, 0), 3.75: (0, 0, 0), 4.0: (0, 0, -18), 4.25: (0, 0, 14), 4.5: (0, 0, -8), 4.8: (0, 0, 0)})
    poke.particle(1.48, "sunmotes", "wound").particle(3.15, "sunmotes", "wound").particle(3.2, "sunmotes", "wound_back")
    fid.append(poke)
    picks = [("fidget_shield", "math.mod(math.floor(q.life_time * 1.3), 5) == 0 && !q.is_item_equipped(1)"),
             ("fidget_sigh", "math.mod(math.floor(q.life_time * 1.3), 5) == 1"),
             ("fidget_doze", "math.mod(math.floor(q.life_time * 1.3), 5) == 2"),
             ("fidget_poke", "math.mod(math.floor(q.life_time * 1.3), 5) == 3 && !q.is_item_equipped(1)")]

    # ------------------------------------------------------------------ forms: entrances and loops
    D = np.array(mb._D, float)
    intro = {}

    # base - RETURN: the blade slides the last of the way home, he flinches, then a long grumbling exhale
    ib = KeyLayer(r, "intro_base", 1.5)
    ib.pos("sword", {0.0: tuple(-D * 4.0), 0.12: tuple(-D * 4.0), 0.24: tuple(-D * 2.6), 0.32: tuple(-D * 0.6),
                     0.36: tuple(D * 0.25), 0.44: (0, 0, 0), 1.5: (0, 0, 0)})
    ib.rot("chest", {0: (0, 0, 0), 0.34: (0, 0, 0), 0.4: (8, 0, 0), 0.62: (4, 0, 0), 1.0: (-1.5, 0, 0), 1.5: (0, 0, 0)})
    ib.rot("head_g", {0: (0, 0, 0), 0.34: (0, 0, 0), 0.4: (12, 0, 0), 0.7: (5, 0, 0), 1.05: (-3, 0, 0), 1.5: (0, 0, 0)})
    ib.rot("jaw", {0: (0, 0, 0), 0.34: (0, 0, 0), 0.42: (16, 0, 0), 0.8: (4, 0, 0), 1.5: (0, 0, 0)})
    ib.scale("corona_f", {0: 0.7, 0.34: 0.8, 0.4: 1.7, 0.7: 1.1, 1.5: 1})
    ib.scale("corona_b", {0: 0.8, 0.37: 0.85, 0.44: 1.5, 0.75: 1.05, 1.5: 1})
    for k, pl in enumerate(PL):
        ib.pos(pl, {0: (0, 0, 0), **{round(0.36 + t, 3): tuple(v) for t, v in shake(0.0, 0.4, tuple(_n(k) * 0.3), freq=7,
                                                                                    decay=6).items()}, 1.5: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        ib.scale(f"lid_{p}", {0: 1, 0.34: 1, 0.4: (1, 1.88, 1), 0.9: (1, 1.8, 1), 1.2: 1, 1.5: 1})
        ib.rot(f"brow_{p}", {0: (0, 0, 0), 0.36: (0, 0, 0), 0.42: (7, 0, -sg * 12), 1.0: (3, 0, -sg * 5), 1.5: (0, 0, 0)})
        for k in range(2):
            ib.rot(f"gill_{p}{k}", {0: (0, 0, 0), 0.9: (0, 0, 0), 1.1: (0, sg * 20, 0), 1.4: (0, 0, 0), 1.5: (0, 0, 0)})
    ib.particle(0.36, "sunmotes", "wound").particle(1.0, "bubbles", "gills")
    intro["base"] = ib

    # lure - the sun blazes: a brace, the flare, he recoils from his own light, squints, the hand comes up
    il = stagger(model, "intro_lure", "base", "lure", 0.75, {"chest": (0.1, 0.35), "skull": (0.12, 0.4)},
                 default=(0.1, 0.4))
    il.scale("corona_f", {0.0: 0.75, 0.1: 0.7, 0.22: 1.7, 0.45: 1.2, 0.75: 1.12})
    il.scale("corona_b", {0.0: 0.8, 0.14: 0.8, 0.28: 1.5, 0.75: 1.08})
    for p in ("r", "l"):
        il.scale(f"lid_{p}", {0.0: 1, 0.12: (1, 0.8, 1), 0.2: (1, 1.88, 1), 0.75: (1, 1.75, 1)})
    il.particle(0.18, "glare", "lure_c").particle(0.2, "sunmotes", "wound")
    intro["lure"] = il
    # the off hand rises as a visor - only while it holds nothing (an expression envelope, not keys: it must
    # release the moment an item is equipped)
    holds = {"lure": gated_hold("lure_hold", 0.8, 0.14, 0.5, {**{bn: (rot, FREE_L) for bn, rot in VISOR_LURE.items()},
                                                              "l_hand": ((-30.0, 0.0, 20.0), FREE_L)})}
    lure_loop = Layer(r, "lure_loop", loop=True)
    lure_loop.uscale("corona_f", lin([(1, 1), (0.1, S(0.8)), (0.07, hb)]))
    lure_loop.uscale("corona_b", lin([(1, 1), (0.08, S(0.8, 60))]))
    for p, side in SIDES:
        lure_loop.scale(f"lid_{p}", None, lin([(1, 1), (0.06, S(1.3, 0 if side < 0 else 90))]), None)
        lure_loop.rot(f"brow_{p}", 5, None, mirror(side, -8))
    lure_loop.rot("head_g", None, mul(-3.5, S(0.55)), None)                  # an irritated slow shake
    lure_loop.rot("jaw", mul(4, f"math.max(0, {S(1.1)})"))

    # maw - the jaw shoots out: a pull-back, then the snap
    imw = stagger(model, "intro_maw", "base", "maw", 0.5, {"jaws": (0.1, 0.16), "jaw": (0.12, 0.2), "chest": (0.06, 0.22),
                                                           "skull": (0.06, 0.2)}, over=-0.18, default=(0.06, 0.24))
    imw.pos("jaws", {0.0: (0, 0, 0), 0.08: (0, 0.15, 1.1), 0.17: (0, -0.1, -1.2), 0.26: (0, 0, 0.3), 0.5: (0, 0, 0)})
    imw.rot("head_g", {0.0: (0, 0, 0), 0.08: (-8, 0, 0), 0.18: (6, 0, 0), 0.5: (0, 0, 0)})
    imw.particle(0.15, "bubbles", "maw")
    intro["maw"] = imw
    maw_loop = Layer(r, "maw_loop", loop=True)                     # the jaws keep snapping as he rushes
    maw_loop.rot("jaw", mul(-12, f"math.max(0, {S(1.6)})"))
    maw_loop.pos("jaws", None, None, mul(-0.5, S(1.6, 60)))
    maw_loop.rot("head_g", mul(3, S(1.6, 100)))
    holds["maw"] = gated_hold("maw_hold", 0.4, 0.04, 0.22, {
        **{f"{p}_arm_g": ((10.0, 0.0, 7.0 * -side), FREE_R if side < 0 else FREE_L) for p, side in SIDES},   # swept back
        **{f"{p}_finger{k}": (((k - 1) * 12.0, 0.0, -side * 10.0), FREE_R if side < 0 else FREE_L)
           for p, side in SIDES for k in range(3)}})

    # bastion - the plates close from the tail up, the shoulders slide in over him, the head tucks
    order = {f"plate{k}": (0.04 * (NPL - 1 - k), 0.26) for k in range(NPL)}
    order.update({"r_pauldron": (0.24, 0.24), "l_pauldron": (0.27, 0.24), "skull": (0.12, 0.34), "chest": (0.05, 0.4),
                  "r_fin0": (0.2, 0.3), "l_fin0": (0.22, 0.3)})
    ibs = stagger(model, "intro_bastion", "base", "bastion", 0.75, order, default=(0.1, 0.4))
    ibs.scale("corona_b", {0.0: 1.0, 0.36: 1.55, 0.75: 1.0})
    ibs.particle(0.32, "sunmotes", "back")
    intro["bastion"] = ibs
    bastion_loop = Layer(r, "bastion_loop", loop=True)              # braced: tight breaths, a racing heart
    for k, pl in enumerate(PL):
        nn = _n(k)
        w = mul(0.07, S(0.9, -k * 35))
        bastion_loop.pos(pl, None, mul(nn[1], w), mul(nn[2], w))
    bastion_loop.uscale("corona_b", lin([(1, 1), (0.12, hb_h)]))
    holds["bastion"] = gated_hold("bastion_hold", 0.8, 0.12, 0.5, {
        **{f"{p}_fore": ((-34.0, 0.0, 0.0), FREE_R if side < 0 else FREE_L) for p, side in SIDES},  # folded across him
        **{f"{p}_finger{k}": ((0.0, 0.0, side * -30.0), FREE_R if side < 0 else FREE_L) for p, side in SIDES for k in range(3)}})
    for p, side in SIDES:
        bastion_loop.rot(f"{p}_pauldron", None, None, mirror(side, mul(0.6, S(1.2))))
    body(bastion_loop, rig, roll=mul(0.5, S(0.4)))
    bastion_loop.particle(0.0, "sunmotes", "back")
    bastion_loop.kw["length"] = 1.5

    # unshackled - TORN OUT: the wound bursts open, he rears back, then sinks into the predator's crouch
    iu_order = {"chest": (0.18, 0.55), "skull": (0.22, 0.5), "r_leg_g": (0.3, 0.45), "l_leg_g": (0.3, 0.45),
                "r_shin": (0.32, 0.45), "l_shin": (0.32, 0.45), "r_foot": (0.32, 0.45), "l_foot": (0.32, 0.45),
                "torso_g": (0.3, 0.45), "head_g": (0.3, 0.45), "tail_g": (0.3, 0.45)}
    iu = stagger(model, "intro_unshackled", "base", "unshackled", 1.2, iu_order, default=(0.25, 0.5))
    iu.scale("corona_f", {0.0: 0.3, 0.06: 2.4, 0.3: 1.35, 0.7: 1.08, 1.2: 1.0})
    iu.scale("corona_b", {0.0: 0.5, 0.1: 2.0, 0.4: 1.2, 1.2: 1.0})
    iu.rot("chest", {0.0: (0, 0, 0), 0.08: (-16, 0, 0), 0.25: (-12, 0, 0), 0.6: (2, 0, 0), 1.2: (0, 0, 0)})
    iu.rot("head_g", {0.0: (0, 0, 0), 0.08: (-22, 0, 0), 0.3: (-14, 0, 0), 0.7: (3, 0, 0), 1.2: (0, 0, 0)})
    iu.rot("jaw", {0.0: (0, 0, 0), 0.08: (30, 0, 0), 0.4: (14, 0, 0), 0.8: (0, 0, 0), 1.2: (0, 0, 0)})
    for p, side in SIDES:
        sg = -1 if side < 0 else 1
        iu.scale(f"lid_{p}", {0.0: 1, 0.06: (1, 0.4, 1), 0.5: (1, 0.4, 1), 0.8: (1, 1.0, 1), 1.2: 1})
        iu.rot(f"{p}_fin0", {0.0: (0, 0, 0), 0.08: (-16, 0, 0), 0.4: (-6, 0, 0), 0.8: (2, 0, 0), 1.2: (0, 0, 0)})
        iu.rot(f"{p}_arm_g", {0.0: (0, 0, 0), 0.1: (-8, 0, -sg * 10), 0.5: (-2, 0, -sg * 3), 1.0: (0, 0, 0)})
    for k, pl in enumerate(PL):
        nn = _n(k)
        iu.pos(pl, {0: (0, 0, 0), 0.06 + 0.02 * k: tuple(nn * 0.8), 0.4 + 0.02 * k: tuple(nn * 0.1), 0.8: (0, 0, 0),
                    1.2: (0, 0, 0)})
    iu.particle(0.0, "glare", "wound").particle(0.02, "sunmotes", "wound").particle(0.1, "sunmotes", "wound_back")
    intro["unshackled"] = iu
    unshackled_loop = Layer(r, "unshackled_loop", loop=True)       # the hunter: low, still, claws ready
    holds["unshackled"] = gated_hold("unshackled_hold", 1.2, 0.45, 0.95, {
        **{f"{p}_arm_g": ((-10.0, 0.0, -7.0 * side), FREE_R if side < 0 else FREE_L) for p, side in SIDES},
        **{f"{p}_fore": ((-14.0, 0.0, 0.0), FREE_R if side < 0 else FREE_L) for p, side in SIDES},
        **{f"{p}_finger{k}": (((k - 1) * 12.0, 0.0, side * 18.0), FREE_R if side < 0 else FREE_L)
           for p, side in SIDES for k in range(3)}})
    for p, side in SIDES:
        e = FREE_R if side < 0 else FREE_L
        for k in range(3):                                          # claws flexing, slowly
            unshackled_loop.rot(f"{p}_finger{k}", None, None, prod(side * 6, S(0.35, k * 50), e))
    unshackled_loop.rot("jaw", lin([(3, 1), (2, S(0.3))]))
    unshackled_loop.rot("head_g", mul(1.2, S(0.12)), mul(4.0, S(0.07, 40)), None)   # slowly tracking

    # daybreak - he hunches over the overloading sun, then arches back as the light floods out of every seam
    order = {f"plate{k}": (0.32 + 0.05 * k, 0.35) for k in range(NPL)}
    order.update({"chest": (0.25, 0.5), "skull": (0.3, 0.5), "r_fin0": (0.4, 0.4), "l_fin0": (0.42, 0.4),
                  "r_pauldron": (0.35, 0.4), "l_pauldron": (0.37, 0.4)})
    idb = stagger(model, "intro_daybreak", "lure", "daybreak", 1.3, order, default=(0.28, 0.5))
    idb.rot("chest", {0.0: (0, 0, 0), 0.22: (9, 0, 0), 0.5: (-6, 0, 0), 0.8: (1, 0, 0), 1.3: (0, 0, 0)})
    idb.rot("head_g", {0.0: (0, 0, 0), 0.22: (10, 0, 0), 0.52: (-10, 0, 0), 0.9: (2, 0, 0), 1.3: (0, 0, 0)})
    idb.scale("corona_f", {0.0: 1.1, 0.22: 0.7, 0.42: 2.2, 0.8: 1.3, 1.3: 1.25})
    idb.scale("corona_b", {0.0: 1.0, 0.3: 0.8, 0.5: 1.9, 1.3: 1.2})
    idb.scale("l_sun", {0.0: 0.0, 0.3: 0.0, 0.45: 1.15, 0.6: 1.0, 1.3: 1.0})
    idb.particle(0.0, "glare", "lure_c").particle(0.42, "sunmotes", "back").particle(0.45, "sunmotes", "wound")
    intro["daybreak"] = idb
    daybreak_loop = Layer(r, "daybreak_loop", loop=True)           # strained: trembling in the flood of light
    daybreak_loop.rot("chest", lin([(1.0, S(2.3)), (0.5, S(1.7, 40))]), None, mul(0.6, S(2.1)))
    daybreak_loop.rot("head_g", lin([(1.2, S(2.2, 20))]), mul(1.0, S(1.9)), None)
    daybreak_loop.rot("jaw", lin([(4, S(0.9)), (3, 1)]))
    daybreak_loop.uscale("corona_f", lin([(1, 1), (0.1, S(0.9)), (0.08, hb_h)]))
    daybreak_loop.uscale("corona_b", lin([(1, 1), (0.1, S(0.9, 90))]))
    for k, pl in enumerate(PL):                                    # the plates breathe open and shut, light pulsing out
        nn = _n(k)
        w = mul(0.18, S(0.5, -k * 30))
        daybreak_loop.pos(pl, None, mul(nn[1], w), mul(nn[2], w))
    for p, side in SIDES:
        daybreak_loop.rot(f"{p}_fin0", lin([(3, S(1.5, 0 if side < 0 else 90))]))
    holds["daybreak"] = gated_hold("daybreak_hold", 0.8, 0.3, 0.5, {     # the left fist closes on the sun (when free)
        **{f"l_finger{k}": ((0.0, 0.0, 64.0), FREE_L) for k in range(3)}, "l_thumb": ((0.0, 0.0, 36.0), FREE_L)})

    fx = {
        "base": A(r, "fx_base", length=3.4).particle(0.0, "sunmotes", "wound"),
        "lure": A(r, "fx_lure", length=0.8).particle(0.0, "sunmotes", "wound").particle(0.4, "glare", "lure_c"),
        "maw": A(r, "fx_maw", length=0.3).particle(0.0, "bubbles", "maw"),
        "bastion": A(r, "fx_bastion", length=1.5).particle(0.0, "sunmotes", "wound_back"),
        "unshackled": A(r, "fx_unshackled", length=1.6).particle(0.0, "sunmotes", "wound").particle(0.8, "sunmotes", "wound_back"),
        "daybreak": A(r, "fx_daybreak", length=0.6).particle(0.0, "sunmotes", "wound").particle(0.3, "sunmotes", "back"),
    }
    built = [fp, tp, neck.anim(), life.anim(), hunt.anim(), hands.anim(), loco.anim(), steps["r"].anim(), steps["l"].anim(),
             air.anim(), land.anim(), land_hard.anim(), atk.anim(), hurt.anim(), swim.anim(), lure_loop.anim(),
             maw_loop.anim(), bastion_loop.anim(), unshackled_loop.anim(), daybreak_loop.anim(),
             wait_anim(r, "fidget_wait", 7.0), wait_anim(r, "fidget_rest", 3.5), *[f.anim() for f in fid],
             *[i.anim() for i in intro.values()], *holds.values(), *fx.values()]
    controllers = {**landing_controller(r, hard_speed=-13.0), **fidget_controller(r, picks), **step_ctrl}
    loops = {"lure": "lure_loop", "maw": "maw_loop", "bastion": "bastion_loop", "unshackled": "unshackled_loop",
             "daybreak": "daybreak_loop"}
    swim_on = f"{TP} && (q.is_swimming || (q.is_in_water && !q.is_on_ground))"
    animate = {}
    for v in mb.VARIANTS:
        lst = [("first_person", "c.is_first_person"), ("third_person", TP), ("neck", TP), ("appendages", None),
               ("life_hunt" if v in HUNT else "life", TP)]
        if v == "base":
            lst.append(("fidget", TP))
        lst += [("locomotion", f"{TP} && {GAIT_OK} && !q.is_swimming"), ("steps", f"{TP} && {GAIT_OK}"),
                ("airborne", f"{TP} && {AIR} && {GAIT_OK}"), ("landing", f"{TP} && !q.is_riding"), ("attack", TP),
                ("swim", swim_on), ("hurt", f"{TP} && q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", TP)]
        if v in loops:
            lst.append((loops[v], TP))
        if v in holds:
            lst.append((f"{v}_hold", TP))
        animate[v] = lst
    particles = {"sunmotes": f"{NS}:sun_motes", "bubbles": f"{NS}:abyss_bubbles", "stepdust": f"{NS}:step_dust",
                 "glare": f"{NS}:sun_glare"}
    return {"anims": built, "animate": animate, "particles": particles, "controllers": controllers, "pre": pre_animation(r)}


def _lowest(model, pose) -> float:
    """Lowest point of the legs for a pose of the leg bones (base form)."""
    from kit.geo import rot_matrix
    from kit.render import bone_matrices
    M = bone_matrices(model, "base", pose)
    lo = math.inf
    for root in ("r_leg_g", "l_leg_g"):
        for bn in model.subtree(root):
            off = model.variant_offset(bn, "base")
            for c in model.bones[bn].cubes:
                if c.cutout or c.accent or not c.in_variant("base"):
                    continue
                o, s = np.array(c.origin) + off, np.array(c.size)
                pts = np.array([[o[0] + s[0] * i, o[1] + s[1] * j, o[2] + s[2] * k]
                                for i in (0, 1) for j in (0, 1) for k in (0, 1)])
                if c.rot is not None:
                    cp = np.array(c.pivot if c.pivot else c.origin) + off
                    pts = (pts - cp) @ rot_matrix(c.rot).T + cp
                w = np.c_[pts, np.ones(8)] @ M[bn].T
                lo = min(lo, float(w[:, 1].min()))
    return lo
