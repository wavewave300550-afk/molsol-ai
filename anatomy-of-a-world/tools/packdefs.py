"""
Pack definitions (behaviour + resource JSON) for THE ANATOMY OF A WORLD.

Single source of truth for identifiers shared with the scripts
(src/bosses/migrating_mountain/ids.ts is checked against this by validate.py).
"""
from __future__ import annotations

import json
import os
from typing import Dict

NS = "anatomy"
ENTITY_FORMAT = "1.26.50"
CLIENT_FORMAT = "1.10.0"

SOUNDS = {
    # id: (file, category, volume, min_distance, max_distance)
    "anatomy.mm.groan": ("mm/groan", "hostile", 1.0, 12, 192),
    "anatomy.mm.rumble": ("mm/rumble", "hostile", 1.0, 12, 160),
    "anatomy.mm.quake": ("mm/quake", "hostile", 1.0, 8, 128),
    "anatomy.mm.crack": ("mm/crack", "hostile", 0.9, 6, 96),
    "anatomy.mm.grind": ("mm/grind", "hostile", 1.0, 8, 128),
    "anatomy.mm.wave": ("mm/wave", "hostile", 0.9, 6, 96),
    "anatomy.mm.resonance": ("mm/resonance", "hostile", 1.0, 10, 128),
    "anatomy.mm.chime": ("mm/chime", "hostile", 0.8, 6, 80),
    "anatomy.mm.heartbeat": ("mm/heartbeat", "hostile", 1.0, 10, 160),
    "anatomy.mm.heart_open": ("mm/heart_open", "hostile", 1.0, 10, 128),
    "anatomy.mm.heart_close": ("mm/heart_close", "hostile", 1.0, 10, 128),
    "anatomy.mm.shatter": ("mm/shatter", "hostile", 1.0, 10, 160),
    "anatomy.mm.unfold": ("mm/unfold", "hostile", 1.0, 16, 256),
    "anatomy.mm.step": ("mm/step", "hostile", 0.45, 8, 96),
    "anatomy.mm.contract": ("mm/contract", "hostile", 1.0, 8, 96),
    "anatomy.mm.whoosh": ("mm/whoosh", "hostile", 0.9, 6, 64),
    "anatomy.mm.node_hurt": ("mm/node_hurt", "hostile", 0.8, 4, 48),
    "anatomy.mm.heart_hurt": ("mm/heart_hurt", "hostile", 0.9, 6, 64),
    "anatomy.mm.warn": ("mm/warn", "hostile", 0.8, 8, 128),
    "anatomy.mm.deflect": ("mm/deflect", "hostile", 0.8, 4, 48),
    "anatomy.mm.vent": ("mm/vent", "hostile", 0.8, 6, 64),
}
MUSIC = {
    "anatomy.music.mm_phase1": ("music/mm_phase1", 0.55),
    "anatomy.music.mm_phase2": ("music/mm_phase2", 0.6),
    "anatomy.music.mm_victory": ("music/mm_victory", 0.6),
}

ENTITY_NAMES = {
    "anatomy:mm_lithic_heart": ("The Migrating Mountain", "เทือกเขาอพยพ"),
    "anatomy:mm_resonance_node": ("Resonance Node", "ไหนดประสานงาน"),
    "anatomy:mm_root_leg": ("Anchorage Root", "รากยึดสมดุล"),
    "anatomy:mm_petal": ("Unfolded Strata", "ชั้นหินที่คลี่ออก"),
    "anatomy:mm_strata_slab": ("Shed Strata", "แผ่นหินที่ผลัดลอก"),
    "anatomy:mm_strata_plate": ("Inverted Strata", "ชั้นหินพลิกกลับ"),
}
ITEM_NAMES = {
    "anatomy:anatomical_atlas": ("Anatomical Atlas", "สมุดกายวิภาคแห่งโลก"),
    "anatomy:restless_lodestone": ("Restless Lodestone", "หินแม่เหล็กไร้สงบ"),
    "anatomy:lithic_heart_shard": ("Lithic Heart Shard", "เศษหัวใจศิลา"),
}


def damage_sensor_env_only() -> dict:
    """Ignore environmental damage; the scripts decide everything else."""
    return {"triggers": [{"cause": c, "deals_damage": "no"} for c in (
        "fall", "suffocation", "fire", "fire_tick", "lava", "drowning", "fly_into_wall", "falling_block", "lightning",
        "block_explosion", "entity_explosion", "magma", "freezing", "contact", "void", "anvil", "piston", "stalactite", "stalagmite")]}


