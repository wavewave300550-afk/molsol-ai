"""Race 009 - Octamyces Undecimus, Witness of the Eleventh Rift.

An extradimensional fungal organism that watches several realities at once - "something is
observing the player from a reality the player cannot observe in return".  Not a monster with
one eye and not malicious: unreadable.  Drawn as elegant pixel art next to vanilla Minecraft:

  * a large ASYMMETRIC mushroom cap of layered violet tissue: stepped bands that overhang the
    wrong way, two geometric plates that interlock through each other, a cowl folded over
    the eye; a coherent iridescent hue drift (blue-violet -> violet -> magenta) with luminous
    cyan-green filaments running inside the rim
  * THE UNDECIMAL EYE in the front of the cap: eleven concentric polygon frames - a triangle
    inside a square inside a pentagon ... out to a thirteen-gon - each its own bone (ring0 ..
    ring10) turning on the viewing axis, stepping forward like a funnel into a starfield void
    (the pupil).  It blinks with eight triangular plates (lid0 .. lid7) that line the socket
    and fold shut over the eye.  The whole eye rides the head group and turns toward where
    the player looks, on its own, inside the cap
  * spiral gill vanes under the cap (they turn) and two gill flaps that open their pores
  * a twisted, partly hollow stalk: a cross of tissue whose arms turn a little more at every
    tier, a glowing spiral core visible in the grooves
  * EIGHT mycelial groups with different jobs (myc0 .. myc7, each a chain myc<N>_0..2):
    0/1 manipulators on the arms (they hold items), 2/3 propulsion fans at the back,
    4 a sensor with fine forked tips, 5 a spore emitter (an earthstar puffball), 6 a
    stabiliser bundle of hanging filaments, 7 a resonance antenna with a turning triangle
  * it floats: nothing touches the ground

Variants: base (Witnessing) | sporeveil | record | offset | frame | unstable (on fire).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from kit.geo import Model
from kit import pixel as px
from models.common import accents, chain, fp_sleeves, humanoid, mat_accent, q, segment

ID = "octamyces"
VARIANTS = ["base", "sporeveil", "record", "offset", "frame", "unstable"]
TEXTURES = {
    "base": {"record": 0.0, "frame": 0.0, "burn": 0.0},
    "record": {"record": 1.0, "frame": 0.0, "burn": 0.0},
    "frame": {"record": 0.0, "frame": 1.0, "burn": 0.0},
    "unstable": {"record": 0.0, "frame": 0.0, "burn": 1.0},
}
VARIANT_TEXTURE = {"base": "base", "sporeveil": "base", "record": "record", "offset": "base", "frame": "frame",
                   "unstable": "unstable"}

# ----------------------------------------------------------------------------- proportions
HEAD = (0.0, 24.0, 0.0)              # the player's head pivot (head_g and the look counter-rotation)
FLOAT_C = (0.0, 14.0, 0.5)           # the body's centre: hover bob, lean and roll pivot about here
CAP_J = (0.0, 15.5, 0.5)             # cap / stalk joint (the cap turns and tilts about it)
EYE_C = (0.0, 22.75, -7.0)           # centre of the iris (ring0's plane)
EYE_PIV = (0.0, 22.75, -8.0)         # the eye turns about a point inside its funnel
RING_SIDES = tuple(range(3, 14))     # ring0 = triangle (innermost) ... ring10 = thirteen-gon
RINGS = len(RING_SIDES)
RING_A0, RING_DA = 0.55, 0.46        # apothem of ring0 and the step outward
RING_DZ = 0.25                       # every ring sits a quarter unit in front of the one inside it
RING_T = 0.5                         # bar thickness (one texel)
LIDS = 8
LID_A = 6.0                          # apothem of the lid octagon (the hinges)
LID_Z = -10.0                        # hinge plane (just in front of the outermost ring)
SOCKET = 6.5                         # half-opening of the socket in the cap
MYC = 8                              # primary mycelial groups
SEGS = 3                             # segments per group
STALK_Y = (6.0, 15.5)                # stalk base / top


def ring_apothem(k: int) -> float:
    return RING_A0 + RING_DA * k


def ring_z(k: int) -> float:
    return EYE_C[2] - RING_DZ * k


def _norm_deg(a: float) -> float:
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if abs(a + 180.0) < 1e-9 else round(a, 4) + 0.0


# ============================================================================= build

def build() -> Model:
    m = Model(ID, ppu=2.0, atlas_width=256)
    humanoid(m)
    # head chain: head_g cancels the player's look (two bones: exact), the cap then turns by a
    # fraction of it about the stalk joint and the eye by more, inside its socket
    m.bone("steady", "head_g", HEAD)
    m.bone("float_h", "steady", FLOAT_C)
    m.bone("float", "torso_g", FLOAT_C)
    m.bone("cap", "float_h", CAP_J)
    _cap(m)
    _eye(m)
    _gills(m)
    _stalk(m)
    _mycelia(m)
    fp_sleeves(m, "tendril_fp", width=4.5)
    accents(m, [
        ("c", "rim", "cap", (-8.75, 16.75, -6.0), (4.5, 0.5, 2.5)),
        ("c", "brow", "cap", (0.0, 30.0, -7.75), (6.0, 0.5, 1.5)),
        ("c", "collar", "stalk", (0.0, 13.0, 0.5), (4.0, 1.0, 4.0)),
        ("l", "r", "myc2_0", (-3.0, 11.75, 3.75), (1.5, 1.5, 1.5)),
        ("l", "l", "myc3_0", (3.0, 11.75, 3.75), (1.5, 1.5, 1.5)),
        ("f", "r", "myc6_2", (-0.75, 3.25, 0.5), (1.0, 0.5, 1.0)),
        ("f", "l", "myc6_2", (0.75, 3.25, 0.5), (1.0, 0.5, 1.0)),
    ])
    m.pack()
    return m


# ----------------------------------------------------------------------------- the cap

# (x0, x1, y0, y1, z0, z1, material): the dome behind the eye, built from staggered bands (an
# X-wide and a Z-deep box per band, offset so no two faces share a plane), the cheeks and the cowl
# framing the socket.  Asymmetric: the creature's left (+X) side swells higher, its right side
# steps OUT as it rises (an overhang the wrong way round).
CAP_BOXES = [
    # band 1 - the rim
    (-11.5, 11.0, 16.0, 19.0, -4.0, 8.5, "cap"),
    (-9.0, 9.5, 16.25, 19.25, -4.0, 9.5, "cap"),
    # band 2
    (-11.0, 11.5, 19.0, 23.0, -4.0, 8.0, "cap"),
    (-9.5, 9.0, 19.25, 23.25, -4.0, 9.0, "cap"),
    # band 3 (the right side steps out over band 2: the impossible overhang)
    (-12.0, 10.5, 23.0, 26.0, -4.0, 7.0, "cap"),
    (-8.5, 8.5, 23.25, 26.25, -4.0, 8.0, "cap"),
    # band 4
    (-9.5, 9.5, 26.0, 28.5, -4.5, 6.0, "cap"),
    (-7.0, 7.5, 26.25, 28.75, -5.0, 7.0, "cap"),
    # band 5 - the cowl: reaches forward over the eye
    (-7.0, 8.0, 28.5, 30.5, -8.5, 4.5, "cap"),
    (-4.5, 5.5, 28.75, 30.75, -9.0, 5.5, "cap"),
    # crown, shifted to the left and back
    (-2.0, 6.0, 30.5, 31.5, -4.5, 3.5, "cap"),
    # cheeks around the socket (front, z -9.5 .. -4)
    (-11.5, -6.5, 16.0, 22.0, -9.5, -4.0, "cap"),
    (-11.0, -6.5, 22.0, 25.5, -9.0, -4.0, "cap"),
    (-9.0, -6.5, 25.5, 28.5, -8.5, -4.0, "cap"),
    (6.5, 11.0, 16.0, 23.5, -9.25, -4.0, "cap"),
    (6.5, 9.5, 23.5, 28.5, -8.75, -4.0, "cap"),
]


def _cap(m: Model) -> None:
    for x0, x1, y0, y1, z0, z1, mat in CAP_BOXES:
        m.cube("cap", (x0, y0, z0), (x1 - x0, y1 - y0, z1 - z0), mat)
    # two geometric plates on the left flank that pass THROUGH each other (an X seen from the
    # side): one tilts up, one tilts down - each its own bone so they can slide apart (offset)
    pa = m.bone("plate_a", "cap", (11.0, 24.0, 1.0))
    m.cube(pa.name, (8.5, 23.75, -3.0), (5.0, 0.5, 8.0), "plate", pivot=(11.0, 24.0, 1.0), rot=(0, 0, 14))
    pb = m.bone("plate_b", "cap", (11.0, 24.0, 1.0))
    m.cube(pb.name, (8.0, 23.75, -1.0), (5.5, 0.5, 6.5), "plate", pivot=(11.0, 24.0, 1.0), rot=(0, 0, -16))
    pb.variant["offset"] = ((0.75, 0.5, 1.5), None)
    pa.variant["offset"] = ((0.5, -0.25, -1.0), None)
    # a folded fin on the crown's right side
    m.cube("cap", (-6.5, 30.25, -2.0), (4.5, 0.5, 7.0), "plate", pivot=(-4.25, 30.5, 1.5), rot=(0, 0, 22))
    m.bones["cap"].locators["cap_top"] = (2.0, 31.75, -0.5)


# ----------------------------------------------------------------------------- the undecimal eye

def _eye(m: Model) -> None:
    cx, cy, cz = EYE_C
    eye = m.bone("eye", "cap", EYE_PIV)
    eye.locators["eye_c"] = (cx, cy, cz + 0.25)
    # the void behind the iris: an octagon of deep space (two squares turned 45 degrees)
    pu = m.bone("pupil", eye.name, (cx, cy, cz + 0.75))
    for a in (0.0, 45.0):
        m.cube(pu.name, (cx - 4.5, cy - 4.5, cz + 0.5), (9.0, 9.0, 0.5), "void", pivot=(cx, cy, cz + 0.75),
               rot=(0, 0, a) if a else None)
    m.cube(pu.name, (cx - 1.0, cy - 1.0, cz + 0.25), (2.0, 2.0, 0.25), "singularity")
    for k, n in enumerate(RING_SIDES):
        z = ring_z(k)
        r = m.bone(f"ring{k}", eye.name, (cx, cy, z))
        a = ring_apothem(k)
        ln = q(2 * (a + RING_T / 2) * math.tan(math.pi / n) + 0.1)
        off = 180.0 / n                              # at rest every polygon has a vertex at the top (aligned)
        for j in range(n):
            ang = _norm_deg(off + 360.0 * j / n)
            m.cube(r.name, (cx - ln / 2, cy + a - RING_T / 2, z - RING_T / 2), (ln, RING_T, RING_T), "ring",
                   pivot=(cx, cy, z), rot=(0, 0, ang) if abs(ang) > 1e-6 else None)
    # eight triangular plates hinged on the octagon around the iris; at rest they are folded back
    # 90 degrees and line the socket, a blink folds them shut (rx -> 0) into a flat octagon
    w = q(2 * LID_A * math.tan(math.pi / LIDS))
    for j in range(LIDS):
        th = _norm_deg(45.0 * j)
        hx, hy = cx + LID_A * math.sin(math.radians(th)), cy + LID_A * math.cos(math.radians(th))
        lid = m.bone(f"lid{j}", eye.name, (hx, hy, LID_Z), (90.0, 0.0, th))
        m.cube(lid.name, (hx - w / 2, hy - LID_A, LID_Z - 0.25), (w, LID_A, 0.5), "lid", cutout=True,
               faces={"north", "south", "up"})


# ----------------------------------------------------------------------------- gills

def _gills(m: Model) -> None:
    """Under the cap: four vanes crossing at the stalk (eight radial fins) that turn slowly, and
    two gill flaps whose pores open."""
    g = m.bone("gill_spin", "cap", (0.0, 15.25, 0.5))
    for k, a in enumerate((0.0, 45.0, 90.0, 135.0)):
        m.cube(g.name, (-6.5, 14.75, 0.25), (13.0, 1.5, 0.5), "gill", pivot=(0.0, 15.25, 0.5),
               rot=(0, a, 0) if a else None)
    for s, p in ((-1, "r"), (1, "l")):
        fl = m.bone(f"gill_{p}", "cap", (s * 4.0, 16.0, 3.0))
        m.cube(fl.name, (s * 4.0 - 2.5, 15.0, 1.0), (5.0, 1.0, 4.5), "pore")
    m.bones["gill_spin"].locators["gills"] = (0.0, 14.5, 0.5)


# ----------------------------------------------------------------------------- the stalk

def _stalk(m: Model) -> None:
    st = m.bone("stalk", "float", (0.0, 11.0, 0.5))
    core = m.bone("stalk_core", st.name, (0.0, 11.0, 0.5))
    m.box(core.name, (0.0, 10.75, 0.5), (2.5, 9.5, 2.5), "core")
    # a twisted cross: every tier's arms turn a little further
    for k, (y0, y1, a, w) in enumerate(((6.5, 9.5, 0.0, 4.5), (9.5, 12.5, 24.0, 4.0), (12.5, 15.5, 48.0, 4.0))):
        yc = (y0 + y1) / 2
        for arm in (0, 90):
            ang = _norm_deg(a + arm)
            m.cube(st.name, (-w / 2, y0, 0.5 - 0.75), (w, y1 - y0, 1.5), "stalk", pivot=(0.0, yc, 0.5),
                   rot=(0, ang, 0) if abs(ang) > 1e-6 else None)
    m.box(st.name, (0.0, 6.25, 0.5), (5.0, 1.5, 5.0), "stalk")           # the volva at the base
    m.box(st.name, (0.0, 15.0, 0.5), (3.5, 1.0, 3.5), "stalk")            # collar under the gills
    st.locators["base_c"] = (0.0, 5.5, 0.5)


# ----------------------------------------------------------------------------- the eight mycelial groups

MYC_PTS = {
    # manipulators: start inside the cap at the arm pivot, end at the vanilla hand
    0: [(-5.0, 21.0, 0.0), (-5.5, 16.0, -0.25), (-6.25, 13.25, -0.75), (-6.0, 10.75, -1.0)],
    # propulsion fans at the back
    2: [(-1.25, 12.5, 2.0), (-3.5, 11.75, 4.5), (-5.0, 11.25, 6.75), (-6.0, 11.5, 8.75)],
    # sensor (front, fine tips)
    4: [(0.75, 11.0, -1.5), (1.25, 12.0, -4.0), (1.75, 13.5, -6.0), (2.0, 15.0, -7.5)],
    # spore emitter (an earthstar on a stem)
    5: [(-1.75, 9.0, 0.0), (-4.0, 8.5, -0.75), (-6.0, 9.0, -1.0), (-7.5, 10.5, -0.75)],
    # stabiliser (lower, a bundle of hanging filaments)
    6: [(0.0, 6.0, 0.5), (0.5, 4.75, 0.25), (-0.25, 3.5, 0.75), (0.25, 2.5, 0.25)],
    # resonance antenna (top / back)
    7: [(3.5, 31.25, 1.5), (4.25, 32.75, 3.0), (4.75, 33.75, 4.75), (4.5, 34.75, 6.25)],
}
MYC_PTS[1] = [(-x, y, z) for x, y, z in MYC_PTS[0]]
MYC_PTS[3] = [(-x, y, z) for x, y, z in MYC_PTS[2]]
MYC_PARENT = {0: "r_arm_g", 1: "l_arm_g", 2: "float", 3: "float", 4: "float", 5: "float", 6: "float", 7: "cap"}
MYC_W = {0: [1.0, 1.0, 0.75], 1: [1.0, 1.0, 0.75], 2: [1.0, 1.0, 0.75], 3: [1.0, 1.0, 0.75], 4: [1.0, 0.75, 0.5],
         5: [1.0, 0.75, 0.75], 6: [1.0, 0.75, 0.75], 7: [0.75, 0.75, 0.5]}


def _mycelia(m: Model) -> None:
    for g in range(MYC):
        pts = MYC_PTS[g]
        root = m.bone(f"myc{g}", MYC_PARENT[g], pts[0])
        chain(m, root.name, f"myc{g}_", pts, MYC_W[g], "hypha")
        tip = f"myc{g}_{SEGS - 1}"
        e = np.array(pts[-1])
        if g in (0, 1):            # a three-pronged grip around the held item
            s = -1 if g == 0 else 1
            m.box(tip, (e[0], e[1] - 0.25, e[2]), (1.5, 1.0, 1.5), "grip")
            m.bones[tip].locators[f"{'r' if g == 0 else 'l'}_grip"] = (e[0], e[1] - 0.75, e[2])
        elif g in (2, 3):          # a fan membrane
            s = -1 if g == 2 else 1
            m.cube(tip, (e[0] - 0.25, e[1] - 2.25, e[2] - 0.5), (0.5, 4.5, 4.0), "fan", cutout=True,
                   pivot=tuple(e), rot=(0, s * 20.0, 0))
        elif g == 4:               # fine forked tips
            segment(m, tip, e, e + np.array([-0.75, 1.25, -1.25]), 0.5, 0.5, "hypha_tip", overlap=0.0)
            segment(m, tip, e, e + np.array([0.75, 0.75, -1.5]), 0.5, 0.5, "hypha_tip", overlap=0.0)
        elif g == 5:               # the earthstar puffball
            m.box(tip, (e[0] - 0.25, e[1] + 0.5, e[2]), (2.5, 2.0, 2.5), "puff")
            m.box(tip, (e[0] - 0.25, e[1] + 0.5, e[2]), (3.5, 0.5, 3.5), "puff_rays")
            m.bones[tip].locators["spores"] = (e[0] - 0.25, e[1] + 1.75, e[2])
        elif g == 6:               # extra hanging filaments in the bundle
            for k, (dx, dz) in enumerate(((-0.75, 0.0), (0.75, 0.5))):
                b = f"myc6_{k + 1}"
                a = np.array(pts[k + 1]) + np.array([dx, 0.0, dz])
                segment(m, b, a, a + np.array([dx * 0.5, -1.5, 0.0]), 0.5, 0.5, "hypha_tip", overlap=0.0)
        elif g == 7:               # a small floating triangle at the tip, echoing the eye
            tri = m.bone("tri", tip, (e[0], e[1] + 1.0, e[2]))
            for j in range(3):
                ang = _norm_deg(120.0 * j)
                m.cube(tri.name, (e[0] - 0.75, e[1] + 1.0 + 0.45 - 0.25, e[2] - 0.25), (1.5, 0.5, 0.5), "crystal",
                       pivot=(e[0], e[1] + 1.0, e[2]), rot=(0, 0, ang) if abs(ang) > 1e-6 else None)


# ============================================================================= materials

def materials():
    return {"cap": mat_cap, "plate": mat_plate, "void": mat_void, "singularity": mat_singularity, "ring": mat_ring,
            "lid": mat_lid, "gill": mat_gill, "pore": mat_pore, "stalk": mat_stalk, "core": mat_core,
            "hypha": mat_hypha, "hypha_tip": mat_hypha_tip, "grip": mat_grip, "fan": mat_fan, "puff": mat_puff,
            "puff_rays": mat_puff_rays, "crystal": mat_crystal, "tendril_fp": mat_hypha, "accent": mat_accent}


def _P(ctx, k):
    return ctx.params.get(k, 0.0)


def _wp(ctx):
    return ctx.wp if ctx.wp is not None else ctx.p


CAP = px.pal("#160c28", "#26123f", "#3a1a5e", "#55237f", "#73309c", "#9441b2", "#b65dc2", "#d785d0", "#f2b6e2")
CAP_COOL = px.pal("#0f0f2c", "#171c48", "#21296a", "#2c3a8c", "#3c4fa8", "#5468be", "#7287d0", "#98abe0", "#c4d0f0")
CYAN = px.pal("#0b2f33", "#0f5552", "#14806f", "#22ab8e", "#4fd6b0", "#9bf5d6", "#e0fff2")
VOID = px.pal("#03020a", "#080614", "#0e0b22", "#171236")
LILAC = px.pal("#2a2140", "#43365f", "#62527f", "#8574a0", "#a898c0", "#ccc0dc", "#ece6f4")
PINK = px.pal("#4a1238", "#7a1d56", "#ad2e77", "#d64f98", "#f07cba", "#ffb3da", "#ffe4f2")
GOLD = px.pal("#5a3a10", "#8f6420", "#c49536", "#ecc561", "#fff0b0")
EMBER = px.pal("#1a0a08", "#3a140c", "#6e2610", "#b24a14", "#f08a28", "#ffd27a")
ASH = px.pal("#0e0b10", "#1b1620", "#2a2230", "#3b3242", "#504658", "#6a6072")


def mat_cap(ctx):
    lv = px.proxy(ctx, (0.0, 22.0, 1.0), (12.0, 10.5, 10.5), 0.85) + 0.02
    lv = px.rim(ctx, lv, 0.08, 0.06)
    p = _wp(ctx)
    c = px.quant(ctx, CAP, lv, dither=0.5)
    cool = px.quant(ctx, CAP_COOL, lv, dither=0.5)
    ix, iy, W, H = px.texel(ctx)
    t = np.clip((-p[:, 0] - 2.0) / 9.0, 0, 1)                    # the right side drifts blue
    d = px.BAYER4[iy % 4, ix % 4]
    c = np.where((d < t)[:, None], cool, c)
    if _P(ctx, "burn") > 0.5:
        c = px.quant(ctx, ASH, lv)
    return c, ctx.ones(), ctx.zeros()


def mat_plate(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx) + 0.05
    c = px.quant(ctx, PINK, lv)
    edge = px.border(ctx, 1)
    c = np.where(edge[:, None], CYAN[5], c)
    g = np.where(edge, 0.55, 0.0)
    if _P(ctx, "burn") > 0.5:
        c = np.where(edge[:, None], EMBER[3], px.quant(ctx, ASH, lv))
        g = np.where(edge, 0.3, 0.0)
    return c, ctx.ones(), g


def mat_void(ctx):
    ix, iy, W, H = px.texel(ctx)
    c = np.broadcast_to(VOID[1], (ctx.N, 3)).copy()
    h = px.hash01(ctx, 3)
    star = h > 0.965
    c = np.where(star[:, None], np.where((px.hash01(ctx, 9) > 0.5)[:, None], CYAN[5], PINK[5]), c)
    return c, ctx.ones(), np.where(star, 0.7, 0.05)


def mat_singularity(ctx):
    c = np.broadcast_to(VOID[0], (ctx.N, 3)).copy()
    return c, ctx.ones(), ctx.zeros()


RING_COL = ["#9bf5d6", "#7eeacd", "#64d8c8", "#5cc0d0", "#6aa2dc", "#7f88e2", "#9670de", "#b05cd6", "#cc52c4",
            "#e45aae", "#f478a2"]


def ring_index(ctx) -> int:
    zc = ctx.origin[2] + ctx.size[2] / 2
    return int(np.clip(round((EYE_C[2] - zc) / RING_DZ), 0, RINGS - 1))


def mat_ring(ctx):
    k = ring_index(ctx)
    base = px.col(RING_COL[k])
    lv = px.light(ctx, grad=0.0)
    c = base[None, :] * (0.75 + 0.35 * lv)[:, None]
    g = 0.35 + 0.4 * _P(ctx, "record") + 0.6 * _P(ctx, "frame")
    if _P(ctx, "burn") > 0.5:
        c = c * 0.45
        g = 0.12
    return c, ctx.ones(), np.full(ctx.N, g)


def mat_lid(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0)
    c = px.quant(ctx, CAP, lv + 0.1)
    if ctx.face in ("north", "south"):
        # triangle: full width at the hinge (top row), apex at the eye's centre (bottom)
        half = (W / 2.0) * (1.0 - (iy + 0.5) / H)
        inside = np.abs(ix + 0.5 - W / 2.0) <= half + 0.25
        edge = inside & (np.abs(ix + 0.5 - W / 2.0) > half - 1.0)
        c = np.where(edge[:, None], CYAN[4], c)
        return c, inside.astype(float), ctx.zeros()
    return c, ctx.ones(), ctx.zeros()


def mat_gill(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0) + 0.1
    c = px.quant(ctx, CYAN, lv)
    lam = (ix % 2) == 0
    c = np.where(lam[:, None], CYAN[2], c)
    g = np.full(ctx.N, 0.35)
    if _P(ctx, "burn") > 0.5:
        c = px.quant(ctx, EMBER, lv - 0.2)
        g = np.full(ctx.N, 0.2)
    return c, ctx.ones(), g


def mat_pore(ctx):
    lv = px.light(ctx) + 0.05
    c = px.quant(ctx, CAP, lv)
    ix, iy, W, H = px.texel(ctx)
    pores = ((ix % 3) == 1) & ((iy % 3) == 1)
    c = np.where(pores[:, None], GOLD[3], c)
    return c, ctx.ones(), np.where(pores, 0.6, 0.0)


def mat_stalk(ctx):
    lv = px.light(ctx, grad=0.12) + 0.05
    c = px.quant(ctx, LILAC, lv)
    ix, iy, W, H = px.texel(ctx)
    strip = px.side(ctx) & ((ix % 4) == 1)
    c = np.where(strip[:, None], CYAN[4], c)
    g = np.where(strip, 0.45, 0.0)
    if _P(ctx, "burn") > 0.5:
        c = px.quant(ctx, ASH, lv)
        g = np.where(strip, 0.15, 0.0)
    return c, ctx.ones(), g


def mat_core(ctx):
    ix, iy, W, H = px.texel(ctx)
    sp = ((ix + iy) % 4) < 2
    c = np.where(sp[:, None], PINK[4], CYAN[4])
    return c, ctx.ones(), np.full(ctx.N, 0.7)


def mat_hypha(ctx):
    lv = px.light(ctx, grad=0.0) + 0.08
    c = px.quant(ctx, LILAC, lv)
    if _P(ctx, "burn") > 0.5:
        c = px.quant(ctx, ASH, lv)
    return c, ctx.ones(), ctx.zeros()


def mat_hypha_tip(ctx):
    lv = px.light(ctx, grad=0.0) + 0.2
    c = px.quant(ctx, CYAN, lv)
    return c, ctx.ones(), np.full(ctx.N, 0.6)


def mat_grip(ctx):
    lv = px.light(ctx) + 0.05
    return px.quant(ctx, PINK, lv), ctx.ones(), np.full(ctx.N, 0.25)


def mat_fan(ctx):
    ix, iy, W, H = px.texel(ctx)
    lv = px.light(ctx, grad=0.0)
    c = px.quant(ctx, CYAN, lv)
    a = ctx.ones()
    if ctx.face in ("east", "west"):
        u = (ix + 0.5) / W
        v = (iy + 0.5) / H
        r = np.hypot(u, v - 0.5)
        a = (r <= 1.0).astype(float)
        vein = (np.abs(np.arctan2(v - 0.5, u) * 4 / np.pi) % 1) < 0.25
        c = np.where(vein[:, None], CYAN[6], CYAN[3])
    return c, a, ctx.zeros()


def mat_puff(ctx):
    lv = px.proxy(ctx, ctx.origin + ctx.size / 2, ctx.size / 2, 0.8) + 0.1
    return px.quant(ctx, GOLD, lv), ctx.ones(), np.full(ctx.N, 0.3)


def mat_puff_rays(ctx):
    lv = px.light(ctx) + 0.05
    return px.quant(ctx, PINK, lv), ctx.ones(), ctx.zeros()


def mat_crystal(ctx):
    lv = px.light(ctx, grad=0.0) + 0.25
    return px.quant(ctx, CYAN, lv), ctx.ones(), np.full(ctx.N, 0.8)
