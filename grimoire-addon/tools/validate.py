#!/usr/bin/env python3
"""Static validation of the generated packs (run after `python3 tools/build.py`).

Checks, without a game client:
  * every JSON file parses; manifests use stable modules and reference each other correctly
  * exactly three grimoire items, chargeable (use_modifiers) and NOT edible/consumable
  * the spell registry matches the specification table (45 spells, names, cooldowns, I11 rule)
  * every id the scripts use (constructs, mobs, particles, sounds, fogs, blocks, animations)
    resolves to a generated file
  * client entities / attachables: geometry, textures, animations, controllers, render controllers
  * geometry integrity: unique bones, valid parents, UVs inside the texture, texture aspect ratio
  * animations only reference bones that exist in every model that plays them
  * particle textures, sound files, block textures and lang keys exist
  * the .mcaddon contains both packs with their manifests
Exit code 1 if any ERROR is reported.
"""
import glob
import json
import os
import re
import sys
import zipfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "packs", "Grimoire_BP")
RP = os.path.join(ROOT, "packs", "Grimoire_RP")
SRC = os.path.join(ROOT, "src")
ERRORS, WARNINGS, INFO = [], [], []

# Specification table: code -> (name, cooldown seconds). I11's cooldown starts after the flight ends.
SPEC = {
    "P01": ("Pressure Lance", 6), "P02": ("Atlas Piston", 18), "P03": ("Isobaric Severance", 10),
    "P04": ("Cataclysm Salvo", 22), "P05": ("Aegis of Isobars", 25), "P06": ("Counterpressure Mantle", 22),
    "P07": ("Titan's Vise", 30), "P08": ("Atmospheric Labyrinth", 35), "P09": ("Resonance Cage", 28),
    "P10": ("Pressure Step", 5), "P11": ("Skyline Pressure Rail", 14), "P12": ("Barometric Omniscience", 25),
    "P13": ("Equilibrium Theft", 35), "P14": ("Isobaric Citadel", 75), "P15": ("Imperial Edict: Thousand Atmospheres", 180),
    "I01": ("Glacial Sovereign's Lance", 8), "I02": ("Boreal Dragon's Roar", 20), "I03": ("Winter's Guillotine", 14),
    "I04": ("Thousandfold Crystal Rain", 25), "I05": ("Lotus of the Eternal Frost", 28), "I06": ("Mirror of the Frozen Throne", 32),
    "I07": ("Chains of Niflheim", 30), "I08": ("Labyrinth of the Pale Moon", 40), "I09": ("Whiteout Dominion", 45),
    "I10": ("Frost Mirror Traverse", 8), "I11": ("Wings of the Winter Seraph", 20), "I12": ("Imperial Frost Legion", 60),
    "I13": ("Hourglass of Still Winter", 50), "I14": ("Grand Magic: Citadel of the Everlasting Winter", 90),
    "I15": ("Imperial Edict: The Last Winter", 180),
    "B01": ("Crimson Stiletto Rain", 7), "B02": ("Guillotine of the Red Court", 16), "B03": ("Sanguine Leviathan", 24),
    "B04": ("Crown of a Thousand Blades", 26), "B05": ("Aegis of the Scarlet Rose", 25), "B06": ("Royal Reprisal", 28),
    "B07": ("Veinbound Marionette", 30), "B08": ("Garden of the Crimson Thorns", 35), "B09": ("Hematic Maelstrom", 40),
    "B10": ("Bloodstep: Shattered Ruby", 7), "B11": ("Arterial Current", 18), "B12": ("Crimson Familiar: The Royal Stag", 55),
    "B13": ("Sovereign's Pulse", 45), "B14": ("Grand Magic: Scarlet Sea of Lament", 90),
    "B15": ("Imperial Edict: Heart of the Crimson Moon", 180),
}
STABLE_MODULES = {"@minecraft/server": "2.11.0", "@minecraft/server-ui": "2.3.0"}
VANILLA_MATERIALS = {"entity_emissive_alpha", "entity_alphablend", "entity_beam_additive", "entity_alphatest",
                     "entity", "entity_emissive", "entity_custom", "entity_alphatest_one_sided"}


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def rel(p):
    return os.path.relpath(p, ROOT)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def png_exists(base):
    for ext in (".png", ".tga"):
        if os.path.exists(base + ext):
            return base + ext
    return None


