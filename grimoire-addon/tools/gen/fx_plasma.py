"""Plasma Magic constructs (Grimoire 04): controlled plasma filaments, magnetic confinement geometry,
white-hot cores. Never flames, never generic lightning bolts."""
import math
from .fxdefs import Fx
from .fxparts import oriented, ring, spin, vibrate
from .fxlib import aim_box, helix_z, polyline, silhouette

P = "plasma"
FIL = ("pl_filament", "pl_magenta", "pl_indigo")
T = 2 * math.pi


# ------------------------------------------------------------------------------------------ PL01 whip
def whip():
    w = Fx("fx_pl_whip", P, bounds=(20, 8, (0, 0, -4)), lifetime=40)
    L = 12.8
    prev = None
    for k in range(10):
        z0 = -k * L
        seg = w.bone(f"g_seg{k}", prev, pivot=(0, 0, z0))
        wd = 1.0 - k * 0.055
        for f in range(3):
            a0 = f * 120 + k * 42
            seg.cbox((math.cos(math.radians(a0)) * 1.3 * wd, math.sin(math.radians(a0)) * 1.3 * wd, z0 - L / 2),
                     (1.1 * wd, 1.1 * wd, L + 0.5), FIL[f], rotation=(0, 0, a0 + 25))
        seg.cbox((0, 0, z0 - L / 2), (0.6 * wd, 0.6 * wd, L), "pl_core")
        prev = f"g_seg{k}"
    tip = w.bone("g_tip", prev, pivot=(0, 0, -10 * L))
    for i, (ry, rx) in enumerate(((0, 0), (28, 12), (-28, -10), (14, -24))):
        b = w.bone(f"g_br{i}", "g_tip", pivot=(0, 0, -10 * L), rotation=(rx, ry, 0))
        b.cbox((0, 0, -10 * L - 3.5), (0.7, 0.7, 7 - i), FIL[i % 3])
    w.bone("g_knot", None, pivot=(0, 0, 0)).cbox((0, 0, 0), (1.6, 1.6, 1.6), "pl_core", rotation=(45, 45, 0))
    form = w.anim("form", length=0.5)
    for k in range(10):
        t0 = 0.035 * k
        form.scale(f"g_seg{k}", {0: [0.01, 0.01, 0.01], t0 + 0.001: [0.01, 0.01, 0.01], t0 + 0.09: [1, 1, 1]})
        form.rot(f"g_seg{k}", {0: [0, (k % 3 - 1) * 40, 0], t0 + 0.12: [0, 0, 0]})
    w.phase(1, "form")
    ready = w.anim("ready", loop=True)
    for k in range(1, 10):
        ready.rot(f"g_seg{k}", [f"math.sin(q.life_time * 240 - {k * 30}) * 5", f"math.sin(q.life_time * 300 - {k * 40}) * 7", 0])
    vibrate(ready, "g_tip", 0.25, 14)
    w.phase(2, "ready")

    def sweep(name, axis, a0, a1, amp):
        a = w.anim(name, length=0.42, loop="hold_on_last_frame")
        idx = 0 if axis == "x" else 1
        k0 = [0, 0, 0]
        k1 = [0, 0, 0]
        k0[idx], k1[idx] = a0, a1
        a.rot("g_seg0", {0: k0, 0.34: k1, 0.42: k1})
        for k in range(1, 10):
            e = f"math.sin(q.life_time * 1100 - {k * 55}) * {amp}"
            a.rot(f"g_seg{k}", [e, 0, 0] if axis == "x" else [0, e, 0])
        vibrate(a, "g_tip", 0.4, 20)
        return name
    w.phase(3, sweep("sweep_a", "y", -80, 80, 13))
    w.phase(4, sweep("sweep_b", "y", 80, -80, 13))
    w.phase(5, sweep("sweep_c", "x", -70, 30, 11))
    dis = w.anim("dissolve", length=0.5)
    for k in range(10):
        dis.scale(f"g_seg{k}", {0: [1, 1, 1], 0.05 + 0.03 * (9 - k): [1.6, 1.6, 0.4], 0.45: [0, 0, 0]})
    w.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ PL02 helix borer
def borer():
    b = Fx("fx_pl_borer", P, bounds=(4, 4, (0, 0, 0)), lifetime=100)
    b.bone("g_core").cbox((0, 0, -3), (2.4, 2.4, 22), "pl_core")
    tipb = b.bone("g_tip", pivot=(0, 0, -14))
    for i, (w_, z) in enumerate(((4.2, -15), (3.0, -18), (1.8, -21), (0.8, -23.5))):
        tipb.cbox((0, 0, z), (w_, w_, 3.2), "pl_core" if i else "pl_titanium", rotation=(0, 0, 45))
    ha = b.bone("g_helix_a", pivot=(0, 0, 0))
    helix_z(ha, (0, 0, 9), 4.4, 24, 3.2, 34, "pl_filament", 0.0, 0.9)
    hb = b.bone("g_helix_b", pivot=(0, 0, 0))
    helix_z(hb, (0, 0, 9), 4.4, 24, 3.2, 34, "pl_magenta", math.pi, 0.9)
    ring(b, "collar", b.top, (0, 0, 9), 6.2, 1.0, 2.0, 12, "pl_titanium", rx=90)
    ring(b, "collar2", b.top, (0, 0, 4), 5.4, 0.8, 1.2, 12, "pl_dark_metal", rx=90)
    form = b.anim("form", length=0.4)
    form.scale("g_helix_a", {0: [3, 3, 0.2], 0.4: [1, 1, 1]}).scale("g_helix_b", {0: [3, 3, 0.2], 0.4: [1, 1, 1]})
    form.scale("g_core", {0: [0.01, 0.01, 0.01], 0.3: [1.2, 1.2, 1.2], 0.4: [1, 1, 1]})
    b.phase(1, "form", "spin")
    sp = b.anim("spin", loop=True)
    sp.rot("g_helix_a", [0, 0, "q.life_time * 720"]).rot("g_helix_b", [0, 0, "-q.life_time * 720"])
    sp.rot("collar", [0, "q.life_time * 200", 0])
    b.phase(2, "spin")
    dr = b.anim("drill", loop=True)
    dr.rot("g_helix_a", [0, 0, "q.life_time * 1700"]).rot("g_helix_b", [0, 0, "-q.life_time * 1700"])
    dr.pos("fade", [f"math.sin(q.life_time * 3000) * 0.3", f"math.cos(q.life_time * 2600) * 0.3", "math.sin(q.life_time * 1800) * 1.2"])
    vibrate(dr, "g_tip", 0.12, 20)
    b.phase(3, "drill")
    un = b.anim("unwind", length=0.6, loop="hold_on_last_frame")
    un.scale("g_helix_a", {0: [1, 1, 1], 0.6: [3.2, 3.2, 1.6]}).scale("g_helix_b", {0: [1, 1, 1], 0.6: [3.2, 3.2, 1.6]})
    un.rot("g_helix_a", {0: [0, 0, 0], 0.6: [0, 0, 260]}).rot("g_helix_b", {0: [0, 0, 0], 0.6: [0, 0, -260]})
    un.scale("g_core", {0: [1, 1, 1], 0.5: [0, 0, 0]}).scale("g_tip", {0: [1, 1, 1], 0.3: [0, 0, 0]})
    b.phase(4, "unwind")


