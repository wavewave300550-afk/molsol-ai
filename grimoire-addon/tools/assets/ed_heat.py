"""Heat Dragon -- `dragon_heat`, the Living Furnace (ED02 Thermal Tyrant; reused by ED05 / ED06).

A horned bipedal predator built on a Carnotaurus body plan: deep short skull with two thick brow
horns, thick neck, vestigial arms pressed to the chest, massive thighs, digitigrade three-toed feet,
horizontal back and a long stiff balancing tail.  Its heat is biological machinery: six gill-like
vent flaps per flank hinge open over glowing lamellae, twelve dorsal plates slide apart over a
glowing furnace spine (neural spines that rise like fins), a throat bellows pumps with every breath,
fissures between the scales light up (texture skins) and the horns glow.

Rendered scale
    SCALE = 1.85 (pass to pack.actor).  Model ~150 units nose->tail = ~17.3 blocks; hip joint 50 units
    = ~5.8 blocks; head top ~5.5 blocks (more when roaring).  Origin (0,0,0) = ground under the hips.
    The horn tips sit ~7.9 blocks in front of the origin, the tail tip ~9.6 blocks behind it.

Rig (bb space, front = -Z, units 1/16 block before scaling; pivots)
    root (0,0,0)
      body      (0,50,6)   pelvis; hip joints lie on its pivot axis so body pitch never moves the hips
        chest   (0,51,-3)  shoulders / furnace; carries neck, arms, plates 1-4, core_1
          ribs  (0,48,-15) ribcage + belly (scaled by breathing); vents vent_{r,l}_1..6 hinge at
                           x=+-11 on their front edges (ry opens, r positive / l negative)
          neck1 (0,54,-31) -> neck2 (0,57,-41) -> head (0,60,-49) -> jaw (0,55.5,-49.5)
                           head: horn_r (5,66,-54) / horn_l (-5,66,-54); neck1: throat (bellows, scaled)
          arm_{s}_1 (+-9.6,44,-29) -> arm_{s}_2 (+-10.6,38.5,-31)          (tiny vestigial arms)
          dplate_{s}_1..4 (hinged on the outer edge x=+-10, y=58.5), core_1 (0,58.5,-17)
        dplate_{s}_5..6, core_2 (0,58.5,7)
        thigh_{s} (+-12.5,50,6) -> shin_{s} (+-12.5,32,-4) -> meta_{s} (+-12.5,13,8)
                    -> toe_{s}_in / toe_{s}_mid / toe_{s}_out (ball at y=2, z=4; toes splay with ry)
        tail1..tail7 (0,52,18) ... (0,43.6,75), tip at z=83
    Locators: foot_r/foot_l (toe_mid), horn_r/horn_l (horn tips), mouth (head), core (chest),
    vent_r/vent_l (ribs).  Legs are driven by a 2-bone IK solver (leg_ik) so planted feet do not slide.

Locomotion speeds (script must move the actor at these, along its yaw)
    move   (run loop, 0.6 s):  RUN_SPEED  ~10.0 blocks/s     charge = same gait, head lowered
    walk   (stalk, 1.2 s):     WALK_SPEED ~3.53 blocks/s     arrive walks for ARRIVE_WALK s
    turn_l / turn_r (0.8 s loops): rotate yaw by TURN_RATE deg/s (r = yaw increasing)

Texture skins (actor.skin): 0 cool (dark red-black, dim fissures), 1 ignited (orange fissures,
glowing horns/vents), 2 white-hot (whole hide radiant).

Helpers in this module: ed_heat_shimmer (heat-shimmer wall that parts), ed_heat_wave (superheated
air front), ed_heat_glass (vitrified ground decal, skin 1 = cooled), ed_heat_lane (charge-lane
telegraph; float property grimoire:len = visible length in blocks, skin 1 = surge).
"""
import math

import numpy as np

from kit import synth as sy, tex
from kit.anim import LIFE, Anim
from kit.geo import Mat, Model, ring
from kit.parts import sym

from .a_fx_common import particles

ACTOR = "dragon_heat"
SCALE = 1.85
LIFETIME = 150

# ---------------------------------------------------------------- gait constants (mirrored in TS)
RUN_T, RUN_DUTY, RUN_SWEEP, RUN_LIFT = 0.6, 0.5, 26.0, 13.0
WALK_T, WALK_DUTY, WALK_SWEEP, WALK_LIFT = 1.2, 0.6, 22.0, 9.0
RUN_SPEED = RUN_SWEEP / 16 * SCALE / (RUN_T * RUN_DUTY)      # blocks / s
WALK_SPEED = WALK_SWEEP / 16 * SCALE / (WALK_T * WALK_DUTY)
TURN_T, TURN_RATE = 0.8, 225.0
ARRIVE_LEN, ARRIVE_WALK = 1.6, 1.2
IGNITE_LEN, IGNITE_ROAR = 1.6, 1.1
SKID_LEN = 0.7
POWER_LEN, POWER_OPEN = 1.4, 1.0
COOL_LEN = 1.2
DEPART_LEN = 2.0
ATTACK_A_LEN, ATTACK_A_HIT = 1.2, 0.55
ATTACK_B_LEN, ATTACK_B_HIT = 1.3, 0.6
REACT_LEN, ROAR_LEN = 0.8, 1.4

STATES = {0: ["hidden"], 1: ["arrive"], 2: ["idle"], 3: ["move"], 4: ["turn_l"], 5: ["turn_r"],
          6: ["attack_a"], 7: ["attack_b"], 8: ["power", "furnace"], 9: ["react"], 10: ["rest"],
          11: ["depart"], 12: ["ignite"], 13: ["charge"], 14: ["skid"], 15: ["pant"], 16: ["cool"],
          17: ["roar"], 18: ["walk"]}
STATE_IDS = {v[0]: k for k, v in STATES.items()}

NV, NP, NT = 6, 6, 7          # vents per flank, dorsal plate pairs, tail bones

# ---------------------------------------------------------------- materials
SK = {None: dict(fis="#6a1a0a", fg=0.2, gap="#120604", gg=0.0, warm=0.0),
      "ignited": dict(fis="#ff6c1c", fg=0.95, gap="#6a1a08", gg=0.28, warm=0.0),
      "whitehot": dict(fis="#fff6d2", fg=1.0, gap="#ffa040", gg=0.8, warm=0.14)}


def _t(ctx, col, glow, a=1.0):
    t = np.zeros((ctx.h, ctx.w, 5))
    t[..., :3] = col
    t[..., 3] = a
    t[..., 4] = glow
    return t


