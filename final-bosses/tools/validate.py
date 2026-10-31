"""
Static validation of the built packs (run after build.py):  python3 tools/validate.py

JSON syntax, manifests, every cross reference (geometry <-> client entity <-> render controller <->
texture <-> animation <-> animation controller), model integrity (UV bounds, bone hierarchy,
solid/glow skeleton parity, animated bones exist), particles, items, language, and every
identifier the scripts use (particles, sounds, effects, entities, items) against the packs or the
vanilla reference index extracted from Mojang/bedrock-samples (tools/vanilla/reference.json).
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "FinalBosses_BP")
RP = os.path.join(ROOT, "build", "FinalBosses_RP")
REF = json.load(open(os.path.join(HERE, "vanilla", "reference.json")))

errors = []
count = [0]


def check(cond, msg):
    count[0] += 1
    if not cond:
        errors.append(msg)
    return cond


def load_all(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        try:
            out[p] = json.load(open(p, encoding="utf-8"))
            check(True, "")
        except Exception as e:  # noqa: BLE001
            check(False, f"invalid JSON {p}: {e}")
    return {k: v for k, v in out.items() if isinstance(v, dict)}


bp_json, rp_json = load_all(BP), load_all(RP)

# ---------------------------------------------------------------- manifests
bpm, rpm = bp_json[os.path.join(BP, "manifest.json")], rp_json[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs not unique")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
for pkg, key in (("server", "@minecraft/server"), ("server-ui", "@minecraft/server-ui")):
    ver = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", pkg, "package.json")))["version"]
    check(deps.get(key) == ver, f"manifest {key} {deps.get(key)} != typings {ver}")
script = [m for m in bpm["modules"] if m["type"] == "script"][0]
check(os.path.exists(os.path.join(BP, script["entry"])), "script entry missing")

# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rp_json.items():
    for g in d.get("minecraft:geometry", []):
        geos[g["description"]["identifier"]] = g
check(len(geos) == 10, f"expected 10 geometries (5 bosses x solid/glow), got {len(geos)}")
for gid, g in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bones")
    parents = {b["name"]: b.get("parent") for b in g["bones"]}
    for b in g["bones"]:
        if b.get("parent"):
            check(b["parent"] in names, f"{gid}: {b['name']} unknown parent")
        for c in b.get("cubes", []):
            check(all(x >= 0 for x in c["size"]), f"{gid}: negative size")
            check(c["uv"], f"{gid}: cube without faces")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                check(0 <= min(u, u + w) and max(u, u + w) <= W and 0 <= min(v, v + h) and max(v, v + h) <= H, f"{gid}: uv out of bounds")
            for k in ("pivot", "rotation", "origin", "size"):
                if k in c:
                    check(all(isinstance(x, (int, float)) and abs(x) < 1000 for x in c[k]), f"{gid}: bad {k}")
    for n in names:
        seen, cur = set(), n
        while cur:
            if not check(cur not in seen, f"{gid}: bone cycle"):
                break
            seen.add(cur)
            cur = parents.get(cur)
for gid in list(geos):
    if gid.endswith(".glow"):
        solid = geos.get(gid[:-5])
        check(solid is not None, f"{gid}: missing solid twin")
        if solid:
            check([b["name"] for b in solid["bones"]] == [b["name"] for b in geos[gid]["bones"]], f"{gid}: skeleton differs from solid layer")
            check(solid["description"]["texture_width"] == geos[gid]["description"]["texture_width"], f"{gid}: atlas size differs")
            n_glow = sum(len(b.get("cubes", [])) for b in geos[gid]["bones"])
            check(n_glow > 0, f"{gid}: energy layer is empty")

# ---------------------------------------------------------------- animations, controllers, render controllers
anims, ctrls, rcs = {}, {}, {}
for p, d in rp_json.items():
    if p.endswith(".animation.json"):
        anims.update(d["animations"])
    if "animation_controllers" in d:
        ctrls.update(d["animation_controllers"])
    if "render_controllers" in d:
        rcs.update(d["render_controllers"])


def molang_ok(expr):
    if not isinstance(expr, str):
        return True
    depth = 0
    for ch in expr:
        depth += (ch == "(") - (ch == ")")
        if depth < 0:
            return False
    return depth == 0 and not re.search(r"[^=!<>]=[^=]", expr.replace("==", "").replace("!=", "").replace("<=", "").replace(">=", "")) or expr.strip().endswith(";")


for name, a in anims.items():
    for bone, chans in a["bones"].items():
        for ch, vals in chans.items():
            check(ch in ("rotation", "position", "scale"), f"{name}: channel {ch}")
            for val in vals if isinstance(vals, list) else [vals]:
                check(molang_ok(val), f"{name}/{bone}: bad molang {val}")

for name, c in ctrls.items():
    states = c["states"]
    check(c["initial_state"] in states, f"{name}: bad initial state")
    for sname, st in states.items():
        for tr in st.get("transitions", []):
            (to, cond), = tr.items()
            check(to in states, f"{name}/{sname}: transition to unknown {to}")
            check(molang_ok(cond), f"{name}/{sname}: bad condition")

client_ids = set()
for p, d in rp_json.items():
    ce = d.get("minecraft:client_entity")
    if not ce:
        continue
    desc = ce["description"]
    ident = desc["identifier"]
    client_ids.add(ident)
    bones = set()
    for key, gid in desc["geometry"].items():
        check(gid in geos, f"{ident}: geometry {gid} missing")
        bones |= {b["name"] for b in geos.get(gid, {"bones": []})["bones"]}
    for key, tex in desc["textures"].items():
        check(os.path.exists(os.path.join(RP, tex + ".png")), f"{ident}: texture {tex} missing")
    for key, aname in desc["animations"].items():
        if aname.startswith("controller."):
            check(aname in ctrls, f"{ident}: controller {aname} missing")
            for st in ctrls.get(aname, {"states": {}})["states"].values():
                for an in st.get("animations", []):
                    short = an if isinstance(an, str) else list(an)[0]
                    check(short in desc["animations"], f"{ident}: controller uses unknown short name {short}")
        else:
            check(aname in anims, f"{ident}: animation {aname} missing")
            for b in anims.get(aname, {"bones": {}})["bones"]:
                check(b in bones, f"{ident}: animated bone {b} not in geometry ({aname})")
    for entry in desc["scripts"]["animate"]:
        short = entry if isinstance(entry, str) else list(entry)[0]
        check(short in desc["animations"], f"{ident}: animate {short} unknown")
    for line in desc["scripts"].get("pre_animation", []):
        check(molang_ok(line), f"{ident}: pre_animation {line}")
    for rc_name in desc["render_controllers"]:
        rc_name = rc_name if isinstance(rc_name, str) else list(rc_name)[0]
        check(rc_name in rcs, f"{ident}: render controller {rc_name} missing")
        rc = rcs.get(rc_name, {})
        check(rc.get("geometry", "").split(".", 1)[-1] in desc["geometry"], f"{ident}: rc geometry key")
        for t in rc.get("textures", []):
            check(t.split(".", 1)[-1] in desc["textures"], f"{ident}: rc texture key {t}")
        for m in rc.get("materials", []):
            for mv in m.values():
                check(mv.split(".", 1)[-1] in desc["materials"], f"{ident}: rc material {mv}")
    for mat in desc["materials"].values():
        check(mat in ("entity_alphatest", "entity_beam_additive"), f"{ident}: unexpected material {mat}")
    if "controller" in desc["animations"]:
        cname = desc["animations"]["controller"]
        for st in ctrls.get(cname, {"states": {}})["states"].values():
            for an in st.get("animations", []):
                full = desc["animations"].get(an)
                check(full in anims, f"{ident}: controller animation {an} -> {full} missing")

# ---------------------------------------------------------------- particles
particles = set()
for p, d in rp_json.items():
    if "particle_effect" in d:
        desc = d["particle_effect"]["description"]
        particles.add(desc["identifier"])
        check(os.path.exists(os.path.join(RP, desc["basic_render_parameters"]["texture"] + ".png")), f"{desc['identifier']}: texture missing")
        check(desc["basic_render_parameters"]["material"] in ("particles_add", "particles_alpha", "particles_blend"), "particle material")
        for comp, val in d["particle_effect"]["components"].items():
            check(comp.startswith("minecraft:"), f"particle component {comp}")
            for s in re.findall(r'"([^"]*(?:variable|math)[^"]*)"', json.dumps(val)):
                check(molang_ok(s), f"{desc['identifier']}: molang {s}")

# ---------------------------------------------------------------- BP entities & items
allowed = set(REF["entity_components"])
bp_entities = {}
for p, d in bp_json.items():
    e = d.get("minecraft:entity")
    if not e:
        continue
    ident = e["description"]["identifier"]
    bp_entities[ident] = e
    for g in [e.get("components", {})] + list(e.get("component_groups", {}).values()):
        for comp in g:
            check(comp in allowed, f"{ident}: component {comp} not in vanilla")
    for ev, body in e.get("events", {}).items():
        for gname in body.get("add", {}).get("component_groups", []):
            check(gname in e.get("component_groups", {}), f"{ident}: event adds unknown group")
    timer = e.get("components", {}).get("minecraft:timer")
    if timer:
        check(timer["time_down_event"]["event"] in e.get("events", {}), f"{ident}: timer event missing")
    check(ident in client_ids, f"{ident}: no client entity")
    for cause in [t.get("cause") for t in e.get("components", {}).get("minecraft:damage_sensor", {}).get("triggers", [])]:
        check(cause is None or re.fullmatch(r"[a-z_]+", cause), f"{ident}: damage cause {cause}")
BOSS_IDS = ("fb:void_emperor", "fb:titan", "fb:devouring_star", "fb:world_parasite", "fb:choir")
for ident in BOSS_IDS:
    e = bp_entities[ident]
    props = e["description"].get("properties", {})
    check(props.get("fb:state", {}).get("client_sync") and props.get("fb:phase", {}).get("client_sync"), f"{ident}: synced properties missing")
    has_bar = "minecraft:boss" in e["components"] or any("minecraft:boss" in g for g in e.get("component_groups", {}).values())
    check(has_bar, f"{ident}: no boss bar")
    # every state value the script can set must have a matching controller state (or fall back to idle)
    ctrl = ctrls.get(f"controller.animation.fb.{ident.split(':')[1]}")
    check(ctrl is not None, f"{ident}: animation controller missing")
    lo, hi = props["fb:state"]["range"]
    check(lo == 0 and hi >= 12, f"{ident}: fb:state range too small")

item_tex = rp_json[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
for k, v in item_tex.items():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {k} missing")
items = set()
for p, d in bp_json.items():
    it = d.get("minecraft:item")
    if not it:
        continue
    ident = it["description"]["identifier"]
    items.add(ident)
    for comp in it["components"]:
        check(comp in set(REF["item_components"]) | {"minecraft:glint"}, f"{ident}: component {comp}")
    check(it["components"]["minecraft:icon"]["textures"]["default"] in item_tex, f"{ident}: icon missing")

lang = dict(l.rstrip("\n").split("=", 1) for l in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") if "=" in l)
for i in items:
    check(f"item.{i}.name" in lang, f"lang {i}")
for e in bp_entities:
    check(f"entity.{e}.name" in lang, f"lang {e}")
for p, d in bp_json.items():
    r = d.get("minecraft:recipe_shaped")
    if r:
        check(r["result"]["item"] in items, "recipe result")
        for k in "".join(r["pattern"]):
            check(k == " " or k in r["key"], "recipe key")

# ---------------------------------------------------------------- scripts
js = ""
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    src = open(p, encoding="utf-8").read()
    js += src + "\n"
    for imp in re.findall(r'from "(\.[^"]+)"', src):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{p}: import {imp} missing")

fx_src = open(os.path.join(ROOT, "src", "core", "fx.ts")).read()
hues = re.findall(r'"([a-z]+)"', re.search(r"export type Hue = ([^;]+);", fx_src).group(1))
tones = re.findall(r'"([a-z]+)"', re.search(r"export type Tone = ([^;]+);", fx_src).group(1))
kinds = re.findall(r"`fb:([a-z]+)_\$\{h\}`", fx_src)
check(len(kinds) >= 6, f"expected 6 hue particle kinds in fx.ts, found {kinds}")
for kind in kinds:
    for h in hues:
        check(f"fb:{kind}_{h}" in particles, f"particle fb:{kind}_{h} missing")
for t in tones:
    check(f"fb:smoke_{t}" in particles, f"particle fb:smoke_{t} missing")
for pid in set(re.findall(r'"(fb:[a-z_]+)"', fx_src)):
    check(pid in particles, f"particle {pid} missing")
for h in set(re.findall(r'(?:mote|burst|sphereWave|groundWave|column|ringWave|beam|moteRing)\([\w.]+,\s*"([a-z]+)"', js)):
    check(h in hues, f"script uses unknown hue {h}")
for t in set(re.findall(r'smoke\([\w.]+,\s*"([a-z]+)"', js)):
    check(t in tones, f"script uses unknown smoke tone {t}")
for pid in set(re.findall(r'(?:spawnParticle|particle)\([^"]*"((?:fb|minecraft):[a-z_]+)"', js)):
    check(pid in particles or pid in REF["particles"], f"particle {pid} unknown")
for snd in set(re.findall(r'(?:sound\([\w.]+,\s*|playSound\()"([a-z0-9_.]+)"', js)):
    check(snd in REF["sounds"], f"sound {snd} not in vanilla")
effects = set(re.findall(r'"minecraft:([a-z_]+)"', open(os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts")).read()))
for eff in set(re.findall(r'(?:effect\([\w.]+,\s*|addEffect\()"([a-z_]+)"', js)):
    check(eff in effects, f"effect {eff} not a Minecraft effect")
for ent in set(re.findall(r'spawnEntity\("([a-z0-9_]+:[a-z_]+)"', js)) | set(re.findall(r'"(fb:choir_echo)"', js)) | set(re.findall(r'typeId: "(fb:[a-z_]+)"', js)):
    check(ent in bp_entities or ent in REF["entities"], f"entity {ent} not defined")
script_items = set(re.findall(r'loot: "([a-z0-9_]+:[a-z_]+)"', js)) | set(re.findall(r'"(fb:[a-z_]+)": \["fb_', js)) | set(re.findall(r'SIGIL = "([a-z]+:[a-z_]+)"', js))
check(len(script_items) >= 6, f"expected 6 script items, found {sorted(script_items)}")
for it in script_items:
    check(it in items, f"item {it} not defined")
blocks = set(re.findall(r'"(minecraft:[a-z_]+)"', open(os.path.join(ROOT, "src", "bosses", "titan.ts")).read() + open(os.path.join(ROOT, "src", "bosses", "parasite.ts")).read() + open(os.path.join(ROOT, "src", "trophies.ts")).read()))
VANILLA_BLOCKS = {"minecraft:polished_blackstone_bricks", "minecraft:smooth_stone", "minecraft:polished_deepslate", "minecraft:crimson_nylium"}
for bl in blocks:
    check(bl in VANILLA_BLOCKS, f"unexpected block id {bl}")
for cat in set(re.findall(r'\["(fb_[a-z]+)",\s*\d+\]', js)):
    check(any(d.get("minecraft:item", {}).get("components", {}).get("minecraft:cooldown", {}).get("category") == cat for d in bp_json.values()),
          f"cooldown category {cat} has no item")
for prop in set(re.findall(r'(?:setProperty|getProperty)\("([a-z0-9_]+:[a-z_]+)"', js)):
    check(all(prop in bp_entities[b]["description"].get("properties", {}) for b in BOSS_IDS), f"property {prop} undefined")
for ev in set(re.findall(r'triggerEvent\("([a-z0-9_]+:[a-z_]+)"', js)):
    check(ev in bp_entities["fb:world_parasite"].get("events", {}), f"event {ev} missing on the dormant boss")

# ---------------------------------------------------------------- model QA (z-fighting / detached parts)
qa = json.load(open(os.path.join(ROOT, "build", "model_qa.json")))
for k, q in qa.items():
    check(not q["zfight"], f"{k}: visible coplanar faces (z-fighting): {q['zfight'][:3]}")
    check(not q["islands"], f"{k}: detached parts: {q['islands'][:3]}")
    check(q["stats"]["cubes"] >= 200, f"{k}: model too simple ({q['stats']['cubes']} cubes)")

# ---------------------------------------------------------------- textures
for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(p)
    check(im.mode == "RGBA", f"{p} not RGBA")
    w, h = im.size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{p} not power of two")

print(f"{count[0]} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
