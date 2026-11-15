"""Design review sheets for a race form, straight from the model code (no pack build needed).

    python3 tools/review.py nurariten --out /tmp/review [--variants base,court] [--pose name]

Per variant: front / three-quarter / side / back at the same scale, the same four as
black silhouettes (does the shape read without texture?), and a small "in-game
distance" view next to the vanilla player and the accepted races 001-003.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

from kit.render import render, sheet  # noqa: E402
from kit.tex import paint  # noqa: E402

BG = (236, 234, 230)
HIDE = ["r_arm_fp", "l_arm_fp"]
RP = os.path.join(ROOT, "packs", "PlayableRaces_RP", "textures", "plrace", "races")


def textures(mod, m):
    out = {}
    for name, params in mod.TEXTURES.items():
        out[name] = paint(m, mod.materials(), params)
    return out


def silhouette(tex: Image.Image) -> Image.Image:
    a = tex.getchannel("A")
    black = Image.new("RGBA", tex.size, (24, 24, 28, 255))
    black.putalpha(a.point(lambda v: 255 if v > 0 else 0))
    return black


def label(img, text):
    ImageDraw.Draw(img).text((8, 6), text, fill=(30, 30, 34))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("race")
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="base")
    ap.add_argument("--scale", type=float, default=7.0)
    ap.add_argument("--cy", type=float, default=17.0)
    ap.add_argument("--size", default="300x400")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    mod = importlib.import_module(f"models.{args.race}")
    m = mod.build()
    tex = textures(mod, m)
    W, H = (int(v) for v in args.size.split("x"))
    for v in args.variants.split(","):
        t = tex[mod.VARIANT_TEXTURE.get(v, "base")]
        sil = silhouette(t)
        imgs, labs = [], []
        for yaw, lab in ((0, "front"), (35, "three-quarter"), (90, "side"), (180, "back")):
            imgs.append(render(m, t, variant=v, yaw=yaw, pitch=8, size=(W, H), scale=args.scale,
                               center=(0, args.cy, 1), hide=HIDE, bg=BG))
            labs.append(f"{v} - {lab}")
        for yaw, lab in ((0, "front"), (35, "three-quarter"), (90, "side"), (180, "back")):
            imgs.append(render(m, sil, variant=v, yaw=yaw, pitch=8, size=(W, H), scale=args.scale,
                               center=(0, args.cy, 1), hide=HIDE, bg=(250, 250, 250), bloom=False))
            labs.append(f"silhouette - {lab}")
        nb, nc = m.stats(v)
        sheet(imgs, cols=4, labels=labs, title=f"{args.race} [{v}] - {nb} bones / {nc} cubes, atlas {m.tex_w}x{m.tex_h}") \
            .save(os.path.join(args.out, f"{args.race}_{v}.png"))
        # in-game distance: the creature next to the accepted races, small, three-quarter view
        cells = []
        for other, tv in (("salamander", "base"), ("golem", "base"), ("jackalope", "base")):
            try:
                om = importlib.import_module(f"models.{other}").build()
                ot = Image.open(os.path.join(RP, other, f"{other}_{tv}.png")).convert("RGBA")
                cells.append(label(render(om, ot, variant="base", yaw=30, pitch=10, size=(170, 230), scale=3.6,
                                          center=(0, 20, 1), hide=HIDE, bg=BG), other))
            except Exception as e:  # pragma: no cover - review helper only
                print("skip", other, e)
        cells.append(label(render(m, t, variant=v, yaw=30, pitch=10, size=(170, 230), scale=3.6,
                                  center=(0, 20, 1), hide=HIDE, bg=BG), args.race))
        cells.append(label(render(m, t, variant=v, yaw=200, pitch=18, size=(170, 230), scale=3.6,
                                  center=(0, 20, 1), hide=HIDE, bg=BG), "from behind (3rd person)"))
        sheet(cells, cols=5, title="in-game distance, next to races 001-003").save(os.path.join(args.out, f"{args.race}_{v}_distance.png"))
        # texture atlas
        big = t.resize((t.width * 3, t.height * 3), Image.NEAREST)
        bg = Image.new("RGBA", big.size, (40, 40, 46, 255))
        rgb = big.copy()
        rgb.putalpha(big.getchannel("A").point(lambda a: 255 if a > 0 else 0))
        bg.alpha_composite(rgb)
        bg.convert("RGB").save(os.path.join(args.out, f"{args.race}_atlas_{mod.VARIANT_TEXTURE.get(v, 'base')}.png"))
        print(f"{v}: {nb} bones, {nc} cubes")


if __name__ == "__main__":
    main()
