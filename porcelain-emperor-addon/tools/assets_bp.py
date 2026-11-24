"""
Behavior pack content: entities, items, blocks, recipes and loot tables.

The Emperor and its fragments carry almost no data-driven AI: their movement,
attacks and timing are driven tick by tick from the gameplay script. The
JSON gives them health, a boss bar, immunities, collision and the synced
properties the client animations read.
"""
from __future__ import annotations

from assets_rp import ACTIONS
from models import PLATES

NS = "porcelain"
ENTITY_FMT = "1.21.0"

BOSS_HEALTH = 900

BLOCKS = {
    # id: (english name, sound, light, seconds_to_destroy, map colour)
    "ivory_marble": ("Ivory Marble", "stone", 0, 2.5, "#F1E8D4"),
    "marble_tile": ("Imperial Marble Tile", "stone", 0, 2.5, "#F6EFE0"),
    "kintsugi_seam": ("Kintsugi Seam", "metal", 12, 3.0, "#F6C64F"),
    "cracked_marble": ("Cracked Imperial Tile", "stone", 4, 1.5, "#E3D6BB"),
    "vermilion_lacquer": ("Vermilion Lacquer", "wood", 0, 2.0, "#C7322A"),
    "imperial_roof": ("Imperial Roof Tile", "stone", 0, 2.0, "#E8B93A"),
    "gilded_floor": ("Gilded Floor", "metal", 9, 2.5, "#E9B848"),
    "seal_tile": ("Imperial Seal Tile", "stone", 6, 2.5, "#C7322A"),
}

ITEMS = {
    # id: (english name, stack, extra components)
    "imperial_seal": ("Cracked Imperial Seal", 1, {"minecraft:glint": True, "minecraft:rarity": "epic"}),
    "kintsugi_heart": ("Kintsugi Heart", 1, {"minecraft:glint": True, "minecraft:rarity": "epic",
                                              "minecraft:allow_off_hand": True}),
    "mandate_shard": ("Shard of the Mandate", 64, {"minecraft:rarity": "rare"}),
}

ENTITIES = {
    "emperor": "The Porcelain Emperor",
    "edict_tablet": "Edict Tablet",
    "shard": "Porcelain Shard",
    "rubble": "Palace Rubble",
    "severed_claw": "Severed Imperial Claw",
    "courtier": "Porcelain Courtier",
}


def immune_triggers(only_players=False):
    t = [{"cause": c, "deals_damage": "no"} for c in
         ("fall", "fire", "fire_tick", "lava", "suffocation", "drowning", "freezing", "magma", "lightning",
          "fly_into_wall", "stalactite", "stalagmite", "contact", "block_explosion")]
    if only_players:
        t.append({"on_damage": {"filters": {"all_of": [
            {"test": "is_family", "subject": "other", "operator": "!=", "value": "player"}]}}, "deals_damage": "no"})
    else:
        t.append({"on_damage": {"filters": {"test": "is_family", "subject": "other", "value": "porcelain"}},
                  "deals_damage": "no"})
    return {"triggers": t}


def despawn_group():
    return ({"porcelain:despawn": {"minecraft:instant_despawn": {}}},
            {"porcelain:despawn": {"add": {"component_groups": ["porcelain:despawn"]}}})


def entity(identifier, components, properties=None, groups=None, events=None):
    g, e = despawn_group()
    g.update(groups or {})
    e.update(events or {})
    desc = {"identifier": identifier, "is_spawnable": False, "is_summonable": True}
    if properties:
        desc["properties"] = properties
    return {"format_version": ENTITY_FMT, "minecraft:entity": {
        "description": desc, "component_groups": g, "components": components, "events": e}}


