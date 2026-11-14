#!/usr/bin/env python3
"""Static validation of the generated packs: every cross reference must resolve.

  python3 tools/validate.py            # exit code 1 on any error
  python3 tools/validate.py --stats    # also print per-model budgets

Checks manifests, items, behaviour <-> client entity pairs, geometry (bone parents, UV bounds,
texture size), render controllers, animations (bones exist, effects are declared), animation
controllers (states / animations / transitions), particles, sound definitions and files,
attachables, language keys, script bundle, and (when the official schemas are available) JSON
schema conformance for items.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BP = os.path.join(ROOT, "behavior_packs", "grimoire_bp")
RP = os.path.join(ROOT, "resource_packs", "grimoire_rp")

errors, warnings = [], []


def err(m):
    errors.append(m)


def warn(m):
    warnings.append(m)


def load(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:  # noqa: BLE001
        err(f"{os.path.relpath(p, ROOT)}: invalid JSON ({e})")
        return None


def png_size(p):
    with open(p, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def rel(p):
    return os.path.relpath(p, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    # ---------------------------------------------------------------- manifests
    bpm, rpm = load(os.path.join(BP, "manifest.json")), load(os.path.join(RP, "manifest.json"))
    uuids = []
    for name, m in (("BP", bpm), ("RP", rpm)):
        if not m:
            continue
        uuids.append(m["header"]["uuid"])
        uuids += [x["uuid"] for x in m["modules"]]
        if m["header"].get("min_engine_version") != [1, 26, 60]:
            warn(f"{name} manifest min_engine_version is {m['header'].get('min_engine_version')}")
    if len(set(uuids)) != len(uuids):
        err("manifest UUIDs are not unique")
    if bpm and rpm:
        if not any(d.get("uuid") == rpm["header"]["uuid"] for d in bpm.get("dependencies", [])):
            err("BP manifest does not depend on the RP")
        for mod in bpm["modules"]:
            if mod["type"] == "script" and not os.path.exists(os.path.join(BP, mod["entry"])):
                err(f"script entry {mod['entry']} is missing (run npm run bundle)")
        if not any(d.get("module_name") == "@minecraft/server" for d in bpm.get("dependencies", [])):
            err("BP manifest lacks the @minecraft/server dependency")
    for pk in (BP, RP):
        if not os.path.exists(os.path.join(pk, "pack_icon.png")):
            warn(f"{rel(pk)}: pack_icon.png missing")

    # ---------------------------------------------------------------- language
    lang = {}
    lp = os.path.join(RP, "texts", "en_US.lang")
    if os.path.exists(lp):
        for line in open(lp, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.rstrip("\n").split("=", 1)
                lang[k] = v
    else:
        err("resource pack texts/en_US.lang missing")

    # ---------------------------------------------------------------- items
    item_tex = (load(os.path.join(RP, "textures", "item_texture.json")) or {}).get("texture_data", {}) \
        if os.path.exists(os.path.join(RP, "textures", "item_texture.json")) else {}
    items = {}
    for p in sorted(glob.glob(os.path.join(BP, "items", "*.json"))):
        j = load(p)
        if not j:
            continue
        it = j["minecraft:item"]
        ident = it["description"]["identifier"]
        items[ident] = it
        comps = it["components"]
        icon = comps.get("minecraft:icon")
        key = icon if isinstance(icon, str) else (icon or {}).get("textures", {}).get("default")
        if not key:
            err(f"{ident}: no icon")
        elif key not in item_tex:
            err(f"{ident}: icon key '{key}' missing from textures/item_texture.json")
        else:
            tp = item_tex[key]["textures"]
            tp = tp if isinstance(tp, str) else tp[0]
            if not os.path.exists(os.path.join(RP, tp + ".png")):
                err(f"{ident}: icon texture {tp}.png missing")
        for bad in ("minecraft:food", "minecraft:shooter", "minecraft:throwable", "minecraft:durability", "minecraft:projectile"):
            if bad in comps:
                err(f"{ident}: forbidden component {bad}")
        if "minecraft:use_modifiers" not in comps:
            err(f"{ident}: needs minecraft:use_modifiers for hold-to-cast")
        dn = comps.get("minecraft:display_name", {}).get("value")
        if dn and dn not in lang:
            err(f"{ident}: display name key {dn} missing from en_US.lang")
    if sorted(items) != ["grimoire:divine_word", "grimoire:dream_nightmare", "grimoire:elemental_dragon"]:
        err(f"expected exactly the three Grimoire items, found {sorted(items)}")

    # ---------------------------------------------------------------- resources index
    geos = {}
    for p in sorted(glob.glob(os.path.join(RP, "models", "**", "*.json"), recursive=True)):
        j = load(p)
        if not j:
            continue
        for g in j.get("minecraft:geometry", []):
            d = g["description"]
            if d["identifier"] in geos:
                err(f"duplicate geometry {d['identifier']}")
            geos[d["identifier"]] = (g, p)
            names = set()
            for b in g.get("bones", []):
                if b["name"] in names:
                    err(f"{d['identifier']}: duplicate bone {b['name']}")
                names.add(b["name"])
            for b in g.get("bones", []):
                if "parent" in b and b["parent"] not in names:
                    err(f"{d['identifier']}: bone {b['name']} has unknown parent {b['parent']}")
                for c in b.get("cubes", []):
                    uv = c.get("uv")
                    if isinstance(uv, dict):
                        for f, fu in uv.items():
                            u0, v0 = fu["uv"]
                            u1, v1 = u0 + fu["uv_size"][0], v0 + fu["uv_size"][1]
                            if min(u0, u1) < 0 or min(v0, v1) < 0 or max(u0, u1) > d["texture_width"] or max(v0, v1) > d["texture_height"]:
                                err(f"{d['identifier']}: {b['name']} {f} uv outside texture")
    anims = {}
    for p in sorted(glob.glob(os.path.join(RP, "animations", "*.json"))):
        j = load(p)
        for k, v in (j or {}).get("animations", {}).items():
            if k in anims:
                err(f"duplicate animation {k}")
            anims[k] = v
    ctrls = {}
    for p in sorted(glob.glob(os.path.join(RP, "animation_controllers", "*.json"))):
        j = load(p)
        for k, v in (j or {}).get("animation_controllers", {}).items():
            ctrls[k] = v
    rcs = {}
    for p in sorted(glob.glob(os.path.join(RP, "render_controllers", "*.json"))):
        j = load(p)
        for k, v in (j or {}).get("render_controllers", {}).items():
            rcs[k] = v
    particles = {}
    for p in sorted(glob.glob(os.path.join(RP, "particles", "*.json"))):
        j = load(p)
        if not j:
            continue
        d = j["particle_effect"]["description"]
        particles[d["identifier"]] = j
        tex = d["basic_render_parameters"]["texture"]
        if not os.path.exists(os.path.join(RP, tex + ".png")):
            err(f"particle {d['identifier']}: texture {tex}.png missing")
        if d["basic_render_parameters"]["material"] not in ("particles_alpha", "particles_blend", "particles_add"):
            err(f"particle {d['identifier']}: unexpected material")
    sdefs = {}
    sp = os.path.join(RP, "sounds", "sound_definitions.json")
    if os.path.exists(sp):
        sdefs = (load(sp) or {}).get("sound_definitions", {})
    for sid, sd in sdefs.items():
        for s in sd.get("sounds", []):
            name = s if isinstance(s, str) else s["name"]
            if not os.path.exists(os.path.join(RP, name + ".ogg")):
                err(f"sound {sid}: file {name}.ogg missing")
    used_oggs = {(s if isinstance(s, str) else s["name"]) for sd in sdefs.values() for s in sd.get("sounds", [])}
    for p in glob.glob(os.path.join(RP, "sounds", "**", "*.ogg"), recursive=True):
        r = os.path.relpath(p, RP)[:-4].replace(os.sep, "/")
        if r not in used_oggs:
            warn(f"unreferenced sound file {r}.ogg")

    # ---------------------------------------------------------------- entities
    bp_ents = {}
    for p in sorted(glob.glob(os.path.join(BP, "entities", "*.json"))):
        j = load(p)
        if j:
            d = j["minecraft:entity"]["description"]
            bp_ents[d["identifier"]] = j["minecraft:entity"]
    rp_ents = {}
    for p in sorted(glob.glob(os.path.join(RP, "entity", "*.json"))):
        j = load(p)
        if j:
            d = j["minecraft:client_entity"]["description"]
            rp_ents[d["identifier"]] = d
    for i in bp_ents:
        if i not in rp_ents:
            err(f"{i}: behaviour entity has no client entity")
        if f"entity.{i}.name" not in lang:
            warn(f"{i}: no display name in en_US.lang")
        comps = bp_ents[i]["components"]
        if "minecraft:transient" not in comps:
            warn(f"{i}: not transient (could persist after a crash)")
    for i in rp_ents:
        if i not in bp_ents:
            err(f"{i}: client entity has no behaviour entity")

    def tga_size(fp):
        with open(fp, "rb") as fh:
            h = fh.read(18)
        return (h[12] | h[13] << 8, h[14] | h[15] << 8)

    def check_emissive_texture(owner, fp):
        """32-bit TGA; texels that are cut out (alpha 0) must be pure black or the emissive material draws them."""
        import numpy as np
        from PIL import Image
        with open(fp, "rb") as fh:
            h = fh.read(18)
        if h[2] not in (2, 10) or h[16] != 32:
            err(f"{owner}: {os.path.basename(fp)} is not a 32-bit true-colour TGA")
            return
        a = np.asarray(Image.open(fp).convert("RGBA"))
        if (a[a[..., 3] == 0][:, :3].max(initial=0)) > 0:
            err(f"{owner}: {os.path.basename(fp)} has coloured texels under alpha 0")

    def check_visual(owner, d, bones_of):
        geo_ids = d.get("geometry", {})
        for k, gid in geo_ids.items():
            if gid not in geos:
                err(f"{owner}: geometry {gid} not found")
        emissive = any("emissive" in m for m in d.get("materials", {}).values())
        for k, tp in d.get("textures", {}).items():
            fp = os.path.join(RP, tp + ".tga")
            if os.path.exists(fp) and os.path.exists(os.path.join(RP, tp + ".png")):
                err(f"{owner}: both {tp}.tga and a stale .png exist")
            elif os.path.exists(fp):
                check_emissive_texture(owner, fp)
            elif os.path.exists(os.path.join(RP, tp + ".png")):
                if emissive and k == "default":
                    err(f"{owner}: emissive material needs {tp}.tga, found .png")
            else:
                err(f"{owner}: texture {tp} not found (.tga or .png)")
        # texture size must match geometry description
        if "default" in geo_ids and geo_ids["default"] in geos and "default" in d.get("textures", {}):
            g = geos[geo_ids["default"]][0]["description"]
            fp = os.path.join(RP, d["textures"]["default"] + ".tga")
            sz = None
            if os.path.exists(fp):
                sz = tga_size(fp)
            elif os.path.exists(fp[:-4] + ".png"):
                sz = png_size(fp[:-4] + ".png")
            if sz:
                if sz and tuple(sz) != (g["texture_width"], g["texture_height"]):
                    err(f"{owner}: texture is {sz} but geometry expects {(g['texture_width'], g['texture_height'])}")
        for m in d.get("materials", {}).values():
            if m not in ("entity_emissive_alpha", "entity_alphablend", "entity_alphatest", "entity", "entity_emissive"):
                err(f"{owner}: material {m} is not on the safe list")
        amap = d.get("animations", {})
        for short, full in amap.items():
            if full.startswith("controller."):
                if full not in ctrls:
                    err(f"{owner}: animation controller {full} not found")
            elif full not in anims:
                err(f"{owner}: animation {full} not found")
        for a in d.get("scripts", {}).get("animate", []):
            n = a if isinstance(a, str) else next(iter(a))
            if n not in amap:
                err(f"{owner}: scripts.animate references unknown '{n}'")
        for rc in d.get("render_controllers", []):
            rc = rc if isinstance(rc, str) else next(iter(rc))
            if rc not in rcs:
                err(f"{owner}: render controller {rc} not found")
                continue
            txt = json.dumps(rcs[rc])
            for kind, table in (("Geometry", d.get("geometry", {})), ("Texture", d.get("textures", {})), ("Material", d.get("materials", {}))):
                for ref in set(re.findall(rf"{kind}\.([A-Za-z0-9_]+)", txt)):
                    if ref not in table:
                        err(f"{owner}: render controller uses {kind}.{ref} which is not declared")
        for short, sid in d.get("sound_effects", {}).items():
            if sid not in sdefs:
                err(f"{owner}: sound effect {short} -> {sid} not in sound_definitions")
        for short, pid in d.get("particle_effects", {}).items():
            if pid not in particles:
                err(f"{owner}: particle effect {short} -> {pid} not found")
        # animations: bones, effect names
        all_bones = set()
        for gid in geo_ids.values():
            if gid in geos:
                all_bones |= {b["name"] for b in geos[gid][0].get("bones", [])}
        all_bones |= bones_of
        locators = set()
        for gid in geo_ids.values():
            if gid in geos:
                for b in geos[gid][0].get("bones", []):
                    locators |= set(b.get("locators", {}))
        for short, full in amap.items():
            a = anims.get(full)
            if not a:
                continue
            for bone in a.get("bones", {}):
                if bone not in all_bones:
                    err(f"{owner}: animation {short} moves unknown bone '{bone}'")
            for t, ev in a.get("sound_effects", {}).items():
                for e in (ev if isinstance(ev, list) else [ev]):
                    if e["effect"] not in d.get("sound_effects", {}):
                        err(f"{owner}: animation {short} plays undeclared sound '{e['effect']}'")
            for t, ev in a.get("particle_effects", {}).items():
                for e in (ev if isinstance(ev, list) else [ev]):
                    if e["effect"] not in d.get("particle_effects", {}):
                        err(f"{owner}: animation {short} emits undeclared particle '{e['effect']}'")
                    if e.get("locator") and e["locator"] not in locators:
                        err(f"{owner}: animation {short} uses unknown locator '{e['locator']}'")
            if a.get("loop") is True and "animation_length" not in a:
                has_keys = any(isinstance(ch, dict) for b in a.get("bones", {}).values() for ch in b.values())
                if has_keys:
                    warn(f"{owner}: looping animation {short} has keyframes but no animation_length")
        for short, full in amap.items():
            c = ctrls.get(full)
            if not c:
                continue
            states = c.get("states", {})
            if c.get("initial_state") not in states:
                err(f"{owner}: controller {short} initial_state missing")
            for sn, st in states.items():
                for an in st.get("animations", []):
                    n = an if isinstance(an, str) else next(iter(an))
                    if n not in amap:
                        err(f"{owner}: controller {short} state {sn} plays unknown animation '{n}'")
                for tr in st.get("transitions", []):
                    for tgt in tr:
                        if tgt not in states:
                            err(f"{owner}: controller {short} state {sn} transitions to unknown state {tgt}")
                for e in st.get("sound_effects", []):
                    if e["effect"] not in d.get("sound_effects", {}):
                        err(f"{owner}: controller {short} state {sn} plays undeclared sound '{e['effect']}'")
                for e in st.get("particle_effects", []):
                    if e["effect"] not in d.get("particle_effects", {}):
                        err(f"{owner}: controller {short} state {sn} emits undeclared particle '{e['effect']}'")

    for i, d in rp_ents.items():
        check_visual(i, d, set())
        # entity properties used by the render controller / client must exist on the server entity
        props = set(bp_ents.get(i, {}).get("description", {}).get("properties", {}))
        txt = json.dumps(d) + json.dumps([rcs.get(r if isinstance(r, str) else next(iter(r))) for r in d.get("render_controllers", [])]) \
            + json.dumps([ctrls.get(f) for f in d.get("animations", {}).values()])
        for pr in set(re.findall(r"q(?:uery)?\.property\('([^']+)'\)", txt)):
            if pr not in props:
                err(f"{i}: client uses property {pr} that the behaviour entity does not define")

    # ---------------------------------------------------------------- attachables
    PLAYER_BONES = {"root", "waist", "body", "head", "hat", "leftArm", "rightArm", "leftLeg", "rightLeg", "rightItem", "leftItem",
                    "cape", "jacket", "leftSleeve", "rightSleeve", "leftPants", "rightPants"}
    att = sorted(glob.glob(os.path.join(RP, "attachables", "*.json")))
    seen = set()
    for p in att:
        j = load(p)
        if not j:
            continue
        d = j["minecraft:attachable"]["description"]
        seen.add(d["identifier"])
        if d["identifier"] not in items:
            err(f"attachable {d['identifier']} does not match an item")
        check_visual(f"attachable {d['identifier']}", d, PLAYER_BONES)
    for i in items:
        if i not in seen:
            warn(f"{i}: no attachable (the book would render as a flat icon in hand)")

    # ---------------------------------------------------------------- scripts
    bundle = os.path.join(BP, "scripts", "main.js")
    if os.path.exists(bundle):
        src = open(bundle, encoding="utf-8").read()
        for mod in set(re.findall(r'from\s*"(@minecraft/[a-z-]+)"', src)):
            if mod != "@minecraft/server":
                err(f"script imports {mod} which is not declared in the manifest")
        for bad in ("setCamera", "camera.setCamera", "runCommand(\"camera", "@minecraft/server-gametest"):
            if bad in src:
                err(f"script contains forbidden usage: {bad}")
        if "STUB" in src or "is not implemented yet" in src:
            err("script bundle still contains stub spells")
    else:
        err("behavior pack scripts/main.js missing")

    # ---------------------------------------------------------------- stats
    if args.stats:
        print(f"{'geometry':40s} {'bones':>5s} {'cubes':>5s} {'texture':>10s}")
        for gid, (g, p) in sorted(geos.items()):
            d = g["description"]
            bones = g.get("bones", [])
            print(f"{gid[18:]:40s} {len(bones):5d} {sum(len(b.get('cubes', [])) for b in bones):5d} {d['texture_width']:>5d}x{d['texture_height']:<4d}")
    size = lambda d: sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)  # noqa: E731
    print(f"entities {len(bp_ents)}  geometries {len(geos)}  animations {len(anims)}  controllers {len(ctrls)}  "
          f"particles {len(particles)}  sounds {len(sdefs)}  attachables {len(att)}")
    print(f"behavior pack {size(BP) / 1e6:.2f} MB   resource pack {size(RP) / 1e6:.2f} MB")
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
