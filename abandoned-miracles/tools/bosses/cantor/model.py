"""
Cantor XIII, The Walking Requiem - geometry and textures.

A cathedral that walks: an open bronze tower on three buttress-legs, a great
inverted bell where a head would be (mouth to the sky, clapper standing out of
it like a spire), an organ facade of pipes across its back, a rose window in
its chest, lancet windows in its flanks, and four small bells hanging from its
eaves. The body is hollow around a glowing wind-chest: it is an instrument, and
every part that sounds is its own bone so it can move when it does.

Phase II removes a piece of the bell's lip (`bell_chunk`), lights the fracture
(`bell_crack_glow`) and lets the two pipe wings unfold.

Geo units: 16 = 1 block. Front is -Z. +X is the creature's LEFT.
"""
from __future__ import annotations

import math

import numpy as np

from kit import paint as P
from kit.geo import Model

IDENT = "geometry.abm.cantor_xiii"

BRONZE = ["#3a2a1c", "#5e4226", "#86602f", "#a98443"]
VERDIGRIS = ["#1f4a44", "#2f6f63", "#4c9482", "#7dbfa6"]
GOLD = ["#6b5220", "#96782d", "#c2a04a", "#e8d07e"]
CHARCOAL = ["#131417", "#1f2227", "#2d3138", "#40454e"]
TIN = ["#5a5648", "#8a8468", "#b5ad88", "#d8d1ac"]
LEAD = "#16161c"
GLASS_BLUE = ["#1c2f78", "#2c4fb8", "#4f7fe0"]
GLASS_PURPLE = ["#3b1c6e", "#6a34b0", "#9a62d8"]
GLASS_CRIMSON = ["#5c1420", "#8e2233", "#b84656"]


def _bronze(patina: float = 0.5, bands: bool = False):
    """Cast bronze going green: verdigris pools in the low, sheltered places."""
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = P.fbm(ctx, 0.16, 5, 3)
        img = P.ramp(np.clip(0.45 + (t - 0.5) * 0.9 + (P.white(ctx) - 0.5) * 0.08, 0, 1), BRONZE)
        n = P.fbm(ctx, 0.09, 17, 3)
        drip = P.noise3(ctx.P * np.array([1.0, 0.18, 1.0], dtype=np.float32), 0.5, 29)
        low = np.clip(1.0 - (ctx.V if ctx.face not in ("up", "down") else 0.5), 0, 1)
        m = np.clip((n * 0.7 + drip * 0.5 - (1.02 - patina) + (1 - low) * 0.18) * 4.0, 0, 1)
        green = P.ramp(np.clip(0.3 + P.fbm(ctx, 0.3, 41, 2) * 0.7, 0, 1), VERDIGRIS)
        img = img * (1 - m[..., None]) + green * m[..., None]
        if bands and ctx.face not in ("up", "down") and ctx.h >= 5:
            for y in (1, ctx.h - 2):
                band = (ctx.Y == y).astype(np.float32)
                img = P.over(img, P.rgba(GOLD[2], 0.85), band)
        img = P.bevel(ctx, img, 0.14, 0.24)
        return P.face_light(ctx, img, 0.05, -0.2)
    return painter


def _gold(ctx: P.FaceCtx) -> np.ndarray:
    t = np.clip(0.6 - (ctx.V - 0.5) * 0.6 + (P.white(ctx) - 0.5) * 0.3, 0, 1)
    img = P.ramp(t, GOLD)
    img = P.over(img, P.rgba("#3d3015", 0.7), (P.white(ctx, 6) < 0.09).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.2, 0.25))


def _charcoal(rivet: bool = True):
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = P.fbm(ctx, 0.22, 61, 2)
        img = P.ramp(np.clip(0.4 + (t - 0.5) * 0.7, 0, 1), CHARCOAL)
        if ctx.w >= 9 and ctx.h >= 9:
            seam = ((ctx.X % 8 == 7) | (ctx.Y % 8 == 7)).astype(np.float32)
            img = P.shade(img, -0.25 * seam)
        if rivet:
            img = P.over(img, P.rgba(BRONZE[3], 0.9), P.rivets(ctx, 4, 1))
        img = P.bevel(ctx, img, 0.12, 0.25)
        return P.face_light(ctx, img, 0.04, -0.2)
    return painter


