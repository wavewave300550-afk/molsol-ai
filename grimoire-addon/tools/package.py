#!/usr/bin/env python3
"""Package the two packs into an importable .mcaddon (plus individual .mcpack files)."""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST = os.path.join(ROOT, "dist")
PACKS = [("behavior_packs/grimoire_bp", "Grimoire_Rebirth_of_the_Arcane_BP"),
         ("resource_packs/grimoire_rp", "Grimoire_Rebirth_of_the_Arcane_RP")]
SKIP = (".DS_Store", "Thumbs.db")


def files(src):
    for r, _d, fs in os.walk(src):
        for f in sorted(fs):
            if f in SKIP or f.endswith((".wav", ".pyc")):
                continue
            p = os.path.join(r, f)
            yield p, os.path.relpath(p, src).replace(os.sep, "/")


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


if __name__ == "__main__":
    main()