# ------------------------------------------------------------------------------------------ PL03 prominence arches
def prominence():
    f = Fx("fx_pl_prominence", P, bounds=(12, 9, (0, 3, 0)), lifetime=120)
    R = 56
    for k, ry in enumerate((0, 38)):
        g = f.bone(f"arch{k}", pivot=(0, 0, 0), rotation=(0, ry, 0))
        ring(f, f"t_arch{k}", f"arch{k}", (0, 0, 0), R, 6, 6, 20, "pl_tube", rx=90, start=0, arc=180)
        for j, (dr, st) in enumerate(((-2.6, FIL[k]), (2.6, FIL[(k + 1) % 3]))):
            ring(f, f"g_fil{k}{j}", f"arch{k}", (0, 0, 0), R + dr, 0.8, 0.8, 24, st, rx=90, start=0, arc=180)
        for sgn in (-1, 1):
            g2 = f.bone(f"g_foot{k}{'l' if sgn > 0 else 'r'}", f"arch{k}", pivot=(sgn * R, 0, 0))
            g2.cbox((sgn * R, 1, 0), (9, 2, 9), "pl_core", rotation=(0, 45, 0))
    er = f.anim("erupt", length=0.7, loop="hold_on_last_frame")
    for k in range(2):
        er.scale(f"arch{k}", {0: [0.25, 0.01, 0.25], 0.45: [1.05, 1.1, 1.05], 0.7: [1, 1, 1]})
    f.phase(1, "erupt")
    tw = f.anim("intertwine", loop=True)
    tw.rot("arch0", [f"math.sin(q.life_time * 90) * 8", "math.sin(q.life_time * 60) * 14", 0])
    tw.rot("arch1", [f"-math.sin(q.life_time * 90) * 8", "38 - math.sin(q.life_time * 60) * 14", 0])
    for k in range(2):
        for j in range(2):
            vibrate(tw, f"g_fil{k}{j}", 0.05, 6, j * 90)
    f.phase(2, "intertwine")
    co = f.anim("collapse", length=0.5, loop="hold_on_last_frame")
    co.rot("arch0", {0: [0, 0, 0], 0.4: [82, 0, 0]}).rot("arch1", {0: [0, 38, 0], 0.4: [-82, 38, 0]})
    co.scale("arch0", {0: [1, 1, 1], 0.4: [1.2, 0.8, 1.2]}).scale("arch1", {0: [1, 1, 1], 0.4: [1.2, 0.8, 1.2]})
    f.phase(3, "collapse")


# ------------------------------------------------------------------------------------------ PL04 membranes + flare
def membrane():
    m = Fx("fx_pl_membrane", P, bounds=(7, 6, (0, 1.2, 0)), lifetime=120)
    for side, sgn in (("l", 1), ("r", -1)):
        half = m.bone(f"half_{side}", pivot=(0, 0, 0))
        m.bone(f"t_mem_{side}", f"half_{side}", pivot=(0, 0, 0)).cbox((sgn * 13, 18, 0), (26, 36, 0.3), "pl_membrane")
        e = m.bone(f"g_edge_{side}", f"half_{side}", pivot=(0, 0, 0))
        e.cbox((sgn * 26, 18, 0), (0.7, 36, 0.7), FIL[0])
        e.cbox((sgn * 13, 36, 0), (26, 0.7, 0.7), FIL[1])
        e.cbox((sgn * 13, 0, 0), (26, 0.7, 0.7), FIL[2])
        sp = m.bone(f"g_spark_{side}", f"half_{side}", pivot=(0, 0, 0))
        sp.cbox((sgn * 26, 0, 0), (1.6, 1.6, 1.6), "pl_core", rotation=(45, 45, 0))
    m.bone("g_spine").cbox((0, 18, 0), (1.2, 37, 1.2), "pl_core")
    dep = m.anim("deploy", length=0.5)
    dep.rot("half_l", {0: [0, 85, 0], 0.5: [0, 0, 0]}).rot("half_r", {0: [0, -85, 0], 0.5: [0, 0, 0]})
    dep.scale("fade", {0: [0.2, 1, 0.2], 0.5: [1, 1, 1]})
    m.phase(1, "deploy")
    sw = m.anim("sweep", loop=True)
    sw.rot("half_l", [0, "math.max(0, math.sin(q.life_time * 140)) * 55", "math.sin(q.life_time * 90) * 6"])
    sw.rot("half_r", [0, "-math.max(0, math.sin(q.life_time * 140)) * 55", "-math.sin(q.life_time * 90) * 6"])
    for side in ("l", "r"):
        sw.pos(f"g_spark_{side}", [0, "math.mod(q.life_time * 60, 36)", 0])
    m.phase(2, sw.ident.split(".")[-1])
    fl = Fx("fx_pl_flare", P, bounds=(4, 6, (0, 2, 0)), lifetime=40)
    col = fl.bone("g_column")
    col.cbox((0, 14, 0), (3, 28, 3), "pl_core")
    for k in range(6):
        sb = fl.bone(f"g_spike{k}", pivot=(0, 2, 0), rotation=(25 + (k % 2) * 20, k * 60, 0))
        sb.cbox((0, 10, 0), (0.8, 18 - (k % 3) * 3, 0.8), FIL[k % 3])
    ring(fl, "g_halo", fl.top, (0, 3, 0), 9, 1, 1, 14, "pl_magenta")
    a = fl.anim("form", length=0.3)
    a.scale("fade", {0: [0.3, 0.01, 0.3], 0.12: [1.3, 1.4, 1.3], 0.3: [1, 1, 1]})
    fl.phase(1, "form", "throb")
    th = fl.anim("throb", loop=True)
    vibrate(th, "g_column", 0.15, 10)
    th.rot("g_halo", [0, "q.life_time * 300", 0])


# ------------------------------------------------------------------------------------------ PL05 stellarator ward
def stellarator():
    s = Fx("fx_pl_stellarator", P, bounds=(6, 3, (0, 1, 0)), lifetime=600)
    R, N = 40, 24
    tube = s.bone("t_tube", pivot=(0, 14, 0))
    ribs = s.bone("ribs", pivot=(0, 14, 0))
    chord = 2 * R * math.tan(math.pi / N) + 0.6
    for k in range(N):
        th = k * 360 / N
        x, z = math.cos(math.radians(th)) * R, math.sin(math.radians(th)) * R
        tw = k * 360 * 2 / N
        yaw = -(th + 90)
        tube.cbox((x, 14, z), (chord, 7, 3.2), "pl_tube", rotation=(tw, yaw, 0))
        if k % 3 == 0:
            ribs.cbox((x, 14, z), (1.0, 9, 5.4), "pl_titanium", rotation=(tw, yaw, 0))
    for i in range(3):
        st = s.bone(f"g_stream{i}", pivot=(0, 14, 0))
        for j in range(5):
            th = math.radians(i * 120 + j * 6)
            st.cbox((math.cos(th) * R, 14 + math.sin(th * 2 + i) * 2, math.sin(th) * R), (1.6, 1.6, 1.6), FIL[i], rotation=(45, 45, 0))
    form = s.anim("form", length=0.6)
    form.scale("t_tube", {0: [0.2, 3, 0.2], 0.6: [1, 1, 1]}).rot("t_tube", {0: [0, -180, 0], 0.6: [0, 0, 0]})
    form.scale("ribs", {0: [1.6, 0.01, 1.6], 0.6: [1, 1, 1]})
    s.phase(1, "form", "run")
    run = s.anim("run", loop=True)
    for i in range(3):
        run.rot(f"g_stream{i}", [f"math.sin(q.life_time * {200 + i * 40}) * 6", f"q.life_time * {220 + i * 45}", 0])
    run.rot("ribs", [0, "q.life_time * 10", 0])
    s.phase(2, "run")
    pu = s.anim("pulse", length=0.3)
    pu.scale("t_tube", {0: [1, 1, 1], 0.08: [1.08, 1.5, 1.08], 0.3: [1, 1, 1]})
    s.pulse("pulse")


