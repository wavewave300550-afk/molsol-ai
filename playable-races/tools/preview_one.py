"""Quick iteration helper: render one race model in several views/variants.

usage: python3 tools/preview_one.py <race> <out.png> [variant ...]
"""
import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit.tex import paint  # noqa: E402
from kit.render import render, sheet  # noqa: E402


def main():
    race = sys.argv[1]
    out = sys.argv[2]
    variants = sys.argv[3:] or ["base"]
    mod = importlib.import_module(f"models.{race}")
    t0 = time.time()
    m = mod.build()
    print(f"built {race}: atlas {m.tex_w}x{m.tex_h}, bones/cubes {m.stats()}  ({time.time()-t0:.1f}s)")
    imgs, labels = [], []
    texcache = {}
    for v in variants:
        tv = mod.VARIANT_TEXTURE.get(v, "base")
        if tv not in texcache:
            texcache[tv] = paint(m, mod.materials(), mod.TEXTURES[tv])
        tex = texcache[tv]
        hide = ["r_arm_fp", "l_arm_fp"]
        for yaw, lab in ((0, "front"), (35, "3/4"), (90, "side"), (180, "back")):
            imgs.append(render(m, tex, variant=v, yaw=yaw, pitch=8, size=(300, 380),
                               hide=hide, scale=float(os.environ.get("PSCALE", "8")), center=(0, float(os.environ.get("PCY", "19")), 2)))
            labels.append(f"{v}: {lab}")
    sheet(imgs, cols=4, labels=labels).save(out)
    texcache[next(iter(texcache))].save(out.replace(".png", "_atlas.png"))
    print("wrote", out, f"({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
