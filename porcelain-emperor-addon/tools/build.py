"""
Build script for "The Porcelain Emperor" (Dragon Boss 001).

    python3 tools/build.py            -> build/ packs + dist/*.mcaddon

Generates every resource/behavior pack file (models, damage-state textures,
animations, controllers, particles, fog, synthesised sounds, arena blocks,
items, entities, language files, manifests), compiles the TypeScript
gameplay scripts and packages the add-on.
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import assets_bp  # noqa: E402
import assets_rp  # noqa: E402
import audio  # noqa: E402
import models  # noqa: E402
import pixels  # noqa: E402
from modelkit import render_preview  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "Porcelain_BP")
RP = os.path.join(BUILD, "Porcelain_RP")
DIST = os.path.join(ROOT, "dist")
CACHE = os.path.join(BUILD, ".cache")

ADDON_FILE = "The_Porcelain_Emperor"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "657f6b52-8929-485c-a11b-059f37577cf8",
    "bp_data": "10875b33-6f91-411d-9d52-65abc377032d",
    "bp_script": "74582a7b-7287-4169-a2d4-aed4c2adfc42",
    "rp_header": "deb76503-e108-4693-a181-3c235aaa77ed",
    "rp_res": "27bb4ba9-7a90-4b5d-9aa5-69c743c3b188",
}
NS = "porcelain"
TEXTURE_VARIANTS = {0: "pristine", 1: "kintsugi", 2: "shattered"}


# --------------------------------------------------------------------------- io helpers

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


# --------------------------------------------------------------------------- manifests

def manifests(pack_icon):
    meta = {"authors": ["Porcelain Emperor add-on"], "product_type": "addon"}
    bp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": meta,
    }
    rp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": meta,
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    for p in (BP, RP):
        save_png(pack_icon, os.path.join(p, "pack_icon.png"))


# --------------------------------------------------------------------------- models & textures

def build_models():
    geo_ids = {}
    built = {}
    for name, fn in models.ALL.items():
        m = fn()
        bw, bh, oy = models.BOUNDS[name]
        write_json(os.path.join(RP, "models", "entity", NS, f"{name}.geo.json"), m.geometry_json(bw, bh, oy))
        n_var = models.VARIANTS.get(name, 1)
        for v in range(n_var):
            img = m.paint(v)
            fname = f"{name}_{TEXTURE_VARIANTS[v]}" if n_var > 1 else name
            save_png(img, os.path.join(RP, "textures", "entity", NS, f"{fname}.png"))
        geo_ids[name] = m.identifier
        built[name] = m
    return geo_ids, built


def build_pack_icon(emperor):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "head.png")
    hide = tuple(f"seg{i}" for i in range(1, models.SEGMENTS + 1)) + ("arm_r", "arm_l")
    render_preview([emperor], p, yaw=-28, pitch=12, size=512, hidden=hide, variant=1)
    from PIL import Image
    return pixels.pack_icon(Image.open(p))


def build_textures():
    terrain = {}
    for key in pixels.BLOCK_TEXTURES:
        save_png(pixels.block_texture(key), os.path.join(RP, "textures", "blocks", NS, f"{key}.png"))
        terrain[f"{NS}_{key}"] = {"textures": f"textures/blocks/{NS}/{key}"}
    write_json(os.path.join(RP, "textures", "terrain_texture.json"),
               {"resource_pack_name": NS, "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4,
                "texture_data": terrain})
    items = {}
    for key in pixels.ICONS:
        save_png(pixels.icon(key), os.path.join(RP, "textures", "items", NS, f"{key}.png"))
        items[f"{NS}_{key}"] = {"textures": f"textures/items/{NS}/{key}"}
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": NS, "texture_name": "atlas.items", "texture_data": items})
    save_png(pixels.particle_atlas(), os.path.join(RP, "textures", "particle", "porcelain_fx.png"))
    blocks_json = {"format_version": "1.21.40"}
    for key, (_n, sound, *_r) in assets_bp.BLOCKS.items():
        blocks_json[f"{NS}:{key}"] = {"sound": sound}
    write_json(os.path.join(RP, "blocks.json"), blocks_json)


# --------------------------------------------------------------------------- resource pack json

def build_rp(geo_ids):
    write_json(os.path.join(RP, "animations", "emperor.animation.json"),
               {"format_version": "1.8.0", "animations": assets_rp.emperor_animations()})
    write_json(os.path.join(RP, "animations", "fragments.animation.json"),
               {"format_version": "1.8.0", "animations": assets_rp.minor_animations()})
    write_json(os.path.join(RP, "animation_controllers", "emperor.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": assets_rp.emperor_controller()})
    write_json(os.path.join(RP, "render_controllers", "porcelain.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": assets_rp.render_controllers()})
    for name, data in assets_rp.client_entities(geo_ids).items():
        write_json(os.path.join(RP, "entity", NS, f"{name}.entity.json"), data)
    for name, data in assets_rp.particles().items():
        write_json(os.path.join(RP, "particles", NS, f"{name}.json"), data)
    for name, data in assets_rp.fogs().items():
        write_json(os.path.join(RP, "fogs", f"{name}.json"), data)
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), assets_rp.sound_definitions())


def build_sounds():
    """Sounds are synthesised once and cached (the music takes a few seconds)."""
    cache = os.path.join(ROOT, "tools", ".sound_cache")
    stamp = os.path.join(cache, "audio.py.sha")
    import hashlib
    src = open(os.path.join(HERE, "audio.py"), "rb").read()
    digest = hashlib.sha256(src).hexdigest()
    if not (os.path.exists(stamp) and open(stamp).read() == digest
            and all(os.path.exists(os.path.join(cache, f"{n}.ogg")) for n in audio.SOUNDS)):
        os.makedirs(cache, exist_ok=True)
        audio.build(cache)
        write_text(stamp, digest)
    dst = os.path.join(RP, "sounds", NS)
    os.makedirs(dst, exist_ok=True)
    for n in audio.SOUNDS:
        shutil.copy(os.path.join(cache, f"{n}.ogg"), os.path.join(dst, f"{n}.ogg"))


# --------------------------------------------------------------------------- behavior pack json

def build_bp():
    for name, data in assets_bp.bp_entities().items():
        write_json(os.path.join(BP, "entities", NS, f"{name}.json"), data)
    for name, data in assets_bp.bp_items().items():
        write_json(os.path.join(BP, "items", NS, f"{name}.json"), data)
    for name, data in assets_bp.bp_blocks().items():
        write_json(os.path.join(BP, "blocks", NS, f"{name}.json"), data)
    for name, data in assets_bp.bp_recipes().items():
        write_json(os.path.join(BP, "recipes", f"{name}.json"), data)
    for name, data in assets_bp.bp_loot().items():
        write_json(os.path.join(BP, "loot_tables", f"{name}.json"), data)


def build_lang():
    lines = assets_bp.lang_lines()
    for root in (BP, RP):
        body = lines if root == RP else lines[:2]
        write_text(os.path.join(root, "texts", "en_US.lang"), "\n".join(body) + "\n")
        write_text(os.path.join(root, "texts", "languages.json"), json.dumps(["en_US"], indent=2) + "\n")


# --------------------------------------------------------------------------- scripts

def build_scripts():
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` in porcelain-emperor-addon/")
    res = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        raise SystemExit("TypeScript compilation failed")


# --------------------------------------------------------------------------- packaging

def zip_dir(zf, folder, arc_root):
    for dirpath, dirs, files in os.walk(folder):
        dirs.sort()
        for fn in sorted(files):
            full = os.path.join(dirpath, fn)
            zf.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))


def package():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, f"{ADDON_FILE}.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, BP, "Porcelain_BP")
        zip_dir(zf, RP, "Porcelain_RP")
    for folder, suffix in ((BP, "BP"), (RP, "RP")):
        with zipfile.ZipFile(os.path.join(DIST, f"{ADDON_FILE}_{suffix}.mcpack"), "w", zipfile.ZIP_DEFLATED) as zf:
            zip_dir(zf, folder, "")
    return addon


def main():
    for p in (BP, RP):
        if os.path.exists(p):
            shutil.rmtree(p)
    geo_ids, built = build_models()
    manifests(build_pack_icon(built["emperor"]))
    build_textures()
    build_rp(geo_ids)
    build_sounds()
    build_bp()
    build_lang()
    build_scripts()
    addon = package()
    print("built", os.path.relpath(addon, ROOT), {k: v.stats() for k, v in built.items()})


if __name__ == "__main__":
    main()
