"""Prism Light constructs (Grimoire 06): lenses, prisms, mirrors and gratings in champagne gold and glass.
The spectrum only appears where light passes through optics: white-light parts are tinted per variant
(0..6 = red, orange, yellow, green, blue, indigo, violet, 7 = white)."""
import math
from .fxdefs import Fx
from .fxparts import oriented, ring, vibrate
from .fxlib import aim_box, polyline, silhouette
from .texkit import style

R_ = "prism_light"
_PURE = [(1.0, 0.24, 0.24), (1.0, 0.58, 0.18), (1.0, 0.94, 0.3), (0.32, 1.0, 0.45), (0.3, 0.56, 1.0), (0.45, 0.36, 1.0), (0.78, 0.36, 1.0), (1, 1, 1)]
# spectral light, not paint: a quarter of the white is kept so tinted glass and light read as luminous pastels
TINTS = [tuple(round(0.25 + 0.75 * c, 3) for c in t) for t in _PURE]
SPEC = [f"pr_s{i}" for i in range(7)]
style('pr_glass_r', 'grad', c1='#ff9a9a', c2='#ff3c3c', a=118, a2=78)
style('pr_glass_g', 'grad', c1='#9affa8', c2='#38ff58', a=118, a2=78)
style('pr_glass_b', 'grad', c1='#9ab8ff', c2='#3c6cff', a=118, a2=78)
style('pr_dim', 'grad', c1='#4a4e66', c2='#262a3a', a=96, a2=64)
style('pr_band_soft', 'glow', c1='#ffffff', c2='#fff4e0', mode='vband', pow=1.8, floor=0.0)
# a hanging curtain of light: dense at the hem, fading to nothing at the top (translucent, never a wall)
style('pr_curtain_light', 'grad', c1='#fff8ee', c2='#ffffff', a=12, a2=150, noise=0.04)
# afterimage: an even soft glow (additive), no stripes
style('pr_ghost', 'glow', c1='#ffffff', c2='#f4f0ea', mode='radial', pow=0.25, floor=0.62)
style('pr_band_core', 'glow', c1='#ffffff', c2='#fffaf0', mode='vband', pow=0.8, floor=0.3)


def tri_pts(r, rot=90):
    return [(math.cos(math.radians(rot + k * 120)) * r, math.sin(math.radians(rot + k * 120)) * r) for k in range(3)]


def disc(bone, center, radius, thick, st, plane="xz"):
    for k in range(3):
        if plane == "xz":
            bone.cbox(center, (radius * 1.93, thick, radius * 1.93 * 0.52), st, rotation=(0, k * 60, 0))
        else:
            bone.cbox(center, (radius * 1.93, radius * 1.93 * 0.52, thick), st, rotation=(0, 0, k * 60))


def lens(bone, center, radius, st="pr_glass", plane="xz"):
    """Biconvex lens: stacked discs, thickest in the middle."""
    for i, (k, dy) in enumerate(((1.0, 0), (0.78, 1.1), (0.78, -1.1), (0.5, 1.9), (0.5, -1.9))):
        c = (center[0], center[1] + dy, center[2]) if plane == "xz" else (center[0], center[1], center[2] + dy)
        disc(bone, c, radius * k, 0.8, st, plane)


def glass_prism(fx, name, parent, center, r, h, axis="y", gold=True):
    """Triangular prism. axis y: standing; axis z: lying along Z."""
    b = fx.bone(name, parent, pivot=center)
    pts = tri_pts(r)
    for i in range(3):
        a, bb = pts[i], pts[(i + 1) % 3]
        L = math.hypot(bb[0] - a[0], bb[1] - a[1])
        mx, my = (a[0] + bb[0]) / 2, (a[1] + bb[1]) / 2
        ang = math.degrees(math.atan2(bb[1] - a[1], bb[0] - a[0]))
        if axis == "y":
            b.cbox((center[0] + mx, center[1], center[2] + my), (L, h, 0.4), "pr_glass_thick", rotation=(0, -ang, 0))
        else:
            b.cbox((center[0] + mx, center[1] + my, center[2]), (L, 0.4, h), "pr_glass_thick", rotation=(0, 0, ang))
    if gold:
        g = fx.bone(f"{name}_gold", name, pivot=center)
        for end in (-1, 1):
            for i in range(3):
                a, bb = pts[i], pts[(i + 1) % 3]
                if axis == "y":
                    aim_box(g, (center[0] + a[0], center[1] + end * h / 2, center[2] + a[1]), (center[0] + bb[0], center[1] + end * h / 2, center[2] + bb[1]), 0.6, "pr_gold")
                else:
                    aim_box(g, (center[0] + a[0], center[1] + a[1], center[2] + end * h / 2), (center[0] + bb[0], center[1] + bb[1], center[2] + end * h / 2), 0.6, "pr_gold")
    return b


# ------------------------------------------------------------------------------------------ PR01
def verdict():
    p = Fx("fx_pr_prism", R_, bounds=(5, 4, (0, 0, 0)), lifetime=120)
    p.bone("aimer", pivot=(0, 0, 0), rotation=(0, 90, 0))   # dispersion fan (+X) points along the model's forward (-Z)
    glass_prism(p, "t_prism", "aimer", (0, 0, 0), 9, 14, axis="z")
    p.bone("g_in", "aimer", pivot=(-5, 0, 0)).cbox((-15, 2, 0), (20, 1, 1), "pr_beam", rotation=(0, 0, -8))
    fan = p.bone("fan", "aimer", pivot=(5, -1, 0))
    for i in range(7):
        b = p.bone(f"g_out{i}", "fan", pivot=(5, -1, 0), rotation=(0, 0, -6 - i * 6))
        b.cbox((16, -1, 0), (22, 0.9, 0.9), SPEC[i])
    form = p.anim("form", length=0.5)
    form.scale("t_prism", {0: [0.01, 0.01, 0.01], 0.4: [1.08, 1.08, 1.08], 0.5: [1, 1, 1]}).rot("t_prism", {0: [0, 0, -120], 0.5: [0, 0, 0]})
    form.scale("g_in", [0, 0, 0]).scale("fan", [0, 0, 0])
    p.phase(1, "form")
    dis = p.anim("disperse", length=0.6, loop="hold_on_last_frame")
    dis.scale("g_in", {0: [0.01, 1, 1], 0.2: [1, 1, 1]})
    for i in range(7):
        dis.scale(f"g_out{i}", {0: [0, 1, 1], 0.2 + i * 0.04: [0, 1, 1], 0.32 + i * 0.04: [1, 1, 1]})
    dis.rot("t_prism", [0, "math.sin(q.life_time * 90) * 6", 0])
    p.phase(2, "disperse")

    rb = Fx("fx_pr_ribbon", R_, bounds=(2, 2, (0, 0, 0)), lifetime=120)
    prev = None
    for k in range(6):
        b = rb.bone(f"g_seg{k}", prev, pivot=(0, 0, -k * 6))
        b.cbox((0, 0, -k * 6 - 3), (3.2 - k * 0.3, 0.4, 6.4), "pr_beam")
        prev = f"g_seg{k}"
    rb.tints = TINTS
    rb.phase(1, rb.default_form(0.2), "flow")
    fl = rb.anim("flow", loop=True)
    for k in range(1, 6):
        fl.rot(f"g_seg{k}", [f"math.sin(q.life_time * 500 - {k * 50}) * 14", f"math.sin(q.life_time * 400 - {k * 40}) * 10", f"q.life_time * 60"])
    rb.phase(2, "flow")

    st = Fx("fx_pr_star", R_, bounds=(5, 2, (0, 0, 0)), lifetime=60)
    for i in range(7):
        b = st.bone(f"g_ray{i}", pivot=(0, 0, 0), rotation=(0, i * 360 / 7, 0))
        b.cbox((0, 0, -12), (2.6, 0.6, 22), SPEC[i])
        b.cbox((0, 0, -26), (1.2, 0.6, 6), SPEC[i])
    st.bone("g_core").cbox((0, 0, 0), (6, 6, 6), "pr_core", rotation=(45, 45, 0))
    bl = st.anim("form", length=0.35)
    bl.scale("fade", {0: [0.01, 0.01, 0.01], 0.2: [1.3, 1.3, 1.3], 0.35: [1, 1, 1]}).rot("fade", {0: [0, -60, 0], 0.35: [0, 0, 0]})
    st.phase(1, "form", "spin")
    sp = st.anim("spin", loop=True)
    sp.rot("fade", [0, "q.life_time * 120", 0])
    st.phase(2, "spin")


