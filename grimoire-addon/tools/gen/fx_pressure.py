"""Pressure Magic constructs: compressed air, compression rings, copper mechanisms, shockwaves.
Palette: orange / golden orange / copper / charcoal / brilliant white (never purple)."""
import math
from .fxdefs import Fx
from .fxparts import oriented, ring, spin, vibrate

P = "pressure"


def fade_in(f, t=0.3):
    return f.default_form(t)


# ---------------------------------------------------------------------------- P01 lance
def lance():
    f = Fx("fx_p_lance", P, bounds=(12, 6, (0, 0, -1.5)))
    sh = f.bone("t_shell")
    for (w, l, z0) in ((9.0, 70, 6), (6.0, 66, 4), (3.6, 62, 2)):
        sh.cbox((0, 0, z0 - l / 2), (w, w, l), "p_air_dense", rotation=(0, 0, 45))
    f.bone("g_core").cbox((0, 0, -26), (1.6, 1.6, 64), "p_core")
    tip = f.bone("g_tip")
    for k, (s, z) in enumerate(((3.2, -60), (2.2, -65), (1.2, -69), (0.5, -72))):
        tip.cbox((0, 0, z), (s, s, 5), "p_glow", rotation=(0, 0, 45))
    fins = f.bone("fins")
    for a in (0, 90, 180, 270):
        fb = oriented(f, f"fin{a}", "fins", (0, 0, 6), rx=0, ry=0)
        x, y = math.cos(math.radians(a)) * 5.5, math.sin(math.radians(a)) * 5.5
        fb.cbox((x, y, 8), (1.6 if a in (90, 270) else 5, 5 if a in (90, 270) else 1.6, 10), "p_copper")
    f.bone("t_trail").cbox((0, 0, 26), (2.6, 2.6, 40), "p_air_thin")
    for i, z in enumerate((4, -12, -28, -44)):
        f.bone(f"slide{i}", pivot=(0, 0, z))
        ring(f, f"g_ring{i}", f"slide{i}", (0, 0, z), 7.0 - i * 0.9, 0.8, 1.3, 12, "p_glow_band", rx=90)
    form = f.anim("form", length=0.35)
    form.scale("fade", {0: [0.2, 0.2, 0.6], 0.25: [1.08, 1.08, 1.02], 0.35: [1, 1, 1]})
    for i in range(4):
        form.pos(f"slide{i}", {0: [0, 0, 22], 0.1 + 0.05 * i: [0, 0, 18], 0.35: [0, 0, 0]})
    fly = f.anim("fly", loop=True)
    for i in range(4):
        spin(fly, f"g_ring{i}", 720 * (1 if i % 2 else -1))
    vibrate(fly, "t_shell", 0.05, 11)
    fly.scale("t_trail", [1, 1, "1.4 + math.sin(q.life_time * 900) * 0.3"])
    f.phase(1, "form", "fly").phase(2, "fly")
    hit = f.anim("impact", length=0.3)
    hit.scale("fade", {0: [1, 1, 1], 0.08: [1.6, 1.6, 0.6], 0.3: [0, 0, 0]})
    f.phase(3, "impact")


