#!/usr/bin/env python3
"""
Gharvok, the Cliffbreaker - procedural Bedrock geometry, rig and textures.

    python3 tools/gen_model.py

Writes
  addon/resource_packs/dragon_dominion/models/entity/gharvok.geo.json
  addon/resource_packs/dragon_dominion/textures/entity/gharvok_{intact,cracked,broken}.png
  source_models/gharvok.bbmodel                (editable Blockbench project, same cubes / UVs / texture)
  tools/.rig.json                              (bone names + measured sizes, read by the other generators)

Units: 16 = 1 block.  The model faces -Z, +X is the creature's LEFT side, feet stand on y = 0.
Rest pose has the wings fully spread (wingspan measured here); the ground animations fold them.
"""
from __future__ import annotations

import base64
import io
import json
import math
import os
import sys
import uuid

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import modelkit as MK  # noqa: E402
import kinematics as K  # noqa: E402

ROOT = os.path.dirname(HERE)
RP = os.path.join(ROOT, "addon", "resource_packs", "dragon_dominion")
GEO_ID = "geometry.dragon_dominion.gharvok"

m = MK.Model(GEO_ID)
box = m.box
cube = m.cube

# ============================================================================ skeleton + cubes
m.bone("root", None, (0, 0, 0))
m.bone("body", "root", (0, 38, 4))
# abdomen (narrower waist)
box("body", (0, 38, 6), (32, 25, 26), {"down": "belly", "default": "scale"})
box("body", (0, 29, 6), (24, 6, 24), "belly")
m.locator("body", "loc_center", (0, 40, 0))

m.bone("chest", "body", (0, 40, -8))
box("chest", (0, 41, -20), (44, 32, 28), {"down": "belly", "default": "scale"})
box("chest", (0, 27.5, -22), (30, 6, 24), "belly")          # sternum plates
box("chest", (0, 44, -35), (34, 22, 4), {"default": "belly", "up": "scale"})  # throat / chest front
for s in (1, -1):
    box("chest", (19 * s, 51, -20), (12, 12, 24), "scale", rotation=(0, 0, -14 * s))  # shoulder mass

m.bone("pelvis", "body", (0, 40, 18))
box("pelvis", (0, 40, 29), (38, 26, 24), {"down": "belly", "default": "scale"})
box("pelvis", (0, 52, 30), (30, 4, 18), "scale")

# ---------------------------------------------------------------- dorsal osteoderms (back plates)
def dorsal(bone, z, y, h, d, tilt=38, width=3.0, lateral=None, lat_x=None):
    box(bone, (0, y + h / 2 - 1, z), (width, h, d), "plate", rotation=(-tilt, 0, 0), pivot=(0, y, z))
    if lateral:
        lh, ld = lateral
        for s in (1, -1):
            box(bone, (lat_x * s, y - 1 + lh / 2, z + 2), (2.5, lh, ld), "plate",
                rotation=(-tilt - 5, 0, 30 * s), pivot=(lat_x * s, y - 2, z + 2))

dorsal("chest", -30, 56, 9, 9, tilt=30, lateral=(6, 7), lat_x=10)
dorsal("chest", -21, 57, 13, 11, lateral=(8, 8), lat_x=12)
dorsal("chest", -11, 57, 14, 11, lateral=(8, 8), lat_x=13)
dorsal("body", 0, 50, 13, 11, lateral=(8, 8), lat_x=11)
dorsal("body", 11, 50, 12, 10, lateral=(7, 8), lat_x=11)
dorsal("pelvis", 21, 53, 12, 10, lateral=(7, 8), lat_x=12)
dorsal("pelvis", 31, 53, 11, 10, lateral=(6, 7), lat_x=12)
dorsal("pelvis", 39, 51, 9, 8, lateral=(5, 6), lat_x=10)
m.locator("chest", "loc_back", (0, 60, -14))

# ---------------------------------------------------------------- neck (3 segments)
m.bone("neck_1", "chest", (0, 47, -32), (-14, 0, 0))
box("neck_1", (0, 48, -40), (24, 23, 16), {"down": "belly", "default": "scale"})
dorsal("neck_1", -40, 58, 10, 10, lateral=(6, 7), lat_x=10)
m.bone("neck_2", "neck_1", (0, 48, -46), (-8, 0, 0))
box("neck_2", (0, 49, -52), (21, 20, 14), {"down": "belly", "default": "scale"})
dorsal("neck_2", -52, 57, 8, 9, lateral=(5, 6), lat_x=9)
m.bone("neck_3", "neck_2", (0, 49, -57), (12, 0, 0))
box("neck_3", (0, 49, -61), (19, 18, 10), {"down": "belly", "default": "scale"})

