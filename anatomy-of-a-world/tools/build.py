"""
Build THE ANATOMY OF A WORLD:

  1. compile TypeScript (src/) -> build/scripts
  2. generate models/textures/animations, particles, sounds, pack JSON, icons
  3. write manifests, assemble build/packs/{BP,RP}
  4. package dist/The_Anatomy_of_a_World.mcaddon (+ per-pack .mcpack)

usage: python3 tools/build.py [--skip-audio] [--skip-tsc]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "packs", "BP")
RP = os.path.join(BUILD, "packs", "RP")
DIST = os.path.join(ROOT, "dist")
sys.path.insert(0, os.path.join(ROOT, "tools"))

VERSION = [1, 1, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
SERVER_UI_VERSION = "2.3.0"
UUID = {
    "bp_header": "df338d62-0627-4bae-96ae-9d90854bbb38",
    "bp_data": "931f8e36-097b-41d3-8e5d-ec2bf1dc84e6",
    "bp_script": "f838087c-7388-4b53-97e0-1fc78cf7fa9a",
    "rp_header": "2090a9b9-bebe-4f6a-9abb-b932cab6841d",
    "rp_res": "13bb1ecf-b407-48f1-8585-9fd42c092255",
}
PACK_NAME = "The_Anatomy_of_a_World"


def run(cmd, **kw):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT, **kw)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)


def manifests():
    write_json(os.path.join(BP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": {"authors": ["THE ANATOMY OF A WORLD"], "product_type": "addon"},
    })
    write_json(os.path.join(RP, "manifest.json"), {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "metadata": {"authors": ["THE ANATOMY OF A WORLD"], "product_type": "addon"},
    })


def audio_stamp() -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, "tools", "audio", "synth.py"), "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()[:16]


def main():
    skip_audio = "--skip-audio" in sys.argv
    skip_tsc = "--skip-tsc" in sys.argv
    # keep cached audio between builds (synthesis is slow); everything else is regenerated
    audio_cache = os.path.join(BUILD, "audio_cache")
    stamp_file = os.path.join(audio_cache, "stamp.txt")
    if os.path.isdir(os.path.join(RP, "sounds", "anatomy")):
        if os.path.isdir(audio_cache):
            shutil.rmtree(audio_cache)
        shutil.copytree(os.path.join(RP, "sounds", "anatomy"), os.path.join(audio_cache, "anatomy"))
        if os.path.exists(os.path.join(BUILD, "audio_stamp.txt")):
            shutil.copy(os.path.join(BUILD, "audio_stamp.txt"), stamp_file)
    for d in (BP, RP):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)

    if not skip_tsc:
        run(["npx", "tsc", "-p", "tsconfig.json"])
    run(["node", "tools/export_mountain.mjs", os.path.join(BUILD, "scripts", "bosses", "migrating_mountain", "mm_data.js")])
    shutil.copytree(os.path.join(BUILD, "scripts"), os.path.join(BP, "scripts"))

    import packdefs
    packdefs.emit(BP, RP)
    run([sys.executable, "tools/models/build_models.py", RP])
    run([sys.executable, "tools/fx/particles.py", RP])

    stamp = audio_stamp()
    cached = os.path.join(audio_cache, "anatomy")
    if os.path.isdir(cached) and os.path.exists(stamp_file) and open(stamp_file).read().strip() == stamp:
        shutil.copytree(cached, os.path.join(RP, "sounds", "anatomy"))
        print("audio: reused cache")
    elif skip_audio and os.path.isdir(cached):
        shutil.copytree(cached, os.path.join(RP, "sounds", "anatomy"))
        print("audio: reused cache (--skip-audio)")
    else:
        run([sys.executable, "tools/audio/synth.py", RP])
    with open(os.path.join(BUILD, "audio_stamp.txt"), "w") as fh:
        fh.write(stamp)

    hero = os.path.join(ROOT, "docs", "images", "boss001_hero.png")
    run([sys.executable, "tools/icons.py", RP, BP, hero])
    manifests()

    # package
    os.makedirs(DIST, exist_ok=True)
    bp_pack = os.path.join(DIST, f"{PACK_NAME}_BP.mcpack")
    rp_pack = os.path.join(DIST, f"{PACK_NAME}_RP.mcpack")
    addon = os.path.join(DIST, f"{PACK_NAME}.mcaddon")
    for p in (bp_pack, rp_pack, addon):
        if os.path.exists(p):
            os.remove(p)

    def add_dir(z, src, prefix):
        for base, _dirs, files in os.walk(src):
            for f in sorted(files):
                full = os.path.join(base, f)
                rel = os.path.relpath(full, src)
                z.write(full, os.path.join(prefix, rel) if prefix else rel)

    with zipfile.ZipFile(bp_pack, "w", zipfile.ZIP_DEFLATED) as z:
        add_dir(z, BP, "")
    with zipfile.ZipFile(rp_pack, "w", zipfile.ZIP_DEFLATED) as z:
        add_dir(z, RP, "")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as z:
        add_dir(z, BP, f"{PACK_NAME}_BP")
        add_dir(z, RP, f"{PACK_NAME}_RP")
    for p in (bp_pack, rp_pack, addon):
        print(f"{os.path.relpath(p, ROOT)}: {os.path.getsize(p) / 1024:.0f} KiB")


if __name__ == "__main__":
    main()
