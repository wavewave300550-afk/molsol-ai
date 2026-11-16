"""
vesper_anims.py - animations, controllers and client scripts of VESPER-0.

Sign conventions (see geo.py): +rx pitches the front down / swings hanging parts back;
+ry turns the front towards the entity's right (-X); +rz raises parts on the right (-X)
side and lowers parts on the left (+X) side.  Hence for mirrored pairs the r/l values of
ry and rz flip sign (R(...) helper below).
"""
from __future__ import annotations

from typing import Dict, List

from anim import Anim, Controller
from vesper_model import LIMBS, RIBS

NS = "animation.sab.vesper"

# ----------------------------------------------------------------------------- act ids (script <-> client contract)
ACT = {
    "idle": 0, "arrive": 1, "depart": 2, "lance_charge": 3, "lance_fire": 4, "rite": 5, "horizon": 6,
    "choir": 7, "genuflect": 8, "vent_flare": 9, "pray": 10, "stunned": 11, "lunge_windup": 12,
    "lunge": 13, "anchored": 14, "talons": 15, "nova_charge": 16, "nova_release": 17, "unhaloed": 18,
    "roar": 19,
}
PHASE = {"p1": 0, "transform": 1, "p2": 2, "dying": 3}

SIDES = ("r", "l")
SG = {"r": 1.0, "l": -1.0}       # sign for ry / rz of mirrored parts
N_RIBS = len(RIBS)
N_PLATES = N_RIBS - 1
LIMB_IDS = list(LIMBS)
GAIT_GROUP = {"fr": 0, "ml": 0, "rr": 0, "fl": 180, "mr": 180, "rl": 180}


def mirror(rx, ry, rz, side):
    s = SG[side]
    return (rx, ry * s, rz * s)


def keys_side(keys, side):
    return {t: mirror(*v, side) for t, v in keys.items()}


def stable(name: str, mod: int) -> int:
    """Deterministic small hash (Python's hash() is salted per process)."""
    return sum((i + 1) * ord(c) for i, c in enumerate(name)) % mod


