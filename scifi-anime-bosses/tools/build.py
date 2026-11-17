"""
build.py - generate the VESPER-0 behavior + resource packs and package the add-on.

    python3 tools/build.py [--skip-audio] [--no-ts]

Outputs build/SAB_VESPER_BP, build/SAB_VESPER_RP and dist/*.mcaddon / *.mcpack.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import aux_anims  # noqa: E402
import aux_models  # noqa: E402
import audio  # noqa: E402
import content as C  # noqa: E402
import icons  # noqa: E402
import tex  # noqa: E402
import vesper_anims as va  # noqa: E402
import vesper_model as vm  # noqa: E402
import vfx  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "SAB_VESPER_BP")
RP = os.path.join(BUILD, "SAB_VESPER_RP")
DIST = os.path.join(ROOT, "dist")
CACHE = os.path.join(ROOT, ".cache")

VERSION = [1, 0, 4]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
UUID = {
    "bp": "8a4f2c1e-5b7d-4e3a-9c21-7d0e6f9b1a01",
    "bp_data": "8a4f2c1e-5b7d-4e3a-9c21-7d0e6f9b1a02",
    "bp_script": "8a4f2c1e-5b7d-4e3a-9c21-7d0e6f9b1a03",
    "rp": "3e6b9d2f-1c4a-4b8e-a7f5-2d9c0e8b4f01",
    "rp_res": "3e6b9d2f-1c4a-4b8e-a7f5-2d9c0e8b4f02",
}
ADDON = "SciFi_Anime_Bosses_VESPER-0"


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(img, np.ndarray):
        tex.save_png(img, path)
    else:
        img.save(path, optimize=True)


# --------------------------------------------------------------------------- manifests

def manifests():
    meta = {"authors": ["SCI-FI ANIME BOSSES"], "product_type": "addon"}
    bp = {"format_version": 2,
          "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp"], "version": VERSION,
                     "min_engine_version": MIN_ENGINE},
          "modules": [{"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
                      {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
                       "entry": "scripts/main.js"}],
          "dependencies": [{"module_name": "@minecraft/server", "version": SERVER_VERSION},
                           {"uuid": UUID["rp"], "version": VERSION}],
          "metadata": meta}
    rp = {"format_version": 2,
          "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp"], "version": VERSION,
                     "min_engine_version": MIN_ENGINE},
          # no dependency back on the behavior pack: the BP depends on the RP, and circular pack dependencies
          # can stop packs from loading
          "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
          "metadata": meta}
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)


# --------------------------------------------------------------------------- models, textures

def models_and_textures():
    boss, main, glow, shield = vm.build()
    aux = aux_models.build_all(main, glow)
    gdir = os.path.join(RP, "models", "entity", "sab")
    for layer in boss.layers():
        ident = boss.identifier if layer == "main" else f"{boss.identifier}.{layer}"
        write_json(os.path.join(gdir, f"{ident.split('geometry.sab.')[1]}.geo.json"), boss.geometry_json(layer))
    for name, m in aux.items():
        layers = m.layers() or ["main"]
        for layer in layers:
            ident = m.identifier if layer == "main" else f"{m.identifier}.{layer}"
            write_json(os.path.join(gdir, f"{ident.split('geometry.sab.')[1]}.geo.json"), m.geometry_json(layer))
    tdir = os.path.join(RP, "textures", "entity", "sab")
    for v in ("p1", "p2"):
        save_png(main.render(v), os.path.join(tdir, f"vesper_{v}.png"))
        save_png(glow.render(v), os.path.join(tdir, f"vesper_glow_{v}.png"))
        sh = shield.render(v)
        tint = tex.hexc("ffe6a0") if v == "p1" else tex.hexc("c47dff")
        sh[..., :3] *= tint
        save_png(sh, os.path.join(tdir, f"vesper_shield_{v}.png"))
    save_png(np.zeros((16, 16, 4), np.float32), os.path.join(tdir, "empty.png"))
    save_png(vfx.atlas_image(), os.path.join(RP, vfx.ATLAS + ".png"))
    icons.save_all(os.path.join(RP, "textures", "items", "sab"))
    write_json(os.path.join(RP, "textures", "item_texture.json"), {
        "resource_pack_name": "sab_vesper", "texture_name": "atlas.items",
        "texture_data": {f"sab_{k}": {"textures": f"textures/items/sab/{k}"} for k in icons.ICONS}})
    return boss, aux, main, glow


def pack_icons(boss, main, glow):
    import render
    sc = render.Scene(512, 512, bg_top=(8, 10, 24), bg_bottom=(40, 30, 72))
    sc.set_camera((24, 7, 30), (0, 4.2, 0), 38)
    sc.add_model(boss, {"main": main.render("p1"), "glow": glow.render("p1")}, hidden=vm.LIMB_BONES + ["shield"])
    img = sc.image().resize((256, 256), Image.LANCZOS)
    for p in (BP, RP):
        img.save(os.path.join(p, "pack_icon.png"))
    return img


# --------------------------------------------------------------------------- animations

def animations():
    boss_anims = va.all_anims() + C.fx_anims()
    write_json(os.path.join(RP, "animations", "sab_vesper_0.animation.json"),
               {"format_version": "1.10.0", "animations": {a.name: a.to_json() for a in boss_anims}})
    ctrls = va.controllers()
    write_json(os.path.join(RP, "animation_controllers", "sab_vesper_0.animation_controllers.json"),
               {"format_version": "1.10.0", "animation_controllers": {c.name: c.to_json() for c in ctrls}})
    aux_all = {}
    for key in aux_anims.ALL:
        anims, amap, animate, pre, init = aux_anims.get(key)
        for a in anims:
            aux_all[a.name] = a.to_json()
        write_json(os.path.join(RP, "entity", "sab", f"{key}.entity.json"),
                   C.aux_client_entity(key, anims, amap, animate, pre, init))
    write_json(os.path.join(RP, "animations", "sab_aux.animation.json"), {"format_version": "1.10.0", "animations": aux_all})
    write_json(os.path.join(RP, "entity", "sab", "vesper_0.entity.json"), C.boss_client_entity())
    write_json(os.path.join(RP, "entity", "sab", "vesper_part.entity.json"), C.part_client_entity())
    write_json(os.path.join(RP, "render_controllers", "sab.render_controllers.json"), C.render_controllers())


def particles():
    for ident, data in vfx.all_effects().items():
        write_json(os.path.join(RP, "particles", "sab", ident.split(":")[1] + ".json"), data)


# --------------------------------------------------------------------------- audio (cached by source hash)

def sounds(skip=False):
    src_hash = hashlib.sha256(open(os.path.join(HERE, "audio.py"), "rb").read()).hexdigest()[:16]
    cache_dir = os.path.join(CACHE, "audio", src_hash)
    sfx_dir = os.path.join(cache_dir, "sfx")
    mus_dir = os.path.join(cache_dir, "music")
    complete = os.path.isdir(sfx_dir) and len(os.listdir(sfx_dir)) == len(audio.SOUNDS) and \
        os.path.isdir(mus_dir) and len(os.listdir(mus_dir)) == len(audio.MUSIC)
    if not complete:
        if skip:
            raise SystemExit("audio cache missing; run without --skip-audio")
        shutil.rmtree(os.path.join(CACHE, "audio"), ignore_errors=True)
        print("  synthesising audio (one-off, cached) ...")
        audio.render_all(sfx_dir, mus_dir)
    shutil.copytree(sfx_dir, os.path.join(RP, "sounds", "sab", "vesper"))
    shutil.copytree(mus_dir, os.path.join(RP, "sounds", "music", "sab"))
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"), C.sound_definitions())


# --------------------------------------------------------------------------- misc RP / BP data

def rp_misc():
    for name, data in C.fogs().items():
        write_json(os.path.join(RP, "fogs", f"{name}.json"), data)
    write_text(os.path.join(RP, "texts", "en_US.lang"), C.lang_rp())
    write_json(os.path.join(RP, "texts", "languages.json"), ["en_US"])


def bp_data():
    for name, data in C.bp_entities().items():
        write_json(os.path.join(BP, "entities", f"sab_{name}.json"), data)  # flat, like every Microsoft sample
    for name, data in C.bp_items().items():
        write_json(os.path.join(BP, "items", "sab", f"{name}.json"), data)
    for name, data in C.bp_recipes().items():
        write_json(os.path.join(BP, "recipes", "sab", f"{name}.json"), data)
    for name, data in C.bp_loot().items():
        write_json(os.path.join(BP, "loot_tables", f"{name}.json"), data)
    write_text(os.path.join(BP, "texts", "en_US.lang"), C.lang_bp())
    write_json(os.path.join(BP, "texts", "languages.json"), ["en_US"])


# --------------------------------------------------------------------------- generated TS ids

def generated_ids():
    ids = {
        "ENT": C.ENT, "ITEMS": C.ITEMS, "FOGS": C.FOGS, "ACT": va.ACT, "PHASE": va.PHASE,
        "PARTICLES": sorted(vfx.all_effects().keys()),
        "SOUNDS": sorted(f"sab.vesper.{k}" for k in C.SOUND_SPEC),
        "MUSIC": {k: f"sab.music.{k}" for k in audio.MUSIC},
        "BOSS_PROPS": sorted(C.BOSS_PROPS.keys()),
    }
    lines = ["// AUTO-GENERATED by tools/build.py from the pack data. Do not edit.", ""]
    lines.append(f"export const ENT = {json.dumps(C.ENT, indent=2)} as const;")
    lines.append(f"export const ITEMS = {json.dumps(C.ITEMS, indent=2)} as const;")
    lines.append(f"export const FOGS = {json.dumps(C.FOGS, indent=2)} as const;")
    lines.append(f"export const ACT = {json.dumps(va.ACT, indent=2)} as const;")
    lines.append(f"export const PHASE = {json.dumps(va.PHASE, indent=2)} as const;")
    lines.append(f"export const MUSIC = {json.dumps(ids['MUSIC'], indent=2)} as const;")
    pid = {p.split(':')[1]: p for p in ids["PARTICLES"]}
    lines.append(f"export const FX = {json.dumps(pid, indent=2)} as const;")
    sid = {s.split('.')[-1]: s for s in ids["SOUNDS"]}
    lines.append(f"export const SND = {json.dumps(sid, indent=2)} as const;")
    write_text(os.path.join(ROOT, "src", "generated", "ids.ts"), "\n".join(lines) + "\n")
    return ids


# --------------------------------------------------------------------------- scripts & packaging

def compile_scripts():
    out = os.path.join(BP, "scripts")
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", out], check=True, cwd=ROOT)


def package():
    os.makedirs(DIST, exist_ok=True)

    def zipdir(zf, folder, prefix):
        for base, _, files in os.walk(folder):
            for fn in sorted(files):
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, folder)
                zf.write(full, os.path.join(prefix, rel) if prefix else rel)
    paths = {}
    for name, folder in (("BP", BP), ("RP", RP)):
        p = os.path.join(DIST, f"{ADDON}_{name}.mcpack")
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            zipdir(zf, folder, "")
        paths[name] = p
    p = os.path.join(DIST, f"{ADDON}.mcaddon")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zipdir(zf, BP, "SAB_VESPER_BP")
        zipdir(zf, RP, "SAB_VESPER_RP")
    paths["addon"] = p
    return paths


def main():
    skip_audio = "--skip-audio" in sys.argv
    no_ts = "--no-ts" in sys.argv
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BP)
    os.makedirs(RP)
    print("manifests"); manifests()
    print("models + textures"); boss, aux, main_atlas, glow_atlas = models_and_textures()
    print("pack icons"); pack_icons(boss, main_atlas, glow_atlas)
    print("animations + client entities"); animations()
    print("particles"); particles()
    print("sounds"); sounds(skip_audio)
    print("rp misc"); rp_misc()
    print("bp data"); bp_data()
    print("generated ids"); generated_ids()
    if not no_ts:
        print("typescript"); compile_scripts()
    paths = package()
    for k, p in paths.items():
        print(f"  {k}: {os.path.relpath(p, ROOT)} ({os.path.getsize(p) / 1024:.0f} KB)")
    print("stats:", json.dumps({"boss": boss.stats(), **{k: m.stats() for k, m in aux.items()}}))


if __name__ == "__main__":
    main()
