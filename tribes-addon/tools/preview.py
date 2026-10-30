"""Render preview PNGs of every model (overlays are shown on a stand-in player body)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from modelkit import Model, render_preview, m_solid
import models

def steve():
    m = Model("preview.steve", seed=5)
    models.humanoid_skeleton(m)
    skin, shirt, pants = m_solid("c69c7b"), m_solid("3aa6a6"), m_solid("3b3f8f")
    m.get("head").add((-4, 24, -4), (8, 8, 8), skin)
    m.get("body").add((-4, 12, -2), (8, 12, 4), shirt)
    m.get("rightArm").add((-8, 12, -2), (4, 12, 4), skin)
    m.get("leftArm").add((4, 12, -2), (4, 12, 4), skin)
    m.get("rightLeg").add((-3.9, 0, -2), (4, 12, 4), pants)
    m.get("leftLeg").add((-0.1, 0, -2), (4, 12, 4), pants)
    return m

def main(out):
    os.makedirs(out, exist_ok=True)
    base = steve()
    for name, fn in models.ALL.items():
        m = fn()
        m.paint()
        group = [base, m] if name.startswith("overlay") else [m]
        for tag, yaw, pitch in (("front", 30, 15), ("back", 200, 20), ("side", 90, 5)):
            render_preview(group, os.path.join(out, f"{name}_{tag}.png"), yaw=yaw, pitch=pitch, title=f"{name} {tag}")
        print(name, m.stats())

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "previews")
