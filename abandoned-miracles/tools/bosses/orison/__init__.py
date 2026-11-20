"""Boss 004 - Orison, The Witness of Tomorrow: everything it contributes to the packs."""
from __future__ import annotations

import json
import os

from kit import icons
from kit import molang as M
from kit import pack as K
from kit.anim import Anim, ClientEntity, Controller
from kit.molang import prop, q, sin
from . import anims, arena, fx, model

KEY = "orison"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# What tools/previews.py renders for this boss.
PREVIEW = {
    "title": "Orison, The Witness of Tomorrow",
    "phase2": "Tomorrow Has Already Happened",
    "base": ["idle", "walk", "turn", "pendulum_swing"],
    "base_p2": ["p2_pose", "p2_flutter"],
    "hidden": ["hourglass_broken_glass", "halo", "halo_glow", "halo_hand_glow", "halo_hour_glow"],
    "hidden_p2": ["hourglass_glass"],
    "pad": 18,
    "actions": [
        (["echo_p1"], 0.6, 1, "01 Footstep Echo - reading the trail"),
        (["echo_p1"], 2.3, 1, "01 Footstep Echo - the gavel counts"),
        (["verdict_p1_a"], 1.75, 1, "02 Pendulum Verdict - drawn back"),
        (["verdict_p1_a"], 2.2, 1, "02 Pendulum Verdict - mid sweep"),
        (["wound_p1"], 0.6, 1, "03 Deferred Wound - setting a mark"),
        (["drain_p1"], 1.25, 1, "04 Hourglass Drain - cast"),
        (["witness_p1"], 1.5, 1, "05 Tomorrow's Witness - locked"),
        (["witness_p1"], 2.22, 1, "05 Tomorrow's Witness - verdict"),
        (["exchange_p1"], 2.19, 1, "06 Secondhand Exchange - displaced"),
        (["hour_p1"], 1.2, 1, "07 The Hour That Never Occurred"),
        (["stagger"], 0.6, 1, "stagger - the mechanism jams"),
        (["death"], 9.2, 2, "death - final pose"),
    ],
    "gifs": [
        ("walk", [], 0.0, 4.0, 1, 1.5),
        ("transition", ["transition"], 0.0, 6.8, 1, 0.0),
        ("pendulum_verdict", ["verdict_p1_a"], 0.0, 4.1, 1, 0.0),
        ("death", ["death"], 0.0, 9.2, 2, 0.0),
    ],
}


def timings() -> dict:
    with open(os.path.join(ROOT, "shared", f"{KEY}.timings.json"), encoding="utf-8") as f:
        return json.load(f)