# ---------------------------------------------------------------------------- P02 atlas piston
def piston():
    f = Fx("fx_p_piston", P, bounds=(14, 36, (0, -8, 0)), tex=(128, 256))
    f.bone("drop")
    head = f.bone("t_head", "drop")
    head.solid_cylinder((0, 0, 0), 44, 14, "p_copper_glass", layers=3)
    rim = f.bone("rim", "drop")
    rim.ring((0, 7, 0), 44, 3, 15, 16, "p_copper")
    rim.ring((0, 7, 0), 32, 2, 15.5, 16, "p_copper_dark")
    for k in range(8):
        a = math.tau * k / 8
        rim.cbox((math.cos(a) * 38, 15, math.sin(a) * 38), (3, 2, 3), "p_copper_rivet")
    face = f.bone("g_face", "drop")
    face.cbox((0, -0.4, 0), (60, 0.2, 60), "p_glow", rotation=(0, 45, 0))
    bands = f.bone("g_bands", "drop")
    bands.ring((0, 4, 0), 45, 1.2, 1.5, 16, "p_glow_band")
    bands.ring((0, 10, 0), 45, 1.2, 1.5, 16, "p_glow_band")
    shaft = f.bone("t_shaft", "drop")
    shaft.solid_cylinder((0, 14, 0), 16, 150, "p_copper_glass", layers=2)
    col = f.bone("collars", "drop")
    for y in (34, 78, 122):
        col.ring((0, y, 0), 18, 3, 6, 12, "p_copper")
    ch = f.bone("g_channels", "drop")
    for k in range(4):
        a = math.tau * k / 4 + math.pi / 4
        ch.cbox((math.cos(a) * 16.5, 90, math.sin(a) * 16.5), (1.2, 150, 1.2), "p_glow_vband")
    for i, (r, y) in enumerate(((62, 30), (74, 76), (54, 120))):
        f.bone(f"rh{i}")
        ring(f, f"g_mring{i}", f"rh{i}", (0, y, 0), r, 1.5, 2.5, 24, "p_glow_band", gap=3)
        ring(f, f"mring{i}", f"rh{i}", (0, y, 0), r + 3, 1.0, 1.5, 12, "p_copper", gap=12)
    form = f.anim("form", length=0.8)
    form.scale("drop", {0: [0.01, 0.01, 0.01], 0.6: [1.04, 1.04, 1.04], 0.8: [1, 1, 1]})
    for i in range(3):
        form.scale(f"rh{i}", {0: [0.01, 1, 0.01], 0.2 + 0.15 * i: [0.2, 1, 0.2], 0.7: [1, 1, 1]})
    hover = f.anim("hover", loop=True)
    for i in range(3):
        spin(hover, f"g_mring{i}", 60 * (1 if i % 2 else -1))
        spin(hover, f"mring{i}", -30 * (1 if i % 2 else -1))
    hover.pos("drop", [0, "math.sin(q.life_time * 90) * 1.5", 0])
    f.phase(1, "form", "hover").phase(2, "hover")
    slam = f.anim("slam", length=0.35, loop="hold_on_last_frame")
    slam.pos("drop", {0: [0, 0, 0], 0.08: [0, 4, 0], 0.3: [0, "-v.len * 16 + 2", 0]})
    f.phase(3, "slam", "hover")
    imp = f.anim("impact", length=0.6, loop="hold_on_last_frame")
    imp.pos("drop", [0, "-v.len * 16 + 2", 0])
    imp.scale("t_head", {0: [1.1, 0.7, 1.1], 0.2: [0.96, 1.08, 0.96], 0.6: [1, 1, 1]})
    f.phase(4, "impact", "hover")
    ret = f.anim("retract", length=0.9, loop="hold_on_last_frame")
    ret.pos("drop", {0: [0, "-v.len * 16 + 2", 0], 0.9: [0, 0, 0]})
    ret.scale("fade", {0: [1, 1, 1], 0.6: [1, 1, 1], 0.9: [0.01, 0.01, 0.01]})
    f.phase(5, "retract", "hover")


# ---------------------------------------------------------------------------- P03 cutting plane
def blade():
    f = Fx("fx_p_blade", P, bounds=(14, 4, (0, 0, -2)))
    body = f.bone("t_body")
    body.ring((0, 0, 0), 64, 18, 0.8, 18, "p_air_dense", start=-165, arc=150)
    inner = f.bone("t_inner")
    inner.ring((0, 0, 0), 50, 10, 0.6, 14, "p_air_thin", start=-160, arc=140)
    edge = f.bone("g_edge")
    edge.ring((0, 0, 0), 73.5, 2.2, 1.2, 24, "p_glow_band", start=-168, arc=156)
    edge.ring((0, 0.4, 0), 56, 0.8, 0.6, 18, "p_glow_band", start=-150, arc=120)
    form = f.anim("form", length=0.3)
    form.scale("fade", {0: [0.15, 1, 1], 0.2: [1.1, 1, 1], 0.3: [1, 1, 1]})
    fly = f.anim("fly", loop=True)
    fly.scale("g_edge", ["1 + math.sin(q.life_time * 1100) * 0.02", 1, "1 + math.sin(q.life_time * 1100) * 0.02"])
    fly.rot("t_inner", [0, "math.sin(q.life_time * 700) * 2", 0])
    f.phase(1, "form", "fly").phase(2, "fly")