# ------------------------------------------------------------------------------------------ PR02
def internal_reflection():
    t = Fx("fx_pr_tri", R_, bounds=(2, 2, (0, 1, 0)), lifetime=200)
    t.bone("body", pivot=(0, 12, 0))
    glass_prism(t, "t_tri", "body", (0, 12, 0), 6, 20, axis="y")
    t.bone("g_glint", "body").cbox((0, 12, 0), (1.2, 16, 1.2), "pr_beam")
    t.phase(1, t.default_form(0.35), "hum")
    hm = t.anim("hum", loop=True)
    hm.rot("body", [0, "math.sin(q.life_time * 60) * 8", 0]).pos("body", [0, "math.sin(q.life_time * 120) * 0.6", 0])
    t.phase(2, "hum")
    op = t.anim("open", length=0.5, loop="hold_on_last_frame")
    op.scale("t_tri", {0: [1, 1, 1], 0.4: [1.9, 0.6, 1.9]}).rot("t_tri", {0: [0, 0, 0], 0.4: [0, 120, 0]})
    op.scale("g_glint", {0: [1, 1, 1], 0.1: [3, 1.2, 3], 0.4: [0, 0, 0]})
    t.phase(3, "open")

    r = Fx("fx_pr_ray", R_, bounds=(3, 3, (0, 0, 0)), lifetime=200)
    r.bone("stretch", pivot=(0, 0, 0))
    r.bone("g_core", "stretch").cbox((0, 0, -8), (0.8, 0.8, 16), "pr_beam")
    r.bone("t_halo", "stretch").cbox((0, 0, -8), (2.4, 2.4, 16), "pr_glass")
    r.tints = TINTS
    r.phase(1, r.default_form(0.15), "shimmer")
    sh = r.anim("shimmer", loop=True)
    vibrate(sh, "g_core", 0.15, 12)
    r.phase(2, "shimmer")


# ------------------------------------------------------------------------------------------ PR03
def caustic():
    l = Fx("fx_pr_lens", R_, bounds=(7, 2, (0, 0, 0)), lifetime=300)
    lb = l.bone("t_lens")
    lens(lb, (0, 0, 0), 40)
    ring(l, "rim", l.top, (0, 0, 0), 40, 1.6, 2.6, 24, "pr_gold")
    for k in range(3):
        l.bone(f"arm{k}", pivot=(0, 0, 0), rotation=(0, k * 120, 0)).cbox((0, 10, -40), (1.2, 20, 1.2), "pr_gold", rotation=(20, 0, 0))
    l.phase(1, l.default_form(0.6), "tilt")
    tl = l.anim("tilt", loop=True)
    tl.rot("fade", ["math.sin(q.life_time * 40) * 10", "q.life_time * 10", "math.cos(q.life_time * 30) * 8"])
    l.phase(2, "tilt")

    c = Fx("fx_pr_caustic", R_, bounds=(6, 1, (0, 0, 0)), lifetime=300)
    c.bone("flower", pivot=(0, 0, 0))
    for k in range(12):
        pb = c.bone(f"g_petal{k}", "flower", pivot=(0, 0, 0), rotation=(0, k * 30, 0))
        pts = [(math.sin(t / 6 * math.pi) * 6 * s, 0.3, -t / 6 * 36) for t in range(7) for s in (1,)]
        polyline(pb, pts, 0.8, "pr_beam")
        polyline(pb, [(-x, y, z) for (x, y, z) in pts], 0.8, "pr_edge")
    c.bone("g_heart", "flower").cbox((0, 0.4, 0), (5, 0.4, 5), "pr_core", rotation=(0, 45, 0))
    c.phase(1, c.default_form(0.5), "drift")
    dr = c.anim("drift", loop=True)
    dr.rot("flower", [0, "q.life_time * 30", 0]).scale("flower", ["1 + math.sin(q.life_time * 120) * 0.05", 1, "1 + math.sin(q.life_time * 120) * 0.05"])
    c.phase(2, "drift")
    ct = c.anim("contract", length=0.5, loop="hold_on_last_frame")
    ct.scale("flower", {0: [1, 1, 1], 0.45: [0.12, 4, 0.12]}).rot("flower", {0: [0, 0, 0], 0.45: [0, 180, 0]})
    ct.scale("g_heart", {0: [1, 1, 1], 0.45: [5, 3, 5]})
    c.phase(3, "contract")


