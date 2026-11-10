#!/usr/bin/env python3
"""
Motion quality checks on the BAKED animation file (what the game will play):

  * foot slip: for speed-synced loops, how far each planted foot moves relative to the ground
    (the ground moves backwards at stride/length in model space)
  * ground penetration: lowest point of the model for every ground clip (additive clips are
    composed over idle_breathe like the controllers do)
  * loop seams: first and last keyframe of every looping channel must match
  * one-shot additive overlays start and end at rest (no pop when the controller enters/leaves them)
  * key density: frames per channel (motion is real keyframes, not a single rotation)

    python3 tools/motion_checks.py            (prints a table, writes tools/motion_report.json)
    python3 tools/motion_checks.py --v1 <old animation.json>   (also measures the old walk)
Exit code 1 on failures.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")
P = "animation.dod.red_dragon."
GEO = K.load_json(os.path.join(RP, "models", "entity", "red_dragon.geo.json"))["minecraft:geometry"][0]
LOCS = {}
for b in GEO["bones"]:
    for ln, lv in (b.get("locators") or {}).items():
        LOCS[ln] = (b["name"], np.array(lv, float))
BALL = {}
for side in ("fl", "fr", "hl", "hr"):
    tb = next(b for b in GEO["bones"] if b["name"] == f"toes_{side}") if any(b["name"] == f"toes_{side}" for b in GEO["bones"]) else None
    BALL[side] = (f"toes_{side}" if tb else f"foot_{side}", np.array(tb["pivot"] if tb else LOCS[f"claw_{side}"][1], float))


def poses(anims, layers, length, n, env=None):
    out = []
    for i in range(n + 1):
        t = length * i / n
        e = dict(env or {})
        e["q.life_time"] = t
        out.append((t, K.sample_pose([anims[P + l] for l, _ in layers], [w for _, w in layers], [t] * len(layers), e)))
    return out


def foot_slip(anims, name, stride_blocks, n=96, geo=None):
    """Max ground-frame drift of each foot while it is on the ground (y within 1 unit of its lowest)."""
    geo = geo or GEO
    a = anims[P + name]
    L = a["animation_length"]
    v = stride_blocks * 16 / L
    res = {}
    seq = poses(anims, [(name, 1)], L, n)
    for side, (bone, pt) in BALL.items():
        if not any(b["name"] == bone for b in geo["bones"]):
            bone, pt = f"foot_{side}", LOCS.get(f"claw_{side}", LOCS.get(f"foot_{side}", (None, np.zeros(3))))[1]
        pos = np.array([K.bone_matrices(geo, p)[bone] @ np.append(pt, 1) for _, p in seq])[:, :3]
        ts = np.array([t for t, _ in seq])
        ground = pos[:, 1] < pos[:, 1].min() + 1.0
        zg = pos[:, 2] - v * ts
        # contiguous contact runs (wrap around the loop)
        worst = 0.0
        idx = np.where(ground[:-1])[0]
        if len(idx):
            runs, cur = [], [idx[0]]
            for j in idx[1:]:
                if j == cur[-1] + 1:
                    cur.append(j)
                else:
                    runs.append(cur)
                    cur = [j]
            runs.append(cur)
            if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == n - 1:
                last = runs.pop()
                runs[0] = last + runs[0]
            for r in runs:
                z = np.array([zg[j] if j >= r[0] else zg[j] + v * L for j in r]) if r[0] > r[-1] else zg[r]
                if r[0] > r[-1]:
                    z = np.array([pos[j, 2] - v * (ts[j] - (L if j >= r[0] else 0)) for j in r])
                worst = max(worst, float(z.max() - z.min()))
        res[side] = round(worst, 3)
    return res


def lowest(anims, layers, length, n=40):
    m = 1e9
    for _, p in poses(anims, layers, length, n):
        for _, _, Pts, _, _ in K.world_faces(GEO, p):
            m = min(m, float(Pts[:, 1].min()))
    return round(m, 2)


def main(argv):
    anims = K.load_json(os.path.join(RP, "animations", "red_dragon.animation.json"))["animations"]
    rep = json.load(open(os.path.join(ROOT, "tools", "anim_report.json")))
    fails = []
    out = {"foot_slip_units": {}, "lowest_point": {}, "loop_seams": {}, "keys": {}}
    out["foot_slip_units"]["walk_loop"] = foot_slip(anims, "walk_loop", 3.0)
    out["foot_slip_units"]["run_loop"] = foot_slip(anims, "run_loop", 2.8)
    for clip, s in out["foot_slip_units"].items():
        if max(s.values()) > 1.5:
            fails.append(f"{clip}: foot slip {s}")
    for n, meta in rep.items():
        if meta["category"].startswith(("C",)) and n not in ("pre_takeoff", "landing_impact"):
            continue
        layers = [(n, 1)] if meta["kind"] == "absolute" else [("idle_breathe", 1), (n, 1)]
        if n == "rest_breathe":
            layers = [("rest_lower", 1), (n, 1)]
        if n in ("flight_bank_left", "flight_bank_right"):
            continue
        low = lowest(anims, layers, meta["length"])
        out["lowest_point"][n] = low
        if low < -1.5:
            fails.append(f"{n}: model goes {low} units below the ground")
    for name, a in anims.items():
        if a.get("loop") is not True:
            continue
        for bone, chans in a["bones"].items():
            for kind, ch in chans.items():
                if isinstance(ch, dict):
                    ks = sorted(ch, key=float)
                    first = ch[ks[0]]["post"] if isinstance(ch[ks[0]], dict) else ch[ks[0]]
                    last = ch[ks[-1]]["post"] if isinstance(ch[ks[-1]], dict) else ch[ks[-1]]
                    if abs(float(ks[-1]) - a["animation_length"]) > 1e-3 or float(ks[0]) > 1e-3 or \
                            max(abs(float(x) - float(y)) for x, y in zip(first, last)) > 0.02:
                        fails.append(f"{name[len(P):]}: {bone}.{kind} loop seam open")
        out["loop_seams"][name[len(P):]] = "closed"
    # one-shot additive overlays must start and end at rest, so entering/leaving them never pops
    # (deg for rotation; position x5 and scale x50 so all three are on a comparable scale)
    out["additive_boundaries"] = {}
    for n, meta in rep.items():
        if meta["kind"] != "additive" or meta["loop"] is not False:
            continue
        a = anims[P + n]
        dev = []
        for t in (0.0, a["animation_length"]):
            pose = K.sample_pose([a], [1], [t], {"q.life_time": t, "q.anim_time": t, "prop:dod:aim": 0})
            dev.append(max([0.0] + [max(float(np.abs(e["rotation"]).max()), float(np.abs(e["position"]).max()) * 5,
                                        float(np.abs(e["scale"] - 1).max()) * 50) for e in pose.values()]))
        out["additive_boundaries"][n] = [round(dev[0], 2), round(dev[1], 2)]
        if max(dev) > 1.0:
            fails.append(f"{n}: additive overlay does not start/end at rest ({dev[0]:.2f} / {dev[1]:.2f})")
    for name, a in anims.items():
        nk = [len(ch) for b in a["bones"].values() for ch in b.values() if isinstance(ch, dict)]
        out["keys"][name[len(P):]] = {"channels": sum(len(b) for b in a["bones"].values()), "keyed": len(nk),
                                      "max_keys": max(nk) if nk else 0}
    if "--v1" in argv:
        old = K.load_json(argv[argv.index("--v1") + 1])["animations"]
        out["v1_walk_foot_slip_units"] = v1_slip(old)
    json.dump(out, open(os.path.join(ROOT, "tools", "motion_report.json"), "w"), indent=1)
    print("foot slip while planted (units, 16 = 1 block):", out["foot_slip_units"])
    if "v1_walk_foot_slip_units" in out:
        print("v1 walk foot slip (same measure):", out["v1_walk_foot_slip_units"])
    worst = sorted(out["lowest_point"].items(), key=lambda kv: kv[1])[:6]
    print("lowest points (ground clips):", worst)
    print(f"loop seams closed: {len(out['loop_seams'])} looping clips")
    wb = max(max(v) for v in out["additive_boundaries"].values())
    print(f"one-shot additive overlays start/end at rest: {len(out['additive_boundaries'])} clips, worst {wb:.2f}")
    for f in fails:
        print("  FAIL:", f)
    return 1 if fails else 0


def v1_slip(old):
    """v1 walk: sine-driven legs on q.modified_distance_moved (no IK, not speed synced).  Measured with
    the same rig at a walking speed of 1.6 b/s (modified_distance_moved ~ 4 units per block)."""
    a = old[P + "walk"]
    speed, n = 1.6, 96
    T = (360 / 22 / 4) / speed  # one v1 leg cycle in seconds
    res = {}
    for side, (bone, pt) in BALL.items():
        pos, ts = [], []
        for i in range(n + 1):
            t = T * i / n
            env = {"q.modified_distance_moved": 4 * speed * t, "q.life_time": t, "v.walk_w": 1.0}
            pose = K.sample_pose([old[P + "idle"], a], [1, 1], [t, t], env)
            pos.append((K.bone_matrices(GEO, pose)[bone] @ np.append(pt, 1))[:3])
            ts.append(t)
        pos, ts = np.array(pos), np.array(ts)
        ground = pos[:, 1] < pos[:, 1].min() + 1.0
        zg = pos[:, 2] - speed * 16 * ts
        res[side] = round(float(zg[ground].max() - zg[ground].min()), 2) if ground.any() else None
    return res


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
