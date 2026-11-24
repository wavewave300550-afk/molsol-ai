"""
Resource pack content: animations, animation controllers, render controllers,
client entities, particles, fogs and sound definitions.

Rotation conventions (see modelkit): +rx tilts forward-pointing bones down and
swings hanging bones back; +ry turns forward-pointing bones to the entity's
right (-X); +rz swings hanging bones towards -X. Positions are in geometry
space (+x = towards +X, the entity's left).
"""
from __future__ import annotations

from models import PLATES, SEGMENTS

NS = "porcelain"
LT = "q.life_time"
PHASE = "q.property('porcelain:phase')"
ACTION = "q.property('porcelain:action')"

# action ids shared with src/config.ts (validated by tools/validate.py)
ACTIONS = {
    "idle": 0, "procession": 1, "edict": 2, "breath": 3, "repair": 4, "dive": 5, "stagger": 6,
    "rubble": 7, "claw": 8, "storm": 9, "kowtow_call": 10, "kowtow_bow": 11, "rush_out": 12,
    "rush_in": 13, "roar": 14, "death": 15, "awaken": 16, "perch": 17,
}

CHAIN = [f"seg{i}" for i in range(1, SEGMENTS + 1)] + ["tail1", "tail2", "tail3"]
SIDES = (("r", -1), ("l", 1))   # bone suffix, geometry side (-1 = -X = entity right)


def anim(bones, loop=True, length=None, hold=False):
    a = {"loop": "hold_on_last_frame" if hold else loop, "bones": bones}
    if length:
        a["animation_length"] = length
    return a


def merge(*dicts):
    out = {}
    for d in dicts:
        for bone, ch in d.items():
            tgt = out.setdefault(bone, {})
            for k, v in ch.items():
                tgt[k] = v
    return out


def kf(points):
    """Keyframes {time: value} -> Bedrock keyframe dict with string times."""
    return {f"{t:.2f}": v for t, v in points}


# --------------------------------------------------------------------------- emperor animations

