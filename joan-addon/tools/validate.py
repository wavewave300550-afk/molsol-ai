"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Cross-checks every reference between files that the game resolves at load
time, plus the identifiers used by the scripts, against the packs themselves
and the vanilla reference index (tools/vanilla/reference.json, extracted from
Mojang/bedrock-samples 1.26.60).
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
BP = os.path.join(ROOT, "build", "Joan_BP")
RP = os.path.join(ROOT, "build", "Joan_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))

errors: list = []
count = {"n": 0}


def check(cond, msg):
    count["n"] += 1
    if not cond:
        errors.append(msg)
    return cond


def rel(p):
    return os.path.relpath(p, ROOT)


def load_all(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        try:
            with open(p, encoding="utf-8") as f:
                out[p] = json.load(f)
            check(True, "")
        except Exception as e:  # noqa: BLE001
            check(False, f"invalid JSON {rel(p)}: {e}")
    return out


bpj = load_all(BP)
rpj = load_all(RP)

# ------------------------------------------------------------------ Molang hygiene
VANILLA_QUERIES = {
    "life_time", "modified_move_speed", "modified_distance_moved", "target_x_rotation", "target_y_rotation", "anim_time",
    "property", "is_on_ground", "ground_speed", "vertical_speed", "delta_time", "body_y_rotation", "all_animations_finished",
    "frame_alpha", "is_alive", "has_target", "time_stamp", "position_delta", "is_moving",
}
MOLANG_FUNCS = {"sin", "cos", "abs", "clamp", "lerp", "min", "max", "random", "floor", "ceil", "mod", "sqrt", "pow", "round",
                "trunc", "exp", "ln", "atan2", "asin", "acos", "atan", "random_integer", "die_roll", "hermite_blend", "lerprotate",
                "pi", "sign", "copy_sign", "min_angle", "inverse_lerp"}


def molang_ok(expr, where, props=None):
    if not isinstance(expr, str):
        return
    depth = 0
    for ch in expr:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            break
    check(depth == 0, f"{where}: unbalanced parentheses in {expr!r}")
    for q in re.findall(r"\b(?:query|q)\.([a-z_]+)", expr):
        check(q in VANILLA_QUERIES, f"{where}: query.{q} is not a query used by vanilla packs")
    for fn in re.findall(r"\bmath\.([a-z_0-9]+)", expr, flags=re.IGNORECASE):
        check(fn.lower() in MOLANG_FUNCS, f"{where}: unknown math.{fn}")
    if props is not None:
        for name in re.findall(r"query\.property\('([^']+)'\)", expr):
            check(name in props, f"{where}: property {name} is not defined on the entity")


def walk_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for x in node:
            yield from walk_strings(x)
    elif isinstance(node, dict):
        for x in node.values():
            yield from walk_strings(x)


# ------------------------------------------------------------------ manifests
bpm = bpj[os.path.join(BP, "manifest.json")]
rpm = rpj[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", u), f"bad uuid {u}")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on the RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on the BP")
script = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script) == 1 and os.path.exists(os.path.join(BP, script[0]["entry"])), "script entry missing")
installed = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")))["version"]
check(deps.get("@minecraft/server") == installed, f"manifest @minecraft/server {deps.get('@minecraft/server')} != typings {installed}")
for root in (BP, RP):
    check(os.path.exists(os.path.join(root, "pack_icon.png")), f"pack_icon missing in {rel(root)}")

# ------------------------------------------------------------------ BP entities (properties used by RP molang)
bp_entities = {}
for p, d in bpj.items():
    e = d.get("minecraft:entity") if isinstance(d, dict) else None
    if e:
        bp_entities[e["description"]["identifier"]] = e
allowed_components = set(REF["entity_components"])
for ident, e in bp_entities.items():
    groups = [e.get("components", {})] + list(e.get("component_groups", {}).values())
    for g in groups:
        for comp in g:
            check(comp in allowed_components, f"{ident}: component {comp} not used by any vanilla entity")
    events = e.get("events", {})
    for name, ev in events.items():
        for key in ("add", "remove"):
            for gname in ev.get(key, {}).get("component_groups", []):
                check(gname in e.get("component_groups", {}), f"{ident}: event {name} refers to unknown group {gname}")
    timer = e.get("components", {}).get("minecraft:timer")
    if timer:
        check(timer["time_down_event"]["event"] in events, f"{ident}: timer event missing")
    for pname, pdef in e["description"].get("properties", {}).items():
        check(pname.startswith("joan:"), f"{ident}: property {pname} must be namespaced")
        check(pdef.get("client_sync") is True, f"{ident}: property {pname} must be client_sync for the renderer")
    if ident == "joan:joan_of_arc":
        comps = e["components"]
        check("minecraft:boss" in comps, "Joan needs minecraft:boss (boss bar)")
        check(e["description"].get("is_spawnable") is True, "Joan must be spawnable (spawn egg)")

