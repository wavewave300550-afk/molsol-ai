"""Static pack files: manifests, the three Grimoire items, creative-menu group, language."""
import json
import os

from kit.pack import _write

VERSION = [1, 0, 1]
MIN_ENGINE = [1, 26, 60]
SCRIPT_API = "2.11.0"
UUID = dict(bp="dd6d51d0-2fbc-4e22-9c57-01ae607e0b30", bp_data="db9a21f4-f433-4c55-8e69-9c25396f729a",
            bp_script="b7ee4cd8-c9fe-43e8-968a-2c2af5c02de3", rp="5174510b-07c5-4e7b-96fc-68e09a3a4e38",
            rp_res="579fe00a-1bc3-49d3-b4bd-72a144439cb7")

BOOKS = [
    ("divine_word", "Codex of the First Word", "Divine Word Magic - six sacred spells. Crouch: next spell. Hold Use, then release: cast."),
    ("dream_nightmare", "The Unawakened Codex", "Dream & Nightmare Magic - six surreal spells. Crouch: next spell. Hold Use, then release: cast."),
    ("elemental_dragon", "Codex of the Four Primordial Dragons", "Elemental Dragon Magic - six primordial spells. Crouch: next spell. Hold Use, then release: cast."),
]


def build(pack):
    name = "Grimoire: Rebirth of the Arcane"
    _write(os.path.join(pack.bp, "manifest.json"), {
        "format_version": 2,
        "header": {"name": name, "description": "Three Grimoires, eighteen spells. Behavior pack.", "uuid": UUID["bp"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"uuid": UUID["rp"], "version": VERSION},
            {"module_name": "@minecraft/server", "version": SCRIPT_API},
        ],
    })
    _write(os.path.join(pack.rp, "manifest.json"), {
        "format_version": 2,
        "header": {"name": name + " (Resources)", "description": "Models, animations, particles and sounds for the three Grimoires.",
                   "uuid": UUID["rp"], "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
    })
    bp_lang = {}
    for ident, title, _lore in BOOKS:
        _write(os.path.join(pack.bp, "items", f"{ident}.json"), {
            "format_version": "1.26.50",
            "minecraft:item": {
                "description": {"identifier": f"grimoire:{ident}", "menu_category": {"category": "equipment"}},
                "components": {
                    "minecraft:icon": {"textures": {"default": f"grimoire_{ident}"}},
                    "minecraft:display_name": {"value": f"item.grimoire:{ident}"},
                    "minecraft:max_stack_size": 1,
                    "minecraft:rarity": "epic",
                    "minecraft:can_destroy_in_creative": False,
                    "minecraft:tags": {"tags": ["grimoire:grimoire"]},
                    # Makes the book hold-to-use: the engine raises itemStartUse on press-and-hold and
                    # itemReleaseUse on release.  Nothing is eaten, shot, thrown or consumed.
                    "minecraft:use_modifiers": {"use_duration": 72000, "movement_modifier": 0.55,
                                                "emit_vibrations": False},
                },
            },
        })
        pack.lang[f"item.grimoire:{ident}"] = title
        bp_lang[f"item.grimoire:{ident}"] = title
    pack.lang["pack.name"] = name
    os.makedirs(os.path.join(pack.bp, "texts"), exist_ok=True)
    with open(os.path.join(pack.bp, "texts", "en_US.lang"), "w", encoding="utf-8") as fh:
        fh.write(f"pack.name={name}\npack.description=Three Grimoires, eighteen spells.\n")
        for k, v in bp_lang.items():
            fh.write(f"{k}={v}\n")
    _write(os.path.join(pack.bp, "texts", "languages.json"), ["en_US"])