# ------------------------------------------------------------------------------------------ PR04
def fraunhofer():
    g = Fx("fx_pr_grating", R_, bounds=(11, 7, (0, 3, 0)), tex=(128, 256), lifetime=500)
    g.bone("frame", pivot=(0, 0, 0))
    fb = g.bone("gold", "frame")
    fb.cbox((0, 96, 0), (164, 4, 4), "pr_gold")
    fb.cbox((0, 0, 0), (164, 4, 4), "pr_gold")
    fb.cbox((-80, 48, 0), (4, 96, 4), "pr_gold")
    fb.cbox((80, 48, 0), (4, 96, 4), "pr_gold")
    fb.cbox((0, 48, 0), (160, 1.2, 1.6), "pr_gold_dark")
    sl = g.bone("slats", "frame")
    for k in range(40):
        sl.cbox((-78 + k * 4, 48, 0), (0.9, 94, 1.0), "pr_gold_dark" if k % 5 else "pr_gold")
    g.bone("t_light", "frame").cbox((0, 48, 1.2), (156, 92, 0.4), "pr_glass")
    g.bone("g_glow", "frame").cbox((0, 48, 1.6), (150, 2, 0.2), "pr_beam")
    dep = g.anim("form", length=0.7)
    dep.scale("frame", {0: [1, 0.01, 1], 0.6: [1, 1.04, 1], 0.7: [1, 1, 1]})
    g.phase(1, "form", "hum")
    hm = g.anim("hum", loop=True)
    hm.pos("g_glow", [0, "math.sin(q.life_time * 90) * 40", 0])
    g.phase(2, "hum")

    b = Fx("fx_pr_band", R_, bounds=(3, 1, (0, 0, 0)), lifetime=500)
    b.bone("stretch", pivot=(0, 0, 0))
    # a ribbon of light on the ground: bright along its middle, fading to nothing at the sides (additive, so it
    # reads as light falling on the floor, not as a painted strip), with two thin brighter filaments
    b.bone("g_band", "stretch").cbox((0, 0.3, -8), (30, 0.2, 16), "pr_band_soft")
    b.bone("g_edge", "stretch").cbox((0, 0.5, -8), (1.2, 0.2, 16), "pr_band_core")
    fil = b.bone("g_fil", "stretch", pivot=(0, 0.6, 0))
    for x in (-6, 6):
        fil.cbox((x, 0.6, -8), (0.6, 0.15, 16), "pr_band_core")
    b.tints = TINTS
    b.phase(1, b.default_form(0.3), "shimmer")
    sh = b.anim("shimmer", loop=True)
    sh.scale("g_band", ["1 + math.sin(q.life_time * 400) * 0.06", 1, 1])
    sh.scale("g_fil", ["1 + math.sin(q.life_time * 260) * 0.35", 1, 1])
    b.phase(2, "shimmer")


# ------------------------------------------------------------------------------------------ PR05
def brewster():
    p = Fx("fx_pr_panel", R_, bounds=(2, 3, (0, 1, 0)), lifetime=500)
    p.bone("panel", pivot=(0, 20, 0))
    p.bone("t_pane", "panel").cbox((0, 22, 0), (28, 40, 0.4), "pr_glass_thick")
    fr = p.bone("frame", "panel")
    for (x, y, w_, h) in ((0, 42, 29, 1.4), (0, 2, 29, 1.4), (-14, 22, 1.4, 40), (14, 22, 1.4, 40)):
        fr.cbox((x, y, 0), (w_, h, 1.2), "pr_gold")
    ln = p.bone("lines", "panel", pivot=(0, 22, 0))
    for k in range(9):
        ln.cbox((-12 + k * 3, 22, -0.4), (0.4, 36, 0.3), "pr_gold")
    dep = p.anim("form", length=0.45)
    dep.rot("panel", {0: [0, 90, 0], 0.45: [0, 0, 0]}).scale("panel", {0: [0.2, 1, 1], 0.45: [1, 1, 1]})
    p.phase(1, "form", "hold")
    hd = p.anim("hold", loop=True)
    hd.rot("lines", [0, 0, "math.sin(q.life_time * 50) * 6"])
    p.phase(2, "hold")
    adj = p.anim("adjust", length=0.5)
    adj.rot("lines", {0: [0, 0, 0], 0.15: [0, 0, 90], 0.5: [0, 0, 0]}).rot("panel", {0: [0, 0, 0], 0.15: [0, 28, 0], 0.5: [0, 0, 0]})
    p.pulse("adjust")


# ------------------------------------------------------------------------------------------ PR06
def parallax():
    r = Fx("fx_pr_rgb", R_, bounds=(2, 3, (0, 1, 0)), lifetime=500)
    for name, st, off in (("red", "pr_glass_r", -1), ("green", "pr_glass_g", 0), ("blue", "pr_glass_b", 1)):
        r.bone(f"t_{name}", pivot=(0, 0, 0))
        silhouette(r, f"t_{name}_", f"t_{name}", st, 1.0, inflate=0.4)
    sep = r.anim("form", length=0.5)
    sep.pos("t_red", {0: [0, 0, 0], 0.5: [-3, 0, 0]}).pos("t_blue", {0: [0, 0, 0], 0.5: [3, 0, 0]})
    r.phase(1, "form")
    hold = r.anim("hold", loop=True)
    hold.pos("t_red", ["-0.8 + math.sin(q.life_time * 200) * 0.4", 0, 0]).pos("t_blue", ["0.8 - math.sin(q.life_time * 200) * 0.4", 0, 0])
    r.phase(2, "hold")
    sh = r.anim("shatter", length=0.5, loop="hold_on_last_frame")
    for name, dx in (("red", -10), ("green", 0), ("blue", 10)):
        sh.pos(f"t_{name}", {0: [0, 0, 0], 0.5: [dx, 4, -6]}).scale(f"t_{name}", {0: [1, 1, 1], 0.5: [1.8, 1.8, 0.05]})
    r.phase(3, "shatter")


# ------------------------------------------------------------------------------------------ PR07
def turnstile():
    g = Fx("fx_pr_gate", R_, bounds=(4, 5, (0, 2, 0)), lifetime=500)
    g.bone("gate", pivot=(0, 0, 0))
    gd = g.bone("posts", "gate")
    gd.cbox((-15, 28, 0), (2.4, 58, 2.4), "pr_gold", rotation=(0, 0, -11))
    gd.cbox((15, 28, 0), (2.4, 58, 2.4), "pr_gold", rotation=(0, 0, 11))
    gd.cbox((0, 56, 0), (22, 2.4, 2.4), "pr_gold")
    gd.cbox((0, 1, 0), (38, 2, 3), "pr_gold_dark")
    g.bone("t_lens", "gate").cbox((0, 28, 0), (26, 52, 0.4), "pr_glass")
    ed = g.bone("g_edge", "gate")
    ed.cbox((-13.5, 28, -0.6), (0.8, 54, 0.4), "pr_beam", rotation=(0, 0, -11))
    ed.cbox((13.5, 28, -0.6), (0.8, 54, 0.4), "pr_beam", rotation=(0, 0, 11))
    wv = g.bone("g_waves", "gate", pivot=(0, 28, 0))
    for k in range(4):
        wv.cbox((0, 12 + k * 11, -0.3), (22 - k * 2, 0.5, 0.2), "pr_beam", rotation=(0, 0, (k % 2) * 8 - 4))
    ar = g.bone("g_arrow", "gate", pivot=(0, 0.3, -10))
    ar.cbox((-3, 0.3, -12), (0.8, 0.2, 9), "pr_beam", rotation=(0, -35, 0))
    ar.cbox((3, 0.3, -12), (0.8, 0.2, 9), "pr_beam", rotation=(0, 35, 0))
    g.tints = TINTS
    dep = g.anim("form", length=0.5)
    dep.scale("gate", {0: [1, 0.01, 1], 0.5: [1, 1, 1]})
    g.phase(1, "form", "distort")
    ds = g.anim("distort", loop=True)
    ds.pos("g_waves", [0, "math.sin(q.life_time * 160) * 3", 0]).scale("g_waves", ["1 + math.sin(q.life_time * 220) * 0.1", 1, 1])
    ds.pos("g_arrow", [0, 0, "-math.mod(q.life_time * 8, 6)"])
    g.phase(2, "distort")
    rf = g.anim("refract", length=0.35)
    rf.scale("t_lens", {0: [1, 1, 1], 0.1: [1.2, 1.05, 4], 0.35: [1, 1, 1]})
    g.pulse("refract")


