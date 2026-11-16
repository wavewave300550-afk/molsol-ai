"""
Builds tools/vanilla/reference.json - the vanilla identifiers the validator and the smoke test
check against - from a local Mojang/bedrock-samples checkout (1.26.60) and @minecraft/vanilla-data.

    python3 tools/vanilla/make_reference.py <path to bedrock-samples>
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def load(p):
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"//[^\n]*", "", t)
    t = re.sub(r",(\s*[}\]])", r"\1", t)
    return json.loads(t)


def vd_ids(name):
    src = open(os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", f"mojang-{name}.d.ts"), encoding="utf-8").read()
    return sorted(set(re.findall(r"[\"'](minecraft:[a-z0-9_.]+)[\"']", src)))


def main(samples):
    bp, rp = os.path.join(samples, "behavior_pack"), os.path.join(samples, "resource_pack")
    sounds = sorted(load(os.path.join(rp, "sounds", "sound_definitions.json"))["sound_definitions"].keys())
    particles = []
    for p in glob.glob(os.path.join(rp, "particles", "*.json")):
        try:
            particles.append(load(p)["particle_effect"]["description"]["identifier"])
        except Exception:
            pass
    entities = {}
    for p in glob.glob(os.path.join(bp, "entities", "*.json")):
        try:
            e = load(p)["minecraft:entity"]
        except Exception:
            continue
        fam = set(e.get("components", {}).get("minecraft:type_family", {}).get("family", []))
        for g in e.get("component_groups", {}).values():
            fam |= set(g.get("minecraft:type_family", {}).get("family", []))
        entities[e["description"]["identifier"]] = sorted(fam)
    loot = sorted(os.path.relpath(p, bp).replace(os.sep, "/") for p in glob.glob(os.path.join(bp, "loot_tables", "**", "*.json"), recursive=True))
    ref = {
        "source": "Mojang/bedrock-samples 1.26.60.5 + @minecraft/vanilla-data 1.26.60",
        "sounds": sounds,
        "particles": sorted(particles),
        "entities": entities,
        "effects": [x.split(":")[1] for x in vd_ids("effect")],
        "blocks": vd_ids("block"),
        "items": vd_ids("item"),
        "loot_tables": loot,
        "entity_types": vd_ids("entity"),
        "dimensions": vd_ids("dimension"),
    }
    with open(os.path.join(HERE, "reference.json"), "w", encoding="utf-8") as f:
        json.dump(ref, f, indent=1)
        f.write("\n")
    print({k: len(v) for k, v in ref.items() if not isinstance(v, str)})


if __name__ == "__main__":
    main(sys.argv[1])