# ------------------------------------------------------------------ geometry
geos = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            geos[g["description"]["identifier"]] = g
check(len(geos) == 5, f"expected 5 geometries, found {len(geos)}")
geo_bones = {}
geo_locators = {}
for gid, g in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bone names")
    geo_bones[gid] = set(names)
    geo_locators[gid] = {k for b in g["bones"] for k in b.get("locators", {})}
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for b in g["bones"]:
        if b.get("parent"):
            check(b["parent"] in parents, f"{gid}: bone {b['name']} has unknown parent")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative cube size in {b['name']}")
            check(len(c["uv"]) > 0, f"{gid}: cube without mapped faces in {b['name']}")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                u0, u1 = sorted((u, u + w))
                v0, v1 = sorted((v, v + h))
                check(0 <= u0 and u1 <= W and 0 <= v0 and v1 <= H, f"{gid}: {face} uv out of bounds in {b['name']}")
    for n in names:
        seen, cur = set(), n
        while cur:
            if cur in seen:
                check(False, f"{gid}: bone cycle at {n}")
                break
            seen.add(cur)
            cur = parents.get(cur)

# ------------------------------------------------------------------ animations, controllers, render controllers
anims = {}
for p, d in rpj.items():
    if isinstance(d, dict) and isinstance(d.get("animations"), dict) and p.endswith(".animation.json"):
        anims.update(d["animations"])
ctrls = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "animation_controllers" in d:
        ctrls.update(d["animation_controllers"])
rcs = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "render_controllers" in d and isinstance(d["render_controllers"], dict):
        rcs.update(d["render_controllers"])
for name, a in anims.items():
    length = a.get("animation_length")
    for bone, chans in a.get("bones", {}).items():
        for ch, vals in chans.items():
            check(ch in ("rotation", "position", "scale"), f"{name}: unknown channel {ch}")
            if isinstance(vals, dict):
                times = sorted(float(t) for t in vals)
                check(all(0 <= t <= (length or 1e9) + 1e-6 for t in times), f"{name}/{bone}: keyframe outside animation_length")
            for s in walk_strings(vals):
                molang_ok(s, f"{name}/{bone}")
    for kind in ("sound_effects", "particle_effects"):
        for t in a.get(kind, {}):
            check(length is None or float(t) <= length + 1e-6, f"{name}: {kind} at {t} beyond length")

sound_defs = rpj[os.path.join(RP, "sounds", "sound_definitions.json")]["sound_definitions"]
for sname, sd in sound_defs.items():
    for s in sd["sounds"]:
        check(os.path.exists(os.path.join(RP, s["name"] + ".ogg")), f"sound file {s['name']}.ogg missing")
particle_ids = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "particle_effect" in d:
        desc = d["particle_effect"]["description"]
        check(desc["identifier"] not in particle_ids, f"duplicate particle {desc['identifier']}")
        particle_ids[desc["identifier"]] = d
        check(os.path.exists(os.path.join(RP, desc["basic_render_parameters"]["texture"] + ".png")), f"particle texture missing for {desc['identifier']}")
        check(desc["basic_render_parameters"]["material"] in ("particles_alpha", "particles_blend", "particles_opaque"),
              f"{desc['identifier']}: material not used by vanilla particles")
        for s in walk_strings(d["particle_effect"]["components"]):
            molang_ok(s, desc["identifier"])
        bb = d["particle_effect"]["components"].get("minecraft:particle_appearance_billboard", {})
        uv = bb.get("uv", {})
        if "uv" in uv:
            check(uv["uv"][0] + uv["uv_size"][0] <= uv["texture_width"] and uv["uv"][1] + uv["uv_size"][1] <= uv["texture_height"],
                  f"{desc['identifier']}: uv outside the atlas")
