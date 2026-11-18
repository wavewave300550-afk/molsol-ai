"""
anim.py - Bedrock animations, animation controllers and client entities.

Animations are authored in Python either as Molang channels (looping,
procedural motion) or as eased keyframe tracks that are baked to linear keys.
Every animation can be sampled numerically (`Anim.sample`) so the preview
renderer shows the same pose the game computes.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .molang import E, ev, fmt, out

Value = Sequence  # [x, y, z] of numbers or molang.E
CHANNELS = {"rot": "rotation", "pos": "position", "scale": "scale"}
IDENTITY = {"rot": (0.0, 0.0, 0.0), "pos": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}


# --------------------------------------------------------------------------- easing

def ease(kind: str, t: float) -> float:
    t = max(0.0, min(1.0, t))
    if kind == "linear":
        return t
    if kind == "in":                       # slow start (wind-up)
        return t * t * t
    if kind == "out":                      # fast start, settle
        return 1 - (1 - t) ** 3
    if kind == "inout":
        return 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2
    if kind == "back":                     # overshoot then settle
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    if kind == "anticip":                  # pull back slightly before moving
        c1, c3 = 1.70158, 2.70158
        return c3 * t * t * t - c1 * t * t
    if kind == "snap":                     # violent: nearly a step, tiny lead-in
        return 1 - (1 - t) ** 5
    if kind == "bounce":
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        if t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        if t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        t -= 2.625 / d1
        return n1 * t * t + 0.984375
    if kind == "step":
        return 0.0 if t < 1 else 1.0
    raise ValueError(kind)


def tkey(t: float) -> str:
    s = f"{t:.4f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


# --------------------------------------------------------------------------- animation

class Anim:
    def __init__(self, name: str, length: Optional[float] = None, loop: Union[bool, str] = False,
                 time_update: Optional[E] = None, override: bool = False, blend_weight=None):
        self.name = name
        self.length = length
        self.loop = loop                                # False | True | "hold"
        self.time_update = time_update
        self.override = override
        self.blend_weight = blend_weight
        self.static: Dict[Tuple[str, str], list] = {}   # (bone, channel) -> [x,y,z]
        self.keys: Dict[Tuple[str, str], Dict[float, list]] = {}
        self.sounds: Dict[float, list] = {}
        self.particles: Dict[float, list] = {}
        self.timeline: Dict[float, list] = {}

    # ------------------------------------------------------------ authoring
    def set(self, bone: str, channel: str, value: Value) -> "Anim":
        """Constant / Molang channel."""
        assert channel in CHANNELS, channel
        self.static[(bone, channel)] = list(value)
        return self

    def rot(self, bone: str, x=0, y=0, z=0) -> "Anim":
        return self.set(bone, "rot", [x, y, z])

    def pos(self, bone: str, x=0, y=0, z=0) -> "Anim":
        return self.set(bone, "pos", [x, y, z])

    def scale(self, bone: str, x=1, y=None, z=None) -> "Anim":
        return self.set(bone, "scale", [x, x if y is None else y, x if z is None else z])

    def key(self, bone: str, channel: str, t: float, value: Value) -> "Anim":
        assert channel in CHANNELS, channel
        self.keys.setdefault((bone, channel), {})[round(float(t), 4)] = list(value)
        return self

    def track(self, bone: str, channel: str, keys: Sequence[Tuple], fps: float = 20.0) -> "Anim":
        """Eased keyframe track. keys: (t, [x,y,z]) or (t, [x,y,z], ease) - the ease
        shapes the segment ARRIVING at that key. Non-linear segments are baked to
        linear sub-keys at `fps` so the game needs no special interpolation mode."""
        keys = sorted(keys, key=lambda k: k[0])
        prev = None
        for k in keys:
            t, val = float(k[0]), [float(x) for x in k[1]]
            kind = k[2] if len(k) > 2 else "inout"
            if prev is not None and kind not in ("linear", "step") and t - prev[0] > 1.0 / fps + 1e-6:
                n = max(2, int(math.ceil((t - prev[0]) * fps)))
                for i in range(1, n):
                    f = i / n
                    e = ease(kind, f)
                    self.key(bone, channel, prev[0] + (t - prev[0]) * f,
                             [prev[1][j] + (val[j] - prev[1][j]) * e for j in range(3)])
            elif prev is not None and kind == "step":
                self.key(bone, channel, t - 0.001, prev[1])
            self.key(bone, channel, t, val)
            prev = (t, val)
        return self

    def poses(self, frames: Sequence[Tuple], fps: float = 20.0, bones: Optional[Iterable[str]] = None) -> "Anim":
        """Whole-body keyframes. frames: (t, pose, ease) where pose maps
        bone -> {'rot': [...], 'pos': [...], 'scale': [...]}. Bones/channels missing from a
        frame return to identity there."""
        used: Dict[Tuple[str, str], bool] = {}
        for fr in frames:
            for b, p in fr[1].items():
                if bones is not None and b not in bones:
                    continue
                for ch in p:
                    used[(b, ch)] = True
        for (b, ch) in used:
            ks = []
            for fr in frames:
                val = fr[1].get(b, {}).get(ch, IDENTITY[ch])
                ks.append((fr[0], val, fr[2] if len(fr) > 2 else "inout"))
            self.track(b, ch, ks, fps)
        return self

    def sound(self, t: float, effect: str) -> "Anim":
        self.sounds.setdefault(round(float(t), 4), []).append({"effect": effect})
        return self

    def particle(self, t: float, effect: str, locator: Optional[str] = None, pre: Optional[str] = None) -> "Anim":
        d = {"effect": effect}
        if locator:
            d["locator"] = locator
        if pre:
            d["pre_effect_script"] = pre
        self.particles.setdefault(round(float(t), 4), []).append(d)
        return self

    def event(self, t: float, molang: str) -> "Anim":
        self.timeline.setdefault(round(float(t), 4), []).append(molang)
        return self

    def bones(self) -> List[str]:
        return sorted({b for b, _ in list(self.static) + list(self.keys)})

    # ------------------------------------------------------------ export
    def json(self) -> dict:
        d: dict = {}
        if self.loop is True:
            d["loop"] = True
        elif self.loop == "hold":
            d["loop"] = "hold_on_last_frame"
        if self.length is not None:
            d["animation_length"] = round(self.length, 4)
        if self.time_update is not None:
            d["anim_time_update"] = str(self.time_update)
        if self.override:
            d["override_previous_animation"] = True
        if self.blend_weight is not None:
            d["blend_weight"] = out(self.blend_weight) if isinstance(self.blend_weight, E) else self.blend_weight
        bones: Dict[str, dict] = {}
        for (b, ch), val in self.static.items():
            bones.setdefault(b, {})[CHANNELS[ch]] = [out(x) for x in val]
        for (b, ch), ks in self.keys.items():
            if (b, ch) in self.static:
                raise ValueError(f"{self.name}: {b}.{ch} has both a static value and keyframes")
            bones.setdefault(b, {})[CHANNELS[ch]] = {tkey(t): [out(x) for x in ks[t]] for t in sorted(ks)}
        d["bones"] = {b: bones[b] for b in sorted(bones)}
        for field, src in (("sound_effects", self.sounds), ("particle_effects", self.particles)):
            if src:
                d[field] = {tkey(t): (v[0] if len(v) == 1 else v) for t, v in sorted(src.items())}
        if self.timeline:
            d["timeline"] = {tkey(t): (v[0] if len(v) == 1 else v) for t, v in sorted(self.timeline.items())}
        return d

    # ------------------------------------------------------------ evaluation
    def sample(self, t: float, env: Optional[dict] = None) -> Dict[str, dict]:
        """Pose contributed by this animation at time t (seconds)."""
        env = dict(env or {})
        if self.time_update is not None:
            t = self.time_update.ev(env)
        if self.length:
            if self.loop is True:
                t = math.fmod(t, self.length)
            else:
                t = min(t, self.length)
        env["q.anim_time"] = t
        pose: Dict[str, dict] = {}
        for (b, ch), val in self.static.items():
            pose.setdefault(b, {})[ch] = [ev(x, env) for x in val]
        for (b, ch), ks in self.keys.items():
            times = sorted(ks)
            if t <= times[0]:
                val = [ev(x, env) for x in ks[times[0]]]
            elif t >= times[-1]:
                val = [ev(x, env) for x in ks[times[-1]]]
            else:
                i = max(j for j in range(len(times)) if times[j] <= t)
                a, bq = times[i], times[i + 1]
                f = (t - a) / (bq - a)
                va, vb = [ev(x, env) for x in ks[a]], [ev(x, env) for x in ks[bq]]
                val = [va[j] + (vb[j] - va[j]) * f for j in range(3)]
            pose.setdefault(b, {})[ch] = val
        return pose


def combine(*poses: Dict[str, dict]) -> Dict[str, dict]:
    """Additive blend as the game does it: rotations and positions add, scales multiply."""
    out_: Dict[str, dict] = {}
    for p in poses:
        for b, chans in p.items():
            dst = out_.setdefault(b, {})
            for ch, v in chans.items():
                if ch not in dst:
                    dst[ch] = list(v)
                elif ch == "scale":
                    dst[ch] = [dst[ch][i] * v[i] for i in range(3)]
                else:
                    dst[ch] = [dst[ch][i] + v[i] for i in range(3)]
    return out_


def weighted(pose: Dict[str, dict], w: float) -> Dict[str, dict]:
    """Scale an additive pose by a blend weight (used for crossfade previews)."""
    out_: Dict[str, dict] = {}
    for b, chans in pose.items():
        for ch, v in chans.items():
            if ch == "scale":
                out_.setdefault(b, {})[ch] = [1 + (x - 1) * w for x in v]
            else:
                out_.setdefault(b, {})[ch] = [x * w for x in v]
    return out_


def animations_file(anims: Iterable[Anim]) -> dict:
    return {"format_version": "1.8.0", "animations": {a.name: a.json() for a in anims}}


# --------------------------------------------------------------------------- controllers

class Controller:
    def __init__(self, name: str, initial: str = "default"):
        self.name, self.initial = name, initial
        self.states: Dict[str, dict] = {}

    def state(self, name: str, animations: Sequence = (), transitions: Sequence[Tuple[str, object]] = (),
              blend: Optional[float] = None, on_entry: Sequence[str] = (), on_exit: Sequence[str] = (),
              shortest: bool = False, sounds: Sequence[str] = (), particles: Sequence = ()) -> "Controller":
        st: dict = {}
        if animations:
            st["animations"] = [a if isinstance(a, str) else {a[0]: str(a[1])} for a in animations]
        if transitions:
            st["transitions"] = [{target: str(expr)} for target, expr in transitions]
        if blend is not None:
            st["blend_transition"] = blend
        if shortest:
            st["blend_via_shortest_path"] = True
        if on_entry:
            st["on_entry"] = list(on_entry)
        if on_exit:
            st["on_exit"] = list(on_exit)
        if sounds:
            st["sound_effects"] = [{"effect": s} for s in sounds]
        if particles:
            st["particle_effects"] = [p if isinstance(p, dict) else {"effect": p} for p in particles]
        self.states[name] = st
        return self

    def json(self) -> dict:
        for name, st in self.states.items():
            for tr in st.get("transitions", []):
                for target in tr:
                    if target not in self.states:
                        raise ValueError(f"{self.name}: state {name} -> unknown state {target}")
        if self.initial not in self.states:
            raise ValueError(f"{self.name}: missing initial state {self.initial}")
        return {"initial_state": self.initial, "states": self.states}


def controllers_file(ctrls: Iterable[Controller]) -> dict:
    return {"format_version": "1.10.0", "animation_controllers": {c.name: c.json() for c in ctrls}}


# --------------------------------------------------------------------------- client entity

class ClientEntity:
    """Resource-pack entity definition."""

    def __init__(self, identifier: str, geometry: str, texture: str):
        self.identifier = identifier
        self.materials = {"default": "entity_alphatest"}
        self.textures = {"default": texture}
        self.geometry = {"default": geometry}
        self.render_controllers: List = []
        self.animations: Dict[str, str] = {}
        self.animate: List = []
        self.pre_animation: List[Tuple[str, E]] = []
        self.initialize: List[str] = []
        self.particle_effects: Dict[str, str] = {}
        self.sound_effects: Dict[str, str] = {}
        self.scale: Optional[str] = None
        self.spawn_egg: Optional[dict] = None

    def var(self, name: str, expr: E) -> E:
        """Declare a per-frame variable (scripts.pre_animation); returns a reference to it."""
        from .molang import v
        self.pre_animation.append((name, expr))
        return v(name)

    def env(self, base: dict) -> dict:
        """Evaluate pre_animation variables for the preview renderer."""
        e = dict(base)
        for name, expr in self.pre_animation:
            e[f"v.{name}"] = expr.ev(e)
        return e

    def json(self) -> dict:
        desc: dict = {"identifier": self.identifier, "materials": self.materials, "textures": self.textures,
                      "geometry": self.geometry}
        scripts: dict = {}
        if self.initialize:
            scripts["initialize"] = list(self.initialize)
        if self.pre_animation:
            scripts["pre_animation"] = [f"v.{n} = {e};" for n, e in self.pre_animation]
        if self.scale:
            scripts["scale"] = self.scale
        if self.animate:
            scripts["animate"] = [a if isinstance(a, str) else {a[0]: str(a[1])} for a in self.animate]
        if scripts:
            desc["scripts"] = scripts
        if self.animations:
            desc["animations"] = self.animations
        desc["render_controllers"] = self.render_controllers
        if self.particle_effects:
            desc["particle_effects"] = self.particle_effects
        if self.sound_effects:
            desc["sound_effects"] = self.sound_effects
        if self.spawn_egg:
            desc["spawn_egg"] = self.spawn_egg
        return {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}}
