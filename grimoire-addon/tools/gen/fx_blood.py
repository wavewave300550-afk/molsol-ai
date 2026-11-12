"""Blood Magic constructs: magically generated blood, crimson crystal constructs, gothic geometry.
Palette: dark burgundy / crimson / scarlet / glowing red / blackened silver."""
import math
import numpy as np
from .fxdefs import Fx
from .fxparts import oriented, ring, spin, vibrate
from .fx_ice import petal
from .art import Art, vein_paths
from . import book as BOOK

B = "blood"


def stiletto(b, x, y, z, s=1.0):
    """Slender blade pointing forward (-Z) with silver crossguard and ruby pommel."""
    b.cbox((x, y, z - 7 * s), (0.9 * s, 0.9 * s, 14 * s), "b_crystal_glow")
    b.cbox((x, y, z - 14.6 * s), (0.5 * s, 0.5 * s, 2 * s), "b_ruby")
    b.cbox((x, y, z + 0.4 * s), (3.4 * s, 0.7 * s, 0.7 * s), "b_silver_light")
    b.cbox((x, y, z + 2.2 * s), (0.8 * s, 0.8 * s, 3 * s), "b_silver")
    b.cbox((x, y, z + 4 * s), (1.2 * s, 1.2 * s, 1.2 * s), "b_ruby")


# ---------------------------------------------------------------------------- B01
def stilettos():
    f = Fx("fx_b_stilettos", B, bounds=(8, 8, (0, 1.5, 0)))
    for r, (rad, n) in enumerate(((10, 8), (19, 12), (28, 16))):
        rb = oriented(f, f"sr{r}", "fade", (0, 24, 6), rx=90)
        for k in range(n):
            a = math.tau * k / n
            hb = oriented(f, f"st{r}_{k}", f"sr{r}", (math.cos(a) * rad, 24, 6 + math.sin(a) * rad), rx=-90)
            stiletto(hb, math.cos(a) * rad, 24, 6 + math.sin(a) * rad, 1.0)
        ring(f, f"g_rr{r}", f"sr{r}", (0, 24, 6), rad, 0.5, 0.5, max(12, n * 2), "b_glow_band", gap=3)
    form = f.anim("form", length=0.8)
    for r in range(3):
        form.scale(f"sr{r}", {0: [0, 0, 0], 0.15 * r: [0, 0, 0], 0.15 * r + 0.35: [1.1, 1.1, 1.1], 0.15 * r + 0.45: [1, 1, 1]})
    hold = f.anim("hold", loop=True)
    for r in range(3):
        spin(hold, f"sr{r}", 50 * (1 if r % 2 else -1))
    f.phase(1, "form", "hold").phase(2, "hold")
    for w in range(3):
        rel = f.anim(f"volley{w}", loop="hold_on_last_frame", length=0.3)
        for r in range(w):
            rel.scale(f"sr{r}", [0, 0, 0])
        rel.scale(f"sr{w}", {0: [1, 1, 1], 0.2: [0, 0, 0]})
        f.phase(3 + w, "hold", f"volley{w}")

    v = Fx("fx_b_stiletto", B, bounds=(3, 3, (0, 0, -0.5)))
    vb = v.bone("blades")
    for (x, y) in ((0, 0), (2.2, 1.4), (-2.2, 1.4), (0, -2.2)):
        stiletto(vb, x, y, 0, 1.1)
    v.bone("t_trail").cbox((0, 0, 14), (1.2, 1.2, 20), "b_liquid_thin")
    fl = v.anim("fly", loop=True)
    fl.rot("blades", [0, 0, "q.life_time * 720"])
    v.phase(1, v.default_form(0.1), "fly").phase(2, "fly")


# ---------------------------------------------------------------------------- B02
def guillotine():
    f = Fx("fx_b_guillotine", B, bounds=(10, 14, (0, 3, 0)), tex=(128, 256))
    fr = f.bone("frame")
    for sgn in (-1, 1):
        fr.cbox((sgn * 44, 60, 0), (6, 120, 6), "b_silver")
        fr.cbox((sgn * 44, 60, 0), (8, 6, 8), "b_silver_light")
        fr.crystal((sgn * 44, 120, 0), 26, 7, "b_silver", "b_ruby")
        for y in (20, 50, 80, 110):
            fr.cbox((sgn * 44, y, 0), (7.6, 2, 7.6), "b_silver_light")
    ring(f, "arch", "frame", (0, 116, 0), 44, 4, 5, 14, "b_silver", rx=90, start=0, arc=180)
    ring(f, "g_arch", "frame", (0, 116, 0), 40, 1.0, 5.5, 14, "b_glow_band", rx=90, start=0, arc=180)
    fr.cbox((0, 118, 0), (94, 6, 6), "b_silver")
    for sgn in (-1, 1):
        ring(f, f"wheel{'l' if sgn > 0 else 'r'}", "frame", (sgn * 18, 118, -4), 6, 1.2, 1.6, 10, "b_silver_light", rx=90)
    fr.crystal((0, 146, 0), 22, 9, "b_ruby", "b_ruby")
    th = f.bone("g_threads")
    for k in range(9):
        x = -32 + k * 8
        th.cbox((x, 99, 0), (0.5, 38, 0.5), "b_glow_vband")
    f.bone("drop")
    blade = f.bone("blade", "drop", pivot=(0, 76, 0))
    blade.cbox((0, 72, 0), (80, 16, 2.4), "b_crystal")
    blade.cbox((0, 82, 0), (84, 4, 3.2), "b_silver")
    f.bone("t_bladeliquid", "drop").cbox((0, 70, 0), (78, 12, 3.4), "b_liquid")
    edge = oriented(f, "g_edge", "drop", (0, 70, 0), rx=90)
    edge.ring((0, 70, 0), 46, 1.4, 3.6, 12, "b_glow_band", start=35, arc=110)
    veins = f.bone("g_veins", "drop")
    for k in range(5):
        veins.cbox((-30 + k * 15, 74, -1.4), (0.5, 10, 0.4), "b_glow_vband")
    form = f.anim("form", length=0.8)
    form.scale("frame", {0: [1, 0.01, 1], 0.6: [1, 1.05, 1], 0.8: [1, 1, 1]})
    form.scale("blade", [0, 0, 0])
    form.scale("t_bladeliquid", [0, 0, 0])
    form.scale("g_edge", [0, 0, 0])
    form.scale("g_threads", [1, 0.01, 1])
    f.phase(1, "form")
    weave = f.anim("weave", length=1.4, loop="hold_on_last_frame")
    weave.scale("g_threads", {0: [1, 0.01, 1], 0.6: [1, 1, 1]})
    weave.scale("blade", {0: [0.05, 0.05, 0.05], 0.5: [0.05, 0.3, 0.05], 1.2: [1.04, 1.04, 1.04], 1.4: [1, 1, 1]})
    weave.scale("t_bladeliquid", {0: [0, 0, 0], 0.7: [0.5, 0.5, 0.5], 1.3: [1, 1, 1]})
    weave.scale("g_edge", {0: [0, 0, 0], 1.0: [0, 0, 0], 1.4: [1, 1, 1]})
    spin(weave, "wheell", 90)
    spin(weave, "wheelr", -90)
    f.phase(2, "weave")
    fall = f.anim("fall", length=0.3, loop="hold_on_last_frame")
    fall.pos("drop", {0: [0, 0, 0], 0.22: [0, "-v.len * 16 + 70", 0]})
    fall.scale("g_threads", {0: [1, 1, 1], 0.05: [1, 0.01, 1]})
    f.phase(3, "fall")
    imp = f.anim("impact", length=0.5, loop="hold_on_last_frame")
    imp.pos("drop", [0, "-v.len * 16 + 70", 0])
    imp.scale("drop", {0: [1, 1, 1], 0.1: [1.15, 0.8, 1.15], 0.5: [0.0, 0.0, 0.0]})
    f.phase(4, "impact")

    cr = Fx("fx_b_crescent", B, bounds=(5, 2, (0, 0, -1)))
    cr.bone("t_body").ring((0, 0, 0), 22, 6, 1.2, 10, "b_liquid", start=-150, arc=120)
    cr.bone("g_edge").ring((0, 0, 0), 25.5, 1.2, 1.4, 12, "b_glow_band", start=-155, arc=130)
    ca = cr.anim("fly", loop=True)
    vibrate(ca, "g_edge", 0.04, 9)
    cr.phase(1, cr.default_form(0.12), "fly").phase(2, "fly")


