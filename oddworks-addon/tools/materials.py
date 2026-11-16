"""Procedural surface painters for ODDWORKS models (see modelkit.FaceCtx)."""
from __future__ import annotations

import math

from modelkit import FaceCtx, Painter, TRANSPARENT, hx, mix, noise2, ramp, shade, with_alpha

# ----------------------------------------------------------------------------- antler / bone

ANTLER = hx("e9dcc0")
ANTLER_DARK = hx("b8a27c")
ANTLER_DEEP = hx("8a7353")
SOOT = hx("1b1714")


def antler(engrave: bool = True, patina: float = 0.35) -> Painter:
    """Caribou-antler: creamy, fine longitudinal grain, darker patina in hollows,
    engraved dot-and-line motif (filled with soot) on the outward (north) faces."""
    def p(f: FaceCtx) -> Painter:
        x, y, z = f.pos
        g = noise2(x * 2.2, y * 9.0, 3) * 0.6 + noise2(x * 7.0, y * 2.0, 5) * 0.4
        col = mix(ANTLER, ANTLER_DARK, g * patina * 1.6)
        if f.face in ("down", "south"):
            col = shade(col, -0.18)
        if f.face == "south":                      # inner face of the goggles: soot blackened
            return f.jitter(mix(SOOT, ANTLER_DEEP, 0.15), 0.05)
        if engrave and f.face == "north":
            # dotted engraving along the upper bar and circle-dots near the temples
            if abs(y - 29.25) < 0.14 and (round(x * 4) % 3 == 0):
                return mix(SOOT, ANTLER_DEEP, 0.3)
            for cx in (-3.75, 3.75):
                d = math.hypot(x - cx, y - 28.2)
                if 0.38 < d < 0.62 or d < 0.14:
                    return mix(SOOT, ANTLER_DEEP, 0.25)
        if f.rng.random() < 0.03:
            col = shade(col, -0.2)
        return f.jitter(col, 0.03)
    return p


def sun_ice(glow_alpha: int = 70) -> Painter:
    """Translucent amber 'sun-ice' lens. Low alpha = emissive under entity_emissive_alpha."""
    def p(f: FaceCtx):
        x, y, _ = f.pos
        t = 0.5 + 0.5 * math.sin(x * 3.1 + y * 1.7)
        col = ramp([(0, "ffd36b"), (0.6, "ffb340"), (1, "fff2c2")], t)
        return with_alpha(col, glow_alpha)
    return p


def sinew(base="6b4a2e") -> Painter:
    b = hx(base)

    def p(f: FaceCtx):
        x, y, z = f.pos
        twist = (x * 3 + z * 3 + y * 4) % 1.0
        col = shade(b, 0.18) if twist < 0.35 else shade(b, -0.12) if twist > 0.75 else b
        return f.jitter(col, 0.03)
    return p


def sealskin() -> Painter:
    base, spot = hx("6f6a62"), hx("3e3a35")

    def p(f: FaceCtx):
        x, y, z = f.pos
        n = noise2(x * 1.7 + z * 1.3, y * 1.9, 11)
        col = mix(base, spot, 1.0 if n > 0.72 else 0.0)
        return f.jitter(col, 0.04)
    return p


# ----------------------------------------------------------------------------- wood / metals / line

def turned_wood(base="9a5b2e", dark="6a3a1c", light="c48a52", axis="y", rings=2.2) -> Painter:
    """Turned hardwood with grain along `axis`, growth rings on end grain."""
    b, d, l = hx(base), hx(dark), hx(light)

    def p(f: FaceCtx):
        x, y, z = f.pos
        along = {"x": x, "y": y, "z": z}[axis]
        across = {"x": y + z, "y": x + z, "z": x + y}[axis]
        g = 0.5 + 0.5 * math.sin(across * 9.0 + noise2(along * 0.8, across * 1.3, 2) * 6.0)
        col = mix(b, d, g * 0.55)
        if g > 0.92:
            col = mix(col, l, 0.5)
        return f.jitter(col, 0.035)
    return p


def lacquer(base="2b1d18", hi="5a3b2c") -> Painter:
    b, h = hx(base), hx(hi)

    def p(f: FaceCtx):
        t = f.u if f.side else f.v
        col = mix(h, b, min(1.0, abs(t - 0.3) * 2.2))
        return f.jitter(col, 0.02)
    return p


def brass(base="c9a24a", dark="7d5f22", light="fff0b0") -> Painter:
    b, d, l = hx(base), hx(dark), hx(light)

    def p(f: FaceCtx):
        t = f.v
        col = mix(l, b, min(1.0, t * 2.4)) if t < 0.5 else mix(b, d, (t - 0.5) * 2)
        if f.face == "up":
            col = shade(b, 0.25)
        return f.jitter(col, 0.03)
    return p


def iron(base="5c5f66", light="a9adb5") -> Painter:
    b, l = hx(base), hx(light)

    def p(f: FaceCtx):
        col = mix(l, b, f.v * 0.9) if f.side else shade(b, 0.12)
        return f.jitter(col, 0.04)
    return p


