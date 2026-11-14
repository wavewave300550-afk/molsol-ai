"""DW06 -- the great codex (spell construct) and the giant ivory page that folds back into it."""
import math

import numpy as np

from kit import tex
from kit.anim import LIFE, Anim
from kit.geo import Mat, Model

from .dw6_common import BLUE, FW, GOLD, IVORY, WGOLD, spin

# ------------------------------------------------------------------------------------------- book
BOOK_STATES = {0: ["hidden"], 1: ["arrive"], 2: ["open"], 3: ["unbind"], 4: ["layered"], 5: ["gather"], 6: ["close"],
               7: ["vanish"]}
BOOK_TILT = -28
# separated page-layer offsets (right side; left mirrored), in the half's frame
LAYER_OFF = [(-6, 14, -2), (-12, 27, 3), (-4, 41, 7)]
LAYER_ROT = [(-6, 0, 10), (4, 0, 18), (-10, 0, 7)]


def leather():
    return tex.trimmed(tex.mottled("#2b3f8f", "#1f2d68", scale=3, var=0.05, edge_dark=0.15), GOLD, 1, 1, glow=0.35)


def page_text():
    return tex.glyph_rows(FW, "#8a6a26", glow=0.35, color2="#b8923a", bg="#f6f0df", bg_glow=0.2, fill=0.8,
                          key="dw6bookpage")


def page_blank():
    def fn(ctx):
        t = tex.tile(ctx, "#f8f3e4", 1, 0.3)
        ix, iy = tex.px(ctx)
        t[..., :3] *= (0.97 + 0.04 * tex.fbm(ix / 4.0, iy / 4.0, 3))[..., None]
        rule = (iy % 4 == 2)
        t[..., :3] = np.where(rule[..., None], t[..., :3] * 0.93, t[..., :3])
        return t
    return Mat(fn, "dw6pageblank")


def build_book():
    m = Model("dw6_book", density=2.0, bounds=(10, 9, (0, 2, 0)), alts=("blank",))
    lea = leather()
    gold = tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=2.0, glow=0.3)
    edge = tex.banded(tex.flat("#efe6cc"), "#d8cba6", every=2, width=1)
    gilt_edge = tex.banded(tex.flat("#e9c15a", glow=0.4), "#b8923a", every=2, width=1)
    paper = tex.alt(page_text(), blank=page_blank())
    medal = tex.stamped(tex.metal("#d9b45a", "#fff3c4", "#8a6a26", glow=0.5), FW[13], "#ffffff", glow=1.0, scale=1)
    root = m.bone("root")
    seal = m.bone("seal", root, pivot=(0, -12, 0))
    seal.plane("y", (0, -12, 0), 84, 84, tex.magic_circle(FW, WGOLD, GOLD, bands=((0.72, 0.92, 24),), lines=(0.68, 0.96),
                                                           star=7, star_r=(0.2, 0.62), core=0.06), faces=("up", "down"))
    book = m.bone("book", root, pivot=(0, 0, 0), rot=(BOOK_TILT, 0, 0))
    book.box((0, 0, 0), (4, 4, 48), lea)                                          # spine
    for z in (-15, 0, 15):
        book.box((0, 0, z), (4.6, 4.6, 2), gold, variant=1)
    for s, sx in (("l", -1), ("r", 1)):
        h = m.bone(f"half_{s}", book, pivot=(0, 6, 0))
        x0 = 0 if sx > 0 else -35
        h.cube((x0, -1, -24), (35, 2, 48), lea, mats={"down": tex.trimmed(lea, WGOLD, 1, 3, glow=0.7)})
        h.cube((x0 + (1 if sx > 0 else 2), 1, -22.5), (32, 5, 45), edge, mats={"up": paper, "east": gilt_edge, "west": gilt_edge})
        for cz in (-21, 21):                                                     # gilt corner guards
            h.box((sx * 31.5, -1.2, cz), (7, 2.6, 7), gold, variant=2)
        h.box((sx * 17.5, -2.2, 0), (10, 1, 10), medal)                          # front medallion (outside of cover)
        h.box((sx * 17.5, -2.6, 0), (4, 1, 14), gold, rot=(0, 45, 0))
        h.box((sx * 17.5, -2.6, 0), (4, 1, 14), gold, rot=(0, -45, 0))
        # three loose page layers that lift and separate in Phase I
        for i in range(3):
            k = i + 1 if sx < 0 else i + 4
            lb = m.bone(f"lay{k}", h, pivot=(sx * 17.5, 6.2, 0))
            lb.plane("y", (sx * 17.5, 6.2 + 0.15 * i, 0), 31, 43, paper, variant=i)
    for j, (bx, col) in enumerate(((-1.4, BLUE), (1.4, "#d9b45a"))):            # bookmark ribbons
        par = "book"
        for k in range(3):
            y = 2 - k * 6
            b = m.bone(f"rib{j}_{k}", par, pivot=(bx, y, -24))
            b.plane("z", (bx, y - 3.25, -24.3), 2.2, 6.5, tex.fabric(col, None, 0.06, glow=0.2, fringe=(k == 2)), variant=k)
            par = b.name
    return m


