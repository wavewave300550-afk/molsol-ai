"""Post-step for the three held books (runs after books_dn / books_dw / books_ed).

1. HAND FRAME.  The book modules place the book with a "place" bone whose numbers are written in the
   player model's own space (hand item bone at (6, 15, 1) in bb space, axes right / up / back).  A bone
   bound with q.item_slot_to_bone_name() does not live in that space.  The frame used here is the one
   Blockbench uses to preview Bedrock attachables (js/formats/bedrock/attachable_preview.js), which is
   what creators check held items against:
     third person : bound point (0, 24, 0) is the hand and the item follows the arm, no extra turn
     first person : item root at (-20, 21, 0) turned ZYX(-95, 45, 115), seen by a camera at (0, 19, -40)
                    looking at (0, 16, 0) with an 18 mm lens, 16:9
   (1.0.2 used a 90-degree turn in third person and the vanilla shield's angles in first person; in
   that reference the book lay flat under the hand and floated next to the crosshair.)
   A "<book>_frame" bone between the bound root and "place" converts between the two:
     third person : a pure shift, so the book modules' third-person numbers are offsets from the hand
                    along the arm's right / up / back
     first person : computed so that the closed book's centre lands at FP_SCREEN (screen position,
                    -1..1 like the crosshair at 0, 0) at FP_DEPTH units in front of the camera, with
                    the book modules' first-person axes = screen right / up / toward the camera
   tools/held_preview.py draws the result.
2. BONE NAMES.

An attachable's bones are matched BY NAME against the player's skeleton, so a book bone called
"root" or "body" would be glued to that player bone instead of following the hand.  This step
renames any colliding bone in the generated geometry, animations and render controller.
"""
import json
import math
import os

import numpy as np

from kit.geo import rot_matrix
from kit.molang import Molang
from kit.pack import RP

PLAYER = {"root", "waist", "body", "head", "hat", "cape", "jacket", "helmet", "leftarm", "rightarm", "leftleg",
          "rightleg", "leftitem", "rightitem", "leftsleeve", "rightsleeve", "leftpants", "rightpants"}


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


HAND = [-6.0, 15.0, 1.0]            # player rightItem pivot (geometry space: X is the holder's left)
HAND_BOUND = [0.0, 24.0, 0.0]       # where that point sits in the bound bone's space
ITEMS = {"book_dw": "divine_word", "book_dn": "dream_nightmare", "book_ed": "elemental_dragon"}

# ---- first-person placement of the CLOSED book (the open / charging motion is added by the book modules)
FP_SCREEN = (0.36, -0.30)           # right of and below the crosshair, clear of it
FP_DEPTH = 22.0                     # units in front of the reference camera (the hand is at about 24)

# Blockbench attachable reference (bb space = the Bedrock file with X mirrored)
_W_FIRST_POS = np.array([-20.0, 21.0, 0.0])
_W_FIRST_ROT = rot_matrix(-95.0, 45.0, 115.0)
_EYE, _TARGET = np.array([0.0, 19.0, -40.0]), np.array([0.0, 16.0, 0.0])
_V_SLOPE = 0.5 * (35.0 / (16 / 9)) / 18.0
_H_SLOPE = _V_SLOPE * 16 / 9


def _euler(R):
    """kit / Blockbench rotation (X, then Y, then Z) of a rotation matrix, degrees."""
    b = -math.asin(max(-1.0, min(1.0, R[2, 0])))
    a = math.atan2(R[2, 1], R[2, 2])
    c = math.atan2(R[1, 0], R[0, 0])
    return tuple(math.degrees(v) for v in (a, b, c))


def _place_position(g, att, an, first_person):
    """Closed-book position of the "place" bone (bb space) as the attachable's animations set it."""
    ev = Molang({"c.is_first_person": 1.0 if first_person else 0.0, "v.open": 0.0})
    pos = np.zeros(3)
    for entry in att["scripts"]["animate"]:
        name, cond = (entry, None) if isinstance(entry, str) else next(iter(entry.items()))
        if cond is not None and not ev(cond):
            continue
        a = an["animations"].get(att["animations"].get(name, ""), {})
        p = a.get("bones", {}).get("place", {}).get("position")
        if p is not None:
            v = [ev(x) for x in (p if isinstance(p, list) else [p, p, p])]
            pos += np.array([-v[0], v[1], v[2]])
    return pos