# ------------------------------------------------------------------------------------------ PL06 corona molt
def molt():
    m = Fx("fx_pl_molt", P, bounds=(2, 3, (0, 1, 0)), lifetime=700)
    m.bone("shell", pivot=(0, 0, 0))
    silhouette(m, "t_", "shell", "pl_membrane_dense", 1.0, inflate=1.2)
    silhouette(m, "g_", "shell", "pl_edge", 1.0, inflate=1.6)
    fit = m.anim("form", length=0.5)
    fit.scale("shell", {0: [1.4, 1.4, 1.4], 0.5: [1, 1, 1]})
    m.phase(1, "form", "idle")
    idle = m.anim("idle", loop=True)
    vibrate(idle, "shell", 0.012, 7)
    m.phase(2, "idle")
    sep = m.anim("molt", length=0.8, loop="hold_on_last_frame")
    sep.pos("shell", {0: [0, 0, 0], 0.8: [0, 2, 10]})
    sep.scale("shell", {0: [1, 1, 1], 0.25: [1.25, 1.25, 1.25], 0.8: [2.4, 2.4, 2.4]})
    sep.rot("shell", {0: [0, 0, 0], 0.8: [0, 25, 0]})
    m.phase(3, "molt")


# ------------------------------------------------------------------------------------------ PL07 fieldline harp
def harp():
    a = Fx("fx_pl_anchor", P, bounds=(2, 3, (0, 1, 0)), lifetime=600)
    body = a.bone("body", pivot=(0, 16, 0))
    for i, (w_, y) in enumerate(((5, 16), (3.6, 19.5), (2.2, 22.5), (3.6, 12.5), (2.2, 9.5), (1, 7.5))):
        body.cbox((0, y, 0), (w_, 3.2, w_), "pl_dark_metal" if i % 2 else "pl_ceramic", rotation=(0, 45, 0))
    a.bone("g_core", "body", pivot=(0, 16, 0)).cbox((0, 16, 0), (2.4, 2.4, 2.4), "pl_core", rotation=(45, 45, 0))
    ring(a, "plates", "body", (0, 16, 0), 6, 0.6, 1.4, 8, "pl_titanium", gap=18)
    ring(a, "g_ring", "body", (0, 16, 0), 4.4, 0.4, 0.4, 12, "pl_magenta", rx=90)
    form = a.anim("form", length=0.4)
    form.pos("body", {0: [0, 14, 0], 0.4: [0, 0, 0]}).scale("body", {0: [0.01, 0.01, 0.01], 0.3: [1.2, 1.2, 1.2], 0.4: [1, 1, 1]})
    a.phase(1, "form", "idle")
    idle = a.anim("idle", loop=True)
    idle.rot("plates", [0, "q.life_time * 90", 0]).rot("g_ring", [0, "q.life_time * -160", 0])
    idle.pos("body", [0, "math.sin(q.life_time * 120) * 0.6", 0])
    a.phase(2, "idle")

    s = Fx("fx_pl_string", P, bounds=(3, 3, (0, 0, 0)), lifetime=600)
    st = s.bone("stretch", pivot=(0, 0, 0))
    s.bone("g_main", "stretch", pivot=(0, 0, 0)).cbox((0, 0, -8), (0.5, 0.5, 16), "pl_filament")
    for i in range(2):
        b = s.bone(f"g_strand{i}", "stretch", pivot=(0, 0, 0), rotation=(0, 0, i * 90))
        b.cbox((0, 0.55, -8), (0.25, 0.25, 16), FIL[1 + i])
    s.bone("g_bead", "stretch", pivot=(0, 0, 0)).cbox((0, 0, 0), (1.6, 1.6, 0.6), "pl_core")
    t = s.anim("tension", length=0.5)
    t.scale("stretch", {0: [0.1, 0.1, 1], 0.5: [1, 1, 1]}).scale("g_bead", [0, 0, 0])
    s.phase(1, "tension")
    vib = s.anim("vibrate", loop=True)
    vib.scale("g_main", ["1 + math.sin(q.life_time * 3600) * 0.4", "1 + math.cos(q.life_time * 3100) * 0.4", 1])
    vib.rot("g_strand0", [0, 0, "q.life_time * 400"]).rot("g_strand1", [0, 0, "-q.life_time * 400"])
    vib.scale("g_bead", [0, 0, 0])
    s.phase(2, "vibrate")
    pul = s.anim("pulse", length=0.35)
    pul.pos("g_bead", {0: [0, 0, 0], 0.3: [0, 0, -16]}).scale("g_bead", {0: [1, 1, 1], 0.3: [2, 2, 2], 0.35: [0, 0, 0]})
    pul.scale("g_main", {0: [1, 1, 1], 0.1: [3, 3, 1], 0.35: [1, 1, 1]})
    s.pulse("pulse")


