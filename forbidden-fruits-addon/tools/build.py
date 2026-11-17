"""
Build "Forbidden Fruits": Jōki Jōki no Mi (steam) + Sekiyu Sekiyu no Mi (petroleum) in one add-on.

    python3 tools/build.py   -> build/Forbidden_BP, build/Forbidden_RP, dist/Forbidden_Fruits*.mcaddon/.mcpack

1. Each fruit's own generator (../joki-joki-addon/tools/build.py, ../sekiyu-addon/tools/build.py) writes its
   assets into build/_parts/<fruit> (ADDON_ASSETS_ONLY=1: no scripts, no packaging).
2. The parts are merged. Any file both parts write is an error, except the shared ones merged here by hand:
   the minecraft:player overrides (BP + RP), the player render controllers, item_texture.json,
   sound_definitions.json and the language files.
3. The combined TypeScript (src/steam, src/oil, src/shared) is compiled into the BP and everything is packaged.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
BUILD = os.path.join(ROOT, "build")
PARTS = os.path.join(BUILD, "_parts")
BP = os.path.join(BUILD, "Forbidden_BP")
RP = os.path.join(BUILD, "Forbidden_RP")
DIST = os.path.join(ROOT, "dist")
VANILLA = os.path.join(REPO, "sekiyu-addon", "tools", "vanilla")

NAME = "Forbidden Fruits"
FILE_BASE = "Forbidden_Fruits"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER, SERVER_UI = "2.11.0", "2.3.0"
UUID = {
    "bp_header": "548d4000-e19e-4090-b2ab-84829ca8de5c",
    "bp_data": "22b291ee-d9ee-4b06-ad91-20417ef1cb4d",
    "bp_script": "f5c5c2d5-831f-4f26-9d36-7874c8d408b3",
    "rp_header": "1e7d1ed8-a067-404f-8f03-a39f5840b6c2",
    "rp_res": "1d71a0f4-4246-4464-81d8-692c28578140",
}
PARTS_SPEC = {  # part name -> (generator project, BP folder, RP folder)
    "steam": ("joki-joki-addon", "Joki_BP", "Joki_RP"),
    "oil": ("sekiyu-addon", "Sekiyu_BP", "Sekiyu_RP"),
}
# files every part writes that are merged by hand (relative to the pack root)
MERGED = {
    "bp": {"manifest.json", "pack_icon.png", "entities/player.json", "texts/en_US.lang", "texts/languages.json"},
    "rp": {"manifest.json", "pack_icon.png", "entity/player.entity.json", "textures/item_texture.json",
           "sounds/sound_definitions.json", "texts/en_US.lang", "texts/languages.json",
           "render_controllers/joki_player.render_controllers.json", "render_controllers/sekiyu_player.render_controllers.json"},
}
PLAYER_RC = {
    "controller.render.player.third_person": "controller.render.forbidden.player.third_person",
    "controller.render.player.first_person": "controller.render.forbidden.player.first_person",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def part(name, side, *rel):
    proj, bp, rp = PARTS_SPEC[name]
    return os.path.join(PARTS, name, bp if side == "bp" else rp, *rel)


# --------------------------------------------------------------------------- 1. generate parts


def generate_parts():
    for name, (proj, _, _) in PARTS_SPEC.items():
        env = dict(os.environ, ADDON_BUILD_DIR=os.path.join(PARTS, name), ADDON_ASSETS_ONLY="1")
        res = subprocess.run([sys.executable, os.path.join(REPO, proj, "tools", "build.py")], env=env, capture_output=True, text=True, cwd=os.path.join(REPO, proj))
        if res.returncode != 0:
            print(res.stdout, res.stderr)
            raise SystemExit(f"{proj} asset build failed")


# --------------------------------------------------------------------------- 2. merge


def copy_parts():
    owner = {}
    for side, dst in (("bp", BP), ("rp", RP)):
        for name in PARTS_SPEC:
            src = part(name, side)
            for dirpath, _, files in os.walk(src):
                for fn in files:
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, src).replace(os.sep, "/")
                    if rel in MERGED[side]:
                        continue
                    key = (side, rel)
                    if key in owner:
                        raise SystemExit(f"file collision between parts: {side}/{rel} ({owner[key]} and {name})")
                    owner[key] = name
                    out = os.path.join(dst, rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    shutil.copy2(full, out)
    return owner


def merge_player_bp():
    steam = load(part("steam", "bp", "entities", "player.json"))
    oil = load(part("oil", "bp", "entities", "player.json"))
    van = load(os.path.join(VANILLA, "player.json"))
    for p in (steam, oil):
        e, v = p["minecraft:entity"], van["minecraft:entity"]
        assert e["components"] == v["components"] and e.get("events") == v.get("events"), "part player.json diverges from vanilla"
    merged = copy.deepcopy(oil)
    props = merged["minecraft:entity"]["description"]["properties"]
    for k, v in steam["minecraft:entity"]["description"]["properties"].items():
        assert k not in props, f"property clash {k}"
        props[k] = v
    write_json(os.path.join(BP, "entities", "player.json"), merged)


def merged_overlay(oil_rc, steam_rc):
    """Oil tint wins while the oil body is active, else the steam glow, else the engine's own colour."""
    out = {}
    for ch in ("r", "g", "b", "a"):
        oil_expr, steam_expr = oil_rc["overlay_color"][ch], steam_rc["overlay_color"][ch]
        assert oil_expr.endswith(": this") and steam_expr.endswith(": this"), "overlay expressions must fall back to `this`"
        out[ch] = oil_expr[: -len("this")] + f"({steam_expr})"
    return out


