#!/usr/bin/env python3
"""
Gharvok animations + animation controllers + the timing table shared with the scripts.

    python3 tools/gen_anims.py

Writes
  addon/resource_packs/dragon_dominion/animations/gharvok.animation.json
  addon/resource_packs/dragon_dominion/animation_controllers/gharvok.animation_controllers.json
  addon/behavior_packs/dragon_dominion/scripts/dragons/gharvok/timings.js   (lengths + hit frames, generated)

Rotation sign reminders (Bedrock, see kinematics.py):
  +x pitches a forward (-Z) pointing part DOWN and lifts a backward (+Z) pointing part (tail) UP.
  +y swings a forward pointing part (head) toward the creature's RIGHT (-X); swings the tail toward +X (left).
  left wing (+X): -z raises it.   Right side values are mirrored automatically: (x, -y, -z).
Every animation is authored for the LEFT side; `sym()` writes the mirrored right side.
"""
from __future__ import annotations

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_dominion")
BP = os.path.join(ROOT, "addon", "behavior_packs", "dragon_dominion")
NS = "animation.dragon_dominion.gharvok"
RIG = json.load(open(os.path.join(HERE, ".rig.json")))
BONES = set(RIG["bones"])
TAIL = [f"tail_{i}" for i in range(1, 9)] + ["tail_blade"]
NECK = ["neck_1", "neck_2", "neck_3", "head"]
FINGERS = ["f1", "f2", "f3", "f4"]


def r(v):
    v = round(float(v), 3)
    return int(v) if v == int(v) else v


class Anim:
    def __init__(self, name, length, loop=False, hold=False, speed_expr=None):
        self.name, self.length, self.loop, self.hold = name, length, loop, hold
        self.speed_expr = speed_expr
        self.ch = {}  # bone -> {"rotation": {t: [x,y,z]}, "position": {...}}
        self.timeline = {}
        self.sounds = {}
        self.particles = {}

    # -------------------------------------------------------------- key helpers
    def key(self, bone, chan, t, v, mirror=True):
        assert bone in BONES, f"{self.name}: unknown bone {bone}"
        d = self.ch.setdefault(bone, {}).setdefault(chan, {})
        d[r(t)] = [r(x) for x in v]
        if mirror and ("_l_" in bone or bone.endswith("_l")):
            rb = bone.replace("_l_", "_r_") if "_l_" in bone else bone[:-2] + "_r"
            if chan == "rotation":
                mv = [v[0], -v[1], -v[2]]
            elif chan == "scale":
                mv = list(v)
            else:
                mv = [-v[0], v[1], v[2]]
            d2 = self.ch.setdefault(rb, {}).setdefault(chan, {})
            d2[r(t)] = [r(x) for x in mv]

    def rot(self, bone, keys, mirror=True):
        """keys: {t: (x, y, z)}"""
        for t, v in keys.items():
            self.key(bone, "rotation", t, v, mirror)

    def scl(self, bone, keys, mirror=True):
        for t, v in keys.items():
            self.key(bone, "scale", t, v, mirror)

    def pos(self, bone, keys, mirror=True):
        for t, v in keys.items():
            self.key(bone, "position", t, v, mirror)

    def rot_lr(self, bone_l, keys_l, keys_r):
        """Independent left/right keys (no mirroring); right keys are given in LEFT-side convention."""
        rb = bone_l.replace("_l_", "_r_") if "_l_" in bone_l else bone_l[:-2] + "_r"
        for t, v in keys_l.items():
            self.key(bone_l, "rotation", t, v, mirror=False)
        for t, v in keys_r.items():
            self.key(rb, "rotation", t, [v[0], -v[1], -v[2]], mirror=False)

    def expr(self, bone, chan, e, mirror=True, mirror_expr=None):
        """Molang expression channel [ex, ey, ez]."""
        assert bone in BONES, bone
        self.ch.setdefault(bone, {})[chan] = e
        if mirror and ("_l_" in bone or bone.endswith("_l")):
            rb = bone.replace("_l_", "_r_") if "_l_" in bone else bone[:-2] + "_r"
            self.ch.setdefault(rb, {})[chan] = mirror_expr or (
                [e[0], neg(e[1]), neg(e[2])] if chan == "rotation" else [neg(e[0]), e[1], e[2]])

    def chain(self, bones, keys, falloff=1.0, delay=None):
        """Same motion down a chain (neck/tail), each link delayed and scaled."""
        if delay is None:  # overlapping action: each link follows the previous one a little later
            delay = 0.035 if bones[0] in TAIL else 0.025
        for i, b in enumerate(bones):
            s = falloff ** i
            # tail values are authored as the whole tail's bend: spread the pitch over its 8 links
            px = 0.3 if b in TAIL else 1.0
            for t, v in keys.items():
                tt = t + delay * i if 0 < t < self.length else t
                if tt >= self.length - 0.02 and t < self.length:
                    continue  # a delayed key that would fall past the end is dropped, never piled up at the end
                self.key(b, "rotation", tt, [v[0] * s * px, v[1] * s, v[2] * s])

    def sound(self, t, s):
        self.sounds[r(t)] = {"effect": s}

    def fx(self, t, effect, locator=None):
        e = {"effect": effect}
        if locator:
            e["locator"] = locator
        self.particles[r(t)] = e

    def json(self):
        out = {}
        if self.loop:
            out["loop"] = True
        elif self.hold:
            out["loop"] = "hold_on_last_frame"
        out["animation_length"] = r(self.length)
        if self.speed_expr:
            out["anim_time_update"] = self.speed_expr
        bones = {}
        for b in sorted(self.ch):
            bones[b] = {}
            for chan, keys in self.ch[b].items():
                if isinstance(keys, list):
                    bones[b][chan] = keys
                else:
                    ks = dict(sorted(keys.items()))
                    bones[b][chan] = {str(k): {"post": v, "lerp_mode": "catmullrom"} for k, v in ks.items()} \
                        if len(ks) > 1 else {str(k): v for k, v in ks.items()}
        out["bones"] = bones
        if self.sounds:
            out["sound_effects"] = {str(k): v for k, v in sorted(self.sounds.items())}
        if self.particles:
            out["particle_effects"] = {str(k): v for k, v in sorted(self.particles.items())}
        return out


def neg(e):
    e = str(e)
    if e in ("0", "0.0"):
        return "0"
    return f"-({e})"


A = {}


def anim(name, length, **kw):
    a = Anim(name, length, **kw)
    A[name] = a
    return a


def sine(amp, period, phase=0.0, base=0.0, t="q.anim_time"):
    """Molang sine in degrees-of-cycle."""
    return f"{base} + {amp} * math.sin(({t} / {period} + {phase}) * 360)"


# =========================================================================== static poses
def _wing_pose(arm, fore, hand, spread):
    d = {"wing_l_arm": arm, "wing_l_fore": fore, "wing_l_hand": hand}
    for k, f in enumerate(FINGERS):
        d[f"wing_l_{f}"] = (0, round(spread * (k - 1.5) / 1.5, 2), 0)
    return d


# both poses were fitted to points read off the reference sheet by tools/fit_wings.py
FOLD = _wing_pose((-124.4, -65.0, 72.5), (42.7, 148.2, 4.0), (23.5, -124.1, -23.1), 30.9)      # tight, for running
DISPLAY = _wing_pose((-56.0, -47.7, -56.1), (-14.6, -17.7, 74.4), (23.3, -59.4, 10.8), 6.6)    # reference stance
FOLD_SCALE = {"wing_l_mem_arm": (1, 1, 0.3), "wing_l_mem_fore": (1, 1, 0.22)}
a = anim("wing_fold", 1.0, loop=True)
for b, v in FOLD.items():
    a.rot(b, {0: v})
for b, v in FOLD_SCALE.items():
    a.scl(b, {0: v})


