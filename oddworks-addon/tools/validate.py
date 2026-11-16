"""
Static cross-reference validator for the built packs (build/ODDWORKS_BP + build/ODDWORKS_RP).

Checks JSON, manifests, every reference between items / attachables / geometry / textures /
animations / controllers / render controllers / client & server entities / particles / sounds /
lang / recipes / loot tables, geometry UV bounds and bone names used by animations, and every
identifier the compiled scripts use (particles, sounds, effects, entities, blocks, player poses,
spawn events) against the packs and the vanilla 1.26.60 reference.

    python3 tools/validate.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "ODDWORKS_BP")
RP = os.path.join(ROOT, "build", "ODDWORKS_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json"), encoding="utf-8"))

errors: list[str] = []
checks = 0


def ok(cond: bool, msg: str) -> bool:
    global checks
    checks += 1
    if not cond:
        errors.append(msg)
    return cond


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(p):
    return os.path.relpath(p, ROOT)


VANILLA_MATERIALS = {"entity", "entity_alphatest", "entity_alphablend", "entity_emissive", "entity_emissive_alpha",
                     "entity_alphatest_glint", "entity_beam_additive", "entity_nocull"}
VANILLA_RENDER_CONTROLLERS = {"controller.render.item_default"}
PARTICLE_MATERIALS = {"particles_add", "particles_alpha", "particles_blend"}
# runtime actor types that have no data-driven definition (item drops, falling blocks, leash knots ...)
HARDCODED_ACTORS = {"minecraft:item", "minecraft:falling_block", "minecraft:leash_knot", "minecraft:painting"}
MOLANG_CTX = re.compile(r"\b(c|context)\.(is_first_person|item_slot|owning_entity)\b")


def all_json(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        try:
            d = load(p)
            ok(True, "")
            if isinstance(d, dict):
                out[p] = d
        except Exception as e:  # noqa: BLE001
            ok(False, f"invalid JSON {rel(p)}: {e}")
    return out


def main():
    if not os.path.isdir(BP) or not os.path.isdir(RP):
        print("build first: python3 tools/build.py")
        return 2
    bpj, rpj = all_json(BP), all_json(RP)

    # ------------------------------------------------------------------ manifests
    bpm, rpm = bpj[os.path.join(BP, "manifest.json")], rpj[os.path.join(RP, "manifest.json")]
    uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
    ok(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
    ok(any(d.get("uuid") == rpm["header"]["uuid"] for d in bpm["dependencies"]), "BP does not depend on RP")
    ok(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP does not depend on BP")
    script = [m for m in bpm["modules"] if m["type"] == "script"]
    ok(len(script) == 1 and os.path.exists(os.path.join(BP, script[0]["entry"])), "script entry missing")
    ok(any(d.get("module_name") == "@minecraft/server" for d in bpm["dependencies"]), "missing @minecraft/server dependency")
    for m in (bpm, rpm):
        ok(m["header"]["min_engine_version"] == [1, 26, 60], "min_engine_version should be 1.26.60")
    for p in (BP, RP):
        ok(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack icon missing in {rel(p)}")

    # ------------------------------------------------------------------ lang
    lang = {}
    for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
        if "=" in line:
            k, v = line.rstrip("\n").split("=", 1)
            lang[k] = v

    # ------------------------------------------------------------------ RP indexes
    item_tex = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
    for k, v in item_tex.items():
        ok(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {k} -> missing png")
    geos = {}
    for p, d in rpj.items():
        if "minecraft:geometry" in d:
            for g in d["minecraft:geometry"]:
                geos[g["description"]["identifier"]] = (p, g)
    anims, ctrls = {}, {}
    for p, d in rpj.items():
        for k, v in d.get("animations", {}).items():
            ok(k not in anims, f"duplicate animation {k}")
            anims[k] = v
        for k, v in d.get("animation_controllers", {}).items():
            ctrls[k] = v
    rcs = set(VANILLA_RENDER_CONTROLLERS)
    for p, d in rpj.items():
        rcs |= set(d.get("render_controllers", {}).keys()) if isinstance(d.get("render_controllers"), dict) else set()
    sound_defs = load(os.path.join(RP, "sounds", "sound_definitions.json"))["sound_definitions"]
    for sid, sd in sound_defs.items():
        for snd in sd["sounds"]:
            ok(os.path.exists(os.path.join(RP, snd["name"] + ".ogg")), f"sound {sid}: missing {snd['name']}.ogg")
    all_sounds = set(sound_defs) | set(REF["sounds"])
    particles = {}
    for p, d in rpj.items():
        if "particle_effect" in d:
            desc = d["particle_effect"]["description"]
            particles[desc["identifier"]] = d
            brp = desc["basic_render_parameters"]
            ok(brp["material"] in PARTICLE_MATERIALS, f"{desc['identifier']}: bad material")
            ok(os.path.exists(os.path.join(RP, brp["texture"] + ".png")), f"{desc['identifier']}: texture missing")
            comps = d["particle_effect"]["components"]
            ok(any(k.startswith("minecraft:emitter_rate") for k in comps), f"{desc['identifier']}: no emitter rate")
            ok(any(k.startswith("minecraft:emitter_shape") for k in comps), f"{desc['identifier']}: no emitter shape")
            bb = comps.get("minecraft:particle_appearance_billboard", {})
            if bb.get("facing_camera_mode") in ("lookat_direction", "direction_x", "direction_y", "direction_z"):
                ok("direction" in bb, f"{desc['identifier']}: directional billboard without direction")
    all_particles = set(particles) | set(REF["particles"])

    # ------------------------------------------------------------------ geometry sanity
    def bone_names(geo):
        return {b["name"].lower() for b in geo["bones"]}

    for gid, (p, g) in geos.items():
        W, H = g["description"]["texture_width"], g["description"]["texture_height"]
        names = [b["name"] for b in g["bones"]]
        ok(len(names) == len(set(names)), f"{gid}: duplicate bone names")
        for b in g["bones"]:
            if "parent" in b:
                ok(b["parent"] in names, f"{gid}: bone {b['name']} parent {b['parent']} missing")
            if "binding" in b:
                ok("item_slot_to_bone_name" in b["binding"], f"{gid}: odd binding {b['binding']}")
            for c in b.get("cubes", []):
                for face, fd in c.get("uv", {}).items():
                    u, v = fd["uv"]
                    w, h = fd["uv_size"]
                    ok(0 <= min(u, u + w) and max(u, u + w) <= W and 0 <= min(v, v + h) and max(v, v + h) <= H,
                       f"{gid}: bone {b['name']} {face} UV out of bounds")

    def check_texture(path_noext, geo=None):
        png = os.path.join(RP, path_noext + ".png")
        if not ok(os.path.exists(png), f"texture missing {path_noext}"):
            return
        im = Image.open(png)
        ok(im.width & (im.width - 1) == 0 and im.height & (im.height - 1) == 0, f"{path_noext}: not power-of-two")
        if geo:
            d = geo["description"]
            ok((im.width, im.height) == (d["texture_width"], d["texture_height"]), f"{path_noext}: size != geometry texture size")

    def check_anim_bones(anim_id, bones):
        a = anims.get(anim_id)
        if not ok(a is not None, f"animation {anim_id} missing"):
            return
        for bn in a.get("bones", {}):
            ok(bn.lower() in bones, f"{anim_id}: animates bone '{bn}' not in geometry")

    def check_client(kind, desc, path):
        geo_ids = desc["geometry"].values()
        bones = set()
        for gid in geo_ids:
            if ok(gid in geos, f"{rel(path)}: geometry {gid} missing"):
                bones |= bone_names(geos[gid][1])
        first_geo = geos.get(next(iter(geo_ids)), (None, None))[1]
        for k, t in desc["textures"].items():
            if t.startswith("textures/misc/"):
                continue
            check_texture(t, first_geo)
        for k, m in desc["materials"].items():
            ok(m in VANILLA_MATERIALS, f"{rel(path)}: unknown material {m}")
        for rc in desc["render_controllers"]:
            name = rc if isinstance(rc, str) else next(iter(rc))
            ok(name in rcs, f"{rel(path)}: render controller {name} missing")
        amap = desc.get("animations", {})
        for key, aid in amap.items():
            if aid.startswith("controller."):
                c = ctrls.get(aid)
                if not ok(c is not None, f"{rel(path)}: controller {aid} missing"):
                    continue
                states = c["states"]
                ok(c.get("initial_state", "default") in states, f"{aid}: initial state missing")
                for sname, st in states.items():
                    for a in st.get("animations", []):
                        an = a if isinstance(a, str) else next(iter(a))
                        ok(an in amap, f"{aid}.{sname}: animation key '{an}' not declared in {rel(path)}")
                    for tr in st.get("transitions", []):
                        ok(next(iter(tr)) in states, f"{aid}.{sname}: transition to unknown state")
            else:
                check_anim_bones(aid, bones)
        for a in desc.get("scripts", {}).get("animate", []):
            an = a if isinstance(a, str) else next(iter(a))
            ok(an in amap, f"{rel(path)}: animate '{an}' not declared")
        return bones

    # ------------------------------------------------------------------ BP items / attachables
    items = {}
    for p, d in bpj.items():
        if "minecraft:item" in d:
            it = d["minecraft:item"]
            iid = it["description"]["identifier"]
            items[iid] = it
            comps = it["components"]
            ok(comps.get("minecraft:icon") in item_tex, f"{iid}: icon key missing from item_texture.json")
            ok(comps["minecraft:display_name"]["value"] in lang, f"{iid}: display name not in en_US.lang")
            for k in ("attack_hit", "attack_miss", "attack_critical_hit"):
                s = comps.get("minecraft:swing_sounds", {}).get(k)
                if s:
                    ok(s in all_sounds, f"{iid}: swing sound {s} missing")
            ok(comps.get("minecraft:use_animation", "none") in {"bow", "brush", "camera", "crossbow", "drink", "eat", "none", "spear", "spyglass"},
               f"{iid}: bad use_animation")
    attach = {}
    for p, d in rpj.items():
        if "minecraft:attachable" in d:
            desc = d["minecraft:attachable"]["description"]
            attach[desc["identifier"]] = desc
            ok(desc["identifier"] in items, f"attachable {desc['identifier']} has no item")
            check_client("attachable", desc, p)
            for s in desc.get("scripts", {}).get("pre_animation", []):
                ok(s.strip().endswith(";"), f"{desc['identifier']}: pre_animation statement without ';'")
    for iid in items:
        ok(iid in attach, f"item {iid} has no attachable (would render as a flat sprite)")

    # ------------------------------------------------------------------ entities
    bp_entities = {}
    for p, d in bpj.items():
        if "minecraft:entity" in d:
            e = d["minecraft:entity"]
            bp_entities[e["description"]["identifier"]] = e
    for p, d in rpj.items():
        if "minecraft:client_entity" in d:
            desc = d["minecraft:client_entity"]["description"]
            ok(desc["identifier"] in bp_entities, f"client entity {desc['identifier']} has no BP entity")
            check_client("entity", desc, p)
    for eid in bp_entities:
        ok(f"entity.{eid}.name" in lang, f"{eid}: name missing from lang")
        ok(any(d.get("minecraft:client_entity", {}).get("description", {}).get("identifier") == eid for d in rpj.values()),
           f"{eid}: no client entity")

    # ------------------------------------------------------------------ recipes / loot
    for p, d in bpj.items():
        r = d.get("minecraft:recipe_shaped")
        if r:
            for k, ing in r["key"].items():
                ok(ing["item"] in REF["items"] or ing["item"] in items, f"{rel(p)}: unknown ingredient {ing['item']}")
            ok(r["result"]["item"] in items, f"{rel(p)}: result is not an ODDWORKS item")
            letters = set("".join(r["pattern"])) - {" "}
            ok(letters <= set(r["key"]), f"{rel(p)}: pattern uses undefined keys")
        if "pools" in d:
            for pool in d["pools"]:
                for en in pool["entries"]:
                    if en["type"] == "loot_table":
                        ok(en["name"] in REF["loot_tables"], f"{rel(p)}: loot table {en['name']} not in vanilla")

    # ------------------------------------------------------------------ compiled scripts
    js = ""
    for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
        js += open(p, encoding="utf-8").read() + "\n"
    strings = set(re.findall(r'"([^"\\\n]{2,120})"', js)) | set(re.findall(r"'([^'\\\n]{2,120})'", js))
    known_ids = (set(particles) | set(bp_entities) | set(items) | set(REF["particles"]) | set(REF["entities"]) | set(REF["blocks"])
                 | set(REF["items"]) | set(REF.get("entity_types", [])) | set(REF.get("dimensions", [])) | HARDCODED_ACTORS)
    for s in sorted(strings):
        if re.fullmatch(r"oddworks:[a-z0-9_]+", s):
            ok(s in known_ids or s.startswith("oddworks:sig_") or s.startswith("oddworks:size_") or s in {"oddworks:guide", "oddworks:weather", "oddworks:lights"},
               f"script references unknown id {s}")
        elif re.fullmatch(r"minecraft:[a-z0-9_]+", s):
            ok(s in known_ids, f"script references unknown vanilla id {s}")
        elif re.fullmatch(r"(oddworks|random|mob|block|item|dig|step|hit|use)\.[a-z0-9_.]+", s):
            ok(s in all_sounds, f"script plays unknown sound {s}")
    for eff in set(re.findall(r'(?:addEffect|getEffect|removeEffect)\(\s*"([a-z_]+)"', js)):
        ok(eff in REF["effects"], f"script uses unknown effect {eff}")
    for pose in set(re.findall(r'pose\(\s*\w+\s*,\s*"([a-z_]+)"', js)):
        ok(f"animation.oddworks.player.{pose}" in anims, f"player pose {pose} missing from RP animations")
    for ev in set(re.findall(r"spawnEvent:\s*`oddworks:size_\$\{size\}`", js)):
        pass
    shell = bp_entities.get("oddworks:ice_shell", {})
    for size in ("s", "m", "l", "xl"):
        ok(f"oddworks:size_{size}" in shell.get("events", {}), f"ice_shell missing spawn event size_{size}")
    for cat in set(re.findall(r'"(oddworks:sig_[a-z_]+)"', js)):
        used = any(cat in json.dumps(a) for a in attach.values())
        ok(used, f"signal {cat} is never read by an attachable")
    for snd in set(re.findall(r'"(oddworks\.[a-z_.]+)"', js)):
        ok(snd in sound_defs, f"script sound {snd} not defined")

    print(f"{checks} checks, {len(errors)} errors")
    for e in errors:
        print("  ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