# ---------------------------------------------------------------------------- B03 leviathan
def leviathan():
    h = Fx("fx_b_serpent_head", B, bounds=(5, 4, (0, 0.5, -1)), tex=(128, 256))
    h.bone("head", pivot=(0, 8, 10))
    sk = h.bone("skull", "head", pivot=(0, 8, 10))
    sk.cbox((0, 10, 4), (18, 12, 20), "b_scales")
    sk.cbox((0, 15, 2), (12, 4, 16), "b_crystal")
    for sgn in (-1, 1):
        sk.cbox((sgn * 9.5, 9, 6), (1.6, 8, 14), "b_silver")
        fin = oriented(h, f"fin{'l' if sgn > 0 else 'r'}", "head", (sgn * 8, 14, 12), rx=-120, ry=sgn * 35)
        fin.crystal((sgn * 8, 14, 12), 18, 4, "b_thorn", "b_ruby")
    crest = h.bone("crest", "head", pivot=(0, 16, 12))
    for k in range(4):
        hb = oriented(h, f"cr{k}", "crest", (0, 16, 6 + k * 4), rx=-100 - k * 8)
        hb.crystal((0, 16, 6 + k * 4), 12 - k * 2, 3, "b_thorn", "b_ruby")
    up = h.bone("upper_jaw", "head", pivot=(0, 9, -4))
    up.cbox((0, 10, -13), (12, 7, 20), "b_scales")
    for k in range(4):
        for sgn in (-1, 1):
            up.cbox((sgn * 4.6, 5.8, -20 + k * 4.5), (1.2, 3.6, 1.2), "b_bone", rotation=(0, 45, 0))
    lo = h.bone("lower_jaw", "head", pivot=(0, 6, 2))
    lo.cbox((0, 4.5, -10), (10, 4, 22), "b_crystal")
    for k in range(4):
        for sgn in (-1, 1):
            lo.cbox((sgn * 3.6, 7.6, -18 + k * 4.5), (1.0, 3, 1.0), "b_bone", rotation=(0, 45, 0))
    h.bone("g_eyes", "head", pivot=(0, 13, -2)).cbox((0, 13, -2), (14, 2, 2.4), "b_core")
    h.bone("t_drip", "head").cbox((0, 2, -8), (8, 4, 14), "b_liquid_thin")
    swim = h.anim("swim", loop=True)
    swim.rot("head", ["math.sin(q.life_time * 220) * 6", "math.sin(q.life_time * 160) * 10", 0])
    swim.rot("lower_jaw", ["10 + math.sin(q.life_time * 300) * 6", 0, 0])
    vibrate(swim, "crest", 0.04, 5)
    h.phase(1, h.default_form(0.3), "swim").phase(2, "swim")
    bite = h.anim("bite", length=0.6, loop="hold_on_last_frame")
    bite.rot("lower_jaw", {0: [10, 0, 0], 0.2: [55, 0, 0], 0.35: [0, 0, 0], 0.6: [8, 0, 0]})
    bite.rot("upper_jaw", {0: [0, 0, 0], 0.2: [-20, 0, 0], 0.35: [0, 0, 0]})
    bite.rot("head", {0: [0, 0, 0], 0.2: [-25, 0, 0], 0.35: [15, 0, 0], 0.6: [0, 0, 0]})
    h.phase(3, "bite")

    s = Fx("fx_b_serpent_seg", B, bounds=(4, 4, (0, 0.4, 0)))
    # horizontal tube along the direction of travel (model forward is -Z)
    oriented(s, "t_body", s.top, (0, 8, 0), rx=90).solid_cylinder((0, 0.5, 0), 8.5, 15, "b_liquid", layers=3)
    oriented(s, "core", s.top, (0, 8, 0), rx=90).solid_cylinder((0, 2.5, 0), 5, 11, "b_crystal", layers=2)
    sc = s.bone("scales")
    for k in range(3):                                               # dorsal scale plates
        sc.cbox((0, 15.4 - abs(k - 1) * 0.5, -5 + k * 5), (9 - abs(k - 1) * 2, 1.4, 5.4), "b_scales", rotation=(-10, 0, 0))
    oriented(s, "dorsal", s.top, (0, 15.5, 1), rx=-38).crystal((0, 15.5, 1), 9, 2.6, "b_thorn", "b_ruby")
    for sgn in (-1, 1):                                              # lateral arteries
        s.bone(f"g_vein_{'l' if sgn > 0 else 'r'}").cbox((sgn * 8.2, 8, 0), (0.4, 1.2, 15), "b_glow_band")
    s.bone("t_belly").cbox((0, 1.4, 0), (8, 1.2, 14), "b_liquid_thin")
    sa = s.anim("pulse_loop", loop=True)
    vibrate(sa, "t_body", 0.05, 2.5)
    sa.scale("core", ["1 + math.sin(q.life_time * 400) * 0.06"] * 3)
    s.phase(1, s.default_form(0.2), "pulse_loop").phase(2, "pulse_loop")

    t = Fx("fx_b_serpent_tail", B, bounds=(4, 3, (0, 0.3, 0)))
    t.bone("tail", pivot=(0, 8, -6))
    for k in range(4):                                               # tapering tube toward +Z (behind)
        r, z = 8 - k * 1.7, k * 5
        oriented(t, f"t_tail{k}", "tail", (0, 8, z), rx=90).solid_cylinder((0, 5, z), r, 6, "b_liquid", layers=2)
        t.bone(f"g_tv{k}", "tail").cbox((0, 8 + r * 0.72, z), (0.5, 0.5, 5.2), "b_glow_band")
    for j, ry in enumerate((-28, 0, 28)):                            # crystal fin fan trailing behind
        oriented(t, f"tfin{j}", "tail", (0, 8, 18), rx=-72, ry=ry).cbox((0, 8 + 8, 18), (0.8, 16 - abs(j - 1) * 3, 4.5 - abs(j - 1)), "b_crystal_glow")
    ta = t.anim("whip", loop=True)
    ta.rot("tail", [0, "math.sin(q.life_time * 300) * 25", 0])
    t.phase(1, t.default_form(0.2), "whip").phase(2, "whip")