def book_anims():
    A = []
    always = Anim("float", loop=True)
    always.rot("seal", (0, spin(24), 0))
    for j in range(2):
        for k in range(3):
            always.rot(f"rib{j}_{k}", (LIFE(6 + 4 * k, 2.6, j * 0.3 + k * 0.12), 0, LIFE(3, 3.3, j * 0.2)))
    A.append(always)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    arrive = Anim("arrive", length=2.8, loop="hold")     # the seal opens first, the codex rises through it
    arrive.scl("seal", {0: 0.0, 0.45: 1.15, 0.75: 1.0})
    arrive.scl("book", {0: 0.0, 0.3: 0.0, 0.75: 0.92, 1.0: 1.0})
    arrive.pos("book", {0: (0, -26, 0), 0.3: (0, -26, 0), 1.1: (0, 3, 0), 1.45: (0, 0, 0)})
    arrive.rot("book", {0: (0, -200, 0), 0.3: (0, -200, 0), 1.25: (0, 0, 0)})
    arrive.rot("half_r", {0: (0, 0, 179), 1.2: (0, 0, 179), 1.95: (0, 0, -9), 2.3: (0, 0, 3), 2.6: (0, 0, 0)})
    for k, lag in ((4, 0.1), (5, 0.2), (6, 0.3)):                                 # pages trail behind the cover
        arrive.rot(f"lay{k}", {0: (0, 0, 0), 1.3 + lag: (0, 0, 0), 1.95 + lag: (0, 0, 28 - lag * 30), 2.6 + lag: (0, 0, 0)})
    A.append(arrive)

    open_ = Anim("open", loop=True)
    open_.pos("root", (0, LIFE(1.0, 4.0), 0))
    for k in range(1, 7):
        open_.rot(f"lay{k}", (0, 0, LIFE(1.5, 3.0, k * 0.17)))
    A.append(open_)

    def layer_target(k):
        i = (k - 1) % 3
        sx = -1 if k <= 3 else 1
        o, r = LAYER_OFF[i], LAYER_ROT[i]
        return (o[0] * sx, o[1], o[2]), (r[0], r[1] * sx, r[2] * sx)

    unbind = Anim("unbind", length=2.0, loop="hold")
    for k in range(1, 7):
        (p, r), d = layer_target(k), 0.12 * ((k - 1) % 3) + (0.05 if k > 3 else 0)
        unbind.pos(f"lay{k}", {0: (0, 0, 0), 0.25 + d: (p[0] * 0.1, p[1] * 0.2, 0), 1.5 + d: (p[0] * 1.05, p[1] * 1.06, p[2]), 1.9: p})
        unbind.rot(f"lay{k}", {0: (0, 0, 0), 0.25 + d: (0, 0, -r[2] * 0.6), 1.5 + d: r, 1.9: r})
    unbind.pos("root", (0, LIFE(1.0, 4.0), 0))
    A.append(unbind)

    layered = Anim("layered", loop=True)
    for k in range(1, 7):
        p, r = layer_target(k)
        layered.pos(f"lay{k}", (p[0], LIFE(1.6, 3.2, k * 0.21, p[1]), p[2]))
        layered.rot(f"lay{k}", (LIFE(4, 4.1, k * 0.13, r[0]), LIFE(6, 5.3, k * 0.19), LIFE(4, 3.7, k * 0.27, r[2])))
    layered.pos("root", (0, LIFE(1.0, 4.0), 0))
    A.append(layered)

    gather = Anim("gather", length=1.5, loop="hold")
    for k in range(1, 7):
        p, r = layer_target(k)
        d = 0.1 * ((k * 5) % 6) / 5
        gather.pos(f"lay{k}", {0: p, 0.2 + d: (p[0], p[1] + 4, p[2]), 1.1 + d: (0, 0, 0), 1.5: (0, 0, 0)})
        gather.rot(f"lay{k}", {0: r, 1.1 + d: (0, 0, 0), 1.5: (0, 0, 0)})
    A.append(gather)

    close = Anim("close", length=1.6, loop="hold")       # the cover swings shut and stays shut
    close.rot("half_r", {0: (0, 0, 0), 0.25: (0, 0, -7), 0.95: (0, 0, 183), 1.1: (0, 0, 179), 1.6: (0, 0, 179)})
    close.pos("root", {0: (0, 0, 0), 0.85: (0, 2.5, 0), 1.05: (0, -1.2, 0), 1.6: (0, 0, 0)})
    close.scl("seal", {0: 1.0, 0.9: 1.0, 1.1: 1.4, 1.6: 1.08})
    A.append(close)
    vanish = Anim("vanish", length=1.5, loop="hold")     # the closed codex lifts, flares and dissolves into light
    vanish.rot("half_r", (0, 0, 179))
    vanish.pos("root", {0: (0, 0, 0), 0.5: (0, 6, 0), 1.5: (0, 22, 0)})
    vanish.rot("root", {0: (0, 0, 0), 1.5: (0, 220, 0)})
    vanish.scl("root", {0: 1.0, 0.45: 1.12, 1.5: 0.0})
    vanish.scl("seal", {0: 1.08, 0.4: 1.7, 1.1: 0.0})
    A.append(vanish)
    return A


