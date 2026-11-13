"""DN06 environments: Dream Zones (floating garden, cloud-city fragment, golden stairway),
Nightmare Zones (upside-down room, predatory corridor, living doors) and the Great Unreality
formations (wheel of doors, spiral-stair drill, expanding room-cube, window-shard, spilled stairs)."""
import math

import numpy as np

from kit import glyphs, tex
from kit.anim import LIFE, Anim, S
from kit.geo import Mat, Model, ring

from .dn_dreamer import (AGED, BURG, CGRAY, INDIGO, IVORY, MAUVE, PBLUE, PEACH, PINK, SGOLD, arch_mat, door_mat,
                         eyewall, gilt, lamp_mat, porc, quilt, spin, wallpaper, window_mat)

DREAMG = list(glyphs.DREAM.values())
ZONE_R = 64          # aura half-size in units (4 blocks at scale 1)


def cloud_mat():
    def fn(ctx):
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, "#ffffff", 1, 0.35)
        n = tex.fbm(ix / 3.0 + ctx.variant * 5, iy / 3.0, 7)
        t[..., :3] = tex.mix(tex.rgb("#e9eefa"), tex.rgb("#fffaf4"), np.clip(n * 1.3 - 0.1 + (1 - ctx.V) * 0.3, 0, 1)[..., None])
        t[..., :3] = np.where((ctx.V > 0.75)[..., None], t[..., :3] * tex.rgb("#f6dbe6"), t[..., :3])
        return t
    return Mat(fn, "dnz_cloud")


def dream_aura():
    return tex.magic_circle(DREAMG, "#fff3c8", PEACH, bands=((0.8, 0.95, 14),), lines=(0.78, 0.98), star=6,
                            star_r=(0.2, 0.6), fill="#ffd9b8", fill_glow=0.35)


