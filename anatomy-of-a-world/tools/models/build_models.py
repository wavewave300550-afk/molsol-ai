"""Build all entity models/textures/animations into build/packs/RP and export preview poses."""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

import migrating_mountain as mm  # noqa: E402
from kit import write_json  # noqa: E402


def sample_poses() -> dict:
    """Named poses for the previewer (bone -> rotation/position/scale), mirroring the baked animations."""
    poses = {}
    poses["mm_root_leg"] = {
        "rest": {},
        "walk_lift": mm.leg_animations()  # placeholder replaced below
    }
    # evaluate the python animation functions directly
    leg = {}
    import math
    for name, t in (("walk_lift", 1.5), ("walk_plant", 4.5)):
        ph = (t / 6.0) * 2 * math.pi
        lift = max(0.0, math.sin(ph))
        swing = math.cos(ph)
        leg[name] = mm.leg_pose({"upper": -12 * lift + 3 * swing, "knee": 10 * lift - 2 * swing, "lower": 6 * lift, "foot": -8 * lift}, toe_curl=10 * lift - 3, yaw=7 * swing)
    leg["stomp_top"] = mm.leg_pose({"upper": -26, "knee": 22, "lower": 10, "foot": -14}, toe_curl=18)
    leg["splay"] = mm.leg_pose({"upper": -18, "knee": -14, "lower": -6, "foot": 34}, toe_curl=-6)
    leg["rest"] = {}
    poses["mm_root_leg"] = leg
    poses["mm_petal"] = {
        "closed": mm.petal_pose(mm.PETAL_CLOSED),
        "open": mm.petal_pose(mm.PETAL_OPEN),
        "folded": mm.petal_pose(mm.PETAL_FOLDED),
        "half": mm.petal_pose(mm.lerp_pose(mm.PETAL_CLOSED, mm.PETAL_OPEN, 0.5)),
    }
    poses["mm_lithic_heart"] = {
        "closed": {f"plate{k}_leaf": {"rotation": [0, 0, 0]} for k in range(8)},
        "open": {f"plate{k}_leaf": {"rotation": [62, 0, 0], "position": [0, -4, -6]} for k in range(8)},
    }
    poses["mm_resonance_node"] = {"rest": {}, "hang": {"root": {"rotation": [180, 0, 0], "position": [0, 56, 0]}}}
    poses["mm_strata_slab"] = {"rest": {}}
    poses["mm_strata_plate"] = {"rest": {}, "wall": {"hinge": {"rotation": [0, 0, -90]}}, "ceiling": {"roll": {"rotation": [0, 0, 180]}}}
    poses["mm_rib_plate"] = poses["mm_strata_plate"]
    return poses


def main(out_rp: str) -> None:
    models, anims = mm.build_all()
    os.makedirs(os.path.join(out_rp, "models", "entity"), exist_ok=True)
    os.makedirs(os.path.join(out_rp, "textures", "entity", "anatomy"), exist_ok=True)
    os.makedirs(os.path.join(out_rp, "animations"), exist_ok=True)
    for short, model in models:
        write_json(os.path.join(out_rp, "models", "entity", f"{short}.geo.json"), model.geometry_json())
        model.atlas.save(os.path.join(out_rp, "textures", "entity", "anatomy", f"{short}.png"))
        print(model.stats())
    for short, a in anims.items():
        write_json(os.path.join(out_rp, "animations", f"{short}.animation.json"), {"format_version": "1.8.0", "animations": a})
        print(f"animations {short}: {', '.join(k.split('.')[-1] for k in a)}")
    prev = os.path.join(ROOT, "tools", "preview", "out")
    os.makedirs(prev, exist_ok=True)
    with open(os.path.join(prev, "poses.json"), "w") as fh:
        json.dump(sample_poses(), fh)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "packs", "RP"))
