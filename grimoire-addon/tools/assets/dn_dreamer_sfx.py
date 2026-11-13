"""DN06 particles and the original sound arc of The Dreamer Who Never Wakes.

Motif: an invented five-note music-box figure (scale degrees 1-5-3-6-2 over a slow pulse).  Phase I
plays it bare; the dream zones play it sweet and consonant; the nightmare zones play the same
contour detuned by a quarter-tone with clashing seconds; Phase V lets it resolve down to 1.
The Dreamer's own voice is breath, a closed-mouth hum and creaking ceramic -- never words.
"""
import numpy as np

from kit import synth as sy

from .a_fx_common import particles

ROOT = 233.08            # a soft B-flat-ish centre, never a known tune
MOTIF = [1.0, 1.5, 1.2599, 1.6818, 1.1225]   # 1 5 3 6 2 (equal-tempered ratios)


def musicbox(ratios, step=0.42, root=ROOT * 2, detune=0.0, dur_note=1.6, bright=0.75, clash=False):
    parts = []
    for i, r in enumerate(ratios):
        f = root * r * (1 + (detune if i % 2 else -detune))
        parts.append((i * step, sy.pluck(f, dur_note, bright) * 0.8))
        parts.append((i * step, sy.bell(f * 2, dur_note * 0.8, inharm=1.0) * 0.18))
        if clash:
            parts.append((i * step + 0.03, sy.pluck(f * 1.0595, dur_note * 0.8, bright) * 0.45))
    return sy.at(step * len(ratios) + dur_note, *parts)


def breath(dur=2.4, inhale=True, depth=1.0):
    n = sy.noise(dur)
    b = sy.bandpass(n, 900 if inhale else 650, 1.2) * 0.7 + sy.lowpass(n, 400) * 0.5
    x = np.linspace(0, 1, len(b))
    e = np.sin(np.pi * x) ** (1.5 if inhale else 0.8)
    sub = sy.osc(sy.sweep(32, 46 if inhale else 30, dur)) * 0.6 * depth * e
    return sy.norm(b * e + sub)


def hum(f=98.0, dur=2.8, vowel="oo"):
    v = sy.choir(f, dur, vowel, voices=3, vibrato=3.1, depth=0.01, attack=0.6, release=0.9, bright=0.6)
    return sy.norm(sy.lowpass(v, 1500))


def ceramic(dur=2.0, f0=70, f1=48):
    g = sy.creak(dur, f0, f1, jitter=0.35)
    return sy.norm(sy.lowpass(g, 2200) + sy.crack(dur, 4200, 10) * 0.25)


