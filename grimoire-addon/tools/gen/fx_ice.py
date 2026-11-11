"""Ice Magic constructs: crystalline models, frozen structures, blue-white illumination.
Palette: sapphire / ice blue / cyan / silver / white."""
import math
import numpy as np
from .fxdefs import Fx
from .fxparts import oriented, ring, spin, vibrate
from .art import Art, vein_paths

I = "ice"


def hexring(f, name, parent, center, radius, thick, height, style, rx=0.0, ry=0.0):
    b = oriented(f, name, parent, center, rx, ry)
    b.ring(center, radius, thick, height, 6, style, start=30)
    return b


# ---------------------------------------------------------------------------- I01 spear + spikes
def spear():
    f = Fx("fx_i_spear", I, bounds=(10, 6, (0, 0, -1.5)))
    f.bone("shards")
    sh = oriented(f, "shaft", "shards", (0, 0, 10), rx=90)
    sh.crystal((0, 0, 10), 72, 6.5, "i_crystal", "i_crystal_glow", tip=0.3)
    guard = oriented(f, "guard", "shards", (0, 0, 2), rx=90)
    for a in (0, 90, 180, 270):
        g = oriented(f, f"gd{a}", "guard", (0, 0, 2), ry=a)
        g.cbox((0, 6, 2 - 4.5), (2, 3, 9), "i_crystal_deep", rotation=(25, 0, 0))
    core = oriented(f, "g_core", "shards", (0, 0, 8), rx=90)
    core.cbox((0, 30, 8), (1.4, 62, 1.4), "i_core")
    for i, z in enumerate((4, -14, -32)):
        f.bone(f"hx{i}", pivot=(0, 0, z))
        hexring(f, f"g_hex{i}", f"hx{i}", (0, 0, z), 9 - i * 1.4, 0.9, 1.2, "i_glow_band", rx=90)
        hexring(f, f"hs{i}", f"hx{i}", (0, 0, z + 0.4), 10 - i * 1.4, 0.6, 0.6, "i_silver", rx=90)
    form = f.anim("form", length=0.8)
    form.scale("shards", {0: [0.05, 0.05, 0.05], 0.5: [0.6, 0.6, 1.0], 0.8: [1, 1, 1]})
    for i in range(3):
        form.scale(f"hx{i}", {0: [0, 0, 0], 0.2 + 0.15 * i: [0, 0, 0], 0.45 + 0.15 * i: [1.2, 1.2, 1.2], 0.8: [1, 1, 1]})
    hold = f.anim("hold", loop=True)
    for i in range(3):
        spin(hold, f"g_hex{i}", 120 * (1 if i % 2 else -1))
        spin(hold, f"hs{i}", -60 * (1 if i % 2 else -1))
    vibrate(hold, "g_core", 0.08, 6)
    f.phase(1, "form", "hold").phase(2, "hold")
    fly = f.anim("fly", loop=True)
    for i in range(3):
        spin(fly, f"g_hex{i}", 600 * (1 if i % 2 else -1))
    f.phase(3, "fly")

    s = Fx("fx_i_spike", I, bounds=(6, 8, (0, 2, 0)))
    rng = np.random.RandomState(5)
    for k in range(6):
        a = 360 * k / 6 + rng.rand() * 30
        tilt = 18 + rng.rand() * 22
        hb = oriented(s, f"sk{k}", "fade", (0, 0, 0), rx=tilt, ry=a)
        ln = 34 + rng.rand() * 26
        hb.crystal((0, 0, 0), ln, 7 + rng.rand() * 4, "i_crystal" if k % 2 else "i_crystal_deep", "i_crystal_glow")
    s.bone("center").crystal((0, 0, 0), 56, 11, "i_crystal", "i_crystal_glow")
    s.bone("g_base").ring((0, 0.5, 0), 14, 3, 1, 8, "i_glow_band")
    rise = s.anim("rise", length=0.25)
    rise.scale("fade", {0: [0.6, 0.01, 0.6], 0.15: [1.1, 1.15, 1.1], 0.25: [1, 1, 1]})
    s.phase(1, "rise")
    sh2 = s.anim("dissolve", length=0.6)
    sh2.scale("fade", {0: [1, 1, 1], 0.1: [1.08, 0.9, 1.08], 0.5: [0.2, 0.0, 0.2]})
    s.phase(15, "dissolve")


