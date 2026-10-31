"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Cross-checks every file: manifests, geometry (hierarchy, UV bounds), every
Molang expression (parsed; queries and variables checked), animations ->
bones, animation controllers -> animations, render controllers -> geometry /
textures / materials / bones, client <-> server entities, entity components
(must exist in vanilla), events, properties used by Molang, particles
(texture, UV, variables, facing modes), items, recipes, loot tables, language
keys, textures, and every identifier the compiled scripts use (sounds,
particles, effects, entities, items, act names) plus the on-screen text rule
(no message longer than 34 visible characters, no titles).
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
sys.path.insert(0, HERE)
from mk import molang  # noqa: E402
import build  # noqa: E402

BP = os.path.join(ROOT, "build", "Legends_BP")
RP = os.path.join(ROOT, "build", "Legends_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))
VD = os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib")
VANILLA_ITEMS = set(re.findall(r'"(minecraft:[a-z0-9_]+)"', open(os.path.join(VD, "mojang-item.d.ts")).read()))
VANILLA_EFFECTS = set(re.findall(r'"minecraft:([a-z_]+)"', open(os.path.join(VD, "mojang-effect.d.ts")).read()))

errors: list = []
checks = {"n": 0}


def check(cond, msg):
    checks["n"] += 1
    if not cond:
        errors.append(msg)
    return cond


def rel(p):
    return os.path.relpath(p, ROOT)


def load_all(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        try:
            out[p] = json.load(open(p, encoding="utf-8"))
            check(True, "")
        except Exception as e:  # noqa: BLE001
            check(False, f"invalid JSON {rel(p)}: {e}")
    return out


bp = {k: v for k, v in load_all(BP).items() if isinstance(v, dict)}
rp = {k: v for k, v in load_all(RP).items() if isinstance(v, dict)}


def molang_ok(expr, where, assigned=None, queries_ok=True, allow_vars=None):
    """Parse an expression and check its references. Returns the variables it assigns."""
    if not isinstance(expr, str):
        return set()
    try:
        q, rd, wr = molang.refs(expr)
    except molang.MolangError as e:
        check(False, f"{where}: bad molang {expr!r}: {e}")
        return set()
    check(True, "")
    for name in q:
        check(name in molang.KNOWN_QUERIES, f"{where}: unknown query.{name}")
    if assigned is not None:
        for v in rd:
            check(v in assigned or v in wr or v in molang.BUILTIN_VARIABLES or (allow_vars and v in allow_vars),
                  f"{where}: variable {v} read but never assigned")
    return wr


# ---------------------------------------------------------------- manifests
bpm = bp[os.path.join(BP, "manifest.json")]
rpm = rp[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", u), f"bad uuid {u}")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
script_mod = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script_mod) == 1 and os.path.exists(os.path.join(BP, script_mod[0]["entry"])), "script entry missing")
for mod in ("server", "server-ui"):
    v = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", mod, "package.json")))["version"]
    check(deps.get(f"@minecraft/{mod}") == v, f"manifest @minecraft/{mod} {deps.get('@minecraft/' + mod)} != typings {v}")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack_icon missing in {rel(p)}")

# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rp.items():
    if "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            geos[g["description"]["identifier"]] = g
expected_geo = len(build.BOSSES) + len(build.CHOIR) + len(build.PROPS)
check(len(geos) == expected_geo, f"expected {expected_geo} geometries, found {len(geos)}")
for gid, g in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bone names")
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for b in g["bones"]:
        if b.get("parent"):
            check(b["parent"] in names, f"{gid}: bone {b['name']} has unknown parent {b['parent']}")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative cube size in {b['name']}")
            check(len(c["uv"]) > 0, f"{gid}: cube without faces in {b['name']}")
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
    cubes = sum(len(b.get("cubes", [])) for b in g["bones"])
    check(cubes <= 450, f"{gid}: {cubes} cubes is too heavy for mobile")

# ---------------------------------------------------------------- animations, controllers, render controllers
anims, acs, rcs = {}, {}, {}
for p, d in rp.items():
    if p.endswith(".animation.json"):
        anims.update(d["animations"])
    if "animation_controllers" in d:
        acs.update(d["animation_controllers"])
    if "render_controllers" in d:
        rcs.update(d["render_controllers"])

client = {}
for p, d in rp.items():
    ce = d.get("minecraft:client_entity")
    if ce:
        client[ce["description"]["identifier"]] = ce["description"]

bp_entities = {}
for p, d in bp.items():
    e = d.get("minecraft:entity")
    if e:
        bp_entities[e["description"]["identifier"]] = e

for ident, desc in client.items():
    where = f"client {ident}"
    pre = desc.get("scripts", {}).get("pre_animation", [])
    assigned = set()
    for stmt in pre:
        check(stmt.strip().endswith(";"), f"{where}: pre_animation statement must end with ';'")
        assigned |= molang_ok(stmt, where, assigned=assigned | molang.BUILTIN_VARIABLES)
    if "scale" in desc.get("scripts", {}):
        molang_ok(desc["scripts"]["scale"], where, assigned)
    gid = desc["geometry"]["default"]
    check(gid in geos, f"{where}: geometry {gid} not defined")
    bones = {b["name"] for b in geos.get(gid, {"bones": []})["bones"]}
    for key, tex in desc["textures"].items():
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"{where}: texture {tex}.png missing")
    for short, full in desc["animations"].items():
        if full.startswith("controller."):
            check(full in acs, f"{where}: controller {full} not defined")
            ctrl = acs.get(full, {})
            states = ctrl.get("states", {})
            check(ctrl.get("initial_state") in states, f"{where}: controller initial state missing")
            for sname, st in states.items():
                for a in st.get("animations", []):
                    an = a if isinstance(a, str) else list(a)[0]
                    check(an in desc["animations"], f"{where}: state {sname} plays unknown animation {an}")
                for tr in st.get("transitions", []):
                    (dest, cond), = tr.items()
                    check(dest in states, f"{where}: transition to unknown state {dest}")
                    molang_ok(cond, f"{where} controller", assigned)
            continue
        check(full in anims, f"{where}: animation {full} not defined")
        a = anims.get(full, {})
        for bone, chans in a.get("bones", {}).items():
            check(bone in bones, f"{where}: {full} animates missing bone {bone}")
            for ch, val in chans.items():
                check(ch in ("rotation", "position", "scale"), f"{full}: unknown channel {ch}")
                vals = []
                if isinstance(val, dict):
                    for t, kv in val.items():
                        float(t)
                        vals += kv.get("post", kv.get("pre", [])) if isinstance(kv, dict) else (kv if isinstance(kv, list) else [kv])
                else:
                    vals = val if isinstance(val, list) else [val]
                for x in vals:
                    molang_ok(x, f"{full}/{bone}", assigned)
        if a.get("loop") is not True and a.get("loop") != "hold_on_last_frame":
            check("animation_length" in a, f"{full}: one-shot animation without length")
    for entry in desc["scripts"].get("animate", []):
        k = entry if isinstance(entry, str) else list(entry)[0]
        check(k in desc["animations"], f"{where}: animate refers to unknown {k}")
        if isinstance(entry, dict):
            molang_ok(list(entry.values())[0], f"{where} animate weight", assigned)
    for rc_name in desc["render_controllers"]:
        check(rc_name in rcs, f"{where}: render controller {rc_name} missing")
        rc = rcs.get(rc_name, {})
        check(rc.get("geometry", "").split(".", 1)[-1] in desc["geometry"], f"{where}: rc geometry key")
        arrays = rc.get("arrays", {}).get("textures", {})
        for arr in arrays.values():
            for t in arr:
                check(t.split(".", 1)[-1] in desc["textures"], f"{where}: rc array texture {t} missing")
        for t in rc.get("textures", []):
            if t.startswith("Array."):
                name = t.split("[")[0]
                check(name in arrays, f"{where}: rc texture array {name} missing")
                molang_ok(t[t.index("[") + 1:-1], f"{where} rc index", assigned)
            else:
                check(t.split(".", 1)[-1] in desc["textures"], f"{where}: rc texture {t} missing")
        for m in rc.get("materials", []):
            for pat, mv in m.items():
                check(mv.split(".", 1)[-1] in desc["materials"], f"{where}: rc material {mv} missing")
        for pv in rc.get("part_visibility", []):
            for bone, expr in pv.items():
                check(bone == "*" or bone in bones, f"{where}: part_visibility on missing bone {bone}")
                molang_ok(expr if isinstance(expr, str) else "", f"{where} visibility", assigned)
        for ch, expr in rc.get("overlay_color", {}).items():
            molang_ok(expr, f"{where} overlay", assigned)
    # every query.property('x') must be declared (client_sync) on the server entity
    bpe = bp_entities.get(ident)
    check(bpe is not None, f"{where}: no behaviour entity")
    props = (bpe or {}).get("description", {}).get("properties", {})
    blob = json.dumps(desc) + json.dumps([anims.get(f, {}) for f in desc["animations"].values()]) + \
        json.dumps([rcs.get(r, {}) for r in desc["render_controllers"]])
    for prop in set(re.findall(r"query\.property\('([a-z_]+:[a-z_]+)'\)", blob)):
        check(prop in props and props[prop].get("client_sync"), f"{where}: property {prop} not client-synced on the server entity")