# ------------------------------------------------------------------------------------------ JSON
def check_json():
    docs = {}
    for pack in (BP, RP):
        for path in glob.glob(f"{pack}/**/*.json", recursive=True):
            try:
                docs[path] = load(path)
            except Exception as e:  # noqa: BLE001
                err(f"invalid JSON {rel(path)}: {e}")
    INFO.append(f"{len(docs)} JSON files parsed")
    return docs


# ------------------------------------------------------------------------------------ manifests
def check_manifests():
    bp, rp = load(f"{BP}/manifest.json"), load(f"{RP}/manifest.json")
    for name, m in (("BP", bp), ("RP", rp)):
        if m.get("format_version") != 2:
            err(f"{name} manifest format_version should be 2")
        if m["header"].get("min_engine_version") != [1, 26, 60]:
            err(f"{name} min_engine_version {m['header'].get('min_engine_version')} != [1, 26, 60]")
    deps = bp.get("dependencies", [])
    if not any(d.get("uuid") == rp["header"]["uuid"] for d in deps):
        err("BP manifest does not depend on the RP uuid")
    for d in deps:
        mod = d.get("module_name")
        if mod:
            if mod not in STABLE_MODULES:
                err(f"BP depends on non-whitelisted module {mod}")
            elif d["version"] != STABLE_MODULES[mod] or "beta" in str(d["version"]):
                err(f"{mod} version {d['version']} is not the stable {STABLE_MODULES[mod]}")
    scripts = [m for m in bp["modules"] if m["type"] == "script"]
    if len(scripts) != 1:
        err("BP must have exactly one script module")
    else:
        entry = os.path.join(BP, scripts[0]["entry"])
        if not os.path.exists(entry):
            err(f"script entry {scripts[0]['entry']} missing")
        else:
            js = open(entry, encoding="utf-8").read()
            imported = set(re.findall(r'from\s*"(@minecraft/[a-z-]+)"', js))
            declared = {d.get("module_name") for d in deps if d.get("module_name")}
            if imported - declared:
                err(f"script imports undeclared modules {sorted(imported - declared)}")
            INFO.append(f"script bundle {len(js) // 1024} KiB, imports {sorted(imported)}")
    uuids = [bp["header"]["uuid"], rp["header"]["uuid"]] + [m["uuid"] for m in bp["modules"] + rp["modules"]]
    if len(set(uuids)) != len(uuids):
        err("duplicate UUIDs across manifests")
    for path in glob.glob(f"{BP}/**/*.json", recursive=True) + glob.glob(f"{RP}/**/*.json", recursive=True):
        if "experiment" in open(path, encoding="utf-8").read().lower():
            err(f"{rel(path)} mentions experiments")


# ---------------------------------------------------------------------------------------- items
def check_items(lang_rp, item_textures):
    items = {}
    for path in glob.glob(f"{BP}/items/*.json"):
        d = load(path)["minecraft:item"]
        items[d["description"]["identifier"]] = d
    want = {"grimoire:pressure", "grimoire:ice", "grimoire:blood"}
    if set(items) != want:
        err(f"items {sorted(items)} != {sorted(want)}")
    for ident, d in items.items():
        comps = d.get("components", {})
        for bad in ("minecraft:food", "minecraft:consumable", "minecraft:durability", "minecraft:throwable", "minecraft:projectile"):
            if bad in comps:
                err(f"{ident} has {bad} (grimoires must not be edible/consumable)")
        if "minecraft:use_modifiers" not in comps:
            err(f"{ident} lacks minecraft:use_modifiers (needed for hold-to-prepare)")
        mss = comps.get("minecraft:max_stack_size")
        if (mss.get("value") if isinstance(mss, dict) else mss) not in (1, None):
            err(f"{ident} should not stack")
        icon = comps.get("minecraft:icon", {})
        tex = icon.get("textures", {}).get("default") if isinstance(icon, dict) else icon
        if tex not in item_textures:
            err(f"{ident} icon '{tex}' not in item_texture.json")
        key = f"item.{ident}"
        if not any(k.startswith(key) for k in lang_rp):
            err(f"lang missing {key}")
    # attachables
    att = {}
    for path in glob.glob(f"{RP}/attachables/*.json"):
        att[load(path)["minecraft:attachable"]["description"]["identifier"]] = path
    for ident in want:
        if ident not in att:
            err(f"no attachable for {ident}")
    return att


