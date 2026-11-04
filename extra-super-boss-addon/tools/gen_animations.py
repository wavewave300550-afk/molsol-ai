#!/usr/bin/env python3
"""
Animations, animation controllers and the boss's client entity.

  RP animations/da_vinci.animation.json            animation.esb.da_vinci.*
  RP animations/props.animation.json               gear spin, sigil grow
  RP animation_controllers/da_vinci.animation_controllers.json
  RP entity/da_vinci.entity.json

Authoring model: an action is a timeline of POSES.  A pose maps bone -> rotation offset (degrees,
added to the rest pose) and optionally 'pos:<bone>' -> position offset (model units).  Every bone
named anywhere in the timeline gets a catmull-rom key at every pose time (0 when the pose does not
mention it), so all bones move together and return to rest cleanly.

Rotation convention (Bedrock): +x pitches a hanging limb BACKWARD (x -90 = arm straight forward),
+z swings a hanging limb toward -X (so his LEFT arm (+X) raises sideways with NEGATIVE z), +y turns
a part toward his left.  Lengths and hit moments come from tools/spec.py.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
P = "animation.esb.da_vinci."
RENDER_SCALE = json.load(open(os.path.join(ROOT, "balance.json")))["boss"]["render_scale"]

FINGERS = ["finger_l_1", "finger_l_2", "finger_l_3", "finger_l_4"]
WINGS_L = ["wing_l", "wing_l_mid", "wing_l_tip"]


def r(v, n=3):
    if isinstance(v, str):
        return v
    v = round(float(v), n)
    return int(v) if v == int(v) else v


def mirror_rot(rot):
    """Rotation of the mirrored (right side) bone for a left side rotation."""
    return [rot[0], -rot[1], -rot[2]]


def fist(curl=80, thumb=30):
    d = {f: (0, 0, curl) for f in FINGERS}
    d["thumb_l"] = (-thumb, 0, 20)
    return d


def spread(amount=1.0):
    return {"finger_l_1": (-9 * amount, 0, -4 * amount), "finger_l_2": (-3 * amount, 0, -2 * amount),
            "finger_l_3": (3 * amount, 0, -2 * amount), "finger_l_4": (10 * amount, 0, -5 * amount),
            "thumb_l": (-22 * amount, 0, -8 * amount)}


def merge(*poses):
    """Later poses override earlier ones bone by bone."""
    out = {}
    for p in poses:
        out.update(p)
    return out


def offset(pose, extra):
    """Add rotation offsets to a pose (used for small breathing motions on top of a held pose)."""
    out = dict(pose)
    for k, v in extra.items():
        a = out.get(k, (0, 0, 0))
        out[k] = tuple(a[i] + v[i] for i in range(3))
    return out


def wings(rot_l, mid_l=(0, 0, 0), tip_l=(0, 0, 0)):
    return {"wing_l": rot_l, "wing_l_mid": mid_l, "wing_l_tip": tip_l,
            "wing_r": tuple(mirror_rot(rot_l)), "wing_r_mid": tuple(mirror_rot(mid_l)), "wing_r_tip": tuple(mirror_rot(tip_l))}


def timeline(keys, smooth=True):
    """keys: [(t, pose)] -> bones dict with catmull-rom (or linear) keyframes."""
    names = []
    for _, pose in keys:
        for k in pose:
            if k not in names:
                names.append(k)
    bones = {}
    for k in names:
        if k.startswith("pos:"):
            bone, ch, zero = k[4:], "position", (0, 0, 0)
        elif k.startswith("scale:"):
            bone, ch, zero = k[6:], "scale", (1, 1, 1)
        else:
            bone, ch, zero = k, "rotation", (0, 0, 0)
        frames = {}
        for t, pose in keys:
            v = pose.get(k, zero)
            key = [r(x) for x in v]
            frames[f"{r(t, 4)}"] = {"post": key, "lerp_mode": "catmullrom"} if smooth else key
        bones.setdefault(bone, {})[ch] = frames
    return bones


ANIMS = {}


def add(name, length, bones, loop=False, hold=False, particles=None, time_update=None, blend=None):
    a = {"animation_length": length, "bones": bones}
    if loop:
        a["loop"] = True
    elif hold:
        a["loop"] = "hold_on_last_frame"
    if particles:
        a["particle_effects"] = {f"{r(t, 4)}": v for t, v in particles}
    if time_update:
        a["anim_time_update"] = time_update
    if blend:
        a["blend_weight"] = blend
    ANIMS[P + name] = a


M = {k: v["moments"] for k, v in spec.ACTIONS.items()}
L = {k: v["length"] for k, v in spec.ACTIONS.items()}

# ------------------------------------------------------------------------------ shared poses
REST = {}
STANCE = {"arm_r": (0, 0, 5), "arm_l": (0, 0, -6), "gauntlet_l": (-10, 0, 0), "forearm_r": (-8, 0, 0)}

# the reference-art pose: gauntlet thrust toward the target, compass held low, wide stance
AIM = merge({
    "torso": (0, 22, 0), "head": (-4, -18, 0), "body": (0, 6, 0),
    "arm_l": (-84, -30, 0), "gauntlet_l": (-6, 0, 0), "ghand_l": (-38, 0, 0),
    "arm_r": (14, 0, 22), "forearm_r": (-28, 0, 0), "hand_r": (0, 0, -10), "compass": (-28, 0, 0),
    "leg_l": (-16, 0, -6), "shin_l": (8, 0, 0), "leg_r": (12, 0, 7), "shin_r": (10, 0, 0), "foot_r": (-8, 0, 0),
    "pos:body": (0, -0.6, 0), "cape_tail_l": (8, 0, 0), "cape_tail_r": (10, 0, 0), "mantle_l": (0, 0, -6),
}, spread(1.0))

KNEEL = {  # down on the right knee
    "pos:root": (0, -7.5, 0),
    "leg_l": (-85, 0, -6), "shin_l": (88, 0, 0), "foot_l": (-4, 0, 0),
    "leg_r": (8, 0, 4), "shin_r": (84, 0, 0), "foot_r": (-40, 0, 0),
    "torso": (18, 0, 0), "head": (24, 0, 0),
    "cape_tail_l": (-6, 0, 0), "cape_tail_r": (-6, 0, 0), "coat_front_l": (-70, 0, 0), "coat_front_r": (-20, 0, 0),
    "coat_back": (10, 0, 0),
}

AIRBORNE = merge({
    "torso": (12, 0, 0), "head": (-10, 0, 0),
    "leg_l": (-20, 0, -5), "shin_l": (30, 0, 0), "leg_r": (10, 0, 5), "shin_r": (45, 0, 0),
    "arm_l": (-60, -10, -20), "gauntlet_l": (-20, 0, 0), "arm_r": (10, 0, 45), "forearm_r": (-30, 0, 0),
    "cape_tail_l": (35, 0, 0), "cape_tail_r": (38, 0, 0), "coat_back": (25, 0, 0), "coat_front_l": (-15, 0, 0),
    "coat_front_r": (10, 0, 0), "hair_tail": (25, 0, 0),
}, fist(70))


# ------------------------------------------------------------------------------ base layers

def base_layers():
    # idle: breathing, cloth and hair sway, clockwork twitches (always on, small)
    t = "q.anim_time"
    bones = {
        "torso": {"rotation": [f"math.sin({t} * 112.5) * 1.2", 0, 0], "position": [0, f"math.sin({t} * 112.5) * 0.12", 0]},
        "head": {"rotation": [f"math.sin({t} * 112.5 - 40) * -1.5", f"math.sin({t} * 56.25) * 3", 0]},
        "arm_r": {"rotation": [f"math.sin({t} * 112.5 + 20) * 2", 0, f"5 + math.sin({t} * 112.5) * 1.5"]},
        "arm_l": {"rotation": [f"math.sin({t} * 112.5 + 60) * 1.5", 0, f"-6 - math.sin({t} * 112.5) * 1.5"]},
        "gauntlet_l": {"rotation": [-10, 0, 0]},
        "forearm_r": {"rotation": [-8, 0, 0]},
        "finger_l_2": {"rotation": [0, 0, f"math.max(0, math.sin({t} * 225 - 90)) * 14"]},
        "finger_l_3": {"rotation": [0, 0, f"math.max(0, math.sin({t} * 225 - 140)) * 12"]},
        "cape_tail_l": {"rotation": [f"3 + math.sin({t} * 112.5 + 30) * 2.5", 0, 0]},
        "cape_tail_r": {"rotation": [f"3 + math.sin({t} * 112.5 + 80) * 2.5", 0, 0]},
        "cape": {"rotation": [f"1 + math.sin({t} * 112.5) * 0.8", 0, 0]},
        "hair_tail": {"rotation": [f"math.sin({t} * 112.5 + 50) * 3", 0, f"math.sin({t} * 56.25) * 2"]},
        "coat_back": {"rotation": [f"2 + math.sin({t} * 112.5 + 20) * 1.5", 0, 0]},
        "mantle_l": {"rotation": [0, 0, f"math.sin({t} * 112.5) * -1"]},
        "mantle_r": {"rotation": [0, 0, f"math.sin({t} * 112.5) * 1"]},
    }
    add("idle", 3.2, bones, loop=True)

    # walk: driven by distance moved, so the stride always matches the real speed
    ph = "q.modified_distance_moved * 24.0"
    amp = "math.min(q.modified_move_speed, 1.0)"
    bones = {
        "leg_l": {"rotation": [f"math.cos({ph}) * 32 * {amp}", 0, 0]},
        "leg_r": {"rotation": [f"math.cos({ph}) * -32 * {amp}", 0, 0]},
        "shin_l": {"rotation": [f"math.max(0, math.sin({ph})) * 38 * {amp}", 0, 0]},
        "shin_r": {"rotation": [f"math.max(0, -math.sin({ph})) * 38 * {amp}", 0, 0]},
        "foot_l": {"rotation": [f"math.cos({ph} + 60) * -10 * {amp}", 0, 0]},
        "foot_r": {"rotation": [f"math.cos({ph} + 60) * 10 * {amp}", 0, 0]},
        "arm_r": {"rotation": [f"math.cos({ph}) * 24 * {amp}", 0, 0]},
        "arm_l": {"rotation": [f"math.cos({ph}) * -12 * {amp}", 0, 0]},
        "torso": {"rotation": [f"4 * {amp}", f"math.cos({ph}) * 5 * {amp}", 0]},
        "body": {"position": [0, f"(math.abs(math.cos({ph})) * 0.8 - 0.6) * {amp}", 0]},
        "coat_front_l": {"rotation": [f"math.cos({ph}) * 24 * {amp}", 0, 0]},
        "coat_front_r": {"rotation": [f"math.cos({ph}) * -24 * {amp}", 0, 0]},
        "robe_side_l": {"rotation": [f"8 * {amp}", 0, 0]},
        "robe_side_r": {"rotation": [f"8 * {amp}", 0, 0]},
        "coat_back": {"rotation": [f"10 * {amp}", 0, 0]},
        "cape_tail_l": {"rotation": [f"(14 + math.sin(q.life_time * 420) * 4) * {amp}", 0, 0]},
        "cape_tail_r": {"rotation": [f"(14 + math.sin(q.life_time * 420 + 90) * 4) * {amp}", 0, 0]},
        "hair_tail": {"rotation": [f"10 * {amp}", 0, 0]},
        "tube": {"rotation": [f"math.cos({ph}) * 8 * {amp}", 0, 0]},
    }
    add("walk", 1.0, bones, loop=True)

    # look at the target (vanilla humanoid queries)
    add("look", 1.0, {"head": {"rotation": ["math.clamp(q.target_x_rotation, -35, 35)",
                                            "math.clamp(q.target_y_rotation, -55, 55)", 0]}}, loop=True)


# ------------------------------------------------------------------------------ wings layers (phase 2)

WING_FOLD = wings((0, -85, 30), (0, -172, 0), (0, -8, 0))
WING_SPREAD = wings((0, -8, -10), (0, -6, 0), (0, -4, 0))
WING_UP = wings((0, -10, -48), (0, -8, -14), (0, -4, -10))
WING_DOWN = wings((0, 6, 22), (0, 4, 18), (0, 2, 14))
WING_SWEPT = wings((0, -40, -18), (0, -40, 0), (0, -30, 0))


def wing_layers():
    hidden = {"wing_l": {"scale": 0}, "wing_r": {"scale": 0}}
    add("wings_hidden", 1.0, hidden, loop=True)
    fold = timeline([(0, WING_FOLD), (1.2, offset(WING_FOLD, wings((0, 0, -3)))), (2.4, WING_FOLD)])
    add("wings_folded", 2.4, fold, loop=True)
    flap = timeline([(0, WING_UP), (0.25, WING_DOWN), (0.5, WING_UP)])
    add("wings_flap", 0.5, flap, loop=True)
    add("wings_swept", 0.4, timeline([(0, WING_UP), (0.2, WING_SWEPT), (0.4, WING_SWEPT)]), hold=True)
    # unfold, synced with the transform action
    tl = L["transform"]
    zero = {"scale:wing_l": (0, 0, 0), "scale:wing_r": (0, 0, 0)}
    one = {"scale:wing_l": (1, 1, 1), "scale:wing_r": (1, 1, 1)}
    keys = [(0, merge(WING_FOLD, zero)), (1.4, merge(WING_FOLD, zero)), (1.9, merge(WING_FOLD, one)),
            (2.2, merge(WING_SPREAD, one)), (2.5, merge(WING_UP, one)), (2.75, merge(WING_DOWN, one)),
            (3.0, merge(WING_UP, one)), (tl, merge(WING_FOLD, one))]
    add("wings_unfold", tl, timeline(keys), hold=True)


# ------------------------------------------------------------------------------ actions

def actions():
    # ---- compass slash (vanilla delayed attack). Speeds up in phase 2 like the attack itself.
    wind = merge(STANCE, {"torso": (0, -26, 0), "head": (0, 18, 0), "arm_r": (-150, 10, 40), "forearm_r": (-30, 0, 0),
                          "compass": (-60, 0, 0), "leg_r": (8, 0, 6), "leg_l": (-10, 0, -4), "pos:body": (0, -0.5, 0)})
    strike = merge(STANCE, {"torso": (8, 28, 0), "head": (0, -16, 0), "arm_r": (-38, 48, -12), "forearm_r": (-6, 0, 0),
                            "compass": (-20, 0, 0), "leg_r": (16, 0, 6), "leg_l": (-18, 0, -4), "shin_r": (10, 0, 0),
                            "pos:body": (0, -1.0, 0), "cape_tail_r": (12, 0, 0)})
    follow = merge(strike, {"arm_r": (-20, 60, -20), "torso": (10, 34, 0)})
    keys = [(0, STANCE), (0.27, wind), (0.45, strike), (0.58, follow), (0.9, STANCE)]
    add("slash", spec.SLASH["length"], timeline(keys),
        time_update="q.anim_time + q.delta_time * (q.property('esb:phase') == 2 ? 1.25 : 1.0)",
        particles=[(0.42, {"effect": "spark", "locator": "loc_compass_tip"})])

    # ---- gear volley: the reference pose, three recoiling shots
    m = M["gear_volley"]
    ready = merge(STANCE, {"torso": (0, 32, 0), "head": (0, -24, 0), "arm_l": (-70, -46, -24), "gauntlet_l": (-30, 0, 0),
                           "pos:body": (0, -0.4, 0)}, fist(60))
    kick = merge(AIM, {"arm_l": (-100, -30, 0), "torso": (-4, 26, 0), "ghand_l": (-55, 0, 0), "pos:body": (0, -0.4, 0.5)})
    keys = [(0, STANCE), (0.45, ready), (0.8, AIM)]
    for s in ("shot1", "shot2", "shot3"):
        keys += [(m[s] - 0.04, AIM), (m[s] + 0.06, kick), (m[s] + 0.25, AIM)]
    keys += [(2.35, AIM), (L["gear_volley"], STANCE)]
    add("gear_volley", L["gear_volley"], timeline(keys),
        particles=[(m[s], {"effect": "steam", "locator": "loc_core"}) for s in ("shot1", "shot2", "shot3")])

    # ---- gauntlet quake: raise the gauntlet overhead, slam it into the ground
    m = M["quake"]
    up = merge({"torso": (-14, 16, 0), "head": (-12, -8, 0), "arm_l": (-168, 0, -12), "gauntlet_l": (-35, 0, 0),
                "arm_r": (0, 0, 42), "forearm_r": (-20, 0, 0), "leg_l": (-14, 0, -6), "leg_r": (10, 0, 6),
                "pos:body": (0, 0.4, 0), "cape_tail_l": (6, 0, 0), "cape_tail_r": (6, 0, 0)}, fist(85))
    fall = merge({"torso": (24, 10, 0), "head": (6, -4, 0), "arm_l": (-70, 0, -8), "gauntlet_l": (-15, 0, 0),
                  "arm_r": (-10, 0, 50), "leg_l": (-36, 0, -8), "shin_l": (40, 0, 0), "leg_r": (14, 0, 8), "shin_r": (40, 0, 0),
                  "pos:body": (0, -1.8, 0)}, fist(85))
    hit = merge({"torso": (38, 6, 0), "head": (-10, 0, 0), "arm_l": (-34, 0, -6), "gauntlet_l": (-10, 0, 0),
                 "arm_r": (-24, 0, 56), "forearm_r": (-20, 0, 0), "leg_l": (-58, 0, -10), "shin_l": (72, 0, 0),
                 "foot_l": (-12, 0, 0), "leg_r": (18, 0, 10), "shin_r": (70, 0, 0), "foot_r": (-20, 0, 0),
                 "pos:root": (0, -3.2, 0), "cape_tail_l": (26, 0, 0), "cape_tail_r": (30, 0, 0), "hair_tail": (20, 0, 0),
                 "coat_front_l": (-40, 0, 0), "coat_front_r": (-10, 0, 0)}, fist(85))
    keys = [(0, STANCE), (0.62, up), (0.86, fall), (m["impact"], hit), (1.3, hit), (L["quake"], STANCE)]
    add("quake", L["quake"], timeline(keys), particles=[(m["impact"], {"effect": "spark", "locator": "loc_palm"})])

    # ---- vitruvian judgement: rises into the pose of the drawing, then brings it down
    m = M["vitruvian"]
    vit = merge({"arm_l": (0, 0, -88), "arm_r": (0, 0, 88), "gauntlet_l": (0, 0, 0), "forearm_r": (0, 0, 0),
                 "leg_l": (0, 0, -15), "leg_r": (0, 0, 15), "head": (-8, 0, 0), "torso": (-4, 0, 0),
                 "pos:root": (0, 3.0, 0), "cape_tail_l": (14, 0, -8), "cape_tail_r": (14, 0, 8), "hair_tail": (12, 0, 0),
                 "coat_front_l": (0, 0, -14), "coat_front_r": (0, 0, 14), "robe_side_l": (0, 0, -10), "robe_side_r": (0, 0, 10),
                 "compass": (60, 0, 0)}, spread(1.3))
    vit_hi = merge(vit, {"pos:root": (0, 3.8, 0), "head": (-14, 0, 0)})
    gather = merge(vit, {"arm_l": (0, 0, -158), "arm_r": (0, 0, 158), "head": (-24, 0, 0), "pos:root": (0, 4.4, 0),
                         "torso": (-10, 0, 0)})
    slam = merge({"arm_l": (-42, 0, -26), "arm_r": (-42, 0, 26), "torso": (30, 0, 0), "head": (12, 0, 0),
                  "leg_l": (-40, 0, -10), "shin_l": (55, 0, 0), "leg_r": (20, 0, 10), "shin_r": (55, 0, 0),
                  "pos:root": (0, -2.4, 0), "cape_tail_l": (30, 0, 0), "cape_tail_r": (30, 0, 0)}, fist(60))
    keys = [(0, STANCE), (m["sigil"], merge(STANCE, {"head": (-20, 0, 0), "arm_l": (0, 0, -30), "arm_r": (0, 0, 30)})),
            (0.75, vit), (1.3, vit_hi), (1.85, vit), (2.35, vit_hi), (2.58, gather), (m["detonate"], slam),
            (3.05, slam), (L["vitruvian"], STANCE)]
    add("vitruvian", L["vitruvian"], timeline(keys),
        particles=[(0.75, {"effect": "spark", "locator": "loc_palm"}), (m["detonate"], {"effect": "spark", "locator": "loc_chest"})])

    # ---- transform (phase 2): kneels clutching the gauntlet, then rises as the wings unfold
    m = M["transform"]
    clutch = merge(KNEEL, {"arm_l": (-70, 40, 0), "gauntlet_l": (-60, 0, 0), "arm_r": (-50, -30, 10), "forearm_r": (-50, 0, 0),
                           "head": (34, 0, 0)}, fist(80))
    rise = merge({"torso": (-6, 0, 0), "head": (-6, 0, 0), "arm_l": (-30, 0, -40), "arm_r": (-30, 0, 40)}, spread(0.5))
    burst = merge({"torso": (-16, 0, 0), "head": (-26, 0, 0), "arm_l": (0, 0, -128), "arm_r": (0, 0, 128),
                   "pos:root": (0, 1.2, 0), "leg_l": (0, 0, -10), "leg_r": (0, 0, 10), "cape_tail_l": (30, 0, -10),
                   "cape_tail_r": (30, 0, 10), "hair_tail": (30, 0, 0)}, spread(1.3))
    keys = [(0, STANCE), (0.45, clutch), (1.2, merge(clutch, {"torso": (24, 0, 0), "head": (40, 0, 0)})), (1.75, rise),
            (m["burst"], burst), (2.9, burst), (L["transform"], STANCE)]
    add("transform", L["transform"], timeline(keys),
        particles=[(m["burst"], {"effect": "pages", "locator": "loc_chest"}), (m["burst"], {"effect": "spark", "locator": "loc_core"})])

    # ---- ornithopter dive: rise, hover, strike
    m = M["dive_rise"]
    crouch = merge({"torso": (24, 0, 0), "arm_l": (30, 0, -20), "arm_r": (30, 0, 20), "leg_l": (-50, 0, -6),
                    "shin_l": (70, 0, 0), "leg_r": (-40, 0, 6), "shin_r": (70, 0, 0), "foot_l": (-15, 0, 0),
                    "foot_r": (-15, 0, 0), "pos:root": (0, -3.6, 0)}, fist(60))
    leap = merge({"torso": (-10, 0, 0), "head": (-14, 0, 0), "arm_l": (-150, 0, -20), "arm_r": (-30, 0, 50),
                  "leg_l": (6, 0, -4), "leg_r": (14, 0, 4), "shin_r": (20, 0, 0), "cape_tail_l": (30, 0, 0),
                  "cape_tail_r": (30, 0, 0)}, fist(60))
    add("dive_rise", L["dive_rise"], timeline([(0, STANCE), (0.3, crouch), (m["leap"], leap), (L["dive_rise"], AIRBORNE)]))
    bob = merge(AIRBORNE, {"pos:root": (0, 0.8, 0), "leg_l": (-26, 0, -5), "leg_r": (16, 0, 5)})
    add("dive_hover", L["dive_hover"], timeline([(0, AIRBORNE), (0.5, bob), (1.0, AIRBORNE)]), loop=True)
    m = M["dive_strike"]
    dive = merge({"root": (38, 0, 0), "torso": (10, 0, 0), "head": (-30, 0, 0), "arm_l": (-160, 0, -6), "gauntlet_l": (0, 0, 0),
                  "arm_r": (30, 0, 30), "leg_l": (10, 0, -4), "leg_r": (20, 0, 4), "cape_tail_l": (50, 0, 0),
                  "cape_tail_r": (52, 0, 0), "hair_tail": (40, 0, 0)}, fist(85))
    land = merge({"torso": (40, 0, 0), "head": (-12, 0, 0), "arm_l": (-28, 0, -8), "arm_r": (-20, 0, 60),
                  "leg_l": (-62, 0, -10), "shin_l": (78, 0, 0), "foot_l": (-14, 0, 0), "leg_r": (24, 0, 10),
                  "shin_r": (74, 0, 0), "foot_r": (-24, 0, 0), "pos:root": (0, -3.4, 0), "cape_tail_l": (36, 0, 0),
                  "cape_tail_r": (40, 0, 0), "coat_front_l": (-42, 0, 0)}, fist(85))
    add("dive_strike", L["dive_strike"], timeline([(0, AIRBORNE), (0.12, dive), (m["impact"], land), (0.8, land),
                                                   (L["dive_strike"], STANCE)]),
        particles=[(m["impact"], {"effect": "spark", "locator": "loc_palm"})])

    # ---- flourish: twirls the compass, then flexes the clockwork fingers one by one
    twirl = merge(STANCE, {"arm_r": (-62, 18, 6), "forearm_r": (-62, 0, 0), "head": (14, -16, 0)})
    look = merge(STANCE, {"arm_l": (-74, -20, -6), "gauntlet_l": (-76, 0, 0), "ghand_l": (0, 0, 0), "head": (16, 22, 0),
                          "torso": (0, 10, 0)})
    keys = [(0, STANCE), (0.35, merge(twirl, {"compass": (-90, 0, 0)})), (0.7, merge(twirl, {"compass": (-90, 360, 0)})),
            (1.05, merge(twirl, {"compass": (-90, 720, 0)})), (1.3, look),
            (1.55, merge(look, {"finger_l_1": (0, 0, 80)})), (1.75, merge(look, {"finger_l_1": (0, 0, 80), "finger_l_2": (0, 0, 85)})),
            (1.95, merge(look, fist(85))), (2.2, merge(look, spread(1.3))), (L["flourish"], STANCE)]
    add("flourish", L["flourish"], timeline(keys), particles=[(1.95, {"effect": "steam", "locator": "loc_core"})])

    # ---- intro: kneeling in a burst of pages, rises and strikes the reference pose
    m = M["intro"]
    bowed = merge(KNEEL, {"arm_l": (-20, 0, -10), "arm_r": (-10, 0, 10), "head": (40, 0, 0)}, fist(40))
    stand = merge(STANCE, {"head": (-6, -24, 0), "torso": (0, -8, 0)})
    flick = merge(STANCE, {"head": (-8, 16, 0), "hair_tail": (0, 0, -20)})
    keys = [(0, bowed), (m["rise"], bowed), (1.7, merge(KNEEL, {"torso": (4, 0, 0), "head": (-4, 0, 0),
                                                              "pos:root": (0, -4.0, 0)})),
            (2.1, stand), (2.35, flick), (m["flex"], AIM), (3.4, merge(AIM, {"head": (-8, -14, 0)})), (L["intro"], STANCE)]
    add("intro", L["intro"], timeline(keys),
        particles=[(m["burst"], {"effect": "pages", "locator": "loc_chest"}), (m["flex"], {"effect": "steam", "locator": "loc_core"})])

    # ---- death: staggers, falls to one knee, the compass slips, slumps (held)
    m = M["death"]
    hit = merge(STANCE, {"torso": (-18, -10, 0), "head": (-20, 0, 0), "arm_r": (-20, 0, 30), "arm_l": (-10, 0, -30),
                         "pos:body": (0, 0, 1.0), "leg_l": (10, 0, 0), "leg_r": (-12, 0, 0)})
    stumble = merge(STANCE, {"torso": (16, 8, 0), "head": (12, 0, 0), "arm_l": (-30, 0, -14), "leg_l": (-30, 0, 0),
                             "shin_l": (30, 0, 0), "pos:body": (0, -1.2, 0)})
    kneel = merge(KNEEL, {"arm_l": (-40, 0, -14), "gauntlet_l": (-30, 0, 0), "arm_r": (-14, 0, 14), "head": (10, 0, 0)}, fist(30))
    drop = merge(kneel, {"hand_r": (0, 0, 30), "compass": (100, 0, 0), "pos:compass": (0, -5.5, -2)})
    slump = merge(KNEEL, {"torso": (40, 0, 0), "head": (36, 0, 0), "arm_l": (10, 0, -6), "gauntlet_l": (-5, 0, 0),
                          "arm_r": (14, 0, 10), "hand_r": (0, 0, 30), "compass": (100, 0, 0), "pos:compass": (0, -5.5, -2)},
                  fist(20))
    keys = [(0, STANCE), (0.3, hit), (0.65, stumble), (m["kneel"], kneel), (1.5, drop),
            (2.0, merge(drop, {"gauntlet_l": (-50, 0, 0)})), (2.2, drop), (2.45, merge(drop, {"gauntlet_l": (-45, 0, 0)})),
            (2.7, drop), (3.3, slump), (L["death"], slump)]
    add("death", L["death"], timeline(keys), hold=True,
        particles=[(m["pages"], {"effect": "pages", "locator": "loc_chest"}), (2.0, {"effect": "spark", "locator": "loc_core"}),
                   (2.45, {"effect": "spark", "locator": "loc_core"})])


# ------------------------------------------------------------------------------ props

def props():
    out = {
        "animation.esb.brass_gear.spin": {
            "loop": True, "animation_length": 0.25,
            "bones": {"spin": {"rotation": [0, "q.life_time * 1440", 0]}},
            "particle_effects": {"0.0": {"effect": "trail", "locator": "loc_gear"}},
        },
        "animation.esb.vitruvian_sigil.grow": {
            "loop": True, "animation_length": 10.0,
            "bones": {
                "root": {"scale": [
                    "q.property('esb:radius') * 0.5 * math.min(1, 0.25 + q.life_time * 2.5)",
                    1,
                    "q.property('esb:radius') * 0.5 * math.min(1, 0.25 + q.life_time * 2.5)"]},
                "outer": {"rotation": [0, "q.life_time * 24", 0]},
                "inner": {"rotation": [0, "q.life_time * -60", 0],
                          "scale": ["1 + math.sin(q.life_time * 540) * 0.04", 1, "1 + math.sin(q.life_time * 540) * 0.04"]},
            },
        },
    }
    return out


# ------------------------------------------------------------------------------ controllers & client entity

def act(a):
    return f"q.property('esb:action') == '{a}'"


def controllers():
    C = {}
    # action layer: one state per scripted action
    states = {"default": {"transitions": [{a: act(a)} for a in spec.ACTIONS]}}
    for a in spec.ACTIONS:
        states[a] = {
            "animations": [a],
            "transitions": [{"default": f"q.property('esb:action') != '{a}'"}],
            "blend_transition": 0.2 if a != "death" else 0.15,
            "blend_via_shortest_path": True,
        }
    # dive phases flow straight into each other without passing through rest
    states["dive_rise"]["transitions"] = [{"dive_hover": act("dive_hover")}, {"dive_strike": act("dive_strike")},
                                          {"default": "!(" + act("dive_rise") + " || " + act("dive_hover") + " || " + act("dive_strike") + ")"}]
    states["dive_hover"]["transitions"] = [{"dive_strike": act("dive_strike")},
                                           {"default": "!(" + act("dive_hover") + " || " + act("dive_strike") + ")"}]
    C["controller.animation.esb.da_vinci.action"] = {"initial_state": "default", "states": states}

    # vanilla delayed attack -> compass slash
    C["controller.animation.esb.da_vinci.attack"] = {"initial_state": "default", "states": {
        "default": {"transitions": [{"slash": "q.is_delayed_attacking && " + act("none")}]},
        "slash": {"animations": ["slash"], "blend_transition": 0.12,
                  "transitions": [{"default": "q.all_animations_finished || !" + act("none")}]},
    }}

    # wings: hidden in phase 1, unfold on transform, folded / flapping / swept in phase 2
    in_air = act("dive_rise") + " || " + act("dive_hover")
    p2 = "q.property('esb:phase') == 2"
    C["controller.animation.esb.da_vinci.wings"] = {"initial_state": "hidden", "states": {
        "hidden": {"animations": ["wings_hidden"],
                   "transitions": [{"unfold": act("transform")}, {"folded": p2}]},
        "unfold": {"animations": ["wings_unfold"],
                   "transitions": [{"folded": "!" + act("transform") + " && " + p2}, {"hidden": "!" + act("transform") + " && !" + p2}]},
        "folded": {"animations": ["wings_folded"], "blend_transition": 0.3,
                   "transitions": [{"flap": in_air}, {"swept": act("dive_strike")}, {"hidden": "!" + p2}]},
        "flap": {"animations": ["wings_flap"], "blend_transition": 0.2,
                 "transitions": [{"swept": act("dive_strike")}, {"folded": "!(" + in_air + ")"}]},
        "swept": {"animations": ["wings_swept"], "blend_transition": 0.1,
                  "transitions": [{"folded": "!" + act("dive_strike")}]},
    }}
    write(os.path.join(RP, "animation_controllers", "da_vinci.animation_controllers.json"),
          {"format_version": "1.10.0", "animation_controllers": C})
    return C


def client_entity():
    names = {k[len(P):]: k for k in ANIMS}
    names.update({"action_controller": "controller.animation.esb.da_vinci.action",
                  "attack_controller": "controller.animation.esb.da_vinci.attack",
                  "wings_controller": "controller.animation.esb.da_vinci.wings"})
    busy = "q.property('esb:action') == 'death' || q.property('esb:action') == 'transform' || q.property('esb:action') == 'intro'"
    ce = {
        "format_version": "1.10.0",
        "minecraft:client_entity": {"description": {
            "identifier": spec.BOSS_ID,
            "materials": {"default": "entity_emissive"},
            "textures": {"default": "textures/entity/da_vinci"},
            "geometry": {"default": "geometry.esb.da_vinci"},
            "render_controllers": ["controller.render.esb.da_vinci"],
            "spawn_egg": {"base_color": "#7E1F2A", "overlay_color": "#D6AE5E"},
            "enable_attachables": False,
            "scripts": {
                "scale": str(RENDER_SCALE),
                "animate": [
                    "idle",
                    {"walk": "!(q.property('esb:action') == 'dive_rise' || q.property('esb:action') == 'dive_hover' || "
                             "q.property('esb:action') == 'dive_strike')"},
                    {"look": f"!({busy})"},
                    "wings_controller",
                    "attack_controller",
                    "action_controller",
                ],
                "should_update_bones_and_effects_offscreen": "1.0",
            },
            "animations": dict(sorted(names.items())),
            "particle_effects": {"spark": "esb:gold_spark", "steam": "esb:steam_puff", "pages": "esb:page_burst"},
        }},
    }
    write(os.path.join(RP, "entity", "da_vinci.entity.json"), ce)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def main():
    base_layers()
    wing_layers()
    actions()
    write(os.path.join(RP, "animations", "da_vinci.animation.json"), {"format_version": "1.8.0", "animations": ANIMS})
    write(os.path.join(RP, "animations", "props.animation.json"), {"format_version": "1.8.0", "animations": props()})
    controllers()
    client_entity()
    print(f"animations: {len(ANIMS)} boss + 2 props; controllers: 3")


if __name__ == "__main__":
    main()
