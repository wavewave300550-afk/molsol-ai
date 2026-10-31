"""
animkit - pose-keyframed acts and procedural loops for Bedrock animation JSON (format 1.8.0).

Acts (one-shot animations driven by the `legends:act` property) are written as a list of key
poses at tick times. A pose names only the bones it changes; every other bone keeps the value it
had at the previous key (cumulative poses), `reset=True` starts again from the rest pose.
Each segment between two keys is eased in Python (two extra linear sub-keys), so motion has
anticipation, snap and follow-through without relying on catmull-rom overshoot:
    "io"  smooth in-out (default)    "in"  accelerate into the key (strikes, slams)
    "out" decelerate into the key    "lin" constant speed         "hold" jump (no blend)
Channels: "r" rotation (deg), "p" position (model units), "s" uniform scale.
Procedural overlays (molang strings) can be added per bone/channel for the whole act.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

A = "query.anim_time"
T = "variable.t"
EASE = {
    "io": (0.259, 0.741),
    "in": (0.111, 0.444),
    "out": (0.556, 0.889),
    "lin": (1 / 3, 2 / 3),
}
REST = {"r": (0.0, 0.0, 0.0), "p": (0.0, 0.0, 0.0), "s": 1.0}
CH_NAME = {"r": "rotation", "p": "position", "s": "scale"}


def f3(x):
    return round(float(x), 3)


def sn(k, ph=0.0, amp=1.0, clock=T, off=None):
    """molang sin wave: sin(clock*k + ph) * amp (degrees, Bedrock style)."""
    p = f" + {f3(ph)}" if ph else ""
    o = f"{f3(off)} + " if off else ""
    return f"({o}math.sin({clock} * {f3(k)}{p}) * {f3(amp)})"


def cs(k, ph=0.0, amp=1.0, clock=T, off=None):
    p = f" + {f3(ph)}" if ph else ""
    o = f"{f3(off)} + " if off else ""
    return f"({o}math.cos({clock} * {f3(k)}{p}) * {f3(amp)})"


def vec(*v):
    return [x if isinstance(x, str) else f3(x) for x in v]


def loop(bones: Dict[str, dict]) -> dict:
    """Procedural loop. bones: {bone: {"r": [x,y,z], "p": [...], "s": v}} (numbers or molang)."""
    out = {}
    for b, chans in bones.items():
        jb = {}
        for ch, val in chans.items():
            if ch == "s":
                jb["scale"] = val if isinstance(val, str) else f3(val)
            else:
                jb[CH_NAME[ch]] = vec(*val)
        out[b] = jb
    return {"loop": True, "bones": out}


class Act:
    def __init__(self, name: str, ticks: int, marks=(), loop: bool = False):
        self.name = name
        self.ticks = int(ticks)
        self.marks = [int(m) for m in marks]
        self.loop = loop
        self.keys: List[Tuple[float, dict, str, bool]] = []
        self.over: Dict[Tuple[str, str], str] = {}

    def at(self, tick, pose: Optional[dict] = None, ease: str = "io", reset: bool = False) -> "Act":
        self.keys.append((float(tick), pose or {}, ease, reset))
        return self

    def overlay(self, bone: str, ch: str, molang) -> "Act":
        """Procedural term added to a channel for the whole act (list of 3 strings/numbers, or a string for 's')."""
        self.over[(bone, ch)] = molang
        return self

    # ------------------------------------------------------------------ export
    def to_json(self) -> dict:
        keys = sorted(self.keys, key=lambda k: k[0])
        if not keys or keys[0][0] > 0:
            keys.insert(0, (0.0, {}, "io", True))
        bones = set()
        for _, pose, _, _ in keys:
            for b, chans in pose.items():
                for ch in chans:
                    bones.add((b, ch))
        for (b, ch) in self.over:
            bones.add((b, ch))
        # cumulative state per key
        states = []
        cur: Dict[Tuple[str, str], object] = {}
        for t, pose, ease, reset in keys:
            if reset:
                cur = {}
            for b, chans in pose.items():
                for ch, val in chans.items():
                    cur[(b, ch)] = tuple(val) if ch != "s" else float(val)
            states.append((t, dict(cur), ease))
        out: Dict[str, dict] = {}
        for (b, ch) in sorted(bones):
            rest = REST[ch]
            frames = {}
            prev = None
            for i, (t, st, ease) in enumerate(states):
                val = st.get((b, ch), rest)
                if prev is not None and ease != "hold" and val != prev[1]:
                    e1, e2 = EASE.get(ease, EASE["io"])
                    t0 = prev[0]
                    for frac, e in ((1 / 3, e1), (2 / 3, e2)):
                        tt = t0 + (t - t0) * frac
                        frames[tt] = self._lerp(prev[1], val, e)
                if prev is not None and ease == "hold" and val != prev[1]:
                    frames[max(prev[0], t - 0.5)] = prev[1]
                frames[t] = val
                prev = (t, val)
            ov = self.over.get((b, ch))
            jf = {}
            for tt in sorted(frames):
                v = frames[tt]
                sec = f"{tt / 20.0:.4f}".rstrip("0").rstrip(".") or "0"
                if ch == "s":
                    jf[sec] = f"{f3(v)} + ({ov})" if ov else f3(v)
                else:
                    if ov:
                        jf[sec] = [f"{f3(v[k])} + ({ov[k]})" if not (isinstance(ov[k], (int, float)) and ov[k] == 0) else f3(v[k]) for k in range(3)]
                    else:
                        jf[sec] = [f3(x) for x in v]
            if len(jf) == 1 and not ov:
                jf = list(jf.values())[0]
                if ch != "s" and isinstance(jf, list) and all(x == 0 for x in jf):
                    continue
            out.setdefault(b, {})[CH_NAME[ch]] = jf
        anim = {"bones": out}
        if self.loop:
            anim["loop"] = True
            anim["animation_length"] = round(self.ticks / 20.0, 3)
        else:
            anim["loop"] = "hold_on_last_frame"
            anim["animation_length"] = round(self.ticks / 20.0, 3)
        return anim

    @staticmethod
    def _lerp(a, b, e):
        if isinstance(a, tuple):
            return tuple(a[k] + (b[k] - a[k]) * e for k in range(3))
        return a + (b - a) * e


def merge(*poses: dict) -> dict:
    """Combine poses; later channels override earlier ones."""
    out: Dict[str, dict] = {}
    for p in poses:
        for b, chans in p.items():
            out.setdefault(b, {}).update(chans)
    return out


def mirror(pose: dict, pairs=(("_r", "_l"),)) -> dict:
    """Mirror a pose left/right: swap *_r/*_l bones, negate y/z rotation and x position."""
    out = {}
    for b, chans in pose.items():
        nb = b
        for a, c in pairs:
            if b.endswith(a):
                nb = b[: -len(a)] + c
            elif b.endswith(c):
                nb = b[: -len(c)] + a
        nc = {}
        for ch, v in chans.items():
            if ch == "r":
                nc[ch] = (v[0], -v[1], -v[2])
            elif ch == "p":
                nc[ch] = (-v[0], v[1], v[2])
            else:
                nc[ch] = v
        out[nb] = nc
    return out


def sym(pose_r: dict) -> dict:
    """A pose and its mirror applied together (both sides do the same)."""
    return merge(pose_r, mirror(pose_r))


def acts_table(acts: List[Act]) -> Dict[str, dict]:
    """{name: {id, ticks, marks}} with ids in declaration order (1-based)."""
    return {a.name: {"id": i + 1, "ticks": a.ticks, "marks": a.marks} for i, a in enumerate(acts)}
