"""
THE WORD OF GOD (Logos) - remastered model.

"In the beginning was the Word." A colossal, unearthly construct of light and law: a radiant core
with a single Eye (closed -> half-open -> open across the phases), three armillary rings of
inscribed gold turning on different axes, the Seven Seals in crimson wax (they break one by one),
two great wings made of golden scripture pages (folded in phase I, unfolding in phase II), a halo
of rays, floating Alpha and Omega, a triad of light above, and a descending column of rings and an
unrolling scroll below in place of a body.

Scale 2.0 -> 8 model units per block. Faces -Z. Eye ~ (0, 44, -8) (script eye(): pos + 5.5 blocks).
"""
import math

from modelkit import Model
from shapes import bevel, orb, ring, spike, strut
from shapes2 import catmull, feather, tube
import lmat as L

ID = "geometry.legends.logos"
KEY = "logos"
SCALE = 2.0
VARIANTS = {"default": "default"}
CORE = (0.0, 44.0, 0.0)


def _glyph_alpha(bone, c, mat):
    x, y, z = c
    strut(bone, (x - 3, y - 5, z), (x, y + 5, z), 1.4, mat, depth=1.0, glow=True)
    strut(bone, (x + 3, y - 5, z), (x, y + 5, z), 1.4, mat, depth=1.0, glow=True)
    bone.add((x - 1.8, y - 1.2, z - 0.5), (3.6, 1.2, 1.0), mat, glow=True)


def _glyph_omega(bone, c, mat):
    x, y, z = c
    ring(bone, (x, y + 1, z), 3.4, 9, mat, thickness=1.2, width=1.0, plane="xy", glow=True, arc=(-50, 230))
    bone.add((x - 4.6, y - 3.6, z - 0.5), (2.6, 1.2, 1.0), mat, glow=True)
    bone.add((x + 2.0, y - 3.6, z - 0.5), (2.6, 1.2, 1.0), mat, glow=True)


