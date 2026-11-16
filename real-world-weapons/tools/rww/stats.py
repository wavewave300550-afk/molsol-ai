"""
Combat balance: every number of the 21 items, derived from the vanilla Bedrock
sword of the same tier (Bedrock Edition 26.60).

Vanilla Bedrock swords have no attack cooldown; the 10-tick (0.5 s) hurt immunity of
mobs caps a sword at 2 damaging hits per second on one target, i.e. ~2 x S damage/s.
Our weapons get a functional attack cooldown (minecraft:cooldown type "attack") and
per-hit damage chosen so single-target damage per second stays within ~±10 % of the
vanilla sword, while each weapon keeps its own profile:

    rapier      S per hit, 0.55 s   -> 0.91 x sword DPS, +reach 3.6, +25 % at long measure
    katana      1.4 S per hit, 0.70 s -> ~1.0 x sword DPS, iai draw-cut +50 %
    zweihander  2 S per hit, 1.00 s  -> 1.0 x sword DPS, reach 4.0, 50 % sweep, knock-back
"""
from __future__ import annotations

from .materials import TIER_ORDER

# vanilla Bedrock sword values per tier: total attack damage, durability, enchantability
VANILLA_SWORD = {
    "wooden": (5, 60, 15),
    "stone": (6, 132, 5),
    "copper": (6, 191, 13),
    "iron": (7, 251, 14),
    "golden": (5, 33, 22),
    "diamond": (8, 1562, 10),
    "netherite": (9, 2032, 15),
}

WEAPONS = {
    "rapier": {"name": "Rapier", "damage_factor": 1.0, "durability_factor": 0.9, "cooldown": 0.55,
               "reach": (0.0, 3.6), "creative_reach": (0.0, 6.0), "hitbox_margin": 0.15},
    "zweihander": {"name": "Zweihänder", "damage_factor": 2.0, "durability_factor": 1.25, "cooldown": 1.0,
                   "reach": (0.0, 4.0), "creative_reach": (0.0, 6.5), "hitbox_margin": 0.35},
    "katana": {"name": "Katana", "damage_factor": 1.4, "durability_factor": 1.0, "cooldown": 0.70,
               "reach": None, "creative_reach": None, "hitbox_margin": None},
}

TIER_ITEM = {   # crafting ingredient (recipe key) and repair item per tier
    "wooden": ({"tag": "minecraft:planks"}, {"tags": "q.all_tags('minecraft:planks')"}),
    "stone": ({"tag": "minecraft:stone_tool_materials"}, {"tags": "q.any_tag('minecraft:stone_tool_materials')"}),
    "copper": ({"item": "minecraft:copper_ingot"}, "minecraft:copper_ingot"),
    "iron": ({"item": "minecraft:iron_ingot"}, "minecraft:iron_ingot"),
    "golden": ({"item": "minecraft:gold_ingot"}, "minecraft:gold_ingot"),
    "diamond": ({"item": "minecraft:diamond"}, "minecraft:diamond"),
    "netherite": (None, "minecraft:netherite_ingot"),
}
NUGGET = {"copper": "minecraft:copper_nugget", "iron": "minecraft:iron_nugget", "golden": "minecraft:gold_nugget"}


def item_id(weapon: str, tier: str) -> str:
    return f"rww:{tier}_{weapon}"


def stats(weapon: str, tier: str) -> dict:
    S, dur, ench = VANILLA_SWORD[tier]
    w = WEAPONS[weapon]
    total = int(round(S * w["damage_factor"]))
    return {
        "total_damage": total,
        "damage": total - 1,                       # minecraft:damage is added to the player's base 1
        "durability": int(round(dur * w["durability_factor"])),
        "enchantability": ench,
        "cooldown": w["cooldown"],
        "dps": total / max(w["cooldown"], 0.5),   # single target, hurt immunity is 0.5 s
        "sword_dps": S / 0.5,
    }


def table():
    rows = []
    for weapon in WEAPONS:
        for tier in TIER_ORDER:
            s = stats(weapon, tier)
            rows.append((weapon, tier, s))
    return rows
