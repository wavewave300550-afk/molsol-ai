"""Geometric building blocks on top of modelkit: bevelled boxes, rings, gears, frames, orbs, struts, spikes."""
import math

from modelkit import Bone


def _n(deg: float) -> float:
    return round((deg + 180) % 360 - 180, 3)


def r3(p):
    return tuple(round(x, 3) for x in p)


def bevel(bone: Bone, origin, size, mat, b=None, **kw):
    """Chamfered box from three overlapping boxes (the hidden overlaps are buried, so no flicker)."""
    x, y, z = origin
    sx, sy, sz = size
    b = b if b is not None else min(1.0, min(size) * 0.18)
    if b <= 0 or min(size) <= 2 * b + 0.05:
        bone.add(origin, size, mat, **kw)
        return
    bone.add((x + b, y, z + b), (sx - 2 * b, sy, sz - 2 * b), mat, **kw)
    bone.add((x, y + b, z + b), (sx, sy - 2 * b, sz - 2 * b), mat, **kw)
    bone.add((x + b, y + b, z), (sx - 2 * b, sy - 2 * b, sz), mat, **kw)


def ring(bone: Bone, center, radius, segments, mat, *, thickness=1.0, width=1.0, plane="xz", glow=False,
         phase=0.0, fill=1.06, arc=(0.0, 360.0), decals=None, jag=None):
    """Circle (or arc) of tangent-aligned cubes. plane 'xz' horizontal, 'xy' faces z, 'yz' faces x.
    jag: optional list of radial-thickness multipliers cycled per segment (shards, gear teeth)."""
    cx, cy, cz = center
    a0, a1 = math.radians(arc[0]), math.radians(arc[1])
    full = abs(arc[1] - arc[0]) >= 359.9
    n = segments
    step = (a1 - a0) / (n if full else max(1, n - 1))
    L = abs(step) * radius * fill
    for i in range(n):
        a = a0 + step * i + phase
        ad = math.degrees(a)
        t = thickness * (jag[i % len(jag)] if jag else 1.0)
        off = (t - thickness) / 2
        r = radius + off
        wd = width + (0.07 if i % 2 else 0.0)        # alternate widths: neighbours never share a plane
        if plane == "xz":
            p = (cx + r * math.cos(a), cy, cz + r * math.sin(a))
            size, rot = (L, wd, t), (0, _n(ad + 90), 0)
        elif plane == "xy":
            p = (cx + r * math.cos(a), cy + r * math.sin(a), cz)
            size, rot = (L, t, wd), (0, 0, _n(ad + 90))
        else:
            p = (cx, cy + r * math.cos(a), cz + r * math.sin(a))
            size, rot = (wd, L, t), (_n(-(ad + 90)), 0, 0)
        origin = tuple(p[k] - size[k] / 2 for k in range(3))
        bone.add(r3(origin), r3(size), mat, pivot=r3(p), rotation=rot, glow=glow, decals=dict(decals or {}))


def gear(bone: Bone, center, radius, teeth, mat, *, plane="xy", width=1.6, hub=None, spokes=4, glow=False):
    """Toothed wheel with hub and spokes."""
    ring(bone, center, radius, teeth * 2, mat, thickness=1.6, width=width, plane=plane, jag=[1.0, 2.2], glow=glow)
    hub_r = hub or max(1.2, radius * 0.25)
    cx, cy, cz = center
    if plane == "xy":
        bone.add((cx - hub_r, cy - hub_r, cz - width / 2 - 0.2), (2 * hub_r, 2 * hub_r, width + 0.4), mat, glow=glow)
    elif plane == "xz":
        bone.add((cx - hub_r, cy - width / 2 - 0.2, cz - hub_r), (2 * hub_r, width + 0.4, 2 * hub_r), mat, glow=glow)
    else:
        bone.add((cx - width / 2 - 0.2, cy - hub_r, cz - hub_r), (width + 0.4, 2 * hub_r, 2 * hub_r), mat, glow=glow)
    for k in range(spokes):
        a = math.pi * k / spokes
        d = (math.cos(a), math.sin(a))
        L = radius - 0.6
        if plane == "xy":
            a_, b_ = (cx - d[0] * L, cy - d[1] * L, cz), (cx + d[0] * L, cy + d[1] * L, cz)
        elif plane == "xz":
            a_, b_ = (cx - d[0] * L, cy, cz - d[1] * L), (cx + d[0] * L, cy, cz + d[1] * L)
        else:
            a_, b_ = (cx, cy - d[0] * L, cz - d[1] * L), (cx, cy + d[0] * L, cz + d[1] * L)
        strut(bone, a_, b_, 0.9, mat, glow=glow)