def emperor_animations():
    A = {}
    # ---- idle: swimming through the sky
    idle = {
        "root": {"position": [0, f"math.sin({LT} * 50) * 2.5", 0]},
        "body": {"rotation": [f"math.sin({LT} * 50 + 40) * 2", f"math.sin({LT} * 35) * 3", 0]},
        "neck1": {"rotation": [f"math.sin({LT} * 50) * 3", f"math.sin({LT} * 55 + 40) * -5", 0]},
        "neck2": {"rotation": [f"math.sin({LT} * 50 - 30) * 2", f"math.sin({LT} * 55 + 20) * -4", 0]},
        "head": {"rotation": [f"math.sin({LT} * 50 - 60) * -3", f"math.sin({LT} * 55) * 6", 0]},
        "crown": {"position": [0, f"1 + math.sin({LT} * 70) * 0.8", 0],
                  "rotation": [f"math.sin({LT} * 70 - 30) * 2", 0, f"math.sin({LT} * 45) * 2"]},
        "mane": {"rotation": [f"math.sin({LT} * 110) * 6", 0, 0]},
        "beard": {"rotation": [f"math.sin({LT} * 100) * 8", 0, 0]},
        "heart": {"scale": f"1 + math.sin({LT} * 240) * 0.07"},
        "ruyi": {"rotation": [0, f"math.sin({LT} * 55 - 480) * 10", f"math.sin({LT} * 40) * 8"]},
    }
    for i, b in enumerate(CHAIN, start=1):
        idle[b] = {"rotation": [f"math.sin({LT} * 70 - {i * 35}) * 2.5",
                                f"math.sin({LT} * 55 - {i * 42}) * {8 + i * 0.7:.1f}", 0]}
    for s, side in SIDES:
        ph = 0 if side < 0 else 180
        out = -side  # +rz swings hanging parts towards -X: outwards for the right limb
        idle[f"arm_{s}"] = {"rotation": [f"math.sin({LT} * 80 + {ph}) * 24 - 6", 0,
                                         f"{6 * out} + math.sin({LT} * 80 + {ph}) * {4 * out}"]}
        idle[f"arm_{s}_fore"] = {"rotation": [f"math.sin({LT} * 80 + {ph - 50}) * 18", 0, 0]}
        idle[f"arm_{s}_talons"] = {"rotation": [f"math.sin({LT} * 80 + {ph - 90}) * 10", 0, 0]}
        idle[f"leg_{s}"] = {"rotation": [f"math.sin({LT} * 80 + {ph + 90}) * 20", 0, f"{5 * out}"]}
        idle[f"leg_{s}_fore"] = {"rotation": [f"math.sin({LT} * 80 + {ph + 40}) * 14", 0, 0]}
        for k in (1, 2, 3):
            idle[f"wh_{s}{k}"] = {"rotation": [f"math.sin({LT} * 90 - {(k - 1) * 50}) * {6 + k * 4}",
                                               f"math.cos({LT} * 70 - {(k - 1) * 40}) * {6 + k * 2}", 0]}
    for i in range(5):
        idle[f"bead_f{i}"] = {"rotation": [f"math.sin({LT} * 90 + {i * 25}) * 6", 0, f"math.sin({LT} * 60 + {i * 40}) * 4"]}
    for i in range(3):
        idle[f"bead_b{i}"] = {"rotation": [f"math.sin({LT} * 90 + {i * 35 + 60}) * 6", 0, f"math.sin({LT} * 60 + {i * 50}) * 4"]}
    for i in range(1, PLATES + 1):
        idle[f"plate{i}"] = {"rotation": [f"math.sin({LT} * 60 - {i * 35}) * 4", 0, 0]}
    A["animation.porcelain.emperor.idle"] = anim(idle)

    # ---- bend & tilt (driven by the script while flying)
    bend = "q.property('porcelain:bend')"
    tilt = "q.property('porcelain:tilt')"
    bd = {
        "root": {"rotation": [f"{tilt} * -30", 0, f"{bend} * -18"]},
        "neck1": {"rotation": [0, f"{bend} * 10", 0]},
        "head": {"rotation": [f"{tilt} * 10", f"{bend} * 8", 0]},
    }
    for i, b in enumerate(CHAIN, start=1):
        bd[b] = {"rotation": [f"{tilt} * {2 + i * 0.4:.1f}", f"{bend} * {7 + i * 0.5:.1f}", 0]}
    A["animation.porcelain.emperor.bend"] = anim(bd)

    # ---- damage state: the rings drift apart, the limbs float further away
    gap = f"({PHASE} >= 3 ? 3.0 : ({PHASE} >= 2 ? 1.0 : 0.0))"
    ph = {b: {"position": [0, 0, gap]} for b in CHAIN + ["ruyi"]}
    ph.update({
        "neck1": {"position": [0, 0, f"-{gap} * 0.8"]},
        "neck2": {"position": [0, 0, f"-{gap} * 0.8"]},
        "crown": {"position": [0, f"{gap} * 1.2", 0]},
        "chest_r": {"rotation": [0, f"{PHASE} >= 3 ? 25 : 0", 0]},
        "chest_l": {"rotation": [0, f"{PHASE} >= 3 ? -25 : 0", 0]},
        "heart": {"scale": f"{PHASE} >= 3 ? 1.25 : 1.0"},
    })
    for s, side in SIDES:
        ph[f"arm_{s}"] = {"position": [f"{gap} * {1.5 * side}", f"-{gap} * 0.5", 0]}
        ph[f"leg_{s}"] = {"position": [f"{gap} * {1.2 * side}", 0, 0]}
    A["animation.porcelain.emperor.phase"] = anim(ph)

    # ---- actions
    def jaws(open_y, open_x=0):
        return {"jaw_r": {"rotation": [open_x, open_y, 0]}, "jaw_l": {"rotation": [open_x, -open_y if isinstance(open_y, (int, float)) else f"-({open_y})", 0]}}

    def arms(rx, rz_out, fore=0):
        d = {}
        for s, side in SIDES:
            rz = rz_out * -side
            d[f"arm_{s}"] = {"rotation": [rx, 0, rz]}
            if fore:
                d[f"arm_{s}_fore"] = {"rotation": [fore, 0, 0]}
        return d

    def chest(open_deg):
        return {"chest_r": {"rotation": [0, open_deg, 0]}, "chest_l": {"rotation": [0, -open_deg, 0]}}

    A["animation.porcelain.emperor.procession"] = anim(merge(
        {b: {"rotation": [0, f"math.sin({LT} * 160 - {i * 40}) * 6", 0]} for i, b in enumerate(CHAIN, 1)},
        {"neck1": {"rotation": [20, 0, 0]}, "neck2": {"rotation": [8, 0, 0]}, "head": {"rotation": [-12, 0, 0]},
         "crown": {"rotation": [-8, 0, 0]}, "mane": {"rotation": [-25, 0, 0]}},
        jaws(8, 6), arms(55, 0), {f"leg_{s}": {"rotation": [60, 0, 0]} for s, _ in SIDES},
        {f"wh_{s}1": {"rotation": [-10, 0, 0]} for s, _ in SIDES},
    ))
    edict = merge(
        {f"plate{i}": {"position": [0, f"2.5 + math.sin({LT} * 400 + {i * 60}) * 0.4", 0],
                       "rotation": [f"-8 + math.sin({LT} * 300 + {i * 50}) * 3", 0, 0]} for i in range(1, PLATES + 1)},
        {"neck1": {"rotation": [-15, 0, 0]}, "head": {"rotation": [-10, 0, 0]}, "body": {"rotation": [-8, 0, 0]}},
        jaws(12, 4), arms(-20, 25),
    )
    A["animation.porcelain.emperor.edict"] = anim(edict)
    A["animation.porcelain.emperor.breath"] = anim(merge(
        {"neck1": {"rotation": kf([(0, [0, 0, 0]), (0.9, [-28, 0, 0]), (1.1, [22, 0, 0]), (2.6, [22, 0, 0]), (3.0, [0, 0, 0])])},
         "neck2": {"rotation": kf([(0, [0, 0, 0]), (0.9, [-10, 0, 0]), (1.1, [6, 0, 0]), (2.6, [6, 0, 0]), (3.0, [0, 0, 0])])},
         "head": {"rotation": kf([(0, [0, 0, 0]), (0.9, [-18, 0, 0]), (1.1, [4, 0, 0]),
                                  (2.6, ["4 + math.sin(q.anim_time * 1500) * 2", 0, 0]), (3.0, [0, 0, 0])])},
         "jaw_r": {"rotation": kf([(0, [0, 0, 0]), (0.8, [0, 4, 0]), (1.0, [14, 34, 0]), (2.6, [14, 34, 0]), (3.0, [0, 0, 0])])},
         "jaw_l": {"rotation": kf([(0, [0, 0, 0]), (0.8, [0, -4, 0]), (1.0, [14, -34, 0]), (2.6, [14, -34, 0]), (3.0, [0, 0, 0])])},
         "throat": {"scale": kf([(0, 1), (0.8, 1.3), (1.0, 1.6), (2.6, 1.6), (3.0, 1)])},
         "crown": {"rotation": kf([(0, [0, 0, 0]), (0.9, [-10, 0, 0]), (1.1, [6, 0, 0]), (3.0, [0, 0, 0])])}},
        {f"arm_{s}": {"rotation": kf([(0, [0, 0, 0]), (0.9, [-30, 0, 0]), (1.1, [20, 0, 0]), (3.0, [0, 0, 0])])} for s, _ in SIDES},
        {f"bead_f{i}": {"rotation": kf([(0, [0, 0, 0]), (0.9, [14, 0, 0]), (1.1, [-16, 0, 0]), (3.0, [0, 0, 0])])} for i in range(5)},
    ), loop=False, length=3.0, hold=True)
    A["animation.porcelain.emperor.repair"] = anim(merge(
        {b: {"rotation": [0, 26 if b.startswith("seg") else 22, 0]} for b in CHAIN},
        chest(40), {"heart": {"scale": f"1.4 + math.sin({LT} * 400) * 0.1"},
                    "neck1": {"rotation": [-20, 0, 0]}, "head": {"rotation": [-15, 0, 0]},
                    "crown": {"position": [0, 2, 0]}},
        arms(-40, 45),
    ))
    A["animation.porcelain.emperor.dive"] = anim(merge(
        {"neck1": {"rotation": [25, 0, 0]}, "neck2": {"rotation": [10, 0, 0]}, "head": {"rotation": [-5, 0, 0]},
         "mane": {"rotation": [-30, 0, 0]}},
        arms(-70, 8), {f"arm_{s}_talons": {"rotation": [-30, 0, 0]} for s, _ in SIDES},
    ))
    A["animation.porcelain.emperor.stagger"] = anim(merge(
        {"neck1": {"rotation": [35, 0, 0]}, "neck2": {"rotation": [15, 0, 0]}, "head": {"rotation": [18, 0, 0]},
         "crown": {"rotation": [0, 0, 18], "position": [0, -1, 0]}, "heart": {"scale": 1.3}},
        jaws(10, 18), arms(30, 10), chest(20),
        {b: {"rotation": [-2, 0, 0]} for b in CHAIN},
        {f"bead_f{i}": {"rotation": [0, 0, f"math.sin({LT} * 50 + {i * 30}) * 12"]} for i in range(5)},
    ))
    A["animation.porcelain.emperor.rubble"] = anim(merge(
        {f"arm_{s}": {"rotation": [-120, 0, 20 * -side]} for s, side in SIDES},
        {f"arm_{s}_talons": {"rotation": [-40, 0, 0]} for s, _ in SIDES},
        {"neck1": {"rotation": [-20, 0, 0]}, "head": {"rotation": [-20, 0, 0]}, "body": {"rotation": [-10, 0, 0]}},
        {f"plate{i}": {"position": [0, f"math.sin({LT} * 600 + {i * 70}) * 0.5", 0]} for i in range(1, PLATES + 1)},
    ))
    A["animation.porcelain.emperor.claw"] = anim(merge(
        {"arm_r": {"rotation": kf([(0, [0, 0, 0]), (0.4, [-100, 0, 10]), (0.8, [-100, 0, 10]), (1.2, [0, 0, 0])])},
         "head": {"rotation": kf([(0, [0, 0, 0]), (0.4, [8, 10, 0]), (1.2, [0, 0, 0])])}},
        jaws(10, 6),
    ), loop=False, length=1.2, hold=True)
    A["animation.porcelain.emperor.storm"] = anim(merge(
        {b: {"rotation": [0, 36, 0]} for b in CHAIN},
        {"ruyi": {"rotation": [0, 30, 0]}, "root": {"rotation": [0, f"{LT} * 120", 0]},
         "neck1": {"rotation": [-30, 0, 0]}, "head": {"rotation": [-10, 0, 0]}},
        arms(-30, 50), jaws(14, 8),
    ))
    A["animation.porcelain.emperor.kowtow_call"] = anim(merge(
        {"neck1": {"rotation": [-25, 0, 0]}, "neck2": {"rotation": [-10, 0, 0]}, "head": {"rotation": [10, 0, 0]},
         "crown": {"position": [0, 2, 0]}, "mask": {"scale": 1.12},
         "bead_f0": {"rotation": [0, 0, 38]}, "bead_f1": {"rotation": [0, 0, 30]},
         "bead_f2": {"rotation": [70, 0, 0]},
         "bead_f3": {"rotation": [0, 0, -30]}, "bead_f4": {"rotation": [0, 0, -38]}},
        arms(-30, 40),
        {f"plate{i}": {"position": [0, f"1.5 + math.sin({LT} * 500 + {i * 60}) * 0.3", 0]} for i in range(1, PLATES + 1)},
    ))
    A["animation.porcelain.emperor.kowtow_bow"] = anim(merge(
        {"neck1": {"rotation": [55, 0, 0]}, "neck2": {"rotation": [25, 0, 0]}, "head": {"rotation": [5, 0, 0]},
         "crown": {"rotation": [15, 0, 0]}, "heart": {"scale": 1.3}},
        arms(-60, 6), chest(30),
    ))
    A["animation.porcelain.emperor.rush_out"] = anim(merge(
        {"root": {"scale": kf([(0, 1.0), (0.5, 0.05), (0.6, 0.01)]),
                  "position": [f"math.sin(q.anim_time * 3000) * 1.5", 0, 0]}},
        {b: {"position": [0, 0, kf([(0, 0), (0.5, 6)])]} for b in CHAIN},
    ), loop=False, length=0.6, hold=True)
    A["animation.porcelain.emperor.rush_in"] = anim(merge(
        {"root": {"scale": kf([(0, 0.01), (0.35, 1.0)])},
         "neck1": {"rotation": kf([(0, [0, 0, 0]), (0.35, [-10, 0, 0]), (0.55, [25, 0, 0]), (1.0, [0, 0, 0])])}},
        {"jaw_r": {"rotation": kf([(0, [0, 0, 0]), (0.35, [12, 32, 0]), (0.6, [0, 0, 0])])},
         "jaw_l": {"rotation": kf([(0, [0, 0, 0]), (0.35, [12, -32, 0]), (0.6, [0, 0, 0])])}},
    ), loop=False, length=1.0, hold=True)
    shake = "math.sin(q.anim_time * 1800) * 6"
    A["animation.porcelain.emperor.roar"] = anim(merge(
        {"body": {"rotation": kf([(0, [0, 0, 0]), (0.5, [-25, 0, 0]), (2.5, [-25, 0, 0]), (3.0, [0, 0, 0])])},
         "neck1": {"rotation": kf([(0, [0, 0, 0]), (0.5, [-20, 0, 0]), (2.5, [-20, 0, 0]), (3.0, [0, 0, 0])])},
         "head": {"rotation": [0, 0, f"(q.anim_time > 0.6 && q.anim_time < 2.4) ? {shake} : 0"]},
         "jaw_r": {"rotation": kf([(0, [0, 0, 0]), (0.5, [20, 38, 0]), (2.5, [20, 38, 0]), (3.0, [0, 0, 0])])},
         "jaw_l": {"rotation": kf([(0, [0, 0, 0]), (0.5, [20, -38, 0]), (2.5, [20, -38, 0]), (3.0, [0, 0, 0])])},
         "throat": {"scale": kf([(0, 1), (0.5, 1.7), (2.5, 1.7), (3.0, 1)])}},
        {f"arm_{s}": {"rotation": kf([(0, [0, 0, 0]), (0.5, [-50, 0, 50 * -side]), (2.5, [-50, 0, 50 * -side]), (3.0, [0, 0, 0])])}
         for s, side in SIDES},
        {f"plate{i}": {"position": [0, f"(q.anim_time < 2.5) ? math.abs(math.sin(q.anim_time * 900 + {i * 40})) * 1.2 : 0", 0]}
         for i in range(1, PLATES + 1)},
    ), loop=False, length=3.0, hold=True)
    death = merge(
        {"root": {"position": [0, kf([(0, 0), (6, 6)]), 0], "scale": kf([(0, 1.0), (5.0, 1.0), (6.0, 0.0)])},
         "head": {"rotation": kf([(0, [0, 0, 0]), (2, [-35, 0, 0])])},
         "jaw_r": {"rotation": kf([(0, [0, 0, 0]), (2, [10, 30, 0])])},
         "jaw_l": {"rotation": kf([(0, [0, 0, 0]), (2, [10, -30, 0])])},
         "heart": {"scale": kf([(0, 1.0), (5, 2.2)])}},
        {b: {"position": [0, 0, kf([(0, 0), (6, i * 3)])],
             "rotation": [f"math.sin(q.anim_time * 2000 + {i * 50}) * 3", 0, f"math.cos(q.anim_time * 1700 + {i * 40}) * 3"]}
         for i, b in enumerate(CHAIN, 1)},
        {f"arm_{s}": {"position": [kf([(0, 0), (6, 8 * side)]), 0, 0]} for s, side in SIDES},
    )
    A["animation.porcelain.emperor.death"] = anim(death, loop=False, length=6.0, hold=True)
    coil = {b: {"rotation": [0, 30, 0]} for b in CHAIN}
    A["animation.porcelain.emperor.perch"] = anim(merge(
        coil, {"neck1": {"rotation": [40, 0, 0]}, "head": {"rotation": [10, 0, 0]},
               "heart": {"scale": f"1 + math.sin({LT} * 90) * 0.05"}},
        arms(40, 5),
    ))
    A["animation.porcelain.emperor.awaken"] = anim(merge(
        {b: {"rotation": kf([(0, [0, 30, 0]), (3.0, [0, 0, 0])])} for b in CHAIN},
        {"neck1": {"rotation": kf([(0, [40, 0, 0]), (2.5, [-10, 0, 0]), (3.2, [0, 0, 0])])},
         "head": {"rotation": kf([(0, [10, 0, 0]), (2.0, [-20, 0, 0]), (4.0, [0, 0, 0])])},
         "jaw_r": {"rotation": kf([(0, [0, 0, 0]), (2.8, [0, 0, 0]), (3.1, [18, 36, 0]), (3.8, [0, 0, 0])])},
         "jaw_l": {"rotation": kf([(0, [0, 0, 0]), (2.8, [0, 0, 0]), (3.1, [18, -36, 0]), (3.8, [0, 0, 0])])},
         "bead_f2": {"rotation": kf([(0, [0, 0, 0]), (2.6, [0, 0, 0]), (3.0, [50, 0, 0]), (4.0, [0, 0, 0])])}},
        {f"arm_{s}": {"rotation": kf([(0, [40, 0, 0]), (3.0, [0, 0, 0])])} for s, _ in SIDES},
    ), loop=False, length=4.0, hold=True)
    return A


