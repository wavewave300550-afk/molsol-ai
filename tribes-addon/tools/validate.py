"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Checks JSON syntax, manifests, cross references between every file
(geometry / textures / animations / render controllers / items / lang),
model integrity (UV bounds, bone hierarchy, animated bones), and that every
identifier the scripts use (particles, sounds, effects, entities, items)
exists in the packs or in vanilla Minecraft (reference index extracted from
Mojang/bedrock-samples, tools/vanilla/reference.json).
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "Tribes_BP")
RP = os.path.join(ROOT, "build", "Tribes_RP")
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


# languages.json is a list; every other pack file is an object
bp_json = {k: v for k, v in load_all(BP).items() if isinstance(v, dict)}
rp_json = {k: v for k, v in load_all(RP).items() if isinstance(v, dict)}

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
pkg_server = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")))["version"]
pkg_ui = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", "server-ui", "package.json")))["version"]
check(deps.get("@minecraft/server") == pkg_server, f"manifest @minecraft/server {deps.get('@minecraft/server')} != typings {pkg_server}")
check(deps.get("@minecraft/server-ui") == pkg_ui, f"manifest @minecraft/server-ui {deps.get('@minecraft/server-ui')} != typings {pkg_ui}")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack_icon missing in {rel(p)}")

# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rp_json.items():
    if isinstance(d, dict) and "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            desc = g["description"]
            geos[desc["identifier"]] = (g, p)
check(len(geos) == 9, f"expected 9 geometries, found {len(geos)}")


def geo_bones(gid):
    g, _ = geos[gid]
    return {b["name"] for b in g["bones"]}


for gid, (g, p) in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bone names")
    for b in g["bones"]:
        if "parent" in b:
            check(b["parent"] in names, f"{gid}: bone {b['name']} has unknown parent {b['parent']}")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative cube size")
            check(len(c["uv"]) > 0, f"{gid}: cube without faces in {b['name']}")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                u0, u1 = sorted((u, u + w))
                v0, v1 = sorted((v, v + h))
                check(0 <= u0 and u1 <= W and 0 <= v0 and v1 <= H, f"{gid}: {face} uv out of bounds in {b['name']}")
    # cycle check
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for n in names:
        seen, cur = set(), n
        while cur:
            check(cur not in seen, f"{gid}: bone cycle at {n}")
            if cur in seen:
                break
            seen.add(cur)
            cur = parents.get(cur)

# ---------------------------------------------------------------- animations & render controllers
anims = {}
for p, d in rp_json.items():
    if isinstance(d, dict) and "animations" in d and isinstance(d["animations"], dict) and p.endswith(".animation.json"):
        anims.update(d["animations"])
rcs = {}
for p, d in rp_json.items():
    if isinstance(d, dict) and "render_controllers" in d and isinstance(d["render_controllers"], dict):
        rcs.update(d["render_controllers"])


def molang_ok(expr):
    if not isinstance(expr, str):
        return True
    depth = 0
    for ch in expr:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return False
    return depth == 0 and "  " not in expr.strip()


for name, a in anims.items():
    for bone, chans in a.get("bones", {}).items():
        for ch, vals in chans.items():
            check(ch in ("rotation", "position", "scale"), f"{name}: unknown channel {ch}")
            for val in vals if isinstance(vals, list) else [vals]:
                check(molang_ok(val), f"{name}/{bone}: unbalanced molang {val}")

VANILLA_RC = {"controller.render.player.first_person", "controller.render.player.third_person",
              "controller.render.player.first_person_spectator", "controller.render.player.third_person_spectator",
              "controller.render.player.map"}

