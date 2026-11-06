#!/usr/bin/env python3
"""Fit wing joint angles so the wrist and finger tips land on target points read off the reference sheet.
Prints pose dicts for gen_anims.py (FOLD = tight fold, DISPLAY = the reference's raised, draped stance)."""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kinematics as K

geo = K.load_json(os.path.join(HERE, "..", "addon", "resource_packs", "dragon_dominion", "models", "entity",
                               "gharvok.geo.json"))["minecraft:geometry"][0]
B = {b["name"]: b for b in geo["bones"]}
FL = {"wing_l_f1": 52, "wing_l_f2": 58, "wing_l_f3": 60, "wing_l_f4": 54}
WRIST = np.array(B["wing_l_hand"]["pivot"], float)


def local(name, rot):
    b = B[name]
    piv = np.array(b["pivot"], float)
    r = np.array(b.get("rotation", [0, 0, 0]), float) + np.array(rot, float)
    return K.affine(t=piv) @ K.affine(K.brot(r)) @ K.affine(t=-piv)


def points(p):
    M = local("wing_l_arm", p["arm"]) @ local("wing_l_fore", p["fore"]) @ local("wing_l_hand", p["hand"])
    out = {"wrist": (M @ np.r_[WRIST, 1])[:3]}
    for i, f in enumerate(FL):
        Mf = M @ local(f, (0, p["spread"] * (i - 1.5) / 1.5, 0))
        out[f] = (Mf @ np.r_[WRIST + [FL[f], 0, 0], 1])[:3]
        out[f + "_mid"] = (Mf @ np.r_[WRIST + [FL[f] * 0.5, 0, 0], 1])[:3]
    out["elbow"] = (local("wing_l_arm", p["arm"]) @ np.r_[B["wing_l_fore"]["pivot"], 1])[:3]
    return out


def fit(targets, weights, seed=1, n=40000, extra=None):
    rng = np.random.default_rng(seed)
    best = None
    def cost(p):
        P = points(p)
        c = sum(weights.get(k, 1) * np.linalg.norm(P[k] - np.array(v)) for k, v in targets.items())
        if extra:
            c += extra(P)
        return c
    for _ in range(n):
        p = {"arm": rng.uniform([-90, -110, -80], [90, 60, 40]), "fore": rng.uniform([-60, -40, -60], [60, 170, 80]),
             "hand": rng.uniform([-90, -170, -90], [90, 60, 90]), "spread": rng.uniform(-30, 30)}
        c = cost(p)
        if best is None or c < best[0]:
            best = (c, p)
    c, p = best
    step = 12.0
    while step > 0.2:  # coordinate descent refine
        improved = False
        for k in ("arm", "fore", "hand"):
            for i in range(3):
                for d in (step, -step):
                    q = {kk: (np.array(vv, float).copy() if kk != "spread" else vv) for kk, vv in p.items()}
                    q[k][i] += d
                    cq = cost(q)
                    if cq < c:
                        c, p, improved = cq, q, True
        for d in (step, -step):
            q = dict(p)
            q["spread"] = p["spread"] + d
            cq = cost(q)
            if cq < c:
                c, p, improved = cq, q, True
        if not improved:
            step /= 2
    return c, p


def show(name, c, p):
    P = points(p)
    print(f"# {name}: cost {c:.1f}")
    print(f'{name} = {{"arm": {tuple(round(float(v), 1) for v in p["arm"])}, "fore": {tuple(round(float(v), 1) for v in p["fore"])}, '
          f'"hand": {tuple(round(float(v), 1) for v in p["hand"])}, "spread": {round(float(p["spread"]), 1)}}}')
    for k in ("elbow", "wrist", "wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4"):
        print("   ", k, np.round(P[k], 1))


if __name__ == "__main__":
    # DISPLAY: wrist high and outside the shoulder, fingers fanned and hanging down to about knee height
    # outside the legs (front view), trailing back over the hips (side view)
    disp_t = {"elbow": (42, 84, -8), "wrist": (74, 96, -6), "wing_l_f1": (116, 46, -4), "wing_l_f2": (106, 32, 14),
              "wing_l_f3": (90, 30, 32), "wing_l_f4": (70, 40, 46)}
    show("DISPLAY", *fit(disp_t, {"wrist": 3, "elbow": 1.5}, n=60000))
    # FOLD: wrist up beside the shoulder hump, fingers lying back along the flank above the hind leg
    fold_t = {"elbow": (32, 70, 14), "wrist": (34, 80, -16), "wing_l_f1": (36, 74, 34), "wing_l_f2": (36, 66, 40),
              "wing_l_f3": (34, 58, 42), "wing_l_f4": (32, 54, 36)}
    show("FOLD", *fit(fold_t, {"wrist": 2, "elbow": 1.5}, seed=2))


def render(poses, out):
    import render_preview as R
    pose = {}
    for name, p in poses.items():
        pose[name] = p
    R.four_view(pose, out)
