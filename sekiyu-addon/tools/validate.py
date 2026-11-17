"""
Static validation of the built packs (run after build.py):  python3 tools/validate.py

JSON, manifests / UUIDs / dependencies, player overrides vs. vanilla 1.26.60 (only the intended
additions), overlay geometry mirrors the vanilla humanoid skeleton, every geometry (UVs inside the
texture, parents, unique bones, animated bones exist), the held-fruit attachable (1.16.0 geometry
with a bone binding, hold poses), construct entities (BP <-> RP, properties used by render
controllers / animations), particles (textures, atlas UVs, Molang, mobile budgets), sounds, fog,
items, lang, textures, and every id the compiled scripts use.
"""
import glob
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BP = os.path.join(ROOT, "build", "Sekiyu_BP")
RP = os.path.join(ROOT, "build", "Sekiyu_RP")
VAN = os.path.join(HERE, "vanilla")
REF = json.load(open(os.path.join(VAN, "reference.json")))

errors = []
count = {"n": 0}


def check(cond, msg):
    count["n"] += 1
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
    return depth == 0 and expr.count("?") - expr.count("??") * 2 <= expr.count(":")


def walk(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
    else:
        yield o


bpj, rpj = load_all(BP), load_all(RP)
J = lambda root, *p: (bpj if root == BP else rpj)[os.path.join(root, *p)]  # noqa: E731

# ---------------------------------------------------------------- manifests
bpm, rpm = J(BP, "manifest.json"), J(RP, "manifest.json")
uuids = [bpm["header"]["uuid"], rpm["header"]["uuid"]] + [m["uuid"] for m in bpm["modules"] + rpm["modules"]]
check(len(set(uuids)) == len(uuids), "manifest UUIDs not unique")
for u in uuids:
    check(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", u), f"bad uuid {u}")
for other in glob.glob(os.path.join(ROOT, "..", "*-addon", "**", "manifest.json"), recursive=True):
    if "sekiyu-addon" in other or "node_modules" in other:
        continue
    try:
        o = json.load(open(other))
        check(not ({o["header"]["uuid"]} | {m["uuid"] for m in o.get("modules", [])}) & set(uuids), f"UUID collision with {other}")
    except Exception:  # noqa: BLE001
        pass
deps = {d.get("uuid") or d.get("module_name"): d["version"] for d in bpm["dependencies"]}
check(deps.get(rpm["header"]["uuid"]) == rpm["header"]["version"], "BP must depend on RP")
check(any(d.get("uuid") == bpm["header"]["uuid"] for d in rpm["dependencies"]), "RP must depend on BP")
for pkg, key in (("server", "@minecraft/server"), ("server-ui", "@minecraft/server-ui")):
    v = json.load(open(os.path.join(ROOT, "node_modules", "@minecraft", pkg, "package.json")))["version"]
    check(deps.get(key) == v and "-" not in v, f"{key} {deps.get(key)} must equal stable typings {v}")
check(os.path.exists(os.path.join(BP, "scripts", "main.js")), "script entry missing")

# ---------------------------------------------------------------- geometry
geos = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "minecraft:geometry" in d:
        for g in d["minecraft:geometry"]:
            geos[g["description"]["identifier"]] = (g, p, d.get("format_version"))
check(len(geos) == 9, f"expected 9 geometries, found {sorted(geos)}")
for gid, (g, p, fv) in geos.items():
    W, H = g["description"]["texture_width"], g["description"]["texture_height"]
    names = [b["name"] for b in g["bones"]]
    check(len(names) == len(set(names)), f"{gid}: duplicate bones")
    for b in g["bones"]:
        if "parent" in b:
            check(b["parent"] in names, f"{gid}: bad parent {b['parent']}")
        for c in b.get("cubes", []):
            check(all(s >= 0 for s in c["size"]), f"{gid}: negative size")
            for face, uv in c["uv"].items():
                u, v = uv["uv"]
                w, h = uv["uv_size"]
                check(0 <= u and u + w <= W and 0 <= v and v + h <= H, f"{gid}: {face} uv outside texture")
    tex = os.path.join(RP, "textures", "entity", "sekiyu", os.path.basename(p).replace(".geo.json", ".png"))
    if "fruit_relic" in p:
        tex = os.path.join(RP, "textures", "entity", "sekiyu", "fruit.png")
    if check(os.path.exists(tex), f"{gid}: texture {tex} missing"):
        check(Image.open(tex).size == (W, H), f"{gid}: texture size != geometry texture_width/height")
fruit_geo = geos["geometry.sekiyu.fruit"][0]
check(geos["geometry.sekiyu.fruit"][2] == "1.16.0", "held fruit geometry must be format 1.16.0 (bone binding)")
check(fruit_geo["bones"][0].get("binding") == "q.item_slot_to_bone_name(c.item_slot)", "held fruit root bone must bind to the hand")
check(not any("binding" in b for b in geos["geometry.sekiyu.fruit_relic"][0]["bones"]), "relic geometry must not bind")
check(sum(len(b.get("cubes", [])) for b in fruit_geo["bones"]) >= 120, "fruit model should be detailed (120+ cubes)")
check(Image.open(os.path.join(RP, "textures", "entity", "sekiyu", "fruit.png")).size[0] <= 256, "fruit texture must fit the 256x256 memory budget")
HUMANOID = {"root": None, "waist": "root", "body": "waist", "head": "body", "rightArm": "body", "leftArm": "body", "rightLeg": "root", "leftLeg": "root"}
ob = {b["name"]: b for b in geos["geometry.sekiyu.oil_body"][0]["bones"]}
for bn, par in HUMANOID.items():
    check(bn in ob and ob[bn].get("parent") == par, f"oil body overlay: humanoid bone {bn} must have parent {par}")

# ---------------------------------------------------------------- animations
anims = {}
for p, d in rpj.items():
    if p.endswith(".animation.json"):
        anims.update(d["animations"])
bone_owner = {}
for gid, (g, _, _) in geos.items():
    for b in g["bones"]:
        bone_owner.setdefault(b["name"], set()).add(gid)
PLAYER_BONES = set(HUMANOID)
for name, a in anims.items():
    for bone, chans in a.get("bones", {}).items():
        check(bone in bone_owner or bone in PLAYER_BONES, f"{name}: animates unknown bone {bone}")
        for val in walk(chans):
            check(molang_ok(val), f"{name}/{bone}: bad molang {val}")
    if name.startswith("animation.sekiyu.player."):
        check(a.get("loop") is False and set(a["bones"]) <= PLAYER_BONES, f"{name}: player clip must be one-shot on vanilla bones")

# ---------------------------------------------------------------- render controllers
rcs = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "render_controllers" in d:
        rcs.update(d["render_controllers"])

# ---------------------------------------------------------------- player overrides
van_bp = json.load(open(os.path.join(VAN, "player.json")))["minecraft:entity"]
pl = J(BP, "entities", "player.json")["minecraft:entity"]
check(pl["components"] == van_bp["components"] and pl.get("events") == van_bp.get("events") and pl.get("component_groups") == van_bp.get("component_groups"),
      "player.json diverges from vanilla")
props = pl["description"]["properties"]
check(props["sekiyu:form"]["range"] == [0, 3] and props["sekiyu:burning"]["type"] == "bool" and all(v["client_sync"] for v in props.values()), "player properties")
van_rp = json.load(open(os.path.join(VAN, "player.entity.json")))["minecraft:client_entity"]["description"]
pe = J(RP, "entity", "player.entity.json")["minecraft:client_entity"]["description"]
for section in ("materials", "textures", "geometry", "animations"):
    for k, val in van_rp[section].items():
        check(pe[section].get(k) == val, f"player.entity.json lost vanilla {section}.{k}")
for section in ("initialize", "pre_animation"):
    check(pe["scripts"][section][: len(van_rp["scripts"][section])] == van_rp["scripts"][section], f"vanilla {section} changed")
    for line in pe["scripts"][section]:
        check(molang_ok(line) and line.strip().endswith(";"), f"bad molang {line[:60]}")
check(pe["scripts"]["animate"][: len(van_rp["scripts"]["animate"])] == van_rp["scripts"]["animate"], "vanilla animate list changed")
for entry in pe["scripts"]["animate"]:
    k = entry if isinstance(entry, str) else list(entry)[0]
    check(k in pe["animations"], f"player animate refers to unknown {k}")
    tgt = pe["animations"].get(k, "")
    check(tgt.startswith("controller.") or tgt in anims or tgt in van_rp["animations"].values(), f"player animation {tgt} not defined")
van_rc = json.load(open(os.path.join(VAN, "player.render_controllers.json")))["render_controllers"]
swap = {"controller.render.player.third_person": "controller.render.sekiyu.player.third_person",
        "controller.render.player.first_person": "controller.render.sekiyu.player.first_person"}
for vname, sname in swap.items():
    mine = rcs.get(sname, {})
    check(mine.get("geometry") == van_rc[vname]["geometry"] and mine.get("textures") == van_rc[vname]["textures"], f"{sname} must keep vanilla geometry/textures")
    check(len(mine.get("part_visibility", [])) == len(van_rc[vname]["part_visibility"]), f"{sname} part_visibility length")
    for a, b in zip(mine.get("part_visibility", []), van_rc[vname]["part_visibility"]):
        check(list(a) == list(b), f"{sname}: part order changed")
        val = list(a.values())[0]
        check(val is False or "sekiyu_form != 3" in str(val), f"{sname}: part {list(a)[0]} must hide while dissolved")
    check(all("this" in v for v in mine.get("overlay_color", {}).values()), f"{sname}: overlay must keep `this` (hurt flash)")
for mine, theirs in zip(pe["render_controllers"], van_rp["render_controllers"]):
    (mk, mc), = mine.items()
    (vk, vc), = theirs.items()
    check(mk == swap.get(vk, vk) and mc == vc, f"player rc {vk} -> {mk}")
for entry in pe["render_controllers"]:
    (k, cond), = entry.items()
    check(k in rcs or k.startswith("controller.render.player."), f"player rc {k} undefined")
    check(molang_ok(cond), f"bad rc condition {cond}")
    rc = rcs.get(k, {})
    if k.startswith("controller.render.sekiyu.") and "Geometry.default" not in rc.get("geometry", ""):
        check(rc["geometry"].split(".", 1)[1] in pe["geometry"], f"{k}: geometry key missing")
        for t in rc["arrays"]["textures"]["Array.skins"]:
            check(t.split(".", 1)[1] in pe["textures"], f"{k}: texture key {t} missing")
        check(pe["materials"].get("sekiyu_oil") == "entity_emissive", "sekiyu_oil material")
for k, v in pe.get("particle_effects", {}).items():
    if v.startswith("sekiyu:"):
        check(os.path.exists(os.path.join(RP, "particles", "sekiyu", v.split(":")[1] + ".json")), f"player particle {v} missing")

# ---------------------------------------------------------------- animation controllers
acs = {}
for p, d in rpj.items():
    if isinstance(d, dict) and "animation_controllers" in d:
        acs.update(d["animation_controllers"])
for name, ac in acs.items():
    st = ac["states"]
    check(ac["initial_state"] in st, f"{name}: initial state")
    for sn, sd in st.items():
        for t in sd.get("transitions", []):
            (to, cond), = t.items()
            check(to in st and molang_ok(cond), f"{name}: bad transition {sn}->{to}")

# ---------------------------------------------------------------- particles
particles = {}
atlas = Image.open(os.path.join(RP, "textures", "particle", "sekiyu_oil.png"))
ALLOWED = re.compile(r"^variable\.(particle_age|particle_lifetime|particle_random_[1-4]|emitter_age|direction(\.[xyz])?|power|radius)$")
for p, d in rpj.items():
    if not (isinstance(d, dict) and "particle_effect" in d):
        continue
    desc = d["particle_effect"]["description"]
    ident = desc["identifier"]
    particles[ident] = d
    check(os.path.exists(os.path.join(RP, desc["basic_render_parameters"]["texture"] + ".png")), f"{ident}: texture")
    comps = d["particle_effect"]["components"]
    bb = comps.get("minecraft:particle_appearance_billboard", {})
    uv = bb.get("uv", {})
    check(uv.get("texture_width") == atlas.size[0], f"{ident}: atlas size")
    fb = uv.get("flipbook")
    if fb:
        check(fb["base_UV"][0] + fb["step_UV"][0] * (fb["max_frame"] - 1) + fb["size_UV"][0] <= atlas.size[0], f"{ident}: flipbook outside atlas")
    rate = comps.get("minecraft:emitter_rate_steady")
    if rate:
        check(rate["max_particles"] <= 60, f"{ident}: too many particles for mobile")
        check("minecraft:emitter_local_space" in comps, f"{ident}: bound emitter must be local space")
    inst = comps.get("minecraft:emitter_rate_instant")
    if inst and isinstance(inst["num_particles"], int):
        check(inst["num_particles"] <= 40, f"{ident}: burst too large for mobile")
    for val in walk(comps):
        if isinstance(val, str):
            check(molang_ok(val), f"{ident}: molang {val[:50]}")
            for var in re.findall(r"variable\.[\w.]+", val):
                check(ALLOWED.match(var), f"{ident}: unknown variable {var}")
check(len(particles) >= 28, f"expected 28+ particles, found {len(particles)}")

# ---------------------------------------------------------------- constructs
bp_ents = {}
for p, d in bpj.items():
    e = d.get("minecraft:entity") if isinstance(d, dict) else None
    if e and e["description"]["identifier"] != "minecraft:player":
        bp_ents[e["description"]["identifier"]] = e
check(len(bp_ents) == 6, f"expected 6 construct entities, found {sorted(bp_ents)}")
client = {}
for p, d in rpj.items():
    ce = d.get("minecraft:client_entity") if isinstance(d, dict) else None
    if ce:
        client[ce["description"]["identifier"]] = ce["description"]
for ident, e in bp_ents.items():
    comps = e["components"]
    for comp in comps:
        check(comp in REF["entity_components"], f"{ident}: unknown component {comp}")
    check("sekiyu_construct" in comps["minecraft:type_family"]["family"], f"{ident}: construct family")
    check(comps["minecraft:timer"]["time_down_event"]["event"] in e["events"], f"{ident}: despawn event")
    check(comps["minecraft:physics"] == {"has_gravity": False, "has_collision": False}, f"{ident}: constructs must not fall or collide")
    cd = client.get(ident)
    if not check(cd is not None, f"{ident}: no client entity"):
        continue
    check(cd["geometry"]["default"] in geos, f"{ident}: geometry missing")
    for t in cd["textures"].values():
        check(os.path.exists(os.path.join(RP, t + ".png")), f"{ident}: texture {t}")
    props = e["description"].get("properties", {})
    for rc in cd["render_controllers"]:
        check(rc in rcs, f"{ident}: rc {rc}")
        if "construct" in rc:
            check("sekiyu:burning" in props and "burning" in cd["textures"], f"{ident}: burning texture/property needed by {rc}")
    for an in cd["animations"].values():
        check(an in anims or an in acs, f"{ident}: animation {an} missing")
        body = json.dumps(anims.get(an) or acs.get(an))
        for prop in re.findall(r"query\.property\('([^']+)'\)", body):
            check(prop in props, f"{ident}: {an} reads undefined property {prop}")
    for k, v in cd.get("particle_effects", {}).items():
        check(v in particles, f"{ident}: particle {v}")
check(bp_ents["sekiyu:oil_pool"]["description"]["properties"]["sekiyu:radius"]["type"] == "float", "pool radius property")

# ---------------------------------------------------------------- attachable
att = J(RP, "attachables", "sekiyu_fruit.attachable.json")["minecraft:attachable"]["description"]
check(att["identifier"] == "sekiyu:sekiyu_fruit" and att["geometry"]["default"] == "geometry.sekiyu.fruit", "attachable target")
for k, v in att["animations"].items():
    check(v in anims, f"attachable animation {v}")
fp = anims["animation.sekiyu.fruit.hold_first_person"]["bones"]["fruit"]
check(0.2 <= fp["scale"] <= 0.5, "first-person fruit scale keeps it out of the crosshair")
for loc in ("vapor_a", "vapor_b", "vapor_c"):
    check(any(loc in b.get("locators", {}) for b in fruit_geo["bones"]), f"locator {loc} missing")

# ---------------------------------------------------------------- items, fog, sounds, lang, textures
items = {}
for p, d in bpj.items():
    it = d.get("minecraft:item") if isinstance(d, dict) else None
    if it:
        items[it["description"]["identifier"]] = it
        for comp in it["components"]:
            check(comp in set(REF["item_components"]) | {"minecraft:glint", "minecraft:hand_equipped", "minecraft:max_stack_size", "minecraft:display_name", "minecraft:icon", "minecraft:tags"}, f"unknown item component {comp}")
check(set(items) == {"sekiyu:sekiyu_fruit", "sekiyu:crude_core"}, "items")
check(items["sekiyu:sekiyu_fruit"]["components"]["minecraft:food"]["can_always_eat"] is True, "fruit edible when full")
itex = J(RP, "textures", "item_texture.json")["texture_data"]
for v in itex.values():
    check(os.path.exists(os.path.join(RP, v["textures"] + ".png")), f"item texture {v}")
fog = J(RP, "fogs", "sekiyu_inferno.json")["minecraft:fog_settings"]
check(fog["description"]["identifier"] == "sekiyu:inferno_fog", "fog id")
sdefs = J(RP, "sounds", "sound_definitions.json")["sound_definitions"]
for ev, sd in sdefs.items():
    for snd in sd["sounds"]:
        f = os.path.join(RP, snd["name"] + ".ogg")
        check(os.path.exists(f) and open(f, "rb").read(4) == b"OggS", f"sound {snd['name']}")
lang = dict(line.rstrip("\n").split("=", 1) for line in open(os.path.join(RP, "texts", "en_US.lang"), encoding="utf-8") if "=" in line)
for ident in list(items) + list(bp_ents):
    check(f"item.{ident}.name" in lang or f"entity.{ident}.name" in lang, f"lang {ident}")
for p in glob.glob(os.path.join(RP, "textures", "**", "*.png"), recursive=True):
    im = Image.open(p)
    w, h = im.size
    check(im.mode == "RGBA" and w & (w - 1) == 0 and h & (h - 1) == 0, f"{p}: RGBA power-of-two")
fruit_png = Image.open(os.path.join(RP, "textures", "items", "sekiyu", "sekiyu_fruit.png"))
check(fruit_png.getpixel((0, 0))[3] == 0, "fruit icon background transparent")

# ---------------------------------------------------------------- scripts <-> packs
js = {p: open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(BP, "scripts", "**", "*.js"), recursive=True)}
alljs = "\n".join(js.values())
for p, src in js.items():
    for imp in re.findall(r'from "(\.[^"]+)"', src):
        check(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), imp))), f"{p}: import {imp}")
    for mod in re.findall(r'from "(@minecraft/[^"]+)"', src):
        check(mod in ("@minecraft/server", "@minecraft/server-ui"), f"undeclared module {mod}")
