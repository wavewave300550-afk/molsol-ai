"""
Calibration of the preview renderer against vanilla ground truth.

Renders the vanilla player (geometry.humanoid.custom + steve.png) holding the vanilla
trident and the scoping spyglass with Mojang's own attachable animations, in third and
first person. If the emulated transform rules are right, the trident shaft passes
through the hand and the spyglass sits at the right eye pointing forward.

    python3 tools/calibrate.py <bedrock-samples>/resource_pack <out_dir>
"""
import json
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelkit as mk  # noqa: E402


def load(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"//[^\n]*", "", t)
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    return json.loads(t)


def player_model(rp):
    data = load(os.path.join(rp, "models", "mobs.json"))
    g = data["geometry.humanoid.custom:geometry.humanoid"]
    tex = Image.open(os.path.join(rp, "textures", "entity", "steve.png"))
    return mk.load_vanilla_geometry({"geometry.humanoid.custom": g}, "geometry.humanoid.custom", tex)


THIRD_PERSON_HOLD = mk.Pose(rightArm={"rotation": [-18, 0, 0]})
FIRST_PERSON = mk.Pose(rightArm={"position": [13.5, -10, 12], "rotation": [95, -45, 115]},
                       rightItem={"position": [0, 0, -1]})


def attach(player, pose, item, item_pose, target="rightItem"):
    pm = mk.world_matrices(player, pose)
    tb = player.get(target)
    key = {"rightItem": "main_hand", "head": "head"}[target]
    # emulate q.item_slot_to_bone_name(...) -> target bone
    for b in item.bones:
        if b.binding:
            b.binding = f"'{key}'"
    im = mk.world_matrices(item, item_pose, bind={key: (pm[target], tb.pivot)})
    return pm, im


def first_person_camera(eye=24.0, fov=70.0):
    # first-person rendering looks towards +Z in model space (head pose has +180 yaw)
    return mk.Camera(tuple(mk.rh((0, eye, 0))), tuple(mk.rh((0, eye, 16))), fov=fov)


def main():
    rp, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    player = player_model(rp)
    trident = mk.load_vanilla_geometry(load(os.path.join(rp, "models", "entity", "trident.geo.json")),
                                       "geometry.trident", Image.open(os.path.join(rp, "textures", "entity", "trident.png")))
    spy = mk.load_vanilla_geometry(load(os.path.join(rp, "models", "entity", "spyglass.geo.json")),
                                   "geometry.spyglass", Image.new("RGBA", (16, 16), (200, 120, 60, 255)))

    # third person trident
    pm, im = attach(player, THIRD_PERSON_HOLD, trident, mk.Pose(pole={"position": [1.5, -2.5, -10.5], "rotation": [97, -1.5, -49]}))
    sc = mk.Scene()
    sc.add_model(player, pm)
    sc.add_model(trident, im)
    hand = (pm["rightItem"] @ np.append(mk.rh(player.get("rightItem").pivot), 1))[:3]
    for yaw, name in ((-60, "front_right"), (-110, "side_right"), (180, "back")):
        sc.render(mk.orbit_camera(target=(0, 18, 0), dist=70, yaw=yaw, pitch=12, fov=40), (420, 420)).save(
            os.path.join(out, f"tp_trident_{name}.png"))
    print("hand pivot (render frame):", np.round(hand, 2))

    # third person spyglass scoping (bound to head)
    pm, im = attach(player, mk.Pose(rightArm={"rotation": [-105, -15, 5]}), spy,
                    mk.Pose(spyglass={"position": [-1, 27, -3], "rotation": [0, -90, 0]}), target="head")
    sc = mk.Scene()
    sc.add_model(player, pm)
    sc.add_model(spy, im)
    for yaw, name in ((-35, "front_right"), (-90, "side_right")):
        sc.render(mk.orbit_camera(target=(0, 26, 0), dist=45, yaw=yaw, pitch=8, fov=40), (420, 420)).save(
            os.path.join(out, f"tp_spyglass_{name}.png"))

    # first person trident, several candidate eye heights
    for eye in (20, 24, 28):
        pm, im = attach(player, FIRST_PERSON, trident, mk.Pose(pole={"position": [-7, -3, -2], "rotation": [152, -9, 25]}))
        sc = mk.Scene()
        sc.add_model(player, pm, hide=("head", "hat", "body", "jacket", "leftArm", "leftSleeve", "leftLeg", "rightLeg", "leftPants", "rightPants"))
        sc.add_model(trident, im)
        sc.render(first_person_camera(eye), (640, 360), bg=(110, 150, 200, 255)).save(os.path.join(out, f"fp_trident_eye{eye}.png"))


if __name__ == "__main__":
    main()
