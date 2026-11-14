"""Animation authoring for kit models (bb space; exported with Blockbench's conversion).

Channel values are either
  * a 3-tuple whose items are numbers or Expr (Molang + python twin for previews), or
  * a keyframe dict {time: (x, y, z)} (optionally smooth=True -> catmullrom).
Scale may also be a single number / Expr (uniform).
"""
from __future__ import annotations

import math

NS = "grimoire"


class Expr:
    """A Molang expression paired with a python evaluator f(t) for previews."""

    def __init__(self, molang, fn):
        self.molang = molang
        self.fn = fn

    def __neg__(self):
        return Expr(f"-({self.molang})", lambda t: -self.fn(t))

    def __add__(self, o):
        if isinstance(o, Expr):
            return Expr(f"({self.molang})+({o.molang})", lambda t: self.fn(t) + o.fn(t))
        return Expr(f"({self.molang})+({_n(o)})", lambda t: self.fn(t) + o)

    __radd__ = __add__

    def __mul__(self, o):
        if isinstance(o, Expr):
            return Expr(f"({self.molang})*({o.molang})", lambda t: self.fn(t) * o.fn(t))
        return Expr(f"({self.molang})*({_n(o)})", lambda t: self.fn(t) * o)

    __rmul__ = __mul__


def _n(v):
    return f"{float(v):.4f}".rstrip("0").rstrip(".") if isinstance(v, (int, float)) else str(v)


def S(amp, period, phase=0.0, base=0.0, clock="q.anim_time"):
    """base + amp * sin(2pi * (t / period + phase)).  Molang trig is in degrees."""
    k = 360.0 / period
    return Expr(f"{_n(base)}+{_n(amp)}*math.sin({clock}*{_n(k)}+{_n(phase * 360.0)})",
                lambda t: base + amp * math.sin(2 * math.pi * (t / period + phase)))


def C(amp, period, phase=0.0, base=0.0, clock="q.anim_time"):
    return S(amp, period, phase + 0.25, base, clock)


def LIFE(amp, period, phase=0.0, base=0.0):
    """Like S but on q.life_time so loops never pop when the animation restarts."""
    return S(amp, period, phase, base, clock="q.life_time")


def M(molang, fn=None):
    """Raw Molang with optional preview function."""
    return Expr(molang, fn or (lambda t: 0.0))


def _ev(v, t):
    return v.fn(t) if isinstance(v, Expr) else float(v)


def _is_keys(v):
    return isinstance(v, dict)


def _interp(keys, t, smooth):
    ts = sorted(keys)
    if t <= ts[0]:
        return tuple(_ev(c, t) for c in keys[ts[0]])
    if t >= ts[-1]:
        return tuple(_ev(c, t) for c in keys[ts[-1]])
    for a, b in zip(ts, ts[1:]):
        if a <= t <= b:
            f = (t - a) / (b - a) if b > a else 0.0
            if smooth:
                f = f * f * (3 - 2 * f)
            va, vb = keys[a], keys[b]
            return tuple(_ev(va[i], t) + (_ev(vb[i], t) - _ev(va[i], t)) * f for i in range(3))
    return (0.0, 0.0, 0.0)