# ------------------------------------------------------------------------------------------ PL08 polarity pylons
def pylon():
    p = Fx("fx_pl_pylon", P, bounds=(3, 6, (0, 2.5, 0)), lifetime=400)
    base = p.bone("base")
    base.cbox((0, 1, 0), (12, 2, 12), "pl_dark_metal", rotation=(0, 45, 0))
    base.cbox((0, 2.6, 0), (8, 1.2, 8), "pl_titanium")
    p.bone("t_core").cbox((0, 36, 0), (4.4, 64, 4.4), "pl_tube")
    for k in range(4):
        seg = p.bone(f"seg{k}", pivot=(0, 12 + k * 16, 0))
        for q in range(3):
            ang = q * 120
            seg.cbox((math.cos(math.radians(ang)) * 4.6, 12 + k * 16, math.sin(math.radians(ang)) * 4.6), (1.4, 12, 3.2),
                     "pl_titanium" if q % 2 else "pl_ceramic", rotation=(0, -ang, 0))
    for name, st, ph in (("g_attract", "pl_magenta", 0.0), ("g_repel", "pl_indigo", math.pi)):
        hb = p.bone(name, pivot=(0, 36, 0))
        for i in range(30):
            t = i / 29
            a = ph + t * 5 * T
            hb.cbox((math.cos(a) * 1.6, 6 + t * 60, math.sin(a) * 1.6), (0.9, 1.4, 0.9), st)
    top = p.bone("g_top", pivot=(0, 70, 0))
    top.cbox((0, 71, 0), (3.6, 3.6, 3.6), "pl_core", rotation=(45, 0, 45))
    ring(p, "g_crown", "g_top", (0, 70, 0), 5, 0.5, 0.5, 10, "pl_filament")
    form = p.anim("form", length=0.6)
    for k in range(4):
        form.scale(f"seg{k}", {0: [0, 0, 0], 0.1 + k * 0.1: [0, 0, 0], 0.25 + k * 0.1: [1, 1, 1]})
    form.scale("t_core", {0: [1, 0, 1], 0.6: [1, 1, 1]})
    p.phase(1, "form", "rest")
    rest = p.anim("rest", loop=True)
    rest.scale("g_attract", [0.6, 0.6, 0.6]).scale("g_repel", [0, 0, 0])
    for k in range(4):
        rest.rot(f"seg{k}", [0, f"q.life_time * {(30 + k * 10) * (1 if k % 2 else -1)}", 0])
    p.phase(2, "rest")
    att = p.anim("attract", loop=True)
    att.rot("g_attract", [0, "q.life_time * 900", 0]).scale("g_repel", [0, 0, 0]).scale("g_attract", [1.3, 1, 1.3])
    att.rot("g_crown", [0, "-q.life_time * 400", 0])
    for k in range(4):
        att.rot(f"seg{k}", [0, f"q.life_time * {(120 + k * 30) * (1 if k % 2 else -1)}", 0])
    p.phase(3, "attract")
    rep = p.anim("repel", loop=True)
    rep.rot("g_repel", [0, "-q.life_time * 900", 0]).scale("g_attract", [0, 0, 0]).scale("g_repel", [1.3, 1, 1.3])
    rep.scale("g_top", ["1.4 + math.sin(q.life_time * 900) * 0.2"] * 3)
    for k in range(4):
        rep.pos(f"seg{k}", [0, 0, 0]).scale(f"seg{k}", [1.25, 1, 1.25])
    p.phase(4, "repel")


# ------------------------------------------------------------------------------------------ PL09 static horizon
def horizon():
    h = Fx("fx_pl_horizon", P, bounds=(24, 4, (0, 0, 0)), lifetime=400)
    S, N = 40, 8
    mem = h.bone("t_mem")
    for i in range(N):
        for j in range(N):
            mem.cbox(((i - N / 2 + 0.5) * S, 0, (j - N / 2 + 0.5) * S), (S + 0.2, 0.3, S + 0.2), "pl_membrane")
    fa = h.bone("g_flow_a")
    fb = h.bone("g_flow_b")
    for k in range(-8, 9):
        fa.cbox((0, 0.6, k * 18), (S * N, 0.5, 0.5), "pl_indigo")
        fb.cbox((k * 18, 0.9, 0), (0.5, 0.5, S * N), "pl_filament")
    ed = h.bone("g_edges")
    half = S * N / 2
    for sgn in (-1, 1):
        ed.cbox((sgn * half, 0.5, 0), (1.2, 1.2, S * N), "pl_magenta")
        ed.cbox((0, 0.5, sgn * half), (S * N, 1.2, 1.2), "pl_magenta")
    form = h.anim("form", length=0.8)
    form.scale("fade", {0: [0.01, 1, 0.01], 0.8: [1, 1, 1]})
    h.phase(1, "form", "flow")
    flow = h.anim("flow", loop=True)
    flow.pos("g_flow_a", [0, 0, "math.mod(q.life_time * 14, 18)"]).pos("g_flow_b", ["-math.mod(q.life_time * 14, 18)", 0, 0])
    h.phase(2, "flow")
    rip = h.anim("ripple", length=0.4)
    rip.pos("t_mem", {0: [0, 0, 0], 0.1: [0, 2.5, 0], 0.4: [0, 0, 0]})
    rip.scale("g_flow_a", {0: [1, 1, 1], 0.1: [1, 4, 1], 0.4: [1, 1, 1]}).scale("g_flow_b", {0: [1, 1, 1], 0.15: [1, 4, 1], 0.4: [1, 1, 1]})
    h.pulse("ripple")
    col = h.anim("dissolve", length=0.8)
    col.scale("fade", {0: [1, 1, 1], 0.7: [0.01, 1, 0.01]})
    col.scale("g_edges", {0: [1, 1, 1], 0.3: [1, 3, 1], 0.7: [0, 0, 0]})
    h.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ PL10 ion skates
def skates():
    s = Fx("fx_pl_skates", P, bounds=(2, 1, (0, 0, 0)), lifetime=240)
    fins = s.bone("stretch", pivot=(0, 1, 3))
    for side, x in (("l", 2.4), ("r", -2.4)):
        r = s.bone(f"runner_{side}", pivot=(x, 0, 0))
        r.cbox((x, 0.4, 0), (1.2, 0.8, 10), "pl_titanium")
        r.cbox((x, 1.2, 0), (0.6, 0.8, 7), "pl_ceramic")
        s.bone(f"g_blade_{side}", f"runner_{side}", pivot=(x, 0, 0)).cbox((x, 0.05, 0), (0.5, 0.25, 10.4), "pl_core")
        fb = s.bone(f"g_fin_{side}", "stretch", pivot=(x, 1, 3))
        for i, (rx, h) in enumerate(((-12, 1.4), (-26, 1.0))):
            fb.cbox((x, 1.4 + 0.9 * i, 3 + 4.5), (0.3, h, 9), FIL[i], rotation=(rx, 0, 0))
    form = s.anim("form", length=0.3)
    form.scale("fade", {0: [0.01, 0.01, 0.01], 0.3: [1, 1, 1]})
    s.phase(1, "form", "glide")
    gl = s.anim("glide", loop=True)
    gl.scale("stretch", [1, "1 + math.sin(q.life_time * 1200) * 0.12", 1])
    s.phase(2, "glide")
    for n, sgn in ((3, 1), (4, -1)):
        tl = s.anim(f"turn{n}", loop=True)
        tl.rot("fade", [0, 0, sgn * 14]).rot("g_fin_l", [0, sgn * 22, 0]).rot("g_fin_r", [0, sgn * 22, 0])
        s.phase(n, f"turn{n}")


