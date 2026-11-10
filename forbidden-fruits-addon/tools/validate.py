"""
Static validation of the combined pack (run after build.py):   python3 tools/validate.py

* every file each fruit's generator produced is in the combined pack byte-for-byte (nothing lost or altered),
  except the shared files merged by hand, which are checked here:
* player.json: vanilla components + both fruits' properties
* player.entity.json: vanilla intact + every addition of both fruits; combined player render controllers
  (oil body hides/tints, steam glow, engine `this` fallback)
* item atlas, sounds, language: union of both fruits
* scripts: one entry that loads shared + steam + oil, all imports resolve, and every particle, sound,
  animation, entity and item id each fruit's scripts use exists in the combined packs
"""
import filecmp
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Forbidden_BP")
RP = os.path.join(BUILD, "Forbidden_RP")
VAN = os.path.join(REPO, "sekiyu-addon", "tools", "vanilla")
sys.path.insert(0, HERE)
import build  # noqa: E402

errors = []
n = {"c": 0}


def check(cond, msg):
    n["c"] += 1
    if not cond:
        errors.append(msg)


def load(p):
    return json.load(open(p, encoding="utf-8"))


def molang_ok(e):
    if not isinstance(e, str):
        return True
    d = 0
    for ch in e:
        d += (ch == "(") - (ch == ")")
        if d < 0:
            return False
    return d == 0


for p in glob.glob(os.path.join(BUILD, "Forbidden_*", "**", "*.json"), recursive=True):
    try:
        load(p)
        check(True, "")
    except Exception as e:  # noqa: BLE001
        check(False, f"invalid JSON {p}: {e}")

# ---------------------------------------------------------------- manifests
bpm, rpm = load(os.path.join(BP, "manifest.json")), load(os.path.join(RP, "manifest.json"))
uu = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uu)) == len(uu), "UUIDs not unique")
for other in glob.glob(os.path.join(REPO, "*-addon", "**", "manifest.json"), recursive=True):
    if "forbidden-fruits-addon" in other or "node_modules" in other:
        continue
    o = load(other)
    check(not ({o["header"]["uuid"]} | {m["uuid"] for m in o.get("modules", [])}) & set(uu), f"UUID collision with {other}")
check(len([m for m in bpm["modules"] if m["type"] == "script"]) == 1 and os.path.exists(os.path.join(BP, "scripts", "main.js")), "one script entry")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get("@minecraft/server") == "2.11.0" and deps.get("@minecraft/server-ui") == "2.3.0" and deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "dependencies")

# ---------------------------------------------------------------- nothing lost from either fruit
for name, (proj, bpn, rpn) in build.PARTS_SPEC.items():
    for side, src_root, dst_root in (("bp", os.path.join(build.PARTS, name, bpn), BP), ("rp", os.path.join(build.PARTS, name, rpn), RP)):
        files = [f for f in glob.glob(os.path.join(src_root, "**", "*"), recursive=True) if os.path.isfile(f)]
        check(len(files) >= 5, f"{name} {side}: part not generated")
        for f in files:
            rel = os.path.relpath(f, src_root).replace(os.sep, "/")
            if rel in build.MERGED[side]:
                continue
            dst = os.path.join(dst_root, rel)
            check(os.path.exists(dst) and filecmp.cmp(f, dst, shallow=False), f"{name}: {side}/{rel} missing or altered")

# ---------------------------------------------------------------- player behaviour
van_bp = load(os.path.join(VAN, "player.json"))["minecraft:entity"]
pl = load(os.path.join(BP, "entities", "player.json"))["minecraft:entity"]
check(pl["components"] == van_bp["components"] and pl.get("events") == van_bp.get("events"), "player.json diverges from vanilla")
props = pl["description"]["properties"]
want = set()
for name, (proj, bpn, _) in build.PARTS_SPEC.items():
    want |= set(load(os.path.join(build.PARTS, name, bpn, "entities", "player.json"))["minecraft:entity"]["description"]["properties"])
check(set(props) == want and len(want) == 5, f"player properties {sorted(props)}")

# ---------------------------------------------------------------- player client
van = load(os.path.join(VAN, "player.entity.json"))["minecraft:client_entity"]["description"]
pe = load(os.path.join(RP, "entity", "player.entity.json"))["minecraft:client_entity"]["description"]
for section in ("materials", "textures", "geometry", "animations"):
    for k, v in van[section].items():
        check(pe[section].get(k) == v, f"lost vanilla {section}.{k}")
for name, (proj, _, rpn) in build.PARTS_SPEC.items():
    part = load(os.path.join(build.PARTS, name, rpn, "entity", "player.entity.json"))["minecraft:client_entity"]["description"]
    for section in ("materials", "textures", "geometry", "animations", "particle_effects"):
        for k, v in part.get(section, {}).items():
            check(pe.get(section, {}).get(k) == v, f"{name}: player {section}.{k} not merged")
    for section in ("initialize", "pre_animation"):
        for line in part["scripts"][section]:
            check(line in pe["scripts"][section], f"{name}: {section} line missing: {line[:50]}")
    for entry in part["scripts"]["animate"]:
        check(entry in pe["scripts"]["animate"], f"{name}: animate entry missing {entry}")
    for entry in part["render_controllers"][len(van["render_controllers"]):]:
        check(entry in pe["render_controllers"], f"{name}: overlay render controller missing {entry}")
for line in pe["scripts"]["pre_animation"] + pe["scripts"]["initialize"]:
    check(molang_ok(line) and line.strip().endswith(";"), f"bad molang {line[:50]}")
check(pe["scripts"]["animate"][: len(van["scripts"]["animate"])] == van["scripts"]["animate"], "vanilla animate order")
rcs = {}
for p in glob.glob(os.path.join(RP, "render_controllers", "*.json")):
    rcs.update(load(p)["render_controllers"])
