"""Reusable construct parts. Orientation lives on parent bones (rest rotation), spinning on child
bones with zero rest rotation, so an animated [0, spin, 0] always spins around the part's own axis."""


def oriented(fx, name, parent, pivot, rx=0.0, ry=0.0):
    """Create name_o (Y rest) > name_t (X rest) > name; returns the content bone."""
    p = parent
    if ry:
        fx.model.bone(f"{name}_o", p, pivot=pivot, rotation=(0, ry, 0))
        p = f"{name}_o"
    if rx:
        fx.model.bone(f"{name}_t", p, pivot=pivot, rotation=(rx, 0, 0))
        p = f"{name}_t"
    return fx.model.bone(name, p, pivot=pivot)


def ring(fx, name, parent, center, radius, thick, height, segs, style, rx=0.0, ry=0.0, gap=0.0, arc=360.0, start=0.0):
    """Ring around `center`; rx=90 makes it face forward (normal along Z)."""
    b = oriented(fx, name, parent, center, rx, ry)
    b.ring(center, radius, thick, height, segs, style, gap=gap, arc=arc, start=start)
    return b


def disc(fx, name, parent, center, radius, rect, rx=0.0, ry=0.0):
    """Flat textured disc (both sides) e.g. a magic circle inside a construct."""
    b = oriented(fx, name, parent, center, rx, ry)
    b.box((center[0] - radius, center[1], center[2] - radius), (radius * 2, 0, radius * 2), None,
          faces={"up": rect, "down": rect})
    return b


def spin(anim, bone, speed, axis="y"):
    v = f"q.life_time * {speed}"
    anim.rot(bone, [v, 0, 0] if axis == "x" else [0, v, 0] if axis == "y" else [0, 0, v])


def vibrate(anim, bone, amp=0.04, hz=8.0, phase=0.0):
    e = f"1 + math.sin(q.life_time * {360 * hz} + {phase}) * {amp}"
    anim.scale(bone, [e, e, e])
