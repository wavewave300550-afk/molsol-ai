"""
pack.py - shared pack plumbing: JSON writing, manifests, entity/item definitions.

Version targets are defined once here and used by the manifests, the validator
and the documentation.
"""
from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ADDON_NAME = "The Abandoned Miracles"
ADDON_TAGLINE = "Four perfect miracles. Four catastrophic successes."
VERSION = [1, 0, 0]
# The LOWEST versions the add-on really needs (not the newest available): a pack that asks for a newer
# script module than the player's game provides does not load at all. The script is type-checked against
# exactly these typings (see package.json), so nothing newer can slip in.
MIN_ENGINE = [1, 26, 10]              # first release whose stable API has world.beforeEvents.entityHurt
SERVER_VERSION = "2.6.0"              # @minecraft/server stable in 1.26.10 (newer games serve it as 2.x)
SERVER_UI_VERSION = "2.0.0"           # @minecraft/server-ui stable in 1.26.10
ENTITY_FORMAT = "1.26.0"
ITEM_FORMAT = "1.21.130"
NAMESPACE = "abm"

UUID = {
    "bp_header": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de001",
    "bp_data": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de002",
    "bp_script": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de003",
    "rp_header": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de011",
    "rp_res": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de012",
    "tw_header": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de021",
    "tw_data": "a8b1c0de-7e11-4f6a-9a01-ab4d0c0de022",
}