def _helpers():
    """The shadow manifestation and the Drain hourglass: small rigs with their own motion."""
    lt = q("life_time")
    layered = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "glass": "entity_alphablend"}

    S = "animation.abm.orison_shadow."
    sh = ClientEntity("abm:orison_shadow", "geometry.abm.orison_shadow", "textures/entity/abm/orison_shadow")
    sh.materials = dict(layered)
    sh.render_controllers = ["controller.render.abm.layered"]
    idle = Anim(S + "idle", loop=True)
    idle.set("stem_glass", "scale", [1 + sin(lt * 210) * 0.07, 1 + sin(lt * 130) * 0.02, 1])
    idle.rot("stem_glass", 0, 0, sin(lt * 70) * 3)
    idle.set("ring_glow", "rot", [0, 0, sin(lt * 150) * 22])                 # the ring keeps a pendulum's time
    idle.set("ring_glow", "pos", [0, sin(lt * 120) * 1.5, 0])
    idle.set("pool_glass", "scale", [1 + sin(lt * 90) * 0.08, 1, 1 + sin(lt * 90 + 90) * 0.08])
    for side, tag in ((1, "l"), (-1, "r")):
        idle.rot(f"sarm_{tag}_glass", sin(lt * 80 + 40 * side) * 6, 0, sin(lt * 55) * 4 * side)
        idle.rot(f"sarm_{tag}_b_glass", sin(lt * 80 + 40 * side - 60) * 9, 0, 0)
    rise = Anim(S + "rise", length=0.5)
    rise.track("stem_glass", "scale", [(0, [1.6, 0.02, 1]), (0.38, [0.85, 1.12, 1], "out"), (0.5, [1, 1, 1], "inout")])
    rise.track("pool_glass", "scale", [(0, [0.2, 1, 0.2]), (0.3, [1.15, 1, 1.15], "out"), (0.5, [1, 1, 1], "inout")])
    point = Anim(S + "point", length=0.4, loop="hold")
    point.track("sarm_l_glass", "rot", [(0, [0, 0, 0]), (0.25, [-96, 0, 16], "snap")])
    point.track("sarm_l_b_glass", "rot", [(0, [0, 0, 0]), (0.25, [24, 0, 0], "snap")])
    point.track("stem_glass", "rot", [(0, [0, 0, 0]), (0.25, [8, 0, 0], "out")])
    strike = Anim(S + "strike", length=0.6, loop="hold")
    for side, tag in ((1, "l"), (-1, "r")):
        strike.track(f"sarm_{tag}_glass", "rot", [(0, [0, 0, 0]), (0.28, [-150, 0, 20 * side], "out"), (0.4, [-30, 0, 6 * side], "snap")])
        strike.track(f"sarm_{tag}_b_glass", "rot", [(0, [0, 0, 0]), (0.28, [30, 0, 0], "out"), (0.4, [20, 0, 0], "snap")])
    strike.track("stem_glass", "rot", [(0, [0, 0, 0]), (0.28, [-12, 0, 0], "out"), (0.4, [22, 0, 0], "snap")])
    strike.sound(0.36, "strike")
    sink = Anim(S + "sink", length=0.4, loop="hold")
    sink.track("stem_glass", "scale", [(0, [1, 1, 1]), (0.4, [1.5, 0.02, 1], "in")])
    sink.track("pool_glass", "scale", [(0, [1, 1, 1]), (0.4, [0.3, 1, 0.3], "in")])
    anim_p = prop("abm:anim")
    sc = Controller("controller.animation.abm.orison_shadow", "rise")
    sc.state("rise", ["rise"], [("idle", q("all_animations_finished"))], blend=0.05)
    sc.state("idle", [], [("strike", anim_p.eq(1)), ("point", anim_p.eq(2)), ("sink", anim_p.eq(3))], blend=0.1)
    sc.state("strike", ["strike"], [("idle", anim_p.ne(1))], blend=0.12)
    sc.state("point", ["point"], [("idle", anim_p.ne(2))], blend=0.12)
    sc.state("sink", ["sink"], [("idle", anim_p.ne(3))], blend=0.1)
    for a in (idle, rise, point, strike, sink):
        sh.animations[a.name[len(S):]] = a.name
    sh.animations["ctl"] = sc.name
    sh.animate = ["idle", "ctl"]
    sh.sound_effects = {"strike": "abm.orison.shadow_strike"}

    H = "animation.abm.orison_hourglass."
    hg = ClientEntity("abm:orison_hourglass", "geometry.abm.orison_hourglass", "textures/entity/abm/orison_hourglass")
    hg.materials = dict(layered)
    hg.render_controllers = ["controller.render.abm.layered"]
    run = Anim(H + "run", loop=True)
    level = M.clamp(lt / 14.0, 0, 1)
    run.set("sand_top", "scale", [1, M.mmax(0.03, 1 - level), 1])
    run.set("sand_bottom", "scale", [1, M.mmax(0.03, level), 1])
    run.set("stream_glow", "scale", [1 + sin(lt * 700) * 0.3, 1, 1 + sin(lt * 700) * 0.3])
    grow = Anim(H + "grow", length=0.5)
    grow.track("root", "scale", [(0, [0.1, 0.1, 0.1]), (0.35, [1.15, 1.15, 1.15], "out"), (0.5, [1, 1, 1], "inout")])
    pulse = Anim(H + "pulse", length=0.5, loop="hold")
    pulse.track("frame", "scale", [(0, [1, 1, 1]), (0.12, [1.25, 0.9, 1.25], "out"), (0.5, [1, 1, 1], "bounce")])
    hc = Controller("controller.animation.abm.orison_hourglass", "idle")
    hc.state("idle", [], [("pulse", anim_p.eq(1))], blend=0.05)
    hc.state("pulse", ["pulse"], [("idle", anim_p.ne(1))], blend=0.05)
    for a in (run, grow, pulse):
        hg.animations[a.name[len(H):]] = a.name
    hg.animations["ctl"] = hc.name
    hg.animate = ["run", "grow", "ctl"]
    return [sh, hg], [idle, rise, point, strike, sink, run, grow, pulse], [sc, hc]


