"""
ODDWORKS Set 01 models.

All held-item geometries use bound bones (vanilla convention): coordinates are authored so
that (0, 24, 0) is the hand pivot (main hand) - see modelkit's binding quirk notes. Head-bound
bones use player-model coordinates directly (head pivot (0, 24, 0) cancels the quirk).
"""
from __future__ import annotations

import math

import materials as mt
from modelkit import Model, flat, hx, solid, with_alpha

D_FINE = 4.0      # texels per unit for held items (fine carving detail)


# =========================================================================== 001 Solar Frost Goggles

def _goggle_band(m: Model, parent: str, tag: str, with_strap: bool):
    """The carved antler band (front at z = -5.25 .. -4.55), slits at y 27.9 .. 28.3."""
    ant = mt.antler()
    z0, th = -5.25, 0.7
    band = m.bone(f"{tag}band", (0, 28, -4.9), parent)
    band.add((-3.3, 28.3, z0), (6.6, 1.3, th), ant)                    # upper bar (engraved)
    band.add((-3.3, 26.95, z0), (2.7, 0.95, th), ant)                  # lower bar right of nose
    band.add((0.6, 26.95, z0), (2.7, 0.95, th), ant)                   # lower bar left of nose
    band.add((-0.6, 27.55, z0), (1.2, 0.8, th), ant)                   # bridge between slits
    band.add((-3.3, 27.9, z0), (0.3, 0.4, th), ant)                    # outer slit ends
    band.add((3.0, 27.9, z0), (0.3, 0.4, th), ant)
    band.add((-3.6, 29.35, z0 - 0.35), (7.2, 0.4, 0.55), mt.antler(engrave=False, patina=0.5))   # brow visor
    # sun-ice lenses recessed in the slits (emissive via low alpha)
    lens = m.bone(f"{tag}lenses", (0, 28.1, -4.9), f"{tag}band")
    lens.add((0.6, 27.9, z0 + 0.22), (2.4, 0.4, 0.3), mt.sun_ice())
    lens.add((-3.0, 27.9, z0 + 0.22), (2.4, 0.4, 0.3), mt.sun_ice())
    # charging glow sheets in front of the slits (scaled up by the charge animation)
    glow = m.bone(f"{tag}glow", (0, 28.1, -5.3), f"{tag}band")
    glow.add((0.45, 27.8, z0 - 0.08), (2.7, 0.6, 0.02), flat("ffd060" + "40"), faces=("north",))
    glow.add((-3.15, 27.8, z0 - 0.08), (2.7, 0.6, 0.02), flat("ffd060" + "40"), faces=("north",))
    full = m.bone(f"{tag}glow_full", (0, 28.1, -5.3), f"{tag}band")
    full.add((0.35, 27.75, z0 - 0.1), (2.9, 0.7, 0.02), flat("e8fbff" + "30"), faces=("north",))
    full.add((-3.25, 27.75, z0 - 0.1), (2.9, 0.7, 0.02), flat("e8fbff" + "30"), faces=("north",))
    # temple wings wrap back around the face
    wl = m.bone(f"{tag}wing_l", (3.3, 28.3, z0), f"{tag}band", rotation=(0, -35, 0))
    wl.add((3.3, 26.95, z0), (1.6, 2.65, th), ant)
    wr = m.bone(f"{tag}wing_r", (-3.3, 28.3, z0), f"{tag}band", rotation=(0, 35, 0))
    wr.add((-4.9, 26.95, z0), (1.6, 2.65, th), ant)
    if with_strap:
        st = m.bone(f"{tag}strap", (0, 28, 0), f"{tag}band")
        seal, cord = mt.sealskin(), mt.sinew()
        st.add((4.62, 27.75, -4.45), (0.3, 0.9, 9.05), seal)
        st.add((-4.92, 27.75, -4.45), (0.3, 0.9, 9.05), seal)
        st.add((-4.92, 27.75, 4.6), (9.84, 0.9, 0.3), seal)
        st.add((4.45, 27.85, -4.85), (0.5, 0.7, 0.5), cord)            # sinew lashings
        st.add((-4.95, 27.85, -4.85), (0.5, 0.7, 0.5), cord)
        st.add((-0.4, 27.7, 4.75), (0.8, 1.0, 0.35), cord)              # knot at the back


