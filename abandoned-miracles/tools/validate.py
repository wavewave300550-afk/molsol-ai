"""
Static validation of the built packs.

    python3 tools/validate.py [--mct] [--json out.json]

Every check below reads the files that actually ship (packs/ and dist/), not the
generators. It verifies syntax, cross-references and budgets; it cannot tell
whether the game renders or plays anything - that is recorded separately in
TEST_REPORT.md. `--mct` additionally runs Mojang's Minecraft Creator Tools
validator and fails on any error it reports.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import struct
import subprocess
import sys
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from kit import molang, vanilla           # noqa: E402
from kit import pack as K                 # noqa: E402
from PIL import Image                     # noqa: E402

OUT = os.path.abspath(os.environ.get("ABM_OUT", ROOT))
PACKS = os.path.join(OUT, "packs")
BP = os.path.join(PACKS, "behavior_packs", "The_Abandoned_Miracles_BP")
RP = os.path.join(PACKS, "resource_packs", "The_Abandoned_Miracles_RP")
DIST = os.path.join(OUT, "dist")
MATERIALS = {"entity_alphatest", "entity_emissive_alpha", "entity_alphablend", "entity", "entity_emissive"}
PARTICLE_MATERIALS = {"particles_alpha", "particles_blend", "particles_add", "particles_opaque"}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class Report:
    def __init__(self):
        self.passed = 0
        self.failures = []
        self.warnings = []
        self.sections = defaultdict(lambda: [0, 0])
        self.section = "general"

    def begin(self, name):
        self.section = name

    def ok(self, cond, msg):
        self.sections[self.section][0 if cond else 1] += 1
        if cond:
            self.passed += 1
        else:
            self.failures.append(f"[{self.section}] {msg}")
        return cond

    def warn(self, msg):
        self.warnings.append(f"[{self.section}] {msg}")


R = Report()


def rel(p):
    return os.path.relpath(p, PACKS).replace(os.sep, "/")


def files(base, ext=None):
    out = []
    for root, dirs, names in os.walk(base):
        dirs.sort()
        for n in sorted(names):
            if ext is None or n.endswith(ext):
                out.append(os.path.join(root, n))
    return out


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def molang_strings(node, path=""):
    """Yield (path, text) for every string in a JSON subtree that looks like a Molang expression."""
    if isinstance(node, str):
        if re.search(r"(\bq\.|\bquery\.|\bv\.|\bvariable\.|math\.|[<>=?*+]|^-?\d)", node) and not node.startswith(("textures/", "sounds/", "geometry.", "animation.", "controller.", "abm", "minecraft:")):
            yield path, node
    elif isinstance(node, list):
        for i, x in enumerate(node):
            yield from molang_strings(x, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, x in node.items():
            yield from molang_strings(x, f"{path}/{k}")


def check_molang(where, node, skip_keys=()):
    for p, text in molang_strings(node):
        if any(p.endswith("/" + k) or f"/{k}/" in p or f"/{k}[" in p for k in skip_keys):
            continue
        try:
            molang.parse(text)
            R.ok(True, "")
        except molang.MolangError as e:
            R.ok(False, f"{where}{p}: {e}")


# --------------------------------------------------------------------------- checks

def check_json():
    R.begin("json")
    n = 0
    for base in (BP, RP):
        for f in files(base, ".json"):
            try:
                load(f)
                R.ok(True, "")
            except Exception as e:                      # noqa: BLE001
                R.ok(False, f"{rel(f)}: {e}")
            n += 1
    return n


def check_manifests():
    R.begin("manifest")
    bp, rp = load(os.path.join(BP, "manifest.json")), load(os.path.join(RP, "manifest.json"))
    uuids = []
    for name, m in (("BP", bp), ("RP", rp)):
        R.ok(m.get("format_version") == 2, f"{name}: format_version must be 2")
        h = m["header"]
        R.ok(h.get("min_engine_version") == K.MIN_ENGINE, f"{name}: min_engine_version {h.get('min_engine_version')} != {K.MIN_ENGINE}")
        R.ok(isinstance(h.get("version"), list) and len(h["version"]) == 3, f"{name}: header.version must be [a,b,c]")
        uuids.append(h["uuid"])
        for mod in m["modules"]:
            uuids.append(mod["uuid"])
            R.ok(mod.get("version") == h["version"], f"{name}: module version differs from header")
        R.ok(os.path.exists(os.path.join(BP if name == "BP" else RP, "pack_icon.png")), f"{name}: pack_icon.png missing")
    for u in uuids:
        R.ok(bool(UUID_RE.match(u)), f"malformed UUID {u}")
    R.ok(len(set(uuids)) == len(uuids), "pack UUIDs are not unique")
    deps = bp.get("dependencies", [])
    R.ok(any(d.get("uuid") == rp["header"]["uuid"] for d in deps), "BP does not depend on the RP header UUID")
    R.ok(any(d.get("uuid") == bp["header"]["uuid"] for d in rp.get("dependencies", [])), "RP does not depend on the BP header UUID")
    mods = {d["module_name"]: d["version"] for d in deps if "module_name" in d}
    R.ok(mods.get("@minecraft/server") == K.SERVER_VERSION, f"@minecraft/server {mods.get('@minecraft/server')} != {K.SERVER_VERSION}")
    R.ok(mods.get("@minecraft/server-ui") == K.SERVER_UI_VERSION, f"@minecraft/server-ui {mods.get('@minecraft/server-ui')} != {K.SERVER_UI_VERSION}")
    for name, v in mods.items():
        R.ok("beta" not in v and "preview" not in v and "rc" not in v, f"{name} {v} is not a stable module version")
        R.ok(name in ("@minecraft/server", "@minecraft/server-ui"), f"unexpected script module {name}")
    script = [m for m in bp["modules"] if m["type"] == "script"]
    R.ok(len(script) == 1 and os.path.exists(os.path.join(BP, script[0]["entry"])), "script module entry file missing")
    pkg = load(os.path.join(ROOT, "package.json"))["devDependencies"]
    R.ok(pkg["@minecraft/server"] == K.SERVER_VERSION and pkg["@minecraft/server-ui"] == K.SERVER_UI_VERSION,
         "typings in package.json differ from the manifest's module versions")
    return bp, rp


def check_script():
    R.begin("script")
    p = os.path.join(BP, "scripts", "main.js")
    src = open(p, encoding="utf-8").read()
    imports = set(re.findall(r'^\s*import\s[^;\n]*?from\s*"([^"]+)"', src, re.M)) | set(re.findall(r'^\s*import\s*"([^"]+)"', src, re.M))
    R.ok(imports <= {"@minecraft/server", "@minecraft/server-ui"}, f"bundle imports unexpected modules: {sorted(imports)}")
    R.ok("eval(" not in src and "new Function(" not in src, "bundle uses eval / Function")
    R.ok("runTimeout(" not in src, "bundle uses system.runTimeout (hazards must use the encounter timeline)")
    R.ok(len(src) < 1_000_000, f"bundle is {len(src)} bytes")
    for api in ("setBlockType", "setBlockPermutation", "fillBlocks", ".setType(", "setPermutation("):
        R.ok(api not in src, f"bundle calls {api} (terrain must never be edited by an encounter)")
    return src


def check_entities():
    R.begin("entities")
    bp_ents, client = {}, {}
    for f in files(os.path.join(BP, "entities"), ".json"):
        e = load(f)["minecraft:entity"]
        ident = e["description"]["identifier"]
        R.ok(ident.startswith("abm:"), f"{rel(f)}: identifier {ident} outside the abm namespace")
        R.ok(ident not in bp_ents, f"duplicate behaviour entity {ident}")
        bp_ents[ident] = e
        props = e["description"].get("properties", {})
        R.ok(len(props) <= 32, f"{ident}: {len(props)} properties (max 32)")
        for k, pr in props.items():
            R.ok(k.startswith("abm:") and pr.get("client_sync") is True, f"{ident}: property {k} must be namespaced and client_sync")
            if pr["type"] in ("int", "float"):
                R.ok(pr["range"][0] <= pr["default"] <= pr["range"][1], f"{ident}: property {k} default outside range")
        comps = e.get("components", {})
        loot = comps.get("minecraft:loot", {}).get("table")
        if loot:
            R.ok(os.path.exists(os.path.join(BP, loot)), f"{ident}: loot table {loot} missing")
        groups = set(e.get("component_groups", {}))
        for ev, body in e.get("events", {}).items():
            for op in ("add", "remove"):
                for g in body.get(op, {}).get("component_groups", []):
                    R.ok(g in groups, f"{ident}: event {ev} refers to missing component group {g}")
        R.ok(e["description"].get("is_spawnable") is False, f"{ident}: must not be naturally spawnable / have a spawn egg")
        R.ok(not os.path.exists(os.path.join(BP, "spawn_rules")), "spawn_rules present: bosses must never spawn on their own")
    for f in files(os.path.join(RP, "entity"), ".json"):
        d = load(f)["minecraft:client_entity"]["description"]
        client[d["identifier"]] = d
    R.ok(set(bp_ents) == set(client), f"behaviour/client entity mismatch: {sorted(set(bp_ents) ^ set(client))}")
    return bp_ents, client


def check_geometry():
    R.begin("geometry")
    geos = {}
    for f in files(os.path.join(RP, "models"), ".json"):
        j = load(f)
        R.ok(j.get("format_version") == "1.12.0", f"{rel(f)}: format_version")
        for g in j["minecraft:geometry"]:
            d = g["description"]
            ident = d["identifier"]
            R.ok(ident not in geos, f"duplicate geometry {ident}")
            names = [b["name"] for b in g["bones"]]
            R.ok(len(names) == len(set(names)), f"{ident}: duplicate bone names")
            seen = set()
            cubes = 0
            locs = []
            for b in g["bones"]:
                if "parent" in b:
                    R.ok(b["parent"] in seen, f"{ident}: bone {b['name']} declared before its parent {b['parent']}")
                seen.add(b["name"])
                locs += list(b.get("locators", {}))
                for c in b.get("cubes", []):
                    cubes += 1
                    for face, uv in c.get("uv", {}).items():
                        x0, y0 = uv["uv"]
                        x1, y1 = x0 + uv["uv_size"][0], y0 + uv["uv_size"][1]
                        inside = all(0 <= v <= d["texture_width"] for v in (x0, x1)) and all(0 <= v <= d["texture_height"] for v in (y0, y1))
                        if not inside:
                            R.ok(False, f"{ident}: {b['name']} {face} UV outside the texture")
            R.ok(len(locs) == len(set(locs)), f"{ident}: duplicate locator names")
            R.ok(cubes <= 480, f"{ident}: {cubes} cubes exceeds the 480-cube budget")
            R.ok(len(names) <= 120, f"{ident}: {len(names)} bones exceeds the 120-bone budget")
            geos[ident] = {"bones": set(names), "locators": set(locs), "tw": d["texture_width"], "th": d["texture_height"],
                           "cubes": cubes, "file": f}
    return geos


def check_client(client, geos, anims, ctrls, rcs, particles, sounds):
    R.begin("client entities")
    use = defaultdict(set)                 # animation / controller id -> entity identifiers
    for ident, d in client.items():
        gid = d["geometry"]["default"]
        if not R.ok(gid in geos, f"{ident}: geometry {gid} not found"):
            continue
        g = geos[gid]
        for key, tex in d["textures"].items():
            p = os.path.join(RP, tex + ".png")
            if R.ok(os.path.exists(p), f"{ident}: texture {tex}.png missing"):
                w, h = Image.open(p).size
                R.ok((w, h) == (g["tw"], g["th"]), f"{ident}: texture is {w}x{h} but geometry expects {g['tw']}x{g['th']}")
                R.ok(w <= 512 and h <= 512 and (w & (w - 1)) == 0 and (h & (h - 1)) == 0, f"{ident}: texture {w}x{h} not power-of-two <= 512")
        for key, mat in d["materials"].items():
            R.ok(mat in MATERIALS, f"{ident}: unknown material {mat}")
        for rc in d["render_controllers"]:
            R.ok(rc in rcs, f"{ident}: render controller {rc} not found")
        amap = d.get("animations", {})
        for short, full in amap.items():
            R.ok(full in anims or full in ctrls, f"{ident}: animation '{short}' -> {full} not found")
            use[full].add(ident)
        for a in d.get("scripts", {}).get("animate", []):
            name = a if isinstance(a, str) else next(iter(a))
            R.ok(name in amap, f"{ident}: scripts.animate references undefined '{name}'")
        for short, pid in d.get("particle_effects", {}).items():
            R.ok(pid in particles, f"{ident}: particle_effects.{short} -> {pid} not found")
        for short, sid in d.get("sound_effects", {}).items():
            R.ok(sid in sounds, f"{ident}: sound_effects.{short} -> {sid} not defined")
        check_molang(f"{ident} scripts", d.get("scripts", {}), skip_keys=("animate",))
        # q.life_time / q.anim_time only count inside an animation; in entity scripts they read 0
        for script in d.get("scripts", {}).get("pre_animation", []) + d.get("scripts", {}).get("initialize", []):
            R.ok(not re.search(r"\bq(uery)?\.(life_time|anim_time)\b", script), f"{ident}: animation-only time query in an entity script: {script}")
        # walk cycles: the query is the limb-swing accumulator (four units per block), never used raw
        for script in d.get("scripts", {}).get("pre_animation", []):
            if "modified_distance_moved" in script:
                R.ok("modified_distance_moved * 0.25" in script, f"{ident}: q.modified_distance_moved used without the 0.25 block conversion")
        for a in d.get("scripts", {}).get("animate", []):
            if isinstance(a, dict):
                check_molang(f"{ident} animate", list(a.values()))
    return use


def check_animations(client, geos, use):
    R.begin("animations")
    anims, ctrls = {}, {}
    for f in files(os.path.join(RP, "animations"), ".json"):
        for name, a in load(f)["animations"].items():
            R.ok(name not in anims, f"duplicate animation {name}")
            anims[name] = a
    for f in files(os.path.join(RP, "animation_controllers"), ".json"):
        for name, c in load(f)["animation_controllers"].items():
            R.ok(name not in ctrls, f"duplicate animation controller {name}")
            ctrls[name] = c
    return anims, ctrls


def check_animation_bodies(client, geos, anims, ctrls, use):
    R.begin("animations")
    for name, a in anims.items():
        users = use.get(name, set())
        if not R.ok(bool(users), f"{name}: not used by any client entity"):
            continue
        length = a.get("animation_length")
        for ident in users:
            d = client[ident]
            g = geos.get(d["geometry"]["default"])
            if not g:
                continue
            for bone in a.get("bones", {}):
                R.ok(bone in g["bones"], f"{name}: bone '{bone}' does not exist in {d['geometry']['default']}")
            for field, table in (("particle_effects", d.get("particle_effects", {})), ("sound_effects", d.get("sound_effects", {}))):
                for t, evs in a.get(field, {}).items():
                    for ev in (evs if isinstance(evs, list) else [evs]):
                        R.ok(ev["effect"] in table, f"{name}: {field} '{ev['effect']}' not declared by {ident}")
                        if "locator" in ev:
                            R.ok(ev["locator"] in g["locators"], f"{name}: locator '{ev['locator']}' missing in {d['geometry']['default']}")
                    if length is not None:
                        R.ok(float(t) <= length + 1e-6, f"{name}: {field} at {t}s is after the end ({length}s)")
        for bone, chans in a.get("bones", {}).items():
            for ch, val in chans.items():
                if isinstance(val, dict):
                    times = [float(t) for t in val]
                    R.ok(times == sorted(times), f"{name}: {bone}.{ch} keyframes out of order")
                    if length is not None:
                        R.ok(max(times) <= length + 1e-6, f"{name}: {bone}.{ch} has a keyframe after the end")
        check_molang(name, {k: v for k, v in a.items() if k in ("bones", "anim_time_update", "blend_weight")})
        # schema rules the game enforces per FILE: one violation discards every animation in it
        R.ok("bones" not in a or len(a["bones"]) > 0, f"{name}: empty 'bones' (the game rejects the whole file)")
        for bone, chans in a.get("bones", {}).items():
            R.ok(isinstance(chans, dict) and len(chans) > 0, f"{name}: bone {bone} has no channel")
        for field in ("sound_effects", "particle_effects", "timeline"):
            R.ok(field not in a or len(a[field]) > 0, f"{name}: empty '{field}'")
    for name, c in ctrls.items():
        users = use.get(name, set())
        R.ok(bool(users), f"{name}: not used by any client entity")
        states = c["states"]
        R.ok(c.get("initial_state") in states, f"{name}: initial_state missing")
        for sname, st in states.items():
            for ident in users:
                amap = client[ident].get("animations", {})
                for a in st.get("animations", []):
                    key = a if isinstance(a, str) else next(iter(a))
                    R.ok(key in amap, f"{name}.{sname}: animation '{key}' not declared by {ident}")
            for tr in st.get("transitions", []):
                for target, cond in tr.items():
                    R.ok(target in states, f"{name}.{sname}: transition to unknown state {target}")
                    # q.anim_time / q.life_time are 0 outside an animation: such a transition never fires
                    R.ok(not re.search(r"\b(anim_time|life_time)\b", str(cond)),
                         f"{name}.{sname}: transition uses an animation-only query ({cond})")
            if not st.get("transitions"):
                R.ok(sname in ("death", "dead", "done"), f"{name}.{sname}: state has no exit")
        # every state must be reachable from the initial state
        reach, todo = {c["initial_state"]}, [c["initial_state"]]
        while todo:
            for tr in states[todo.pop()].get("transitions", []):
                for target in tr:
                    if target in states and target not in reach:
                        reach.add(target)
                        todo.append(target)
        R.ok(reach == set(states), f"{name}: unreachable states {sorted(set(states) - reach)}")
        check_molang(name, c)


def check_facing(client):
    """Every boss (and every helper the script turns) faces by the published yaw, not by engine rotation."""
    R.begin("facing")
    turned = {"abm:vesperra", "abm:cantor_xiii", "abm:nomos", "abm:orison", "abm:vesperra_heir", "abm:orison_shadow"}
    for f in files(os.path.join(BP, "entities"), ".json"):
        e = load(f)["minecraft:entity"]
        ident = e["description"]["identifier"]
        if ident not in turned:
            continue
        prop = e["description"].get("properties", {}).get("abm:yaw", {})
        R.ok(prop.get("type") == "float" and prop.get("client_sync") is True and prop.get("range") == [-180.0, 180.0],
             f"{ident}: property abm:yaw missing or not a synced float in [-180, 180]")
        R.ok("minecraft:body_rotation_always_follows_head" not in e.get("components", {}),
             f"{ident}: body_rotation_always_follows_head pins the body to the head yaw")
        d = client.get(ident, {})
        sc = d.get("scripts", {})
        R.ok("face" in d.get("animations", {}) and "face" in sc.get("animate", []), f"{ident}: no always-on facing animation")
        R.ok(any("v.yaw" in s for s in sc.get("initialize", [])) and any(s.startswith("v.yaw =") for s in sc.get("pre_animation", [])),
             f"{ident}: v.yaw is not initialised and updated")


def check_render_controllers(client, geos):
    R.begin("render controllers")
    rcs = {}
    for f in files(os.path.join(RP, "render_controllers"), ".json"):
        rcs.update(load(f)["render_controllers"])
    for name, rc in rcs.items():
        users = [d for d in client.values() if name in d["render_controllers"]]
        for d in users:
            g = geos.get(d["geometry"]["default"])
            if not g:
                continue
            for m in rc.get("materials", []):
                for pat, ref in m.items():
                    key = ref.split(".", 1)[1]
                    # The game resolves every Material.<name> a controller mentions, whether or not the
                    # bone pattern matches anything on this entity: all of them must be declared.
                    R.ok(key in d["materials"], f"{name}: material '{key}' not declared by {d['identifier']}")
            for pv in rc.get("part_visibility", []):
                for pat in pv:
                    R.ok(pat == "*" or any(fnmatch.fnmatch(b, pat) for b in g["bones"]),
                         f"{name}: part_visibility pattern '{pat}' matches no bone of {d['identifier']}")
        check_molang(name, rc.get("part_visibility", []))
    return rcs


def check_particles():
    R.begin("particles")
    out = {}
    for f in files(os.path.join(RP, "particles"), ".json"):
        p = load(f)["particle_effect"]
        d = p["description"]
        ident = d["identifier"]
        R.ok(ident not in out, f"duplicate particle {ident}")
        R.ok(ident.startswith("abm:") and os.path.basename(f) == ident.split(":")[1] + ".json", f"{rel(f)}: file name / identifier mismatch")
        brp = d["basic_render_parameters"]
        R.ok(brp["material"] in PARTICLE_MATERIALS, f"{ident}: material {brp['material']}")
        tex = os.path.join(RP, brp["texture"] + ".png")
        if R.ok(os.path.exists(tex), f"{ident}: texture {brp['texture']} missing"):
            w, h = Image.open(tex).size
            uv = p["components"].get("minecraft:particle_appearance_billboard", {}).get("uv", {})
            R.ok(uv.get("texture_width") == w and uv.get("texture_height") == h, f"{ident}: uv texture size does not match the sheet {w}x{h}")
        comps = p["components"]
        R.ok(any(k.startswith("minecraft:emitter_rate") for k in comps) and any(k.startswith("minecraft:emitter_lifetime") for k in comps)
             and any(k.startswith("minecraft:emitter_shape") for k in comps), f"{ident}: emitter rate/lifetime/shape incomplete")
        R.ok("minecraft:particle_lifetime_expression" in comps, f"{ident}: particles never expire")
        rate = comps.get("minecraft:emitter_rate_steady", {}).get("max_particles")
        if rate is not None:
            R.ok(isinstance(rate, (int, float)) and rate <= 600, f"{ident}: max_particles {rate} too high")
        check_molang(ident, comps)
        # Seen in the game: the emitter ticks once per rendered frame, so anything placed by the emitter's
        # age comes out in per-frame clumps (a dotted or missing line, different on every device).
        for k, c in comps.items():
            if k.startswith("minecraft:emitter_shape"):
                R.ok("emitter_age" not in json.dumps(c), f"{ident}: particle placement depends on emitter age (frame-rate dependent)")
        out[ident] = p
    return out


def ogg_info(path):
    with open(path, "rb") as f:
        data = f.read(4096)
    if data[:4] != b"OggS":
        return None
    i = data.find(b"\x01vorbis")
    if i < 0:
        return None
    channels = data[i + 11]
    rate = struct.unpack_from("<I", data, i + 12)[0]
    return channels, rate


def check_sounds():
    R.begin("sounds")
    p = os.path.join(RP, "sounds", "sound_definitions.json")
    defs = load(p)["sound_definitions"] if os.path.exists(p) else {}
    used = set()
    total = 0
    for name, d in defs.items():
        R.ok(re.fullmatch(r"abm\.[a-z_]+\.[a-z_0-9]+", name) is not None, f"sound event name {name}")
        R.ok(d.get("category") in ("hostile", "neutral", "ambient", "player", "music", "block", "ui", "weather", "record"), f"{name}: category")
        R.ok(len(d.get("sounds", [])) > 0, f"{name}: no clips")
        for s in d.get("sounds", []):
            f = os.path.join(RP, s["name"] + ".ogg")
            used.add(os.path.normpath(f))
            if R.ok(os.path.exists(f), f"{name}: {s['name']}.ogg missing"):
                info = ogg_info(f)
                if R.ok(info is not None, f"{s['name']}.ogg is not Ogg Vorbis"):
                    R.ok(info[0] == 1, f"{s['name']}.ogg is not mono (positional audio needs mono)")
                    R.ok(info[1] in (44100, 48000, 22050), f"{s['name']}.ogg sample rate {info[1]}")
                total += os.path.getsize(f)
            R.ok(isinstance(s.get("volume", 1.0), (int, float)), f"{name}: volume must be a number")
            R.ok("pitch" not in s or isinstance(s["pitch"], (int, float)), f"{name}: pitch must be a number")
    for f in files(os.path.join(RP, "sounds"), ".ogg"):
        R.ok(os.path.normpath(f) in used, f"orphan sound file {rel(f)}")
    R.ok(total < 12 * 1024 * 1024, f"audio is {total / 1e6:.1f} MB")
    return defs, total


def check_items(lang, src):
    R.begin("items")
    items = {}
    atlas = load(os.path.join(RP, "textures", "item_texture.json"))["texture_data"]
    known_items = set(vanilla.ids("Item").values())
    for f in files(os.path.join(BP, "items"), ".json"):
        it = load(f)["minecraft:item"]
        ident = it["description"]["identifier"]
        R.ok(ident.startswith("abm:") and ident not in items, f"item identifier {ident}")
        items[ident] = it
        icon = it["components"]["minecraft:icon"]
        key = icon if isinstance(icon, str) else icon.get("textures", {}).get("default")
        if R.ok(key in atlas, f"{ident}: icon '{key}' not in item_texture.json"):
            tex = atlas[key]["textures"]
            p = os.path.join(RP, tex + ".png")
            if R.ok(os.path.exists(p), f"{ident}: icon file {tex}.png missing"):
                R.ok(Image.open(p).size == (16, 16), f"{ident}: icon is not 16x16")
        R.ok(f"item.{ident}.name" in lang, f"{ident}: no display name in en_US.lang")
        R.ok(it["description"].get("menu_category", {}).get("category") in ("items", "equipment", "construction", "nature"),
             f"{ident}: not in a Creative inventory category")
    for f in files(os.path.join(BP, "recipes"), ".json"):
        r = load(f).get("minecraft:recipe_shaped")
        if not R.ok(r is not None, f"{rel(f)}: only shaped recipes are expected"):
            continue
        widths = {len(row) for row in r["pattern"]}
        R.ok(len(widths) == 1 and len(r["pattern"]) <= 3, f"{rel(f)}: ragged pattern")
        for ch in set("".join(r["pattern"])) - {" "}:
            R.ok(ch in r["key"], f"{rel(f)}: pattern key '{ch}' undefined")
        for k, v in r["key"].items():
            R.ok(v["item"] in known_items or v["item"] in items, f"{rel(f)}: unknown ingredient {v['item']}")
        R.ok(r["result"]["item"] in items, f"{rel(f)}: result {r['result']['item']} is not one of our items")
    for f in files(os.path.join(BP, "loot_tables"), ".json"):
        for pool in load(f)["pools"]:
            for e in pool["entries"]:
                R.ok(e["name"] in known_items or e["name"] in items, f"{rel(f)}: unknown loot item {e['name']}")
    for lit in set(re.findall(r'"(abm:[a-z_0-9]+)"', src)):
        pass
    return items


def check_lang(client, src):
    R.begin("localization")
    langs = {}
    for name, base in (("BP", BP), ("RP", RP)):
        p = os.path.join(base, "texts", "en_US.lang")
        if not R.ok(os.path.exists(p), f"{name}: texts/en_US.lang missing"):
            continue
        d = {}
        for i, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            if not R.ok("=" in line, f"{name} en_US.lang:{i}: not key=value"):
                continue
            k, v = line.split("=", 1)
            R.ok(k not in d, f"{name} en_US.lang: duplicate key {k}")
            d[k] = v
        langs[name] = d
        R.ok(load(os.path.join(base, "texts", "languages.json")) == ["en_US"], f"{name}: languages.json")
        R.ok("pack.name" in d and "pack.description" in d, f"{name}: pack.name / pack.description missing")
    lang = langs.get("RP", {})
    for ident in client:
        R.ok(f"entity.{ident}.name" in lang, f"{ident}: no entity name in en_US.lang")
    # every translation key the script can send must exist
    keys = set(re.findall(r'translate:\s*"([a-zA-Z0-9_.:]+)"', src))
    templ = re.findall(r'translate:\s*`([^`]+)`', src) + re.findall(r'tr\(`([^`]+)`', src)
    keys |= set(re.findall(r'tr\("([a-zA-Z0-9_.:]+)"', src)) | set(re.findall(r'nameKey:\s*"([a-zA-Z0-9_.:]+)"', src))
    for k in sorted(keys):
        R.ok(k in lang, f"script uses translation key '{k}' that en_US.lang does not define")
    bosses = sorted({i.split(":")[1] for i in client if f"abm.lore.{ {'cantor_xiii': 'cantor'}.get(i.split(':')[1], i.split(':')[1]) }" in lang})
    present = sorted({m for m in ("vesperra", "cantor", "nomos", "orison") if f"abm.lore.{m}" in lang})
    for t in templ:
        prefix = t.split("${")[0]
        if prefix.startswith("entity."):
            continue
        if prefix in ("abm.summon.fail.",):
            for reason in ("unknown", "overlap", "floor", "ceiling", "unloaded", "spawn"):
                R.ok(prefix + reason in lang, f"missing translation {prefix + reason}")
        else:
            for b in present:
                R.ok(prefix + b in lang, f"missing translation {prefix + b}")
    return lang


def read_nbt(data):
    pos = 0

    def rd(fmt):
        nonlocal pos
        v = struct.unpack_from("<" + fmt, data, pos)
        pos += struct.calcsize("<" + fmt)
        return v[0]

    def s():
        nonlocal pos
        n = rd("H")
        v = data[pos:pos + n].decode("utf-8")
        pos += n
        return v

    def payload(t):
        nonlocal pos
        if t == 1:
            return rd("b")
        if t == 2:
            return rd("h")
        if t == 3:
            return rd("i")
        if t == 4:
            return rd("q")
        if t == 5:
            return rd("f")
        if t == 6:
            return rd("d")
        if t == 8:
            return s()
        if t == 9:
            et, n = rd("b"), rd("i")
            if et == 3:
                v = list(struct.unpack_from(f"<{n}i", data, pos))
                pos += 4 * n
                return v
            return [payload(et) for _ in range(n)]
        if t == 10:
            o = {}
            while True:
                tt = rd("b")
                if tt == 0:
                    return o
                name = s()                 # read the name BEFORE the payload
                o[name] = payload(tt)
        raise ValueError(f"NBT tag {t}")
    t = rd("b")
    s()
    return payload(t), pos


def check_structures():
    R.begin("structures")
    out = {}
    for f in files(os.path.join(BP, "structures"), ".mcstructure"):
        data = open(f, "rb").read()
        try:
            root, used = read_nbt(data)
        except Exception as e:                           # noqa: BLE001
            R.ok(False, f"{rel(f)}: NBT does not parse: {e}")
            continue
        R.ok(used == len(data), f"{rel(f)}: trailing bytes")
        R.ok(root.get("format_version") == 1, f"{rel(f)}: format_version")
        sx, sy, sz = root["size"]
        R.ok(sx <= 64 and sz <= 64 and sy <= 64, f"{rel(f)}: size {sx}x{sy}x{sz} exceeds 64 per axis")
        idx = root["structure"]["block_indices"]
        pal = root["structure"]["palette"]["default"]["block_palette"]
        R.ok(len(idx) == 2 and all(len(layer) == sx * sy * sz for layer in idx), f"{rel(f)}: index arrays have the wrong length")
        R.ok(all(-1 <= v < len(pal) for v in idx[0]), f"{rel(f)}: palette index out of range")
        for b in pal:
            msg = vanilla.check_block(b["name"], {})
            R.ok(not msg, f"{rel(f)}: {msg}")
            R.ok(set(b["states"]) <= vanilla.block_states().get(b["name"], set()), f"{rel(f)}: {b['name']} has unknown states {sorted(b['states'])}")
        R.ok(root["structure"]["entities"] == [], f"{rel(f)}: structure contains entities")
        out[os.path.basename(f)] = {"size": [sx, sy, sz], "blocks": sum(1 for v in idx[0] if v >= 0), "palette": len(pal)}
    return out


def check_packaging():
    R.begin("packaging")
    addon = os.path.join(DIST, "The_Abandoned_Miracles.mcaddon")
    if not R.ok(os.path.exists(addon), "dist/The_Abandoned_Miracles.mcaddon missing"):
        return {}
    with zipfile.ZipFile(addon) as z:
        R.ok(z.testzip() is None, "mcaddon archive is corrupt")
        names = z.namelist()
        R.ok(all("\\" not in n for n in names), "archive contains backslash paths")
        tops = {n.split("/")[0] for n in names}
        R.ok(len(tops) == 2, f"mcaddon should contain exactly two pack folders, found {sorted(tops)}")
        for top, base in (("The_Abandoned_Miracles_BP", BP), ("The_Abandoned_Miracles_RP", RP)):
            R.ok(f"{top}/manifest.json" in names, f"{top}/manifest.json missing from the archive")
            want = {f"{top}/" + os.path.relpath(f, base).replace(os.sep, "/") for f in files(base)}
            got = {n for n in names if n.startswith(top + "/")}
            R.ok(want == got, f"{top}: archive differs from the pack folder ({len(want ^ got)} files)")
            for f in files(base):
                arc = f"{top}/" + os.path.relpath(f, base).replace(os.sep, "/")
                if arc in got and z.read(arc) != open(f, "rb").read():
                    R.ok(False, f"{arc}: archive content is stale")
        for n in names:
            R.ok(len(n) <= 100, f"path too long ({len(n)}): {n}")
    size = os.path.getsize(addon)
    R.ok(size < 25 * 1024 * 1024, f"mcaddon is {size / 1e6:.1f} MB")
    return {"mcaddon_bytes": size, "files": len(names)}


KNOWN_COMMANDS = {"gamerule", "time", "weather", "tickingarea", "setworldspawn", "scoreboard", "execute", "structure",
                  "tp", "give", "tellraw", "tag", "function", "scriptevent"}


def check_testworld(client, items):
    """The optional demonstration world: archive, level.dat, pack references, kit functions."""
    R.begin("test world")
    path = os.path.join(DIST, "The_Abandoned_Miracles_Test_World.mcworld")
    if not os.path.exists(path):
        R.warn("test world not built; skipped")
        return None
    from kit import nbt
    with zipfile.ZipFile(path) as z:
        R.ok(z.testzip() is None, "mcworld archive is corrupt")
        names = set(z.namelist())
        for need in ("level.dat", "levelname.txt", "world_behavior_packs.json", "world_resource_packs.json"):
            R.ok(need in names, f"mcworld: {need} missing")
        raw = z.read("level.dat")
        size = struct.unpack("<ii", raw[:8])
        R.ok(size[1] == len(raw) - 8, "level.dat header length does not match its payload")
        lv = nbt.loads(raw[8:]).v
        R.ok(lv["LevelName"].v == z.read("levelname.txt").decode(), "level name differs between level.dat and levelname.txt")
        R.ok(lv["Generator"].v == 2, "test world is not a flat world")
        R.ok(lv["commandsEnabled"].v == 1, "cheats are not enabled in the test world")
        R.ok("gametest" not in lv["experiments"].v and all(t.v == 0 for t in lv["experiments"].v.values()), "test world enables experiments")
        packs = {}
        for n in names:
            m = re.match(r"(behavior_packs|resource_packs)/([^/]+)/manifest.json$", n)
            if m:
                h = json.loads(z.read(n))["header"]
                packs[h["uuid"]] = (m.group(1), m.group(2), h["version"])
        for ref_file, kind in (("world_behavior_packs.json", "behavior_packs"), ("world_resource_packs.json", "resource_packs")):
            for ref in json.loads(z.read(ref_file)):
                ok = ref["pack_id"] in packs and packs[ref["pack_id"]][0] == kind and packs[ref["pack_id"]][2] == ref["version"]
                R.ok(ok, f"{ref_file} references a pack that is not embedded: {ref}")
        R.ok(len(packs) == 3, f"expected 3 embedded packs, found {len(packs)}")
        structures = {"abm:" + os.path.basename(n)[:-12] for n in names if "/structures/abm/" in n}
        structures |= {"abmtw:" + os.path.basename(n)[:-12] for n in names if "/structures/abmtw/" in n}
        fns = {n.split("/functions/")[1][:-11] for n in names if n.endswith(".mcfunction")}
        with open(os.path.join(BP, "scripts", "main.js"), encoding="utf-8") as bf:
            bundle = bf.read()
        tick = [n for n in names if n.endswith("functions/tick.json")]
        if R.ok(len(tick) == 1, "kit tick.json missing"):
            for f in json.loads(z.read(tick[0]))["values"]:
                R.ok(f in fns, f"tick.json runs missing function {f}")
        loaded = set()
        for n in names:
            if not n.endswith(".mcfunction"):
                continue
            for i, line in enumerate(z.read(n).decode().splitlines(), 1):
                if not line.strip():
                    continue
                R.ok(line.split()[0] in KNOWN_COMMANDS, f"{n}:{i}: unexpected command '{line.split()[0]}'")
                R.ok(len(line) < 1800, f"{n}:{i}: command too long")
                for st in re.findall(r"structure load (\S+)", line):
                    R.ok(st in structures, f"{n}:{i}: structure {st} is not in the world's packs")
                    loaded.add(st)
                for fn in re.findall(r"run function (\S+)", line):
                    R.ok(fn in fns, f"{n}:{i}: function {fn} missing")
                for it in re.findall(r"give @s (\S+)", line):
                    R.ok(it in items, f"{n}:{i}: gives unknown item {it}")
                for ev in re.findall(r"^scriptevent (\S+)", line):
                    R.ok(f'"{ev}"' in bundle, f"{n}:{i}: script event {ev} is not handled by the add-on's script")
                R.ok("\\u00a7" not in line, f"{n}:{i}: colour code written as a \\u escape")
                # seen in the game: `execute if score #name ...` is a syntax error, and one bad line unloads the function
                for who in re.findall(r"\bscore (\S+) \S+ matches", line) + re.findall(r"scoreboard players \w+ (\S+) ", line):
                    R.ok(bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*|@[a-z](\[.*\])?", who)), f"{n}:{i}: score holder '{who}' is not a plain name or selector")
                if line.startswith("scriptevent"):
                    R.ok(len(line.split()) >= 3, f"{n}:{i}: scriptevent needs a message argument")
                m = re.search(r"tellraw @s (\{.*\})$", line)
                if m:
                    try:
                        json.loads(m.group(1))
                        R.ok(True, "")
                    except ValueError as e:
                        R.ok(False, f"{n}:{i}: tellraw JSON invalid: {e}")
        arenas = {s for s in structures if s.startswith("abm:")}
        R.ok(arenas <= loaded, f"arenas never placed by the kit: {sorted(arenas - loaded)}")
        for n in names:
            if n.endswith(".mcstructure") and "/abmtw/" in n:
                root, used = read_nbt(z.read(n))
                R.ok(max(root["size"]) <= 64, f"{n}: larger than 64 blocks")
    return {"bytes": os.path.getsize(path), "files": len(names), "arenas": sorted(arenas)}


def run_mct():
    R.begin("minecraft creator tools")
    script = None
    base = os.path.expanduser("~/.npm/_npx")
    for root, dirs, names in os.walk(base):
        if root.endswith(os.path.join("debug-addon", "scripts")) and "validate-summary.mjs" in names:
            script = os.path.join(root, "validate-summary.mjs")
            break
    if not script:
        R.warn("Minecraft Creator Tools validator not installed; skipped")
        return None
    r = subprocess.run(["node", script, PACKS], capture_output=True, text=True, timeout=600)
    m = re.search(r"(\d+) error\(s\), (\d+) warning\(s\)", r.stdout)
    if not R.ok(m is not None, "could not read the Creator Tools summary"):
        return None
    errors, warnings = int(m.group(1)), int(m.group(2))
    R.ok(errors == 0, f"Creator Tools reports {errors} error(s):\n" + r.stdout[:1500])
    R.ok(warnings == 0, f"Creator Tools reports {warnings} warning(s):\n" + r.stdout[:1500])
    return {"errors": errors, "warnings": warnings, "summary": r.stdout.splitlines()[0] if r.stdout else ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mct", action="store_true")
    ap.add_argument("--json", default=os.path.join(OUT, "build", "validate_results.json"))
    args = ap.parse_args()
    summary = {}
    summary["json_files"] = check_json()
    check_manifests()
    src = check_script()
    bp_ents, client = check_entities()
    geos = check_geometry()
    particles = check_particles()
    sounds, audio_bytes = check_sounds()
    rcs = check_render_controllers(client, geos)
    check_facing(client)
    anims, ctrls = check_animations(client, geos, {})
    use = check_client(client, geos, anims, ctrls, rcs, particles, sounds)
    check_animation_bodies(client, geos, anims, ctrls, use)
    lang = check_lang(client, src)
    items = check_items(lang, src)
    summary["structures"] = check_structures()
    summary["packaging"] = check_packaging()
    summary["testworld"] = check_testworld(client, items)
    if args.mct:
        summary["mct"] = run_mct()
    summary.update({
        "entities": len(bp_ents), "geometries": {k: {"bones": len(v["bones"]), "cubes": v["cubes"], "texture": [v["tw"], v["th"]]} for k, v in geos.items()},
        "animations": len(anims), "animation_controllers": len(ctrls), "particles": len(particles), "sound_events": len(sounds),
        "audio_bytes": audio_bytes, "items": len(items), "lang_keys": len(lang),
        "checks_passed": R.passed, "checks_failed": len(R.failures),
        "sections": {k: {"passed": v[0], "failed": v[1]} for k, v in R.sections.items()},
        "failures": R.failures, "warnings": R.warnings,
    })
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    for k, v in R.sections.items():
        print(f"  {k:26s} {v[0]:5d} passed  {v[1]:3d} failed")
    for w in R.warnings:
        print("  warning:", w)
    for f in R.failures[:60]:
        print("  FAIL", f)
    print(f"validation: {R.passed} checks passed, {len(R.failures)} failed")
    sys.exit(1 if R.failures else 0)


if __name__ == "__main__":
    main()