# ------------------------------------------------------------------------------------------ PL11 prominence sling + tail
def sling():
    f = Fx("fx_pl_sling", P, bounds=(6, 5, (0, 2, 0)), lifetime=80)
    f.bone("frame", pivot=(0, 0, 0))
    stem = f.bone("g_stem", "frame", pivot=(0, 0, 0))
    polyline(stem, [(0, 0, 0), (0, 10, 2), (0, 18, 3)], 2.2, "pl_core")
    for side, sgn in (("l", 1), ("r", -1)):
        arm = f.bone(f"g_arm_{side}", "frame", pivot=(0, 18, 3))
        pts = [(sgn * (math.sin(t / 8 * 1.3) * 26), 18 + t * 3.0, 3 + math.sin(t / 8 * 2.2) * 3) for t in range(9)]
        polyline(arm, pts, 1.8, FIL[0 if sgn > 0 else 1])
        polyline(f.bone(f"arm_shell_{side}", f"g_arm_{side}", pivot=(0, 18, 3)), pts, 2.8, "pl_ceramic")
    tips = {"l": (26 * math.sin(1.3), 42, 3 + 3 * math.sin(2.2)), "r": (-26 * math.sin(1.3), 42, 3 + 3 * math.sin(2.2))}
    cradle = f.bone("g_cradle", "frame", pivot=(0, 34, 3))
    cradle.cbox((0, 34, 3), (5, 3, 3), "pl_core")
    rest = (0, 34, 3)
    for side in ("l", "r"):
        aim_box(f.bone(f"g_band_{side}", "frame", pivot=rest), tips[side], rest, 0.7, "pl_magenta")
    form = f.anim("form", length=0.5)
    form.scale("frame", {0: [0.01, 0.01, 0.01], 0.35: [1.1, 1.1, 1.1], 0.5: [1, 1, 1]})
    f.phase(1, "form")
    ten = f.anim("tension", length=0.5, loop="hold_on_last_frame")
    ten.pos("g_cradle", {0: [0, 0, 0], 0.5: [0, -4, 22]})
    for side, sgn in (("l", 1), ("r", -1)):
        ten.rot(f"g_band_{side}", {0: [0, 0, 0], 0.5: [-30, sgn * 40, 0]}).scale(f"g_band_{side}", {0: [1, 1, 1], 0.5: [1, 1.5, 1]})
        ten.rot(f"g_arm_{side}", {0: [0, 0, 0], 0.5: [12, 0, sgn * -8]})
    vibrate(ten, "g_cradle", 0.15, 16)
    f.phase(2, "tension")
    rel = f.anim("release", length=0.4, loop="hold_on_last_frame")
    rel.pos("g_cradle", {0: [0, -4, 22], 0.08: [0, 2, -30], 0.4: [0, 0, 0]})
    for side, sgn in (("l", 1), ("r", -1)):
        rel.rot(f"g_band_{side}", {0: [-30, sgn * 40, 0], 0.08: [25, -sgn * 30, 0], 0.4: [0, 0, 0]})
        rel.rot(f"g_arm_{side}", {0: [12, 0, sgn * -8], 0.1: [-10, 0, sgn * 6], 0.4: [0, 0, 0]})
    f.phase(3, "release")

    t = Fx("fx_pl_tail", P, bounds=(3, 3, (0, 1, 2)), lifetime=120)
    for i in range(3):
        b = t.bone(f"g_strand{i}", pivot=(0, 14, 0))
        helix_z(b, (0, 14, 2), 2.2 + i * 0.6, 60, 2.4, 22, FIL[i], i * T / 3, 1.2 - i * 0.2, direction=1)
    sp = t.anim("twist", loop=True)
    for i in range(3):
        sp.rot(f"g_strand{i}", [0, 0, f"q.life_time * {(500 + i * 120) * (1 if i % 2 else -1)}"])
    t.phase(1, t.default_form(0.2), "twist").phase(2, "twist")


# ------------------------------------------------------------------------------------------ PL12 auroral manta
def manta():
    m = Fx("fx_pl_manta", P, bounds=(7, 3, (0, 0.5, 0)), tex=(128, 256), lifetime=600)
    body = m.bone("body", pivot=(0, 8, 0))
    body.cbox((0, 8, 0), (12, 4.2, 22), "pl_ceramic")
    body.cbox((0, 8.6, -12), (9, 3, 6), "pl_ceramic")
    body.cbox((0, 10.4, 2), (6, 1.2, 14), "pl_dark_metal")
    m.bone("g_spine", "body", pivot=(0, 8, 0)).cbox((0, 10.6, 0), (1.2, 0.6, 24), "pl_core")
    for side, sgn in (("l", 1), ("r", -1)):
        m.bone(f"g_eye_{side}", "body", pivot=(sgn * 4, 9, -13)).cbox((sgn * 4.6, 9, -13.5), (0.8, 1.2, 1.6), "pl_core")
        cf = m.bone(f"cephalic_{side}", "body", pivot=(sgn * 3.4, 8, -15), rotation=(0, sgn * -14, 0))
        cf.cbox((sgn * 3.4, 6.8, -18.5), (1.6, 4, 6), "pl_ceramic", rotation=(20, 0, 0))
        prev = "body"
        x0 = 6
        for k, (w_, ln, st) in enumerate(((14, 22, "pl_membrane_dense"), (12, 16, "pl_membrane_dense"), (10, 9, "pl_membrane"))):
            wb = m.bone(f"wing_{side}{k}", prev, pivot=(sgn * x0, 8, 0))
            m.bone(f"t_wing_{side}{k}", f"wing_{side}{k}", pivot=(sgn * x0, 8, 0)).cbox((sgn * (x0 + w_ / 2), 8, -2 + k * 2), (w_, 1.4, ln), st)
            ch = m.bone(f"g_ch_{side}{k}", f"wing_{side}{k}", pivot=(sgn * x0, 8, 0))
            ch.cbox((sgn * (x0 + w_ / 2), 8.8, -2 + k * 2 - ln * 0.2), (w_, 0.3, 0.4), FIL[k])
            ch.cbox((sgn * (x0 + w_ / 2), 8.8, -2 + k * 2 + ln * 0.15), (w_ * 0.8, 0.3, 0.4), FIL[(k + 1) % 3])
            ch.cbox((sgn * (x0 + w_), 8.4, -2 + k * 2), (0.5, 0.5, ln * 0.8), FIL[2])
            prev = f"wing_{side}{k}"
            x0 += w_
    prev = "body"
    z = 11
    for k in range(5):
        tb = m.bone(f"tail{k}", prev, pivot=(0, 8, z))
        tb.cbox((0, 8, z + 3), (1.6 - k * 0.22, 1.2 - k * 0.15, 6), "pl_ceramic")
        prev = f"tail{k}"
        z += 6
    m.bone("g_barb", prev, pivot=(0, 8, z)).cbox((0, 8, z + 1.6), (1.4, 1.4, 3.2), "pl_core", rotation=(0, 0, 45))
    asm = m.anim("form", length=1.2)
    asm.scale("fade", {0: [0.05, 0.05, 0.05], 0.7: [0.8, 1.2, 0.8], 1.2: [1, 1, 1]})
    for side, sgn in (("l", 1), ("r", -1)):
        asm.rot(f"wing_{side}0", {0: [0, 0, sgn * -80], 0.9: [0, 0, sgn * 10], 1.2: [0, 0, 0]})
        asm.rot(f"wing_{side}1", {0: [0, 0, sgn * -60], 1.0: [0, 0, 0]})
    m.phase(1, "form", "swim")
    swim = m.anim("swim", loop=True)
    for side, sgn in (("l", 1), ("r", -1)):
        for k, amp in enumerate((16, 20, 26)):
            swim.rot(f"wing_{side}{k}", [0, 0, f"{sgn} * math.sin(q.life_time * 220 - {k * 45}) * {amp}"])
    for k in range(5):
        swim.rot(f"tail{k}", [f"math.sin(q.life_time * 220 - {k * 40}) * 5", f"math.sin(q.life_time * 160 - {k * 50}) * 9", 0])
    swim.pos("body", [0, "math.sin(q.life_time * 220) * 0.8", 0])
    m.phase(2, "swim")
    dive = m.anim("dive", loop=True)
    for side, sgn in (("l", 1), ("r", -1)):
        dive.rot(f"wing_{side}0", [0, sgn * 28, sgn * -24]).rot(f"wing_{side}1", [0, sgn * 10, sgn * -12]).rot(f"wing_{side}2", [0, 0, sgn * -10])
    for k in range(5):
        dive.rot(f"tail{k}", [-6, f"math.sin(q.life_time * 500 - {k * 40}) * 4", 0])
    m.phase(3, "dive")
    strike = m.anim("strike", length=0.5)
    for k in range(5):
        strike.rot(f"tail{k}", {0: [0, 0, 0], 0.15: [-30 + k * 4, 0, 0], 0.3: [26 - k * 3, 0, 0], 0.5: [0, 0, 0]})
    strike.scale("g_barb", {0: [1, 1, 1], 0.25: [2.4, 2.4, 2.4], 0.5: [1, 1, 1]})
    m.pulse("strike")
    dis = m.anim("dissolve", length=0.9)
    dis.scale("fade", {0: [1, 1, 1], 0.3: [1.1, 0.9, 1.1], 0.85: [0, 0, 0]})
    for side, sgn in (("l", 1), ("r", -1)):
        dis.rot(f"wing_{side}0", {0: [0, 0, 0], 0.8: [0, 0, sgn * 70]})
    m.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ PL13 reconnection
