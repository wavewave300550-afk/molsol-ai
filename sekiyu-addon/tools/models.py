"""
All Sekiyu models besides the fruit (see fruit_model.py), built with oilkit.

Every model is painted twice from the same layout: STYLE["burning"] = False gives glossy crude
oil (near-black brown, amber sheen, a few glowing fissures), True gives the ignited version
(molten orange veins, glowing crust). Glow is encoded as low texture alpha for the
entity_emissive material (no texel is ever fully transparent).

Models
  oil_body      player overlay (Petroleum Body): shell on the vanilla humanoid skeleton + drips + eyes
  puddle        dissolved player (Petroleum Infiltration)
  serpent       Black Serpent: head with jaws, 10 chained body segments
  tide          Black Tide wave: 8 crest columns across a 6-block front
  prison        Tar Prison: 8 tendrils x 3 segments around a base pool
  pool          oil slick (scaled by the script's radius)
  geyser        Black Geyser eruption column with a splash crown
"""
import math

import numpy as np

import oilkit
from oilkit import Model, fbm

STYLE = {"burning": False}

OIL_DARK = np.array([0.045, 0.03, 0.025])
OIL_BROWN = np.array([0.19, 0.09, 0.04])
AMBER = np.array([0.98, 0.62, 0.14])
FISSURE = np.array([1.0, 0.36, 0.06])
EMBER = np.array([1.0, 0.72, 0.25])


def oil(scale=3.0, seed=1, gloss=1.0, veins=1.0, glow=0.25, tint=None):
    """Glossy crude oil / burning oil painter (3D-noise based, seamless across faces).

    `scale` is in model units per noise cell (x3 internally, so oil reads as large glossy swirls).
    """
    def p(pts, face, u, v):
        q = pts / 3.0
        n1 = fbm(q, scale, seed)
        n2 = fbm(q + 17.3, scale * 0.6, seed + 3)
        n3 = fbm(q * np.array([1, 1.8, 1]) - 4.1, scale * 1.4, seed + 9)
        col = OIL_DARK[None] * (1 - n1[:, None]) + OIL_BROWN[None] * (n1[:, None] ** 2) * 0.9
        # specular sheen: thin bright amber-white streaks, like light on wet crude
        sheen = np.clip((n2 - 0.58) * 5.0, 0, 1) ** 1.5 * gloss
        spec = np.array([1.0, 0.82, 0.55])
        col = col * (1 - sheen[:, None] * 0.6) + spec[None] * sheen[:, None] * 0.55
        vein = np.clip(1 - np.abs(n3 - 0.5) * 60, 0, 1) * veins
        if face == "up":
            col = col * 1.15
        if face == "down":
            col = col * 0.7
        out = np.ones((len(pts), 4), np.float32)
        if STYLE["burning"]:
            hot = np.clip(1 - np.abs(n3 - 0.5) * 7, 0, 1)
            col = col * (1 - hot[:, None]) + (FISSURE * 0.6 + EMBER * 0.4)[None] * hot[:, None]
            out[:, 3] = np.where(hot > 0.4, 0.25, 1.0)
        else:
            col = col * (1 - vein[:, None]) + FISSURE[None] * vein[:, None]
            out[:, 3] = np.where(vein > 0.6, glow, 1.0)
        if tint is not None:
            col = col * tint
        out[:, :3] = np.clip(col, 0, 1)
        return out
    return p


def amber_glow(alpha=0.2):
    def p(pts, face, u, v):
        out = np.ones((len(pts), 4), np.float32)
        out[:, :3] = (EMBER if STYLE["burning"] else AMBER)
        out[:, 3] = alpha
        return out
    return p


def painted_twice(model):
    STYLE["burning"] = False
    normal = model.paint().copy()
    STYLE["burning"] = True
    burning = model.paint().copy()
    STYLE["burning"] = False
    model.texture = normal
    return normal, burning


# --------------------------------------------------------------------------- player oil body

