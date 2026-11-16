"""Build the Playable Races add-on (behavior pack + resource pack + packages).

    python3 tools/build.py            # generate packs/, compile scripts, package dist/
    python3 tools/build.py --no-tsc   # skip TypeScript compilation

Everything in packs/ is generated from tools/ (models, textures, animations,
attachables, particles, items, entities, manifests) and src/ (scripts).
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from kit.tex import paint  # noqa: E402
from kit.render import render  # noqa: E402
from anims import core as acore  # noqa: E402
from anims import races as aset  # noqa: E402
from anims import life  # noqa: E402
from models import salamander, golem, jackalope, xenentoma, spaghetti, nurariten, common  # noqa: E402
from models import dinosauroid, bathyas, octamyces  # noqa: E402
from anims import nurariten as anim_nurariten  # noqa: E402
from anims import xenentoma as anim_xenentoma  # noqa: E402
from anims import spaghetti as anim_spaghetti  # noqa: E402
from anims import dinosauroid as anim_dinosauroid  # noqa: E402
from anims import bathyas as anim_bathyas  # noqa: E402
from anims import octamyces as anim_octamyces  # noqa: E402
import fx  # noqa: E402
import fx_ex  # noqa: E402
from vfx import atlas as vfx_atlas  # noqa: E402

NS = "plrace"
VERSION = [1, 4, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_API = "2.11.0"
UI_API = "2.3.0"
BP_NAME, RP_NAME = "PlayableRaces_BP", "PlayableRaces_RP"
# permanent identifiers (never change: existing worlds depend on them)
UUID = {
    "bp": "6a3f2c1e-8d4b-4f7a-9c2e-1b5d7e9f0a21",
    "bp_data": "7b4e3d2f-9e5c-4a8b-8d3f-2c6e8f0a1b32",
    "bp_script": "8c5f4e3a-af6d-4b9c-9e4a-3d7f9a1b2c43",
    "rp": "9d6a5f4b-b07e-4cad-8f5b-4e8a0b2c3d54",
    "rp_res": "ae7b6a5c-c18f-4dbe-9a6c-5f9b1c3d4e65",
}
PACKS = os.path.join(ROOT, "packs")
BP = os.path.join(PACKS, BP_NAME)
RP = os.path.join(PACKS, RP_NAME)
DIST = os.path.join(ROOT, "dist")
TEXROOT = "textures/plrace/races"

# One entry per race.  Codes and keys are permanent (worlds store them); a new race is a
# model module, an animation set, a RaceDef in src/races and one entry here.
RACES = {
    "salamander": {
        "code": "001", "mod": salamander, "anims": lambda m: aset.salamander(m), "bounds": (3.2, 3.2, (0, 1.2, 0.4)),
        "display": "Aberrant Flora Salamander", "protection": 2, "hover": "green", "focus": ("Dewheart Focus", "green"),
        "variants": {"base": "Stable", "bloom": "Blooming", "dormant": "Dormant", "predatory": "Predatory", "rooted": "Rooted"},
        "icon": {"variant": "bloom", "tex": "bloom", "head": ((0, 27.5, -2), 4.3), "body": ((0, 19, 3), 5.4)},
        "portrait_bg": (24, 58, 30)},
    "golem": {
        "code": "002", "mod": golem, "anims": lambda m: aset.golem(m, list(golem.MOVABLE)), "bounds": (4.6, 4.2, (0, 1.6, 0)),
        "display": "Runic Titan Golem", "protection": 3, "hover": "gold", "focus": ("Rune Keystone Focus", "gold"),
        "variants": {"base": "Aligned", "siege": "Siege Configuration", "bastion": "Bastion Configuration",
                     "arcane": "Arcane Configuration", "scattered": "Reassembling", "disrupted": "Disrupted"},
        "icon": {"variant": "base", "tex": "base", "head": ((0, 37.5, 0), 3.7), "body": ((0, 22, 0), 4.7)},
        "portrait_bg": (52, 40, 18)},
    "jackalope": {
        "code": "003", "mod": jackalope, "anims": lambda m: aset.jackalope(m), "bounds": (3.0, 3.2, (0, 1.2, 0)),
        "display": "Blood Moon Jackalope", "protection": 1, "hover": "red", "focus": ("Moonbone Focus", "red"),
        "variants": {"base": "Ordinary Lunar", "hunt": "Hunting", "awakened": "Blood Moon Awakened",
                     "awakened_hunt": "Blood Moon Hunt"},
        "icon": {"variant": "awakened", "tex": "awakened", "head": ((0, 28.5, -1), 3.4), "body": ((0, 19, 0), 5.8)},
        "portrait_bg": (46, 14, 26)},
    "xenentoma": {
        "code": "004", "mod": xenentoma, "anims": anim_xenentoma.anims, "bounds": (3.8, 3.8, (0, 1.3, 0.5)),
        "display": "Xenentoma", "protection": 2, "hover": "light_purple", "focus": ("Sensillum Focus", "light_purple"),
        "variants": {"base": "Listening", "survey": "Foretarsal Survey", "glide": "Interstitial Glide",
                     "surge": "Anamorphic Surge", "teneral": "Freshly Moulted"},
        "icon": {"variant": "survey", "tex": "sense", "head": ((0, 27.5, -3), 3.6), "body": ((0, 18, 3), 4.6)},
        "portrait_bg": (40, 30, 58)},
    "spaghetti": {
        "code": "005", "mod": spaghetti, "anims": anim_spaghetti.anims, "bounds": (4.0, 3.2, (0, 1.0, 0)),
        "display": "Flying Spaghetti Monster", "protection": 1, "hover": "yellow", "focus": ("Holy Colander Focus", "yellow"),
        "variants": {"base": "Noodly", "rigid": "Al Dente", "detached": "Meatballs Away", "revelation": "Great Pasta Revelation",
                     "brittle": "Overcooked"},
        "icon": {"variant": "base", "tex": "base", "head": ((0, 21, 0), 2.4), "body": ((0, 15, 0), 4.3)},
        "portrait_bg": (70, 50, 18)},
    "nurariten": {
        "code": "006", "mod": nurariten, "anims": anim_nurariten.anims, "bounds": (4.0, 4.0, (0, 1.6, 0.5)),
        "display": "Nurariten", "protection": 2, "hover": "gold", "focus": ("Mandate Shaku Focus", "gold"),
        "variants": {"base": "Uninvited Sovereign", "nocturne": "Nocturne Radiance", "edict": "Celestial Edict",
                     "court": "Uninvited Court", "throne": "The Throne Without Permission"},
        "icon": {"variant": "court", "tex": "radiant", "head": ((0, 29.5, 0), 3.2), "body": ((0, 20, 2), 3.7)},
        "portrait_bg": (60, 46, 22)},
    # ---- Expansion 02 (v1.4.0)
    "dinosauroid": {
        "code": "007", "mod": dinosauroid, "anims": anim_dinosauroid.anims, "bounds": (4.0, 3.6, (0, 1.4, 0.5)),
        "display": "The Unknown Dinosauroid", "protection": 1, "hover": "dark_aqua", "focus": ("Fossil Quill Focus", "dark_aqua"),
        "variants": {"base": "Composed", "night": "Display Skin (night)", "display": "Crest of Misclassification",
                     "veer": "Hindwing Veer", "overflow": "Taxonomic Error"},
        "icon": {"variant": "display", "tex": "base", "head": ((0, 28, -2), 3.6), "body": ((0, 18, 1), 5.0)},
        "portrait_bg": (16, 52, 50)},
    "bathyas": {
        "code": "008", "mod": bathyas, "anims": anim_bathyas.anims, "bounds": (4.0, 4.0, (0, 1.5, 0.3)),
        "display": "Bathyas, the Sun-Impaled", "protection": 2, "hover": "white", "focus": ("Abyssal Hilt Focus", "white"),
        "variants": {"base": "Impaled", "lure": "Lure of the Impaled Sun", "maw": "Goblin Maw Rush", "bastion": "Isopod Bastion",
                     "unshackled": "Unshackled", "daybreak": "Abyssal Daybreak"},
        "icon": {"variant": "base", "tex": "base", "head": ((0, 27, -1), 3.4), "body": ((0, 18, 0), 5.0)},
        "portrait_bg": (14, 26, 40)},
    "octamyces": {
        "code": "009", "mod": octamyces, "anims": anim_octamyces.anims, "bounds": (4.0, 3.6, (0, 1.3, 0)),
        "display": "Octamyces Undecimus", "protection": 1, "hover": "dark_purple", "focus": ("Undecimal Lens Focus", "dark_purple"),
        "variants": {"base": "Witnessing", "sporeveil": "Parallax Sporeveil", "record": "The Eye That Records",
                     "offset": "Hyphal Offset", "frame": "The Eleventh Frame", "unstable": "Destabilised (burning)"},
        "icon": {"variant": "record", "tex": "record", "head": ((0, 25, -2), 3.8), "body": ((0, 17, 0), 5.0)},
        "portrait_bg": (40, 18, 56)},
}
DISPLAY = {race: info["display"] for race, info in RACES.items()}
VARIANT_NAMES = {race: info["variants"] for race, info in RACES.items()}


def crest_variants(race):
    mod = RACES[race]["mod"]
    return [v for v in mod.VARIANTS if v not in getattr(mod, "ENTITY_ONLY", set())]
ARMOR_TINT = [  # (item-name fragment, rgb) for armour assimilation accents
    ("leather", (0.62, 0.42, 0.26)), ("chainmail", (0.62, 0.64, 0.68)), ("golden", (1.0, 0.82, 0.30)),
    ("diamond", (0.36, 0.90, 0.86)), ("netherite", (0.30, 0.26, 0.29)), ("copper", (0.86, 0.52, 0.34)),
    ("turtle", (0.38, 0.66, 0.32)), ("iron", (0.86, 0.86, 0.88)),
]


def wjson(path, data):
    """Write pack JSON: strict (no NaN/Infinity) and with every Molang string in the
    vanilla-proven sign form (see anims.core.canon)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(acore.canon_tree(data), f, indent=1, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def item_id(race, variant):
    return f"{NS}:form_{race}" if variant == "base" else f"{NS}:form_{race}_{variant}"


STATIC = "static"   # display-check twin of each base form: same body, no animation or script at all


def static_id(race):
    return f"{NS}:form_{race}_{STATIC}"


# ============================================================================= models & attachables

def build_races(report):
    lang = []
    geo_index = {}
    for race, info in RACES.items():
        mod = info["mod"]
        model = mod.build()
        info["model"] = model
        mats = mod.materials()
        # textures
        texpaths = {}
        for tv, params in mod.TEXTURES.items():
            img = paint(model, mats, params)
            rel = f"{TEXROOT}/{race}/{race}_{tv}"
            os.makedirs(os.path.dirname(os.path.join(RP, rel)), exist_ok=True)
            img.save(os.path.join(RP, rel + ".png"))
            texpaths[tv] = rel
            info.setdefault("tex_img", {})[tv] = img
        # geometry per variant: solid / cutout / accent passes
        geos = []
        for v in mod.VARIANTS:
            gid = f"geometry.{NS}.{race}.{v}"
            geos.append(model.geometry_json(gid, variant=v, cutout=False, bounds=info["bounds"]))
            if model.has_layer(v, cutout=True):
                geos.append(model.geometry_json(gid + ".cutout", variant=v, cutout=True, bounds=info["bounds"]))
            if model.has_layer(v, accent=True):
                geos.append(model.geometry_json(gid + ".accent", variant=v, cutout=False, accent=True, bounds=info["bounds"]))
        wjson(os.path.join(RP, f"models/entity/plrace/{race}.geo.json"), {"format_version": "1.16.0", "minecraft:geometry": geos})
        geo_index[race] = [g["description"]["identifier"] for g in geos]
        nb, nc = model.stats("base")
        report.append(f"{race}: atlas {model.tex_w}x{model.tex_h}, base form {nb} bones / {nc} cubes, "
                      f"{len(mod.VARIANTS)} variants, {len(mod.TEXTURES)} texture sets")
        # animations
        A = info["anims"](model)
        wjson(os.path.join(RP, f"animations/plrace/{race}.animation.json"), life.compact(acore.file(A["anims"])))
        if A["controllers"]:
            wjson(os.path.join(RP, f"animation_controllers/plrace/{race}.ac.json"),
                  life.compact(acore.controller_file(A["controllers"])))
        report.extend(f"  {line}" for line in aset.FIT_REPORT if line.startswith(race))
        short = {a.name.split(f"animation.{NS}.{race}.")[1]: a.name for a in A["anims"]}
        for cid in A["controllers"]:
            short[cid.split(".")[-1]] = cid
        # attachables (one per form item; entity-only variants are geometry for helper entities)
        for v in crest_variants(race):
            iid = item_id(race, v)
            gid = f"geometry.{NS}.{race}.{v}"
            geometry = {"default": gid}
            rcs = [f"controller.render.{NS}.form"]
            materials = {"default": "entity_emissive_alpha"}
            if model.has_layer(v, cutout=True):
                geometry["cutout"] = gid + ".cutout"
                materials["cutout"] = "entity_alphatest"
                rcs.append(f"controller.render.{NS}.form_cutout")
            if model.has_layer(v, accent=True):
                geometry["accent"] = gid + ".accent"
                materials["accent"] = "entity_alphatest"
                rcs += [f"controller.render.{NS}.{race}_accent_{s}" for s in ("c", "l", "f")]
            animate = []
            used = {}
            for nm, cond in A["animate"][v]:
                if nm not in short:
                    raise KeyError(f"{race}/{v}: animation {nm} missing")
                used[nm] = short[nm]
                animate.append(nm if cond is None else {nm: cond})
            # animations played by controller states must be declared on the attachable too
            for cid in [used[k] for k in list(used) if used[k].startswith("controller.")]:
                for st in A["controllers"][cid]["states"].values():
                    for e in st.get("animations", []):
                        nm = e if isinstance(e, str) else next(iter(e))
                        if nm not in short:
                            raise KeyError(f"{race}/{v}: controller animation {nm} missing")
                        used[nm] = short[nm]
            att = {"format_version": "1.10.0", "minecraft:attachable": {"description": {
                "identifier": iid,
                "materials": materials,
                "textures": {"default": texpaths[mod.VARIANT_TEXTURE[v]]},
                "geometry": geometry,
                "animations": used,
                "particle_effects": A["particles"],
                "scripts": {"pre_animation": A["pre"], "animate": [life.compact(e) for e in animate]},
                "render_controllers": rcs,
            }}}
            wjson(os.path.join(RP, f"attachables/plrace/form_{race}_{v}.json"), att)
            lang.append((f"item.{iid}", f"{DISPLAY[race]} Form ({VARIANT_NAMES[race][v]})"))
            if v == "base":   # the display check's still twin (Codex > Display Check)
                desc = att["minecraft:attachable"]["description"]
                still = {"format_version": "1.10.0", "minecraft:attachable": {"description": {
                    "identifier": static_id(race), "materials": desc["materials"], "textures": desc["textures"],
                    "geometry": desc["geometry"], "render_controllers": desc["render_controllers"]}}}
                wjson(os.path.join(RP, f"attachables/plrace/form_{race}_{STATIC}.json"), still)
                lang.append((f"item.{static_id(race)}", f"{DISPLAY[race]} Form (display check)"))
    # player-skeleton pose animations (scripts trigger these with playAnimation)
    wjson(os.path.join(RP, "animations/plrace/poses.animation.json"), acore.file(aset.poses()))
    return lang, geo_index


def render_controllers():
    rc = {
        f"controller.render.{NS}.form": {
            "geometry": "Geometry.default",
            "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"],
            "is_hurt_color": {"r": 1.0, "g": 0.2, "b": 0.2, "a": 0.45},
            "on_fire_color": {"r": 1.0, "g": 0.55, "b": 0.2, "a": 0.35},
        },
        f"controller.render.{NS}.form_cutout": {
            "geometry": "Geometry.cutout",
            "materials": [{"*": "Material.cutout"}],
            "textures": ["Texture.default"],
            "is_hurt_color": {"r": 1.0, "g": 0.2, "b": 0.2, "a": 0.45},
        },
    }
    # armour assimilation: one pass per armour slot, tinted by the worn armour's material
    for race, info in RACES.items():
        model = info["model"]
        for s, slot in common.ARMOR_SLOTS.items():
            bones = sorted({bn for v in info["mod"].VARIANTS for bn in model.accent_bones(v, f"acc_{s}_")})
            others = sorted({bn for v in info["mod"].VARIANTS for bn in model.accent_bones(v, "acc_")} - set(bones))
            worn = f"query.has_armor_slot({ {'c': 1, 'l': 2, 'f': 3}[s] })"
            vis = [{"*": False}] + [{b: worn} for b in bones] + [{b: False} for b in others]
            rc[f"controller.render.{NS}.{race}_accent_{s}"] = {
                "geometry": "Geometry.accent",
                "materials": [{"*": "Material.accent"}],
                "textures": ["Texture.default"],
                "part_visibility": vis,
                "overlay_color": _tint_expr(slot),
            }
    return {"format_version": "1.10.0", "render_controllers": rc}


