"""
Vesperra, The Ivory Succession - geometry and textures.

Silhouette: a crowned porcelain mask on a slender neck, a bell-shaped dress of
overlapping ivory plates, six long chitin legs that emerge from under the hem
and arch above it, two folded bone-needle limbs, and a long plated abdomen
trailing behind like a train. Under the dress sits the organism the dress was
built around: dark chitin, burgundy tissue and pale pupal segments.

The porcelain shell is four hinged sections - front apron, back mantle, left
and right exterior shells - so Phase II can unfold them. The left and right
exterior shells and the crown/face shield are the three breakable armour
regions; each has an intact, a cracked and a destroyed look.

Geo units: 16 = 1 block. Front is -Z. +X is the creature's LEFT.
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from kit import paint as P
from kit.geo import Model

IDENT = "geometry.abm.vesperra"

# palette -------------------------------------------------------------------
IVORY = ["#b7a585", "#d6c8a8", "#ebe1c8", "#f6efdc"]
IVORY_WORN = ["#9d8b6c", "#c2b291", "#ddd0b2", "#ece2c9"]
BONE = ["#a89878", "#cdbf9f", "#e4d9bd", "#f0e8d2"]
CHITIN = ["#140c10", "#22141a", "#341a22", "#4a2029"]
TISSUE = ["#3a0d16", "#5c1522", "#7d1f2e", "#a2354a"]
PUPA = ["#8f7c62", "#b7a383", "#d2c09f", "#e6d8b9"]
GOLD = ["#6f5521", "#9a7a30", "#c2a04a", "#e6cc7a"]
CRACK = "#5a4a38"
GOLD_LINE = "#b08d3c"


def _porcelain(worn: bool = False, gold_rim: bool = False, cracks: float = 0.5, filigree: bool = False):
    """Glazed ivory: soft mottling, vertical glaze streaks, craquelure, optional gilt rim / filigree."""
    pal = IVORY_WORN if worn else IVORY

    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = P.fbm(ctx, 0.11, 11, 3)
        streak = P.noise3(ctx.P * np.array([1.0, 0.12, 1.0], dtype=np.float32), 0.55, 23)
        t = np.clip(0.52 + (t - 0.5) * 0.9 + (streak - 0.5) * 0.28 + (P.white(ctx) - 0.5) * 0.06, 0, 1)
        img = P.ramp(t, pal)
        if cracks:
            img = P.over(img, P.rgba(CRACK, 0.75), P.crack_mask(ctx, cracks * ctx.w * ctx.h / 180.0, 1, 0.5))
        img = P.grime(ctx, img, 30, 70, 0.14)
        img = P.bevel(ctx, img, 0.16, 0.2)
        if filigree and ctx.face in ("north", "south", "east", "west") and ctx.w >= 7 and ctx.h >= 9:
            cxm = (ctx.w - 1) / 2
            d = np.abs(ctx.X - cxm)
            y = ctx.Y - ctx.h * 0.42
            lozenge = (np.abs(d + np.abs(y) * 0.8 - min(ctx.w, ctx.h) * 0.24) < 0.6)
            stem = (d < 0.6) & (y > min(ctx.w, ctx.h) * 0.3) & (ctx.Y < ctx.h - 2)
            img = P.over(img, P.rgba(GOLD_LINE, 0.9), (lozenge | stem).astype(np.float32))
        if gold_rim and ctx.face not in ("up", "down") and ctx.h >= 4:
            rim = (ctx.Y >= ctx.h - 2).astype(np.float32)
            g = P.ramp(np.clip(0.35 + P.white(ctx, 5) * 0.5 - (ctx.Y == ctx.h - 1) * 0.3, 0, 1), GOLD)
            img = img * (1 - rim[..., None]) + g * rim[..., None]
        return P.face_light(ctx, img)
    return painter


def _cracked_overlay(ctx: P.FaceCtx) -> np.ndarray:
    """Transparent sheet carrying only heavy fractures and exposed dark fissures (armour state 1)."""
    img = ctx.fill((0, 0, 0, 0))
    m = P.crack_mask(ctx, 2.2 * ctx.w * ctx.h / 100.0 + 1.5, 7, 1.0)
    wide = np.zeros_like(m)
    wide[:, 1:] = np.maximum(wide[:, 1:], m[:, :-1])
    hole = (m > 0) & (P.white(ctx, 9) < 0.35)
    img = P.over(img, P.rgba("#3d2c22"), wide * 0.0 + m)
    img = P.over(img, P.rgba(TISSUE[1]), hole.astype(np.float32))
    img[..., 3] = np.where((m > 0) | hole, 1.0, 0.0)
    return img


def _chitin(ridged: bool = True):
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = P.fbm(ctx, 0.2, 31, 2)
        t = 0.3 + (t - 0.5) * 0.7
        if ridged:
            t = t + 0.22 * P.stripes(ctx, 4.0, 1.0, "y" if ctx.face in ("north", "south", "east", "west") else "x")
        sheen = np.clip(1 - np.abs(ctx.U - 0.3) * 3.2, 0, 1) * 0.35     # wet highlight band
        img = P.ramp(np.clip(t + sheen, 0, 1), CHITIN)
        img = P.bevel(ctx, img, 0.18, 0.25)
        return P.face_light(ctx, img, 0.05, -0.2)
    return painter


def _tissue(ctx: P.FaceCtx) -> np.ndarray:
    t = P.fbm(ctx, 0.3, 41, 3)
    vein = np.abs(P.noise3(ctx.P, 0.42, 43) - 0.5) < 0.045
    img = P.ramp(np.clip(0.45 + (t - 0.5) * 1.1, 0, 1), TISSUE)
    img = P.over(img, P.rgba(TISSUE[0]), vein.astype(np.float32))
    img = P.over(img, P.rgba("#c9566c", 0.8), (P.white(ctx, 2) < 0.035).astype(np.float32))   # wet specks
    return P.face_light(ctx, P.outline(ctx, img, 0.25), 0.0, -0.2)


def _bone():
    def painter(ctx: P.FaceCtx) -> np.ndarray:
        t = P.fbm(ctx, 0.25, 51, 2)
        img = P.ramp(np.clip(0.55 + (t - 0.5) * 0.8, 0, 1), BONE)
        img = P.over(img, P.rgba(BONE[0]), (P.white(ctx, 4) < 0.07).astype(np.float32))       # pores
        img = P.bevel(ctx, img, 0.14, 0.22)
        return P.face_light(ctx, img)
    return painter


def _needle(ctx: P.FaceCtx) -> np.ndarray:
    """Bone needle: pale shaft, a blood-dark groove, stained towards the point."""
    t = P.fbm(ctx, 0.3, 61, 2)
    img = P.ramp(np.clip(0.6 + (t - 0.5) * 0.6, 0, 1), BONE)
    if ctx.face in ("east", "west", "north", "south") and ctx.w >= 2:
        groove = (ctx.X == ctx.w // 2).astype(np.float32)
        img = P.over(img, P.rgba(TISSUE[1], 0.85), groove)
    return P.face_light(ctx, P.bevel(ctx, img, 0.12, 0.2))


def _pupa(ctx: P.FaceCtx) -> np.ndarray:
    """Waxy larval segments: horizontal bands with tissue seams."""
    t = P.fbm(ctx, 0.2, 71, 2)
    img = P.ramp(np.clip(0.5 + (t - 0.5) * 0.7, 0, 1), PUPA)
    seam = P.stripes(ctx, 5.0, 1.0, "y")
    img = P.over(img, P.rgba(TISSUE[1], 0.9), seam)
    img = P.shade(img, -0.12 * P.stripes(ctx, 5.0, 1.0, "y", 1.0))
    return P.face_light(ctx, P.bevel(ctx, img, 0.1, 0.2), 0.0, -0.2)


def _gold(ctx: P.FaceCtx) -> np.ndarray:
    t = np.clip(0.55 - (ctx.V - 0.5) * 0.7 + (P.white(ctx) - 0.5) * 0.35, 0, 1)
    img = P.ramp(t, GOLD)
    img = P.over(img, P.rgba("#3d3015", 0.7), (P.white(ctx, 6) < 0.1).astype(np.float32))      # tarnish
    return P.bevel(ctx, img, 0.2, 0.25)


def _mask_face(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """Decal for the front of the porcelain mask: serene eye slits, a seam, a fracture from the brow."""
    if ctx.face != "north":
        return img
    w, h = ctx.w, ctx.h
    out = img.copy()
    ey = int(h * 0.42)
    for sx in (int(w * 0.22), int(w * 0.62)):
        ex = np.zeros((h, w), dtype=np.float32)
        ex[ey, sx:sx + max(2, w // 5)] = 1
        ex[ey + 1, sx + 1:sx + max(2, w // 5)] = 0.8
        out = P.over(out, P.rgba("#1a0d10"), ex)
        lid = np.zeros((h, w), dtype=np.float32)
        lid[ey - 1, sx:sx + max(2, w // 5)] = 1
        out = P.over(out, P.rgba(GOLD_LINE, 0.8), lid)
    seam = ((ctx.X == w // 2) & (ctx.Y > int(h * 0.62))).astype(np.float32)
    out = P.over(out, P.rgba(CRACK, 0.7), seam)
    lips = np.zeros((h, w), dtype=np.float32)
    lips[int(h * 0.78), w // 2 - 1:w // 2 + 2] = 1
    out = P.over(out, P.rgba(TISSUE[2], 0.9), lips)
    tear = ((ctx.X == int(w * 0.72)) & (ctx.Y > ey + 1) & (ctx.Y < int(h * 0.75))).astype(np.float32)
    out = P.over(out, P.rgba(CRACK, 0.85), tear)
    return out


def _true_face(ctx: P.FaceCtx, img: np.ndarray) -> np.ndarray:
    """What the mask hid: sockets and a lipless seam."""
    if ctx.face != "north":
        return img
    w, h = ctx.w, ctx.h
    out = img.copy()
    ey = int(h * 0.38)
    for sx in (int(w * 0.15), int(w * 0.6)):
        sock = np.zeros((h, w), dtype=np.float32)
        sock[ey:ey + 3, sx:sx + 2] = 1
        out = P.over(out, P.rgba("#08040a"), sock)
        glint = np.zeros((h, w), dtype=np.float32)
        glint[ey + 1, sx] = 1
        out = P.over(out, P.rgba("#ff5a4a"), glint)
    mouth = np.zeros((h, w), dtype=np.float32)
    mouth[int(h * 0.72), 1:w - 1] = 1
    mouth[int(h * 0.72) + 1, 2:w - 2:2] = 1
    out = P.over(out, P.rgba("#12070b"), mouth)
    return out


def _mirror(side: int, origin, size):
    """Mirror a box about X for the right-hand side (side = -1)."""
    if side > 0:
        return origin, size
    return (-(origin[0] + size[0]), origin[1], origin[2]), size


def _mrot(side: int, rot):
    return rot if side > 0 else (rot[0], -rot[1], -rot[2])


def _mp(side: int, p):
    return (p[0] * side, p[1], p[2])


def _plate(bone, phi: float, radius: float, top_y: float, w: float, h: float, tilt: float, mat,
           thick: float = 1.5, **kw):
    """A dress plate hanging from a hinge on a circle around the body.
    phi: azimuth in degrees, 0 = front, 90 = creature's left, 180 = back."""
    a = math.radians(phi)
    hx, hz = radius * math.sin(a), -radius * math.cos(a)
    return bone.box((hx - w / 2, top_y - h, hz - thick / 2), (w, h, thick), mat,
                    pivot=(hx, top_y, hz), rotation=(-tilt, -phi, 0), **kw)