HUMANOID = {
    # bone: (parent, pivot, cube origin, cube size)
    "root": (None, (0, 0, 0), None, None),
    "waist": ("root", (0, 12, 0), None, None),
    "body": ("waist", (0, 24, 0), (-4, 12, -2), (8, 12, 4)),
    "head": ("body", (0, 24, 0), (-4, 24, -4), (8, 8, 8)),
    "rightArm": ("body", (-5, 22, 0), (-8, 12, -2), (4, 12, 4)),
    "leftArm": ("body", (5, 22, 0), (4, 12, -2), (4, 12, 4)),
    "rightLeg": ("root", (-1.9, 12, 0), (-3.9, 0, -2), (4, 12, 4)),
    "leftLeg": ("root", (1.9, 12, 0), (-0.1, 0, -2), (4, 12, 4)),
}
SHELL_BONES = {"body": "oil_torso", "head": "oil_head", "rightArm": "oil_arm_r", "leftArm": "oil_arm_l",
               "rightLeg": "oil_leg_r", "leftLeg": "oil_leg_l"}
DRIPS = [  # (humanoid bone, x, y, z, length) - hanging strands animated by the overlay animation
    ("rightArm", -6.0, 12, -1.0, 3.0), ("rightArm", -7.2, 12, 1.0, 2.0), ("leftArm", 6.0, 12, 0.5, 3.2),
    ("leftArm", 7.0, 12, -1.2, 2.2), ("body", -2.5, 12, -2.6, 2.4), ("body", 1.8, 12, 2.4, 3.0),
    ("head", -2.0, 24, -4.7, 1.8), ("head", 2.6, 24, -4.6, 1.4), ("rightLeg", -2.0, 0.2, -2.6, 1.0),
]


def eyes_painter():
    base = oil(3.0, seed=4)

    def p(pts, face, u, v):
        out = base(pts, face, u, v)
        if face == "north":
            # two glowing amber eye slits on the face
            for ex in (-2.0, 2.0):
                m = (np.abs(pts[:, 0] - ex) < 1.1) & (np.abs(pts[:, 1] - 28.3) < 0.45)
                out[m, :3] = EMBER if STYLE["burning"] else AMBER
                out[m, 3] = 0.15
        return out
    return p


def oil_body():
    m = Model("geometry.sekiyu.oil_body", tpu=2.0)
    shell = oil(2.6, seed=2)
    for name, (parent, pivot, origin, size) in HUMANOID.items():
        m.bone(name, pivot, parent)
        if origin is None:
            continue
        sb = m.bone(SHELL_BONES[name], pivot, name)
        paint = eyes_painter() if name == "head" else shell
        sb.add(origin, size, paint, inflate=0.55)
        # thicker globs so the silhouette reads as liquid, not as a skin recolour
        if name == "body":
            sb.add((-4.5, 18, -2.9), (9, 6, 1), shell, inflate=0.2)
            sb.add((-3, 12.5, 2.0), (6, 7, 1), shell, inflate=0.25)
        if name in ("rightArm", "leftArm"):
            x = origin[0] - 0.4 if name == "rightArm" else origin[0] + 0.4
            sb.add((x, 11.6, -2.2), (4, 3, 4.4), shell, inflate=0.2)
        if name == "head":
            sb.add((-4.4, 30.5, -4.4), (8.8, 2.0, 8.8), shell, inflate=0.2)
    for i, (bone, x, y, z, length) in enumerate(DRIPS):
        d = m.bone(f"oil_drip_{i}", (x, y, z), bone)
        d.add((x - 0.5, y - length, z - 0.5), (1, length, 1), shell)
        d.add((x - 0.75, y - length - 1.2, z - 0.75), (1.5, 1.4, 1.5), amber_glow(0.55) if i % 3 == 0 else shell)
    m.get("oil_torso").locators["drip_chest"] = (0, 14, -2.5)
    return m


def puddle():
    m = Model("geometry.sekiyu.puddle", tpu=2.0)
    root = m.bone("puddle", (0, 0, 0))
    p = oil(3.0, seed=11, glow=0.3)
    rng = np.random.default_rng(3)
    root.add((-8, 0, -8), (16, 1.2, 16), p)
    for _ in range(9):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(5, 9)
        s = rng.uniform(3, 6)
        root.add((math.cos(a) * r - s / 2, 0, math.sin(a) * r - s / 2), (s, rng.uniform(0.6, 1.0), s), p)
    hump = m.bone("puddle_hump", (0, 0, 0), "puddle")
    hump.add((-4, 0.5, -4), (8, 2.6, 8), p)
    hump.add((-2.5, 2.5, -2.5), (5, 1.4, 5), p)
    for i, (x, z) in enumerate(((-4, 3), (3, -4), (5, 4), (-5, -3))):
        b = m.bone(f"bubble_{i}", (x, 1.2, z), "puddle")
        b.add((x - 0.8, 1.0, z - 0.8), (1.6, 1.6, 1.6), p)
    eye = m.bone("puddle_eyes", (0, 3.0, -3.5), "puddle_hump")
    eye.add((-2.2, 3.2, -3.6), (1.2, 0.5, 0.4), amber_glow(0.15))
    eye.add((1.0, 3.2, -3.6), (1.2, 0.5, 0.4), amber_glow(0.15))
    return m