def num(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


# ----------------------------------------------------------------------------- client scripts

PRE_ANIMATION = [
    "variable.t = query.life_time;",
    "variable.dt = math.min(query.delta_time, 0.1);",
    "variable.phase = query.property('sab:phase');",
    "variable.act = query.property('sab:act');",
    "variable.hd = variable.hd + math.min_angle(query.property('sab:heading') - variable.hd) * math.min(1.0, variable.dt * 7.0);",
    "variable.pt = variable.pt + (query.property('sab:pitch') - variable.pt) * math.min(1.0, variable.dt * 5.0);",
    "variable.bk = variable.bk + (query.property('sab:bank') - variable.bk) * math.min(1.0, variable.dt * 4.0);",
    "variable.ly = variable.ly + (query.property('sab:look_yaw') - variable.ly) * math.min(1.0, variable.dt * 5.0);",
    "variable.lp = variable.lp + (query.property('sab:look_pitch') - variable.lp) * math.min(1.0, variable.dt * 5.0);",
    "variable.chg = variable.chg + (query.property('sab:charge') - variable.chg) * math.min(1.0, variable.dt * 6.0);",
    "variable.spd = math.clamp(query.ground_speed / 9.0, 0.0, 1.0);",
    "variable.rs = 1.0 + variable.chg * 5.0 + (query.property('sab:enrage') ? 1.5 : 0.0);",
    "variable.ra = math.mod(variable.ra + variable.dt * 13.0 * variable.rs, 360.0);",
    "variable.rb = math.mod(variable.rb - variable.dt * 21.0 * variable.rs, 360.0);",
    "variable.rc = math.mod(variable.rc + variable.dt * 33.0 * variable.rs, 360.0);",
    "variable.cg = math.mod(variable.cg + variable.dt * (55.0 + variable.chg * 260.0), 360.0);",
    "variable.gait = math.mod(variable.gait + variable.dt * (160.0 + 420.0 * variable.spd), 360.0);",
    "variable.hurt = query.hurt_time > 0 ? 1.0 : 0.0;",
]

INITIALIZE = [
    "variable.hd = query.property('sab:heading');",
    "variable.pt = 0.0;", "variable.bk = 0.0;", "variable.ly = 0.0;", "variable.lp = 0.0;", "variable.chg = 0.0;",
    "variable.ra = 0.0;", "variable.rb = 120.0;", "variable.rc = 240.0;", "variable.cg = 0.0;", "variable.gait = 0.0;",
]


# ----------------------------------------------------------------------------- base layers

def base() -> Anim:
    a = Anim(f"{NS}.base", loop=True)
    a.rot_e("root", "0", "math.min_angle(variable.hd - query.body_y_rotation)", "0")
    a.rot_e("body", "variable.pt + math.sin(variable.t * 40.0) * 1.2",
            "0",
            "variable.bk + math.sin(variable.t * 27.0) * 1.5 + variable.hurt * math.sin(variable.t * 1900.0) * 1.2")
    a.pos_e("body", "0", "math.sin(variable.t * 55.0) * 3.0", "0")
    # head tracks the current target (look properties come from the script)
    for bone, w in (("neck_2", 0.25), ("neck_1", 0.3), ("skull", 0.45)):
        a.rot_e(bone, f"variable.lp * {w}", f"variable.ly * {w}", "0")
    # gyroscopic rings
    a.rot_e("ring_a_spin", "0", "0", "variable.ra")
    a.rot_e("ring_b_spin", "0", "0", "variable.rb")
    a.rot_e("ring_c_spin", "0", "0", "variable.rc")
    a.rot_e("ring_a", "math.sin(variable.t * 19.0) * 4.0", "math.cos(variable.t * 15.0) * 5.0", "0")
    a.rot_e("ring_b", "math.sin(variable.t * 23.0 + 40.0) * 6.0", "math.cos(variable.t * 17.0) * 7.0", "0")
    a.rot_e("ring_c", "math.sin(variable.t * 27.0 + 90.0) * 7.0", "math.cos(variable.t * 21.0 + 30.0) * 8.0", "0")
    # artificial sun + gyro cage
    a.rot_e("sun", "variable.t * 11.0", "variable.t * 23.0", "0")
    a.scl_e("sun", "1.0 + math.sin(variable.t * 140.0) * 0.04 + variable.chg * 0.4")
    a.rot_e("cage_1", "variable.cg", "0", "0")
    a.rot_e("cage_2", "0", "-variable.cg * 1.3", "0")
    # censers swing, spires sway, ribs breathe
    for i in range(1, 4):
        a.rot_e(f"censer_{i}", f"math.sin(variable.t * 62.0 + {i * 47}) * 6.0", "0", f"math.cos(variable.t * 44.0 + {i * 31}) * 4.0")
    for i in range(1, 5):
        a.rot_e(f"spire_{i}", f"math.sin(variable.t * 33.0 + {i * 25}) * 2.0", "0", f"math.cos(variable.t * 29.0 + {i * 40}) * 1.5")
    for i in range(1, N_RIBS + 1):
        for s in SIDES:
            a.rot_e(f"rib_{s}{i}", "0", "0", f"{num(SG[s])} * (math.sin(variable.t * 36.0 - {i * 20}) * 1.4 + 1.4)")
    return a


def idle_p1() -> Anim:
    a = Anim(f"{NS}.idle_p1", loop=True)
    for i in range(1, 7):
        a.rot_e(f"tail_{i}", f"math.sin(variable.t * 45.0 - {i * 35}) * {2.0 + i * 0.9:.1f}",
                f"math.sin(variable.t * 31.0 - {i * 30}) * {1.0 + i * 0.5:.1f}", "0")
    for s in SIDES:
        g = SG[s]
        a.rot_e(f"fluke_{s}", "math.sin(variable.t * 45.0 - 245.0) * 9.0", "0", f"{num(g)} * math.sin(variable.t * 45.0 - 200.0) * 4.0")
        a.rot_e(f"fin_{s}", "math.sin(variable.t * 40.0 + 60.0) * 6.0", "0", f"{num(g)} * (6.0 + math.sin(variable.t * 40.0) * 10.0)")
        a.rot_e(f"fin_{s}_blade", "0", "0", f"{num(g)} * math.sin(variable.t * 40.0 - 40.0) * 8.0")
        a.rot_e(f"fin_{s}_tip", "0", "0", f"{num(g)} * math.sin(variable.t * 40.0 - 80.0) * 7.0")
        a.rot_e(f"mandible_{s}", "(math.sin(variable.t * 30.0) * 0.5 + 0.5) * 1.5", "0", "0")
        a.rot_e(f"engine_{s}", "math.sin(variable.t * 30.0 + 90.0) * 2.0", "0", "0")
    return a


def pose_p2() -> Anim:
    a = Anim(f"{NS}.pose_p2", loop=True)
    for b, v in P2_POSE.items():
        a.rot(b, {0.0: v}, lerp="linear")
    a.pos("body", {0.0: (0, -8, 0)}, lerp="linear")
    a.pos("skull", {0.0: (0, -6, 0)}, lerp="linear")
    a.pos("maw", {0.0: (0, -4, 0)}, lerp="linear")
    return a


def _p2_pose() -> Dict[str, tuple]:
    p = {"skull": (10, 0, 0), "maw": (8, 0, 0)}
    for s in SIDES:
        p[f"mandible_{s}"] = mirror(18, 16, 0, s)
        p[f"fin_{s}"] = mirror(0, 0, -25, s)
        p[f"fin_{s}_blade"] = mirror(0, 35, 0, s)
        p[f"engine_{s}"] = (10, 0, 0)
        for i in range(1, N_RIBS + 1):
            p[f"rib_{s}{i}"] = mirror(0, 0, 10, s)
    for i, rx in enumerate((8, 12, 14, 16, 16, 14), start=1):
        p[f"tail_{i}"] = (rx, 0, 0)
    for i in range(1, 5):
        p[f"spire_{i}"] = (-10, 0, 0)
    return p


P2_POSE = _p2_pose()


def idle_p2() -> Anim:
    a = Anim(f"{NS}.idle_p2", loop=True)
    a.rot_e("body", "math.sin(variable.t * 311.0) * 0.6", "0", "math.sin(variable.t * 90.0) * 1.5")
    for i in range(1, 7):
        a.rot_e(f"tail_{i}", f"math.sin(variable.t * 80.0 - {i * 40}) * {3 + i}",
                f"math.sin(variable.t * 60.0 - {i * 45}) * {4 + i * 1.5:.1f}", "0")
    for s in SIDES:
        g = num(SG[s])
        a.rot_e(f"mandible_{s}", "math.sin(variable.t * 120.0) * 4.0 + math.sin(variable.t * 47.0) * 3.0",
                f"{g} * math.sin(variable.t * 90.0) * 4.0", "0")
        a.rot_e(f"fin_{s}", "0", "0", f"{g} * math.sin(variable.t * 70.0) * 4.0")
        for i in range(1, N_RIBS + 1):
            a.rot_e(f"rib_{s}{i}", "0", "0", f"{g} * math.sin(variable.t * 70.0 - {i * 30}) * 3.0")
    a.rot_e("maw", "math.sin(variable.t * 120.0) * 2.0", "0", "0")
    # limbs: twitch + tripod gait scaled by ground speed
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        g = num(SG[s])
        ph = GAIT_GROUP[lid]
        k = (stable(lid, 7)) * 23
        a.rot_e(f"limb_{lid}_femur",
                f"math.sin(variable.t * 50.0 + {k}) * 3.0 + math.cos(variable.gait + {ph}) * 16.0 * variable.spd",
                f"{g} * math.cos(variable.gait + {ph}) * 10.0 * variable.spd",
                f"{g} * (math.sin(variable.t * 41.0 + {k}) * 3.0 + math.max(0.0, math.sin(variable.gait + {ph})) * 22.0 * variable.spd)")
        a.rot_e(f"limb_{lid}_tibia", f"math.sin(variable.t * 65.0 + {k}) * 4.0 - math.max(0.0, math.sin(variable.gait + {ph})) * 14.0 * variable.spd", "0", "0")
        a.rot_e(f"limb_{lid}_talon", f"math.sin(variable.t * 83.0 + {k}) * 6.0", "0", "0")
    return a


# ----------------------------------------------------------------------------- ring formations

RING_REST_ROT = {"a": 0.0, "b": 22.0, "c": -18.0}


def rings_lance(a: Anim, t_in=1.4, hold=None):
    a.pos("ring_a", {0.0: (0, 0, 0), 0.7: (0, 6, -120), t_in: (0, 0, -236)})
    a.pos("ring_b", {0.0: (0, 0, 0), 0.6: (0, 40, -90), t_in: (0, -8, -164)})
    a.rot("ring_b", {0.0: (0, 0, 0), t_in: (-22, 0, 0)})
    a.pos("ring_c", {0.0: (0, 0, 0), 0.45: (0, 170, -60), 0.95: (0, 150, -340), t_in: (0, 0, -462)})
    a.rot("ring_c", {0.0: (0, 0, 0), t_in: (18, 0, 0)})


def rings_hold_lance(a: Anim):
    a.pos("ring_a", {0.0: (0, 0, -236)}, lerp="linear")
    a.pos("ring_b", {0.0: (0, -8, -164)}, lerp="linear")
    a.rot("ring_b", {0.0: (-22, 0, 0)}, lerp="linear")
    a.pos("ring_c", {0.0: (0, 0, -462)}, lerp="linear")
    a.rot("ring_c", {0.0: (18, 0, 0)}, lerp="linear")


# ----------------------------------------------------------------------------- acts

def act_anims() -> List[Anim]:
    out = []

    # ---- arrive (6 s): rings materialise, the ship levels out and sings
    a = Anim(f"{NS}.arrive", 6.0, "hold_on_last_frame")
    for n, spin in (("a", 720), ("b", -900), ("c", 1080)):
        a.scl(f"ring_{n}", {0.0: 0.01, 1.2: 0.4, 2.4: 1.15, 3.0: 1.0})
        a.rot(f"ring_{n}_spin", {0.0: (0, 0, 0), 3.0: (0, 0, spin)}, lerp="linear")
    a.rot("body", {0.0: (22, 0, 0), 2.5: (8, 0, 0), 4.0: (-6, 0, 0), 5.2: (0, 0, 0)})
    a.scl("sun", {0.0: 0.2, 1.5: 0.6, 3.6: 1.4, 4.4: 1.0})
    for s in SIDES:
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, -35), 2.0: (0, 0, -20), 3.6: (0, 0, 28), 5.0: (0, 0, 0)}, s))
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 3.6: (0, 0, 0), 4.0: (22, 10, 0), 4.8: (20, 8, 0), 5.4: (0, 0, 0)}, s))
    a.rot("skull", {0.0: (0, 0, 0), 3.5: (0, 0, 0), 4.0: (-16, 0, 0), 5.0: (-10, 0, 0), 5.6: (0, 0, 0)})
    a.fx(0.0, "arrival_flash", "core").fx(3.9, "choir_burst", "jaw").fx(2.4, "ring_spark", "ring_a")
    a.sfx(3.9, "roar")
    out.append(a)

    # ---- depart (5 s)
    a = Anim(f"{NS}.depart", 5.0, "hold_on_last_frame")
    a.rot("body", {0.0: (0, 0, 0), 1.5: (-24, 0, 0), 5.0: (-30, 0, 0)})
    a.scl("sun", {0.0: 1.0, 2.0: 1.5, 5.0: 0.3})
    for n in "abc":
        a.scl(f"ring_{n}", {0.0: 1.0, 2.5: 1.2, 5.0: 0.05})
    for s in SIDES:
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, 0), 1.5: (0, 0, 30), 5.0: (0, 0, 35)}, s))
    a.fx(0.2, "ring_spark", "ring_a").fx(4.6, "arrival_flash", "core")
    out.append(a)

    # ---- Litany Lance: charge (rings assemble into a barrel in front of the prow)
    a = Anim(f"{NS}.lance_charge", 1.8, "hold_on_last_frame")
    rings_lance(a)
    a.rot("body", {0.0: (0, 0, 0), 0.8: (-4, 0, 0), 1.8: (2, 0, 0)})
    a.scl("sun", {0.0: 1.0, 1.8: 1.35})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 1.2: (6, 4, 0), 1.8: (9, 5, 0)}, s))
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, 0), 1.0: (0, 0, 18), 1.8: (0, 0, 22)}, s))
    a.fx(0.2, "lance_gather", "prow").fx(0.9, "lance_gather", "prow")
    for i in range(1, 5):
        a.fx(0.3 + i * 0.25, "spire_spark", f"spire_tip_{i}")
    out.append(a)

    # ---- Litany Lance: fire (hold the barrel, recoil and shudder)
    a = Anim(f"{NS}.lance_fire", 2.6, "hold_on_last_frame")
    rings_hold_lance(a)
    a.pos("body", {0.0: (0, 0, 0), 0.12: (0, 2, 12), 0.6: (0, 0, 6), 2.6: (0, 0, 4)})
    a.rot_e("skull", "math.sin(query.anim_time * 2400.0) * 0.8", "0", "0")
    a.scl("sun", {0.0: 1.35, 0.1: 1.6, 2.6: 1.3})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (9, 5, 0), 0.15: (16, 9, 0), 2.6: (14, 8, 0)}, s))
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, 22), 0.2: (0, 0, 12), 2.6: (0, 0, 14)}, s))
    a.rot("maw", {0.0: (0, 0, 0), 0.15: (6, 0, 0)})
    a.fx(0.0, "lance_muzzle", "prow")
    out.append(a)

    # ---- Halo Rite: rings descend, go flat and drop one by one (waves at 1.2 / 2.1 / 3.0 s)
    a = Anim(f"{NS}.rite", 4.2, "hold_on_last_frame")
    a.rot("ring_a", {0.0: (0, 0, 0), 0.9: (90, 0, 0)})
    a.rot("ring_b", {0.0: (0, 0, 0), 0.8: (68, 0, 0)})
    a.rot("ring_c", {0.0: (0, 0, 0), 0.7: (108, 0, 0)})
    a.pos("ring_c", {0.0: (0, 0, 0), 0.7: (0, -134, -82), 1.1: (0, -150, -82), 1.2: (0, -210, -82), 1.6: (0, -140, -82), 4.2: (0, -134, -82)})
    a.pos("ring_b", {0.0: (0, 0, 0), 0.8: (0, -122, 88), 2.0: (0, -132, 88), 2.1: (0, -150, 88), 2.5: (0, -125, 88), 4.2: (0, -122, 88)})
    a.pos("ring_a", {0.0: (0, 0, 0), 0.9: (0, -150, 0), 2.9: (0, -160, 0), 3.0: (0, -220, 0), 3.4: (0, -150, 0), 4.2: (0, -150, 0)})
    a.rot("body", {0.0: (0, 0, 0), 0.8: (-6, 0, 0), 4.2: (-4, 0, 0)})
    a.pos("body", {0.0: (0, 0, 0), 0.8: (0, 10, 0), 4.2: (0, 8, 0)})
    a.fx(1.2, "ring_spark", "ring_c").fx(2.1, "ring_spark", "ring_b").fx(3.0, "ring_spark", "ring_a")
    out.append(a)

    # ---- Event Horizon cast: rear back, sun contracts, rings tilt and whirl
    a = Anim(f"{NS}.horizon", 2.4, "hold_on_last_frame")
    a.rot("body", {0.0: (0, 0, 0), 1.0: (-12, 0, 0), 1.6: (8, 0, 0), 2.4: (0, 0, 0)})
    a.scl("sun", {0.0: 1.0, 1.5: 0.55, 1.65: 1.5, 2.4: 1.0})
    a.rot("ring_a", {0.0: (0, 0, 0), 1.4: (28, 0, 0), 2.4: (0, 0, 0)})
    a.rot("ring_b", {0.0: (0, 0, 0), 1.4: (30, 0, 0), 2.4: (0, 0, 0)})
    a.rot("ring_c", {0.0: (0, 0, 0), 1.4: (-25, 0, 0), 2.4: (0, 0, 0)})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 1.2: (6, 3, 0), 1.6: (22, 10, 0), 2.4: (0, 0, 0)}, s))
    a.fx(0.3, "horizon_gather", "core").fx(1.6, "core_flare", "core")
    out.append(a)

    # ---- Choir of Satellites: spires open like hatches, drones launch at 0.9 s
    a = Anim(f"{NS}.choir", 2.0, "hold_on_last_frame")
    for i, z in enumerate((26, -26, 26, -26), start=1):
        a.rot(f"spire_{i}", {0.0: (0, 0, 0), 0.6: (8, 0, z), 1.2: (6, 0, z * 0.8), 2.0: (0, 0, 0)})
        a.fx(0.9, "drone_launch", f"spire_tip_{i}")
    a.rot("body", {0.0: (0, 0, 0), 0.7: (5, 0, 0), 2.0: (0, 0, 0)})
    out.append(a)

    # ---- Genuflection: kneel and vent (plates open, heart exposed)
    a = Anim(f"{NS}.genuflect", 1.4, "hold_on_last_frame")
    _open_plates(a, 1.2, 40)
    a.rot("body", {0.0: (0, 0, 0), 1.2: (7, 0, 0)})
    a.pos("body", {0.0: (0, 0, 0), 1.2: (0, -10, 0)})
    a.scl("sun", {0.0: 1.0, 1.2: 1.25})
    for s in SIDES:
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, 0), 1.2: (0, 0, -16)}, s))
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 1.2: (7, 2, 0)}, s))
        for i in range(1, N_RIBS + 1):
            a.rot(f"rib_{s}{i}", keys_side({0.0: (0, 0, 0), 1.2: (0, 0, 6)}, s))
    for n in "abc":
        a.pos(f"ring_{n}", {0.0: (0, 0, 0), 1.2: (0, -30, 0)})
    a.fx(0.8, "vent_steam", "core")
    out.append(a)
    v = Anim(f"{NS}.vent_breathe", 2.0, True)
    for i in range(1, N_PLATES + 1):
        for s in SIDES:
            v.rot_e(f"plate_{s}{i}", "0", "0", f"{num(SG[s])} * math.sin(query.anim_time * 180.0 + {i * 50}) * 3.0")
    v.scl_e("reactor", "1.0 + math.sin(query.anim_time * 360.0) * 0.06")
    v.fx(0.0, "heart_sparks", "core").fx(1.0, "vent_steam", "core")
    out.append(v)

    # ---- vent flare (warning before the vent burst)
    a = Anim(f"{NS}.vent_flare", 1.5, "hold_on_last_frame")
    _open_plates(a, 0.0, 40, extra_shake=True)
    a.rot("body", {0.0: (7, 0, 0)}, lerp="linear")
    a.pos("body", {0.0: (0, -10, 0)}, lerp="linear")
    a.scl("sun", {0.0: 1.25, 1.3: 1.7, 1.5: 1.2})
    a.fx(0.0, "vent_steam", "core").fx(0.6, "vent_steam", "core").fx(1.35, "core_flare", "core")
    out.append(a)

    # ---- prayer (loop): rings form an armillary crown above, fins raised like arms
    a = Anim(f"{NS}.pray", 6.0, True)
    a.rot("ring_a", {0.0: (90, 0, 0)}, lerp="linear")
    a.pos_e("ring_a", "0", "196.0 + math.sin(query.anim_time * 60.0) * 6.0", "0")
    a.rot("ring_b", {0.0: (-22, 0, 0)}, lerp="linear")
    a.pos_e("ring_b", "0", "128.0 + math.sin(query.anim_time * 60.0 + 120.0) * 6.0", "126")
    a.rot("ring_c", {0.0: (18, 90, 0)}, lerp="linear")
    a.pos_e("ring_c", "0", "136.0 + math.sin(query.anim_time * 60.0 + 240.0) * 6.0", "-124")
    a.rot_e("body", "-14.0 + math.sin(query.anim_time * 60.0) * 2.0", "0", "0")
    a.pos_e("body", "0", "math.sin(query.anim_time * 60.0) * 5.0", "0")
    a.rot("skull", {0.0: (-18, 0, 0)}, lerp="linear")
    for s in SIDES:
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, 32)}, s), lerp="linear")
        a.rot(f"fin_{s}_blade", keys_side({0.0: (0, -10, 12)}, s), lerp="linear")
    for i in range(1, 7):
        a.rot(f"tail_{i}", {0.0: (-4, 0, 0)}, lerp="linear")
    for lid in LIMB_IDS:          # phase II: mantis-like praying limbs
        s = LIMBS[lid][0]
        a.rot(f"limb_{lid}_femur", {0.0: mirror(-30, -25, 35, s)}, lerp="linear")
        a.rot(f"limb_{lid}_tibia", {0.0: mirror(-20, 0, -70, s)}, lerp="linear")
        a.rot(f"limb_{lid}_talon", {0.0: mirror(30, 0, -30, s)}, lerp="linear")
    a.fx(0.0, "prayer_glyphs", "core").fx(3.0, "prayer_glyphs", "core")
    out.append(a)

    # ---- stunned (prayer broken): lolling, rings wobbling erratically, heart exposed
    a = Anim(f"{NS}.stunned", 3.0, True)
    a.rot_e("body", "16.0 + math.sin(query.anim_time * 120.0) * 3.0", "0", "18.0 + math.sin(query.anim_time * 90.0) * 4.0")
    a.pos("body", {0.0: (0, -22, 0)}, lerp="linear")
    _open_plates(a, 0.0, 34)
    for n, k in (("a", 0), ("b", 70), ("c", 140)):
        a.rot_e(f"ring_{n}", f"math.sin(query.anim_time * 230.0 + {k}) * 12.0", f"math.cos(query.anim_time * 170.0 + {k}) * 10.0", "0")
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (16, 6, 0)}, s), lerp="linear")
        a.rot(f"fin_{s}", keys_side({0.0: (0, 0, -26)}, s), lerp="linear")
    for i in range(1, 7):
        a.rot(f"tail_{i}", {0.0: (-6, 0, 0)}, lerp="linear")
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        a.rot_e(f"limb_{lid}_femur", f"math.sin(query.anim_time * 140.0 + {stable(lid, 90)}) * 6.0", "0", f"{num(SG[s])} * -18.0")
    a.fx(0.0, "stun_sparks", "core").fx(1.5, "stun_sparks", "eyes")
    out.append(a)

    # ---- Predator Lunge: windup / dash / anchored
    a = Anim(f"{NS}.lunge_windup", 1.3, "hold_on_last_frame")
    a.pos("body", {0.0: (0, 0, 0), 1.0: (0, -18, 34), 1.3: (0, -20, 38)})
    a.rot("body", {0.0: (0, 0, 0), 1.0: (8, 0, 0)})
    a.rot("skull", {0.0: (0, 0, 0), 1.0: (12, 0, 0)})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 0.6: (26, 24, 0), 1.3: (28, 26, 0)}, s))
    for i in range(1, 7):
        a.rot(f"tail_{i}", {0.0: (0, 0, 0), 1.0: (10, 0, 0)})
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        front = lid.startswith("f")
        a.rot(f"limb_{lid}_femur", keys_side({0.0: (0, 0, 0), 1.0: (-14 if front else 10, -10, 26)}, s))
        a.rot(f"limb_{lid}_tibia", {0.0: (0, 0, 0), 1.0: (-18, 0, 0)})
    a.fx(0.1, "roar_wave", "jaw")
    out.append(a)
    a = Anim(f"{NS}.lunge", 0.7, "hold_on_last_frame")
    a.pos("body", {0.0: (0, -20, 38), 0.18: (0, -8, -52), 0.7: (0, -12, -30)})
    a.rot("body", {0.0: (8, 0, 0), 0.18: (-8, 0, 0), 0.7: (4, 0, 0)})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (28, 26, 0), 0.28: (30, 28, 0), 0.38: (2, 2, 0), 0.7: (6, 4, 0)}, s))
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        a.rot(f"limb_{lid}_femur", keys_side({0.0: (0, -10, 26), 0.2: (30, 30, 8), 0.7: (18, 18, 0)}, s))
        a.rot(f"limb_{lid}_tibia", {0.0: (-18, 0, 0), 0.2: (20, 0, 0), 0.7: (8, 0, 0)})
    a.fx(0.0, "lunge_trail", "core")
    out.append(a)
    a = Anim(f"{NS}.anchored", 1.6, True)
    a.pos("body", {0.0: (0, -34, -20)}, lerp="linear")
    a.rot_e("body", "6.0 + math.sin(query.anim_time * 225.0) * 2.0", "0", "math.sin(query.anim_time * 112.5) * 2.5")
    a.scl_e("sun", "1.3 + math.sin(query.anim_time * 450.0) * 0.08")
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        a.rot(f"limb_{lid}_femur", {0.0: mirror(10, 0, -6, s)}, lerp="linear")
        a.rot(f"limb_{lid}_tibia", {0.0: (16, 0, 0)}, lerp="linear")
        a.rot(f"limb_{lid}_talon", {0.0: (32, 0, 0)}, lerp="linear")
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (12, 6, 0)}, s), lerp="linear")
    a.fx(0.0, "heart_sparks", "core")
    out.append(a)

    # ---- Reaping Talons (loop, 1 s = two strikes; script strikes every 0.5 s)
    a = Anim(f"{NS}.talons", 1.0, True)
    for lid, t0 in (("fl", 0.0), ("fr", 0.5)):
        s = LIMBS[lid][0]
        keys = {t0: (0, 0, 0), t0 + 0.22: (-40, 0, 38), t0 + 0.4: (34, 0, -6), t0 + 0.5: (24, 0, 0)}
        if t0 > 0:
            keys = {0.0: (24, 0, 0), 0.1: (6, 0, 0), **keys}
        else:
            keys[1.0] = (0, 0, 0)
        a.rot(f"limb_{lid}_femur", keys_side(keys, s))
        tk = {t0: (0, 0, 0), t0 + 0.22: (-50, 0, 0), t0 + 0.4: (30, 0, 0), t0 + 0.5: (20, 0, 0)}
        if t0 > 0:
            tk = {0.0: (20, 0, 0), 0.1: (4, 0, 0), **tk}
        else:
            tk[1.0] = (0, 0, 0)
        a.rot(f"limb_{lid}_tibia", tk)
    a.rot_e("body", "math.sin(query.anim_time * 720.0) * 3.0", "0", "math.sin(query.anim_time * 360.0) * 5.0")
    a.fx(0.4, "talon_dust", "talon_fl").fx(0.9, "talon_dust", "talon_fr")
    out.append(a)

    # ---- Black Sun Nova: charge / release
    a = Anim(f"{NS}.nova_charge", 3.0, "hold_on_last_frame")
    a.rot("body", {0.0: (0, 0, 0), 2.6: (-18, 0, 0)})
    a.pos("body", {0.0: (0, 0, 0), 2.6: (0, 12, 0)})
    a.rot_e("root", "math.sin(query.anim_time * 1500.0) * query.anim_time * 0.6", "0", "math.cos(query.anim_time * 1300.0) * query.anim_time * 0.6")
    a.scl("sun", {0.0: 1.0, 2.8: 1.95})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 2.0: (30, 28, 0)}, s))
        for i in range(1, N_RIBS + 1):
            a.rot(f"rib_{s}{i}", keys_side({0.0: (0, 0, 0), 2.4: (0, 0, 14)}, s))
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        a.rot(f"limb_{lid}_femur", keys_side({0.0: (0, 0, 0), 2.4: (0, 0, 24)}, s))
    a.fx(0.2, "nova_gather", "core").fx(1.4, "nova_gather", "core")
    out.append(a)
    a = Anim(f"{NS}.nova_release", 1.2, "hold_on_last_frame")
    a.rot("body", {0.0: (-18, 0, 0), 0.12: (12, 0, 0), 1.2: (0, 0, 0)})
    a.scl("sun", {0.0: 1.95, 0.08: 0.6, 0.6: 1.15, 1.2: 1.0})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (30, 28, 0), 1.2: (0, 0, 0)}, s))
    a.fx(0.0, "core_flare", "core")
    out.append(a)

    # ---- Unhaloed stagger (phase II)
    a = Anim(f"{NS}.unhaloed", 2.0, True)
    a.rot_e("body", "12.0 + math.sin(query.anim_time * 180.0) * 3.0", "0", "-20.0 + math.sin(query.anim_time * 135.0) * 4.0")
    a.pos("body", {0.0: (0, -26, 0)}, lerp="linear")
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        a.rot_e(f"limb_{lid}_femur", f"math.sin(query.anim_time * 200.0 + {stable(lid, 120)}) * 8.0", "0", f"{num(SG[s])} * -22.0")
        a.rot(f"limb_{lid}_tibia", {0.0: (-24, 0, 0)}, lerp="linear")
    a.fx(0.0, "stun_sparks", "core")
    out.append(a)

    # ---- roar (phase II intimidation)
    a = Anim(f"{NS}.roar", 2.0, "hold_on_last_frame")
    a.rot("skull", {0.0: (0, 0, 0), 0.35: (-24, 0, 0), 1.6: (-20, 0, 0), 2.0: (0, 0, 0)})
    a.rot_e("neck_1", "0", "math.sin(query.anim_time * 900.0) * (query.anim_time < 1.6 ? 3.0 : 0.0)", "0")
    a.rot("maw", {0.0: (0, 0, 0), 0.35: (14, 0, 0), 1.6: (12, 0, 0), 2.0: (0, 0, 0)})
    a.rot("body", {0.0: (0, 0, 0), 0.4: (-8, 0, 0), 2.0: (0, 0, 0)})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 0.35: (34, 32, 0), 1.6: (30, 30, 0), 2.0: (0, 0, 0)}, s))
    for lid in ("fr", "fl"):
        s = LIMBS[lid][0]
        a.rot(f"limb_{lid}_femur", keys_side({0.0: (0, 0, 0), 0.4: (-20, 0, 34), 1.6: (-16, 0, 30), 2.0: (0, 0, 0)}, s))
    a.fx(0.35, "roar_wave", "jaw")
    out.append(a)
    return out


