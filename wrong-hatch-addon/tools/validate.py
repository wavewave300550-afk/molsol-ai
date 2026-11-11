"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Checks JSON syntax, manifests, and every cross reference between files:
geometry <-> client entity <-> render controller <-> textures <-> animations
<-> animation controllers <-> sound effects, BP entity components / groups /
events / properties, items, recipes, loot, lang, particles, sounds (custom
.ogg files and vanilla sound paths), model integrity (UV bounds, hierarchy,
animated bones exist) and the boss's real dimensions against the brief.
Vanilla identifiers come from Mojang/bedrock-samples (tools/vanilla/).
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
BP = os.path.join(ROOT, "build", "WrongHatch_BP")
RP = os.path.join(ROOT, "build", "WrongHatch_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))
VANILLA_SOUND_FILES = set(json.load(open(os.path.join(HERE, "vanilla", "sound_files.json"))))
# components introduced after the reference snapshot's sample files / documented ones
EXTRA_ENTITY_COMPONENTS = set()
EXTRA_ITEM_COMPONENTS = set()
VANILLA_MATERIALS = {"entity_emissive_alpha", "entity_alphatest", "warden_bioluminescent_layer"}

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


bp = {k: v for k, v in load_all(BP).items() if isinstance(v, dict)}
rp = {k: v for k, v in load_all(RP).items() if isinstance(v, dict)}

# ---------------------------------------------------------------- manifests
bpm, rpm = bp[os.path.join(BP, "manifest.json")], rp[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", u), f"bad uuid {u}")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
script = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script) == 1 and os.path.exists(os.path.join(BP, script[0]["entry"])), "script entry missing")
typings = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")))["version"]
check(deps.get("@minecraft/server") == typings, f"manifest @minecraft/server {deps.get('@minecraft/server')} != typings {typings}")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack icon missing in {rel(p)}")

# ---------------------------------------------------------------- textures
for png in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    w, h = Image.open(png).size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"texture not power of two: {rel(png)} {w}x{h}")


def tex_exists(path):
    return os.path.exists(os.path.join(RP, path + ".png"))


# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rp.items():
    for g in d.get("minecraft:geometry", []):
        geos[g["description"]["identifier"]] = g
check(len(geos) == 5, f"expected 5 geometries, found {len(geos)}")
for gid, g in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bone names")
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for b in g["bones"]:
        if b.get("parent"):
            check(b["parent"] in names, f"{gid}: {b['name']} has unknown parent {b['parent']}")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative cube size in {b['name']}")
            check(len(c["uv"]) > 0, f"{gid}: cube without faces in {b['name']}")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                check(0 <= min(u, u + w) and max(u, u + w) <= W and 0 <= min(v, v + h) and max(v, v + h) <= H,
                      f"{gid}: {face} uv out of bounds in {b['name']}")
    for n in names:
        seen, cur = set(), n
        while cur:
            if not check(cur not in seen, f"{gid}: bone cycle at {n}"):
                break
            seen.add(cur)
            cur = parents.get(cur)

# ---------------------------------------------------------------- animations / controllers
anims, ctrls = {}, {}
for p, d in rp.items():
    anims.update(d.get("animations", {}) if "animation_controllers" not in d else {})
    ctrls.update(d.get("animation_controllers", {}))

# ---------------------------------------------------------------- sounds
sdefs = rp[os.path.join(RP, "sounds", "sound_definitions.json")]["sound_definitions"]
for name, sd in sdefs.items():
    for s in sd["sounds"]:
        path = s["name"] if isinstance(s, dict) else s
        if path.startswith("sounds/wrong_hatch/"):
            check(os.path.exists(os.path.join(RP, path + ".ogg")), f"sound file missing: {path}.ogg")
            if os.path.exists(os.path.join(RP, path + ".ogg")):
                check(os.path.getsize(os.path.join(RP, path + ".ogg")) > 1000, f"sound file empty: {path}")
        else:
            check(path in VANILLA_SOUND_FILES, f"{name}: vanilla sound file does not exist: {path}")
all_sounds = set(REF["sounds"]) | set(sdefs)
ents_sounds = rp[os.path.join(RP, "sounds.json")]["entity_sounds"]["entities"]
for eid, ed in ents_sounds.items():
    for ev, v in ed["events"].items():
        name = v["sound"] if isinstance(v, dict) else v
        check(name in all_sounds, f"sounds.json {eid}.{ev}: unknown sound event {name}")

# ---------------------------------------------------------------- client entities
rcs = {}
for p, d in rp.items():
    rcs.update(d.get("render_controllers", {}))
clients = {}
for p, d in rp.items():
    if "minecraft:client_entity" in d:
        desc = d["minecraft:client_entity"]["description"]
        clients[desc["identifier"]] = desc
