"""
Animations for the five final bosses (Bedrock animation JSON, format 1.8.0).

Every boss gets: idle, move, atk_a, atk_b, atk_c, atk_d, channel, ultimate, stagger, death, spawn
(+ dormant / burrow for the World Parasite). Idle loops use `variable.t`, a clock that runs faster in
later phases. State animations ease in with E and attacks use keyframes so that strikes land on the
same tick as the script's damage.
"""

T = "variable.t"
E = "math.min(query.anim_time * 3.0, 1.0)"
A = "query.anim_time"


def s(k, ph=0, amp=1.0, clock=T):
    ph_s = f" + {ph}" if ph else ""
    return f"math.sin({clock} * {k}{ph_s}) * {amp}"


def c(k, ph=0, amp=1.0, clock=T):
    ph_s = f" + {ph}" if ph else ""
    return f"math.cos({clock} * {k}{ph_s}) * {amp}"


def loop(bones):
    return {"loop": True, "bones": bones}


def once(bones, length):
    return {"loop": "hold_on_last_frame", "animation_length": length, "bones": bones}


def kf(frames):
    """{time: [x,y,z]} keyframes with smooth interpolation."""
    return {f"{t:.2f}": {"post": list(v), "lerp_mode": "catmullrom"} for t, v in frames}


def eased(x=0, y=0, z=0):
    return [f"{x} * {E}" if x else 0, f"{y} * {E}" if y else 0, f"{z} * {E}" if z else 0]


# --------------------------------------------------------------------------- Void Emperor

