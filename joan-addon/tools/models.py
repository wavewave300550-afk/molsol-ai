"""
All entity models of the add-on, built with modelkit.

    joan      - BOSS 001 Joan of Arc (armour, royal mantle, halo, war banner with
                a 6-bone cloth chain, tatters and streamers, phase II chains)
    standard  - phantom standard planted by Convergence of the Standard
    stake     - the pyre of Road to the Stake (post, chains, faggots, flames)
    waystone  - Lily Waystone (floating fleur-de-lis node that reverses a road)
    seraph    - Seraph Light (path-bound projectile of Heaven's Detour)

Echoes (Martyr's Procession) reuse the Joan geometry with the ghost texture.
"""
from __future__ import annotations

import math

import materials as M
from art import fleur_mask
from modelkit import Model, hx, mix

# --------------------------------------------------------------------------- shared constants
BANNER_X = -5.9          # pole axis x (right hand)
POLE_BOTTOM = -3.0
POLE_TOP = 53.0
CLOTH_TOP = 52.0
CLOTH_Z0 = 0.55
CLOTH_SEG = 5.0
CLOTH_N = 6
CLOTH_H0, CLOTH_H1 = 18.0, 11.0     # hoist / fly height of the banner
TATTERS = [(17.0, "cloth_3"), (22.5, "cloth_4"), (27.0, "cloth_5")]