# ------------------------------------------------------------------------------------------ PR08
def kaleidoscope():
    k = Fx("fx_pr_kaleido", R_, bounds=(14, 7, (0, 3, 0)), tex=(256, 256), lifetime=500)
    k.bone("drum", pivot=(0, 0, 0))
    for i in range(12):
        ang = i * 30
        holder = k.bone(f"mh{i}", "drum", pivot=(0, 0, 0), rotation=(0, ang, 0))
        m = k.bone(f"mirror{i}", f"mh{i}", pivot=(0, 0, -96))
        tilt = -14 if i % 2 else 14
        m.cbox((0, 40, -96), (28, 80, 1.2), "pr_mirror", rotation=(tilt, 0, 0))
        k.bone(f"g_mf{i}", f"mirror{i}", pivot=(0, 0, -96)).cbox((0, 40, -97), (29, 1.2, 0.4), "pr_edge", rotation=(tilt, 0, 0))
        m.cbox((-14, 40, -96), (1.2, 80, 1.6), "pr_gold", rotation=(tilt, 0, 0))
    ring(k, "crown_ring", "drum", (0, 82, 0), 98, 2, 2, 24, "pr_gold")
    asm = k.anim("form", length=0.9)
    for i in range(12):
        asm.rot(f"mirror{i}", {0: [-88, 0, 0], 0.4 + i * 0.03: [-88, 0, 0], 0.8 + i * 0.03: [0, 0, 0]})
    k.phase(1, "form")
    rot = k.anim("turn", loop=True)
    rot.rot("drum", [0, "q.life_time * 14", 0])
    for i in range(12):
        rot.rot(f"mirror{i}", [0, f"math.sin(q.life_time * 60 + {i * 30}) * 8", 0])
    k.phase(2, "turn")
    re = k.anim("rearrange", length=0.6)
    for i in range(12):
        re.rot(f"mirror{i}", {0: [0, 0, 0], 0.3: [0, 60 if i % 2 else -60, 0], 0.6: [0, 0, 0]})
    k.pulse("rearrange")

    f = Fx("fx_pr_figure", R_, bounds=(2, 3, (0, 1, 0)), lifetime=500)
    f.bone("fig", pivot=(0, 0, 0))
    silhouette(f, "m_", "fig", "pr_mirror", 1.0)
    silhouette(f, "g_", "fig", "pr_edge", 1.0, inflate=0.5)
    ap = f.anim("form", length=0.4)
    ap.scale("fig", {0: [0.05, 1, 0.05], 0.4: [1, 1, 1]})
    f.phase(1, "form", "idle")
    idl = f.anim("idle", loop=True)
    idl.rot("fig", [0, "math.sin(q.life_time * 30) * 10", 0])
    f.phase(2, "idle")
    sh = f.anim("shimmer", length=0.4)
    sh.scale("fig", {0: [1, 1, 1], 0.1: [1.1, 0.95, 0.4], 0.4: [1, 1, 1]})
    f.pulse("shimmer")


# ------------------------------------------------------------------------------------------ PR09
def tapestry():
    e = Fx("fx_pr_emitter", R_, bounds=(2, 5, (0, 2, 0)), lifetime=500)
    col = e.bone("column")
    for k in range(3):
        a = math.radians(k * 120)
        col.cbox((math.cos(a) * 4, 32, math.sin(a) * 4), (1.4, 64, 1.4), "pr_gold")
    e.bone("t_core", "column").cbox((0, 32, 0), (5, 60, 5), "pr_glass_thick")
    e.bone("g_core", "column").cbox((0, 32, 0), (1.6, 58, 1.6), "pr_beam")
    for k in range(3):
        ring(e, f"g_wave{k}", e.top, (0, 14 + k * 18, 0), 6, 0.5, 0.5, 14, "pr_edge")
    e.phase(1, e.default_form(0.5), "emit")
    em = e.anim("emit", loop=True)
    for k in range(3):
        em.scale(f"g_wave{k}", [f"1 + math.mod(q.life_time * 2 + {k * 0.33}, 1) * 3"] * 3)
    e.phase(2, "emit")

    t = Fx("fx_pr_tapestry", R_, bounds=(4, 5, (0, 2, -2)), lifetime=500)
    t.bone("stretch", pivot=(0, 0, 0))
    br = t.bone("g_bright", "stretch", pivot=(0, 0, 0))
    dk = t.bone("t_dark", "stretch", pivot=(0, 0, 0))
    for k in range(8):
        y = 4 + k * 8
        if k % 2 == 0:
            br.cbox((0, y, -8), (0.4, 4, 16), "pr_beam")
        else:
            dk.cbox((0, y, -8), (0.6, 4, 16), "pr_dim")
    t.phase(1, t.default_form(0.5), "shift")
    sh = t.anim("shift", loop=True)
    sh.pos("g_bright", [0, "math.mod(q.life_time * 6, 16) - 8", 0]).pos("t_dark", [0, "math.mod(q.life_time * 6, 16) - 8", 0])
    t.phase(2, "shift")


# ------------------------------------------------------------------------------------------ PR10
def rayline():
    w = Fx("fx_pr_waypoint", R_, bounds=(2, 2, (0, 0, 0)), lifetime=120)
    core = w.bone("core")
    for i, (s, y) in enumerate(((5, 0), (3.6, 2.4), (2, 4.2), (3.6, -2.4), (2, -4.2))):
        core.cbox((0, y, 0), (s, 2.4, s), "pr_glass_thick", rotation=(0, 45, 0))
    w.bone("g_heart", "core").cbox((0, 0, 0), (1.4, 1.4, 1.4), "pr_core", rotation=(45, 45, 0))
    ring(w, "gyro", w.top, (0, 0, 0), 6, 0.6, 0.6, 12, "pr_gold", rx=90)
    w.phase(1, w.default_form(0.3), "spin")
    sp = w.anim("spin", loop=True)
    sp.rot("core", [0, "q.life_time * 160", 0]).rot("gyro", [0, "q.life_time * 240", 0])
    w.phase(2, "spin")

    a = Fx("fx_pr_afterimage", R_, bounds=(2, 3, (0, 1, 0)), lifetime=60)
    a.bone("cut", pivot=(0, 0, 0))
    silhouette(a, "g_", "cut", "pr_ghost", 1.0)
    a.tints = TINTS
    pop = a.anim("form", length=0.2)
    pop.scale("cut", {0: [1.2, 1.2, 0.05], 0.2: [1, 1, 0.08]})
    a.phase(1, "form")
    a.phase(15, a.default_dissolve(0.4, 0))


