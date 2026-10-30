"""
All 3D models of the add-on, described with modelkit.

  Player overlays (rendered on top of the player's own skin, follow every
  vanilla player animation because the bones mirror geometry.humanoid.custom):
      geometry.tribes.overlay.dinosauroid
      geometry.tribes.overlay.anunnaki
      geometry.tribes.overlay.pastafarian
      geometry.tribes.overlay.spacer
  Tribe guardians / projectiles:
      geometry.tribes.raptor          (Dinosauroid pack hunter)
      geometry.tribes.lamassu         (Anunnaki winged guardian)
      geometry.tribes.noodle_avatar   (avatar of the Flying Spaghetti Monster)
      geometry.tribes.meatball        (FSM projectile)
      geometry.tribes.drone           (Spacer combat drone)
"""
import math

from modelkit import (Model, hx, shade, mix, TRANSPARENT, m_solid, m_scales, m_stripes, m_gold,
                      m_metal, m_feather, m_noodle, m_meatball, m_glow, m_flame, m_cloth,
                      m_colander, m_bone)


# --------------------------------------------------------------------------- shared helpers

def humanoid_skeleton(m: Model):
    """Bones mirroring geometry.humanoid.custom so the vanilla player pose drives them."""
    m.bone("root", (0, 0, 0))
    m.bone("waist", (0, 12, 0), "root")
    m.bone("body", (0, 24, 0), "waist")
    m.bone("head", (0, 24, 0), "body")
    m.bone("rightArm", (-5, 22, 0), "body")
    m.bone("leftArm", (5, 22, 0), "body")
    m.bone("rightLeg", (-1.9, 12, 0), "root")
    m.bone("leftLeg", (1.9, 12, 0), "root")


def fill(setp, x0, y0, x1, y1, col):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            setp(x, y, col)


def reptile_eyes(eye="f5d327", pupil="111111", brow="22401b", row=2):
    e, p, b = hx(eye), hx(pupil), hx(brow)

    def d(setp, w, h):
        cx = w // 2
        fill(setp, 0, row - 1, cx - 2, row - 1, b)
        fill(setp, cx + 1, row - 1, w - 1, row - 1, b)
        for x0 in (1, cx + 1):
            fill(setp, x0, row, x0 + 1, row + 1, e)
        setp(2, row, p); setp(2, row + 1, p)
        setp(cx + 1, row, p); setp(cx + 1, row + 1, p)
    return d


def snout_front(nostril="1b2a14", tooth="f4f0de"):
    n, t = hx(nostril), hx(tooth)

    def d(setp, w, h):
        setp(1, 0, n); setp(w - 2, 0, n)
        for x in range(w):
            if x % 2 == 0:
                setp(x, h - 1, t)
    return d


def teeth_row(tooth="f4f0de"):
    t = hx(tooth)

    def d(setp, w, h):
        for x in range(w):
            if x % 2 == 1:
                setp(x, h - 1, t)
    return d


def gem_row(gem="1f4fa8", gem_light="6fa3ff", row=None, step=3):
    g, gl = hx(gem), hx(gem_light)

    def d(setp, w, h):
        r = h // 2 if row is None else row
        for x in range(1, w - 1, step):
            setp(x, r, g)
            setp(x, r - 1 if r > 0 else r, gl)
    return d


def eyeball(pupil="101010", iris="2f6b3a"):
    p, i = hx(pupil), hx(iris)

    def d(setp, w, h):
        cx, cy = w // 2, h // 2
        if w >= 5:
            fill(setp, cx - 1, cy - 1, cx + 1, cy + 1, i)
        setp(cx, cy, p)
    return d


def visor(dark="0b2a4a", light="38e8ff", frame="4a5563"):
    dk, lt, fr = hx(dark), hx(light), hx(frame)

    def d(setp, w, h):
        x0, x1, y0, y1 = 1, w - 2, 2, int(h * 0.62)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = (y - y0) / max(1, (y1 - y0))
                col = mix(lt, dk, 0.35 + t * 0.6)
                setp(x, y, col)
        # glossy highlight streak
        for k in range(3):
            setp(x0 + 1 + k, y0 + k, shade(lt, 0.6))
        for x in range(x0 - 1, x1 + 2):
            setp(x, y0 - 1, fr)
            setp(x, y1 + 1, fr)
    return d


