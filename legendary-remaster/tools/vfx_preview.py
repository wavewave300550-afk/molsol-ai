"""Render docs/preview_vfx.png: the spectacle sprites tinted the way the scripts tint them."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fx_atlas2  # noqa: E402

CELLS = [
    ("Taotie", (1.0, 0.45, 0.12)), ("Nidhogg", (0.45, 1.0, 0.32)), ("Hanuman", (1.0, 0.78, 0.25)),
    ("Alicorn", (0.78, 0.62, 1.0)), ("Tenko", (0.25, 0.66, 1.0)), ("The Word", (1.0, 0.94, 0.68)),
    ("crack", (1.0, 0.45, 0.12)), ("rays", (1.0, 0.94, 0.68)),
    ("lightning", (0.62, 0.9, 1.0)), ("lightning", (1.0, 0.94, 0.68)), ("dome rim", (0.78, 0.62, 1.0)),
    ("flare", (1.0, 1.0, 1.0)), ("falling star", (1.0, 0.96, 0.75)), ("sakura", (1.0, 0.72, 0.92)),
    ("wind", (0.78, 1.0, 0.93)), ("force dome", (0.45, 1.0, 0.32)),
]


def main(out):
    tile = 200
    W = H = tile * 4
    y = np.linspace(0, 1, H)[:, None]
    bg = np.zeros((H, W, 3), np.float32)
    bg[..., 0] = 0.05 + 0.04 * y
    bg[..., 1] = 0.04 + 0.03 * y
    bg[..., 2] = 0.10 + 0.08 * y
    for i, (label, col) in enumerate(CELLS):
        r, c = divmod(i, 4)
        a, lum = fx_atlas2.CELLS[r][c]()
        a = np.array(Image.fromarray((a * 255).astype(np.uint8)).resize((tile - 30, tile - 30), Image.LANCZOS), np.float32) / 255
        lum = np.array(Image.fromarray((lum * 255).astype(np.uint8)).resize((tile - 30, tile - 30), Image.LANCZOS), np.float32) / 255
        y0, x0 = r * tile + 6, c * tile + 15
        for ch in range(3):
            bg[y0:y0 + tile - 30, x0:x0 + tile - 30, ch] += a * lum * col[ch] * 1.15
    img = Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for i, (label, _) in enumerate(CELLS):
        r, c = divmod(i, 4)
        d.text((c * tile + 12, r * tile + tile - 20), label, fill=(225, 220, 240))
    img.save(out)
    return out


if __name__ == "__main__":
    print(main(sys.argv[1]))