def emperor():
    a = {}
    idle = {
        "throne": {"position": [0, s(90, amp=0.6), 0], "rotation": [s(40, amp=1.2), 0, c(35, amp=1.0)]},
        "hand_r": {"position": [0, s(70, amp=1.5), 0], "rotation": [s(50, amp=5), s(30, amp=8), 0]},
        "hand_l": {"position": [0, s(70, 120, 1.5), 0], "rotation": [s(50, 120, 5), s(30, 90, -8), 0]},
        "mask": {"position": [0, s(80, 40, 0.8), 0], "rotation": [s(45, amp=4), s(25, amp=10), 0]},
        "mask_halo": {"rotation": [0, 0, f"{T} * 25"]},
        "rift": {"rotation": [0, 0, f"-{T} * 12"]},
        "crown_orbs": {"position": [0, s(100, amp=0.5), 0]},
    }
    for side in ("r", "l"):
        for k in range(4):
            idle[f"finger_{side}{k}_a"] = {"rotation": [s(60, k * 30, 6), 0, 0]}
            idle[f"finger_{side}{k}_b"] = {"rotation": [s(60, k * 30 + 40, 8), 0, 0]}
    for i in range(4):
        idle[f"cape{i}"] = {"rotation": [s(70, -i * 40, 3 + i * 2), 0, s(50, -i * 30, 1 + i)]}
    a["idle"] = loop(idle)
    gait = f"math.sin({A} * 420)"
    a["move"] = loop({
        "leg_fr": {"rotation": [f"{gait} * 22", 0, 0]}, "leg_bl": {"rotation": [f"{gait} * 22", 0, 0]},
        "leg_fl": {"rotation": [f"-{gait} * 22", 0, 0]}, "leg_br": {"rotation": [f"-{gait} * 22", 0, 0]},
        "throne": {"position": [0, f"math.abs({gait}) * 1.2", 0], "rotation": [4, 0, f"{gait} * 2"]},
    })
    a["atk_a"] = once({
        "hand_r": {"position": kf([(0, (0, 0, 0)), (0.6, (8, 16, -10)), (1.1, (8, 18, -16)), (1.22, (8, -8, -30)), (1.7, (8, -6, -30))]),
                   "rotation": kf([(0, (0, 0, 0)), (0.6, (-40, 0, 0)), (1.1, (-50, 0, 0)), (1.22, (60, 0, 0)), (1.7, (55, 0, 0))])},
        "mask": {"rotation": kf([(0, (0, 0, 0)), (1.1, (-10, 0, 0)), (1.25, (8, 0, 0))])},
    }, 1.7)
    curl = {f"finger_l{k}_a": {"rotation": kf([(0, (0, 0, 0)), (0.6, (-20, 0, 0)), (0.75, (50, 0, 0)), (2.8, (50, 0, 0))])} for k in range(4)}
    curl.update({f"finger_l{k}_b": {"rotation": kf([(0, (0, 0, 0)), (0.75, (70, 0, 0)), (2.8, (70, 0, 0))])} for k in range(4)})
    a["atk_b"] = once(dict(curl, hand_l={"position": kf([(0, (0, 0, 0)), (0.7, (-14, 10, -30)), (2.4, (-12, 14, -24)), (2.6, (-4, 8, -10)), (2.8, (0, 0, 0))])}), 2.8)
    a["atk_c"] = loop({"mask": {"position": eased(0, 6, -4)}})
    gallop = f"math.sin({A} * 900)"
    a["atk_d"] = loop({
        "leg_fr": {"rotation": [f"{gallop} * 35", 0, 0]}, "leg_bl": {"rotation": [f"{gallop} * 35", 0, 0]},
        "leg_fl": {"rotation": [f"-{gallop} * 35", 0, 0]}, "leg_br": {"rotation": [f"-{gallop} * 35", 0, 0]},
        "throne": {"rotation": [f"12 * {E}", 0, 0], "position": [0, f"math.abs({gallop}) * 2", 0]},
        "hand_r": {"position": eased(-4, 4, 10)}, "hand_l": {"position": eased(4, 4, 10)},
    })
    a["channel"] = loop({
        "hand_r": {"position": eased(-6, 14, 0), "rotation": eased(-30, 0, -20)},
        "hand_l": {"position": eased(6, 14, 0), "rotation": eased(-30, 0, 20)},
        "mask": {"position": eased(0, 6, -4)}, "mask_halo": {"scale": f"1 + 0.4 * {E}"},
        "rift": {"rotation": [0, 0, f"-{A} * 60"]},
    })
    a["ultimate"] = loop({
        "throne": {"rotation": eased(-8, 0, 0)},
        "rift": {"scale": f"1 + 0.6 * {E}", "rotation": [0, 0, f"-{A} * 90"]},
        "mask": {"position": eased(0, 14, -6), "scale": f"1 + 0.3 * {E}", "rotation": [f"-15 * {E}", f"{s(400, amp=4, clock=A)}", 0]},
        "mask_halo": {"scale": f"1 + 0.8 * {E}", "rotation": [0, 0, f"{A} * 200"]},
        "hand_r": {"position": eased(-16, 10, 0), "rotation": eased(0, 0, -40)},
        "hand_l": {"position": eased(16, 10, 0), "rotation": eased(0, 0, 40)},
        "crown_orbs": {"scale": f"1 + 0.6 * {E}", "position": eased(0, 6, 0)},
        **{f"cape{i}": {"rotation": eased(-15 - i * 5, 0, 0)} for i in range(4)},
    })
    a["stagger"] = loop({
        "throne": {"rotation": [f"10 * {E}", 0, f"{s(300, amp=3, clock=A)}"]},
        "hand_r": {"position": eased(0, -10, 0)}, "hand_l": {"position": eased(0, -10, 0)},
        "mask": {"position": eased(0, -6, 0), "rotation": eased(25, 0, 0)},
    })
    a["death"] = once({
        "throne": {"rotation": [f"{A} * 8", 0, f"{A} * 6"], "position": [0, f"-{A} * 3", 0]},
        "hand_r": {"position": [f"-{A} * 3", f"-{A} * 12", 0], "rotation": [f"{A} * 40", 0, 0]},
        "hand_l": {"position": [f"{A} * 3", f"-{A} * 12", 0], "rotation": [f"{A} * 40", 0, 0]},
        "mask": {"rotation": [f"{A} * 60", 0, f"{A} * 20"], "position": [0, f"-{A} * 4", f"-{A} * 3"]},
        "rift": {"scale": f"math.max(0, 1 - {A} / 4)"},
        "crown_orbs": {"position": [0, f"{A} * 6", 0]},
        **{leg: {"rotation": [0, 0, f"math.min(30, {A} * 10) * {sgn}"]} for leg, sgn in (("leg_fr", -1), ("leg_br", -1), ("leg_fl", 1), ("leg_bl", 1))},
    }, 5.0)
    rise = f"(1 - math.min(1, {A} / 3))"
    a["spawn"] = once({
        "throne": {"position": [0, f"-40 * {rise}", 0]},
        "rift": {"scale": f"math.min(1, {A} / 2)"},
        "mask": {"position": [0, f"24 * (1 - math.min(1, math.max(0, {A} - 1) / 2))", 0]},
        "hand_r": {"position": [f"-20 * {rise}", 0, 0]}, "hand_l": {"position": [f"20 * {rise}", 0, 0]},
    }, 3.5)
    return a