# =========================================================================== helpers for gaits
LEGS = {  # bone chain, is_front
    "fl": ("arm_l_upper", "arm_l_lower", "hand_l"),
    "fr": ("arm_r_upper", "arm_r_lower", "hand_r"),
    "hl": ("leg_l_thigh", "leg_l_shin", "leg_l_foot"),
    "hr": ("leg_r_thigh", "leg_r_shin", "leg_r_foot"),
}


def gait(a, period, phases, swing, lift, t="q.anim_time", base=None):
    """Sinusoidal leg cycle. phases: {'fl': 0.0, ...} (fraction of a cycle).
    Upper bone swings (-x = forward), lower joints flex only during the forward (lifted) half."""
    base = base or {}
    for leg, ph in phases.items():
        up, mid, low = LEGS[leg]
        front = leg[0] == "f"
        ang = f"(({t}) / {period} + {ph}) * 360"
        b0, b1, b2 = base.get(leg, (0, 0, 0))
        a.expr(up, "rotation", [f"{b0} - {swing} * math.sin({ang})", 0, 0], mirror=False)
        up_ = f"math.pow(math.max(0, math.cos({ang})), 2)"     # lifted (swing) phase, smooth in and out
        down_ = f"math.pow(math.max(0, -math.cos({ang})), 2)"  # planted (stance) phase
        if front:
            a.expr(mid, "rotation", [f"{b1} + {lift} * {up_}", 0, 0], mirror=False)
            a.expr(low, "rotation", [f"{b2} + {lift * 0.8} * {up_} - {swing * 0.35} * {down_}", 0, 0], mirror=False)
        else:
            a.expr(mid, "rotation", [f"{b1} - {lift} * {up_}", 0, 0], mirror=False)
            a.expr(low, "rotation", [f"{b2} + {lift * 1.1} * {up_}", 0, 0], mirror=False)
        # the foot rises while it swings forward instead of dragging through the ground
        a.expr(up, "position", [0, f"{lift * 0.06} * {up_}", 0], mirror=False)


def tail_wave(a, amp_y, period, lag=0.07, amp_x=0.0, base_x=0.0, t="q.anim_time", grow=1.12):
    for i, b in enumerate(TAIL):
        k = grow ** i
        a.expr(b, "rotation", [f"{base_x * 0.3} + {amp_x * k * 0.3} * math.sin((({t}) / {period} - {lag * i}) * 360 + 90)",
                               f"{amp_y * k} * math.sin((({t}) / {period} - {lag * i}) * 360)", 0])


def legs_static(a, t, fl=(0, 0, 0), hl=(0, 0, 0), fr=None, hr=None):
    """Key all four legs at time t: tuples are (upper, mid, low) x-rotations."""
    fr = fr or fl
    hr = hr or hl
    for leg, v in (("fl", fl), ("fr", fr), ("hl", hl), ("hr", hr)):
        for bone, x in zip(LEGS[leg], v):
            a.key(bone, "rotation", t, [x, 0, 0], mirror=False)


def legs_keys(a, keys):
    """keys: {t: dict(fl=(..), hl=(..), fr=?, hr=?)}"""
    for t, d in keys.items():
        legs_static(a, t, **d)


def wings(a, keys, mirror=True):
    """Wing keys relative to the SPREAD rest pose. keys: {t: {'arm': (x,y,z), 'fore':..., 'hand':..., 'fingers': yaw}}"""
    for t, d in keys.items():
        for part in ("arm", "fore", "hand"):
            if part in d:
                a.key(f"wing_l_{part}", "rotation", t, d[part], mirror)
        if "fingers" in d:
            spread = d["fingers"]
            for i, f in enumerate(FINGERS):
                a.key(f"wing_l_{f}", "rotation", t, [0, spread * (i - 1.5) / 1.5, 0], mirror)
        for mem in ("mem_arm", "mem_fore"):
            if mem in d:
                a.key(f"wing_l_{mem}", "scale", t, d[mem], mirror)


def fold_keys(frac=1.0, extra=None):
    """A wing key dict equal to the folded pose * frac (plus extra)."""
    d = {"arm": [v * frac for v in FOLD["wing_l_arm"]], "fore": [v * frac for v in FOLD["wing_l_fore"]],
         "hand": [v * frac for v in FOLD["wing_l_hand"]],
         "mem_arm": [1 - (1 - v) * frac for v in FOLD_SCALE["wing_l_mem_arm"]],
         "mem_fore": [1 - (1 - v) * frac for v in FOLD_SCALE["wing_l_mem_fore"]]}
    if extra:
        for k, v in extra.items():
            d[k] = [x + y for x, y in zip(d.get(k, [0, 0, 0]), v)] if k in d else v
    return d


def display_delta(a, t, frac=1.0):
    """Key the display pose as an exact additive delta on top of the folded pose (Bedrock sums euler angles)."""
    for b in DISPLAY:
        d = [(x - y) * frac for x, y in zip(DISPLAY[b], FOLD.get(b, (0, 0, 0)))]
        a.key(b, "rotation", t, d)
    for b, sv in FOLD_SCALE.items():
        a.key(b, "scale", t, [1 + (1 / v - 1) * frac for v in sv])


SPREAD_UP = {"arm": (0, 8, -28), "fore": (0, -10, 18), "hand": (0, 8, 6), "fingers": 0}
DOWNSTROKE = {"arm": (0, -6, 26), "fore": (0, 6, 14), "hand": (0, -6, 12), "fingers": -6}

# =========================================================================== LOCOMOTION
a = anim("idle_breathing", 6.4, loop=True)  # two breaths; the slow tail sway loops exactly once
a.expr("body", "position", [0, sine(0.45, 3.2), 0])
a.expr("chest", "rotation", [sine(-1.2, 3.2), 0, 0])
a.expr("neck_1", "rotation", [sine(1.5, 3.2, 0.1), 0, 0])
a.expr("head", "rotation", [sine(-1.5, 3.2, 0.15), 0, 0])
a.expr("jaw", "rotation", [f"1 + 1 * math.max(0, math.sin((q.anim_time / 3.2 + 0.25) * 360))", 0, 0])
a.expr("crown", "rotation", [sine(-1.0, 3.2, 0.2), 0, 0])
tail_wave(a, 3.0, 6.4, lag=0.05, amp_x=0.8)
a.expr("wing_l_arm", "rotation", [0, 0, sine(1.2, 3.2, 0.1)])
for leg in ("fl", "fr", "hl", "hr"):  # keep the feet planted while the body breathes
    up, mid, low = LEGS[leg]
    a.expr(up, "position", [0, sine(-0.3, 3.2), 0], mirror=False)

a = anim("idle_head_scan", 4.0)
a.chain(["neck_1", "neck_2", "neck_3", "head"], {0: (0, 0, 0), 0.6: (-3, -9, 2), 1.4: (-3, -9, 2), 2.1: (2, 10, -2),
                                                  2.9: (2, 10, -2), 3.5: (0, 0, 0), 4.0: (0, 0, 0)}, falloff=0.9)
a.rot("jaw", {0: (0, 0, 0), 1.0: (0, 0, 0), 1.2: (6, 0, 0), 1.4: (0, 0, 0), 4.0: (0, 0, 0)})
a.rot("crown", {0: (0, 0, 0), 0.6: (-4, 0, 0), 2.1: (-4, 0, 0), 3.5: (0, 0, 0)})
a.sound(1.15, "snort")

