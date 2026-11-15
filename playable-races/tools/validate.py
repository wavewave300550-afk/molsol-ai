"""Static validation of the generated packs (cross-references Creator Tools does not check).

    python3 tools/validate.py

Checks manifests, every attachable/geometry/texture/animation/render-controller link,
bone names used by animations, UV bounds, binding pivots against the vanilla player
skeleton, the player render-controller override against vanilla, particles, items,
lang keys, and every identifier string the compiled scripts use (particles, sounds,
effects, items, entities, animations, fogs).
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
sys.path.insert(0, os.path.join(HERE, "kit"))
import ljson  # noqa: E402

BP = os.path.join(ROOT, "packs", "PlayableRaces_BP")
RP = os.path.join(ROOT, "packs", "PlayableRaces_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))
VANILLA_SOUNDS = set(REF["sounds"])
VANILLA_PARTICLES = set(REF["particles"])
VANILLA_ENTITIES = set(REF["entities"])
VANILLA_EFFECTS = {"speed", "slowness", "haste", "mining_fatigue", "strength", "instant_health", "instant_damage",
                   "jump_boost", "nausea", "regeneration", "resistance", "fire_resistance", "water_breathing",
                   "invisibility", "blindness", "night_vision", "hunger", "weakness", "poison", "wither",
                   "health_boost", "absorption", "saturation", "levitation", "fatal_poison", "conduit_power",
                   "slow_falling", "bad_omen", "village_hero", "darkness", "wind_charged", "weaving", "oozing",
                   "infested", "trial_omen", "raid_omen"}
VANILLA_MATERIALS = {"entity", "entity_alphatest", "entity_alphablend", "entity_emissive", "entity_emissive_alpha",
                     "entity_emissive_alpha_one_sided", "entity_nocull", "entity_alphatest_glint", "armor", "armor_enchanted"}
BOUND = {"root", "waist", "body", "head", "rightArm", "leftArm", "rightLeg", "leftLeg"}

checks = 0
errors: list = []


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        errors.append(msg)
    return cond


def load(path):
    try:
        return ljson.load(path)
    except Exception as e:  # noqa: BLE001
        errors.append(f"invalid JSON {os.path.relpath(path, ROOT)}: {e}")
        return None


def all_json(root):
    return sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True))


# ----------------------------------------------------------------------------- load everything
for f in all_json(BP) + all_json(RP):
    check(load(f) is not None, f"json {f}")

bpm = load(os.path.join(BP, "manifest.json"))
rpm = load(os.path.join(RP, "manifest.json"))
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs must be unique")
check(any(d.get("uuid") == rpm["header"]["uuid"] for d in bpm["dependencies"]), "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
check(rpm["header"].get("pack_scope") == "world", "RP pack_scope must be 'world' (cooperative add-on)")
for m in (bpm, rpm):
    check(m["header"].get("min_engine_version") == [1, 26, 60], "min_engine_version set on both packs")
deps = {d.get("module_name"): d.get("version") for d in bpm["dependencies"] if "module_name" in d}
check(deps.get("@minecraft/server") == "2.11.0" and deps.get("@minecraft/server-ui") == "2.3.0", "stable script module versions")
script = next(m for m in bpm["modules"] if m["type"] == "script")
check(os.path.exists(os.path.join(BP, script["entry"])), "script entry exists")
check(os.path.exists(os.path.join(BP, "pack_icon.png")) and os.path.exists(os.path.join(RP, "pack_icon.png")), "pack icons")

# ----------------------------------------------------------------------------- geometry
geos = {}
for f in glob.glob(os.path.join(RP, "models", "**", "*.geo.json"), recursive=True):
    d = load(f)
    for g in d["minecraft:geometry"]:
        gid = g["description"]["identifier"]
        check(gid not in geos, f"duplicate geometry {gid}")
        check(gid.startswith("geometry.plrace."), f"geometry namespaced: {gid}")
        geos[gid] = g
        names = [b["name"] for b in g["bones"]]
        check(len(set(n.lower() for n in names)) == len(names), f"{gid}: duplicate bone names")
        for b in g["bones"]:
            if "parent" in b:
                check(b["parent"] in names, f"{gid}: bone {b['name']} parent {b['parent']} missing")
            for c in b.get("cubes", []):
                for face, uv in c.get("uv", {}).items():
                    u, v = uv["uv"]
                    w, h = uv["uv_size"]
                    tw, th = g["description"]["texture_width"], g["description"]["texture_height"]
                    check(0 <= u and 0 <= v and u + w <= tw and v + h <= th, f"{gid}: UV out of bounds on {b['name']}/{face}")

vanilla_bones = {b["name"]: b for b in json.load(open(os.path.join(HERE, "vanilla", "humanoid_custom_bones.json")))["geometry.humanoid.custom"]}
for gid, g in geos.items():
    if gid.startswith("geometry.plrace.jackalope") or gid.startswith("geometry.plrace.golem") or gid.startswith("geometry.plrace.salamander"):
        bones = {b["name"]: b for b in g["bones"]}
        for bn in BOUND:
            if check(bn in bones, f"{gid}: bound bone {bn} missing"):
                vp = vanilla_bones[bn]["pivot"]
                check(all(abs(a - b) < 1e-6 for a, b in zip(bones[bn]["pivot"], vp)), f"{gid}: {bn} pivot must match the player skeleton {vp}")
                check("rotation" not in bones[bn], f"{gid}: bound bone {bn} must not have a rest rotation")

# ----------------------------------------------------------------------------- animations
anims = {}
for f in glob.glob(os.path.join(RP, "animations", "**", "*.json"), recursive=True):
    for k, v in load(f)["animations"].items():
        check(k not in anims, f"duplicate animation {k}")
        check(k.startswith("animation.plrace."), f"animation namespaced: {k}")
        anims[k] = v
ctrls = {}
for f in glob.glob(os.path.join(RP, "animation_controllers", "**", "*.json"), recursive=True):
    for k, v in load(f)["animation_controllers"].items():
        ctrls[k] = v
rcs = {}
for f in glob.glob(os.path.join(RP, "render_controllers", "**", "*.json"), recursive=True):
    for k, v in load(f)["render_controllers"].items():
        rcs[k] = v
particles = {}
for f in glob.glob(os.path.join(RP, "particles", "**", "*.json"), recursive=True):
    d = load(f)["particle_effect"]
    pid = d["description"]["identifier"]
    particles[pid] = d
    tex = d["description"]["basic_render_parameters"]["texture"]
    check(os.path.exists(os.path.join(RP, tex + ".png")), f"particle {pid} texture")
    check(pid.startswith("plrace:"), f"particle namespaced {pid}")

pose_bones = {"rightarm", "leftarm", "body", "head", "rightleg", "leftleg", "root", "waist"}
for k, v in anims.items():
    if k.startswith("animation.plrace.pose."):
        for bn in v.get("bones", {}):
            check(bn.lower() in pose_bones, f"pose {k} animates non-player bone {bn}")

# ----------------------------------------------------------------------------- attachables
atts = {}
for f in glob.glob(os.path.join(RP, "attachables", "**", "*.json"), recursive=True):
    d = load(f)["minecraft:attachable"]["description"]
    iid = d["identifier"]
    atts[iid] = d
    for key, gid in d["geometry"].items():
        check(gid in geos, f"{iid}: geometry {gid} missing")
    for key, tex in d["textures"].items():
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"{iid}: texture {tex} missing")
    for key, mat in d["materials"].items():
        check(mat in VANILLA_MATERIALS, f"{iid}: unknown material {mat}")
    for rc in d["render_controllers"]:
        check(rc in rcs, f"{iid}: render controller {rc} missing")
        if rc in rcs:
            gkey = rcs[rc]["geometry"].split(".")[-1]
            check(gkey in d["geometry"], f"{iid}: render controller {rc} needs geometry key {gkey}")
            for mm in rcs[rc]["materials"]:
                for _, expr in mm.items():
                    mk = expr.split(".")[-1]
                    check(mk in d["materials"], f"{iid}: {rc} needs material key {mk}")
    geo_bones = set()
    for gid in d["geometry"].values():
        if gid in geos:
            geo_bones |= {b["name"].lower() for b in geos[gid]["bones"]}
    locators = set()
    for gid in d["geometry"].values():
        for b in geos.get(gid, {}).get("bones", []):
            locators |= set(b.get("locators", {}).keys())
    short = d["animations"]
    for sn, full in short.items():
        if full.startswith("controller."):
            check(full in ctrls, f"{iid}: controller {full} missing")
            for st in ctrls.get(full, {}).get("states", {}).values():
                for a in st.get("animations", []):
                    an = a if isinstance(a, str) else list(a.keys())[0]
                    check(an in short, f"{iid}: controller state animation {an} not mapped")
            continue
        if not check(full in anims, f"{iid}: animation {full} missing"):
            continue
        race_key = d["geometry"]["default"].rsplit(".", 1)[0] + "."
        race_bones = {b["name"].lower() for g, gd in geos.items() if g.startswith(race_key) for b in gd["bones"]}
        for bn in anims[full].get("bones", {}):
            # layers are shared by a race's forms: a part that only exists in some forms is skipped
            # by the client in the others, but every bone must exist in at least one form (typos)
            check(bn.lower() in geo_bones or bn.lower() in race_bones, f"{iid}: animation {full} targets missing bone {bn}")
        for t, pe in anims[full].get("particle_effects", {}).items():
            for e in (pe if isinstance(pe, list) else [pe]):
                check(e["effect"] in d.get("particle_effects", {}), f"{iid}: particle key {e['effect']} not declared")
                if "locator" in e:
                    check(e["locator"] in locators, f"{iid}: locator {e['locator']} missing")
    for entry in d["scripts"]["animate"]:
        nm = entry if isinstance(entry, str) else list(entry.keys())[0]
        check(nm in short, f"{iid}: animate entry {nm} not mapped")
    for key, pid in d.get("particle_effects", {}).items():
        check(pid in particles or pid in VANILLA_PARTICLES, f"{iid}: particle {pid} missing")

# ----------------------------------------------------------------------------- Molang
import molang as _molang  # noqa: E402

KNOWN_QUERIES = {
    "life_time", "modified_distance_moved", "modified_move_speed", "is_on_ground", "is_in_water", "is_swimming",
    "vertical_speed", "is_sprinting", "is_sneaking", "target_x_rotation", "target_y_rotation", "yaw_speed",
    "hurt_time", "time_of_day", "anim_time", "all_animations_finished", "any_animation_finished",
    "is_item_equipped", "is_using_item", "is_first_person", "ground_speed", "is_moving", "delta_time",
    "is_riding", "is_gliding", "is_sleeping",
}
PLAYER_PUBLIC = {"attack_time", "is_first_person"}   # variables the player exposes to attachables / poses


def molang_strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from molang_strings(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("effect", "locator", "lerp_mode", "pre_effect_script"):
                continue
            yield from molang_strings(v, f"{path}.{k}")


def check_expr(where, expr, defined):
    try:
        _molang.check(expr)
    except SyntaxError as e:
        check(False, f"{where}: Molang does not parse: {e}")
        return
    for name in re.findall(r"\b(?:q|query)\.([a-z_0-9]+)", expr):
        check(name in KNOWN_QUERIES, f"{where}: unknown query q.{name}")
    for name in re.findall(r"\b(?:v|variable)\.([a-z_0-9]+)", expr):
        check(name in defined or name in PLAYER_PUBLIC, f"{where}: variable v.{name} is never set")
    check(not re.search(r"\bv\.[a-z_0-9]+\s*=", expr) or where.endswith("pre_animation"), f"{where}: assignment outside pre_animation")


race_vars = {}
for f in glob.glob(os.path.join(RP, "attachables", "**", "*.json"), recursive=True):
    d = load(f)["minecraft:attachable"]["description"]
    pre = d.get("scripts", {}).get("pre_animation", [])
    defined = set()
    for stmt in pre:
        defined |= set(re.findall(r"\bv\.([a-z_0-9]+)\s*=", stmt))
        check_expr(f"{d['identifier']} pre_animation", stmt, defined)
    race_vars[d["identifier"]] = defined
    for entry in d.get("scripts", {}).get("animate", []):
        if isinstance(entry, dict):
            for k, v in entry.items():
                check_expr(f"{d['identifier']} animate {k}", v, defined)
all_defined = set().union(*race_vars.values()) if race_vars else set()
for f in glob.glob(os.path.join(RP, "animations", "**", "*.json"), recursive=True):
    for name, a in load(f).get("animations", {}).items():
        for where, expr in molang_strings(a.get("bones", {})):
            check_expr(f"{name}{where}", expr, all_defined)
        if "anim_time_update" in a:
            check_expr(f"{name}.anim_time_update", a["anim_time_update"], all_defined)
for f in glob.glob(os.path.join(RP, "animation_controllers", "**", "*.json"), recursive=True):
    for name, c in load(f).get("animation_controllers", {}).items():
        for st_name, st in c.get("states", {}).items():
            for tr in st.get("transitions", []):
                for target, cond in tr.items():
                    check(target in c["states"], f"{name}: transition to unknown state {target}")
                    check_expr(f"{name}.{st_name}->{target}", cond, all_defined)
            for a in st.get("animations", []):
                if isinstance(a, dict):
                    for k, v in a.items():
                        check_expr(f"{name}.{st_name}.{k}", v, all_defined)
        check(c.get("initial_state", "default") in c.get("states", {}), f"{name}: initial state missing")

# ----------------------------------------------------------------------------- items & icons
item_tex = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
for k, v in item_tex.items():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {k}")
lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line and not line.startswith("#"):
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
items = {}
for f in glob.glob(os.path.join(BP, "items", "**", "*.json"), recursive=True):
    d = load(f)["minecraft:item"]
    iid = d["description"]["identifier"]
    items[iid] = d
    comps = d["components"]
    check(comps.get("minecraft:icon") in item_tex, f"{iid}: icon texture ref")
    dn = comps.get("minecraft:display_name", {}).get("value")
    check(dn in lang, f"{iid}: display name {dn} not in en_US.lang")
    if iid.startswith("plrace:form_"):
        check(iid in atts, f"{iid}: attachable missing")
        check("plrace:form" in comps["minecraft:tags"]["tags"], f"{iid}: form tag")
        check(comps["minecraft:wearable"]["slot"] == "slot.armor.head", f"{iid}: head slot")
for k, v in lang.items():
    check(len(v) > 0, f"empty lang value {k}")

# ----------------------------------------------------------------------------- vanilla overrides
vp = ljson.load(os.path.join(HERE, "vanilla", "player.render_controllers.json"))["render_controllers"]["controller.render.player.third_person"]
ours = rcs.get("controller.render.player.third_person")
if check(ours is not None, "player third-person override present"):
    vparts = [list(x.keys())[0] for x in vp["part_visibility"]]
    oparts = [list(x.keys())[0] for x in ours["part_visibility"]]
    check(vparts == oparts, "player override keeps vanilla part list")
    for x, y in zip(vp["part_visibility"], ours["part_visibility"]):
        (kv, vv), (ko, vo) = list(x.items())[0], list(y.items())[0]
        crest_items = sorted(i for i in items if i.startswith("plrace:form_")) if items else []
        m = re.search(r"query\.is_item_name_any\('slot\.armor\.head', 0, ([^)]*)\)", vo)
        listed = sorted(re.findall(r"'([a-z_:]+)'", m.group(1))) if m else []
        check(m is not None, f"override for {kv} tests the form crest ({vo[:60]})")
        cond = m.group(0) if m else ""
        check(vo == f"!{cond}" or vo == f"({vv}) && !{cond}", f"override for {kv} = vanilla && !form")
        if crest_items:
            check(listed == crest_items, f"override for {kv} lists every crest item")
    for key in ("geometry", "materials", "textures"):
        check(vp[key] == ours[key], f"player override keeps vanilla {key}")
va = ljson.load(os.path.join(HERE, "vanilla", "armor.render_controllers.json"))["render_controllers"]["controller.render.armor"]
oa = rcs.get("controller.render.armor")
if check(oa is not None, "armor override present"):
    for key in ("geometry", "materials", "textures"):
        check(va[key] == oa[key], f"armor override keeps vanilla {key}")

# ----------------------------------------------------------------------------- entities
entities = {}
for f in glob.glob(os.path.join(BP, "entities", "**", "*.json"), recursive=True):
    d = load(f)["minecraft:entity"]
    entities[d["description"]["identifier"]] = d
for f in glob.glob(os.path.join(RP, "entity", "**", "*.json"), recursive=True):
    d = load(f)["minecraft:client_entity"]["description"]
    eid = d["identifier"]
    check(eid in entities, f"client entity {eid} has a behavior")
    for gid in d["geometry"].values():
        check(gid in geos, f"{eid}: geometry {gid}")
    for t in d["textures"].values():
        check(os.path.exists(os.path.join(RP, t + ".png")), f"{eid}: texture {t}")
    for rc in d["render_controllers"]:
        check(rc in rcs, f"{eid}: render controller {rc}")
    gb = set()
    for gid in d["geometry"].values():
        gb |= {b["name"].lower() for b in geos.get(gid, {}).get("bones", [])}
    for full in d["animations"].values():
        if check(full in anims, f"{eid}: animation {full}"):
            for bn in anims[full].get("bones", {}):
                check(bn.lower() in gb, f"{eid}: {full} bone {bn}")
    check(f"entity.{eid}.name" in lang, f"{eid}: lang name")

# ----------------------------------------------------------------------------- scripts
js = ""
for f in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    js += open(f, encoding="utf-8").read() + "\n"
for pid in set(re.findall(r'"(plrace:[a-z_]+)"', js)):
    known = pid in particles or pid in items or pid in entities or pid in atts or pid in {
        "plrace:focus", "plrace:codex", "plrace:form", "plrace:data", "plrace:settings", "plrace:bloodmoon", "plrace:weather",
        "plrace:race", "plrace:moon_action", "plrace:blood_moon", "plrace:setrace", "plrace:resetcooldowns",
        "plrace:unique", "plrace:unique_action"}
    check(known, f"script references unknown id {pid}")
for m in re.finditer(r'(?:sound|privateSound)\([^,]+,\s*"([a-z0-9_.]+)"', js):
    check(m.group(1) in VANILLA_SOUNDS, f"script sound {m.group(1)} not a vanilla sound event")
for m in re.finditer(r'playSound\("([a-z0-9_.]+)"', js):
    check(m.group(1) in VANILLA_SOUNDS, f"script sound {m.group(1)} not a vanilla sound event")
for m in re.finditer(r'(?:effect\([^,]+,\s*|getEffect\(|removeEffect\()"([a-z_]+)"', js):
    check(m.group(1) in VANILLA_EFFECTS, f"script effect {m.group(1)} unknown")
for m in re.finditer(r'pose\([^,]+,\s*"([a-z_]+)"', js):
    check(f"animation.plrace.pose.{m.group(1)}" in anims, f"script pose {m.group(1)} missing")
for m in re.finditer(r"(?:spawnParticle|particle|privateParticle)\([^\"]*?\"(plrace:[a-z_]+)\"", js):
    check(m.group(1) in particles, f"script particle {m.group(1)} missing")
for m in re.finditer(r"q\.is_item_name_any\('slot\.armor\.head', 0, ([^)]+)\)", js):
    for iid in re.findall(r"'([a-z_:]+)'", m.group(1)):
        check(iid in items, f"stop expression references unknown item {iid}")
check(os.path.exists(os.path.join(RP, "fogs", "plrace_blood_moon.json")), "blood moon fog file")

# ----------------------------------------------------------------------------- textures
for f in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(f)
    w, h = im.size
    check(w * h * 4 <= 262144 or "/ui/" in f, f"texture over memory budget: {os.path.relpath(f, RP)}")

print(f"{checks} checks, {len(errors)} errors")
for e in errors[:80]:
    print("  ERROR", e)
sys.exit(1 if errors else 0)