# ---------------------------------------------------------------- head: wedge skull + crownshield
m.bone("head", "neck_3", (0, 50, -64), (10, 0, 0))
box("head", (0, 52, -71), (22, 16, 16), {"down": "skin", "default": "skull"})      # cranium
box("head", (0, 51, -87), (16, 10, 18), {"down": "mouth", "default": "skull"})     # upper snout
box("head", (0, 50, -97), (10, 8, 6), {"down": "mouth", "default": "beak"}, rotation=(18, 0, 0),
    pivot=(0, 54, -95))                                                             # hooked beak
box("head", (0, 46, -101), (5, 7, 4), "beak", rotation=(38, 0, 0), pivot=(0, 52, -99))   # beak point
box("head", (0, 58.5, -84), (6, 4, 30), "crown", rotation=(8, 0, 0), pivot=(0, 58, -70))  # nasal keel
for s in (1, -1):
    box("head", (8.5 * s, 59, -76), (9, 5, 15), "crown", rotation=(6, -10 * s, 14 * s))   # brow ridge
    box("head", (11.1 * s, 55, -77), (1, 3, 6), "eye")                                     # recessed eye
    box("head", (11.8 * s, 50, -67), (4, 11, 12), "crown", rotation=(0, 8 * s, 0))        # cheek plate
    box("head", (6.6 * s, 45.2, -88), (1, 2, 16), "teeth")                                 # upper teeth
    box("head", (9.3 * s, 52, -88), (2, 6, 14), "skull", rotation=(0, 6 * s, 0))         # snout flank
m.locator("head", "loc_mouth", (0, 47, -96))
m.locator("head", "loc_brow", (0, 60, -78))
m.locator("head", "loc_eyes", (0, 55, -78))

m.bone("jaw", "head", (0, 47, -66))
box("jaw", (0, 44, -82), (14, 5, 30), {"up": "mouth", "default": "skull", "down": "belly"})
box("jaw", (0, 42.5, -70), (12, 4, 10), "skin")
for s in (1, -1):
    box("jaw", (5.6 * s, 47.5, -84), (1, 2, 20), "teeth")

# crownshield: a fan of bony plates around the back of the skull, swept rearward.
CROWN_PIV = (0, 56, -68)
m.bone("crown", "head", CROWN_PIV)
box("crown", (0, 56, -64), (24, 18, 6), "crown")                     # crown base collar
box("crown", (0, 63, -66), (16, 6, 12), "crown", rotation=(-20, 0, 0))
CROWN_PLATES = []  # (bone, angle)
BREAK = {60: "crown_break_a", 80: "crown_break_a", -40: "crown_break_b", -20: "crown_break_b"}
m.bone("crown_break_a", "crown", CROWN_PIV)
m.bone("crown_break_b", "crown", CROWN_PIV)
m.bone("crown_stubs", "crown", CROWN_PIV)


def crown_plate(bone, ang, r0, length, width, tilt, thick=3.0, mat="crown"):
    px, py, pz = CROWN_PIV
    # base plate, then a narrower tip, then a spike - all pointing "up" before rotation
    cube(bone, (px - width / 2, py + r0, pz - thick / 2), (width, length * 0.55, thick), mat,
         rotation=(-tilt, 0, ang), pivot=CROWN_PIV)
    cube(bone, (px - width * 0.32, py + r0 + length * 0.55, pz - thick * 0.4), (width * 0.64, length * 0.3, thick * 0.8),
         mat, rotation=(-tilt, 0, ang), pivot=CROWN_PIV)
    cube(bone, (px - 1.75, py + r0 + length * 0.8, pz - 1), (3.5, length * 0.24, 2), "crown_tip",
         rotation=(-tilt, 0, ang), pivot=CROWN_PIV)


for ang in range(-100, 101, 20):
    bone = BREAK.get(ang, "crown")
    length = 17 + 7 * abs(math.sin(math.radians(ang)))
    crown_plate(bone, ang, 7, length, 12, 30 + abs(ang) * 0.1)
    CROWN_PLATES.append((bone, ang))
for ang in range(-90, 91, 30):           # inner, shorter ring swept further back over the neck
    crown_plate("crown", ang, 5, 15, 8, 58, thick=2.5)
for ang in (60, 80, -40, -20):           # broken stumps (only visible in the BROKEN state)
    crown_plate("crown_stubs", ang, 7, 9, 12.2, 30 + abs(ang) * 0.1, thick=3.2, mat="crown_break")
m.locator("crown", "loc_crown", (0, 66, -70))

