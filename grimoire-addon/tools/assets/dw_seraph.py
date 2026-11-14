"""Seraphim -- six-winged celestial of the Divine Word (DW01, DW05).

Original design: a veiled, flame-hearted figure.  Upper wing pair veils the face, lower
pair wraps the trailing inscription-ribbons, middle pair flies.  Feathers carry luminous
inscription overlays that appear when it chants.
"""
import numpy as np

from kit import glyphs, tex
from kit.anim import LIFE, Anim, S
from kit.geo import Mat, Model, ring
from kit.parts import feather_wing, flutter, sym, wave

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"


inscription = tex.inscription


def face_mat():
    """Serene mask: closed eyes and a vertical line of light."""
    art = ["       ", "       ", "##   ##", "  # #  ", "   #   ", "   #   ", "   #   ", "       ", "  ###  ", "       "]
    return tex.stamped(tex.porcelain(IVORY, "#e2d6bd", crack=0.0, gilt=GOLD), art, GOLD, glow=0.55, key="seraface")


def build_model():
    m = Model("seraph", density=1.0, bounds=(40, 34, (0, 12, 0)), alts=("inscribed",))
    ivory = tex.marble(IVORY, "#d9cfb8", scale=6)
    robe = tex.vgrad("#fbf7ec", "#e3d6b4", var=0.03, glow_bottom=0.25)
    gold = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0)
    gold_t = tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=3.0, glow=0.15)
    blue = tex.trimmed(tex.speck(BLUE, 0.05, edge_dark=0.2), GOLD, 1, 0, glow=0.2)
    flame = tex.shaped(tex.m_leaf(), "#fff8d8", "#ffd060", glow=1.0, var=0, key="seraflame")
    def fz(base, tip, rachis, **kw):   # feather that gains luminous inscriptions in the 'inscribed' skin
        return tex.alt(tex.feather(base, tip, rachis, **kw),
                       inscribed=tex.feather(base, tip, rachis, glyph_color="#fffbe6", glyph_glow=1.0,
                                             **{**kw, "glow": 0.3, "glow_tip": 0.75}))
    f_main = [fz("#fbf8ee", "#f3e3a8", GOLD, glow=0.05, glow_tip=0.35),
              fz("#f6f1e2", "#ecd590", "#b8923a", glow=0.05, glow_tip=0.3, notch=0.1)]
    f_up = [fz("#fdfbf4", "#dfe6ff", SILVER, glow=0.08, glow_tip=0.45),
            fz("#f4f1ea", "#c9d4ff", "#aab2c8", glow=0.08, glow_tip=0.4)]
    f_low = [fz("#f7efd8", "#e8c468", GOLD, glow=0.05, glow_tip=0.4),
             fz("#f2e7c8", "#d9b04a", "#a17a28", glow=0.05, glow_tip=0.35)]
    covert = tex.feather("#fffdf6", "#f2ead2", "#d9c7a0", glow=0.04, taper=0.9, notch=0.0)

    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 62, 0))
    # torso: layered ivory vestments with gold bands and a blue stole
    body.cube((-7, 74, -4), (14, 14, 8), tex.trimmed(ivory, GOLD, 1, 1, glow=0.2))
    body.cube((-8, 85, -4.5), (16, 3, 9), gold)                      # collar / pauldron band
    body.cube((-5, 62, -3), (10, 12, 6), ivory, variant=1)
    body.cube((-6, 60.5, -3.5), (12, 2, 7), gold_t)                   # girdle
    body.cube((-2, 62, -4.6), (4, 26, 1), blue)                       # stole (front)
    body.cube((-6.5, 50, -3.5), (13, 11, 7), robe)
    body.cube((-7.5, 40, -4), (15, 10.5, 8), robe, variant=1)
    body.cube((-8.5, 30, -4.5), (17, 10.5, 9), robe, variant=2)
    body.cube((-9, 28.5, -5), (18, 2, 10), gold_t, variant=1)         # hem band
    core = m.bone("core", body, pivot=(0, 79, -4.8))
    core.plane("z", (0, 79, -4.8), 7, 10, flame)
    core.plane("z", (0, 79, -5.0), 3.5, 6, tex.glow_flat("#ffffff", 1.0, core="#fffbe0"))

    # trailing inscription ribbons instead of legs
    rb_mat = tex.overlay(tex.fabric("#fbf5e3", None, 0.04, glow=0.2, fringe=True), lambda c, t: t, "rib")
    rb_glyph = inscription(GOLD, 0.9, 0.7, key="ribg")
    for i, (rx, rz) in enumerate([(-6, -3), (0, -4.5), (6, -3), (-6, 3.5), (0, 4.5), (6, 3.5)]):
        par = body.name
        for s in range(3):
            y1 = 29 - s * 9
            b = m.bone(f"ribbon{i + 1}_{s + 1}", par, pivot=(rx, y1, rz))
            b.plane("z", (rx, y1 - 4.5, rz), 4, 9, rb_mat, variant=(i + s) % 3)
            b.plane("z", (rx, y1 - 4.5, rz - 0.2 if rz < 0 else rz + 0.2), 4, 9, rb_glyph, variant=(i * 3 + s) % 4)
            par = b.name

    # head: veiled mask, crown ring, great halo with orbiting letters
    head = m.bone("head", body, pivot=(0, 88, 0))
    head.cube((-2, 88, -2), (4, 2.5, 4), ivory)
    head.cube((-4, 90, -4), (8, 10, 8), tex.porcelain(IVORY, "#e2d6bd", crack=0.0), mats={"north": face_mat()})
    head.cube((-4.5, 97, -4.5), (9, 3.5, 9), gold_t)                  # diadem
    head.cube((-1, 100.5, -5), (2, 4, 1), gold)
    head.plane("z", (0, 105.5, -4.6), 3, 4, flame)
    crown = m.bone("crown", head, pivot=(0, 104, 0), rot=(8, 0, 0))
    ring(crown, (0, 104, 0), 7.5, 12, (4.2, 1.2, 1.2), gold_t, axis="y", cycle=2)
    halo = m.bone("halo", head, pivot=(0, 95, 6))
    ring(halo, (0, 95, 6), 19, 28, (4.6, 1.6, 1.0), gold, axis="z", cycle=2)
    ring(halo, (0, 95, 6.2), 15.5, 22, (4.7, 0.8, 0.6), gold_t, axis="z")
    for k in range(8):   # rays
        a = k * 45 + 22.5
        halo.box((0, 95 + 24, 6.1), (1.2, 9, 0.4), gold_t, rot=(0, 0, a), pivot=(0, 95, 6.1))
    hg = m.bone("halo_glyphs", head, pivot=(0, 95, 6.6))
    seqi = glyphs.seq(3, 12)
    for k in range(12):
        a = k * 30
        gmat = tex.bitmap_cut(glyphs.FIRST_WORD[seqi[k] % len(glyphs.FIRST_WORD)], WGOLD, glow=1.0, color2="#ffd76a")
        hg.box((0, 95 + 24.5, 6.6), (3.6, 5, 0), gmat, rot=(0, 0, a), pivot=(0, 95, 6.6), faces=("north", "south"))

    # arms with long sleeves
    for s, sx in (("r", 1), ("l", -1)):
        up = m.bone(f"arm_{s}_1", body, pivot=(sx * 8.5, 85, 0))
        up.box((sx * 8.5, 79, 0), (3.4, 12, 3.6), ivory, variant=2)
        up.box((sx * 8.5, 85.5, 0), (4.6, 3, 4.8), gold)
        lo = m.bone(f"arm_{s}_2", up, pivot=(sx * 8.5, 73, 0))
        lo.box((sx * 8.5, 68, 0), (4.2, 10, 4.4), robe, variant=1)
        lo.box((sx * 8.5, 63.6, 0), (4.8, 1.4, 5), gold_t)
        lo.box((sx * 8.5, 61.5, 0), (2.4, 3.2, 1.6), tex.porcelain(IVORY, "#e2d6bd", crack=0.0))

    # six wings
    wings = {}
    for s, sx in (("r", 1), ("l", -1)):
        wings[f"wm_{s}"] = feather_wing(
            m, f"wm_{s}", body, (sx * 5.5, 82, 4.5), sx, [24, 28, 20],
            [dict(n=4, l0=24, l1=32, w=9, a0=3, a1=10, covert=(11, 7)),
             dict(n=5, l0=34, l1=42, w=9, a0=12, a1=27, covert=(13, 7)),
             dict(n=4, l0=42, l1=47, w=9, a0=31, a1=55, covert=(13, 7))],
            gold, f_main, covert, tip_feathers=dict(n=4, l=47, w=9, a0=60, a1=88))
        wings[f"wu_{s}"] = feather_wing(
            m, f"wu_{s}", body, (sx * 3.5, 87.5, 3.5), sx, [15, 18, 13],
            [dict(n=3, l0=16, l1=22, w=8, a0=3, a1=10, covert=(8, 6)),
             dict(n=4, l0=24, l1=30, w=8, a0=12, a1=28, covert=(9, 6)),
             dict(n=3, l0=30, l1=33, w=8, a0=32, a1=56, covert=(9, 6))],
            gold_t, f_up, covert, arm_thick=2.4, tip_feathers=dict(n=3, l=33, w=8, a0=62, a1=88))
        wings[f"wl_{s}"] = feather_wing(
            m, f"wl_{s}", body, (sx * 5, 64, 4), sx, [15, 19, 14],
            [dict(n=3, l0=20, l1=27, w=8, a0=3, a1=10, covert=(9, 6)),
             dict(n=4, l0=29, l1=36, w=8, a0=12, a1=28, covert=(10, 6)),
             dict(n=3, l0=36, l1=40, w=8, a0=32, a1=56, covert=(10, 6))],
            gold, f_low, covert, arm_thick=2.6, tip_feathers=dict(n=3, l=40, w=8, a0=62, a1=88))
    return m, wings