# ------------------------------------------------------------------------------------------ PR11
def sail():
    s = Fx("fx_pr_sail", R_, bounds=(6, 3, (0, 2, 0)), lifetime=400)
    s.bone("rig", pivot=(0, 40, 0))
    s.bone("spine", "rig", pivot=(0, 40, 0)).cbox((0, 40, 4), (1.4, 1.4, 64), "pr_gold")
    for side, sgn in (("l", 1), ("r", -1)):
        h = s.bone(f"wing_{side}", "rig", pivot=(0, 40, 0))
        for row in range(4):
            w_ = 30 - row * 7
            z = -16 + row * 14
            s.bone(f"t_pane_{side}{row}", f"wing_{side}", pivot=(0, 40, z)).cbox((sgn * w_ / 2, 40, z), (w_, 0.4, 13), "pr_iris")
        aim_box(h, (0, 40, -28), (sgn * 32, 40, 36), 1.0, "pr_gold")
        aim_box(h, (sgn * 32, 40, 36), (0, 40, 36), 0.8, "pr_gold")
        s.bone(f"g_lead_{side}", f"wing_{side}", pivot=(0, 40, 0))
        aim_box(s[f"g_lead_{side}"], (0, 40.6, -28), (sgn * 32, 40.6, 36), 0.4, "pr_edge")
    for k in range(3):
        aim_box(s.bone(f"cord{k}", "rig", pivot=(0, 0, 0)), (0, 2, 0), ((k - 1) * 16, 40, 12), 0.25, "pr_gold_dark")
    op = s.anim("form", length=0.6)
    op.rot("wing_l", {0: [0, 0, -80], 0.6: [0, 0, 0]}).rot("wing_r", {0: [0, 0, 80], 0.6: [0, 0, 0]})
    s.phase(1, "form", "glide")
    gl = s.anim("glide", loop=True)
    gl.rot("wing_l", [0, 0, "math.sin(q.life_time * 80) * 5"]).rot("wing_r", [0, 0, "-math.sin(q.life_time * 80 + 30) * 5"])
    gl.rot("rig", ["math.sin(q.life_time * 50) * 3", 0, "math.sin(q.life_time * 35) * 4"])
    s.phase(2, "glide")
    rt = s.anim("dissolve", length=0.5)
    rt.rot("wing_l", {0: [0, 0, 0], 0.4: [0, 0, -85]}).rot("wing_r", {0: [0, 0, 0], 0.4: [0, 0, 85]}).scale("rig", {0: [1, 1, 1], 0.5: [0, 0, 0]})
    s.phase(15, "dissolve")


# ------------------------------------------------------------------------------------------ PR12
def diagnosis():
    s = Fx("fx_pr_spectroscope", R_, bounds=(3, 3, (0, 0, 0)), lifetime=300)
    s.bone("inst", pivot=(0, 0, 0))
    tube = s.bone("tube", "inst")
    tube.cbox((0, 0, 0), (4, 4, 26), "pr_gold")
    tube.cbox((0, 0, 0), (4, 4, 26), "pr_gold_dark", rotation=(0, 0, 45))
    tube.cbox((0, 0, 14), (5.4, 5.4, 3), "pr_gold")
    s.bone("t_obj", "inst").cbox((0, 0, -13.5), (6, 6, 0.6), "pr_glass_thick")
    col = s.bone("collimator", "inst", pivot=(0, 0, 0))
    col.cbox((6, 0, -2), (8, 2.4, 2.4), "pr_gold_dark")
    glass_prism(s, "t_mid", "inst", (0, 5, 0), 3, 4, axis="y")
    ring(s, "dial", "inst", (0, 0, 4), 4.4, 0.6, 1.2, 12, "pr_gold", rx=90)
    plate = s.bone("readout", "inst", pivot=(0, 8, 0))
    for i in range(7):
        s.bone(f"g_line{i}", "readout", pivot=(-6 + i * 2, 9, 0)).cbox((-6 + i * 2, 9.5, 0), (1.4, 3, 0.3), SPEC[i])
    s.bone("stretch", pivot=(0, 0, -14))
    s.bone("g_scan", "stretch").cbox((0, 0, -22), (0.4, 0.4, 16), "pr_beam")
    asm = s.anim("form", length=0.7)
    asm.scale("inst", {0: [0.2, 0.2, 0.2], 0.6: [1.05, 1.05, 1.05], 0.7: [1, 1, 1]}).rot("inst", {0: [0, -180, 0], 0.7: [0, 0, 0]})
    asm.scale("g_scan", [0, 0, 0])
    s.phase(1, "form")
    sc = s.anim("scan", loop=True)
    sc.rot("t_mid", [0, "q.life_time * 240", 0]).rot("dial", [0, "q.life_time * 180", 0])
    vibrate(sc, "g_scan", 0.3, 18)
    for i in range(7):
        sc.scale(f"g_line{i}", [1, 0, 1])
    s.phase(2, "scan")
    an = s.anim("analyze", length=0.8, loop="hold_on_last_frame")
    for i in range(7):
        an.scale(f"g_line{i}", {0: [1, 0, 1], 0.1 * i + 0.001: [1, 0, 1], 0.1 * i + 0.15: [1, 1 + (i * 37 % 5) * 0.3, 1]})
    an.rot("t_mid", [0, "q.life_time * 60", 0])
    s.phase(3, "analyze")

    w = Fx("fx_pr_weakpoint", R_, bounds=(2, 2, (0, 0, 0)), lifetime=400)
    w.bone("reticle", pivot=(0, 0, 0))
    for i in range(7):
        w.bone(f"g_bar{i}", "reticle", pivot=(0, 0, 0), rotation=(0, 0, i * 360 / 7)).cbox((0, 7, 0), (1.6, 3.2, 0.3), SPEC[i])
    cr = w.bone("cross", "reticle")
    for k in range(4):
        cr.cbox((0, 0, 0), (0.5, 18, 0.3), "pr_gold", rotation=(0, 0, k * 45))
    w.bone("g_center", "reticle").cbox((0, 0, 0), (1.6, 1.6, 1.6), "pr_core", rotation=(45, 0, 45))
    lk = w.anim("form", length=0.4)
    lk.scale("reticle", {0: [2.4, 2.4, 2.4], 0.4: [1, 1, 1]}).rot("reticle", {0: [0, 0, -90], 0.4: [0, 0, 0]})
    w.phase(1, "form", "pulse_loop")
    pl = w.anim("pulse_loop", loop=True)
    pl.rot("reticle", [0, "q.life_time * 90", "q.life_time * 40"]).scale("g_center", ["1 + math.sin(q.life_time * 400) * 0.3"] * 3)
    w.phase(2, "pulse_loop")


