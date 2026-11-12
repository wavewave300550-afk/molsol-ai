"""Summoned mobs with real AI: the three Imperial Frost Legion knights (and the Royal Stag, see blood)."""
import math
from .modelkit import Model, geometry_file
from .anim import Anim, anim_file, controller_file
from .fxdefs import dump
from .fxparts import oriented
from .texkit import Atlas

MOBS = []

ACT_PROP = {"grimoire:act": {"type": "int", "range": [0, 7], "default": 4, "client_sync": True}}
# act: 0 normal, 1 attack, 2 special, 3 defend/guard, 4 summoning, 5 prepare (stag charge), 6 charging, 7 dissolve


class Mob:
    def __init__(self, name, tex=(128, 256), bounds=(3, 3.5, (0, 1.5, 0))):
        self.name = name
        self.ident = f"grimoire:{name}"
        self.model = Model(f"geometry.grimoire.{name}", tex[0], tex[1], bounds, atlas=Atlas(tex[0], tex[1], density=1.0))
        self.anims = {}
        self.controllers = {}
        self.animate = []
        self.bp_components = {}
        self.bp_groups = {}
        self.bp_events = {}
        self.scale = 1.0
        MOBS.append(self)

    def anim(self, short, loop=False, length=None):
        a = Anim(f"animation.grimoire.{self.name}.{short}", loop=loop, length=length)
        self.anims[short] = a
        return a

    def write(self, rp, bp):
        for a in self.anims.values():
            for bone in a.bones:
                if bone not in self.model.by_name:
                    raise ValueError(f"{self.name}: {a.ident} references missing bone {bone}")
        dump(f"{rp}/models/entity/grimoire/{self.name}.geo.json", geometry_file([self.model]))
        self.model.atlas.save(f"{rp}/textures/entity/grimoire/{self.name}.png")
        dump(f"{rp}/animations/grimoire/{self.name}.animation.json", anim_file(self.anims.values()))
        dump(f"{rp}/animation_controllers/grimoire/{self.name}.ac.json", controller_file(self.controllers))
        anims = {k: a.ident for k, a in self.anims.items()}
        for k in self.controllers:
            anims[k.split(".")[-1]] = k
        dump(f"{rp}/entity/grimoire/{self.name}.entity.json", {
            "format_version": "1.10.0",
            "minecraft:client_entity": {
                "description": {
                    "identifier": self.ident,
                    "materials": {"default": "entity_emissive_alpha", "trans": "entity_alphablend", "glow": "entity_beam_additive"},
                    "textures": {"default": f"textures/entity/grimoire/{self.name}"},
                    "geometry": {"default": self.model.ident},
                    "animations": anims,
                    "scripts": {"scale": str(self.scale), "animate": self.animate},
                    "render_controllers": ["controller.render.grimoire.fx"],
                }
            },
        })
        dump(f"{bp}/entities/grimoire/{self.name}.json", {
            "format_version": "1.26.30",
            "minecraft:entity": {
                "description": {"identifier": self.ident, "is_spawnable": False, "is_summonable": True, "properties": ACT_PROP},
                "component_groups": {"grimoire:despawn": {"minecraft:instant_despawn": {}}, **self.bp_groups},
                "components": self.bp_components,
                "events": {"grimoire:expire": {"add": {"component_groups": ["grimoire:despawn"]}}, **self.bp_events},
            },
        })

    def locomotion_controller(self, walk="walk", idle="idle"):
        self.controllers[f"controller.animation.grimoire.{self.name}.move"] = {
            "initial_state": "idle",
            "states": {
                "idle": {"animations": [idle], "transitions": [{"walk": "q.modified_move_speed > 0.08"}], "blend_transition": 0.2},
                "walk": {"animations": [walk], "transitions": [{"idle": "q.modified_move_speed <= 0.08"}], "blend_transition": 0.2},
            },
        }
        self.animate.append("move")

    def action_controller(self, acts):
        """acts: {act_value: animation short name}; act 0 = no overlay."""
        states = {"none": {"transitions": [{f"a{k}": f"q.property('grimoire:act') == {k}"} for k in acts], "blend_transition": 0.1}}
        for k, an in acts.items():
            states[f"a{k}"] = {
                "animations": [an],
                "transitions": [{"none": f"q.property('grimoire:act') != {k}"}] + [{f"a{o}": f"q.property('grimoire:act') == {o}"} for o in acts if o != k],
                "blend_transition": 0.08,
            }
        self.controllers[f"controller.animation.grimoire.{self.name}.act"] = {"initial_state": "none", "states": states}
        self.animate.append("act")