def _tint_expr(slot):
    def chan(i):
        expr = str({0: 0.72, 1: 0.74, 2: 0.82}[i])
        for frag, rgb in reversed(ARMOR_TINT):
            names = [f"'minecraft:{frag}_{p}'" for p in ("helmet", "chestplate", "leggings", "boots")]
            expr = f"(query.is_item_name_any('{slot}', 0, {', '.join(names)}) ? {rgb[i]} : {expr})"
        return expr
    return {"r": chan(0), "g": chan(1), "b": chan(2), "a": "0.62"}


def form_hidden_expr():
    """Client-side test 'a race form crest is worn'. Uses explicit item names (always known
    to clients); regenerated automatically when future races add crest items."""
    names = [item_id(r, v) for r in RACES for v in crest_variants(r)] + [static_id(r) for r in RACES]
    return "query.is_item_name_any('slot.armor.head', 0, " + ", ".join(f"'{n}'" for n in names) + ")"


def player_overrides():
    FORM_HIDDEN = form_hidden_expr()
    """Minimal override of two vanilla render controllers.  Everything is the vanilla
    1.26.60 definition; the only addition is '&& !<form worn>' on every part, which
    hides the player's own skin/armour while a race form is manifested."""
    tp_parts = [
        ("*", "true"), ("helmet", "variable.helmet_layer_visible"), ("leftLegging", "variable.leg_layer_visible"),
        ("rightLegging", "variable.leg_layer_visible"), ("leftBoot", "variable.boot_layer_visible"),
        ("rightBoot", "variable.boot_layer_visible"),
        ("leftSock", "variable.boot_layer_visible && variable.leg_layer_visible"),
        ("rightSock", "variable.boot_layer_visible && variable.leg_layer_visible"),
        ("bodyArmor", "variable.chest_layer_visible"), ("leftArmArmor", "variable.chest_layer_visible"),
        ("rightArmArmor", "variable.chest_layer_visible"), ("belt", "variable.chest_layer_visible && variable.leg_layer_visible"),
    ]
    vis = [{p: (f"!{FORM_HIDDEN}" if c == "true" else f"({c}) && !{FORM_HIDDEN}")} for p, c in tp_parts]
    player_rc = {"format_version": "1.8.0", "render_controllers": {
        "controller.render.player.third_person": {
            "geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
            "textures": ["Texture.default"], "part_visibility": vis}}}
    armor_rc = {"format_version": "1.8.0", "render_controllers": {
        "controller.render.armor": {
            "geometry": "Geometry.default",
            "materials": [{"*": "variable.is_enchanted ? Material.enchanted : Material.default"}],
            "textures": ["variable.has_trim ? variable.trim_path : Texture.default", "Texture.enchanted"],
            "part_visibility": [{"*": f"!{FORM_HIDDEN}"}]}}}
    return player_rc, armor_rc