# ---------------------------------------------------------------- BP entities
allowed = set(REF["entity_components"])
for ident, e in bp_entities.items():
    groups = [e.get("components", {})] + list(e.get("component_groups", {}).values())
    for g in groups:
        for comp in g:
            check(comp in allowed, f"{ident}: component {comp} not found in vanilla")
    for ev_name, ev in e.get("events", {}).items():
        for k in ("add", "remove"):
            for gname in ev.get(k, {}).get("component_groups", []):
                check(gname in e.get("component_groups", {}), f"{ident}: event {ev_name} uses unknown group {gname}")
    t = e.get("components", {}).get("minecraft:timer")
    if t:
        check(t["time_down_event"]["event"] in e.get("events", {}), f"{ident}: timer event missing")
    check(ident in client, f"{ident}: no client entity")
    loot = e.get("components", {}).get("minecraft:loot")
    if loot:
        check(os.path.exists(os.path.join(BP, loot["table"])), f"{ident}: loot table missing")
    for pname, pd in e["description"].get("properties", {}).items():
        check(pd["type"] in ("int", "float", "bool", "enum"), f"{ident}: bad property type")
        if pd["type"] in ("int", "float"):
            check(pd["range"][0] <= pd["default"] <= pd["range"][1], f"{ident}: property default out of range")
    xp = e.get("components", {}).get("minecraft:experience_reward")
    if xp:
        molang_ok(xp.get("on_death", ""), f"{ident} xp")