# ------------------------------------------------------------------------------------------- page
PAGE_STATES = {0: ["hidden"], 1: ["manifest"], 2: ["idle"], 3: ["split"], 4: ["reform"], 5: ["fold"], 6: ["slip"]}
PAGE_TILT = 9             # degrees the page leans back: it hangs ~40 m away, its face toward the caster's eye
PAGE_SCALE = 3.0          # 120 x 88 model units -> 22.5 x 16.5 blocks (fits the upper view at ~40 m)
PW, PH = 120, 88
COLS = [-60, -30, 0, 30]
ROWS = [0, 22, 44, 66]
FOLD_PIVOT = {1: (0, 0, 0), 2: (0, 44, 0), 3: (-30, 0, 0), 4: (0, 22, 0)}
FOLD_ROT = {1: (0, 180, 0), 2: (-180, 0, 0), 3: (0, 180, 0), 4: (-180, 0, 0)}
FOLD_T = {1: (0.15, 0.7), 2: (0.7, 1.25), 3: (1.25, 1.8), 4: (1.8, 2.35)}
FOLD_LEN = 2.6
S_FOLD = [1.0, 0.8, 0.62, 0.45, 0.3]
# columns of the page ruling, in page units measured from the viewer's left (a = -X) -> tablet slots
RULE_A0, RULE_A1 = -45.0, 57.0