def build() -> Model:
    m = Model(IDENT, density=1.0, bounds=(9.0, 9.0, 3.5))
    m.materials.update({
        "porcelain": _porcelain(cracks=0.45),
        "porcelain_rim": _porcelain(gold_rim=True, cracks=0.4),
        "porcelain_fil": _porcelain(gold_rim=True, cracks=0.35, filigree=True),
        "porcelain_worn": _porcelain(worn=True, cracks=0.9),
        "crack": _cracked_overlay,
        "chitin": _chitin(True),
        "chitin_smooth": _chitin(False),
        "tissue": _tissue,
        "bone": _bone(),
        "needle": _needle,
        "pupa": _pupa,
        "gold": _gold,
        "eye": P.glow("#ffd9c8", "#c2202c", 0.12),
        "core": P.glow("#ffb69a", "#7d1f2e", 0.2),
    })

    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 58, 0), "root")

    # ------------------------------------------------------------------ inner organism
    thorax = m.bone("thorax", (0, 60, 0), "body")
    thorax.box((-6, 46, -6), (12, 12, 13), "chitin")                    # pelvis block (leg sockets)
    thorax.box((-5, 58, -5), (10, 12, 10), "pupa")                      # larval midsection
    thorax.box((-6.5, 70, -6), (13, 11, 11), "chitin")                  # upper chest
    for i, y in enumerate((59, 63, 67)):                                # exposed ribs over the pupa
        thorax.box((-6, y, -6), (12, 1.5, 1), "bone")
        thorax.box((-6.5, y, -5), (1, 1.5, 9), "bone")
        thorax.box((5.5, y, -5), (1, 1.5, 9), "bone")
    thorax.box((-3.5, 60, -5.6), (7, 9, 1), "tissue")                   # the cavity the core sits in
    thorax.box((-8.5, 76, -4), (17, 5, 8), "chitin_smooth")             # shoulder yoke
    thorax.locator("core", (0, 64, -7))
    core = m.bone("core_glow", (0, 64, -5), "thorax")
    core.box((-2, 61.5, -6.4), (4, 5, 1.2), "core")

    # ------------------------------------------------------------------ neck and head
    neck = m.bone("neck", (0, 81, -1), "thorax")
    neck.box((-2.5, 80, -3), (5, 9, 5), "chitin")
    neck.box((-3.5, 83, -3.5), (7, 1.5, 6), "bone")
    neck.box((-3, 86.5, -3.2), (6, 1.5, 5.4), "bone")
    head = m.bone("head", (0, 89, -1), "neck")
    head.box((-4, 89, -6), (8, 12, 9), "chitin_smooth", decal={"north": _true_face})     # the true face
    head.box((-3, 87, -5), (6, 3, 5), "tissue")                                           # throat
    for side in (1, -1):
        o, s = _mirror(side, (2.5, 86, -6.5), (1.5, 4, 1.5))
        head.box(o, s, "bone", pivot=_mp(side, (3.2, 90, -6)), rotation=_mrot(side, (18, 0, -14)))   # mandibles
    eyes = m.bone("eyes_glow", (0, 95, -6), "head")
    eyes.box((-3.1, 95.6, -6.25), (1.2, 1.2, 0.5), "eye")
    eyes.box((1.9, 95.6, -6.25), (1.2, 1.2, 0.5), "eye")
    head.locator("mouth", (0, 90, -7))

    # integrated skeletal crown: grows out of the skull, always present
    crown = m.bone("crown", (0, 100, -1), "head")
    crown.box((-4.5, 100, -6.5), (9, 2, 10), "bone")                                      # brow band
    spire = [(0, 14, 0, 0), (-3, 10, 10, 0), (3, 10, -10, 0), (-4.2, 7, 20, 4), (4.2, 7, -20, 4)]
    for i, (x, hgt, lean, back) in enumerate(spire):
        crown.box((x - 0.9, 101.5, -1.5 + back * 0.4), (1.8, hgt, 1.8), "bone",
                  pivot=(x, 101.5, -0.6), rotation=(-6, 0, lean))
    for side in (1, -1):                                                                   # swept-back horns
        o, s = _mirror(side, (3.6, 99, 0), (1.6, 1.6, 9))
        crown.box(o, s, "bone", pivot=_mp(side, (4.4, 100, 0)), rotation=_mrot(side, (-28, -14, 0)))
    crown.box((-1, 102, 2.5), (2, 9, 1.5), "bone", pivot=(0, 102, 3), rotation=(-20, 0, 0))   # rear spine
    crown.locator("crown", (0, 114, -1))

    # armour region C: the porcelain mask and frontal crest (the face the court was meant to see)
    sc = m.bone("shield_c", (0, 96, -6), "head")
    sc.box((-4.5, 88.5, -7.2), (9, 12.5, 1.6), "porcelain", decal={"north": _mask_face}, density=1)
    sc.box((-5, 90, -6.2), (1.2, 9, 3.5), "porcelain")                                    # cheek guards
    sc.box((3.8, 90, -6.2), (1.2, 9, 3.5), "porcelain")
    sc.box((-5.5, 100.5, -7.8), (11, 3, 2.2), "gold")                                     # diadem band
    sc.box((-1.6, 103, -7.6), (3.2, 9, 1.4), "porcelain_fil")                             # crest blade
    sc.box((-4.6, 103, -7.4), (2.2, 5.5, 1.2), "porcelain_rim", pivot=(-3.5, 103, -7), rotation=(0, 0, 14))
    sc.box((2.4, 103, -7.4), (2.2, 5.5, 1.2), "porcelain_rim", pivot=(3.5, 103, -7), rotation=(0, 0, -14))
    sc.box((-0.8, 104.5, -8.0), (1.6, 1.6, 0.6), "tissue")                                # crest jewel (a sealed wound)
    scc = m.bone("shield_c_crack", (0, 96, -6), "shield_c")
    scc.box((-4.5, 88.5, -7.2), (9, 12.5, 1.6), "crack", inflate=0.08, faces=("north",))
    scc.box((-1.6, 103, -7.6), (3.2, 9, 1.4), "crack", inflate=0.08, faces=("north",))

    # ------------------------------------------------------------------ needle limbs (folded like a mantis)
    # Laid out hanging straight down, then folded: upper arm forward-down, forearm back up to
    # the chest, needle hanging in front of the dress.
    for side, tag in ((1, "l"), (-1, "r")):
        a = m.bone(f"arm_{tag}_a", _mp(side, (9, 78, -3)), "thorax", _mrot(side, (-52, -10, 10)))
        o, s = _mirror(side, (7.5, 59, -4.5), (3, 19, 3))
        a.box(o, s, "chitin", uv_key="arm_a")
        o, s = _mirror(side, (7, 74, -5), (4, 5, 4))
        a.box(o, s, "porcelain_rim", uv_key="arm_pauld")
        b = m.bone(f"arm_{tag}_b", _mp(side, (9, 59, -3)), f"arm_{tag}_a", _mrot(side, (-100, 0, 0)))
        o, s = _mirror(side, (7.8, 37, -4.2), (2.4, 22, 2.4))
        b.box(o, s, "chitin", uv_key="arm_b")
        o, s = _mirror(side, (7.3, 57.3, -4.7), (3.4, 3.4, 3.4))
        b.box(o, s, "tissue", uv_key="arm_joint")
        c = m.bone(f"arm_{tag}_c", _mp(side, (9, 37, -3)), f"arm_{tag}_b", _mrot(side, (136, 0, 0)))
        o, s = _mirror(side, (7.9, 21, -4.1), (2.2, 16, 2.2))
        c.box(o, s, "needle", uv_key="needle_1")
        o, s = _mirror(side, (8.2, 7, -3.8), (1.6, 14, 1.6))
        c.box(o, s, "needle", uv_key="needle_2")
        o, s = _mirror(side, (8.5, -5, -3.5), (1, 12, 1))
        c.box(o, s, "needle", uv_key="needle_3")
        o, s = _mirror(side, (7.3, 35.3, -4.7), (3.4, 3.4, 3.4))
        c.box(o, s, "tissue", uv_key="arm_joint2")
        o, s = _mirror(side, (7.4, 30, -5.2), (3.2, 5, 1.2))
        c.box(o, s, "porcelain_worn", uv_key="needle_guard")                                 # ivory hand guard
        c.locator(f"needle_{tag}", _mp(side, (9, -5, -3)))

    # ------------------------------------------------------------------ the dress: four hinged shell sections
    # Each section = bodice piece + a long lower skirt tier + a shorter overskirt tier laid on top.
    LOWER = dict(h=31, tilt=38, r=9.5, top=67)       # hem ~ 28 units out, ~42 units up
    UPPER = dict(h=17, tilt=46, r=8.0, top=71)

    def tier(bone, phis, spec, w, mat, **kw):
        for phi in phis:
            _plate(bone, phi, spec["r"], spec["top"], w, spec["h"], spec["tilt"], mat, **kw)

    # front apron
    sf = m.bone("shell_f", (0, 80, -8), "thorax")
    sf.box((-6.5, 66, -8.2), (13, 15, 2), "porcelain_fil")                                  # bodice
    sf.box((-7.5, 79.5, -8.6), (15, 2.5, 2.6), "gold")                                      # neckline band
    tier(sf, (-30, 30), LOWER, 12, "porcelain_rim")
    _plate(sf, 0, 9.8, 67, 12, 36, 34, "porcelain_fil", thick=1.8)                           # long central tabard
    sfo = m.bone("shell_f_over", (0, 70, -8), "shell_f")
    tier(sfo, (-18, 18), UPPER, 9, "porcelain_fil", thick=1.2)
    _plate(sfo, 0, 8.4, 72, 7, 12, 40, "gold", thick=1.0)

    # back mantle: skirt, high collar, and the train lying over the abdomen
    sb = m.bone("shell_b", (0, 78, 6), "thorax")
    sb.box((-7, 62, 5.5), (14, 19, 2), "porcelain_fil")
    tier(sb, (150, 180, 210), LOWER, 12, "porcelain_rim")
    sbo = m.bone("shell_b_over", (0, 70, 8), "shell_b")
    tier(sbo, (165, 195), UPPER, 9, "porcelain_fil", thick=1.2)
    col = m.bone("shell_b_collar", (0, 80, 7), "shell_b")
    for i, (x, hgt, lean) in enumerate(((0, 20, 0), (-5.5, 17, 16), (5.5, 17, -16), (-10, 12, 32), (10, 12, -32))):
        col.box((x - 2.2, 80, 6.2), (4.4, hgt, 1.2), "porcelain_fil" if i == 0 else "porcelain_rim",
                pivot=(x, 80, 6.8), rotation=(14, 0, lean))                                  # collar fan
    for i, (z, wdt, ln, drop) in enumerate(((10, 18, 16, 0), (24, 16, 16, 5), (38, 13, 15, 11), (51, 9, 13, 18))):
        sb.box((-wdt / 2, 61 - drop, z), (wdt, 2, ln), "porcelain_rim" if i % 2 else "porcelain_fil",
               pivot=(0, 62 - drop, z), rotation=(-(10 + i * 3), 0, 0))                      # train scales

    # left / right exterior shells (armour regions L and R) + their cracked look
    for side, tag in ((1, "l"), (-1, "r")):
        sh = m.bone(f"shell_{tag}", _mp(side, (9, 80, 0)), "thorax")
        o, s = _mirror(side, (7.5, 60, -7), (2.2, 22, 14))
        sh.box(o, s, "porcelain_fil")                                                        # flank cuirass
        o, s = _mirror(side, (7, 78, -7), (9, 5, 14))
        sh.box(o, s, "porcelain_rim", pivot=_mp(side, (8, 80, 0)), rotation=_mrot(side, (0, 0, -18)))   # pauldron
        o, s = _mirror(side, (13, 80.5, -5), (4.5, 2.2, 10))
        sh.box(o, s, "gold", pivot=_mp(side, (8, 80, 0)), rotation=_mrot(side, (0, 0, -18)))
        o, s = _mirror(side, (15, 82, -1.2), (2.4, 8, 2.4))
        sh.box(o, s, "bone", pivot=_mp(side, (8, 80, 0)), rotation=_mrot(side, (0, 0, -30)))             # shoulder spire
        tier(sh, tuple(p * side for p in (60, 90, 120)), LOWER, 12.5, "porcelain_rim")
        sho = m.bone(f"shell_{tag}_over", _mp(side, (9, 70, 0)), f"shell_{tag}")
        tier(sho, tuple(p * side for p in (48, 76, 104, 132)), UPPER, 8.5, "porcelain_fil", thick=1.2)
        sh.locator(f"shell_{tag}", _mp(side, (18, 60, 0)))
        cr = m.bone(f"shell_{tag}_crack", _mp(side, (9, 80, 0)), f"shell_{tag}")
        o, s = _mirror(side, (7.5, 60, -7), (2.2, 22, 14))
        cr.box(o, s, "crack", inflate=0.1, faces=("west" if side > 0 else "east",))
        for phi in (60, 90, 120):
            _plate(cr, phi * side, LOWER["r"], LOWER["top"], 12.5, LOWER["h"], LOWER["tilt"], "crack",
                   inflate=0.1, faces=("north",))
        for phi in (76, 104):
            _plate(cr, phi * side, UPPER["r"], UPPER["top"], 8.5, UPPER["h"], UPPER["tilt"], "crack",
                   thick=1.2, inflate=0.1, faces=("north",))
        # what the shell protected: raw flank tissue, only seen once the shell is gone or open
        wound = m.bone(f"flank_{tag}", _mp(side, (7, 66, 0)), "thorax")
        o, s = _mirror(side, (6.2, 58, -4.5), (1.2, 12, 9))
        wound.box(o, s, "tissue")

    # ------------------------------------------------------------------ abdomen (four segments, trailing)
    seg = [(0, 54, 6, 15, 14, 16, 12), (0, 53, 20, 14, 13, 15, 0), (0, 53, 33, 11, 11, 14, 0), (0, 54, 45, 8, 8, 12, 0)]
    parent = "thorax"
    for i, (x, y, z, wdt, hgt, ln, droop) in enumerate(seg):
        b = m.bone(f"abdomen_{i + 1}", (0, y + hgt * 0.6, z), parent, (-(droop if i == 0 else 7), 0, 0))
        b.box((-wdt / 2, y, z), (wdt, hgt, ln), "chitin")
        b.box((-wdt / 2 - 0.5, y + hgt - 2.5, z + 1), (wdt + 1, 3, ln - 3), "porcelain_worn")      # dorsal tergite
        b.box((-wdt / 2 + 1, y - 0.6, z + 2), (wdt - 2, 1.2, ln - 4), "pupa")                       # pale underside
        parent = b.name
    tip = m.bone("abdomen_tip", (0, 58, 57), parent, (-10, 0, 0))
    tip.box((-1.5, 56.5, 57), (3, 3, 7), "tissue")
    tip.box((-0.8, 57.2, 63), (1.6, 1.6, 10), "needle")
    tip.locator("tail", (0, 58, 73))

    # ------------------------------------------------------------------ six legs: hip yaw -> femur -> tibia -> tarsus
    hips = {1: (-9, 40), 2: (1, 0), 3: (11, -40)}            # z offset, yaw (front legs angle forward)
    for side, tag in ((1, "l"), (-1, "r")):
        for n, (hz, yaw) in hips.items():
            hip = m.bone(f"leg_{tag}{n}", _mp(side, (5.5, 44, hz)), "body", _mrot(side, (0, yaw, 0)))
            o, s = _mirror(side, (4, 42, hz - 2.5), (4, 5, 5))
            hip.box(o, s, "tissue", uv_key="hip")
            fa = m.bone(f"leg_{tag}{n}_a", _mp(side, (6, 44, hz)), f"leg_{tag}{n}", _mrot(side, (0, 0, -40)))
            o, s = _mirror(side, (6, 42.2, hz - 1.8), (34, 3.6, 3.6))
            fa.box(o, s, "chitin", uv_key="femur")
            o, s = _mirror(side, (16, 44.6, hz - 2.4), (16, 2.2, 4.8))
            fa.box(o, s, "porcelain_worn", uv_key="greave_a")                               # ivory greave
            tb = m.bone(f"leg_{tag}{n}_b", _mp(side, (40, 44, hz)), f"leg_{tag}{n}_a", _mrot(side, (0, 0, 110)))
            o, s = _mirror(side, (38.2, 42.2, hz - 1.8), (3.6, 3.6, 3.6))
            tb.box(o, s, "tissue", uv_key="knee")
            o, s = _mirror(side, (40, 42.6, hz - 1.4), (48, 2.8, 2.8))
            tb.box(o, s, "chitin", uv_key="tibia")
            o, s = _mirror(side, (44, 44.8, hz - 1.9), (20, 1.6, 3.8))
            tb.box(o, s, "porcelain_worn", uv_key="greave_b")
            tc = m.bone(f"leg_{tag}{n}_c", _mp(side, (88, 44, hz)), f"leg_{tag}{n}_b", _mrot(side, (0, 0, 14)))
            o, s = _mirror(side, (88, 43, hz - 1), (12, 2, 2))
            tc.box(o, s, "chitin_smooth", uv_key="tarsus_a")
            o, s = _mirror(side, (100, 43.4, hz - 0.6), (7.5, 1.2, 1.2))
            tc.box(o, s, "bone", uv_key="tarsus_b")
            tc.locator(f"foot_{tag}{n}", _mp(side, (107.5, 44, hz)))
    return m