# ---------------------------------------------------------------------------- B04 crowns
def crowns():
    f = Fx("fx_b_crown", B, bounds=(4, 3, (0, 0.8, 0)))
    f.bone("crown")
    f.bone("band", "crown").ring((0, 0, 0), 12, 2.2, 4, 12, "b_silver")
    pts = f.bone("points", "crown")
    for k in range(8):
        a = math.tau * k / 8
        pts.crystal((math.cos(a) * 12, 2, math.sin(a) * 12), 9 if k % 2 == 0 else 6, 2.6, "b_crystal", "b_ruby")
    f.bone("g_gems", "crown").ring((0, 0.5, 0), 12.8, 1.2, 1.4, 8, "b_core", gap=26)
    bl = f.bone("blades", "crown")
    for k in range(6):
        a = math.tau * k / 6
        hb = oriented(f, f"cb{k}", "blades", (0, -3, 0), ry=k * 60)
        hb.cbox((0, -3, -11), (1.2, 0.6, 12), "b_crystal_glow")
        hb.cbox((0, -3, -17.5), (2.6, 0.5, 2), "b_ruby")
    f.bone("g_ring", "crown").ring((0, -3, 0), 16, 0.5, 0.5, 18, "b_glow_band")
    idle = f.anim("idle", loop=True)
    spin(idle, "blades", 360)
    idle.pos("crown", [0, "math.sin(q.life_time * 180) * 1", 0])
    idle.rot("crown", [0, "q.life_time * 40", 0])
    f.phase(1, f.default_form(0.3), "idle").phase(2, "idle")
    sl = f.anim("slash", length=0.35)
    sl.scale("blades", {0: [1, 1, 1], 0.08: [1.8, 1, 1.8], 0.35: [1, 1, 1]})
    sl.scale("g_ring", {0: [1, 1, 1], 0.08: [2, 1, 2], 0.35: [1, 1, 1]})
    f.pulse("slash")

    g = Fx("fx_b_grand_crown", B, bounds=(12, 10, (0, 2, 0)), tex=(128, 256))
    g.bone("crown")
    g.bone("band", "crown").ring((0, 0, 0), 44, 6, 12, 20, "b_silver")
    g.bone("band2", "crown").ring((0, 7, 0), 46, 2, 2, 20, "b_silver_light")
    gp = g.bone("points", "crown")
    for k in range(16):
        a = math.tau * k / 16
        gp.crystal((math.cos(a) * 44, 6, math.sin(a) * 44), 30 if k % 2 == 0 else 18, 7, "b_crystal", "b_ruby")
    for i, ry in enumerate((0, 90)):
        ring(g, f"arch{i}", "crown", (0, 6, 0), 44, 3, 4, 14, "b_silver", rx=90, ry=ry, start=0, arc=180)
    g.bone("orb", "crown").solid_cylinder((0, 50, 0), 6, 10, "b_ruby", layers=3)
    g.bone("cross", "crown").cbox((0, 64, 0), (2.5, 14, 2.5), "b_silver_light")
    g.model.by_name["cross"].cbox((0, 66, 0), (9, 2.5, 2.5), "b_silver_light")
    gb = g.bone("blades", "crown")
    for k in range(12):
        hb = oriented(g, f"gb{k}", "blades", (0, -8, 0), ry=k * 30)
        hb.cbox((0, -8, -46), (3, 1.4, 40), "b_crystal_glow")
    g.bone("g_core", "crown").solid_cylinder((0, -4, 0), 16, 6, "b_core", layers=3)
    form = g.anim("form", length=1.0)
    form.scale("crown", {0: [0.05, 0.05, 0.05], 0.7: [1.08, 1.08, 1.08], 1.0: [1, 1, 1]})
    form.rot("crown", {0: [0, -180, 0], 1.0: [0, 0, 0]})
    gi = g.anim("idle", loop=True)
    spin(gi, "blades", 180)
    gi.rot("crown", [0, "q.life_time * 20", 0])
    g.phase(1, "form", "idle").phase(2, "idle")
    strike = g.anim("strike", length=0.6, loop="hold_on_last_frame")
    strike.pos("crown", {0: [0, 0, 0], 0.1: [0, 10, 0], 0.3: [0, "-v.len * 16", 0]})
    strike.scale("blades", {0: [1, 1, 1], 0.3: [1.5, 1, 1.5], 0.6: [1.5, 1, 1.5]})
    g.phase(3, "strike")


