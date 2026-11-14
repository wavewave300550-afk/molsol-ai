"""Post-step for the three held books (runs after books_dn / books_dw / books_ed).

1. HAND FRAME.  The book modules place the book with a "place" bone whose numbers are written in the
   player model's own space (hand item bone at (6, 15, 1) in bb space, axes right / up / back).  A bone
   bound with q.item_slot_to_bone_name() does not live in that space.  The frame used here is the one
   Blockbench uses to preview Bedrock attachables (js/formats/bedrock/attachable_preview.js), which is
   what creators check held items against:
     third person : bound point (0, 24, 0) is the hand and the item follows the arm, no extra turn
     first person : item root at (-20, 21, 0) turned ZYX(-95, 45, 115), seen by a camera at (0, 19, -40)
                    looking at (0, 16, 0) with an 18 mm lens, 16:9
   (1.0.2 used a 90-degree turn in third person and the vanilla shield's angles in first person; in
   that reference the book lay flat under the hand and floated next to the crosshair.)
   A "<book>_frame" bone between the bound root and "place" converts between the two:
     third person : a pure shift, so the book modules' third-person numbers are offsets from the hand
                    along the arm's right / up / back
     first person : computed so that the closed book's centre lands at FP_SCREEN (screen position,
                    -1..1 like the crosshair at 0, 0) at FP_DEPTH units in front of the camera, with
                    the book modules' first-person axes = screen right / up / toward the camera
   tools/held_preview.py draws the result.
2. MATERIAL.  The held book uses entity_alphatest, like every vanilla held item, with the plain
   texture Model.save() writes as <name>_held.png.
3. BONE NAMES.  (below)
4. OPEN BY EXPRESSION.  On an iPhone (26.62) the Dream & Nightmare and Elemental Dragon books did not
   open: their open animation was keyframed and driven through anim_time_update ("v.open * length"),
   which the held item ignored, while the Divine Word book (rotations written as expressions of
   v.open) opened.  Every anim_time_update animation of a held book is baked here into expressions
   of v.open: each keyframed channel is sampled (catmull-rom like the keys), simplified, and written
   as a piecewise-linear expression; the animation becomes a plain loop.
5. BUILT-IN CIRCLE.  The selection / charge circle (tools/assets/_book_aura.py) is re-centred on the
   book AS POSED (kit.heldpose evaluates the attachable's own animations): centred on the closed book
   just behind its back cover at rest, gliding to sit under the open book while Use is held, sized
   from the posed book, and smaller in third person.

An attachable's bones are matched BY NAME against the player's skeleton, so a book bone called
"root" or "body" would be glued to that player bone instead of following the hand.  This step
renames any colliding bone in the generated geometry, animations and render controller.
"""
import json
import math
import os

import numpy as np

from kit.geo import rot_matrix
from kit.heldpose import corners, cube_box, pose_bones
from kit.molang import Molang
from kit.pack import RP

PLAYER = {"root", "waist", "body", "head", "hat", "cape", "jacket", "helmet", "leftarm", "rightarm", "leftleg",
          "rightleg", "leftitem", "rightitem", "leftsleeve", "rightsleeve", "leftpants", "rightpants"}


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


HAND = [-6.0, 15.0, 1.0]            # player rightItem pivot (geometry space: X is the holder's left)
HAND_BOUND = [0.0, 24.0, 0.0]       # where that point sits in the bound bone's space
ITEMS = {"book_dw": "divine_word", "book_dn": "dream_nightmare", "book_ed": "elemental_dragon"}

# ---- first-person placement of the CLOSED book (the open / charging motion is added by the book modules)
FP_SCREEN = (0.36, -0.30)           # right of and below the crosshair, clear of it
FP_DEPTH = 22.0                     # units in front of the reference camera (the hand is at about 24)