def _hide(base, dark, light, size=3, crack=1.0, key="hide"):
    """Pebbled theropod hide with a network of thermal fissures that light up per skin."""
    kb, kd, kl = tex.rgb(base), tex.rgb(dark), tex.rgb(light)

    def fn(ctx):
        P = SK[ctx.alt]
        ix, iy = tex.px(ctx)
        row = iy // size
        ox = ix + (row % 2) * ((size + 1) // 2)
        lx, ly = ox % size, iy % size
        cell = tex._hash(ox // size, row + 97 * ctx.variant, 7)
        col = kd + (kb - kd) * (0.45 + 0.55 * cell)[..., None]
        hi = (ly == 1) & (lx >= 1)
        col = np.where(hi[..., None], col * 0.6 + kl * 0.45, col)
        gap = (lx == 0) | (ly == 0)
        col = np.where(gap[..., None], tex.rgb(P["gap"]) if ctx.alt else col * 0.55, col)
        glow = np.where(gap, P["gg"], 0.0)
        n = tex.fbm(ix / 7.0 + ctx.variant * 9.3 + 3.1, iy / 7.0 + ctx.variant * 4.7, 11 + ctx.variant)
        fis = np.abs(n - 0.5) < 0.03 * crack
        col = np.where(fis[..., None], tex.rgb(P["fis"]), col)
        glow = np.where(fis, P["fg"], glow)
        if P["warm"]:
            body = ~fis & ~gap
            col = np.where(body[..., None], np.clip(col * 1.3 + np.array([0.2, 0.04, 0.0]), 0, 1), col)
            glow = np.where(body, P["warm"], glow)
        t = tex.grain(ctx, _t(ctx, col, glow), 0.05)
        return tex.edge(ctx, t, 0.1)
    return Mat(fn, f"edheat_{key}{base}{size}{crack}")


def _horn(level):
    """Keratin horn segment; level 0 (base) .. 3 (tip) glows hotter in the ignited skins."""
    def fn(ctx):
        ix, iy = tex.px(ctx)
        f = level / 3.0
        col = np.broadcast_to(tex.mix(tex.rgb("#2c1b14"), tex.rgb("#6e4c34"), f), (ctx.h, ctx.w, 3)).copy()
        ridge = (ix + 2 * iy) % 4 == 0
        col[ridge] *= 0.65
        glow = np.full((ctx.h, ctx.w), 0.03 * level)
        if ctx.alt == "ignited":
            col = tex.mix(col, tex.rgb("#ff8a2c"), 0.4 + 0.17 * level)
            col[ridge] = tex.rgb("#ffe0a0")
            glow[:] = 0.55 + 0.15 * level
        elif ctx.alt == "whitehot":
            col = tex.mix(col, tex.rgb("#fff3cf"), 0.62 + 0.12 * level)
            glow[:] = 0.88 + 0.04 * level
        return tex.grain(ctx, _t(ctx, col, glow), 0.04)
    return Mat(fn, f"edheat_horn{level}")


def _skinned(table, pattern, key):
    """Generic per-skin painter: table[alt] = (c1, c2, glow1, glow2); pattern(ctx) -> bool mask for c1."""
    def fn(ctx):
        c1, c2, g1, g2 = table[ctx.alt]
        m = pattern(ctx)
        col = np.where(m[..., None], tex.rgb(c1), tex.rgb(c2))
        glow = np.where(m, g1, g2)
        return tex.grain(ctx, _t(ctx, col, glow), 0.05)
    return Mat(fn, f"edheat_{key}")


def _vent_inner():
    tbl = {None: ("#4a0e06", "#160504", 0.3, 0.1), "ignited": ("#ffb040", "#c8340c", 1.0, 0.75),
           "whitehot": ("#ffffff", "#ffd27a", 1.0, 1.0)}
    return _skinned(tbl, lambda c: (tex.px(c)[1] % 2 == 0) & (tex.px(c)[0] > 0) & (tex.px(c)[0] < c.w - 1), "vent")


def _core():
    tbl = {None: ("#ff8a28", "#9a2a08", 0.9, 0.6), "ignited": ("#ffe6a0", "#ff7a1c", 1.0, 0.95),
           "whitehot": ("#ffffff", "#fff0c0", 1.0, 1.0)}
    return _skinned(tbl, lambda c: (tex.px(c)[1] + tex.px(c)[0]) % 3 != 0, "core")


def _bed():
    """Glowing furnace grate under the dorsal plates."""
    tbl = {None: ("#c4400e", "#3a0c06", 0.8, 0.2), "ignited": ("#ffc050", "#c8360c", 1.0, 0.7),
           "whitehot": ("#ffffff", "#ffb048", 1.0, 0.95)}
    return _skinned(tbl, lambda c: (tex.px(c)[0] % 4 == 0) | (tex.px(c)[1] % 5 == 0), "bed")


def _bellows():
    tbl = {None: ("#5a1a10", "#2a0c08", 0.12, 0.0), "ignited": ("#ff6a20", "#3a100a", 0.85, 0.05),
           "whitehot": ("#fff0c0", "#ff9a40", 1.0, 0.5)}
    return _skinned(tbl, lambda c: tex.px(c)[1] % 3 == 0, "bellows")


def _mouth():
    tbl = {None: ("#5a140c", "#3a0c08", 0.3, 0.15), "ignited": ("#ffb040", "#ff5a14", 1.0, 0.85),
           "whitehot": ("#ffffff", "#fff0c0", 1.0, 1.0)}
    return _skinned(tbl, lambda c: tex.px(c)[0] % 3 == 0, "mouth")


def _plate():
    """Basalt-dark dorsal armour with osteoderm pits; plate rims glow when the furnace is lit."""
    rim = {None: ("#4a1a0e", 0.08), "ignited": ("#ff7a2a", 0.85), "whitehot": ("#fff0c0", 1.0)}

    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 3.0 + ctx.variant * 5.1, iy / 3.0, 3)
        col = tex.mix(tex.rgb("#1c0c0a"), tex.rgb("#3e1a14"), n[..., None])
        pit = tex._hash(ix // 3, iy // 3 + ctx.variant * 13, 4) > 0.82
        col = np.where(pit[..., None], col * 0.5, col)
        d = np.minimum(np.minimum(ix, ctx.w - 1 - ix), np.minimum(iy, ctx.h - 1 - iy))
        rc, rg = rim[ctx.alt]
        edge = d == 0
        col = np.where(edge[..., None], tex.rgb(rc), col)
        glow = np.where(edge, rg, 0.15 if ctx.alt == "whitehot" else 0.0)
        return tex.grain(ctx, _t(ctx, col, glow), 0.05)
    return Mat(fn, "edheat_plate")


# ---------------------------------------------------------------- geometry helpers
def seg(b, p0, p1, w, h, mat, axis="y", grow=0.0, **kw):
    """Box spanning joint p0 -> p1 (both (x, y, z)); long axis 'y' (limbs) or 'z' (neck, tail)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    c = tuple((p0 + p1) / 2)
    d = p1 - p0
    L = float(np.linalg.norm(d)) + grow
    dy, dz = d[1], d[2]
    if axis == "z":
        if dz < 0:
            dy, dz = -dy, -dz
        a = math.degrees(math.atan2(-dy, dz))
        size = (w, h, L)
    else:
        if dy > 0:
            dy, dz = -dy, -dz
        a = math.degrees(math.atan2(-dz, -dy))
        size = (w, L, h)
    return b.box(c, size, mat, rot=(a, 0, 0), pivot=c, **kw)


# leg joints (y, z) in bind pose
HIP, KNEE0, ANK0, BALL0 = (50.0, 6.0), (32.0, -4.0), (13.0, 8.0), (2.0, 4.0)
LEG_X = 12.5
TAIL_J = [(52, 18), (51, 28), (49.8, 38), (48.3, 48), (46.8, 58), (45.2, 67), (43.6, 75), (42, 83)]


def build_model():
    m = Model(ACTOR, density=1.0, bounds=(30, 16, (0, 5, 0)), alts=("ignited", "whitehot"))
    hide = _hide("#3b1411", "#170806", "#5e2117", 3, 1.0, "body")
    limb = _hide("#33120f", "#140705", "#552015", 3, 0.8, "limb")
    belly = _hide("#5c2a1e", "#2a120c", "#7a3e2a", 4, 0.5, "belly")
    skull = _hide("#431713", "#180806", "#6a2a1c", 2, 1.2, "skull")
    plate, vent, core, bed = _plate(), _vent_inner(), _core(), _bed()
    horn = [_horn(i) for i in range(4)]
    throat, mouth = _bellows(), _mouth()
    tooth = tex.bone_mat("#efe4c8", "#b9a77f", pores=0.05)
    claw = tex.speck("#1b1210", 0.05, edge_dark=0.25)
    eye = tex.eye_mat(iris="#ffb21e", sclera="#2e0a05", pupil="#0d0302", lid="#2a0d09", glow=0.95, slit=True,
                      ring="#fff2a0")

    root = m.bone("root")
    body = m.bone("body", root, pivot=(0, 50, 6))
    body.box((0, 50, 8), (20, 17, 22), hide)                                  # pelvis
    body.box((0, 43, 9), (15, 4, 16), belly)
    body.plane("y", (0, 58.56, 7), 19, 16, bed, faces=("up",))
    for z in (0, 7, 14):
        for sx in (1, -1):
            body.box((sx * 10.3, 55.5, z), (1.6, 2.2, 3.2), plate, variant=z % 2)
    body.locator("tailroot", (0, 54, 20))

    chest = m.bone("chest", body, pivot=(0, 51, -3))
    chest.box((0, 52, -29), (18, 12, 8), hide, variant=1)                     # shoulder hump
    chest.box((0, 46.5, -31), (15, 11, 6), belly, variant=1)                  # pectoral keel
    chest.locator("core", (0, 62, -12))
    ribs = m.bone("ribs", chest, pivot=(0, 48, -15))
    ribs.box((0, 48, -15), (22, 21, 26), hide, variant=2)
    ribs.box((0, 38, -14), (17, 5, 22), belly)
    ribs.plane("y", (0, 58.56, -15.5), 21, 25, bed, faces=("up",), variant=1)
    ribs.locator("vent_r", (12.5, 47, -14)).locator("vent_l", (-12.5, 47, -14))
    for k in range(NV):
        zc = -25 + k * 4.4
        for s, sx in (("r", 1), ("l", -1)):
            ribs.plane("x", (sx * 11.03, 47, zc), 3.4, 12, vent, variant=k % 2)
            f = m.bone(f"vent_{s}_{k + 1}", ribs, pivot=(sx * 11, 47, zc - 2.0))
            x0 = 11.0 if sx > 0 else -11.9
            f.cube((x0, 40.5, zc - 2.0), (0.9, 13, 4.3), limb, variant=k % 3,
                   mats={("west" if sx > 0 else "east"): vent})
            f.cube((x0 + (0.9 if sx > 0 else -0.6), 51.0, zc - 1.0), (0.6, 1.4, 2.4), plate)   # flap stud

    # dorsal plates + furnace core
    for i in range(NP):
        zc = -29 + 8 * i
        par = chest if i < 4 else body
        for s, sx in (("r", 1), ("l", -1)):
            p = m.bone(f"dplate_{s}_{i + 1}", par, pivot=(sx * 10, 58.5, zc))
            x0 = 0.25 if sx > 0 else -10.55
            p.cube((x0, 58.3, zc - 3.9), (10.3, 3.0, 7.8), plate, variant=i % 2)
            for xo in (3.4, 7.4):
                p.box((sx * xo, 61.9, zc + (0.6 if xo > 4 else -0.6)), (1.8, 1.4, 3.6), plate, variant=1)
    for name, par, z0, z1 in (("core_1", chest, -33, -1), ("core_2", body, -1, 15)):
        zc = (z0 + z1) / 2
        c = m.bone(name, par, pivot=(0, 58.5, zc))
        c.box((0, 59.4, zc), (2.6, 1.8, z1 - z0), core)
        for z in np.arange(z0 + 2, z1 - 1, 4.0):
            c.box((0, 59.9, float(z)), (1.3, 2.8, 1.6), core, variant=1)                  # neural spine fins
            c.box((0, 58.9, float(z) + 2), (17, 0.8, 1.0), core, variant=2)               # glowing ribs

    # neck, throat bellows, head
    n1 = m.bone("neck1", chest, pivot=(0, 54, -31))
    seg(n1, (0, 54.5, -29), (0, 57, -42), 14, 15, hide, axis="z", grow=2)
    for zz in (-33, -38):
        for sx in (1, -1):
            n1.box((sx * 7.0, 58.5, zz), (1.4, 2, 3), plate, variant=1)
    thr = m.bone("throat", n1, pivot=(0, 50, -36))
    thr.box((0, 48.6, -41), (9, 5, 15), throat)
    n2 = m.bone("neck2", n1, pivot=(0, 57, -41))
    seg(n2, (0, 57, -40), (0, 59.5, -50), 12.5, 13.5, hide, axis="z", grow=2, variant=1)
    head = m.bone("head", n2, pivot=(0, 60, -49))
    head.box((0, 62, -55.5), (12, 10, 13), skull)                             # cranium
    head.box((0, 60.5, -64.5), (10.5, 9, 7), skull, variant=1)                # deep blunt snout
    head.box((0, 55.5, -58.5), (11, 3, 19), skull, variant=2)                 # maxilla
    head.box((0, 65.6, -63), (5, 1.6, 6), plate)                              # nasal rugosity
    head.box((0, 67.6, -57), (6, 1.4, 6), plate, variant=1)
    for sx in (1, -1):
        head.box((sx * 4.6, 66.8, -53.5), (3.6, 2.6, 6.2), skull, variant=1)  # brow ridge
        head.box((sx * 6.0, 59.5, -54), (1.2, 5, 9), skull, variant=2)        # jugal
        head.box((sx * 6.4, 63.2, -56), (0.6, 3, 4.2), eye, faces=("east",) if sx > 0 else ("west",))
        for k, z in enumerate(np.arange(-66.5, -50, 2.3)):
            head.box((sx * 5.05, 53.2, float(z)), (0.9, 1.9, 0.9), tooth, variant=k % 2)
    for x in (-3, -1, 1, 3):
        head.box((x, 53.3, -67.6), (0.9, 1.8, 0.9), tooth)
    head.plane("y", (0, 54.02, -58.5), 10, 18.5, mouth, faces=("down",))
    head.locator("mouth", (0, 55, -67))
    for s, sx in (("r", 1), ("l", -1)):
        h = m.bone(f"horn_{s}", head, pivot=(sx * 5, 66, -54), rot=(0, -12 * sx, 32 * sx))
        for k, (dx, sz) in enumerate(((3.0, 6.4), (7.2, 5.0), (10.6, 3.6), (13.4, 2.4), (15.3, 1.4))):
            h.box((sx * (5 + dx), 66, -54), (sz if k else 6.0, sz, sz), horn[min(k, 3)], variant=k // 4)
        h.locator(f"horn_{s}", (sx * 20.5, 66, -54))
    jaw = m.bone("jaw", head, pivot=(0, 55.5, -49.5))
    jaw.box((0, 52.6, -58), (9.8, 3.8, 17.5), skull, mats={"up": mouth})
    jaw.box((0, 51.6, -63.5), (8, 2.6, 6), skull, variant=1)
    for sx in (1, -1):
        for z in np.arange(-65, -51, 2.6):
            jaw.box((sx * 4.2, 55.1, float(z)), (0.8, 1.4, 0.8), tooth)

    # vestigial arms
    for s, sx in (("r", 1), ("l", -1)):
        a1 = m.bone(f"arm_{s}_1", chest, pivot=(sx * 9.6, 44, -29))
        seg(a1, (sx * 9.6, 44, -29), (sx * 10.6, 38.5, -31), 3.2, 3.6, limb)
        a2 = m.bone(f"arm_{s}_2", a1, pivot=(sx * 10.6, 38.5, -31))
        seg(a2, (sx * 10.6, 38.5, -31), (sx * 10.6, 35.2, -34.4), 2.6, 2.6, limb, variant=1)
        for k, xo in enumerate((-0.8, 0.0, 0.8)):
            a2.box((sx * 10.6 + xo, 34.4, -35.0), (0.6, 1.4, 0.7), claw)

    # legs
    for s, sx in (("r", 1), ("l", -1)):
        X = sx * LEG_X
        th = m.bone(f"thigh_{s}", body, pivot=(X, HIP[0], HIP[1]))
        seg(th, (X, HIP[0], HIP[1]), (X + sx * 0.5, KNEE0[0], KNEE0[1]), 10.5, 14, limb)
        th.box((X, 45.5, 7), (11.5, 11, 18), limb, variant=1)                 # drumstick muscle
        sh = m.bone(f"shin_{s}", th, pivot=(X, KNEE0[0], KNEE0[1]))
        seg(sh, (X, KNEE0[0], KNEE0[1]), (X, ANK0[0], ANK0[1]), 7.5, 8.5, limb, variant=2)
        seg(sh, (X, 31, -3), (X, 21, 2), 8.5, 10, limb, variant=1)            # calf
        mt = m.bone(f"meta_{s}", sh, pivot=(X, ANK0[0], ANK0[1]))
        seg(mt, (X, ANK0[0], ANK0[1]), (X, BALL0[0], BALL0[1]), 5.5, 5, limb)
        mt.box((X - sx * 2.6, 8, 9.6), (1.2, 1.2, 2.6), claw)                 # dewclaw spur
        for name, xo, ry in (("in", -1.9, 15), ("mid", 0.0, 0), ("out", 1.9, -15)):
            px = X + sx * xo
            to = m.bone(f"toe_{s}_{name}", mt, pivot=(px, BALL0[0], BALL0[1] + 0.5), rot=(0, ry * sx, 0))
            ln = 12 if name == "mid" else 9.5
            to.box((px, 1.3, BALL0[1] + 0.5 - ln / 2), (3.2 if name == "mid" else 2.6, 2.6, ln), limb, variant=1)
            to.box((px, 1.0, BALL0[1] + 0.5 - ln - 1.1), (2.0, 2.0, 2.6), claw)
            if name == "mid":
                to.locator(f"foot_{s}", (px, 0.5, -1))

    # tail
    par = body
    W = [16, 14, 12, 10, 8, 6, 4.5]
    H = [15, 13, 11, 9, 7.5, 6, 4.5]
    for i in range(NT):
        (y0, z0), (y1, z1) = TAIL_J[i], TAIL_J[i + 1]
        tb = m.bone(f"tail{i + 1}", par, pivot=(0, y0, z0))
        seg(tb, (0, y0, z0), (0, y1, z1), W[i], H[i], hide if i < 4 else limb, axis="z", grow=2, variant=i % 3)
        if i < 5:
            tb.box((0, (y0 + y1) / 2 + H[i] / 2 + 0.5, (z0 + z1) / 2), (2.2, 1.6, 4.5), plate, variant=i % 2)
        if i < 3:
            for sx in (1, -1):
                tb.box((sx * (W[i] / 2 + 0.3), (y0 + y1) / 2 + 2, (z0 + z1) / 2), (1.4, 2, 3), plate)
        par = tb
    return m, {"vents": NV, "plates": NP, "tail": NT}


# ---------------------------------------------------------------- leg IK
def _ang(p, c):
    """World angle of the vector p -> c in the YZ plane: 0 = straight down, + = toward the front (-Z)."""
    return math.degrees(math.atan2(-(c[1] - p[1]), -(c[0] - p[0])))


L1 = math.dist(HIP, KNEE0)
L2 = math.dist(KNEE0, ANK0)
L3 = math.dist(ANK0, BALL0)
A1_0, A2_0, A3_0 = _ang(HIP, KNEE0), _ang(KNEE0, ANK0), _ang(ANK0, BALL0)


def leg_ik(by, bz, a3, bob=0.0, hz=0.0, pitch=0.0, toe=0.0):
    """Local rx of thigh, shin, meta, toes so the ball of the foot sits at (by, bz) (root space) with the
    metatarsus at world angle a3; hips displaced by body pos (bob, hz) and pitched by body rx."""
    hy, hzz = HIP[0] + bob, HIP[1] + hz
    r3 = math.radians(a3)
    ay, az = by + L3 * math.cos(r3), bz + L3 * math.sin(r3)
    dy, dz = ay - hy, az - hzz
    D = min(max(math.hypot(dy, dz), abs(L1 - L2) + 0.05), L1 + L2 - 0.05)
    a_ha = math.degrees(math.atan2(-dz, -dy))
    alpha = math.degrees(math.acos(max(-1.0, min(1.0, (L1 * L1 + D * D - L2 * L2) / (2 * L1 * D)))))
    a1 = a_ha + alpha
    ky, kz = hy - L1 * math.cos(math.radians(a1)), hzz - L1 * math.sin(math.radians(a1))
    a2 = math.degrees(math.atan2(-(az - kz), -(ay - ky)))
    d1, d2, d3 = a1 - A1_0, a2 - A2_0, a3 - A3_0
    return d1 - pitch, d2 - d1, d3 - d2, toe - d3


def sm(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def gait_foot(ph, duty, sweep, lift, zc=4.0, a3s=(10.0, 34.0), a3w=-36.0, curl=-30.0, splay=(10.0, -4.0)):
    """(by, bz, a3, toe, splay) for a foot at gait phase ph (0 = foot strike)."""
    zf, zb = zc - sweep / 2, zc + sweep / 2
    if ph < duty:
        f = ph / duty
        return (2.0, zf + (zb - zf) * f, a3s[0] + (a3s[1] - a3s[0]) * f, 0.0, splay[0])
    s = (ph - duty) / (1 - duty)
    by = 2.0 + lift * math.sin(math.pi * s)
    bz = zb + (zf - zb) * sm(s)
    a3 = a3s[1] + (a3w - a3s[1]) * sm(s / 0.5) if s < 0.5 else a3w + (a3s[0] - a3w) * sm((s - 0.5) / 0.5)
    return (by, bz, a3, curl * math.sin(math.pi * s), splay[0] + (splay[1] - splay[0]) * math.sin(math.pi * s))


STAND = (2.0, 4.0, A3_0, 0.0, 6.0)


def kf(t, keys):
    """Smoothstep interpolation of scalars or tuples between keyframes {time: value}."""
    ts = sorted(keys)
    if t <= ts[0]:
        return keys[ts[0]]
    if t >= ts[-1]:
        return keys[ts[-1]]
    for a, b in zip(ts, ts[1:]):
        if a <= t <= b:
            f = sm((t - a) / (b - a))
            va, vb = keys[a], keys[b]
            if isinstance(va, tuple):
                return tuple(x + (y - x) * f for x, y in zip(va, vb))
            return va + (vb - va) * f
    return keys[ts[-1]]


# ---------------------------------------------------------------- pose builder + baking
def pose(bob=0.0, hz=0.0, pitch=0.0, yaw=0.0, roll=0.0, chest=(0, 0, 0), neck1=(0, 0, 0), neck2=(0, 0, 0),
         head=(0, 0, 0), jaw=0.0, throat=1.0, ribs=1.0, vents=0.0, plates=0.0, slide=0.0, core=0.0, core_s=1.0,
         arms=((0, 0), (0, 0)), tail=None, legs=None, root_pos=(0, 0, 0), root_scl=(1, 1, 1), root_rot=(0, 0, 0),
         plate_drop=None):
    P = {}

    def put(b, ch, v):
        P.setdefault(b, {})[ch] = tuple(float(x) for x in v)

    put("root", "pos", root_pos)
    put("root", "scl", root_scl)
    put("root", "rot", root_rot)
    put("body", "pos", (0, bob, hz))
    put("body", "rot", (pitch, yaw, roll))
    put("chest", "rot", chest)
    put("neck1", "rot", neck1)
    put("neck2", "rot", neck2)
    put("head", "rot", head)
    put("jaw", "rot", (jaw, 0, 0))
    put("ribs", "scl", (ribs, 1 + (ribs - 1) * 1.15, 1 + (ribs - 1) * 0.35))
    put("throat", "scl", (1 + (throat - 1) * 0.5, throat, 1 + (throat - 1) * 0.3))
    for k in range(NV):
        a = vents[k] if isinstance(vents, (list, tuple)) else vents
        put(f"vent_r_{k + 1}", "rot", (0, a, 0))
        put(f"vent_l_{k + 1}", "rot", (0, -a, 0))
    for i in range(NP):
        a = plates[i] if isinstance(plates, (list, tuple)) else plates
        sl = slide[i] if isinstance(slide, (list, tuple)) else slide
        dy = 0.0
        if plate_drop is not None:
            dx, dy, dr = plate_drop[i]
            sl, a = sl + dx, a + dr
        put(f"dplate_r_{i + 1}", "rot", (0, 0, -a))
        put(f"dplate_l_{i + 1}", "rot", (0, 0, a))
        put(f"dplate_r_{i + 1}", "pos", (sl, dy, 0))
        put(f"dplate_l_{i + 1}", "pos", (-sl, dy, 0))
    for c in ("core_1", "core_2"):
        put(c, "pos", (0, core, 0))
        put(c, "scl", (1 + (core_s - 1) * 0.3, core_s, 1))
    (rx, rz), (lx, lz) = arms
    put("arm_r_1", "rot", (rx, 0, rz))
    put("arm_l_1", "rot", (lx, 0, -lz))
    put("arm_r_2", "rot", (rx * 0.7, 0, 0))
    put("arm_l_2", "rot", (lx * 0.7, 0, 0))
    tails = tail if isinstance(tail, list) else [tail or (0, 0)] * NT
    for i, (tx, ty) in enumerate(tails):
        put(f"tail{i + 1}", "rot", (tx, ty, 0))
    r, l = legs if legs is not None else (STAND, STAND)
    for s, f, sg in (("r", r, 1), ("l", l, -1)):
        th, sh, me, to = leg_ik(f[0], f[1], f[2], bob, hz, pitch, f[3])
        put(f"thigh_{s}", "rot", (th, 0, 0))
        put(f"shin_{s}", "rot", (sh, 0, 0))
        put(f"meta_{s}", "rot", (me, 0, 0))
        put(f"toe_{s}_in", "rot", (to, sg * f[4], 0))
        put(f"toe_{s}_mid", "rot", (to, 0, 0))
        put(f"toe_{s}_out", "rot", (to, -sg * f[4], 0))
    return P


IDENT = {"rot": (0, 0, 0), "pos": (0, 0, 0), "scl": (1, 1, 1)}


def bake(anim, fn, length, dt=0.05, tol=0.08):
    """Sample fn(t) -> {bone: {channel: xyz}} into linear keyframes (identical in preview and game)."""
    n = max(2, int(round(length / dt)))
    tracks = {}
    for i in range(n + 1):
        t = round(length * i / n, 4)
        for b, chs in fn(t).items():
            for ch, v in chs.items():
                tracks.setdefault((b, ch), {})[t] = v
    for (b, ch), keys in tracks.items():
        ts = sorted(keys)
        vals = [keys[t] for t in ts]
        if all(max(abs(a - c) for a, c in zip(v, vals[0])) < 1e-3 for v in vals):
            if max(abs(a - c) for a, c in zip(vals[0], IDENT[ch])) > 1e-3:
                getattr(anim, ch)(b, tuple(round(x, 3) for x in vals[0]))
            continue
        keep = [0]
        for j in range(1, len(ts) - 1):
            a, c = keep[-1], j + 1
            f = (ts[j] - ts[a]) / (ts[c] - ts[a])
            err = max(abs(vals[a][k] + (vals[c][k] - vals[a][k]) * f - vals[j][k]) for k in range(3))
            if err > tol:
                keep.append(j)
        keep.append(len(ts) - 1)
        getattr(anim, ch)(b, {ts[j]: tuple(round(x, 3) for x in vals[j]) for j in keep}, smooth=False)
    return anim


# ---------------------------------------------------------------- animations
def _run_pose(t, charge=False):
    ph = (t / RUN_T) % 1.0
    r = gait_foot(ph, RUN_DUTY, RUN_SWEEP, RUN_LIFT)
    l = gait_foot((ph + 0.5) % 1.0, RUN_DUTY, RUN_SWEEP, RUN_LIFT)
    sw, cw = math.sin(2 * math.pi * ph), math.cos(2 * math.pi * ph)
    bob = -3 + 2 * math.cos(4 * math.pi * ph)
    bounce = math.cos(4 * math.pi * ph)
    tails = [((-1 - (4 if charge else 0) * (i < 3)) + 1.6 * 1.1 ** i * math.sin(2 * math.pi * (2 * ph - 0.07 * i + 0.1)),
              3.5 * 1.12 ** i * math.sin(2 * math.pi * (ph + 0.5 - 0.08 * i))) for i in range(NT)]
    hl = (-14, -8, -20) if charge else (-6, -2, -3)
    return pose(bob=bob, pitch=-9 if charge else -5, yaw=3 * sw, roll=2.5 * cw,
                chest=(2 + 1.5 * bounce, -5 * sw, -1.5 * cw),
                neck1=(hl[0] - 2 * bounce, 2 * sw, 0), neck2=(hl[1], 1.5 * sw, 0),
                head=(hl[2] + 2.5 * bounce, 1.5 * sw, 0), jaw=-3 if charge else -6 - 3 * bounce,
                throat=1.0 + 0.12 * bounce, ribs=1.0 + 0.025 * bounce,
                vents=[(24 + 6 * math.sin(2 * math.pi * (2 * ph - 0.1 * k))) if charge else 0 for k in range(NV)],
                plates=8 if charge else 0, core=1.0 if charge else 0, core_s=1.15 if charge else 1.0,
                arms=((10 * sw, 4), (-10 * sw, 4)), tail=tails, legs=(r, l))


def _walk_pose(t):
    ph = (t / WALK_T) % 1.0
    r = gait_foot(ph, WALK_DUTY, WALK_SWEEP, WALK_LIFT, a3s=(12, 30), a3w=-30, curl=-24, splay=(9, -3))
    l = gait_foot((ph + 0.5) % 1.0, WALK_DUTY, WALK_SWEEP, WALK_LIFT, a3s=(12, 30), a3w=-30, curl=-24, splay=(9, -3))
    sw, cw = math.sin(2 * math.pi * ph), math.cos(2 * math.pi * ph)
    b2 = math.cos(4 * math.pi * ph)
    tails = [(-0.5 + 1.0 * math.sin(2 * math.pi * (2 * ph - 0.08 * i)), 5 * 1.1 ** i * math.sin(2 * math.pi * (ph + 0.5 - 0.09 * i)))
             for i in range(NT)]
    return pose(bob=-2 + 1.2 * b2, pitch=-3, yaw=4 * sw, roll=2 * cw, chest=(0, -4 * sw, -1 * cw),
                neck1=(-8 - 2.5 * b2, 3 * sw, 0), neck2=(-3, 2 * sw, 0), head=(-4 + 3 * b2, 2 * sw, 0),
                jaw=-2, throat=1.0 + 0.06 * b2, arms=((6 * sw, 3), (-6 * sw, 3)), tail=tails, legs=(r, l))


def _turn_pose(t, side):
    """side = +1 turn right (yaw increasing), -1 turn left.  Stepping in place while pivoting."""
    ph = (t / TURN_T) % 1.0
    r = gait_foot(ph, 0.5, 7, 8, a3s=(16, 26), a3w=-20, curl=-18)
    l = gait_foot((ph + 0.5) % 1.0, 0.5, 7, 8, a3s=(16, 26), a3w=-20, curl=-18)
    sw = math.sin(2 * math.pi * ph)
    b2 = math.cos(4 * math.pi * ph)
    y = -side   # model ry that swings the front toward the turn
    tails = [(-1, -y * (5 + 2.2 * i) + 2.5 * math.sin(2 * math.pi * (ph - 0.07 * i))) for i in range(NT)]
    return pose(bob=-3 + 1.2 * b2, pitch=-4, yaw=y * (9 + 2 * sw), roll=-side * 4 * -1 * -1, chest=(0, y * 8, 0),
                neck1=(-6, y * 12, 0), neck2=(-2, y * 9, 0), head=(-4 + 2 * b2, y * 11, side * 4), jaw=-4,
                arms=((8, 6), (8, 6)), tail=tails, legs=(r, l))


def build_anims(info=None):
    A = []
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)

    # always: breathing + small life (life_time based, never pops)
    br = Anim("breathe", loop=True)
    br.scl("ribs", (1 + LIFE(0.022, 2.6), 1 + LIFE(0.03, 2.6), 1 + LIFE(0.008, 2.6)))
    br.scl("throat", (1 + LIFE(0.05, 2.6, 0.08), 1 + LIFE(0.2, 2.6, 0.08), 1 + LIFE(0.04, 2.6, 0.08)))
    br.scl("core_1", (1, 1 + LIFE(0.06, 1.3), 1))
    br.scl("core_2", (1, 1 + LIFE(0.06, 1.3, 0.3), 1))
    br.rot("tail6", (0, LIFE(2.5, 3.4, 0.1), 0))
    br.rot("tail7", (0, LIFE(4.0, 3.4), 0))
    br.rot("jaw", (LIFE(0.8, 2.6, 0.3), 0, 0))
    for k in range(NV):
        sym(br, f"vent_{{s}}_{k + 1}", rot=(0, LIFE(1.2, 2.6, 0.05 * k, 1.2), 0))
    A.append(br)

    idle = Anim("idle", length=6.0, loop=True)

    def idle_fn(t):
        s = lambda a, p, ph=0.0: a * math.sin(2 * math.pi * (t / p + ph))
        tails = [(s(1.2, 3, -0.06 * i), s(3.0 * 1.12 ** i, 6, -0.07 * i)) for i in range(NT)]
        return pose(yaw=s(2, 6), chest=(s(1, 3), s(-2, 6), 0), neck1=(-4 + s(3, 6), s(9, 6, 0.1), 0),
                    neck2=(s(2, 3, 0.2), s(5, 6, 0.15), 0), head=(s(4, 3, 0.3), s(8, 6, 0.2), s(4, 6, 0.27)),
                    jaw=-2 + s(1.5, 3), arms=((s(5, 3), 3), (s(5, 3, 0.4), 3)), tail=tails)
    bake(idle, idle_fn, 6.0, dt=0.1)
    A.append(idle)

    run = Anim("move", length=RUN_T, loop=True)
    bake(run, lambda t: _run_pose(t), RUN_T, dt=RUN_T / 12, tol=0.05)
    for t0, s in ((0.0, "r"), (RUN_T / 2, "l")):
        run.sound(t0, "step")
        run.particle(t0, "step", locator=f"foot_{s}")
        run.particle(t0, "scorch", locator=f"foot_{s}")
    A.append(run)

    ch = Anim("charge", length=RUN_T, loop=True)
    bake(ch, lambda t: _run_pose(t, charge=True), RUN_T, dt=RUN_T / 12, tol=0.05)
    for t0, s in ((0.0, "r"), (RUN_T / 2, "l")):
        ch.sound(t0, "step")
        ch.particle(t0, "step", locator=f"foot_{s}")
        ch.particle(t0, "scorch", locator=f"foot_{s}")
        ch.particle(t0 + 0.12, "haze", locator=f"foot_{s}")
    ch.particle(0.15, "horn", locator="horn_r")
    ch.particle(0.45, "horn", locator="horn_l")
    ch.particle(0.2, "vent", locator="vent_r")
    ch.particle(0.5, "vent", locator="vent_l")
    A.append(ch)

    walk = Anim("walk", length=WALK_T, loop=True)
    bake(walk, _walk_pose, WALK_T, dt=WALK_T / 16, tol=0.05)
    for t0, s in ((0.0, "r"), (WALK_T / 2, "l")):
        walk.sound(t0, "step")
        walk.particle(t0, "step", locator=f"foot_{s}")
    A.append(walk)

    for name, side in (("turn_l", -1), ("turn_r", 1)):
        tn = Anim(name, length=TURN_T, loop=True)
        bake(tn, lambda t, sd=side: _turn_pose(t, sd), TURN_T, dt=TURN_T / 12, tol=0.05)
        tn.sound(0.0, "step")
        tn.particle(0.0, "scorch", locator="foot_r")
        tn.particle(TURN_T / 2, "scorch", locator="foot_l")
        A.append(tn)

    # ---- attack_a: horn toss (hit at ATTACK_A_HIT)
    def atk_a(t):
        rf = (kf(t, {0: 2.0, 0.3: 2.0, 0.38: 9.0, 0.47: 2.0, 0.85: 2.0, 0.95: 8.0, 1.08: 2.0}),
              kf(t, {0: 4.0, 0.3: 4.0, 0.47: -7.0, 0.85: -7.0, 1.08: 4.0}),
              kf(t, {0: A3_0, 0.38: -10.0, 0.47: 8.0, 0.85: 8.0, 0.95: -10.0, 1.08: A3_0}),
              kf(t, {0: 0.0, 0.38: -18.0, 0.47: 0.0, 0.95: -15.0, 1.08: 0.0}), 10.0)
        return pose(bob=kf(t, {0: 0, 0.35: -5, 0.55: -3, 0.75: -1, 1.2: 0}),
                    hz=kf(t, {0: 0, 0.35: 3, 0.55: -7, 0.75: -6, 1.2: 0}),
                    pitch=kf(t, {0: 0, 0.35: -10, 0.5: -14, 0.7: 4, 1.2: 0}),
                    chest=kf(t, {0: (0, 0, 0), 0.35: (-3, 0, 0), 0.7: (5, 0, 0), 1.2: (0, 0, 0)}),
                    neck1=kf(t, {0: (0, 0, 0), 0.35: (-20, 0, 0), 0.5: (-12, 0, 0), 0.72: (16, -4, 0), 1.2: (0, 0, 0)}),
                    neck2=kf(t, {0: (0, 0, 0), 0.35: (-10, 0, 0), 0.72: (10, 0, 0), 1.2: (0, 0, 0)}),
                    head=kf(t, {0: (0, 0, 0), 0.35: (-16, 0, 0), 0.5: (-26, 0, 0), 0.7: (24, 0, -8), 0.85: (18, 0, 4),
                                1.2: (0, 0, 0)}),
                    jaw=kf(t, {0: 0, 0.5: -4, 0.66: -24, 0.9: -10, 1.2: 0}),
                    vents=kf(t, {0: 0, 0.4: 0, 0.55: 28, 1.2: 0}),
                    tail=kf(t, {0: (0, 0), 0.35: (-3, 0), 0.55: (-7, 0), 0.8: (2, 0), 1.2: (0, 0)}),
                    arms=((kf(t, {0: 0, 0.5: -30, 1.2: 0}), 8),) * 2, legs=(rf, STAND))
    aa = bake(Anim("attack_a", length=ATTACK_A_LEN, loop="hold"), atk_a, ATTACK_A_LEN)
    aa.sound(0.25, "snarl")
    aa.particle(ATTACK_A_HIT, "spark", locator="horn_r").particle(ATTACK_A_HIT, "spark", locator="horn_l")
    aa.particle(0.47, "step", locator="foot_r")
    A.append(aa)

    # ---- attack_b: whole-body pivot and tail whip (hit at ATTACK_B_HIT)
    def atk_b(t):
        W = {0: 0.0, 0.35: -14.0, 0.62: 30.0, 0.85: 10.0, 1.3: 0.0}
        tails = [(kf(t, {0: 0, 0.4: -4, 0.7: -1, 1.3: 0}), kf(max(0, t - 0.035 * i), W) * (0.7 + 0.12 * i)) for i in range(NT)]
        lf = (kf(t, {0: 2.0, 0.42: 2.0, 0.52: 8.0, 0.62: 2.0}), kf(t, {0: 4.0, 0.42: 4.0, 0.62: 10.0, 1.1: 10.0, 1.3: 4.0}),
              kf(t, {0: A3_0, 0.52: -8.0, 0.62: 18.0, 1.3: A3_0}), kf(t, {0: 0, 0.52: -15, 0.62: 0}), 12.0)
        return pose(bob=kf(t, {0: 0, 0.35: -3, 0.6: -4, 1.3: 0}),
                    yaw=kf(t, {0: 0, 0.35: 12, 0.62: -26, 0.85: -18, 1.3: 0}),
                    roll=kf(t, {0: 0, 0.35: 3, 0.62: -6, 1.3: 0}),
                    chest=kf(t, {0: (0, 0, 0), 0.35: (0, 6, 0), 0.62: (0, -10, 0), 1.3: (0, 0, 0)}),
                    neck1=kf(t, {0: (0, 0, 0), 0.35: (-6, -6, 0), 0.62: (-4, 16, 0), 1.3: (0, 0, 0)}),
                    head=kf(t, {0: (0, 0, 0), 0.35: (-4, -6, 0), 0.62: (4, 14, 6), 1.3: (0, 0, 0)}),
                    jaw=kf(t, {0: 0, 0.4: -14, 0.7: -6, 1.3: 0}), tail=tails, legs=(STAND, lf))
    ab = bake(Anim("attack_b", length=ATTACK_B_LEN, loop="hold"), atk_b, ATTACK_B_LEN)
    ab.sound(0.3, "snarl")
    ab.particle(ATTACK_B_HIT, "scorch", locator="foot_l")
    A.append(ab)

    # ---- roar: rearing head-up roar
    def roar_fn(t):
        shake = 5 * math.sin(t * 28) * sm((t - 0.4) / 0.2) * (1 - sm((t - 1.0) / 0.3))
        return pose(bob=kf(t, {0: 0, 0.3: -3, 0.6: -1, 1.4: 0}), pitch=kf(t, {0: 0, 0.3: -4, 0.6: 6, 1.1: 5, 1.4: 0}),
                    chest=kf(t, {0: (0, 0, 0), 0.6: (5, 0, 0), 1.4: (0, 0, 0)}),
                    neck1=kf(t, {0: (0, 0, 0), 0.3: (-10, 0, 0), 0.6: (12, 0, 0), 1.1: (10, 0, 0), 1.4: (0, 0, 0)}),
                    neck2=kf(t, {0: (0, 0, 0), 0.6: (8, 0, 0), 1.4: (0, 0, 0)}),
                    head=(kf(t, {0: 0, 0.3: -6, 0.6: 18, 1.1: 14, 1.4: 0}), 0, shake),
                    jaw=kf(t, {0: 0, 0.3: -4, 0.5: -36, 1.05: -32, 1.3: -4, 1.4: 0}),
                    throat=kf(t, {0: 1.0, 0.3: 1.25, 0.6: 1.45, 1.1: 1.2, 1.4: 1.0}),
                    ribs=kf(t, {0: 1.0, 0.3: 1.08, 0.7: 0.98, 1.4: 1.0}),
                    vents=kf(t, {0: 0, 0.5: 16, 1.1: 14, 1.4: 0}),
                    tail=kf(t, {0: (0, 0), 0.6: (-5, 0), 1.4: (0, 0)}), arms=((kf(t, {0: 0, 0.6: -35, 1.4: 0}), 18),) * 2)
    ro = bake(Anim("roar", length=ROAR_LEN, loop="hold"), roar_fn, ROAR_LEN)
    ro.sound(0.35, "roar")
    ro.particle(0.6, "ember", locator="mouth")
    A.append(ro)

    # ---- ignite (Stage I): deep inhale, fissures light, vents crack open, horns flare, bellow, hunting crouch
    def ign(t):
        vents = [kf(t, {0: 0, 0.5 + 0.05 * k: 0, 0.85 + 0.05 * k: 34, 1.6: 30}) for k in range(NV)]
        plates = [kf(t, {0: 0, 0.6 + 0.04 * i: 0, 0.95 + 0.04 * i: 12, 1.6: 9}) for i in range(NP)]
        shake = 4 * math.sin(t * 30) * sm((t - 1.05) / 0.1) * (1 - sm((t - 1.35) / 0.15))
        return pose(bob=kf(t, {0: 0, 0.5: -4, 1.0: -3, 1.25: -1, 1.6: -3}),
                    pitch=kf(t, {0: 0, 0.5: -3, 1.1: 5, 1.6: -6}),
                    chest=kf(t, {0: (0, 0, 0), 0.5: (-2, 0, 0), 1.15: (5, 0, 0), 1.6: (1, 0, 0)}),
                    neck1=kf(t, {0: (0, 0, 0), 0.5: (-10, 0, 0), 1.15: (10, 0, 0), 1.6: (-10, 0, 0)}),
                    neck2=kf(t, {0: (0, 0, 0), 0.5: (-4, 0, 0), 1.15: (8, 0, 0), 1.6: (-6, 0, 0)}),
                    head=(kf(t, {0: 0, 0.5: -8, 1.15: 16, 1.6: -12}), 0, shake),
                    jaw=kf(t, {0: 0, 0.95: -2, 1.12: -30, 1.4: -24, 1.6: -4}),
                    throat=kf(t, {0: 1.0, 0.5: 1.5, 0.9: 1.3, 1.15: 1.45, 1.6: 1.05}),
                    ribs=kf(t, {0: 1.0, 0.55: 1.11, 1.0: 1.06, 1.3: 0.98, 1.6: 1.03}),
                    vents=vents, plates=plates, slide=[p * 0.15 for p in plates],
                    core=kf(t, {0: 0, 0.7: 0, 1.1: 1.5, 1.6: 1.2}), core_s=kf(t, {0: 1.0, 0.7: 1.0, 1.1: 1.35, 1.6: 1.2}),
                    tail=kf(t, {0: (0, 0), 0.5: (1, 0), 1.15: (-5, 0), 1.6: (-2, 0)}),
                    arms=((kf(t, {0: 0, 1.15: -25, 1.6: 0}), 10),) * 2,
                    legs=(STAND, (2.0, kf(t, {0: 4.0, 1.25: 4.0, 1.6: 10.0}),
                                  kf(t, {0: A3_0, 1.25: A3_0, 1.42: -10.0, 1.6: 24.0}), 0.0, 8.0)))
    ig = bake(Anim("ignite", length=IGNITE_LEN, loop="hold"), ign, IGNITE_LEN)
    ig.sound(0.0, "snort").sound(0.62, "hiss").sound(IGNITE_ROAR, "bellow")
    ig.particle(0.8, "vent", locator="vent_r").particle(0.8, "vent", locator="vent_l")
    ig.particle(0.95, "vent", locator="vent_r").particle(0.95, "vent", locator="vent_l")
    ig.particle(1.0, "horn", locator="horn_r").particle(1.0, "horn", locator="horn_l")
    ig.particle(1.15, "ember", locator="core").particle(1.2, "ember", locator="mouth")
    A.append(ig)

    # ---- skid: braced feet, lean back, tail up (script decelerates over SKID_LEN)
    def skid(t):
        fr = (2.0, kf(t, {0: 4.0, 0.15: -11.0}), kf(t, {0: 20.0, 0.15: -2.0}), kf(t, {0: 0, 0.15: 8.0}), 16.0)
        fl = (kf(t, {0: 9.0, 0.12: 2.0}), kf(t, {0: 12.0, 0.2: -4.0}), kf(t, {0: -20.0, 0.2: 4.0}), 0.0, 16.0)
        return pose(bob=kf(t, {0: -3, 0.2: -7, 0.7: -5}), hz=kf(t, {0: 0, 0.25: 4, 0.7: 2}),
                    pitch=kf(t, {0: -8, 0.2: 9, 0.45: 7, 0.7: 1}), roll=kf(t, {0: 0, 0.25: -4, 0.7: 0}),
                    chest=kf(t, {0: (0, 0, 0), 0.25: (3, 0, 0), 0.7: (0, 0, 0)}),
                    neck1=kf(t, {0: (-12, 0, 0), 0.25: (6, 0, 0), 0.7: (0, 0, 0)}),
                    head=kf(t, {0: (-16, 0, 0), 0.25: (10, 0, 4), 0.7: (2, 0, 0)}),
                    jaw=kf(t, {0: -3, 0.25: -16, 0.7: -8}), throat=kf(t, {0: 1.0, 0.3: 1.25, 0.7: 1.1}),
                    vents=kf(t, {0: 22, 0.3: 30, 0.7: 18}), plates=8, core=1.0, core_s=1.15,
                    tail=kf(t, {0: (-3, 0), 0.25: (-9, 0), 0.7: (-3, 0)}),
                    arms=((kf(t, {0: 0, 0.25: -40, 0.7: -15}), 14),) * 2, legs=(fr, fl))
    sk = bake(Anim("skid", length=SKID_LEN, loop="hold"), skid, SKID_LEN)
    sk.sound(0.0, "skid")
    for t0 in (0.05, 0.25, 0.45):
        sk.particle(t0, "skid", locator="foot_r").particle(t0, "skid", locator="foot_l")
    A.append(sk)

    # ---- power (Stage III): the furnace opens fully at POWER_OPEN and holds
    def pw(t):
        vents = [kf(t, {0: 22, 0.3: 18, 0.42 + 0.06 * k: 30, 0.72 + 0.05 * k: 80, 1.4: 78}) for k in range(NV)]
        plates = [kf(t, {0: 8, 0.3: 4, 0.45 + 0.06 * i: 10, 0.8 + 0.04 * i: 58, 1.4: 55}) for i in range(NP)]
        slide = [kf(t, {0: 0, 0.45 + 0.06 * i: 0, 0.8 + 0.04 * i: 4.5, 1.4: 4.5}) for i in range(NP)]
        return pose(bob=kf(t, {0: -3, 0.3: -5, 0.9: -1, 1.4: -1.5}), pitch=kf(t, {0: -4, 0.3: -6, 0.95: 8, 1.4: 7}),
                    chest=kf(t, {0: (0, 0, 0), 0.3: (-3, 0, 0), 0.95: (6, 0, 0), 1.4: (5, 0, 0)}),
                    neck1=kf(t, {0: (-8, 0, 0), 0.3: (-16, 0, 0), 0.95: (12, 0, 0), 1.4: (10, 0, 0)}),
                    neck2=kf(t, {0: (0, 0, 0), 0.95: (6, 0, 0), 1.4: (5, 0, 0)}),
                    head=kf(t, {0: (-8, 0, 0), 0.3: (-14, 0, 0), 0.95: (12, 0, 0), 1.4: (10, 0, 0)}),
                    jaw=kf(t, {0: 0, 0.8: -10, 1.0: -38, 1.4: -30}),
                    throat=kf(t, {0: 1.0, 0.3: 0.9, 0.95: 1.4, 1.4: 1.3}),
                    ribs=kf(t, {0: 1.0, 0.3: 0.96, 0.95: 1.14, 1.4: 1.12}),
                    vents=vents, plates=plates, slide=slide,
                    core=kf(t, {0: 1.0, 0.6: 1.0, 1.0: 3.4, 1.4: 3.0}), core_s=kf(t, {0: 1.15, 0.6: 1.15, 1.0: 1.85, 1.4: 1.7}),
                    tail=[kf(t, {0: (0, 0), 0.3: (2, 0), 0.95: (-6 - i * 0.5, 0), 1.4: (-5, 0)}) for i in range(NT)],
                    arms=((kf(t, {0: 0, 0.3: 10, 0.95: -40, 1.4: -36}), kf(t, {0: 4, 0.95: 32, 1.4: 30})),) * 2,
                    legs=((2.0, 4.0, A3_0, 0.0, 14.0), (2.0, kf(t, {0: 4.0, 0.3: 4.0, 0.5: 10.0}), A3_0, 0.0, 14.0)))
    po = bake(Anim("power", length=POWER_LEN, loop="hold"), pw, POWER_LEN)
    po.sound(0.4, "hiss").sound(0.9, "roar")
    for t0 in (0.6, 0.75, 0.9):
        po.particle(t0, "vent", locator="vent_r").particle(t0, "vent", locator="vent_l")
    po.particle(0.95, "ember", locator="core").particle(1.0, "horn", locator="horn_r").particle(1.0, "horn", locator="horn_l")
    A.append(po)

    fu = Anim("furnace", length=2.0, loop=True)        # layered on power: the open furnace breathes
    fu.scl("core_1", (1 + LIFE(0.05, 0.5), 1 + LIFE(0.12, 0.5), 1))
    fu.scl("core_2", (1 + LIFE(0.05, 0.5, 0.25), 1 + LIFE(0.12, 0.5, 0.25), 1))
    for k in range(NV):
        sym(fu, f"vent_{{s}}_{k + 1}", rot=(0, LIFE(5, 0.4, 0.07 * k), 0))
    for i in range(NP):
        sym(fu, f"dplate_{{s}}_{i + 1}", rot=(0, 0, LIFE(3, 0.6, 0.1 * i)))
    fu.rot("jaw", (LIFE(3, 0.3), 0, 0))
    fu.particle(0.0, "ember", locator="core").particle(1.0, "ember", locator="core")
    fu.particle(0.5, "vent", locator="vent_r").particle(1.5, "vent", locator="vent_l")
    fu.sound(0.0, "thrum")
    A.append(fu)

    # ---- cool: vents close back-to-front, plates settle, steam, exhausted exhale
    def cool(t):
        vents = [kf(t, {0: 78, 0.15 + 0.07 * (NV - 1 - k): 78, 0.55 + 0.07 * (NV - 1 - k): 6, 1.2: 0}) for k in range(NV)]
        plates = [kf(t, {0: 55, 0.1 + 0.05 * (NP - 1 - i): 55, 0.6 + 0.05 * (NP - 1 - i): 3, 1.2: 0}) for i in range(NP)]
        slide = [kf(t, {0: 4.5, 0.1 + 0.05 * (NP - 1 - i): 4.5, 0.6 + 0.05 * (NP - 1 - i): 0.0}) for i in range(NP)]
        return pose(bob=kf(t, {0: -1.5, 0.6: -4, 1.2: -3}), pitch=kf(t, {0: 7, 0.6: -4, 1.2: -3}),
                    chest=kf(t, {0: (5, 0, 0), 0.6: (-2, 0, 0), 1.2: (0, 0, 0)}),
                    neck1=kf(t, {0: (10, 0, 0), 0.6: (-12, 0, 0), 1.2: (-10, 0, 0)}),
                    neck2=kf(t, {0: (5, 0, 0), 1.2: (-4, 0, 0)}),
                    head=kf(t, {0: (10, 0, 0), 0.6: (-10, 0, 0), 1.2: (-8, 0, 0)}),
                    jaw=kf(t, {0: -30, 0.5: -14, 1.2: -6}), throat=kf(t, {0: 1.3, 0.6: 0.92, 1.2: 1.0}),
                    ribs=kf(t, {0: 1.12, 0.6: 0.95, 1.2: 1.0}), vents=vents, plates=plates, slide=slide,
                    core=kf(t, {0: 3.0, 0.8: 0.0}), core_s=kf(t, {0: 1.7, 0.8: 1.0}),
                    tail=kf(t, {0: (-5, 0), 0.8: (2, 0), 1.2: (1, 0)}),
                    arms=((kf(t, {0: -36, 0.7: 5, 1.2: 0}), kf(t, {0: 30, 0.7: 4})),) * 2,
                    legs=((2.0, 4.0, A3_0, 0.0, kf(t, {0: 14.0, 1.2: 6.0})),) * 2)
    co = bake(Anim("cool", length=COOL_LEN, loop="hold"), cool, COOL_LEN)
    co.sound(0.05, "cool")
    for t0 in (0.15, 0.45, 0.8):
        co.particle(t0, "steam", locator="vent_r").particle(t0, "steam", locator="vent_l")
    co.particle(0.5, "steam", locator="core").particle(0.95, "steam", locator="core")
    A.append(co)

    # ---- pant: heavy breathing after exertion
    def pant(t):
        b = math.sin(2 * math.pi * t / 0.9)
        b2 = math.sin(2 * math.pi * (t / 0.9 - 0.12))
        return pose(bob=-3, pitch=-5, chest=(1.5 * b, 0, 0), neck1=(-10 + 3 * b2, 0, 0), neck2=(-4, 0, 0),
                    head=(-6 + 4 * b2, 0, 0), jaw=-12 - 7 * b2, throat=1.2 + 0.3 * b, ribs=1.04 + 0.07 * b,
                    vents=[16 + 12 * math.sin(2 * math.pi * (t / 0.9 - 0.04 * k)) for k in range(NV)],
                    tail=[(1 + 1.2 * b2, 0) for _ in range(NT)], arms=((-6 * b, 3),) * 2)
    pa = bake(Anim("pant", length=1.8, loop=True), pant, 1.8, dt=0.05, tol=0.05)
    pa.sound(0.0, "snort").sound(0.9, "snort")
    pa.particle(0.45, "steam", locator="mouth").particle(1.35, "steam", locator="mouth")
    pa.particle(0.5, "ember", locator="vent_r").particle(1.4, "ember", locator="vent_l")
    A.append(pa)

    # ---- rest: settled crouch, head low, slow deep breaths
    def rest(t):
        b = math.sin(2 * math.pi * t / 4.0)
        return pose(bob=-9, pitch=-4, chest=(-2 + b, 0, 0), neck1=(-16 + 2 * b, 3 * math.sin(2 * math.pi * t / 8), 0),
                    neck2=(-6, 0, 0), head=(-8 + 1.5 * b, 4 * math.sin(2 * math.pi * (t / 8 + 0.1)), 0),
                    throat=1.0 + 0.15 * b, ribs=1.0 + 0.04 * b, tail=[(2.2, 1.5 * math.sin(2 * math.pi * (t / 8 - 0.06 * i)))
                                                                       for i in range(NT)], arms=((8, 2),) * 2)
    re = bake(Anim("rest", length=8.0, loop=True), rest, 8.0, dt=0.2, tol=0.05)
    A.append(re)

    # ---- react: flinch, recoil, startled hiss with vents snapping open
    def react(t):
        rf = (kf(t, {0: 2.0, 0.08: 7.0, 0.22: 2.0}), kf(t, {0: 4.0, 0.22: 10.0, 0.6: 10.0, 0.8: 4.0}),
              kf(t, {0: A3_0, 0.08: -10.0, 0.22: 24.0, 0.8: A3_0}), kf(t, {0: 0, 0.08: -14, 0.22: 0}), 12.0)
        return pose(bob=kf(t, {0: 0, 0.12: -3, 0.8: 0}), hz=kf(t, {0: 0, 0.12: 4, 0.5: 2, 0.8: 0}),
                    pitch=kf(t, {0: 0, 0.12: 6, 0.4: -2, 0.8: 0}), yaw=kf(t, {0: 0, 0.12: 10, 0.4: -4, 0.8: 0}),
                    neck1=kf(t, {0: (0, 0, 0), 0.12: (12, 8, 0), 0.4: (-4, -4, 0), 0.8: (0, 0, 0)}),
                    head=kf(t, {0: (0, 0, 0), 0.12: (16, 6, 10), 0.4: (-6, -4, -4), 0.8: (0, 0, 0)}),
                    jaw=kf(t, {0: 0, 0.15: -22, 0.5: -8, 0.8: 0}),
                    vents=kf(t, {0: 0, 0.1: 32, 0.6: 0}), plates=kf(t, {0: 0, 0.1: 14, 0.6: 0}),
                    tail=[kf(max(0, t - 0.04 * i), {0: (0, 0), 0.15: (-4, -10), 0.45: (0, 6), 0.8: (0, 0)}) for i in range(NT)],
                    arms=((kf(t, {0: 0, 0.12: -30, 0.8: 0}), 10),) * 2, legs=(rf, STAND))
    rc = bake(Anim("react", length=REACT_LEN, loop="hold"), react, REACT_LEN)
    rc.sound(0.05, "snarl")
    rc.particle(0.1, "vent", locator="vent_r").particle(0.1, "vent", locator="vent_l")
    A.append(rc)

    # ---- depart: cools into slag -- collapses, plates crack off, sinks and settles away
    drop = [(i * 0.0) for i in range(NP)]

    def depart(t):
        fall = [(kf(t, {0: 0, 0.55 + 0.08 * i: 0, 1.2 + 0.08 * i: 7.0}),
                 kf(t, {0: 0, 0.55 + 0.08 * i: 0, 1.2 + 0.08 * i: -12.0}),
                 kf(t, {0: 0, 0.55 + 0.08 * i: 4, 1.2 + 0.08 * i: 70.0})) for i in range(NP)]
        sink = sm((t - 0.8) / 1.1)
        return pose(bob=kf(t, {0: 0, 0.8: -20, 2.0: -24}), pitch=kf(t, {0: -3, 0.8: -7}), roll=kf(t, {0: 0, 0.8: 5}),
                    chest=kf(t, {0: (0, 0, 0), 0.8: (-6, 0, 0)}),
                    neck1=kf(t, {0: (-8, 0, 0), 0.8: (-24, 6, 0), 2.0: (-28, 8, 0)}),
                    neck2=kf(t, {0: (-4, 0, 0), 0.8: (-14, 0, 0)}),
                    head=kf(t, {0: (-8, 0, 0), 0.8: (-14, 8, 10), 2.0: (-16, 10, 14)}),
                    jaw=kf(t, {0: 0, 0.8: -10}), throat=kf(t, {0: 1.0, 0.8: 0.8}), ribs=kf(t, {0: 1.0, 0.4: 1.08, 1.0: 0.9}),
                    vents=kf(t, {0: 10, 0.5: 0}), plate_drop=fall,
                    tail=[kf(t, {0: (0, 0), 0.9: (3.5, 4 - i), 2.0: (4, 5 - i)}) for i in range(NT)],
                    arms=((kf(t, {0: 0, 0.8: 20}), 2),) * 2,
                    root_pos=(0, -26 * sink, 0), root_scl=(1 + 0.12 * sink, max(0.0, 1 - 0.85 * sink) * (1 - sm((t - 1.85) / 0.15)),
                                                           1 + 0.06 * sink))
    de = bake(Anim("depart", length=DEPART_LEN, loop="hold"), depart, DEPART_LEN)
    de.sound(0.0, "depart")
    de.particle(0.2, "steam", locator="core").particle(0.6, "slag", locator="core").particle(0.9, "slag", locator="vent_r")
    de.particle(1.1, "slag", locator="vent_l").particle(1.3, "steam", locator="core").particle(1.5, "slag", locator="core")
    A.append(de)

    # ---- arrive: stalks out of the heat-shimmer wall (unfolding from its plane), then shakes and snarls
    def arrive(t):
        tw = min(t, ARRIVE_WALK)
        p = _walk_pose(tw)
        if t > ARRIVE_WALK:   # settle from the last walk frame into a wide stance
            f = sm((t - ARRIVE_WALK) / (ARRIVE_LEN - ARRIVE_WALK))
            q = pose(bob=-2, neck1=(4, 0, 0), head=(10, 0, 0), jaw=-20, throat=1.3, ribs=1.05, vents=10)
            for b, chs in q.items():
                for c, v in chs.items():
                    a0 = p.get(b, {}).get(c, IDENT[c])
                    p.setdefault(b, {})[c] = tuple(x + (y - x) * f for x, y in zip(a0, v))
        sz = sm(t / 0.5)
        wob = 0.1 * math.sin(t * 45) * (1 - sm(t / 0.7))
        p["root"]["scl"] = (1 + wob, 1.06 - 0.06 * sz, 0.03 + 0.97 * sz)
        hs = 6 * math.sin(t * 34) * sm((t - 1.3) / 0.1) * (1 - sm((t - 1.5) / 0.1))
        p["head"]["rot"] = (p["head"]["rot"][0], p["head"]["rot"][1], p["head"]["rot"][2] + hs)
        return p
    ar = bake(Anim("arrive", length=ARRIVE_LEN, loop="hold"), arrive, ARRIVE_LEN, tol=0.05)
    for t0, s in ((0.0, "r"), (WALK_T / 2, "l"), (WALK_T, "r")):
        ar.sound(t0, "step")
        ar.particle(t0, "step", locator=f"foot_{s}")
    ar.sound(1.3, "snarl")
    ar.particle(0.1, "haze", locator="core").particle(0.4, "haze", locator="core")
    A.append(ar)
    return A


# ---------------------------------------------------------------- constructs
def _shimmer_mat(seed, tint, a_scale=1.0, key="sh"):
    """Translucent heat-distortion curtain (blend): wavering refraction bands, warm at the base."""
    kt, kw = tex.rgb(tint), tex.rgb("#fff8ec")

    def fn(ctx):
        u, v = ctx.U, ctx.V
        sd = seed + ctx.variant * 1.7
        w1 = np.sin((u * 3 + 0.35 * np.sin(v * 8 + sd)) * 2 * np.pi) * 0.5 + 0.5
        w2 = np.sin((u * 9 + 0.6 * np.sin(v * 13 + sd * 2)) * 2 * np.pi) * 0.5 + 0.5
        fadev = np.clip(v * 1.3, 0, 1) ** 1.4
        a = (0.06 + 0.32 * w1 ** 5 + 0.16 * w2 ** 10) * fadev * a_scale
        col = kw + (kt - kw) * np.clip((1 - w1) * 0.6 + 0.4 * v, 0, 1)[..., None]
        sp = ctx.rng.random((ctx.h, ctx.w)) < 0.004
        a = np.where(sp, 0.9, a)
        col = np.where(sp[..., None], tex.rgb("#ffcf70"), col)
        return _t(ctx, col, 0.0, np.clip(a, 0, 1))
    return Mat(fn, f"edheat_{key}{seed}{tint}{a_scale}", mode="blend")


def _ribbon_mat(tint, key):
    """Superheated air front (blend): bright crest line, translucent wavering body."""
    kt, kc = tex.rgb(tint), tex.rgb("#fffbe8")

    def fn(ctx):
        u, v = ctx.U, ctx.V
        crest = np.exp(-((v - 0.14 - 0.03 * np.sin(u * 12 + ctx.variant)) / 0.05) ** 2)
        streak = np.sin((u * 10 + 0.4 * np.sin(v * 9 + ctx.variant * 2)) * 2 * np.pi) * 0.5 + 0.5
        body = (v > 0.12) * (0.1 + 0.2 * streak ** 4) * (0.5 + 0.5 * v)
        a = np.clip(0.8 * crest + body, 0, 0.95)
        col = kc + (kt - kc) * np.clip(v * 1.2, 0, 1)[..., None]
        return _t(ctx, col, 0.0, a)
    return Mat(fn, f"edheat_rib{key}{tint}", mode="blend")


def _seam_mat():
    def fn(ctx):
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 3.0, iy / 2.0, 21)
        hot = np.abs(n - 0.5) < 0.12
        col = np.where(hot[..., None], tex.rgb("#ffb040"), tex.rgb("#3a0e06"))
        return tex.grain(ctx, _t(ctx, col, np.where(hot, 1.0, 0.25), np.where(n > 0.25, 1.0, 0.0)), 0.06)
    return Mat(fn, "edheat_seam")


def shimmer_model():
    """Heat-shimmer wall: 9 x 8 blocks at scale 2; two folding curtains of hot air over a glowing seam."""
    m = Model("ed_heat_shimmer", density=0.5, bounds=(12, 10, (0, 4, 0)))
    root = m.bone("root")
    seam = m.bone("seam", root)
    seam.plane("y", (0, 0.3, 0), 74, 6, _seam_mat(), faces=("up",))
    mats = [_shimmer_mat(1.0, "#ffb070"), _shimmer_mat(2.3, "#ff9050", 0.85), _shimmer_mat(3.7, "#ffd0a0", 0.7)]
    for s, sx in (("r", 1), ("l", -1)):
        par = root
        for k in range(4):
            x0 = sx * 9 * k
            b = m.bone(f"cur_{s}_{k + 1}", par, pivot=(x0, 0, 0))
            b.plane("z", (x0 + sx * 4.6, 32, 0), 9.4, 64, mats[(k + (s == "l")) % 3], variant=k % 2)
            b.plane("z", (x0 + sx * 4.6, 28, 1.8), 9.4, 56, mats[(k + 1) % 3], variant=(k + 1) % 2)
            par = b
    return m


def shimmer_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    rip = Anim("ripple", loop=True)
    for s in ("r", "l"):
        for k in range(4):
            ph = k * 0.17 + (0.5 if s == "l" else 0)
            rip.rot(f"cur_{s}_{k + 1}", (LIFE(2.5, 1.9, ph), LIFE(7, 2.3, ph), 0))
            rip.pos(f"cur_{s}_{k + 1}", (0, LIFE(0.8, 1.3, ph), LIFE(1.4, 1.7, ph)))
    rip.scl("seam", (1, 1 + LIFE(0.5, 0.6), 1))
    form = Anim("form", length=0.6, loop="hold")
    for s in ("r", "l"):
        form.scl(f"cur_{s}_1", {0: (1, 0, 1), 0.45: (1, 1.08, 1), 0.6: (1, 1, 1)})
    form.scl("seam", {0: (0, 1, 1), 0.3: (1, 1, 1)})
    hold = Anim("hold", loop=True)
    hold.pos("root", (0, LIFE(0.3, 2.0), 0))
    part = Anim("part", length=0.9, loop="hold")
    sym(part, "cur_{s}_1", pos={0: (0, 0, 0), 0.9: (22, 0, 0)}, rot={0: (0, 0, 0), 0.9: (0, 40, 0)})
    for k, a in ((2, -80), (3, 80), (4, -80)):
        sym(part, f"cur_{{s}}_{k}", rot={0: (0, 0, 0), 0.9: (0, a, 0)})
    part.scl("cur_r_1", {0: 1.0, 0.9: (1, 0.85, 1)})
    part.scl("cur_l_1", {0: 1.0, 0.9: (1, 0.85, 1)})
    fade = Anim("fade", length=0.6, loop="hold")
    for s in ("r", "l"):
        fade.scl(f"cur_{s}_1", {0: (1, 0.85, 1), 0.6: (1, 0, 1)})
        fade.pos(f"cur_{s}_1", {0: (0, 0, 0), 0.6: (0, 10, 0)})
    fade.scl("seam", {0: 1.0, 0.6: (0, 1, 1)})
    return [hidden, rip, form, hold, part, fade]


def wave_model():
    """Superheated air front: three nested translucent arcs bulging forward (-Z) + an ember skirt."""
    m = Model("ed_heat_wave", density=0.5, bounds=(14, 8, (0, 2, 0)))
    root = m.bone("root")
    for j, (R, Hh, tint) in enumerate(((52, 46, "#ffb060"), (44, 36, "#ff8a3a"), (36, 26, "#ff5a20"))):
        b = m.bone(f"arc{j + 1}", root, pivot=(0, 0, 8 * j))
        n = 9
        tl = 2 * R * math.sin(math.radians(110 / n / 2)) * 1.12
        ring(b, (0, Hh / 2, R + 8 * j), R, n, (tl, 0, Hh), _ribbon_mat(tint, j), axis="y", start=215, sweep=110,
             cycle=2)
    sk = m.bone("skirt", root)
    ring(sk, (0, 1.2, 50), 50, 14, (3.5, 3.0, 2.4), tex.glow_flat("#ff9a30", 1.0, core="#fff2c0"), axis="y",
         start=212, sweep=116)
    ring(sk, (0, 0.6, 46), 46, 10, (5, 6, 1.2), tex.glow_flat("#c8360c", 0.8, core="#ff8a2a"), axis="y",
         start=214, sweep=112)
    return m


def wave_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    surge = Anim("surge", loop=True)
    for j in range(3):
        surge.pos(f"arc{j + 1}", (0, LIFE(2.5, 0.7, j * 0.2), LIFE(3.0, 0.9, j * 0.3)))
        surge.scl(f"arc{j + 1}", (1, 1 + LIFE(0.1, 0.6, j * 0.17), 1))
        surge.rot(f"arc{j + 1}", (LIFE(6, 0.8, j * 0.25), 0, 0))
    surge.scl("skirt", (1, 1 + LIFE(0.4, 0.3), 1))
    rise = Anim("rise", length=0.35, loop="hold")
    rise.scl("root", {0: (0.3, 0.0, 0.3), 0.2: (1.1, 1.15, 1.1), 0.35: (1, 1, 1)})
    travel = Anim("travel", loop=True)
    travel.rot("root", (LIFE(2, 0.5), 0, 0))
    burst = Anim("burst", length=0.6, loop="hold")
    burst.scl("root", {0: (1, 1, 1), 0.3: (1.5, 1.2, 1.5), 0.6: (2.0, 0.0, 2.0)})
    burst.pos("root", {0: (0, 0, 0), 0.6: (0, 10, 0)})
    return [hidden, surge, rise, travel, burst]


def _glass_mat():
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r, ang = np.hypot(u, v), np.arctan2(v, u)
        rim = 0.84 + 0.1 * np.sin(ang * 5 + 1.3 + ctx.variant) + 0.05 * np.sin(ang * 11)
        ix, iy = tex.px(ctx)
        n = tex.fbm(ix / 5.0 + ctx.variant * 7, iy / 5.0, 5)
        crack = (np.abs(n - 0.5) < 0.035) | ((np.abs(np.sin(ang * 7 + n * 3)) < 0.07) & (r > 0.18))
        hot = ctx.alt is None
        pc = tex.mix(tex.rgb("#7a1e08"), tex.rgb("#d0581a"), n[..., None]) if hot else \
            tex.mix(tex.rgb("#0e080c"), tex.rgb("#2a2232"), n[..., None])
        pg = np.clip(0.6 - r * 0.5, 0, 1) if hot else np.zeros_like(r)
        col = np.where(crack[..., None], tex.rgb("#ffe2a0" if hot else "#6a2410"), pc)
        glow = np.where(crack, 1.0 if hot else 0.3, pg)
        gl = ctx.rng.random(r.shape) < (0.0 if hot else 0.02)
        col = np.where(gl[..., None], tex.rgb("#c8c0e0"), col)
        return _t(ctx, col, glow, (r < rim) * 1.0)
    return Mat(fn, "edheat_glass")


def glass_model():
    m = Model("ed_heat_glass", density=1.0, bounds=(5, 2, (0, 0, 0)), alts=("cool",))
    root = m.bone("root")
    disc = m.bone("disc", root)
    disc.plane("y", (0, 0.15, 0), 56, 56, _glass_mat(), faces=("up",))
    sh = m.bone("shards", root)
    shard = tex.alt(tex.crystal("#ffb050", "#c8400c", "#fff2c0", mode="solid", glow=0.9),
                    cool=tex.crystal("#3a2a3a", "#120a10", "#9a90b0", mode="solid", glow=0.05))
    rng = np.random.default_rng(7)
    for k in range(7):
        a = k * 51.4 + 10
        rr = 8 + 12 * rng.random()
        x, z = rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a))
        h = 3 + 4 * rng.random()
        sh.box((x, h / 2, z), (1.8, h, 1.6), shard, rot=(rng.uniform(-25, 25), a, rng.uniform(-25, 25)),
               pivot=(x, 0, z), variant=k % 2)
    return m


def glass_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=0.3, loop="hold")
    appear.scl("disc", {0: 0.0, 0.2: 1.1, 0.3: 1.0})
    appear.pos("shards", {0: (0, -8, 0), 0.3: (0, 0, 0)})
    hold = Anim("hold", loop=True)
    fade = Anim("fade", length=0.8, loop="hold")
    fade.scl("disc", {0: 1.0, 0.8: 0.0})
    fade.pos("shards", {0: (0, 0, 0), 0.8: (0, -9, 0)})
    return [hidden, appear, hold, fade]


LANE_SEGS = 16   # 2 blocks each


def _lane_mat():
    def fn(ctx):
        u, v = ctx.U, ctx.V
        surge = ctx.alt == "hot"
        edge = (np.abs(u - 0.06) < 0.02) | (np.abs(u - 0.94) < 0.02)
        dash = ((np.abs(u - 0.13) < 0.018) | (np.abs(u - 0.87) < 0.018)) & ((v * 4) % 1 < 0.45)
        chev = (np.abs(np.abs(u - 0.5) * 0.9 - (v - 0.22)) < 0.05) & (np.abs(u - 0.5) < 0.3)
        sp = (ctx.rng.random(u.shape) < 0.012) & (np.abs(u - 0.5) < 0.36)
        mask = edge | dash | chev | sp
        c_e = tex.rgb("#fff2c0" if surge else "#ff7a2a")
        c_c = tex.rgb("#ffffff" if surge else "#ffc060")
        col = np.where(chev[..., None], c_c, c_e)
        return _t(ctx, col, np.where(mask, 1.0 if surge else 0.85, 0.0), mask * 1.0)
    return Mat(fn, "edheat_lane")


def lane_model():
    """Charge-lane telegraph laid along -Z (the actor's facing); 2-block segments shown up to grimoire:len."""
    m = Model("ed_heat_lane", density=1.0, bounds=(70, 4, (0, 0, 0)), alts=("hot",))
    root = m.bone("root")
    mat = _lane_mat()
    for k in range(LANE_SEGS):
        b = m.bone(f"seg{k + 1}", root, pivot=(0, 0, -32 * k - 16))
        b.plane("y", (0, 0.2 + 0.02 * (k % 2), -32 * k - 16), 80, 32, mat, faces=("up",), variant=k % 2)
    return m


def lane_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    appear = Anim("appear", length=0.9, loop="hold")
    for k in range(LANE_SEGS):
        t0 = 0.035 * k
        appear.scl(f"seg{k + 1}", {0: (0, 1, 0), t0: (0, 1, 0), t0 + 0.15: (1.15, 1, 1.1), t0 + 0.3: (1, 1, 1),
                                   0.9: (1, 1, 1)})
    armed = Anim("armed", loop=True)
    for k in range(LANE_SEGS):
        armed.scl(f"seg{k + 1}", (1 + LIFE(0.05, 0.6, -k * 0.06), 1, 1))
    surge = Anim("surge", loop=True)
    for k in range(LANE_SEGS):
        surge.scl(f"seg{k + 1}", (1.1 + LIFE(0.12, 0.25, k * 0.07), 1, 1))
    fade = Anim("fade", length=0.5, loop="hold")
    fade.scl("root", {0: (1, 1, 1), 0.5: (0, 1, 1)})
    return [hidden, appear, armed, surge, fade]


# ---------------------------------------------------------------- sounds
def _harsh(sig, drive=2.2):
    return sy.norm(np.tanh(sig * drive))


def _voice(dur, f0, f1, rasp=0.45):
    a = sy.roar(dur, f0=f0, f1=f1, growl=31, rough=0.8, formant=(650, 1450), breath=0.6, bend=0.35)
    b = sy.roar(dur, f0=f0 * 2.02, f1=f1 * 1.9, growl=47, rough=0.9, formant=(900, 2100), breath=0.8, bend=0.2)
    hiss = sy.highpass(sy.noise(dur), 2500) * sy.env(dur, 0.05 * dur, 0.2 * dur, 0.5, 0.4 * dur) * 0.25
    return _harsh(a + rasp * b + hiss)


def build_sounds(pack):
    roar = _voice(2.0, 150, 95)
    sy.save(pack, "ed_heat_roar", sy.reverb(roar, 1.0, 0.2), max_distance=80,
            variants=[sy.reverb(sy.pitch(roar, 1.07), 1.0, 0.2), sy.reverb(sy.pitch(_voice(1.9, 140, 100), 0.95), 1.0, 0.2)])
    bel = sy.at(1.6, (0.0, _voice(1.4, 115, 82, 0.3)), (0.0, sy.thump(0.8, 70, 35, 0.2) * 0.5))
    sy.save(pack, "ed_heat_bellow", sy.reverb(bel, 1.0, 0.2), max_distance=72)
    snarl = _voice(0.75, 190, 130, 0.7)
    sy.save(pack, "ed_heat_snarl", sy.reverb(snarl, 0.6, 0.15), max_distance=48,
            variants=[sy.reverb(sy.pitch(snarl, 1.1), 0.6, 0.15)])
    inhale = sy.bandpass(sy.noise(0.4), 900, 2.0) * sy.env(0.4, 0.15, 0.1, 0.8, 0.12)
    exhale = (sy.bandpass(sy.noise(0.5), 600, 1.5) + sy.roar(0.5, 70, 55, growl=20, rough=0.5, breath=0.2) * 0.4) \
        * sy.env(0.5, 0.03, 0.1, 0.7, 0.25)
    sy.save(pack, "ed_heat_snort", sy.at(1.0, (0.0, sy.norm(inhale) * 0.5), (0.42, sy.norm(exhale))), volume=0.8,
            max_distance=40)
    hiss = sy.highpass(sy.noise(1.6), 1800) * sy.env(1.6, 0.02, 0.3, 0.55, 0.8)
    whistle = sy.osc(sy.sweep(2600, 1700, 1.6), wave_="sine") * sy.env(1.6, 0.05, 0.2, 0.4, 0.8) * 0.12
    sy.save(pack, "ed_heat_hiss", sy.at(1.7, (0.0, sy.norm(hiss + whistle)), (0.05, sy.crack(0.8, 3000, 16) * 0.3)),
            max_distance=56)
    t = sy.t_axis(2.0)
    thrum = (np.sin(2 * np.pi * 46 * t) + 0.5 * np.sin(2 * np.pi * 92 * t) + 0.25 * np.sin(2 * np.pi * 138 * t)) \
        * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t))
    roarair = sy.lowpass(sy.noise(2.0), 420) * (0.6 + 0.4 * np.sin(2 * np.pi * 5.3 * t + 1))
    sy.save(pack, "ed_heat_thrum", sy.fade(sy.norm(thrum + 1.4 * sy.norm(roarair)), 0.15, 0.3), volume=0.9, max_distance=48)
    ign = sy.at(1.8, (0.0, sy.thump(0.9, 90, 32, 0.6)), (0.05, sy.wind(1.5, 200, 1500, 1.4, 0.3) * 0.7),
                (0.1, sy.crack(1.0, 2500, 22) * 0.35), (0.3, sy.whoosh(1.2, 300, 2400) * 0.5))
    sy.save(pack, "ed_heat_ignite", sy.reverb(ign, 1.2, 0.25), max_distance=72)
    step = sy.at(0.6, (0.0, sy.thump(0.5, 72, 30, 0.5)), (0.02, sy.highpass(sy.noise(0.4), 3000) * sy.decay(0.4, 0.12) * 0.25))
    sy.save(pack, "ed_heat_step", step, volume=0.9, max_distance=40,
            variants=[sy.pitch(step, 1.08), sy.pitch(step, 0.93)])
    hit = sy.at(0.7, (0.0, sy.crack(0.35, 3500, 10) * 0.7), (0.0, sy.thump(0.45, 120, 48, 0.8)),
                (0.01, sy.bell(196, 0.6, bright=0.6, inharm=1.3) * 0.25))
    sy.save(pack, "ed_heat_hit", hit, max_distance=48, variants=[sy.pitch(hit, 1.1), sy.pitch(hit, 0.9)])
    skid = sy.at(1.0, (0.0, sy.wind(0.9, 1800, 450, 1.5, 0.2) * sy.env(0.9, 0.02, 0.2, 0.7, 0.4)),
                 (0.0, sy.crack(0.8, 1800, 34) * 0.4), (0.05, sy.thump(0.5, 60, 28, 0.6) * 0.6))
    sy.save(pack, "ed_heat_skid", skid, max_distance=56)
    tt = sy.t_axis(1.8)
    tones = sum(np.sin(2 * np.pi * f * tt + 2 * np.sin(2 * np.pi * (0.7 + i * 0.3) * tt)) for i, f in enumerate((1150, 1310, 1590, 1870)))
    sh = sy.norm(tones) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * tt)) * 0.35 + sy.bandpass(sy.noise(1.8), 2600, 1.5) * 0.4
    sy.save(pack, "ed_heat_shimmer", sy.reverb(sy.fade(sy.norm(sh), 0.4, 0.6), 1.2, 0.3), volume=0.8, max_distance=48)
    wv = sy.at(2.2, (0.0, sy.whoosh(2.0, 150, 1600, 1.2)), (0.0, sy.rumble(2.0, 55) * 0.7),
               (0.1, sy.crack(1.5, 2500, 30) * 0.3), (0.0, sy.thump(0.8, 80, 30, 0.4) * 0.6))
    sy.save(pack, "ed_heat_wave", sy.reverb(wv, 1.3, 0.25), max_distance=80)
    st = sy.highpass(sy.noise(1.8), 3000) * sy.env(1.8, 0.02, 0.4, 0.5, 1.0)
    cool = sy.at(1.9, (0.0, sy.norm(st) * 0.8), (0.2, sy.crack(1.5, 6000, 22) * 0.4), (0.0, sy.whoosh(0.8, 2400, 900) * 0.3))
    sy.save(pack, "ed_heat_cool", cool, max_distance=48)
    dep = sy.at(2.2, (0.0, sy.rumble(2.0, 45)), (0.1, sy.crack(1.6, 1500, 25) * 0.6), (0.6, sy.thump(0.7, 60, 26, 0.5) * 0.7),
                (1.0, sy.norm(sy.highpass(sy.noise(1.0), 2500) * sy.decay(1.0, 0.4)) * 0.3))
    sy.save(pack, "ed_heat_depart", sy.reverb(dep, 1.2, 0.2), max_distance=64)
    gl = sy.at(0.6, (0.0, sy.crack(0.45, 4500, 12)), (0.05, sy.shimmer(0.5, 2600, 6) * 0.3))
    sy.save(pack, "ed_heat_glass", gl, volume=0.6, max_distance=32)
    ln = sy.at(1.2, (0.0, sy.wind(1.1, 150, 700, 1.6, 0.2) * 0.8), (0.0, sy.osc(sy.sweep(55, 75, 1.1), wave_="saw") * 0.15))
    sy.save(pack, "ed_heat_lane", sy.fade(sy.lowpass(ln, 1500), 0.1, 0.3), volume=0.8, max_distance=48)