def knight_components(health, damage, speed, kb, height=2.5, width=0.8, extra_family=()):
    owner_filter = {"all_of": [{"test": "is_owner", "subject": "other", "value": False},
                               {"test": "is_family", "subject": "other", "operator": "!=", "value": "grimoire_summon"}]}
    return {
        "minecraft:type_family": {"family": ["grimoire_summon", "frost_knight", "mob", *extra_family]},
        "minecraft:health": {"value": health, "max": health},
        "minecraft:collision_box": {"width": width, "height": height},
        "minecraft:movement": {"value": speed},
        "minecraft:navigation.walk": {"can_path_over_water": True, "avoid_damage_blocks": True, "avoid_water": True},
        "minecraft:movement.basic": {},
        "minecraft:jump.static": {},
        "minecraft:can_climb": {},
        "minecraft:physics": {},
        "minecraft:pushable_by_block": {},
        "minecraft:attack": {"damage": damage},
        "minecraft:knockback_resistance": {"value": kb},
        "minecraft:damage_sensor": {"triggers": [
            {"cause": "fall", "deals_damage": "no"},
            {"cause": "freezing", "deals_damage": "no"},
            {"on_damage": {"filters": {"test": "is_owner", "subject": "other", "value": True}}, "deals_damage": "no"},
        ]},
        "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "total_supply": 15, "suffocate_time": 0},
        "minecraft:loot": {"table": "loot_tables/grimoire/empty.json"},
        "minecraft:experience_reward": {"on_death": "0"},
        "minecraft:tameable": {"probability": 0, "tame_items": "minecraft:barrier", "tame_event": {"event": "grimoire:tamed", "target": "self"}},
        "minecraft:behavior.float": {"priority": 0},
        "minecraft:behavior.melee_box_attack": {"priority": 2, "track_target": True, "speed_multiplier": 1.25},
        "minecraft:behavior.hurt_by_target": {"priority": 3, "entity_types": {"filters": owner_filter}},
        "minecraft:behavior.nearest_attackable_target": {"priority": 4, "reselect_targets": True, "must_see": False,
            "entity_types": [{"filters": {"any_of": [{"test": "is_family", "subject": "other", "value": "monster"},
                                                     {"test": "is_family", "subject": "other", "value": "dragon"},
                                                     {"test": "is_family", "subject": "other", "value": "hoglin_adult"}]}, "max_dist": 18}]},
        "minecraft:behavior.random_look_around": {"priority": 9},
        "minecraft:behavior.look_at_player": {"priority": 8, "look_distance": 8, "look_time": {"min": 1, "max": 2}},
        "minecraft:timer": {"time": 90, "looping": False, "time_down_event": {"event": "grimoire:expire", "target": "self"}},
    }


TAMED_GROUP = {"grimoire:tamed": {
    "minecraft:is_tamed": {},
    "minecraft:behavior.follow_owner": {"priority": 5, "speed_multiplier": 1.15, "start_distance": 8, "stop_distance": 3, "post_teleport_distance": -1},
    "minecraft:behavior.owner_hurt_by_target": {"priority": 1},
    "minecraft:behavior.owner_hurt_target": {"priority": 2},
}}