fx = js[os.path.join(BP, "scripts", "core", "fx.js")]
P_ids = re.findall(r'"(sekiyu:[a-z_]+)"', fx[fx.index("export const P"):fx.index("export const S")])
S_ids = re.findall(r'"(sekiyu\.[a-z_.]+)"', fx[fx.index("export const S"):fx.index("export function particle")])
for pid in P_ids:
    check(pid in particles and "minecraft:emitter_lifetime_once" in particles[pid]["particle_effect"]["components"], f"script particle {pid}")
check(set(S_ids) == set(sdefs), f"sound events mismatch {sorted(set(S_ids) ^ set(sdefs))}")
for a in set(re.findall(r'anim\(\w+, "(\w+)"\)', alljs)):
    check(f"animation.sekiyu.player.{a}" in anims, f"player clip {a} missing")
for a in set(re.findall(r'entityAnim\(\w+, "([\w.]+)"\)', alljs)):
    check(a in anims, f"entity clip {a} missing")
cfg = js[os.path.join(BP, "scripts", "config.js")]
for ident in re.findall(r'"(sekiyu:[a-z_]+)"', cfg[cfg.index("export const ENT"):cfg.index("export const CONSTRUCT_FAMILY")]):
    check(ident in bp_ents, f"script entity {ident} not defined")