# ------------------------------------------------------------------------------------------ PR13
def benediction():
    b = Fx("fx_pr_benediction", R_, bounds=(5, 4, (0, 2, 0)), lifetime=300)
    b.bone("halo", pivot=(0, 40, 0))
    for i in range(7):
        a = math.radians(i * 360 / 7)
        x, z = math.cos(a) * 30, math.sin(a) * 30
        glass_prism(b, f"t_pr{i}", "halo", (x, 40, z), 3.4, 6, axis="y", gold=False)
        b.bone(f"g_glow{i}", "halo", pivot=(x, 40, z)).cbox((x, 40, z), (1.4, 4, 1.4), SPEC[i])
        rb = b.bone(f"g_rib{i}", "halo", pivot=(0, 40, 0))
        pts = []
        for t in range(6):
            rr = 30 * (1 - t / 6)
            aa = a + t * 0.5
            pts.append((math.cos(aa) * rr, 40 - t * 1.4, math.sin(aa) * rr))
        polyline(rb, pts, 0.7, SPEC[i])
    # the white point burns in the middle of the halo, above the head (not in the caster's face)
    core = b.bone("g_white", pivot=(0, 40, 0))
    for i, s in enumerate((8, 6, 3.5)):
        core.cbox((0, 40, 0), (s, s, s), "pr_core", rotation=(i * 30, i * 45, 0))
    ap = b.anim("form", length=0.5)
    ap.scale("halo", {0: [0.2, 0.2, 0.2], 0.5: [1, 1, 1]}).scale("g_white", [0, 0, 0])
    for i in range(7):
        ap.scale(f"g_rib{i}", [0, 0, 0])
    b.phase(1, "form")
    wv = b.anim("weave", length=1.2, loop="hold_on_last_frame")
    wv.rot("halo", [0, "q.life_time * 120", 0]).scale("g_white", {0: [0, 0, 0], 1.0: [0.6, 0.6, 0.6]})
    for i in range(7):
        wv.scale(f"g_rib{i}", {0: [0, 0, 0], 0.1 * i: [0, 0, 0], 0.1 * i + 0.3: [1, 1, 1]})
    b.phase(2, "weave")
    wl = b.anim("white", length=0.8, loop="hold_on_last_frame")
    wl.scale("halo", {0: [1, 1, 1], 0.6: [0.1, 0.1, 0.1]}).rot("halo", [0, "q.life_time * 400", 0])
    wl.scale("g_white", {0: [0.6, 0.6, 0.6], 0.3: [1.6, 1.6, 1.6], 0.8: [1.2, 1.2, 1.2]})
    b.phase(3, "white")