def _pipe(ctx: P.FaceCtx) -> np.ndarray:
    """Organ pipe metal: a vertical highlight, a dark mouth near the foot, a gilt collar."""
    t = np.clip(0.75 - np.abs(ctx.U - 0.35) * 1.3 + (P.fbm(ctx, 0.3, 71, 2) - 0.5) * 0.3, 0, 1)
    img = P.ramp(t, TIN)
    img = P.over(img, P.rgba(VERDIGRIS[1], 0.55), (P.fbm(ctx, 0.12, 73, 2) > 0.66).astype(np.float32))
    if ctx.face == "north" and ctx.h >= 12 and ctx.w >= 3:
        mouth = ((ctx.Y >= ctx.h - 9) & (ctx.Y <= ctx.h - 7) & (ctx.X >= 1) & (ctx.X < ctx.w - 1)).astype(np.float32)
        img = P.over(img, P.rgba("#0c0c10"), mouth)
        lip = ((ctx.Y == ctx.h - 10) & (ctx.X >= 1) & (ctx.X < ctx.w - 1)).astype(np.float32)
        img = P.over(img, P.rgba(GOLD[3]), lip)
    if ctx.face not in ("up", "down") and ctx.h >= 8:
        img = P.over(img, P.rgba(GOLD[2], 0.9), (ctx.Y == 2).astype(np.float32))
    if ctx.face == "up":
        img = P.over(img, P.rgba("#08080c"), (ctx.edge_dist() >= 1).astype(np.float32))
    return P.face_light(ctx, P.bevel(ctx, img, 0.1, 0.22), 0.0, -0.2)