def frame_cube(bone: Bone, center, side, t, mat, glow=False):
    cx, cy, cz = center
    h = side / 2
    L = side + t
    for a in (-h, h):
        for b in (-h, h):
            bone.add((cx - L / 2, cy + a - t / 2, cz + b - t / 2), (L, t, t), mat, glow=glow)
            bone.add((cx + a - t / 2, cy - L / 2 + t, cz + b - t / 2), (t, L - 2 * t, t), mat, glow=glow)
            bone.add((cx + a - t / 2, cy + b - t / 2, cz - L / 2 + t), (t, t, L - 2 * t), mat, glow=glow)


def orb(bone: Bone, center, r, mat, glow=False, k=0.72, **kw):
    cx, cy, cz = center
    for sx, sy, sz in ((2 * r, 2 * r * k, 2 * r * k), (2 * r * k, 2 * r, 2 * r * k), (2 * r * k, 2 * r * k, 2 * r)):
        bone.add(r3((cx - sx / 2, cy - sy / 2, cz - sz / 2)), r3((sx, sy, sz)), mat, glow=glow, **kw)


def strut(bone: Bone, a, b, thickness, mat, glow=False, depth=None, **kw):
    """Box from point a to point b. Built along +y, then pitched (x) and yawed (y)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    if L < 1e-6:
        return
    d = (dx / L, dy / L, dz / L)
    alpha = math.atan2(math.hypot(d[0], d[2]), d[1])
    phi = math.atan2(d[0], d[2]) if (abs(d[0]) > 1e-9 or abs(d[2]) > 1e-9) else 0.0
    rot = (_n(-math.degrees(alpha)), _n(-math.degrees(phi)), 0)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
    dz_ = depth if depth is not None else thickness
    origin = (mid[0] - thickness / 2, mid[1] - L / 2, mid[2] - dz_ / 2)
    bone.add(r3(origin), r3((thickness, L, dz_)), mat, pivot=r3(mid), rotation=rot if any(rot) else None, glow=glow, **kw)


def spike(bone: Bone, base, tip, width, mat, steps=3, glow=False, tip_mat=None):
    """Tapered spike from base to tip made of shrinking struts."""
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        a = tuple(base[k] + (tip[k] - base[k]) * t0 for k in range(3))
        b = tuple(base[k] + (tip[k] - base[k]) * min(1.0, t1 + 0.08) for k in range(3))
        w = width * (1 - t0 * 0.75)
        strut(bone, a, b, max(0.3, w), tip_mat if (tip_mat and i == steps - 1) else mat, glow=glow)


def chain_links(bone: Bone, top, n, link, mat):
    """Hanging chain: alternating links rotated 90 degrees."""
    x, y, z = top
    for i in range(n):
        yy = y - i * link * 0.9
        if i % 2 == 0:
            bone.add(r3((x - link * 0.35, yy - link, z - 0.25)), r3((link * 0.7, link, 0.5)), mat)
        else:
            bone.add(r3((x - 0.25, yy - link, z - link * 0.35)), r3((0.5, link, link * 0.7)), mat)


def mirror_x(origin, size):
    return (-(origin[0] + size[0]), origin[1], origin[2])


def mx(p):
    return (-p[0], p[1], p[2])