def fleur_decal(size_w: int, size_h: int, color, outline=None, cx: float = 0.5, cy: float = 0.5):
    mask = fleur_mask(size_w, size_h)

    def dec(setp, w, h, variant):
        if variant.startswith("glow") or variant == "ghost":
            return
        col = color if variant != "burning" else mix(color, hx("6a4a20"), 0.35)
        ox = int(w * cx - size_w / 2)
        oy = int(h * cy - size_h / 2)
        for y in range(size_h):
            for x in range(size_w):
                if mask[y][x]:
                    shade_row = 0.18 if y < size_h * 0.4 else 0.0
                    setp(ox + x, oy + y, mix(col, hx("fff6c8"), shade_row))
                elif outline is not None:
                    if any(0 <= x + dx < size_w and 0 <= y + dy < size_h and mask[y + dy][x + dx]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        setp(ox + x, oy + y, outline)
    return dec


def hair_fringe() -> M.Painter:
    base = M.hair()

    def p(f):
        if not f.glow and f.y >= f.h - 1 and (f.x % 3 == 1):
            return (0, 0, 0, 0)          # jagged bangs
        return base(f)
    return p


# =========================================================================== Joan
def joan() -> Model:
    m = Model("geometry.joan.joan_of_arc", seed=1431, ppu=2)
    steel = M.steel()
    steel_trim = M.steel(trim=True)
    steel_dk = M.steel(dark=0.25, spec=0.12)
    gold = M.gold()
    gold_r = M.gold(rivets=True)
    blue = M.royal_blue()
    blue_ermine = M.royal_blue(ermine_hem=6, trim_rows=0)
    leather = M.leather()
    hair = M.hair()

    root = m.bone("root", (0, 0, 0))
    root.locators["feet"] = (0, 0.2, 0)

    # ------------------------------------------------------------------ hips & skirt
    hips = m.bone("hips", (0, 15, 0), "root")
    hips.add((-4.5, 13.9, -2.65), (9, 1.6, 5.3), leather)
    hips.add((-1.2, 13.8, -3.0), (2.4, 1.8, 0.45), gold_r)                     # buckle
    hips.add((-4.7, 11.2, -2.85), (9.4, 2.8, 5.7), steel_trim)                 # fauld
    hips.add((-4.55, 10.3, -2.7), (9.1, 1.0, 5.4), steel_dk)                   # lower lame
    tf = m.bone("tabard_f", (0, 13.9, -2.95), "hips")
    tf.add((-2.5, 3.6, -3.25), (5.0, 10.3, 0.35), M.royal_blue(trim_rows=2),
           decals={"north": [fleur_decal(7, 8, M.GOLD, cx=0.5, cy=0.55)]})
    tb = m.bone("tabard_b", (0, 13.9, 2.95), "hips")
    tb.add((-3.0, 4.6, 2.9), (6.0, 9.3, 0.35), M.royal_blue(trim_rows=2))
    for side, name in ((-1, "tasset_r"), (1, "tasset_l")):
        t = m.bone(name, (side * 2.6, 11.2, -2.7), "hips")
        x0 = -4.95 if side < 0 else 0.35
        t.add((x0, 7.9, -3.05), (4.6, 3.4, 0.7), steel_trim)
        t.add((x0 + 0.3, 7.3, -3.0), (4.0, 0.7, 0.6), gold)

    # ------------------------------------------------------------------ torso
    torso = m.bone("torso", (0, 15, 0), "hips")
    torso.add((-4.3, 14.6, -2.45), (8.6, 1.3, 4.9), steel_dk)                  # waist lames
    torso.add((-4.4, 15.6, -2.55), (8.8, 10.2, 5.1), steel)                    # cuirass
    torso.add((-3.7, 16.6, -3.1), (7.4, 8.4, 0.6), steel_trim,
              decals={"north": [fleur_decal(11, 12, M.GOLD, outline=hx("8a5a10"), cy=0.48)]})
    torso.add((-3.8, 17.2, 2.5), (7.6, 7.4, 0.45), steel)                      # backplate
    torso.add((-3.0, 25.5, -2.25), (6.0, 2.0, 4.5), steel_trim)                # gorget
    torso.add((-3.2, 27.0, -2.45), (6.4, 0.5, 4.9), gold)                      # gorget rim
    torso.locators["chest"] = (0, 21, -3.2)
    torso.locators["back"] = (0, 22, 3.2)

    # ------------------------------------------------------------------ mantle (royal blue, ermine)
    cape = m.bone("cape", (0, 26.4, 2.75), "torso")
    cape.add((-5.0, 25.2, 1.9), (10.0, 1.7, 1.5), M.flat_color("f4f2ea", ghost_alpha=140))   # ermine collar
    cape.add((-4.8, 16.9, 2.75), (9.6, 8.6, 0.45), blue)
    cl = m.bone("cape_lower", (0, 16.9, 2.95), "cape")
    cl.add((-5.0, 8.6, 2.8), (10.0, 8.3, 0.4), blue_ermine)

    # ------------------------------------------------------------------ head
    head = m.bone("head", (0, 27, 0), "torso")
    head.add((-3.5, 27.0, -3.5), (7, 8, 7), hair, face_mats={"north": M.face(), "down": M.skin()})
    head.add((-3.9, 33.0, -3.9), (7.8, 2.45, 7.8), hair)                        # crown of the bob
    head.add((-3.7, 32.85, -4.06), (7.4, 0.6, 0.5), hair_fringe())              # bangs
    head.add((-4.02, 28.3, -3.62), (0.62, 4.8, 7.4), hair)                      # side bob (right)
    head.add((3.4, 28.3, -3.62), (0.62, 4.8, 7.4), hair)                        # side bob (left)
    head.add((-3.9, 28.0, 3.38), (7.8, 5.1, 0.62), hair)                        # back of the bob
    head.locators["eyes"] = (0, 31.5, -3.8)
    head.locators["crown"] = (0, 36, 0)

    halo = m.bone("halo", (0, 32.2, 5.4), "head")
    R = 5.3
    for k in range(8):
        halo.add((-2.2, 32.2 + R - 0.35, 5.05), (4.4, 0.7, 0.7), M.halo(), pivot=(0, 32.2, 5.4),
                 rotation=(0, 0, k * 45))
    for k in range(4):
        a = math.radians(k * 90)
        cx, cy = math.sin(a) * R, math.cos(a) * R
        halo.add((cx - 0.55, 32.2 + cy - 0.55, 4.75), (1.1, 1.1, 0.6), M.gem("4a86ff"))
    halo.locators["halo"] = (0, 32.2, 5.4)

    # ------------------------------------------------------------------ arms
    for side in (-1, 1):
        s = "r" if side < 0 else "l"
        X = lambda x0, w: (x0 if side < 0 else -x0 - w)   # noqa: E731  mirror an origin x
        arm = m.bone(f"arm_{s}", (side * 5.0, 25.5, 0), "torso")
        arm.add((X(-8.7, 4.6), 24.4, -3.05), (4.6, 2.3, 6.1), steel_trim)        # pauldron dome
        arm.add((X(-9.05, 4.4), 22.4, -3.25), (4.4, 2.2, 6.5), steel)            # flared lame
        arm.add((X(-9.15, 0.5), 22.6, -1.0), (0.5, 1.8, 2.0), gold)               # rivet strip
        arm.add((X(-8.9, 1.1), 24.9, -0.55), (1.1, 1.1, 1.1), M.gem("2f5fe0"))   # enamel boss
        arm.add((X(-7.6, 3.4), 18.6, -1.7), (3.4, 4.6, 3.4), steel)              # rerebrace
        fa = m.bone(f"forearm_{s}", (side * 5.9, 18.6, 0), f"arm_{s}")
        fa.add((X(-8.0, 4.0), 17.3, -1.9), (4.0, 2.4, 3.8), steel_trim)          # couter
        fa.add((X(-8.35, 0.6), 16.7, 0.1), (0.6, 3.4, 2.6), gold)                # couter fan
        fa.add((X(-7.5, 3.3), 13.1, -1.65), (3.3, 4.4, 3.3), steel)              # vambrace
        hand = m.bone(f"hand_{s}", (side * 5.9, 13.0, 0), f"forearm_{s}")
        hand.add((X(-7.95, 4.1), 11.9, -2.05), (4.1, 1.5, 4.1), steel_trim)      # cuff
        hand.add((X(-7.6, 3.4), 9.4, -1.75), (3.4, 2.6, 3.5), steel_dk)          # gauntlet
        hand.locators[f"hand_{s}"] = (side * 5.9, 10.5, -0.5)
        chain = m.bone(f"chain_{s}", (side * 5.9, 12.0, 0), f"hand_{s}")
        iron = M.flat_color("4a4642", glow="ff8a2a", glow_variant="glow2")
        chain.add((X(-8.1, 4.4), 11.3, -2.2), (4.4, 0.9, 4.4), iron)             # manacle
        for i in range(4):
            yy = 10.6 - i * 1.25
            if i % 2 == 0:
                chain.add((X(-8.6, 0.4), yy - 1.1, -0.6), (0.4, 1.2, 1.2), iron)
            else:
                chain.add((X(-8.9, 1.0), yy - 1.1, -0.2), (1.0, 1.2, 0.4), iron)

    # ------------------------------------------------------------------ legs
    for side in (-1, 1):
        s = "r" if side < 0 else "l"
        X = lambda x0, w: (x0 if side < 0 else -x0 - w)   # noqa: E731
        leg = m.bone(f"leg_{s}", (side * 2.15, 15.0, 0), "root")
        leg.add((X(-4.2, 4.1), 8.6, -2.15), (4.1, 6.6, 4.3), steel)              # cuisse
        shin = m.bone(f"shin_{s}", (side * 2.15, 8.6, 0), f"leg_{s}")
        shin.add((X(-4.4, 4.5), 7.3, -2.75), (4.5, 2.6, 2.0), steel_trim)        # poleyn
        shin.add((X(-4.75, 0.6), 6.9, -1.3), (0.6, 3.0, 2.4), gold)              # poleyn wing
        shin.add((X(-4.0, 3.7), 1.4, -2.0), (3.7, 6.2, 4.0), steel)              # greave
        shin.add((X(-4.2, 4.1), 0.0, -3.4), (4.1, 1.6, 5.4), steel_dk)           # sabaton
        shin.add((X(-3.65, 3.0), 0.0, -4.35), (3.0, 1.0, 1.0), steel)            # pointed toe

    # ------------------------------------------------------------------ the war banner (right hand)
    banner = m.bone("banner", (BANNER_X, 10.9, 0), "hand_r")
    wood = M.wood()
    banner.add((BANNER_X - 0.55, POLE_BOTTOM, -0.55), (1.1, POLE_TOP - POLE_BOTTOM, 1.1), wood)
    for y in (6.0, 22.0, 38.0, 47.0):
        banner.add((BANNER_X - 0.72, y, -0.72), (1.44, 0.8, 1.44), gold)
    banner.add((BANNER_X - 0.78, POLE_BOTTOM - 0.4, -0.78), (1.56, 1.8, 1.56), gold)   # ferrule
    # finial: a golden lily
    banner.add((BANNER_X - 1.0, 52.4, -1.0), (2.0, 0.8, 2.0), gold_r)                   # collar
    banner.add((BANNER_X - 0.45, 53.2, -0.45), (0.9, 4.2, 0.9), gold)                   # centre petal
    banner.add((BANNER_X - 0.25, 57.4, -0.25), (0.5, 0.8, 0.5), gold)                   # tip
    for side in (-1, 1):
        banner.add((BANNER_X + side * 1.3 - 0.45, 53.9, -0.35), (0.9, 2.2, 0.7), gold,
                   pivot=(BANNER_X + side * 0.4, 53.6, 0), rotation=(0, 0, side * 28))
    banner.add((BANNER_X - 1.2, 53.4, -0.4), (2.4, 0.5, 0.8), gold)                    # band
    banner.add((BANNER_X - 0.35, 55.0, -0.95), (0.7, 0.7, 0.4), M.gem("3a76ff"))
    banner.locators["banner_top"] = (BANNER_X, 57.5, 0)
    banner.locators["banner_mid"] = (BANNER_X, 40.0, 14.0)
    banner.locators["banner_foot"] = (BANNER_X, POLE_BOTTOM, 0)

    cloth = M.BannerCloth(CLOTH_Z0, CLOTH_SEG * CLOTH_N, CLOTH_TOP, CLOTH_H0, CLOTH_H1)
    parent = "banner"
    for i in range(CLOTH_N):
        z = CLOTH_Z0 + i * CLOTH_SEG
        h = math.ceil(cloth.height_at(i * CLOTH_SEG) + 1.0)
        b = m.bone(f"cloth_{i}", (BANNER_X, CLOTH_TOP, z), parent)
        b.add((BANNER_X, CLOTH_TOP - h, z), (0, h, CLOTH_SEG), cloth, faces=("east",))
        parent = b.name
    m.get("cloth_5").locators["cloth_tip"] = (BANNER_X, CLOTH_TOP - 6, CLOTH_Z0 + CLOTH_SEG * CLOTH_N)
    for k, (s_at, par) in enumerate(TATTERS):
        bottom = CLOTH_TOP - cloth.height_at(s_at) + 0.6
        z = CLOTH_Z0 + s_at
        t = m.bone(f"tatter_{k}", (BANNER_X, bottom, z), par)
        t.add((BANNER_X, bottom - 2.8, z - 0.7), (0, 2.8, 1.4), M.BannerTatter(), faces=("east",))
    # blue streamers tied under the finial
    for k, dx in enumerate((-0.6, 0.6)):
        r1 = m.bone(f"ribbon_{k}", (BANNER_X + dx, 52.2, 0.0), "banner")
        r1.add((BANNER_X + dx, 45.2, -0.5), (0, 7.0, 1.0), M.ribbon(), faces=("east",))
        r2 = m.bone(f"ribbon_{k}b", (BANNER_X + dx, 45.2, 0.0), f"ribbon_{k}")
        r2.add((BANNER_X + dx, 40.2, -0.5), (0, 5.0, 1.0), M.ribbon(tip=True), faces=("east",))
    return m


# =========================================================================== phantom standard
def standard() -> Model:
    m = Model("geometry.joan.phantom_standard", seed=7, ppu=2)
    root = m.bone("root", (0, 0, 0))
    pole = m.bone("pole", (0, 0, 0), "root")
    pole.add((-0.55, -4, -0.55), (1.1, 44, 1.1), M.wood())
    pole.add((-1.0, 39.6, -1.0), (2.0, 0.8, 2.0), M.gold(rivets=True))
    pole.add((-0.45, 40.4, -0.45), (0.9, 3.4, 0.9), M.gold())
    for side in (-1, 1):
        pole.add((side * 1.2 - 0.45, 40.9, -0.35), (0.9, 1.8, 0.7), M.gold(), pivot=(side * 0.4, 40.6, 0),
                 rotation=(0, 0, side * 28))
    pole.locators["top"] = (0, 44, 0)
    pole.locators["base"] = (0, 0.2, 0)
    cloth = M.BannerCloth(0.55, 16.0, 39.4, 12.0, 8.0)
    parent = "pole"
    for i in range(4):
        z = 0.55 + i * 4
        h = math.ceil(cloth.height_at(i * 4) + 1)
        b = m.bone(f"cloth_{i}", (0, 39.4, z), parent)
        b.add((0, 39.4 - h, z), (0, h, 4), cloth, faces=("east",))
        parent = b.name
    # cracked-earth socket where it is planted
    sock = m.bone("socket", (0, 0, 0), "root")
    for k in range(6):
        a = k * 60
        sock.add((-0.6, 0.0, 1.0), (1.2, 0.5, 3.2), M.flat_color("6a5a48", glow="9fd2ff"), pivot=(0, 0, 0),
                 rotation=(0, a, 0))
    return m


# =========================================================================== the stake (pyre)
def stake() -> Model:
    m = Model("geometry.joan.stake", seed=1431, ppu=2)
    root = m.bone("root", (0, 0, 0))
    post = m.bone("post", (0, 0, 0), "root")
    w = M.wood()
    post.add((-1.6, 0, -1.6), (3.2, 58, 3.2), w)
    post.add((-2.6, 48, -2.0), (5.2, 3.0, 0.5), M.flat_color("d9cfb6", glow="ffb35c", glow_variant="glow2"))  # placard
    iron = M.flat_color("4c4844", glow="ff8a2a", glow_variant="glow2")
    for y in (16.0, 19.0, 30.0):
        post.add((-2.0, y, -2.0), (4.0, 1.0, 4.0), iron)
    for i in range(5):
        post.add((-2.3 + (i % 2) * 3.9, 20.0 + i * 1.6, -0.5), (0.7, 1.3, 1.0), iron)
    post.locators["top"] = (0, 58, 0)
    post.locators["bind"] = (0, 24, -2.2)
    pile = m.bone("pile", (0, 0, 0), "root")
    # radial faggots (bundled sticks) in two rings
    for ring, (r, n, tilt, ln) in enumerate(((5.0, 10, -42, 15.0), (9.5, 14, -26, 15.0), (14.0, 18, -12, 12.0))):
        for k in range(n):
            a = k * 360 / n + ring * 13
            pile.add((-1.3, 0.0, r - 1.0), (2.6, 2.2, ln), M.wood(), pivot=(0, 0, r - 1.0),
                     rotation=(tilt, a, 0))
            pile.add((-1.4, 0.4, r + 1.5), (2.8, 1.4, 0.6), M.flat_color("7a6a3a"), pivot=(0, 0, r - 1.0),
                     rotation=(tilt, a, 0))   # binding cord
    pile.locators["fire"] = (0, 6, 0)
    fl = m.bone("flames", (0, 0, 0), "root")
    flame = M.ember_flame()
    for k in range(12):
        a = k * 30
        r = 4.0 + (k % 3) * 2.5
        h = 14 + (k % 4) * 6
        fl.add((-3.5, 2.0, r), (7.0, h + 8, 0), flame, pivot=(0, 0, 0), rotation=(0, a, 0), faces=("north",))
    return m


# =========================================================================== lily waystone
def waystone() -> Model:
    m = Model("geometry.joan.waystone", seed=5, ppu=2)
    root = m.bone("root", (0, 0, 0))
    lily = m.bone("lily", (0, 16, 0), "root")
    g = M.gold()
    lily.add((-1.5, 13.0, -1.0), (3.0, 7.0, 2.0), g)          # centre petal body
    lily.add((-1.0, 20.0, -0.8), (2.0, 2.4, 1.6), g)
    lily.add((-0.5, 22.4, -0.5), (1.0, 1.4, 1.0), g)
    for side in (-1, 1):
        lily.add((side * 3.2 - 1.0, 15.0, -0.8), (2.0, 5.0, 1.6), g, pivot=(side * 1.5, 13.0, 0),
                 rotation=(0, 0, side * 30))
        lily.add((side * 5.0 - 0.8, 17.6, -0.7), (1.6, 2.6, 1.4), g, pivot=(side * 5.0, 19.0, 0),
                 rotation=(0, 0, -side * 35))
    lily.add((-4.0, 12.0, -1.2), (8.0, 1.4, 2.4), M.gold(rivets=True))   # band
    lily.add((-0.9, 8.6, -0.8), (1.8, 3.4, 1.6), g)                       # foot
    for side in (-1, 1):
        lily.add((side * 2.2 - 0.8, 9.6, -0.7), (1.6, 2.6, 1.4), g, pivot=(side * 1.2, 12.0, 0),
                 rotation=(0, 0, side * 25))
    lily.add((-0.9, 15.0, -1.45), (1.8, 1.8, 0.5), M.gem("4a86ff"))      # heart gem
    lily.locators["core"] = (0, 15.5, 0)
    ring = m.bone("ring", (0, 15.5, 0), "root")
    for k in range(10):
        ring.add((-1.6, 15.2, 8.0), (3.2, 0.6, 0.6), M.halo(), pivot=(0, 15.5, 0), rotation=(0, k * 36, 0))
    return m


# =========================================================================== seraph light
def seraph() -> Model:
    m = Model("geometry.joan.seraph_light", seed=9, ppu=2)
    root = m.bone("root", (0, 4, 0))
    core = m.bone("core", (0, 4, 0), "root")
    core.add((-1.5, 2.5, -1.5), (3, 3, 3), M.halo())
    core.add((-0.5, 5.5, -0.5), (1, 1.6, 1), M.gold())
    core.locators["core"] = (0, 4, 0)
    for k, (name, rz) in enumerate((("wing_r", 1), ("wing_l", -1))):
        w = m.bone(name, (rz * -1.5, 4.5, 0), "core")
        x0 = -7.5 if rz > 0 else 1.5
        w.add((x0, 3.0, 0), (6.0, 4.0, 0), M.seraph_wing(), faces=("north",))
    for k, (name, sx) in enumerate((("wing_r2", 1), ("wing_l2", -1))):
        w = m.bone(name, (sx * -1.5, 3.5, 0), "core")
        x0 = -6.0 if sx > 0 else 1.5
        w.add((x0, 1.0, 0), (4.5, 3.0, 0), M.seraph_wing(), faces=("north",))
    return m


ALL = {
    "joan": joan,
    "standard": standard,
    "stake": stake,
    "waystone": waystone,
    "seraph": seraph,
}

# texture variants painted for every model, and their render layers
VARIANTS = {
    "joan": ["base", "burning", "ghost", "white", "glow1", "glow2"],
    "standard": ["ghost", "glow1"],
    "stake": ["base", "burning", "white", "glow2"],
    "waystone": ["base", "glow1", "glow2"],
    "seraph": ["base", "glow1", "glow2"],
}
