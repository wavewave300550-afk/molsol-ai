#!/usr/bin/env python3
"""Writes the hand-keyed animations (player skill poses, Oath Grizzly, Grizzly Shade).

Style: anime action timing - anticipation (wind-up) -> very fast strike -> short impact hold ->
follow-through -> recovery, with smooth catmull-rom curves.

Timings here must stay in sync with scripts-src/config.ts:
  * Ultimate: the grizzly spawns 4 ticks after the cast and its paws hit the ground 1.75 s later
    (tick 39), exactly when the player's axe slam lands (1.95 s into `ult`).
  * Relentless Pursuit: the dash takes 5 ticks (0.25 s), the slam lands at 0.33 s.

Player animations are played from script with Entity.playAnimation(), so nothing overrides the
vanilla player. First- and third-person keyframes are separate (Molang v.is_first_person); the
first-person poses were tuned with tools/hold_sim.py so the axe never covers the crosshair.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANIM = os.path.join(ROOT, "addon", "resource_packs", "grizzly_oath", "animations")
FP = "v.is_first_person"
Z = (0, 0, 0)


def val(fp, tp):
    if fp == tp:
        return fp
    return f"{FP} ? {fp} : {tp}"


def key(v, smooth=True):
    v = list(v)
    return {"post": v, "lerp_mode": "catmullrom"} if smooth else v


def channel(keys, smooth=True):
    return {f"{t:.2f}": key(v, smooth) for t, v in keys}


def arm(*keys):
    """keys: (time, fp_xyz, tp_xyz) for the right arm (holds the axe)."""
    return {"rotation": channel([(t, [val(a, b) for a, b in zip(fp, tp)]) for t, fp, tp in keys])}


def tp(*keys, field="rotation"):
    """Third-person only (body / head / legs / left arm). In first person these stay still."""
    return {field: channel([(t, [val(0, x) for x in xyz]) for t, xyz in keys])}


def rot(*keys):
    return {"rotation": channel(list(keys))}


RAISED_FP = (15, -10, -40)  # axe lifted at the right of the screen
SLAM_FP = (40, 5, 30)  # axe driven down out of the bottom-right
SLAM2_FP = (44, 7, 33)


def player_animations():
    a = {}
    # Frontier Cleave: heavy forehand (right->left) / backhand (left->right), alternated by script.
    a["animation.grizzly_oath.player.cleave_r"] = {
        "animation_length": 0.45,
        "bones": {
            "rightArm": arm((0.0, Z, (-40, 0, 10)), (0.07, (-8, -15, -4), (-165, -10, 35)), (0.12, (-10, -17, -6), (-170, -8, 32)),
                            (0.19, (35, 10, 35), (-20, 40, -35)), (0.26, (38, 12, 38), (-10, 45, -40)), (0.45, Z, Z)),
            "body": tp((0.0, Z), (0.07, (0, -20, 0)), (0.19, (8, 28, 0)), (0.26, (8, 30, 0)), (0.45, Z)),
            "head": tp((0.0, Z), (0.07, (0, -10, 0)), (0.19, (5, 12, 0)), (0.45, Z)),
            "leftArm": tp((0.0, Z), (0.07, (-30, 0, -20)), (0.19, (20, 0, -10)), (0.45, Z)),
            "rightLeg": tp((0.0, Z), (0.19, (12, 0, 0)), (0.45, Z)),
            "leftLeg": tp((0.0, Z), (0.19, (-16, 0, 0)), (0.45, Z)),
        },
    }
    a["animation.grizzly_oath.player.cleave_l"] = {
        "animation_length": 0.45,
        "bones": {
            "rightArm": arm((0.0, Z, (-40, 0, 0)), (0.07, (-20, 15, 0), (-120, 40, -35)), (0.12, (-22, 16, -2), (-135, 45, -40)),
                            (0.19, (20, 40, 20), (-35, -35, 35)), (0.26, (22, 42, 22), (-30, -40, 40)), (0.45, Z, Z)),
            "body": tp((0.0, Z), (0.07, (0, 20, 0)), (0.19, (8, -28, 0)), (0.26, (8, -30, 0)), (0.45, Z)),
            "head": tp((0.0, Z), (0.07, (0, 10, 0)), (0.19, (5, -12, 0)), (0.45, Z)),
            "leftArm": tp((0.0, Z), (0.07, (20, 0, -10)), (0.19, (-30, 0, -20)), (0.45, Z)),
            "rightLeg": tp((0.0, Z), (0.19, (-14, 0, 0)), (0.45, Z)),
            "leftLeg": tp((0.0, Z), (0.19, (12, 0, 0)), (0.45, Z)),
        },
    }
    # Grizzly Rend: coil, then a wide horizontal sweep with a deep stance.
    a["animation.grizzly_oath.player.rend"] = {
        "animation_length": 0.6,
        "bones": {
            "rightArm": arm((0.0, Z, (-60, 40, 0)), (0.1, (-5, -28, -5), (-95, 75, 0)), (0.16, (-8, -30, -8), (-100, 78, 0)),
                            (0.26, (0, 25, 15), (-85, -80, 0)), (0.33, (2, 27, 17), (-80, -85, 5)), (0.6, Z, Z)),
            "leftArm": tp((0.0, Z), (0.1, (-30, 0, -25)), (0.26, (-10, 0, 25)), (0.6, Z)),
            "body": tp((0.0, Z), (0.1, (0, 40, 0)), (0.26, (6, -45, 0)), (0.33, (6, -48, 0)), (0.6, Z)),
            "head": tp((0.0, Z), (0.1, (0, -15, 0)), (0.26, (0, 20, 0)), (0.6, Z)),
            "rightLeg": tp((0.0, Z), (0.26, (18, 0, 6)), (0.6, Z)),
            "leftLeg": tp((0.0, Z), (0.26, (-22, 0, -6)), (0.6, Z)),
        },
    }
    # Relentless Pursuit: sprinting lean with the axe cocked overhead, then a crushing slam.
    a["animation.grizzly_oath.player.pursuit"] = {
        "animation_length": 0.8,
        "bones": {
            "rightArm": arm((0.0, RAISED_FP, (-170, 0, 15)), (0.28, RAISED_FP, (-180, 0, 15)), (0.33, SLAM_FP, (-20, 0, 0)),
                            (0.4, SLAM2_FP, (-10, 0, 0)), (0.8, Z, Z)),
            "leftArm": tp((0.0, (50, 0, -15)), (0.28, (55, 0, -15)), (0.33, (-40, 0, -15)), (0.8, Z)),
            "body": tp((0.0, (16, 0, 0)), (0.28, (16, 0, 0)), (0.33, (30, 0, 0)), (0.4, (32, 0, 0)), (0.8, Z)),
            "head": tp((0.0, (-20, 0, 0)), (0.33, (-10, 0, 0)), (0.8, Z)),
            "rightLeg": tp((0.0, (-40, 0, 0)), (0.28, (-35, 0, 0)), (0.33, (-28, 0, 0)), (0.8, Z)),
            "leftLeg": tp((0.0, (35, 0, 0)), (0.28, (30, 0, 0)), (0.33, (25, 0, 0)), (0.8, Z)),
        },
    }
    # Unbroken Will: axe raised to the sky, roaring, chest out, wide stance.
    shake = "math.sin(q.anim_time * 1800) * 3"
    a["animation.grizzly_oath.player.will"] = {
        "animation_length": 1.4,
        "bones": {
            "rightArm": arm((0.0, Z, Z), (0.18, RAISED_FP, (-182, 0, 8)), (0.3, RAISED_FP, (-176, 0, 10)), (1.05, RAISED_FP, (-176, 0, 10)), (1.4, Z, Z)),
            "leftArm": tp((0.0, Z), (0.18, (-20, 0, -38)), (1.05, (-20, 0, -38)), (1.4, Z)),
            "head": {"rotation": channel([(0.0, [0, 0, 0]), (0.18, [val(0, f"-28 + {shake}"), 0, 0]), (1.05, [val(0, f"-26 + {shake}"), 0, 0]), (1.4, [0, 0, 0])])},
            "body": tp((0.0, Z), (0.18, (-12, 0, 0)), (1.05, (-10, 0, 0)), (1.4, Z)),
            "rightLeg": tp((0.0, Z), (0.18, (0, 0, 9)), (1.05, (0, 0, 9)), (1.4, Z)),
            "leftLeg": tp((0.0, Z), (0.18, (0, 0, -9)), (1.05, (0, 0, -9)), (1.4, Z)),
        },
    }
    # Oath of the Grizzly: raise the burning axe, tremble with power while the grizzly roars,
    # then slam at 1.95 s together with the grizzly's paws.
    tremble = "math.sin(q.anim_time * 2400) * 2"
    a["animation.grizzly_oath.player.ult"] = {
        "animation_length": 2.5,
        "bones": {
            "rightArm": {"rotation": channel([
                (0.0, [0, 0, 0]),
                (0.3, [val(15, -178), val(-10, 0), val(-40, 10)]),
                (1.0, [val(f"15 + {tremble}", f"-182 + {tremble}"), val(-10, 0), val(-40, 12)]),
                (1.7, [val(12, -195), val(-12, 0), val(-45, 15)]),
                (1.95, [val(40, -15), val(5, 0), val(30, 0)]),
                (2.05, [val(44, -10), val(7, 0), val(33, 0)]),
                (2.5, [0, 0, 0]),
            ])},
            "leftArm": tp((0.0, Z), (0.3, (-35, 0, -35)), (1.7, (-35, 0, -35)), (1.95, (-60, 0, -10)), (2.5, Z)),
            "head": tp((0.0, Z), (0.3, (-25, 0, 0)), (1.7, (-25, 0, 0)), (1.95, (10, 0, 0)), (2.5, Z)),
            "body": tp((0.0, Z), (0.3, (-6, 0, 0)), (1.7, (-15, 0, 0)), (1.95, (35, 0, 0)), (2.05, (38, 0, 0)), (2.5, Z)),
            "rightLeg": tp((0.0, Z), (1.7, (5, 0, 6)), (1.95, (-25, 0, 0)), (2.05, (-26, 0, 0)), (2.5, Z)),
            "leftLeg": tp((0.0, Z), (1.7, (-5, 0, -6)), (1.95, (20, 0, 0)), (2.05, (22, 0, 0)), (2.5, Z)),
        },
    }
    return a


def oath_grizzly_animation():
    # Bear faces -Z. Negative X on `body` rears the front up (same sign vanilla polar bears use).
    roar_y = "math.sin(q.anim_time * 1900) * 7"
    roar_x = "math.sin(q.anim_time * 2600) * 4"
    breathe = "math.sin(q.anim_time * 400) * 2"
    return {
        "animation.oath_grizzly.ultimate": {
            "animation_length": 3.2,
            "bones": {
                "root": {
                    "position": channel([(0.0, [0, -34, 0]), (0.38, [0, 2, 0]), (0.5, [0, 0, 0]), (1.75, [0, 0, 0]), (1.82, [0, -2.5, 0]),
                                         (2.1, [0, 0, 0]), (2.55, [0, 0, 0]), (3.15, [0, -40, 0])]),
                    "scale": channel([(0.0, [0.55, 0.55, 0.55]), (0.38, [1.05, 1.05, 1.05]), (0.5, [1, 1, 1]), (1.75, [1, 1, 1]),
                                      (1.82, [1.06, 0.93, 1.06]), (2.0, [1, 1, 1]), (2.55, [1, 1, 1]), (3.15, [0.6, 0.6, 0.6])]),
                },
                "body": rot((0.0, [0, 0, 0]), (0.45, [-8, 0, 0]), (0.8, [-58, 0, 0]), (0.92, [-67, 0, 0]), (1.02, [-62, 0, 0]),
                            (1.45, [f"-64 + {breathe}", 0, 0]), (1.55, [-70, 0, 0]), (1.67, [-82, 0, 0]), (1.75, [6, 0, 0]),
                            (1.85, [3, 0, 0]), (2.1, [2, 0, 0]), (2.55, [0, 0, 0])),
                "head": rot((0.0, [0, 0, 0]), (0.45, [10, 0, 0]), (0.85, [38, 0, 0]), (1.0, [f"18 + {roar_x}", roar_y, 0]),
                            (1.45, [f"24 + {roar_x}", roar_y, 0]), (1.62, [40, 0, 0]), (1.75, [-18, 0, 0]), (2.1, [-5, 0, 0]), (2.55, [0, 0, 0])),
                "jaw": rot((0.0, [0, 0, 0]), (0.8, [0, 0, 0]), (0.95, [42, 0, 0]), (1.45, [f"40 + {roar_x}", 0, 0]), (1.6, [10, 0, 0]),
                           (1.75, [32, 0, 0]), (2.0, [30, 0, 0]), (2.3, [0, 0, 0])),
                "arm_l": rot((0.0, [0, 0, 0]), (0.85, [-35, 0, -25]), (1.5, [-50, 0, -30]), (1.66, [-100, 0, -15]), (1.75, [28, 0, 0]),
                             (1.85, [24, 0, 0]), (2.1, [10, 0, 0]), (2.55, [0, 0, 0])),
                "arm_r": rot((0.0, [0, 0, 0]), (0.85, [-35, 0, 25]), (1.5, [-50, 0, 30]), (1.66, [-100, 0, 15]), (1.75, [28, 0, 0]),
                             (1.85, [24, 0, 0]), (2.1, [10, 0, 0]), (2.55, [0, 0, 0])),
                "leg_l": rot((0.0, [0, 0, 0]), (0.85, [8, 0, 0]), (1.75, [-4, 0, 0]), (2.1, [0, 0, 0])),
                "leg_r": rot((0.0, [0, 0, 0]), (0.85, [8, 0, 0]), (1.75, [-4, 0, 0]), (2.1, [0, 0, 0])),
                "tail": rot((0.0, [0, 0, 0]), (0.85, [30, "math.sin(q.anim_time * 900) * 15", 0]), (1.75, [0, 0, 0])),
            },
        }
    }


def shade_animation():
    roar = "math.sin(q.anim_time * 2200) * 5"
    return {
        "animation.grizzly_shade.roar": {
            "animation_length": 3.0,
            "bones": {
                "root": {
                    "position": channel([(0.0, [0, -24, 0]), (0.35, [0, 1.5, 0]), (0.45, [0, 0, 0]), (2.3, [0, 0, 0]), (2.9, [0, -30, 0])]),
                    "scale": channel([(0.0, [0.6, 0.6, 0.6]), (0.35, [1.05, 1.05, 1.05]), (0.45, [1, 1, 1]), (2.3, [1, 1, 1]), (2.9, [0.5, 0.5, 0.5])]),
                },
                "body": rot((0.0, [0, 0, 0]), (0.4, [-10, 0, 0]), (0.72, [-58, 0, 0]), (0.82, [-54, 0, 0]), (2.1, [-56, 0, 0]), (2.6, [0, 0, 0])),
                "head": rot((0.0, [0, 0, 0]), (0.72, [32, 0, 0]), (0.85, [f"16 + {roar}", roar, 0]), (1.9, [f"20 + {roar}", roar, 0]), (2.6, [0, 0, 0])),
                "jaw": rot((0.0, [0, 0, 0]), (0.7, [0, 0, 0]), (0.85, [42, 0, 0]), (1.8, [40, 0, 0]), (2.0, [0, 0, 0])),
                "arm_l": rot((0.0, [0, 0, 0]), (0.72, [-45, 0, -32]), (2.1, [-40, 0, -30]), (2.6, [0, 0, 0])),
                "arm_r": rot((0.0, [0, 0, 0]), (0.72, [-45, 0, 32]), (2.1, [-40, 0, 30]), (2.6, [0, 0, 0])),
            },
        }
    }


def write(name, anims):
    os.makedirs(ANIM, exist_ok=True)
    with open(os.path.join(ANIM, name), "w", encoding="utf-8") as fh:
        json.dump({"format_version": "1.10.0", "animations": anims}, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    write("grizzly_oath.player.animation.json", player_animations())
    write("oath_grizzly.animation.json", oath_grizzly_animation())
    write("grizzly_shade.animation.json", shade_animation())
    print("animations written")
