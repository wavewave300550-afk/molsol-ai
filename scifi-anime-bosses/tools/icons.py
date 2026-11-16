"""icons.py - 16x16 item icons (procedural pixel art) for the VESPER-0 add-on."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

OUT = (40, 22, 10, 255)


def _canvas():
    return np.zeros((16, 16, 4), np.uint8)


def _put(img, x, y, c):
    if 0 <= x < 16 and 0 <= y < 16:
        img[y, x] = c


def _outline(img, color=(26, 18, 34, 255)):
    a = img[..., 3] > 0
    out = np.zeros_like(a)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        out |= np.roll(np.roll(a, dx, 1), dy, 0)
    edge = out & ~a
    img[edge] = color
    return img


def psalter():
    img = _canvas()
    gold, gold_d, gold_h = (227, 179, 65, 255), (150, 100, 24, 255), (255, 236, 160, 255)
    page, page_d = (240, 236, 224, 255), (200, 192, 172, 255)
    cyan, cyan_h = (79, 232, 255, 255), (216, 251, 255, 255)
    for y in range(2, 14):
        for x in range(3, 13):
            _put(img, x, y, gold)
    for y in range(3, 13):
        _put(img, 3, y, gold_d)
        _put(img, 12, y, gold_d)
    for x in range(3, 13):
        _put(img, x, 2, gold_h)
        _put(img, x, 13, gold_d)
    for y in range(3, 13):
        _put(img, 13, y, page if y % 2 else page_d)
    # glowing ring emblem with an eye
    cx, cy = 7.5, 7.5
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - cx, y - cy)
            if 2.3 < d < 3.5 and 3 <= x <= 12:
                _put(img, x, y, cyan)
    _put(img, 7, 7, cyan_h)
    _put(img, 8, 7, cyan_h)
    _put(img, 7, 8, (20, 30, 40, 255))
    _put(img, 8, 8, (20, 30, 40, 255))
    for x in (5, 10):
        _put(img, x, 3, cyan)
    return _outline(img)


def halo():
    img = _canvas()
    white, gold, gold_d = (240, 236, 222, 255), (227, 179, 65, 255), (140, 92, 20, 255)
    cyan = (79, 232, 255, 255)
    for y in range(16):
        for x in range(16):
            dx, dy = (x - 7.5) / 6.8, (y - 7.5) / 4.6
            d = math.hypot(dx, dy)
            if 0.66 < d < 1.0:
                ang = math.degrees(math.atan2(dy, dx)) % 360
                c = white if d > 0.8 else gold
                if y > 9:
                    c = gold_d if d < 0.8 else gold
                if int(ang) % 60 < 10:
                    c = cyan
                _put(img, x, y, c)
    for (x, y) in ((7, 2), (8, 2), (14, 7), (1, 8)):
        _put(img, x, y, (79, 232, 255, 255))
    return _outline(img)


def alloy():
    img = _canvas()
    top, mid, low = (250, 248, 240, 255), (214, 206, 186, 255), (160, 146, 120, 255)
    vio = (179, 92, 255, 255)
    for y in range(5, 12):
        x0 = 2 + max(0, 6 - y)
        x1 = 13 - max(0, 6 - y)
        for x in range(x0, x1 + 1):
            c = top if y <= 6 else (mid if y < 10 else low)
            _put(img, x, y, c)
    for x in range(3, 13):
        _put(img, x, 11, low)
    for (x, y) in ((5, 6), (6, 6), (9, 8), (10, 8), (11, 9)):
        _put(img, x, y, vio)
    _put(img, 4, 7, (227, 179, 65, 255))
    _put(img, 12, 10, (227, 179, 65, 255))
    return _outline(img)


ICONS = {"astral_psalter": psalter, "orison_halo": halo, "vesper_alloy": alloy}


def save_all(dirpath):
    import os
    os.makedirs(dirpath, exist_ok=True)
    for k, fn in ICONS.items():
        Image.fromarray(fn(), "RGBA").save(os.path.join(dirpath, f"{k}.png"))