# ---------------------------------------------------------------------------- P04 ring wings + discs
def salvo():
    f = Fx("fx_p_salvo", P, bounds=(10, 8, (0, 1, 0)))
    f.bone("wings")
    idx = 0
    for s in (-1, 1):
        for r in range(3):
            for k in range(4):
                x = s * (11 + k * 9)
                y = 8 + r * 10 + k * 3.5
                z = 7 + k * 3 + r
                f.bone(f"wr{idx}", "wings", pivot=(x, y, z))
                ring(f, f"g_wring{idx}", f"wr{idx}", (x, y, z), 4.6 - r * 0.4, 0.7, 1.0, 10, "p_glow_band", rx=90)
                ring(f, f"wcop{idx}", f"wr{idx}", (x, y, z + 0.6), 5.4 - r * 0.4, 0.6, 0.6, 8, "p_copper", rx=90, gap=10)
                idx += 1
    hub = f.bone("hub", "wings", pivot=(0, 18, 8))
    ring(f, "hubring", "hub", (0, 18, 8), 6, 1.5, 2, 12, "p_copper", rx=90)
    ring(f, "g_hubcore", "hub", (0, 18, 8), 3, 1.2, 2.2, 8, "p_glow_band", rx=90)
    for s in (-1, 1):
        f.bone(f"strut{'l' if s > 0 else 'r'}", "wings").cbox((s * 22, 22, 10), (34, 1.4, 1.4), "p_copper_dark", rotation=(0, 0, 0))
    form = f.anim("form", length=0.9)
    for i in range(idx):
        t0 = 0.05 + (i % 12) * 0.05
        form.scale(f"wr{i}", {0: [0, 0, 0], t0: [0, 0, 0], t0 + 0.12: [1.3, 1.3, 1.3], t0 + 0.2: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    for i in range(idx):
        spin(idle, f"g_wring{i}", 240 * (1 if i % 2 else -1))
    spin(idle, "hubring", 120)
    idle.pos("wings", [0, "math.sin(q.life_time * 120) * 0.6", 0])
    f.phase(1, "form", "idle").phase(2, "idle")
    fire = f.anim("fire", loop=True, length=0.5)
    for i in range(idx):
        ph = (i % 4) * 0.12
        fire.scale(f"wr{i}", {0: [1, 1, 1], ph: [1, 1, 1], ph + 0.05: [1.5, 1.5, 1.5], ph + 0.15: [1, 1, 1], 0.5: [1, 1, 1]})
    f.phase(3, "fire", "idle")

    d = Fx("fx_p_disc", P, bounds=(3, 3, (0, 0, 0)))
    ring(d, "t_disc", "fade", (0, 0, 0), 4.5, 6, 1.4, 12, "p_air_dense", rx=90)
    ring(d, "g_rim", "fade", (0, 0, 0), 7.6, 1.2, 1.8, 14, "p_glow_band", rx=90)
    oriented(d, "g_dcore", "fade", (0, 0, 0), rx=90).solid_cylinder((0, -0.9, 0), 1.8, 1.8, "p_core", layers=2)
    a = d.anim("spin", loop=True)
    spin(a, "t_disc", 1440)
    spin(a, "g_rim", -1440)
    d.phase(1, d.default_form(0.15), "spin").phase(2, "spin")


# ---------------------------------------------------------------------------- P05 aegis dome
def dome():
    f = Fx("fx_p_dome", P, bounds=(14, 9, (0, 2, 0)), tex=(128, 256))
    f.bone("squash")
    radii = (82, 72, 62)
    for i, r in enumerate(radii):
        f.bone(f"layer{i}", "squash")
        sh = f.bone(f"t_shell{i}", f"layer{i}")
        sh.dome((0, 0, 0), r, "p_air" if i else "p_air_dense", bands=6, segs=20, thickness=0.6, band=r * 0.14, cap=True)
        ring(f, f"g_base{i}", f"layer{i}", (0, 1, 0), r, 1.2, 2, 24, "p_glow_band")
        ring(f, f"g_arc{i}a", f"layer{i}", (0, 0, 0), r * 0.98, 0.8, 1.2, 20, "p_glow_band", rx=90, ry=30 * i, arc=180, start=0)
        ring(f, f"g_arc{i}b", f"layer{i}", (0, 0, 0), r * 0.98, 0.8, 1.2, 20, "p_glow_band", rx=90, ry=30 * i + 90, arc=180, start=0)
        ring(f, f"cop{i}", f"layer{i}", (0, r * 0.55, 0), r * 0.83, 0.8, 1.0, 16, "p_copper", gap=6)
    act = f.anim("active", loop=True)
    for i in range(3):
        spin(act, f"g_base{i}", 25 * (1 if i % 2 else -1))
        spin(act, f"cop{i}", -40 * (1 if i % 2 else -1))
        act.rot(f"layer{i}", [0, f"q.life_time * {8 + 6 * i} * {1 if i % 2 else -1}", 0])
    form = f.anim("form", length=0.8)
    for i in range(3):
        form.scale(f"layer{i}", {0: [0.01, 0.01, 0.01], 0.15 * (2 - i): [0.01, 0.01, 0.01], 0.15 * (2 - i) + 0.4: [1.05, 1.05, 1.05], 0.8: [1, 1, 1]})
    f.phase(1, "form", "active").phase(2, "active")
    for k in range(3):
        b = f.anim(f"break{k}", length=0.35, loop="hold_on_last_frame")
        b.scale(f"layer{k}", {0: [1, 1, 1], 0.08: [1.12, 1.12, 1.12], 0.3: [0, 0, 0]})
        g = f.anim(f"gone{k}", loop=True)
        g.scale(f"layer{k}", [0, 0, 0])
    f.phase(3, "active", "break0")
    f.phase(4, "active", "gone0", "break1")
    f.phase(5, "active", "gone0", "gone1", "break2")
    pul = f.anim("compress", length=0.4)
    pul.scale("squash", {0: [1, 1, 1], 0.06: [0.9, 0.86, 0.9], 0.2: [1.05, 1.06, 1.05], 0.4: [1, 1, 1]})
    f.pulse("compress")


# ---------------------------------------------------------------------------- P06 mantle
def mantle():
    f = Fx("fx_p_mantle", P, bounds=(3, 3, (0, 1, 0)))
    f.bone("cloak")
    ring(f, "g_shoulder", "cloak", (0, 23, 0), 9.5, 1.0, 1.4, 14, "p_glow_band")
    ring(f, "t_collar", "cloak", (0, 25, 0), 8.2, 2.5, 4, 12, "p_air_dense")
    ring(f, "g_waist", "cloak", (0, 12, 0), 10.5, 0.8, 1.0, 14, "p_glow_band")
    for k in range(10):
        a = 360 * k / 10
        hb = oriented(f, f"t_rib{k}", "cloak", (0, 24, 0), ry=a)
        hb.cbox((0, 13, -9.5), (6, 20, 0.4), "p_air")
    form = f.anim("form", length=0.4)
    form.scale("cloak", {0: [1.8, 0.2, 1.8], 0.3: [0.95, 1.05, 0.95], 0.4: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    for k in range(10):
        idle.rot(f"t_rib{k}", [f"math.sin(q.life_time * 160 + {k * 36}) * 9", 0, 0])
    spin(idle, "g_shoulder", 70)
    spin(idle, "g_waist", -50)
    f.phase(1, "form", "idle").phase(2, "idle")
    pul = f.anim("contract", length=0.45)
    pul.scale("cloak", {0: [1, 1, 1], 0.1: [0.7, 0.95, 0.7], 0.22: [1.45, 1.1, 1.45], 0.45: [1, 1, 1]})
    f.pulse("contract")


# ---------------------------------------------------------------------------- P07 titan's vise
def vise():
    f = Fx("fx_p_vise", P, bounds=(7, 5, (0, 1, 0)))
    for i in range(6):
        f.model.bone(f"ph{i}", "fade", pivot=(0, 0, 0), rotation=(0, 60 * i, 0))
        f.model.bone(f"pm{i}", f"ph{i}", pivot=(0, 0, 0))
        pl = oriented(f, f"plate{i}", f"pm{i}", (0, 16, -32), rx=90)
        pl.hexplate((0, 16, -32), 12, 2.4, "p_copper_dark", edge_style="p_copper")
        for k in range(6):
            a = math.tau * k / 6
            pl.cbox((math.cos(a) * 9.5, 17.4, -32 + math.sin(a) * 9.5), (1.2, 0.8, 1.2), "p_copper_rivet")
        ring(f, f"g_pr{i}", f"pm{i}", (0, 16, -30.6), 6.5, 0.8, 1.0, 12, "p_glow_band", rx=90)
        ring(f, f"g_pc{i}", f"pm{i}", (0, 16, -30.4), 3.2, 0.8, 1.2, 8, "p_glow_band", rx=90)
    ring(f, "g_top", "fade", (0, 34, 0), 26, 1.0, 1.5, 18, "p_glow_band")
    ring(f, "g_bot", "fade", (0, 1, 0), 26, 1.0, 1.5, 18, "p_glow_band")
    form = f.anim("form", length=0.6)
    for i in range(6):
        form.pos(f"pm{i}", {0: [0, 0, -18], 0.1 * i: [0, 0, -18], 0.1 * i + 0.25: [0, 0, 0]})
    form.scale("fade", {0: [0.6, 0.6, 0.6], 0.5: [1, 1, 1]})
    squeeze = f.anim("squeeze", loop="hold_on_last_frame", length=5.5)
    for i in range(6):
        squeeze.pos(f"pm{i}", {0: [0, 0, 0], 5.5: [0, 0, 13]})
        spin(squeeze, f"g_pr{i}", 300 * (1 if i % 2 else -1))
    spin(squeeze, "g_top", 90)
    spin(squeeze, "g_bot", -90)
    f.phase(1, "form").phase(2, "squeeze")
    pul = f.anim("pulse", length=0.3)
    for i in range(6):
        pul.scale(f"plate{i}", {0: [1, 1, 1], 0.06: [1.12, 1.12, 1.12], 0.3: [1, 1, 1]})
    pul.scale("g_top", {0: [1, 1, 1], 0.08: [0.7, 1, 0.7], 0.3: [1, 1, 1]})
    f.pulse("pulse")
    crush = f.anim("crush", length=0.4, loop="hold_on_last_frame")
    for i in range(6):
        crush.pos(f"pm{i}", {0: [0, 0, 13], 0.15: [0, 0, 20], 0.4: [0, 0, 18]})
    f.phase(3, "crush")


# ---------------------------------------------------------------------------- P08/P14 columns
def column():
    f = Fx("fx_p_column", P, bounds=(4, 12, (0, 3, 0)))
    f.bone("t_body").cylinder((0, 0, 0), 9, 64, 10, "p_air_dense", thickness=1.2)
    f.bone("g_core").solid_cylinder((0, 0, 0), 1.6, 64, "p_core", layers=2)
    f.bone("t_runes").ring((0, 32, 0), 10.2, 0.6, 7, 12, "p_runes_air")
    caps = f.bone("caps")
    for y in (0, 63):
        caps.ring((0, y + 1, 0), 11, 2.5, 3, 10, "p_copper")
    caps.hexplate((0, 66, 0), 8, 1.6, "p_copper_dark", edge_style="p_copper")
    caps.crystal((0, 66.8, 0), 9, 3.2, "p_amber")
    for i in range(5):
        ring(f, f"g_cr{i}", "fade", (0, 8 + i * 12, 0), 11.5, 0.9, 1.4, 12, "p_glow_band")
    rise = f.anim("rise", length=0.8)
    rise.scale("fade", {0: [0.6, 0.01, 0.6], 0.6: [1.05, 1.04, 1.05], 0.8: [1, 1, 1]})
    idle = f.anim("idle", loop=True)
    for i in range(5):
        idle.pos(f"g_cr{i}", [0, f"math.sin(q.life_time * 90 + {i * 72}) * 4", 0])
        spin(idle, f"g_cr{i}", 60 * (1 if i % 2 else -1))
    spin(idle, "t_runes", 25)
    f.phase(1, "rise", "idle").phase(2, "idle")
    pul = f.anim("flash", length=0.3)
    pul.scale("g_core", {0: [1, 1, 1], 0.08: [3, 1, 3], 0.3: [1, 1, 1]})
    f.pulse("flash")
    sink = f.anim("dissolve", length=0.8)
    sink.scale("fade", {0: [1, 1, 1], 0.7: [0.4, 0.01, 0.4]})
    f.phase(15, "dissolve")


# ---------------------------------------------------------------------------- P09 resonance cage
def cage():
    f = Fx("fx_p_cage", P, bounds=(11, 11, (0, 0, 0)))
    f.bone("cage")
    orient = ((0, 0), (90, 0), (90, 60), (90, 120), (50, 30), (50, 210))
    for i, (rx, ry) in enumerate(orient):
        ring(f, f"g_cring{i}", "cage", (0, 0, 0), 70 - i * 1.5, 1.4, 1.8, 28, "p_glow_band", rx=rx, ry=ry, gap=2)
        ring(f, f"cc{i}", "cage", (0, 0, 0), 72 - i * 1.5, 0.8, 1.0, 14, "p_copper", rx=rx, ry=ry, gap=14)
    f.bone("t_haze", "cage").sphere_shell((0, 0, 0), 66, "p_air_thin", rings=5, segs=16, thickness=0.5, band=8)
    f.bone("g_core", "cage").solid_cylinder((0, -4, 0), 4, 8, "p_core", layers=3)
    vib = f.anim("vibrate", loop=True)
    for i in range(6):
        vibrate(vib, f"g_cring{i}", 0.025, 3 + i * 1.7, i * 40)
        spin(vib, f"cc{i}", 20 + i * 9)
    vib.rot("cage", [0, "q.life_time * 12", 0])
    f.phase(1, f.default_form(0.6), "vibrate").phase(2, "vibrate")
    pul = f.anim("pulse", length=0.45)
    pul.scale("cage", {0: [1, 1, 1], 0.1: [0.82, 0.82, 0.82], 0.25: [1.08, 1.08, 1.08], 0.45: [1, 1, 1]})
    pul.scale("g_core", {0: [1, 1, 1], 0.1: [2.5, 2.5, 2.5], 0.45: [1, 1, 1]})
    f.pulse("pulse")


# ---------------------------------------------------------------------------- P10 step ring / P11 rail ring
def step_ring():
    f = Fx("fx_p_step_ring", P, bounds=(4, 2, (0, 0, 0)))
    f.bone("g_ring").ring((0, 0.4, 0), 15, 2.2, 0.8, 16, "p_glow_band")
    f.bone("g_inner").ring((0, 0.5, 0), 9, 1.4, 0.8, 12, "p_glow_band")
    f.bone("cop").ring((0, 0.3, 0), 17.5, 1.2, 0.8, 12, "p_copper", gap=10)
    f.bone("t_air").ring((0, 1.5, 0), 12, 6, 3, 14, "p_air")
    idle = f.anim("idle", loop=True)
    spin(idle, "g_ring", 360)
    spin(idle, "g_inner", -540)
    f.phase(1, f.default_form(0.12), "idle").phase(2, "idle")
    col = f.anim("collapse", length=0.35, loop="hold_on_last_frame")
    col.scale("fade", {0: [1, 1, 1], 0.1: [0.3, 1, 0.3], 0.22: [2.4, 1.4, 2.4], 0.35: [0, 0, 0]})
    f.phase(3, "collapse")


def rail_ring():
    f = Fx("fx_p_rail_ring", P, bounds=(5, 5, (0, 0, 0)))
    ring(f, "g_rim", "fade", (0, 0, 0), 28, 2.4, 3, 24, "p_glow_band", rx=90)
    ring(f, "segs", "fade", (0, 0, 0), 32, 2.5, 4, 8, "p_copper", rx=90, gap=16)
    ring(f, "t_film", "fade", (0, 0, 0), 14, 26, 0.4, 16, "p_air_thin", rx=90)
    ring(f, "g_inner", "fade", (0, 0, 0), 22, 0.8, 1.2, 18, "p_glow_band", rx=90, gap=5)
    idle = f.anim("idle", loop=True)
    spin(idle, "segs", 120)
    spin(idle, "g_inner", -240)
    f.phase(1, f.default_form(0.25), "idle").phase(2, "idle")
    burst = f.anim("burst", length=0.4, loop="hold_on_last_frame")
    burst.scale("fade", {0: [1, 1, 1], 0.08: [1.35, 1.35, 1.35], 0.4: [0, 0, 0]})
    f.phase(3, "burst")


# ---------------------------------------------------------------------------- P12 sonar + markers
def sonar():
    f = Fx("fx_p_sonar", P, bounds=(16, 16, (0, 0, 0)))
    for i, (rx, ry) in enumerate(((0, 0), (90, 0), (90, 90))):
        ring(f, f"g_sr{i}", "fade", (0, 0, 0), 16, 0.5, 0.8, 32, "p_glow_band", rx=rx, ry=ry, gap=2)
    ring(f, "t_band", "fade", (0, 0, 0), 15.5, 0.3, 3, 24, "p_air")
    a = f.anim("scan", loop=True)
    for i in range(3):
        spin(a, f"g_sr{i}", 90 * (i + 1))
    f.phase(1, f.default_form(0.3), "scan").phase(2, "scan")

    m = Fx("fx_p_marker", P, bounds=(2, 3, (0, 1, 0)),
           components={"minecraft:nameable": {"always_show": True, "allow_name_tag_renaming": False}})
    dm = oriented(m, "g_diam", "fade", (0, 6, 0), rx=45)
    dm.cbox((0, 6, 0), (3, 3, 3), "p_amber", rotation=(0, 45, 0))
    m.bone("g_halo").ring((0, 6, 0), 5, 0.4, 0.4, 12, "p_glow_band")
    mm = m.anim("bob", loop=True)
    mm.pos("g_diam", [0, "math.sin(q.life_time * 200) * 0.8", 0])
    spin(mm, "g_halo", 120)
    m.phase(1, m.default_form(0.2), "bob").phase(2, "bob")


# ---------------------------------------------------------------------------- P13 crystal + converging field
def crystal():
    f = Fx("fx_p_crystal", P, bounds=(3, 3, (0, 0, 0)))
    f.bone("gem")
    f.bone("up", "gem").crystal((0, 0, 0), 9, 5, "p_amber", "p_amber")
    dn = oriented(f, "down", "gem", (0, 0, 0), rx=180)
    dn.crystal((0, 0, 0), 7, 5, "p_amber", "p_amber")
    ring(f, "g_o1", "gem", (0, 0, 0), 7, 0.4, 0.6, 14, "p_glow_band", rx=70)
    ring(f, "g_o2", "gem", (0, 0, 0), 8, 0.4, 0.6, 14, "p_glow_band", rx=70, ry=90)
    f.bone("g_glow", "gem").solid_cylinder((0, -3, 0), 2.4, 6, "p_core", layers=2)
    a = f.anim("vibrate", loop=True)
    a.pos("gem", ["math.sin(q.life_time * 2400) * 0.25", "math.sin(q.life_time * 150) * 1.2", "math.cos(q.life_time * 2100) * 0.25"])
    a.rot("gem", [0, "q.life_time * 90", 0])
    spin(a, "g_o1", 300)
    spin(a, "g_o2", -260)
    f.phase(1, f.default_form(0.4), "vibrate").phase(2, "vibrate")

    fld = Fx("fx_p_field", P, bounds=(18, 8, (0, 1, 0)))
    for i in range(12):
        fld.model.bone(f"fh{i}", "fade", pivot=(0, 0, 0), rotation=(0, 30 * i, 0))
        fld.model.bone(f"fm{i}", f"fh{i}", pivot=(0, 0, 0))
        y = 6 + (i % 3) * 14
        ring(fld, f"g_fr{i}", f"fm{i}", (0, y, -120), 9 + (i % 3) * 2, 0.8, 1.2, 12, "p_glow_band", rx=90)
    conv = fld.anim("converge", length=2.0, loop="hold_on_last_frame")
    for i in range(12):
        conv.pos(f"fm{i}", {0: [0, 0, 0], 1.8: [0, -(6 + (i % 3) * 14) + 24, 118]})
        conv.scale(f"fm{i}", {0: [1, 1, 1], 1.8: [0.15, 0.15, 0.15]})
        spin(conv, f"g_fr{i}", 400)
    fld.phase(1, fld.default_form(0.4)).phase(2, "converge")


# ---------------------------------------------------------------------------- P14 citadel control ring
def citadel_ring():
    f = Fx("fx_p_citadel_ring", P, bounds=(22, 6, (0, 0, 0)), tex=(128, 256))
    f.bone("rot")
    f.bone("band", "rot").ring((0, 0, 0), 150, 6, 6, 36, "p_copper")
    f.bone("g_inner", "rot").ring((0, 0, 0), 141, 2, 3, 36, "p_glow_band")
    f.bone("t_runes", "rot").ring((0, 0, 0), 146, 1, 8, 36, "p_runes_air")
    pend = f.bone("pendants", "rot")
    for k in range(8):
        a = math.tau * k / 8
        x, z = math.cos(a) * 150, math.sin(a) * 150
        d = oriented(f, f"pd{k}", "pendants", (x, -4, z), rx=180)
        d.crystal((x, -4, z), 22, 7, "p_amber", "p_amber")
    spokes = f.bone("spokes", "rot")
    for k in range(4):
        sb = oriented(f, f"sp{k}", "spokes", (0, 0, 0), ry=45 + 90 * k)
        sb.cbox((0, 0, -75), (3, 2.5, 140), "p_copper_dark")
    f.bone("hub", "rot").hexplate((0, 0, 0), 16, 4, "p_copper", edge_style="p_gold")
    f.bone("g_hubcore", "rot").solid_cylinder((0, -2, 0), 6, 6, "p_core", layers=3)
    form = f.anim("form", length=1.6)
    form.scale("fade", {0: [0.01, 1, 0.01], 1.2: [1.04, 1, 1.04], 1.6: [1, 1, 1]})
    form.pos("fade", {0: [0, 120, 0], 1.6: [0, 0, 0]})
    idle = f.anim("idle", loop=True)
    idle.rot("rot", [0, "q.life_time * 10", 0])
    spin(idle, "g_inner", -30)
    f.phase(1, "form", "idle").phase(2, "idle")
    pul = f.anim("fire", length=0.35)
    pul.scale("g_hubcore", {0: [1, 1, 1], 0.08: [3, 3, 3], 0.35: [1, 1, 1]})
    pul.scale("g_inner", {0: [1, 1, 1], 0.1: [1.03, 1.6, 1.03], 0.35: [1, 1, 1]})
    f.pulse("fire")


# ---------------------------------------------------------------------------- P15 edict layers + fronts
def edict():
    f = Fx("fx_p_layers", P, bounds=(40, 12, (0, 2, 0)), tex=(128, 256))
    n = 12
    for i in range(n):
        r = 24 + i * 23
        f.bone(f"ly{i}")
        ring(f, f"t_ly{i}", f"ly{i}", (0, 6 + (i % 3) * 5, 0), r, 6 + i * 0.4, 1.4, 24 + i * 2, "p_air")
        ring(f, f"g_ly{i}", f"ly{i}", (0, 6 + (i % 3) * 5, 0), r + 4, 0.9, 1.4, 24 + i * 2, "p_glow_band", gap=1.5)
    dom = f.anim("dominion", loop=True)
    for i in range(n):
        dom.rot(f"ly{i}", [0, f"q.life_time * {(14 - i) * (1 if i % 2 else -1)}", 0])
        dom.pos(f"ly{i}", [0, f"math.sin(q.life_time * 80 + {i * 30}) * 1.5", 0])
    form = f.anim("form", length=2.4)
    for i in range(n):
        t0 = i * 0.16
        form.scale(f"ly{i}", {0: [0.01, 1, 0.01], t0: [0.01, 1, 0.01], t0 + 0.4: [1.04, 1, 1.04], t0 + 0.6: [1, 1, 1]})
    f.phase(1, "form", "dominion").phase(2, "dominion")
    comp = f.anim("compress", length=4.2, loop="hold_on_last_frame")
    for i in range(n):
        j = n - 1 - i
        t0 = 0.2 + j * 0.3
        comp.scale(f"ly{i}", {0: [1, 1, 1], t0: [1, 1, 1], t0 + 0.08: [1.06, 2.5, 1.06], t0 + 0.3: [0.04, 3, 0.04]})
    f.phase(3, "compress", "dominion")
    gone = f.anim("gone", loop=True)
    for i in range(n):
        gone.scale(f"ly{i}", [0, 0, 0])
    f.phase(4, "gone")

    fr = Fx("fx_p_front", P, bounds=(48, 24, (0, 4, 0)), tex=(128, 256))
    fr.bone("t_shell").dome((0, 0, 0), 64, "p_air_dense", bands=6, segs=24, thickness=0.8, band=9, cap=False)
    fr.bone("g_edge").ring((0, 1, 0), 64, 3, 3, 32, "p_glow_band")
    fr.bone("g_edge2").ring((0, 30, 0), 56, 1.5, 2, 28, "p_glow_band")
    exp = fr.anim("expand", length=0.9, loop="hold_on_last_frame")
    exp.scale("fade", {0: [0.1, 0.1, 0.1], 0.7: ["v.size * 0 + 1", 1, 1], 0.9: [1.05, 0.6, 1.05]})
    exp.scale("t_shell", {0: [1, 1, 1], 0.6: [1, 1, 1], 0.9: [1.05, 0.05, 1.05]})
    fr.phase(1, "expand").phase(2, "expand")


for build in (lance, piston, blade, salvo, dome, mantle, vise, column, cage, step_ring, rail_ring, sonar, crystal, citadel_ring, edict):
    build()