# ============================================================================== knight bodies
def humanoid(m, h=1.0, w=1.0, heavy=False):
    """Crystalline armored humanoid ~2.5 blocks tall. Returns joint names."""
    b = m.model
    b.bone("root", pivot=(0, 0, 0))
    b.bone("waist", "root", pivot=(0, 19 * h, 0))
    body = b.bone("body", "waist", pivot=(0, 30 * h, 0))
    cw = 12 * w
    body.cbox((0, 25 * h, 0), (cw, 12 * h, 7 * w), "i_crystal_deep")           # chest
    body.cbox((0, 26.5 * h, -3.8 * w), (cw * 0.8, 8 * h, 1.2), "i_silver")      # breastplate
    body.cbox((0, 27 * h, -4.6 * w), (2.2, 6 * h, 0.8), "i_crystal_glow")       # core crystal
    body.cbox((0, 20.5 * h, 0), (cw * 0.85, 3 * h, 6 * w), "i_silver_dark")    # belt
    body.cbox((0, 17 * h, -3.2 * w), (cw * 0.7, 6 * h, 1), "i_crystal")          # front tasset
    body.cbox((0, 17 * h, 3.2 * w), (cw * 0.7, 6 * h, 1), "i_crystal")           # back tasset
    if heavy:
        body.cbox((0, 25 * h, 0), (cw + 2, 12 * h, 8 * w), "i_crystal_deep")
    head = b.bone("head", "body", pivot=(0, 31 * h, 0))
    head.cbox((0, 36 * h, 0), (9 * w, 10 * h, 9 * w), "i_crystal")
    head.cbox((0, 36 * h, -0.4), (9.6 * w, 1.6 * h, 9.6 * w), "i_silver")
    b.bone("g_visor", "head", pivot=(0, 36 * h, 0)).cbox((0, 37 * h, -4.7 * w), (6 * w, 1.2 * h, 0.4), "i_core")
    for side, nm in ((-1, "arm_r"), (1, "arm_l")):
        ax = side * (cw / 2 + 2.2)
        arm = b.bone(nm, "body", pivot=(ax, 29 * h, 0))
        arm.cbox((ax, 23 * h, 0), (4 * w, 12 * h, 4 * w), "i_crystal_deep")
        arm.cbox((ax, 18.5 * h, 0), (4.6 * w, 4 * h, 4.6 * w), "i_silver")       # gauntlet
        pw = 7 * w if heavy else 6 * w
        arm.cbox((ax + side * 0.6, 29.5 * h, 0), (pw, 3 * h, pw), "i_silver")     # pauldron
        arm.crystal((ax + side * 2, 31 * h, 0), 6 * h, 2.6, "i_crystal_glow")
        b.bone(f"item_{nm[-1]}", nm, pivot=(ax, 17 * h, -1))
    for side, nm in ((-1, "leg_r"), (1, "leg_l")):
        lx = side * 3 * w
        leg = b.bone(nm, "root", pivot=(lx, 19 * h, 0))
        leg.cbox((lx, 13 * h, 0), (4.6 * w, 12 * h, 4.6 * w), "i_crystal_deep")
        leg.cbox((lx, 3 * h, -0.4), (5 * w, 6 * h, 5.6 * w), "i_silver")           # sabaton
        leg.cbox((lx, 11 * h, -2.6 * w), (3.4 * w, 5 * h, 0.8), "i_crystal")       # knee guard
    return h


def knight_anims(m, h, attack, special, defend=None):
    idle = m.anim("idle", loop=True)
    idle.pos("body", [0, "math.sin(q.life_time * 90) * 0.35", 0])
    idle.rot("arm_r", ["math.sin(q.life_time * 80) * 2", 0, 0])
    idle.rot("arm_l", ["-math.sin(q.life_time * 80) * 2", 0, 0])
    walk = m.anim("walk", loop=True)
    sw = "math.cos(q.modified_distance_moved * 38.17) * 38 * math.min(1, q.modified_move_speed * 2.2)"
    walk.rot("leg_r", [sw, 0, 0]).rot("leg_l", [f"-{sw}", 0, 0])
    walk.rot("arm_r", [f"-{sw} * 0.5", 0, 0]).rot("arm_l", [f"{sw} * 0.5", 0, 0])
    walk.pos("body", [0, "math.abs(math.sin(q.modified_distance_moved * 38.17)) * 0.6", 0])
    summon = m.anim("summon", length=1.0, loop="hold_on_last_frame")
    summon.pos("root", {0: [0, -38 * h, 0], 0.7: [0, 1, 0], 1.0: [0, 0, 0]})
    summon.rot("head", {0: [30, 0, 0], 1.0: [0, 0, 0]})
    dis = m.anim("dissolve", length=0.9, loop="hold_on_last_frame")
    dis.scale("root", {0: [1, 1, 1], 0.15: [1.06, 1.06, 1.06], 0.8: [0, 0, 0]})
    dis.pos("head", {0: [0, 0, 0], 0.8: [0, 10, 0]})
    dis.pos("arm_r", {0: [0, 0, 0], 0.8: [-8, 2, 0]})
    dis.pos("arm_l", {0: [0, 0, 0], 0.8: [8, 2, 0]})
    m.locomotion_controller()
    acts = {1: attack, 2: special, 4: "summon", 7: "dissolve"}
    if defend:
        acts[3] = defend
    m.action_controller(acts)


