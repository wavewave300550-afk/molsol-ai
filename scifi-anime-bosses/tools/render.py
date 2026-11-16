"""
render.py - software preview renderer for geo.Model.

Z-buffered triangle rasteriser in numpy with perspective-correct UVs, nearest texel
sampling (like the game), Lambert lighting, emissive-from-alpha (entity_emissive) and an
additive glow pass (entity_beam_additive).  The model->world transform follows Bedrock:
model space is mirrored on Z relative to the world for an entity with yaw 0 (which faces
+Z / south), and yaw turns the entity clockwise seen from above.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

import geo

FACE_AXES = {
    # face: (normal, u axis, v axis) in model space; v axis points "down" the texture
    "north": ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
    "south": ((0, 0, 1), (-1, 0, 0), (0, -1, 0)),
    "east": ((-1, 0, 0), (0, 0, -1), (0, -1, 0)),   # Bedrock "east" = model -X side
    "west": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "up": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "down": ((0, -1, 0), (-1, 0, 0), (0, 0, -1)),
}


def _face_quad(c: geo.Cube, face: str):
    """Corners (tl, tr, br, bl) of a face in (unrotated) model space."""
    i = c.inflate
    x0, y0, z0 = c.origin[0] - i, c.origin[1] - i, c.origin[2] - i
    x1, y1, z1 = c.origin[0] + c.size[0] + i, c.origin[1] + c.size[1] + i, c.origin[2] + c.size[2] + i
    n, ua, va = FACE_AXES[face]
    center = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    half = ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
    fc = tuple(center[k] + n[k] * half[k] for k in range(3))
    hu = sum(abs(ua[k]) * half[k] for k in range(3))
    hv = sum(abs(va[k]) * half[k] for k in range(3))
    def pt(su, sv):
        return tuple(fc[k] + ua[k] * hu * su + va[k] * hv * sv for k in range(3))
    return pt(-1, -1), pt(1, -1), pt(1, 1), pt(-1, 1)


class Scene:
    def __init__(self, width=960, height=600, bg_top=(10, 12, 26), bg_bottom=(46, 38, 70)):
        self.W, self.H = width, height
        self.color = np.zeros((height, width, 3), np.float32)
        t = np.linspace(0, 1, height, dtype=np.float32)[:, None]
        top = np.array(bg_top, np.float32) / 255
        bot = np.array(bg_bottom, np.float32) / 255
        self.color[:] = (top * (1 - t) + bot * t)[:, None, :].reshape(height, 1, 3)
        self.depth = np.full((height, width), np.inf, np.float32)
        self.glow = np.zeros((height, width, 3), np.float32)
        self.light_dir = np.array(geo.v_norm((-0.45, 0.8, 0.35)), np.float32)
        self.ambient = 0.42
        self.set_camera((30, 14, -30), (0, 4, 0), 38)

    def set_camera(self, eye, target, fov=38, up=(0, 1, 0)):
        self.eye = np.array(eye, np.float32)
        f = np.array(target, np.float32) - self.eye
        f /= np.linalg.norm(f)
        r = np.cross(f, np.array(up, np.float32))
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        self.cam = (r, u, f)
        self.focal = (self.H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P: np.ndarray):
        r, u, f = self.cam
        d = P - self.eye
        x = d @ r
        y = d @ u
        z = d @ f
        z = np.maximum(z, 1e-3)
        sx = self.W / 2 + x / z * self.focal
        sy = self.H / 2 - y / z * self.focal
        return sx, sy, z

    # ------------------------------------------------------------------ geometry -> triangles
    def add_model(self, model: geo.Model, textures: Dict[str, np.ndarray], pose: Optional[dict] = None,
                  position=(0, 0, 0), yaw=0.0, scale=1.0, hidden: Iterable[str] = (),
                  glow_tint=(1.0, 1.0, 1.0, 1.0), layers=("main", "glow")):
        mats = model.bone_world_matrices(pose or {})
        hidden = set(hidden)
        cy, sy = math.cos(math.radians(-yaw)), math.sin(math.radians(-yaw))
        pos = np.array(position, np.float32)

        def to_world(p):
            x, y, z = p[0] / 16 * scale, p[1] / 16 * scale, -p[2] / 16 * scale
            return np.array((x * cy + z * sy, y, -x * sy + z * cy), np.float32) + pos

        for layer in layers:
            tex = textures.get(layer)
            if tex is None:
                continue
            for b in model.bones:
                if b.name in hidden:
                    continue
                R, t = mats[b.name]
                for ci, c in enumerate(b.cubes):
                    if c.layer != layer:
                        continue
                    cm = geo.bedrock_matrix(c.rotation)
                    cp = c.pivot or c.origin
                    for face in geo.FACES:
                        key = (b.name, ci, face)
                        if key not in model.uv:
                            continue
                        quad = _face_quad(c, face)
                        wq = []
                        for p in quad:
                            q = geo.v_add(geo.m_apply(cm, geo.v_sub(p, cp)), cp)
                            q = geo.v_add(geo.m_apply(R, q), t)
                            wq.append(to_world(q))
                        u, v, w, h = model.uv[key]
                        uvq = [(u, v), (u + w, v), (u + w, v + h), (u, v + h)]
                        self._draw_quad(np.array(wq), uvq, tex, layer, glow_tint)

    def _draw_quad(self, P, uvq, tex, layer, tint):
        n = np.cross(P[1] - P[0], P[3] - P[0])
        nl = np.linalg.norm(n)
        if nl < 1e-9:
            return
        n /= nl
        # outward normal: our corner order (tl,tr,br,bl) seen from outside is clockwise in a
        # left-handed sense after the Z mirror, so flip to point outward
        n = -n
        center = P.mean(axis=0)
        if np.dot(n, self.eye - center) <= 0:
            return  # back face
        shade = self.ambient + (1 - self.ambient) * max(0.0, float(np.dot(n, self.light_dir)))
        for tri in ((0, 1, 2), (0, 2, 3)):
            self._raster(P[list(tri)], [uvq[i] for i in tri], tex, layer, shade, tint)

    def _raster(self, P, uvs, tex, layer, shade, tint):
        r, u, f = self.cam
        if ((P - self.eye) @ f).min() < 0.08:
            return  # near-plane rejection (no clipping needed at preview quality)
        sx, sy, z = self.project(P)
        minx = max(int(math.floor(sx.min())), 0)
        maxx = min(int(math.ceil(sx.max())), self.W - 1)
        miny = max(int(math.floor(sy.min())), 0)
        maxy = min(int(math.ceil(sy.max())), self.H - 1)
        if minx > maxx or miny > maxy:
            return
        xs = np.arange(minx, maxx + 1, dtype=np.float32) + 0.5
        ys = np.arange(miny, maxy + 1, dtype=np.float32) + 0.5
        X, Y = np.meshgrid(xs, ys)
        x0, x1, x2 = sx
        y0, y1, y2 = sy
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            return
        w0 = ((x1 - X) * (y2 - Y) - (x2 - X) * (y1 - Y)) / area
        w1 = ((x2 - X) * (y0 - Y) - (x0 - X) * (y2 - Y)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not inside.any():
            return
        iz = w0 / z[0] + w1 / z[1] + w2 / z[2]
        depth = 1.0 / np.maximum(iz, 1e-6)
        uu = (w0 * uvs[0][0] / z[0] + w1 * uvs[1][0] / z[1] + w2 * uvs[2][0] / z[2]) * depth
        vv = (w0 * uvs[0][1] / z[0] + w1 * uvs[1][1] / z[1] + w2 * uvs[2][1] / z[2]) * depth
        th, tw = tex.shape[:2]
        ui = np.clip(np.floor(uu - 1e-4), 0, tw - 1).astype(int)
        vi = np.clip(np.floor(vv - 1e-4), 0, th - 1).astype(int)
        texel = tex[vi, ui]
        region = (slice(miny, maxy + 1), slice(minx, maxx + 1))
        if layer == "main":
            visible = inside & (texel[..., 3] > 0.004) & (depth < self.depth[region])
            emissive = np.clip((1.0 - texel[..., 3]) / 0.975, 0, 1)
            rgb = texel[..., :3] * (shade * (1 - emissive) + emissive)[..., None]
            cur = self.color[region]
            cur[visible] = rgb[visible]
            self.color[region] = cur
            dcur = self.depth[region]
            dcur[visible] = depth[visible]
            self.depth[region] = dcur
        else:
            visible = inside & (depth < self.depth[region])
            add = texel[..., :3] * texel[..., 3:4] * np.array(tint[:3], np.float32) * tint[3]
            g = self.glow[region]
            g[visible] += add[visible]
            self.glow[region] = g

    # ------------------------------------------------------------------ output
    def image(self, bloom=False) -> Image.Image:
        out = self.color + self.glow
        if bloom:
            g = self.glow.copy()
            for _ in range(3):
                g = (g + np.roll(g, 2, 0) + np.roll(g, -2, 0) + np.roll(g, 2, 1) + np.roll(g, -2, 1)) / 5
            out = out + g * 0.6
        out = np.clip(out, 0, 1)
        return Image.fromarray((out * 255).astype(np.uint8), "RGB")


def ground_plane(scene: Scene, y=0.0, size=40, color=(0.22, 0.30, 0.20), checker=4):
    """Rasterise a simple grass-like checker ground for context."""
    for gx in range(-size, size, checker):
        for gz in range(-size, size, checker):
            P = np.array([(gx, y, gz), (gx + checker, y, gz), (gx + checker, y, gz + checker), (gx, y, gz + checker)], np.float32)
            k = ((gx // checker) + (gz // checker)) % 2
            c = np.array(color, np.float32) * (0.92 if k else 1.0)
            tex = np.zeros((1, 1, 4), np.float32)
            tex[0, 0, :3] = c
            tex[0, 0, 3] = 1.0
            for tri in ((0, 2, 1), (0, 3, 2)):
                scene._raster(P[list(tri)], [(0, 0)] * 3, tex, "main", 0.9, (1, 1, 1, 1))