def assets() -> K.BossAssets:
    T = timings()
    out = K.BossAssets(KEY)
    out.models = {"orison": model.build(), "orison_shadow": model.build_shadow(), "orison_hourglass": model.build_hourglass()}

    anim_list, ctrls, ce = anims.build_all(T)
    ce.particle_effects = fx.client_particles()
    snd = fx.sounds()
    ce.sound_effects = {k: f"abm.orison.{k}" for k in snd}
    helper_ce, helper_anims, helper_ctrls = _helpers()
    out.client_entities = [ce] + helper_ce
    out.animations = anim_list + helper_anims
    # models face the yaw the script publishes (abm:yaw), not whatever the engine does with the body
    from kit.anim import add_facing
    for _ce in out.client_entities:
        if _ce.identifier in ('abm:orison', 'abm:orison_shadow'):
            out.animations.append(add_facing(_ce, "animation." + _ce.identifier.replace(":", ".") + "."))
    out.controllers = ctrls + helper_ctrls

    glass = "q.property('abm:glass')"
    out.render_controllers["controller.render.abm.orison"] = K.render_controller(
        materials=K.layered_materials(),
        part_visibility=[{"*": True}, {"hourglass_glass": f"{glass} == 0"}, {"hourglass_broken_glass": f"{glass} == 1"}]
        + [{b: f"{glass} == 1"} for b in model.HALO_BONES])      # the dial of unlived hours exists only after the burst

    out.bp_entities["orison"] = K.boss_entity(
        "abm:orison", "abm_orison", 600, 1.8, 6.4, 3.2, 8.2, "loot_tables/abm/orison.json",
        {"abm:glass": K.int_prop(0, 1)})
    out.bp_entities["orison_hourglass"] = K.helper_entity("abm:orison_hourglass", "abm_hourglass", 16, 1.0, 2.3, 40)
    out.bp_entities["orison_shadow"] = K.helper_entity("abm:orison_shadow", "abm_shadow", 20, 0.8, 2.6, 1500,
                                                       damageable=False, gravity=False)

    out.particles = fx.particles()
    out.textures["textures/particle/abm/orison"] = fx.sprite_sheet()
    out.sounds = {f"abm.orison.{k}": v for k, v in snd.items()}

    out.item_icons["abm_seal_orison"] = icons.seal(
        ["########", ".######.", "..####..", "...##...", "...##...", "..#..#..", ".#.##.#.", "########"],
        "#9ca2ae", "#17203a", "#0e1426", "#243052", "#dfe9ff")
    out.item_icons["abm_unlived_hourglass"] = icons.icon([
        "................",
        "...gggggggggg...",
        "...gssssssssg...",
        "....pwwwwwwp....",
        "....pwyyyywp....",
        ".....pyyyyp.....",
        "......pyyp......",
        ".......pp.......",
        ".......pb.......",
        "......p.bp......",
        ".....p..b.p.....",
        "....p...b..p....",
        "....p......p....",
        "...gssssssssg...",
        "...gggggggggg...",
        "................",
    ], {"g": "#a39462", "s": "#6b717d", "p": "#b9c9e6", "w": "#e8f0ff", "y": "#d2c593", "b": "#8fa6d8"})
    out.items["seal_orison"] = K.item("abm:seal_orison", "abm_seal_orison", stack=1, rarity="rare")
    out.items["unlived_hourglass"] = K.item("abm:unlived_hourglass", "abm_unlived_hourglass", stack=1, glint=True,
                                            rarity="epic", cooldown=("abm_trophy", 3.0))
    out.recipes["seal_orison"] = K.shaped_recipe(
        "abm:seal_orison", ["GCG", "CSC", "GCG"],
        {"G": "minecraft:glass", "C": "minecraft:clock", "S": "minecraft:soul_sand"},
        "abm:seal_orison", ["minecraft:clock"])
    out.loot["orison"] = K.loot_table([
        K.loot_pool([("abm:unlived_hourglass", 1, 1, 1)]),
        K.loot_pool([("minecraft:clock", 2, 1, 2), ("minecraft:gold_ingot", 3, 6, 12),
                     ("minecraft:iron_ingot", 3, 8, 16), ("minecraft:amethyst_shard", 2, 4, 8)], rolls=3),
        K.loot_pool([("minecraft:diamond", 1, 2, 4)]),
    ])
    out.structures[arena.NAME] = arena.build()
    out.lang = {
        "entity.abm:orison.name": "Orison, The Witness of Tomorrow",
        "entity.abm:orison_hourglass.name": "Hourglass of Orison",
        "entity.abm:orison_shadow.name": "Shadow of Tomorrow",
        "item.abm:seal_orison.name": "Seal of the Unlived Hour",
        "item.abm:unlived_hourglass.name": "Hourglass of the Unlived Future",
        "abm.lore.orison": "It was built to see every death coming, and it did. It has been passing sentence in advance ever since.",
        "abm.trophy.orison": "The sand has stopped halfway. Whatever it was counting towards has been let off.",
        "abm.summon.ok.orison": "§7The court is in session before anyone has done anything. §fOrison§7 already knows the verdict.",
        "abm.defeat.orison": "§7For once, something happened that §fOrison§7 did not see.",
        "abm.arena.orison": "The Court of Unlived Hours",
    }
    return out
