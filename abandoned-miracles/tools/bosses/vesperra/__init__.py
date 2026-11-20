"""Boss 001 - Vesperra, The Ivory Succession: everything she contributes to the packs."""
from __future__ import annotations

import json
import os

from kit import icons
from kit import pack as K
from kit.anim import Anim, ClientEntity, Controller
from kit.molang import prop, q, sin
from . import anims, arena, fx, model

KEY = "vesperra"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# What tools/previews.py renders for this boss.
PREVIEW = {
    "title": "Vesperra, The Ivory Succession",
    "phase2": "The True Empress",
    "base": ["idle", "walk", "turn"],
    "base_p2": ["p2_pose", "p2_flutter"],
    "hidden": ["shield_c_crack", "shell_l_crack", "shell_r_crack"],
    "actions": [
        (["scythe_p1"], 0.85, 1, "01 Ivory Scythe - raise"),
        (["scythe_p1"], 1.3, 1, "01 Ivory Scythe - sweep"),
        (["procession_p1"], 1.8, 1, "02 Needle Procession"),
        (["molting_p1"], 1.56, 1, "03 Royal Molting - eject"),
        (["cocoon_p1"], 1.6, 1, "04 Cocoon Edict - weaving"),
        (["feint_p1"], 1.3, 1, "05 False Submission - feint"),
        (["feint_p1"], 2.62, 1, "05 False Submission - thrust"),
        (["stagger"], 0.6, 1, "genuine stagger (compare 05)"),
        (["heirs_p1"], 1.0, 1, "06 The Heirs - call"),
        (["coronation_p1"], 1.3, 1, "07 Coronation of Fracture"),
        (["scythe_p2", "scythe_thrust_p2"], 3.54, 2, "Phase II - scythe thrust"),
        (["death"], 8.8, 2, "death - final pose"),
    ],
    "gifs": [
        ("walk", [], 0.0, 3.6, 1, 1.7),
        ("transition", ["transition"], 0.0, 6.5, 1, 0.0),
        ("royal_molting", ["molting_p1"], 0.0, 3.8, 1, 0.0),
        ("death", ["death"], 0.0, 8.8, 2, 0.0),
    ],
}


def timings() -> dict:
    with open(os.path.join(ROOT, "shared", f"{KEY}.timings.json"), encoding="utf-8") as f:
        return json.load(f)