def _open_plates(a: Anim, t_open: float, angle: float, extra_shake=False):
    for i in range(1, N_PLATES + 1):
        for s in SIDES:
            if extra_shake:
                a.rot_e(f"plate_{s}{i}", "0", "0",
                        f"{num(SG[s])} * ({angle} + math.sin(query.anim_time * 1400.0 + {i * 60}) * (2.0 + query.anim_time * 4.0))")
            elif t_open > 0:
                a.rot(f"plate_{s}{i}", keys_side({0.0: (0, 0, 0), t_open * (0.6 + 0.08 * i): (0, 0, angle * 1.08), t_open + 0.2: (0, 0, angle)}, s))
            else:
                a.rot(f"plate_{s}{i}", keys_side({0.0: (0, 0, angle)}, s), lerp="linear")


# ----------------------------------------------------------------------------- transformation (9 s) & death (8 s)

def folded_limb_pose(lid):
    s = LIMBS[lid][0]
    return {
        f"limb_{lid}_femur": mirror(0, 0, 112, s),
        f"limb_{lid}_tibia": mirror(0, 0, -150, s),
        f"limb_{lid}_talon": mirror(0, 0, -100, s),
    }


def transform() -> Anim:
    a = Anim(f"{NS}.transform", 9.0, "hold_on_last_frame")
    # 0.0-1.5 shudder
    a.rot_e("root", "math.sin(query.anim_time * 1700.0) * math.min(query.anim_time, 1.5) * 0.9",
            "0", "math.cos(query.anim_time * 1500.0) * math.min(query.anim_time, 1.5) * 0.9")
    a.scl("sun", {0.0: 1.0, 0.4: 1.2, 0.6: 0.9, 0.9: 1.3, 1.2: 0.8, 1.5: 1.1, 6.0: 1.2, 6.5: 0.25, 6.65: 0.25,
                  7.0: 1.5, 7.6: 1.0})
    # 1.5-3.0 rings spin up, tumble and fly away (script swaps them for Seraph entities at 3.0 s)
    for n, (dx, dy, dz), tumble in (("a", (0, 300, 0), (420, 0, 0)), ("b", (-420, 160, -260), (0, 540, 0)),
                                    ("c", (420, 160, 300), (0, 0, 620))):
        a.rot(f"ring_{n}", {0.0: (0, 0, 0), 1.5: (0, 0, 0), 2.4: tuple(v * 0.6 for v in tumble), 3.0: tumble})
        a.pos(f"ring_{n}", {0.0: (0, 0, 0), 2.0: (0, 0, 0), 3.0: (dx, dy, dz)})
        a.scl(f"ring_{n}", {0.0: 1.0, 2.0: 1.1, 3.0: 0.3})
    # 2.5-4.0 armour plates blow off (script spawns falling hull plates at 3.9 s)
    for i in range(1, N_PLATES + 1):
        for s in SIDES:
            g = SG[s]
            t0 = 2.5 + (i % 3) * 0.15
            a.pos(f"plate_{s}{i}", {0.0: (0, 0, 0), t0: (0, 0, 0), 4.0: (-g * (90 + i * 12), 70 + i * 18, (i - 3) * 20)})
            a.rot(f"plate_{s}{i}", {0.0: (0, 0, 0), t0 - 0.4: (0, 0, g * 12), t0: (0, 0, g * 30),
                                     4.0: (g * 160 * (1 if i % 2 else -1), 90, g * 220)})
            a.scl(f"plate_{s}{i}", {0.0: 1.0, t0: 1.0, 4.0: 0.7})
    # 3.5-6.0 six limbs unfold out of the hull (front, mid, rear pairs staggered)
    for lid in LIMB_IDS:
        start = {"f": 3.5, "m": 4.0, "r": 4.5}[lid[0]]
        folded = folded_limb_pose(lid)
        for bone, fv in folded.items():
            mid = tuple(v * 0.35 for v in fv)
            over = tuple(-v * 0.08 for v in fv)
            a.rot(bone, {0.0: fv, start: fv, start + 0.55: mid, start + 0.95: over, start + 1.3: (0, 0, 0)})
    # 4.0-6.0 ribs spread, 7.5-9.0 skull rises and the jaw splits; end exactly on the P2 pose
    for s in SIDES:
        for i in range(1, N_RIBS + 1):
            end = P2_POSE[f"rib_{s}{i}"]
            a.rot(f"rib_{s}{i}", {0.0: (0, 0, 0), 4.0: (0, 0, 0), 5.2: mirror(0, 0, 22, s), 6.0: end, 9.0: end})
        endm = P2_POSE[f"mandible_{s}"]
        a.rot(f"mandible_{s}", {0.0: (0, 0, 0), 7.4: (0, 0, 0), 7.8: mirror(32, 30, 0, s), 8.6: mirror(26, 24, 0, s), 9.0: endm})
        for b in (f"fin_{s}", f"fin_{s}_blade", f"engine_{s}"):
            end = P2_POSE[b]
            a.rot(b, {0.0: (0, 0, 0), 4.5: (0, 0, 0), 6.0: tuple(v * 1.2 for v in end), 9.0: end})
    a.rot("skull", {0.0: (0, 0, 0), 7.3: (6, 0, 0), 7.8: (-26, 0, 0), 8.6: (-20, 0, 0), 9.0: P2_POSE["skull"]})
    a.pos("skull", {0.0: (0, 0, 0), 7.3: (0, 0, 0), 9.0: (0, -6, 0)})
    a.rot("maw", {0.0: (0, 0, 0), 7.4: (0, 0, 0), 7.8: (16, 0, 0), 9.0: P2_POSE["maw"]})
    a.pos("maw", {0.0: (0, 0, 0), 7.4: (0, 0, 0), 9.0: (0, -4, 0)})
    for i in range(1, 7):
        end = P2_POSE[f"tail_{i}"]
        a.rot(f"tail_{i}", {0.0: (0, 0, 0), 5.0: (0, 0, 0), 7.0: tuple(v * 1.3 for v in end), 9.0: end})
    for i in range(1, 5):
        a.rot(f"spire_{i}", {0.0: (0, 0, 0), 5.5: (0, 0, 0), 9.0: P2_POSE[f"spire_{i}"]})
    a.pos("body", {0.0: (0, 0, 0), 1.5: (0, 6, 0), 3.0: (0, 18, 0), 6.0: (0, 10, 0), 9.0: (0, -8, 0)})
    a.rot("body", {0.0: (0, 0, 0), 2.0: (-10, 0, 0), 4.0: (-16, 0, 0), 6.5: (-8, 0, 0), 7.8: (-12, 0, 0), 9.0: (0, 0, 0)})
    a.fx(0.0, "stun_sparks", "core").fx(1.6, "ring_spark", "ring_a").fx(2.6, "debris_burst", "core")
    a.fx(3.4, "debris_burst", "core").fx(6.5, "core_implode", "core").fx(6.65, "arrival_flash", "core")
    a.fx(7.8, "roar_wave", "jaw")
    a.sfx(7.7, "roar")
    return a