# ---------------------------------------------------------------- particles
def build_particles(pack):
    fx = particles(pack)
    fx.effect("ed_heat_ember", "ember", count=10, life=(0.8, 1.6), size=(0.09, 0.0), shape=("sphere", 0.8), speed=(0.3, 1.2),
              accel=(0, 1.4, 0), drag=0.8, colors=["#fff2b0ff", "#ff8a24ff", "#c02a0800"])
    fx.effect("ed_heat_haze", "wave", count=5, life=(0.7, 1.2), size=(0.5, 1.2), shape=("box", (1.2, 0.3, 1.2)),
              direction=(0, 1, 0), speed=(0.2, 0.5), accel=(0, 0.8, 0), colors=["#fff1dc00", "#ffe6c855", "#ffd2a000"],
              blend="blend", spin=(360, 30))
    fx.effect("ed_heat_vent", None, sprites=["ember", "glow", "dot"], count=14, life=(0.35, 0.7), size=(0.22, 0.02),
              shape=("sphere", 0.4), speed=(2.5, 5.5), accel=(0, 2.5, 0), drag=2.0,
              colors=["#fffbe0ff", "#ffb040ff", "#ff4a1000"])
    fx.effect("ed_heat_steam", "smoke", count=7, life=(1.4, 2.4), size=(0.4, 1.4), shape=("sphere", 0.6), speed=(0.4, 1.2),
              accel=(0, 1.2, 0), drag=1.2, colors=["#f4efe8cc", "#c9c4bd88", "#9a958f00"], blend="blend", spin=(360, 25))
    fx.effect("ed_heat_step", "ringthin", count=1, life=(0.45, 0.6), size=(0.4, 2.8), facing="emitter_transform_xz",
              colors=["#ffd28acc", "#ff7a2a66", "#ff4a1000"])
    fx.effect("ed_heat_scorch", "puff", count=6, life=(0.6, 1.1), size=(0.3, 0.8), shape=("disc", 0.8), speed=(0.5, 1.4),
              accel=(0, 0.6, 0), drag=1.4, colors=["#3a2a24bb", "#1a121000"], blend="blend", spin=(360, 40))
    fx.effect("ed_heat_spark", "spark", count=16, life=(0.3, 0.7), size=(0.14, 0.0), shape=("sphere", 0.4), speed=(4, 9),
              accel=(0, -9, 0), drag=1.0, colors=["#ffffffff", "#ffc060ff", "#ff401000"], spin=(360, 300))
    fx.effect("ed_heat_horn", "glow", count=1, life=(0.3, 0.45), size=(0.5, 1.6), colors=["#fff6d0ff", "#ff9a3000"])
    fx.effect("ed_heat_slag", "rock", count=9, life=(1.0, 1.8), size=(0.16, 0.08), shape=("sphere", 1.2), speed=(1.0, 3.0),
              accel=(0, -10, 0), drag=0.3, colors=["#ff8a2aff", "#7a1e08ff", "#2a141000"], blend="blend",
              spin=(360, 200), collide=True)
    fx.effect("ed_heat_ring", "ringthin", count=1, life=(0.5, 0.6), size=(0.8, 7.5), facing="emitter_transform_xz",
              colors=["#fff4d0ff", "#ff8a2aaa", "#ff401000"])
    fx.effect("ed_heat_wavefront", None, sprites=["wave", "arc"], count=8, life=(0.5, 0.9), size=(0.6, 1.4),
              shape=("box", (2.5, 0.4, 0.4)), direction=(0, 1, 0), speed=(0.8, 2.0), drag=1.0,
              colors=["#fff8e8aa", "#ffc88066", "#ff8a2a00"], blend="blend", facing="lookat_y")
    fx.effect("ed_heat_skid", "puff", count=12, life=(0.6, 1.2), size=(0.4, 1.0), shape=("disc", 1.2), speed=(1.0, 2.8),
              accel=(0, 0.5, 0), drag=2.0, colors=["#8a7462cc", "#5a4a3e00"], blend="blend", spin=(360, 40))