def goggles() -> Model:
    m = Model("geometry.oddworks.solar_frost_goggles", density=D_FINE, seed=11)
    m.bounds = (2.5, 2.5, 1.5)
    # third person: bound to the head, worn on the forehead / pulled over the eyes
    m.bone("tp_root", (0, 28, -4.9), binding="q.item_slot_to_bone_name('head')")
    _goggle_band(m, "tp_root", "tp_", with_strap=True)
    # first person: held in the hand ...
    m.bone("fp_root", (0, 28, -4.9), binding="q.item_slot_to_bone_name('main_hand')")
    _goggle_band(m, "fp_root", "fp_", with_strap=False)
    hang = m.bone("fp_cord", (0, 28, -4.9), "fp_root")
    hang.add((4.4, 27.0, -4.95), (0.3, 2.2, 0.3), mt.sinew())
    hang.add((-4.7, 27.0, -4.95), (0.3, 2.2, 0.3), mt.sinew())
    # ... and the inside view while charging: soot-black inner face of the goggles framing one
    # fused horizontal slit (binocular view through both eye slits). Centred on the pivot so the
    # animation can park it in front of the camera; faces south (towards the wearer).
    mask = m.bone("fp_mask", (0, 28, -4.9), binding="q.item_slot_to_bone_name('main_hand')")
    inner = mt.antler()
    # slightly see-through (alpha blended) so the world stays readable even off-centre
    soot = lambda f: with_alpha(f.jitter(hx("1c1714"), 0.05), 215)
    big_w, big_h = 72.0, 34.0
    slit = 3.6
    mask.add((-big_w / 2, 28 + slit / 2, -4.9), (big_w, big_h / 2 - slit / 2, 0.05), soot, faces=("south",),
             density=0.5)
    mask.add((-big_w / 2, 28 - big_h / 2, -4.9), (big_w, big_h / 2 - slit / 2, 0.05), soot, faces=("south",),
             density=0.5)
    rim = m.bone("fp_mask_rim", (0, 28, -4.95), "fp_mask")
    rim.add((-big_w / 2, 28 + slit / 2 - 0.35, -4.95), (big_w, 0.35, 0.05), mt.sun_ice(55), faces=("south",),
            density=1.0)
    rim.add((-big_w / 2, 28 - slit / 2, -4.95), (big_w, 0.35, 0.05), mt.sun_ice(55), faces=("south",),
            density=1.0)
    carve = m.bone("fp_mask_carve", (0, 28, -4.98), "fp_mask")
    carve.add((-1.4, 28 - big_h / 2, -4.98), (2.8, big_h / 2 - slit / 2 - 0.2, 0.05), inner, faces=("south",),
              density=1.0)
    return m


# =========================================================================== 002 Endless Handline

def _octa(bone, cx, cz, y0, h, r, paint, density=None):
    """Octagonal prism around a vertical axis: four (2r x s) slabs at 0/45/90/135 degrees.
    Each slab is a hair shorter than the previous so the coplanar caps never z-fight."""
    s = 2 * r * math.tan(math.pi / 8)
    for i, (w, d, rot) in enumerate(((2 * r, s, 0), (s, 2 * r, 0), (2 * r, s, 45), (s, 2 * r, 45))):
        e = 0.012 * i
        kw = {"density": density}
        if rot:
            kw.update(pivot=(cx, y0, cz), rotation=(0, rot, 0))
        bone.add((cx - w / 2, y0 + e, cz - d / 2), (w, h - 2 * e, d), paint, **kw)


def handline(cast: bool = False) -> Model:
    m = Model("geometry.oddworks.endless_handline" + ("_cast" if cast else ""), density=D_FINE, seed=23)
    m.bounds = (3.0, 3.0, 1.0)
    root = m.bone("reel", (0, 24, 0), binding="q.item_slot_to_bone_name(c.item_slot)")
    wood = mt.turned_wood(axis="y")
    handle = m.bone("handle", (0, 24, 0), "reel")
    _octa(handle, 0, 0, 20.3, 4.9, 0.8, wood)                            # short turned handle
    _octa(handle, 0, 0, 19.6, 0.75, 1.05, mt.turned_wood(base="7c4522", axis="y"))   # pommel
    handle.add((-1.05, 22.2, -1.05), (2.1, 0.3, 2.1), mt.brass())       # brass ferrule ring
    drum = m.bone("drum", (0, 27.1, 0), "handle")
    flange = mt.turned_wood(base="8a4f26", dark="5a2f14", axis="y")
    _octa(drum, 0, 0, 25.2, 0.55, 3.0, flange)                           # lower flange
    _octa(drum, 0, 0, 28.45, 0.55, 3.0, flange)                          # upper flange
    _octa(drum, 0, 0, 25.75, 2.7, 1.55, wood)                            # core
    _octa(drum, 0, 0, 25.85, 2.5, 2.35 if not cast else 1.85, mt.line_windings(wind_axis="y"))
    drum.add((-0.9, 28.98, -0.9), (1.8, 0.12, 1.8), mt.pearl())         # mother-of-pearl inlay cap
    drum.add((-0.25, 28.6, -3.35), (0.5, 0.5, 0.45), mt.brass())         # brass line guide
    if not cast:
        whirl = m.bone("whirl", (0, 29.0, 0), "drum")
        rig = m.bone("sinker_rig", (0, 28.85, -3.15), "whirl")
        line = m.bone("line", (0, 28.85, -3.15), "sinker_rig")
        line.add((-0.07, 25.6, -3.22), (0.14, 3.25, 0.14), flat("efe6cf"))   # line stub
        weight = m.bone("weight", (0, 25.6, -3.15), "sinker_rig")
        _octa(weight, 0, -3.15, 24.1, 1.55, 0.55, mt.lead())                  # egg sinker
        weight.add((-0.32, 24.35, -3.47), (0.64, 1.05, 0.64), mt.lead())
        hook = m.bone("hook", (0, 24.1, -3.15), "weight")
        steel = mt.iron()
        hook.add((-0.06, 22.2, -3.21), (0.12, 1.9, 0.12), steel)              # shank
        hook.add((-0.06, 22.05, -3.21), (0.75, 0.15, 0.12), steel)            # bend
        hook.add((0.6, 22.05, -3.21), (0.12, 0.85, 0.12), steel)              # point
        hook.add((0.42, 22.75, -3.21), (0.2, 0.12, 0.12), steel)              # barb
    else:
        # empty rig bones so the shared reel animations resolve on the line-out model too
        m.bone("whirl", (0, 29.0, 0), "drum")
        m.bone("sinker_rig", (0, 28.85, -3.15), "whirl")
        m.bone("line", (0, 28.85, -3.15), "sinker_rig")
        m.bone("weight", (0, 25.6, -3.15), "sinker_rig")
    return m