def death() -> Anim:
    a = Anim(f"{NS}.death", 8.0, "hold_on_last_frame")
    a.rot_e("root", "math.sin(query.anim_time * 1300.0) * (query.anim_time < 4.0 ? 1.4 : 0.4)", "0",
            "math.cos(query.anim_time * 1100.0) * (query.anim_time < 4.0 ? 1.4 : 0.4)")
    a.rot("body", {0.0: (0, 0, 0), 2.0: (-14, 0, 6), 4.0: (10, 0, 24), 6.0: (16, 0, 30), 8.0: (22, 0, 34)})
    a.pos("body", {0.0: (0, 0, 0), 2.0: (0, 8, 0), 4.5: (0, -30, 0), 8.0: (0, -70, 0)})
    a.scl("sun", {0.0: 1.0, 3.5: 2.1, 5.6: 2.3, 6.1: 0.05, 8.0: 0.01})
    for lid in LIMB_IDS:
        s = LIMBS[lid][0]
        k = (stable(lid, 5)) * 0.12
        fv = folded_limb_pose(lid)
        a.rot(f"limb_{lid}_femur", {0.0: (0, 0, 0), 0.5 + k: mirror(-20, 10, 30, s), 1.2 + k: mirror(16, -10, -10, s),
                                    2.0 + k: mirror(-10, 0, 20, s), 4.0: tuple(v * 0.6 for v in fv[f"limb_{lid}_femur"]),
                                    8.0: tuple(v * 0.55 for v in fv[f"limb_{lid}_femur"])})
        a.rot(f"limb_{lid}_tibia", {0.0: (0, 0, 0), 1.0 + k: (-30, 0, 0), 4.0: tuple(v * 0.55 for v in fv[f"limb_{lid}_tibia"]),
                                    8.0: tuple(v * 0.6 for v in fv[f"limb_{lid}_tibia"])})
    for s in SIDES:
        a.rot(f"mandible_{s}", keys_side({0.0: (0, 0, 0), 0.6: (34, 32, 0), 2.5: (30, 26, 0), 5.0: (20, 10, 0), 8.0: (24, 12, 0)}, s))
        for i in range(1, N_RIBS + 1):
            a.rot(f"rib_{s}{i}", keys_side({0.0: (0, 0, 0), 3.0: (0, 0, 12), 6.0: (0, 0, -4), 8.0: (0, 0, -8)}, s))
            a.scl(f"rib_{s}{i}", {0.0: 1.0, 6.0 + i * 0.25: 1.0, 6.4 + i * 0.25: 0.05})
    a.rot("skull", {0.0: (0, 0, 0), 0.6: (-28, 0, 0), 2.5: (-22, 0, 0), 5.0: (16, 0, 10), 8.0: (24, 0, 14)})
    for i in range(1, 7):
        a.rot(f"tail_{i}", {0.0: (0, 0, 0), 2.0: (14, 0, 0), 5.0: (-8, 6, 0), 8.0: (-12, 8, 0)})
        a.scl(f"tail_{i}", {0.0: 1.0, 6.2 + i * 0.2: 1.0, 6.6 + i * 0.2: 0.05})
    a.fx(0.0, "stun_sparks", "core").fx(1.5, "stun_sparks", "core").fx(3.0, "nova_gather", "core")
    a.fx(6.0, "core_implode", "core").fx(6.15, "arrival_flash", "core").fx(6.3, "debris_burst", "core")
    a.sfx(0.3, "roar")
    return a


