"""ED06 -- the Great Codex construct, the four dragon emblems and the luminous skeletal imagery.

ed6_codex   (scale 2.4, ~4.2 blocks wide, ~4.2 tall + orbits ~11 blocks across)
    A spell construct of the Codex of the Four Primordial Dragons: antique-bronze cover scales
    (12 front, 12 back), an articulated vertebral spine of 8 ivory vertebrae, aged-gold corners,
    a glowing draconic seal on the back cover with four lineage gems, and riffling pages with
    anatomical drawings.  Origin = 1 block under the book's lower edge.
    Float properties (eased on the client, so changing them never snaps):
        grimoire:sep  0 = scales and vertebrae bound to the book, 1 = separated, orbiting
                      (cover scales on two horizontal rings, vertebrae on a vertical halo)
        grimoire:open 0 = closed, 1 = front cover swung open, book tilted back to show its pages
    Skins: 0 dark gems, 1..4 = that many lineage gems lit (Nature, Heat, Water & Ice, Air).
    STATES 0 hidden / 1 rise (2.0 s) / 2 hover / 3 beat (0.6 s heartbeat thump) /
           4 absorb (loop: pages riffle) / 5 vanish (1.6 s: shrinks into a mote and rises)
ed6_emblem  kinds 0-3 = Nature (sauropod skull, leaves & roots) / Heat (horned carnotaur skull,
    flame tongues) / Water & Ice (long spinosaur skull, wave crests) / Air (raptor skull, feather
    ring).  Ground sigil radius 2 blocks at size 1, a standing translucent skull projection and six
    rising rune claws.  STATES 0 hidden / 1 appear (1.0 s) / 2 beat (0.8 s) / 3 glow / 4 fade (1.0 s)
ed6_spirit  kinds 0-3 = luminous line-art skeleton of each dragon in that dragon's own model space,
    so spawning it at the dragon's position / yaw with size = the dragon's SCALE overlays it.  A
    ribbon of draconic inscriptions runs along each spine.
    STATES 0 hidden / 1 form (1.2 s) / 2 hold / 3 stream (1.4 s: folds into a ribbon and vanishes)
"""
import math

import numpy as np

from kit import tex
from kit.anim import LIFE, Anim, M
from kit.geo import Mat, Model, ring

from .ed6_common import BRONZE, BRONZE_HI, BRONZE_LO, DR, GOLD, IVORY, LINEAGE, T, rgb, mix, px, spin, worley

# ============================================================================== skull silhouettes (side view, snout left)
SKULLS = [
    [  # Nature: sauropod -- tall domed skull, huge nasal arch over the eye, spoon teeth
        "              ########          ",
        "           ##############       ",
        "         ######      ######     ",
        "        #####          #####    ",
        "       #####  ########  ######  ",
        "      ######  ########  ####### ",
        "     #######   ######   ###  ###",
        "    #########          ###    ##",
        "   ###########        ####    ##",
        "  ##############    ######   ###",
        " ######  #######################",
        " #####    ###### ####   ########",
        "#######  ######  ####   ####### ",
        "################################",
        "# # # # # # #################   ",
        "               ##############   ",
        "# # # # # # ###########         ",
        " ######################         ",
    ],
    [  # Heat: carnotaur -- two thick brow horns, deep short skull, keyhole orbit
        "                 ###     ###    ",
        "                ####    ####    ",
        "               #####   #####    ",
        "              ######  ######    ",
        "         ######################  ",
        "      ##########################",
        "    #######     #####   ###  ###",
        "   ######        ###    ##    ##",
        "  #######        ###    ##    ##",
        " ########       ####   ####  ###",
        "##########     ######  #########",
        "################################",
        "# # # # # # ####################",
        "             ##   ##########    ",
        "# # # # # # ##############      ",
        " ######################         ",
    ],
    [  # Water & Ice: spinosaur -- very long narrow snout with a rosette, crest, interlocking teeth
        "                         ####   ",
        "                       ######## ",
        "                ###  ###########",
        "  ####       ######## ###  #####",
        " ######################     ####",
        "##############################  ",
        "# # #  #  #  #  #  ##########   ",
        "                    #######     ",
        "# # #  #  #  #  #  ###          ",
        "#######################         ",
        " #####                          ",
    ],
    [  # Air: microraptor -- rounded braincase, huge orbit, slender toothy snout, feather crest
        "                     # # # #    ",
        "                    ## ## ## #  ",
        "                  ###########   ",
        "              ######      ####  ",
        "          ########   ##    #### ",
        "      ###########   ####   #####",
        "  ##############     ##   ######",
        "#####   #########         ######",
        "################################",
        "# # # # # ##################### ",
        "          ##############        ",
        "# # # # ###############         ",
        " ###################            ",
    ],
]
SKULLS = [np.array([[c == "#" for c in r.ljust(32)[:32]] for r in s], dtype=bool) for s in SKULLS]


def skull_sample(k, u, v, x0, x1, yc):
    """Bitmap of skull k drawn in the box x0..x1 (u axis, left = snout), centred on v = yc.  Returns bool."""
    bm = SKULLS[k]
    h, w = bm.shape
    cell = (x1 - x0) / w
    y0 = yc + cell * h / 2
    ix = np.floor((u - x0) / cell).astype(int)
    iy = np.floor((y0 - v) / cell).astype(int)
    ok = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
    return np.where(ok, bm[np.clip(iy, 0, h - 1), np.clip(ix, 0, w - 1)], False)


