"""
Deep cross-reference validation of the built packs (build/packs/BP, build/packs/RP).
Complements Minecraft Creator Tools' schema validation with checks that span
files: geometry <-> animations <-> controllers <-> client entities <-> scripts,
block palette ids/states against vanilla 1.26.60, sound/particle/fog ids.

usage: python3 tools/validate.py    (exit code 1 on any error)
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BP = os.path.join(ROOT, "build", "packs", "BP")
RP = os.path.join(ROOT, "build", "packs", "RP")
errors: list[str] = []
checks = 0


def err(msg: str) -> None:
    errors.append(msg)


def ok() -> None:
    global checks
    checks += 1


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


# ----------------------------------------------------------------------------- load everything
vanilla = load(os.path.join(ROOT, "tools", "vanilla", "reference.json"))
vblocks = load(os.path.join(ROOT, "tools", "vanilla", "blocks.json"))
bp_manifest = load(os.path.join(BP, "manifest.json"))
rp_manifest = load(os.path.join(RP, "manifest.json"))

geos: dict[str, dict] = {}
for f in glob.glob(os.path.join(RP, "models", "entity", "*.json")):
    for g in load(f)["minecraft:geometry"]:
        geos[g["description"]["identifier"]] = {"file": f, "geo": g}
anims: dict[str, dict] = {}
for f in glob.glob(os.path.join(RP, "animations", "*.json")):
    for k, v in load(f)["animations"].items():
        anims[k] = v
controllers: dict[str, dict] = {}
for f in glob.glob(os.path.join(RP, "animation_controllers", "*.json")):
    controllers.update(load(f)["animation_controllers"])
render_ctrls: dict[str, dict] = {}
for f in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
    render_ctrls.update(load(f)["render_controllers"])
particles = {load(f)["particle_effect"]["description"]["identifier"]: load(f) for f in glob.glob(os.path.join(RP, "particles", "*.json"))}
sound_defs = load(os.path.join(RP, "sounds", "sound_definitions.json"))["sound_definitions"]
client_entities = {load(f)["minecraft:client_entity"]["description"]["identifier"]: load(f)["minecraft:client_entity"]["description"] for f in glob.glob(os.path.join(RP, "entity", "*.json"))}
bp_entities = {load(f)["minecraft:entity"]["description"]["identifier"]: load(f)["minecraft:entity"] for f in glob.glob(os.path.join(BP, "entities", "**", "*.json"), recursive=True)}
bp_items = {load(f)["minecraft:item"]["description"]["identifier"]: load(f)["minecraft:item"] for f in glob.glob(os.path.join(BP, "items", "*.json"))}
fogs = {load(f)["minecraft:fog_settings"]["description"]["identifier"] for f in glob.glob(os.path.join(RP, "fogs", "*.json"))}
item_tex = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
lang = dict(line.split("=", 1) for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8").read().splitlines() if "=" in line)

# ----------------------------------------------------------------------------- manifests
uuids = [bp_manifest["header"]["uuid"], rp_manifest["header"]["uuid"]] + [m["uuid"] for m in bp_manifest["modules"] + rp_manifest["modules"]]
if len(set(uuids)) != len(uuids):
    err("manifest: duplicate UUIDs")
ok()
dep_uuids = [d["uuid"] for d in bp_manifest["dependencies"] if "uuid" in d]
if rp_manifest["header"]["uuid"] not in dep_uuids:
    err("manifest: BP does not depend on RP")
ok()
script = next(m for m in bp_manifest["modules"] if m["type"] == "script")
if not os.path.exists(os.path.join(BP, script["entry"])):
    err(f"manifest: script entry {script['entry']} missing")
ok()

# ----------------------------------------------------------------------------- geometry
for gid, info in geos.items():
    g = info["geo"]
    d = g["description"]
    tw, th = d["texture_width"], d["texture_height"]
    names = set()
    for b in g["bones"]:
        if b["name"] in names:
            err(f"{gid}: duplicate bone {b['name']}")
        names.add(b["name"])
        if b.get("parent") and b["parent"] not in {x["name"] for x in g["bones"]}:
            err(f"{gid}: bone {b['name']} parent {b['parent']} missing")
        for c in b.get("cubes", []):
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                if u < 0 or v < 0 or u + w > tw or v + h > th:
                    err(f"{gid}: bone {b['name']} {face} uv out of bounds")
                ok()
    info["bones"] = names
    info["locators"] = {k for b in g["bones"] for k in b.get("locators", {})}

# ----------------------------------------------------------------------------- client entities
for ident, ce in client_entities.items():
    if ident not in bp_entities:
        err(f"client entity {ident} has no behaviour entity")
    ok()
    for key, tex in ce["textures"].items():
        p = os.path.join(RP, tex + ".png")
        if not os.path.exists(p):
            err(f"{ident}: texture {tex} missing")
        else:
            w, h = Image.open(p).size
            for gk, gid in ce["geometry"].items():
                gd = geos.get(gid)
                if gd and (gk == key or (key == "default" and gk == "default")):
                    d = gd["geo"]["description"]
                    if (d["texture_width"], d["texture_height"]) != (w, h):
                        err(f"{ident}: texture {tex} is {w}x{h} but {gid} expects {d['texture_width']}x{d['texture_height']}")
            if w & (w - 1) or h & (h - 1):
                err(f"{ident}: texture {tex} not power of two")
        ok()
    for gid in ce["geometry"].values():
        if gid not in geos:
            err(f"{ident}: geometry {gid} missing")
        ok()
    for rc in ce["render_controllers"]:
        name = rc if isinstance(rc, str) else list(rc)[0]
        if name not in render_ctrls:
            err(f"{ident}: render controller {name} missing")
        ok()
    bones = set().union(*(geos[g]["bones"] for g in ce["geometry"].values() if g in geos))
    locs = set().union(*(geos[g]["locators"] for g in ce["geometry"].values() if g in geos))
    pfx = ce.get("particle_effects", {})
    sfx = ce.get("sound_effects", {})
    for pid in pfx.values():
        if pid not in particles and pid.replace("minecraft:", "") not in vanilla["particles"]:
            err(f"{ident}: particle {pid} missing")
        ok()
    for sid in sfx.values():
        if sid not in sound_defs:
            err(f"{ident}: sound effect {sid} missing")
        ok()
    for short, full in ce["animations"].items():
        if full.startswith("controller."):
            c = controllers.get(full)
            if not c:
                err(f"{ident}: controller {full} missing")
                continue
            states = c["states"]
            if c.get("initial_state", "default") not in states:
                err(f"{full}: initial state missing")
            for sname, st in states.items():
                for a in st.get("animations", []):
                    an = a if isinstance(a, str) else list(a)[0]
                    if an not in ce["animations"]:
                        err(f"{full}.{sname}: animation '{an}' not declared by {ident}")
                    ok()
                for t in st.get("transitions", []):
                    tgt = list(t)[0]
                    if tgt not in states:
                        err(f"{full}.{sname}: transition to unknown state {tgt}")
                    ok()
            continue
        a = anims.get(full)
        if not a:
            err(f"{ident}: animation {full} missing")
            continue
        for bone in a.get("bones", {}):
            if bone not in bones:
                err(f"{full}: animates bone '{bone}' missing from {ident} geometry")
            ok()
        for t, ev in a.get("particle_effects", {}).items():
            for e in ev if isinstance(ev, list) else [ev]:
                if e["effect"] not in pfx:
                    err(f"{full}: particle effect key '{e['effect']}' not declared in {ident}")
                if e.get("locator") and e["locator"] not in locs:
                    err(f"{full}: locator '{e['locator']}' missing in {ident} geometry")
                ok()
        for t, ev in a.get("sound_effects", {}).items():
            for e in ev if isinstance(ev, list) else [ev]:
                if e["effect"] not in sfx:
                    err(f"{full}: sound effect key '{e['effect']}' not declared in {ident}")
                ok()
    for a in ce["scripts"].get("animate", []):
        an = a if isinstance(a, str) else list(a)[0]
        if an not in ce["animations"]:
            err(f"{ident}: animate entry '{an}' not declared")
        ok()

# ----------------------------------------------------------------------------- behaviour entities
known_components = set(vanilla["entity_components"])
for ident, e in bp_entities.items():
    for comp in e.get("components", {}):
        if comp not in known_components:
            err(f"{ident}: unknown component {comp}")
        ok()
    if f"entity.{ident}.name" not in lang:
        err(f"{ident}: missing lang name")
    ok()

# ----------------------------------------------------------------------------- sounds
for sid, d in sound_defs.items():
    for s in d["sounds"]:
        name = s["name"] if isinstance(s, dict) else s
        if not os.path.exists(os.path.join(RP, name + ".ogg")):
            err(f"sound {sid}: file {name}.ogg missing")
        ok()

# ----------------------------------------------------------------------------- items
for ident, it in bp_items.items():
    icon = it["components"]["minecraft:icon"]["textures"]["default"]
    if icon not in item_tex:
        err(f"{ident}: icon {icon} not in item_texture.json")
    else:
        t = item_tex[icon]["textures"]
        t = t[0] if isinstance(t, list) else t
        if not os.path.exists(os.path.join(RP, t + ".png")):
            err(f"{ident}: icon file {t}.png missing")
    if f"item.{ident}.name" not in lang:
        err(f"{ident}: missing lang name")
    ok()

# ----------------------------------------------------------------------------- block palette (scripts)
pal_src = open(os.path.join(ROOT, "src", "gen", "palette.ts"), encoding="utf-8").read()
for m in re.finditer(r'pal\("(minecraft:[a-z0-9_]+)"(?:, (\{[^}]*\}))?\)', pal_src):
    bid, st = m.group(1), m.group(2)
    if bid not in vblocks["blocks"]:
        err(f"palette: unknown block {bid}")
        continue
    allowed = vblocks["blocks"][bid]
    if st:
        for name, val in re.findall(r'"?([a-z_:]+)"?: ("[^"]*"|true|false|-?\d+)', st):
            if name not in allowed:
                err(f"palette: {bid} has no state '{name}' (allowed: {allowed})")
                continue
            t = vblocks["state_types"].get(name)
            vt = "string" if val.startswith('"') else "boolean" if val in ("true", "false") else "number"
            if t and t != vt:
                err(f"palette: {bid} state {name} expects {t}, got {vt}")
            ok()
    ok()

# ----------------------------------------------------------------------------- script string references
js = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True) if not f.endswith("mm_data.js"))
for sid in set(re.findall(r'"(anatomy\.(?:mm|music)\.[a-z0-9_]+)"', js)):
    if sid not in sound_defs:
        err(f"scripts: sound id {sid} not defined")
    ok()
for ident in set(re.findall(r'"(anatomy:mm_[a-z_]+)"', js)):
    if ident not in bp_entities and ident not in particles:
        err(f"scripts: id {ident} is neither an entity nor a particle")
    ok()
for an in set(re.findall(r'"(animation\.anatomy\.[a-z0-9_.]+)"', js)):
    if an not in anims:
        err(f"scripts: animation {an} not defined")
    ok()
for fog in set(re.findall(r'"(anatomy:migration_mist)"', js)):
    if fog not in fogs:
        err(f"scripts: fog {fog} not defined")
    ok()
props = {p for e in bp_entities.values() for p in e["description"].get("properties", {})}
for p in set(re.findall(r'"(anatomy:(?:leg_index|pose|hanging|charging|dying|open|phase|petal_state|petal_index|variant|flip))"', js)):
    if p not in props:
        err(f"scripts: property {p} not declared on any entity")
    ok()
for item in set(re.findall(r'"(anatomy:(?:anatomical_atlas|restless_lodestone|lithic_heart_shard))"', js)):
    if item not in bp_items:
        err(f"scripts: item {item} missing")
    ok()
dim_ids = {load(f)["minecraft:dimension"]["description"]["identifier"] for f in glob.glob(os.path.join(BP, "dimensions", "*.json"))}
for d in set(re.findall(r'"(anatomy:migration_path)"', js)):
    if d not in dim_ids:
        err(f"scripts: dimension {d} not defined")
    ok()

print(f"validate: {checks} checks, {len(errors)} error(s)")
for e in errors:
    print("  ERROR", e)
sys.exit(1 if errors else 0)
