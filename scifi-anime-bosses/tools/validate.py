"""
validate.py - static validation of the built VESPER-0 packs.

1. JSON-schema validation of every file against the Minecraft Bedrock JSON schemas that
   ship with Microsoft's Minecraft Creator Tools (Blockception schemas).
2. Cross-reference checks the schemas cannot do: geometry <-> animations (bones, locators),
   render controllers <-> geometry/materials/textures, molang syntax + allowed queries +
   synced properties, particles/sounds/textures/lang keys referenced by packs and by the
   compiled scripts, UV bounds, texture sizes, manifests and dependencies.

Exit code 1 on any error.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import molang  # noqa: E402

BP = os.path.join(ROOT, "build", "SAB_VESPER_BP")
RP = os.path.join(ROOT, "build", "SAB_VESPER_RP")
CT_SCHEMAS = os.environ.get("CT_SCHEMAS") or next(iter(glob.glob(
    "/root/.npm/_npx/*/node_modules/@minecraft/creator-tools/res/latest/schemas")), None)

VANILLA_MATERIALS = {
    "entity", "entity_alphatest", "entity_alphablend", "entity_emissive", "entity_emissive_alpha",
    "entity_emissive_alpha_one_sided", "entity_beam_additive", "entity_beam", "charged_creeper", "entity_nocull",
    "entity_alphatest_one_sided", "beacon_beam", "beacon_beam_transparent", "breeze_wind", "conduit_wind",
    "guardian_ghost", "wither_boss_armor", "warden_bioluminescent_layer",
}
PARTICLE_MATERIALS = {"particles_alpha", "particles_blend", "particles_add", "particles_opaque"}
VANILLA_ITEMS_USED = {"minecraft:amethyst_shard", "minecraft:copper_ingot", "minecraft:end_crystal", "minecraft:ender_eye"}

errors: List[str] = []
warnings: List[str] = []
checks = 0


def err(msg):
    errors.append(msg)


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        err(msg)
    return cond


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rel(p):
    return os.path.relpath(p, ROOT)


# ----------------------------------------------------------------------------- schema validation

SCHEMA_MAP = [
    ("BP", "entities/**/*.json", "behavior/entities/entities.json"),
    ("BP", "items/**/*.json", "behavior/items/items.json"),
    ("BP", "recipes/**/*.json", "behavior/recipes/recipes.json"),
    ("BP", "loot_tables/**/*.json", "behavior/loot_tables/loot_tables.json"),
    ("RP", "entity/**/*.json", "resource/entity/entity.json"),
    ("RP", "models/**/*.json", "resource/models/entity/model_entity.json"),
    ("RP", "animations/*.json", "resource/animations/actor_animation.json"),
    ("RP", "animation_controllers/*.json", "resource/animation_controllers/animation_controller.json"),
    ("RP", "render_controllers/*.json", "resource/render_controllers/render_controllers.json"),
    ("RP", "particles/**/*.json", "resource/particles/particles.json"),
    ("RP", "sounds/sound_definitions.json", "resource/sounds/sound_definitions.json"),
    ("RP", "fogs/*.json", "resource/fog/fog.json"),
    ("BP", "manifest.json", "general/manifest.json"),
    ("RP", "manifest.json", "general/manifest.json"),
]


def _known_schema_gap(e) -> bool:
    """Engine features the community schemas do not model (verified against vanilla data)."""
    inst = e.instance
    # vanilla sound_definitions.json (1.26.60) uses "load_on_low_memory" on 369 definitions
    if isinstance(inst, dict) and "load_on_low_memory" in inst and "name" in inst:
        trimmed = {k: v for k, v in inst.items() if k != "load_on_low_memory"}
        return set(trimmed) <= {"name", "volume", "pitch", "stream", "weight", "is3D", "interruptible"}
    return False


def schema_validation():
    try:
        import jsonschema
    except ImportError:
        warnings.append("jsonschema not installed: schema validation skipped")
        return 0
    if not CT_SCHEMAS or not os.path.isdir(CT_SCHEMAS):
        warnings.append("Creator Tools schemas not found: schema validation skipped")
        return 0
    n = 0
    for pack, pattern, schema_rel in SCHEMA_MAP:
        sp = os.path.join(CT_SCHEMAS, schema_rel)
        if not os.path.exists(sp):
            alt = glob.glob(os.path.join(CT_SCHEMAS, os.path.dirname(schema_rel), "*.json"))
            alt = [a for a in alt if not a.endswith("index.json")]
            if not alt:
                warnings.append(f"schema {schema_rel} missing")
                continue
            sp = alt[0]
        schema = load(sp)
        validator = jsonschema.Draft7Validator(schema)
        base = BP if pack == "BP" else RP
        for path in glob.glob(os.path.join(base, pattern), recursive=True):
            data = load(path)
            errs = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
            n += 1
            for e in errs[:5]:
                loc = "/".join(str(p) for p in e.path)
                if _known_schema_gap(e):
                    continue
                err(f"[schema] {rel(path)} @ {loc}: {e.message[:300]}")
    return n


# ----------------------------------------------------------------------------- geometry index

class Geo:
    def __init__(self, ident, desc, bones):
        self.ident = ident
        self.desc = desc
        self.bones = {b["name"]: b for b in bones}
        self.locators = {}
        for b in bones:
            for k in (b.get("locators") or {}):
                self.locators[k] = b["name"]


def load_geometries() -> Dict[str, Geo]:
    geos = {}
    for path in glob.glob(os.path.join(RP, "models", "**", "*.json"), recursive=True):
        data = load(path)
        for g in data.get("minecraft:geometry", []):
            ident = g["description"]["identifier"]
            ok(ident not in geos, f"duplicate geometry {ident}")
            geos[ident] = Geo(ident, g["description"], g.get("bones", []))
            tw, th = g["description"]["texture_width"], g["description"]["texture_height"]
            names = set()
            for b in g.get("bones", []):
                ok(b["name"] not in names, f"{ident}: duplicate bone {b['name']}")
                names.add(b["name"])
                if b.get("parent"):
                    ok(b["parent"] in names or any(x["name"] == b["parent"] for x in g["bones"]),
                       f"{ident}: bone {b['name']} has unknown parent {b['parent']}")
                for c in b.get("cubes", []):
                    for face, uv in c.get("uv", {}).items():
                        u, v = uv["uv"]
                        w, h = uv["uv_size"]
                        lo_u, hi_u = min(u, u + w), max(u, u + w)
                        lo_v, hi_v = min(v, v + h), max(v, v + h)
                        ok(lo_u >= -1e-6 and hi_u <= tw + 1e-6 and lo_v >= -1e-6 and hi_v <= th + 1e-6,
                           f"{ident}: bone {b['name']} {face} uv out of bounds {uv}")
    return geos


# ----------------------------------------------------------------------------- molang

def check_molang(expr, where, props=None, extra_vars=()):
    global checks
    if not isinstance(expr, str):
        return
    checks += 1
    try:
        tree = molang.parse(expr)
    except molang.MolangError as e:
        err(f"[molang] {where}: {e}")
        return
    qs, fs, vs = molang.references(tree)
    for q in qs:
        if q not in molang.KNOWN_QUERIES:
            err(f"[molang] {where}: unknown/unexpected query {q}")
    for f in fs:
        if f not in molang.MATH_FUNCS:
            err(f"[molang] {where}: unknown math function {f}")
    if props is not None:
        for m in re.finditer(r"query\.(?:property|has_property)\('([^']+)'\)", expr.replace('"', "'")):
            name = m.group(1)
            ok(name in props, f"[molang] {where}: property {name} is not defined on the entity")
            if name in props:
                ok(props[name].get("client_sync"), f"[molang] {where}: property {name} is read on the client but not client_sync")


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


# ----------------------------------------------------------------------------- cross references

def cross_refs():
    geos = load_geometries()
    # behavior entities
    bp_entities = {}
    for path in glob.glob(os.path.join(BP, "entities", "**", "*.json"), recursive=True):
        d = load(path)["minecraft:entity"]
        ident = d["description"]["identifier"]
        bp_entities[ident] = d
        props = d["description"].get("properties", {})
        ok(len(props) <= 32, f"{ident}: more than 32 properties")
        for pn, pd in props.items():
            ok(re.match(r"^[a-z0-9_]+:[a-z0-9_]+$", pn) is not None, f"{ident}: bad property name {pn}")
            if pd["type"] in ("int", "float"):
                lo, hi = pd["range"]
                ok(lo <= pd["default"] <= hi, f"{ident}: default of {pn} out of range")
        for ev, body in d.get("events", {}).items():
            for key in ("add", "remove"):
                for g in body.get(key, {}).get("component_groups", []):
                    ok(g in d.get("component_groups", {}), f"{ident}: event {ev} references unknown group {g}")
        loot = d["components"].get("minecraft:loot", {}).get("table")
        if loot:
            ok(os.path.exists(os.path.join(BP, loot)), f"{ident}: loot table {loot} missing")
    # client entities
    rc_data = {}
    for path in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
        rc_data.update(load(path)["render_controllers"])
    anim_data = {}
    for path in glob.glob(os.path.join(RP, "animations", "*.json")):
        anim_data.update(load(path)["animations"])
    ctrl_data = {}
    for path in glob.glob(os.path.join(RP, "animation_controllers", "*.json")):
        ctrl_data.update(load(path)["animation_controllers"])
    particles = {}
    for path in glob.glob(os.path.join(RP, "particles", "**", "*.json"), recursive=True):
        p = load(path)["particle_effect"]
        particles[p["description"]["identifier"]] = (path, p)
    sounds = load(os.path.join(RP, "sounds", "sound_definitions.json"))["sound_definitions"]
    lang = {}
    for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
        if "=" in line:
            k, v = line.rstrip("\n").split("=", 1)
            lang[k] = v
    client_ids = set()
    for path in glob.glob(os.path.join(RP, "entity", "**", "*.json"), recursive=True):
        d = load(path)["minecraft:client_entity"]["description"]
        ident = d["identifier"]
        client_ids.add(ident)
        ok(ident in bp_entities, f"client entity {ident} has no behavior entity")
        props = bp_entities.get(ident, {}).get("description", {}).get("properties", {})
        where = f"{rel(path)}"
        for k, m in d.get("materials", {}).items():
            ok(m.split(".")[0] in VANILLA_MATERIALS, f"{where}: material {m} is not a known vanilla material")
        for k, t in d.get("textures", {}).items():
            ok(os.path.exists(os.path.join(RP, t + ".png")), f"{where}: texture {t}.png missing")
        for k, g in d.get("geometry", {}).items():
            ok(g in geos, f"{where}: geometry {g} missing")
        main_geo = geos.get(d.get("geometry", {}).get("default"))
        scripts = d.get("scripts", {})
        for s in scripts.get("initialize", []) + scripts.get("pre_animation", []):
            check_molang(s, f"{where} scripts", props)
        for a in scripts.get("animate", []):
            if isinstance(a, dict):
                for name, cond in a.items():
                    ok(name in d.get("animations", {}), f"{where}: animate references unknown {name}")
                    check_molang(cond, f"{where} animate {name}", props)
            else:
                ok(a in d.get("animations", {}), f"{where}: animate references unknown {a}")
        pfx = d.get("particle_effects", {})
        for k, ident_p in pfx.items():
            ok(ident_p in particles, f"{where}: particle {ident_p} missing")
        sfx = d.get("sound_effects", {})
        for k, s in sfx.items():
            ok(s in sounds, f"{where}: sound {s} missing from sound_definitions")
        # animations / controllers
        for short, full in d.get("animations", {}).items():
            if full.startswith("controller."):
                ok(full in ctrl_data, f"{where}: controller {full} missing")
                ctrl = ctrl_data.get(full, {})
                for sname, st in ctrl.get("states", {}).items():
                    for a in st.get("animations", []):
                        names = list(a.keys()) if isinstance(a, dict) else [a]
                        for nm in names:
                            ok(nm in d["animations"], f"{full}.{sname}: animation {nm} not mapped on {ident}")
                        if isinstance(a, dict):
                            for cond in a.values():
                                check_molang(cond, f"{full}.{sname} blend", props)
                    for tr in st.get("transitions", []):
                        for to, cond in tr.items():
                            ok(to in ctrl["states"], f"{full}.{sname}: transition to unknown state {to}")
                            check_molang(cond, f"{full}.{sname} -> {to}", props)
                    ok(ctrl.get("initial_state", "default") in ctrl["states"], f"{full}: initial state missing")
                continue
            ok(full in anim_data, f"{where}: animation {full} missing")
            an = anim_data.get(full, {})
            for bone, chans in an.get("bones", {}).items():
                ok(main_geo is not None and bone in main_geo.bones, f"{full}: bone {bone} not in {d.get('geometry', {}).get('default')}")
                for ch in chans.values():
                    for s in walk_strings(ch):
                        if s in ("linear", "catmullrom"):
                            continue
                        check_molang(s, f"{full}/{bone}", props)
            for key in ("anim_time_update", "blend_weight"):
                if key in an:
                    check_molang(an[key], f"{full} {key}", props)
            for t, effs in an.get("particle_effects", {}).items():
                for e in effs if isinstance(effs, list) else [effs]:
                    ok(e["effect"] in pfx, f"{full}@{t}: particle effect {e['effect']} not mapped on {ident}")
                    if "locator" in e and main_geo is not None:
                        ok(e["locator"] in main_geo.locators, f"{full}@{t}: locator {e['locator']} not in geometry")
            for t, effs in an.get("sound_effects", {}).items():
                for e in effs if isinstance(effs, list) else [effs]:
                    ok(e["effect"] in sfx, f"{full}@{t}: sound effect {e['effect']} not mapped on {ident}")
        # render controllers
        for rcn in d.get("render_controllers", []):
            if isinstance(rcn, dict):
                for nm, cond in rcn.items():
                    check_molang(cond, f"{where} render condition", props)
                    rcn = nm
            ok(rcn in rc_data, f"{where}: render controller {rcn} missing")
            rc = rc_data.get(rcn, {})
            gkey = rc.get("geometry", "").split(".")[-1]
            gid = d.get("geometry", {}).get(gkey)
            ok(gid is not None, f"{rcn}: Geometry.{gkey} not defined on {ident}")
            geo = geos.get(gid)
            for mat in rc.get("materials", []):
                for v in mat.values():
                    ok(v.split(".")[-1] in d.get("materials", {}), f"{rcn}: {v} not defined on {ident}")
            arrays = rc.get("arrays", {}).get("textures", {})
            for arr in arrays.values():
                for t in arr:
                    ok(t.split(".")[-1] in d.get("textures", {}), f"{rcn}: {t} not defined on {ident}")
            for t in rc.get("textures", []):
                if t.startswith("Texture."):
                    ok(t.split(".")[-1] in d.get("textures", {}), f"{rcn}: {t} not defined on {ident}")
                else:
                    for m in re.finditer(r"\[(.*)\]$", t):
                        check_molang(m.group(1), f"{rcn} texture index", props)
            for pv in rc.get("part_visibility", []):
                for bone, cond in pv.items():
                    if bone != "*":
                        ok(geo is not None and bone in geo.bones, f"{rcn}: part_visibility bone {bone} not in {gid}")
                    if isinstance(cond, str) and cond not in ("true", "false"):
                        check_molang(cond, f"{rcn} part_visibility {bone}", props)
            for key in ("is_hurt_color", "on_fire_color", "color", "overlay_color"):
                for s in walk_strings(rc.get(key, {})):
                    check_molang(s, f"{rcn} {key}", props)
            for s in walk_strings(rc.get("uv_anim", {})):
                check_molang(s, f"{rcn} uv_anim", props)
        ok(f"entity.{ident}.name" in lang, f"lang: entity.{ident}.name missing")
    for ident in bp_entities:
        ok(ident in client_ids, f"behavior entity {ident} has no client entity")
    # particles
    for ident, (path, p) in particles.items():
        mat = p["description"]["basic_render_parameters"]["material"]
        ok(mat in PARTICLE_MATERIALS, f"{rel(path)}: particle material {mat}")
        texp = p["description"]["basic_render_parameters"]["texture"]
        ok(os.path.exists(os.path.join(RP, texp + ".png")), f"{rel(path)}: texture {texp} missing")
        for s in walk_strings(p["components"]):
            if s in ("outwards", "inwards", "rotate_xyz", "lookat_y", "lookat_xyz", "lookat_direction",
                     "derive_from_velocity", "x", "y", "z"):
                continue
            check_molang(s, f"{rel(path)}")
    # sounds
    for name, sd in sounds.items():
        for s in sd["sounds"]:
            nm = s["name"] if isinstance(s, dict) else s
            ok(os.path.exists(os.path.join(RP, nm + ".ogg")), f"sound file {nm}.ogg missing")
    # items
    item_tex = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
    for path in glob.glob(os.path.join(BP, "items", "**", "*.json"), recursive=True):
        d = load(path)["minecraft:item"]
        ident = d["description"]["identifier"]
        icon = d["components"].get("minecraft:icon")
        icon_name = icon if isinstance(icon, str) else (icon or {}).get("textures", {}).get("default")
        ok(icon_name in item_tex, f"{ident}: icon {icon_name} not in item_texture.json")
        if icon_name in item_tex:
            ok(os.path.exists(os.path.join(RP, item_tex[icon_name]["textures"] + ".png")), f"{ident}: icon png missing")
        dn = d["components"].get("minecraft:display_name", {}).get("value")
        ok(dn in lang, f"{ident}: display name key {dn} missing in lang")
    for path in glob.glob(os.path.join(BP, "recipes", "**", "*.json"), recursive=True):
        txt = open(path).read()
        for it in re.findall(r'"(minecraft:[a-z_]+)"', txt):
            if it.startswith("minecraft:recipe"):
                continue
            ok(it in VANILLA_ITEMS_USED, f"{rel(path)}: unexpected vanilla item {it}")
    return geos, bp_entities, particles, sounds


def check_textures():
    from PIL import Image
    for path in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
        im = Image.open(path)
        w, h = im.size
        ok(w & (w - 1) == 0 and h & (h - 1) == 0, f"{rel(path)}: texture size {w}x{h} not a power of two")
        ok(w <= 1024 and h <= 1024, f"{rel(path)}: texture larger than 1024 (mobile budget)")


def check_manifests():
    bpm = load(os.path.join(BP, "manifest.json"))
    rpm = load(os.path.join(RP, "manifest.json"))
    uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
    ok(len(set(uuids)) == len(uuids), "manifest uuids not unique")
    for u in uuids:
        ok(re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", u) is not None, f"bad uuid {u}")
    deps = {d.get("uuid") for d in bpm["dependencies"]}
    ok(rpm["header"]["uuid"] in deps, "BP does not depend on RP")
    ok(bpm["header"]["uuid"] in {d.get("uuid") for d in rpm["dependencies"]}, "RP does not depend on BP")
    script = [m for m in bpm["modules"] if m["type"] == "script"]
    ok(len(script) == 1, "BP must have one script module")
    if script:
        ok(os.path.exists(os.path.join(BP, script[0]["entry"])), f"script entry {script[0]['entry']} missing")
    srv = [d for d in bpm["dependencies"] if d.get("module_name") == "@minecraft/server"]
    ok(srv and srv[0]["version"] == "2.11.0", "@minecraft/server dependency must be 2.11.0 (stable)")
    ok(bpm["header"]["min_engine_version"] == [1, 26, 60], "min_engine_version must be 1.26.60")


def check_scripts(particles, sounds, bp_entities):
    """Every sab:* id / sound / fog string literal in the compiled scripts must exist."""
    js_files = glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True)
    if not js_files:
        err("no compiled scripts")
        return
    item_ids = set()
    for path in glob.glob(os.path.join(BP, "items", "**", "*.json"), recursive=True):
        item_ids.add(load(path)["minecraft:item"]["description"]["identifier"])
    fog_ids = set()
    for path in glob.glob(os.path.join(RP, "fogs", "*.json")):
        fog_ids.add(load(path)["minecraft:fog_settings"]["description"]["identifier"])
    known = set(particles) | set(bp_entities) | item_ids | fog_ids
    props = set()
    for d in bp_entities.values():
        props |= set(d["description"].get("properties", {}))
    events = set()
    for d in bp_entities.values():
        events |= set(d.get("events", {}))
    # keys that legitimately exist only in scripts
    script_only = {
        "sab:arena", "sab:flags", "sab:owner", "sab:cinematics", "sab:halo_awarded",   # dynamic properties
        "sab:vesper", "sab:vesper_cinematics", "sab:vesper_action", "sab:toggle",      # custom commands / enums
    }
    # custom item components and cooldown categories must exist on an item definition
    item_components, cooldowns = set(), set()
    for path in glob.glob(os.path.join(BP, "items", "**", "*.json"), recursive=True):
        comps = load(path)["minecraft:item"]["components"]
        item_components |= {k for k in comps if not k.startswith("minecraft:")}
        if "minecraft:cooldown" in comps:
            cooldowns.add(comps["minecraft:cooldown"]["category"])
    all_src = ""
    for path in js_files:
        src = open(path, encoding="utf-8").read()
        all_src += src
        for m in re.finditer(r'"(sab:[a-z0-9_]+)"', src):
            s = m.group(1)
            ok(s in known or s in props or s in events or s in script_only or s in item_components or s in cooldowns,
               f"{rel(path)}: unknown identifier {s}")
    for comp in item_components:
        ok(f'registerCustomComponent("{comp}"' in all_src, f"item custom component {comp} is never registered by a script")
    for cat in cooldowns:
        ok(f'"{cat}"' in all_src, f"cooldown category {cat} unused by scripts")
        for m in re.finditer(r'"(sab\.(?:vesper|music)\.[a-z0-9_]+)"', src):
            ok(m.group(1) in sounds, f"{rel(path)}: unknown sound {m.group(1)}")


def main():
    n_schema = schema_validation()
    geos, bp_entities, particles, sounds = cross_refs()
    check_textures()
    check_manifests()
    check_scripts(particles, sounds, bp_entities)
    print(f"schema-validated files: {n_schema}")
    print(f"cross-reference checks: {checks}")
    for w in warnings:
        print("WARNING:", w)
    if errors:
        print(f"{len(errors)} ERROR(S):")
        for e in errors[:200]:
            print("  -", e)
        sys.exit(1)
    print("validation passed: 0 errors")


if __name__ == "__main__":
    main()