WALK_SPEED = "math.max(q.ground_speed, q.property('dragon_dominion:gait') == 1 ? 2.2 : (q.property('dragon_dominion:gait') == 2 ? 5.8 : 0.0))"
a = anim("walk", 1.3, loop=True, speed_expr=f"q.anim_time + q.delta_time * math.clamp({WALK_SPEED} / 2.2, 0.6, 1.8)")
gait(a, 1.3, {"fl": 0.0, "hr": 0.06, "fr": 0.5, "hl": 0.56}, swing=22, lift=24)
a.expr("body", "position", [0, "0.6 * math.cos((q.anim_time / 1.3) * 720)", 0])
a.expr("body", "rotation", [0, "2 * math.sin((q.anim_time / 1.3) * 360)", "1.8 * math.sin((q.anim_time / 1.3) * 360)"])
a.expr("neck_1", "rotation", ["1.5 * math.cos((q.anim_time / 1.3) * 720 + 60)", "-2 * math.sin((q.anim_time / 1.3) * 360 - 30)", 0])
a.expr("head", "rotation", ["-1.5 * math.cos((q.anim_time / 1.3) * 720 + 80)", "-1 * math.sin((q.anim_time / 1.3) * 360 - 60)", 0])
tail_wave(a, 4.0, 1.3, lag=0.07)
a.fx(0.05, "step", "loc_claw_l")
a.fx(0.7, "step", "loc_claw_r")
a.sound(0.05, "step")
a.sound(0.7, "step")

a = anim("run", 0.72, loop=True, speed_expr=f"q.anim_time + q.delta_time * math.clamp({WALK_SPEED} / 5.8, 0.7, 1.6)")
gait(a, 0.72, {"fl": 0.0, "fr": 0.1, "hl": 0.5, "hr": 0.6}, swing=30, lift=34)
a.expr("body", "position", [0, "1.4 * math.cos((q.anim_time / 0.72) * 720)", 0])
a.expr("body", "rotation", ["4 * math.sin((q.anim_time / 0.72) * 360 + 90)", 0, 0])
a.expr("neck_1", "rotation", ["6 - 4 * math.sin((q.anim_time / 0.72) * 360 + 60)", 0, 0])
a.expr("head", "rotation", ["4 + 3 * math.sin((q.anim_time / 0.72) * 360 + 30)", 0, 0])
tail_wave(a, 3.0, 0.72, lag=0.06, amp_x=3.5, base_x=4)
a.fx(0.0, "step", "loc_claw_l")
a.fx(0.36, "step", "loc_foot_l")
a.sound(0.0, "step")
a.sound(0.36, "step")

a = anim("turn", 1.0, loop=True)
gait(a, 1.0, {"fl": 0.0, "hr": 0.0, "fr": 0.5, "hl": 0.5}, swing=8, lift=22)
a.expr("body", "rotation", [0, "4 * math.sin(q.anim_time * 360)", 0])
a.expr("neck_1", "rotation", [0, "-v.turn_dir * 8", 0])
a.expr("head", "rotation", [0, "-v.turn_dir * 6", 0])
tail_wave(a, 6.0, 1.0, lag=0.07)

a = anim("jump", 1.0)
a.pos("body", {0: (0, 0, 0), 0.3: (0, -5, 0), 0.42: (0, 2, 0), 0.75: (0, 1, 0), 0.88: (0, -4, 0), 1.0: (0, 0, 0)})
a.rot("body", {0: (0, 0, 0), 0.3: (6, 0, 0), 0.42: (-14, 0, 0), 0.7: (6, 0, 0), 0.88: (3, 0, 0), 1.0: (0, 0, 0)})
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)),
              0.3: dict(fl=(-10, 30, 10), hl=(-25, 30, 20)),
              0.42: dict(fl=(-45, 20, 30), hl=(45, -10, -30)),
              0.7: dict(fl=(-30, 50, 20), hl=(-20, 40, 30)),
              0.88: dict(fl=(-5, 25, 0), hl=(-20, 25, 15)),
              1.0: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.chain(["tail_1", "tail_2", "tail_3", "tail_4"], {0: (0, 0, 0), 0.42: (-10, 0, 0), 0.7: (8, 0, 0), 1.0: (0, 0, 0)})
a.chain(["neck_1", "head"], {0: (0, 0, 0), 0.3: (10, 0, 0), 0.42: (-10, 0, 0), 0.88: (12, 0, 0), 1.0: (0, 0, 0)})
a.fx(0.4, "dust_ring")
a.fx(0.88, "dust_ring")

a = anim("takeoff", 1.2)
a.pos("body", {0: (0, 0, 0), 0.4: (0, -6, 0), 0.62: (0, 3, 0), 1.2: (0, 2, 0)})
a.rot("body", {0: (0, 0, 0), 0.4: (4, 0, 0), 0.62: (-16, 0, 0), 1.2: (-6, 0, 0)})
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.4: dict(fl=(-10, 35, 10), hl=(-30, 35, 25)),
              0.62: dict(fl=(-30, 10, 30), hl=(50, -10, -30)), 1.2: dict(fl=(-40, 60, 40), hl=(35, 20, 30))})
wings(a, {0: fold_keys(0.0, None), 0.35: SPREAD_UP | {"arm": (0, 10, -42)},
          0.62: DOWNSTROKE | {"arm": (0, -8, 34)}, 0.9: SPREAD_UP, 1.2: {"arm": (0, 0, 0), "fore": (0, 0, 0), "hand": (0, 0, 0), "fingers": 0}})
a.chain(["neck_1", "neck_2", "head"], {0: (0, 0, 0), 0.4: (12, 0, 0), 0.62: (-14, 0, 0), 1.2: (-4, 0, 0)}, falloff=0.8)
a.chain(TAIL[:5], {0: (0, 0, 0), 0.62: (-8, 0, 0), 1.2: (6, 0, 0)}, falloff=1.1)
a.fx(0.62, "wing_gust")
a.sound(0.6, "flap")

a = anim("wing_flap", 0.8, loop=True)
a.expr("wing_l_arm", "rotation", ["0", "6 * math.sin(q.anim_time / 0.8 * 360 + 90)", "-6 - 38 * math.cos(q.anim_time / 0.8 * 360)"])
a.expr("wing_l_fore", "rotation", ["0", "-6 * math.sin(q.anim_time / 0.8 * 360 + 90)", "-20 * math.cos(q.anim_time / 0.8 * 360 - 50)"])
a.expr("wing_l_hand", "rotation", ["0", "0", "-14 * math.cos(q.anim_time / 0.8 * 360 - 90)"])
a.expr("body", "position", [0, "-2.5 * math.cos(q.anim_time / 0.8 * 360 + 180)", 0])
a.expr("neck_1", "rotation", ["-6 + 3 * math.cos(q.anim_time / 0.8 * 360)", 0, 0])
legs_static(a, 0, fl=(-35, 55, 40), hl=(40, 20, 35))
tail_wave(a, 2.0, 0.8, lag=0.08, amp_x=3.0, base_x=4)
a.sound(0.35, "flap")

a = anim("glide", 3.0, loop=True)
a.expr("wing_l_arm", "rotation", ["0", "0", "-4 + 2.5 * math.sin(q.anim_time / 3.0 * 360)"])
a.expr("wing_l_fore", "rotation", ["0", "0", "3 * math.sin(q.anim_time / 3.0 * 360 - 40)"])
a.expr("wing_l_hand", "rotation", ["0", "0", "2 + 2 * math.sin(q.anim_time / 3.0 * 360 - 80)"])
a.expr("body", "rotation", ["-3", "0", "4 * math.sin(q.anim_time / 3.0 * 360)"])
a.expr("neck_1", "rotation", ["-6", "0", "0"])
a.expr("head", "rotation", ["6", "0", "0"])
legs_static(a, 0, fl=(-40, 60, 40), hl=(45, 20, 40))
tail_wave(a, 3.0, 3.0, lag=0.06, base_x=5)

a = anim("landing", 1.0)
wings(a, {0: SPREAD_UP | {"arm": (0, 18, -30), "fore": (0, -20, 10)}, 0.3: {"arm": (0, 20, -20), "fore": (0, -26, 6), "hand": (0, 10, 0), "fingers": 8},
          0.45: {"arm": (0, 0, 12), "fore": (0, 0, 6), "hand": (0, 0, 0), "fingers": 0}, 1.0: fold_keys(0.7)})