# ============================================================================= items

def items(lang):
    out = {}
    for race, info in RACES.items():
        for v in crest_variants(race) + [STATIC]:
            iid = static_id(race) if v == STATIC else item_id(race, v)
            out[iid] = {"format_version": "1.21.90", "minecraft:item": {
                "description": {"identifier": iid, "menu_category": {"category": "none", "is_hidden_in_commands": True}},
                "components": {
                    "minecraft:icon": f"{NS}:crest_{race}",
                    "minecraft:display_name": {"value": f"item.{iid}"},
                    "minecraft:max_stack_size": 1,
                    "minecraft:wearable": {"slot": "slot.armor.head", "protection": info["protection"]},
                    "minecraft:enchantable": {"slot": "armor_head", "value": 10},
                    "minecraft:tags": {"tags": [f"{NS}:form", f"{NS}:form_{info['code']}", f"{NS}:form_{race}"]},
                    "minecraft:hover_text_color": info["hover"],
                }}}
    for race, info in RACES.items():
        name, col = info["focus"]
        iid = f"{NS}:focus_{race}"
        out[iid] = {"format_version": "1.21.90", "minecraft:item": {
            "description": {"identifier": iid, "menu_category": {"category": "equipment", "is_hidden_in_commands": False}},
            "components": {
                "minecraft:icon": f"{NS}:focus_{race}",
                "minecraft:display_name": {"value": f"item.{iid}"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:glint": False,
                "minecraft:hover_text_color": col,
                "minecraft:use_modifiers": {"use_duration": 1000, "movement_modifier": 1.0},
                "minecraft:tags": {"tags": [f"{NS}:focus"]},
                f"{NS}:focus": {},
            }}}
        lang.append((f"item.{iid}", name))
    out[f"{NS}:codex"] = {"format_version": "1.21.90", "minecraft:item": {
        "description": {"identifier": f"{NS}:codex", "menu_category": {"category": "items"}},
        "components": {
            "minecraft:icon": f"{NS}:codex",
            "minecraft:display_name": {"value": f"item.{NS}:codex"},
            "minecraft:max_stack_size": 64,
            "minecraft:use_modifiers": {"use_duration": 1000, "movement_modifier": 1.0},
            f"{NS}:codex": {},
        }}}
    lang.append((f"item.{NS}:codex", "Lineage Codex"))
    # Bathyas' drawn sun (v1.4): a real weapon that only exists while it is out of his chest.  The
    # scripts lock it to the inventory, never duplicate it and take it back on death, logout or reload.
    out[f"{NS}:sun_sword"] = {"format_version": "1.21.90", "minecraft:item": {
        "description": {"identifier": f"{NS}:sun_sword", "menu_category": {"category": "none", "is_hidden_in_commands": True}},
        "components": {
            "minecraft:icon": f"{NS}:sun_sword",
            "minecraft:display_name": {"value": f"item.{NS}:sun_sword"},
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": True,
            "minecraft:damage": {"value": 7},
            "minecraft:can_destroy_in_creative": False,
            "minecraft:glint": True,
            "minecraft:hover_text_color": "gold",
            "minecraft:tags": {"tags": [f"{NS}:sun_sword"]},
        }}}
    lang.append((f"item.{NS}:sun_sword", "The Impaled Sun"))
    for iid, data in out.items():
        wjson(os.path.join(BP, f"items/plrace/{iid.split(':')[1]}.json"), data)
    recipe = {"format_version": "1.20.10", "minecraft:recipe_shapeless": {
        "description": {"identifier": f"{NS}:codex"}, "tags": ["crafting_table"],
        "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:lapis_lazuli"}, {"item": "minecraft:bone_meal"}],
        "unlock": [{"item": "minecraft:book"}],
        "result": {"item": f"{NS}:codex"}}}
    wjson(os.path.join(BP, "recipes/plrace/codex.json"), recipe)


