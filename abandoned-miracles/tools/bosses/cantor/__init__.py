"""Boss 002 - Cantor XIII, The Walking Requiem: everything it contributes to the packs."""
from __future__ import annotations

import json
import os

from kit import icons
from kit import pack as K
from kit.anim import Anim, ClientEntity, Controller
from kit.molang import prop, q, sin
from . import anims, arena, fx, model

KEY = "cantor"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# What tools/previews.py renders for this boss.
PREVIEW = {
    "title": "Cantor XIII, The Walking Requiem",
    "phase2": "The Broken Symphony",
    "base": ["idle", "walk", "turn"],
    "base_p2": ["p2_pose", "p2_unstable"],
    "hidden": ["bell_crack_glow"],
    "hidden_p2": ["bell_chunk"],
    "pad": 30,
    "actions": [
        (["downbeat_p1"], 0.85, 1, "01 Prime Downbeat - wind-up"),
        (["downbeat_p1"], 1.55, 1, "01 Prime Downbeat - toll"),
        (["counterpoint_p1"], 1.9, 1, "02 Counterpoint - left rank"),
        (["aria_p1"], 2.04, 1, "03 Glass Aria - volley"),
        (["held_p1"], 2.85, 1, "04 Held Note - swell"),
        (["held_p1"], 3.05, 1, "04 Held Note - blast"),
        (["silent_p1"], 2.2, 1, "05 The Silent Measure - arrested"),
        (["twin_p1"], 1.55, 1, "06 Twin Resonance - bells flung"),
        (["requiem_p1"], 4.55, 1, "07 The Final Requiem - measure 2"),
        (["stagger"], 0.5, 1, "stagger"),
        (["requiem_p2"], 6.75, 2, "Phase II - requiem"),
        (["death"], 10.9, 2, "death - final pose"),
    ],
    "gifs": [
        ("walk", [], 0.0, 4.9, 1, 1.0),
        ("transition", ["transition"], 0.0, 7.0, 1, 0.0),
        ("final_requiem", ["requiem_p1"], 0.0, 10.7, 1, 0.0),
        ("death", ["death"], 0.0, 11.0, 2, 0.0),
    ],
}


def timings() -> dict:
    with open(os.path.join(ROOT, "shared", f"{KEY}.timings.json"), encoding="utf-8") as f:
        return json.load(f)


def _bell_helper():
    """The detached secondary bell: sways idly, swings hard while it winds up a pulse."""
    lt = q("life_time")
    A = "animation.abm.cantor_bell."
    ce = ClientEntity("abm:cantor_bell", "geometry.abm.cantor_bell", "textures/entity/abm/cantor_bell")
    ce.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha"}
    ce.render_controllers = ["controller.render.abm.layered"]
    idle = Anim(A + "idle", loop=True)
    idle.rot("bell", sin(lt * 110) * 4, 0, sin(lt * 83 + 40) * 4)
    idle.rot("clapper", -sin(lt * 110 - 40) * 7, 0, -sin(lt * 83) * 7)
    idle.scale("bell_glow", 1 + sin(lt * 500) * 0.08)
    land = Anim(A + "land", length=0.6)
    land.track("root", "scale", [(0, [0.4, 0.4, 0.4]), (0.35, [1.15, 0.9, 1.15], "out"), (0.6, [1, 1, 1], "inout")])
    land.track("root", "pos", [(0, [0, 26, 0]), (0.35, [0, 0, 0], "bounce")])
    ring = Anim(A + "ring", length=1.5, loop=True)
    ring.rot("bell", sin(q("anim_time") * 720) * 24, 0, 0)
    ring.rot("clapper", -sin(q("anim_time") * 720 - 60) * 34, 0, 0)
    ring.scale("bell_glow", 1.4)
    ctl = Controller("controller.animation.abm.cantor_bell", "land")
    ctl.state("land", ["land"], [("idle", q("anim_time").ge(0.6))], blend=0.1)
    ctl.state("idle", [], [("ring", prop("abm:anim").eq(1))], blend=0.15)
    ctl.state("ring", ["ring"], [("idle", prop("abm:anim").ne(1))], blend=0.15)
    for a in (idle, land, ring):
        ce.animations[a.name[len(A):]] = a.name
    ce.animations["ctl"] = ctl.name
    ce.animate = ["idle", "ctl"]
    return ce, [idle, land, ring], [ctl]


