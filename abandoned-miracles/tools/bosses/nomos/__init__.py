"""Boss 003 - Nomos, The Unmapped Sovereign: everything it contributes to the packs."""
from __future__ import annotations

import json
import os

from kit import icons
from kit import pack as K
from . import anims, arena, fx, model

KEY = "nomos"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# What tools/previews.py renders for this boss.
PREVIEW = {
    "title": "Nomos, The Unmapped Sovereign",
    "phase2": "There Is No North",
    "base": ["idle", "walk", "turn"],
    "base_p1": ["compass_spin"],
    "base_p2": ["p2_pose", "p2_compass"],
    "pad": 30,
    "actions": [
        (["compass_spin", "meridian_p1"], 1.55, 1, "01 Meridian Incision - scribing"),
        (["compass_spin", "shear_p1"], 1.7, 1, "02 Latitude Shear - calipers open"),
        (["compass_spin", "shear_p1"], 4.6, 1, "02 Latitude Shear - closing"),
        (["compass_spin", "borders_p1"], 0.5, 1, "03 Ink Borders - stamp"),
        (["compass_spin", "gate_p1"], 1.2, 1, "04 Unmapped Gate - folding away"),
        (["compass_spin", "gate_p1"], 2.2, 1, "04 Unmapped Gate - arrival"),
        (["compass_spin", "darts_p1"], 2.0, 1, "05 Compass Darts - locked"),
        (["compass_spin", "folded_p1"], 1.6, 1, "06 Folded Country - one side open"),
        (["compass_spin", "recalc_p1"], 2.2, 1, "07 The Great Recalculation"),
        (["stagger"], 0.6, 1, "stagger"),
        (["folded_p2"], 1.5, 2, "Phase II - Folded Country"),
        (["death"], 9.5, 2, "death - final pose"),
    ],
    "gifs": [
        ("walk", ["compass_spin"], 0.0, 4.0, 1, 1.3),
        ("transition", ["transition"], 0.0, 7.5, 1, 0.0),
        ("unmapped_gate", ["compass_spin", "gate_p1"], 0.0, 3.8, 1, 0.0),
        ("death", ["death"], 0.0, 9.5, 2, 0.0),
    ],
}


def timings() -> dict:
    with open(os.path.join(ROOT, "shared", f"{KEY}.timings.json"), encoding="utf-8") as f:
        return json.load(f)


def assets() -> K.BossAssets:
    T = timings()
    out = K.BossAssets(KEY)
    out.models = {"nomos": model.build()}

    anim_list, ctrls, ce = anims.build_all(T)
    ce.particle_effects = fx.client_particles()
    snd = fx.sounds()
    ce.sound_effects = {k: f"abm.nomos.{k}" for k in snd}
    out.client_entities = [ce]
    out.animations = anim_list
    # models face the yaw the script publishes (abm:yaw), not whatever the engine does with the body
    from kit.anim import add_facing
    for _ce in out.client_entities:
        if _ce.identifier in ('abm:nomos',):
            out.animations.append(add_facing(_ce, "animation." + _ce.identifier.replace(":", ".") + "."))
    out.controllers = ctrls

    out.bp_entities["nomos"] = K.boss_entity(
        "abm:nomos", "abm_nomos", 560, 2.8, 5.0, 4.6, 6.6, "loot_tables/abm/nomos.json",
        {f"abm:q{k}": K.int_prop(0, 7) for k in range(1, 5)})

    out.particles = fx.particles()
    out.textures["textures/particle/abm/nomos"] = fx.sprite_sheet()
    out.sounds = {f"abm.nomos.{k}": v for k, v in snd.items()}

    out.item_icons["abm_seal_nomos"] = icons.seal(
        ["...##...", ".#.##.#.", "..####..", "###..###", "###..###", "..####..", ".#.##.#.", "...##..."],
        "#a98a34", "#d8c69b", "#b89f73", "#ece0bd", "#1f8f5a")
    out.item_icons["abm_sovereign_needle"] = icons.icon([
        "................",
        ".............e..",
        "............eE..",
        "...........eEe..",
        "..........eEe...",
        ".........eEe....",
        "........bEe.....",
        ".......bBb......",
        "......sBb.......",
        ".....sSb........",
        "....sSs.........",
        "...sSs..........",
        "..sSs...........",
        "..ss............",
        "................",
        "................",
    ], {"e": "#1f9a62", "E": "#b6ffd6", "b": "#7c6426", "B": "#d3b659", "s": "#565b66", "S": "#c9cfd8"})
    out.items["seal_nomos"] = K.item("abm:seal_nomos", "abm_seal_nomos", stack=1, rarity="rare")
    out.items["sovereign_needle"] = K.item("abm:sovereign_needle", "abm_sovereign_needle", stack=1, glint=True, rarity="epic",
                                           cooldown=("abm_trophy", 3.0))
    out.recipes["seal_nomos"] = K.shaped_recipe(
        "abm:seal_nomos", ["PCP", "CMC", "PCP"],
        {"P": "minecraft:paper", "C": "minecraft:compass", "M": "minecraft:empty_map"},
        "abm:seal_nomos", ["minecraft:compass"])
    out.loot["nomos"] = K.loot_table([
        K.loot_pool([("abm:sovereign_needle", 1, 1, 1)]),
        K.loot_pool([("minecraft:emerald", 3, 6, 12), ("minecraft:paper", 3, 8, 16),
                     ("minecraft:copper_ingot", 2, 8, 16), ("minecraft:compass", 1, 1, 2)], rolls=3),
        K.loot_pool([("minecraft:diamond", 1, 2, 4)]),
    ])
    out.structures[arena.NAME] = arena.build()
    out.lang = {
        "entity.abm:nomos.name": "Nomos, The Unmapped Sovereign",
        "item.abm:seal_nomos.name": "Seal of the Unmapped Sovereign",
        "item.abm:sovereign_needle.name": "Needle of the Unmapped Sovereign",
        "abm.lore.nomos": "It was built to map every place there is. Where the world disagreed with the map, it began correcting the world.",
        "abm.trophy.nomos": "The needle turns once, slowly, and points at nothing you can see.",
        "abm.summon.ok.nomos": "§7Every line on the floor straightens. §fNomos§7 has begun to measure you.",
        "abm.defeat.nomos": "§7The last needle stops. §fNomos§7 has run out of north.",
        "abm.arena.nomos": "The Observatory of Unwritten Borders",
    }
    return out
