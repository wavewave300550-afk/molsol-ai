"""Offline Bedrock animation runtime (preview/QA only).

Plays an attachable's `scripts.animate` list - plain animations with blend
conditions and animation controllers - the way the client does:

* rotation / position channels of every running animation are summed (scaled by
  the blend weight), scale channels multiply;
* keyframes interpolate linearly or with Catmull-Rom (`lerp_mode`), `pre`/`post`
  values are honoured, the first/last key holds outside the key range;
* `loop: true` wraps at `animation_length`, `hold_on_last_frame` holds, a
  non-looping animation stops contributing once finished;
* an animation (re)starts from time 0 whenever its blend weight becomes non-zero;
* controllers run `on_entry` / `on_exit` scripts, evaluate transitions in order,
  provide `q.all_animations_finished` / `q.any_animation_finished`, and restart
  their state's animations on entry;
* `anim_time_update` and `this` are supported.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import molang

CHANNELS = ("rotation", "position", "scale")


def _is_key_object(v) -> bool:
    return isinstance(v, dict) and any(k in v for k in ("pre", "post", "lerp_mode"))


class Channel:
    def __init__(self, raw):
        self.keys: Optional[List[Tuple[float, object, object, str]]] = None
        self.const = None
        if isinstance(raw, dict) and not _is_key_object(raw):
            keys = []
            for t, v in raw.items():
                if _is_key_object(v):
                    pre = v.get("pre", v.get("post"))
                    post = v.get("post", v.get("pre"))
                    keys.append((float(t), pre, post, v.get("lerp_mode", "linear")))
                else:
                    keys.append((float(t), v, v, "linear"))
            keys.sort(key=lambda k: k[0])
            self.keys = keys
        else:
            self.const = raw

    @property
    def max_time(self) -> float:
        return self.keys[-1][0] if self.keys else 0.0

    def value(self, t: float, env: molang.Env, this: np.ndarray) -> np.ndarray:
        if self.keys is None:
            return _vec(self.const, env, this)
        ks = self.keys
        if t <= ks[0][0]:
            return _vec(ks[0][1], env, this)
        if t >= ks[-1][0]:
            return _vec(ks[-1][2], env, this)
        i = 0
        while i + 1 < len(ks) and ks[i + 1][0] <= t:
            i += 1
        t0, t1 = ks[i][0], ks[i + 1][0]
        a = (t - t0) / max(t1 - t0, 1e-9)
        p1 = _vec(ks[i][2], env, this)
        p2 = _vec(ks[i + 1][1], env, this)
        if ks[i][3] == "catmullrom" or ks[i + 1][3] == "catmullrom":
            p0 = _vec(ks[i - 1][2], env, this) if i > 0 else p1
            p3 = _vec(ks[i + 2][1], env, this) if i + 2 < len(ks) else p2
            a2, a3 = a * a, a * a * a
            return 0.5 * ((2 * p1) + (-p0 + p2) * a + (2 * p0 - 5 * p1 + 4 * p2 - p3) * a2 + (-p0 + 3 * p1 - 3 * p2 + p3) * a3)
        return p1 + (p2 - p1) * a


def _vec(raw, env: molang.Env, this: np.ndarray) -> np.ndarray:
    if isinstance(raw, (list, tuple)):
        out = np.zeros(3)
        for i, c in enumerate(raw[:3]):
            env.this = float(this[i])
            out[i] = molang.evaluate(c, env)
        return out
    env.this = float(this[0])
    x = molang.evaluate(raw, env)
    return np.array([x, x, x], float)


class Animation:
    def __init__(self, name: str, data: dict):
        self.name = name
        self.loop = data.get("loop", False)
        self.time_update = data.get("anim_time_update")
        self.bones: Dict[str, Dict[str, Channel]] = {}
        mx = 0.0
        for bn, chans in (data.get("bones") or {}).items():
            cc = {}
            for ch in CHANNELS:
                if ch in chans:
                    cc[ch] = Channel(chans[ch])
                    mx = max(mx, cc[ch].max_time)
            self.bones[bn.lower()] = cc
        self.length = float(data.get("animation_length", mx))
        self.particles = data.get("particle_effects") or {}

    def local_time(self, t: float) -> float:
        if self.loop is True and self.length > 0:
            return math.fmod(t, self.length)
        if self.loop == "hold_on_last_frame":
            return min(t, self.length)
        return t

    def finished(self, t: float) -> bool:
        return self.loop is not True and t >= self.length

    def played_once(self, t: float) -> bool:
        return t >= self.length

    def apply(self, t: float, weight: float, env: molang.Env, pose: "Pose") -> None:
        if weight == 0 or (self.loop is False and t > self.length and self.length > 0):
            return
        lt = self.local_time(t)
        env.q["anim_time"] = lt
        for bn, chans in self.bones.items():
            for ch, chan in chans.items():
                cur = pose.get(bn, ch)
                v = chan.value(lt, env, cur)
                pose.add(bn, ch, v, weight)


class Pose:
    """Accumulated bone channels (lower-case bone names)."""

    def __init__(self):
        self.ch: Dict[str, Dict[str, np.ndarray]] = {}

    def get(self, bone: str, ch: str) -> np.ndarray:
        d = self.ch.get(bone, {})
        if ch in d:
            return d[ch]
        return np.ones(3) if ch == "scale" else np.zeros(3)

    def add(self, bone: str, ch: str, v: np.ndarray, w: float = 1.0) -> None:
        d = self.ch.setdefault(bone, {})
        if ch == "scale":
            d[ch] = d.get(ch, np.ones(3)) * (1 + (np.asarray(v, float) - 1) * w)
        else:
            d[ch] = d.get(ch, np.zeros(3)) + np.asarray(v, float) * w

    def for_render(self, names: Dict[str, str]) -> Dict[str, dict]:
        out = {}
        for bn, d in self.ch.items():
            real = names.get(bn)
            if real is None:
                continue
            e = {}
            if "rotation" in d:
                e["rot"] = tuple(d["rotation"])
            if "position" in d:
                e["pos"] = tuple(d["position"])
            if "scale" in d:
                e["scale"] = tuple(d["scale"])
            out[real] = e
        return out


class _Track:
    """A running animation reference with its own clock."""

    def __init__(self, anim: Animation, now: float):
        self.anim = anim
        self.start = now
        self.t = 0.0
        self.last = now

    def advance(self, now: float, env: molang.Env) -> float:
        dt = now - self.last
        self.last = now
        if self.anim.time_update:
            env.q["anim_time"] = self.t
            env.q["delta_time"] = dt
            self.t = molang.evaluate(self.anim.time_update, env)
        else:
            self.t += dt
        return self.t


class Controller:
    def __init__(self, name: str, data: dict, rt: "Runtime"):
        self.name = name
        self.states = data["states"]
        self.state = data.get("initial_state", "default")
        self.rt = rt
        self.tracks: Dict[str, _Track] = {}
        self.entered = False
        self.history: List[Tuple[float, str]] = []

    def _enter(self, state: str, now: float, env: molang.Env) -> None:
        self.state = state
        self.tracks = {}
        self.history.append((now, state))
        for s in self.states[state].get("on_entry", []) or []:
            molang.evaluate(s, env)

    def _exit(self, env: molang.Env) -> None:
        for s in self.states[self.state].get("on_exit", []) or []:
            molang.evaluate(s, env)

    def _anims(self) -> List[Tuple[str, object]]:
        out = []
        for e in self.states[self.state].get("animations", []) or []:
            if isinstance(e, str):
                out.append((e, None))
            else:
                (k, v), = e.items()
                out.append((k, v))
        return out

    def step(self, now: float, env: molang.Env, pose: Pose, weight: float) -> None:
        if not self.entered:
            self.entered = True
            self._enter(self.state, now, env)
        names = [n for n, _ in self._anims()]
        fin = [self.tracks[n].anim.played_once(self.tracks[n].t) for n in names if n in self.tracks]
        env.q["all_animations_finished"] = 1.0 if (not names or (len(fin) == len(names) and all(fin))) else 0.0
        env.q["any_animation_finished"] = 1.0 if any(fin) else 0.0
        for tr in self.states[self.state].get("transitions", []) or []:
            (target, cond), = tr.items()
            if molang.evaluate(cond, env):
                self._exit(env)
                self._enter(target, now, env)
                break
        for name, wexpr in self._anims():
            w = 1.0 if wexpr is None else molang.evaluate(wexpr, env)
            target = self.rt.resolve(name)
            if isinstance(target, Controller):
                target.step(now, env, pose, w * weight)
                continue
            if w == 0:
                self.tracks.pop(name, None)
                continue
            tr_ = self.tracks.get(name)
            if tr_ is None:
                tr_ = self.tracks[name] = _Track(target, now)
            t = tr_.advance(now, env)
            target.apply(t, w * weight, env, pose)


class Runtime:
    """Runs one attachable (or client entity) description."""

    def __init__(self, desc: dict, animations: Dict[str, Animation], controllers: Dict[str, dict]):
        self.short = desc.get("animations", {})
        self.animations = animations
        self.controller_defs = controllers
        self.controllers: Dict[str, Controller] = {}
        scripts = desc.get("scripts", {})
        self.pre = scripts.get("pre_animation", []) or []
        self.init = scripts.get("initialize", []) or []
        self.entries: List[Tuple[str, object]] = []
        for e in scripts.get("animate", []) or []:
            if isinstance(e, str):
                self.entries.append((e, None))
            else:
                (k, v), = e.items()
                self.entries.append((k, v))
        self.tracks: Dict[str, _Track] = {}
        self.initialized = False

    def resolve(self, short: str):
        full = self.short.get(short)
        if full is None:
            raise KeyError(f"animation '{short}' is not declared")
        if full.startswith("controller."):
            if short not in self.controllers:
                self.controllers[short] = Controller(full, self.controller_defs[full], self)
            return self.controllers[short]
        return self.animations[full]

    def step(self, now: float, env: molang.Env) -> Pose:
        if not self.initialized:
            self.initialized = True
            for s in self.init:
                molang.evaluate(s, env)
        for s in self.pre:
            molang.evaluate(s, env)
        pose = Pose()
        for name, cond in self.entries:
            w = 1.0 if cond is None else molang.evaluate(cond, env)
            target = self.resolve(name)
            if isinstance(target, Controller):
                if w:
                    target.step(now, env, pose, w)
                continue
            if not w:
                self.tracks.pop(name, None)
                continue
            tr = self.tracks.get(name)
            if tr is None:
                tr = self.tracks[name] = _Track(target, now)
            t = tr.advance(now, env)
            target.apply(t, w, env, pose)
        return pose


def load_animations(files) -> Dict[str, Animation]:
    from . import ljson
    out = {}
    for f in files:
        for name, data in ljson.load(f).get("animations", {}).items():
            out[name] = Animation(name, data)
    return out


def load_controllers(files) -> Dict[str, dict]:
    from . import ljson
    out = {}
    for f in files:
        out.update(ljson.load(f).get("animation_controllers", {}))
    return out