# --------------------------------------------------------------------------- Titan of Creation

def titan():
    a = {}
    idle = {
        "hips": {"position": [0, s(60, amp=0.4), 0]},
        "torso": {"rotation": [s(40, amp=1.2), s(25, amp=2), 0]},
        "core_gear": {"rotation": [0, 0, f"{T} * 60"]},
        "gear_halo": {"rotation": [0, 0, f"-{T} * 20"]},
        "astrolabe": {"rotation": [0, f"{T} * 30", 0]},
        "solids": {"rotation": [0, f"{T} * 15", 0]},
        "head": {"rotation": [s(35, amp=3), s(22, amp=8), 0]},
        "arm_r": {"rotation": [s(50, amp=3), 0, 0]},
        "arm_l": {"rotation": [s(50, 90, 3), 0, 0]},
        "holo": {"rotation": [0, f"{T} * 90", 0]},
    }
    for k in range(3):
        idle[f"claw_{k}_a"] = {"rotation": [s(90, k * 60, 8), 0, 0]}
    a["idle"] = loop(idle)
    step = f"math.sin({A} * 170)"
    a["move"] = loop({
        "leg_r": {"rotation": [f"{step} * 20", 0, 0]}, "leg_l": {"rotation": [f"-{step} * 20", 0, 0]},
        "shin_r": {"rotation": [f"math.max(0, -{step}) * 22", 0, 0]}, "shin_l": {"rotation": [f"math.max(0, {step}) * 22", 0, 0]},
        "arm_r": {"rotation": [f"-{step} * 12", 0, 0]}, "arm_l": {"rotation": [f"{step} * 12", 0, 0]},
        "hips": {"position": [0, f"math.abs({step}) * 1.2", 0]},
        "torso": {"rotation": [0, f"{step} * 4", 0]},
    })
    a["atk_a"] = once({
        "arm_r": {"rotation": kf([(0, (0, 0, 0)), (0.8, (-150, 0, -10)), (1.12, (-160, 0, -10)), (1.24, (-25, 0, 0)), (1.7, (-20, 0, 0))])},
        "forearm_r": {"rotation": kf([(0, (0, 0, 0)), (0.8, (-30, 0, 0)), (1.24, (-5, 0, 0))])},
        "torso": {"rotation": kf([(0, (0, 0, 0)), (0.8, (-10, -12, 0)), (1.24, (15, 8, 0)), (1.7, (10, 4, 0))])},
        "hips": {"position": kf([(0, (0, 0, 0)), (1.12, (0, 0, 0)), (1.24, (0, -2, 0)), (1.7, (0, -1, 0))])},
    }, 1.7)
    a["atk_b"] = once({
        "arm_l": {"rotation": kf([(0, (0, 0, 0)), (0.6, (-120, 0, 10)), (1.0, (-40, 0, 0)), (1.3, (-35, 0, 0))])},
        **{f"claw_{k}_a": {"rotation": kf([(0, (0, 0, 0)), (0.6, (-35, 0, 0)), (1.0, (20, 0, 0))])} for k in range(3)},
        "torso": {"rotation": kf([(0, (0, 0, 0)), (1.0, (12, 0, 0)), (1.3, (8, 0, 0))])},
    }, 1.3)
    a["atk_c"] = loop({
        "core_gear": {"rotation": [0, 0, f"{A} * 720"]},
        "arm_r": {"rotation": eased(-70, 0, -10)}, "arm_l": {"rotation": eased(-70, 0, 10)},
        "head": {"rotation": [f"-15 * {E} + {s(900, amp=3, clock=A)}", 0, 0]},
        "torso": {"rotation": [f"{s(720, amp=3, clock=A)}", 0, 0]},
    })
    a["atk_d"] = loop({
        "torso": {"rotation": [0, f"{A} * 420", 0]}, "gear_halo": {"scale": f"1 + 0.3 * {E}"},
        "arm_r": {"rotation": eased(0, 0, -60)}, "arm_l": {"rotation": eased(0, 0, 60)},
    })
    a["channel"] = loop({
        "arm_l": {"rotation": eased(-85, 0, 0)}, "forearm_l": {"rotation": eased(-10, 0, 0)},
        "holo": {"scale": f"1 + 0.8 * {E}"}, "head": {"rotation": eased(8, 15, 0)},
        **{f"claw_{k}_a": {"rotation": eased(-30, 0, 0)} for k in range(3)},
    })
    a["ultimate"] = loop({
        "hips": {"position": eased(0, -2, 0)},
        "arm_r": {"rotation": eased(-170, 0, -20)}, "arm_l": {"rotation": eased(-170, 0, 20)},
        "gear_halo": {"scale": f"1 + 0.5 * {E}", "rotation": [0, 0, f"-{A} * 240"]},
        "astrolabe": {"scale": f"1 + 0.4 * {E}", "rotation": [0, f"{A} * 400", 0]},
        "head": {"rotation": [0, f"math.max(0, {A} - 3.0) * 103", 0]},
        "core_gear": {"rotation": [0, 0, f"{A} * 600"]},
        "solids": {"scale": f"1 + 0.6 * {E}", "rotation": [0, f"{A} * 120", 0]},
    })
    a["stagger"] = loop({
        "torso": {"rotation": eased(20, 0, 0)}, "head": {"rotation": eased(15, 0, 0)},
        "arm_r": {"rotation": eased(10, 0, -5)}, "arm_l": {"rotation": eased(10, 0, 5)},
        "hips": {"position": eased(0, -3, 0)}, "gear_halo": {"rotation": [f"{s(300, amp=6, clock=A)}", 0, 0]},
    })
    a["death"] = once({
        "torso": {"rotation": [f"math.min(40, {A} * 12)", 0, f"{A} * 3"]},
        "hips": {"position": [0, f"-{A} * 3", 0]},
        "arm_r": {"rotation": [f"{A} * 10", 0, f"-{A} * 8"]}, "arm_l": {"rotation": [f"{A} * 10", 0, f"{A} * 8"]},
        "gear_halo": {"position": [0, f"-{A} * 8", f"{A} * 4"], "rotation": [f"{A} * 30", 0, 0]},
        "head": {"rotation": [f"{A} * 15", f"{A} * 20", 0]},
        "solids": {"scale": f"math.max(0, 1 - {A} / 3)"},
    }, 5.0)
    a["spawn"] = once({
        "hips": {"position": [0, f"-70 * (1 - math.min(1, {A} / 3.5))", 0]},
        "gear_halo": {"scale": f"math.min(1, {A} / 3.5)"},
        "arm_r": {"rotation": [f"-160 * (1 - math.min(1, {A} / 3.5))", 0, 0]},
        "arm_l": {"rotation": [f"-160 * (1 - math.min(1, {A} / 3.5))", 0, 0]},
    }, 4.0)
    return a