item_tex = rpj[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
for k, val in item_tex.items():
    check(os.path.exists(os.path.join(RP, val["textures"] + ".png")), f"item texture {val['textures']} missing")

client_entities = {}
for p, d in rpj.items():
    ce = d.get("minecraft:client_entity") if isinstance(d, dict) else None
    if not ce:
        continue
    desc = ce["description"]
    ident = desc["identifier"]
    client_entities[ident] = desc
    props = set(bp_entities.get(ident, {}).get("description", {}).get("properties", {}).keys())
    check(ident in bp_entities, f"{ident}: client entity without a behaviour entity")
    for gid in desc.get("geometry", {}).values():
        check(gid in geos, f"{ident}: geometry {gid} not defined")
    for tex in desc.get("textures", {}).values():
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"{ident}: texture {tex}.png missing")
    egg = desc.get("spawn_egg", {}).get("texture")
    if egg:
        check(egg in item_tex, f"{ident}: spawn egg texture {egg} not in item_texture.json")
    bones = set()
    locators = set()
    for gid in desc.get("geometry", {}).values():
        bones |= geo_bones.get(gid, set())
        locators |= geo_locators.get(gid, set())
    amap = desc.get("animations", {})
    for short, full in amap.items():
        if full.startswith("controller."):
            check(full in ctrls, f"{ident}: controller {full} missing")
            ctrl = ctrls.get(full, {})
            states = ctrl.get("states", {})
            check(ctrl.get("initial_state", "default") in states, f"{full}: initial state missing")
            for sname, st in states.items():
                for an in st.get("animations", []):
                    key = an if isinstance(an, str) else list(an)[0]
                    check(key in amap, f"{full}/{sname}: animation {key} not in {ident} animations")
                for tr in st.get("transitions", []):
                    (target, cond), = tr.items()
                    check(target in states, f"{full}/{sname}: transition to unknown state {target}")
                    molang_ok(cond, f"{full}/{sname}", props)
                for s in st.get("on_entry", []) + st.get("on_exit", []):
                    molang_ok(s, f"{full}/{sname}", props)
        else:
            check(full in anims, f"{ident}: animation {full} missing")
            a = anims.get(full, {})
            for b in a.get("bones", {}):
                check(b in bones, f"{ident}: {full} animates bone {b} missing from its geometry")
            for s in walk_strings(a.get("bones", {})):
                molang_ok(s, f"{ident}:{full}", props)
            for t, effs in a.get("sound_effects", {}).items():
                for eff in effs if isinstance(effs, list) else [effs]:
                    snd = desc.get("sound_effects", {}).get(eff["effect"])
                    check(snd in sound_defs, f"{ident}: {full} sound effect {eff['effect']} -> {snd} undefined")
            for t, effs in a.get("particle_effects", {}).items():
                for eff in effs if isinstance(effs, list) else [effs]:
                    pid = desc.get("particle_effects", {}).get(eff["effect"])
                    check(pid in particle_ids, f"{ident}: {full} particle {eff['effect']} -> {pid} undefined")
                    if "locator" in eff:
                        check(eff["locator"] in locators, f"{ident}: locator {eff['locator']} not in geometry")
    for entry in desc.get("scripts", {}).get("animate", []):
        key = entry if isinstance(entry, str) else list(entry)[0]
        check(key in amap, f"{ident}: animate refers to unknown {key}")
        if isinstance(entry, dict):
            molang_ok(list(entry.values())[0], f"{ident}: animate {key}", props)
    for section in ("initialize", "pre_animation"):
        for s in desc.get("scripts", {}).get(section, []):
            molang_ok(s, f"{ident}: {section}", props)
    for entry in desc.get("render_controllers", []):
        name = entry if isinstance(entry, str) else list(entry)[0]
        if isinstance(entry, dict):
            molang_ok(list(entry.values())[0], f"{ident}: render condition", props)
        check(name in rcs, f"{ident}: render controller {name} missing")
        rc = rcs.get(name, {})
        arrays = rc.get("arrays", {})
        g = rc.get("geometry", "").split(".", 1)[-1]
        check(g in desc.get("geometry", {}), f"{ident}: {name} geometry key {g} missing")
        for t in rc.get("textures", []):
            if t.startswith("Array."):
                arr = t.split("[")[0]
                found = arrays.get("textures", {}).get(arr)
                check(found is not None, f"{ident}: {name} array {arr} missing")
                for tt in found or []:
                    check(tt.split(".", 1)[-1] in desc.get("textures", {}), f"{ident}: {name} texture {tt} missing")
                molang_ok(t[t.index("["):], f"{ident}: {name} texture index", props)
            else:
                check(t.split(".", 1)[-1] in desc.get("textures", {}), f"{ident}: {name} texture {t} missing")
        for m in rc.get("materials", []):
            for mv in m.values():
                check(mv.split(".", 1)[-1] in desc.get("materials", {}), f"{ident}: {name} material {mv} missing")
    for pid in desc.get("particle_effects", {}).values():
        check(pid in particle_ids, f"{ident}: particle {pid} not defined")
    for sid in desc.get("sound_effects", {}).values():
        check(sid in sound_defs, f"{ident}: sound {sid} not defined")
