"""Reusable rig parts: feathered wings, symmetric animation helpers, limb chains."""
from __future__ import annotations

import math

from .anim import Expr


def mirror_rot(v):
    """Mirror a rotation channel across the YZ plane (right side -> left side)."""
    if isinstance(v, dict):
        return {t: (x[0], _neg(x[1]), _neg(x[2])) for t, x in v.items()}
    return (v[0], _neg(v[1]), _neg(v[2]))


def mirror_pos(v):
    if isinstance(v, dict):
        return {t: (_neg(x[0]), x[1], x[2]) for t, x in v.items()}
    return (_neg(v[0]), v[1], v[2])


def _neg(c):
    return -c


def sym(anim, pattern, rot=None, pos=None, scl=None, smooth=True, phase_l=None):
    """Apply a channel to '{s}'='r' and mirrored to '{s}'='l'.  pattern e.g. 'wing_{s}_a1'.

    phase_l: optional alternative rot for the left side (already in right-side terms,
    it is mirrored for you) -- used for out-of-phase gaits.
    """
    r, l = pattern.format(s="r"), pattern.format(s="l")
    if rot is not None:
        anim.rot(r, rot, smooth)
        anim.rot(l, mirror_rot(phase_l if phase_l is not None else rot), smooth)
    if pos is not None:
        anim.pos(r, pos, smooth)
        anim.pos(l, mirror_pos(pos), smooth)
    if scl is not None:
        anim.scl(r, scl, smooth)
        anim.scl(l, scl, smooth)
    return anim


def feather_wing(model, name, parent, pivot, side, segs, rows, arm_mat, feather_mats, covert_mat=None,
                 arm_thick=3.0, droop=0.0, z_back=0.6, tip_feathers=None, overlay=None, overlay_prefix="insc_"):
    """Feathered wing extending along side*X from `pivot` (rest pose = fully spread).

    segs : segment lengths, bones '{name}_a1..N' chained from the shoulder.
    rows : per segment dict(n, l0, l1, w, a0, a1, bones=True, covert=(len, w) | None)
           n flight feathers from length l0 (inner) to l1 (outer), fanned from angle a0 to a1
           (0 = straight down, + = toward the wing tip).
    tip_feathers : dict(n, l, w, a0, a1) extra primaries radiating from the wing tip.
    overlay : optional Mat drawn on duplicate planes just in front of every flight feather in
           bones named '{overlay_prefix}{name}_...' (so a render controller can toggle them).
    Returns dict(arms=[...], feathers=[...]) of bone names.
    """
    arms, feathers = [], []
    x = pivot[0]
    par = parent
    px, py, pz = pivot
    for i, L in enumerate(segs):
        b = model.bone(f"{name}_a{i + 1}", par, pivot=(x, py, pz))
        arms.append(b.name)
        x0, x1 = (x, x + L) if side > 0 else (x - L, x)
        t = arm_thick * (1 - 0.18 * i)
        b.cube((x0, py - t / 2, pz - t / 2), (L, t, t), arm_mat, variant=i)
        row = rows[i]
        n = row["n"]
        for k in range(n):
            f = (k + 0.5) / n
            fx = x + side * L * f
            fl = row["l0"] + (row["l1"] - row["l0"]) * f
            ang = (row["a0"] + (row["a1"] - row["a0"]) * f) * side
            w = row["w"]
            mat = feather_mats[(k + i) % len(feather_mats)]
            zz = pz + z_back + 0.12 * ((k + i) % 3)
            if row.get("bones", True):
                fb = model.bone(f"{name}_f{i + 1}_{k + 1}", b.name, pivot=(fx, py - droop, zz), rot=(0, 0, ang))
                fb.cube((fx - w / 2, py - droop - fl, zz), (w, fl, 0), mat, variant=k % 3)
                feathers.append(fb.name)
                if overlay is not None:
                    ob = model.bone(f"{overlay_prefix}{name}_f{i + 1}_{k + 1}", fb.name, pivot=(fx, py - droop, zz))
                    ob.cube((fx - w / 2, py - droop - fl, zz - 0.25), (w, fl, 0), overlay, variant=k % 4)
            else:
                b.cube((fx - w / 2, py - droop - fl, zz), (w, fl, 0), mat, variant=k % 3,
                       rot=(0, 0, ang), pivot=(fx, py - droop, zz))
        cv = row.get("covert")
        if cv and covert_mat is not None:
            cl, cw = cv
            m = max(2, int(round(L / (cw * 0.8))))
            for k in range(m):
                f = (k + 0.5) / m
                fx = x + side * L * f
                ang = (row["a0"] + (row["a1"] - row["a0"]) * f) * side * 0.6
                b.cube((fx - cw / 2, py - cl, pz - t / 2 - 0.15 - 0.1 * (k % 2)), (cw, cl, 0), covert_mat,
                       variant=k % 2, rot=(0, 0, ang), pivot=(fx, py, pz))
        x = x + side * L
        par = b.name
    if tip_feathers:
        tf = tip_feathers
        last = model.bones[arms[-1]]
        for k in range(tf["n"]):
            f = k / max(1, tf["n"] - 1)
            ang = (tf["a0"] + (tf["a1"] - tf["a0"]) * f) * side
            mat = feather_mats[k % len(feather_mats)]
            zz = pz + z_back + 0.1 * (k % 3)
            fb = model.bone(f"{name}_t{k + 1}", last.name, pivot=(x, py, zz), rot=(0, 0, ang))
            fb.cube((x - tf["w"] / 2, py - tf["l"], zz), (tf["w"], tf["l"], 0), mat, variant=k % 3)
            feathers.append(fb.name)
            if overlay is not None:
                ob = model.bone(f"{overlay_prefix}{name}_t{k + 1}", fb.name, pivot=(x, py, zz))
                ob.cube((x - tf["w"] / 2, py - tf["l"], zz - 0.25), (tf["w"], tf["l"], 0), overlay, variant=k % 4)
    return {"arms": arms, "feathers": feathers}


def flutter(anim, feathers, amp=3.0, period=2.4, spread=0.13, clock="q.life_time"):
    """Small independent sway on a list of feather bones (secondary motion)."""
    from .anim import S
    for i, f in enumerate(feathers):
        anim.rot(f, (S(amp * 0.6, period * 1.3, i * spread * 1.7, clock=clock), 0,
                     S(amp, period, i * spread, clock=clock)))
    return anim


def segmented(model, prefix, parent, start, step, n, size_fn, mat_fn, pivot_at_start=True):
    """A chain of n bones each carrying one box; returns bone names.

    start: joint of first bone; step: vector to next joint; size_fn(i) -> (sx, sy, sz) box centred on
    the segment; mat_fn(i) -> Mat.
    """
    names = []
    p = list(start)
    par = parent
    for i in range(n):
        b = model.bone(f"{prefix}{i + 1}", par, pivot=tuple(p))
        s = size_fn(i)
        c = [p[k] + step[k] / 2 for k in range(3)]
        b.box(tuple(c), s, mat_fn(i), variant=i % 3)
        names.append(b.name)
        par = b.name
        p = [p[k] + step[k] for k in range(3)]
    return names


def wave(anim, bones, axis, amp, period, lag=0.12, grow=1.0, clock="q.anim_time", base=0.0):
    """Travelling sine wave down a bone chain (tails, necks, ribbons)."""
    from .anim import S
    for i, b in enumerate(bones):
        a = amp * (grow ** i)
        v = [0, 0, 0]
        v[axis] = S(a, period, -i * lag, base, clock=clock)
        anim.rot(b, tuple(v))
    return anim
