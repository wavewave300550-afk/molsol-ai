"""Race 004 - Xenentoma (เซเนนโทมา).  (v1.2 redesign)

An eyeless, antenna-less hexapod from an alternative evolutionary lineage, built on
the proturan blueprint (soil hexapods whose raised forelegs do the work of antennae,
whose conical head carries two "pseudoculi", and which add abdominal segments as
they moult) - drawn as a rearing, slender, glass-pale mantis-insect:

  * high-kneed, splayed hind legs; a thorax leaning forward under shingled tergites
  * a cone head pitched down, two opalescent false eyes, a retractable stylet, palps
  * anterior pair  - sensory forelimbs raised in a tall V, ending in glowing sensilla
  * middle pair    - slim manipulative limbs (bound to the player's arms: they hold items)
  * twelve tapering abdominal segments in an S-curve clear of the ground
  * pale chitin (ivory / pale grey) with muted violet membranes and a violet nerve glow

Variants: base | survey | glide | surge | teneral (freshly moulted) | exuvia (the shed
shell, used by the decoy entity only - no crest item).
"""
from __future__ import annotations

import math

import numpy as np

from kit.geo import Model, rot_matrix
from kit import pixel as px
from models.common import accents, chain, fp_sleeves, humanoid, mat_accent, side_rot

