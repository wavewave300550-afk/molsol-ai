#!/usr/bin/env python3
"""Storyboards of every attack / skill, rendered from what the real scripts emit.

    node tools/fx_preview/scenes.mjs && python3 tools/fx_preview/render.py

Uses: tools/fx_preview/.scenes.json (particles, animations, spawned entities, player track),
the pack's particle atlas, the axe / grizzly geometry + textures and the player animations. The
particle motion mirrors the particle JSON written by tools/fx_assets.py (lifetime, speed, drag,
gravity, size and colour curves, facing mode, flipbooks).
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RP = os.path.join(ROOT, "addon", "resource_packs", "grizzly_oath")
sys.path.insert(0, os.path.dirname(HERE))
import anim_sample  # noqa: E402
from hold_sim import I, rot_i, xform  # noqa: E402
from render_preview import FACES  # noqa: E402

W, H = 960, 540
VFOV = 62


def load_json(*p):
    return json.load(open(os.path.join(*p)))


ATLAS = np.asarray(Image.open(os.path.join(RP, "textures", "particle", "grizzly_oath_fx.png")).convert("RGBA"), float) / 255.0
AXE_GEO = load_json(RP, "models", "entity", "grizzlys_oath.geo.json")["minecraft:geometry"][0]
BEAR_GEO = load_json(RP, "models", "entity", "oath_grizzly.geo.json")["minecraft:geometry"][0]
TEX = {
    "axe": np.asarray(Image.open(os.path.join(RP, "textures", "attachables", "grizzlys_oath.png")).convert("RGBA"), float) / 255,
    "axe_awake": np.asarray(Image.open(os.path.join(RP, "textures", "attachables", "grizzlys_oath_awakened.png")).convert("RGBA"), float) / 255,
    "bear": np.asarray(Image.open(os.path.join(RP, "textures", "entity", "oath_grizzly.png")).convert("RGBA"), float) / 255,
    "shade": np.asarray(Image.open(os.path.join(RP, "textures", "entity", "grizzly_shade.png")).convert("RGBA"), float) / 255,
}
PANIMS = load_json(RP, "animations", "grizzly_oath.player.animation.json")["animations"]
_HOLDS = load_json(RP, "animations", "grizzlys_oath.attachable.animation.json")["animations"]
HOLD = _HOLDS["animation.grizzlys_oath.hold_third_person"]["bones"]["grizzlys_oath"]
HOLD_FP = _HOLDS["animation.grizzlys_oath.hold_first_person"]["bones"]["grizzlys_oath"]
BEAR_ANIM = load_json(RP, "animations", "oath_grizzly.animation.json")["animations"]["animation.oath_grizzly.ultimate"]
SHADE_ANIM = load_json(RP, "animations", "grizzly_shade.animation.json")["animations"]["animation.grizzly_shade.roar"]


# ----------------------------------------------------------------------------- camera / raster

class Cam:
    def __init__(self, eye, target):
        self.eye = np.array(eye, float)
        f = np.array(target, float) - self.eye
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0, 1, 0])
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)
        self.focal = (H / 2) / math.tan(math.radians(VFOV / 2))
        ys, xs = np.mgrid[0:H, 0:W]
        self.D = (self.f[None, None, :] + self.r[None, None, :] * ((xs + 0.5 - W / 2) / self.focal)[..., None]
                  + self.u[None, None, :] * ((H / 2 - ys - 0.5) / self.focal)[..., None])

    def project(self, p):
        c = np.asarray(p, float) - self.eye
        z = c @ self.f
        return np.array([W / 2 + (c @ self.r) / z * self.focal, H / 2 - (c @ self.u) / z * self.focal]), z


class Canvas:
    def __init__(self, cam):
        self.cam = cam
        self.img = np.zeros((H, W, 3))
        self.depth = np.full((H, W), np.inf)
        self.glow = np.zeros((H, W, 3))

    def background(self, ground_y):
        D = self.cam.D
        sky = np.clip(D[..., 1] * 1.4 + 0.25, 0, 1)[..., None]
        self.img[:] = (1 - sky) * np.array([0.33, 0.13, 0.14]) + sky * np.array([0.08, 0.06, 0.11])
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = (ground_y - self.cam.eye[1]) / D[..., 1]
        hit = (lam > 0) & np.isfinite(lam)
        P = self.cam.eye + D * lam[..., None]
        chk = ((np.floor(P[..., 0]) + np.floor(P[..., 2])) % 2 == 0)
        base = np.where(chk[..., None], np.array([0.22, 0.26, 0.2]), np.array([0.19, 0.23, 0.17]))
        fade = np.clip(1 - lam / 40, 0.15, 1)[..., None]
        col = base * fade + np.array([0.12, 0.07, 0.08]) * (1 - fade)
        self.img[hit] = col[hit]
        self.depth[hit] = lam[hit]

    def _solve(self, p0, e1, e2):
        n = np.cross(e1, e2)
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = ((p0 - self.cam.eye) @ n) / (self.cam.D @ n)
        hit = self.cam.eye + self.cam.D * lam[..., None] - p0
        a11, a12, a22 = e1 @ e1, e1 @ e2, e2 @ e2
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            return None
        b1, b2 = hit @ e1, hit @ e2
        s = (b1 * a22 - b2 * a12) / det
        t = (b2 * a11 - b1 * a12) / det
        ok = (lam > 0.05) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
        return lam, s, t, ok, n

    def bbox(self, corners):
        pts = []
        for c in corners:
            sp, z = self.cam.project(c)
            if z <= 0.05:
                return 0, 0, W, H
            pts.append(sp)
        pts = np.array(pts)
        x0, y0 = np.floor(pts.min(0)).astype(int) - 1
        x1, y1 = np.ceil(pts.max(0)).astype(int) + 1
        return max(0, x0), max(0, y0), min(W, x1), min(H, y1)

    def opaque_quad(self, p0, e1, e2, tex, uv, uvs, alpha_mul=1.0):
        x0, y0, x1, y1 = self.bbox([p0, p0 + e1, p0 + e2, p0 + e1 + e2])
        if x1 <= x0 or y1 <= y0:
            return
        sub = Canvas.__new__(Canvas)
        D = self.cam.D[y0:y1, x0:x1]
        n = np.cross(e1, e2)
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = ((p0 - self.cam.eye) @ n) / (D @ n)
        hit = self.cam.eye + D * lam[..., None] - p0
        a11, a12, a22 = e1 @ e1, e1 @ e2, e2 @ e2
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            return
        b1, b2 = hit @ e1, hit @ e2
        s = (b1 * a22 - b2 * a12) / det
        t = (b2 * a11 - b1 * a12) / det
        dep = self.depth[y0:y1, x0:x1]
        ok = (lam > 0.05) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1) & (lam < dep)
        if not ok.any():
            return
        TH, TW = tex.shape[:2]
        uu = np.clip(np.floor(uv[0] + s * uvs[0]), 0, TW - 1).astype(int)
        vv = np.clip(np.floor(uv[1] + t * uvs[1]), 0, TH - 1).astype(int)
        tx = tex[vv, uu]
        ok &= tx[..., 3] > 0
        nn = n / (np.linalg.norm(n) + 1e-9)
        shade = 0.55 + 0.45 * abs(nn @ np.array([0.35, 0.85, -0.4]) / np.linalg.norm([0.35, 0.85, -0.4]))
        em = tx[..., 3] < 0.5
        col = np.where(em[..., None], tx[..., :3], tx[..., :3] * shade)
        region = self.img[y0:y1, x0:x1]
        if alpha_mul < 1.0:
            a = alpha_mul * np.where(em, 1.0, tx[..., 3])[..., None]
            region[ok] = (region * (1 - a) + col * a)[ok]
        else:
            region[ok] = col[ok]
            dep[ok] = lam[ok]
        g = self.glow[y0:y1, x0:x1]
        g[ok & em] = np.maximum(g[ok & em], tx[..., :3][ok & em] * 0.8)

    def particle_quad(self, center, ax, ay, cell, frame, color, alpha):
        """Alpha-blended textured billboard. ax/ay: half-extent vectors."""
        p0 = center - ax - ay
        e1, e2 = 2 * ax, 2 * ay
        x0, y0, x1, y1 = self.bbox([p0, p0 + e1, p0 + e2, p0 + e1 + e2])
        if x1 <= x0 or y1 <= y0 or alpha <= 0.003:
            return
        D = self.cam.D[y0:y1, x0:x1]
        n = np.cross(e1, e2)
        if np.linalg.norm(n) < 1e-9:
            return
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = ((p0 - self.cam.eye) @ n) / (D @ n)
        hit = self.cam.eye + D * lam[..., None] - p0
        a11, a12, a22 = e1 @ e1, e1 @ e2, e2 @ e2
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            return
        b1, b2 = hit @ e1, hit @ e2
        s = (b1 * a22 - b2 * a12) / det
        t = (b2 * a11 - b1 * a12) / det
        dep = self.depth[y0:y1, x0:x1]
        ok = (lam > 0.05) & (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1) & (lam < dep)
        if not ok.any():
            return
        u0 = (cell[0] + frame) * 64
        v0 = cell[1] * 64
        uu = np.clip(np.floor(u0 + s * 64), 0, 255).astype(int)
        vv = np.clip(np.floor(v0 + (1 - t) * 64), 0, 255).astype(int)
        a = ATLAS[vv, uu, 3] * alpha
        a = np.where(ok, a, 0)[..., None]
        region = self.img[y0:y1, x0:x1]
        col = np.array(color[:3])
        region[:] = region * (1 - a) + col * a
        bright = max(color[:3])
        if bright > 0.5:
            g = self.glow[y0:y1, x0:x1]
            g[:] = np.maximum(g, col * a * 0.9)

    def finish(self):
        from PIL import ImageFilter

        g = Image.fromarray((np.clip(self.glow, 0, 1) * 255).astype(np.uint8))
        bloom = sum(np.asarray(g.filter(ImageFilter.GaussianBlur(r)), float) / 255 * w for r, w in ((4, 0.6), (14, 0.5)))
        out = 1 - (1 - np.clip(self.img, 0, 1)) * (1 - np.clip(bloom, 0, 1))
        return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


# ----------------------------------------------------------------------------- models

def world_from_model(loc, yaw, scale=1 / 16):
    th = math.radians(180 - yaw)
    c, s = math.cos(th), math.sin(th)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    L = np.array(loc, float)
    return lambda p: L + R @ (np.asarray(p, float) * scale)


def model_quads(geo, pose, to_world, root_fn=None):
    bones = {b["name"]: b for b in geo["bones"]}
    cache = {}

    def chain(name):
        if name in cache:
            return cache[name]
        b = bones[name]
        p = pose.get(name, {})
        rot = np.array(b.get("rotation", [0, 0, 0]), float) + np.array(p.get("rotation", [0, 0, 0]), float)
        sc = p.get("scale", 1.0)
        f = xform(b.get("pivot", [0, 0, 0]), tuple(rot), p.get("position", [0, 0, 0]), sc if not isinstance(sc, list) else sc)
        par = chain(b["parent"]) if b.get("parent") else (root_fn or (lambda v: v))
        g = lambda v, f=f, par=par: par(f(v))
        cache[name] = g
        return g

    out = []
    for b in geo["bones"]:
        fn = chain(b["name"])
        for c in b.get("cubes", []):
            inf = c.get("inflate", 0)
            o = np.array(c["origin"], float) - inf
            s = np.array(c["size"], float) + 2 * inf
            for face, f in c.get("uv", {}).items():
                sel, ua, va, _ = FACES[face]
                tl = np.where(np.array(sel) == 1, o + s, o)
                q0 = to_world(fn(I(tl)))
                q1 = to_world(fn(I(tl + np.array(ua, float) * s)))
                q2 = to_world(fn(I(tl + np.array(va, float) * s)))
                out.append((q0, q1 - q0, q2 - q0, f["uv"], f["uv_size"]))
    return out


SKIN = np.zeros((4, 4, 4))
SKIN[..., :3] = [0.42, 0.3, 0.26]
SKIN[..., 3] = 1
CLOTH = np.zeros((4, 4, 4))
CLOTH[..., :3] = [0.16, 0.13, 0.15]
CLOTH[..., 3] = 1


def player_quads(loc, yaw, ppose, awake):
    to_world = world_from_model(loc, yaw)
    base = {"rightArm": [-18, 0, 0]}
    def bone(name, pivot, origin, size, tex):
        rot = np.array(base.get(name, [0, 0, 0]), float) + np.array(ppose.get(name, {}).get("rotation", [0, 0, 0]), float)
        f = xform(pivot, tuple(rot))
        q = []
        o = np.array(origin, float)
        s = np.array(size, float)
        for face, (sel, ua, va, _) in FACES.items():
            tl = np.where(np.array(sel) == 1, o + s, o)
            q0 = to_world(f(I(tl)))
            q.append((q0, to_world(f(I(tl + np.array(ua, float) * s))) - q0, to_world(f(I(tl + np.array(va, float) * s))) - q0, [0, 0], [4, 4], tex))
        return q, f
    quads = []
    for name, piv, o, s, tx in (("head", (0, 24, 0), (-4, 24, -4), (8, 8, 8), SKIN), ("body", (0, 24, 0), (-4, 12, -2), (8, 12, 4), CLOTH),
                                ("leftArm", (5, 22, 0), (4, 12, -2), (4, 12, 4), CLOTH), ("rightLeg", (-1.9, 12, 0), (-3.9, 0, -2), (4, 12, 4), CLOTH),
                                ("leftLeg", (1.9, 12, 0), (-0.1, 0, -2), (4, 12, 4), CLOTH)):
        quads += bone(name, piv, o, s, tx)[0]
    arm_q, arm_f = bone("rightArm", (-5, 22, 0), (-8, 12, -2), (4, 12, 4), CLOTH)
    quads += arm_q
    bind = I((-6, 15, 1)) - np.array([0, 24, 0], float)
    root_fn = lambda v: arm_f(v + bind)
    hold = {"grizzlys_oath": {"rotation": HOLD["rotation"], "position": HOLD["position"], "scale": HOLD["scale"]}}
    for q in model_quads(AXE_GEO, hold, to_world, root_fn):
        quads.append(q + (TEX["axe_awake" if awake else "axe"],))
    return quads


def fp_axe_quads(loc, ppose, awake):
    """First-person axe: vanilla first_person.empty_hand arm pose + our additive arm animation."""
    to_world = lambda v: np.asarray(loc, float) + np.asarray(v, float) / 16.0
    extra = np.array(ppose.get("rightArm", {}).get("rotation", [0, 0, 0]), float)
    arm_f = xform((-5, 22, 0), tuple(np.array([95, -45, 115], float) + extra), (13.5, -10, 12))
    item_f = xform((-6, 15, 1), (0, 0, 0), (0, 0, -1))
    bind = I((-6, 15, 1)) - np.array([0, 24, 0], float)
    root_fn = lambda v: arm_f(item_f(v + bind))
    hold = {"grizzlys_oath": {"rotation": HOLD_FP["rotation"], "position": HOLD_FP["position"], "scale": HOLD_FP["scale"]}}
    return [q + (TEX["axe_awake" if awake else "axe"],) for q in model_quads(AXE_GEO, hold, to_world, root_fn)]


# ----------------------------------------------------------------------------- particles

GRAV = {"sparks": -7, "blood": -12, "shard": -22, "ember": 0.6, "smoke": 0.8, "dust": 0.6, "flame": 1.4, "glow": 0}
DRAG = {"sparks": 5, "smoke": 1.5, "dust": 3.5, "ember": 0.8, "flame": 1.2, "shard": 0.5}
CELLS = {"glow": (0, 0), "star": (1, 0), "sparks": (2, 0), "shard": (3, 0), "slash": (0, 1), "claw_flash": (0, 2), "crack": (1, 2),
         "ring": (2, 2), "smoke": (3, 2), "dust": (3, 2), "flame": (0, 3), "streak": (2, 0), "ember": (0, 0), "blood": (0, 0)}


def col(vars_, default=(1, 0.15, 0.1, 1)):
    c = vars_.get("variable.color")
    return (c["red"], c["green"], c["blue"], c["alpha"]) if c else default


def spawn(ev, rnd):
    """Expand one emitter event into particle dicts with initial state."""
    i, v, at = ev["id"], ev["vars"], np.array([ev["loc"]["x"], ev["loc"]["y"], ev["loc"]["z"]], float)
    t0 = ev["t"] / 20.0
    P = []

    def mk(**k):
        d = dict(id=i, t0=t0, pos=at.copy(), vel=np.zeros(3), vars=v, rot=0.0, life=0.3)
        d.update(k)
        P.append(d)

    def rand_dir(up_bias=0.0):
        d = np.array([rnd.uniform(-1, 1), rnd.uniform(-1, 1) + up_bias, rnd.uniform(-1, 1)])
        return d / (np.linalg.norm(d) + 1e-9)

    if i == "sparks":
        for _ in range(int(v.get("variable.count", 8))):
            mk(vel=rand_dir() * rnd.uniform(4, 9) * v.get("variable.speed", 1), life=rnd.uniform(0.18, 0.34))
    elif i == "shard":
        for _ in range(int(v.get("variable.count", 8))):
            d = np.array([rnd.uniform(-1, 1), rnd.uniform(0.8, 1.6), rnd.uniform(-1, 1)])
            mk(vel=d / np.linalg.norm(d) * rnd.uniform(4, 8), life=rnd.uniform(0.6, 0.9), rot=rnd.uniform(0, 360))
    elif i == "blood":
        for _ in range(2):
            mk(vel=rand_dir() * rnd.uniform(0.5, 1.5), life=0.6)
    elif i == "ember":
        d = np.array([rnd.uniform(-0.3, 0.3), 1, rnd.uniform(-0.3, 0.3)])
        mk(vel=d / np.linalg.norm(d) * rnd.uniform(0.6, 1.4), life=rnd.uniform(0.6, 1.0))
    elif i == "smoke":
        mk(vel=rand_dir() * rnd.uniform(0.2, 0.6), life=rnd.uniform(0.7, 1.1), rot=rnd.uniform(0, 360))
    elif i == "dust":
        d = np.array([v["variable.dir"][k] for k in "xyz"]) if "variable.dir" in v else np.array([0, 0, 1.0])
        mk(vel=d / (np.linalg.norm(d) + 1e-9) * v.get("variable.speed", 3), life=rnd.uniform(0.6, 0.9), rot=rnd.uniform(0, 360))
    elif i == "flame":
        mk(vel=np.array([0, rnd.uniform(0.5, 1.1), 0]), life=rnd.uniform(0.45, 0.75))
    elif i == "crack":
        mk(life=v.get("variable.life", 1.2), rot=rnd.uniform(0, 360))
    elif i in ("glow", "star", "slash", "claw_flash", "streak", "ring"):
        default_life = {"glow": 0.3, "star": 0.16, "slash": 0.2, "claw_flash": 0.28, "streak": 0.3, "ring": 0.45}[i]
        mk(life=v.get("variable.life", default_life), rot=v.get("variable.rot", 0))
    return P


def step(p, age, dt=1 / 60):
    """Advance motion to `age` seconds (cached incremental integration)."""
    while p.get("_age", 0.0) + 1e-9 < age:
        h = min(dt, age - p.get("_age", 0.0))
        acc = np.array([0, GRAV.get(p["id"], 0) + (p["vars"].get("variable.rise", 0) if p["id"] == "glow" else 0), 0]) - DRAG.get(p["id"], 0) * p["vel"]
        p["vel"] = p["vel"] + acc * h
        p["pos"] = p["pos"] + p["vel"] * h
        p["_age"] = p.get("_age", 0.0) + h


def draw_particle(cv, p, now):
    age = now - p["t0"]
    if age < 0 or age > p["life"]:
        return
    step(p, age)
    T = age / p["life"]
    v = p["vars"]
    i = p["id"]
    cam = cv.cam
    c = col(v)
    frame = 0
    pos = p["pos"]

    def facing(rot=0.0):
        a = math.radians(rot)
        return cam.r * math.cos(a) + cam.u * math.sin(a), -cam.r * math.sin(a) + cam.u * math.cos(a)

    if i == "glow":
        s = v.get("variable.size", 0.2) * (1 - 0.5 * T)
        ax, ay = facing()
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], 0, c, c[3] * (1 - T))
    elif i == "star":
        s = v.get("variable.size", 0.5) * ((0.4 + 3 * T) if T < 0.2 else (1.15 - 0.95 * (T - 0.2)))
        ax, ay = facing(p["rot"])
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], 0, c, c[3] * (1 - T * T))
    elif i == "slash":
        s = v.get("variable.size", 1) * (0.92 + 0.16 * T)
        ax, ay = facing(p["rot"])
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], min(3, int(T * 4)), c, c[3] * (1 - T ** 3))
    elif i == "claw_flash":
        s = v.get("variable.size", 1) * ((0.6 + T * 2.7) if T < 0.15 else 1)
        ax, ay = facing(p["rot"])
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], 0, c, c[3] * (1 - T * T))
    elif i in ("streak", "sparks"):
        if i == "streak":
            d = np.array([v["variable.dir"][k] for k in "xyz"])
            sx, sy = v.get("variable.len", 1) * (1 - 0.4 * T), v.get("variable.wid", 0.1) * (1 - T)
            cc, a = c, c[3] * (1 - T)
        else:
            d = p["vel"]
            sx, sy = 0.26 * (1 - T) + 0.05, 0.035 * (1 - 0.5 * T)
            cc, a = (1, 0.92 - 0.8 * T, 0.65 - 0.6 * T), 1 - T * T
        d = d / (np.linalg.norm(d) + 1e-9)
        to_cam = cam.eye - pos
        yax = np.cross(d, to_cam)
        if np.linalg.norm(yax) < 1e-6:
            return
        yax /= np.linalg.norm(yax)
        cv.particle_quad(pos, d * sx, yax * sy, CELLS[i], 0, cc, a)
    elif i in ("ring", "crack"):
        if i == "ring":
            s = v.get("variable.radius", 4) * (1 - (1 - min(1, T * 1.25)) ** 3) + 0.3
            a = c[3] * (1 - T)
        else:
            s = v.get("variable.radius", 2) * min(1, age * 14)
            a = c[3] * (1 - T * T)
        ang = math.radians(p["rot"])
        ax = np.array([math.cos(ang), 0, math.sin(ang)]) * s
        ay = np.array([-math.sin(ang), 0, math.cos(ang)]) * s
        cv.particle_quad(pos, ax, ay, CELLS[i], 0, c, a)
    elif i in ("smoke", "dust"):
        s = v.get("variable.size", 0.5) * ((0.6 + 0.6 * T) if i == "smoke" else (0.5 + 0.9 * T))
        cc = c if i == "smoke" else (0.45, 0.39, 0.36, 1)
        a = (c[3] if i == "smoke" else 0.65) * (1 - T)
        ax, ay = facing(p["rot"])
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], 0, cc, a)
    elif i == "ember":
        s = 0.06 * (1 - T) + 0.02
        ax, ay = facing()
        cv.particle_quad(pos, ax * s, ay * s, CELLS[i], 0, (1, 0.4 - 0.3 * T, 0.15), 1 - T * T)
    elif i == "flame":
        sz = v.get("variable.size", 0.4)
        sx, sy = sz * (1 - 0.35 * T), sz * 1.4 * (1 - 0.2 * T)
        to_cam = cam.eye - pos
        to_cam[1] = 0
        n = np.linalg.norm(to_cam)
        if n < 1e-6:
            return
        rax = np.cross([0, 1, 0], to_cam / n)
        cv.particle_quad(pos, rax * sx, np.array([0, 1.0, 0]) * sy, CELLS[i], min(3, int(T * 4)), c, c[3] * (1 - T))
    elif i == "blood":
        ax, ay = facing()
        cv.particle_quad(pos, ax * 0.05, ay * 0.07, CELLS[i], 0, (0.6, 0.02, 0.03), 1)
    elif i == "shard":
        ax, ay = facing(p["rot"] + age * 300)
        cv.particle_quad(pos, ax * 0.11, ay * 0.11, CELLS[i], 0, (0.3, 0.05, 0.05), 1 - T * T)


# ----------------------------------------------------------------------------- scenes

def render_frame(scene, tick, cam_spec, particles, label):
    trk = {s["t"]: s for s in scene["track"]}
    pl = trk.get(tick, scene["track"][-1])
    ploc = np.array([pl["x"], pl["y"], pl["z"]])
    fp = cam_spec is first_person
    eye, target = cam_spec(ploc)
    cv = Canvas(Cam(eye, target))
    cv.background(64.0)
    now = tick / 20.0
    # player pose from the newest animation that is still playing
    ppose = {}
    for a in scene["anims"]:
        anim = PANIMS.get(a["name"])
        if anim and a["t"] <= tick <= a["t"] + anim["animation_length"] * 20 + 2:
            ppose = anim_sample.pose(anim, (tick - a["t"]) / 20.0, fp=fp)
    awake = scene["name"].startswith("Oath") and tick < 72
    for q0, e1, e2, uv, uvs, tex in (fp_axe_quads(ploc, ppose, awake) if fp else player_quads(ploc, 0, ppose, awake)):
        cv.opaque_quad(q0, e1, e2, tex, uv, uvs)
    for m in scene["mobs"]:
        to_w = world_from_model([m["x"], 64, m["z"]], 180)
        for name, piv, o, s in (("b", (0, 24, 0), (-4, 12, -2), (8, 12, 4)), ("h", (0, 24, 0), (-4, 24, -4), (8, 8, 8)), ("l", (0, 12, 0), (-4, 0, -2), (8, 12, 4))):
            ztex = np.zeros((4, 4, 4))
            ztex[..., :3] = [0.2, 0.42, 0.24] if name != "l" else [0.2, 0.22, 0.45]
            ztex[..., 3] = 1
            for face, (sel, ua, va, _) in FACES.items():
                tl = np.where(np.array(sel) == 1, np.array(o) + np.array(s), np.array(o, float))
                q0 = to_w(I(tl))
                cv.opaque_quad(q0, to_w(I(tl + np.array(ua) * np.array(s))) - q0, to_w(I(tl + np.array(va) * np.array(s))) - q0, ztex, [0, 0], [4, 4])
    for sp in scene["spawned"]:
        age = (tick - sp["t"]) / 20.0
        if sp["id"] == "grizzly_oath:oath_grizzly" and 0 <= age <= 3.2:
            pose = anim_sample.pose(BEAR_ANIM, age)
            for q in model_quads(BEAR_GEO, pose, world_from_model([sp["loc"]["x"], sp["loc"]["y"], sp["loc"]["z"]], sp["yaw"], 2.6 / 16)):
                cv.opaque_quad(*q, tex=TEX["bear"]) if False else cv.opaque_quad(q[0], q[1], q[2], TEX["bear"], q[3], q[4])
        if sp["id"] == "grizzly_oath:grizzly_shade" and 0 <= age <= 3.0:
            pose = anim_sample.pose(SHADE_ANIM, age)
            for q in model_quads(BEAR_GEO, pose, world_from_model([sp["loc"]["x"], sp["loc"]["y"], sp["loc"]["z"]], sp["yaw"], 1.6 / 16)):
                cv.opaque_quad(q[0], q[1], q[2], TEX["shade"], q[3], q[4], alpha_mul=0.7)
    live = [p for p in particles if p["t0"] <= now <= p["t0"] + p["life"]]
    for p in live:
        step(p, now - p["t0"])
    live.sort(key=lambda p: -np.linalg.norm(p["pos"] - cv.cam.eye))
    for p in live:
        draw_particle(cv, p, now)
    img = cv.finish()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 26], fill=(10, 4, 6))
    d.text((10, 7), label, fill=(255, 210, 195))
    return img


def first_person(ploc):
    eye = ploc + np.array([0, 1.62, 0])
    return eye, eye + np.array([0, -0.08, 1.0])


def ult_cam(ploc):
    return ploc + np.array([-12.5, 5.0, 2.5]), ploc + np.array([0, 2.6, -1.8])


def behind_right(ploc):
    return ploc + np.array([-3.2, 2.6, -4.6]), ploc + np.array([0, 1.0, 3.5])


def wide(ploc):
    return ploc + np.array([-8.5, 5.5, -6.0]), ploc + np.array([0, 1.2, 2.5])


def side(ploc):
    return ploc + np.array([-5.5, 1.8, 1.0]), ploc + np.array([0, 1.1, 1.2])


SHOTS = {
    "Frontier Cleave": [(1, side, "swing (forehand)"), (2, side, "impact"), (4, side, "follow-through")],
    "Grizzly Rend": [(1, behind_right, "cast"), (3, behind_right, "claws racing"), (6, behind_right, "12 blocks"), (14, behind_right, "scars fade")],
    "Relentless Pursuit": [(2, side, "dash"), (4, side, "dash end"), (8, side, "slam"), (12, side, "shockwave")],
    "Unbroken Will": [(3, behind_right, "roar"), (14, behind_right, "grizzly shade"), (40, behind_right, "aura (buff 8 s)")],
    "Oath of the Grizzly": [(8, ult_cam, "grizzly rises"), (24, ult_cam, "roar"), (35, ult_cam, "wind-up"), (40, ult_cam, "SLAM"), (46, ult_cam, "shockwave 8 blocks")],
}

FP_SHOTS = {
    "Frontier Cleave": [(0, "idle"), (1, "swing"), (2, "impact"), (4, "follow-through")],
    "Grizzly Rend": [(1, "cast"), (3, "claws racing"), (6, "claws far")],
    "Relentless Pursuit": [(2, "dash"), (8, "slam"), (11, "shockwave")],
    "Unbroken Will": [(4, "roar"), (30, "aura")],
    "Oath of the Grizzly": [(10, "charge"), (40, "SLAM"), (45, "shockwave")],
}


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    scenes = json.load(open(os.path.join(HERE, ".scenes.json")))
    for sc in scenes:
        rnd = random.Random(7)
        shots = SHOTS[sc["name"]]
        tiles = []
        for tick, cam, txt in shots:
            parts = [q for e in sc["particles"] for q in spawn(e, rnd)]
            tiles.append(render_frame(sc, tick, cam, parts, f"{sc['name']}  -  {txt}  ({tick / 20:.2f} s)"))
        cols = 2 if len(tiles) > 3 else len(tiles)
        rows = math.ceil(len(tiles) / cols)
        sheet = Image.new("RGB", (W * cols, H * rows), (0, 0, 0))
        for k, t in enumerate(tiles):
            sheet.paste(t, ((k % cols) * W, (k // cols) * H))
        name = sc["name"].lower().replace(" ", "_").replace("'", "")
        sheet.save(os.path.join(out_dir, f"fx_{name}.png"))
        fp_tiles = []
        for tick, txt in FP_SHOTS[sc["name"]]:
            parts = [q for e in sc["particles"] for q in spawn(e, random.Random(7))]
            fp_tiles.append(render_frame(sc, tick, first_person, parts, f"FIRST PERSON  {sc['name']}  -  {txt}  ({tick / 20:.2f} s)"))
        fp_tiles = [t.resize((W // 2, H // 2), Image.LANCZOS) for t in fp_tiles]
        cols = 2
        rows = math.ceil(len(fp_tiles) / cols)
        fsheet = Image.new("RGB", (W // 2 * cols, H // 2 * rows), (0, 0, 0))
        for k, t in enumerate(fp_tiles):
            fsheet.paste(t, ((k % cols) * (W // 2), (k // cols) * (H // 2)))
        fsheet.save(os.path.join(out_dir, f"fp_{name}.png"))
        print("rendered", name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "preview"))