# --------------------------------------------------------------------------- Devouring Star

def star():
    a = {}
    idle = {
        "body": {"position": [0, s(70, amp=1.5), 0], "rotation": [s(50, amp=3), 0, s(40, amp=2)]},
        "head": {"rotation": [s(45, amp=3), s(30, amp=6), 0]},
        "jaw": {"rotation": [s(60, amp=4), 0, 0]},
        "mandible_r": {"rotation": [0, s(70, amp=6), 0]}, "mandible_l": {"rotation": [0, s(70, amp=-6), 0]},
        "inner_jaw": {"position": [0, 0, s(90, amp=0.6)]},
    }
    for side, sg in (("l", 1), ("r", -1)):
        for k in range(3):
            idle[f"fin_{side}{k}"] = {"rotation": [0, 0, f"{sg} * {s(120, -k * 40, 10 + k * 5)}"]}
    for i in range(6):
        idle[f"tail{i}"] = {"rotation": [s(80, -i * 35, 4), s(90, -i * 45, 6 + i * 2), 0]}
    for k in range(3):
        idle[f"lure{k}"] = {"rotation": [s(90, -k * 40, 6 + k * 3), 0, c(70, 0, 4)]}
    a["idle"] = loop(idle)
    move = {f"fin_{side}{k}": {"rotation": [0, 0, f"{sg} * {s(260, -k * 40, 12 + k * 6, A)}"]} for side, sg in (("l", 1), ("r", -1)) for k in range(3)}
    move.update({f"tail{i}": {"rotation": [0, s(240, -i * 45, 8 + i * 3, A), 0]} for i in range(6)})
    a["move"] = loop(move)
    a["atk_a"] = once({
        "head": {"rotation": kf([(0, (0, 0, 0)), (0.8, (-15, 0, 0)), (0.95, (10, 0, 0)), (2.0, (8, 0, 0))])},
        "jaw": {"rotation": kf([(0, (0, 0, 0)), (0.7, (5, 0, 0)), (0.9, (38, 0, 0)), (2.0, (36, 0, 0))])},
        "inner_jaw": {"position": kf([(0, (0, 0, 0)), (0.9, (0, 0, -2.5)), (2.0, (0, 0, -2.5))])},
    }, 2.0)
    a["atk_b"] = loop({
        "jaw": {"rotation": eased(48, 0, 0)}, "mandible_r": {"rotation": eased(0, -35, 0)}, "mandible_l": {"rotation": eased(0, 35, 0)},
        "body": {"rotation": eased(15, 0, 0)}, "head": {"rotation": eased(10, 0, 0)},
        **{f"tail{i}": {"rotation": eased(-6, 0, 0)} for i in range(6)},
    })
    a["atk_c"] = loop({
        "head": {"rotation": [f"{s(720, amp=-12, clock=A)}", 0, 0]},
        "jaw": {"rotation": [f"math.max(0, {s(720, amp=35, clock=A)})", 0, 0]},
    })
    a["atk_d"] = loop({
        "body": {"rotation": [0, f"{A} * 420", 0]},
        **{f"tail{i}": {"rotation": eased(0, 22, 0)} for i in range(6)},
        **{f"fin_{side}0": {"rotation": eased(0, 0, 25 * sg)} for side, sg in (("l", 1), ("r", -1))},
    })
    a["channel"] = loop({
        "lure0": {"rotation": eased(-35, 0, 0)}, "lure1": {"rotation": eased(-15, 0, 0)}, "lure2": {"rotation": eased(25, 0, 0)},
        "jaw": {"rotation": eased(25, 0, 0)},
        **{f"fin_{side}{k}": {"rotation": eased(0, 0, 18 * sg)} for side, sg in (("l", 1), ("r", -1)) for k in range(3)},
    })
    a["ultimate"] = loop({
        "body": {"rotation": eased(-30, 0, 0), "scale": f"1 + {s(400, amp=0.05, clock=A)}"},
        "jaw": {"rotation": eased(52, 0, 0)}, "mandible_r": {"rotation": eased(0, -45, 0)}, "mandible_l": {"rotation": eased(0, 45, 0)},
        "head": {"rotation": [f"-10 * {E}", f"{s(600, amp=4, clock=A)}", 0]},
        **{f"fin_{side}{k}": {"rotation": eased(0, 0, 35 * sg)} for side, sg in (("l", 1), ("r", -1)) for k in range(3)},
        **{f"tail{i}": {"rotation": eased(-12, 0, 0)} for i in range(6)},
        "lure2": {"scale": f"1 + 0.8 * {E}"},
    })
    a["stagger"] = loop({
        **{f"fin_{side}{k}": {"rotation": eased(0, 0, -20 * sg)} for side, sg in (("l", 1), ("r", -1)) for k in range(3)},
        "jaw": {"rotation": eased(20, 0, 0)}, "body": {"rotation": eased(15, 0, 0)},
        **{f"tail{i}": {"rotation": eased(6, 0, 0)} for i in range(6)},
    })
    a["death"] = once({
        "body": {"rotation": [f"{A} * 15", 0, f"{A} * 40"], "position": [0, f"-{A} * 6", 0]},
        "jaw": {"rotation": eased(50, 0, 0)},
        **{f"fin_{side}{k}": {"rotation": [0, 0, f"-{A} * 8 * {sg}"]} for side, sg in (("l", 1), ("r", -1)) for k in range(3)},
    }, 5.0)
    a["spawn"] = once({
        "body": {"position": [0, f"40 * (1 - math.min(1, {A} / 3))", 0], "rotation": [f"-60 * (1 - math.min(1, {A} / 3))", 0, 0]},
        "jaw": {"rotation": [f"40 * math.min(1, {A} / 3)", 0, 0]},
    }, 3.5)
    return a


