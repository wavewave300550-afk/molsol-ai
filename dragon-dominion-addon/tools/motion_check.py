#!/usr/bin/env python3
"""
Motion quality report for every animation, measured on the files the game plays:
  * peak angular speed per bone (deg/s) and where it happens
  * jerk spikes: frame-to-frame change of angular velocity (sudden starts / stops = "not smooth")
  * loop seams: pose difference between the last and first frame of looping animations

    python3 tools/motion_check.py [--strict]      (--strict fails the build on violations)
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kinematics as K

RP = os.path.join(HERE, "..", "addon", "resource_packs", "dragon_dominion")
ANIMS = K.load_json(os.path.join(RP, "animations", "gharvok.animation.json"))["animations"]
FPS = 60
# limits: strikes may be fast, but nothing may snap. Accel limit is on the change of angular velocity per second.
MAX_SPEED = 900.0      # deg/s for any bone (claw / tail strikes peak here)
MAX_ACCEL = 30000.0    # deg/s^2 (a snap from rest to 900 deg/s in 1/30 s)
SEAM = 1.0             # deg


def sample(anim, t):
    pose = K.sample_pose([anim], [1.0], [t], {"q.life_time": t, "q.delta_time": 1 / FPS, "q.ground_speed": 2.2})
    return {b: np.r_[p["rotation"], p["position"] * 10] for b, p in pose.items()}


def check(name, a):
    L = a["animation_length"]
    n = max(3, int(L * FPS))
    looped = a.get("loop") is True
    # for loops, the last sample is just before the wrap and is followed by the first frame again,
    # so a seam shows up as a speed / acceleration spike
    ts = np.linspace(0, L, n + 1)[:-1] if looped else np.linspace(0, L, n + 1)
    frames = [sample(a, t) for t in ts] + ([sample(a, 0.0)] if looped else [])
    if looped:
        ts = np.r_[ts, L]
    bones = sorted(frames[0])
    arr = np.array([[f.get(b, np.zeros(6)) for b in bones] for f in frames])  # T x B x 6
    vel = np.diff(arr, axis=0) * FPS
    spd = np.linalg.norm(vel[..., :3], axis=2)
    acc = np.linalg.norm(np.diff(vel[..., :3], axis=0), axis=2) * FPS
    i, j = np.unravel_index(np.argmax(spd), spd.shape)
    k, l = np.unravel_index(np.argmax(acc), acc.shape) if acc.size else (0, 0)
    seam = 0.0
    if looped:
        # the step across the wrap compared with the steps next to it: a true seam is a jump much
        # bigger than the normal per-frame motion
        wrap = np.abs(arr[-1] - arr[-2])[..., :3]
        near = np.maximum(np.abs(arr[-2] - arr[-3])[..., :3], np.abs(arr[1] - arr[0])[..., :3])
        seam = float(np.maximum(wrap - near * 1.2, 0).max())
    return {"anim": name.split(".")[-1], "peak_speed": float(spd.max()), "speed_at": (bones[j], round(float(ts[i]), 2)),
            "peak_accel": float(acc.max()) if acc.size else 0.0, "accel_at": (bones[l], round(float(ts[k]), 2)),
            "seam": seam}


if __name__ == "__main__":
    rows = [check(n, a) for n, a in ANIMS.items()]
    bad = []
    print(f"{'animation':18} {'peak deg/s':>11} {'(bone @ t)':28} {'peak deg/s^2':>13} {'(bone @ t)':28} {'loop seam':>9}")
    for r in sorted(rows, key=lambda r: -r["peak_accel"]):
        flag = ""
        if r["peak_speed"] > MAX_SPEED or r["peak_accel"] > MAX_ACCEL or r["seam"] > SEAM:
            flag = "  <-- rough"
            bad.append(r["anim"])
        print(f"{r['anim']:18} {r['peak_speed']:11.0f} {str(r['speed_at']):28} {r['peak_accel']:13.0f} "
              f"{str(r['accel_at']):28} {r['seam']:9.2f}{flag}")
    json.dump(rows, open(os.path.join(HERE, "..", "docs", ".motion.json"), "w"), indent=1)
    print(f"\n{len(rows) - len(bad)}/{len(rows)} animations within limits (speed <= {MAX_SPEED:.0f} deg/s, "
          f"accel <= {MAX_ACCEL:.0f} deg/s^2, loop seam <= {SEAM} deg)")
    if bad and "--strict" in sys.argv:
        sys.exit(1)