# --------------------------------------------------------------------------- helper entities

def build_heir() -> Model:
    """An Heir: a shed shell plate that grew legs and a crude crown of its own."""
    m = Model("geometry.abm.vesperra_heir", density=1.0, bounds=(3.0, 3.0, 1.0))
    m.materials.update({"porcelain": _porcelain(worn=True, cracks=1.1, gold_rim=True), "chitin": _chitin(),
                        "tissue": _tissue, "bone": _bone(), "eye": P.glow("#ffd9c8", "#c2202c", 0.12)})
    root = m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 9, 0), "root")
    body.box((-5, 8, -7), (10, 3, 14), "porcelain")                              # the plate it once was
    body.box((-6, 9.5, -5), (12, 2.2, 10), "porcelain", pivot=(0, 10, 0), rotation=(0, 0, 0))
    body.box((-3.5, 5.5, -5), (7, 3, 10), "tissue")                              # what grew underneath
    body.box((-2, 6, -8.5), (4, 3, 2), "chitin")                                 # blind head
    for i, x in enumerate((-2.2, 0, 2.2)):
        body.box((x - 0.5, 11, -6 + abs(x) * 0.6), (1, 3.5 - abs(x) * 0.5, 1), "bone")   # its own little crown
    eye = m.bone("eye_glow", (0, 7.5, -8.6), "body")
    eye.box((-0.6, 7, -8.75), (1.2, 1.2, 0.4), "eye")
    for side, tag in ((1, "l"), (-1, "r")):
        for n, (hz, yaw) in enumerate(((-4, 30), (0, 0), (4, -30)), 1):
            hip = m.bone(f"leg_{tag}{n}", _mp(side, (3, 7, hz)), "body", _mrot(side, (0, yaw, -35)))
            o, s = _mirror(side, (3, 6.4, hz - 0.6), (7, 1.2, 1.2))
            hip.box(o, s, "chitin", uv_key="hl_a")
            low = m.bone(f"leg_{tag}{n}_b", _mp(side, (10, 7, hz)), f"leg_{tag}{n}", _mrot(side, (0, 0, 105)))
            o, s = _mirror(side, (10, 6.5, hz - 0.5), (11.6, 1, 1))
            low.box(o, s, "bone", uv_key="hl_b")
    body.locator("heir", (0, 10, 0))
    return m