# ============================================================================= mirage entity

def mirage_entity(lang):
    ident = f"{NS}:velvet_mirage"
    bp = {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": ident, "is_spawnable": False, "is_summonable": True},
        "component_groups": {f"{NS}:expire": {"minecraft:instant_despawn": {}}},
        "components": {
            "minecraft:type_family": {"family": [f"{NS}_mirage", "player", "mob"]},
            "minecraft:health": {"value": 1, "max": 1},
            "minecraft:collision_box": {"width": 0.6, "height": 1.7},
            "minecraft:physics": {},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": True},
            "minecraft:movement": {"value": 0.32},
            "minecraft:movement.basic": {},
            "minecraft:jump.static": {},
            "minecraft:navigation.walk": {"can_walk": True, "avoid_water": True},
            "minecraft:knockback_resistance": {"value": 1.0},
            "minecraft:fire_immune": {},
            "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
            "minecraft:loot": {"table": "loot_tables/empty.json"},
            "minecraft:experience_reward": {"on_death": "0"},
            "minecraft:conditional_bandwidth_optimization": {},
            "minecraft:timer": {"time": 12, "looping": False, "time_down_event": {"event": f"{NS}:expire"}},
            "minecraft:damage_sensor": {"triggers": [{"cause": "fall", "deals_damage": "no"},
                                                     {"cause": "suffocation", "deals_damage": "no"}]},
        },
        "events": {f"{NS}:expire": {"add": {"component_groups": [f"{NS}:expire"]}}}}}
    wjson(os.path.join(BP, "entities/plrace/velvet_mirage.json"), bp)
    # client: re-uses the jackalope form geometry with a translucent spectral texture
    anim = acore.Anim(f"animation.{NS}.mirage.run")
    sw = "math.cos(q.modified_distance_moved * 38.17) * q.modified_move_speed * 57.3"
    anim.bone("rightLeg", rot=[f"{sw} * 1.2", 0, 0]).bone("leftLeg", rot=[f"-{sw} * 1.2", 0, 0])
    anim.bone("rightArm", rot=[f"-{sw} * 0.8", 0, 0]).bone("leftArm", rot=[f"{sw} * 0.8", 0, 0])
    anim.bone("body", rot=[8, 0, 0], pos=[0, "math.abs(math.sin(q.life_time * 540)) * 0.8", 0])
    anim.bone("r_ear", rot=[-20, 0, aset.osc(1.4, 6)]).bone("l_ear", rot=[-20, 0, aset.osc(1.3, -6, 50)])
    for b in common.FIRST_PERSON_ONLY:
        anim.bone(b, scale=0)
    look = acore.Anim(f"animation.{NS}.mirage.look")
    look.bone("head", rot=["q.target_x_rotation", "q.target_y_rotation", 0])
    wjson(os.path.join(RP, "animations/plrace/mirage.animation.json"), acore.file([anim, look]))
    rp = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": ident,
        "materials": {"default": "entity_alphablend", "cutout": "entity_alphablend"},
        "textures": {"default": f"{TEXROOT}/jackalope/jackalope_mirage"},
        "geometry": {"default": f"geometry.{NS}.jackalope.base", "cutout": f"geometry.{NS}.jackalope.base.cutout"},
        "animations": {"run": f"animation.{NS}.mirage.run", "look": f"animation.{NS}.mirage.look"},
        "scripts": {"animate": ["run", "look"]},
        "particle_effects": {"shimmer": f"{NS}:velvet_shimmer"},
        "render_controllers": [f"controller.render.{NS}.mirage", f"controller.render.{NS}.mirage_cutout"],
        "enable_attachables": False}}}
    wjson(os.path.join(RP, "entity/plrace/velvet_mirage.entity.json"), rp)
    lang.append((f"entity.{ident}.name", "Velvet Mirage"))
    # spectral texture: the jackalope atlas washed into translucent moonlight-violet
    base = RACES["jackalope"]["tex_img"]["base"].convert("RGBA")
    px = base.load()
    out = Image.new("RGBA", base.size)
    po = out.load()
    for y in range(base.size[1]):
        for x in range(base.size[0]):
            r, g, b, a = px[x, y]
            if a == 0:
                po[x, y] = (0, 0, 0, 0)
                continue
            lum = (r + g + b) / 3
            po[x, y] = (int(150 + lum * 0.5), int(140 + lum * 0.45), int(230 + lum * 0.1), 150)
    out.save(os.path.join(RP, f"{TEXROOT}/jackalope/jackalope_mirage.png"))


def proxy_entity(lang, ident, name, geometry, texture, anims, families, health=1, size=(0.6, 1.6), timer=30,
                 physics=True, gravity=True, materials=None, scale_events=None, particles=None, extra=None, rcs=None):
    """A script-owned helper entity: no AI, no drops, no XP, a behaviour-pack timer that
    despawns it on its own (safety net), visual only unless `health` > 1."""
    comps = {
        "minecraft:type_family": {"family": [f"{NS}_proxy"] + list(families)},
        "minecraft:health": {"value": health, "max": health},
        "minecraft:collision_box": {"width": size[0], "height": size[1]},
        "minecraft:physics": {"has_gravity": gravity, "has_collision": physics},
        "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
        "minecraft:knockback_resistance": {"value": 1.0},
        "minecraft:fire_immune": {},
        "minecraft:breathable": {"total_supply": 15, "suffocate_time": 0, "breathes_water": True},
        "minecraft:loot": {"table": "loot_tables/empty.json"},
        "minecraft:experience_reward": {"on_death": "0"},
        "minecraft:conditional_bandwidth_optimization": {},
        "minecraft:timer": {"time": timer, "looping": False, "time_down_event": {"event": f"{NS}:expire"}},
        "minecraft:damage_sensor": {"triggers": [{"cause": c, "deals_damage": "no"} for c in ("fall", "suffocation", "drowning", "fire", "fire_tick", "lava")]
                                    if health > 1 else [{"cause": "all", "deals_damage": "no"}]},
    }
    comps.update(extra or {})
    groups = {f"{NS}:expire": {"minecraft:instant_despawn": {}}}
    events = {f"{NS}:expire": {"add": {"component_groups": [f"{NS}:expire"]}}}
    for ev, sc in (scale_events or {}).items():
        groups[f"{NS}:{ev}"] = {"minecraft:scale": {"value": sc}}
        events[f"{NS}:{ev}"] = {"add": {"component_groups": [f"{NS}:{ev}"]}}
    bp = {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": ident, "is_spawnable": False, "is_summonable": True},
        "component_groups": groups, "components": comps, "events": events}}
    short = ident.split(":")[1]
    wjson(os.path.join(BP, f"entities/plrace/{short}.json"), bp)
    rcs = rcs or ([f"controller.render.{NS}.form"] + ([f"controller.render.{NS}.form_cutout"] if "cutout" in geometry else []))
    rp = {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": ident,
        "materials": materials or {"default": "entity_emissive_alpha", "cutout": "entity_alphatest"},
        "textures": {"default": texture},
        "geometry": geometry,
        "animations": {k: v for k, v in anims.items()},
        "scripts": {"animate": list(anims.keys())},
        "particle_effects": particles or {},
        "render_controllers": rcs,
        "enable_attachables": False}}}
    wjson(os.path.join(RP, f"entity/plrace/{short}.entity.json"), rp)
    lang.append((f"entity.{ident}.name", name))


