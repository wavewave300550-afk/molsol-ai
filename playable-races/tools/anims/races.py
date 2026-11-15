"""Animation sets for the three race forms (attachable-side) and the player
skeleton poses that scripts trigger with Entity.playAnimation()."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

from anims.core import Anim, NS, VSWING, WALK, PHASE, T, osc, n
from models.common import THIRD_PERSON_ONLY, FIRST_PERSON_ONLY

SPRINT = "(q.is_sprinting ? 1 : 0)"
AIR = "!q.is_on_ground && !q.is_in_water"
DAY = "(q.time_of_day > 0.25 && q.time_of_day < 0.75)"
SUN = f"({DAY} ? math.sin((q.time_of_day - 0.25) * 360) : -0.35)"


def A(race: str, name: str, **kw) -> Anim:
    return Anim(f"animation.{NS}.{race}.{name}", **kw)


def view_anims(race: str) -> Tuple[Anim, Anim]:
    fp = A(race, "first_person")
    for b in THIRD_PERSON_ONLY:
        fp.bone(b, scale=0)
    tp = A(race, "third_person")
    for b in FIRST_PERSON_ONLY:
        tp.bone(b, scale=0)
    return fp, tp


def transition(model, race: str, name: str, frm: str, to: str, length: float, ease=(0.0, 1.0)) -> Anim:
    """Animate every bone whose rest pose differs between two variants, from the
    `frm` pose into the `to` pose (the geometry of `to` is the rest state)."""
    a = A(race, name, loop="hold", length=length)
    for bn in model.order:
        if not model.bone_in_variant(bn, to):
            continue
        r_from = np.array(model.bone_rot(bn, frm), float)
        r_to = np.array(model.bone_rot(bn, to), float)
        dr = r_from - r_to
        t_from = _own_offset(model, bn, frm)
        t_to = _own_offset(model, bn, to)
        dt = t_from - t_to
        kf_r = {} if np.allclose(dr, 0, atol=0.01) else {0.0: list(dr), length * 0.6: list(dr * 0.15), length: [0, 0, 0]}
        kf_t = {} if np.allclose(dt, 0, atol=0.01) else {0.0: list(dt), length * 0.6: list(dt * 0.12), length: [0, 0, 0]}
        if kf_r or kf_t:
            a.bone(bn, rot=kf_r or None, pos=kf_t or None)
    return a


def _own_offset(model, bn, variant):
    b = model.bones[bn]
    if variant in b.variant:
        return np.array(b.variant[variant][0], float)
    return np.zeros(3)


# ============================================================================ salamander

def salamander(model) -> Dict[str, object]:
    r = "salamander"
    fp, tp = view_anims(r)
    amb = A(r, "ambient")
    for side, s in (("r", -1), ("l", 1)):
        for k in range(3):
            amb.bone(f"gill_{side}{k}", rot=[osc(0.45, 5, k * 50), f"{osc(0.45, 8, k * 50 + 90)} * {-s}", 0])
        for k in range(4):
            amb.bone(f"plate_{side}{k}", rot=[0, 0, f"({osc(0.28, 3, k * 45)} + {SUN} * 9 + (q.modified_move_speed < 0.05 && {DAY} ? 7 : 0)) * {-s}"])
        amb.bone(f"{side}_lobe0", rot=[osc(0.6, 2, 30), 0, 0])
        amb.bone(f"{side}_tendril0", rot=[osc(0.7, 6, 10), 0, osc(0.5, 4)])
        amb.bone(f"{side}_tendril1", rot=[osc(0.6, 7, 70), 0, osc(0.45, 4, 40)])
    for k in range(4):
        amb.bone(f"tail{k}", rot=[osc(0.25, 1.5, k * 30), osc(0.35, 3 + k * 2.5, -k * 40), 0])
    for k in range(5):
        amb.bone(f"petal{k}_l", rot=[osc(0.3, 4, k * 72), 0, 0])
    amb.bone("jaw", rot=[f"math.max(0, {osc(0.22, 3)})", 0, 0])
    amb.bone("torso", scale=[f"1 + {osc(0.4, 0.012)}", 1, f"1 + {osc(0.4, 0.02)}"])

    loco = A(r, "locomotion")
    for k in range(4):
        loco.bone(f"tail{k}", rot=[0, f"math.sin({PHASE} - {k * 45}) * {6 + k * 5} * {WALK}", 0])
    loco.bone("torso", rot=[f"{WALK} * 8", f"math.sin({PHASE}) * 4 * {WALK}", 0])
    loco.bone("skull", rot=[f"-{WALK} * 6", f"-math.sin({PHASE}) * 3 * {WALK}", 0])
    for k, sign in enumerate((1, 1, -1, -1)):
        loco.bone(f"r_toe{k}", rot=[0, f"math.max(0, -math.cos({PHASE})) * {sign * 12} * {WALK}", 0])
        loco.bone(f"l_toe{k}", rot=[0, f"math.max(0, math.cos({PHASE})) * {-sign * 12} * {WALK}", 0])
    for side, s in (("r", -1), ("l", 1)):
        for k in range(3):
            loco.bone(f"gill_{side}{k}", rot=[f"-{WALK} * 14", 0, 0])

    swim = A(r, "swim")
    # in the vanilla swim pose the body lies horizontal: swing the tail back along the body axis
    swim.bone("tail0", rot=[f"-76 * (q.is_swimming ? 1 : 0.35) + {osc(0.55, 3)}", osc(1.15, 14, 0), 0])
    for k in range(1, 4):
        swim.bone(f"tail{k}", rot=[osc(0.55, 3, -k * 30), osc(1.15, 14 + k * 8, -k * 58), 0])
    swim.bone("torso", rot=[0, osc(1.15, 7, 40), 0])
    for side, s in (("r", -1), ("l", 1)):
        swim.bone(f"{side}_thigh", rot=[f"22 + {osc(1.15, 10, 0 if s < 0 else 180)}", 0, f"{-s} * -10"])
        for k in range(3):
            swim.bone(f"gill_{side}{k}", rot=[-24, f"{osc(1.15, 9, k * 40)}", 0])
        for k in range(4):
            swim.bone(f"plate_{side}{k}", rot=[0, 0, f"-18 * {-s}"])
    swim.particle(0.0, "bubbles", "mouth")
    swim.loop, swim.length = True, 1.6

    air = A(r, "airborne")
    air.bone("tail0", rot=[-14, 0, 0])
    air.bone("tail1", rot=[-6, 0, 0])
    for side, s in (("r", -1), ("l", 1)):
        air.bone(f"{side}_thigh", rot=[0, 0, f"{-s} * -9"])
        for k in range(4):
            air.bone(f"{side}_toe{k}", rot=[0, (k - 1.5) * 9 * (1 if s < 0 else -1), 0])

    hurt = A(r, "hurt")
    for side, s in (("r", -1), ("l", 1)):
        for k in range(3):
            hurt.bone(f"gill_{side}{k}", rot=[-18, f"{-s} * 18", 0])
        for k in range(4):
            hurt.bone(f"plate_{side}{k}", rot=[0, 0, f"12 * {-s}"])

    # ---- state intros / loops
    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.6),
        "bloom": transition(model, r, "intro_bloom", "base", "bloom", 1.3),
        "dormant": transition(model, r, "intro_dormant", "base", "dormant", 2.2),
        "predatory": transition(model, r, "intro_predatory", "base", "predatory", 0.3),
        "rooted": transition(model, r, "intro_rooted", "base", "rooted", 1.0),
    }
    for side in ("r", "l"):
        intro["rooted"].bone(f"{side}_roots", scale={0.0: [1, 0.05, 1], 0.7: [1, 1.08, 1], 1.0: [1, 1, 1]})
        intro["predatory"].bone(f"{side}_tendril0x", scale={0.0: [1, 0.1, 1], 0.3: [1, 1, 1]})
        intro["predatory"].bone(f"{side}_tendril1x", scale={0.0: [1, 0.1, 1], 0.3: [1, 1, 1]})
    for side, s_ in (("r", -1), ("l", 1)):
        for k in range(4):
            intro["base"].bone(f"plate_{side}{k}", rot={0.0: [0, 0, 0], 0.15: [0, 0, 9 * -s_], 0.35: [0, 0, -4 * -s_], 0.6: [0, 0, 0]})
    intro["rooted"].particle(0.0, "rootburst", "spores")
    intro["bloom"].particle(0.2, "dew", "spores")
    intro["dormant"].particle(0.4, "flakes", "spores")
    intro["predatory"].particle(0.0, "drip", "mouth")

    pred_loop = A(r, "predatory_loop")
    for side in ("r", "l"):
        pred_loop.bone(f"{side}_lobe0", rot=[osc(2.2, 5), 0, 0])
        pred_loop.bone(f"{side}_lobe1", rot=[osc(2.2, -5, 40), 0, 0])
        pred_loop.bone(f"{side}_tendril0x", rot=[osc(1.6, 10), 0, osc(1.1, 8)])
        pred_loop.bone(f"{side}_tendril1x", rot=[osc(1.4, 12, 60), 0, osc(1.0, 8, 30)])
    pred_loop.bone("jaw", rot=[osc(1.8, 3), 0, 0])
    dorm_loop = A(r, "dormant_loop")
    dorm_loop.bone("torso", scale=[f"1 + {osc(0.18, 0.008)}", 1, 1])
    root_loop = A(r, "rooted_loop")
    for side in ("r", "l"):
        for k in range(5):
            root_loop.bone(f"{side}_root{k}", rot=[osc(0.4, 2.5, k * 50), 0, osc(0.33, 2.5, k * 70)])

    fx = {
        "bloom": A(r, "fx_bloom", length=2.4).particle(0.0, "spores", "spores").particle(1.2, "pollen", "pollen"),
        "dormant": A(r, "fx_dormant", length=3.0).particle(0.0, "flakes", "spores"),
        "predatory": A(r, "fx_predatory", length=1.2).particle(0.0, "drip", "mouth"),
        "rooted": A(r, "fx_rooted", length=2.0).particle(0.0, "spores", "spores"),
        "base": A(r, "fx_base", length=4.0).particle(0.0, "drip", "mouth"),
    }
    anims = [fp, tp, amb, loco, swim, air, hurt, pred_loop, dorm_loop, root_loop, *intro.values(), *fx.values()]
    animate = {}
    for v in ("base", "bloom", "dormant", "predatory", "rooted"):
        lst = [("first_person", "c.is_first_person"), ("third_person", "!c.is_first_person"),
               ("ambient", None), ("locomotion", "!q.is_swimming"),
               ("swim", "q.is_swimming || (q.is_in_water && !q.is_on_ground)"), ("airborne", AIR),
               ("hurt", "q.hurt_time > 0"), (f"intro_{v}", None), (f"fx_{v}", "!c.is_first_person")]
        if v == "predatory":
            lst.append(("predatory_loop", None))
        if v == "dormant":
            lst.append(("dormant_loop", None))
        if v == "rooted":
            lst.append(("rooted_loop", None))
        animate[v] = lst
    particles = {"spores": f"{NS}:spore_drift", "pollen": f"{NS}:pollen", "dew": f"{NS}:dew_burst",
                 "flakes": f"{NS}:dry_flake", "drip": f"{NS}:sticky_drip", "rootburst": f"{NS}:root_burst",
                 "bubbles": f"{NS}:bubble_trail"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": {}}


# ============================================================================ golem

def golem(model, movable: List[str]) -> Dict[str, object]:
    r = "golem"
    fp, tp = view_anims(r)
    amb = A(r, "ambient")
    amb.bone("ring_a", rot=[0, 0, f"{T} * 52"])
    amb.bone("ring_b", rot=[0, f"-{T} * 38", 0])
    amb.bone("ring_c", rot=[f"{T} * 71", 0, 0])
    amb.bone("crystal", rot=[0, f"{T} * 30", 0], pos=[0, osc(0.45, 0.35), 0],
             scale=f"1 + {osc(0.9, 0.05)}")
    for k in range(4):
        amb.bone(f"sat{k}", pos=[osc(0.21, 0.3, k * 90), osc(0.3 + k * 0.07, 0.55, k * 80), 0],
                 rot=[f"{T} * {14 + k * 6}", f"{T} * {22 + k * 7}", 0])
    amb.bone("r_shoulder", pos=[0, osc(0.22, 0.28), 0])
    amb.bone("l_shoulder", pos=[0, osc(0.24, 0.24, 120), 0])
    amb.bone("slab_a", pos=[0, osc(0.31, 0.4, 30), 0], rot=[0, 0, osc(0.2, 1.4)])
    amb.bone("slab_b", pos=[0, osc(0.28, 0.4, 200), 0], rot=[0, 0, osc(0.22, -1.4, 60)])
    amb.bone("r_orbit", rot=[0, f"{T} * 75", 0])
    amb.bone("l_orbit", rot=[0, f"-{T} * 68", 0])
    amb.bone("r_upper", pos=[0, osc(0.4, 0.12), 0])
    amb.bone("l_upper", pos=[0, osc(0.4, 0.12, 90), 0])
    amb.bone("crown", rot=["math.clamp(q.target_x_rotation, -50, 50) * 0.8", "q.target_y_rotation", 0])
    for side in ("r", "l"):
        amb.bone(f"{side}_foot_rune", scale="q.is_on_ground ? 0 : 1")

    loco = A(r, "locomotion")
    step = f"math.abs(math.sin({PHASE}))"
    loco.bone("pelvis", pos=[0, f"-{step} * 0.45 * {WALK}", 0])
    loco.bone("midriff", pos=[0, f"-{step} * 0.3 * {WALK}", 0])
    loco.bone("r_shoulder", pos=[f"-1.2 * {SPRINT}", f"-0.6 * {SPRINT}", f"1.8 * {SPRINT}"],
              rot=[0, 0, f"math.sin({PHASE}) * 2.5 * {WALK}"])
    loco.bone("l_shoulder", pos=[f"1.2 * {SPRINT}", f"-0.6 * {SPRINT}", f"1.8 * {SPRINT}"],
              rot=[0, 0, f"math.sin({PHASE}) * 2.5 * {WALK}"])
    for k in range(4):
        loco.bone(f"sat{k}", pos=[0, f"-1 * {SPRINT}", f"3.2 * {SPRINT}"])
    loco.bone("slab_a", pos=[0, 0, f"1.4 * {SPRINT}"], rot=[f"-8 * {SPRINT}", 0, 0])
    loco.bone("slab_b", pos=[0, 0, f"1.4 * {SPRINT}"], rot=[f"-8 * {SPRINT}", 0, 0])
    for side in ("r", "l"):
        loco.bone(f"{side}_hip", pos=[0, f"{step} * 0.25 * {WALK}", 0])

    air = A(r, "airborne")
    for k in range(4):
        air.bone(f"sat{k}", pos=[0, 1.8, 0])
    air.bone("r_shoulder", pos=[0, 0.7, 0])
    air.bone("l_shoulder", pos=[0, 0.7, 0])
    air.bone("slab_a", pos=[0, 1.1, 0])
    air.bone("slab_b", pos=[0, 1.1, 0])

    hurt = A(r, "hurt")
    for k, bn in enumerate(["r_shoulder", "l_shoulder", "slab_a", "slab_b", "pillar_r", "pillar_l", "arch", "crown",
                            "r_upper", "l_upper"]):
        hurt.bone(bn, pos=[osc(7.0, 0.35, k * 37), osc(9.0, 0.35, k * 53), osc(8.0, 0.25, k * 71)],
                  rot=[0, 0, osc(6.0, 2.5, k * 29)])
    hurt.bone("core", scale="1.15")

    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.5),
        "siege": A(r, "intro_siege", loop="hold", length=0.45),
        "bastion": transition(model, r, "intro_bastion", "base", "bastion", 0.35),
        "arcane": transition(model, r, "intro_arcane", "base", "arcane", 0.7),
        "scattered": A(r, "intro_scattered", loop="hold", length=1.0),
        "disrupted": A(r, "intro_disrupted", loop="hold", length=0.6),
    }
    intro["base"].bone("core", scale={0.0: 1.35, 0.25: 0.95, 0.5: 1.0})
    for bn in ("r_shoulder", "l_shoulder", "slab_a", "slab_b"):
        intro["base"].bone(bn, pos={0.0: [0, 1.2, 0], 0.3: [0, -0.2, 0], 0.5: [0, 0, 0]})
    intro["base"].particle(0.0, "pulse", "core")
    intro["siege"].bone("hammer", scale={0.0: 0.15, 0.3: 1.12, 0.45: 1.0})
    intro["siege"].bone("r_fist", scale={0.0: 1.0, 0.2: 1.25, 0.45: 1.0})
    intro["siege"].particle(0.0, "burst", "core")
    intro["arcane"].bone("arcane_ring", scale={0.0: 0.1, 0.5: 1.08, 0.7: 1.0})
    intro["arcane"].particle(0.0, "burst", "core")
    # scattered: every fragment bursts away from the core, spins, and converges
    centers = {}
    for bn in movable:
        b = model.bones[bn]
        centers[bn] = np.array(b.pivot, float)
    core = np.array([0.0, 24.0, 0.0])
    for k, bn in enumerate(movable):
        d = centers[bn] - core
        d[1] += 4.0
        nrm = np.linalg.norm(d)
        d = d / nrm if nrm > 1e-6 else np.array([0.0, 1.0, 0.0])
        dist = 7.0 + (k * 37 % 5)
        spin = [(k * 53 % 120) - 60, (k * 97 % 160) - 80, (k * 31 % 90) - 45]
        intro["scattered"].bone(bn, pos={0.0: [0, 0, 0], 0.22: list(d * dist), 0.5: list(d * dist * 1.1),
                                         0.82: list(d * dist * 0.15), 1.0: [0, 0, 0]},
                                rot={0.0: [0, 0, 0], 0.5: spin, 1.0: [0, 0, 0]})
    intro["scattered"].bone("core", scale={0.0: 1.0, 0.3: 1.6, 0.85: 1.4, 1.0: 1.0})
    intro["scattered"].particle(0.0, "burst", "core")
    for k, bn in enumerate(["r_shoulder", "l_shoulder", "slab_a", "slab_b", "crown", "arch"]):
        intro["disrupted"].bone(bn, pos={0.0: [0, 0, 0], 0.15: [round(math.sin(math.radians(k * 50)) * 1.4, 3), -0.8, 0.6], 0.6: [0, 0, 0]})
    intro["disrupted"].particle(0.0, "sparks", "core")

    siege_loop = A(r, "siege_loop")
    siege_loop.bone("hammer", rot=[0, 0, osc(1.5, 1.5)])
    bastion_loop = A(r, "bastion_loop")
    bastion_loop.bone("slab_a", pos=[0, 0, osc(2.0, 0.12)])
    bastion_loop.bone("slab_b", pos=[0, 0, osc(2.0, 0.12, 90)])
    arcane_loop = A(r, "arcane_loop")
    arcane_loop.bone("arcane_ring", rot=[0, f"{T} * 46", 0])
    arcane_loop.bone("slab_a", rot=[0, f"{T} * 30", 0])
    arcane_loop.bone("slab_b", rot=[0, f"-{T} * 30", 0])
    disrupted_loop = A(r, "disrupted_loop")
    for k, bn in enumerate(["r_shoulder", "l_shoulder", "slab_a", "slab_b", "sat0", "sat1", "sat2", "sat3", "crown"]):
        disrupted_loop.bone(bn, pos=[f"{osc(0.7 + k * 0.13, 0.6, k * 40)}", f"{osc(0.9 + k * 0.1, 0.5, k * 77)} - 0.4",
                                     f"{osc(0.5 + k * 0.11, 0.5, k * 13)}"],
                            rot=[osc(0.6, 3, k * 30), osc(0.5, 4, k * 60), osc(0.8, 5, k * 90)])
    disrupted_loop.bone("crystal", scale="math.mod(q.life_time * 6.3, 1) > 0.35 ? 1 : 0.55")
    disrupted_loop.bone("ring_b", rot=[osc(1.7, 9), 0, osc(1.3, 6)])

    fx = {v: A(r, f"fx_{v}", length=1.6 if v != "base" else 2.6).particle(0.0, "motes", "core")
          for v in ("base", "siege", "bastion", "arcane", "scattered", "disrupted")}
    fx["disrupted"].particle(0.8, "sparks", "core")
    anims = [fp, tp, amb, loco, air, hurt, siege_loop, bastion_loop, arcane_loop, disrupted_loop,
             *intro.values(), *fx.values()]
    animate = {}
    for v in ("base", "siege", "bastion", "arcane", "scattered", "disrupted"):
        lst = [("first_person", "c.is_first_person"), ("third_person", "!c.is_first_person"), ("ambient", None),
               ("locomotion", None), ("airborne", AIR), ("hurt", "q.hurt_time > 0"), (f"intro_{v}", None),
               (f"fx_{v}", "!c.is_first_person")]
        if v in ("siege", "bastion", "arcane", "disrupted"):
            lst.append((f"{v}_loop", None))
        animate[v] = lst
    particles = {"motes": f"{NS}:rune_mote", "burst": f"{NS}:rune_burst", "pulse": f"{NS}:rune_pulse",
                 "sparks": f"{NS}:rune_spark"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": {}}


# ============================================================================ jackalope

def jackalope(model) -> Dict[str, object]:
    r = "jackalope"
    fp, tp = view_anims(r)
    amb = A(r, "ambient")
    tw_r = "(math.mod(q.life_time, 4.3) < 0.2 ? math.sin(math.mod(q.life_time, 4.3) * 1800) * 11 : 0)"
    tw_l = "(math.mod(q.life_time + 1.7, 3.1) < 0.2 ? math.sin(math.mod(q.life_time + 1.7, 3.1) * 1800) * 11 : 0)"
    amb.bone("r_ear", rot=[osc(0.23, 3), 0, f"{osc(0.31, 2.5)} + {tw_r}"])
    amb.bone("l_ear", rot=[osc(0.27, 3, 70), 0, f"{osc(0.29, -2.5, 40)} - {tw_l}"])
    amb.bone("r_ear_tip", rot=[osc(0.41, 5, 30), 0, 0])
    amb.bone("l_ear_tip", rot=[osc(0.37, 5, 110), 0, 0])
    amb.bone("nose", pos=[0, 0, "math.mod(q.life_time, 2.6) < 0.6 ? math.sin(q.life_time * 2400) * 0.12 : 0"])
    amb.bone("scut", rot=[f"{osc(0.6, 4)} + (math.mod(q.life_time + 0.8, 3.7) < 0.15 ? 14 : 0)", 0, 0])
    amb.bone("skull", rot=[osc(0.17, 1.5), osc(0.11, 2), 0])
    for k in range(6):
        amb.bone(f"dorsal{k}", rot=[osc(0.5, 3, k * 30), 0, 0])

    listen = A(r, "listen")
    listen.bone("r_ear", rot=[16, 28, 6])
    listen.bone("l_ear", rot=[12, -8, 0])
    listen.bone("skull", rot=[-4, 0, 9])
    listen.bone("scut", rot=[10, 0, 0])

    loco = A(r, "locomotion")
    cancel = f"(q.is_sprinting ? 1.0 : 0.55)"
    bound = f"({PHASE} * 0.5)"
    loco.bone("r_thigh", rot=[f"-{VSWING} * 1.4 * {cancel} + {SPRINT} * math.sin({bound}) * 40 * {WALK}", 0, 0])
    loco.bone("l_thigh", rot=[f"{VSWING} * 1.4 * {cancel} + {SPRINT} * math.sin({bound}) * 40 * {WALK}", 0, 0])
    for side in ("r", "l"):
        loco.bone(f"{side}_shin", rot=[f"{SPRINT} * math.max(0, math.sin({bound} + 40)) * 30 * {WALK}", 0, 0])
        loco.bone(f"{side}_foot", rot=[f"{SPRINT} * math.cos({bound}) * 22 * {WALK}", 0, 0])
        loco.bone(f"{side}_ear", rot=[f"-{WALK} * 12 - {SPRINT} * 16", 0, 0])
    loco.bone("torso", rot=[f"{WALK} * 6 + {SPRINT} * math.sin({bound} + 90) * 6", 0, 0],
              pos=[0, f"{SPRINT} * math.abs(math.sin({bound})) * 0.9", 0])
    loco.bone("scut", rot=[f"{SPRINT} * math.sin({bound}) * 14", 0, 0])
    loco.bone("skull", rot=[f"{SPRINT} * math.sin({bound} - 60) * 4", 0, 0])

    air = A(r, "airborne")
    rising = "(q.vertical_speed > 0 ? 1 : 0)"
    for side in ("r", "l"):
        air.bone(f"{side}_thigh", rot=[f"{rising} * 30 - (1 - {rising}) * 14", 0, 0])
        air.bone(f"{side}_shin", rot=[f"-{rising} * 22 + (1 - {rising}) * 10", 0, 0])
        air.bone(f"{side}_foot", rot=[f"{rising} * 26", 0, 0])
        air.bone(f"{side}_ear", rot=[-22, 0, 0])
    air.bone("scut", rot=[16, 0, 0])

    land = A(r, "land", loop=False, length=0.35)
    for side in ("r", "l"):
        land.bone(f"{side}_thigh", rot={0.0: [-24, 0, 0], 0.1: [-28, 0, 0], 0.35: [0, 0, 0]})
        land.bone(f"{side}_shin", rot={0.0: [34, 0, 0], 0.1: [38, 0, 0], 0.35: [0, 0, 0]})
        land.bone(f"{side}_foot", rot={0.0: [-10, 0, 0], 0.35: [0, 0, 0]})
        land.bone(f"{side}_ear", rot={0.0: [14, 0, 0], 0.15: [-6, 0, 0], 0.35: [0, 0, 0]})
    land.bone("scut", rot={0.0: [-14, 0, 0], 0.18: [10, 0, 0], 0.35: [0, 0, 0]})
    land.bone("torso", pos={0.0: [0, -0.9, 0], 0.35: [0, 0, 0]})

    hurt = A(r, "hurt")
    hurt.bone("r_ear", rot=[-34, 0, 8])
    hurt.bone("l_ear", rot=[-34, 0, -8])
    hurt.bone("scut", rot=[-12, 0, 0])

    intro = {
        "base": A(r, "intro_base", loop="hold", length=0.4),
        "hunt": transition(model, r, "intro_hunt", "base", "hunt", 0.25),
        "awakened": transition(model, r, "intro_awakened", "base", "awakened", 1.8),
        "awakened_hunt": transition(model, r, "intro_awakened_hunt", "awakened", "awakened_hunt", 0.25),
    }
    intro["base"].bone("r_ear", rot={0.0: [-14, 0, 0], 0.2: [6, 0, 0], 0.4: [0, 0, 0]})
    intro["base"].bone("l_ear", rot={0.0: [-14, 0, 0], 0.25: [6, 0, 0], 0.4: [0, 0, 0]})
    aw = intro["awakened"]
    for side in ("r", "l"):
        for nm, t0, t1 in (("back", 0.35, 0.95), ("low", 0.55, 1.15), ("crown", 0.8, 1.4), ("crown2", 0.95, 1.6)):
            aw.bone(f"{side}_tine_{nm}", scale={0.0: 0.02, t0: 0.02, t1: 1.12, t1 + 0.15: 1.0})
    aw.bone("skull", rot={0.0: [0, 0, 0], 0.45: [-30, 0, 0], 1.3: [-30, 0, 0], 1.8: [0, 0, 0]})
    aw.particle(0.0, "awaken", "antlers")
    aw.particle(0.9, "embers", "antlers")
    intro["hunt"].particle(0.0, "embers", "antlers")

    hunt_loop = A(r, "hunt_loop")
    hunt_loop.bone("r_ear", rot=[osc(9, 1.4), 0, 0])
    hunt_loop.bone("l_ear", rot=[osc(9, 1.4, 90), 0, 0])

    fx = {
        "base": A(r, "fx_base", length=3.2).particle(0.0, "moonmotes", "antlers"),
        "hunt": A(r, "fx_hunt", length=0.5).particle(0.0, "embers", "antlers"),
        "awakened": A(r, "fx_awakened", length=0.9).particle(0.0, "embers", "antlers").particle(0.45, "bloodmist", "tail"),
        "awakened_hunt": A(r, "fx_awakened_hunt", length=0.45).particle(0.0, "embers", "antlers"),
    }
    controllers = {
        f"controller.animation.{NS}.jackalope.landing": {
            "initial_state": "ground",
            "states": {
                "ground": {"transitions": [{"air": "!q.is_on_ground && !q.is_in_water"}]},
                "air": {"transitions": [{"landing": "q.is_on_ground"}, {"ground": "q.is_in_water"}]},
                "landing": {"animations": ["land"], "transitions": [{"air": "!q.is_on_ground && !q.is_in_water"},
                                                                     {"ground": "q.all_animations_finished"}]},
            },
        }
    }
    anims = [fp, tp, amb, listen, loco, air, land, hurt, hunt_loop, *intro.values(), *fx.values()]
    animate = {}
    for v in ("base", "hunt", "awakened", "awakened_hunt"):
        night = "q.time_of_day < 0.23 || q.time_of_day > 0.77"
        lst = [("first_person", "c.is_first_person"), ("third_person", "!c.is_first_person"), ("ambient", None),
               ("listen", "q.is_sneaking && q.modified_move_speed < 0.02"), ("locomotion", "!q.is_swimming"),
               ("airborne", AIR), ("landing", None), ("hurt", "q.hurt_time > 0"), (f"intro_{v}", None),
               (f"fx_{v}", f"!c.is_first_person && ({night})" if v == "base" else "!c.is_first_person")]
        if v in ("hunt", "awakened_hunt"):
            lst.append(("hunt_loop", None))
        animate[v] = lst
    particles = {"moonmotes": f"{NS}:moon_mote", "embers": f"{NS}:blood_ember", "awaken": f"{NS}:awaken_spiral",
                 "bloodmist": f"{NS}:blood_mist"}
    return {"anims": anims, "animate": animate, "particles": particles, "controllers": controllers}


# ============================================================================ player poses

FPK_ARM = "(1 - variable.is_first_person * 0.7)"
FPK = "(1 - variable.is_first_person)"


def _pk(vec, k):
    return [f"{v} * {k}" if v != 0 else 0 for v in vec]


def pose(name: str, length: float, loop=False, **bones) -> Anim:
    a = Anim(f"animation.{NS}.pose.{name}", loop=(True if loop else False), length=length)
    for bn, frames in bones.items():
        k = FPK_ARM if bn in ("rightarm", "leftarm") else FPK
        a.bone(bn, rot={t: _pk(v, k) for t, v in frames.items()})
    return a


def poses() -> List[Anim]:
    out = [
        pose("sal_snare", 0.55, rightarm={0: [0, 0, 0], 0.12: [-96, 6, 0], 0.4: [-82, 0, 0], 0.55: [0, 0, 0]},
             body={0: [0, 0, 0], 0.12: [0, -14, 0], 0.55: [0, 0, 0]}),
        pose("sal_embrace", 0.7, rightarm={0: [0, 0, 0], 0.15: [-90, 32, 0], 0.35: [-88, -22, 0], 0.7: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [-90, -32, 0], 0.35: [-88, 22, 0], 0.7: [0, 0, 0]},
             body={0: [0, 0, 0], 0.35: [12, 0, 0], 0.7: [0, 0, 0]}),
        pose("sal_root", 1.0, loop=True, rightarm={0: [-22, 0, 38], 1.0: [-22, 0, 38]},
             leftarm={0: [-22, 0, -38], 1.0: [-22, 0, -38]}, rightleg={0: [0, 0, 7], 1.0: [0, 0, 7]},
             leftleg={0: [0, 0, -7], 1.0: [0, 0, -7]}, head={0: [-16, 0, 0], 1.0: [-16, 0, 0]}),
        pose("sal_jet", 0.5, rightarm={0: [0, 0, 0], 0.1: [42, 0, 12], 0.5: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.1: [42, 0, -12], 0.5: [0, 0, 0]}),
        pose("gol_edict", 1.1, rightarm={0: [0, 0, 0], 0.35: [-172, 0, 8], 0.5: [-176, 0, 8], 0.62: [-34, 0, 0], 1.1: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.35: [-160, 0, -8], 0.5: [-164, 0, -8], 0.62: [-30, 0, 0], 1.1: [0, 0, 0]},
             body={0: [0, 0, 0], 0.5: [-9, 0, 0], 0.62: [18, 0, 0], 1.1: [0, 0, 0]}),
        pose("gol_bastion", 1.0, loop=True, rightarm={0: [-76, -26, 0], 1.0: [-76, -26, 0]},
             leftarm={0: [-76, 26, 0], 1.0: [-76, 26, 0]}, body={0: [6, 0, 0], 1.0: [6, 0, 0]}),
        pose("gol_glyph", 1.2, rightarm={0: [0, 0, 0], 0.3: [-10, 0, 84], 0.6: [-12, 0, 86], 0.8: [-62, 0, 22], 1.2: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.3: [-10, 0, -84], 0.6: [-12, 0, -86], 0.8: [-62, 0, -22], 1.2: [0, 0, 0]},
             head={0: [0, 0, 0], 0.6: [-14, 0, 0], 0.8: [16, 0, 0], 1.2: [0, 0, 0]}),
        pose("gol_reassemble", 1.0, rightarm={0: [0, 0, 0], 0.2: [-40, 0, 60], 0.8: [-40, 0, 60], 1.0: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.2: [-40, 0, -60], 0.8: [-40, 0, -60], 1.0: [0, 0, 0]}),
        pose("jak_bound", 0.45, rightleg={0: [-32, 0, 0], 0.1: [28, 0, 0], 0.45: [0, 0, 0]},
             leftleg={0: [-32, 0, 0], 0.1: [28, 0, 0], 0.45: [0, 0, 0]},
             body={0: [16, 0, 0], 0.1: [-10, 0, 0], 0.45: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.1: [36, 0, 10], 0.45: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.1: [36, 0, -10], 0.45: [0, 0, 0]}),
        pose("jak_brand", 0.7, head={0: [0, 0, 0], 0.15: [32, 0, 0], 0.55: [32, 0, 0], 0.7: [0, 0, 0]},
             body={0: [0, 0, 0], 0.15: [24, 0, 0], 0.55: [20, 0, 0], 0.7: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.15: [42, 0, 14], 0.7: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [42, 0, -14], 0.7: [0, 0, 0]}),
        pose("jak_mirage", 0.5, body={0: [0, 0, 0], 0.15: [-16, 0, 0], 0.5: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.15: [-30, 0, 60], 0.5: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.15: [-30, 0, -60], 0.5: [0, 0, 0]}),
        pose("jak_waltz", 0.5, loop=True, rightarm={0: [-130, 0, 40], 0.25: [-30, 0, 10], 0.5: [-130, 0, 40]},
             leftarm={0: [-30, 0, -10], 0.25: [-130, 0, -40], 0.5: [-30, 0, -10]},
             body={0: [10, -18, 0], 0.25: [10, 18, 0], 0.5: [10, -18, 0]}, head={0: [-8, 0, 6], 0.25: [-8, 0, -6], 0.5: [-8, 0, 6]}),
        pose("jak_howl", 1.6, head={0: [0, 0, 0], 0.4: [-42, 0, 0], 1.2: [-42, 0, 0], 1.6: [0, 0, 0]},
             body={0: [0, 0, 0], 0.4: [-12, 0, 0], 1.2: [-12, 0, 0], 1.6: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.4: [-20, 0, 40], 1.2: [-20, 0, 40], 1.6: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.4: [-20, 0, -40], 1.2: [-20, 0, -40], 1.6: [0, 0, 0]}),
        pose("rite", 1.8, head={0: [0, 0, 0], 0.5: [-30, 0, 0], 1.3: [-30, 0, 0], 1.8: [0, 0, 0]},
             rightarm={0: [0, 0, 0], 0.5: [-150, 0, 20], 1.3: [-150, 0, 20], 1.8: [0, 0, 0]},
             leftarm={0: [0, 0, 0], 0.5: [-150, 0, -20], 1.3: [-150, 0, -20], 1.8: [0, 0, 0]}),
    ]
    return out