def assets() -> K.BossAssets:
    T = timings()
    out = K.BossAssets(KEY)
    out.models = {"cantor_xiii": model.build(), "cantor_bell": model.build_bell()}

    anim_list, ctrls, ce = anims.build_all(T)
    ce.particle_effects = fx.client_particles()
    snd = fx.sounds()
    ce.sound_effects = {k: f"abm.cantor.{k}" for k in snd}
    bell_ce, bell_anims, bell_ctrls = _bell_helper()
    out.client_entities = [ce, bell_ce]
    out.animations = anim_list + bell_anims
    out.controllers = ctrls + bell_ctrls

    phase, anim, out_p = (f"q.property('abm:{n}')" for n in ("phase", "anim", "bells_out"))
    out.render_controllers["controller.render.abm.cantor"] = K.render_controller(
        materials=[{"*": "Material.default"}, {"*_glow": "Material.glow"}],
        part_visibility=[
            {"*": True},
            {"bell_chunk": f"{phase} == 1"},
            {"bell_crack_glow": f"{phase} == 2 || {anim} == 8"},
            {"bell_s1": f"{out_p} == 0"}, {"bell_s2": f"{out_p} == 0"},
        ])

    out.bp_entities["cantor_xiii"] = K.boss_entity(
        "abm:cantor_xiii", "abm_cantor", 520, 3.2, 8.2, 5.2, 9.4, "loot_tables/abm/cantor.json",
        {"abm:bells_out": K.int_prop(0, 1), "abm:silent": K.int_prop(0, 1)})
    out.bp_entities["cantor_bell"] = K.helper_entity("abm:cantor_bell", "abm_cantor_bell", 24, 1.3, 2.1, 30)

    out.particles = fx.particles()
    out.textures["textures/particle/abm/cantor"] = fx.sprite_sheet()
    out.sounds = {f"abm.cantor.{k}": v for k, v in snd.items()}

    out.item_icons["abm_seal_cantor"] = icons.seal(
        ["...##...", "...##...", "..####..", "..####..", ".######.", ".######.", "########", "...##..."],
        "#c2a04a", "#3c7d70", "#245249", "#6fb8a2", "#f0dc96")
    out.item_icons["abm_bell_fragment"] = icons.icon([
        "................",
        ".........gg.....",
        "........gbbg....",
        ".......gbbtbg...",
        "......gbbbbbg...",
        ".....gbtbbbbbg..",
        "....kbbbbbtbbg..",
        "...kbbbbbbbbbg..",
        "...kbtbbbbbbbbg.",
        "..kbbbbbbwbbbbg.",
        "..kbbbbtwwbbbtg.",
        "..kkbbbbwbbbbgg.",
        "....kkbbbbbgg...",
        "......kkbgg.....",
        "........k.......",
        "................",
    ], {"g": "#e8d07e", "b": "#86602f", "t": "#4c9482", "k": "#3a2a1c", "w": "#fff3c4"})
    out.items["seal_cantor"] = K.item("abm:seal_cantor", "abm_seal_cantor", stack=1, rarity="rare")
    out.items["bell_fragment"] = K.item("abm:bell_fragment", "abm_bell_fragment", stack=1, glint=True, rarity="epic",
                                        cooldown=("abm_trophy", 3.0))
    out.recipes["seal_cantor"] = K.shaped_recipe(
        "abm:seal_cantor", ["CGC", "GBG", "CGC"],
        {"C": "minecraft:copper_block", "G": "minecraft:gold_ingot", "B": "minecraft:bell"},
        "abm:seal_cantor", ["minecraft:bell"])
    out.loot["cantor"] = K.loot_table([
        K.loot_pool([("abm:bell_fragment", 1, 1, 1)]),
        K.loot_pool([("minecraft:copper_ingot", 3, 12, 24), ("minecraft:gold_ingot", 3, 6, 10),
                     ("minecraft:amethyst_shard", 2, 6, 12), ("minecraft:noteblock", 1, 2, 4)], rolls=3),
        K.loot_pool([("minecraft:diamond", 1, 2, 4)]),
    ])
    out.structures[arena.NAME] = arena.build()
    out.lang = {
        "entity.abm:cantor_xiii.name": "Cantor XIII, The Walking Requiem",
        "entity.abm:cantor_bell.name": "Resonant Bell",
        "item.abm:seal_cantor.name": "Seal of the Last Note",
        "item.abm:bell_fragment.name": "Fragment of the Thirteenth Bell",
        "abm.lore.cantor": "An instrument built so that a whole people could sing as one. It learned the song, and now it corrects every voice that is not its own.",
        "abm.trophy.cantor": "Hold it to your ear. It is still counting.",
        "abm.summon.ok.cantor": "§7Somewhere above you a bell draws breath. §fCantor XIII§7 begins the service.",
        "abm.defeat.cantor": "§7The last note ends. For the first time in an age, §fCantor XIII§7 is quiet.",
        "abm.arena.cantor": "The Basilica of the Last Note",
    }
    return out