def kinematic(health, width, height, families, only_players=True, lifetime=None):
    c = {
        "minecraft:type_family": {"family": families},
        "minecraft:health": {"value": health, "max": health},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:damage_sensor": immune_triggers(only_players=only_players),
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "suffocate_time": 0, "total_supply": 15},
        "minecraft:is_hidden_when_invisible": {},
        "minecraft:conditional_bandwidth_optimization": {
            "default_values": {"max_optimized_distance": 64.0, "max_dropped_ticks": 2, "use_motion_prediction_hints": True}},
    }
    if lifetime:
        # safety net: fragments never outlive a fight even if the script is gone
        c["minecraft:timer"] = {"looping": False, "time": lifetime, "randomInterval": False,
                                "time_down_event": {"event": "porcelain:despawn", "target": "self"}}
    return c


def bp_entities():
    E = {}
    E["emperor"] = entity(f"{NS}:emperor", {
        "minecraft:type_family": {"family": ["porcelain", "porcelain_boss", "monster", "mob"]},
        "minecraft:health": {"value": BOSS_HEALTH, "max": BOSS_HEALTH},
        "minecraft:boss": {"hud_range": 96, "name": "The Porcelain Emperor", "should_darken_sky": False},
        "minecraft:collision_box": {"width": 6.0, "height": 4.5},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:freezing_immune": {},
        "minecraft:persistent": {},
        "minecraft:nameable": {},
        "minecraft:movement": {"value": 0.0},
        "minecraft:damage_sensor": immune_triggers(only_players=False),
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "suffocate_time": 0, "total_supply": 15},
        "minecraft:is_hidden_when_invisible": {},
        "minecraft:conditional_bandwidth_optimization": {
            "default_values": {"max_optimized_distance": 128.0, "max_dropped_ticks": 1, "use_motion_prediction_hints": True}},
    }, properties={
        f"{NS}:phase": {"type": "int", "range": [1, 4], "default": 1, "client_sync": True},
        f"{NS}:action": {"type": "int", "range": [0, max(ACTIONS.values())], "default": 0, "client_sync": True},
        f"{NS}:plates": {"type": "int", "range": [0, PLATES], "default": PLATES, "client_sync": True},
        f"{NS}:claw": {"type": "int", "range": [0, 1], "default": 0, "client_sync": True},
        f"{NS}:bend": {"type": "float", "range": [-1.0, 1.0], "default": 0.0, "client_sync": True},
        f"{NS}:tilt": {"type": "float", "range": [-1.0, 1.0], "default": 0.0, "client_sync": True},
    })
    E["edict_tablet"] = entity(f"{NS}:edict_tablet", kinematic(10, 1.0, 1.8, ["porcelain", "porcelain_fragment", "inanimate"],
                                                               lifetime=240),
                               properties={f"{NS}:embedded": {"type": "bool", "default": False, "client_sync": True}})
    E["shard"] = entity(f"{NS}:shard", kinematic(4, 0.7, 0.7, ["porcelain", "porcelain_fragment", "inanimate"], lifetime=240))
    E["rubble"] = entity(f"{NS}:rubble", kinematic(16, 1.1, 1.1, ["porcelain", "porcelain_fragment", "inanimate"], lifetime=240))
    E["severed_claw"] = entity(f"{NS}:severed_claw", kinematic(60, 1.3, 1.8, ["porcelain", "porcelain_claw", "monster"],
                                                               lifetime=240),
                               properties={f"{NS}:strike": {"type": "bool", "default": False, "client_sync": True}})
    E["courtier"] = entity(f"{NS}:courtier", {
        "minecraft:type_family": {"family": ["porcelain", "porcelain_minion", "monster", "mob"]},
        "minecraft:health": {"value": 14, "max": 14},
        "minecraft:attack": {"damage": 3},
        "minecraft:collision_box": {"width": 0.7, "height": 1.7},
        "minecraft:movement": {"value": 0.27},
        "minecraft:movement.basic": {},
        "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_damage_blocks": True},
        "minecraft:jump.static": {},
        "minecraft:physics": {},
        "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
        "minecraft:fire_immune": {},
        "minecraft:damage_sensor": immune_triggers(only_players=False),
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "suffocate_time": 0, "total_supply": 15},
        "minecraft:loot": {"table": "loot_tables/entities/porcelain_courtier.json"},
        "minecraft:experience_reward": {"on_death": "3"},
        "minecraft:behavior.float": {"priority": 0},
        "minecraft:behavior.melee_box_attack": {"priority": 2, "speed_multiplier": 1.25, "track_target": True},
        "minecraft:behavior.nearest_attackable_target": {
            "priority": 1, "must_see": False, "reselect_targets": True, "within_radius": 40,
            "entity_types": [{"filters": {"test": "is_family", "subject": "other", "value": "player"}, "max_dist": 40}]},
        "minecraft:behavior.hurt_by_target": {"priority": 1},
        "minecraft:behavior.random_stroll": {"priority": 6, "speed_multiplier": 0.8},
        "minecraft:behavior.look_at_player": {"priority": 7, "look_distance": 12},
        "minecraft:timer": {"looping": False, "time": 300, "randomInterval": False,
                            "time_down_event": {"event": "porcelain:despawn", "target": "self"}},
        "minecraft:conditional_bandwidth_optimization": {},
    })
    return E


