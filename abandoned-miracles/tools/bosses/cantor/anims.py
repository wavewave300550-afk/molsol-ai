"""
Cantor XIII - rig animation.

Three legs, so nothing is ever symmetrical: one leg swings while two bear the
weight, and the whole tower lurches towards the pair that is planted. The gait
is driven by distance travelled and the turn by yaw turned (each leg has its
own phase), so feet stay planted at any speed. A leg at azimuth a strides by
swinging its hip (the tangential share, sin a) and by reaching with its shin
(the radial share, cos a) - the front leg reaches, the rear legs swing.

Everything that sounds is animated as an instrument: the great bell and its
clapper, the four eave bells, the pipe ranks, the shutters, the windows.
Attack keyframes come from shared/cantor.timings.json.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from kit import molang as M
from kit.anim import Anim, ClientEntity, Controller, combine
from kit.molang import E, cond, cos, mod, prop, q, sin, v

A = "animation.abm.cantor."
LEGS = {1: 0.0, 2: 125.0, 3: 235.0}            # azimuth from the front, towards the left
PHASE = {1: 0.0, 2: 1 / 3, 3: 2 / 3}
PIPES = ["pipe_c1", "pipe_c2", "pipe_c3"] + [f"pipe_{t}{k}" for t in "lr" for k in (1, 2, 3, 4)]
SMALL = ["bell_s1", "bell_s2", "bell_s3", "bell_s4"]
STRIDE_T, STRIDE_R, LIFT = 16.0, 10.0, 11.0


def sec(ticks: float) -> float:
    return round(ticks / 20.0, 4)


def merge(*poses: Dict[str, dict]) -> Dict[str, dict]:
    return combine(*poses)


def stance(drop: float = 0.0, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0, fwd: float = 0.0,
           side: float = 0.0) -> Dict[str, dict]:
    """Sink (drop > 0) or rise on the three legs; thighs fold and feet stay flat."""
    pose: Dict[str, dict] = {"body": {"pos": [side, -drop, -fwd], "rot": [pitch, yaw, roll]}}
    d = drop * 1.3
    for n in LEGS:
        pose[f"leg_{n}_a"] = {"rot": [0, 0, -d]}
        pose[f"leg_{n}_c"] = {"rot": [0, 0, d]}
    return pose


def bell(x: float = 0.0, z: float = 0.0, clap: float = 1.0) -> Dict[str, dict]:
    """Tilt the great bell; the clapper lags the other way."""
    return {"bell": {"rot": [x, 0, z]}, "clapper": {"rot": [-x * 0.9 * clap, 0, -z * 0.9 * clap]}}


def pipes(rise: float = 0.0, names=PIPES, stagger: float = 0.0) -> Dict[str, dict]:
    return {n: {"pos": [0, rise + stagger * i, 0]} for i, n in enumerate(names)}


def wings(open_: float = 0.0, fan: float = 0.0, sweep: float = 0.0) -> Dict[str, dict]:
    """Unfold the two pipe wings: the rail tilts outward and every pipe leans further than the last."""
    pose = {"wing_l": {"rot": [0, -sweep, open_]}, "wing_r": {"rot": [0, sweep, -open_]}}
    for k in (1, 2, 3, 4):
        pose[f"pipe_l{k}"] = {"rot": [0, 0, fan * k]}
        pose[f"pipe_r{k}"] = {"rot": [0, 0, -fan * k]}
    return pose


def windows(front: float = 0.0, sides: float = 0.0) -> Dict[str, dict]:
    return {"panel_f": {"rot": [0, front, 0]}, "panel_l": {"rot": [0, -sides, 0]}, "panel_r": {"rot": [0, sides, 0]}}


def shutters(a: float = 0.0) -> Dict[str, dict]:
    return {"shutter_l": {"rot": [a, 0, 0]}, "shutter_r": {"rot": [a, 0, 0]}}


def small_bells(out: float = 0.0, twist: float = 0.0) -> Dict[str, dict]:
    sign = {"bell_s1": (1, -1), "bell_s2": (-1, -1), "bell_s3": (1, 1), "bell_s4": (-1, 1)}
    return {n: {"rot": [-out * sz + twist, 0, out * sx]} for n, (sx, sz) in sign.items()}


# The broken stance of Phase II: wings fanned, bell askew, the whole tower listing.
P2_POSE = merge(wings(open_=36, fan=9, sweep=14), stance(drop=3, pitch=-4, roll=3), bell(-9, 7, 0.4),
                windows(18, 12), shutters(-30), pipes(5, ["pipe_c1", "pipe_c2", "pipe_c3"]))


def client_entity() -> ClientEntity:
    ce = ClientEntity("abm:cantor_xiii", "geometry.abm.cantor_xiii", "textures/entity/abm/cantor_xiii")
    ce.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha"}
    ce.render_controllers = ["controller.render.abm.cantor"]
    p2 = ce.var("p2", prop("abm:phase").eq(2))
    ce.var("duty", cond(p2, 0.66, 0.72))
    ce.var("gait", M.BLOCKS_MOVED * cond(p2, 0.5, 0.411))
    ce.var("turn", (v("yaw") + 3600) / 60.0)        # v.yaw: see kit.anim.add_facing
    ce.var("go", M.clamp(q("modified_move_speed") * 5, 0, 1))
    for n, off in PHASE.items():
        ce.var(f"w{n}", mod(v("gait") + off, 1))
        ce.var(f"t{n}", mod(v("turn") + off, 1))
    # the pulse the windows keep: two beats a second, uneven once the symphony is broken
    from kit.anim import add_clock
    lt = add_clock(ce)
    ce.var("lit", cond(prop("abm:silent").eq(1), 0,
                       cond(p2, (sin(lt * 520) + sin(lt * 333)).gt(-0.4), sin(lt * 720).gt(-0.35))))
    return ce


def stroke(p: E, duty) -> E:
    duty = E.of(duty)
    return cond(p.lt(duty), 1 - p * 2 / duty, (p - duty) * 2 / (1 - duty) - 1)


def lift(p: E, duty) -> E:
    duty = E.of(duty)
    return cond(p.lt(duty), 0, sin((p - duty) / (1 - duty) * 180))


def build_base() -> List[Anim]:
    lt = q("life_time")
    go, gait, lit = v("go"), v("gait"), v("lit")

    idle = Anim(A + "idle", loop=True)
    idle.rot("bell", sin(lt * 90) * 3, 0, sin(lt * 61 + 40) * 2.2)
    idle.rot("clapper", -sin(lt * 90 - 35) * 4, 0, -sin(lt * 61 + 5) * 3)
    sign = {"bell_s1": (1, -1), "bell_s2": (-1, -1), "bell_s3": (1, 1), "bell_s4": (-1, 1)}
    for i, (n, (sx, sz)) in enumerate(sign.items()):
        idle.rot(n, sin(lt * (70 + i * 13) + i * 80) * 5, 0, sin(lt * (83 + i * 9) + i * 50) * 5)
    for i, n in enumerate(PIPES):                                  # the ranks breathe
        idle.set(n, "pos", [0, sin(lt * 180 + i * 47) * 0.5, 0])
    idle.rot("shutter_l", sin(lt * 140) * 3, 0, 0).rot("shutter_r", sin(lt * 140 + 90) * 3, 0, 0)
    idle.set("body", "pos", [0, sin(lt * 90) * 0.5, 0])
    idle.scale("core_glow", 1 + sin(lt * 720) * 0.06)
    idle.set("reeds", "pos", [sin(lt * 2900) * 0.08, 0, 0])
    # stained glass is lit by moving the bright pane in front of / behind its dark backing
    idle.set("panel_f_glow", "pos", [0, 0, (1 - lit) * 0.9])
    idle.set("panel_l_glow", "pos", [(1 - lit) * -0.6, 0, 0])
    idle.set("panel_r_glow", "pos", [(1 - lit) * 0.6, 0, 0])

    walk = Anim(A + "walk", loop=True)
    turn = Anim(A + "turn", loop=True)
    duty = v("duty")
    for n, az in LEGS.items():
        pw, pt = v(f"w{n}"), v(f"t{n}")
        s, c = math.sin(math.radians(az)), math.cos(math.radians(az))
        sw, lw = stroke(pw, duty), lift(pw, duty)
        walk.rot(f"leg_{n}", 0, sw * (STRIDE_T * s), 0)
        walk.rot(f"leg_{n}_a", 0, 0, lw * -LIFT)
        walk.rot(f"leg_{n}_b", 0, 0, sw * (-STRIDE_R * c))
        walk.rot(f"leg_{n}_c", 0, 0, lw * LIFT + sw * (STRIDE_R * c))
        st, ltn = stroke(pt, 0.72), lift(pt, 0.72)
        turn.rot(f"leg_{n}", 0, st * 21.6, 0)
        turn.rot(f"leg_{n}_a", 0, 0, ltn * -9)
        turn.rot(f"leg_{n}_c", 0, 0, ltn * 9)
    # the tower drops onto each footfall and leans over whichever pair is planted
    walk.set("body", "pos", [0, M.mabs(sin(gait * 540)) * -2.4 * go, 0])
    walk.set("body", "rot", [cos(gait * 360) * 2.6 * go, 0, sin(gait * 360) * 3.4 * go])
    walk.rot("bell", cos(gait * 360 - 80) * 6 * go, 0, sin(gait * 360 - 80) * 7 * go)
    walk.rot("clapper", -cos(gait * 360 - 140) * 8 * go, 0, -sin(gait * 360 - 140) * 9 * go)
    for i, n in enumerate(SMALL):
        walk.rot(n, cos(gait * 360 - 120 - i * 30) * 11 * go, 0, sin(gait * 360 - 120 - i * 30) * 12 * go)
    for i, n in enumerate(PIPES):
        walk.set(n, "pos", [0, M.mabs(sin(gait * 540 - 30 - i * 9)) * -1.1 * go, 0])
    walk.rot("wing_l", 0, 0, sin(gait * 360 - 60) * 2 * go).rot("wing_r", 0, 0, sin(gait * 360 - 60) * 2 * go)
    walk.rot("shutter_l", M.mabs(sin(gait * 540)) * -8 * go, 0, 0).rot("shutter_r", M.mabs(sin(gait * 540)) * -8 * go, 0, 0)

    hold = Anim(A + "p2_pose", loop=True)
    for b, ch in P2_POSE.items():
        for c, val in ch.items():
            hold.set(b, c, val)
    wobble = Anim(A + "p2_unstable", loop=True)
    wobble.set("body", "rot", [sin(lt * 130) * 2 + sin(lt * 47) * 1.5, 0, sin(lt * 97 + 30) * 2.4 + sin(lt * 31) * 1.6])
    wobble.rot("bell", sin(lt * 210) * 5 + sin(lt * 77) * 4, 0, sin(lt * 163 + 60) * 5)
    wobble.rot("clapper", -sin(lt * 210 - 50) * 9, 0, -sin(lt * 163) * 8)
    wobble.rot("wing_l", 0, sin(lt * 150) * 3, sin(lt * 260) * 2.5 + sin(lt * 71) * 3)
    wobble.rot("wing_r", 0, -sin(lt * 150 + 70) * 3, -sin(lt * 260 + 40) * 2.5 - sin(lt * 71 + 90) * 3)
    for k in (1, 2, 3, 4):
        wobble.rot(f"pipe_l{k}", sin(lt * (190 + k * 23)) * 2.5, 0, 0).rot(f"pipe_r{k}", sin(lt * (205 + k * 19)) * 2.5, 0, 0)
    wobble.scale("bell_crack_glow", 1 + sin(lt * 900) * 0.04)

    steps = Anim(A + "footfalls", length=2.0, loop=True)

    steps.pos("root", 0, 0, 0)        # a sound-only animation still needs one bone channel (see Anim.json)
    for t in (0.0, 0.667, 1.333):
        steps.sound(t, "step")
    return [idle, walk, turn, hold, wobble, steps]


# --------------------------------------------------------------------------- attacks

def toll(a: Anim, t: float, x: float, z: float, wind: float = 0.45, bones_dip: float = 7.0) -> List[Tuple]:
    """Key frames for one toll of the great bell peaking at time t (wind-up, strike, ring-down)."""
    return [(t - wind, merge(bell(-x * 1.25, -z * 1.25), stance(drop=-2)), "out"),
            (t - 0.06, merge(bell(-x * 1.25, -z * 1.25), stance(drop=-2)), "linear"),
            (t + 0.05, merge(bell(x, z), stance(drop=bones_dip, pitch=x * 0.25, roll=-z * 0.25), small_bells(14)), "snap"),
            (t + 0.35, merge(bell(-x * 0.5, -z * 0.5), stance(drop=1)), "out"),
            (t + 0.7, merge(bell(x * 0.25, z * 0.25)), "inout")]


def downbeat(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    strike, end = sec(t["strike"]), sec(t["end"])
    a = Anim(A + f"downbeat_p{phase}", length=end, loop="hold")
    frames = [(0, {})]
    frames.append((strike * 0.55, merge(bell(-30, 0), stance(drop=7, pitch=-5), shutters(-40), pipes(-3)), "out"))
    frames += toll(a, strike, 20, 0, wind=0.3, bones_dip=11)[1:]
    a.sound(0.05, "creak").sound(strike - 0.02, "bell_strike").particle(strike, "spark", "bell").particle(strike, "dust", "base")
    if phase == 2:
        second = sec(t["second"])
        frames += toll(a, second, 4, 24, wind=0.4, bones_dip=9)
        a.sound(second - 0.02, "bell_strike").particle(second, "spark", "bell")
    frames += [(end - 0.6, {}, "inout"), (end, {})]
    a.poses(frames)
    return [a]


def counterpoint(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    first, second, end = sec(t["first"]), sec(t["second"]), sec(t["end"])
    a = Anim(A + f"counterpoint_p{phase}", length=end, loop="hold")
    left = [f"pipe_l{k}" for k in (1, 2, 3, 4)]
    right = [f"pipe_r{k}" for k in (1, 2, 3, 4)]
    up_l = merge(pipes(7, left, 2.0), wings(open_=10), stance(roll=5, drop=2), bell(0, -10))
    up_r = merge(pipes(7, right, 2.0), wings(open_=10), stance(roll=-5, drop=2), bell(0, 10))
    down_l = merge(pipes(-4, left), stance(roll=-4, drop=6), bell(0, 12), shutters(-45))
    down_r = merge(pipes(-4, right), stance(roll=4, drop=6), bell(0, -12), shutters(-45))
    a.poses([(0, {}), (first - 0.5, up_l, "out"), (first - 0.06, up_l, "linear"), (first + 0.05, down_l, "snap"),
             (first + 0.5, {}, "out"), (second - 0.5, up_r, "inout"), (second - 0.06, up_r, "linear"),
             (second + 0.05, down_r, "snap"), (second + 0.6, {}, "out"), (end, {})])
    a.sound(first - 0.5, "organ_rise").sound(first, "wave").sound(second - 0.5, "organ_rise").sound(second, "wave")
    a.particle(first, "note", "wing_l").particle(second, "note", "wing_r")
    return [a]


def glass_aria(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    open_, first, gap, n, end = sec(t["open"]), sec(t["first"]), sec(t["gap"]), t["volleys"], sec(t["end"])
    a = Anim(A + f"aria_p{phase}", length=end, loop="hold")
    wide = merge(windows(104, 78), stance(drop=-3, pitch=-6), bell(-8, 0), shutters(-20))
    frames = [(0, {}), (open_, wide, "back")]
    for i in range(n):
        tm = first + i * gap
        kick = merge(wide, stance(drop=3, pitch=-11, fwd=-4), bell(-16, (8 if i % 2 else -8)))
        frames += [(tm - 0.08, wide, "linear"), (tm + 0.04, kick, "snap"), (tm + 0.3, wide, "out")]
        a.sound(tm - 0.02, "glass_shard").particle(tm, "glass", "chest")
    last = first + (n - 1) * gap
    frames += [(last + 0.7, merge(windows(20, 14)), "inout"), (end - 0.3, {}, "inout"), (end, {})]
    a.poses(frames)
    a.sound(0.05, "glass_open")
    if phase == 2:
        w = sec(t["wave"])
        a.sound(w - 0.02, "bell_strike").particle(w, "spark", "bell")
    return [a]


def held_note(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    blast, end = sec(t["blast"]), sec(t["end"])
    a = Anim(A + f"held_p{phase}", length=end, loop="hold")
    swell = merge(pipes(11, PIPES, 0.4), wings(open_=14, fan=2), stance(drop=-5, pitch=-12), bell(-22, 0, 0.3),
                  shutters(-70), {"core_glow": {"scale": [1.5, 1.2, 1.5]}})
    fire = merge(pipes(-5), wings(open_=4), stance(drop=8, pitch=12, fwd=7), bell(16, 0), shutters(-10))
    frames = [(0, {}), (blast * 0.3, merge(pipes(4, PIPES, 0.15), shutters(-30), stance(drop=-2, pitch=-4)), "out"),
              (blast - 0.12, swell, "in"), (blast + 0.05, fire, "snap"), (blast + 0.6, merge(stance(drop=2, pitch=4)), "out")]
    a.sound(0.05, "organ_charge").sound(blast - 0.02, "organ_blast")
    a.particle(blast * 0.3, "note", "pipe_top").particle(blast * 0.65, "note", "pipe_top").particle(blast, "spark", "chest")
    if phase == 2:
        echo = sec(t["echo"])
        frames += [(echo - 0.5, merge(pipes(8, PIPES, 0.3), stance(drop=-3, pitch=-8), bell(-14, 6), shutters(-60)), "out"),
                   (echo - 0.08, merge(pipes(8, PIPES, 0.3), stance(drop=-3, pitch=-8), bell(-14, 6), shutters(-60)), "linear"),
                   (echo + 0.05, fire, "snap"), (echo + 0.6, {}, "out")]
        a.sound(echo - 0.02, "organ_blast").particle(echo, "spark", "chest")
    frames += [(end - 0.4, {}, "inout"), (end, {})]
    a.poses(frames)
    return [a]


def silent_measure(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    freeze, strike, end = sec(t["freeze"]), sec(t["strike"]), sec(t["end"])
    a = Anim(A + f"silent_p{phase}", length=end, loop="hold")
    # It starts exactly like Prime Downbeat ... and then holds its breath: bell arrested mid-swing,
    # pipes drawn in, shutters shut, eave bells pinned still. (The script also darkens the windows.)
    held = merge(bell(-36, 0, 0.0), stance(drop=10, pitch=-7), pipes(-8), shutters(18), small_bells(0),
                 wings(open_=-6), {"core_glow": {"scale": [0.5, 0.5, 0.5]}})
    burst = merge(bell(22, 0), stance(drop=-6, pitch=6), pipes(8), shutters(-60), small_bells(22))
    frames = [(0, {}), (freeze * 0.75, merge(bell(-30, 0), stance(drop=7, pitch=-5), shutters(-40)), "out"),
              (freeze, held, "snap"), (strike - 0.1, held, "linear"), (strike + 0.05, burst, "snap"),
              (strike + 0.6, merge(bell(-8, 0)), "out")]
    a.sound(0.05, "creak").sound(freeze, "silence").sound(strike - 0.02, "implode")
    a.particle(strike, "spark", "bell").particle(strike, "dust", "base")
    if phase == 2:
        second = sec(t["second"])
        frames += [(second - 0.3, merge(bell(-26, 10), stance(drop=6)), "out"), (second + 0.05, merge(burst, bell(18, -12)), "snap"),
                   (second + 0.6, {}, "out")]
        a.sound(second - 0.02, "implode").particle(second, "spark", "bell")
    frames += [(end - 0.5, {}, "inout"), (end, {})]
    a.poses(frames)
    return [a]


def twin_resonance(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    det, end = sec(t["detach"]), sec(t["end"])
    a = Anim(A + f"twin_p{phase}", length=end, loop="hold")
    wind = merge(stance(drop=6, roll=0, pitch=6), bell(10, 0), {"bell_s1": {"rot": [30, 0, -30]}, "bell_s2": {"rot": [30, 0, 30]}})
    fling = merge(stance(drop=-5, pitch=-10), bell(-14, 0), {"bell_s1": {"rot": [-95, 0, 80]}, "bell_s2": {"rot": [-95, 0, -80]}},
                  small_bells(0))
    a.poses([(0, {}), (det * 0.7, wind, "out"), (det - 0.06, wind, "linear"), (det + 0.05, fling, "snap"),
             (det + 0.5, merge(stance(drop=1)), "out"), (end, {}, "inout")])
    a.sound(0.05, "creak").sound(det - 0.02, "detach").particle(det, "spark", "bell_s1").particle(det, "spark", "bell_s2")
    return [a]


def final_requiem(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    strikes, end = [sec(x) for x in t["strikes"]], sec(t["end"])
    a = Anim(A + f"requiem_p{phase}", length=end, loop="hold")
    tall = merge(stance(drop=-8), wings(open_=18, fan=3), pipes(8, PIPES, 0.3), shutters(-60), windows(60, 40))
    frames = [(0, {}), (strikes[0] * 0.5, tall, "out")]
    swing = [(20, 0), (0, 22), (-20, 0), (0, -22)]
    groups = [["pipe_c1", "pipe_c2", "pipe_c3"], [f"pipe_l{k}" for k in (1, 2, 3, 4)],
              [f"pipe_r{k}" for k in (1, 2, 3, 4)], PIPES]
    for i, tm in enumerate(strikes):
        x, z = swing[i % 4]
        up = merge(tall, bell(-x * 1.2, -z * 1.2), pipes(14, groups[i % 4]))
        hit = merge(tall, bell(x, z), stance(drop=4, pitch=x * 0.3, roll=-z * 0.3), pipes(-2, groups[i % 4]), small_bells(18))
        frames += [(tm - 0.45, up, "out"), (tm - 0.06, up, "linear"), (tm + 0.05, hit, "snap"), (tm + 0.5, tall, "out")]
        a.sound(tm - 0.02, f"requiem_{i + 1}").particle(tm, "spark", "bell").particle(tm, "note", "pipe_top")
    frames += [(end - 0.7, {}, "inout"), (end, {})]
    a.poses(frames)
    a.sound(0.05, "requiem_start")
    return [a]


# --------------------------------------------------------------------------- set pieces

def set_pieces(T: dict) -> List[Anim]:
    out: List[Anim] = []

    ti = T["intro"]
    wake, toll_t, total = sec(ti["wake"]), sec(ti["toll"]), sec(ti["total"])
    asleep = merge(stance(drop=24, pitch=10), bell(34, 0, 0.0), pipes(-12), shutters(20), wings(open_=-8), small_bells(0),
                   {"core_glow": {"scale": [0.2, 0.2, 0.2]}})
    intro = Anim(A + "intro", length=total, loop="hold")
    frames = [(0, asleep), (wake * 0.6, asleep, "linear"), (toll_t - 0.5, merge(stance(drop=-4), bell(-26, 0), pipes(6)), "inout")]
    frames += toll(intro, toll_t, 18, 0, wind=0.3, bones_dip=8)[1:]
    frames += [(total, {}, "inout")]
    intro.poses(frames)
    intro.sound(wake * 0.6, "intro").sound(toll_t - 0.02, "bell_strike").particle(toll_t, "spark", "bell").particle(wake, "dust", "base")
    out.append(intro)

    ts = sec(T["stagger"]["total"])
    slump = merge(stance(drop=12, pitch=14, roll=-9), bell(26, -14, 0.2), pipes(-6, PIPES, -0.3), wings(open_=-4),
                  shutters(10), small_bells(26))
    stag = Anim(A + "stagger", length=ts, loop="hold")
    stag.poses([(0, {}), (0.25, slump, "snap"), (0.6, merge(slump, bell(18, 10, 0.2)), "inout"), (ts - 0.6, slump, "inout"),
                (ts, {}, "inout")])
    stag.sound(0.02, "stagger").particle(0.05, "spark", "bell")
    out.append(stag)

    tt = T["transition"]
    crack, brk, unfold, total = sec(tt["crack"]), sec(tt["break"]), sec(tt["unfold"]), sec(tt["total"])
    tr = Anim(A + "transition", length=total, loop="hold")
    frames = [(0, {})]
    k, tm = 0, 0.2
    while tm < crack:                                      # the bell rings itself apart
        amp = 10 + 22 * tm / crack
        frames.append((tm, merge(bell(amp if k % 2 else -amp, (amp * 0.4 if k % 4 < 2 else -amp * 0.4)), stance(drop=2 + k % 2)), "inout"))
        tm += 0.22
        k += 1
    reel = merge(bell(-34, 12, 0.2), stance(drop=14, pitch=-10, roll=6), shutters(-70), pipes(-5))
    frames += [(crack + 0.1, reel, "snap"), (brk - 0.1, merge(reel, bell(-30, 16, 0.2)), "linear"),
               (brk + 0.08, merge(bell(22, -8), stance(drop=16, pitch=12, roll=-4), pipes(6)), "snap"),
               (unfold, merge(P2_POSE, pipes(9, PIPES, 0.2)), "inout"),
               (unfold + 0.5, merge(P2_POSE, wings(open_=12, fan=3), stance(drop=-6, pitch=-10), pipes(14, PIPES, 0.4)), "out"),
               (total - 0.35, merge(P2_POSE, wings(open_=12, fan=3), stance(drop=-6, pitch=-10), pipes(14, PIPES, 0.4)), "linear"),
               (total, P2_POSE, "inout")]
    tr.poses(frames)
    # the lost piece of the lip tumbles to the floor (it is hidden for good once Phase II is live)
    tr.track("bell_chunk", "pos", [(0, [0, 0, 0]), (brk, [0, 0, 0], "linear"), (brk + 0.7, [22, -138, -26], "in"),
                                   (brk + 0.85, [24, -132, -28], "out"), (brk + 1.0, [25, -138, -29], "in")])
    tr.track("bell_chunk", "rot", [(0, [0, 0, 0]), (brk, [0, 0, 0], "linear"), (brk + 0.7, [150, 40, 110], "linear"),
                                   (brk + 1.0, [180, 50, 120], "out")])
    tr.sound(0.05, "transition_ring").sound(crack, "transition_crack").sound(brk, "transition_break")
    tr.sound(unfold - 0.6, "transition_unfold").sound(unfold + 0.4, "transition_roar")
    tr.particle(crack, "spark", "bell").particle(brk, "fragments", "bell").particle(unfold + 0.5, "note", "wing_l")
    tr.particle(unfold + 0.5, "note", "wing_r").particle(brk + 0.8, "dust", "base")
    out.append(tr)

    # ---- death (authored over the Phase II stance)
    td = T["death"]
    bell_t, pipes_t, pstep, legs_t, lstep, total = (sec(td[k]) for k in ("bell", "pipes", "pipeStep", "legs", "legStep", "total"))
    dz = Anim(A + "death", length=total, loop="hold")
    # 1. the main bell breaks: it rocks, shears off its headstock and falls in front of the tower
    dz.track("bell", "rot", [(0, [0, 0, 0]), (0.5, [24, 0, 0], "inout"), (1.0, [-26, 0, 8], "inout"), (bell_t, [30, 0, -6], "inout"),
                             (bell_t + 0.9, [118, 10, -20], "in"), (bell_t + 1.1, [108, 10, -20], "out"), (bell_t + 1.25, [114, 10, -20], "in")])
    dz.track("bell", "pos", [(0, [0, 0, 0]), (bell_t, [0, 0, 0], "linear"), (bell_t + 0.9, [0, -100, -52], "in"),
                             (bell_t + 1.1, [0, -96, -54], "out"), (bell_t + 1.25, [0, -100, -55], "in")])
    dz.track("clapper", "rot", [(0, [0, 0, 0]), (bell_t, [-30, 0, 10], "inout"), (bell_t + 0.9, [-70, 0, 30], "in")])
    dz.sound(0.05, "death_toll").sound(bell_t, "death_bell").particle(bell_t, "fragments", "bell").particle(bell_t + 0.9, "dust", "base")
    # 2. the pipes fall silent, one after another
    order = ["pipe_l4", "pipe_r4", "pipe_l3", "pipe_r3", "pipe_l2", "pipe_r2", "pipe_l1", "pipe_r1", "pipe_c2", "pipe_c3", "pipe_c1"]
    for i, n in enumerate(order):
        t0 = pipes_t + i * pstep
        lean = (18 + (i * 37) % 30) * (1 if i % 2 == 0 else -1)
        dz.track(n, "pos", [(0, [0, 0, 0]), (t0, [0, 3, 0], "out"), (t0 + 0.5, [0, -9 - (i % 3) * 3, 0], "bounce")])
        dz.track(n, "rot", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.5, [10 + (i * 23) % 25, 0, lean * 0.5], "bounce")])
        dz.sound(t0, f"death_pipe{i % 3 + 1}")
        if i % 3 == 0:
            dz.particle(t0, "note", "pipe_top")
    dz.track("wing_l", "rot", [(0, [0, 0, 0]), (pipes_t, [0, 0, 0], "linear"), (legs_t, [10, 0, 26], "inout")])
    dz.track("wing_r", "rot", [(0, [0, 0, 0]), (pipes_t, [0, 0, 0], "linear"), (legs_t, [10, 0, -34], "inout")])
    # 3. the three legs give way in three different directions
    l1, l2, l3 = legs_t, legs_t + lstep, legs_t + 2 * lstep
    dz.track("leg_1_b", "rot", [(0, [0, 0, 0]), (l1, [0, 0, 0], "linear"), (l1 + 0.45, [0, 0, -48], "in")])        # front leg skids out ahead
    dz.track("leg_1_c", "rot", [(0, [0, 0, 0]), (l1, [0, 0, 0], "linear"), (l1 + 0.45, [0, 0, 30], "in")])
    dz.track("leg_2", "rot", [(0, [0, 0, 0]), (l2, [0, 0, 0], "linear"), (l2 + 0.45, [0, -38, 0], "in")])          # left leg swings wide
    dz.track("leg_2_a", "rot", [(0, [0, 0, 0]), (l2, [0, 0, 0], "linear"), (l2 + 0.45, [0, 0, 34], "in")])
    dz.track("leg_3_a", "rot", [(0, [0, 0, 0]), (l3, [0, 0, 0], "linear"), (l3 + 0.45, [0, 0, -52], "in")])         # right leg folds under
    dz.track("leg_3_b", "rot", [(0, [0, 0, 0]), (l3, [0, 0, 0], "linear"), (l3 + 0.45, [0, 0, 58], "in")])
    dz.track("body", "pos", [(0, [0, 0, 0]), (l1, [0, 0, 0], "linear"), (l1 + 0.5, [0, -12, -6], "in"), (l2, [0, -12, -6], "linear"),
                             (l2 + 0.5, [5, -24, -3], "in"), (l3, [5, -24, -3], "linear"), (l3 + 0.5, [2, -41, 2], "in"),
                             (l3 + 0.7, [2, -39, 2], "out"), (l3 + 0.85, [2, -41, 2], "in")])
    dz.track("body", "rot", [(0, [0, 0, 0]), (l1, [0, 0, 0], "linear"), (l1 + 0.5, [16, 0, 0], "in"), (l2, [16, 0, 0], "linear"),
                             (l2 + 0.5, [12, 0, 14], "in"), (l3, [12, 0, 14], "linear"), (l3 + 0.5, [6, 0, 8], "in")])
    for tm in (l1, l2, l3):
        dz.sound(tm + 0.4, "death_leg").particle(tm + 0.45, "dust", "base")
    # 4. one last note, and then nothing moves
    dz.sound(l3 + 0.9, "death_final")
    for n in ("core_glow", "panel_f_glow", "panel_l_glow", "panel_r_glow", "bell_crack_glow"):
        dz.track(n, "scale", [(0, [1, 1, 1]), (l3 + 0.9, [1, 1, 1], "linear"), (total - 0.2, [0.01, 0.01, 0.01], "in")])
    for i, n in enumerate(SMALL):
        dz.track(n, "rot", [(0, [0, 0, 0]), (bell_t, [20, 0, 20], "inout"), (l3 + 0.6, [-30 + i * 20, 0, 24 - i * 16], "bounce")])
    out.append(dz)
    return out


def build_all(T: dict) -> Tuple[List[Anim], List[Controller], ClientEntity]:
    ce = client_entity()
    anims: List[Anim] = build_base()
    for ph in (1, 2):
        anims += downbeat(T["prime_downbeat"], ph)
        anims += counterpoint(T["counterpoint"], ph)
        anims += glass_aria(T["glass_aria"], ph)
        anims += held_note(T["held_note"], ph)
        anims += silent_measure(T["silent_measure"], ph)
        anims += twin_resonance(T["twin_resonance"], ph)
        anims += final_requiem(T["final_requiem"], ph)
    anims += set_pieces(T)
    for a in anims:
        ce.animations[a.name[len(A):]] = a.name

    anim_p = prop("abm:anim")
    is_p2 = prop("abm:phase").eq(2)
    act = Controller("controller.animation.abm.cantor.action", "none")
    entries = []
    names = {1: "downbeat", 2: "counterpoint", 3: "aria", 4: "held", 5: "silent", 6: "twin", 7: "requiem"}
    for idx, nm in names.items():
        for ph in (1, 2):
            state = f"{nm}_p{ph}"
            entries.append((state, anim_p.eq(idx).and_(is_p2 if ph == 2 else prop("abm:phase").eq(1))))
            act.state(state, [state], [("none", anim_p.ne(idx))], blend=0.2)
    for state, idx in (("transition", 8), ("stagger", 9), ("death", 10), ("intro", 11)):
        entries.append((state, anim_p.eq(idx)))
        act.state(state, [state], [] if state == "death" else [("none", anim_p.ne(idx))], blend=0.25)
    act.state("none", [], entries, blend=0.25)

    phase = Controller("controller.animation.abm.cantor.phase", "one")
    phase.state("one", [], [("two", is_p2)], blend=0.25)
    phase.state("two", ["p2_pose", "p2_unstable"], [("one", prop("abm:phase").eq(1))], blend=0.25)

    feet = Controller("controller.animation.abm.cantor.feet", "still")
    feet.state("still", [], [("moving", q("modified_move_speed").gt(0.1).and_(anim_p.eq(0)))])
    feet.state("moving", ["footfalls"], [("still", q("modified_move_speed").lt(0.05).or_(anim_p.ne(0)))])

    ce.animations["ctl_action"] = act.name
    ce.animations["ctl_phase"] = phase.name
    ce.animations["ctl_feet"] = feet.name
    ce.animate = ["idle", "walk", "turn", "ctl_phase", "ctl_action", "ctl_feet"]
    return anims, [act, phase, feet], ce
