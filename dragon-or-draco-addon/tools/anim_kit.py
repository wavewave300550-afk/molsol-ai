"""
anim_kit - animation authoring toolkit for the Red Dragon (V2).

Bedrock keyframes only interpolate linearly or with catmull-rom, so everything here is authored
as continuous functions of time (eased key poses, procedural cycles, spring simulations, IK) and
then *baked*: sampled densely, reduced to the fewest catmull-rom keys that reproduce the curve
within a tolerance (checked against Bedrock's own catmull-rom formula), and written as keyframes.

Pieces:
  Rig            forward kinematics on the real geometry (shared math with kinematics.py)
  ease / Keys    eased key poses (in, out, in-out, overshoot, settle)
  Clip           an animation: channels = functions of t; bake() -> Bedrock JSON
  spring_chain   follow-through / overlapping action for tails, necks, wing tips
  lm_solve       damped least squares, used for leg IK (planted feet) and head stabilisation
"""
from __future__ import annotations

import json
import math
import os
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

import kinematics as K

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")

Vec = np.ndarray
LEFT_TAGS = (("_l_", "_r_"), ("_fl", "_fr"), ("_hl", "_hr"), ("eyelid_l", "eyelid_r"))


def v(*a) -> Vec:
    return np.array(a, dtype=float)


ZERO = v(0, 0, 0)
ONE = v(1, 1, 1)


def right_of(name: str) -> Optional[str]:
    for a, b in LEFT_TAGS:
        if a in name:
            return name.replace(a, b)
    return None


def mirror_vec(val: Vec, kind: str) -> Vec:
    if kind == "rotation":
        return v(val[0], -val[1], -val[2])
    if kind == "position":
        return v(-val[0], val[1], val[2])
    return val


# ----------------------------------------------------------------------------- easing