def build_anchor() -> Model:
    """Cocoon anchor: a pale chrysalis impaled on a bone stake, tethered with thread."""
    m = Model("geometry.abm.cocoon_anchor", density=1.0, bounds=(2.5, 3.5, 1.2))
    m.materials.update({"pupa": _pupa, "bone": _bone(), "tissue": _tissue, "porcelain": _porcelain(worn=True, cracks=0.8),
                        "core": P.glow("#ffb69a", "#7d1f2e", 0.2)})
    root = m.bone("root", (0, 0, 0))
    root.box((-1, 0, -1), (2, 26, 2), "bone", pivot=(0, 0, 0), rotation=(0, 0, 4))
    root.box((-3, 0, -3), (6, 2, 6), "porcelain")
    pod = m.bone("pod", (0, 16, 0), "root")
    pod.box((-3.5, 9, -3.5), (7, 13, 7), "pupa")
    pod.box((-2.5, 22, -2.5), (5, 3, 5), "pupa")
    pod.box((-2.5, 6.5, -2.5), (5, 2.5, 5), "tissue")
    glow = m.bone("pod_glow", (0, 15, 0), "pod")
    glow.box((-1.5, 12, -3.75), (3, 5, 0.5), "core")
    glow.box((-1.5, 12, 3.25), (3, 5, 0.5), "core")
    pod.locator("anchor", (0, 16, 0))
    return m