# ------------------------------------------------------------------------------------------ PR14
def observatory():
    o = Fx("fx_pr_observatory", R_, bounds=(14, 9, (0, 1, 0)), tex=(256, 256), lifetime=600)
    o.bone("frame", pivot=(0, 0, 0))
    ring(o, "ring_a", "frame", (0, 0, 0), 70, 2.4, 3, 28, "pr_gold")
    ring(o, "ring_b", "frame", (0, 4, 0), 90, 1.6, 2, 32, "pr_gold_dark", gap=4)
    for k in range(4):
        o.bone(f"strut{k}", "frame", pivot=(0, 0, 0), rotation=(0, k * 90 + 45, 0)).cbox((0, 2, -80), (2, 2, 22), "pr_gold")
    core = o.bone("core", "frame", pivot=(0, 10, 0))
    for i in range(7):
        a = math.radians(i * 360 / 7)
        glass_prism(o, f"t_cp{i}", "core", (math.cos(a) * 20, 10, math.sin(a) * 20), 4, 10, axis="y", gold=False)
        o.bone(f"g_cs{i}", "core", pivot=(0, 10, 0)).cbox((math.cos(a) * 20, 10, math.sin(a) * 20), (1.2, 8, 1.2), SPEC[i])
    o.bone("g_input", "frame", pivot=(0, 10, 0)).cbox((0, 50, 0), (3, 80, 3), "pr_vbeam")
    for k in range(4):
        arm = o.bone(f"arm{k}", "frame", pivot=(0, 10, 0), rotation=(0, k * 90, 0))
        arm.cbox((0, 10, -36), (2.4, 2.4, 50), "pr_gold")
        lp = o.bone(f"lensp{k}", f"arm{k}", pivot=(0, 10, -62))
        lens(o.bone(f"t_lens{k}", f"lensp{k}", pivot=(0, 10, -62)), (0, 10, -62), 16, plane="xz")
        ring(o, f"lrim{k}", f"lensp{k}", (0, 10, -62), 16, 1.2, 1.6, 16, "pr_gold")
        o.bone(f"g_path{k}", f"arm{k}", pivot=(0, 10, 0)).cbox((0, 10, -40), (0.8, 0.8, 44), SPEC[(k * 2) % 7])
    for k in range(3):
        mp = o.bone(f"mirror{k}", "frame", pivot=(0, 20, 0), rotation=(0, k * 120 + 60, 0))
        mp.cbox((0, 24, -48), (16, 12, 1.2), "pr_mirror", rotation=(30, 0, 0))
        mp.cbox((0, 30.5, -48), (17, 1, 1.6), "pr_gold", rotation=(30, 0, 0))
    asm = o.anim("form", length=1.5)
    asm.scale("frame", {0: [0.2, 0.2, 0.2], 1.3: [1.03, 1.03, 1.03], 1.5: [1, 1, 1]})
    for k in range(4):
        asm.scale(f"arm{k}", {0: [0, 0, 0], 0.5 + k * 0.15: [0, 0, 0], 1.0 + k * 0.15: [1, 1, 1]})
    asm.rot("ring_a", {0: [0, 180, 0], 1.5: [0, 0, 0]})
    o.phase(1, "form")
    act = o.anim("active", loop=True)
    act.rot("ring_a", [0, "q.life_time * 18", 0]).rot("ring_b", [0, "-q.life_time * 12", 0]).rot("core", [0, "q.life_time * 60", 0])
    for k in range(4):
        act.rot(f"arm{k}", [0, f"{k * 90} + math.sin(q.life_time * 40 + {k * 70}) * 25", 0])
        act.rot(f"lensp{k}", [f"math.sin(q.life_time * 70 + {k * 50}) * 20", 0, 0])
    for k in range(3):
        act.rot(f"mirror{k}", [0, f"{k * 120 + 60} + math.sin(q.life_time * 50 + {k * 40}) * 30", 0])
    o.phase(2, "active")
    cv = o.anim("converge", length=1.0, loop="hold_on_last_frame")
    for k in range(4):
        cv.rot(f"lensp{k}", {0: [0, 0, 0], 0.8: [-60, 0, 0]}).rot(f"arm{k}", {0: [0, k * 90, 0], 0.8: [0, k * 90, 0]})
    cv.rot("core", [0, "q.life_time * 400", 0]).scale("g_input", {0: [1, 1, 1], 0.8: [2.6, 1, 2.6]})
    o.phase(3, "converge")
    fin = o.anim("flash", length=0.6, loop="hold_on_last_frame")
    fin.scale("core", {0: [1, 1, 1], 0.15: [2.2, 2.2, 2.2], 0.6: [1.4, 1.4, 1.4]})
    o.phase(4, "flash")

    f = Fx("fx_pr_focal", R_, bounds=(3, 5, (0, 2, 0)), lifetime=500)
    f.bone("cone", pivot=(0, 0, 0))
    for i in range(7):
        a = math.radians(i * 360 / 7)
        aim_box(f.bone(f"g_ln{i}", "cone"), (math.cos(a) * 22, 70, math.sin(a) * 22), (0, 0, 0), 0.6, SPEC[i])
    ring(f, "g_spot", "cone", (0, 0.3, 0), 6, 0.6, 0.2, 14, "pr_edge")
    f.bone("g_flare", "cone").cbox((0, 0.5, 0), (3, 1, 3), "pr_core", rotation=(0, 45, 0))
    f.phase(1, f.default_form(0.3), "hunt")
    hn = f.anim("hunt", loop=True)
    hn.rot("cone", [0, "q.life_time * 90", 0]).scale("g_spot", ["1 + math.sin(q.life_time * 500) * 0.15"] * 3)
    f.phase(2, "hunt")
    sk = f.anim("strike", length=0.35)
    sk.scale("g_flare", {0: [1, 1, 1], 0.08: [6, 4, 6], 0.35: [1, 1, 1]})
    f.pulse("strike")

    il = Fx("fx_pr_illumination", R_, bounds=(22, 3, (0, 0, 0)), tex=(256, 256), lifetime=120)
    il.bone("mandala", pivot=(0, 0, 0))
    for r, n, st in ((160, 7, "pr_beam"), (112, 7, "pr_edge"), (72, 3, "pr_beam"), (40, 7, "pr_edge")):
        b = il.bone(f"g_poly{r}", "mandala")
        for k in range(n):
            a1, a2 = math.radians(k * 360 / n), math.radians((k + 1) * 360 / n)
            aim_box(b, (math.cos(a1) * r, 0.5, math.sin(a1) * r), (math.cos(a2) * r, 0.5, math.sin(a2) * r), 1.6, st)
    sp = il.bone("g_spokes", "mandala")
    for k in range(7):
        a = math.radians(k * 360 / 7)
        aim_box(sp, (0, 0.6, 0), (math.cos(a) * 160, 0.6, math.sin(a) * 160), 1.0, SPEC[k])
    unf = il.anim("form", length=0.7)
    unf.scale("mandala", {0: [0.01, 1, 0.01], 0.5: [1.08, 1, 1.08], 0.7: [1, 1, 1]}).rot("mandala", {0: [0, -90, 0], 0.7: [0, 0, 0]})
    il.phase(1, "form", "spin")
    sp2 = il.anim("spin", loop=True)
    sp2.rot("g_poly112", [0, "q.life_time * 40", 0]).rot("g_poly72", [0, "-q.life_time * 60", 0])
    il.phase(2, "spin")


