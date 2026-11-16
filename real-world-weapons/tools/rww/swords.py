"""
The three historical swords as Bedrock cube models, plus their per-tier painters.

Scale: 1 model unit = 5 cm.  (The Bedrock player model is 32 units tall and its
arm 12 units long; Capoferro's rule "the sword twice the length of the arm"
then gives a 24-unit / 122 cm rapier, matching the museum specimens.)
Lengths follow the reference proportions in docs/historical_references.md.
Minecraft adaptations (documented there too): blade widths x1.2-1.25 and
thicknesses x1.5-2 for legibility; grips and guards enlarged to fit the
4x4-unit Minecraft fist.

Model frame (file coordinates): grip/blade along +y, true edge toward -z,
flats facing +-x, the right hand's item pivot at (0, 24, 0).  With the held
pose, the right fist encloses y 23..27 of the grip, so every guard starts at
y >= 27.  Root bones are bound to the holder's item slot.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np

from . import materials as M
from .materials import ITO, LEATHER, METALS, TIERS, hx, mix, ramp, shade, tnoise
from .modelkit import Model, Texel

HAND_Y = 24.0
BINDING = "q.item_slot_to_bone_name(c.item_slot)"
CM = 0.2  # units per cm

# ============================================================================ geometry


def _blade_segments(m: Model, bone, y0: float, y1: float, hw0: float, hw1: float, t0: float, t1: float,
                    n: int, part: str = "blade", s_range=(0.0, 1.0), **meta):
    """Straight tapering blade made of n boxes (centre line x=z=0)."""
    L = (y1 - y0) / n
    for i in range(n):
        f = (i + 0.5) / n
        hw = hw0 + (hw1 - hw0) * f
        ht = t0 + (t1 - t0) * f
        ya = y0 + i * L
        s0 = s_range[0] + (s_range[1] - s_range[0]) * i / n
        s1 = s_range[0] + (s_range[1] - s_range[0]) * (i + 1) / n
        m.add(bone, (-ht / 2, ya, -hw), (ht, L, hw * 2), part, meta=dict(meta, hw=hw, zc=0.0, s0=s0, s1=s1))


def _point(m: Model, bone, y0: float, hw: float, th: float, length: float, steps: int = 3, part="blade", **meta):
    """Symmetric spear point built from shrinking boxes."""
    L = length / steps
    for i in range(steps):
        k = 1 - (i + 1) / (steps + 1)
        w = hw * k
        t = th * (0.6 + 0.4 * k)
        m.add(bone, (-t / 2, y0 + i * L, -w), (t, L, w * 2), part,
              meta=dict(meta, hw=w, zc=0.0, s0=0.97, s1=1.0, point=True))


def build_rapier() -> Model:
    m = Model("geometry.rww.rapier", density=8)
    b = m.bone("rww_rapier", (0, HAND_Y, 0), binding=BINDING)
    # --- grip, ferrules, pommel (hand-adapted: grip 4 units for the Minecraft fist)
    m.add(b, (-0.36, 23.0, -0.42), (0.72, 4.0, 0.84), "grip")
    m.add(b, (-0.45, 22.8, -0.5), (0.9, 0.3, 1.0), "band")
    m.add(b, (-0.45, 26.75, -0.5), (0.9, 0.3, 1.0), "band")
    m.add(b, (-0.58, 21.55, -0.62), (1.16, 1.25, 1.24), "pommel")
    m.add(b, (-0.5, 21.65, -0.5), (1.0, 1.05, 1.0), "pommel", pivot=(0, 22.15, 0), rotation=(0, 45, 0))
    m.add(b, (-0.42, 22.75, -0.42), (0.84, 0.12, 0.84), "pommel")
    m.add(b, (-0.26, 21.2, -0.26), (0.52, 0.38, 0.52), "pommel")
    # --- quillon block (ecusson) and ricasso
    m.add(b, (-0.5, 27.0, -0.55), (1.0, 0.62, 1.1), "block")
    m.add(b, (-0.13, 27.6, -0.31), (0.26, 1.05, 0.62), "ricasso")
    # --- blade: 106 cm incl. ricasso -> 21.2 u; forte 2.4 cm (shown 3 cm), near point ~1.2 cm
    _blade_segments(m, b, 28.6, 47.5, 0.30, 0.13, 0.24, 0.13, 9, s_range=(0.05, 0.97), weapon="rapier")
    _point(m, b, 47.5, 0.13, 0.13, 1.25, 3, weapon="rapier")
    # --- quillons: straight bar with recurved ends (span 6 u, hand-adapted from 22 cm)
    q = (0.3, 0.32)
    m.polyline(b, [(0, 27.3, 0.45), (0, 27.3, 1.9), (0, 27.12, 2.65), (0, 26.82, 3.1)], q, "guard")
    m.polyline(b, [(0, 27.3, -0.45), (0, 27.3, -1.9), (0, 27.48, -2.65), (0, 27.78, -3.1)], q, "guard")
    m.add(b, (-0.22, 26.52, 2.98), (0.44, 0.44, 0.44), "guard")
    m.add(b, (-0.22, 27.66, -3.42), (0.44, 0.44, 0.44), "guard")
    # --- knuckle-bow: front quillon -> pommel, clearing the fist (>= 3.2 units on the knuckle side)
    kb = [(0, 27.25, -1.35), (0, 26.6, -2.75), (0, 25.6, -3.45), (0, 24.4, -3.62), (0, 23.2, -3.45),
          (0, 22.3, -2.7), (0, 21.85, -1.6), (0, 21.85, -0.62)]
    m.polyline(b, kb, (0.3, 0.3), "ring", plane="yz")
    # --- arms of the hilt (pas d'ane): loops beside the ricasso, in the blade plane
    for sgn in (-1, 1):
        m.polyline(b, [(0, 27.55, 0.5 * sgn), (0, 27.75, 1.12 * sgn), (0, 28.2, 1.32 * sgn), (0, 28.6, 1.0 * sgn),
                       (0, 28.68, 0.3 * sgn)], (0.22, 0.22), "ring", plane="yz")
    # --- outer side-ring (x-z plane, outside face = file -x) and swept bars to the knuckle-bow
    m.ellipse(b, (-1.42, 27.3, 0.0), 1.25, 1.5, "xz", 10, (0.24, 0.24), "ring")
    m.polyline(b, [(-2.62, 27.3, -0.5), (-2.62, 26.3, -1.7), (-2.45, 25.2, -2.95), (-1.4, 24.6, -3.55), (-0.15, 24.4, -3.62)],
               (0.24, 0.24), "ring", plane="3d")
    m.polyline(b, [(-2.5, 27.3, 0.75), (-2.66, 25.9, -0.4), (-2.55, 24.1, -2.5), (-1.45, 23.3, -3.42), (-0.15, 23.2, -3.45)],
               (0.24, 0.24), "ring", plane="3d")
    # inner (body side) counter-guard
    m.polyline(b, [(0.45, 27.3, -0.6), (2.35, 26.6, -1.55), (2.4, 25.3, -3.1), (1.2, 24.7, -3.55), (0.15, 24.5, -3.62)],
               (0.22, 0.22), "ring", plane="3d")
    return m


def build_zweihander() -> Model:
    m = Model("geometry.rww.zweihander", density=8)
    b = m.bone("rww_zweihander", (0, HAND_Y, 0), binding=BINDING)
    # --- grip: 8.6 u (43 cm; specimens 40-49 cm) - room for two Minecraft fists
    m.add(b, (-0.42, 18.4, -0.46), (0.84, 8.6, 0.92), "grip")
    m.add(b, (-0.5, 22.3, -0.54), (1.0, 0.5, 1.08), "grip_band")     # mid swelling / wire band
    m.add(b, (-0.5, 26.6, -0.54), (1.0, 0.4, 1.08), "grip_band")     # ferrule under the cross
    # --- pommel: pear-shaped, ~8 cm
    m.add(b, (-0.62, 17.0, -0.66), (1.24, 1.0, 1.32), "pommel")
    m.add(b, (-0.52, 16.6, -0.52), (1.04, 1.5, 1.04), "pommel", pivot=(0, 17.35, 0), rotation=(0, 45, 0))
    m.add(b, (-0.45, 18.0, -0.48), (0.9, 0.42, 0.96), "pommel")
    m.add(b, (-0.3, 16.3, -0.3), (0.6, 0.35, 0.6), "pommel")
    # --- cross guard: 50 cm span -> 10 u, 3 cm thick bar
    m.add(b, (-0.3, 27.0, -4.3), (0.6, 0.6, 8.6), "guard")
    m.add(b, (-0.42, 26.9, -0.62), (0.84, 0.8, 1.24), "guard")       # centre block (ecusson)
    for sgn in (-1, 1):
        m.polyline(b, [(0, 27.3, 4.1 * sgn), (0, 27.55, 4.6 * sgn), (0, 28.0, 4.9 * sgn)], (0.5, 0.5), "guard", plane="yz")
        m.add(b, (-0.3, 27.9, 4.9 * sgn - 0.3), (0.6, 0.6, 0.6), "guard")
    # side rings: one on each face, parallel to the flat, enclosing the ricasso base
    for sgn in (-1, 1):
        m.ellipse(b, (0.72 * sgn, 28.7, 0.0), 1.05, 1.05, "yz", 10, (0.26, 0.26), "ring", start=-90, end=270)
    # --- ricasso (28 cm -> 5.6 u), leather covered, studded
    m.add(b, (-0.23, 27.6, -0.47), (0.46, 5.6, 0.94), "ricasso_leather")
    for yy in (28.6, 30.0, 31.4, 32.6):
        for sgn in (-1, 1):
            m.add(b, (0.21 * sgn - 0.06, yy, -0.08), (0.12, 0.16, 0.16), "stud")
    # --- parrying hooks (Parierhaken) at the top of the ricasso, angled toward the point
    for sgn in (-1, 1):
        m.polyline(b, [(0, 33.15, 0.45 * sgn), (0, 33.4, 1.2 * sgn), (0, 33.95, 1.6 * sgn), (0, 34.55, 1.62 * sgn)],
                   (0.32, 0.36), "hook", plane="yz")
    # --- blade beyond the hooks: 94 cm -> 18.8 u; 4.5 cm -> ~3 cm (shown x1.15)
    _blade_segments(m, b, 33.2, 50.4, 0.52, 0.35, 0.36, 0.24, 10, s_range=(0.0, 0.96), weapon="zweihander")
    _point(m, b, 50.4, 0.35, 0.24, 1.6, 3, weapon="zweihander")
    return m


KATANA_SORI = 0.40      # 2.0 cm (Edo specimens 1.5-2.0 cm)
KATANA_NAGASA = 14.2    # 71 cm


def katana_arc():
    """Centre line of the blade: circle with base tangent along +y, curving toward +z (mune)."""
    L, s = KATANA_NAGASA, KATANA_SORI
    R = L * L / (8 * s) + s / 2
    total = 2 * math.asin(L / (2 * R))
    return R, total


def build_katana() -> Model:
    m = Model("geometry.rww.katana", density=8)
    b = m.bone("rww_katana", (0, HAND_Y, 0), binding=BINDING)
    y_machi = 27.41
    # --- tsuka: hand-adapted to 7.2 u for two Minecraft fists (real 26 cm -> 5.2 u)
    m.add(b, (-0.33, 19.4, -0.43), (0.66, 7.2, 0.86), "tsuka")
    m.add(b, (-0.36, 18.95, -0.47), (0.72, 0.45, 0.94), "kashira")
    m.add(b, (-0.28, 18.82, -0.38), (0.56, 0.13, 0.76), "kashira")
    m.add(b, (-0.38, 26.6, -0.49), (0.76, 0.34, 0.98), "fuchi")
    for sgn, yy in ((1, 22.1), (-1, 23.0)):        # menuki (omote / ura), offset as on real tsuka
        m.add(b, (0.33 * sgn - 0.06, yy, -0.28), (0.12, 0.62, 0.42), "menuki")
    # --- seppa + tsuba (iron, ~7.8 x 7.2 cm; enlarged to sit against the fist)
    m.add(b, (-0.62, 26.94, -0.72), (1.24, 0.06, 1.44), "seppa")
    m.add(b, (-1.3, 27.0, -0.75), (2.6, 0.35, 1.5), "tsuba")
    m.add(b, (-0.78, 27.0, -1.4), (1.56, 0.35, 2.8), "tsuba")
    m.add(b, (-1.0, 27.0, -1.0), (2.0, 0.35, 2.0), "tsuba", pivot=(0, 27.175, 0), rotation=(0, 45, 0))
    m.add(b, (-0.62, 27.35, -0.72), (1.24, 0.06, 1.44), "seppa")
    # --- habaki (3.5 cm)
    m.add(b, (-0.19, 27.41, -0.45), (0.38, 0.7, 0.9), "habaki")
    # --- curved blade (shinogi-zukuri), torii-zori
    R, total = katana_arc()
    n = 11
    kissaki_len = 0.8
    blade_len_arc = R * total
    usable = blade_len_arc - kissaki_len
    for i in range(n):
        a0 = (usable * i / n) / R
        a1 = (usable * (i + 1) / n) / R
        am = (a0 + a1) / 2
        p0 = np.array([y_machi + R * math.sin(a0), R * (1 - math.cos(a0))])
        p1 = np.array([y_machi + R * math.sin(a1), R * (1 - math.cos(a1))])
        mid = (p0 + p1) / 2
        f = (i + 0.5) / n
        hw = 0.36 + (0.26 - 0.36) * f
        ht = 0.24 + (0.18 - 0.24) * f
        L = float(np.linalg.norm(p1 - p0)) + 0.06
        m.add(b, (-ht / 2, mid[0] - L / 2, mid[1] - hw), (ht, L, hw * 2), "blade",
              pivot=(0, mid[0], mid[1]), rotation=(-math.degrees(am), 0, 0),
              meta=dict(weapon="katana", hw=hw, zc=float(mid[1]), yc=float(mid[0]), s0=a0 / total, s1=a1 / total))
    # --- kissaki (chu-kissaki ~3.3 cm, shown 4 cm): edge side rises (fukura) toward the mune-side tip
    a_start = usable / R
    hw = 0.26
    ht = 0.18
    steps = 3
    for i in range(steps):
        a0 = a_start + (kissaki_len * i / steps) / R
        a1 = a_start + (kissaki_len * (i + 1) / steps) / R
        am = (a0 + a1) / 2
        p0 = np.array([y_machi + R * math.sin(a0), R * (1 - math.cos(a0))])
        p1 = np.array([y_machi + R * math.sin(a1), R * (1 - math.cos(a1))])
        mid = (p0 + p1) / 2
        k = [0.86, 0.6, 0.3][i]
        w = hw * k
        # keep the mune (+z side) line straight: shift centre toward +z as the edge recedes
        normal = np.array([-math.sin(am), math.cos(am)])   # (dy, dz) pointing toward +z (mune)
        c = mid + normal * (hw - w)
        L = float(np.linalg.norm(p1 - p0)) + 0.05
        m.add(b, (-ht / 2 * (1 - 0.15 * i), c[0] - L / 2, c[1] - w), (ht * (1 - 0.15 * i), L, w * 2), "blade",
              pivot=(0, c[0], c[1]), rotation=(-math.degrees(am), 0, 0),
              meta=dict(weapon="katana", hw=w, zc=float(c[1]), yc=float(c[0]), s0=a0 / total, s1=a1 / total,
                        kissaki=True))
    return m


BUILDERS = {"rapier": build_rapier, "zweihander": build_zweihander, "katana": build_katana}

# ============================================================================ painters


def _across(t: Texel) -> float:
    """-1 (edge side, -z) .. +1 (back side, +z) across the blade width, in the box's own frame."""
    hw = t.box.meta.get("hw", 0.3)
    zc = t.box.origin[2] + t.box.size[2] / 2
    return float(np.clip((t.p[2] - zc) / hw, -1, 1))


