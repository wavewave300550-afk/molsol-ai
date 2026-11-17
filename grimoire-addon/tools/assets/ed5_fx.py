"""ED05 particles and original sounds: stone rising / grinding, the museum hush, bone clatter with a
pitched resonance per species, thin and distant echoes of each living dragon's voice (derived from the
living modules' own synthesis), the imprint projection and the fracture."""
from __future__ import annotations

import numpy as np

from kit import synth as sy

from . import ed_air, ed_heat, ed_nature, ed_tide
from .a_fx_common import particles
from .ed5_bones import GLOW, GLOW2, SPECIES

RUNES = [f"rune{i}" for i in range(1, 7)]


def _a(c, a):
    return c + a


def build_particles(pack):
    fx = particles(pack)
    fx.effect("ed5_bonedust", "puff", count=8, life=(0.7, 1.4), size=(0.4, 1.1), shape=("disc", 1.0), speed=(0.6, 1.8),
              accel=(0, 0.4, 0), drag=1.6, colors=["#e9dfc6bb", "#b8a98544", "#b8a98500"], blend="blend", spin=(360, 40))
    fx.effect("ed5_rock", "rock", count=9, life=(0.7, 1.3), size=(0.18, 0.12), shape=("disc", 1.0), direction=(0, 1, 0),
              speed=(3, 7), accel=(0, -16, 0), colors=["#8a7a62ff", "#5d4f3cff"], blend="alpha", spin=(360, 240), collide=True)
    fx.effect("ed5_dust", "smoke", count=10, life=(1.2, 2.2), size=(0.9, 2.4), shape=("disc", 2.2), speed=(0.8, 2.2),
              accel=(0, 0.6, 0), drag=1.4, colors=["#9c8a6ccc", "#7a6a5266", "#7a6a5200"], blend="blend", spin=(360, 25))
    fx.effect("ed5_moss", None, sprites=["leaf", "dot"], count=8, life=(1.2, 2.2), size=(0.12, 0.06), shape=("sphere", 1.6),
              speed=(0.3, 1.0), accel=(0, -0.5, 0), drag=1.2, colors=["#d8ffb0ff", "#8fe85aee", "#3f8a2a00"], spin=(360, 120))
    fx.effect("ed5_ember", "ember", count=10, life=(0.6, 1.3), size=(0.1, 0.0), shape=("sphere", 0.8), speed=(0.8, 2.6),
              accel=(0, 1.6, 0), drag=0.8, colors=["#fff2c0ff", "#ff9a3aff", "#c8380a00"])
    fx.effect("ed5_haze", "smoke", count=6, life=(0.8, 1.5), size=(0.6, 1.5), shape=("disc", 0.9), speed=(0.4, 1.2),
              accel=(0, 1.8, 0), drag=1.0, colors=["#ffb46a55", "#ff7a2a33", "#ff7a2a00"], blend="blend", spin=(360, 50))
    fx.effect("ed5_frost", "flake", count=9, life=(0.9, 1.8), size=(0.13, 0.05), shape=("sphere", 1.2), speed=(0.4, 1.4),
              accel=(0, -0.7, 0), drag=1.0, colors=["#ffffffff", "#cfefffdd", "#7fd8ff00"], spin=(360, 90))
    fx.effect("ed5_shard", "shard", count=12, life=(0.5, 1.0), size=(0.2, 0.06), shape=("sphere", 0.5), speed=(4, 9),
              accel=(0, -8, 0), drag=0.4, colors=["#ffffffff", "#bfeaffff", "#5fb6ea00"], spin=(360, 380))
    fx.effect("ed5_glint", "star", count=4, life=(0.3, 0.6), size=(0.26, 0.0), shape=("sphere", 1.0),
              colors=["#ffffffff", "#bff4ff00"], spin=(360, 180))
    fx.effect("ed5_feather", "feather", count=5, life=(1.2, 2.2), size=(0.24, 0.14), shape=("sphere", 1.2), speed=(0.4, 1.4),
              accel=(0, -0.6, 0), drag=1.8, colors=["#ffffffcc", "#cfe2ffaa", "#a9c8ff00"], blend="blend", spin=(360, 160))
    fx.effect("ed5_wind", None, sprites=["wave", "arc", "slash"], count=6, life=(0.35, 0.7), size=(0.7, 0.2),
              shape=("disc", 2.0), speed=(5, 10), drag=2.4, colors=["#ffffffee", "#d6e8ffaa", "#a9c8ff00"])
    fx.effect("ed5_rune", None, sprites=RUNES, count=5, life=(1.0, 1.8), size=(0.22, 0.06), shape=("sphere", 1.2),
              speed=(0.2, 0.7), accel=(0, 0.9, 0), drag=0.6, colors=["#fff0c8ff", "#e0b060ff", "#8a6a3a00"])
    fx.effect("ed5_rune_fall", None, sprites=RUNES, count=4, life=(0.8, 1.3), size=(0.26, 0.1), shape=("disc", 1.6),
              direction=(0, -1, 0), speed=(3.0, 5.5), drag=0.2, colors=["#ffffffff", "#ffe2a0ff", "#8a6a3a00"])
    fx.effect("ed5_crack", "spark", count=12, life=(0.4, 0.9), size=(0.14, 0.0), shape=("disc", 2.5), direction=(0, 1, 0),
              speed=(2.0, 5.0), accel=(0, -4, 0), drag=0.8, colors=["#fff2c8ff", "#e0a050ff", "#8a6a3a00"], spin=(360, 200))
    fx.effect("ed5_line", "slash", count=1, life=(0.45, 0.6), size=(1.3, 0.4), facing="emitter_transform_xz",
              colors=["#ffffffff", "#d8ffb0cc", "#8a6a3a00"])
    fx.effect("ed5_frag", None, sprites=["bone", "rock", "scale"] + RUNES, count=10, life=(2.2, 3.6), size=(0.3, 0.12),
              shape=("sphere", 3.0), speed=(0.6, 2.4), accel=(0, -1.1, 0), drag=0.9,
              colors=["#fffbe8ff", "#ffe0a0ee", "#e9dfc6aa", "#8a6a3a00"], spin=(360, 140))
    fx.effect("ed5_frag_big", "rock", count=7, life=(1.4, 2.4), size=(0.45, 0.3), shape=("sphere", 2.0), speed=(2, 5),
              accel=(0, -9, 0), drag=0.3, colors=["#c9b48aff", "#8a7a62ff", "#5d4f3c00"], blend="alpha", spin=(360, 200))
    fx.effect("ed5_glow_mote", "dot", count=8, life=(1.2, 2.2), size=(0.08, 0.0), shape=("sphere", 3.5), speed=(0.05, 0.4),
              accel=(0, 0.5, 0), colors=["#fff6dcff", "#e0b06000"])
    for sp in SPECIES:
        g, g2 = GLOW[sp], GLOW2[sp]
        fx.effect(f"ed5_ring_{sp}", "ringthin", count=1, life=(0.55, 0.65), size=(0.5, 6.5), facing="emitter_transform_xz",
                  colors=[_a(g2, "ff"), _a(g, "cc"), _a(g, "00")])
        fx.effect(f"ed5_ray_{sp}", "beam", count=2, life=(0.25, 0.45), size=(0.22, 0.05), size_y=(0.9, 1.6),
                  shape=("sphere", 0.3), colors=[_a(g2, "ff"), _a(g, "ee"), _a(g, "00")], facing="lookat_y")
        fx.effect(f"ed5_mote_{sp}", "dot", count=7, life=(1.0, 2.0), size=(0.1, 0.0), shape=("sphere", 2.6), speed=(0.1, 0.5),
                  accel=(0, 0.6, 0), colors=[_a(g2, "ff"), _a(g, "aa"), _a(g, "00")])
        fx.effect(f"ed5_burst_{sp}", "star", count=10, life=(0.4, 0.9), size=(0.3, 0.0), shape=("sphere", 0.8),
                  speed=(3, 7), drag=1.6, colors=["#ffffffff", _a(g2, "ff"), _a(g, "00")], spin=(360, 300))


