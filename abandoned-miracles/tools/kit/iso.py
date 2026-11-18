"""
iso.py - isometric preview of an arena structure (flat block colours, no game textures).

Mojang's structure renderer needs to download vanilla textures, which is not
possible offline, so arenas are previewed with representative colours instead.
The picture shows layout and proportions; it is not what the blocks look like in game.
"""
from __future__ import annotations

import zlib
from typing import Dict, Tuple

from PIL import Image, ImageDraw

COLORS: Dict[str, Tuple[int, int, int]] = {
    "smooth_quartz": (236, 230, 222), "quartz_bricks": (232, 226, 216), "quartz_pillar": (230, 224, 214),
    "chiseled_quartz_block": (228, 221, 210), "quartz_block": (236, 230, 222), "smooth_quartz_slab": (236, 230, 222),
    "smooth_quartz_stairs": (236, 230, 222), "calcite": (222, 224, 220), "bone_block": (210, 206, 180),
    "polished_blackstone": (54, 48, 58), "polished_blackstone_bricks": (48, 44, 52), "blackstone": (40, 36, 42),
    "gilded_blackstone": (92, 70, 40), "chiseled_polished_blackstone": (52, 48, 56),
    "deepslate_tiles": (56, 56, 60), "polished_deepslate": (72, 72, 76), "deepslate_bricks": (70, 70, 72),
    "cobbled_deepslate": (80, 80, 84), "chiseled_deepslate": (60, 60, 64),
    "pearlescent_froglight": (246, 236, 230), "ochre_froglight": (248, 232, 164), "verdant_froglight": (212, 240, 200),
    "soul_lantern": (90, 190, 200), "lantern": (236, 170, 80), "sea_lantern": (190, 220, 214), "glowstone": (220, 180, 100),
    "white_candle": (240, 236, 220), "candle": (230, 200, 150), "white_wool": (238, 240, 240), "mushroom_stem": (206, 202, 190),
    "web": (228, 232, 238), "smooth_stone": (160, 160, 160), "stone_bricks": (124, 124, 124), "chiseled_stone_bricks": (120, 120, 120),
    "stone": (126, 126, 126), "lodestone": (150, 150, 158), "waxed_oxidized_cut_copper": (82, 162, 132),
    "waxed_oxidized_copper": (84, 164, 134), "waxed_weathered_copper": (108, 152, 110), "waxed_exposed_copper": (160, 126, 104),
    "waxed_exposed_cut_copper": (156, 122, 100), "waxed_copper": (192, 108, 80), "waxed_cut_copper": (190, 106, 78),
    "waxed_oxidized_copper_grate": (80, 156, 128), "waxed_oxidized_chiseled_copper": (84, 160, 132),
    "waxed_oxidized_copper_bulb": (120, 180, 140), "waxed_copper_bulb": (220, 150, 90),
    "birch_planks": (194, 176, 122), "pale_oak_planks": (228, 218, 212), "dark_oak_planks": (68, 44, 22), "spruce_planks": (114, 84, 48),
    "stripped_birch_log": (196, 176, 118), "amethyst_block": (134, 98, 190), "tinted_glass": (44, 38, 50),
    "blue_stained_glass": (52, 76, 178), "purple_stained_glass": (128, 64, 178), "red_stained_glass": (154, 52, 52),
    "light_blue_stained_glass": (104, 154, 216), "white_stained_glass": (240, 240, 240), "yellow_stained_glass": (230, 230, 60),
    "green_stained_glass": (102, 128, 52), "cyan_stained_glass": (76, 128, 154), "magenta_stained_glass": (178, 76, 216),
    "gold_block": (246, 208, 62), "raw_gold_block": (222, 170, 48), "iron_block": (220, 220, 220), "emerald_block": (42, 176, 90),
    "lapis_block": (30, 68, 140), "copper_block": (192, 108, 80), "cartography_table": (104, 88, 68), "bookshelf": (150, 120, 80),
    "white_concrete": (208, 214, 214), "black_concrete": (10, 12, 16), "gray_concrete": (56, 58, 62), "light_gray_concrete": (126, 126, 116),
    "green_concrete": (74, 92, 38), "cyan_concrete": (22, 120, 136), "blue_concrete": (44, 46, 144), "white_terracotta": (210, 178, 162),
    "light_gray_terracotta": (136, 108, 98), "gray_terracotta": (58, 42, 36), "black_terracotta": (38, 22, 16), "green_terracotta": (76, 84, 42),
    "cyan_terracotta": (86, 92, 92), "yellow_terracotta": (186, 134, 36), "brown_terracotta": (78, 52, 36),
    "sculk": (14, 30, 36), "crying_obsidian": (40, 12, 70), "obsidian": (18, 12, 28), "smooth_basalt": (72, 72, 78), "basalt": (80, 80, 86),
    "polished_basalt": (96, 96, 100), "tuff": (108, 110, 102), "polished_tuff": (98, 104, 100), "tuff_bricks": (98, 104, 98),
    "chiseled_tuff_bricks": (100, 104, 98), "dripstone_block": (134, 108, 92), "end_rod": (240, 236, 220), "bell": (252, 210, 70),
    "lightning_rod": (192, 108, 80), "dark_prismarine": (52, 92, 76), "prismarine_bricks": (98, 172, 158), "mud_bricks": (138, 104, 80),
    "sandstone": (216, 204, 156), "cut_sandstone": (218, 206, 160), "smooth_sandstone": (222, 208, 164), "chiseled_sandstone": (216, 204, 156),
    "white_carpet": (238, 240, 240), "red_carpet": (160, 40, 34), "moss_carpet": (90, 110, 44), "pale_moss_carpet": (150, 154, 144),
    "andesite": (136, 136, 136), "polished_andesite": (132, 134, 134), "diorite": (188, 188, 188), "polished_diorite": (192, 192, 194),
    "resin_bricks": (206, 96, 24), "chiseled_resin_bricks": (202, 92, 24), "grass_block": (112, 160, 70), "dirt": (134, 96, 66),
}
SKIP = {"air", "structure_void", "light_block_15"}


