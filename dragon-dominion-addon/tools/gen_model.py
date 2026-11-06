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

# ============================================================================ skeleton + cubes (v2)
# Silhouette targets read off the reference sheet: a deep, broad chest and shoulder mass close to the ground,
# short thick splayed forelimbs, head carried BELOW the line of the back, a flared crownshield fan behind the
# skull, every surface bristling with pointed bronze plates, and a long tail with spikes on both sides that
# ends in a spearhead blade.


def spike(bone, base, length, width, rot, thick=None, mat="plate", tip="plate_tip", steps=3, pivot=None, r0=0.0,
          flat="z"):
    """A pointed plate grown along local +Y from `base` (+ r0), tapering to a tip, rotated by `rot` about `pivot`
    (default: the base). Stacked, narrowing boxes read as a spike in Minecraft's voxel style."""
    thick = thick if thick is not None else max(1.2, width * 0.32)
    seg = length / steps
    piv = pivot or base
    for k in range(steps):
        f = k / steps
        w = width * (1 - f * 0.72)
        t = thick * (1 - f * 0.4)
        # flat="z": the broad side faces the creature's flank (a sail seen from the side, like the reference's
        # osteoderms); flat="x": the broad side faces forward (crown fan, claws)
        wx, wz = (w, t) if flat == "x" else (t, w)
        cube(bone, (base[0] - wx / 2, base[1] + r0 + k * seg - 0.02, base[2] - wz / 2), (wx, seg + 0.04, wz),
             mat if k < steps - 1 else tip, rotation=rot, pivot=piv)


def side_spikes(bone, x, y, z, length, width, rot, steps=2, mat="plate", tip="plate_tip"):
    """Mirrored pair on a central (unmirrored) bone. rot is given for the LEFT (+X) side."""
    for s in (1, -1):
        spike(bone, (x * s, y, z), length, width, (rot[0], rot[1] * s, rot[2] * s), steps=steps, mat=mat, tip=tip)


m.bone("root", None, (0, 0, 0))
m.bone("body", "root", (0, 42, 6))
box("body", (0, 43, 8), (38, 30, 24), {"down": "belly", "default": "scale"})          # waist
box("body", (0, 30.5, 8), (32, 7, 25), "belly")                                       # ochre underside band
m.locator("body", "loc_center", (0, 44, 0))

m.bone("chest", "body", (0, 44, -8))
box("chest", (0, 47, -17), (50, 40, 30), {"down": "belly", "default": "scale"})       # deep, broad chest
box("chest", (0, 31, -18), (44, 10, 31), "belly")                                     # ochre chest underside
box("chest", (0, 41, -33), (38, 28, 4), "belly")                                      # throat / breast plates
for s in (1, -1):
    box("chest", (22 * s, 61, -16), (17, 17, 27), "scale", rotation=(0, 0, -16 * s))   # shoulder humps

m.bone("pelvis", "body", (0, 44, 20))
box("pelvis", (0, 45, 30), (40, 30, 24), {"down": "belly", "default": "scale"})
box("pelvis", (0, 33, 30), (34, 8, 22), "belly")
box("pelvis", (0, 59, 32), (32, 5, 18), "scale")

# dorsal osteoderms: one big central row + two lateral rows per side, all swept back
for bone, z, y, ln, w in (("chest", -29, 66, 14, 10), ("chest", -19, 70, 19, 12), ("chest", -8, 68, 19, 12),
                          ("body", 3, 58, 17, 11), ("body", 13, 58, 16, 11), ("pelvis", 22, 61, 16, 11),
                          ("pelvis", 31, 61, 14, 10), ("pelvis", 40, 59, 12, 9)):
    spike(bone, (0, y - 1, z), ln, w, (-38, 0, 0))
    side_spikes(bone, 10, y - 3, z + 2, ln * 0.6, w * 0.85, (-42, 0, 36))
    side_spikes(bone, 18, y - 8, z + 3, ln * 0.5, w * 0.8, (-55, 0, 58))
