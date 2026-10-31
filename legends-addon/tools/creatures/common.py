"""
Shared creature-spec structures and modelling helpers.

A Creature bundles everything the build needs for one entity: the model, its
texture variants, always-on animations (with Molang blend weights), the
"acts" (one-shot / held actions triggered by the script through the
legends:act property), part visibility rules and render tweaks.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mk.anim import Anim, kf, wave, fmt  # noqa: E402,F401
from mk.geo import Model, Bone  # noqa: E402


@dataclass
class Act:
    name: str
    anim: Anim
    length: float
    marks: List[float] = field(default_factory=list)   # impact moments (seconds) the script syncs to
    id: int = 0


@dataclass
class Creature:
    key: str
    model: Model
    acts: List[Act] = field(default_factory=list)
    loops: List[Tuple[str, Anim, Optional[str]]] = field(default_factory=list)   # (short, anim, blend weight)
    pre: List[str] = field(default_factory=list)
    visibility: List[Tuple[str, str]] = field(default_factory=list)            # (bone, molang)
    variants: int = 1                                                           # texture variants
    variant_expr: str = "0"                                                     # molang -> texture index
    overlay: Optional[Dict[str, str]] = None
    scale: float = 1.0
    description: str = ""
    preview_props: Dict[str, float] = field(default_factory=dict)

    def act(self, name: str, length: float, marks: Sequence[float] = (), loop="hold_on_last_frame") -> Anim:
        a = Anim(loop=loop, length=length)
        self.acts.append(Act(name, a, length, list(marks), len(self.acts) + 1))
        return a

    def loop(self, short: str, weight: Optional[str] = None) -> Anim:
        a = Anim(loop=True)
        self.loops.append((short, a, weight))
        return a

    def act_by_name(self, name) -> Act:
        for a in self.acts:
            if a.name == name:
                return a
        raise KeyError(name)


COMMON_PRE = [
    "variable.act = query.property('legends:act')",
    "variable.ph = query.property('legends:phase')",
    "variable.calm = math.lerp(variable.calm ?? 1.0, variable.act == 0 ? 1.0 : 0.2, 0.12)",
    "variable.mv = math.lerp(variable.mv ?? 0.0, query.property('legends:move'), 0.2)",
    "variable.dist = (variable.dist ?? 0.0) + query.delta_time * variable.mv * 6.0",
    "variable.fx = query.property('legends:fx')",
    "variable.ova = variable.fx == 0 ? 0.0 : (0.30 + math.sin(query.life_time * 540.0) * 0.12)",
    "variable.ovr = variable.fx == 3 ? 0.35 : 1.0",
    "variable.ovg = variable.fx == 2 ? 0.25 : (variable.fx == 3 ? 0.65 : (variable.fx == 1 || variable.fx == 4 ? 0.82 : 1.0))",
    "variable.ovb = variable.fx == 2 ? 0.2 : (variable.fx == 3 ? 1.0 : (variable.fx == 1 || variable.fx == 4 ? 0.3 : 1.0))",
]

# --------------------------------------------------------------------------- geometry helpers

AXES = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


def seg_box(start, direction: str, length: float, a: float, b: float, overlap: float = 0.6):
    """Origin/size of a box starting at `start` extending `length` along an axis with cross section a x b."""
    d = AXES[direction]
    x, y, z = start
    ax = [i for i in range(3) if d[i] != 0][0]
    lo = [0.0, 0.0, 0.0]
    size = [0.0, 0.0, 0.0]
    cross = [i for i in range(3) if i != ax]
    for i, s in zip(cross, (a, b)):
        lo[i] = start[i] - s / 2
        size[i] = s
    L = length + overlap
    if d[ax] > 0:
        lo[ax] = start[ax] - overlap
    else:
        lo[ax] = start[ax] - length
    size[ax] = L
    return tuple(lo), tuple(size)


def chain(m: Model, name: str, parent: str, start, direction: str, lengths: Sequence[float],
          sections: Sequence[Tuple[float, float]], rots: Sequence[Optional[Tuple[float, float, float]]],
          mat, extra: Optional[Callable[[Bone, int, Tuple[float, float, float]], None]] = None,
          overlap: float = 0.6, inflate: float = 0.0, share: Optional[str] = None, mirror=False) -> List[str]:
    """Chain of bones (tail, neck, horn...).  Bone i's pivot is the end of segment i-1."""
    d = AXES[direction]
    names = []
    p = tuple(float(v) for v in start)
    par = parent
    for i, L in enumerate(lengths):
        bn = f"{name}{i}"
        bone = m.bone(bn, p, par, rots[i] if i < len(rots) else None)
        o, s = seg_box(p, direction, L, sections[i][0], sections[i][1], overlap if i else 0.0)
        bone.add(o, s, mat[i] if isinstance(mat, (list, tuple)) else mat, inflate=inflate,
                 share=(f"{share}{i}" if share else None), mirror=mirror)
        if extra:
            extra(bone, i, p)
        names.append(bn)
        par = bn
        p = (p[0] + d[0] * L, p[1] + d[1] * L, p[2] + d[2] * L)
    return names


