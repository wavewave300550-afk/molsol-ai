"""
Nomos - rig animation.

Locomotion: a deliberate lateral-sequence walk (one divider-leg at a time, three
always planted), driven by distance travelled; turning steps are driven by the
body's yaw. Leg poses for raising / lowering the plane table are solved with
two-link inverse kinematics here, so the steel points stay where they stand.

The compass is four nested rings ("indicators"). In Phase I they tumble like an
armillary; in Phase II each one lies flat above its own map sheet and its
needle points along a world bearing supplied by the script (properties
abm:q1..q4, eight steps of 45 degrees).

Attack keyframes come from shared/nomos.timings.json - the same beats the
script uses for telegraphs and hits.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from kit import molang as M
from kit.anim import Anim, ClientEntity, Controller, combine
from kit.molang import E, cond, mod, prop, q, sin, cos, v

A = "animation.abm.nomos."
LEGS = [("fl", 1, -1), ("fr", -1, -1), ("bl", 1, 1), ("br", -1, 1)]          # tag, x sign, z sign
SEQ = {"bl": 0.0, "fl": 0.25, "br": 0.5, "fr": 0.75}                       # lateral sequence
FOLD = (68.0, -136.0, 136.0)
THIGH, SHANK = 30.0, 85.5
E1, REL = 50.0, -134.0                                                      # bind: thigh elevation, knee angle
SCRIBE_BIND = (48.0, -10.0, 15.0)
SHEETS = ("fl", "fr", "bl", "br")
# where each indicator rests in Phase II, relative to the compass hub (geo units): above its own sheet
IND_HOME = {1: (33.0, -3.0, 34.5), 2: (-33.0, -3.0, 34.5), 3: (33.0, -3.0, 57.5), 4: (-33.0, -3.0, 57.5)}


def sec(ticks: float) -> float:
    return round(ticks / 20.0, 4)


# --------------------------------------------------------------------------- pose helpers

def _leg_ik(drop: float, spread: float = 0.0) -> Tuple[float, float]:
    """Thigh / shank offsets (degrees, left side) that keep the foot planted when the hip
    moves down by `drop` (negative = body rises) and the foot is `spread` further out."""
    x0 = THIGH * math.cos(math.radians(E1)) + SHANK * math.cos(math.radians(E1 + REL))
    h0 = THIGH * math.sin(math.radians(E1)) + SHANK * math.sin(math.radians(E1 + REL))
    x, h = x0 + spread, h0 + drop
    d = min(THIGH + SHANK - 0.5, max(SHANK - THIGH + 0.5, math.hypot(x, h)))
    knee = math.degrees(math.acos((THIGH ** 2 + SHANK ** 2 - d * d) / (2 * THIGH * SHANK)))     # interior angle
    base = math.degrees(math.atan2(h, x))
    alpha = math.degrees(math.acos((THIGH ** 2 + d * d - SHANK ** 2) / (2 * THIGH * d)))
    e1 = base + alpha                                                                              # knee above the line
    rel = -(180.0 - knee)
    return -(e1 - E1), -(rel - REL)


def stance(drop: float = 0.0, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0, fwd: float = 0.0,
           spread: float = 0.0, per_leg: Dict[str, float] = None) -> Dict[str, dict]:
    """Lower (drop > 0) or raise the table; legs are re-solved so the points stay planted."""
    pose: Dict[str, dict] = {"body": {"pos": [0, -drop, -fwd], "rot": [pitch, yaw, roll]}}
    for tag, sx, _ in LEGS:
        d = drop + (per_leg or {}).get(tag, 0.0)
        a, b = _leg_ik(d, spread)
        pose[f"leg_{tag}_a"] = {"rot": [0, 0, sx * a]}
        pose[f"leg_{tag}_b"] = {"rot": [0, 0, sx * b]}
    return pose


def scribe(tag: str, ta: float, tb: float, tc: float, yaw: float = 0.0) -> Dict[str, dict]:
    """Ruling-pen arm from absolute segment angles (0 = hanging, 90 = pointing forward)."""
    side = 1 if tag == "l" else -1
    return {
        f"scribe_{tag}_a": {"rot": [SCRIBE_BIND[0] - ta, -yaw * side, 0]},
        f"scribe_{tag}_b": {"rot": [-(tb - ta) - (SCRIBE_BIND[0] - SCRIBE_BIND[1]), 0, 0]},
        f"scribe_{tag}_c": {"rot": [-(tc - tb) + (SCRIBE_BIND[2] - SCRIBE_BIND[1]), 0, 0]},
    }


def scribes(ta, tb, tc, yaw=0.0) -> Dict[str, dict]:
    return {**scribe("l", ta, tb, tc, yaw), **scribe("r", ta, tb, tc, yaw)}


def sheet(tag: str, openness: float, lift: float = 0.0) -> Dict[str, dict]:
    """Unfold one map sheet: 0 = pleated, 1 = flat. `lift` tilts the whole sheet up from its hinge."""
    sx = 1 if tag.endswith("l") else -1
    out = {}
    for i in range(3):
        extra = -lift if i == 0 else 0.0
        out[f"map_{tag}_{i + 1}"] = {"rot": [0, 0, sx * (-FOLD[i] * openness + extra)]}
    return out


def sheets(fl=0.0, fr=0.0, bl=0.0, br=0.0, lift=0.0) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for tag, o in zip(SHEETS, (fl, fr, bl, br)):
        out.update(sheet(tag, o, lift))
    return out


def merge(*poses: Dict[str, dict]) -> Dict[str, dict]:
    return combine(*poses)


IND_SPAN = {1: 1.0, 2: 1.22, 3: 1.55, 4: 2.2}


def indicators_out(frac: float = 1.0) -> Dict[str, dict]:
    """The four rings leave the hub for their sheets and lie flat."""
    out = {}
    for k, (x, y, z) in IND_HOME.items():
        # nested rings are different sizes on the hub; as separate indicators they open to a similar span
        s = 1 + (IND_SPAN[k] - 1) * frac
        out[f"ind_{k}"] = {"pos": [x * frac, y * frac, z * frac], "rot": [90 * frac, 0, 0], "scale": [s, s, s]}
    return out


P2_STANCE = stance(drop=-14)
P2_POSE = merge(P2_STANCE, sheets(1, 1, 1, 1, lift=5), indicators_out(1.0), scribes(64, 30, 66, yaw=26),
                {"neck": {"rot": [14, 0, 0]}, "plumb_line": {"pos": [0, 0, 0]}})


# --------------------------------------------------------------------------- client entity

def client_entity() -> ClientEntity:
    ce = ClientEntity("abm:nomos", "geometry.abm.nomos", "textures/entity/abm/nomos")
    ce.materials = {"default": "entity_alphatest", "glow": "entity_emissive_alpha", "glass": "entity_alphablend"}
    ce.render_controllers = ["controller.render.abm.layered"]
    ce.var("p2", prop("abm:phase").eq(2))
    ce.var("gait", q("modified_distance_moved") * 0.9)
    ce.var("turn", (q("body_y_rotation") + 3600) / 60.0)
    ce.var("go", M.clamp(q("modified_move_speed") * 4, 0, 1))
    for tag, _, _ in LEGS:
        ce.var(f"w_{tag}", mod(v("gait") + SEQ[tag], 1))
        ce.var(f"t_{tag}", mod(v("turn") + SEQ[tag], 1))
    return ce


def stroke(p: E, duty) -> E:
    duty = E.of(duty)
    return cond(p.lt(duty), 1 - p * 2 / duty, (p - duty) * 2 / (1 - duty) - 1)


def lift(p: E, duty) -> E:
    duty = E.of(duty)
    return cond(p.lt(duty), 0, sin((p - duty) / (1 - duty) * 180))


# --------------------------------------------------------------------------- always-on layers

def build_base() -> List[Anim]:
    lt = q("life_time")
    go, gait = v("go"), v("gait")
    DUTY = 0.78

    idle = Anim(A + "idle", loop=True)
    idle.set("body", "pos", [0, sin(lt * 60) * 0.5, 0])
    idle.rot("neck", sin(lt * 40) * 3, sin(lt * 23) * 7, 0)
    idle.rot("scope_base", 0, sin(lt * 30) * 42, 0).rot("scope", sin(lt * 47) * 7, 0, 0)       # sweeping a horizon
    idle.pos("level_bubble_glow", sin(lt * 60) * 1.6, 0, 0)
    idle.rot("plumb_line", sin(lt * 80) * 4, 0, cos(lt * 80) * 3)
    idle.rot("protractor", 0, 0, sin(lt * 35) * 1.5)
    for tag, sx in (("l", 1), ("r", -1)):
        # the pens keep testing the ground: a tap, a short stroke, a lift
        idle.rot(f"scribe_{tag}_a", sin(lt * 45 + 90 * sx) * 2.5, sin(lt * 31 + 40 * sx) * 3 * sx, 0)
        idle.rot(f"scribe_{tag}_c", M.mmax(0, sin(lt * 90 + 110 * sx)) * -7, 0, 0)
    for tag, sx, sz in LEGS:
        idle.rot(f"map_{tag}_2", 0, 0, sin(lt * 50 + 60 * sz) * 2.5 * sx)
        idle.rot(f"map_{tag}_3", 0, 0, sin(lt * 50 + 60 * sz - 70) * 3.5 * sx)
    for i in (1, 5):
        idle.rot(f"spine_{i}", 0, sin(lt * 27 + i * 40) * 1.2, 0)

    walk = Anim(A + "walk", loop=True)
    turn = Anim(A + "turn", loop=True)
    for tag, sx, _ in LEGS:
        pw, pt = v(f"w_{tag}"), v(f"t_{tag}")
        walk.rot(f"leg_{tag}", 0, stroke(pw, DUTY) * 14 * sx, 0)
        walk.rot(f"leg_{tag}_a", 0, 0, lift(pw, DUTY) * 9 * -sx)
        walk.rot(f"leg_{tag}_b", 0, 0, lift(pw, DUTY) * 7 * sx)
        turn.rot(f"leg_{tag}", 0, stroke(pt, 0.75) * 22.5, 0)
        turn.rot(f"leg_{tag}_a", 0, 0, lift(pt, 0.75) * 8 * -sx)
        turn.rot(f"leg_{tag}_b", 0, 0, lift(pt, 0.75) * 6 * sx)
    # the table stays level like an instrument should; everything hung from it swings a beat late
    walk.set("body", "pos", [0, sin(gait * 1440) * 0.35 * go, 0])
    walk.set("body", "rot", [0, 0, sin(gait * 360 + 45) * 1.1 * go])
    walk.rot("spine_1", 0, sin(gait * 360) * 2.2 * go, 0)
    walk.rot("spine_4", 0, sin(gait * 360 - 120) * 1.6 * go, 0).rot("spine_5", 0, sin(gait * 360 - 170) * 2.4 * go, 0)
    walk.rot("plumb_line", sin(gait * 360 - 90) * 9 * go, 0, sin(gait * 720) * 3 * go)
    walk.rot("plumb_bob", sin(gait * 360 - 150) * 6 * go, 0, 0)
    walk.rot("head", 0, 0, sin(gait * 360 + 100) * -1.2 * go)
    for tag, sx, sz in LEGS:
        walk.rot(f"map_{tag}_1", 0, 0, sin(gait * 360 + 70 * sz) * 3.2 * go)
        walk.rot(f"map_{tag}_3", 0, 0, sin(gait * 360 + 70 * sz - 90) * 4.5 * go)
    for tag, sx in (("l", 1), ("r", -1)):
        walk.rot(f"scribe_{tag}_a", sin(gait * 360 + 90 * sx) * 5 * go, 0, 0)
        walk.rot(f"scribe_{tag}_c", sin(gait * 360 + 90 * sx - 60) * -8 * go, 0, 0)

    # Phase I: the armillary tumbles - four rings on four different axes and rates
    spin = Anim(A + "compass_spin", loop=True)
    spin.rot("ind_1", 0, 0, lt * 14)
    spin.rot("ind_2", 0, lt * 37, 0)
    spin.rot("ind_3", lt * -52, 0, 0)
    spin.rot("ind_4", lt * 23, lt * -81, 0)
    for k, (rate, amp) in enumerate(((70, 25), (95, 40), (120, 55), (160, 80)), 1):
        spin.rot(f"ind_{k}_needle", 0, 0, sin(lt * rate + k * 50) * amp)
    spin.scale("ind_4_tip_glow", 1 + sin(lt * 300) * 0.25)

    # Phase II: stance, open canopy, one indicator above each sheet
    hold = Anim(A + "p2_pose", loop=True)
    for b, ch in P2_POSE.items():
        for c, val in ch.items():
            hold.set(b, c, val)
    comp = Anim(A + "p2_compass", loop=True)
    for k in range(1, 5):
        # needle bearing = world theta (property * 45 degrees); the ring itself keeps a slow drift
        comp.rot(f"ind_{k}_needle", 0, 0, 90 - prop(f"abm:q{k}") * 45 + q("body_y_rotation"))
        comp.rot(f"ind_{k}", 0, sin(lt * (40 + k * 7) + k * 90) * 6, 0)
        comp.set(f"ind_{k}", "pos", [0, sin(lt * (90 + k * 11) + k * 70) * 1.2, 0])
        comp.scale(f"ind_{k}_tip_glow", 1 + sin(lt * 260 + k * 90) * 0.3)
    for tag, sx, sz in LEGS:
        comp.rot(f"map_{tag}_1", 0, 0, sin(lt * 70 + 90 * sz) * 2.5 * sx)
        comp.rot(f"map_{tag}_3", 0, 0, sin(lt * 70 + 90 * sz - 80) * 5 * sx)

    steps = Anim(A + "footfalls", length=0.8, loop=True)
    steps.sound(0.0, "step").sound(0.4, "step")
    return [idle, walk, turn, spin, hold, comp, steps]


# --------------------------------------------------------------------------- attacks

def meridian(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    end = sec(t["end"])
    a = Anim(A + f"meridian_p{phase}", length=end, loop="hold")
    ready_r = scribe("r", 70, 30, 20, yaw=-6)
    reach_r = scribe("r", 96, 80, 62, yaw=-2)
    ready_l = scribe("l", 70, 30, 20, yaw=-6)
    reach_l = scribe("l", 96, 80, 62, yaw=-2)
    if phase == 1:
        d1, h1, d2, h2 = sec(t["draw1"]), sec(t["hit1"]), sec(t["draw2"]), sec(t["hit2"])
        lean = stance(drop=6, pitch=9)
        jolt = stance(drop=-3, pitch=-7)
        side = scribe("l", 76, 60, 50, yaw=62)
        side_end = scribe("l", 76, 60, 50, yaw=-30)
        a.poses([(0, {}), (d1 + 0.15, merge(ready_r, stance(drop=2)), "out"), (h1 - 0.25, merge(reach_r, lean), "inout"),
                 (h1, merge(scribe("r", 60, 10, -10), jolt), "snap"), (d2 + 0.1, merge(side, stance(drop=4, pitch=4)), "out"),
                 (h2 - 0.25, merge(side_end, stance(drop=5, pitch=6, roll=-4)), "inout"),
                 (h2, merge(scribe("l", 60, 10, -10), jolt), "snap"), (end - 0.3, {}, "inout"), (end, {})])
        a.sound(d1, "scribe").sound(h1, "incision").sound(d2, "scribe").sound(h2, "incision")
        a.particle(d1 + 0.3, "ink", "nib_r").particle(d2 + 0.3, "ink", "nib_l").particle(h1, "spark", "compass_front")
    else:
        frames = [(0, {})]
        for i in range(t["count"]):
            mark = sec(t["draw1"] + i * t["gap"])
            hit = sec(t["hit1"] + i * t["gap"])
            tag = "r" if i % 2 == 0 else "l"
            ready, reach = (ready_r, reach_r) if tag == "r" else (ready_l, reach_l)
            frames += [(mark + 0.1, merge(ready, stance(drop=1)), "out"), (mark + 0.5, merge(reach, stance(drop=4, pitch=6)), "out")]
            a.sound(mark, "scribe").sound(hit, "incision").particle(mark + 0.3, "ink", f"nib_{tag}")
        frames += [(end - 0.4, stance(drop=-2, pitch=-4), "inout"), (end, {}, "inout")]
        a.poses(frames)
    return [a]


def shear(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    start, dur, end = sec(t["start"]), sec(t["duration"]), sec(t["end"])
    a = Anim(A + f"shear_p{phase}", length=end, loop="hold")
    wide = merge(scribes(84, 70, 60, yaw=78), stance(drop=-4, pitch=-5), {"neck": {"rot": [-12, 0, 0]}})
    shut = merge(scribes(84, 70, 60, yaw=4), stance(drop=5, pitch=7), {"neck": {"rot": [8, 0, 0]}})
    frames = [(0, {}), (start - 0.3, wide, "out"), (start, wide, "linear"), (start + dur, shut, "linear")]
    a.sound(0.1, "calipers").sound(start, "shear")
    if phase == 2:
        s2 = sec(t["start2"])
        # second closing, at right angles: one pen ahead, one behind
        cross = merge(scribe("l", 110, 100, 96, yaw=10), scribe("r", -30, -40, -50, yaw=10), stance(drop=-4))
        frames = [(0, {}), (start - 0.3, wide, "out"), (start, wide, "linear"), (s2 - 0.1, shut, "linear"),
                  (s2 + 0.3, cross, "out"), (s2 + dur, merge(scribes(40, 20, 10, yaw=4), stance(drop=5, pitch=7)), "linear")]
        a.sound(s2, "shear")
    frames += [(end - 0.4, stance(drop=1), "inout"), (end, {}, "inout")]
    a.poses(frames)
    return [a]


def borders(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    mark, active, end = sec(t["mark"]), sec(t["active"]), sec(t["end"])
    a = Anim(A + f"borders_p{phase}", length=end, loop="hold")
    up = merge(scribes(120, 130, 140, yaw=30), stance(drop=-6, pitch=-8), {"plumb_line": {"rot": [26, 0, 0]}})
    stab = merge(scribes(40, 16, 2, yaw=22), stance(drop=9, pitch=8), {"plumb_line": {"pos": [0, -18, 0], "rot": [-8, 0, 0]}})
    hold = merge(scribes(44, 18, 4, yaw=22), stance(drop=7, pitch=6), {"plumb_line": {"pos": [0, -18, 0]}})
    a.poses([(0, {}), (mark, up, "out"), (mark + 0.2, stab, "snap"), (active - 0.15, hold, "linear"),
             (active, merge(scribes(60, 40, 20, yaw=40), stance(drop=-2, pitch=-5)), "snap"), (end - 0.3, {}, "inout"), (end, {})])
    a.sound(mark + 0.2, "border_stamp").sound(active, "border_set")
    a.particle(mark + 0.2, "ink", "nib_l").particle(mark + 0.2, "ink", "nib_r").particle(mark + 0.2, "ink", "plumb")
    return [a]


def gate(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    end = sec(t["end"])
    a = Anim(A + f"gate_p{phase}", length=end, loop="hold")
    tuck = merge(stance(drop=20, spread=-8), scribes(30, 120, 20, yaw=-10), {"neck": {"rot": [40, 0, 0]},
                 "plumb_line": {"rot": [50, 0, 0]}})
    slam = merge(stance(drop=10, pitch=6, spread=6), scribes(60, 30, 10, yaw=50))
    jumps = [(t["fold"], t["relocate"], t["strike"])]
    if phase == 2:
        jumps.append((t["fold2"], t["relocate2"], t["strike2"]))
    frames = [(0, {})]
    scale = [(0.0, [1, 1, 1])]
    for fold, reloc, strike in jumps:
        f, r, s = sec(fold), sec(reloc), sec(strike)
        frames += [(f - 0.45, merge(stance(drop=-5, pitch=-6), scribes(100, 110, 120, yaw=20)), "out"), (f, tuck, "in"),
                   (r + 0.05, tuck, "linear"), (s, slam, "snap"), (s + 0.5, stance(drop=2), "out")]
        # Preparation: the whole creature folds flat like a closed map, then to a line, then is gone ...
        scale += [(f - 0.05, [1, 1, 1], "linear"), (f + 0.3, [0.06, 1, 1], "in"), (r - 0.12, [0.06, 0.05, 1], "in"),
                  (r - 0.02, [0.02, 0.02, 0.02], "linear"),
                  # ... arrival: a line, a sheet, a sovereign
                  (r + 0.05, [0.06, 0.05, 1], "linear"), (r + 0.16, [0.06, 1, 1], "out"), (s - 0.02, [1, 1, 1], "out")]
        a.sound(f - 0.4, "gate_ready").sound(f, "gate_fold").sound(r + 0.03, "gate_unfold").sound(s, "gate_arrive")
        a.particle(f + 0.1, "flake", "core").particle(s, "flake", "core").particle(s, "spark", "compass_front")
    frames += [(end - 0.3, {}, "inout"), (end, {})]
    a.poses(frames)
    a.track("root", "scale", scale + [(end, [1, 1, 1], "linear")])
    return [a]


def darts(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    end = sec(t["end"])
    a = Anim(A + f"darts_p{phase}", length=end, loop="hold")
    brace = merge(stance(drop=5, pitch=-10), scribes(-20, 30, 70, yaw=24), {"neck": {"rot": [-22, 0, 0]}})
    volleys = [t["lock"]] + ([t["lock2"]] if phase == 2 else [])
    last = sec(volleys[-1] + 3 * t["interval"] + t["warn"])
    a.poses([(0, {}), (sec(t["appear"]) + 0.4, brace, "out"), (last + 0.2, brace, "linear"), (end - 0.2, {}, "inout"), (end, {})])
    a.sound(sec(t["appear"]), "dart_spin")
    for k in range(1, 5):
        keys_pos = [(0.0, [0, 0, 0])]
        keys_scale = [(0.0, [1, 1, 1])]
        for lock0 in volleys:
            lock = sec(lock0 + (k - 1) * t["interval"])
            fire = lock + sec(t["warn"])
            # lock: the ring snaps rigid and swells; launch: it recoils along its axis
            keys_scale += [(lock - 0.05, [1, 1, 1], "linear"), (lock + 0.05, [1.22, 1.22, 1.22], "snap"), (fire, [1.1, 1.1, 1.1], "linear"),
                           (fire + 0.3, [1, 1, 1], "out")]
            kick = [0, 0, 5] if phase == 1 else [0, -5, 0]
            keys_pos += [(fire - 0.03, [0, 0, 0], "linear"), (fire + 0.05, kick, "snap"), (fire + 0.4, [0, 0, 0], "out")]
            a.sound(lock, "dart_lock").sound(fire, "dart_fire")
            a.particle(fire, "spark", f"needle_{k}")
        a.track(f"ind_{k}", "scale", keys_scale + [(end, [1, 1, 1], "linear")])
        a.track(f"ind_{k}", "pos", keys_pos + [(end, [0, 0, 0], "linear")])
    return [a]


def folded(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    end = sec(t["end"])
    a = Anim(A + f"folded_p{phase}", length=end, loop="hold")
    frames = [(0, {})]
    n = t["count"]
    for i in range(n):
        mark = sec(t["mark"] + i * t["interval"])
        hit = sec(t["hit"] + i * t["interval"])
        left = i % 2 == 0
        if phase == 1:
            # one side of the country is unfolded over the marked corridors, then snapped shut on them
            opened = merge(sheets(fl=0.75 if left else 0, bl=0.75 if left else 0, fr=0 if left else 0.75, br=0 if left else 0.75),
                           stance(drop=-3, roll=6 if left else -6))
            shut = merge(sheets(), stance(drop=5, roll=-3 if left else 3))
        else:
            # the canopy is already open: front and rear pairs rear up and slap down in turn
            opened = merge(sheet("fl" if left else "bl", 0, lift=34), sheet("fr" if left else "br", 0, lift=34),
                           stance(drop=-3, pitch=-5 if left else 5))
            shut = merge(sheet("fl" if left else "bl", 0, lift=-8), sheet("fr" if left else "br", 0, lift=-8),
                         stance(drop=4, pitch=4 if left else -4))
        frames += [(mark + 0.35, opened, "out"), (hit - 0.12, opened, "linear"), (hit + 0.03, shut, "snap")]
        a.sound(mark, "unfold").sound(hit, "fold_slam")
        a.particle(hit, "flake", "sheet_fl" if left else "sheet_fr").particle(hit, "flake", "sheet_bl" if left else "sheet_br")
    frames += [(end - 0.35, {}, "inout"), (end, {})]
    a.poses(frames)
    return [a]


def recalculation(T: dict, phase: int) -> List[Anim]:
    t = T[f"p{phase}"]
    end = sec(t["end"])
    a = Anim(A + f"recalc_p{phase}", length=end, loop="hold")
    first = sec(t["preview"])
    strikes = [sec(t["strike"] + i * t["interval"]) for i in range(3)]
    tall = merge(stance(drop=-12 if phase == 1 else -6, pitch=-4), scribes(100, 100, 100, yaw=70), {"neck": {"rot": [-18, 0, 0]}})
    if phase == 1:
        tall = merge(tall, sheets(1, 1, 1, 1, lift=10))
    frames = [(0, {}), (first + 0.9, tall, "inout")]
    for i, s in enumerate(strikes):
        slam = merge(tall, stance(drop=9, pitch=5), scribes(-30, -20, -10, yaw=-50 + i * 20))
        frames += [(s - 0.5, tall, "linear"), (s - 0.1, merge(tall, stance(drop=-3)), "out"), (s + 0.04, slam, "snap"), (s + 0.6, tall, "out")]
        a.sound(s - 0.9, "recalc_shift").sound(s, "recalc_strike")
        a.particle(s, "spark", "compass_front").particle(s, "flake", "core")
    frames += [(end - 0.6, tall, "linear"), (end, {}, "inout")]
    a.poses(frames)
    a.sound(0.05, "recalc_begin")
    # the rings (or, in Phase II, the needles' housings) wind up and snap to a new alignment for each configuration
    for k in range(1, 5):
        keys = [(0.0, [0, 0, 0]), (first, [0, 0, 0], "linear")]
        ang = 0.0
        for i, s in enumerate(strikes):
            ang += 360 + 90 * ((k + i) % 4)
            keys += [(s - 0.9, [0, 0, ang - 300], "in"), (s, [0, 0, ang], "snap")] if phase == 1 else \
                    [(s - 0.9, [0, ang - 300, 0], "in"), (s, [0, ang, 0], "snap")]
        keys += [(end, keys[-1][1], "linear")]
        a.track(f"ind_{k}", "rot", keys)
    return [a]


# --------------------------------------------------------------------------- set pieces

def set_pieces(T: dict) -> List[Anim]:
    out: List[Anim] = []

    # ---- intro: a closed instrument case stands up, levels itself and starts measuring
    ti = T["intro"]
    unfold, align, total = sec(ti["unfold"]), sec(ti["align"]), sec(ti["total"])
    packed = merge(stance(drop=44, spread=-14), scribes(20, 150, 30, yaw=-12), {"neck": {"rot": [62, 0, 0]},
                   "plumb_line": {"rot": [70, 0, 0]}, "scope": {"rot": [14, 0, 0]}})
    half = merge(stance(drop=14, roll=5, per_leg={"fl": -8, "br": -8}), scribes(40, 80, 30), {"neck": {"rot": [30, 0, 0]}})
    level = merge(stance(drop=-5), scribes(70, 40, 30, yaw=30), {"neck": {"rot": [-14, 0, 0]}})
    intro = Anim(A + "intro", length=total, loop="hold")
    intro.poses([(0, packed), (0.5, packed, "linear"), (unfold, half, "inout"), (align, level, "out"),
                 (total - 0.6, level, "linear"), (total, {}, "inout")])
    for k in range(1, 5):
        intro.track(f"ind_{k}", "scale", [(0, [0.2, 0.2, 0.2]), (unfold, [0.2, 0.2, 0.2], "linear"),
                                           (unfold + 0.5 + k * 0.3, [1.15, 1.15, 1.15], "out"), (align + 0.6, [1, 1, 1], "inout")])
    intro.sound(0.4, "intro_unpack").sound(unfold + 0.4, "dart_spin").sound(align, "intro_level")
    intro.particle(unfold, "flake", "core").particle(align, "spark", "compass_front")
    out.append(intro)

    # ---- stagger: knocked out of true
    ts = sec(T["stagger"]["total"])
    reel = merge(stance(drop=12, roll=11, pitch=6, per_leg={"fr": 10, "br": 6}), scribe("l", 30, 10, 0, yaw=30),
                 scribe("r", 20, 0, -10, yaw=10), {"neck": {"rot": [26, 0, -14]}, "plumb_line": {"rot": [0, 0, 34]},
                 "scope": {"rot": [20, 0, 0]}})
    for k in range(1, 5):
        reel[f"ind_{k}"] = {"rot": [(-1) ** k * 22, k * 17, (-1) ** k * 12], "pos": [(-1) ** k * 2, -k, 0]}
    stag = Anim(A + "stagger", length=ts, loop="hold")
    stag.poses([(0, {}), (0.2, reel, "snap"), (ts - 0.6, reel, "linear"), (ts, {}, "inout")])
    stag.sound(0.02, "stagger").particle(0.05, "spark", "compass_front").particle(0.1, "flake", "core")
    out.append(stag)

    # ---- phase transition: THERE IS NO NORTH
    tt = T["transition"]
    scatter, rise, unfold, total = sec(tt["scatter"]), sec(tt["rise"]), sec(tt["unfold"]), sec(tt["total"])
    tr = Anim(A + "transition", length=total, loop="hold")
    shudder = merge(stance(drop=8, roll=-6, spread=4), scribes(30, 100, 20, yaw=-8), {"neck": {"rot": [20, 0, 8]}})
    risen = merge(P2_STANCE, scribes(64, 30, 66, yaw=26), {"neck": {"rot": [-20, 0, 0]}})
    legs_and_body = [b for b in P2_POSE if b.startswith(("leg_", "body", "scribe", "neck", "plumb"))]
    tr.poses([(0, {}), (scatter * 0.5, shudder, "snap"), (scatter, shudder, "linear"), (rise, risen, "inout"),
              (total - 0.5, risen, "linear"), (total, {b: P2_POSE[b] for b in legs_and_body}, "inout")], bones=legs_and_body)
    # the four sheets open one after another
    for i, tag in enumerate(SHEETS):
        t0 = rise + i * 0.42
        flat = sheet(tag, 1.0, lift=5)
        over = sheet(tag, 1.0, lift=22)
        for bone in flat:
            tr.track(bone, "rot", [(0, [0, 0, 0]), (t0, [0, 0, 0], "linear"), (t0 + 0.5, over[bone]["rot"], "out"),
                                    (t0 + 0.85, flat[bone]["rot"], "bounce"), (total, flat[bone]["rot"], "linear")])
        tr.sound(t0, "unfold").particle(t0 + 0.3, "flake", f"sheet_{tag}")
    # the compass comes apart: every ring spins up, leaves the hub, and settles above its own sheet
    for k in range(1, 5):
        go_t = unfold + (k - 1) * 0.3
        home = IND_HOME[k]
        tr.track(f"ind_{k}", "rot", [(0, [0, 0, 0]), (scatter, [0, 0, 360 * k], "in"), (go_t, [0, 0, 720 * k], "linear"),
                                      (go_t + 0.7, [90, 0, 720 * k + 360], "out"), (total, [90, 0, 720 * k + 360], "linear")])
        tr.track(f"ind_{k}", "pos", [(0, [0, 0, 0]), (go_t, [0, 0, 0], "linear"), (go_t + 0.35, [home[0] * 0.5, 16, home[2] * 0.5], "out"),
                                      (go_t + 0.7, list(home), "in"), (total, list(home), "linear")])
        tr.sound(go_t, "ring_release").particle(go_t, "spark", f"needle_{k}")
    tr.sound(0.05, "transition_shudder").sound(scatter, "transition_wind").sound(rise - 0.2, "transition_rise")
    tr.particle(scatter * 0.5, "spark", "compass_front")
    out.append(tr)

    # ---- death (on top of the Phase II stance)
    td = T["death"]
    mis, fold, collapse, needle, total = (sec(td[k]) for k in ("misalign", "fold", "collapse", "needle", "total"))
    dz = Anim(A + "death", length=total, loop="hold")
    # 1. the rings lose alignment: each drifts off its sheet on its own wrong axis
    drift = {1: ([24, 0, -30], [8, 6, -6]), 2: ([-34, 50, 20], [-10, 3, 4]), 3: ([40, -70, 44], [6, -4, 9]), 4: ([-20, 110, -50], [-7, 8, -5])}
    fallen = {1: ([8, 0, 0], [-6, -70, -30]), 2: ([-4, 30, 0], [8, -72, -22]), 3: ([12, 200, 0], [-14, -74, -40]), 4: ([-6, 120, 0], [10, -76, -34])}
    for k in range(1, 5):
        r1, p1 = drift[k]
        r2, p2_ = fallen[k]
        tk = collapse + (k - 1) * 0.25
        dz.track(f"ind_{k}", "rot", [(0, [0, 0, 0]), (mis, r1, "inout"), (tk, [r1[0] * 1.6, r1[1] * 1.5, r1[2] * 1.6], "linear"),
                                      (tk + 0.55, r2, "in"), (total, r2, "linear")])
        dz.track(f"ind_{k}", "pos", [(0, [0, 0, 0]), (mis, p1, "inout"), (tk, p1, "linear"), (tk + 0.55, p2_, "in"),
                                      (tk + 0.7, [p2_[0], p2_[1] + 3, p2_[2]], "out"), (tk + 0.85, p2_, "in"), (total, p2_, "linear")])
        dz.sound(tk + 0.5, "ring_drop")
    # 2. it tries to fold back into a map, in the wrong order and against its own hinges
    wrong = {"fl": (0.5, -40), "fr": (1.3, 30), "bl": (-0.4, 60), "br": (0.8, -70)}
    crumple = {"fl": (1.9, -20), "fr": (0.2, 80), "bl": (1.5, 40), "br": (-0.6, 10)}
    for tag in SHEETS:
        w = sheet(tag, 1.0 - wrong[tag][0], lift=wrong[tag][1])
        c = sheet(tag, 1.0 - crumple[tag][0], lift=crumple[tag][1])
        flat = sheet(tag, 1.0)
        for bone in w:
            base = flat[bone]["rot"]
            dz.track(bone, "rot", [(0, [0, 0, 0]), (mis, [0, 0, 0], "linear"),
                                    (fold, [w[bone]["rot"][j] - base[j] for j in range(3)], "bounce"),
                                    (collapse, [c[bone]["rot"][j] - base[j] for j in range(3)], "inout"),
                                    (total, [c[bone]["rot"][j] - base[j] for j in range(3)], "linear")])
            dz.track(bone, "scale", [(0, [1, 1, 1]), (fold, [1, 1, 1], "linear"), (collapse + 0.6, [0.7, 1, 0.8], "in"),
                                      (total, [0.7, 1, 0.8], "linear")])
    dz.sound(mis - 0.3, "transition_wind").sound(fold - 0.5, "fold_slam").sound(fold + 0.6, "death_crumple")
    # 3. the legs go one at a time; the table comes down
    strain = merge(stance(drop=4, roll=-5, pitch=4), scribes(40, 100, 30, yaw=-10), {"neck": {"rot": [22, 0, 10]}})
    kneel = merge(stance(drop=30, roll=14, pitch=10, per_leg={"fr": 16, "br": 10}), scribes(20, 10, 0, yaw=20),
                  {"neck": {"rot": [40, 0, 18]}, "plumb_line": {"rot": [0, 0, 40]}})
    down = merge(stance(drop=66, roll=17, pitch=6, spread=20), scribes(10, 0, -10, yaw=40),
                 {"neck": {"rot": [58, 0, 24]}, "plumb_line": {"rot": [0, 0, 78]}, "scope": {"rot": [34, 0, 0]},
                  "tail": {"rot": [-30, 0, 0]}})
    core = [b for b in down if not b.startswith(("map_", "ind_"))]
    dz.poses([(0, {}), (mis, strain, "inout"), (fold, strain, "linear"), (collapse, kneel, "in"),
              (collapse + 0.8, down, "bounce"), (total, down, "linear")], bones=core)
    dz.sound(collapse, "death_fall").particle(collapse + 0.8, "dust", "core").particle(fold, "flake", "core")
    # 4. three needles stop; the last one turns a little longer, slows, and stops too
    for k in (2, 3, 4):
        stop = mis + k * 0.5
        dz.track(f"ind_{k}_needle", "rot", [(0, [0, 0, 0]), (stop, [0, 0, 360 * k], "out"), (total, [0, 0, 360 * k], "linear")])
        dz.track(f"ind_{k}_tip_glow", "scale", [(0, [1, 1, 1]), (stop, [1, 1, 1], "linear"), (stop + 0.4, [0.01, 0.01, 0.01], "in")])
    dz.track("ind_1_needle", "rot", [(0, [0, 0, 0]), (collapse, [0, 0, 1440], "linear"), (needle, [0, 0, 1700], "out"),
                                      (total, [0, 0, 1700], "linear")])
    dz.track("ind_1_tip_glow", "scale", [(0, [1, 1, 1]), (needle, [1, 1, 1], "linear"), (total, [0.01, 0.01, 0.01], "in")])
    dz.sound(needle - 0.9, "needle_slow").sound(needle, "needle_stop")
    for b in ("level_bubble_glow", "protractor_glow"):
        dz.track(b, "scale", [(0, [1, 1, 1]), (collapse, [1, 1, 1], "linear"), (collapse + 1.0, [0.01, 0.01, 0.01], "in")])
    out.append(dz)
    return out


def build_all(T: dict) -> Tuple[List[Anim], List[Controller], ClientEntity]:
    ce = client_entity()
    anims: List[Anim] = build_base()
    for ph in (1, 2):
        anims += meridian(T["meridian_incision"], ph)
        anims += shear(T["latitude_shear"], ph)
        anims += borders(T["ink_borders"], ph)
        anims += gate(T["unmapped_gate"], ph)
        anims += darts(T["compass_darts"], ph)
        anims += folded(T["folded_country"], ph)
        anims += recalculation(T["great_recalculation"], ph)
    anims += set_pieces(T)
    for a in anims:
        ce.animations[a.name[len(A):]] = a.name

    anim_p = prop("abm:anim")
    is_p2 = prop("abm:phase").eq(2)
    is_p1 = prop("abm:phase").eq(1)
    act = Controller("controller.animation.abm.nomos.action", "none")
    entries = []
    names = {1: "meridian", 2: "shear", 3: "borders", 4: "gate", 5: "darts", 6: "folded", 7: "recalc"}
    for idx, nm in names.items():
        for ph in (1, 2):
            state = f"{nm}_p{ph}"
            entries.append((state, anim_p.eq(idx).and_(is_p2 if ph == 2 else is_p1)))
            act.state(state, [state], [("none", anim_p.ne(idx))], blend=0.18)
    for state, idx in (("transition", 8), ("stagger", 9), ("death", 10), ("intro", 11)):
        entries.append((state, anim_p.eq(idx)))
        act.state(state, [state], [] if state == "death" else [("none", anim_p.ne(idx))], blend=0.2)
    act.state("none", [], entries, blend=0.22)

    # one -> changing (rings settle into alignment while the transition plays) -> two
    phase = Controller("controller.animation.abm.nomos.phase", "one")
    phase.state("one", ["compass_spin"], [("two", is_p2), ("changing", anim_p.eq(8))], blend=0.6)
    phase.state("changing", [], [("two", is_p2), ("one", anim_p.ne(8).and_(is_p1))], blend=0.25)
    phase.state("two", ["p2_pose", "p2_compass"], [("one", is_p1)], blend=0.25)

    feet = Controller("controller.animation.abm.nomos.feet", "still")
    moving = q("modified_move_speed").gt(0.12).and_(anim_p.eq(0))
    feet.state("still", [], [("moving", moving)])
    feet.state("moving", ["footfalls"], [("still", q("modified_move_speed").lt(0.06).or_(anim_p.ne(0)))])

    ce.animations["ctl_action"] = act.name
    ce.animations["ctl_phase"] = phase.name
    ce.animations["ctl_feet"] = feet.name
    ce.animate = ["idle", "walk", "turn", "ctl_phase", "ctl_action", "ctl_feet"]
    return anims, [act, phase, feet], ce