def _along(t: Texel) -> float:
    s0, s1 = t.box.meta.get("s0", 0.0), t.box.meta.get("s1", 1.0)
    y0, y1 = t.box.origin[1], t.box.origin[1] + t.box.size[1]
    f = (t.p[1] - y0) / max(1e-6, (y1 - y0))
    return s0 + (s1 - s0) * float(np.clip(f, 0, 1))


def blade_painter(tier_key: str, weapon: str):
    tier = TIERS[tier_key]
    d, mcol, l, h = tier.blade

    def straight(t: Texel):
        w = _across(t)          # -1..1 (edges at both ends for straight blades)
        s = _along(t)
        aw = abs(w)
        n = tnoise(t, 11)
        if tier.kind == "wood":
            c = M.wood_paint(M.METALS["wood_light"] if tier_key == "wooden" else M.METALS["wood_dark"], t, 3)
            if t.face in ("north", "south"):
                c = shade(c, 0.08)
            return c
        if t.face in ("north", "south"):            # the edges
            c = mix(l, h, 0.6)
            if tier.kind == "stone" and n > 0.7:
                c = shade(d, 0.05)                    # knapped / chipped edge
            return c
        if t.face in ("up", "down"):
            return mcol
        # flats (east / west)
        if weapon == "rapier":
            prof = 1 - aw                              # flattened diamond: ridge in the middle
            c = ramp([d, mcol, l, h], 0.25 + 0.6 * prof)
            if s < 0.14 and aw < 0.22:                 # single short fuller at the forte
                c = shade(d, -0.15) if aw < 0.12 else shade(mcol, -0.1)
            if aw > 0.84:
                c = mix(c, h, 0.55)                    # honed bevel
        else:                                          # zweihander: hexagonal section
            if aw < 0.34:
                c = ramp([mcol, l], 0.45 + 0.3 * (1 - aw / 0.34))
            else:
                c = ramp([l, mcol, d], (aw - 0.34) / 0.66 * 0.8)
                if aw > 0.86:
                    c = mix(c, h, 0.6)
            if 0.05 < s < 0.13 and aw < 0.3 and tier_key in ("iron", "golden", "netherite"):
                c = mix(c, (M.hx("c79422") if tier_key != "golden" else M.hx("8a5e10")), 0.45)   # etched band
        c = shade(c, 0.06 * (1 - s) - 0.05 * s)
        if tier.kind == "stone":
            c = shade(c, (n - 0.5) * 0.22)
            if n > 0.93:
                c = shade(d, -0.2)
        elif tier.kind == "gem":
            band = math.sin((t.p[1] * 2.2 + w * 3.0)) > 0.72
            if band:
                c = mix(c, h, 0.45)
            if n > 0.975:
                c = (255, 255, 255, 255)
        elif tier_key == "copper":
            if n > 0.965:
                c = mix(c, M.hx("4fa58a"), 0.55)       # verdigris speckles
        elif tier_key == "netherite":
            c = shade(c, (n - 0.5) * 0.08)
            if n > 0.985:
                c = mix(c, M.hx("8e6f87"), 0.5)
        else:
            c = shade(c, (n - 0.5) * 0.05)
        return c

    def katana(t: Texel):
        w = _across(t)          # -1 = ha (edge, -z), +1 = mune (+z)
        s = _along(t)
        n = tnoise(t, 21)
        kis = t.box.meta.get("kissaki", False)
        if tier.kind == "wood":                        # bokken: plain wood, no hamon
            c = M.wood_paint(M.METALS["wood_light"], t, 4)
            if t.face == "north":
                c = shade(c, 0.06)
            return c
        if t.face == "north":                          # ha (cutting edge)
            return mix(l, h, 0.7) if tier.kind != "stone" else mix(mcol, l, 0.5)
        if t.face == "south":                          # mune (iori-mune): ridge highlight
            return ramp([d, mcol, l], 0.4 + 0.4 * (1 - abs(t.fu - 0.5) * 2))
        if t.face in ("up", "down"):
            return mcol
        # flats: shinogi line at w = +0.36, hamon boundary wavy (notare with gunome)
        y = float(t.p[1])
        hamon = -1 + 0.52 + 0.09 * math.sin(y * 3.1) + 0.05 * math.sin(y * 7.3 + 1.3)
        if kis:
            hamon = -1 + 0.62                          # boshi follows the fukura
        shinogi = 0.36
        if tier.kind == "stone":
            c = ramp([d, mcol, l], 0.35 + 0.4 * (1 - abs(w)) + (n - 0.5) * 0.25)
            if w < -0.7:
                c = mix(c, l, 0.4)
            return c
        if w < hamon:                                  # hamon (hardened edge) — misty white
            k = (w + 1) / max(0.05, (hamon + 1))
            c = mix(h, l, 0.35 + 0.4 * k)
            if k > 0.82 and n > 0.45:
                c = mix(c, (255, 255, 255, 255), 0.35)   # nie crystals along the boundary
        elif w < shinogi:                              # hira-ji: darker steel with grain
            c = ramp([d, mcol, l], 0.38 + 0.25 * ((w - hamon) / (shinogi - hamon + 1e-6)) + (n - 0.5) * 0.12)
        else:                                          # shinogi-ji: burnished, slightly darker
            c = ramp([d, mcol], 0.55 + (n - 0.5) * 0.1)
        if abs(w - shinogi) < 0.09:
            c = mix(c, h, 0.55)                        # shinogi ridge line
        if kis and t.box.meta.get("s0", 0) < 0.97 and t.y < 1:
            c = mix(c, h, 0.6)                         # yokote
        if tier.kind == "gem" and n > 0.975:
            c = (255, 255, 255, 255)
        if tier_key == "netherite" and w < hamon:
            c = mix(c, M.hx("8a6c84"), 0.35)
        return c

    return katana if weapon == "katana" else straight