# ---------------------------------------------------------------- forelimbs (left built, right mirrored)
m.bone("arm_l_upper", "chest", (21, 46, -22), (0, 0, -6))
box("arm_l_upper", (25, 35, -22), (14, 24, 15), "scale")
box("arm_l_upper", (31.5, 40, -22), (3, 18, 17), "plate", rotation=(0, 0, -8))
box("arm_l_upper", (30, 47, -26), (3, 10, 8), "plate", rotation=(-30, 0, -40), pivot=(30, 44, -22))
m.bone("arm_l_lower", "arm_l_upper", (26, 24, -21), (-8, 0, 2))
box("arm_l_lower", (26, 14, -21), (11, 21, 12), "scale_dark")
box("arm_l_lower", (31, 15, -21), (2.5, 16, 12), "plate")
box("arm_l_lower", (26, 25, -13), (4, 9, 4), "horn", rotation=(55, 0, 0), pivot=(26, 22, -14))  # elbow spike
m.bone("hand_l", "arm_l_lower", (26, 5, -22), (8, 0, 0))
box("hand_l", (26, 2.5, -26), (16, 5, 15), "scale_dark")
for i, dx in enumerate((-6, -2, 2, 6)):
    box("hand_l", (26 + dx, 2.5, -34.5), (3, 4, 3), "scale_dark")
    box("hand_l", (26 + dx, 2, -38), (2.4, 3, 5), "horn", rotation=(30, 0, 0), pivot=(26 + dx, 3, -36))
m.locator("hand_l", "loc_claw_l", (26, 3, -36))

# ---------------------------------------------------------------- hind legs
m.bone("leg_l_thigh", "pelvis", (19, 44, 28))
box("leg_l_thigh", (24, 34, 27), (15, 26, 21), "scale", rotation=(-12, 0, 0))
box("leg_l_thigh", (31, 37, 28), (3, 16, 16), "plate", rotation=(-12, 0, -6))
m.bone("leg_l_shin", "leg_l_thigh", (24, 23, 24))
box("leg_l_shin", (24, 16, 29), (10, 18, 10), "scale_dark", rotation=(38, 0, 0))
m.bone("leg_l_foot", "leg_l_shin", (24, 10, 35))
box("leg_l_foot", (24, 6, 33), (9, 12, 8), "scale_dark", rotation=(-20, 0, 0))
box("leg_l_foot", (24, 2, 28), (14, 4, 15), "scale_dark")
for dx in (-5, 0, 5):
    box("leg_l_foot", (24 + dx, 1.8, 19), (2.4, 3, 5), "horn", rotation=(25, 0, 0), pivot=(24 + dx, 3, 21))
m.locator("leg_l_foot", "loc_foot_l", (24, 0, 28))

# ---------------------------------------------------------------- wings
SHOULDER = (20, 57, -18)
WRIST = (100, 57, -18)
m.bone("wing_l_arm", "chest", SHOULDER)
box("wing_l_arm", (37, 57, -18), (34, 6, 7), "wing_bone")
box("wing_l_arm", (24, 58, -18), (10, 9, 10), "scale")
m.bone("wing_l_fore", "wing_l_arm", (54, 57, -18))
box("wing_l_fore", (77, 57, -18), (46, 5, 5), "wing_bone")
box("wing_l_fore", (55, 59, -18), (4, 7, 4), "horn", rotation=(-35, 0, 0))   # elbow spur
m.bone("wing_l_hand", "wing_l_fore", WRIST)
box("wing_l_hand", WRIST, (8, 8, 8), "wing_bone")
# big wrist horn: curved forward / up like the reference
box("wing_l_hand", (100, 65, -18), (5, 12, 5), "wing_bone", rotation=(-10, 0, 0), pivot=(100, 60, -18))
box("wing_l_hand", (100, 74, -21), (3.4, 9, 3.4), "horn", rotation=(-45, 0, 0), pivot=(100, 70, -19))
m.locator("wing_l_hand", "loc_wrist_l", (100, 62, -18))

# membranes: thin planes. Inner membrane on arm + forearm with a scalloped trailing edge to the flank.
MEMBRANE_PANELS = []  # (bone, cube, polygon in (x, z) model coords)
def membrane(bone, x0, x1, z0, z1, poly):
    c = cube(bone, (x0, SHOULDER[1], z0), (x1 - x0, 0, z1 - z0), "membrane", faces=("up", "down"), share_updown=True,
             poly=poly)
    MEMBRANE_PANELS.append((bone, c, poly))