def echo_entity(lang):
    """Octamyces' Hyphal Offset echo (v1.4): its own body left behind for 3 s - visual only."""
    a = acore.Anim(f"animation.{NS}.hyphal_echo.drift", loop=True)
    for b in common.FIRST_PERSON_ONLY:
        a.bone(b, scale=0)
    for k in range(11):
        a.bone(f"ring{k}", rot=[0, 0, f"q.life_time * {(-1) ** k * (40 + 9 * k)}"])
    a.bone("root", pos=[0, "q.life_time * 0.8", 0])
    wjson(os.path.join(RP, "animations/plrace/hyphal_echo.animation.json"), acore.file([a]))
    proxy_entity(lang, f"{NS}:hyphal_echo", "Hyphal Echo", {"default": f"geometry.{NS}.octamyces.base"},
                 f"{TEXROOT}/octamyces/octamyces_base", {"drift": f"animation.{NS}.hyphal_echo.drift"}, ["inanimate"],
                 health=1, size=(0.6, 1.8), timer=6, physics=False, gravity=False,
                 materials={"default": "entity_alphablend"}, rcs=[f"controller.render.{NS}.echo"])


def race_entities(lang):
    """Helper entities of races 004+ (shells, meatballs, gates, heralds, processions)."""
    # Xenentoma: the shed exuvia (a decoy that keeps the creature's shape)
    a = acore.Anim(f"animation.{NS}.exuvia.settle", loop="hold", length=6.0)
    a.bone("body", rot={0.0: [0, 0, 0], 0.4: [6, 0, 0], 6.0: [14, 0, 2]})
    a.bone("thorax", pos={0.0: [0, 0, 0], 6.0: [0, -0.8, 0]})
    a.bone("head", rot={0.0: [0, 0, 0], 1.0: [10, 0, 0], 6.0: [26, 0, -4]})
    for b in common.FIRST_PERSON_ONLY:
        a.bone(b, scale=0)
    wjson(os.path.join(RP, "animations/plrace/exuvia.animation.json"), acore.file([a]))
    proxy_entity(lang, f"{NS}:exuvia", "Shed Exuvia",
                 {"default": f"geometry.{NS}.xenentoma.exuvia", "cutout": f"geometry.{NS}.xenentoma.exuvia.cutout"},
                 f"{TEXROOT}/xenentoma/xenentoma_exuvia", {"settle": f"animation.{NS}.exuvia.settle"},
                 [f"{NS}_decoy", "player", "mob"], health=16, size=(0.6, 1.6), timer=16, physics=True)
    # Flying Spaghetti Monster: a detached meatball (script-steered, no physics)
    mm = spaghetti.build_meatball()
    tex = paint(mm, spaghetti.materials(), spaghetti.TEXTURES["base"])
    tex.save(_mk(os.path.join(RP, f"{TEXROOT}/spaghetti/meatball.png")))
    wjson(os.path.join(RP, "models/entity/plrace/meatball.geo.json"), {"format_version": "1.16.0", "minecraft:geometry": [
        mm.geometry_json(f"geometry.{NS}.meatball", variant=None, cutout=False, bounds=(1.5, 1.5, (0, 0.25, 0)))]})
    spin = acore.Anim(f"animation.{NS}.meatball.spin", loop=True)
    spin.bone("ball", rot=["q.life_time * 720", 0, "math.sin(q.life_time * 400) * 10"])
    for k in range(2):
        spin.bone(f"tether{k}", rot=[aset.osc(3.0, 14, k * 90), aset.osc(2.4, 20, k * 60), 0])
    trail = acore.Anim(f"animation.{NS}.meatball.trail", loop=True, length=0.15)
    trail.particle(0.0, "trail", "trail")
    wjson(os.path.join(RP, "animations/plrace/meatball.animation.json"), acore.file([spin, trail]))
    proxy_entity(lang, f"{NS}:meatball", "Meatball", {"default": f"geometry.{NS}.meatball"},
                 f"{TEXROOT}/spaghetti/meatball", {"spin": f"animation.{NS}.meatball.spin", "trail": f"animation.{NS}.meatball.trail"}, ["inanimate"],
                 health=1, size=(0.5, 0.5), timer=14, physics=False, gravity=False,
                 particles={"trail": f"{NS}:meatball_trail"})
    # Nurariten: the celestial gate, the heralds and the processions of the Hundred Heavens
    for ident, name, builder, geo_id, bounds, anims, families, extra in (
        (f"{NS}:celestial_gate", "Celestial Gate", nurariten.build_gate, "celestial_gate", (12, 14, (0, 6, 0)), "gate", ["inanimate"], {"huge": 3.6}),
        (f"{NS}:herald", "Celestial Herald", nurariten.build_heralds, "herald", (3, 2, (0, 0.6, 0)), "herald", ["inanimate"], None),
        (f"{NS}:procession", "Procession of the Hundred Heavens", nurariten.build_procession, "procession", (3, 3, (0, 0.8, 0)), "procession", ["inanimate"], None),
    ):
        mm = builder()
        tex = paint(mm, nurariten.materials(), nurariten.TEXTURES["radiant"])
        tex.save(_mk(os.path.join(RP, f"{TEXROOT}/nurariten/{geo_id}.png")))
        wjson(os.path.join(RP, f"models/entity/plrace/{geo_id}.geo.json"), {"format_version": "1.16.0", "minecraft:geometry": [
            mm.geometry_json(f"geometry.{NS}.{geo_id}", variant=None, cutout=False, bounds=bounds)]})
        an = acore.Anim(f"animation.{NS}.{geo_id}.idle", loop=True)
        if anims == "gate":
            an.bone("ring", rot=[0, 0, "q.life_time * 24"]).bone("ring_inner", rot=[0, 0, "-q.life_time * 40"])
        elif anims == "herald":
            an.bone("pair", pos=[0, aset.osc(0.5, 0.6), 0]).bone("decree", rot=[aset.osc(0.7, 3), 0, aset.osc(0.4, 2)])
            for sd in ("r", "l"):
                an.bone(f"herald_{sd}", rot=[aset.osc(0.6, 3, 0 if sd == "r" else 90), 0, 0])
        else:
            for row in range(6):
                for sd, ph in (("r", 0), ("l", 180)):
                    an.bone(f"fig_{row}_{sd}", pos=[0, f"math.abs(math.sin(q.life_time * 220 + {row * 60 + ph})) * 0.7", 0],
                            rot=[aset.osc(1.2, 3, row * 60 + ph), 0, aset.osc(0.6, 2, row * 40)])
            an.bone("palanquin", pos=[0, "math.abs(math.sin(q.life_time * 220 + 240)) * 0.5", 0])
            for sd, ph in (("r", 0), ("l", 70)):
                an.bone(f"fig_0_{sd}_banner", rot=[0, aset.osc(0.8, 18, ph), aset.osc(1.1, 4, ph)])
        wjson(os.path.join(RP, f"animations/plrace/{geo_id}.animation.json"), acore.file([an]))
        base_scale = {"herald": 2.2, "procession": 2.0}.get(anims)
        proxy_entity(lang, ident, name, {"default": f"geometry.{NS}.{geo_id}"}, f"{TEXROOT}/nurariten/{geo_id}",
                     {"idle": f"animation.{NS}.{geo_id}.idle"}, families, health=1, size=(0.6, 0.6), timer=20,
                     physics=False, gravity=False, scale_events=extra,
                     extra={"minecraft:scale": {"value": base_scale}} if base_scale else None)


def echo_render_controllers(rc):
    """Octamyces' Hyphal Offset echo: the body, translucent and tinted toward its own iridescence, fading."""
    rc["render_controllers"][f"controller.render.{NS}.echo"] = {
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
        "color": {"r": 0.55, "g": 0.95, "b": 1.0, "a": "math.clamp(0.5 - q.life_time * 0.12, 0.08, 0.5)"}}