# ============================================================================== emblems
def _ornament(k, u, v, r, a):
    """Lineage ornament band (0.56 .. 0.76)."""
    if k == 0:      # leaves on a wavy vine with roots creeping inward
        n = 10
        ak = (a * n / (2 * math.pi)) % 1.0
        s = (ak - 0.5) * 2 * math.pi * r / n
        t = (r - 0.57) / 0.19
        leaf = (t > 0) & (t < 1) & (np.abs(s) < 0.075 * np.sin(np.pi * np.clip(t, 0, 1)) ** 0.8)
        vine = np.abs(r - (0.6 + 0.018 * np.sin(a * 20))) < 0.012
        roots = (np.abs(((a * 7 / (2 * math.pi)) % 1.0) - 0.5) < 0.012 + 0.02 * (0.56 - r)) & (r < 0.56) & (r > 0.5)
        return leaf | vine | roots, leaf & (np.abs(s) < 0.01)
    if k == 1:      # flame tongues licking outward
        n = 14
        ak = (a * n / (2 * math.pi)) % 1.0
        s = (ak - 0.5) * 2 * math.pi * r / n + 0.02 * np.sin(r * 40)
        t = (r - 0.56) / 0.21
        tongue = (t > 0) & (t < 1) & (np.abs(s) < 0.085 * (1 - np.clip(t, 0, 1)) ** 1.2)
        core = tongue & (np.abs(s) < 0.03 * (1 - np.clip(t, 0, 1)))
        vents = (np.abs(r - 0.585) < 0.01)
        return tongue | vents, core
    if k == 2:      # wave crests and droplets
        crest = np.abs(r - (0.64 + 0.045 * np.sin(a * 12))) < 0.018
        crest2 = np.abs(r - (0.6 + 0.03 * np.sin(a * 12 + 1.2))) < 0.01
        da = (a * 12 / (2 * math.pi)) % 1.0
        drop = np.hypot((da - 0.5) * 2 * math.pi * r / 12, r - 0.73) < 0.025
        return crest | crest2 | drop, crest
    n = 16          # feathers with rachis, alternating length
    ak = (a * n / (2 * math.pi)) % 1.0
    idx = np.floor(a * n / (2 * math.pi)).astype(int)
    L = np.where(idx % 2 == 0, 0.2, 0.15)
    s = (ak - 0.5) * 2 * math.pi * r / n
    t = (r - 0.565) / L
    vane = (t > 0) & (t < 1) & (np.abs(s) < 0.06 * np.sin(np.pi * np.clip(t, 0, 1) ** 0.7))
    rach = vane & (np.abs(s) < 0.008)
    return vane, rach


def emblem_mat(k):
    b, m, d = (rgb(c) for c in LINEAGE[k])
    gl = rgb(GOLD)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        r = np.hypot(u, v)
        a = np.arctan2(v, u) % (2 * math.pi)
        t = T(ctx, m, 1.0, 0.0)
        pxl = 2.0 / ctx.w
        lines = (np.abs(r - 0.985) < pxl * 1.2) | (np.abs(r - 0.955) < pxl * 0.8) | (np.abs(r - 0.79) < pxl) | \
                (np.abs(r - 0.535) < pxl * 1.3) | (np.abs(r - 0.505) < pxl * 0.7)
        # glyph band 0.81 .. 0.94
        stack = np.array([[[c == "#" for c in row] for row in g] for g in DR], dtype=bool)
        ng, gh, gw = stack.shape
        nb = 22
        seg = a / (2 * math.pi) * nb
        gi = np.floor(seg).astype(int) % nb
        lx = np.floor((seg - np.floor(seg)) * (gw + 2)).astype(int) - 1
        ly = np.floor((0.935 - r) / (0.12 / gh)).astype(int)
        inside = (lx >= 0) & (lx < gw) & (ly >= 0) & (ly < gh) & (r < 0.935) & (r > 0.815)
        glyph = inside & stack[(gi * 5 + k * 3) % ng, np.clip(ly, 0, gh - 1), np.clip(lx, 0, gw - 1)]
        orn, orn_hi = _ornament(k, u, v, r, a)
        orn &= (r > 0.5) & (r < 0.78)
        disc = r < 0.505
        sk = skull_sample(k, u, v, -0.47, 0.47, -0.01)
        sk_out = disc & ~sk & (r > 0.0)
        on = lines | glyph | orn | disc
        col = np.broadcast_to(m, t[..., :3].shape).copy()
        col = np.where(glyph[..., None] | lines[..., None], mix(b, gl, 0.35), col)
        col = np.where(orn[..., None], mix(m, b, 0.35), col)
        col = np.where(orn_hi[..., None], b, col)
        # medallion: deep lineage colour over bronze, faint concentric grain
        grain = 0.5 + 0.5 * np.sin(r * 90 + tex.fbm(u * 6, v * 6, 3 + k) * 4)
        med = mix(mix(rgb(BRONZE_LO), d, 0.55), mix(rgb(BRONZE), d, 0.4), grain[..., None] * 0.6)
        col = np.where(sk_out[..., None], med, col)
        col = np.where((disc & sk)[..., None], mix(b, rgb("#ffffff"), 0.35), col)
        t[..., :3] = col
        t[..., 3] = on * 1.0
        glow = np.where(sk_out, 0.25, 1.0)
        glow = np.where(orn & ~orn_hi, 0.85, glow)
        t[..., 4] = glow
        return t
    return Mat(fn, f"ed6emblem{k}", directional=True)


def skull_mat(k, mode="solid", a=1.0, glow=1.0, key=""):
    b, m, d = (rgb(c) for c in LINEAGE[k])

    def fn(ctx):
        u, v = ctx.U * 2 - 1, (1 - ctx.V * 2) * ctx.h / ctx.w
        sk = skull_sample(k, u, v, -1.0, 1.0, 0.0)
        # outline ring of the bitmap for a crisp inked edge
        pad = np.pad(sk, 1)
        nb = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
        rim = sk & ~nb
        t = T(ctx, mix(b, rgb("#ffffff"), 0.25), glow, 0.0)
        t[..., :3] = np.where(rim[..., None], m, t[..., :3])
        t[..., 3] = np.where(sk, a, 0.0)
        return t
    return Mat(fn, f"ed6skull{k}{mode}{a}{glow}{key}", mode=mode, directional=True)


