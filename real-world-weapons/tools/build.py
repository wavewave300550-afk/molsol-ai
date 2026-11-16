"""
Build "Real-World Weapons — Base Release 01".

    python3 tools/build.py        -> build/RWW_BP, build/RWW_RP, dist/*.mcpack, dist/*.mcaddon

Generates every pack file (21 items, recipes, creative catalog, 3 geometries,
21 model textures, 21 icons, 21 attachables, attachable + player animations,
sounds, language files, manifests), compiles the TypeScript gameplay script
and packages the add-on.  The build is deterministic.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from rww import anims, icons, swords  # noqa: E402
from rww.materials import TIER_ORDER, TIERS  # noqa: E402
from rww.stats import NUGGET, TIER_ITEM, WEAPONS, item_id, stats  # noqa: E402

BUILD = os.path.join(ROOT, "build")
BP = os.path.join(BUILD, "RWW_BP")
RP = os.path.join(BUILD, "RWW_RP")
DIST = os.path.join(ROOT, "dist")

ADDON = "Real-World Weapons"
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 60]
SERVER_VERSION = "2.11.0"
ITEM_FORMAT = "1.26.60"
RECIPE_FORMAT = "1.26.60"
UUID = {
    "bp_header": "4f6d2b8e-1c3a-4e5f-9a7b-2d8c6e0f1a01",
    "bp_data": "4f6d2b8e-1c3a-4e5f-9a7b-2d8c6e0f1a02",
    "bp_script": "4f6d2b8e-1c3a-4e5f-9a7b-2d8c6e0f1a03",
    "rp_header": "9b3e7c1d-5a2f-4d8e-b6c4-8f1a2e3d4c01",
    "rp_res": "9b3e7c1d-5a2f-4d8e-b6c4-8f1a2e3d4c02",
}
WEAPON_ORDER = ["rapier", "zweihander", "katana"]
ICON_ITEM = "iron"

# --------------------------------------------------------------------------- names
NAMES_EN = {w: WEAPONS[w]["name"] for w in WEAPON_ORDER}
GROUP_EN = {"rapier": "Rapiers", "zweihander": "Zweihänder", "katana": "Katanas"}

SOUNDS = {
    # event: (vanilla sound files, pitch, volume) — reuses vanilla audio at weapon-specific pitches
    "rww.rapier.swing": (["sounds/item/spear/attackmiss1", "sounds/item/spear/attackmiss2", "sounds/item/spear/attackmiss3"], 1.35, 0.55),
    "rww.rapier.hit": (["sounds/item/spear/attackhit1", "sounds/item/spear/attackhit2", "sounds/item/spear/attackhit3"], 1.25, 0.8),
    "rww.katana.swing": (["sounds/item/spear/attackmiss1", "sounds/item/spear/attackmiss2", "sounds/item/spear/attackmiss3"], 1.08, 0.7),
    "rww.katana.hit": (["sounds/mob/player/attack/strong1", "sounds/mob/player/attack/strong2", "sounds/mob/player/attack/strong3"], 1.15, 0.9),
    "rww.zweihander.swing": (["sounds/item/mace/smash_air1", "sounds/item/mace/smash_air2", "sounds/item/mace/smash_air3"], 1.0, 0.8),
    "rww.zweihander.hit": (["sounds/mob/player/attack/strong1", "sounds/mob/player/attack/strong2", "sounds/mob/player/attack/strong3"], 0.75, 1.0),
    "rww.zweihander.sweep": (["sounds/item/spear/attackmiss1", "sounds/item/spear/attackmiss2", "sounds/item/spear/attackmiss3"], 0.7, 0.8),
}


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def display_name(weapon, tier):
    return f"{TIERS[tier].name} {NAMES_EN[weapon]}"


# --------------------------------------------------------------------------- behavior pack

def manifests():
    bp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["bp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [
            {"type": "data", "uuid": UUID["bp_data"], "version": VERSION},
            {"type": "script", "language": "javascript", "uuid": UUID["bp_script"], "version": VERSION,
             "entry": "scripts/main.js"},
        ],
        "dependencies": [
            {"module_name": "@minecraft/server", "version": SERVER_VERSION},
            {"uuid": UUID["rp_header"], "version": VERSION},
        ],
        "metadata": {"authors": ["Real-World Weapons"], "product_type": "addon"},
    }
    rp = {
        "format_version": 2,
        "header": {"name": "pack.name", "description": "pack.description", "uuid": UUID["rp_header"],
                   "version": VERSION, "min_engine_version": MIN_ENGINE},
        "modules": [{"type": "resources", "uuid": UUID["rp_res"], "version": VERSION}],
        "dependencies": [{"uuid": UUID["bp_header"], "version": VERSION}],
        "metadata": {"authors": ["Real-World Weapons"], "product_type": "addon"},
    }
    write_json(os.path.join(BP, "manifest.json"), bp)
    write_json(os.path.join(RP, "manifest.json"), rp)
    pi = icons.pack_icon()
    for p in (BP, RP):
        pi.save(os.path.join(p, "pack_icon.png"))


def item_json(weapon, tier):
    s = stats(weapon, tier)
    w = WEAPONS[weapon]
    iid = item_id(weapon, tier)
    repair_material = TIER_ITEM[tier][1]
    comps = {
        "minecraft:icon": {"textures": {"default": f"rww_{tier}_{weapon}"}},
        "minecraft:display_name": {"value": f"item.{iid}.name"},
        "minecraft:max_stack_size": {"value": 1},
        "minecraft:hand_equipped": {"value": True},
        "minecraft:can_destroy_in_creative": {"value": False},
        "minecraft:damage": {"value": s["damage"]},
        "minecraft:durability": {"max_durability": s["durability"]},
        "minecraft:repairable": {"repair_items": [
            {"items": [iid], "repair_amount": "context.other->query.remaining_durability + 0.12 * query.max_durability"},
            {"items": [repair_material], "repair_amount": "query.max_durability * 0.25"},
        ]},
        "minecraft:enchantable": {"slot": "sword", "value": s["enchantability"]},
        "minecraft:tags": {"tags": [f"minecraft:{tier}_tier", "rww:weapon", f"rww:{weapon}", f"rww:tier_{tier}"]},
        "minecraft:cooldown": {"category": "rww:weapon", "duration": s["cooldown"], "type": "attack"},
        "minecraft:swing_duration": {"value": s["cooldown"]},
        "minecraft:swing_sounds": {"attack_miss": f"rww.{weapon}.swing", "attack_hit": f"rww.{weapon}.hit",
                                   "attack_critical_hit": "game.player.attack.critical"},
        "rww:weapon": {"type": weapon, "tier": tier, "damage": s["total_damage"]},
    }
    if w["reach"]:
        comps["minecraft:piercing_weapon"] = {
            "reach": {"min": w["reach"][0], "max": w["reach"][1]},
            "creative_reach": {"min": w["creative_reach"][0], "max": w["creative_reach"][1]},
            "hitbox_margin": w["hitbox_margin"],
        }
    if tier == "wooden":
        comps["minecraft:fuel"] = {"duration": 10.0}
    if tier == "netherite":
        comps["minecraft:fire_resistant"] = {"value": True}
    return {"format_version": ITEM_FORMAT,
            "minecraft:item": {"description": {"identifier": iid}, "components": comps}}


PATTERNS = {
    "rapier": ["  M", " M ", "S  "],          # slender blade, swept hilt
    "katana": [" M", " M", "S "],             # curved blade (offset hilt)
    "zweihander": [" M ", " M ", "MSM"],      # long blade, broad cross-guard
}


def recipes():
    out = {}
    for weapon in WEAPON_ORDER:
        for tier in TIER_ORDER:
            iid = item_id(weapon, tier)
            if tier == "netherite":
                out[f"smithing_netherite_{weapon}"] = {"format_version": RECIPE_FORMAT, "minecraft:recipe_smithing_transform": {
                    "description": {"identifier": f"rww:smithing_netherite_{weapon}"},
                    "tags": ["smithing_table"],
                    "template": "minecraft:netherite_upgrade_smithing_template",
                    "base": item_id(weapon, "diamond"),
                    "addition": "minecraft:netherite_ingot",
                    "result": iid}}
                continue
            mat = TIER_ITEM[tier][0]
            out[f"{tier}_{weapon}"] = {"format_version": RECIPE_FORMAT, "minecraft:recipe_shaped": {
                "description": {"identifier": iid},
                "tags": ["crafting_table"],
                "pattern": PATTERNS[weapon],
                "key": {"M": mat, "S": {"item": "minecraft:stick"}},
                "unlock": [mat],
                "result": {"item": iid}}}
            if tier in NUGGET:
                out[f"furnace_{tier}_{weapon}"] = {"format_version": RECIPE_FORMAT, "minecraft:recipe_furnace": {
                    "description": {"identifier": f"rww:furnace_{tier}_{weapon}"},
                    "unlock": [{"item": iid}],
                    "tags": ["furnace", "blast_furnace"],
                    "input": iid,
                    "output": NUGGET[tier]}}
    return out


def behavior_pack():
    for weapon in WEAPON_ORDER:
        for tier in TIER_ORDER:
            write_json(os.path.join(BP, "items", weapon, f"{tier}_{weapon}.json"), item_json(weapon, tier))
    for name, r in recipes().items():
        write_json(os.path.join(BP, "recipes", f"{name}.json"), r)
    catalog = {"format_version": "1.21.60", "minecraft:crafting_items_catalog": {"categories": [{
        "category_name": "equipment",
        "groups": [{"group_identifier": {"icon": item_id(w, ICON_ITEM), "name": f"rww:itemGroup.name.{w}"},
                    "items": [item_id(w, t) for t in TIER_ORDER]} for w in WEAPON_ORDER]}]}}
    write_json(os.path.join(BP, "item_catalog", "crafting_item_catalog.json"), catalog)
    write_text(os.path.join(BP, "texts", "en_US.lang"),
               f"pack.name={ADDON} BP\npack.description=Rapier, Zweihänder and Katana in seven material tiers. Requires the {ADDON} resource pack.\n")
    write_json(os.path.join(BP, "texts", "languages.json"), ["en_US"])


# --------------------------------------------------------------------------- resource pack

def resource_pack():
    item_textures = {}
    attach_anims = {}
    for weapon in WEAPON_ORDER:
        m = swords.BUILDERS[weapon]()
        m.layout()
        write_json(os.path.join(RP, "models", "entity", "rww", f"{weapon}.geo.json"),
                   m.geometry_json(bounds=(5.0, 5.0), offset=(0.0, 1.5, 0.0)))
        for tier in TIER_ORDER:
            tex = m.paint(swords.painters(weapon, tier))
            p = os.path.join(RP, "textures", "entity", "rww", f"{weapon}_{tier}.png")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tex.save(p)
            ip = os.path.join(RP, "textures", "items", "rww", f"{tier}_{weapon}.png")
            os.makedirs(os.path.dirname(ip), exist_ok=True)
            icons.icon(weapon, tier).save(ip)
            item_textures[f"rww_{tier}_{weapon}"] = {"textures": f"textures/items/rww/{tier}_{weapon}"}
            write_json(os.path.join(RP, "attachables", "rww", f"{tier}_{weapon}.json"), attachable(weapon, tier))
        attach_anims.update(anims.attachable_animations(weapon))
    write_json(os.path.join(RP, "textures", "item_texture.json"),
               {"resource_pack_name": "rww", "texture_name": "atlas.items", "texture_data": item_textures})
    write_json(os.path.join(RP, "animations", "rww_attachables.animation.json"),
               {"format_version": "1.10.0", "animations": attach_anims})
    player_anims = {}
    for weapon in WEAPON_ORDER:
        wa = anims.solve_weapon(weapon)
        player_anims[f"animation.rww.{weapon}.arms"] = anims.arms_animation(wa)
        player_anims[f"animation.rww.{weapon}.body"] = anims.body_animation(wa)
    write_json(os.path.join(RP, "animations", "rww_player.animation.json"),
               {"format_version": "1.10.0", "animations": player_anims})
    sounds = {}
    for ev, (files, pitch, vol) in SOUNDS.items():
        sounds[ev] = {"category": "player",
                      "sounds": [{"name": f, "pitch": pitch, "volume": vol} for f in files]}
    write_json(os.path.join(RP, "sounds", "sound_definitions.json"),
               {"format_version": "1.20.20", "sound_definitions": sounds})
    langs()


def attachable(weapon, tier):
    return {"format_version": "1.10.0", "minecraft:attachable": {"description": {
        "identifier": item_id(weapon, tier),
        "materials": {"default": "entity_alphatest", "enchanted": "entity_alphatest_glint"},
        "textures": {"default": f"textures/entity/rww/{weapon}_{tier}", "enchanted": "textures/misc/enchanted_item_glint"},
        "geometry": {"default": f"geometry.rww.{weapon}"},
        "animations": {"hold_first_person": f"animation.rww.{weapon}.hold_fp",
                       "hold_third_person": f"animation.rww.{weapon}.hold_tp"},
        "scripts": {"animate": [{"hold_first_person": "c.is_first_person"},
                                {"hold_third_person": "!c.is_first_person"}]},
        "render_controllers": ["controller.render.item_default"],
    }}}


def langs():
    en = [f"pack.name={ADDON}",
          "pack.description=Base Release 01: historically researched Rapier, Zweihänder and Katana in seven material tiers."]
    for w in WEAPON_ORDER:
        en.append(f"rww:itemGroup.name.{w}={GROUP_EN[w]}")
        for t in TIER_ORDER:
            en.append(f"item.{item_id(w, t)}.name={display_name(w, t)}")
    write_text(os.path.join(RP, "texts", "en_US.lang"), "\n".join(en) + "\n")
    write_json(os.path.join(RP, "texts", "languages.json"), ["en_US"])


# --------------------------------------------------------------------------- scripts + packaging

def compile_scripts():
    tsc = os.path.join(ROOT, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        raise SystemExit("TypeScript not installed: run `npm install` first")
    subprocess.run([tsc, "-p", os.path.join(ROOT, "tsconfig.json")], check=True, cwd=ROOT)


def zip_dir(src, dst, prefix=""):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in sorted(os.walk(src)):
            for f in sorted(files):
                full = os.path.join(base, f)
                arc = os.path.join(prefix, os.path.relpath(full, src))
                info = zipfile.ZipInfo(arc, date_time=(2026, 11, 16, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(full, "rb") as fh:
                    z.writestr(info, fh.read())


def package():
    os.makedirs(DIST, exist_ok=True)
    bp_pack = os.path.join(DIST, "Real_World_Weapons_BP.mcpack")
    rp_pack = os.path.join(DIST, "Real_World_Weapons_RP.mcpack")
    zip_dir(BP, bp_pack)
    zip_dir(RP, rp_pack)
    addon = os.path.join(DIST, "Real_World_Weapons.mcaddon")
    with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in ((BP, "Real_World_Weapons_BP"), (RP, "Real_World_Weapons_RP")):
            for base, _, files in sorted(os.walk(src)):
                for f in sorted(files):
                    full = os.path.join(base, f)
                    arc = os.path.join(name, os.path.relpath(full, src))
                    info = zipfile.ZipInfo(arc, date_time=(2026, 11, 16, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(full, "rb") as fh:
                        z.writestr(info, fh.read())
    return addon


def main():
    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    manifests()
    behavior_pack()
    resource_pack()
    compile_scripts()
    addon = package()
    n_items = len(WEAPON_ORDER) * len(TIER_ORDER)
    print(f"built {n_items} items -> {os.path.relpath(addon, ROOT)}")


if __name__ == "__main__":
    main()
