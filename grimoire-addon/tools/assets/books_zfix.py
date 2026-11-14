"""Post-step for the three held books (runs after books_dn / books_dw / books_ed).

1. HAND FRAME.  The book modules place the book with a "place" bone whose numbers are written in the
   player model's own space (hand item bone at (6, 15, 1) in bb space, axes right / up / back).  A bone
   bound with q.item_slot_to_bone_name() does NOT live in that space.  Measured from the vanilla
   attachables (shield, trident, spyglass) and Mojang's wrench sample, the bound space is:
     third person : point (0, 24, 0) is the hand; -Y is the holder's forward, -Z is up
                    (the model space turned 90 degrees about X around the hand)
     first person : the same hand point, but the axes follow the first-person arm; the vanilla
                    main-hand shield (rotation 91, 65, -43) is drawn upright and facing the camera,
                    so that rotation is the screen-aligned frame (X = screen left, Y = up, Z = toward
                    the camera)
   A "<book>_frame" bone is inserted between the bound root and "place" to convert between the two,
   so the placement numbers in the book modules mean: offsets from the hand along the holder's
   right / up / back in third person, and along screen right / up / toward-camera in first person.
2. BONE NAMES.

An attachable's bones are matched BY NAME against the player's skeleton, so a book bone called
"root" or "body" would be glued to that player bone instead of following the hand.  This step
renames any colliding bone in the generated geometry, animations and render controller.
"""
import json
import os

from kit.pack import RP

PLAYER = {"root", "waist", "body", "head", "hat", "cape", "jacket", "helmet", "leftarm", "rightarm", "leftleg",
          "rightleg", "leftitem", "rightitem", "leftsleeve", "rightsleeve", "leftpants", "rightpants"}


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


HAND = [-6.0, 15.0, 1.0]            # player rightItem pivot (geometry space: X is the holder's left)
HAND_BOUND = [0.0, 24.0, 0.0]       # where that point sits in the bound bone's space
FP_FRAME = (91.0, 65.0, -43.0)      # vanilla main-hand shield, first person
TP_FRAME = (90.0, 0.0, 0.0)
ITEMS = {"book_dw": "divine_word", "book_dn": "dream_nightmare", "book_ed": "elemental_dragon"}


def _hand_frame(g, geo, bones):
    frame = f"{g}_frame"
    if any(b["name"] == frame for b in bones):
        return
    bound = next(b for b in bones if "binding" in b)
    i = bones.index(bound)
    bones.insert(i + 1, {"name": frame, "parent": bound["name"], "pivot": list(HAND)})
    for b in bones:
        if b.get("parent") == bound["name"] and b["name"] != frame:
            b["parent"] = frame
    anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
    an = json.load(open(anim_p, encoding="utf-8"))
    an["animations"][f"animation.grimoire.{g}.hand_frame"] = {"loop": True, "bones": {frame: {
        "rotation": [f"c.is_first_person ? {FP_FRAME[i]} : {TP_FRAME[i]}" for i in range(3)],
        "position": [HAND_BOUND[i] - HAND[i] for i in range(3)]}}}
    _dump(anim_p, an)
    att_p = os.path.join(RP, "attachables", f"{ITEMS[g]}.json")
    att = json.load(open(att_p, encoding="utf-8"))
    d = att["minecraft:attachable"]["description"]
    d["animations"]["hand_frame"] = f"animation.grimoire.{g}.hand_frame"
    if "hand_frame" not in d["scripts"]["animate"]:
        d["scripts"]["animate"].insert(0, "hand_frame")
    _dump(att_p, att)
    print(f"    {g}: hand frame bone added")


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
