"""Manifests, items, recipes, blocks, language and texture registries."""
from .fxdefs import dump

VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_MODULE = "2.11.0"
UI_MODULE = "2.3.0"

BP_UUID = "1dcdd281-148f-43d0-86bd-a29bfeda5bb1"
BP_DATA_UUID = "65f3fb7f-5aca-468a-a1bc-539f8921244d"
BP_SCRIPT_UUID = "0b10b33a-87fc-4503-b006-9f76517ff7c3"
RP_UUID = "bfec4fe7-3e6a-47d3-b8c3-f667105b9234"
RP_RES_UUID = "f87b2246-6194-4786-9b07-769dc75fb7de"

NAME = "Grimoire: Imperial Magic"
DESC = "Six Grimoires (Pressure, Ice, Blood, Plasma, Darkness, Prism Light) with 15 spells each. No mana - only cooldowns. Crouch to select, hold Use to prepare, release to cast."


def manifests(bp, rp):
    dump(f"{bp}/manifest.json", {
        "format_version": 2,
        "header": {"name": f"{NAME} BP", "description": DESC, "uuid": BP_UUID, "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": BP_DATA_UUID, "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": BP_SCRIPT_UUID, "version": VERSION, "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"uuid": RP_UUID, "version": VERSION},
            {"module_name": "@minecraft/server", "version": SERVER_MODULE},
        ],
        "metadata": {"authors": ["Grimoire: Imperial Magic"], "license": "All rights reserved", "generated_with": {"grimoire_build": ["1.0.0"]}},
    })
    dump(f"{rp}/manifest.json", {
        "format_version": 2,
        "header": {"name": f"{NAME} RP", "description": DESC, "uuid": RP_UUID, "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": RP_RES_UUID, "version": VERSION}],
        "dependencies": [{"uuid": BP_UUID, "version": VERSION}],
        "metadata": {"authors": ["Grimoire: Imperial Magic"]},
    })


SCHOOL_TEXT = {
    "pressure": ("Pressure Grimoire", "gold"),
    "ice": ("Ice Grimoire", "aqua"),
    "blood": ("Blood Grimoire", "red"),
    "plasma": ("Plasma Grimoire", "light_purple"),
    "darkness": ("Darkness Grimoire", "dark_green"),
    "prism_light": ("Prism Light Grimoire", "white"),
}


def items(bp):
    for school, (title, color) in SCHOOL_TEXT.items():
        dump(f"{bp}/items/grimoire_{school}.json", {
            "format_version": "1.26.60",
            "minecraft:item": {
                "description": {"identifier": f"grimoire:{school}", "menu_category": {"category": "equipment", "group": "minecraft:itemGroup.name.enchantedBook"}},
                "components": {
                    "minecraft:icon": f"grimoire_{school}",
                    "minecraft:display_name": {"value": f"item.grimoire:{school}.name"},
                    "minecraft:max_stack_size": 1,
                    # Hold-to-prepare: use_modifiers alone makes the item chargeable (verified on BDS 1.26.63:
                    # itemStartUse/itemReleaseUse fire). Not food, not throwable, never consumed.
                    "minecraft:use_modifiers": {"use_duration": 3600, "movement_modifier": 0.8, "emit_vibrations": False},
                    "minecraft:use_animation": "none",
                    "minecraft:interact_button": f"action.grimoire.cast",
                    "minecraft:hover_text_color": color,
                    "minecraft:hand_equipped": False,
                    "minecraft:allow_off_hand": False,
                    "minecraft:fire_resistant": {"value": True},
                    "minecraft:should_despawn": False,
                    "minecraft:tags": {"tags": ["grimoire:grimoire", f"grimoire:{school}"]},
                    "minecraft:glint": False,
                },
            },
        })


RECIPES = {
    "pressure": (["CBC", "RXR", "CBC"], {"C": "minecraft:copper_ingot", "B": "minecraft:breeze_rod", "R": "minecraft:blaze_powder", "X": "minecraft:book"}),
    "ice": (["DPD", "AXA", "DPD"], {"D": "minecraft:diamond", "P": "minecraft:blue_ice", "A": "minecraft:amethyst_shard", "X": "minecraft:book"}),
    "blood": (["RNR", "GXG", "RNR"], {"R": "minecraft:redstone_block", "N": "minecraft:nether_wart_block", "G": "minecraft:ghast_tear", "X": "minecraft:book"}),
    "plasma": (["AGA", "LXL", "AGA"], {"A": "minecraft:amethyst_block", "G": "minecraft:glowstone_dust", "L": "minecraft:lightning_rod", "X": "minecraft:book"}),
    "darkness": (["SOS", "IXI", "SOS"], {"S": "minecraft:sculk", "O": "minecraft:obsidian", "I": "minecraft:ink_sac", "X": "minecraft:book"}),
    "prism_light": (["GQG", "PXP", "GQG"], {"G": "minecraft:gold_ingot", "Q": "minecraft:quartz", "P": "minecraft:glass_pane", "X": "minecraft:book"}),
}


def recipes(bp):
    for school, (pattern, key) in RECIPES.items():
        dump(f"{bp}/recipes/grimoire_{school}.json", {
            "format_version": "1.26.60",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"grimoire:craft_{school}"},
                "tags": ["crafting_table"],
                "pattern": pattern,
                "key": {k: {"item": v} for k, v in key.items()},
                "result": {"item": f"grimoire:{school}", "count": 1},
                "unlock": [{"item": "minecraft:book"}],
            },
        })