# ---------------------------------------------------------------------------- B05 rose aegis
def rose_aegis():
    f = Fx("fx_b_rose_aegis", B, bounds=(9, 6, (0, 1.5, 0)), tex=(128, 256))
    layers = ((10, 46, 32, 30, 66, "b_petal_dark"), (8, 38, 28, 22, 50, "b_petal"), (6, 30, 22, 14, 34, "b_petal_bright"))
    for L, (n, ln, w, rad, tilt, st) in enumerate(layers):
        f.bone(f"layer{L}")
        for k in range(n):
            a = 360 * k / n + L * 17
            x, z = math.cos(math.radians(a)) * rad * 0.35, math.sin(math.radians(a)) * rad * 0.35
            petal(f, f"pt{L}_{k}", f"layer{L}", (x, 1 + L * 3, z), -a + 90, tilt - L * 10, ln, w, st, "b_glow_band")
    stem = f.bone("thornring")
    for k in range(12):
        a = 30 * k
        hb = oriented(f, f"th{k}", "thornring", (0, 0, 0), rx=60, ry=a)
        hb.crystal((0, 0, 0), 22 + (k % 3) * 6, 3, "b_thorn", "b_ruby")
    fl = f.bone("float")
    for k in range(8):
        a = math.tau * k / 8
        hb = oriented(f, f"fp{k}", "float", (math.cos(a) * 40, 30 + (k % 3) * 8, math.sin(a) * 40), rx=40, ry=k * 45)
        hb.cbox((math.cos(a) * 40, 34 + (k % 3) * 8, math.sin(a) * 40), (6, 8, 0.6), "b_petal")
    f.bone("g_core").solid_cylinder((0, 2, 0), 6, 10, "b_core", layers=2)
    bloom = f.anim("bloom", length=1.0)
    for L, (n, *_r) in enumerate(layers):
        for k in range(n):
            bloom.rot(f"pt{L}_{k}", {0: [-60, 0, 0], 0.3 + L * 0.12: [-35, 0, 0], 0.85: [5, 0, 0], 1.0: [0, 0, 0]})
    bloom.scale("fade", {0: [0.3, 0.3, 0.3], 0.6: [1.03, 1.03, 1.03], 1.0: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    for L in range(3):
        idle.rot(f"layer{L}", [0, f"q.life_time * {(8 + L * 5) * (1 if L % 2 else -1)}", 0])
    idle.rot("float", [0, "q.life_time * 40", 0])
    vibrate(idle, "g_core", 0.2, 1.3)
    f.phase(1, "bloom", "idle").phase(2, "idle")
    for k in range(3):
        b = f.anim(f"shatter{k}", length=0.4, loop="hold_on_last_frame")
        b.scale(f"layer{k}", {0: [1, 1, 1], 0.06: [1.15, 1.1, 1.15], 0.3: [0, 0, 0]})
        gg = f.anim(f"gone{k}", loop=True)
        gg.scale(f"layer{k}", [0, 0, 0])
    f.phase(3, "idle", "shatter0").phase(4, "idle", "gone0", "shatter1").phase(5, "idle", "gone0", "gone1", "shatter2")
    hit = f.anim("absorb", length=0.3)
    hit.scale("g_core", {0: [1, 1, 1], 0.06: [2.5, 2.5, 2.5], 0.3: [1, 1, 1]})
    f.pulse("absorb")


# ---------------------------------------------------------------------------- B06 fan shield + lances
def fan():
    f = Fx("fx_b_fan", B, bounds=(6, 5, (0, 1.5, -0.5)))
    f.bone("fan", pivot=(0, 6, -10))
    pan = oriented(f, "panels", "fan", (0, 6, -10), rx=90)
    for k in range(12):
        a = -80 + k * (160 / 11)
        hb = oriented(f, f"fp{k}", "panels", (0, 6, -10), ry=a)
        hb.cbox((0, 6, -10 + 18), (7, 1.2, 34), "b_crystal")
        hb.cbox((0, 6.8, -10 + 18), (0.8, 0.6, 34), "b_silver")
        f.model.bone(f"g_fv{k}", f"fp{k}", pivot=(0, 6, -10)).cbox((1.6, 6.9, -10 + 14), (0.5, 0.4, 22), "b_glow_band")
    ring(f, "rim", "fan", (0, 6, -10), 36, 2, 2.4, 14, "b_silver", rx=90, start=10, arc=160)
    f.bone("hub", "fan", pivot=(0, 6, -10)).solid_cylinder((0, 4, -10), 4, 4, "b_ruby", layers=3)
    open_ = f.anim("form", length=0.6)
    for k in range(12):
        open_.rot(f"fp{k}", {0: [0, -(-80 + k * (160 / 11)), 0], 0.5: [0, 0, 0]})
    f.phase(1, "form")
    idle = f.anim("idle", loop=True)
    idle.pos("fan", [0, "math.sin(q.life_time * 100) * 0.6", 0])
    for k in range(12):
        vibrate(idle, f"g_fv{k}", 0.1, 1.5, k * 30)
    f.phase(2, "idle")
    comp = f.anim("compress", length=0.5)
    comp.scale("fan", {0: [1, 1, 1], 0.08: [0.85, 0.85, 0.85], 0.25: [1.12, 1.12, 1.12], 0.5: [1, 1, 1]})
    f.pulse("compress")

    l = Fx("fx_b_lance", B, bounds=(3, 3, (0, 0, -1)))
    lb = oriented(l, "body", "fade", (0, 0, 10), rx=90)
    lb.crystal((0, 0, 10), 36, 2.6, "b_crystal", "b_ruby", tip=0.3)
    rib = l.bone("t_spiral")
    for k in range(6):
        rib.cbox((math.cos(k) * 1.8, math.sin(k) * 1.8, 4 - k * 5), (1.2, 1.2, 5), "b_liquid")
    l.bone("t_trail").cbox((0, 0, 16), (1.4, 1.4, 16), "b_liquid_thin")
    la = l.anim("fly", loop=True)
    la.rot("t_spiral", [0, 0, "q.life_time * 900"])
    l.phase(1, l.default_form(0.1), "fly").phase(2, "fly")


# ---------------------------------------------------------------------------- B07/B13 threads, sigils
def threads():
    t = Fx("fx_b_thread", B, bounds=(2, 2, (0, 0, -1)))
    t.bone("stretch", pivot=(0, 0, 0))
    t.model.bone("g_line", "stretch", pivot=(0, 0, 0)).cbox((0, 0, -8), (0.4, 0.4, 16), "b_glow_band")
    t.model.bone("t_sheath", "stretch", pivot=(0, 0, 0)).cbox((0, 0, -8), (0.9, 0.9, 16), "b_liquid_thin")
    t.bone("g_hook").cbox((0, 0, 0), (1.6, 1.6, 1.6), "b_core", rotation=(0, 45, 0))
    ta = t.anim("tension", loop=True)
    ta.scale("g_line", ["1 + math.sin(q.life_time * 2400) * 0.4", "1 + math.cos(q.life_time * 2100) * 0.4", 1])
    t.phase(1, t.default_form(0.15), "tension").phase(2, "tension")
    tp = t.anim("pulse", length=0.4)
    tp.scale("t_sheath", {0: [1, 1, 1], 0.1: [3, 3, 1], 0.4: [1, 1, 1]})
    t.pulse("pulse")

    h = Fx("fx_b_heart_sigil", B, bounds=(2, 2, (0, 0.5, 0)), tex=(64, 64))
    a = Art(64, 64, ss=4)
    a.circle(32, 32, 29, outline=(255, 60, 70), width=1.6)
    a.ring_ticks(32, 32, 25, 28, 24, (255, 120, 120), 0.6)
    for k in range(4):
        ang = math.radians(45 + 90 * k)
        a.circle(32 + math.cos(ang) * 22, 32 + math.sin(ang) * 22, 3, outline=(255, 90, 90), width=0.8)
    a.radial_glow(32, 34, 18, (255, 30, 50), 0.8)
    a.poly(BOOK.heart_pts(32, 34, 0.95), fill=(255, 40, 60), outline=(255, 200, 200), width=1.2)
    a.poly(BOOK.heart_pts(28, 30, 0.25), fill=(255, 220, 220))
    img = a.finish(emissive=False, alpha_from_glow=False)
    img[..., 3] = np.clip(img[..., :3].max(-1) * 1.5, 0, 255)
    rect = ('rect',) + h.model.atlas.put_image('sigil', img)
    for i, ry in enumerate((0, 90)):
        pl = oriented(h, f"g_heart{i}", "fade", (0, 6, 0), rx=90, ry=ry)
        pl.box((-6, 6, -6), (12, 0, 12), None, faces={"up": rect, "down": rect})
    ha = h.anim("beat", loop=True)
    beat = "1 + math.pow(math.max(0, math.sin(q.life_time * 300)), 10) * 0.35"
    ha.scale("g_heart0", [beat] * 3)
    ha.scale("g_heart1", [beat] * 3)
    ha.rot("fade", [0, "q.life_time * 60", 0])
    h.phase(1, h.default_form(0.2), "beat").phase(2, "beat")


# ---------------------------------------------------------------------------- B08/B14 roses, roots, thorns, waves
def roses():
    f = Fx("fx_b_rose", B, bounds=(8, 10, (0, 3, 0)), tex=(128, 256))
    st = f.bone("stem")
    for k in range(6):
        st.cbox((math.sin(k * 0.8) * 1.5, 6 + k * 12, 0), (4, 12.5, 4), "b_burgundy")
        st.crystal((2.6 + math.sin(k * 0.8) * 1.5, 6 + k * 12, 0), 6, 1.6, "b_thorn", "b_ruby")
    for sgn in (-1, 1):
        leaf = oriented(f, f"leaf{'l' if sgn > 0 else 'r'}", "stem", (0, 30 + sgn * 8, 0), rx=60, ry=sgn * 90)
        leaf.cbox((0, 37 + sgn * 8, 0), (8, 14, 0.8), "b_petal_dark")
    f.bone("bloom", pivot=(0, 76, 0))
    for L, (n, ln, w, rad, tilt, s) in enumerate(((7, 28, 20, 10, 70, "b_petal_dark"), (6, 24, 18, 7, 48, "b_petal"), (5, 18, 14, 4, 26, "b_petal_bright"))):
        f.model.bone(f"rl{L}", "bloom", pivot=(0, 76, 0))
        for k in range(n):
            a = 360 * k / n + L * 25
            petal(f, f"rp{L}_{k}", f"rl{L}", (math.cos(math.radians(a)) * rad * 0.3, 74 + L * 2, math.sin(math.radians(a)) * rad * 0.3), -a + 90, tilt, ln, w, s, "b_glow_band")
    f.bone("g_heart", "bloom").solid_cylinder((0, 74, 0), 4, 8, "b_core", layers=2)
    grow = f.anim("form", length=1.2)
    grow.scale("stem", {0: [1, 0.01, 1], 0.7: [1, 1, 1]})
    grow.scale("bloom", {0: [0, 0, 0], 0.6: [0, 0, 0], 1.1: [1.05, 1.05, 1.05], 1.2: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    idle.rot("bloom", [f"math.sin(q.life_time * 60) * 4", "q.life_time * 12", 0])
    vibrate(idle, "g_heart", 0.2, 1.1)
    f.phase(1, "form", "idle").phase(2, "idle")
    pul = f.anim("release", length=0.5)
    pul.scale("bloom", {0: [1, 1, 1], 0.12: [1.25, 1.1, 1.25], 0.5: [1, 1, 1]})
    pul.scale("g_heart", {0: [1, 1, 1], 0.1: [3, 3, 3], 0.5: [1, 1, 1]})
    f.pulse("release")

    r = Fx("fx_b_roots", B, tex=(256, 256), bounds=(20, 3, (0, 0, 0)))
    rs = np.random.RandomState(77)
    a = Art(256, 256, ss=2)
    for pts, depth in vein_paths(rs, 256, 256, [(128, 128, rs.rand() * 6.28) for _ in range(12)], life=110, branch=0.06, wobble=0.45):
        a.line(pts, (255, 40, 50) if depth else (200, 20, 34), 2.0 if depth == 0 else 1.0)
    img = a.finish(emissive=False, alpha_from_glow=False)
    img[..., 3] = np.clip(img[..., :3].max(-1) * 1.3, 0, 255)
    rect = ('rect',) + r.model.atlas.put_image('roots', img)
    r.bone("g_net").box((-150, 0.2, -150), (300, 0, 300), None, faces={"up": rect, "down": rect})
    ridges = r.bone("ridges")
    for k in range(14):
        ang = rs.rand() * math.tau
        rr = 20 + rs.rand() * 110
        hb = oriented(r, f"rg{k}", "ridges", (math.cos(ang) * rr, 0, math.sin(ang) * rr), ry=rs.rand() * 360)
        hb.cbox((math.cos(ang) * rr, 1.2, math.sin(ang) * rr), (2.5, 2.4, 24 + rs.rand() * 20), "b_burgundy")
    gr = r.anim("spread", length=1.5, loop="hold_on_last_frame")
    gr.scale("g_net", {0: [0.05, 1, 0.05], 1.4: [1, 1, 1]})
    gr.scale("ridges", {0: [0.05, 0, 0.05], 1.5: [1, 1, 1]})
    pa = r.anim("pulse_loop", loop=True)
    vibrate(pa, "g_net", 0.015, 1.2)
    r.phase(1, "spread").phase(2, "spread", "pulse_loop")

    th = Fx("fx_b_thorns", B, bounds=(4, 5, (0, 1.5, 0)))
    for k in range(7):
        ang = 360 * k / 7
        hb = oriented(th, f"tn{k}", "fade", (0, 0, 0), rx=12 + (k % 3) * 10, ry=ang)
        hb.crystal((0, 0, 0), 30 + (k % 3) * 10, 3.4, "b_thorn", "b_ruby")
    th.bone("c").crystal((0, 0, 0), 44, 4.5, "b_thorn", "b_ruby")
    erupt = th.anim("form", length=0.2)
    erupt.scale("fade", {0: [0.5, 0.01, 0.5], 0.12: [1.1, 1.2, 1.1], 0.2: [1, 1, 1]})
    th.phase(1, "form")

    w = Fx("fx_b_wave_ring", B, bounds=(10, 2, (0, 0.2, 0)))
    for k in range(6):
        hb = oriented(w, f"wb{k}", "fade", (0, 0, 0), ry=k * 60)
        hb.ring((0, 2, 0), 28, 4, 1.2, 6, "b_liquid", start=-120, arc=50)
        hb.ring((0, 2.2, 0), 30.5, 0.9, 1.4, 6, "b_glow_band", start=-122, arc=54)
    ex = w.anim("expand", length=0.6, loop="hold_on_last_frame")
    ex.scale("fade", {0: [0.2, 1, 0.2], 0.6: [1.3, 1, 1.3]})
    ex.rot("fade", [0, "q.anim_time * 360", 0])
    w.phase(1, "expand")


# ---------------------------------------------------------------------------- B09/B14 sea, whirlpool, pillar, beasts, tidal wave
def liquids():
    s = Fx("fx_b_sea", B, bounds=(36, 3, (0, 0, 0)), tex=(256, 256))
    a = Art(256, 256, ss=2)
    rsea = np.random.RandomState(9)
    a.radial_glow(128, 128, 126, (150, 8, 22), 1.0)
    for k in range(9):
        rr = 20 + k * 12 + rsea.rand() * 4
        a.circle(128, 128, rr, outline=(255, 70, 80) if k % 2 else (190, 20, 34), width=1.4 if k % 2 else 0.8)
    for pts, depth in vein_paths(rsea, 256, 256, [(128, 128, rsea.rand() * 6.28) for _ in range(8)], life=60, branch=0.04, wobble=0.5):
        a.line(pts, (255, 60, 70), 0.6)
    img = a.finish(emissive=False, alpha_from_glow=False)
    yy, xx = np.mgrid[0:256, 0:256]
    rad = np.sqrt((xx - 127.5) ** 2 + (yy - 127.5) ** 2) / 128.0
    img[..., 3] = np.clip((1.0 - rad) * 6, 0, 1) * 215
    rect = ('rect',) + s.model.atlas.put_image('sea', img)
    s.bone("t_surface").box((-128, 0.4, -128), (256, 0, 256), None, faces={"up": rect, "down": rect})
    for i in range(5):
        ring(s, f"t_rip{i}", "fade", (0, 1.3, 0), 24 + i * 22, 3, 0.6, 18 + i * 4, "b_liquid_thin")
        ring(s, f"g_rip{i}", "fade", (0, 1.5, 0), 26 + i * 22, 0.6, 0.4, 18 + i * 4, "b_glow_band", gap=4)
    sa = s.anim("ripple", loop=True)
    for i in range(5):
        sa.scale(f"t_rip{i}", [f"1 + math.sin(q.life_time * 120 - {i * 50}) * 0.05"] * 3)
        spin(sa, f"g_rip{i}", 6 * (1 if i % 2 else -1))
    form = s.anim("form", length=1.0)
    form.scale("fade", {0: [0.05, 1, 0.05], 1.0: [1, 1, 1]})
    s.phase(1, "form", "ripple").phase(2, "ripple")
    whirl = s.anim("whirl", loop=True)
    for i in range(5):
        spin(whirl, f"t_rip{i}", (5 - i) * 70)
        spin(whirl, f"g_rip{i}", (5 - i) * 90)
        whirl.pos(f"t_rip{i}", [0, f"-{(5 - i) * 0.4} * math.min(1, q.anim_time)", 0])
    s.phase(3, "whirl")

    w = Fx("fx_b_whirl", B, bounds=(18, 4, (0, 0, 0)))
    for k in range(4):
        hb = oriented(w, f"arm{k}", "fade", (0, 0, 0), ry=k * 90)
        for j in range(6):
            r0 = 120 - j * 18
            hb.ring((0, 1.5 + j * 0.1, 0), r0, 6 - j * 0.6, 1.2, 4, "b_liquid", start=j * 22, arc=50)
    funnel = oriented(w, "t_funnel", "fade", (0, 2, 0), rx=180)
    funnel.cone((0, 2, 0), 26, 22, 5, "b_liquid")
    w.bone("g_eye").solid_cylinder((0, -1, 0), 6, 3, "b_core", layers=2)
    wa = w.anim("spin", loop=True)
    for k in range(4):
        wa.rot(f"arm{k}", [0, "q.life_time * 220", 0])
    w.phase(1, w.default_form(0.6), "spin").phase(2, "spin")

    p = Fx("fx_b_pillar", B, bounds=(6, 18, (0, 6, 0)), tex=(128, 256))
    p.bone("col")
    for k in range(8):
        hb = p.model.bone(f"pc{k}", "col", pivot=(0, k * 28, 0))
        hb.solid_cylinder((0, k * 28, 0), 22 - k * 1.3, 29, "b_liquid", layers=2)
    p.model.bone("g_core", "col", pivot=(0, 0, 0)).solid_cylinder((0, 0, 0), 5, 224, "b_core", layers=2)
    for k in range(4):
        ring(p, f"g_pr{k}", "col", (0, 30 + k * 50, 0), 26, 1.2, 2, 14, "b_glow_band", gap=3)
    rise = p.anim("form", length=0.9)
    rise.scale("col", {0: [1, 0.01, 1], 0.7: [1.05, 1.06, 1.05], 0.9: [1, 1, 1]})
    pa = p.anim("swirl", loop=True)
    for k in range(8):
        pa.rot(f"pc{k}", [0, f"q.life_time * {120 + k * 20} * {1 if k % 2 else -1}", 0])
    for k in range(4):
        pa.pos(f"g_pr{k}", [0, f"math.mod(q.life_time * 60 + {k * 50}, 200) - 30", 0])
    p.phase(1, "form", "swirl").phase(2, "swirl")
    burst = p.anim("burst", length=0.5, loop="hold_on_last_frame")
    burst.scale("col", {0: [1, 1, 1], 0.12: [1.6, 1.1, 1.6], 0.45: [0, 0, 0]})
    p.phase(3, "burst")

    bst = Fx("fx_b_beast", B, bounds=(7, 9, (0, 3, -1)), tex=(128, 256))
    bst.bone("neck", pivot=(0, 0, 0))
    curve = (-10, -8, 6, 12, 15, 14)          # S-curve: rises, then leans over its prey (forward is -Z)
    for k in range(6):
        y, r = k * 14, 16 - k * 1.6
        hb = bst.model.bone(f"nk{k}", "neck" if k == 0 else f"nk{k - 1}", pivot=(0, y, 0), rotation=(curve[k], 0, 0))
        hb.solid_cylinder((0, y, 0), r, 15, "b_liquid", layers=2)
        sp = bst.model.bone(f"nk{k}_sp", f"nk{k}", pivot=(0, y + 8, r * 0.7), rotation=(-40, 0, 0))
        sp.crystal((0, y + 8, r * 0.7), 9 - k * 0.6, 3, "b_thorn", "b_ruby")          # dorsal spikes, raked back
        bst.model.bone(f"g_nv{k}", f"nk{k}", pivot=(0, y, 0)).cbox((0, y + 7.5, -r * 0.71), (1.2, 14, 0.4), "b_glow_band")  # throat vein
    hd = bst.model.bone("maw", "nk5", pivot=(0, 84, 0))
    hd.cbox((0, 92, -3), (17, 13, 18), "b_scales")                                   # skull
    hd.cbox((0, 90, -17), (12, 8, 14), "b_liquid_solid")                             # snout
    hd.cbox((0, 94.6, -16), (8, 1.4, 12), "b_crystal_glow")                          # snout ridge
    for j, (rx, ry, ln) in enumerate(((-60, 0, 16), (-70, 26, 12), (-70, -26, 12))):  # horn crest
        hb = bst.model.bone(f"horn{j}", "maw", pivot=(0, 98, 2), rotation=(rx, ry, 0))
        hb.crystal((0, 98, 2), ln, 4, "b_thorn", "b_ruby")
    for k in range(5):
        for sgn in (-1, 1):
            hd.cbox((sgn * 5.2, 84.6, -23 + k * 3.4), (1.4, 4, 1.4), "b_bone", rotation=(0, 45, 0))   # upper fangs
    eyes = bst.model.bone("g_eyes", "maw", pivot=(0, 95, -8))
    for sgn in (-1, 1):
        eyes.cbox((sgn * 8.6, 95, -8), (0.4, 2.2, 4), "b_core")
    jaw = bst.model.bone("jaw", "maw", pivot=(0, 86, 2))
    jaw.cbox((0, 83.5, -10), (13, 4.5, 24), "b_liquid_solid")
    for k in range(4):
        for sgn in (-1, 1):
            jaw.cbox((sgn * 4.4, 87, -19 + k * 3.6), (1.2, 3, 1.2), "b_bone", rotation=(0, 45, 0))     # lower fangs
    rise = bst.anim("form", length=0.8)
    rise.scale("fade", {0: [1, 0.01, 1], 0.6: [1, 1.05, 1], 0.8: [1, 1, 1]})
    sway = bst.anim("sway", loop=True)
    for k in range(6):
        sway.rot(f"nk{k}", [f"math.sin(q.life_time * 120 + {k * 30}) * 6", 0, f"math.cos(q.life_time * 90 + {k * 40}) * 4"])
    sway.rot("jaw", ["15 + math.sin(q.life_time * 200) * 8", 0, 0])
    bst.phase(1, "form", "sway").phase(2, "sway")
    lunge = bst.anim("lunge", length=0.7)
    for k in range(6):
        lunge.rot(f"nk{k}", {0: [0, 0, 0], 0.25: [-10, 0, 0], 0.45: [18, 0, 0], 0.7: [0, 0, 0]})
    lunge.rot("jaw", {0: [15, 0, 0], 0.3: [50, 0, 0], 0.45: [0, 0, 0], 0.7: [15, 0, 0]})
    bst.pulse("lunge")

    tw = Fx("fx_b_tidal", B, bounds=(30, 12, (0, 4, 0)), tex=(128, 256))
    wall = tw.bone("wall")
    for k in range(24):
        a = -60 + k * 5
        hb = oriented(tw, f"tw{k}", "wall", (0, 0, 0), ry=a)
        hb.cbox((0, 50, -200), (36, 100, 24), "b_liquid")
        crest = tw.model.bone(f"g_cr{k}", f"tw{k}", pivot=(0, 100, -200))
        crest.cbox((0, 104, -194), (36, 8, 16), "b_glow_band")
    wv = tw.anim("surge", loop=True)
    for k in range(24):
        wv.pos(f"tw{k}", [0, f"math.sin(q.life_time * 200 + {k * 30}) * 4", 0])
    tw.phase(1, tw.default_form(0.6), "surge").phase(2, "surge")


# ---------------------------------------------------------------------------- B10/B11 fragments + ribbon
def flow_parts():
    fr = Fx("fx_b_fragments", B, bounds=(3, 4, (0, 1, 0)))
    for k in range(14):
        ang = math.tau * k / 14
        y = 4 + (k % 5) * 6
        fr.bone(f"fg{k}").cbox((math.cos(ang) * 8, y, math.sin(ang) * 8), (1.5, 3.8 - (k % 3) * 0.6, 1.5), "b_ruby",
                               rotation=(30 + (k % 4) * 12, 45 + k * 23, (k % 3 - 1) * 20))   # tilted ruby shards
    swirl = fr.anim("swirl", loop=True)
    for k in range(14):
        swirl.rot(f"fg{k}", [0, f"q.life_time * {200 + k * 15}", 0])
    fr.phase(1, fr.default_form(0.15), "swirl").phase(2, "swirl")
    conv = fr.anim("converge", length=0.4, loop="hold_on_last_frame")
    for k in range(14):
        conv.scale(f"fg{k}", {0: [1, 1, 1], 0.4: [0.1, 0.1, 0.1]})
    fr.phase(3, "converge")

    rb = Fx("fx_b_ribbon", B, bounds=(5, 3, (0, 0, -1)))
    for k, (dz, dy) in enumerate(((0, 0), (-8, 0.8), (-16, 1.4), (-24, 1.0))):
        seg = rb.bone(f"t_rs{k}")
        w = 14 - k
        seg.cbox((0, dy, dz - 4), (w, 1.4, 9), "b_liquid")
        for sgn in (-1, 1):                                          # raised liquid lips: a flowing channel
            seg.cbox((sgn * (w / 2 + 0.3), dy + 1.0, dz - 4), (1.2, 2.6, 9), "b_liquid", rotation=(0, 0, sgn * -22))
        rb.model.bone(f"g_rv{k}", "fade", pivot=(0, dy, dz)).cbox((0, dy + 0.8, dz - 4), (1.0, 0.4, 9), "b_glow_band")
    br = oriented(rb, "branch", "fade", (0, 1, -12), ry=40)
    br.cbox((0, 1, -18), (5, 0.8, 12), "b_liquid_solid")
    ra = rb.anim("flow", loop=True)
    for k in range(4):
        ra.pos(f"t_rs{k}", [0, f"math.sin(q.life_time * 300 + {k * 60}) * 1.2", 0])
        ra.rot(f"t_rs{k}", [0, 0, f"math.sin(q.life_time * 240 + {k * 50}) * 10"])
    ra.scale("branch", ["0.8 + math.sin(q.life_time * 180) * 0.2"] * 3)
    rb.phase(1, rb.default_form(0.2), "flow").phase(2, "flow")


# ---------------------------------------------------------------------------- B15 heart, vessels, hands, cages, astral book
def heart_parts():
    h = Fx("fx_b_heart", B, bounds=(12, 14, (0, 4, 0)), tex=(128, 256))
    h.bone("heart", pivot=(0, 40, 0))
    v = h.model.bone("ventricles", "heart", pivot=(0, 40, 0))
    for a in (0, 30, 60):
        v.cbox((0, 36, 0), (40, 34, 26), "b_crystal", rotation=(0, a, 0))
    for k, (w, y, dx) in enumerate(((32, 16, -3), (22, 7, -6), (12, 0, -8))):
        for a in (0, 45):
            v.cbox((dx, y, 1), (w, 10, w * 0.75), "b_crystal" if k < 2 else "b_crystal_glow", rotation=(0, a, 0))
    for k in range(6):
        v.cbox((-16 + k * 6.5, 37 + (k % 2) * 5, -16.6), (3.4, 22, 1), "b_ruby")
    atr = h.model.bone("atria", "heart", pivot=(0, 56, 0))
    for (x, w) in ((-12, 20), (13, 17)):
        for a in (0, 45):
            atr.cbox((x, 57, 3), (w, 15, w * 0.9), "b_crystal_glow", rotation=(0, a, 0))
    aorta = h.model.bone("aorta", "heart", pivot=(4, 64, 0))
    ring(h, "arch_v", "aorta", (5, 67, 5), 7, 4.5, 4.5, 10, "b_liquid_solid", rx=90, start=-10, arc=200)
    aorta.solid_cylinder((-2, 62, 6), 3.2, 14, "b_liquid_solid", layers=2)
    aorta.solid_cylinder((12, 62, 4), 2.6, 12, "b_liquid_solid", layers=2)
    aorta.solid_cylinder((-10, 60, -2), 2.4, 12, "b_liquid_solid", layers=2)
    h.model.bone("g_veins", "heart", pivot=(0, 40, 0)).cbox((0, 36, -16.9), (34, 40, 0.3), "b_veins")
    h.model.bone("g_core", "heart", pivot=(0, 40, 0)).solid_cylinder((0, 24, 0), 9, 26, "b_core", layers=3)
    for k in range(8):
        hb = oriented(h, f"sh{k}", "heart", (0, 40, 0), rx=-50 + 15 * (k % 3), ry=k * 45)
        hb.crystal((0, 40, 0), 36 + (k % 3) * 6, 4.5, "b_crystal_glow", "b_ruby")
    form = h.anim("form", length=1.6)
    form.scale("heart", {0: [0.05, 0.05, 0.05], 1.2: [1.05, 1.05, 1.05], 1.6: [1, 1, 1]})
    beat = h.anim("beat", loop=True, length=1.0)
    beat.scale("ventricles", {0: [1, 1, 1], 0.08: [0.86, 0.9, 0.86], 0.22: [1.08, 1.06, 1.08], 0.4: [1, 1, 1], 1.0: [1, 1, 1]})
    beat.scale("atria", {0: [1, 1, 1], 0.3: [1, 1, 1], 0.36: [0.9, 0.92, 0.9], 0.5: [1.05, 1.04, 1.05], 0.7: [1, 1, 1], 1.0: [1, 1, 1]})
    beat.scale("g_core", {0: [1, 1, 1], 0.1: [1.5, 1.4, 1.5], 0.4: [1, 1, 1], 1.0: [1, 1, 1]})
    beat.rot("heart", [0, "q.life_time * 8", 0])
    h.phase(1, "form", "beat").phase(2, "beat")
    stop = h.anim("stopped", loop=True)
    stop.scale("g_core", [0.6, 0.6, 0.6])
    vibrate(stop, "heart", 0.008, 9)
    h.phase(3, "stopped")
    final = h.anim("final", length=0.8, loop="hold_on_last_frame")
    final.scale("heart", {0: [1, 1, 1], 0.1: [0.8, 0.8, 0.8], 0.25: [1.6, 1.6, 1.6], 0.6: [0, 0, 0]})
    h.phase(4, "final")

    vs = Fx("fx_b_vessel", B, bounds=(4, 4, (0, 0, -1)))
    vs.bone("stretch", pivot=(0, 0, 0))
    vs.model.bone("t_tube", "stretch", pivot=(0, 0, 0)).cbox((0, 0, -8), (3.2, 3.2, 16), "b_liquid")
    vs.model.bone("g_flow", "stretch", pivot=(0, 0, 0)).cbox((0, 0, -8), (1.2, 1.2, 16), "b_glow_band")
    for k in range(3):
        hb = vs.model.bone(f"vb{k}", "stretch", pivot=(0, 0, -4 - k * 4), rotation=(0, 35 * (1 if k % 2 else -1), 0))
        hb.cbox((0, 0, -4 - k * 4 - 3), (1.6, 1.6, 6), "b_liquid_solid")
    va = vs.anim("pulse_loop", loop=True)
    va.scale("g_flow", ["1 + math.pow(math.max(0, math.sin(q.life_time * 216)), 8)", "1 + math.pow(math.max(0, math.sin(q.life_time * 216)), 8)", 1])
    grow = vs.anim("form", length=0.6)
    grow.scale("stretch", {0: [1, 1, 0.01], 0.6: [1, 1, 1]})
    vs.phase(1, "form", "pulse_loop").phase(2, "pulse_loop")
    retract = vs.anim("retract", length=0.6, loop="hold_on_last_frame")
    retract.scale("stretch", {0: [1, 1, 1], 0.6: [1, 1, 0.01]})
    vs.phase(3, "retract")

    hd = Fx("fx_b_hand", B, bounds=(6, 8, (0, 2.5, 0)), tex=(128, 256))
    hd.bone("arm")
    hd.bone("t_wrist", "arm").solid_cylinder((0, 0, 0), 10, 30, "b_liquid", layers=2)
    palm = hd.model.bone("palm", "arm", pivot=(0, 30, 0))
    palm.cbox((0, 40, 0), (24, 20, 8), "b_liquid_solid")
    for k, x in enumerate((-9, -3, 3, 9)):
        prev = "palm"
        for j in range(3):
            fb = hd.model.bone(f"f{k}_{j}", prev, pivot=(x, 50 + j * 7, 0))
            fb.cbox((x, 53.5 + j * 7, 0), (5 - j * 0.6, 7.2, 5 - j * 0.6), "b_liquid_solid")
            prev = f"f{k}_{j}"
        hd.model.bone(f"g_nail{k}", prev, pivot=(x, 71, 0)).cbox((x, 71.5, -1.6), (3, 2, 1), "b_ruby")
    thumb = hd.model.bone("thumb", "palm", pivot=(-12, 38, 0), rotation=(0, 0, 0))
    thumb.cbox((-15, 44, 0), (5, 12, 5), "b_liquid_solid")
    rise = hd.anim("form", length=0.7)
    rise.pos("arm", {0: [0, -60, 0], 0.6: [0, 2, 0], 0.7: [0, 0, 0]})
    hd.phase(1, "form")
    grab = hd.anim("grab", length=0.8, loop="hold_on_last_frame")
    for k in range(4):
        for j in range(3):
            grab.rot(f"f{k}_{j}", {0: [0, 0, 0], 0.4: [-35, 0, 0], 0.8: [-55, 0, 0]})
    grab.rot("thumb", {0: [0, 0, 0], 0.8: [0, 40, 0]})
    hd.phase(2, "grab")

    cg = Fx("fx_b_cage", B, bounds=(4, 5, (0, 1.5, 0)))
    for k in range(8):
        hb = oriented(cg, f"bar{k}", "fade", (0, 0, 0), ry=k * 45)
        tilt = cg.model.bone(f"bt{k}", f"bar{k}", pivot=(0, 0, -14), rotation=(-12, 0, 0))
        tilt.crystal((0, 0, -14), 46, 3.2, "b_thorn", "b_ruby")
    cg.bone("g_ring").ring((0, 0.5, 0), 15, 1, 0.6, 16, "b_glow_band")
    close = cg.anim("form", length=0.4)
    close.scale("fade", {0: [1.6, 0.01, 1.6], 0.3: [0.95, 1.08, 0.95], 0.4: [1, 1, 1]})
    cg.phase(1, "form")

    # astral copy of the Blood Grimoire rising above the caster (B15 Phase 1)
    bk = Fx("fx_b_book", B, bounds=(3, 3, (0, 0, 0)), tex=(256, 256))
    src, _dims = BOOK.build_book("blood")
    bk.model.atlas = src.atlas
    for bone in src.bones:
        if bone.name.startswith("flow_"):
            continue  # flow overlays need the attachable's second render controller
        if bone.name == "book":
            bone.binding = None
            bone.parent = "fade"
        nb = bk.model.bone(bone.name, bone.parent, pivot=bone.pivot, rotation=bone.rotation)
        nb.cubes = bone.cubes
    bo = bk.anim("open", loop=True)
    bo.scale("book", [3, 3, 3])
    bo.rot("half_r", [0, -14, 0]).rot("half_l", [0, 14, 0])
    for i in range(3):
        bo.rot(f"flip{i}", [0, f"-14 - math.mod(q.life_time * 160 + {i * 60}, 152)", 0])
    bo.rot("g_sigil_spin", [0, "q.life_time * 90", 0])
    bo.scale("heart", ["1 + math.pow(math.max(0, math.sin(q.life_time * 216)), 12) * 0.22"] * 3)
    bo.pos("book", [0, "math.sin(q.life_time * 90) * 2", 0])
    bk.phase(1, bk.default_form(0.6), "open").phase(2, "open")


for build in (stilettos, guillotine, leviathan, crowns, rose_aegis, fan, threads, roses, liquids, flow_parts, heart_parts):
    build()
