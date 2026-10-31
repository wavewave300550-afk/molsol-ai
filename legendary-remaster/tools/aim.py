"""
aim - tiny IK helpers for authoring poses: find the Bedrock rotation of a bone that puts a point
attached to it (e.g. a child pivot or a claw tip) at a target, given the current pose.
Coordinate descent, coarse to fine. Used offline to produce numeric keyframe poses.
"""
import math

from modelkit import Cube


def xf_point(model, bone_name, pose):
    b = model.get(bone_name)
    dummy = Cube((0, 0, 0), (0, 0, 0), None)
    return model.transform(b, dummy, pose)


def solve(model, pose, bone, local_pt, target, axes=(0, 1, 2), init=None, span=180.0, lock=None, reg=0.0015):
    """Return a rotation (deg, Bedrock convention) for `bone` added to the pose so that
    local_pt (rest model space, attached to bone) lands as close as possible to target."""
    cur = list(init or pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0)))
    lock = lock or {}

    def err(rot):
        p = dict(pose)
        q = dict(p.get(bone, {}))
        q["rot"] = tuple(rot)
        p[bone] = q
        f = xf_point(model, bone, p)
        x = f(local_pt)
        return sum((x[k] - target[k]) ** 2 for k in range(3)) + reg * sum(r * r for r in rot)

    best = err(cur)
    step = span / 4
    while step > 0.05:
        improved = True
        while improved:
            improved = False
            for ax in axes:
                if ax in lock:
                    continue
                for d in (-step, step):
                    trial = list(cur)
                    trial[ax] += d
                    e = err(trial)
                    if e < best - 1e-9:
                        best, cur, improved = e, trial, True
        step *= 0.5
    for ax, v in lock.items():
        cur[ax] = v
    return tuple(round(v, 2) for v in cur), math.sqrt(best)


def chain(model, pose, steps):
    """steps: list of (bone, local_pt, target[, axes]) solved in order; returns the updated pose."""
    pose = {k: dict(v) for k, v in pose.items()}
    report = []
    for st in steps:
        bone, pt, tgt = st[0], st[1], st[2]
        axes = st[3] if len(st) > 3 else (0, 1, 2)
        rot, e = solve(model, pose, bone, pt, tgt, axes=axes)
        pose.setdefault(bone, {})["rot"] = rot
        report.append((bone, rot, round(e, 2)))
    return pose, report


def two_bone(S, W, L1, L2, pole):
    """Elbow position for a 2-bone chain from S to W (lengths L1, L2), bent towards `pole` (direction)."""
    d = [W[k] - S[k] for k in range(3)]
    D = math.sqrt(sum(x * x for x in d))
    D = min(D, L1 + L2 - 1e-3)
    u = [x / max(1e-9, D) for x in d]
    a = (L1 * L1 - L2 * L2 + D * D) / (2 * D)          # distance from S to the circle centre along u
    r = math.sqrt(max(0.0, L1 * L1 - a * a))
    c = [S[k] + u[k] * a for k in range(3)]
    pd = sum(pole[k] * u[k] for k in range(3))
    v = [pole[k] - pd * u[k] for k in range(3)]
    vl = math.sqrt(sum(x * x for x in v)) or 1.0
    return tuple(c[k] + v[k] / vl * r for k in range(3))
