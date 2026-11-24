"""
Render the documentation images from the real models, textures and arena blueprint.

    python3 tools/build.py && python3 tools/preview.py      -> docs/images/*.png

Software renders (orthographic, no shading model of the game), so colours and
lighting differ a little from Minecraft, but geometry, proportions, textures
and damage states are the real ones shipped in the packs.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

import arena_preview  # noqa: E402
import models  # noqa: E402
import pixels  # noqa: E402
from modelkit import render_preview  # noqa: E402

OUT = os.path.join(ROOT, "docs", "images")
TMP = os.path.join(ROOT, "build", ".preview")
BG = (30, 28, 38, 255)


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle((0, img.size[1] - 30, img.size[0], img.size[1]), fill=(20, 18, 26, 255))
    d.text((10, img.size[1] - 22), text, fill=(246, 214, 140, 255))
    return img


def sheet(images, cols, cell):
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGBA", (cols * cell, rows * cell), BG)
    for i, im in enumerate(images):
        canvas.paste(im.resize((cell, cell), Image.LANCZOS), ((i % cols) * cell, (i // cols) * cell))
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    emp = models.emperor()
    names = ["I - pristine porcelain", "II - kintsugi", "III - shattered"]
    shots = []
    for v in range(3):
        p = os.path.join(TMP, f"e{v}.png")
        render_preview([emp], p, yaw=-35, pitch=18, size=720, extra_rot=models.IDLE_POSE, variant=v, bg=BG)
        shots.append(label(Image.open(p).convert("RGBA"), f"Phase {names[v]}"))
    sheet(shots, 3, 720).save(os.path.join(OUT, "emperor_phases.png"))
    hide = tuple(f"seg{i}" for i in range(1, models.SEGMENTS + 1))
    p = os.path.join(TMP, "head.png")
    render_preview([emp], p, yaw=-28, pitch=10, size=900, hidden=hide + ("arm_r", "arm_l"), variant=0, bg=BG)
    p2 = os.path.join(TMP, "face.png")
    render_preview([emp], p2, yaw=0, pitch=6, size=900, hidden=hide, variant=2, bg=BG)
    sheet([label(Image.open(p).convert("RGBA"), "Mask face veiled by the mianliu crown"),
           label(Image.open(p2).convert("RGBA"), "Phase III: the mask's eyes open")], 2, 720).save(os.path.join(OUT, "emperor_head.png"))
    p3 = os.path.join(TMP, "side.png")
    render_preview([emp], p3, yaw=-90, pitch=4, size=1200, extra_rot=models.IDLE_POSE, variant=1, bg=BG)
    Image.open(p3).save(os.path.join(OUT, "emperor_side.png"))
    minis = []
    for name in ("edict_tablet", "shard", "rubble", "severed_claw", "courtier"):
        m = models.ALL[name]()
        p = os.path.join(TMP, f"{name}.png")
        render_preview([m], p, yaw=-30 if name != "courtier" else 20, pitch=18, size=420, bg=BG)
        minis.append(label(Image.open(p).convert("RGBA"), name.replace("_", " ")))
    sheet(minis, 5, 360).save(os.path.join(OUT, "fragments.png"))
    # blocks + icons
    tiles = [pixels.block_texture(k).resize((96, 96), Image.NEAREST) for k in pixels.BLOCK_TEXTURES]
    icons = [pixels.icon(k).resize((96, 96), Image.NEAREST) for k in pixels.ICONS]
    canvas = Image.new("RGBA", (len(tiles) * 104 + 8, 2 * 104 + 8), BG)
    for i, t in enumerate(tiles):
        canvas.paste(t, (8 + i * 104, 8))
    for i, t in enumerate(icons):
        canvas.alpha_composite(t, (8 + i * 104, 112))
    canvas.save(os.path.join(OUT, "blocks_and_items.png"))
    # arena from the compiled blueprint
    js = os.path.join(TMP, "js")
    subprocess.run([os.path.join(ROOT, "node_modules", ".bin", "tsc"), "-p", os.path.join(ROOT, "tsconfig.json"), "--outDir", js], check=True)
    dump = os.path.join(TMP, "arena.json")
    subprocess.run(["node", os.path.join(HERE, "arena_dump.mjs"), js, dump], check=True, capture_output=True)
    data = json.load(open(dump))
    arena_preview.top_down(data, os.path.join(OUT, "arena_plan.png"))
    arena_preview.iso(data, os.path.join(OUT, "arena_iso.png"))
    arena_preview.iso(data, os.path.join(OUT, "arena_iso_fractured.png"), fractured=True)
    Image.open(os.path.join(ROOT, "build", "Porcelain_RP", "pack_icon.png")).save(os.path.join(OUT, "pack_icon.png"))
    print("docs images in", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
