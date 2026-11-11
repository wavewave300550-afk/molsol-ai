#!/usr/bin/env python3
"""Build Grimoire: Imperial Magic -> packs/Grimoire_BP, packs/Grimoire_RP, dist/*.mcaddon.

Steps: generate every resource (models, textures, animations, particles, sounds, icons),
generate behavior data (items, entities, blocks, recipes), bundle the TypeScript with esbuild,
then zip .mcpack files and the combined .mcaddon.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from gen import styles  # noqa: E401,F401  (registers texture styles)
from gen import book, packs, particles, sounds, icons, fxdefs, fogs, playeranim  # noqa: E402
from gen import fx_common, fx_pressure, fx_ice, fx_blood, mobs  # noqa: E402,F401  (register constructs)

BP = os.path.join(ROOT, "packs", "Grimoire_BP")
RP = os.path.join(ROOT, "packs", "Grimoire_RP")
DIST = os.path.join(ROOT, "dist")


def spells_from_ts():
    """Single source of truth for spell metadata is the TypeScript registry."""
    out = []
    for school in ("pressure", "ice", "blood"):
        src = open(os.path.join(ROOT, "src", "spells", school, "index.ts"), encoding="utf-8").read()
        for m in re.finditer(r'code: "([PIB]\d\d)", id: "([a-z_.]+)", school: S, name: "([^"]+)", cooldown: (\d+), charge: (\d+), enhanceable: (true|false)(, cooldownAfterEnd: true)?', src):
            out.append({"code": m.group(1), "id": m.group(2), "school": school, "name": m.group(3),
                        "cooldown": int(m.group(4)), "charge": int(m.group(5)), "enhanceable": m.group(6) == "true",
                        "cooldownAfterEnd": bool(m.group(7))})
        params = re.findall(r'params: \{([^}]*)\}', src)
        for sp, p in zip([s for s in out if s["school"] == school], params):
            sp["params"] = {k.strip(): float(v) for k, v in (x.split(":") for x in p.split(",") if ":" in x)}
        blurbs = re.findall(r'blurb: "([^"]+)"', src)
        for sp, b in zip([s for s in out if s["school"] == school], blurbs):
            sp["blurb"] = b
    return out


def clean():
    for d in (BP, RP):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)
    for sub in ("texts", "scripts"):
        os.makedirs(os.path.join(BP, sub), exist_ok=True)
    for sub in ("texts", "textures/entity/grimoire", "textures/particle", "render_controllers", "attachables",
                "animations/grimoire", "animation_controllers/grimoire", "models/entity/grimoire", "particles/grimoire"):
        os.makedirs(os.path.join(RP, sub), exist_ok=True)


def bundle():
    subprocess.run(["npx", "esbuild", "src/main.ts", "--bundle", "--format=esm", "--platform=neutral", "--target=es2022",
                    "--external:@minecraft/server", "--external:@minecraft/server-ui",
                    f"--outfile={os.path.join(BP, 'scripts', 'main.js')}", "--log-level=warning"], cwd=ROOT, check=True)


def zipdir(src, dst, prefix=""):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(src):
            for f in sorted(files):
                full = os.path.join(base, f)
                rel = os.path.relpath(full, src)
                z.write(full, os.path.join(prefix, rel) if prefix else rel)


def package():
    os.makedirs(DIST, exist_ok=True)
    bp_pack = os.path.join(DIST, "Grimoire_Imperial_Magic_BP.mcpack")
    rp_pack = os.path.join(DIST, "Grimoire_Imperial_Magic_RP.mcpack")
    zipdir(BP, bp_pack)
    zipdir(RP, rp_pack)
    addon = os.path.join(DIST, "Grimoire_Imperial_Magic.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in ((BP, "Grimoire_BP"), (RP, "Grimoire_RP")):
            for base, _, files in os.walk(src):
                for f in sorted(files):
                    full = os.path.join(base, f)
                    z.write(full, os.path.join(name, os.path.relpath(full, src)))
    return addon


def main():
    skip_sounds = "--no-sounds" in sys.argv
    clean()
    spells = spells_from_ts()
    assert len(spells) == 45, f"expected 45 spells, parsed {len(spells)}"
    packs.manifests(BP, RP)
    packs.items(BP)
    packs.recipes(BP)
    packs.blocks(BP, RP)
    packs.item_textures(RP)
    packs.lang(RP, BP, spells)
    icons.write_icons(RP, BP)
    book.write_books(RP)
    particle_ids = particles.write_particles(RP)
    sound_ids = [] if skip_sounds else sounds.write_sounds(RP)
    fogs.write_fogs(RP)
    playeranim.write(RP)
    fxdefs.dump(os.path.join(RP, "render_controllers", "grimoire_fx.render_controllers.json"), fxdefs.shared_render_controller())
    extra_rc = {}
    for fx in fxdefs.REGISTRY:
        fx.write(RP, BP)
        rc = fx.render_controller()
        if rc:
            extra_rc[f"controller.render.grimoire.{fx.name}"] = rc
    if extra_rc:
        fxdefs.dump(os.path.join(RP, "render_controllers", "grimoire_fx_variants.render_controllers.json"),
                    {"format_version": "1.10.0", "render_controllers": extra_rc})
    bundle()
    meta = {"spells": spells, "particles": particle_ids, "sounds": sound_ids,
            "constructs": [f.ident for f in fxdefs.REGISTRY]}
    with open(os.path.join(ROOT, ".build_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    addon = package()
    cubes = sum(f.model.cube_count() for f in fxdefs.REGISTRY)
    print(f"built {len(spells)} spells, {len(fxdefs.REGISTRY)} constructs ({cubes} cubes), "
          f"{len(particle_ids)} particles, {len(sound_ids)} sounds -> {os.path.relpath(addon, ROOT)} "
          f"({os.path.getsize(addon) // 1024} KiB)")


if __name__ == "__main__":
    main()
