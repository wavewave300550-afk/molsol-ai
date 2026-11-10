#!/usr/bin/env python3
"""
Rig V2 - upgrades the approved Red Dragon geometry for advanced animation WITHOUT changing its
look.  Runs after gen_model.py and edits the generated files in place:

  * toes_fl / toes_fr / toes_hl / toes_hr : the toe + claw cubes move out of each foot bone into a
    child bone pivoting at the ball of the foot, so a foot can roll (heel lifts, toes stay planted)
    and the toes can flex during a step.
  * eyelid_l / eyelid_r : two new thin lid cubes for blinking.  In the rest pose the lid is folded
    up into the skull (rest rotation z = +/-90), so the model looks exactly as approved; the blink
    animation swings it down over the eye.  Its texels are painted into unused texture space.

Guarantees (checked here, the build fails otherwise):
  * every pre-existing cube keeps its origin/size/rotation/UV byte for byte,
  * every pre-existing cube corner sits at the same model-space position in the rest pose,
  * every pre-existing texel of red_dragon.png is unchanged,
  * the new lids are hidden inside the head in the rest pose and cover the eyes when closed.
"""
from __future__ import annotations

import copy
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
GEO = os.path.join(RP, "models", "entity", "red_dragon.geo.json")
TEX = os.path.join(RP, "textures", "entity", "red_dragon.png")

# ball-of-foot pivots (front edge / bottom of each foot pad); toe + claw cubes start in front of the pad
TOES = {
    "foot_fl": ("toes_fl", (22, 1.5, -31), lambda c: c["origin"][2] < -31.5),
    "foot_fr": ("toes_fr", (-22, 1.5, -31), lambda c: c["origin"][2] < -31.5),
    "foot_hl": ("toes_hl", (19, -12.5, 24), lambda c: c["origin"][2] < 23.5),
    "foot_hr": ("toes_hr", (-19, -12.5, 24), lambda c: c["origin"][2] < 23.5),
}

# eye cubes are at x 9.6..10.6 (left) / -10.6..-9.6 (right), y 50..53, z -108..-103
LID_PIVOT_X, LID_TOP, LID_Z0, LID_Z1 = 10.3, 53.2, -108.3, -102.7
LID_THICK, LID_HEIGHT = 0.6, 3.2


def corners(geo, names=None):
    out = {}
    for b, f, P, n, uv in K.world_faces(geo, None):
        if names is not None and b not in names:
            continue
        out.setdefault(b, []).append(np.round(P, 4))
    return out