def handline_sinker() -> Model:
    """Thrown sinker + hook (entity oddworks:handline_hook). Origin at the sinker centre."""
    m = Model("geometry.oddworks.handline_hook", density=D_FINE, seed=29)
    m.bounds = (1.0, 1.0, 0.25)
    b = m.bone("body", (0, 1.5, 0))
    _octa(b, 0, 0, 0.6, 1.8, 0.62, mt.lead())
    b.add((-0.36, 0.85, -0.36), (0.72, 1.3, 0.72), mt.lead())
    steel = mt.iron()
    hook = m.bone("hook", (0, 0.6, 0), "body")
    hook.add((-0.07, -1.5, -0.07), (0.14, 2.1, 0.14), steel)
    hook.add((-0.07, -1.65, -0.07), (0.85, 0.15, 0.14), steel)
    hook.add((0.71, -1.65, -0.07), (0.14, 0.95, 0.14), steel)
    hook.add((0.5, -0.88, -0.07), (0.24, 0.14, 0.14), steel)
    eye = m.bone("eye", (0, 2.4, 0), "body")
    eye.add((-0.25, 2.35, -0.08), (0.5, 0.45, 0.16), mt.brass())
    return m


def handline_bobber() -> Model:
    """Float used when the line rests on water: cork body, red tip, glowing line eye."""
    m = Model("geometry.oddworks.handline_bobber", density=D_FINE, seed=31)
    m.bounds = (1.0, 1.0, 0.25)
    b = m.bone("body", (0, 0, 0))
    _octa(b, 0, 0, -0.9, 1.4, 1.0, solid("e9e2cf", 0.05))
    _octa(b, 0, 0, 0.5, 1.0, 0.85, solid("c8262b", 0.05))
    b.add((-0.3, 1.5, -0.3), (0.6, 0.9, 0.6), solid("e9e2cf", 0.05))
    b.add((-0.12, 2.4, -0.12), (0.24, 0.45, 0.24), flat("7fe0d0" + "60"))
    return m


# =========================================================================== 003 Bamboo Sword Cane

NODES_SHEATH = (11.0, 15.0, 18.9)
NODES_HANDLE = (22.6, 26.3)


def _cane_parts(m: Model, parent: str, drawn: bool):
    """Handle (with blade) in the hand; sheath from y 7.0 to 21.0 when sheathed."""
    handle = m.bone("handle", (0, 24, 0), parent)
    hb = mt.bamboo(nodes=NODES_HANDLE, smoked=0.45)
    handle.add((-0.8, 21.05, -0.8), (1.6, 6.15, 1.6), hb)                    # grip section
    handle.add((-0.85, 27.2, -0.85), (1.7, 0.45, 1.7), mt.bamboo(nodes=(27.42,), smoked=0.6))   # node cap
    handle.add((-0.86, 21.0, -0.86), (1.72, 0.32, 1.72), mt.lacquer())        # hidden collar (habaki seat)
    cord = m.bone("cord", (0, 26.4, 0.8), "handle")
    cord.add((-0.12, 23.7, 0.8), (0.24, 2.7, 0.24), mt.silk_cord())            # sageo loop hanging
    cord.add((-0.3, 23.3, 0.68), (0.6, 0.45, 0.45), mt.silk_cord("d7b45a", "7a1f2b"))
    blade = m.bone("blade", (0, 21, 0), "handle")
    steel = mt.blade_steel()
    blade.add((-0.45, 8.6, -0.16), (0.9, 12.45, 0.32), steel)                  # slender straight blade
    blade.add((-0.45, 7.75, -0.16), (0.62, 0.9, 0.32), steel)                  # kissaki (tip)
    blade.add((-0.55, 20.55, -0.24), (1.1, 0.45, 0.48), mt.brass(base="b08a3a"))   # habaki collar
    sheath = m.bone("sheath", (0, 21, 0), parent)
    sb = mt.bamboo(nodes=NODES_SHEATH, smoked=0.15)
    sheath.add((-0.78, 7.6, -0.78), (1.56, 13.4, 1.56), sb)
    sheath.add((-0.7, 7.0, -0.7), (1.4, 0.6, 1.4), mt.iron(base="3d3f44", light="8a8f98"))   # ferrule
    return handle, blade, sheath


