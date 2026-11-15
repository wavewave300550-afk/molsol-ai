"""Race 004 - Xenentoma (เซเนนโทมา).

An eyeless, antenna-less hexapod from an alternative evolutionary lineage, inspired
by Protura (soil hexapods whose raised forelegs do the work of antennae, whose
conical head carries two "pseudoculi" of unknown function, and which add abdominal
segments as they moult).  Everything here is fiction built on that blueprint:

  * conical head, two false eyes (pseudoculi), a retractable needle stylet, palps
  * anterior pair  - sensory forelimbs held forward, ending in glowing sensilla
  * middle pair    - manipulative limbs bound to the player's arms (hold items)
  * posterior pair - segmented walking legs with pretarsal claws
  * three thoracic segments under split dorsal tergites (they open when it moults)
  * twelve articulated abdominal segments with intersegmental membranes that show
    when the abdomen stretches (Anamorphic Surge); styli on the first three
  * translucent ivory / pale grey / muted violet chitin with a glowing nerve cord

Variants: base | survey | glide | surge | teneral (freshly moulted) | exuvia (the
shed shell, used by the decoy entity only - no crest item).
"""
from __future__ import annotations

import numpy as np

from kit.geo import Model
from kit.tex import Ctx, hx
from kit import noise as nz
from models.common import humanoid, side_rot, fp_sleeves, ramp, bevel, face_light, mix3, clamp01, accents, mat_accent

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