ID = "xenentoma"
VARIANTS = ["base", "survey", "glide", "surge", "teneral", "exuvia"]
ENTITY_ONLY = {"exuvia"}          # geometry for the decoy entity; no crest item / attachable
TEXTURES = {
    "base": {"sense": 0.0, "teneral": 0.0, "shell": 0.0},
    "sense": {"sense": 1.0, "teneral": 0.0, "shell": 0.0},
    "teneral": {"sense": 0.2, "teneral": 1.0, "shell": 0.0},
    "exuvia": {"sense": 0.0, "teneral": 0.0, "shell": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "survey": "sense", "glide": "base", "surge": "sense", "teneral": "teneral",
                   "exuvia": "exuvia"}
SEGMENTS = 12

# palettes (dark -> light)
CHITIN = px.pal("#4b4057", "#8e8597", "#b8b0b6", "#d5cec9", "#e9e2d4", "#f7f2ea")
TENERAL = px.pal("#6e6884", "#a7a1bd", "#cdc8dd", "#e4e0ee", "#f4f1f9", "#ffffff")
SHELL = px.pal("#4a3a24", "#7a6240", "#a88c62", "#cdb68c", "#e6d7b8", "#f5ecd8")
MEMBRANE = px.pal("#2e2440", "#4f3f6c", "#7d6596", "#a58fc6")
CLAW = px.pal("#1e1826", "#2e2638", "#4b4057", "#6d6280")
GLOW = "#cdb8ff"

THORAX_PIVOT = (0.0, 12.0, 0.5)
THORAX_LEAN = 20.0


def _lean(p):
    """Where a point given in the upright thorax frame sits once the thorax leans forward."""
    piv = np.array(THORAX_PIVOT)
    return tuple(piv + rot_matrix((THORAX_LEAN, 0, 0)) @ (np.array(p, float) - piv))


def _unlean(p):
    """The upright-thorax-frame point that lands on world point p once the thorax leans."""
    piv = np.array(THORAX_PIVOT)
    return tuple(piv + rot_matrix((THORAX_LEAN, 0, 0)).T @ (np.array(p, float) - piv))


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    for g in ("torso_g", "head_g", "tail_g", "r_arm_g", "l_arm_g", "r_leg_g", "l_leg_g"):
        m.bones[g].variant["glide"] = ((0.0, -6.5, 0.0), None)      # the whole body drops flat for the glide
    _legs(m)
    _thorax(m)
    _head(m)
    _forelimbs(m)
    _middle_limbs(m)
    _abdomen(m)
    fp_sleeves(m, "limb", width=4.5)
    accents(m, [
        ("c", "chest", "thorax", (0, 18.5, -2.6), (4.0, 4.0, 0.5)),
        ("c", "rsh", "r_mid0", (-4.75, 20.5, -2.0), (2.0, 1.0, 2.0)),
        ("c", "lsh", "l_mid0", (4.75, 20.5, -2.0), (2.0, 1.0, 2.0)),
        ("l", "r", "r_femur0", (-4.25, 14.0, 0.0), (2.0, 1.0, 2.0)),
        ("l", "l", "l_femur0", (4.25, 14.0, 0.0), (2.0, 1.0, 2.0)),
        ("f", "r", "r_foot", (-6.75, 1.0, -1.0), (1.5, 0.5, 2.0)),
        ("f", "l", "l_foot", (6.75, 1.0, -1.0), (1.5, 0.5, 2.0)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- legs: high-kneed, splayed

def _legs(m: Model) -> None:
    for s, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        m.box(g, (s * 2.25, 12.0, 0.5), (2.5, 2.5, 2.5), "chitin")                       # coxa
        hip, knee, ankle, foot = (s * 2.5, 12.25, 0.5), (s * 6.5, 15.5, -0.5), (s * 7.25, 3.5, 0.5), (s * 6.75, 0.75, -1.5)
        fem = chain(m, g, f"{p}_femur", [hip, knee], [2.0], "limb")
        tib = chain(m, fem[-1], f"{p}_tibia", [knee, ankle], [1.25], "limb")
        tar = m.bone(f"{p}_foot", tib[-1], ankle)
        from models.common import segment
        segment(m, tar.name, ankle, foot, 0.75, 0.75, "limb")
        for dz, ang in ((-1.25, 0.0), (0.5, 180.0)):                                       # two pretarsal claws
            m.cube(tar.name, (foot[0] - 0.25, 0.0, foot[2] + (dz if dz < 0 else 0.0)), (0.5, 0.5, 1.25), "claw")
        tar.locators[f"{p}_step"] = (foot[0], 0.2, foot[2])
        # variants: glide = splayed flat like a water strider; survey = a wider stance
        m.bones[fem[0]].variant.update({"glide": ((0, 0, 0), side_rot((0, 0, 58), s)),
                                       "survey": ((0, 0, 0), side_rot((0, 0, 8), s))})
        m.bones[tib[0]].variant.update({"glide": ((0, 0, 0), side_rot((0, 0, 12), s))})


# ----------------------------------------------------------------------------- thorax

TERGITES = [  # (y centre, height, width, back z) in the upright thorax frame
    (14.5, 4.0, 5.5, 3.25),
    (18.75, 4.5, 6.5, 3.5),
    (22.5, 3.0, 4.0, 2.0),
]


def _thorax(m: Model) -> None:
    t = m.bone("thorax", "torso_g", THORAX_PIVOT, (THORAX_LEAN, 0.0, 0.0))
    t.variant.update({"glide": ((0, 0.0, 1.0), (76.0, 0.0, 0.0)), "survey": ((0, 0, 0), (12.0, 0.0, 0.0)),
                      "surge": ((0, 0, 0), (26.0, 0.0, 0.0)), "exuvia": ((0, -1.0, 0), (28.0, 0.0, 0.0))})
    m.box(t.name, (0, 14.5, 0.75), (5.5, 4.0, 5.0), "chitin")                            # metathorax
    m.box(t.name, (0, 18.75, 0.5), (6.5, 4.5, 6.0), "chitin")                            # mesothorax
    for (y, h, w, d, z) in ((14.5, 3.5, 5.0, 5.0, 0.75), (18.75, 4.0, 6.0, 6.0, 0.5)):  # rolled cores: octagonal sections
        m.cube(t.name, (-w / 2, y - h / 2, z - d / 2), (w, h, d), "chitin", pivot=(0, y, z), rot=(0, 45, 0))
    m.box(t.name, (0, 22.5, 0.0), (4.0, 3.0, 4.0), "chitin")                             # prothorax
    m.box(t.name, (0, 12.75, 3.0), (2.0, 2.0, 2.5), "membrane")                          # petiole
    for k, (y, h, w, bz) in enumerate(TERGITES):
        tg = m.bone(f"tergite{k}", t.name, (0, y + h / 2, bz))
        tg.variant.update({"teneral": ((0, 0, 0), (-8.0, 0, 0)), "exuvia": ((0, 0, 0.5), (-24.0, 0, 0))})
        m.box(tg.name, (0, y, bz + 0.25), (w - 1.5, h + 0.5, 1.0), "tergite")            # centre plate
        for s in (-1, 1):                                                                 # flanges wrap the sides
            x = s * ((w - 1.5) / 2 + 0.75)
            m.cube(tg.name, (x - 1.0, y - (h + 0.5) / 2, bz - 0.5), (2.0, h + 0.5, 1.0), "tergite",
                   pivot=(s * (w - 1.5) / 2, y, bz + 0.25), rot=(0, -s * 30.0, 0))
        m.box(t.name, (0, y, -(w / 2 - 0.5) if k else -2.0), (w - 2.5, h - 1.0, 0.5), "sternite")
    t.locators["core"] = (0, 18.5, -2.6)
    t.locators["back"] = (0, 20.0, 4.2)


# ----------------------------------------------------------------------------- the cone head

HEAD_BASE = (0.0, 24.25, -3.0)


def _head(m: Model) -> None:
    hb = m.bone("skull", "head_g", HEAD_BASE, (15.0, 0.0, 0.0))
    hb.variant.update({"survey": ((0, 0, 0), (28.0, 0, 0)), "glide": ((0, -8.0, -5.0), (-4.0, 0, 0)),
                       "exuvia": ((0, -1.5, 0), (35.0, 0, 0))})
    x, y, z = HEAD_BASE
    m.box(hb.name, (0, y, z + 0.75), (4.0, 3.5, 2.5), "head")                         # back of the head
    for (w, h, ln, z0, roll) in ((4.5, 4.0, 3.5, 0.0, False), (3.5, 3.5, 3.5, 0.0, True),
                                 (3.5, 3.0, 3.0, 3.0, False), (2.5, 2.5, 3.0, 3.0, True),
                                 (2.5, 2.0, 2.5, 5.5, False), (1.5, 1.5, 1.5, 7.75, False)):
        o = (-w / 2, y - h / 2, z - z0 - ln)
        if roll:
            m.cube(hb.name, o, (w, h, ln), "head", pivot=(0, y, z), rot=(0, 0, 45))
        else:
            m.cube(hb.name, o, (w, h, ln), "head")
    hb.locators["mouth"] = (0, y - 0.25, z - 9.5)
    st = m.bone("stylet", hb.name, (0, y - 0.25, z - 7.5))
    m.cube(st.name, (-0.25, y - 0.5, z - 9.25), (0.5, 0.5, 3.0), "claw")              # hidden in the tip until it strikes
    for s, p in ((-1, "r"), (1, "l")):                                                # palps under the cone
        chain(m, hb.name, f"{p}_palp", [(s * 0.9, y - 1.5, z - 4.5), (s * 1.25, y - 2.75, z - 6.0), (s * 1.0, y - 3.5, z - 7.5)],
              [0.5, 0.5], "limb")
        hair = m.bone(f"{p}_hair", hb.name, (s * 2.25, y + 1.0, z - 1.5))
        m.cube(hair.name, (s * 2.25 - (0.0 if s > 0 else 0.0), y + 0.5, z - 3.0), (0.0, 2.0, 3.0), "hair", cutout=True)
    hb.locators["eyes"] = (0, y + 0.5, z - 2.0)


# ----------------------------------------------------------------------------- sensory forelimbs (a tall V)

def _forelimbs(m: Model) -> None:
    for s, p in ((-1, "r"), (1, "l")):
        sh = (s * 2.25, 22.25, -3.25)
        world = [sh, (s * 3.5, 27.5, -5.0), (s * 5.5, 32.0, -5.5), (s * 7.5, 35.5, -5.0), (s * 9.0, 37.5, -4.0)]
        pts = [_unlean(q_) for q_ in world]            # they ride on the thorax (lean with it)
        names = chain(m, "thorax", f"{p}_sense", pts, [1.25, 1.0, 0.75, 0.5], "limb")
        tip = names[-1]
        ex, ey, ez = pts[-1]
        m.box(tip, (ex, ey, ez), (0.75, 0.75, 0.75), "sensilla")                       # glowing sensory pad
        m.cube(tip, (ex - 1.0, ey - 0.25, ez), (2.0, 2.0, 0.0), "hair", cutout=True)     # crossed fans of hairs
        m.cube(tip, (ex, ey - 0.25, ez - 1.0), (0.0, 2.0, 2.0), "hair", cutout=True)
        m.bones[tip].locators[f"{p}_sensilla"] = (ex, ey + 0.5, ez)
        m.bones[names[0]].variant.update({
            "survey": ((0, 1.5, 0), side_rot((-14, 0, 12), s)),
            "glide": ((0, 0, 0), side_rot((8, 0, 22), s)),
            "surge": ((0, 0, 0), side_rot((-6, 0, 18), s)),
            "exuvia": ((0, -2.5, 0), side_rot((128, 0, -6), s)),    # the empty shell's limbs droop
        })


# ----------------------------------------------------------------------------- manipulative middle limbs

def _middle_limbs(m: Model) -> None:
    for s, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        pts = [(s * 4.5, 21.0, -1.5), (s * 6.25, 16.0, -2.0), (s * 6.0, 11.75, -1.25)]
        names = chain(m, g, f"{p}_mid", pts, [1.25, 1.0], "limb")
        claw = m.bone(f"{p}_claw", names[-1], pts[-1])
        cx, cy, cz = pts[-1]
        for k, (dx, dz) in enumerate(((-0.6, -0.4), (0.6, -0.4), (0.0, 0.6))):
            d = m.bone(f"{p}_digit{k}", claw.name, (cx + dx, cy, cz + dz))
            m.cube(d.name, (cx + dx - 0.25, cy - 2.0, cz + dz - 0.25), (0.5, 2.0, 0.5), "claw")


# ----------------------------------------------------------------------------- abdomen: twelve tapering segments

ABD_W = [3.5, 4.5, 5.0, 5.5, 5.5, 5.0, 4.5, 4.0, 3.25, 2.5, 2.0, 1.25]


def _abdomen_points():
    """An S-curve: back and a little down from the petiole, then up behind the creature."""
    start = np.array(_lean((0, 12.75, 4.25)))
    pts = [start]
    ang = math.radians(-22.0)                       # heading below horizontal, pointing back (+Z)
    for k in range(SEGMENTS):
        ln = 1.25 if k < 7 else 1.0
        ang += math.radians(2.0 if k < 3 else 13.0)
        d = np.array([0.0, math.sin(ang), math.cos(ang)])
        pts.append(pts[-1] + d * ln)
    return [tuple(p) for p in pts]


def _abdomen(m: Model) -> None:
    pts = _abdomen_points()
    names = chain(m, "tail_g", "abd", pts, ABD_W, "segment", heights=[w * 0.85 for w in ABD_W], overlap=0.5)
    for k, (bn, w) in enumerate(zip(names, ABD_W)):
        a = np.array(pts[k])
        b = np.array(pts[k + 1])
        from models.common import segment
        segment(m, bn, a, a + (b - a) * 0.3, w + 0.5, w * 0.85 + 0.5, "ring", overlap=0.0)   # the overlapping plate edge
        # surge: every segment slides out of the one before it and the abdomen arches over the back
        m.bones[bn].variant.update({"surge": ((0.0, 0.25, 0.7), (13.0 if k > 1 else 6.0, 0.0, 0.0)),
                                    "glide": ((0.0, 0.0, 0.0), (-13.0 if k >= 3 else 6.0, 0.0, 0.0)),
                                    "exuvia": ((0.0, 0.0, 0.0), (4.0, 0.0, 0.0))})
    end = names[-1]
    tip = np.array(pts[-1])
    for s in (-1, 1):                                                               # cerci
        m.cube(end, (tip[0] + s * 0.5 - 0.25, tip[1] - 0.25, tip[2]), (0.5, 0.5, 1.5), "claw",
               pivot=tuple(tip), rot=(0, s * 25.0, 0))
    m.bones[end].locators["telson"] = tuple(tip)


# ============================================================================= materials

def materials():
    return {"chitin": mat_chitin, "tergite": mat_tergite, "sternite": mat_sternite, "limb": mat_limb,
            "segment": mat_segment, "ring": mat_ring, "membrane": mat_membrane, "head": mat_head,
            "claw": mat_claw, "sensilla": mat_sensilla, "hair": mat_hair, "accent": mat_accent}


def _pal(ctx):
    if ctx.params.get("shell", 0) > 0.5:
        return SHELL
    if ctx.params.get("teneral", 0) > 0.5:
        return TENERAL
    return CHITIN


def _sense(ctx):
    return ctx.params.get("sense", 0.0)


def mat_chitin(ctx):
    return px.shade(ctx, _pal(ctx), up=0.12, down=0.14), ctx.ones(), ctx.zeros()


def mat_tergite(ctx):
    """Back plates: the lightest surfaces, each with a pale rim along its edges (lit from behind)."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.1) + 0.1
    c = px.quant(ctx, _pal(ctx), lv)
    rim = px.border(ctx, 1)
    c = np.where(rim[:, None], _pal(ctx)[-1], c)
    g = np.where(rim, 0.12 + 0.3 * ctx.params.get("teneral", 0), 0.0) if ctx.params.get("shell", 0) < 0.5 else ctx.zeros()
    return c, ctx.ones(), g


def mat_sternite(ctx):
    """Belly plates: smooth, a shade warmer, a fine keel and one ganglion glowing through."""
    c = px.shade(ctx, _pal(ctx), offset=0.04)
    ix, iy, W, H = px.texel(ctx)
    g = ctx.zeros()
    if ctx.face == "north" and W >= 3:
        keel = ix == W // 2
        c = np.where(keel[:, None], _pal(ctx)[2], c)
        dot = keel & (iy == H // 2)
        if ctx.params.get("shell", 0) < 0.5:
            c = np.where(dot[:, None], px.col(GLOW), c)
            g = np.where(dot, 0.5 + 0.4 * _sense(ctx), 0.0)
    return c, ctx.ones(), g


def mat_limb(ctx):
    """Slim limbs lit as cylinders, darker at the joints."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.06)
    c = px.quant(ctx, _pal(ctx), lv)
    if px.side(ctx) and W > 2:
        joint = (ix == 0) | (ix == W - 1)
        c = np.where(joint[:, None], _pal(ctx)[1], c)
    return c, ctx.ones(), ctx.zeros()


def mat_segment(ctx):
    """Abdominal segment: pale chitin with a violet intersegmental membrane band at its tail end."""
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, _pal(ctx), up=0.1, down=0.1)
    g = ctx.zeros()
    if px.side(ctx) and ctx.face in ("east", "west", "up", "down"):
        pass
    if ctx.face in ("east", "west"):
        band = ix == (0 if ctx.face == "west" else W - 1)
        c = np.where(band[:, None], MEMBRANE[2], c)
        g = np.where(band, 0.25 + 0.5 * _sense(ctx), 0.0)
    if ctx.face == "down" and W >= 2:                                                  # ventral nerve cord
        cord = (ix == W // 2) & ((iy % 3) == 1)
        c = np.where(cord[:, None], px.col(GLOW), c)
        g = np.where(cord, 0.6 + 0.3 * _sense(ctx), g)
    if ctx.params.get("shell", 0) > 0.5:
        g = ctx.zeros()
    return c, ctx.ones(), g


def mat_ring(ctx):
    """The overlapping front edge of each segment: a slightly darker collar with a pale lip."""
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, _pal(ctx), offset=-0.12, up=0.2)
    return c, ctx.ones(), ctx.zeros()


def mat_membrane(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = px.shade(ctx, MEMBRANE)
    dots = (px.hash01(ctx, 3) < 0.15)
    c = np.where(dots[:, None], px.col(GLOW), c)
    return c, ctx.ones(), np.where(dots, 0.5 + 0.4 * _sense(ctx), 0.1)


PSEUDOCULUS = [".oOo.",
               "oOWOo",
               "oOOOo",
               ".ooo."]


def mat_head(ctx):
    """Smooth cone head lit as one rounded form; opalescent false eyes on its flanks."""
    ix, iy, W, H = px.texel(ctx)
    lv = px.proxy(ctx, (0.0, 24.0, -6.0), (2.8, 2.6, 6.0), 0.8) + 0.04
    c = px.quant(ctx, _pal(ctx), lv)
    g = ctx.zeros()
    big = ctx.fw >= 3.4 and ctx.fh >= 3.9 and ctx.face in ("east", "west")             # the base section only
    if big and ctx.params.get("shell", 0) < 0.5:
        c, g = px.decal(ctx, c, PSEUDOCULUS, {"o": MEMBRANE[2], "O": "#b9a6ee", "W": "#ffffff"}, 1, "c",
                        glow=g, glow_chars="oOW", glow_level=0.45 + 0.4 * _sense(ctx))
    return c, ctx.ones(), g


def mat_claw(ctx):
    return px.shade(ctx, CLAW), ctx.ones(), ctx.zeros()


def mat_sensilla(ctx):
    c = px.shade(ctx, px.pal("#7d6596", "#a58fc6", "#cdb8ff", "#efe6ff"), offset=0.1)
    if ctx.params.get("shell", 0) > 0.5:
        return px.shade(ctx, SHELL), ctx.ones(), ctx.zeros()
    return c, ctx.ones(), np.full(ctx.N, 0.55 + 0.4 * _sense(ctx))


def mat_hair(ctx):
    """Rows of 1-texel sensory hairs (cutout)."""
    ix, iy, W, H = px.texel(ctx)
    hair = ((ix % 2) == 0) & ((iy + ix // 2) % 4 != 3)
    c = np.broadcast_to(_pal(ctx)[-2], (ctx.N, 3)).copy()
    return c, hair.astype(float), ctx.zeros()