def emblem_model(k):
    m = Model(f"ed6_emblem_{k}", density=3.0, bounds=(14, 6, (0, 2, 0)))
    asp = SKULLS[k].shape[0] / SKULLS[k].shape[1]
    root = m.bone("root")
    sig = m.bone("sigil", root)
    sig.plane("y", (0, 0.3, 0), 64, 64, emblem_mat(k), faces=("up",))
    sk = m.bone("skull", root, pivot=(0, 0.7, 0))
    sk.plane("y", (0, 0.7, 0.5), 30, 30 * asp, skull_mat(k, key="flat"), faces=("up",))
    holo = m.bone("holo", root, pivot=(0, 22, 0))
    holo.plane("z", (0, 22, 0), 50, 50 * asp, skull_mat(k, mode="blend", a=0.62, glow=1.0, key="holo"), density=2.0)
    claws = m.bone("claws", root)
    b, mcol, d = LINEAGE[k]
    for i in range(6):
        cb = m.bone(f"claw{i + 1}", claws, pivot=(0, 0, 0), rot=(0, i * 60 + 30, 0))
        cb.plane("z", (0, 4.5, -29), 5, 8, tex.bitmap_cut(DR[(i * 2 + k) % len(DR)], b, glow=1.0, color2=mcol))
    return m


def emblem_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    turn = Anim("turn", loop=True)
    turn.rot("claws", (0, spin(-12), 0))
    turn.rot("holo", (0, spin(24), 0))
    turn.pos("holo", (0, LIFE(1.2, 3.1), 0))
    A.append(turn)
    appear = Anim("appear", length=1.0, loop="hold")
    appear.scl("sigil", {0: 0.0, 0.55: 1.1, 0.8: 0.97, 1.0: 1.0})
    appear.scl("skull", {0: 0.0, 0.4: 0.0, 0.8: 1.15, 1.0: 1.0})
    appear.scl("holo", 0.0)
    for i in range(6):
        appear.pos(f"claw{i + 1}", {0: (0, -9, 0), 0.4 + i * 0.07: (0, -9, 0), 0.75 + i * 0.04: (0, 1, 0), 1.0: (0, 0, 0)})
    A.append(appear)
    beat = Anim("beat", length=0.8, loop="hold")     # lub-dub
    beat.scl("sigil", {0: 1.0, 0.07: 1.13, 0.2: 0.98, 0.3: 1.08, 0.5: 0.99, 0.8: 1.0})
    beat.scl("skull", {0: 1.0, 0.07: 1.3, 0.2: 1.0, 0.3: 1.18, 0.8: 1.05})
    beat.scl("holo", {0: 0.0, 0.1: 1.25, 0.3: 0.95, 0.4: 1.1, 0.8: 1.0})
    beat.pos("holo", {0: (0, -14, 0), 0.3: (0, 2, 0), 0.8: (0, 0, 0)})
    for i in range(6):
        beat.pos(f"claw{i + 1}", {0: (0, 0, 0), 0.08: (0, 3, 0), 0.4: (0, 0, 0)})
    A.append(beat)
    glow = Anim("glow", loop=True, length=1.6)       # heart keeps beating slowly
    glow.scl("sigil", {0: 1.0, 0.1: 1.05, 0.25: 1.0, 0.35: 1.03, 0.6: 1.0, 1.6: 1.0})
    glow.scl("skull", {0: 1.05, 0.1: 1.15, 0.25: 1.05, 0.35: 1.1, 0.6: 1.05, 1.6: 1.05})
    glow.scl("holo", 1.0)
    A.append(glow)
    fade = Anim("fade", length=1.0, loop="hold")
    fade.scl("sigil", {0: 1.0, 0.2: 1.08, 1.0: 0.0})
    fade.scl("skull", {0: 1.05, 0.5: 0.0})
    fade.scl("holo", {0: 1.0, 0.5: 0.0})
    fade.pos("holo", {0: (0, 0, 0), 0.5: (0, 14, 0)})
    for i in range(6):
        fade.pos(f"claw{i + 1}", {0: (0, 0, 0), 0.6: (0, -9, 0)})
    A.append(fade)
    return A


EMBLEM_STATES = {0: ["hidden"], 1: ["appear"], 2: ["beat"], 3: ["glow"], 4: ["fade"]}

# ============================================================================== the great codex
CX = (0.0, 24.0, 0.0)         # book centre
R_SC = (30.0, 36.0)           # orbit radius of the two scale tiers
R_VT = 33.0                   # vertebra halo radius
W_SC = (38.0, -30.0)          # deg / s
W_VT = 46.0
SC_COLS, SC_ROWS = (-10.0, 0.0, 10.0), (38.0, 28.5, 19.0, 9.5)
VT_Y = [5.0 + 5.0 * i for i in range(8)]


