"""Shared Divine Word constructs: inscription circle, judgment column, sacred target mark,
plus Divine particles and the DW01 sound set."""
from kit import glyphs, synth as sy, tex
from kit.anim import Anim, M
from kit.geo import Model, ring

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def circle_model():
    """Three counter-rotating inscription rings.  Base radius 2 blocks; scale with grimoire:size."""
    m = Model("dw_circle", density=2.0, bounds=(60, 6, (0, 0, 0)))
    root = m.bone("root")
    outer = m.bone("outer", root)
    outer.plane("y", (0, 0.3, 0), 64, 64, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.80, 0.96, 30),), lines=(0.77, 0.99)),
                faces=("up", "down"))
    mid = m.bone("mid", root)
    mid.plane("y", (0, 0.6, 0), 48, 48, tex.magic_circle(FW, "#fffbe8", "#e9c15a", bands=((0.66, 0.9, 18),), lines=(0.62, 0.95),
                                                         star=6, star_r=(0.2, 0.6)), faces=("up", "down"))
    inner = m.bone("inner", root)
    inner.plane("y", (0, 0.9, 0), 26, 26, tex.magic_circle(FW, "#ffffff", WGOLD, bands=((0.5, 0.92, 8),), lines=(0.96,),
                                                           core=0.16, star=4, star_r=(0.1, 0.46)), faces=("up", "down"))
    # eight small standing letter-plates that rise from the rim
    plates = m.bone("plates", root)
    for k in range(8):
        a = k * 45
        g = tex.bitmap_cut(FW[(k * 5 + 2) % len(FW)], WGOLD, glow=1.0, color2="#ffd76a")
        b = m.bone(f"plate{k + 1}", plates, pivot=(0, 0, 0), rot=(0, a, 0))
        b.plane("z", (0, 5, -30), 5, 7, g)
    return m


def circle_anims():
    idle = Anim("spin", loop=True)
    idle.rot("outer", (0, spin(22), 0))
    idle.rot("mid", (0, spin(-38), 0))
    idle.rot("inner", (0, spin(70), 0))
    idle.rot("plates", (0, spin(-22), 0))
    form = Anim("form", length=0.8, loop="hold")
    form.scl("outer", {0: 0.0, 0.5: 1.08, 0.8: 1.0})
    form.scl("mid", {0: 0.0, 0.15: 0.0, 0.6: 1.1, 0.8: 1.0})
    form.scl("inner", {0: 0.0, 0.3: 0.0, 0.7: 1.2, 0.8: 1.0})
    for k in range(8):
        form.pos(f"plate{k + 1}", {0: (0, -9, 0), 0.35 + k * 0.03: (0, -9, 0), 0.8: (0, 0, 0)})
    hold = Anim("hold", loop=True)
    fade = Anim("fade", length=0.6, loop="hold")
    fade.scl("root", {0: 1.0, 0.25: 1.12, 0.6: 0.0})
    for k in range(8):
        fade.pos(f"plate{k + 1}", {0: (0, 0, 0), 0.6: (0, 22, 0)})
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    return [idle, form, hold, fade, hidden]