def sword_knight():
    m = Mob("frost_knight_sword")
    h = humanoid(m, 1.0, 1.0)
    crest = m.model.bone("crest", "head", pivot=(0, 41, 0))
    for k in range(5):
        crest.crystal((0, 40.5, -3 + k * 1.8), 5 + (2 - abs(k - 2)) * 2, 1.6, "i_crystal_glow")
    cape = m.model.bone("cape", "body", pivot=(0, 30, 4))
    for k in range(6):
        cape.cbox((-5 + k * 2, 18, 4.3), (2, 22 - (k % 2) * 4, 0.6), "i_ice")
    m.model.bone("t_capeglass", "cape", pivot=(0, 30, 4)).cbox((0, 19, 4.9), (11, 20, 0.2), "i_ice_pale")
    sw = m.model.bone("sword", "item_r", pivot=(-8.2, 17, -1))
    blade = oriented(m, "blade", "sword", (-8.2, 16, -1), rx=90)
    blade.cbox((-8.2, 16 + 15, -1), (2, 30, 0.8), "i_crystal")
    blade.cbox((-8.2, 16 + 30.5, -1), (1.2, 3, 0.6), "i_crystal_glow")
    m.model.bone("g_edge", "blade", pivot=(-8.2, 16, -1)).cbox((-8.2, 16 + 15, -1.5), (0.4, 28, 0.3), "i_glow_band")
    sw.cbox((-8.2, 16, -2), (7, 1.4, 1.6), "i_silver")
    sw.cbox((-8.2, 16, 2), (1.2, 1.2, 5), "i_silver_dark")
    atk = m.anim("slash", length=0.5)
    atk.rot("arm_r", {0: [0, 0, 0], 0.12: [-150, 20, 0], 0.3: [-20, -30, 0], 0.5: [0, 0, 0]})
    atk.rot("body", {0: [0, 0, 0], 0.12: [0, 18, 0], 0.3: [0, -25, 0], 0.5: [0, 0, 0]})
    sp = m.anim("crescent", length=0.8)
    sp.rot("root", {0: [0, 0, 0], 0.6: [0, 360, 0], 0.8: [0, 360, 0]})
    sp.rot("arm_r", {0: [0, 0, 0], 0.1: [-90, 0, 0], 0.6: [-90, 0, 0], 0.8: [0, 0, 0]})
    sp.scale("g_edge", {0: [1, 1, 1], 0.1: [3, 1, 3], 0.6: [3, 1, 3], 0.8: [1, 1, 1]})
    guard = m.anim("guard", loop=True)
    guard.rot("arm_r", [-70, 30, 0])
    knight_anims(m, h, "slash", "crescent", "guard")
    m.bp_components = knight_components(40, 7, 0.32, 0.6, extra_family=("frost_knight_sword",))
    m.bp_groups = dict(TAMED_GROUP)
    m.bp_events = {"grimoire:tamed": {"add": {"component_groups": ["grimoire:tamed"]}}}


def spear_knight():
    m = Mob("frost_knight_spear", bounds=(3, 4, (0, 1.7, 0)))
    h = humanoid(m, 1.1, 0.92)
    for side in (-1, 1):
        wing = oriented(m, f"helmwing{'l' if side > 0 else 'r'}", "head", (side * 5, 40, 1), rx=-20, ry=side * 20)
        for k in range(3):
            wing.cbox((side * (5 + k * 1.2), 40 + k * 2.8, 2 + k * 1.5), (1, 6 - k, 3.4), "i_crystal_glow")
    spear = m.model.bone("spear", "item_r", pivot=(-8.0, 18.7, -1))
    shaft = oriented(m, "shaft", "spear", (-8.0, 18.7, -1), rx=70)
    shaft.cbox((-8.0, 18.7 + 8, -1), (1.4, 56, 1.4), "i_silver_dark")
    for y in (0, 14, 28):
        shaft.cbox((-8.0, 18.7 + y - 6, -1), (2, 1.4, 2), "i_silver")
    shaft.crystal((-8.0, 18.7 + 36, -1), 16, 4.5, "i_crystal", "i_crystal_glow", tip=0.6)
    m.model.bone("g_tipglow", "shaft", pivot=(-8.0, 18.7 + 44, -1)).cbox((-8.0, 18.7 + 44, -1), (1, 8, 1), "i_core")
    thrust = m.anim("thrust", length=0.45)
    thrust.rot("arm_r", {0: [0, 0, 0], 0.1: [-30, 0, 0], 0.22: [-80, 0, 0], 0.45: [0, 0, 0]})
    thrust.pos("arm_r", {0: [0, 0, 0], 0.22: [0, 0, -4], 0.45: [0, 0, 0]})
    lunge = m.anim("lunge", length=0.7)
    lunge.rot("body", {0: [0, 0, 0], 0.15: [-10, 0, 0], 0.35: [24, 0, 0], 0.7: [0, 0, 0]})
    lunge.rot("arm_r", {0: [0, 0, 0], 0.15: [-20, 0, 0], 0.35: [-95, 0, 0], 0.7: [0, 0, 0]})
    lunge.rot("leg_l", {0: [0, 0, 0], 0.35: [-35, 0, 0], 0.7: [0, 0, 0]})
    lunge.rot("leg_r", {0: [0, 0, 0], 0.35: [25, 0, 0], 0.7: [0, 0, 0]})
    lunge.scale("g_tipglow", {0: [1, 1, 1], 0.35: [3, 2, 3], 0.7: [1, 1, 1]})
    guard = m.anim("brace", loop=True)
    guard.rot("arm_r", [-55, 0, 0]).rot("body", [8, 0, 0])
    knight_anims(m, h, "thrust", "lunge", "brace")
    m.bp_components = knight_components(36, 6, 0.34, 0.5, height=2.7, extra_family=("frost_knight_spear",))
    m.bp_groups = dict(TAMED_GROUP)
    m.bp_events = {"grimoire:tamed": {"add": {"component_groups": ["grimoire:tamed"]}}}


