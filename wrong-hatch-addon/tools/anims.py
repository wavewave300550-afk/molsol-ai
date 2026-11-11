"""
Animations + animation controllers for The Wrong Hatch and its minions.

Key frames are written in *ticks* and converted to seconds. Positions are in
model units (1/8 block) and converted to geometry units (x2). Rotations are
Bedrock euler degrees added on top of the rest pose. Right-side values are
mirrored automatically to the left side (y and z rotation negated).
"""
from __future__ import annotations

from spec import ACTION_ID, ACTION_LEN, ACTIONS

SCALE = 2.0          # model units -> geometry units
T = "query.anim_time"
LT = "query.life_time"


def sec(tick: float) -> str:
    return f"{tick / 20.0:.2f}"


def track(frames: dict, *, pos: bool = False, smooth: bool = True):
    """frames: {tick: (x, y, z) | number}  ->  Bedrock keyframe dict."""
    out = {}
    for t in sorted(frames):
        v = frames[t]
        if isinstance(v, (int, float)):
            v = [v, v, v]
        v = [round(x * SCALE, 3) if (pos and isinstance(x, (int, float))) else x for x in v]
        out[sec(t)] = {"post": list(v), "lerp_mode": "catmullrom"} if smooth else list(v)
    return out


def mirror(v):
    if isinstance(v, (int, float)):
        return v
    x, y, z = v
    neg = lambda a: (-a if isinstance(a, (int, float)) else f"-({a})")  # noqa: E731
    return (x, neg(y), neg(z))


class A:
    """Builder for one animation."""

    def __init__(self, length=None, loop=False):
        self.data = {"loop": loop, "bones": {}}
        if length:
            self.data["animation_length"] = round(length / 20.0, 2)
        self.sounds = {}

    def _b(self, bone):
        return self.data["bones"].setdefault(bone, {})

    def rot(self, bone, frames, both=False):
        self._b(bone)["rotation"] = track(frames) if isinstance(frames, dict) else list(frames)
        if both:
            left = bone.replace("_r", "_l")
            if isinstance(frames, dict):
                self._b(left)["rotation"] = track({t: mirror(v) for t, v in frames.items()})
            else:
                self._b(left)["rotation"] = list(mirror(tuple(frames)))
        return self

    def pos(self, bone, frames):
        if isinstance(frames, dict):
            self._b(bone)["position"] = track(frames, pos=True)
        else:
            self._b(bone)["position"] = [x * SCALE if isinstance(x, (int, float)) else f"({x}) * {SCALE}" for x in frames]
        return self

    def scale(self, bone, frames):
        self._b(bone)["scale"] = track(frames) if isinstance(frames, dict) else frames
        return self

    def sound(self, tick, effect):
        self.data.setdefault("sound_effects", {})[sec(tick)] = {"effect": effect}
        return self

    def build(self):
        return self.data


ZERO = (0, 0, 0)
SPREAD = (0, -90, 38)        # full span (~9.6 blocks)
RAISED = (0, -60, 140)       # guillotine wind-up, blades over the back
WRAP = (-10, 95, -18)        # wings wrapped around the body