def folds_of(c, r):
    out = []
    if c in (2, 3):
        out.append(1)
    if r in (2, 3):
        out.append(2)
    if c in (1, 2):
        out.append(3)
    if r in (1, 2):
        out.append(4)
    return out


def page_front():
    gold, ink = tex.rgb("#c9a24a"), tex.rgb("#e2cf98")
    blue, wg = tex.rgb(BLUE), tex.rgb("#ffe9a3")
    stack = np.array([[[c == "#" for c in row] for row in g] for g in FW], dtype=bool)

    def fn(ctx):
        a, b = -ctx.X, ctx.Y
        t = tex.tile(ctx, "#f7f1e0", 1, 0.34)
        n = tex.fbm(a * 0.9, b * 0.9, 5)
        t[..., :3] *= (0.95 + 0.07 * n)[..., None]
        ed = np.minimum(np.minimum(a + 60, 60 - a), np.minimum(b, 88 - b))
        t[..., :3] *= (0.9 + 0.1 * np.clip(ed / 8, 0, 1))[..., None]
        on_gold = (np.abs(ed - 2.2) < 0.32) | (np.abs(ed - 3.4) < 0.2)
        # ruling lines and the seven column guides
        inside = (a > RULE_A0) & (a < RULE_A1) & (b > 7) & (b < 81)
        rule = inside & (np.abs(((b - 8.0) % 5.5) - 0) < 0.22)
        cw = (RULE_A1 - RULE_A0) / 7
        colg = (b > 6) & (b < 82) & (np.abs(((a - RULE_A0 + cw / 2) % cw) - cw / 2) < 0.2) & (a > RULE_A0 - 0.5) & (a < RULE_A1 + 0.5)
        colg &= ((np.floor(b / 1.1) % 2) == 0)
        t[..., :3] = np.where(rule[..., None], tex.mix(t[..., :3], ink, 0.75), t[..., :3])
        t[..., :3] = np.where(colg[..., None], tex.mix(t[..., :3], gold, 0.55), t[..., :3])
        t[..., 4] = np.where(rule | colg, 0.45, t[..., 4])
        # illuminated margin: royal-blue band, gold vine, three glyph roundels
        band = (a > -57) & (a < -47.5) & (b > 4.5) & (b < 83.5)
        t[..., :3] = np.where(band[..., None], blue * (0.85 + 0.2 * n[..., None]), t[..., :3])
        t[..., 4] = np.where(band, 0.35, t[..., 4])
        vine = band & (np.abs(a - (-52.25 + 2.6 * np.sin(b * 0.45))) < 0.45)
        leaf = band & (np.hypot(a - (-52.25 + 2.6 * np.sin(b * 0.45)) - 1.6 * np.cos(b * 0.9), (b % 4.0) - 2) < 0.7)
        bord = band & ((np.abs(a + 57) < 0.5) | (np.abs(a + 47.5) < 0.5) | (np.abs(b - 4.5) < 0.5) | (np.abs(b - 83.5) < 0.5))
        gl = np.zeros_like(band)
        for k, cb in enumerate((18.0, 44.0, 70.0)):
            rr = np.hypot(a + 52.25, b - cb)
            disc = rr < 4.1
            gl |= np.abs(rr - 3.7) < 0.35
            gx = np.floor((a + 52.25 + 2.5) / 1.0).astype(int)
            gy = np.floor((cb + 3.5 - b) / 1.0).astype(int)
            okg = disc & (gx >= 0) & (gx < 5) & (gy >= 0) & (gy < 7)
            gi = [2, 7, 14][k]
            gl |= okg & stack[gi, np.clip(gy, 0, 6), np.clip(gx, 0, 4)]
            t[..., :3] = np.where((disc & ~gl)[..., None], blue * 0.7, t[..., :3])
        orn = vine | leaf | bord | gl | on_gold
        t[..., :3] = np.where(orn[..., None], tex.mix(gold, wg, 0.5 + 0.5 * np.sin(a * 0.7 + b * 0.3)[..., None] ** 2), t[..., :3])
        t[..., 4] = np.where(orn, 0.95, t[..., 4])
        # corner fleurons
        for ca, cb in ((-60, 0), (60, 0), (-60, 88), (60, 88)):
            d = np.hypot(a - ca * 0.9, b - (cb * 0.92 + 3.5))
            fl = (d < 2.2) & (np.abs(np.sin(np.arctan2(b - (cb * 0.92 + 3.5), a - ca * 0.9) * 4)) > 0.35 + d * 0.15)
            t[..., :3] = np.where(fl[..., None], gold, t[..., :3])
            t[..., 4] = np.where(fl, 0.9, t[..., 4])
        return t
    return Mat(fn, "dw6pagefront", spatial=True)