# Blockbench attachable reference (bb space = the Bedrock file with X mirrored)
_W_FIRST_POS = np.array([-20.0, 21.0, 0.0])
_W_FIRST_ROT = rot_matrix(-95.0, 45.0, 115.0)
_EYE, _TARGET = np.array([0.0, 19.0, -40.0]), np.array([0.0, 16.0, 0.0])
_V_SLOPE = 0.5 * (35.0 / (16 / 9)) / 18.0
_H_SLOPE = _V_SLOPE * 16 / 9


def _euler(R):
    """kit / Blockbench rotation (X, then Y, then Z) of a rotation matrix, degrees."""
    b = -math.asin(max(-1.0, min(1.0, R[2, 0])))
    a = math.atan2(R[2, 1], R[2, 2])
    c = math.atan2(R[1, 0], R[0, 0])
    return tuple(math.degrees(v) for v in (a, b, c))


def _place_position(g, att, an, first_person):
    """Closed-book position of the "place" bone (bb space) as the attachable's animations set it."""
    ev = Molang({"c.is_first_person": 1.0 if first_person else 0.0, "v.open": 0.0})
    pos = np.zeros(3)
    for entry in att["scripts"]["animate"]:
        name, cond = (entry, None) if isinstance(entry, str) else next(iter(entry.items()))
        if cond is not None and not ev(cond):
            continue
        a = an["animations"].get(att["animations"].get(name, ""), {})
        p = a.get("bones", {}).get("place", {}).get("position")
        if p is not None:
            v = [ev(x) for x in (p if isinstance(p, list) else [p, p, p])]
            pos += np.array([-v[0], v[1], v[2]])
    return pos