def boss_animations() -> dict:
    an = {}
    # ------------------------------------------------------------------ locomotion / ambient
    an["idle"] = {"loop": True, "bones": {
        "body": {"position": [0, f"math.sin({LT} * 110) * 0.5", 0]},
        "neck": {"rotation": [f"math.sin({LT} * 90) * 2", 0, 0]},
        "head": {"rotation": [f"math.sin({LT} * 70) * 3", f"math.sin({LT} * 37) * 8 + (math.sin({LT} * 23) > 0.92 ? 18 : 0)",
                              f"math.sin({LT} * 53) * 4"]},
        "wattle": {"rotation": [f"math.sin({LT} * 160) * 6", 0, f"math.sin({LT} * 120) * 5"]},
        "comb": {"rotation": [0, 0, f"math.sin({LT} * 180) * 2"]},
        "core": {"scale": f"1 + math.sin({LT} * 200) * (0.03 + variable.phase * 0.02)"},
        "fan": {"rotation": [f"math.sin({LT} * 60) * 3", 0, 0]},
        "wing_r": {"rotation": [0, 0, f"math.sin({LT} * 80) * 2"]},
        "wing_l": {"rotation": [0, 0, f"-math.sin({LT} * 80) * 2"]},
        **{f"sickle_{s}{i}": {"rotation": [f"math.sin({LT} * 70 - {i * 30}) * {1 + i * 0.6}", 0, 0]}
           for s in "rl" for i in range(1, 7)},
        **{f"curl_{s}{i}": {"rotation": [f"math.sin({LT} * 85 - {i * 40}) * {1 + i * 0.8}", 0, 0]}
           for s in "rl" for i in range(1, 5)},
    }}
    walk = "query.modified_distance_moved * 22"
    spd = "math.min(1, query.modified_move_speed * 1.6)"
    an["walk"] = {"loop": True, "bones": {
        "leg_r": {"rotation": [f"math.cos({walk}) * 32 * {spd}", 0, 0]},
        "leg_l": {"rotation": [f"-math.cos({walk}) * 32 * {spd}", 0, 0]},
        "foot_r": {"rotation": [f"math.max(0, -math.sin({walk})) * 26 * {spd}", 0, 0]},
        "foot_l": {"rotation": [f"math.max(0, math.sin({walk})) * 26 * {spd}", 0, 0]},
        "body": {"position": [0, f"math.abs(math.sin({walk})) * 1.2 * {spd}", 0],
                 "rotation": [f"4 * {spd}", 0, f"math.sin({walk}) * 3 * {spd}"]},
        # the chicken head bob: thrust forward, then hold while the body catches up
        "neck": {"position": [0, 0, f"(math.sin({walk} * 2) * -1.6 - 0.6) * {spd} * {SCALE}"]},
        "wing_r": {"rotation": [0, 0, f"math.sin({walk}) * 4 * {spd}"]},
        "wing_l": {"rotation": [0, 0, f"math.sin({walk}) * 4 * {spd}"]},
        "tail": {"rotation": [0, f"math.sin({walk}) * 5 * {spd}", 0]},
    }}
    an["turn"] = {"loop": True, "bones": {
        "leg_r": {"rotation": [f"math.sin({LT} * 720) * 16 * math.clamp(math.abs(query.yaw_speed) / 6, 0, 1)", 0, 0]},
        "leg_l": {"rotation": [f"-math.sin({LT} * 720) * 16 * math.clamp(math.abs(query.yaw_speed) / 6, 0, 1)", 0, 0]},
    }}
    an["look"] = {"loop": True, "bones": {
        "head": {"rotation": ["math.clamp(query.target_x_rotation, -30, 30) * 0.6",
                              "math.clamp(query.target_y_rotation, -50, 50) * 0.7", 0]},
    }}
    an["hurt"] = {"loop": True, "bones": {
        "body": {"rotation": ["-math.min(query.hurt_time, 6) * 1.4", 0, "math.sin(query.hurt_time * 160) * 2"]},
        "head": {"rotation": ["-math.min(query.hurt_time, 6) * 3", 0, 0]},
        "wattle": {"rotation": ["math.sin(query.hurt_time * 200) * 12", 0, 0]},
    }}

    # ------------------------------------------------------------------ actions
    a = A(60)
    a.pos("root", {0: (0, -9, 0), 30: (0, -6, 0), 38: (0, 2, 0), 46: ZERO})
    a.rot("body", {0: (45, 0, 0), 30: (34, 0, 0), 40: (-14, 0, 0), 60: ZERO})
    a.rot("wing_r", {0: WRAP, 34: WRAP, 41: SPREAD, 52: (0, -80, 55), 60: ZERO}, both=True)
    a.rot("neck", {0: (40, 0, 0), 34: (36, 0, 0), 41: (-28, 0, 0), 54: (-20, 0, 0), 60: ZERO})
    a.rot("jaw", {0: ZERO, 39: ZERO, 43: (32, 0, 0), 54: (30, 0, 0), 60: ZERO})
    a.scale("core", {0: 0.6, 38: 1.0, 41: 1.5, 50: 1.0})
    a.sound(40, "crow")
    an["intro"] = a

    a = A(24)
    a.rot("neck", {0: ZERO, 9: (-26, 0, 0), 13: (48, 0, 0), 17: (40, 0, 0), 24: ZERO})
    a.pos("neck", {0: ZERO, 9: (0, 1, 3), 13: (0, -3, -6), 17: (0, -2, -5), 24: ZERO})
    a.rot("body", {0: ZERO, 9: (-6, 0, 0), 13: (12, 0, 0), 24: ZERO})
    a.rot("jaw", {0: ZERO, 8: (25, 0, 0), 12: (2, 0, 0), 24: ZERO})
    a.sound(12, "peck")
    an["peck"] = a

    a = A(44)
    frames_n, frames_p, frames_y = {0: ZERO}, {0: ZERO}, {0: ZERO}
    for i, hit in enumerate((12, 24, 36)):
        side = (-1, 1, 0)[i]
        frames_n[hit - 4] = (-24, side * 10, 0)
        frames_n[hit] = (46, side * 14, 0)
        frames_p[hit - 4] = (0, 1, 3)
        frames_p[hit] = (0, -3, -6)
        frames_y[hit] = (0, side * 8, 0)
    frames_n[44], frames_p[44], frames_y[44] = ZERO, ZERO, ZERO
    a.rot("neck", frames_n).pos("neck", frames_p).rot("body", frames_y)
    a.rot("jaw", {0: ZERO, 8: (24, 0, 0), 12: ZERO, 20: (24, 0, 0), 24: ZERO, 32: (24, 0, 0), 36: ZERO, 44: ZERO})
    for h in (11, 23, 35):
        a.sound(h, "peck")
    an["peck_combo"] = a

    def guillotine(a, start, hit):
        a.rot("wing_r", {start: ZERO, start + 16: RAISED, start + 20: (0, -50, 150), hit + 1: (0, -100, 40),
                         hit + 5: (0, -105, 18)}, both=True)
        a.sound(start + 6, "wing_whoosh")
        a.sound(hit, "guillotine")

    a = A(36)
    guillotine(a, 0, 22)
    a.data["bones"]["wing_r"]["rotation"][sec(36)] = {"post": [0, 0, 0], "lerp_mode": "catmullrom"}
    a.data["bones"]["wing_l"]["rotation"][sec(36)] = {"post": [0, 0, 0], "lerp_mode": "catmullrom"}
    a.rot("body", {0: ZERO, 16: (-14, 0, 0), 23: (18, 0, 0), 30: (10, 0, 0), 36: ZERO})
    a.pos("root", {0: ZERO, 16: (0, 1, 1.5), 23: (0, -1, -2.5), 36: ZERO})
    a.rot("neck", {0: ZERO, 16: (-24, 0, 0), 23: (22, 0, 0), 36: ZERO})
    a.rot("jaw", {0: ZERO, 14: (28, 0, 0), 24: (10, 0, 0), 36: ZERO})
    an["guillotine"] = a

    a = A(52)
    guillotine(a, 0, 22)
    a.data["bones"]["wing_r"]["rotation"].update(track({30: RAISED, 36: SPREAD, 44: SPREAD, 52: ZERO}))
    a.data["bones"]["wing_l"]["rotation"].update(track({30: mirror(RAISED), 36: mirror(SPREAD), 44: mirror(SPREAD), 52: ZERO}))
    a.rot("root", {0: ZERO, 32: ZERO, 44: (0, 360, 0), 52: (0, 360, 0)}, )
    a.rot("body", {0: ZERO, 16: (-14, 0, 0), 23: (18, 0, 0), 30: (-6, 0, 0), 38: (10, 0, 0), 52: ZERO})
    a.sound(34, "wing_whoosh")
    an["guillotine_double"] = a

    a = A(30)
    a.rot("body", {0: ZERO, 6: (20, 0, 0), 26: (18, 0, 0), 30: ZERO})
    a.rot("neck", {0: ZERO, 6: (22, 0, 0), 26: (20, 0, 0), 30: ZERO})
    a.rot("leg_r", {0: ZERO, 6: (-30, 0, 0), 10: (52, 0, 0), 13: (-24, 0, 0), 16: (58, 0, 0), 22: (-10, 0, 0), 30: ZERO})
    a.rot("leg_l", {0: ZERO, 8: (10, 0, 0), 12: (40, 0, 0), 18: (-8, 0, 0), 30: ZERO})
    a.rot("tail", {0: ZERO, 6: (-14, 0, 0), 26: (-14, 0, 0), 30: ZERO})
    a.sound(10, "scratch").sound(16, "scratch")
    an["back_scratch"] = a

    a = A(26)
    for i in range(1, 7):
        a.rot(f"sickle_r{i}", {0: ZERO, 8: (-8, 0, 0), 22: (-8, 0, 0), 26: ZERO}, both=True)
    a.rot("root", {0: ZERO, 10: (0, -20, 0), 22: (0, 360, 0), 26: (0, 360, 0)})
    a.rot("wing_r", {0: ZERO, 10: (0, -40, 30), 22: (0, -40, 30), 26: ZERO}, both=True)
    a.rot("body", {0: ZERO, 10: (8, 0, -6), 22: (8, 0, -6), 26: ZERO})
    a.sound(12, "wing_whoosh")
    an["sickle_sweep"] = a

    a = A(40)
    a.pos("root", {0: ZERO, 10: (0, -3, 0), 15: (0, 8, 0), 19: (0, 9, 0), 22: (0, -2, 0), 28: (0, -1, 0), 40: ZERO})
    a.rot("body", {0: ZERO, 10: (14, 0, 0), 16: (-12, 0, 0), 22: (26, 0, 0), 30: (18, 0, 0), 40: ZERO})
    a.rot("wing_r", {0: ZERO, 10: (0, -30, 70), 17: (0, -70, 120), 22: (0, -85, 14), 32: (0, -60, 10), 40: ZERO}, both=True)
    a.rot("leg_r", {0: ZERO, 10: (-20, 0, 0), 16: (35, 0, 0), 22: (-10, 0, 0), 40: ZERO}, both=True)
    a.rot("neck", {0: ZERO, 16: (-24, 0, 0), 22: (30, 0, 0), 40: ZERO})
    a.sound(12, "wing_whoosh")
    an["broodquake"] = a

    a = A(40)
    a.pos("root", {0: ZERO, 10: (0, -2, 0), 36: (0, -2, 0), 40: ZERO})
    a.rot("body", {0: ZERO, 10: (-20, 0, 0), 36: (-20, 0, 0), 40: ZERO})
    a.rot("neck", {0: ZERO, 10: (-26, 0, 0), 36: (-24, 0, 0), 40: ZERO})
    a.rot("jaw", {0: ZERO, 12: (30, 0, 0), 36: (30, 0, 0), 40: ZERO})
    a.rot("wing_r", {0: ZERO, 10: (0, -30, 40), 36: (0, -30, 40), 40: ZERO}, both=True)
    core = {0: 1.0}
    for t in (16, 22, 28, 34):
        core[t - 3] = 1.25
        core[t] = 0.9
    core[40] = 1.0
    a.scale("core", core)
    an["egg_mortar"] = a

    a = A(32)
    a.scale("body", {0: 1.0, 14: 1.07, 18: 0.96, 24: 1.0, 32: 1.0})
    a.rot("wing_r", {0: ZERO, 14: (0, -20, 38), 18: (0, -75, 28), 24: (0, -60, 20), 32: ZERO}, both=True)
    a.rot("wing_r_primaries", {0: ZERO, 14: (-20, 0, 20), 18: ZERO}, both=True)
    a.rot("body", {0: ZERO, 14: (-10, 0, 0), 18: (10, 0, 0), 32: ZERO})
    a.rot("fan", {0: ZERO, 14: (-18, 0, 0), 20: ZERO})
    a.sound(4, "fluff")
    an["feather_volley"] = a

    a = A(16)
    a.rot("wing_r", {0: ZERO, 16: WRAP}, both=True)
    a.rot("neck", {0: ZERO, 16: (34, 0, 0)}).pos("neck", {0: ZERO, 16: (0, -3, 2)})
    a.pos("root", {0: ZERO, 16: (0, -3, 0)})
    a.rot("fan", {0: ZERO, 16: (24, 0, 0)})
    a.sound(2, "shell_close")
    an["fortress_enter"] = a

    an["fortress_hold"] = {"loop": True, "bones": {
        "wing_r": {"rotation": [WRAP[0], WRAP[1], f"{WRAP[2]} + math.sin({T} * 900) * 0.8"]},
        "wing_l": {"rotation": [WRAP[0], -WRAP[1], f"{-WRAP[2]} - math.sin({T} * 900) * 0.8"]},
        "neck": {"rotation": [34, 0, 0], "position": [0, -3 * SCALE, 2 * SCALE]},
        "root": {"position": [f"math.sin({T} * 1300) * 0.15", -3 * SCALE, 0]},
        "fan": {"rotation": [24, 0, 0]},
        "core": {"scale": f"1.05 + math.sin({T} * 400) * 0.08"},
    }}

    a = A(20)
    a.rot("wing_r", {0: WRAP, 6: (0, -40, 30), 9: (0, -90, 70), 14: (0, -80, 50), 20: ZERO}, both=True)
    a.rot("neck", {0: (34, 0, 0), 8: (-20, 0, 0), 20: ZERO})
    a.pos("root", {0: (0, -3, 0), 8: (0, 1.5, 0), 20: ZERO})
    a.scale("body", {0: 1.0, 8: 1.12, 12: 1.0})
    an["fortress_burst"] = a

    an["stunned"] = {"loop": True, "animation_length": 1.5, "bones": {
        "neck": {"rotation": [f"20 + math.sin({T} * 240) * 6", 0, f"math.sin({T} * 120) * 16"]},
        "head": {"rotation": [0, f"math.sin({T} * 240) * 10", f"math.sin({T} * 120) * 12"]},
        "jaw": {"rotation": [f"16 + math.sin({T} * 480) * 6", 0, 0]},
        "body": {"rotation": [8, 0, f"math.sin({T} * 120) * 5"]},
        "root": {"position": [0, -1.5 * SCALE, 0]},
        "wing_r": {"rotation": [6, 0, -6]},
        "wing_l": {"rotation": [6, 0, 6]},
        "comb": {"rotation": [0, 0, f"math.sin({T} * 240) * 8"]},
    }}

    a = A(50)
    a.rot("body", {0: ZERO, 18: (-24, 0, 0), 40: (-22, 0, 0), 50: ZERO})
    a.rot("neck", {0: ZERO, 18: (-40, 0, 0), 24: (-46, 0, 0), 40: (-42, 0, 0), 50: ZERO})
    a.rot("jaw", {0: ZERO, 20: (36, 0, 0), 40: (34, 0, 0), 50: ZERO})
    a.rot("wing_r", {0: ZERO, 18: (0, -80, 70), 24: (0, -90, 62), 40: (0, -85, 66), 50: ZERO}, both=True)
    a.pos("root", {0: ZERO, 18: (0, 1, 0), 40: (0, 1, 0), 50: ZERO})
    a.rot("comb", {0: ZERO, 24: (0, 0, 8), 28: (0, 0, -8), 32: (0, 0, 6), 36: ZERO})
    a.scale("core", {0: 1.0, 22: 1.4, 26: 1.0})
    a.sound(22, "crow")
    an["crow"] = a

    a = A(44)
    a.pos("root", {0: ZERO, 10: (0, -3, 0), 40: (0, -3, 0), 44: ZERO})
    a.rot("body", {0: ZERO, 10: (12, 0, 0), 40: (12, 0, 0), 44: ZERO})
    tail = {0: ZERO}
    for t in (20, 26, 32, 38):
        tail[t - 3] = (-18, 0, 0)
        tail[t] = (6, 0, 0)
    tail[44] = ZERO
    a.rot("tail", tail)
    a.rot("neck", {0: ZERO, 12: (-10, 50, 0), 40: (-10, 50, 0), 44: ZERO})
    a.rot("wing_r", {0: ZERO, 10: (0, 0, 22), 40: (0, 0, 22), 44: ZERO}, both=True)
    an["rotten_hatch"] = a

    a = A(30)
    a.rot("body", {0: ZERO, 6: (22, 0, 0), 30: (24, 0, 0)})
    a.rot("neck", {0: ZERO, 6: (30, 0, 0), 30: (34, 0, 0)}).pos("neck", {0: ZERO, 30: (0, -2, -2)})
    a.rot("leg_r", {0: ZERO, 4: (-25, 0, 0), 7: (45, 0, 0), 12: (-25, 0, 0), 15: (45, 0, 0), 20: ZERO})
    a.rot("leg_l", {0: ZERO, 8: (-25, 0, 0), 11: (45, 0, 0), 16: (-25, 0, 0), 19: (45, 0, 0), 24: ZERO})
    a.rot("wing_r", {0: ZERO, 10: (20, 0, 18), 30: (24, 0, 20)}, both=True)
    a.rot("jaw", {0: ZERO, 22: ZERO, 25: (30, 0, 0), 30: (20, 0, 0)})
    a.sound(6, "scratch").sound(14, "scratch").sound(24, "cluck")
    an["rush_windup"] = a

    an["rush_charge"] = {"loop": True, "animation_length": 0.4, "bones": {
        "body": {"rotation": [26, 0, f"math.sin({T} * 900) * 3"]},
        "neck": {"rotation": [36, 0, 0], "position": [0, -2 * SCALE, -2 * SCALE]},
        "leg_r": {"rotation": [f"math.sin({T} * 900) * 55", 0, 0]},
        "leg_l": {"rotation": [f"-math.sin({T} * 900) * 55", 0, 0]},
        "wing_r": {"rotation": [24, 0, f"24 + math.sin({T} * 1800) * 8"]},
        "wing_l": {"rotation": [24, 0, f"-24 - math.sin({T} * 1800) * 8"]},
        "root": {"position": [0, f"math.abs(math.sin({T} * 900)) * 1.5 * {SCALE}", 0]},
        "jaw": {"rotation": [22, 0, 0]},
    }}

    a = A(28)
    a.rot("body", {0: ZERO, 20: (-20, 0, 0), 28: (-18, 0, 0)})
    a.rot("neck", {0: ZERO, 20: (-34, 0, 0), 28: (-30, 0, 0)})
    a.rot("jaw", {0: ZERO, 18: (34, 0, 0)})
    a.rot("wing_r", {0: ZERO, 20: (0, -70, 44), 28: (0, -72, 46)}, both=True)
    a.scale("core", {0: 1.0, 26: 1.55, 28: 1.5})
    a.sound(0, "charge")
    an["beam_charge"] = a

    an["beam_fire"] = {"loop": True, "animation_length": 1.0, "bones": {
        "body": {"rotation": [f"-14 + math.sin({T} * 1400) * 1.2", 0, 0]},
        "neck": {"rotation": [-26, 0, 0]},
        "jaw": {"rotation": [34, 0, 0]},
        "wing_r": {"rotation": [0, -72, f"46 + math.sin({T} * 1100) * 2"]},
        "wing_l": {"rotation": [0, 72, f"-46 - math.sin({T} * 1100) * 2"]},
        "core": {"scale": f"1.5 + math.sin({T} * 2600) * 0.08"},
    }}

    a = A(54)
    a.scale("core", {0: 1.0, 6: 1.3, 12: 1.0, 24: 1.4, 30: 1.05, 42: 1.6, 48: 2.0, 52: 1.0})
    a.rot("wing_r", {0: ZERO, 18: (0, -40, 40), 36: (0, -70, 50), 48: (0, -90, 48), 54: ZERO}, both=True)
    a.rot("body", {0: ZERO, 36: (-16, 0, 0), 48: (-24, 0, 0), 54: ZERO})
    a.rot("neck", {0: ZERO, 36: (-20, 0, 0), 48: (-36, 0, 0), 54: ZERO})
    a.sound(0, "pulse").sound(18, "pulse").sound(36, "pulse")
    an["dawn_flash"] = a

    a = A(36)
    a.rot("neck", {0: ZERO, 14: (-38, 0, 0), 30: (-36, 0, 0), 36: ZERO})
    a.rot("jaw", {0: ZERO, 16: (34, 0, 0), 30: (30, 0, 0), 36: ZERO})
    a.scale("core", {0: 1.0, 18: 1.35, 22: 0.9, 36: 1.0})
    a.rot("skirt", {0: ZERO, 18: (0, 0, 4), 20: (0, 0, -4), 22: (0, 0, 3), 24: ZERO})
    a.rot("wing_r", {0: ZERO, 14: (0, -40, 50), 30: (0, -40, 50), 36: ZERO}, both=True)
    a.sound(14, "crow")
    an["brood_call"] = a

    a = A(24)
    a.pos("root", {0: ZERO, 6: (0, -2.5, 0), 18: ZERO, 20: (0, -1.5, 0), 24: ZERO})
    a.rot("wing_r", {0: ZERO, 6: (0, -60, 95), 9: (0, -80, 10), 12: (0, -70, 95), 15: (0, -80, 10), 24: ZERO}, both=True)
    a.rot("leg_r", {0: ZERO, 8: (30, 0, 0), 16: (30, 0, 0), 20: ZERO}, both=True)
    a.sound(8, "flap")
    an["wing_hop"] = a

    a = A(20)
    a.rot("wing_r", {0: ZERO, 4: (0, -70, 110), 8: (0, -85, 15), 12: (0, -70, 110), 16: (0, -85, 15), 20: (0, -70, 100)},
          both=True)
    a.rot("leg_r", {0: ZERO, 10: (40, 0, 0), 20: (40, 0, 0)}, both=True)
    a.sound(4, "flap").sound(12, "flap")
    an["sky_rise"] = a

    an["sky_hover"] = {"loop": True, "animation_length": 0.6, "bones": {
        "wing_r": {"rotation": [0, -78, f"62 + math.sin({T} * 600) * 48"]},
        "wing_l": {"rotation": [0, 78, f"-62 - math.sin({T} * 600) * 48"]},
        "leg_r": {"rotation": [-10, 0, 0]}, "leg_l": {"rotation": [-10, 0, 0]},
        "foot_r": {"rotation": [f"20 + math.sin({T} * 600) * 6", 0, 0]},
        "foot_l": {"rotation": [f"20 + math.sin({T} * 600) * 6", 0, 0]},
        "body": {"rotation": [-8, 0, 0]},
        "neck": {"rotation": [24, 0, 0]},
    }}

    a = A(10)
    a.rot("wing_r", {0: (0, -78, 80), 6: (40, -10, 20), 10: (40, -10, 20)}, both=True)
    a.rot("body", {0: (-8, 0, 0), 6: (36, 0, 0), 10: (36, 0, 0)})
    a.rot("leg_r", {0: (-10, 0, 0), 6: (-50, 0, 0), 10: (-50, 0, 0)}, both=True)
    a.sound(0, "wing_whoosh")
    an["sky_dive"] = a

    a = A(20)
    a.pos("root", {0: (0, -4, 0), 8: (0, -1, 0), 20: ZERO})
    a.rot("body", {0: (24, 0, 0), 20: ZERO})
    a.rot("wing_r", {0: (0, -85, 12), 10: (0, -60, 10), 20: ZERO}, both=True)
    a.rot("neck", {0: (30, 0, 0), 20: ZERO})
    an["land_slam"] = a

    an["molt_storm"] = {"loop": True, "animation_length": 1.0, "bones": {
        "root": {"rotation": [0, f"{T} * 720", 0]},
        "wing_r": {"rotation": [0, -90, f"34 + math.sin({T} * 1440) * 6"]},
        "wing_l": {"rotation": [0, 90, f"-34 - math.sin({T} * 1440) * 6"]},
        "body": {"rotation": [6, 0, 0]},
        "neck": {"rotation": [-10, 0, 0]},
        "fan": {"rotation": [-20, 0, 0]},
    }}

    a = A(16)
    a.scale("body", {0: 1.0, 4: 0.92, 6: 1.18, 11: 1.0})
    a.rot("wing_r", {0: ZERO, 4: (0, 20, -10), 6: (0, -90, 70), 12: (0, -60, 30), 16: ZERO}, both=True)
    a.rot("fan", {0: ZERO, 6: (-30, 0, 0), 16: ZERO})
    a.sound(5, "molt")
    an["molt_burst"] = a

    an["final_hatch"] = {"loop": True, "animation_length": 2.0, "bones": {
        "root": {"position": [f"math.sin({T} * 2200) * 0.3", -4 * SCALE, f"math.cos({T} * 1900) * 0.3"]},
        "wing_r": {"rotation": [WRAP[0], WRAP[1], f"{WRAP[2]} + math.sin({T} * 1600) * 3"]},
        "wing_l": {"rotation": [WRAP[0], -WRAP[1], f"{-WRAP[2]} - math.sin({T} * 1600) * 3"]},
        "neck": {"rotation": [f"-30 + math.sin({T} * 300) * 6", 0, f"math.sin({T} * 1100) * 4"]},
        "jaw": {"rotation": [30, 0, 0]},
        "body": {"rotation": [f"-10 + math.sin({T} * 2400) * 1.5", 0, 0]},
        "core": {"scale": f"1.5 + math.sin({T} * 720) * 0.25"},
        "fan": {"rotation": [-24, 0, 0]},
    }}

    a = A(30)
    a.rot("wing_r", {0: WRAP, 8: (0, -40, 50), 10: (0, -90, 75), 18: (0, -85, 60), 30: ZERO}, both=True)
    a.scale("core", {0: 1.5, 8: 2.2, 12: 1.0, 30: 1.0})
    a.pos("root", {0: (0, -4, 0), 10: (0, 2, 0), 30: ZERO})
    a.rot("neck", {0: (-30, 0, 0), 10: (-45, 0, 0), 30: ZERO})
    a.rot("jaw", {0: (30, 0, 0), 12: (38, 0, 0), 30: ZERO})
    a.sound(8, "nova")
    an["hatch_nova"] = a

    a = A(100)
    a.rot("body", {0: ZERO, 10: (8, 0, 10), 20: (4, 0, -12), 30: (10, 0, 8), 50: (14, 0, -4), 80: (18, 0, 3),
                   92: (22, 0, -2), 100: (34, 0, 0)})
    a.pos("root", {0: ZERO, 30: ZERO, 50: (0, -4, 0), 90: (0, -4.5, 0), 100: (0, -6, 0)})
    a.rot("leg_r", {0: ZERO, 30: ZERO, 50: (60, 0, 8), 100: (70, 0, 10)}, both=True)
    a.rot("wing_r", {0: ZERO, 30: (10, 0, -6), 60: (20, 0, 20), 90: (24, 0, 26), 100: (0, -80, 50)}, both=True)
    a.rot("neck", {0: ZERO, 20: (-20, 0, 10), 40: (30, 0, -14), 70: (40, 0, 18), 100: (50, 0, 0)})
    a.rot("jaw", {0: ZERO, 10: (30, 0, 0), 60: (24, 0, 0), 100: (36, 0, 0)})
    a.scale("core", {0: 1.0, 60: 1.3, 90: 1.8, 96: 2.4, 100: 0.2})
    a.sound(0, "crow")
    an["death"] = a

    out = {}
    for name, val in an.items():
        out[f"animation.wrong_hatch.{name}"] = val.build() if isinstance(val, A) else val
    # sanity: every action except none has an animation
    for name, ln, _ in ACTIONS:
        if name != "none":
            assert f"animation.wrong_hatch.{name}" in out, name
            if ln:
                assert abs(out[f"animation.wrong_hatch.{name}"]["animation_length"] - ln / 20) < 0.01, name
    return out