# ---------------------------------------------------------------- particles
particles = {}
FACING = {"rotate_xyz", "rotate_y", "lookat_xyz", "lookat_y", "direction_x", "direction_y", "direction_z",
          "emitter_transform_xy", "emitter_transform_xz", "emitter_transform_yz"}
for p, d in rp.items():
    if "particle_effect" in d:
        desc = d["particle_effect"]["description"]
        particles[desc["identifier"]] = d
        tex = desc["basic_render_parameters"]["texture"]
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"particle texture {tex} missing")
        comps = d["particle_effect"]["components"]
        bb = comps.get("minecraft:particle_appearance_billboard", {})
        check(bb.get("facing_camera_mode") in FACING, f"{desc['identifier']}: bad facing mode")
        uv = bb.get("uv", {})
        im = Image.open(os.path.join(RP, tex + ".png"))
        check(uv.get("texture_width") == im.width and uv.get("texture_height") == im.height, f"{desc['identifier']}: uv texture size")
        check(uv["uv"][0] + uv["uv_size"][0] <= im.width and uv["uv"][1] + uv["uv_size"][1] <= im.height, f"{desc['identifier']}: uv out of range")
        for expr in re.findall(r'"((?:[^"\\]|\\.)*(?:variable|math)\.[^"]*)"', json.dumps(comps)):
            molang_ok(expr, desc["identifier"], assigned=set(), allow_vars=build.PARTICLE_VARS)