def write_json(path: str, obj, compact_lists: bool = True, minify: bool = False) -> None:
    """minify=True writes one top-level entry per line with no other whitespace (large generated files)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if minify:
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(obj, indent=1, ensure_ascii=False)
        if compact_lists:
            text = _compact(text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def _compact(text: str) -> str:
    """Collapse short numeric arrays onto one line (keeps geometry/animation files readable and small)."""
    import re
    pat = re.compile(r"\[\s*((?:-?[\d.eE+]+|\"[^\"\n]{0,80}\")(?:,\s*(?:-?[\d.eE+]+|\"[^\"\n]{0,80}\")){0,7})\s*\]")
    return pat.sub(lambda m: "[" + re.sub(r"\s*\n\s*", " ", m.group(1)) + "]", text)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --------------------------------------------------------------------------- manifests

def bp_manifest() -> dict:
    return {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"uuid": UUID["rp_header"], "version": VERSION},
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"module_name": "@minecraft/server-ui", "version": SERVER_UI_VERSION},
        ],
        "metadata": {"authors": ["The Abandoned Miracles project"], "license": "All rights reserved"},
    }


def rp_manifest() -> dict:
    return {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": {"authors": ["The Abandoned Miracles project"], "license": "All rights reserved"},
    }


# --------------------------------------------------------------------------- entities

STANDARD_PROPS = {
    "abm:anim": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
    "abm:variant": {"type": "int", "range": [0, 7], "default": 0, "client_sync": True},
    "abm:phase": {"type": "int", "range": [1, 2], "default": 1, "client_sync": True},
    "abm:move": {"type": "int", "range": [0, 3], "default": 0, "client_sync": True},
}

NO_DAMAGE_CAUSES = ["fall", "suffocation", "drowning", "contact", "fire", "fire_tick", "lava", "magma",
                    "freezing", "lightning", "stalactite", "stalagmite", "fly_into_wall", "falling_block",
                    "anvil", "campfire", "soul_campfire", "temperature", "wither"]


def int_prop(lo: int, hi: int, default: int = 0) -> dict:
    return {"type": "int", "range": [lo, hi], "default": default, "client_sync": True}


def boss_entity(identifier: str, family: str, health: float, width: float, height: float,
                hit_width: float, hit_height: float, loot: str, extra_props: Optional[dict] = None) -> dict:
    """Behaviour definition shared by the four bosses.

    Bosses carry no AI goals: the script steers them. Health is native (so the engine's boss bar is real);
    the phase gate and the death sequence are enforced by the script before damage is applied.
    """
    props = dict(STANDARD_PROPS)
    # a boss is born in its INTRO pose (animation state 11), so it never flashes its bind pose on spawn
    props["abm:anim"] = {"type": "int", "range": [0, 15], "default": 11, "client_sync": True}
    props.update(extra_props or {})
    return {
        "format_version": ENTITY_FORMAT,
        "minecraft:entity": {
            "description": {"identifier": identifier, "is_spawnable": False, "is_summonable": True,
                            "properties": props},
            "component_groups": {
                "abm:bar": {"minecraft:boss": {"hud_range": 48, "should_darken_sky": False}},
                "abm:remnant": {
                    "minecraft:timer": {"looping": False, "time": 30, "time_down_event": {"event": "abm:despawn"}},
                    "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                },
                "abm:gone": {"minecraft:instant_despawn": {}},
            },
            "components": {
                # no "monster" family: the game removes monsters on Peaceful, and golems hunt them
                "minecraft:type_family": {"family": ["abm_boss", family, "mob"]},
                "minecraft:health": {"value": health, "max": health},
                "minecraft:collision_box": {"width": width, "height": height},
                "minecraft:custom_hit_test": {"hitboxes": [{"width": hit_width, "height": hit_height,
                                                            "pivot": [0, hit_height / 2, 0]}]},
                "minecraft:physics": {},
                "minecraft:movement": {"value": 0.2},
                "minecraft:movement.basic": {},
                "minecraft:jump.static": {},
                "minecraft:variable_max_auto_step": {"base_value": 1.0625, "controlled_value": 1.0625,
                                                     "jump_prevented_value": 1.0625},
                "minecraft:body_rotation_always_follows_head": {},
                "minecraft:knockback_resistance": {"value": 1.0},
                "minecraft:persistent": {},
                "minecraft:fire_immune": {},
                "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
                "minecraft:nameable": {"always_show": False, "allow_name_tag_renaming": False},
                "minecraft:damage_sensor": {"triggers": [{"cause": c, "deals_damage": "no"} for c in NO_DAMAGE_CAUSES]},
                "minecraft:loot": {"table": loot},
            },
            "events": {
                "minecraft:entity_spawned": {"add": {"component_groups": ["abm:bar"]}},
                "abm:hide_bar": {"remove": {"component_groups": ["abm:bar"]}},
                "abm:become_remnant": {"add": {"component_groups": ["abm:remnant"]}},
                "abm:despawn": {"add": {"component_groups": ["abm:gone"]}},
            },
        },
    }


def helper_entity(identifier: str, family: str, health: float, width: float, height: float,
                  max_life_seconds: float, *, damageable: bool = True, gravity: bool = True,
                  extra_props: Optional[dict] = None, knockback_resistance: float = 1.0) -> dict:
    """Behaviour definition for helper entities (minions, anchors, bells, ...).

    A native timer removes the entity after `max_life_seconds` even if scripts are not running,
    so helpers can never be left behind in a world.
    """
    props = {"abm:anim": int_prop(0, 15), "abm:variant": int_prop(0, 7)}
    props.update(extra_props or {})
    comps = {
        "minecraft:type_family": {"family": ["abm_helper", family, "inanimate" if not damageable else "mob"]},
        "minecraft:health": {"value": health, "max": health},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:physics": {"has_gravity": gravity, "has_collision": gravity},
        "minecraft:knockback_resistance": {"value": knockback_resistance},
        "minecraft:fire_immune": {},
        "minecraft:persistent": {},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
        "minecraft:timer": {"looping": False, "time": max_life_seconds, "time_down_event": {"event": "abm:despawn"}},
        "minecraft:damage_sensor": {"triggers": (
            [{"cause": c, "deals_damage": "no"} for c in NO_DAMAGE_CAUSES] if damageable
            else [{"cause": "all", "deals_damage": "no"}])},
    }
    return {
        "format_version": ENTITY_FORMAT,
        "minecraft:entity": {
            "description": {"identifier": identifier, "is_spawnable": False, "is_summonable": True,
                            "properties": props},
            "component_groups": {"abm:gone": {"minecraft:instant_despawn": {}}},
            "components": comps,
            "events": {"abm:despawn": {"add": {"component_groups": ["abm:gone"]}}},
        },
    }


# --------------------------------------------------------------------------- items

def item(identifier: str, icon: str, *, category: str = "items", group: Optional[str] = None,
         stack: int = 1, glint: bool = False, rarity: Optional[str] = None, tags: Sequence[str] = (),
         cooldown: Optional[Tuple[str, float]] = None, hand_equipped: bool = False) -> dict:
    comps: dict = {
        "minecraft:icon": icon,
        "minecraft:max_stack_size": stack,
        "minecraft:display_name": {"value": f"item.{identifier}.name"},
    }
    if glint:
        comps["minecraft:glint"] = True
    if rarity:
        comps["minecraft:rarity"] = rarity
    if tags:
        comps["minecraft:tags"] = {"tags": list(tags)}
    if cooldown:
        comps["minecraft:cooldown"] = {"category": cooldown[0], "duration": cooldown[1]}
    if hand_equipped:
        comps["minecraft:hand_equipped"] = True
    menu: dict = {"category": category}
    if group:
        menu["group"] = group
    return {"format_version": ITEM_FORMAT,
            "minecraft:item": {"description": {"identifier": identifier, "menu_category": menu},
                               "components": comps}}


def shaped_recipe(identifier: str, pattern: Sequence[str], key: Dict[str, str], result: str,
                  unlock: Sequence[str]) -> dict:
    return {"format_version": "1.21.60",
            "minecraft:recipe_shaped": {
                "description": {"identifier": identifier},
                "tags": ["crafting_table"],
                "pattern": list(pattern),
                "key": {k: {"item": v} for k, v in key.items()},
                "unlock": [{"item": u} for u in unlock],
                "result": {"item": result, "count": 1}}}


def loot_table(pools: Sequence[dict]) -> dict:
    return {"pools": list(pools)}


def loot_pool(entries: Sequence[Tuple[str, int, int, int]], rolls=1) -> dict:
    """entries: (item, weight, min, max)."""
    return {"rolls": rolls, "entries": [
        {"type": "item", "name": name, "weight": w,
         "functions": [{"function": "set_count", "count": {"min": lo, "max": hi}}]}
        for name, w, lo, hi in entries]}


# --------------------------------------------------------------------------- render controllers

def render_controller(geometry: str = "Geometry.default", texture: str = "Texture.default",
                      materials: Optional[List[dict]] = None, part_visibility: Optional[List[dict]] = None,
                      overlay_color: Optional[dict] = None, is_hurt_color: Optional[dict] = None) -> dict:
    rc: dict = {"geometry": geometry,
                "materials": materials or [{"*": "Material.default"}],
                "textures": [texture]}
    if part_visibility:
        rc["part_visibility"] = part_visibility
    if overlay_color:
        rc["overlay_color"] = overlay_color
    if is_hurt_color:
        rc["is_hurt_color"] = is_hurt_color
    return rc


def layered_materials() -> List[dict]:
    """Bone-name convention shared with the preview renderer: *_glow emissive, *_glass translucent."""
    return [{"*": "Material.default"}, {"*_glow": "Material.glow"}, {"*_glow_*": "Material.glow"},
            {"*_glass": "Material.glass"}, {"*_glass_*": "Material.glass"}]


LAYER_MATERIALS = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "glass": "entity_alphablend"}


# --------------------------------------------------------------------------- packaging

def zip_dir(src: str, dst: str, prefix: str = "") -> int:
    """Deterministic zip of a directory (sorted entries, fixed timestamps)."""
    n = 0
    with zipfile.ZipFile(dst, "a" if os.path.exists(dst) else "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src):
            dirs.sort()
            for f in sorted(files):
                full = os.path.join(root, f)
                rel = os.path.join(prefix, os.path.relpath(full, src)).replace(os.sep, "/")
                zi = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                with open(full, "rb") as fh:
                    z.writestr(zi, fh.read())
                n += 1
    return n


# --------------------------------------------------------------------------- boss production spec

@dataclass
class BossAssets:
    """Everything one boss contributes to the packs."""
    key: str
    models: Dict[str, object] = field(default_factory=dict)              # file stem -> geo.Model
    client_entities: List[object] = field(default_factory=list)          # anim.ClientEntity
    animations: List[object] = field(default_factory=list)               # anim.Anim
    controllers: List[object] = field(default_factory=list)              # anim.Controller
    render_controllers: Dict[str, dict] = field(default_factory=dict)
    bp_entities: Dict[str, dict] = field(default_factory=dict)           # file stem -> definition
    particles: Dict[str, dict] = field(default_factory=dict)             # file stem -> particle json
    textures: Dict[str, object] = field(default_factory=dict)            # RP-relative path (no ext) -> PIL image
    sounds: Dict[str, dict] = field(default_factory=dict)                # sound event id -> {"clips": [...], opts}
    item_icons: Dict[str, object] = field(default_factory=dict)          # icon key -> PIL image (16x16)
    items: Dict[str, dict] = field(default_factory=dict)                 # file stem -> item json
    recipes: Dict[str, dict] = field(default_factory=dict)
    loot: Dict[str, dict] = field(default_factory=dict)                  # table stem -> loot json
    structures: Dict[str, object] = field(default_factory=dict)          # name -> nbt.Structure
    lang: Dict[str, str] = field(default_factory=dict)
    previews: Optional[Callable] = None                                   # fn(out_dir) -> list of image paths