def immovable(width: float, height: float) -> dict:
    return {
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": False, "has_collision": False},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:persistent": {},
        "minecraft:fire_immune": {},
        "minecraft:conditional_bandwidth_optimization": {"default_values": {"max_optimized_distance": 160.0, "max_dropped_ticks": 0, "use_motion_prediction_hints": True}},
    }


def entity(identifier: str, components: dict, properties: dict | None = None, families=("anatomy_part",), summonable=True) -> dict:
    desc = {"identifier": identifier, "is_spawnable": False, "is_summonable": summonable}
    if properties:
        desc["properties"] = properties
    comps = {"minecraft:type_family": {"family": list(families) + ["anatomy", "inanimate"]}}
    comps.update(components)
    return {"format_version": ENTITY_FORMAT, "minecraft:entity": {"description": desc, "components": comps}}


def prop_int(lo, hi, default=0):
    return {"type": "int", "range": [lo, hi], "default": default, "client_sync": True}


def prop_bool(default=False):
    return {"type": "bool", "default": default, "client_sync": True}


def behaviour_entities() -> Dict[str, dict]:
    E = {}
    invuln = {"minecraft:damage_sensor": {"triggers": {"cause": "all", "deals_damage": "no"}}, "minecraft:health": {"value": 100, "max": 100}}
    E["mm_root_leg"] = entity("anatomy:mm_root_leg", {**immovable(1.0, 1.0), **invuln},
                              {"anatomy:leg_index": prop_int(0, 15), "anatomy:pose": prop_int(0, 3)}, ("anatomy_part", "migrating_mountain"))
    E["mm_resonance_node"] = entity("anatomy:mm_resonance_node", {
        **immovable(2.2, 3.4),
        "minecraft:health": {"value": 260, "max": 260},
        "minecraft:damage_sensor": damage_sensor_env_only(),
        "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
    }, {"anatomy:hanging": prop_bool(), "anatomy:charging": prop_bool(), "anatomy:dying": prop_bool()}, ("anatomy_part", "migrating_mountain", "anatomy_target"))
    E["mm_lithic_heart"] = entity("anatomy:mm_lithic_heart", {
        **immovable(5.0, 6.0),
        "minecraft:health": {"value": 1000, "max": 1000},
        "minecraft:boss": {"hud_range": 150, "should_darken_sky": False},
        "minecraft:damage_sensor": damage_sensor_env_only(),
        "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
    }, {"anatomy:open": prop_bool(), "anatomy:phase": prop_int(0, 3), "anatomy:dying": prop_bool(), "anatomy:charging": prop_bool()},
        ("anatomy_part", "migrating_mountain", "anatomy_target", "anatomy_boss"))
    E["mm_strata_slab"] = entity("anatomy:mm_strata_slab", {
        "minecraft:collision_box": {"width": 2.0, "height": 1.6},
        "minecraft:physics": {},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:projectile": {
            "on_hit": {"remove_on_hit": {}},
            "power": 1.0, "gravity": 0.08, "inertia": 1.0, "liquid_inertia": 1.0, "uncertainty_base": 0.0,
            "uncertainty_multiplier": 0.0, "reflect_on_hurt": False,
            "ignored_entities": ["anatomy:mm_strata_slab", "anatomy:mm_root_leg", "anatomy:mm_petal", "anatomy:mm_lithic_heart", "anatomy:mm_resonance_node", "anatomy:mm_strata_plate"],
        },
        "minecraft:conditional_bandwidth_optimization": {"default_values": {"max_optimized_distance": 160.0, "max_dropped_ticks": 0, "use_motion_prediction_hints": True}},
    }, None, ("anatomy_part", "migrating_mountain", "projectile"), True)
    E["mm_petal"] = entity("anatomy:mm_petal", {**immovable(1.0, 1.0), **invuln},
                           {"anatomy:petal_state": prop_int(0, 3), "anatomy:petal_index": prop_int(0, 15)}, ("anatomy_part", "migrating_mountain"))
    E["mm_strata_plate"] = entity("anatomy:mm_strata_plate", {**immovable(1.0, 1.0), **invuln},
                                  {"anatomy:variant": prop_int(0, 1), "anatomy:flip": prop_int(0, 4)}, ("anatomy_part", "migrating_mountain"))
    return E


