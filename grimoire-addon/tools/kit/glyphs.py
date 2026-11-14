"""Original invented scripts used as magical lettering (no real-world alphabet or scripture).

FIRST_WORD : flowing celestial letterforms (stems ending in orbs) for Divine Word magic.
DRACONIC   : angular claw-cut runes for the dragon codex.
DREAM      : small pictograms (moon, star, key, door, stair, bed, window, closed eye).
Glyphs are lists of equal-length strings, '#' = ink.
"""
from __future__ import annotations

import numpy as np

FIRST_WORD = [
    ["  #  ", " ### ", "  #  ", "  #  ", "# # #", " ### ", "  #  "],
    ["#   #", "#   #", " # # ", "  #  ", "  #  ", " ### ", "#   #"],
    [" ### ", "#   #", "    #", "  ## ", "    #", "#   #", " ### "],
    ["#    ", "#  # ", "# ###", "#  # ", "#    ", "#   #", " ### "],
    [" ### ", "# # #", "  #  ", " ### ", "  #  ", "  #  ", " # # "],
    ["#   #", " # # ", "  #  ", "#####", "  #  ", " # # ", "#   #"],
    ["  #  ", " # # ", "#   #", "# # #", "#   #", " # # ", "  #  "],
    ["#####", "    #", "  ###", "    #", "  # #", "  # #", "###  "],
    [" #   ", "###  ", " #   ", " ####", " #  #", " #  #", "##  #"],
    ["#   #", "## ##", "# # #", "  #  ", "  #  ", " # # ", "#   #"],
    ["  ## ", " #   ", "#####", " #   ", "  ## ", "    #", " ### "],
    [" # # ", "#####", " # # ", "  #  ", " ### ", "#   #", " ### "],
    ["###  ", "  #  ", "  ###", "    #", "  ###", "  #  ", "###  "],
    ["  #  ", "# # #", "# # #", " ### ", "  #  ", "#   #", "#####"],
    [" ### ", "#   #", "# # #", "#   #", " # # ", " # # ", "## ##"],
    ["#    ", "##   ", "# #  ", "#  # ", "#####", "   # ", "  ###"],
    ["  #  ", "  #  ", "#####", "  #  ", " # # ", "#   #", "  #  "],
    [" ####", "#    ", "# ## ", "#  # ", "#    ", "#   #", " ### "],
]

DRACONIC = [
    ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    ["#####", " #   ", "  #  ", "   # ", "  #  ", " #   ", "#####"],
    ["  #  ", " # # ", "#   #", "  #  ", "  #  ", "  #  ", "  #  "],
    ["#    ", "##   ", "# #  ", "#  # ", "# #  ", "##   ", "#    "],
    ["# # #", "# # #", "# # #", " ### ", "  #  ", "  #  ", "  #  "],
    ["    #", "   ##", "  # #", " #  #", "#####", "    #", "    #"],
    ["#   #", " # # ", "  #  ", " # # ", "#   #", "#   #", "#   #"],
    ["#####", "#    ", "###  ", "#    ", "#    ", "#   #", "#####"],
    ["  #  ", " ##  ", "# #  ", "  #  ", "  # #", "  ## ", "  #  "],
    ["#   #", "## ##", "# # #", "#   #", " # # ", "  #  ", "  #  "],
    [" ####", "#    ", " #   ", "  #  ", "   # ", "    #", "#### "],
    ["# #  ", "# #  ", "#####", "  # #", "  # #", "  #  ", "  #  "],
]

DREAM = {
    "moon": ["  ###  ", " ##    ", "##     ", "##     ", "##     ", " ##    ", "  ###  "],
    "star": ["   #   ", "   #   ", " ##### ", "#######", " ##### ", "  # #  ", " #   # "],
    "key": ["  ##   ", " #  #  ", "  ##   ", "  #    ", "  #    ", "  ###  ", "  ##   "],
    "door": [" ##### ", " #   # ", " #   # ", " #  ## ", " #   # ", " #   # ", " ##### "],
    "stair": ["     ##", "     ##", "   ####", "   ####", " ######", " ######", "#######"],
    "bed": ["       ", "#      ", "#      ", "##    #", "#######", "#     #", "#     #"],
    "window": ["#######", "#  #  #", "#  #  #", "#######", "#  #  #", "#  #  #", "#######"],
    "eye": ["       ", "       ", "#     #", " #   # ", "  ###  ", " # # # ", "       "],
}


def bitmap(glyph):
    return np.array([[c == "#" for c in row] for row in glyph], dtype=bool)


def line(script, indices, gap=1, scale=1):
    """Compose glyphs into one bitmap row (list of strings)."""
    gl = [script[i % len(script)] for i in indices]
    h = len(gl[0])
    rows = []
    for r in range(h):
        rows.append((" " * gap).join(g[r] for g in gl))
    if scale > 1:
        rows = ["".join(c * scale for c in row) for row in rows for _ in range(scale)]
    return rows


def block(script, rows_of_indices, gap=1, line_gap=2):
    """Several text lines stacked into one bitmap."""
    out = []
    width = 0
    lines = [line(script, idx, gap) for idx in rows_of_indices]
    width = max(len(l[0]) for l in lines)
    for i, l in enumerate(lines):
        pad = width - len(l[0])
        out += [r + " " * pad for r in l]
        if i < len(lines) - 1:
            out += [" " * width] * line_gap
    return out


def rects(glyph):
    """Greedy cover of a glyph's ink with rectangles -> [(x, y_from_top, w, h)] (few cubes)."""
    bm = bitmap(glyph).copy()
    h, w = bm.shape
    out = []
    for y in range(h):
        x = 0
        while x < w:
            if bm[y, x]:
                x1 = x
                while x1 < w and bm[y, x1]:
                    x1 += 1
                y1 = y + 1
                while y1 < h and bm[y1, x:x1].all():
                    y1 += 1
                bm[y:y1, x:x1] = False
                out.append((x, y, x1 - x, y1 - y))
                x = x1
            else:
                x += 1
    return out


def extrude(bone, glyph, origin, pixel, depth, mat, **kw):
    """Build a 3D letter from cubes. origin = top-left-front corner (x east, y up, z).

    The glyph reads correctly when viewed from the north (front); x grows to the viewer's
    right, i.e. toward -X in bb space.
    """
    ox, oy, oz = origin
    cubes = []
    for (x, y, w, h) in rects(glyph):
        cubes.append(bone.cube((ox - (x + w) * pixel, oy - (y + h) * pixel, oz), (w * pixel, h * pixel, depth), mat, **kw))
    return cubes


def seq(seed, n):
    """Deterministic pseudo-random glyph index sequence."""
    out, s = [], seed * 7919 + 13
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        out.append((s >> 8) % 97)
    return out