def merge_player_rp():
    van = load(os.path.join(VANILLA, "player.entity.json"))["minecraft:client_entity"]["description"]
    steam = load(part("steam", "rp", "entity", "player.entity.json"))["minecraft:client_entity"]["description"]
    oil_doc = load(part("oil", "rp", "entity", "player.entity.json"))
    oil = oil_doc["minecraft:client_entity"]["description"]
    merged = copy.deepcopy(oil)
    for section in ("materials", "textures", "geometry", "animations", "particle_effects"):
        for k, v in steam.get(section, {}).items():
            if van.get(section, {}).get(k) == v:
                continue
            assert k not in merged.get(section, {}) or merged[section][k] == v, f"player {section}.{k} clash"
            merged.setdefault(section, {})[k] = v
    for section in ("initialize", "pre_animation"):
        extra = steam["scripts"][section][len(van["scripts"][section]):]
        merged["scripts"][section] = merged["scripts"][section] + extra
    merged["scripts"]["animate"] += steam["scripts"]["animate"][len(van["scripts"]["animate"]):]
    # render controller list: vanilla order with the combined player controllers, then each part's overlays
    rcs = []
    for entry in van["render_controllers"]:
        (k, cond), = entry.items()
        rcs.append({PLAYER_RC.get(k, k): cond})
    for src in (oil, steam):
        for entry in src["render_controllers"][len(van["render_controllers"]):]:
            rcs.append(entry)
    merged["render_controllers"] = rcs
    oil_doc["minecraft:client_entity"]["description"] = merged
    write_json(os.path.join(RP, "entity", "player.entity.json"), oil_doc)

    steam_rcs = load(part("steam", "rp", "render_controllers", "joki_player.render_controllers.json"))["render_controllers"]
    oil_rcs = load(part("oil", "rp", "render_controllers", "sekiyu_player.render_controllers.json"))["render_controllers"]
    out = {}
    for view in ("third_person", "first_person"):
        o = oil_rcs[f"controller.render.sekiyu.player.{view}"]
        s = steam_rcs[f"controller.render.joki.player.{view}"]
        rc = copy.deepcopy(o)  # vanilla + "hidden while dissolved" part visibility
        rc["overlay_color"] = merged_overlay(o, s)
        out[f"controller.render.forbidden.player.{view}"] = rc
    for k, v in {**oil_rcs, **steam_rcs}.items():
        if ".player." not in k:
            out[k] = v
    write_json(os.path.join(RP, "render_controllers", "forbidden_player.render_controllers.json"), {"format_version": "1.8.0", "render_controllers": out})


