"""Prove that two builds animate identically: every attachable's pre_animation script and
every animation channel is evaluated in both pack trees under hundreds of random player
states, and the results must agree (rewrites of the Molang text only, no motion change).

    python3 tools/molang_equiv.py <old_packs_dir> [<new_packs_dir>] [--samples 300]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kit import molang  # noqa: E402


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def animations(root):
    out = {}
    for f in glob.glob(os.path.join(root, "PlayableRaces_RP", "animations", "**", "*.json"), recursive=True):
        out.update(_load(f)["animations"])
    return out


def attachables(root):
    out = {}
    for f in glob.glob(os.path.join(root, "PlayableRaces_RP", "attachables", "**", "*.json"), recursive=True):
        d = _load(f)["minecraft:attachable"]["description"]
        out[os.path.basename(f)] = d
    return out


def random_env(rng: random.Random) -> molang.Env:
    held = [rng.random() < 0.5, rng.random() < 0.3]
    q = {
        "life_time": rng.uniform(0, 2000), "anim_time": rng.uniform(0, 5),
        "modified_move_speed": rng.choice([0.0, rng.uniform(0, 1.2)]), "modified_distance_moved": rng.uniform(0, 3000),
        "is_sprinting": float(rng.random() < 0.4), "is_sneaking": float(rng.random() < 0.2),
        "is_on_ground": float(rng.random() < 0.7), "is_in_water": float(rng.random() < 0.1),
        "is_swimming": float(rng.random() < 0.05), "is_riding": float(rng.random() < 0.05),
        "is_gliding": float(rng.random() < 0.05), "is_sleeping": float(rng.random() < 0.05),
        "vertical_speed": rng.uniform(-14, 10), "yaw_speed": rng.uniform(-300, 300),
        "target_x_rotation": rng.uniform(-80, 80), "target_y_rotation": rng.uniform(-90, 90),
        "hurt_time": rng.choice([0.0, rng.uniform(0, 10)]), "time_of_day": rng.uniform(0, 1),
        "all_animations_finished": float(rng.random() < 0.5),
        "is_item_equipped": lambda slot=0: float(held[int(slot) if slot in (0, 1) else 0]),
    }
    v = {"attack_time": rng.choice([0.0, rng.uniform(0, 1)])}
    return molang.Env(q=q, v=v, c={"is_first_person": 0.0})


def channel_strings(anim):
    """(bone, channel, axis) -> Molang string for every expression-valued channel."""
    out = {}
    for bone, chans in anim.get("bones", {}).items():
        for ch, val in chans.items():
            if isinstance(val, list):
                for i, x in enumerate(val):
                    if isinstance(x, str):
                        out[(bone, ch, i)] = x
            elif isinstance(val, str):
                out[(bone, ch, -1)] = val
    return out


def keyframes(anim):
    return {(bone, ch): val for bone, chans in anim.get("bones", {}).items() for ch, val in chans.items()
            if isinstance(val, dict)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new", nargs="?", default=os.path.join(os.path.dirname(HERE), "packs"))
    ap.add_argument("--samples", type=int, default=300)
    args = ap.parse_args()
    old_a, new_a = animations(args.old), animations(args.new)
    old_t, new_t = attachables(args.old), attachables(args.new)
    rng = random.Random(7)
    worst, compared, problems = 0.0, 0, []
    for fname, nd in sorted(new_t.items()):
        od = old_t.get(fname)
        if od is None:
            continue
        pre_o = od.get("scripts", {}).get("pre_animation", [])
        pre_n = nd.get("scripts", {}).get("pre_animation", [])
        names = sorted(set(od["animations"]) & set(nd["animations"]))
        exprs = []
        for short in names:
            ao, an = old_a.get(od["animations"][short]), new_a.get(nd["animations"][short])
            if ao is None or an is None:
                continue
            so, sn = channel_strings(ao), channel_strings(an)
            if set(so) != set(sn):
                problems.append(f"{fname}:{short}: channel sets differ")
            if keyframes(ao) != keyframes(an):
                problems.append(f"{fname}:{short}: keyframes differ")
            exprs += [(short, key, so[key], sn[key]) for key in sorted(set(so) & set(sn), key=str)]
        for _ in range(args.samples):
            seed = rng.random()
            envs = []
            for pre in (pre_o, pre_n):
                env = random_env(random.Random(seed))
                for stmt in pre:
                    molang.evaluate(stmt, env)
                envs.append(env)
            for short, key, eo, en in exprs:
                a, b = molang.evaluate(eo, envs[0]), molang.evaluate(en, envs[1])
                compared += 1
                d = abs(a - b) / max(1.0, abs(a), abs(b))
                if not math.isfinite(d) or d > 1e-6:
                    problems.append(f"{fname}:{short}:{key}: {a} != {b}")
                worst = max(worst, d if math.isfinite(d) else 1e9)
    print(f"{compared} channel evaluations compared across {len(new_t)} attachables; worst relative difference {worst:.2e}")
    for p in sorted(set(problems))[:30]:
        print("  MISMATCH", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