def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=512)
    humanoid(m)
    _legs(m)
    _thorax(m)
    _forelimbs(m)
    _middle_limbs(m)
    _head(m)
    _abdomen(m)
    fp_sleeves(m, "chitin", width=4.2)
    accents(m, [
        ("c", "sternum", "thorax", (0, 19.0, -2.05), (5.2, 2.6, 0.5)),
        ("c", "rsh", "r_arm_g", (-5.4, 22.7, 0.1), (3.2, 1.0, 3.2)),
        ("c", "lsh", "l_arm_g", (5.4, 22.7, 0.1), (3.2, 1.0, 3.2)),
        ("l", "r", "r_femur", (-1.9, 8.6, -0.95), (2.0, 3.2, 0.5)),
        ("l", "l", "l_femur", (1.9, 8.6, -0.95), (2.0, 3.2, 0.5)),
        ("f", "r", "r_tibia", (-1.9, 3.0, -1.05), (1.7, 2.8, 0.5)),
        ("f", "l", "l_tibia", (1.9, 3.0, -1.05), (1.7, 2.8, 0.5)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- posterior pair: walking legs

FEMUR_ROT, TIBIA_ROT, TARSUS_ROT = (-6, 0, 22), (8, 0, -40), (-2, 0, 18)


def _legs(m: Model) -> None:
    for side, g, p in ((-1, "r_leg_g", "r"), (1, "l_leg_g", "l")):
        hx_ = 1.9 * side
        m.box(g, (hx_ + 0.3 * side, 11.5, 0.4), (3.0, 2.2, 3.2), "chitin")              # coxa
        fem = m.bone(f"{p}_femur", g, (hx_, 11.0, 0.3), side_rot(FEMUR_ROT, side))
        fem.variant.update({"glide": ((0, -3.3, 0.6), side_rot((-10, 0, 80), side))})
        m.box(fem.name, (hx_, 10.6, 0.3), (2.6, 1.2, 2.6), "membrane")                  # trochanter
        m.box(fem.name, (hx_, 7.9, 0.3), (2.2, 5.0, 2.3), "chitin")                     # femur
        m.cube(fem.name, (hx_ + 1.1 * side, 6.0, -0.9), (0.0, 3.2, 2.4), "setae", cutout=True, faces={"east", "west"})
        tib = m.bone(f"{p}_tibia", fem.name, (hx_, 5.5, 0.3), side_rot(TIBIA_ROT, side))
        tib.variant.update({"glide": ((0, 0, 0), side_rot((8, 0, -72), side))})
        m.box(tib.name, (hx_, 5.4, 0.3), (2.1, 1.0, 2.1), "membrane")                   # knee
        m.box(tib.name, (hx_, 2.6, 0.3), (1.7, 5.4, 1.8), "chitin")                     # tibia
        m.cube(tib.name, (hx_ + 0.85 * side, 1.0, -0.6), (0.0, 3.4, 1.8), "setae", cutout=True, faces={"east", "west"})
        tar = m.bone(f"{p}_tarsus", tib.name, (hx_, -0.1, 0.3), side_rot(TARSUS_ROT, side))
        tar.variant.update({"glide": ((0, 0, 0), side_rot((2, 0, -8), side))})
        tar.locators[f"{p}_step"] = (hx_, -0.3, -1.2)
        m.box(tar.name, (hx_, 0.0, -0.4), (2.0, 1.0, 3.4), "chitin")                    # tarsus pad
        m.box(tar.name, (hx_, -0.3, 0.9), (1.6, 0.6, 1.2), "membrane")                  # heel joint
        for k, dx in enumerate((-0.55, 0.55)):                                           # pretarsal claws
            cl = m.bone(f"{p}_toe{k}", tar.name, (hx_ + dx, 0.0, -2.0), (0, 10 * (1 if dx < 0 else -1), 0))
            m.box(cl.name, (hx_ + dx, -0.2, -2.9), (0.6, 0.7, 1.9), "claw")
            m.box(cl.name, (hx_ + dx, -0.4, -3.9), (0.5, 0.5, 0.7), "claw")


# ----------------------------------------------------------------------------- thorax and tergites

def _thorax(m: Model) -> None:
    t = m.bone("thorax", "torso_g", (0, 12, 0.5), (6, 0, 0))
    t.variant.update({"glide": ((0, -5.6, 0), (74, 0, 0)), "survey": ((0, 0, 0), (-4, 0, 0)),
                      "surge": ((0, 0, 0), (14, 0, 0)), "exuvia": ((0, -1.0, 0), (16, 0, 0))})
    m.box(t.name, (0, 13.3, 1.2), (5.6, 2.6, 4.8), "chitin")                          # abdominal joint / pelvis
    for (y, w, h, d) in ((16.0, 6.6, 3.0, 5.0), (19.1, 7.2, 3.2, 5.2), (22.2, 6.2, 2.8, 4.8)):
        m.box(t.name, (0, y, 0.7), (w, h, d), "chitin", faces={"north", "south", "east", "west"})
        m.box(t.name, (0, y, 0.7), (w, h, d), "segment", faces={"up", "down"})
        m.box(t.name, (0, y, 0.7 - d / 2 - 0.12), (w * 0.72, h * 0.8, 0.25), "sternite")    # ventral plate
        m.box(t.name, (0, y - h / 2 - 0.15, 0.7), (w * 0.84, 0.3, d * 0.84), "membrane")   # intersegment band
    m.box(t.name, (0, 24.1, 0.3), (3.6, 1.6, 3.4), "membrane")                        # neck
    for side in (-1, 1):
        m.cube(t.name, (3.5 * side, 16.5, -1.2), (0.0, 5.2, 3.0), "setae", cutout=True, faces={"east", "west"})
    # dorsal tergites in two halves hinged at their outer edges: they split along the
    # midline when the creature moults (exuvia) and flare during the Surge
    for k, y in enumerate((22.4, 19.4, 16.3)):
        for side, p in ((-1, "r"), (1, "l")):
            name = f"tergite_{p}{k}"
            b = m.bone(name, t.name, (3.7 * side, y, 3.3), (-8, 0, 0))
            b.variant.update({
                "exuvia": ((0, 0, 0), side_rot((-8, -38, 0), side)),
                "surge": ((0, 0, 0), side_rot((-14, -10, 0), side)),
                "teneral": ((0, 0, 0), side_rot((-8, -6, 0), side)),
            })
            x0 = 0.0 if side > 0 else -3.7
            m.cube(name, (x0, y - 1.75, 3.0), (3.7, 3.5, 0.7), "tergite")
    t.locators["core"] = (0, 18.5, -1.0)
    t.locators["back"] = (0, 20.0, 3.6)


# ----------------------------------------------------------------------------- anterior pair: sensory forelimbs

SENSE_REST = {"base": ((-38, 16, 0), (24, 0, 0), (16, 0, 0)),
              "survey": ((-72, 30, 0), (-4, 0, 0), (-8, 0, 0)),
              "glide": ((10, 44, 0), (40, 0, 0), (30, 0, 0)),
              "surge": ((-50, 40, 0), (10, 0, 0), (6, 0, 0)),
              "exuvia": ((30, 10, 0), (30, 0, 0), (20, 0, 0)),
              "teneral": ((-30, 20, 0), (30, 0, 0), (24, 0, 0))}


def _forelimbs(m: Model) -> None:
    for side, p in ((-1, "r"), (1, "l")):
        x = 2.4 * side
        segs = (("sense0", 22.5, -1.6, 5.2, 1.0), ("sense1", None, None, 4.6, 0.8), ("sense2", None, None, 3.6, 0.6))
        parent, z0 = "thorax", -1.6
        for k, (nm, _, _, ln, th) in enumerate(segs):
            name = f"{p}_{nm}"
            rest = {v: ((0, 0, 0), side_rot(SENSE_REST[v][k], side)) for v in SENSE_REST}
            b = m.bone(name, parent, (x, 22.5, z0), side_rot(SENSE_REST["base"][k], side))
            b.variant.update(rest)
            m.box(name, (x, 22.5, z0), (th + 0.5, th + 0.5, th + 0.5), "membrane")    # joint
            m.cube(name, (x - th / 2, 22.5 - th / 2, z0 - ln), (th, th, ln), "chitin")
            if k == 2:
                # tarsal sensilla: fans of glowing sensory hairs (the creature's "antennae")
                m.cube(name, (x, 22.5 - 1.3, z0 - ln - 0.6), (0.0, 2.6, ln * 0.8), "sensilla", cutout=True,
                       faces={"east", "west"})
                m.cube(name, (x - 1.3, 22.5, z0 - ln - 0.6), (2.6, 0.0, ln * 0.8), "sensilla", cutout=True,
                       faces={"up", "down"})
                b.locators[f"{p}_sensilla"] = (x, 22.5, z0 - ln - 0.6)
            else:
                m.cube(name, (x, 22.5 - 0.9, z0 - ln * 0.8), (0.0, 1.8, ln * 0.6), "setae", cutout=True,
                       faces={"east", "west"})
            parent, z0 = name, z0 - ln


# ----------------------------------------------------------------------------- middle pair: manipulative limbs

def _middle_limbs(m: Model) -> None:
    for side, g, p in ((-1, "r_arm_g", "r"), (1, "l_arm_g", "l")):
        ax = 5.4 * side
        m.bones[g].variant.update({"glide": ((-1.2 * side, -10.5, -8.0), None)})      # tucked along the flat body
        m.box(g, (ax, 21.2, 0.1), (3.0, 2.8, 3.0), "chitin")                            # coxa
        m.box(g, (ax, 19.6, 0.1), (2.4, 0.8, 2.4), "membrane")
        up = m.bone(f"{p}_mid0", g, (ax, 19.4, 0.1), side_rot((0, 0, 5), side))
        up.variant.update({"glide": ((0, 0, 0), side_rot((-50, 0, 40), side)),
                           "exuvia": ((0, 0, 0), side_rot((10, 0, 12), side))})
        m.box(up.name, (ax, 17.0, 0.1), (2.0, 4.8, 2.0), "chitin")
        m.cube(up.name, (ax + 1.0 * side, 15.6, -0.8), (0.0, 2.8, 1.6), "setae", cutout=True, faces={"east", "west"})
        lo = m.bone(f"{p}_mid1", up.name, (ax, 14.6, 0.1), side_rot((-8, 0, -5), side))
        lo.variant.update({"glide": ((0, 0, 0), side_rot((60, 0, 0), side))})
        m.box(lo.name, (ax, 14.5, 0.1), (2.2, 1.0, 2.2), "membrane")
        m.box(lo.name, (ax, 12.4, 0.0), (1.7, 4.2, 1.7), "chitin")
        hand = m.bone(f"{p}_claw", lo.name, (ax, 10.4, 0.0))
        m.box(hand.name, (ax, 9.8, 0.0), (2.0, 1.2, 2.2), "chitin")
        for k, (dx, dz) in enumerate(((0.0, -0.75), (0.0, 0.75), (-0.65 * side, 0.0))):
            c = m.bone(f"{p}_digit{k}", hand.name, (ax + dx, 9.2, dz))
            m.box(c.name, (ax + dx, 8.4, dz), (0.6, 1.6, 0.6), "claw")


# ----------------------------------------------------------------------------- head

def _head(m: Model) -> None:
    hb = m.bone("skull", "head_g", (0, 24.2, 0.2), (6, 0, 0))
    hb.variant.update({"survey": ((0, 0, 0), (-10, 0, 0)), "exuvia": ((0, -0.6, 0), (24, 0, 0)),
                       "glide": ((0, -13.2, -10.6), (8, 0, 0))})
    # conical head: a tapering stack, no eyes, no antennae
    for (y, z, w, h, d) in ((26.0, -0.8, 5.0, 4.4, 4.6), (25.8, -4.0, 4.0, 3.6, 2.4), (25.6, -6.0, 3.0, 2.8, 1.8),
                            (25.4, -7.5, 1.9, 1.9, 1.4), (25.3, -8.6, 1.0, 1.0, 1.0)):
        m.box(hb.name, (0, y, z), (w, h, d), "chitin")
    m.box(hb.name, (0, 28.3, -1.2), (3.2, 0.4, 3.4), "tergite")                        # cranial plate
    m.box(hb.name, (0, 24.1, -3.4), (3.0, 0.5, 4.0), "sternite")                       # gular plate
    for side, p in ((-1, "r"), (1, "l")):
        # pseudoculi: false eyes - iridescent sensory discs with no lens and no pupil
        m.box(hb.name, (2.55 * side, 26.4, -2.0), (0.4, 1.6, 1.4), "pseudoculus")
        palp = m.bone(f"{p}_palp", hb.name, (0.7 * side, 24.6, -7.4), side_rot((20, 0, -10), side))
        m.box(palp.name, (0.7 * side, 24.0, -7.7), (0.4, 1.4, 0.4), "membrane")
        m.box(palp.name, (0.7 * side, 23.2, -7.8), (0.35, 0.6, 0.35), "claw")
    st = m.bone("stylet", hb.name, (0, 25.1, -6.0))
    m.cube(st.name, (-0.2, 24.9, -10.5), (0.4, 0.4, 4.5), "stylet")                   # tip shows at rest
    hb.locators["mouth"] = (0, 25.2, -9.6)


# ----------------------------------------------------------------------------- abdomen

def _abdomen(m: Model) -> None:
    parent, y, z = "tail_g", 12.6, 3.0
    for k in range(SEGMENTS):
        w = 5.2 - k * 0.27
        h = 3.6 - k * 0.17
        ln = 2.0 - k * 0.04
        name = f"abd{k}"
        b = m.bone(name, parent, (0, y, z), (-10 if k == 0 else -4, 0, 0))
        b.variant.update({
            # Anamorphic Surge: every segment stretches out of the previous one (the
            # intersegmental membranes show) and the abdomen arches over the back
            "surge": ((0, 0, 0.9), (70 if k == 0 else 10, 0, 0)),
            "glide": ((0, -5.4 if k == 0 else 0, 0), (2 if k == 0 else 0.5, 0, 0)),
            "survey": ((0, 0, 0), (-16 if k == 0 else -3.5, 0, 0)),
            "exuvia": ((0, 0, -0.1), (-14 if k == 0 else -5, 0, 0)),
        })
        m.box(name, (0, y, z - 0.25), (w * 0.84, h * 0.78, 1.0), "membrane")
        m.box(name, (0, y, z + ln / 2 + 0.2), (w, h, ln), "segment", faces={"east", "west", "down", "north", "south"})
        m.box(name, (0, y, z + ln / 2 + 0.2), (w, h, ln), "tergite", faces={"up"})
        if k < 3:   # abdominal styli, as on real proturans' first three segments
            for side in (-1, 1):
                m.cube(name, (w * 0.3 * side, y - h / 2 - 0.9, z + 0.3), (0.0, 0.9, 1.0), "setae", cutout=True,
                       faces={"east", "west"})
        if k == SEGMENTS - 1:
            m.box(name, (0, y, z + ln + 0.7), (w * 0.7, h * 0.7, 1.0), "telson")
            b.locators["telson"] = (0, y, z + ln + 1.2)
        parent, z = name, z + ln


# ============================================================================= materials

def materials():
    return {"chitin": mat_chitin, "segment": mat_segment, "tergite": mat_tergite, "sternite": mat_sternite,
            "membrane": mat_membrane, "pseudoculus": mat_pseudoculus, "setae": mat_setae, "sensilla": mat_sensilla,
            "claw": mat_claw, "stylet": mat_stylet, "telson": mat_telson, "accent": mat_accent}


def _P(ctx):
    return ctx.params.get("sense", 0.0), ctx.params.get("teneral", 0.0), ctx.params.get("shell", 0.0)


def _chitin(ctx: Ctx, tone=0.0):
    sense, ten, shell = _P(ctx)
    p = ctx.p
    n = nz.fbm(p, 0.8, 3, seed=11)
    c = ramp([(0, "#8f8898"), (0.35, "#bdb6b4"), (0.7, "#e2dccf"), (1, "#f5f0e4")], n * 0.7 + 0.25 + tone)
    # growth lines of the cuticle
    lines = np.abs(np.mod(p[:, 1] * 1.6 + nz.value(p, 0.6, seed=5) * 1.4, 1.0) - 0.5) < 0.06
    c = np.where(lines[:, None], c * 0.88, c)
    # translucency: where the cuticle is thin the violet tissue beneath shows through
    thin = nz.smoothstep(0.52, 0.82, nz.fbm(p * 1.3, 0.55, 2, seed=21))
    c = mix3(c, hx("#8a72b0"), thin * 0.42)
    glow = thin * (0.08 + 0.3 * sense)
    if ten > 0:      # freshly moulted: pale, soft, pinkish and glossy
        c = mix3(c, hx("#fbf3f4"), 0.45 * ten)
        c = mix3(c, hx("#e8c7d8"), thin * 0.4 * ten)
        gloss = nz.hash_points(p, 0.5, 9) < 0.07
        c = np.where((gloss & (ctx.face in ("up", "north", "east", "west")))[:, None], hx("#ffffff"), c)
    if shell > 0:    # shed exuvia: dull amber-grey, cracked
        c = mix3(c, hx("#b2a27f"), 0.55 * shell)
        crack = nz.smoothstep(0.88, 0.95, nz.ridged(p, 0.7, 2, seed=8))
        c = mix3(c, hx("#4f4436"), crack * shell)
        glow = glow * 0.0
    return c, glow


def mat_chitin(ctx):
    c, g = _chitin(ctx)
    return bevel(ctx, face_light(ctx, c, 0.10, 0.18), 0.18, 0.5), ctx.ones() * 1.0, g


def mat_segment(ctx):
    c, g = _chitin(ctx, tone=-0.05)
    # a darker sclerotised ring at the back edge of every segment
    v = ctx.t / max(ctx.fh, 1e-6)
    u = ctx.s / max(ctx.fw, 1e-6)
    ring = (u > 0.86) if ctx.face in ("east", "west") else (v > 0.8)
    c = np.where(ring[:, None], c * 0.78, c)
    spiracle = (np.abs(u - 0.4) < 0.08) & (np.abs(v - 0.45) < 0.1) & (ctx.face in ("east", "west"))
    c = np.where(spiracle[:, None], hx("#3c3046"), c)
    return bevel(ctx, face_light(ctx, c, 0.12, 0.2), 0.16, 0.4), ctx.ones(), g


def mat_tergite(ctx):
    sense, ten, shell = _P(ctx)
    c, g = _chitin(ctx, tone=0.0)
    c = mix3(c, hx("#b9aed0"), 0.22)
    u = ctx.s / max(ctx.fw, 1e-6)
    v = ctx.t / max(ctx.fh, 1e-6)
    ridge = np.abs(np.mod(v * 3.0, 1.0) - 0.5) < 0.08
    c = np.where(ridge[:, None], c * 1.12, c)
    edge = ctx.edge < 0.3
    c = np.where(edge[:, None], mix3(c, hx("#5d4f73"), 0.55), c)
    if shell > 0:   # the moulting split along the midline
        split = np.abs(u - 0.5) < 0.04
        c = np.where(split[:, None], hx("#2d2433"), c)
    return bevel(ctx, c, 0.2, 0.4), ctx.ones(), g


def mat_sternite(ctx):
    sense, ten, shell = _P(ctx)
    c, g = _chitin(ctx, tone=0.15)
    u = ctx.s / max(ctx.fw, 1e-6)
    v = ctx.t / max(ctx.fh, 1e-6)
    # the ventral nerve cord: a chain of glowing ganglia seen through the thin plate
    cord = np.abs(u - 0.5) < 0.07
    gang = ((u - 0.5) ** 2 * 4 + (np.mod(v * 2.0, 1.0) - 0.5) ** 2) < 0.05
    nerve = (cord | gang) & (shell == 0)
    col = mix3(hx("#9f7fe0"), hx("#efe0ff"), 0.3 + 0.5 * sense)
    c = np.where(nerve[:, None], col, c)
    g = np.where(nerve, 0.45 + 0.45 * sense, g)
    return c, ctx.ones(), g


def mat_membrane(ctx):
    sense, ten, shell = _P(ctx)
    n = nz.fbm(ctx.p, 1.6, 2, seed=17)
    c = ramp([(0, "#5e4a78"), (0.5, "#8d6fa8"), (1, "#c4a3cf")], n)
    c = mix3(c, hx("#e7c3d6"), 0.35 * ten)
    if shell > 0:
        c = mix3(c, hx("#6e5f4a"), 0.7 * shell)
    sheen = nz.hash_points(ctx.p, 0.5, 13) < 0.05
    c = np.where(sheen[:, None], c * 1.35, c)
    return c, ctx.ones(), ctx.zeros() + 0.06 * (1 - shell)


def mat_pseudoculus(ctx):
    sense, ten, shell = _P(ctx)
    c = np.broadcast_to(hx("#2a2236"), (ctx.N, 3)).copy()
    g = ctx.zeros()
    if ctx.face in ("east", "west"):
        u = ctx.s / ctx.fw - 0.5
        v = ctx.t / ctx.fh - 0.5
        r = np.sqrt(u * u * 1.4 + v * v)
        rings = ramp([(0, "#f4eeff"), (0.3, "#b9a6e6"), (0.55, "#7d62b8"), (0.8, "#d8d0c4"), (1, "#3a3046")], r / 0.55)
        disc = r < 0.55
        c = np.where(disc[:, None], rings, c)
        # concentric "lens-less" rings: there is no pupil - it is not an eye
        band = np.abs(np.mod(r * 9, 1.0) - 0.5) < 0.12
        c = np.where((disc & band)[:, None], c * 0.82, c)
        g = np.where(disc, 0.25 + 0.55 * sense, 0.0) * (1 - shell)
    return c, ctx.ones(), g


def mat_setae(ctx):
    sense, ten, shell = _P(ctx)
    u = ctx.s / max(ctx.fw, 1e-6)
    v = ctx.t / max(ctx.fh, 1e-6)
    hair = np.mod(u * 7 + v * 1.5, 1.0) < 0.22
    alpha = np.where(hair & (v > 0.1), 1.0, 0.0)
    c = mix3(hx("#d8d2c8"), hx("#f7f3ea"), v)
    return c, alpha, ctx.zeros()


def mat_sensilla(ctx):
    sense, ten, shell = _P(ctx)
    u = ctx.s / max(ctx.fw, 1e-6)
    v = ctx.t / max(ctx.fh, 1e-6)
    hair = (np.mod(u * 5 + v * 0.8, 1.0) < 0.28) & (np.abs(v - 0.5) < 0.45 - 0.25 * u)
    tip = u > 0.7
    c = np.where(tip[:, None], mix3(hx("#b49cf0"), hx("#f2e9ff"), sense), hx("#e6e0d4"))
    g = np.where(tip & hair, 0.35 + 0.6 * sense, 0.0) * (1 - shell)
    return c, np.where(hair, 1.0, 0.0), g


def mat_claw(ctx):
    sense, ten, shell = _P(ctx)
    c = ramp([(0, "#6d4f2c"), (0.6, "#3a2a1c"), (1, "#1a120c")], 1 - ctx.local[:, 1])
    c = mix3(c, hx("#c8b49a"), 0.5 * ten)
    return c, ctx.ones(), ctx.zeros()


def mat_stylet(ctx):
    sense, ten, shell = _P(ctx)
    tip = ctx.local[:, 2] < 0.25
    c = np.where(tip[:, None], hx("#c9b2ff"), hx("#2c2338"))
    return c, ctx.ones(), np.where(tip, 0.5 + 0.4 * sense, 0.0) * (1 - shell)


def mat_telson(ctx):
    sense, ten, shell = _P(ctx)
    c, g = _chitin(ctx, tone=0.1)
    tipg = nz.smoothstep(0.4, 1.0, ctx.local[:, 2])
    c = mix3(c, hx("#b79cf2"), tipg * 0.5)
    return bevel(ctx, c, 0.2, 0.3), ctx.ones(), tipg * (0.2 + 0.4 * sense) * (1 - shell)