def build():
    m = Model(ID, seed=61, density=2)
    GD = L.divine_gold()
    GDP = L.divine_gold(glyphs=False)
    PG = L.parchment()
    WAX = L.wax_seal()
    LIGHT = L.glow("ffffff", "ffd870", "r")
    RAY = L.glow("fffbe8", "ffc640", "vb")
    cx, cy, cz = CORE

    root = m.bone("root", (0, 0, 0))
    core = m.bone("core", CORE, "root")
    orb(core, CORE, 7.5, L.glow("ffffff", "fff0b0", "r"), glow=True)
    orb(core, CORE, 6.2, L.solid("fff8e0", 0.02))
    # the Eye: lids (solid gold) over a glowing eye
    eye = m.bone("eye", (cx, cy, cz - 6), "core")
    eye.add((cx - 7.5, cy - 4.2, cz - 9.4), (15, 8.4, 1.0), L.glow("fffef0", "ffe080", "r"), glow=True,
            decals={"north": L.eye_decal()})
    bevel(eye, (cx - 9.5, cy - 5.8, cz - 9.0), (19, 11.6, 2.4), GDP, b=1.0)       # eye frame (almond setting)
    for sx in (-1, 1):
        spike(eye, (sx * 9.5, cy, cz - 8.4), (sx * 14, cy, cz - 7.6), 3.0, GD, steps=2)    # almond corners
    lid_t = m.bone("lid_top", (cx, cy + 4.6, cz - 9), "eye")
    bevel(lid_t, (cx - 8, cy, cz - 10.6), (16, 4.6, 1.8), GD, b=0.5)
    lid_b = m.bone("lid_bot", (cx, cy - 4.6, cz - 9), "eye")
    bevel(lid_b, (cx - 8, cy - 4.6, cz - 10.6), (16, 4.6, 1.8), GD, b=0.5)
    # armillary rings
    for name, r, plane, n in (("ring_a", 13, "xy", 16), ("ring_b", 16, "yz", 18), ("ring_c", 19.5, "xz", 22)):
        rb = m.bone(name, CORE, "core")
        ring(rb, CORE, r, n, GD, thickness=1.8, width=2.6, plane=plane)
        ring(rb, CORE, r + 1.2, n, L.glow("fff6c8", "ffb830", "u"), thickness=0.5, width=0.8, plane=plane, glow=True)
    # halo of rays (behind)
    halo = m.bone("halo", (cx, cy, cz + 6), "root")
    for k in range(18):
        ang = k / 18 * 2 * math.pi
        L0 = 24 if k % 2 == 0 else 22
        L1 = 36 if k % 2 == 0 else 31
        a = (cx + math.cos(ang) * L0, cy + math.sin(ang) * L0, cz + 7)
        b = (cx + math.cos(ang) * L1, cy + math.sin(ang) * L1, cz + 7)
        spike(halo, a, b, 3.2 if k % 2 == 0 else 2.2, RAY, glow=True, steps=2)
    ring(halo, (cx, cy, cz + 7), 22.5, 24, GD, thickness=1.4, width=1.2, plane="xy")
    # the Seven Seals on an arc above and around the core
    for k in range(7):
        ang = math.radians(90 + (k - 3) * 26)
        p = (cx + math.cos(ang) * 26, cy + math.sin(ang) * 26 - 2, cz + 2)
        sb = m.bone(f"seal{k + 1}", p, "root")
        bevel(sb, (p[0] - 3, p[1] - 3, p[2] - 1.2), (6, 6, 2.4), WAX, b=0.8)
        strut(sb, (p[0], p[1] + 3, p[2]), (cx + math.cos(ang) * 22.6, cy + math.sin(ang) * 22.6, cz + 6), 0.6, GDP)
    # scripture wings (pages fanned); rest = unfolded
    for side, sx in (("r", -1), ("l", 1)):
        wb = m.bone(f"wing_{side}", (sx * 8, 46, 2), "root")
        for k in range(6):
            yaw = sx * (78 + k * 6)
            pitch = -34 + k * 17
            ln = 32 - abs(k - 2.5) * 2.4
            feather(wb, (sx * 8, 46 + 0.15 * k, 2 + 0.25 * k), ln, 12, yaw, pitch, PG, thick=0.8)
            feather(wb, (sx * 8, 46.4 + 0.15 * k, 2.3 + 0.25 * k), ln * 0.5, 3.4, yaw, pitch, GDP, thick=1.2)
    # Alpha and Omega
    al = m.bone("alpha", (-34, 40, -2), "root", floating=True)
    _glyph_alpha(al, (-34, 40, -2), L.glow("ffffff", "ffcf50", "u"))
    om = m.bone("omega", (34, 40, -2), "root", floating=True)
    _glyph_omega(om, (34, 40, -2), L.glow("ffffff", "ffcf50", "u"))
    # triad of light above
    tri = m.bone("triad", (cx, 66, cz), "root", floating=True)
    for k in range(3):
        ang = k / 3 * 2 * math.pi + math.pi / 2
        c = (cx + math.cos(ang) * 4.5, 66 + math.sin(ang) * 4.5, cz)
        orb(tri, c, 1.8, LIGHT, glow=True)
    ring(tri, (cx, 66, cz), 4.5, 9, L.glow("fff6c8", "ffb830", "u"), thickness=0.6, width=0.6, plane="xy", glow=True)
    # descending column of rings and the unrolling scroll
    col = m.bone("column", (cx, 34, cz), "root", floating=True)
    for k, (y, r) in enumerate(((33, 7), (27, 6), (21, 5), (15.5, 4), (10.5, 3), (6.5, 2))):
        ring(col, (cx, y, cz), r, 10 + (6 - k), GD if k % 2 == 0 else GDP, thickness=1.2, width=1.2, plane="xz", phase=k * 0.2)
        orb(col, (cx, y - 2.5, cz), max(0.9, r * 0.32), LIGHT, glow=True)
    scroll = m.bone("scroll", (cx, 34, cz), "column")
    spts = [(cx + math.cos(t * 0.9) * (6 - t * 0.6), 36 - t * 3.4, cz + math.sin(t * 0.9) * (6 - t * 0.6)) for t in range(9)]
    for k in range(len(spts) - 1):
        a, b = spts[k], spts[k + 1]
        strut(scroll, a, b, 4.2 - k * 0.3, PG, depth=0.6)
    return m