# flank plates: rows of small spikes pointing back and out, giving the reference's bristling sides
for bone, z, ys, x in (("chest", -24, (52, 40), 25), ("chest", -12, (54, 42), 25), ("body", 4, (50, 39), 19),
                       ("body", 14, (49, 38), 19), ("pelvis", 26, (52, 40), 20), ("pelvis", 36, (50, 40), 20)):
    for y in ys:
        for sgn in (1, -1):
            # an overlapping leaf scale lying on the flank, its trailing edge lifted away from the body
            box(bone, (sgn * (x + 0.6), y, z + 3), (2.4, 8, 9), "plate", rotation=(0, -14 * sgn, 0),
                pivot=(sgn * x, y, z - 1))
            box(bone, (sgn * (x + 1.6), y - 0.5, z + 9), (2.0, 4.5, 5), "plate_tip", rotation=(0, -14 * sgn, 0),
                pivot=(sgn * x, y, z - 1))
m.locator("chest", "loc_back", (0, 70, -14))

# ---------------------------------------------------------------- neck (3 segments, carried low)
m.bone("neck_1", "chest", (0, 52, -31), (3, 0, 0))
box("neck_1", (0, 52, -39), (30, 27, 17), {"down": "belly", "default": "scale"})
box("neck_1", (0, 40, -39), (24, 5, 17), "belly")
spike("neck_1", (0, 64, -40), 14, 10, (-40, 0, 0))
side_spikes("neck_1", 10, 61, -39, 9, 7, (-45, 0, 45))
side_spikes("neck_1", 15, 51, -38, 7, 5.5, (-80, 0, 30))
m.bone("neck_2", "neck_1", (0, 51, -46), (0, 0, 0))
box("neck_2", (0, 50, -52), (25, 23, 14), {"down": "belly", "default": "scale"})
box("neck_2", (0, 40, -52), (20, 4, 14), "belly")
spike("neck_2", (0, 60, -52), 12, 9, (-42, 0, 0))
side_spikes("neck_2", 9, 58, -52, 8, 6, (-45, 0, 45))
m.bone("neck_3", "neck_2", (0, 49, -57), (-2, 0, 0))
box("neck_3", (0, 48, -61), (22, 20, 10), {"down": "belly", "default": "scale"})

# ---------------------------------------------------------------- head: wedge skull + beak + crownshield
m.bone("head", "neck_3", (0, 48, -64), (3, 0, 0))
box("head", (0, 50, -72), (24, 17, 16), {"down": "skin", "default": "skull"})              # cranium
box("head", (0, 48, -85), (19, 13, 12), {"down": "mouth", "default": "skull"})             # snout
box("head", (0, 46.5, -96), (14, 10, 11), {"down": "mouth", "default": "skull"})           # muzzle
box("head", (0, 45, -104), (9, 9, 7), {"down": "mouth", "default": "beak"}, rotation=(22, 0, 0), pivot=(0, 49, -101))
box("head", (0, 41, -107.5), (4.5, 8, 4), "beak", rotation=(40, 0, 0), pivot=(0, 46, -105))  # hooked beak point
box("head", (0, 56, -88), (5, 4, 30), "crown", rotation=(12, 0, 0), pivot=(0, 56, -74))       # nasal keel
box("head", (0, 59.5, -71), (6, 5, 16), "crown")                                               # cranial keel
for s in (1, -1):
    box("head", (10.5 * s, 57.5, -79), (10, 6, 15), "crown", rotation=(8, -12 * s, 18 * s))     # flared brow
    box("head", (12.6 * s, 52.5, -80), (0.6, 3, 6), "eye")                                       # recessed eye
    box("head", (11 * s, 48, -91), (2, 7, 16), "skull", rotation=(0, 7 * s, 0))                  # snout flank
    box("head", (8.3 * s, 41.4, -92), (1, 2.2, 22), "teeth")                                     # upper teeth
    spike("head", (12 * s, 46, -69), 12, 7, (-105, 0, 58 * s), mat="crown", tip="crown_tip")      # cheek horn
m.locator("head", "loc_mouth", (0, 42, -104))
m.locator("head", "loc_brow", (0, 58, -80))
m.locator("head", "loc_eyes", (0, 53, -80))

m.bone("jaw", "head", (0, 43, -70))
box("jaw", (0, 40, -89), (16, 5, 38), {"up": "mouth", "default": "skull", "down": "belly"})
box("jaw", (0, 38.5, -74), (14, 5, 10), "skin")
for s in (1, -1):
    box("jaw", (6.9 * s, 43.6, -92), (1, 2.2, 24), "teeth")

