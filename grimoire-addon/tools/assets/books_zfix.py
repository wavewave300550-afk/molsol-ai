"""Post-step for the three held books (runs after books_dn / books_dw / books_ed).

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


def build(pack):
    for g in ("book_dw", "book_dn", "book_ed"):
        geo_p = os.path.join(RP, "models", "entity", f"{g}.geo.json")
        if not os.path.exists(geo_p):
            continue
        geo = json.load(open(geo_p, encoding="utf-8"))
        bones = geo["minecraft:geometry"][0]["bones"]
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