# =========================================================================== animation
from animkit import A, T, Act, cs, loop, sn

FOLD = {   # phase I: the page-wings folded down along the column
    "wing_r": {"r": [30, -60, -70]}, "wing_l": {"r": [30, 60, 70]},
}


def loops():
    idle = {
        "root": {"p": [0, sn(60, amp=1.2), 0]},
        "core": {"r": [0, sn(20, amp=6), 0]},
        "ring_a": {"r": [0, 0, f"{T} * 24"]}, "ring_b": {"r": [f"{T} * -18", 0, 0]}, "ring_c": {"r": [0, f"{T} * 14", 0]},
        "halo": {"r": [0, 0, f"{T} * -6"]},
        "triad": {"r": [0, f"{T} * 40", 0], "p": [0, sn(70, amp=1), 0]},
        "alpha": {"p": [0, sn(50, amp=1.6), 0], "r": [0, sn(30, amp=12), 0]},
        "omega": {"p": [0, sn(50, 180, 1.6), 0], "r": [0, sn(30, 90, 12), 0]},
        "column": {"r": [0, f"{T} * 30", 0]},
        "wing_r": {"r": [sn(40, amp=3), sn(30, amp=4), 0]}, "wing_l": {"r": [sn(40, 120, 3), sn(30, 90, -4), 0]},
        "lid_top": {"r": ["82 * variable.open", 0, 0]}, "lid_bot": {"r": ["-82 * variable.open", 0, 0]},
        "eye": {"r": [sn(50, amp=4), sn(35, amp=6), 0]},
    }
    for k in range(7):
        idle[f"seal{k + 1}"] = {"r": [0, 0, sn(60, k * 50, 6)], "p": [0, sn(45, k * 40, 0.6), 0]}
    fold = {b: {"r": v["r"]} for b, v in FOLD.items()}
    return {"idle": loop(idle), "fold": loop(fold)}