CROWN_PIV = (0, 54, -67)
m.bone("crown", "head", CROWN_PIV)
box("crown", (0, 54, -63), (30, 22, 6), "crown")                                          # crown base collar
box("crown", (0, 63, -66), (18, 7, 12), "crown", rotation=(-20, 0, 0))
m.bone("crown_break_a", "crown", CROWN_PIV)
m.bone("crown_break_b", "crown", CROWN_PIV)
m.bone("crown_stubs", "crown", CROWN_PIV)
OUTER = [round(a) for a in np.linspace(-108, 108, 13)]
BREAK = {OUTER[8]: "crown_break_a", OUTER[9]: "crown_break_a", OUTER[3]: "crown_break_b", OUTER[4]: "crown_break_b"}
CROWN_PLATES = []
for ang in OUTER:   # outer fan: longest at the sides, giving the horseshoe / shield outline of the reference
    bone = BREAK.get(ang, "crown")
    ln = 22 + 9 * abs(math.sin(math.radians(ang)))
    spike(bone, CROWN_PIV, ln, 13, (-26 - abs(ang) * 0.08, 0, ang), thick=3.2, r0=8, mat="crown", tip="crown_tip", flat="x")
    CROWN_PLATES.append((bone, ang))
for ang in np.linspace(-92, 92, 9):   # middle ring
    spike("crown", CROWN_PIV, 17, 11, (-44, 0, float(ang)), thick=2.8, r0=6, mat="crown", tip="crown_tip", flat="x")
for ang in np.linspace(-70, 70, 5):   # inner ring, swept back over the neck
    spike("crown", CROWN_PIV, 13, 9, (-64, 0, float(ang)), thick=2.4, r0=5, mat="crown", tip="crown_tip", steps=2, flat="x")
for ang in BREAK:   # broken stumps (only visible in the BROKEN state)
    spike("crown_stubs", CROWN_PIV, 9, 13.4, (-26 - abs(ang) * 0.08, 0, ang), thick=3.4, r0=8, mat="crown_break",
          tip="crown_break", steps=2, flat="x")
m.locator("crown", "loc_crown", (0, 66, -70))

# ---------------------------------------------------------------- forelimbs (left built, right mirrored): thick, armored, splayed
m.bone("arm_l_upper", "chest", (23, 50, -20), (-4, 0, -10))
box("arm_l_upper", (24, 38, -20), (18, 28, 20), "scale")
for (sx, sy, sz, ln, wd, rot) in ((31, 52, -26, 12, 11, (-35, 0, 50)), (32, 48, -15, 11, 10, (-50, 0, 55)),
                                  (32, 41, -24, 9, 9, (-72, 0, 40)), (32, 40, -13, 9, 9, (-75, 0, 40)),
                                  (31, 32, -20, 8, 8, (-85, 0, 30))):
    spike("arm_l_upper", (sx, sy, sz), ln, wd, rot, steps=2)
m.bone("arm_l_lower", "arm_l_upper", (24, 25, -19), (-6, 0, 0))
box("arm_l_lower", (24, 14.5, -18), (15, 22, 16), "scale_dark")
spike("arm_l_lower", (24, 23, -10), 12, 7, (-115, 0, 0))                     # elbow spike, points back
for (sy, sz) in ((20, -14), (13, -20), (9, -12)):
    spike("arm_l_lower", (30.5, sy, sz), 8, 8, (-80, 0, 30), steps=2)
m.bone("hand_l", "arm_l_lower", (24, 5, -20), (6, 0, 0))
box("hand_l", (24, 3, -23), (21, 6, 19), "scale_dark")
for dx in (-7.5, -2.5, 2.5, 7.5):
    box("hand_l", (24 + dx, 3, -34), (4.4, 5, 6), "scale_dark")
    spike("hand_l", (24 + dx, 4, -36.5), 9, 3.8, (108, 0, 0), thick=3.0, mat="claw", tip="claw_tip", flat="x")
m.locator("hand_l", "loc_claw_l", (24, 3, -38))

# ---------------------------------------------------------------- hind legs: heavy thighs for leaping
m.bone("leg_l_thigh", "pelvis", (20, 50, 28), (0, 0, -6))
box("leg_l_thigh", (24, 37, 28), (19, 31, 25), "scale", rotation=(-10, 0, 0))
for (sy, sz, ln) in ((48, 26, 11), (44, 35, 10), (37, 28, 9), (31, 36, 8)):
    spike("leg_l_thigh", (33, sy, sz), ln, ln * 0.9, (-70, 0, 35), steps=2)