# ---------------------------------------------------------------- items, recipes, loot, lang
item_tex = rp[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
for k, v in item_tex.items():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {v['textures']} missing")
items = set()
ITEM_OK = set(REF["item_components"]) | {"minecraft:glint", "minecraft:max_stack_size", "minecraft:display_name", "minecraft:icon", "minecraft:tags"}
for p, d in bp.items():
    it = d.get("minecraft:item")
    if it:
        ident = it["description"]["identifier"]
        items.add(ident)
        for comp in it["components"]:
            check(comp in ITEM_OK, f"{ident}: unknown item component {comp}")
        check(it["components"]["minecraft:icon"]["textures"]["default"] in item_tex, f"{ident}: icon missing")
lang = dict(l.rstrip("\n").split("=", 1) for l in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") if "=" in l)
for ident in items:
    check(f"item.{ident}.name" in lang, f"lang for {ident} missing")
for ident in bp_entities:
    check(f"entity.{ident}.name" in lang, f"lang for {ident} missing")
for p, d in bp.items():
    for kind in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless"):
        r = d.get(kind)
        if not r:
            continue
        ings = [v["item"] for v in r.get("key", {}).values()] + [v["item"] for v in r.get("ingredients", [])]
        for i in ings:
            check(i in VANILLA_ITEMS or i in items, f"recipe {r['description']['identifier']}: unknown item {i}")
        check(r["result"]["item"] in items, "recipe result unknown")
        if kind == "minecraft:recipe_shaped":
            keys = set("".join(r["pattern"])) - {" "}
            check(keys == set(r["key"]), f"recipe {r['description']['identifier']}: pattern/key mismatch")
for p, d in bp.items():
    if "pools" in d:
        for pool in d["pools"]:
            for en in pool["entries"]:
                check(en["name"] in VANILLA_ITEMS or en["name"] in items, f"loot {rel(p)}: unknown item {en['name']}")

# ---------------------------------------------------------------- scripts
js = {}
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    src = open(p, encoding="utf-8").read()
    js[p] = src
    for imp in re.findall(r'from "(\.[^"]+)"', src):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{rel(p)}: import {imp} not found")
alljs = "\n".join(js.values())
for snd in set(re.findall(r'(?:sound\(\s*[\w.]+,\s*|playSound\()"([a-z0-9_.]+)"', alljs)) | \
        set(re.findall(r'sound\([^)]*?\?\s*"([a-z0-9_.]+)"\s*:\s*"([a-z0-9_.]+)"', alljs) and []):
    check(snd in REF["sounds"], f"sound {snd} not in vanilla sound definitions")
for a, b in re.findall(r'\?\s*"([a-z]+\.[a-z0-9_.]+)"\s*:\s*"([a-z]+\.[a-z0-9_.]+)"', alljs):
    for snd in (a, b):
        check(snd in REF["sounds"], f"sound {snd} not in vanilla sound definitions")
known_ids = set(particles) | set(bp_entities) | set(items)
for e in bp_entities.values():
    known_ids |= set(e["description"].get("properties", {})) | set(e.get("events", {}))
DYN_PROPS = {"legends:home", "legends:owner", "legends:codex_given"}
COMMANDS = {"legends:codex", "legends:summon", "legends:phase", "legends:clear", "legends:sigils", "legends:boss"}
known_ids |= DYN_PROPS | COMMANDS
for pid in set(re.findall(r'"(legends:[a-z_]+)"', alljs)):
    check(pid in known_ids, f"script references unknown id {pid}")
for kind in set(re.findall(r'spawn\(dim, `legends:\$\{kind\}`', alljs)):
    pass
for kind in set(re.findall(r'deco\([^,]+,\s*"([a-z]+)"', alljs)):
    check(f"legends:{kind}" in particles, f"deco particle legends:{kind} missing")
for prop in set(re.findall(r'spawnProp\([^,]+,\s*"([a-z_]+)"', alljs)):
    check(f"legends:{prop}" in bp_entities, f"prop legends:{prop} not defined")
effects = set(re.findall(r'effect\([^,]+,\s*"([a-z_]+)"', alljs)) | set(re.findall(r'\["([a-z_]+)",\s*\d+,\s*\d+\]', alljs))
effects |= set(re.findall(r'POISON = .*?"([a-z_]+)"', alljs))
for eff in effects:
    check(eff in VANILLA_EFFECTS, f"effect {eff} is not a Minecraft effect")
for eff in re.findall(r'mob_effects":\s*\[([^\]]*)\]', json.dumps(bp_entities)):
    for e2 in re.findall(r'\\?"([a-z_]+)\\?"', eff):
        check(e2 in VANILLA_EFFECTS, f"mob_effect_immunity: {e2} not an effect")
for ident in set(re.findall(r'new ItemStack\("([a-z_]+:[a-z_]+)"', alljs)):
    check(ident in items or ident in VANILLA_ITEMS, f"ItemStack {ident} unknown")
for ev in set(re.findall(r'triggerEvent\("([a-z_]+:[a-z_]+)"\)', alljs)) | set(re.findall(r'this\.form\("([a-z_]+:[a-z_]+)"\)', alljs)):
    check(any(ev in e.get("events", {}) for e in bp_entities.values()), f"event {ev} not defined on any entity")
for prop in set(re.findall(r'(?:setProperty|getProperty)\("([a-z_]+:[a-z_]+)"', alljs)) | {f"legends:{n}" for n in re.findall(r'this\.prop\("([a-z]+)"', alljs)}:
    check(any(prop in e["description"].get("properties", {}) for e in bp_entities.values()), f"property {prop} not declared")

# act names used by each boss script must exist in that creature's act table
gen = open(os.path.join(ROOT, "src", "generated", "data.ts")).read()
acts = {m.group(1).lower(): set(re.findall(r"(\w+): \{ id:", m.group(2))) for m in re.finditer(r"export const (\w+)_ACTS = \{(.*?)\} as const;", gen)}
for name, keys in (("taotie", ["taotie"]), ("nidhogg", ["nidhogg"]), ("hanuman", ["hanuman"]), ("alicorn", ["alicorn"]),
                   ("tenko", ["tenko"]), ("logos", ["logos", "seraph", "cherub", "ophan"])):
    p = os.path.join(BP, "scripts", "bosses", f"{name}.js")
    src = js.get(p, "")
    known = set().union(*[acts.get(k, set()) for k in keys])
    for a in set(re.findall(r'\.(?:act|play)\("([a-z_0-9]+)"\)', src)):
        check(a in known, f"{name}.js: act '{a}' does not exist")
for a in set(re.findall(r'this\.act\("([a-z_0-9]+)"\)', js.get(os.path.join(BP, "scripts", "bosses", "boss.js"), ""))):
    for k in ("taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos"):
        check(a in acts.get(k, set()), f"boss.js uses act '{a}' missing on {k}")
# the screen-clarity rule: only action-bar notices, short
check("setTitle(" not in alljs, "scripts must not use setTitle (screen clarity)")
for txt in re.findall(r'(?:say|notify)\([^`"]*?[`"]([^`"]+)[`"]', alljs):
    vis = re.sub(r"§.", "", re.sub(r"\$\{[^}]+\}", "XXXXXXXXXXXXXXXXXXXX", txt))
    check(len(vis) <= 34 or "${" in txt, f"notice too long ({len(vis)}): {txt!r}")
for cls in ("phaseNames", "ultName", "title"):
    for m in re.finditer(cls + r' = (\[[^\]]*\]|"[^"]*")', alljs):
        for s in re.findall(r'"([^"]*)"', m.group(1)):
            check(len(s) + 4 <= 34, f"{cls} text too long for the action bar: {s!r}")

# ---------------------------------------------------------------- textures
for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(p)
    check(im.mode == "RGBA", f"{rel(p)} is not RGBA")
    w, h = im.size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{rel(p)} size {im.size} not power of two")
    check(w <= 1024 and h <= 1024, f"{rel(p)} too large for mobile")

print(f"{checks['n']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
