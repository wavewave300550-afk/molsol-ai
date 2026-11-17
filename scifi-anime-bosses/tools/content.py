"""
content.py - JSON content of the behavior and resource packs (data only, no IO).

Identifiers here are the single source of truth: build.py also emits
src/generated/ids.ts from them so scripts and packs cannot drift apart.
"""
from __future__ import annotations

from typing import Dict, List

import audio
import vesper_anims as va
import vesper_model as vm
import vfx

NS = "sab"
BOSS = f"{NS}:vesper_0"
ENT = {
    "boss": BOSS, "part": f"{NS}:vesper_part", "cherub": f"{NS}:cherub", "orb": f"{NS}:plasma_orb",
    "censer": f"{NS}:censer", "seraph": f"{NS}:seraph", "plate": f"{NS}:hull_plate",
    "singularity": f"{NS}:singularity", "lance": f"{NS}:lance", "halo": f"{NS}:orison_halo",
}
ITEMS = {"psalter": f"{NS}:astral_psalter", "halo": f"{NS}:orison_halo", "alloy": f"{NS}:vesper_alloy"}
FOGS = {"p1": f"{NS}:fog_vesper_p1", "p2": f"{NS}:fog_vesper_p2"}
FORMAT_ENTITY = "1.26.50"
FORMAT_ITEM = "1.21.90"
FAMILY = ["sab_vesper"]

ENTITY_NAMES = {
    "boss": "VESPER-0", "part": "VESPER-0", "cherub": "Cherub Drone", "orb": "Plasma Orison",
    "censer": "Psalm Censer", "seraph": "Seraph Halo", "plate": "Fallen Reliquary Plate",
    "singularity": "Event Horizon", "lance": "Litany Lance", "halo": "Orison Halo",
}
ITEM_NAMES = {"psalter": "Astral Psalter", "halo": "Orison Halo", "alloy": "Vesper Alloy"}


def prop(kind, default, rng=None, sync=True):
    p = {"type": kind, "default": default, "client_sync": sync}
    if rng is not None:
        p["range"] = rng
    return p


BOSS_PROPS = {
    "sab:phase": prop("int", 0, [0, 3]),
    "sab:act": prop("int", 0, [0, 31]),
    "sab:heading": prop("float", 0.0, [-360.0, 360.0]),
    "sab:pitch": prop("float", 0.0, [-60.0, 60.0]),
    "sab:bank": prop("float", 0.0, [-60.0, 60.0]),
    "sab:look_yaw": prop("float", 0.0, [-90.0, 90.0]),
    "sab:look_pitch": prop("float", 0.0, [-60.0, 60.0]),
    "sab:charge": prop("float", 0.0, [0.0, 1.0]),
    "sab:shield": prop("bool", False),
    "sab:skin": prop("int", 0, [0, 1]),
    "sab:rings": prop("bool", True),
    "sab:plates": prop("bool", True),
    "sab:limbs": prop("bool", False),
    "sab:censers": prop("bool", True),
    "sab:enrage": prop("bool", False),
}

ENV_IMMUNE = ["fall", "suffocation", "drowning", "fire", "fire_tick", "lava", "fly_into_wall", "magma",
              "contact", "freezing", "campfire", "soul_campfire", "stalagmite", "stalactite", "falling_block",
              "piston", "temperature", "anvil", "lightning"]


def damage_sensor(extra: List[dict] = None):
    trig = [{"cause": c, "deals_damage": "no"} for c in ENV_IMMUNE]
    trig.append({"on_damage": {"filters": {"test": "is_family", "subject": "other", "value": "sab_vesper"}},
                 "deals_damage": "no"})
    return {"triggers": (extra or []) + trig}


def base_components(health, width, height, families, kb=1.0, persistent=False):
    c = {
        "minecraft:type_family": {"family": families},
        "minecraft:health": {"value": health, "max": health},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": kb},
        "minecraft:fire_immune": {},
        "minecraft:damage_sensor": damage_sensor(),
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "breathes_solids": True,
                                 "suffocate_time": -1, "total_supply": 15},
        "minecraft:conditional_bandwidth_optimization": {"default_values": {"max_optimized_distance": 128.0,
                                                                            "max_dropped_ticks": 0,
                                                                            "use_motion_prediction_hints": True}},
    }
    if persistent:
        c["minecraft:persistent"] = {}
    return c


