#!/usr/bin/env python3
"""Held-book preview: where an attachable ends up in first and third person.

Uses the reference Blockbench uses for Bedrock attachables (js/formats/bedrock/attachable_preview.js):
  third person  - the item follows the right arm, raised 15 degrees; bound point (0, 24, 0) is the hand
  first person  - item root at (-20, 21, 0) turned ZYX(-95, 45, 115); camera at (0, 19, -40) looking at
                  (0, 16, 0), 18 mm focal length, 16:9
All maths is in Blockbench's space (the Bedrock file with X mirrored), like the rest of the kit.

Faces are coloured by the book's own axes so its orientation can be read at a glance:
  red = front cover (-Z side of the model), blue = back cover (+Z), green = spine (+X), white = page
  edges (-X), grey = top / bottom.

  python3 tools/held_preview.py            -> tools/_preview/held_books.jpg
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kit.geo import rot_matrix  # noqa: E402
from kit.molang import Molang  # noqa: E402
import scene  # noqa: E402

RP = os.path.join(HERE, "..", "resource_packs", "grimoire_rp")
BOOKS = {"book_dw": "divine_word", "book_dn": "dream_nightmare", "book_ed": "elemental_dragon"}
SIDE = "--side" in sys.argv

# ---------------------------------------------------------------- Blockbench attachable reference
ARM_ANGLE = 15.0
W_FIRST_POS = np.array([-20.0, 21.0, 0.0])
W_FIRST_ROT = rot_matrix(-95.0, 45.0, 115.0)        # three.js Euler order ZYX == kit order (X, then Y, then Z)
CAM_FIRST = (np.array([0.0, 19.0, -40.0]), np.array([0.0, 16.0, 0.0]))
FOCAL_MM, FILM_GAUGE, ASPECT = 18.0, 35.0, 16 / 9
V_SLOPE = 0.5 * (FILM_GAUGE / ASPECT) / FOCAL_MM     # tan(vertical fov / 2), as three.js computes it
H_SLOPE = V_SLOPE * ASPECT


def w_third(p):
    r = rot_matrix(ARM_ANGLE, 0, 0)
    return np.array([5.0, 22.0, 0.0]) + (np.asarray(p) + np.array([1.0, -31.0, 1.0])) @ r.T


def w_first(p):
    return W_FIRST_POS + np.asarray(p) @ W_FIRST_ROT.T


def first_person_camera_basis():
    eye, tgt = CAM_FIRST
    f = (tgt - eye) / np.linalg.norm(tgt - eye)
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return eye, f, r, u


# ---------------------------------------------------------------- geometry + pose (Bedrock file -> bb space)
def _bb_vec(v):
    return np.array([-float(v[0]), float(v[1]), float(v[2])])


def _bb_rot(v):
    return (-float(v[0]), -float(v[1]), float(v[2]))


def load_book(g, first_person, open_amount):
    geo = json.load(open(os.path.join(RP, "models", "entity", f"{g}.geo.json")))["minecraft:geometry"][0]
    anims = json.load(open(os.path.join(RP, "animations", f"{g}.animation.json")))["animations"]
    att = json.load(open(os.path.join(RP, "attachables", f"{BOOKS[g]}.json")))["minecraft:attachable"]["description"]
    ev = Molang({"c.is_first_person": 1.0 if first_person else 0.0, "context.is_first_person": 1.0 if first_person else 0.0,
                  "v.open": open_amount, "variable.open": open_amount, "q.life_time": 0.0, "q.anim_time": 0.0,
                  "q.main_hand_item_use_duration": 0.0})
    pose = {}
    ctl_path = os.path.join(RP, "animation_controllers", f"{g}.animation_controllers.json")
    ctls = json.load(open(ctl_path))["animation_controllers"] if os.path.exists(ctl_path) else {}
    use = Molang({**ev.env, "q.main_hand_item_use_duration": 100.0 if open_amount > 0 else 0.0, "q.is_sneaking": 0.0,
                  "q.all_animations_finished": 1.0})

    def apply(a, at_end):
        for bone, chs in a.get("bones", {}).items():
            r, p, s = pose.get(bone, ((0, 0, 0), np.zeros(3), np.ones(3)))
            for ch, val in chs.items():
                if isinstance(val, dict):          # keyframes: steady state = last key, else the first
                    keys = sorted(val, key=float)
                    val = val[keys[-1] if at_end else keys[0]]
                    if isinstance(val, dict):
                        val = val.get("post", val.get("pre"))
                if not isinstance(val, list):
                    val = [val, val, val]
                x = [ev(c) for c in val]
                if ch == "rotation":
                    rr = _bb_rot(x)
                    r = tuple(r[i] + rr[i] for i in range(3))
                elif ch == "position":
                    p = p + _bb_vec(x)
                elif ch == "scale":
                    s = s * np.array(x)
            pose[bone] = (r, p, s)

    for entry in att["scripts"]["animate"]:
        name, cond = (entry, None) if isinstance(entry, str) else next(iter(entry.items()))
        if cond is not None and not ev(cond):
            continue
        full = att["animations"].get(name, "")
        if full in ctls:                           # controller: follow its transitions to the steady state
            c = ctls[full]
            st = c.get("initial_state", "default")
            for _ in range(3):
                nxt = None
                for t in c["states"][st].get("transitions", []):
                    (to, q), = t.items()
                    if use(q):
                        nxt = to
                        break
                if nxt is None:
                    break
                st = nxt
            for an in c["states"][st].get("animations", []) or []:
                an = an if isinstance(an, str) else next(iter(an))
                a = anims.get(att["animations"].get(an, ""))
                if a:
                    apply(a, True)
            continue
        a = anims.get(full)
        if a:
            apply(a, False)
    bones = {b["name"]: b for b in geo["bones"]}
    mats = {}

    def mat(name):
        if name in mats:
            return mats[name]
        b = bones[name]
        piv = _bb_vec(b.get("pivot", [0, 0, 0]))
        br = _bb_rot(b.get("rotation", [0, 0, 0]))
        r, p, s = pose.get(name, ((0, 0, 0), np.zeros(3), np.ones(3)))
        R = rot_matrix(*(br[i] + r[i] for i in range(3))) @ np.diag(s)
        m = np.eye(4)
        m[:3, :3] = R
        m[:3, 3] = piv + p - R @ piv
        if b.get("parent"):
            m = mat(b["parent"]) @ m
        mats[name] = m
        return m

    quads, cols = [], []
    pal = {"north": (0.85, 0.15, 0.15), "south": (0.2, 0.35, 0.95), "east": (0.15, 0.75, 0.25), "west": (0.95, 0.95, 0.9),
           "up": (0.55, 0.55, 0.55), "down": (0.4, 0.4, 0.4)}
    for name, b in bones.items():
        M = mat(name)
        for c in b.get("cubes", []):
            o, sz, inf = np.array(c["origin"], float), np.array(c["size"], float), float(c.get("inflate", 0.0))
            x0 = -(o[0] + sz[0]) - inf
            lo = np.array([x0, o[1] - inf, o[2] - inf])
            hi = lo + sz + 2 * inf
            cm = np.eye(4)
            if c.get("rotation"):
                cp = _bb_vec(c.get("pivot", [0, 0, 0]))
                R = rot_matrix(*_bb_rot(c["rotation"]))
                cm[:3, :3] = R
                cm[:3, 3] = cp - R @ cp
            x0, y0, z0 = lo
            x1, y1, z1 = hi
            faces = {"north": [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
                     "south": [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
                     "east": [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
                     "west": [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
                     "up": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
                     "down": [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]}
            T = M @ cm
            for f, pts in faces.items():
                P = np.array([list(q) + [1.0] for q in pts]) @ T.T
                quads.append(P[:, :3])
                cols.append(pal[f])
    return np.array(quads), np.array(cols, dtype=np.float32)


def player_quads():
    """The Blockbench attachable reference player (wide arms), right arm raised 15 degrees."""
    parts = [((-4, 24, -4), (8, 8, 8), None), ((-4, 12, -2), (8, 12, 4), None),
             ((4, 12, -2), (4, 12, 4), ((5, 22, 0), (ARM_ANGLE, 0, 0))), ((-8, 12, -2), (4, 12, 4), ((-5, 22, 0), (1, 0, -3))),
             ((-0.1, 0, -2), (4, 12, 4), None), ((-3.9, 0, -2), (4, 12, 4), None)]
    quads, cols = [], []
    for (o, s, rot) in parts:
        lo = np.array(o, float)
        hi = lo + np.array(s, float)
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        fs = [[(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)], [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
              [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)], [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
              [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)]]
        for k, pts in enumerate(fs):
            P = np.array(pts, float)
            if rot:
                c, e = np.array(rot[0], float), rot[1]
                P = c + (P - c) @ rot_matrix(*e).T
            quads.append(P)
            cols.append((0.32, 0.55, 0.62) if k != 0 else (0.75, 0.6, 0.45))   # the face side (-Z) in skin colour
    return np.array(quads), np.array(cols, dtype=np.float32)


def render_view(g, first_person, open_amount, size=(640, 360)):
    q, c = load_book(g, first_person, open_amount)
    flat = q.reshape(-1, 3)
    if first_person:
        w = w_first(flat).reshape(-1, 4, 3)
        eye, tgt = CAM_FIRST
        cam = scene.Cam(eye, tgt, math.degrees(2 * math.atan(H_SLOPE)), size)
        fr = scene.Frame(cam)
        fr.add_quads(w, flat=c)
        img, _ = fr.render(sky=(0.55, 0.62, 0.72), plane=False)
        d = ImageDraw.Draw(img)
        W, H = size
        d.line((W / 2 - 8, H / 2, W / 2 + 8, H / 2), fill=(255, 255, 255))
        d.line((W / 2, H / 2 - 8, W / 2, H / 2 + 8), fill=(255, 255, 255))
        hand = w_first(np.array([[0.0, 24.0, 0.0]]))
        hx, hy, hz = cam.project(hand)
        d.ellipse((hx[0] - 4, hy[0] - 4, hx[0] + 4, hy[0] + 4), outline=(255, 255, 0))
        cx, cy, _ = cam.project(w.reshape(-1, 3).mean(axis=0, keepdims=True))
        d.text((6, 4), f"{g} first person  open={open_amount:g}  book centre NDC ({(cx[0] / W * 2 - 1):+.2f}, {(1 - cy[0] / H * 2):+.2f})",
               fill=(255, 255, 255))
    else:
        w = w_third(flat).reshape(-1, 4, 3)
        pq, pc = player_quads()
        eye = np.array([-44.0, 22.0, -58.0]) if not SIDE else np.array([70.0, 18.0, -6.0])
        cam = scene.Cam(eye, np.array([0.0, 15.0, 0.0]), 34, size)
        fr = scene.Frame(cam)
        fr.add_quads(pq, flat=pc)
        fr.add_quads(w, flat=c)
        img, _ = fr.render(sky=(0.55, 0.62, 0.72), plane=False)
        d = ImageDraw.Draw(img)
        d.text((6, 4), f"{g} third person  open={open_amount:g}  (player faces -Z, right arm on +X)", fill=(255, 255, 255))
    return img


def main():
    rows = []
    for g in BOOKS:
        rows.append([render_view(g, True, 0.0), render_view(g, True, 1.0), render_view(g, False, 0.0), render_view(g, False, 1.0)])
    W, H = rows[0][0].size
    sheet = Image.new("RGB", (W * 4, H * len(rows)))
    for j, row in enumerate(rows):
        for i, im in enumerate(row):
            sheet.paste(im, (i * W, j * H))
    os.makedirs(os.path.join(HERE, "_preview"), exist_ok=True)
    out = os.path.join(HERE, "_preview", "held_books_side.jpg" if SIDE else "held_books.jpg")
    sheet.save(out, quality=88)
    print(out)


if __name__ == "__main__":
    main()