# ----------------------------------------------------------------------------- resource side
def client_entity(identifier: str, short: str, animations: dict, animate: list, pre: list | None = None, rc: str = "controller.render.anatomy.default",
                  extra_tex: dict | None = None, extra_geo: dict | None = None, particles: dict | None = None, sounds: dict | None = None) -> dict:
    desc = {
        "identifier": identifier,
        "materials": {"default": "entity_emissive_alpha"},
        "textures": {"default": f"textures/entity/anatomy/{short}"},
        "geometry": {"default": f"geometry.anatomy.{short}"},
        "render_controllers": [rc],
        "animations": animations,
        "scripts": {"animate": animate},
        "enable_attachables": False,
        "hide_armor": True,
    }
    if pre:
        desc["scripts"]["pre_animation"] = pre
    if extra_tex:
        desc["textures"].update(extra_tex)
    if extra_geo:
        desc["geometry"].update(extra_geo)
    if particles:
        desc["particle_effects"] = particles
    if sounds:
        desc["sound_effects"] = sounds
    return {"format_version": CLIENT_FORMAT, "minecraft:client_entity": {"description": desc}}


def client_entities() -> Dict[str, dict]:
    C = {}
    A = "animation.anatomy."
    C["mm_root_leg"] = client_entity("anatomy:mm_root_leg", "mm_root_leg", {
        "walk": A + "mm_root_leg.walk", "splay": A + "mm_root_leg.splay", "collapse": A + "mm_root_leg.collapse",
        "stomp": A + "mm_root_leg.stomp", "flinch": A + "mm_root_leg.flinch", "gait": "controller.animation.anatomy.mm_root_leg.gait",
    }, ["gait"], ["v.phase = q.property('anatomy:leg_index') * 0.4286;"], particles={"mist": "anatomy:mm_mist"}, sounds={"step": "anatomy.mm.step"})
    C["mm_resonance_node"] = client_entity("anatomy:mm_resonance_node", "mm_resonance_node", {
        "idle": A + "mm_resonance_node.idle", "charge": A + "mm_resonance_node.charge", "death": A + "mm_resonance_node.death",
        "hang": A + "mm_resonance_node.hang", "state": "controller.animation.anatomy.mm_resonance_node.state",
    }, [{"hang": "q.property('anatomy:hanging')"}, "state"])
    C["mm_lithic_heart"] = client_entity("anatomy:mm_lithic_heart", "mm_lithic_heart", {
        "closed": A + "mm_lithic_heart.closed", "opened": A + "mm_lithic_heart.opened", "beat": A + "mm_lithic_heart.beat",
        "rings": A + "mm_lithic_heart.rings", "charge": A + "mm_lithic_heart.charge", "hurt": A + "mm_lithic_heart.hurt",
        "death": A + "mm_lithic_heart.death", "iris": "controller.animation.anatomy.mm_lithic_heart.iris",
    }, ["rings", {"beat": "!q.property('anatomy:dying')"}, "iris"], rc="controller.render.anatomy.mm_lithic_heart")
    C["mm_strata_slab"] = client_entity("anatomy:mm_strata_slab", "mm_strata_slab", {"tumble": A + "mm_strata_slab.tumble"}, ["tumble"])
    C["mm_petal"] = client_entity("anatomy:mm_petal", "mm_petal", {
        "closed": A + "mm_petal.closed", "unfold": A + "mm_petal.unfold", "open": A + "mm_petal.open", "folded": A + "mm_petal.folded",
        "collapse": A + "mm_petal.collapse", "state": "controller.animation.anatomy.mm_petal.state",
    }, ["state"])
    C["mm_strata_plate"] = client_entity("anatomy:mm_strata_plate", "mm_strata_plate", {
        "flip_wall": A + "mm_strata_plate.flip_wall", "flip_ceiling": A + "mm_strata_plate.flip_ceiling",
        "unflip_wall": A + "mm_strata_plate.unflip_wall", "unflip_ceiling": A + "mm_strata_plate.unflip_ceiling",
        "state": "controller.animation.anatomy.mm_strata_plate.state",
    }, ["state"], rc="controller.render.anatomy.mm_strata_plate",
        extra_tex={"rib": "textures/entity/anatomy/mm_rib_plate"}, extra_geo={"rib": "geometry.anatomy.mm_rib_plate"})
    return C