def reconnection():
    f = Fx("fx_pl_fieldloop", P, bounds=(8, 7, (0, 2.5, 0)), lifetime=200)
    f.bone("loops", pivot=(0, 0, 0))
    for k, (r, ry) in enumerate(((48, 0), (40, 30), (32, 60))):
        g = f.bone(f"loop{k}", "loops", pivot=(0, 0, 0), rotation=(0, ry, 0))
        ring(f, f"g_lf{k}", f"loop{k}", (0, 0, 0), r, 1.1, 1.1, 26, FIL[k], rx=90, start=0, arc=180)
        ring(f, f"t_lt{k}", f"loop{k}", (0, 0, 0), r, 3.4, 3.4, 18, "pl_tube", rx=90, start=0, arc=180)
    f.bone("g_feet", "loops").cbox((0, 0.5, 0), (4, 1, 4), "pl_core")
    f.phase(1, f.default_form(0.6))
    for n, sgn in ((2, 1), (3, -1)):
        a = f.anim(f"twist{n}", loop=True)
        a.rot("loops", [0, f"q.life_time * {sgn * 60}", 0])
        for k in range(3):
            vibrate(a, f"g_lf{k}", 0.04, 5, k * 60)
        f.phase(n, f"twist{n}")
    rup = f.anim("rupture", length=0.6, loop="hold_on_last_frame")
    for k in range(3):
        rup.rot(f"loop{k}", {0: [0, 0, 0], 0.15: [0, 0, (-1) ** k * 25], 0.6: [90, 0, (-1) ** k * 60]})
        rup.scale(f"loop{k}", {0: [1, 1, 1], 0.15: [1.4, 0.7, 1.4], 0.6: [0.3, 1.6, 0.3]})
    f.phase(4, "rupture")

    x = Fx("fx_pl_xpoint", P, bounds=(5, 5, (0, 0, 0)), lifetime=200)
    for k, rz in enumerate((40, -40)):
        ring(x, f"g_arc{k}", x.top, (0, 0, 0), 30, 1.4, 1.4, 16, FIL[k], rx=90, start=-60 + rz, arc=120)
        ring(x, f"g_arcb{k}", x.top, (0, 0, 0), 30, 1.4, 1.4, 16, FIL[k], rx=90, start=120 + rz, arc=120)
    core = x.bone("g_core")
    for i, s_ in enumerate((6, 4.6, 3.2)):
        core.cbox((0, 0, 0), (s_, s_, s_), "pl_core", rotation=(i * 30, i * 45, 0))
    for k in range(8):
        x.bone(f"g_spk{k}", pivot=(0, 0, 0), rotation=(0, 0, k * 45)).cbox((0, 8, 0), (0.6, 10, 0.6), FIL[k % 3])
    a = x.anim("form", length=0.4)
    a.scale("fade", {0: [0.01, 0.01, 0.01], 0.4: [0.6, 0.6, 0.6]})
    x.phase(1, "form")
    hot = x.anim("intensify", length=1.6, loop="hold_on_last_frame")
    hot.scale("fade", {0: [0.6, 0.6, 0.6], 1.6: [1.4, 1.4, 1.4]})
    hot.rot("g_core", [0, "q.life_time * 400", "q.life_time * 300"])
    vibrate(hot, "g_core", 0.2, 18)
    x.phase(2, "intensify")
    rc = x.anim("reconnect", length=0.5, loop="hold_on_last_frame")
    rc.rot("g_arc0", {0: [0, 0, 0], 0.15: [0, 0, 90]}).rot("g_arc1", {0: [0, 0, 0], 0.15: [0, 0, -90]})
    rc.rot("g_arcb0", {0: [0, 0, 0], 0.15: [0, 0, 90]}).rot("g_arcb1", {0: [0, 0, 0], 0.15: [0, 0, -90]})
    rc.scale("fade", {0: [1.4, 1.4, 1.4], 0.1: [2.6, 2.6, 2.6], 0.5: [1.8, 1.8, 1.8]})
    x.phase(3, "reconnect")

    j = Fx("fx_pl_jet", P, bounds=(4, 4, (0, 0, 0)), lifetime=80)
    st = j.bone("stretch", pivot=(0, 0, 0))
    j.bone("g_core", "stretch").cbox((0, 0, -8), (1.6, 1.6, 16), "pl_core")
    for i in range(3):
        b = j.bone(f"g_sheath{i}", "stretch", pivot=(0, 0, 0))
        helix_z(b, (0, 0, 0), 2.4, 16, 1.5, 10, FIL[i], i * T / 3, 0.9)
    j.bone("t_glow", "stretch").cbox((0, 0, -8), (4.6, 4.6, 16), "pl_tube")
    a = j.anim("form", length=0.25)
    a.scale("fade", {0: [0.2, 0.2, 0.2], 0.25: [1, 1, 1]})
    j.phase(1, "form", "flow")
    fl = j.anim("flow", loop=True)
    for i in range(3):
        fl.rot(f"g_sheath{i}", [0, 0, f"q.life_time * {900 * (1 if i % 2 else -1)}"])
    vibrate(fl, "g_core", 0.18, 16)
    j.phase(2, "flow")


