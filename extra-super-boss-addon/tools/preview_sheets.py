#!/usr/bin/env python3
"""
Pose sheets and animated GIFs rendered from the real pack files.

    python3 tools/preview_sheets.py            -> docs/preview/poses.png, docs/preview/anim/*.gif
    python3 tools/preview_sheets.py --sheet    -> only the pose sheet (fast)

Layers are combined the way the client entity does: idle + walk + look + wings layer + action.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kinematics as K  # noqa: E402
import render_preview as R  # noqa: E402
import spec  # noqa: E402

P = "animation.esb.da_vinci."
ANIM_DIR = os.path.join(R.OUT, "anim")


def layered_pose(action=None, t=0.0, phase=1, wings=None, speed=0.0, dist=0.0, life=None):
    env = {"q.modified_move_speed": speed, "q.modified_distance_moved": dist, "q.target_x_rotation": 0,
           "q.target_y_rotation": 0, "q.life_time": life if life is not None else t,
           "q.property('esb:phase')": phase, "q.delta_time": 0.05}
    names, times = [P + "idle", P + "walk"], [env["q.life_time"], 0.0]
    if wings is None:
        wings = "wings_hidden" if phase == 1 else "wings_folded"
    names.append(P + wings)
    times.append(t if wings in ("wings_unfold", "wings_swept") else env["q.life_time"])
    if action:
        names.append(P + action)
        times.append(t)
    anims = [R.ANIMS[n] for n in names]
    return K.sample_pose(anims, [1.0] * len(anims), times, env)


SHEET = [
    ("idle", None, 0.0, 1, None),
    ("intro: kneel", "intro", 0.6, 1, None),
    ("intro: signature pose", "intro", 3.0, 1, None),
    ("slash: wind-up", "slash", 0.27, 1, None),
    ("slash: strike", "slash", 0.45, 1, None),
    ("gear volley: aim", "gear_volley", 1.3, 1, None),
    ("quake: raise", "quake", 0.62, 1, None),
    ("quake: impact", "quake", 0.95, 1, None),
    ("vitruvian", "vitruvian", 1.3, 1, None),
    ("vitruvian: slam", "vitruvian", 2.8, 1, None),
    ("transform: clutch", "transform", 0.9, 2, "wings_unfold"),
    ("transform: burst", "transform", 2.25, 2, "wings_unfold"),
    ("phase 2 idle", None, 0.0, 2, None),
    ("dive: hover", "dive_hover", 0.3, 2, "wings_flap"),
    ("dive: strike", "dive_strike", 0.12, 2, "wings_swept"),
    ("flourish", "flourish", 0.7, 1, None),
    ("death: kneel", "death", 1.6, 1, None),
    ("death: slump", "death", 4.2, 1, None),
]


def sheet(views=((30, 8),), cols=6, size=(300, 380), scale=6.2, name="poses.png"):
    tiles = []
    for label, action, t, phase, wings in SHEET:
        pose = layered_pose(action, t, phase, wings)
        for yaw, pitch in views:
            cam = K.Camera((0, 19, 0), yaw, pitch, scale=scale, size=size)
            img = R.draw(cam, pose)
            ImageDraw.Draw(img).text((8, 6), label, fill=(245, 225, 190), font=R.font(15))
            tiles.append(img)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * size[0], rows * size[1]))
    for i, tl in enumerate(tiles):
        out.paste(tl, ((i % cols) * size[0], (i // cols) * size[1]))
    p = os.path.join(R.OUT, name)
    out.save(p)
    print("wrote", p)


GIFS = [
    # name, action, phase, wings layer, duration, walk speed
    ("idle", None, 1, None, 3.2, 0.0),
    ("walk", None, 1, None, 1.6, 1.0),
    ("intro", "intro", 1, None, spec.ACTIONS["intro"]["length"], 0.0),
    ("slash", "slash", 1, None, spec.SLASH["length"], 0.0),
    ("gear_volley", "gear_volley", 1, None, spec.ACTIONS["gear_volley"]["length"], 0.0),
    ("quake", "quake", 1, None, spec.ACTIONS["quake"]["length"], 0.0),
    ("vitruvian", "vitruvian", 1, None, spec.ACTIONS["vitruvian"]["length"], 0.0),
    ("transform", "transform", 2, "wings_unfold", spec.ACTIONS["transform"]["length"], 0.0),
    ("dive_rise", "dive_rise", 2, "wings_flap", spec.ACTIONS["dive_rise"]["length"], 0.0),
    ("dive_hover", "dive_hover", 2, "wings_flap", 1.0, 0.0),
    ("dive_strike", "dive_strike", 2, "wings_swept", spec.ACTIONS["dive_strike"]["length"], 0.0),
    ("flourish", "flourish", 1, None, spec.ACTIONS["flourish"]["length"], 0.0),
    ("death", "death", 1, None, spec.ACTIONS["death"]["length"] + 0.4, 0.0),
    ("phase2_walk", None, 2, None, 1.6, 1.0),
]


def flat_bg(size):
    return np.broadcast_to(np.array([0.16, 0.10, 0.09]), (size[1], size[0], 3)).copy()


def gifs(only=None, fps=12, size=(256, 320), scale=5.1):
    os.makedirs(ANIM_DIR, exist_ok=True)
    for name, action, phase, wings, dur, speed in GIFS:
        if only and name not in only:
            continue
        frames = []
        n = max(2, int(round(dur * fps)))
        for i in range(n):
            t = i / fps
            dist = t * 4.0 * speed * 1.4  # ~ modified distance at walking speed
            pose = layered_pose(action, t, phase, wings, speed=speed, dist=dist, life=t + 0.5)
            cam = K.Camera((0, 21, 0), 32, 10, scale=scale, size=size)
            img = R.draw(cam, pose, bg=flat_bg(size), ground=False)
            ImageDraw.Draw(img).text((8, 6), name, fill=(245, 225, 190), font=R.font(14))
            frames.append(img)
        pal = frames[len(frames) // 2].convert("P", palette=Image.ADAPTIVE, colors=128)
        frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
        p = os.path.join(ANIM_DIR, f"{name}.gif")
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, disposal=2)
        print("wrote", p)


# ------------------------------------------------------------------------------ Boss 2: Edison
PE = "animation.esb.edison."
E_GEO = R.load_geo("edison")
E_TEX = R.load_tex("edison")
E_TEX2 = R.load_tex("edison_charged")
D_GEO = R.load_geo("dynamo")
D_TEX = R.load_tex("dynamo")
D_TEX2 = R.load_tex("dynamo_charged")
C_GEO = R.load_geo("electric_chair")
C_TEX = R.load_tex("electric_chair")
E_SCALE = 1.45


def edison_pose(action=None, t=0.0, phase=1, speed=0.0, dist=0.0, life=None):
    env = {"q.modified_move_speed": speed, "q.modified_distance_moved": dist, "q.target_x_rotation": 0, "q.target_y_rotation": 0,
           "q.life_time": life if life is not None else t, "q.property('esb:phase')": phase, "q.delta_time": 0.05}
    names, times = [PE + "idle", PE + "walk"], [env["q.life_time"], 0.0]
    if action:
        names.append(PE + action)
        times.append(t)
    return K.sample_pose([R.ANIMS[n] for n in names], [1.0] * len(names), times, env)


def scaled(pose, s=E_SCALE, offset=(0, 0, 0)):
    """Apply the client render scale (and a world offset) to a pose, for drawing next to other models."""
    p = {k: {kk: np.array(vv, dtype=float).copy() for kk, vv in v.items()} for k, v in (pose or {}).items()}
    root = p.setdefault("root", {"rotation": np.zeros(3), "position": np.zeros(3), "scale": np.ones(3)})
    root["position"] = root["position"] * s + np.array(offset, dtype=float)
    root["scale"] = root["scale"] * s
    return p


E_SHEET = [
    ("intro: on the Dynamo", "intro", 0.6, 1), ("intro: hop", "intro", 3.0, 1), ("idle", None, 0.0, 1),
    ("shank: wind", "shank", 0.14, 1), ("shank: thrust", "shank", 0.3, 1), ("bulb toss", "bulb_toss", 0.8, 1),
    ("vanish: crush", "vanish", 0.35, 1), ("backstab", "backstab", 0.25, 1), ("overload: pull", "overload", 1.0, 1),
    ("overload: surge", "overload", 1.6, 1), ("chair: snap", "chair", 0.6, 1), ("transform", "transform", 2.2, 2),
    ("phase 2 idle", None, 0.0, 2), ("stunned", "stunned", 1.5, 1), ("flourish", "flourish", 0.9, 1), ("death", "death", 4.0, 1),
]


def edison_sheet(cols=8, size=(260, 340), name="edison_poses.png"):
    tiles = []
    for label, action, t, phase in E_SHEET:
        pose = edison_pose(action, t, phase)
        tex = E_TEX2 if phase == 2 else E_TEX
        if action == "intro" and t < 2.9:
            cam = K.Camera((0, 30, 0), 28, 8, scale=size[1] / 82, size=size)
            img = R.draw(cam, scaled(pose, offset=(0, 33.5, 0)), geo=E_GEO, tex=tex, extra=[(D_GEO, D_TEX, None, False)])
        else:
            cam = K.Camera((0, 27, 0), 28, 8, scale=size[1] / 78, size=size)
            img = R.draw(cam, scaled(pose), geo=E_GEO, tex=tex)
        ImageDraw.Draw(img).text((8, 6), label, fill=(245, 225, 190), font=R.font(14))
        tiles.append(img)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * size[0], rows * size[1]))
    for i, tl in enumerate(tiles):
        out.paste(tl, ((i % cols) * size[0], (i // cols) * size[1]))
    p = os.path.join(R.OUT, name)
    out.save(p)
    print("wrote", p)


E_GIFS = [
    ("edison_intro", "intro", 1), ("edison_shank", "shank", 1), ("edison_bulb_toss", "bulb_toss", 1),
    ("edison_vanish_backstab", "vanish+backstab", 1), ("edison_overload", "overload", 1), ("edison_chair", "chair", 1),
    ("edison_transform", "transform", 2), ("edison_stunned", "stunned", 1), ("edison_flourish", "flourish", 1),
    ("edison_death", "death", 1), ("edison_walk", None, 1), ("edison_phase2_walk", None, 2),
]


def edison_gifs(only=None, fps=12, size=(256, 320)):
    os.makedirs(ANIM_DIR, exist_ok=True)
    acts = {k: v["length"] for k, v in spec.EDISON_ACTIONS.items()}
    acts["shank"] = spec.SHANK["length"]
    hop, land = spec.EDISON_ACTIONS["intro"]["moments"]["hop"], spec.EDISON_ACTIONS["intro"]["moments"]["land"]
    for name, action, phase in E_GIFS:
        if only and name not in only:
            continue
        seq = [(a, acts[a]) for a in action.split("+")] if action else [(None, 1.6)]
        frames = []
        for act_name, dur in seq:
            for i in range(max(2, int(round(dur * fps)))):
                t = i / fps
                speed = 1.0 if act_name is None else 0.0
                pose = edison_pose(act_name, t, phase, speed=speed, dist=t * 4.0 * 1.4, life=t + 0.3)
                tex = E_TEX2 if phase == 2 else E_TEX
                extra, off, tgt, sc = [], (0, 0, 0), (0, 24, 0), size[1] / 64
                if act_name == "intro":
                    k = min(1.0, max(0.0, (t - hop) / (land - hop)))
                    off = (0, 33.5 * (1 - k) + np.sin(k * np.pi) * 12, -41.6 * k)
                    extra = [(D_GEO, D_TEX, None, False)]
                    tgt, sc = (0, 28, -14), size[1] / 92
                cam = K.Camera(tgt, 30, 10, scale=sc, size=size)
                img = R.draw(cam, scaled(pose, offset=off), bg=flat_bg(size), ground=False, geo=E_GEO, tex=tex, extra=extra)
                ImageDraw.Draw(img).text((8, 6), name.replace("edison_", ""), fill=(245, 225, 190), font=R.font(14))
                frames.append(img)
        pal = frames[len(frames) // 2].convert("P", palette=Image.ADAPTIVE, colors=128)
        frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
        p = os.path.join(ANIM_DIR, f"{name}.gif")
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, disposal=2)
        print("wrote", p)


def props_sheet(name="edison_props.png", size=(420, 460)):
    """The Dynamo (DC and AC), the electric chair (armed / locked) and the thrown bulb."""
    tiles = []
    for label, geo, tex, sc, tgt in (("The Dynamo", D_GEO, D_TEX, 9, (0, 17, 0)), ("The Dynamo (phase 2, AC)", D_GEO, D_TEX2, 9, (0, 17, 0)),
                                     ("Electric Chair", C_GEO, C_TEX, 10, (0, 17, 0))):
        cam = K.Camera(tgt, 28, 12, scale=sc, size=size)
        img = R.draw(cam, None, geo=geo, tex=tex)
        ImageDraw.Draw(img).text((10, 8), label, fill=(245, 225, 190), font=R.font(16))
        tiles.append(img)
    out = Image.new("RGB", (size[0] * len(tiles), size[1]))
    for i, tl in enumerate(tiles):
        out.paste(tl, (i * size[0], 0))
    p = os.path.join(R.OUT, name)
    out.save(p)
    print("wrote", p)


# ------------------------------------------------------------------------------ ULTIMATES
HORSE_GEO = R.load_geo("gran_cavallo")
HORSE_TEX = R.load_tex("gran_cavallo")
PHONO_GEO = R.load_geo("phonograph")
PHONO_TEX = R.load_tex("phonograph")
RING_GEO = R.load_geo("sound_ring")
RING_TEX = R.load_tex("sound_ring")
DV_SCALE = 1.6
HORSE_SCALE = 1.75
PHONO_SCALE = 2.2
_PROP_ANIMS = K.load_json(os.path.join(R.RP, "animations", "ultimate_props.animation.json"))["animations"]


def prop_pose(anim, t, scale, offset=(0, 0, 0), yaw=0.0, life=None):
    p = K.sample_pose([_PROP_ANIMS[anim]], [1.0], [t], {"q.life_time": life if life is not None else t, "q.anim_time": t})
    root = p.setdefault("root", {"rotation": np.zeros(3), "position": np.zeros(3), "scale": np.ones(3)})
    root["position"] = root["position"] * scale + np.array(offset, dtype=float)
    root["scale"] = root["scale"] * scale
    root["rotation"] = root["rotation"] + np.array([0, yaw, 0])
    return p


def ultimates_sheet(name="ultimates.png", size=(760, 640)):
    """Showcase: Il Gran Cavallo rearing over Leonardo; Edison cranking the tinfoil phonograph inside a sound ring."""
    import json as _j
    speed = _j.load(open(os.path.join(R.ROOT, "balance.json")))["edison"]["ultimate"]["ring_speed"]
    # Leonardo presents the Great Horse as it rears (the horse is 5 blocks in front of him, facing the camera side)
    lp = scaled(layered_pose("ultimate", 2.0, 2, None, life=1.0), DV_SCALE, (0, 0, 0))
    hp = prop_pose("animation.esb.gran_cavallo.rise", 2.0, HORSE_SCALE, (0, 0, -80), yaw=0)
    cam = K.Camera((0, 50, -42), -62, 6, scale=size[1] / 185, size=size)
    a = R.draw(cam, lp, ground=True, extra=[(HORSE_GEO, HORSE_TEX, hp, False)])
    ImageDraw.Draw(a).text((14, 10), "ULTIMATE - IL GRAN CAVALLO", fill=(255, 215, 130), font=R.font(24))
    ImageDraw.Draw(a).text((14, 40), "Leonardo's clay horse of Milan (1482-1499)", fill=(240, 220, 190), font=R.font(16))
    # Edison at the crank of the phonograph, a sound wave rolling out from the horn
    ph_yaw = 0.0
    pp = prop_pose("animation.esb.phonograph.play", 0.3, PHONO_SCALE, (0, 0, -56), yaw=ph_yaw, life=0.3)
    ep = scaled(edison_pose("ultimate", 5.0, 2, life=1.0), E_SCALE, (46, 0, -56))
    ep["root"]["rotation"] = ep["root"]["rotation"] + np.array([0, -90, 0])
    rp = prop_pose("animation.esb.sound_ring.grow", 0.9, 1.0, (0, 0, -122), life=0.9)
    rp["root"]["scale"] = np.array([0.9 * speed, 1.0, 0.9 * speed])
    cam = K.Camera((10, 40, -70), 210, 14, scale=size[1] / 200, size=size)
    b = R.draw(cam, ep, ground=True, geo=E_GEO, tex=E_TEX2,
               extra=[(PHONO_GEO, PHONO_TEX, pp, False), (RING_GEO, RING_TEX, rp, True)])
    ImageDraw.Draw(b).text((14, 10), "ULTIMATE - MARY HAD A LITTLE LAMB", fill=(170, 225, 255), font=R.font(24))
    ImageDraw.Draw(b).text((14, 40), "the first words ever recorded (1877) - jump the sound waves", fill=(220, 235, 245), font=R.font(16))
    out = Image.new("RGB", (size[0] * 2, size[1]))
    out.paste(a, (0, 0))
    out.paste(b, (size[0], 0))
    pth = os.path.join(R.OUT, name)
    out.save(pth)
    print("wrote", pth)


def ultimate_gifs(fps=10, size=(360, 300)):
    """The showpieces in motion: the horse rising, pawing, galloping and crumbling; the phonograph playing."""
    os.makedirs(ANIM_DIR, exist_ok=True)
    H = "animation.esb.gran_cavallo."
    seq = [("rise", 2.4), ("paw", 1.2), ("gallop", 1.5), ("crumble", 2.4)]
    frames = []
    for anim, dur in seq:
        for i in range(int(dur * fps)):
            t = i / fps
            pose = prop_pose(H + anim, t, 1.0, life=t)
            img = R.draw(K.Camera((0, 26, -6), 62, 8, scale=size[1] / 76, size=size), pose, bg=flat_bg(size), ground=False,
                         geo=HORSE_GEO, tex=HORSE_TEX)
            ImageDraw.Draw(img).text((8, 6), f"Il Gran Cavallo - {anim}", fill=(245, 225, 190), font=R.font(13))
            frames.append(img)
    _save_gif(frames, "ultimate_gran_cavallo.gif", fps)
    frames = []
    P = "animation.esb.phonograph."
    for anim, dur in (("assemble", 1.2), ("play", 2.2), ("blast", 1.0), ("fold", 1.0)):
        for i in range(int(dur * fps)):
            t = i / fps
            pose = prop_pose(P + anim, t, 1.0, life=t)
            img = R.draw(K.Camera((0, 15, -12), 140, 12, scale=size[1] / 50, size=size), pose, bg=flat_bg(size), ground=False,
                         geo=PHONO_GEO, tex=PHONO_TEX)
            ImageDraw.Draw(img).text((8, 6), f"tinfoil phonograph - {anim}", fill=(245, 225, 190), font=R.font(13))
            frames.append(img)
    _save_gif(frames, "ultimate_phonograph.gif", fps)


def _save_gif(frames, name, fps):
    pal = frames[len(frames) // 2].convert("P", palette=Image.ADAPTIVE, colors=128)
    frames = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    pth = os.path.join(ANIM_DIR, name)
    frames[0].save(pth, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, disposal=2)
    print("wrote", pth)


def run_all():
    sheet()
    gifs()
    edison_sheet()
    props_sheet()
    edison_gifs()
    ultimates_sheet()
    ultimate_gifs()


if __name__ == "__main__":
    if "--sheet" in sys.argv:
        sheet()
        edison_sheet()
        props_sheet()
        ultimates_sheet()
    elif "--gif" in sys.argv:
        gifs([a for a in sys.argv[2:]] or None)
    else:
        run_all()