def mirage_render_controllers(rc):
    rc["render_controllers"][f"controller.render.{NS}.mirage"] = {
        "geometry": "Geometry.default", "materials": [{"*": "Material.default"}], "textures": ["Texture.default"],
        "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": "0.55 + math.sin(q.life_time * 300) * 0.15"}}
    rc["render_controllers"][f"controller.render.{NS}.mirage_cutout"] = {
        "geometry": "Geometry.cutout", "materials": [{"*": "Material.cutout"}], "textures": ["Texture.default"],
        "color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 0.5}}


# ============================================================================= icons

def _render_icon(race, size, yaw=28, pitch=12, focus="head"):
    info = RACES[race]
    model = info["model"]
    ic = info["icon"]
    tex = info["tex_img"][ic["tex"]]
    v = ic["variant"]
    if focus == "head":
        center, k = ic["head"]
        scale = k * size / 32
    else:
        center, k = ic["body"]
        scale = k * size / 128
    img = render(model, tex, variant=v, yaw=yaw, pitch=pitch, size=(size * 2, size * 2), scale=scale,
                 center=center, ss=2, bg=(0, 0, 0), bloom=False, ground=False, hide=["r_arm_fp", "l_arm_fp"])
    return img


def _key_out_black(img):
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            r, g, b, a = px[x, y]
            if r < 3 and g < 3 and b < 3:
                px[x, y] = (0, 0, 0, 0)
    return img


def icons():
    d = os.path.join(RP, TEXROOT, "items")
    ui = os.path.join(RP, TEXROOT, "ui")
    os.makedirs(d, exist_ok=True)
    os.makedirs(ui, exist_ok=True)
    tex_entries = {}
    for race, info in RACES.items():
        # crest icon: mini head portrait (32px)
        head = _key_out_black(_render_icon(race, 32)).resize((32, 32), Image.LANCZOS)
        head.save(os.path.join(d, f"crest_{race}.png"))
        tex_entries[f"{NS}:crest_{race}"] = {"textures": f"{TEXROOT}/items/crest_{race}"}
        # UI portraits for the lineage selection forms
        por = _render_icon(race, 128, yaw=24, pitch=8, focus="body")
        por = _key_out_black(por).resize((128, 128), Image.LANCZOS)
        bgc = info["portrait_bg"]
        bg = Image.new("RGBA", (128, 128), bgc + (255,))
        g = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(g).ellipse([8, 8, 120, 120], fill=150)
        bg = Image.composite(Image.new("RGBA", (128, 128), tuple(min(255, c * 2) for c in bgc) + (255,)), bg,
                             g.filter(ImageFilter.GaussianBlur(14)))
        bg.alpha_composite(por)
        bg.save(os.path.join(ui, f"portrait_{info['code']}.png"))
    for race, img in _focus_icons().items():
        img.save(os.path.join(d, f"focus_{race}.png"))
        tex_entries[f"{NS}:focus_{race}"] = {"textures": f"{TEXROOT}/items/focus_{race}"}
    _codex_icon().save(os.path.join(d, "codex.png"))
    tex_entries[f"{NS}:codex"] = {"textures": f"{TEXROOT}/items/codex"}
    _sun_sword_icon().save(os.path.join(d, "sun_sword.png"))
    tex_entries[f"{NS}:sun_sword"] = {"textures": f"{TEXROOT}/items/sun_sword"}
    # list form (one entry each): accepted by every client and preferred by the Creator Tools schema
    tex_entries = {k: {"textures": [v["textures"]] if isinstance(v["textures"], str) else v["textures"]} for k, v in tex_entries.items()}
    wjson(os.path.join(RP, "textures/item_texture.json"),
          {"resource_pack_name": RP_NAME, "texture_name": "atlas.items", "texture_data": tex_entries})


def _pix(size=32):
    S = 8
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), S


def _finish(img, size=32):
    return img.resize((size, size), Image.LANCZOS)