# --------------------------------------------------------------------------- Black Serpent

SERPENT_SEGMENTS = 10


def serpent():
    m = Model("geometry.sekiyu.serpent", tpu=1.5, max_tex=512)
    skin = oil(4.0, seed=21, glow=0.3)
    belly = oil(3.0, seed=23, gloss=0.4, veins=0.3, tint=np.array([1.3, 1.1, 0.9]))
    m.bone("root", (0, 0, 0))
    # neck rises in an S from the ground; head at the front (-Z is the entity's facing)
    neck = m.bone("neck", (0, 40, -6), "root")
    neck.add((-9, 30, -10), (18, 18, 16), skin)
    neck.add((-8, 22, -2), (16, 14, 10), skin)
    head = m.bone("head", (0, 50, -12), "neck")
    head.add((-10, 44, -36), (20, 13, 26), skin)               # skull
    head.add((-8, 45, -46), (16, 9, 11), skin)                 # snout
    head.add((-11, 55, -33), (5, 3, 15), skin)                 # brow ridges
    head.add((6, 55, -33), (5, 3, 15), skin)
    head.add((-10.2, 52, -36.3), (3.6, 2.2, 1), amber_glow(0.12))  # eyes
    head.add((6.6, 52, -36.3), (3.6, 2.2, 1), amber_glow(0.12))
    for x in (-6.5, 4.5):                                      # upper fangs
        head.add((x, 40, -45.5), (2, 5, 2), amber_glow(0.5))
    jaw = m.bone("jaw", (0, 44, -14), "head")
    jaw.add((-9.5, 38, -44), (19, 6, 28), belly)
    for x in (-6.0, 4.0):
        jaw.add((x, 43.5, -43), (2, 3.5, 2), amber_glow(0.5))
    # hood frills
    head.add((-16, 40, -20), (6, 18, 8), skin)
    head.add((10, 40, -20), (6, 18, 8), skin)
    # body chain trailing behind (+Z), tapering; segment i pivots at its front
    prev = "neck"
    z = 4.0
    y = 26.0
    for i in range(SERPENT_SEGMENTS):
        w = 18 - i * 1.2
        h = 16 - i * 1.0
        length = 14.0
        y_i = max(h / 2, y - i * 7.0)   # descends to the ground over the first segments
        seg = m.bone(f"seg_{i}", (0, y_i, z), prev)
        seg.add((-w / 2, y_i - h / 2, z), (w, h, length + 1.0), skin)
        seg.add((-w / 2 + 1, y_i - h / 2 - 0.6, z + 1), (w - 2, 1.2, length - 1), belly)
        seg.add((-1, y_i + h / 2 - 0.2, z + 3), (2, 1.6, 4), skin)   # dorsal ridge
        if i % 3 == 1:
            seg.add((w / 2 - 1.2, y_i - h / 2 - 2.5, z + 5), (1, 2.5, 1), amber_glow(0.5))  # drip
        prev = f"seg_{i}"
        z += length
    return m


# --------------------------------------------------------------------------- Black Tide

def tide():
    m = Model("geometry.sekiyu.tide", tpu=1.2, max_tex=512)
    p = oil(5.0, seed=31, glow=0.3)
    crest = oil(3.0, seed=33, gloss=1.6, veins=1.4, glow=0.25)
    m.bone("wave", (0, 0, 0))
    cols = 8
    width = 96
    cw = width / cols
    for i in range(cols):
        x0 = -width / 2 + i * cw
        hfac = (1.0 - abs(i - (cols - 1) / 2) / cols * 0.7) * (0.92 + 0.08 * math.sin(i * 2.1))
        H = 56 * hfac
        b = m.bone(f"col_{i}", (x0 + cw / 2, 0, 8), "wave")
        b.add((x0, 0, -10), (cw + 0.4, 5, 40), p)                       # spreading base slick
        # rising back slope in steps (back is +Z), steepening towards the crest
        for k, (dz, dy, dh, dd) in enumerate(((14, 4, 0.30, 16), (8, 4 + H * 0.25, 0.30, 14), (3, 4 + H * 0.5, 0.25, 12))):
            b.add((x0, dy, dz - 10), (cw + 0.4, H * dh, dd), p)
        c = m.bone(f"crest_{i}", (x0 + cw / 2, 4 + H * 0.72, -2), f"col_{i}", rotation=(-18, 0, 0))
        c.add((x0, 4 + H * 0.70, -10), (cw + 0.4, H * 0.2, 14), crest)   # lip leaning forward (-Z)
        c.add((x0 + 0.5, 4 + H * 0.58, -16), (cw - 0.6, H * 0.14, 8), crest)  # curling tip
        c.add((x0 + cw * 0.4, 4 + H * 0.46, -15.5), (1.6, 6, 1.6), amber_glow(0.5))  # crest drip
    return m


