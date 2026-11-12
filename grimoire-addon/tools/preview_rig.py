#!/usr/bin/env python3
"""Hand-placement check: vanilla player rig (first and third person) holding an attachable.

  python3 tools/preview_rig.py trident     # validation with vanilla's own trident attachable
  python3 tools/preview_rig.py books       # the six grimoires
The bound bone is re-parented to the player's hand bone with its pivot on the hand pivot (the documented binding
rule); poses use vanilla's player animations (holding / first_person.empty_hand). Offline renders, not screenshots.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from preview import bundle, sheet, TMP, OUT, RP  # noqa: E402

VAN = os.environ.get("GRIMOIRE_VANILLA_RP", "/tmp/claude-0/-home-user-molsol-ai/1f348b4e-de82-53f0-a823-d92dc5bb7691/scratchpad/bs/resource_pack")
PLAYER = {"geo": f"{VAN}/models/entity/humanoid.custom.geo.json", "geoId": "geometry.humanoid.custom", "bindTo": "rightItem"}
FIRST = [{"file": f"{VAN}/animations/player_firstperson.animation.json", "name": "animation.player.first_person.empty_hand"}]
THIRD = [{"file": f"{VAN}/animations/player.animation.json", "name": "animation.player.holding"}]
EYE = [0, 27.6, 0]


def views(job_base, item_bone, anims_first, anims_third, frames_extra, label):
    jobs, cells = [], []
    for i, (name, fp, cam, use, v) in enumerate([
        ("third person 3/4", False, {"yaw": -35, "pitch": 12, "dist": 46, "target": [-4, 17, -4], "fov": 40}, anims_third, {}),
        ("third person front", False, {"yaw": 0, "pitch": 6, "dist": 46, "target": [-4, 17, -4], "fov": 40}, anims_third, {}),
        ("first person", True, {"eye": EYE, "fov": 60}, anims_first, {}),
        ("first person, preparing", True, {"eye": EYE, "fov": 60}, anims_first, {"ck": 1}),
    ]):
        out = f"{TMP}/rig_{label}_{i}.png"
        job = dict(job_base)
        job.update({"out": out, "size": 360, "aspect": 16 / 9 if fp else 1, "camera": cam,
                    "rig": {**PLAYER, "anims": FIRST if fp else THIRD, "firstPerson": fp, "itemBone": item_bone},
                    "frames": [{"t": 0.5, "anims": use, "c": {"is_first_person": 1 if fp else 0}, "v": v,
                                "q": {"is_using_item": 1 if v.get("ck") else 0}, **frames_extra}]})
        jobs.append(job)
        cells.append((out, f"{label} - {name}"))
    return jobs, cells


def run(jobs):
    os.makedirs(TMP, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=TMP) as f:
        json.dump(jobs, f)
    subprocess.run(["node", "tools/preview/render.mjs", f.name], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def main():
    bundle()
    what = sys.argv[1] if len(sys.argv) > 1 else "books"
    jobs, cells = [], []
    if what == "trident":
        anim = f"{VAN}/animations/trident.animation.json"
        import glob
        for f in glob.glob(f"{VAN}/animations/*.json"):
            if "animation.trident.wield_third_person" in open(f).read():
                anim = f
        base = {"geo": f"{VAN}/models/entity/trident.geo.json", "textures": {"default": f"{RP}/textures/entity/grimoire/book_pressure.png"},
                "anims": [{"file": anim, "name": "animation.trident.wield_first_person"}, {"file": anim, "name": "animation.trident.wield_third_person"}]}
        j, c = views(base, "pole", [0], [1], {}, "trident")
        jobs += j
        cells += c
    else:
        for s in ("pressure", "ice", "blood", "plasma", "darkness", "prism_light"):
            n = f"animation.grimoire.book_{s}"
            keys = ["pose", "closed", "open", "charge", "emblem"] + (["extras"] if s in ("plasma", "darkness", "prism_light") else [])
            base = {"geo": f"{RP}/models/entity/grimoire/book_{s}.geo.json",
                    "textures": {"default": f"{RP}/textures/entity/grimoire/book_{s}.png", "flow": f"{RP}/textures/entity/grimoire/book_{s}_flow.png"},
                    "anims": [{"file": f"{RP}/animations/grimoire/book_{s}.animation.json", "name": f"{n}.{k}"} for k in keys], "flow": True}
            closed = [0, 1, 4] + ([5] if len(keys) > 5 else [])
            j, c = views(base, "book", closed, closed, {}, s)
            # the "preparing" view plays open + charge instead of closed
            j[3]["frames"][0]["anims"] = [0, 2, 3, 4] + ([5] if len(keys) > 5 else [])
            jobs += j
            cells += c
    run(jobs)
    out = os.path.join(OUT, f"hand_{what}.png")
    print(sheet(cells, 4, out, f"Hand placement check on the vanilla player rig: {what} (offline render)"))


if __name__ == "__main__":
    main()