# ------------------------------------------------------------------------------------- geometry
def load_geometries():
    geos = {}
    for path in glob.glob(f"{RP}/models/**/*.json", recursive=True):
        for g in load(path).get("minecraft:geometry", []):
            ident = g["description"]["identifier"]
            if ident in geos:
                err(f"duplicate geometry {ident}")
            geos[ident] = (g, path)
    return geos


def check_geometry(ident, g, path):
    desc = g["description"]
    tw, th = desc.get("texture_width", 64), desc.get("texture_height", 64)
    names, cubes = set(), 0
    bones = g.get("bones", [])
    for b in bones:
        n = b["name"]
        if n in names:
            err(f"{ident}: duplicate bone {n}")
        names.add(n)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n):
            err(f"{ident}: bad bone name {n!r}")
    for b in bones:
        if b.get("parent") and b["parent"] not in names:
            err(f"{ident}: bone {b['name']} has missing parent {b['parent']}")
        for c in b.get("cubes", []):
            cubes += 1
            uv = c.get("uv", {})
            if isinstance(uv, dict):
                for face, f in uv.items():
                    u, v = f["uv"]
                    w, h = f.get("uv_size", [0, 0])
                    lo_u, hi_u = min(u, u + w), max(u, u + w)
                    lo_v, hi_v = min(v, v + h), max(v, v + h)
                    if lo_u < -0.01 or lo_v < -0.01 or hi_u > tw + 0.01 or hi_v > th + 0.01:
                        err(f"{ident}: bone {b['name']} {face} UV {f} outside {tw}x{th}")
    # parent cycles
    parent = {b["name"]: b.get("parent") for b in bones}
    for n in parent:
        seen, cur = set(), n
        while cur:
            if cur in seen:
                err(f"{ident}: bone cycle at {n}")
                break
            seen.add(cur)
            cur = parent.get(cur)
    return names, cubes, (tw, th)


# ----------------------------------------------------------------------------------- animations
def load_animations():
    anims, ctrls = {}, {}
    for path in glob.glob(f"{RP}/animations/**/*.json", recursive=True):
        for k, v in load(path).get("animations", {}).items():
            anims[k] = v
    for path in glob.glob(f"{RP}/animation_controllers/**/*.json", recursive=True):
        for k, v in load(path).get("animation_controllers", {}).items():
            ctrls[k] = v
    return anims, ctrls


def load_render_controllers():
    rcs = {}
    for path in glob.glob(f"{RP}/render_controllers/*.json"):
        rcs.update(load(path).get("render_controllers", {}))
    return rcs


