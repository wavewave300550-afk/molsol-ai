"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Checks JSON syntax, manifests, cross references between every file
(geometry / textures / animations / animation controllers / render
controllers / particles / sounds / blocks / items / lang), model integrity
(UV bounds, bone hierarchy, animated bones exist), Molang references to entity
properties (must exist and be client_sync), and that every identifier the
scripts use (porcelain:* ids, particles, sounds, fogs, effects, vanilla
entities/blocks/items) exists in the packs, in @minecraft/vanilla-data or in
the vanilla reference index (Mojang/bedrock-samples 1.26.60).
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "Porcelain_BP")
RP = os.path.join(ROOT, "build", "Porcelain_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))

errors: list = []
checks = {"count": 0}


def check(cond, msg):
    checks["count"] += 1
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


bp_json = {k: v for k, v in load_all(BP).items() if isinstance(v, dict)}
rp_json = {k: v for k, v in load_all(RP).items() if isinstance(v, dict)}

# ---------------------------------------------------------------- vanilla data (@minecraft/vanilla-data)
VD = os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "index.js")
vd_src = open(VD, encoding="utf-8").read() if os.path.exists(VD) else ""
vanilla_ids = set(re.findall(r'"(minecraft:[a-z0-9_.]+)"', vd_src))
check(len(vanilla_ids) > 1000, "could not read @minecraft/vanilla-data ids")

# ---------------------------------------------------------------- manifests
bpm = bp_json[os.path.join(BP, "manifest.json")]
rpm = rp_json[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", u), f"bad uuid {u}")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
script_mod = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script_mod) == 1 and os.path.exists(os.path.join(BP, script_mod[0]["entry"])), "script entry missing")
pkg = lambda n: json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", n, "package.json")))["version"]  # noqa: E731
check(deps.get("@minecraft/server") == pkg("server"), "manifest @minecraft/server != installed typings")
check(deps.get("@minecraft/server-ui") == pkg("server-ui"), "manifest @minecraft/server-ui != installed typings")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack_icon missing in {rel(p)}")

# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rp_json.items():
    if "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            geos[g["description"]["identifier"]] = (g, p)
check(len(geos) == 6, f"expected 6 geometries, found {len(geos)}")
for gid, (g, p) in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bone names")
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for b in g["bones"]:
        if "parent" in b:
            check(b["parent"] in names, f"{gid}: bone {b['name']} has unknown parent {b['parent']}")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative cube size in {b['name']}")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                u0, u1 = sorted((u, u + w))
                v0, v1 = sorted((v, v + h))
                check(0 <= u0 and u1 <= W and 0 <= v0 and v1 <= H, f"{gid}: {face} uv out of bounds in {b['name']}")
    for n in names:
        seen, cur = set(), n
        while cur:
            if not check(cur not in seen, f"{gid}: bone cycle at {n}"):
                break
            seen.add(cur)
            cur = parents.get(cur)


def geo_bones(gid):
    return {b["name"] for b in geos[gid][0]["bones"]}


# ---------------------------------------------------------------- entities (BP) and their properties
bp_entities = {}
for p, d in bp_json.items():
    if "minecraft:entity" in d:
        e = d["minecraft:entity"]
        ident = e["description"]["identifier"]
        bp_entities[ident] = e
        comps = dict(e.get("components", {}))
        for g in e.get("component_groups", {}).values():
            comps.update(g)
        for c in comps:
            check(c in REF["entity_components"], f"{ident}: unknown entity component {c}")
        for ev, body in e.get("events", {}).items():
            for grp in body.get("add", {}).get("component_groups", []):
                check(grp in e.get("component_groups", {}), f"{ident}: event {ev} adds unknown group {grp}")
        timer = comps.get("minecraft:timer")
        if timer:
            check(timer["time_down_event"]["event"] in e.get("events", {}), f"{ident}: timer event missing")
check(len(bp_entities) == 6, f"expected 6 BP entities, found {len(bp_entities)}")

# ---------------------------------------------------------------- client entities, animations, controllers, render controllers
anims = {}
for p, d in rp_json.items():
    if "animations" in d and "format_version" in d:
        anims.update(d["animations"])
ctrls = {}
for p, d in rp_json.items():
    if "animation_controllers" in d:
        ctrls.update(d["animation_controllers"])
rcs = {}
for p, d in rp_json.items():
    if "render_controllers" in d:
        rcs.update(d["render_controllers"])

MOLANG_PROP = re.compile(r"q(?:uery)?\.property\('([a-z_]+:[a-z_]+)'\)")


def molang_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from molang_strings(k)
            yield from molang_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from molang_strings(v)