def chest_core(core="38e8ff", ring="1a7f99"):
    c, r = hx(core), hx(ring)

    def d(setp, w, h):
        cx, cy = w // 2, 3
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            setp(cx + dx - 1 if dx < 0 else cx + dx, cy + dy, r)
        fill(setp, cx - 1, cy - 1, cx, cy, c)
        # panel seam lines
        for y in range(6, h - 1):
            setp(cx - 1, y, hx("aab4bf"))
    return d


def sash(col="e8b923", dark="a8740c"):
    c, d_ = hx(col), hx(dark)

    def d(setp, w, h):
        for y in range(h):
            x = int(y * (w - 1) / max(1, h - 1))
            setp(x, y, c)
            setp(min(w - 1, x + 1), y, d_)
    return d


def light_strip(col="38e8ff", vertical=True):
    c = hx(col)

    def d(setp, w, h):
        if vertical:
            for y in range(1, h - 1):
                setp(w // 2, y, c)
        else:
            for x in range(1, w - 1):
                setp(x, h // 2, c)
    return d


def human_face(skin="c89f73", eye="1f4fa8", brow="1d1a2b", lip="8a4a3a"):
    s, e, b, l = hx(skin), hx(eye), hx(brow), hx(lip)

    def d(setp, w, h):
        cx = w // 2
        # brows
        fill(setp, 1, 2, cx - 2, 2, b)
        fill(setp, cx + 1, 2, w - 2, 2, b)
        # almond lapis eyes with white
        for x0 in (2, cx + 1):
            fill(setp, x0, 3, x0 + 1, 3, hx("f4f0de"))
            setp(x0 + (1 if x0 == 2 else 0), 3, e)
            setp(x0, 4, shade(s, -0.25)); setp(x0 + 1, 4, shade(s, -0.25))
        # nose
        fill(setp, cx - 1, 4, cx, 6, shade(s, -0.12))
    return d


# --------------------------------------------------------------------------- player overlays

def overlay_dinosauroid() -> Model:
    m = Model("geometry.tribes.overlay.dinosauroid", seed=11)
    humanoid_skeleton(m)
    sc = m_scales("4f8a3c", "2f5a26", "7fb85a")
    sc_belly = m_scales("4f8a3c", "2f5a26", "7fb85a", belly="e2d29a")
    crest = m_stripes("e8742a", "a8401a", period=2, axis="y")
    claw = m_bone()
    mouth = m_solid("9c3434", 0.05, 0)

    head = m.get("head")
    head.add((-4, 24, -4), (8, 8, 8), sc, inflate=0.6, decals={"north": reptile_eyes()})
    head.add((-3, 25.5, -9.5), (6, 3, 5.2), sc, decals={"north": snout_front(),
                                                     "east": teeth_row(), "west": teeth_row()},
             face_mats={"down": mouth})
    head.add((-2.5, 23.3, -8.9), (5, 1.8, 4.6), sc, pivot=(0, 24.8, -4.4), rotation=(10, 0, 0),
             face_mats={"up": mouth}, decals={"north": teeth_row(), "east": teeth_row(), "west": teeth_row()})
    head.add((-0.5, 32.5, -3.5), (1, 3, 8), crest)
    head.add((-0.5, 30.5, 4.5), (1, 2.5, 2.5), crest)
    head.add((-4.9, 30.6, -4.9), (2.2, 0.8, 1.2), m_solid("2f5a26"))   # brow ridges
    head.add((2.7, 30.6, -4.9), (2.2, 0.8, 1.2), m_solid("2f5a26"))

    body = m.get("body")
    body.add((-4, 12, -2), (8, 12, 4), sc_belly, inflate=0.3)
    for y in (21, 17.5, 14):
        body.add((-0.5, y, 2.3), (1, 2.6, 2.2), crest)

    t1 = m.bone("dino_tail1", (0, 13.5, 2.3), "body", rotation=(-22, 0, 0))
    t1.add((-2, 11.5, 2.3), (4, 4, 6), m_stripes("4f8a3c", "2f5a26", period=3, axis="x"))
    t1.add((-0.5, 15.5, 3.5), (1, 1.5, 3), crest)
    t2 = m.bone("dino_tail2", (0, 13.5, 8.3), "dino_tail1", rotation=(-8, 0, 0))
    t2.add((-1.5, 12, 8.3), (3, 3, 6), m_stripes("4f8a3c", "2f5a26", period=3, axis="x"))
    t2.add((-0.5, 15, 9.5), (1, 1.2, 3), crest)
    t3 = m.bone("dino_tail3", (0, 13.5, 14.3), "dino_tail2", rotation=(-6, 0, 0))
    t3.add((-1, 12.5, 14.3), (2, 2, 5.5), m_stripes("4f8a3c", "e8742a", period=3, axis="x"))

    ra, la = m.get("rightArm"), m.get("leftArm")
    ra.add((-8, 12, -2), (4, 5, 4), sc, inflate=0.35)
    la.add((4, 12, -2), (4, 5, 4), sc, inflate=0.35)
    for z in (-1.8, -0.4, 1.0):
        ra.add((-7.4, 10.2, z), (0.8, 1.8, 0.8), claw)
        la.add((6.6, 10.2, z), (0.8, 1.8, 0.8), claw)

    rl, ll = m.get("rightLeg"), m.get("leftLeg")
    rl.add((-3.9, 0, -2), (4, 6, 4), sc, inflate=0.35)
    ll.add((-0.1, 0, -2), (4, 6, 4), sc, inflate=0.35)
    for x in (-3.6, -2.3, -1.0):
        rl.add((x, 0, -3.4), (0.8, 0.8, 1.4), claw)
    for x in (0.2, 1.5, 2.8):
        ll.add((x, 0, -3.4), (0.8, 0.8, 1.4), claw)
    return m


def overlay_anunnaki() -> Model:
    m = Model("geometry.tribes.overlay.anunnaki", seed=23)
    humanoid_skeleton(m)
    gold = m_gold()
    gold_dark = m_gold("c9961a", "7a520a", "f5d76e")
    lapis = m_solid("1f4fa8", 0.08)
    robe = m_cloth("f3eee0", "e8b923", trim_rows=1)
    robe_long = m_cloth("f3eee0", "e8b923", trim_rows=2)
    beard = m_stripes("1d1a2b", "3b3f7a", period=2, axis="y", var=0.04)

    head = m.get("head")
    head.add((-4.5, 31.2, -4.5), (9, 2, 9), gold, decals={"north": gem_row(), "south": gem_row(),
                                                         "east": gem_row(), "west": gem_row()})
    head.add((-4, 33.2, -4), (8, 2, 8), gold_dark)
    head.add((-3.5, 35.2, -3.5), (7, 2, 7), gold)
    head.add((-2.5, 37.2, -2.5), (5, 1.5, 5), gold_dark)
    head.add((-1, 38.7, -1), (2, 2, 2), m_glow("1f4fa8", "9cc4ff"))
    # horns of divinity on every tier
    for i, (y, x) in enumerate(((31.6, 4.6), (33.6, 4.1), (35.6, 3.6))):
        h = 3.2 - i * 0.6
        head.add((-x - 1.2, y, -1.2), (1.2, h, 1.2), m_bone("efe3c0"), pivot=(-x, y, -0.6), rotation=(0, 0, 28))
        head.add((x, y, -1.2), (1.2, h, 1.2), m_bone("efe3c0"), pivot=(x, y, -0.6), rotation=(0, 0, -28))
    head.add((-3.5, 19.6, -5.3), (7, 5.6, 1.6), beard)
    head.add((-2.5, 18.2, -5.1), (5, 1.6, 1.2), beard)
    head.add((-3, 24.6, -4.9), (6, 1, 0.9), beard)

    body = m.get("body")
    body.add((-4, 12, -2), (8, 12, 4), robe, inflate=0.3, decals={"north": sash()})
    body.add((-4.6, 21.4, -2.6), (9.2, 2.6, 5.2), gold, decals={"north": gem_row(row=1, step=2)})
    body.add((-4.4, 12, -2.4), (8.8, 1.5, 4.8), gold_dark, decals={"north": gem_row(row=0, step=4)})

    feather_up = m_feather("f5d76e", "1f4fa8", "fff6c8", "v+")
    feather_lo = m_feather("f3eee0", "e8b923", "fff6c8", "v+")
    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        up = m.bone(f"anu_wing_{nm}u", (2 * side, 21, 2.6), "body", rotation=(0, 22 * side, 18 * side))
        lo = m.bone(f"anu_wing_{nm}l", (2 * side, 17.5, 2.6), "body", rotation=(0, 18 * side, -22 * side))
        for b, mat, scale in ((up, feather_up, 1.0), (lo, feather_lo, 0.75)):
            py = b.pivot[1]
            segs = ((2, 4, 4), (6, 4, 7), (10, 5, 10))   # (start, width, hang)
            for x0, w, hang in segs:
                x0s, ws, hs = x0 * scale, w * scale, hang * scale
                ox = 2 * side + x0s * side if side > 0 else 2 * side - (x0s + ws)
                b.add((ox, py + 1.2 - hs, 2.6), (ws, hs, 0.5), mat)
            # leading edge bone
            lx = 2 if side > 0 else -2 - 15 * scale
            b.add((lx, py + 1.2, 2.5), (15 * scale, 1, 0.7), gold)

    ra, la = m.get("rightArm"), m.get("leftArm")
    ra.add((-8.5, 21.2, -2.5), (5, 2.6, 5), gold, decals={"north": gem_row(row=1, step=4)})
    la.add((3.5, 21.2, -2.5), (5, 2.6, 5), gold, decals={"north": gem_row(row=1, step=4)})
    ra.add((-8, 13, -2), (4, 3, 4), gold_dark, inflate=0.4)
    la.add((4, 13, -2), (4, 3, 4), gold_dark, inflate=0.4)
    ra.add((-8, 16, -2), (4, 5, 4), robe, inflate=0.3)
    la.add((4, 16, -2), (4, 5, 4), robe, inflate=0.3)

    rl, ll = m.get("rightLeg"), m.get("leftLeg")
    rl.add((-3.9, 0, -2), (4, 12, 4), robe_long, inflate=0.32)
    ll.add((-0.1, 0, -2), (4, 12, 4), robe_long, inflate=0.32)
    rl.add((-3.9, 0, -2), (4, 1.2, 4), lapis, inflate=0.5)
    ll.add((-0.1, 0, -2), (4, 1.2, 4), lapis, inflate=0.5)
    return m


def overlay_pastafarian() -> Model:
    m = Model("geometry.tribes.overlay.pastafarian", seed=37)
    humanoid_skeleton(m)
    noodle = m_noodle()
    noodle_sauce = m_noodle(sauce="c0281b")
    meat = m_meatball()
    col = m_colander()
    rim = m_metal("d7dce3", "8f99a5", panel=5)

    head = m.get("head")
    head.add((-5, 30, -5), (10, 0.8, 10), rim)
    head.add((-4.6, 30.8, -4.6), (9.2, 2.6, 9.2), col)
    head.add((-3.8, 33.4, -3.8), (7.6, 1.0, 7.6), col)
    head.add((-6.6, 31, -1), (1.6, 1, 2), rim)
    head.add((5, 31, -1), (1.6, 1, 2), rim)
    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        st = m.bone(f"fsm_stalk_{nm}", (1.6 * side, 34.4, 0), "head", rotation=(-8, 0, -20 * side))
        st.add((1.6 * side - 0.5, 34.4, -0.5), (1, 6, 1), noodle)
        ey = m.bone(f"fsm_eye_{nm}", (1.6 * side, 40.4, 0), f"fsm_stalk_{nm}")
        ey.add((1.6 * side - 1.5, 40.2, -1.5), (3, 3, 3), m_solid("f6f3ee", 0.04, 0.05),
               decals={"north": eyeball()})

    body = m.get("body")
    body.add((-4, 12, -2), (8, 12, 4), noodle_sauce, inflate=0.3)
    body.add((-1.5, 13.5, -3), (3, 3, 1.2), meat)
    body.add((-2.5, 18.5, -3.1), (2.4, 2.4, 1.4), meat)
    body.add((0.6, 16, -3.1), (2.2, 2.2, 1.4), meat)

    anchors = ((-2.5, 21), (2.5, 21), (-3.0, 16.5), (3.0, 16.5), (-1.2, 13.5), (1.2, 13.5))
    for i, (x, y) in enumerate(anchors):
        side = -1 if x < 0 else 1
        a = m.bone(f"fsm_ten{i}_a", (x, y, 2.3), "body", rotation=(-25 + i * 6, 25 * side, 0))
        a.add((x - 0.5, y - 0.5, 2.3), (1, 1, 5), noodle)
        b = m.bone(f"fsm_ten{i}_b", (x, y, 7.3), f"fsm_ten{i}_a", rotation=(-15, 0, 0))
        b.add((x - 0.45, y - 0.45, 7.3), (0.9, 0.9, 4.5), noodle)
        c = m.bone(f"fsm_ten{i}_c", (x, y, 11.8), f"fsm_ten{i}_b", rotation=(-15, 0, 0))
        c.add((x - 0.4, y - 0.4, 11.8), (0.8, 0.8, 4), noodle)

    ra, la = m.get("rightArm"), m.get("leftArm")
    ra.add((-9, 20.5, -2.5), (5, 4, 5), meat)
    la.add((4, 20.5, -2.5), (5, 4, 5), meat)
    ra.add((-8, 12, -2), (4, 4, 4), noodle, inflate=0.3)
    la.add((4, 12, -2), (4, 4, 4), noodle, inflate=0.3)

    rl, ll = m.get("rightLeg"), m.get("leftLeg")
    rl.add((-3.9, 0, -2), (4, 5, 4), noodle, inflate=0.32)
    ll.add((-0.1, 0, -2), (4, 5, 4), noodle, inflate=0.32)
    return m


def overlay_spacer() -> Model:
    m = Model("geometry.tribes.overlay.spacer", seed=41)
    humanoid_skeleton(m)
    white = m_metal()
    grey = m_metal("b9c2cc", "6f7b88", panel=3)
    dark = m_metal("3b4552", "232a33", panel=4)
    glow = m_glow("1a9fc0", "c9fbff")
    red = m_glow("b3261e", "ffb3a8")

    head = m.get("head")
    head.add((-5, 23.2, -5), (10, 10, 10), white, decals={"north": visor()})
    head.add((-1, 33.2, -4), (2, 0.8, 8.5), grey)
    head.add((-5.8, 25.8, -2), (0.8, 3.4, 4), dark, decals={"east": light_strip(vertical=False),
                                                            "west": light_strip(vertical=False)})
    head.add((5, 25.8, -2), (0.8, 3.4, 4), dark, decals={"east": light_strip(vertical=False),
                                                         "west": light_strip(vertical=False)})
    head.add((3.6, 33.2, 1), (0.6, 4, 0.6), grey)
    head.add((3.4, 37.2, 0.8), (1, 1, 1), red)

    body = m.get("body")
    body.add((-4, 12, -2), (8, 12, 4), white, inflate=0.35, decals={"north": chest_core()})
    body.add((-3.5, 14, 2.4), (7, 9, 3), grey, decals={"south": light_strip()})
    body.add((-3.2, 11.5, 2.9), (2.4, 2.5, 2.4), dark)
    body.add((0.8, 11.5, 2.9), (2.4, 2.5, 2.4), dark)
    body.add((-4, 23, 2.6), (8, 1, 2.4), dark)
    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        fx = -2 if side < 0 else 2
        fl = m.bone(f"space_flame_{nm}", (fx, 11.5, 4.1), "body")
        fl.add((fx - 0.8, 7.0, 3.3), (1.6, 4.5, 1.6), m_flame("e9fdff", "38e8ff", "2b6cff"))

    ra, la = m.get("rightArm"), m.get("leftArm")
    ra.add((-8.6, 21.2, -2.6), (5.2, 2.6, 5.2), white)
    la.add((3.4, 21.2, -2.6), (5.2, 2.6, 5.2), white)
    ra.add((-8, 12, -2), (4, 4.5, 4), dark, inflate=0.35, decals={"north": light_strip(vertical=False)})
    la.add((4, 12, -2), (4, 4.5, 4), dark, inflate=0.35, decals={"north": light_strip(vertical=False)})
    la.add((8.3, 13.5, -1.2), (0.6, 2.4, 2.4), glow)

    rl, ll = m.get("rightLeg"), m.get("leftLeg")
    rl.add((-3.9, 0, -2), (4, 5, 4), white, inflate=0.35)
    ll.add((-0.1, 0, -2), (4, 5, 4), white, inflate=0.35)
    rl.add((-3.9, 6.5, -2.8), (4, 2.2, 0.8), grey)
    ll.add((-0.1, 6.5, -2.8), (4, 2.2, 0.8), grey)
    rl.add((-3.9, 0, -2), (4, 1, 4), dark, inflate=0.5)
    ll.add((-0.1, 0, -2), (4, 1, 4), dark, inflate=0.5)
    return m


# --------------------------------------------------------------------------- guardians

def raptor() -> Model:
    m = Model("geometry.tribes.raptor", seed=53)
    sc = m_scales("3f7f6a", "254a3e", "6fb08f")
    stripe = m_stripes("3f7f6a", "d9672a", period=4, width=1, axis="x")
    belly = m_solid("e6d7a6", 0.05)
    feather = m_stripes("d9672a", "8a3414", period=2, axis="y")
    claw = m_bone()
    mouth = m_solid("9c3434", 0.05, 0)

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 14, 0), "root")
    body.add((-3, 10.5, -6), (6, 7, 12), stripe, face_mats={"down": belly})
    body.add((-0.5, 17.5, -5), (1, 1.5, 10), feather)
    neck = m.bone("neck", (0, 15.5, -5.5), "body", rotation=(-20, 0, 0))
    neck.add((-2, 14, -9.5), (4, 7, 4.5), sc, face_mats={"north": belly})
    head = m.bone("head", (0, 20.5, -8), "neck", rotation=(20, 0, 0))
    eyes = reptile_eyes(row=1)
    head.add((-2.5, 19.5, -12), (5, 4.5, 5.5), sc, decals={"east": eyes, "west": eyes})
    head.add((-1.8, 19.8, -16), (3.6, 2.8, 4.2), sc, decals={"north": snout_front(),
                                                             "east": teeth_row(), "west": teeth_row()},
             face_mats={"down": mouth})
    head.add((-0.5, 24, -11.5), (1, 2.2, 5.5), feather, pivot=(0, 24, -6), rotation=(-12, 0, 0))
    jaw = m.bone("jaw", (0, 19.8, -11.5), "head")
    jaw.add((-1.6, 18.4, -15.6), (3.2, 1.4, 4.4), sc, face_mats={"up": mouth},
            decals={"east": teeth_row(), "west": teeth_row()})

    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        arm = m.bone(f"arm_{nm}", (2.6 * side, 13.5, -5), "body", rotation=(-35, 0, 0))
        arm.add((2.6 * side - 0.75, 9.5, -5.75), (1.5, 4.5, 1.5), sc)
        arm.add((2.6 * side - 0.75, 9.5, -5.75), (1.5, 1.5, 1.5), feather, inflate=0.2)
        arm.add((2.6 * side - 0.3, 8.3, -6.0), (0.6, 1.2, 0.6), claw)
        leg = m.bone(f"leg_{nm}", (2.5 * side, 12.5, 1), "root")
        lx = 2.5 * side - 1.5
        leg.add((lx, 7.5, -1.2), (3, 6.5, 4.2), sc)
        leg.add((lx + 0.5, 2, 1.2), (2, 6, 2), sc, pivot=(2.5 * side, 7.5, 2), rotation=(18, 0, 0))
        leg.add((lx, 0, -2.5), (3, 1.8, 4.5), sc)
        leg.add((lx + 1.0, 1.6, -3.4), (1, 2.6, 1), claw, pivot=(2.5 * side, 1.6, -2.9), rotation=(-30, 0, 0))
        for k in range(3):
            leg.add((lx + k * 1.0, 0, -3.5), (0.8, 0.8, 1.2), claw)

    t1 = m.bone("tail1", (0, 15, 6), "body", rotation=(-8, 0, 0))
    t1.add((-2, 11.5, 6), (4, 5, 7), stripe)
    t2 = m.bone("tail2", (0, 14.5, 13), "tail1", rotation=(-4, 0, 0))
    t2.add((-1.5, 12.5, 13), (3, 3.5, 7), stripe)
    t3 = m.bone("tail3", (0, 14.2, 20), "tail2", rotation=(-3, 0, 0))
    t3.add((-1, 13.2, 20), (2, 2, 7), stripe)
    t3.add((-0.5, 15.2, 21), (1, 1.6, 5), feather)
    return m


