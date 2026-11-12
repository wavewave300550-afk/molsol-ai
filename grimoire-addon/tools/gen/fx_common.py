"""Constructs shared by all three Grimoires: preparation sigils and great magic circles."""
from .fxdefs import Fx
from .circles import PAINTERS
from . import circles2  # noqa: F401  (registers the expansion 02 painters)

SCH = {"pressure": "p", "ice": "i", "blood": "b", "plasma": "pl", "darkness": "d", "prism_light": "pr"}
FULL = ('rect', 0, 0, 256, 256)


def circle_fx(name, school, radius_px, variants=(0, 1, 2), lifetime=120, sparks=True):
    paths = []
    f = Fx(name, school, tex=(256, 256), bounds=(96, 48, (0, 0, 0)), lifetime=lifetime)
    for v in variants:
        rel = f"textures/entity/grimoire/{name}_v{v}"
        f.images[rel] = PAINTERS[school](256, v)
        paths.append(rel)
    f.variants = paths
    spin = f.bone("g_spin")
    spin.box((-radius_px, 0.05, -radius_px), (radius_px * 2, 0, radius_px * 2), None, faces={"up": FULL, "down": FULL})
    inner = f.bone("g_inner")
    inner.box((-radius_px * 0.55, 0.12, -radius_px * 0.55), (radius_px * 1.1, 0, radius_px * 1.1), None, faces={"up": FULL, "down": FULL})
    if sparks:
        import math
        core = ('rect', 118, 118, 20, 20)  # glowing centre of the circle art (same texture as the disc)
        for i in range(6):
            ang = math.tau * i / 6
            pb = f.bone(f"g_mote{i}", "g_spin")
            pb.cbox((math.cos(ang) * radius_px * 0.92, 0.6, math.sin(ang) * radius_px * 0.92), (1.2, 1.2, 1.2), core)
    # animations
    form = f.anim("form", length=0.6)
    form.scale("fade", {0: [0.01, 0.01, 0.01], 0.35: [1.06, 1.06, 1.06], 0.6: [1, 1, 1]})
    form.rot("g_spin", {0: [0, -120, 0], 0.6: [0, 0, 0]})
    f.phase(1, "form", "spin")
    spin_a = f.anim("spin", loop=True)
    spin_a.rot("g_spin", [0, "q.life_time * 18", 0])
    spin_a.rot("g_inner", [0, "-q.life_time * 32", 0])
    spin_a.scale("g_inner", ["1 + math.sin(q.life_time * 180) * 0.03"] * 3)
    fast = f.anim("fast", loop=True)
    fast.rot("g_spin", [0, "q.life_time * 90", 0])
    fast.rot("g_inner", [0, "-q.life_time * 140", 0])
    fast.scale("g_inner", ["1 + math.sin(q.life_time * 600) * 0.06"] * 3)
    f.phase(2, "spin")
    f.phase(3, "fast")
    pulse = f.anim("pulse", length=0.35)
    pulse.scale("fade", {0: [1, 1, 1], 0.08: [1.12, 1.12, 1.12], 0.35: [1, 1, 1]})
    f.pulse("pulse")
    dis = f.anim("dissolve", length=0.7)
    dis.scale("fade", {0: [1, 1, 1], 0.2: [1.1, 1.1, 1.1], 0.6: [0, 0, 0]})
    dis.rot("g_spin", {0: [0, 0, 0], 0.6: [0, 160, 0]})
    f.phase(15, "dissolve")
    return f


for school, s in SCH.items():
    # preparation sigil under the caster's feet (follows the player while charging)
    circle_fx(f"fx_sigil_{s}", school, 24, variants=(1,), lifetime=60)
    # great circle: variant 0 main, 1 seal, 2 sky
    circle_fx(f"fx_circle_{s}", school, 16, variants=(0, 1, 2), lifetime=120)