BLOCKS = {
    "pressure_barrier": ("grimoire_pressure_barrier", 7),
    "frost_wall": ("grimoire_frost_wall", 6),
    "blood_thornwall": ("grimoire_blood_thornwall", 6),
    "shadow_step_low": ("grimoire_shadow_step", 2),
    "shadow_step_high": ("grimoire_shadow_step", 2),
}

# D11 Stairway of the Unlit Sky: thin walkable panels. Low panels top out at half a block, high panels at a full
# block, so successive steps rise 0.5 (inside the player's automatic step height).
STEP_PANELS = {"shadow_step_low": 4, "shadow_step_high": 12}


def blocks(bp, rp):
    for name, (tex, light) in BLOCKS.items():
        comps_extra = {}
        geometry = "minecraft:geometry.full_block"
        if name in STEP_PANELS:
            y0 = STEP_PANELS[name]
            geometry = f"geometry.grimoire.{name}"
            # Format 1.26.60 (verified on BDS 1.26.63): collision_box must be an ARRAY of {origin, size} boxes; a single
            # object is rejected and min/max needs an experiment. Selection boxes keep the object form.
            comps_extra = {"minecraft:collision_box": [{"origin": [-8, y0, -8], "size": [16, 4, 16]}],
                           "minecraft:selection_box": {"origin": [-8, y0, -8], "size": [16, 4, 16]}}
            dump(f"{rp}/models/blocks/grimoire/{name}.geo.json", {"format_version": "1.12.0", "minecraft:geometry": [{
                "description": {"identifier": geometry, "texture_width": 16, "texture_height": 16},
                "bones": [{"name": "panel", "pivot": [0, 0, 0], "cubes": [{"origin": [-8, y0, -8], "size": [16, 4, 16], "uv": {
                    f: {"uv": [0, 0], "uv_size": [16, 16 if f in ("up", "down") else 4]} for f in ("north", "south", "east", "west", "up", "down")}}]}],
            }]})
        dump(f"{bp}/blocks/{name}.json", {
            "format_version": "1.26.60",
            "minecraft:block": {
                "description": {"identifier": f"grimoire:{name}", "menu_category": {"category": "none", "is_hidden_in_commands": True}},
                "components": {
                    **comps_extra,
                    "minecraft:geometry": {"identifier": geometry},
                    "minecraft:material_instances": {"*": {"texture": tex, "render_method": "blend", "ambient_occlusion": 0.0, "face_dimming": False}},
                    "minecraft:light_emission": light,
                    "minecraft:light_dampening": 0,
                    "minecraft:destructible_by_mining": False,
                    "minecraft:destructible_by_explosion": False,
                    "minecraft:flammable": False,
                    "minecraft:loot": "loot_tables/grimoire/empty.json",
                    "minecraft:map_color": {"pressure_barrier": "#ff9a3a", "frost_wall": "#9fd8ff", "blood_thornwall": "#a0101e"}.get(name, "#123a26"),
                    "minecraft:tick": {"interval_range": [60, 90], "looping": True},
                    "grimoire:temporary": {},
                },
            },
        })
    dump(f"{bp}/loot_tables/grimoire/empty.json", {"pools": []})
    dump(f"{rp}/blocks.json", {"format_version": "1.21.40", **{f"grimoire:{n}": {"sound": "glass"} for n in BLOCKS}})
    dump(f"{rp}/textures/terrain_texture.json", {
        "resource_pack_name": "grimoire",
        "texture_name": "atlas.terrain",
        "padding": 8,
        "num_mip_levels": 4,
        "texture_data": {tex: {"textures": f"textures/blocks/grimoire/{tex[len('grimoire_'):]}"} for name, (tex, _) in BLOCKS.items()},
    })
    dump(f"{rp}/textures/flipbook_textures.json", [
        {"flipbook_texture": f"textures/blocks/grimoire/{tex[len('grimoire_'):]}", "atlas_tile": tex, "ticks_per_frame": 3, "blend_frames": True}
        for tex in dict.fromkeys(t for t, _ in BLOCKS.values())
    ])


def item_textures(rp):
    dump(f"{rp}/textures/item_texture.json", {
        "resource_pack_name": "grimoire",
        "texture_name": "atlas.items",
        "texture_data": {f"grimoire_{s}": {"textures": f"textures/items/grimoire_{s}"} for s in SCHOOL_TEXT},
    })


def lang(rp, bp, spells):
    lines = ["## Grimoire: Imperial Magic"]
    for s, (title, _) in SCHOOL_TEXT.items():
        lines.append(f"item.grimoire:{s}.name={title}")
    lines.append("action.grimoire.cast=Prepare / Cast")
    for n in BLOCKS:
        lines.append(f"tile.grimoire:{n}.name=Spell Barrier")
    for sp in spells:
        lines.append(f"grimoire.spell.{sp['id']}={sp['name']}")
    txt = "\n".join(lines) + "\n"
    for root in (rp, bp):
        with open(f"{root}/texts/en_US.lang", "w", encoding="utf-8") as f:
            f.write(txt)
        dump(f"{root}/texts/languages.json", ["en_US"])