def boss_controller() -> dict:
    states = {"default": {"transitions": [
        {name: f"query.property('wh:anim') == {ACTION_ID[name]}"} for name, _, _ in ACTIONS if name != "none"
    ], "blend_transition": 0.15}}
    for name, ln, _ in ACTIONS:
        if name == "none":
            continue
        states[name] = {
            "animations": [name],
            "transitions": [{"default": f"query.property('wh:anim') != {ACTION_ID[name]}"}],
            "blend_transition": 0.12,
        }
    return {"controller.animation.wrong_hatch.action": {"initial_state": "default", "states": states}}


def minion_animations() -> dict:
    lt = LT
    walk = "query.modified_distance_moved * 40"
    spd = "math.min(1, query.modified_move_speed * 2)"
    return {
        "animation.wrong_hatch.chick.move": {"loop": True, "bones": {
            "leg_r": {"rotation": [f"math.cos({walk}) * 40 * {spd}", 0, 0]},
            "leg_l": {"rotation": [f"-math.cos({walk}) * 40 * {spd}", 0, 0]},
            "head": {"rotation": [f"math.sin({lt} * 400) * 6 * {spd}", f"math.sin({lt} * 90) * 10", 0]},
            "wing_r": {"rotation": [0, 0, f"(math.sin({lt} * 1500) * 30 + 30) * {spd}"]},
            "wing_l": {"rotation": [0, 0, f"-(math.sin({lt} * 1500) * 30 + 30) * {spd}"]},
            "body": {"position": [0, f"math.abs(math.sin({walk})) * 0.8 * {spd}", 0]},
        }},
        "animation.wrong_hatch.chick.fuse": {"loop": True, "bones": {
            "body": {"scale": f"1 + math.abs(math.sin({lt} * 1200)) * 0.18"},
            "wing_r": {"rotation": [0, 0, f"math.sin({lt} * 3000) * 40 + 40"]},
            "wing_l": {"rotation": [0, 0, f"-math.sin({lt} * 3000) * 40 - 40"]},
        }},
        "animation.wrong_hatch.egg.wobble": {"loop": True, "bones": {
            "egg": {"rotation": [f"math.sin({lt} * 700) * math.min({lt} * 6, 10)", 0,
                                 f"math.cos({lt} * 520) * math.min({lt} * 6, 12)"],
                    "scale": f"1 + math.max(0, math.sin({lt} * 900)) * math.min({lt} * 0.03, 0.08)"},
        }},
        "animation.wrong_hatch.egg.lobbed": {"loop": True, "bones": {
            "egg": {"rotation": [f"{lt} * 720", f"{lt} * 300", 0], "scale": 0.7},
        }},
        "animation.wrong_hatch.brood_shell.pulse": {"loop": True, "bones": {
            "egg": {"rotation": [f"math.sin({lt} * 500) * 2", 0, f"math.cos({lt} * 430) * 2"],
                    "scale": f"1 + math.sin({lt} * 360) * 0.03"},
            "yolk": {"scale": f"1 + math.abs(math.sin({lt} * 360)) * 0.1"},
        }},
        "animation.wrong_hatch.feather_dart.fly": {"loop": True, "bones": {
            "body": {"rotation": ["-query.target_x_rotation", 0, f"{lt} * 900"]},
        }},
    }


def minion_controller() -> dict:
    return {"controller.animation.wrong_hatch.chick": {"initial_state": "default", "states": {
        "default": {"animations": ["move"],
                    "transitions": [{"fuse": "query.property('wh:fuse') == true"}]},
        "fuse": {"animations": ["move", "fuse"],
                 "transitions": [{"default": "query.property('wh:fuse') == false"}]},
    }}}


ANIMATED_BOSS_BONES_OK = True
_ = ACTION_LEN
