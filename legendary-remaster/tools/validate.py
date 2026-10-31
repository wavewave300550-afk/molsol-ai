"""
Static validation of the built packs (build/Legends_BP, build/Legends_RP).

Checks: JSON parses; manifests and dependency UUIDs; every BP entity has a client entity and vice
versa; client entities reference existing geometry ids, textures, animations, controllers and render
controllers; animation controllers reference animations declared by their entity; render
controllers only show bones that exist in the geometry; act controllers cover every act of
generated/data.js; texture sizes are sane; every sound/particle id string used by the scripts
exists in the vanilla reference or the pack; lang names for every entity and item.
"""
import json
import os
import re
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "build", "Legends_BP")
RP = os.path.join(ROOT, "build", "Legends_RP")
REF = json.load(open(os.path.join(ROOT, "tools", "vanilla", "reference.json")))
errors, notes = [], []


def err(m):
    errors.append(m)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:                              # noqa: BLE001
        err(f"JSON error {os.path.relpath(path, ROOT)}: {e}")
        return None


def walk(d, ext):
    for dp, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(ext):
                yield os.path.join(dp, f)


# ------------------------------------------------------------------ JSON + manifests
jsons = {p: load(p) for p in list(walk(BP, ".json")) + list(walk(RP, ".json"))}
bpm, rpm = jsons[os.path.join(BP, "manifest.json")], jsons[os.path.join(RP, "manifest.json")]
deps = [d.get("uuid") for d in bpm.get("dependencies", []) if "uuid" in d]
if rpm["header"]["uuid"] not in deps:
    err("BP manifest does not depend on the RP")
mods = {d.get("module_name"): d.get("version") for d in bpm.get("dependencies", []) if "module_name" in d}
notes.append(f"script modules: {mods}")
if bpm["header"]["version"] != rpm["header"]["version"]:
    err("BP/RP versions differ")

# ------------------------------------------------------------------ geometry index
geos = {}
for p in walk(os.path.join(RP, "models"), ".json"):
    d = jsons[p]
    for g in d.get("minecraft:geometry", []):
        bones = {b["name"] for b in g.get("bones", [])}
        geos[g["description"]["identifier"]] = {"bones": bones, "tw": g["description"]["texture_width"], "th": g["description"]["texture_height"]}
        for b in g.get("bones", []):
            if b.get("parent") and b["parent"] not in bones:
                err(f"{g['description']['identifier']}: bone {b['name']} has unknown parent {b['parent']}")
            for c in b.get("cubes", []):
                for face, uv in c.get("uv", {}).items():
                    u, v = uv["uv"]
                    w, h = uv["uv_size"]
                    if min(u, u + w) < 0 or min(v, v + h) < 0 or max(u, u + w) > g["description"]["texture_width"] + 1e-6 or max(v, v + h) > g["description"]["texture_height"] + 1e-6:
                        err(f"{g['description']['identifier']}: UV out of atlas in {b['name']}")

# ------------------------------------------------------------------ animations / controllers / render controllers
anims = {}
for p in walk(os.path.join(RP, "animations"), ".json"):
    for k, v in jsons[p].get("animations", {}).items():
        anims[k] = v
ctrls = {}
for p in walk(os.path.join(RP, "animation_controllers"), ".json"):
    for k, v in jsons[p].get("animation_controllers", {}).items():
        ctrls[k] = v
rcs = {}
for p in walk(os.path.join(RP, "render_controllers"), ".json"):
    for k, v in jsons[p].get("render_controllers", {}).items():
        rcs[k] = v

client = {}
for p in walk(os.path.join(RP, "entity"), ".json"):
    desc = jsons[p]["minecraft:client_entity"]["description"]
    client[desc["identifier"]] = desc
    ident = desc["identifier"]
    for gk, gid in desc.get("geometry", {}).items():
        if gid not in geos:
            err(f"{ident}: geometry {gid} missing")
    for tk, tpath in desc.get("textures", {}).items():
        f = os.path.join(RP, tpath + ".png")
        if not os.path.exists(f):
            err(f"{ident}: texture {tpath} missing")
        else:
            im = Image.open(f)
            gid = desc["geometry"].get("default")
            if gid in geos:
                g = geos[gid]
                if abs(im.size[0] / g["tw"] - im.size[1] / g["th"]) > 1e-6:
                    err(f"{ident}: texture {tpath} aspect does not match the atlas")
            if max(im.size) > 2048:
                err(f"{ident}: texture {tpath} too large {im.size}")
    for ak, aid in desc.get("animations", {}).items():
        if aid.startswith("controller."):
            if aid not in ctrls:
                err(f"{ident}: controller {aid} missing")
            else:
                for st in ctrls[aid]["states"].values():
                    for an in st.get("animations", []):
                        name = an if isinstance(an, str) else list(an.keys())[0]
                        if name not in desc["animations"]:
                            err(f"{ident}: controller uses undeclared animation {name}")
        elif aid not in anims:
            err(f"{ident}: animation {aid} missing")
    bones = set()
    for gid in desc.get("geometry", {}).values():
        bones |= geos.get(gid, {}).get("bones", set())
    for aid in desc.get("animations", {}).values():
        a = anims.get(aid)
        if a:
            for b in a.get("bones", {}):
                if b not in bones:
                    err(f"{ident}: animation {aid} drives unknown bone {b}")
    for item in desc.get("scripts", {}).get("animate", []):
        name = item if isinstance(item, str) else list(item.keys())[0]
        if name not in desc.get("animations", {}):
            err(f"{ident}: animate refers to undeclared {name}")
    for rc in desc.get("render_controllers", []):
        name = rc if isinstance(rc, str) else list(rc.keys())[0]
        if name not in rcs:
            err(f"{ident}: render controller {name} missing")
            continue
        r = rcs[name]
        gkey = r["geometry"].split(".")[-1]
        if gkey not in desc["geometry"]:
            err(f"{ident}: render controller {name} uses geometry '{gkey}' not declared")
        for pv in r.get("part_visibility", []):
            for b in pv:
                if b != "*" and b not in bones:
                    err(f"{ident}: render controller {name} toggles unknown bone {b}")
        for m in r.get("materials", []):
            for mk in m.values():
                if mk.split(".")[-1] not in desc["materials"]:
                    err(f"{ident}: material {mk} not declared")