# wing pose presets (right side; mirrored automatically): (a1, a2, a3) rotations
SPREAD = dict(wu=((0, 0, 34), (0, 0, 6), (0, 0, 4)), wm=((0, 0, 6), (0, 0, 0), (0, 0, -2)),
              wl=((0, 0, -30), (0, 0, -8), (0, 0, -6)))
VEIL = dict(wu=((0, 74, 26), (0, 66, -6), (0, 34, -4)), wm=((0, 14, 4), (0, 10, -6), (0, 6, -8)),
            wl=((0, 62, -44), (0, 64, -4), (0, 38, 0)))
COCOON = dict(wu=((0, 80, 20), (0, 70, -8), (0, 40, -4)), wm=((0, 68, -8), (0, 62, -10), (0, 40, -6)),
              wl=((0, 66, -48), (0, 66, -4), (0, 40, 0)))


def _set_wings(a, t_to_pose):
    """t_to_pose: {time: preset}.  Writes keyframes for all three wing pairs."""
    for w in ("wu", "wm", "wl"):
        for j in range(3):
            keys = {t: p[w][j] for t, p in t_to_pose.items()}
            if len(keys) == 1:
                sym(a, f"{w}_{{s}}_a{j + 1}", rot=next(iter(keys.values())))
            else:
                sym(a, f"{w}_{{s}}_a{j + 1}", rot=keys)