# ---------------------------------------------------------------------------- I02 dragon head
def dragon():
    f = Fx("fx_i_dragon", I, bounds=(10, 8, (0, 1, -2)), tex=(128, 256))
    f.bone("head", pivot=(0, 16, 24))
    sk = f.bone("skull", "head", pivot=(0, 16, 24))
    sk.cbox((0, 22, 10), (24, 16, 30), "i_crystal_deep")            # cranium
    sk.cbox((0, 26, 4), (18, 6, 26), "i_crystal")                     # brow plate
    for sgn in (-1, 1):
        sk.cbox((sgn * 9, 27, -6), (5, 4, 10), "i_crystal_deep", rotation=(0, sgn * 12, 0))   # brow ridges
        sk.cbox((sgn * 12.5, 20, 12), (2, 10, 22), "i_silver")                             # cheek plates
    snout = f.bone("upper_jaw", "head", pivot=(0, 18, -4))
    snout.cbox((0, 19, -18), (16, 9, 30), "i_crystal")
    snout.cbox((0, 23, -20), (10, 3, 24), "i_crystal_deep")
    for k in range(5):
        for sgn in (-1, 1):
            snout.cbox((sgn * 6.5, 13.5, -28 + k * 6), (1.6, 5, 1.6), "i_white", rotation=(0, 45, 0))
    snout.crystal((0, 23, -32), 9, 3, "i_crystal_glow")
    jaw = f.bone("lower_jaw", "head", pivot=(0, 14, 6))
    jaw.cbox((0, 11, -14), (14, 5, 36), "i_crystal_deep")
    for k in range(5):
        for sgn in (-1, 1):
            jaw.cbox((sgn * 5.5, 15, -26 + k * 6), (1.4, 4, 1.4), "i_white", rotation=(0, 45, 0))
    eyes = f.bone("g_eyes", "head", pivot=(0, 24, 0))
    for sgn in (-1, 1):
        eyes.cbox((sgn * 8.6, 25, -2), (2.2, 2.6, 4), "i_core")
    horns = f.bone("horns", "head", pivot=(0, 28, 16))
    for i, (x, a, ln) in enumerate(((-8, -25, 40), (8, 25, 40), (-4, -12, 30), (4, 12, 30), (-11, -40, 26), (11, 40, 26))):
        hb = oriented(f, f"horn{i}", "horns", (x, 28, 18), rx=-110 + i * 4, ry=a)
        hb.crystal((x, 28, 18), ln, 5 if i < 2 else 3.6, "i_crystal", "i_crystal_glow")
    mane = f.bone("mane", "head", pivot=(0, 20, 26))
    for k in range(8):
        hb = oriented(f, f"mn{k}", "mane", (0, 18, 26), rx=-130 + k * 6, ry=-60 + k * 17)
        hb.crystal((0, 18, 26), 22 + (k % 3) * 6, 4, "i_crystal_deep", "i_crystal_glow")
    neck = f.bone("neck", pivot=(0, 14, 28))
    for k in range(3):
        neck.cbox((0, 12 - k * 4, 34 + k * 9), (18 - k * 2, 16 - k * 2, 10), "i_crystal_deep")
        neck.cbox((0, 21 - k * 4, 34 + k * 9), (4, 3, 8), "i_crystal_glow")
    f.bone("g_breath", "head", pivot=(0, 15, -30)).cbox((0, 15, -36), (6, 6, 12), "i_glow")
    rise = f.anim("form", length=0.7)
    rise.pos("fade", {0: [0, -30, 18], 0.5: [0, 3, 0], 0.7: [0, 0, 0]})
    rise.scale("fade", {0: [0.2, 0.2, 0.2], 0.5: [1.05, 1.05, 1.05], 0.7: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    idle.rot("head", ["math.sin(q.life_time * 100) * 3", "math.sin(q.life_time * 70) * 4", 0])
    idle.rot("lower_jaw", ["4 + math.sin(q.life_time * 140) * 2", 0, 0])
    idle.scale("g_breath", [0, 0, 0])
    f.phase(1, "form", "idle")
    roar = f.anim("roar", length=0.8, loop="hold_on_last_frame")
    roar.rot("lower_jaw", {0: [4, 0, 0], 0.25: [42, 0, 0], 0.8: [36, 0, 0]})
    roar.rot("upper_jaw", {0: [0, 0, 0], 0.25: [-10, 0, 0], 0.8: [-8, 0, 0]})
    roar.rot("head", {0: [0, 0, 0], 0.15: [-14, 0, 0], 0.5: [6, 0, 0], 0.8: [0, 0, 0]})
    roar.scale("g_breath", {0: [0, 0, 0], 0.3: [1, 1, 1]})
    f.phase(2, "roar")
    br = f.anim("breath", loop=True)
    br.rot("lower_jaw", ["38 + math.sin(q.life_time * 900) * 2", 0, 0])
    br.rot("upper_jaw", ["-8 + math.sin(q.life_time * 900) * 1", 0, 0])
    br.rot("head", ["math.sin(q.life_time * 600) * 1.5", "math.sin(q.life_time * 400) * 1.5", 0])
    br.scale("g_breath", ["1.2 + math.sin(q.life_time * 1200) * 0.3"] * 3)
    vibrate(br, "mane", 0.03, 10)
    f.phase(3, "breath")
    close = f.anim("close", length=0.4, loop="hold_on_last_frame")
    close.rot("lower_jaw", {0: [38, 0, 0], 0.3: [0, 0, 0]})
    close.scale("g_breath", [0, 0, 0])
    f.phase(4, "close")
    dis = f.anim("dissolve", length=0.8)
    dis.scale("fade", {0: [1, 1, 1], 0.15: [1.08, 1.08, 1.08], 0.7: [0, 0, 0]})
    dis.pos("horns", {0: [0, 0, 0], 0.6: [0, 10, 6]})
    dis.pos("lower_jaw", {0: [0, 0, 0], 0.6: [0, -8, -4]})
    f.phase(15, "dissolve")


# ---------------------------------------------------------------------------- I03 guillotine + fracture
def guillotine():
    f = Fx("fx_i_guillotine", I, bounds=(24, 10, (0, 2, 0)), tex=(128, 256))
    f.bone("drop")
    L = 300
    b = f.bone("t_blade", "drop")
    b.cbox((0, 32, 0), (3, 56, L), "i_ice")
    b.cbox((0, 8, 0), (2, 8, L - 6), "i_ice_pale")
    f.bone("g_edge", "drop").cbox((0, 3.5, 0), (1.4, 1.6, L - 2), "i_glow_band")
    sp = f.bone("spine", "drop")
    sp.cbox((0, 61, 0), (6, 6, L + 6), "i_silver")
    for k in range(9):
        z = -L / 2 + 15 + k * (L - 30) / 8
        sp.crystal((0, 63, z), 18 + (k % 2) * 10, 4.5, "i_crystal", "i_crystal_glow")
        sp.cbox((0, 46, z), (3.6, 22, 2), "i_silver_dark")
    form = f.anim("form", length=0.6)
    form.scale("drop", {0: [1, 0.05, 0.4], 0.4: [1, 1.05, 1.02], 0.6: [1, 1, 1]})
    hover = f.anim("hover", loop=True)
    hover.pos("drop", [0, "math.sin(q.life_time * 200) * 1.2", 0])
    f.phase(1, "form", "hover").phase(2, "hover")
    fall = f.anim("fall", length=0.3, loop="hold_on_last_frame")
    fall.pos("drop", {0: [0, 0, 0], 0.25: [0, "-v.len * 16 + 6", 0]})
    f.phase(3, "fall")
    imp = f.anim("impact", length=0.5, loop="hold_on_last_frame")
    imp.pos("drop", [0, "-v.len * 16 + 6", 0])
    imp.scale("t_blade", {0: [1.4, 1, 1], 0.15: [1, 1, 1]})
    f.phase(4, "impact")

    fr = Fx("fx_i_fracture", I, tex=(256, 256), bounds=(18, 4, (0, 0, 0)))
    rs = np.random.RandomState(13)
    a = Art(256, 256, ss=2)
    for pts, depth in vein_paths(rs, 256, 256, [(128, 128, rs.rand() * 6.28) for _ in range(9)], life=110, branch=0.05, wobble=0.25):
        a.line(pts, (150, 230, 255) if depth else (220, 250, 255), 1.6 if depth == 0 else 0.9)
    a.radial_glow(128, 128, 40, (90, 200, 255), 0.6)
    img = a.finish(emissive=False, alpha_from_glow=False)
    img[..., 3] = np.clip(img[..., :3].max(-1) * 1.4, 0, 255)
    rect = ('rect',) + fr.model.atlas.put_image('crack', img)
    fr.bone("g_crack").box((-96, 0.2, -96), (192, 0, 192), None, faces={"up": rect, "down": rect})
    cr = fr.bone("crystals")
    for k in range(10):
        ang = rs.rand() * math.tau
        rr = 20 + rs.rand() * 70
        hb = oriented(fr, f"fc{k}", "crystals", (math.cos(ang) * rr, 0, math.sin(ang) * rr), rx=15 + rs.rand() * 20, ry=rs.rand() * 360)
        hb.crystal((math.cos(ang) * rr, 0, math.sin(ang) * rr), 10 + rs.rand() * 12, 3.5, "i_crystal", "i_crystal_glow")
    spread = fr.anim("spread", length=0.8, loop="hold_on_last_frame")
    spread.scale("g_crack", {0: [0.05, 1, 0.05], 0.6: [1, 1, 1]})
    spread.scale("crystals", {0: [0, 0, 0], 0.3: [0, 0, 0], 0.8: [1, 1, 1]})
    fr.phase(1, "spread")


# ---------------------------------------------------------------------------- I04 sword formation + volley
def sword(b, x, y, z, s=1.0):
    b.cbox((x, y - 9 * s, z), (1.6 * s, 18 * s, 0.6 * s), "i_crystal")
    b.cbox((x, y - 19 * s, z), (0.9 * s, 3 * s, 0.5 * s), "i_crystal_glow")
    b.cbox((x, y + 0.6 * s, z), (4.6 * s, 1 * s, 1 * s), "i_silver")
    b.cbox((x, y + 3 * s, z), (0.9 * s, 4 * s, 0.9 * s), "i_silver_dark")


def swords():
    f = Fx("fx_i_swords", I, bounds=(30, 6, (0, 0, 0)), tex=(128, 128))
    rings = ((64, 18), (112, 26), (160, 34), (208, 42))
    for r, (rad, n) in enumerate(rings):
        b = f.bone(f"sr{r}")
        for k in range(n):
            a = math.tau * k / n
            sword(b, math.cos(a) * rad, 0, math.sin(a) * rad, 1.1)
        ring(f, f"g_cr{r}", f"sr{r}", (0, 10, 0), rad, 1.0, 1.0, max(18, n), "i_glow_band", gap=2)
    form = f.anim("form", length=1.0)
    for r in range(4):
        form.scale(f"sr{r}", {0: [0, 0, 0], 0.15 * r: [0, 0, 0], 0.15 * r + 0.3: [1.05, 1.05, 1.05], 0.15 * r + 0.4: [1, 1, 1]})
    hover = f.anim("hover", loop=True)
    for r in range(4):
        hover.rot(f"sr{r}", [0, f"q.life_time * {12 + r * 5} * {1 if r % 2 else -1}", 0])
    f.phase(1, "form", "hover").phase(2, "hover")
    for w in range(4):
        rel = f.anim(f"release{w}", loop="hold_on_last_frame", length=0.4)
        for r in range(4):
            if r < w:
                rel.scale(f"sr{3 - r}", [0, 0, 0])
        rel.pos(f"sr{3 - w}", {0: [0, 0, 0], 0.3: [0, -60, 0]})
        rel.scale(f"sr{3 - w}", {0: [1, 1, 1], 0.3: [1, 1.6, 1], 0.4: [0, 0, 0]})
        f.phase(3 + w, "hover", f"release{w}")

    v = Fx("fx_i_volley", I, bounds=(4, 6, (0, 1, 0)))
    b = v.bone("blades")
    for k, (x, z, y) in enumerate(((0, 0, 0), (6, 3, 8), (-6, 2, 5), (3, -6, 12), (-4, -5, 15), (1, 6, 18))):
        sword(b, x, y + 14, z, 1.15)
    v.bone("t_trail").cbox((0, 46, 0), (14, 40, 14), "i_ice_pale")
    fall = v.anim("fall", loop=True)
    fall.scale("t_trail", [1, "1.2 + math.sin(q.life_time * 2000) * 0.2", 1])
    v.phase(1, v.default_form(0.12), "fall").phase(2, "fall")


# ---------------------------------------------------------------------------- I05 lotus
def petal(f, name, parent, base, angle, tilt, length, width, style, edge):
    hb = oriented(f, name, parent, base, rx=tilt, ry=angle)
    segs = 3
    seg_l = length / segs
    p = name
    for i in range(segs):
        sb = f.model.bone(f"{name}_s{i}", p, pivot=(base[0], base[1] + seg_l * i, base[2]), rotation=(-14 if i else 0, 0, 0))
        w = width * (0.75 + 0.35 * math.sin(math.pi * (i + 0.6) / segs))
        sb.cbox((base[0], base[1] + seg_l * i + seg_l / 2, base[2]), (w, seg_l * 1.04, 0.8), style)
        sb.cbox((base[0], base[1] + seg_l * i + seg_l / 2, base[2] - 0.5), (0.6, seg_l, 0.3), edge)
        p = f"{name}_s{i}"
    return hb


def lotus():
    f = Fx("fx_i_lotus", I, bounds=(10, 6, (0, 1, 0)), tex=(128, 256))
    layers = ((8, 52, 30, 40, 70), (6, 40, 24, 30, 52), (5, 30, 18, 24, 34))   # n, length, width, radius, tilt
    for L, (n, ln, w, rad, tilt) in enumerate(layers):
        f.bone(f"layer{L}")
        for k in range(n):
            a = 360 * k / n + L * 20
            x, z = math.cos(math.radians(a)) * rad * 0.3, math.sin(math.radians(a)) * rad * 0.3
            petal(f, f"t_p{L}_{k}", f"layer{L}", (x, 2 + L * 3, z), -a + 90, tilt - L * 12, ln, w, "i_ice", "i_crystal_glow")
    core = f.bone("core")
    core.crystal((0, 4, 0), 30, 7, "i_crystal", "i_crystal_glow")
    for k in range(6):
        a = 60 * k
        hb = oriented(f, f"pist{k}", "core", (0, 6, 0), rx=24, ry=a)
        hb.crystal((0, 6, 0), 18, 3, "i_crystal_deep", "i_crystal_glow")
    f.bone("g_glow", "core").solid_cylinder((0, 6, 0), 5, 10, "i_core", layers=2)
    pads = f.bone("pads")
    for k in range(6):
        a = math.tau * k / 6
        pads.hexplate((math.cos(a) * 54, 0.6, math.sin(a) * 54), 18, 1.2, "i_frost", edge_style="i_silver")
    bloom = f.anim("bloom", length=1.0)
    for L, (n, *_rest) in enumerate(layers):
        for k in range(n):
            bloom.rot(f"t_p{L}_{k}", {0: [-60, 0, 0], 0.3 + L * 0.15: [-40, 0, 0], 0.8 + L * 0.05: [4, 0, 0], 1.0: [0, 0, 0]})
    bloom.scale("fade", {0: [0.3, 0.3, 0.3], 0.5: [1.02, 1.02, 1.02], 1.0: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    for L in range(3):
        idle.rot(f"layer{L}", [0, f"math.sin(q.life_time * 40 + {L * 60}) * 4", 0])
    spin(idle, "core", 30)
    vibrate(idle, "g_glow", 0.15, 1.2)
    f.phase(1, "bloom", "idle").phase(2, "idle")
    for k in range(3):
        b = f.anim(f"shatter{k}", length=0.4, loop="hold_on_last_frame")
        b.scale(f"layer{k}", {0: [1, 1, 1], 0.06: [1.2, 1.1, 1.2], 0.3: [0, 0, 0]})
        g = f.anim(f"gone{k}", loop=True)
        g.scale(f"layer{k}", [0, 0, 0])
    f.phase(3, "idle", "shatter0").phase(4, "idle", "gone0", "shatter1").phase(5, "idle", "gone0", "gone1", "shatter2")
    hit = f.anim("shimmer", length=0.3)
    hit.scale("g_glow", {0: [1, 1, 1], 0.06: [2.2, 2.2, 2.2], 0.3: [1, 1, 1]})
    f.pulse("shimmer")


# ---------------------------------------------------------------------------- I06/I10 mirrors
def mirror():
    f = Fx("fx_i_mirror", I, bounds=(5, 5, (0, 0, 0)))
    f.bone("frame")
    pane = oriented(f, "t_pane", "frame", (0, 0, 0), rx=90)
    pane.hexplate((0, 0, 0), 22, 1.0, "i_mirror")
    hexring(f, "rim", "frame", (0, 0, 0), 23, 2.2, 2.4, "i_silver", rx=90)
    hexring(f, "g_rim", "frame", (0, 0, 0), 20, 0.9, 2.8, "i_glow_band", rx=90)
    sp = oriented(f, "spikes", "frame", (0, 0, 0), rx=90)
    for k in range(6):
        a = 360 * k / 6 + 30
        hb = oriented(f, f"msp{k}", "spikes", (0, 0, 0), ry=-a + 90)
        hb.cbox((0, 0, -27), (2.4, 2.4, 9), "i_crystal_glow", rotation=(0, 45, 0))
    f.bone("g_runes", "frame").cbox((0, 0, -0.6), (30, 30, 0.1), "i_runes_ice", rotation=(0, 0, 0))
    form = f.anim("form", length=0.5)
    form.scale("frame", {0: [0.05, 0.05, 1], 0.35: [1.08, 1.08, 1], 0.5: [1, 1, 1]})
    form.rot("frame", {0: [0, 0, 0], 0.5: [0, 0, 0]})
    idle = f.anim("idle", loop=True)
    spin(idle, "g_rim", 60)
    idle.pos("frame", [0, "math.sin(q.life_time * 110) * 1.2", 0])
    f.phase(1, "form", "idle").phase(2, "idle")
    pul = f.anim("reflect", length=0.3)
    pul.scale("t_pane", {0: [1, 1, 1], 0.05: [1.1, 1.1, 1.1], 0.3: [1, 1, 1]})
    pul.scale("g_rim", {0: [1, 1, 1], 0.05: [1.35, 1.35, 1.35], 0.3: [1, 1, 1]})
    f.pulse("reflect")
    shat = f.anim("shatter", length=0.5, loop="hold_on_last_frame")
    shat.scale("frame", {0: [1, 1, 1], 0.08: [1.25, 1.25, 1.25], 0.4: [0, 0, 0]})
    for k in range(6):
        shat.pos(f"msp{k}", {0: [0, 0, 0], 0.4: [0, 0, -16]})
    f.phase(3, "shatter")
    port = f.anim("portal", loop=True)
    port.scale("t_pane", ["1 + math.sin(q.life_time * 900) * 0.06", "1 + math.cos(q.life_time * 900) * 0.06", 1])
    spin(port, "g_rim", 360)
    f.phase(4, "portal", "idle")


# ---------------------------------------------------------------------------- I07 chains
def chains():
    f = Fx("fx_i_chains", I, bounds=(4, 4, (0, 1, 0)))
    f.bone("strands")
    for k in range(4):
        hb = oriented(f, f"ch{k}", "strands", (0, 0, 0), rx=-12, ry=90 * k + 45)
        hb.chain((0, 0, -9), 9, 4.4, 2.6, 0.7, "i_silver")
        f.model.bone(f"chg{k}", f"ch{k}", pivot=(0, 0, 0)).chain((0, 1, -9), 9, 4.4, 2.0, 0.35, "i_crystal_glow")
    f.bone("g_ring").ring((0, 0.4, 0), 12, 1.0, 0.6, 16, "i_glow_band")
    crys = f.bone("crystals")
    for k, (y, rr) in enumerate(((4, 6), (12, 5.5), (19, 6), (25, 5), (30, 4))):
        for j in range(3):
            a = 120 * j + k * 40
            hb = oriented(f, f"cg{k}_{j}", "crystals", (0, y, 0), rx=70, ry=a)
            hb.crystal((0, y, 0), rr + 3, 2.6, "i_crystal", "i_crystal_glow")
    rise = f.anim("form", length=0.6)
    rise.scale("strands", {0: [1, 0.01, 1], 0.4: [1, 1.1, 1], 0.6: [1, 1, 1]})
    rise.scale("crystals", [0, 0, 0])
    wrap = f.anim("bind", loop="hold_on_last_frame", length=3.0)
    wrap.rot("strands", {0: [0, 0, 0], 3.0: [0, 220, 0]})
    for k in range(5):
        wrap.scale(f"cg{k}_0", {0: [0, 0, 0], 0.4 + k * 0.45: [0, 0, 0], 0.8 + k * 0.45: [1, 1, 1]})
        wrap.scale(f"cg{k}_1", {0: [0, 0, 0], 0.5 + k * 0.45: [0, 0, 0], 0.9 + k * 0.45: [1, 1, 1]})
        wrap.scale(f"cg{k}_2", {0: [0, 0, 0], 0.6 + k * 0.45: [0, 0, 0], 1.0 + k * 0.45: [1, 1, 1]})
    vibrate(wrap, "g_ring", 0.06, 6)
    f.phase(1, "form").phase(2, "bind")
    br = f.anim("break", length=0.4, loop="hold_on_last_frame")
    br.scale("fade", {0: [1, 1, 1], 0.08: [1.2, 1.05, 1.2], 0.35: [0, 0, 0]})
    f.phase(3, "break")


# ---------------------------------------------------------------------------- ice shell (freeze)
def shell():
    f = Fx("fx_i_shell", I, bounds=(3, 3, (0, 1, 0)))
    f.bone("t_block").cbox((0, 14, 0), (14, 28, 14), "i_ice_pale")
    cr = f.bone("cr")
    for k in range(8):
        a = 45 * k
        hb = oriented(f, f"sc{k}", "cr", (0, 2 + (k % 3) * 8, 0), rx=60 - (k % 2) * 20, ry=a)
        hb.crystal((0, 2 + (k % 3) * 8, 0), 12 + (k % 3) * 4, 4, "i_crystal", "i_crystal_glow")
    f.bone("g_frost").ring((0, 1, 0), 9, 2, 0.6, 10, "i_glow_band")
    form = f.anim("form", length=0.35)
    form.scale("fade", {0: [1.3, 0.05, 1.3], 0.25: [1.05, 1.08, 1.05], 0.35: [1, 1, 1]})
    f.phase(1, "form")
    sh = f.anim("shatter", length=0.4, loop="hold_on_last_frame")
    sh.scale("fade", {0: [1, 1, 1], 0.06: [1.25, 1.15, 1.25], 0.35: [0, 0, 0]})
    f.phase(3, "shatter")


# ---------------------------------------------------------------------------- towers / arch / moon / crown
def tower():
    f = Fx("fx_i_tower", I, bounds=(5, 12, (0, 3, 0)), tex=(128, 256))
    body = f.bone("body")
    body.crystal((0, 0, 0), 100, 18, "i_crystal_deep", "i_crystal", tip=0.28)
    for y in (10, 38, 66):
        body.ring((0, y, 0), 10.5, 2, 3, 6, "i_silver", start=30)
    win = f.bone("g_windows")
    for y in (24, 52):
        for a in range(0, 360, 120):
            win.cbox((math.cos(math.radians(a)) * 9.2, y, math.sin(math.radians(a)) * 9.2), (2.4, 5, 2.4), "i_core")
    sp = f.bone("spires")
    for k in range(4):
        hb = oriented(f, f"tsp{k}", "spires", (0, 60, 0), rx=24, ry=90 * k + 45)
        hb.crystal((0, 60, 0), 34, 5, "i_crystal", "i_crystal_glow")
    f.bone("g_crown").ring((0, 74, 0), 7, 1.2, 1.2, 6, "i_glow_band", start=30)
    base = f.bone("base")
    base.hexplate((0, 0.8, 0), 16, 1.6, "i_frost", edge_style="i_silver")
    rise = f.anim("form", length=1.0)
    rise.scale("fade", {0: [0.7, 0.01, 0.7], 0.7: [1.04, 1.06, 1.04], 1.0: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    spin(idle, "g_crown", 40)
    vibrate(idle, "g_windows", 0.08, 0.8)
    f.phase(1, "form", "idle").phase(2, "idle")
    fire = f.anim("fire", length=0.3)
    fire.scale("g_crown", {0: [1, 1, 1], 0.06: [2.2, 2.2, 2.2], 0.3: [1, 1, 1]})
    f.pulse("fire")
    dis = f.anim("dissolve", length=1.0)
    dis.scale("fade", {0: [1, 1, 1], 0.2: [1.04, 0.95, 1.04], 0.9: [0.6, 0.0, 0.6]})
    f.phase(15, "dissolve")

    ar = Fx("fx_i_arch", I, bounds=(8, 8, (0, 3, 0)))
    for sgn in (-1, 1):
        ar.bone(f"pillar{'l' if sgn > 0 else 'r'}").crystal((sgn * 40, 0, 0), 64, 9, "i_crystal_deep", "i_crystal")
    ring(ar, "arc", "fade", (0, 64, 0), 40, 6, 6, 12, "i_crystal", rx=90, start=180, arc=180)
    ring(ar, "g_arc", "fade", (0, 64, 0), 34, 1.2, 6.5, 12, "i_glow_band", rx=90, start=180, arc=180)
    ar.bone("key").crystal((0, 100, 0), 16, 7, "i_crystal_glow")
    ar.phase(1, ar.default_form(0.8))

    mo = Fx("fx_i_moon", I, tex=(256, 256), bounds=(30, 4, (0, 0, 0)))
    from .circles import circle_ice
    rect = ('rect',) + mo.model.atlas.put_image("moon", circle_ice(256, 1))
    mo.bone("g_disc").box((-160, 0, -160), (320, 0, 320), None, faces={"up": rect, "down": rect})
    mo.bone("g_halo").ring((0, 0, 0), 176, 4, 1, 40, "i_glow_band")
    ma = mo.anim("idle", loop=True)
    spin(ma, "g_disc", 6)
    vibrate(ma, "g_halo", 0.02, 0.3)
    mo.phase(1, mo.default_form(1.0), "idle").phase(2, "idle")


def crown():
    f = Fx("fx_i_crown", I, bounds=(14, 10, (0, 2, 0)), tex=(128, 256))
    f.bone("crown")
    f.bone("circlet", "crown").ring((0, 0, 0), 60, 6, 10, 24, "i_silver")
    f.bone("g_band", "crown").ring((0, 6, 0), 61, 1.2, 1.4, 24, "i_glow_band")
    spikes = f.bone("spikes", "crown")
    for k in range(12):
        a = math.tau * k / 12
        x, z = math.cos(a) * 58, math.sin(a) * 58
        hb = oriented(f, f"cs{k}", "spikes", (x, 4, z), rx=-8 if k % 2 else 0, ry=0)
        hb.crystal((x, 4, z), 56 if k % 2 == 0 else 34, 10 if k % 2 == 0 else 7, "i_crystal" if k % 2 else "i_crystal_deep", "i_crystal_glow")
    gems = f.bone("g_gems", "crown")
    for k in range(12):
        a = math.tau * (k + 0.5) / 12
        gems.cbox((math.cos(a) * 62.5, 2, math.sin(a) * 62.5), (4, 4, 4), "i_core", rotation=(0, 45, 0))
    for i, r in enumerate((76, 88)):
        ring(f, f"g_halo{i}", "crown", (0, 30 + i * 18, 0), r, 1.2, 1.2, 32, "i_glow_band", gap=3)
    f.bone("g_heart", "crown").crystal((0, -6, 0), 40, 14, "i_crystal_glow")
    form = f.anim("form", length=1.4)
    form.scale("crown", {0: [0.05, 0.05, 0.05], 1.0: [1.05, 1.05, 1.05], 1.4: [1, 1, 1]})
    form.pos("crown", {0: [0, 80, 0], 1.4: [0, 0, 0]})
    idle = f.anim("idle", loop=True)
    idle.rot("crown", [0, "q.life_time * 14", 0])
    spin(idle, "g_halo0", -30)
    spin(idle, "g_halo1", 24)
    idle.pos("crown", [0, "math.sin(q.life_time * 60) * 2", 0])
    f.phase(1, "form", "idle").phase(2, "idle")
    fire = f.anim("fire", length=0.35)
    fire.scale("g_heart", {0: [1, 1, 1], 0.08: [1.8, 1.8, 1.8], 0.35: [1, 1, 1]})
    f.pulse("fire")
    dis = f.anim("dissolve", length=0.9)
    dis.scale("crown", {0: [1, 1, 1], 0.15: [1.1, 1.1, 1.1], 0.8: [0, 0, 0]})
    for k in range(12):
        dis.pos(f"cs{k}", {0: [0, 0, 0], 0.8: [math.cos(math.tau * k / 12) * 40, 20, math.sin(math.tau * k / 12) * 40]})
    f.phase(15, "dissolve")


# ---------------------------------------------------------------------------- I09/I15 beam, I14 shard, I15 moon crystal
def beams():
    f = Fx("fx_i_beam", I, bounds=(6, 6, (0, 0, -2)))
    f.bone("stretch", pivot=(0, 0, 0))
    col = oriented(f, "t_col", "stretch", (0, 0, 0), rx=90)
    col.solid_cylinder((0, 0, 0), 10, 16, "i_ice_pale", layers=3)
    core = oriented(f, "g_core", "stretch", (0, 0, 0), rx=90)
    core.solid_cylinder((0, 0, 0), 4, 16, "i_core", layers=2)
    ring(f, "g_mouth", "fade", (0, 0, 0), 14, 1.4, 1.6, 12, "i_glow_band", rx=90)
    a = f.anim("pulse_loop", loop=True)
    vibrate(a, "g_core", 0.15, 12)
    spin(a, "g_mouth", 300)
    f.phase(1, f.default_form(0.15), "pulse_loop").phase(2, "pulse_loop")

    s = Fx("fx_i_shard", I, bounds=(3, 3, (0, 0, -1)))
    sb = oriented(s, "body", "fade", (0, 0, 6), rx=90)
    sb.crystal((0, 0, 6), 26, 4, "i_crystal", "i_crystal_glow", tip=0.4)
    ring(s, "g_r", "fade", (0, 0, 0), 4, 0.5, 0.8, 6, "i_glow_band", rx=90)
    s.bone("t_trail").cbox((0, 0, 16), (2, 2, 18), "i_ice_pale")
    sa = s.anim("fly", loop=True)
    spin(sa, "g_r", 900)
    s.phase(1, s.default_form(0.1), "fly").phase(2, "fly")

    m = Fx("fx_i_moon_crystal", I, bounds=(24, 30, (0, 0, 0)), tex=(128, 256))
    m.bone("drop")
    body = m.bone("t_body", "drop")
    for a in (0, 60, 120):
        body.cbox((0, 0, 0), (224, 150, 128), "i_ice", rotation=(0, a, 0))
    up = m.bone("tipup", "drop")
    up.crystal((0, 70, 0), 150, 150, "i_crystal_deep", "i_crystal", tip=0.9)
    dn = oriented(m, "tipdn", "drop", (0, -70, 0), rx=180)
    dn.crystal((0, -70, 0), 150, 150, "i_crystal_deep", "i_crystal", tip=0.9)
    m.bone("g_heart", "drop").solid_cylinder((0, -40, 0), 40, 80, "i_core", layers=3)
    ring(m, "g_belt", "drop", (0, 0, 0), 136, 3, 6, 6, "i_glow_band", start=30)
    form = m.anim("form", length=2.0)
    form.scale("drop", {0: [0.02, 0.02, 0.02], 1.6: [1.03, 1.03, 1.03], 2.0: [1, 1, 1]})
    idle = m.anim("idle", loop=True)
    idle.rot("drop", [0, "q.life_time * 10", 0])
    vibrate(idle, "g_heart", 0.08, 1.5)
    m.phase(1, "form", "idle").phase(2, "idle")
    desc = m.anim("descend", loop="hold_on_last_frame", length=2.2)
    desc.pos("drop", {0: [0, 0, 0], 2.0: [0, "-v.len * 16", 0]})
    desc.rot("drop", [0, "q.life_time * 40", 0])
    m.phase(3, "descend")
    sh = m.anim("shatter", length=0.6, loop="hold_on_last_frame")
    sh.pos("drop", [0, "-v.len * 16", 0])
    sh.scale("drop", {0: [1, 1, 1], 0.1: [1.3, 0.8, 1.3], 0.5: [0, 0, 0]})
    m.phase(4, "shatter")


# ---------------------------------------------------------------------------- I11 seraph wings
def wings():
    f = Fx("fx_i_wings", I, bounds=(8, 6, (0, 1.5, 0.4)), tex=(128, 256))
    f.bone("wings", pivot=(0, 22, 3))
    pairs = ((26, 30, 13), (18, 24, 10), (8, 18, 8))   # root height, span per segment, feather length
    for pi, (ry0, seg, fl) in enumerate(pairs):
        for side in (1, -1):
            nm = f"w{pi}{'l' if side > 0 else 'r'}"
            root = f.model.bone(nm, "wings", pivot=(side * 3, ry0, 3))
            prev = nm
            x0 = side * 3
            for s in range(4):
                sx = x0 + side * seg * s * 0.62
                sb = f.model.bone(f"{nm}_s{s}", prev, pivot=(sx, ry0 + s * (4 - pi * 1.2), 4))
                L = seg * (0.62 if s < 3 else 0.7)
                cx = sx + side * L / 2
                sb.cbox((cx, ry0 + s * (4 - pi * 1.2), 4), (L, 2.2, 2.2), "i_silver")
                for k in range(3):
                    fx_ = sx + side * L * (0.2 + 0.3 * k)
                    fb = f.model.bone(f"t_{nm}_f{s}{k}", f"{nm}_s{s}", pivot=(fx_, ry0 + s * (4 - pi * 1.2), 4), rotation=(0, side * (8 + k * 6), 0))
                    ln = fl * (1.2 - 0.1 * s) * (1 + 0.15 * k)
                    fb.cbox((fx_, ry0 + s * (4 - pi * 1.2) - ln / 2, 4.5), (3.4, ln, 0.8), "i_ice")
                    fb.cbox((fx_, ry0 + s * (4 - pi * 1.2) - ln - 1.2, 4.5), (1.6, 2.4, 0.7), "i_crystal_glow")
                prev = f"{nm}_s{s}"
            gl = f.model.bone(f"g_{nm}_glow", nm, pivot=(side * 3, ry0, 3))
            gl.cbox((side * (3 + seg * 1.1), ry0 + 4, 4), (seg * 2.2, 0.6, 0.6), "i_glow_band")
    f.bone("g_halo", pivot=(0, 34, 6)).ring((0, 34, 6), 7, 0.7, 0.7, 12, "i_glow_band")
    names = [f"w{pi}{c}" for pi in range(3) for c in "lr"]
    opening = f.anim("form", length=0.9)
    for nm in names:
        side = 1 if nm.endswith("l") else -1
        opening.rot(nm, {0: [20, -side * 75, 0], 0.6: [-6, side * 4, 0], 0.9: [0, 0, 0]})
    fly = f.anim("fly", loop=True)
    for pi in range(3):
        for c in "lr":
            nm = f"w{pi}{c}"
            side = 1 if c == "l" else -1
            amp = 22 - pi * 4
            ph = pi * 40
            # flap: mirrored Z rotations (symmetric regardless of axis sign), segments lag behind
            # banking: same Y sign on both sides sweeps one wing forward and the other back
            fly.rot(nm, [f"math.sin(q.life_time * 260 + {ph}) * 6", "(v.len - 1) * 30", f"{side} * math.sin(q.life_time * 260 + {ph}) * {amp}"])
            for s in range(4):
                fly.rot(f"{nm}_s{s}", [0, 0, f"{side} * math.sin(q.life_time * 260 + {ph + 30 * (s + 1)}) * {6 + s * 2}"])
    spin(fly, "g_halo", 90)
    f.phase(1, "form", "fly").phase(2, "fly")
    close = f.anim("close", length=0.6, loop="hold_on_last_frame")
    for nm in names:
        side = 1 if nm.endswith("l") else -1
        close.rot(nm, {0: [0, 0, 0], 0.5: [20, -side * 75, 0]})
    f.phase(3, "close")


# ---------------------------------------------------------------------------- I13 hourglass
def hourglass():
    f = Fx("fx_i_hourglass", I, bounds=(6, 8, (0, 0, 0)), tex=(128, 256))
    fr = f.bone("frame")
    fr.hexplate((0, 46, 0), 26, 4, "i_silver", edge_style="i_silver_dark")
    fr.hexplate((0, -46, 0), 26, 4, "i_silver", edge_style="i_silver_dark")
    for k in range(6):
        a = math.tau * k / 6 + math.pi / 6
        x, z = math.cos(a) * 22, math.sin(a) * 22
        fr.cbox((x, 0, z), (2.4, 88, 2.4), "i_silver")
        for y in (-30, -10, 10, 30):
            fr.cbox((x, y, z), (3.6, 2, 3.6), "i_silver_dark", rotation=(0, 45, 0))
    for k in range(6):
        a = math.tau * k / 6 + math.pi / 6
        fr.crystal((math.cos(a) * 24, 48, math.sin(a) * 24), 12, 3, "i_crystal_glow")
    bulb_up = oriented(f, "t_bulbu", "fade", (0, 2, 0), rx=180)
    bulb_up.cone((0, 2, 0), 18, 42, 6, "i_glass")
    f.bone("t_bulbd").cone((0, -42, 0), 18, 42, 6, "i_glass")
    sand_u = f.model.bone("sandu", "fade", pivot=(0, 2, 0))
    sb = oriented(f, "g_sandu", "sandu", (0, 2, 0), rx=180)
    sb.cone((0, 2, 0), 14, 30, 5, "i_glow")
    sand_d = f.model.bone("sandd", "fade", pivot=(0, -42, 0))
    f.model.bone("g_sandd", "sandd", pivot=(0, -42, 0)).cone((0, -42, 0), 14, 26, 5, "i_glow")
    f.bone("g_stream").cbox((0, -20, 0), (1.2, 44, 1.2), "i_core")
    form = f.anim("form", length=0.8)
    form.scale("fade", {0: [0.05, 0.05, 0.05], 0.6: [1.04, 1.04, 1.04], 0.8: [1, 1, 1]})
    form.scale("sandd", [1, 0.05, 1])
    form.scale("g_stream", [0, 0, 0])
    f.phase(1, "form")
    cnt = f.anim("countdown", loop="hold_on_last_frame", length=4.0)
    cnt.scale("sandu", {0: [1, 1, 1], 4.0: [0.05, 0.05, 0.05]})
    cnt.scale("sandd", {0: [1, 0.05, 1], 4.0: [1, 1, 1]})
    cnt.scale("g_stream", ["1 + math.sin(q.life_time * 2000) * 0.2", 1, 1])
    cnt.rot("frame", [0, "q.anim_time * 20", 0])
    f.phase(2, "countdown")
    burst = f.anim("burst", length=0.6, loop="hold_on_last_frame")
    burst.scale("fade", {0: [1, 1, 1], 0.1: [1.3, 1.3, 1.3], 0.5: [0, 0, 0]})
    f.phase(3, "burst")


for build in (spear, dragon, guillotine, swords, lotus, mirror, chains, shell, tower, crown, beams, wings, hourglass):
    build()