def painters(weapon: str, tier_key: str) -> Dict[str, callable]:
    tier = TIERS[tier_key]
    blade = blade_painter(tier_key, weapon)

    def pal_metal(name):
        pal = METALS[name]

        def p(t):
            if name.startswith("wood"):
                return M.wood_paint(pal, t, 5)
            if name.startswith("stone"):
                return M.stone_paint(pal, t, 6)
            return M.metal_paint(pal, t, 7)
        return p

    # ---------------------------------------------------------------- choose fittings per tier
    if weapon == "rapier":
        hilt = {"wooden": "wood_dark", "stone": "stone_dark", "copper": "bronze", "iron": "blued",
                "golden": "gilt", "diamond": "silver", "netherite": "blackened"}[tier_key]
        wire = {"wooden": "tan", "stone": "brown", "copper": "copper", "iron": "silver", "golden": "gilt",
                "diamond": "silver", "netherite": "gilt"}[tier_key]
        hilt_p = pal_metal(hilt)
        inlay = tier_key in ("netherite", "iron", "diamond")
        inlay_col = {"netherite": M.hx("d6a84a"), "iron": M.hx("c9ced6"), "diamond": M.hx("5fe3da")}.get(tier_key)

        def guard(t):
            c = hilt_p(t)
            if inlay and tnoise(t, 31) > 0.9 and t.face not in ("up", "down"):
                c = mix(c, inlay_col, 0.75)          # silver / gold encrustation dots
            return c

        def grip(t):
            if wire in ("tan", "brown"):
                return M.leather_paint(LEATHER[wire], t, 8)
            pal = METALS[wire]
            q = int(math.floor(t.p[1] * 8 + (t.p[0] + t.p[2]) * 4 + 1e-4))
            c = ramp([pal[0], pal[1], pal[2], pal[3]], 0.35 + 0.45 * (q % 3 == 1) + 0.2 * (q % 3 == 2))
            if q % 6 == 0:
                c = shade(pal[0], -0.2)               # twisted & braided wire rows
            return c

        def band(t):
            pal = METALS[wire] if wire not in ("tan", "brown") else METALS[hilt]
            q = int(math.floor(t.p[1] * 8 + 1e-4)) + int(math.floor((t.p[0] + t.p[2]) * 8 + 1e-4))
            return ramp([pal[0], pal[2], pal[3]], 0.4 + 0.5 * (q % 2))   # Turk's head braid

        def ricasso(t):
            c = blade(t)
            if t.face in ("east", "west") and 0.3 < t.fv < 0.7 and 0.3 < t.fu < 0.7 and tier.kind == "metal":
                c = shade(c, -0.35)                   # maker's mark punched on the ricasso
            return c
        return {"blade": blade, "ricasso": ricasso, "grip": grip, "band": band, "pommel": guard, "block": guard,
                "guard": guard, "ring": guard}

    if weapon == "zweihander":
        hilt = {"wooden": "wood_dark", "stone": "stone_dark", "copper": "bronze", "iron": "blackened",
                "golden": "gilt", "diamond": "steel", "netherite": "netherite"}[tier_key]
        leather = {"wooden": "tan", "stone": "brown", "copper": "brown", "iron": "black", "golden": "red",
                   "diamond": "black", "netherite": "red"}[tier_key]
        hilt_p = pal_metal(hilt)
        stud_pal = METALS["gilt"] if tier_key in ("golden", "netherite") else METALS["steel"]

        def grip(t):
            # black leather spirally wrapped over the wooden core (Wallace A472: "bound with black leather")
            pal = LEATHER[leather]
            c = M.leather_paint(pal, t, 9)
            q = int(math.floor(t.p[1] * 8 + (t.p[0] - t.p[2]) * 5 + 1e-4))
            if q % 5 == 0:
                c = shade(pal[0], -0.15)          # seam between wraps
            elif q % 5 == 1:
                c = mix(c, pal[3], 0.35)          # raised edge catching the light
            return c

        def band(t):
            pal = METALS["gilt"] if tier_key in ("golden", "netherite") else (METALS["steel"] if tier.kind != "wood" else METALS["wood_dark"])
            q = int(math.floor(t.p[1] * 8 + (t.p[0] + t.p[2]) * 6 + 1e-4))
            return ramp([pal[0], pal[2], pal[3]], 0.3 + 0.6 * (q % 2))

        def ricasso_leather(t):
            if t.face in ("up", "down"):
                return LEATHER[leather][1]
            return M.leather_paint(LEATHER[leather], t, 10, stitch=t.face in ("north", "south"))

        def stud(t):
            return M.metal_paint(stud_pal, t, 12)

        def hook(t):
            return blade(t) if tier.kind != "wood" else hilt_p(t)
        return {"blade": blade, "grip": grip, "grip_band": band, "pommel": hilt_p, "guard": hilt_p, "ring": hilt_p,
                "ricasso_leather": ricasso_leather, "stud": stud, "hook": hook}

    # katana
    ito_name = {"wooden": None, "stone": "brown", "copper": "green", "iron": "kon", "golden": "black",
                "diamond": "white", "netherite": "purple"}[tier_key]
    fittings = {"wooden": "wood_light", "stone": "stone_dark", "copper": "copper", "iron": "shakudo",
                "golden": "gilt", "diamond": "shibuichi", "netherite": "shakudo"}[tier_key]
    tsuba_m = {"wooden": "wood_dark", "stone": "stone_dark", "copper": "bronze", "iron": "iron_russet",
               "golden": "gilt", "diamond": "iron_russet", "netherite": "netherite"}[tier_key]
    habaki_m = {"wooden": "wood_light", "stone": "stone", "copper": "copper", "iron": "copper",
                "golden": "gilt", "diamond": "silver", "netherite": "gilt"}[tier_key]
    fit_p = pal_metal(fittings)
    tsuba_p = pal_metal(tsuba_m)
    habaki_p = pal_metal(habaki_m)

    def tsuka(t):
        if ito_name is None:                      # bokken: plain wooden grip
            return M.wood_paint(METALS["wood_light"], t, 13)
        ito = ITO[ito_name]
        period = 1.2
        y = float(t.p[1])
        k = ((y - 19.4) / period) % 1.0
        # position across the face, 0..1
        u = t.fu
        if t.face in ("up", "down"):
            return ito[1]
        # diamond (hishigami) windows showing the white ray-skin (same)
        dd = abs(u - 0.5) * 1.15 + abs(k - 0.5)
        if dd < 0.33:
            n = tnoise(t, 14)
            return mix(hx("e9e4d6"), hx("bdb6a3"), n * 0.8)    # same nodules
        # crossing braid: alternate over/under by diagonal direction
        diag = (u + k) % 1.0 < 0.5
        c = ramp([ito[0], ito[1], ito[2], ito[3]], 0.35 + (0.35 if diag else 0.1) + (tnoise(t, 15) - 0.5) * 0.15)
        if abs(dd - 0.33) < 0.05:
            c = shade(ito[0], -0.2)
        return c

    def menuki(t):
        return M.metal_paint(METALS["gilt"] if tier_key not in ("wooden", "stone") else METALS[fittings], t, 16)

    def tsuba(t):
        c = tsuba_p(t)
        if t.face in ("up", "down"):
            r = math.hypot(t.p[0], t.p[2])
            if r > 1.15:
                c = shade(c, 0.12)                     # raised rim (mimi)
            elif r < 0.55:
                c = shade(c, -0.12)                    # seppa-dai
        return c
    return {"blade": blade, "tsuka": tsuka, "kashira": fit_p, "fuchi": fit_p, "menuki": menuki,
            "seppa": habaki_p, "tsuba": tsuba, "habaki": habaki_p}
