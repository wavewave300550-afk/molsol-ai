"""
aux_anims.py - animations of the helper entities.

Entities oriented by the script carry a synced `sab:heading` property; their aim bone
compensates the engine body yaw exactly like the boss root does.
"""
from __future__ import annotations

from anim import Anim, Controller

HEADING = "math.min_angle(query.property('sab:heading') - query.body_y_rotation)"


def cherub():
    idle = Anim("animation.sab.cherub.idle", 2.0, True)
    idle.pos_e("body", "0", "math.sin(query.anim_time * 180.0) * 1.2", "0")
    idle.rot_e("body", "math.sin(query.anim_time * 180.0 + 90.0) * 4.0", HEADING, "0")
    for i in range(1, 5):
        sign = -1 if i % 2 else 1
        idle.rot_e(f"wing_{i}", "0", f"{sign} * math.sin(query.anim_time * 1080.0) * 14.0", f"{sign} * math.sin(query.anim_time * 1080.0 + 90.0) * 8.0")
    idle.rot_e("halo", "0", "query.anim_time * 180.0", "0")
    idle.scl_e("body", "1.0 + query.property('sab:charge') * 0.18 * (math.sin(query.anim_time * 1440.0) * 0.5 + 0.5)")
    idle.fx(0.0, "orb_trail", "muzzle")
    return [idle], {"idle": "animation.sab.cherub.idle"}, ["idle"]


def plasma_orb():
    a = Anim("animation.sab.plasma_orb.spin", 1.0, True)
    a.rot_e("core", "query.anim_time * 360.0", "query.anim_time * 720.0", "0")
    a.scl_e("core", "1.0 + math.sin(query.anim_time * 1440.0) * 0.12")
    a.fx(0.0, "orb_trail").fx(0.5, "orb_trail")
    return [a], {"spin": "animation.sab.plasma_orb.spin"}, ["spin"]


def censer():
    a = Anim("animation.sab.censer.idle", 4.0, True)
    a.rot_e("body", "math.sin(query.anim_time * 90.0) * 9.0", "query.anim_time * 45.0", "math.cos(query.anim_time * 90.0) * 6.0")
    a.pos_e("body", "0", "math.sin(query.anim_time * 180.0) * 2.0", "0")
    a.rot_e("ring", "20.0", "-query.anim_time * 180.0", "0")
    a.fx(0.0, "censer_smoke", "incense").fx(1.0, "censer_smoke", "incense").fx(2.0, "censer_smoke", "incense").fx(3.0, "censer_smoke", "incense")
    return [a], {"idle": "animation.sab.censer.idle"}, ["idle"]


def seraph():
    a = Anim("animation.sab.seraph.motion", 2.0, True)
    a.rot_e("tilt", "query.property('sab:tilt')", HEADING, "0")
    a.rot_e("spin", "0", "0", "variable.spin")
    a.scl_e("spin", "query.property('sab:mode') == 1 ? 1.0 + math.sin(query.anim_time * 1440.0) * 0.05 : 1.0")
    pre = ["variable.spin = math.mod(variable.spin + math.min(query.delta_time, 0.1) * "
           "(query.property('sab:mode') == 3 ? 0.0 : (query.property('sab:mode') == 2 ? 1440.0 : (query.property('sab:mode') == 1 ? 900.0 : 260.0))), 360.0);"]
    return [a], {"motion": "animation.sab.seraph.motion"}, ["motion"], pre, ["variable.spin = 0.0;"]


def hull_plate():
    a = Anim("animation.sab.hull_plate.settle", 1.2, "hold_on_last_frame")
    a.pos("slab", {0.0: (0, 14, 0), 0.25: (0, -4, 0), 0.5: (0, 1, 0), 0.8: (0, 0, 0)})
    a.rot("slab", {0.0: (-12, 0, 0), 0.25: (6, 0, 0), 0.5: (-2, 0, 0), 0.8: (0, 0, 0)})
    a.fx(0.25, "dust")
    glow = Anim("animation.sab.hull_plate.glow", 3.0, True)
    glow.scl_e("cracks", "1.0 + math.sin(query.anim_time * 120.0) * 0.01")
    return [a, glow], {"settle": "animation.sab.hull_plate.settle", "glow": "animation.sab.hull_plate.glow"}, ["settle", "glow"]


def singularity():
    a = Anim("animation.sab.singularity.spin", 2.0, True)
    a.rot_e("core", "query.anim_time * 90.0", "query.anim_time * 180.0", "0")
    a.rot_e("disk", "14.0", "-query.anim_time * 540.0", "8.0")
    a.scl_e("root", "variable.sz")
    a.scl_e("lens", "1.0 + math.sin(query.anim_time * 720.0) * 0.08")
    pre = ["variable.target = query.property('sab:stage') == 0 ? 0.5 : (query.property('sab:stage') == 1 ? 1.0 + query.property('sab:radius') * 0.04 : 0.05);",
           "variable.sz = variable.sz + (variable.target - variable.sz) * math.min(1.0, math.min(query.delta_time, 0.1) * 6.0);"]
    return [a], {"spin": "animation.sab.singularity.spin"}, ["spin"], pre, ["variable.sz = 0.05;"]


def lance():
    a = Anim("animation.sab.lance.beam", 1.0, True)
    a.rot_e("aim", "query.property('sab:pitch')", HEADING, "0")
    a.scl_e("beam", "variable.pw", "variable.pw", "math.max(query.property('sab:len'), 0.1) / 32.0")
    a.rot_e("rings", "0", "0", "query.anim_time * 720.0")
    a.scl_e("muzzle", "0.6 + variable.pw * 0.5 + math.sin(query.anim_time * 2160.0) * 0.08")
    pre = ["variable.pw = variable.pw + (query.property('sab:power') - variable.pw) * math.min(1.0, math.min(query.delta_time, 0.1) * 10.0);"]
    return [a], {"beam": "animation.sab.lance.beam"}, ["beam"], pre, ["variable.pw = 0.0;"]


def orison_halo():
    a = Anim("animation.sab.orison_halo.spin", 0.5, True)
    a.rot_e("spin", "0", "query.anim_time * 1440.0", "0")
    a.fx(0.0, "halo_trail").fx(0.25, "halo_trail")
    return [a], {"spin": "animation.sab.orison_halo.spin"}, ["spin"]


ALL = {
    "cherub": cherub, "plasma_orb": plasma_orb, "censer": censer, "seraph": seraph, "hull_plate": hull_plate,
    "singularity": singularity, "lance": lance, "orison_halo": orison_halo,
}


def get(name):
    res = ALL[name]()
    anims, amap, animate = res[0], res[1], res[2]
    pre = res[3] if len(res) > 3 else []
    init = res[4] if len(res) > 4 else []
    return anims, amap, animate, pre, init
