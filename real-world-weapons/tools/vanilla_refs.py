"""
Regenerate tools/vanilla_refs.json — the list of vanilla identifiers this add-on
depends on, each verified against Mojang/bedrock-samples (only names are stored,
no Mojang files are copied).

    python3 tools/vanilla_refs.py /path/to/bedrock-samples
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def strip(t):
    return re.sub(r"(?<![:\"])//[^\n]*", "", t)


def main(samples):
    rp = os.path.join(samples, "resource_pack")
    bp = os.path.join(samples, "behavior_pack")
    meta = os.path.join(samples, "metadata")
    version = json.load(open(os.path.join(samples, "version.json")))["latest"]["version"]
    sd = json.loads(strip(open(os.path.join(rp, "sounds", "sound_definitions.json")).read()))["sound_definitions"]
    sound_files = sorted({(s if isinstance(s, str) else s["name"]) for v in sd.values() for s in v.get("sounds", [])})
    particles = []
    for p in glob.glob(os.path.join(rp, "particles", "*.json")):
        m = re.search(r'"identifier"\s*:\s*"([^"]+)"', open(p).read())
        if m:
            particles.append(m.group(1))
    particles = sorted(set(particles))
    rcs = set()
    for p in glob.glob(os.path.join(rp, "render_controllers", "*.json")):
        rcs |= set(json.loads(strip(open(p).read()))["render_controllers"].keys())
    q = json.load(open(os.path.join(meta, "molang_modules", "mojang-molang-queries.json")))
    queries = sorted(x["name"].split(".", 1)[1] for x in q["queries"])
    items = sorted(x["name"] for x in json.load(open(os.path.join(meta, "vanilladata_modules", "mojang-items.json")))["data_items"])
    tags_used = set()
    for p in glob.glob(os.path.join(bp, "recipes", "*.json")):
        for m in re.finditer(r'"tag"\s*:\s*"([^"]+)"', open(p).read()):
            tags_used.add(m.group(1))
    attach_mats = set()
    for p in glob.glob(os.path.join(rp, "attachables", "*.json")):
        d = json.loads(strip(open(p).read()))
        attach_mats |= set(d["minecraft:attachable"]["description"].get("materials", {}).values())
    out = {
        "source": f"Mojang/bedrock-samples {version}",
        "sound_events": sorted(sd.keys()),
        "sound_files": sound_files,
        "particles": particles,
        "render_controllers": sorted(rcs),
        "attachable_materials": sorted(attach_mats),
        "molang_queries": queries,
        "items": items,
        "recipe_tags": sorted(tags_used),
        "textures": ["textures/misc/enchanted_item_glint"],
        "player_bones": ["root", "waist", "body", "head", "hat", "cape", "leftarm", "leftsleeve", "leftitem", "rightarm",
                          "rightsleeve", "rightitem", "leftleg", "leftpants", "rightleg", "rightpants", "jacket"],
    }
    assert os.path.exists(os.path.join(rp, "textures", "misc", "enchanted_item_glint.png"))
    json.dump(out, open(os.path.join(HERE, "vanilla_refs.json"), "w"), indent=1)
    print("wrote vanilla_refs.json from", version, {k: len(v) for k, v in out.items() if isinstance(v, list)})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/home/user/mojang/bedrock-samples")