def page_back():
    return tex.trimmed(tex.mottled("#ece3cb", "#ddd1b2", scale=6, var=0.02, glow=0.25, edge_dark=0.0), GOLD, 1, 1, glow=0.6)


def build_page():
    m = Model("dw6_page", density=1.0, bounds=(44, 40, (0, 8, 0)))
    front, back = page_front(), page_back()
    root = m.bone("root")
    tilt = m.bone("tilt", root, pivot=(0, 0, 0), rot=(PAGE_TILT, 0, 0))
    for c in range(4):
        for r in range(4):
            par = tilt.name
            chain = sorted(folds_of(c, r), reverse=True)        # outermost (last) fold first
            for k in chain:
                par = m.bone(f"f{k}_{c}{r}", par, pivot=FOLD_PIVOT[k]).name
            cx, cy = COLS[c] + 15, ROWS[r] + 11
            p = m.bone(f"p{c}{r}", par, pivot=(cx, cy, 0))
            p.plane("z", (cx, cy, 0), 30, 22, front, mats={"south": back}, density=5.5)
    return m


def _fold_channels(a, final=False):
    for c in range(4):
        for r in range(4):
            for k in folds_of(c, r):
                b = f"f{k}_{c}{r}"
                t0, t1 = FOLD_T[k]
                rot, dz = FOLD_ROT[k], -0.35 * k
                if final:
                    a.rot(b, rot)
                    a.pos(b, (0, 0, dz))
                else:
                    mid = tuple(v * 0.55 for v in rot)
                    a.rot(b, {0: (0, 0, 0), t0: (0, 0, 0), t0 + (t1 - t0) * 0.45: mid, t1: rot, FOLD_LEN: rot})
                    a.pos(b, {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.1: (0, 0, dz), FOLD_LEN: (0, 0, dz)})