def entity(identifier, components, properties=None, groups=None, events=None, spawnable=False):
    desc = {"identifier": identifier, "is_spawnable": spawnable, "is_summonable": True}
    if properties:
        desc["properties"] = properties
    body = {"description": desc, "components": components}
    if groups:
        body["component_groups"] = groups
    if events:
        body["events"] = events
    return {"format_version": FORMAT_ENTITY, "minecraft:entity": body}


def bp_entities() -> Dict[str, dict]:
    out = {}
    # ---- the boss
    c = base_components(1200, 8.0, 7.5, FAMILY + ["sab_boss", "monster", "mob"], persistent=True)
    c.update({
        "minecraft:boss": {"hud_range": 96, "should_darken_sky": True},
        "minecraft:body_rotation_always_follows_head": {},
        "minecraft:can_fly": {},
        "minecraft:nameable": {"allow_name_tag_renaming": False, "always_show": False},
        "minecraft:mob_effect_immunity": {"mob_effects": ["levitation", "slowness", "poison", "wither", "weakness",
                                                          "slow_falling", "nausea", "blindness", "darkness",
                                                          "fatal_poison", "infested", "oozing", "weaving",
                                                          "wind_charged", "mining_fatigue", "hunger"]},
        "minecraft:loot": {"table": "loot_tables/entities/sab_vesper_0.json"},
    })
    groups = {
        "sab:hull_open": {"minecraft:collision_box": {"width": 0.6, "height": 0.6}},
        "sab:hull_p2": {"minecraft:collision_box": {"width": 7.0, "height": 6.0}},
    }
    events = {
        "sab:set_hull_p1": {"remove": {"component_groups": ["sab:hull_open", "sab:hull_p2"]}},
        "sab:set_hull_p2": {"add": {"component_groups": ["sab:hull_p2"]}, "remove": {"component_groups": ["sab:hull_open"]}},
        "sab:set_hull_open": {"add": {"component_groups": ["sab:hull_open"]}, "remove": {"component_groups": ["sab:hull_p2"]}},
    }
    out["vesper_0"] = entity(BOSS, c, BOSS_PROPS, groups, events, spawnable=True)

    # ---- proxy hitboxes (prow / stern / heart): damage is forwarded to the boss by script
    c = base_components(1000, 4.5, 4.0, FAMILY + ["sab_part", "inanimate"])
    groups = {
        "sab:prow": {"minecraft:collision_box": {"width": 4.5, "height": 4.0}},
        "sab:stern": {"minecraft:collision_box": {"width": 3.6, "height": 3.6}},
        "sab:heart": {"minecraft:collision_box": {"width": 3.2, "height": 3.2}},
        "sab:legs": {"minecraft:collision_box": {"width": 6.0, "height": 4.0}},
    }
    events = {f"sab:as_{k}": {"add": {"component_groups": [f"sab:{k}"]}} for k in ("prow", "stern", "heart", "legs")}
    out["vesper_part"] = entity(ENT["part"], c, {"sab:part": prop("int", 0, [0, 3], sync=False)}, groups, events)

    # ---- Cherub drone (P1 autonomous system)
    c = base_components(16, 1.1, 1.3, FAMILY + ["sab_minion", "monster", "mob"], kb=0.4)
    out["cherub"] = entity(ENT["cherub"], c, {"sab:heading": prop("float", 0.0, [-360.0, 360.0]),
                                              "sab:charge": prop("float", 0.0, [0.0, 1.0])})
    # ---- plasma orb (parryable projectile)
    c = base_components(4, 0.9, 0.9, FAMILY + ["sab_projectile"])
    out["plasma_orb"] = entity(ENT["orb"], c, {"sab:reflected": prop("bool", False)})
    # ---- censer (prayer node, killable)
    c = base_components(24, 1.3, 2.4, FAMILY + ["sab_censer", "monster"])
    out["censer"] = entity(ENT["censer"], c, {"sab:dark": prop("bool", False)})
    # ---- Seraph halo (P2 ring weapon)
    c = base_components(40, 2.4, 2.4, FAMILY + ["sab_seraph", "monster", "mob"])
    out["seraph"] = entity(ENT["seraph"], c, {"sab:ring": prop("int", 0, [0, 2]), "sab:mode": prop("int", 0, [0, 3]),
                                              "sab:heading": prop("float", 0.0, [-360.0, 360.0]),
                                              "sab:tilt": prop("float", 0.0, [-90.0, 90.0])})
    # ---- fallen hull plate (P2 line-of-sight cover)
    c = base_components(1000, 3.0, 4.2, FAMILY + ["sab_cover", "inanimate"])
    c["minecraft:physics"] = {"has_gravity": False, "has_collision": False}
    out["hull_plate"] = entity(ENT["plate"], c, {"sab:cracks": prop("int", 0, [0, 3])})
    # ---- Event Horizon singularity (visual anchor)
    c = base_components(1000, 0.4, 0.4, FAMILY + ["sab_effect", "inanimate"])
    out["singularity"] = entity(ENT["singularity"], c, {"sab:stage": prop("int", 0, [0, 2]),
                                                        "sab:radius": prop("float", 6.0, [0.0, 16.0])})
    # ---- Litany Lance beam (visual)
    c = base_components(1000, 0.4, 0.4, FAMILY + ["sab_effect", "inanimate"])
    out["lance"] = entity(ENT["lance"], c, {"sab:heading": prop("float", 0.0, [-360.0, 360.0]),
                                            "sab:pitch": prop("float", 0.0, [-90.0, 90.0]),
                                            "sab:len": prop("float", 0.0, [0.0, 64.0]),
                                            "sab:power": prop("float", 0.0, [0.0, 1.0])})
    # ---- thrown Orison Halo (player weapon projectile, script driven)
    c = base_components(1000, 0.6, 0.4, FAMILY + ["sab_player_halo", "inanimate"])
    out["orison_halo"] = entity(ENT["halo"], c)
    return out


