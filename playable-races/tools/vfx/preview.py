"""Offline preview of Bedrock particle effects (the subset this add-on writes).

Simulates emitters (instant / steady rates, once lifetimes, point / sphere / disc / box
shapes, creation and timeline events that start child effects), particles (Molang
lifetimes, speed, acceleration, drag, parametric motion, ground collision, spin) and their
appearance (Molang sizes, lookat_xyz / lookat_y / lookat_direction / emitter_transform_xz,
static, picked and flipbook UVs, constant and gradient tints, add / blend / alpha), then
draws them over a race model rendered with kit.render, frame by frame.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence

import numpy as np
from PIL import Image

from kit import molang
from kit.render import render

U = 16.0   # model units per block


def _num(x, env):
    return float(molang.evaluate(x, env)) if isinstance(x, str) else float(x)


def _vec(v, env):
    return np.array([_num(c, env) for c in v], float)


class Emitter:
    def __init__(self, sim, name, origin, t0, vars_):
        self.sim, self.name, self.origin, self.t0 = sim, name, np.array(origin, float), t0
        self.pe = sim.effects[name]["particle_effect"]
        self.c = self.pe["components"]
        self.vars = dict(vars_)
        self.rand = [random.random() for _ in range(4)]
        once = self.c.get("minecraft:emitter_lifetime_once")
        self.active = float(once.get("active_time", 0.05)) if once else 1.0
        self.done_spawn = False
        self.accum = 0.0
        self.alive: List[dict] = []
        self.fired = set()
        self.age = 0.0
        lev = self.c.get("minecraft:emitter_lifetime_events", {})
        ce = lev.get("creation_event")
        for ev in ([ce] if isinstance(ce, str) else (ce or [])):
            self.fire(ev, t0)

    def env(self, p=None):
        v = dict(self.vars)
        v.update({"emitter_age": self.age, "emitter_lifetime": self.active})
        for i, r in enumerate(self.rand):
            v[f"emitter_random_{i + 1}"] = r
        if p is not None:
            v.update({"particle_age": p["age"], "particle_lifetime": p["life"]})
            for i, r in enumerate(p["rand"]):
                v[f"particle_random_{i + 1}"] = r
        return molang.Env(v=v)

    def fire(self, ev, now):
        e = self.pe.get("events", {}).get(ev, {})
        pe = e.get("particle_effect")
        if pe:
            child = pe["effect"].split(":")[-1]
            if child in self.sim.effects:
                self.sim.emitters.append(Emitter(self.sim, child, self.origin, now, {}))
        for sub in e.get("sequence", []):
            for k, v in sub.items():
                pass

    def spawn(self):
        c = self.c
        p = {"age": 0.0, "life": 1.0, "rand": [random.random() for _ in range(4)]}
        env = self.env(p)
        life = c.get("minecraft:particle_lifetime_expression", {}).get("max_lifetime", 1.0)
        p["life"] = max(0.02, _num(life, env))
        env = self.env(p)
        pos, d = np.zeros(3), np.zeros(3)
        for key in ("minecraft:emitter_shape_point", "minecraft:emitter_shape_sphere", "minecraft:emitter_shape_disc",
                    "minecraft:emitter_shape_box"):
            sh = c.get(key)
            if sh is None:
                continue
            off = _vec(sh.get("offset", [0, 0, 0]), env)
            if key.endswith("point"):
                pos = off
                d = np.zeros(3)
            elif key.endswith("sphere"):
                u = np.random.normal(size=3)
                u /= np.linalg.norm(u) + 1e-9
                r = _num(sh.get("radius", 0), env) * (1.0 if sh.get("surface_only") else random.random() ** (1 / 3))
                pos, d = off + u * r, u
            elif key.endswith("disc"):
                a = random.uniform(0, 2 * math.pi)
                r = _num(sh.get("radius", 0), env) * (1.0 if sh.get("surface_only") else math.sqrt(random.random()))
                u = np.array([math.cos(a), 0, math.sin(a)])
                pos, d = off + u * r, u
            else:
                hd = _vec(sh.get("half_dimensions", [0, 0, 0]), env)
                pos = off + np.array([random.uniform(-1, 1) for _ in range(3)]) * hd
                d = pos / (np.linalg.norm(pos) + 1e-9)
            dirn = sh.get("direction", "outwards")
            if dirn == "inwards":
                d = -d
            elif isinstance(dirn, list):
                d = _vec(dirn, env)
                d /= np.linalg.norm(d) + 1e-9
            break
        speed = _num(c.get("minecraft:particle_initial_speed", 0), env)
        p["pos"], p["vel"], p["p0"] = pos, d * speed, pos.copy()
        spin = c.get("minecraft:particle_initial_spin", {})
        p["rot"] = _num(spin.get("rotation", 0), env)
        p["rot_rate"] = _num(spin.get("rotation_rate", 0), env)
        self.alive.append(p)

    def step(self, now, dt):
        c = self.c
        prev = self.age
        self.age = now - self.t0
        lev = c.get("minecraft:emitter_lifetime_events", {})
        for k, ev in lev.get("timeline", {}).items():
            if prev < float(k) <= self.age and k not in self.fired:
                self.fired.add(k)
                for e in ([ev] if isinstance(ev, str) else ev):
                    self.fire(e, now)
        if "minecraft:emitter_rate_instant" in c and not self.done_spawn:
            n = int(_num(c["minecraft:emitter_rate_instant"]["num_particles"], self.env()))
            for _ in range(n):
                self.spawn()
            self.done_spawn = True
        elif "minecraft:emitter_rate_steady" in c and self.age <= self.active:
            st = c["minecraft:emitter_rate_steady"]
            self.accum += _num(st["spawn_rate"], self.env()) * dt
            while self.accum >= 1 and len(self.alive) < _num(st["max_particles"], self.env()):
                self.spawn()
                self.accum -= 1
        dyn = c.get("minecraft:particle_motion_dynamic", {})
        par = c.get("minecraft:particle_motion_parametric", {}).get("relative_position")
        col = c.get("minecraft:particle_motion_collision")
        keep = []
        for p in self.alive:
            p["age"] += dt
            if p["age"] > p["life"]:
                continue
            env = self.env(p)
            if par is not None:
                p["pos"] = _vec(par, env)
            else:
                acc = _vec(dyn.get("linear_acceleration", [0, 0, 0]), env)
                drag = _num(dyn.get("linear_drag_coefficient", 0), env)
                p["vel"] = p["vel"] + (acc - drag * p["vel"]) * dt
                p["pos"] = p["pos"] + p["vel"] * dt
                if col is not None:
                    floor = -self.origin[1] + float(col.get("collision_radius", 0.05))
                    if p["pos"][1] < floor and p["vel"][1] < 0:
                        p["pos"][1] = floor
                        p["vel"][1] = -p["vel"][1] * float(col.get("coefficient_of_restitution", 0))
                        p["vel"][[0, 2]] *= max(0.0, 1 - float(col.get("collision_drag", 0)) * 0.1)
            p["rot"] += p["rot_rate"] * dt
            keep.append(p)
        self.alive = keep

    def finished(self):
        return self.age > self.active and not self.alive and self.done_or_steady()

    def done_or_steady(self):
        lev = self.c.get("minecraft:emitter_lifetime_events", {})
        last = max([float(k) for k in lev.get("timeline", {})] + [0.0])
        return self.age > last


class Sim:
    def __init__(self, effects: Dict[str, dict]):
        self.effects = effects
        self.emitters: List[Emitter] = []

    def start(self, name, origin=(0, 0, 0), t=0.0, vars_=None):
        self.emitters.append(Emitter(self, name, origin, t, vars_ or {}))

    def step(self, now, dt):
        for em in list(self.emitters):
            em.step(now, dt)
        self.emitters = [e for e in self.emitters if not e.finished()]

    def drawables(self, atlases: Dict[str, Image.Image]):
        out = []
        for em in self.emitters:
            pe = em.pe
            tex = atlases.get(pe["description"]["basic_render_parameters"]["texture"])
            mat = pe["description"]["basic_render_parameters"]["material"]
            bb = em.c.get("minecraft:particle_appearance_billboard")
            if bb is None or tex is None:
                continue
            tint_c = em.c.get("minecraft:particle_appearance_tinting", {}).get("color", [1, 1, 1, 1])
            for p in em.alive:
                env = em.env(p)
                w, h = _num(bb["size"][0], env), _num(bb["size"][1], env)
                if w <= 0 or h <= 0:
                    continue
                uv = bb.get("uv", {})
                if "flipbook" in uv:
                    fb = uv["flipbook"]
                    mf = int(_num(fb["max_frame"], env))
                    if fb.get("stretch_to_lifetime"):
                        fr = min(mf - 1, int(p["age"] / p["life"] * mf))
                    else:
                        fr = int(p["age"] * float(fb.get("frames_per_second", 8)))
                        fr = fr % mf if fb.get("loop") else min(mf - 1, fr)
                    bx, by = _vec(fb["base_UV"], env)
                    sx, sy = _vec(fb.get("step_UV", [0, 0]), env)
                    cw, ch = _vec(fb["size_UV"], env)
                    rect = (bx + sx * fr, by + sy * fr, cw, ch)
                elif "uv" in uv:
                    ux, uy = _vec(uv["uv"], env)
                    rect = (ux, uy, *_vec(uv["uv_size"], env))
                else:
                    rect = (0, 0, tex.width, tex.height)
                if isinstance(tint_c, dict):
                    t = _num(tint_c.get("interpolant", 0), env)
                    keys = sorted((float(k), v) for k, v in tint_c["gradient"].items())
                    col = np.array(keys[-1][1], float)
                    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
                        if t0 <= t <= t1:
                            f = (t - t0) / max(t1 - t0, 1e-6)
                            col = np.array(c0, float) * (1 - f) + np.array(c1, float) * f
                            break
                    if t < keys[0][0]:
                        col = np.array(keys[0][1], float)
                else:
                    col = np.array([_num(x, env) for x in tint_c], float)
                    if len(col) == 3:
                        col = np.append(col, 1.0)
                dirv = None
                dspec = bb.get("direction")
                if dspec and dspec.get("mode") == "custom":
                    dirv = _vec(dspec.get("custom_direction", [0, 1, 0]), env)
                out.append({"pos": em.origin + p["pos"], "vel": p["vel"] if dirv is None else dirv, "w": w, "h": h, "rot": p["rot"],
                            "mode": bb.get("facing_camera_mode", "lookat_xyz"), "tex": tex, "rect": rect, "col": col, "mat": mat})
        return out


class Camera:
    def __init__(self, yaw, pitch, scale, center, size):
        th, ph = math.radians(yaw), math.radians(pitch)
        self.f = np.array([math.sin(th) * math.cos(ph), -math.sin(ph), math.cos(th) * math.cos(ph)])
        r = np.cross([0.0, 1.0, 0.0], self.f)
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.f, self.r)
        self.scale, self.center, self.size = scale, np.array(center, float), size

    def project(self, p_blocks, ss=1):
        rel = np.asarray(p_blocks, float) * U - self.center
        return (self.size[0] * ss / 2 + (rel @ self.r) * self.scale * ss, self.size[1] * ss / 2 - (rel @ self.u) * self.scale * ss,
                rel @ self.f)


def _corners(d, cam: Camera):
    """Four world corners (blocks) of a particle quad: top-left, top-right, bottom-right, bottom-left."""
    c, w, h = d["pos"], d["w"], d["h"]
    rot = math.radians(d["rot"])
    mode = d["mode"]
    if mode == "emitter_transform_xz":
        a, b = np.array([1.0, 0, 0]), np.array([0, 0, 1.0])
    elif mode == "lookat_y":
        a = cam.r
        b = np.array([0, -1.0, 0])
    elif mode == "lookat_direction":
        v = d["vel"]
        if np.linalg.norm(v) < 1e-4:
            v = np.array([0, 1.0, 0])
        b = -v / np.linalg.norm(v)
        a = np.cross(b, cam.f)
        if np.linalg.norm(a) < 1e-6:
            a = cam.r
        a = a / np.linalg.norm(a)
    else:
        a, b = cam.r, -cam.u
    if mode != "lookat_direction" and mode != "lookat_y":
        a, b = a * math.cos(rot) + b * math.sin(rot), -a * math.sin(rot) + b * math.cos(rot)
    hw, hh = a * w / 2, b * h / 2
    return [c - hw - hh, c + hw - hh, c + hw + hh, c - hw + hh]


def _draw(frame: np.ndarray, d, cam: Camera, ss=1):
    pts = [cam.project(p, ss)[:2] for p in _corners(d, cam)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
    x1, y1 = int(math.ceil(max(xs))) + 1, int(math.ceil(max(ys))) + 1
    H, W = frame.shape[:2]
    if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H or x1 - x0 > 4000 or y1 - y0 > 4000:
        return
    rx, ry, rw, rh = d["rect"]
    spr = d["tex"].crop((int(rx), int(ry), int(rx + rw), int(ry + rh)))
    # affine map: destination (x, y) -> sprite (u, v) from three corners
    (ax, ay), (bx, by), _, (dx_, dy_) = pts
    A = np.array([[bx - ax, dx_ - ax], [by - ay, dy_ - ay]])
    if abs(np.linalg.det(A)) < 1e-6:
        return
    Ai = np.linalg.inv(A) * np.array([[spr.width], [spr.height]])
    a_, b_ = Ai[0]
    d_, e_ = Ai[1]
    c_ = -(a_ * (ax - x0) + b_ * (ay - y0))
    f_ = -(d_ * (ax - x0) + e_ * (ay - y0))
    warped = spr.transform((x1 - x0, y1 - y0), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BILINEAR)
    sp = np.asarray(warped, float) / 255.0
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    sp = sp[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    col = d["col"]
    rgb = sp[..., :3] * col[:3]
    a = sp[..., 3:4] * col[3]
    region = frame[cy0:cy1, cx0:cx1]
    if d["mat"] == "particles_add":
        region += rgb * a
    elif d["mat"] == "particles_alpha":
        m = (a >= 0.5).astype(float)
        region[:] = region * (1 - m) + rgb * m
    else:
        region[:] = region * (1 - a) + rgb * a


def run(effects: Dict[str, dict], atlases: Dict[str, Image.Image], entry: str, *, vars_=None, model=None, texture=None,
        variant=None, pose=None, yaw=30.0, pitch=18.0, size=(420, 360), scale=5.0, center=(0, 14, 0), seconds=1.6, fps=20,
        origin=(0, 0, 0), extra: Sequence = (), bg=(30, 32, 40), label: str = "", seed: int = 1) -> List[Image.Image]:
    """Frames of `entry` spawned at `origin` (blocks; the model stands at 0,0,0).
    extra: [(time, effect, origin, vars)] further spawns (several script calls)."""
    random.seed(seed)
    np.random.seed(seed)
    sim = Sim(effects)
    sched = sorted([(0.0, entry, origin, vars_ or {})] + list(extra), key=lambda x: x[0])
    cam = Camera(yaw, pitch, scale, center, size)
    frames = []
    dt = 1.0 / fps
    n = int(round(seconds * fps))
    base = None
    for i in range(n + 1):
        now = i * dt
        while sched and sched[0][0] <= now + 1e-9:
            t, e, o, v = sched.pop(0)
            sim.start(e, o, now, v)
        sim.step(now, dt)
        ds = sorted(sim.drawables(atlases), key=lambda d: -cam.project(d["pos"])[2])
        ground = [d for d in ds if d["mode"] == "emitter_transform_xz"]
        rest = [d for d in ds if d["mode"] != "emitter_transform_xz"]

        def backdrop(img, ss):
            arr = np.asarray(img, float) / 255.0
            arr = arr.copy()
            for d in ground:
                _draw(arr, d, cam, ss)
            img.paste(Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)))
        if model is not None:
            im = render(model, texture, variant=variant, pose=pose, yaw=yaw, pitch=pitch, size=size, scale=scale, center=center,
                        bg=bg, backdrop=backdrop, hide=["r_arm_fp", "l_arm_fp"], ground=True)
        else:
            img = Image.new("RGB", size, bg)
            backdrop(img, 1)
            im = img
        arr = np.asarray(im, float) / 255.0
        arr = arr.copy()
        for d in rest:
            _draw(arr, d, cam)
        frame = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
        if label:
            from PIL import ImageDraw
            ImageDraw.Draw(frame).text((8, 6), label, fill=(235, 235, 240))
        frames.append(frame)
    return frames


def sheet_strip(frames: List[Image.Image], picks: Sequence[int], cols: int = 4) -> Image.Image:
    sel = [frames[i] for i in picks if i < len(frames)]
    w, h = sel[0].size
    rows = (len(sel) + cols - 1) // cols
    out = Image.new("RGB", (w * cols, h * rows), (0, 0, 0))
    for k, f in enumerate(sel):
        out.paste(f, ((k % cols) * w, (k // cols) * h))
    return out
