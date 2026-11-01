#!/usr/bin/env python3
"""
Red Dragon animations + animation controllers  ->  RP animations/red_dragon.animation.json
                                                    RP animation_controllers/red_dragon.animation_controllers.json

All 18 approved animations, keyframed (catmull-rom) per joint, plus Molang loops.  The
left side is authored and mirrored to the right (+X is the dragon's left; mirroring a
rotation negates y and z).  Rotations are deltas on top of the geometry rest pose, whose
wings are spread: ground animations add the FOLD pose to fold them.

State comes from two server-synced entity properties (set by the script):
    dod:flight  ground | takeoff | fly | glide | landing
    dod:action  none | roar | bite | claw | tail | buffet | fire_charge | fire_breath | look | stretch | death
and dod:aim (int, degrees, + = down) for aiming the fire breath, dod:run (bool).
Every action state leaves as soon as the property changes, so nothing can stay stuck in an
attack pose; actions are one at a time by construction (single enum).
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
P = "animation.dod.red_dragon."

LEFT_TAGS = (("_l_", "_r_"), ("_fl", "_fr"), ("_hl", "_hr"))


def right_name(n):
    for a, b in LEFT_TAGS:
        if a in n:
            return n.replace(a, b)
    return None


def mirror_val(v, kind):
    """Mirror a channel value (list or molang string list) across the YZ plane."""
    if isinstance(v, dict):
        return {k: mirror_val(x, kind) for k, x in v.items()}
    if kind == "scale":
        return v
    x, y, z = v
    neg = lambda e: (-e if isinstance(e, (int, float)) else f"-({e})")  # noqa: E731
    if kind == "rotation":
        return [x, neg(y), neg(z)]
    return [neg(x), y, z]  # position


def r(v):
    if isinstance(v, (int, float)):
        v = round(float(v), 3)
        return int(v) if v == int(v) else v
    return v


def vec(v):
    return [r(x) for x in v]


class Anim:
    def __init__(self, name, length, loop=False):
        self.name = name
        self.length = length
        self.loop = loop
        self.bones = {}
        self.sounds = {}
        self.particles = {}
        self.timeline = {}

    def key(self, bone, kind, frames, mirror=True, mode="catmullrom"):
        """frames: {time: [x,y,z]} or a constant [x,y,z] (numbers or molang strings)."""
        if isinstance(frames, dict):
            ch = {}
            for t, v in sorted(frames.items()):
                if mode == "linear":
                    ch[f"{t:g}"] = vec(v)
                else:
                    ch[f"{t:g}"] = {"post": vec(v), "lerp_mode": "catmullrom"}
        else:
            ch = vec(frames)
        self.bones.setdefault(bone, {})[kind] = ch
        rn = right_name(bone)
        if mirror and rn:
            if isinstance(ch, dict):
                mch = {}
                for t, val in ch.items():
                    if isinstance(val, dict):
                        mch[t] = {"post": mirror_val(val["post"], kind), "lerp_mode": val["lerp_mode"]}
                    else:
                        mch[t] = mirror_val(val, kind)
            else:
                mch = mirror_val(ch, kind)
            self.bones.setdefault(rn, {})[kind] = mch

    def rot(self, bone, frames, **kw):
        self.key(bone, "rotation", frames, **kw)

    def pos(self, bone, frames, **kw):
        self.key(bone, "position", frames, **kw)

    def scale(self, bone, frames, **kw):
        self.key(bone, "scale", frames, **kw)

    def sound(self, t, effect):
        # client entity maps the short key to the sound event (mob.dod.red_dragon.<key>)
        self.sounds[f"{t:g}"] = {"effect": effect.replace("mob.dod.red_dragon.", "")}

    def particle(self, t, effect, locator, pre=None):
        e = {"effect": effect, "locator": locator}
        if pre:
            e["pre_effect_script"] = pre
        self.particles.setdefault(f"{t:g}", [])
        self.particles[f"{t:g}"].append(e)

    def json(self):
        d = {}
        if self.loop:
            d["loop"] = self.loop
        d["animation_length"] = self.length
        d["bones"] = self.bones
        if self.sounds:
            d["sound_effects"] = self.sounds
        if self.particles:
            d["particle_effects"] = {t: (v if len(v) > 1 else v[0]) for t, v in self.particles.items()}
        if self.timeline:
            d["timeline"] = self.timeline
        return d


ANIMS = {}


def new(name, length, loop=False):
    a = Anim(name, length, loop)
    ANIMS[P + name] = a
    return a


# ----------------------------------------------------------------------------- shared poses (left side)

# folded wing, relative to the spread rest pose
FOLD = {
    "wing_l_upper": [-80, -60, 16],
    "wing_l_fore": [0, 155, 0],
    "wing_l_hand": [0, -152, 0],
    "wing_l_f1": [0, -12, 0],
    "wing_l_f2": [0, 14, 0],
    "wing_l_f3": [0, 40, 0],
    "wing_l_f4": [0, 62, 0],
}
FOLD_MEM_SCALE = {"wing_l_mem_a": [1, 1, 0.5], "wing_l_mem_b": [1, 1, 0.06], "wing_l_mem_f1": [1, 1, 0.6],
                  "wing_l_mem_f2": [1, 1, 0.6], "wing_l_mem_f3": [1, 1, 0.6]}
WING_BONES = list(FOLD)
MEM_BONES = list(FOLD_MEM_SCALE)


def lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def scaled(v, k):
    return [x * k for x in v]


def add(*vs):
    return [sum(v[i] for v in vs) for i in range(3)]


ZERO = [0, 0, 0]
ONE = [1, 1, 1]

# tucked legs for flight
TUCK = {
    "leg_fl_upper": [55, 0, 6], "leg_fl_lower": [-75, 0, 0], "foot_fl": [40, 0, 0],
    "leg_hl_thigh": [62, 0, 4], "leg_hl_shin": [-30, 0, 0], "leg_hl_meta": [30, 0, 0], "foot_hl": [35, 0, 0],
}
# neck stretched forward in flight
FLY_NECK = {"neck_1": [30, 0, 0], "neck_2": [6, 0, 0], "neck_3": [-6, 0, 0], "neck_4": [-8, 0, 0], "head": [-12, 0, 0]}
TAIL = [f"tail_{i}" for i in range(1, 9)]
NECK = ["neck_1", "neck_2", "neck_3", "neck_4", "head"]


# ----------------------------------------------------------------------------- 1. idle breathing (+ folded wings)

a = new("idle", 4.0, loop=True)
for b, v in FOLD.items():
    a.rot(b, v)
a.rot("wing_l_upper", [FOLD["wing_l_upper"][0], FOLD["wing_l_upper"][1],
                       f"{FOLD['wing_l_upper'][2]} + math.sin(q.anim_time * 90) * 1.5"])
for b, s in FOLD_MEM_SCALE.items():
    a.scale(b, s)
a.rot("neck_1", ["math.sin(q.anim_time * 90) * 1.5", 0, 0], mirror=False)
a.rot("head", ["-math.sin(q.anim_time * 90 - 40) * 2", "math.sin(q.anim_time * 45) * 3", 0], mirror=False)
a.rot("jaw", ["math.max(0, math.sin(q.anim_time * 90 - 60)) * 2", 0, 0], mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, [f"math.sin(q.anim_time * 90 - {i * 25}) * 1.2",
              f"math.sin(q.anim_time * 45 - {i * 30}) * {2 + i * 0.5}", 0], mirror=False)

# breathing layer: always on (chest rises, flanks expand, nostril smoke now and then)
a = new("breathe", 4.0, loop=True)
a.scale("chest", ["1 + math.sin(q.anim_time * 90) * 0.025", "1 + math.sin(q.anim_time * 90) * 0.035", 1], mirror=False)
a.scale("body", ["1 + math.sin(q.anim_time * 90 - 30) * 0.02", "1 + math.sin(q.anim_time * 90 - 30) * 0.02", 1],
        mirror=False)
a.pos("chest", [0, "math.sin(q.anim_time * 90) * 0.4", 0], mirror=False)
a.particle(2.2, "nostril_smoke", "nostril_l")
a.particle(2.2, "nostril_smoke", "nostril_r")

# ----------------------------------------------------------------------------- 2. look around (idle scan)

a = new("look_around", 3.2)
a.rot("neck_1", {0: ZERO, 0.6: [-6, 16, 0], 1.5: [-8, 18, 0], 2.2: [-6, -18, 0], 2.8: [-4, -14, 0], 3.2: ZERO},
      mirror=False)
a.rot("neck_2", {0: ZERO, 0.6: [-4, 10, 0], 1.5: [-4, 12, 0], 2.2: [-4, -12, 0], 2.8: [-2, -10, 0], 3.2: ZERO},
      mirror=False)
a.rot("neck_3", {0: ZERO, 0.6: [0, 8, 0], 2.2: [0, -8, 0], 3.2: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.6: [6, 14, -8], 1.2: [2, 20, -10], 1.5: [4, 16, -6], 2.2: [6, -16, 8], 2.8: [4, -18, 10],
               3.2: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 1.3: ZERO, 1.45: [6, 0, 0], 1.6: ZERO, 3.2: ZERO}, mirror=False)
a.sound(1.3, "mob.dod.red_dragon.sniff")

# ----------------------------------------------------------------------------- head tracking (look at target)

a = new("look_at_target", 1.0, loop=True)
for b, k in (("neck_2", 0.25), ("neck_3", 0.25), ("neck_4", 0.2), ("head", 0.3)):
    a.rot(b, [f"math.clamp(q.target_x_rotation, -45, 45) * {k}", f"math.clamp(q.target_y_rotation, -70, 70) * {k}",
              0], mirror=False)

# ----------------------------------------------------------------------------- 3. walk  4. run  (distance driven)

PH = "q.modified_distance_moved * 22"
a = new("walk", 1.0, loop=True)
for leg, off in (("fl", 0), ("hl", 180)):
    # diagonal gait: front-left with hind-right, front-right with hind-left
    s = f"math.sin({PH} + {off})"
    c = f"math.cos({PH} + {off})"
    if leg == "fl":
        a.rot("leg_fl_upper", [f"{s} * 22", 0, 0])
        a.rot("leg_fl_lower", [f"-math.max(0, {c}) * 30", 0, 0])
        a.rot("foot_fl", [f"math.max(0, {c}) * 18 - {s} * 8", 0, 0])
    else:
        a.rot("leg_hl_thigh", [f"{s} * 20", 0, 0])
        a.rot("leg_hl_shin", [f"math.max(0, {c}) * 26", 0, 0])
        a.rot("leg_hl_meta", [f"-math.max(0, {c}) * 18", 0, 0])
        a.rot("foot_hl", [f"-{s} * 12 + math.max(0, {c}) * 12", 0, 0])
# the mirrored right legs need the opposite phase: rewrite them explicitly
for leg in ("leg_fr_upper", "leg_fr_lower", "foot_fr", "leg_hr_thigh", "leg_hr_shin", "leg_hr_meta", "foot_hr"):
    left = leg.replace("_fr", "_fl").replace("_hr", "_hl")
    ch = a.bones[left]["rotation"]
    src, dst = (f"{PH} + 0)", f"{PH} + 180)") if "_fr" in leg else (f"{PH} + 180)", f"{PH} + 360)")
    a.bones[leg]["rotation"] = [ch[0].replace(src, dst), ch[1], ch[2]]
a.pos("body", [0, f"-math.abs(math.sin({PH})) * 1.2", 0], mirror=False)
a.rot("body", [0, f"math.sin({PH}) * 2", f"math.sin({PH}) * 1.5"], mirror=False)
a.rot("neck_1", [f"math.abs(math.sin({PH})) * 2", f"-math.sin({PH}) * 3", 0], mirror=False)
a.rot("head", [f"-math.abs(math.sin({PH})) * 2", f"math.sin({PH}) * 3", 0], mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, [0, f"math.sin({PH} - {40 + i * 28}) * {2.5 + i * 0.6}", 0], mirror=False)
a.rot("wing_l_upper", [0, 0, f"math.abs(math.sin({PH})) * 2"])

PR = "q.modified_distance_moved * 17"
a = new("run", 1.0, loop=True)
# bounding gallop: front legs together, hind legs together, half a cycle apart
for leg, off in (("leg_fl_upper", 0), ("leg_hl_thigh", 180)):
    s = f"math.sin({PR} + {off})"
    c = f"math.cos({PR} + {off})"
    if leg == "leg_fl_upper":
        a.rot("leg_fl_upper", [f"{s} * 38 - 6", 0, 0])
        a.rot("leg_fl_lower", [f"-math.max(0, {c}) * 48", 0, 0])
        a.rot("foot_fl", [f"math.max(0, {c}) * 25 - {s} * 10", 0, 0])
    else:
        a.rot("leg_hl_thigh", [f"{s} * 34", 0, 0])
        a.rot("leg_hl_shin", [f"math.max(0, {c}) * 40", 0, 0])
        a.rot("leg_hl_meta", [f"-math.max(0, {c}) * 28", 0, 0])
        a.rot("foot_hl", [f"-{s} * 16 + math.max(0, {c}) * 16", 0, 0])
for leg in ("leg_fr_upper", "leg_fr_lower", "foot_fr", "leg_hr_thigh", "leg_hr_shin", "leg_hr_meta", "foot_hr"):
    left = leg.replace("_fr", "_fl").replace("_hr", "_hl")
    ch = a.bones[left]["rotation"]
    # small lag between left and right feet so the landing reads as weight, not a hop
    a.bones[leg]["rotation"] = [ch[0].replace(f"{PR} + ", f"{PR} - 25 + ") if isinstance(ch[0], str) else ch[0],
                                ch[1], ch[2]]
a.pos("body", [0, f"math.sin({PR} * 2 - 60) * 2.2 - 1", f"-math.sin({PR}) * 1.5"], mirror=False)
a.rot("body", [f"math.sin({PR}) * 5", 0, 0], mirror=False)
a.rot("neck_1", [f"14 + math.sin({PR} + 40) * 4", 0, 0], mirror=False)
a.rot("neck_2", [4, 0, 0], mirror=False)
a.rot("head", [f"-14 - math.sin({PR} + 40) * 4", 0, 0], mirror=False)
a.rot("jaw", [f"4 + math.max(0, math.sin({PR} * 2)) * 4", 0, 0], mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, [f"-3 + math.sin({PR} * 2 - {60 + i * 30}) * 2.5", f"math.sin({PR} - {i * 30}) * {2 + i * 0.5}", 0],
          mirror=False)
a.rot("wing_l_upper", [0, 0, f"-6 + math.sin({PR} * 2) * 4"])

# ----------------------------------------------------------------------------- 5. wing fold / spread (one-shots + idle stretch)


def wing_frames(a, frames, mirror=True):
    """frames: {t: k} where k=1 means folded, 0 spread (relative to the folded base pose
    that ground animations already apply => the delta to spread is -FOLD)."""
    for b in WING_BONES:
        a.rot(b, {t: scaled(FOLD[b], -(1 - k)) for t, k in frames.items()}, mirror=mirror)
    for b, s in FOLD_MEM_SCALE.items():
        # the idle layer already multiplies by s; scale back to 1 when spread
        a.scale(b, {t: [1, 1, 1 + (1 / s[2] - 1) * (1 - k)] for t, k in frames.items()}, mirror=mirror)


a = new("wing_spread", 0.9, loop="hold_on_last_frame")
wing_frames(a, {0: 1, 0.45: 0.35, 0.9: 0})
a.rot("wing_l_upper", {0: scaled(FOLD["wing_l_upper"], -0), 0.45: add(scaled(FOLD["wing_l_upper"], -0.65), [0, 0, -12]),
                       0.9: add(scaled(FOLD["wing_l_upper"], -1), [0, 0, -18])})
a.sound(0.3, "mob.dod.red_dragon.wing_unfold")

a = new("wing_fold", 0.9, loop="hold_on_last_frame")
wing_frames(a, {0: 0, 0.5: 0.6, 0.9: 1})
a.sound(0.1, "mob.dod.red_dragon.wing_unfold")

a = new("wing_stretch", 2.8)
wing_frames(a, {0: 1, 0.6: 0, 2.0: 0, 2.8: 1})
a.rot("wing_l_upper", {0: ZERO, 0.6: add(scaled(FOLD["wing_l_upper"], -1), [0, 0, -30]),
                       1.0: add(scaled(FOLD["wing_l_upper"], -1), [0, 8, 18]),
                       1.4: add(scaled(FOLD["wing_l_upper"], -1), [0, 0, -35]),
                       2.0: add(scaled(FOLD["wing_l_upper"], -1), [0, 0, -10]), 2.8: ZERO})
a.rot("neck_1", {0: ZERO, 0.6: [-14, 0, 0], 1.6: [-16, 0, 0], 2.8: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.6: [-10, 0, 0], 1.0: [-16, 0, 6], 1.6: [-12, 0, -4], 2.8: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 0.8: [20, 0, 0], 1.3: [24, 0, 0], 1.7: ZERO, 2.8: ZERO}, mirror=False)
a.rot("body", {0: ZERO, 0.6: [-5, 0, 0], 2.0: [-4, 0, 0], 2.8: ZERO}, mirror=False)
a.sound(0.25, "mob.dod.red_dragon.wing_unfold")
a.sound(1.0, "mob.dod.red_dragon.flap")
a.sound(0.85, "mob.dod.red_dragon.growl")
a.sound(2.2, "mob.dod.red_dragon.wing_unfold")

# ----------------------------------------------------------------------------- 7. flying (flap cycle)

FLAP = 1.1
a = new("fly", FLAP, loop=True)
up, down = -48, 30
a.rot("wing_l_upper", {0: [0, -4, up], 0.18: [0, 0, up + 10], FLAP * 0.5: [0, 10, down], FLAP * 0.75: [0, 4, 0],
                       FLAP: [0, -4, up]})
a.rot("wing_l_fore", {0: [0, 0, 22], FLAP * 0.25: [0, 0, -2], FLAP * 0.5: [0, 0, -14], FLAP * 0.75: [0, -6, 18],
                      FLAP: [0, 0, 22]})
a.rot("wing_l_hand", {0: [0, 0, 10], FLAP * 0.3: [0, 0, -4], FLAP * 0.55: [0, 0, -10], FLAP * 0.8: [0, 0, 14],
                      FLAP: [0, 0, 10]})
for i, f in enumerate(("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4")):
    a.rot(f, {0: [0, 0, 6 + i * 2], FLAP * 0.55: [0, -3 * i, -6 - i * 2], FLAP: [0, 0, 6 + i * 2]})
a.pos("root", {0: [0, -3, 0], FLAP * 0.55: [0, 3.5, 0], FLAP: [0, -3, 0]}, mirror=False)
a.rot("body", {0: [4, 0, 0], FLAP * 0.55: [-2, 0, 0], FLAP: [4, 0, 0]}, mirror=False)
for b, v in TUCK.items():
    a.rot(b, v)
for b, v in FLY_NECK.items():
    a.rot(b, {0: add(v, [2, 0, 0]), FLAP * 0.55: add(v, [-3, 0, 0]), FLAP: add(v, [2, 0, 0])}, mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, [f"-4 + math.sin(q.anim_time * {360 / FLAP} - {80 + i * 35}) * 3",
              f"math.sin(q.anim_time * {180 / FLAP} - {i * 30}) * {1.5 + i * 0.4}", 0], mirror=False)
a.sound(FLAP * 0.4, "mob.dod.red_dragon.flap")

# ----------------------------------------------------------------------------- 8. glide

a = new("glide", 3.0, loop=True)
a.rot("wing_l_upper", [0, "math.sin(q.anim_time * 120) * 2", "-10 + math.sin(q.anim_time * 120) * 4"])
a.rot("wing_l_fore", [0, 0, "4 + math.sin(q.anim_time * 120 - 30) * 2"])
a.rot("wing_l_hand", [0, 0, "2 + math.sin(q.anim_time * 120 - 60) * 2"])
a.rot("wing_l_f4", [0, "math.sin(q.anim_time * 240) * 2", 0])
a.rot("root", [0, 0, "math.sin(q.anim_time * 120) * 4"], mirror=False)
a.pos("root", [0, "math.sin(q.anim_time * 120 + 90) * 1.5", 0], mirror=False)
for b, v in TUCK.items():
    a.rot(b, v)
for b, v in FLY_NECK.items():
    a.rot(b, v, mirror=False)
a.rot("head", [FLY_NECK["head"][0], "math.sin(q.anim_time * 60) * 6", 0], mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, [-3, f"math.sin(q.anim_time * 120 - {i * 25}) * {1 + i * 0.4}", 0], mirror=False)
a.sound(1.5, "mob.dod.red_dragon.glide")

# ----------------------------------------------------------------------------- 6. takeoff

a = new("takeoff", 1.6, loop="hold_on_last_frame")
fu = FOLD["wing_l_upper"]
# wings: folded -> raised high -> big downstroke at the leap -> two climbing flaps -> top of a fly stroke
a.rot("wing_l_upper", {0: fu, 0.4: [0, -10, -62], 0.62: [0, 14, 34], 0.9: [0, -4, -46], 1.15: [0, 10, 30],
                       1.4: [0, 0, -10], 1.6: [0, -4, up]})
a.rot("wing_l_fore", {0: FOLD["wing_l_fore"], 0.4: [0, 0, 10], 0.62: [0, 0, -14], 0.9: [0, 0, 22], 1.15: [0, 0, -14],
                      1.6: [0, 0, 22]})
a.rot("wing_l_hand", {0: FOLD["wing_l_hand"], 0.4: [0, 0, 6], 0.62: [0, 0, -10], 0.9: [0, 0, 12], 1.6: [0, 0, 10]})
for f in ("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4"):
    a.rot(f, {0: FOLD[f], 0.4: ZERO, 1.6: [0, 0, 8]})
for b, s in FOLD_MEM_SCALE.items():
    a.scale(b, {0: s, 0.4: ONE, 1.6: ONE})
a.pos("root", {0: ZERO, 0.38: [0, -6, 0], 0.55: [0, 4, -2], 0.8: [0, 2, 0], 1.6: [0, -3, 0]}, mirror=False)
a.rot("body", {0: ZERO, 0.38: [6, 0, 0], 0.6: [-12, 0, 0], 1.0: [-4, 0, 0], 1.6: [4, 0, 0]}, mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.38: [14, 0, 0], 0.55: [-20, 0, 0], 0.9: TUCK["leg_fl_upper"], 1.6: TUCK["leg_fl_upper"]})
a.rot("leg_fl_lower", {0: ZERO, 0.38: [-24, 0, 0], 0.55: [10, 0, 0], 0.9: TUCK["leg_fl_lower"], 1.6: TUCK["leg_fl_lower"]})
a.rot("foot_fl", {0: ZERO, 0.38: [10, 0, 0], 0.9: TUCK["foot_fl"], 1.6: TUCK["foot_fl"]})
a.rot("leg_hl_thigh", {0: ZERO, 0.38: [-16, 0, 0], 0.6: [30, 0, 0], 1.0: TUCK["leg_hl_thigh"], 1.6: TUCK["leg_hl_thigh"]})
a.rot("leg_hl_shin", {0: ZERO, 0.38: [22, 0, 0], 0.6: [-40, 0, 0], 1.0: TUCK["leg_hl_shin"], 1.6: TUCK["leg_hl_shin"]})
a.rot("leg_hl_meta", {0: ZERO, 0.38: [-14, 0, 0], 0.6: [30, 0, 0], 1.6: TUCK["leg_hl_meta"]})
a.rot("foot_hl", {0: ZERO, 0.6: [30, 0, 0], 1.6: TUCK["foot_hl"]})
for b in NECK:
    v = FLY_NECK[b]
    a.rot(b, {0: ZERO, 0.38: [10 if b == "neck_1" else 2, 0, 0], 0.62: scaled(v, 0.4), 1.6: add(v, [2, 0, 0])},
          mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, {0: ZERO, 0.38: [6, 0, 0], 0.62: [-8, 0, 0], 1.6: [-4, 0, 0]}, mirror=False)
a.sound(0.0, "mob.dod.red_dragon.wing_unfold")
a.sound(0.55, "mob.dod.red_dragon.takeoff")
a.sound(1.05, "mob.dod.red_dragon.flap")
a.particle(0.55, "dust_ring", "ground")

# ----------------------------------------------------------------------------- 9. landing

a = new("landing", 1.4, loop="hold_on_last_frame")
a.rot("wing_l_upper", {0: [0, 0, -10], 0.25: [0, 26, -40], 0.45: [0, 30, 12], 0.65: [0, 24, -36], 0.85: [0, 12, -6],
                       1.4: fu})
a.rot("wing_l_fore", {0: [0, 0, 4], 0.45: [0, 0, -12], 0.65: [0, 0, 16], 0.85: [0, 0, 0], 1.4: FOLD["wing_l_fore"]})
a.rot("wing_l_hand", {0: ZERO, 0.85: ZERO, 1.4: FOLD["wing_l_hand"]})
for f in ("wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4"):
    a.rot(f, {0: ZERO, 0.85: ZERO, 1.4: FOLD[f]})
for b, s in FOLD_MEM_SCALE.items():
    a.scale(b, {0: ONE, 0.85: ONE, 1.4: s})
a.rot("body", {0: [0, 0, 0], 0.35: [-16, 0, 0], 0.7: [-8, 0, 0], 0.85: [5, 0, 0], 1.4: ZERO}, mirror=False)
a.pos("root", {0: ZERO, 0.7: [0, 1, 0], 0.85: [0, -5, 0], 1.1: [0, -1, 0], 1.4: ZERO}, mirror=False)
a.rot("leg_fl_upper", {0: TUCK["leg_fl_upper"], 0.4: [-28, 0, 0], 0.75: [-10, 0, 0], 0.9: [12, 0, 0], 1.4: ZERO})
a.rot("leg_fl_lower", {0: TUCK["leg_fl_lower"], 0.4: [10, 0, 0], 0.9: [-20, 0, 0], 1.4: ZERO})
a.rot("foot_fl", {0: TUCK["foot_fl"], 0.4: [8, 0, 0], 0.9: [10, 0, 0], 1.4: ZERO})
a.rot("leg_hl_thigh", {0: TUCK["leg_hl_thigh"], 0.45: [-18, 0, 0], 0.9: [-12, 0, 0], 1.4: ZERO})
a.rot("leg_hl_shin", {0: TUCK["leg_hl_shin"], 0.45: [10, 0, 0], 0.9: [20, 0, 0], 1.4: ZERO})
a.rot("leg_hl_meta", {0: TUCK["leg_hl_meta"], 0.45: [0, 0, 0], 0.9: [-12, 0, 0], 1.4: ZERO})
a.rot("foot_hl", {0: TUCK["foot_hl"], 0.45: [10, 0, 0], 0.9: [0, 0, 0], 1.4: ZERO})
for b in NECK:
    v = FLY_NECK[b]
    a.rot(b, {0: v, 0.4: scaled(v, 0.4), 0.85: [6 if b == "neck_1" else 0, 0, 0], 1.4: ZERO}, mirror=False)
for i, t in enumerate(TAIL):
    a.rot(t, {0: [-3, 0, 0], 0.5: [4, 0, 0], 0.85: [8, 0, 0], 1.4: ZERO}, mirror=False)
a.sound(0.25, "mob.dod.red_dragon.flap")
a.sound(0.6, "mob.dod.red_dragon.flap")
a.sound(0.85, "mob.dod.red_dragon.land")
a.particle(0.85, "dust_ring", "ground")
a.sound(1.05, "mob.dod.red_dragon.wing_unfold")

# ----------------------------------------------------------------------------- 10. roar

a = new("roar", 2.3)
wing_frames(a, {0: 1, 0.5: 0.45, 0.8: 0.2, 1.7: 0.2, 2.3: 1})
a.rot("wing_l_upper", {0: ZERO, 0.5: add(scaled(fu, -0.55), [0, 0, -14]),
                       0.8: add(scaled(fu, -0.8), [0, 0, -28]),
                       1.2: add(scaled(fu, -0.8), [0, 4, -22]), 1.7: add(scaled(fu, -0.8), [0, 0, -26]), 2.3: ZERO})
a.rot("neck_1", {0: ZERO, 0.5: [-26, 0, 0], 0.75: [8, 0, 0], 1.6: [6, 0, 0], 2.3: ZERO}, mirror=False)
a.rot("neck_2", {0: ZERO, 0.5: [-10, 0, 0], 0.75: [6, 0, 0], 1.6: [6, 0, 0], 2.3: ZERO}, mirror=False)
a.rot("neck_3", {0: ZERO, 0.5: [-6, 0, 0], 0.75: [4, 0, 0], 2.3: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.5: [-20, 0, 0], 0.75: [-6, 0, 0], 1.6: [-8, 0, 0], 2.3: ZERO}, mirror=False)
# head shake while roaring
a.rot("neck_4", ["0", "(q.anim_time > 0.75 && q.anim_time < 1.7) ? math.sin(q.anim_time * 1500) * 4 : 0", 0],
      mirror=False)
a.rot("jaw", {0: ZERO, 0.45: [12, 0, 0], 0.75: [42, 0, 0], 1.6: [40, 0, 0], 1.9: [8, 0, 0], 2.3: ZERO}, mirror=False)
a.rot("body", {0: ZERO, 0.5: [-6, 0, 0], 0.8: [2, 0, 0], 1.7: [2, 0, 0], 2.3: ZERO}, mirror=False)
a.pos("chest", {0: ZERO, 0.5: [0, 2, 1], 0.8: [0, 0, -1.5], 1.7: [0, 0, -1.5], 2.3: ZERO}, mirror=False)
a.scale("chest", {0: ONE, 0.5: [1.05, 1.07, 1], 0.9: [1.0, 1.0, 1], 2.3: ONE}, mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.5: [-6, 0, -4], 0.8: [6, 0, -6], 1.7: [6, 0, -6], 2.3: ZERO})
for i, t in enumerate(TAIL):
    a.rot(t, {0: ZERO, 0.6: [5, 0, 0], 1.2: [7, 0, 0], 2.3: ZERO}, mirror=False)
a.sound(0.5, "mob.dod.red_dragon.roar")
a.sound(0.55, "mob.dod.red_dragon.roar_layer")
a.particle(0.8, "roar_breath", "mouth")

# ----------------------------------------------------------------------------- 11. bite  (impact 0.45 s)

a = new("bite", 0.95)
a.rot("neck_1", {0: ZERO, 0.3: [-16, 0, 0], 0.45: [26, 0, 0], 0.6: [22, 0, 0], 0.95: ZERO}, mirror=False)
a.rot("neck_2", {0: ZERO, 0.3: [-8, 0, 0], 0.45: [14, 0, 0], 0.6: [12, 0, 0], 0.95: ZERO}, mirror=False)
a.rot("neck_3", {0: ZERO, 0.3: [-8, 0, 0], 0.45: [8, 0, 0], 0.95: ZERO}, mirror=False)
a.rot("neck_4", {0: ZERO, 0.3: [-4, 0, 0], 0.45: [4, 0, 0], 0.95: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.3: [-12, 0, 0], 0.45: [-6, 0, 0], 0.55: [-2, 0, 4], 0.95: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 0.28: [34, 0, 0], 0.42: [30, 0, 0], 0.47: [0, 0, 0], 0.6: [4, 0, 0], 0.95: ZERO}, mirror=False)
a.pos("body", {0: ZERO, 0.3: [0, 0, 2], 0.45: [0, -1, -4], 0.95: ZERO}, mirror=False)
a.rot("body", {0: ZERO, 0.3: [-3, 0, 0], 0.45: [4, 0, 0], 0.95: ZERO}, mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.45: [-8, 0, 0], 0.95: ZERO})
a.sound(0.25, "mob.dod.red_dragon.growl")
a.sound(0.45, "mob.dod.red_dragon.bite")

# ----------------------------------------------------------------------------- 12. claw swipe  (impact 0.55 s, right fore claw)

a = new("claw", 1.15)
a.rot("body", {0: ZERO, 0.4: [-10, 8, -4], 0.55: [-2, -12, 3], 0.75: [0, -8, 2], 1.15: ZERO}, mirror=False)
a.pos("body", {0: ZERO, 0.4: [0, 3, 1], 0.6: [0, 0, -2], 1.15: ZERO}, mirror=False)
a.rot("leg_fr_upper", {0: ZERO, 0.4: [-78, 0, -24], 0.55: [-10, 26, 20], 0.7: [8, 18, 10], 1.15: ZERO}, mirror=False)
a.rot("leg_fr_lower", {0: ZERO, 0.4: [-42, 0, 0], 0.55: [10, 0, 0], 0.7: [-6, 0, 0], 1.15: ZERO}, mirror=False)
a.rot("foot_fr", {0: ZERO, 0.4: [-30, 0, 0], 0.55: [40, 0, 0], 0.75: [10, 0, 0], 1.15: ZERO}, mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.4: [-10, 0, 0], 0.6: [6, 0, 0], 1.15: ZERO}, mirror=False)
a.rot("neck_1", {0: ZERO, 0.4: [-8, 10, 0], 0.55: [8, -8, 0], 1.15: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.4: [-4, 6, 0], 0.55: [4, -6, 0], 1.15: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 0.35: [14, 0, 0], 0.6: [20, 0, 0], 0.9: [4, 0, 0], 1.15: ZERO}, mirror=False)
a.rot("wing_l_upper", {0: ZERO, 0.45: [0, 0, -10], 1.15: ZERO})
a.sound(0.4, "mob.dod.red_dragon.swipe")
a.particle(0.55, "claw_slash", "foot_fr")

# ----------------------------------------------------------------------------- 13. tail smash  (impact 0.72 s, sweeps the rear arc)

a = new("tail_smash", 1.35)
a.rot("body", {0: ZERO, 0.45: [0, -12, 2], 0.72: [0, 14, -2], 1.0: [0, 6, 0], 1.35: ZERO}, mirror=False)
a.rot("pelvis", {0: ZERO, 0.45: [0, -14, 0], 0.72: [0, 18, 0], 1.0: [0, 6, 0], 1.35: ZERO}, mirror=False)
a.rot("chest", {0: ZERO, 0.45: [0, 6, 0], 0.72: [0, -6, 0], 1.35: ZERO}, mirror=False)
a.rot("neck_1", {0: ZERO, 0.45: [-6, 22, 0], 0.72: [-4, 26, 0], 1.0: [0, 10, 0], 1.35: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.45: [0, 16, 0], 0.72: [0, 18, 0], 1.35: ZERO}, mirror=False)
for i, t in enumerate(TAIL):
    wind = 9 + i * 1.5
    sweep = -(18 + i * 2.5)
    # windup lifts the tail (+x), the slam brings it down hard (-x) while sweeping across the rear arc
    a.rot(t, {0: ZERO, 0.45: [4 + i, wind, 0], 0.62: [-2, sweep * 0.6, 0], 0.72: [-(5 + i * 0.5), sweep, 0],
              0.9: [-2, sweep * 0.7, 0], 1.35: ZERO}, mirror=False)
a.rot("leg_hl_thigh", {0: ZERO, 0.45: [-6, 0, 0], 0.72: [6, 0, 0], 1.35: ZERO})
a.sound(0.5, "mob.dod.red_dragon.swipe")
a.sound(0.72, "mob.dod.red_dragon.tail_slam")
a.particle(0.72, "dust_ring", "tail_tip")

# ----------------------------------------------------------------------------- 14. wing buffet  (impact 0.7 s)

a = new("wing_buffet", 1.45)
wing_frames(a, {0: 1, 0.45: 0, 1.05: 0, 1.45: 1})
a.rot("wing_l_upper", {0: ZERO, 0.45: add(scaled(fu, -1), [0, -14, -62]), 0.7: add(scaled(fu, -1), [0, 38, 30]),
                       0.85: add(scaled(fu, -1), [0, 20, -30]), 1.0: add(scaled(fu, -1), [0, 30, 20]), 1.45: ZERO})
a.rot("wing_l_fore", {0: scaled(FOLD["wing_l_fore"], -0.0), 0.45: add(scaled(FOLD["wing_l_fore"], -1), [0, 0, 10]),
                      0.7: add(scaled(FOLD["wing_l_fore"], -1), [0, 10, -10]),
                      1.05: scaled(FOLD["wing_l_fore"], -1), 1.45: ZERO})
a.rot("body", {0: ZERO, 0.45: [-18, 0, 0], 0.7: [-8, 0, 0], 1.05: [-10, 0, 0], 1.45: ZERO}, mirror=False)
a.pos("body", {0: ZERO, 0.45: [0, 6, 2], 0.7: [0, 3, 0], 1.45: ZERO}, mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.45: [-44, 0, -6], 0.8: [-30, 0, -4], 1.3: ZERO})
a.rot("leg_fl_lower", {0: ZERO, 0.45: [-30, 0, 0], 1.3: ZERO})
a.rot("neck_1", {0: ZERO, 0.45: [-18, 0, 0], 0.7: [6, 0, 0], 1.45: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.45: [-6, 0, 0], 0.7: [10, 0, 0], 1.45: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 0.6: [26, 0, 0], 0.9: [20, 0, 0], 1.45: ZERO}, mirror=False)
a.sound(0.3, "mob.dod.red_dragon.wing_unfold")
a.sound(0.62, "mob.dod.red_dragon.buffet")
a.particle(0.7, "wind_burst", "chest")
a.particle(0.7, "dust_ring", "ground")

# ----------------------------------------------------------------------------- 15. fire breath charge  16. release

CHARGE = {"neck_1": [-22, 0, 0], "neck_2": [-10, 0, 0], "neck_3": [-4, 0, 0], "neck_4": [2, 0, 0], "head": [-14, 0, 0]}
a = new("fire_charge", 1.3, loop="hold_on_last_frame")
for b, v in CHARGE.items():
    a.rot(b, {0: ZERO, 0.6: scaled(v, 0.8), 1.3: v}, mirror=False)
a.rot("jaw", {0: ZERO, 0.5: [6, 0, 0], 1.3: [10, 0, 0]}, mirror=False)
a.scale("chest", {0: ONE, 1.3: [1.07, 1.09, 1.02]}, mirror=False)
a.rot("body", {0: ZERO, 1.3: [-4, 0, 0]}, mirror=False)
a.pos("head", [0, 0, "q.anim_time > 0.5 ? math.sin(q.anim_time * 2400) * 0.25 : 0"], mirror=False)
a.sound(0.0, "mob.dod.red_dragon.fire_charge")
a.sound(0.1, "mob.dod.red_dragon.fire_charge_layer")
a.particle(0.0, "fire_charge_glow", "mouth")
a.particle(0.0, "fire_charge_core", "mouth")
a.particle(0.15, "nostril_smoke", "nostril_l")
a.particle(0.15, "nostril_smoke", "nostril_r")
a.particle(0.7, "nostril_smoke", "nostril_l")
a.particle(0.7, "nostril_smoke", "nostril_r")

# release: neck thrust forward so the head (and the fire jet bound to it) points level at dod:aim = 0,
# then pitched by dod:aim (degrees, + = down) spread over neck_2..head.
BREATH = {"neck_1": [10, 0, 0], "neck_2": [6, 0, 0], "neck_3": [4, 0, 0], "neck_4": [2, 0, 0], "head": [-21.3, 0, 0]}
AIM = "math.clamp(q.property('dod:aim'), -45, 60)"
BL = 3.2
a = new("fire_breath", BL, loop="hold_on_last_frame")
for b, v in BREATH.items():
    k = {"neck_1": 0.0, "neck_2": 0.25, "neck_3": 0.25, "neck_4": 0.2, "head": 0.3}[b]
    sweep = {"neck_1": 0, "neck_2": 2.5, "neck_3": 2, "neck_4": 1.5, "head": 2}[b]
    a.rot(b, [f"{v[0]} + {AIM} * {k}", f"math.sin(q.anim_time * 140) * {sweep}", 0], mirror=False)
a.rot("jaw", {0: [10, 0, 0], 0.12: [38, 0, 0], BL: [36, 0, 0]}, mirror=False)
a.pos("chest", [0, 0, "1.2 + math.sin(q.anim_time * 1700) * 0.25"], mirror=False)
a.rot("body", [-2, 0, 0], mirror=False)
a.scale("chest", {0: [1.07, 1.09, 1.02], 0.5: [1.02, 1.03, 1], BL: [0.98, 0.98, 1]}, mirror=False)
a.rot("leg_fl_upper", [-6, 0, -3])
# flame jet (red_dragon_fire.geo.json): grows out of the mouth in 0.25 s, flickers per segment
# the jet grows out of the mouth in 0.25 s; its length follows dod:jet (blocks to the first wall, max 12)
GROW = "math.min(q.anim_time * 4, 1)"
a.scale("fire_jet", [f"0.25 + 0.75 * {GROW}", f"0.25 + 0.75 * {GROW}",
                     f"math.max(0.02, {GROW} * math.clamp(q.property('dod:jet') / 12, 0.08, 1))"], mirror=False)
for i in range(8):
    a.scale(f"fire_s{i + 1}", [f"1 + math.sin(q.anim_time * {1500 + i * 210} + {i * 57}) * 0.16",
                               f"1 + math.sin(q.anim_time * {1300 + i * 170} + {i * 91}) * 0.16",
                               f"1 + math.sin(q.anim_time * {900 + i * 130} + {i * 33}) * 0.08"], mirror=False)
    a.rot(f"fire_s{i + 1}", [f"math.sin(q.anim_time * {700 + i * 90}) * {1 + i * 0.5}",
                             f"math.sin(q.anim_time * {610 + i * 80} + 40) * {1 + i * 0.5}",
                             f"q.anim_time * {200 + i * 40}"], mirror=False)
a.scale("fire_mouth", ["1 + math.sin(q.anim_time * 2500) * 0.25"] * 3, mirror=False)
for t in (0.0, 0.8, 1.6, 2.4):
    a.particle(t, "fire_mouth_burst", "mouth")
a.sound(0.0, "mob.dod.red_dragon.fire_breath")

# ----------------------------------------------------------------------------- 17. hurt (additive flinch)

a = new("hurt", 0.45)
a.rot("neck_1", {0: ZERO, 0.08: [-10, 4, 0], 0.45: ZERO}, mirror=False)
a.rot("head", {0: ZERO, 0.08: [-8, -8, 6], 0.45: ZERO}, mirror=False)
a.rot("jaw", {0: ZERO, 0.08: [16, 0, 0], 0.3: [4, 0, 0], 0.45: ZERO}, mirror=False)
a.pos("body", {0: ZERO, 0.08: [0, -1.5, 1.5], 0.45: ZERO}, mirror=False)
a.rot("body", {0: ZERO, 0.08: [-3, 0, 2], 0.45: ZERO}, mirror=False)
a.rot("wing_l_upper", {0: ZERO, 0.1: [0, 0, -6], 0.45: ZERO})
for i, t in enumerate(TAIL[:5]):
    a.rot(t, {0: ZERO, 0.12: [0, 4 + i, 0], 0.45: ZERO}, mirror=False)

# ----------------------------------------------------------------------------- 18. death (collapse, held)

a = new("death", 2.8, loop="hold_on_last_frame")
a.pos("root", {0: ZERO, 0.4: [0, -1, 0], 1.0: [0, -6, 0], 1.6: [0, -13, 0], 2.0: [0, -12, 0], 2.8: [0, -13, 0]},
      mirror=False)
a.rot("root", {0: ZERO, 0.4: [-4, 0, 0], 1.0: [3, 0, -3], 1.6: [1, 0, -5], 2.0: [0, 0, -4], 2.8: [0, 0, -5]},
      mirror=False)
a.rot("leg_fl_upper", {0: ZERO, 0.4: [-10, 0, 0], 1.0: [40, 0, -10], 1.6: [70, 0, -16], 2.8: [72, 0, -16]})
a.rot("leg_fl_lower", {0: ZERO, 1.0: [-50, 0, 0], 1.6: [-95, 0, 0], 2.8: [-95, 0, 0]})
a.rot("foot_fl", {0: ZERO, 1.6: [30, 0, 0], 2.8: [30, 0, 0]})
a.rot("leg_hl_thigh", {0: ZERO, 1.0: [-20, 0, -8], 1.6: [-40, 0, -18], 2.8: [-42, 0, -18]})
a.rot("leg_hl_shin", {0: ZERO, 1.6: [40, 0, 0], 2.8: [42, 0, 0]})
a.rot("leg_hl_meta", {0: ZERO, 1.6: [-30, 0, 0], 2.8: [-30, 0, 0]})
a.rot("neck_1", {0: ZERO, 0.4: [-24, 0, 0], 0.8: [-26, 6, 0], 1.4: [22, 10, 0], 1.8: [30, 12, 0], 2.8: [30, 12, 0]},
      mirror=False)
a.rot("neck_2", {0: ZERO, 0.4: [-10, 0, 0], 1.4: [10, 8, 0], 1.8: [12, 8, 0], 2.8: [12, 8, 0]}, mirror=False)
a.rot("neck_3", {0: ZERO, 1.4: [2, 8, 0], 1.8: [-4, 8, 0], 2.8: [-4, 8, 0]}, mirror=False)
a.rot("neck_4", {0: ZERO, 1.8: [-10, 4, 0], 2.8: [-10, 4, 0]}, mirror=False)
a.rot("head", {0: ZERO, 0.4: [-20, 0, 0], 1.4: [-6, 0, 10], 1.8: [-22, 0, 20], 2.1: [-16, 0, 18], 2.8: [-18, 0, 20]},
      mirror=False)
a.rot("jaw", {0: ZERO, 0.4: [36, 0, 0], 1.0: [30, 0, 0], 1.8: [14, 0, 0], 2.8: [16, 0, 0]}, mirror=False)
# wings: the folded base pose is active (ground); spread them half and let them drape over the ground
wing_frames(a, {0: 1, 0.5: 0.5, 1.6: 0.15, 2.8: 0.15})
a.rot("wing_l_upper", {0: ZERO, 0.5: add(scaled(fu, -0.5), [0, 0, -30]), 1.6: add(scaled(fu, -0.85), [0, -10, 6]),
                       2.8: add(scaled(fu, -0.85), [0, -10, 8])})
TAIL_DEATH = [12, 10, 4, -2, -6, -6, -4, -2]
for i, t in enumerate(TAIL):
    a.rot(t, {0: ZERO, 0.6: [4, 0, 0], 1.6: [TAIL_DEATH[i], 5 + i, 0], 2.8: [TAIL_DEATH[i], 6 + i, 0]}, mirror=False)
a.sound(0.35, "mob.dod.red_dragon.death")
a.particle(1.6, "dust_ring", "ground")
a.particle(1.7, "death_embers", "chest")


# ----------------------------------------------------------------------------- controllers

ACTIONS = {
    "roar": "roar", "bite": "bite", "claw": "claw", "tail": "tail_smash", "buffet": "wing_buffet",
    "fire_charge": "fire_charge", "fire_breath": "fire_breath", "look": "look_around", "stretch": "wing_stretch",
}


def ctrl_action():
    states = {"default": {"transitions": [{a: f"q.property('dod:action') == '{a}'"} for a in ACTIONS]}}
    for a, anim in ACTIONS.items():
        tr = [{o: f"q.property('dod:action') == '{o}'"} for o in ACTIONS if o != a]
        tr.append({"default": f"q.property('dod:action') != '{a}'"})
        states[a] = {"animations": [anim], "transitions": tr, "blend_transition": 0.18}
    states["default"]["blend_transition"] = 0.22
    return {"initial_state": "default", "states": states}


def ctrl_move():
    F = "q.property('dod:flight')"
    dead = "q.property('dod:action') == 'death' || !q.is_alive"
    def go(dst_map):  # noqa: E306
        return [{"dead": dead}] + [{k: v} for k, v in dst_map.items()]
    return {
        "initial_state": "ground",
        "states": {
            "ground": {
                "animations": ["idle", {"walk": "v.walk_w"}, {"run": "v.run_w"}],
                "transitions": go({"takeoff": f"{F} == 'takeoff'", "fly": f"{F} == 'fly'", "glide": f"{F} == 'glide'",
                                   "landing": f"{F} == 'landing'"}),
                "blend_transition": 0.35,
            },
            "takeoff": {
                "animations": ["takeoff"],
                "transitions": go({"fly": f"{F} == 'fly'", "glide": f"{F} == 'glide'",
                                   "landing": f"{F} == 'landing'", "ground": f"{F} == 'ground'"}),
                "blend_transition": 0.25,
            },
            "fly": {
                "animations": ["fly"],
                "transitions": go({"glide": f"{F} == 'glide'", "landing": f"{F} == 'landing'",
                                   "ground": f"{F} == 'ground'", "takeoff": f"{F} == 'takeoff'"}),
                "blend_transition": 0.4,
            },
            "glide": {
                "animations": ["glide"],
                "transitions": go({"fly": f"{F} == 'fly'", "landing": f"{F} == 'landing'",
                                   "ground": f"{F} == 'ground'", "takeoff": f"{F} == 'takeoff'"}),
                "blend_transition": 0.5,
            },
            "landing": {
                "animations": ["landing"],
                "transitions": go({"ground": f"{F} == 'ground'", "takeoff": f"{F} == 'takeoff'", "fly": f"{F} == 'fly'",
                                   "glide": f"{F} == 'glide'"}),
                "blend_transition": 0.3,
            },
            "dead": {
                "animations": ["death"],
                "transitions": [{"ground": "q.property('dod:action') != 'death' && q.is_alive"}],
                "blend_transition": 0.3,
            },
        },
    }


def ctrl_look():
    on = "q.property('dod:action') == 'none' && q.property('dod:flight') == 'ground' && q.is_alive"
    return {
        "initial_state": "on",
        "states": {
            "on": {"animations": ["look_at_target"], "transitions": [{"off": f"!({on})"}], "blend_transition": 0.4},
            "off": {"transitions": [{"on": on}], "blend_transition": 0.4},
        },
    }


def ctrl_hurt():
    return {
        "initial_state": "default",
        "states": {
            "default": {"transitions": [{"hurt": "q.hurt_time > 0 && q.is_alive"}]},
            "hurt": {"animations": ["hurt"], "transitions": [{"default": "q.all_animations_finished"}],
                     "blend_transition": 0.1},
        },
    }


def main():
    anims = {k: v.json() for k, v in ANIMS.items()}
    doc = {"format_version": "1.10.0", "animations": anims}
    os.makedirs(os.path.join(RP, "animations"), exist_ok=True)
    with open(os.path.join(RP, "animations", "red_dragon.animation.json"), "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    ctrls = {
        "controller.animation.dod.red_dragon.move": ctrl_move(),
        "controller.animation.dod.red_dragon.action": ctrl_action(),
        "controller.animation.dod.red_dragon.look": ctrl_look(),
        "controller.animation.dod.red_dragon.hurt": ctrl_hurt(),
    }
    os.makedirs(os.path.join(RP, "animation_controllers"), exist_ok=True)
    with open(os.path.join(RP, "animation_controllers", "red_dragon.animation_controllers.json"), "w") as f:
        json.dump({"format_version": "1.10.0", "animation_controllers": ctrls}, f, indent=1)
        f.write("\n")
    print(f"{len(anims)} animations, {len(ctrls)} controllers")


if __name__ == "__main__":
    main()
