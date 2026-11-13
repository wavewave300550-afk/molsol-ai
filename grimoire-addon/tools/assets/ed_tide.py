"""Water & Ice Dragon -- "The Cryogenic Tidal Sovereign" (ED03; reused by ED05 as a skeleton and ED06 alive).

Spinosaurus-inspired, sail-backed, semi-aquatic dragon plus the ED03 constructs (water streams, the suspended
water mass, tidal currents that freeze into spiral ice, the frozen crown, travelling ice shards, ice
encasements), its particles and its own aquatic voice.  Everything is original procedural content.

RIG  (bb space: front = -Z, +X = the dragon's RIGHT side, +Y up; units 1/16 block; rendered at SCALE = 2.0)
  root (0,0,0)                         feet / ground contact at y = 0 (script position = ground point under the chest)
   body    pivot (0,30,18)             pelvis / hips; parent of everything else
    spine1 (0,31,10)  -> spine2 (0,31,-7)                  mid torso -> chest + shoulders
      neck1 (0,33,-20) -> neck2 (0,37,-29) -> neck3 (0,40,-36) -> head (0,42,-42) -> jaw (0,39.5,-47)
          head: headfin (blend ear-frills)      jaw: jawfin (blend throat fin)
      arm_{r,l}_1 shoulder (+-10,28,-15) -> arm_{s}_2 elbow (+-11.5,15,-11) -> hand_{s} wrist (+-11.5,5,-16)
          armfin_{s} (blend forearm fin, child of arm_{s}_2); three ivory claws, big thumb claw inside
    leg_{r,l}_1 hip (+-9.5,29,19) -> leg_{s}_2 knee (+-11,17,14) -> leg_{s}_3 ankle (+-11,7,21) -> foot_{s} (+-11,1.5,17)
          footweb_{s} (blend toe webbing)
    tail1 (0,31,29) -> ... -> tail10   10-bone chain along +Z (91 units), drooping 0.7 per joint; tailfin{i}
          (blend paddle fin per segment: tall dorsal fin, ventral fin from tail5 on, caudal fan on tailfin10)
    sail_1 .. sail_12   dorsal spine rods, pivot at their base on the back (z = -19 .. 33, front to back), parented
          by position to spine2 / spine1 / body / tail1; each has children sailm_i (blend membrane) and
          sailice_i (blend hexagonal ice plates + ice crest, scaled by the client variable v.frost)
    sailflow_1..3 (child of spine1, blend water sheets visible only in the 'power' state)
  Locators: mouth, snout (head) | chest (spine2) | hand_r, hand_l | foot_r, foot_l | tail_mid (tail5) |
            tail_tip (tail10) | sail_front (sail_2), sail_peak (sail_6), sail_back (sail_11)
  Rendered size: ~25.5 blocks long (snout z=-86 .. tail tip z=+120), back ~5 blocks high, sail crest ~9 blocks.

LOCOMOTION (script speeds that keep the feet planted)
  'move'  sinuous quadrupedal walk (lateral sequence, girdles counter-rotate, tail wave): cycle 1.6 s,
          WALK_SPEED = 2.5 blocks/s.   'swim' whole-body lateral wave, tail-driven, limbs tucked: cycle 1.2 s,
          SWIM_SPEED = 14 blocks/s (also used to 'swim' through the air).  turn_l / turn_r last 1.0 s: rotate the
          yaw up to 90 degrees over that second.

FROST / SKINS
  Texture skin 1 = 'cryo' (actor.skin(1)): frosted scales, white-glowing hexagonal veins, icy fins.  The hex ice
  plates on the sail grow front-to-back over ~1.4 s whenever the actor enters 'power' (client controller sets
  v.frost_goal = 1) and thaw back-to-front on 'arrive' / 'depart' / 'hidden'.  Scripts can also hold the frost
  with the float property grimoire:frost (0..1).  Recommended: state(power) + skin(1) in the same tick.

STATES / STATE_IDS below (contract names + swim, land, roar, attack_c).  attack_a = two-way tail sweep (hits at
0.5 s to the right, 1.05 s back across), attack_b = overhead tail strike (hit 0.9 s), attack_c = sail flare
(hit 0.45 s), power = sail crystallisation, rest = settled with the head lowered, depart = dissolves into water.
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, Anim, M, S
from kit.geo import Mat, Model, ring
from kit.parts import sym, wave

from .a_fx_common import particles

ACTOR = "dragon_tide"
SCALE = 2.0
LIFETIME = 150
WALK_SPEED = 2.5      # blocks / s for 'move'
WALK_CYCLE = 1.6
SWIM_SPEED = 14.0     # blocks / s for 'swim'
SWIM_CYCLE = 1.2

STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["move"], 4: ["turn_l"], 5: ["turn_r"], 6: ["attack_a"],
          7: ["attack_b"], 8: ["power"], 9: ["react"], 10: ["rest"], 11: ["depart"], 12: ["swim"], 13: ["land"],
          14: ["roar"], 15: ["attack_c"]}
STATE_IDS = {v[0]: k for k, v in STATES.items()}
ALWAYS = ["breathe", "sail_life", "fins_life", "frost"]
LENGTHS = {"arrive": 1.0, "land": 0.8, "power": 1.5, "attack_a": 1.5, "attack_b": 1.7, "attack_c": 1.1, "roar": 1.4,
           "react": 0.8, "depart": 1.6, "turn_l": 1.0, "turn_r": 1.0}
HITS = {"attack_a": (0.5, 1.05), "attack_b": (0.9,), "attack_c": (0.45,), "land": (0.25,)}

SAPH_D, SAPH, AQUA, BELLY = "#0b2350", "#17437f", "#2f88c6", "#a8d4e8"
IVORY, ICE, GLOW, SILVER = "#e9dfc6", "#eef9ff", "#7ff4ff", "#a9c4dd"

TAIL_L = [10, 10, 10, 10, 9, 9, 9, 8, 8, 8]
TAIL = [f"tail{i + 1}" for i in range(10)]
NSAIL = 12
SAIL = [f"sail_{i + 1}" for i in range(NSAIL)]
NECK = ["neck1", "neck2", "neck3"]
rgb, mix = tex.rgb, tex.mix


# ----------------------------------------------------------------------------------------------- painters
def _hex_edge(x, y, s):
    """~0 on the borders of a pointy-top honeycomb of cell radius s (pixel units)."""
    w, h = math.sqrt(3) * s, 3.0 * s
    ax, ay = x - w * np.round(x / w), y - h * np.round(y / h)
    bx, by = x - w * (np.round((x - w / 2) / w) + 0.5), y - h * (np.round((y - h / 2) / h) + 0.5)
    da, db = np.hypot(ax, ay), np.hypot(bx, by)
    da2, db2 = np.hypot(w - np.abs(ax), ay), np.hypot(w - np.abs(bx), by)
    return np.where(da < db, np.minimum(db - da, da2 - da), np.minimum(da - db, db2 - db))


def hide_mat(top, mid, belly, key, spots=True, frost=0.4):
    """Countershaded scales: dark sapphire back, aquatic flanks, pale belly; lateral line of bioluminescent
    spots.  'cryo' skin: frost bloom on the upper surfaces, white sparkles, spots turn ice-white."""
    kt, km, kb, ki, kg = rgb(top), rgb(mid), rgb(belly), rgb(ICE), rgb(GLOW)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, mid)
        if ctx.group == "up":
            base = np.broadcast_to(kt, (ctx.h, ctx.w, 3)).copy()
        elif ctx.group == "down":
            base = np.broadcast_to(kb, (ctx.h, ctx.w, 3)).copy()
        else:
            v = ctx.V[..., None]
            base = np.where(v < 0.55, mix(kt, km, np.clip(v / 0.55, 0, 1)), mix(km, kb, np.clip((v - 0.55) / 0.45, 0, 1)))
        t[..., :3] = base
        sz = 3
        row = iy // sz
        ox = ix + (row % 2)
        lx, ly = ox % sz, iy % sz
        cell = tex._hash(ox // sz, row, 5 + ctx.variant)
        t[..., :3] *= (0.9 + 0.18 * cell)[..., None]
        gap = (ly == 0) | ((lx == 0) & (ly < sz - 1))
        t[..., :3] = np.where(gap[..., None], t[..., :3] * 0.72, t[..., :3])
        hi = (ly == 1) & (lx == 1)
        t[..., :3] = np.where(hi[..., None], np.clip(t[..., :3] * 1.14 + 0.02, 0, 1), t[..., :3])
        cryo = ctx.alt == "cryo"
        if spots and ctx.group == "side" and ctx.h >= 8:
            sp = (np.abs(ctx.V - 0.42) < 0.55 / ctx.h) & ((ix + ctx.variant) % 4 == 1)
            t[..., :3] = np.where(sp[..., None], ki if cryo else kg, t[..., :3])
            t[..., 4] = np.where(sp, 1.0 if cryo else 0.85, t[..., 4])
        if cryo:
            if ctx.group == "side":
                amt = np.clip(1 - ctx.V * 1.4, 0, 1) * frost
            else:
                amt = np.full((ctx.h, ctx.w), frost * 1.5 if ctx.group == "up" else 0.0)
            t[..., :3] = mix(t[..., :3], ki, (amt * 0.75)[..., None])
            sparkle = (tex._hash(ix, iy, 77 + ctx.variant) > 0.92) & (amt > 0.12)
            t[..., :3] = np.where(sparkle[..., None], ki, t[..., :3])
            t[..., 4] = np.where(sparkle, 0.7, t[..., 4])
        return tex.grain(ctx, t, 0.045)
    return Mat(fn, key)


def membrane_mat(key, f0, f1, seed=0):
    """Translucent sail panel (blend).  f0/f1: top edge height as a fraction of the panel at its front/back."""
    deep, hi, rim = rgb("#0d3672"), rgb("#53b8ec"), rgb("#c6f3ff")
    ice_d, ice_h = rgb("#8fc6ec"), rgb("#f4fcff")

    def fn(ctx):
        ix, iy = tex.px(ctx)
        zf = ctx.U if ctx.face == "west" else 1 - ctx.U
        v = ctx.V
        top = 1 - (f0 + (f1 - f0) * zf)
        inside = v >= top
        y = np.clip((v - top) / np.maximum(1 - top, 1e-3), 0, 1)
        t = np.zeros((ctx.h, ctx.w, 5))
        if ctx.alt == "cryo":
            col = mix(ice_h, ice_d, (y * 0.8)[..., None])
            a = 0.55 + 0.3 * y
            e = _hex_edge(ix + 0.5 + seed * 3, iy + 0.5, 2.6)
            ln = e < 0.75
            col = np.where(ln[..., None], rgb("#ffffff"), col)
            a = np.where(ln, 0.95, a)
        else:
            col = mix(hi, deep, y[..., None])
            rip = 0.5 + 0.5 * np.sin((zf * 5 + v * 13 + seed * 0.7) * np.pi)
            col = np.clip(col * (0.86 + 0.22 * rip[..., None]), 0, 1)
            a = 0.3 + 0.32 * y
        rimm = inside & (v < top + 2.0 / ctx.h)
        col = np.where(rimm[..., None], rim, col)
        a = np.where(rimm, 0.85, a)
        t[..., :3] = col
        t[..., 3] = np.where(inside, a, 0.0)
        return t
    return Mat(fn, key, mode="blend", directional=True)


def veins_mat(key, f0, f1, seed=0):
    """Solid cut-out glowing vein network laid over a membrane (blend cannot glow).  Cryo: hex lattice."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        zf = ctx.U if ctx.face == "west" else 1 - ctx.U
        top = 1 - (f0 + (f1 - f0) * zf)
        inside = ctx.V >= top + 2.5 / ctx.h
        t = tex.tile(ctx, GLOW, 0.0, 0.0)
        if ctx.alt == "cryo":
            on = inside & (_hex_edge(ix + 0.5 + seed * 3, iy + 0.5, 2.6) < 0.55)
            col, g = "#f6fdff", 1.0
        else:
            l1 = ((ix * 2 + iy + seed) % 11) == 0
            l2 = ((iy - ix * 3 + seed * 5) % 17) == 0
            stem = (np.abs(ctx.U - 0.5) < 0.6 / ctx.w) & (iy % 2 == 0)
            on = inside & (l1 | l2 | stem) & (tex._hash(ix // 2, iy // 2, 41 + seed) < 0.86)
            col, g = GLOW, 0.95
        t[..., :3] = rgb(col)
        t[..., 3] = np.where(on, 1.0, 0.0)
        t[..., 4] = g
        return t
    return Mat(fn, key, directional=True)


def ice_plate_mat(key):
    """Hexagonal ice plate with concentric rings and six spokes (blend)."""
    def fn(ctx):
        u, v = ctx.U * 2 - 1, 1 - ctx.V * 2
        hn = np.maximum(np.abs(u) * 0.866 + np.abs(v) * 0.5, np.abs(v))
        inside = hn <= 0.97
        rings = np.abs(((hn * 2.6 + 0.15) % 1) - 0.5) > 0.36
        ang = np.arctan2(v, u)
        spoke = np.abs(np.sin(ang * 3 + np.pi / 2)) * np.hypot(u, v) < 0.09
        rim = hn > 0.84
        t = tex.tile(ctx, "#a9dcfa", 0.0)
        t[..., :3] = mix(rgb("#e8f8ff"), rgb("#7fbfee"), np.clip(hn, 0, 1)[..., None])
        ln = rings | spoke | rim
        t[..., :3] = np.where(ln[..., None], rgb("#ffffff"), t[..., :3])
        t[..., 3] = np.where(inside, np.where(ln, 0.95, 0.55), 0.0)
        return t
    return Mat(fn, key, mode="blend")


def fin_mat(key, base="#3c9ed6", edge="#c8f4ff"):
    """Transparent ray-finned membrane (blend); cryo skin turns it to frosted glass."""
    kb, ke = rgb(base), rgb(edge)

    def fn(ctx):
        ix, iy = tex.px(ctx)
        cryo = ctx.alt == "cryo"
        col = mix(kb, ke, (1 - ctx.V)[..., None] * 0.65)
        a = np.full((ctx.h, ctx.w), 0.36)
        rays = (ix % 3) == 1
        col = np.where(rays[..., None], col * 0.7 + 0.08, col)
        a = np.where(rays, 0.62, a)
        edg = (iy == 0) | (iy == ctx.h - 1)
        col = np.where(edg[..., None], ke, col)
        a = np.where(edg, 0.8, a)
        if cryo:
            col = mix(col, rgb(ICE), 0.6)
            a = np.clip(a + 0.2, 0, 1)
            fz = tex._hash(ix, iy, 13 + ctx.variant) > 0.88
            col = np.where(fz[..., None], 1.0, col)
            a = np.where(fz, 0.95, a)
        t = np.zeros((ctx.h, ctx.w, 5))
        t[..., :3] = np.clip(col, 0, 1)
        t[..., 3] = a
        return t
    return Mat(fn, key, mode="blend")


def teeth_mat(key, down=True, period=3):
    """Strip of conical teeth (cut-out) hanging from (down) or rising out of the gum line."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        v = ctx.V if down else 1 - ctx.V
        lx = (ix % period) + 0.5
        half = (1 - v) * period / 2 * 0.95
        inside = np.abs(lx - period / 2) <= half
        t = tex.tile(ctx, IVORY, 1.0, 0.0)
        t[..., :3] = mix(rgb("#f6f1e4"), rgb("#b8ab8a"), v[..., None] * 0.6)
        t[..., 3] = np.where(inside, 1.0, 0.0)
        return t
    return Mat(fn, key, directional=True)


# ----------------------------------------------------------------------------------------------- dragon model
def _sail_layout():
    out = []
    zs = np.linspace(-19, 33, NSAIL)
    for i, z in enumerate(zs):
        f = (i + 0.5) / NSAIL
        h = 9 + 23 * math.sin(math.pi * (0.06 + 0.88 * f)) ** 1.2
        out.append((float(z), h, -3 + 12 * f))
    return out


def build_model():
    m = Model(ACTOR, density=1.0, bounds=(34, 14, (0, 4, 1)), alts=("cryo",))
    hide = hide_mat(SAPH_D, AQUA, BELLY, "tide_hide")
    hide2 = hide_mat("#0e2a5c", "#2a7cba", "#b6dcec", "tide_hide2")
    head_m = hide_mat("#0c2552", "#2a77b6", "#c2e2ef", "tide_headhide", spots=False)
    belly = tex.alt(tex.banded(tex.speck(BELLY, 0.05, edge_dark=0.1), "#7fb2cc", every=3, width=1),
                    cryo=tex.banded(tex.speck("#d6eef8", 0.05, edge_dark=0.1), "#a9d6ee", every=3, width=1))
    spine = tex.alt(tex.vgrad("#b5f1ff", "#14396e", var=0.03, glow_top=0.8, glow_bottom=0.0, edge_dark=0.12),
                    cryo=tex.vgrad("#ffffff", "#8cc9f2", var=0.03, glow_top=1.0, glow_bottom=0.5, edge_dark=0.08))
    crys = tex.crystal("#d8f4ff", "#6fb3ea", "#ffffff", a=1.0, mode="solid", glow=0.35, facets=3.0)
    crys_b = tex.crystal("#cdeeff", "#5aa4e0", "#ffffff", a=0.62, mode="blend", facets=3.0)
    claw = tex.vgrad("#efe7d2", "#4c4638", var=0.03, edge_dark=0.1)
    finm = fin_mat("tide_fin")
    finm2 = fin_mat("tide_fin2", base="#2f8cc8", edge="#9fe9ff")
    eye = tex.eye_mat(iris=GLOW, sclera="#0a1832", pupil="#03060d", lid=SAPH_D, glow=1.0, slit=True, ring="#e9fbff")
    crest = tex.alt(tex.trimmed(tex.speck("#123a72", 0.05), GLOW, 1, 0, glow=0.8),
                    cryo=tex.trimmed(tex.speck("#cfe9fa", 0.05), "#ffffff", 1, 0, glow=1.0))
    teeth_d, teeth_u = teeth_mat("tide_teeth_d", True), teeth_mat("tide_teeth_u", False)
    fluid = tex.fluid("#2d7fd0", "#a6e4ff", a=0.5, flow=4)

    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 30, 18))
    body.box((0, 31, 20), (17, 18, 20), hide, mats={"down": belly})                  # pelvis z 10..30
    body.box((0, 40.2, 20), (7, 2.4, 20), hide2, variant=1)                         # dorsal ridge
    sp1 = m.bone("spine1", body, pivot=(0, 31, 10))
    sp1.box((0, 30, 1.5), (19, 21, 17.4), hide, variant=1, mats={"down": belly})    # mid torso z -7..10
    sp1.box((0, 24.5, 1.5), (21, 9, 15), hide2, variant=2, mats={"down": belly})    # flank bulge
    sp1.box((0, 40.6, 1.5), (7.5, 2.4, 17.4), hide2, variant=1)
    sp2 = m.bone("spine2", sp1, pivot=(0, 31, -7))
    sp2.box((0, 30, -14), (18, 22, 14.4), hide, variant=2, mats={"down": belly})    # chest z -21..-7
    sp2.box((0, 23.5, -14.5), (20, 9, 12), hide2, mats={"down": belly})             # keel / chest bulge
    sp2.box((0, 41.2, -14), (7, 2.4, 14), hide2, variant=2)
    sp2.locator("chest", (0, 26, -21))

    # neck: S-curve rising from the shoulders, small crest spines
    n1 = m.bone("neck1", sp2, pivot=(0, 33, -20))
    n1.box((0, 35, -25), (13, 14, 11), hide, variant=1, mats={"down": belly})
    n1.box((0, 43, -25), (1.2, 4, 1.2), spine, rot=(15, 0, 0))
    n2 = m.bone("neck2", n1, pivot=(0, 37, -29))
    n2.box((0, 39, -33), (10.5, 11, 9.5), hide, variant=2, mats={"down": belly})
    n2.box((0, 45.5, -33), (1.1, 3.4, 1.1), spine, rot=(15, 0, 0))
    n3 = m.bone("neck3", n2, pivot=(0, 40, -36))
    n3.box((0, 41.5, -39.5), (9, 9.5, 8.5), hide, mats={"down": belly})

    # head: long, low crocodilian skull with a terminal rosette and a nasal crest
    head = m.bone("head", n3, pivot=(0, 42, -42))
    head.box((0, 43, -48), (11, 9, 12), head_m)                                      # cranium
    head.box((0, 47.9, -47.5), (7, 1.6, 9), head_m, variant=1)                      # skull roof
    for sx in (1, -1):
        head.box((sx * 4.3, 47.2, -50), (2.6, 2, 6.5), head_m, variant=2)          # brow ridge
        head.plane("x", (sx * 5.55, 44.2, -50.2), 3.6, 2.6, eye, density=4)
        head.plane("x", (sx * 3.56, 36.4, -70), 30, 2.6, teeth_d, density=2)        # upper tooth row
        head.plane("x", (sx * 4.56, 36.5, -83), 5.6, 2.8, teeth_d, density=2, variant=1)
        head.box((sx * 3.8, 50.5, -45.5), (1.8, 5.2, 1.8), crys, rot=(28, 0, -14 * sx))   # ice brow horns
        head.box((sx * 2.6, 49.2, -42.8), (1.3, 3.4, 1.3), crys, rot=(40, 0, -10 * sx), variant=1)
    head.box((0, 40.2, -70), (7, 5, 32), head_m, variant=1)                          # snout
    head.box((0, 43.2, -62), (5, 1.6, 14), head_m, variant=2)                        # snout ridge
    head.box((0, 45.0, -58), (1.6, 3.2, 9), crest)                                   # nasal crest
    head.box((0, 40, -83), (9, 5.6, 6), head_m)                                      # rosette
    head.locator("mouth", (0, 37.5, -84))
    head.locator("snout", (0, 41, -86))
    hf = m.bone("headfin", head, pivot=(0, 44, -43))                                 # aquatic frills
    for sx in (1, -1):
        hf.plane("x", (sx * 6.2, 45, -39), 8, 7, finm, rot=(0, sx * 24, 0), pivot=(sx * 5.6, 45, -43), density=2)
        hf.plane("x", (sx * 6.0, 40.5, -40.5), 6, 4, finm2, rot=(0, sx * 30, 0), pivot=(sx * 5.4, 40.5, -43),
                 density=2, variant=1)
    jaw = m.bone("jaw", head, pivot=(0, 39.5, -47))
    jaw.box((0, 37, -51), (10, 5, 9), head_m, variant=2, mats={"down": belly})
    jaw.box((0, 35.8, -70), (6.4, 3.4, 30), head_m, variant=1, mats={"down": belly})
    jaw.box((0, 36, -82.5), (8, 3.6, 5), head_m, mats={"down": belly})
    for sx in (1, -1):
        jaw.plane("x", (sx * 3.1, 38.6, -70), 28, 2.2, teeth_u, density=2)
    jf = m.bone("jawfin", jaw, pivot=(0, 34.5, -50))
    jf.plane("x", (0, 31.5, -53), 10, 5, finm, density=2, variant=2)

    # forelimbs: strong, three-clawed, can brace / knuckle-walk; translucent forearm fin
    for s, sx in (("r", 1), ("l", -1)):
        a1 = m.bone(f"arm_{s}_1", sp2, pivot=(sx * 10, 28, -15))
        a1.box((sx * 11, 21.5, -13), (6.5, 15, 7.5), hide, rot=(-17, 0, 0), variant=1)
        a1.box((sx * 13.2, 27, -15), (2, 5.5, 2), crys, rot=(0, 45, -25 * sx))
        a2 = m.bone(f"arm_{s}_2", a1, pivot=(sx * 11.5, 15, -11))
        a2.box((sx * 11.5, 10, -13.5), (5.5, 12.5, 5.5), hide, rot=(26.5, 0, 0), variant=2)
        hd = m.bone(f"hand_{s}", a2, pivot=(sx * 11.5, 5, -16))
        hd.box((sx * 11.5, 2.4, -18), (6.4, 4, 6.5), hide2)
        hd.box((sx * (11.5 - 2.4), 1.5, -22.6), (1.9, 2.4, 5.2), claw, rot=(22, sx * 18, 0))
        hd.box((sx * 11.5, 1.3, -22.4), (1.5, 2, 3.8), claw, rot=(22, 0, 0))
        hd.box((sx * (11.5 + 2.3), 1.3, -22), (1.5, 2, 3.4), claw, rot=(22, -sx * 14, 0))
        hd.locator(f"hand_{s}", (sx * 11.5, 0.5, -19))
        af = m.bone(f"armfin_{s}", a2, pivot=(sx * 12.6, 14, -10))
        af.plane("x", (sx * 12.6, 10, -9.2), 5.5, 12, finm, rot=(26.5, 0, 0), pivot=(sx * 12.6, 10, -11.5), density=2)

        # hindlimbs: short, thick thigh, webbed feet
        l1 = m.bone(f"leg_{s}_1", body, pivot=(sx * 9.5, 29, 19))
        l1.box((sx * 11, 23, 17), (8, 16, 11), hide, rot=(22.6, 0, 0), variant=2)
        l2 = m.bone(f"leg_{s}_2", l1, pivot=(sx * 11, 17, 14))
        l2.box((sx * 11, 12, 17.5), (5.5, 13, 5.5), hide, rot=(-35, 0, 0), variant=1)
        l3 = m.bone(f"leg_{s}_3", l2, pivot=(sx * 11, 7, 21))
        l3.box((sx * 11, 4.2, 18.6), (4.5, 8.5, 4.5), hide2, rot=(40, 0, 0), variant=1)
        ft = m.bone(f"foot_{s}", l3, pivot=(sx * 11, 1.5, 17))
        ft.box((sx * 11, 1, 15), (7, 2, 7), hide2, variant=2)
        for dx, ry in ((-2.6, 14), (0, 0), (2.6, -14)):
            ft.box((sx * (11 + dx), 0.8, 10), (1.6, 1.6, 5.5), claw, rot=(0, ry * sx, 0))
        ft.locator(f"foot_{s}", (sx * 11, 0.3, 14))
        fw = m.bone(f"footweb_{s}", ft, pivot=(sx * 11, 1.2, 11.5))
        fw.plane("y", (sx * 11, 1.25, 9.6), 7.2, 4.6, finm2, density=2)

    # tail: deep paddle with tall dorsal and ventral fins (spinosaur neural spines)
    fin_t = [5, 7, 9, 12, 14, 16, 17, 17, 15, 11]
    fin_b = [0, 0, 0, 0, 4, 6, 8, 9, 9, 8]
    z, y = 29.0, 31.0
    par = body.name
    for i, L in enumerate(TAIL_L):
        f = i / 9
        w = 15 - 11.5 * f ** 0.85
        hh = 16 - 10.5 * f
        b = m.bone(TAIL[i], par, pivot=(0, y, z))
        b.box((0, y - 0.35, z + L / 2), (w, hh, L + 0.8), hide if i % 2 == 0 else hide2, variant=i % 3,
              mats={"down": belly})
        b.box((0, y + hh / 2 + fin_t[i] * 0.42, z + L * 0.5), (0.9, fin_t[i] * 0.84, 0.9), spine, rot=(14, 0, 0))
        if i in (5, 6, 7):
            for sx in (1, -1):
                b.box((sx * w / 2, y + hh * 0.25, z + L / 2), (1.4, 4, 1.4), crys, rot=(30, 0, -35 * sx), variant=i % 2)
        fb = m.bone(f"tailfin{i + 1}", b, pivot=(0, y + hh / 2 - 1, z))
        fb.plane("x", (0, y + hh / 2 + fin_t[i] / 2 - 1, z + L / 2), L + 0.6, fin_t[i], finm, density=2, variant=i % 3)
        if fin_b[i]:
            fb.plane("x", (0, y - hh / 2 - fin_b[i] / 2 + 0.8, z + L / 2), L, fin_b[i], finm2, density=2, variant=i % 3)
        if i == 9:
            fb.plane("x", (0, y - 0.5, z + L + 3.5), 8, hh + 14, finm, density=2, variant=1)
            b.locator("tail_tip", (0, y, z + L + 2))
        if i == 4:
            b.locator("tail_mid", (0, y, z + L / 2))
        par = b.name
        z += L
        y -= 0.7

    # dorsal sail: individually articulated spines, membranes, glowing veins, hidden hexagonal ice armour
    lay = _sail_layout()
    ice_m = ice_plate_mat("tide_iceplate")
    for i, (zz, h, rake) in enumerate(lay):
        parent = "spine2" if zz < -7 else ("spine1" if zz < 10 else ("body" if zz < 29 else TAIL[0]))
        base = 38.6 if parent == TAIL[0] else 40.0
        hp = lay[i - 1][1] if i > 0 else h * 0.7
        hn = lay[i + 1][1] if i < NSAIL - 1 else h * 0.7
        f0, f1 = min(1.0, ((hp + h) / 2 - 1) / (h - 1)), min(1.0, ((hn + h) / 2 - 1) / (h - 1))
        sb = m.bone(SAIL[i], parent, pivot=(0, base, zz), rot=(rake, 0, 0))
        sb.box((0, base + h / 2, zz), (1.7, h, 1.7), spine, variant=i % 3)
        for vx in (0.16, -0.16):
            sb.plane("x", (vx, base + (h - 1) / 2, zz), 5.2, h - 1, veins_mat(f"tide_veins{i}", f0, f1, i), density=2)
        mb = m.bone(f"sailm_{i + 1}", sb, pivot=(0, base, zz))
        mb.plane("x", (0, base + (h - 1) / 2, zz), 5.3, h - 1, membrane_mat(f"tide_memb{i}", f0, f1, i), density=2)
        ib = m.bone(f"sailice_{i + 1}", sb, pivot=(0, base + h * 0.5, zz))
        s1, s2 = min(7.0, 0.42 * h), min(5.5, 0.32 * h)
        for vx in (0.95, -0.95):
            ib.plane("x", (vx, base + h * 0.32, zz), s1, s1, ice_m, density=2)
            ib.plane("x", (vx * 1.1, base + h * 0.7, zz + 0.9), s2, s2, ice_m, density=2, variant=1)
        ib.box((0, base + h + 2.6, zz), (2.4, 6.5, 2.4), crys_b, rot=(0, 45, 0), variant=i % 3)
        if i == 1:
            sb.locator("sail_front", (0, base + h, zz))
        if i == 5:
            sb.locator("sail_peak", (0, base + h, zz))
        if i == 10:
            sb.locator("sail_back", (0, base + h, zz))
    for k in range(3):
        fb = m.bone(f"sailflow_{k + 1}", sp1, pivot=(0, 44 + k * 6, 0))
        for vx in (1.1, -1.1):
            fb.plane("x", (vx, 46 + k * 7, 0), 10, 7, fluid, density=1, variant=k)
    return m, {"sail": lay}


# ----------------------------------------------------------------------------------------------- animation helpers
def R(x=0.0, y=0.0, z=0.0):
    return (x, y, z)


def _cycle_keys(fn, length, phase, n=8):
    """Sample a gait function fn(p in 0..1) -> tuple into loop-safe keyframes; contact (p=0) at t = phase*length."""
    return {round(length * k / n, 4): fn(((k / n) - phase) % 1.0) for k in range(n + 1)}


def _hind(p):
    st = 0.6
    if p < st:
        q = p / st
        th, sh, mt, lift = 20 - 40 * q, 6 * q, 14 * q * q, 0.0
    else:
        q = (p - st) / (1 - st)
        s = math.sin(math.pi * q)
        th = -20 + 40 * (0.5 - 0.5 * math.cos(math.pi * q))
        sh, mt, lift = 6 * (1 - q) - 34 * s, 14 * (1 - q) - 8 * s, 18 * s
    return th, sh, mt, -(th + sh + mt) + lift


def _fore(p):
    st = 0.6
    if p < st:
        q = p / st
        up, fo, lift = 18 - 36 * q, -4 * q, 0.0
    else:
        q = (p - st) / (1 - st)
        s = math.sin(math.pi * q)
        up = -18 + 36 * (0.5 - 0.5 * math.cos(math.pi * q))
        fo, lift = -4 + 4 * q - 38 * s, 22 * s
    return up, fo, -(up + fo) + lift


def _keys_ch(keys, idx):
    return {t: R(v[idx]) for t, v in keys.items()}


TW = [1.0, 0.8, 0.62, 0.52, 0.46, 0.42, 0.38, 0.35, 0.32, 0.3]


def _turn(name, sgn):
    a = Anim(name, length=1.0, loop="hold")
    for b, amt, d in (("neck1", 12, 0.0), ("neck2", 10, 0.04), ("neck3", 8, 0.08), ("head", 10, 0.1)):
        a.rot(b, {0: R(), 0.12: R(y=3 * sgn), 0.42 + d: R(y=-amt * sgn), 0.78: R(y=-amt * 0.45 * sgn), 1.0: R()})
    a.rot("spine2", {0: R(), 0.3: R(y=-5 * sgn), 0.65: R(y=-7 * sgn), 1.0: R()})
    a.rot("spine1", {0: R(), 0.4: R(y=-3 * sgn), 0.75: R(y=-4 * sgn), 1.0: R()})
    a.rot("body", {0: R(), 0.5: R(z=-2.5 * sgn), 1.0: R()})
    for i, tb in enumerate(TAIL):
        d = 0.025 * i
        a.rot(tb, {0: R(), 0.2 + d: R(y=-1.5 * sgn), 0.6 + d: R(y=5 * sgn * TW[i] * 1.6), 0.85 + d * 0.4: R(y=2.5 * sgn), 1.0: R()})
    lead, trail = ("r", "l") if sgn > 0 else ("l", "r")
    for s, t0 in ((lead, 0.12), (trail, 0.38)):
        a.rot(f"arm_{s}_1", {0: R(), t0: R(), t0 + 0.16: R(16), t0 + 0.32: R(2), 1.0: R()})
        a.rot(f"arm_{s}_2", {0: R(), t0: R(), t0 + 0.16: R(-30), t0 + 0.32: R(), 1.0: R()})
    for s, t0 in ((trail, 0.45), (lead, 0.62)):
        a.rot(f"leg_{s}_1", {0: R(), t0: R(), t0 + 0.14: R(14), t0 + 0.28: R(3), 1.0: R()})
        a.rot(f"leg_{s}_2", {0: R(), t0: R(), t0 + 0.14: R(-26), t0 + 0.28: R(), 1.0: R()})
    a.sound(0.3, "step")
    a.sound(0.62, "step")
    return a


# ----------------------------------------------------------------------------------------------- animations
def build_anims(info=None):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    br = Anim("breathe", loop=True)
    br.rot("spine2", R(LIFE(0.9, 3.6)))
    br.rot("neck1", R(LIFE(-0.7, 3.6, 0.05)))
    br.pos("body", R(0, LIFE(0.3, 3.6, 0.1), 0))
    br.rot("jaw", R(LIFE(0.8, 3.6, 0.2, base=-0.9)))
    br.rot("headfin", R(LIFE(5, 1.9)))
    A.append(br)

    sl = Anim("sail_life", loop=True)   # ripple travelling front to back along the individually boned sail
    for i, b in enumerate(SAIL):
        sl.rot(b, R(LIFE(1.5, 3.0, -i * 0.06), 0, LIFE(1.1, 4.4, -i * 0.05)))
    A.append(sl)

    fl = Anim("fins_life", loop=True)
    for i in range(10):
        fl.rot(f"tailfin{i + 1}", R(0, 0, LIFE(3.5, 1.6, -i * 0.07)))
    sym(fl, "armfin_{s}", rot=R(0, LIFE(6, 1.4), 0))
    fl.rot("jawfin", R(LIFE(4, 2.0)))
    A.append(fl)

    fr = Anim("frost", loop=True)       # hex ice armour grows front -> back with the client variable v.frost
    for i in range(NSAIL):
        d = 0.55 * i / (NSAIL - 1)
        fr.scl(f"sailice_{i + 1}", M(f"math.clamp((v.frost - {d:.3f}) * 2.4, 0, 1)", lambda t: 1.0))
    A.append(fr)

    idle = Anim("idle", loop=True, length=6.0)
    wave(idle, TAIL, 1, 2.6, 6.0, lag=0.05, grow=1.08)
    idle.rot("neck2", R(S(1.6, 6.0, 0.15), S(3.5, 6.0, 0.3), 0))
    idle.rot("head", R(S(2.2, 3.0, 0.4), S(5, 6.0, 0.4), S(1.5, 6.0, 0.1)))
    idle.sound(2.4, "click")
    A.append(idle)

    # sinuous quadrupedal walk (lateral sequence LH, LF, RH, RF), girdles counter-rotate, tail sculls
    Lw = WALK_CYCLE
    mv = Anim("move", loop=True, length=Lw)
    ph = {"l_h": 0.0, "l_f": 0.25, "r_h": 0.5, "r_f": 0.75}
    for s in ("r", "l"):
        hk = _cycle_keys(_hind, Lw, ph[f"{s}_h"])
        for j, b in enumerate((f"leg_{s}_1", f"leg_{s}_2", f"leg_{s}_3", f"foot_{s}")):
            mv.rot(b, _keys_ch(hk, j))
        fk = _cycle_keys(_fore, Lw, ph[f"{s}_f"])
        for j, b in enumerate((f"arm_{s}_1", f"arm_{s}_2", f"hand_{s}")):
            mv.rot(b, _keys_ch(fk, j))
    mv.rot("body", R(0, S(2.5, Lw, -0.25), S(1.2, Lw, -0.25)))
    mv.rot("spine1", R(0, S(-1.5, Lw, -0.4), 0))
    mv.rot("spine2", R(0, S(3.0, Lw, -0.5), 0))
    mv.rot("head", R(S(1.2, Lw / 2, 0.1), S(-2.5, Lw, -0.6), 0))
    mv.pos("root", R(0, S(0.45, Lw / 2, 0.1), 0))
    wave(mv, TAIL, 1, 4.5, Lw, lag=0.07, grow=1.1)
    mv.sound(0.0, "step")
    mv.sound(0.8, "step")
    A.append(mv)

    # swimming: whole-body lateral wave driven from the tail, limbs tucked, sail streamlined
    P = SWIM_CYCLE
    sw = Anim("swim", loop=True, length=P)
    for k, (b, amp) in enumerate((("head", -2.5), ("neck3", -3), ("neck2", -3.5), ("neck1", -4), ("spine2", -4.5),
                                  ("spine1", -5), ("body", 6))):
        sw.rot(b, R(0, S(amp, P, -0.07 * k), 0))
    for i, tb in enumerate(TAIL):
        sw.rot(tb, R(0, S(7.5 * 1.05 ** i, P, -0.07 * (7 + i)), 0))
    sym(sw, "arm_{s}_1", rot=R(-58, 0, 10))
    sym(sw, "arm_{s}_2", rot=R(64, 0, 0))
    sym(sw, "hand_{s}", rot=R(30, 0, 0))
    sym(sw, "leg_{s}_1", rot=R(-62, 0, 6))
    sym(sw, "leg_{s}_2", rot=R(35, 0, 0))
    sym(sw, "leg_{s}_3", rot=R(-40, 0, 0))
    sym(sw, "foot_{s}", rot=R(-55, 0, 0))
    for b in SAIL:
        sw.rot(b, R(10))
    sw.rot("jaw", R(1.5))
    sw.rot("root", R(0, 0, S(3, P, -0.3)))
    sw.particle(0.0, "trail", "tail_tip")
    sw.particle(0.6, "trail", "tail_tip")
    sw.particle(0.3, "bubble", "chest")
    A.append(sw)

    A.append(_turn("turn_r", 1))
    A.append(_turn("turn_l", -1))

    # summoning: forms from water, coiled and compact, uncoils with a whole-body undulation
    ar = Anim("arrive", length=LENGTHS["arrive"], loop="hold")
    ar.scl("root", {0: (0.18, 0.18, 0.3), 0.45: (0.72, 0.68, 1.08), 0.8: (1.03, 1.03, 1.0), 1.0: 1.0})
    ar.pos("root", {0: R(0, -6, 0), 1.0: R()})
    for i, tb in enumerate(TAIL):
        ar.rot(tb, {0: R(y=22 * TW[i] * 1.4), 0.35 + i * 0.02: R(y=-10 * TW[i]), 0.7 + i * 0.02: R(y=4 * TW[i]), 1.0: R()})
    for b, amt in (("neck1", -16), ("neck2", -10), ("head", -8)):
        ar.rot(b, {0: R(-10, amt), 0.45: R(6, -amt * 0.6), 1.0: R()})
    ar.rot("jaw", {0: R(), 0.4: R(-22), 0.75: R(-6), 1.0: R()})
    for i, b in enumerate(SAIL):
        ar.rot(b, {0: R(40), 0.35 + i * 0.025: R(30), 0.75 + i * 0.015: R(-5), 1.0: R()})
    sym(ar, "arm_{s}_1", rot={0: R(-58, 0, 10), 0.6: R(-30, 0, 6), 1.0: R()})
    sym(ar, "arm_{s}_2", rot={0: R(64), 0.6: R(30), 1.0: R()})
    sym(ar, "leg_{s}_1", rot={0: R(-62), 0.6: R(-30), 1.0: R()})
    ar.sound(0.0, "emerge")
    ar.particle(0.1, "spray", "chest")
    ar.particle(0.45, "spray", "tail_mid")
    ar.particle(0.7, "mist", "sail_peak")
    A.append(ar)

    # landing from a swim: reach, impact (0.25 s), compress, rebound
    la = Anim("land", length=LENGTHS["land"], loop="hold")
    la.pos("body", {0: R(0, 6, 0), 0.25: R(0, -3, 0), 0.5: R(0, 0.6, 0), 0.8: R()})
    sym(la, "arm_{s}_1", rot={0: R(30, 0, 4), 0.25: R(8, 0, 8), 0.55: R(2, 0, 3), 0.8: R()})
    sym(la, "arm_{s}_2", rot={0: R(-10), 0.25: R(12), 0.8: R()})
    sym(la, "leg_{s}_1", rot={0: R(24), 0.25: R(10), 0.8: R()})
    la.rot("neck1", {0: R(6), 0.3: R(-8), 0.55: R(3), 0.8: R()})
    la.rot("head", {0: R(4), 0.3: R(-4), 0.8: R()})
    for i, b in enumerate(SAIL):
        la.rot(b, {0: R(12), 0.28 + i * 0.01: R(-6), 0.55: R(3), 0.8: R()})
    for i, tb in enumerate(TAIL):
        la.rot(tb, {0: R(-4 * TW[i]), 0.3 + i * 0.015: R(6 * TW[i]), 0.6: R(-2 * TW[i]), 0.8: R()})
    la.sound(0.2, "land")
    la.particle(0.25, "splash", "hand_r")
    la.particle(0.25, "splash", "hand_l")
    la.particle(0.3, "spray", "foot_r")
    A.append(la)

    # power: sail crystallisation -- brace, rear the chest, sail raised front-to-back, water runs over the sail
    pw = Anim("power", length=LENGTHS["power"], loop="hold")
    pw.pos("body", {0: R(), 0.3: R(0, -2, 0), 0.8: R(0, 1.2, 0), 1.5: R(0, 0.6, 0)})
    pw.rot("spine2", {0: R(), 0.3: R(-3), 0.85: R(6), 1.5: R(3)})
    pw.rot("neck1", {0: R(), 0.3: R(-6), 0.85: R(12), 1.5: R(6)})
    pw.rot("neck2", {0: R(), 0.85: R(6), 1.5: R(3)})
    pw.rot("head", {0: R(), 0.3: R(-4), 0.85: R(12, -6), 1.5: R(5, -4)})
    pw.rot("jaw", {0: R(), 0.6: R(), 0.9: R(-16), 1.2: R(-4), 1.5: R()})
    sym(pw, "arm_{s}_1", rot={0: R(), 0.3: R(6, 0, 10), 1.5: R(4, 0, 8)})
    sym(pw, "arm_{s}_2", rot={0: R(), 0.3: R(8), 1.5: R(5)})
    for i, b in enumerate(SAIL):
        d = i * 0.045
        pw.rot(b, {0: R(), 0.3: R(10), 0.45 + d: R(12), 0.7 + d: R(-6), 0.95 + d: R(-2), 1.5: R(-3)})
        pw.scl(b, {0: 1.0, 0.45 + d: 1.0, 0.75 + d: (1, 1.16, 1), 1.5: (1, 1.1, 1)})
    for i, tb in enumerate(TAIL):
        pw.rot(tb, {0: R(), 0.4 + i * 0.03: R(-3 * TW[i], 4 * TW[i]), 1.0 + i * 0.03: R(-1 * TW[i], -3 * TW[i]), 1.5: R()})
    for k in range(3):
        t0 = 0.2 + k * 0.22
        pw.pos(f"sailflow_{k + 1}", {0: R(0, 0, -26), t0: R(0, 0, -26), t0 + 0.7: R(0, 2, 34), 1.5: R(0, 2, 34)})
        pw.scl(f"sailflow_{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.12: 1.0, t0 + 0.55: 1.0, t0 + 0.7: 0.0, 1.5: 0.0})
    pw.sound(0.0, "sail")
    pw.particle(0.5, "flake", "sail_front")
    pw.particle(0.8, "glint", "sail_peak")
    pw.particle(1.1, "flake", "sail_back")
    pw.particle(1.2, "glint", "sail_front")
    A.append(pw)

    # attack_a: two-way tail sweep -- wind-up left, whip right (hit 0.5 s), backhand across (hit 1.05 s)
    h1, h2 = HITS["attack_a"]
    aa = Anim("attack_a", length=LENGTHS["attack_a"], loop="hold")
    for i, tb in enumerate(TAIL):
        w, d = TW[i], 0.022 * i
        aa.rot(tb, {0: R(), 0.28 + d: R(-4 * w, -22 * w), h1 + d: R(0, 21 * w), 0.72 + d: R(0, 15 * w),
                    h2 + d: R(0, -19 * w), 1.32: R(0, -5 * w), 1.5: R()})
    aa.rot("body", {0: R(), 0.28: R(0, -6), h1: R(0, 9, -2), 0.75: R(0, 6), h2: R(0, -7, 2), 1.32: R(0, -2), 1.5: R()})
    aa.pos("body", {0: R(), 0.28: R(0, -1.5, 0), h1: R(0, 0.5, 0), 0.8: R(0, -1, 0), h2: R(0, 0.4, 0), 1.5: R()})
    aa.rot("spine2", {0: R(), 0.28: R(0, 4), h1: R(0, -6), h2: R(0, 5), 1.5: R()})
    aa.rot("neck1", {0: R(), 0.3: R(-3, -6), h1: R(2, -10), h2: R(2, -4), 1.5: R()})
    aa.rot("head", {0: R(), 0.3: R(0, -8), h1: R(4, -10), h2: R(2, -6), 1.5: R()})
    aa.rot("jaw", {0: R(), h1 - 0.1: R(-10), h1 + 0.2: R(-2), h2: R(-8), 1.5: R()})
    sym(aa, "arm_{s}_1", rot={0: R(), 0.3: R(4, 0, 8), 1.3: R(4, 0, 8), 1.5: R()})
    sym(aa, "leg_{s}_1", rot={0: R(), 0.3: R(6, 0, 5), 1.3: R(6, 0, 5), 1.5: R()})
    for i, b in enumerate(SAIL):
        aa.rot(b, {0: R(), h1 + i * 0.015: R(4, 0, -4), h2 + i * 0.015: R(-2, 0, 4), 1.5: R()})
    aa.sound(0.28, "sweep")
    aa.sound(0.82, "sweep")
    aa.particle(h1 - 0.04, "spray", "tail_tip")
    aa.particle(h1 + 0.02, "spray", "tail_mid")
    aa.particle(h2 - 0.04, "spray", "tail_tip")
    A.append(aa)

    # attack_b: overhead tail strike -- brace, tail rises and curls, slams down and across (hit 0.9 s)
    hb = HITS["attack_b"][0]
    ab = Anim("attack_b", length=LENGTHS["attack_b"], loop="hold")
    wu = [0.9, 1.0, 1.0, 0.9, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
    for i, tb in enumerate(TAIL):
        w, d = TW[i], 0.018 * i
        ab.rot(tb, {0: R(), 0.55 + d: R(-9 * wu[i], -8 * w), hb + d * 0.5: R(7 * w, 20 * w), 1.15 + d: R(-2 * w, 14 * w),
                    1.7: R()})
    ab.pos("body", {0: R(), 0.5: R(0, -1.5, 0), 0.75: R(0, 1.8, 0), hb: R(0, -2.2, 0), 1.2: R(0, 0.3, 0), 1.7: R()})
    ab.rot("body", {0: R(), 0.55: R(-2, -7, 2), hb: R(2, 12, -3), 1.2: R(0, 9, -1), 1.7: R()})
    ab.rot("spine2", {0: R(), 0.5: R(-4, 3), hb: R(2, -10), 1.3: R(0, -6), 1.7: R()})
    ab.rot("neck1", {0: R(), 0.5: R(-6, -4), hb: R(4, -8), 1.7: R()})
    ab.rot("head", {0: R(), 0.5: R(-6, -6), hb: R(8, -10), 1.3: R(2, -6), 1.7: R()})
    ab.rot("jaw", {0: R(), hb - 0.15: R(-18), hb + 0.25: R(-4), 1.7: R()})
    sym(ab, "arm_{s}_1", rot={0: R(), 0.45: R(10, 0, 12), 1.4: R(8, 0, 10), 1.7: R()})
    sym(ab, "arm_{s}_2", rot={0: R(), 0.45: R(10), 1.4: R(8), 1.7: R()})
    for i, b in enumerate(SAIL):
        ab.rot(b, {0: R(), 0.55: R(14), hb + i * 0.012: R(-8, 0, -3), 1.3: R(-2), 1.7: R()})
    ab.sound(0.5, "swing")
    ab.particle(hb, "spray", "tail_tip")
    ab.particle(hb + 0.02, "splinter", "tail_tip")
    A.append(ab)

    # attack_c: sail flare -- the sail folds, then snaps upright and fans toward the target side (hit 0.45 s)
    hc = HITS["attack_c"][0]
    ac = Anim("attack_c", length=LENGTHS["attack_c"], loop="hold")
    ac.pos("body", {0: R(), 0.25: R(0, -1.5, 0), hc: R(0, 0.8, 0), 1.1: R()})
    ac.rot("body", {0: R(), 0.25: R(0, 0, 3), hc: R(0, 0, -5), 0.75: R(0, 0, -4), 1.1: R()})
    ac.rot("head", {0: R(), 0.25: R(-4, 4), hc: R(6, -12), 0.8: R(3, -8), 1.1: R()})
    ac.rot("jaw", {0: R(), 0.3: R(), hc: R(-14), 0.8: R(-4), 1.1: R()})
    for i, b in enumerate(SAIL):
        f = i / (NSAIL - 1)
        ac.rot(b, {0: R(), 0.22 + f * 0.05: R(14), hc + f * 0.05: R(-8 + 16 * f, 0, -3), 0.8: R(-4 + 8 * f), 1.1: R()})
        ac.scl(b, {0: 1.0, 0.22: (1, 0.94, 1), hc + f * 0.05: (1, 1.14, 1), 0.85: (1, 1.06, 1), 1.1: 1.0})
    ac.sound(0.2, "flare")
    ac.particle(hc, "glint", "sail_peak")
    ac.particle(hc, "flake", "sail_front")
    ac.particle(hc + 0.03, "flake", "sail_back")
    A.append(ac)

    # react: flinch away, sail snaps flat, tail lashes, recover
    re = Anim("react", length=LENGTHS["react"], loop="hold")
    re.rot("neck1", {0: R(), 0.1: R(8, 8), 0.35: R(-3, -3), 0.8: R()})
    re.rot("head", {0: R(), 0.1: R(12, 12, 4), 0.35: R(-4, -4), 0.8: R()})
    re.rot("jaw", {0: R(), 0.1: R(-18), 0.4: R(-4), 0.8: R()})
    re.rot("spine2", {0: R(), 0.12: R(0, 6, 3), 0.4: R(0, -2), 0.8: R()})
    re.pos("body", {0: R(), 0.12: R(0, 0.5, 1.5), 0.45: R(0, -0.4, -0.3), 0.8: R()})
    for i, b in enumerate(SAIL):
        re.rot(b, {0: R(), 0.1 + i * 0.01: R(14), 0.4: R(-3), 0.8: R()})
    for i, tb in enumerate(TAIL):
        re.rot(tb, {0: R(), 0.15 + i * 0.02: R(0, -9 * TW[i]), 0.45 + i * 0.02: R(0, 5 * TW[i]), 0.8: R()})
    re.sound(0.0, "hurt")
    re.particle(0.05, "spray", "chest")
    A.append(re)

    # rest: settled, belly near the ground, head lowered, tail curled, sail relaxed
    rs = Anim("rest", loop=True, length=6.0)
    rs.pos("body", R(0, -7, 0))
    sym(rs, "leg_{s}_1", rot=R(42, 0, 6))
    sym(rs, "leg_{s}_2", rot=R(-52, 0, 0))
    sym(rs, "leg_{s}_3", rot=R(14, 0, 0))
    sym(rs, "foot_{s}", rot=R(-4, 0, 0))
    sym(rs, "arm_{s}_1", rot=R(-28, 0, 8))
    sym(rs, "arm_{s}_2", rot=R(58, 0, 0))
    sym(rs, "hand_{s}", rot=R(-30, 0, 0))
    rs.rot("neck1", R(S(1.5, 6.0, 0, -14)))
    rs.rot("neck2", R(-8))
    rs.rot("head", R(S(1.2, 6.0, 0.2, -4), S(2.5, 6.0, 0.4), 0))
    for i, tb in enumerate(TAIL):
        rs.rot(tb, R(1.5, 7 * TW[i] * 1.3, 0))
    for i, b in enumerate(SAIL):
        rs.rot(b, R(8, 0, 3))
    A.append(rs)

    # depart: lifts its head, then dissolves into water -- tail tip first, sail back-to-front, collapses
    dp = Anim("depart", length=LENGTHS["depart"], loop="hold")
    dp.rot("neck1", {0: R(), 0.35: R(10), 1.0: R(4), 1.5: R(-10)})
    dp.rot("head", {0: R(), 0.35: R(8, -4), 1.0: R(2), 1.5: R(-6)})
    dp.rot("jaw", {0: R(), 0.25: R(-14), 0.6: R(-3), 1.6: R()})
    for i, tb in enumerate(TAIL):
        t0 = 0.3 + (9 - i) * 0.07
        dp.scl(tb, {0: 1.0, t0: 1.0, t0 + 0.22: (0.4, 0.15, 1.1), t0 + 0.3: 0.0})
        dp.rot(tb, {0: R(), t0: R(0, 4 * TW[i]), t0 + 0.3: R(6, -4 * TW[i])})
    for i, b in enumerate(SAIL):
        t0 = 0.4 + (NSAIL - 1 - i) * 0.045
        dp.scl(b, {0: 1.0, t0: (1, 1.08, 1), t0 + 0.25: (1.4, 0.0, 1.4)})
    sym(dp, "arm_{s}_1", rot={0: R(), 0.9: R(), 1.4: R(-20, 0, 25)})
    sym(dp, "leg_{s}_1", rot={0: R(), 0.9: R(), 1.4: R(25, 0, 20)})
    dp.pos("root", {0: R(), 0.9: R(), 1.6: R(0, -14, 0)})
    dp.scl("root", {0: 1.0, 1.0: 1.0, 1.35: (1.12, 0.55, 1.08), 1.6: (1.25, 0.0, 1.15)})
    dp.sound(0.0, "depart")
    dp.particle(0.45, "spray", "tail_mid")
    dp.particle(0.8, "mist", "sail_peak")
    dp.particle(1.1, "spray", "chest")
    dp.particle(1.35, "mist", "mouth")
    A.append(dp)

    # roar: inhale, neck arches up, jaws wide, sail fans fully, head shakes
    ro = Anim("roar", length=LENGTHS["roar"], loop="hold")
    ro.pos("body", {0: R(), 0.3: R(0, -1, 0), 0.6: R(0, 0.8, 0), 1.4: R()})
    ro.rot("neck1", {0: R(), 0.3: R(-6), 0.6: R(14, -4), 1.1: R(12, -4), 1.4: R()})
    ro.rot("neck2", {0: R(), 0.6: R(8), 1.1: R(7), 1.4: R()})
    ro.rot("head", {0: R(), 0.3: R(-8), 0.6: R(16, -10), 0.75: R(15, -12, 4), 0.9: R(16, -9, -4), 1.05: R(15, -11, 3),
                    1.2: R(10, -6), 1.4: R()})
    ro.rot("jaw", {0: R(), 0.3: R(-3), 0.55: R(-32), 1.1: R(-30), 1.3: R(-6), 1.4: R()})
    ro.rot("headfin", {0: R(), 0.55: R(-20), 1.1: R(-18), 1.4: R()})
    sym(ro, "arm_{s}_1", rot={0: R(), 0.35: R(6, 0, 12), 1.2: R(6, 0, 12), 1.4: R()})
    for i, b in enumerate(SAIL):
        f = i / (NSAIL - 1)
        ro.rot(b, {0: R(), 0.3: R(8), 0.55 + f * 0.1: R(-8 + 16 * f), 1.15: R(-6 + 12 * f), 1.4: R()})
        ro.scl(b, {0: 1.0, 0.55 + f * 0.1: (1, 1.14, 1), 1.15: (1, 1.12, 1), 1.4: 1.0})
    for i, tb in enumerate(TAIL):
        ro.rot(tb, {0: R(), 0.6 + i * 0.02: R(-4 * TW[i], 3 * TW[i]), 1.4: R()})
    ro.sound(0.3, "roar")
    ro.particle(0.55, "mist", "mouth")
    ro.particle(0.85, "mist", "mouth")
    ro.particle(0.7, "glint", "sail_peak")
    A.append(ro)
    return A


# ----------------------------------------------------------------------------------------------- constructs
def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def stream_model():
    """Flying ribbon of water (head at -Z) that spirals into the suspended mass."""
    m = Model("ed_tide_stream", density=1.0, bounds=(10, 5, (0, 0.5, 0)))
    water = tex.fluid("#2a78cc", "#b4ecff", a=0.55, flow=3)
    foam = tex.fluid("#bfefff", "#ffffff", a=0.7, flow=2)
    root = m.bone("root")
    par = root.name
    z = -14.0
    for k in range(7):
        b = m.bone(f"s{k + 1}", par, pivot=(0, 8, z))
        w = 6.5 * (1 - 0.1 * k)
        b.box((0, 8, z + 5), (w, w * 0.8, 10.5), water, variant=k % 3)
        b.plane("y", (0, 8 + w * 0.42, z + 5), w * 0.6, 10, foam, variant=k % 2)
        if k == 0:
            b.box((0, 8, z - 1.5), (w * 0.7, w * 0.6, 4), water, variant=1)
        par = b.name
        z += 10
    return m


def stream_anims():
    flow = Anim("flow", loop=True)
    names = [f"s{k + 1}" for k in range(7)]
    wave(flow, names, 1, 13, 1.0, lag=0.13, clock="q.life_time")
    for i, n in enumerate(names):
        flow.rot(n, R(LIFE(6, 1.4, -i * 0.11), S(13, 1.0, -i * 0.13, clock="q.life_time"), 0))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=0.4, loop="hold")
    form.scl("root", {0: (0.2, 0.2, 0.0), 0.4: 1.0})
    hold = Anim("hold", loop=True)
    fade = Anim("fade", length=0.4, loop="hold")
    fade.scl("root", {0: 1.0, 0.2: (0.6, 0.6, 1.5), 0.4: 0.0})
    return [flow, hidden, form, hold, fade]


def mass_model():
    """Immense suspended water formation (radius ~4.5 blocks at size 1): layered translucent shells, two
    tilted internal swirl currents, a bright core, bubbles and hanging drips."""
    m = Model("ed_tide_mass", density=0.3, bounds=(20, 18, (0, 0, 0)))
    water = tex.fluid("#1d5ca6", "#8fd8ff", a=0.3, flow=4)
    deep = tex.fluid("#0d3470", "#3f8fd8", a=0.34, flow=3)
    light = tex.fluid("#6fc8ff", "#e0f8ff", a=0.5, flow=2)
    core_m = tex.fluid("#bff0ff", "#ffffff", a=0.55, flow=2)
    root = m.bone("root")
    shell = m.bone("shell", root)
    for k, ry in enumerate((0, 45)):
        shell.box((0, 0, 0), (140, 72, 140), water, rot=(0, ry, 0), variant=k)
        shell.box((0, 48, 0), (100, 26, 100), deep, rot=(0, ry + 22.5, 0), variant=k)
        shell.box((0, -48, 0), (100, 26, 100), deep, rot=(0, ry + 22.5, 0), variant=k + 1)
    s1 = m.bone("swirl1", root, rot=(20, 0, 12))
    ring(s1, (0, 0, 0), 54, 12, (26, 12, 7), light, axis="y")
    s2 = m.bone("swirl2", root, rot=(-28, 0, -18))
    ring(s2, (0, 0, 0), 40, 10, (22, 9, 6), light, axis="y", variant=1)
    core = m.bone("core", root)
    core.box((0, 0, 0), (26, 26, 26), core_m, rot=(45, 45, 0))
    bub = m.bone("bubbles", root)
    rng = np.random.default_rng(7)
    for k in range(10):
        p = rng.uniform(-40, 40, 3)
        bub.box(tuple(p), (4, 4, 4), light, variant=k % 2)
    for k in range(4):
        a = k * 90 + 30
        x, z = 38 * math.cos(math.radians(a)), 38 * math.sin(math.radians(a))
        d = m.bone(f"drip{k + 1}", root, pivot=(x, -56, z))
        d.box((x, -70, z), (8, 30, 8), water, variant=k % 2)
        d.box((x, -90, z), (4, 14, 4), light, variant=k % 2)
    return m


def mass_anims():
    churn = Anim("churn", loop=True)
    churn.rot("swirl1", R(0, spin(80), 0))
    churn.rot("swirl2", R(0, spin(-120), 0))
    churn.rot("core", R(spin(40), spin(60), 0))
    churn.scl("shell", (LIFE(0.04, 2.3, 0, 1), LIFE(0.05, 1.9, 0.3, 1), LIFE(0.04, 2.7, 0.6, 1)))
    churn.pos("bubbles", R(0, M("math.mod(q.life_time*30, 40) - 20", lambda t: (t * 30) % 40 - 20), 0))
    churn.rot("bubbles", R(0, spin(25), 0))
    for k in range(4):
        churn.rot(f"drip{k + 1}", R(LIFE(6, 1.7, k * 0.2), 0, LIFE(5, 2.1, k * 0.3)))
        churn.scl(f"drip{k + 1}", (1, LIFE(0.15, 1.3, k * 0.25, 1), 1))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    gather = Anim("gather", length=1.0, loop="hold")
    gather.scl("root", {0: 0.05, 0.6: 1.12, 1.0: 1.0})
    gather.scl("swirl1", {0: 0.3, 1.0: 1.0})
    hold = Anim("hold", loop=True)
    hold.pos("root", R(0, LIFE(2, 3.0), 0))
    burst = Anim("burst", length=0.6, loop="hold")
    burst.scl("shell", {0: 1.0, 0.2: (1.18, 0.9, 1.18), 0.6: (1.05, 0.97, 1.05)})
    burst.scl("core", {0: 1.0, 0.15: 1.6, 0.6: 0.6})
    disperse = Anim("disperse", length=1.0, loop="hold")
    disperse.scl("root", {0: 1.0, 0.3: (1.2, 0.8, 1.2), 1.0: (1.6, 0.0, 1.6)})
    disperse.pos("root", {0: R(), 1.0: R(0, -50, 0)})
    return [churn, hidden, gather, hold, burst, disperse]


CUR_R = 64.0
CUR_N = 8
CUR_SWEEP = 160.0


def current_model(name, side):
    """Tidal current arc around a target group: radius 4 blocks at size 1, sweeping 160 degrees from the
    model front (-Z) toward +X (side=+1) or -X (side=-1).  Segment k: water w{k}, frozen slab i{k},
    spiral ice sp{k} (three twisted prisms + a core spike)."""
    m = Model(name, density=1.0, bounds=(20, 6, (0, 1, 0)))
    water = tex.fluid("#2a74c8", "#b8efff", a=0.55, flow=3)
    foam = tex.fluid("#cff4ff", "#ffffff", a=0.75, flow=2)
    ice = tex.crystal("#d8f2ff", "#6aaee6", "#ffffff", a=0.7, mode="blend", facets=3.0)
    ice2 = tex.crystal("#eefaff", "#8cc8f0", "#ffffff", a=0.8, mode="blend", facets=2.5)
    root = m.bone("root")
    seg = CUR_SWEEP / CUR_N
    chord = 2 * CUR_R * math.sin(math.radians(seg / 2)) + 1.5
    for k in range(CUR_N):
        th = math.radians(seg * (k + 0.5))
        p = (side * CUR_R * math.sin(th), 0.0, -CUR_R * math.cos(th))
        ry = -side * math.degrees(th)
        w = m.bone(f"w{k}", root, pivot=p, rot=(0, ry, 0))
        w.box((p[0], 5, p[2]), (chord, 9, 8), water, variant=k % 3)
        w.box((p[0], 9.5, p[2] + 1.5), (chord - 2, 3, 5), foam, variant=k % 2)
        i = m.bone(f"i{k}", root, pivot=p, rot=(0, ry, 0))
        i.box((p[0], 1.5, p[2]), (chord, 3, 12), ice, variant=k % 3)
        s = m.bone(f"sp{k}", root, pivot=p, rot=(0, ry, 0))
        for j in range(3):
            a = math.radians(j * 120 + k * 25)
            cx, cz = p[0] + 3.2 * math.cos(a), p[2] + 3.2 * math.sin(a)
            s.box((cx, 17, cz), (3.6, 34, 3.6), ice, rot=(0, j * 120 + k * 25, 16), pivot=(cx, 17, cz), variant=j)
        s.box((p[0], 20, p[2]), (4.4, 40, 4.4), ice2, rot=(0, 45, 0), variant=k % 2)
    return m


def current_anims():
    ks = range(CUR_N)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=0.8, loop="hold")
    flow = Anim("flow", loop=True, length=1.0)
    freeze = Anim("freeze", length=0.95, loop="hold")
    spiral = Anim("spiral", length=0.6, loop="hold")
    ice = Anim("ice", loop=True)
    rise = Anim("rise", length=0.8, loop="hold")
    shatter = Anim("shatter", length=0.35, loop="hold")
    for k in ks:
        t = k * 0.06
        form.scl(f"w{k}", {0: 0.0, t: 0.0, t + 0.15: (1, 1.35, 1), t + 0.3: 1.0})
        flow.pos(f"w{k}", R(0, S(1.6, 1.0, -k * 0.12), 0))
        flow.scl(f"w{k}", (1, S(0.12, 1.0, -k * 0.12, 1), 1))
        for an in (form, flow):
            an.scl(f"i{k}", 0.0)
            an.scl(f"sp{k}", 0.0)
        t = k * 0.08
        freeze.scl(f"w{k}", {0: 1.0, t: 1.0, t + 0.2: (0.7, 0.15, 1)})
        freeze.scl(f"i{k}", {0: 0.0, t: 0.0, t + 0.12: (1.1, 1.3, 1.1), t + 0.25: 1.0})
        freeze.scl(f"sp{k}", {0: 0.0, t + 0.08: 0.0, t + 0.35: (1, 0.42, 1)})
        spiral.scl(f"w{k}", 0.0)
        t = k * 0.025
        spiral.scl(f"sp{k}", {0: (1, 0.42, 1), t + 0.35: (1, 1.12, 1), t + 0.42: 1.0, 0.6: 1.0})
        spiral.rot(f"sp{k}", {0: R(), t + 0.4: R(0, 70), 0.6: R(0, 70)})
        ice.scl(f"w{k}", 0.0)
        ice.rot(f"sp{k}", R(0, 70, 0))
        rise.scl(f"w{k}", 0.0)
        rise.rot(f"sp{k}", {0: R(0, 70), 0.8: R(0, 250)})
        rise.pos(f"sp{k}", {0: R(), 0.2 + t: R(0, 4, 0), 0.8: R(0, 70, 0)})
        rise.scl(f"sp{k}", {0: 1.0, 0.3: (1, 1.2, 1), 0.8: (0.2, 0.6, 0.2)})
        rise.scl(f"i{k}", {0: 1.0, 0.5: 0.0})
        shatter.scl(f"w{k}", 0.0)
    shatter.scl("root", {0: 1.0, 0.1: 1.15, 0.35: 0.0})
    return [hidden, form, flow, freeze, spiral, ice, rise, shatter]


CROWN_R = 64.0
CROWN_N = 12


def _hexprism(bone, center, w, h, mat, lean, spin0=0.0, variant=0):
    for j in range(3):
        bone.box(center, (w, h, w * 0.58), mat, rot=(0, spin0 + j * 60, -lean), variant=(variant + j) % 3)


def crown_model():
    """Colossal crown of ice around the targets (radius 4 blocks at size 1).  Each of the 12 segments: band
    (with one draconic rune), leaning hexagonal main spike in two parts and two translucent side spikes, so
    it can fracture in three successive waves (a: side spikes, b: spike crowns, c: base + band)."""
    m = Model("ed_tide_crown", density=1.0, bounds=(24, 12, (0, 3, 0)))
    ice_s = tex.crystal("#e4f7ff", "#6fb2e8", "#ffffff", a=1.0, mode="solid", glow=0.3, facets=3.0)
    ice_t = tex.crystal("#f4fcff", "#9fd2f4", "#ffffff", a=1.0, mode="solid", glow=0.55, facets=2.5)
    ice_b = tex.crystal("#cdeeff", "#5aa4e0", "#ffffff", a=0.6, mode="blend", facets=3.0)
    band_base = tex.crystal("#bfe6fb", "#3f86c8", "#e8f8ff", a=1.0, mode="solid", glow=0.2, facets=4.0)
    root = m.bone("root")
    chord = 2 * CROWN_R * math.sin(math.radians(180 / CROWN_N)) + 1
    for k in range(CROWN_N):
        a = k * 360 / CROWN_N
        P = (CROWN_R * math.sin(math.radians(a)), 0.0, -CROWN_R * math.cos(math.radians(a)))
        seg = m.bone(f"seg{k}", root, pivot=P, rot=(0, -(90 + a), 0))     # local +X points to the centre
        c = m.bone(f"cr{k}_c", seg, pivot=P)
        b = m.bone(f"cr{k}_b", c, pivot=P)
        sa = m.bone(f"cr{k}_a", c, pivot=P)
        px, _, pz = P
        rune = tex.stamped(band_base, glyphs.DRACONIC[k % len(glyphs.DRACONIC)], "#e9fbff", glow=1.0,
                           key=f"crownrune{k % len(glyphs.DRACONIC)}")
        c.box((px, 3.5, pz), (9, 7, chord), band_base, mats={"west": rune, "east": rune}, variant=k % 2)
        l1, h1 = 12, 34
        _hexprism(c, (px + 17 * math.sin(math.radians(l1)), 17 * math.cos(math.radians(l1)), pz), 9, h1, ice_s, l1,
                  k * 17, k)
        top = (px + h1 * math.sin(math.radians(l1)), h1 * math.cos(math.radians(l1)), pz)
        l2, h2 = 18, 26 + (k % 2) * 8
        _hexprism(b, (top[0] + h2 / 2 * math.sin(math.radians(l2)), top[1] + h2 / 2 * math.cos(math.radians(l2)), pz),
                  6.5, h2, ice_t, l2, k * 23, k + 1)
        tip = (top[0] + h2 * math.sin(math.radians(l2)), top[1] + h2 * math.cos(math.radians(l2)), pz)
        b.box((tip[0] + 3 * math.sin(math.radians(24)), tip[1] + 3, pz), (3.2, 9, 3.2), ice_t, rot=(0, 45, -24))
        for dz in (-11, 11):
            sh = 20 + (k + (dz > 0)) % 3 * 4
            for j in range(2):
                sa.box((px - 3 + sh / 2 * math.sin(math.radians(6)), sh / 2, pz + dz), (4.6, sh, 2.8), ice_b,
                       rot=(0, j * 90 + 45, -6 - (dz > 0) * 4), variant=j)
    return m


def crown_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    asm = Anim("assemble", length=1.2, loop="hold")
    hold = Anim("hold", loop=True)
    f1 = Anim("frac1", length=0.5, loop="hold")
    f2 = Anim("frac2", length=0.5, loop="hold")
    f3 = Anim("frac3", length=0.6, loop="hold")
    for k in range(CROWN_N):
        t = k * 0.045
        asm.pos(f"cr{k}_c", {0: R(0, -40, 0), t: R(0, -40, 0), t + 0.35: R(0, 3, 0), t + 0.5: R()})
        asm.scl(f"cr{k}_c", {0: (0.6, 0.6, 0.6), t: (0.6, 0.6, 0.6), t + 0.35: 1.05, t + 0.5: 1.0})
        asm.scl(f"cr{k}_b", {0: (1, 0, 1), t + 0.3: (1, 0, 1), t + 0.55: (1, 1.12, 1), t + 0.68: 1.0})
        asm.scl(f"cr{k}_a", {0: 0.0, t + 0.4: 0.0, t + 0.62: 1.08, t + 0.7: 1.0})
        hold.scl(f"cr{k}_b", (1, LIFE(0.03, 1.6, k * 0.08, 1), 1))
        j = (k % 3) * 0.04
        f1.rot(f"cr{k}_a", {0: R(), 0.3 + j: R(0, 0, -45)})
        f1.scl(f"cr{k}_a", {0: 1.0, 0.1 + j: 1.1, 0.35 + j: 0.0})
        for an in (f2, f3):
            an.scl(f"cr{k}_a", 0.0)
        f2.rot(f"cr{k}_b", {0: R(), 0.3 + j: R(0, 0, -40)})
        f2.scl(f"cr{k}_b", {0: 1.0, 0.12 + j: 1.06, 0.4 + j: 0.0})
        f3.scl(f"cr{k}_b", 0.0)
        f3.rot(f"cr{k}_c", {0: R(), 0.35 + j: R(0, 0, -28)})
        f3.scl(f"cr{k}_c", {0: 1.0, 0.12 + j: 1.08, 0.5 + j: 0.0})
    return [hidden, asm, hold, f1, f2, f3]


def shard_model():
    """Sharp ice formation that flies (pointing -Z) from the crown toward an enemy."""
    m = Model("ed_tide_shard", density=2.0, bounds=(5, 3, (0, 0.5, 0)))
    ice = tex.crystal("#f0fbff", "#7fc0ee", "#ffffff", a=1.0, mode="solid", glow=0.5, facets=2.5)
    trail_m = tex.fluid("#bfeaff", "#ffffff", a=0.45, flow=2)
    root = m.bone("root")
    sp = m.bone("spin", root, pivot=(0, 8, 0))
    sp.box((0, 8, -2), (4.6, 4.6, 32), ice, rot=(0, 0, 45))
    sp.box((0, 8, -21), (2.6, 2.6, 9), ice, rot=(0, 0, 45), variant=1)
    for sx in (1, -1):
        sp.box((sx * 4.2, 9.6, 3), (2.6, 2.6, 20), ice, rot=(0, -sx * 8, 45), variant=1)
    tr = m.bone("trail", root, pivot=(0, 8, 14))
    tr.plane("x", (0, 8, 22), 22, 5, trail_m)
    tr.plane("y", (0, 8, 22), 5, 22, trail_m, variant=1)
    return m


def shard_anims():
    always = Anim("spin", loop=True)
    always.rot("spin", R(0, 0, spin(720)))
    always.scl("trail", (1, LIFE(0.2, 0.2, 0, 1), 1))
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    launch = Anim("launch", length=0.2, loop="hold")
    launch.scl("root", {0: 0.2, 0.15: 1.1, 0.2: 1.0})
    hit = Anim("hit", length=0.3, loop="hold")
    hit.scl("root", {0: 1.0, 0.08: 1.5, 0.3: 0.0})
    return [always, hidden, launch, hit]


def frozen_model():
    """Ice encasement around a frozen enemy: seven leaning crystals (translucent) grown from the ground."""
    m = Model("ed_tide_frozen", density=2.0, bounds=(4, 4, (0, 1, 0)))
    ice = tex.crystal("#d4f1ff", "#5aa4e0", "#ffffff", a=0.62, mode="blend", facets=2.5)
    root = m.bone("root")
    hs = [26, 20, 31, 18, 25, 22, 14]
    for k in range(7):
        a = k * 360 / 6 + 10 if k < 6 else 0
        r = 9.5 if k < 6 else 0
        b = m.bone(f"fr{k}", root, pivot=(0, 0, 0), rot=(0, a, 0))
        h = hs[k]
        lean = -16 if k < 6 else 0
        b.box((0, h / 2, -r), (6, h, 4.4), ice, rot=(lean, 0, 0), pivot=(0, 0, -r), variant=k % 3)
        b.box((0, h * 0.35, -r - 0.5), (4, h * 0.7, 6), ice, rot=(lean, 60, 0), pivot=(0, 0, -r), variant=(k + 1) % 3)
    return m


def frozen_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    enc = Anim("encase", length=0.5, loop="hold")
    hold = Anim("hold", loop=True)
    sh = Anim("shatter", length=0.35, loop="hold")
    for k in range(7):
        t = k * 0.04
        enc.scl(f"fr{k}", {0: (0.4, 0.0, 0.4), t: (0.4, 0.0, 0.4), t + 0.25: (1.05, 1.12, 1.05), t + 0.32: 1.0})
        hold.scl(f"fr{k}", (1, LIFE(0.02, 1.3, k * 0.1, 1), 1))
        sh.scl(f"fr{k}", {0: 1.0, 0.08: (1.25, 1.1, 1.25), 0.3: (1.6, 0.0, 1.6)})
    return [hidden, enc, hold, sh]


# ----------------------------------------------------------------------------------------------- sound
def _bubble_am(sig, rate=14.0, depth=0.45):
    lfo = sy.lowpass(np.abs(sy.noise(len(sig) / sy.SR)), rate)
    lfo = lfo / (np.max(np.abs(lfo)) + 1e-9)
    return sig * (1 - depth + depth * np.clip(lfo, 0, 1))


def _bellow(dur, f0, f1, bright=1.0):
    """Resonant, bubbling bellow (the dragon's base voice)."""
    v = sy.roar(dur, f0=f0, f1=f1, growl=11, rough=0.35, formant=(330 * bright, 820 * bright), breath=0.22, bend=0.3)
    v = _bubble_am(v, 16, 0.4)
    sub = sy.osc(sy.sweep(f0 * 0.5, f1 * 0.5, dur)) * sy.env(dur, 0.1 * dur, 0.2, 0.8, 0.3 * dur)
    return sy.norm(sy.lowpass(v, 2600) + 0.5 * sub)


def _clicks(dur, n=9, f=2400, accel=1.7):
    """Sonar-like click train that speeds up."""
    out = np.zeros(int(sy.SR * dur))
    gap, t = dur * 0.2, 0.01
    for _ in range(n):
        L = int(sy.SR * 0.014)
        tt = np.arange(L) / sy.SR
        c = (np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.0022) + 0.6 * np.sin(2 * np.pi * f * 0.37 * tt) * np.exp(-tt / 0.004))
        i = int(sy.SR * t)
        if i >= len(out):
            break
        out[i:i + L] += c[:len(out) - i]
        t += gap
        gap /= accel ** (1.0 / n) * 1.06
    return sy.norm(out)


def _groan(dur, f0=62, f1=48):
    """Deep bell-ice groan: inharmonic partials gliding down through hollow resonances."""
    t = sy.t_axis(dur)
    f = sy.sweep(f0, f1, dur, 0.7) * (1 + 0.012 * np.sin(2 * np.pi * 0.7 * t))
    out = np.zeros(len(t))
    for r, a in ((1, 1.0), (2.76, 0.5), (5.4, 0.32), (8.93, 0.16), (13.3, 0.08)):
        out += a * sy.osc(f * r, wave_="sine", phase=r)
    out = sy.formants(out, [(420, 220, 1.0), (1150, 320, 0.45), (2600, 600, 0.15)])
    return sy.norm(out * sy.env(dur, 0.25 * dur, 0.2, 0.85, 0.35 * dur))


def build_sounds(pack):
    def save(name, sig, rv=(1.2, 0.3), **kw):
        sy.save(pack, name, sy.reverb(sig, rv[0], rv[1]), **kw)

    save("ed_tide_emerge", sy.at(2.2, (0.0, sy.water(1.6, 50, 300) * 0.55), (0.05, sy.whoosh(0.8, 200, 1600) * 0.45),
                                 (0.25, _bellow(1.6, 70, 96) * 0.95), (1.1, _clicks(0.6, 7, 2600) * 0.3)), (1.6, 0.35),
         max_distance=72)
    save("ed_tide_click", sy.at(1.0, (0.0, _clicks(0.7, 8, 2300) * 0.8), (0.15, _clicks(0.5, 5, 1500) * 0.4),
                                (0.25, sy.bell(1400, 0.6, inharm=1.2) * 0.1)), (0.9, 0.3), volume=0.6, max_distance=40)
    step = sy.mixdown([sy.thump(0.5, 80, 34, 0.25), sy.water(0.4, 8, 400) * 0.35], [1.0, 0.6])
    save("ed_tide_step", step, (0.5, 0.15), volume=0.7, max_distance=40,
         variants=[sy.reverb(sy.pitch(step, 1.1), 0.5, 0.15), sy.reverb(sy.pitch(step, 0.9), 0.5, 0.15)])
    save("ed_tide_land", sy.at(1.3, (0.0, sy.thump(1.0, 90, 28, 0.5)), (0.0, sy.water(1.2, 60, 250) * 0.7),
                               (0.02, sy.whoosh(0.5, 1800, 300) * 0.3)), (1.2, 0.3), max_distance=64)
    save("ed_tide_sail", sy.at(2.0, (0.0, sy.water(1.8, 30, 600) * 0.32), (0.1, sy.shimmer(1.6, 2400, 26) * 0.45),
                               (0.3, _groan(1.5, 92, 70) * 0.6), (0.6, sy.crack(1.0, 7000, 22) * 0.35),
                               (0.9, sy.bell(1760, 1.0, inharm=1.25) * 0.28)), (1.8, 0.4), max_distance=72)
    save("ed_tide_sweep", sy.mixdown([sy.whoosh(0.8, 150, 1400), sy.water(0.9, 30, 350) * 0.5]), (0.8, 0.25),
         max_distance=56)
    save("ed_tide_swing", sy.whoosh(0.9, 90, 900), (0.8, 0.25), max_distance=56)
    save("ed_tide_flare", sy.at(1.1, (0.0, sy.whoosh(0.6, 400, 2600) * 0.6), (0.2, sy.crack(0.6, 7500, 16) * 0.5),
                                (0.22, sy.shimmer(0.8, 3000, 16) * 0.45), (0.25, sy.bell(2093, 0.8, inharm=1.3) * 0.25)),
         (1.2, 0.35), max_distance=64)
    save("ed_tide_roar", sy.at(2.6, (0.0, _bellow(2.3, 82, 58)), (0.15, _groan(2.2, 55, 44) * 0.7),
                               (0.3, sy.water(2.0, 40, 220) * 0.28), (1.2, sy.crack(1.0, 6500, 30) * 0.32),
                               (0.5, sy.bell(220, 1.8, inharm=1.4) * 0.3)), (2.2, 0.42), max_distance=96)
    save("ed_tide_hurt", sy.at(0.9, (0.0, _bellow(0.6, 120, 165, 1.2)), (0.1, _clicks(0.4, 5, 2900) * 0.4)),
         (0.8, 0.25), max_distance=48)
    dep = sy.at(2.2, (0.0, sy.lowpass(sy.water(2.0, 80, 200), 1600) * 0.7), (0.0, _groan(1.8, 60, 40) * 0.5),
                (0.6, sy.shimmer(1.4, 2200, 18)[::-1] * 0.3), (0.2, _bellow(1.0, 70, 52) * 0.4))
    save("ed_tide_depart", dep, (1.8, 0.4), max_distance=72)
    # constructs / spell beats
    save("ed_tide_currents", sy.at(2.0, (0.0, sy.wind(1.8, 200, 900) * 0.5), (0.0, sy.water(1.8, 40, 300) * 0.6),
                                   (0.1, sy.rumble(1.6, 60) * 0.3)), (1.4, 0.35), max_distance=64)
    save("ed_tide_mass", sy.at(2.4, (0.0, sy.rumble(2.2, 55) * 0.6), (0.0, sy.water(2.2, 60, 180) * 0.5),
                               (0.4, _groan(1.8, 70, 82) * 0.32)), (2.0, 0.4), max_distance=80)
    flow = sy.mixdown([sy.whoosh(1.0, 120, 800), sy.water(1.0, 40, 280) * 0.7])
    save("ed_tide_flow", flow, (1.0, 0.3), max_distance=56, variants=[sy.reverb(sy.pitch(flow, 1.12), 1.0, 0.3)])
    fz = sy.at(1.8, (0.0, sy.highpass(sy.noise(1.2), 3500) * sy.decay(1.2, 0.5) * 0.25), (0.05, sy.crack(0.6, 7000, 18) * 0.6),
               (0.35, sy.crack(0.6, 6000, 18) * 0.5), (0.65, sy.crack(0.6, 5200, 18) * 0.45),
               (0.1, _groan(1.5, 110, 88) * 0.4), (0.4, sy.bell(1568, 1.2, inharm=1.35) * 0.25))
    save("ed_tide_freeze", fz, (1.6, 0.35), max_distance=64)
    sp = sy.at(1.3, (0.0, sy.highpass(sy.creak(1.0, 320, 640), 600) * 0.45), (0.1, sy.crack(0.8, 6000, 20) * 0.5),
               (0.3, sy.shimmer(0.9, 2800, 14) * 0.4))
    save("ed_tide_spiral", sp, (1.2, 0.35), max_distance=56)
    cr = sy.at(2.0, (0.0, sy.rumble(1.6, 50) * 0.45), (0.0, sy.crack(1.2, 5000, 26) * 0.4),
               *[(0.12 * k, sy.bell(f, 1.2, inharm=1.3) * 0.22) for k, f in enumerate((587, 831, 1109, 1397, 1661))],
               (0.5, sy.shimmer(1.2, 2600, 20) * 0.35))
    save("ed_tide_crown", cr, (2.0, 0.42), max_distance=80)
    save("ed_tide_impact", sy.at(1.4, (0.0, sy.thump(1.2, 70, 24, 0.8)), (0.0, sy.crack(1.0, 5000, 30) * 0.6),
                                 (0.02, sy.water(1.0, 40, 260) * 0.5)), (1.6, 0.35), max_distance=80)
    frac = sy.at(1.3, (0.0, sy.crack(0.9, 5600, 36)), (0.0, sy.thump(0.6, 120, 50, 0.4) * 0.5),
                 (0.05, sy.bell(392, 1.1, inharm=1.45) * 0.35), (0.2, sy.shimmer(1.0, 3000, 18) * 0.35))
    save("ed_tide_fracture", frac, (1.4, 0.38), max_distance=72,
         variants=[sy.reverb(sy.pitch(frac, 1.15), 1.4, 0.38), sy.reverb(sy.pitch(frac, 0.88), 1.4, 0.38)])
    sh = sy.at(0.6, (0.0, sy.crack(0.4, 7000, 10)), (0.0, sy.pluck(2637, 0.4, 0.9) * 0.3))
    save("ed_tide_shatter", sh, (0.6, 0.2), volume=0.75, max_distance=40,
         variants=[sy.reverb(sy.pitch(sh, 1.2), 0.6, 0.2), sy.reverb(sy.pitch(sh, 0.85), 0.6, 0.2)])
    fin = sy.at(2.6, (0.0, sy.thump(1.6, 60, 20, 1.0)), (0.0, sy.rumble(2.2, 45) * 0.5), (0.05, sy.crack(1.6, 6000, 50) * 0.5),
                (0.2, sy.shimmer(2.0, 2400, 40) * 0.4), (0.3, _groan(2.0, 50, 38) * 0.4), (0.0, sy.water(1.6, 60, 220) * 0.4))
    save("ed_tide_finale", fin, (2.4, 0.45), max_distance=96)
    save("ed_tide_splash", sy.at(1.0, (0.0, sy.water(0.9, 50, 300)), (0.0, sy.thump(0.5, 110, 40, 0.2) * 0.5)),
         (0.9, 0.25), max_distance=56)


# ----------------------------------------------------------------------------------------------- build
def _controller():
    ctl = {}
    for k, names in STATES.items():
        spec = {"animations": list(names)}
        if names[0] == "power":
            spec["on_entry"] = ["v.frost_goal = 1.0;"]
        elif names[0] in ("hidden", "arrive", "depart"):
            spec["on_entry"] = ["v.frost_goal = 0.0;"]
        ctl[k] = spec
    return ctl


def build(pack):
    fx = particles(pack)
    fx.effect("ed_tide_spray", "drop", count=14, life=(0.5, 1.0), size=(0.14, 0.06), shape=("sphere", 0.6), speed=(3, 7),
              accel=(0, -12, 0), drag=0.6, colors=["#e6fbffff", "#6fc8f0ee", "#2a6fb000"], blend="blend")
    fx.effect("ed_tide_mist", "puff", count=8, life=(1.0, 1.8), size=(0.6, 1.6), shape=("sphere", 1.2), speed=(0.3, 1.0),
              accel=(0, 0.3, 0), drag=1.2, colors=["#cfeaffaa", "#8fc3e855", "#5f9ccf00"], blend="blend", spin=(360, 30))
    fx.effect("ed_tide_bubble", "ring", count=6, life=(0.8, 1.5), size=(0.08, 0.16), shape=("sphere", 1.0), speed=(0.2, 0.6),
              accel=(0, 1.2, 0), colors=["#bff4ffff", "#7fd8ff00"])
    fx.effect("ed_tide_flake", "flake", count=8, life=(1.0, 2.0), size=(0.13, 0.05), shape=("sphere", 1.4), speed=(0.2, 0.8),
              accel=(0, -0.6, 0), drag=1.0, colors=["#ffffffff", "#cfefffcc", "#9fd8ff00"], spin=(360, 90))
    fx.effect("ed_tide_splinter", "shard", count=12, life=(0.4, 0.9), size=(0.18, 0.06), shape=("sphere", 0.4),
              speed=(4, 9), accel=(0, -9, 0), drag=0.5, colors=["#ffffffff", "#bfe9ffff", "#6fb6ea00"], spin=(360, 400))
    fx.effect("ed_tide_frost_ring", "ringthin", count=1, life=(0.5, 0.6), size=(0.5, 6.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#bfe9ffcc", "#6fb6ea00"])
    fx.effect("ed_tide_splash", "drop", count=22, life=(0.6, 1.1), size=(0.2, 0.08), shape=("disc", 1.2), direction=(0, 1, 0),
              speed=(5, 10), accel=(0, -16, 0), drag=0.4, colors=["#f0fcffff", "#7fcff5ee", "#2a6fb000"], blend="blend")
    fx.effect("ed_tide_glint", "star", count=4, life=(0.3, 0.6), size=(0.25, 0.0), shape=("sphere", 1.0),
              colors=["#ffffffff", "#bff4ff00"], spin=(360, 180))
    fx.effect("ed_tide_trail", "drop", count=6, life=(0.4, 0.8), size=(0.12, 0.04), shape=("sphere", 0.8), speed=(0.5, 1.5),
              accel=(0, -6, 0), colors=["#dff8ffee", "#5fb8ee00"], blend="blend")
    fx.effect("ed_tide_frostline", "diamond", count=2, life=(0.25, 0.45), size=(0.24, 0.04), shape=("sphere", 0.25),
              speed=(0.2, 0.6), colors=["#ffffffff", "#9fe6ffff", "#4f9fe000"])
    fx.effect("ed_tide_shock", "ring", count=1, life=(0.6, 0.7), size=(1.0, 9.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#9fdcffcc", "#3f86c800"])
    fx.effect("ed_tide_rain", "drop", count=14, life=(0.7, 1.2), size=(0.1, 0.05), shape=("disc", 4.0), direction=(0, -1, 0),
              speed=(4, 8), accel=(0, -10, 0), colors=["#cfefffdd", "#5fa8e000"], blend="blend")
    fx.effect("ed_tide_rune", None, sprites=[f"rune{i}" for i in range(1, 7)], count=4, life=(0.9, 1.5), size=(0.22, 0.05),
              shape=("sphere", 1.0), speed=(0.2, 0.6), accel=(0, 1.0, 0), drag=0.5, colors=["#ffffffff", "#bfeaffff", "#6fb6ea00"])

    snd = {k: f"grimoire.ed_tide_{k}" for k in ("emerge", "click", "step", "land", "sail", "sweep", "swing", "flare", "roar",
                                                 "hurt", "depart")}
    prt = {k: f"grimoire:ed_tide_{k}" for k in ("spray", "mist", "bubble", "flake", "splinter", "splash", "glint", "trail")}

    m, info = build_model()
    anims = build_anims(info)
    pack.actor(ACTOR, m, anims, _controller(), always=ALWAYS, scale=SCALE, lifetime=LIFETIME,
               props={"frost": {"type": "float", "range": [0.0, 1.0], "default": 0.0, "client_sync": True}},
               init=["v.frost = 0.0;", "v.frost_goal = 0.0;"],
               pre_anim=["v.frost = v.frost + math.clamp(math.max(v.frost_goal, q.property('grimoire:frost')) - v.frost, "
                         "-q.delta_time * 0.7, q.delta_time * 0.7);"],
               visibility=[{"sailflow*": f"q.property('grimoire:state') == {STATE_IDS['power']}"}],
               sounds=snd, particles=prt, display="Abyssal Cryotitan", blend=0.25)

    st = Model  # noqa: F841 (keeps flake8 quiet about unused import patterns)
    a = stream_model()
    pack.actor("ed_tide_stream", a, stream_anims(), {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["fade"]}, always=["flow"],
               size_prop=True, lifetime=60, display="Tidal Stream", blend=0.1)
    ms = mass_model()
    pack.actor("ed_tide_mass", ms, mass_anims(), {0: ["hidden"], 1: ["gather"], 2: ["hold"], 3: ["burst"], 4: ["disperse"]},
               always=["churn"], size_prop=True, lifetime=60, display="Suspended Deep", blend=0.15)
    cw, ccw = current_model("ed_tide_current", 1), current_model("ed_tide_current_ccw", -1)
    ca = current_anims()
    pack.actor("ed_tide_current", cw, ca, {0: ["hidden"], 1: ["form"], 2: ["flow"], 3: ["freeze"], 4: ["spiral"], 5: ["ice"],
                                           6: ["rise"], 7: ["shatter"]},
               kinds=[ccw], size_prop=True, lifetime=60, display="Tidal Current", blend=0.1)
    cm = crown_model()
    cra = crown_anims()
    pack.actor("ed_tide_crown", cm, cra, {0: ["hidden"], 1: ["assemble"], 2: ["hold"], 3: ["frac1"], 4: ["frac2"], 5: ["frac3"]},
               size_prop=True, lifetime=60, display="Frozen Tidal Crown", blend=0.05)
    sm = shard_model()
    pack.actor("ed_tide_shard", sm, shard_anims(), {0: ["hidden"], 1: ["launch"], 2: ["hit"]}, always=["spin"],
               size_prop=True, lifetime=60, display="Ice Shard", blend=0.0)
    fm = frozen_model()
    fa = frozen_anims()
    pack.actor("ed_tide_frozen", fm, fa, {0: ["hidden"], 1: ["encase"], 2: ["hold"], 3: ["shatter"]},
               lifetime=60, display="Ice Encasement", blend=0.05)

    build_sounds(pack)

    # ---- previews
    by = {x.name: x for x in anims}
    tide = Anim("pv_tide")
    for i in range(NSAIL):
        tide.scl(f"sailice_{i + 1}", 0.0)
    br = (by["breathe"], 1.0)
    side, q3, top, back = (90, 6), (35, 18), (0, 80), (-145, 16)
    pack.preview("ed_tide_a", m, [[(by["idle"], 0.0), br, (tide, 0)], [(by["move"], 0.4), (tide, 0)],
                                  [(by["swim"], 0.3), (tide, 0)]], views=(side, q3, top), cell=(520, 360))
    pack.preview("ed_tide_b", m, [[(by["power"], 1.5), br], [(by["attack_c"], 0.45)], [(by["roar"], 0.8)]],
                 views=(side, q3, back), cell=(520, 360), skin="cryo")
    pack.preview("ed_tide_c", m, [[(by["attack_a"], 0.28), (tide, 0)], [(by["attack_a"], 0.5), (tide, 0)],
                                  [(by["attack_b"], 0.55)], [(by["attack_b"], 0.9)], [(by["rest"], 0.0), (tide, 0)],
                                  [(by["depart"], 1.1), (tide, 0)], [(by["turn_r"], 0.5), (tide, 0)],
                                  [(by["arrive"], 0.4), (tide, 0)]], views=(side, top), cell=(460, 300))
    cb = {x.name: x for x in cra}
    pack.preview("ed_tide_crown", cm, [(cb["hold"], 0.2), (cb["frac2"], 0.2)], views=((20, 22), (0, 70)), cell=(420, 360))
    cub = {x.name: x for x in ca}
    pack.preview("ed_tide_current", cw, [(cub["flow"], 0.3), (cub["ice"], 0.0)], views=((20, 25), (0, 80)), cell=(420, 320))
    pack.preview("ed_tide_props", ms, [None], views=((20, 15),), cell=(360, 360))
    pack.preview("ed_tide_props2", sm, [None], views=((60, 15),), cell=(300, 200))
    pack.preview("ed_tide_props3", fm, [(fa[2], 0)], views=((20, 15),), cell=(300, 300))
    pack.preview("ed_tide_props4", a, [None], views=((60, 25),), cell=(300, 200))
    print(f"    {ACTOR}: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}; crown {cm.cube_count()} cubes "
          f"{len(cm.order)} bones; current {cw.cube_count()} cubes")