FINGERS = [  # name, rest yaw (deg; + = forward), length
    ("wing_l_f1", 12, 46),
    ("wing_l_f2", -18, 52),
    ("wing_l_f3", -45, 54),
    ("wing_l_f4", -72, 50),
]
tips = []
for name, yaw, length in FINGERS:
    a = math.radians(yaw)
    tips.append((WRIST[0] + length * math.cos(a), WRIST[2] - length * math.sin(a)))
# inner membrane: from body flank (20, 24) to f4 tip
f4tip = tips[-1]
inner = [(20, -18), (WRIST[0], -18), (WRIST[0], f4tip[1] - 2), (f4tip[0], f4tip[1]), ("scallop", 10), (20, 22)]
m.bone("wing_l_mem_arm", "wing_l_arm", SHOULDER)
m.bone("wing_l_mem_fore", "wing_l_fore", (54, 57, -18))
membrane("wing_l_mem_arm", 20, 54, -18, 31, inner)
membrane("wing_l_mem_fore", 54, WRIST[0], -18, 31, inner)

for i, (name, yaw, length) in enumerate(FINGERS):
    m.bone(name, "wing_l_hand", WRIST, (0, yaw, 0))
    box(name, (WRIST[0] + length / 2, WRIST[1], WRIST[2]), (length, 2.6, 2.6), "wing_bone")
    box(name, (WRIST[0] + length + 2, WRIST[1] - 1.5, WRIST[2] + 0.5), (5, 2, 2), "horn",
        rotation=(0, -20, 30), pivot=(WRIST[0] + length, WRIST[1], WRIST[2]))           # hooked tip talon
    # membrane fan from this finger back to the next one (or to the forearm line for the last finger)
    nyaw, nlen = (FINGERS[i + 1][1], FINGERS[i + 1][2]) if i + 1 < len(FINGERS) else (-92, 44)
    d = math.radians(yaw - nyaw)
    tip_next = (nlen * math.cos(d), nlen * math.sin(d))       # in this finger's local frame (x along, z behind)
    poly_local = [(0, 0), (length, 0), ("scallop", 6 + 2 * i), tip_next]
    xs = [p[0] for p in poly_local if not isinstance(p[0], str)]
    zs = [p[1] for p in poly_local if not isinstance(p[0], str)]
    poly = [p if isinstance(p[0], str) else (WRIST[0] + p[0], WRIST[2] + p[1]) for p in poly_local]
    membrane(name, WRIST[0], WRIST[0] + max(xs), WRIST[2], WRIST[2] + max(zs) + 0.5, poly)
m.locator("wing_l_f2", "loc_wingtip_l", (WRIST[0] + 50, WRIST[1], WRIST[2]))

# ---------------------------------------------------------------- tail (7 segments + blade)
TAIL = [  # (bone, length, width, height, rest pitch)
    ("tail_1", 12, 22, 20, -10),
    ("tail_2", 11, 18, 16, -6),
    ("tail_3", 10, 15, 13, -4),
    ("tail_4", 10, 12, 11, -2),
    ("tail_5", 10, 10, 9, 0),
    ("tail_6", 9, 8, 7, 2),
    ("tail_7", 9, 6.5, 6, 3),
]
parent, z, y = "pelvis", 38, 42
for i, (name, length, w, h, pitch) in enumerate(TAIL):
    m.bone(name, parent, (0, y, z), (pitch, 0, 0))
    box(name, (0, y, z + length / 2), (w, h, length + 1), {"down": "belly", "default": "scale"})
    tall = 11 - i * 1.1
    box(name, (0, y + h / 2 + tall / 2 - 1.5, z + length * 0.45), (2.5, tall, length * 0.75), "plate",
        rotation=(-40, 0, 0), pivot=(0, y + h / 2 - 1, z + length * 0.45))
    if i < 6:
        for s in (1, -1):
            lw = 6 - i * 0.6
            box(name, (s * (w / 2 + lw / 2 - 1), y + h * 0.15, z + length * 0.5), (lw, 2, 5), "plate",
                rotation=(0, -25 * s, 10 * s), pivot=(s * (w / 2 - 1), y, z + length * 0.5))
    parent, z = name, z + length
    y -= 0
m.bone("tail_blade", parent, (0, y, z), (4, 0, 0))
box("tail_blade", (0, y, z + 9), (22, 3, 18), "plate")                  # broad flattened bony blade
box("tail_blade", (0, y, z + 21), (12, 2.6, 8), "plate")
box("tail_blade", (0, y, z + 28), (5, 2, 8), "crown_tip")
box("tail_blade", (0, y + 3, z + 10), (3, 6, 14), "plate", rotation=(-20, 0, 0))
for s in (1, -1):
    for k, (dz, ln) in enumerate(((4, 9), (12, 8), (20, 6))):
        box("tail_blade", (s * (11 + ln / 2 - 2), y, z + dz), (ln, 2, 3.5), "plate",
            rotation=(0, -35 * s, 0), pivot=(s * 9, y, z + dz))
