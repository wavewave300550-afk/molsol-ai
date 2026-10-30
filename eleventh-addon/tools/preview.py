"""Render preview PNGs of every being (front / back / side / top)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beings  # noqa: E402
from modelkit import render_preview  # noqa: E402

VIEWS = (("front", 25, 12), ("back", 205, 18), ("side", 90, 8), ("top", 35, 60))


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, fn in beings.ALL.items():
        m = fn()
        m.paint()
        for tag, yaw, pitch in VIEWS:
            render_preview([m], os.path.join(out, f"{name}_{tag}.png"), yaw=yaw, pitch=pitch, size=640, title=f"{name} {tag}")
        st = m.stats()
        print(name, st, "glow cubes:", sum(c.glow for b in m.bones for c in b.cubes))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "previews")