# --------------------------------------------------------------------------- Tar Prison

TENDRIL_BEND = -24  # rest pose pitch of the upper tendril segments (curl inward over the target)


def prison():
    m = Model("geometry.sekiyu.prison", tpu=1.5)
    p = oil(3.0, seed=41, glow=0.3, gloss=0.6)
    base = m.bone("prison", (0, 0, 0))
    base.add((-20, 0, -20), (40, 1.5, 40), p)
    base.add((-14, 1, -14), (28, 1.5, 28), p)
    for i in range(8):
        a = i / 8 * math.tau
        x, z = math.cos(a) * 16, math.sin(a) * 16
        yaw = -math.degrees(a) + 90
        t0 = m.bone(f"tendril_{i}", (x, 1, z), "prison", rotation=(0, round(yaw, 2), 0))
        t0.add((x - 2.5, 1, z - 2.5), (5, 14, 5), p)
        t1 = m.bone(f"tendril_{i}_b", (x, 15, z), f"tendril_{i}", rotation=(TENDRIL_BEND, 0, 0))
        t1.add((x - 2, 15, z - 2), (4, 13, 4), p)
        t2 = m.bone(f"tendril_{i}_c", (x, 28, z), f"tendril_{i}_b", rotation=(TENDRIL_BEND * 1.4, 0, 0))
        t2.add((x - 1.5, 28, z - 1.5), (3, 11, 3), p)
        t2.add((x - 0.8, 38, z - 0.8), (1.6, 3, 1.6), amber_glow(0.45))
    return m


# --------------------------------------------------------------------------- oil pool & geyser

def pool():
    m = Model("geometry.sekiyu.pool", tpu=1.5)
    p = oil(3.5, seed=51, glow=0.35, gloss=1.4)
    root = m.bone("pool", (0, 0, 0))
    rng = np.random.default_rng(5)
    root.add((-11, 0.05, -11), (22, 0.6, 22), p)
    for _ in range(10):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(9, 13)
        s = rng.uniform(4, 8)
        root.add((math.cos(a) * r - s / 2, 0.02, math.sin(a) * r - s / 2), (s, 0.5, s), p)
    for i in range(3):
        b = m.bone(f"pool_bubble_{i}", (0, 0.5, 0), "pool")
        x, z = rng.uniform(-7, 7, 2)
        b.add((x - 0.9, 0.4, z - 0.9), (1.8, 1.2, 1.8), p)
    return m


def geyser():
    m = Model("geometry.sekiyu.geyser", tpu=1.0)
    p = oil(4.0, seed=61, glow=0.3, gloss=1.5)
    root = m.bone("geyser", (0, 0, 0))
    root.add((-14, 0, -14), (28, 2, 28), p)
    col = m.bone("column", (0, 0, 0), "geyser")
    for k, (w, y0, h) in enumerate(((16, 0, 40), (13, 38, 36), (10, 72, 30), (7, 100, 16))):
        col.add((-w / 2, y0, -w / 2), (w, h, w), p, rotation=(0, k * 22.5, 0), pivot=(0, y0, 0))
    crown = m.bone("crown", (0, 112, 0), "column")
    for i in range(6):
        a = i / 6 * math.tau
        x, z = math.cos(a) * 7, math.sin(a) * 7
        crown.add((x - 2.5, 108, z - 2.5), (5, 5, 5), p, rotation=(0, round(math.degrees(a), 1), 30), pivot=(x, 108, z))
    return m


ALL = {
    "oil_body": oil_body,
    "puddle": puddle,
    "serpent": serpent,
    "tide": tide,
    "prison": prison,
    "pool": pool,
    "geyser": geyser,
}