def animation_controllers() -> dict:
    P = "q.property"
    ctrl = {}
    ctrl["controller.animation.anatomy.mm_root_leg.gait"] = {
        "initial_state": "walk",
        "states": {
            "walk": {"animations": ["walk"], "transitions": [{"splay": f"{P}('anatomy:pose') == 1"}, {"collapse": f"{P}('anatomy:pose') == 2"}], "blend_transition": 1.5},
            "splay": {"animations": ["splay"], "transitions": [{"walk": f"{P}('anatomy:pose') == 0"}, {"collapse": f"{P}('anatomy:pose') == 2"}], "blend_transition": 3.0},
            "collapse": {"animations": ["collapse"], "transitions": [{"walk": f"{P}('anatomy:pose') == 0"}], "blend_transition": 0.6},
        },
    }
    ctrl["controller.animation.anatomy.mm_resonance_node.state"] = {
        "initial_state": "idle",
        "states": {
            "idle": {"animations": ["idle"], "transitions": [{"dying": f"{P}('anatomy:dying')"}, {"charging": f"{P}('anatomy:charging')"}], "blend_transition": 0.3},
            "charging": {"animations": ["idle", "charge"], "transitions": [{"dying": f"{P}('anatomy:dying')"}, {"idle": f"!{P}('anatomy:charging')"}], "blend_transition": 0.3},
            "dying": {"animations": ["death"]},
        },
    }
    ctrl["controller.animation.anatomy.mm_lithic_heart.iris"] = {
        "initial_state": "closed",
        "states": {
            "closed": {"animations": ["closed"], "transitions": [{"dying": f"{P}('anatomy:dying')"}, {"opened": f"{P}('anatomy:open')"}, {"charging": f"{P}('anatomy:charging')"}], "blend_transition": 0.7},
            "charging": {"animations": ["closed", "charge"], "transitions": [{"dying": f"{P}('anatomy:dying')"}, {"opened": f"{P}('anatomy:open')"}, {"closed": f"!{P}('anatomy:charging')"}], "blend_transition": 0.4},
            "opened": {"animations": ["opened"], "transitions": [{"dying": f"{P}('anatomy:dying')"}, {"closed": f"!{P}('anatomy:open')"}], "blend_transition": 0.7},
            "dying": {"animations": ["opened", "death"], "blend_transition": 0.3},
        },
    }
    ctrl["controller.animation.anatomy.mm_petal.state"] = {
        "initial_state": "closed",
        "states": {
            "closed": {"animations": ["closed"], "transitions": [{"unfolding": f"{P}('anatomy:petal_state') == 1"}, {"folded": f"{P}('anatomy:petal_state') == 2"}]},
            "unfolding": {"animations": ["unfold"], "transitions": [{"open": "q.all_animations_finished"}, {"folded": f"{P}('anatomy:petal_state') == 2"}, {"collapse": f"{P}('anatomy:petal_state') == 3"}]},
            "open": {"animations": ["open"], "transitions": [{"folded": f"{P}('anatomy:petal_state') == 2"}, {"collapse": f"{P}('anatomy:petal_state') == 3"}, {"closed": f"{P}('anatomy:petal_state') == 0"}], "blend_transition": 0.4},
            "folded": {"animations": ["folded"], "transitions": [{"open": f"{P}('anatomy:petal_state') == 1"}, {"collapse": f"{P}('anatomy:petal_state') == 3"}, {"closed": f"{P}('anatomy:petal_state') == 0"}], "blend_transition": 1.1},
            "collapse": {"animations": ["collapse"], "blend_transition": 0.5},
        },
    }
    flip = f"{P}('anatomy:flip')"
    ctrl["controller.animation.anatomy.mm_strata_plate.state"] = {
        "initial_state": "rest",
        "states": {
            "rest": {"transitions": [{"wall": f"{flip} == 1"}, {"ceiling": f"{flip} == 2"}, {"unwall": f"{flip} == 3"}, {"unceiling": f"{flip} == 4"}]},
            "wall": {"animations": ["flip_wall"], "transitions": [{"unwall": f"{flip} == 3"}, {"rest": f"{flip} == 0"}]},
            "ceiling": {"animations": ["flip_ceiling"], "transitions": [{"unceiling": f"{flip} == 4"}, {"rest": f"{flip} == 0"}]},
            "unwall": {"animations": ["unflip_wall"], "transitions": [{"rest": f"{flip} == 0"}, {"wall": f"{flip} == 1"}]},
            "unceiling": {"animations": ["unflip_ceiling"], "transitions": [{"rest": f"{flip} == 0"}, {"ceiling": f"{flip} == 2"}]},
        },
    }
    return {"format_version": "1.10.0", "animation_controllers": ctrl}


