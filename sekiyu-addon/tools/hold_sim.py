#!/usr/bin/env python3
"""Simulates how the held axe (attachable) appears in first and third person.

Built from Mojang's vanilla data (bedrock-samples 1.26.60):
  * player geometry: rightArm pivot (-5,22,0), arm cube (-8,12,-2)+(4,12,4), rightItem pivot (-6,15,1)
  * first person: animation.player.first_person.empty_hand ("defines the base pose even when the
    player is carrying an item") -> rightarm pos (13.5,-10,12) rot (95,-45,115), rightitem pos (0,0,-1)
  * third person: animation.player.holding -> rightarm rot x -18
  * attachable binding: item-space point (0,24,0) sits on the bound bone's pivot. Verified with the
    vanilla shield (its grip lands on (0.6,24.5,-0.2) after its third-person transform), trident,
    and the Microsoft wrench / turret-kit samples.
Math follows Blockbench's Bedrock conversion: x mirrored, rotation Rz(z)*Ry(-y)*Rx(-x).

Adapted from the Grizzly's Oath add-on in this repository; used as a library by tools/preview.py.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_preview import FACES, rx, ry, rz, sample  # noqa: E402

EYE = 25.92  # 1.62 blocks


def rot_i(r):
    x, y, z = (math.radians(v) for v in r)
    return rz(z) @ ry(-y) @ rx(-x)


def I(p):
    return np.array([-p[0], p[1], p[2]], float)


def xform(pivot_f, rot=(0, 0, 0), pos=(0, 0, 0), scale=1.0):
    piv = I(pivot_f)
    R = rot_i(rot)
    off = I(pos)
    s = np.array(scale if isinstance(scale, (list, tuple)) else [scale] * 3, float)
    return lambda p: R @ ((p - piv) * s) + piv + off


ARM_EXTRA = [0.0, 0.0, 0.0]  # additive rightArm rotation (what playAnimation adds)


def player_chain(view):
    if view == "first":
        base = np.array([95, -45, 115], float) + np.array(ARM_EXTRA, float)
        arm = xform((-5, 22, 0), tuple(base), (13.5, -10, 12))
        item = xform((-6, 15, 1), (0, 0, 0), (0, 0, -1))
    else:
        arm = xform((-5, 22, 0), tuple(np.array([-18, 0, 0], float) + np.array(ARM_EXTRA, float)))
        item = xform((-6, 15, 1))
    bind = I((-6, 15, 1)) - np.array([0, 24, 0], float)
    return arm, item, bind


def anim_pose(anim_file, anim_name):
    a = json.load(open(anim_file))["animations"][anim_name]
    pose = {}
    for bone, ch in a.get("bones", {}).items():
        pose[bone] = {k: sample(v, 0) for k, v in ch.items()}
    return pose


def item_quads(geo, pose, view):
    arm, item, bind = player_chain(view)
    bones = {b["name"]: b for b in geo["bones"]}
    cache = {}

    def world(name):
        if name in cache:
            return cache[name]
        b = bones[name]
        p = pose.get(name, {})
        rot = np.array(b.get("rotation", [0, 0, 0]), float) + np.array(p.get("rotation", [0, 0, 0]), float)
        f = xform(b.get("pivot", [0, 0, 0]), rot, p.get("position", [0, 0, 0]), p.get("scale", 1.0))
        if b.get("parent"):
            par = world(b["parent"])
            g = lambda v, f=f, par=par: par(f(v))
        else:
            g = lambda v, f=f: arm(item(f(v) + bind))
        cache[name] = g
        return g

    quads = []
    for b in geo["bones"]:
        W = world(b["name"])
        for c in b.get("cubes", []):
            inf = c.get("inflate", 0)
            o = np.array(c["origin"], float) - inf
            s = np.array(c["size"], float) + 2 * inf
            for face, f in c.get("uv", {}).items():
                sel, ua, va, _ = FACES[face]
                tl = np.where(np.array(sel) == 1, o + s, o)
                p0 = W(I(tl))
                p1 = W(I(tl + np.array(ua, float) * s))
                p2 = W(I(tl + np.array(va, float) * s))
                quads.append((p0, p1 - p0, p2 - p0, f["uv"], f["uv_size"]))
    return quads


def box_quads(fn, o, s):
    o = np.array(o, float)
    s = np.array(s, float)
    quads = []
    for face, (sel, ua, va, _) in FACES.items():
        tl = np.where(np.array(sel) == 1, o + s, o)
        p0 = fn(I(tl))
        quads.append((p0, fn(I(tl + np.array(ua, float) * s)) - p0, fn(I(tl + np.array(va, float) * s)) - p0, None, None))
    return quads


def arm_quads(view):
    arm, _, _ = player_chain(view)
    quads = box_quads(arm, (-8, 12, -2), (4, 12, 4))
    if view != "first":  # stand-in body for third person
        ident = lambda p: p
        quads += box_quads(ident, (-4, 12, -2), (8, 12, 4)) + box_quads(ident, (-4, 24, -4), (8, 8, 8))
        quads += box_quads(ident, (-3.9, 0, -2), (4, 12, 4)) + box_quads(ident, (-0.1, 0, -2), (4, 12, 4))
        quads += box_quads(xform((5, 22, 0), (-18, 0, 0)), (4, 12, -2), (4, 12, 4))
    return quads


def camera(view):
    if view == "first":
        eye = np.array([0, EYE, 0], float)
        f = np.array([0, 0, 1], float)
    else:
        eye = np.array([38, 24, -24], float)
        target = np.array([0, 17, 0], float)
        f = target - eye
        f /= np.linalg.norm(f)
    r = np.cross(f, [0, 1, 0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    if view == "first":
        r = -r if r[0] > 0 else r  # first person: player's right is -x
    return eye, f, r, u


def render(view, geo, tex, pose, W=1000, H=462, vfov=60, bg=(120, 165, 210)):
    tex = np.asarray(tex.convert("RGBA"), float) / 255.0
    TH, TW = tex.shape[:2]
    eye, f, r, u = camera(view)
    if view == "first":
        r = np.array([-1.0, 0, 0])
    focal = (H / 2) / math.tan(math.radians(vfov / 2))
    ys, xs = np.mgrid[0:H, 0:W]
    D = f[None, None, :] + r[None, None, :] * ((xs + 0.5 - W / 2) / focal)[..., None] + u[None, None, :] * ((H / 2 - ys - 0.5) / focal)[..., None]
    img = np.zeros((H, W, 3))
    img[:] = np.array(bg) / 255.0
    depth = np.full((H, W), np.inf)
    quads = item_quads(geo, pose, view) + [(q[0], q[1], q[2], "skin", None) for q in arm_quads(view)]
    for p0, e1, e2, uv, uvs in quads:
        n = np.cross(e1, e2)
        denom = D @ n
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = ((p0 - eye) @ n) / denom
        hit = eye + D * lam[..., None] - p0
        # solve hit = s*e1 + t*e2 (least squares via 2x2 normal equations)
        a11, a12, a22 = e1 @ e1, e1 @ e2, e2 @ e2
        b1, b2 = hit @ e1, hit @ e2
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            continue
        s = (b1 * a22 - b2 * a12) / det
        t = (b2 * a11 - b1 * a12) / det
        ok = (lam > 2.0) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1) & (lam < depth)
        if not ok.any():
            continue
        nn = n / np.linalg.norm(n)
        shade = 0.6 + 0.4 * abs(nn @ np.array([0.3, 0.9, -0.3]) / np.linalg.norm([0.3, 0.9, -0.3]))
        if uv == "skin":
            col = np.array([0.78, 0.6, 0.47]) * shade
            img[ok] = col
            depth[ok] = lam[ok]
            continue
        uu = np.clip(np.floor(uv[0] + s * uvs[0]), 0, TW - 1).astype(int)
        vv = np.clip(np.floor(uv[1] + t * uvs[1]), 0, TH - 1).astype(int)
        texel = tex[vv, uu]
        ok &= texel[..., 3] > 0
        em = texel[..., 3] < 0.5
        col = np.where(em[..., None], texel[..., :3], texel[..., :3] * shade)
        img[ok] = col[ok]
        depth[ok] = lam[ok]
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    d.line([(W / 2 - 8, H / 2), (W / 2 + 8, H / 2)], fill=(255, 255, 255), width=2)
    d.line([(W / 2, H / 2 - 8), (W / 2, H / 2 + 8)], fill=(255, 255, 255), width=2)
    return out
