"""
Static validation of the built packs (run after tools/build.py):

    python3 tools/validate.py

Checks: JSON syntax; manifests / UUIDs / dependencies / script module version vs
typings; all 21 items (identifiers, components, stats == tools/rww/stats.py,
swing_duration == attack cooldown, tags, custom component); recipes (patterns,
keys, results, smithing chain); creative catalog; icons + item_texture.json;
attachables -> geometry / texture / animation / render controller; geometry
integrity (UV inside the texture, bone hierarchy, binding); animation bones exist
(attachable root / vanilla player rig, case-insensitive); every Molang expression
parses, uses only known math functions and vanilla queries, and evaluates to finite
values over a grid of player states; two-handed grip accuracy; sounds -> vanilla
files; lang keys; script <-> pack identifiers (custom component, animation names,
controllers, sound events, particles).
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rww import molang  # noqa: E402
from rww.materials import TIER_ORDER  # noqa: E402
from rww.stats import WEAPONS, item_id, stats  # noqa: E402

BP = os.path.join(ROOT, "build", "RWW_BP")
RP = os.path.join(ROOT, "build", "RWW_RP")
REF = json.load(open(os.path.join(HERE, "vanilla_refs.json")))

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
    for p in sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
        try:
            with open(p, encoding="utf-8") as f:
                out[p] = json.load(f)
            check(True, "")
        except Exception as e:  # noqa: BLE001
            check(False, f"invalid JSON {rel(p)}: {e}")
    return out


bp = {k: v for k, v in load_all(BP).items() if isinstance(v, dict)}   # languages.json is a list
rp = {k: v for k, v in load_all(RP).items() if isinstance(v, dict)}
WEAPON_ORDER = ["rapier", "zweihander", "katana"]
ITEM_IDS = {item_id(w, t) for w in WEAPON_ORDER for t in TIER_ORDER}
check(len(ITEM_IDS) == 21, "expected 21 item identifiers")

# ---------------------------------------------------------------------------------------------- manifests
bpm, rpm = bp[os.path.join(BP, "manifest.json")], rp[os.path.join(RP, "manifest.json")]
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", u), f"bad uuid {u}")
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on the RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on the BP")
typings = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")))["version"]
check(deps.get("@minecraft/server") == typings, f"manifest @minecraft/server {deps.get('@minecraft/server')} != typings {typings}")
check(not any("beta" in str(v) for v in deps.values()), "no beta script modules allowed")
script = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script) == 1 and os.path.exists(os.path.join(BP, script[0]["entry"])), "script entry missing")
for m in (bpm, rpm):
    check(m["header"]["min_engine_version"] == [1, 26, 60], "min_engine_version must be 1.26.60")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack_icon missing in {rel(p)}")

# ---------------------------------------------------------------------------------------------- items
items = {}
for p, d in bp.items():
    if "minecraft:item" in d:
        iid = d["minecraft:item"]["description"]["identifier"]
        check(iid not in items, f"duplicate item {iid}")
        items[iid] = (p, d)
check(set(items) == ITEM_IDS, f"item set mismatch: {sorted(set(items) ^ ITEM_IDS)}")
lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line:
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
item_tex = rp[os.path.join(RP, "textures", "item_texture.json")]["texture_data"]
for iid, (p, d) in items.items():
    tier, weapon = iid.split(":")[1].rsplit("_", 1)
    c = d["minecraft:item"]["components"]
    s = stats(weapon, tier)
    check(d["format_version"] == "1.26.60", f"{iid}: item format_version")
    check(c["minecraft:damage"]["value"] == s["damage"], f"{iid}: damage")
    check(c["minecraft:durability"]["max_durability"] == s["durability"], f"{iid}: durability")
    check(c["minecraft:enchantable"] == {"slot": "sword", "value": s["enchantability"]}, f"{iid}: enchantable")
    cd = c["minecraft:cooldown"]
    check(cd["type"] == "attack" and cd["category"] == "rww:weapon" and cd["duration"] == WEAPONS[weapon]["cooldown"], f"{iid}: cooldown")
    check(c["minecraft:swing_duration"]["value"] == cd["duration"], f"{iid}: swing_duration must equal the attack cooldown")
    check(c["minecraft:max_stack_size"]["value"] == 1, f"{iid}: stack size")
    tags = c["minecraft:tags"]["tags"]
    check(f"rww:{weapon}" in tags and "rww:weapon" in tags and f"minecraft:{tier}_tier" in tags, f"{iid}: tags")
    check("minecraft:is_spear" not in tags, f"{iid}: must not use the vanilla spear animation tag")
    cc = c.get("rww:weapon")
    check(cc == {"type": weapon, "tier": tier, "damage": s["total_damage"]}, f"{iid}: custom component params")
    if WEAPONS[weapon]["reach"]:
        pw = c.get("minecraft:piercing_weapon")
        check(pw and pw["reach"]["max"] == WEAPONS[weapon]["reach"][1] and pw["reach"]["min"] == 0, f"{iid}: reach")
    else:
        check("minecraft:piercing_weapon" not in c, f"{iid}: katana keeps vanilla targeting")
    icon = c["minecraft:icon"]["textures"]["default"]
    check(icon in item_tex, f"{iid}: icon key {icon} missing in item_texture.json")
    if icon in item_tex:
        f = os.path.join(RP, item_tex[icon]["textures"] + ".png")
        if check(os.path.exists(f), f"{iid}: icon file missing"):
            im = Image.open(f)
            check(im.size == (32, 32) and im.mode == "RGBA", f"{iid}: icon must be 32x32 RGBA")
    dn = c["minecraft:display_name"]["value"]
    check(dn in lang and lang[dn].strip(), f"{iid}: display name {dn} missing in en_US.lang")
    for ev in c["minecraft:swing_sounds"].values():
        check(ev.startswith("rww.") or ev in REF["sound_events"], f"{iid}: unknown sound event {ev}")
    for r in c["minecraft:repairable"]["repair_items"]:
        for it in r["items"]:
            if isinstance(it, str):
                check(it in ITEM_IDS or it in REF["items"], f"{iid}: repair item {it}")
        molang.parse(r["repair_amount"])
    check(("minecraft:fire_resistant" in c) == (tier == "netherite"), f"{iid}: fire resistance only for netherite")
    check(("minecraft:fuel" in c) == (tier == "wooden"), f"{iid}: fuel only for wooden")

# ---------------------------------------------------------------------------------------------- recipes
crafted = set()
smith = set()
for p, d in bp.items():
    for kind in ("minecraft:recipe_shaped", "minecraft:recipe_smithing_transform", "minecraft:recipe_furnace"):
        if kind not in d:
            continue
        r = d[kind]
        if kind == "minecraft:recipe_shaped":
            res = r["result"]["item"]
            crafted.add(res)
            used = set("".join(r["pattern"])) - {" "}
            check(used == set(r["key"]), f"{rel(p)}: pattern keys mismatch")
            for k, v in r["key"].items():
                if "item" in v:
                    check(v["item"] in REF["items"], f"{rel(p)}: unknown ingredient {v['item']}")
                else:
                    check(v["tag"] in REF["recipe_tags"], f"{rel(p)}: unknown tag {v['tag']}")
            check("crafting_table" in r["tags"], f"{rel(p)}: crafting tag")
        elif kind == "minecraft:recipe_smithing_transform":
            smith.add(r["result"])
            check(r["template"] == "minecraft:netherite_upgrade_smithing_template", f"{rel(p)}: template")
            check(r["base"] in ITEM_IDS and r["base"].startswith("rww:diamond_"), f"{rel(p)}: base")
            check(r["result"] == r["base"].replace("diamond", "netherite"), f"{rel(p)}: result")
        else:
            check(r["input"] in ITEM_IDS and r["output"] in REF["items"], f"{rel(p)}: furnace recipe")
for iid in ITEM_IDS:
    if "netherite" in iid:
        check(iid in smith, f"{iid}: no smithing recipe")
    else:
        check(iid in crafted, f"{iid}: no crafting recipe")
patterns = {}
for p, d in bp.items():
    r = d.get("minecraft:recipe_shaped")
    if r:
        key = (tuple(r["pattern"]), json.dumps(r["key"], sort_keys=True))
        check(key not in patterns, f"recipe collision {rel(p)} vs {patterns.get(key)}")
        patterns[key] = rel(p)

cat = bp[os.path.join(BP, "item_catalog", "crafting_item_catalog.json")]["minecraft:crafting_items_catalog"]
listed = [i for c in cat["categories"] for g in c["groups"] for i in g["items"]]
check(sorted(listed) == sorted(ITEM_IDS), "creative catalog must list all 21 items exactly once")
for c in cat["categories"]:
    for g in c["groups"]:
        check(g["group_identifier"]["name"] in lang, f"group name {g['group_identifier']['name']} missing in lang")

# ---------------------------------------------------------------------------------------------- geometry
geos = {}
for p, d in rp.items():
    if "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            gid = g["description"]["identifier"]
            geos[gid] = g
            W, H = g["description"]["texture_width"], g["description"]["texture_height"]
            names = {b["name"].lower() for b in g["bones"]}
            for b in g["bones"]:
                if b.get("parent"):
                    check(b["parent"].lower() in names, f"{gid}: bone {b['name']} has unknown parent")
                for c in b.get("cubes", []):
                    for face, uv in c["uv"].items():
                        u, v = uv["uv"]
                        w, h = uv["uv_size"]
                        u0, u1 = sorted((u, u + w))
                        v0, v1 = sorted((v, v + h))
                        check(0 <= u0 and u1 <= W and 0 <= v0 and v1 <= H, f"{gid}: uv out of bounds on {face}")
            roots = [b for b in g["bones"] if not b.get("parent")]
            check(len(roots) == 1 and roots[0].get("binding") == "q.item_slot_to_bone_name(c.item_slot)",
                  f"{gid}: single bound root bone expected")
check(set(geos) == {f"geometry.rww.{w}" for w in WEAPON_ORDER}, "geometry set")

# ---------------------------------------------------------------------------------------------- animations
animations = {}
for p, d in rp.items():
    if "animations" in d and isinstance(d["animations"], dict):
        animations.update(d["animations"])
QUERIES = set(REF["molang_queries"])
VAR_OK = {"attack_time", "is_first_person", "player_arm_height", "hand_bob", "attack_body_rot_y", "swim_amount"}


def molang_check(expr, where):
    try:
        prog = molang.parse(expr)
    except molang.MolangError as e:
        check(False, f"{where}: Molang parse error {e}")
        return
    for prob in molang.check_arity(prog):
        check(False, f"{where}: {prob}")
    for qn in molang.names_used(prog, "query"):
        check(qn in QUERIES, f"{where}: unknown query.{qn}")
    for vn in molang.names_used(prog, "variable"):
        check(vn.startswith("rww_") or vn in VAR_OK, f"{where}: unexpected variable v.{vn}")


n_expr = 0
for an, a in animations.items():
    for bone, ch in (a.get("bones") or {}).items():
        for chan, vec in ch.items():
            for i, e in enumerate(vec if isinstance(vec, list) else [vec]):
                if isinstance(e, str):
                    molang_check(e, f"{an}/{bone}.{chan}[{i}]")
                    n_expr += 1

for w in WEAPON_ORDER:
    for k in ("arms", "body"):
        name = f"animation.rww.{w}.{k}"
        check(name in animations, f"missing {name}")
        for bone in animations.get(name, {}).get("bones", {}):
            check(bone.lower() in REF["player_bones"], f"{name}: bone {bone} not in the player rig")
    check(animations.get(f"animation.rww.{w}.arms", {}).get("override_previous_animation") is True, f"{w} arms must override")
    check(not animations.get(f"animation.rww.{w}.body", {}).get("override_previous_animation"), f"{w} body must be additive")

# ---------------------------------------------------------------------------------------------- attachables
attachables = {}
for p, d in rp.items():
    if "minecraft:attachable" in d:
        desc = d["minecraft:attachable"]["description"]
        attachables[desc["identifier"]] = desc
check(set(attachables) == ITEM_IDS, "one attachable per item")
for iid, desc in attachables.items():
    gid = desc["geometry"]["default"]
    check(gid in geos, f"{iid}: geometry {gid}")
    for k, t in desc["textures"].items():
        ok = os.path.exists(os.path.join(RP, t + ".png")) or t in REF["textures"]
        check(ok, f"{iid}: texture {t}")
        if os.path.exists(os.path.join(RP, t + ".png")) and gid in geos:
            im = Image.open(os.path.join(RP, t + ".png"))
            d = geos[gid]["description"]
            check(im.size == (d["texture_width"], d["texture_height"]), f"{iid}: texture size != geometry")
    for m in desc["materials"].values():
        check(m in REF["attachable_materials"], f"{iid}: material {m}")
    for rc in desc["render_controllers"]:
        check(rc in REF["render_controllers"], f"{iid}: render controller {rc}")
    root = geos[gid]["bones"][0]["name"].lower() if gid in geos else ""
    for short, full in desc["animations"].items():
        check(full in animations, f"{iid}: animation {full}")
        for bone in animations.get(full, {}).get("bones", {}):
            check(bone.lower() == root, f"{iid}: {full} animates unknown bone {bone}")
    for entry in desc["scripts"]["animate"]:
        for short, cond in (entry.items() if isinstance(entry, dict) else [(entry, None)]):
            check(short in desc["animations"], f"{iid}: animate entry {short}")
            if cond:
                molang_check(cond, f"{iid}: animate condition")

# ---------------------------------------------------------------------------------------------- sounds
sd = rp[os.path.join(RP, "sounds", "sound_definitions.json")]["sound_definitions"]
for ev, v in sd.items():
    for s in v["sounds"]:
        check(s["name"] in REF["sound_files"], f"sound {ev}: vanilla file {s['name']} not found")
for iid, (p, d) in items.items():
    for ev in d["minecraft:item"]["components"]["minecraft:swing_sounds"].values():
        check(ev in sd or ev in REF["sound_events"], f"{iid}: sound event {ev} undefined")

# ---------------------------------------------------------------------------------------------- script <-> packs
js = ""
for p in glob.glob(os.path.join(BP, "scripts", "*.js")):
    js += open(p, encoding="utf-8").read()
check('"rww:weapon"' in js, "script must register the rww:weapon custom component")
for an in re.findall(r"animation\.rww\.\$\{weapon\}\.(\w+)", js):
    for w in WEAPON_ORDER:
        check(f"animation.rww.{w}.{an}" in animations, f"script plays animation.rww.{w}.{an} which is not defined")
for ev in re.findall(r'playSound\("([^"]+)"', js):
    check(ev in sd or ev in REF["sound_events"], f"script sound {ev} undefined")
for pt in re.findall(r'"(minecraft:[a-z_]+_emitter)"', js):
    check(pt in REF["particles"], f"script particle {pt} unknown")
for stop in re.findall(r"`(!q\.equipped_item_any_tag[^`]+)`", js):
    for w in WEAPON_ORDER:
        molang_check(stop.replace("${weapon}", w), "stop expression")

# ---------------------------------------------------------------------------------------------- numeric sweep
from rww import preview  # noqa: E402

bad = 0
for w in WEAPON_ORDER:
    states = [{}, {"moving": 0.8, "distance": 2.3}, {"moving": 1.0, "sprinting": True, "distance": 4.1},
              {"sneaking": True}, {"on_ground": False, "vertical_speed": -6}, {"swimming": True, "swim_amount": 1.0},
              {"riding": True}, {"first_person": True}, {"first_person": True, "moving": 0.8, "distance": 1.7}]
    for st in states:
        for atk in [None] + [(v, t) for v in range(3) for t in (0.03, 0.15, 0.3, 0.5, 0.8, 0.97)]:
            pose, ctx = preview.simulate(w, st, frames=6, attack=atk)
            for bname, bpz in pose.items():
                vals = list(bpz.rot) + list(bpz.pos)
                if not all(math.isfinite(x) for x in vals) or max(abs(x) for x in bpz.rot) > 900 or max(abs(x) for x in bpz.pos) > 40:
                    bad += 1
check(bad == 0, f"{bad} non-finite / out-of-range bone values in the animation sweep")

# two-handed grip accuracy (left hand on the grip) over stances and every attack frame
grip_report = {}
for w in ("katana", "zweihander"):
    worst = 0.0
    total = []
    # in combat (the Zweihander otherwise rests one-handed on the shoulder, by design)
    combat = {"rww_lat": 1e9, "rww_carry": 0.0}
    for st in ({}, {"moving": 0.8, "distance": 2.3}, {"sneaking": True}, {"on_ground": False, "vertical_speed": -3}):
        pose, ctx = preview.simulate(w, st, frames=30, variables=dict(combat))
        pm = preview.player.player_matrices(pose)
        am = preview.attach(w, ctx, pm, False)
        e, _ = preview.grip_error(w, pm, am)
        worst = max(worst, e)
        total.append(e)
    for v in range(3):
        for i in range(1, 40):
            t = i / 40
            pose, ctx = preview.simulate(w, {}, frames=2, attack=(v, t), variables={"rww_carry": 0.0})
            pm = preview.player.player_matrices(pose)
            am = preview.attach(w, ctx, pm, False)
            e, _ = preview.grip_error(w, pm, am)
            total.append(e)
            worst = max(worst, e)
    grip_report[w] = (worst, sum(total) / len(total))
    check(worst < 1.6, f"{w}: left hand leaves the grip by {worst:.2f} units")
    check(sum(total) / len(total) < 0.35, f"{w}: mean grip error {sum(total) / len(total):.2f}")

# IK solution quality + frame-to-frame continuity of every attack (no snaps / whole turns)
from rww import anims  # noqa: E402

continuity = {}
for w in WEAPON_ORDER:
    try:
        wa = anims.solve_weapon(w)
    except ValueError as e:
        check(False, f"{w}: {e}")
        continue
    shrug = max(max(p.info["shrugR"], p.info["shrugL"]) for keys in wa.attacks for _, p in keys)
    loco = max(max(p.info["shrugR"], p.info["shrugL"]) for p in wa.poses.values())
    check(shrug <= 2.5 and loco <= 2.5, f"{w}: shoulder offset {max(shrug, loco):.2f} > 2.5 units")
    worst = 0.0
    for v in range(3):
        prev = None
        for i in range(0, 201):
            t = i / 200
            pose, ctx = preview.simulate(w, {}, frames=1, attack=(v, t) if 0 < t < 1 else None,
                                         variables={"rww_carry": 0.0})
            cur = {b: (pose[b].rot.copy(), pose[b].pos.copy()) for b in ("rightarm", "leftarm", "rightitem", "body")}
            if prev is not None:
                for b in cur:
                    worst = max(worst, float(max(abs(cur[b][0] - prev[b][0]))))
            prev = cur
    continuity[w] = (shrug, worst)
    check(worst < 30.0, f"{w}: a bone rotates {worst:.1f} degrees within 1/200 of a swing (snap)")

print(f"{count['n']} checks, {n_expr} animation expressions, {len(errors)} errors")
for w, (shrug, worst) in continuity.items():
    print(f"  {w}: max shoulder offset {shrug:.2f} units, max rotation step {worst:.1f} deg per 1/200 swing")
for w, (worst, mean) in grip_report.items():
    print(f"  two-handed grip {w}: worst {worst:.2f} units, mean {mean:.3f} units (Minecraft fist = 4 units)")
for e in errors[:60]:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
