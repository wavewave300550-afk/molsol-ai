"""Darkness Magic constructs (Grimoire 05): dark-green folding planes, occlusion, silhouettes.
Light-absorbing surfaces (lit, alpha-blended); only muted jade lines are additive. No smoke, no vines,
no purple voids, no singularities."""
import math
import random
from .fxdefs import Fx
from .fxparts import oriented, ring, vibrate
from .fxlib import aim_box, silhouette, walk_cycle

D = "darkness"


# ------------------------------------------------------------------------------------------ decoy (tactical)
def decoy():
    """Invisible lure used by Darkness and Prism Light misdirection spells (no geometry)."""
    Fx("decoy", "shared", bounds=(1, 2, (0, 1, 0)), lifetime=400, family=("grimoire_fx", "grimoire_decoy", "mob"),
       components={"minecraft:collision_box": {"width": 0.6, "height": 1.8},
                   "minecraft:health": {"value": 20, "max": 20}})


def _diamond(bone, cx, cy, cz, w, h, thick, style, plane="xy"):
    pts = [(0, h), (w, 0), (0, -h), (-w, 0)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        if plane == "xy":
            A, B = (cx + a[0], cy + a[1], cz), (cx + b[0], cy + b[1], cz)
        else:
            A, B = (cx + a[0], cy, cz + a[1]), (cx + b[0], cy, cz + b[1])
        aim_box(bone, A, B, thick, style, pad=thick)


# ------------------------------------------------------------------------------------------ D01 origami sheet
def origami():
    f = Fx("fx_d_sheet", D, bounds=(3, 2, (0, 0, 0)), lifetime=120)
    f.bone("spinner", pivot=(0, 0, 0))
    for k in range(4):
        f.bone(f"flap{k}", "spinner", pivot=(0, 0, 0), rotation=(0, k * 90, 0))
        fb = f.bone(f"fold{k}", f"flap{k}", pivot=(0, 0, 0))
        fb.cbox((6, 0, 0), (8.6, 0.3, 8.6), "d_glass" if k % 2 else "d_plate", rotation=(0, 45, 0))
        f.bone(f"g_edge{k}", f"fold{k}", pivot=(0, 0, 0)).cbox((11.8, 0.2, 0), (0.3, 0.3, 4), "d_jade_line", rotation=(0, 45, 0))
    cr = f.bone("g_crease", "spinner")
    cr.cbox((0, 0.25, 0), (17, 0.15, 0.25), "d_jade_line", rotation=(0, 45, 0))
    cr.cbox((0, 0.25, 0), (17, 0.15, 0.25), "d_jade_line", rotation=(0, -45, 0))
    fold = f.anim("fold", loop=True)
    for k in range(4):
        fold.rot(f"fold{k}", [0, 0, f"math.max(0, math.sin(q.life_time * 120 - {k * 70})) * 150"])
    fold.rot("spinner", ["math.sin(q.life_time * 50) * 20", "q.life_time * 40", 0])
    f.phase(1, f.default_form(0.25), "fold")
    blade = f.anim("blade", loop=True)
    for k in range(4):
        blade.rot(f"fold{k}", [0, 0, 0]).scale(f"fold{k}", [1.7 if k % 2 == 0 else 0.7, 1, 1])
    blade.rot("spinner", [0, "q.life_time * 900", 0])
    f.phase(2, "blade")
    flat = f.anim("dissolve", length=0.5)
    flat.scale("spinner", {0: [1, 1, 1], 0.4: [1.5, 0.01, 1.5]})
    f.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D02 maw
def maw():
    m = Fx("fx_d_maw", D, bounds=(4, 4, (0, 1.5, 0)), lifetime=120)
    rnd = random.Random(2)
    for name, z, sgn, w_, h in (("jaw_f", -9, 1, 26, 30), ("jaw_b", 9, -1, 22, 26)):
        j = m.bone(name, pivot=(0, 0, z))
        j.cbox((0, h / 2, z), (w_, h, 2.4), "d_glass")
        j.cbox((0, h * 0.3, z - sgn * 0.8), (w_ * 0.8, h * 0.35, 1.2), "d_plate", rotation=(0, 0, 4 * sgn))
        for k in range(7):
            x = -w_ / 2 + 2 + k * (w_ - 4) / 6
            ln = 5 + rnd.random() * 4
            j.cbox((x, h - 1.5, z + sgn * ln / 2), (1.8, 1.8, ln), "d_jade_tile" if k % 3 == 0 else "d_plate", rotation=(0, 0, 45))
        e = m.bone(f"g_{name}_edge", name, pivot=(0, 0, z))
        e.cbox((0, h, z), (w_, 0.3, 0.4), "d_jade_line")
    m.bone("t_pool").cbox((0, 0.1, 0), (30, 0.2, 26), "d_shadow")
    rise = m.anim("rise", length=0.6, loop="hold_on_last_frame")
    rise.rot("jaw_f", {0: [90, 0, 0], 0.6: [42, 0, 0]}).rot("jaw_b", {0: [-90, 0, 0], 0.6: [-42, 0, 0]})
    m.phase(1, "rise")
    op = m.anim("open", loop=True)
    op.rot("jaw_f", ["42 + math.sin(q.life_time * 200) * 4", 0, 0]).rot("jaw_b", ["-42 - math.sin(q.life_time * 200) * 4", 0, 0])
    m.phase(2, "open")
    sn = m.anim("snap", length=0.3, loop="hold_on_last_frame")
    sn.rot("jaw_f", {0: [42, 0, 0], 0.1: [-20, 0, 0], 0.18: [-15, 0, 0]}).rot("jaw_b", {0: [-42, 0, 0], 0.1: [20, 0, 0], 0.18: [15, 0, 0]})
    sn.scale("fade", {0: [1, 1, 1], 0.1: [1.08, 0.92, 1.08], 0.3: [1, 1, 1]})
    m.phase(3, "snap")
    fr = m.anim("dissolve", length=0.6)
    fr.scale("jaw_f", {0: [1, 1, 1], 0.5: [1.6, 0.02, 1.6]}).scale("jaw_b", {0: [1, 1, 1], 0.5: [1.6, 0.02, 1.6]})
    fr.rot("jaw_f", {0: [-15, 0, 0], 0.5: [80, 30, 0]}).rot("jaw_b", {0: [15, 0, 0], 0.5: [-80, -30, 0]})
    m.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D03 unwritten glyphs
def glyphs():
    g = Fx("fx_d_glyph", D, bounds=(3, 3, (0, 0, 0)), lifetime=200)
    lattice = [(x, y) for x in range(-2, 3) for y in range(-2, 3)]
    for v in range(5):
        rnd = random.Random(30 + v)
        gb = g.bone(f"glyph{v}")
        strokes = []
        while len(strokes) < 7 + v:
            a = rnd.choice(lattice)
            b = (a[0] + rnd.choice((-2, -1, 0, 1, 2)), a[1] + rnd.choice((-2, -1, 0, 1, 2)))
            if b == a or abs(b[0]) > 2 or abs(b[1]) > 2:
                continue
            strokes.append((a, b))
        for i, (a, b) in enumerate(strokes):
            sb = g.bone(f"st{v}_{i}", f"glyph{v}")
            A, B = (a[0] * 4.8, a[1] * 4.8, 0), (b[0] * 4.8, b[1] * 4.8, 0)
            if i % 3 == 2:   # erased stroke: only the outline remains
                aim_box(g.bone(f"g_er{v}_{i}", f"st{v}_{i}"), A, B, 0.35, "d_jade_line")
            else:
                aim_box(sb, A, B, 1.8 if v < 4 else 2.4, "d_plate" if i % 2 else "d_glass")
        g.bone(f"g_dot{v}", f"glyph{v}").cbox((rnd.choice((-1, 1)) * 9, rnd.choice((-1, 1)) * 9, 0), (1.2, 1.2, 1.2), "d_jade_line")
    sel = g.anim("select", loop=True)
    for v in range(5):
        sel.scale(f"glyph{v}", [f"v.var == {v} ? 1 : 0"] * 3)
    g.keep("select")
    con = g.anim("construct", length=0.6)
    for v in range(5):
        n = 7 + v
        for i in range(n):
            t0 = 0.05 * i
            con.scale(f"st{v}_{i}", {0: [0, 0, 0], t0 + 0.001: [0, 0, 0], t0 + 0.08: [1.2, 1.2, 1.2], t0 + 0.12: [1, 1, 1]})
    g.phase(1, "construct")
    fl = g.anim("drift", loop=True)
    fl.rot("fade", ["math.sin(q.life_time * 90) * 10", "math.sin(q.life_time * 60) * 18", 0])
    g.phase(2, "drift")
    im = g.anim("imprint", loop=True)
    im.scale("fade", [0.7, 0.7, 0.2]).rot("fade", [0, "q.life_time * 30", 0])
    g.phase(3, "imprint")


# ------------------------------------------------------------------------------------------ D04 eclipse discs
def eclipse():
    e = Fx("fx_d_eclipse", D, bounds=(11, 2, (0, 0, 0)), lifetime=400)
    disc = e.bone("t_disc")
    for k in range(3):
        disc.cbox((0, 0, 0), (140, 0.6, 140), "d_shadow", rotation=(0, k * 30, 0))
    occ = e.bone("occluder", pivot=(0, 0, 0))
    for k in range(3):
        occ.cbox((14, 0.8, 8), (88, 0.8, 88), "d_void", rotation=(0, 15 + k * 30, 0))
    ring(e, "g_rim", e.top, (0, 0.4, 0), 80, 0.8, 0.6, 32, "d_jade_line")
    ring(e, "g_rim2", e.top, (0, 0.4, 0), 70, 0.4, 0.4, 28, "d_jade_line", gap=4)
    e.phase(1, e.default_form(0.6))
    dr = e.anim("drift", loop=True)
    dr.rot("fade", ["math.sin(q.life_time * 40) * 8", "q.life_time * 14", "math.cos(q.life_time * 35) * 8"])
    dr.rot("occluder", [0, "-q.life_time * 30", 0])
    e.phase(2, "drift")
    cv = e.anim("converge", loop=True)
    cv.rot("fade", [0, "q.life_time * 90", 0]).rot("g_rim2", [0, "-q.life_time * 200", 0])
    e.phase(3, "converge")

    u = Fx("fx_d_umbra", D, bounds=(11, 1, (0, 0, 0)), lifetime=400)
    ub = u.bone("t_shade")
    for k in range(3):
        ub.cbox((0, 0.15, 0), (150, 0.1, 150), "d_shadow_thin", rotation=(0, k * 30, 0))
    ring(u, "g_edge", u.top, (0, 0.3, 0), 80, 0.6, 0.2, 32, "d_jade_line")
    u.phase(1, u.default_form(0.6))
    ful = u.anim("full", loop=True)
    ful.scale("t_shade", ["1 + math.sin(q.life_time * 300) * 0.04", 2, "1 + math.sin(q.life_time * 300) * 0.04"])
    u.phase(3, "full")


# ------------------------------------------------------------------------------------------ D05 velvet cloak
def velvet():
    v = Fx("fx_d_velvet", D, bounds=(2, 3, (0, 1, 0)), lifetime=600)
    N = 12
    for k in range(N):
        a = k * 360 / N
        x, z = math.cos(math.radians(a)) * 6.4, math.sin(math.radians(a)) * 6.4
        pb = v.bone(f"panel{k}", pivot=(x, 24, z), rotation=(0, -a - 90, 0))
        pb.cbox((x, 13, z), (3.6, 22 - (k % 3), 0.5), "d_shadow" if k % 2 else "d_glass", rotation=(0, -a - 90, 0))
        v.bone(f"g_hem{k}", f"panel{k}", pivot=(x, 24, z)).cbox((x, 2.2 + (k % 3), z), (3.6, 0.3, 0.6), "d_jade_line", rotation=(0, -a - 90, 0))
    ring(v, "collar", v.top, (0, 24, 0), 6.6, 1.0, 1.6, 12, "d_plate")
    v.phase(1, v.default_form(0.5), "flow")
    fl = v.anim("flow", loop=True)
    for k in range(N):
        fl.rot(f"panel{k}", [f"8 + math.sin(q.life_time * 110 + {k * 30}) * 7", 0, f"math.sin(q.life_time * 80 + {k * 45}) * 4"])
    v.phase(2, "flow")
    pl = v.anim("fold", length=0.45)
    for k in range(N):
        pl.rot(f"panel{k}", {0: [8, 0, 0], 0.1: [55, 0, 0], 0.45: [8, 0, 0]})
        pl.scale(f"panel{k}", {0: [1, 1, 1], 0.1: [1.5, 0.6, 3], 0.45: [1, 1, 1]})
    v.pulse("fold")


# ------------------------------------------------------------------------------------------ D06 lock + latch
def latch():
    lk = Fx("fx_d_lock", D, bounds=(2, 1, (0, 0, 0)), lifetime=700)
    lb = lk.bone("lock")
    lb.cbox((0, 0.3, 2), (12, 0.6, 10), "d_plate")
    lb.cbox((0, 0.7, 2), (2.2, 0.3, 5), "d_void")
    ring(lk, "shackle", "lock", (0, 0.4, -3), 5, 1.2, 0.6, 10, "d_emerald", start=180, arc=180)
    lk.bone("g_line", "lock").cbox((0, 0.75, 2), (12.4, 0.1, 10.4), "d_jade_edge")
    lk.phase(1, lk.default_form(0.4), "idle")
    idl = lk.anim("idle", loop=True)
    idl.rot("lock", [0, "math.sin(q.life_time * 40) * 10", 0])
    lk.phase(2, "idle")

    la = Fx("fx_d_latch", D, bounds=(4, 4, (0, 1.5, 0)), lifetime=200)
    la.bone("frame", pivot=(0, 0, 0))
    for sgn in (-1, 1):
        post = la.bone(f"post{'l' if sgn > 0 else 'r'}", "frame", pivot=(sgn * 13, 0, 0))
        post.cbox((sgn * 13, 20, 0), (4, 40, 4), "d_plate")
        post.cbox((sgn * 13, 30, 0), (6, 4, 6), "d_emerald")
        post.cbox((sgn * 13, 10, 0), (6, 4, 6), "d_emerald")
    bolt = la.bone("bolt", "frame", pivot=(0, 20, 0))
    bolt.cbox((0, 20, 0), (34, 5, 3), "d_emerald")
    bolt.cbox((-17, 20, 0), (3, 8, 4), "d_plate")
    la.bone("g_bolt", "bolt").cbox((0, 22.6, 0), (34, 0.3, 3.2), "d_jade_line")
    la.bone("t_pin").cbox((0, 0.2, 0), (24, 0.2, 24), "d_shadow")
    ap = la.anim("form", length=0.3)
    ap.scale("frame", {0: [1, 0.01, 1], 0.3: [1, 1, 1]}).pos("bolt", [-34, 0, 0])
    la.phase(1, "form")
    cl = la.anim("close", length=0.35, loop="hold_on_last_frame")
    cl.pos("bolt", {0: [-34, 0, 0], 0.15: [2, 0, 0], 0.25: [0, 0, 0]})
    cl.scale("g_bolt", {0: [1, 1, 1], 0.15: [1, 8, 1], 0.35: [1, 1, 1]})
    la.phase(2, "close")
    hold = la.anim("hold", loop=True)
    vibrate(hold, "bolt", 0.02, 12)
    la.phase(3, "hold")
    rel = la.anim("dissolve", length=0.5)
    rel.pos("bolt", {0: [0, 0, 0], 0.25: [-34, 0, 0]}).scale("frame", {0: [1, 1, 1], 0.5: [1, 0.01, 1]})
    la.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D07 curtain
def curtain():
    c = Fx("fx_d_curtain", D, bounds=(9, 7, (0, 3, 0)), lifetime=500)
    N = 9
    for k in range(N):
        x = (k - (N - 1) / 2) * 13
        ln = 96 - (k * 7 % 11)
        s = c.bone(f"strip{k}", pivot=(x, 100, 0))
        s.cbox((x, 100 - ln / 2, 0), (13.4, ln, 0.6), "d_shadow" if k % 2 else "d_shadow_thin")
        c.bone(f"g_hem{k}", f"strip{k}", pivot=(x, 100, 0)).cbox((x, 100 - ln, 0), (13.4, 0.5, 0.8), "d_jade_line")
        for f in range(2):
            c.bone(f"fray{k}{f}", f"strip{k}", pivot=(x, 100, 0)).cbox((x - 3 + f * 6, 102, 0), (2, 5, 0.4), "d_shadow_thin")
    dsc = c.anim("descend", length=0.8, loop="hold_on_last_frame")
    for k in range(N):
        dsc.scale(f"strip{k}", {0: [1, 0.01, 1], 0.05 * k + 0.3: [1, 1.05, 1], 0.05 * k + 0.45: [1, 1, 1]})
    c.phase(1, "descend")
    und = c.anim("undulate", loop=True)
    for k in range(N):
        und.rot(f"strip{k}", [f"math.sin(q.life_time * 70 + {k * 40}) * 5", 0, f"math.sin(q.life_time * 50 + {k * 25}) * 2"])
    c.phase(2, "undulate")
    fa = c.anim("dissolve", length=0.8)
    for k in range(N):
        fa.rot(f"strip{k}", {0: [0, 0, 0], 0.6: [-70, 0, 0]}).scale(f"strip{k}", {0: [1, 1, 1], 0.7: [1, 0.01, 1]})
    c.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D08 mosaic
MOSAIC_N = 8


def mosaic_pattern(p, i, j):
    """Same pattern the script uses: True = jade side up (safe path)."""
    if p == 0:
        return i in (3, 4) or j in (3, 4)
    return abs(i - j) <= 0 or abs(i + j - (MOSAIC_N - 1)) <= 0 or (i in (0, 7) and j in (0, 7))


def mosaic():
    m = Fx("fx_d_mosaic", D, bounds=(11, 2, (0, 0, 0)), lifetime=500)
    S = 20
    for i in range(MOSAIC_N):
        for j in range(MOSAIC_N):
            x, z = (i - (MOSAIC_N - 1) / 2) * S, (j - (MOSAIC_N - 1) / 2) * S
            tb = m.bone(f"t{i}_{j}", pivot=(x, 0.7, z))
            tb.box((x - 9.5, 0.1, z - 9.5), (19, 1.2, 19), "d_plate", faces={"up": "d_glass", "down": "d_jade_tile"})
            if (i + j) % 2 == 0:
                m.bone(f"g_d{i}_{j}", f"t{i}_{j}", pivot=(x, 0.7, z)).cbox((x, 1.35, z), (26, 0.1, 0.4), "d_jade_line", rotation=(0, 45, 0))
    form = m.anim("form", length=1.0)
    for i in range(MOSAIC_N):
        for j in range(MOSAIC_N):
            d = math.hypot(i - 3.5, j - 3.5)
            form.scale(f"t{i}_{j}", {0: [0, 0, 0], 0.08 * d + 0.001: [0, 0, 0], 0.08 * d + 0.3: [1, 1, 1]})
    m.phase(1, "form")
    for ph, p in ((2, 0), (3, 1)):
        a = m.anim(f"pattern{p}", length=0.9, loop="hold_on_last_frame")
        for i in range(MOSAIC_N):
            for j in range(MOSAIC_N):
                up = 180 if mosaic_pattern(p, i, j) else 0
                other = 180 if mosaic_pattern(1 - p, i, j) else 0
                d = math.hypot(i - 3.5, j - 3.5) * 0.08
                a.rot(f"t{i}_{j}", {0: [other, 0, 0], d + 0.001: [other, 0, 0], d + 0.3: [up, 0, 0]})
        m.phase(ph, f"pattern{p}")
    dis = m.anim("dissolve", length=1.0)
    for i in range(MOSAIC_N):
        for j in range(MOSAIC_N):
            d = math.hypot(i - 3.5, j - 3.5) * 0.06
            dis.scale(f"t{i}_{j}", {0: [1, 1, 1], d + 0.001: [1, 1, 1], d + 0.4: [0, 0, 0]})
    m.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D09 censor's seal
def mask():
    m = Fx("fx_d_mask", D, bounds=(2, 2, (0, 0, 0)), lifetime=400)
    face = m.bone("face")
    face.cbox((0, 0, 0), (10, 13, 2.6), "d_plate")
    face.cbox((0, 0, -0.6), (8, 15, 2.2), "d_plate")
    face.cbox((0, 0, -1), (11.4, 9, 1.8), "d_emerald")
    m.bone("g_rim", "face").cbox((0, 0, -1.4), (11.8, 15.4, 0.2), "d_jade_edge")
    for sgn in (-1, 1):
        m.bone(f"g_ap{'l' if sgn > 0 else 'r'}", "face", pivot=(sgn * 2.4, 1, -1.8)).cbox((sgn * 2.4, 1, -1.8), (0.5, 4, 0.2), "d_jade_line")
    pn = m.bone("panels", pivot=(0, 0, -3))
    for k in range(4):
        pn.cbox((-6 + k * 4, 0, -3.4 - k * 0.2), (3.8, 16, 0.4), "d_glass" if k % 2 else "d_shadow")
    form = m.anim("form", length=0.6)
    form.scale("face", {0: [0.01, 0.01, 0.01], 0.4: [1, 1, 1]}).pos("panels", {0: [0, 20, 0], 0.6: [0, 0, 0]})
    m.phase(1, "form", "watch")
    w = m.anim("watch", loop=True)
    for side in ("l", "r"):
        w.scale(f"g_ap{side}", [1, "math.pow(math.max(0, math.sin(q.life_time * 90)), 4)", 1])
    w.pos("panels", [0, "math.max(0, math.sin(q.life_time * 90)) * 8", 0])
    w.rot("face", [0, "math.sin(q.life_time * 30) * 8", 0])
    m.phase(2, "watch")


# ------------------------------------------------------------------------------------------ D10 silhouette traverse
def silhouette_fx():
    s = Fx("fx_d_silhouette", D, bounds=(2, 2, (0, 0.5, 0)), lifetime=120)
    s.bone("figure", pivot=(0, 0, 0))
    silhouette(s, "t_", "figure", "d_shadow", 1.0)
    silhouette(s, "g_", "figure", "d_jade_edge", 1.0, inflate=0.5)
    fl = s.anim("flatten", length=0.3, loop="hold_on_last_frame")
    fl.rot("figure", {0: [0, 0, 0], 0.3: [-90, 0, 0]}).scale("figure", {0: [1, 1, 1], 0.3: [1.1, 1.1, 0.12]})
    s.phase(1, "flatten")
    tr = s.anim("travel", loop=True)
    tr.rot("figure", [-90, 0, 0]).scale("figure", ["1.1 + math.sin(q.life_time * 900) * 0.06", 1.3, 0.12])
    s.phase(2, "travel")
    ri = s.anim("rise", length=0.4, loop="hold_on_last_frame")
    ri.rot("figure", {0: [-90, 0, 0], 0.3: [0, 0, 0]}).scale("figure", {0: [1.1, 1.3, 0.12], 0.3: [1, 1, 1], 0.4: [1.05, 1.05, 1.05]})
    s.phase(3, "rise")


# ------------------------------------------------------------------------------------------ D11 stair panel
def step():
    s = Fx("fx_d_step", D, bounds=(2, 1, (0, 0, 0)), lifetime=400)
    for side, sgn in (("l", 1), ("r", -1)):
        h = s.bone(f"half_{side}", pivot=(0, 0, 0))
        h.cbox((sgn * 4, -0.2, 0), (8, 0.4, 16), "d_glass")
        s.bone(f"g_e{side}", f"half_{side}", pivot=(0, 0, 0)).cbox((sgn * 8, -0.05, 0), (0.3, 0.3, 16), "d_jade_line")
    un = s.anim("unfold", length=0.3, loop="hold_on_last_frame")
    un.rot("half_l", {0: [0, 0, -88], 0.3: [0, 0, 0]}).rot("half_r", {0: [0, 0, 88], 0.3: [0, 0, 0]})
    s.phase(1, "unfold")
    fo = s.anim("fold", length=0.35, loop="hold_on_last_frame")
    fo.rot("half_l", {0: [0, 0, 0], 0.3: [0, 0, -88]}).rot("half_r", {0: [0, 0, 0], 0.3: [0, 0, 88]})
    fo.scale("fade", {0: [1, 1, 1], 0.35: [0.2, 0.2, 0.2]})
    s.phase(3, "fold")


# ------------------------------------------------------------------------------------------ D12 doppelganger
def double():
    d = Fx("fx_d_double", D, bounds=(2, 3, (0, 1, 0)), lifetime=600)
    d.bone("figure", pivot=(0, 0, 0))
    names = silhouette(d, "", "figure", "d_glass", 1.0)
    for part, (x, y0, y1) in (("body", (0, 13, 23)), ("arm_l", (6, 11, 21)), ("arm_r", (-6, 11, 21)), ("leg_l", (2, 1, 11)), ("leg_r", (-2, 1, 11))):
        seam = d.bone(f"g_seam_{part}", names[part], pivot=(x, y1, 0))
        seam.cbox((x, (y0 + y1) / 2, -2.2), (0.3, y1 - y0, 0.2), "d_jade_line")
        seam.cbox((x, (y0 + y1) / 2, 2.2), (0.3, y1 - y0, 0.2), "d_jade_line")
    d.bone("g_face", names["head"], pivot=(0, 24, 0)).cbox((0, 28, -4.15), (7, 7, 0.2), "d_jade_edge")
    rise = d.anim("rise", length=0.8, loop="hold_on_last_frame")
    rise.rot("figure", {0: [-90, 0, 0], 0.6: [8, 0, 0], 0.8: [0, 0, 0]}).scale("figure", {0: [1, 1, 0.1], 0.6: [1, 1, 1]})
    d.phase(1, "rise")
    idle = d.anim("idle", loop=True)
    idle.rot(names["body"], [0, "math.sin(q.life_time * 40) * 3", 0])
    d.phase(2, "idle")
    walk = d.anim("walk", loop=True)
    walk_cycle(walk, names, 30, 420)
    d.phase(3, "walk")
    atk = d.anim("attack", length=0.4)
    atk.rot(names["arm_r"], {0: [0, 0, 0], 0.12: [-120, 0, 10], 0.3: [20, 0, 0], 0.4: [0, 0, 0]})
    atk.rot(names["body"], {0: [0, 0, 0], 0.15: [0, 25, 0], 0.4: [0, 0, 0]})
    d.pulse("attack")
    fr = d.anim("dissolve", length=0.8)
    for i, part in enumerate(("head", "body", "arm_l", "arm_r", "leg_l", "leg_r")):
        fr.pos(names[part], {0: [0, 0, 0], 0.7: [(i % 3 - 1) * 8, 4 + i, (i % 2) * 6 - 3]})
        fr.scale(names[part], {0: [1, 1, 1], 0.7: [1.4, 1.4, 0.05]})
    d.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D13 footfall reversal
def footfall():
    t = Fx("fx_d_tracker", D, bounds=(2, 1, (0, 0, 0)), lifetime=300)
    for i, (w_, h) in enumerate(((11, 15), (8, 11), (5, 7))):
        b = t.bone(f"shut{i}", pivot=(0, 0.2, 0))
        _diamond(b, 0, 0.2 + i * 0.1, 0, w_, h, 0.6, "d_plate" if i % 2 else "d_jade_tile", plane="xz")
    t.bone("hole").cbox((0, 0.5, 0), (2.2, 0.2, 6), "d_void")
    t.bone("g_ring").cbox((0, 0.1, 0), (24, 0.1, 24), "d_jade_edge", rotation=(0, 45, 0))
    t.phase(1, t.default_form(0.4), "record")
    rec = t.anim("record", loop=True)
    for i in range(3):
        rec.rot(f"shut{i}", [0, f"q.life_time * {(40 + i * 25) * (1 if i % 2 else -1)}", 0])
    t.phase(2, "record")

    w = Fx("fx_d_wraith", D, bounds=(2, 3, (0, 1, 0)), lifetime=200)
    body = w.bone("blade", pivot=(0, 0, 0))
    body.cbox((0, 12, 0), (8, 22, 0.6), "d_glass", rotation=(0, 0, 0))
    body.cbox((0, 25, 0), (5, 6, 0.6), "d_glass", rotation=(0, 0, 45))
    body.cbox((0, 2, 0), (3, 6, 0.6), "d_shadow", rotation=(0, 0, 45))
    _diamond(w.bone("g_edge", "blade"), 0, 14, -0.4, 5, 15, 0.3, "d_jade_line")
    ri = w.anim("rise", length=0.4, loop="hold_on_last_frame")
    ri.rot("blade", {0: [-90, 0, 0], 0.35: [10, 0, 0]})
    w.phase(1, "rise")
    gl = w.anim("glide", loop=True)
    gl.rot("blade", ["14 + math.sin(q.life_time * 400) * 3", 0, "math.sin(q.life_time * 250) * 6"])
    w.phase(2, "glide")
    st = w.anim("strike", length=0.35)
    st.pos("blade", {0: [0, 0, 0], 0.12: [0, 0, -10], 0.35: [0, 0, 0]}).rot("blade", {0: [14, 0, 0], 0.12: [40, 0, 0], 0.35: [14, 0, 0]})
    w.pulse("strike")


# ------------------------------------------------------------------------------------------ D14 court of the unseen
def court():
    d = Fx("fx_d_door", D, bounds=(4, 8, (0, 3.5, 0)), lifetime=600)
    d.bone("slab", pivot=(0, 0, 0))
    d.bone("core", "slab", pivot=(0, 0, 0)).cbox((0, 56, 0), (40, 112, 4), "d_glass")
    for k, (y, h) in enumerate(((22, 30), (58, 30), (92, 22))):
        p = d.bone(f"inset{k}", "slab", pivot=(0, y, -2.4))
        p.cbox((0, y, -2.4), (30, h, 1.2), "d_plate")
        p.cbox((0, y, -3.1), (16, h * 0.5, 0.6), "d_emerald")
        d.bone(f"g_seam{k}", f"inset{k}", pivot=(0, y, -2.4)).cbox((0, y + h / 2 + 2, -2.6), (32, 0.4, 0.4), "d_jade_line")
    ri = d.anim("rise", length=0.8, loop="hold_on_last_frame")
    ri.scale("slab", {0: [1, 0.01, 1], 0.7: [1, 1.04, 1], 0.8: [1, 1, 1]})
    d.phase(1, "rise")
    hm = d.anim("hum", loop=True)
    for k in range(3):
        hm.pos(f"inset{k}", [0, 0, f"math.sin(q.life_time * 60 + {k * 60}) * 0.6"])
    d.phase(2, "hum")
    fo = d.anim("fold", length=1.0, loop="hold_on_last_frame")
    fo.rot("slab", {0: [0, 0, 0], 1.0: [-28, 0, 0]}).scale("slab", {0: [1, 1, 1], 1.0: [0.8, 1.15, 0.8]})
    d.phase(3, "fold")
    sh = d.anim("dissolve", length=0.9)
    for k in range(3):
        sh.pos(f"inset{k}", {0: [0, 0, 0], 0.8: [(k - 1) * 20, -30, -20]}).scale(f"inset{k}", {0: [1, 1, 1], 0.8: [1.4, 0.02, 1.4]})
    sh.scale("core", {0: [1, 1, 1], 0.6: [1, 0.01, 1]})
    d.phase(15, "dissolve")

    ds = Fx("fx_d_doorshadow", D, bounds=(4, 12, (0, 0, -5)), lifetime=600)
    sb = ds.bone("t_shadow")
    sb.cbox((0, 0.12, -80), (40, 0.1, 160), "d_shadow_thin")
    e = ds.bone("g_edges")
    for sgn in (-1, 1):
        e.cbox((sgn * 20, 0.2, -80), (0.4, 0.1, 160), "d_jade_line")
    ds.phase(1, ds.default_form(0.6))

    f = Fx("fx_d_fold", D, bounds=(2, 3, (0, 1, 0)), lifetime=80)
    for k in range(4):
        f.bone(f"base{k}", pivot=(0, 0, 0), rotation=(0, k * 90, 0))
        p = f.bone(f"plate{k}", f"base{k}", pivot=(0, 0, -7))
        p.cbox((0, 12, -7), (13, 24, 0.6), "d_glass" if k % 2 else "d_plate")
        f.bone(f"g_pe{k}", f"plate{k}", pivot=(0, 0, -7)).cbox((0, 12, -7.4), (0.3, 24, 0.2), "d_jade_line")
    sp = f.anim("spring", length=0.3, loop="hold_on_last_frame")
    for k in range(4):
        sp.rot(f"plate{k}", {0: [90, 0, 0], 0.18: [-22, 0, 0], 0.3: [-16, 0, 0]})
    f.phase(1, "spring")
    fl = f.anim("dissolve", length=0.4)
    for k in range(4):
        fl.rot(f"plate{k}", {0: [-16, 0, 0], 0.35: [90, 0, 0]})
    f.phase(15, "dissolve")

    mo = Fx("fx_d_monolith", D, bounds=(10, 12, (0, 5, 0)), tex=(128, 256), lifetime=300)
    mo.bone("mono", pivot=(0, 0, 0))
    for k in range(7):
        pb = mo.bone(f"mp{k}", "mono", pivot=(0, 0, 0), rotation=(0, k * 360 / 7, 0))
        pb.cbox((0, 70, -18), (34, 140, 3), "d_glass" if k % 2 else "d_plate", rotation=(-12, 0, 0))
        mo.bone(f"g_mp{k}", f"mp{k}", pivot=(0, 0, 0)).cbox((0, 70, -19.8), (0.6, 136, 0.4), "d_jade_line", rotation=(-12, 0, 0))
    rnd = random.Random(14)
    for k in range(24):
        mo.bone(f"sh{k}", "mono", pivot=(0, 40, 0)).cbox((rnd.uniform(-20, 20), rnd.uniform(20, 120), rnd.uniform(-20, 20)),
                                                    (rnd.uniform(6, 14), 0.4, rnd.uniform(6, 14)), "d_glass", rotation=(rnd.uniform(-30, 30), rnd.uniform(0, 90), 0))
    asm = mo.anim("assemble", length=1.2, loop="hold_on_last_frame")
    for k in range(7):
        asm.rot(f"mp{k}", {0: [0, k * 360 / 7 + 40, 0], 1.0: [0, k * 360 / 7, 0]})
        asm.pos(f"mp{k}", {0: [0, 0, 0], 1.0: [0, 0, 0]})
    asm.scale("mono", {0: [1.8, 0.6, 1.8], 1.0: [1, 1, 1]})
    for k in range(24):
        asm.scale(f"sh{k}", [0, 0, 0])
    mo.phase(1, "assemble")
    hold = mo.anim("hold", loop=True)
    hold.rot("mono", [0, "q.life_time * 20", 0])
    for k in range(24):
        hold.scale(f"sh{k}", [0, 0, 0])
    mo.phase(2, "hold")
    sh2 = mo.anim("dissolve", length=1.4)
    for k in range(7):
        sh2.scale(f"mp{k}", {0: [1, 1, 1], 0.2: [0, 0, 0]})
    for k in range(24):
        sh2.scale(f"sh{k}", {0: [1, 1, 1], 1.2: [1, 1, 1], 1.4: [0, 0, 0]})
        sh2.pos(f"sh{k}", {0: [0, 0, 0], 1.3: [(k % 5 - 2) * 14, -140, (k % 3 - 1) * 14]})
        sh2.rot(f"sh{k}", {0: [0, 0, 0], 1.3: [0, k * 40, 0]})
    mo.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ D15 world without an outline
def outline_world():
    dm = Fx("fx_d_domain", D, bounds=(42, 2, (0, 0, 0)), lifetime=900)
    S, N = 40, 8
    pl = dm.bone("t_field")
    for i in range(N):
        for j in range(N):
            if math.hypot(i - 3.5, j - 3.5) > 4.3:
                continue
            pl.cbox(((i - 3.5) * S, 0.1, (j - 3.5) * S), (S + 0.2, 0.15, S + 0.2), "d_shadow")
    ln = dm.bone("g_lines")
    for r in (40, 80, 120, 160):
        for k in range(4):
            ang = k * 90
            ln.cbox((math.cos(math.radians(ang)) * r, 0.35, math.sin(math.radians(ang)) * r), (0.5, 0.1, r * 2), "d_jade_line", rotation=(0, ang, 0))
    for k in range(8):
        ln.cbox((0, 0.3, 0), (0.5, 0.1, 320), "d_jade_line", rotation=(0, k * 22.5, 0))
    sp = dm.anim("spread", length=2.0, loop="hold_on_last_frame")
    sp.scale("fade", {0: [0.01, 1, 0.01], 2.0: [1, 1, 1]})
    dm.phase(1, "spread")
    br = dm.anim("breathe", loop=True)
    br.rot("g_lines", [0, "q.life_time * 6", 0])
    dm.phase(2, "breathe")

    o = Fx("fx_d_outline", D, bounds=(3, 3, (0, 1, 0)), lifetime=900)
    ob = o.bone("g_box")
    W_, H_ = 12, 30
    corners = [(x, y, z) for x in (-W_, W_) for y in (0, H_) for z in (-W_, W_)]
    k = 0
    for a in range(8):
        for b in range(a + 1, 8):
            A, B = corners[a], corners[b]
            if sum(1 for i in range(3) if A[i] != B[i]) == 1:
                aim_box(o.bone(f"g_ed{k}", "g_box"), A, B, 0.4, "d_jade_line")
                k += 1
    tr = o.anim("trace", length=0.6)
    for i in range(k):
        tr.scale(f"g_ed{i}", {0: [0, 0, 0], i * 0.04 + 0.001: [0, 0, 0], i * 0.04 + 0.12: [1, 1, 1]})
    o.phase(1, "trace", "flicker")
    fl = o.anim("flicker", loop=True)
    fl.scale("g_box", ["1 + math.floor(math.mod(q.life_time * 8, 2)) * 0.03"] * 3)
    o.phase(2, "flicker")

    r = Fx("fx_d_replica", D, bounds=(2, 3, (0, 1, 0)), lifetime=600)
    r.bone("fig", pivot=(0, 0, 0))
    r.bone("torso", "fig", pivot=(0, 12, 0)).cbox((0, 19, 0), (7, 15, 3.6), "d_void", rotation=(0, 0, 6))
    r.bone("skull", "torso", pivot=(0, 26, 0)).cbox((1, 30, 0), (9, 7, 9), "d_glass", rotation=(0, 20, 12))
    for side, sgn in (("l", 1), ("r", -1)):
        a = r.bone(f"limb_{side}", "torso", pivot=(sgn * 5, 24, 0))
        a.cbox((sgn * 6, 14, 0), (2.4, 22, 2.4), "d_glass", rotation=(0, 0, sgn * -8))
        lg = r.bone(f"leg_{side}", "fig", pivot=(sgn * 2, 12, 0))
        lg.cbox((sgn * 2.4, 6, 0), (2.6, 13, 2.6), "d_void", rotation=(0, 0, sgn * 5))
    r.bone("g_cracks", "torso", pivot=(0, 12, 0)).cbox((0, 19, -1.9), (0.3, 14, 0.2), "d_jade_line", rotation=(0, 0, 18))
    ri = r.anim("rise", length=0.6, loop="hold_on_last_frame")
    ri.rot("fig", {0: [-90, 0, 0], 0.5: [10, 0, 0], 0.6: [0, 0, 0]})
    r.phase(1, "rise")
    stalk = r.anim("stalk", loop=True)
    step = "math.floor(q.life_time * 5)"
    stalk.rot("limb_l", [f"math.sin({step} * 77) * 35", 0, 0]).rot("limb_r", [f"math.cos({step} * 61) * 35", 0, 0])
    stalk.rot("skull", [0, f"math.sin({step} * 113) * 40", f"math.cos({step} * 97) * 20"])
    stalk.rot("leg_l", [f"math.sin({step} * 90) * 25", 0, 0]).rot("leg_r", [f"-math.sin({step} * 90) * 25", 0, 0])
    r.phase(2, "stalk")
    at = r.anim("strike", length=0.4)
    at.rot("torso", {0: [0, 0, 0], 0.1: [40, 0, 0], 0.4: [0, 0, 0]}).rot("limb_r", {0: [0, 0, 0], 0.1: [-150, 0, 0], 0.3: [30, 0, 0]})
    r.pulse("strike")

    s = Fx("fx_d_spire", D, bounds=(4, 9, (0, 4, 0)), lifetime=600)
    s.bone("col").cbox((0, 50, 0), (6, 100, 6), "d_void", rotation=(0, 45, 0))
    for k in range(6):
        s.bone(f"ps{k}", pivot=(0, 0, 0), rotation=(0, k * 60, 0))
        p = s.bone(f"petal{k}", f"ps{k}", pivot=(0, 4, -4))
        p.cbox((0, 46, -4), (10, 90 - k * 6, 0.8), "d_glass" if k % 2 else "d_plate")
        s.bone(f"g_pe{k}", f"petal{k}", pivot=(0, 4, -4)).cbox((0, 46, -4.6), (0.4, 84 - k * 6, 0.2), "d_jade_line")
    un = s.anim("unfold", length=1.0, loop="hold_on_last_frame")
    for k in range(6):
        un.rot(f"petal{k}", {0: [0, 0, 0], 0.2: [0, 0, 0], 0.9: [24 + (k % 2) * 10, 0, 0]})
    un.scale("fade", {0: [1, 0.05, 1], 0.4: [1, 1, 1]})
    s.phase(1, "unfold")
    s.phase(15, s.default_dissolve(0.6, 0))

    p = Fx("fx_d_plane", D, bounds=(14, 14, (0, 6, 0)), tex=(256, 256), lifetime=900)
    p.bone("hinge", pivot=(0, 0, 0))
    for i in range(4):
        for j in range(4):
            pb = p.bone(f"pn{i}{j}", "hinge", pivot=((i - 1.5) * 48, (j + 0.5) * 48, 0))
            pb.cbox(((i - 1.5) * 48, (j + 0.5) * 48, 0), (47.6, 47.6, 3), "d_glass" if (i + j) % 2 else "d_plate")
    g = p.bone("g_grid", "hinge")
    for k in range(5):
        g.cbox(((k - 2) * 48, 96, -1.8), (0.6, 192, 0.3), "d_jade_line")
        g.cbox((0, k * 48, -1.8), (192, 0.6, 0.3), "d_jade_line")
    for r_ in (20, 44, 70):
        for (x, y, w_, h_) in ((0, 96 - r_, 2 * r_, 0.5), (0, 96 + r_, 2 * r_, 0.5), (-r_, 96, 0.5, 2 * r_), (r_, 96, 0.5, 2 * r_)):
            g.cbox((x, y, -2.0), (w_, h_, 0.3), "d_jade_line")
    p.phase(1, p.default_form(0.8))
    tilt = p.anim("lean", loop=True)
    tilt.rot("hinge", ["math.sin(q.life_time * 40) * 3", 0, 0])
    p.phase(2, "lean")
    fo = p.anim("fold", length=0.6, loop="hold_on_last_frame")
    fo.rot("hinge", {0: [0, 0, 0], 0.5: [88, 0, 0], 0.6: [84, 0, 0]})
    p.phase(3, "fold")
    fr = p.anim("dissolve", length=1.0)
    for i in range(4):
        for j in range(4):
            fr.pos(f"pn{i}{j}", {0: [0, 0, 0], 0.9: [(i - 1.5) * 18, (j - 1.5) * 12, -20 - (i + j) * 4]})
            fr.scale(f"pn{i}{j}", {0: [1, 1, 1], 0.9: [0.1, 0.1, 0.1]})
            fr.rot(f"pn{i}{j}", {0: [0, 0, 0], 0.9: [i * 40, j * 50, 0]})
    p.phase(15, "dissolve")


decoy()
origami()
maw()
glyphs()
eclipse()
velvet()
latch()
curtain()
mosaic()
mask()
silhouette_fx()
step()
double()
footfall()
court()
outline_world()