m.bone("leg_l_shin", "leg_l_thigh", (25, 23, 24))
box("leg_l_shin", (25, 15.5, 30), (13, 20, 13), "scale_dark", rotation=(36, 0, 0))
spike("leg_l_shin", (25, 18, 36), 9, 6, (-115, 0, 0), steps=2)
m.bone("leg_l_foot", "leg_l_shin", (25, 9, 36))
box("leg_l_foot", (25, 5.5, 33), (11, 11, 9), "scale_dark", rotation=(-22, 0, 0))
box("leg_l_foot", (25, 2.5, 27), (17, 5, 17), "scale_dark")
for dx in (-5.5, 0, 5.5):
    spike("leg_l_foot", (25 + dx, 3.5, 18.5), 8, 3.6, (108, 0, 0), thick=2.8, mat="claw", tip="claw_tip", flat="x")
m.locator("leg_l_foot", "loc_foot_l", (25, 0, 27))

# ---------------------------------------------------------------- wings
SHOULDER = (22, 63, -18)
ELBOW = (58, 63, -18)
WRIST = (108, 63, -18)
m.bone("wing_l_arm", "chest", SHOULDER)
box("wing_l_arm", ((SHOULDER[0] + ELBOW[0]) / 2, 63, -18), (ELBOW[0] - SHOULDER[0], 7, 8), "wing_bone")
box("wing_l_arm", (26, 64, -18), (11, 10, 11), "scale")
spike("wing_l_arm", (40, 66, -18), 8, 5, (-30, 0, 20), steps=2)
m.bone("wing_l_fore", "wing_l_arm", ELBOW)
box("wing_l_fore", ((ELBOW[0] + WRIST[0]) / 2, 63, -18), (WRIST[0] - ELBOW[0], 5.5, 5.5), "wing_bone")
spike("wing_l_fore", (ELBOW[0], 65, -18), 9, 5, (-40, 0, 0), steps=2, mat="wing_bone", tip="claw_tip")  # elbow spur
m.bone("wing_l_hand", "wing_l_fore", WRIST)
box("wing_l_hand", WRIST, (9, 9, 9), "wing_bone")
# the big hooked wrist horn of the reference: rises, then curls forward
spike("wing_l_hand", (WRIST[0], 66, -18), 13, 6, (-8, 0, -8), thick=6, steps=2, mat="wing_bone", tip="wing_bone")
spike("wing_l_hand", (WRIST[0] - 1.8, 78, -19.5), 11, 4.5, (55, 0, -10), thick=4.5, steps=3, mat="claw", tip="claw_tip",
      pivot=(WRIST[0] - 1.8, 78, -19.5))
m.locator("wing_l_hand", "loc_wrist_l", (WRIST[0], 70, -18))

MEMBRANE_PANELS = []  # (bone, cube, polygon in (x, z) model coords)


def membrane(bone, x0, x1, z0, z1, poly):
    c = cube(bone, (x0, SHOULDER[1], z0), (x1 - x0, 0, z1 - z0), "membrane", faces=("up", "down"), share_updown=True,
             poly=poly)
    MEMBRANE_PANELS.append((bone, c, poly))


FINGERS = [  # name, rest yaw (deg; + = forward), length
    ("wing_l_f1", 10, 52),
    ("wing_l_f2", -18, 58),
    ("wing_l_f3", -44, 60),
    ("wing_l_f4", -70, 54),
]
tips = []
for name, yaw, length in FINGERS:
    a = math.radians(yaw)
    tips.append((WRIST[0] + length * math.cos(a), WRIST[2] - length * math.sin(a)))
f4tip = tips[-1]
inner = [(SHOULDER[0], -18), (WRIST[0], -18), (WRIST[0], f4tip[1] - 2), (f4tip[0], f4tip[1]), ("scallop", 11),
         (SHOULDER[0], 26)]
m.bone("wing_l_mem_arm", "wing_l_arm", SHOULDER)
m.bone("wing_l_mem_fore", "wing_l_fore", ELBOW)
membrane("wing_l_mem_arm", SHOULDER[0], ELBOW[0], -18, f4tip[1] + 1, inner)
membrane("wing_l_mem_fore", ELBOW[0], WRIST[0], -18, f4tip[1] + 1, inner)