def check_client(kind, ident, desc, path, geos, anims, ctrls, rcs, bone_sets, tex_sizes, cube_counts):
    # geometry
    gmap = desc.get("geometry", {})
    used_bones = set()
    gsizes = []
    for key, gid in gmap.items():
        if gid not in geos:
            err(f"{kind} {ident}: geometry {gid} missing")
            continue
        used_bones |= bone_sets[gid]
        gsizes.append(tex_sizes[gid])
        cube_counts[ident] = cube_counts.get(ident, 0) + 0  # placeholder for ordering
    # textures (+ aspect ratio vs geometry)
    for key, t in desc.get("textures", {}).items():
        f = png_exists(os.path.join(RP, t))
        if not f:
            err(f"{kind} {ident}: texture {t} missing")
            continue
        if key.startswith("flow") or key == "flow":
            continue
        w, h = Image.open(f).size
        for gw, gh in gsizes:
            if abs(w / h - gw / gh) > 1e-3 and key in ("default", "v0", "v1", "v2"):
                err(f"{kind} {ident}: texture {t} {w}x{h} aspect differs from geometry {gw}x{gh}")
    # materials
    for key, mat in desc.get("materials", {}).items():
        base = mat.split(":")[0]
        if base not in VANILLA_MATERIALS:
            warn(f"{kind} {ident}: non-vanilla material {mat}")
    # animations / controllers
    amap = desc.get("animations", {})
    for short, full in amap.items():
        if full in anims:
            for bone in anims[full].get("bones", {}):
                if used_bones and bone not in used_bones:
                    err(f"{kind} {ident}: animation {full} targets missing bone {bone}")
        elif full in ctrls:
            for st_name, st in ctrls[full]["states"].items():
                for a in st.get("animations", []):
                    a_name = a if isinstance(a, str) else list(a.keys())[0]
                    if a_name not in amap:
                        err(f"{kind} {ident}: controller {full} state {st_name} plays unknown '{a_name}'")
                for tr in st.get("transitions", []):
                    for target in tr:
                        if target not in ctrls[full]["states"]:
                            err(f"{kind} {ident}: controller {full} transitions to unknown state {target}")
        else:
            err(f"{kind} {ident}: animation/controller {full} not found")
    scripts = desc.get("scripts", {})
    for entry in scripts.get("animate", []):
        key = entry if isinstance(entry, str) else list(entry.keys())[0]
        if key not in amap:
            err(f"{kind} {ident}: scripts.animate '{key}' not in animations")
    # render controllers
    for rc in desc.get("render_controllers", []):
        name = rc if isinstance(rc, str) else list(rc.keys())[0]
        if name not in rcs:
            err(f"{kind} {ident}: render controller {name} missing")
            continue
        body = json.dumps(rcs[name])
        for ref in re.findall(r"Geometry\.([a-z0-9_]+)", body):
            if ref not in gmap and not ref.startswith("q"):
                err(f"{kind} {ident}: render controller {name} uses Geometry.{ref}")
        for ref in re.findall(r"Texture\.([a-z0-9_]+)", body):
            if ref not in desc.get("textures", {}):
                err(f"{kind} {ident}: render controller {name} uses Texture.{ref}")
        for ref in re.findall(r"Material\.([a-z0-9_]+)", body):
            if ref not in desc.get("materials", {}):
                err(f"{kind} {ident}: render controller {name} uses Material.{ref}")


# ------------------------------------------------------------------------------- script ids
def script_ids():
    text = ""
    for path in glob.glob(f"{SRC}/**/*.ts", recursive=True):
        text += open(path, encoding="utf-8").read() + "\n"
    ids = set(re.findall(r'["\'`](grimoire:[a-z0-9_]+)["\'`]', text))
    sounds = set(re.findall(r'["\'`](grimoire\.[a-z0-9_]+\.[a-z0-9_]+)["\'`]', text))
    for tmpl in re.findall(r"`grimoire\.\$\{[^}]+\}\.([a-z0-9_]+)`", text):
        for school in ("pressure", "ice", "blood"):
            sounds.add(f"grimoire.{school}.{tmpl}")
    particles_tmpl = re.findall(r"`grimoire:\$\{[^}]+\}_([a-z0-9_]+)`", text)
    for tmpl in particles_tmpl:
        for school in ("pressure", "ice", "blood"):
            ids.add(f"grimoire:{school}_{tmpl}")
    fogs = set(re.findall(r"fog @s push (grimoire:[a-z0-9_]+)", text))
    fogs |= {i for i in re.findall(r'["\'](grimoire:(?:whiteout|whiteout_caster))["\']', text)}
    anims = set(re.findall(r'["\'](animation\.grimoire\.[a-z0-9_.]+)["\']', text))
    return ids, sounds, fogs, anims, text