for ident in bp_entities:
    check(ident in client_entities, f"{ident}: no client entity")

# ------------------------------------------------------------------ items, recipes, lang
bp_items = {}
for p, d in bpj.items():
    it = d.get("minecraft:item") if isinstance(d, dict) else None
    if it:
        bp_items[it["description"]["identifier"]] = it
EXTRA_ITEM = {"minecraft:glint", "minecraft:rarity"}
for ident, it in bp_items.items():
    for comp in it["components"]:
        check(comp in set(REF["item_components"]) | EXTRA_ITEM, f"{ident}: unknown item component {comp}")
    check(it["components"]["minecraft:icon"]["textures"]["default"] in item_tex, f"{ident}: icon missing from item_texture.json")
for p, d in bpj.items():
    r = d.get("minecraft:recipe_shaped") if isinstance(d, dict) else None
    if r:
        check(r["result"]["item"] in bp_items, "recipe result is not one of our items")
        for k, ing in r["key"].items():
            check(ing["item"].startswith("minecraft:"), f"recipe ingredient {ing}")
        used = set("".join(r["pattern"])) - {" "}
        check(used <= set(r["key"]), "recipe pattern uses an undefined key")
lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line:
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
for ident in bp_entities:
    check(f"entity.{ident}.name" in lang, f"lang key for entity {ident} missing")
check("item.spawn_egg.entity.joan:joan_of_arc.name" in lang, "spawn egg name missing")
for ident in bp_items:
    check(f"item.{ident}.name" in lang, f"lang key for item {ident} missing")

# ------------------------------------------------------------------ scripts vs data
js = ""
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    src = open(p, encoding="utf-8").read()
    js += src + "\n"
    for imp in re.findall(r'from "(\.[^"]+)"', src):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{rel(p)}: import {imp} not found")
for pid in set(re.findall(r'"(joan:[a-z_]+)"', js)):
    if pid in particle_ids or pid in bp_entities or pid in bp_items or pid.startswith("joan:") and pid.split(":")[1] in (
            "phase", "action", "seq", "fire", "state", "stake", "sinking", "owner", "home", "started", "darken", "brighten",
            "despawn", "road", "skill", "summon", "clear", "joan_of_arc"):
        check(True, "")
    else:
        check(False, f"script uses unknown id {pid}")
for snd in set(re.findall(r'(?:sound\([^,]+,\s*|playSound\()"([a-z0-9_.]+)"', js)) | set(re.findall(r'"(joan\.[a-z_.]+)"', js)):
    check(snd in sound_defs or snd in REF["sounds"], f"script sound {snd} undefined")
for eff in set(re.findall(r'emit(?:Segment)?\([^"]*"([a-z_]+:[a-z_]+)"', js)):
    check(eff in particle_ids, f"script particle {eff} undefined")
for ent in set(re.findall(r'"(minecraft:[a-z_]+)"', js)):
    pass
joan_props = set(bp_entities["joan:joan_of_arc"]["description"]["properties"])
for prop in set(re.findall(r'setProperty\(\s*"([a-z_:]+)"', js)):
    check(prop in joan_props, f"script sets unknown Joan property {prop}")
for prop in set(re.findall(r'setProp\([^,]+,\s*"([a-z_:]+)"', js)):
    owners = [i for i, e in bp_entities.items() if prop in e["description"].get("properties", {})]
    check(bool(owners), f"script sets minion property {prop} that no entity defines")
for ev in set(re.findall(r'triggerEvent\("([a-z_:]+)"\)', js)):
    check(ev in bp_entities["joan:joan_of_arc"]["events"], f"script triggers unknown event {ev}")

# ------------------------------------------------------------------ textures
for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(p)
    check(im.mode == "RGBA", f"{rel(p)} is not RGBA")
    w, h = im.size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{rel(p)} size {im.size} is not a power of two")
for ident, desc in client_entities.items():
    for gid in desc.get("geometry", {}).values():
        g = geos.get(gid)
        if not g:
            continue
        W, H = g["description"]["texture_width"], g["description"]["texture_height"]
        for tex in desc.get("textures", {}).values():
            p = os.path.join(RP, tex + ".png")
            if os.path.exists(p) and os.path.basename(tex).split("_")[0] in gid:
                tw, th = Image.open(p).size
                check(tw * H == th * W, f"{ident}: {tex} aspect differs from {gid}")

print(f"{count['n']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