# ----------------------------------------------------------------------------- items / recipes / loot

def bp_items() -> Dict[str, dict]:
    def item(key, comps, category="equipment"):
        return {"format_version": FORMAT_ITEM, "minecraft:item": {
            "description": {"identifier": ITEMS[key], "menu_category": {"category": category}},
            "components": {"minecraft:icon": f"sab_{key_icon[key]}",
                           "minecraft:display_name": {"value": f"item.{ITEMS[key]}.name"}, **comps}}}
    key_icon = {"psalter": "astral_psalter", "halo": "orison_halo", "alloy": "vesper_alloy"}
    return {
        "astral_psalter": item("psalter", {
            "minecraft:max_stack_size": 1,
            "minecraft:glint": True,
            "minecraft:rarity": "epic",
            "minecraft:tags": {"tags": ["sab:summoner"]},
            "sab:psalter": {},
        }, "items"),
        "orison_halo": item("halo", {
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:damage": 9,
            "minecraft:durability": {"max_durability": 1200},
            "minecraft:repairable": {"repair_items": [{"items": [ITEMS["alloy"]], "repair_amount": "query.max_durability * 0.25"}]},
            "minecraft:enchantable": {"slot": "sword", "value": 18},
            "minecraft:rarity": "epic",
            "minecraft:cooldown": {"category": "sab:orison", "duration": 2.5},
            "minecraft:tags": {"tags": ["minecraft:is_sword", "sab:orison"]},
            "sab:orison": {},
        }),
        "vesper_alloy": item("alloy", {"minecraft:max_stack_size": 64, "minecraft:rarity": "rare"}, "items"),
    }