def _focus_icons():
    out = {}
    # Dewheart: a dew-filled seed pod cradled by leaves
    img, d, S = _pix()
    d.polygon([(4 * S, 22 * S), (14 * S, 12 * S), (13 * S, 26 * S)], fill=(52, 140, 48, 255))
    d.polygon([(28 * S, 22 * S), (18 * S, 12 * S), (19 * S, 26 * S)], fill=(70, 170, 60, 255))
    d.ellipse([9 * S, 7 * S, 23 * S, 23 * S], fill=(40, 90, 50, 255))
    d.ellipse([11 * S, 9 * S, 21 * S, 21 * S], fill=(230, 70, 110, 255))
    d.ellipse([13 * S, 10 * S, 17 * S, 14 * S], fill=(255, 220, 235, 255))
    for k in range(7):
        a = k * 2 * math.pi / 7
        x, y = 16 * S + math.cos(a) * 8 * S, 15 * S + math.sin(a) * 8 * S
        d.ellipse([x - S, y - S, x + S, y + S], fill=(200, 30, 60, 255))
    out["salamander"] = _finish(img)
    # Rune Keystone: basalt wedge with a glowing glyph
    img, d, S = _pix()
    d.polygon([(8 * S, 6 * S), (24 * S, 6 * S), (27 * S, 26 * S), (5 * S, 26 * S)], fill=(44, 44, 52, 255))
    d.polygon([(8 * S, 6 * S), (24 * S, 6 * S), (22 * S, 9 * S), (10 * S, 9 * S)], fill=(80, 80, 92, 255))
    w = int(1.6 * S)
    d.line([16 * S, 10 * S, 16 * S, 23 * S], fill=(255, 196, 70, 255), width=w)
    d.line([16 * S, 13 * S, 21 * S, 10 * S], fill=(255, 196, 70, 255), width=w)
    d.line([16 * S, 17 * S, 11 * S, 14 * S], fill=(255, 196, 70, 255), width=w)
    d.line([12 * S, 22 * S, 20 * S, 22 * S], fill=(255, 225, 140, 255), width=w)
    d.rectangle([5 * S, 25 * S, 27 * S, 27 * S], fill=(200, 150, 50, 255))
    out["golem"] = _finish(img)
    # Moonbone: a crescent of black bone with a blood-red gem
    img, d, S = _pix()
    d.ellipse([4 * S, 4 * S, 28 * S, 28 * S], fill=(30, 26, 44, 255))
    d.ellipse([10 * S, 2 * S, 32 * S, 24 * S], fill=(0, 0, 0, 0))
    d.ellipse([6 * S, 6 * S, 26 * S, 26 * S], outline=(200, 205, 225, 255), width=S)
    d.ellipse([9 * S, 17 * S, 15 * S, 23 * S], fill=(210, 20, 40, 255))
    d.ellipse([10 * S, 18 * S, 12 * S, 20 * S], fill=(255, 160, 170, 255))
    out["jackalope"] = _finish(img)
    # Sensillum: a pale chitin rod ending in a fan of glowing sensory hairs
    img, d, S = _pix()
    d.polygon([(6 * S, 27 * S), (9 * S, 27 * S), (19 * S, 12 * S), (16 * S, 11 * S)], fill=(226, 220, 206, 255))
    for k, (x, y) in enumerate(((10, 23), (13, 18.5), (16, 14))):
        d.ellipse([(x - 1.6) * S, (y - 1.6) * S, (x + 1.6) * S, (y + 1.6) * S], fill=(140, 118, 176, 255))
    for k in range(7):
        a = -2.3 + k * 0.32
        x2, y2 = 18 * S + math.cos(a) * 11 * S, 11 * S + math.sin(a) * 11 * S
        d.line([18 * S, 11 * S, x2, y2], fill=(222, 204, 255, 255), width=int(0.9 * S))
        d.ellipse([x2 - S, y2 - S, x2 + S, y2 + S], fill=(250, 238, 255, 255))
    out["xenentoma"] = _finish(img)
    # Holy Colander: a steel colander full of spaghetti with a meatball on top
    img, d, S = _pix()
    d.pieslice([4 * S, 6 * S, 28 * S, 30 * S], 0, 180, fill=(170, 176, 186, 255))
    d.rectangle([3 * S, 17 * S, 29 * S, 19 * S], fill=(200, 206, 214, 255))
    for k in range(5):
        x = 8 * S + k * 4 * S
        d.ellipse([x - S, 22 * S, x + S, 24 * S], fill=(90, 94, 104, 255))
    for k in range(6):
        x0 = 6 * S + k * 3.6 * S
        d.arc([x0, 9 * S, x0 + 7 * S, 21 * S], 180, 360, fill=(246, 226, 158, 255), width=int(1.2 * S))
    d.ellipse([12 * S, 6 * S, 21 * S, 15 * S], fill=(140, 72, 40, 255))
    d.ellipse([14 * S, 7 * S, 18 * S, 10 * S], fill=(200, 50, 30, 255))
    out["spaghetti"] = _finish(img)
    # Mandate Shaku: an ivory court baton banded in gold, with a vermilion tassel
    img, d, S = _pix()
    d.polygon([(13 * S, 3 * S), (19 * S, 3 * S), (18 * S, 27 * S), (14 * S, 27 * S)], fill=(238, 232, 214, 255))
    for yy in (6, 14, 22):
        d.rectangle([13 * S, yy * S, 19 * S, (yy + 1.4) * S], fill=(214, 168, 70, 255))
    d.line([16 * S, 27 * S, 16 * S, 30 * S], fill=(190, 40, 30, 255), width=int(1.4 * S))
    d.ellipse([14.6 * S, 28.6 * S, 17.4 * S, 31.4 * S], fill=(200, 46, 32, 255))
    d.ellipse([14.8 * S, 9 * S, 17.2 * S, 11.4 * S], fill=(255, 220, 110, 255))
    out["nurariten"] = _finish(img)
    # Fossil Quill: a fossilised feather in amber-veined stone, a sickle claw for a nib
    img, d, S = _pix()
    d.line([8 * S, 27 * S, 23 * S, 5 * S], fill=(236, 224, 196, 255), width=int(1.3 * S))
    for k in range(8):
        t = 0.18 + k * 0.09
        x, y = 8 * S + (23 - 8) * S * t, 27 * S + (5 - 27) * S * t
        L = (3.5 + 3.2 * math.sin(t * math.pi)) * S
        for side in (-1, 1):
            d.line([x, y, x + side * L * 0.9 - 0.3 * L, y + side * L * 0.55 + 0.2 * L], fill=(62, 200, 170, 255) if k % 2 else (40, 150, 132, 255),
                   width=int(0.9 * S))
    d.polygon([(7 * S, 26 * S), (9.5 * S, 27.5 * S), (5 * S, 31 * S)], fill=(250, 244, 230, 255))
    d.ellipse([18 * S, 8 * S, 21 * S, 11 * S], fill=(255, 176, 70, 255))
    out["dinosauroid"] = _finish(img)
    # Abyssal Hilt: a black, barnacled hilt whose pommel is a small trapped sun
    img, d, S = _pix()
    d.polygon([(14 * S, 10 * S), (18 * S, 10 * S), (19 * S, 25 * S), (13 * S, 25 * S)], fill=(18, 26, 34, 255))
    for yy in (13, 16, 19, 22):
        d.line([13.5 * S, yy * S, 18.5 * S, (yy + 0.8) * S], fill=(56, 92, 96, 255), width=int(0.8 * S))
    d.polygon([(6 * S, 8 * S), (26 * S, 8 * S), (24 * S, 11 * S), (8 * S, 11 * S)], fill=(28, 40, 52, 255))
    d.line([8 * S, 8.5 * S, 24 * S, 8.5 * S], fill=(255, 226, 140, 255), width=int(0.8 * S))
    d.ellipse([11 * S, 24 * S, 21 * S, 31.5 * S], fill=(255, 240, 190, 255))
    d.ellipse([13 * S, 25.5 * S, 19 * S, 30 * S], fill=(255, 255, 245, 255))
    for k in range(8):
        a = k * math.pi / 4
        d.line([16 * S + math.cos(a) * 5.5 * S, 27.8 * S + math.sin(a) * 4.5 * S, 16 * S + math.cos(a) * 7.5 * S,
                27.8 * S + math.sin(a) * 6 * S], fill=(255, 214, 110, 255), width=int(0.7 * S))
    d.polygon([(15 * S, 2 * S), (17 * S, 2 * S), (17.5 * S, 8 * S), (14.5 * S, 8 * S)], fill=(240, 236, 220, 255))
    out["bathyas"] = _finish(img)
    # Undecimal Lens: concentric polygons (3..11 sides) in iridescent violet, cyan and pink, a void pupil
    img, d, S = _pix()
    cols = [(164, 107, 255), (95, 245, 210), (255, 122, 217)]
    for k, sides in enumerate(range(11, 2, -1)):
        r = (14.5 - k * 1.45) * S
        rot = k * 0.37
        pts = [(16 * S + math.cos(rot + i * 2 * math.pi / sides) * r, 16 * S + math.sin(rot + i * 2 * math.pi / sides) * r) for i in range(sides)]
        d.polygon(pts, outline=cols[k % 3] + (255,), width=int(0.9 * S))
    d.ellipse([12.5 * S, 12.5 * S, 19.5 * S, 19.5 * S], fill=(18, 8, 34, 255))
    d.ellipse([14.2 * S, 13.6 * S, 15.6 * S, 15 * S], fill=(230, 220, 255, 255))
    out["octamyces"] = _finish(img)
    return out


def _sun_sword_icon():
    """The Impaled Sun drawn out of the chest: a white-gold blade with a sunburst guard (32 px)."""
    img, d, S = _pix()
    d.polygon([(26.5 * S, 3.5 * S), (28.5 * S, 5.5 * S), (13 * S, 21 * S), (11 * S, 19 * S)], fill=(255, 250, 230, 255))
    d.line([27.5 * S, 4.5 * S, 12 * S, 20 * S], fill=(255, 214, 110, 255), width=int(0.7 * S))
    cx, cy = 11 * S, 21 * S
    for k in range(12):
        a = k * math.pi / 6
        r2 = (5.5 if k % 2 == 0 else 4.0) * S
        d.line([cx, cy, cx + math.cos(a) * r2, cy + math.sin(a) * r2], fill=(255, 206, 90, 255), width=int(0.9 * S))
    d.ellipse([cx - 2.4 * S, cy - 2.4 * S, cx + 2.4 * S, cy + 2.4 * S], fill=(255, 246, 210, 255))
    d.line([9 * S, 23 * S, 4 * S, 28 * S], fill=(30, 36, 44, 255), width=int(2.2 * S))
    d.ellipse([2.5 * S, 26.5 * S, 5.5 * S, 29.5 * S], fill=(255, 226, 140, 255))
    return _finish(img)


def _codex_icon():
    img, d, S = _pix()
    d.rectangle([6 * S, 4 * S, 26 * S, 28 * S], fill=(58, 38, 70, 255))
    d.rectangle([8 * S, 5 * S, 26 * S, 27 * S], fill=(232, 222, 196, 255))
    d.rectangle([6 * S, 4 * S, 24 * S, 27 * S], fill=(70, 44, 86, 255))
    d.rectangle([6 * S, 4 * S, 8 * S, 27 * S], fill=(40, 24, 50, 255))
    for k, col in enumerate(((80, 200, 90), (255, 190, 60), (220, 40, 60))):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        x, y = 16 * S + math.cos(a) * 5 * S, 15 * S + math.sin(a) * 5 * S
        d.ellipse([x - 2.6 * S, y - 2.6 * S, x + 2.6 * S, y + 2.6 * S], fill=col + (255,))
    d.ellipse([12.5 * S, 11.5 * S, 19.5 * S, 18.5 * S], outline=(230, 210, 140, 255), width=S)
    return _finish(img)


