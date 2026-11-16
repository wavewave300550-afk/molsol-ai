"""
Player preview rig: the Bedrock humanoid skeleton, a procedural mannequin skin,
and an emulation of the vanilla player animation stack (enough of it to judge
how our runtime animations compose with the game's own animations).

The bone layout (names, pivots, cube boxes, box-UV offsets) mirrors the vanilla
geometry.humanoid.custom.  Vanilla animation expressions below are the
formulas the game uses (bedrock-samples v1.26.60.5); they are reproduced only to
emulate the stack in offline previews.
"""
from __future__ import annotations

import math
import random
from typing import Dict, Optional

import numpy as np
from PIL import Image

from . import molang
from .bedrock import BonePose, Geo, apply_animation, load_geometries, rest_pose, world_matrices

RIG = {
    "format_version": "1.16.0",
    "minecraft:geometry": [{
        "description": {"identifier": "geometry.preview.humanoid", "texture_width": 64, "texture_height": 64},
        "bones": [
            {"name": "root", "pivot": [0, 0, 0]},
            {"name": "waist", "parent": "root", "pivot": [0, 12, 0]},
            {"name": "body", "parent": "waist", "pivot": [0, 24, 0],
             "cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 16]}]},
            {"name": "jacket", "parent": "body", "pivot": [0, 24, 0],
             "cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 32], "inflate": 0.25}]},
            {"name": "head", "parent": "body", "pivot": [0, 24, 0],
             "cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [0, 0]}]},
            {"name": "hat", "parent": "head", "pivot": [0, 24, 0],
             "cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [32, 0], "inflate": 0.5}]},
            {"name": "leftArm", "parent": "body", "pivot": [5, 22, 0],
             "cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [32, 48]}]},
            {"name": "leftSleeve", "parent": "leftArm", "pivot": [5, 22, 0],
             "cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [48, 48], "inflate": 0.25}]},
            {"name": "leftItem", "parent": "leftArm", "pivot": [6, 15, 1]},
            {"name": "rightArm", "parent": "body", "pivot": [-5, 22, 0],
             "cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}]},
            {"name": "rightSleeve", "parent": "rightArm", "pivot": [-5, 22, 0],
             "cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 32], "inflate": 0.25}]},
            {"name": "rightItem", "parent": "rightArm", "pivot": [-6, 15, 1]},
            {"name": "leftLeg", "parent": "root", "pivot": [1.9, 12, 0],
             "cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [16, 48]}]},
            {"name": "leftPants", "parent": "leftLeg", "pivot": [1.9, 12, 0],
             "cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [0, 48], "inflate": 0.25}]},
            {"name": "rightLeg", "parent": "root", "pivot": [-1.9, 12, 0],
             "cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}]},
            {"name": "rightPants", "parent": "rightLeg", "pivot": [-1.9, 12, 0],
             "cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 32], "inflate": 0.25}]},
        ],
    }],
}

PLAYER_GEO: Geo = load_geometries(RIG)["geometry.preview.humanoid"]


def _fill(img, x0, y0, w, h, col, rng=None, var=0.0):
    px = img.load()
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            c = col
            if rng is not None and var:
                f = 1 + (rng.random() - 0.5) * var
                c = tuple(max(0, min(255, int(v * f))) for v in col[:3]) + (col[3] if len(col) > 3 else 255,)
            px[x, y] = c if len(c) == 4 else c + (255,)


def _box(img, u, v, s, cols, rng, var=0.08):
    """Paint a box-UV region: cols = dict(top, bottom, right, front, left, back)."""
    sx, sy, sz = s
    _fill(img, u + sz, v, sx, sz, cols["top"], rng, var)
    _fill(img, u + sz + sx, v, sx, sz, cols["bottom"], rng, var)
    _fill(img, u, v + sz, sz, sy, cols["right"], rng, var)
    _fill(img, u + sz, v + sz, sx, sy, cols["front"], rng, var)
    _fill(img, u + sz + sx, v + sz, sz, sy, cols["left"], rng, var)
    _fill(img, u + sz * 2 + sx, v + sz, sx, sy, cols["back"], rng, var)


def mannequin_skin() -> Image.Image:
    """A neutral 64x64 preview skin: linen shirt, dark doublet, breeches, boots."""
    rng = random.Random(7)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    skin = (214, 170, 132, 255)
    hair = (74, 52, 36, 255)
    shirt = (226, 222, 210, 255)
    doublet = (112, 36, 40, 255)
    breeches = (78, 66, 52, 255)
    boots = (38, 30, 26, 255)

    def same(c):
        return {k: c for k in ("top", "bottom", "right", "front", "left", "back")}
    head = same(skin)
    head["top"] = hair
    head["back"] = hair
    _box(img, 0, 0, (8, 8, 8), head, rng, 0.05)
    px = img.load()
    for x in range(8, 16):            # hair fringe on the face
        px[x, 8] = hair
    for x in (0, 1, 2, 3, 4, 5, 6, 7):  # side hair
        px[x, 8] = hair
        px[x + 16, 8] = hair
        px[x, 9] = hair
        px[x + 16, 9] = hair
    for x in (9, 10, 13, 14):         # eyes
        px[x, 12] = (250, 250, 250, 255)
    px[10, 12] = (54, 82, 140, 255)
    px[13, 12] = (54, 82, 140, 255)
    for x in range(10, 14):           # mouth / beard line
        px[x, 14] = (150, 104, 80, 255)
    body = same(doublet)
    body["top"] = shirt
    _box(img, 16, 16, (8, 12, 4), body, rng)
    for y in range(20, 32):           # doublet buttons
        if y % 2 == 0:
            px[24, y] = (210, 180, 90, 255)
    _fill(img, 20, 20, 8, 1, shirt)   # collar
    arm = same(shirt)
    arm["bottom"] = skin
    _box(img, 40, 16, (4, 12, 4), arm, rng)
    _box(img, 32, 48, (4, 12, 4), arm, rng)
    for (u, v) in ((40, 16), (32, 48)):  # hands
        for face_u in range(u, u + 16):
            for y in range(v + 4 + 9, v + 4 + 12):
                px[face_u, y] = skin
    leg = same(breeches)
    _box(img, 0, 16, (4, 12, 4), leg, rng)
    _box(img, 16, 48, (4, 12, 4), leg, rng)
    for (u, v) in ((0, 16), (16, 48)):   # boots
        for face_u in range(u, u + 16):
            for y in range(v + 4 + 6, v + 4 + 12):
                px[face_u, y] = boots
    return img


# ----------------------------------------------------------------------------- vanilla stack emulation

VANILLA_TP = {
    "look_at_target": {"bones": {"head": {"rotation": ["query.target_x_rotation", "query.target_y_rotation", 0.0]}}},
    "move.arms": {"bones": {"leftarm": {"rotation": ["variable.tcos0", 0.0, 0.0]},
                            "rightarm": {"rotation": ["-variable.tcos0", 0.0, 0.0]}}},
    "move.legs": {"bones": {"leftleg": {"rotation": ["variable.tcos0 * -1.4", -0.1, -0.1]},
                            "rightleg": {"rotation": ["variable.tcos0 * 1.4", 0.1, 0.1]}}},
    "holding": {"bones": {"rightarm": {"rotation": ["variable.is_holding_right ? (-this * 0.5 - 18.0) : 0.0", 0.0, 0.0]}}},
    "sneaking": {"bones": {
        "body": {"position": [0.0, -2.0, 0.0]}, "head": {"position": [0.0, -1.0, 0.0]},
        "leftarm": {"rotation": [-5.7, 0.0, 0.0]}, "rightarm": {"rotation": [-5.7, 0.0, 0.0]},
        "leftleg": {"rotation": [-28.0, -0.1, -0.1]}, "rightleg": {"rotation": [-28.0, 0.1, 0.1]},
        "root": {"position": [0.0, 1.25, 9.0], "rotation": ["28.0 - this", 0.0, 0.0]}}},
    "bob": {"bones": {"leftarm": {"rotation": [0.0, 0.0, "-((math.cos(query.life_time * 103.2) * 2.865) + 2.865)"]},
                      "rightarm": {"rotation": [0.0, 0.0, "(math.cos(query.life_time * 103.2) * 2.865) + 2.865"]}}},
    "attack.rotations": {"bones": {
        "body": {"rotation": [0.0, "variable.attack_body_rot_y", 0.0]},
        "leftarm": {"rotation": ["-(math.sin((1 - math.pow((1 - variable.attack_time), 4)) * 180) * 1.2 + math.sin(variable.attack_time * 180)) * 10.0", 0.0, 0.0]},
        "rightarm": {"rotation": ["-(math.sin((1 - math.pow((1 - variable.attack_time), 4)) * 180) * 1.2 + math.sin(variable.attack_time * 180)) * 30.0",
                                  "-(math.sin((1 - math.pow((1 - variable.attack_time), 4)) * 180) ? (-90.0 * math.sin((1 - math.pow((1 - variable.attack_time), 4)) * 180)) + 30.0 : 0.0)", 0.0]}}},
    "swimming": {"override_previous_animation": True, "loop": True, "animation_length": 1.3, "bones": {
        "leftarm": {"rotation": {"0": [0.0, 180.0, 180.0], "0.7": [0.0, 180.0, 287.2], "1.1": [90.0, 180.0, 180.0], "1.3": [0.0, 180.0, 180.0]}},
        "rightarm": {"rotation": {"0": [0.0, 180.0, -180.0], "0.7": [0.0, 180.0, -287.2], "1.1": [90.0, 180.0, -180.0], "1.3": [0.0, 180.0, -180.0]}},
        "root": {"position": [0.0, "(math.sin(query.target_x_rotation) * 17.0 + 5.0) * variable.swim_amount", "(math.cos(query.target_x_rotation) * 17.0) * variable.swim_amount"],
                 "rotation": ["variable.swim_amount * (90 + query.target_x_rotation)", 0.0, 0.0]}}},
    "swimming.legs": {"override_previous_animation": True, "bones": {
        "leftleg": {"rotation": ["math.lerp(0.0, math.cos(query.life_time * 390.0 + 180.0) * 17.2, variable.swim_amount)", -0.1, -0.1]},
        "rightleg": {"rotation": ["math.lerp(0.0, math.cos(query.life_time * 390.0) * 17.2, variable.swim_amount)", 0.1, 0.1]}}},
}

VANILLA_FP = {
    "first_person_base_pose": {"bones": {"body": {"rotation": ["query.target_x_rotation", "query.target_y_rotation", 0.0]}}},
    "first_person_breathing_bob": {"bones": {"rightitem": {"position": [0.0, "variable.bob_animation * math.sin(q.life_time * 45.0) * 0.5", 0.0]}}},
    "first_person_swap_item": {"bones": {"rightarm": {"position": [0.0, "-10.0 * (1.0 - variable.player_arm_height)", 0.0]}}},
    "first_person_attack_rotation": {"bones": {"rightarm": {
        "position": ["math.clamp(-15.5 * math.sin(variable.first_person_item_rotation_factor * variable.attack_time * 112.0), -7.0, 999.0) * math.sin(variable.first_person_item_rotation_factor * variable.attack_time * 112.0)",
                     "math.sin(variable.first_person_item_rotation_factor * (1.0 - variable.attack_time) * (1.0 - variable.attack_time) * 200.0) * 7.5 - variable.first_person_item_rotation_factor * variable.attack_time * 15.0 + variable.short_arm_offset_right",
                     "math.sin(variable.first_person_item_rotation_factor * variable.attack_time * 120.0) * 1.75"],
        "rotation": ["math.sin(variable.first_person_item_rotation_factor * (1.0 - variable.attack_time) * (1.0 - variable.attack_time) * 280.0) * -60.0",
                     "math.sin(variable.first_person_item_rotation_factor * (1.0 - variable.attack_time) * (1.0 - variable.attack_time) * 280.0) * 40.0",
                     "math.sin(variable.first_person_item_rotation_factor * (1.0 - variable.attack_time) * (1.0 - variable.attack_time) * 280.0) * 20.0"]}}},
    "first_person_attack_rotation_item": {"override_previous_animation": True, "bones": {"rightitem": {
        "position": ["-math.sin(math.sqrt(variable.attack_time) * Math.Pi * 100) * 10", "math.sin(math.sqrt(variable.attack_time) * Math.Pi * 2 * 60) * 10", "-math.sin(variable.attack_time * Math.Pi * 65) * 2"],
        "rotation": ["-math.sin(math.sqrt(variable.attack_time) * Math.Pi * 20) * 25", "-math.sin(math.sqrt(variable.attack_time) * 75.0) * 15.0", "-math.sin(math.sqrt(variable.attack_time) * 25) * 15"]}}},
    "first_person_empty_hand": {"bones": {
        "rightarm": {"position": [13.5, -10.0, 12.0], "rotation": [95.0, -45.0, 115.0]},
        "rightitem": {"position": [0.0, 0.0, -1.0]}}},
    "first_person_walk": {"bones": {"rightarm": {"position": [
        "math.sin(-query.walk_distance * 180.0) * variable.hand_bob * 9.75",
        "-math.abs(math.cos(-query.walk_distance * 180.0)) * variable.hand_bob * 15.0 + variable.short_arm_offset_right", 0.0]}}},
}

DEFAULT_STATE = {
    "first_person": False, "attack_time": 0.0, "moving": 0.0, "distance": 0.0, "sneaking": False, "sprinting": False,
    "on_ground": True, "vertical_speed": 0.0, "swimming": False, "swim_amount": 0.0, "in_water": False,
    "life_time": 0.0, "anim_time": 3.0, "target_x": 0.0, "target_y": 0.0, "arm_height": 1.0, "delta_time": 1 / 60,
    "mainhand_tags": ("rww:weapon",), "offhand_empty": True, "riding": False, "sleeping": False, "is_jumping": False,
    "cooldown_remaining": 0.0,
}


def make_context(state: dict, variables: Optional[dict] = None) -> molang.Context:
    s = dict(DEFAULT_STATE)
    s.update(state)
    v = variables if variables is not None else {}
    at = s["attack_time"]
    speed = s["moving"]
    v.update({
        "attack_time": at, "is_first_person": 1.0 if s["first_person"] else 0.0,
        "tcos0": math.cos(math.radians(s["distance"] * 38.17)) * speed * 57.3,
        "attack_body_rot_y": math.sin(math.radians(360 * math.sqrt(max(0.0, at)))) * 5.0,
        "is_holding_right": 1.0, "is_holding_left": 0.0, "first_person_item_rotation_factor": 1.0,
        "player_arm_height": s["arm_height"], "bob_animation": 1.0, "hand_bob": 0.06 * speed,
        "short_arm_offset_right": 0.0, "short_arm_offset_left": 0.0, "is_using_vr": 0.0,
        "swim_amount": s["swim_amount"], "is_paperdoll": 0.0, "gliding_speed_value": 1.0,
    })
    tags = set(s["mainhand_tags"])
    q = {
        "is_first_person": 1.0 if s["first_person"] else 0.0,
        "modified_move_speed": speed, "modified_distance_moved": s["distance"], "walk_distance": s["distance"] / 16.0,
        "is_moving": 1.0 if speed > 0.01 else 0.0, "is_sneaking": 1.0 if s["sneaking"] else 0.0,
        "is_sprinting": 1.0 if s["sprinting"] else 0.0, "is_on_ground": 1.0 if s["on_ground"] else 0.0,
        "vertical_speed": s["vertical_speed"], "is_swimming": 1.0 if s["swimming"] else 0.0,
        "is_in_water": 1.0 if s["in_water"] else 0.0, "life_time": s["life_time"], "time_stamp": int(s["life_time"] * 20),
        "target_x_rotation": s["target_x"], "target_y_rotation": s["target_y"], "delta_time": s["delta_time"],
        "is_riding": 1.0 if s["riding"] else 0.0, "is_sleeping": 1.0 if s["sleeping"] else 0.0,
        "is_jumping": 1.0 if s["is_jumping"] else 0.0, "is_gliding": 0.0, "is_emoting": 0.0, "is_crawling": 0.0,
        "is_alive": 1.0, "blocking": 0.0,
    }

    def qfn(name, args):
        if name == "equipped_item_any_tag":
            slot = args[0] if args else ""
            if slot in ("slot.weapon.mainhand", "main_hand", 0, 0.0):
                return 1.0 if any(a in tags for a in args[1:]) else 0.0
            return 0.0
        if name == "is_item_name_any":
            slot = args[0] if args else ""
            names = [a for a in args[1:] if isinstance(a, str)]
            if slot == "slot.weapon.offhand":
                return 1.0 if (s["offhand_empty"] and "" in names) else 0.0
            return 0.0
        if name == "cooldown_time_remaining":
            return s["cooldown_remaining"]
        return None
    ctx = molang.Context(queries=q, query_fn=qfn, variables=v)
    ctx.state = s  # type: ignore[attr-defined]
    return ctx


def vanilla_layers(state: dict):
    s = dict(DEFAULT_STATE)
    s.update(state)
    if s["first_person"]:
        layers = ["first_person_base_pose", "first_person_breathing_bob", "first_person_swap_item"]
        if s["attack_time"] > 0:
            layers += ["first_person_attack_rotation", "first_person_attack_rotation_item"]
        layers += ["first_person_empty_hand", "first_person_walk"]
        return [VANILLA_FP[k] for k in layers]
    layers = ["look_at_target", "move.arms", "move.legs", "holding"]
    if s["sneaking"]:
        layers.append("sneaking")
    layers.append("bob")
    if s["swim_amount"] > 0:
        layers += ["swimming", "swimming.legs"]
    if s["attack_time"] >= 0:
        layers.append("attack.rotations")
    return [VANILLA_TP[k] for k in layers]


def compose(state: dict, runtime_anims=(), variables: Optional[dict] = None, include_vanilla: bool = True):
    """Return (pose, ctx) for the player: vanilla stack followed by runtime animations.

    runtime_anims: iterable of (animation_json, anim_time) evaluated after the vanilla stack.
    """
    ctx = make_context(state, variables)
    rest = rest_pose(PLAYER_GEO)
    pose: Dict[str, BonePose] = {k: BonePose(b.rot.copy(), b.pos.copy(), b.scale.copy()) for k, b in rest.items()}
    s = ctx.state  # type: ignore[attr-defined]
    if include_vanilla:
        for layer in vanilla_layers(state):
            t = s["life_time"]
            apply_animation(layer, pose, rest, ctx, t)
    for anim, t in runtime_anims:
        apply_animation(anim, pose, rest, ctx, t)
    return pose, ctx


def player_matrices(pose, root: Optional[np.ndarray] = None):
    return world_matrices(PLAYER_GEO, pose, root=root)


FIRST_PERSON_VISIBLE = {"rightarm", "rightsleeve"}
