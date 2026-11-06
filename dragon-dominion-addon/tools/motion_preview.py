#!/usr/bin/env python3
"""
Animated previews (GIF) rendered from the pack's real geometry, texture and keyframes, including the
controller cross-fades (linear blend over each state's blend_transition) and the spring-eased wing layers,
so what you see is how the client should blend between states. NOT a capture from Minecraft.

    python3 tools/motion_preview.py            -> docs/preview/anim/*.gif  + docs/preview/anim/fight_reel.gif
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kinematics as K
import render_preview as R

OUT = os.path.join(R.OUT, "anim")
FPS = 20
A = R.anims()
NSA = "animation.dragon_dominion.gharvok."
BLEND_ACTION, BLEND_LOCO = 0.3, 0.4


class Spring:
    def __init__(self, v, k, c):
        self.x, self.v, self.k, self.c = v, 0.0, k, c

    def step(self, target, dt):
        self.v += ((target - self.x) * self.k - self.v * self.c) * dt
        self.x = min(1.0, max(0.0, self.x + self.v * dt))
        return self.x


def timeline(segments):
    """segments: [(locomotion_anim, action_anim or None, seconds)]. Yields per-frame (spec, label)."""
    fold, disp = Spring(1, 36, 12), Spring(1, 25, 10)
    prev = {}  # anim -> (start_time, weight at fade-out start, fade start)
    t_global = 0.0
    active = []  # [name, start, fade_in_end, fade_out_start or None]
    for loco, action, dur in segments:
        for a in active:
            if a[3] is None and a[0] not in (loco, action):
                a[3] = t_global
        for name in (loco, action):
            if name and not any(a[0] == name and a[3] is None for a in active):
                active.append([name, t_global, t_global + (BLEND_ACTION if name == action else BLEND_LOCO), None])
        tf, td = R.wing_weights(action or loco)
        if action is None and loco in ("walk", "run", "idle_breathing"):
            tf, td = R.wing_weights(loco)
        n = int(dur * FPS)
        for _ in range(n):
            spec = []
            for a in list(active):
                name, start, fin, fout = a
                w = min(1.0, (t_global - start) / max(1e-6, fin - start))
                if fout is not None:
                    w *= max(0.0, 1 - (t_global - fout) / (BLEND_ACTION))
                    if w <= 0:
                        active.remove(a)
                        continue
                anim = A[NSA + name]
                t = t_global - start
                if not anim.get("loop") is True:
                    t = min(t, anim["animation_length"])
                spec.append((name, t, w))
            f = fold.step(tf, 1 / FPS)
            d = disp.step(td, 1 / FPS)
            spec += [("wing_fold", 0.0, f), ("wing_display", 0.0, d)]
            yield spec, action or loco
            t_global += 1 / FPS


def render_gif(segments, name, yaw=55, pitch=12, size=(560, 400), scale=1.9, label=True):
    frames = []
    for spec, lab in timeline(segments):
        cam = K.Camera((0, 36, 10), yaw, pitch, scale=scale, size=size)
        im = R.render(cam, R.pose_of(spec))
        if label:
            ImageDraw.Draw(im).text((10, 8), lab, fill=(60, 60, 60), font=R.font(16))
        frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=128))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    frames[0].save(p, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    print("wrote", p, len(frames), "frames")


L = lambda n: A[NSA + n]["animation_length"]
CLIPS = {
    "idle": [("idle_breathing", None, 6.4)],
    "walk": [("walk", None, 2.6)],
    "run": [("run", None, 1.5)],
    "roar": [("idle_breathing", None, 0.4), ("idle_breathing", "roar", L("roar")), ("idle_breathing", None, 0.8)],
    "claw_combo": [("idle_breathing", None, 0.3), ("idle_breathing", "claw_combo", L("claw_combo")), ("idle_breathing", None, 0.6)],
    "crushing_charge": [("idle_breathing", "charge_windup", L("charge_windup")), ("idle_breathing", "charge", 1.2),
                        ("idle_breathing", "charge_impact", L("charge_impact")), ("idle_breathing", "stagger", 1.6),
                        ("idle_breathing", None, 0.8)],
    "tail_sweep": [("idle_breathing", None, 0.3), ("idle_breathing", "tail_sweep", L("tail_sweep")), ("idle_breathing", None, 0.6)],
    "wing_pressure": [("idle_breathing", None, 0.3), ("idle_breathing", "wing_pressure", L("wing_pressure")), ("idle_breathing", None, 0.8)],
    "cliff_dive": [("idle_breathing", "takeoff", L("takeoff")), ("wing_flap", None, 1.6), ("glide", "cliff_dive", 0.9),
                   ("idle_breathing", "landing", L("landing")), ("idle_breathing", None, 0.8)],
    "skullbreaker": [("idle_breathing", None, 0.3), ("idle_breathing", "skullbreaker", L("skullbreaker")), ("idle_breathing", None, 0.8)],
    "skull_fracture": [("idle_breathing", None, 0.3), ("idle_breathing", "skull_fracture", L("skull_fracture")), ("idle_breathing", "exhausted", 2.4), ("idle_breathing", None, 0.6)],
    "death": [("idle_breathing", None, 0.3), ("idle_breathing", "death", L("death") + 0.6)],
}

if __name__ == "__main__":
    only = sys.argv[1:]
    for name, seg in CLIPS.items():
        if only and name not in only:
            continue
        render_gif(seg, f"{name}.gif")