client_entities = {}
for p, d in rp_json.items():
    if "minecraft:client_entity" not in d:
        continue
    desc = d["minecraft:client_entity"]["description"]
    ident = desc["identifier"]
    client_entities[ident] = desc
    check(ident in bp_entities, f"client entity {ident} has no behavior entity")
    props = bp_entities.get(ident, {}).get("description", {}).get("properties", {})
    for gk, gid in desc["geometry"].items():
        check(gid in geos, f"{ident}: geometry {gid} not found")
    for tk, tex in desc["textures"].items():
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"{ident}: texture {tex}.png missing")
    bones = set()
    for gid in desc["geometry"].values():
        if gid in geos:
            bones |= geo_bones(gid)
    used_anims = set()
    for short, full in desc.get("animations", {}).items():
        if full.startswith("controller."):
            check(full in ctrls, f"{ident}: animation controller {full} missing")
            ctrl = ctrls.get(full, {})
            states = ctrl.get("states", {})
            check(ctrl.get("initial_state", "default") in states, f"{full}: initial state missing")
            for sname, st in states.items():
                for a in st.get("animations", []):
                    an = a if isinstance(a, str) else list(a.keys())[0]
                    check(an in desc["animations"], f"{full}.{sname}: animation short name {an} not declared on {ident}")
                    used_anims.add(an)
                for tr in st.get("transitions", []):
                    for tgt, cond in tr.items():
                        check(tgt in states, f"{full}.{sname}: transition to unknown state {tgt}")
            for s in molang_strings(ctrl):
                for prop in MOLANG_PROP.findall(s):
                    check(prop in props and props[prop].get("client_sync"), f"{full}: property {prop} missing or not client_sync on {ident}")
        else:
            check(full in anims, f"{ident}: animation {full} missing")
            for bone in anims.get(full, {}).get("bones", {}):
                check(bone in bones, f"{full}: animates unknown bone {bone} (geometry of {ident})")
            for s in molang_strings(anims.get(full, {})):
                for prop in MOLANG_PROP.findall(s):
                    check(prop in props and props[prop].get("client_sync"), f"{full}: property {prop} missing or not client_sync on {ident}")
    for a in desc.get("scripts", {}).get("animate", []):
        an = a if isinstance(a, str) else list(a.keys())[0]
        check(an in desc["animations"], f"{ident}: animate entry {an} not declared")
        used_anims.add(an)
    for short in desc.get("animations", {}):
        check(short in used_anims, f"{ident}: animation {short} is declared but never played")
    for rc in desc["render_controllers"]:
        name = rc if isinstance(rc, str) else list(rc.keys())[0]
        check(name in rcs, f"{ident}: render controller {name} missing")
        r = rcs.get(name, {})
        for s in molang_strings(r):
            for m in re.findall(r"Texture\.([a-z_]+)", s):
                check(m in desc["textures"], f"{name}: Texture.{m} not defined on {ident}")
            for m in re.findall(r"Geometry\.([a-z_]+)", s):
                check(m in desc["geometry"], f"{name}: Geometry.{m} not defined on {ident}")
            for m in re.findall(r"Material\.([a-z_]+)", s):
                check(m in desc["materials"], f"{name}: Material.{m} not defined on {ident}")
            for prop in MOLANG_PROP.findall(s):
                check(prop in props and props[prop].get("client_sync"), f"{name}: property {prop} missing on {ident}")
        for pv in r.get("part_visibility", []):
            for bone in pv:
                if bone != "*":
                    check(bone in bones, f"{name}: part_visibility for unknown bone {bone}")
check(len(client_entities) == 6, f"expected 6 client entities, found {len(client_entities)}")

# ---------------------------------------------------------------- particles, sounds, fogs
particles = set()
for p, d in rp_json.items():
    if "particle_effect" in d:
        desc = d["particle_effect"]["description"]
        particles.add(desc["identifier"])
        tex = desc["basic_render_parameters"]["texture"]
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"particle {desc['identifier']}: texture {tex} missing")
        atlas = Image.open(os.path.join(RP, tex + ".png")) if os.path.exists(os.path.join(RP, tex + ".png")) else None
        for s in molang_strings(d["particle_effect"]["components"]):
            pass
        app = d["particle_effect"]["components"].get("minecraft:particle_appearance_billboard", {})
        uv = app.get("uv", {})
        if atlas and uv:
            u, v = uv["uv"]
            w, h = uv["uv_size"]
            check(u + w <= atlas.size[0] and v + h <= atlas.size[1], f"particle {desc['identifier']}: uv outside atlas")
        mode = app.get("facing_camera_mode")
        check(mode in ("rotate_xyz", "rotate_y", "lookat_xyz", "lookat_y", "lookat_direction", "direction_x", "direction_y",
                       "direction_z", "emitter_transform_xy", "emitter_transform_xz", "emitter_transform_yz"),
              f"particle {desc['identifier']}: bad facing mode {mode}")
sd = rp_json[os.path.join(RP, "sounds", "sound_definitions.json")]["sound_definitions"]
sounds = set(sd)
for ev, d in sd.items():
    for s in d["sounds"]:
        name = s["name"] if isinstance(s, dict) else s
        check(os.path.exists(os.path.join(RP, name + ".ogg")), f"sound {ev}: file {name}.ogg missing")
fogs = set()
for p, d in rp_json.items():
    if "minecraft:fog_settings" in d:
        fogs.add(d["minecraft:fog_settings"]["description"]["identifier"])