# ------------------------------------------------------------------------------------------ PL14 stellarator cathedral
def cathedral():
    c = Fx("fx_pl_cathedral", P, bounds=(16, 10, (0, 2, 0)), tex=(256, 256), lifetime=600)
    R, N = 96, 30
    c.bone("assembly", pivot=(0, 0, 0))
    tube = c.bone("t_chamber", "assembly", pivot=(0, 0, 0))
    ribs = c.bone("ribs", "assembly", pivot=(0, 0, 0))
    chord = 2 * R * math.tan(math.pi / N) + 1
    for k in range(N):
        th = k * 360 / N
        x, z = math.cos(math.radians(th)) * R, math.sin(math.radians(th)) * R
        tw = k * 360 * 3 / N
        yaw = -(th + 90)
        y = math.sin(math.radians(th * 3)) * 8
        tube.cbox((x, y, z), (chord, 14, 6), "pl_tube", rotation=(tw, yaw, 0))
        if k % 2 == 0:
            ribs.cbox((x, y, z), (2, 18, 9), "pl_titanium" if k % 4 else "pl_dark_metal", rotation=(tw, yaw, 0))
    for i in range(3):
        st = c.bone(f"g_current{i}", "assembly", pivot=(0, 0, 0))
        for j in range(6):
            th = math.radians(i * 120 + j * 5)
            st.cbox((math.cos(th) * R, math.sin(th * 3) * 8, math.sin(th) * R), (3, 3, 3), FIL[i], rotation=(45, 45, 0))
    for k in range(6):
        ang = k * 60
        bt = c.bone(f"buttress{k}", "assembly", pivot=(0, 0, 0), rotation=(0, ang, 0))
        bt.cbox((R + 10, 26, 0), (4, 56, 9), "pl_ceramic", rotation=(0, 0, -18))
        bt.cbox((R + 2, 56, 0), (3, 22, 6), "pl_titanium", rotation=(0, 0, 30))
        c.bone(f"g_bt{k}", f"buttress{k}", pivot=(0, 0, 0)).cbox((R + 10.5, 26, 0), (0.8, 50, 10), "pl_channel", rotation=(0, 0, -18))
    for i in range(3):
        ring(c, f"outer{i}", "assembly", (0, 0, 0), R + 26 + i * 8, 1.6, 3, 24, "pl_titanium", rx=60 + i * 30, ry=i * 40, gap=6)
    lan = c.bone("g_lantern", "assembly", pivot=(0, -20, 0))
    for i, s_ in enumerate((14, 10, 6)):
        lan.cbox((0, -20, 0), (s_, s_ * 1.5, s_), "pl_core", rotation=(0, i * 30, 0))
    spire = c.bone("spire", "assembly", pivot=(0, 0, 0))
    for i in range(4):
        spire.cbox((0, 16 + i * 14, 0), (10 - i * 2, 14, 10 - i * 2), "pl_dark_metal" if i % 2 else "pl_ceramic", rotation=(0, 45 * i, 0))
    asm = c.anim("form", length=2.0)
    asm.scale("assembly", {0: [0.2, 0.2, 0.2], 1.6: [1.05, 1.05, 1.05], 2.0: [1, 1, 1]})
    asm.rot("t_chamber", {0: [0, -240, 0], 1.8: [0, 0, 0]}).rot("ribs", {0: [0, 200, 0], 1.8: [0, 0, 0]})
    for k in range(6):
        asm.pos(f"buttress{k}", {0: [0, 120, 0], 0.4 + k * 0.15: [0, 120, 0], 1.0 + k * 0.15: [0, 0, 0]})
    c.phase(1, "form")
    act = c.anim("active", loop=True)
    for i in range(3):
        act.rot(f"g_current{i}", [0, f"q.life_time * {90 + i * 20}", 0])
        act.rot(f"outer{i}", [0, f"q.life_time * {(20 + i * 8) * (1 if i % 2 else -1)}", 0])
    act.rot("t_chamber", [0, "q.life_time * 6", 0]).rot("ribs", [0, "q.life_time * 6", 0])
    vibrate(act, "g_lantern", 0.06, 3)
    c.phase(2, "active")
    acc = c.anim("accelerate", loop=True)
    for i in range(3):
        acc.rot(f"g_current{i}", [0, f"q.life_time * {600 + i * 120}", 0])
        acc.rot(f"outer{i}", [0, f"q.life_time * {(160 + i * 50) * (1 if i % 2 else -1)}", 0])
    acc.scale("g_lantern", ["1.5 + math.sin(q.life_time * 1200) * 0.25"] * 3)
    for k in range(6):
        acc.scale(f"g_bt{k}", [1, "1 + math.sin(q.life_time * 900 + {}) * 0.3".format(k * 60), 1.6])
    c.phase(3, "accelerate")
    dis = c.anim("dissolve", length=1.4)
    for k in range(6):
        dis.pos(f"buttress{k}", {0: [0, 0, 0], 1.2: [0, 60 + k * 10, 0]})
    dis.scale("assembly", {0: [1, 1, 1], 0.4: [1.08, 1.08, 1.08], 1.3: [0, 0, 0]})
    dis.rot("t_chamber", {0: [0, 0, 0], 1.3: [0, 300, 0]})
    c.phase(15, "dissolve")

    br = Fx("fx_pl_branch", P, bounds=(4, 4, (0, 0, 0)), lifetime=60)
    br.bone("stretch", pivot=(0, 0, 0))
    br.bone("g_stem", "stretch").cbox((0, 0, -8), (1.2, 1.2, 16), "pl_core")
    for i, (ry, rx, zz, ln) in enumerate(((22, 8, -4, 7), (-26, -6, -7, 6), (18, -14, -10, 5), (-20, 10, -12, 4))):
        b = br.bone(f"g_off{i}", "stretch", pivot=(0, 0, zz), rotation=(rx, ry, 0))
        b.cbox((0, 0, zz - ln / 2), (0.5, 0.5, ln), FIL[i % 3])
    a = br.anim("form", length=0.2)
    a.scale("fade", {0: [1, 1, 0.01], 0.2: [1, 1, 1]})
    br.phase(1, "form", "crackle")
    cr = br.anim("crackle", loop=True)
    for i in range(4):
        cr.rot(f"g_off{i}", [f"math.sin(q.life_time * 2000 + {i * 70}) * 8", f"math.cos(q.life_time * 1700 + {i * 50}) * 8", 0])
    br.phase(2, "crackle")

    bm = Fx("fx_pl_beam", P, bounds=(4, 4, (0, 0, 0)), lifetime=80)
    bm.bone("stretch", pivot=(0, 0, 0))
    bm.bone("g_core", "stretch").cbox((0, 0, -8), (3.2, 3.2, 16), "pl_core")
    bm.bone("t_sheath", "stretch").cbox((0, 0, -8), (7, 7, 16), "pl_tube")
    for i in range(3):
        b = bm.bone(f"g_coil{i}", "stretch", pivot=(0, 0, 0))
        helix_z(b, (0, 0, 0), 4.6, 16, 2, 14, FIL[i], i * T / 3, 0.9)
    ring(bm, "emitter", bm.top, (0, 0, 0), 6, 1.2, 1.6, 10, "pl_titanium", rx=90)
    a = bm.anim("form", length=0.3)
    a.scale("stretch", {0: [0.2, 0.2, 0.01], 0.3: [1, 1, 1]})
    bm.phase(1, "form", "fire")
    fi = bm.anim("fire", loop=True)
    for i in range(3):
        fi.rot(f"g_coil{i}", [0, 0, f"q.life_time * {700 * (1 if i % 2 else -1)}"])
    vibrate(fi, "g_core", 0.2, 22)
    fi.rot("emitter", [0, "q.life_time * 400", 0])
    bm.phase(2, "fire")


