"""
Vesperra - rig animation.

Locomotion is procedural and exact: every leg has its own phase in a
metachronal wave, driven by distance actually travelled (walking) and by body
yaw actually turned (turning), so a planted foot stays planted at any speed.
Attacks are keyframed against the beat timings in shared/vesperra.timings.json,
the same numbers the script uses for its hit windows.

Angles for the needle limbs are given as absolute segment directions measured
from straight down towards the front (0 = hanging, 90 = pointing forward,
180 = straight up) and converted to bone offsets by `arm()`.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from kit import molang as M
from kit.anim import Anim, ClientEntity, Controller, combine
from kit.molang import E, cond, cos, mod, prop, q, sin, v

A = "animation.abm.vesperra."
LEGS = [("l", 1, 1), ("l", 2, 1), ("l", 3, 1), ("r", 1, -1), ("r", 2, -1), ("r", 3, -1)]
# contact order: a wave travelling forwards along each side, the sides half a cycle apart
WAVE = {"l3": 0.0, "l2": 0.33, "l1": 0.66, "r3": 0.5, "r2": 0.83, "r1": 0.16}
TRIPOD = {"l1": 0.0, "r2": 0.0, "l3": 0.0, "r1": 0.5, "l2": 0.5, "r3": 0.5}
ARM_BIND = (52.0, 152.0, 16.0)


def sec(ticks: float) -> float:
    return round(ticks / 20.0, 4)


# --------------------------------------------------------------------------- pose helpers

def arm(tag: str, ta: float, tb: float, tc: float, yaw: float = 0.0, roll: float = 0.0) -> Dict[str, dict]:
    """Needle limb pose from absolute segment angles. yaw > 0 swings the limb outwards."""
    side = 1 if tag == "l" else -1
    return {
        f"arm_{tag}_a": {"rot": [ARM_BIND[0] - ta, -yaw * side, -roll * side]},
        f"arm_{tag}_b": {"rot": [(ARM_BIND[1] - ARM_BIND[0]) - (tb - ta), 0, 0]},
        f"arm_{tag}_c": {"rot": [(ARM_BIND[2] - ARM_BIND[1]) - (tc - tb), 0, 0]},
    }


def arms(ta, tb, tc, yaw=0.0, roll=0.0) -> Dict[str, dict]:
    return {**arm("l", ta, tb, tc, yaw, roll), **arm("r", ta, tb, tc, yaw, roll)}


def stance(drop: float = 0.0, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0, fwd: float = 0.0,
           splay: float = 0.0) -> Dict[str, dict]:
    """Lower (drop > 0) or raise the body; the legs flex so the feet stay near the ground.
    Yaw twists the upper body (thorax, dress, train) over planted legs."""
    pose: Dict[str, dict] = {"body": {"pos": [0, -drop, -fwd], "rot": [pitch, 0, roll]}}
    if yaw:
        pose["thorax"] = {"rot": [0, yaw, 0]}
    for tag, n, side in LEGS:
        pose[f"leg_{tag}{n}_a"] = {"rot": [0, 0, -side * (drop * 1.15 + splay)]}
        pose[f"leg_{tag}{n}_b"] = {"rot": [0, 0, side * (drop * 0.35 + splay * 0.6)]}
    return pose


def shells(l: float = 0.0, r: float = 0.0, f: float = 0.0, b: float = 0.0, back_sweep: float = 0.0) -> Dict[str, dict]:
    """Open the four shell sections by the given angles (0 = closed)."""
    return {
        "shell_l": {"rot": [0, -back_sweep, -l]},
        "shell_r": {"rot": [0, back_sweep, r]},
        "shell_f": {"rot": [-f, 0, 0]},
        "shell_b": {"rot": [b, 0, 0]},
    }


def merge(*poses: Dict[str, dict]) -> Dict[str, dict]:
    return combine(*poses)


# The transformed stance of Phase II: the dress stands open like four petals.
P2_POSE = merge(
    shells(l=78, r=78, f=64, b=52, back_sweep=28),
    stance(drop=7, pitch=9),
    arms(74, 128, 58, yaw=8),
    {"neck": {"rot": [10, 0, 0]}, "head": {"rot": [-14, 0, 0]},
     "abdomen_1": {"rot": [-10, 0, 0]}, "abdomen_2": {"rot": [8, 0, 0]}, "abdomen_3": {"rot": [10, 0, 0]},
     "abdomen_4": {"rot": [12, 0, 0]}, "abdomen_tip": {"rot": [24, 0, 0]}},
)


# --------------------------------------------------------------------------- client entity (variables)

def client_entity() -> ClientEntity:
    ce = ClientEntity("abm:vesperra", "geometry.abm.vesperra", "textures/entity/abm/vesperra")
    ce.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha"}
    ce.render_controllers = ["controller.render.abm.vesperra"]
    p2 = ce.var("p2", prop("abm:phase").eq(2))
    ce.var("duty", cond(p2, 0.55, 0.7))
    ce.var("gait", q("modified_distance_moved") * cond(p2, 0.42, 0.526))
    ce.var("turn", (q("body_y_rotation") + 3600) / 60.0)
    ce.var("go", M.clamp(q("modified_move_speed") * 4, 0, 1))
    for tag, n, _ in LEGS:
        key = f"{tag}{n}"
        ce.var(f"w_{key}", mod(v("gait") + cond(p2, TRIPOD[key], WAVE[key]), 1))
        ce.var(f"t_{key}", mod(v("turn") + WAVE[key], 1))
    return ce


def stroke(p: E, duty) -> E:
    """+1 at touchdown, -1 at lift-off (linear through stance), fast return during swing."""
    duty = E.of(duty)
    return cond(p.lt(duty), 1 - p * 2 / duty, (p - duty) * 2 / (1 - duty) - 1)


def lift(p: E, duty) -> E:
    duty = E.of(duty)
    return cond(p.lt(duty), 0, sin((p - duty) / (1 - duty) * 180))


# --------------------------------------------------------------------------- locomotion / idle

def build_base() -> List[Anim]:
    lt = q("life_time")
    p2 = v("p2")
    go = v("go")
    gait = v("gait")

    idle = Anim(A + "idle", loop=True)
    idle.set("body", "pos", [0, sin(lt * 72) * 0.6, 0]).set("body", "rot", [sin(lt * 72 - 20) * 0.8, 0, 0])
    idle.rot("neck", sin(lt * 50 + 40) * 2, 0, 0)
    idle.rot("head", sin(lt * 31) * 1.5, sin(lt * 24) * 5, sin(lt * 36 + 60) * 2.5)
    idle.rot("shell_l", 0, 0, sin(lt * 72 - 50) * 0.9).rot("shell_r", 0, 0, -sin(lt * 72 - 50) * 0.9)
    idle.rot("shell_f", sin(lt * 72 - 65) * 0.8, 0, 0).rot("shell_b", -sin(lt * 72 - 80) * 0.8, 0, 0)
    idle.rot("shell_b_collar", sin(lt * 72 - 110) * 1.2, 0, 0)
    idle.scale("abdomen_1", 1 + sin(lt * 72) * 0.03, 1 - sin(lt * 72) * 0.035, 1)
    for i in (2, 3, 4):
        idle.rot(f"abdomen_{i}", sin(lt * 60 - i * 35) * 1.6, sin(lt * 27 - i * 50) * 1.4, 0)
    idle.rot("abdomen_tip", 0, sin(lt * 45) * 7, 0)
    for tag, side in (("l", 1), ("r", -1)):
        idle.rot(f"arm_{tag}_b", sin(lt * 64 + 30 * side) * 1.8, 0, 0)
        idle.rot(f"arm_{tag}_c", sin(lt * 96 + 70 * side) * 3.2, 0, 0)
    idle.scale("core_glow", 1 + sin(lt * 140) * 0.08)

    walk = Anim(A + "walk", loop=True)
    turn = Anim(A + "turn", loop=True)
    for tag, n, side in LEGS:
        key = f"{tag}{n}"
        pw, pt = v(f"w_{key}"), v(f"t_{key}")
        duty = v("duty")
        walk.rot(f"leg_{key}", 0, stroke(pw, duty) * cond(p2, 17, 13) * side, 0)
        walk.rot(f"leg_{key}_a", 0, 0, lift(pw, duty) * cond(p2, 17, 12) * -side)
        walk.rot(f"leg_{key}_b", 0, 0, lift(pw, duty) * 9 * side)
        turn.rot(f"leg_{key}", 0, stroke(pt, 0.7) * 21, 0)
        turn.rot(f"leg_{key}_a", 0, 0, lift(pt, 0.7) * 11 * -side)
    # ceremonial carriage: the body barely bobs, the dress follows a beat late
    walk.set("body", "pos", [0, sin(gait * 1080) * 0.5 * go, 0])
    walk.set("body", "rot", [go * cond(p2, 5, 1.5), sin(gait * 360) * 1.3 * go, sin(gait * 360 + 90) * 1.6 * go])
    walk.rot("shell_l", 0, 0, sin(gait * 360 + 40) * 2.4 * go)
    walk.rot("shell_r", 0, 0, sin(gait * 360 + 40) * 2.4 * go)
    walk.rot("shell_f", sin(gait * 720 - 60) * 1.8 * go, 0, 0)
    walk.rot("shell_b", sin(gait * 720 - 100) * 1.8 * go, 0, 0)
    walk.rot("shell_b_collar", sin(gait * 720 - 150) * 2.5 * go, 0, 0)
    walk.rot("head", sin(gait * 720 + 30) * 1.2 * go, 0, -sin(gait * 360 + 90) * 1.2 * go)
    for i in (1, 2, 3, 4):
        walk.rot(f"abdomen_{i}", 0, sin(gait * 360 - 45 * i) * 3.2 * go, 0)
    for tag, side in (("l", 1), ("r", -1)):
        walk.rot(f"arm_{tag}_a", sin(gait * 360 + 90 * side) * 2.5 * go, 0, 0)
        walk.rot(f"arm_{tag}_c", sin(gait * 360 + 90 * side - 60) * 5 * go, 0, 0)

    # Phase II carriage: held pose + a restless flutter of the opened shells
    hold = Anim(A + "p2_pose", loop=True)
    for b, ch in P2_POSE.items():
        for c, val in ch.items():
            hold.set(b, c, val)
    flut = Anim(A + "p2_flutter", loop=True)
    flut.rot("shell_l", 0, sin(lt * 230) * 2.5, sin(lt * 410) * 3.5 + sin(lt * 93) * 4)
    flut.rot("shell_r", 0, -sin(lt * 230 + 50) * 2.5, -sin(lt * 410 + 70) * 3.5 - sin(lt * 93 + 40) * 4)
    flut.rot("shell_b", sin(lt * 120) * 4, 0, 0).rot("shell_f", sin(lt * 150 + 60) * 3, 0, 0)
    flut.rot("head", 0, sin(lt * 310) * 2.2, sin(lt * 190) * 4)
    flut.scale("core_glow", 1 + sin(lt * 420) * 0.25)
    flut.scale("abdomen_1", 1 + sin(lt * 200) * 0.05, 1 - sin(lt * 200) * 0.06, 1)

    steps = Anim(A + "footfalls", length=0.96, loop=True)
    for t in (0.0, 0.32, 0.64):
        steps.sound(t, "step")
    return [idle, walk, turn, hold, flut, steps]


# --------------------------------------------------------------------------- attacks

def scythe(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    h1, dec, h2, end = sec(t["hit1"]), sec(t["decide"]), sec(t["hit2"]), sec(t["end"])
    sfx = "p2" if phase == 2 else "p1"
    base = Anim(A + f"scythe_{sfx}", length=end, loop="hold")
    raised = merge(arms(150, 172, 205, yaw=28), stance(drop=-4, pitch=-9, yaw=52),
                   {"neck": {"rot": [-10, 0, 0]}})
    low_r = merge(arms(96, 94, 90, yaw=34), stance(drop=7, pitch=13, yaw=58, roll=4))
    low_l = merge(arms(96, 94, 90, yaw=34), stance(drop=7, pitch=13, yaw=-62, roll=-4))
    rest = merge(arms(70, 120, 70, yaw=10), stance(drop=3, pitch=6, yaw=-30))
    base.poses([(0, {}), (h1 * 0.62, raised, "out"), (h1 - 0.14, raised, "linear"), (h1 - 0.06, low_r, "in"),
                (h1 + 0.08, low_l, "linear"), (dec + 0.25, rest, "out"), (dec + 0.5, {}, "inout"), (end, {})])
    base.sound(0.05, "scythe_wind").sound(h1 - 0.1, "scythe_swing")
    base.particle(h1 - 0.02, "shards", "needle_l").particle(h1 + 0.04, "shards", "needle_r")

    # follow-up A: she has turned (the script rotates her); mirrored sweep, left to right
    fa = Anim(A + f"scythe_turn_{sfx}", length=end, loop="hold")
    raised_m = merge(arms(150, 172, 205, yaw=28), stance(drop=-4, pitch=-9, yaw=-52), {"neck": {"rot": [-10, 0, 0]}})
    low_lm = merge(arms(96, 94, 90, yaw=34), stance(drop=7, pitch=13, yaw=-58))
    low_rm = merge(arms(96, 94, 90, yaw=34), stance(drop=7, pitch=13, yaw=62))
    tail = [(h2 + 0.5, merge(arms(70, 120, 70, yaw=10), stance(drop=3, pitch=6, yaw=30)), "out")]
    fa.poses([(dec + 0.4, {}), (h2 - 0.42, raised_m, "out"), (h2 - 0.14, raised_m, "linear"),
              (h2 - 0.06, low_lm, "in"), (h2 + 0.08, low_rm, "linear")] + tail +
             ([] if phase == 2 else [(end - 0.2, {}, "inout")]))
    fa.sound(h2 - 0.1, "scythe_swing").particle(h2, "shards", "needle_l")

    # follow-up B: both needles crossed, then flung apart - a crescent of shards leaves them
    fb = Anim(A + f"scythe_cast_{sfx}", length=end, loop="hold")
    crossed = merge(arms(110, 150, 120, yaw=-26), stance(drop=5, pitch=8))
    flung = merge(arms(98, 96, 92, yaw=62), stance(drop=-2, pitch=-6, fwd=5))
    fb.poses([(dec + 0.4, {}), (h2 - 0.4, crossed, "out"), (h2 - 0.1, crossed, "linear"), (h2 + 0.05, flung, "snap"),
              (h2 + 0.5, merge(arms(80, 130, 70, yaw=30), stance(drop=2)), "out")] +
             ([] if phase == 2 else [(end - 0.2, {}, "inout")]))
    fb.sound(h2 - 0.08, "scythe_swing").particle(h2, "shards", "needle_l").particle(h2, "shards", "needle_r")
    out = [base, fa, fb]

    if phase == 2:
        # Phase II: a third beat - a two-needle thrust along the marked lane
        h3 = sec(t["hit3"])
        th = Anim(A + "scythe_thrust_p2", length=end, loop="hold")
        cocked = merge(arms(40, 70, 92, yaw=6), stance(drop=8, pitch=4, fwd=-6))
        lunge = merge(arms(92, 92, 91, yaw=2), stance(drop=6, pitch=10, fwd=12))
        th.poses([(h2 + 0.3, {}), (h3 - 0.3, cocked, "out"), (h3 - 0.08, cocked, "linear"), (h3 + 0.04, lunge, "snap"),
                  (h3 + 0.6, lunge, "linear"), (end - 0.15, {}, "inout")])
        th.sound(h3 - 0.04, "thrust").particle(h3 + 0.04, "shards", "needle_l")
        out.append(th)
    return out


def procession(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    plant, first, gap, end = sec(t["plant"]), sec(t["first"]), sec(t["gap"]), sec(t["end"])
    a = Anim(A + f"procession_p{phase}", length=end, loop="hold")
    lane = [v("lane1"), v("lane2"), v("lane3")]
    high = merge(arm("r", 128, 160, 150, yaw=6), stance(drop=-3, pitch=-6))
    planted = merge(arm("r", 62, 82, 6, yaw=4), stance(drop=9, pitch=14), {"neck": {"rot": [-12, 0, 0]}})
    a.poses([(0, {}), (plant * 0.6, high, "out"), (plant, planted, "in"), (end - 0.7, planted, "linear"),
             (end - 0.35, merge(arm("r", 110, 150, 60), stance(drop=2)), "out"), (end, {}, "inout")],
            bones=["arm_r_a", "arm_r_b", "arm_r_c", "body", "thorax", "neck"] + [f"leg_{tg}{n}_{s}" for tg, n, _ in LEGS for s in "ab"])
    # the free needle points down each lane in the order they will fire
    ready = arm("l", 118, 140, 100)
    stab = arm("l", 84, 86, 80)
    hits = [first + i * gap for i in range(3)]
    keys_a, keys_b, keys_c = [(0.0, [0, 0, 0])], [(0.0, [0, 0, 0])], [(0.0, [0, 0, 0])]
    for i, h in enumerate(hits):
        yaw = lane[i] * (30 if phase == 1 else 26)
        for (tt, pose) in ((h - 0.28, ready), (h - 0.03, stab), (h + 0.12, stab)):
            r = pose["arm_l_a"]["rot"]
            a.key("arm_l_a", "rot", tt, [r[0], yaw, r[2]])
            a.key("arm_l_b", "rot", tt, pose["arm_l_b"]["rot"])
            a.key("arm_l_c", "rot", tt, pose["arm_l_c"]["rot"])
        a.sound(h - 0.04, "needle_stab")
    for b in ("arm_l_a", "arm_l_b", "arm_l_c"):
        a.key(b, "rot", 0.0, [0, 0, 0]).key(b, "rot", plant, [0, 0, 0]).key(b, "rot", end, [0, 0, 0])
    a.sound(plant - 0.05, "needle_plant").particle(plant, "dust", "needle_r")
    if phase == 2:
        cross = sec(t["cross"])
        for (tt, pose) in ((cross - 0.35, arm("l", 150, 170, 190, yaw=30)), (cross, arm("l", 70, 60, 20, yaw=10)),
                           (cross + 0.3, arm("l", 70, 60, 20, yaw=10))):
            for b in ("arm_l_a", "arm_l_b", "arm_l_c"):
                a.key(b, "rot", tt, pose[b]["rot"])
        a.sound(cross - 0.05, "needle_plant").particle(cross, "dust", "needle_l")
    return [a]


def molting(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    launch, end = sec(t["launch"]), sec(t["end"])
    a = Anim(A + f"molting_p{phase}", length=end, loop="hold")
    k = 1.0 if phase == 1 else 0.55          # in Phase II the shells are already open; smaller swing
    tight = merge(shells(l=-6 * k, r=-6 * k, f=-5 * k, b=-5 * k), stance(drop=9, pitch=6), arms(40, 150, 30, yaw=-8),
                  {"abdomen_1": {"scale": [1.14, 0.82, 0.9]}, "abdomen_2": {"scale": [1.1, 0.86, 0.92]},
                   "head": {"rot": [16, 0, 0]}})
    burst = merge(shells(l=46 * k, r=46 * k, f=38 * k, b=40 * k, back_sweep=8), stance(drop=-6, pitch=-8),
                  arms(120, 150, 170, yaw=50),
                  {"abdomen_1": {"scale": [0.9, 1.18, 1.08]}, "abdomen_2": {"scale": [0.92, 1.12, 1.06]},
                   "head": {"rot": [-22, 0, 0]}, "shell_b_collar": {"rot": [-24, 0, 0]}})
    settle = merge(shells(l=8 * k, r=8 * k, f=6 * k, b=6 * k), stance(drop=2), arms(70, 140, 40, yaw=10))
    frames = [(0, {}), (launch * 0.7, tight, "out"), (launch - 0.08, tight, "linear"), (launch + 0.06, burst, "snap"),
              (launch + 0.55, settle, "bounce")]
    a.sound(0.05, "molt_wind").sound(launch - 0.03, "molt_burst")
    for loc in ("shell_l", "shell_r", "core"):
        a.particle(launch, "molt", loc)
    if phase == 2:
        second = sec(t["second"])
        frames += [(second - 0.3, tight, "in"), (second - 0.06, tight, "linear"), (second + 0.06, burst, "snap"),
                   (second + 0.55, settle, "bounce")]
        a.sound(second - 0.03, "molt_burst")
        for loc in ("shell_l", "shell_r", "tail"):
            a.particle(second, "molt", loc)
    frames += [(end, {}, "inout")]
    a.poses(frames)
    return [a]


def cocoon(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    spawn, con, end = sec(t["spawn"]), sec(t["constrict"]), sec(t["end"])
    a = Anim(A + f"cocoon_p{phase}", length=end, loop="hold")
    curl = {"abdomen_1": {"rot": [-34, 0, 0]}, "abdomen_2": {"rot": [-30, 0, 0]}, "abdomen_3": {"rot": [-28, 0, 0]},
            "abdomen_4": {"rot": [-26, 0, 0]}, "abdomen_tip": {"rot": [-30, 0, 0]}}
    spit = merge(curl, stance(drop=-5, pitch=-10), arms(100, 140, 110, yaw=18),
                 {"abdomen_1": {"scale": [1.12, 0.86, 1]}})
    weave_a = merge(curl, stance(drop=2, pitch=4), arm("l", 104, 118, 96, yaw=22), arm("r", 80, 132, 70, yaw=6))
    weave_b = merge(curl, stance(drop=2, pitch=4), arm("l", 80, 132, 70, yaw=6), arm("r", 104, 118, 96, yaw=22))
    pull = merge(stance(drop=6, pitch=-6), arms(60, 30, 100, yaw=44), {"neck": {"rot": [-14, 0, 0]}})
    frames = [(0, {}), (spawn, spit, "snap")]
    tt, flip = spawn + 0.3, False
    while tt < con - 0.3:
        frames.append((tt, weave_a if flip else weave_b, "inout"))
        flip = not flip
        tt += 0.34
    frames += [(con - 0.14, weave_a, "linear"), (con + 0.04, pull, "snap"), (con + 0.5, pull, "linear"), (end, {}, "inout")]
    a.poses(frames)
    a.sound(spawn - 0.05, "cocoon_spit").sound(spawn + 0.3, "cocoon_weave").sound(con, "cocoon_snap")
    a.particle(spawn, "drip", "tail")
    return [a]


def false_submission(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    cue, thrust, dash, end = sec(t["cue"]), sec(t["thrust"]), sec(t["dash"]), sec(t["end"])
    a = Anim(A + f"feint_p{phase}", length=end, loop="hold")
    # The collapse looks like a stagger EXCEPT for the needles: cocked back along the flanks, never limp.
    sag = merge(stance(drop=15, pitch=18, roll=5), arms(-24, 46, 92, yaw=4),
                {"neck": {"rot": [22, 0, 6]}, "head": {"rot": [20, 0, 10]}, "shell_l": {"rot": [0, 0, 5]},
                 "shell_r": {"rot": [0, 0, -3]}, "shell_b_collar": {"rot": [10, 0, 0]}})
    coiled = merge(stance(drop=17, pitch=12, fwd=-7), arms(-30, 30, 91, yaw=2),
                   {"neck": {"rot": [6, 0, 0]}, "head": {"rot": [-18, 0, 0]}})
    spear = merge(stance(drop=10, pitch=12, fwd=13), arms(91, 91, 90, yaw=1), {"head": {"rot": [-14, 0, 0]}})
    stuck = merge(stance(drop=14, pitch=20, fwd=9), arms(70, 62, 44, yaw=3), {"neck": {"rot": [14, 0, 0]}})
    tug = merge(stance(drop=11, pitch=15, fwd=6), arms(74, 66, 46, yaw=3), {"neck": {"rot": [8, 0, 0]}})
    frames = [(0, {}), (0.7, sag, "bounce"), (cue - 0.05, sag, "linear"), (cue + 0.12, coiled, "out"),
              (thrust - 0.06, coiled, "linear"), (thrust + dash * 0.5, spear, "snap"), (thrust + dash, stuck, "out")]
    a.sound(0.1, "feint_fall").sound(cue, "feint_cue").sound(thrust - 0.04, "thrust")
    a.particle(cue, "glint", "crown").particle(cue + 0.2, "glint", "core")
    a.particle(thrust + dash, "dust", "needle_l").particle(thrust + dash, "dust", "needle_r")
    if phase == 1:
        tt = thrust + dash + 0.35
        while tt < end - 0.9:
            frames += [(tt, tug, "out"), (tt + 0.22, stuck, "in")]
            tt += 0.5
    else:
        cue2, thrust2 = sec(t["cue2"]), sec(t["thrust2"])
        frames += [(cue2, coiled, "out"), (thrust2 - 0.06, coiled, "linear"), (thrust2 + dash * 0.5, spear, "snap"),
                   (thrust2 + dash, stuck, "out")]
        a.sound(cue2, "feint_cue").sound(thrust2 - 0.04, "thrust").particle(cue2, "glint", "crown")
        tt = thrust2 + dash + 0.35
        while tt < end - 0.9:
            frames += [(tt, tug, "out"), (tt + 0.22, stuck, "in")]
            tt += 0.5
    frames += [(end - 0.5, merge(stance(drop=4), arms(70, 130, 50)), "out"), (end, {}, "inout")]
    a.poses(frames)
    return [a]


def heirs(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    det, end = sec(t["detach"]), sec(t["end"])
    a = Anim(A + f"heirs_p{phase}", length=end, loop="hold")
    rear = merge(stance(drop=-7, pitch=-15), arms(130, 150, 100, yaw=58), {"neck": {"rot": [-12, 0, 0]},
                 "shell_l": {"rot": [0, 0, -10]}, "shell_r": {"rot": [0, 0, 10]}})
    shed = merge(stance(drop=5, pitch=6), arms(80, 130, 60, yaw=30), {"shell_l": {"rot": [0, 0, -26]},
                 "shell_r": {"rot": [0, 0, 26]}, "shell_b": {"rot": [14, 0, 0]}})
    a.poses([(0, {}), (det * 0.7, rear, "out"), (det - 0.05, rear, "linear"), (det + 0.08, shed, "snap"),
             (det + 0.5, merge(stance(drop=1)), "bounce"), (end, {}, "inout")])
    a.sound(0.1, "heirs_call").sound(det, "heirs_detach")
    a.particle(det, "molt", "shell_l").particle(det, "molt", "shell_r")
    return [a]


def coronation(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    first, interval, warn, count, end = sec(t["first"]), sec(t["interval"]), sec(t["warn"]), t["count"], sec(t["end"])
    a = Anim(A + f"coronation_p{phase}", length=end, loop="hold")
    crowned = merge(stance(drop=-7, pitch=-12), arms(140, 165, 190, yaw=46),
                    {"neck": {"rot": [-16, 0, 0], "pos": [0, 3, 0]}, "head": {"rot": [-10, 0, 0]},
                     "crown": {"scale": [1.12, 1.25, 1.12]}, "shell_b_collar": {"rot": [-18, 0, 0]},
                     "shell_l": {"rot": [0, 0, -9]}, "shell_r": {"rot": [0, 0, 9]}, "shell_f": {"rot": [-8, 0, 0]}})
    body_bones = ["body", "thorax", "neck", "head", "crown", "shell_b_collar", "shell_l", "shell_r", "shell_f"] + \
                 [f"leg_{tg}{n}_{s}" for tg, n, _ in LEGS for s in "ab"]
    last = first + interval * (count - 1) + warn
    a.poses([(0, {}), (first * 0.8, crowned, "out"), (last, crowned, "linear"), (end - 0.2, {}, "inout"), (end, {})],
            bones=body_bones)
    a.sound(0.05, "crown_raise")
    # each mark: one needle stabs down, alternating - seven beats the player can count
    up_l, up_r = arm("l", 140, 165, 190, yaw=46), arm("r", 140, 165, 190, yaw=46)
    for tag, up in (("l", up_l), ("r", up_r)):
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            a.key(b, "rot", 0.0, [0, 0, 0]).key(b, "rot", first * 0.8, up[b]["rot"])
    for i in range(count):
        tm = first + i * interval
        tag = "l" if i % 2 == 0 else "r"
        up = up_l if tag == "l" else up_r
        down = arm(tag, 66, 72, 14, yaw=14 + (i % 3) * 8)
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            a.key(b, "rot", tm - 0.16, up[b]["rot"]).key(b, "rot", tm, down[b]["rot"])
            a.key(b, "rot", tm + 0.14, down[b]["rot"]).key(b, "rot", tm + 0.4, up[b]["rot"])
        a.sound(tm, "fracture_mark").particle(tm, "dust", f"needle_{tag}")
        a.particle(tm + warn, "glint", "crown")
    for tag, up in (("l", up_l), ("r", up_r)):
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            a.key(b, "rot", last, up[b]["rot"]).key(b, "rot", end - 0.2, [0, 0, 0]).key(b, "rot", end, [0, 0, 0])
    return [a]


# --------------------------------------------------------------------------- set pieces

def set_pieces(T: dict) -> List[Anim]:
    out: List[Anim] = []

    # ---- intro: she is found folded like a chrysalis and unfolds into court posture
    ti = T["intro"]
    rise, crown, total = sec(ti["rise"]), sec(ti["crown"]), sec(ti["total"])
    folded = merge(stance(drop=34, pitch=24, splay=-6), arms(20, 150, 10, yaw=-10),
                   {"neck": {"rot": [40, 0, 0]}, "head": {"rot": [30, 0, 0]}, "crown": {"scale": [0.9, 0.7, 0.9]},
                    "shell_l": {"rot": [0, 0, 7]}, "shell_r": {"rot": [0, 0, -7]}, "shell_b_collar": {"rot": [26, 0, 0]},
                    "abdomen_1": {"rot": [-30, 0, 0]}, "abdomen_2": {"rot": [-30, 0, 0]}, "abdomen_3": {"rot": [-30, 0, 0]}})
    half = merge(stance(drop=10, pitch=8), arms(40, 150, 12), {"neck": {"rot": [20, 0, 0]}, "head": {"rot": [12, 0, 0]}})
    regal = merge(stance(drop=-6, pitch=-8), arms(120, 160, 150, yaw=40),
                  {"neck": {"rot": [-14, 0, 0], "pos": [0, 2, 0]}, "crown": {"scale": [1.1, 1.2, 1.1]},
                   "shell_b_collar": {"rot": [-14, 0, 0]}})
    intro = Anim(A + "intro", length=total, loop="hold")
    intro.poses([(0, folded), (rise * 0.5, folded, "linear"), (crown, half, "inout"), (crown + 0.9, regal, "out"),
                 (total - 0.5, regal, "linear"), (total, {}, "inout")])
    intro.sound(rise * 0.5, "intro_rise").sound(crown + 0.3, "crown_raise")
    intro.particle(crown + 0.9, "glint", "crown").particle(rise, "dust", "core")
    out.append(intro)

    # ---- stagger: a genuine loss of composure. Needles hang LIMP and splayed (compare the feint).
    ts = sec(T["stagger"]["total"])
    reel = merge(stance(drop=13, pitch=13, roll=-9), arm("l", 34, 22, 8, yaw=30), arm("r", 26, 14, 2, yaw=22),
                 {"neck": {"rot": [10, 0, -14]}, "head": {"rot": [8, 0, -22]}, "shell_l": {"rot": [0, 0, -12]},
                  "shell_r": {"rot": [0, 0, -8]}, "shell_b_collar": {"rot": [16, 0, 0]}})
    stag = Anim(A + "stagger", length=ts, loop="hold")
    stag.poses([(0, {}), (0.22, reel, "snap"), (ts - 0.55, reel, "linear"), (ts, {}, "inout")])
    stag.sound(0.02, "stagger").particle(0.05, "shards", "core")
    out.append(stag)

    # ---- phase transition: the porcelain splits along four seams and stands open
    tt = T["transition"]
    crack, split, unfold, total = sec(tt["crack"]), sec(tt["split"]), sec(tt["unfold"]), sec(tt["total"])
    clutch = merge(stance(drop=10, pitch=16), arms(60, 150, 40, yaw=-18), {"neck": {"rot": [26, 0, 0]},
                   "head": {"rot": [18, 0, 0]}})
    bulge = merge(stance(drop=4, pitch=-14, splay=5), arms(130, 150, 60, yaw=30),
                  {"neck": {"rot": [-26, 0, 0]}, "head": {"rot": [-20, 0, 8]},
                   "shell_l": {"scale": [1.08, 1.04, 1.08]}, "shell_r": {"scale": [1.08, 1.04, 1.08]},
                   "shell_f": {"scale": [1.06, 1.04, 1.1]}, "shell_b": {"scale": [1.06, 1.04, 1.1]},
                   "abdomen_1": {"scale": [1.15, 1.15, 1.0]}})
    jolt = merge(bulge, shells(l=12, r=12, f=9, b=9))
    screech = merge(P2_POSE, {"neck": {"rot": [-8, 0, 0]}, "head": {"rot": [-34, 0, 0]}},
                    arms(120, 150, 150, yaw=62), shells(l=14, r=14, f=10, b=12))
    tr = Anim(A + "transition", length=total, loop="hold")
    tr.poses([(0, {}), (crack * 0.5, clutch, "out"), (crack, clutch, "linear"), (split - 0.5, bulge, "inout"),
              (split - 0.08, bulge, "linear"), (split + 0.05, jolt, "snap"), (unfold, P2_POSE, "inout"),
              (unfold + 0.45, screech, "out"), (total - 0.3, screech, "linear"), (total, P2_POSE, "inout")])
    tr.sound(0.05, "transition_crack").sound(split - 0.05, "transition_split").sound(unfold + 0.25, "transition_cry")
    for loc in ("shell_l", "shell_r", "core"):
        tr.particle(crack, "shards", loc).particle(split, "molt", loc)
    tr.particle(unfold + 0.3, "drip", "core").particle(unfold + 0.45, "glint", "crown")
    out.append(tr)

    # ---- death (authored on top of the Phase II stance, which stays active underneath)
    td = T["death"]
    crown_t, molt, fail, collapse, total = (sec(td[k]) for k in ("crown", "molt", "fail", "collapse", "total"))
    dz = Anim(A + "death", length=total, loop="hold")
    recoil = merge(stance(drop=-3, pitch=-16), arms(130, 160, 120, yaw=40), {"neck": {"rot": [-24, 0, 0]}})
    # 1. the crown fractures first
    dz.track("crown", "rot", [(0, [0, 0, 0]), (crown_t - 0.3, [0, 0, 6], "linear"), (crown_t, [10, 0, 34], "snap"),
                              (crown_t + 0.5, [40, 20, 96], "in")])
    dz.track("crown", "pos", [(0, [0, 0, 0]), (crown_t, [0, -1, 0], "linear"), (crown_t + 0.5, [-9, -46, 4], "in"),
                              (crown_t + 0.7, [-10, -50, 4], "bounce")])
    dz.track("shield_c", "pos", [(0, [0, 0, 0]), (crown_t + 0.1, [0, 0, 0], "linear"), (crown_t + 0.7, [4, -52, -6], "in")])
    dz.track("shield_c", "rot", [(0, [0, 0, 0]), (crown_t + 0.1, [0, 0, 0], "linear"), (crown_t + 0.7, [70, 0, -40], "in")])
    # 2. one last molt is attempted: the petals try to close and renew ...
    closing = shells(l=-52, r=-52, f=-44, b=-36, back_sweep=-20)
    half_shut = shells(l=-30, r=-22, f=-20, b=-16, back_sweep=-10)
    strain = merge(closing, stance(drop=-4, pitch=-6), arms(110, 150, 60, yaw=20),
                   {"abdomen_1": {"scale": [1.16, 0.8, 0.92]}, "abdomen_2": {"scale": [1.12, 0.84, 0.94]}})
    # 3. ... and cannot finish
    slack = merge(half_shut, stance(drop=9, pitch=10, roll=4), arms(60, 80, 30, yaw=14),
                  {"neck": {"rot": [18, 0, 6]}, "head": {"rot": [14, 0, 10]}})
    # 4/5. the shell falls away in stages, the legs curl, the body settles
    fallen = merge(stance(drop=30, pitch=20, roll=7, splay=-10), arms(30, 40, 10, yaw=20),
                   {"neck": {"rot": [34, 0, 8]}, "head": {"rot": [26, 0, 16]},
                    "abdomen_1": {"rot": [12, 0, 0]}, "abdomen_tip": {"rot": [-20, 0, 0]}})
    for tag, n, side in LEGS:
        fallen[f"leg_{tag}{n}_b"] = {"rot": [0, 0, side * 46]}
        fallen[f"leg_{tag}{n}_c"] = {"rot": [0, 0, side * 30]}
    core = [b for b in fallen if not b.startswith("shell")] + ["abdomen_2"]
    dz.poses([(0, {}), (0.4, recoil, "snap"), (crown_t + 0.6, recoil, "linear"), (molt, strain, "inout"),
              (fail - 0.4, strain, "linear"), (fail, slack, "bounce"), (collapse, slack, "linear"),
              (total - 0.5, fallen, "in"), (total, fallen, "bounce")], bones=core)
    drop = {"shell_l": ([-46, -40, 6], [0, -20, -60]), "shell_r": ([46, -40, 6], [0, 20, 60]),
            "shell_f": ([0, -44, -22], [-70, 0, 0]), "shell_b": ([0, -58, 14], [-31, 0, 0])}
    for i, (b, (dp, dr)) in enumerate(drop.items()):
        t0 = fail + 0.25 + i * 0.4
        c, h = closing[b]["rot"], half_shut[b]["rot"]
        dz.track(b, "rot", [(0, [0, 0, 0]), (crown_t + 0.6, [0, 0, 0], "linear"), (molt, c, "inout"),
                            (fail - 0.4, c, "linear"), (fail, h, "bounce"), (t0, h, "linear"),
                            (t0 + 0.5, [h[k] + dr[k] for k in range(3)], "in")])
        dz.track(b, "pos", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.5, dp, "in"),
                            (t0 + 0.62, [dp[0], dp[1] + 2, dp[2]], "out"), (t0 + 0.75, dp, "in")])
        dz.sound(t0 + 0.45, "armor_break")
    dz.sound(0.05, "death_cry").sound(crown_t, "armor_break").sound(molt - 0.4, "molt_wind")
    dz.sound(fail, "death_fail").sound(total - 0.5, "death_fall")
    dz.particle(crown_t, "shards", "crown").particle(fail, "drip", "core").particle(total - 0.4, "dust", "core")
    for loc in ("shell_l", "shell_r"):
        dz.particle(fail + 0.7, "molt", loc)
    dz.scale("core_glow", 0)
    dz.scale("eyes_glow", 0)
    for b in ("core_glow", "eyes_glow"):
        del dz.static[(b, "scale")]
        dz.track(b, "scale", [(0, [1, 1, 1]), (fail, [1, 1, 1], "linear"), (collapse, [0.01, 0.01, 0.01], "in")])
    out.append(dz)
    return out


def build_all(T: dict) -> Tuple[List[Anim], List[Controller], ClientEntity]:
    ce = client_entity()
    # lane order of the Needle Procession, decoded from the synced variant (0..5)
    var = prop("abm:variant")
    ce.var("lane1", cond(var.lt(2), -1, cond(var.lt(4), 0, 1)))
    ce.var("lane2", cond(var.eq(0).or_(var.eq(5)), 0, cond(var.eq(2).or_(var.eq(4)), -1, 1)))
    ce.var("lane3", cond(var.eq(0).or_(var.eq(2)), 1, cond(var.eq(1).or_(var.eq(4)), 0, -1)))

    anims: List[Anim] = build_base()
    for ph in (1, 2):
        anims += scythe(T["ivory_scythe"], ph)
        anims += procession(T["needle_procession"], ph)
        anims += molting(T["royal_molting"], ph)
        anims += cocoon(T["cocoon_edict"], ph)
        anims += false_submission(T["false_submission"], ph)
        anims += heirs(T["the_heirs"], ph)
        anims += coronation(T["coronation"], ph)
    anims += set_pieces(T)

    for a in anims:
        ce.animations[a.name[len(A):]] = a.name
    anim_p = prop("abm:anim")
    is_p2 = prop("abm:phase").eq(2)

    act = Controller("controller.animation.abm.vesperra.action", "none")
    entries = []
    names = {1: "scythe", 2: "procession", 3: "molting", 4: "cocoon", 5: "feint", 6: "heirs", 7: "coronation"}
    for idx, nm in names.items():
        for ph in (1, 2):
            state = f"{nm}_p{ph}"
            want = anim_p.eq(idx).and_(is_p2 if ph == 2 else prop("abm:phase").eq(1))
            entries.append((state, want))
            if nm == "scythe":
                vr = prop("abm:variant")
                layers = [state, (f"scythe_turn_p{ph}", vr.eq(1)), (f"scythe_cast_p{ph}", vr.eq(2))]
                if ph == 2:
                    layers.append("scythe_thrust_p2")
            else:
                layers = [state]
            act.state(state, layers, [("none", anim_p.ne(idx))], blend=0.18)
    for state, idx in (("transition", 8), ("stagger", 9), ("death", 10), ("intro", 11)):
        entries.append((state, anim_p.eq(idx)))
        act.state(state, [state], [] if state == "death" else [("none", anim_p.ne(idx))], blend=0.2)
    act.state("none", [], entries, blend=0.22)

    phase = Controller("controller.animation.abm.vesperra.phase", "one")
    phase.state("one", [], [("two", is_p2)], blend=0.25)
    phase.state("two", ["p2_pose", "p2_flutter"], [("one", prop("abm:phase").eq(1))], blend=0.25)

    feet = Controller("controller.animation.abm.vesperra.feet", "still")
    moving = q("modified_move_speed").gt(0.12).and_(anim_p.eq(0))
    feet.state("still", [], [("moving", moving)])
    feet.state("moving", ["footfalls"], [("still", q("modified_move_speed").lt(0.06).or_(anim_p.ne(0)))])

    ce.animations["ctl_action"] = act.name
    ce.animations["ctl_phase"] = phase.name
    ce.animations["ctl_feet"] = feet.name
    ce.animate = ["idle", "walk", "turn", "ctl_phase", "ctl_action", "ctl_feet"]
    return anims, [act, phase, feet], ce