# ---------------------------------------------------------------- blocks and items
lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line:
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
terrain = rp_json[os.path.join(RP, "textures", "terrain_texture.json")]["texture_data"]
itemtex = rp_json[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
blocks_json = rp_json[os.path.join(RP, "blocks.json")]
blocks = set()
items = set()
for p, d in bp_json.items():
    if "minecraft:block" in d:
        ident = d["minecraft:block"]["description"]["identifier"]
        blocks.add(ident)
        mi = d["minecraft:block"]["components"]["minecraft:material_instances"]["*"]["texture"]
        check(mi in terrain, f"block {ident}: texture key {mi} missing from terrain_texture.json")
        check(ident in blocks_json, f"block {ident}: missing from blocks.json")
        check(f"tile.{ident}.name" in lang, f"block {ident}: lang key missing")
    if "minecraft:item" in d:
        ident = d["minecraft:item"]["description"]["identifier"]
        items.add(ident)
        icon = d["minecraft:item"]["components"]["minecraft:icon"]
        check(icon in itemtex, f"item {ident}: icon {icon} missing from item_texture.json")
        check(f"item.{ident}.name" in lang, f"item {ident}: lang key missing")
for k, t in list(terrain.items()) + list(itemtex.items()):
    check(os.path.exists(os.path.join(RP, t["textures"] + ".png")), f"texture {t['textures']} missing")
    im = Image.open(os.path.join(RP, t["textures"] + ".png"))
    check(im.size[0] == im.size[1] == 16, f"texture {t['textures']} must be 16x16")
for ident in bp_entities:
    check(f"entity.{ident}.name" in lang, f"entity {ident}: lang key missing")
for p, d in bp_json.items():
    for rk in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
        if rk in d:
            r = d[rk]
            ingredients = list(r.get("key", {}).values()) + r.get("ingredients", [])
            for ing in ingredients + [r["result"]]:
                iid = ing["item"]
                check(iid in items or iid in vanilla_ids, f"recipe {r['description']['identifier']}: unknown item {iid}")
    if "pools" in d:
        for pool in d["pools"]:
            for entry in pool["entries"]:
                if entry["type"] == "item":
                    check(entry["name"] in items or entry["name"] in vanilla_ids, f"loot: unknown item {entry['name']}")
for e in bp_entities.values():
    loot = e.get("components", {}).get("minecraft:loot")
    if loot:
        check(os.path.exists(os.path.join(BP, loot["table"])), f"loot table {loot['table']} missing")
for tex in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    w, h = Image.open(tex).size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"texture {rel(tex)} is not power-of-two ({w}x{h})")

# ---------------------------------------------------------------- scripts: every id they use must exist
js = ""
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    js += open(p, encoding="utf-8").read() + "\n"
config = open(os.path.join(ROOT, "src", "config.ts"), encoding="utf-8").read()
known_porcelain = set(bp_entities) | blocks | items | particles | fogs | {"porcelain:fractured_mandate"}
props_all = set()
for e in bp_entities.values():
    props_all |= set(e["description"].get("properties", {}))
for ident in set(re.findall(r'"(porcelain:[a-z_]+)"', js)):
    if ident in ("porcelain:skill", "porcelain:leave", "porcelain:join", "porcelain:summon", "porcelain:seal", "porcelain:reset",
                 "porcelain:phase", "porcelain:mandate_arena", "porcelain:despawn"):
        continue
    if ident in ("porcelain:fight_active", "porcelain:return", "porcelain:victories"):
        continue
    check(ident in known_porcelain or ident in props_all, f"script uses unknown id {ident}")
for ident in set(re.findall(r'"(porcelain\.[a-z_.]+)"', js)):
    check(ident in sounds, f"script uses unknown sound {ident}")
for ident in set(re.findall(r'"(minecraft:[a-z0-9_]+)"', js)):
    check(ident in vanilla_ids or ident in ("minecraft:health", "minecraft:inventory", "minecraft:equippable", "minecraft:item", "minecraft:free"),
          f"script uses unknown vanilla id {ident}")
for eff in set(re.findall(r'addEffect\("([a-z_]+)"', js)):
    check(f"minecraft:{eff}" in vanilla_ids, f"script uses unknown effect {eff}")
# action ids in config.ts must match the animation controller
acts = dict((k.lower(), int(v)) for k, v in re.findall(r"^\s+([A-Z_]+): (\d+),", config.split("export const ACT")[1].split("} as const")[0], re.M))
sys.path.insert(0, HERE)
import assets_rp  # noqa: E402
check(acts == assets_rp.ACTIONS, f"ACT in config.ts {acts} != assets_rp.ACTIONS {assets_rp.ACTIONS}")
emp_props = bp_entities["porcelain:emperor"]["description"]["properties"]
check(emp_props["porcelain:action"]["range"][1] == max(acts.values()), "porcelain:action range does not cover every action")

if errors:
    print(f"VALIDATION FAILED: {len(errors)} problem(s) in {checks['count']} checks")
    for e in errors[:80]:
        print("  -", e)
    sys.exit(1)
print(f"validation OK: {checks['count']} checks passed")