for i, (name, yaw, length) in enumerate(FINGERS):
    m.bone(name, "wing_l_hand", WRIST, (0, yaw, 0))
    box(name, (WRIST[0] + length / 2, WRIST[1], WRIST[2]), (length, 2.8, 2.8), "wing_bone")
    spike(name, (WRIST[0] + length, WRIST[1], WRIST[2]), 6, 2.6, (0, 0, -100), thick=2.4, steps=2, mat="claw",
          tip="claw_tip", flat="x")                                                                   # hooked tip talon
    nyaw, nlen = (FINGERS[i + 1][1], FINGERS[i + 1][2]) if i + 1 < len(FINGERS) else (-92, 50)
    d = math.radians(yaw - nyaw)
    tip_next = (nlen * math.cos(d), nlen * math.sin(d))
    poly_local = [(0, 0), (length, 0), ("scallop", 7 + 2 * i), tip_next]
    xs = [p[0] for p in poly_local if not isinstance(p[0], str)]
    zs = [p[1] for p in poly_local if not isinstance(p[0], str)]
    poly = [p if isinstance(p[0], str) else (WRIST[0] + p[0], WRIST[2] + p[1]) for p in poly_local]
    membrane(name, WRIST[0], WRIST[0] + max(xs), WRIST[2], WRIST[2] + max(zs) + 0.5, poly)
m.locator("wing_l_f2", "loc_wingtip_l", (WRIST[0] + 58, WRIST[1], WRIST[2]))

# ---------------------------------------------------------------- tail: 8 segments, spikes on both sides, spearhead blade
TAIL = [  # (bone, length, width, height, rest pitch)
    ("tail_1", 12, 26, 22, -9),
    ("tail_2", 11, 22, 18, -5),
    ("tail_3", 10, 18, 15, -3),
    ("tail_4", 10, 15, 12, -2),
    ("tail_5", 9, 12, 10, 0),
    ("tail_6", 9, 10, 8, 1),
    ("tail_7", 8, 8, 7, 2),
    ("tail_8", 8, 7, 6, 2),
]
parent, z, y = "pelvis", 41, 47
for i, (name, length, w, h, pitch) in enumerate(TAIL):
    m.bone(name, parent, (0, y, z), (pitch, 0, 0))
    box(name, (0, y, z + length / 2), (w, h, length + 1), {"down": "belly", "default": "scale"})
    spike(name, (0, y + h / 2 - 1, z + length * 0.45), 14 - i * 1.2, 9 - i * 0.6, (-48, 0, 0),
          steps=3 if i < 4 else 2)
    side_spikes(name, w / 2 - 1, y + h * 0.1, z + length * 0.5, 13 - i * 0.8, 6.5 - i * 0.35, (-62, 0, 78),
                steps=2)
    parent, z = name, z + length
m.bone("tail_blade", parent, (0, y, z), (3, 0, 0))
for dz, wd, th in ((4, 12, 3.2), (11, 20, 3), (18, 16, 2.8), (24, 11, 2.6), (29, 7, 2.4), (33.5, 3.5, 2.2)):
    box("tail_blade", (0, y, z + dz), (wd, th, 7.2), "plate")                      # broad flat spearhead
spike("tail_blade", (0, y + 1, z + 12), 10, 7, (-55, 0, 0), steps=2)
for s in (1, -1):
    spike("tail_blade", (s * 8, y, z + 9), 9, 4, (-60, 0, 80 * s), steps=2)
m.locator("tail_blade", "loc_tail_tip", (0, y, z + 30))

m.mirror(names={"arm_l_upper", "arm_l_lower", "hand_l", "leg_l_thigh", "leg_l_shin", "leg_l_foot",
                "wing_l_arm", "wing_l_fore", "wing_l_hand", "wing_l_mem_arm", "wing_l_mem_fore",
                "wing_l_f1", "wing_l_f2", "wing_l_f3", "wing_l_f4"})

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
    """Overlapping diamond scales (rhombic tiling): each scale lit on its upper edge, shadowed on its lower rim,
    with per-scale colour jitter and large-scale mottling. Reads as reptile hide instead of bricks."""
    A, B, D = hexcol(base_a), hexcol(base_b), hexcol(dark)

    def paint(ctx):
        P = face_points(ctx)
        h, w = P.shape[:2]
        n = noise2(P.reshape(-1, 3), 16.0, 3).reshape(h, w)
        col = mix(A, B, np.clip((n - 0.3) * 1.8, 0, 1))
        U, V = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
        a = (U + V * 1.3) / 4.2
        b = (U - V * 1.3) / 4.2
        fa, fb = a - np.floor(a), b - np.floor(b)
        cell = (np.floor(a).astype(int) * 73 + np.floor(b).astype(int) * 151) % 11
        col = col * (0.88 + cell[..., None] * 0.022)
        lower = np.minimum(fa, fb)          # distance to the scale's lower-left/right rim
        upper = np.minimum(1 - fa, 1 - fb)  # distance to the upper rim
        col = np.where((lower < 0.2)[..., None], mix(col, D, 0.6), col)
        col = np.where((upper < 0.22)[..., None] & (lower >= 0.2)[..., None], col * 1.14, col)
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


