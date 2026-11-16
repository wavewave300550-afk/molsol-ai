"""
Player rig for previews + a first-person pose solver.

The vanilla player geometry/texture are only used for preview renders; they are read from a
local checkout of Mojang/bedrock-samples when available (BEDROCK_SAMPLES env var) and replaced
by a plain stand-in skeleton otherwise.
"""
from __future__ import annotations

import json
import math
import os
import re

import numpy as np
from PIL import Image

import modelkit as mk

EYE = 1.62 * 16 / 0.9375          # player eye height in model units (render scale 0.9375)

THIRD_PERSON_HOLD = mk.Pose(rightArm={"rotation": [-18, 0, 0]})
FIRST_PERSON = mk.Pose(rightArm={"position": [13.5, -10, 12], "rotation": [95, -45, 115]},
                       rightItem={"position": [0, 0, -1]})
FP_HIDE = ("head", "hat", "body", "jacket", "leftArm", "leftSleeve", "leftLeg", "rightLeg", "leftPants", "rightPants",
           "cape", "waist")


def _load(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"//[^\n]*", "", t)
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    return json.loads(t)


def player_model():
    rp = os.environ.get("BEDROCK_SAMPLES")
    if rp:
        rp = os.path.join(rp, "resource_pack")
    if rp and os.path.exists(os.path.join(rp, "models", "mobs.json")):
        g = _load(os.path.join(rp, "models", "mobs.json"))["geometry.humanoid.custom:geometry.humanoid"]
        tex = Image.open(os.path.join(rp, "textures", "entity", "steve.png"))
        return mk.load_vanilla_geometry({"geometry.humanoid.custom": g}, "geometry.humanoid.custom", tex)
    # stand-in: same skeleton, flat colours
    m = mk.Model("geometry.standin", 1.0)
    skin, shirt, pants, hair = mk.solid("c9946b"), mk.solid("2ea3a3"), mk.solid("3b3a8f"), mk.solid("3b2a1d")
    m.bone("root", (0, 0, 0))
    m.bone("waist", (0, 12, 0), "root")
    m.bone("body", (0, 24, 0), "waist").add((-4, 12, -2), (8, 12, 4), shirt)
    m.bone("head", (0, 24, 0), "body").add((-4, 24, -4), (8, 8, 8), skin)
    m.get("head").add((-4.25, 29.5, -4.25), (8.5, 2.75, 8.5), hair)
    m.bone("rightArm", (-5, 22, 0), "body").add((-8, 12, -2), (4, 12, 4), skin)
    m.bone("rightItem", (-6, 15, 1), "rightArm")
    m.bone("leftArm", (5, 22, 0), "body").add((4, 12, -2), (4, 12, 4), skin)
    m.bone("leftItem", (6, 15, 1), "leftArm")
    m.bone("rightLeg", (-1.9, 12, 0), "root").add((-3.9, 0, -2), (4, 12, 4), pants)
    m.bone("leftLeg", (1.9, 12, 0), "root").add((-0.1, 0, -2), (4, 12, 4), pants)
    return m


SLOT_BONES = {"main_hand": "rightItem", "off_hand": "leftItem", "head": "head", "chest": "body"}


def attach(player, ppose, item, ipose):
    """World matrices for the player and an attachable whose bones bind to player bones."""
    pm = mk.world_matrices(player, ppose)
    binds = {}
    for slot, bone in SLOT_BONES.items():
        binds[slot] = (pm[bone], player.get(bone).pivot)
    # c.item_slot resolves to main_hand for held items
    saved = {}
    for b in item.bones:
        if b.binding:
            saved[b.name] = b.binding
            b.binding = b.binding.replace("c.item_slot", "'main_hand'")
    im = mk.world_matrices(item, ipose, bind=binds)
    for b in item.bones:
        if b.name in saved:
            b.binding = saved[b.name]
    return pm, im


def fp_camera(fov=70.0):
    return mk.Camera(tuple(mk.rh((0, EYE, 0))), tuple(mk.rh((0, EYE, 16))), fov=fov)


def euler_from_rh(R) -> list:
    """Bedrock [rx, ry, rz] for a right-handed rotation matrix (inverse of modelkit.rot_rh)."""
    R = np.asarray(R)[:3, :3]
    b = -math.asin(max(-1.0, min(1.0, R[2, 0])))
    if abs(math.cos(b)) > 1e-6:
        a = math.atan2(R[2, 1], R[2, 2])
        c = math.atan2(R[1, 0], R[0, 0])
    else:
        a, c = math.atan2(-R[1, 2], R[1, 1]), 0.0
    return [round(-math.degrees(a), 2), round(-math.degrees(b), 2), round(math.degrees(c), 2)]


def solve_bound_pose(player, ppose, slot, bone_pivot, world_point_bedrock, world_rot_rh):
    """Animation position/rotation for a bone bound to `slot` so that its pivot lands on
    `world_point_bedrock` (player model coordinates) with world orientation `world_rot_rh`."""
    pm = mk.world_matrices(player, ppose)
    tb = player.get(SLOT_BONES[slot])
    A = pm[SLOT_BONES[slot]] @ mk._t(mk.rh((tb.pivot[0], tb.pivot[1] - 24.0, tb.pivot[2])))
    Q = np.append(mk.rh(world_point_bedrock), 1.0)
    local = np.linalg.inv(A) @ Q
    pos_rh = local[:3] - mk.rh(bone_pivot)
    pos = [round(-pos_rh[0], 3), round(pos_rh[1], 3), round(pos_rh[2], 3)]
    R = A[:3, :3].T @ np.asarray(world_rot_rh)[:3, :3]
    return pos, euler_from_rh(R)


def rot_world(yaw=0.0, pitch=0.0, roll=0.0):
    """Right-handed world rotation: roll about Z, then pitch about X, then yaw about Y (degrees)."""
    return (mk._ry(math.radians(yaw)) @ mk._rx(math.radians(pitch)) @ mk._rz(math.radians(roll)))[:3, :3]


def rot_axes(y_dir, z_hint):
    """Rotation (render frame) that maps the model's +Y axis onto `y_dir` and keeps its +Z axis
    as close to `z_hint` as possible. Directions are camera-space render-frame vectors:
    +X = screen LEFT, +Y = up, +Z = forward (away from the eye)."""
    y = np.asarray(y_dir, float)
    y /= np.linalg.norm(y)
    z = np.asarray(z_hint, float)
    z = z - np.dot(z, y) * y
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])