def shield_knight():
    m = Mob("frost_knight_shield", bounds=(3.5, 3.5, (0, 1.5, 0)))
    h = humanoid(m, 1.0, 1.25, heavy=True)
    for side in (-1, 1):
        horn = oriented(m, f"horn{'l' if side > 0 else 'r'}", "head", (side * 5.5, 39, 0), rx=-15, ry=side * 70)
        horn.crystal((side * 5.5, 39, 0), 11, 3, "i_crystal_deep", "i_crystal_glow")
    sh = m.model.bone("shield", "item_l", pivot=(10.5, 17, -1))
    sh.cbox((13.5, 22, -4), (1.6, 34, 22), "i_crystal_deep")                  # tower shield
    sh.cbox((14.6, 22, -4), (0.6, 30, 18), "i_silver")
    sh.cbox((14.9, 24, -4), (0.4, 10, 10), "i_crystal_glow", rotation=(45, 0, 0))   # hex crest (diamond)
    for y in (8, 36):
        sh.cbox((13.5, y, -4), (2.2, 1.4, 23), "i_silver_dark")
    m.model.bone("g_crest", "shield", pivot=(15, 24, -4)).cbox((15.2, 24, -4), (0.2, 5, 5), "i_core", rotation=(45, 0, 0))
    mace = m.model.bone("mace", "item_r", pivot=(-10.5, 17, -1))
    mace.cbox((-10.5, 22, -1), (1.6, 12, 1.6), "i_silver_dark")
    mace.crystal((-10.5, 27, -1), 8, 5, "i_crystal", "i_crystal_glow")
    bash = m.anim("bash", length=0.5)
    bash.rot("arm_l", {0: [0, 0, 0], 0.15: [-60, -20, 0], 0.3: [-80, 0, 0], 0.5: [0, 0, 0]})
    bash.pos("arm_l", {0: [0, 0, 0], 0.3: [0, 0, -4], 0.5: [0, 0, 0]})
    slam = m.anim("slam", length=0.8)
    slam.rot("arm_l", {0: [0, 0, 0], 0.3: [-150, 0, 0], 0.5: [-40, 0, 0], 0.8: [0, 0, 0]})
    slam.rot("body", {0: [0, 0, 0], 0.5: [20, 0, 0], 0.8: [0, 0, 0]})
    slam.scale("g_crest", {0: [1, 1, 1], 0.5: [3, 3, 3], 0.8: [1, 1, 1]})
    guard = m.anim("bulwark", loop=True)
    guard.rot("arm_l", [-75, -35, 0]).rot("body", [6, 0, 0])
    guard.rot("leg_r", [10, 0, 0]).rot("leg_l", [-10, 0, 0])
    guard.scale("g_crest", ["1.5 + math.sin(q.life_time * 400) * 0.3"] * 3)
    knight_anims(m, h, "bash", "slam", "bulwark")
    m.bp_components = knight_components(80, 4, 0.26, 1.0, width=1.0, extra_family=("frost_knight_shield",))
    m.bp_groups = dict(TAMED_GROUP)
    m.bp_events = {"grimoire:tamed": {"add": {"component_groups": ["grimoire:tamed"]}}}


sword_knight()
spear_knight()
shield_knight()


