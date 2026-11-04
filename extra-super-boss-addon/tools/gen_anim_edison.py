#!/usr/bin/env python3
"""
Edison animations + controllers + client entities (Edison, Dynamo, Electric Chair, Volt Bulb).

  RP animations/edison.animation.json, edison_props.animation.json
  RP animation_controllers/edison.animation_controllers.json
  RP entity/edison.entity.json, dynamo.entity.json, electric_chair.entity.json, volt_bulb.entity.json

Same authoring model and rotation convention as gen_animations.py (poses on a timeline, catmull-rom).
Lengths and hit moments come from tools/spec.py (EDISON_ACTIONS).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec  # noqa: E402
from gen_animations import merge, r, timeline, write  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "extra_super_boss")
P = "animation.esb.edison."
BAL = json.load(open(os.path.join(ROOT, "balance.json")))
RENDER_SCALE = BAL["edison"]["render_scale"]
M = {k: v["moments"] for k, v in spec.EDISON_ACTIONS.items()}
L = {k: v["length"] for k, v in spec.EDISON_ACTIONS.items()}

ANIMS = {}


def add(name, length, bones, loop=False, hold=False, particles=None, time_update=None):
    a = {"animation_length": length, "bones": bones}
    if loop:
        a["loop"] = True
    elif hold:
        a["loop"] = "hold_on_last_frame"
    if particles:
        a["particle_effects"] = {f"{r(t, 4)}": v for t, v in particles}
    if time_update:
        a["anim_time_update"] = time_update
    ANIMS[P + name] = a


def fist_l():
    return {"hand_l": (0, 0, 0)}


BULB_GONE = {"scale:bulb_l": (0, 0, 0)}
BULB_BACK = {"scale:bulb_l": (1, 1, 1)}

# sitting on the Dynamo in the reference pose: right leg over the edge, left knee up, bulb raised
SIT = {
    "pos:root": (0, -15.3, 0),
    "leg_r": (-90, 0, 4), "shin_r": (84, 0, 0), "foot_r": (-10, 0, 0),
    "leg_l": (-138, 0, -10), "shin_l": (140, 0, 0), "foot_l": (-20, 0, 0),
    "apron_l": (-120, 0, 0), "apron_r": (-80, 0, 0),
    "torso": (6, 10, 0), "head": (-30, 16, 0),
    "arm_l": (-168, 6, -14), "forearm_l": (-18, 0, 0),
    "arm_r": (-58, -34, 8), "forearm_r": (-62, 0, 0), "hand_r": (0, 0, 20),
}
CROUCH = {"pos:root": (0, -2.6, 0), "leg_l": (-48, 0, -6), "shin_l": (64, 0, 0), "foot_l": (-16, 0, 0),
          "leg_r": (-30, 0, 6), "shin_r": (70, 0, 0), "foot_r": (-30, 0, 0), "torso": (24, 0, 0), "head": (-16, 0, 0),
          "apron_l": (-36, 0, 0), "apron_r": (-24, 0, 0), "arm_r": (-30, 0, 20), "arm_l": (-20, 0, -26)}
KNEEL = {"pos:root": (0, -7.4, 0), "leg_l": (-85, 0, -6), "shin_l": (88, 0, 0), "foot_l": (-4, 0, 0),
         "leg_r": (8, 0, 4), "shin_r": (84, 0, 0), "foot_r": (-40, 0, 0), "torso": (16, 0, 0), "head": (20, 0, 0),
         "apron_l": (-70, 0, 0), "apron_r": (-10, 0, 0)}


def base_layers():
    t = "q.anim_time"
    bones = {  # light on his feet: a slight ready crouch, weight shifting, the bulb bobbing
        "body": {"position": [f"math.sin({t} * 150) * 0.25", f"-0.5 + math.sin({t} * 300) * 0.15", 0]},
        "torso": {"rotation": [f"5 + math.sin({t} * 300) * 1.2", f"math.sin({t} * 150) * 3", 0]},
        "head": {"rotation": [f"math.sin({t} * 300 - 40) * -1.5", f"math.sin({t} * 150 + 60) * 5", 0]},
        "arm_r": {"rotation": [f"-14 + math.sin({t} * 300) * 2", 0, f"6 + math.sin({t} * 300) * 1.5"]},
        "forearm_r": {"rotation": [-24, 0, 0]},
        "shiv": {"rotation": [0, f"math.sin({t} * 150) * 14", 0]},
        "arm_l": {"rotation": [f"-6 + math.sin({t} * 300 + 60) * 2", 0, f"-8 - math.sin({t} * 300) * 1.5"]},
        "forearm_l": {"rotation": [-14, 0, 0]},
        "bulb_l": {"position": [0, f"math.max(0, math.sin({t} * 300)) * 0.6", 0]},
        "leg_l": {"rotation": [-8, 0, -3]},
        "shin_l": {"rotation": [12, 0, 0]},
        "leg_r": {"rotation": [6, 0, 3]},
        "shin_r": {"rotation": [10, 0, 0]},
        "foot_r": {"rotation": [-6, 0, 0]},
    }
    add("idle", 2.4, bones, loop=True)
    ph = "q.modified_distance_moved * 27.0"
    amp = "math.min(q.modified_move_speed, 1.0)"
    bones = {
        "leg_l": {"rotation": [f"math.cos({ph}) * 36 * {amp}", 0, 0]},
        "leg_r": {"rotation": [f"math.cos({ph}) * -36 * {amp}", 0, 0]},
        "shin_l": {"rotation": [f"math.max(0, math.sin({ph})) * 46 * {amp}", 0, 0]},
        "shin_r": {"rotation": [f"math.max(0, -math.sin({ph})) * 46 * {amp}", 0, 0]},
        "foot_l": {"rotation": [f"math.cos({ph} + 60) * -12 * {amp}", 0, 0]},
        "foot_r": {"rotation": [f"math.cos({ph} + 60) * 12 * {amp}", 0, 0]},
        "arm_r": {"rotation": [f"math.cos({ph}) * 26 * {amp}", 0, 0]},
        "arm_l": {"rotation": [f"math.cos({ph}) * -26 * {amp}", 0, 0]},
        "torso": {"rotation": [f"10 * {amp}", f"math.cos({ph}) * 7 * {amp}", 0]},
        "body": {"position": [0, f"(math.abs(math.cos({ph})) * 0.9 - 0.7) * {amp}", 0]},
        "apron_l": {"rotation": [f"math.min(0, math.cos({ph})) * 30 * {amp}", 0, 0]},
        "apron_r": {"rotation": [f"math.min(0, -math.cos({ph})) * 30 * {amp}", 0, 0]},
    }
    add("walk", 1.0, bones, loop=True)
    add("look", 1.0, {"head": {"rotation": ["math.clamp(q.target_x_rotation, -35, 35)",
                                            "math.clamp(q.target_y_rotation, -60, 60)", 0]}}, loop=True)


def actions():
    # ---- shank: quick lunge with the broken bulb (vanilla delayed attack drives it)
    wind = {"torso": (6, -24, 0), "arm_r": (24, 0, 18), "forearm_r": (-40, 0, 0), "pos:body": (0, -0.8, 0.6),
            "leg_l": (-14, 0, 0), "leg_r": (10, 0, 0)}
    thrust = {"torso": (16, 26, 0), "head": (6, -18, 0), "arm_r": (-92, 18, 0), "forearm_r": (-4, 0, 0),
              "pos:body": (0, -1.4, -1.6), "leg_l": (-34, 0, -4), "shin_l": (24, 0, 0), "leg_r": (22, 0, 4),
              "shin_r": (18, 0, 0), "apron_l": (-26, 0, 0)}
    add("shank", spec.SHANK["length"], timeline([(0, {}), (0.14, wind), (0.3, thrust), (0.42, thrust), (0.6, {})]),
        time_update="q.anim_time + q.delta_time * (q.property('esb:phase') == 2 ? 1.2 : 1.0)",
        particles=[(0.3, {"effect": "spark", "locator": "loc_shiv"})])

    # ---- bulb toss: three side-arm knife throws with the left hand, a fresh bulb each time
    keys = [(0, {})]
    for name in ("throw1", "throw2", "throw3"):
        t = M["bulb_toss"][name]
        keys += [(t - 0.18, merge({"torso": (0, -28, 0), "head": (0, 22, 0), "arm_l": (18, -20, -48), "forearm_l": (-50, 0, 0),
                                    "leg_l": (-16, 0, -6), "leg_r": (12, 0, 6)}, BULB_BACK)),
                 (t, merge({"torso": (8, 24, 0), "head": (0, -18, 0), "arm_l": (-82, 34, -6), "forearm_l": (-6, 0, 0),
                            "leg_l": (-24, 0, -6), "leg_r": (16, 0, 6)}, BULB_BACK)),
                 (t + 0.04, merge({"torso": (8, 24, 0), "head": (0, -18, 0), "arm_l": (-70, 40, -4), "forearm_l": (-10, 0, 0),
                                   "leg_l": (-24, 0, -6), "leg_r": (16, 0, 6)}, BULB_GONE))]
    keys += [(1.45, merge({"arm_l": (-20, 0, -14)}, BULB_GONE)), (L["bulb_toss"], BULB_BACK)]
    add("bulb_toss", L["bulb_toss"], timeline(keys))

    # ---- vanish: crushes the bulb in his fist (blackout), drops into a crouch and fades
    m = M["vanish"]
    show = merge({"arm_l": (-100, -26, 0), "forearm_l": (-46, 0, 0), "head": (6, 14, 0), "torso": (4, 10, 0)}, BULB_BACK)
    crush = merge(show, {"hand_l": (0, 0, 30), "forearm_l": (-58, 0, 0)}, BULB_GONE)
    low = merge(CROUCH, {"arm_l": (-10, 0, -40), "arm_r": (10, 0, 40)}, BULB_GONE)
    add("vanish", L["vanish"], timeline([(0, BULB_BACK), (0.25, show), (m["crush"], crush), (m["fade"], low), (L["vanish"], low)]),
        hold=True, particles=[(m["crush"], {"effect": "glass", "locator": "loc_bulb"})])

    # ---- backstab: rises out of the crouch with an upward thrust, a new bulb appears afterwards
    m = M["backstab"]
    rise = merge({"torso": (28, 18, 0), "head": (-14, -14, 0), "arm_r": (-128, 22, 0), "forearm_r": (-10, 0, 0),
                  "leg_l": (-40, 0, -6), "shin_l": (40, 0, 0), "leg_r": (16, 0, 6), "shin_r": (30, 0, 0),
                  "pos:root": (0, -1.0, -0.8)}, BULB_GONE)
    add("backstab", L["backstab"], timeline([(0, merge(CROUCH, BULB_GONE)), (m["stab"], rise), (0.45, merge(rise, {"shiv": (0, 0, 40)})),
                                              (0.7, merge({}, BULB_GONE)), (L["backstab"], BULB_BACK)]),
        particles=[(m["stab"], {"effect": "spark", "locator": "loc_shiv"})])

    # ---- overload: grabs the Dynamo lever, wrenches it down, throws his arms up as the current flows
    m = M["overload"]
    grab = {"torso": (18, 0, 0), "arm_r": (-82, 6, 0), "arm_l": (-82, -6, 0), "forearm_r": (-10, 0, 0), "forearm_l": (-10, 0, 0)}
    pull = {"torso": (-12, 0, 0), "head": (-8, 0, 0), "arm_r": (-24, 6, 0), "arm_l": (-24, -6, 0), "pos:body": (0, -1.6, 1.0),
            "leg_l": (-30, 0, -6), "shin_l": (40, 0, 0), "leg_r": (20, 0, 6), "shin_r": (34, 0, 0)}
    surge = {"torso": (-18, 0, 0), "head": (-30, 0, 0), "arm_l": (0, 0, -128), "arm_r": (0, 0, 128), "pos:root": (0, 0.6, 0)}
    add("overload", L["overload"], timeline([(0, {}), (m["grab"], grab), (0.8, merge(grab, {"torso": (24, 0, 0)})), (m["pull"], pull),
                                              (m["discharge"], surge), (2.0, surge), (L["overload"], {})]),
        particles=[(m["discharge"], {"effect": "spark", "locator": "loc_bulb"}), (m["discharge"], {"effect": "spark", "locator": "loc_shiv"})])

    # ---- chair: points the shiv at the condemned, snaps his fingers, clenches the fist to lock it
    m = M["chair"]
    point = {"arm_r": (-90, 8, 0), "forearm_r": (0, 0, 0), "torso": (0, 14, 0), "head": (0, -12, 0),
             "arm_l": (-104, -24, -18), "forearm_l": (-40, 0, 0)}
    snap = merge(point, {"hand_l": (0, 0, -30), "forearm_l": (-52, 0, 0)})
    clench = merge(point, {"arm_l": (-70, -10, -10), "forearm_l": (-80, 0, 0), "hand_l": (0, 0, 20), "torso": (8, 14, 0)})
    add("chair", L["chair"], timeline([(0, {}), (0.3, point), (m["snap"], snap), (0.75, point), (m["lock"], clench), (1.8, clench),
                                        (L["chair"], {})]),
        particles=[(m["snap"], {"effect": "spark", "locator": "loc_bulb"})])

    # ---- transform (Current War): hunched over the surge, then stands in a burst of AC light
    m = M["transform"]
    hunch = {"torso": (36, 0, 0), "head": (26, 0, 0), "arm_l": (-46, 34, 0), "arm_r": (-46, -34, 0), "forearm_l": (-60, 0, 0),
             "forearm_r": (-60, 0, 0), "leg_l": (-24, 0, -6), "shin_l": (36, 0, 0), "leg_r": (14, 0, 6), "shin_r": (30, 0, 0),
             "pos:root": (0, -1.6, 0)}
    shake = merge(hunch, {"torso": (40, 6, 4), "head": (30, -8, 0)})
    burst = {"torso": (-16, 0, 0), "head": (-30, 0, 0), "arm_l": (-10, 0, -62), "arm_r": (-10, 0, 62), "pos:root": (0, 1.0, 0),
             "leg_l": (0, 0, -10), "leg_r": (0, 0, 10)}
    add("transform", L["transform"], timeline([(0, {}), (0.5, hunch), (0.8, shake), (1.1, hunch), (1.4, shake), (1.7, {"torso": (10, 0, 0)}),
                                                (m["burst"], burst), (2.8, burst), (L["transform"], {})]),
        particles=[(m["burst"], {"effect": "spark", "locator": "loc_chest_e"})])

    # ---- stunned (the Dynamo was destroyed): staggers to one knee, head swimming
    daze = merge(KNEEL, {"arm_l": (-10, 0, -20), "arm_r": (-10, 0, 20), "head": (24, 0, 10)})
    add("stunned", L["stunned"], timeline([(0, {}), (0.3, {"torso": (-20, 0, 0), "head": (-16, 0, 0), "pos:body": (0, 0, 1.0)}),
                                            (0.8, daze), (1.4, merge(daze, {"head": (20, 0, -12)})), (2.0, merge(daze, {"head": (24, 0, 12)})),
                                            (2.5, daze), (L["stunned"], {})]),
        particles=[(0.8, {"effect": "spark", "locator": "loc_head_e"}), (1.8, {"effect": "spark", "locator": "loc_head_e"})])

    # ---- flourish: tosses the bulb, watches it spin, catches it; twirls the shiv
    m = M["flourish"]
    up = {"arm_l": (-120, 0, -10), "forearm_l": (-10, 0, 0), "head": (-30, 0, 0)}
    keys = [(0, {}), (0.4, merge({"arm_l": (-60, 0, -10)})), (0.55, merge(up, {"pos:bulb_l": (0, 4, 0)})),
            (0.9, merge(up, {"pos:bulb_l": (0, 13, 0), "bulb_l": (0, 0, 360), "head": (-40, 0, 0)})),
            (m["catch"], merge(up, {"pos:bulb_l": (0, 0, 0), "bulb_l": (0, 0, 720)})),
            (1.5, {"arm_l": (-40, 0, -10), "bulb_l": (0, 0, 720)}), (1.6, {"arm_r": (-50, 0, 0), "bulb_l": (0, 0, 720)}),
            (2.0, {"arm_r": (-50, 0, 0), "shiv": (0, 360, 0), "bulb_l": (0, 0, 720)}), (L["flourish"], {"bulb_l": (0, 0, 720), "shiv": (0, 360, 0)})]
    add("flourish", L["flourish"], timeline(keys))

    # ---- intro: sitting on the Dynamo in the reference pose, then hops down into his stance
    m = M["intro"]
    lit = merge(SIT, {"head": (-34, 22, 0)})
    stand_top = merge(CROUCH, {"pos:root": (0, -2.0, 0)})
    jump = {"torso": (10, 0, 0), "leg_l": (-60, 0, -6), "shin_l": (80, 0, 0), "leg_r": (-40, 0, 6), "shin_r": (90, 0, 0),
            "arm_l": (-30, 0, -50), "arm_r": (-30, 0, 50)}
    keys = [(0, SIT), (m["light"], lit), (1.8, merge(SIT, {"head": (-20, -6, 0)})), (2.4, lit), (2.85, stand_top),
            (m["hop"], jump), (m["land"], merge(CROUCH, {"pos:root": (0, -3.2, 0)})), (3.9, {"head": (0, -10, 0)}),
            (L["intro"], {})]
    add("intro", L["intro"], timeline(keys), particles=[(m["light"], {"effect": "spark", "locator": "loc_bulb"})])

    # ---- death: staggers, falls to his knees, the bulb flickers out, slumps
    m = M["death"]
    hit = {"torso": (-20, -8, 0), "head": (-18, 0, 0), "pos:body": (0, 0, 1.0), "arm_r": (-10, 0, 30), "arm_l": (-10, 0, -30)}
    kneel = merge(KNEEL, {"arm_l": (-50, 0, -10), "forearm_l": (-40, 0, 0), "head": (10, 0, 0)})
    keys = [(0, {}), (0.3, hit), (m["kneel"], merge(kneel, {"scale:bulb_l": (1, 1, 1)})),
            (1.6, merge(kneel, {"scale:bulb_l": (0.7, 0.7, 0.7)})), (1.8, merge(kneel, {"scale:bulb_l": (1, 1, 1)})),
            (2.3, merge(kneel, {"scale:bulb_l": (0.5, 0.5, 0.5)})), (2.6, merge(kneel, {"scale:bulb_l": (0.9, 0.9, 0.9)})),
            (m["fade"], merge(KNEEL, {"torso": (42, 0, 0), "head": (34, 0, 0), "arm_l": (14, 0, -6), "arm_r": (14, 0, 6),
                                      "scale:bulb_l": (0, 0, 0)})),
            (L["death"], merge(KNEEL, {"torso": (44, 0, 0), "head": (36, 0, 0), "arm_l": (14, 0, -6), "arm_r": (14, 0, 6),
                                       "scale:bulb_l": (0, 0, 0)}))]
    add("death", L["death"], timeline(keys), hold=True, particles=[(m["fade"], {"effect": "glass", "locator": "loc_bulb"})])


def props():
    bulbs = [f"bulb_{i}" for i in range(1, 6)]
    idle = {b: {"scale": f"1 + math.sin(q.life_time * 840 + {i * 70}) * 0.04"} for i, b in enumerate(bulbs)}
    idle.update({f"lever_{i}": {"rotation": [0, 0, 0]} for i in (1, 2, 3)})
    charge = {b: {"scale": f"1.18 + math.sin(q.life_time * 2400 + {i * 50}) * 0.12"} for i, b in enumerate(bulbs)}
    charge.update({f"lever_{i}": {"rotation": [f"-60 + math.sin(q.life_time * 3000 + {i * 90}) * 4", 0, 0]} for i in (1, 2, 3)})
    out = {
        "animation.esb.dynamo.idle": {"loop": True, "animation_length": 1.0, "bones": idle},
        "animation.esb.dynamo.charge": {"loop": True, "animation_length": 0.5, "bones": charge,
                                        "particle_effects": {"0.0": {"effect": "zap", "locator": "loc_coil"},
                                                             "0.25": {"effect": "zap", "locator": "loc_top"}}},
        "animation.esb.electric_chair.armed": {"loop": True, "animation_length": 0.5, "bones": {
            "root": {"scale": "math.min(1, 0.2 + q.life_time * 3.2)"},
            "helmet": {"position": [0, 3, 0]},
            "straps": {"scale": 0.0001}},
            "particle_effects": {"0.0": {"effect": "zap", "locator": "loc_helmet"}}},
        "animation.esb.electric_chair.locked": {"loop": True, "animation_length": 0.2, "bones": {
            "helmet": {"position": ["math.sin(q.life_time * 7200) * 0.2", "math.sin(q.life_time * 5400) * 0.3", 0]},
            "frame": {"rotation": [0, "math.sin(q.life_time * 6000) * 1.2", 0]}},
            "particle_effects": {"0.0": {"effect": "zap", "locator": "loc_helmet"}, "0.1": {"effect": "zap", "locator": "loc_seat"}}},
        "animation.esb.volt_bulb.spin": {"loop": True, "animation_length": 0.25, "bones": {
            "spin": {"rotation": ["q.life_time * 1080", "q.life_time * 400", 0]}},
            "particle_effects": {"0.0": {"effect": "trail", "locator": "loc_bulb_p"}}},
    }
    return out


def act(a):
    return f"q.property('esb:action') == '{a}'"


def controllers():
    C = {}
    states = {"default": {"transitions": [{a: act(a)} for a in spec.EDISON_ACTIONS]}}
    for a in spec.EDISON_ACTIONS:
        states[a] = {"animations": [a], "transitions": [{"default": f"q.property('esb:action') != '{a}'"}],
                     "blend_transition": 0.15, "blend_via_shortest_path": True}
    # vanish flows straight into the backstab
    states["vanish"]["transitions"] = [{"backstab": act("backstab")}, {"default": "!(" + act("vanish") + " || " + act("backstab") + ")"}]
    C["controller.animation.esb.edison.action"] = {"initial_state": "default", "states": states}
    C["controller.animation.esb.edison.attack"] = {"initial_state": "default", "states": {
        "default": {"transitions": [{"shank": "q.is_delayed_attacking && " + act("none")}]},
        "shank": {"animations": ["shank"], "blend_transition": 0.08,
                  "transitions": [{"default": "q.all_animations_finished || !" + act("none")}]},
    }}
    C["controller.animation.esb.dynamo.mode"] = {"initial_state": "idle", "states": {
        "idle": {"animations": ["idle"], "transitions": [{"charge": "q.property('esb:mode') == 'charging'"}]},
        "charge": {"animations": ["charge"], "blend_transition": 0.15, "transitions": [{"idle": "q.property('esb:mode') != 'charging'"}]},
    }}
    C["controller.animation.esb.electric_chair.state"] = {"initial_state": "armed", "states": {
        "armed": {"animations": ["armed"], "transitions": [{"locked": "q.property('esb:state') == 'locked'"}]},
        "locked": {"animations": ["locked"], "blend_transition": 0.1, "transitions": [{"armed": "q.property('esb:state') != 'locked'"}]},
    }}
    write(os.path.join(RP, "animation_controllers", "edison.animation_controllers.json"), {"format_version": "1.10.0", "animation_controllers": C})


def client_entities():
    names = {k[len(P):]: k for k in ANIMS}
    names.update({"action_controller": "controller.animation.esb.edison.action",
                  "attack_controller": "controller.animation.esb.edison.attack"})
    busy = " || ".join(act(a) for a in ("death", "intro", "transform", "stunned"))
    write(os.path.join(RP, "entity", "edison.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": spec.EDISON_ID,
        "materials": {"default": "entity_emissive"},
        "textures": {"default": "textures/entity/edison", "charged": "textures/entity/edison_charged"},
        "geometry": {"default": "geometry.esb.edison"},
        "render_controllers": ["controller.render.esb.edison"],
        "spawn_egg": {"base_color": "#5D6A44", "overlay_color": "#FFD27A"},
        "enable_attachables": False,
        "scripts": {"scale": str(RENDER_SCALE), "animate": ["idle", {"walk": "!" + act("intro")}, {"look": f"!({busy})"},
                                                            "attack_controller", "action_controller"],
                    "should_update_bones_and_effects_offscreen": "1.0"},
        "animations": dict(sorted(names.items())),
        "particle_effects": {"spark": "esb:volt_spark", "glass": "esb:glass_shards"},
    }}})
    write(os.path.join(RP, "entity", "dynamo.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": spec.DYNAMO_ID,
        "materials": {"default": "entity_emissive"},
        "textures": {"default": "textures/entity/dynamo", "charged": "textures/entity/dynamo_charged"},
        "geometry": {"default": "geometry.esb.dynamo"},
        "render_controllers": ["controller.render.esb.dynamo"],
        "animations": {"idle": "animation.esb.dynamo.idle", "charge": "animation.esb.dynamo.charge",
                       "mode_controller": "controller.animation.esb.dynamo.mode"},
        "particle_effects": {"zap": "esb:volt_spark"},
        "scripts": {"animate": ["mode_controller"]},
    }}})
    write(os.path.join(RP, "entity", "electric_chair.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": spec.CHAIR_ID,
        "materials": {"default": "entity_emissive"},
        "textures": {"default": "textures/entity/electric_chair"},
        "geometry": {"default": "geometry.esb.electric_chair"},
        "render_controllers": ["controller.render.esb.electric_chair"],
        "animations": {"armed": "animation.esb.electric_chair.armed", "locked": "animation.esb.electric_chair.locked",
                       "state_controller": "controller.animation.esb.electric_chair.state"},
        "particle_effects": {"zap": "esb:volt_spark"},
        "scripts": {"animate": ["state_controller"]},
    }}})
    write(os.path.join(RP, "entity", "volt_bulb.entity.json"), {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": spec.VOLT_BULB_ID,
        "materials": {"default": "entity_emissive"},
        "textures": {"default": "textures/entity/volt_bulb"},
        "geometry": {"default": "geometry.esb.volt_bulb"},
        "render_controllers": ["controller.render.esb.volt_bulb"],
        "animations": {"spin": "animation.esb.volt_bulb.spin"},
        "particle_effects": {"trail": "esb:volt_spark"},
        "scripts": {"animate": ["spin"]},
    }}})


def main():
    base_layers()
    actions()
    write(os.path.join(RP, "animations", "edison.animation.json"), {"format_version": "1.8.0", "animations": ANIMS})
    write(os.path.join(RP, "animations", "edison_props.animation.json"), {"format_version": "1.8.0", "animations": props()})
    controllers()
    client_entities()
    print(f"edison animations: {len(ANIMS)} + 5 props; controllers: 4")


if __name__ == "__main__":
    main()