class Anim:
    def __init__(self, name, length=None, loop=False, model=None):
        """loop: True | False | 'hold' (hold_on_last_frame)."""
        self.name = name
        self.length = length
        self.loop = loop
        self.model = model
        self.tracks = {}  # bone -> {'rot'|'pos'|'scl': (value, smooth)}
        self.sounds = {}
        self.particles = {}
        self.timeline = {}
        self.blend_weight = None
        self.override = False
        self.anim_time_update = None

    # -- authoring
    def _set(self, bone, ch, v, smooth):
        if isinstance(bone, (list, tuple)):
            for b in bone:
                self._set(b, ch, v, smooth)
            return self
        if ch == "scl" and not _is_keys(v) and not isinstance(v, (tuple, list)):
            v = (v, v, v)
        if _is_keys(v):
            v = {float(k): (tuple(x) if isinstance(x, (tuple, list)) else (x, x, x)) for k, x in v.items()}
        self.tracks.setdefault(bone, {})[ch] = (v, smooth)
        return self

    def rot(self, bone, v, smooth=True):
        return self._set(bone, "rot", v, smooth)

    def pos(self, bone, v, smooth=True):
        return self._set(bone, "pos", v, smooth)

    def scl(self, bone, v, smooth=True):
        return self._set(bone, "scl", v, smooth)

    def sound(self, t, effect):
        self.sounds.setdefault(float(t), []).append(effect)
        return self

    def particle(self, t, effect, locator=None, script=None):
        self.particles.setdefault(float(t), []).append((effect, locator, script))
        return self

    def event(self, t, molang):
        self.timeline.setdefault(float(t), []).append(molang)
        return self

    @property
    def full(self):
        return f"animation.{NS}.{self.model}.{self.name}"

    # -- preview
    def pose(self, t):
        if self.length and self.loop is True:
            t = t % self.length
        elif self.length:
            t = min(t, self.length)
        out = {}
        for bone, chs in self.tracks.items():
            vals = {}
            for ch, (v, smooth) in chs.items():
                vals[ch] = _interp(v, t, smooth) if _is_keys(v) else tuple(_ev(c, t) for c in v)
            out[bone] = (vals.get("rot", (0, 0, 0)), vals.get("pos", (0, 0, 0)), vals.get("scl", (1, 1, 1)))
        return out

    # -- export
    def to_json(self):
        j = {}
        if self.loop is True:
            j["loop"] = True
        elif self.loop == "hold":
            j["loop"] = "hold_on_last_frame"
        if self.length is not None:
            j["animation_length"] = round(float(self.length), 4)
        if self.override:
            j["override_previous_animation"] = True
        if self.blend_weight is not None:
            j["blend_weight"] = self.blend_weight
        if self.anim_time_update is not None:
            j["anim_time_update"] = self.anim_time_update
        bones = {}
        for bone, chs in self.tracks.items():
            jb = {}
            for ch, (v, smooth) in chs.items():
                name = {"rot": "rotation", "pos": "position", "scl": "scale"}[ch]
                if _is_keys(v):
                    jb[name] = {_t(t): _key(ch, v[t], smooth and len(v) > 2) for t in sorted(v)}
                else:
                    jb[name] = _vec(ch, v)
            bones[bone] = jb
        if bones:
            j["bones"] = bones
        if self.sounds:
            j["sound_effects"] = {_t(t): ([{"effect": e} for e in es] if len(es) > 1 else {"effect": es[0]})
                                  for t, es in sorted(self.sounds.items())}
        if self.particles:
            def pe(e):
                d = {"effect": e[0]}
                if e[1]:
                    d["locator"] = e[1]
                if e[2]:
                    d["pre_effect_script"] = e[2]
                return d
            j["particle_effects"] = {_t(t): ([pe(e) for e in es] if len(es) > 1 else pe(es[0]))
                                     for t, es in sorted(self.particles.items())}
        if self.timeline:
            j["timeline"] = {_t(t): ms for t, ms in sorted(self.timeline.items())}
        return j


def _t(t):
    return f"{t:.4f}".rstrip("0").rstrip(".") if "." in f"{t:.4f}" else f"{t:.1f}"


def _c(v, neg):
    if isinstance(v, Expr):
        return (-v).molang if neg else v.molang
    v = -float(v) if neg else float(v)
    return round(v, 3) + 0.0


def _vec(ch, v):
    if ch == "rot":
        return [_c(v[0], True), _c(v[1], True), _c(v[2], False)]
    if ch == "pos":
        return [_c(v[0], True), _c(v[1], False), _c(v[2], False)]
    return [_c(v[0], False), _c(v[1], False), _c(v[2], False)]


def _key(ch, v, smooth):
    vec = _vec(ch, v)
    return {"post": vec, "lerp_mode": "catmullrom"} if smooth else vec


def animations_file(anims):
    return {"format_version": "1.8.0", "animations": {a.full: a.to_json() for a in anims}}


def state_controller(model, states, prop="grimoire:state", blend=0.2, initial=0, name="main"):
    """Animation controller that mirrors an int entity property.

    states: {int: [anim short names]} or {int: {'animations': [...], 'blend': 0.3,
             'sounds': [...], 'particles': [(effect, locator)]}}
    """
    cid = f"controller.animation.{NS}.{model}.{name}"
    js = {}
    for k, spec in states.items():
        if isinstance(spec, (list, tuple)):
            spec = {"animations": list(spec)}
        st = {"animations": list(spec.get("animations", []))}
        st["transitions"] = [{f"s{o}": f"q.property('{prop}') == {o}"} for o in states if o != k]
        st["blend_transition"] = spec.get("blend", blend)
        if spec.get("sounds"):
            st["sound_effects"] = [{"effect": s} for s in spec["sounds"]]
        if spec.get("particles"):
            st["particle_effects"] = [({"effect": e, "locator": l} if l else {"effect": e})
                                      for e, l in spec["particles"]]
        if spec.get("on_entry"):
            st["on_entry"] = spec["on_entry"]
        js[f"s{k}"] = st
    return cid, {"initial_state": f"s{initial}", "states": js}