def render_controllers() -> dict:
    return {
        "format_version": "1.8.0",
        "render_controllers": {
            "controller.render.anatomy.default": {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"]},
            "controller.render.anatomy.mm_lithic_heart": {
                "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
                "overlay_color": {"r": 0.85, "g": 0.6, "b": 1.0, "a": "q.property('anatomy:charging') ? 0.25 + 0.15 * math.sin(q.life_time * 720) : (q.property('anatomy:open') ? 0.08 : 0.0)"},
            },
            "controller.render.anatomy.mm_strata_plate": {
                "arrays": {"geometries": {"Array.geo": ["Geometry.default", "Geometry.rib"]}, "textures": {"Array.tex": ["Texture.default", "Texture.rib"]}},
                "geometry": "Array.geo[q.property('anatomy:variant')]", "materials": [{"*": "Material.default"}],
                "textures": ["Array.tex[q.property('anatomy:variant')]"],
            },
        },
    }


def sound_definitions() -> dict:
    defs = {}
    for sid, (f, cat, vol, mn, mx) in SOUNDS.items():
        defs[sid] = {"category": cat, "min_distance": mn, "max_distance": mx,
                     "sounds": [{"name": f"sounds/anatomy/{f}", "volume": vol, "load_on_low_memory": True}]}
    for sid, (f, vol) in MUSIC.items():
        defs[sid] = {"category": "music", "sounds": [{"name": f"sounds/anatomy/{f}", "stream": True, "volume": vol, "is3D": False}]}
    return {"format_version": "1.20.20", "sound_definitions": defs}


def entity_sounds() -> dict:
    return {"entity_sounds": {"entities": {
        "anatomy:mm_lithic_heart": {"volume": 1.0, "pitch": [0.9, 1.1], "events": {"hurt": "anatomy.mm.heart_hurt"}},
        "anatomy:mm_resonance_node": {"volume": 1.0, "pitch": [0.9, 1.15], "events": {"hurt": "anatomy.mm.node_hurt"}},
    }}}


def fog() -> dict:
    return {
        "format_version": "1.16.100",
        "minecraft:fog_settings": {
            "description": {"identifier": "anatomy:migration_mist"},
            "distance": {
                "air": {"fog_start": 0.42, "fog_end": 1.0, "fog_color": "#D6E4F2", "render_distance_type": "render"},
                "weather": {"fog_start": 0.2, "fog_end": 0.7, "fog_color": "#9AA8B8", "render_distance_type": "render"},
                "water": {"fog_start": 0, "fog_end": 50.0, "fog_color": "#3F76E4", "render_distance_type": "fixed"},
            },
        },
    }


def dimension() -> dict:
    return {
        "format_version": "1.26.50",
        "minecraft:dimension": {
            "description": {"identifier": "anatomy:migration_path"},
            "components": {
                "minecraft:dimension_height": {"min_y": -64, "height_range": 384},
                "minecraft:generation": {"generator_type": "void"},
                "minecraft:default_biome": {"biome": "minecraft:forest"},
                "minecraft:clouds": {"height": 100},
            },
        },
    }


def items() -> Dict[str, dict]:
    def item(key, icon, category, stack, extra_components, glint=False):
        comps = {
            "minecraft:icon": {"textures": {"default": icon}},
            "minecraft:display_name": {"value": f"item.anatomy:{key}.name"},
            "minecraft:max_stack_size": stack,
            "minecraft:glint": glint,
            "minecraft:tags": {"tags": ["anatomy:item"]},
        }
        comps.update(extra_components)
        return {"format_version": "1.21.90", "minecraft:item": {"description": {"identifier": f"anatomy:{key}", "menu_category": {"category": category}}, "components": comps}}
    return {
        "anatomical_atlas": item("anatomical_atlas", "anatomy_atlas", "items", 1, {"anatomy:atlas": {}}),
        "restless_lodestone": item("restless_lodestone", "anatomy_restless_lodestone", "items", 16,
                                   {"anatomy:summoner": {"boss": "migrating_mountain"}}, glint=True),
        "lithic_heart_shard": item("lithic_heart_shard", "anatomy_lithic_heart_shard", "items", 64, {"anatomy:heart_shard": {}}, glint=True),
    }


def recipes() -> Dict[str, dict]:
    return {
        "anatomical_atlas": {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
            "description": {"identifier": "anatomy:anatomical_atlas"}, "tags": ["crafting_table"],
            "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:amethyst_shard"}],
            "result": {"item": "anatomy:anatomical_atlas"}, "unlock": [{"item": "minecraft:book"}]}},
        "restless_lodestone": {"format_version": "1.20.10", "minecraft:recipe_shaped": {
            "description": {"identifier": "anatomy:restless_lodestone"}, "tags": ["crafting_table"],
            "pattern": ["TAT", "ACA", "TMT"],
            "key": {"T": {"item": "minecraft:tuff"}, "A": {"item": "minecraft:amethyst_shard"}, "C": {"item": "minecraft:compass"}, "M": {"item": "minecraft:mossy_cobblestone"}},
            "result": {"item": "anatomy:restless_lodestone"}, "unlock": [{"item": "minecraft:compass"}]}},
    }