for p, d in rp_json.items():
    ce = d.get("minecraft:client_entity") if isinstance(d, dict) else None
    if not ce:
        continue
    desc = ce["description"]
    ident = desc["identifier"]
    is_player = ident == "minecraft:player"
    for key, gid in desc.get("geometry", {}).items():
        if gid.startswith("geometry.tribes"):
            check(gid in geos, f"{ident}: geometry {gid} not defined")
    for key, tex in desc.get("textures", {}).items():
        if "tribes" in tex:
            check(os.path.exists(os.path.join(RP, tex + ".png")), f"{ident}: texture {tex}.png missing")
    used_bones = set()
    for key, aname in desc.get("animations", {}).items():
        if "tribes" in aname:
            check(aname in anims, f"{ident}: animation {aname} not defined")
            used_bones |= set(anims.get(aname, {}).get("bones", {}).keys())
    animate = desc.get("scripts", {}).get("animate", [])
    for entry in animate:
        k = entry if isinstance(entry, str) else list(entry.keys())[0]
        check(k in desc.get("animations", {}), f"{ident}: animate refers to unknown short name {k}")
        if isinstance(entry, dict):
            check(molang_ok(list(entry.values())[0]), f"{ident}: bad animate condition")
    all_geo_bones = set()
    for gid in desc.get("geometry", {}).values():
        if gid in geos:
            all_geo_bones |= geo_bones(gid)
    for b in used_bones:
        check(b in all_geo_bones, f"{ident}: animated bone '{b}' missing from its geometries")
    for entry in desc.get("render_controllers", []):
        rc_name = entry if isinstance(entry, str) else list(entry.keys())[0]
        if rc_name in VANILLA_RC:
            continue
        check(rc_name in rcs, f"{ident}: render controller {rc_name} not defined")
        rc = rcs.get(rc_name, {})
        g = rc.get("geometry", "").split(".", 1)[-1]
        check(g in desc.get("geometry", {}), f"{ident}: rc {rc_name} geometry key {g} missing")
        for t in rc.get("textures", []):
            check(t.split(".", 1)[-1] in desc.get("textures", {}), f"{ident}: rc {rc_name} texture key {t} missing")
        for m in rc.get("materials", []):
            for mv in m.values():
                check(mv.split(".", 1)[-1] in desc.get("materials", {}), f"{ident}: rc {rc_name} material {mv} missing")
    if is_player:
        van = json.load(open(os.path.join(HERE, "vanilla", "player.entity.json")))["minecraft:client_entity"]["description"]
        for section in ("materials", "textures", "geometry", "animations"):
            for k, val in van[section].items():
                check(desc[section].get(k) == val, f"player.entity.json lost vanilla {section}.{k}")
        check(desc["render_controllers"][:len(van["render_controllers"])] == van["render_controllers"],
              "player.entity.json vanilla render controllers changed")
        check(desc["scripts"]["animate"][:len(van["scripts"]["animate"])] == van["scripts"]["animate"],
              "player.entity.json vanilla animate list changed")

# overlay bones must mirror the vanilla humanoid skeleton so the player's animations drive them
HUMANOID = {"root": None, "waist": "root", "body": "waist", "head": "body", "rightArm": "body",
            "leftArm": "body", "rightLeg": "root", "leftLeg": "root"}
for gid, (g, _) in geos.items():
    if ".overlay." in gid:
        parents = {b["name"]: b.get("parent") for b in g["bones"]}
        for bn, par in HUMANOID.items():
            check(parents.get(bn, "MISSING") == par, f"{gid}: humanoid bone {bn} must have parent {par}")

# ---------------------------------------------------------------- particles
particle_ids = set()
for p, d in rp_json.items():
    if isinstance(d, dict) and "particle_effect" in d:
        desc = d["particle_effect"]["description"]
        particle_ids.add(desc["identifier"])
        tex = desc["basic_render_parameters"]["texture"]
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"particle texture {tex} missing")

# ---------------------------------------------------------------- BP entities & items
bp_entities = set()
allowed_entity = set(REF["entity_components"])
for p, d in bp_json.items():
    e = d.get("minecraft:entity")
    if not e:
        continue
    ident = e["description"]["identifier"]
    bp_entities.add(ident)
    groups = [e.get("components", {})] + list(e.get("component_groups", {}).values())
    for g in groups:
        for comp in g:
            check(comp in allowed_entity, f"{ident}: component {comp} not found in any vanilla entity")
    for ev_name, ev in e.get("events", {}).items():
        for gname in ev.get("add", {}).get("component_groups", []):
            check(gname in e.get("component_groups", {}), f"{ident}: event {ev_name} adds unknown group {gname}")
    timer = e.get("components", {}).get("minecraft:timer")
    if timer:
        check(timer["time_down_event"]["event"] in e.get("events", {}), f"{ident}: timer event missing")
    tame = e.get("components", {}).get("minecraft:tameable")
    if tame:
        check(tame["tame_event"]["event"] in e.get("events", {}), f"{ident}: tame event missing")
    if ident != "minecraft:player":
        rp_ok = any(isinstance(d2, dict) and d2.get("minecraft:client_entity", {}).get("description", {}).get("identifier") == ident for d2 in rp_json.values())
        check(rp_ok, f"{ident}: no client entity")
    else:
        props = e["description"].get("properties", {})
        check("tribes:race" in props and props["tribes:race"].get("client_sync") is True, "player race property missing")
        van = json.load(open(os.path.join(HERE, "vanilla", "player.json")))["minecraft:entity"]
        check(van["components"] == e["components"] and van.get("component_groups") == e.get("component_groups")
              and van.get("events") == e.get("events"), "player.json diverges from vanilla beyond the property")