a.pos("body", {0: (0, 6, 0), 0.32: (0, 2, 0), 0.42: (0, -6, 0), 0.65: (0, -2, 0), 1.0: (0, 0, 0)})
a.rot("body", {0: (-14, 0, 0), 0.32: (-8, 0, 0), 0.42: (6, 0, 0), 0.7: (2, 0, 0), 1.0: (0, 0, 0)})
legs_keys(a, {0: dict(fl=(-45, 30, 30), hl=(-30, 10, 10)), 0.32: dict(fl=(-30, 10, 10), hl=(-20, 10, 10)),
              0.42: dict(fl=(-10, 35, 10), hl=(-25, 35, 25)), 0.7: dict(fl=(-4, 12, 2), hl=(-10, 12, 8)),
              1.0: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.chain(["neck_1", "neck_2", "head"], {0: (-8, 0, 0), 0.42: (16, 0, 0), 0.7: (-4, 0, 0), 1.0: (0, 0, 0)}, falloff=0.8)
a.chain(TAIL, {0: (8, 0, 0), 0.42: (-10, 0, 0), 0.7: (4, 0, 0), 1.0: (0, 0, 0)}, falloff=1.05)
a.fx(0.42, "dust_ring")
a.sound(0.42, "land")

# =========================================================================== COMBAT
a = anim("roar", 2.4)
a.chain(["neck_1", "neck_2", "neck_3"], {0: (0, 0, 0), 0.45: (10, 0, 0), 0.75: (-22, 0, 0), 1.9: (-18, 0, 0), 2.4: (0, 0, 0)}, falloff=0.8)
a.rot("head", {0: (0, 0, 0), 0.45: (8, 0, 0), 0.75: (-16, 0, 0), 1.0: (-14, 4, 0), 1.2: (-16, -4, 0), 1.4: (-14, 4, 0),
               1.6: (-16, -4, 0), 1.9: (-14, 0, 0), 2.4: (0, 0, 0)}, mirror=False)
a.rot("jaw", {0: (0, 0, 0), 0.5: (4, 0, 0), 0.75: (38, 0, 0), 1.85: (34, 0, 0), 2.2: (0, 0, 0)})
a.rot("crown", {0: (0, 0, 0), 0.75: (-10, 0, 0), 1.9: (-10, 0, 0), 2.4: (0, 0, 0)})
a.rot("body", {0: (0, 0, 0), 0.45: (3, 0, 0), 0.75: (-8, 0, 0), 1.9: (-6, 0, 0), 2.4: (0, 0, 0)})
a.pos("body", {0: (0, 0, 0), 0.45: (0, -2, 0), 0.75: (0, 1, 0), 2.4: (0, 0, 0)})
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.75: dict(fl=(6, -4, 0), hl=(-6, 8, 2)), 1.9: dict(fl=(6, -4, 0), hl=(-6, 8, 2)), 2.4: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
wings(a, {0: {"arm": (0, 0, 0), "fore": (0, 0, 0)}, 0.75: {"arm": (-8, 6, -12), "fore": (0, -6, -8)},
          1.9: {"arm": (-8, 6, -11), "fore": (0, -6, -8)}, 2.4: {"arm": (0, 0, 0), "fore": (0, 0, 0)}})  # flare
a.chain(TAIL, {0: (0, 0, 0), 0.75: (8, 0, 0), 1.9: (6, 0, 0), 2.4: (0, 0, 0)}, falloff=1.05)
a.fx(0.8, "roar_breath", "loc_mouth")

a = anim("claw_combo", 2.0)
# left swipe: windup 0.15-0.42, strike 0.42-0.6 (hit 0.55); right: windup 0.7-0.92, strike 0.92-1.1 (hit 1.05)
a.rot_lr("arm_l_upper", {0: (0, 0, 0), 0.4: (-70, 10, -20), 0.52: (-20, -20, 10), 0.62: (12, -10, 8), 0.9: (0, 0, 0), 2.0: (0, 0, 0)},
         {0: (0, 0, 0), 0.4: (6, 0, 0), 0.62: (0, 0, 0), 0.9: (-72, 10, -20), 1.02: (-20, -20, 10), 1.12: (12, -10, 8), 1.5: (0, 0, 0), 2.0: (0, 0, 0)})
a.rot_lr("arm_l_lower", {0: (0, 0, 0), 0.4: (40, 0, 0), 0.52: (-10, 0, 0), 0.62: (10, 0, 0), 0.9: (0, 0, 0)},
         {0: (0, 0, 0), 0.9: (40, 0, 0), 1.02: (-10, 0, 0), 1.12: (10, 0, 0), 1.5: (0, 0, 0)})
a.rot_lr("hand_l", {0: (0, 0, 0), 0.4: (-30, 0, 0), 0.52: (20, 0, 0), 0.9: (0, 0, 0)},
         {0: (0, 0, 0), 0.9: (-30, 0, 0), 1.02: (20, 0, 0), 1.5: (0, 0, 0)})
a.rot("body", {0: (0, 0, 0), 0.4: (-6, -6, -4), 0.55: (5, 6, 3), 0.9: (-6, 6, 4), 1.05: (5, -6, -3), 1.5: (0, 0, 0), 2.0: (0, 0, 0)}, mirror=False)
a.pos("body", {0: (0, 0, 0), 0.4: (0, 2, 3), 0.55: (0, -1, -3), 0.9: (0, 2, 3), 1.05: (0, -1, -3), 1.5: (0, 0, 0)}, mirror=False)
a.chain(["neck_1", "neck_2", "head"], {0: (0, 0, 0), 0.4: (-4, 6, 0), 0.55: (8, -6, 0), 0.9: (-4, -6, 0), 1.05: (8, 6, 0), 1.5: (0, 0, 0)}, falloff=0.9)
a.rot("jaw", {0: (0, 0, 0), 0.5: (18, 0, 0), 0.7: (6, 0, 0), 1.0: (20, 0, 0), 1.3: (0, 0, 0)})
a.chain(TAIL, {0: (0, 0, 0), 0.55: (0, -6, 0), 1.05: (0, 6, 0), 1.6: (0, 0, 0)}, falloff=1.08)
a.fx(0.55, "claw_slash", "loc_claw_l")
a.fx(1.05, "claw_slash", "loc_claw_r")

a = anim("charge_windup", 1.4)
a.chain(["neck_1", "neck_2", "neck_3"], {0: (0, 0, 0), 0.5: (-10, 0, 0), 0.9: (15, 0, 0), 1.4: (16, 0, 0)}, falloff=0.75)
a.rot("head", {0: (0, 0, 0), 0.5: (-10, 0, 0), 0.9: (18, 0, 0), 1.1: (16, 3, 0), 1.25: (18, -3, 0), 1.4: (18, 0, 0)}, mirror=False)
a.rot("crown", {0: (0, 0, 0), 0.9: (6, 0, 0), 1.4: (6, 0, 0)})
a.rot("jaw", {0: (0, 0, 0), 0.4: (24, 0, 0), 0.7: (0, 0, 0)})
a.rot("body", {0: (0, 0, 0), 0.5: (-4, 0, 0), 0.9: (8, 0, 0), 1.4: (9, 0, 0)})
a.pos("body", {0: (0, 0, 0), 0.9: (0, -3, 3), 1.4: (0, -3.5, 4)})
a.rot_lr("arm_l_upper", {0: (0, 0, 0), 0.9: (-10, 0, -8), 1.4: (-10, 0, -8)}, {0: (0, 0, 0), 0.6: (-20, 0, 0), 0.8: (15, 0, 0), 1.0: (-18, 0, 0), 1.2: (14, 0, 0), 1.4: (-6, 0, -6)})
a.rot_lr("arm_l_lower", {0: (0, 0, 0), 1.4: (12, 0, 0)}, {0: (0, 0, 0), 0.6: (30, 0, 0), 0.8: (6, 0, 0), 1.0: (30, 0, 0), 1.2: (6, 0, 0), 1.4: (12, 0, 0)})
legs_keys(a, {0: dict(hl=(0, 0, 0)), 0.9: dict(hl=(-22, 28, 16)), 1.4: dict(hl=(-24, 30, 18))})
a.chain(TAIL, {0: (0, 0, 0), 0.9: (10, 0, 0), 1.1: (10, 8, 0), 1.25: (10, -8, 0), 1.4: (12, 0, 0)}, falloff=1.06)
a.fx(0.8, "dust_puff", "loc_claw_r")
a.fx(1.2, "dust_puff", "loc_claw_r")
a.fx(0.45, "roar_breath", "loc_mouth")

a = anim("charge", 0.6, loop=True)
gait(a, 0.6, {"fl": 0.0, "fr": 0.12, "hl": 0.5, "hr": 0.62}, swing=34, lift=36)
a.expr("body", "position", [0, "-2 + 1.6 * math.cos((q.anim_time / 0.6) * 720)", 0])
a.expr("body", "rotation", ["6 + 5 * math.sin((q.anim_time / 0.6) * 360 + 90)", 0, 0])
a.expr("neck_1", "rotation", ["16 - 3 * math.sin((q.anim_time / 0.6) * 360 + 90)", 0, 0])
a.expr("neck_2", "rotation", ["12", 0, 0])
a.expr("neck_3", "rotation", ["8", 0, 0])
a.expr("head", "rotation", ["16 + 2 * math.sin((q.anim_time / 0.6) * 360)", 0, 0])
a.expr("crown", "rotation", ["6", 0, 0])
tail_wave(a, 2.5, 0.6, lag=0.06, amp_x=3, base_x=6)
a.fx(0.0, "step", "loc_claw_l")
a.fx(0.3, "step", "loc_foot_r")
a.sound(0.0, "step")
a.sound(0.3, "step")

a = anim("charge_impact", 1.6)
a.chain(["neck_1", "neck_2", "neck_3"], {0: (18, 0, 0), 0.12: (-26, 0, 0), 0.4: (-10, 0, 0), 0.7: (6, 0, 0), 1.6: (0, 0, 0)}, falloff=0.8)
a.rot("head", {0: (16, 0, 0), 0.12: (-24, 0, 0), 0.5: (-6, 8, 0), 0.7: (-6, -8, 0), 0.9: (-4, 6, 0), 1.1: (-2, -4, 0), 1.6: (0, 0, 0)}, mirror=False)
a.rot("body", {0: (8, 0, 0), 0.12: (-10, 0, 3), 0.5: (3, 0, -4), 0.8: (0, 0, 3), 1.6: (0, 0, 0)}, mirror=False)
a.pos("body", {0: (0, -2, 0), 0.12: (0, 1, 6), 0.5: (0, -2, 8), 1.6: (0, 0, 0)}, mirror=False)
legs_keys(a, {0: dict(fl=(-20, 10, 0), hl=(10, 0, 0)), 0.12: dict(fl=(-34, 10, 10), hl=(-10, 20, 10)),
              0.5: dict(fl=(10, 20, 0), hl=(-14, 26, 14), fr=(-6, 26, 6)), 1.0: dict(fl=(4, 8, 0), hl=(-6, 10, 4)), 1.6: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.rot("jaw", {0: (0, 0, 0), 0.15: (26, 0, 0), 0.6: (8, 0, 0), 1.2: (0, 0, 0)})
a.chain(TAIL, {0: (8, 0, 0), 0.15: (-8, 0, 0), 0.6: (4, 10, 0), 1.0: (0, -6, 0), 1.6: (0, 0, 0)}, falloff=1.06)
a.fx(0.05, "impact_burst", "loc_crown")
a.fx(0.6, "daze_stars", "loc_crown")

a = anim("tail_sweep", 1.8)
# windup 0-0.6 (tail coils to the left), sweep 0.6-1.0 (to the right, lag down the tail), recover
a.rot("pelvis", {0: (0, 0, 0), 0.6: (0, 18, 0), 0.8: (0, -22, 0), 1.0: (0, -26, 0), 1.8: (0, 0, 0)}, mirror=False)
a.rot("body", {0: (0, 0, 0), 0.6: (0, 10, -4), 0.8: (0, -12, 4), 1.1: (0, -10, 2), 1.8: (0, 0, 0)}, mirror=False)
a.rot("chest", {0: (0, 0, 0), 0.6: (0, -6, 0), 0.85: (0, 8, 0), 1.8: (0, 0, 0)}, mirror=False)
for i, b in enumerate(TAIL):
    lag = i * 0.03
    a.rot(b, {0: (0, 0, 0), 0.55: (4, 12 + i * 1.5, 0), 0.62 + lag: (6, 14 + i * 1.2, 0), 0.82 + lag: (2, -20 - i * 2.2, 0),
              1.0 + lag: (0, -16 - i * 1.5, 0), 1.8: (0, 0, 0)}, mirror=False)
a.chain(["neck_1", "neck_2", "head"], {0: (0, 0, 0), 0.6: (0, -12, 0), 0.85: (4, 14, 0), 1.8: (0, 0, 0)}, falloff=0.9)
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.6: dict(fl=(-4, 6, 0), hl=(-10, 14, 6), hr=(6, 0, 0)),
              0.85: dict(fl=(4, 0, 0), hl=(8, 0, 0), hr=(-12, 16, 8)), 1.8: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.fx(0.8, "tail_trail", "loc_tail_tip")
a.fx(0.9, "tail_trail", "loc_tail_tip")

a = anim("wing_pressure", 2.2)
a.rot("body", {0: (0, 0, 0), 0.6: (-24, 0, 0), 0.95: (-26, 0, 0), 1.1: (-12, 0, 0), 1.5: (0, 0, 0), 2.2: (0, 0, 0)})
a.pos("body", {0: (0, 0, 0), 0.6: (0, 6, 4), 0.95: (0, 7, 4), 1.1: (0, 3, 2), 1.5: (0, -1, 0), 2.2: (0, 0, 0)})
wings(a, {0: fold_keys(0.0), 0.6: {"arm": (0, 18, -46), "fore": (0, -20, 14), "hand": (0, 14, 8), "fingers": 10},
          0.9: {"arm": (0, 22, -50), "fore": (0, -24, 16), "hand": (0, 16, 10), "fingers": 12},
          1.05: {"arm": (0, -30, 30), "fore": (0, -6, 20), "hand": (0, -18, 18), "fingers": -6},
          1.4: {"arm": (0, -10, 10), "fore": (0, 0, 6), "hand": (0, 0, 4), "fingers": 0},
          2.2: {"arm": (0, 0, 0), "fore": (0, 0, 0), "hand": (0, 0, 0), "fingers": 0}})
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.6: dict(fl=(-30, 40, 30), hl=(20, -6, -16)),
              0.95: dict(fl=(-34, 44, 30), hl=(22, -8, -18)), 1.2: dict(fl=(-24, 20, 10), hl=(10, 0, -6)),
              1.5: dict(fl=(-4, 18, 4), hl=(-6, 12, 4)), 2.2: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.chain(["neck_1", "neck_2", "head"], {0: (0, 0, 0), 0.6: (14, 0, 0), 1.0: (24, 0, 0), 1.5: (4, 0, 0), 2.2: (0, 0, 0)}, falloff=0.8)
a.rot("jaw", {0: (0, 0, 0), 0.9: (30, 0, 0), 1.3: (10, 0, 0), 1.7: (0, 0, 0)})
a.chain(TAIL, {0: (0, 0, 0), 0.6: (14, 0, 0), 1.1: (4, 0, 0), 2.2: (0, 0, 0)}, falloff=1.04)
a.fx(1.0, "wing_gust", "loc_center")
a.fx(1.5, "dust_ring")

a = anim("cliff_dive", 1.0, loop=True)
a.expr("body", "rotation", ["14 + 2 * math.sin(q.anim_time * 360)", 0, 0])
a.expr("neck_1", "rotation", ["6", 0, 0])
a.expr("head", "rotation", ["10", 0, 0])
a.expr("jaw", "rotation", ["20 + 6 * math.sin(q.anim_time * 720)", 0, 0])
for b, v in (("wing_l_arm", (0, -30, -20)), ("wing_l_fore", (0, 50, 6)), ("wing_l_hand", (0, -40, 0))):
    a.expr(b, "rotation", [str(v[0]), str(v[1]), f"{v[2]} + 3 * math.sin(q.anim_time * 720)"])
legs_static(a, 0, fl=(-60, 20, -10), hl=(-30, 30, 10))
tail_wave(a, 2.0, 1.0, lag=0.05, base_x=6)

a = anim("skullbreaker", 3.2)
# brace 0-0.6, raise head 0.6-1.35, slam 1.35-1.55 (impact 1.55), stuck 1.55-2.2, recover 2.2-3.2
a.rot_lr("arm_l_upper", {0: (0, 0, 0), 0.6: (-12, 0, -14), 1.35: (-14, 0, -16), 1.55: (-6, 0, -16), 2.4: (-6, 0, -12), 3.2: (0, 0, 0)},
         {0: (0, 0, 0), 0.6: (-12, 0, -14), 1.35: (-14, 0, -16), 1.55: (-6, 0, -16), 2.4: (-6, 0, -12), 3.2: (0, 0, 0)})
legs_keys(a, {0: dict(hl=(0, 0, 0)), 0.6: dict(hl=(-14, 22, 10)), 1.35: dict(hl=(-20, 30, 14)), 1.55: dict(hl=(-8, 16, 6)), 3.2: dict(hl=(0, 0, 0))})
a.rot("body", {0: (0, 0, 0), 0.6: (-2, 0, 0), 1.35: (-14, 0, 0), 1.55: (12, 0, 0), 2.2: (10, 0, 0), 3.2: (0, 0, 0)})
a.pos("body", {0: (0, 0, 0), 0.6: (0, -2, 2), 1.35: (0, 3, 5), 1.55: (0, -4, -2), 2.2: (0, -4, -1), 3.2: (0, 0, 0)})
a.chain(["neck_1", "neck_2", "neck_3"], {0: (0, 0, 0), 0.6: (4, 0, 0), 1.35: (-30, 0, 0), 1.48: (10, 0, 0), 1.55: (26, 0, 0),
                                         2.2: (24, 0, 0), 3.2: (0, 0, 0)}, falloff=0.85)
a.rot("head", {0: (0, 0, 0), 1.35: (-28, 0, 0), 1.55: (34, 0, 0), 1.75: (30, 5, 0), 1.95: (32, -5, 0), 2.2: (30, 0, 0), 3.2: (0, 0, 0)}, mirror=False)
a.rot("crown", {0: (0, 0, 0), 1.35: (-8, 0, 0), 1.55: (4, 0, 0), 3.2: (0, 0, 0)})
a.rot("jaw", {0: (0, 0, 0), 1.0: (14, 0, 0), 1.4: (0, 0, 0), 2.4: (0, 0, 0), 2.7: (18, 0, 0), 3.2: (0, 0, 0)})
wings(a, {0: {"arm": (0, 0, 0), "fore": (0, 0, 0)}, 1.35: {"arm": (0, 6, -14), "fore": (0, 0, 0)}, 1.55: {"arm": (0, 0, 8), "fore": (0, 0, 0)}, 3.2: {"arm": (0, 0, 0), "fore": (0, 0, 0)}})
a.chain(TAIL, {0: (0, 0, 0), 1.35: (-6, 0, 0), 1.55: (16, 0, 0), 2.2: (6, 0, 0), 3.2: (0, 0, 0)}, falloff=1.05)
a.fx(1.55, "impact_burst", "loc_crown")
a.fx(1.56, "dust_ring")

# =========================================================================== REACTIONS
a = anim("hit_reaction", 0.5)
a.chain(["neck_1", "neck_2", "head"], {0: (0, 0, 0), 0.08: (-8, 6, 0), 0.25: (3, -2, 0), 0.5: (0, 0, 0)}, falloff=0.9)
a.rot("body", {0: (0, 0, 0), 0.08: (-3, 0, 3), 0.3: (1, 0, -1), 0.5: (0, 0, 0)}, mirror=False)
a.rot("jaw", {0: (0, 0, 0), 0.1: (14, 0, 0), 0.4: (0, 0, 0)})
a.rot("chest", {0: (0, 0, 0), 0.08: (-3, 0, 0), 0.3: (1, 0, 0), 0.5: (0, 0, 0)})
a.rot("crown", {0: (0, 0, 0), 0.08: (-5, 0, 0), 0.35: (0, 0, 0)})
a.chain(TAIL[:4], {0: (0, 0, 0), 0.1: (6, -4, 0), 0.35: (-2, 2, 0), 0.5: (0, 0, 0)}, falloff=1.1)
wings(a, {0: {"arm": (0, 0, 0)}, 0.1: {"arm": (0, 0, -6)}, 0.5: {"arm": (0, 0, 0)}})

a = anim("stagger", 2.4)
a.rot("body", {0: (0, 0, 0), 0.25: (6, 0, 10), 0.6: (4, 0, -8), 1.0: (8, 0, 8), 1.5: (6, 0, -4), 2.0: (2, 0, 2), 2.4: (0, 0, 0)}, mirror=False)
a.pos("body", {0: (0, 0, 0), 0.25: (0, -5, 0), 1.5: (0, -4, 0), 2.4: (0, 0, 0)}, mirror=False)
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.25: dict(fl=(10, 30, -10), fr=(-6, 10, 0), hl=(-14, 24, 10)),
              0.6: dict(fl=(-4, 10, 0), fr=(12, 30, -10), hl=(-10, 20, 8)), 1.5: dict(fl=(6, 20, -6), fr=(4, 16, -4), hl=(-12, 22, 10)),
              2.4: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
a.chain(["neck_1", "neck_2", "neck_3", "head"], {0: (0, 0, 0), 0.25: (20, 10, 0), 0.6: (16, -12, 0), 1.0: (22, 10, 0),
                                                 1.5: (18, -6, 0), 2.0: (8, 0, 0), 2.4: (0, 0, 0)}, falloff=0.8)
a.rot("jaw", {0: (0, 0, 0), 0.3: (24, 0, 0), 1.8: (16, 0, 0), 2.4: (0, 0, 0)})
wings(a, {0: {"arm": (0, 0, 0)}, 0.3: {"arm": (0, 0, 10)}, 2.0: {"arm": (0, 0, 6)}, 2.4: {"arm": (0, 0, 0)}})
a.chain(TAIL, {0: (0, 0, 0), 0.4: (-6, 8, 0), 1.0: (-6, -8, 0), 2.4: (0, 0, 0)}, falloff=1.04)
a.fx(0.3, "daze_stars", "loc_crown")

a = anim("skull_fracture", 2.0)
a.chain(["neck_1", "neck_2", "neck_3"], {0: (0, 0, 0), 0.1: (-24, 0, 0), 0.4: (-10, 0, 0), 1.0: (12, 0, 0), 1.6: (4, 0, 0), 2.0: (0, 0, 0)}, falloff=0.85)
a.rot("head", {0: (0, 0, 0), 0.1: (-20, 0, 0), 0.3: (-10, 18, 0), 0.5: (-10, -18, 0), 0.7: (-6, 14, 0), 0.9: (0, -10, 0), 1.2: (10, 0, 0), 2.0: (0, 0, 0)}, mirror=False)
a.rot("jaw", {0: (0, 0, 0), 0.12: (40, 0, 0), 1.0: (30, 0, 0), 1.6: (0, 0, 0)})
a.rot("crown", {0: (0, 0, 0), 0.1: (-14, 0, 0), 0.4: (6, 0, 0), 2.0: (0, 0, 0)})
a.rot("body", {0: (0, 0, 0), 0.1: (-8, 0, 0), 0.6: (4, 0, 4), 1.2: (6, 0, -2), 2.0: (0, 0, 0)}, mirror=False)
a.pos("body", {0: (0, 0, 0), 0.1: (0, 2, 4), 0.8: (0, -3, 2), 2.0: (0, 0, 0)}, mirror=False)
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.15: dict(fl=(-16, 10, 6), hl=(-6, 10, 4)), 0.8: dict(fl=(8, 24, -4), hl=(-12, 20, 8)), 2.0: dict(fl=(0, 0, 0), hl=(0, 0, 0))})
wings(a, {0: {"arm": (0, 0, 0), "fore": (0, 0, 0)}, 0.15: {"arm": (0, 8, -18), "fore": (0, -8, 6)}, 1.2: {"arm": (0, 0, 4), "fore": (0, 0, 0)}, 2.0: {"arm": (0, 0, 0), "fore": (0, 0, 0)}})
a.chain(TAIL, {0: (0, 0, 0), 0.15: (12, 0, 0), 0.6: (4, 10, 0), 1.2: (2, -8, 0), 2.0: (0, 0, 0)}, falloff=1.05)
a.fx(0.05, "skull_shards", "loc_crown")
a.fx(0.4, "daze_stars", "loc_crown")

a = anim("exhausted", 2.4, loop=True)
a.expr("body", "position", [0, "-3 + 1.1 * math.sin(q.anim_time / 1.2 * 360)", 0])
a.expr("body", "rotation", ["4 + 1.5 * math.sin(q.anim_time / 1.2 * 360 + 60)", 0, 0])
a.expr("neck_1", "rotation", ["14 + 2 * math.sin(q.anim_time / 1.2 * 360 + 90)", 0, 0])
a.expr("neck_2", "rotation", ["8", 0, 0])
a.expr("head", "rotation", ["10 + 3 * math.sin(q.anim_time / 1.2 * 360 + 120)", "3 * math.sin(q.anim_time / 2.4 * 360)", 0])
a.expr("jaw", "rotation", ["14 + 6 * math.sin(q.anim_time / 1.2 * 360 + 90)", 0, 0])
legs_static(a, 0, fl=(4, 18, -4), hl=(-12, 22, 10))
a.expr("wing_l_arm", "rotation", ["0", "0", "8 + 2 * math.sin(q.anim_time / 1.2 * 360)"])
tail_wave(a, 1.5, 2.4, lag=0.05, base_x=-3)
a.fx(0.3, "roar_breath", "loc_mouth")
a.fx(1.5, "roar_breath", "loc_mouth")

a = anim("death", 3.6, hold=True)
a.rot("root", {0: (0, 0, 0), 0.6: (6, 0, -4), 1.3: (8, 0, 10), 1.9: (6, 0, 76), 2.2: (6, 0, 82), 2.4: (6, 0, 78), 3.6: (6, 0, 80)}, mirror=False)
a.pos("root", {0: (0, 0, 0), 1.3: (0, -6, 0), 1.9: (-14, -8, 0), 2.2: (-18, -10, 0), 3.6: (-18, -10, 0)}, mirror=False)
legs_keys(a, {0: dict(fl=(0, 0, 0), hl=(0, 0, 0)), 0.6: dict(fl=(6, 30, -6), hl=(-10, 18, 8)), 1.3: dict(fl=(30, 60, -20), hl=(-20, 34, 14)),
              2.2: dict(fl=(-20, 30, 10), fr=(10, 40, 0), hl=(-30, 40, 20), hr=(10, 20, 10)), 3.6: dict(fl=(-24, 34, 12), fr=(14, 44, 4), hl=(-34, 44, 22), hr=(14, 24, 12))})
a.chain(["neck_1", "neck_2", "neck_3", "head"], {0: (0, 0, 0), 0.4: (-16, 0, 0), 1.3: (10, 0, 0), 1.9: (6, 0, -18), 2.15: (2, 0, -26),
                                                 2.35: (4, 0, -20), 3.6: (4, 0, -24)}, falloff=0.9)
a.rot("jaw", {0: (0, 0, 0), 0.4: (34, 0, 0), 1.2: (20, 0, 0), 2.3: (24, 0, 0), 3.6: (16, 0, 0)})
wings(a, {0: {"arm": (0, 0, 0), "fore": (0, 0, 0)}, 0.4: {"arm": (0, 10, -24), "fore": (0, -6, 10)},
          1.9: {"arm": (0, -10, 20), "fore": (0, 20, 10)}, 3.6: {"arm": (0, -14, 24), "fore": (0, 26, 14)}})
a.chain(TAIL, {0: (0, 0, 0), 0.4: (10, 0, 0), 1.9: (-4, 10, 0), 2.6: (0, -8, 0), 3.0: (0, 4, 0), 3.6: (0, 2, 0)}, falloff=1.04)
a.fx(2.2, "dust_ring")
a.sound(2.2, "land")

# small layers --------------------------------------------------------------------------
a = anim("wing_display", 1.0, loop=True)  # preview / future use: the display pose as a static layer
display_delta(a, 0, 1.0)

a = anim("injured_overlay", 1.6, loop=True)
a.expr("neck_1", "rotation", ["6 + 1.5 * math.sin(q.anim_time / 1.6 * 360)", 0, 0])
a.expr("jaw", "rotation", ["6 + 4 * math.sin(q.anim_time / 0.8 * 360)", 0, 0])
a.expr("body", "position", [0, "-1 + 0.6 * math.sin(q.anim_time / 0.8 * 360)", 0])
a.expr("wing_l_arm", "rotation", ["0", "0", "4"])

TIMINGS = {
    "roar": {"length": 2.4, "shout": 0.75},
    "idle_head_scan": {"length": 4.0},
    "claw_combo": {"length": 2.0, "hits": [0.55, 1.05], "telegraph": 0.15},
    "charge_windup": {"length": 1.4},
    "charge_impact": {"length": 1.6},
    "tail_sweep": {"length": 1.8, "hit_start": 0.62, "hit_end": 0.98},
    "wing_pressure": {"length": 2.2, "gust": 1.0},
    "takeoff": {"length": 1.2, "liftoff": 0.6},
    "landing": {"length": 1.0, "impact": 0.42},
    "jump": {"length": 1.0, "leave": 0.4, "land": 0.88},
    "skullbreaker": {"length": 3.2, "impact": 1.55},
    "hit_reaction": {"length": 0.5},
    "stagger": {"length": 2.4},
    "skull_fracture": {"length": 2.0},
    "death": {"length": 3.6},
}
for n, t in TIMINGS.items():
    assert abs(A[n].length - t["length"]) < 1e-6, n


# =========================================================================== codes shared with scripts
ANIM_CODES = ["none", "idle_head_scan", "roar", "claw_combo", "charge_windup", "charge", "charge_impact", "tail_sweep",
              "wing_pressure", "takeoff", "cliff_dive", "landing", "jump", "skullbreaker", "stagger", "skull_fracture",
              "exhausted", "death"]
FLIGHT_CODES = ["ground", "flap", "glide"]
GAIT_CODES = ["auto", "walk", "run"]
P_ANIM = "q.property('dragon_dominion:anim')"
P_FLIGHT = "q.property('dragon_dominion:flight')"
P_GAIT = "q.property('dragon_dominion:gait')"
P_PHASE = "q.property('dragon_dominion:phase')"
for n in ANIM_CODES[1:]:
    assert n in A, n


def code(n):
    return ANIM_CODES.index(n)


# wing fold target per action (1 = folded on the back, 0 = fully spread as authored)
FOLD_TARGET = {"takeoff": 0.0, "landing": 0.0, "wing_pressure": 0.0, "cliff_dive": 0.35,
               "skull_fracture": 0.7, "death": 0.85}
# display stance weight on top of the fold (1 = the reference's raised, draped wings); 0 = tight fold
DISPLAY_OFF = ["charge_windup", "charge", "charge_impact", "takeoff", "landing", "wing_pressure", "cliff_dive", "death"]


def fold_expr():
    e = "1.0"
    for n, v in sorted(FOLD_TARGET.items(), key=lambda kv: -code(kv[0])):
        e = f"({P_ANIM} == {code(n)} ? {v} : {e})"
    return f"v.fold_t = {P_FLIGHT} > 0 ? 0.0 : {e};"


def disp_expr():
    off = " || ".join(f"{P_ANIM} == {code(n)}" for n in DISPLAY_OFF)
    return f"v.disp_t = ({P_FLIGHT} > 0 || {off}) ? 0.0 : (v.running ? 0.2 : (v.walking ? 0.85 : 1.0));"


PRE_ANIMATION = [
    f"v.busy = {P_ANIM} > 0;",
    fold_expr(),
    # critically damped ease toward the targets: no snapping when a state changes
    "v.fold_v = (v.fold_v ?? 0.0) + ((v.fold_t - (v.fold ?? 1.0)) * 36.0 - (v.fold_v ?? 0.0) * 12.0) * math.min(q.delta_time, 0.05);",
    "v.fold = math.clamp((v.fold ?? 1.0) + v.fold_v * math.min(q.delta_time, 0.05), 0.0, 1.0);",
    "v.yaw_d = q.body_y_rotation - (v.last_yaw ?? q.body_y_rotation);",
    "v.yaw_d = v.yaw_d > 180 ? v.yaw_d - 360 : (v.yaw_d < -180 ? v.yaw_d + 360 : v.yaw_d);",
    "v.last_yaw = q.body_y_rotation;",
    "v.turn = math.lerp(v.turn ?? 0.0, v.yaw_d / math.max(q.delta_time, 0.016), math.min(1.0, q.delta_time * 5.0));",
    "v.turn_dir = math.clamp(v.turn / 60.0, -1.0, 1.0);",
    f"v.walking = {P_GAIT} == 1 || ({P_GAIT} == 0 && q.ground_speed > 0.3);",
    f"v.running = {P_GAIT} == 2 || ({P_GAIT} == 0 && q.ground_speed > 4.5);",
    disp_expr(),
    "v.disp_v = (v.disp_v ?? 0.0) + ((v.disp_t - (v.disp ?? 1.0)) * 25.0 - (v.disp_v ?? 0.0) * 10.0) * math.min(q.delta_time, 0.05);",
    "v.disp = math.clamp((v.disp ?? 1.0) + v.disp_v * math.min(q.delta_time, 0.05), 0.0, 1.0);",
    f"v.injured = math.lerp(v.injured ?? 0.0, ({P_PHASE} >= 3 && !v.busy) ? 1.0 : 0.0, math.min(1.0, q.delta_time * 2.0));",
]
ANIMATE = ["locomotion", "action", {"wing_fold": "v.fold"}, {"wing_display": "v.disp"}, "flinch",
           {"injured_overlay": "v.injured"}]


def controllers():
    C = {}
    B = 0.4
    C["controller.animation.dragon_dominion.gharvok.locomotion"] = {"initial_state": "idle", "states": {
        "idle": {"animations": ["idle_breathing"], "blend_transition": B, "transitions": [
            {"flap": f"{P_FLIGHT} == 1"}, {"glide": f"{P_FLIGHT} == 2"},
            {"run": "!v.busy && v.running"}, {"walk": "!v.busy && v.walking"},
            {"turn": "!v.busy && math.abs(v.turn) > 30"}]},
        "walk": {"animations": ["walk"], "blend_transition": B, "transitions": [
            {"idle": f"v.busy || !v.walking || {P_FLIGHT} > 0"}, {"run": "v.running"}]},
        "run": {"animations": ["run"], "blend_transition": B, "transitions": [
            {"idle": f"v.busy || {P_FLIGHT} > 0 || (!v.running && !v.walking)"}, {"walk": "!v.running"}]},
        "turn": {"animations": ["turn"], "blend_transition": 0.3, "transitions": [
            {"idle": f"v.busy || {P_FLIGHT} > 0 || math.abs(v.turn) < 10"}, {"walk": "v.walking"}]},
        "flap": {"animations": [{"wing_flap": "!v.busy"}], "blend_transition": 0.35, "transitions": [
            {"idle": f"{P_FLIGHT} == 0"}, {"glide": f"{P_FLIGHT} == 2"}]},
        "glide": {"animations": [{"glide": "!v.busy"}], "blend_transition": 0.4, "transitions": [
            {"idle": f"{P_FLIGHT} == 0"}, {"flap": f"{P_FLIGHT} == 1"}]},
    }}
    states = {"none": {"transitions": [{n: f"{P_ANIM} == {code(n)}"} for n in ANIM_CODES[1:]]}}
    for n in ANIM_CODES[1:]:
        states[n] = {"animations": [n], "blend_transition": 0.3 if n not in ("death",) else 0.4,
                     "transitions": [{"none": f"{P_ANIM} != {code(n)}"}]}
    C["controller.animation.dragon_dominion.gharvok.action"] = {"initial_state": "none", "states": states}
    C["controller.animation.dragon_dominion.gharvok.flinch"] = {"initial_state": "calm", "states": {
        "calm": {"transitions": [{"flinch": "q.hurt_time > 0 && !v.busy && q.is_alive"}]},
        "flinch": {"animations": ["hit_reaction"], "blend_transition": 0.15,
                   "transitions": [{"calm": "q.all_animations_finished || v.busy"}]},
    }}
    return {"format_version": "1.10.0", "animation_controllers": C}


def write_timings():
    out = os.path.join(BP, "scripts", "dragons", "gharvok")
    os.makedirs(out, exist_ok=True)
    lines = ["// GENERATED by tools/gen_anims.py - do not edit. Animation codes and keyframe timings (seconds),",
             "// shared by the client animations and the combat scripts so hits land on the drawn frame.",
             f"export const ANIM = Object.freeze({json.dumps({n: i for i, n in enumerate(ANIM_CODES)})});",
             f"export const FLIGHT = Object.freeze({json.dumps({n: i for i, n in enumerate(FLIGHT_CODES)})});",
             f"export const GAIT = Object.freeze({json.dumps({n: i for i, n in enumerate(GAIT_CODES)})});",
             f"export const TIMINGS = Object.freeze({json.dumps(TIMINGS, indent=2)});", ""]
    with open(os.path.join(out, "timings.js"), "w") as f:
        f.write("\n".join(lines))
    with open(os.path.join(HERE, ".anim.json"), "w") as f:
        json.dump({"anims": list(A), "animate": ANIMATE, "pre_animation": PRE_ANIMATION,
                   "controllers": ["locomotion", "action", "flinch"], "codes": ANIM_CODES,
                   "flight": FLIGHT_CODES, "gait": GAIT_CODES}, f, indent=1)

# write -------------------------------------------------------------------------------
def write():
    os.makedirs(os.path.join(RP, "animations"), exist_ok=True)
    data = {"format_version": "1.8.0", "animations": {f"{NS}.{n}": a.json() for n, a in A.items()}}
    with open(os.path.join(RP, "animations", "gharvok.animation.json"), "w") as f:
        json.dump(data, f, indent=1)
    os.makedirs(os.path.join(RP, "animation_controllers"), exist_ok=True)
    with open(os.path.join(RP, "animation_controllers", "gharvok.animation_controllers.json"), "w") as f:
        json.dump(controllers(), f, indent=1)
    write_timings()
    print(f"{len(A)} animations, 3 controllers")


if __name__ == "__main__":
    write()