def bp_recipes() -> Dict[str, dict]:
    return {
        "astral_psalter": {"format_version": "1.20.10", "minecraft:recipe_shaped": {
            "description": {"identifier": "sab:astral_psalter"},
            "tags": ["crafting_table"],
            "pattern": ["ACA", "CEC", "ACA"],
            "key": {"A": {"item": "minecraft:amethyst_shard"}, "C": {"item": "minecraft:copper_ingot"},
                    "E": {"item": "minecraft:end_crystal"}},
            "unlock": [{"item": "minecraft:end_crystal"}],
            "result": {"item": ITEMS["psalter"]}}},
        "astral_psalter_from_alloy": {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": {"identifier": "sab:astral_psalter_from_alloy"},
            "tags": ["crafting_table"],
            "ingredients": [{"item": ITEMS["alloy"], "count": 3}, {"item": "minecraft:ender_eye"},
                            {"item": "minecraft:amethyst_shard"}],
            "unlock": [{"item": ITEMS["alloy"]}],
            "result": {"item": ITEMS["psalter"]}}},
    }


def bp_loot() -> Dict[str, dict]:
    # fallback only: the scripted death sequence spawns the real rewards per participant
    return {"entities/sab_vesper_0": {"pools": [{"rolls": 1, "entries": [{"type": "item", "name": ITEMS["alloy"],
                                                                           "weight": 1, "functions": [{"function": "set_count", "count": {"min": 3, "max": 5}}]}]}]}}


# ----------------------------------------------------------------------------- resource pack: client entities

FX_ANIMS = {
    "fx_engines": ("animation.sab.vesper.fx_engines", 1.0, [(0.0, "engine_trail", "exhaust_r"), (0.0, "engine_trail", "exhaust_l")]),
    "fx_engines_dark": ("animation.sab.vesper.fx_engines_dark", 1.0, [(0.0, "engine_trail_dark", "exhaust_r"), (0.0, "engine_trail_dark", "exhaust_l")]),
    "fx_censers": ("animation.sab.vesper.fx_censers", 2.0, [(0.0, "censer_smoke", "censer_1"), (0.7, "censer_smoke", "censer_2"), (1.4, "censer_smoke", "censer_3")]),
    "fx_ichor": ("animation.sab.vesper.fx_ichor", 1.5, [(0.0, "ember_drip", "jaw"), (0.5, "ember_drip", "core"), (1.0, "ember_drip", "belly")]),
}


def fx_anims():
    from anim import Anim
    out = []
    for key, (name, length, effects) in FX_ANIMS.items():
        a = Anim(name, length, True)
        for t, eff, loc in effects:
            a.fx(t, eff, loc)
        out.append(a)
    hum = Anim("animation.sab.vesper.fx_hum", 4.0, True)
    hum.sfx(0.0, "hum")
    out.append(hum)
    return out


def boss_client_entity() -> dict:
    anims = {va.short_name(a.name): a.name for a in va.all_anims()}
    anims.update({k: v[0] for k, v in FX_ANIMS.items()})
    anims["fx_hum"] = "animation.sab.vesper.fx_hum"
    anims["phase_controller"] = "controller.animation.sab.vesper.phase"
    anims["act_controller"] = "controller.animation.sab.vesper.act"
    animate = list(va.ANIMATE) + [
        {"fx_engines": "query.property('sab:skin') == 0"},
        {"fx_engines_dark": "query.property('sab:skin') == 1"},
        {"fx_censers": "query.property('sab:censers')"},
        {"fx_ichor": "query.property('sab:phase') == 2"},
        "fx_hum",
    ]
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": BOSS,
        "materials": {"default": "entity_emissive", "glow": "entity_beam_additive", "shield": "charged_creeper"},
        "textures": {"p1": "textures/entity/sab/vesper_p1", "p2": "textures/entity/sab/vesper_p2",
                     "glow_p1": "textures/entity/sab/vesper_glow_p1", "glow_p2": "textures/entity/sab/vesper_glow_p2",
                     "shield_p1": "textures/entity/sab/vesper_shield_p1", "shield_p2": "textures/entity/sab/vesper_shield_p2"},
        "geometry": {"default": "geometry.sab.vesper_0", "glow": "geometry.sab.vesper_0.glow",
                     "shield": "geometry.sab.vesper_0.shield"},
        "scripts": {"initialize": va.INITIALIZE, "pre_animation": va.PRE_ANIMATION, "animate": animate,
                    "should_update_bones_and_effects_offscreen": True, "should_update_effects_offscreen": True},
        "animations": anims,
        "particle_effects": {k: v for k, v in vfx.short_map().items()},
        "sound_effects": {"roar": "sab.vesper.roar", "hum": "sab.vesper.hum"},
        "render_controllers": ["controller.render.sab.vesper_0", "controller.render.sab.vesper_0.glow",
                               {"controller.render.sab.vesper_0.shield": "query.property('sab:shield')"}],
        "spawn_egg": {"base_color": "#e9ecef", "overlay_color": "#4fe8ff"},
    }}}


