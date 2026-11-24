"""Render filmstrips of baked actions:  python3 tools/animpreview.py <outdir> [action ...]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anims  # noqa: E402
from modelkit import contact_sheet, render  # noqa: E402


def strip(sampler, act, out, frames=6, yaw=35, variant="base", glow="glow1"):
    baked = sampler.bake(act)
    n = len(next(iter(baked.values())))
    idx = [round(i * (n - 1) / (frames - 1)) for i in range(frames)]
    paths = []
    for k, f in enumerate(idx):
        pose = {bone: chans[f] for bone, chans in baked.items()}
        p = os.path.join(out, f"{act.name}_{k}.png")
        render([(sampler.model, pose, variant, glow, (0, 0, 0))], p, yaw=yaw, pitch=12, size=360,
               title=f"{act.name} t={f * anims.DT:.2f}", span=78, center=(0, 26, 4))
        paths.append(p)
    sheet = os.path.join(out, f"strip_{act.name}.png")
    contact_sheet(paths, sheet, cols=frames, cell=300)
    for p in paths:
        os.remove(p)
    return sheet


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    want = sys.argv[2:]
    s = anims.Sampler()
    for a in anims.actions():
        if want and a.name not in want:
            continue
        v, g = ("burning", "glow2") if a.id in (7, 23, 24, 25, 27) else ("base", "glow1")
        print(strip(s, a, out, variant=v, glow=g))