def _frames(g, att, an):
    """(first-person rotation, position), (third-person rotation, position) for the frame bone, Bedrock values."""
    hand_bb = np.array([-HAND[0], HAND[1], HAND[2]])
    bound_bb = np.array([-HAND_BOUND[0], HAND_BOUND[1], HAND_BOUND[2]])
    # third person: shift the authored hand onto the bound hand
    tp_rot, tp_pos = (0.0, 0.0, 0.0), bound_bb - hand_bb
    # first person: screen-aligned axes, closed book centre at FP_SCREEN / FP_DEPTH
    f = (_TARGET - _EYE) / np.linalg.norm(_TARGET - _EYE)
    r = np.cross(f, [0.0, 1.0, 0.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    S = np.column_stack([r, u, -f])
    centre = _EYE + FP_DEPTH * (f + FP_SCREEN[0] * _H_SLOPE * r + FP_SCREEN[1] * _V_SLOPE * u)
    R = _W_FIRST_ROT.T @ S
    P = _place_position(g, att, an, True)
    t = _W_FIRST_ROT.T @ (centre - _W_FIRST_POS) - hand_bb - R @ (P - hand_bb)
    fp_rot = _euler(R)

    def bedrock(rot, pos):
        return ([round(-rot[0], 3), round(-rot[1], 3), round(rot[2], 3)],
                [round(-float(pos[0]), 3), round(float(pos[1]), 3), round(float(pos[2]), 3)])
    return bedrock(fp_rot, t), bedrock(tp_rot, tp_pos)


def _hand_frame(g, geo, bones):
    frame = f"{g}_frame"
    if not any(b["name"] == frame for b in bones):
        bound = next(b for b in bones if "binding" in b)
        i = bones.index(bound)
        bones.insert(i + 1, {"name": frame, "parent": bound["name"], "pivot": list(HAND)})
        for b in bones:
            if b.get("parent") == bound["name"] and b["name"] != frame:
                b["parent"] = frame
    anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
    an = json.load(open(anim_p, encoding="utf-8"))
    att_p = os.path.join(RP, "attachables", f"{ITEMS[g]}.json")
    att = json.load(open(att_p, encoding="utf-8"))
    d = att["minecraft:attachable"]["description"]
    (fr, fp), (tr, tp) = _frames(g, d, an)
    an["animations"][f"animation.grimoire.{g}.hand_frame"] = {"loop": True, "bones": {frame: {
        "rotation": [f"c.is_first_person ? {fr[i]} : {tr[i]}" for i in range(3)],
        "position": [f"c.is_first_person ? {fp[i]} : {tp[i]}" for i in range(3)]}}}
    _dump(anim_p, an)
    # MATERIAL.  Every vanilla held item (bow, crossbow, shield, trident) uses entity_alphatest; the glowing
    # entity_emissive_alpha drew the spell entities but left the held book invisible in first person on
    # an iPhone (26.62).  The held book uses the vanilla material and the plain texture Model.save()
    # writes for it; blend parts keep entity_alphablend.
    d["materials"]["default"] = "entity_alphatest"
    d["textures"]["default"] = d["textures"]["default"].removesuffix("_held") + "_held"
    d["animations"]["hand_frame"] = f"animation.grimoire.{g}.hand_frame"
    if "hand_frame" not in d["scripts"]["animate"]:
        d["scripts"]["animate"].insert(0, "hand_frame")
    _dump(att_p, att)
    print(f"    {g}: hand frame  first person rot {fr} pos {fp}  third person rot {tr} pos {tp}")


# ---- open by expression (see 4. above)
BAKE_STEP = 0.02                    # sampling step in v.open
BAKE_TOL = (0.6, 0.06, 0.012)       # simplification tolerance: rotation (deg), position (px), scale


def _keys(val):
    """[(time, [x, y, z], catmullrom)] of a keyframed channel."""
    out = []
    for k, v in val.items():
        cat = isinstance(v, dict) and v.get("lerp_mode") == "catmullrom"
        if isinstance(v, dict):
            v = v.get("post", v.get("pre"))
        v = v if isinstance(v, list) else [v, v, v]
        out.append((float(k), [float(x) for x in v], cat))
    return sorted(out, key=lambda e: e[0])


def _sample(keys, t):
    """Channel value at time t: linear between keys, catmull-rom where a key asks for it."""
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return keys[0][1]
    if t >= ts[-1]:
        return keys[-1][1]
    j = max(i for i in range(len(ts)) if ts[i] <= t)
    p1, p2 = np.array(keys[j][1]), np.array(keys[j + 1][1])
    f = (t - ts[j]) / (ts[j + 1] - ts[j])
    if not (keys[j][2] or keys[j + 1][2]):
        return list(p1 + (p2 - p1) * f)
    p0 = np.array(keys[j - 1][1]) if j > 0 else p1
    p3 = np.array(keys[j + 2][1]) if j + 2 < len(keys) else p2
    v = 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
    return list(v)


def _simplify(us, vs, tol):
    """Indices of a piecewise-linear subset of (us, vs) within tol (Douglas-Peucker)."""
    keep = {0, len(us) - 1}
    stack = [(0, len(us) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = vs[i], vs[j]
        err = [abs(vs[k] - (a + (b - a) * (us[k] - us[i]) / (us[j] - us[i]))) for k in range(i + 1, j)]
        k = int(np.argmax(err)) + i + 1
        if err[k - i - 1] > tol:
            keep.add(k)
            stack += [(i, k), (k, j)]
    return sorted(keep)


def _piecewise(us, vs, var="v.open"):
    """Molang for the piecewise-linear curve through (us, vs) over var in 0..1."""
    vs = [round(v, 3) + 0.0 for v in vs]
    if max(vs) - min(vs) < 1e-6:
        return vs[0]

    def num(x):                                   # negative constants in brackets, like the DW book's
        return f"({x})" if x < 0 else f"{x}"
    expr = num(vs[-1])
    for i in range(len(us) - 2, -1, -1):
        u0, u1, a, b = round(us[i], 4), round(us[i + 1], 4), vs[i], vs[i + 1]
        k = round((b - a) / (u1 - u0), 4)
        seg = num(a) if abs(b - a) < 1e-6 else f"({num(a)} {'-' if k < 0 else '+'} {abs(k)} * ({var} - {u0}))"
        expr = f"({var} < {u1} ? {seg} : {expr})"
    return expr


def _bake_open(g):
    anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
    an = json.load(open(anim_p, encoding="utf-8"))
    baked = []
    for name, a in an["animations"].items():
        atu = a.get("anim_time_update")
        if not atu:
            continue
        length = float(a.get("animation_length", 0.0))
        assert atu.replace(" ", "") == f"v.open*{length:g}".replace(" ", ""), (name, atu)
        us = [min(1.0, i * BAKE_STEP) for i in range(int(round(1 / BAKE_STEP)) + 1)]
        n_terms = 0
        for bone, chs in a.get("bones", {}).items():
            for ch, val in list(chs.items()):
                if not isinstance(val, dict):
                    continue                      # already a constant / expression: unchanged
                keys = _keys(val)
                tol = BAKE_TOL[{"rotation": 0, "position": 1, "scale": 2}[ch]]
                samples = [_sample(keys, u * length) for u in us]
                comps = []
                for c in range(3):
                    vs = [s_[c] for s_ in samples]
                    idx = _simplify(us, vs, tol)
                    comps.append(_piecewise([us[i] for i in idx], [vs[i] for i in idx]))
                    n_terms += len(idx)
                chs[ch] = comps
        for k in ("anim_time_update", "animation_length"):
            a.pop(k, None)
        a["loop"] = True
        baked.append(f"{name.split('.')[-1]} ({n_terms} points)")
    if baked:
        _dump(anim_p, an)
        print(f"    {g}: baked to v.open expressions: {', '.join(baked)}")


# ---- built-in circle (see _book_aura.py): diameter relative to the posed book's larger side
AURA_CLOSED = 1.3                   # crouch flare behind the closed book
AURA_OPEN = 1.4                     # under the open book while charging (reaches past the open pages)
AURA_GAP = 0.6                      # units behind the back cover / under the open pages
AURA_THIRD_PERSON = 0.6             # smaller when seen from outside (other players, F5 view)
AURA_BONES = ("aura", "aura_ring", "aura_ring2")
AURA_SKIP = {"book_dw": ("dr", "rb"), "book_ed": ("ribbon",)}     # drifting motes, hanging ribbons


def _posed_box(g, parent, open_amount):
    """Box of the visible book body, in the circle parent's bind space (Bedrock file coordinates).
    Drifting motes and hanging ribbons (AURA_SKIP) are left out: they swing and float around the
    book, the covers, spine and corner pieces decide."""
    bones, mat = pose_bones(RP, g, ITEMS[g], True, open_amount, {"v.aura": 0.0, "v.sel": 1.0})
    inv = np.linalg.inv(mat(parent))
    pts = []
    for name, b in bones.items():
        if name in AURA_BONES or not b.get("cubes") or name.startswith(AURA_SKIP.get(g, ())):
            continue
        M = inv @ mat(name)
        if abs(np.linalg.det(M[:3, :3])) < 1e-6:          # hidden at this moment (scaled to 0)
            continue
        for c in b["cubes"]:
            lo, hi, cm = cube_box(c)
            pts.append((corners(lo, hi) @ (M @ cm).T)[:, :3])
    pts = np.concatenate(pts)
    pts[:, 0] = -pts[:, 0]                                  # bb -> file
    return pts.min(axis=0), pts.max(axis=0)


def _place_aura(g):
    geo_p = os.path.join(RP, "models", "entity", f"{g}.geo.json")
    geo = json.load(open(geo_p, encoding="utf-8"))
    bones = {b["name"]: b for b in geo["minecraft:geometry"][0]["bones"]}
    if "aura" not in bones:
        return
    parent = bones["aura"]["parent"]
    c_lo, c_hi = _posed_box(g, parent, 0.0)
    o_lo, o_hi = _posed_box(g, parent, 1.0)
    closed = np.array([(c_lo[0] + c_hi[0]) / 2, (c_lo[1] + c_hi[1]) / 2, c_hi[2] + AURA_GAP])
    opened = np.array([(o_lo[0] + o_hi[0]) / 2, (o_lo[1] + o_hi[1]) / 2, o_hi[2] + AURA_GAP])
    piv0 = np.array(bones["aura"]["pivot"], float)
    built_d = float(bones["aura_ring"]["cubes"][0]["size"][0])
    delta = closed - piv0
    for name in AURA_BONES:                               # move the circle onto the closed book
        b = bones[name]
        b["pivot"] = [round(float(v), 4) for v in np.array(b["pivot"], float) + delta]
        for c in b.get("cubes", []):
            c["origin"] = [round(float(v), 4) for v in np.array(c["origin"], float) + delta]
            if "pivot" in c:
                c["pivot"] = [round(float(v), 4) for v in np.array(c["pivot"], float) + delta]
    _dump(geo_p, geo)
    k_c = AURA_CLOSED * max(c_hi[0] - c_lo[0], c_hi[1] - c_lo[1]) / built_d
    k_o = AURA_OPEN * max(o_hi[0] - o_lo[0], o_hi[1] - o_lo[1]) / built_d
    glide = opened - closed
    anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
    an = json.load(open(anim_p, encoding="utf-8"))
    att = json.load(open(os.path.join(RP, "attachables", f"{ITEMS[g]}.json"), encoding="utf-8"))
    full = att["minecraft:attachable"]["description"]["animations"]["aura"]
    bone = an["animations"][full]["bones"]["aura"]
    bone["scale"] = (f"v.aura * ({k_c:.4f} + {k_o - k_c:.4f} * v.open)"
                     f" * (c.is_first_person ? 1.0 : {AURA_THIRD_PERSON})")
    bone["position"] = [f"v.open * {glide[i]:.4f}" for i in range(3)]
    _dump(anim_p, an)
    print(f"    {g}: circle on '{parent}'  closed book {np.round(c_hi - c_lo, 2).tolist()} centre "
          f"{np.round(closed, 2).tolist()}  open book {np.round(o_hi - o_lo, 2).tolist()} glide "
          f"{np.round(glide, 2).tolist()}  scale {k_c:.2f} -> {k_o:.2f}")


def build(pack):
    for g in ("book_dw", "book_dn", "book_ed"):
        geo_p = os.path.join(RP, "models", "entity", f"{g}.geo.json")
        if not os.path.exists(geo_p):
            continue
        geo = json.load(open(geo_p, encoding="utf-8"))
        bones = geo["minecraft:geometry"][0]["bones"]
        _hand_frame(g, geo, bones)
        _dump(geo_p, geo)
        ren = {b["name"]: f"{g}_{b['name']}" for b in bones if b["name"].lower() in PLAYER}
        if not ren:
            _bake_open(g)
            _place_aura(g)
            continue
        for b in bones:
            b["name"] = ren.get(b["name"], b["name"])
            if "parent" in b:
                b["parent"] = ren.get(b["parent"], b["parent"])
        _dump(geo_p, geo)
        anim_p = os.path.join(RP, "animations", f"{g}.animation.json")
        if os.path.exists(anim_p):
            an = json.load(open(anim_p, encoding="utf-8"))
            for a in an.get("animations", {}).values():
                if "bones" in a:
                    a["bones"] = {ren.get(k, k): v for k, v in a["bones"].items()}
            _dump(anim_p, an)
        rc_p = os.path.join(RP, "render_controllers", f"{g}.render_controllers.json")
        if os.path.exists(rc_p):
            rc = json.load(open(rc_p, encoding="utf-8"))
            for c in rc.get("render_controllers", {}).values():
                for key in ("materials", "part_visibility"):
                    if key in c:
                        c[key] = [{ren.get(k, k): v for k, v in e.items()} for e in c[key]]
            _dump(rc_p, rc)
        print(f"    {g}: renamed bones {ren}")
        _bake_open(g)
        _place_aura(g)