def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def smoother(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


EASE: Dict[str, Callable[[float], float]] = {
    "linear": lambda u: u,
    "in": lambda u: u * u * u,
    "out": lambda u: 1 - (1 - u) ** 3,
    "inout": smoother,
    "smooth": smooth,
    # overshoot then settle (follow-through)
    "back": lambda u: 1 + 2.2 * (u - 1) ** 3 + 1.2 * (u - 1) ** 2,
    # fast attack, damped wobble into place
    "settle": lambda u: 1 - math.exp(-6 * u) * math.cos(9 * u) if u < 1 else 1.0,
    "snap": lambda u: 1 - (1 - u) ** 5,
}


class Keys:
    """Eased key poses: [(t, value, ease_into_this_key), ...] -> value(t)."""

    def __init__(self, keys: Sequence[Tuple]):
        ks = []
        for k in keys:
            t, val = k[0], k[1]
            e = k[2] if len(k) > 2 else "inout"
            ks.append((float(t), np.asarray(val, dtype=float), e))
        ks.sort(key=lambda x: x[0])
        self.k = ks

    def __call__(self, t: float) -> Vec:
        k = self.k
        if t <= k[0][0]:
            return k[0][1]
        for (t0, a, _), (t1, b, e) in zip(k, k[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                return a + (b - a) * EASE[e](u)
        return k[-1][1]


def wave(t, period, amp, phase=0.0, offset=0.0):
    return offset + amp * math.sin(2 * math.pi * (t / period) + phase)


# ----------------------------------------------------------------------------- rig / FK

class Rig:
    def __init__(self, geo_path=None):
        geo_path = geo_path or os.path.join(RP, "models", "entity", "red_dragon.geo.json")
        self.geo = K.load_json(geo_path)["minecraft:geometry"][0]
        self.bones = {b["name"]: b for b in self.geo["bones"]}
        self.order = [b["name"] for b in self.geo["bones"]]
        self.parent = {b["name"]: b.get("parent") for b in self.geo["bones"]}
        self.pivot = {b["name"]: np.array(b.get("pivot", [0, 0, 0]), float) for b in self.geo["bones"]}
        self.rest = {b["name"]: np.array(b.get("rotation", [0, 0, 0]), float) for b in self.geo["bones"]}
        self.locators = {}
        for b in self.geo["bones"]:
            for ln, lv in (b.get("locators") or {}).items():
                self.locators[ln] = (b["name"], np.array(lv, float))

    def local(self, name, pose):
        piv = self.pivot[name]
        p = pose.get(name)
        rot = self.rest[name] + (p["rotation"] if p else 0)
        pos = p["position"] if p else ZERO
        scl = p["scale"] if p else ONE
        return K.affine(t=piv + pos) @ K.affine(K.brot(rot)) @ K.affine(np.diag(scl)) @ K.affine(t=-piv)

    def world(self, pose, upto: Optional[Sequence[str]] = None):
        mats = {}
        names = self.order
        if upto is not None:
            need = set()
            for n in upto:
                while n and n not in need:
                    need.add(n)
                    n = self.parent[n]
            names = [n for n in self.order if n in need]
        for n in names:
            par = self.parent[n]
            L = self.local(n, pose)
            mats[n] = mats[par] @ L if par else L
        return mats

    def point(self, mats, bone, local_point):
        return (mats[bone] @ np.append(local_point, 1.0))[:3]

    def pitch_of(self, mats, bone):
        """World pitch of a bone's forward (-Z) axis in degrees (+ = front down)."""
        f = mats[bone][:3, :3] @ v(0, 0, -1)
        f /= np.linalg.norm(f)
        return math.degrees(math.asin(-max(-1, min(1, f[1]))))

    def yaw_of(self, mats, bone):
        f = mats[bone][:3, :3] @ v(0, 0, -1)
        return math.degrees(math.atan2(f[0], -f[2]))


def pose_entry(pose, bone):
    if bone not in pose:
        pose[bone] = {"rotation": ZERO.copy(), "position": ZERO.copy(), "scale": ONE.copy()}
    return pose[bone]


# ----------------------------------------------------------------------------- solver

def lm_solve(x0, residual, iters=10, lam=1e-3, eps=1e-3, tol=1e-6):
    x = np.array(x0, dtype=float)
    r = residual(x)
    cost = r @ r
    for _ in range(iters):
        J = np.empty((r.size, x.size))
        for i in range(x.size):
            dx = np.zeros_like(x)
            dx[i] = eps
            J[:, i] = (residual(x + dx) - r) / eps
        A = J.T @ J + lam * np.eye(x.size)
        step = -np.linalg.solve(A, J.T @ r)
        xn = x + step
        rn = residual(xn)
        cn = rn @ rn
        if cn < cost:
            x, r, cost = xn, rn, cn
            lam *= 0.5
            if np.abs(step).max() < tol:
                break
        else:
            lam *= 4
    return x, cost


# ----------------------------------------------------------------------------- springs

def spring_chain(drive_angle: np.ndarray, drive_lin: np.ndarray, dt: float, n: int, k=60.0, c=9.0, g=0.85,
                 h=0.0, gain=1.0, cycles=1, falloff=1.12) -> np.ndarray:
    """Follow-through for an n-segment chain on one axis.

    drive_angle[t]: world angle (deg) of the chain's root/parent over time.
    drive_lin[t]: linear acceleration of the root perpendicular to the chain (units/s^2).
    Each segment's relative angle a_i resists its parent's angular acceleration (inertia g),
    is pulled back to 0 by a spring (k) with damping (c) and reacts to the root's linear
    acceleration (h).  Deeper segments are lighter/looser (falloff) so the tip lags most.
    Returns rel[t, i] (deg).  For loops, pass the cycle and cycles>1: the last cycle is returned.
    """
    T = len(drive_angle)
    W = np.tile(drive_angle, cycles)
    A = np.tile(drive_lin, cycles)
    # angular acceleration of the drive (periodic-safe central difference)
    Wd = np.gradient(np.unwrap(np.radians(W))) / dt
    Wdd = np.degrees(np.gradient(Wd) / dt)
    a = np.zeros(n)
    av = np.zeros(n)
    out = np.zeros((T * cycles, n))
    for t in range(T * cycles):
        parent_acc = Wdd[t]
        for i in range(n):
            ki = k / (falloff ** i)
            ci = c / (falloff ** (i * 0.5))
            acc = -ki * a[i] - ci * av[i] - g * parent_acc - h * A[t] * (1 + 0.15 * i)
            av[i] += acc * dt
            a[i] += av[i] * dt
            parent_acc = parent_acc + acc  # this segment's world acceleration drives the next
        out[t] = a * gain
    return out[-T:]


# ----------------------------------------------------------------------------- clips

def catmull_curve(kt, kv, ts):
    """Bedrock catmull-rom through keys (kt, kv) evaluated at every ts (endpoints duplicated)."""
    n = len(kt)
    i = np.clip(np.searchsorted(kt, ts, side="right") - 1, 0, n - 2)
    t0, t1 = kt[i], kt[i + 1]
    u = ((ts - t0) / np.where(t1 > t0, t1 - t0, 1.0))[:, None]
    p1, p2 = kv[i], kv[i + 1]
    p0 = np.where((i > 0)[:, None], kv[np.maximum(i - 1, 0)], p1)
    p3 = np.where((i + 2 < n)[:, None], kv[np.minimum(i + 2, n - 1)], p2)
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def reduce_keys(times, vals, tol):
    """Fewest keys whose Bedrock catmull-rom curve stays within tol of the dense samples."""
    n = len(times)
    step = max(1, int(round(0.2 / max(1e-6, times[1] - times[0]))))
    keep = set(range(0, n, step)) | {0, n - 1}
    for _ in range(n):
        ks = np.array(sorted(keep))
        err = np.abs(catmull_curve(times[ks], vals[ks], times) - vals).max(axis=1)
        j = int(np.argmax(err))
        if err[j] <= tol:
            break
        keep.add(j)
    ks = sorted(keep)
    idx = 1
    while idx < len(ks) - 1:  # one removal sweep
        trial = ks[:idx] + ks[idx + 1:]
        err = np.abs(catmull_curve(times[trial], vals[trial], times) - vals).max()
        if err <= tol:
            ks = trial
        else:
            idx += 1
    return ks


def fmt(x):
    x = round(float(x), 2)
    return int(x) if x == int(x) else x


class Clip:
    def __init__(self, name: str, length: float, loop=False, anim_time_update: Optional[str] = None,
                 rate: int = 30, additive: bool = False, note: str = ""):
        self.name = name
        self.length = length
        self.loop = loop
        self.atu = anim_time_update
        self.rate = rate
        self.additive = additive
        self.note = note
        self.ch: Dict[Tuple[str, str], Callable[[float], Vec]] = {}
        self.molang: Dict[Tuple[str, str], List] = {}  # channels written as Molang (cheap loops)
        self.sounds: Dict[float, str] = {}
        self.particles: List[Tuple[float, str, str]] = []
        self.samples: Dict[Tuple[str, str], np.ndarray] = {}  # pre-baked arrays (IK, springs)

    # -- channel authoring
    def set(self, bone, kind, fn, mirror=False):
        self.ch[(bone, kind)] = fn
        if mirror and right_of(bone):
            self.ch[(right_of(bone), kind)] = (lambda f: (lambda t: mirror_vec(f(t), kind)))(fn)

    def add(self, bone, kind, fn, mirror=False):
        prev = self.ch.get((bone, kind))
        if prev is None:
            self.set(bone, kind, fn, mirror)
            return
        if kind == "scale":
            self.ch[(bone, kind)] = (lambda p, f: (lambda t: p(t) * f(t)))(prev, fn)
        else:
            self.ch[(bone, kind)] = (lambda p, f: (lambda t: p(t) + f(t)))(prev, fn)
        if mirror and right_of(bone):
            rb = right_of(bone)
            mf = (lambda f: (lambda t: mirror_vec(f(t), kind)))(fn)
            prev_r = self.ch.get((rb, kind))
            if prev_r is None:
                self.ch[(rb, kind)] = mf
            elif kind == "scale":
                self.ch[(rb, kind)] = (lambda p, f: (lambda t: p(t) * f(t)))(prev_r, mf)
            else:
                self.ch[(rb, kind)] = (lambda p, f: (lambda t: p(t) + f(t)))(prev_r, mf)

    def keys(self, bone, kind, keylist, mirror=False, add=False):
        k = Keys(keylist)
        (self.add if add else self.set)(bone, kind, k, mirror)

    def rot(self, bone, keylist, **kw):
        self.keys(bone, "rotation", keylist, **kw)

    def pos(self, bone, keylist, **kw):
        self.keys(bone, "position", keylist, **kw)

    def scl(self, bone, keylist, **kw):
        self.keys(bone, "scale", keylist, **kw)

    def const(self, bone, kind, val, mirror=False, add=False):
        val = np.asarray(val, float)
        (self.add if add else self.set)(bone, kind, lambda t, val=val: val, mirror)

    def sound(self, t, key):
        self.sounds[round(t, 3)] = key

    def particle(self, t, effect, locator):
        self.particles.append((round(t, 3), effect, locator))

    def times(self):
        n = max(2, int(round(self.length * self.rate)) + 1)
        return np.linspace(0.0, self.length, n)

    # -- evaluation (for previews and IK of dependent clips)
    def value(self, bone, kind, t):
        key = (bone, kind)
        val = ONE.copy() if kind == "scale" else ZERO.copy()
        if key in self.samples:
            ts = self.times()
            arr = self.samples[key]
            sv = np.array([np.interp(t, ts, arr[:, j]) for j in range(3)])
            val = val * sv if kind == "scale" else val + sv
        if key in self.ch:
            cv = self.ch[key](t)
            val = val * cv if kind == "scale" else val + cv
        return val

    def pose(self, t, base=None):
        pose = {} if base is None else {b: {k: x.copy() for k, x in p.items()} for b, p in base.items()}
        keys = set(self.ch) | set(self.samples)
        for bone, kind in keys:
            e = pose_entry(pose, bone)
            val = self.value(bone, kind, t)
            if kind == "scale":
                e["scale"] = e["scale"] * val
            else:
                e[kind] = e[kind] + val
        return pose

    def bake_channel(self, key):
        ts = self.times()
        vals = np.array([self.value(key[0], key[1], t) for t in ts], float)
        kind = key[1]
        if self.loop is True:
            vals[-1] = vals[0]  # exact loop seam
        rest = ONE if kind == "scale" else ZERO
        if np.abs(vals - rest).max() < (0.002 if kind == "scale" else 0.05):
            return None
        if np.abs(vals - vals[0]).max() < (0.002 if kind == "scale" else 0.05):
            return [fmt(x) for x in vals[0]]
        tol = {"rotation": 0.35, "position": 0.06, "scale": 0.004}[kind]
        ks = reduce_keys(ts, vals, tol)
        out = {}
        for j in ks:
            out[f"{ts[j]:.4g}"] = {"post": [fmt(x) for x in vals[j]], "lerp_mode": "catmullrom"}
        return out

    def bake(self):
        bones: Dict[str, Dict] = {}
        for key in sorted(set(self.ch) | set(self.samples)):
            data = self.bake_channel(key)
            if data is None:
                continue
            bones.setdefault(key[0], {})[key[1]] = data
        for key, chan in self.molang.items():
            bones.setdefault(key[0], {})[key[1]] = chan
        d = {}
        if self.loop:
            d["loop"] = True if self.loop is True else "hold_on_last_frame"
        d["animation_length"] = round(self.length, 4)
        if self.atu:
            d["anim_time_update"] = self.atu
        d["bones"] = bones
        if self.sounds:
            d["sound_effects"] = {f"{t:g}": {"effect": s} for t, s in sorted(self.sounds.items())}
        if self.particles:
            pe = {}
            for t, eff, loc in sorted(self.particles):
                pe.setdefault(f"{t:g}", []).append({"effect": eff, "locator": loc})
            d["particle_effects"] = {k: (x if len(x) > 1 else x[0]) for k, x in pe.items()}
        return d
