"""
Docs previews rendered from the built pack files (python3 tools/build.py first). Not in-game screenshots.

    python3 tools/preview.py   -> docs/preview/*.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import art  # noqa: E402
import fruit_icon  # noqa: E402
import hold_sim  # noqa: E402
import render_preview as rp  # noqa: E402

RP = os.path.join(ROOT, "build", "Sekiyu_RP")
OUT = os.path.join(ROOT, "docs", "preview")


def geo(name):
    return rp.load_geo(os.path.join(RP, "models", "entity", "sekiyu", f"{name}.geo.json"))


def tex(name):
    return Image.open(os.path.join(RP, "textures", "entity", "sekiyu", f"{name}.png"))


def fit(g):
    pts = np.array([p for b in g["bones"] for c in b.get("cubes", []) for p in (np.array(c["origin"]), np.array(c["origin"]) + np.array(c["size"]))])
    lo, hi = pts.min(0), pts.max(0)
    return tuple((lo + hi) / 2), (hi - lo).max()


def tile(g, t, yaw, pitch, size, title, sub=None, hue=(70, 40, 20), zoom=0.82):
    ctr, span = fit(g)
    c, a, gl = rp.render(g, t, {}, yaw, pitch, size, size / span * zoom, ctr)
    return rp.label(rp.compose(c, a, gl, rp.backdrop(size, hue)), title, sub)


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    S = 520
    fruit, ftex = geo("fruit_relic"), tex("fruit")
    ref = fruit_icon.source().resize((S, S), Image.LANCZOS)
    refbg = rp.backdrop(S, (70, 40, 20)).convert("RGBA")
    refbg.alpha_composite(ref)
    sheet = Image.new("RGB", (S * 3, S))
    sheet.paste(rp.label(refbg.convert("RGB"), "approved reference art"), (0, 0))
    sheet.paste(tile(fruit, ftex, 0, 0, S, "3D model - front", "184 cubes, art projected onto the geometry"), (S, 0))
    sheet.paste(tile(fruit, ftex, 35, 18, S, "3D model - 3/4 view", "glowing fissures use the emissive material"), (S * 2, 0))
    sheet.save(os.path.join(OUT, "fruit_reference_vs_3d.png"))

    anim = json.load(open(os.path.join(RP, "animations", "sekiyu_fruit.animation.json")))["animations"]
    hg = geo("fruit")
    held = Image.new("RGB", (640, 720))
    for i, (view, an) in enumerate((("first", "animation.sekiyu.fruit.hold_first_person"), ("third", "animation.sekiyu.fruit.hold_third_person"))):
        img = hold_sim.render(view, hg, ftex, {"fruit": anim[an]["bones"]["fruit"]}, W=640, H=360)
        ImageDraw.Draw(img).text((8, 8), f"held fruit - {view} person (simulated from vanilla hand transforms)", fill=(0, 0, 0))
        held.paste(img, (0, i * 360))
    held.save(os.path.join(OUT, "fruit_held.png"))

    T = 360
    tiles = []
    for name, title, yaw, pitch in (("oil_body", "Petroleum Body overlay", 30, 10), ("puddle", "Infiltration puddle", 35, 35), ("serpent", "Black Serpent", 70, 10),
                                    ("tide", "Black Tide wave", 200, 18), ("prison", "Tar Prison", 35, 25), ("geyser", "Black Geyser", 35, 10), ("pool", "oil pool", 35, 40)):
        g = geo(name)
        tiles.append(tile(g, tex(name), yaw, pitch, T, title, "crude oil"))
        tiles.append(tile(g, tex(f"{name}_burning"), yaw, pitch, T, title, "ignited", hue=(120, 40, 10)))
    cols = 4
    sheet = Image.new("RGB", (T * cols, T * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * T, (i // cols) * T))
    sheet.save(os.path.join(OUT, "models_oil_and_burning.png"))

    icons = [fruit_icon.fruit_icon(128).resize((64, 64), Image.LANCZOS), art.core_icon().resize((64, 64), Image.NEAREST)] + [art.ui_icon(n).resize((64, 64), Image.NEAREST) for n in art.UI_ICONS]
    strip = Image.new("RGBA", (len(icons) * 68 + 4, 72), (139, 139, 139, 255))
    for i, ic in enumerate(icons):
        strip.alpha_composite(ic, (i * 68 + 4, 4))
    strip.save(os.path.join(OUT, "items_and_console_icons.png"))
    atlas = Image.new("RGBA", (512, 512), (150, 160, 170, 255))
    atlas.alpha_composite(art.particle_atlas().resize((512, 512), Image.NEAREST))
    atlas.save(os.path.join(OUT, "particle_atlas_x4.png"))
    print("previews ->", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