item_textures = rp_json[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
for k, v in item_textures.items():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {v['textures']} missing")
ITEM_EXTRA = {"minecraft:glint", "minecraft:hand_equipped", "minecraft:max_stack_size"}
bp_items = set()
for p, d in bp_json.items():
    it = d.get("minecraft:item")
    if not it:
        continue
    ident = it["description"]["identifier"]
    bp_items.add(ident)
    comps = it["components"]
    for comp in comps:
        check(comp in set(REF["item_components"]) | ITEM_EXTRA, f"{ident}: unknown item component {comp}")
    check(comps["minecraft:icon"]["textures"]["default"] in item_textures, f"{ident}: icon not in item_texture.json")

lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line:
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
for ident in bp_items:
    check(f"item.{ident}.name" in lang, f"lang key for {ident} missing")
for ident in bp_entities - {"minecraft:player"}:
    check(f"entity.{ident}.name" in lang, f"lang key for {ident} missing")

for p, d in bp_json.items():
    r = d.get("minecraft:recipe_shapeless")
    if r:
        check(r["result"]["item"] in bp_items, "recipe result unknown")

# ---------------------------------------------------------------- scripts
js = ""
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    js += open(p, encoding="utf-8").read() + "\n"
    for imp in re.findall(r'from "(\.[^"]+)"', open(p, encoding="utf-8").read()):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{rel(p)}: import {imp} not found")

for c in set(re.findall(r'(?:mote|burst|flare)\(\s*[\w.]+,\s*"(\w+)"', js)) | set(re.findall(r'(?:beam|ring|sphere|column|spiral)\(\s*[\w.]+,\s*"(\w+)"', js)):
    for kind in ("mote", "burst", "flare"):
        check(f"tribes:{c}_{kind}" in particle_ids, f"particle tribes:{c}_{kind} missing")
for pid in set(re.findall(r'"((?:tribes|minecraft):[a-z_]+_(?:mote|burst|flare|emitter))"', js)):
    check(pid in particle_ids or pid in REF["particles"], f"particle {pid} not defined")
for snd in set(re.findall(r'(?:sound\(\s*[\w.]+,\s*|playSound\()"([a-z0-9_.]+)"', js)):
    check(snd in REF["sounds"], f"sound {snd} not found in vanilla sound_definitions")
effect_ids = set(re.findall(r'"minecraft:([a-z_]+)"', open(os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts")).read()))
used_effects = set(re.findall(r'(?:addEffect|removeEffect|getEffect)\(\s*"([a-z_]+)"', js))
used_effects |= set(re.findall(r'effect: "([a-z_]+)"', js))
neg = re.search(r"NEGATIVE_EFFECTS = \[([^\]]+)\]", js)
if neg:
    used_effects |= set(re.findall(r'"([a-z_]+)"', neg.group(1)))
for eff in used_effects:
    check(eff in effect_ids, f"effect {eff} is not a Minecraft effect")
for ent in set(re.findall(r'spawnEntity\(\s*"([a-z_]+:[a-z_]+)"', js)) | {f"tribes:{k}" for k in re.findall(r'spawnSummon\([^,]+,\s*"([a-z_]+)"', js)}:
    check(ent in bp_entities or ent in REF["entities"], f"spawned entity {ent} not defined")
script_items = set(re.findall(r'relic: "([a-z_]+:[a-z_]+)"', js)) | set(re.findall(r'CODEX_ITEM = "([a-z_]+:[a-z_]+)"', js))
check(len(script_items) == 5, f"expected 5 script items, found {sorted(script_items)}")
for item in script_items:
    check(item in bp_items, f"item {item} referenced by scripts but not defined")
check("tribes:race" in js, "scripts never touch tribes:race")

# ---------------------------------------------------------------- textures
for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(p)
    check(im.mode == "RGBA", f"{rel(p)} is not RGBA")
    w, h = im.size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{rel(p)} size {im.size} is not a power of two")

print(f"{checks['count']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