def merge_tables():
    tex = {"resource_pack_name": "forbidden_fruits", "texture_name": "atlas.items", "texture_data": {}}
    snd = {"format_version": "1.20.20", "sound_definitions": {}}
    for name in PARTS_SPEC:
        for k, v in load(part(name, "rp", "textures", "item_texture.json"))["texture_data"].items():
            assert k not in tex["texture_data"], f"item texture clash {k}"
            tex["texture_data"][k] = v
        for k, v in load(part(name, "rp", "sounds", "sound_definitions.json"))["sound_definitions"].items():
            assert k not in snd["sound_definitions"], f"sound clash {k}"
            snd["sound_definitions"][k] = v
    write_json(os.path.join(RP, "textures", "item_texture.json"), tex)
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), snd)


def merge_lang():
    head = [f"pack.name={NAME}",
            "pack.description=Two original fan-made devil fruits: Jōki Jōki no Mi (steam pressure) and Sekiyu Sekiyu no Mi (petroleum Logia). One fruit per body."]
    lines, seen = [], set()
    for name in PARTS_SPEC:
        for line in open(part(name, "rp", "texts", "en_US.lang"), encoding="utf-8"):
            line = line.rstrip("\n")
            if "=" not in line or line.startswith("pack."):
                continue
            k = line.split("=", 1)[0]
            assert k not in seen, f"lang clash {k}"
            seen.add(k)
            lines.append(line)
    for root, body in ((RP, head + lines), (BP, head)):
        os.makedirs(os.path.join(root, "texts"), exist_ok=True)
        open(os.path.join(root, "texts", "en_US.lang"), "w", encoding="utf-8").write("\n".join(body) + "\n")
        open(os.path.join(root, "texts", "languages.json"), "w").write('[\n  "en_US"\n]\n')


def manifests():
    meta = {"authors": ["Forbidden Fruits add-on (fan-made)"], "product_type": "addon"}
    bp = {"format_version": 2,
          "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
          "modules": [{"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
                      {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"}],
          "dependencies": [{"module_name": "@minecraft/server", "version": SERVER}, {"module_name": "@minecraft/server-ui", "version": SERVER_UI},
                           {"uuid": UUID["rp_header"], "version": VERSION}],
          "metadata": meta}
    rp = {"format_version": 2,
          "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
          "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
          "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
          "metadata": meta}
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    icon = pack_icon()
    for p in (BP, RP):
        icon.save(os.path.join(p, "pack_icon.png"))


def pack_icon(size=256):
    """Both fruits on a dark violet gradient."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    g = np.clip(1 - r * 1.9, 0, 1) ** 1.5
    bg = np.dstack([0.08 + 0.32 * g, 0.03 + 0.08 * g, 0.12 + 0.28 * g, np.ones_like(g)])
    img = Image.fromarray((bg * 255).astype(np.uint8), "RGBA")
    steam = Image.open(part("steam", "rp", "textures", "items", "joki", "joki_fruit.png")).convert("RGBA").resize((140, 140), Image.NEAREST)
    oil = Image.open(part("oil", "rp", "textures", "items", "sekiyu", "sekiyu_fruit.png")).convert("RGBA").resize((150, 150), Image.LANCZOS)
    img.alpha_composite(steam, (8, 26))
    img.alpha_composite(oil, (100, 92))
    return img


# --------------------------------------------------------------------------- 3. scripts + package


def build_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in forbidden-fruits-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", os.path.join(BP, "scripts")], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


def zip_dir(zf, folder, arc_root):
    for dirpath, dirs, files in os.walk(folder):
        dirs.sort()
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            info = zipfile.ZipInfo(os.path.join(arc_root, os.path.relpath(full, folder)).replace(os.sep, "/"), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full, "rb") as f:
                zf.writestr(info, f.read())


def package():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, f"{FILE_BASE}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Forbidden_BP")
        zip_dir(zf, RP, "Forbidden_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{FILE_BASE}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    generate_parts()
    copy_parts()
    merge_player_bp()
    merge_player_rp()
    merge_tables()
    merge_lang()
    manifests()
    build_scripts()
    print("built", os.path.relpath(package(), ROOT))


if __name__ == "__main__":
    main()
