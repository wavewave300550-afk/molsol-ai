"""DW05 Imperial Edict: The Threefold Heavenly Throne -- gates, sentences, the EMPTY throne and the
verdict lettering.  The three witnesses (seraph, cherub, ophanim) are reused from their own modules.

Actors (all prefixed dw5_):
  dw5_gate_seraph  soaring lancet arch of feathered ribs, two lancet door leaves, luminous interior
  dw5_gate_cherub  square bronze tetrapylon: four arched doors, four creature emblems, turns once
                   to show every emblem before its doors open
  dw5_gate_ophan   circular wheel-portal: counter-rotating eye rings, armillary meridian, an iris
                   of eight petals that folds back into the rim
  dw5_sentence     ring of giant First-Word letters on gold rails (3 kinds = 3 different sentences)
  dw5_throne       the enormous EMPTY throne: stepped inscribed dais, glowing empty seat, armrests
                   ending in the cherub and ophanim emblems, back = an open book with a blade of
                   light between its pages, crowned by the six-winged seraph emblem.  No figure.
  dw5_letter       one gigantic extruded verdict letter (6 kinds) that ignites, plunges, shatters
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M
from kit.geo import Mat, Model, ring

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD

# ---- shared state tables (mirrored in src/spells/dw05_heavenly_throne.ts)
GATE_STATES = {0: ["hidden"], 1: ["manifest"], 2: ["closed"], 3: ["open"], 4: ["opened"], 5: ["close"], 6: ["fold"]}
SENTENCE_STATES = {0: ["hidden"], 1: ["unfold"], 2: ["idle"], 3: ["gather"]}
THRONE_STATES = {0: ["hidden"], 1: ["assemble"], 2: ["idle"], 3: ["declare"], 4: ["unmake"]}
LETTER_STATES = {0: ["hidden"], 1: ["ignite"], 2: ["hold"], 3: ["plunge"], 4: ["impact"]}
# animation lengths in seconds (the spell timeline uses the same numbers)
T_MANIFEST, T_CLOSE, T_FOLD = 1.6, 1.0, 1.4
T_OPEN = {"seraph": 1.5, "cherub": 2.4, "ophan": 1.6}
T_UNFOLD, T_GATHER = 1.6, 1.4
T_ASSEMBLE, T_DECLARE, T_UNMAKE = 3.0, 1.0, 2.0
T_IGNITE, T_IMPACT = 0.5, 0.6


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def glyph_mat(i, color=WGOLD, color2="#ffd76a", glow=1.0):
    return tex.bitmap_cut(FW[i % len(FW)], color, glow=glow, color2=color2)


def mats():
    K = {}
    K["marble"] = tex.trimmed(tex.marble(IVORY, "#d9cfb8", scale=6), GOLD, 1, 0, glow=0.15)
    K["marble2"] = tex.marble("#efe7d4", "#cdbf9f", scale=5)
    K["gold"] = tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=2.0, glow=0.1)
    K["gold_t"] = tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=3.0, glow=0.3)
    K["silver"] = tex.metal(SILVER, "#ffffff", "#8a93a3", bands=2.5, glow=0.15)
    K["bronze"] = tex.plates("#a07a36", "#5e421a", "#d8b25a", cell=(10, 10), rivet="#ffe08a", glow_line=0.05)
    K["bronze_s"] = tex.metal("#a9823a", "#e6c470", "#5a3f18", bands=2.0)
    K["insc"] = tex.glyph_rows(FW, WGOLD, glow=1.0, bg="#e9dcc0", bg_glow=0.12, key="dw5insc")
    K["insc_blue"] = tex.glyph_rows(FW, "#ffe08a", glow=1.0, bg=BLUE, bg_glow=0.08, scale=2, key="dw5inscb")
    K["glowcore"] = tex.glow_flat("#fff6d8", 1.0, core="#ffffff")
    return K


def text_line(m, parent, y, z, n=12, w=12, h=16, seed=0, pivot=None):
    """Horizontal line of letters (what a gate is written from and folds back into)."""
    b = m.bone("text", parent, pivot=pivot or (0, y, z))
    span = (n - 1) * (w + 1.5)
    for k in range(n):
        b.plane("z", (-span / 2 + k * (w + 1.5), y, z), w, h, glyph_mat(seed + k * 5), faces=("north",))
    return b


def gate_text_anims(manifest, fold, closed, opened, opn, close, hidden):
    manifest.scl("text", {0: 0.0, 0.25: 1.2, 0.45: 1.0, 1.0: 1.0, 1.3: 0.0})
    fold.scl("text", {0: 0.0, 0.35: 0.0, 0.6: 1.25, 0.95: 1.0, T_FOLD: 0.0})
    fold.pos("text", {0: (0, 0, 0), 0.8: (0, 0, 0), T_FOLD: (0, 50, 0)})
    for a in (closed, opened, opn, close):
        a.scl("text", 0.0)
    hidden.scl("root", 0.0)


def body_manifest(a, fold):
    a.scl("body", {0: (0.0, 0.0, 0.0), 0.3: (1.04, 0.02, 1.0), 1.1: (1.0, 1.06, 1.0), 1.4: (1.0, 1.0, 1.0)})
    fold.scl("body", {0: (1, 1, 1), 0.2: (1.03, 1.05, 1.0), 0.65: (1.0, 0.02, 1.0), 1.0: (0.0, 0.0, 0.0)})


# =============================================================================================
# SERAPH GATE: lancet arch of feathered ribs
W_S, HS, R_S = 96.0, 96.0, 144.0
APEX = HS + math.sqrt(R_S ** 2 - (R_S - W_S / 2) ** 2)


def lancet_half(y):
    if y <= HS:
        return W_S / 2
    dy = y - HS
    if dy >= R_S:
        return 0.0
    return max(0.0, math.sqrt(R_S * R_S - dy * dy) - (R_S - W_S / 2))


def lancet_light():
    def fn(ctx):
        x = (ctx.U * 2 - 1) * (W_S / 2)
        y = APEX - ctx.V * (APEX - 12)
        hw = np.vectorize(lancet_half)(y)
        inside = np.abs(x) <= hw
        r = np.clip(np.hypot(x / (W_S / 2), (y - 90) / 110), 0, 1)
        t = tex.tile(ctx, WGOLD, 0.0, 1.0)
        t[..., :3] = tex.mix(tex.rgb("#ffffff"), tex.rgb("#ffd76a"), r[..., None] ** 1.4)
        t[..., 3] = np.where(inside, 0.92 - 0.4 * r, 0.0)
        return t
    return Mat(fn, "dw5lancetlight", mode="blend", directional=True)


def seraph_gate():
    K = mats()
    m = Model("dw5_gate_seraph", density=0.75, bounds=(34, 34, (0, 14, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 100, 0))
    body.box((0, 4, 0), (150, 8, 44), K["marble"], mats={"north": K["insc"]})
    body.box((0, 10, 0), (128, 4, 34), K["gold"])
    feather = [tex.feather("#fbf8ee", "#ffe39a", GOLD, glow=0.15, glow_tip=0.9),
               tex.feather("#f6f1e2", "#fff3c4", "#b8923a", glow=0.15, glow_tip=0.85, notch=0.1)]
    for sx in (1, -1):
        x = sx * 55
        body.box((x, 54, 0), (14, 84, 18), K["marble"], mats={"north": K["insc"]})
        for y in (30, 60, 90):
            body.box((x, y, 0), (16, 3, 20), K["gold"])
        body.box((x, 99, 0), (18, 6, 22), K["gold_t"])
        body.box((x, 14, 0), (18, 4, 22), K["gold"])
    # feathered ribs of the arch
    th1 = math.degrees(math.acos((R_S - W_S / 2) / R_S))
    n = 8
    plumes = {}
    for s, sx in (("r", 1), ("l", -1)):
        rib = m.bone(f"rib_{s}", body, pivot=(0, HS, 0))
        for g in range(3):
            plumes[(s, g)] = m.bone(f"plume_{s}{g + 1}", rib, pivot=(sx * 60, HS + 30 * g, 0))
        cx = -sx * (R_S - W_S / 2)
        for k in range(n):
            th = th1 * (k + 0.5) / n
            rr = R_S + 7
            px_, py_ = cx + sx * rr * math.cos(math.radians(th)), HS + rr * math.sin(math.radians(th))
            rib.box((px_, py_, 0), (14, 20, 18), K["marble"], rot=(0, 0, sx * th), pivot=(px_, py_, 0),
                    mats={"north": K["insc"]}, variant=k % 2)
            ro = R_S + 14
            bx, by = cx + sx * ro * math.cos(math.radians(th)), HS + ro * math.sin(math.radians(th))
            g = min(2, k * 3 // n)
            for j, dth in enumerate((-14, 10)):
                L = 26 + k * 2.2 + j * 3
                ang = th + dth
                rz = sx * (90 + ang)
                plumes[(s, g)].cube((bx - 5, by - L, -1 + j * 0.3), (10, L, 0), feather[(k + j) % 2],
                                    rot=(0, 0, rz), pivot=(bx, by, -1 + j * 0.3), variant=k % 3)
        # jamb plumes rising like flames
        for k, y in enumerate((30, 52, 74)):
            L = 18 + k * 4
            plumes[(s, 0)].cube((sx * 62 - 4, y - L, -1), (8, L, 0), feather[k % 2], rot=(0, 0, sx * 112),
                                pivot=(sx * 62, y, -1), variant=k)
    body.box((0, APEX + 9, 0), (16, 16, 20), K["gold_t"], rot=(0, 0, 45), pivot=(0, APEX + 9, 0))
    # lancet door leaves
    for s, sx in (("r", 1), ("l", -1)):
        d = m.bone(f"door_{s}", body, pivot=(sx * 48, 12, 0))
        leaf = tex.scales("#f3ead2", "#b8923a", "#fffaf0", size=6, glow_gap=0.25)
        y = 12.0
        while y < APEX - 4:
            y1 = min(APEX - 2, y + 14)
            hw = lancet_half(y1)
            if hw < 2:
                break
            x0, x1 = (0.0, hw) if sx > 0 else (-hw, 0.0)
            d.cube((x0, y, -1.5), (x1 - x0, y1 - y, 3), leaf, variant=int(y) % 3)
            y = y1
        d.box((sx * 1.2, (12 + APEX) / 2 - 6, -1.8), (2.4, APEX - 30, 3.6), K["gold_t"])
        d.plane("z", (sx * 24, 72, -1.7), 22, 30, glyph_mat(3 if sx > 0 else 7, "#fffbe6"), faces=("north",))
        d.plane("z", (sx * 20, 128, -1.7), 14, 20, glyph_mat(11 if sx > 0 else 14, "#fffbe6"), faces=("north",))
    light = m.bone("light", body, pivot=(0, 12, 4))
    light.plane("z", (0, (APEX + 12) / 2, 4), W_S, APEX - 12, lancet_light())
    # crown: six small wings around a flame (the seraph's sigil)
    crown = m.bone("crown", body, pivot=(0, APEX + 22, -2))
    for k, a in enumerate((25, 62, 104)):
        for sx in (1, -1):
            crown.cube((-4, APEX + 22 - 22, -2), (8, 22, 0), feather[k % 2], rot=(0, 0, sx * (180 - a)),
                       pivot=(0, APEX + 22, -2), variant=k)
    crown.plane("z", (0, APEX + 30, -2.5), 12, 22, tex.shaped(tex.m_leaf(), "#fff8d8", "#ffd060", glow=1.0, var=0,
                                                             key="dw5flame"), faces=("north",))
    text_line(m, root, 100, -12, n=12, seed=2)
    return m


def seraph_gate_anims():
    hidden, manifest, closed, opn, opened, close, fold = (Anim("hidden", loop=True), Anim("manifest", T_MANIFEST, "hold"),
        Anim("closed", loop=True), Anim("open", T_OPEN["seraph"], "hold"), Anim("opened", loop=True),
        Anim("close", T_CLOSE, "hold"), Anim("fold", T_FOLD, "hold"))
    always = Anim("breathe", loop=True)
    for s, sx in (("r", 1), ("l", -1)):
        for g in range(3):
            always.rot(f"plume_{s}{g + 1}", (0, LIFE(4, 3.1, g * 0.2), LIFE(sx * 3, 2.6, g * 0.17)))
    always.rot("crown", (0, 0, LIFE(4, 4.0)))
    body_manifest(manifest, fold)
    manifest.scl("crown", {0: 0.0, 1.15: 0.0, 1.45: 1.3, T_MANIFEST: 1.0})
    for a in (manifest, closed, fold):
        a.scl("light", 0.0)
    to = T_OPEN["seraph"]
    for s, sx in (("r", 1), ("l", -1)):
        opn.rot(f"door_{s}", {0: (0, 0, 0), 0.15: (0, -sx * 4, 0), 0.4: (0, 0, 0), 1.2: (0, sx * 104, 0), to: (0, sx * 98, 0)})
        opened.rot(f"door_{s}", (0, sx * 98, 0))
        close.rot(f"door_{s}", {0: (0, sx * 98, 0), 0.75: (0, sx * -3, 0), T_CLOSE: (0, 0, 0)})
        for g in range(3):   # the plumes flare as the arch opens
            opn.scl(f"plume_{s}{g + 1}", {0: 1.0, 0.6 + g * 0.15: 1.0, 1.0 + g * 0.15: 1.25, to: 1.15})
            opened.scl(f"plume_{s}{g + 1}", LIFE(0.05, 1.8, g * 0.2, base=1.15))
    opn.scl("light", {0: 0.0, 0.35: 0.0, 1.0: 1.05, to: 1.0})
    opened.scl("light", LIFE(0.03, 1.3, base=1.0))
    close.scl("light", {0: 1.0, 0.7: 0.0})
    opn.scl("crown", {0: 1.0, 0.9: 1.0, 1.2: 1.4, to: 1.2})
    opened.scl("crown", 1.2)
    gate_text_anims(manifest, fold, closed, opened, opn, close, hidden)
    return [hidden, manifest, closed, opn, opened, close, fold, always]


# =============================================================================================
# CHERUB GATE: bronze tetrapylon of four doors and four emblems
EMBLEMS = {
    "human": ["   ####   ", "  #    #  ", " # #  # # ", " #      # ", " #  ##  # ", " #      # ", "  # ## #  ",
              "   #  #   ", "    ##    "],
    "lion": ["# # ## # #", " ######## ", "##  ##  ##", " # #  # # ", "##  ##  ##", " #  ##  # ", "## #### ##",
             " #  ##  # ", "# ###### #"],
    "ox": ["#        #", "##      ##", " ######## ", "  #    #  ", "  # ## #  ", "  #    #  ", "   #  #   ",
           "   ####   ", "   #  #   "],
    "eagle": ["    ##    ", "   #  #   ", "#  ####  #", "## #### ##", " ######## ", "  ######  ", "   ####   ",
              "   #  #   ", "  #    #  "],
}


def medallion(name):
    base = tex.shaped(tex.m_disc(0.96), GOLD, "#8a6a26", glow=0.25, outline=WGOLD, glow_edge=0.9, key=f"dw5med{name}")
    return tex.stamped(base, EMBLEMS[name], "#fffbe6", glow=1.0, scale=2, key=f"dw5medst{name}")


def emblem_face(name, bg="#c9a24a"):
    return tex.stamped(tex.metal(bg, "#ffe9a3", "#7a5a1e", bands=2.0, glow=0.2), EMBLEMS[name], "#fffbe6", glow=1.0,
                       key=f"dw5embf{name}")


def cherub_gate():
    K = mats()
    m = Model("dw5_gate_cherub", density=0.75, bounds=(26, 26, (0, 11, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 80, 0))
    body.box((0, 4, 0), (136, 8, 136), K["marble"])
    for sx in (1, -1):
        for sz in (1, -1):
            body.box((sx * 45, 52, sz * 45), (30, 88, 30), K["bronze"])
            body.box((sx * 45, 11, sz * 45), (34, 6, 34), K["gold"])
            body.box((sx * 45, 93, sz * 45), (34, 5, 34), K["gold_t"])
    leaf = tex.plates("#9a7432", "#5a3f18", "#d8b25a", cell=(10, 10), rivet="#ffe08a")
    which = {0: "human", 1: "ox", 2: "eagle", 3: "lion"}
    wing = tex.feather("#fbf5e3", "#ffe39a", GOLD, glow=0.1, glow_tip=0.6)
    for k in range(4):
        side = m.bone(f"side{k}", body, pivot=(0, 0, 0), rot=(0, k * 90, 0))
        ring(side, (0, 66, -60), 34, 9, (12.5, 8, 10), K["gold_t"], axis="z", start=0, sweep=180)
        for sx in (1, -1):
            side.box((sx * 34, 66, -60), (10, 4, 12), K["gold"])
            side.box((sx * 25, 88, -58), (10, 16, 6), K["bronze_s"])
        side.plane("z", (0, 112, -64.6), 28, 28, medallion(which[k]), faces=("north",))
        for sx in (1, -1):
            side.cube((-5, 112 - 26, -64.4), (10, 26, 0), wing, rot=(0, 0, sx * 80), pivot=(sx * 12, 112, -64.4))
        for s, sx in (("r", 1), ("l", -1)):
            d = m.bone(f"door{k}_{s}", side, pivot=(sx * 30, 8, -60))
            x0, x1 = (0, 30) if sx > 0 else (-30, 0)
            d.cube((x0, 8, -61.5), (30, 58, 3), leaf)
            for j, y in enumerate((66, 76, 86)):
                hw = math.sqrt(max(0.0, 30 ** 2 - (y + 10 - 66) ** 2)) if j < 2 else math.sqrt(max(0.0, 900 - 26 ** 2))
                hw = max(4.0, min(30.0, hw))
                xa, xb = (0, hw) if sx > 0 else (-hw, 0)
                d.cube((xa, y, -61.5), (xb - xa, 10, 3), leaf, variant=j + 1)
            d.plane("z", (sx * 15, 40, -61.7), 16, 22, glyph_mat(k * 4 + (1 if sx > 0 else 2), "#ffe9a3"), faces=("north",))
    body.box((0, 97, 0), (128, 3, 128), K["gold"])
    body.box((0, 113, 0), (124, 30, 124), K["insc_blue"])
    body.box((0, 129.5, 0), (130, 3, 130), K["gold"])
    body.box((0, 135, 0), (110, 8, 110), K["bronze_s"])
    body.box((0, 143, 0), (84, 8, 84), K["bronze_s"], mats={"north": K["insc"], "south": K["insc"], "east": K["insc"],
                                                            "west": K["insc"]})
    body.box((0, 151, 0), (56, 8, 56), K["bronze_s"])
    crown = m.bone("crown", body, pivot=(0, 160, 0))
    crown.box((0, 163, 0), (14, 14, 14), K["gold_t"], rot=(0, 45, 0), pivot=(0, 163, 0))
    ring(crown, (0, 176, 0), 16, 10, (10.5, 2.5, 2.5), K["gold_t"], axis="y")
    ring(crown, (0, 176, 0), 16, 10, (10.5, 2.5, 2.5), K["gold"], axis="z")
    light = m.bone("light", body, pivot=(0, 8, 0))
    light.box((0, 50, 0), (58, 84, 58), tex.glow_flat(WGOLD, 1.0, a=0.75, core="#ffffff", mode="blend"))
    text_line(m, root, 80, -70, n=12, seed=6)
    return m


def cherub_gate_anims():
    hidden, manifest, closed, opn, opened, close, fold = (Anim("hidden", loop=True), Anim("manifest", T_MANIFEST, "hold"),
        Anim("closed", loop=True), Anim("open", T_OPEN["cherub"], "hold"), Anim("opened", loop=True),
        Anim("close", T_CLOSE, "hold"), Anim("fold", T_FOLD, "hold"))
    always = Anim("breathe", loop=True)
    always.rot("crown", (0, spin(36), 0))
    body_manifest(manifest, fold)
    manifest.scl("crown", {0: 0.0, 1.1: 0.0, 1.4: 1.4, T_MANIFEST: 1.0})
    for a in (manifest, closed, fold):
        a.scl("light", 0.0)
    to = T_OPEN["cherub"]
    # the tetrapylon turns once: every emblem passes the front, with a settle at each quarter
    opn.rot("body", {0: (0, 0, 0), 0.25: (0, 96, 0), 0.32: (0, 90, 0), 0.55: (0, 186, 0), 0.62: (0, 180, 0),
                     0.85: (0, 276, 0), 0.92: (0, 270, 0), 1.15: (0, 362, 0), 1.25: (0, 360, 0)})
    opn.pos("body", {0: (0, 0, 0), 0.6: (0, 3, 0), 1.25: (0, 0, 0)})
    for k in range(4):
        t0 = 1.25 + (0.0, 0.18, 0.36, 0.18)[k]
        for s, sx in (("r", 1), ("l", -1)):
            opn.rot(f"door{k}_{s}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.12: (0, -sx * 3, 0), t0 + 0.7: (0, sx * 102, 0),
                                     min(to, t0 + 0.85): (0, sx * 96, 0)})
            opened.rot(f"door{k}_{s}", (0, sx * 96, 0))
            close.rot(f"door{k}_{s}", {0: (0, sx * 96, 0), 0.7: (0, -sx * 2, 0), T_CLOSE: (0, 0, 0)})
    opn.scl("light", {0: 0.0, 1.3: 0.0, 1.9: 1.05, to: 1.0})
    opened.scl("light", LIFE(0.03, 1.1, base=1.0))
    close.scl("light", {0: 1.0, 0.65: 0.0})
    gate_text_anims(manifest, fold, closed, opened, opn, close, hidden)
    return [hidden, manifest, closed, opn, opened, close, fold, always]


# =============================================================================================
# OPHANIM GATE: wheel-portal with an iris of petals
R_IRIS = 54.0


def petal_mat(k):
    gi = FW[(k * 5 + 3) % len(FW)]
    bm = glyphs.bitmap(gi)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        wv = (v + 1) / 2
        inside = (np.abs(u) <= wv * 1.02) & (v <= 1.0)
        t = tex.tile(ctx, SILVER, 1.0, 0.15)
        t[..., :3] = tex.mix(tex.rgb("#eef1f6"), tex.rgb("#c9a24a"), np.clip(wv, 0, 1)[..., None] ** 1.5)
        rim = inside & ((np.abs(u) > wv * 1.02 - 0.08) | (v > 0.93))
        t[..., :3] = np.where(rim[..., None], tex.rgb("#ffe08a"), t[..., :3])
        t[..., 4] = np.where(rim, 0.8, 0.12)
        # one luminous letter near the rim
        gx0, gx1, gy0, gy1 = 0.38, 0.62, 0.1, 0.42
        inb = (ctx.U >= gx0) & (ctx.U < gx1) & (ctx.V >= gy0) & (ctx.V < gy1)
        ix = np.clip(((ctx.U - gx0) / (gx1 - gx0) * bm.shape[1]).astype(int), 0, bm.shape[1] - 1)
        iy = np.clip(((ctx.V - gy0) / (gy1 - gy0) * bm.shape[0]).astype(int), 0, bm.shape[0] - 1)
        g = inb & bm[iy, ix]
        t[..., :3] = np.where(g[..., None], tex.rgb("#fffbe6"), t[..., :3])
        t[..., 4] = np.where(g, 1.0, t[..., 4])
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return tex.grain(ctx, t, 0.03)
    return Mat(fn, f"dw5petal{k}", directional=True)


def ophan_gate():
    K = mats()
    m = Model("dw5_gate_ophan", density=0.75, bounds=(26, 26, (0, 0, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 0, 0))
    frame = m.bone("frame", body, pivot=(0, 0, 0))
    ring(frame, (0, 0, 0), 61, 24, (16.6, 12, 12), K["marble"], axis="z", cycle=2)
    ring(frame, (0, 0, -1), 55, 24, (14.8, 2.4, 13), K["gold_t"], axis="z")
    ra = m.bone("ra", body, pivot=(0, 0, -6))
    ring(ra, (0, 0, -6), 70, 30, (15.2, 5, 5), K["gold"], axis="z")
    eye = tex.eye_mat("#2b3f8f", "#f6f1e2", "#10131c", GOLD, glow=0.9)
    for k in range(10):
        a = math.radians(k * 36 + 18)
        p = (70 * math.cos(a), 70 * math.sin(a), -9)
        eb = m.bone(f"eye{k + 1}", ra, pivot=p)
        eb.box(p, (10, 10, 5), K["gold_t"], mats={"north": eye}, rot=(0, 0, k * 36 + 18 - 90), pivot=p)
    for k in range(10):
        a = k * 36
        ra.box((0, 70, -9.2), (6, 8, 0), glyph_mat(k * 3 + 1), rot=(0, 0, a), pivot=(0, 0, -9.2), faces=("north",))
    rb = m.bone("rb", body, pivot=(0, 0, 5))
    ring(rb, (0, 0, 5), 79, 32, (15.6, 7, 4), K["gold_t"], axis="z", cycle=2)
    ring(rb, (0, 0, 5), 86, 20, (6, 6, 4), K["gold"], axis="z")
    gyro = m.bone("gyro", body, pivot=(0, 0, 0))
    mer = m.bone("meridian", gyro, pivot=(0, 0, 0), rot=(0, 0, 18))
    ring(mer, (0, 0, 0), 92, 28, (20.8, 3, 4), K["silver"], axis="x")
    for k in range(6):
        a = math.radians(k * 60 + 30)
        mer.box((0, 98 * math.sin(a), 98 * math.cos(a)), (0, 7, 5), glyph_mat(k * 4 + 2), faces=("east", "west"))
    for k in range(8):
        ik = m.bone(f"iris{k + 1}", body, pivot=(0, 0, 0), rot=(0, 0, k * 45))
        pk = m.bone(f"petal{k + 1}", ik, pivot=(0, R_IRIS, -2 - 0.3 * k))
        w = 2 * R_IRIS * math.tan(math.radians(22.5)) * 1.28
        pk.plane("z", (0, R_IRIS / 2 + 1, -2 - 0.3 * k), w, R_IRIS + 4, petal_mat(k), faces=("north",))
    light = m.bone("light", body, pivot=(0, 0, 3))
    light.plane("z", (0, 0, 3), 110, 110, tex.shaped(tex.m_disc(1.0), "#ffffff", "#ffd76a", glow=1.0, var=0, a=0.85,
                                                      mode="blend", key="dw5ophlight"), faces=("north",))
    vort = m.bone("vortex", body, pivot=(0, 0, 1.5))
    vort.plane("z", (0, 0, 1.5), 104, 104, tex.magic_circle(FW, "#ffffff", WGOLD, bands=((0.7, 0.9, 16),), lines=(0.66, 0.95),
                                                             star=7, star_r=(0.2, 0.62), core=0.1), faces=("north",))
    text_line(m, root, 0, -14, n=10, seed=9)
    return m


def ophan_gate_anims():
    hidden, manifest, closed, opn, opened, close, fold = (Anim("hidden", loop=True), Anim("manifest", T_MANIFEST, "hold"),
        Anim("closed", loop=True), Anim("open", T_OPEN["ophan"], "hold"), Anim("opened", loop=True),
        Anim("close", T_CLOSE, "hold"), Anim("fold", T_FOLD, "hold"))
    always = Anim("turn", loop=True)
    always.rot("ra", (0, 0, spin(24)))
    always.rot("rb", (0, 0, spin(-15)))
    always.rot("gyro", (0, spin(30), 0))
    always.rot("vortex", (0, 0, spin(-60)))
    manifest.scl("body", {0: 0.0, 0.3: (1.0, 0.03, 1.0), 1.1: (1.0, 1.05, 1.0), 1.4: 1.0})
    manifest.rot("rb", {0: (0, 0, -220), 1.4: (0, 0, 0)})
    fold.scl("body", {0: 1.0, 0.25: 1.05, 0.65: (1.0, 0.03, 1.0), 1.0: 0.0})
    fold.rot("ra", {0: (0, 0, 0), 1.0: (0, 0, 300)})
    for a in (manifest, closed, fold):
        a.scl("light", 0.0)
        a.scl("vortex", 0.0)
        for k in range(10):
            a.scl(f"eye{k + 1}", (1.0, 0.15, 1.0))
    to = T_OPEN["ophan"]
    opn.rot("ra", {0: (0, 0, 0), to: (0, 0, 260)})
    opn.rot("rb", {0: (0, 0, 0), to: (0, 0, -200)})
    for k in range(10):
        t0 = 0.05 + 0.03 * k
        opn.scl(f"eye{k + 1}", {0: (1, 0.15, 1), t0: (1, 0.15, 1), t0 + 0.12: (1, 1.2, 1), t0 + 0.2: (1, 1, 1)})
        close.scl(f"eye{k + 1}", {0: (1, 1, 1), 0.5: (1, 1, 1), 0.7: (1, 0.15, 1)})
    for k in range(8):
        t0 = 0.4 + 0.05 * k
        opn.rot(f"petal{k + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.08: (6, 0, 0), t0 + 0.6: (-104, 0, 0), to: (-98, 0, 0)})
        opn.scl(f"petal{k + 1}", {0: 1.0, t0 + 0.6: 0.62, to: 0.62})
        opened.rot(f"petal{k + 1}", (-98, 0, 0))
        opened.scl(f"petal{k + 1}", 0.62)
        close.rot(f"petal{k + 1}", {0: (-98, 0, 0), 0.1 + 0.04 * k: (-98, 0, 0), 0.75 + 0.03 * k: (2, 0, 0), T_CLOSE: (0, 0, 0)})
        close.scl(f"petal{k + 1}", {0: 0.62, 0.75: 1.0})
    opn.scl("light", {0: 0.0, 0.6: 0.0, 1.2: 1.05, to: 1.0})
    opn.scl("vortex", {0: 0.0, 0.8: 0.0, 1.4: 1.0})
    opened.scl("light", LIFE(0.04, 0.9, base=1.0))
    close.scl("light", {0: 1.0, 0.6: 0.0})
    close.scl("vortex", {0: 1.0, 0.5: 0.0})
    gate_text_anims(manifest, fold, closed, opened, opn, close, hidden)
    return [hidden, manifest, closed, opn, opened, close, fold, always]


# =============================================================================================
# SENTENCE: a ring of giant letters on gold rails (radius 8 blocks at size 1)
R_SEN = 128.0
N_SEN = 24


def sentence_model(kind):
    K = mats()
    m = Model(f"dw5_sentence{'' if kind == 0 else kind + 1}", density=1.0, bounds=(60, 10, (0, 1, 0)))
    root = m.bone("root")
    sp = m.bone("spin", root)
    seq = glyphs.seq(41 + kind * 17, N_SEN)
    tang = 2 * math.pi * R_SEN / N_SEN + 0.8
    for k in range(N_SEN):
        a = m.bone(f"a{k + 1}", sp, pivot=(0, 0, 0), rot=(0, k * 360 / N_SEN, 0))
        l = m.bone(f"l{k + 1}", a, pivot=(0, 0, -R_SEN))
        gm = glyph_mat(seq[k], "#fffbe6" if kind != 1 else "#ffffff", "#ffd76a" if kind != 1 else "#dfe8ff")
        l.plane("z", (0, 17, -R_SEN), 22, 30, gm, faces=("north",))
        rail = K["gold_t"] if kind != 1 else K["silver"]
        l.box((0, 35, -R_SEN), (tang, 2.4, 2.4), rail, variant=k % 2)
        l.box((0, -1, -R_SEN), (tang, 2.4, 2.4), rail, variant=(k + 1) % 2)
        if k % 3 == 0:
            l.box((tang / 2, 17, -R_SEN), (3, 3, 0.6), K["glowcore"], rot=(0, 0, 45), pivot=(tang / 2, 17, -R_SEN))
    return m


def sentence_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    always = Anim("drift", loop=True)
    always.rot("spin", (0, spin(7), 0))
    unfold = Anim("unfold", length=T_UNFOLD, loop="hold")
    idle = Anim("idle", loop=True)
    gather = Anim("gather", length=T_GATHER, loop="hold")
    for k in range(N_SEN):
        b = f"l{k + 1}"
        t0 = k * 0.045
        unfold.scl(b, {0: 0.0, t0: 0.0, t0 + 0.18: 1.25, t0 + 0.32: 1.0})
        unfold.rot(b, {0: (85, 0, 0), t0: (85, 0, 0), t0 + 0.3: (-9, 0, 0), t0 + 0.45: (0, 0, 0)})
        idle.pos(b, (0, LIFE(1.4, 3.0, k / N_SEN * 2), 0))
        g0 = (k % 8) * 0.06
        gather.pos(b, {0: (0, 0, 0), g0: (0, -3, 0), g0 + 0.9: (0, 170, R_SEN * 0.85)})
        gather.rot(b, {0: (0, 0, 0), g0 + 0.9: (-30, 0, 0)})
        gather.scl(b, {0: 1.0, g0 + 0.25: 1.3, g0 + 0.6: 1.0, g0 + 0.95: 0.0})
    return [hidden, always, unfold, idle, gather]


# =============================================================================================
# THE EMPTY THRONE (origin = centre of the dais floor; front faces -Z, toward the caster)
def page_mat(seed):
    base = tex.glyph_rows(FW, "#c9a24a", glow=0.9, color2="#fff3c4", bg="#f7f1e2", bg_glow=0.3, seed=seed, key=f"dw5page{seed}")

    def post(ctx, t):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        inside = (v <= 0.62) | ((u ** 2 + ((v - 0.62) / 0.38) ** 2) <= 1.0)
        border = inside & ((np.abs(u) > 0.9) | (v < -0.94) | ((v > 0.62) & ((u ** 2 + ((v - 0.62) / 0.38) ** 2) > 0.8)))
        t[..., :3] = np.where(border[..., None], tex.rgb(GOLD), t[..., :3])
        t[..., 4] = np.where(border, 0.6, t[..., 4])
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return t
    return tex.overlay(base, post, f"dw5pagecut{seed}")


def blade_mat(key, core=False):
    def fn(ctx):
        u = ctx.U * 2 - 1
        width = 0.25 + 0.75 * np.clip(ctx.V, 0, 1) ** 0.6       # V = 0 at the top: the blade tapers to a point
        a = np.clip(1 - (np.abs(u) / width) ** (3 if core else 1.6), 0, 1)
        a *= np.clip((1 - ctx.V) * 6, 0, 1) * np.clip(ctx.V * 30, 0, 1) ** 0.3
        t = tex.tile(ctx, WGOLD, 0.0, 1.0)
        t[..., :3] = tex.mix(tex.rgb("#ffffff"), tex.rgb("#ffd76a" if not core else "#fff8e0"), np.abs(u)[..., None])
        t[..., 3] = a * (0.95 if core else 0.7)
        return t
    return Mat(fn, key, mode="blend", directional=True)


def streak_mat(key):
    def fn(ctx):
        u = ctx.U * 2 - 1
        t = tex.tile(ctx, WGOLD, 0.0, 1.0)
        t[..., :3] = tex.rgb("#fff3c4")
        t[..., 3] = np.clip(ctx.V ** 1.3 * (1 - np.abs(u) ** 1.4) * 0.85, 0, 1)
        return t
    return Mat(fn, key, mode="blend", directional=True)


FAR = {"s": (0, 150, 110), "c": (190, -30, -40), "o": (-190, -50, -40)}   # where each witness's letters come from


def throne_model():
    K = mats()
    m = Model("dw5_throne", density=0.6, bounds=(30, 30, (0, 12, 0)))
    root = m.bone("root")
    riser = tex.glyph_rows(FW, WGOLD, glow=1.0, bg="#efe6cf", bg_glow=0.12, key="dw5riser")
    for i, (y, z, w, d) in enumerate(((4, 0, 128, 104), (12, 6, 108, 88), (20, 12, 88, 72))):
        st = m.bone(f"step{i + 1}", root, pivot=(0, y - 4, z - d / 2))
        st.box((0, y, z), (w, 8, d), K["marble"], mats={"north": riser}, variant=i)
        st.box((0, y + 4.6, z - d / 2 + 1), (w + 1, 1.4, 2.4), K["gold_t"])
    seat = m.bone("seat", root, pivot=(0, 24, 22))
    seat.box((0, 33, 22), (52, 18, 40), K["marble2"], mats={"north": K["insc_blue"]})
    seat.box((0, 43.5, 20), (58, 3, 44), K["gold"])
    seat.box((0, 25.5, 22), (58, 3, 44), K["gold"], variant=1)
    sg = m.bone("seat_glow", seat, pivot=(0, 45.2, 20))
    sg.plane("y", (0, 45.3, 20), 46, 36, tex.shaped(tex.m_disc(1.0), "#ffffff", "#ffe08a", glow=1.0, var=0, a=0.4,
                                                     mode="blend", key="dw5seatglow"), faces=("up",))
    wing = tex.feather("#fbf8ee", "#ffe39a", GOLD, glow=0.15, glow_tip=0.85)
    for s, sx in (("r", 1), ("l", -1)):
        arm = m.bone(f"arm_{s}", root, pivot=(sx * 32, 44, 40))
        arm.box((sx * 32, 54, 16), (8, 5, 46), K["gold_t"])
        arm.box((sx * 32, 49, 0), (6, 12, 6), K["marble2"])
        arm.box((sx * 32, 49, 34), (6, 12, 6), K["marble2"], variant=1)
        arm.box((sx * 32, 51, -7), (7, 7, 7), K["gold"], rot=(45, 0, 0), pivot=(sx * 32, 51, -7))
    # right armrest (+X, the caster's left, the Cherubim's side): a four-faced emblem block with wings
    er = m.bone("emb_r", "arm_r", pivot=(32, 58, -6))
    er.box((32, 64, -6), (12, 12, 12), K["gold"], mats={"north": emblem_face("human"), "east": emblem_face("lion"),
                                                       "west": emblem_face("ox"), "south": emblem_face("eagle")})
    for sx in (1, -1):
        er.cube((32 - 3, 70 - 18, -6), (6, 18, 0), wing, rot=(0, 0, sx * 150), pivot=(32 + sx * 4, 68, -6))
    # left armrest (-X): the wheel within a wheel, with an eye at its hub
    el = m.bone("emb_l", "arm_l", pivot=(-32, 64, -6))
    elw = m.bone("emb_l_w", el, pivot=(-32, 64, -6))
    ring(elw, (-32, 64, -6), 9, 12, (5.2, 2.4, 2.4), K["gold_t"], axis="z")
    ring(elw, (-32, 64, -6), 9, 12, (5.2, 2.4, 2.4), K["gold"], axis="x")
    el.box((-32, 64, -6), (5, 5, 5), K["gold"], mats={"north": tex.eye_mat("#2b3f8f", "#f6f1e2", "#10131c", GOLD, glow=0.9)})
    # back: an open book standing on its spine, a blade of light between the pages
    spine = m.bone("spine", root, pivot=(0, 24, 44))
    spine.box((0, 80, 44), (8, 112, 8), K["gold_t"], mats={"north": K["insc_blue"]})
    for s, sx, rot in (("r", 1, 24), ("l", -1, -24)):
        pg = m.bone(f"page_{s}", root, pivot=(0, 30, 42), rot=(0, rot, 0))
        pg.plane("z", (sx * 30, 88, 41), 54, 118, page_mat(3 if sx > 0 else 8), faces=("north",))
        pg.plane("z", (sx * 30, 88, 42.6), 58, 122, tex.overlay(tex.metal(GOLD, "#ffe9a3", "#7a5a1e", bands=3.0, glow=0.2),
                                                             lambda c, t: _arch_cut(c, t), "dw5cover"), faces=("north",))
    blade = m.bone("blade", root, pivot=(0, 26, 39))
    bc = m.bone("blade_core", blade, pivot=(0, 26, 39))
    bc.plane("z", (0, 111, 38.5), 24, 170, blade_mat("dw5blade"), faces=("north",))
    bc.plane("x", (0, 111, 38.5), 24, 170, blade_mat("dw5blade2"), faces=("east",))
    bc.plane("z", (0, 111, 38.0), 7, 166, blade_mat("dw5bladecore", core=True), faces=("north",))
    crest = m.bone("crest", root, pivot=(0, 150, 40))
    for k, a in enumerate((26, 64, 106)):
        for sx in (1, -1):
            L = 34 - k * 4
            crest.cube((-5, 150 - L, 40), (10, L, 0), wing, rot=(0, 0, sx * (180 - a)), pivot=(0, 150, 40), variant=k)
    crest.plane("z", (0, 160, 39.5), 14, 26, tex.shaped(tex.m_leaf(), "#fff8d8", "#ffd060", glow=1.0, var=0, key="dw5flame2"),
                faces=("north",))
    crest.box((0, 150, 40), (7, 7, 4), K["glowcore"], rot=(0, 0, 45), pivot=(0, 150, 40))
    halo = m.bone("halo", root, pivot=(0, 112, 50))
    hs = m.bone("halo_spin", halo, pivot=(0, 112, 50))
    ring(hs, (0, 112, 50), 64, 28, (14.8, 4, 2), K["gold_t"], axis="z", cycle=2)
    for k in range(12):
        hs.box((0, 112 + 72, 50.2), (1.6, 12, 0.6), K["gold_t"], rot=(0, 0, k * 30 + 15), pivot=(0, 112, 50.2))
    hg = m.bone("halo_glyphs", halo, pivot=(0, 112, 50.6))
    for k in range(14):
        hg.box((0, 112 + 58, 50.6), (6, 8, 0), glyph_mat(k * 3 + 5), rot=(0, 0, k * 360 / 14), pivot=(0, 112, 50.6),
               faces=("north", "south"))
    # dissolving swarm (visible while it is unmade) and the three converging streams (while assembling)
    sw = m.bone("swarm", root, pivot=(0, 60, 20))
    for k in range(16):
        a = math.radians(k * 22.5)
        sw.box((48 * math.cos(a), 50 + (k % 4) * 14, 20 + 48 * math.sin(a)), (8, 11, 0), glyph_mat(k * 7 + 1), rot=(0, -k * 22.5 + 90, 0),
               pivot=(48 * math.cos(a), 50, 20 + 48 * math.sin(a)), faces=("north", "south"))
    st = m.bone("streams", root, pivot=(0, 60, 20))
    for w in ("s", "c", "o"):
        for i in range(6):
            b = m.bone(f"st_{w}{i + 1}", st, pivot=(0, 60, 20))
            b.plane("z", (0, 60, 20), 10, 14, glyph_mat(i * 5 + ord(w)), faces=("north",))
    return m


def _arch_cut(ctx, t):
    u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
    inside = (v <= 0.62) | ((u ** 2 + ((v - 0.62) / 0.38) ** 2) <= 1.0)
    t[..., 3] = np.where(inside, 1.0, 0.0)
    return t


def throne_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    always = Anim("glory", loop=True)
    always.rot("halo_spin", (0, 0, spin(10)))
    always.rot("halo_glyphs", (0, 0, spin(-18)))
    always.rot("emb_l_w", (spin(40), 0, spin(70)))
    always.scl("seat_glow", LIFE(0.12, 2.2, base=1.0))
    always.scl("blade_core", (LIFE(0.08, 0.7, base=1.0), 1.0, LIFE(0.08, 0.7, base=1.0)))
    always.rot("crest", (0, 0, LIFE(2.5, 4.2)))
    always.rot("swarm", (0, spin(60), 0))

    asm = Anim("assemble", length=T_ASSEMBLE, loop="hold")
    for j, w in enumerate(("s", "c", "o")):
        fx, fy, fz = FAR[w]
        for i in range(6):
            ta = 0.05 + i * 0.14 + j * 0.05
            far = (fx * (1 + 0.1 * i) + (i % 2) * 10, fy * (1 + 0.1 * i) + (i % 3) * 8, fz * (1 + 0.1 * i))
            asm.pos(f"st_{w}{i + 1}", {0: far, ta: far, ta + 0.55: (0, 0, 0)})
            asm.scl(f"st_{w}{i + 1}", {0: 0.0, ta: 0.7, ta + 0.1: 1.3, ta + 0.5: 1.0, ta + 0.62: 0.0})
    for i in range(3):
        t = 0.2 + 0.2 * i
        asm.scl(f"step{i + 1}", {0: 0.0, t: (0.02, 0.3, 1.0), t + 0.25: (1.08, 0.3, 1.0), t + 0.42: (1.0, 1.0, 1.0)})
        asm.pos(f"step{i + 1}", {0: (0, -6, 0), t: (0, -6, 0), t + 0.42: (0, 0, 0)})
    asm.scl("seat", {0: 0.0, 0.8: 0.0, 1.05: (1.1, 0.4, 1.1), 1.3: 1.0})
    for s in ("r", "l"):
        asm.scl(f"arm_{s}", {0: 0.0, 1.05: (1.0, 1.0, 0.0), 1.4: (1.0, 1.0, 1.08), 1.55: 1.0})
    asm.scl("emb_r", {0: 0.0, 1.4: 0.0, 1.6: 1.4, 1.75: 1.0})
    asm.scl("emb_l", {0: 0.0, 1.45: 0.0, 1.65: 1.4, 1.8: 1.0})
    asm.scl("spine", {0: 0.0, 1.35: (1.0, 0.0, 1.0), 1.7: (1.0, 1.05, 1.0), 1.8: 1.0})
    asm.scl("page_r", {0: 0.0, 1.5: 0.0, 1.7: 1.0})
    asm.scl("page_l", {0: 0.0, 1.5: 0.0, 1.7: 1.0})
    asm.rot("page_r", {0: (0, 66, 0), 1.85: (0, 66, 0), 2.3: (0, -5, 0), 2.45: (0, 0, 0)})
    asm.rot("page_l", {0: (0, -66, 0), 1.85: (0, -66, 0), 2.3: (0, 5, 0), 2.45: (0, 0, 0)})
    asm.scl("blade", {0: 0.0, 2.1: (1.0, 0.0, 1.0), 2.45: (1.3, 1.1, 1.3), 2.6: 1.0})
    asm.scl("crest", {0: 0.0, 2.4: 0.0, 2.65: 1.3, 2.8: 1.0})
    asm.scl("halo", {0: 0.0, 2.45: 0.0, 2.8: 1.12, 3.0: 1.0})
    asm.scl("seat_glow", {0: 0.0, 2.6: 0.0, 3.0: 1.0})

    idle = Anim("idle", loop=True)
    declare = Anim("declare", length=T_DECLARE, loop="hold")
    declare.scl("blade", {0: 1.0, 0.3: (1.8, 1.15, 1.8), T_DECLARE: (1.35, 1.08, 1.35)})
    declare.rot("page_r", {0: (0, 0, 0), 0.4: (0, -12, 0), T_DECLARE: (0, -10, 0)})
    declare.rot("page_l", {0: (0, 0, 0), 0.4: (0, 12, 0), T_DECLARE: (0, 10, 0)})
    declare.scl("halo", {0: 1.0, 0.35: 1.3, T_DECLARE: 1.2})
    declare.scl("crest", {0: 1.0, 0.3: 1.4, T_DECLARE: 1.25})
    declare.scl("seat_glow", {0: 1.0, 0.3: 1.6, T_DECLARE: 1.35})

    un = Anim("unmake", length=T_UNMAKE, loop="hold")
    un.scl("crest", {0: 1.0, 0.15: 1.3, 0.4: 0.0})
    un.pos("crest", {0: (0, 0, 0), 0.4: (0, 20, 0)})
    un.scl("halo", {0: 1.0, 0.2: 1.25, 0.5: 0.0})
    un.scl("blade", {0: 1.0, 0.3: (1.0, 1.0, 1.0), 0.7: (0.0, 1.3, 0.0)})
    un.rot("page_r", {0: (0, 0, 0), 0.5: (0, 0, 0), 0.9: (0, 66, 0)})
    un.rot("page_l", {0: (0, 0, 0), 0.5: (0, 0, 0), 0.9: (0, -66, 0)})
    un.scl("page_r", {0: 1.0, 0.85: 1.0, 1.1: 0.0})
    un.scl("page_l", {0: 1.0, 0.85: 1.0, 1.1: 0.0})
    un.scl("spine", {0: 1.0, 0.9: 1.0, 1.15: (1.0, 0.0, 1.0)})
    for s in ("r", "l"):
        un.scl(f"arm_{s}", {0: 1.0, 1.0: 1.0, 1.2: (1.0, 1.0, 0.0)})
    un.scl("emb_r", {0: 1.0, 0.85: 1.3, 1.05: 0.0})
    un.scl("emb_l", {0: 1.0, 0.85: 1.3, 1.05: 0.0})
    un.scl("seat", {0: 1.0, 1.1: 1.0, 1.4: (1.1, 0.0, 1.1)})
    for i in range(3):
        t = 1.25 + 0.15 * (2 - i)
        un.scl(f"step{i + 1}", {0: 1.0, t: 1.0, t + 0.15: (1.06, 0.3, 1.0), t + 0.35: (0.0, 0.3, 1.0)})
    un.scl("swarm", {0: 0.0, 0.3: 1.0, 1.6: 2.4, T_UNMAKE: 0.0})
    un.pos("swarm", {0: (0, 0, 0), 0.4: (0, 0, 0), T_UNMAKE: (0, 120, 0)})
    return [hidden, always, asm, idle, declare, un]


# =============================================================================================
# VERDICT LETTER: a gigantic extruded letter (origin = bottom centre)
LETTER_GLYPHS = [0, 5, 6, 9, 13, 16]


def letter_model(i):
    K = mats()
    m = Model(f"dw5_letter{'' if i == 0 else i + 1}", density=1.0, bounds=(8, 12, (0, 4, 0)))
    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 30, 0))
    face = tex.glow_flat("#fff6d8", 1.0, core="#ffffff")
    side = tex.metal("#e2bd62", "#fff3c4", "#8a6a26", bands=2.0, glow=0.6)
    glyphs.extrude(body, FW[LETTER_GLYPHS[i]], (20, 60, -3), 8, 6, face,
                   mats={"east": side, "west": side, "up": side, "down": side, "south": side})
    halo = m.bone("halo", root, pivot=(0, 32, 6))
    halo.plane("z", (0, 32, 6), 84, 84, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.72, 0.92, 14),), lines=(0.68, 0.97),
                                                          star=5, star_r=(0.2, 0.6)), faces=("north",))
    trail = m.bone("trail", root, pivot=(0, 60, 0))
    st = streak_mat("dw5lettertrail")
    trail.plane("z", (0, 150, 0), 36, 180, st, faces=("north",))
    trail.plane("x", (0, 150, 0), 36, 180, st, faces=("east",))
    return m


def letter_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    always = Anim("shine", loop=True)
    always.rot("halo", (0, 0, spin(40)))
    ign = Anim("ignite", length=T_IGNITE, loop="hold")
    ign.scl("body", {0: 0.0, 0.25: 1.3, T_IGNITE: 1.0})
    ign.rot("body", {0: (0, 180, 0), 0.3: (0, -10, 0), T_IGNITE: (0, 0, 0)})
    ign.scl("halo", {0: 0.0, 0.15: 0.0, 0.4: 1.2, T_IGNITE: 1.0})
    ign.scl("trail", 0.0)
    hold = Anim("hold", loop=True)
    hold.pos("body", (0, LIFE(1.5, 2.2), 0))
    hold.scl("halo", LIFE(0.05, 0.8, base=1.0))
    hold.scl("trail", 0.0)
    pl = Anim("plunge", loop=True, length=1.0)
    pl.scl("body", (0.85, 1.35, 0.85))
    pl.scl("halo", (0.6, 0.6, 0.6))
    pl.scl("trail", 1.0)
    imp = Anim("impact", length=T_IMPACT, loop="hold")
    imp.scl("body", {0: (1.6, 0.35, 1.6), 0.15: (1.9, 0.15, 1.9), 0.35: 0.0})
    imp.pos("halo", {0: (0, -26, -6), 0.6: (0, -26, -6)})
    imp.rot("halo", {0: (-90, 0, 0), 0.6: (-90, 0, 0)})
    imp.scl("halo", {0: 1.0, 0.3: 3.0, T_IMPACT: 0.0})
    imp.scl("trail", {0: 1.0, 0.12: 0.0})
    return [hidden, always, ign, hold, pl, imp]


# =============================================================================================
def build_fx(pack):
    fx = particles(pack)
    G = [f"glyph{i}" for i in range(1, 9)]
    fx.effect("dw5_stream", None, sprites=G, count=2, life=(0.5, 0.8), size=(0.3, 0.12), shape=("sphere", 0.4),
              speed=(0.1, 0.4), drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw5_gate_rays", "beam", count=8, life=(0.5, 0.9), size=(0.18, 0.04), size_y=(2.5, 4.5), shape=("disc", 3.0),
              direction=(0, 1, 0), speed=(2, 5), colors=["#ffffffcc", "#fff3c4aa", "#ffd76a00"], facing="lookat_y")
    fx.effect("dw5_gate_dust", "dot", count=18, life=(0.8, 1.6), size=(0.12, 0.0), shape=("sphere", 3.5), speed=(0.5, 2.0),
              accel=(0, 0.6, 0), drag=1.2, colors=["#fff3c4ff", "#ffd76aaa", "#c9a24a00"])
    fx.effect("dw5_seat_glow", "glow", count=1, life=(0.9, 1.2), size=(1.6, 3.4), colors=["#fff8e0aa", "#fff3c400"])
    fx.effect("dw5_edict_trail", "beam", count=2, life=(0.25, 0.4), size=(0.35, 0.05), size_y=(3.0, 1.0), shape=("sphere", 0.6),
              colors=["#ffffffff", "#ffe39a00"], facing="lookat_y")
    fx.effect("dw5_edict_impact", "ringthin", count=1, life=(0.55, 0.7), size=(0.6, 9.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#fff3c4cc", "#c9a24a00"])
    fx.effect("dw5_edict_letters", None, sprites=G, count=12, life=(0.7, 1.2), size=(0.32, 0.08), shape=("sphere", 1.0),
              speed=(3.5, 7.0), accel=(0, -2.5, 0), drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"])
    fx.effect("dw5_fold", None, sprites=G, count=10, life=(0.8, 1.4), size=(0.28, 0.06), shape=("box", (4.0, 0.3, 0.3)),
              speed=(0.4, 1.2), accel=(0, 2.0, 0), drag=0.8, colors=["#fffbe6ff", "#ffd76aaa", "#c9a24a00"])
    fx.effect("dw5_domain", "ringthin", count=1, life=(0.9, 1.1), size=(1.0, 16.0), facing="emitter_transform_xz",
              colors=["#fff3c4ff", "#ffd76a99", "#2b3f8f00"])


def build_sounds(pack):
    def chord(f, vowel, dur, ratios=(1.0, 1.26, 1.5), bright=1.0, attack=0.25, release=0.5):
        return sy.mixdown([sy.choir(f * r, dur, vowel, voices=4 if i else 5, bright=bright, attack=attack, release=release)
                           for i, r in enumerate(ratios)])
    # three gate timbres: air and feathers / bronze and weight / wheels and glass
    sg = sy.at(2.4, (0.0, sy.wind(2.0, 600, 3200, q=2.5, gust=0.4) * 0.3),
               (0.1, sy.choir(523.3, 1.9, "ee", voices=4, attack=0.6, release=0.8) * 0.45),
               (0.3, sy.whoosh(0.6, 500, 3500) * 0.4), (0.7, sy.whoosh(0.6, 700, 4200) * 0.4),
               (1.0, sy.shimmer(1.2, 2600, 20) * 0.35), (1.1, sy.bell(1396.9, 1.2) * 0.3), (1.25, sy.bell(2093, 1.0) * 0.18))
    sy.save(pack, "dw5_gate_seraph", sy.reverb(sg, 2.2, 0.45), max_distance=96)
    cg = sy.at(3.0, *[(i * 0.3, sy.thump(0.5, 95 - i * 6, 40, 0.4) * 0.55) for i in range(4)], (0.0, sy.rumble(1.4, 60, 2.0) * 0.5),
               (1.2, sy.creak(1.1, 90, 150, 0.3) * 0.45), (1.3, sy.bell(98, 2.2, bright=0.6, inharm=1.3) * 0.65),
               (1.35, sy.bell(196, 1.8, bright=0.7, inharm=1.2) * 0.35), (2.1, sy.thump(0.8, 70, 30, 0.6) * 0.7))
    sy.save(pack, "dw5_gate_cherub", sy.reverb(sy.lowpass(cg, 4000), 1.8, 0.4), max_distance=96)
    clicks = [(0.05 + 1.1 * (1 - (1 - i / 16) ** 1.7), sy.pluck(1800 + 90 * i, 0.12, 0.9) * 0.28) for i in range(16)]
    hum = sy.lowpass(sy.osc(sy.sweep(55, 130, 2.0, 0.7), wave_="saw") * sy.env(2.0, 0.3, 0.2, 0.8, 0.6), 900) * 0.35
    og = sy.at(2.6, (0.0, hum), *clicks, (1.2, sy.bell(1046.5, 1.3, inharm=0.8) * 0.35), (1.3, sy.pluck(1568, 0.9, 0.6) * 0.35),
               (1.45, sy.pluck(2349, 0.8, 0.6) * 0.3), (1.2, sy.whoosh(0.9, 2000, 400) * 0.25))
    sy.save(pack, "dw5_gate_ophan", sy.reverb(og, 1.8, 0.4), max_distance=96)
    close = sy.at(1.4, (0.0, sy.whoosh(0.7, 2500, 300) * 0.35), (0.55, sy.thump(0.6, 120, 40, 0.4) * 0.6),
                  (0.6, sy.bell(392, 0.8, bright=0.8) * 0.3))
    sy.save(pack, "dw5_gate_close", sy.reverb(close, 1.4, 0.35), max_distance=80,
            variants=[sy.reverb(sy.pitch(close, 0.85), 1.4, 0.35), sy.reverb(sy.pitch(close, 1.15), 1.4, 0.35)])
    fold = sy.at(1.6, (0.0, sy.scribble(1.0, 8)[::-1] * 0.5), (0.3, sy.shimmer(1.0, 2400, 14)[::-1] * 0.35),
                 (0.8, sy.pluck(1174.7, 0.5, 0.6) * 0.3), (0.95, sy.pluck(880, 0.5, 0.6) * 0.3))
    sy.save(pack, "dw5_fold", sy.reverb(fold, 1.4, 0.4), max_distance=80)
    man = sy.at(3.0, (0.0, sy.scribble(2.2, 12) * 0.45), (0.0, sy.pad(110, 2.8, cutoff=1200, attack=1.0) * 0.4),
                (0.4, sy.choir(220, 2.4, "oo", voices=5, attack=1.0, release=1.0) * 0.45), (1.6, sy.bell(659.3, 1.3) * 0.3))
    sy.save(pack, "dw5_manifest", sy.reverb(man, 2.4, 0.45), max_distance=96)
    sen = sy.at(2.0, (0.0, sy.scribble(1.5, 10) * 0.45), (0.1, chord(329.6, "eh", 1.6, (1.0, 1.335, 1.5), attack=0.4) * 0.45),
                (0.3, sy.shimmer(1.4, 2000, 16) * 0.3))
    sy.save(pack, "dw5_sentence", sy.reverb(sen, 2.0, 0.42), max_distance=80,
            variants=[sy.reverb(sy.pitch(sen, 0.89), 2.0, 0.42), sy.reverb(sy.pitch(sen, 1.12), 2.0, 0.42)])
    dom = sy.at(2.2, (0.0, sy.thump(1.0, 100, 32, 0.5) * 0.7), (0.0, chord(130.8, "ah", 1.8, (1.0, 1.5, 2.0), bright=1.2) * 0.65),
                (0.05, sy.bell(261.6, 1.8, bright=0.8) * 0.4))
    sy.save(pack, "dw5_domain", sy.reverb(dom, 2.4, 0.45), max_distance=96)
    bed = sy.at(5.0, (0.0, sy.pad(73.4, 5.0, voices=5, cutoff=700, attack=1.5, release=1.5) * 0.5),
                (0.3, sy.choir(146.8, 4.6, "oo", voices=6, attack=1.4, release=1.4) * 0.45),
                (0.8, sy.choir(220.0, 3.8, "oh", voices=4, attack=1.2, release=1.4) * 0.25),
                (1.0, sy.shimmer(3.5, 1600, 14, 1.8) * 0.12))
    sy.save(pack, "dw5_bed", sy.reverb(bed, 2.6, 0.4), volume=0.8, max_distance=96)
    form = sy.at(4.2, (0.0, sy.choir(196, 4.0, "ah", attack=1.6, release=0.8) * 0.4),
                 (0.6, sy.choir(246.9, 3.4, "ah", voices=4, attack=1.3, release=0.8) * 0.35),
                 (1.2, sy.choir(293.7, 2.8, "oh", voices=4, attack=1.0, release=0.8) * 0.35),
                 (1.8, sy.choir(392, 2.2, "ee", voices=4, attack=0.8, release=0.8) * 0.3),
                 (0.0, sy.whoosh(3.0, 200, 2600) * 0.25), (1.0, sy.shimmer(3.0, 2400, 26) * 0.3),
                 (2.9, sy.bell(587.3, 1.3) * 0.4), (2.95, sy.bell(784, 1.2) * 0.3))
    sy.save(pack, "dw5_throne_form", sy.reverb(form, 2.8, 0.45), max_distance=112)
    spk = sy.at(1.8, (0.0, chord(110, "oh", 1.4, (1.0, 1.5, 2.0), bright=0.9, attack=0.05, release=0.7) * 0.7),
                (0.0, sy.thump(0.6, 80, 34, 0.3) * 0.4), (0.02, sy.bell(440, 1.4, bright=0.7) * 0.35))
    sy.save(pack, "dw5_speak", sy.reverb(spk, 2.4, 0.45), max_distance=112)
    ign = sy.at(0.7, (0.0, sy.pluck(1760, 0.5, 0.8) * 0.5), (0.02, sy.bell(2637, 0.6) * 0.25), (0.0, sy.whoosh(0.3, 3000, 6000) * 0.2))
    sy.save(pack, "dw5_ignite", sy.reverb(ign, 1.0, 0.35), volume=0.7, max_distance=64,
            variants=[sy.reverb(sy.pitch(ign, r), 1.0, 0.35) for r in (0.89, 1.12, 1.26)])
    vd = sy.at(5.0, (0.0, sy.thump(1.6, 140, 26, 0.8)), (0.0, sy.crack(0.7, 6000, 18) * 0.45),
               (0.02, chord(98, "ah", 3.0, (1.0, 1.5, 2.0, 2.52), bright=1.4, attack=0.03, release=1.6) * 0.75),
               (0.05, sy.bell(196, 3.0, bright=0.9) * 0.55), (0.1, sy.bell(587.3, 2.4) * 0.35), (0.35, sy.bell(784, 2.0) * 0.28),
               (0.6, sy.bell(1174.7, 1.6) * 0.22), (0.0, sy.rumble(4.0, 55, 2.5) * 0.5), (1.2, sy.thump(1.0, 90, 30, 0.4) * 0.45))
    sy.save(pack, "dw5_verdict", sy.reverb(vd, 3.2, 0.5), max_distance=128)
    lf = sy.at(1.0, (0.0, sy.whoosh(0.35, 4000, 500) * 0.5), (0.33, sy.thump(0.6, 120, 36, 0.6) * 0.8),
               (0.34, sy.bell(523.3, 0.6, bright=1.2) * 0.3), (0.33, sy.crack(0.3, 5000, 8) * 0.25))
    sy.save(pack, "dw5_letter_fall", sy.reverb(lf, 1.4, 0.35), max_distance=80,
            variants=[sy.reverb(sy.pitch(lf, r), 1.4, 0.35) for r in (0.9, 1.1)])
    wd = sy.at(3.6, (0.0, chord(220, "oo", 1.6, (1.0, 1.26, 1.5), attack=0.3, release=0.6) * 0.5),
               (1.3, chord(174.6, "ah", 2.2, (1.0, 1.26, 1.5, 2.0), attack=0.3, release=1.2) * 0.55),
               (0.2, sy.shimmer(2.5, 2800, 18)[::-1] * 0.25), (1.3, sy.bell(349.2, 2.0, bright=0.8) * 0.3))
    sy.save(pack, "dw5_withdraw", sy.reverb(wd, 2.8, 0.45), max_distance=112)
    un = sy.at(2.8, (0.0, sy.shimmer(2.4, 2200, 30, 2.6) * 0.45), (0.0, sy.scribble(1.8, 10) * 0.35),
               (0.2, sy.choir(293.7, 2.2, "oo", voices=4, attack=0.1, release=1.6) * 0.35), (0.0, sy.whoosh(1.6, 500, 3500) * 0.3))
    sy.save(pack, "dw5_unmake", sy.reverb(un, 2.4, 0.45), max_distance=112)


def build(pack):
    build_fx(pack)
    build_sounds(pack)
    gates = [("dw5_gate_seraph", seraph_gate, seraph_gate_anims, "Gate of the Seraphim", 1.5, ["breathe"]),
             ("dw5_gate_cherub", cherub_gate, cherub_gate_anims, "Gate of the Cherubim", 2.0, ["breathe"]),
             ("dw5_gate_ophan", ophan_gate, ophan_gate_anims, "Gate of the Ophanim", 2.0, ["turn"])]
    for ident, mk, an, disp, sc, alw in gates:
        m = mk()
        A = an()
        pack.actor(ident, m, A, GATE_STATES, always=alw, scale=sc, lifetime=60, display=disp, blend=0.1)
        by = {a.name: a for a in A}
        ab = by[alw[0]]
        pack.preview(ident, m, [[(by["closed"], 0), (ab, 0.5)], [(by["opened"], 0), (ab, 0.5)],
                                [(by["manifest"], 0.7), (ab, 0.5)], [(by["fold"], 0.7), (ab, 0.5)]],
                     views=((0, 6), (35, 15)), cell=(380, 380))
        print(f"    {ident}: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}")
    sms = [sentence_model(k) for k in range(3)]
    sa = sentence_anims()
    pack.actor("dw5_sentence", sms[0], sa, SENTENCE_STATES, always=["drift"], kinds=sms[1:], size_prop=True, lifetime=60,
               display="Sacred Sentence", blend=0.0)
    sb = {a.name: a for a in sa}
    pack.preview("dw5_sentence", sms[0], [(sb["unfold"], 0.6), (sb["idle"], 0.5), (sb["gather"], 0.7)],
                 views=((20, 25),), cell=(380, 380))
    th = throne_model()
    ta = throne_anims()
    pack.actor("dw5_throne", th, ta, THRONE_STATES, always=["glory"], scale=2.0, lifetime=60, display="The Empty Throne",
               visibility=[{"swarm": "q.property('grimoire:state') == 4"}, {"streams": "q.property('grimoire:state') == 1"}],
               blend=0.1)
    tb = {a.name: a for a in ta}
    gl = (tb["glory"], 1.0)
    pack.preview("dw5_throne", th, [[(tb["idle"], 0), gl], [(tb["declare"], T_DECLARE), gl]],
                 views=((0, 8), (35, 15), (110, 10)), cell=(400, 400), hide=("swarm", "streams"))
    pack.preview("dw5_throne_b", th, [[(tb["assemble"], t), gl] for t in (0.6, 1.4, 2.0, 2.5)] +
                 [[(tb["unmake"], 0.9), gl]], views=((30, 15),), cell=(300, 300), hide=("streams",))
    print(f"    dw5_throne: {th.cube_count()} cubes, {len(th.order)} bones, tex {th.tex_size}")
    lms = [letter_model(i) for i in range(len(LETTER_GLYPHS))]
    la = letter_anims()
    pack.actor("dw5_letter", lms[0], la, LETTER_STATES, always=["shine"], kinds=lms[1:], scale=1.2, lifetime=60,
               display="Verdict Letter", blend=0.0)
    lb = {a.name: a for a in la}
    pack.preview("dw5_letter", lms[0], [(lb["hold"], 0.2), (lb["plunge"], 0.2), (lb["impact"], 0.2)],
                 views=((0, 5), (40, 15)), cell=(260, 260))