def lamassu() -> Model:
    m = Model("geometry.tribes.lamassu", seed=67)
    hide = m_stripes("d8c79a", "b9a575", period=3, axis="y", var=0.05)
    hide_belly = m_solid("c8b484", 0.05)
    gold = m_gold()
    gold_dark = m_gold("c9961a", "7a520a", "f5d76e")
    hoof = m_solid("3a3326", 0.06)
    beard = m_stripes("1d1a2b", "3b3f7a", period=2, axis="y", var=0.04)
    skin = m_solid("c89f73", 0.04, 0.05)
    feather_a = m_feather("f5d76e", "1f4fa8", "fff6c8", "u+")
    feather_b = m_feather("e8b923", "13306b", "fff6c8", "u+")

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 22, 0), "root")
    body.add((-7, 16, -12), (14, 13, 24), hide, face_mats={"down": hide_belly})
    body.add((-7.5, 15, -13), (15, 15, 4), hide)                           # chest
    body.add((-7.6, 26.5, -12.6), (15.2, 2, 25.2), gold_dark, decals={"east": gem_row(), "west": gem_row()})
    body.add((-0.5, 12, 11.5), (1, 15, 1), hide, pivot=(0, 27, 12), rotation=(15, 0, 0))   # tail
    body.add((-1.5, 9, 13.5), (3, 4, 3), beard, pivot=(0, 27, 12), rotation=(15, 0, 0))

    for (nm, x, z) in (("fr", -4.5, -8), ("fl", 4.5, -8), ("br", -4.5, 8), ("bl", 4.5, 8)):
        leg = m.bone(f"leg_{nm}", (x, 17, z), "root")
        leg.add((x - 2, 2.5, z - 2), (4, 15, 4), hide)
        leg.add((x - 2.5, 0, z - 2.5), (5, 2.5, 5), hoof)
        leg.add((x - 2.3, 2.5, z - 2.3), (4.6, 1.2, 4.6), gold)

    head = m.bone("head", (0, 29, -12), "body")
    head.add((-5, 29, -20), (10, 10, 8), skin, decals={"north": human_face()})
    head.add((-4.5, 21.5, -21.2), (9, 8.5, 3), beard)
    head.add((-3.5, 18.5, -20.8), (7, 3, 2.4), beard)
    head.add((-5.6, 28.5, -19.5), (11.2, 8, 7.6), beard, faces=("east", "west", "south"))   # hair at back
    head.add((-5.5, 38.6, -20.5), (11, 2.6, 9), gold, decals={"north": gem_row(), "east": gem_row(), "west": gem_row()})
    head.add((-5, 41.2, -20), (10, 2.6, 8), gold_dark)
    head.add((-4.2, 43.8, -19.2), (8.4, 2.2, 6.4), gold)
    head.add((-3, 46, -18), (6, 1.2, 4), m_glow("1f4fa8", "9cc4ff"))
    for i, y in enumerate((39, 41.6, 44)):
        hh = 3.6 - i * 0.8
        head.add((-6.8, y, -17), (1.4, hh, 1.4), m_bone("efe3c0"), pivot=(-5.6, y, -16.3), rotation=(0, 0, 30))
        head.add((5.4, y, -17), (1.4, hh, 1.4), m_bone("efe3c0"), pivot=(5.6, y, -16.3), rotation=(0, 0, -30))

    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        w = m.bone(f"wing_{nm}", (6.5 * side, 28, -8), "body", rotation=(22, 0, -10 * side))
        x = 6.5 * side - 0.5
        w.add((x, 27, -8), (1, 5, 22), gold, faces=("east", "west", "up", "north", "south"))
        w.add((x, 31.5, -7), (1, 5, 20), feather_a)
        w.add((x, 36, -6), (1, 5, 17), feather_b)
        w.add((x, 40.5, -5), (1, 4, 13), feather_a)
    return m


