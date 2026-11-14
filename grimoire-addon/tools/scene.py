#!/usr/bin/env python3
"""Scene previewer: draws recorded spell casts with the real models, poses and placements.

The traces come from the headless mock server (node tests/run.mjs trace) and the actor meshes
from a build run with GRIMOIRE_SCENE=1.  Nothing here runs in the game; it exists so that the
layout of a whole spell (where things stand, which way they face, how big they are, when they
appear and vanish) can be looked at without launching Minecraft.

  python3 tools/scene.py dw01                      # contact sheet, automatic times
  python3 tools/scene.py dw01 --times 2,4.5 --view chase,top
  python3 tools/scene.py dw01 --report             # timing / placement table only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kit.geo import _trs  # noqa: E402

SCENE = os.path.join(HERE, "_scene")
TRACE = os.path.join(HERE, "..", "tests", ".out", "trace")
GROUND = 64.0
SIZES = np.array([1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768])
ZERO = ((0, 0, 0), (0, 0, 0), (1, 1, 1))
_defs = {}


def actor_def(ident):
    if ident not in _defs:
        p = os.path.join(SCENE, f"{ident}.pkl")
        if not os.path.exists(p):
            _defs[ident] = None
        else:
            with open(p, "rb") as fh:
                _defs[ident] = pickle.load(fh)
    return _defs[ident]


def merged_pose(d, state, t_state, t_life):
    pose = {}
    names = [(n, t_state) for n in d["states"].get(state, [])] + [(n, t_life) for n in d["always"]]
    for n, t in names:
        a = d["anims"].get(n)
        if a is None:
            continue
        for b, (r, p, s) in a.pose(max(0.0, t)).items():
            if b in pose:
                r0, p0, s0 = pose[b]
                pose[b] = (tuple(r0[i] + r[i] for i in range(3)), tuple(p0[i] + p[i] for i in range(3)),
                           tuple(s0[i] * s[i] for i in range(3)))
            else:
                pose[b] = (tuple(r), tuple(p), tuple(s))
    return pose


def model_quads(m, pose):
    """Posed quads of one model in bb space: (F,4,3)."""
    idx, mats = {}, []
    for i, (name, parent, pivot, rot) in enumerate(m["bones"]):
        pr, pp, ps = pose.get(name, ZERO)
        mm = _trs(pivot, tuple(rot[k] + pr[k] for k in range(3)), pp, ps)
        if parent:
            mm = mats[idx[parent]] @ mm
        idx[name] = i
        mats.append(mm)
    M = np.array(mats)[m["bone"]]
    return np.einsum("fij,fkj->fki", M[:, :3, :3], m["quads"]) + M[:, None, :3, 3]


def to_world(q, pos, yaw, s):
    y = math.radians(yaw)
    f = np.array([-math.sin(y), 0.0, math.cos(y)])
    r = np.array([-f[2], 0.0, f[0]])
    u = np.array([0.0, 1.0, 0.0])
    basis = np.stack([r, u, -f], axis=0) * (s / 16.0)      # rows: images of bb x, y, z
    return q @ basis + np.array(pos)


class Cam:
    def __init__(self, eye, target, fov=70.0, size=(880, 500)):
        self.eye = np.array(eye, dtype=float)
        fwd = np.array(target, dtype=float) - self.eye
        self.fwd = fwd / np.linalg.norm(fwd)
        up0 = np.array([0.0, 1.0, 0.0])
        if abs(self.fwd @ up0) > 0.999:
            up0 = np.array([0.0, 0.0, 1.0])
        self.right = np.cross(self.fwd, up0)
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.fwd)
        self.W, self.H = size
        self.f = (self.W / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P):
        d = P - self.eye
        z = d @ self.fwd
        zz = np.maximum(z, 1e-3)
        return self.W / 2 + self.f * (d @ self.right) / zz, self.H / 2 - self.f * (d @ self.up) / zz, z


class Frame:
    def __init__(self, cam):
        self.cam = cam
        self.pts = []    # (x, y, z, rgb) solid
        self.blend = []  # (x, y, z, rgb, a)
        self.labels = []

    def add_quads(self, Q, uv=None, atlas=None, mode=None, flat=None, glow_flat=0.0):
        cam = self.cam
        if len(Q) == 0:
            return
        c = Q.mean(axis=1)
        x, y, z = cam.project(Q.reshape(-1, 3))
        x, y, z = x.reshape(-1, 4), y.reshape(-1, 4), z.reshape(-1, 4)
        vis = (z.max(axis=1) > 0.3) & (x.max(axis=1) > 0) & (x.min(axis=1) < cam.W) & (y.max(axis=1) > 0) & (y.min(axis=1) < cam.H)
        if not vis.any():
            return
        zc = np.maximum(z.min(axis=1), 0.6)
        pxw = zc / cam.f * 0.8
        eu, ev = Q[:, 1] - Q[:, 0], Q[:, 3] - Q[:, 0]
        nu = SIZES[np.searchsorted(SIZES, np.clip(np.ceil(np.linalg.norm(eu, axis=1) / pxw), 1, 768))]
        nv = SIZES[np.searchsorted(SIZES, np.clip(np.ceil(np.linalg.norm(ev, axis=1) / pxw), 1, 768))]
        n = np.cross(eu, ev)
        ln = np.linalg.norm(n, axis=1)
        n = n / np.maximum(ln, 1e-9)[:, None]
        L = np.array([0.45, 0.8, -0.55])
        L /= np.linalg.norm(L)
        shade = 0.55 + 0.45 * np.abs(n @ L)
        key = nu * 1000 + nv
        for k in np.unique(key[vis]):
            sel = np.where(vis & (key == k))[0]
            a, b = int(k // 1000), int(k % 1000)
            s = (np.arange(a) + 0.5) / a
            t = (np.arange(b) + 0.5) / b
            P = (Q[sel, 0][:, None, None, :] + s[None, :, None, None] * eu[sel][:, None, None, :]
                 + t[None, None, :, None] * ev[sel][:, None, None, :])
            if atlas is not None:
                u0, v0, uw, vh = (uv[sel, i] for i in range(4))
                tu = u0[:, None] + np.minimum((s[None, :] * uw[:, None]).astype(int), np.maximum(uw[:, None] - 1, 0))
                tv = v0[:, None] + np.minimum((t[None, :] * vh[:, None]).astype(int), np.maximum(vh[:, None] - 1, 0))
                tu = np.clip(tu, 0, atlas.shape[1] - 1)
                tv = np.clip(tv, 0, atlas.shape[0] - 1)
                tex = atlas[tv[:, None, :], tu[:, :, None]].astype(np.float32) / 255.0     # (K,a,b,4)
            else:
                tex = np.empty((len(sel), a, b, 4), dtype=np.float32)
                fl = np.array(flat, dtype=np.float32)
                tex[..., :3] = fl[sel][:, None, None, :] if fl.ndim == 2 else fl
                tex[..., 3] = 1.0 - glow_flat * 250 / 255
            sh = shade[sel][:, None, None]
            px, py, pz = cam.project(P.reshape(-1, 3))
            tex = tex.reshape(-1, 4)
            sh = np.broadcast_to(sh, (len(sel), a, b)).reshape(-1)
            md = np.broadcast_to((mode[sel] if mode is not None else np.zeros(len(sel), dtype=np.int8))[:, None, None],
                                 (len(sel), a, b)).reshape(-1)
            ok = (pz > 0.3) & (px >= 0) & (px < cam.W - 1) & (py >= 0) & (py < cam.H - 1) & (tex[:, 3] > 0.004)
            so = ok & (md == 0)
            if so.any():
                glow = np.clip((1.0 - tex[so, 3]) / (250.0 / 255.0), 0, 1)[:, None]
                col = tex[so, :3] * (sh[so][:, None] * (1 - glow) + glow * 1.08)
                self.pts.append((px[so], py[so], pz[so], col))
            bo = ok & (md == 1)
            if bo.any():
                self.blend.append((px[bo], py[bo], pz[bo], tex[bo, :3], tex[bo, 3]))

    def box(self, lo, hi, color, glow=0.0):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        f = [((x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)), ((x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)),
             ((x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)), ((x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)),
             ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)), ((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0))]
        self.add_quads(np.array(f, dtype=float), flat=color, glow_flat=glow)

    def render(self, sky=(0.42, 0.55, 0.78), plane=True):
        cam = self.cam
        W, H = cam.W, cam.H
        img = np.empty((H, W, 3), dtype=np.float32)
        img[:] = np.array(sky, dtype=np.float32)
        zb = np.full(H * W, np.inf, dtype=np.float32)
        # ground: analytic checker on y = GROUND
        jj, ii = np.mgrid[0:H, 0:W]
        d = (cam.fwd[None, None, :] + ((ii - W / 2 + 0.5) / cam.f)[..., None] * cam.right[None, None, :]
             - ((jj - H / 2 + 0.5) / cam.f)[..., None] * cam.up[None, None, :])
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (GROUND - cam.eye[1]) / d[..., 1]
        hit = (t > 0) & (t < 400) & np.isfinite(t) & plane
        gx = cam.eye[0] + d[..., 0] * t
        gz = cam.eye[2] + d[..., 2] * t
        chk = ((np.floor(gx) + np.floor(gz)) % 2 == 0)
        big = ((np.floor(gx / 8) + np.floor(gz / 8)) % 2 == 0)
        g = np.where(chk, 0.36, 0.31) + np.where(big, 0.035, 0.0)
        fog = np.clip(t / 220.0, 0, 1)[..., None]
        gcol = np.stack([g * 0.75, g * 1.05, g * 0.62], axis=-1)
        gcol = gcol * (1 - fog) + np.array(sky, dtype=np.float32) * fog
        img[hit] = gcol[hit]
        zb.reshape(H, W)[hit] = t[hit]
        flat = img.reshape(-1, 3)
        if self.pts:
            px = np.concatenate([p[0] for p in self.pts])
            py = np.concatenate([p[1] for p in self.pts])
            pz = np.concatenate([p[2] for p in self.pts]).astype(np.float32)
            col = np.concatenate([p[3] for p in self.pts]).astype(np.float32)
            ix, iy = px.astype(np.int32), py.astype(np.int32)
            order = np.argsort(-pz, kind="stable")
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                idx = (iy + dy) * W + ix + dx
                io, zo, co = idx[order], pz[order], col[order]
                keep = zo < zb[io]
                io, zo, co = io[keep], zo[keep], co[keep]
                flat[io] = np.clip(co, 0, 1)
                zb[io] = zo
        if self.blend:
            px = np.concatenate([p[0] for p in self.blend])
            py = np.concatenate([p[1] for p in self.blend])
            pz = np.concatenate([p[2] for p in self.blend]).astype(np.float32)
            col = np.concatenate([p[3] for p in self.blend]).astype(np.float32)
            al = np.concatenate([p[4] for p in self.blend]).astype(np.float32)
            idx = py.astype(np.int32) * W + px.astype(np.int32)
            order = np.argsort(-pz, kind="stable")
            io, zo, co, ao = idx[order], pz[order], col[order], al[order]
            keep = zo < zb[io]
            io, co, ao = io[keep], co[keep], ao[keep]
            # nearest blend sample per pixel wins (last write), composited once over the solid image
            last = np.full(H * W, -1, dtype=np.int64)
            last[io] = np.arange(len(io))
            pix = np.where(last >= 0)[0]
            j = last[pix]
            flat[pix] = flat[pix] * (1 - ao[j][:, None]) + np.clip(co[j], 0, 1) * ao[j][:, None]
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
        return out, zb.reshape(H, W)


_terr = {}


def terrain_quads(tr):
    """Top and side faces of the recorded height map as quads + colours."""
    key = id(tr)
    if key in _terr:
        return _terr[key]
    T = tr["terrain"]
    n, x0, z0 = T["n"], T["x0"], T["z0"]
    h = np.array(T["h"], dtype=float).reshape(n, n)       # [z, x]
    q, col = [], []
    for zi in range(n):
        for xi in range(n):
            x, z, y = x0 + xi, z0 + zi, h[zi, xi]
            c = 0.36 if (x + z) % 2 == 0 else 0.31
            q.append(((x, y, z), (x + 1, y, z), (x + 1, y, z + 1), (x, y, z + 1)))
            col.append((c * 0.75, c * 1.05, c * 0.62))
            for dx, dz, a, b in ((1, 0, (x + 1, z), (x + 1, z + 1)), (-1, 0, (x, z + 1), (x, z)),
                                 (0, 1, (x + 1, z + 1), (x, z + 1)), (0, -1, (x, z), (x + 1, z))):
                xj, zj = xi + dx, zi + dz
                lo = h[zj, xj] if 0 <= xj < n and 0 <= zj < n else y - 2
                if lo < y:
                    q.append(((a[0], y, a[1]), (b[0], y, b[1]), (b[0], lo, b[1]), (a[0], lo, a[1])))
                    col.append((0.42, 0.33, 0.24))
    _terr[key] = (np.array(q, dtype=float), np.array(col, dtype=np.float32))
    return _terr[key]


def ground_at(tr, x, z):
    T = tr.get("terrain")
    if not T:
        return GROUND
    xi, zi = int(math.floor(x)) - T["x0"], int(math.floor(z)) - T["z0"]
    if 0 <= xi < T["n"] and 0 <= zi < T["n"]:
        return T["h"][zi * T["n"] + xi]
    return GROUND


def row_at(a, tick):
    """Latest trace row at or before tick, and the tick its state value began."""
    f = a["f"]
    cur = None
    for r in f:
        if r[0] <= tick:
            cur = r
        else:
            break
    if cur is None:
        return None, 0
    since = cur[0]
    for r in reversed(f):
        if r[0] > cur[0]:
            continue
        if r[5] != cur[5]:
            break
        since = r[0]
    return cur, since


def cam_for(view, tr, tick, fov, size, cam_spec):
    cas = tr["caster"][0]
    cp = np.array(cas[1:4])
    yaw = math.radians(cas[4])
    fw = np.array([-math.sin(yaw), 0.0, math.cos(yaw)])
    rt = np.array([-fw[2], 0.0, fw[0]])
    up = np.array([0.0, 1.0, 0.0])
    loc = lambda r, u, f: cp + rt * r + up * u + fw * f   # noqa: E731
    if cam_spec:
        v = [float(x) for x in cam_spec.split(",")]
        return Cam(loc(*v[:3]), loc(*v[3:6]), fov, size)
    if view == "pov":
        pitch = math.radians(cas[5])
        return Cam(cp + up * 1.62, cp + up * 1.62 + fw * math.cos(pitch) * 10 - up * math.sin(pitch) * 10, 70, size)
    if view == "top":
        return Cam(loc(0, 70, 12), loc(0, 0, 12.01), 50, size)
    if view == "side":
        return Cam(loc(34, 8, 12), loc(0, 5, 12), 55, size)
    if view == "front":
        return Cam(loc(0, 7, 44), loc(0, 5, 10), 55, size)
    if view == "wide":
        return Cam(loc(-14, 16, -26), loc(0, 6, 16), 62, size)
    return Cam(loc(-4.5, 6.5, -11), loc(0, 3.0, 12), 62, size)  # chase


def draw_frame(tr, tick, view="chase", size=(880, 500), fov=62, labels=False, cam_spec=None, show_blocks=True):
    cam = cam_for(view, tr, tick, fov, size, cam_spec)
    fr = Frame(cam)
    notes = []
    for aid, a in tr["actors"].items():
        if a["spawn"] > tick or (0 <= a["end"] <= tick):
            continue
        row, since = row_at(a, tick)
        if row is None:
            continue
        _, x, y, z, yaw, state, kind, size_p, skin = row
        d = actor_def(a["type"])
        if d is None:
            notes.append(f"no mesh for {a['type']}")
            continue
        if state == 0:
            continue
        pose = merged_pose(d, int(state), (tick - since) / 20.0, (tick - a["spawn"]) / 20.0)
        m = d["models"][min(int(kind), len(d["models"]) - 1)]
        sc = d["scale"] if not isinstance(d["scale"], str) else 1.0
        try:
            sc = float(sc)
        except Exception:
            sc = 1.0
        if d["size_prop"]:
            sc *= float(size_p)
        if len(m["quads"]) == 0 or sc <= 0:
            continue
        q = model_quads(m, pose)
        w = to_world(q.reshape(-1, 3), (x, y, z), yaw, sc).reshape(-1, 4, 3)
        sk = d["skins"][int(skin)] if int(skin) < len(d["skins"]) else "default"
        atlas = m["atlas"].get(sk, m["atlas"]["default"])
        fr.add_quads(w, uv=m["uv"], atlas=atlas, mode=m["mode"])
        if labels:
            fr.labels.append(((x, y, z), f"{a['type']}:{int(state)}" + (f"k{int(kind)}" if kind else "")))
    # caster and mobs
    cas = min(tr["caster"], key=lambda r: abs(r[0] - tick))
    cx, cy, cz = cas[1:4]
    fr.box((cx - 0.3, cy, cz - 0.3), (cx + 0.3, cy + 1.8, cz + 0.3), (0.2, 0.45, 1.0), glow=0.6)
    mrow = min(tr["mobs"], key=lambda r: abs(r[0] - tick))
    for mx, my, mz, alive in [m for m in mrow[1:] if isinstance(m, list)]:
        if alive:
            fr.box((mx - 0.3, my, mz - 0.3), (mx + 0.3, my + 1.9, mz + 0.3), (0.25, 0.75, 0.25), glow=0.5)
    if show_blocks:
        cells = {}
        for t, bx, by, bz, typ in tr["blocks"]:
            if t > tick:
                break
            if typ == "minecraft:air":
                cells.pop((bx, by, bz), None)
            else:
                cells[(bx, by, bz)] = typ
        bq = []
        for (bx, by, bz), typ in cells.items():
            if "barrier" in typ:
                c = 0.5
                bq.append(((bx + 0.5 - 0.12, by + 0.5 + 0.12, bz + 0.5), (bx + 0.5 + 0.12, by + 0.5 + 0.12, bz + 0.5),
                           (bx + 0.5 + 0.12, by + 0.5 - 0.12, bz + 0.5), (bx + 0.5 - 0.12, by + 0.5 - 0.12, bz + 0.5)))
                bq.append(((bx + 0.5, by + 0.5 + 0.12, bz + 0.5 - 0.12), (bx + 0.5, by + 0.5 + 0.12, bz + 0.5 + 0.12),
                           (bx + 0.5, by + 0.5 - 0.12, bz + 0.5 + 0.12), (bx + 0.5, by + 0.5 - 0.12, bz + 0.5 - 0.12)))
                bq.append(((bx + 0.38, by + 0.5, bz + 0.38), (bx + 0.62, by + 0.5, bz + 0.38),
                           (bx + 0.62, by + 0.5, bz + 0.62), (bx + 0.38, by + 0.5, bz + 0.62)))
        if bq:
            fr.add_quads(np.array(bq, dtype=float), flat=(1.0, 0.15, 0.15), glow_flat=1.0)
    if tr.get("terrain"):
        tq, tc = terrain_quads(tr)
        fr.add_quads(tq, flat=tc)
    img, zb = fr.render(plane=not tr.get("terrain"))
    dr = ImageDraw.Draw(img)
    # particles spawned during the last half second
    for t, pid, px, py, pz in tr["particles"]:
        if t > tick or t < tick - 10:
            continue
        sx, sy, sz = cam.project(np.array([[px, py, pz]]))
        if sz[0] > 0.3 and 0 <= sx[0] < cam.W and 0 <= sy[0] < cam.H:
            h = zlib.crc32(pid.encode())
            col = (150 + h % 106, 150 + (h >> 8) % 106, 150 + (h >> 16) % 106)
            r = 2 if sz[0] > 25 else 3
            dr.ellipse((sx[0] - r, sy[0] - r, sx[0] + r, sy[0] + r), outline=col)
    for (x, y, z), text in fr.labels:
        sx, sy, sz = cam.project(np.array([[x, y, z]]))
        if sz[0] > 0.3 and 0 <= sx[0] < cam.W and 0 <= sy[0] < cam.H:
            dr.line((sx[0] - 3, sy[0], sx[0] + 3, sy[0]), fill=(255, 255, 0))
            dr.line((sx[0], sy[0] - 3, sx[0], sy[0] + 3), fill=(255, 255, 0))
            dr.text((sx[0] + 4, sy[0] - 4), text, fill=(255, 255, 255))
    dr.text((6, 4), f"{tr['id']}  {view}  t={(tick - tr['release']) / 20:.2f}s (tick {tick})", fill=(255, 255, 255))
    for i, nline in enumerate(sorted(set(notes))[:6]):
        dr.text((6, 18 + 12 * i), nline, fill=(255, 120, 120))
    return img


def report(tr):
    rel = tr["release"]
    cas = tr["caster"][0]
    by = {}
    for a in tr["actors"].values():
        by.setdefault(a["type"], []).append(a)
    print(f"== {tr['id']}: {tr['ticks']} ticks ({(tr['ticks'] - rel) / 20:.1f}s after release), dmg {tr['dmg']}, problems {tr['problems']}")
    for typ, lst in sorted(by.items(), key=lambda kv: min(a["spawn"] for a in kv[1])):
        d = actor_def(typ)
        life = d["lifetime"] if d else None
        sp = [(a["spawn"] - rel) / 20 for a in lst]
        alive = [((a["end"] if a["end"] >= 0 else tr["ticks"]) - a["spawn"]) / 20 for a in lst]
        ys = [r[2] - ground_at(tr, r[1], r[3]) + GROUND for a in lst for r in a["f"]]
        ds = [math.hypot(r[1] - cas[1], r[3] - cas[3]) for a in lst for r in a["f"]]
        states = []
        for a in lst[:1]:
            last = None
            for r in a["f"]:
                if r[5] != last:
                    states.append(f"{int(r[5])}@{(r[0] - rel) / 20:.1f}")
                    last = r[5]
        hid = 0.0
        for a in lst:
            f = a["f"]
            end = a["end"] if a["end"] >= 0 else tr["ticks"]
            for i, r in enumerate(f):
                nxt = f[i + 1][0] if i + 1 < len(f) else end
                if r[5] == 0:
                    hid += (nxt - r[0]) / 20
        sizes = sorted({r[7] for a in lst for r in a["f"]})
        kinds = sorted({int(r[6]) for a in lst for r in a["f"]})
        flag = ""
        if life is not None and max(alive) > life - 0.5:
            flag += f"  !! OUTLIVES timer {life}s"
        if min(ys) < GROUND - 0.01:
            flag += f"  (below ground min y={min(ys) - GROUND:+.1f})"
        if max(ds) > 56:
            flag += f"  (far {max(ds):.0f}m)"
        if hid > 0.3 * len(lst):
            flag += f"  (hidden {hid / len(lst):.1f}s avg)"
        print(f"  {typ:26s} x{len(lst):<3d} spawn {min(sp):6.1f}..{max(sp):6.1f}s  alive {min(alive):5.1f}..{max(alive):5.1f}s"
              f"  y {min(ys) - GROUND:+5.1f}..{max(ys) - GROUND:+5.1f}  dist {min(ds):4.1f}..{max(ds):4.1f}"
              f"  kinds {kinds} size {sizes[0]:g}..{sizes[-1]:g}  st {' '.join(states[:9])}{flag}")
    per = {}
    for p in tr["particles"]:
        per[p[0]] = per.get(p[0], 0) + 1
    if per:
        print(f"  particles: total {len(tr['particles'])}, peak/tick {max(per.values())}, ticks at cap(>=90): {sum(1 for v in per.values() if v >= 90)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spell")
    ap.add_argument("--times", default="")
    ap.add_argument("--view", default="chase")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--hills", action="store_true")
    ap.add_argument("--real", default=None, nargs="?", const="", help="trace recorded on a real server (tools/real_trace.py)")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--cam", default="")
    ap.add_argument("--fov", type=float, default=62)
    ap.add_argument("--size", default="880x500")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(HERE, "_preview", "scene"))
    args = ap.parse_args()
    suffix = "_hills" if args.hills else ""
    if args.real is not None:
        suffix = "_real" + (("_" + args.real) if args.real else "")
    tr = json.load(open(os.path.join(TRACE, f"{args.spell}{suffix}.json")))
    if suffix:
        tr["id"] += " " + suffix[1:]
    report(tr)
    if args.report:
        return
    size = tuple(int(v) for v in args.size.split("x"))
    rel, end = tr["release"], tr["ticks"] - 10
    if args.times:
        ticks = [rel + int(round(float(t) * 20)) for t in args.times.split(",")]
    else:
        ticks = [int(rel + (end - rel) * (i + 0.5) / args.n) for i in range(args.n)]
    views = args.view.split(",")
    cells = [draw_frame(tr, t, v, size, args.fov, args.labels, args.cam or None) for t in ticks for v in views]
    cols = args.cols if len(views) == 1 else len(views)
    rows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * size[0], rows * size[1]))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % cols) * size[0], (i // cols) * size[1]))
    os.makedirs(args.out, exist_ok=True)
    name = f"{args.spell}{suffix}_{'-'.join(views)}{'_' + args.times.replace(',', '_') if args.times else ''}.jpg"
    path = os.path.join(args.out, name)
    sheet.save(path, quality=88)
    print(path)


if __name__ == "__main__":
    main()