def page_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    manifest = Anim("manifest", length=2.5, loop="hold")   # a seam of light opens into the page
    manifest.scl("root", {0: (0.0, 0.0, 1.0), 0.3: (0.012, 0.3, 1.0), 0.6: (0.012, 1.0, 1.0), 1.7: (1.03, 1.0, 1.0),
                          2.0: (0.995, 1.0, 1.0), 2.5: (1.0, 1.0, 1.0)})
    for c in range(4):
        for r in range(4):
            d = abs(c - 1.5) * 0.18 + (3 - r) * 0.06
            manifest.rot(f"p{c}{r}", {0: (0, 0, 0), 0.9 + d: (-12, 0, 0), 1.6 + d: (3, 0, 0), 2.1 + d * 0.5: (0, 0, 0)})
    A.append(manifest)
    idle = Anim("idle", loop=True)
    idle.pos("root", (0, LIFE(1.5, 7.0), 0))                 # a slow breath (letters are written on its face)
    idle.rot("root", (LIFE(0.6, 9.0), 0, LIFE(0.4, 11.0)))
    A.append(idle)
    split = Anim("split", length=1.2, loop="hold")          # the sheet parts along its ruling
    for c in range(4):
        for r in range(4):
            d = c * 0.12 + (3 - r) * 0.04
            split.scl(f"p{c}{r}", {0: 1.0, 0.15 + d: (1.0, 1.06, 1.0), 0.55 + d: (0.94, 0.0, 1.0)})
            split.pos(f"p{c}{r}", {0: (0, 0, 0), 0.55 + d: (0, 0, -6)})
    A.append(split)
    reform = Anim("reform", length=1.1, loop="hold")
    for c in range(4):
        for r in range(4):
            d = (3 - c) * 0.07 + r * 0.03
            reform.scl(f"p{c}{r}", {0: (0.9, 0.0, 1.0), 0.1 + d: (0.9, 0.0, 1.0), 0.55 + d: (1.0, 1.08, 1.0), 0.75 + d: 1.0})
    A.append(reform)
    fold = Anim("fold", length=FOLD_LEN, loop="hold")        # four folds in halves, shrinking to a book page
    _fold_channels(fold)
    keys_s, keys_p = {0: 1.0}, {0: (0, 0, 0)}
    shift = [0, 30, 30, 45, 45]
    for k in range(1, 5):
        t1 = FOLD_T[k][1]
        keys_s[t1] = S_FOLD[k]
        keys_p[t1] = (shift[k] * S_FOLD[k], 0, 0)
    keys_s[FOLD_LEN], keys_p[FOLD_LEN] = S_FOLD[4], (shift[4] * S_FOLD[4], 0, 0)
    fold.scl("root", keys_s)
    fold.pos("root", keys_p)
    fold.rot("tilt", {0: (0, 0, 0), 1.0: (-PAGE_TILT * 0.5, 0, 0), 2.35: (-PAGE_TILT, 0, 0), FOLD_LEN: (-PAGE_TILT, 0, 0)})
    A.append(fold)
    slip = Anim("slip", length=0.8, loop="hold")             # the folded page slides into the codex
    _fold_channels(slip, final=True)
    slip.rot("tilt", (-PAGE_TILT, 0, 0))
    s4 = S_FOLD[4]
    slip.scl("root", {0: s4, 0.2: s4 * 1.1, 0.8: 0.0})
    slip.pos("root", {0: (45 * s4, 0, 0), 0.8: (45 * s4, -10, 0)})
    A.append(slip)
    return A


def build(pack):
    bm = build_book()
    ba = book_anims()
    pack.actor("dw6_book", bm, ba, BOOK_STATES, always=["float"], scale=1.3, size_prop=True, lifetime=90,
               display="Codex of the First Word")
    pm = build_page()
    pa = page_anims()
    pack.actor("dw6_page", pm, pa, PAGE_STATES, scale=PAGE_SCALE, lifetime=90, display="The First Page", blend=0.1)
    by = {a.name: a for a in ba}
    fl = (by["float"], 0.5)
    pack.preview("dw6_book", bm, [[(by["arrive"], 0.9), fl], [(by["open"], 0.0), fl], [(by["layered"], 1.0), fl],
                                  [(by["close"], 1.6), fl], [(by["vanish"], 0.6), fl]], views=((25, 30), (160, 25)), skin=None)
    pack.preview("dw6_book_blank", bm, [[(by["layered"], 1.0), fl]], views=((25, 30),), skin="blank")
    pb = {a.name: a for a in pa}
    pack.preview("dw6_page", pm, [(pb["idle"], 0.0), (pb["fold"], 0.7), (pb["fold"], 1.25), (pb["fold"], 1.8), (pb["fold"], 2.6)],
                 views=((20, 15), (-60, 10)))
    print(f"    dw6_book: {bm.cube_count()} cubes, {len(bm.order)} bones, tex {bm.tex_size}; "
          f"dw6_page: {pm.cube_count()} cubes, {len(pm.order)} bones, tex {pm.tex_size}")