def _frames(g, att, an):
    """(first-person rotation, position), (third-person rotation, position) for the frame bone, Bedrock values."""
    hand_bb = np.array([-HAND[0], HAND[1], HAND[2]])
    bound_bb = np.array([-HAND_BOUND[0], HAND_BOUND[1], HAND_BOUND[2]])
    # third person: shift the authored hand onto the bound hand
    tp_rot, tp_pos = (0.0, 0.0, 0.0), bound_bb - hand_bb
    # first person: screen-aligned axes, closed book centre at FP_SCREEN / FP_DEPTH
    f = (_TARGET - _EYE) / np.linalg.norm(_TARGET - _EYE)
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    S = np.column_stack([r, u, -f])
    centre = _EYE + FP_DEPTH * (f + FP_SCREEN[0] * _H_SLOPE * r + FP_SCREEN[1] * _V_SLOPE * u)
    R = _W_FIRST_ROT.T @ S
    P = _place_position(g, att, an, True)
    t = _W_FIRST_ROT.T @ (centre - _W_FIRST_POS) - hand_bb - R @ (P - hand_bb)
    fp_rot = _euler(R)

    def bedrock(rot, pos):
        return ([round(-rot[0], 3), round(-rot[1], 3), round(rot[2], 3)],
                [round(-float(pos[0]), 3), round(float(pos[1]), 3), round(float(pos[2]), 3)])
    return bedrock(fp_rot, t), bedrock(tp_rot, tp_pos)


def _hand_frame(g, geo, bones):
    frame = f"{g}_frame"
    if not any(b["name"] == frame for b in bones):
        bound = next(b for b in bones if "binding" in b)
        i = bones.index(bound)
        bones.insert(i + 1, {"name": frame, "parent": bound["name"], "pivot": list(HAND)})
        for b in bones:
            if b.get("parent") == bound["name"] and b["name"] != frame:
                b["parent"] = frame
    anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
    an = json.load(open(anim_p, encoding="utf-8"))
    att_p = os.path.join(RP, "attachables", f"{ITEMS[g]}.json")
    att = json.load(open(att_p, encoding="utf-8"))
    d = att["minecraft:attachable"]["description"]
    (fr, fp), (tr, tp) = _frames(g, d, an)
    an["animations"][f"animation.grimoire.{g}.hand_frame"] = {"loop": True, "bones": {frame: {
        "rotation": [f"c.is_first_person ? {fr[i]} : {tr[i]}" for i in range(3)],
        "position": [f"c.is_first_person ? {fp[i]} : {tp[i]}" for i in range(3)]}}}
    _dump(anim_p, an)
    d["animations"]["hand_frame"] = f"animation.grimoire.{g}.hand_frame"
    if "hand_frame" not in d["scripts"]["animate"]:
        d["scripts"]["animate"].insert(0, "hand_frame")
    _dump(att_p, att)
    print(f"    {g}: hand frame  first person rot {fr} pos {fp}  third person rot {tr} pos {tp}")


def build(pack):
    for g in ("book_dw", "book_dn", "book_ed"):
        geo_p = os.path.join(RP, "models", "entity", f"{g}.geo.json")
        if not os.path.exists(geo_p):
            continue
        geo = json.load(open(geo_p, encoding="utf-8"))
        bones = geo["minecraft:geometry"][0]["bones"]
        _hand_frame(g, geo, bones)
        _dump(geo_p, geo)
        ren = {b["name"]: f"{g}_{b['name']}" for b in bones if b["name"].lower() in PLAYER}
        if not ren:
            continue
        for b in bones:
            b["name"] = ren.get(b["name"], b["name"])
            if "parent" in b:
                b["parent"] = ren.get(b["parent"], b["parent"])
        _dump(geo_p, geo)
        anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
        if os.path.exists(anim_p):
            an = json.load(open(anim_p, encoding="utf-8"))
            for a in an.get("animations", {}).values():
                if "bones" in a:
                    a["bones"] = {ren.get(k, k): v for k, v in a["bones"].items()}
            _dump(anim_p, an)
        rc_p = os.path.join(RP, "render_controllers", f"{g}.render_controllers.json")
        if os.path.exists(rc_p):
            rc = json.load(open(rc_p, encoding="utf-8"))
            for c in rc.get("render_controllers", {}).values():
                for key in ("materials", "part_visibility"):
                    if key in c:
                        c[key] = [{ren.get(k, k): v for k, v in e.items()} for e in c[key]]
            _dump(rc_p, rc)
        print(f"    {g}: renamed bones {ren}")