def _mix(p, q, f):
    return {w: tuple(tuple(p[w][j][k] + (q[w][j][k] - p[w][j][k]) * f for k in range(3)) for j in range(3)) for w in p}


def _mod(p, **kw):
    """Copy of a preset with per-wing additive tweaks: wu=((dx,dy,dz) for a1, a2, a3)."""
    out = {w: tuple(tuple(v) for v in p[w]) for w in p}
    for w, d in kw.items():
        out[w] = tuple(tuple(out[w][j][k] + d[j][k] for k in range(3)) for j in range(3))
    return out


def build_anims(wings):
    A = []
    feathers_all = [f for w in wings.values() for f in w["feathers"] if "_t" in f or "_f3_" in f]

    hover = Anim("hover", loop=True)
    hover.pos("body", (0, LIFE(2.2, 4.2), 0))
    hover.rot("body", (LIFE(1.6, 5.6), 0, 0))
    hover.rot("halo", (0, 0, M_spin(14)))
    hover.rot("halo_glyphs", (0, 0, M_spin(-26)))
    hover.rot("crown", (0, M_spin(40), 0))
    hover.scl("core", LIFE(0.12, 1.4, base=1.0))
    for i in range(6):
        wave(hover, [f"ribbon{i + 1}_{s + 1}" for s in range(3)], 0, 9, 3.2, lag=0.18, grow=1.3, clock="q.life_time")
        hover.rot(f"ribbon{i + 1}_1", (LIFE(8, 3.2, i * 0.13), 0, LIFE(5, 4.1, i * 0.21)))
    flutter(hover, feathers_all, amp=2.4, period=2.8)
    A.append(hover)

    flap = Anim("flap", loop=True, length=3.0)   # middle pair keeps it aloft
    sym(flap, "wm_{s}_a1", rot=(0, S(5, 3.0, 0.1), S(11, 3.0)))
    sym(flap, "wm_{s}_a2", rot=(0, 0, S(9, 3.0, -0.12)))
    sym(flap, "wm_{s}_a3", rot=(0, 0, S(8, 3.0, -0.24)))
    A.append(flap)

    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    arrive = Anim("arrive", length=1.5, loop="hold")
    arrive.scl("root", {0: 0.05, 0.35: (0.5, 0.25, 0.5), 0.95: (0.95, 1.05, 0.95), 1.3: 1.0})
    arrive.pos("root", {0: (0, -30, 0), 1.0: (0, 4, 0), 1.5: (0, 0, 0)})
    arrive.rot("root", {0: (0, -220, 0), 1.3: (0, 0, 0)})
    _set_wings(arrive, {0: COCOON, 0.9: COCOON, 1.5: VEIL})
    sym(arrive, "arm_{s}_1", rot={0: (-20, 0, 0), 1.5: (-52, 0, -8)})
    sym(arrive, "arm_{s}_2", rot={0: (-40, 0, 0), 1.5: (-78, 0, -20)})
    arrive.rot("head", {0: (24, 0, 0), 1.5: (12, 0, 0)})
    A.append(arrive)

    veiled = Anim("veiled", loop=True)
    _set_wings(veiled, {0: VEIL})
    sym(veiled, "arm_{s}_1", rot=(-52, 0, -8))            # hands pressed together in prayer
    sym(veiled, "arm_{s}_2", rot=(-78, 0, -20))
    veiled.rot("head", (12, 0, 0))
    A.append(veiled)

    unfurl = Anim("unfurl", length=1.3, loop="hold")
    half = _mix(VEIL, SPREAD, 0.5)
    for w, (t0, t1) in (("wl", (0.0, 0.5)), ("wm", (0.22, 0.82)), ("wu", (0.55, 1.2))):   # sequential opening
        for j in range(3):
            sym(unfurl, f"{w}_{{s}}_a{j + 1}", rot={0: VEIL[w][j], t0: VEIL[w][j], (t0 + t1) / 2 + 0.05 * j: half[w][j],
                                                  t1 + 0.03 * j: SPREAD[w][j], 1.3: SPREAD[w][j]})
    sym(unfurl, "arm_{s}_1", rot={0: (-52, 0, -8), 0.6: (-52, 0, -8), 1.3: (-18, 0, 24)})
    sym(unfurl, "arm_{s}_2", rot={0: (-78, 0, -20), 0.6: (-78, 0, -20), 1.3: (-30, 0, 6)})
    unfurl.rot("head", {0: (12, 0, 0), 0.7: (12, 0, 0), 1.3: (-6, 0, 0)})
    unfurl.pos("root", {0: (0, 0, 0), 0.9: (0, 3, 0), 1.3: (0, 5, 0)})
    A.append(unfurl)

    open_idle = Anim("open", loop=True)
    _set_wings(open_idle, {0: SPREAD})
    sym(open_idle, "arm_{s}_1", rot=(-18, 0, 24))
    sym(open_idle, "arm_{s}_2", rot=(-30, 0, 6))
    open_idle.rot("head", (-6, 0, 0))
    open_idle.pos("root", (0, 5, 0))
    A.append(open_idle)

    # three chants: each a different ceremonial gesture, ending held
    c1p = _mod(SPREAD, wu=((0, 0, 22), (0, 0, 10), (0, 0, 8)), wm=((0, -10, 8), (0, 0, 4), (0, 0, 4)))
    chant1 = Anim("chant1", length=1.5, loop="hold")      # upper pair lifts into a V, right hand raised
    _set_wings(chant1, {0: SPREAD, 0.45: _mod(SPREAD, wu=((0, 0, -8), (0, 0, 0), (0, 0, 0))), 0.9: c1p, 1.5: c1p})
    chant1.rot("arm_r_1", {0: (-18, 0, 24), 0.9: (-150, 0, 14), 1.5: (-146, 0, 14)})
    chant1.rot("arm_r_2", {0: (-30, 0, 6), 0.9: (-12, 0, 0), 1.5: (-12, 0, 0)})
    chant1.rot("arm_l_1", {0: (-18, 0, -24), 0.9: (-40, 0, -10), 1.5: (-40, 0, -10)})
    chant1.rot("arm_l_2", {0: (-30, 0, -6), 0.9: (-70, 0, 18), 1.5: (-70, 0, 18)})
    chant1.rot("head", {0: (-6, 0, 0), 0.9: (-18, 0, 0), 1.5: (-16, 0, 0)})
    chant1.pos("root", {0: (0, 5, 0), 0.5: (0, 3, 0), 0.9: (0, 9, 0), 1.5: (0, 8, 0)})
    A.append(chant1)

    c2p = _mod(SPREAD, wm=((0, 46, 10), (0, 26, 0), (0, 16, 0)), wu=((0, -12, 6), (0, 0, 0), (0, 0, 0)),
               wl=((0, 20, 8), (0, 10, 0), (0, 0, 0)))
    chant2 = Anim("chant2", length=1.5, loop="hold")      # middle pair thrusts forward, arms spread wide
    _set_wings(chant2, {0: c1p, 0.5: _mod(SPREAD, wm=((0, -24, 10), (0, -8, 0), (0, 0, 0))), 0.95: c2p, 1.5: c2p})
    sym(chant2, "arm_{s}_1", rot={0: (-90, 0, 14), 0.95: (-70, 0, 62), 1.5: (-68, 0, 60)})
    sym(chant2, "arm_{s}_2", rot={0: (-30, 0, 0), 0.95: (-14, 0, 0), 1.5: (-14, 0, 0)})
    chant2.rot("head", {0: (-16, 0, 0), 0.95: (4, 0, 0), 1.5: (2, 0, 0)})
    chant2.pos("root", {0: (0, 8, 0), 0.5: (0, 10, 4), 0.95: (0, 6, -5), 1.5: (0, 6, -4)})
    chant2.rot("body", {0: (0, 0, 0), 0.5: (-8, 0, 0), 0.95: (9, 0, 0), 1.5: (7, 0, 0)})
    A.append(chant2)

    c3p = dict(wu=((0, 0, 58), (0, 0, 10), (0, 0, 8)), wm=((0, 0, 12), (0, 0, 4), (0, 0, 2)),
               wl=((0, 0, -50), (0, 0, -10), (0, 0, -8)))
    chant3 = Anim("chant3", length=1.6, loop="hold")      # the full sixfold star, both arms raised
    _set_wings(chant3, {0: c2p, 0.45: COCOON, 0.95: c3p, 1.6: c3p})
    sym(chant3, "arm_{s}_1", rot={0: (-70, 0, 62), 0.45: (-60, 0, -6), 0.95: (-165, 0, 26), 1.6: (-162, 0, 26)})
    sym(chant3, "arm_{s}_2", rot={0: (-14, 0, 0), 0.45: (-80, 0, -20), 0.95: (-8, 0, 0), 1.6: (-8, 0, 0)})
    chant3.rot("head", {0: (2, 0, 0), 0.45: (16, 0, 0), 0.95: (-24, 0, 0), 1.6: (-22, 0, 0)})
    chant3.pos("root", {0: (0, 6, -4), 0.45: (0, 2, 0), 0.95: (0, 14, 0), 1.6: (0, 13, 0)})
    chant3.scl("halo", {0: 1.0, 0.45: 0.9, 0.95: 1.35, 1.6: 1.3})
    chant3.scl("core", {0: 1.0, 0.95: 1.9, 1.6: 1.7})
    A.append(chant3)

    vd = dict(wu=((0, 30, -20), (0, 10, -10), (0, 0, -8)), wm=((0, 34, -34), (0, 12, -12), (0, 0, -10)),
              wl=((0, 26, -62), (0, 10, -8), (0, 0, -6)))
    verdict = Anim("verdict", length=1.2, loop="hold")    # finishing blow: all six wings sweep down
    _set_wings(verdict, {0: c3p, 0.3: _mod(c3p, wu=((0, -10, 8),) * 3, wm=((0, -12, 14),) * 3), 0.55: vd, 1.2: vd})
    sym(verdict, "arm_{s}_1", rot={0: (-162, 0, 26), 0.3: (-178, 0, 20), 0.55: (-40, 0, 30), 1.2: (-42, 0, 30)})
    sym(verdict, "arm_{s}_2", rot={0: (-8, 0, 0), 0.55: (-20, 0, 0), 1.2: (-20, 0, 0)})
    verdict.rot("head", {0: (-22, 0, 0), 0.55: (20, 0, 0), 1.2: (18, 0, 0)})
    verdict.rot("body", {0: (0, 0, 0), 0.3: (-10, 0, 0), 0.55: (14, 0, 0), 1.2: (10, 0, 0)})
    verdict.pos("root", {0: (0, 13, 0), 0.3: (0, 17, 2), 0.55: (0, 4, -3), 1.2: (0, 6, -2)})
    A.append(verdict)

    depart = Anim("depart", length=1.6, loop="hold")
    _set_wings(depart, {0: SPREAD, 0.6: VEIL, 1.0: COCOON, 1.6: COCOON})
    sym(depart, "arm_{s}_1", rot={0: (-18, 0, 24), 0.6: (-52, 0, -8), 1.6: (-52, 0, -8)})
    sym(depart, "arm_{s}_2", rot={0: (-30, 0, 6), 0.6: (-78, 0, -20), 1.6: (-78, 0, -20)})
    depart.rot("head", {0: (-6, 0, 0), 0.6: (14, 0, 0), 1.6: (20, 0, 0)})
    depart.pos("root", {0: (0, 5, 0), 0.8: (0, 10, 0), 1.6: (0, 60, 0)})
    depart.rot("root", {0: (0, 0, 0), 0.8: (0, 0, 0), 1.6: (0, 300, 0)})
    depart.scl("root", {0: 1.0, 0.9: 1.0, 1.45: (0.35, 1.5, 0.35), 1.6: 0.0})
    A.append(depart)
    return A


def M_spin(deg_per_s):
    from kit.anim import M
    return M(f"q.life_time*{deg_per_s}", lambda t: t * deg_per_s)


# state ids shared by every spell that uses the Seraphim
STATES = {0: ["hidden"], 1: ["arrive"], 2: ["veiled", "flap"], 3: ["unfurl"], 4: ["open", "flap"],
          5: ["chant1"], 6: ["chant2"], 7: ["chant3"], 8: ["verdict"], 9: ["depart"]}


def build(pack):
    m, wings = build_model()
    anims = build_anims(wings)
    pack.actor("seraph", m, anims, STATES, always=["hover"], scale=2.0, lifetime=120,
               display="Seraphim")
    by = {a.name: a for a in anims}
    hv = (by["hover"], 1.0)
    pack.preview("seraph_a", m, [[(by["veiled"], 0), hv], [(by["open"], 0), hv]])
    pack.preview("seraph_b", m, [[(by["chant1"], 1.5), hv], [(by["chant2"], 1.5), hv], [(by["chant3"], 1.6), hv],
                                 [(by["verdict"], 1.2), hv]], views=((25, 12), (-70, 10), (0, 60)), skin="inscribed")
    print(f"    seraph: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")