for mine, theirs in zip(pe["render_controllers"], van["render_controllers"]):
    (mk, mc), = mine.items()
    (vk, vc), = theirs.items()
    check(mk == build.PLAYER_RC.get(vk, vk) and mc == vc, f"player rc {vk} -> {mk}")
for entry in pe["render_controllers"]:
    (k, cond), = entry.items()
    check(k in rcs or k.startswith("controller.render.player."), f"render controller {k} undefined")
for k in build.PLAYER_RC.values():
    rc = rcs.get(k, {})
    for ch, expr in rc.get("overlay_color", {}).items():
        check(all(t in expr for t in ("sekiyu_form", "joki_glow", "this")) and molang_ok(expr), f"{k}.{ch} must combine oil tint, steam glow and `this`")
    check(all(v is False or "sekiyu_form != 3" in str(v) for e in rc.get("part_visibility", []) for v in e.values()), f"{k}: hide while dissolved")
for k, v in pe.get("particle_effects", {}).items():
    if ":" in v and not v.startswith("minecraft:"):
        ns, nm = v.split(":")
        check(os.path.exists(os.path.join(RP, "particles", ns, nm + ".json")), f"player particle {v} missing")

# ---------------------------------------------------------------- tables
tex = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
snd = load(os.path.join(RP, "sounds", "sound_definitions.json"))["sound_definitions"]
lang = dict(l.rstrip("\n").split("=", 1) for l in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") if "=" in l)
for name, (proj, bpn, rpn) in build.PARTS_SPEC.items():
    for k in load(os.path.join(build.PARTS, name, rpn, "textures", "item_texture.json"))["texture_data"]:
        check(k in tex, f"item texture {k} missing")
    for k, d in load(os.path.join(build.PARTS, name, rpn, "sounds", "sound_definitions.json"))["sound_definitions"].items():
        check(snd.get(k) == d, f"sound {k} missing")
    for l in open(os.path.join(build.PARTS, name, rpn, "texts", "en_US.lang"), encoding="utf-8"):
        if "=" in l and not l.startswith("pack."):
            k, v = l.rstrip("\n").split("=", 1)
            check(lang.get(k) == v, f"lang {k} missing")
check(lang.get("pack.name") == "Forbidden Fruits", "pack name")
for v in tex.values():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture file {v}")
for d in snd.values():
    for s in d["sounds"]:
        check(os.path.exists(os.path.join(RP, s["name"] + ".ogg")), f"sound file {s['name']}")

# ---------------------------------------------------------------- scripts
js = {p: open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True)}
main = js[os.path.join(BP, "scripts", "main.js")]
for sub in ("./shared/fruits.js", "./steam/main.js", "./oil/main.js"):
    check(f'import "{sub}"' in main, f"main.js must load {sub}")
for p, src in js.items():
    for imp in re.findall(r'from "(\.[^"]+)"|import "(\.[^"]+)"', src):
        imp = imp[0] or imp[1]
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{p}: import {imp} unresolved")
particles = set()
for p in glob.glob(os.path.join(RP, "particles", "**", "*.json"), recursive=True):
    particles.add(load(p)["particle_effect"]["description"]["identifier"])
anims = {}
for p in glob.glob(os.path.join(RP, "animations", "*.json")):
    anims.update(load(p)["animations"])
bp_items = {load(p)["minecraft:item"]["description"]["identifier"] for p in glob.glob(os.path.join(BP, "items", "*.json"))}
bp_ents = {load(p)["minecraft:entity"]["description"]["identifier"] for p in glob.glob(os.path.join(BP, "entities", "**", "*.json"), recursive=True)}
for sub, ns, prefix in (("steam", "joki", "joki"), ("oil", "sekiyu", "sekiyu")):
    fx = js[os.path.join(BP, "scripts", sub, "core", "fx.js")]
    for pid in re.findall(rf'"({ns}:[a-z_]+)"', fx[fx.index("export const P"):fx.index("export const S")]):
        check(pid in particles, f"{sub}: particle {pid}")
    for sid in re.findall(rf'"({ns}\.[a-z_.]+)"', fx[fx.index("export const S"):fx.index("export function particle")]):
        check(sid in snd, f"{sub}: sound {sid}")
    alljs = "\n".join(s for p, s in js.items() if f"{os.sep}{sub}{os.sep}" in p)
    for a in set(re.findall(r'anim\(\w+, "(\w+)"\)', alljs)):
        check(f"animation.{prefix}.player.{a}" in anims, f"{sub}: player animation {a}")
    for a in set(re.findall(r'entityAnim\(\w+, "([\w.]+)"\)', alljs)):
        check(a in anims, f"{sub}: entity animation {a}")
    for item in set(re.findall(rf'"({ns}:[a-z_]+)"', js[os.path.join(BP, "scripts", sub, "config.js")])):
        if item.endswith(("_fruit", "_valve", "_core")):
            check(item in bp_items, f"{sub}: item {item}")
        if item in ("sekiyu:oil_pool", "sekiyu:black_tide", "sekiyu:black_geyser", "sekiyu:tar_prison", "sekiyu:black_serpent", "sekiyu:fruit_relic"):
            check(item in bp_ents, f"{sub}: entity {item}")
shared = js[os.path.join(BP, "scripts", "shared", "fruits.js")]
for item in re.findall(r'item: "([a-z]+:[a-z_]+)"', shared):
    check(item in bp_items, f"shared fruit {item} not an item")
check(len(re.findall(r'item: "', shared)) == 2, "both fruits registered in the one-fruit rule")

print(f"{n['c']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