def acts():
    out = []
    lid = lambda o: {"lid_top": {"r": (28 * o, 0, 0)}, "lid_bot": {"r": (-28 * o, 0, 0)}}
    spread = lambda k: {"wing_r": {"r": (0, -k, -k * 0.6)}, "wing_l": {"r": (0, k, k * 0.6)}}
    # 1 advent (80, 60): descends in a pillar of light, rings spin up
    a = Act("advent", 80, [60])
    a.at(0, {"root": {"p": (0, 40, 0), "s": 0.4}, "ring_a": {"s": 0.3}, "ring_b": {"s": 0.3}, "ring_c": {"s": 0.3}})
    a.at(56, {"root": {"p": (0, 2, 0), "s": 1.0}, "ring_a": {"s": 1.0}, "ring_b": {"s": 1.0}, "ring_c": {"s": 1.0}}, "out")
    a.at(60, {"root": {"p": (0, 0, 0), "s": 1.08}, "halo": {"s": 1.3}}, "in")
    a.at(80, {"root": {"s": 1.0}, "halo": {"s": 1.0}})
    out.append(a.overlay("ring_a", "r", [0, 0, f"{A} * 400"]).overlay("ring_c", "r", [0, f"{A} * 300", 0]))
    # 2 speak (40, 16): the Word is spoken - everything pulses outward
    a = Act("speak", 40, [16])
    a.at(12, {"core": {"s": 0.85}, **lid(0.2)})
    a.at(16, {"core": {"s": 1.3}, "halo": {"s": 1.25}, "ring_a": {"s": 1.15}, "ring_b": {"s": 1.15}, "ring_c": {"s": 1.15}, **lid(1.0)}, "in")
    a.at(40, {"core": {"s": 1.0}, "halo": {"s": 1.0}, "ring_a": {"s": 1.0}, "ring_b": {"s": 1.0}, "ring_c": {"s": 1.0}})
    out.append(a)
    # 3 fiat (48, 24): "Let there be light" - rings align flat, the grid ignites
    a = Act("fiat", 48, [24])
    a.at(20, {"ring_a": {"r": (90, 0, 0)}, "ring_b": {"r": (0, 0, 90)}, "core": {"s": 1.15}})
    a.at(24, {"core": {"s": 0.9}, "halo": {"s": 1.2}}, "in")
    a.at(48, {"ring_a": {"r": (0, 0, 0)}, "ring_b": {"r": (0, 0, 0)}, "core": {"s": 1.0}, "halo": {"s": 1.0}})
    out.append(a)
    # 4 lances (36, 12)
    a = Act("lances", 36, [12])
    a.at(10, {**spread(18), "halo": {"s": 1.15}})
    a.at(12, {**spread(-6), "halo": {"s": 0.95}}, "in")
    a.at(36, {**spread(0), "halo": {"s": 1.0}})
    out.append(a.overlay("halo", "r", [0, 0, f"{A} * 160"]))
    # 5 gaze (60, 16): judgement - the eye stares down, the core leans
    a = Act("gaze", 60, [16])
    a.at(14, {"core": {"r": (24, 0, 0)}, **lid(1.0), "eye": {"s": 1.25}})
    a.at(52, {"core": {"r": (24, 0, 0)}, "eye": {"s": 1.25}}, "lin")
    a.at(60, {"core": {"r": (0, 0, 0)}, "eye": {"s": 1.0}})
    out.append(a)
    # 6 trumpet (44, 12, 24, 36): three soundings - the halo flares each time
    a = Act("trumpet", 44, [12, 24, 36])
    for mk in (12, 24, 36):
        a.at(mk - 4, {"halo": {"s": 0.9}, **spread(-8)}, "out")
        a.at(mk, {"halo": {"s": 1.35}, **spread(16)}, "in")
    a.at(44, {"halo": {"s": 1.0}, **spread(0)})
    out.append(a)
    # 7 babel (64, 10): the rings tilt into a spiral tower and spin
    a = Act("babel", 64, [10])
    a.at(10, {"ring_a": {"r": (30, 0, 0)}, "ring_b": {"r": (0, 0, 40)}, "ring_c": {"r": (20, 0, 0)}}, "in")
    a.at(58, {"ring_a": {"r": (30, 0, 0)}}, "lin")
    a.at(64, {"ring_a": {"r": (0, 0, 0)}, "ring_b": {"r": (0, 0, 0)}, "ring_c": {"r": (0, 0, 0)}})
    out.append(a.overlay("column", "r", [0, f"{A} * 600", 0]).overlay("ring_c", "r", [0, f"{A} * 500", 0]))
    # 8 reforge (50, 36): re-speaks a fallen member of the Choir
    a = Act("reforge", 50, [36])
    a.at(30, {"core": {"s": 1.4}, "triad": {"s": 1.6}, **spread(20)})
    a.at(36, {"core": {"s": 0.9}, "triad": {"s": 0.8}}, "in")
    a.at(50, {"core": {"s": 1.0}, "triad": {"s": 1.0}, **spread(0)})
    out.append(a)
    # 9 unseal (40, 20): a seal cracks - recoil
    a = Act("unseal", 40, [20])
    a.at(16, {"core": {"r": (-10, 0, 0)}, "halo": {"s": 0.9}})
    a.at(20, {"core": {"r": (8, 0, 0)}, "halo": {"s": 1.3}}, "in")
    a.at(40, {"core": {"r": (0, 0, 0)}, "halo": {"s": 1.0}})
    out.append(a.overlay("root", "p", [f"math.sin({A} * 2400) * 0.4", 0, 0]))
    # 10 apocalypse (280, 60, 160, 252): ULT - the Final Word
    a = Act("apocalypse", 280, [60, 160, 252])
    a.at(40, {**spread(24), "halo": {"s": 1.4}, **lid(1.0), "core": {"s": 1.2}}, "out")
    a.at(60, {"triad": {"s": 2.0}, "root": {"p": (0, 6, 0)}}, "in")
    a.at(160, {"halo": {"s": 1.7}, "core": {"s": 1.35}}, "io")
    a.at(240, {"halo": {"s": 2.1}, "core": {"s": 1.6}, "eye": {"s": 1.6}, **spread(30)}, "io")
    a.at(252, {"halo": {"s": 2.6}, "core": {"s": 0.8}, "eye": {"s": 2.0}, "root": {"p": (0, 2, 0)}}, "in")
    a.at(280, {"halo": {"s": 1.0}, "core": {"s": 1.0}, "eye": {"s": 1.0}, "triad": {"s": 1.0}, **spread(0), "root": {"p": (0, 0, 0)}}, "out")
    out.append(a.overlay("ring_a", "r", [0, 0, f"{A} * 160"]).overlay("ring_b", "r", [f"{A} * -140", 0, 0]))
    # 11 death (120, 100): the Word falls silent - rings stop, seals fall, the light folds inward
    a = Act("death", 120, [100])
    a.at(30, {"ring_a": {"r": (40, 0, 20)}, "ring_b": {"r": (30, 0, 0)}, "ring_c": {"r": (-20, 0, 30)}, **lid(0.0), "root": {"p": (0, -4, 0)}}, "io")
    a.at(80, {**spread(-30), "halo": {"s": 0.6}, "core": {"s": 0.8}, "root": {"p": (0, -10, 0)},
              **{f"seal{k + 1}": {"p": (0, -30, 0)} for k in range(7)}}, "io")
    a.at(100, {"core": {"s": 1.6}}, "in")
    a.at(120, {"root": {"s": 0.02, "p": (0, 20, 0)}}, "in")
    out.append(a)
    # 12 alpha_omega (70, 20, 50): the Beginning and the End sweep from both sides
    a = Act("alpha_omega", 70, [20, 50])
    a.at(16, {"alpha": {"p": (-6, 6, 0), "s": 1.6}, "omega": {"p": (6, 6, 0), "s": 1.6}, **lid(1.0)})
    a.at(20, {"alpha": {"p": (0, 0, 0), "s": 2.0}, "omega": {"p": (0, 0, 0), "s": 2.0}}, "in")
    a.at(50, {"alpha": {"r": (0, 180, 0)}, "omega": {"r": (0, -180, 0)}}, "lin")
    a.at(70, {"alpha": {"s": 1.0, "r": (0, 0, 0)}, "omega": {"s": 1.0, "r": (0, 0, 0)}})
    out.append(a)
    # 13 concord (60, 24): conducts the Choir - wings raised, triad blazing
    a = Act("concord", 60, [24])
    a.at(18, {**spread(30), "triad": {"s": 1.8, "p": (0, 6, 0)}, "core": {"s": 1.15}})
    a.at(24, {"triad": {"s": 2.2}, "halo": {"s": 1.3}}, "in")
    a.at(60, {**spread(0), "triad": {"s": 1.0, "p": (0, 0, 0)}, "core": {"s": 1.0}, "halo": {"s": 1.0}})
    out.append(a)
    return out