def build(pack):
    fx = particles(pack)
    # ---- particles
    fx.effect("dn_dreamer_mote", "dot", count=10, life=(1.6, 3.0), size=(0.09, 0.0), shape=("sphere", 3.0), speed=(0.05, 0.25),
              accel=(0, 0.25, 0), colors=["#fff3c8ff", "#ffd9b8cc", "#e8b4c800"])
    fx.effect("dn_dreamer_petal", "petal", count=8, life=(1.8, 3.0), size=(0.16, 0.1), shape=("sphere", 2.0), speed=(0.2, 0.7),
              accel=(0.3, -0.6, 0), drag=1.3, colors=["#ffd9e6ff", "#e8b4c8ee", "#ffd9b800"], blend="blend", spin=(360, 140))
    fx.effect("dn_dreamer_moon", "moon", count=5, life=(1.6, 2.6), size=(0.3, 0.12), shape=("sphere", 1.6), speed=(0.2, 0.6),
              accel=(0, 0.3, 0), drag=0.8, colors=["#fff3c8ff", "#ffd99aee", "#ffd99a00"], spin=(360, 40))
    fx.effect("dn_dreamer_star", "star", count=8, life=(0.8, 1.6), size=(0.14, 0.0), shape=("sphere", 2.2), speed=(0.1, 0.4),
              colors=["#ffffffff", "#fff3c8ff", "#bcd6f000"], spin=(360, 90))
    fx.effect("dn_dreamer_porcelain", "shard", count=10, life=(1.2, 2.2), size=(0.2, 0.12), shape=("sphere", 1.6),
              speed=(1.0, 3.0), accel=(0, -6, 0), drag=0.6, colors=["#fbf6ecff", "#e9cf8aff", "#cfc6b000"], blend="blend",
              spin=(360, 320))
    fx.effect("dn_dreamer_dust", "puff", count=12, life=(0.8, 1.6), size=(0.5, 1.4), shape=("disc", 1.8), speed=(0.8, 2.2),
              accel=(0, 0.5, 0), drag=1.6, colors=["#efe4d0cc", "#cfc6b000"], blend="blend", spin=(360, 50))
    fx.effect("dn_dreamer_feather", "feather", count=10, life=(1.6, 2.6), size=(0.2, 0.16), shape=("sphere", 1.5),
              speed=(1.0, 2.6), accel=(0, -0.9, 0), drag=1.8, colors=["#fffdf8ff", "#f6dbe6cc", "#f6dbe600"], blend="blend",
              spin=(360, 160))
    fx.effect("dn_dreamer_glint", "spark", count=10, life=(0.4, 0.9), size=(0.18, 0.0), shape=("sphere", 0.8), speed=(1.5, 4.0),
              drag=1.4, colors=["#ffffffff", "#ffe9b8ff", "#e9cf8a00"], spin=(360, 200))
    fx.effect("dn_dreamer_key", None, sprites=["key", "window", "door"], count=4, life=(1.2, 2.0), size=(0.22, 0.1),
              shape=("sphere", 1.4), speed=(0.2, 0.6), accel=(0, 0.6, 0), colors=["#fff3c8ff", "#ffd9b8ff", "#ffd9b800"])
    fx.effect("dn_dreamer_heal", "cross", count=6, life=(0.8, 1.4), size=(0.14, 0.04), shape=("disc", 1.0), direction=(0, 1, 0),
              speed=(0.6, 1.4), colors=["#ffd9b8ff", "#fff3c8ff", "#e8b4c800"])
    fx.effect("dn_dreamer_ring", "ringthin", count=1, life=(0.7, 0.8), size=(0.4, 4.2), facing="emitter_transform_xz",
              colors=["#fff3c8ff", "#ffd9b8cc", "#e8b4c800"])
    fx.effect("dn_dreamer_nring", "ringthin", count=1, life=(0.6, 0.7), size=(0.4, 4.6), facing="emitter_transform_xz",
              colors=["#b8a6d6ff", "#6e2f3acc", "#2a2d5200"])
    fx.effect("dn_dreamer_shock", "ring", count=1, life=(0.6, 0.7), size=(0.6, 9.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#bcd6f0cc", "#6a4a6e00"])
    fx.effect("dn_dreamer_eye", "eye", count=5, life=(0.8, 1.6), size=(0.24, 0.1), shape=("sphere", 1.6), speed=(0.1, 0.4),
              accel=(0, 0.2, 0), colors=["#f3e3b0ff", "#8e3446ee", "#2a2d5200"])
    fx.effect("dn_dreamer_smoke", "smoke", count=8, life=(1.0, 1.8), size=(0.5, 1.2), shape=("disc", 2.0), speed=(0.2, 0.8),
              accel=(0, 0.8, 0), drag=1.0, colors=["#4a3e6acc", "#2a2d5288", "#2a2d5200"], blend="blend", spin=(360, 30))
    fx.effect("dn_dreamer_door", "door", count=4, life=(0.8, 1.4), size=(0.3, 0.1), shape=("sphere", 1.5), speed=(0.6, 1.6),
              drag=1.0, colors=["#b8a6d6ff", "#6e2f3aee", "#2a2d5200"], spin=(360, 120))
    fx.effect("dn_dreamer_beam", "beam", count=10, life=(0.5, 0.9), size=(0.25, 0.05), size_y=(2.0, 4.0), shape=("disc", 3.5),
              direction=(0, -1, 0), speed=(4, 8), colors=["#ffffffff", "#bcd6f0ee", "#ffd9b800"], facing="lookat_y")
    fx.effect("dn_dreamer_trail", "dot", count=3, life=(0.5, 0.9), size=(0.18, 0.0), shape=("sphere", 0.3), speed=(0.0, 0.3),
              colors=["#fff3c8ff", "#e8b4c8cc", "#e8b4c800"])
    fx.effect("dn_dreamer_ntrail", "dot", count=3, life=(0.5, 0.9), size=(0.2, 0.0), shape=("sphere", 0.3), speed=(0.0, 0.3),
              colors=["#b8a6d6ff", "#6e2f3acc", "#2a2d5200"])

    # ---- sounds
    def save(name, sig, **kw):
        sy.save(pack, name, sig, max_distance=kw.pop("max_distance", 80), **kw)

    # Phase I: near-silent music box + the sleeper's breath
    mb = musicbox(MOTIF, step=0.55)
    save("dn_dreamer_musicbox", sy.reverb(sy.at(5.0, (0.0, mb * 0.7), (0.0, sy.pad(ROOT / 2, 4.6, cutoff=700) * 0.25),
                                               (1.2, breath(3.0) * 0.35)), 2.4, 0.5), volume=0.8)
    save("dn_dreamer_breath", sy.reverb(breath(2.6) * 0.8, 1.6, 0.4), volume=0.8,
         variants=[sy.reverb(breath(2.8, inhale=False) * 0.8, 1.6, 0.4)])
    bedsig = sy.at(3.0, (0.0, sy.whoosh(2.4, 200, 1600) * 0.5), (0.4, sy.wind(2.2, 500, 1100, gust=0.8) * 0.35),
                   (1.8, sy.creak(0.9, 140, 110) * 0.3), (2.1, sy.bell(ROOT * 4, 0.9) * 0.25))
    save("dn_dreamer_bed", sy.reverb(bedsig, 1.8, 0.4))
    save("dn_dreamer_mark", sy.reverb(sy.at(0.6, (0.0, sy.pluck(ROOT * 6, 0.45, 0.9) * 0.7), (0.08, sy.pluck(ROOT * 9, 0.4, 0.9) * 0.4)),
                                      0.9, 0.35), volume=0.6, max_distance=40)
    book = sy.at(2.4, (0.0, sy.scribble(1.0, 5) * 0.35), (0.1, sy.whoosh(0.9, 900, 3500) * 0.3),
                 (0.5, sy.shimmer(1.6, 2400, 14) * 0.35), (0.3, sy.pad(ROOT, 1.9, cutoff=1400) * 0.25))
    save("dn_dreamer_book", sy.reverb(book, 1.6, 0.4), max_distance=32)
    # Phase II: manifesting porcelain, the rising (groan + sub inhale), the door, the hum
    man = sy.at(4.5, (0.0, sy.crack(4.0, 5200, 40) * 0.35), (0.2, hum(87.3, 4.0, "oo") * 0.6),
                (0.5, sy.shimmer(3.5, 1600, 20) * 0.25), (3.6, sy.bell(ROOT * 2, 0.9) * 0.3))
    save("dn_dreamer_manifest", sy.reverb(man, 2.2, 0.45))
    groan = sy.at(3.2, (0.0, ceramic(3.0, 62, 44)), (0.0, sy.rumble(3.0, 36) * 0.7), (0.2, breath(2.8, True, 1.6) * 0.6))
    save("dn_dreamer_groan", sy.reverb(sy.lowpass(groan, 2400), 2.4, 0.4), max_distance=96,
         variants=[sy.reverb(sy.lowpass(sy.pitch(groan, 0.86), 2400), 2.4, 0.4)])
    save("dn_dreamer_inhale", sy.reverb(sy.at(3.0, (0.0, breath(3.0, True, 2.5)), (0.0, sy.osc(sy.sweep(28, 52, 3.0)) * 0.5 * sy.env(3.0, 1.2, 0.2, 0.9, 0.8))),
                                        1.8, 0.35), max_distance=96)
    door = sy.at(1.6, (0.0, sy.creak(0.9, 260, 420, 0.3) * 0.7), (0.8, sy.bell(ROOT * 4 * 1.5, 0.8) * 0.4),
                 (0.9, sy.shimmer(0.7, 2600, 9) * 0.35))
    save("dn_dreamer_door", sy.reverb(door, 1.5, 0.4))
    save("dn_dreamer_hum", sy.reverb(hum(98.0, 3.0, "oo"), 2.2, 0.45), max_distance=96,
         variants=[sy.reverb(hum(110.0, 3.0, "oh"), 2.2, 0.45)])
    sweep = sy.at(2.4, (0.0, sy.whoosh(1.4, 120, 900) * 0.8), (0.3, sy.rumble(1.8, 40) * 0.6), (0.2, ceramic(1.6, 90, 60) * 0.4),
                  (1.0, sy.thump(1.0, 70, 28, 0.4) * 0.7))
    save("dn_dreamer_sweep", sy.reverb(sweep, 1.8, 0.35), max_distance=96)
    pil = sy.at(1.4, (0.0, sy.whoosh(0.5, 300, 1500) * 0.4), (0.4, sy.lowpass(sy.thump(0.8, 80, 30, 0.6), 600)),
                (0.45, sy.wind(0.8, 1800, 3000, gust=0.0) * 0.25))
    save("dn_dreamer_pillow", sy.reverb(pil, 1.2, 0.3))
    knocks = [(0.12 * k, sy.lowpass(sy.thump(0.25, 260 - k * 14, 90, 0.8), 2200) * (0.6 + 0.04 * k)) for k in range(10)]
    save("dn_dreamer_stairs", sy.reverb(sy.at(1.8, (0.0, sy.creak(0.5, 300, 200) * 0.4), *knocks), 1.2, 0.3))
    # Phase III: the hands rise; two interleaved motifs (sweet dream / detuned nightmare)
    rais = sy.at(2.6, (0.0, breath(2.4, True, 2.0) * 0.6), (0.4, sy.choir(ROOT / 2, 2.0, "ah", voices=4) * 0.4),
                 (0.4, sy.choir(ROOT * 0.75, 2.0, "oo", voices=3) * 0.3), (1.2, ceramic(1.2, 110, 80) * 0.3))
    save("dn_dreamer_raise", sy.reverb(rais, 2.4, 0.45), max_distance=96)
    sweet = musicbox([MOTIF[0], MOTIF[2], MOTIF[1]], step=0.32, root=ROOT * 2, bright=0.9)
    sweet2 = musicbox([MOTIF[3], MOTIF[1], MOTIF[2]], step=0.32, root=ROOT * 2, bright=0.9)
    save("dn_dreamer_sweet", sy.reverb(sy.at(2.0, (0.0, sweet * 0.7), (0.0, sy.shimmer(1.2, 2800, 8) * 0.2)), 1.8, 0.45),
         variants=[sy.reverb(sy.at(2.0, (0.0, sweet2 * 0.7)), 1.8, 0.45)], volume=0.7, max_distance=48)
    sour = musicbox([MOTIF[0], MOTIF[2], MOTIF[1]], step=0.32, root=ROOT * 1.5, detune=0.028, clash=True, bright=0.5)
    sour2 = musicbox([MOTIF[4], MOTIF[1], MOTIF[3]], step=0.36, root=ROOT * 1.5, detune=0.03, clash=True, bright=0.5)
    save("dn_dreamer_sour", sy.reverb(sy.at(2.0, (0.0, sour * 0.6), (0.3, sy.creak(0.8, 120, 70) * 0.35)), 1.6, 0.4),
         variants=[sy.reverb(sy.at(2.0, (0.0, sour2 * 0.6), (0.2, sy.creak(0.7, 160, 90) * 0.3)), 1.6, 0.4)],
         volume=0.7, max_distance=48)
    bloom = sy.at(1.6, (0.0, sy.shimmer(1.2, 1800, 14) * 0.5), (0.0, sy.pad(ROOT * 2, 1.4, cutoff=2600) * 0.35),
                  (0.2, sy.whoosh(1.0, 600, 2600) * 0.3))
    save("dn_dreamer_bloom", sy.reverb(bloom, 1.8, 0.45), max_distance=48)
    emerge = sy.at(1.8, (0.0, sy.rumble(1.4, 48) * 0.6), (0.1, sy.creak(1.2, 90, 150, 0.4) * 0.6),
                   (0.6, sy.crack(0.8, 3000, 8) * 0.3), (0.3, sy.roar(1.2, 70, 50, growl=18, breath=0.6) * 0.3))
    save("dn_dreamer_emerge", sy.reverb(emerge, 1.6, 0.4), max_distance=48)
    bite = sy.at(0.9, (0.0, sy.creak(0.25, 220, 120) * 0.6), (0.18, sy.thump(0.5, 140, 50, 0.7)), (0.2, sy.crack(0.4, 2600, 8) * 0.4))
    save("dn_dreamer_bite", sy.reverb(bite, 0.9, 0.3), max_distance=40,
         variants=[sy.reverb(sy.pitch(bite, 1.15), 0.9, 0.3)])
    save("dn_dreamer_heal", sy.reverb(sy.at(0.8, (0.0, sy.bell(ROOT * 6, 0.6) * 0.5), (0.05, sy.pluck(ROOT * 4.5, 0.6, 0.9) * 0.4)),
                                      0.8, 0.4), volume=0.5, max_distance=24)
    # Phase IV: the Great Unreality, escalating layered strikes
    unr = sy.at(4.0, (0.0, sy.rumble(3.8, 34) * 0.7), (0.0, ceramic(3.5, 55, 90) * 0.5),
                (0.3, sy.creak(2.5, 120, 300, 0.5) * 0.4), (0.0, sy.shimmer(3.0, 1400, 30)[::-1] * 0.3),
                (2.6, sy.choir(ROOT / 2, 1.4, "ah", voices=4) * 0.5))
    save("dn_dreamer_unreality", sy.reverb(unr, 2.6, 0.45), max_distance=112)
    wheel = sy.at(3.0, (0.0, sy.rumble(3.0, 50, wobble=5.0) * 0.6),
                  *[(0.25 * k, sy.lowpass(sy.thump(0.3, 160, 60, 0.6), 1400) * 0.5) for k in range(12)],
                  *[(0.25 * k + 0.12, sy.creak(0.18, 300, 200) * 0.2) for k in range(12)])
    save("dn_dreamer_wheel", sy.reverb(wheel, 1.4, 0.35), max_distance=80)
    glass = sy.at(1.2, (0.0, sy.whoosh(0.5, 800, 5000) * 0.4), (0.45, sy.crack(0.7, 7000, 22) * 0.8),
                  (0.45, sy.shimmer(0.7, 3200, 12) * 0.4))
    save("dn_dreamer_glass", sy.reverb(glass, 1.0, 0.3), variants=[sy.reverb(sy.pitch(glass, 1.12), 1.0, 0.3)])
    drill = sy.at(3.0, (0.0, sy.wind(3.0, 200, 1400, q=3.0, gust=0.2) * 0.6), (0.0, ceramic(2.8, 120, 60) * 0.5),
                  (1.0, sy.rumble(2.0, 42) * 0.7), (1.1, sy.thump(1.0, 90, 30, 0.6) * 0.8))
    save("dn_dreamer_drill", sy.reverb(drill, 1.8, 0.35), max_distance=96)
    pend = sy.at(2.6, (0.0, sy.whoosh(2.4, 100, 900) * 0.8), (0.1, sy.creak(2.2, 70, 50, 0.3) * 0.5),
                 (1.1, sy.thump(1.2, 60, 24, 0.5) * 0.9), (1.1, sy.crack(0.6, 3000, 10) * 0.3))
    save("dn_dreamer_pendulum", sy.reverb(pend, 2.0, 0.4), max_distance=112)
    room = sy.at(1.6, (0.0, sy.whoosh(0.4, 600, 2600) * 0.4), (0.4, sy.thump(0.7, 120, 40, 0.5) * 0.8),
                 (0.42, sy.creak(0.4, 400, 180) * 0.4), (0.9, sy.lowpass(sy.thump(0.6, 90, 30, 0.8), 900) * 0.8))
    save("dn_dreamer_room", sy.reverb(room, 1.2, 0.35), variants=[sy.reverb(sy.pitch(room, 0.9), 1.2, 0.35)])
    beam = sy.at(4.0, (0.0, sy.pad(ROOT, 3.8, cutoff=2400) * 0.45), (0.0, sy.pad(ROOT * 1.5, 3.8, cutoff=2000) * 0.35),
                 (0.0, sy.water(3.6, 60, 400) * 0.35), (0.2, sy.shimmer(3.4, 1800, 40) * 0.4),
                 (0.0, sy.choir(ROOT * 2, 3.6, "oo", voices=4) * 0.35))
    save("dn_dreamer_beam", sy.reverb(beam, 2.8, 0.5), max_distance=112)
    final = sy.at(2.2, (0.0, sy.thump(1.6, 110, 26, 0.9)), (0.0, sy.crack(0.6, 4400, 18) * 0.5),
                  (0.02, sy.bell(ROOT / 2, 2.0, inharm=1.2) * 0.6), (0.05, sy.rumble(1.8, 32) * 0.6))
    save("dn_dreamer_final", sy.reverb(final, 2.6, 0.45), max_distance=128)
    # Phase V: porcelain panels drifting apart, the motif resolving, one soft click
    brk = sy.at(3.4, (0.0, sy.crack(3.0, 6000, 50) * 0.5), (0.2, sy.shimmer(3.0, 2400, 36) * 0.45),
                (0.0, breath(3.2, False, 1.0) * 0.4))
    save("dn_dreamer_break", sy.reverb(brk, 2.4, 0.5), max_distance=96)
    res = musicbox([MOTIF[3], MOTIF[1], MOTIF[2], MOTIF[4], MOTIF[0], 0.5], step=0.6, bright=0.6)
    morning = sy.at(5.5, (0.0, res * 0.7), (0.0, sy.pad(ROOT, 5.2, cutoff=1100) * 0.3), (3.0, sy.pad(ROOT / 2, 2.4, cutoff=800) * 0.3))
    save("dn_dreamer_morning", sy.reverb(morning, 3.0, 0.5), volume=0.9, max_distance=64)
    click = sy.at(0.6, (0.0, sy.lowpass(sy.crack(0.08, 3200, 2), 4000) * 0.7), (0.0, sy.thump(0.2, 220, 120, 0.4) * 0.4))
    save("dn_dreamer_click", sy.reverb(click, 0.6, 0.25), volume=0.6, max_distance=24)