# --------------------------------------------------------------------------- World Parasite

def parasite():
    a = {}
    roots = [(k, s_) for k in range(4) for s_ in range(5)]
    a["dormant"] = loop({
        "tree": {"rotation": [s(30, amp=1.5), 0, c(25, amp=1.5)]},
        "heart": {"scale": f"1 + {s(30, amp=0.02)}"},
    })
    idle = {
        "maw": {"rotation": [f"-12 + {s(50, amp=3)}", 0, 0]},
        "eyelid_r": {"rotation": [-100, 0, 0]}, "eyelid_l": {"rotation": [-100, 0, 0]},
        "heart": {"scale": f"1 + {s(120, amp=0.08)}"},
        "tree": {"rotation": [s(40, amp=4), 0, c(35, amp=4)]},
        "canopy": {"rotation": [s(55, amp=3), 0, c(45, amp=3)]},
        "body": {"position": [0, s(40, amp=0.4), 0]},
    }
    for k, s_ in roots:
        idle[f"root{k}_{s_}"] = {"rotation": [0, s(60, -s_ * 40 + k * 90, 6 + s_ * 3), s(50, -s_ * 30 + k * 60, 4)]}
    a["idle"] = loop(idle)
    a["move"] = loop({
        "body": {"position": [0, f"math.abs({s(180, amp=1.2, clock=A)})", 0]},
        **{f"root{k}_0": {"rotation": [0, s(180, k * 90, 15, A), 0]} for k in range(4)},
    })
    a["atk_a"] = once({
        "maw": {"rotation": kf([(0, (0, 0, 0)), (0.5, (-30, 0, 0)), (1.2, (-26, 0, 0)), (1.6, (0, 0, 0))])},
        **{f"root{k}_0": {"rotation": kf([(0, (0, 0, 0)), (0.5, (0, 0, 20)), (0.7, (0, 0, -15)), (1.6, (0, 0, 0))])} for k in range(4)},
    }, 1.6)
    a["atk_b"] = once({
        "heart": {"scale": kf([(0, (1, 1, 1)), (0.4, (1.4, 1.4, 1.4)), (0.55, (0.8, 0.8, 0.8)), (0.8, (1, 1, 1))])},
        "tree": {"rotation": kf([(0, (0, 0, 0)), (0.4, (12, 0, 8)), (0.6, (-10, 0, -8)), (0.8, (0, 0, 0))])},
    }, 0.8)
    a["atk_c"] = once({
        "body": {"position": kf([(0, (0, 0, 0)), (0.9, (0, 6, 0)), (1.2, (0, -2, 0)), (1.5, (0, 0, 0))])},
        "maw": {"rotation": kf([(0, (0, 0, 0)), (0.9, (-25, 0, 0)), (1.2, (5, 0, 0)), (1.5, (0, 0, 0))])},
        **{f"root{k}_0": {"rotation": kf([(0, (0, 0, 0)), (0.9, (0, 0, 25 if k < 2 else -25)), (1.2, (0, 0, 0))])} for k in range(4)},
    }, 1.5)
    a["atk_d"] = a["atk_a"]
    a["channel"] = loop({
        "maw": {"rotation": eased(-20, 0, 0)}, "heart": {"scale": f"1 + {s(500, amp=0.15, clock=A)}"},
        **{f"root{k}_0": {"rotation": eased(0, 0, -30 if k < 2 else 30)} for k in range(4)},
        **{f"root{k}_2": {"rotation": eased(0, 0, -20 if k < 2 else 20)} for k in range(4)},
    })
    a["burrow"] = loop({
        "maw": {"rotation": [0, 0, 0]}, "eyelid_r": {"rotation": [0, 0, 0]}, "eyelid_l": {"rotation": [0, 0, 0]},
        **{f"root{k}_0": {"rotation": eased(0, 0, 40 if k < 2 else -40)} for k in range(4)},
        "tree": {"rotation": [f"{s(800, amp=8, clock=A)}", 0, 0]},
    })
    a["ultimate"] = loop({
        "maw": {"rotation": eased(-55, 0, 0)}, "heart": {"scale": f"1 + 0.4 * {E} + {s(600, amp=0.1, clock=A)}"},
        **{f"root{k}_0": {"rotation": eased(0, 0, -60 if k < 2 else 60)} for k in range(4)},
        **{f"root{k}_1": {"rotation": eased(0, 0, -20 if k < 2 else 20)} for k in range(4)},
        "tree": {"rotation": [f"{s(600, amp=15, clock=A)}", 0, f"{c(500, amp=10, clock=A)}"]},
    })
    a["stagger"] = loop({
        "maw": {"rotation": eased(-5, 0, 0)}, "eyelid_r": {"rotation": eased(50, 0, 0)}, "eyelid_l": {"rotation": eased(50, 0, 0)},
        "heart": {"scale": f"1 + {s(60, amp=0.03, clock=A)}"},
    })
    a["death"] = once({
        "maw": {"rotation": [f"-math.min(60, {A} * 30)", 0, 0]},
        "eyelid_r": {"rotation": [f"math.min(100, {A} * 40)", 0, 0]}, "eyelid_l": {"rotation": [f"math.min(100, {A} * 40)", 0, 0]},
        "body": {"position": [0, f"-{A} * 5", 0]},
        "tree": {"rotation": [f"math.min(85, {A} * 25)", 0, 0]},
        "heart": {"scale": f"math.max(0.3, 1 - {A} * 0.15)"},
    }, 5.0)
    a["spawn"] = once({
        "maw": {"rotation": kf([(0, (0, 0, 0)), (1.0, (-10, 0, 0)), (2.0, (-45, 0, 0)), (3.0, (-12, 0, 0))])},
        "eyelid_r": {"rotation": kf([(0, (0, 0, 0)), (1.0, (0, 0, 0)), (1.5, (-100, 0, 0))])},
        "eyelid_l": {"rotation": kf([(0, (0, 0, 0)), (1.1, (0, 0, 0)), (1.6, (-100, 0, 0))])},
        "body": {"position": [f"{s(1500, amp=0.6, clock=A)} * (1 - math.min(1, {A} / 3))", 0, 0]},
    }, 3.0)
    return a