def night_aura():
    def fn(ctx):
        u, v = ctx.U * 2 - 1, ctx.V * 2 - 1
        r = np.hypot(u, v)
        ix, iy = tex.px(ctx)
        t = tex.tile(ctx, INDIGO, 0.0, 0.5)
        crack = np.abs(tex.vnoise(ix / 3.0, iy / 3.0, 3) - tex.vnoise(ix / 3.0 + 7, iy / 3.0 + 3, 4)) < 0.06
        rim = np.abs(r - 0.93) < 0.03
        eyes = (tex._hash(ix // 3, iy // 3, 11) > 0.9) & ((ix % 3) == 1) & ((iy % 3) == 1) & (r < 0.85)
        on = (crack & (r < 0.95)) | rim | eyes
        t[..., :3] = np.where(crack[..., None], tex.rgb("#8e3446"), tex.rgb("#b8a6d6"))
        t[..., :3] = np.where(eyes[..., None], tex.rgb("#f3e3b0"), t[..., :3])
        t[..., 3] = np.where(on, 1.0, np.where(r < 0.93, 0.0, 0.0))
        t[..., 4] = np.where(on, 0.9, 0.0)
        return t
    return Mat(fn, "dnz_nightaura", directional=True)


def zone_shell(name):
    m = Model(name, density=1.0, bounds=(10, 10, (0, 2, 0)))
    root = m.bone("root")
    aura = m.bone("aura", root)
    flt = m.bone("float", root, pivot=(0, 0, 0))
    sp = m.bone("spin", flt, pivot=(0, 0, 0))
    return m, aura, flt, sp


# ---------------------------------------------------------------- dream zones
def garden():
    m, aura, flt, sp = zone_shell("dn_dreamer_garden")
    aura.plane("y", (0, 0.3, 0), ZONE_R * 2, ZONE_R * 2, dream_aura(), faces=("up", "down"), density=0.75)
    earth = tex.stone("#b88f6a", "#7d5a40", "#d4ac86", cracks=0.1)
    grass = tex.mottled("#9fcf8a", "#cfe9a8", scale=3, glow=0.15)
    for k, (w, y) in enumerate(((44, 44), (34, 38), (24, 32), (14, 26), (6, 20))):
        sp.box((0, y - 3, 0), (w, 6, w * 0.9), earth, variant=k % 3)
    sp.box((0, 47.5, 0), (46, 1.2, 41), grass)
    leaf = tex.foliage("#7fbf7a", "#c9f0b0", holes=0.3, glow=0.2, flowers=PINK)
    for k in range(5):
        a = math.radians(k * 72 + 20)
        x, z = math.cos(a) * 15, math.sin(a) * 13
        for r in (0, 90):
            sp.plane("z", (x, 54, z), 10, 12, leaf, rot=(0, r + k * 17, 0), pivot=(x, 54, z), variant=k % 2)
    sp.plane("z", (0, 58, 6), 18, 22, arch_mat(IVORY, "#efe4d0", SGOLD, key="gardengate", glow=0.2))
    sp.box((0, 50, -6), (8, 3, 8), gilt(0.3))
    sp.box((0, 51.8, -6), (6, 0.6, 6), tex.flat("#9fd0ff", glow=0.8))
    sp.box((0, 55, -6), (1.2, 6, 1.2), gilt(0.3))
    for k in range(4):   # dangling roots + lanterns
        a = math.radians(k * 90 + 45)
        x, z = math.cos(a) * 9, math.sin(a) * 9
        sp.box((x, 18, z), (0.8, 10, 0.8), tex.flat("#7d5a40"))
        sp.box((x, 12, z), (2.4, 2.4, 2.4), lamp_mat())
    return m


def cloudcity():
    m, aura, flt, sp = zone_shell("dn_dreamer_cloudcity")
    aura.plane("y", (0, 0.3, 0), ZONE_R * 2, ZONE_R * 2, dream_aura(), faces=("up", "down"), density=0.75)
    cl = cloud_mat()
    for k, (x, y, z, w, h, d) in enumerate([(0, 36, 0, 44, 10, 34), (-14, 40, 6, 22, 10, 20), (14, 39, -6, 24, 9, 22),
                                            (4, 31, 2, 30, 6, 24), (-6, 44, -4, 16, 6, 14)]):
        sp.box((x, y, z), (w, h, d), cl, variant=k % 3)
    win = window_mat("#ffe7b0", SGOLD, "#fbf4ea", arch=True)
    dome = gilt(0.4)
    for k, (x, z, w, h) in enumerate(((-8, 0, 7, 30), (6, -4, 6, 22), (12, 8, 5, 36), (-2, 10, 5, 18))):
        y0 = 44
        sp.box((x, y0 + h / 2, z), (w, h, w), win, variant=k % 2)
        sp.box((x, y0 + h + 1, z), (w + 1, 2, w + 1), dome)
        sp.box((x, y0 + h + 3, z), (w - 2, 2, w - 2), dome)
        sp.box((x, y0 + h + 5.5, z), (1, 3, 1), dome)
    sp.box((-1, 62, -2), (14, 1, 3), dome, rot=(0, -20, 0))
    sp.plane("z", (0, 52, -18), 10, 12, door_mat(PEACH, SGOLD, glass="#fff0c8", key="cityGate"))
    return m


def stairway():
    m, aura, flt, sp = zone_shell("dn_dreamer_stairway")
    aura.plane("y", (0, 0.3, 0), ZONE_R * 2, ZONE_R * 2, dream_aura(), faces=("up", "down"), density=0.75)
    g = gilt(0.45)
    sp.box((0, 34, 0), (3, 68, 3), tex.glow_flat("#fff3c8", 1.0, core="#ffffff"))
    for k in range(15):
        a = k * 28
        y = 4 + k * 4.4
        sp.box((9, y, 0), (14, 1.6, 5.5), g, rot=(0, -a, 0), pivot=(0, y, 0), variant=k % 2)
        sp.box((15.5, y + 4, 0), (0.6, 8, 0.6), g, rot=(0, -a, 0), pivot=(0, y, 0))
    sp.box((0, 72, 0), (14, 1.4, 14), g)
    sp.plane("z", (0, 81, 0), 10, 16, door_mat("#fff3c8", SGOLD, glass="#ffffff", key="goldDoor", glow=0.6))
    sp.box((0, 89.5, 0), (12, 1.2, 1.2), g)
    return m


def dream_anims():
    A = []
    turn = Anim("turn", loop=True)
    turn.rot("aura", (0, spin(10), 0))
    turn.rot("spin", (0, spin(14), 0))
    turn.pos("float", (0, LIFE(2.5, 4.4), 0))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    bloom = Anim("bloom", length=1.5, loop="hold")
    bloom.scl("aura", {0: 0.0, 0.6: 1.08, 0.9: 1.0})
    bloom.scl("float", {0: 0.0, 0.3: 0.0, 1.1: 1.1, 1.5: 1.0}, smooth=False)
    bloom.pos("float", {0: (0, -40, 0), 0.3: (0, -40, 0), 1.2: (0, 4, 0), 1.5: (0, 0, 0)})
    bloom.rot("spin", {0: (0, -180, 0), 1.5: (0, 0, 0)})
    A.append(bloom)
    A.append(Anim("idle", loop=True))
    fold = Anim("fold", length=1.2, loop="hold")      # lifts and folds flat to join a formation
    fold.pos("float", {0: (0, 0, 0), 1.2: (0, 70, 0)})
    fold.scl("float", {0: 1.0, 0.5: (1.1, 0.5, 1.1), 1.2: (0.2, 0.0, 1.4)}, smooth=False)
    fold.rot("spin", {0: (0, 0, 0), 1.2: (0, 400, 0)})
    fold.scl("aura", {0: 1.0, 1.2: 0.0}, smooth=False)
    A.append(fold)
    fade = Anim("fade", length=1.0, loop="hold")
    fade.scl("root", {0: 1.0, 0.25: 1.06, 1.0: 0.0}, smooth=False)
    A.append(fade)
    return A


ZONE_STATES = {0: ["hidden"], 1: ["bloom"], 2: ["idle"], 3: ["fold"], 4: ["fade"], 5: ["bite"]}


# ---------------------------------------------------------------- nightmare zones
def _night_shell(name):
    m, aura, flt, sp = zone_shell(name)
    aura.plane("y", (0, 0.3, 0), ZONE_R * 2, ZONE_R * 2, night_aura(), faces=("up", "down"), density=0.75)
    return m, aura, flt, sp


def slot_jaw(m, parent, k, angle, hinge):
    s = m.bone(f"slot{k}", parent, pivot=(0, 0, 0), rot=(0, angle, 0))
    j = m.bone(f"jaw{k}", s, pivot=hinge)
    return j


def upside_room():
    m, aura, flt, sp = _night_shell("dn_dreamer_uproom")
    wp = wallpaper(MAUVE, "#7d5a80", dots="#cfc6b0", glow=0.15, key="uproomwp")
    fl = tex.wood("#5a4a5e", "#3a2e40", plank=3)
    sp.box((0, 74, 0), (44, 3, 44), fl)                                   # the floor is the ceiling
    sp.plane("y", (0, 72.4, 0), 30, 30, tex.fabric(BURG, "#8e3446", stripe_w=2, glow=0.1), faces=("down",))
    # furniture hanging upside-down
    W = tex.wood("#6a5a6e", "#40344a")
    sp.box((-8, 66, -6), (14, 2, 10), W)                                  # table
    for sx in (-1, 1):
        for sz in (-1, 1):
            sp.box((-8 + sx * 6, 69.5, -6 + sz * 4), (1.2, 5, 1.2), W)
    sp.box((10, 64, 8), (12, 4, 18), quilt(INDIGO, "#4a3e6a", BURG, key="upbed"))  # bed, belly-up
    sp.box((10, 60.5, 0), (12, 6, 1.5), W)
    sp.box((-12, 62, 12), (1, 10, 1), gilt(0.2))                           # lamp hanging the wrong way
    sp.box((-12, 56, 12), (5, 3, 5), tex.glow_flat("#f3e3b0", 0.9, core="#ffffff"))
    sp.box((0, 78, 0), (3, 6, 3), gilt(0.3))                               # chandelier standing up
    sp.box((0, 82, 0), (10, 2, 10), gilt(0.3))
    for k in range(3):   # three walls that clap like jaws
        j = slot_jaw(m, sp, k + 1, k * 90 - 90, (0, 72.5, 22))
        j.box((0, 56, 22), (44, 33, 2), wp, variant=k)
        j.plane("z", (0, 58, 20.8), 10, 13, window_mat("#f3e3b0", "#4a3e6a", MAUVE, glow=0.9))
        for t in range(6):
            j.box((-17.5 + t * 7, 38.5, 21), (2.5, 3, 2.5), tex.flat(AGED), rot=(0, 0, 45))
    return m


def corridor():
    m, aura, flt, sp = _night_shell("dn_dreamer_corridor")
    ew = eyewall("corrEyes")
    for k, side in enumerate((1, -1)):    # two walls hinged at the floor, toothed along the top
        j = slot_jaw(m, sp, k + 1, 0 if side > 0 else 180, (0, 0, -16))
        j.box((0, 16, -16), (60, 32, 3), ew, variant=k)
        for t in range(9):
            j.box((-26 + t * 6.5, 32 + (t % 2), -14.8), (3, 5 + (t % 3) * 1.5, 2.5), tex.flat(AGED), rot=(0, 0, 45))
        for x in (-18, 6):
            j.plane("z", (x, 11, -14.3), 9, 18, door_mat(AGED, "#8e3446", glass="#f3e3b0", key="corrdoor", alt_night=False))
    # twisted columns at both ends (architecture that should not stand)
    col = porc(AGED, "#b3a88f")
    for x in (-34, 34):
        for k in range(8):
            sp.box((x, 3 + k * 6, 0), (5, 6, 5), col, rot=(0, k * 13, k * 4 * (1 if x > 0 else -1)), pivot=(x, 3 + k * 6, 0),
                   variant=k % 3)
        sp.box((x, 50, 0), (8, 3, 8), gilt(0.2))
    sp.box((0, 52, 0), (76, 3, 6), porc(AGED, "#b3a88f"), rot=(0, 0, 4))
    return m


def living_doors():
    m, aura, flt, sp = _night_shell("dn_dreamer_doors")
    ew = eyewall("doorEyes")
    W = tex.wood("#6e5a6e", "#3e3246")
    for k in range(5):
        j = slot_jaw(m, sp, k + 1, k * 72, (0, 0, -40))
        j.box((-7.5, 15, -40), (2, 30, 3), W)
        j.box((7.5, 15, -40), (2, 30, 3), W)
        j.box((0, 31, -40), (17, 2.5, 3.5), W)
        j.plane("z", (0, 15, -39.6), 13, 29, ew, variant=k % 3)
        d = m.bone(f"door{k + 1}", j, pivot=(-6.5, 0, -41.6))
        d.cube((-6.5, 0.5, -42.2), (13, 29, 1.2), door_mat(MAUVE, "#8e3446", knob=True, key="livingdoor", alt_night=False))
        d.box((4, 15, -43), (1.4, 1.4, 1.4), gilt(0.5))
        for t in range(4):
            j.box((-5 + t * 3.3, 1.2, -38), (2, 2.4, 2), tex.flat(AGED), rot=(0, 0, 45))
    return m


def night_anims():
    A = []
    turn = Anim("turn", loop=True)
    turn.rot("aura", (0, spin(-12), 0))
    turn.rot("spin", (0, spin(-8), 0))
    turn.pos("float", (0, LIFE(1.2, 3.1), 0))
    A.append(turn)
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    A.append(hidden)
    em = Anim("emerge", length=1.5, loop="hold")      # rises out of the ground, twisting into place
    em.scl("aura", {0: 0.0, 0.5: 1.12, 0.8: 1.0})
    em.pos("float", {0: (0, -70, 0), 0.3: (0, -70, 0), 1.2: (0, 3, 0), 1.5: (0, 0, 0)})
    em.rot("float", {0: (0, 0, 0), 0.3: (20, 120, -10), 1.5: (0, 0, 0)})
    em.scl("float", {0: 0.0, 0.3: 0.0, 1.0: (1.0, 1.15, 1.0), 1.5: 1.0}, smooth=False)
    for k in range(5):
        em.rot(f"jaw{k + 1}", {0: (60, 0, 0), 1.0: (60, 0, 0), 1.5: (0, 0, 0)})
    A.append(em)
    idle = Anim("idle", loop=True, length=2.0)        # hungry architecture: jaws flex out of sync
    for k in range(5):
        idle.rot(f"jaw{k + 1}", (S(9, 2.0, k * 0.21, base=6), 0, 0))
        idle.rot(f"door{k + 1}", (0, S(40, 2.0, k * 0.37, base=-40), 0))
    A.append(idle)
    bite = Anim("bite", length=0.7, loop="hold")
    for k in range(5):
        bite.rot(f"jaw{k + 1}", {0: (6, 0, 0), 0.15: (-12, 0, 0), 0.3: (34, 0, 0), 0.45: (28, 0, 0), 0.7: (8, 0, 0)})
        bite.rot(f"door{k + 1}", {0: (0, -80, 0), 0.25: (0, -100, 0), 0.32: (0, 0, 0), 0.7: (0, -10, 0)})
    bite.pos("float", {0: (0, 0, 0), 0.3: (0, -3, 0), 0.7: (0, 0, 0)})
    A.append(bite)
    fold = Anim("fold", length=1.2, loop="hold")
    fold.pos("float", {0: (0, 0, 0), 1.2: (0, 70, 0)})
    fold.rot("float", {0: (0, 0, 0), 1.2: (180, 90, 0)})
    fold.scl("float", {0: 1.0, 0.6: (0.6, 1.3, 0.6), 1.2: 0.0}, smooth=False)
    for k in range(5):
        fold.rot(f"jaw{k + 1}", {0: (0, 0, 0), 0.6: (80, 0, 0)})
    fold.scl("aura", {0: 1.0, 1.2: 0.0}, smooth=False)
    A.append(fold)
    fade = Anim("fade", length=1.0, loop="hold")
    fade.scl("root", {0: 1.0, 0.25: 1.06, 1.0: 0.0}, smooth=False)
    A.append(fade)
    return A


NIGHT_STATES = {0: ["hidden"], 1: ["emerge"], 2: ["idle"], 3: ["fold"], 4: ["fade"], 5: ["bite"]}


# ---------------------------------------------------------------- formations
WHEEL_R = 30.0
WHEEL_H = 42.0          # axle height (units): outer rim touches the ground
WHEEL_SCALE = 1.6
WHEEL_SPIN = 120.0      # deg/s while rolling


def wheel_model():
    m = Model("dn_dreamer_wheel", density=1.0, bounds=(14, 14, (0, 4, 0)))
    root = m.bone("root")
    roll = m.bone("roll", root, pivot=(0, WHEEL_H, 0))
    g = gilt(0.35)
    roll.box((0, WHEEL_H, 0), (16, 10, 10), g)
    roll.box((0, WHEEL_H, 0), (18, 6, 6), tex.glow_flat(PEACH, 1.0, core="#ffffff"))
    for side in (-1, 1):
        ring(roll, (side * 7, WHEEL_H, 0), WHEEL_R + 9, 16, (12.5, 2.4, 1.6), g, axis="x")
    for k in range(8):
        a = k * 45
        b = m.bone(f"wdoor{k + 1}", roll, pivot=(0, WHEEL_H, 0), rot=(-a, 0, 0))
        b.box((0, WHEEL_H + 10, 0), (2, 20, 2), tex.wood("#5a4a5e", "#3a2e40"))
        b.cube((-6.5, WHEEL_H + 17, -0.9), (13, 24, 1.8), tex.wood("#6e5a6e", "#3e3246"),
               mats={"north": door_mat(MAUVE if k % 2 else PEACH, "#8e3446" if k % 2 else SGOLD, key=f"wd{k % 2}",
                                       alt_night=False),
                     "south": door_mat(MAUVE if k % 2 else PEACH, "#8e3446" if k % 2 else SGOLD, key=f"wd{k % 2}",
                                       alt_night=False)})
        b.box((0, WHEEL_H + 42.5, 0), (14, 1.6, 2.6), g)
    return m


def wheel_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    asm = Anim("assemble", length=1.0, loop="hold")
    for k in range(8):
        t0 = k * 0.07
        asm.pos(f"wdoor{k + 1}", {0: (0, 60 + k * 5, 0), t0: (0, 60 + k * 5, 0), t0 + 0.5: (0, -2, 0), t0 + 0.65: (0, 0, 0)})
        asm.scl(f"wdoor{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.4: 1.0}, smooth=False)
    asm.rot("roll", {0: (0, 0, 0), 1.0: (-90, 0, 0)})
    roll = Anim("roll", loop=True)
    roll.rot("roll", (spin(-WHEEL_SPIN), 0, 0))
    brk = Anim("break", length=0.9, loop="hold")
    for k in range(8):
        brk.pos(f"wdoor{k + 1}", {0: (0, 0, 0), 0.9: (0, 50, 0)})
        brk.rot(f"wdoor{k + 1}", {0: (0, 0, 0), 0.9: (0, 0, 90 + k * 30)})
    brk.scl("root", {0: 1.0, 0.5: 1.05, 0.9: 0.0}, smooth=False)
    return [hidden, asm, roll, brk]


DRILL_H = 120.0


def drill_model():
    m = Model("dn_dreamer_drill", density=1.0, bounds=(14, 22, (0, 6, 0)))
    root = m.bone("root")
    sp = m.bone("auger", root)
    g = gilt(0.45)
    st = tex.wood("#f6e9cf", "#d6bf94", plank=3)
    sp.box((0, DRILL_H / 2, 0), (5, DRILL_H, 5), tex.glow_flat("#fff3c8", 0.9, core="#ffffff"))
    sp.box((0, 2, 0), (2, 6, 2), g)
    for f in range(4):
        fb = m.bone(f"flight{f + 1}", sp)
        for k in range(6):
            i = f * 6 + k
            y = DRILL_H - 4 - i * 4.8
            r = 6 + (y / DRILL_H) * 26
            a = i * 32
            fb.box((r / 2 + 2, y, 0), (r, 2, 6), st, rot=(0, -a, 0), pivot=(0, y, 0), variant=i % 2)
            fb.box((r + 2, y + 4, 0), (0.8, 8, 0.8), g, rot=(0, -a, 0), pivot=(0, y, 0))
    sp.box((0, DRILL_H + 1, 0), (16, 2, 16), g)
    sp.plane("z", (0, DRILL_H + 10, 0), 10, 16, door_mat(PEACH, SGOLD, glass="#fff0c8", key="drilldoor"))
    return m


def drill_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    form = Anim("form", length=1.0, loop="hold")
    for f in range(4):
        t0 = f * 0.15
        form.scl(f"flight{f + 1}", {0: 0.0, t0: 0.0, t0 + 0.4: 1.1, t0 + 0.5: 1.0}, smooth=False)
        form.rot(f"flight{f + 1}", {0: (0, 90, 0), t0 + 0.5: (0, 0, 0)})
    sp = Anim("spin", loop=True)
    sp.rot("auger", (0, spin(220), 0))
    bore = Anim("bore", loop=True)
    bore.rot("auger", (0, spin(720), 0))
    brk = Anim("break", length=0.8, loop="hold")
    for f in range(4):
        brk.pos(f"flight{f + 1}", {0: (0, 0, 0), 0.8: (0, 20 + f * 8, 0)})
        brk.scl(f"flight{f + 1}", {0: 1.0, 0.3: 1.3, 0.8: 0.0}, smooth=False)
    brk.scl("auger", {0: 1.0, 0.8: (0.0, 1.0, 0.0)}, smooth=False)
    return [hidden, form, sp, bore, brk]


ROOM_BIG = 5.5      # expanded room scale (16 units * 5.5 = 5.5 blocks)


def roomcube_model():
    m = Model("dn_dreamer_roomcube", density=2.0, bounds=(10, 10, (0, 3, 0)))
    root = m.bone("root")
    rm = m.bone("room", root)
    W = tex.wood("#e9d6b8", "#b8946a", plank=2)
    rm.box((0, 0.5, 0), (16, 1, 16), W)
    rm.plane("y", (0, 1.05, 0), 10, 10, tex.fabric("#c98aa4", SGOLD, stripe_w=1, glow=0.2), faces=("up",))
    rm.box((-2, 2.5, 3), (8, 2.4, 6), tex.flat("#fff6ea", glow=0.2))
    rm.box((-2.5, 3.9, 2.8), (6, 0.6, 6.2), tex.fabric(PINK, "#f6d9e4", stripe_w=1, glow=0.2))
    rm.box((5, 3, 5), (2, 4, 2), W)
    rm.box((5, 6, 5), (2.6, 2, 2.6), lamp_mat())
    outer = porc()
    walls = [("wall_n", (0, 0.5, -8), "z", (0, 8.5, -8)), ("wall_s", (0, 0.5, 8), "z", (0, 8.5, 8)),
             ("wall_w", (-8, 0.5, 0), "x", (-8, 8.5, 0)), ("wall_e", (8, 0.5, 0), "x", (8, 8.5, 0))]
    paper = [wallpaper(PINK, "#f4cfdc", glow=0.3), wallpaper(PBLUE, "#d9e8f7", glow=0.3)]
    for i, (n, hinge, ax, c) in enumerate(walls):
        b = m.bone(n, rm, pivot=hinge)
        size = (16, 16, 1) if ax == "z" else (1, 16, 16)
        b.box(c, size, outer, mats={("south" if c[2] < 0 else "north") if ax == "z" else ("east" if c[0] < 0 else "west"):
                                    paper[i % 2]})
        if i == 0:
            b.plane("z", (2, 10, -8.6), 5, 6, window_mat(), faces=("north",))
        if i == 2:
            b.plane("x", (-8.6, 7, 3), 5, 10, door_mat(PEACH, SGOLD, glass="#fff0c8", key="rcdoor"), faces=("west",))
    rm.box((0, 16.8, 0), (17, 1.2, 17), tex.fabric(PINK, "#f3d2df", stripe_w=2, glow=0.15))
    return m


OUT = {"wall_n": (-90, 0, 0), "wall_s": (90, 0, 0), "wall_w": (0, 0, 90), "wall_e": (0, 0, -90)}
IN = {"wall_n": (25, 0, 0), "wall_s": (-25, 0, 0), "wall_w": (0, 0, -25), "wall_e": (0, 0, 25)}


def roomcube_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    fly = Anim("fly", loop=True, length=1.0)
    fly.rot("room", (spin(260), spin(180), 0))
    fly.scl("root", 0.4)
    exp = Anim("expand", length=0.8, loop="hold")    # unfolds flat, grows, walls swing up around the enemy
    exp.scl("root", {0: 0.4, 0.35: ROOM_BIG * 1.1, 0.5: ROOM_BIG}, smooth=False)
    for n in OUT:
        exp.rot(n, {0: OUT[n], 0.4: OUT[n], 0.65: tuple(-c * 0.08 for c in OUT[n]), 0.8: (0, 0, 0)})
    crush = Anim("crush", length=0.5, loop="hold")
    crush.scl("root", {0: ROOM_BIG, 0.12: ROOM_BIG * 0.9, 0.5: ROOM_BIG * 0.95}, smooth=False)
    for n in IN:
        crush.rot(n, {0: (0, 0, 0), 0.12: IN[n], 0.5: tuple(c * 0.8 for c in IN[n])})
    fade = Anim("fade", length=0.7, loop="hold")
    fade.scl("root", {0: ROOM_BIG * 0.95, 0.7: 0.0}, smooth=False)
    for n in OUT:
        fade.rot(n, {0: tuple(c * 0.8 for c in IN[n]), 0.5: OUT[n]})
    return [hidden, fly, exp, crush, fade]


def shard_model():
    m = Model("dn_dreamer_shard", density=2.0, bounds=(5, 5, (0, 1, 0)))
    root = m.bone("root")
    w = m.bone("win", root, pivot=(0, 8, 0))
    w.box((0, 8, 0), (11, 14, 1.2), window_mat("#cfe4ff", SGOLD, IVORY, arch=True, glow=1.0))
    w.box((0, 16, 0), (8, 2, 1.4), gilt(0.5))
    glass = tex.crystal("#dceeff", "#9cc0ee", "#ffffff", a=0.6, glow=0.6)
    tr = m.bone("trail", w, pivot=(0, 8, 0))
    for k in range(4):
        tr.box((-3 + k * 2, 8 - k, 2 + k * 3), (1.6, 4, 0.2), glass, rot=(0, 0, 30 * k), pivot=(-3 + k * 2, 8 - k, 2 + k * 3))
    return m


def shard_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    fly = Anim("fly", loop=True)
    fly.rot("win", (0, 0, spin(540)))
    fly.scl("root", 1.0)
    sh = Anim("shatter", length=0.4, loop="hold")
    sh.scl("root", {0: 1.0, 0.1: 1.6, 0.4: 0.0}, smooth=False)
    sh.rot("win", {0: (0, 0, 0), 0.4: (90, 0, 180)})
    return [hidden, fly, sh]


STAIRS_N = 10
STAIR_SCALE = 2.0


def stairs_model():
    m = Model("dn_dreamer_stairs", density=1.0, bounds=(14, 8, (0, 2, -7)))
    root = m.bone("root")
    st = tex.wood("#fbf3e4", "#dccdb0", plank=2)
    g = gilt(0.3)
    run = tex.fabric(PINK, SGOLD, stripe_w=1, glow=0.15)
    for k in range(STAIRS_N):
        z = -5 - k * 10
        y = (STAIRS_N - 1 - k) * 4
        b = m.bone(f"step{k + 1}", root, pivot=(0, y, z))
        b.box((0, y + 1.5, z), (26, 3, 10), st, variant=k % 2)
        b.box((0, y + 3.1, z), (10, 0.3, 10.2), run, faces=("up",))
        if y > 0:
            b.box((0, y / 2, z + 4), (22, y, 1.5), porc(), variant=k % 3)
        for sx in (-1, 1):
            b.box((sx * 12.5, y + 7, z), (1, 8, 1), g)
        if k % 3 == 0:
            b.box((0, y + 11.2, z), (26, 0.8, 1), g)
    return m


def stairs_anims():
    hidden = Anim("hidden", loop=True)
    hidden.scl("root", 0.0)
    spill = Anim("spill", length=2.0, loop="hold")
    for k in range(STAIRS_N):
        t0 = 0.2 + k * 0.12
        spill.pos(f"step{k + 1}", {0: (0, 80, 30), t0: (0, 80, 30), t0 + 0.18: (0, -2, 0), t0 + 0.3: (0, 1, 0), t0 + 0.4: (0, 0, 0)},
                  smooth=False)
        spill.rot(f"step{k + 1}", {0: (40, 0, 20), t0: (40, 0, 20), t0 + 0.2: (0, 0, 0)}, smooth=False)
        spill.scl(f"step{k + 1}", {0: 0.0, t0: 0.0, t0 + 0.05: 1.0}, smooth=False)
    fade = Anim("fade", length=1.0, loop="hold")
    for k in range(STAIRS_N):
        fade.pos(f"step{k + 1}", {0: (0, 0, 0), 0.3 + k * 0.05: (0, 0, 0), 1.0: (0, -30, 0)})
    fade.scl("root", {0: 1.0, 0.6: 1.0, 1.0: 0.0}, smooth=False)
    return [hidden, spill, fade]


def build(pack):
    da = dream_anims()
    dz = [garden(), cloudcity(), stairway()]
    pack.actor("dn_dreamer_dream", dz[0], da, ZONE_STATES | {5: ["idle"]}, always=["turn"], kinds=dz[1:], lifetime=120,
               display="Dream Zone")
    na = night_anims()
    nz = [upside_room(), corridor(), living_doors()]
    pack.actor("dn_dreamer_night", nz[0], na, NIGHT_STATES, always=["turn"], kinds=nz[1:], lifetime=120,
               display="Nightmare Zone", blend=0.15)
    dby = {a.name: a for a in da}
    nby = {a.name: a for a in na}
    for i, mm in enumerate(dz):
        pack.preview(f"dn_dreamer_zone_d{i}", mm, [(dby["idle"], 0)], views=((25, 25), (115, 15)), cell=(320, 320))
    for i, mm in enumerate(nz):
        pack.preview(f"dn_dreamer_zone_n{i}", mm, [(nby["bite"], 0.35)], views=((25, 25), (115, 15)), cell=(320, 320))
    wm = wheel_model()
    pack.actor("dn_dreamer_wheel", wm, wheel_anims(), {0: ["hidden"], 1: ["assemble"], 2: ["roll"], 3: ["break"]},
               scale=WHEEL_SCALE, lifetime=60, display="Wheel of Doors")
    dm = drill_model()
    pack.actor("dn_dreamer_drill", dm, drill_anims(), {0: ["hidden"], 1: ["form"], 2: ["spin"], 3: ["bore"], 4: ["break"]},
               scale=1.5, lifetime=60, display="Spiral Stair")
    rc = roomcube_model()
    rca = roomcube_anims()
    pack.actor("dn_dreamer_roomcube", rc, rca, {0: ["hidden"], 1: ["fly"], 2: ["expand"], 3: ["crush"], 4: ["fade"]},
               lifetime=60, display="Room")
    sm = shard_model()
    pack.actor("dn_dreamer_shard", sm, shard_anims(), {0: ["hidden"], 1: ["fly"], 2: ["shatter"]}, scale=1.5, lifetime=40,
               display="Window Shard")
    stm = stairs_model()
    sta = stairs_anims()
    pack.actor("dn_dreamer_stairs", stm, sta, {0: ["hidden"], 1: ["spill"], 2: ["fade"]}, scale=STAIR_SCALE, lifetime=60,
               display="Spilled Stairs")
    pack.preview("dn_dreamer_formations", wm, [None], views=((70, 10), (20, 20)), cell=(300, 300))
    pack.preview("dn_dreamer_drill", dm, [None], views=((20, 15),), cell=(300, 300))
    rby = {a.name: a for a in rca}
    pack.preview("dn_dreamer_roomcube", rc, [(rby["expand"], 0.55)], views=((25, 30),), cell=(300, 300))
    pack.preview("dn_dreamer_stairs", stm, [None], views=((60, 25),), cell=(300, 300))
