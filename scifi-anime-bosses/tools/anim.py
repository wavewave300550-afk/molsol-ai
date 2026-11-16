"""
anim.py - Bedrock animation / animation-controller authoring + evaluation.

An Anim holds per-bone channels; each channel is either keyframes {time: (x,y,z)} with
linear or catmullrom interpolation, or a molang expression triple.  Anims export to the
Bedrock "animations" JSON format and can be *evaluated* in Python (via molang.py) so the
preview renderer animates exactly the data the game will run.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

import molang

Vec3 = Tuple[float, float, float]
KeyVal = Union[Vec3, Tuple[str, str, str]]


def _fmt(v):
    if isinstance(v, str):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return round(v, 4) if isinstance(v, float) else v


class Channel:
    def __init__(self, keys: Optional[Dict[float, KeyVal]] = None, expr: Optional[Sequence] = None,
                 lerp: str = "linear"):
        self.keys = dict(sorted((keys or {}).items()))
        self.expr = list(expr) if expr is not None else None
        self.lerp = lerp

    def to_json(self):
        if self.expr is not None:
            return [_fmt(e) for e in self.expr]
        out = {}
        for t, v in self.keys.items():
            val = [_fmt(c) for c in v]
            k = f"{t:.4f}".rstrip("0").rstrip(".") if t else "0.0"
            if "." not in k:
                k += ".0"
            out[k] = {"post": val, "lerp_mode": "catmullrom"} if self.lerp == "catmullrom" else val
        return out

    def evaluate(self, t: float, ctx: molang.Context) -> Vec3:
        if self.expr is not None:
            return tuple(molang.evaluate(e, ctx) if isinstance(e, str) else float(e) for e in self.expr)
        times = list(self.keys)
        vals = [tuple(molang.evaluate(c, ctx) if isinstance(c, str) else float(c) for c in self.keys[k]) for k in times]
        if t <= times[0]:
            return vals[0]
        if t >= times[-1]:
            return vals[-1]
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                span = times[i + 1] - times[i]
                u = (t - times[i]) / span if span > 0 else 0.0
                if self.lerp == "catmullrom":
                    p0 = vals[max(0, i - 1)]
                    p1, p2 = vals[i], vals[i + 1]
                    p3 = vals[min(len(vals) - 1, i + 2)]
                    return tuple(_catmull(p0[k], p1[k], p2[k], p3[k], u) for k in range(3))
                return tuple(vals[i][k] + (vals[i + 1][k] - vals[i][k]) * u for k in range(3))
        return vals[-1]


def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


class Anim:
    def __init__(self, name: str, length: Optional[float] = None, loop: Union[bool, str] = False,
                 anim_time_update: Optional[str] = None, blend_weight: Optional[str] = None,
                 override: bool = False):
        self.name = name
        self.length = length
        self.loop = loop
        self.anim_time_update = anim_time_update
        self.blend_weight = blend_weight
        self.override = override
        self.bones: Dict[str, Dict[str, Channel]] = {}
        self.particles: Dict[float, List[dict]] = {}
        self.sounds: Dict[float, List[dict]] = {}
        self.timeline: Dict[float, List[str]] = {}

    # ---------------------------------------------------------------- authoring
    def _ch(self, bone, kind, ch: Channel):
        self.bones.setdefault(bone, {})[kind] = ch
        return self

    def rot(self, bone, keys, lerp="catmullrom"):
        return self._ch(bone, "rotation", Channel(keys=keys, lerp=lerp))

    def pos(self, bone, keys, lerp="catmullrom"):
        return self._ch(bone, "position", Channel(keys=keys, lerp=lerp))

    def scl(self, bone, keys, lerp="catmullrom"):
        keys = {t: (v, v, v) if isinstance(v, (int, float, str)) else v for t, v in keys.items()}
        return self._ch(bone, "scale", Channel(keys=keys, lerp=lerp))

    def rot_e(self, bone, x="0", y="0", z="0"):
        return self._ch(bone, "rotation", Channel(expr=(x, y, z)))

    def pos_e(self, bone, x="0", y="0", z="0"):
        return self._ch(bone, "position", Channel(expr=(x, y, z)))

    def scl_e(self, bone, x="1", y=None, z=None):
        return self._ch(bone, "scale", Channel(expr=(x, y if y is not None else x, z if z is not None else x)))

    def fx(self, t, effect, locator=None, script=None):
        e = {"effect": effect}
        if locator:
            e["locator"] = locator
        if script:
            e["pre_effect_script"] = script
        self.particles.setdefault(round(t, 4), []).append(e)
        return self

    def sfx(self, t, effect):
        self.sounds.setdefault(round(t, 4), []).append({"effect": effect})
        return self

    # ---------------------------------------------------------------- export
    def to_json(self) -> dict:
        out: dict = {}
        if self.loop:
            out["loop"] = self.loop
        if self.length is not None:
            out["animation_length"] = self.length
        if self.anim_time_update:
            out["anim_time_update"] = self.anim_time_update
        if self.blend_weight:
            out["blend_weight"] = self.blend_weight
        if self.override:
            out["override_previous_animation"] = True
        bones = {}
        for b, chans in self.bones.items():
            bones[b] = {k: ch.to_json() for k, ch in chans.items()}
        if bones:
            out["bones"] = bones

        def tl(d):
            res = {}
            for t, lst in sorted(d.items()):
                k = f"{t:.4f}".rstrip("0").rstrip(".") if t else "0.0"
                if "." not in k:
                    k += ".0"
                res[k] = lst[0] if len(lst) == 1 else lst
            return res
        if self.particles:
            out["particle_effects"] = tl(self.particles)
        if self.sounds:
            out["sound_effects"] = tl(self.sounds)
        return out

    # ---------------------------------------------------------------- evaluation
    def evaluate(self, t: float, ctx: molang.Context) -> Dict[str, dict]:
        """Pose contribution at anim time t (loop / hold handled here)."""
        if self.length:
            if self.loop is True:
                t = t % self.length
            else:
                t = min(t, self.length)
        ctx.queries["query.anim_time"] = t
        pose = {}
        for b, chans in self.bones.items():
            pb = {}
            for kind, ch in chans.items():
                pb[kind] = ch.evaluate(t, ctx)
            pose[b] = pb
        return pose

    def molang_strings(self):
        """All molang expressions (for validation)."""
        out = []
        for chans in self.bones.values():
            for ch in chans.values():
                vals = ch.expr if ch.expr is not None else [c for v in ch.keys.values() for c in v]
                out.extend(v for v in vals if isinstance(v, str))
        for x in (self.anim_time_update, self.blend_weight):
            if x:
                out.append(x)
        return out


def merge_poses(*poses: Dict[str, dict], weights: Optional[Sequence[float]] = None) -> Dict[str, dict]:
    """Bedrock-style additive combination of animation outputs."""
    out: Dict[str, dict] = {}
    weights = weights or [1.0] * len(poses)
    for pose, w in zip(poses, weights):
        for b, chans in pose.items():
            ob = out.setdefault(b, {})
            for kind, v in chans.items():
                if kind == "scale":
                    cur = ob.get("scale", (1.0, 1.0, 1.0))
                    ob["scale"] = tuple(cur[i] * (1 + (v[i] - 1) * w) for i in range(3))
                else:
                    cur = ob.get(kind, (0.0, 0.0, 0.0))
                    ob[kind] = tuple(cur[i] + v[i] * w for i in range(3))
    return out


class Controller:
    """Animation controller with states; transitions are molang conditions."""

    def __init__(self, name: str, initial: str = "default"):
        self.name = name
        self.initial = initial
        self.states: Dict[str, dict] = {}

    def state(self, name, animations: Sequence = (), transitions: Optional[List[Tuple[str, str]]] = None,
              blend: Optional[float] = None, on_entry: Optional[List[str]] = None, particles=None, sounds=None,
              shortest=False):
        st: dict = {}
        if animations:
            st["animations"] = list(animations)
        if transitions:
            st["transitions"] = [{to: cond} for to, cond in transitions]
        if blend is not None:
            st["blend_transition"] = blend
            if shortest:
                st["blend_via_shortest_path"] = True
        if on_entry:
            st["on_entry"] = on_entry
        if particles:
            st["particle_effects"] = particles
        if sounds:
            st["sound_effects"] = sounds
        self.states[name] = st
        return self

    def to_json(self) -> dict:
        return {"initial_state": self.initial, "states": self.states}

    def molang_strings(self):
        out = []
        for st in self.states.values():
            for tr in st.get("transitions", []):
                out.extend(tr.values())
            for a in st.get("animations", []):
                if isinstance(a, dict):
                    out.extend(a.values())
            out.extend(st.get("on_entry", []))
        return out