def main():
    if not os.path.isdir(BP) or not os.path.isdir(RP):
        print("packs/ missing - run python3 tools/build.py first")
        return 2
    check_json()
    check_manifests()
    lang_rp = {ln.split("=", 1)[0] for ln in open(f"{RP}/texts/en_US.lang", encoding="utf-8") if "=" in ln}
    item_textures = load(f"{RP}/textures/item_texture.json")["texture_data"]
    for k, v in item_textures.items():
        t = v["textures"] if isinstance(v["textures"], str) else v["textures"][0]
        if not png_exists(os.path.join(RP, t)):
            err(f"item texture {k} -> {t} missing")
    attachables = check_items(lang_rp, item_textures)

    # spells vs specification
    meta = load(os.path.join(ROOT, ".build_meta.json"))
    spells = {s["code"]: s for s in meta["spells"]}
    if set(spells) != set(SPEC):
        err(f"spell codes differ from spec: missing {sorted(set(SPEC) - set(spells))}, extra {sorted(set(spells) - set(SPEC))}")
    for code, (name, cd) in SPEC.items():
        s = spells.get(code)
        if not s:
            continue
        if s["name"] != name:
            err(f"{code} name '{s['name']}' != spec '{name}'")
        if s["cooldown"] != cd:
            err(f"{code} cooldown {s['cooldown']} != spec {cd}")
        if s["cooldownAfterEnd"] != (code == "I11"):
            err(f"{code} cooldownAfterEnd={s['cooldownAfterEnd']} (only I11 may start its cooldown after the effect)")
    for school in ("pressure", "ice", "blood"):
        n = sum(1 for s in spells.values() if s["school"] == school)
        if n != 15:
            err(f"{school} has {n} spells, expected 15")
    if len({s["id"] for s in spells.values()}) != len(spells):
        err("duplicate spell ids")
    INFO.append(f"{len(spells)} spells match the specification table")

    # geometry / entities
    geos = load_geometries()
    anims, ctrls = load_animations()
    rcs = load_render_controllers()
    bone_sets, tex_sizes, cubes = {}, {}, {}
    for gid, (g, path) in geos.items():
        names, n, size = check_geometry(gid, g, path)
        bone_sets[gid], tex_sizes[gid], cubes[gid] = names, size, n
    client = {}
    for path in glob.glob(f"{RP}/entity/**/*.json", recursive=True):
        desc = load(path)["minecraft:client_entity"]["description"]
        client[desc["identifier"]] = desc
        check_client("entity", desc["identifier"], desc, path, geos, anims, ctrls, rcs, bone_sets, tex_sizes, {})
    for ident, path in attachables.items():
        desc = load(path)["minecraft:attachable"]["description"]
        check_client("attachable", ident, desc, path, geos, anims, ctrls, rcs, bone_sets, tex_sizes, {})
    server = {}
    for path in glob.glob(f"{BP}/entities/**/*.json", recursive=True):
        d = load(path)["minecraft:entity"]
        server[d["description"]["identifier"]] = d
    for ident in server:
        if ident not in client:
            err(f"BP entity {ident} has no client entity")
    for ident in client:
        if ident not in server:
            err(f"client entity {ident} has no BP entity")

    # particles
    particles = {}
    for path in glob.glob(f"{RP}/particles/**/*.json", recursive=True):
        d = load(path)["particle_effect"]
        pid = d["description"]["identifier"]
        particles[pid] = d
        tex = d["description"]["basic_render_parameters"]["texture"]
        if not png_exists(os.path.join(RP, tex)):
            err(f"particle {pid} texture {tex} missing")
    # sounds
    sdefs = load(f"{RP}/sounds/sound_definitions.json")["sound_definitions"]
    for sid, sd in sdefs.items():
        for snd in sd["sounds"]:
            name = snd["name"] if isinstance(snd, dict) else snd
            if not any(os.path.exists(os.path.join(RP, name + ext)) for ext in (".ogg", ".wav", ".fsb")):
                err(f"sound {sid} file {name} missing")
    # fogs / blocks
    fogs = {load(p)["minecraft:fog_settings"]["description"]["identifier"] for p in glob.glob(f"{RP}/fogs/*.json")}
    blocks = {load(p)["minecraft:block"]["description"]["identifier"] for p in glob.glob(f"{BP}/blocks/*.json")}
    terrain = load(f"{RP}/textures/terrain_texture.json")["texture_data"]
    for k, v in terrain.items():
        t = v["textures"] if isinstance(v["textures"], str) else v["textures"][0]
        t = t if isinstance(t, str) else t.get("path")
        if not png_exists(os.path.join(RP, t)):
            err(f"terrain texture {k} -> {t} missing")
    for path in glob.glob(f"{BP}/blocks/*.json"):
        d = load(path)["minecraft:block"]
        for inst in d.get("components", {}).get("minecraft:material_instances", {}).values():
            if inst.get("texture") not in terrain:
                err(f"block {d['description']['identifier']} texture {inst.get('texture')} not in terrain_texture.json")
    for b in blocks:
        if not any(k.startswith(f"tile.{b}") for k in lang_rp):
            warn(f"lang missing tile.{b}.name")

    # cross-reference script ids
    ids, sounds, fog_ids, anim_ids, text = script_ids()
    known_props = set()
    for d in list(server.values()):
        known_props |= set(d["description"].get("properties", {}))
    resolved = {"constructs": 0, "particles": 0, "sounds": 0, "fogs": 0}
    non_asset = {"grimoire:pressure", "grimoire:ice", "grimoire:blood", "grimoire:temporary", "grimoire:rules",
                 "grimoire:state", "grimoire:session", "grimoire:owner", "grimoire:phase", "grimoire:act", "grimoire:book",
                 "grimoire:debug_reply", "grimoire:debug", "grimoire:config", "grimoire:getbook", "grimoire:guide",
                 "grimoire:resetcooldowns", "grimoire:charge", "grimoire:release", "grimoire:aux"}
    for i in sorted(ids):
        if i.startswith("grimoire:fx_") or i in server:
            if i not in server:
                err(f"script uses entity {i} which is not generated")
            resolved["constructs"] += 1
        elif i in particles:
            resolved["particles"] += 1
        elif i in fogs or i in blocks or i in non_asset or i in known_props:
            if i in fogs:
                resolved["fogs"] += 1
        elif re.fullmatch(r"grimoire:[a-z]+_(charge|release)", i):
            if i not in particles:
                err(f"particle {i} (from template) missing")
        else:
            warn(f"unclassified script id {i}")
    for s in sorted(sounds):
        if s not in sdefs:
            err(f"script uses sound {s} which is not defined")
        else:
            resolved["sounds"] += 1
    for pid in sorted(particles):
        if pid not in ids:
            warn(f"particle {pid} is generated but never spawned by scripts")
    for sid in sorted(sdefs):
        if sid not in sounds:
            warn(f"sound {sid} is defined but never played by scripts")
    for f in sorted(fog_ids):
        if f not in fogs:
            err(f"script pushes fog {f} which is not defined")
    for a in sorted(anim_ids):
        if a not in anims and a not in ctrls:
            err(f"script plays animation {a} which is not defined")
    # every generated construct is used by some script (dead assets)
    for ident in server:
        if ident not in ids and not re.search(re.escape(ident.split(":")[1]), text):
            warn(f"entity {ident} is generated but never referenced by scripts")
    INFO.append("script ids resolved: " + ", ".join(f"{k} {v}" for k, v in resolved.items()) + f", animations {len(anim_ids)}")

    # mcaddon
    dist = os.path.join(ROOT, "dist", "Grimoire_Imperial_Magic.mcaddon")
    if not os.path.exists(dist):
        err("dist/Grimoire_Imperial_Magic.mcaddon missing")
    else:
        with zipfile.ZipFile(dist) as z:
            names = z.namelist()
            for pack in ("Grimoire_BP/manifest.json", "Grimoire_RP/manifest.json"):
                if not any(n.endswith(pack) and n.count("/") == 1 for n in names):
                    err(f".mcaddon lacks top-level {pack}")
            INFO.append(f".mcaddon: {len(names)} entries, {os.path.getsize(dist) // 1024} KiB")

    heavy = sorted(cubes.items(), key=lambda kv: -kv[1])[:5]
    INFO.append("largest models (cubes): " + ", ".join(f"{k.split('.')[-1]} {v}" for k, v in heavy))
    INFO.append(f"{len(geos)} geometries, {len(anims)} animations, {len(ctrls)} controllers, {len(particles)} particles, "
                f"{len(sdefs)} sounds, {len(fogs)} fogs, {len(blocks)} blocks")

    for m in INFO:
        print("INFO   ", m)
    for m in WARNINGS:
        print("WARNING", m)
    for m in ERRORS:
        print("ERROR  ", m)
    print(f"\nvalidate: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