def all_cube_corners(geo):
    """{(cube signature) -> rest-pose corners} so cubes can be compared after moving bones."""
    mats = K.bone_matrices(geo, None)
    res = {}
    for b in geo["bones"]:
        M = mats[b["name"]]
        for c in b.get("cubes", []):
            key = json.dumps(c, sort_keys=True)
            lo, hi = K.cube_corners(c)
            C = np.eye(4)
            if "rotation" in c:
                piv = np.array(c.get("pivot", (lo + hi) / 2), dtype=float)
                C = K.affine(t=piv) @ K.affine(K.brot(c["rotation"])) @ K.affine(t=-piv)
            pts = np.array([[x, y, z, 1] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            res.setdefault(key, []).append(np.round((pts @ (M @ C).T)[:, :3], 4))
    return res


def free_rect(img, w, h, start_y=330):
    """First fully transparent w x h area (with a 1 px margin) at or below start_y."""
    H, W = img.shape[:2]
    a = img[..., 3]
    for y in range(start_y, H - h - 1):
        for x in range(1, W - w - 1):
            if not a[y - 1:y + h + 1, x - 1:x + w + 1].any():
                return x, y
    raise RuntimeError("no free texture space for the eyelids")


def paint_lid(w, h, seed):
    rng = np.random.default_rng(seed)
    base = np.array([0x6A, 0x1C, 0x1D], dtype=float)
    col = base[None, None, :] * (0.85 + 0.3 * rng.random((h, w, 1)))
    if h >= 3:
        col[-1] = col[-1] * 0.55  # lid rim
        col[0] = np.minimum(255, col[0] * 1.25)  # light catches the top of the lid
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(col, 0, 255)
    out[..., 3] = 255
    return out


def main():
    geo_doc = json.load(open(GEO))
    geo = geo_doc["minecraft:geometry"][0]
    if any(b["name"].startswith(("toes_", "eyelid_")) for b in geo["bones"]):
        print("rig_v2: already applied")
        return
    before = all_cube_corners(geo)
    before_cubes = {json.dumps(c, sort_keys=True) for b in geo["bones"] for c in b.get("cubes", [])}
    img = np.array(Image.open(TEX).convert("RGBA"))
    img_before = img.copy()

    bones = geo["bones"]
    by = {b["name"]: b for b in bones}

    # ---- toes
    for foot, (toe, pivot, is_toe) in TOES.items():
        fb = by[foot]
        keep, move = [], []
        for c in fb["cubes"]:
            (move if is_toe(c) else keep).append(c)
        assert len(move) == 6, f"{foot}: expected 3 toes + 3 claws, found {len(move)}"
        fb["cubes"] = keep
        nb = {"name": toe, "parent": foot, "pivot": list(pivot), "cubes": move}
        bones.insert(bones.index(fb) + 1, nb)

    # ---- eyelids (new cubes with UVs in unused texture space)
    lid_faces = {"north": (1, 4), "south": (1, 4), "east": (6, 4), "west": (6, 4), "up": (1, 6), "down": (1, 6)}
    head_i = bones.index(by["head"])
    for side, sx in (("l", 1), ("r", -1)):
        uv = {}
        for k, (face, (w, h)) in enumerate(lid_faces.items()):
            x, y = free_rect(img, w, h)
            img[y:y + h, x:x + w] = paint_lid(w, h, 40 + k + (0 if sx > 0 else 10))
            uv[face] = {"uv": [x, y], "uv_size": [w, h]}
        x0 = LID_PIVOT_X if sx > 0 else -LID_PIVOT_X - LID_THICK
        cube = {"origin": [x0, LID_TOP - LID_HEIGHT, LID_Z0], "size": [LID_THICK, LID_HEIGHT, LID_Z1 - LID_Z0], "uv": uv}
        bone = {"name": f"eyelid_{side}", "parent": "head", "pivot": [sx * LID_PIVOT_X, LID_TOP, (LID_Z0 + LID_Z1) / 2],
                "rotation": [0, 0, 90 * sx], "cubes": [cube]}
        bones.insert(head_i + 1, bone)

    # ---- guarantees
    after = all_cube_corners(geo)
    for key, pts in before.items():
        assert key in after, "a pre-existing cube changed"
        for a, b in zip(sorted(pts, key=lambda p: p.tobytes()), sorted(after[key], key=lambda p: p.tobytes())):
            assert np.abs(a - b).max() < 1e-3, "a pre-existing cube moved in the rest pose"
    after_cubes = {json.dumps(c, sort_keys=True) for b in geo["bones"] for c in b.get("cubes", [])}
    assert before_cubes <= after_cubes, "a pre-existing cube's data changed"
    changed = np.any(img_before != img, axis=2)
    assert not np.any(img_before[changed][:, 3] > 0), "a pre-existing texel was overwritten"

    # lids: hidden in the skull at rest, covering the eye when closed (rest + animation z -/+90)
    mats = K.bone_matrices(geo, None)
    for side, sx in (("l", 1), ("r", -1)):
        b = next(x for x in bones if x["name"] == f"eyelid_{side}")
        lo, hi = K.cube_corners(b["cubes"][0])
        pts = np.array([[x, y, z, 1] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        rest = (pts @ mats[b["name"]].T)[:, :3]
        hm = mats["head"]
        local_rest = (np.c_[rest, np.ones(8)] @ np.linalg.inv(hm).T)[:, :3]  # back into head space
        assert (np.abs(local_rest[:, 0]) <= 10.35).all(), f"eyelid_{side} pokes out of the skull at rest"
        pose = {f"eyelid_{side}": {"rotation": np.array([0, 0, -90.0 * sx]), "position": np.zeros(3), "scale": np.ones(3)}}
        closed = (pts @ K.bone_matrices(geo, pose)[b["name"]].T)[:, :3]
        local_closed = (np.c_[closed, np.ones(8)] @ np.linalg.inv(hm).T)[:, :3]
        assert np.abs(local_closed[:, 0]).max() >= 10.85, f"eyelid_{side} does not cover the eye when closed"

    json.dump(geo_doc, open(GEO, "w"), indent=1)
    open(GEO, "a").write("\n")
    Image.fromarray(img, "RGBA").save(TEX, optimize=True)
    n = len(bones)
    print(f"rig_v2: {n} bones (+4 toe bones, +2 eyelids); existing cubes, UVs and texels unchanged")


if __name__ == "__main__":
    main()
