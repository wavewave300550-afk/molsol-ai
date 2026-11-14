#!/usr/bin/env python3
"""Package the two packs into an importable .mcaddon (plus individual .mcpack files) and a
ready-to-play .mcworld that has both packs embedded."""
from __future__ import annotations

import json
import os
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST = os.path.join(ROOT, "dist")
PACKS = [("behavior_packs/grimoire_bp", "Grimoire_Rebirth_of_the_Arcane_BP"),
         ("resource_packs/grimoire_rp", "Grimoire_Rebirth_of_the_Arcane_RP")]
SKIP = (".DS_Store", "Thumbs.db")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from kit import nbt  # noqa: E402


def files(src):
    for r, _d, fs in os.walk(src):
        for f in sorted(fs):
            if f in SKIP or f.endswith((".wav", ".pyc")):
                continue
            p = os.path.join(r, f)
            yield p, os.path.relpath(p, src).replace(os.sep, "/")


def _patch_level(data, name):
    """Rename the template world and turn cheats on (for /grimoire:reset and friends).  Everything else,
    including the version fields, stays as the dedicated server that generated it wrote it."""
    doc = nbt.load(data)
    r = doc["root"]
    nbt.set(r, "LevelName", nbt.STRING, name)
    nbt.set(r, "cheatsEnabled", nbt.BYTE, 1)
    nbt.set(r, "commandsEnabled", nbt.BYTE, 1)
    return nbt.dump(doc)


def world(version):
    """A ready-to-play flat creative world with both packs embedded (generated once by a real
    Bedrock Dedicated Server 1.26.62, kept in tools/world_template; minimum client 1.26.60)."""
    tpl = os.path.join(ROOT, "tools", "world_template")
    vtext = ".".join(str(v) for v in version)
    name = f"Grimoire Test {vtext}"
    out = os.path.join(DIST, "Grimoire_Test_World.mcworld")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        level = _patch_level(open(os.path.join(tpl, "level.dat"), "rb").read(), name)
        z.writestr("level.dat", level)
        z.writestr("level.dat_old", level)
        z.writestr("levelname.txt", name)
        for f in sorted(os.listdir(os.path.join(tpl, "db"))):
            z.write(os.path.join(tpl, "db", f), f"db/{f}")
        for (src, pname), kind in zip(PACKS, ("behavior_packs", "resource_packs")):
            full = os.path.join(ROOT, src)
            man = json.load(open(os.path.join(full, "manifest.json"), encoding="utf-8"))
            z.writestr(f"world_{kind}.json", json.dumps([{"pack_id": man["header"]["uuid"], "version": man["header"]["version"]}]))
            for p, r in files(full):
                z.write(p, f"{kind}/{pname}/{r}")
    print(f"  {os.path.basename(out):48s} {os.path.getsize(out) / 1e6:6.2f} MB")


def main():
    os.makedirs(DIST, exist_ok=True)
    addon = os.path.join(DIST, "Grimoire_Rebirth_of_the_Arcane.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as za:
        for src, name in PACKS:
            full = os.path.join(ROOT, src)
            single = os.path.join(DIST, name + ".mcpack")
            with zipfile.ZipFile(single, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zp:
                for p, r in files(full):
                    zp.write(p, r)
                    za.write(p, f"{name}/{r}")
            print(f"  {os.path.basename(single):48s} {os.path.getsize(single) / 1e6:6.2f} MB")
    print(f"  {os.path.basename(addon):48s} {os.path.getsize(addon) / 1e6:6.2f} MB")
    man = json.load(open(os.path.join(ROOT, PACKS[0][0], "manifest.json"), encoding="utf-8"))
    world(man["header"]["version"])


if __name__ == "__main__":
    main()
