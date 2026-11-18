"""
Build "The Abandoned Miracles".

    python3 tools/build.py [--no-sounds] [--no-script] [--only vesperra,...]

Generates every pack file from the Python asset sources and the TypeScript
gameplay sources:

    packs/behavior_packs, packs/resource_packs   the add-on (also committed, so it can be inspected without building)
    assets/blockbench/      editable .bbmodel sources for every model
    dist/                   The_Abandoned_Miracles.mcaddon (+ separate .mcpack files)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from kit import pack as K          # noqa: E402
from kit import sfx                # noqa: E402
from kit.anim import animations_file, controllers_file  # noqa: E402

# ABM_OUT redirects every generated file (packs, dist, bbmodels) to another folder, so a
# single-boss development build never touches the committed full build.
OUT = os.path.abspath(os.environ.get("ABM_OUT", ROOT))
BP = os.path.join(OUT, "packs", "behavior_packs", "The_Abandoned_Miracles_BP")
RP = os.path.join(OUT, "packs", "resource_packs", "The_Abandoned_Miracles_RP")
DIST = os.path.join(OUT, "dist")
CACHE = os.path.join(ROOT, "build", "cache")
BBMODELS = os.path.join(OUT, "assets", "blockbench")
BOSSES = ["vesperra", "cantor", "nomos", "orison"]


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def load_bosses(only=None):
    out = []
    for key in BOSSES:
        if only and key not in only:
            continue
        if not os.path.exists(os.path.join(HERE, "bosses", key, "__init__.py")):
            log(f"boss '{key}' has no asset module yet - skipped")
            continue
        t = time.time()
        mod = importlib.import_module(f"bosses.{key}")
        a = mod.assets()
        log(f"{key}: assets generated in {time.time() - t:.1f}s")
        out.append(a)
    return out


# --------------------------------------------------------------------------- writers

def write_models(assets) -> dict:
    stats = {}
    for a in assets:
        for stem, model in a.models.items():
            model.paint()
            K.write_json(os.path.join(RP, "models", "entity", "abm", f"{stem}.geo.json"), model.geometry_json())
            tex = os.path.join(RP, "textures", "entity", "abm", f"{stem}.png")
            os.makedirs(os.path.dirname(tex), exist_ok=True)
            model.texture.save(tex)
            K.write_json(os.path.join(BBMODELS, f"{stem}.bbmodel"), model.bbmodel_json(stem), compact_lists=True)
            stats[stem] = model.stats()
    return stats


def write_client(assets) -> None:
    rcs = {"controller.render.abm.layered": K.render_controller(materials=K.layered_materials())}
    for a in assets:
        for ce in a.client_entities:
            K.write_json(os.path.join(RP, "entity", ce.identifier.split(":")[1] + ".entity.json"), ce.json())
        if a.animations:
            K.write_json(os.path.join(RP, "animations", f"abm_{a.key}.animation.json"), animations_file(a.animations),
                         minify=True)
        if a.controllers:
            K.write_json(os.path.join(RP, "animation_controllers", f"abm_{a.key}.ac.json"),
                         controllers_file(a.controllers))
        rcs.update(a.render_controllers)
        for stem, p in a.particles.items():
            K.write_json(os.path.join(RP, "particles", "abm", f"{stem}.json"), p)
        for rel, img in a.textures.items():
            path = os.path.join(RP, rel + ".png")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            img.save(path)
    K.write_json(os.path.join(RP, "render_controllers", "abm.render_controllers.json"),
                 {"format_version": "1.10.0", "render_controllers": rcs})


def write_sounds(assets, enabled: bool) -> int:
    defs = {}
    n = 0
    os.makedirs(CACHE, exist_ok=True)
    for a in assets:
        for event, spec in a.sounds.items():
            entries = []
            for stem, samples in spec["clips"].items():
                rel = f"sounds/abm/{a.key}/{stem}"
                dst = os.path.join(RP, rel + ".ogg")
                entries.append({"name": rel, "volume": spec.get("volume", 1.0), "load_on_low_memory": True})
                if not enabled:
                    continue
                import numpy as np
                digest = hashlib.sha1(np.asarray(samples, dtype="<f4").tobytes()).hexdigest()[:20]
                cached = os.path.join(CACHE, f"{digest}.ogg")
                if not os.path.exists(cached):
                    tmp = f"{cached}.{os.getpid()}.ogg"
                    sfx.save_ogg(samples, tmp)
                    os.replace(tmp, cached)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(cached, dst)
                n += 1
            defs[event] = {"category": spec.get("category", "hostile"), "min_distance": spec.get("min", 6.0),
                           "max_distance": spec.get("max", 48.0), "sounds": entries}
    K.write_json(os.path.join(RP, "sounds", "sound_definitions.json"),
                 {"format_version": "1.20.20", "sound_definitions": defs})
    return n


def write_items(assets, shared) -> None:
    tex = {}
    icons = dict(shared["icons"])
    items = dict(shared["items"])
    recipes = dict(shared["recipes"])
    for a in assets:
        icons.update(a.item_icons)
        items.update(a.items)
        recipes.update(a.recipes)
        for stem, table in a.loot.items():
            K.write_json(os.path.join(BP, "loot_tables", "abm", f"{stem}.json"), table)
        for name, st in a.structures.items():
            errs = st.validate() if hasattr(st, "validate") else []
            if errs:
                raise SystemExit(f"structure {name}: " + "; ".join(errs))
            path = os.path.join(BP, "structures", "abm", f"{name}.mcstructure")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(st.to_bytes())
    for key, img in icons.items():
        path = os.path.join(RP, "textures", "items", "abm", f"{key}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
        tex[key] = {"textures": f"textures/items/abm/{key}"}
    K.write_json(os.path.join(RP, "textures", "item_texture.json"),
                 {"resource_pack_name": "abm", "texture_name": "atlas.items", "texture_data": tex})
    for stem, it in items.items():
        K.write_json(os.path.join(BP, "items", "abm", f"{stem}.json"), it)
    for stem, r in recipes.items():
        K.write_json(os.path.join(BP, "recipes", "abm", f"{stem}.json"), r)


def write_entities(assets) -> None:
    for a in assets:
        for stem, ent in a.bp_entities.items():
            K.write_json(os.path.join(BP, "entities", "abm", f"{stem}.json"), ent)


def write_lang(assets, shared) -> None:
    lang = dict(shared["lang"])
    for a in assets:
        lang.update(a.lang)
    for k, v in lang.items():
        if "\n" in v or "\r" in v or "=" in k:
            raise SystemExit(f"lang entry {k} contains a line break or a bad key")
    body = "\n".join(f"{k}={v}" for k, v in lang.items()) + "\n"
    for pack in (BP, RP):
        K.write_text(os.path.join(pack, "texts", "en_US.lang"), body)
        K.write_json(os.path.join(pack, "texts", "languages.json"), ["en_US"])


def compile_script(only=None) -> None:
    esbuild = os.path.join(ROOT, "node_modules", ".bin", "esbuild")
    out = os.path.join(BP, "scripts", "main.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    entry = os.path.join(ROOT, "src", "main.ts")
    if only:
        # development build: bundle only the selected bosses, so unfinished work elsewhere cannot break it
        entry = os.path.join(OUT, "build", "entry_" + "_".join(sorted(only)) + ".ts")
        os.makedirs(os.path.dirname(entry), exist_ok=True)
        src = os.path.join(ROOT, "src").replace(os.sep, "/")
        lines = [f'import {{ boot }} from "{src}/boot";']
        lines += [f'import {{ MODULE as {k} }} from "{src}/bosses/{k}";' for k in sorted(only)]
        lines.append("boot({ " + ", ".join(sorted(only)) + " });")
        K.write_text(entry, "\n".join(lines) + "\n")
    cmd = [esbuild, entry, "--bundle", "--format=esm", "--target=es2021",
           "--external:@minecraft/server", "--external:@minecraft/server-ui", "--charset=utf8",
           "--legal-comments=none", f"--outfile={out}", "--log-level=warning"]
    subprocess.run(cmd, check=True, cwd=ROOT)
    log(f"script bundled: {os.path.getsize(out) / 1024:.0f} KiB")


def package() -> None:
    os.makedirs(DIST, exist_ok=True)
    targets = {
        "The_Abandoned_Miracles.mcaddon": [(BP, "The_Abandoned_Miracles_BP"), (RP, "The_Abandoned_Miracles_RP")],
        "The_Abandoned_Miracles_BP.mcpack": [(BP, "")],
        "The_Abandoned_Miracles_RP.mcpack": [(RP, "")],
    }
    for name, parts in targets.items():
        dst = os.path.join(DIST, name)
        if os.path.exists(dst):
            os.remove(dst)
        n = sum(K.zip_dir(src, dst, prefix) for src, prefix in parts)
        log(f"{name}: {n} files, {os.path.getsize(dst) / 1024:.0f} KiB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sounds", action="store_true", help="skip audio synthesis/encoding (keeps definitions)")
    ap.add_argument("--no-script", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    t0 = time.time()
    import shared_assets
    assets = load_bosses(set(args.only.split(",")) if args.only else None)
    keep_sounds = os.path.join(OUT, "build", "sounds_keep")
    if args.no_sounds and os.path.isdir(os.path.join(RP, "sounds", "abm")):
        shutil.rmtree(keep_sounds, ignore_errors=True)
        shutil.copytree(os.path.join(RP, "sounds", "abm"), keep_sounds)
    for p in (BP, RP):
        shutil.rmtree(p, ignore_errors=True)
        os.makedirs(p)
    shared = shared_assets.build([a.key for a in assets])
    K.write_json(os.path.join(BP, "manifest.json"), K.bp_manifest())
    K.write_json(os.path.join(RP, "manifest.json"), K.rp_manifest())
    for p in (BP, RP):
        shared["pack_icon"].save(os.path.join(p, "pack_icon.png"))
    stats = write_models(assets)
    write_client(assets)
    n = write_sounds(assets, not args.no_sounds)
    if args.no_sounds and os.path.isdir(keep_sounds):
        shutil.copytree(keep_sounds, os.path.join(RP, "sounds", "abm"), dirs_exist_ok=True)
    write_items(assets, shared)
    write_entities(assets)
    write_lang(assets, shared)
    if not args.no_script:
        compile_script(set(args.only.split(",")) if args.only else None)
    package()
    K.write_json(os.path.join(OUT, "build", "model_stats.json"), stats)
    for stem, s in stats.items():
        log(f"model {stem}: {s['bones']} bones, {s['cubes']} cubes, texture {s['texture'][0]}x{s['texture'][1]}")
    log(f"{n} sound clips encoded; done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