def ring_cubes(bone: Bone, center, radius: float, n: int, thick: float, depth: float, mat, plane: str = "xy",
               phase: float = 0.0, arc: float = 360.0, inflate=0.0, decals=None):
    """Approximate a ring/arc with n rotated boxes in the given plane (xy = facing Z, xz = flat, yz = facing X)."""
    seg = 2 * math.pi * radius * (arc / 360.0) / n * 1.08
    for i in range(n):
        a = math.radians(phase + arc * (i + 0.5) / n)
        cx, cy, cz = center
        if plane == "xy":
            px, py, pz = cx + math.cos(a) * radius, cy + math.sin(a) * radius, cz
            # segment tangent along (-sin, cos) in xy -> rotate a box (seg x thick) about Z
            deg = math.degrees(a) + 90
            o = (px - seg / 2, py - thick / 2, pz - depth / 2)
            bone.add(o, (seg, thick, depth), mat, pivot=(px, py, pz), rotation=(0, 0, -deg), inflate=inflate,
                     decals=decals or {})
        elif plane == "xz":
            px, py, pz = cx + math.cos(a) * radius, cy, cz + math.sin(a) * radius
            deg = math.degrees(a) + 90
            o = (px - seg / 2, py - depth / 2, pz - thick / 2)
            bone.add(o, (seg, depth, thick), mat, pivot=(px, py, pz), rotation=(0, -deg, 0), inflate=inflate,
                     decals=decals or {})
        else:  # yz
            px, py, pz = cx, cy + math.cos(a) * radius, cz + math.sin(a) * radius
            deg = math.degrees(a)
            o = (px - depth / 2, py - thick / 2, pz - seg / 2)
            bone.add(o, (depth, thick, seg), mat, pivot=(px, py, pz), rotation=(-deg, 0, 0), inflate=inflate,
                     decals=decals or {})


def mirror_x(o, s):
    """Mirror a box (origin, size) across the YZ plane."""
    return (-(o[0] + s[0]), o[1], o[2]), s


def sym(bone_r: Bone, bone_l: Bone, origin, size, mat, **kw):
    """Add a box to a right-side bone and its mirror to the left-side bone."""
    bone_r.add(origin, size, mat, **kw)
    o2, s2 = mirror_x(origin, size)
    kw2 = dict(kw)
    if "pivot" in kw2 and kw2["pivot"] is not None:
        p = kw2["pivot"]
        kw2["pivot"] = (-p[0], p[1], p[2])
    if "rotation" in kw2 and kw2["rotation"] is not None:
        r = kw2["rotation"]
        kw2["rotation"] = (r[0], -r[1], -r[2])
    kw2["mirror"] = not kw.get("mirror", False)
    bone_l.add(o2, s2, mat, **kw2)


def mrot(r):
    """Mirror a Bedrock rotation across the YZ plane."""
    return None if r is None else (r[0], -r[1], -r[2])


def mpt(p):
    return (-p[0], p[1], p[2])


def descendants(m: Model, name: str) -> List[str]:
    out, frontier = [name], [name]
    while frontier:
        nxt = [b.name for b in m.bones if b.parent in frontier]
        out += nxt
        frontier = nxt
    return out


def scale_subtree(m: Model, name: str, k: float, about=None):
    """Uniformly scale a bone and all its descendants about the bone's pivot (geometry only)."""
    root = m.get(name)
    c0 = about or root.pivot

    def sp(p):
        return tuple(c0[i] + (p[i] - c0[i]) * k for i in range(3))
    for bn in descendants(m, name):
        b = m.get(bn)
        b.pivot = sp(b.pivot)
        for cb in b.cubes:
            cb.origin = sp(cb.origin)
            cb.size = tuple(v * k for v in cb.size)
            if cb.pivot:
                cb.pivot = sp(cb.pivot)
            cb.inflate *= k
        b.locators = {n: sp(p) for n, p in b.locators.items()}


def translate_subtree(m: Model, name: str, d):
    """Move a bone and all its descendants by d (geometry only)."""
    def tp(p):
        return tuple(p[i] + d[i] for i in range(3))
    for bn in descendants(m, name):
        b = m.get(bn)
        b.pivot = tp(b.pivot)
        for cb in b.cubes:
            cb.origin = tp(cb.origin)
            if cb.pivot:
                cb.pivot = tp(cb.pivot)
        b.locators = {n: tp(p) for n, p in b.locators.items()}