AUX_CLIENT = {
    # key: (entity key, geometry, textures, render controllers, has glow)
    "cherub": ("cherub", "geometry.sab.cherub", {"default": "vesper_p1", "glow": "vesper_glow_p1"}, ["controller.render.sab.main", "controller.render.sab.glow"]),
    "plasma_orb": ("orb", "geometry.sab.plasma_orb", {"dark": "vesper_p2", "light": "vesper_p1", "glow": "vesper_glow_p2", "glow_light": "vesper_glow_p1"},
                   ["controller.render.sab.orb", "controller.render.sab.orb_glow"]),
    "censer": ("censer", "geometry.sab.censer", {"light": "vesper_p1", "dark": "vesper_p2", "glow": "vesper_glow_p1", "glow_light": "vesper_glow_p1"},
               ["controller.render.sab.censer", "controller.render.sab.censer_glow"]),
    "seraph": ("seraph", "geometry.sab.seraph", {"default": "vesper_p2", "glow": "vesper_glow_p2"}, ["controller.render.sab.seraph", "controller.render.sab.seraph_glow"]),
    "hull_plate": ("plate", "geometry.sab.hull_plate", {"default": "vesper_p2", "glow": "vesper_glow_p2"}, ["controller.render.sab.main", "controller.render.sab.glow"]),
    "singularity": ("singularity", "geometry.sab.singularity", {"default": "vesper_p2", "glow": "vesper_glow_p2"}, ["controller.render.sab.main", "controller.render.sab.glow"]),
    "lance": ("lance", "geometry.sab.lance", {"default": "vesper_p1", "glow": "vesper_glow_p1"}, ["controller.render.sab.main", "controller.render.sab.glow"]),
    "orison_halo": ("halo", "geometry.sab.orison_halo", {"default": "vesper_p1", "glow": "vesper_glow_p1"}, ["controller.render.sab.main", "controller.render.sab.glow"]),
}


def aux_client_entity(key, anims, amap, animate, pre, init) -> dict:
    ekey, geo_id, texs, rcs = AUX_CLIENT[key]
    scripts = {"animate": animate}
    if pre:
        scripts["pre_animation"] = pre
    if init:
        scripts["initialize"] = init
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": ENT[ekey],
        "materials": {"default": "entity_emissive", "glow": "entity_beam_additive"},
        "textures": {k: f"textures/entity/sab/{v}" for k, v in texs.items()},
        "geometry": {"default": geo_id, "glow": f"{geo_id}.glow"},
        "scripts": scripts,
        "animations": amap,
        "particle_effects": {k: v for k, v in vfx.short_map().items()},
        "render_controllers": rcs,
    }}}


def part_client_entity() -> dict:
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": ENT["part"],
        "materials": {"default": "entity_alphatest"},
        "textures": {"default": "textures/entity/sab/empty"},
        "geometry": {"default": "geometry.sab.empty"},
        "render_controllers": ["controller.render.sab.empty"],
    }}}


def _vis(rules):
    return [{"*": True}] + [{b: cond} for b, cond in rules]


def boss_visibility(glow=False):
    rules = [("shield", "false")]
    rules += [(b, "query.property('sab:limbs')") for b in vm.LIMB_BONES]
    rules += [(b, "query.property('sab:plates')") for b in vm.PLATE_BONES]
    rules += [(b, "query.property('sab:rings')") for b in vm.RING_BONES]
    rules += [(b, "query.property('sab:censers')") for b in vm.CENSER_BONES]
    return _vis(rules)


NO_HURT = {"r": 0.0, "g": 0.0, "b": 0.0, "a": 0.0}