def emperor_controller():
    states = {}
    names = list(ACTIONS.keys())
    for name in names:
        st = {"transitions": [{other: f"{ACTION} == {ACTIONS[other]}"} for other in names if other != name],
              "blend_transition": 0.3}
        if name != "idle":
            st["animations"] = [name]
        states["default" if name == "idle" else name] = st
    # transitions must reference state names: "idle" is the default state
    for st in states.values():
        st["transitions"] = [{("default" if k == "idle" else k): v for k, v in tr.items()} for tr in st["transitions"]]
    return {"controller.animation.porcelain.emperor.action": {"initial_state": "default", "states": states}}


# --------------------------------------------------------------------------- minor animations

def minor_animations():
    A = {}
    emb = "q.property('porcelain:embedded')"
    A["animation.porcelain.edict_tablet.fly"] = anim({
        "tablet": {"rotation": [f"{emb} ? 0 : {LT} * 540", f"{emb} ? 0 : {LT} * 200", 0],
                   "position": [0, f"{emb} ? -2 : 0", 0]},
        "halo": {"scale": f"{emb} ? (1 + math.sin({LT} * 360) * 0.08) : 0.6"},
    })
    A["animation.porcelain.shard.spin"] = anim({"shard": {"rotation": [f"{LT} * 720", f"{LT} * 380", 0]}})
    A["animation.porcelain.rubble.float"] = anim({
        "chunk": {"rotation": [f"math.sin({LT} * 40) * 12", f"{LT} * 30", f"math.cos({LT} * 50) * 10"]},
        "pebbles": {"rotation": [0, f"{LT} * -160", 0]},
    })
    A["animation.porcelain.severed_claw.hunt"] = anim({
        "claw": {"position": [0, f"math.sin({LT} * 200) * 1.2", 0]},
        "talons": {"rotation": [f"q.property('porcelain:strike') ? (math.sin({LT} * 1400) * 35 - 20) : math.sin({LT} * 300) * 12", 0, 0]},
        "palm": {"rotation": [f"q.property('porcelain:strike') ? -25 : 0", 0, 0]},
    })
    walk = "q.modified_distance_moved"
    spd = "q.modified_move_speed"
    A["animation.porcelain.courtier.move"] = anim({
        "leg_r": {"rotation": [f"math.cos({walk} * 38.17) * 40 * {spd}", 0, 0]},
        "leg_l": {"rotation": [f"-math.cos({walk} * 38.17) * 40 * {spd}", 0, 0]},
        "arm_r": {"rotation": [f"-math.cos({walk} * 38.17) * 25 * {spd} + (q.has_target ? -40 + math.sin({LT} * 700) * 30 : 0)", 0, 0]},
        "arm_l": {"rotation": [f"math.cos({walk} * 38.17) * 25 * {spd} + (q.has_target ? -40 - math.sin({LT} * 700) * 30 : 0)", 0, 0]},
        "body": {"rotation": [f"q.has_target ? 8 : 0", 0, f"math.sin({LT} * 90) * 2"]},
        "head": {"rotation": ["q.target_x_rotation * 0.5", "q.target_y_rotation * 0.7", 0]},
    })
    A["animation.porcelain.courtier.rise"] = anim({
        "root": {"scale": f"math.clamp({LT} * 1.2, 0.05, 1.0)",
                 "position": [0, f"math.min(0, ({LT} - 0.8) * 12)", 0]},
    })
    return A