def lang(locale: str) -> str:
    th = locale == "th_TH"
    lines = [
        "pack.name=THE ANATOMY OF A WORLD",
        "pack.description=" + ("บอสทดลองขนาดมหึมา ร่างกายของพวกมันคือสนามรบ" if th else "Experimental colossal bosses whose bodies are the battlefield."),
    ]
    for ident, (en, thai) in ENTITY_NAMES.items():
        lines.append(f"entity.{ident}.name={thai if th else en}")
    for ident, (en, thai) in ITEM_NAMES.items():
        lines.append(f"item.{ident}.name={thai if th else en}")
    return "\n".join(lines) + "\n"


def write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if isinstance(data, str):
            fh.write(data)
        else:
            json.dump(data, fh, indent=1, ensure_ascii=False)


def emit(bp: str, rp: str) -> None:
    for short, data in behaviour_entities().items():
        write(os.path.join(bp, "entities", "migrating_mountain", f"{short}.json"), data)
    for short, data in client_entities().items():
        write(os.path.join(rp, "entity", f"{short}.entity.json"), data)
    write(os.path.join(rp, "animation_controllers", "anatomy_mm.animation_controllers.json"), animation_controllers())
    write(os.path.join(rp, "render_controllers", "anatomy.render_controllers.json"), render_controllers())
    write(os.path.join(rp, "sounds", "sound_definitions.json"), sound_definitions())
    write(os.path.join(rp, "sounds.json"), entity_sounds())
    write(os.path.join(rp, "fogs", "migration_mist.json"), fog())
    write(os.path.join(bp, "dimensions", "migration_path.json"), dimension())
    for key, data in items().items():
        write(os.path.join(bp, "items", f"{key}.json"), data)
    for key, data in recipes().items():
        write(os.path.join(bp, "recipes", f"{key}.json"), data)
    # Bedrock only loads its supported locales from packs; Thai names ship as docs/th_TH.reference.lang
    write(os.path.join(rp, "texts", "en_US.lang"), lang("en_US"))
    write(os.path.join(bp, "texts", "en_US.lang"), lang("en_US"))
    write(os.path.join(rp, "texts", "languages.json"), ["en_US"])
    write(os.path.join(bp, "texts", "languages.json"), ["en_US"])
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    write(os.path.join(root, "docs", "th_TH.reference.lang"), lang("th_TH"))
    write(os.path.join(rp, "textures", "item_texture.json"), {
        "resource_pack_name": "anatomy", "texture_name": "atlas.items",
        "texture_data": {
            "anatomy_atlas": {"textures": ["textures/items/anatomy/anatomical_atlas"]},
            "anatomy_restless_lodestone": {"textures": ["textures/items/anatomy/restless_lodestone"]},
            "anatomy_lithic_heart_shard": {"textures": ["textures/items/anatomy/lithic_heart_shard"]},
        }})