def render_controllers() -> dict:
    rc = {
        "controller.render.sab.vesper_0": {
            "arrays": {"textures": {"Array.skins": ["Texture.p1", "Texture.p2"]}},
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Array.skins[query.property('sab:skin')]"],
            "part_visibility": boss_visibility(),
            "is_hurt_color": {"r": "query.property('sab:skin') == 1 ? 0.78 : 1.0",
                              "g": "query.property('sab:skin') == 1 ? 0.3 : 0.86",
                              "b": "query.property('sab:skin') == 1 ? 1.0 : 0.55", "a": 0.45},
            "on_fire_color": NO_HURT,
        },
        "controller.render.sab.vesper_0.glow": {
            "arrays": {"textures": {"Array.glows": ["Texture.glow_p1", "Texture.glow_p2"]}},
            "geometry": "Geometry.glow",
            "materials": [{"*": "Material.glow"}],
            "textures": ["Array.glows[query.property('sab:skin')]"],
            "part_visibility": boss_visibility(True),
            "ignore_lighting": True,
            "is_hurt_color": NO_HURT,
            "on_fire_color": NO_HURT,
        },
        "controller.render.sab.vesper_0.shield": {
            "arrays": {"textures": {"Array.shields": ["Texture.shield_p1", "Texture.shield_p2"]}},
            "geometry": "Geometry.shield",
            "materials": [{"*": "Material.shield"}],
            "textures": ["Array.shields[query.property('sab:skin')]"],
            "uv_anim": {"offset": ["query.life_time * 0.05", "query.life_time * 0.08"], "scale": [1.0, 1.0]},
            "ignore_lighting": True,
            "is_hurt_color": NO_HURT,
            "on_fire_color": NO_HURT,
        },
        "controller.render.sab.main": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                                       "textures": ["Texture.default"]},
        "controller.render.sab.glow": {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}],
                                       "textures": ["Texture.glow"], "ignore_lighting": True, "is_hurt_color": NO_HURT},
        "controller.render.sab.orb": {"arrays": {"textures": {"Array.t": ["Texture.dark", "Texture.light"]}},
                                      "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                                      "textures": ["Array.t[query.property('sab:reflected')]"]},
        "controller.render.sab.orb_glow": {"arrays": {"textures": {"Array.t": ["Texture.glow", "Texture.glow_light"]}},
                                           "geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}],
                                           "textures": ["Array.t[query.property('sab:reflected')]"], "ignore_lighting": True,
                                           "is_hurt_color": NO_HURT},
        "controller.render.sab.censer": {"arrays": {"textures": {"Array.t": ["Texture.light", "Texture.dark"]}},
                                         "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                                         "textures": ["Array.t[query.property('sab:dark')]"]},
        "controller.render.sab.censer_glow": {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}],
                                              "textures": ["Texture.glow"], "ignore_lighting": True, "is_hurt_color": NO_HURT},
        "controller.render.sab.seraph": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                                         "textures": ["Texture.default"],
                                         "part_visibility": _vis([("rim_a", "query.property('sab:ring') == 0"),
                                                                  ("rim_b", "query.property('sab:ring') == 1"),
                                                                  ("rim_c", "query.property('sab:ring') == 2")])},
        "controller.render.sab.seraph_glow": {"geometry": "Geometry.glow", "materials": [{"*": "Material.glow"}],
                                              "textures": ["Texture.glow"], "ignore_lighting": True, "is_hurt_color": NO_HURT,
                                              "part_visibility": _vis([("rim_a", "query.property('sab:ring') == 0 && query.property('sab:mode') != 3"),
                                                                       ("rim_b", "query.property('sab:ring') == 1 && query.property('sab:mode') != 3"),
                                                                       ("rim_c", "query.property('sab:ring') == 2 && query.property('sab:mode') != 3")])},
        "controller.render.sab.empty": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
                                        "textures": ["Texture.default"]},
    }
    return {"format_version": "1.8.0", "render_controllers": rc}


# ----------------------------------------------------------------------------- sounds, fogs, lang