def entity_cfg():
    return {
        "scale": SCALE,
        "textures": {"default": f"textures/entity/legends/{KEY}"},
        "pre": [
            "variable.open = math.lerp(variable.open ?? 0.0, variable.ph >= 3 ? 1.0 : (variable.ph >= 2 ? 0.55 : 0.0), 0.04);",
            "variable.seals = query.property('legends:var');",
            "variable.unfold = math.lerp(variable.unfold ?? 0.0, variable.ph >= 2 ? 1.0 : 0.0, 0.03);",
        ],
        "animate": [{"idle": "variable.calm + 0.25"}, {"fold": "1.0 - variable.unfold"}, "ctrl_act"],
        "visibility": [{f"seal{k}": f"variable.seals < {k}"} for k in range(1, 8)],
        "bounds": (16, 14, 4.0),
    }


if __name__ == "__main__":
    import sys
    from modelkit import render_preview, zfight_report, island_report, deflicker
    out = sys.argv[1]
    m = build()
    m.paint()
    print(m.stats())
    print("islands", island_report(m))
    print("zfight", len(zfight_report(m)), "after deflicker", deflicker(m))
    fold = {b: {"rot": tuple(v["r"])} for b, v in FOLD.items()}
    render_preview([m], f"{out}/logos_p1.png", yaw=25, pitch=8, size=700, step=2, pose=fold)
    render_preview([m], f"{out}/logos_p3.png", yaw=-20, pitch=8, size=700, step=2, pose={"seal1": {"scale": 0.001}, "seal2": {"scale": 0.001},
                   "lid_top": {"rot": (82, 0, 0)}, "lid_bot": {"rot": (-82, 0, 0)}})
