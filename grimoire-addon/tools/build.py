#!/usr/bin/env python3
"""Asset build: runs every module in tools/assets/ and writes pack files.

  python3 tools/build.py                 # build everything
  python3 tools/build.py --only dw_seraph,books
  python3 tools/build.py --preview       # also write contact sheets to tools/_preview/
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kit.pack import PREVIEW, Pack  # noqa: E402
from kit.render import render, sheet  # noqa: E402


class Previewer:
    def __init__(self, enabled):
        self.enabled = enabled

    def __call__(self, name, model, poses=None, views=((25, 18), (155, 18), (-90, 8), (0, 80)), cell=(400, 400),
                 **kw):
        """poses: list of None | pose dict | (Anim, t)."""
        if not self.enabled:
            return
        ps = []
        for p in (poses or [None]):
            if isinstance(p, tuple):
                ps.append(p[0].pose(p[1]))
            elif isinstance(p, list):  # merge several (anim, t)
                merged = {}
                for a, t in p:
                    for b, (r, pp, s) in a.pose(t).items():
                        if b in merged:
                            r0, p0, s0 = merged[b]
                            merged[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + pp[i] for i in range(3)),
                                         tuple(s0[i] * s[i] for i in range(3)))
                        else:
                            merged[b] = (r, pp, s)
                ps.append(merged)
            else:
                ps.append(p)
        os.makedirs(PREVIEW, exist_ok=True)
        sheet(model, views=views, poses=ps, cell=cell, **kw).save(os.path.join(PREVIEW, f"{name}.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    mods = sorted(f[:-3] for f in os.listdir(os.path.join(HERE, "assets")) if f.endswith(".py") and not f.startswith("_"))
    if args.only:
        want = set(args.only.split(","))
        missing = want - set(mods)
        if missing:
            sys.exit(f"unknown asset modules: {sorted(missing)}")
        mods = [m for m in mods if m in want]
    pack = Pack()
    pack.preview = Previewer(args.preview)
    for m in mods:
        t0 = time.time()
        mod = importlib.import_module(f"assets.{m}")
        mod.build(pack)
        print(f"  {m:28s} {time.time() - t0:5.1f}s")
    pack.flush()
    print(f"built {len(pack.actors)} actors, {len(pack.models)} models, {len(pack.sound_defs)} sounds")


if __name__ == "__main__":
    main()
