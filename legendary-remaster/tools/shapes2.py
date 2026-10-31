"""More building blocks: tapered tubes along curves (horns, tails, tentacles), feather fans,
stepped flanges and symmetric helpers. Built on shapes.strut (square-section rotated boxes)."""
import math

from modelkit import Bone
from shapes import r3, strut


def tube(bone: Bone, pts, w0, w1, mat, glow=False, overlap=0.6, depth_ratio=1.0, mats=None, soft=True):
    """Tapered chain of struts through pts (list of xyz). Width lerps w0 -> w1.
    Each segment is extended by `overlap` units into the next so joints stay closed."""
    n = len(pts) - 1
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        if L < 1e-6:
            continue
        ext = min(overlap, L * 0.4)
        d = tuple((b[k] - a[k]) / L for k in range(3))
        b2 = tuple(b[k] + d[k] * ext for k in range(3)) if i < n - 1 else b
        w = w0 + (w1 - w0) * (i / max(1, n - 1))
        m = mats[i] if mats else mat
        strut(bone, a, b2, max(0.25, w), m, glow=glow, depth=max(0.25, w * depth_ratio), soft=soft)


def spiral_pts(base, axis_dir, radial0, r0, r1, turns, n, advance):
    """Points of a conical spiral starting at `base`.
    axis_dir: unit axis of the spiral; radial0: unit vector from the axis to the start point.
    r0->r1 radius, `turns` revolutions, `advance` distance along the axis over the whole spiral."""
    ax = axis_dir
    u = radial0
    # v = ax x u
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    center = tuple(base[k] - u[k] * r0 for k in range(3))
    out = []
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        r = r0 + (r1 - r0) * t
        out.append(tuple(center[k] + ax[k] * advance * t + (u[k] * math.cos(a) + v[k] * math.sin(a)) * r for k in range(3)))
    return out


def bezier(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        out.append(tuple(mt ** 3 * p0[k] + 3 * mt * mt * t * p1[k] + 3 * mt * t * t * p2[k] + t ** 3 * p3[k] for k in range(3)))
    return out


def stepped_flange(bone: Bone, x0, x1, y0, z0, z1, heights, mat, **kw):
    """Notched bronze flange: a row of boxes of varying height along z (x0..x1 thickness)."""
    n = len(heights)
    dz = (z1 - z0) / n
    for i, h in enumerate(heights):
        bone.add(r3((x0, y0, z0 + i * dz)), r3((x1 - x0, h, dz + (0.05 if i % 2 else 0))), mat, **kw)


def feather(bone: Bone, root, length, width, yaw, pitch, mat, thick=0.6, glow=False, roll=0.0):
    """Flat feather/plate pointing from root along (yaw, pitch): built along -z then rotated."""
    x, y, z = root
    origin = (x - width / 2, y - thick / 2, z - length)
    bone.add(r3(origin), r3((width, thick, length)), mat, pivot=r3(root),
             rotation=(round(pitch, 3), round(yaw, 3), round(roll, 3)), glow=glow)


def mirror_pts(pts):
    return [(-p[0], p[1], p[2]) for p in pts]


def catmull(points, n_per=4):
    """Catmull-Rom spline through control points (endpoints duplicated)."""
    P = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n_per):
            t = s / n_per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(3)))
    out.append(tuple(points[-1]))
    return out