order = re.findall(r'"(\w+)"', re.search(r"ABILITY_ORDER = \[([^\]]+)\]", cfg).group(1))
check(len(order) == 8, "exactly eight abilities")
for name in order + ["logia", "hud", "guide"]:
    check(os.path.exists(os.path.join(RP, "textures", "sekiyu", "ui", name + ".png")), f"menu icon {name}")
effect_ids = set(re.findall(r'"minecraft:([a-z_]+)"', open(os.path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts")).read()))
for eff in set(re.findall(r'(?:addEffect|removeEffect|getEffect)\(\s*"([a-z_]+)"', alljs)) | {"invisibility", "speed", "resistance"}:
    check(eff in effect_ids, f"effect {eff}")
check('FOG_ID = "sekiyu:inferno_fog"' in alljs and "fog @s push ${FOG_ID}" in alljs, "inferno fog id used by scripts")
for bad in ("applyImpulse(", "runCommandAsync(", "@minecraft/server-gametest"):
    check(bad not in alljs, f"unsupported API {bad}")
code = re.sub(r"/\*.*?\*/|//[^\n]*", "", alljs, flags=re.S).lower()
check("fuel" not in code and "ammo" not in code and "oilamount" not in code, "no oil gauge / ammunition system")

print(f"{count['n']} checks, {len(errors)} errors")
for e in errors:
    print("  ERROR:", e)
sys.exit(1 if errors else 0)
