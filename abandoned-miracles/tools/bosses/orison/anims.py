"""
Orison - rig animation.

Orison moves like a mechanism that is slightly out of step with the present:
the pendulum (its head) keeps time, the torso answers a beat late, the coffin
and the plumb weight later still, and the ribbons last. Gestures snap between
held poses instead of flowing. The two stilt legs are driven by distance
actually travelled and yaw actually turned, so planted feet stay planted and
the stop-start "tick-tock" pace set by the script reads as deliberate.

Attack keyframes use the beat timings in shared/orison.timings.json - the same
numbers the script uses for its hazards.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from kit import molang as M
from kit.anim import Anim, ClientEntity, Controller, combine
from kit.molang import E, cond, floor, mod, prop, q, sin, v

A = "animation.abm.orison."
LEG_TAGS = ("l", "r")
ARM_TAGS = ("ul", "ur", "ll", "lr")
RIBBONS = {1: "abcde", 2: "abcde", 3: "abcd"}


def sec(ticks: float) -> float:
    return round(ticks / 20.0, 4)


# --------------------------------------------------------------------------- pose helpers

def arm(tag: str, a=(0.0, 0.0, 0.0), b: float = 0.0, c: float = 0.0, twist: float = 0.0) -> Dict[str, dict]:
    """Offsets on one arm. Shoulder x < 0 swings forward; z lifts sideways (left arms: negative = up/out,
    right arms: positive = up/out). b and c bend the elbow and wrist (negative = forward)."""
    return {f"arm_{tag}_a": {"rot": [a[0], a[1], a[2]]}, f"arm_{tag}_b": {"rot": [b, 0, 0]},
            f"arm_{tag}_c": {"rot": [c, twist, 0]}}


def stance(drop: float = 0.0, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0, fwd: float = 0.0,
           lean: float = 0.0) -> Dict[str, dict]:
    """Lower (drop > 0) or raise the body on the stilts; pitch/yaw/lean bend the torso over planted legs."""
    pose: Dict[str, dict] = {"body": {"pos": [0, -drop, -fwd], "rot": [0, 0, roll]}}
    if pitch or yaw or lean:
        pose["torso"] = {"rot": [pitch, yaw, lean]}
    if drop:
        for t in LEG_TAGS:
            pose[f"leg_{t}_a"] = {"rot": [-1.3 * drop, 0, 0]}
            pose[f"leg_{t}_b"] = {"rot": [2.3 * drop, 0, 0]}
            pose[f"leg_{t}_c"] = {"rot": [-2.0 * drop, 0, 0]}
            pose[f"leg_{t}_d"] = {"rot": [1.0 * drop, 0, 0]}
    return pose


def merge(*poses: Dict[str, dict]) -> Dict[str, dict]:
    return combine(*poses)


# What the four hands do when they are simply lowered to hang (cancels most of the bind pose).
LIMP = merge(arm("ul", (0, 0, 104), 10, 18), arm("ur", (14, 0, -66), 60, 30), arm("ll", (40, -18, 0), 60, -26),
             arm("lr", (4, 0, -30), 84, -50))
# A crown of hands: all four raised.
RAISED = merge(arm("ul", (-10, 0, -22), -10, -12), arm("ur", (-20, 0, 60), 40, 20), arm("ll", (-40, -20, -70), 30, -20),
               arm("lr", (-30, 0, 70), 50, -40))

# Phase II carriage: the case hangs open, the body hunches and the hands spread low and wide.
P2_POSE = merge(
    stance(drop=6, pitch=11, lean=-4),
    arm("ul", (-18, 0, 34), -14, -10), arm("ur", (-12, 0, 22), 20, -18), arm("ll", (10, -30, -46), 20, -30),
    arm("lr", (-16, 0, 26), 30, -22),
    {"sand_top": {"scale": [0.05, 0.02, 0.05]}, "sand_glow": {"scale": [0.01, 0.01, 0.01]},
     "sand_bottom": {"scale": [1.0, 0.55, 1.0]}, "coffin": {"rot": [0, 0, 9]},
     "ribbon_1_a": {"rot": [10, 0, -18]}, "ribbon_2_a": {"rot": [10, 0, 18]}, "ribbon_3_a": {"rot": [22, 0, 0]}},
)


# --------------------------------------------------------------------------- client entity

def client_entity() -> ClientEntity:
    ce = ClientEntity("abm:orison", "geometry.abm.orison", "textures/entity/abm/orison")
    ce.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "glass": "entity_alphablend"}
    ce.render_controllers = ["controller.render.abm.orison"]
    p2 = ce.var("p2", prop("abm:phase").eq(2))
    ce.var("gait", M.BLOCKS_MOVED * cond(p2, 0.3, 0.327))
    ce.var("turn", (v("yaw") + 3600) / 60.0)        # v.yaw: see kit.anim.add_facing
    ce.var("go", M.clamp(q("modified_move_speed") * 4, 0, 1))
    ce.var("w_l", mod(v("gait"), 1))
    ce.var("w_r", mod(v("gait") + 0.5, 1))
    ce.var("t_l", mod(v("turn"), 1))
    ce.var("t_r", mod(v("turn") + 0.5, 1))
    return ce


def stroke(p: E, duty: float) -> E:
    """+1 at touchdown, -1 at lift-off, fast return while the foot is in the air."""
    return cond(p.lt(duty), 1 - p * 2 / duty, (p - duty) * 2 / (1 - duty) - 1)


def lift(p: E, duty: float) -> E:
    return cond(p.lt(duty), 0, sin((p - duty) / (1 - duty) * 180))


# --------------------------------------------------------------------------- always-on layers

def build_base() -> List[Anim]:
    lt = q("life_time")
    p2 = v("p2")
    go = v("go")
    gait = v("gait")
    beat = lt * 150                       # the pendulum's own time: one swing every 2.4 s

    swing = Anim(A + "pendulum_swing", loop=True)
    swing.rot("pendulum", 0, 0, cond(p2, sin(lt * 250) * 30 + sin(lt * 97) * 9, sin(beat) * 26))
    swing.rot("escapement", 0, 0, floor(lt * 1.25) * 30 + M.clamp(mod(lt * 1.25, 1) * 5, 0, 1) * 30)
    swing.scale("pendulum_glow", 1, 1 + sin(lt * 300) * 0.12, 1)

    idle = Anim(A + "idle", loop=True)
    # everything below answers the pendulum late: torso, then coffin, then plumb weight, then ribbons
    idle.set("torso", "rot", [sin(lt * 75) * 1.0, M.clamp(sin(lt * 24) * 6, -1, 1) * 7, sin(beat - 70) * 1.6])
    idle.set("body", "pos", [sin(lt * 37) * 0.8, sin(beat * 2 - 40) * 0.35, 0])
    idle.rot("coffin", sin(lt * 110) * 3, 0, sin(beat - 150) * 7)
    idle.rot("plumb", sin(lt * 61) * 4, 0, sin(beat - 210) * 13)
    idle.scale("coffin_glow", 1 + sin(lt * 220) * 0.2, 1, 1)
    idle.scale("sand_top", 1, 1 - mod(lt * 0.02, 1) * 0.7, 1)
    idle.scale("sand_bottom", 1, 0.5 + mod(lt * 0.02, 1) * 1.1, 1)
    # four hands on four different clocks
    idle.rot("arm_ul_a", 0, 0, floor(mod(lt * 0.5, 6)) * 2.5 + sin(lt * 40) * 1.5)        # ticks round like a minute hand
    idle.rot("arm_ul_c", sin(lt * 47) * 3, 0, 0)
    idle.rot("arm_ur_a", sin(lt * 57 + 40) * 4, 0, 0)
    idle.rot("arm_ur_c", M.clamp(sin(lt * 31) * 5, -1, 1) * 10, 0, 0)                      # the hour hand wags, pauses, wags
    idle.rot("arm_ll_c", sin(lt * 83) * 4, lt * 140, 0)                                    # the key keeps winding
    idle.rot("arm_ll_b", sin(lt * 83 + 90) * 3, 0, 0)
    idle.rot("arm_lr_a", sin(lt * 33) * 3.5, 0, 0)
    idle.rot("arm_lr_c", sin(lt * 33 - 60) * 6, 0, 0)                                      # the gavel is weighed
    for i, segs in RIBBONS.items():
        for k, ch in enumerate(segs):
            name = f"ribbon_{i}_{ch}"
            idle.rot(name, sin(lt * 90 - k * 55 + i * 70) * (4 + k), 0, sin(lt * 60 - k * 40 + i * 30) * (3 + k))
        idle.pos(f"ribbon_{i}_a", sin(lt * 33 + i * 120) * 1.2, sin(lt * 45 + i * 90) * 2.2, 0)

    walk = Anim(A + "walk", loop=True)
    turn = Anim(A + "turn", loop=True)
    for t, side in (("l", 1), ("r", -1)):
        pw, pt = v(f"w_{t}"), v(f"t_{t}")
        walk.rot(f"leg_{t}_a", stroke(pw, 0.62) * -15 + lift(pw, 0.62) * -10, 0, 0)
        walk.rot(f"leg_{t}_b", lift(pw, 0.62) * 34, 0, 0)
        walk.rot(f"leg_{t}_c", lift(pw, 0.62) * -30, 0, 0)
        walk.rot(f"leg_{t}_d", stroke(pw, 0.62) * 15 + lift(pw, 0.62) * 14, 0, 0)
        turn.rot(f"leg_{t}", 0, stroke(pt, 0.62) * 18.6, 0)
        turn.rot(f"leg_{t}_b", lift(pt, 0.62) * 22, 0, 0)
        turn.rot(f"leg_{t}_c", lift(pt, 0.62) * -20, 0, 0)
    # the body arrives after the legs: it leans into each step late and the head whips later still
    walk.set("body", "pos", [0, M.mabs(sin(gait * 360)) * -1.4 * go, 0])
    walk.set("torso", "rot", [go * 5 + sin(gait * 720 - 80) * 2.6 * go, 0, sin(gait * 360 - 60) * 2.2 * go])
    walk.rot("pendulum", sin(gait * 720 - 150) * 7 * go, 0, 0)
    walk.rot("plumb", sin(gait * 720 - 220) * 16 * go, 0, 0)
    walk.rot("coffin", sin(gait * 720 - 180) * 6 * go, 0, 0)
    for i in RIBBONS:
        walk.rot(f"ribbon_{i}_a", go * 20 + sin(gait * 360 - i * 60) * 6 * go, 0, 0)
        walk.rot(f"ribbon_{i}_b", go * 12, 0, 0)

    hold = Anim(A + "p2_pose", loop=True)
    for b, chans in P2_POSE.items():
        for c, val in chans.items():
            hold.set(b, c, val)
    flut = Anim(A + "p2_flutter", loop=True)
    gate = M.clamp(sin(lt * 53) * 4, 0, 1)                       # twitches come in bursts, then stillness
    flut.rot("torso", 0, sin(lt * 610) * 1.4 * gate, sin(lt * 900) * 0.9 * gate)
    flut.rot("coffin", 0, 0, sin(lt * 420) * 5 * gate)
    flut.rot("arm_ul_c", sin(lt * 700) * 5 * gate, 0, 0)
    flut.rot("arm_lr_c", sin(lt * 520 + 40) * 6 * gate, 0, 0)
    flut.rot("hourglass", 0, 0, sin(lt * 800) * 1.5 * gate)
    # the dial of unlived hours: the face creeps one way, its hands run the other, far too fast
    flut.rot("halo", 0, 0, lt * 7)
    flut.rot("halo_hand_glow", 0, 0, lt * -64)
    flut.rot("halo_hour_glow", 0, 0, lt * -11 + sin(lt * 240) * 6 * gate)
    flut.scale("halo_glow", 1 + sin(lt * 190) * 0.035)

    steps = Anim(A + "footfalls", length=1.6, loop=True)

    steps.pos("root", 0, 0, 0)        # a sound-only animation still needs one bone channel (see Anim.json)
    steps.sound(0.0, "step").sound(0.8, "step")
    return [swing, idle, walk, turn, hold, flut, steps]


# --------------------------------------------------------------------------- attacks

GAVEL_UP = arm("lr", (-70, 0, 20), 20, -30)
GAVEL_DOWN = arm("lr", (-8, 0, 6), 30, 34)


def footstep_echo(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    mark, first, gap, count, end = sec(t["mark"]), sec(t["first"]), sec(t["gap"]), t["count"], sec(t["end"])
    a = Anim(A + f"echo_p{phase}", length=end, loop="hold")
    read = merge(stance(drop=8, pitch=26, yaw=-10), arm("ur", (-30, 0, -40), 20, 30), arm("ul", (-10, 0, 40), -10, -10))
    found = merge(stance(drop=3, pitch=10), arm("ur", (-50, 0, -20), 10, -50), arm("ul", (-20, 0, 10), -20, -20))
    last = first + gap * (count - 1)
    body = ["body", "torso"] + [f"leg_{s}_{k}" for s in LEG_TAGS for k in "abcd"] + \
           [f"arm_{g}_{k}" for g in ("ur", "ul") for k in "abc"]
    a.poses([(0, {}), (mark * 0.75, read, "out"), (mark - 0.04, read, "linear"), (mark + 0.1, found, "snap"),
             (last + 0.3, found, "linear"), (end, {}, "inout")], bones=body)
    # the gavel counts the echoes out, one tap each
    up, down = GAVEL_UP, GAVEL_DOWN
    for b in ("arm_lr_a", "arm_lr_b", "arm_lr_c"):
        a.key(b, "rot", 0.0, [0, 0, 0]).key(b, "rot", first - 0.3, up[b]["rot"])
    for i in range(count):
        tm = first + i * gap
        for b in ("arm_lr_a", "arm_lr_b", "arm_lr_c"):
            a.key(b, "rot", tm - 0.1, up[b]["rot"]).key(b, "rot", tm, down[b]["rot"]).key(b, "rot", tm + 0.08, down[b]["rot"])
        a.sound(tm, "tap")
    for b in ("arm_lr_a", "arm_lr_b", "arm_lr_c"):
        a.key(b, "rot", last + 0.4, up[b]["rot"]).key(b, "rot", end, [0, 0, 0])
    a.sound(0.05, "echo_read").sound(mark, "echo_mark").particle(mark, "glint", "hour")
    return [a]


def pendulum_verdict(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    swing, sweep, end = sec(t["swing"]), sec(t["sweep"]), sec(t["end"])
    out: List[Anim] = []
    for name, sgn in (("a", 1), ("b", -1)):
        a = Anim(A + f"verdict_p{phase}_{name}", length=end, loop="hold")
        # the head is lowered like a felling axe and drawn back to the side it will start from
        drawn = merge(stance(drop=6, pitch=34, yaw=-72 * sgn), {"pendulum": {"rot": [78, 0, 0], "scale": [1.3, 2.3, 1.3]}},
                      arm("ul", (-10, 0, 60), 0, 0), arm("lr", (-20, 0, 20), 0, 0))
        thrown = merge(stance(drop=8, pitch=38, yaw=72 * sgn), {"pendulum": {"rot": [84, 0, 0], "scale": [1.3, 2.3, 1.3]}},
                       arm("ul", (-10, 0, 60), 0, 0), arm("lr", (-20, 0, 20), 0, 0))
        frames = [(0, {}), (swing * 0.6, drawn, "out"), (swing, drawn, "linear"), (swing + sweep, thrown, "linear")]
        a.sound(0.05, "verdict_wind").sound(swing - 0.05, "verdict_swing")
        if phase == 2:
            s2 = sec(t["swing2"])
            frames += [(s2, thrown, "linear"), (s2 + sweep, drawn, "linear"), (s2 + sweep + 0.4, drawn, "out")]
            a.sound(s2 - 0.05, "verdict_swing")
        else:
            frames += [(swing + sweep + 0.35, thrown, "out")]
        frames += [(end, {}, "inout")]
        a.poses(frames)
        out.append(a)
    return out


def deferred_wound(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    first, gap, count, fuse, end = sec(t["first"]), sec(t["gap"]), t["count"], sec(t["fuse"]), sec(t["end"])
    a = Anim(A + f"wound_p{phase}", length=end, loop="hold")
    last_mark = first + gap * (count - 1)
    set_pose = merge(stance(drop=4, pitch=14), arm("ll", (-30, -10, -20), 30, 0))
    body = ["body", "torso"] + [f"leg_{s}_{k}" for s in LEG_TAGS for k in "abcd"] + ["arm_ll_a", "arm_ll_b"]
    a.poses([(0, {}), (first * 0.7, set_pose, "out"), (last_mark + fuse, set_pose, "linear"), (end, {}, "inout")], bones=body)
    a.key("arm_ll_c", "rot", 0.0, [0, 0, 0]).key("arm_ll_c", "rot", last_mark + fuse, [0, 1440, 0]).key("arm_ll_c", "rot", end, [0, 1440, 0])
    high = arm("ul", (-30, 0, 30), -10, -10)
    stab = arm("ul", (-64, 0, 96), -20, -30)
    for b in ("arm_ul_a", "arm_ul_b", "arm_ul_c"):
        a.key(b, "rot", 0.0, [0, 0, 0]).key(b, "rot", first - 0.3, high[b]["rot"])
    for i in range(count):
        tm = first + i * gap
        for b in ("arm_ul_a", "arm_ul_b", "arm_ul_c"):
            a.key(b, "rot", tm - 0.12, high[b]["rot"]).key(b, "rot", tm, stab[b]["rot"]).key(b, "rot", tm + 0.1, stab[b]["rot"])
        a.sound(tm, "wound_mark").particle(tm, "glint", "minute")
    for b in ("arm_ul_a", "arm_ul_b", "arm_ul_c"):
        a.key(b, "rot", last_mark + 0.4, high[b]["rot"]).key(b, "rot", end, [0, 0, 0])
    return [a]


def hourglass_drain(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    cast, end = sec(t["cast"]), sec(t["end"])
    a = Anim(A + f"drain_p{phase}", length=end, loop="hold")
    cup = merge(stance(drop=7, pitch=16), arm("ll", (-16, 14, 0), -14, -10), arm("lr", (-40, 30, -20), -20, 30),
                {"hourglass": {"scale": [1.22, 1.22, 1.22]}})
    pour = merge(stance(drop=-5, pitch=-14), arm("ll", (-50, -40, -70), 40, 0), arm("lr", (-50, 0, 80), 60, 0),
                 arm("ul", (-10, 0, -20), 0, 0), arm("ur", (-20, 0, 50), 30, 0),
                 {"hourglass": {"scale": [0.9, 0.9, 0.9], "rot": [0, 0, 180]}})
    a.poses([(0, {}), (cast * 0.7, cup, "out"), (cast - 0.05, cup, "linear"), (cast + 0.12, pour, "snap"),
             (cast + 0.7, pour, "linear"), (end, {}, "inout")])
    a.sound(0.05, "drain_wind").sound(cast, "drain_cast").particle(cast, "sand", "sand")
    return [a]


def tomorrows_witness(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    lock, strike, end = sec(t["lock"]), sec(t["strike"]), sec(t["end"])
    a = Anim(A + f"witness_p{phase}", length=end, loop="hold")
    # it stops. Only the hour hand moves, rising to point at where you are going to be.
    seek = merge(stance(pitch=-4), arm("ur", (-40, 0, -30), 30, 20))
    fixed = merge(stance(pitch=-8, yaw=4), arm("ur", (-58, 0, -52), 64, 34), GAVEL_UP)
    slam = merge(stance(drop=6, pitch=18), arm("ur", (-58, 0, -52), 64, 34), GAVEL_DOWN)
    a.poses([(0, {}), (lock - 0.1, seek, "out"), (lock + 0.05, fixed, "snap"), (strike - 0.12, fixed, "linear"),
             (strike, slam, "snap"), (strike + 0.5, slam, "linear"), (end, {}, "inout")])
    a.sound(0.02, "witness_hush").sound(lock, "witness_lock").sound(strike - 0.02, "gavel")
    a.particle(lock, "glint", "hour")
    return [a]


def secondhand_exchange(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    a = Anim(A + f"exchange_p{phase}", length=sec(t["end"]), loop="hold")
    point = merge(stance(pitch=-6, yaw=-12), arm("ul", (-70, 0, 96), 10, 20))
    thin = [0.05, 1.12, 0.05]
    frames = [(0, {})]
    scale_keys = [(0, [1, 1, 1])]
    beats = [(t["mark"], t["swap"], t["strike"])]
    if phase == 2:
        beats.append((t["mark2"], t["swap2"], t["strike2"]))
    for mk, sw, st in beats:
        mk, sw, st = sec(mk), sec(sw), sec(st)
        frames += [(mk + 0.25, point, "snap"), (sw - 0.35, point, "linear"),
                   (sw + 0.3, merge(stance(drop=-3, pitch=-10), GAVEL_UP), "out"), (st - 0.1, merge(stance(drop=-3, pitch=-10), GAVEL_UP), "linear"),
                   (st, merge(stance(drop=7, pitch=20), GAVEL_DOWN), "snap"), (st + 0.4, merge(stance(drop=7, pitch=20), GAVEL_DOWN), "linear")]
        # the displacement itself: the whole body narrows to a line, and widens again somewhere else
        scale_keys += [(sw - 0.3, [1, 1, 1], "linear"), (sw - 0.02, thin, "in"), (sw + 0.06, thin, "linear"), (sw + 0.32, [1, 1, 1], "back")]
        a.sound(mk, "exchange_mark").sound(sw - 0.25, "exchange_swap").sound(st - 0.02, "gavel")
        a.particle(sw - 0.05, "wisp", "chest").particle(sw + 0.1, "wisp", "chest")
    frames += [(sec(t["end"]), {}, "inout")]
    scale_keys += [(sec(t["end"]), [1, 1, 1], "linear")]
    a.poses(frames)
    a.track("root", "scale", scale_keys)
    return [a]


def hour_never(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    preview, show, step, exe, gap, end = (sec(t[k]) for k in ("preview", "show", "step", "exec", "gap", "end"))
    a = Anim(A + f"hour_p{phase}", length=end, loop="hold")
    court = merge(stance(drop=-6, pitch=-10), RAISED)
    last = exe + 2 * gap
    body = ["body", "torso", "pendulum"] + [f"leg_{s}_{k}" for s in LEG_TAGS for k in "abcd"]
    a.poses([(0, {}), (preview * 0.8, merge(court, {"pendulum": {"scale": [1.15, 1.25, 1.15]}}), "out"),
             (last + 0.3, merge(court, {"pendulum": {"scale": [1.15, 1.25, 1.15]}}), "linear"), (end, {}, "inout")], bones=body)
    # preview: one hand per pattern points it out - I, II, III
    order = ("ur", "ul", "lr")
    point = {"ur": arm("ur", (-70, 0, -40), 60, 30), "ul": arm("ul", (-70, 0, 100), 10, 20), "lr": arm("lr", (-90, 0, 0), 60, -30)}
    for tag in ARM_TAGS:
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            a.key(b, "rot", 0.0, [0, 0, 0]).key(b, "rot", preview * 0.8, RAISED[b]["rot"])
    for i, tag in enumerate(order):
        tm = preview + i * step
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            a.key(b, "rot", tm - 0.05, RAISED[b]["rot"]).key(b, "rot", tm + 0.12, point[tag][b]["rot"])
            a.key(b, "rot", tm + show - 0.15, point[tag][b]["rot"]).key(b, "rot", tm + show + 0.1, RAISED[b]["rot"])
        a.sound(tm, "hour_chime")
    # execution: the gavel falls three times, in the order that was shown
    for i in range(3):
        tm = exe + i * gap
        for b in ("arm_lr_a", "arm_lr_b", "arm_lr_c"):
            a.key(b, "rot", tm - 0.5, GAVEL_UP[b]["rot"]).key(b, "rot", tm - 0.1, GAVEL_UP[b]["rot"])
            a.key(b, "rot", tm, GAVEL_DOWN[b]["rot"]).key(b, "rot", tm + 0.2, GAVEL_DOWN[b]["rot"])
        a.sound(tm - 0.02, "gavel")
    for tag in ARM_TAGS:
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            if tag != "lr":
                a.key(b, "rot", last + 0.3, RAISED[b]["rot"])
            a.key(b, "rot", end, [0, 0, 0])
    a.sound(0.05, "hour_call")
    return [a]


# --------------------------------------------------------------------------- set pieces

def set_pieces(T: dict) -> List[Anim]:
    out: List[Anim] = []
    folded = merge(stance(drop=34, pitch=44), LIMP, {"pendulum": {"rot": [0, 0, 88]}, "coffin": {"rot": [20, 0, 0]}})

    # ---- intro: found folded shut like a stopped clock; it is wound, and stands
    ti = T["intro"]
    wake, swing, total = sec(ti["wake"]), sec(ti["swing"]), sec(ti["total"])
    intro = Anim(A + "intro", length=total, loop="hold")
    half = merge(stance(drop=16, pitch=20), {"pendulum": {"rot": [0, 0, 88]}})
    body = [b for b in folded if not b.startswith("arm_")]
    intro.poses([(0, folded), (wake, folded, "linear"), (swing, half, "inout"),
                 (swing + 0.5, merge(stance(drop=4, pitch=6), {"pendulum": {"rot": [0, 0, -14]}}), "out"), (total, {}, "inout")], bones=body)
    for i, tag in enumerate(ARM_TAGS):                 # the hands unfold one at a time
        t0 = wake + i * 0.42
        for b in (f"arm_{tag}_a", f"arm_{tag}_b", f"arm_{tag}_c"):
            intro.track(b, "rot", [(0, LIMP[b]["rot"]), (t0, LIMP[b]["rot"], "linear"), (t0 + 0.45, [0, 0, 0], "back"), (total, [0, 0, 0], "linear")])
        intro.sound(t0, "tick")
    intro.sound(0.2, "intro_wind").sound(swing, "intro_strike").particle(swing, "glint", "bob")
    out.append(intro)

    # ---- stagger: the mechanism jams; the head falls sideways and hangs
    ts = sec(T["stagger"]["total"])
    jam = merge(stance(drop=12, pitch=24, lean=-12), LIMP, {"pendulum": {"rot": [10, 0, 96]}, "coffin": {"rot": [0, 0, 20]},
                                                           "plumb": {"rot": [0, 0, 30]}})
    stag = Anim(A + "stagger", length=ts, loop="hold")
    stag.poses([(0, {}), (0.2, jam, "snap"), (ts - 0.6, jam, "linear"), (ts, {}, "inout")])
    stag.sound(0.02, "stagger").particle(0.06, "spark", "top")
    out.append(stag)

    # ---- phase transition: the hourglass bursts; what was being held back comes out
    tt = T["transition"]
    crack, shatter, emerge, total = (sec(tt[k]) for k in ("crack", "shatter", "emerge", "total"))
    clutch = merge(stance(drop=6, pitch=-16), arm("ll", (-16, 14, 0), -14, -10), arm("lr", (-40, 30, -20), -20, 30),
                   arm("ur", (10, 20, -50), 20, 40), {"hourglass": {"scale": [1.08, 1.08, 1.08]}})
    strain = merge(clutch, {"hourglass": {"scale": [1.3, 1.3, 1.3], "rot": [0, 0, 6]}, "torso": {"rot": [-22, 0, 5]}})
    burst = merge(stance(drop=-4, pitch=-30), RAISED, {"hourglass": {"scale": [0.92, 0.92, 0.92]},
                                                      "sand_top": {"scale": [0.05, 0.02, 0.05]}, "sand_glow": {"scale": [0.01, 0.01, 0.01]},
                                                      "pendulum": {"rot": [-20, 0, 0]}})
    spent = merge(stance(drop=18, pitch=38), LIMP, {"sand_top": {"scale": [0.05, 0.02, 0.05]}, "sand_glow": {"scale": [0.01, 0.01, 0.01]},
                                                   "sand_bottom": {"scale": [1, 0.55, 1]}, "pendulum": {"rot": [24, 0, 30]}})
    tr = Anim(A + "transition", length=total, loop="hold")
    tr.poses([(0, {}), (crack * 0.6, clutch, "out"), (crack, clutch, "linear"), (shatter - 0.3, strain, "inout"),
              (shatter - 0.04, strain, "linear"), (shatter + 0.08, burst, "snap"), (shatter + 0.7, burst, "linear"),
              (emerge, spent, "bounce"), (emerge + 0.5, spent, "linear"), (total, P2_POSE, "inout")])
    # the dial unfolds out of the burst (it is invisible until the glass breaks)
    tr.track("halo", "scale", [(0, [0.02, 0.02, 0.02]), (shatter, [0.02, 0.02, 0.02], "linear"),
                               (shatter + 0.12, [0.45, 0.45, 0.45], "out"), (emerge, [1.12, 1.12, 1.12], "out"),
                               (emerge + 0.4, [1, 1, 1], "inout"), (total, [1, 1, 1], "linear")])
    tr.track("halo", "rot", [(0, [0, 0, -150]), (shatter, [0, 0, -150], "linear"), (emerge + 0.4, [0, 0, 0], "out"),
                             (total, [0, 0, 0], "linear")])
    tr.sound(0.05, "transition_crack").sound(shatter - 0.03, "transition_shatter").sound(emerge, "shadow_emerge")
    tr.particle(crack, "shard", "sand").particle(shatter, "shard", "sand").particle(shatter, "sand", "sand")
    tr.particle(shatter + 0.5, "sand", "sand").particle(emerge, "wisp", "chest")
    out.append(tr)

    # ---- death (plays over the Phase II carriage)
    td = T["death"]
    stop, repeat, ribbons, empty, total = (sec(td[k]) for k in ("stop", "repeat", "ribbons", "empty", "total"))
    dz = Anim(A + "death", length=total, loop="hold")
    # 1. the pendulum stops (its swing layer is faded out by the controller; this is the last settle)
    dz.track("pendulum", "rot", [(0, [0, 0, 14]), (stop * 0.5, [0, 0, -6], "inout"), (stop, [0, 0, 0], "inout"),
                                 (empty, [0, 0, 0], "linear"), (total, [30, 0, 70], "in")])
    # 2. the body goes through its last motion again - a verdict raised and delivered - but nothing answers it
    raise_ = merge(stance(pitch=-8, yaw=4), arm("ur", (-58, 0, -52), 64, 34), GAVEL_UP)
    fall = merge(stance(drop=6, pitch=18), arm("ur", (-58, 0, -52), 64, 34), GAVEL_DOWN)
    half_raise = merge(stance(pitch=-4), arm("ur", (-30, 0, -30), 30, 20), arm("lr", (-36, 0, 12), 10, -14))
    # 5. ... and then there is nothing holding it up
    down = merge(stance(drop=40, pitch=52, lean=14), LIMP, {"coffin": {"rot": [30, 0, 24]}, "plumb": {"rot": [40, 0, 0]}})
    core = [b for b in down if not b.startswith("ribbon")] + ["arm_ur_a", "arm_ur_b", "arm_ur_c"]
    dz.poses([(0, {}), (stop, {}, "linear"), (repeat - 0.5, raise_, "out"), (repeat - 0.1, raise_, "linear"), (repeat, fall, "snap"),
              (repeat + 0.6, fall, "linear"), (ribbons - 0.5, half_raise, "inout"), (empty, half_raise, "linear"),
              (total - 0.6, down, "in"), (total, down, "bounce")], bones=[b for b in dict.fromkeys(core) if b != "pendulum"])
    # 3. the ribbons fall, one after another
    drop = {1: ([6, -104, 4], [60, 0, 40]), 2: ([-5, -90, 6], [70, 0, -50]), 3: ([0, -80, 2], [84, 0, 10])}
    for i, (dp, dr) in drop.items():
        t0 = ribbons + (i - 1) * 0.35
        dz.track(f"ribbon_{i}_a", "pos", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.55, dp, "in"), (t0 + 0.7, [dp[0], dp[1] + 3, dp[2]], "out"), (t0 + 0.85, dp, "in")])
        dz.track(f"ribbon_{i}_a", "rot", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.55, dr, "in")])
        for k, ch in enumerate(RIBBONS[i][1:]):
            dz.track(f"ribbon_{i}_{ch}", "rot", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.6, [8 + k * 4, 0, 0], "in")])
        dz.sound(t0 + 0.5, "ribbon_fall")
    # 4. the hourglass empties completely
    dz.track("sand_bottom", "scale", [(0, [1, 1, 1]), (ribbons, [1, 1, 1], "linear"), (empty, [0.6, 0.04, 0.6], "in"), (total, [0.02, 0.02, 0.02], "linear")])
    dz.track("coffin_glow", "scale", [(0, [1, 1, 1]), (empty, [1, 1, 1], "linear"), (empty + 0.5, [0.01, 0.01, 0.01], "in")])
    # the dial of unlived hours closes last: the hours it showed are let go
    dz.track("halo", "scale", [(0, [1, 1, 1]), (ribbons, [1, 1, 1], "linear"), (empty, [1.06, 1.06, 1.06], "inout"),
                               (empty + 0.7, [0.02, 0.02, 0.02], "in"), (total, [0.02, 0.02, 0.02], "linear")])
    dz.track("pendulum_glow", "scale", [(0, [1, 1, 1]), (stop, [1, 1, 1], "linear"), (stop + 0.8, [0.01, 0.01, 0.01], "in")])
    dz.sound(0.05, "death_stop").sound(repeat - 0.02, "gavel").sound(ribbons - 0.3, "death_empty").sound(total - 0.55, "death_fall")
    dz.particle(ribbons, "sand", "sand").particle(empty - 0.3, "sand", "sand").particle(total - 0.4, "spark", "top")
    out.append(dz)
    return out


def build_all(T: dict) -> Tuple[List[Anim], List[Controller], ClientEntity]:
    ce = client_entity()
    anims: List[Anim] = build_base()
    for ph in (1, 2):
        anims += footstep_echo(T["footstep_echo"], ph)
        anims += pendulum_verdict(T["pendulum_verdict"], ph)
        anims += deferred_wound(T["deferred_wound"], ph)
        anims += hourglass_drain(T["hourglass_drain"], ph)
        anims += tomorrows_witness(T["tomorrows_witness"], ph)
        anims += secondhand_exchange(T["secondhand_exchange"], ph)
        anims += hour_never(T["hour_never"], ph)
    anims += set_pieces(T)
    for a in anims:
        ce.animations[a.name[len(A):]] = a.name
    anim_p = prop("abm:anim")
    is_p2 = prop("abm:phase").eq(2)
    is_p1 = prop("abm:phase").eq(1)
    var = prop("abm:variant")

    act = Controller("controller.animation.abm.orison.action", "none")
    entries = []
    names = {1: "echo", 2: "verdict", 3: "wound", 4: "drain", 5: "witness", 6: "exchange", 7: "hour"}
    for idx, nm in names.items():
        for ph in (1, 2):
            state = f"{nm}_p{ph}"
            entries.append((state, anim_p.eq(idx).and_(is_p2 if ph == 2 else is_p1)))
            if nm == "verdict":
                layers = [(f"verdict_p{ph}_a", var.eq(0)), (f"verdict_p{ph}_b", var.eq(1))]
            else:
                layers = [state]
            act.state(state, layers, [("none", anim_p.ne(idx))], blend=0.14)
    for state, idx in (("transition", 8), ("stagger", 9), ("death", 10), ("intro", 11)):
        entries.append((state, anim_p.eq(idx)))
        act.state(state, [state], [] if state == "death" else [("none", anim_p.ne(idx))], blend=0.16)
    act.state("none", [], entries, blend=0.2)

    phase = Controller("controller.animation.abm.orison.phase", "one")
    phase.state("one", [], [("two", is_p2)], blend=0.25)
    phase.state("two", ["p2_pose", "p2_flutter"], [("one", is_p1)], blend=0.25)

    # the pendulum keeps time unless Orison is deliberately still, jammed, waking or dead
    still = anim_p.eq(5).or_(anim_p.eq(9)).or_(anim_p.eq(10)).or_(anim_p.eq(11))
    pend = Controller("controller.animation.abm.orison.pendulum", "swing")
    pend.state("swing", ["pendulum_swing"], [("still", still)], blend=0.5)
    pend.state("still", [], [("swing", anim_p.eq(0))], blend=0.7)

    feet = Controller("controller.animation.abm.orison.feet", "still")
    feet.state("still", [], [("moving", q("modified_move_speed").gt(0.12).and_(anim_p.eq(0)))])
    feet.state("moving", ["footfalls"], [("still", q("modified_move_speed").lt(0.06).or_(anim_p.ne(0)))])

    ce.animations.update({"ctl_action": act.name, "ctl_phase": phase.name, "ctl_pendulum": pend.name, "ctl_feet": feet.name})
    ce.animate = ["idle", "walk", "turn", "ctl_pendulum", "ctl_phase", "ctl_action", "ctl_feet"]
    return anims, [act, phase, pend, feet], ce