DRAGON_SOUNDS = {k: f"grimoire.ed_heat_{k}" for k in ("step", "roar", "bellow", "snarl", "snort", "hiss", "thrum", "skid",
                                                      "cool", "depart")}
DRAGON_PARTICLES = {k: f"grimoire:ed_heat_{k}" for k in ("step", "scorch", "haze", "vent", "horn", "ember", "spark",
                                                         "steam", "slag", "skid")}


def build(pack):
    build_particles(pack)
    m, info = build_model()
    anims = build_anims(info)
    pack.actor(ACTOR, m, anims, STATES, always=["breathe"], scale=SCALE, lifetime=LIFETIME, display="Heat Dragon",
               sounds=DRAGON_SOUNDS, particles=DRAGON_PARTICLES, blend=0.2)
    by = {a.name: a for a in anims}
    br = (by["breathe"], 0.0)
    side = ((-90, 6), (35, 14), (150, 16), (0, 82))
    pack.preview("ed_heat_a", m, [[(by["idle"], 0.0), br]], views=side)
    pack.preview("ed_heat_b", m, [[(by["move"], 0.0), br], [(by["move"], 0.15), br], [(by["charge"], 0.3), br]],
                 views=((-90, 4), (40, 12)), skin="ignited")
    pack.preview("ed_heat_c", m, [[(by["ignite"], 1.15), br], [(by["power"], 1.4), br], [(by["depart"], 1.2), br]],
                 views=((-90, 6), (40, 30)), skin="whitehot")

    sm_ = shimmer_model()
    pack.actor("ed_heat_shimmer", sm_, shimmer_anims(), {0: ["hidden"], 1: ["form"], 2: ["hold"], 3: ["part"], 4: ["fade"]},
               always=["ripple"], scale=2.0, lifetime=60, display="Heat Shimmer", blend=0.1)
    wm = wave_model()
    pack.actor("ed_heat_wave", wm, wave_anims(), {0: ["hidden"], 1: ["rise"], 2: ["travel"], 3: ["burst"]},
               always=["surge"], scale=1.4, lifetime=60, display="Superheated Wave", blend=0.1)
    gm = glass_model()
    pack.actor("ed_heat_glass", gm, glass_anims(), {0: ["hidden"], 1: ["appear"], 2: ["hold"], 3: ["fade"]},
               scale=1.0, lifetime=60, display="Vitrified Ground", blend=0.0)
    lm = lane_model()
    vis = [{f"seg{k + 1}": f"q.property('grimoire:len') > {2 * k + 0.5}"} for k in range(LANE_SEGS)]
    pack.actor("ed_heat_lane", lm, lane_anims(), {0: ["hidden"], 1: ["appear"], 2: ["armed"], 3: ["surge"], 4: ["fade"]},
               scale=1.0, lifetime=60, display="Charge Lane", blend=0.0, visibility=vis,
               props={"len": {"type": "float", "range": [0.0, 64.0], "default": 16.0, "client_sync": True}})
    pack.preview("ed_heat_fx", sm_, [None], views=((20, 10),))
    pack.preview("ed_heat_fx2", wm, [None], views=((25, 25),))
    pack.preview("ed_heat_fx3", gm, [None], views=((10, 60),))
    build_sounds(pack)
    print(f"    dragon_heat: {m.cube_count()} cubes, {len(m.order)} bones, tex {m.tex_size}, "
          f"run {RUN_SPEED:.3f} b/s, walk {WALK_SPEED:.3f} b/s")
