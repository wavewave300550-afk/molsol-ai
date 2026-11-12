"""Geometry helpers shared by the expansion 02 construct modules (code reuse only; each spell builds
its own silhouette from these primitives)."""
import math


def aim_rot(d):
    """Cube rotation (rx, ry, 0) that turns a +Y-aligned box to point along vector d.
    Raw Bedrock cube rotation: X = Rx(-a), then Y = Ry(+b) (X applied first)."""
    x, y, z = d
    L = math.sqrt(x * x + y * y + z * z) or 1.0
    x, y, z = x / L, y / L, z / L
    a = math.degrees(math.acos(max(-1.0, min(1.0, y))))
    b = math.degrees(math.atan2(-x, -z)) if abs(a) > 1e-6 else 0.0
    return (a, b, 0.0)


def aim_box(bone, A, B, thick, style, pad=0.0):
    """Box spanning point A to point B (pixels) with a square cross-section."""
    d = (B[0] - A[0], B[1] - A[1], B[2] - A[2])
    L = math.sqrt(sum(c * c for c in d))
    mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2)
    bone.cbox(mid, (thick, L + pad, thick), style, rotation=aim_rot(d))
    return L


def helix_z(bone, base, radius, length, turns, n, style, phase=0.0, size=0.6, direction=-1):
    """Small cubes along a helix around the Z axis, from base towards `direction` * length."""
    for i in range(n):
        t = i / max(1, n - 1)
        a = phase + t * turns * math.tau
        p = (base[0] + math.cos(a) * radius, base[1] + math.sin(a) * radius, base[2] + direction * t * length)
        bone.cbox(p, (size, size, size * 1.8), style, rotation=(0, 0, math.degrees(a)))


def polyline(bone, pts, thick, style):
    for a, b in zip(pts, pts[1:]):
        aim_box(bone, a, b, thick, style, pad=thick * 0.5)


def silhouette(fx, prefix, parent, style, scale=1.0, inflate=0.0, offset=(0, 0, 0), limbs=True):
    """Player-proportioned figure (1.8 blocks). Returns the bone names created (head, body, arms, legs)."""
    s = scale
    ox, oy, oz = offset
    names = {}
    def part(name, pivot, center, size):
        b = fx.bone(f"{prefix}{name}", parent, pivot=(ox + pivot[0] * s, oy + pivot[1] * s, oz + pivot[2] * s))
        b.cbox((ox + center[0] * s, oy + center[1] * s, oz + center[2] * s),
               (size[0] * s + inflate, size[1] * s + inflate, size[2] * s + inflate), style)
        names[name] = f"{prefix}{name}"
        return b
    part("body", (0, 12, 0), (0, 18, 0), (8, 12, 4))
    part("head", (0, 24, 0), (0, 28, 0), (8, 8, 8))
    if limbs:
        part("arm_l", (6, 22, 0), (6, 16, 0), (4, 12, 4))
        part("arm_r", (-6, 22, 0), (-6, 16, 0), (4, 12, 4))
        part("leg_l", (2, 12, 0), (2, 6, 0), (4, 12, 4))
        part("leg_r", (-2, 12, 0), (-2, 6, 0), (4, 12, 4))
    return names


def walk_cycle(anim, names, amp=28, speed=420):
    anim.rot(names["arm_l"], [f"math.sin(q.life_time * {speed}) * {amp}", 0, 0])
    anim.rot(names["arm_r"], [f"-math.sin(q.life_time * {speed}) * {amp}", 0, 0])
    anim.rot(names["leg_l"], [f"-math.sin(q.life_time * {speed}) * {amp}", 0, 0])
    anim.rot(names["leg_r"], [f"math.sin(q.life_time * {speed}) * {amp}", 0, 0])