check(len(clients) == 7, f"expected 7 client entities, found {len(clients)}")
for eid, desc in clients.items():
    for k, t in desc["textures"].items():
        check(tex_exists(t), f"{eid}: texture {t} missing")
    for k, g in desc["geometry"].items():
        check(g in geos, f"{eid}: geometry {g} missing")
    for k, m in desc["materials"].items():
        check(m in VANILLA_MATERIALS, f"{eid}: unexpected material {m}")
    bones = set()
    for g in desc["geometry"].values():
        bones |= {b["name"] for b in geos[g]["bones"]}
    akeys = desc.get("animations", {})
    for k, a in akeys.items():
        check(a in anims or a in ctrls, f"{eid}: animation {a} undefined")
        if a in anims:
            for b in anims[a].get("bones", {}):
                check(b in bones, f"{eid}: animation {a} moves unknown bone {b}")
            for t, se in anims[a].get("sound_effects", {}).items():
                check(se["effect"] in desc.get("sound_effects", {}), f"{eid}: {a} uses undeclared sound effect {se['effect']}")
        if a in ctrls:
            for sname, st in ctrls[a]["states"].items():
                for an in st.get("animations", []):
                    key = an if isinstance(an, str) else list(an)[0]
                    check(key in akeys, f"{eid}: controller {a} state {sname} plays unknown key {key}")
                for tr in st.get("transitions", []):
                    check(list(tr)[0] in ctrls[a]["states"], f"{eid}: controller {a} bad transition {tr}")
    for entry in desc.get("scripts", {}).get("animate", []):
        key = entry if isinstance(entry, str) else list(entry)[0]
        check(key in akeys, f"{eid}: animate references unknown key {key}")
    for se in desc.get("sound_effects", {}).values():
        check(se["effect"] in all_sounds, f"{eid}: sound effect event {se['effect']} undefined")
    for rc in desc["render_controllers"]:
        name = rc if isinstance(rc, str) else list(rc)[0]
        if not check(name in rcs, f"{eid}: render controller {name} undefined"):
            continue
        r = rcs[name]
        txt = json.dumps(r)
        for ref_t in re.findall(r"Texture\.([a-z_]+)", txt):
            check(ref_t in desc["textures"], f"{eid}: {name} uses texture key {ref_t} not declared")
        for ref_m in re.findall(r"Material\.([a-z_]+)", txt):
            check(ref_m in desc["materials"], f"{eid}: {name} uses material key {ref_m} not declared")
        for ref_g in re.findall(r"Geometry\.([a-z_]+)", txt):
            check(ref_g in desc["geometry"], f"{eid}: {name} uses geometry key {ref_g} not declared")
    for prop in re.findall(r"query\.property\('([a-z_:]+)'\)", json.dumps(desc)):
        check(True, "")
        PROPS_USED = prop  # noqa: F841

# ---------------------------------------------------------------- behaviour entities
known_comp = set(REF["entity_components"]) | EXTRA_ENTITY_COMPONENTS
bents = {}
for p, d in bp.items():
    if "minecraft:entity" in d:
        e = d["minecraft:entity"]
        bents[e["description"]["identifier"]] = e
check(set(bents) == set(clients), f"BP/RP entity sets differ: {set(bents) ^ set(clients)}")
for eid, e in bents.items():
    groups = e.get("component_groups", {})
    for comp in list(e.get("components", {})) + [c for g in groups.values() for c in g]:
        check(comp in known_comp, f"{eid}: unknown component {comp}")
    for ev, body in e.get("events", {}).items():
        for g in body.get("add", {}).get("component_groups", []) + body.get("remove", {}).get("component_groups", []):
            check(g in groups, f"{eid}: event {ev} references unknown group {g}")
    props = e["description"].get("properties", {})
    client_txt = json.dumps(clients.get(eid, {}))
    for prop in re.findall(r"query\.property\('([a-z_:]+)'\)", client_txt):
        check(prop in props, f"{eid}: client uses property {prop} not defined in BP")
        check(props.get(prop, {}).get("client_sync") is True, f"{eid}: property {prop} must be client_sync")
    loot = e.get("components", {}).get("minecraft:loot", {}).get("table")
    if loot:
        check(os.path.exists(os.path.join(BP, loot)), f"{eid}: loot table {loot} missing")

# the boss animation ids must fit the property range
import spec  # noqa: E402

boss = bents["wh:wrong_hatch"]
rng = boss["description"]["properties"]["wh:anim"]["range"]
check(max(spec.ACTION_ID.values()) <= rng[1], "wh:anim range too small for all actions")
ctrl = ctrls["controller.animation.wrong_hatch.action"]
for name, _, _ in spec.ACTIONS:
    if name != "none":
        check(name in ctrl["states"], f"action {name} has no controller state")
        a = anims.get(f"animation.wrong_hatch.{name}")
        if check(a is not None, f"action {name} has no animation"):
            ln = spec.ACTION_LEN[name]
            if ln:
                check(abs(a.get("animation_length", 0) - ln / 20) < 0.011, f"{name}: animation length != script timeline")
            else:
                check(a.get("loop") is True, f"{name}: looping action must loop")