m.locator("tail_blade", "loc_tail_tip", (0, y, z + 24))

m.mirror(names={"arm_l_upper", "arm_l_lower", "hand_l", "leg_l_thigh", "leg_l_shin", "leg_l_foot",
                "wing_l_arm", "wing_l_fore", "wing_l_hand", "wing_l_mem_arm", "wing_l_mem_fore", "wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4"})
for name in ("arm_l_upper", "leg_l_thigh", "wing_l_arm"):
    pass  # parents of mirrored roots are shared (chest / pelvis)

# mirrored membrane polygons
for bn in list(m.order):
    if not bn.startswith("wing_r"):
        continue
    for c in m.bones[bn].cubes:
        if "poly" in c.params:
            c.params["poly"] = [p if isinstance(p[0], str) else (-p[0], p[1]) for p in c.params["poly"]]

# ============================================================================ textures
TEX_W = 1024


def noise2(shape_pts, scale, rng_seed, octaves=3):
    """Smooth value noise sampled at 3D points (N,3) -> (N,)."""
    out = np.zeros(shape_pts.shape[0])
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        f = (2 ** o) / scale
        p = shape_pts * f
        i = np.floor(p).astype(int)
        t = p - i
        t = t * t * (3 - 2 * t)

        def h(ix, iy, iz):
            v = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (rng_seed * 2654435761 + o * 97)
            v = (v ^ (v >> 13)) * 1274126177
            return ((v ^ (v >> 16)) & 0xFFFF) / 65535.0

        acc = 0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    wgt = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                    acc = acc + wgt * h(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
        out += acc * amp
        tot += amp
        amp *= 0.5
    return out / tot


def face_points(ctx):
    """(h, w, 3) model-space (cube local, pre-rotation) positions of each texel centre."""
    lo, hi = K.cube_corners({"origin": ctx.cube.origin, "size": ctx.cube.size, "inflate": ctx.cube.inflate})
    q = np.array(K.face_quads(lo, hi)[ctx.face], dtype=float)
    U, V = ctx.grid()
    P = q[0][None, None] + (q[1] - q[0])[None, None] * U[..., None] + (q[3] - q[0])[None, None] * V[..., None]
    return P


def hexcol(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def mix(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


def finish(rgb, alpha=None):
    h, w = rgb.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = 255 if alpha is None else alpha
    return out


def face_shade(ctx):
    # bake soft top-lighting: undersides darker, tops a little lighter
    return {"up": 1.06, "down": 0.78}.get(ctx.face, 0.95)


def p_scale(base_a, base_b, dark):
    A, B, D = hexcol(base_a), hexcol(base_b), hexcol(dark)

    def paint(ctx):
        P = face_points(ctx)
        h, w = P.shape[:2]
        flat = P.reshape(-1, 3)
        n = noise2(flat, 18.0, 3).reshape(h, w)
        col = mix(A, B, np.clip((n - 0.3) * 1.8, 0, 1))
        # scales: staggered grid on the face texel grid
        U, V = np.meshgrid(np.arange(w), np.arange(h))
        row = V // 3
        ux = (U + (row % 2) * 2) % 4
        vy = V % 3
        edge = (ux == 0) | (vy == 2)
        cell = (row * 31 + (U + (row % 2) * 2) // 4 * 17) % 7
        col = col * (0.9 + cell[..., None] * 0.03)
        col = np.where(edge[..., None], mix(col, D, 0.55), col)
        hi = (vy == 0) & (ux == 2)
        col = np.where(hi[..., None], col * 1.12, col)
        return finish(col * face_shade(ctx))
    return paint


def p_belly(ctx):
    P = face_points(ctx)
    h, w = P.shape[:2]
    n = noise2(P.reshape(-1, 3), 14.0, 5).reshape(h, w)
    col = mix(hexcol("#a8823f"), hexcol("#c49a52"), n)
    # transverse bands: along the creature's long axis (z) for down faces / along y for front faces
    coord = P[..., 2] if ctx.face in ("down", "up", "east", "west") else P[..., 1]
    band = np.mod(np.floor(coord), 4) == 0
    col = np.where(band[..., None], mix(col, hexcol("#5e4524"), 0.55), col)
    return finish(col * face_shade(ctx))


def plate_like(light, mid, dark, seed, cracks=0, tip_dark=False):
    L, M_, D = hexcol(light), hexcol(mid), hexcol(dark)

    def paint(ctx):
        P = face_points(ctx)
        h, w = P.shape[:2]
        n = noise2(P.reshape(-1, 3), 7.0, seed).reshape(h, w)
        U, V = ctx.grid()
        col = mix(M_, L, np.clip(n * 1.4 - 0.2, 0, 1))
        # weathered streaks following the long axis of the plate
        la = ctx.long_axis_on_face()
        streak_coord = (U if la == "v" else V) * max(w, h)
        streak = (np.sin(streak_coord * 2.1 + n * 6) > 0.85)
        col = np.where(streak[..., None], mix(col, D, 0.35), col)
        # darker toward the edges (weathering)
        e = np.minimum.reduce([U, 1 - U, V, 1 - V]) * min(w, h)
        col = np.where((e < 0.9)[..., None], mix(col, D, 0.45), col)
        if tip_dark:
            col = mix(col, D * 0.75, np.clip((1 - V) * 0.6, 0, 0.6) if ctx.face not in ("up", "down") else 0.2)
        speck = ctx.rng.random((h, w)) < 0.05
        col = np.where(speck[..., None], col * 0.82, col)
        if cracks:
            col = crack_overlay(col, ctx, cracks)
        return finish(col * face_shade(ctx))
    return paint


def crack_overlay(col, ctx, level):
    h, w = col.shape[:2]
    rng = np.random.default_rng(int(abs(hash((ctx.cube.origin, ctx.face))) % (2 ** 31)))
    dark = hexcol("#2a221c")
    raw = hexcol("#8a3f35")
    out = col.copy()
    n_cracks = (1 if level == 1 else 3) * max(1, (w * h) // 120)
    for _ in range(n_cracks):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        ang = rng.uniform(0, math.tau)
        for _ in range(int(rng.integers(4, 10 if level == 1 else 16))):
            ix, iy = int(x), int(y)
            if 0 <= ix < w and 0 <= iy < h:
                out[iy, ix] = dark
                if level == 2 and rng.random() < 0.35:
                    for dx, dy in ((1, 0), (0, 1)):
                        if 0 <= ix + dx < w and 0 <= iy + dy < h:
                            out[iy + dy, ix + dx] = raw
            ang += rng.normal(0, 0.6)
            x += math.cos(ang)
            y += math.sin(ang)
    return out


def p_horn(ctx):
    U, V = ctx.grid()
    la = ctx.long_axis_on_face()
    t = V if la == "v" else U if la == "u" else np.full_like(U, 0.5)
    col = mix(hexcol("#5a4f43"), hexcol("#221e1b"), t)
    return finish(col * face_shade(ctx))


def p_wing_bone(ctx):
    P = face_points(ctx)
    h, w = P.shape[:2]
    n = noise2(P.reshape(-1, 3), 6.0, 11).reshape(h, w)
    col = mix(hexcol("#5b5244"), hexcol("#8f8470"), n)
    U, V = ctx.grid()
    ridge = np.abs(V - 0.5) < 0.18 if ctx.long_axis_on_face() == "u" else np.abs(U - 0.5) < 0.18
    col = np.where(ridge[..., None], col * 1.15, col)
    return finish(col * face_shade(ctx))


def point_in_poly(px, pz, poly):
    """Even-odd test against a polygon given as [(x,z) | ('scallop', depth)] (scallop = concave arc to next pt)."""
    pts = []
    for k, p in enumerate(poly):
        if isinstance(p[0], str):
            a = pts[-1]
            b = poly[(k + 1) % len(poly)]
            depth = p[1]
            # concave arc: bow the edge toward the polygon centroid
            cx = np.mean([q[0] for q in poly if not isinstance(q[0], str)])
            cz = np.mean([q[1] for q in poly if not isinstance(q[0], str)])
            mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dx, dz = cx - mx, cz - mz
            dl = math.hypot(dx, dz) or 1
            for s in np.linspace(0.08, 0.92, 9):
                bow = math.sin(math.pi * s) * depth
                pts.append((a[0] + (b[0] - a[0]) * s + dx / dl * bow, a[1] + (b[1] - a[1]) * s + dz / dl * bow))
        else:
            pts.append(p)
    inside = np.zeros_like(px, dtype=bool)
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        cond = ((z1 > pz) != (z2 > pz)) & (px < (x2 - x1) * (pz - z1) / ((z2 - z1) + 1e-12) + x1)
        inside ^= cond
    return inside


def p_membrane(ctx):
    P = face_points(ctx)
    h, w = P.shape[:2]
    n = noise2(P.reshape(-1, 3), 10.0, 21).reshape(h, w)
    n2 = noise2(P.reshape(-1, 3) * 1.0 + 50, 4.0, 22, octaves=2).reshape(h, w)
    col = mix(hexcol("#9a6440"), hexcol("#7a4a2e"), n)
    blot = n2 > 0.62
    col = np.where(blot[..., None], mix(col, hexcol("#3e2a1e"), 0.75), col)
    # veins radiating from the wrist / shoulder
    rel = P[..., [0, 2]] - np.array([abs(WRIST[0]) * np.sign(P[..., 0].mean() or 1), WRIST[2]])[None, None]
    ang = np.arctan2(rel[..., 1], rel[..., 0])
    vein = np.abs(np.sin(ang * 18 + n * 3)) < 0.07
    col = np.where(vein[..., None], col * 0.75, col)
    alpha = None
    poly = ctx.cube.params.get("poly")
    if poly is not None:
        inside = point_in_poly(P[..., 0], P[..., 2], poly)
        # ragged edge
        edge_noise = ctx.rng.random((h, w)) < 0.06
        alpha = np.where(inside & ~edge_noise | inside & (n > 0.3), 255, 0).astype(np.uint8)
    return finish(col, alpha)


def solid(c, var=0.06):
    C = hexcol(c)

    def paint(ctx):
        col = C * (1 - var + ctx.rng.random((ctx.h, ctx.w, 1)) * var * 2)
        return finish(col * face_shade(ctx))
    return paint


def p_eye(ctx):
    U, V = ctx.grid()
    col = mix(hexcol("#ffbf3a"), hexcol("#c26b12"), V)
    slit = np.abs(U - 0.5) < 0.18
    col = np.where(slit[..., None], hexcol("#1a120c"), col)
    return finish(col)


def painters(level):
    return {
        "scale": p_scale("#5d6450", "#737a62", "#33382c"),
        "scale_dark": p_scale("#4d5343", "#636a55", "#2a2e24"),
        "skin": p_scale("#4f5545", "#5f664f", "#2e3228"),
        "belly": p_belly,
        "plate": plate_like("#cfc6ad", "#a69d86", "#5d574b", 7),
        "skull": plate_like("#bdb49c", "#8f8a78", "#4f4b42", 8, cracks=level),
        "crown": plate_like("#d8cfb6", "#aaa18a", "#5d574b", 9, cracks=level),
        "crown_tip": plate_like("#e2dac4", "#b8ae95", "#6d6656", 10, cracks=level, tip_dark=True),
        "crown_break": plate_like("#d8cfb6", "#9a7f6a", "#3b2a22", 12, cracks=2),
        "beak": plate_like("#bdb49c", "#8f8a78", "#3f3b35", 13, tip_dark=True),
        "horn": p_horn,
        "wing_bone": p_wing_bone,
        "membrane": p_membrane,
        "eye": p_eye,
        "mouth": solid("#5b2420"),
        "teeth": solid("#e6dcc0", 0.04),
    }


# ============================================================================ build
def measure(geo):
    pts = np.concatenate([P for _, _, P, _, _ in K.world_faces(geo, None)])
    pts_nowing = np.concatenate([P for b, _, P, _, _ in K.world_faces(geo, None) if not b.startswith("wing")])
    return pts.min(0), pts.max(0), pts_nowing.min(0), pts_nowing.max(0)


def write_bbmodel(geo, pngs, path):
    """Blockbench 4.x project (bedrock entity format). Bedrock x is negated in Blockbench's space."""
    g = geo["minecraft:geometry"][0]
    d = g["description"]
    elements, groups = [], {}
    for b in g["bones"]:
        grp = {"name": b["name"], "origin": [-b["pivot"][0], b["pivot"][1], b["pivot"][2]],
               "rotation": [-(b.get("rotation", [0, 0, 0])[0]), -(b.get("rotation", [0, 0, 0])[1]),
                            b.get("rotation", [0, 0, 0])[2]],
               "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "bone/" + b["name"])), "export": True,
               "isOpen": False, "visibility": True, "children": [], "parent": b.get("parent")}
        groups[b["name"]] = grp
        for k, c in enumerate(b.get("cubes", [])):
            o, s = c["origin"], c["size"]
            frm = [-(o[0] + s[0]), o[1], o[2]]
            to = [-o[0], o[1] + s[1], o[2] + s[2]]
            piv = c.get("pivot", [o[0] + s[0] / 2, o[1] + s[1] / 2, o[2] + s[2] / 2])
            rot = c.get("rotation", [0, 0, 0])
            faces = {}
            for f in ("north", "east", "south", "west", "up", "down"):
                if f in c["uv"]:
                    (u, v), (w, h) = c["uv"][f]["uv"], c["uv"][f]["uv_size"]
                    faces[f] = {"uv": [u, v, u + w, v + h], "texture": 0}
                else:
                    faces[f] = {"uv": [0, 0, 0, 0], "texture": None}
            eid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cube/{b['name']}/{k}"))
            elements.append({"name": f"{b['name']}_{k}", "box_uv": False, "rescale": False, "locked": False,
                             "from": frm, "to": to, "autouv": 0, "color": k % 8, "inflate": c.get("inflate", 0),
                             "origin": [-piv[0], piv[1], piv[2]], "rotation": [-rot[0], -rot[1], rot[2]],
                             "faces": faces, "type": "cube", "uuid": eid})
            grp["children"].append(eid)
    outliner = []
    for b in g["bones"]:
        grp = groups[b["name"]]
        par = grp.pop("parent")
        (groups[par]["children"] if par else outliner).append(grp)
    textures = []
    for i, (name, png) in enumerate(pngs):
        textures.append({"path": "", "name": name + ".png", "folder": "", "namespace": "", "id": str(i),
                         "width": d["texture_width"], "height": d["texture_height"], "uv_width": d["texture_width"],
                         "uv_height": d["texture_height"], "particle": False, "render_mode": "default",
                         "visible": True, "mode": "bitmap", "saved": True,
                         "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "tex/" + name)), "relative_path": "",
                         "source": "data:image/png;base64," + base64.b64encode(png).decode()})
    bb = {"meta": {"format_version": "4.10", "model_format": "bedrock", "box_uv": False},
          "name": "gharvok", "model_identifier": d["identifier"].replace("geometry.", ""),
          "visible_box": [d["visible_bounds_width"], d["visible_bounds_height"], d["visible_bounds_offset"][1]],
          "variable_placeholders": "", "variable_placeholder_buttons": [], "timeline_setups": [],
          "unhandled_root_fields": {},
          "resolution": {"width": d["texture_width"], "height": d["texture_height"]},
          "elements": elements, "outliner": outliner, "textures": textures}
    with open(path, "w") as f:
        json.dump(bb, f, separators=(",", ":"))


def main():
    used = m.pack(TEX_W, pad=1)
    tex_h = 1 << max(6, math.ceil(math.log2(used)))
    geo = m.to_json(TEX_W, tex_h, 20, 9, [0, 2.5, 0])
    os.makedirs(os.path.join(RP, "models", "entity"), exist_ok=True)
    os.makedirs(os.path.join(RP, "textures", "entity"), exist_ok=True)
    with open(os.path.join(RP, "models", "entity", "gharvok.geo.json"), "w") as f:
        json.dump(geo, f, indent=1)
    pngs = []
    for level, name in enumerate(("intact", "cracked", "broken")):
        img = m.paint(TEX_W, tex_h, painters(level), seed=5)
        im = Image.fromarray(img, "RGBA")
        p = os.path.join(RP, "textures", "entity", f"gharvok_{name}.png")
        im.save(p, optimize=True)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        pngs.append((f"gharvok_{name}", buf.getvalue()))
    write_bbmodel(geo, pngs[:1], os.path.join(ROOT, "source_models", "gharvok.bbmodel"))
    lo, hi, nlo, nhi = measure(geo["minecraft:geometry"][0])
    nb, nc = m.stats()
    rig = {
        "geometry": GEO_ID, "bones": m.order, "cubes": nc, "texture": [TEX_W, tex_h],
        "length_blocks": round((hi[2] - lo[2]) / 16, 2), "height_blocks": round((nhi[1] - nlo[1]) / 16, 2),
        "wingspan_blocks": round((hi[0] - lo[0]) / 16, 2), "body_width_blocks": round((nhi[0] - nlo[0]) / 16, 2),
        "crown_plates": CROWN_PLATES,
        "locators": {ln: bn for bn in m.order for ln in m.bones[bn].locators},
    }
    with open(os.path.join(HERE, ".rig.json"), "w") as f:
        json.dump(rig, f, indent=1)
    print(f"gharvok: {nb} bones, {nc} cubes, texture {TEX_W}x{tex_h} (used {used} rows)")
    print(f"  length {rig['length_blocks']} blocks, height (no wings) {rig['height_blocks']}, "
          f"wingspan {rig['wingspan_blocks']}, body width {rig['body_width_blocks']}")


if __name__ == "__main__":
    main()
