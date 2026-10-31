"""
Render preview sheets of creatures: rest pose from several angles, plus poses
sampled from the real animations (acts at their impact marks) with the same
Molang the game evaluates.

    python3 tools/preview.py [creature ...] [--out DIR] [--acts]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from creatures import registry  # noqa: E402
from mk import molang  # noqa: E402
from mk.anim import sample  # noqa: E402
from mk.render import render_views  # noqa: E402


def make_env(c, props, life=1.3, moving=0.0):
    p = dict(c.preview_props)
    p.update(props)
    q = {"life_time": life, "modified_move_speed": moving, "modified_distance_moved": life * 3 * moving,
         "is_on_ground": 1.0, "target_x_rotation": 0.0, "target_y_rotation": 0.0, "ground_speed": moving,
         "is_moving": 1.0 if moving else 0.0,
         "property": lambda name: float(p.get(name, 0)), "has_property": lambda name: 1.0}
    env = molang.Env(q)
    for _ in range(80):          # let lerp-smoothed variables settle
        for s in c.pre:
            molang.evaluate(s, env)
    return env


def pose_for(c, act=None, t=0.0, props=None, life=1.3, moving=0.0):
    props = dict(props or {})
    if act:
        props["legends:act"] = c.act_by_name(act).id
    env = make_env(c, props, life, moving)
    pose = {}
    for short, a, weight in c.loops:
        w = molang.evaluate(weight, env) if weight else 1.0
        env.queries["anim_time"] = life
        sample(a.json(), life, env, w, pose)
    if act:
        sample(c.act_by_name(act).anim.json(), t, env, 1.0, pose)
    vis_rules = c.visibility

    def visible(bone):
        for b, expr in vis_rules:
            if b == bone and not molang.evaluate(expr, env):
                return False
        return True
    return pose, visible


def render_creature(c, out, acts=False):
    m = c.model
    m.paint()
    views = [(-35, 18), (35, 12), (90, 4), (180, 15), (0, 70)]
    labels = ["front-right", "front-left", "left side", "back", "top"]
    ph = c.preview_props.get("legends:phase", 1)
    pose, vis = pose_for(c, props={"legends:phase": ph})
    img = render_views([(m, pose, vis)], views, size=380, labels=labels, title=f"{c.key} — rest pose  {m.stats()}")
    tag = "".join(f"_{k.split(':')[-1]}{int(v)}" for k, v in c.preview_props.items() if k != "legends:phase")
    img.save(os.path.join(out, f"{c.key}{tag}_rest.png"))
    if acts:
        frames = []
        for a in c.acts:
            ts = a.marks[:1] or [a.length * 0.5]
            frames.append((a, ts[0]))
        tag = "".join(f"_{k.split(':')[-1]}{int(v)}" for k, v in c.preview_props.items() if k != "legends:phase")
        for i in range(0, len(frames), 5):
            chunk = frames[i:i + 5]
            groups = []
            imgs = []
            for a, tt in chunk:
                props = {"legends:phase": ph}
                pose, vis = pose_for(c, a.name, tt, props)
                imgs.append(render_views([(m, pose, vis)], [(-40, 14)], size=300, labels=[f"{a.name} @{tt:.2f}s"]))
            from PIL import Image
            sheet = Image.new("RGB", (300 * len(imgs), imgs[0].height))
            for k, im in enumerate(imgs):
                sheet.paste(im, (k * 300, 0))
            sheet.save(os.path.join(out, f"{c.key}{tag}_acts{i // 5}.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "docs", "previews"))
    ap.add_argument("--acts", action="store_true")
    ap.add_argument("--phase", type=int, default=None)
    ap.add_argument("--prop", action="append", default=[])
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for name, fn in registry.ALL.items():
        if args.names and name not in args.names:
            continue
        c = fn()
        if args.phase is not None:
            c.preview_props["legends:phase"] = args.phase
        for kv in args.prop:
            k, v = kv.split("=")
            c.preview_props[k] = float(v)
        render_creature(c, args.out, args.acts)
        print(name, c.model.stats())


if __name__ == "__main__":
    main()
