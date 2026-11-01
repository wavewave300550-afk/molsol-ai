"""Samples Bedrock animation JSON (linear + catmull-rom keyframes, simple Molang) for previews."""
import math
import re

FP_RE = re.compile(r"^\s*v\.is_first_person\s*\?\s*(.+?)\s*:\s*(.+)$")


def ev(expr, t=0.0, fp=False):
    if isinstance(expr, (int, float)):
        return float(expr)
    s = str(expr).strip()
    m = FP_RE.match(s)
    if m:
        s = m.group(1) if fp else m.group(2)
    s = s.replace("q.anim_time", f"({t})").replace("query.anim_time", f"({t})")
    s = s.replace("math.sin(", "_sin(").replace("math.cos(", "_cos(").replace("math.min(", "min(").replace("math.max(", "max(")
    s = s.replace("math.pow(", "pow(").replace("math.abs(", "abs(")
    return float(eval(s, {"__builtins__": {}}, {"_sin": lambda d: math.sin(math.radians(d)), "_cos": lambda d: math.cos(math.radians(d)), "min": min, "max": max, "pow": pow, "abs": abs}))


def _vec(v, t, fp):
    if isinstance(v, dict):
        v = v.get("post", v.get("pre"))
    if isinstance(v, (int, float, str)):
        x = ev(v, t, fp)
        return [x, x, x]
    return [ev(c, t, fp) for c in v]


def _smooth(v):
    return isinstance(v, dict) and v.get("lerp_mode") == "catmullrom"


def sample_channel(ch, t, fp=False):
    if not isinstance(ch, dict) or not all(re.match(r"^[0-9.]+$", k) for k in ch):
        return _vec(ch, t, fp)
    keys = sorted((float(k), v) for k, v in ch.items())
    if t <= keys[0][0]:
        return _vec(keys[0][1], t, fp)
    if t >= keys[-1][0]:
        return _vec(keys[-1][1], t, fp)
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            p1, p2 = _vec(v0, t, fp), _vec(v1, t, fp)
            if _smooth(v0) or _smooth(v1):
                p0 = _vec(keys[i - 1][1], t, fp) if i > 0 else p1
                p3 = _vec(keys[i + 2][1], t, fp) if i + 2 < len(keys) else p2
                return [0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
                        for a, b, c, d in zip(p0, p1, p2, p3)]
            return [a + (b - a) * u for a, b in zip(p1, p2)]
    return _vec(keys[-1][1], t, fp)


def pose(anim, t, fp=False):
    out = {}
    length = anim.get("animation_length")
    if length is not None:
        t = min(t, length)
    for bone, chans in anim.get("bones", {}).items():
        out[bone] = {k: sample_channel(v, t, fp) for k, v in chans.items()}
    return out
