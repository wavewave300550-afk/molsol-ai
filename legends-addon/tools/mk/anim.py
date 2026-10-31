"""
Animation authoring helpers + a sampler that evaluates Bedrock animation JSON
at a given time (used by the preview renderer to show real poses).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Union

from . import molang

Num = Union[float, int, str]


def fmt(v: Num) -> Num:
    if isinstance(v, float):
        r = round(v, 4)
        return int(r) if r == int(r) else r
    return v


def kf(points: Dict[float, Sequence[Num]], smooth: bool = True) -> dict:
    """Keyframe channel. points: {time_seconds: [x, y, z]} (or scalar for scale)."""
    out = {}
    for t in sorted(points):
        val = points[t]
        v = [fmt(x) for x in val] if isinstance(val, (list, tuple)) else fmt(val)
        key = f"{t:.4f}".rstrip("0").rstrip(".") if t else "0.0"
        if "." not in key:
            key += ".0"
        out[key] = {"post": v, "lerp_mode": "catmullrom"} if smooth else v
    return out


def wave(amp: float, speed: float, phase: float = 0.0, base: float = 0.0, t: str = "q.life_time") -> str:
    """amp * sin(t * speed + phase) + base, as Molang (degrees)."""
    s = f"math.sin({t} * {fmt(speed)}{' + ' + str(fmt(phase)) if phase > 0 else (' - ' + str(fmt(-phase)) if phase < 0 else '')}) * {fmt(amp)}"
    if base:
        s = f"{s} + {fmt(base)}" if base > 0 else f"{s} - {fmt(-base)}"
    return s


class Anim:
    def __init__(self, loop: Union[bool, str] = True, length: Optional[float] = None):
        self.loop = loop
        self.length = length
        self.bones: Dict[str, dict] = {}
        self.particles: Dict[str, list] = {}
        self.sounds: Dict[str, list] = {}

    def _ch(self, bone, ch, value):
        self.bones.setdefault(bone, {})[ch] = value
        return self

    def rot(self, bone, value):
        return self._ch(bone, "rotation", [fmt(x) for x in value] if isinstance(value, (list, tuple)) else value)

    def pos(self, bone, value):
        return self._ch(bone, "position", [fmt(x) for x in value] if isinstance(value, (list, tuple)) else value)

    def scl(self, bone, value):
        return self._ch(bone, "scale", [fmt(x) for x in value] if isinstance(value, (list, tuple)) else fmt(value))

    def particle(self, t: float, effect: str, locator: Optional[str] = None):
        e = {"effect": effect}
        if locator:
            e["locator"] = locator
        self.particles.setdefault(f"{t:.2f}", []).append(e)
        return self

    def sound(self, t: float, effect: str):
        self.sounds.setdefault(f"{t:.2f}", []).append({"effect": effect})
        return self

    def json(self) -> dict:
        a: dict = {"loop": self.loop}
        if self.length:
            a["animation_length"] = fmt(self.length)
        a["bones"] = self.bones
        if self.particles:
            a["particle_effects"] = self.particles
        if self.sounds:
            a["sound_effects"] = self.sounds
        return a


# --------------------------------------------------------------------------- sampling

def _eval_vec(v, env, scalar=False):
    if isinstance(v, (list, tuple)):
        return tuple(float(molang.evaluate(x, env)) for x in v)
    x = float(molang.evaluate(v, env))
    return (x, x, x)


def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
                        + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3) for i in range(3))


def sample_channel(ch, t: float, env) -> tuple:
    if isinstance(ch, dict):
        keys = sorted(ch.items(), key=lambda kv: float(kv[0]))
        times = [float(k) for k, _ in keys]
        vals, modes = [], []
        for _, v in keys:
            if isinstance(v, dict):
                vals.append(_eval_vec(v.get("post", v.get("pre")), env))
                modes.append(v.get("lerp_mode", "linear"))
            else:
                vals.append(_eval_vec(v, env))
                modes.append("linear")
        if t <= times[0]:
            return vals[0]
        if t >= times[-1]:
            return vals[-1]
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                u = (t - times[i]) / max(1e-9, times[i + 1] - times[i])
                if modes[i] == "catmullrom" or modes[i + 1] == "catmullrom":
                    p0 = vals[max(0, i - 1)]
                    p3 = vals[min(len(vals) - 1, i + 2)]
                    return _catmull(p0, vals[i], vals[i + 1], p3, u)
                return tuple(vals[i][k] + (vals[i + 1][k] - vals[i][k]) * u for k in range(3))
    return _eval_vec(ch, env)


def sample(anim: dict, t: float, env, weight: float = 1.0, pose: Optional[dict] = None) -> dict:
    """Accumulate an animation's contribution into pose {bone: {'rotation','position','scale'}}."""
    pose = pose if pose is not None else {}
    length = anim.get("animation_length")
    loop = anim.get("loop", False)
    tt = t
    if length:
        if loop is True:
            tt = t % length
        else:
            tt = min(t, length)
    env.queries["anim_time"] = tt
    for bone, chans in anim.get("bones", {}).items():
        b = pose.setdefault(bone, {"rotation": [0.0, 0.0, 0.0], "position": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]})
        for ch, val in chans.items():
            v = sample_channel(val, tt, env)
            if ch == "scale":
                for i in range(3):
                    b["scale"][i] *= 1 + (v[i] - 1) * weight
            else:
                for i in range(3):
                    b[ch][i] += v[i] * weight
    return pose