# ================================================================ sounds
def knock(f, dur=0.4, q=6.0, decay=0.08, click=0.6):
    """Hollow struck bone: resonant band-passed impulse plus a decaying body tone."""
    t = sy.t_axis(dur)
    exc = sy.noise(dur) * np.exp(-t / 0.003)
    body = sy.bandpass(exc, f, q) * 3 + sy.bandpass(exc, f * 2.7, q * 1.3) * 1.2 * click
    body += np.sin(2 * np.pi * f * t) * np.exp(-t / decay) * 0.9 + np.sin(2 * np.pi * f * 1.52 * t) * np.exp(-t / (decay * 0.6)) * 0.35
    return sy.norm(sy.fade(body, 0.0005, 0.02))


def scatter(dur, events):
    out = np.zeros(int(sy.SR * dur))
    for at, sig, g in events:
        i = int(sy.SR * at)
        if i < len(out):
            out[i:i + len(sig)] += sig[:len(out) - i] * g
    return out


def clatter(sp, n=None, seed=3):
    rng = np.random.default_rng(seed)
    if sp == "nature":      # large hollow knocks
        ev = [(t, knock(rng.uniform(120, 230), 0.7, 5, 0.16), rng.uniform(0.5, 1.0)) for t in np.sort(rng.random(7)) * 0.8]
        sig = sy.at(1.6, (0.0, scatter(1.6, ev)), (0.0, sy.thump(0.9, 80, 34, 0.3) * 0.5))
        return sy.reverb(sy.norm(sig), 1.2, 0.3)
    if sp == "heat":        # dry rattles
        ev = [(t, knock(rng.uniform(1400, 2600), 0.06, 10, 0.008, 0.3), rng.uniform(0.3, 1.0)) for t in
              np.sort(rng.random(34) ** 1.3) * 0.5]
        dry = sy.highpass(sy.noise(0.6), 2500) * np.exp(-sy.t_axis(0.6) / 0.15) * 0.15
        return sy.reverb(sy.norm(scatter(0.8, ev) + np.pad(dry, (0, int(sy.SR * 0.2)))), 0.6, 0.15)
    if sp == "tide":        # glassy clicks
        ev = [(t, sy.norm(sy.bell(rng.uniform(2600, 4800), 0.5, bright=1.4, inharm=1.25)) * 0.6 +
               knock(rng.uniform(1800, 3000), 0.5, 14, 0.05, 0.4) * 0.6, rng.uniform(0.4, 1.0)) for t in np.sort(rng.random(9)) * 0.6]
        return sy.reverb(sy.norm(sy.at(1.1, (0.0, scatter(1.1, ev)), (0.0, sy.shimmer(1.0, 3200, 8) * 0.2))), 1.0, 0.3)
    # air: bamboo-like flutter (hollow tubes knocking in a quick rhythm) + wing swish
    ev = [(0.03 + k * 0.07 + rng.uniform(0, 0.015), knock(rng.choice([520, 610, 740, 880]) * rng.uniform(0.97, 1.03), 0.25, 9,
                                                          0.05, 0.9), 0.5 + 0.5 * np.sin(k * 0.6)) for k in range(9)]
    return sy.reverb(sy.norm(sy.at(0.9, (0.0, scatter(0.9, ev)), (0.0, sy.whoosh(0.8, 600, 2600) * 0.35))), 0.7, 0.22)


