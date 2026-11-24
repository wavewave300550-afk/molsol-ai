"""Render documentation images from the real models / animations:  python3 tools/docs.py"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import anims  # noqa: E402
import icons  # noqa: E402
import models  # noqa: E402
import particles  # noqa: E402
from modelkit import render  # noqa: E402

OUT = os.path.join(ROOT, "docs", "images")
TMP = os.path.join(ROOT, "build", ".docs")
BG = (28, 31, 44, 255)


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    d.rectangle([0, im.height - 26, im.width, im.height], fill=(16, 18, 26, 255))
    d.text((10, im.height - 20), text, fill=(236, 226, 196, 255))
    return im


def row(cells, path):
    w = sum(c.width for c in cells)
    h = max(c.height for c in cells)
    out = Image.new("RGBA", (w, h), BG)
    x = 0
    for c in cells:
        out.paste(c, (x, 0))
        x += c.width
    out.save(path)
    return path


def frame(sampler, act_name, t, variant, glow, yaw=30, size=420, span=80, center=(0, 26, 4)):
    act = next(a for a in anims.actions() if a.name == act_name)
    baked = sampler.bake(act)
    n = len(next(iter(baked.values())))
    f = min(n - 1, int(round(t * anims.FPS)))
    pose = {bone: ch[f] for bone, ch in baked.items()}
    p = os.path.join(TMP, f"{act_name}_{f}.png")
    render([(sampler.model, pose, variant, glow, (0, 0, 0))], p, yaw=yaw, pitch=10, size=size, bg=BG, span=span,
           center=center)
    return Image.open(p).convert("RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    s = anims.Sampler()
    # ---- the two phases + the procession echo
    cells = []
    for title, act, t, var, glow, yaw in (("Phase I - The Maiden Standard", "taunt", 0.0, "base", "glow1", 28),
                                          ("Phase II - The Saint of the Burning Road", "phase_rise", 2.35, "burning", "glow2", -28),
                                          ("Martyr's Procession echo", "taunt", 0.0, "ghost", None, 200)):
        cells.append(label(frame(s, act, t, var, glow, yaw=yaw, size=460), title))
    row(cells, os.path.join(OUT, "joan_phases.png"))
    # ---- signature moves
    picks = [("melee_sweep", 0.45, "Standard Sweep"), ("trail_dash", 0.1, "Banner Trail"), ("surge_ride", 0.1, "Pilgrim's Surge"),
             ("orleans_hold", 0.3, "Road of Orleans"), ("false_point", 0.85, "False Salvation"), ("converge_throw", 0.34, "Convergence"),
             ("detour_spin", 0.15, "Heaven's Detour"), ("procession_hold", 0.3, "Martyr's Procession"),
             ("ult_channel", 0.4, "Road to the Stake"), ("death", 5.4, "Freed from the Road")]
    tiles = []
    for name, t, cap in picks:
        p2 = name in ("ult_channel",)
        var, glow = ("burning", "glow2") if p2 else (("white", "glow1") if name == "death" else ("base", "glow1"))
        tiles.append(label(frame(s, name, t, var, glow, size=300, span=100, center=(0, 32, 4)), cap))
    top = row(tiles[:5], os.path.join(TMP, "a.png"))
    bot = row(tiles[5:], os.path.join(TMP, "b.png"))
    a, b = Image.open(top), Image.open(bot)
    sheet = Image.new("RGBA", (max(a.width, b.width), a.height + b.height), BG)
    sheet.paste(a, (0, 0))
    sheet.paste(b, (0, a.height))
    sheet.save(os.path.join(OUT, "joan_moves.png"))
    # ---- helpers of the fight
    cells = []
    for name, var, glow, cap, yaw in (("standard", "ghost", "glow1", "Phantom Standard", 40),
                                      ("waystone", "base", "glow2", "Lily Waystone (burning)", 25),
                                      ("waystone", "base", "glow1", "Lily Waystone (turned)", 25),
                                      ("stake", "burning", "glow2", "The Stake", 30),
                                      ("seraph", "base", "glow1", "Seraph Light", 20)):
        m = models.ALL[name]()
        p = os.path.join(TMP, f"e_{name}_{glow}.png")
        render([(m, {}, var, glow, (0, 0, 0))], p, yaw=yaw, pitch=16, size=300, bg=BG)
        cells.append(label(Image.open(p).convert("RGBA"), cap))
    row(cells, os.path.join(OUT, "entities.png"))
    # ---- items, spawn egg, particle atlas
    strip = Image.new("RGBA", (5 * 140, 170), BG)
    for i, (fn, cap) in enumerate(((icons.banner_icon, "Banner of Divine Paths"), (icons.heart_icon, "Unburnt Heart"),
                                   (icons.standard_icon, "Pilgrim's Standard"), (icons.spawn_egg, "Spawn egg"))):
        im = fn().resize((128, 128), Image.NEAREST)
        strip.alpha_composite(im, (6 + i * 140, 6))
        ImageDraw.Draw(strip).text((6 + i * 140, 145), cap, fill=(236, 226, 196, 255))
    atlas = particles.atlas().resize((128, 128), Image.LANCZOS)
    tile = Image.new("RGBA", (128, 128), (40, 52, 96, 255))
    tile.alpha_composite(atlas)
    strip.alpha_composite(tile, (6 + 4 * 140, 6))
    ImageDraw.Draw(strip).text((6 + 4 * 140, 145), "Particle atlas", fill=(236, 226, 196, 255))
    strip.save(os.path.join(OUT, "items.png"))
    icons.pack_icon().save(os.path.join(TMP, "bg.png"))
    print("docs images written to", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