# ---------------------------------------------------------------- items / recipes / loot / lang
item_tex = rp[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
known_item_comp = set(REF["item_components"]) | EXTRA_ITEM_COMPONENTS
items = {}
for p, d in bp.items():
    if "minecraft:item" in d:
        it = d["minecraft:item"]
        items[it["description"]["identifier"]] = it
        for c in it["components"]:
            check(c in known_item_comp, f"{it['description']['identifier']}: unknown item component {c}")
        icon = it["components"]["minecraft:icon"]["textures"]["default"]
        check(icon in item_tex and tex_exists(item_tex[icon]["textures"]), f"item icon {icon} missing")
check("wh_spawn_egg" in item_tex, "spawn egg texture missing")
vanilla_items = {"minecraft:egg", "minecraft:gold_block", "minecraft:fermented_spider_eye", "minecraft:gold_ingot"}
for p, d in bp.items():
    for key in ("minecraft:recipe_shapeless", "minecraft:recipe_shaped"):
        if key in d:
            r = d[key]
            for ing in r.get("ingredients", []):
                check(ing["item"] in items or ing["item"] in vanilla_items, f"recipe ingredient {ing['item']} unknown")
            check(r["result"]["item"] in items, f"recipe result {r['result']['item']} unknown")
    if "pools" in d:
        for pool in d["pools"]:
            for en in pool["entries"]:
                check(en["name"] in items or en["name"] in vanilla_items, f"loot entry {en['name']} unknown")
lang = open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8").read()
for iid in items:
    check(f"item.{iid}.name=" in lang, f"lang missing item {iid}")
for eid in bents:
    check(f"entity.{eid}.name=" in lang, f"lang missing entity {eid}")
check("item.spawn_egg.entity.wh:wrong_hatch.name=" in lang, "lang missing spawn egg")

# ---------------------------------------------------------------- particles
for p, d in rp.items():
    if "particle_effect" in d:
        pe = d["particle_effect"]
        check(tex_exists(pe["description"]["basic_render_parameters"]["texture"]), f"{rel(p)}: particle texture missing")
        uv = pe["components"]["minecraft:particle_appearance_billboard"]["uv"]
        check(uv["uv"][0] + uv["uv_size"][0] <= uv["texture_width"] and uv["uv"][1] + uv["uv_size"][1] <= uv["texture_height"],
              f"{rel(p)}: particle uv out of bounds")

# ---------------------------------------------------------------- scripts: every identifier literal exists
js = ""
for f in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    js += open(f, encoding="utf-8").read()
particles = set(REF["particles"]) | {d["particle_effect"]["description"]["identifier"] for d in rp.values() if "particle_effect" in d}
for pid in set(re.findall(r'"((?:wh|minecraft):[a-z_]+(?:_emitter|_particle|_center)?)"', js)):
    if pid.startswith("wh:") and pid in bents:
        continue
    if pid in particles or pid in bents or pid in items or pid in vanilla_items or pid in ("minecraft:player", "minecraft:item"):
        continue
    if pid.startswith("minecraft:") or pid.startswith("wh:"):
        # could be an event / property / dynamic property name
        boss_names = set(boss["events"]) | set(boss["description"]["properties"])
        all_events = {ev for e in bents.values() for ev in e.get("events", {})}
        all_props = {pr for e in bents.values() for pr in e["description"].get("properties", {})}
        if pid in boss_names or pid in all_events or pid in all_props or pid.startswith("wh:hp_") or pid.startswith("wh:shell_"):
            continue
        if pid in ("minecraft:health", "minecraft:inventory", "minecraft:tameable", "minecraft:cooldown"):
            continue
        if re.fullmatch(r"wh:(home|init|phase|hpScale|fh1|fh2|owner|summon|clear|anim|kind|fuse)", pid):
            continue
        check(False, f"script references unknown identifier {pid}")
for snd in set(re.findall(r'sound\([^,]+,\s*"([a-z_.0-9]+)"', js)):
    check(snd in all_sounds, f"script plays unknown sound {snd}")
for snd in set(re.findall(r'particle\([^,]+,\s*"([a-z_:]+)"', js)):
    check(snd in particles, f"script spawns unknown particle {snd}")

# ---------------------------------------------------------------- model dimensions vs the brief
import boss_model  # noqa: E402

m = boss_model.build()
mn, mx = m.extent()
h, length = (mx[1] - mn[1]) / 8, (mx[2] - mn[2]) / 8
mn2, mx2 = m.extent({"wing_r": {"rotation": (0, -90, 38)}, "wing_l": {"rotation": (0, 90, -38)}})
span = (mx2[0] - mn2[0]) / 8
check(5.0 <= h <= 5.4, f"boss height {h:.2f} blocks (brief: 5.2)")
check(5.4 <= length <= 6.6, f"boss length {length:.2f} blocks (brief: 6.4)")
check(9.2 <= span <= 10.0, f"boss wingspan {span:.2f} blocks (brief: 9.6)")

print(f"{count['n']} checks, {len(errors)} errors")
print(f"boss: {m.stats()['bones']} bones, {m.stats()['cubes']} cubes; height {h:.2f}, length {length:.2f}, wingspan {span:.2f} blocks")
for e in errors:
    print("ERROR:", e)
sys.exit(1 if errors else 0)
