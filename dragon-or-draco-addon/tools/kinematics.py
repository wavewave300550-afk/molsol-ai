"""
kinematics - forward kinematics, a tiny Molang evaluator, animation sampling and a
software rasteriser for previewing the add-on's real .geo.json / .animation.json files.

Rotation convention (derived from Blockbench's Bedrock codec, which negates X on import
and applies rotation [-rx, -ry, rz] in ZYX order in its right-handed space):

    in Bedrock model space   R(rx, ry, rz) = Rz(-rz) @ Ry(ry) @ Rx(-rx)

so  +rx pitches a -Z (forward) pointing part DOWN, +ry swings a +Z pointing part toward
+X, +rz tips a +X pointing part DOWN.  Animation rotation keys are added to the bone's
rest rotation; animation position keys are Bedrock-space unit offsets.

World placement used by the scripts (Minecraft yaw: 0 = facing +Z/south):
    world = entity_pos + Ryaw(yaw) @ (x/16, y/16, -z/16)
"""
from __future__ import annotations

import json
import math
import re
from typing import Dict, List, Optional

import numpy as np


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def brot(r):
    x, y, z = (math.radians(v) for v in r)
    return rz(-z) @ ry(y) @ rx(-x)


def affine(R=None, t=None):
    M = np.eye(4)
    if R is not None:
        M[:3, :3] = R
    if t is not None:
        M[:3, 3] = t
    return M


# --------------------------------------------------------------------------- molang

class Molang:
    """Evaluates the Molang subset the generated animations use."""

    FUNCS = {
        "math.sin": lambda d: math.sin(math.radians(d)),
        "math.cos": lambda d: math.cos(math.radians(d)),
        "math.abs": abs,
        "math.clamp": lambda v, a, b: max(a, min(b, v)),
        "math.min": min,
        "math.max": max,
        "math.lerp": lambda a, b, t: a + (b - a) * t,
        "math.pow": pow,
        "math.sqrt": math.sqrt,
        "math.floor": math.floor,
        "math.mod": lambda a, b: math.fmod(a, b),
        "math.pi": math.pi,
    }

    def __init__(self, env: Dict[str, float]):
        self.env = env
        self.cache = {}

    def eval(self, expr):
        if isinstance(expr, (int, float)):
            return float(expr)
        src = self.cache.get(expr)
        if src is None:
            s = expr.strip().rstrip(";")
            s = s.replace("query.", "q.").replace("variable.", "v.")
            s = re.sub(r"q\.property\('([^']+)'\)", lambda m: f"E.get('prop:{m.group(1)}', 0.0)", s)
            s = re.sub(r"\bmath\.pi\b", "PI", s)
            s = re.sub(r"\bmath\.(\w+)", lambda m: f"F['math.{m.group(1)}']", s)
            s = re.sub(r"\b([qv])\.(\w+)", lambda m: f"E.get('{m.group(1)}.{m.group(2)}', 0.0)", s)
            s = s.replace("&&", " and ").replace("||", " or ")
            s = re.sub(r"!(?!=)", " not ", s)
            # ternary a ? b : c  (single level)
            if "?" in s:
                c, rest = s.split("?", 1)
                a, b = rest.split(":", 1)
                s = f"(({a}) if ({c}) else ({b}))"
            src = compile(s, "<molang>", "eval")
            self.cache[expr] = src
        return float(eval(src, {"F": self.FUNCS, "E": self.env, "PI": math.pi}))


# --------------------------------------------------------------------------- animation sampling

