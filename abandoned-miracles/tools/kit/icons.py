"""icons.py - 16x16 item icons authored as character grids (one char per pixel, '.' = transparent)."""
from __future__ import annotations

from typing import Dict, Sequence

from PIL import Image


def icon(rows: Sequence[str], palette: Dict[str, str]) -> Image.Image:
    h, w = len(rows), max(len(r) for r in rows)
    if (w, h) != (16, 16):
        raise ValueError(f"icon must be 16x16, got {w}x{h}")
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row.ljust(16, ".")):
            if ch in (".", " "):
                continue
            c = palette[ch].lstrip("#")
            px[x, y] = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)
    return img


def seal(sigil: Sequence[str], rim: str, wax: str, wax_dark: str, wax_light: str, mark: str) -> Image.Image:
    """A wax seal disc carrying an 8x8 sigil (rows of '#'/'.')."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()

    def col(h):
        h = h.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    for y in range(16):
        for x in range(16):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            if d < 7.6:
                c = col(rim) if d > 6.4 else col(wax)
                if 5.2 < d <= 6.4:
                    c = col(wax_dark)
                if d <= 5.2 and (x + y) < 12 and d > 3.6:
                    c = col(wax_light)
                px[x, y] = c
    for sy, row in enumerate(sigil):
        for sx, ch in enumerate(row):
            if ch == "#":
                px[4 + sx, 4 + sy] = col(mark)
    return img