# --------------------------------------------------------------------------- render controllers

def render_controllers():
    vis = [{"*": True}]
    for i in range(1, PLATES + 1):
        vis.append({f"plate{i}": f"q.property('porcelain:plates') >= {i}"})
    for i in (2, 4, 6):
        vis.append({f"seg{i}_top": f"{PHASE} < 3"})
    vis.append({"arm_r": "q.property('porcelain:claw') == 0"})
    return {
        "controller.render.porcelain.emperor": {
            "arrays": {"textures": {"Array.skins": ["Texture.pristine", "Texture.kintsugi", "Texture.shattered"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": [f"Array.skins[math.clamp({PHASE} - 1, 0, 2)]"],
            "part_visibility": vis,
        },
        "controller.render.porcelain.default": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
        },
    }


# --------------------------------------------------------------------------- client entities

def client_entities(geo_ids):
    tex = "textures/entity/porcelain"

    def ce(identifier, model, animations, animate, material="entity_emissive_alpha", textures=None, rc=None,
           controllers=None, offscreen=False):
        desc = {
            "identifier": identifier,
            "materials": {"default": material},
            "textures": textures or {"default": f"{tex}/{model}"},
            "geometry": {"default": geo_ids[model]},
            "animations": animations,
            "scripts": {"animate": animate},
            "render_controllers": [rc or "controller.render.porcelain.default"],
        }
        if offscreen:
            desc["scripts"]["should_update_bones_and_effects_offscreen"] = True
        return {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}

    emp_anims = {name.split(".")[-1]: name for name in emperor_animations()}
    emp_anims["action_ctrl"] = "controller.animation.porcelain.emperor.action"
    return {
        "emperor": ce(f"{NS}:emperor", "emperor", emp_anims, ["idle", "bend", "phase", "action_ctrl"],
                      textures={"pristine": f"{tex}/emperor_pristine", "kintsugi": f"{tex}/emperor_kintsugi",
                                "shattered": f"{tex}/emperor_shattered"},
                      rc="controller.render.porcelain.emperor", offscreen=True),
        "edict_tablet": ce(f"{NS}:edict_tablet", "edict_tablet", {"fly": "animation.porcelain.edict_tablet.fly"}, ["fly"]),
        "shard": ce(f"{NS}:shard", "shard", {"spin": "animation.porcelain.shard.spin"}, ["spin"]),
        "rubble": ce(f"{NS}:rubble", "rubble", {"float": "animation.porcelain.rubble.float"}, ["float"]),
        "severed_claw": ce(f"{NS}:severed_claw", "severed_claw", {"hunt": "animation.porcelain.severed_claw.hunt"}, ["hunt"]),
        "courtier": ce(f"{NS}:courtier", "courtier", {"move": "animation.porcelain.courtier.move",
                                                         "rise": "animation.porcelain.courtier.rise"}, ["move", "rise"]),
    }


# --------------------------------------------------------------------------- particles

TEX_FX = "textures/particle/porcelain_fx"


def _uv(name):
    from pixels import PARTICLE_UV
    u, v, w, h = PARTICLE_UV[name]
    return {"texture_width": 128, "texture_height": 128, "uv": [u, v], "uv_size": [w, h]}


def particle(identifier, comps, material="particles_alpha"):
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": identifier,
                        "basic_render_parameters": {"material": material, "texture": TEX_FX}},
        "components": comps}}