def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def sample_channel(chan, t, mol: Molang):
    """chan is a Bedrock channel: list/number/str or {time: value | {post, lerp_mode}}."""
    if chan is None:
        return None
    if not isinstance(chan, dict):
        return _vec(chan, mol)
    keys = []
    for k, v in chan.items():
        mode = "linear"
        if isinstance(v, dict):
            mode = v.get("lerp_mode", "linear")
            v = v.get("post", v.get("pre"))
        keys.append((float(k), _vec(v, mol), mode))
    keys.sort(key=lambda x: x[0])
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(len(keys) - 1):
        t0, v0, m0 = keys[i]
        t1, v1, m1 = keys[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            if m0 == "catmullrom" or m1 == "catmullrom":
                vp = keys[i - 1][1] if i > 0 else v0
                vn = keys[i + 2][1] if i + 2 < len(keys) else v1
                return _catmull(vp, v0, v1, vn, f)
            return v0 + (v1 - v0) * f
    return keys[-1][1]


def _vec(v, mol):
    if isinstance(v, list):
        return np.array([mol.eval(x) for x in v], dtype=float)
    x = mol.eval(v)
    return np.array([x, x, x], dtype=float)


def sample_pose(animations: List[dict], weights: List[float], times: List[float], env: Dict[str, float]):
    """Sum several animations (Bedrock adds rotation/position, multiplies scale)."""
    pose = {}
    for anim, w, t in zip(animations, weights, times):
        if w == 0:
            continue
        e = dict(env)
        e["q.anim_time"] = t
        e["q.life_time"] = env.get("q.life_time", t)
        mol = Molang(e)
        if anim.get("loop") is True and anim.get("animation_length"):
            t = t % anim["animation_length"]
            mol.env["q.anim_time"] = t
        for bone, ch in anim.get("bones", {}).items():
            p = pose.setdefault(bone, {"rotation": np.zeros(3), "position": np.zeros(3), "scale": np.ones(3)})
            r = sample_channel(ch.get("rotation"), t, mol)
            if r is not None:
                p["rotation"] += r * w
            q = sample_channel(ch.get("position"), t, mol)
            if q is not None:
                p["position"] += q * w
            s = sample_channel(ch.get("scale"), t, mol)
            if s is not None:
                p["scale"] *= 1 + (s - 1) * w
    return pose


# --------------------------------------------------------------------------- forward kinematics

def bone_matrices(geo: dict, pose: Optional[dict] = None) -> Dict[str, np.ndarray]:
    pose = pose or {}
    by_name = {b["name"]: b for b in geo["bones"]}
    mats: Dict[str, np.ndarray] = {}

    def get(name):
        if name in mats:
            return mats[name]
        b = by_name[name]
        piv = np.array(b.get("pivot", [0, 0, 0]), dtype=float)
        rot = np.array(b.get("rotation", [0, 0, 0]), dtype=float)
        p = pose.get(name)
        pos = np.zeros(3)
        scl = np.ones(3)
        if p is not None:
            rot = rot + p["rotation"]
            pos = p["position"]
            scl = p["scale"]
        local = affine(t=piv + pos) @ affine(brot(rot)) @ affine(np.diag(scl)) @ affine(t=-piv)
        parent = b.get("parent")
        M = (get(parent) @ local) if parent else local
        mats[name] = M
        return M

    for n in by_name:
        get(n)
    return mats


def cube_corners(c: dict):
    o = np.array(c["origin"], dtype=float)
    s = np.array(c["size"], dtype=float)
    inf = c.get("inflate", 0.0)
    lo, hi = o - inf, o + s + inf
    return lo, hi


# face -> 4 corners (as lo/hi selectors) in texture order TL, TR, BR, BL (u right, v down)
def face_quads(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    return {
        "north": [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
        "south": [(x1, y1, z1), (x0, y1, z1), (x0, y0, z1), (x1, y0, z1)],
        "east": [(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)],
        "west": [(x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (x1, y0, z0)],
        "up": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        "down": [(x1, y0, z1), (x0, y0, z1), (x0, y0, z0), (x1, y0, z0)],
    }


FACE_NORMALS = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (-1, 0, 0), "west": (1, 0, 0),
                "up": (0, 1, 0), "down": (0, -1, 0)}


def world_faces(geo: dict, pose: Optional[dict] = None, hidden=()):
    """Yield (bone, face, corners[4,3] model space, normal[3], uv rect) for every face."""
    mats = bone_matrices(geo, pose)
    for b in geo["bones"]:
        if b["name"] in hidden:
            continue
        M = mats[b["name"]]
        for c in b.get("cubes", []):
            lo, hi = cube_corners(c)
            C = np.eye(4)
            if "rotation" in c:
                piv = np.array(c.get("pivot", (lo + hi) / 2), dtype=float)
                C = affine(t=piv) @ affine(brot(c["rotation"])) @ affine(t=-piv)
            T = M @ C
            for f, q in face_quads(lo, hi).items():
                if f not in c["uv"]:
                    continue
                P = np.array([list(p) + [1.0] for p in q]) @ T.T
                n = T[:3, :3] @ np.array(FACE_NORMALS[f], dtype=float)
                n = n / (np.linalg.norm(n) + 1e-9)
                yield b["name"], f, P[:, :3], n, c["uv"][f]


def locator_world(geo: dict, pose: Optional[dict], bone: str, name: str):
    mats = bone_matrices(geo, pose)
    for b in geo["bones"]:
        if b["name"] == bone:
            loc = b["locators"][name]
            off = loc["offset"] if isinstance(loc, dict) else loc
            return (mats[bone] @ np.array(list(off) + [1.0]))[:3]
    raise KeyError(bone)


# --------------------------------------------------------------------------- rasteriser

class Camera:
    """Orbit camera around a target. yaw 0 looks at the creature's face (from -Z),
    yaw 90 looks at its left flank (from +X)."""

    def __init__(self, target, yaw, pitch, dist=None, scale=2.0, size=(900, 600), fov=None):
        self.target = np.array(target, dtype=float)
        self.size = size
        self.scale = scale
        self.fov = fov
        self.dist = dist or 600
        y, p = math.radians(yaw), math.radians(pitch)
        # display space = Bedrock space with X negated (right handed, not mirrored on screen)
        fwd = np.array([math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p)])
        # camera sits at target - fwd*dist, looking along fwd; yaw 0 => fwd = +Z (sees north faces)
        self.fwd = fwd / np.linalg.norm(fwd)
        up = np.array([0.0, 1.0, 0.0])
        self.right = np.cross(self.fwd, up)
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.fwd)

    def project(self, P):
        D = P.copy()
        D[:, 0] = -D[:, 0]  # Bedrock -> display (right handed)
        T = self.target.copy()
        T[0] = -T[0]
        rel = D - T
        x = rel @ self.right
        y = rel @ self.up
        z = rel @ self.fwd + self.dist
        if self.fov:
            f = (self.size[1] / 2) / math.tan(math.radians(self.fov) / 2)
            sx = self.size[0] / 2 + x * f / np.maximum(z, 1)
            sy = self.size[1] / 2 - y * f / np.maximum(z, 1)
        else:
            sx = self.size[0] / 2 + x * self.scale
            sy = self.size[1] / 2 - y * self.scale
        return np.stack([sx, sy, z], axis=1)

    def view_normal(self, n):
        d = n.copy()
        d[0] = -d[0]
        return d


def render(faces, tex: np.ndarray, cam: Camera, bg=(0, 0, 0, 0), light=(0.45, 0.8, -0.35), emissive_alpha=128,
           additive_bones=(), image=None, zbuf=None, ambient=0.42):
    W, H = cam.size
    if image is None:
        image = np.zeros((H, W, 3), dtype=float)
        image[:] = np.array(bg[:3]) / 255.0
        cover = np.zeros((H, W), dtype=bool)
    else:
        cover = None
    if zbuf is None:
        zbuf = np.full((H, W), np.inf)
    glow = np.zeros((H, W, 3), dtype=float)
    L = np.array(light, dtype=float)
    L[0] = -L[0]
    L /= np.linalg.norm(L)
    th, tw = tex.shape[:2]
    texf = tex.astype(float) / 255.0
    for bone, f, P, n, (uvo, uvs) in ((b, f, P, n, (uv["uv"], uv["uv_size"])) for b, f, P, n, uv in faces):
        S = cam.project(P)
        nd = cam.view_normal(n)
        facing = nd @ cam.fwd
        additive = any(bone.startswith(a) for a in additive_bones)
        if facing > 0 and not additive:
            continue  # back face
        if abs(uvs[0]) < 1e-6 or abs(uvs[1]) < 1e-6:
            continue
        shade = ambient + (1 - ambient) * max(0.0, float(nd @ (-L) * -1) if False else max(0.0, float(nd @ L)))
        uv_corners = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
        for tri in ((0, 1, 2), (0, 2, 3)):
            _raster_tri(S[list(tri)], uv_corners[list(tri)], uvo, uvs, texf, tw, th, image, zbuf, glow, shade,
                        emissive_alpha, additive, cover)
    return image, zbuf, glow, cover


def _raster_tri(S, UV, uvo, uvs, texf, tw, th, image, zbuf, glow, shade, ea, additive, cover):
    H, W = zbuf.shape
    xs, ys = S[:, 0], S[:, 1]
    x0, x1 = int(max(0, math.floor(xs.min()))), int(min(W - 1, math.ceil(xs.max())))
    y0, y1 = int(max(0, math.floor(ys.min()))), int(min(H - 1, math.ceil(ys.max())))
    if x1 < x0 or y1 < y0:
        return
    (ax, ay), (bx, by), (cx, cy) = S[0, :2], S[1, :2], S[2, :2]
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-9:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
    w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
    w2 = 1 - w0 - w1
    inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not inside.any():
        return
    z = w0 * S[0, 2] + w1 * S[1, 2] + w2 * S[2, 2]
    u = w0 * UV[0, 0] + w1 * UV[1, 0] + w2 * UV[2, 0]
    v = w0 * UV[0, 1] + w1 * UV[1, 1] + w2 * UV[2, 1]
    tx = np.clip((uvo[0] + u * uvs[0]).astype(int), 0, tw - 1)
    ty = np.clip((uvo[1] + v * uvs[1]).astype(int), 0, th - 1)
    texel = texf[ty, tx]
    sub_z = zbuf[y0:y1 + 1, x0:x1 + 1]
    if additive:
        m = inside & (z < sub_z)
        img = glow[y0:y1 + 1, x0:x1 + 1]
        img[m] += texel[m, :3] * 0.55
        return
    alpha = texel[..., 3]
    opaque = alpha > 0.02
    m = inside & opaque & (z < sub_z)
    emiss = alpha < (ea / 255.0)
    col = texel[..., :3] * np.where(emiss[..., None], 1.0, shade)
    img = image[y0:y1 + 1, x0:x1 + 1]
    img[m] = col[m]
    sub_z[m] = z[m]
    g = glow[y0:y1 + 1, x0:x1 + 1]
    g[m & emiss] = texel[m & emiss, :3]
    if cover is not None:
        cover[y0:y1 + 1, x0:x1 + 1] |= m


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
