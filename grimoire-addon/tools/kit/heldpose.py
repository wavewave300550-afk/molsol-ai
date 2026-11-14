"""Pose of a held book (attachable) as the game would draw it, in Blockbench space.

Shared by tools/held_preview.py (pictures) and tools/assets/books_zfix.py (placing the built-in
circle on the posed book).  Evaluates the attachable's animate list with kit.molang: plain
animations, Molang-driven one-shots (anim_time_update) and controllers followed to their steady
state.  pre_animation is NOT run: pass the variables it would compute in `extra` (v.open, v.aura...).
Blockbench space = the Bedrock file with X mirrored.
"""
from __future__ import annotations

import json
import os

import numpy as np

from kit.geo import rot_matrix
from kit.molang import Molang


def bb_vec(v):
    return np.array([-float(v[0]), float(v[1]), float(v[2])])


def bb_rot(v):
    return (-float(v[0]), -float(v[1]), float(v[2]))


def pose_bones(rp, g, item, first_person, open_amount, extra=None):
    """(bones by name, mat(name) -> 4x4 bone-to-model matrix) for book model `g` held as `item`."""
    geo = json.load(open(os.path.join(rp, "models", "entity", f"{g}.geo.json")))["minecraft:geometry"][0]
    anims = json.load(open(os.path.join(rp, "animations", f"{g}.animation.json")))["animations"]
    att = json.load(open(os.path.join(rp, "attachables", f"{item}.json")))["minecraft:attachable"]["description"]
    ev = Molang({"c.is_first_person": 1.0 if first_person else 0.0, "context.is_first_person": 1.0 if first_person else 0.0,
                  "v.open": open_amount, "variable.open": open_amount, "q.life_time": 0.0, "q.anim_time": 0.0,
                  "q.main_hand_item_use_duration": 0.0,
                  "v.aura": 0.9 * open_amount, "v.sel": 1.0, "v.spin1": 0.0, "v.spin2": 0.0, **(extra or {})})
    pose = {}
    ctl_path = os.path.join(rp, "animation_controllers", f"{g}.animation_controllers.json")
    ctls = json.load(open(ctl_path))["animation_controllers"] if os.path.exists(ctl_path) else {}
    use = Molang({**ev.env, "q.main_hand_item_use_duration": 100.0 if open_amount > 0 else 0.0, "q.is_sneaking": 0.0,
                  "q.all_animations_finished": 1.0})

    def key_value(v):
        if isinstance(v, dict):
            v = v.get("post", v.get("pre"))
        if not isinstance(v, list):
            v = [v, v, v]
        return np.array([ev(c) for c in v], float)

    def apply(a, at_end):
        t_set = ev(a["anim_time_update"]) if "anim_time_update" in a else None
        for bone, chs in a.get("bones", {}).items():
            r, p, s = pose.get(bone, ((0, 0, 0), np.zeros(3), np.ones(3)))
            for ch, val in chs.items():
                if isinstance(val, dict):          # keyframes
                    keys = sorted(val, key=float)
                    if t_set is not None:          # time driven by Molang: interpolate at that time
                        ts = [float(k) for k in keys]
                        if t_set <= ts[0]:
                            x = key_value(val[keys[0]])
                        elif t_set >= ts[-1]:
                            x = key_value(val[keys[-1]])
                        else:
                            j = max(i for i in range(len(ts)) if ts[i] <= t_set)
                            f = (t_set - ts[j]) / (ts[j + 1] - ts[j])
                            x = key_value(val[keys[j]]) * (1 - f) + key_value(val[keys[j + 1]]) * f
                        x = list(x)
                    else:                          # steady state = last key, else the first
                        x = list(key_value(val[keys[-1] if at_end else keys[0]]))
                else:
                    x = list(key_value(val))
                if ch == "rotation":
                    rr = bb_rot(x)
                    r = tuple(r[i] + rr[i] for i in range(3))
                elif ch == "position":
                    p = p + bb_vec(x)
                elif ch == "scale":
                    s = s * np.array(x)
            pose[bone] = (r, p, s)

    for entry in att["scripts"]["animate"]:
        name, cond = (entry, None) if isinstance(entry, str) else next(iter(entry.items()))
        if cond is not None and not ev(cond):
            continue
        full = att["animations"].get(name, "")
        if full in ctls:                           # controller: follow its transitions to the steady state
            c = ctls[full]
            st = c.get("initial_state", "default")
            for _ in range(3):
                nxt = None
                for t in c["states"][st].get("transitions", []):
                    (to, q), = t.items()
                    if use(q):
                        nxt = to
                        break
                if nxt is None:
                    break
                st = nxt
            for an in c["states"][st].get("animations", []) or []:
                an = an if isinstance(an, str) else next(iter(an))
                a = anims.get(att["animations"].get(an, ""))
                if a:
                    apply(a, True)
            continue
        a = anims.get(full)
        if a:
            apply(a, False)
    bones = {b["name"]: b for b in geo["bones"]}
    mats = {}

    def mat(name):
        if name in mats:
            return mats[name]
        b = bones[name]
        piv = bb_vec(b.get("pivot", [0, 0, 0]))
        br = bb_rot(b.get("rotation", [0, 0, 0]))
        r, p, s = pose.get(name, ((0, 0, 0), np.zeros(3), np.ones(3)))
        R = rot_matrix(*(br[i] + r[i] for i in range(3))) @ np.diag(s)
        m = np.eye(4)
        m[:3, :3] = R
        m[:3, 3] = piv + p - R @ piv
        if b.get("parent"):
            m = mat(b["parent"]) @ m
        mats[name] = m
        return m

    return bones, mat


def cube_box(c):
    """(lo, hi, cube matrix) of a geometry cube in bb space (cube rotation about its own pivot)."""
    o, sz, inf = np.array(c["origin"], float), np.array(c["size"], float), float(c.get("inflate", 0.0))
    x0 = -(o[0] + sz[0]) - inf
    lo = np.array([x0, o[1] - inf, o[2] - inf])
    hi = lo + sz + 2 * inf
    cm = np.eye(4)
    if c.get("rotation"):
        cp = bb_vec(c.get("pivot", [0, 0, 0]))
        R = rot_matrix(*bb_rot(c["rotation"]))
        cm[:3, :3] = R
        cm[:3, 3] = cp - R @ cp
    return lo, hi, cm


def corners(lo, hi):
    return np.array([[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