# ============================================================================== B12 Royal Stag
def royal_stag():
    m = Mob("royal_stag", tex=(128, 256), bounds=(4, 5, (0, 2, 0)))
    b = m.model
    side_faces = {"east": "b_stag_hide", "west": "b_stag_hide"}

    def shard(bone, base, h, w, rx, rz=0.0, style="b_crystal_glow", tip="b_ruby"):
        """Tilted crystal spike whose base stays planted at `base`."""
        x, y, z = base
        bone.box((x - w / 2, y - 0.6, z - w / 2), (w, h * 0.72 + 0.6, w), style, rotation=(rx, 0, rz), pivot=base)
        bone.box((x - w * 0.3, y + h * 0.72, z - w * 0.3), (w * 0.6, h * 0.28, w * 0.6), tip, rotation=(rx, 0, rz), pivot=base)

    b.bone("root", pivot=(0, 0, 0))
    body = b.bone("body", "root", pivot=(0, 24, 0))
    # tapered torso: deep chest, ribcage, narrow waist, rounded haunch (sides carry the glowing vessel hide)
    body.cbox((0, 28, -11), (15, 16, 11), "b_crystal", faces=side_faces)        # chest (withers 36)
    body.cbox((0, 27, -2), (14, 14, 10), "b_crystal", faces=side_faces)         # ribcage
    body.cbox((0, 27.5, 6), (12.5, 12, 8), "b_crystal", faces=side_faces)       # waist
    body.cbox((0, 28, 13), (14, 14, 9), "b_crystal", faces=side_faces)          # haunch
    body.cbox((0, 20.6, 0), (9.5, 1.6, 22), "b_burgundy")                        # belly
    body.cbox((0, 23, -16.9), (11, 9, 1.2), "b_crystal_glow")                    # breast plate
    for i, (z, top, h) in enumerate(((-14.5, 36, 3.2), (-11, 36, 4.6), (-7.5, 36, 5.2), (-3.5, 34, 4.4),
                                     (0.5, 34, 3.8), (4.5, 33.5, 3.2), (9, 35, 2.8), (13, 35, 2.2))):
        shard(body, (0, top, z), h, 1.7 - i * 0.06, -38)                           # spine ridge
    veins = b.bone("g_veins", "body", pivot=(0, 24, 0))
    veins.cbox((0, 28.5, -17.6), (3.2, 3.2, 0.6), "b_core", rotation=(0, 0, 45))   # crystallised heart
    for side in (1, -1):                                                           # main arteries along the flanks
        for (x, z0, z1, y) in ((7.56, -16, -5.6, 29.5), (7.06, -7, 3, 29), (6.31, 2, 10, 28.6), (7.06, 8.6, 17, 29.2)):
            veins.cbox((side * x, y, (z0 + z1) / 2), (0.2, 0.7, z1 - z0), "b_glow_band")
    neck = b.bone("neck", "body", pivot=(0, 33, -13))
    neck.cbox((0, 39.5, -16), (7.5, 15, 8), "b_crystal", rotation=(25, 0, 0), faces=side_faces)
    neck.cbox((0, 35.2, -18.6), (8.4, 6, 3), "b_burgundy", rotation=(25, 0, 0))   # throat ruff
    for i, (y, z) in enumerate(((36.7, -10.3), (39.0, -11.4), (41.2, -12.4), (43.6, -13.6), (46.0, -14.6))):
        shard(neck, (0, y, z), 3.4 - abs(i - 2) * 0.4, 1.3, -62)                  # crystal mane
    head = b.bone("head", "neck", pivot=(0, 45, -19))
    head.cbox((0, 47.5, -22.5), (8, 7.5, 9), "b_crystal")
    head.cbox((0, 45.5, -29.5), (5.6, 5, 7), "b_crystal")                         # muzzle
    head.cbox((0, 47.6, -29), (4.4, 1.2, 5.4), "b_crystal_glow")                   # blaze
    head.cbox((0, 45.4, -33.2), (3.8, 3.2, 1), "b_burgundy")                      # nose
    head.cbox((0, 43.2, -28.5), (4.6, 1.2, 5.6), "b_burgundy")                    # jaw
    eyes = b.bone("g_eyes", "head", pivot=(0, 48, -24))
    for side in (1, -1):
        eyes.cbox((side * 4.06, 48.3, -24.6), (0.24, 1.3, 2.2), "b_core")
    for side, nm in ((1, "ear_l"), (-1, "ear_r")):
        ear = b.bone(nm, "head", pivot=(side * 4, 50, -20.5))
        ear.cbox((side * 6.2, 50.5, -20.5), (5, 2, 2.6), "b_crystal", rotation=(0, side * 20, side * -15))
        ear.cbox((side * 6.4, 50.5, -21.85), (3.4, 1.2, 0.2), "b_glow_band", rotation=(0, side * 20, side * -15))
    # branching vascular antlers (bind-pose chains; rest rotations bend them)
    for side, nm in ((1, "ant_l"), (-1, "ant_r")):
        b.bone(nm, "head", pivot=(side * 2.6, 51, -21), rotation=(-20, side * 25, 0))
        b.bone(nm + "_burr", nm, pivot=(side * 2.6, 51, -21)).cbox((side * 2.6, 51.4, -21), (3.2, 1.6, 3.2), "b_silver")
        prev = nm
        y = 51
        for s_ in range(4):
            seg = b.bone(f"{nm}_{s_}", prev, pivot=(side * 2.6, y, -21), rotation=(10 if s_ else 0, 0, 0))
            seg.cbox((side * 2.6, y + 4.5, -21), (2.2 - s_ * 0.3, 9.4, 2.2 - s_ * 0.3), "b_crystal_glow")
            seg.cbox((side * 2.6, y + 4.5, -22.2), (0.5, 9, 0.5), "b_glow_band")
            # tines branch forward / outward from each segment
            for t, (rx, ry, ln) in enumerate(((-55, side * 30, 7 - s_), (-30, -side * 40, 6 - s_ * 0.8))):
                tb = b.bone(f"{nm}_{s_}t{t}", f"{nm}_{s_}", pivot=(side * 2.6, y + 7, -21), rotation=(rx, ry, 0))
                tb.cbox((side * 2.6, y + 7 + ln / 2, -21), (1.2, ln, 1.2), "b_crystal_glow")
                tb.cbox((side * 2.6, y + 7 + ln + 0.6, -21), (0.8, 1.2, 0.8), "b_ruby")
            prev = f"{nm}_{s_}"
            y += 9
    legs = (("leg_fl", 5, -10), ("leg_fr", -5, -10), ("leg_bl", 5, 12), ("leg_br", -5, 12))
    for nm, x, z in legs:
        back = z > 0
        up = b.bone(nm, "root", pivot=(x, 22, z))
        if back:
            up.cbox((x, 20, z + 0.5), (5, 10, 7.5), "b_crystal", faces=side_faces)   # thigh
            up.cbox((x, 14, z + 1.2), (3.6, 6, 4), "b_crystal")
        else:
            up.cbox((x, 17.5, z), (4.2, 11, 5), "b_crystal", faces=side_faces)
        low = b.bone(f"{nm}_low", nm, pivot=(x, 12, z + (1.2 if back else 0)))
        low.cbox((x, 7, z + (1.6 if back else 0.4)), (2.6, 10, 2.8), "b_crystal")
        low.cbox((x, 9.5, z + (0.15 if back else -1.05)), (1.4, 4, 0.2), "b_glow_band")   # shin vessel
        low.cbox((x, 1.2, z - 0.4 + (1.2 if back else 0)), (3.6, 2.4, 4.2), "b_silver")   # blackened-silver hoof
        b.bone(f"g_{nm}_hoof", f"{nm}_low", pivot=(x, 1, z)).cbox((x, 0.3, z - 0.4 + (1.2 if back else 0)), (3, 0.4, 3.6), "b_core")
    tail = b.bone("tail", "body", pivot=(0, 33, 17.5))
    tail.cbox((0, 32, 19), (3.4, 5, 2.6), "b_crystal_glow", rotation=(30, 0, 0))

    def gait(a, speed_mult, amp):
        ph = f"q.modified_distance_moved * {38.17 * speed_mult}"
        k = f"math.min(1, q.modified_move_speed * 2.5)"
        a.rot("leg_fl", [f"math.cos({ph}) * {amp} * {k}", 0, 0])
        a.rot("leg_br", [f"math.cos({ph}) * {amp} * {k}", 0, 0])
        a.rot("leg_fr", [f"-math.cos({ph}) * {amp} * {k}", 0, 0])
        a.rot("leg_bl", [f"-math.cos({ph}) * {amp} * {k}", 0, 0])
        for nm in ("leg_fl", "leg_fr", "leg_bl", "leg_br"):
            a.rot(f"{nm}_low", [f"math.max(0, math.sin({ph})) * {amp * 0.8} * {k}", 0, 0])
        a.pos("body", [0, f"math.abs(math.sin({ph})) * {amp / 30} * {k}", 0])
        a.rot("neck", [f"math.sin({ph} * 2) * {amp / 8}", 0, 0])

    idle = m.anim("idle", loop=True)
    idle.scale("body", [1, "1 + math.sin(q.life_time * 100) * 0.015", "1 + math.sin(q.life_time * 100) * 0.01"])
    idle.rot("head", ["math.sin(q.life_time * 40) * 4", "math.sin(q.life_time * 25) * 12", 0])
    idle.rot("ear_l", [0, 0, "math.max(0, math.sin(q.life_time * 300)) * math.pow(math.sin(q.life_time * 30), 8) * 30"])
    idle.rot("tail", ["math.sin(q.life_time * 150) * 8", 0, 0])
    walk = m.anim("walk", loop=True)
    gait(walk, 1.0, 26)
    run = m.anim("run", loop=True)
    gait(run, 0.8, 48)
    run.rot("neck", [-6, 0, 0])
    m.controllers[f"controller.animation.grimoire.royal_stag.move"] = {
        "initial_state": "idle",
        "states": {
            "idle": {"animations": ["idle"], "transitions": [{"walk": "q.modified_move_speed > 0.06"}], "blend_transition": 0.25},
            "walk": {"animations": ["walk"], "transitions": [{"idle": "q.modified_move_speed <= 0.06"}, {"run": "q.modified_move_speed > 0.45"}], "blend_transition": 0.2},
            "run": {"animations": ["run"], "transitions": [{"walk": "q.modified_move_speed <= 0.45"}], "blend_transition": 0.2},
        },
    }
    m.animate.append("move")
    summon = m.anim("summon", length=1.4, loop="hold_on_last_frame")
    summon.scale("root", {0: [0.05, 0.05, 0.05], 0.8: [0.6, 1.1, 0.6], 1.2: [1.04, 0.98, 1.04], 1.4: [1, 1, 1]})
    summon.rot("root", {0: [0, -180, 0], 1.2: [0, 0, 0]})
    summon.rot("neck", {0: [40, 0, 0], 1.0: [-20, 0, 0], 1.4: [0, 0, 0]})
    prep = m.anim("prepare", loop=True)
    prep.rot("neck", [38, 0, 0]).rot("head", [20, 0, 0])
    prep.rot("leg_fl", ["-20 + math.sin(q.life_time * 500) * 25", 0, 0])
    prep.rot("leg_fl_low", ["30 + math.sin(q.life_time * 500) * 20", 0, 0])
    prep.rot("body", [6, 0, 0])
    prep.scale("g_veins", ["1 + math.sin(q.life_time * 900) * 0.04"] * 3)
    charge = m.anim("charge", loop=True)
    gait(charge, 0.7, 55)
    charge.rot("neck", [42, 0, 0]).rot("head", [22, 0, 0])
    dfn = m.anim("defend", length=1.0, loop="hold_on_last_frame")
    dfn.rot("body", {0: [0, 0, 0], 0.3: [-38, 0, 0], 0.7: [-38, 0, 0], 1.0: [0, 0, 0]})
    dfn.rot("leg_fl", {0: [0, 0, 0], 0.3: [-70, 0, 0], 0.7: [-60, 0, 0], 1.0: [0, 0, 0]})
    dfn.rot("leg_fr", {0: [0, 0, 0], 0.3: [-50, 0, 0], 0.7: [-70, 0, 0], 1.0: [0, 0, 0]})
    dfn.scale("g_veins", {0: [1, 1, 1], 0.4: [1.15, 1.15, 1.15], 1.0: [1, 1, 1]})
    for nm in ("ant_l", "ant_r"):
        dfn.scale(nm, {0: [1, 1, 1], 0.4: [1.2, 1.2, 1.2], 1.0: [1, 1, 1]})
    dis = m.anim("dissolve", length=1.2, loop="hold_on_last_frame")
    dis.scale("root", {0: [1, 1, 1], 0.2: [1.05, 1.05, 1.05], 1.1: [0, 0, 0]})
    dis.pos("ant_l", {0: [0, 0, 0], 1.0: [8, 10, 0]})
    dis.pos("ant_r", {0: [0, 0, 0], 1.0: [-8, 10, 0]})
    m.action_controller({2: "charge", 3: "defend", 4: "summon", 5: "prepare", 6: "charge", 7: "dissolve"})
    comps = knight_components(60, 8, 0.33, 0.8, height=2.4, width=1.4, extra_family=("royal_stag",))
    comps["minecraft:type_family"] = {"family": ["grimoire_summon", "royal_stag", "mob"]}
    comps["minecraft:timer"] = {"time": 60, "looping": False, "time_down_event": {"event": "grimoire:expire", "target": "self"}}
    m.bp_components = comps
    m.bp_groups = dict(TAMED_GROUP)
    m.bp_events = {"grimoire:tamed": {"add": {"component_groups": ["grimoire:tamed"]}}}


royal_stag()