def plate_like(light, mid, dark, seed, cracks=0, tip_dark=False, ridge=True):
    """Weathered bronze / bone armour plate: lighter central ridge along the long axis, darker worn edges,
    fine streaks; optional crack overlay for the fracture states."""
    L, M_, D = hexcol(light), hexcol(mid), hexcol(dark)

    def paint(ctx):
        P = face_points(ctx)
        h, w = P.shape[:2]
        n = noise2(P.reshape(-1, 3), 6.0, seed).reshape(h, w)
        U, V = ctx.grid()
        col = mix(M_, L, np.clip(n * 1.3 - 0.15, 0, 1))
        la = ctx.long_axis_on_face()
        across = U if la == "v" else V
        if ridge and la != "n":
            col = mix(col, L * 1.05, np.clip(1 - np.abs(across - 0.5) * 4, 0, 1) * 0.45)
        streak = (np.sin(across * max(w, h) * 2.3 + n * 7) > 0.88)
        col = np.where(streak[..., None], mix(col, D, 0.3), col)
        e = np.minimum.reduce([U, 1 - U, V, 1 - V]) * min(w, h)
        col = np.where((e < 0.9)[..., None], mix(col, D, 0.5), col)
        if tip_dark:
            along = V if la == "v" else U
            col = mix(col, D * 0.8, np.clip((1 - along) * 0.5, 0, 0.5) if ctx.face not in ("up", "down") else 0.15)
        speck = ctx.rng.random((h, w)) < 0.05
        col = np.where(speck[..., None], col * 0.84, col)
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
        "scale": p_scale("#566046", "#6c7452", "#2b3022"),
        "scale_dark": p_scale("#4a5240", "#5d644c", "#24281d"),
        "skin": p_scale("#4e5444", "#5e654e", "#2a2e22"),
        "belly": p_belly,
        "plate": plate_like("#cdb488", "#9a7f57", "#4d3f2c", 7),                    # bronze osteoderms
        "plate_tip": plate_like("#e0cfa6", "#b89c6e", "#5c4c35", 17),
        "skull": plate_like("#c2ae86", "#8f7a58", "#4a3d2c", 8, cracks=level),
        "crown": plate_like("#d4bd90", "#a2875e", "#4d3f2c", 9, cracks=level),
        "crown_tip": plate_like("#e6d7b2", "#bda274", "#5c4c35", 10, cracks=level),
        "crown_break": plate_like("#d4bd90", "#9a7462", "#3b2a22", 12, cracks=2),
        "beak": plate_like("#bba47c", "#8a7454", "#3a3026", 13, tip_dark=True),
        "claw": plate_like("#4a4038", "#2e2925", "#1a1715", 14, ridge=False),
        "claw_tip": plate_like("#d8ccae", "#a89a7c", "#4a4038", 15, ridge=False),
        "horn": p_horn,
        "wing_bone": plate_like("#a8916b", "#7d6a4e", "#3f3427", 11),
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
        # reference points (model units) the combat scripts use, see config.js geometry
        "points": {"head": [0, 50, -72], "mouth": [0, 42, -104], "tail_tip": [0, 47, -(-41 - sum(t[1] for t in TAIL) - 33)]},
    }
    with open(os.path.join(HERE, ".rig.json"), "w") as f:
        json.dump(rig, f, indent=1)
    print(f"gharvok: {nb} bones, {nc} cubes, texture {TEX_W}x{tex_h} (used {used} rows)")
    print(f"  length {rig['length_blocks']} blocks, height (no wings) {rig['height_blocks']}, "
          f"wingspan {rig['wingspan_blocks']}, body width {rig['body_width_blocks']}")


if __name__ == "__main__":
    main()
