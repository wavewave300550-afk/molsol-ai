"""
animview - evaluate generated Bedrock animations (keyframes + the molang subset we emit) and
render posed frames with modelkit.render_preview, for animation QA (motion, clipping, timing).

Only evaluates expressions produced by animkit/boss_* (math.sin/cos/abs/min/max/clamp, numbers,
query.anim_time, variable.*). Never used on third-party files.
"""
import math
import re
import sys

from PIL import Image

from modelkit import render_preview


def _molang_fn(env):
    def sin(x):
        return math.sin(math.radians(x))

    def cos(x):
        return math.cos(math.radians(x))
    ns = {"sin": sin, "cos": cos, "abs": abs, "min": min, "max": max,
          "clamp": lambda v, a, b: max(a, min(b, v)), "pow": pow, "sqrt": math.sqrt, "lerp": lambda a, b, t: a + (b - a) * t}
    ns.update(env)
    return ns


def ev(expr, env):
    if isinstance(expr, (int, float)):
        return float(expr)
    e = expr.replace("math.", "").replace("query.anim_time", "anim_time").replace("query.life_time", "life_time")
    e = re.sub(r"variable\.(\w+)", r"v_\1", e)
    e = e.replace("&&", " and ").replace("||", " or ")
    return float(eval(e, {"__builtins__": {}}, _molang_fn(env)))


def chan_at(ch, t, env):
    """Evaluate a channel (list, string, number or keyframe dict) at time t."""
    if isinstance(ch, dict):
        keys = sorted(ch.items(), key=lambda kv: float(kv[0]))
        times = [float(k) for k, _ in keys]
        vals = [v["post"] if isinstance(v, dict) and "post" in v else v for _, v in keys]
        if t <= times[0]:
            return _val(vals[0], env)
        if t >= times[-1]:
            return _val(vals[-1], env)
        for i in range(len(times) - 1):
            if times[i] <= t <= times[i + 1]:
                a, b = _val(vals[i], env), _val(vals[i + 1], env)
                f = (t - times[i]) / max(1e-9, times[i + 1] - times[i])
                if isinstance(a, tuple):
                    return tuple(a[k] + (b[k] - a[k]) * f for k in range(3))
                return a + (b - a) * f
    return _val(ch, env)


def _val(v, env):
    if isinstance(v, list):
        return tuple(ev(x, env) for x in v)
    return ev(v, env)


def pose_from(anims, t, env, weights=None):
    """Sum several animations (name -> json) at time t into a render_preview pose."""
    pose = {}
    for name, a in anims.items():
        w = (weights or {}).get(name, 1.0)
        if w == 0:
            continue
        length = a.get("animation_length")
        tt = t
        if length and a.get("loop") is True:
            tt = t % length
        elif length:
            tt = min(t, length)
        e = dict(env)
        e["anim_time"] = tt
        for bone, chans in a.get("bones", {}).items():
            p = pose.setdefault(bone, {})
            if "rotation" in chans:
                r = chan_at(chans["rotation"], tt, e)
                o = p.get("rot", (0, 0, 0))
                p["rot"] = tuple(o[k] + r[k] * w for k in range(3))
            if "position" in chans:
                r = chan_at(chans["position"], tt, e)
                o = p.get("pos", (0, 0, 0))
                p["pos"] = tuple(o[k] + r[k] * w for k in range(3))
            if "scale" in chans:
                s = chan_at(chans["scale"], tt, e)
                if isinstance(s, tuple):
                    s = s[1]
                p["scale"] = p.get("scale", 1.0) * (1 + (s - 1) * w)
    return pose


def strip(model, anims, times, path, env=None, weights=None, hide=None, yaw=35, pitch=15, size=360, labels=None, box=None):
    """Render a row of posed frames into one image."""
    frames = []
    for i, t in enumerate(times):
        env2 = {"v_t": t, "v_dist": t * 6.0, "life_time": t, **(env or {})}
        pose = pose_from(anims, t, env2, weights)
        for b, s in (hide or {}).items():
            pose.setdefault(b, {})["scale"] = s
        tmp = path + f".f{i}.png"
        render_preview([model], tmp, yaw=yaw, pitch=pitch, size=size, pose=pose, step=2,
                       title=(labels[i] if labels else f"t={t:.2f}s"), view_box=box)
        frames.append(Image.open(tmp))
    W = sum(f.width for f in frames)
    out = Image.new("RGBA", (W, frames[0].height))
    x = 0
    for f in frames:
        out.paste(f, (x, 0))
        x += f.width
    out.save(path)
    import os
    for i in range(len(times)):
        os.remove(path + f".f{i}.png")
    return path