bp_entities = {}
for p in walk(os.path.join(BP, "entities"), ".json"):
    e = jsons[p]["minecraft:entity"]
    bp_entities[e["description"]["identifier"]] = e
for ident in bp_entities:
    if ident not in client:
        err(f"{ident}: no client entity")
for ident in client:
    if ident not in bp_entities:
        err(f"{ident}: client entity without behaviour entity")

# ------------------------------------------------------------------ acts vs controllers
data = open(os.path.join(BP, "scripts", "generated", "data.js"), encoding="utf-8").read()
for name, body in re.findall(r"export const (\w+)_ACTS = (\{.*?\});", data):
    acts = json.loads(body)
    key = name.lower()
    cid = f"controller.animation.legends.{key}.act"
    if cid not in ctrls:
        err(f"{key}: act controller missing")
        continue
    states = ctrls[cid]["states"]
    prop_max = bp_entities[f"legends:{key}"]["description"]["properties"]["legends:act"]["range"][1]
    for an, v in acts.items():
        if an not in states:
            err(f"{key}: act {an} has no controller state")
        if v["id"] > prop_max:
            err(f"{key}: act id {v['id']} exceeds legends:act range {prop_max}")
        a = anims.get(f"animation.legends.{key}.act.{an}")
        if a and abs(a["animation_length"] - v["ticks"] / 20) > 1e-3:
            err(f"{key}: act {an} length {a['animation_length']} != {v['ticks']} ticks")
        if any(m > v["ticks"] for m in v["marks"]):
            err(f"{key}: act {an} mark beyond its length")

# ------------------------------------------------------------------ script ids
pack_particles = {jsons[p]["particle_effect"]["description"]["identifier"] for p in walk(os.path.join(RP, "particles"), ".json")}
sounds = set(REF["sounds"])
src = "".join(open(p, encoding="utf-8").read() for p in walk(os.path.join(BP, "scripts"), ".js"))
for sid in set(re.findall(r'sound\(this\.dim, "([^"]+)"', src)) | set(re.findall(r'sound\(dim, "([^"]+)"', src)):
    if sid not in sounds:
        err(f"script sound {sid} is not a vanilla sound")
for pid in set(re.findall(r'"(legends:[a-z_]+)"', src)):
    if pid.startswith("legends:") and pid not in bp_entities and pid not in pack_particles and not re.match(r"legends:(act|phase|var|fly|fx|move|home|owner|codex_given|boss|summon|codex|phase|clear|sigils|form_\w+|sigil_\w+|core_\w+)$", pid):
        notes.append(f"unmatched id string in scripts: {pid}")
for ent in re.findall(r'spawnProp\([^,]+, "([a-z_]+)"', src):
    if f"legends:{ent}" not in bp_entities:
        err(f"script spawns unknown prop {ent}")

# ------------------------------------------------------------------ lang
lang = open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8").read()
for ident in bp_entities:
    if f"entity.{ident}.name=" not in lang:
        err(f"lang: no name for {ident}")
for p in walk(os.path.join(BP, "items"), ".json"):
    iid = jsons[p]["minecraft:item"]["description"]["identifier"]
    if f"item.{iid}.name=" not in lang:
        err(f"lang: no name for item {iid}")

print(f"{len(jsons)} JSON files, {len(geos)} geometries, {len(anims)} animations, {len(ctrls)} controllers, {len(rcs)} render controllers, "
      f"{len(client)} client entities, {len(bp_entities)} entities")
for n in notes:
    print("note:", n)
for e in errors:
    print("ERROR:", e)
print("OK" if not errors else f"{len(errors)} error(s)")
sys.exit(1 if errors else 0)