def _helpers():
    """Heir and cocoon anchor: small rigs with their own motion."""
    lt = q("life_time")
    dist = q("modified_distance_moved") * 0.25      # blocks (the query counts four units per block)
    A = "animation.abm.vesperra_heir."
    heir = ClientEntity("abm:vesperra_heir", "geometry.abm.vesperra_heir", "textures/entity/abm/vesperra_heir")
    heir.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha"}
    heir.render_controllers = ["controller.render.abm.layered"]
    idle = Anim(A + "idle", loop=True)
    idle.set("body", "pos", [0, sin(lt * 300) * 0.4, 0]).rot("body", sin(lt * 190) * 3, 0, sin(lt * 240) * 4)
    walk = Anim(A + "walk", loop=True)
    for tag, side in (("l", 1), ("r", -1)):
        for n in (1, 2, 3):
            ph = (n * 120 + (0 if side > 0 else 180))
            walk.rot(f"leg_{tag}{n}", 0, sin(dist * 520 + ph) * 26 * side, 0)
            walk.rot(f"leg_{tag}{n}_b", 0, 0, sin(dist * 520 + ph + 90) * 14 * side)
    emerge = Anim(A + "emerge", length=0.7)
    emerge.track("body", "scale", [(0, [0.2, 0.2, 0.2]), (0.5, [1.15, 1.15, 1.15], "out"), (0.7, [1, 1, 1], "inout")])
    emerge.track("body", "pos", [(0, [0, 10, 0]), (0.5, [0, 0, 0], "bounce")])
    bite = Anim(A + "bite", length=0.8, loop="hold")
    bite.track("body", "rot", [(0, [0, 0, 0]), (0.5, [-34, 0, 0], "out"), (0.6, [22, 0, 0], "snap"), (0.8, [0, 0, 0], "out")])
    bite.track("body", "pos", [(0, [0, 0, 0]), (0.5, [0, 3, 3], "out"), (0.6, [0, 0, -7], "snap"), (0.8, [0, 0, 0], "out")])
    bite.sound(0.58, "bite")
    hc = Controller("controller.animation.abm.vesperra_heir", "emerge")
    hc.state("emerge", ["emerge"], [("idle", q("all_animations_finished"))], blend=0.1)
    hc.state("idle", [], [("bite", prop("abm:anim").eq(1))], blend=0.1)
    hc.state("bite", ["bite"], [("idle", prop("abm:anim").ne(1))], blend=0.1)
    for a in (idle, walk, emerge, bite):
        heir.animations[a.name[len(A):]] = a.name
    heir.animations["ctl"] = hc.name
    heir.animate = ["idle", "walk", "ctl"]
    heir.sound_effects = {"bite": "abm.vesperra.heir_bite"}

    B = "animation.abm.cocoon_anchor."
    anchor = ClientEntity("abm:cocoon_anchor", "geometry.abm.cocoon_anchor", "textures/entity/abm/cocoon_anchor")
    anchor.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha"}
    anchor.render_controllers = ["controller.render.abm.layered"]
    pulse = Anim(B + "pulse", loop=True)
    pulse.scale("pod", 1 + sin(lt * 400) * 0.07, 1 - sin(lt * 400) * 0.05, 1 + sin(lt * 400) * 0.07)
    pulse.rot("pod", sin(lt * 130) * 4, 0, sin(lt * 170) * 4)
    grow = Anim(B + "grow", length=0.5)
    grow.track("root", "scale", [(0, [0.1, 0.1, 0.1]), (0.35, [1.2, 1.2, 1.2], "out"), (0.5, [1, 1, 1], "inout")])
    for a in (pulse, grow):
        anchor.animations[a.name[len(B):]] = a.name
    anchor.animate = ["pulse", "grow"]
    return [heir, anchor], [idle, walk, emerge, bite, pulse, grow], [hc]