def pack_icon(path_bp, path_rp):
    """Nine lineages on soft spotlights in their own colours (3 x 3)."""
    layout = (  # race, spotlight colour, size, x, y   (back row first so the front row overlaps it)
        ("nurariten", (236, 196, 120), 96, -2, 4), ("bathyas", (255, 236, 170), 104, 76, -2), ("golem", (255, 150, 60), 100, 158, 2),
        ("xenentoma", (170, 120, 236), 92, -4, 82), ("octamyces", (180, 110, 255), 92, 82, 80), ("dinosauroid", (70, 214, 182), 96, 162, 80),
        ("salamander", (110, 210, 120), 92, -2, 162), ("spaghetti", (246, 198, 96), 90, 84, 166), ("jackalope", (236, 60, 76), 92, 166, 162))
    icon = Image.new("RGBA", (256, 256), (18, 16, 30, 255))
    vign = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(vign).ellipse([-40, -40, 296, 296], fill=120)
    icon = Image.composite(Image.new("RGBA", (256, 256), (44, 34, 64, 255)), icon, vign.filter(ImageFilter.GaussianBlur(40)))
    for race, col, size, x, y in layout:
        spot = Image.new("L", (256, 256), 0)
        cx, cy = x + size / 2, y + size * 0.56
        ImageDraw.Draw(spot).ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=150)
        icon = Image.composite(Image.new("RGBA", (256, 256), col + (255,)), icon, spot.filter(ImageFilter.GaussianBlur(12)))
    for race, col, size, x, y in layout:
        img = _key_out_black(_render_icon(race, 128, yaw=26, pitch=6, focus="body")).resize((size, size), Image.LANCZOS)
        icon.alpha_composite(img, (x, y))
    icon.save(path_bp)
    icon.save(path_rp)


# ============================================================================= particles, sounds, texts, manifests

def particles():
    fx.atlas().save(_mk(os.path.join(RP, f"{TEXROOT}/particles/particles.png")))
    fx_ex.atlas().save(_mk(os.path.join(RP, f"{TEXROOT}/particles/particles_ex.png")))
    vfx_atlas.atlas().save(_mk(os.path.join(RP, f"{TEXROOT}/particles/particles_vfx.png")))
    for name, data in fx.particles().items():
        wjson(os.path.join(RP, f"particles/plrace/{name}.json"), data)
    wjson(os.path.join(RP, "fogs/plrace_blood_moon.json"), fx.fog())
    wjson(os.path.join(RP, "fogs/plrace_heaven_light.json"), fx.heaven_fog())
    wjson(os.path.join(RP, "fogs/plrace_abyss.json"), fx.abyss_fog())


def _mk(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def texts(lang_rp, lang_bp):
    lines = ["## Playable Races - Foundation + Expansion 01 + Expansion 02 (Races 001-009)"]
    lines += [f"{k}={v}" for k, v in lang_rp]
    os.makedirs(os.path.join(RP, "texts"), exist_ok=True)
    with open(os.path.join(RP, "texts/en_US.lang"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    wjson(os.path.join(RP, "texts/languages.json"), ["en_US"])
    os.makedirs(os.path.join(BP, "texts"), exist_ok=True)
    with open(os.path.join(BP, "texts/en_US.lang"), "w", encoding="utf-8") as f:
        f.write("\n".join([f"{k}={v}" for k, v in lang_bp]) + "\n")
    wjson(os.path.join(BP, "texts/languages.json"), ["en_US"])


def manifests():
    bp = {"format_version": 2, "header": {
        "name": "pack.name", "description": "pack.description", "uuid": UUID["bp"], "version": VERSION,
        "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION, "entry": "scripts/main.js"}],
        "dependencies": [
            {"uuid": UUID["rp"], "version": VERSION},
            {"module_name": "@minecraft/server", "version": SERVER_API},
            {"module_name": "@minecraft/server-ui", "version": UI_API}],
        "metadata": {"authors": ["Playable Races project"], "product_type": "addon",
                     "generated_with": {"plrace_build": ["1.4.0"]}}}
    rp = {"format_version": 2, "header": {
        "name": "pack.name", "description": "pack.description", "uuid": UUID["rp"], "pack_scope": "world",
        "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp"], "version": VERSION}],
        "metadata": {"authors": ["Playable Races project"], "product_type": "addon",
                     "generated_with": {"plrace_build": ["1.4.0"]}}}
    wjson(os.path.join(BP, "manifest.json"), bp)
    wjson(os.path.join(RP, "manifest.json"), rp)


def compile_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        print("!! node_modules missing - run `npm install` (skipping script compile)")
        return False
    r = subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json")], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-6000:], r.stderr[-2000:])
        raise SystemExit("TypeScript compilation failed")
    return True


def package():
    os.makedirs(DIST, exist_ok=True)

    def zipdir(zf, folder, arc_root):
        for base, _, files in os.walk(folder):
            for fn in sorted(files):
                full = os.path.join(base, fn)
                rel = os.path.relpath(full, folder)
                zf.write(full, os.path.join(arc_root, rel) if arc_root else rel)

    paths = {}
    for name, folder in ((BP_NAME, BP), (RP_NAME, RP)):
        p = os.path.join(DIST, f"{name}.mcpack")
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
            zipdir(zf, folder, "")
        paths[name] = p
    addon = os.path.join(DIST, "PlayableRaces.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as zf:
        zipdir(zf, BP, BP_NAME)
        zipdir(zf, RP, RP_NAME)
    paths["addon"] = addon
    return paths


def main():
    no_tsc = "--no-tsc" in sys.argv
    for d in (BP, RP):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    report = []
    lang_rp, _ = build_races(report)
    rc = render_controllers()
    mirage_entity(lang_rp)
    race_entities(lang_rp)
    echo_entity(lang_rp)
    mirage_render_controllers(rc)
    echo_render_controllers(rc)
    wjson(os.path.join(RP, "render_controllers/plrace/forms.render_controllers.json"), rc)
    prc, arc = player_overrides()
    wjson(os.path.join(RP, "render_controllers/plrace/player_form_visibility.render_controllers.json"), prc)
    wjson(os.path.join(RP, "render_controllers/plrace/armor_form_visibility.render_controllers.json"), arc)
    items(lang_rp)
    icons()
    particles()
    pack_icon(os.path.join(BP, "pack_icon.png"), os.path.join(RP, "pack_icon.png"))
    lang_rp = [("pack.name", "Playable Races (Resources)"), (f"{NS}.rp_version", ".".join(map(str, VERSION))),
               ("pack.description", "Races 001-009: Flora Salamander, Runic Titan Golem, Blood Moon Jackalope, Xenentoma, Flying Spaghetti Monster, Nurariten [Unique], Unknown Dinosauroid, Bathyas [Unique], Octamyces Undecimus")] + lang_rp
    lang_bp = [("pack.name", "Playable Races"),
               ("pack.description", "Nine playable lineages: Salamander, Golem, Jackalope, Xenentoma, Flying Spaghetti Monster, the Unique Nurariten, the Unknown Dinosauroid, the Unique Bathyas and Octamyces Undecimus")]
    texts(lang_rp, lang_bp)
    manifests()
    compiled = False if no_tsc else compile_scripts()
    paths = package()
    for line in report:
        print(" -", line)
    print("scripts compiled:", compiled)
    for k, p in paths.items():
        print(f" {k}: {os.path.relpath(p, ROOT)} ({os.path.getsize(p) // 1024} KB)")


if __name__ == "__main__":
    main()