def cane(drawn: bool) -> Model:
    m = Model("geometry.oddworks.bamboo_sword_cane" + ("_drawn" if drawn else ""), density=D_FINE, seed=41)
    m.bounds = (3.0, 3.5, 1.0)
    m.bone("cane", (0, 24, 0), binding="q.item_slot_to_bone_name(c.item_slot)")
    _cane_parts(m, "cane", drawn)
    if not drawn:
        m.bone("hip_sheath", (0, 21, 0), "cane")       # empty: shared animations stay valid
    if drawn:
        # third person: the emptied sheath is carried in the left hand (iai: saya stays in the off hand)
        hip = m.bone("hip_sheath", (0, 21, 0), binding="q.item_slot_to_bone_name('off_hand')")
        sb = mt.bamboo(nodes=NODES_SHEATH, smoked=0.15)
        hip.add((-0.78, 7.6, -0.78), (1.56, 13.4, 1.56), sb)
        hip.add((-0.7, 7.0, -0.7), (1.4, 0.6, 1.4), mt.iron(base="3d3f44", light="8a8f98"))
    return m


# =========================================================================== entities

def sun_dog() -> Model:
    """Parhelion: a small mock sun with a 22-degree halo ring and two sun-dog glints."""
    m = Model("geometry.oddworks.sun_dog", density=2.0, seed=53)
    m.bounds = (3.0, 3.0, 0.5)
    core = m.bone("core", (0, 6, 0))
    core.add((-1.5, 4.5, -1.5), (3, 3, 3), mt.sun_core(45))
    core.add((-1.0, 5.0, -2.0), (2, 2, 4), mt.sun_core(70))
    core.add((-2.0, 5.0, -1.0), (4, 2, 2), mt.sun_core(70))
    core.add((-1.0, 4.0, -1.0), (2, 4, 2), mt.sun_core(70))
    halo = m.bone("halo", (0, 6, 0), "core")
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = math.cos(a) * 5.0, 6 + math.sin(a) * 5.0
        halo.add((x - 0.6, y - 0.6, -0.05), (1.2, 1.2, 0.1), flat("fff0b0" + "50"), faces=("north", "south"),
                 pivot=(x, y, 0), rotation=(0, 0, math.degrees(a)))
    dogs = m.bone("dogs", (0, 6, 0), "core")
    for sx in (-1, 1):
        dogs.add((sx * 5.0 - 0.7, 5.3, -0.1), (1.4, 1.4, 0.2), flat("ffffff" + "28"), faces=("north", "south"))
    return m


def ice_shell() -> Model:
    """Translucent block of ice that encases a frozen mob (scaled per size class)."""
    m = Model("geometry.oddworks.ice_shell", density=1.0, seed=59)
    m.bounds = (3.0, 4.0, 1.5)
    b = m.bone("shell", (0, 0, 0))
    ice = mt.clear_ice(140)
    b.add((-8, 0, -8), (16, 16, 16), ice, translucent=True)
    sp = m.bone("spikes", (0, 16, 0), "shell")
    for (x, z, h, r) in ((-5, -4, 4, 12), (4, 3, 5, -10), (1, -6, 3, 8), (-3, 5, 3.5, -14)):
        sp.add((x - 1, 16, z - 1), (2, h, 2), mt.clear_ice(170), pivot=(x, 16, z), rotation=(r, 0, r * 0.6),
               translucent=True)
    return m


ALL_ITEM_MODELS = {
    "solar_frost_goggles": goggles,
    "endless_handline": lambda: handline(False),
    "endless_handline_cast": lambda: handline(True),
    "bamboo_sword_cane": lambda: cane(False),
    "bamboo_sword_cane_drawn": lambda: cane(True),
}
ALL_ENTITY_MODELS = {
    "handline_hook": handline_sinker,
    "handline_bobber": handline_bobber,
    "sun_dog": sun_dog,
    "ice_shell": ice_shell,
}