def thin_distant(sig, lo=420, hi=2600, pitch=1.0, rv=3.2):
    """A living voice remembered by stone: thinned, slightly pitched, pushed far back in a long hall."""
    s = sy.pitch(sig, pitch) if pitch != 1.0 else sig
    s = sy.lowpass(sy.highpass(s, lo), hi)
    s = sy.norm(s) * 0.7
    s = np.concatenate([np.zeros(int(sy.SR * 0.12)), s])
    return sy.reverb(s, rv, 0.72, tone=3200, predelay=0.09)


def stone_grind(dur, f0=45, f1=80):
    return sy.norm(sy.at(dur, (0.0, sy.lowpass(sy.creak(dur, f0, f1, 0.5), 900) * 0.8), (0.0, sy.rumble(dur, 48, 3.0) * 0.7),
                         (0.1, sy.crack(dur * 0.8, 1800, 34) * 0.3)))


def build_sounds(pack):
    rv = sy.reverb
    # -- the museum hush: hall air, a sub drone and far, slow bronze chimes
    t = sy.t_axis(5.0)
    air = sy.lowpass(sy.noise(5.0), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t))
    drone = (np.sin(2 * np.pi * 41.2 * t) + 0.4 * np.sin(2 * np.pi * 61.7 * t + 1)) * 0.35
    chimes = sy.at(5.0, (0.6, sy.bell(659.3 * 0.75, 2.4, bright=0.5) * 0.12), (2.6, sy.bell(493.9 * 0.75, 2.2, bright=0.5) * 0.1))
    hush = sy.fade(sy.norm(air * 0.55 + drone + chimes), 1.2, 1.4)
    sy.save(pack, "ed5_hush", rv(hush, 2.6, 0.5), volume=0.55, max_distance=72)
    # -- the Grimoire opens; inscriptions fall
    op = sy.at(2.4, (0.0, sy.thump(0.8, 70, 30, 0.2) * 0.6), (0.05, sy.scribble(1.4, 7) * 0.45),
               (0.15, sy.bell(246.9, 2.0, bright=0.6) * 0.45), (0.5, sy.bell(370.0, 1.8, bright=0.6) * 0.3),
               (0.2, sy.pad(61.7, 2.2, cutoff=500) * 0.5))
    sy.save(pack, "ed5_open", rv(op, 2.4, 0.45), max_distance=72)
    ins = sy.at(2.2, (0.0, sy.shimmer(1.6, 1500, 16)[::-1] * 0.35), (0.0, sy.scribble(1.6, 9) * 0.35),
                (1.55, sy.thump(0.6, 95, 36, 0.4) * 0.8), (1.55, sy.crack(0.5, 2200, 14) * 0.35))
    sy.save(pack, "ed5_inscribe", rv(ins, 1.6, 0.35), max_distance=64)
    # -- stone: cracking earth and a slab rising, the monument grinding, locking
    rise = sy.at(2.6, (0.0, sy.crack(0.9, 2400, 30) * 0.6), (0.0, sy.thump(0.7, 80, 30, 0.6) * 0.7),
                 (0.2, stone_grind(2.0, 40, 75) * 0.9), (1.9, sy.thump(0.7, 64, 26, 0.5) * 0.8))
    sy.save(pack, "ed5_rise", rv(rise, 1.8, 0.35), variants=[rv(sy.pitch(rise, 0.9), 1.8, 0.35)], max_distance=80)
    sy.save(pack, "ed5_grind", rv(sy.at(3.2, (0.0, stone_grind(3.0, 35, 60)), (0.6, sy.lowpass(sy.creak(2.0, 60, 40, 0.4), 700) * 0.5)),
                                   2.0, 0.4), max_distance=80)
    lock = sy.at(2.4, (0.0, sy.thump(1.2, 58, 22, 0.8)), (0.02, sy.bell(98.0, 2.2, bright=0.7, inharm=1.15) * 0.55),
                 (0.02, sy.crack(0.8, 1500, 30) * 0.45), (0.05, sy.rumble(2.0, 36, 1.0) * 0.6))
    sy.save(pack, "ed5_lock", rv(lock, 2.6, 0.45), max_distance=96)
    aw = sy.at(2.2, (0.0, sy.pad(98.0, 2.0, cutoff=900) * 0.5), (0.0, sy.osc(sy.sweep(196, 294, 1.8)) * sy.env(1.8, 0.6, 0.2, 0.8, 0.6) * 0.3),
               (0.4, sy.shimmer(1.6, 1800, 14) * 0.35), (0.1, sy.crack(1.2, 3000, 12) * 0.2))
    sy.save(pack, "ed5_awaken", rv(aw, 2.0, 0.45), variants=[rv(sy.pitch(aw, 1.12), 2.0, 0.45), rv(sy.pitch(aw, 0.9), 2.0, 0.45)],
            max_distance=80)
    # -- bones: clatter per species, peel out of the slab, settle back, sweeps
    for i, sp in enumerate(SPECIES):
        c = clatter(sp, seed=11 + i)
        sy.save(pack, f"ed5_clatter_{sp}", c, variants=[sy.pitch(c, 1.08), sy.pitch(c, 0.93)], max_distance=56)
    peel = sy.at(2.0, (0.0, sy.crack(1.0, 2600, 40) * 0.6), (0.05, stone_grind(0.9, 70, 120) * 0.5),
                 (0.3, sy.whoosh(1.2, 200, 2200) * 0.5), (0.7, sy.thump(0.5, 110, 50, 0.6) * 0.4))
    sy.save(pack, "ed5_peel", rv(peel, 1.4, 0.35), max_distance=72)
    settle = sy.at(1.6, (0.0, sy.whoosh(0.9, 2400, 300) * 0.5), (0.55, sy.thump(0.8, 90, 34, 0.6) * 0.8),
                   (0.56, sy.crack(0.7, 1600, 26) * 0.4), (0.6, sy.shimmer(0.9, 1400, 8) * 0.2))
    sy.save(pack, "ed5_settle", rv(settle, 1.6, 0.4), max_distance=72)
    sw = sy.whoosh(0.7, 180, 1600, 1.4)
    sy.save(pack, "ed5_sweep", rv(sw, 0.8, 0.2), variants=[rv(sy.pitch(sw, 1.15), 0.8, 0.2)], max_distance=48)
    # -- echoes of the living voices (derived from the living dragons' own synthesis)
    call = ed_nature._call(2.8, [(0, 58), (0.3, 78), (0.65, 66), (1.0, 48)], horn=1.0, whale=0.5)
    sy.save(pack, "ed5_echo_nature", thin_distant(call, 260, 2000, 1.0, 3.6), volume=0.8, max_distance=96)
    roar = ed_heat._voice(1.6, 160, 100, 0.4)
    sy.save(pack, "ed5_echo_heat", thin_distant(roar, 500, 3000, 0.94, 2.8), volume=0.75, max_distance=80)
    bel = sy.at(2.2, (0.0, ed_tide._bellow(1.6, 72, 98)), (1.0, ed_tide._clicks(0.7, 8, 2700) * 0.5))
    sy.save(pack, "ed5_echo_tide", thin_distant(bel, 380, 3400, 1.05, 3.0), volume=0.75, max_distance=80)
    shr = sy.at(1.4, (0.0, ed_air._shriek(0.8)), (0.5, ed_air._chirr(0.5) * 0.6))
    sy.save(pack, "ed5_echo_air", thin_distant(shr, 900, 5200, 0.9, 2.6), volume=0.7, max_distance=80)
    # -- the four skeletal attacks
    slam = sy.at(2.4, (0.0, sy.thump(1.6, 60, 18, 0.8)), (0.0, sy.crack(1.0, 2600, 34) * 0.55), (0.03, sy.rumble(2.2, 36, 1.4) * 0.8),
                 (0.05, clatter("nature", seed=99) * 0.5))
    sy.save(pack, "ed5_slam", rv(slam, 2.0, 0.35), max_distance=112)
    sp_ = sy.at(1.2, (0.0, sy.crack(0.7, 2000, 28) * 0.7), (0.02, sy.thump(0.7, 120, 44, 0.6) * 0.7),
                (0.06, sy.lowpass(sy.creak(0.6, 260, 140, 0.3), 1500) * 0.35))
    sy.save(pack, "ed5_spike", rv(sp_, 1.0, 0.3), variants=[rv(sy.pitch(sp_, 1.12), 1.0, 0.3), rv(sy.pitch(sp_, 0.88), 1.0, 0.3)],
            max_distance=64)
    tt = sy.t_axis(1.6)
    burn = sy.at(1.8, (0.0, sy.wind(1.5, 200, 900, 1.3, 0.4) * 0.8), (0.0, sy.crack(1.5, 3200, 40) * 0.3),
                 (0.0, sy.lowpass(sy.noise(1.6), 300) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt)) * 0.5))
    sy.save(pack, "ed5_burn", rv(burn, 1.0, 0.2), max_distance=64)
    skid = sy.at(1.0, (0.0, sy.crack(0.8, 1800, 40) * 0.6), (0.0, sy.wind(0.8, 1600, 400, 1.5, 0.2) * 0.5),
                 (0.0, clatter("heat", seed=7) * 0.6))
    sy.save(pack, "ed5_skid", skid, max_distance=56)
    ice = sy.at(1.4, (0.0, sy.crack(0.8, 6500, 30) * 0.8), (0.0, sy.shimmer(1.2, 2600, 22) * 0.5),
                (0.02, sy.thump(0.5, 160, 70, 0.5) * 0.4), (0.1, sy.bell(1760, 0.9, bright=1.4, inharm=1.3) * 0.25))
    sy.save(pack, "ed5_ice", rv(ice, 1.4, 0.35), variants=[rv(sy.pitch(ice, 1.1), 1.4, 0.35)], max_distance=64)
    sy.save(pack, "ed5_icecrack", rv(sy.at(0.9, (0.0, sy.crack(0.6, 5500, 22)), (0.05, sy.shimmer(0.7, 3000, 10) * 0.4)), 0.8, 0.25),
            max_distance=48)
    gust = sy.at(1.2, (0.0, sy.whoosh(1.0, 300, 2400, 1.2)), (0.0, sy.thump(0.5, 90, 40, 0.3) * 0.5),
                 (0.05, clatter("air", seed=5) * 0.3))
    sy.save(pack, "ed5_gust", rv(gust, 0.9, 0.25), variants=[rv(sy.pitch(gust, 1.12), 0.9, 0.25)], max_distance=64)
    # -- phase III: tablets blaze, imprints project, all four together, the fracture
    bl = sy.at(2.6, (0.0, sy.pad(73.4, 2.4, cutoff=700) * 0.6), (0.0, sy.osc(sy.sweep(146.8, 220, 2.2)) * sy.env(2.2, 0.8, 0.2, 0.8, 0.6) * 0.35),
               (0.2, sy.shimmer(2.0, 2200, 26) * 0.4), (0.0, sy.crack(2.0, 2500, 18) * 0.25))
    sy.save(pack, "ed5_blaze", rv(bl, 2.4, 0.45), max_distance=96)
    pr = sy.at(2.0, (0.0, sy.osc(sy.sweep(880, 110, 0.6, 0.5)) * sy.env(0.6, 0.01, 0.1, 0.7, 0.3) * 0.5),
               (0.0, sy.pad(55.0, 1.8, cutoff=600) * 0.6), (0.55, sy.thump(1.0, 70, 26, 0.7)), (0.56, sy.crack(1.0, 2200, 30) * 0.5))
    sy.save(pack, "ed5_project", rv(pr, 2.2, 0.4), variants=[rv(sy.pitch(pr, 1.1), 2.2, 0.4), rv(sy.pitch(pr, 0.92), 2.2, 0.4)],
            max_distance=112)
    fin = sy.at(3.6, (0.0, sy.osc(sy.sweep(1200, 80, 0.9, 0.4)) * sy.env(0.9, 0.01, 0.1, 0.7, 0.4) * 0.4),
                (0.8, sy.thump(2.0, 52, 16, 0.9)), (0.8, sy.crack(1.4, 3000, 60) * 0.6), (0.82, sy.rumble(2.6, 32, 1.2)),
                (0.85, sy.shimmer(2.2, 2400, 30) * 0.35), (0.9, sy.bell(110, 2.4, bright=0.8, inharm=1.2) * 0.4))
    sy.save(pack, "ed5_finale", rv(fin, 3.0, 0.45), max_distance=128)
    frac = sy.at(3.0, (0.0, sy.crack(1.2, 2200, 70) * 0.8), (0.0, sy.thump(1.0, 70, 26, 0.6) * 0.7),
                 (0.1, sy.lowpass(sy.crack(1.8, 900, 90), 1600) * 0.6), (0.3, sy.shimmer(2.4, 2000, 40) * 0.45),
                 (0.05, stone_grind(1.0, 90, 160) * 0.4))
    sy.save(pack, "ed5_fracture", rv(frac, 2.6, 0.45), max_distance=112)
    rain = sy.at(3.0, (0.0, sy.shimmer(2.8, 1600, 46) * 0.7), (0.2, clatter("tide", seed=42) * 0.25))
    sy.save(pack, "ed5_rain", rv(rain, 2.4, 0.5), volume=0.7, max_distance=72)


def build(pack):
    build_particles(pack)
    build_sounds(pack)