def color_of(name: str) -> Tuple[int, int, int]:
    n = name.replace("minecraft:", "")
    if n in COLORS:
        return COLORS[n]
    for suffix in ("_stairs", "_slab", "_wall"):
        if n.endswith(suffix) and n[: -len(suffix)] in COLORS:
            return COLORS[n[: -len(suffix)]]
    h = zlib.crc32(n.encode())
    return (90 + h % 80, 90 + (h >> 8) % 80, 90 + (h >> 16) % 80)


def render(structure, cell: int = 7, bg=(24, 25, 31)) -> Image.Image:
    """Painter's-algorithm isometric view from the south-east, looking north-west."""
    sx, sy, sz = structure.size
    w = (sx + sz) * cell + 2 * cell
    h = (sx + sz) * cell // 2 + sy * cell + 2 * cell
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    ox, oy = sz * cell + cell, sy * cell + cell
    blocks = {}
    for x, y, z, name, _ in structure.blocks():
        n = name.replace("minecraft:", "")
        if n not in SKIP:
            blocks[(x, y, z)] = n

    def shade(c, k):
        return tuple(max(0, min(255, int(v * k))) for v in c)
    for key in sorted(blocks, key=lambda p: (p[0] + p[2], p[1])):
        x, y, z = key
        n = blocks[key]
        c = color_of(n)
        thin = n.endswith("_slab") or n.endswith("carpet") or n == "web"
        hh = cell // 2 if thin else cell
        px = ox + (x - z) * cell
        py = oy + (x + z) * cell // 2 - y * cell
        top = [(px, py - hh), (px + cell, py - hh + cell // 2), (px, py - hh + cell), (px - cell, py - hh + cell // 2)]
        if (x, y + 1, z) not in blocks or thin:
            d.polygon(top, fill=shade(c, 1.0))
        if (x, y, z + 1) not in blocks:
            d.polygon([top[3], top[2], (px, py + cell), (px - cell, py + cell // 2)], fill=shade(c, 0.72))
        if (x + 1, y, z) not in blocks:
            d.polygon([top[2], top[1], (px + cell, py + cell // 2), (px, py + cell)], fill=shade(c, 0.56))
    return img