# ----------------------------------------------------------------------------- controllers & client entity wiring

ACT_STATE_ANIMS = {
    "arrive": ["arrive"], "depart": ["depart"], "lance_charge": ["lance_charge"], "lance_fire": ["lance_fire"],
    "rite": ["rite"], "horizon": ["horizon"], "choir": ["choir"], "genuflect": ["genuflect", "vent_breathe"],
    "vent_flare": ["vent_flare"], "pray": ["pray"], "stunned": ["stunned"], "lunge_windup": ["lunge_windup"],
    "lunge": ["lunge"], "anchored": ["anchored"], "talons": ["talons"], "nova_charge": ["nova_charge"],
    "nova_release": ["nova_release"], "unhaloed": ["unhaloed"], "roar": ["roar"],
}


def controllers() -> List[Controller]:
    ph = Controller("controller.animation.sab.vesper.phase", "p1")
    p = "query.property('sab:phase')"
    ph.state("p1", ["idle_p1"], [("transform", f"{p} == 1"), ("p2", f"{p} == 2"), ("dying", f"{p} == 3")], blend=0.4)
    ph.state("transform", ["transform"], [("p2", f"{p} == 2"), ("dying", f"{p} == 3")], blend=0.3)
    ph.state("p2", ["pose_p2", "idle_p2"], [("dying", f"{p} == 3")], blend=0.25)
    ph.state("dying", [{"death": "1.0"}], [("p2", f"{p} == 2")], blend=0.4)

    act = Controller("controller.animation.sab.vesper.act", "idle")
    q = "query.property('sab:act')"
    names = [n for n in ACT if n != "idle"]
    act.state("idle", [], [(n, f"{q} == {ACT[n]}") for n in names], blend=0.45)
    for n in names:
        tr = [("idle", f"{q} == 0")] + [(m, f"{q} == {ACT[m]}") for m in names if m != n]
        act.state(n, ACT_STATE_ANIMS[n], tr, blend=0.35)
    return [ph, act]


def all_anims() -> List[Anim]:
    return [base(), idle_p1(), pose_p2(), idle_p2(), transform(), death()] + act_anims()


def short_name(full: str) -> str:
    return full.split(".")[-1]


ANIMATE = ["base", "phase_controller", "act_controller"]