def column_model(name, c_core, c_glyph, c_ring):
    """Judgment column: 12 blocks tall at size 1.  Grows downward from an inscription seal."""
    H = 192
    m = Model(name, density=1.0, bounds=(12, 28, (0, 6, 0)))
    root = m.bone("root")
    col = m.bone("col", root, pivot=(0, H, 0))
    col.box((0, H / 2, 0), (5, H, 5), tex.vgrad("#ffffff", c_core, var=0.0, glow_top=1.0, glow_bottom=0.9, edge_dark=0))
    curtain = tex.glyph_rows(FW, c_glyph, glow=1.0, color2="#ffffff", fill=0.85, key=f"{name}cur")
    col.plane("z", (0, H / 2, 0), 22, H, curtain)
    col.plane("x", (0, H / 2, 0), 22, H, curtain, variant=1)
    veil = tex.overlay(tex.vgrad(c_core, "#ffffff", var=0, glow_top=0.8, glow_bottom=1.0, edge_dark=0),
                       lambda c, t: _lattice(c, t), f"{name}veil")
    col.plane("z", (0, H / 2, 0), 13, H, veil, rot=(0, 45, 0), pivot=(0, H / 2, 0))
    col.plane("z", (0, H / 2, 0), 13, H, veil, rot=(0, -45, 0), pivot=(0, H / 2, 0), variant=1)
    for i, y in enumerate((24, 66, 108, 150)):
        rb = m.bone(f"ring{i + 1}", col, pivot=(0, y, 0))
        ring(rb, (0, y, 0), 13 + (i % 2) * 2, 12, (5.2, 1.0, 1.0), tex.metal(c_ring, "#fff6cf", "#8a6a26", glow=0.5), axis="y")
        for k in range(6):
            g = tex.bitmap_cut(FW[(i * 6 + k * 3) % len(FW)], c_glyph, glow=1.0, color2="#ffffff")
            rb.box((0, y + 5.5, -(15 + (i % 2) * 2)), (4.5, 6.3, 0), g, rot=(0, k * 60, 0), pivot=(0, y, 0),
                   faces=("north", "south"))
    seal = m.bone("seal", root, pivot=(0, 0, 0))
    seal.plane("y", (0, 1.0, 0), 44, 44, tex.magic_circle(FW, "#ffffff", c_glyph, bands=((0.7, 0.93, 16),), lines=(0.66, 0.97),
                                                          star=5, star_r=(0.2, 0.62), core=0.12), faces=("up", "down"))
    return m


