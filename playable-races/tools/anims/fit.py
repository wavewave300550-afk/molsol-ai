"""Gait ground-fitting.

The player's walk cycle swings the legs as rigid pendulums; with the races'
own knees, digitigrade feet and reduced strides the feet would sink into or
float above the ground at some phases.  This samples a locomotion layer with
the real Molang runtime (kit/animrt) on top of the vanilla skeleton (kit/playersim),
measures the lowest point of the legs at each stride phase, and fits a short
Fourier series of the body bob that keeps the lowest foot on the ground
(plus an optional deliberate flight arc).  The result is a Molang expression of
the stride phase, so it stays stateless and exact in game.
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence

import numpy as np

from anims.core import Anim, n
from anims.life import PH
from kit import animrt
from kit.playersim import Sim, vanilla_skeleton
from kit.render import collect_quads

UPPER_GROUPS = ("torso_g", "head_g", "r_arm_g", "l_arm_g", "tail_g", "r_arm_fp", "l_arm_fp",
                "r_foot_rune", "l_foot_rune")   # golem sole runes only show while airborne


def foot_floor(model, anims: Sequence[Anim], speed: float, sprint: bool, samples: int = 48,
               variant: str = "base") -> np.ndarray:
    """Lowest y of the leg geometry over one stride cycle (phase 0..360, `samples` steps)."""
    rt = [animrt.Animation(a.name, a.json()) for a in anims]
    names = {bn.lower(): bn for bn in model.order}
    hide = [b for b in UPPER_GROUPS if b in model.bones]
    out = np.zeros(samples)
    for k in range(samples):
        ph = 360.0 * k / samples
        sim = Sim()
        sim.mspeed = speed
        sim.sprint = sprint
        sim.dist = ph / 38.17 + 9.4315 * 30          # whole strides + phase
        env = sim.env()
        env.v = {"attack_time": 0.0}
        pose = animrt.Pose()
        for a in rt:
            a.apply(0.0, 1.0, env, pose)
        base = vanilla_skeleton(sim)
        for bn, d in pose.ch.items():
            for ch, v in d.items():
                base.add(bn, ch, v)
        quads = collect_quads(model, variant, base.for_render(names), hide=hide)
        out[k] = min(float(q[0][:, 1].min()) for q in quads)
    return out


def fourier(values: np.ndarray, harmonics: int) -> List[float]:
    """Least-squares coefficients [a0, a1, b1, a2, b2, ...] of a periodic sample set."""
    N = len(values)
    th = np.linspace(0, 2 * math.pi, N, endpoint=False)
    cols = [np.ones(N)]
    for h in range(1, harmonics + 1):
        cols += [np.cos(h * th), np.sin(h * th)]
    A = np.stack(cols, axis=1)
    coef, *_ = np.linalg.lstsq(A, values, rcond=None)
    return [float(c) for c in coef]


def series(coef: Sequence[float], phase: str = PH, tol: float = 0.02) -> str:
    """Molang for a0 + sum(a_h cos(h*phase) + b_h sin(h*phase)) (phase in degrees)."""
    terms = [n(coef[0])] if abs(coef[0]) > tol else []
    for h in range(1, (len(coef) - 1) // 2 + 1):
        a, b = coef[2 * h - 1], coef[2 * h]
        arg = phase if h == 1 else f"{phase} * {h}"
        if abs(a) > tol:
            terms.append(f"{n(a)} * math.cos({arg})")
        if abs(b) > tol:
            terms.append(f"{n(b)} * math.sin({arg})")
    return " + ".join(terms) if terms else "0"


def ground_bob(model, anims: Sequence[Anim], speed: float, sprint: bool, harmonics: int = 4,
               clearance: Optional[Callable[[np.ndarray], np.ndarray]] = None, samples: int = 48,
               report: Optional[list] = None, label: str = "") -> str:
    """Bob (model units, + up) that puts the lowest foot on the ground at every stride phase."""
    floor = foot_floor(model, anims, speed, sprint, samples)
    target = -floor
    if clearance is not None:
        target = target + clearance(np.linspace(0, 360, samples, endpoint=False))
    coef = fourier(target, harmonics)
    if report is not None:
        th = np.linspace(0, 2 * math.pi, samples, endpoint=False)
        fit = coef[0] + sum(coef[2 * h - 1] * np.cos(h * th) + coef[2 * h] * np.sin(h * th) for h in range(1, harmonics + 1))
        err = np.abs(fit - target).max()
        report.append(f"{label}: foot floor {floor.min():+.2f}..{floor.max():+.2f} -> bob fit max error {err:.2f} units")
    return series(coef)
