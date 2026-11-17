#!/usr/bin/env python3
"""Creature motion check: do the dragons move the way their animations were made to move?

Reads a recorded cast (tests/.out/trace/<spell>[_real_<tag>].json) and checks every tick of every
dragon against the locomotion contract written in its asset module (tools/assets/ed_*.py):

  * STILL      a standing / acting state must not travel (a frozen pose sliding over the ground)
  * GAIT       a locomotion loop must travel at the speed its cycle was authored for (else the feet
               skate or the legs run in place)
  * TURN       turning in place must not exceed the species' turn rate
  * RADIUS     while travelling, the path must not curve tighter than the body allows (a 17-block
               dragon cannot whip around a 3-block circle)
  * BODIES     two dragons must not pass through each other (each body is a few capsules along its
               yaw, sized from the module docstrings)

  python3 tools/motion_check.py ed06              # summary + worst moments
  python3 tools/motion_check.py ed06 --real v110  # a real-server trace
  python3 tools/motion_check.py ed06 --strict     # exit 1 on any violation (for tests / CI)

Speeds are horizontal blocks per second measured over 3 ticks; the first and last 3 ticks of every
state are grace time (blends, starts and stops).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = os.path.join(HERE, "..", "tests", ".out", "trace")

# state ids -> names (mirrors STATES in the dragon modules)
NAMES = {
    "dragon_heat": ["hidden", "arrive", "idle", "move", "turn_l", "turn_r", "attack_a", "attack_b", "power", "react",
                    "rest", "depart", "ignite", "charge", "skid", "pant", "cool", "roar", "walk"],
    "dragon_tide": ["hidden", "arrive", "idle", "move", "turn_l", "turn_r", "attack_a", "attack_b", "power", "react",
                    "rest", "depart", "swim", "land", "roar", "attack_c"],
    "dragon_air": ["hidden", "arrive", "idle", "move", "glide", "turn_l", "turn_r", "roll", "stoop", "flare", "land",
                   "attack_a", "attack_b", "power", "react", "rest", "depart", "flutter"],
    "dragon_nature": ["hidden", "arrive", "idle", "move", "turn_l", "turn_r", "attack_a", "attack_b", "power", "react",
                      "rest", "depart"],
}

# Locomotion contracts.  gait: state -> (min, max) blocks/s while the loop plays.  free: states whose
# own animation contains travel (one-shots such as a landing or a skid) -> (min, max).  turn: in-place
# turn states -> max deg/s.  radius: state -> minimum turning radius (blocks) while travelling.
# Every other state is STILL (<= STILL_MAX blocks/s).
STILL_MAX = 0.6
C = {
    "dragon_heat": {   # ed_heat.py: run 10.02 (move, charge), walk 3.53, turn 225 deg/s
        "gait": {"move": (8.5, 11.5), "charge": (8.5, 11.5), "walk": (3.0, 4.1)},
        "free": {"arrive": (0.0, 4.1), "skid": (0.0, 11.5), "depart": (0.0, 4.1)},
        "turn": {"turn_l": 230.0, "turn_r": 230.0},
        "radius": {"move": 8.0, "charge": 14.0, "walk": 4.0, "arrive": 4.0},
    },
    "dragon_tide": {   # ed_tide.py: walk 2.5 (move), swim 14 (also through the air), turns 90 deg in 1.0 s
        "gait": {"move": (2.1, 2.9), "swim": (11.9, 16.1)},
        "speed3": True,
        "free": {"arrive": (0.0, 16.1), "land": (0.0, 16.1), "depart": (0.0, 16.1)},
        "turn": {"turn_l": 95.0, "turn_r": 95.0},
        "radius": {"swim": 10.0, "move": 4.0},
    },
    "dragon_air": {    # ed_air.py: flap 8-16, glide / banks 14-24, stoop 26-40, flutter 0-4
        "gait": {"move": (7.0, 17.0), "glide": (12.0, 25.0), "turn_l": (12.0, 25.0), "turn_r": (12.0, 25.0),
                 "stoop": (15.0, 41.0), "flutter": (0.0, 4.5)},
        "speed3": True,
        "free": {"arrive": (0.0, 25.0), "roll": (8.0, 25.0), "flare": (0.0, 25.0), "land": (0.0, 4.0),
                 "depart": (0.0, 17.0), "attack_a": (0.0, 25.0), "attack_b": (0.0, 25.0), "power": (0.0, 4.5)},
        "turn": {},
        "radius": {"move": 7.0, "glide": 12.0, "turn_l": 9.0, "turn_r": 9.0, "roll": 10.0},
    },
    "dragon_nature": {  # ed_nature.py: walk 1.5, turn 20 deg/s
        "gait": {"move": (1.25, 1.75)},
        "free": {"arrive": (0.0, 1.0), "depart": (0.0, 1.0)},
        "turn": {"turn_l": 24.0, "turn_r": 24.0},
        "radius": {"move": 6.0},
    },
}
GRACE = 3

# Body capsules per dragon: (ahead0, up0, ahead1, up1, side, radius) in blocks relative to the origin
# and its facing (side = sideways offset, used for the wings).  From the rig notes in each module.
BODY = {
    "dragon_heat": [(-9.6, 3.6, 7.0, 4.2, 0, 1.8)],                       # 17 blocks nose-tail, hips 5.8 up
    "dragon_tide": [(-15.0, 2.6, 10.5, 3.2, 0, 2.2), (-4.0, 6.0, 4.0, 6.5, 0, 2.2)],   # body + sail
    "dragon_air": [(-6.5, 0.9, 6.5, 0.9, 0, 1.0), (0.0, 0.9, 0.0, 0.9, 8.0, 0.6)],     # body, wings (16 span)
    "dragon_nature": [(-18.0, 5.0, 6.0, 7.0, 0, 3.6), (4.0, 8.0, 16.0, 13.0, 0, 1.6)], # body + tail, neck + head
}
CLEAR = 0.5


def _seg(a, b, c, d):
    """Shortest distance between segments ab and cd (3D)."""
    import numpy as np
    a, b, c, d = map(np.asarray, (a, b, c, d))
    u, v, w = b - a, d - c, a - c
    A, B, Cc, D, E = u @ u, u @ v, v @ v, u @ w, v @ w
    den = A * Cc - B * B
    sc = 0.0 if den < 1e-9 else min(1.0, max(0.0, (B * E - Cc * D) / den))
    tc = 0.0 if Cc < 1e-9 else min(1.0, max(0.0, (A * sc * 0 + B * sc + E) / Cc))
    sc = 0.0 if A < 1e-9 else min(1.0, max(0.0, (B * tc - D) / A))
    return float(np.linalg.norm(w + sc * u - tc * v))


def _capsules(typ, row):
    _, x, y, z, yaw = row[:5]
    f = (-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
    r = (-f[1], f[0])
    out = []
    for a0, h0, a1, h1, side, rad in BODY[typ]:
        if side:
            p = (x + f[0] * a0 + r[0] * side, y + h0, z + f[1] * a0 + r[1] * side)
            q = (x + f[0] * a0 - r[0] * side, y + h0, z + f[1] * a0 - r[1] * side)
        else:
            p = (x + f[0] * a0, y + h0, z + f[1] * a0)
            q = (x + f[0] * a1, y + h1, z + f[1] * a1)
        out.append((p, q, rad))
    return out


def bodies(tr):
    """Closest approach of every pair of dragons (blocks of clearance, < 0 = the bodies overlap)."""
    acts = [a for a in (tr["actors"].values() if isinstance(tr["actors"], dict) else tr["actors"]) if a["type"] in BODY]
    rel = tr.get("release", 0)
    rows = {a["type"]: {r[0]: r for r in a["f"] if int(r[5]) != 0} for a in acts}
    out = {}
    types = sorted(rows)
    for i in range(len(types)):
        for j in range(i + 1, len(types)):
            A, B = rows[types[i]], rows[types[j]]
            best = (1e9, 0)
            bad = []
            for t in sorted(set(A) & set(B)):
                ca, cb = _capsules(types[i], A[t]), _capsules(types[j], B[t])
                c = min(_seg(p, q, u, v) - r1 - r2 for p, q, r1 in ca for u, v, r2 in cb)
                if c < best[0]:
                    best = (c, (t - rel) / 20)
                if c < CLEAR:
                    bad.append((t - rel) / 20)
            out[(types[i], types[j])] = (best, bad)
    return out


def load(spell, real):
    name = f"{spell}_real_{real}.json" if real else f"{spell}.json"
    return json.load(open(os.path.join(TRACE, name)))


def runs(frames):
    """Split rows into runs of one state; rows are [t, x, y, z, yaw, state, ...] at consecutive ticks."""
    out, cur = [], []
    for r in frames:
        if cur and (r[5] != cur[-1][5] or r[0] - cur[-1][0] != 1):
            out.append(cur)
            cur = []
        cur.append(r)
    if cur:
        out.append(cur)
    return out


def check(tr):
    acts = tr["actors"].values() if isinstance(tr["actors"], dict) else tr["actors"]
    rel = tr.get("release", 0)
    report = {}
    for a in acts:
        typ = a["type"]
        if typ not in C:
            continue
        con, names = C[typ], NAMES[typ]
        viol = defaultdict(list)
        stats = defaultdict(list)
        for run in runs(a["f"]):
            st = names[int(run[0][5])] if int(run[0][5]) < len(names) else str(run[0][5])
            if st == "hidden" or len(run) <= 2 * GRACE:
                continue
            for i in range(GRACE, len(run) - GRACE):
                p, q = run[i - 1], run[i + 2] if i + 2 < len(run) else run[i]
                n = q[0] - p[0]
                if n <= 0:
                    continue
                sp = (math.hypot(q[1] - p[1], q[2] - p[2], q[3] - p[3]) if con.get("speed3") and st in con["gait"]
                      else math.hypot(q[1] - p[1], q[3] - p[3])) * 20 / n
                dyaw = ((q[4] - p[4] + 540) % 360 - 180) * 20 / n
                t = (run[i][0] - rel) / 20
                stats[st].append(sp)
                vert = abs(q[2] - p[2]) * 20 / n
                if st in con["gait"]:
                    lo, hi = con["gait"][st]
                    if con.get("speed3") and vert > 1.0 and math.hypot(q[1] - p[1], q[3] - p[3]) * 20 / n < 2.0:
                        pass                                    # rising / sinking in place: treading water, hovering
                    elif not lo <= sp <= hi:
                        viol["GAIT"].append((t, st, f"{sp:.1f} b/s, made for {lo:g}-{hi:g}"))
                elif st in con["free"]:
                    lo, hi = con["free"][st]
                    if sp > hi:
                        viol["GAIT"].append((t, st, f"{sp:.1f} b/s, at most {hi:g}"))
                elif st in con["turn"]:
                    if sp > STILL_MAX * 2:
                        viol["STILL"].append((t, st, f"turning in place but travelling {sp:.1f} b/s"))
                    if abs(dyaw) > con["turn"][st]:
                        viol["TURN"].append((t, st, f"{abs(dyaw):.0f} deg/s, at most {con['turn'][st]:g}"))
                else:
                    if sp > STILL_MAX:
                        viol["STILL"].append((t, st, f"standing state travelling {sp:.1f} b/s"))
                if st in con["radius"] and sp > 1.0 and abs(dyaw) > 1e-3:
                    r = sp / math.radians(abs(dyaw))
                    if r < con["radius"][st]:
                        viol["RADIUS"].append((t, st, f"turn radius {r:.1f} blocks at {sp:.1f} b/s "
                                                      f"({abs(dyaw):.0f} deg/s), at least {con['radius'][st]:g}"))
        g = viol.get("GAIT", [])
        keep = []
        for k, e in enumerate(g):
            run_ = [x for x in g if x[1] == e[1] and abs(x[0] - e[0]) <= 0.11]
            if len(run_) >= 3 or any(abs(x[0] - e[0]) <= 0.11 and x is not e for x in g if x[1] == e[1]) and len(run_) >= 3:
                keep.append(e)
        if g:
            viol["GAIT"] = keep
            if not keep:
                del viol["GAIT"]
        report[typ] = (viol, stats)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spell")
    ap.add_argument("--real", default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--all", action="store_true", help="list every violating moment")
    args = ap.parse_args()
    rep = check(load(args.spell, args.real))
    total = 0
    for typ, (viol, stats) in rep.items():
        n = sum(len(v) for v in viol.values())
        total += n
        print(f"{typ}: {n} violating ticks " + ("" if not n else
              "(" + ", ".join(f"{k} {len(v)}" for k, v in sorted(viol.items())) + ")"))
        for k, v in sorted(viol.items()):
            # group consecutive moments of one state into spans
            spans, cur = [], None
            for t, st, msg in v:
                if cur and cur[1] == st and t - cur[2] <= 0.11:
                    cur[2] = t
                    cur[3] = msg
                else:
                    if cur:
                        spans.append(cur)
                    cur = [t, st, t, msg]
            if cur:
                spans.append(cur)
            for s in (spans if args.all else spans[:6]):
                print(f"   {k:6s} {s[0]:5.1f}-{s[2]:5.1f}s  {s[1]:9s} {s[3]}")
            if not args.all and len(spans) > 6:
                print(f"   {k:6s} ... {len(spans) - 6} more spans")
    for (a, b), ((c, t), bad) in bodies(load(args.spell, args.real)).items():
        flag = f"  !! {len(bad)} ticks closer than {CLEAR} ({bad[0]:.1f}-{bad[-1]:.1f}s)" if bad else ""
        print(f"BODIES {a} / {b}: closest {c:.1f} blocks at {t:.1f}s{flag}")
        total += len(bad)
    print(f"total violating ticks: {total}")
    if args.strict and total:
        sys.exit(1)


if __name__ == "__main__":
    main()