def lead() -> Painter:
    b = hx("6e7684")

    def p(f: FaceCtx):
        col = shade(b, (0.5 - f.v) * 0.35) if f.side else shade(b, 0.15 if f.face == "up" else -0.2)
        if f.rng.random() < 0.06:
            col = shade(col, -0.12)
        return f.jitter(col, 0.03)
    return p


def line_windings(base="efe6cf", shadow="b9ae92", glow="7fe0d0", wind_axis="x") -> Painter:
    """Braided 'drowned silk' line wound on the drum: diagonal windings, faint teal glow
    every few turns (alpha < 255 renders emissive with entity_emissive_alpha)."""
    b, s, g = hx(base), hx(shadow), hx(glow)

    def p(f: FaceCtx):
        x, y, z = f.pos
        along = {"x": x, "y": y, "z": z}[wind_axis]
        around = math.atan2(y - 0, z - 0) if wind_axis == "x" else math.atan2(x, z)
        k = (along * 4.0 + around * 0.6) % 1.0
        col = b if k < 0.62 else s
        if int(along * 4.0) % 5 == 2 and k < 0.4:
            return with_alpha(mix(col, g, 0.6), 150)
        return f.jitter(col, 0.025)
    return p


def pearl() -> Painter:
    def p(f: FaceCtx):
        x, y, z = f.pos
        t = (math.sin(x * 2.3 + y * 1.1) + math.sin(z * 1.7 - y * 2.0)) * 0.25 + 0.5
        col = ramp([(0, "d9f2ff"), (0.35, "f7e6ff"), (0.7, "e3fff1"), (1, "fff6dc")], t)
        return with_alpha(col, 215)
    return p


# ----------------------------------------------------------------------------- bamboo / blade / cord

def bamboo(nodes=(0.0,), base="c8b25a", light="e8d98e", dark="8f7a2e", node_col="5e4b1c",
           smoked: float = 0.0, axis="y") -> Painter:
    """Aged golden bamboo: long fibres, sheen band, dark node rings at the given positions."""
    b, l, d, nc = hx(base), hx(light), hx(dark), hx(node_col)
    if smoked:
        b, l, d = mix(b, hx("6b4a22"), smoked), mix(l, hx("9b7a42"), smoked), mix(d, hx("3e2a12"), smoked)

    def p(f: FaceCtx):
        x, y, z = f.pos
        along = {"x": x, "y": y, "z": z}[axis]
        across = {"x": (y, z), "y": (x, z), "z": (x, y)}[axis]
        for n in nodes:
            dn = along - n
            if abs(dn) < 0.32:
                return f.jitter(nc, 0.04)
            if 0.32 <= abs(dn) < 0.62:
                return f.jitter(mix(d, b, 0.4), 0.04)
        fib = noise2(across[0] * 6.0 + across[1] * 6.0, along * 0.35, 9)
        col = mix(b, d, fib * 0.45)
        if f.side and 0.2 < f.u < 0.42:
            col = mix(col, l, 0.45)                 # sheen stripe
        if not f.side:
            col = shade(col, -0.1)
        return f.jitter(col, 0.025)
    return p


def blade_steel(edge_side: str = "west") -> Painter:
    """Polished steel with a wavy hamon line, darker spine and a bright cutting edge."""
    spine, body, hamon, edge = hx("8c939e"), hx("c9d0d8"), hx("f2f6fa"), hx("ffffff")

    def p(f: FaceCtx):
        x, y, z = f.pos
        if f.face in ("north", "south"):
            t = f.u if f.face == "north" else 1 - f.u          # across the blade width
            wave = 0.55 + 0.08 * math.sin(y * 3.4) + 0.05 * math.sin(y * 7.9)
            if t > 0.86:
                col = edge
            elif t > wave:
                col = mix(hamon, body, 0.25)
            else:
                col = mix(spine, body, t / max(wave, 0.01))
            if abs(t - wave) < 0.05:
                col = shade(col, 0.15)
            return col
        if f.face == edge_side:
            return edge
        return shade(spine, -0.15)
    return p


def silk_cord(a="7a1f2b", b="d7b45a") -> Painter:
    ca, cb = hx(a), hx(b)

    def p(f: FaceCtx):
        x, y, z = f.pos
        k = int((y * 3 + x * 2 + z * 2) * 2) % 3
        return f.jitter(cb if k == 0 else ca, 0.04)
    return p


# ----------------------------------------------------------------------------- ice / sun

def clear_ice(alpha=150) -> Painter:
    def p(f: FaceCtx):
        x, y, z = f.pos
        n = noise2(x * 0.9 + z * 0.7, y * 0.9, 4)
        col = mix(hx("bfe9ff"), hx("f2fbff"), n)
        a = alpha
        if f.edge:
            col, a = hx("ffffff"), min(255, alpha + 60)
        elif n > 0.78:
            col, a = hx("ffffff"), min(255, alpha + 40)    # internal fractures
        return with_alpha(col, a)
    return p


def sun_core(alpha=40) -> Painter:
    def p(f: FaceCtx):
        d = math.hypot(f.u - 0.5, f.v - 0.5) * 2
        col = ramp([(0, "fffbe6"), (0.5, "ffe08a"), (1, "ffb347")], d)
        return with_alpha(col, alpha)
    return p