# ------------------------------------------------------------------------------------------ PL15 heavenwide network
def network():
    import random
    rnd = random.Random(1515)
    n = Fx("fx_pl_network", P, bounds=(28, 10, (0, 3, 0)), tex=(256, 256), lifetime=900)
    nodes = []
    for i in range(4):
        for j in range(4):
            nodes.append(((i - 1.5) * 96 + rnd.uniform(-22, 22), rnd.uniform(10, 90), (j - 1.5) * 96 + rnd.uniform(-22, 22)))
    def edges(seed, k):
        r = random.Random(seed)
        out = set()
        for a in range(len(nodes)):
            d = sorted(range(len(nodes)), key=lambda b: (nodes[a][0] - nodes[b][0]) ** 2 + (nodes[a][2] - nodes[b][2]) ** 2 + (nodes[a][1] - nodes[b][1]) ** 2)
            for b in d[1:1 + k]:
                if r.random() < 0.85:
                    out.add((min(a, b), max(a, b)))
        return sorted(out)
    old = edges(1, 2)
    new = [e for e in edges(7, 3) if e not in old][:len(old)]
    n.bone("web", pivot=(0, 0, 0))
    for k, (a, b) in enumerate(old):
        A, B = nodes[a], nodes[b]
        mid = tuple((A[i] + B[i]) / 2 for i in range(3))
        bone = n.bone(f"g_e{k}", "web", pivot=mid)
        aim_box(bone, A, B, 1.4, FIL[k % 3])
    for k, (a, b) in enumerate(new):
        A, B = nodes[a], nodes[b]
        mid = tuple((A[i] + B[i]) / 2 for i in range(3))
        aim_box(n.bone(f"g_r{k}", "web", pivot=mid), A, B, 1.8, "pl_core" if k % 2 else FIL[k % 3])
    for k, p in enumerate(nodes):
        n.bone(f"g_n{k}", "web", pivot=p).cbox(p, (4.5, 4.5, 4.5), "pl_core", rotation=(45, 45, 0))
    gen = n.anim("genesis", length=2.2, loop="hold_on_last_frame")
    for k in range(len(old)):
        t0 = 0.04 * k
        gen.scale(f"g_e{k}", {0: [0, 0, 0], t0 + 0.001: [0, 0, 0], t0 + 0.4: [1, 1, 1]})
    for k in range(len(new)):
        gen.scale(f"g_r{k}", [0, 0, 0])
    for k in range(len(nodes)):
        gen.scale(f"g_n{k}", {0: [0, 0, 0], 0.6 + k * 0.05: [0, 0, 0], 0.9 + k * 0.05: [1, 1, 1]})
    n.phase(1, "genesis")
    con = n.anim("confine", loop=True)
    for k in range(len(old)):
        con.rot(f"g_e{k}", [f"math.sin(q.life_time * 80 + {k * 23}) * 6", f"math.sin(q.life_time * 60 + {k * 31}) * 8", 0])
    for k in range(len(new)):
        con.scale(f"g_r{k}", [0, 0, 0])
    for k in range(len(nodes)):
        con.scale(f"g_n{k}", [f"1 + math.pow(math.max(0, math.sin(q.life_time * 200 + {k * 40})), 6) * 0.9"] * 3)
    con.rot("web", [0, "math.sin(q.life_time * 20) * 6", 0])
    n.phase(2, "confine")
    still = n.anim("still", loop=True)
    for k in range(len(new)):
        still.scale(f"g_r{k}", [0, 0, 0])
    for k in range(len(nodes)):
        still.scale(f"g_n{k}", [1.6, 1.6, 1.6])
    n.phase(3, "still")
    rc = n.anim("reconnect", length=0.8, loop="hold_on_last_frame")
    for k in range(len(old)):
        rc.scale(f"g_e{k}", {0: [1, 1, 1], 0.08: [2.5, 0.5, 2.5], 0.25: [0, 0, 0]})
        rc.rot(f"g_e{k}", {0: [0, 0, 0], 0.25: [0, 90, 40]})
    for k in range(len(new)):
        rc.scale(f"g_r{k}", {0: [0, 0, 0], 0.2: [0, 0, 0], 0.45: [1.6, 1.3, 1.6], 0.8: [1, 1, 1]})
    for k in range(len(nodes)):
        rc.scale(f"g_n{k}", {0: [1.6, 1.6, 1.6], 0.2: [3, 3, 3], 0.8: [1.2, 1.2, 1.2]})
    n.phase(4, "reconnect")
    un = n.anim("dissolve", length=1.6)
    for k in range(len(new)):
        un.scale(f"g_r{k}", {0: [1, 1, 1], 0.1 + 0.04 * k: [1, 1, 1], 0.5 + 0.04 * k: [3, 0, 3]})
        un.rot(f"g_r{k}", {0: [0, 0, 0], 0.5 + 0.04 * k: [0, 0, 180]})
    for k in range(len(old)):
        un.scale(f"g_e{k}", [0, 0, 0])
    for k in range(len(nodes)):
        un.scale(f"g_n{k}", {0: [1, 1, 1], 1.0: [0, 0, 0]})
    n.phase(15, "dissolve")

    sj = Fx("fx_pl_sweepjet", P, bounds=(6, 6, (0, 0, 0)), lifetime=120)
    sj.bone("stretch", pivot=(0, 0, 0))
    for i in range(3):
        b = sj.bone(f"g_braid{i}", "stretch", pivot=(0, 0, 0))
        helix_z(b, (0, 0, 0), 2.0, 16, 2.5, 16, ("pl_core", "pl_magenta", "pl_filament")[i], i * T / 3, 1.6)
    sj.bone("t_body", "stretch").cbox((0, 0, -8), (9, 9, 16), "pl_tube")
    fan = sj.bone("g_fan", "stretch", pivot=(0, 0, -16))
    for k in range(5):
        fan.cbox((0, 0, -17), (0.6, 0.6, 3), FIL[k % 3], rotation=((k - 2) * 18, (k - 2) * 12, 0))
    a = sj.anim("form", length=0.3)
    a.scale("fade", {0: [0.1, 0.1, 1], 0.3: [1, 1, 1]})
    sj.phase(1, "form", "rage")
    rg = sj.anim("rage", loop=True)
    for i in range(3):
        rg.rot(f"g_braid{i}", [0, 0, f"q.life_time * {1100 * (1 if i % 2 else -1)}"])
    vibrate(rg, "t_body", 0.12, 14)
    sj.phase(2, "rage")

    jn = Fx("fx_pl_junction", P, bounds=(4, 4, (0, 0, 0)), lifetime=400)
    for k in range(6):
        jb = jn.bone(f"g_lobe{k}", pivot=(0, 0, 0), rotation=((k % 3) * 60, k * 60, 0))
        for t in range(4):
            jb.cbox((math.sin(t * 0.8) * 3, 3 + t * 3, 0), (1.0, 3.2, 1.0), FIL[k % 3], rotation=(0, 0, -t * 20))
    jn.bone("g_knot").cbox((0, 0, 0), (5, 5, 5), "pl_core", rotation=(45, 0, 45))
    jn.phase(1, jn.default_form(0.4), "pulse_loop")
    pl = jn.anim("pulse_loop", loop=True)
    for k in range(6):
        pl.rot(f"g_lobe{k}", [0, f"q.life_time * {120 + k * 20}", 0])
    vibrate(pl, "g_knot", 0.25, 6)
    jn.phase(2, "pulse_loop")
    hit = jn.anim("impact", length=0.4)
    hit.scale("fade", {0: [1, 1, 1], 0.08: [2.8, 2.8, 2.8], 0.4: [1, 1, 1]})
    jn.pulse("impact")


whip()
borer()
prominence()
membrane()
stellarator()
molt()
harp()
pylon()
horizon()
skates()
sling()
manta()
reconnection()
cathedral()
network()
