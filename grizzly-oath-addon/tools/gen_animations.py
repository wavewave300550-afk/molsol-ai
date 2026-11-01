#!/usr/bin/env python3
"""Writes the hand-keyed animations (player skill poses, Oath Grizzly, Grizzly Shade).

Timings here must stay in sync with scripts-src/config.ts:
  * Ultimate: the grizzly spawns 4 ticks after the cast and its paws hit the ground 1.75 s later
    (tick 39), which is exactly when the player's axe slam lands (1.95 s into `ult`).
  * Relentless Pursuit: the dash takes 5 ticks (0.25 s), the slam lands at 0.35 s.

Player animations are played from script with Entity.playAnimation(), so nothing overrides the
vanilla player. First-person and third-person keyframes are separate (Molang v.is_first_person).
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANIM = os.path.join(ROOT, "addon", "resource_packs", "grizzly_oath", "animations")
FP = "v.is_first_person"


def raw_rot(*keys):
    return {"rotation": {f"{t:.2f}": [x, y, z] for t, x, y, z in keys}}


def val(fp, tp):
    """Keyframe component: first-person value vs third-person value."""
    if fp == tp:
        return fp
    return f"{FP} ? {fp} : {tp}"


def arm(*keys):
    """keys: (time, fp_xyz, tp_xyz). First-person poses were tuned with tools/hold_sim.py so the axe
    stays in the lower-right of the screen and never covers the crosshair."""
    return {"rotation": {f"{t:.2f}": [val(a, b) for a, b in zip(fp, tp)] for t, fp, tp in keys}}


def tp_only(*keys):
    """Body / head / left arm move in third person only (rotating them in first person would swing
    the whole first-person arm across the screen)."""
    return {"rotation": {f"{t:.2f}": [val(0, v) for v in xyz] for t, xyz in keys}}


Z = (0, 0, 0)
RAISED_FP = (15, -10, -40)  # axe lifted at the right of the screen
SLAM_FP = (40, 5, 30)  # axe driven down out of the bottom-right


def player_animations():
    a = {}
    # Frontier Cleave: heavy forehand (right) / backhand (left) slashes, alternated by script.
    a["animation.grizzly_oath.player.cleave_r"] = {
        "animation_length": 0.4,
        "bones": {
            "rightArm": arm((0.0, (-15, -22, -8), (-150, -10, 35)), (0.06, (-18, -25, -10), (-165, -5, 30)),
                            (0.16, (35, 10, 35), (-25, 35, -30)), (0.4, Z, Z)),
            "body": tp_only((0.0, (0, -15, 0)), (0.16, (0, 25, 0)), (0.4, Z)),
        },
    }
    a["animation.grizzly_oath.player.cleave_l"] = {
        "animation_length": 0.4,
        "bones": {
            "rightArm": arm((0.0, (-35, 0, -25), (-120, 40, -35)), (0.06, (-38, 2, -28), (-135, 45, -40)),
                            (0.16, (20, 40, 20), (-35, -35, 35)), (0.4, Z, Z)),
            "body": tp_only((0.0, (0, 20, 0)), (0.16, (0, -25, 0)), (0.4, Z)),
        },
    }
    # Grizzly Rend: wide horizontal sweep.
    a["animation.grizzly_oath.player.rend"] = {
        "animation_length": 0.55,
        "bones": {
            "rightArm": arm((0.0, (-5, -28, -5), (-95, 70, 0)), (0.12, (-8, -30, -8), (-100, 75, 0)),
                            (0.25, (-35, 0, -25), (-80, -75, 0)), (0.55, Z, Z)),
            "leftArm": tp_only((0.0, (-20, 0, -20)), (0.55, Z)),
            "body": tp_only((0.0, (0, 35, 0)), (0.25, (0, -40, 0)), (0.55, Z)),
        },
    }
    # Relentless Pursuit: axe cocked overhead during the dash, then a crushing overhead slam.
    a["animation.grizzly_oath.player.pursuit"] = {
        "animation_length": 0.75,
        "bones": {
            "rightArm": arm((0.0, RAISED_FP, (-170, 0, 15)), (0.28, RAISED_FP, (-175, 0, 15)),
                            (0.36, SLAM_FP, (-20, 0, 0)), (0.75, Z, Z)),
            "leftArm": tp_only((0.0, (40, 0, -10)), (0.36, (-30, 0, -10)), (0.75, Z)),
            "body": tp_only((0.0, (10, 0, 0)), (0.28, (15, 0, 0)), (0.36, (35, 0, 0)), (0.75, Z)),
        },
    }
    # Unbroken Will: axe raised to the sky, chest out, head up.
    a["animation.grizzly_oath.player.will"] = {
        "animation_length": 1.3,
        "bones": {
            "rightArm": arm((0.0, Z, Z), (0.2, RAISED_FP, (-175, 0, 10)), (1.05, RAISED_FP, (-175, 0, 10)), (1.3, Z, Z)),
            "leftArm": tp_only((0.0, Z), (0.2, (-15, 0, -25)), (1.05, (-15, 0, -25)), (1.3, Z)),
            "head": tp_only((0.0, Z), (0.2, (-25, 0, 0)), (1.05, (-25, 0, 0)), (1.3, Z)),
            "body": tp_only((0.0, Z), (0.2, (-8, 0, 0)), (1.05, (-8, 0, 0)), (1.3, Z)),
        },
    }
    # Oath of the Grizzly: raise the burning axe, hold while the grizzly roars, slam at 1.95 s.
    a["animation.grizzly_oath.player.ult"] = {
        "animation_length": 2.5,
        "bones": {
            "rightArm": arm((0.0, Z, Z), (0.3, RAISED_FP, (-175, 0, 10)), (1.7, (12, -12, -45), (-185, 0, 15)),
                            (1.95, SLAM_FP, (-15, 0, 0)), (2.5, Z, Z)),
            "leftArm": tp_only((0.0, Z), (0.3, (-30, 0, -30)), (1.7, (-30, 0, -30)), (1.95, (-50, 0, -10)), (2.5, Z)),
            "head": tp_only((0.0, Z), (0.3, (-20, 0, 0)), (1.7, (-20, 0, 0)), (1.95, (5, 0, 0)), (2.5, Z)),
            "body": tp_only((0.0, Z), (1.7, (-10, 0, 0)), (1.95, (30, 0, 0)), (2.5, Z)),
        },
    }
    return a


def oath_grizzly_animation():
    # Bear faces -Z. Negative X on `body` rears the front up (same sign vanilla polar bears use).
    return {
        "animation.oath_grizzly.ultimate": {
            "animation_length": 3.2,
            "bones": {
                "root": {
                    "position": {"0.00": [0, -34, 0], "0.45": [0, 0, 0], "2.55": [0, 0, 0], "3.15": [0, -40, 0]},
                    "scale": {"0.00": 0.55, "0.45": 1.0, "2.55": 1.0, "3.15": 0.6},
                },
                "body": raw_rot((0.0, 0, 0, 0), (0.45, -8, 0, 0), (0.85, -62, 0, 0), (1.5, -66, 0, 0),
                                (1.62, -74, 0, 0), (1.75, 12, 0, 0), (2.0, 6, 0, 0), (2.55, 0, 0, 0)),
                "head": raw_rot((0.0, 0, 0, 0), (0.45, 10, 0, 0), (0.85, 38, 0, 0), (1.0, 20, 0, 0), (1.45, 24, 0, 0),
                                (1.62, 40, 0, 0), (1.75, -15, 0, 0), (2.1, -5, 0, 0), (2.55, 0, 0, 0)),
                "jaw": raw_rot((0.0, 0, 0, 0), (0.8, 0, 0, 0), (0.95, 38, 0, 0), (1.45, 38, 0, 0), (1.6, 10, 0, 0),
                               (1.75, 30, 0, 0), (2.0, 30, 0, 0), (2.3, 0, 0, 0)),
                "arm_l": raw_rot((0.0, 0, 0, 0), (0.85, -35, 0, -25), (1.5, -50, 0, -30), (1.62, -95, 0, -15),
                                 (1.75, 25, 0, 0), (2.1, 10, 0, 0), (2.55, 0, 0, 0)),
                "arm_r": raw_rot((0.0, 0, 0, 0), (0.85, -35, 0, 25), (1.5, -50, 0, 30), (1.62, -95, 0, 15),
                                 (1.75, 25, 0, 0), (2.1, 10, 0, 0), (2.55, 0, 0, 0)),
                "leg_l": raw_rot((0.0, 0, 0, 0), (0.85, 8, 0, 0), (1.75, 0, 0, 0)),
                "leg_r": raw_rot((0.0, 0, 0, 0), (0.85, 8, 0, 0), (1.75, 0, 0, 0)),
                "tail": raw_rot((0.0, 0, 0, 0), (0.85, 30, 0, 0), (1.75, 0, 0, 0)),
            },
        }
    }


def shade_animation():
    return {
        "animation.grizzly_shade.roar": {
            "animation_length": 3.0,
            "bones": {
                "root": {
                    "position": {"0.00": [0, -24, 0], "0.40": [0, 0, 0], "2.30": [0, 0, 0], "2.90": [0, -30, 0]},
                    "scale": {"0.00": 0.6, "0.40": 1.0, "2.30": 1.0, "2.90": 0.5},
                },
                "body": raw_rot((0.0, 0, 0, 0), (0.4, -10, 0, 0), (0.75, -55, 0, 0), (2.1, -58, 0, 0), (2.6, 0, 0, 0)),
                "head": raw_rot((0.0, 0, 0, 0), (0.75, 32, 0, 0), (0.85, 18, 0, 0), (1.9, 22, 0, 0), (2.6, 0, 0, 0)),
                "jaw": raw_rot((0.0, 0, 0, 0), (0.7, 0, 0, 0), (0.85, 40, 0, 0), (1.8, 40, 0, 0), (2.0, 0, 0, 0)),
                "arm_l": raw_rot((0.0, 0, 0, 0), (0.75, -40, 0, -30), (2.1, -40, 0, -30), (2.6, 0, 0, 0)),
                "arm_r": raw_rot((0.0, 0, 0, 0), (0.75, -40, 0, 30), (2.1, -40, 0, 30), (2.6, 0, 0, 0)),
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
