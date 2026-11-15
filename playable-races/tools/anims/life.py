"""Building blocks for layered, organic attachable motion.

Everything here is *stateless* Molang (a function of queries such as
q.life_time, q.modified_distance_moved, q.vertical_speed ...), so the result
is identical on every device, needs no variables that persist between frames
and survives the attachable being re-created whenever the race form changes.
Layers add up (rotation / position) or multiply (scale), exactly like the
client blends the attachable's animate list.

Conventions (Bedrock JSON space; see kit/geo.py): front = -Z, creature's right
= -X.  +rx tips the front down (a hanging limb swings back, an upward part
leans forward, a backward part lifts), +ry turns the front toward the
creature's right, +rz tilts the top toward +X (a hanging right limb swings
outward).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from anims.core import Anim, NS, n

Expr = Union[str, float, int, None]

# ----------------------------------------------------------------------------- query snippets
T = "q.life_time"
MOVE = "math.clamp(q.modified_move_speed, 0, 1)"              # 0 still .. 1 sprint
STILL = "(1 - math.clamp(q.modified_move_speed * 5, 0, 1))"   # 1 when standing
PH = "(q.modified_distance_moved * 38.17)"                    # stride phase, degrees (vanilla leg phase)
TCOS = "(math.cos(q.modified_distance_moved * 38.17) * q.modified_move_speed * 57.3)"  # vanilla variable.tcos0
SPR = "(q.is_sprinting ? 1 : 0)"
WALKING = "(q.is_sprinting ? 0 : 1)"
RISE = "math.clamp(q.vertical_speed / 7, 0, 1)"               # vertical_speed is m/s (vanilla fox pounce)
FALL = "math.clamp(-q.vertical_speed / 7, 0, 1)"
ATK = "math.sin(math.clamp(v.attack_time ?? 0, 0, 1) * 180)"  # player's public swing variable, 0..1..0
LOOK = "math.clamp(q.target_y_rotation, -70, 70)"             # head yaw relative to the body
TURN = "math.clamp(q.yaw_speed * 0.02, -1, 1)"                # bounded: units differ between sources
EMPTY_R = "(q.is_item_equipped(0) ? 0.2 : 1)"                 # arms move freely only with empty hands
EMPTY_L = "(q.is_item_equipped(1) ? 0.2 : 1)"
K = math.pi / 180.0

# Hot sub-expressions are computed once per frame in the attachable's pre_animation
# script and referenced as variables by every layer (see shared_vars / compact).
# Order matters: longer snippets that contain shorter ones come first.
SHARED = [
    (TCOS, "v.plr_tc"),
    (PH, "v.plr_ph"),
    (MOVE, "v.plr_mv"),
    (STILL, "v.plr_still"),
    (SPR, "v.plr_spr"),
    (WALKING, "v.plr_walk"),
]


def shared_vars() -> List[str]:
    return [
        "v.plr_ph = q.modified_distance_moved * 38.17;",
        "v.plr_tc = math.cos(v.plr_ph) * q.modified_move_speed * 57.3;",
        "v.plr_mv = math.clamp(q.modified_move_speed, 0, 1);",
        "v.plr_still = 1 - math.clamp(q.modified_move_speed * 5, 0, 1);",
        "v.plr_spr = q.is_sprinting ? 1 : 0;",
        "v.plr_walk = 1 - v.plr_spr;",
    ]


def compact(obj, extra: Sequence[Tuple[str, str]] = ()):
    """Replace shared snippets by their per-frame variables in every string of a JSON tree."""
    table = list(extra) + SHARED
    if isinstance(obj, str):
        for a, b in table:
            obj = obj.replace(a, b)
        return obj
    if isinstance(obj, list):
        return [compact(x, extra) for x in obj]
    if isinstance(obj, dict):
        return {k: compact(v, extra) for k, v in obj.items()}
    return obj


def S(freq: float, phase: float = 0.0, t: str = T) -> str:
    """Unit sine at `freq` Hz (Molang trig is in degrees)."""
    return f"math.sin({t} * {n(freq * 360)}{' + ' + n(phase) if phase else ''})"


def C(freq: float, phase: float = 0.0, t: str = T) -> str:
    return f"math.cos({t} * {n(freq * 360)}{' + ' + n(phase) if phase else ''})"


def SQ(freq: float, phase: float = 0.0, sharp: float = 4.0) -> str:
    """Soft square wave in [-1, 1]: quick moves between held poses (saccades, ear flicks)."""
    return f"math.clamp({S(freq, phase)} * {n(sharp)}, -1, 1)"


def BUMP(period: float, dur: float, off: float = 0.0) -> str:
    """0..1..0 half-sine pulse lasting `dur` s, once every `period` s."""
    m = f"math.mod({T}{' + ' + n(off) if off else ''}, {n(period)})"
    return f"({m} < {n(dur)} ? math.sin({m} * {n(180.0 / dur)}) : 0)"


def STEP(phase: float = 0.0) -> str:
    """sin(stride phase + phase)."""
    return f"math.sin({PH}{' + ' + n(phase) if phase else ''})"


def CSTEP(phase: float = 0.0) -> str:
    return f"math.cos({PH}{' + ' + n(phase) if phase else ''})"


def POS(e: str) -> str:
    return f"math.max(0, {e})"


def IMPACT(lag: float = 0.0, sharp: int = 8) -> str:
    """Sharp 0..1 spike at each footfall (|cos| peaks), optionally lagging."""
    return f"math.pow(math.abs({CSTEP(-lag)}), {sharp})"


def mul(c: float, e: Expr) -> Expr:
    if e is None or c == 0:
        return None
    if isinstance(e, (int, float)):
        return c * e
    if c == 1:
        return e
    return f"{n(c)} * ({e})"


def prod(*es: Expr) -> Expr:
    num = 1.0
    parts = []
    for e in es:
        if e is None:
            return None
        if isinstance(e, (int, float)):
            num *= e
        else:
            parts.append(f"({e})")
    if num == 0:
        return None
    if not parts:
        return num
    return " * ".join(([n(num)] if num != 1 else []) + parts)


def lin(pairs: Iterable[Tuple[float, Expr]]) -> Expr:
    """sum(c_i * e_i), skipping empty terms."""
    terms = [mul(c, e) for c, e in pairs]
    terms = [t for t in terms if t is not None and not (isinstance(t, (int, float)) and abs(t) < 1e-6)]
    if not terms:
        return None
    nums = sum(t for t in terms if isinstance(t, (int, float)))
    strs = [t for t in terms if isinstance(t, str)]
    if not strs:
        return nums
    out = " + ".join(f"({s})" for s in strs)
    return f"{out} + {n(nums)}" if abs(nums) > 1e-6 else out


def _join_sum(terms: List[Expr]) -> Union[str, float]:
    nums = sum(t for t in terms if isinstance(t, (int, float)))
    strs = [t for t in terms if isinstance(t, str)]
    if not strs:
        return round(nums, 4)
    if len(strs) == 1 and abs(nums) < 1e-6:
        return strs[0]
    out = " + ".join(f"({s})" for s in strs)
    return f"{out} + {n(nums)}" if abs(nums) > 1e-6 else out


def _join_prod(terms: List[Expr]) -> Union[str, float]:
    nums = 1.0
    strs = []
    for t in terms:
        if isinstance(t, (int, float)):
            nums *= t
        else:
            strs.append(t)
    if not strs:
        return round(nums, 4)
    if len(strs) == 1 and abs(nums - 1) < 1e-6:
        return strs[0]
    out = " * ".join(f"({s})" for s in strs)
    return f"{out} * {n(nums)}" if abs(nums - 1) > 1e-6 else out


# ----------------------------------------------------------------------------- expression layers

class Layer:
    """One animation built from summed Molang contributions per bone/channel."""

    def __init__(self, race: str, name: str, **kw):
        self.race, self.name, self.kw = race, name, kw
        self.ch: Dict[str, Dict[str, List[List[Expr]]]] = {}
        self.parts: List[tuple] = []

    def _axes(self, bone: str, ch: str) -> List[List[Expr]]:
        return self.ch.setdefault(bone, {}).setdefault(ch, [[], [], []])

    def _add(self, bone: str, ch: str, vals) -> "Layer":
        ax = self._axes(bone, ch)
        for i, e in enumerate(vals):
            if e is None:
                continue
            if ch != "scale" and isinstance(e, (int, float)) and e == 0:
                continue
            ax[i].append(e)
        return self

    def rot(self, bone: str, x: Expr = None, y: Expr = None, z: Expr = None) -> "Layer":
        return self._add(bone, "rot", (x, y, z))

    def pos(self, bone: str, x: Expr = None, y: Expr = None, z: Expr = None) -> "Layer":
        return self._add(bone, "pos", (x, y, z))

    def scale(self, bone: str, x: Expr = None, y: Expr = None, z: Expr = None) -> "Layer":
        return self._add(bone, "scale", (x, y, z))

    def uscale(self, bone: str, s: Expr) -> "Layer":
        return self._add(bone, "scale", (s, s, s))

    def particle(self, t: float, effect: str, locator: Optional[str] = None) -> "Layer":
        self.parts.append((t, effect, locator))
        return self

    def anim(self) -> Anim:
        a = Anim(f"animation.{NS}.{self.race}.{self.name}", **self.kw)
        for bone, chans in self.ch.items():
            out = {}
            for ch, axes in chans.items():
                if ch == "scale":
                    vec = [_join_prod(t) for t in axes]
                    if all(v == 1 for v in vec):
                        continue
                else:
                    vec = [_join_sum(t) for t in axes]
                    if all(v == 0 for v in vec):
                        continue
                out[ch] = vec
            if out:
                a.bone(bone, rot=out.get("rot"), pos=out.get("pos"), scale=out.get("scale"))
        for t, e, loc in self.parts:
            a.particle(t, e, loc)
        return a


# ----------------------------------------------------------------------------- keyframed layers

def _v3(v, ch: str) -> np.ndarray:
    if isinstance(v, (int, float)):
        return np.array([v, v, v], float) if ch == "scale" else np.array([0, 0, 0], float) + v
    return np.array(v, float)


def catmull(keys: Dict[float, np.ndarray], t: float) -> np.ndarray:
    ts = sorted(keys)
    if t <= ts[0]:
        return keys[ts[0]]
    if t >= ts[-1]:
        return keys[ts[-1]]
    i = max(k for k in range(len(ts)) if ts[k] <= t)
    t0, t1 = ts[i], ts[i + 1]
    a = (t - t0) / (t1 - t0)
    p1, p2 = keys[t0], keys[t1]
    p0 = keys[ts[i - 1]] if i > 0 else p1
    p3 = keys[ts[i + 2]] if i + 2 < len(ts) else p2
    a2, a3 = a * a, a * a * a
    return 0.5 * ((2 * p1) + (-p0 + p2) * a + (2 * p0 - 5 * p1 + 4 * p2 - p3) * a2 + (-p0 + 3 * p1 - 3 * p2 + p3) * a3)


class KeyLayer:
    """A keyframed animation whose contributions per bone/channel are summed
    (scale: multiplied) and written as Catmull-Rom keys."""

    def __init__(self, race: str, name: str, length: float, loop=False):
        self.race, self.name, self.length, self.loop = race, name, length, loop
        self.curves: Dict[Tuple[str, str], List[Dict[float, np.ndarray]]] = {}
        self.parts: List[tuple] = []

    def add(self, bone: str, ch: str, keys: Dict[float, object]) -> "KeyLayer":
        norm = {round(float(t), 4): _v3(v, ch) for t, v in keys.items()}
        self.curves.setdefault((bone, ch), []).append(norm)
        return self

    def rot(self, bone, keys):
        return self.add(bone, "rot", keys)

    def pos(self, bone, keys):
        return self.add(bone, "pos", keys)

    def scale(self, bone, keys):
        return self.add(bone, "scale", keys)

    def particle(self, t: float, effect: str, locator: Optional[str] = None) -> "KeyLayer":
        self.parts.append((t, effect, locator))
        return self

    def anim(self) -> Anim:
        a = Anim(f"animation.{NS}.{self.race}.{self.name}", loop=self.loop, length=self.length)
        by_bone: Dict[str, Dict[str, dict]] = {}
        for (bone, ch), lst in self.curves.items():
            times = sorted(set(t for k in lst for t in k))
            out = {}
            for t in times:
                if ch == "scale":
                    v = np.ones(3)
                    for k in lst:
                        v = v * catmull(k, t)
                else:
                    v = np.zeros(3)
                    for k in lst:
                        v = v + catmull(k, t)
                out[t] = {"post": [round(float(x), 3) for x in v], "lerp_mode": "catmullrom"}
            by_bone.setdefault(bone, {})[ch] = out
        for bone, chans in by_bone.items():
            a.bone(bone, rot=chans.get("rot"), pos=chans.get("pos"), scale=chans.get("scale"))
        for t, e, loc in self.parts:
            a.particle(t, e, loc)
        return a


# ----------------------------------------------------------------------------- whole-body motion

# Pitch of the player's own bone each group hangs from.  A child bone's position
# offset is applied in its parent's (rotated) frame, so an offset meant in body
# space has to be counter-rotated by the parent's swing (legs/arms) or look pitch (head).
PARENT_PITCH = {
    "r_leg_g": f"(1.4 * {TCOS})", "l_leg_g": f"(-1.4 * {TCOS})",
    "r_arm_g": f"(-{TCOS})", "l_arm_g": f"{TCOS}",
    "head_g": "q.target_x_rotation",
}


class Rig:
    """Where a race's parts attach, so whole-body motion (lean / roll / twist
    about the hips, vertical bob, lateral sway) moves every bound group
    coherently: the trunk rotates, and the head and arm groups (which hang from
    the player's own skeleton, not from the trunk) are translated by the
    same small-angle displacement."""

    def __init__(self, torso: str, hip: Sequence[float], attached: Sequence[Tuple[str, Sequence[float]]],
                 legs: Sequence[str] = ("r_leg_g", "l_leg_g"), tail: Optional[str] = "tail_g", leg_len: float = 12.0):
        self.torso = torso
        self.hip = np.array(hip, float)
        self.attached = [(b, np.array(p, float)) for b, p in attached]
        self.legs = list(legs)
        self.tail = tail
        self.leg_len = leg_len

    def upper(self) -> List[str]:
        return [self.torso] + [b for b, _ in self.attached] + ([self.tail] if self.tail else [])


def offset(ly: Layer, bone: str, dx: Expr, dy: Expr, dz: Expr) -> None:
    """Translate a group by a body-space offset, compensating its parent's pitch."""
    pitch = PARENT_PITCH.get(bone)
    if pitch is None or (dy is None and dz is None):
        ly.pos(bone, dx, dy, dz)
        return
    c, s = f"math.cos({pitch})", f"math.sin({pitch})"
    ly.pos(bone, dx,
           lin([(1.0, prod(dy, c) if dy is not None else None), (-1.0, prod(dz, s) if dz is not None else None)]),
           lin([(1.0, prod(dy, s) if dy is not None else None), (1.0, prod(dz, c) if dz is not None else None)]))


def body(ly: Layer, rig: Rig, lean: Expr = None, twist: Expr = None, roll: Expr = None,
         bob: Expr = None, sway: Expr = None) -> None:
    """lean (+ = forward), twist (+ = shoulders turn right), roll (+ = top tilts left),
    bob (+ = up, whole body incl. legs), sway (+ = hips shift left, feet stay planted)."""
    ly.rot(rig.torso, lean, twist, roll)
    for bone, p in rig.attached:
        dx, dy, dz = p - rig.hip
        offset(ly, bone,
               lin([(dz * K, twist), (dy * K, roll)]),
               lin([(-dx * K, roll), (dz * K, lean)]),
               lin([(-dy * K, lean), (-dx * K, twist)]))
    if bob is not None:
        for b in rig.upper() + rig.legs:
            offset(ly, b, None, bob, None)
    if sway is not None:
        for b in rig.upper():
            ly.pos(b, sway, None, None)
        for lg in rig.legs:
            ly.pos(lg, sway, None, None)
            ly.rot(lg, None, None, mul(1.0 / (rig.leg_len * K), sway))


def body_keys(kl: KeyLayer, rig: Rig, keys: Dict[float, dict]) -> None:
    """Keyframed version of body(): keys = {t: {"lean":, "twist":, "roll":, "bob":, "sway":}}."""
    tor, bob_k, sway_k = {}, {}, {}
    att = {b: {} for b, _ in rig.attached}
    for t, d in keys.items():
        L, Y, R = d.get("lean", 0.0), d.get("twist", 0.0), d.get("roll", 0.0)
        tor[t] = (L, Y, R)
        for b, p in rig.attached:
            dx, dy, dz = p - rig.hip
            att[b][t] = ((Y * dz + R * dy) * K, (-R * dx + L * dz) * K, (-L * dy - Y * dx) * K)
        bob_k[t] = d.get("bob", 0.0)
        sway_k[t] = d.get("sway", 0.0)
    kl.rot(rig.torso, tor)
    for b, k in att.items():
        kl.pos(b, k)
    if any(abs(v) > 1e-6 for v in bob_k.values()):
        for b in rig.upper() + rig.legs:
            kl.pos(b, {t: (0, v, 0) for t, v in bob_k.items()})
    if any(abs(v) > 1e-6 for v in sway_k.values()):
        for b in rig.upper():
            kl.pos(b, {t: (v, 0, 0) for t, v in sway_k.items()})
        for lg in rig.legs:
            kl.pos(lg, {t: (v, 0, 0) for t, v in sway_k.items()})
            kl.rot(lg, {t: (0, 0, v / (rig.leg_len * K)) for t, v in sway_k.items()})


def stride(ly: Layer, keep: Expr, legs=("r_leg_g", "l_leg_g")) -> None:
    """Scale the player's own leg swing down to `keep` (0..1) by counter-rotating the leg groups."""
    c = lin([(1.0, 1.0), (-1.0, keep)]) if isinstance(keep, str) else 1.0 - keep
    ly.rot(legs[0], prod(-1.4, c, TCOS))
    ly.rot(legs[1], prod(1.4, c, TCOS))


def arm_swing(ly: Layer, keep: float, arms=("r_arm_g", "l_arm_g")) -> None:
    """Scale the player's own arm swing down to `keep` (only while that hand is empty)."""
    ly.rot(arms[0], prod(1.0 - keep, TCOS, EMPTY_R))
    ly.rot(arms[1], prod(-(1.0 - keep), TCOS, EMPTY_L))


def pendulum_bob(keep: float, leg_len: float, gain: float = 1.0) -> str:
    """Hip drop that keeps both feet on the ground while the legs swing by keep * vanilla."""
    return f"-{n(leg_len * gain)} * (1 - math.cos({n(1.4 * keep)} * {TCOS}))"


def fidget_controller(race: str, picks: Sequence[Tuple[str, str]], wait: str = "fidget_wait") -> dict:
    """Idle-fidget state machine without persistent variables: a timer animation
    runs while standing; when it finishes one fidget is picked pseudo-randomly
    (q.life_time), any movement / fall / hit cancels back to the timer."""
    moving = ("q.modified_move_speed > 0.04 || !q.is_on_ground || q.is_in_water || q.hurt_time > 0 || q.is_sneaking"
              " || q.is_riding || q.is_sleeping || q.is_gliding")
    states = {
        "wait": {"animations": [wait],
                 "transitions": [{"moving": moving}] + [{name: f"q.all_animations_finished && ({cond})"} for name, cond in picks]
                 + [{"rest": "q.all_animations_finished"}]},
        "moving": {"transitions": [{"wait": "!(" + moving + ")"}]},
        "rest": {"animations": ["fidget_rest"],
                 "transitions": [{"moving": moving}, {"wait": "q.all_animations_finished"}]},
    }
    for name, _ in picks:
        states[name] = {"animations": [name], "blend_transition": 0.3,
                        "transitions": [{"moving": moving}, {"wait": "q.all_animations_finished"}]}
    states["moving"]["blend_transition"] = 0.2
    return {f"controller.animation.{NS}.{race}.fidget": {"initial_state": "wait", "states": states}}


def landing_controller(race: str, hard_speed: float = -13.0, soft_speed: float = -5.5) -> dict:
    """ground -> air -> (falling | falling_hard) -> land / land_hard.  Small hops
    and stepping down a block do not trigger the squash."""
    air = "!q.is_on_ground && !q.is_in_water"
    return {f"controller.animation.{NS}.{race}.landing": {
        "initial_state": "ground",
        "states": {
            "ground": {"transitions": [{"air": air}]},
            "air": {"transitions": [{"falling_hard": f"q.vertical_speed < {n(hard_speed)}"},
                                    {"falling": f"q.vertical_speed < {n(soft_speed)}"},
                                    {"ground": "q.is_on_ground || q.is_in_water"}]},
            "falling": {"transitions": [{"falling_hard": f"q.vertical_speed < {n(hard_speed)}"},
                                        {"land": "q.is_on_ground"}, {"ground": "q.is_in_water"}]},
            "falling_hard": {"transitions": [{"land_hard": "q.is_on_ground"}, {"ground": "q.is_in_water"}]},
            "land": {"animations": ["land"], "transitions": [{"air": air}, {"ground": "q.all_animations_finished"}]},
            "land_hard": {"animations": ["land_hard"], "transitions": [{"air": air}, {"ground": "q.all_animations_finished"}]},
        }}}


def wait_anim(race: str, name: str, length: float) -> Anim:
    a = Anim(f"animation.{NS}.{race}.{name}", loop=False, length=length)
    a.bone("head_g", rot=[0, 0, 0])
    return a