def _gear(ctx: P.FaceCtx) -> np.ndarray:
    """Joint housing: a toothed rim around a bronze boss."""
    img = _charcoal(False)(ctx)
    if ctx.face in ("north", "south") and min(ctx.w, ctx.h) >= 7:
        d = np.sqrt((ctx.X - (ctx.w - 1) / 2) ** 2 + (ctx.Y - (ctx.h - 1) / 2) ** 2)
        r = min(ctx.w, ctx.h) / 2
        ang = np.arctan2(ctx.Y - (ctx.h - 1) / 2, ctx.X - (ctx.w - 1) / 2)
        teeth = ((d > r - 2.2) & (d <= r) & (np.floor(ang * 8 / math.pi) % 2 == 0)).astype(np.float32)
        img = P.over(img, P.rgba(BRONZE[2]), ((d <= r - 2.2) & (d > 1.5)).astype(np.float32))
        img = P.over(img, P.rgba(BRONZE[3]), teeth)
        img = P.over(img, P.rgba(GOLD[3]), (d <= 1.5).astype(np.float32))
    else:
        tooth = ((ctx.X // 2) % 2 == 0).astype(np.float32) * (ctx.edge_dist() == 0)
        img = P.over(img, P.rgba(BRONZE[3], 0.9), tooth)
    return img


def _bell(inside_top: bool = False):
    """The great bell: darker, smoother bronze with cast bands; the mouth (top face) is a dark well."""
    base = _bronze(0.36)

    def painter(ctx: P.FaceCtx) -> np.ndarray:
        if inside_top and ctx.face == "up":
            d = np.sqrt((ctx.U - 0.5) ** 2 + (ctx.V - 0.5) ** 2) * 2
            return P.ramp(np.clip(1 - d, 0, 1) * 0.5 + (P.white(ctx) - 0.5) * 0.04, ["#07060a", "#151018", "#2a1c14"])
        img = base(ctx)
        if ctx.face not in ("up", "down") and ctx.w >= 12 and ctx.h >= 5:
            ring = (ctx.Y == ctx.h - 2).astype(np.float32)                    # cast moulding wire
            img = P.shade(img, 0.22 * ring - 0.2 * (ctx.Y == ctx.h - 1))
            runes = ((ctx.Y == ctx.h // 2 - 1) & (ctx.X % 4 < 2) & (ctx.X > 1) & (ctx.X < ctx.w - 2)).astype(np.float32)
            img = P.over(img, P.rgba(BRONZE[0], 0.75), runes)
        return img
    return painter


def _lead(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return P.over(img, P.rgba(LEAD), mask.astype(np.float32))


def _rose(alpha: float):
    """Rose window: petals of blue, purple and crimson round a gold eye, held in lead."""
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        cx, cy = (ctx.w - 1) / 2, (ctx.h - 1) / 2
        dx, dy = ctx.X - cx, ctx.Y - cy
        d = np.sqrt(dx * dx + dy * dy)
        r = min(ctx.w, ctx.h) / 2
        ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
        petal = np.floor(ang / 45).astype(int)
        t = np.clip(1 - d / r, 0, 1)
        img = ctx.fill((0, 0, 0, 1))
        for k, pal in enumerate((GLASS_BLUE, GLASS_PURPLE, GLASS_CRIMSON, GLASS_BLUE)):
            m = (petal % 4 == k)
            col = P.ramp(np.clip(0.25 + t * 0.9 + (P.white(ctx, k) - 0.5) * 0.15, 0, 1), pal)
            img[m] = col[m]
        img = P.over(img, P.rgba(GOLD[3]), (d < r * 0.2).astype(np.float32))
        img = _lead(img, (np.abs((ang % 45) - 22.5) > 20.5) & (d >= r * 0.2))
        img = _lead(img, (np.abs(d - r * 0.2) < 0.6) | (np.abs(d - r * 0.62) < 0.55) | (d > r - 1))
        img[..., 3] = np.where(d > r + 0.3, 0.0, alpha + (1 - alpha) * (np.abs(d - r * 0.62) < 0.55))
        img[..., 3] = np.where(_is_lead(img), 1.0, img[..., 3])
        return img
    return painter


def _is_lead(img: np.ndarray) -> np.ndarray:
    return (np.abs(img[..., 0] - 0x16 / 255) < 0.01) & (np.abs(img[..., 2] - 0x1c / 255) < 0.01)


def _lancet(alpha: float, palette):
    """Lancet window: lozenge quarries with a pointed head."""
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = np.clip(0.35 + (1 - ctx.V) * 0.5 + (P.white(ctx) - 0.5) * 0.2, 0, 1)
        img = P.ramp(t, palette)
        loz = ((ctx.X + ctx.Y) % 4 == 0) | ((ctx.X - ctx.Y) % 4 == 0)
        img = _lead(img, loz)
        img = _lead(img, ctx.edge_dist() == 0)
        img[..., 3] = np.where(_is_lead(img), 1.0, alpha)
        if ctx.w >= 4:
            point = (ctx.Y < 3) & (np.abs(ctx.X - (ctx.w - 1) / 2) > ctx.Y * 1.2 + 0.6)
            img[point] = (0, 0, 0, 0)
        return img
    return painter


def _dark_glass(ctx: P.FaceCtx) -> np.ndarray:
    """What the windows look like unlit (shown behind the glowing panes, and alone when silenced)."""
    t = P.fbm(ctx, 0.3, 83, 2)
    img = P.ramp(np.clip(0.3 + t * 0.5, 0, 1), ["#0b0d18", "#141a30", "#1d2748"])
    img = _lead(img, ((ctx.X + ctx.Y) % 4 == 0) | (ctx.edge_dist() == 0))
    return img


def _mp(side: int, p):
    return (p[0] * side, p[1], p[2])


def _mirror(side: int, origin, size):
    if side > 0:
        return origin, size
    return (-(origin[0] + size[0]), origin[1], origin[2]), size


def _mrot(side: int, rot):
    return rot if side > 0 else (rot[0], -rot[1], -rot[2])


# Tripod: azimuth from the front towards the creature's left. One leg leads, two brace behind.
LEG_AZIMUTH = {1: 0.0, 2: 125.0, 3: 235.0}
THIGH, SHIN = 34.0, 61.0
THIGH_ELEV, SHIN_ELEV = 25.0, -82.0


def build() -> Model:
    m = Model(IDENT, density=1.0, bounds=(11.0, 12.0, 4.5))
    m.materials.update({
        "bronze": _bronze(0.42),
        "bronze_band": _bronze(0.45, bands=True),
        "bronze_old": _bronze(0.72),
        "gold": _gold,
        "charcoal": _charcoal(True),
        "charcoal_plain": _charcoal(False),
        "pipe": _pipe,
        "gear": _gear,
        "bell": _bell(False),
        "bell_mouth": _bell(True),
        "rose": _rose(0.22),
        "lancet_b": _lancet(0.24, GLASS_BLUE),
        "lancet_p": _lancet(0.24, GLASS_PURPLE),
        "lancet_c": _lancet(0.24, GLASS_CRIMSON),
        "dark_glass": _dark_glass,
        "core": P.glow("#fff3c4", "#d9902a", 0.14),
        "crack": P.glow("#fff0c8", "#ff7a2a", 0.1),
        "ember": P.glow("#ffe9b0", "#c9641c", 0.2),
    })

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 60, 0), "root")

    # ------------------------------------------------------------------ the tower: a hollow frame round the wind-chest
    body.box((-8, 44, -8), (16, 8, 16), "gear")                       # hub the legs are geared to
    body.box((-13, 52, -13), (26, 6, 26), "charcoal")
    body.box((-16, 58, -16), (32, 8, 32), "bronze_band")              # sound-board drum
    body.box((-17, 65, -17), (34, 2, 34), "gold")
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box((sx * 13 - 2.5, 67, sz * 13 - 2.5), (5, 37, 5), "bronze")       # corner piers
            body.box((sx * 13 - 3.5, 67, sz * 13 - 3.5), (7, 3, 7), "gold")          # pier bases
            body.box((sx * 13 - 3.5, 97, sz * 13 - 3.5), (7, 3, 7), "gold")          # capitals
    for sz in (-1, 1):                                                 # pointed gables front and back
        z = sz * 15.5 - 2.5
        body.box((-13, 100, z), (26, 4, 5), "bronze_band")
        body.box((-8, 104, z + 0.5), (16, 3, 4), "bronze")
    for sx in (-1, 1):
        x = sx * 15.5 - 2.5
        body.box((x, 100, -13), (5, 4, 26), "bronze_band")
    body.box((-17, 104, -17), (34, 5, 34), "bronze_old")              # roof slab
    body.box((-18, 108, -18), (36, 2, 36), "gold")                    # cornice
    body.box((-11, 110, -11), (22, 4, 22), "charcoal")                # bell seat
    body.box((-3, 66, -3), (6, 38, 6), "charcoal_plain")              # the wind-chest column
    for y in (72, 82, 92):
        body.box((-5, y, -5), (10, 2, 10), "gold")                    # chest collars
    body.locator("chest", (0, 82, -17))
    body.locator("base", (0, 46, 0))

    core = m.bone("core_glow", (0, 82, 0), "body")
    core.box((-4.5, 74.5, -4.5), (9, 7, 9), "core")
    core.box((-4.5, 84.5, -4.5), (9, 7, 9), "core")

    # reeds: a rank of brass tongues under the rose window
    reeds = m.bone("reeds", (0, 66, -17), "body")
    for i in range(7):
        x = -9 + i * 3
        reeds.box((x - 0.7, 66, -18.2), (1.4, 5 + (i % 3) * 1.5, 1.4), "gold", uv_key=f"reed{i % 3}")

    # ------------------------------------------------------------------ windows (hinged, so they can open)
    pf = m.bone("panel_f", (-9, 82, -16), "body")
    pf.box((-9.5, 70, -17), (19, 24, 1.6), "charcoal")
    pf.box((-8, 71.5, -17.4), (16, 21, 0.6), "dark_glass")
    pfg = m.bone("panel_f_glow", (0, 82, -17.4), "panel_f")
    pfg.box((-8, 72.5, -17.9), (16, 16, 0.5), "rose", density=2, faces=("north",))
    for side, tag, mat in ((1, "l", "lancet_b"), (-1, "r", "lancet_c")):
        pl = m.bone(f"panel_{tag}", _mp(side, (16, 84, -9)), "body")
        o, s = _mirror(side, (15.2, 69, -9), (1.6, 30, 18))
        pl.box(o, s, "charcoal")
        o, s = _mirror(side, (16.6, 70.5, -7.5), (0.6, 27, 15))
        pl.box(o, s, "dark_glass")
        pg = m.bone(f"panel_{tag}_glow", _mp(side, (17, 84, 0)), f"panel_{tag}")
        for k, z in enumerate((-7, -2, 3)):
            o, s = _mirror(side, (17.25, 71, z), (0.5, 26, 4))
            pg.box(o, s, mat if k != 1 else "lancet_p", faces=("west" if side > 0 else "east",), uv_key=f"lan{k}{tag}")

    # shutters: louvres in the back wall either side of the great pipes
    for side, tag in ((1, "l"), (-1, "r")):
        sh = m.bone(f"shutter_{tag}", _mp(side, (9, 96, 16)), "body")
        for k in range(4):
            o, s = _mirror(side, (5, 70 + k * 6.5, 15.2), (8, 4.5, 1.4))
            sh.box(o, s, "bronze_old", pivot=_mp(side, (9, 72.2 + k * 6.5, 16)), rotation=(-24, 0, 0), uv_key="louvre")

    # ------------------------------------------------------------------ the organ: three great pipes and two wings of four
    def pipe(bone, x, z, base_y, height, w):
        bone.box((x - w / 2, base_y, z - w / 2), (w, height, w), "pipe")
        bone.box((x - w / 2 + 1, base_y - 4, z - w / 2 + 1), (w - 2, 4, w - 2), "charcoal_plain")
        bone.box((x - w / 2 - 0.5, base_y + height - 6, z - w / 2 - 0.5), (w + 1, 2, w + 1), "gold")

    for i, (x, hgt, w) in enumerate(((0, 72, 6), (-7, 60, 5), (7, 60, 5))):
        pc = m.bone(f"pipe_c{i + 1}", (x, 66, 20), "body")
        pipe(pc, x, 20, 66, hgt, w)
        if i == 0:
            pc.locator("pipe_top", (0, 138, 20))
    for side, tag in ((1, "l"), (-1, "r")):
        wing = m.bone(f"wing_{tag}", _mp(side, (11, 68, 19)), "body")
        o, s = _mirror(side, (10, 64, 17), (20, 4, 5))
        wing.box(o, s, "bronze_band")                                  # wing rail the pipes stand on
        for k, (x, hgt) in enumerate(((13, 50), (18, 42), (23, 34), (28, 26)), 1):
            pb = m.bone(f"pipe_{tag}{k}", _mp(side, (x, 68, 19.5)), f"wing_{tag}")
            pipe(pb, x * side, 19.5, 68, hgt, 4)
        wing.locator(f"wing_{tag}", _mp(side, (22, 90, 20)))

    # ------------------------------------------------------------------ the great bell: inverted, mouth to the sky
    bell = m.bone("bell", (0, 114, 0), "body")
    bell.box((-5, 113, -5), (10, 5, 10), "gold")                       # headstock
    bell.box((-8, 118, -8), (16, 6, 16), "bell")
    bell.box((-11.5, 124, -11.5), (23, 7, 23), "bell")
    # the two widest courses are cast in pieces so that one piece can be lost
    bell.box((-15.5, 131, -15.5), (22, 7, 31), "bell")
    bell.box((6.5, 131, -4), (9, 7, 19.5), "bell")
    bell.box((-19.5, 138, -19.5), (27, 6, 39), "bell_mouth")
    bell.box((7.5, 138, -6), (12, 6, 25.5), "bell_mouth")
    # gilt lip: four strips round the dark mouth (the front-left corner belongs to the piece that breaks off)
    bell.box((-20.5, 144, 18.5), (41, 2, 2), "gold")
    bell.box((-20.5, 144, -18.5), (2, 2, 37), "gold")
    bell.box((18.5, 144, -7), (2, 2, 25.5), "gold")
    bell.box((-20.5, 144, -20.5), (28, 2, 2), "gold")
    bell.locator("bell", (0, 146, 0))
    chunk = m.bone("bell_chunk", (13, 136, -13), "bell")
    chunk.box((6.5, 131, -15.5), (9, 7, 11.5), "bell")
    chunk.box((7.5, 138, -19.5), (12, 6, 13.5), "bell_mouth")
    chunk.box((7.5, 144, -20.5), (13, 2, 2), "gold")
    chunk.box((18.5, 144, -18.5), (2, 2, 11.5), "gold")
    crack = m.bone("bell_crack_glow", (9, 134, -9), "bell")
    crack.box((6.2, 124.5, -4.6), (0.5, 20, 0.8), "crack")
    crack.box((6.6, 131.5, -4.4), (9, 0.8, 0.5), "crack")
    crack.box((-2, 126, -11.8), (0.8, 13, 0.5), "crack")
    crack.box((-8, 134, -15.8), (12, 0.8, 0.5), "crack")
    crack.box((7.5, 144.2, -7.3), (12.5, 2.2, 0.5), "ember")
    clap = m.bone("clapper", (0, 122, 0), "bell")
    clap.box((-1.3, 122, -1.3), (2.6, 30, 2.6), "charcoal_plain")
    clap.box((-4, 150, -4), (8, 6, 8), "gold")
    clap.box((-1.5, 156, -1.5), (3, 4, 3), "gold")
    clap.locator("clapper", (0, 160, 0))

    # pinnacles on the roof corners and a gable over the rose window
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box((sx * 15 - 1.5, 110, sz * 15 - 1.5), (3, 9, 3), "bronze", uv_key="pinnacle")
            body.box((sx * 15 - 1, 119, sz * 15 - 1), (2, 3, 2), "gold", uv_key="pinnacle_tip")
    for k, (w, y) in enumerate(((22, 96), (15, 99), (8, 102))):
        body.box((-w / 2, y, -19), (w, 3, 2.5), "bronze_old" if k else "bronze_band")
    body.box((-1.5, 105, -19), (3, 5, 2.5), "gold")

    # ------------------------------------------------------------------ four small bells swung out on brackets from the eaves
    for i, (sx, sz) in enumerate(((1, -1), (-1, -1), (1, 1), (-1, 1)), 1):
        cx, cz = sx * 22, sz * 22
        body.box((min(sx * 16, cx) , 105, cz - 1 if sz < 0 else cz - 1), (6, 2, 2), "charcoal_plain", uv_key="bracket_x")
        body.box((cx - 1, 105, min(sz * 16, cz)), (2, 2, 6), "charcoal_plain", uv_key="bracket_z")
        sb = m.bone(f"bell_s{i}", (cx, 105, cz), "body")
        sb.box((cx - 0.6, 96, cz - 0.6), (1.2, 9, 1.2), "charcoal_plain", uv_key="rope")
        sb.box((cx - 2.5, 93, cz - 2.5), (5, 3, 5), "bell", uv_key="sb_a")
        sb.box((cx - 4, 88, cz - 4), (8, 5, 8), "bell", uv_key="sb_b")
        sb.box((cx - 4.5, 86.6, cz - 4.5), (9, 1.4, 9), "gold", uv_key="sb_c")
        sb.box((cx - 1, 84.5, cz - 1), (2, 2.5, 2), "charcoal_plain", uv_key="sb_d")
        sb.locator(f"bell_s{i}", (cx, 86, cz))

    # ------------------------------------------------------------------ three buttress-legs: hip yaw -> thigh -> shin -> foot
    for n, az in LEG_AZIMUTH.items():
        hip = m.bone(f"leg_{n}", (0, 52, 0), "body", (0, 90 - az, 0))
        hip.box((6, 46, -5), (8, 12, 10), "gear", uv_key="hip")
        th = m.bone(f"leg_{n}_a", (10, 52, 0), f"leg_{n}", (0, 0, -THIGH_ELEV))
        th.box((10, 47.5, -4.5), (THIGH, 9, 9), "bronze_band", uv_key="thigh")
        th.box((14, 56.5, -1.5), (24, 2.2, 3), "charcoal_plain", uv_key="piston_a")       # piston along the thigh
        th.box((16, 55.5, -2.5), (4, 4, 5), "gold", uv_key="piston_cap")
        sh = m.bone(f"leg_{n}_b", (10 + THIGH, 52, 0), f"leg_{n}_a", (0, 0, THIGH_ELEV - SHIN_ELEV))
        sh.box((10 + THIGH - 6, 45.5, -6.5), (12, 13, 13), "gear", uv_key="knee")
        sh.box((10 + THIGH, 48, -4), (SHIN, 8, 8), "charcoal", uv_key="shin")
        sh.box((10 + THIGH + 8, 56, -1.5), (30, 5, 3), "bronze", uv_key="fin_a")           # buttress fin
        sh.box((10 + THIGH + 8, 61, -1.5), (16, 3, 3), "bronze", uv_key="fin_b")
        sh.box((10 + THIGH + SHIN - 12, 47, -5), (4, 10, 10), "gold", uv_key="anklet")
        ft = m.bone(f"leg_{n}_c", (10 + THIGH + SHIN, 52, 0), f"leg_{n}_b", (0, 0, SHIN_ELEV))
        x0 = 10 + THIGH + SHIN
        ft.box((x0 - 8, 46, -8), (16, 6, 16), "bronze_old", uv_key="foot_a")               # pier-base foot
        ft.box((x0 - 6, 52, -6), (12, 3, 12), "gold", uv_key="foot_b")
        ft.locator(f"foot_{n}", (x0, 46, 0))
    return m


def build_bell() -> Model:
    """A detached secondary bell (Twin Resonance): it stands on three stub legs of its own."""
    m = Model("geometry.abm.cantor_bell", density=1.0, bounds=(3.0, 3.5, 1.5))
    m.materials.update({"bell": _bell(False), "bell_mouth": _bell(True), "gold": _gold, "charcoal": _charcoal(False),
                        "core": P.glow("#fff3c4", "#d9902a", 0.14)})
    root = m.bone("root", (0, 0, 0))
    for k, az in enumerate((0, 120, 240)):
        a = math.radians(az)
        root.box((-1, 0, -1), (2, 13, 2), "charcoal", pivot=(0, 12, 0), rotation=(26 * math.cos(a), 0, 26 * math.sin(a)),
                 uv_key="stand")
    root.box((-2.5, 12, -2.5), (5, 2, 5), "gold")
    bell = m.bone("bell", (0, 14, 0), "root")
    bell.box((-3, 14, -3), (6, 4, 6), "bell")
    bell.box((-4.5, 18, -4.5), (9, 5, 9), "bell")
    bell.box((-6, 23, -6), (12, 5, 12), "bell_mouth")
    bell.box((-6.5, 28, -6.5), (13, 1.5, 13), "gold")
    glow = m.bone("bell_glow", (0, 29, 0), "bell")
    glow.box((-4.5, 29.6, -4.5), (9, 0.5, 9), "core")
    clap = m.bone("clapper", (0, 18, 0), "bell")
    clap.box((-0.6, 18, -0.6), (1.2, 14, 1.2), "charcoal")
    clap.box((-1.5, 31, -1.5), (3, 3, 3), "gold")
    bell.locator("ring", (0, 30, 0))
    return m