def particles():
    P = {}
    life = "variable.particle_age / variable.particle_lifetime"
    # ground decal telegraph: script sets variable.size (radius), variable.life (seconds) and variable.color
    P["telegraph"] = particle(f"{NS}:telegraph", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.08, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": 25},
        "minecraft:particle_appearance_billboard": {
            "size": [f"variable.size * (0.6 + 0.4 * math.min(1, {life} * 4))",
                     f"variable.size * (0.6 + 0.4 * math.min(1, {life} * 4))"],
            "facing_camera_mode": "emitter_transform_xz", "uv": _uv("seal")},
        "minecraft:particle_appearance_tinting": {"color": [
            "variable.color.r", "variable.color.g", "variable.color.b",
            f"(0.45 + 0.4 * math.abs(math.sin(variable.particle_age * 400))) * (1 - math.max(0, {life} - 0.85) * 6)"]},
    }, material="particles_blend")
    P["crack_decal"] = particle(f"{NS}:crack_decal", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.06, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": "variable.life"},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)"},
        "minecraft:particle_appearance_billboard": {"size": ["variable.size", "variable.size"],
                                                    "facing_camera_mode": "emitter_transform_xz", "uv": _uv("crack")},
        "minecraft:particle_appearance_tinting": {"color": [1, 0.9, 0.55, f"1 - {life} * {life}"]},
        "minecraft:particle_appearance_lighting": {},
    }, material="particles_blend")
    # flat expanding shock ring (kowtow judgement, dive impact)
    P["ring_wave"] = particle(f"{NS}:ring_wave", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"offset": [0, 0.3, 0]},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.9},
        "minecraft:particle_appearance_billboard": {"size": [f"0.5 + variable.size * {life}", f"0.5 + variable.size * {life}"],
                                                    "facing_camera_mode": "emitter_transform_xz", "uv": _uv("ring")},
        "minecraft:particle_appearance_tinting": {"color": [1, 0.85, 0.4, f"1 - {life}"]},
    }, material="particles_add")

    def burst(name, uvname, count, speed, size, lifetime, color, gravity=0.0, drag=2.0, material="particles_alpha",
              radius=0.3, rise=0.0, spin=True):
        comps = {
            "minecraft:emitter_rate_instant": {"num_particles": count},
            "minecraft:emitter_lifetime_once": {"active_time": 0.05},
            "minecraft:emitter_shape_sphere": {"radius": radius, "surface_only": False, "direction": "outwards"},
            "minecraft:particle_initial_speed": speed,
            "minecraft:particle_lifetime_expression": {
                "max_lifetime": f"{lifetime[0]} + variable.particle_random_1 * {round(lifetime[1] - lifetime[0], 3)}"},
            "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, rise - gravity, 0], "linear_drag_coefficient": drag},
            "minecraft:particle_appearance_billboard": {
                "size": [f"{size} * (1 - {life} * 0.6)", f"{size} * (1 - {life} * 0.6)"],
                "facing_camera_mode": "rotate_xyz", "uv": _uv(uvname)},
            "minecraft:particle_appearance_tinting": {"color": [color[0], color[1], color[2], f"1 - {life} * {life}"]},
        }
        if spin:
            comps["minecraft:particle_initial_spin"] = {"rotation": "math.random(0, 360)", "rotation_rate": "math.random(-400, 400)"}
        if gravity:
            comps["minecraft:particle_motion_collision"] = {"coefficient_of_restitution": 0.25, "collision_drag": 3,
                                                            "collision_radius": 0.05}
        P[name] = particle(f"{NS}:{name}", comps, material)

    gold = (1.0, 0.82, 0.32)
    burst("gold_burst", "spark", 18, 4.0, 0.22, (0.4, 0.8), gold, drag=3.5, material="particles_add")
    burst("chip_burst", "chip", 14, 5.0, 0.28, (0.8, 1.6), (1, 1, 1), gravity=14.0, drag=0.6)
    burst("flake_burst", "flake", 10, 3.0, 0.2, (0.9, 1.6), (1, 1, 1), gravity=3.0, drag=1.5)
    burst("dust_puff", "dot", 10, 1.6, 0.6, (0.6, 1.1), (0.93, 0.9, 0.82), drag=2.5, rise=0.6)
    burst("petals", "petal", 16, 2.0, 0.22, (2.0, 3.5), (1, 1, 1), gravity=0.6, drag=1.0, radius=2.0)
    # single motes (lines / trails / beams are drawn from scripts)
    P["gold_mote"] = particle(f"{NS}:gold_mote", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {"direction": ["math.random(-1, 1)", "math.random(0, 1)", "math.random(-1, 1)"]},
        "minecraft:particle_initial_speed": 0.2,
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.5 + variable.particle_random_1 * 0.5"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 0.4, 0], "linear_drag_coefficient": 1.5},
        "minecraft:particle_appearance_billboard": {"size": [f"0.16 * (1 - {life} * 0.5)", f"0.16 * (1 - {life} * 0.5)"],
                                                    "facing_camera_mode": "lookat_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.84, 0.36, f"1 - {life}"]},
    }, material="particles_add")
    P["red_mote"] = particle(f"{NS}:red_mote", {
        "minecraft:emitter_rate_instant": {"num_particles": 1},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_point": {},
        "minecraft:particle_lifetime_expression": {"max_lifetime": 0.35},
        "minecraft:particle_appearance_billboard": {"size": [0.2, 0.2], "facing_camera_mode": "lookat_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.25, 0.18, f"1 - {life}"]},
    }, material="particles_add")
    # gilded breath: molten gold flowing along variable.dir_x/y/z at variable.speed (set from script)
    P["breath"] = particle(f"{NS}:breath", {
        "minecraft:emitter_rate_instant": {"num_particles": 6},
        "minecraft:emitter_lifetime_once": {"active_time": 0.05},
        "minecraft:emitter_shape_sphere": {"radius": 0.4, "direction": [
            "variable.dir_x + math.random(-0.25, 0.25)", "variable.dir_y + math.random(-0.1, 0.1)",
            "variable.dir_z + math.random(-0.25, 0.25)"]},
        "minecraft:particle_initial_speed": "variable.speed",
        "minecraft:particle_lifetime_expression": {"max_lifetime": "0.55 + variable.particle_random_1 * 0.3"},
        "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, -6, 0], "linear_drag_coefficient": 1.2},
        "minecraft:particle_initial_spin": {"rotation": "math.random(0, 360)", "rotation_rate": 200},
        "minecraft:particle_appearance_billboard": {"size": [f"0.25 + {life} * 0.55", f"0.25 + {life} * 0.55"],
                                                    "facing_camera_mode": "rotate_xyz", "uv": _uv("dot")},
        "minecraft:particle_appearance_tinting": {"color": {"gradient": {"0.0": "#FFFFF6D6", "0.4": "#FFFFC64F", "1.0": "#00D99A26"},
                                                            "interpolant": life}},
    }, material="particles_add")
    P["gate_swirl"] = particle(f"{NS}:gate_swirl", {
        "minecraft:emitter_rate_steady": {"spawn_rate": 30, "max_particles": 60},
        "minecraft:emitter_lifetime_once": {"active_time": 1.0},
        "minecraft:emitter_shape_disc": {"radius": 3.2, "plane_normal": "z", "surface_only": True, "direction": "inwards"},
        "minecraft:particle_initial_speed": 1.5,
        "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
        "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 0.5},
        "minecraft:particle_appearance_billboard": {"size": [0.18, 0.18], "facing_camera_mode": "lookat_xyz", "uv": _uv("spark")},
        "minecraft:particle_appearance_tinting": {"color": [1.0, 0.9, 0.55, f"1 - {life}"]},
    }, material="particles_add")
    return P


# --------------------------------------------------------------------------- fogs

def fogs():
    def fog(identifier, color, start, end, haze):
        return {"format_version": "1.16.100", "minecraft:fog_settings": {
            "description": {"identifier": identifier},
            "distance": {
                "air": {"fog_start": start, "fog_end": end, "fog_color": color, "render_distance_type": "fixed"},
                "weather": {"fog_start": start * 0.7, "fog_end": end * 0.8, "fog_color": color, "render_distance_type": "fixed"},
            },
            "volumetric": {
                "density": {"air": {"max_density": haze, "zero_density_height": 140.0, "max_density_height": 60.0, "uniform": False}},
                "media_coefficients": {"air": {"scattering": [0.04, 0.035, 0.02], "absorption": [0.0, 0.003, 0.008]}},
            },
        }}
    return {
        "mandate": fog(f"{NS}:mandate_fog", "#F3E6C8", 34.0, 110.0, 0.35),
        "fractured": fog(f"{NS}:mandate_fog_fractured", "#E3B25A", 24.0, 90.0, 0.5),
        "mended": fog(f"{NS}:mandate_fog_mended", "#FFF4DA", 48.0, 140.0, 0.2),
    }


# --------------------------------------------------------------------------- sounds

SOUND_EVENTS = {
    # event id: (file, category, volume, pitch range, max_distance)
    f"{NS}.chime": ("chime", "hostile", 1.0, None, 48),
    f"{NS}.chime_low": ("chime_low", "hostile", 1.0, None, 64),
    f"{NS}.crack": ("crack", "hostile", 1.0, None, 48),
    f"{NS}.shatter": ("shatter", "hostile", 1.0, None, 64),
    f"{NS}.gong": ("gong", "hostile", 1.0, None, 96),
    f"{NS}.stamp": ("stamp", "hostile", 1.0, None, 64),
    f"{NS}.roar": ("roar", "hostile", 1.0, None, 128),
    f"{NS}.hum": ("hum", "hostile", 0.9, None, 64),
    f"{NS}.music.mandate": ("music_mandate", "music", 0.75, None, None),
}


def sound_definitions():
    defs = {}
    for ev, (f, cat, vol, _pitch, maxd) in SOUND_EVENTS.items():
        d = {"category": cat, "sounds": [{"name": f"sounds/porcelain/{f}", "volume": vol,
                                          "stream": cat == "music"}]}
        if maxd:
            d["max_distance"] = maxd
            d["min_distance"] = 4.0
        defs[ev] = d
    return {"format_version": "1.20.20", "sound_definitions": defs}