def bp_items():
    out = {}
    for key, (_name, stack, extra) in ITEMS.items():
        comps = {
            "minecraft:icon": f"{NS}_{key}",
            "minecraft:display_name": {"value": f"item.{NS}:{key}.name"},
            "minecraft:max_stack_size": stack,
        }
        comps.update(extra)
        out[key] = {"format_version": "1.21.60", "minecraft:item": {
            "description": {"identifier": f"{NS}:{key}", "menu_category": {"category": "items"}},
            "components": comps}}
    return out


def bp_blocks():
    out = {}
    for key, (_name, _sound, light, secs, color) in BLOCKS.items():
        comps = {
            "minecraft:destructible_by_mining": {"seconds_to_destroy": secs},
            "minecraft:destructible_by_explosion": {"explosion_resistance": 1200},
            "minecraft:material_instances": {"*": {"texture": f"{NS}_{key}", "render_method": "opaque"}},
            "minecraft:map_color": color,
        }
        if light:
            comps["minecraft:light_emission"] = light
        out[key] = {"format_version": "1.21.60", "minecraft:block": {
            "description": {"identifier": f"{NS}:{key}", "menu_category": {"category": "construction"}},
            "components": comps}}
    return out


def bp_recipes():
    return {
        "imperial_seal": {"format_version": "1.20.10", "minecraft:recipe_shaped": {
            "description": {"identifier": f"{NS}:imperial_seal"},
            "tags": ["crafting_table"],
            "pattern": ["GQG", "QDQ", "GQG"],
            "key": {"G": {"item": "minecraft:gold_block"}, "Q": {"item": "minecraft:quartz_block"},
                    "D": {"item": "minecraft:diamond"}},
            "unlock": [{"item": "minecraft:quartz_block"}],
            "result": {"item": f"{NS}:imperial_seal"}}},
        "imperial_seal_from_shards": {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": {"identifier": f"{NS}:imperial_seal_from_shards"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": f"{NS}:mandate_shard"}] * 4 + [{"item": "minecraft:gold_ingot"}],
            "unlock": [{"item": f"{NS}:mandate_shard"}],
            "result": {"item": f"{NS}:imperial_seal"}}},
    }


def bp_loot():
    return {
        "entities/porcelain_courtier": {"pools": [{"rolls": 1, "entries": [
            {"type": "item", "name": f"{NS}:mandate_shard", "weight": 1},
            {"type": "empty", "weight": 3}]}]},
    }


def lang_lines():
    lines = ["pack.name=The Porcelain Emperor",
             "pack.description=Dragon Boss 001: the Porcelain Emperor and its custom dimension, The Fractured Mandate."]
    for key, name in ENTITIES.items():
        lines.append(f"entity.{NS}:{key}.name={name}")
    for key, (name, *_rest) in ITEMS.items():
        lines.append(f"item.{NS}:{key}.name={name}")
    for key, (name, *_rest) in BLOCKS.items():
        lines.append(f"tile.{NS}:{key}.name={name}")
    return lines