def assets() -> K.BossAssets:
    T = timings()
    out = K.BossAssets(KEY)
    boss = model.build()
    heir_m, anchor_m = model.build_heir(), model.build_anchor()
    out.models = {"vesperra": boss, "vesperra_heir": heir_m, "cocoon_anchor": anchor_m}

    anim_list, ctrls, ce = anims.build_all(T)
    ce.particle_effects = fx.client_particles()
    snd = fx.sounds()
    ce.sound_effects = {k: f"abm.vesperra.{k}" for k in snd}
    helper_ce, helper_anims, helper_ctrls = _helpers()
    out.client_entities = [ce] + helper_ce
    out.animations = anim_list + helper_anims
    # models face the yaw the script publishes (abm:yaw), not whatever the engine does with the body
    from kit.anim import add_facing
    for _ce in out.client_entities:
        if _ce.identifier in ('abm:vesperra', 'abm:vesperra_heir'):
            out.animations.append(add_facing(_ce, "animation." + _ce.identifier.replace(":", ".") + "."))
    out.controllers = ctrls + helper_ctrls

    al, ar, ac, molt = (f"q.property('abm:{n}')" for n in ("armor_l", "armor_r", "armor_c", "molt"))
    out.render_controllers["controller.render.abm.vesperra"] = K.render_controller(
        materials=[{"*": "Material.default"}, {"*_glow": "Material.glow"}],
        part_visibility=[
            {"*": True},
            {"shell_l*": f"{al} < 2"}, {"shell_r*": f"{ar} < 2"}, {"shield_c*": f"{ac} < 2"},
            {"shell_l_crack": f"{al} == 1"}, {"shell_r_crack": f"{ar} == 1"}, {"shield_c_crack": f"{ac} == 1"},
            {"shell_l_over": f"{al} < 2 && {molt} < 1"}, {"shell_r_over": f"{ar} < 2 && {molt} < 1"},
            {"shell_f_over": f"{molt} < 1"}, {"shell_b_over": f"{molt} < 1"}, {"shell_b_collar": f"{molt} < 2"},
        ])

    out.bp_entities["vesperra"] = K.boss_entity(
        "abm:vesperra", "abm_vesperra", 480, 3.0, 5.6, 4.6, 7.0, "loot_tables/abm/vesperra.json",
        {"abm:armor_l": K.int_prop(0, 2), "abm:armor_r": K.int_prop(0, 2), "abm:armor_c": K.int_prop(0, 2),
         "abm:molt": K.int_prop(0, 2)})
    out.bp_entities["vesperra_heir"] = K.helper_entity("abm:vesperra_heir", "abm_heir", 14, 1.1, 0.9, 45,
                                                       knockback_resistance=0.6)
    out.bp_entities["cocoon_anchor"] = K.helper_entity("abm:cocoon_anchor", "abm_anchor", 8, 0.9, 1.7, 20)

    out.particles = fx.particles()
    out.textures["textures/particle/abm/vesperra"] = fx.sprite_sheet()
    out.sounds = {f"abm.vesperra.{k}": v for k, v in snd.items()}

    out.item_icons["abm_seal_vesperra"] = icons.seal(
        ["...##...", "..#..#..", ".#.##.#.", "#.#..#.#", ".#.##.#.", "..####..", ".#.##.#.", "#..##..#"],
        "#c2a04a", "#e6dcc2", "#b7a585", "#f6efdc", "#7d1f2e")
    out.item_icons["abm_ivory_diadem"] = icons.icon([
        "................",
        "......b.........",
        "......b...b.....",
        "..b...i...b.....",
        "..b..bib..i..b..",
        "..i..iii.bib.b..",
        ".bib.iwi.iii.i..",
        ".iii.iii.iwi.ib.",
        ".iwiiigiiiiiiii.",
        ".ggggggrggggggg.",
        ".giiiigggiiiiig.",
        "..sisiiiiiisis..",
        "...ss.sccs.ss...",
        "......c..c......",
        "................",
        "................",
    ], {"b": "#cdbf9f", "i": "#f0e8d2", "w": "#ffffff", "g": "#c2a04a", "r": "#a2354a", "s": "#b7a585", "c": "#5a4a38"})
    out.items["seal_vesperra"] = K.item("abm:seal_vesperra", "abm_seal_vesperra", stack=1, rarity="rare")
    out.items["ivory_diadem"] = K.item("abm:ivory_diadem", "abm_ivory_diadem", stack=1, glint=True, rarity="epic",
                                       cooldown=("abm_trophy", 3.0))
    out.recipes["seal_vesperra"] = K.shaped_recipe(
        "abm:seal_vesperra", ["QBQ", "BEB", "QBQ"],
        {"Q": "minecraft:quartz_block", "B": "minecraft:bone_block", "E": "minecraft:fermented_spider_eye"},
        "abm:seal_vesperra", ["minecraft:bone_block"])
    out.loot["vesperra"] = K.loot_table([
        K.loot_pool([("abm:ivory_diadem", 1, 1, 1)]),
        K.loot_pool([("minecraft:bone_block", 3, 8, 16), ("minecraft:quartz", 3, 8, 16),
                     ("minecraft:gold_ingot", 2, 4, 8), ("minecraft:string", 2, 6, 12)], rolls=3),
        K.loot_pool([("minecraft:diamond", 1, 2, 4)]),
    ])
    out.structures[arena.NAME] = arena.build()
    out.lang = {
        "entity.abm:vesperra.name": "Vesperra, The Ivory Succession",
        "entity.abm:vesperra_heir.name": "Heir of Vesperra",
        "entity.abm:cocoon_anchor.name": "Cocoon Anchor",
        "item.abm:seal_vesperra.name": "Seal of the Ivory Succession",
        "item.abm:ivory_diadem.name": "Ivory Diadem of Succession",
        "abm.lore.vesperra": "An empress who was asked never to end. She has been obeying ever since.",
        "abm.trophy.vesperra": "The diadem is warm. Something inside it is still growing.",
        "abm.summon.ok.vesperra": "§7The hall remembers a court. §fVesperra§7 rises to hold it.",
        "abm.defeat.vesperra": "§7The succession is over. §fVesperra§7 will not be replaced.",
        "abm.arena.vesperra": "The Hall of Endless Succession",
    }
    return out