# --------------------------------------------------------------------------- Choir of Mirrors

def choir():
    a = {}
    idle = {
        "body": {"position": [0, s(60, amp=1.2), 0]},
        "mask": {"rotation": [s(40, amp=3), s(25, amp=6), 0]},
        "mask_shard": {"position": [s(70, amp=0.6), c(60, amp=0.5), 0], "rotation": [0, 0, s(50, amp=6)]},
        "halo": {"rotation": [0, 0, f"{T} * 20"]},
        "voice": {"rotation": [0, f"{T} * 60", 0], "position": [0, s(90, amp=0.6), 0]},
        "chorus": {"rotation": [0, f"{T} * 30", 0]},
    }
    for side, sg in (("l", 1), ("r", -1)):
        for tier in range(3):
            idle[f"wing_{side}{tier}"] = {"rotation": [0, f"{sg} * {s(50, tier * 30, 6)}", f"{sg} * {s(60, tier * 40, 5)}"]}
    for k in range(4):
        for s_ in range(3):
            idle[f"ribbon{k}_{s_}"] = {"rotation": [s(90, -s_ * 40 + k * 30, 6 + s_ * 4), 0, c(70, -s_ * 30, 4)]}
    for k in range(6):
        idle[f"chorister{k}"] = {"position": [0, s(80, k * 60, 1.2), 0]}
    a["idle"] = loop(idle)
    a["move"] = loop({
        **{f"wing_{side}{t}": {"rotation": eased(0, -12 * sg, 0)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
        **{f"ribbon{k}_0": {"rotation": eased(25, 0, 0)} for k in range(4)},
    })
    a["atk_a"] = loop({
        "mask": {"rotation": eased(-15, 0, 0)}, "mask_shard": {"position": eased(2, 2, -1)}, "halo": {"scale": f"1 + 0.15 * {E}"},
        **{f"wing_{side}{t}": {"rotation": [0, 0, f"{sg} * (10 * {E} + {s(900, t * 60, 3, A)})"]} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
    })
    a["atk_b"] = loop({
        "halo": {"rotation": [0, 0, f"{A} * 400"]},
        **{f"wing_{side}{t}": {"rotation": eased(0, -30 * sg, 0)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
    })
    a["atk_c"] = loop({
        **{f"wing_{side}{t}": {"rotation": eased(0, 0, 25 * sg)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
        "chorus": {"rotation": [0, f"{A} * 200", 0]}, "mask": {"rotation": eased(-10, 0, 0)},
    })
    a["atk_d"] = loop({"chorus": {"scale": f"1 + 0.8 * {E}", "rotation": [0, f"{A} * 400", 0]}})
    a["channel"] = loop({
        **{f"wing_{side}{t}": {"rotation": eased(0, 10 * sg, 18 * sg)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
        "halo": {"scale": f"1 + 0.3 * {E}"}, "mask": {"rotation": eased(-12, 0, 0)},
    })
    a["ultimate"] = loop({
        **{f"wing_{side}{t}": {"rotation": eased(0, 15 * sg, 35 * sg)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
        "halo": {"scale": f"1 + 0.8 * {E}", "rotation": [0, 0, f"{A} * 160"]},
        "chorus": {"scale": f"1 + 0.5 * {E}", "rotation": [0, f"{A} * 160", 0]},
        "mask": {"position": eased(0, 4, 0)}, "mask_shard": {"position": eased(6, 4, -2)},
        "voice": {"scale": f"1 + 0.6 * {E}"},
    })
    a["stagger"] = loop({
        **{f"wing_{side}{t}": {"rotation": eased(0, 0, -20 * sg)} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
        "mask": {"rotation": eased(20, 0, 0)}, "mask_shard": {"position": eased(0, -4, 0)},
    })
    a["death"] = once({
        "halo": {"scale": f"math.max(0, 1 - {A} / 4)"},
        "mask_shard": {"position": [0, f"-{A} * 10", 0], "rotation": [f"{A} * 90", 0, 0]},
        "mask": {"rotation": [f"{A} * 10", 0, f"{A} * 8"]},
        "chorus": {"scale": f"1 + {A} * 0.5"},
        **{f"wing_{side}{t}": {"rotation": [0, 0, f"-{A} * 12 * {sg}"], "scale": f"math.max(0, 1 - {A} / 5)"} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
    }, 5.0)
    a["spawn"] = once({
        "halo": {"scale": f"math.min(1, {A} / 2)"},
        "body": {"position": [0, f"30 * (1 - math.min(1, {A} / 3))", 0]},
        **{f"wing_{side}{t}": {"scale": f"math.min(1, {A} / 2.5)"} for side, sg in (("l", 1), ("r", -1)) for t in range(3)},
    }, 3.5)
    return a


ALL = {"void_emperor": emperor, "titan": titan, "devouring_star": star, "world_parasite": parasite, "choir": choir}