def _lattice(ctx, t):
    ix, iy = tex.px(ctx)
    keep = ((ix + iy) % 3 != 0) & ((iy // 2) % 4 != 3)
    t[..., 3] = keep * 1.0
    return t


def column_anims():
    H = 192
    always = Anim("turn", loop=True)
    for i, r in enumerate((90, -130, 110, -150)):
        always.rot(f"ring{i + 1}", (0, spin(r), 0))
    always.rot("seal", (0, spin(60), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    descend = Anim("descend", length=0.5, loop="hold")       # the inscription falls, the column is drawn behind it
    descend.pos("seal", {0: (0, H, 0), 0.3: (0, 0, 0)}, smooth=False)
    descend.scl("seal", {0: 0.5, 0.3: 1.0, 0.4: 1.5, 0.5: 1.15})
    descend.scl("col", {0: (0.3, 0.0, 0.3), 0.3: (1.25, 1.0, 1.25), 0.42: (0.9, 1.0, 0.9), 0.5: (1.0, 1.0, 1.0)})
    hold = Anim("hold", loop=True)
    hold.scl("col", (_pulse(), 1.0, _pulse()))
    dissolve = Anim("dissolve", length=0.6, loop="hold")     # thins into a thread of letters and lifts away
    dissolve.scl("col", {0: (1.0, 1.0, 1.0), 0.35: (0.25, 1.0, 0.25), 0.6: (0.0, 1.0, 0.0)})
    dissolve.scl("seal", {0: 1.15, 0.6: 0.0})
    for i in range(4):
        dissolve.scl(f"ring{i + 1}", {0: 1.0, 0.6: 3.2})
        dissolve.pos(f"ring{i + 1}", {0: (0, 0, 0), 0.6: (0, 26 + i * 8, 0)})
    return [always, hidden, descend, hold, dissolve]


def _pulse():
    from kit.anim import LIFE
    return LIFE(0.07, 0.35, base=1.0)


def mark_model():
    """Sacred mark that floats above a judged enemy; three petals light as judgments land."""
    m = Model("dw_mark", density=2.0, bounds=(4, 4, (0, 1, 0)), alts=("two", "three"))
    root = m.bone("root")
    halo = m.bone("halo", root, pivot=(0, 6, 0))
    halo.plane("y", (0, 6, 0), 14, 14, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.62, 0.94, 8),), lines=(0.58, 0.98)),
               faces=("up", "down"))
    dim, lit = tex.rgb("#7a6a3a"), None
    for k in range(3):
        b = m.bone(f"petal{k + 1}", root, pivot=(0, 6, 0), rot=(0, k * 120, 0))
        off = tex.bitmap_cut(FW[(k * 4 + 1) % len(FW)], "#8a7440", glow=0.15)
        on = tex.bitmap_cut(FW[(k * 4 + 1) % len(FW)], "#ffffff", glow=1.0, color2=WGOLD)
        mat = tex.alt(on if k == 0 else off, two=(on if k <= 1 else off), three=on)
        b.plane("z", (0, 10.5, -5.5), 5, 7, mat)
    return m


def mark_anims():
    turn = Anim("turn", loop=True)
    turn.rot("halo", (0, spin(140), 0))
    turn.rot("root", (0, spin(-60), 0))
    from kit.anim import LIFE
    turn.pos("root", (0, LIFE(1.2, 1.6), 0))
    appear = Anim("appear", length=0.3, loop="hold")
    appear.scl("root", {0: 0.0, 0.2: 1.3, 0.3: 1.0})
    hold = Anim("hold", loop=True)
    burst = Anim("burst", length=0.35, loop="hold")
    burst.scl("root", {0: 1.0, 0.15: 2.2, 0.35: 0.0})
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    return [turn, appear, hold, burst, hidden]


def build(pack):
    fx = particles(pack)
    # ---- particles
    fx.effect("dw_glyph_rise", None, sprites=[f"glyph{i}" for i in range(1, 9)], count=5, life=(0.9, 1.6), size=(0.16, 0.05),
              shape=("sphere", 0.9), speed=(0.2, 0.7), accel=(0, 0.9, 0), drag=0.6, colors=["#fff3c4ff", "#ffd76aff", "#c9a24a00"])
    fx.effect("dw_glyph_fall", None, sprites=[f"glyph{i}" for i in range(1, 9)], count=4, life=(0.8, 1.3), size=(0.2, 0.08),
              shape=("disc", 1.6), direction=(0, -1, 0), speed=(2.0, 4.0), drag=0.2, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw_spark", "spark", count=14, life=(0.35, 0.8), size=(0.16, 0.0), shape=("sphere", 0.3), speed=(2.5, 6.0),
              accel=(0, -3, 0), drag=1.2, colors=["#ffffffff", "#ffe9a3ff", "#c9a24a00"], spin=(360, 200))
    fx.effect("dw_feather", "feather", count=6, life=(1.6, 2.6), size=(0.22, 0.16), shape=("sphere", 1.8), speed=(0.2, 0.9),
              accel=(0, -1.1, 0), drag=1.6, colors=["#fffdf4ff", "#f3e3a8cc", "#f3e3a800"], blend="blend", spin=(360, 120))
    fx.effect("dw_mote", "dot", count=8, life=(1.0, 2.0), size=(0.07, 0.0), shape=("sphere", 2.5), speed=(0.05, 0.3),
              accel=(0, 0.35, 0), colors=["#fff3c4ff", "#fff3c400"])
    fx.effect("dw_pillar_burst", "beam", count=10, life=(0.3, 0.55), size=(0.14, 0.02), size_y=(1.6, 3.2), shape=("disc", 1.3),
              direction=(0, 1, 0), speed=(6, 12), colors=["#ffffffff", "#fff3c4ff", "#ffd76a00"], facing="lookat_y")
    fx.effect("dw_ring", "ringthin", count=1, life=(0.5, 0.6), size=(0.5, 6.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#ffe9a3cc", "#c9a24a00"])
    fx.effect("dw_halo", "ring", count=1, life=(0.6, 0.8), size=(0.3, 2.6), colors=["#fff3c4ff", "#c9a24a00"])

    # ---- models
    c = circle_model()
    ca = circle_anims()
    pack.actor("dw_circle", c, ca, {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["fade"]}, always=["spin"],
               size_prop=True, lifetime=120, display="Inscription Circle")
    cols = [column_model("dw_column", "#fff1c0", WGOLD, GOLD), column_model("dw_column_silver", "#eef2ff", "#dfe8ff", SILVER),
            column_model("dw_column_verdict", "#ffe08a", "#ffffff", "#e9c15a")]
    cola = column_anims()
    pack.actor("dw_column", cols[0], cola, {0: ["hidden"], 1: ["descend"], 2: ["hold"], 3: ["dissolve"]}, always=["turn"],
               kinds=cols[1:], size_prop=True, lifetime=60, display="Column of Judgment", blend=0.0)
    mk = mark_model()
    mka = mark_anims()
    pack.actor("dw_mark", mk, mka, {0: ["hidden"], 1: ["appear"], 2: ["hold"], 3: ["burst"]}, always=["turn"],
               lifetime=120, display="Sacred Mark", blend=0.0)
    by = {a.name: a for a in cola}
    pack.preview("dw_column", cols[0], [(by["hold"], 0.2)], views=((20, 10), (0, 60)))
    pack.preview("dw_circle", c, [(ca[2], 0.0)], views=((0, 75), (25, 25)))

    # ---- sounds (original synthesis): Seraphic Litany
    def chord(root_hz, vowel, dur, third=1.25, fifth=1.5, bright=1.0):
        return sy.mixdown([sy.choir(root_hz, dur, vowel, bright=bright), sy.choir(root_hz * third, dur, vowel, voices=4),
                           sy.choir(root_hz * fifth, dur, vowel, voices=4), sy.choir(root_hz * 2, dur, "ee", voices=3) * 0.5])
    arrive = sy.at(2.0, (0.0, sy.pad(146.8, 1.9, cutoff=1400) * 0.5), (0.2, sy.choir(293.7, 1.6, "oo") * 0.7),
                   (0.5, sy.shimmer(1.4, 2200, 22) * 0.35), (1.25, sy.bell(1174.7, 0.9) * 0.45))
    sy.save(pack, "dw_seraph_arrive", sy.reverb(arrive, 1.8, 0.4), max_distance=64)
    sy.save(pack, "dw_unfurl", sy.reverb(sy.at(1.2, (0.0, sy.whoosh(0.55, 500, 2600) * 0.5), (0.3, sy.whoosh(0.5, 700, 3200) * 0.5),
                                               (0.6, sy.whoosh(0.5, 900, 4200) * 0.55), (0.55, sy.shimmer(0.8, 2600, 12) * 0.3)), 1.0, 0.3))
    sy.save(pack, "dw_chant1", sy.reverb(chord(196.0, "ah", 1.25, 1.189, 1.498), 2.0, 0.42), max_distance=72)
    sy.save(pack, "dw_chant2", sy.reverb(chord(233.1, "oh", 1.25, 1.26, 1.498), 2.0, 0.42), max_distance=72)
    sy.save(pack, "dw_chant3", sy.reverb(chord(293.7, "ah", 1.5, 1.26, 1.498, bright=1.3), 2.4, 0.45), max_distance=72)
    col = sy.at(1.0, (0.0, sy.whoosh(0.3, 3000, 400) * 0.6), (0.24, sy.thump(0.7, 130, 36, 0.5)), (0.25, sy.bell(587.3, 1.1) * 0.5),
                (0.25, sy.choir(587.3, 0.7, "ah", voices=3, attack=0.02, release=0.4) * 0.4))
    sy.save(pack, "dw_column", sy.reverb(col, 1.4, 0.35), variants=[sy.reverb(sy.pitch(col, 1.12), 1.4, 0.35),
                                                                    sy.reverb(sy.pitch(col, 0.9), 1.4, 0.35)], max_distance=64)
    verdict = sy.at(1.8, (0.0, sy.thump(1.2, 150, 30, 0.7)), (0.0, sy.crack(0.5, 5000, 10) * 0.4),
                    (0.02, chord(146.8, "ah", 1.6, 1.26, 1.498, bright=1.4) * 0.8), (0.05, sy.bell(293.7, 1.6) * 0.6),
                    (0.1, sy.bell(880, 1.4) * 0.3))
    sy.save(pack, "dw_verdict", sy.reverb(verdict, 2.6, 0.45), max_distance=80)
    dep = sy.at(1.4, (0.0, sy.choir(392, 1.3, "oo", release=0.9) * 0.6), (0.2, sy.shimmer(1.1, 3000, 16)[::-1] * 0.35),
                (0.0, sy.whoosh(1.0, 400, 3000) * 0.3))
    sy.save(pack, "dw_depart", sy.reverb(dep, 1.8, 0.45))
    sy.save(pack, "dw_mark", sy.reverb(sy.at(0.5, (0.0, sy.pluck(1318.5, 0.4, 0.8) * 0.8), (0.07, sy.pluck(1975.5, 0.4, 0.8) * 0.6)), 0.8, 0.3),
            volume=0.7, max_distance=32)
    sy.save(pack, "dw_circle", sy.reverb(sy.at(1.0, (0.0, sy.scribble(0.8, 7) * 0.5), (0.0, sy.pad(293.7, 1.0, cutoff=2400) * 0.4),
                                               (0.5, sy.bell(880, 0.6) * 0.35)), 1.2, 0.35))