def noodle_avatar() -> Model:
    m = Model("geometry.tribes.noodle_avatar", seed=79)
    noodle = m_noodle()
    noodle_s = m_noodle(sauce="c0281b")
    meat = m_meatball()

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 20, 0), "root")
    body.add((-8, 14, -6), (16, 10, 12), noodle_s)
    body.add((-6, 24, -5), (12, 3.5, 10), noodle)
    body.add((-10.5, 15, -4), (3, 7, 8), noodle)
    body.add((7.5, 15, -4), (3, 7, 8), noodle)
    body.add((-5, 11, -4), (10, 3, 8), noodle_s)
    body.add((-3, 26.5, -3), (6, 1.5, 6), noodle)
    mb_r = m.bone("meatball_r", (-6, 18, -7), "body")
    mb_r.add((-10, 14, -11), (8, 8, 8), meat)
    mb_r.add((-9.5, 14.5, -11.5), (7, 7, 9), meat)
    mb_l = m.bone("meatball_l", (6, 18, -7), "body")
    mb_l.add((2, 14, -11), (8, 8, 8), meat)
    mb_l.add((2.5, 14.5, -11.5), (7, 7, 9), meat)

    for side in (-1, 1):
        nm = "r" if side < 0 else "l"
        st = m.bone(f"stalk_{nm}", (3 * side, 26, -2), "body", rotation=(-10, 0, -18 * side))
        st.add((3 * side - 0.75, 26, -2.75), (1.5, 11, 1.5), noodle)
        ey = m.bone(f"eye_{nm}", (3 * side, 37, -2), f"stalk_{nm}")
        ey.add((3 * side - 2.5, 36, -4.5), (5, 5, 5), m_solid("f6f3ee", 0.03, 0.06),
               decals={"north": eyeball()})

    n = 8
    for i in range(n):
        ang = 2 * math.pi * i / n
        x, z = round(math.cos(ang) * 6, 2), round(math.sin(ang) * 4, 2)
        y = 12
        a = m.bone(f"ten{i}_a", (x, y, z), "body",
                   rotation=(round(18 * math.sin(ang), 2), 0, round(18 * math.cos(ang), 2)))
        a.add((x - 0.75, y - 7, z - 0.75), (1.5, 7, 1.5), noodle)
        b = m.bone(f"ten{i}_b", (x, y - 7, z), f"ten{i}_a")
        b.add((x - 0.6, y - 13, z - 0.6), (1.2, 6, 1.2), noodle)
        c = m.bone(f"ten{i}_c", (x, y - 13, z), f"ten{i}_b")
        c.add((x - 0.5, y - 18, z - 0.5), (1, 5, 1), noodle)
    return m


