"""
Static validation of the built packs (run after build.py):

    python3 tools/validate.py

Checks JSON syntax, manifests / UUIDs / dependencies, the player overrides against the vanilla
1.26.60 files (only the intended additions may differ), the steam animation controller, every
particle (texture, atlas UVs, Molang balance, allowed variables), sounds (definitions + .ogg files),
items, language keys, textures, and that every id the compiled scripts use (particles, sounds,
animations, effects, items, actor properties, menu icons) exists in the packs or in vanilla.
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "Joki_BP")
RP = os.path.join(ROOT, "build", "Joki_RP")
VAN = os.path.join(HERE, "vanilla")
REF = json.load(open(os.path.join(VAN, "reference.json")))

errors = []
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


def molang_ok(expr):
    if not isinstance(expr, str):
        return True
    depth = 0
    for ch in expr:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return False
    if depth != 0:
        return False
    # ternaries must be complete
    return expr.count("?") - expr.count("??") * 2 <= expr.count(":")


def walk_values(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from walk_values(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_values(v)
    else:
        yield o


bp_json = load_all(BP)
rp_json = load_all(RP)
J = lambda root, *p: (bp_json if root == BP else rp_json)[os.path.join(root, *p)]  # noqa: E731

# ---------------------------------------------------------------- manifests
bpm, rpm = J(BP, "manifest.json"), J(RP, "manifest.json")
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs are not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", u), f"bad uuid v4 {u}")
for other in glob.glob(os.path.join(ROOT, "..", "*-addon", "**", "manifest.json"), recursive=True):
    if "joki-joki-addon" in other or "node_modules" in other:
        continue
    try:
        o = json.load(open(other))
        theirs = {o["header"]["uuid"]} | {m["uuid"] for m in o.get("modules", [])}
        check(not (theirs & set(uuids)), f"UUID collision with {other}")
    except Exception:  # noqa: BLE001
        pass
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on the RP (same version)")
check(any(d.get("uuid") == bpm["header"]["uuid"] and d["version"] == bpm["header"]["version"] for d in rpm["dependencies"]), "RP must depend on the BP")
script_mod = [m for m in bpm["modules"] if m["type"] == "script"]
check(len(script_mod) == 1 and os.path.exists(os.path.join(BP, script_mod[0]["entry"])), "script entry missing")
for pkg, key in (("server", "@minecraft/server"), ("server-ui", "@minecraft/server-ui")):
    v = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", pkg, "package.json")))["version"]
    check(deps.get(key) == v, f"manifest {key} {deps.get(key)} != typings {v}")
    check("-" not in deps.get(key, "-"), f"{key} must be a stable (non-beta) version")
check(bpm["header"]["min_engine_version"] == [1, 26, 60] and rpm["header"]["min_engine_version"] == [1, 26, 60], "min_engine_version")
for p in (BP, RP):
    check(os.path.exists(os.path.join(p, "pack_icon.png")), f"pack_icon missing in {rel(p)}")

# ---------------------------------------------------------------- behaviour pack player override
van_bp = json.load(open(os.path.join(VAN, "player.json")))
pl = J(BP, "entities", "player.json")
e = pl["minecraft:entity"]
ve = van_bp["minecraft:entity"]
check(e["components"] == ve["components"] and e.get("component_groups") == ve.get("component_groups") and e.get("events") == ve.get("events"),
      "player.json diverges from vanilla beyond the properties")
desc_extra = {k: v for k, v in e["description"].items() if k != "properties"}
check(desc_extra == ve["description"], "player.json description changed beyond properties")
props = e["description"].get("properties", {})
check(set(props) == {"joki:mode", "joki:heat", "joki:overheat"}, f"unexpected properties {sorted(props)}")
for k, pdef in props.items():
    check(pdef.get("client_sync") is True, f"{k} must be client_sync")
check(props["joki:mode"]["range"] == [0, 4] and props["joki:heat"]["range"] == [0, 10] and props["joki:overheat"]["type"] == "bool", "property ranges")

# ---------------------------------------------------------------- resource pack player override
van_rp = json.load(open(os.path.join(VAN, "player.entity.json")))["minecraft:client_entity"]["description"]
pe = J(RP, "entity", "player.entity.json")["minecraft:client_entity"]["description"]
for section in ("materials", "textures", "geometry", "animations"):
    for k, val in van_rp[section].items():
        check(pe[section].get(k) == val, f"player.entity.json lost vanilla {section}.{k}")
for section in ("initialize", "pre_animation"):
    check(pe["scripts"][section][: len(van_rp["scripts"][section])] == van_rp["scripts"][section], f"vanilla {section} changed")
    for line in pe["scripts"][section]:
        check(molang_ok(line) and line.strip().endswith(";"), f"bad molang statement: {line[:80]}")
check(pe["scripts"]["animate"][: len(van_rp["scripts"]["animate"])] == van_rp["scripts"]["animate"], "vanilla animate list changed")
check(pe["scripts"]["animate"][-1] == "joki_steam" and pe["animations"].get("joki_steam") == "controller.animation.joki.steam", "steam controller not animated")
swap = {"controller.render.player.third_person": "controller.render.joki.player.third_person",
        "controller.render.player.first_person": "controller.render.joki.player.first_person"}
check(len(pe["render_controllers"]) == len(van_rp["render_controllers"]), "render controller count changed")
for mine, theirs in zip(pe["render_controllers"], van_rp["render_controllers"]):
    (vk, vc), = theirs.items()
    (mk, mc), = mine.items()
    check(mk == swap.get(vk, vk) and mc == vc, f"render controller entry {vk} -> {mk} wrong")
for key in ("enable_attachables",):
    check(pe.get(key) == van_rp.get(key), f"{key} changed")

van_rc = json.load(open(os.path.join(VAN, "player.render_controllers.json")))["render_controllers"]
rcs = {}
for p, d in rp_json.items():
    if isinstance(d, dict) and "render_controllers" in d:
        rcs.update(d["render_controllers"])
for vname, jname in swap.items():
    check(jname in rcs, f"{jname} missing")
    mine = dict(rcs.get(jname, {}))
    ov = mine.pop("overlay_color", None)
    check(mine == van_rc[vname], f"{jname} must equal vanilla {vname} apart from overlay_color")
    check(ov is not None and set(ov) == {"r", "g", "b", "a"} and all(molang_ok(x) and "this" in x for x in ov.values()),
          f"{jname} overlay_color must keep `this` for hurt flashes")

# variables used in render controllers / controller must be defined by pre_animation or initialize
defined = set()
for line in pe["scripts"]["initialize"] + pe["scripts"]["pre_animation"]:
    m = re.match(r"\s*(variable\.\w+)\s*=", line)
    if m:
        defined.add(m.group(1))
for rc_name in swap.values():
    for val in walk_values(rcs.get(rc_name, {}).get("overlay_color", {})):
        for var in re.findall(r"variable\.joki_\w+", str(val)):
            check(var in defined, f"{rc_name} uses undefined {var}")

# ---------------------------------------------------------------- particles
atlas = Image.open(os.path.join(RP, "textures", "particle", "joki_steam.png"))
particle_ids = {}
ALLOWED_VARS = re.compile(r"^variable\.(particle_age|particle_lifetime|particle_random_[1-4]|emitter_age|emitter_lifetime|direction(\.[xyz])?|power|radius)$")
for p, d in rp_json.items():
    if not (isinstance(d, dict) and "particle_effect" in d):
        continue
    pdesc = d["particle_effect"]["description"]
    ident = pdesc["identifier"]
    check(ident not in particle_ids, f"duplicate particle {ident}")
    particle_ids[ident] = d
    tex = pdesc["basic_render_parameters"]["texture"]
    check(os.path.exists(os.path.join(RP, tex + ".png")), f"{ident}: texture {tex} missing")
    check(pdesc["basic_render_parameters"]["material"] in ("particles_alpha", "particles_blend", "particles_add"), f"{ident}: material")
    comps = d["particle_effect"]["components"]
    check(any(k.startswith("minecraft:emitter_rate") for k in comps), f"{ident}: no emitter rate")
    check(any(k.startswith("minecraft:emitter_lifetime") for k in comps), f"{ident}: no emitter lifetime")
    check(any(k.startswith("minecraft:emitter_shape") for k in comps), f"{ident}: no emitter shape")
    check("minecraft:particle_lifetime_expression" in comps, f"{ident}: no particle lifetime")
    bb = comps.get("minecraft:particle_appearance_billboard")
    check(bb is not None, f"{ident}: no billboard")
    if bb:
        uv = bb["uv"]
        check(uv["texture_width"] == atlas.size[0] and uv["texture_height"] == atlas.size[1], f"{ident}: atlas size mismatch")
        u0, v0 = uv["uv"]
        if isinstance(u0, (int, float)):
            check(0 <= u0 and u0 + uv["uv_size"][0] <= atlas.size[0], f"{ident}: u out of atlas")
        check(isinstance(v0, (int, float)) and 0 <= v0 and v0 + uv["uv_size"][1] <= atlas.size[1], f"{ident}: v out of atlas")
        if bb["facing_camera_mode"] == "lookat_direction":
            check(bb.get("direction", {}).get("mode") == "derive_from_velocity", f"{ident}: lookat_direction needs a direction mode")
    rate = comps.get("minecraft:emitter_rate_steady")
    if rate:
        check(rate["max_particles"] <= 80, f"{ident}: too many particles for mobile ({rate['max_particles']})")
        check("minecraft:emitter_local_space" in comps, f"{ident}: looping body emitter must be in local space")
    inst = comps.get("minecraft:emitter_rate_instant")
    if inst:
        check(inst["num_particles"] <= 70, f"{ident}: burst too large for mobile")
    for val in walk_values(comps):
        if isinstance(val, str):
            check(molang_ok(val), f"{ident}: unbalanced molang {val[:60]}")
            for var in re.findall(r"variable\.[\w.]+", val):
                check(ALLOWED_VARS.match(var), f"{ident}: unknown variable {var}")
check(len(particle_ids) >= 30, f"expected 30+ particles, found {len(particle_ids)}")

# ---------------------------------------------------------------- steam animation controller
ac = J(RP, "animation_controllers", "joki_steam.animation_controllers.json")["animation_controllers"]["controller.animation.joki.steam"]
states = ac["states"]
check(ac["initial_state"] in states, "initial state missing")
fx_map = pe.get("particle_effects", {})
for st, sd in states.items():
    for t in sd.get("transitions", []):
        (target, cond), = t.items()
        check(target in states, f"controller: {st} -> unknown {target}")
        check(molang_ok(cond), f"controller: bad condition {cond}")
    for pe_ in sd.get("particle_effects", []):
        short = pe_["effect"]
        check(short in fx_map, f"controller state {st}: effect {short} not registered on the player")
        check(fx_map.get(short) in particle_ids, f"controller state {st}: particle {fx_map.get(short)} missing")
        pd = particle_ids.get(fx_map.get(short), {}).get("particle_effect", {}).get("components", {})
        check("minecraft:emitter_lifetime_looping" in pd, f"state {st}: {short} must loop (ends with the state)")
    keys = sorted(k for k in states if k != st)
    check(len(sd.get("transitions", [])) == len(keys), f"controller: {st} must reach every other state")
check(len(states) == 9, "expected 9 steam states")

# ---------------------------------------------------------------- player animations
anims = {}
for p, d in rp_json.items():
    if p.endswith(".animation.json"):
        anims.update(d["animations"])
HUMANOID_BONES = {"head", "body", "rightArm", "leftArm", "rightLeg", "leftLeg"}
for name, a in anims.items():
    check(name.startswith("animation.joki.player."), f"unexpected animation {name}")
    check(a.get("loop") is False and a.get("animation_length", 0) > 0, f"{name}: must be one-shot with a length")
    for bone, chans in a["bones"].items():
        check(bone in HUMANOID_BONES, f"{name}: bone {bone} is not a vanilla player bone")
        for ch, frames in chans.items():
            check(ch == "rotation", f"{name}: channel {ch}")
            times = sorted(float(t) for t in frames)
            check(times[0] == 0.0 and abs(times[-1] - a["animation_length"]) < 1e-6, f"{name}/{bone}: keyframes must span the clip")
            last = frames[max(frames, key=float)]["post"]
            check(all(x == 0 for x in last), f"{name}/{bone}: must end at rest pose")
            for f in frames.values():
                for x in f["post"]:
                    check(molang_ok(x), f"{name}: bad molang {x}")

# ---------------------------------------------------------------- sounds
sdefs = J(RP, "sounds", "sound_definitions.json")["sound_definitions"]
for ev, sd in sdefs.items():
    check(ev.startswith("joki."), f"sound {ev} outside namespace")
    for snd in sd["sounds"]:
        check(os.path.exists(os.path.join(RP, snd["name"] + ".ogg")), f"sound file {snd['name']}.ogg missing")
for ogg in glob.glob(os.path.join(RP, "sounds", "**", "*.ogg"), recursive=True):
    with open(ogg, "rb") as f:
        check(f.read(4) == b"OggS", f"{rel(ogg)} is not an Ogg file")

# ---------------------------------------------------------------- items, textures, lang
item_tex = J(RP, "textures", "item_texture.json")["texture_data"]
for k, v in item_tex.items():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {v['textures']} missing")
ITEM_EXTRA = {"minecraft:glint", "minecraft:hand_equipped", "minecraft:max_stack_size", "minecraft:display_name", "minecraft:icon", "minecraft:tags"}
bp_items = {}
for p, d in bp_json.items():
    it = d.get("minecraft:item") if isinstance(d, dict) else None
    if not it:
        continue
    ident = it["description"]["identifier"]
    bp_items[ident] = it
    for comp in it["components"]:
        check(comp in set(REF["item_components"]) | ITEM_EXTRA, f"{ident}: unknown item component {comp}")
    check(it["components"]["minecraft:icon"]["textures"]["default"] in item_tex, f"{ident}: icon not in item_texture.json")
    check(it["description"].get("menu_category", {}).get("category") in ("equipment", "items", "nature", "construction"), f"{ident}: not in creative inventory")
fruit = bp_items.get("joki:joki_fruit", {}).get("components", {})
check(fruit.get("minecraft:food", {}).get("can_always_eat") is True, "fruit must be edible at full hunger")
check(fruit.get("minecraft:use_animation") == "eat" and fruit.get("minecraft:use_modifiers", {}).get("use_duration", 0) > 0, "fruit must be eaten over time")

lang = {}
for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8"):
    if "=" in line:
        k, v = line.rstrip("\n").split("=", 1)
        lang[k] = v
for ident in bp_items:
    check(f"item.{ident}.name" in lang, f"lang key for {ident} missing")
for root in (BP, RP):
    check("pack.name" in open(os.path.join(root, "texts", "en_US.lang"), encoding="utf-8").read(), "pack.name lang")

for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True) + [os.path.join(BP, "pack_icon.png"), os.path.join(RP, "pack_icon.png")]:
    im = Image.open(p)
    check(im.mode == "RGBA", f"{rel(p)} is not RGBA")
    w, h = im.size
    check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{rel(p)} size {im.size} is not a power of two")
fruit_png = Image.open(os.path.join(RP, "textures", "items", "joki", "joki_fruit.png"))
fw, fh = fruit_png.size
check(fw >= 64 and fw == fh, "fruit texture must be square, 64px or more")
corners = [fruit_png.getpixel(c)[3] for c in ((0, 0), (fw - 1, 0), (0, fh - 1), (fw - 1, fh - 1))]
check(all(a == 0 for a in corners), "fruit texture must have a transparent background")

# ---------------------------------------------------------------- scripts <-> packs
js = {}
for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True):
    src = open(p, encoding="utf-8").read()
    js[p] = src
    for imp in re.findall(r'from "(\.[^"]+)"', src):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{rel(p)}: import {imp} not found")
    for mod in re.findall(r'from "(@minecraft/[^"]+)"', src):
        check(mod in ("@minecraft/server", "@minecraft/server-ui"), f"{rel(p)}: imports undeclared module {mod}")
alljs = "\n".join(js.values())
fx_src = js[os.path.join(BP, "scripts", "core", "fx.js")]
P_ids = re.findall(r'"(joki:[a-z_]+)"', fx_src[fx_src.index("export const P"):fx_src.index("export const S")])
S_ids = re.findall(r'"(joki\.[a-z_.]+)"', fx_src[fx_src.index("export const S"):fx_src.index("export function particle")])
check(len(P_ids) >= 20 and len(S_ids) >= 20, "fx catalog parse failed")
for pid in P_ids:
    check(pid in particle_ids, f"script particle {pid} not defined")
    pd = particle_ids.get(pid, {}).get("particle_effect", {}).get("components", {})
    check("minecraft:emitter_lifetime_once" in pd, f"script particle {pid} must be a one-shot emitter")
for sid in S_ids:
    check(sid in sdefs, f"script sound {sid} not defined")
check(set(sdefs) == set(S_ids), f"unused / missing sound events: {sorted(set(sdefs) ^ set(S_ids))}")
for m in re.findall(r"animation\.joki\.player\.\$\{name\}", alljs):
    del m
anim_names = re.search(r'anim\(p, name\)|function anim\(p, name\)', fx_src)
check(anim_names is not None, "anim() helper missing")
used_anims = set(re.findall(r'anim\(\w+, "(\w+)"\)', alljs))
check(len(used_anims) >= 8, f"expected 8+ player animations used, found {sorted(used_anims)}")
for a in used_anims:
    check(f"animation.joki.player.{a}" in anims, f"animation.joki.player.{a} missing")
effect_ids = set(re.findall(r'"minecraft:([a-z_]+)"', open(os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts")).read()))
used_effects = set(re.findall(r'(?:addEffect|removeEffect|getEffect)\(\s*"([a-z_]+)"', alljs)) | set(re.findall(r'ensureEffect\(p, "([a-z_]+)"', alljs))
used_effects |= {"speed", "strength"}
for eff in used_effects:
    check(eff in effect_ids, f"effect {eff} is not a Minecraft effect")
for item in set(re.findall(r'"(joki:[a-z_]+)"', js[os.path.join(BP, "scripts", "config.js")])):
    if item in ("joki:owner", "joki:selected", "joki:hud", "joki:welcomed", "joki:mode", "joki:heat", "joki:overheat", "joki:pvp"):
        continue
    check(item in bp_items, f"item {item} referenced by scripts but not defined")
for prop in ("joki:mode", "joki:heat", "joki:overheat"):
    check(f'"{prop}"' in alljs, f"scripts never set {prop}")
ui_src = js[os.path.join(BP, "scripts", "ui.js")]
cfg = js[os.path.join(BP, "scripts", "config.js")]
ability_ids = re.findall(r'ABILITY_ORDER = \[([^\]]+)\]', cfg)[0]
for aid in re.findall(r'"(\w+)"', ability_ids):
    check(os.path.exists(os.path.join(RP, "textures", "joki", "ui", aid + ".png")), f"menu icon {aid} missing")
for name in ("mode_1", "mode_2", "mode_3", "hud", "guide"):
    check(os.path.exists(os.path.join(RP, "textures", "joki", "ui", name + ".png")), f"menu icon {name} missing")
check("textures/items/joki/steam_valve" in ui_src and os.path.exists(os.path.join(RP, "textures/items/joki/steam_valve.png")), "valve icon path")
check(len(re.findall(r'"\w+"', ability_ids)) == 9, "expected 9 abilities")
for bad in ("applyImpulse(", "@minecraft/server-gametest", "@minecraft/debug-utilities", "runCommandAsync("):
    check(bad not in alljs, f"scripts use unsupported/unstable API: {bad}")

print(f"{count['n']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