SOUND_SPEC = {
    # name: (category, max_distance, volume)
    "arrive": ("hostile", 160, 1.0), "roar": ("hostile", 128, 1.0), "hum": ("hostile", 48, 0.55), "choir": ("hostile", 96, 0.9),
    "lance_charge": ("hostile", 96, 1.0), "lance_fire": ("hostile", 96, 1.0), "bell_low": ("hostile", 112, 1.0),
    "bell_high": ("hostile", 112, 0.9), "horizon": ("hostile", 64, 1.0), "implode": ("hostile", 64, 1.0),
    "prayer": ("hostile", 112, 0.85), "prayer_broken": ("hostile", 112, 1.0), "benediction": ("hostile", 128, 1.0),
    "transform": ("hostile", 128, 1.0), "nova_charge": ("hostile", 112, 1.0), "nova": ("hostile", 128, 1.0),
    "death": ("hostile", 160, 1.0), "drone_launch": ("hostile", 48, 0.8), "drone_charge": ("hostile", 32, 0.7),
    "plasma_fire": ("hostile", 32, 0.8), "parry": ("player", 32, 1.0), "vent": ("hostile", 48, 0.9),
    "vent_burst": ("hostile", 48, 1.0), "lunge": ("hostile", 64, 1.0), "talon": ("hostile", 48, 1.0),
    "seraph_whine": ("hostile", 40, 0.9), "seraph_slice": ("hostile", 32, 0.9), "plate_impact": ("hostile", 64, 1.0),
    "hurt_hull": ("hostile", 32, 0.8), "hurt_flesh": ("hostile", 32, 0.9), "shield": ("hostile", 24, 0.8),
    "halo_throw": ("player", 24, 0.8), "halo_catch": ("player", 16, 0.7), "censer": ("hostile", 32, 0.8),
    "censer_break": ("hostile", 40, 1.0), "psalter": ("player", 48, 1.0),
}


def sound_definitions() -> dict:
    sd = {}
    for name, (cat, dist, vol) in SOUND_SPEC.items():
        sd[f"sab.vesper.{name}"] = {"category": cat, "min_distance": 4.0, "max_distance": float(dist),
                                    "sounds": [{"name": f"sounds/sab/vesper/{name}", "volume": vol, "load_on_low_memory": True}]}
    for name in audio.MUSIC:
        sd[f"sab.music.{name}"] = {"category": "music",
                                   "sounds": [{"name": f"sounds/music/sab/{name}", "stream": True, "volume": 0.45}]}
    return {"format_version": "1.20.20", "sound_definitions": sd}


def fog(identifier, color, start, end, water_color="#2a1840"):
    return {"format_version": "1.21.90", "minecraft:fog_settings": {
        "description": {"identifier": identifier},
        "distance": {
            "air": {"fog_start": start, "fog_end": end, "fog_color": color, "render_distance_type": "render"},
            "weather": {"fog_start": start * 0.8, "fog_end": end * 0.9, "fog_color": color, "render_distance_type": "render"},
            "water": {"fog_start": 0.0, "fog_end": 30.0, "fog_color": water_color, "render_distance_type": "fixed"},
        }}}


def fogs() -> Dict[str, dict]:
    return {"sab_fog_vesper_p1": fog(FOGS["p1"], "#1d1f3a", 0.45, 1.0),
            "sab_fog_vesper_p2": fog(FOGS["p2"], "#2a0f3a", 0.28, 0.9)}


def lang_rp() -> str:
    lines = ["pack.name=SCI-FI ANIME BOSSES - VESPER-0 (Resources)",
             "pack.description=Boss 001: VESPER-0, The Ship That Learned to Pray. Models, animations, effects and sound."]
    for k, ident in ENT.items():
        lines.append(f"entity.{ident}.name={ENTITY_NAMES[k]}")
    lines.append(f"item.spawn_egg.entity.{BOSS}.name=Spawn VESPER-0")
    for k, ident in ITEMS.items():
        lines.append(f"item.{ident}.name={ITEM_NAMES[k]}")
    return "\n".join(lines) + "\n"


def lang_bp() -> str:
    return ("pack.name=SCI-FI ANIME BOSSES - VESPER-0\n"
            "pack.description=Boss 001: VESPER-0, The Ship That Learned to Pray. Summon it with the Astral Psalter.\n")