# ------------------------------------------------------------------------------------------ PR15
def coronation():
    c = Fx("fx_pr_colossus", R_, bounds=(5, 6, (0, 2, 0)), lifetime=900)
    c.bone("body", pivot=(0, 32, 0))
    glass_prism(c, "t_big", "body", (0, 32, 0), 20, 60, axis="y")
    sc = c.bone("g_spectrum", "body", pivot=(0, 32, 0))
    for i in range(7):
        sc.cbox((math.cos(i) * 4, 32, math.sin(i) * 4), (0.8, 50, 0.8), SPEC[i])
    c.phase(1, c.default_form(0.8), "turn")
    tn = c.anim("turn", loop=True)
    tn.rot("body", [0, "q.life_time * 40", 0]).rot("g_spectrum", [0, "-q.life_time * 120", 0])
    c.phase(2, "turn")
    still = c.anim("still", loop=True)
    vibrate(still, "g_spectrum", 0.1, 4)
    c.phase(3, "still")

    cu = Fx("fx_pr_curtain", R_, bounds=(11, 13, (0, 6, 0)), tex=(128, 256), lifetime=500)
    for k in range(6):
        s = cu.bone(f"t_strip{k}", pivot=((k - 2.5) * 27, 192, 0))
        s.cbox(((k - 2.5) * 27, 96, 0), (27.4, 192, 0.6), "pr_curtain_light")
    cu.tints = TINTS
    ds = cu.anim("form", length=0.8)
    for k in range(6):
        ds.scale(f"t_strip{k}", {0: [1, 0.01, 1], 0.4 + k * 0.05: [1, 1, 1]})
    cu.phase(1, "form", "wave")
    wv = cu.anim("wave", loop=True)
    for k in range(6):
        wv.rot(f"t_strip{k}", [f"math.sin(q.life_time * 90 + {k * 50}) * 6", 0, 0])
    cu.phase(2, "wave")

    fl = Fx("fx_pr_flower", R_, bounds=(6, 4, (0, 1, 0)), lifetime=200)
    fl.bone("bloom", pivot=(0, 0, 0))
    for layer, (rr, tilt, n) in enumerate(((30, 60, 7), (22, 40, 7), (14, 20, 7))):
        for k in range(n):
            pb = fl.bone(f"p{layer}{k}", "bloom", pivot=(0, 2 + layer * 3, 0), rotation=(0, k * 360 / n + layer * 25, 0))
            inner = fl.bone(f"t_pt{layer}{k}", f"p{layer}{k}", pivot=(0, 2 + layer * 3, 0))
            inner.cbox((0, 2 + layer * 3 + rr / 2, -2), (10 - layer * 2, rr, 0.4), "pr_glass_thick", rotation=(-tilt, 0, 0))
            fl.bone(f"g_pe{layer}{k}", f"p{layer}{k}", pivot=(0, 2 + layer * 3, 0)).cbox((0, 2 + layer * 3 + rr / 2, -2.4), (0.5, rr, 0.3), SPEC[(k + layer) % 7], rotation=(-tilt, 0, 0))
    fl.bone("g_pistil", "bloom").cbox((0, 8, 0), (4, 12, 4), "pr_core")
    bm = fl.anim("form", length=0.7, loop="hold_on_last_frame")
    for layer in range(3):
        for k in range(7):
            bm.scale(f"p{layer}{k}", {0: [0.2, 0.2, 0.2], 0.2 + layer * 0.1: [0.2, 0.2, 0.2], 0.6 + layer * 0.05: [1, 1, 1]})
    fl.phase(1, "form")
    hold = fl.anim("hold", loop=True)
    hold.rot("bloom", [0, "q.life_time * 40", 0])
    fl.phase(2, "hold")
    dsp = fl.anim("disperse", length=0.6, loop="hold_on_last_frame")
    dsp.scale("bloom", {0: [1, 1, 1], 0.5: [2.2, 1.6, 2.2]}).rot("bloom", {0: [0, 0, 0], 0.5: [0, 120, 0]})
    fl.phase(3, "disperse")

    cr = Fx("fx_pr_crown", R_, bounds=(8, 10, (0, 0, 0)), tex=(256, 256), lifetime=900)
    cr.bone("crown", pivot=(0, 0, 0))
    ring(cr, "band", "crown", (0, 0, 0), 48, 3, 10, 28, "pr_gold")
    for k in range(7):
        sp = cr.bone(f"spike{k}", "crown", pivot=(0, 5, 0), rotation=(0, k * 360 / 7, 0))
        hinge = cr.bone(f"sh{k}", f"spike{k}", pivot=(0, 5, -48))
        hinge.cbox((0, 22, -48), (5, 34, 3), "pr_gold", rotation=(-10, 0, 0))
        cr.bone(f"t_sg{k}", f"sh{k}", pivot=(0, 5, -48)).cbox((0, 24, -46.5), (3, 28, 0.6), "pr_glass_thick", rotation=(-10, 0, 0))
        glass_prism(cr, f"t_tip{k}", f"sh{k}", (0, 42, -51), 3, 6, axis="y", gold=False)
        cr.bone(f"g_tip{k}", f"sh{k}", pivot=(0, 42, -51)).cbox((0, 42, -51), (1.4, 4, 1.4), SPEC[k])
    cr.bone("g_core", "crown").cbox((0, 6, 0), (14, 14, 14), "pr_core", rotation=(45, 45, 0))
    lz = cr.bone("lenses", "crown", pivot=(0, 0, 0))
    for i, (y, rr) in enumerate(((-20, 30), (-38, 22), (-54, 14))):
        lens(cr.bone(f"t_fl{i}", "lenses", pivot=(0, y, 0)), (0, y, 0), rr)
        ring(cr, f"flr{i}", "lenses", (0, y, 0), rr, 1, 1.4, 18, "pr_gold")
    cr.bone("g_shaft", "crown").cbox((0, -40, 0), (4, 80, 4), "pr_vbeam")
    asm = cr.anim("form", length=1.2, loop="hold_on_last_frame")
    for k in range(7):
        asm.rot(f"sh{k}", {0: [80, 0, 0], 0.3 + k * 0.08: [80, 0, 0], 0.8 + k * 0.08: [0, 0, 0]})
    asm.scale("lenses", [0, 0, 0]).scale("g_shaft", [0, 0, 0])
    cr.phase(1, "form")
    sh = cr.anim("shine", loop=True)
    sh.scale("g_core", ["1.2 + math.sin(q.life_time * 300) * 0.2"] * 3).rot("band", [0, "q.life_time * 20", 0])
    for i in range(3):
        sh.rot(f"t_fl{i}", [0, f"q.life_time * {(30 + i * 20) * (1 if i % 2 else -1)}", 0])
    cr.phase(2, "shine")
    cl = cr.anim("close", length=0.9, loop="hold_on_last_frame")
    for k in range(7):
        cl.rot(f"sh{k}", {0: [0, 0, 0], 0.8: [-55, 0, 0]})
    cl.scale("g_core", {0: [1.2, 1.2, 1.2], 0.8: [0.2, 0.2, 0.2]}).scale("lenses", {0: [1, 1, 1], 0.6: [0, 0, 0]})
    cr.phase(3, "close")

    bl = Fx("fx_pr_bloom", R_, bounds=(12, 12, (0, 4, 0)), tex=(256, 256), lifetime=200)
    bl.bone("geo", pivot=(0, 48, 0))
    C = (0, 48, 0)
    octa = [(48, 48, 0), (-48, 48, 0), (0, 96, 0), (0, 0, 0), (0, 48, 48), (0, 48, -48)]
    ob = bl.bone("g_octa", "geo", pivot=C)
    for i in range(6):
        for j in range(i + 1, 6):
            if (i // 2) != (j // 2):
                aim_box(ob, octa[i], octa[j], 1.6, "pr_beam")
    cb = bl.bone("g_cube", "geo", pivot=C)
    s = 30
    cube = [(x, 48 + y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
    for i in range(8):
        for j in range(i + 1, 8):
            if sum(1 for k in range(3) if cube[i][k] != cube[j][k]) == 1:
                aim_box(cb, cube[i], cube[j], 1.2, "pr_edge")
    st = bl.bone("g_star", "geo", pivot=C)
    for k in range(7):
        a = math.radians(k * 360 / 7)
        aim_box(st, C, (math.cos(a) * 70, 48 + (k % 2) * 20 - 10, math.sin(a) * 70), 1.0, SPEC[k])
    un = bl.anim("form", length=0.8, loop="hold_on_last_frame")
    un.scale("geo", {0: [0.02, 0.02, 0.02], 0.6: [1.1, 1.1, 1.1], 0.8: [1, 1, 1]})
    un.rot("g_octa", {0: [0, 0, 0], 0.8: [0, 90, 0]}).rot("g_cube", {0: [45, 0, 45], 0.8: [0, 0, 0]})
    bl.phase(1, "form")
    hd = bl.anim("hold", loop=True)
    hd.rot("g_octa", [0, "q.life_time * 50", 0]).rot("g_cube", ["q.life_time * 30", 0, "q.life_time * 20"]).rot("g_star", [0, "-q.life_time * 40", 0])
    bl.phase(2, "hold")
    fb = bl.anim("fold", length=0.7, loop="hold_on_last_frame")
    fb.scale("geo", {0: [1, 1, 1], 0.6: [0.02, 0.02, 0.02]}).rot("geo", {0: [0, 0, 0], 0.6: [0, 270, 0]})
    bl.phase(3, "fold")


verdict()
internal_reflection()
caustic()
fraunhofer()
brewster()
parallax()
turnstile()
kaleidoscope()
tapestry()
rayline()
sail()
diagnosis()
benediction()
observatory()
coronation()