def meatball() -> Model:
    m = Model("geometry.tribes.meatball", seed=83)
    meat = m_meatball()
    body = m.bone("ball", (0, 3, 0))
    body.add((-3, 0.5, -3), (6, 5, 6), meat)
    body.add((-2.5, 0, -2.5), (5, 6, 5), meat)
    body.add((-3.4, 1, -2), (6.8, 4, 4), meat)
    body.add((-2, 1, -3.4), (4, 4, 6.8), meat)
    body.add((-3.6, 2.6, -0.4), (7.2, 0.8, 0.8), m_noodle(), pivot=(0, 3, 0), rotation=(0, 35, 20))
    return m


def drone() -> Model:
    m = Model("geometry.tribes.drone", seed=97)
    white = m_metal()
    dark = m_metal("3b4552", "232a33", panel=4)
    orange = m_solid("ff8a2a", 0.05)
    glow = m_glow("1a9fc0", "e9fdff")
    blade = m_solid("2b313a", 0.04, 0)

    m.bone("root", (0, 0, 0))
    body = m.bone("body", (0, 8, 0), "root")
    body.add((-3, 5, -3), (6, 4, 6), white, decals={"east": light_strip(vertical=False),
                                                     "west": light_strip(vertical=False)})
    body.add((-2, 9, -2), (4, 1.5, 4), dark)
    body.add((-1.5, 3.5, -1.5), (3, 1.5, 3), dark)
    body.add((-1.5, 5.5, -3.6), (3, 3, 0.6), glow)
    body.add((-3.2, 4.8, -3.2), (6.4, 0.5, 6.4), orange)
    body.add((1.5, 10.5, 1), (0.4, 3, 0.4), dark)
    body.add((1.3, 13.5, 0.8), (0.8, 0.8, 0.8), m_glow("b3261e", "ffb3a8"))
    for i in range(4):
        arm = m.bone(f"arm{i}", (0, 7.5, 0), "body", rotation=(0, 45 + 90 * i, 0))
        arm.add((2.5, 7, -0.5), (5, 1, 1), dark)
        arm.add((7, 6.5, -1), (2, 2, 2), white)
        rot = m.bone(f"rotor{i}", (8, 8.6, 0), f"arm{i}")
        rot.add((5, 8.6, -0.5), (6, 0.3, 1), blade)
        rot.add((7.5, 8.6, -3), (1, 0.3, 6), blade)
    return m


ALL = {
    "overlay_dinosauroid": overlay_dinosauroid,
    "overlay_anunnaki": overlay_anunnaki,
    "overlay_pastafarian": overlay_pastafarian,
    "overlay_spacer": overlay_spacer,
    "raptor": raptor,
    "lamassu": lamassu,
    "noodle_avatar": noodle_avatar,
    "meatball": meatball,
    "drone": drone,
}