def _scale_plate_mat(seed):
    """One armoured bronze scale: domed, ridged, verdigris in the pits, hot gold rim."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        ix, iy = px(ctx)
        inside = (v < 0.05) | (u * u + ((v - 0.05) / 0.95) ** 2 < 1.0)
        sh = np.clip(1 - (u * u + (v + 0.25) ** 2) * 0.55, 0, 1)
        col = mix(rgb(BRONZE_LO), rgb(BRONZE_HI), sh[..., None] ** 1.3)
        n = tex.fbm(ix / 2.0 + seed * 3, iy / 2.0, 91 + ctx.variant)
        verd = (n > 0.66) & (sh < 0.7)
        col = np.where(verd[..., None], mix(col, rgb("#4f8a7a"), 0.55), col)
        ridge = (np.abs(u) < 0.08) & (v < 0.5)
        col = np.where(ridge[..., None], np.clip(col * 1.25 + 0.05, 0, 1), col)
        pad = np.pad(inside, 1)
        rimm = inside & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        col = np.where(rimm[..., None], rgb(GOLD), col)
        t = T(ctx, col, np.where(rimm, 0.4, 0.0))
        t[..., 3] = inside * 1.0
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, f"ed6plate{seed}", directional=True)


def _etched_leather():
    def fn(ctx):
        ix, iy = px(ctx)
        n = tex.fbm(ix / 3.0, iy / 3.0, 12)
        t = T(ctx, mix(rgb("#2a1a0e"), rgb("#4e3218"), n[..., None]))
        f1, e = worley(ix, iy, 9, 5)
        tool = e < 0.9
        t[..., :3] = np.where(tool[..., None], t[..., :3] * 0.6, t[..., :3])
        chan = (e < 0.7) & (tex.fbm(ix / 6.0, iy / 6.0, 33) > 0.6)
        t[..., :3] = np.where(chan[..., None], rgb("#ffcf7a"), t[..., :3])
        t[..., 4] = np.where(chan, 0.8, 0.0)
        return tex.grain(ctx, t, 0.05)
    return Mat(fn, "ed6leather")


def _page_mat():
    """Bone-ivory page: sepia skull study of one lineage (variant) and glowing draconic lines."""
    stack = np.array([[[c == "#" for c in row] for row in g] for g in DR], dtype=bool)

    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        ix, iy = px(ctx)
        t = T(ctx, mix(rgb("#f2ead4"), rgb("#d8c9a4"), (np.abs(u) * 0.4 + tex.fbm(ix / 4.0, iy / 4.0, 7) * 0.5)[..., None]))
        k = ctx.variant % 4
        sk = skull_sample(k, u, v, -0.8, 0.8, 0.28)
        pad = np.pad(sk, 1)
        rim = sk & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        t[..., :3] = np.where(rim[..., None], rgb("#6a4a2a"), t[..., :3])
        t[..., :3] = np.where((sk & ~rim)[..., None], mix(t[..., :3], rgb("#b89a6a"), 0.35), t[..., :3])
        ng, gh, gw = stack.shape
        cy = (iy - int(ctx.h * 0.62)) // (gh + 2)
        ly = (iy - int(ctx.h * 0.62)) % (gh + 2)
        cx_ = (ix - 2) // (gw + 1)
        lx = (ix - 2) % (gw + 1)
        gi = (tex._hash(cx_, cy, 5 + ctx.variant) * 997).astype(int) % ng
        ok = (iy >= int(ctx.h * 0.62)) & (cy < 3) & (lx < gw) & (ly < gh) & (ix >= 2) & (ix < ctx.w - 2)
        g = ok & stack[gi, np.clip(ly, 0, gh - 1), np.clip(lx, 0, gw - 1)]
        b = rgb(LINEAGE[k][1])
        t[..., :3] = np.where(g[..., None], b, t[..., :3])
        t[..., 4] = np.where(g, 1.0, 0.0)
        return tex.edge(ctx, t, 0.08)
    return Mat(fn, "ed6page", directional=True)


def _seal_mat():
    return tex.magic_circle(DR, "#ffe2a0", "#ff9a3a", glow=1.0, bands=((0.62, 0.86, 12),), lines=(0.58, 0.9, 0.97),
                            star=4, star_r=(0.15, 0.55), core=0.1, key="ed6seal")


def _gem_mat(k):
    b, m, d = LINEAGE[k]
    off = tex.crystal(d, "#14100c", "#6a5a4a", a=1.0, mode="solid", glow=0.0, facets=2.0)
    on = tex.crystal(b, m, "#ffffff", a=1.0, mode="solid", glow=1.0, facets=2.0)
    return tex.alt(off, **{f"g{j + 1}": (on if j >= k else off) for j in range(4)})


def codex_model():
    m = Model("ed6_codex", density=1.0, bounds=(16, 14, (0, 1.5, 0)), alts=("g1", "g2", "g3", "g4"))
    cx, cy, cz = CX
    root = m.bone("root")
    book = m.bone("book", root, pivot=CX)
    gold = tex.metal(GOLD, "#fff0c0", "#7a5a1e", bands=2.0, glow=0.15)
    leather = tex.trimmed(_etched_leather(), GOLD, 1, 1, glow=0.4)
    inner = tex.magic_circle(DR, "#ffe2a0", "#c9a24a", glow=1.0, bands=((0.72, 0.9, 16),), lines=(0.68, 0.94),
                             star=4, star_r=(0.2, 0.6), fill="#2a1a0c", fill_glow=0.1, key="ed6inner")
    page_edge = tex.banded(tex.vgrad("#efe6cc", "#cdbb92", var=0.03, edge_dark=0.0), "#b8a47a", every=2, horizontal=False)
    # page block
    blk = m.bone("block", book, pivot=CX)
    blk.cube((-14.5, 4.0, -3.4), (30.0, 40.0, 6.8), page_edge, mats={"north": _page_mat()}, variant=1)
    # spine (leather) with gold bands
    spn = m.bone("spine", book, pivot=CX)
    spn.cube((-17.6, 2.6, -5.0), (2.4, 42.8, 10.0), leather)
    for y in (6.0, 24.0, 42.0):
        spn.box((-17.0, y, 0), (3.2, 1.4, 10.6), gold)
    # back cover (static): seal + lineage gems on its outside (+Z)
    cb = m.bone("cover_b", book, pivot=(-16, cy, 4.3))
    cb.cube((-16.0, 2.6, 3.4), (32.6, 42.8, 1.6), leather)
    cb.plane("z", (0.0, cy, 5.05), 22, 22, _seal_mat())
    for (x, y) in ((-14.6, 4.0), (15.2, 4.0), (-14.6, 44.0), (15.2, 44.0)):
        cb.box((x, y, 4.2), (3.6, 3.6, 2.4), gold)
    gems = m.bone("gems", cb, pivot=(0, cy, 5.2))
    for k, (x, y) in enumerate(((-9.0, 45.6), (9.0, 45.6), (-9.0, 2.4), (9.0, 2.4))):
        gems.box((x, y, 5.0), (3.2, 2.6, 1.6), _gem_mat(k), rot=(0, 0, 45))
    # front cover: hinged at the spine, opens to the left
    cf = m.bone("cover_f", book, pivot=(-16, cy, -4.3))
    cf.cube((-16.0, 2.6, -5.0), (32.6, 42.8, 1.6), leather, mats={"south": inner})
    for (x, y) in ((-14.6, 4.0), (15.2, 4.0), (-14.6, 44.0), (15.2, 44.0)):
        cf.box((x, y, -4.2), (3.6, 3.6, 2.4), gold)
    cf.box((16.4, cy, -4.2), (1.6, 10.0, 2.0), gold)                       # clasp tongue
    # three riffling leaves hinged at the spine
    for k in range(3):
        lf = m.bone(f"leaf{k + 1}", book, pivot=(-14.5, cy, -3.5 - 0.05 * k))
        lf.plane("z", (0.25, cy, -3.5 - 0.05 * k), 29.5, 39.0, _page_mat(), variant=k + 1)

    # ---- orbiting cover scales: bone pivot = book centre, plate placed on its orbit at angle 0 (front)
    info = {"plates": [], "verts": []}
    keel = tex.metal(BRONZE_HI, "#fff0c0", BRONZE_LO, bands=1.0, glow=0.1)
    i = 0
    for side, zc in (("f", -5.7), ("b", 5.7)):
        for yi, y in enumerate(SC_ROWS):
            for xi, x in enumerate(SC_COLS):
                tier = i % 2
                R = R_SC[tier]
                hy = (6.0 if tier else -5.0) + (i % 3 - 1) * 1.5
                b = m.bone(f"sc{i + 1}", root, pivot=CX)
                b.plane("z", (cx, cy + hy - 1.0, -R - 0.15 * (3 - yi)), 11.0, 12.5, _scale_plate_mat(i % 3), density=1.5,
                        variant=i % 3)
                b.box((cx, cy + hy + 0.5, -R - 0.5 - 0.15 * (3 - yi)), (1.6, 8.0, 1.0), keel, variant=i % 2)
                a = (i * 15.0 if tier == 0 else i * 15.0 + 7.5) % 360
                rb = 0.0 if side == "f" else 180.0
                qx = x if side == "f" else -x
                bound_rot_pos = (qx, y - cy - hy, zc + (R if side == "f" else -R))
                info["plates"].append(dict(bone=b.name, tier=tier, a=a, rb=rb, pb=bound_rot_pos, bob=(i * 0.37) % 1.0))
                i += 1
    # ---- vertebrae: vertical halo, bone pivot = book centre, vertebra placed at the top of the halo
    bonem = tex.bone_mat(IVORY, "#b8a985", pores=0.12)
    for k, y in enumerate(VT_Y):
        b = m.bone(f"vt{k + 1}", root, pivot=CX)
        top = cy + R_VT
        b.box((0, top, 0), (4.4, 3.6, 5.0), bonem, variant=k % 3)                  # centrum
        b.box((0, top + 3.4, 0), (1.6, 4.2, 2.2), bonem, variant=(k + 1) % 3)       # neural spine
        b.box((0, top + 0.6, 0), (1.4, 1.4, 9.6), bonem, variant=(k + 2) % 3)       # transverse processes
        b.box((0, top + 5.8, 0), (2.4, 1.2, 2.4), tex.glow_flat("#ffe2a0", 0.9, core="#ffffff"))   # ember node
        a = k * 45.0
        # bound: rz = 90 brings the halo top to the spine side (-X); then shift to the spine slot
        pb = (-17.6 + R_VT - 0.5, y - cy, 0.0)
        info["verts"].append(dict(bone=b.name, a=a, pb=pb))
    return m, info


def _ease_var(name):
    return f"v.{name} = v.{name} + (q.property('grimoire:{name}') - v.{name}) * math.min(1.0, q.delta_time * 1.3);"


def codex_anims(info, preview_sep=None, preview_open=None):
    """preview_sep / preview_open: if given, Molang-free constant poses for the previews."""
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    life = Anim("life", loop=True)
    life.pos("book", (0, LIFE(0.8, 3.4), 0))
    life.rot("book", (LIFE(1.5, 5.3), LIFE(4.0, 7.1), LIFE(1.5, 4.4, 0.3)))
    life.scl("gems", LIFE(0.06, 1.1, base=1.0))
    A.append(life)

    # separation + opening, driven by the eased client variables v.sep and v.op
    orb = Anim("orbit", loop=True)
    S_ = "v.sep"
    for p in info["plates"]:
        w = W_SC[p["tier"]]
        if preview_sep is None:
            ry = M(f"{S_}*({p['a']:.1f}+q.life_time*{w})+(1-{S_})*{p['rb']:.1f}")
            bob = f"math.sin(q.life_time*90+{p['bob'] * 360:.0f})*2.0"
            pos = tuple(M(f"(1-{S_})*({c:.2f})" + (f"+{S_}*{bob}" if j == 1 else "")) for j, c in enumerate(p["pb"]))
            orb.rot(p["bone"], (M(f"{S_}*math.sin(q.life_time*70+{p['a']:.0f})*12"), ry, 0))
            orb.pos(p["bone"], pos)
        else:
            s = preview_sep
            orb.rot(p["bone"], (s * 8 * math.sin(math.radians(p["a"] * 3)), s * (p["a"] + 40) + (1 - s) * p["rb"], 0))
            orb.pos(p["bone"], tuple((1 - s) * c for c in p["pb"]))
    for p in info["verts"]:
        if preview_sep is None:
            rz = M(f"{S_}*({p['a']:.1f}+q.life_time*{W_VT})+(1-{S_})*90")
            orb.rot(p["bone"], (0, M(f"{S_}*20"), rz))
            orb.pos(p["bone"], tuple(M(f"(1-{S_})*({c:.2f})") for c in p["pb"]))
        else:
            s = preview_sep
            orb.rot(p["bone"], (0, s * 20, s * (p["a"] + 30) + (1 - s) * 90))
            orb.pos(p["bone"], tuple((1 - s) * c for c in p["pb"]))
    if preview_open is None:
        orb.rot("cover_f", (0, M("v.op*158"), 0))
        orb.rot("root", (M("v.op*24"), 0, 0))
    else:
        orb.rot("cover_f", (0, preview_open * 158, 0))
        orb.rot("root", (preview_open * 24, 0, 0))
    A.append(orb)

    hover = Anim("hover", loop=True)
    A.append(hover)
    rise = Anim("rise", length=2.0, loop="hold")
    rise.scl("root", {0: 0.04, 0.6: 0.4, 1.4: 1.08, 2.0: 1.0})
    rise.pos("root", {0: (0, -30, 0), 1.5: (0, 3, 0), 2.0: (0, 0, 0)})
    rise.rot("book", {0: (0, -240, 0), 1.5: (0, 8, 0), 2.0: (0, 0, 0)})
    A.append(rise)
    beat = Anim("beat", length=0.6, loop="hold")
    beat.scl("book", {0: 1.0, 0.06: 1.07, 0.16: 0.99, 0.26: 1.04, 0.6: 1.0})
    beat.scl("gems", {0: 1.0, 0.06: 1.6, 0.3: 1.0})
    A.append(beat)
    absorb = Anim("absorb", length=1.2, loop=True)
    for k in range(3):
        t0 = 0.1 + k * 0.22
        absorb.rot(f"leaf{k + 1}", {0: (0, 0, 0), t0: (0, 0, 0), t0 + 0.35: (0, 150 - k * 6, 0), 1.0: (0, 152 - k * 6, 0),
                                    1.2: (0, 0, 0)})
    absorb.scl("book", {0: 1.0, 0.1: 1.03, 0.6: 1.0, 1.2: 1.0})
    A.append(absorb)
    vanish = Anim("vanish", length=1.6, loop="hold")
    vanish.scl("root", {0: 1.0, 0.35: 1.1, 1.3: 0.08, 1.6: 0.0})
    vanish.pos("root", {0: (0, 0, 0), 0.4: (0, -2, 0), 1.6: (0, 26, 0)})
    vanish.rot("book", {0: (0, 0, 0), 1.6: (0, 300, 0)})
    A.append(vanish)
    return A


CODEX_STATES = {0: ["hidden"], 1: ["rise"], 2: ["hover"], 3: ["beat"], 4: ["absorb"], 5: ["vanish"]}

# ============================================================================== luminous skeletons
SPIRIT_TINT = ["#ecffd0", "#ffe6b8", "#dcf6ff", "#f6fbff"]


def _stick(bone, p0, p1, w, mat, **kw):
    """Thin box spanning p0 -> p1 (bb coords)."""
    d = np.array(p1, dtype=float) - np.array(p0, dtype=float)
    L = float(np.linalg.norm(d))
    if L < 1e-3:
        return None
    d /= L
    a = math.degrees(math.asin(max(-1.0, min(1.0, d[2]))))
    b = math.degrees(math.atan2(-d[0], d[1]))
    c = tuple((np.array(p0) + np.array(p1)) / 2)
    return bone.box(c, (w, L + w * 0.6, w), mat, rot=(a, 0, b), pivot=c, **kw)


def _poly(bone, pts, w, mat, closed=False):
    for a, b in zip(pts, pts[1:] + ([pts[0]] if closed else [])):
        _stick(bone, a, b, w, mat)


def _lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _spine_pts(pts, n):
    """Resample a polyline to n points (uniform by segment)."""
    out = []
    seg = len(pts) - 1
    for i in range(n):
        f = i / (n - 1) * seg
        j = min(int(f), seg - 1)
        out.append(_lerp(pts[j], pts[j + 1], f - j))
    return out


def spirit_model(k):
    m = Model(f"ed6_spirit_{k}", density=1.0, bounds=(44, 30, (0, 6, 0)))
    tint = SPIRIT_TINT[k]
    line = tex.glow_flat(tint, 1.0, core="#ffffff")
    gold = tex.glow_flat("#ffd98a", 1.0, core="#fff6dc")
    runes = tex.glyph_rows(DR, "#ffe2a0", glow=1.0, color2=LINEAGE[k][0], fill=0.9, key=f"ed6spr{k}")
    root = m.bone("root")
    W = [2.2, 1.9, 1.9, 1.5][k]
    if k == 0:      # sauropod
        spine = [(0, 30, 144), (0, 44, 100), (0, 58, 62), (0, 66, 30), (0, 70, 0), (0, 68, -30), (0, 66, -46), (0, 76, -66),
                 (0, 88, -86), (0, 97, -105), (0, 102, -122)]
        head = (0, 102, -126)
        ribz = [-34, -22, -10, 2, 14, 24]
        rib = lambda z: [(0, 68, z), (22, 58, z), (17, 36, z)]
        legs = [[(22, 60, -30), (24, 30, -30), (24, 4, -30), (24, 2, -38)], [(22, 62, 30), (24, 30, 33), (24, 4, 28), (24, 2, 20)]]
        skull = [(0, 98, -121), (0, 108, -124), (0, 110, -132), (0, 104, -140), (0, 97, -139), (0, 95, -130)]
        eye, eye_r = (0, 104, -128), 2.4
        run = ((0, 82, 40), 150, 10)
    elif k == 1:    # carnotaur
        spine = [(0, 42, 83), (0, 46, 60), (0, 50, 36), (0, 54, 16), (0, 57, 4), (0, 58, -10), (0, 57, -25), (0, 58, -36),
                 (0, 61, -46)]
        head = (0, 60, -50)
        ribz = [-26, -18, -10, -2]
        rib = lambda z: [(0, 57, z), (11, 50, z), (9, 38, z)]
        legs = [[(12.5, 52, 6), (12.5, 32, -4), (12.5, 13, 8), (12.5, 2, -4), (12.5, 1, -12)]]
        skull = [(0, 58, -46), (0, 68, -50), (0, 69, -60), (0, 62, -72), (0, 54, -71), (0, 52, -58)]
        eye, eye_r = (0, 63, -58), 2.2
        run = ((0, 70, 10), 90, 8)
    elif k == 2:    # spinosaur
        spine = [(0, 24, 120), (0, 27, 90), (0, 30, 56), (0, 31, 29), (0, 31, 10), (0, 31, -7), (0, 33, -20), (0, 38, -32),
                 (0, 42, -42)]
        head = (0, 42, -44)
        ribz = [-12, -4, 4, 12]
        rib = lambda z: [(0, 31, z), (10, 24, z), (8, 13, z)]
        legs = [[(9.5, 29, 19), (11, 17, 14), (11, 7, 21), (11, 1.5, 15)], [(10, 28, -15), (11.5, 15, -11), (11.5, 5, -16)]]
        skull = [(0, 45, -42), (0, 44, -56), (0, 39, -74), (0, 37, -88), (0, 33, -86), (0, 34, -66), (0, 36, -44)]
        eye, eye_r = (0, 42, -50), 1.8
        run = ((0, 82, 7), 70, 8)
    else:           # microraptor (wings spread, flight pose)
        spine = [(0, 32, 69), (0, 32, 45), (0, 32, 24), (0, 31, 8), (0, 31, -6), (0, 33, -14), (0, 34, -22), (0, 35, -30)]
        head = (0, 35, -34)
        ribz = [-8, -2, 4]
        rib = lambda z: [(0, 32, z), (5, 28, z), (4, 24, z)]
        legs = [[(5, 29, 9), (7, 26, 19), (8, 24, 32), (8, 23, 41)]]
        skull = [(0, 33, -31), (0, 40, -33), (0, 41, -39), (0, 36, -48), (0, 32, -47), (0, 31, -38)]
        eye, eye_r = (0, 37, -37), 2.0
        run = ((0, 44, 10), 60, 6)

    gs = m.bone("g_spine", root, pivot=spine[len(spine) // 2])
    _poly(gs, spine, W, line)
    for p in _spine_pts(spine, 14)[1:-1]:                    # neural spines
        h = (9 if k == 1 else 6) * W
        _stick(gs, p, (p[0], p[1] + h * (0.6 if k != 2 else 0.4), p[2]), W * 0.7, gold)
    gsk = m.bone("g_skull", root, pivot=head)
    _poly(gsk, skull, W * 1.1, line, closed=True)
    _poly(gsk, [(eye[0], eye[1] + eye_r * math.sin(a), eye[2] + eye_r * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]],
          W * 0.8, gold, closed=True)
    jaw = [skull[-1], (skull[-2][0], skull[-2][1] - 4, skull[-2][2] + 2)]
    _stick(gsk, jaw[0], jaw[1], W * 0.9, line)
    if k == 1:   # horns
        for s in (1, -1):
            _poly(gsk, [(s * 3, 67, -52), (s * 7, 74, -55), (s * 10, 77, -60)], W * 1.1, gold)
    if k == 3:   # crest
        for j in range(4):
            _stick(gsk, (0, 40, -33 + j * 2), (0, 46 + j, -28 + j * 4), W * 0.6, gold)
    gr = m.bone("g_ribs", root, pivot=(0, spine[len(spine) // 2][1], spine[len(spine) // 2][2]))
    for z in ribz:
        for s in (1, -1):
            pts = [(s * x, y, zz) for (x, y, zz) in rib(z)]
            _poly(gr, pts, W * 0.8, line)
    gl = m.bone("g_limbs", root, pivot=(0, 40, 0))
    for leg in legs:
        for s in (1, -1):
            _poly(gl, [(s * x, y, z) for (x, y, z) in leg], W, line)
    gw = m.bone("g_wings", root, pivot=(0, 34, -9))
    if k == 3:
        for s in (1, -1):
            arm = [(s * 5, 34, -9), (s * 20, 34, -9), (s * 39, 34, -8), (s * 54, 34, -6)]
            _poly(gw, arm, W, line)
            for j in range(9):
                f = j / 8
                base = _lerp(arm[1], arm[3], f) if f > 0 else arm[1]
                L = 18 + 12 * f
                _stick(gw, base, (base[0] + s * 6 * f, base[1], base[2] + L), W * 0.55, gold)
            for j in range(4):    # hind-wing feathers
                b0 = (s * 8, 24, 30 + j * 3)
                _stick(gw, b0, (s * (12 + j * 2), 23, 44 + j * 3), W * 0.5, gold)
        for j in range(7):        # tail fan
            a = math.radians(-36 + j * 12)
            _stick(gw, (0, 32, 64), (math.sin(a) * 18, 32, 64 + math.cos(a) * 18), W * 0.55, gold)
    gsail = m.bone("g_sail", root, pivot=(0, 31, 7))
    if k == 2:
        tips = []
        for j in range(12):
            z = -19 + j * 52 / 11
            h = 30 + 40 * math.sin(math.pi * (j + 0.5) / 12)
            _stick(gsail, (0, 32, z), (0, h + 2, z + 2), W * 0.7, line)
            tips.append((0, h + 2, z + 2))
        _poly(gsail, tips, W * 0.6, gold)
    if k == 0:   # glowing tree-glyphs along the back (the forest it carried)
        for j, z in enumerate((-20, 6, 30)):
            _stick(gsail, (0, 70, z), (0, 86, z), W * 0.8, gold)
            for s in (1, -1):
                _stick(gsail, (0, 78, z), (s * 6, 86, z - 3), W * 0.6, gold)
    gru = m.bone("g_runes", root, pivot=run[0])
    (c, L, H) = run
    gru.plane("x", c, L, H, runes)
    gru.plane("x", (c[0], c[1] + H * 0.9, c[2] - L * 0.15), L * 0.7, H * 0.7, runes, variant=1)
    return m


def spirit_anims():
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    form = Anim("form", length=1.2, loop="hold")
    form.scl("g_spine", {0: (1, 0.0, 0.0), 0.35: (1, 1.05, 1.05), 0.5: 1.0})
    form.scl("g_skull", {0: 0.0, 0.3: 0.0, 0.65: 1.25, 0.85: 1.0})
    form.scl("g_ribs", {0: (1, 0, 1), 0.25: (1, 0, 1), 0.6: (1, 1.1, 1), 0.8: 1.0})
    form.scl("g_limbs", {0: (1, 0, 1), 0.35: (1, 0, 1), 0.75: 1.0})
    form.scl("g_wings", {0: (0, 1, 1), 0.3: (0, 1, 1), 0.8: (1.06, 1, 1), 1.0: 1.0})
    form.scl("g_sail", {0: (1, 0, 1), 0.4: (1, 0, 1), 0.9: (1, 1.08, 1), 1.0: 1.0})
    form.scl("g_runes", {0: 0.0, 0.7: 0.0, 1.2: 1.0})
    A.append(form)
    hold = Anim("hold", loop=True)
    hold.scl("root", LIFE(0.015, 0.9, base=1.0))
    hold.pos("g_runes", (0, LIFE(1.5, 2.2), 0))
    hold.pos("g_skull", (0, LIFE(0.8, 3.0, 0.2), 0))
    A.append(hold)
    stream = Anim("stream", length=1.4, loop="hold")
    stream.scl("root", {0: 1.0, 0.25: (1.06, 1.06, 1.06), 0.9: (0.3, 0.45, 0.8), 1.4: 0.0})
    stream.scl("g_ribs", {0: 1.0, 0.5: (0.2, 1, 1)})
    stream.scl("g_limbs", {0: 1.0, 0.6: (1, 0.1, 1)})
    stream.scl("g_wings", {0: 1.0, 0.6: (0.1, 1, 1)})
    stream.pos("g_runes", {0: (0, 0, 0), 1.0: (0, 10, 0)})
    A.append(stream)
    return A


SPIRIT_STATES = {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["stream"]}


# ============================================================================== build
def build(pack):
    cm, info = codex_model()
    ca = codex_anims(info)
    pack.actor("ed6_codex", cm, ca, CODEX_STATES, always=["life", "orbit"], scale=2.4, lifetime=150,
               props={"sep": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "client_sync": True},
                      "open": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "client_sync": True}},
               init=["v.sep = 0.0; v.op = 0.0;"],
               pre_anim=[_ease_var("sep"), _ease_var("open").replace("v.open", "v.op")],
               display="The Great Codex", blend=0.25)
    ems = [emblem_model(k) for k in range(4)]
    ea = emblem_anims()
    pack.actor("ed6_emblem", ems[0], ea, EMBLEM_STATES, always=["turn"], kinds=ems[1:], size_prop=True, lifetime=150,
               display="Dragon Emblem", blend=0.15)
    sps = [spirit_model(k) for k in range(4)]
    sa = spirit_anims()
    pack.actor("ed6_spirit", sps[0], sa, SPIRIT_STATES, kinds=sps[1:], size_prop=True, lifetime=150,
               display="Primordial Inscription", blend=0.15)

    # ---- previews
    by = {a.name: a for a in ca}
    bound = {a.name: a for a in codex_anims(info, 0.0, 0.0)}["orbit"]
    sep = {a.name: a for a in codex_anims(info, 1.0, 0.0)}["orbit"]
    opened = {a.name: a for a in codex_anims(info, 1.0, 1.0)}["orbit"]
    half = {a.name: a for a in codex_anims(info, 0.45, 0.0)}["orbit"]
    pack.preview("ed6_codex", cm, [[(bound, 0), (by["life"], 0.0)], [(half, 0)], [(sep, 0)], [(opened, 0), (by["absorb"], 0.5)]],
                 views=((200, 15), (20, 12), (90, 5)), cell=(360, 360), skin="g4")
    eb = {a.name: a for a in ea}
    import os
    from PIL import Image
    from kit.pack import PREVIEW
    from kit.render import render
    if getattr(pack.preview, "enabled", False):
        out = Image.new("RGBA", (4 * 340, 2 * 340))
        for k in range(4):
            out.paste(render(ems[k], (eb["glow"].pose(0.1)), yaw=0, pitch=88, size=(340, 340)), (340 * k, 0))
            out.paste(render(ems[k], (eb["beat"].pose(0.3)), yaw=25, pitch=22, size=(340, 340)), (340 * k, 340))
        out.save(os.path.join(PREVIEW, "ed6_emblems.png"))
        out = Image.new("RGBA", (4 * 380, 2 * 300))
        for k in range(4):
            out.paste(render(sps[k], None, yaw=-90, pitch=4, size=(380, 300)), (380 * k, 0))
            out.paste(render(sps[k], None, yaw=35, pitch=20, size=(380, 300)), (380 * k, 300))
        out.save(os.path.join(PREVIEW, "ed6_spirits.png"))
    print(f"    ed6_codex {cm.cube_count()}c {len(cm.order)}b tex {cm.tex_size}; emblem {ems[0].cube_count()}c tex {ems[0].tex_size}; "
          f"spirits {[s.cube_count() for s in sps]}c")
