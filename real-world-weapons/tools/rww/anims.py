"""
Animation authoring for the three weapons.

Third-person poses are authored as *sword* configurations in the player's body
frame (display space: +x = player's right, -z = front, +y = up):
    two-handed: grip centre C, blade direction g, true-edge direction e
    one-handed: right-hand point h, g, e  (+ an independent left-arm pose)
and solved with stiff-arm IK (Minecraft arms have no elbow) into Bedrock Euler
angles for rightArm / leftArm / rightItem (+ small shoulder offsets).

Runtime player animations (played by the script with Entity.playAnimation):
  animation.rww.<w>.arms  override_previous_animation, bones rightArm/leftArm/rightItem
      - locomotion blend: guard, walk, sprint, sneak, airborne, landing, swim (+ carry for the Zweihander)
      - equip intro driven by query.anim_time
      - three attack variants driven by the engine's variable.attack_time (exactly synced to the
        swing / attack cooldown), variant chosen by a client-side combo counter
      - first-person branch (variable.is_first_person): vanilla first-person arm pose without the
        vanilla swing, plus weapon-specific first-person attack motion
  animation.rww.<w>.body  additive, bones body / rightLeg / leftLeg (torso twist, lunges, steps)

Attachable animations: animation.rww.<w>.hold_tp / hold_fp place the sword in the hand.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import posing as P
from .bedrock import euler_file_to_matrix

R_TP = euler_file_to_matrix((90.0, 0.0, 0.0))[:3, :3]     # attachable third-person grip (blade ⟂ forearm)
SPACING = {"katana": 4.0, "zweihander": 4.4}
SWING = {"rapier": 0.55, "katana": 0.70, "zweihander": 1.00}
EQUIP_TIME = {"rapier": 0.45, "katana": 0.6, "zweihander": 0.8}

# Attachable transforms (solved with tools/rww/posing + previews; see docs/technical_design.md)
HOLD_TP = {w: {"rotation": [90.0, 0.0, 0.0], "position": [0.0, 0.0, 0.0]} for w in ("rapier", "zweihander", "katana")}
HOLD_FP = {
    "rapier": {"rotation": [134.18, 36.42, -64.49], "position": [-2.05, -1.33, -4.73]},
    "zweihander": {"rotation": [129.21, 19.38, -38.3], "position": [-0.59, -1.33, -4.12]},
    "katana": {"rotation": [128.28, 46.09, -68.05], "position": [-2.51, -0.23, -6.3]},
}

CHANNELS = [("rightarm", "rotation"), ("rightarm", "position"), ("rightitem", "rotation"),
            ("leftarm", "rotation"), ("leftarm", "position")]


def U(*v):
    return P.unit(np.array(v, float))


def lead(g):
    """Leading-edge direction for a horizontal right-to-left sweep: up x blade."""
    return P.unit(np.cross([0.0, 1.0, 0.0], g))


def lean(v, deg):
    """Express a world direction in the frame of a body leaning forward by deg (vanilla sneak leans 28°)."""
    a = math.radians(deg)
    # body leaning forward = display Rx(-deg); body-frame vector = Rx(+deg) * world
    c, s = math.cos(a), math.sin(a)
    x, y, z = v
    return np.array([x, y * c - z * s, y * s + z * c])


@dataclass
class Spec:
    kind: str                         # 'two' | 'one'
    g: Sequence[float]                # blade direction
    e: Optional[Sequence[float]]      # true-edge direction (None: carried from the previous key, no wrist roll)
    C: Optional[Sequence[float]] = None
    h: Optional[Sequence[float]] = None
    left: Optional[dict] = None       # one-handed: {'h': (...), 'fwd': (...)} or {'dir': (...)}
    lam: float = 0.25


@dataclass
class Pose:
    v: Dict[Tuple[str, str], np.ndarray] = field(default_factory=dict)
    info: dict = field(default_factory=dict)


def _file_pos(p):
    return np.array([-p[0], p[1], p[2]])


def _fist_fwd(pose: Optional[Pose], bone: str):
    if pose is None:
        return None
    return euler_file_to_matrix(tuple(pose.v[(bone, "rotation")]))[:3, :3] @ P.FIST_FWD


def solve(weapon: str, s: Spec, prev: Optional[Pose] = None, continuity: float = 0.8) -> Pose:
    """IK for one key.  `prev` (the previous key) keeps the forearm twist continuous: the
    twist hint blends the blade direction with the previous fist direction."""
    g = P.unit(s.g)
    fR, fL = _fist_fwd(prev, "rightarm"), _fist_fwd(prev, "leftarm")

    def hint(base, f):
        return base if f is None else P.unit(np.asarray(base, float) + continuity * f)
    e = np.asarray(s.e, float)
    e = P.unit(e - g * np.dot(e, g))
    out = Pose()
    if s.kind == "two":
        d = SPACING[weapon]
        C = P.two_hand_center(s.C, g, d, lam=s.lam)
        hR, hL = C + g * d / 2, C - g * d / 2
        RR, pR = P.solve_arm("right", hR, hint(g, fR))
        RL, pL = P.solve_arm("left", hL, hint(g, fL))
        out.info = {"C": C, "shrugR": float(np.linalg.norm(pR)), "shrugL": float(np.linalg.norm(pL))}
    else:
        hR = np.asarray(s.h, float)
        RR, pR = P.solve_arm("right", hR, hint(g, fR))
        lf = s.left or {"h": (-6.0, 15.0, -1.0), "fwd": (0, 0, -1)}
        if "dir" in lf:
            hl = P.SHOULDER["left"] + P.ARM_LEN * P.unit(lf["dir"])
            RL, pL = P.solve_arm("left", hl, lf.get("fwd", (0, 0, -1)))
        elif "h" in lf:
            RL, pL = P.solve_arm("left", lf["h"], lf.get("fwd", (0, 0, -1)))
        else:
            RL = euler_file_to_matrix(lf["euler"])[:3, :3]
            pL = np.zeros(3)
        out.info = {"shrugR": float(np.linalg.norm(pR)), "shrugL": float(np.linalg.norm(pL))}
    Rw = P.wrist_for(RR, g, e, R_TP)
    out.v[("rightarm", "rotation")] = np.array(P.file_euler_from_matrix(RR))
    out.v[("rightarm", "position")] = _file_pos(pR)
    out.v[("rightitem", "rotation")] = np.array(P.file_euler_from_matrix(Rw))
    out.v[("leftarm", "rotation")] = np.array(P.file_euler_from_matrix(RL))
    out.v[("leftarm", "position")] = _file_pos(pL)
    return out


def unwrap_to(pose: Pose, ref: Pose) -> Pose:
    """Choose equivalent Euler angles closest to ref (avoid 360° spins when blending)."""
    q = Pose(dict(pose.v), pose.info)
    for k, val in pose.v.items():
        if k[1] != "rotation":
            continue
        r = ref.v[k]
        best = None
        x, y, z = val
        # (x, y, z) and (x+180, 180-y, z+180) describe the same ZYX rotation
        for cand in ((x, y, z), (x + 180, 180 - y, z + 180)):
            c = np.array([r[i] + ((cand[i] - r[i] + 180) % 360) - 180 for i in range(3)])
            cost = float(np.sum(np.abs(c - r)))
            if best is None or cost < best[0]:
                best = (cost, c)
        q.v[k] = best[1]
    return q


# ============================================================================ weapon libraries
# (all coordinates: display space, player body frame)

def lib_rapier():
    guard_left = {"h": (-3.4, 20.6, -5.6), "fwd": (0.2, 1.0, -0.3)}   # left hand raised before the chest (Capoferro)
    edge_down = (0, -1, 0)
    guard = Spec("one", g=U(-0.14, 0.2, -0.97), e=edge_down, h=(3.6, 17.0, -6.0), left=guard_left)
    poses = {
        "guard": guard,
        "walk": Spec("one", g=U(-0.1, 0.05, -0.99), e=edge_down, h=(4.4, 16.0, -5.2), left={"h": (-4.6, 17.0, -5.4), "fwd": (0.2, 1, -0.4)}),
        "sprint": Spec("one", g=U(0.0, -0.42, -0.9), e=edge_down, h=(5.6, 15.5, -2.8), left={"h": (-6.4, 15.6, -1.6)}),
        "sneak": Spec("one", g=lean(U(-0.12, 0.05, -0.99), 28), e=lean(edge_down, 28), h=(3.4, 17.6, -5.6), left=guard_left),
        "air": Spec("one", g=U(-0.1, 0.32, -0.94), e=edge_down, h=(4.2, 18.4, -5.4), left={"h": (-8.6, 19.0, -2.0), "fwd": (0, 1, 0)}),
        "swim": Spec("one", g=U(0.0, 0.98, -0.2), e=(0, 0, -1), h=(4.0, 28.6, -1.6), left={"h": (-6.0, 15, -1.0)}),
        "equip": Spec("one", g=U(-0.55, -0.55, 0.62), e=(0, 1, 0), h=(0.6, 15.6, -3.6), left={"h": (-5.6, 15.0, -2.4)}),
    }
    attacks = [
        [  # 0: stoccata — straight lunge thrust under the opponent's sword
            (0.0, guard),
            (0.07, Spec("one", g=U(-0.1, 0.12, -0.99), e=edge_down, h=(4.4, 16.0, -4.4), left=guard_left)),
            (0.20, Spec("one", g=U(-0.08, 0.04, -1.0), e=U(0.45, -0.89, 0), h=(2.6, 20.4, -6.9), left={"dir": (-0.45, 0.42, 0.79), "fwd": (0, 1, 0)})),
            (0.34, Spec("one", g=U(-0.08, 0.02, -1.0), e=U(0.45, -0.89, 0), h=(2.8, 20.0, -6.8), left={"dir": (-0.45, 0.38, 0.81), "fwd": (0, 1, 0)})),
            (0.62, Spec("one", g=U(-0.12, 0.14, -0.98), e=None, h=(3.4, 18.0, -6.3), left=guard_left)),
            (1.0, guard),
        ],
        [  # 1: imbroccata — descending thrust from a high hand (seconda: hand pronated, true edge outward)
            (0.0, guard),
            (0.08, Spec("one", g=U(-0.06, -0.12, -0.99), e=U(0.97, 0.2, 0.0), h=(3.9, 22.2, -5.7), left=guard_left)),
            (0.22, Spec("one", g=U(-0.08, -0.28, -0.96), e=U(0.97, 0.15, 0.0), h=(2.8, 21.4, -6.8), left={"dir": (-0.5, 0.3, 0.81), "fwd": (0, 1, 0)})),
            (0.36, Spec("one", g=U(-0.09, -0.24, -0.97), e=None, h=(2.9, 21.0, -6.7), left={"dir": (-0.5, 0.3, 0.81), "fwd": (0, 1, 0)})),
            (0.64, Spec("one", g=U(-0.13, 0.1, -0.98), e=None, h=(3.3, 18.6, -6.2), left=guard_left)),
            (1.0, guard),
        ],
        [  # 2: punta riversa — thrust from the inside line, hand supinated (quarta)
            (0.0, guard),
            (0.08, Spec("one", g=U(0.38, 0.1, -0.92), e=U(0.7, -0.7, 0), h=(1.2, 16.6, -5.4), left=guard_left)),
            (0.22, Spec("one", g=U(-0.22, 0.06, -0.97), e=U(-0.75, -0.5, 0), h=(1.4, 19.6, -7.0), left={"dir": (-0.48, 0.34, 0.81), "fwd": (0, 1, 0)})),
            (0.36, Spec("one", g=U(-0.2, 0.04, -0.98), e=U(-0.75, -0.5, 0), h=(1.6, 19.2, -6.9), left={"dir": (-0.48, 0.34, 0.81), "fwd": (0, 1, 0)})),
            (0.64, Spec("one", g=U(-0.16, 0.16, -0.97), e=None, h=(3.0, 17.8, -6.2), left=guard_left)),
            (1.0, guard),
        ],
    ]
    return poses, attacks


def lib_katana():
    e_dn = U(0, -0.91, -0.42)
    guard = Spec("two", g=U(0.0, 0.42, -0.91), e=e_dn, C=(0.0, 17.4, -6.0))      # chudan-no-kamae
    poses = {
        "guard": guard,
        "walk": Spec("two", g=U(0.0, 0.36, -0.93), e=e_dn, C=(0.0, 17.0, -5.8)),
        "sprint": Spec("one", g=U(0.1, -0.5, 0.86), e=(0, 1, 0), h=(6.0, 15.4, -1.2), left={"h": (-6.4, 15.6, -1.6)}),   # blade trailing low
        "sneak": Spec("two", g=lean(U(0.0, -0.32, -0.95), 28), e=lean(U(0, -0.95, 0.32), 28), C=(0.0, 17.2, -5.6)),   # gedan
        "air": Spec("two", g=U(0.0, 0.8, -0.6), e=U(0, -0.6, -0.8), C=(0.4, 19.6, -5.0)),
        "swim": Spec("one", g=U(0.0, 0.98, -0.2), e=(0, 0, -1), h=(4.0, 28.6, -1.6), left={"h": (-6.0, 15, -1.0)}),
        "equip": Spec("one", g=U(-0.55, -0.4, 0.73), e=(0, 1, 0), h=(0.4, 16.0, -3.4), left={"h": (-3.6, 16.2, -3.0), "fwd": (0, 0, -1)}),
    }
    attacks = [
        [  # 0: kesa-giri — diagonal cut from the right shoulder down to the left hip
            (0.0, guard),
            (0.08, Spec("two", g=U(0.28, 0.88, 0.38), e=U(-0.5, 0.2, -0.84), C=(2.4, 21.8, -3.4))),
            (0.2, Spec("two", g=U(-0.5, 0.25, -0.83), e=U(-0.55, -0.8, 0.2), C=(0.6, 18.4, -6.4))),
            (0.32, Spec("two", g=U(-0.6, -0.5, -0.62), e=U(-0.45, -0.45, 0.77), C=(-0.9, 15.8, -5.2))),
            (0.6, Spec("two", g=U(-0.2, 0.18, -0.96), e=None, C=(-0.3, 16.6, -5.8))),
            (1.0, guard),
        ],
        [  # 1: kiri-age (gyaku-kesa) — rising diagonal from low left to high right
            (0.0, guard),
            (0.08, Spec("two", g=U(-0.55, -0.55, -0.62), e=U(0.3, 0.6, -0.74), C=(-1.0, 15.6, -5.0))),
            (0.2, Spec("two", g=U(0.12, 0.4, -0.91), e=U(0.55, 0.75, -0.36), C=(0.4, 18.6, -6.4))),
            (0.32, Spec("two", g=U(0.55, 0.68, -0.48), e=U(0.45, 0.6, 0.66), C=(2.0, 20.8, -4.8))),
            (0.6, Spec("two", g=U(0.18, 0.5, -0.85), e=None, C=(0.6, 18.0, -5.8))),
            (1.0, guard),
        ],
        [  # 2: kiri-oroshi — overhead vertical cut, then yoko-chiburi (flick to the right)
            (0.0, guard),
            (0.08, Spec("two", g=U(0.0, 0.72, 0.69), e=U(0, 0.69, -0.72), C=(0.2, 23.0, -2.8))),
            (0.18, Spec("two", g=U(0.0, 0.55, -0.83), e=U(0, -0.83, -0.55), C=(0.0, 21.0, -5.8))),
            (0.28, Spec("two", g=U(0.0, -0.18, -0.98), e=U(0, -0.98, 0.18), C=(0.0, 17.0, -6.4))),
            (0.5, Spec("two", g=U(0.5, -0.12, -0.86), e=None, C=(1.4, 16.8, -6.0))),
            (0.72, Spec("two", g=U(0.12, 0.3, -0.95), e=None, C=(0.4, 17.2, -6.0))),
            (1.0, guard),
        ],
    ]
    return poses, attacks


def lib_zweihander():
    e_dn = U(0, -0.83, -0.55)
    guard = Spec("two", g=U(-0.15, 0.55, -0.82), e=e_dn, C=(1.4, 16.8, -5.6))
    carry = Spec("one", g=U(0.32, 0.66, 0.68), e=U(0.2, -0.72, 0.66), h=(6.8, 18.2, -4.6),
                 left={"h": (-6.2, 15.0, -1.2)})                                  # marching carry on the right shoulder
    poses = {
        "guard": guard,
        "walk": Spec("two", g=U(-0.12, 0.5, -0.86), e=e_dn, C=(1.4, 16.6, -5.4)),
        "carry": carry,
        "sprint": carry,
        "sneak": Spec("two", g=lean(U(-0.1, -0.45, -0.89), 28), e=lean(U(0, -0.89, 0.45), 28), C=(1.0, 17.0, -5.2)),   # low guard (Alber)
        "air": Spec("two", g=U(-0.1, 0.75, -0.65), e=U(0, -0.65, -0.75), C=(1.4, 19.0, -4.8)),
        "swim": Spec("one", g=U(0.0, 0.98, -0.2), e=(0, 0, -1), h=(4.0, 28.6, -1.6), left={"h": (-6.0, 15, -1.0)}),
        "equip": Spec("one", g=U(0.1, -0.6, 0.79), e=(0, 0, -1), h=(6.2, 15.0, -2.0), left={"h": (-6.0, 15.0, -1.0)}),
    }
    attacks = [
        [  # 0: Oberhau — committed diagonal cut from over the right shoulder to low left
            (0.0, guard),
            (0.1, Spec("two", g=U(0.35, 0.62, 0.7), e=U(-0.3, 0.75, -0.6), C=(3.2, 22.6, -2.2))),
            (0.24, Spec("two", g=U(-0.6, 0.22, -0.77), e=U(-0.55, -0.8, 0.2), C=(0.8, 18.6, -6.4))),
            (0.36, Spec("two", g=U(-0.66, -0.52, -0.54), e=U(-0.4, -0.45, 0.8), C=(-1.4, 15.0, -5.0))),
            (0.52, Spec("two", g=U(-0.76, -0.58, -0.3), e=None, C=(-1.8, 14.6, -4.2))),
            (0.78, Spec("two", g=U(-0.3, 0.3, -0.9), e=None, C=(0.2, 16.4, -5.6))),
            (1.0, guard),
        ],
        [  # 1: Unterhau — rising backhand diagonal from low left to high right
            (0.0, guard),
            (0.1, Spec("two", g=U(-0.7, -0.52, -0.48), e=U(0.3, 0.55, -0.78), C=(-1.6, 14.8, -4.4))),
            (0.24, Spec("two", g=U(0.18, 0.32, -0.93), e=U(0.5, 0.78, -0.37), C=(0.8, 18.2, -6.4))),
            (0.36, Spec("two", g=U(0.6, 0.64, -0.46), e=U(0.42, 0.56, 0.71), C=(3.0, 21.2, -4.2))),
            (0.52, Spec("two", g=U(0.5, 0.8, 0.32), e=None, C=(3.2, 22.2, -3.2))),
            (0.78, Spec("two", g=U(0.1, 0.62, -0.78), e=None, C=(2.0, 18.6, -5.2))),
            (1.0, guard),
        ],
        [  # 2: Mittelhau — horizontal cut from the right across to the left at chest height (edge leads the sweep)
            (0.0, guard),
            (0.1, Spec("two", g=U(0.9, 0.2, 0.38), e=lead(U(0.9, 0.2, 0.38)), C=(3.6, 18.6, -3.0))),
            (0.24, Spec("two", g=U(0.0, 0.18, -0.98), e=lead(U(0.0, 0.18, -0.98)), C=(0.6, 18.4, -6.6))),
            (0.36, Spec("two", g=U(-0.9, 0.12, 0.4), e=lead(U(-0.9, 0.12, 0.4)), C=(-2.8, 18.0, -4.0))),
            (0.52, Spec("two", g=U(-0.85, 0.3, 0.42), e=None, C=(-3.0, 18.6, -3.4))),
            (0.78, Spec("two", g=U(-0.3, 0.5, -0.8), e=None, C=(0.0, 17.4, -5.6))),
            (1.0, guard),
        ],
    ]
    return poses, attacks


LIBS = {"rapier": lib_rapier, "katana": lib_katana, "zweihander": lib_zweihander}

# Additive torso / leg motion: per attack variant, keyframes of
# (t, body_rot (file xyz), right_leg_x, left_leg_x)  -- file convention (negative leg x = forward)
BODY_KEYS = {
    "rapier": [
        [(0, (0, 0, 0), 0, 0), (0.07, (2, 6, 0), 4, -4), (0.2, (14, -24, 0), -40, 26), (0.34, (12, -22, 0), -38, 24),
         (0.62, (5, -8, 0), -14, 8), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.08, (-4, 8, 0), 6, -6), (0.22, (12, -20, 0), -34, 22), (0.36, (10, -18, 0), -32, 20),
         (0.64, (4, -6, 0), -12, 6), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.08, (2, 14, 0), 4, -4), (0.22, (12, -16, 0), -36, 24), (0.36, (10, -14, 0), -34, 22),
         (0.64, (4, -5, 0), -12, 6), (1.0, (0, 0, 0), 0, 0)],
    ],
    "katana": [
        [(0, (0, 0, 0), 0, 0), (0.08, (-3, 16, 0), 6, -4), (0.2, (8, -10, 0), -20, 12), (0.32, (12, -22, 0), -24, 14),
         (0.6, (4, -6, 0), -8, 4), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.08, (6, -18, 0), -6, 6), (0.2, (4, 4, 0), -16, 10), (0.32, (-2, 18, 0), -20, 12),
         (0.6, (0, 5, 0), -6, 3), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.08, (-6, 0, 0), 4, -2), (0.18, (6, 0, 0), -16, 10), (0.28, (12, -4, 0), -22, 14),
         (0.5, (8, 8, 0), -18, 12), (0.72, (2, 2, 0), -6, 4), (1.0, (0, 0, 0), 0, 0)],
    ],
    "zweihander": [
        [(0, (0, 0, 0), 0, 0), (0.1, (-6, 30, 0), 14, -10), (0.24, (10, -12, 0), -22, 16), (0.36, (16, -34, 0), -30, 20),
         (0.52, (14, -38, 0), -28, 18), (0.78, (4, -10, 0), -8, 6), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.1, (12, -30, 0), -10, 12), (0.24, (4, 4, 0), -18, 14), (0.36, (-4, 30, 0), -24, 16),
         (0.52, (-6, 34, 0), -22, 14), (0.78, (0, 10, 0), -6, 4), (1.0, (0, 0, 0), 0, 0)],
        [(0, (0, 0, 0), 0, 0), (0.1, (2, 36, 0), 10, -8), (0.24, (6, 0, 0), -18, 12), (0.36, (8, -40, 0), -26, 18),
         (0.52, (6, -42, 0), -24, 16), (0.78, (2, -12, 0), -8, 4), (1.0, (0, 0, 0), 0, 0)],
    ],
}

# First-person attacks are authored in camera space (camera looks +z, screen-left = +x, up = +y):
# keys of (t, (ndc_x, ndc_y), depth, blade_dir, edge_dir) for the grip point, solved into a rightItem
# rotation + rightArm offset on top of the vanilla first-person arm pose.
FP_BASE = {
    "rapier": ((0.42, -0.55), 16.0, (0.38, 0.40, 0.83), (-0.3, -0.9, 0.3)),
    "zweihander": ((0.40, -0.62), 17.0, (0.45, 0.62, 0.64), (-0.5, -0.4, 0.75)),
    "katana": ((0.36, -0.55), 15.0, (0.30, 0.48, 0.82), (-0.15, -0.95, 0.25)),
}
FP_ATTACKS = {
    "rapier": [
        [(0.07, (0.46, -0.6), 14.5, (0.32, 0.32, 0.89), (-0.3, -0.9, 0.3)),
         (0.2, (0.16, -0.3), 21.0, (0.06, 0.1, 0.99), (0.0, -1.0, 0.1)),
         (0.34, (0.17, -0.32), 20.5, (0.07, 0.11, 0.99), (0.0, -1.0, 0.1)),
         (0.62, (0.32, -0.46), 17.5, (0.26, 0.3, 0.92), (-0.2, -0.95, 0.25))],
        [(0.08, (0.42, 0.02), 15.0, (0.3, -0.12, 0.95), (-0.95, 0.2, 0.25)),
         (0.22, (0.15, -0.16), 21.0, (0.08, -0.18, 0.98), (-0.95, 0.2, 0.2)),
         (0.36, (0.16, -0.18), 20.5, (0.09, -0.16, 0.98), (-0.95, 0.2, 0.2)),
         (0.64, (0.33, -0.45), 17.0, (0.3, 0.26, 0.92), (-0.3, -0.9, 0.3))],
        [(0.08, (0.08, -0.62), 15.0, (-0.28, 0.32, 0.9), (-0.6, -0.75, 0.25)),
         (0.22, (0.12, -0.33), 21.0, (0.02, 0.08, 1.0), (0.95, -0.3, 0.0)),
         (0.36, (0.13, -0.34), 20.5, (0.03, 0.09, 1.0), (0.95, -0.3, 0.0)),
         (0.64, (0.32, -0.48), 17.0, (0.3, 0.32, 0.9), (-0.3, -0.9, 0.3))],
    ],
    "katana": [
        [(0.08, (0.56, 0.02), 14.0, (0.22, 0.9, 0.38), (0.5, 0.05, 0.86)),
         (0.2, (0.14, -0.22), 16.0, (0.78, 0.18, 0.6), (0.3, -0.9, 0.3)),
         (0.32, (-0.26, -0.62), 15.0, (0.62, -0.52, 0.58), (-0.4, -0.5, 0.77)),
         (0.6, (0.2, -0.55), 15.0, (0.4, 0.3, 0.86), (-0.15, -0.95, 0.25))],
        [(0.08, (-0.18, -0.68), 15.0, (0.62, -0.48, 0.62), (-0.3, 0.75, 0.6)),
         (0.2, (0.18, -0.34), 16.0, (-0.08, 0.42, 0.9), (-0.55, 0.8, 0.2)),
         (0.32, (0.54, 0.06), 15.0, (-0.5, 0.66, 0.56), (-0.6, -0.1, 0.8)),
         (0.6, (0.4, -0.4), 15.0, (0.1, 0.5, 0.86), (-0.15, -0.95, 0.25))],
        [(0.08, (0.26, 0.3), 14.0, (0.06, 0.95, 0.3), (0.0, 0.3, -0.95)),
         (0.18, (0.16, 0.0), 16.0, (0.05, 0.55, 0.83), (0.0, -0.83, 0.55)),
         (0.28, (0.12, -0.48), 16.0, (0.0, -0.22, 0.97), (0.0, -0.97, -0.22)),
         (0.5, (0.42, -0.55), 15.0, (-0.46, -0.1, 0.88), (-0.88, 0.0, -0.46)),
         (0.72, (0.38, -0.55), 15.0, (0.2, 0.4, 0.89), (-0.15, -0.95, 0.25))],
    ],
    "zweihander": [
        [(0.1, (0.6, 0.12), 15.0, (0.25, 0.9, 0.35), (0.5, 0.0, 0.86)),
         (0.24, (0.12, -0.2), 17.0, (0.82, 0.18, 0.55), (0.3, -0.9, 0.3)),
         (0.36, (-0.32, -0.66), 16.0, (0.66, -0.5, 0.56), (-0.4, -0.5, 0.77)),
         (0.52, (-0.4, -0.72), 16.0, (0.7, -0.56, 0.44), (-0.4, -0.45, 0.8)),
         (0.78, (0.22, -0.6), 16.5, (0.42, 0.4, 0.81), (-0.5, -0.4, 0.75))],
        [(0.1, (-0.28, -0.74), 16.0, (0.68, -0.5, 0.54), (-0.3, 0.75, 0.6)),
         (0.24, (0.18, -0.36), 17.0, (-0.06, 0.45, 0.89), (-0.55, 0.8, 0.2)),
         (0.36, (0.6, 0.12), 15.0, (-0.52, 0.66, 0.54), (-0.6, -0.1, 0.8)),
         (0.52, (0.64, 0.18), 15.0, (-0.55, 0.7, 0.45), (-0.6, -0.1, 0.8)),
         (0.78, (0.44, -0.46), 16.5, (0.2, 0.6, 0.77), (-0.5, -0.4, 0.75))],
        [(0.1, (0.72, -0.3), 15.0, (-0.9, 0.2, 0.38), (0.38, 0.0, 0.92)),
         (0.24, (0.2, -0.36), 17.0, (0.0, 0.2, 0.98), (0.98, 0.0, -0.2)),
         (0.36, (-0.5, -0.4), 15.0, (0.9, 0.15, 0.4), (0.4, 0.0, -0.92)),
         (0.52, (-0.56, -0.42), 15.0, (0.88, 0.2, 0.42), (0.42, 0.0, -0.9)),
         (0.78, (0.2, -0.55), 16.5, (0.42, 0.5, 0.75), (-0.5, -0.4, 0.75))],
    ],
}


def _fp_targets(weapon: str):
    base = FP_BASE[weapon]
    out = []
    for keys in FP_ATTACKS[weapon]:
        out.append([(0.0,) + base] + list(keys) + [(1.0,) + base])
    return out


def solve_fp_keys(weapon: str):
    """Solve the camera-space first-person keys into (t, rightarm offset (file), rightitem rotation (file))."""
    from . import bedrock, player
    TH = math.tan(math.radians(70.25) / 2)
    TW = TH * 16 / 9
    pose, _ = player.compose({"first_person": True}, include_vanilla=True)
    # our fp branch: vanilla base arm pose, rightItem at (0,0,-1), no swing
    pm = player.player_matrices(pose)
    Mri = pm["rightitem"]
    Rarm = Mri[:3, :3]
    hold = HOLD_FP[weapon]
    Rhold = euler_file_to_matrix(tuple(hold["rotation"]))[:3, :3]
    ri_piv = bedrock.disp(player.PLAYER_GEO.bones["rightitem"].pivot)
    hold_pos = np.array([-hold["position"][0], hold["position"][1], hold["position"][2]])
    variants = []
    for keys in _fp_targets(weapon):
        out = []
        prev = np.zeros(3)
        for (t, ndc, depth, blade, edge) in keys:
            Rt = P.basis_from(P.unit(blade), -P.unit(edge))
            Rw = Rarm.T @ Rt @ Rhold.T
            e = np.array(P.file_euler_from_matrix(Rw))
            # unwrap against the previous key
            cands = [e, np.array([e[0] + 180, 180 - e[1], e[2] + 180])]
            best = None
            for c in cands:
                c = np.array([prev[i] + ((c[i] - prev[i] + 180) % 360) - 180 for i in range(3)])
                cost = float(np.sum(np.abs(c - prev)))
                if best is None or cost < best[0]:
                    best = (cost, c)
            e = best[1]
            prev = e
            # grip point after the wrist rotation (rotation about the rightItem pivot)
            Rw_m = euler_file_to_matrix(tuple(e))[:3, :3]
            grip_local = ri_piv + Rw_m @ hold_pos          # rightItem frame (pivot-relative offsets)
            grip_world = (Mri @ np.r_[grip_local, 1.0])[:3]
            target = np.array([-ndc[0] * depth * TW, 27.41 + ndc[1] * depth * TH, depth])
            delta_world = target - grip_world
            # arm position offsets are expressed in the body frame (= world at pitch 0 in first person)
            off_file = np.array([-delta_world[0], delta_world[1], delta_world[2]])
            out.append((t, off_file, e))
        # the base key must be exactly zero offset / zero rotation
        b0 = out[0]
        out = [(t, off - b0[1], rot - b0[2]) for (t, off, rot) in out]
        variants.append(out)
    return variants


# ============================================================================ Molang codegen

def num(x: float) -> str:
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


def lerp(a: str, b: str, t: str) -> str:
    if a == b:
        return a
    return f"math.lerp({a}, {b}, {t})"


def catmull(keys: List[Tuple[float, float]], T: str) -> str:
    """Piecewise cubic (Catmull-Rom, clamped ends) through (t, value) keys, as a Molang expression of T."""
    ts = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    n = len(keys)
    if all(abs(v - vs[0]) < 1e-4 for v in vs):
        return num(vs[0])
    segs = []
    for i in range(n - 1):
        p0 = vs[i - 1] if i > 0 else vs[i]
        p1, p2 = vs[i], vs[i + 1]
        p3 = vs[i + 2] if i + 2 < n else vs[i + 1]
        # tangents scaled for non-uniform spacing (Catmull-Rom on unit parameter)
        dt = ts[i + 1] - ts[i]
        m1 = (p2 - p0) / ((ts[i + 1] - ts[i - 1]) if i > 0 else dt) * dt if i > 0 else (p2 - p1) * 0.0
        m2 = (p3 - p1) / ((ts[i + 2] - ts[i]) if i + 2 < n else dt) * dt if i + 2 < n else (p2 - p1) * 0.0
        a = p1
        b = m1
        c = 3 * (p2 - p1) - 2 * m1 - m2
        d = 2 * (p1 - p2) + m1 + m2
        u = f"(({T} - {num(ts[i])}) * {num(1.0 / dt)})"
        poly = f"({num(a)} + {u} * ({num(b)} + {u} * ({num(c)} + {u} * {num(d)})))"
        segs.append((ts[i + 1], poly))
    expr = segs[-1][1]
    for t_end, poly in reversed(segs[:-1]):
        expr = f"({T} < {num(t_end)} ? {poly} : {expr})"
    return expr


def eval_catmull(keys, t):
    """Python twin of catmull() (for previews/checks)."""
    from . import molang
    return molang.evaluate(catmull(keys, "v.t"), molang.Context(variables={"t": t}))


# ============================================================================ solving + assembling

def _interp_spec(a: Spec, b: Spec, f: float) -> Spec:
    """Intermediate spec between two keys (positions lerp, directions nlerp)."""
    def L(x, y):
        return None if x is None or y is None else tuple(np.array(x, float) + (np.array(y, float) - np.array(x, float)) * f)

    def N(x, y):
        v = np.array(x, float) * (1 - f) + np.array(y, float) * f
        if np.linalg.norm(v) < 1e-6:
            v = np.array(y, float)
        return tuple(P.unit(v))
    if a.kind != b.kind:
        return b if f >= 0.5 else a
    # whole sword orientation: shortest rotation (quaternion slerp) between the two keys
    Ra = P.sword_basis(P.unit(a.g), P.unit(np.asarray(a.e, float) - P.unit(a.g) * np.dot(a.e, P.unit(a.g))))
    Rb = P.sword_basis(P.unit(b.g), P.unit(np.asarray(b.e, float) - P.unit(b.g) * np.dot(b.e, P.unit(b.g))))
    Rf = P.quat_to_mat(P.slerp(P.mat_to_quat(Ra), P.mat_to_quat(Rb), f))
    g_f, e_f = tuple(Rf[:, 1]), tuple(-Rf[:, 2])
    left = None
    def lh(lf):
        if lf is None:
            return None
        if "dir" in lf:
            return tuple(P.SHOULDER["left"] + P.ARM_LEN * P.unit(lf["dir"]))
        return lf.get("h")
    def sph(pa, pb, shoulder):
        """interpolate a hand target around the shoulder: slerp direction, lerp reach"""
        va, vb = np.asarray(pa, float) - shoulder, np.asarray(pb, float) - shoulder
        la, lb = np.linalg.norm(va), np.linalg.norm(vb)
        ua, ub = va / la, vb / lb
        d = float(np.clip(np.dot(ua, ub), -1, 1))
        th = math.acos(d)
        if th < 1e-4:
            u = ua
        else:
            u = (math.sin((1 - f) * th) * ua + math.sin(f * th) * ub) / math.sin(th)
        return tuple(shoulder + u * (la + (lb - la) * f))
    if a.left and b.left and lh(a.left) is not None and lh(b.left) is not None:
        left = {"h": sph(lh(a.left), lh(b.left), P.SHOULDER["left"]),
                "fwd": N(a.left.get("fwd", (0, 0, -1)), b.left.get("fwd", (0, 0, -1)))}
    else:
        left = (b.left if f >= 0.5 else a.left)
    h = None if a.h is None or b.h is None else sph(a.h, b.h, P.SHOULDER["right"])
    return Spec(a.kind, g_f, e_f, L(a.C, b.C), h, left, a.lam)


@dataclass
class WeaponAnim:
    weapon: str
    poses: Dict[str, Pose]
    attacks: List[List[Tuple[float, Pose]]]
    report: List[str]


def _body_rot_at(weapon: str, variant: int, t: float) -> np.ndarray:
    keys = BODY_KEYS[weapon][variant]
    for i in range(len(keys) - 1):
        t0, r0 = keys[i][0], np.array(keys[i][1], float)
        t1, r1 = keys[i + 1][0], np.array(keys[i + 1][1], float)
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return r0 + (r1 - r0) * f
    return np.array(keys[-1][1], float)


BODY_PIVOT = np.array([0.0, 24.0, 0.0])


def to_body(s: Spec, body_rot_file) -> Spec:
    """Re-express a world-frame (waist-frame) sword spec in the frame of a body rotated by body_rot_file,
    so the sword ends up where it was authored even while the torso twists and leans."""
    Rb = euler_file_to_matrix(tuple(body_rot_file))[:3, :3]
    Ri = Rb.T

    def pt(p):
        return None if p is None else tuple(Ri @ (np.asarray(p, float) - BODY_PIVOT) + BODY_PIVOT)

    def dr(d):
        return tuple(Ri @ np.asarray(d, float))
    left = None
    if s.left is not None:
        left = dict(s.left)
        if "dir" in left:
            left["dir"] = dr(left["dir"])
        if "h" in left:
            left["h"] = pt(left["h"])
        if "fwd" in left:
            left["fwd"] = dr(left["fwd"])
    return Spec(s.kind, dr(s.g), dr(s.e), pt(s.C), pt(s.h), left, s.lam)


def solve_weapon(weapon: str, substeps: int = 2) -> WeaponAnim:
    specs, atk_specs = LIBS[weapon]()
    report = []
    guard = solve(weapon, specs["guard"])
    poses = {"guard": guard}
    for k, s in specs.items():
        if k == "guard":
            continue
        poses[k] = unwrap_to(solve(weapon, s), guard)
    for k, p in poses.items():
        report.append(f"{weapon}.{k}: shrug R {p.info['shrugR']:.2f} L {p.info['shrugL']:.2f}")
    attacks = []
    for vi, keys in enumerate(atk_specs):
        keys = _resolve_edges(keys)
        out = []
        prev = guard
        for i, (t, s) in enumerate(keys):
            if i > 0 and substeps:
                t0, s0 = keys[i - 1]
                for j in range(1, substeps + 1):
                    f = j / (substeps + 1)
                    tt = t0 + (t - t0) * f
                    ps = unwrap_to(solve(weapon, to_body(_interp_spec(s0, s, f), _body_rot_at(weapon, vi, tt)), prev), prev)
                    out.append((tt, ps))
                    prev = ps
            p = unwrap_to(solve(weapon, to_body(s, _body_rot_at(weapon, vi, t)), prev if i > 0 else None), prev)
            out.append((t, p))
            prev = p
            report.append(f"{weapon}.atk{vi}@{t}: shrug R {p.info['shrugR']:.2f} L {p.info['shrugL']:.2f}")
        attacks.append(_consistent_eulers(out, guard))
    return WeaponAnim(weapon, poses, attacks, report)


def _resolve_edges(keys):
    """Keys with e=None get the previous key's edge carried along the blade's minimal rotation
    (parallel transport): the swordsman keeps the wrist still through follow-through / recovery."""
    out = []
    prev_g = prev_e = None
    for t, s in keys:
        g = P.unit(s.g)
        if s.e is None:
            R = P.rot_align(prev_g, g)
            e = R @ prev_e
            s = Spec(s.kind, s.g, tuple(e), s.C, s.h, s.left, s.lam)
        e = np.asarray(s.e, float)
        prev_g, prev_e = g, P.unit(e - g * np.dot(e, g))
        out.append((t, s))
    return out


def _wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def _consistent_eulers(keys: List[Tuple[float, Pose]], guard: Pose) -> List[Tuple[float, Pose]]:
    """Pick, per bone rotation, which of the two equivalent ZYX Euler forms each key uses
    (dynamic programming, endpoints pinned to the guard's canonical angles), then unwrap the
    chain so that consecutive keys differ by < 180 degrees per axis.  Prevents Euler blends
    from sweeping through unrelated rotations."""
    n = len(keys)
    out = [Pose(dict(p.v), p.info) for _, p in keys]
    for k in [c for c in CHANNELS if c[1] == "rotation"]:
        def forms(v):
            a = np.array([_wrap(x) for x in v])
            b = np.array([_wrap(v[0] + 180.0), _wrap(180.0 - v[1]), _wrap(v[2] + 180.0)])
            return [a, b]
        g = np.array(guard.v[k], float)
        cand = [forms(p.v[k]) for _, p in keys]
        cand[0] = [g]
        cand[-1] = [g]
        INF = 1e18
        cost = [[INF] * len(c) for c in cand]
        back = [[0] * len(c) for c in cand]
        cost[0][0] = 0.0
        for i in range(1, n):
            for j, cj in enumerate(cand[i]):
                for m, cm in enumerate(cand[i - 1]):
                    c = cost[i - 1][m] + float(np.sum(np.abs([_wrap(x) for x in (cj - cm)])))
                    if c < cost[i][j]:
                        cost[i][j], back[i][j] = c, m
        j = 0
        seq = [None] * n
        for i in range(n - 1, -1, -1):
            seq[i] = cand[i][j]
            j = back[i][j]
        vals = [g.copy()]
        for i in range(1, n):
            vals.append(vals[-1] + np.array([_wrap(x) for x in (seq[i] - vals[-1])]))
        drift = vals[-1] - g
        if np.max(np.abs(drift)) > 1e-6:
            raise ValueError(f"{k}: attack keys wind a whole turn ({np.round(drift, 1)}); fix the edge directions")
        for i in range(n):
            out[i].v[k] = vals[i]
    return [(keys[i][0], out[i]) for i in range(n)]


_FP_CACHE: Dict[str, list] = {}


def _fp(weapon):
    if weapon not in _FP_CACHE:
        _FP_CACHE[weapon] = solve_fp_keys(weapon)
    return _FP_CACHE[weapon]


STATE_UPDATE = (
    "v.rww_k = math.min(1.0, math.clamp(q.delta_time, 0.0, 0.1) * 11.0);"
    "v.rww_swim_t = (q.is_swimming || q.is_crawling) ? 1.0 : 0.0;"
    "v.rww_air_t = (!q.is_on_ground && !q.is_riding && !q.is_in_water && v.rww_swim_t < 0.5) ? 1.0 : 0.0;"
    "v.rww_sprint_t = (q.is_sprinting && v.rww_air_t < 0.5 && v.rww_swim_t < 0.5 && !q.is_sneaking) ? 1.0 : 0.0;"
    "v.rww_walk_t = math.clamp(q.modified_move_speed * 1.6, 0.0, 1.0) * (1.0 - v.rww_sprint_t) * (1.0 - v.rww_air_t) * (1.0 - v.rww_swim_t) * (q.is_riding ? 0.0 : 1.0);"
    "v.rww_sneak_t = (q.is_sneaking && v.rww_swim_t < 0.5) ? 1.0 : 0.0;"
    "v.rww_walk = (v.rww_walk ?? 0.0) + (v.rww_walk_t - (v.rww_walk ?? 0.0)) * v.rww_k;"
    "v.rww_sprint = (v.rww_sprint ?? 0.0) + (v.rww_sprint_t - (v.rww_sprint ?? 0.0)) * v.rww_k;"
    "v.rww_sneak = (v.rww_sneak ?? 0.0) + (v.rww_sneak_t - (v.rww_sneak ?? 0.0)) * v.rww_k;"
    "v.rww_air = (v.rww_air ?? 0.0) + (v.rww_air_t - (v.rww_air ?? 0.0)) * v.rww_k * 0.7;"
    "v.rww_swim = (v.rww_swim ?? 0.0) + (v.rww_swim_t - (v.rww_swim ?? 0.0)) * v.rww_k * 0.6;"
    "v.rww_land = (q.is_on_ground && (v.rww_wasair ?? 0.0) > 0.5 && (v.rww_fallv ?? 0.0) < -5.0) ? 1.0 : math.max(0.0, (v.rww_land ?? 0.0) - math.clamp(q.delta_time, 0.0, 0.1) * 4.0);"
    "v.rww_fallv = q.is_on_ground ? 0.0 : math.min(v.rww_fallv ?? 0.0, q.vertical_speed);"
    "v.rww_wasair = q.is_on_ground ? 0.0 : 1.0;"
    "v.rww_at = math.max(v.attack_time ?? 0.0, 0.0);"
    "v.rww_edge = (v.rww_at > 0.0 && ((v.rww_pat ?? 0.0) <= 0.0 || v.rww_at < (v.rww_pat ?? 0.0) - 0.25)) ? 1.0 : 0.0;"
    "v.rww_combo = v.rww_edge > 0.5 ? ((q.life_time - (v.rww_lat ?? -99.0)) > 2.5 ? 0.0 : math.mod((v.rww_combo ?? 0.0) + 1.0, 3.0)) : (v.rww_combo ?? 0.0);"
    "v.rww_lat = v.rww_edge > 0.5 ? q.life_time : (v.rww_lat ?? -99.0);"
    "v.rww_pat = v.rww_at;"
    "v.rww_aw = v.rww_at > 0.0 ? math.clamp(math.min(v.rww_at / 0.05, (1.0 - v.rww_at) / 0.12), 0.0, 1.0) : 0.0;"
)


def state_update(weapon: str) -> str:
    hb = f"v.rww_hb_{weapon}"
    eq0 = f"v.rww_eq0_{weapon}"
    s = STATE_UPDATE
    # equip intro: a fresh start is detected when this weapon's heartbeat is older than 0.3 s
    s += f"{eq0} = (q.life_time - ({hb} ?? -99.0)) > 0.3 ? q.life_time : ({eq0} ?? q.life_time);"
    s += f"{hb} = q.life_time;"
    s += f"v.rww_eq = math.hermite_blend(math.clamp((q.life_time - {eq0}) / {num(EQUIP_TIME[weapon])}, 0.0, 1.0));"
    if weapon == "zweihander":
        # marching carry on the shoulder when not fighting (no attack for 4 s), or while sprinting
        s += ("v.rww_carry_t = ((q.life_time - (v.rww_lat ?? -99.0)) > 4.0 && v.rww_sneak_t < 0.5 && v.rww_air_t < 0.5) || v.rww_sprint_t > 0.5 ? 1.0 : 0.0;"
              "v.rww_carry = (v.rww_carry ?? 1.0) + (v.rww_carry_t - (v.rww_carry ?? 1.0)) * v.rww_k * 0.5;")
    return s


GAIT = "q.modified_distance_moved * 38.17"


def _osc(weapon: str, bone: str, channel: str, axis: int) -> Dict[str, str]:
    """Extra procedural terms per locomotion state (strings added to the solved pose values)."""
    out: Dict[str, str] = {}
    two = weapon in ("katana", "zweihander")
    breathe = "math.sin(q.life_time * 90.0) * 0.12"
    if channel == "position" and axis == 1:
        out["guard"] = breathe
        if two or bone == "rightarm":
            out["walk"] = f"-math.abs(math.sin({GAIT})) * 0.45"
    if weapon == "rapier" and bone == "leftarm" and channel == "rotation" and axis == 0:
        out["walk"] = f"math.cos({GAIT}) * 16.0"
        out["sprint"] = f"math.cos({GAIT}) * 38.0"
    if bone == "leftarm" and channel == "rotation" and axis == 0 and weapon in ("katana", "zweihander"):
        out["sprint"] = f"math.cos({GAIT}) * 38.0"
        if weapon == "zweihander":
            out["carry"] = f"math.cos({GAIT}) * 22.0 * v.rww_walk"
    if bone == "rightarm" and channel == "rotation" and axis == 0:
        out["sprint"] = f"-math.cos({GAIT}) * 14.0"
    if bone == "leftarm" and channel == "rotation" and axis == 2:
        out["swim"] = "math.sin(q.life_time * 277.0) * 50.0"
    if bone == "leftarm" and channel == "rotation" and axis == 0:
        out["swim"] = "math.cos(q.life_time * 277.0) * 70.0 - 40.0"
    return out


def _tp_expr(wa: WeaponAnim, key) -> List[str]:
    bone, channel = key
    exprs = []
    order = ["walk", "carry", "sneak", "sprint", "air", "swim"]
    weights = {"walk": "v.rww_walk", "carry": "v.rww_carry", "sneak": "v.rww_sneak", "sprint": "v.rww_sprint",
               "air": "v.rww_air", "swim": "v.rww_swim"}
    for ax in range(3):
        osc = _osc(wa.weapon, bone, channel, ax)
        g = wa.poses["guard"].v[key][ax]
        e = num(g) if "guard" not in osc else f"({num(g)} + {osc['guard']})"
        for st in order:
            if st not in wa.poses:
                continue
            val = wa.poses[st].v[key][ax]
            term = num(val) if st not in osc else f"({num(val)} + {osc[st]})"
            e = lerp(e, term, weights[st])
        if channel == "position" and ax == 1 and bone in ("rightarm", "leftarm"):
            e = f"({e} - v.rww_land * 1.4)"
        # equip intro
        e = lerp(num(wa.poses["equip"].v[key][ax]), e, "v.rww_eq")
        # attacks
        variants = []
        for keys in wa.attacks:
            variants.append(catmull([(t, p.v[key][ax]) for t, p in keys], "v.rww_at"))
        atk = f"(v.rww_combo < 0.5 ? {variants[0]} : (v.rww_combo < 1.5 ? {variants[1]} : {variants[2]}))"
        e = lerp(e, atk, "v.rww_aw")
        exprs.append(e)
    return exprs


# vanilla first-person arm pose (reproduced so the vanilla swing can be replaced by ours)
FP_ARM_ROT = (95.0, -45.0, 115.0)
FP_ARM_POS = ("13.5", "-10.0 - 10.0 * (1.0 - (v.player_arm_height ?? 1.0)) - math.abs(math.cos(-q.walk_distance * 180.0)) * (v.hand_bob ?? 0.0) * 15.0",
              "12.0")
FP_ARM_POS_X_BOB = "math.sin(-q.walk_distance * 180.0) * (v.hand_bob ?? 0.0) * 9.75"


def _fp_exprs(weapon: str, key) -> List[str]:
    bone, channel = key
    keys = _fp(weapon)
    out = []
    for ax in range(3):
        if bone == "leftarm":
            out.append("0")
            continue
        if bone == "rightarm" and channel == "rotation":
            out.append(num(FP_ARM_ROT[ax]))
            continue
        if bone == "rightarm" and channel == "position":
            variants = [catmull([(t, float(pos[ax])) for t, pos, rot in v], "v.rww_at") for v in keys]
            atk = f"(v.rww_combo < 0.5 ? {variants[0]} : (v.rww_combo < 1.5 ? {variants[1]} : {variants[2]}))"
            base = FP_ARM_POS[ax] if ax != 0 else f"({FP_ARM_POS[0]} + {FP_ARM_POS_X_BOB})"
            out.append(f"({base} + v.rww_aw * {atk})")
            continue
    return out


def _fp_item(weapon: str, channel: str) -> List[str]:
    keys = _fp(weapon)
    out = []
    for ax in range(3):
        if channel == "position":
            out.append("0" if ax != 1 else "math.sin(q.life_time * 45.0) * 0.5")
            continue
        variants = [catmull([(t, float(rot[ax])) for t, pos, rot in v], "v.rww_at") for v in keys]
        out.append(f"(v.rww_aw * (v.rww_combo < 0.5 ? {variants[0]} : (v.rww_combo < 1.5 ? {variants[1]} : {variants[2]})))")
    return out


def arms_animation(wa: WeaponAnim) -> dict:
    w = wa.weapon
    bones: Dict[str, dict] = {"rightarm": {}, "rightitem": {}, "leftarm": {}}
    for key in CHANNELS:
        bone, channel = key
        tp = _tp_expr(wa, key)
        fp = _fp_item(w, channel) if bone == "rightitem" else _fp_exprs(w, key)
        bones[bone][channel] = [f"v.is_first_person ? {fp[i]} : {tp[i]}" for i in range(3)]
    fpi_pos = _fp_item(w, "position")
    bones["rightitem"]["position"] = [f"v.is_first_person ? {fpi_pos[i]} : 0" for i in range(3)]
    bones["rightitem"]["position"][2] = "v.is_first_person ? -1.0 : 0"
    # all per-frame state is computed once, in the first channel evaluated
    first = bones["rightarm"]["rotation"][0]
    bones["rightarm"]["rotation"][0] = f"{state_update(w)}return {first};"
    return {"loop": True, "override_previous_animation": True, "bones": bones}


def body_animation(wa: WeaponAnim) -> dict:
    w = wa.weapon
    keys = BODY_KEYS[w]
    tp = "(1.0 - v.is_first_person)"
    rot = []
    for ax in range(3):
        variants = [catmull([(k[0], k[1][ax]) for k in v], "v.rww_at") for v in keys]
        atk = f"(v.rww_combo < 0.5 ? {variants[0]} : (v.rww_combo < 1.5 ? {variants[1]} : {variants[2]}))"
        extra = ""
        if ax == 1:
            # cancel the vanilla attack body twist, add a small two-handed walking sway / equip twist
            extra = " - (v.attack_body_rot_y ?? 0.0)"
            if w != "rapier":
                extra += f" + math.sin({GAIT}) * 3.0 * (v.rww_walk ?? 0.0)"
            extra += " + (1.0 - (v.rww_eq ?? 1.0)) * " + {"rapier": "18.0", "katana": "26.0", "zweihander": "-14.0"}[w]
        if ax == 0 and w == "rapier":
            extra = " + (v.rww_sneak ?? 0.0) * -6.0"
        rot.append(f"{tp} * ((v.rww_aw ?? 0.0) * {atk}{extra})")
    legs = {}
    for li, leg in ((2, "rightleg"), (3, "leftleg")):
        variants = [catmull([(k[0], k[li]) for k in v], "v.rww_at") for v in keys]
        atk = f"(v.rww_combo < 0.5 ? {variants[0]} : (v.rww_combo < 1.5 ? {variants[1]} : {variants[2]}))"
        stance = {"rapier": (-8.0, 6.0), "katana": (-6.0, 5.0), "zweihander": (-7.0, 6.0)}[w][li - 2]
        legs[leg] = {"rotation": [f"{tp} * ((v.rww_aw ?? 0.0) * {atk} + {num(stance)} * (1.0 - (v.rww_walk ?? 0.0)) * (1.0 - (v.rww_sprint ?? 0.0)) * (1.0 - (v.rww_swim ?? 0.0)) * (1.0 - (v.rww_sneak ?? 0.0)) * (q.is_riding ? 0.0 : 1.0))", 0, 0]}
    return {"loop": True, "bones": {"body": {"rotation": rot}, **legs}}


def attachable_animations(weapon: str) -> Dict[str, dict]:
    root = f"rww_{weapon}"
    return {
        f"animation.rww.{weapon}.hold_tp": {"loop": True, "bones": {root: HOLD_TP[weapon]}},
        f"animation.rww.{weapon}.hold_fp": {"loop": True, "bones": {root: HOLD_FP[weapon]}},
    }
