#!/usr/bin/env python3
"""
Red Dragon model generator  ->  RP models/entity/red_dragon.geo.json
                                 RP models/entity/red_dragon_fire.geo.json
                                 RP textures/entity/red_dragon.png
                                 RP textures/entity/red_dragon_fire.png

Anatomy follows the approved design (Project Director brief): western dragon, four legs
separate from two huge wings, long thick neck, long head with a big jaw, two black main
horns sweeping back, broad chest, belly armour plates, dorsal spikes, long tapering tail
with a bony spiked tip, amber slit-pupil eyes, black claws.

Rig (62 bones): root > body > chest / pelvis; neck_1..4 > head > jaw + horns; front legs
upper > lower > foot; hind legs thigh > shin > meta > foot; wings upper > fore > hand >
f1..f4 with membrane bones (wing_*_mem_*); tail_1..8.  Right side bones are mirrors of
the left (+X is the dragon's left).

The rest pose has the wings spread (T-pose) so the membranes are laid out flat; the
ground animations fold them.

Palette (approved): main #9D211E, highlight #BD392C, dark armour #4B171A, membrane
#79222B, belly #C98150, horns/claws #292427, eyes #FFCD57, fire glow #FF6B1E.

Pixels with alpha 10 are emissive under the entity_emissive material (eyes, mouth glow).
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modelkit import Model, FaceCtx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_or_draco")

# ----------------------------------------------------------------------------- palette


def hexrgb(s):
    s = s.lstrip("#")
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


MAIN = hexrgb("#9D211E")
HIGH = hexrgb("#BD392C")
ARMOR = hexrgb("#4B171A")
MEMB = hexrgb("#79222B")
BELLY = hexrgb("#C98150")
HORN = hexrgb("#292427")
EYE = hexrgb("#FFCD57")
FIRE = hexrgb("#FF6B1E")
IVORY = hexrgb("#E6D7BA")
BLACK = hexrgb("#120A0A")

GLOW_ALPHA = 10


def mix(a, b, t):
    t = np.asarray(t, dtype=float)
    if t.ndim:
        t = t[..., None]
    return a * (1 - t) + b * t


def smooth_noise(w, h, rng, cell=6.0):
    gw, gh = int(w / cell) + 3, int(h / cell) + 3
    g = rng.random((gh, gw))
    xs = np.arange(w) / cell
    ys = np.arange(h) / cell
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    fx = xs - x0
    fy = ys - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x0 + 1)]
    c = g[np.ix_(y0 + 1, x0)]
    d = g[np.ix_(y0 + 1, x0 + 1)]
    top = a * (1 - fx) + b * fx
    bot = c * (1 - fx) + d * fx
    return top * (1 - fy[:, None]) + bot * fy[:, None]


def finish(col, alpha=255):
    h, w = col.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
    out[..., 3] = alpha
    return out


def side_ao(ctx: FaceCtx, col, strength=0.12):
    """Darken the lower part of side faces, lighten the top a little."""
    if ctx.face in ("north", "south", "east", "west") and ctx.h > 2:
        v = (np.arange(ctx.h) + 0.5) / ctx.h
        f = 1.04 - strength * v
        col = col * f[:, None, None]
    elif ctx.face == "down":
        col = col * 0.82
    return col


# ----------------------------------------------------------------------------- painters

def scales(ctx: FaceCtx, base=MAIN, hi=HIGH, dark=ARMOR, sw=5, sh=3, dorsal=0.0):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    ncols = w // sw + 3
    nrows = h // sh + 3
    tbl = ctx.rng.random((nrows + 1, ncols + 1))

    def nearest(r):
        off = (r % 2) * (sw / 2)
        c = np.floor((X - off) / sw + 0.5)
        cx = c * sw + off
        cy = r * sh
        d = np.sqrt(((X - cx) / (sw * 0.62)) ** 2 + ((Y - cy) / (sh * 1.05)) ** 2)
        return d, (Y - cy) / sh, c.astype(int)

    r0 = np.floor(Y / sh).astype(int)
    d_up, fy_up, c_up = nearest(r0)          # scale whose centre is just above the texel
    d_lo, fy_lo, c_lo = nearest(r0 + 1)      # scale of the next row (partly covered)
    own_up = d_up <= 1.0
    d = np.where(own_up, d_up, d_lo)
    fy = np.where(own_up, fy_up, fy_lo)
    r = np.where(own_up, tbl[np.clip(r0, 0, nrows), np.clip(c_up, 0, ncols)],
                 tbl[np.clip(r0 + 1, 0, nrows), np.clip(c_lo, 0, ncols)])
    b = mix(base, dark, dorsal)
    col = b[None, None, :] * (0.88 + 0.22 * r)[..., None]
    # light catches the upper middle of each scale, the rim darkens toward the bottom edge
    lit = np.clip(1 - d * 1.4, 0, 1) * np.clip(0.6 - fy, 0, 1) * 1.6
    col = mix(col, hi, np.clip(lit, 0, 1) * (0.7 - 0.4 * dorsal))
    rim = np.clip((d - 0.72) / 0.28, 0, 1)
    col = mix(col, dark * 0.8, rim * 0.75)
    n = smooth_noise(w, h, ctx.rng, 8.0)
    col = col * (0.88 + 0.24 * n)[..., None]
    return finish(side_ao(ctx, col))


def scales_back(ctx):
    return scales(ctx, dorsal=0.32)


def scales_fine(ctx):
    return scales(ctx, sw=4, sh=2)


def belly(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    band = 4
    ly = Y % band
    rnd = ctx.rng.random(h // band + 2)[Y // band]
    col = BELLY[None, None, :] * (0.92 + 0.12 * rnd)[..., None]
    col = np.where((ly == 1)[..., None], mix(col, hexrgb("#E6A877"), 0.45), col)
    col = np.where((ly == 0)[..., None], mix(col, hexrgb("#5E2E1A"), 0.7), col)
    col = np.where((ly == band - 1)[..., None], mix(col, hexrgb("#8A5030"), 0.4), col)
    U = (X + 0.5) / w
    edge = np.clip(1 - np.minimum(U, 1 - U) * 6, 0, 1)
    if ctx.face in ("up", "down", "north", "south"):
        col = mix(col, MAIN * 0.8, edge * 0.55)
    n = smooth_noise(w, h, ctx.rng, 5.0)
    col = col * (0.92 + 0.14 * n)[..., None]
    return finish(side_ao(ctx, col, 0.08))


def armor(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    tw, th = 6, 5
    row = Y // th
    off = (row % 2) * 3
    lx = (X + off) % tw
    ly = Y % th
    tbl = ctx.rng.random((h // th + 2, (w + tw) // tw + 2))
    r = tbl[row, (X + off) // tw]
    col = ARMOR[None, None, :] * (0.85 + 0.3 * r)[..., None]
    col = np.where(((ly == 0) | (lx == 0))[..., None], mix(col, hexrgb("#7A2C2E"), 0.55), col)
    col = np.where(((ly == th - 1) | (lx == tw - 1))[..., None], mix(col, hexrgb("#1E0809"), 0.6), col)
    n = smooth_noise(w, h, ctx.rng, 4.0)
    col = col * (0.9 + 0.2 * n)[..., None]
    return finish(side_ao(ctx, col, 0.1))


def horn(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    tip = ctx.p.get("tip", 0.0)
    base = mix(HORN, hexrgb("#0E0B0C"), tip)
    col = base[None, None, :] * (0.9 + 0.2 * ctx.rng.random((h, w)))[..., None]
    la = ctx.long_axis_on_face()
    if la == "u":
        ring = (X % 3 == 0)
    elif la == "v":
        ring = (Y % 3 == 0)
    else:
        ring = np.zeros_like(X, dtype=bool)
    col = np.where(ring[..., None], mix(col, hexrgb("#4A4045"), 0.6), col)
    if ctx.face == "up":
        col = mix(col, hexrgb("#5A5055"), 0.25)
    return finish(side_ao(ctx, col, 0.18))


def claw(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    col = np.ones((h, w, 1)) * mix(HORN, hexrgb("#0C0A0B"), 0.35)[None, None, :]
    if ctx.face == "up":
        col = mix(col, hexrgb("#5C5458"), 0.4)
    col = col * (0.92 + 0.16 * ctx.rng.random((h, w)))[..., None]
    return finish(col)


def spine(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    V = (np.arange(h) + 0.5) / h
    if ctx.face in ("north", "south", "east", "west"):
        t = V
    else:
        t = np.full(h, 0.4 if ctx.face == "up" else 0.9)
    col = mix(hexrgb("#1C1517"), ARMOR * 1.1, t)[:, None, :] * np.ones((h, w, 1))
    col = col * (0.88 + 0.24 * ctx.rng.random((h, w)))[..., None]
    if ctx.face in ("north", "east") and w > 1:
        col[:, 0] = mix(col[:, 0], hexrgb("#6E3034"), 0.5)
    return finish(col)


def membrane(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    V = (Y + 0.5) / h
    n = smooth_noise(w, h, ctx.rng, 6.0)
    col = MEMB[None, None, :] * (0.86 + 0.22 * n)[..., None]
    col = mix(col, hexrgb("#8F2E36"), np.clip(0.45 - V, 0, 1))
    phase = ctx.rng.random() * 10
    wave = np.sin(X * 0.35 + phase) * 1.2
    vein = np.abs(((Y + wave) % 7) - 3.5) < 0.6
    col = np.where(vein[..., None], mix(col, hexrgb("#4E141B"), 0.55), col)
    spot = ctx.rng.random((h, w)) > 0.985
    col = np.where(spot[..., None], mix(col, hexrgb("#A83A3F"), 0.5), col)
    return finish(col)


def wingbone(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    col = hexrgb("#5E1B1F")[None, None, :] * (0.9 + 0.2 * ctx.rng.random((h, w)))[..., None]
    if ctx.face == "up":
        col = mix(col, HIGH, 0.35)
    la = ctx.long_axis_on_face()
    knuckle = (X % 12 == 0) if la == "u" else (Y % 12 == 0) if la == "v" else np.zeros_like(X, bool)
    col = np.where(knuckle[..., None], mix(col, ARMOR * 0.8, 0.6), col)
    return finish(side_ao(ctx, col))


def eye(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    U = (X + 0.5) / w
    V = (Y + 0.5) / h
    d = np.sqrt((U - 0.5) ** 2 + (V - 0.5) ** 2)
    col = mix(EYE, hexrgb("#C9801E"), np.clip(d * 1.6, 0, 1))
    alpha = np.full((h, w), GLOW_ALPHA)
    pupil = (np.abs(U - 0.5) < (0.5 / w + 0.01)) & (np.abs(V - 0.5) < 0.42)
    if w >= 3:
        col = np.where(pupil[..., None], hexrgb("#160904"), col)
        alpha = np.where(pupil, 255, alpha)
    out = finish(col)
    out[..., 3] = alpha
    return out


def mouth(ctx: FaceCtx):
    """Mouth interior: dark gums with an emissive fire glow (#FF6B1E) deep in the throat."""
    w, h = ctx.w, ctx.h
    X, Y = np.meshgrid(np.arange(w), np.arange(h))
    U = (X + 0.5) / w
    n = smooth_noise(w, h, ctx.rng, 3.0)
    centre = 1 - np.abs(U - 0.5) * 2
    g = np.clip(centre * 0.9 + n * 0.5 - 0.35, 0, 1)
    col = mix(ARMOR * 0.8, FIRE, g)
    col = mix(col, EYE, np.clip(g - 0.6, 0, 1) * 1.5)
    out = finish(col)
    out[..., 3] = np.where(g > 0.35, GLOW_ALPHA, 255)
    return out


def teeth(ctx: FaceCtx):
    w, h = ctx.w, ctx.h
    V = (np.arange(h) + 0.5) / h
    col = mix(IVORY, hexrgb("#B5A283"), V * 0.6)[:, None, :] * np.ones((h, w, 1))
    return finish(col)


def nostril(ctx: FaceCtx):
    col = np.ones((ctx.h, ctx.w, 1)) * BLACK[None, None, :]
    return finish(col)


def gum(ctx: FaceCtx):
    col = np.ones((ctx.h, ctx.w, 1)) * hexrgb("#5A1A1E")[None, None, :]
    col = col * (0.9 + 0.2 * ctx.rng.random((ctx.h, ctx.w)))[..., None]
    return finish(side_ao(ctx, col))


PAINTERS = {
    "scales": scales, "scales_back": scales_back, "scales_fine": scales_fine, "belly": belly, "armor": armor,
    "horn": horn, "claw": claw, "spine": spine, "membrane": membrane, "wingbone": wingbone, "eye": eye,
    "mouth": mouth, "teeth": teeth, "nostril": nostril, "gum": gum,
}

# material bundles
TORSO = {"up": "scales_back", "down": "belly", "default": "scales"}
LIMB = {"up": "scales_back", "default": "scales"}
NECK = {"up": "scales_back", "down": "belly", "default": "scales"}
UNDERPLATE = {"down": "belly", "north": "belly", "south": "belly", "default": "belly"}


# ----------------------------------------------------------------------------- anatomy

def spike(m: Model, bone, x, y, z, height, length=5, width=3, tilt=-28, mat="spine"):
    """A dorsal spike standing on (x, y, z), tilted back."""
    m.cube(bone, (x - width / 2, y - 1, z - length / 2), (width, height + 1, length), mat,
           rotation=(tilt, 0, 0), pivot=(x, y, z))


def build() -> Model:
    m = Model("geometry.dod.red_dragon")

    # ------------------------------------------------------------------ torso
    m.bone("root", None, (0, 0, 0))
    m.bone("body", "root", (0, 40, 6))
    m.bone("chest", "body", (0, 42, -6))
    m.bone("pelvis", "body", (0, 42, 20))

    # mid body
    m.cube("body", (-18, 27, -8), (36, 30, 30), TORSO)
    m.cube("body", (-14, 23, -6), (28, 5, 27), UNDERPLATE)
    # chest - broad and deep
    m.cube("chest", (-20, 25, -36), (40, 33, 30), TORSO)
    m.cube("chest", (-15, 20, -34), (30, 6, 27), UNDERPLATE)
    m.cube("chest", (-12, 30, -40), (24, 24, 5), {"down": "belly", "default": "scales"})  # sternum / neck base
    for s in (1, -1):
        x0 = 17 if s > 0 else -26
        # shoulder muscles + dark armour plates
        m.cube("chest", (x0, 33, -33), (9, 21, 19), LIMB)
        m.cube("chest", (x0 - (1 if s < 0 else 0), 52, -34), (10, 4, 21), "armor")
    # dorsal armour plates flanking the spine
    for z0, z1 in ((-34, -20), (-19, -7)):
        for s in (1, -1):
            x = 3 if s > 0 else -12
            m.cube("chest", (x, 57, z0), (9, 3, z1 - z0), "armor")
    for z0, z1 in ((-6, 7), (8, 21)):
        for s in (1, -1):
            x = 3 if s > 0 else -12
            m.cube("body", (x, 56, z0), (9, 3, z1 - z0), "armor")
    # pelvis + hips
    m.cube("pelvis", (-16, 31, 20), (32, 25, 24), TORSO)
    m.cube("pelvis", (-12, 28, 21), (24, 4, 20), UNDERPLATE)
    for s in (1, -1):
        x0 = 13 if s > 0 else -22
        m.cube("pelvis", (x0, 33, 23), (9, 20, 19), LIMB)
        m.cube("pelvis", (x0 - (1 if s < 0 else 0), 51, 22), (10, 4, 21), "armor")
    for s in (1, -1):
        x = 3 if s > 0 else -11
        m.cube("pelvis", (x, 55, 22), (8, 3, 20), "armor")
    # dorsal spikes
    for z, hgt in ((-31, 9), (-23, 11), (-14, 11)):
        spike(m, "chest", 0, 58, z, hgt)
    for z, hgt in ((-3, 10), (6, 10), (15, 9)):
        spike(m, "body", 0, 57, z, hgt)
    for z, hgt in ((26, 8), (35, 7)):
        spike(m, "pelvis", 0, 56, z, hgt)

    # ------------------------------------------------------------------ neck (straight forward, posed by rest rotations)
    neck = [
        ("neck_1", "chest", (0, 47, -36), 22, 21, 16, -40),
        ("neck_2", "neck_1", (0, 47, -51), 19, 18, 15, -12),
        ("neck_3", "neck_2", (0, 47, -65), 17, 16, 14, 14),
        ("neck_4", "neck_3", (0, 47, -78), 15, 15, 13, 18),
    ]
    for name, parent, piv, w, h, d, rot in neck:
        m.bone(name, parent, piv, (rot, 0, 0))
        z1 = piv[2] + 1
        z0 = z1 - d - 1
        m.cube(name, (-w / 2, piv[1] - h / 2, z0), (w, h, d + 1), NECK)
        m.cube(name, (-w / 2 + 3, piv[1] - h / 2 - 2, z0 + 1), (w - 6, 3, d - 1), UNDERPLATE)
        spike(m, name, 0, piv[1] + h / 2, (z0 + z1) / 2, 7 if name != "neck_4" else 5, length=4)

    # ------------------------------------------------------------------ head
    m.bone("head", "neck_4", (0, 47, -90), (20, 0, 0))
    hz = -90
    m.cube("head", (-10, 40, hz - 18), (20, 16, 19), NECK)  # skull
    m.cube("head", (-7, 45, hz - 38), (14, 8, 20),
           {"down": "mouth", "up": "scales_back", "default": "scales_fine"})  # snout / upper jaw
    m.cube("head", (-3, 52, hz - 36), (6, 3, 22), "armor")  # nasal ridge
    m.cube("head", (-8, 48, hz - 40), (16, 5, 3), {"up": "scales_back", "default": "scales_fine"})  # snout tip
    for s in (1, -1):
        sx = 1 if s > 0 else -1
        # nostrils
        m.cube("head", (3.5 if s > 0 else -5.5, 50, hz - 40.5), (2, 2, 1), "nostril")
        # brow ridges (dark armour), eyes, cheek muscles
        m.cube("head", (5 if s > 0 else -12, 54, hz - 20), (7, 4, 10), "armor", rotation=(0, 0, -12 * sx),
               pivot=(8.5 * sx, 56, hz - 15))
        m.cube("head", (9.6 if s > 0 else -10.6, 50, hz - 18), (1, 3, 5), "eye")
        m.cube("head", (8 if s > 0 else -12, 41, hz - 12), (4, 9, 11), "scales")
        # cheek spikes (small)
        m.cube("head", (10 if s > 0 else -13, 43, hz - 6), (3, 3, 9), "horn", rotation=(10, 20 * sx, 0),
               pivot=(11.5 * sx, 44.5, hz - 6))
        # upper teeth
        for i, z in enumerate((hz - 37, hz - 33, hz - 29, hz - 25, hz - 21)):
            ht = 3.5 if i == 0 else 2.5
            m.cube("head", (5.2 if s > 0 else -6.7, 45 - ht, z), (1.5, ht, 1.5), "teeth")
    # back-of-skull frill of small spikes
    for x, hgt in ((-6, 5), (-2, 6), (2, 6), (6, 5)):
        m.cube("head", (x - 1, 54, hz - 3), (2, hgt, 2), "horn", rotation=(-45, 0, 0), pivot=(x, 55, hz - 2))
    m.locator("head", "mouth", (0, 44.5, hz - 37))
    m.locator("head", "throat", (0, 44, hz - 14))
    m.locator("head", "nostril_l", (4.5, 51, hz - 40))
    m.locator("head", "nostril_r", (-4.5, 51, hz - 40))
    m.locator("head", "eyes", (0, 51, hz - 16))

    # jaw
    m.bone("jaw", "head", (0, 44, hz - 6))
    m.cube("jaw", (-6.5, 39, hz - 37), (13, 5.5, 31), {"up": "mouth", "down": "belly", "default": "scales_fine"})
    m.cube("jaw", (-8.5, 38, hz - 14), (17, 7, 10), {"up": "gum", "down": "belly", "default": "scales"})
    m.cube("jaw", (-5, 37.5, hz - 36), (10, 2, 18), "armor")  # chin plate
    for s in (1, -1):
        for i, z in enumerate((hz - 35, hz - 31, hz - 27, hz - 23)):
            ht = 3 if i == 0 else 2
            m.cube("jaw", (4.5 if s > 0 else -6, 44.5, z), (1.5, ht, 1.5), "teeth")

    # horns: two big black horns sweeping back, built straight back from the skull and bent by rest rotations
    m.bone("horn_l_1", "head", (6, 55, hz - 4), (28, 16, 0))
    m.cube("horn_l_1", (3.5, 52.5, hz - 4), (5, 5, 14), "horn")
    m.bone("horn_l_2", "horn_l_1", (6, 55, hz + 9), (-14, 6, 0))
    m.cube("horn_l_2", (4, 53, hz + 9), (4, 4, 12), "horn", tip=0.3)
    m.bone("horn_l_3", "horn_l_2", (6, 55, hz + 20), (-18, 4, 0))
    m.cube("horn_l_3", (4.5, 53.5, hz + 20), (3, 3, 10), "horn", tip=0.6)
    m.cube("horn_l_3", (5, 54, hz + 29), (2, 2, 5), "horn", tip=0.85)

    # ------------------------------------------------------------------ front legs (left; mirrored later)
    m.bone("leg_fl_upper", "chest", (22, 44, -24), (14, 0, -4))
    m.cube("leg_fl_upper", (16, 22, -31), (12, 26, 14), LIMB)
    m.cube("leg_fl_upper", (15, 35, -32), (14, 12, 16), LIMB)  # shoulder mass
    m.cube("leg_fl_upper", (16.5, 38, -33), (11, 8, 2), "armor")
    m.bone("leg_fl_lower", "leg_fl_upper", (22, 23, -24), (-30, 0, 4))
    m.cube("leg_fl_lower", (17.5, 4, -29), (9, 21, 10), LIMB)
    m.cube("leg_fl_lower", (17, 8, -30.5), (10, 9, 2), "armor")  # forearm plate
    m.bone("foot_fl", "leg_fl_lower", (22, 5, -24), (16, 0, 0))
    m.cube("foot_fl", (16.5, 0, -31), (11, 5, 12), LIMB)
    for i, x in enumerate((17.5, 21, 24.5)):
        m.cube("foot_fl", (x, 0, -36), (3, 3, 6), "scales_fine")
        m.cube("foot_fl", (x + 0.25, -0.5, -39.5), (2.5, 3, 4), "claw", rotation=(18, 0, 0), pivot=(x + 1.5, 2, -36))
    m.cube("foot_fl", (19, 1, -19.5), (2.5, 2.5, 3), "claw")  # dew claw
    m.locator("foot_fl", "foot_fl", (22, 0, -30))

    # ------------------------------------------------------------------ hind legs (left)
    m.bone("leg_hl_thigh", "pelvis", (19, 44, 32), (-48, 0, -3))
    m.cube("leg_hl_thigh", (12, 18, 23), (14, 28, 19), LIMB)
    m.cube("leg_hl_thigh", (11.5, 32, 22), (15, 14, 21), LIMB)  # haunch
    m.cube("leg_hl_thigh", (13, 28, 21.5), (12, 10, 2), "armor")
    m.bone("leg_hl_shin", "leg_hl_thigh", (19, 20, 32), (93, 0, 3))
    m.cube("leg_hl_shin", (14.5, 1, 27.5), (9, 21, 10), LIMB)
    m.bone("leg_hl_meta", "leg_hl_shin", (19, 2, 32), (-73, 0, 0))
    m.cube("leg_hl_meta", (15.5, -10, 28.5), (7, 13, 8), LIMB)
    m.cube("leg_hl_meta", (15, -3, 36), (8, 5, 2), "armor")  # hock plate
    m.bone("foot_hl", "leg_hl_meta", (19, -9, 32), (28, 0, 0))
    m.cube("foot_hl", (13.5, -14, 24), (11, 5, 13), LIMB)
    for x in (14, 17.75, 21.5):
        m.cube("foot_hl", (x, -14, 18), (3, 3, 6), "scales_fine")
        m.cube("foot_hl", (x + 0.25, -14.5, 14.5), (2.5, 3, 4), "claw", rotation=(18, 0, 0), pivot=(x + 1.5, -12, 18))
    m.cube("foot_hl", (17.75, -13, 36.5), (2.5, 2.5, 3.5), "claw")  # back toe
    m.locator("foot_hl", "foot_hl", (19, -14, 30))

    # ------------------------------------------------------------------ wings (left): spread T-pose in the XZ plane
    wy = 56
    m.bone("wing_l_upper", "chest", (18, wy, -22), (0, 0, -12))
    m.cube("wing_l_upper", (16, wy - 5, -27), (14, 10, 10), LIMB)  # shoulder joint
    m.cube("wing_l_upper", (28, wy - 4, -26), (32, 8, 8), "wingbone")
    m.bone("wing_l_mem_a", "wing_l_upper", (18, wy, -22))
    m.bone("wing_l_fore", "wing_l_upper", (60, wy, -22), (0, 8, 0))
    m.cube("wing_l_fore", (58, wy - 3.5, -25.5), (8, 7, 7), "wingbone")  # elbow
    m.cube("wing_l_fore", (64, wy - 3, -25), (46, 6, 6), "wingbone")
    m.bone("wing_l_mem_b", "wing_l_fore", (60, wy, -22))
    m.bone("wing_l_hand", "wing_l_fore", (110, wy, -22), (0, -8, 0))
    m.cube("wing_l_hand", (106, wy - 4, -26), (8, 8, 8), "wingbone")
    # thumb claw pointing forward
    m.cube("wing_l_hand", (108, wy - 1.5, -34), (3, 3, 9), "wingbone", rotation=(-10, 15, 0), pivot=(109.5, wy, -26))
    m.cube("wing_l_hand", (108.5, wy - 1, -38), (2, 2, 5), "claw", rotation=(-10, 15, 0), pivot=(109.5, wy, -26))

    # fingers fanning from the wrist (angles: + = forward for the left wing)
    fingers = [("f1", 14, 72), ("f2", -16, 68), ("f3", -44, 60), ("f4", -70, 52)]
    for name, ang, length in fingers:
        bn = f"wing_l_{name}"
        m.bone(bn, "wing_l_hand", (110, wy, -22), (0, ang, 0))
        m.cube(bn, (110, wy - 2, -24), (length * 0.55, 4, 4), "wingbone")
        m.cube(bn, (110 + length * 0.55, wy - 1.5, -23.5), (length * 0.45, 3, 3), "wingbone")
        m.cube(bn, (110 + length - 1, wy - 1, -23), (5, 2, 2), "claw" if name == "f1" else "wingbone")
    m.locator("wing_l_f1", "wing_l_tip", (110 + 72, wy, -22))

    # membranes: thin double-sided voxel staircases (no alpha cut-outs -> robust UV orientation)
    def panel(bone, x0, z0, length, depths, y=wy):  # noqa: E306
        """depths: list of membrane depths (toward +Z) for equal steps along +X."""
        n = len(depths)
        step = length / n
        for i, d in enumerate(depths):
            if d <= 0.5:
                continue
            m.cube(bone, (x0 + i * step, y - 0.25, z0), (step, 0.5, d), "membrane", faces=("up", "down"),
                   share_updown=True)

    # membranes between fingers: in each finger's local frame the next finger lies `delta` degrees behind.
    for i in range(3):
        name, ang, length = fingers[i]
        _, ang2, length2 = fingers[i + 1]
        delta = math.radians(ang - ang2)
        mb = f"wing_l_mem_{name}"
        m.bone(mb, f"wing_l_{name}", (110, wy, -22), (0, ang, 0))
        steps = 8
        depths = []
        tip2 = (length2 * math.cos(delta), length2 * math.sin(delta))
        for k in range(steps):
            xm = (k + 0.5) / steps * length
            if xm <= tip2[0]:
                d = xm * math.tan(delta)
            else:
                t = (xm - tip2[0]) / max(1e-6, length - tip2[0])
                d = tip2[1] * (1 - t)
            sag = 0.18 * d * math.sin(math.pi * (k + 0.5) / steps) if k >= steps // 2 else 0
            depths.append(max(0.0, d * 0.94 - sag))
        panel(mb, 110 + 2, -22, length - 3, depths, y=wy + 0.35 * (i + 1))
    # inner membrane: from the arm back to the flank / tail base, and from the forearm to finger 4
    panel("wing_l_mem_a", 22, -22, 38, [48, 50, 51, 52, 52], y=wy - 0.35)
    f4_tip = (110 + 52 * math.cos(math.radians(70)), -22 + 52 * math.sin(math.radians(70)))
    depths_b = []
    for k in range(9):
        x = 60 + (k + 0.5) / 9 * (f4_tip[0] - 60)
        t = (x - 60) / (f4_tip[0] - 60)
        d = 52 + (f4_tip[1] + 22 - 52) * t
        depths_b.append(d * (0.97 - 0.12 * math.sin(math.pi * t)))
    panel("wing_l_mem_b", 60, -22, f4_tip[0] - 60, depths_b, y=wy - 0.7)

    # ------------------------------------------------------------------ tail (straight back, drooping by rest rotations)
    # rest rotation x: + lifts a backward-pointing segment, so the tail droops with negative values
    # and curls back up toward the tip to rest along the ground
    tail = [(18, 16, 14, -16), (15, 14, 13, -12), (13, 12, 12, -6), (11, 10, 12, 2), (9, 8, 11, 7), (7, 7, 11, 8),
            (6, 5, 10, 6), (4, 4, 9, 4)]
    z = 43
    parent = "pelvis"
    for i, (w, h, d, rot) in enumerate(tail, start=1):
        name = f"tail_{i}"
        m.bone(name, parent, (0, 46, z), (rot, 0, 0))
        m.cube(name, (-w / 2, 46 - h / 2, z - 1), (w, h, d + 1), NECK)
        if w >= 6:
            m.cube(name, (-w / 2 + 2, 46 - h / 2 - 1.5, z), (w - 4, 2, d - 1), UNDERPLATE)
        sh = max(2.0, h * 0.5)
        spike(m, name, 0, 46 + h / 2, z + d / 2, sh, length=max(2, min(5, d * 0.35)), width=2 if w < 9 else 3)
        if i in (1, 2, 3):
            for s in (1, -1):
                x = w / 2 - 1 if s > 0 else -w / 2 - 1
                m.cube(name, (x, 46 - 1, z + 2), (2, 4, d - 4), "armor")
        parent = name
        z += d
    # bony spiked tail tip
    tip = "tail_8"
    tz = z
    m.cube(tip, (-2.5, 43.5, tz - 2), (5, 5, 6), "horn")
    m.cube(tip, (-1.5, 44.5, tz + 3), (3, 3, 8), "horn", tip=0.4)
    m.cube(tip, (-1, 45, tz + 10), (2, 2, 4), "horn", tip=0.8)
    for s in (1, -1):
        sx = 1 if s > 0 else -1
        m.cube(tip, (-1, 44.5, tz - 1), (2, 3, 9), "horn", rotation=(0, 38 * sx, 0), pivot=(0, 46, tz), tip=0.5)
        m.cube(tip, (-1, 44.5, tz - 4), (2, 2, 7), "horn", rotation=(0, 62 * sx, 0), pivot=(0, 46, tz - 3), tip=0.6)
    m.cube(tip, (-1, 46, tz - 2), (2, 7, 3), "horn", rotation=(-35, 0, 0), pivot=(0, 47, tz), tip=0.5)
    m.locator(tip, "tail_tip", (0, 46, tz + 10))

    m.locator("chest", "chest", (0, 40, -30))
    m.locator("root", "ground", (0, 0, 0))

    # mirror every left bone to the right side: wings/horns (_l_), front legs (_fl), hind legs (_hl)
    m.mirror("_l_", "_r_")
    m.mirror("_fl", "_fr")
    m.mirror("_hl", "_hr")
    return m


# ----------------------------------------------------------------------------- fire jet geometry

CHAIN = ["root", "body", "chest", "neck_1", "neck_2", "neck_3", "neck_4", "head"]


def build_fire(main: Model):
    """Second geometry rendered with an additive material only while breathing fire.
    Its chain bones copy the main skeleton's pivots/rest rotations so every animation
    moves it exactly like the head; the jet starts at the mouth and points forward (-Z)."""
    f = Model("geometry.dod.red_dragon_fire")
    for n in CHAIN:
        b = main.bones[n]
        f.bone(n, b.parent if n != "root" else None, b.pivot, b.rotation)
    mouth = main.bones["head"].locators["mouth"]["offset"]
    mx, my, mz = mouth
    f.bone("fire_jet", "head", (mx, my, mz))
    segs = 8
    seg_len = 24.0
    for i in range(segs):
        name = f"fire_s{i + 1}"
        z_far = mz - i * seg_len
        f.bone(name, "fire_jet", (mx, my, z_far - seg_len / 2))
        d0 = i * seg_len
        width = 6 + (d0 + seg_len) * 0.30
        core = width * 0.45
        # outer flame (overlaps the next segment a little)
        f.cube(name, (mx - width / 2, my - width / 2, z_far - seg_len - 4), (width, width, seg_len + 4), "fire_outer")
        f.cube(name, (mx - core / 2, my - core / 2, z_far - seg_len - 2), (core, core, seg_len + 2), "fire_core")
    # mouth burst
    f.bone("fire_mouth", "fire_jet", (mx, my, mz))
    f.cube("fire_mouth", (mx - 5, my - 4, mz - 6), (10, 8, 8), "fire_core")
    # manual UVs: left half of the fire texture = outer flame, right half = white-hot core
    k = 0
    for bn in f.order:
        for c in f.bones[bn].cubes:
            for face in c.faces:
                vo = (k * 13) % 64
                k += 1
                if c.mat == "fire_outer":
                    c.uv[face] = (0, vo, 64, 64)
                else:
                    c.uv[face] = (64, vo, 64, 64)
    return f


def fire_texture(size=128, seed=7):
    """Vertically tileable flame pattern; black = no contribution under additive blending."""
    rng = np.random.default_rng(seed)
    h = w = size
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for half, (c_lo, c_mid, c_hi) in enumerate(((hexrgb("#7A1408"), FIRE, hexrgb("#FFB347")),
                                                 (hexrgb("#FF8A2A"), EYE, hexrgb("#FFF6D8")))):
        x0 = half * (w // 2)
        hw = w // 2
        # tileable noise: sum of sines with integer periods over the height
        Y, X = np.meshgrid(np.arange(h), np.arange(hw), indexing="ij")
        v = np.zeros((h, hw))
        for k in range(6):
            fy = rng.integers(1, 5)
            fx = rng.uniform(0.05, 0.25)
            ph = rng.uniform(0, 6.28)
            v += np.sin(2 * math.pi * fy * Y / h + X * fx + ph) * (0.6 ** k)
        v = (v - v.min()) / (v.max() - v.min())
        streak = np.sin(X * 0.9 + np.sin(2 * math.pi * Y / h * 2) * 2) * 0.15
        v = np.clip(v + streak, 0, 1)
        col = np.where(v[..., None] < 0.5, mix(c_lo, c_mid, v * 2), mix(c_mid, c_hi, (v - 0.5) * 2))
        bright = np.clip(v * 1.4 - 0.15, 0, 1) if half == 0 else np.clip(v * 0.8 + 0.35, 0, 1)
        col = col * bright[..., None]
        out[:, x0:x0 + hw, :3] = np.clip(col, 0, 255).astype(np.uint8)
        out[:, x0:x0 + hw, 3] = 255
    return out


# ----------------------------------------------------------------------------- main

def dilate(img, passes=2):
    """Copy border texels into the transparent padding so mip-mapping never samples empty
    (alpha 0 = fully emissive black under entity_emissive) pixels at face edges."""
    out = img.copy()
    for _ in range(passes):
        empty = out[..., 3] == 0
        filled = out.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(out, (dy, dx), axis=(0, 1))
            take = empty & (src[..., 3] > 0) & (filled[..., 3] == 0)
            filled[take] = src[take]
        out = filled
    return out


def main():
    m = build()
    nb, nc = m.stats()
    W = 512
    used = m.pack(W, pad=1)
    H = 1 << (used - 1).bit_length()
    H = max(H, 256)
    assert used <= H <= 1024, used
    img = dilate(m.paint(W, H, PAINTERS, seed=3))

    geo = m.to_json(W, H, visible_w=24, visible_h=10, visible_off=[0, 3.5, 0])
    os.makedirs(os.path.join(RP, "models", "entity"), exist_ok=True)
    os.makedirs(os.path.join(RP, "textures", "entity"), exist_ok=True)
    with open(os.path.join(RP, "models", "entity", "red_dragon.geo.json"), "w") as fh:
        json.dump(geo, fh, indent=1)
        fh.write("\n")
    Image.fromarray(img, "RGBA").save(os.path.join(RP, "textures", "entity", "red_dragon.png"), optimize=True)

    fire = build_fire(m)
    fgeo = fire.to_json(128, 128, visible_w=30, visible_h=14, visible_off=[0, 4, 0])
    with open(os.path.join(RP, "models", "entity", "red_dragon_fire.geo.json"), "w") as fh:
        json.dump(fgeo, fh, indent=1)
        fh.write("\n")
    Image.fromarray(fire_texture(), "RGBA").save(os.path.join(RP, "textures", "entity", "red_dragon_fire.png"),
                                                 optimize=True)
    print(f"red_dragon: {nb} bones, {nc} cubes, atlas {W}x{H} ({used} rows used)")
    fb, fc = fire.stats()
    print(f"red_dragon_fire: {fb} bones, {fc} cubes")


if __name__ == "__main__":
    main()
