"""
Item texture for the Jōki Jōki no Mi, made from the reference artwork (art/joki_fruit_reference.png).

The art already has a transparent background. It is cropped to its silhouette, padded to a
square, downsampled in premultiplied alpha (no dark fringes), given a little extra contrast so the
spirals survive at item size, then cut to hard alpha with a 1px dark outline so it reads well both
in the inventory (blended) and in the hand (alpha-tested).
"""
import os

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "art", "joki_fruit_reference.png")


def _premul_resize(im: Image.Image, size: int) -> Image.Image:
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0
    rgb = a[..., :3] * a[..., 3:4]
    pm = Image.fromarray(np.dstack([rgb, a[..., 3:4]]).__mul__(255).clip(0, 255).astype(np.uint8), "RGBA")
    small = np.asarray(pm.resize((size, size), Image.LANCZOS)).astype(np.float32) / 255.0
    alpha = small[..., 3:4]
    out_rgb = np.where(alpha > 1e-4, small[..., :3] / np.maximum(alpha, 1e-4), 0)
    return Image.fromarray((np.dstack([out_rgb, alpha]) * 255).clip(0, 255).astype(np.uint8), "RGBA")


def source() -> Image.Image:
    im = Image.open(SRC).convert("RGBA")
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 40)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    im = im.crop(box)
    w, h = im.size
    side = max(w, h)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - w) // 2, (side - h) // 2))
    return sq


def fruit_icon(size: int = 128) -> Image.Image:
    sq = source()
    # pad so the outline never touches the border
    pad = int(sq.size[0] * 0.03)
    big = Image.new("RGBA", (sq.size[0] + 2 * pad, sq.size[1] + 2 * pad), (0, 0, 0, 0))
    big.paste(sq, (pad, pad))
    # pre-sharpen the detail at an intermediate size, then go down
    mid = _premul_resize(big, size * 4)
    rgb = mid.convert("RGB")
    # light smoothing first so the 4x->1x step does not alias the fine glossy highlights
    rgb = rgb.filter(ImageFilter.GaussianBlur(0.7))
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=3))
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Color(rgb).enhance(1.12)
    mid = Image.merge("RGBA", (*rgb.split(), mid.getchannel("A")))
    small = _premul_resize(mid, size)
    arr = np.asarray(small).astype(np.int32).copy()
    alpha = arr[..., 3]
    solid = alpha >= 90
    arr[..., 3] = np.where(solid, 255, 0)
    # 1px outline around the silhouette, tinted by the pixels it borders (dark red by the fruit,
    # cool grey by the steam) instead of a flat black line
    pad_s = np.pad(solid, 1)
    pad_c = np.pad(arr[..., :3], ((1, 1), (1, 1), (0, 0)))
    acc = np.zeros(arr[..., :3].shape, np.float64)
    cnt = np.zeros(solid.shape, np.float64)
    for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2)):
        m = pad_s[dy:dy + solid.shape[0], dx:dx + solid.shape[1]]
        acc += pad_c[dy:dy + solid.shape[0], dx:dx + solid.shape[1]] * m[..., None]
        cnt += m
    edge = (cnt > 0) & ~solid
    tint = acc / np.maximum(cnt, 1)[..., None]
    arr[..., :3] = np.where(edge[..., None], (tint * 0.32).astype(np.int32), arr[..., :3])
    arr[..., 3] = np.where(edge, 255, arr[..., 3])
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")


def pack_icon(size: int = 256) -> Image.Image:
    """Pack icon: the fruit over a dark boiler-room gradient with a hot glow behind it."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.52) ** 2)
    glow = np.clip(1.0 - r * 2.0, 0, 1) ** 1.6
    bg = np.zeros((size, size, 4), np.float32)
    bg[..., 0] = 0.10 + 0.75 * glow
    bg[..., 1] = 0.04 + 0.22 * glow ** 1.5
    bg[..., 2] = 0.05 + 0.05 * glow
    bg[..., 3] = 1.0
    base = Image.fromarray((bg * 255).astype(np.uint8), "RGBA")
    fruit = _premul_resize(source(), int(size * 0.86))
    base.alpha_composite(fruit, ((size - fruit.size[0]) // 2, (size - fruit.size[1]) // 2 + 4))
    return base


if __name__ == "__main__":
    fruit_icon().save("joki_fruit_preview.png")
    print("wrote joki_fruit_preview.png")
