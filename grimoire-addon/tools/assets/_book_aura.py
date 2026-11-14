"""Magic circle built into each held book (shared helper for books_dw / books_dn / books_ed).

The selection vision used to be a separate entity floating in front of the eyes.  On an iPhone it
never lined up with the book in the hand: the first-person item and the world are drawn with
different cameras, and a world entity trails behind when the player turns.  This circle is part of
the held book's own model, so it is always exactly where the book is.

  * crouch (spell selection): the circle flares out behind the book and fades (0.9 s)
  * hold Use (charging): the circle stays open behind the opened book and spins faster

Driven entirely by Molang in the attachable: v.sel (time since the last crouch press) and v.open
(the hold value the books already compute).  tools/assets/books_zfix.py then re-centres the circle on
the posed book (closed: behind the back cover; open: under the pages) and sets its size.
"""
from __future__ import annotations

import contextlib
import math

from kit import tex
from kit.anim import Anim, M

# pre_animation lines (appended after the book's own v.open lines).  Timed with q.delta_time like the
# verified open / close lines (no q.life_time).
#   v.sel  0 -> 1 over 0.9 s after a crouch press; a press while the circle shows re-pulses it
#   v.aura circle scale: crouch flare (spread out 0.15 s, hold, shrink away) or the charge hold
#   v.spin1 / v.spin2 ring angles, integrated so a speed change never makes them jump
SEL_PRE_ANIMATION = [
    "v.press = q.is_sneaking && !(v.was_sneak ?? 0.0);",
    "v.s0 = v.sel ?? 1.0;",
    "v.sel = v.press ? (v.s0 < 1.0 ? math.min(v.s0, 0.17) : 0.0) : math.min(v.s0 + q.delta_time / 0.9, 1.0);",
    "v.was_sneak = q.is_sneaking;",
    "v.flare = v.sel < 0.17 ? math.sin(v.sel / 0.17 * 90.0) * 1.1 : "
    "(v.sel < 0.67 ? 1.1 - 0.2 * (v.sel - 0.17) : math.cos((v.sel - 0.67) / 0.33 * 90.0));",
    "v.aura = math.max(v.sel < 1.0 ? v.flare : 0.0, v.open * 0.9);",
    "v.spin1 = math.mod((v.spin1 ?? 0.0) + q.delta_time * (35.0 + 150.0 * v.open + 320.0 * (1.0 - v.sel)), 360.0);",
    "v.spin2 = math.mod((v.spin2 ?? 0.0) - q.delta_time * (55.0 + 120.0 * v.open + 240.0 * (1.0 - v.sel)), 360.0);",
]


def _extent(model):
    """Bind-pose extent of every cube (raw origins and sizes; good enough for an upright book)."""
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for name in model.order:
        for c in model.bones[name].cubes:
            for i in range(3):
                lo[i] = min(lo[i], c.origin[i])
                hi[i] = max(hi[i], c.origin[i] + c.size[i])
    return lo, hi


def add_aura(model, parent, script, color, color2, star=6, density=None):
    """Add the circle bones to a held-book model (before it is saved).  The book is modelled upright
    with its front cover facing -Z (toward the camera in first person), so the circle stands just
    behind it (+Z), parallel to the cover, and its front face looks the same way as the cover."""
    lo, hi = _extent(model)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    height = hi[1] - lo[1]
    z = hi[2] + max(0.6, height * 0.04)
    d = height * 1.45
    outer = tex.magic_circle(script, color, color2, glow=1.0, bands=((0.74, 0.95, 20),), lines=(0.72, 0.98),
                             star=star, star_r=(0.3, 0.66), key=f"aura_outer_{model.name}")
    inner = tex.magic_circle(script, color2, color, glow=1.0, bands=((0.62, 0.92, 12),), lines=(0.6, 0.95),
                             key=f"aura_inner_{model.name}")
    if density is not None:
        outer = outer.but(density=density)
        inner = inner.but(density=density)
    a = model.bone("aura", parent, pivot=(cx, cy, z))
    r1 = model.bone("aura_ring", "aura", pivot=(cx, cy, z))
    r1.plane("z", (cx, cy, z), d, d, outer)
    r2 = model.bone("aura_ring2", "aura", pivot=(cx, cy, z - 0.2))
    r2.plane("z", (cx, cy, z - 0.2), d * 0.62, d * 0.62, inner)
    return a


def aura_anim():
    """Always-on animation: scale from v.aura (books_zfix adds the size factor and the open glide),
    rings spin faster while charging and whirl for a moment on crouch."""
    an = Anim("aura", loop=True)
    an.scl("aura", M("v.aura", lambda t: 0.0))
    an.rot("aura_ring", (0, 0, M("v.spin1", lambda t: t * 35)))
    an.rot("aura_ring2", (0, 0, M("v.spin2", lambda t: -t * 55)))
    return an


AURA_BONES = ("aura", "aura_ring", "aura_ring2")


@contextlib.contextmanager
def without_aura(model):
    """Hide the circle bones while an inventory / pack icon is rendered from the model (the icon
    renderers draw the bind pose, where the circle is not scaled away)."""
    saved = {n: model.bones.pop(n) for n in AURA_BONES if n in model.bones}
    order = list(model.order)
    model.order[:] = [n for n in model.order if n not in saved]
    try:
        yield model
    finally:
        model.bones.update(saved)
        model.order[:] = order
