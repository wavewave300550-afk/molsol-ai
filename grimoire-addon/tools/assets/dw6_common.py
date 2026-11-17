"""DW06 The Word Before Creation -- shared palette, letter helpers, particles and sound design.

Every DW06 construct lives in dw6_codex (great book, giant page), dw6_edifice (letters, the six
written structures, written walls, refuge dome, domain boundary) and dw6_laws (seven law tablets,
descending lines of sacred text, the final white-gold formation).

Particles are tuned to read from the caster's eye at 10-45 m: larger sprites, long soft fades
(every effect fades in and out, nothing pops), white -> white-gold -> antique gold colour layering.
"""
import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import M

from .a_fx_common import particles

IVORY, GOLD, WGOLD, SILVER, BLUE = "#f5f0e1", "#c9a24a", "#fff3c4", "#d8dde3", "#2b3f8f"
FW = glyphs.FIRST_WORD

# letters (indices into FIRST_WORD) written for each structure kind -- mirrored in the spell
LETTER = {0: 0, 1: 6, 2: 5, 3: 9, 4: 11, 5: 13}


def spin(rate, phase=0.0):
    return M(f"q.life_time*{rate}+{phase}", lambda t: t * rate + phase)


def strokes(glyph, n=5):
    """Split a glyph's ink rectangles into n ordered strokes (top to bottom)."""
    rs = glyphs.rects(glyph)
    out = [[] for _ in range(n)]
    for i, r in enumerate(rs):
        out[min(n - 1, i * n // len(rs))].append(r)
    return [s for s in out if s] + [[] for s in out if not s]


def extrude_strokes(m, parent, glyph, center, pixel, depth, mat, prefix="s", n=5, edge=None):
    """3D letter whose ink rectangles are split over n stroke bones (drawn one after another).

    center = glyph centre (x, y, z_front).  Returns the bone names.  The letter reads from the
    model's front (-Z), like glyphs.extrude.
    """
    gh, gw = len(glyph), len(glyph[0])
    ox, oy, oz = center[0] + gw * pixel / 2, center[1] + gh * pixel / 2, center[2]
    names = []
    for k, st in enumerate(strokes(glyph, n)):
        if st:
            x, y, w, h = st[0]
            pv = (ox - x * pixel, oy - y * pixel, oz)
        else:
            pv = (center[0], center[1], oz)
        b = m.bone(f"{prefix}{k + 1}", parent, pivot=pv)
        for (x, y, w, h) in st:
            b.cube((ox - (x + w) * pixel, oy - (y + h) * pixel, oz), (w * pixel, h * pixel, depth), mat)
            if edge is not None:   # luminous face inlay on the front of every stroke
                b.cube((ox - (x + w) * pixel + pixel * 0.25, oy - (y + h) * pixel + pixel * 0.25, oz - 0.12),
                       (w * pixel - pixel * 0.5, h * pixel - pixel * 0.5, 0), edge)
        names.append(b.name)
    return names


def extrude(bone, glyph, center, pixel, depth, mat, **kw):
    gh, gw = len(glyph), len(glyph[0])
    return glyphs.extrude(bone, glyph, (center[0] + gw * pixel / 2, center[1] + gh * pixel / 2, center[2]),
                          pixel, depth, mat, **kw)


# ---------------------------------------------------------------- shared materials
def marble(variant_key=""):
    return tex.marble("#f6f1e4", "#cbbf9f", vein2="#d9b45a", scale=6)


def gold_metal(glow=0.25):
    return tex.metal("#d9b45a", "#fff3c4", "#8a6a26", bands=2.5, glow=glow)


def text_band(color=WGOLD, bg=None, glow=1.0, seed=0, fill=0.85, key=None):
    return tex.glyph_rows(FW, color, glow=glow, color2="#ffffff", bg=bg, bg_glow=0.25 if bg else 0.0, fill=fill,
                          seed=seed, key=key)


def engraved(base_hex="#f2ecdc", ink=GOLD, seed=0, glow=0.75):
    """Marble face with gilded engraved lettering."""
    return tex.glyph_rows(FW, ink, glow=glow, color2="#fff3c4", bg=base_hex, bg_glow=0.05, fill=0.7, seed=seed,
                          key=f"dw6eng{base_hex}{ink}{seed}{glow}")


# ---------------------------------------------------------------- particles
def build_particles(pack):
    fx = particles(pack)
    gl = [f"glyph{i}" for i in range(1, 9)]
    # ---- continuous ambient layers (cheap, long-lived, fade in and out)
    fx.effect("dw6_motes", "dot", count=2, life=(2.2, 3.2), size=(0.1, 0.035), shape=("sphere", 2.2), speed=(0.03, 0.16),
              accel=(0, 0.07, 0), colors=["#fffdf400", "#fffdf4dd", "#fff3c4aa", "#fffdf400"])
    fx.effect("dw6_script", None, sprites=gl, count=1, life=(2.0, 3.0), size=(0.36, 0.12), shape=("sphere", 0.5),
              speed=(0.05, 0.25), accel=(0, 0.34, 0), drag=0.5, colors=["#fff3c400", "#fff3c4ff", "#e9c15add", "#c9a24a00"])
    fx.effect("dw6_glint", "star", count=1, life=(0.45, 0.75), size=(0.5, 0.0), spin=(360, 160),
              colors=["#ffffff00", "#ffffffff", "#fff3c4cc", "#e9c15a00"])
    fx.effect("dw6_ember", "ember", count=3, life=(1.4, 2.4), size=(0.15, 0.03), shape=("sphere", 1.8), speed=(0.1, 0.5),
              accel=(0, -0.9, 0), drag=0.6, colors=["#ffffff00", "#fff3c4ff", "#e9c15acc", "#c9a24a00"])
    fx.effect("dw6_feather", "feather", count=2, life=(2.4, 3.4), size=(0.34, 0.24), shape=("sphere", 1.4), speed=(0.1, 0.4),
              accel=(0, -0.32, 0), drag=1.0, spin=(360, 50), blend="blend",
              colors=["#fffdf600", "#fffdf6ee", "#f3e3a8cc", "#e9c15a00"])
    # ---- letters and ink
    fx.effect("dw6_ink", None, sprites=gl, count=8, life=(0.6, 1.1), size=(0.34, 0.05), shape=("sphere", 0.8),
              speed=(1.0, 3.0), accel=(0, -0.8, 0), drag=1.2, colors=["#ffffffff", "#ffe08aff", "#c9a24a00"])
    fx.effect("dw6_letters", None, sprites=gl, count=5, life=(1.4, 2.2), size=(0.42, 0.12), shape=("sphere", 1.2),
              speed=(0.2, 0.7), accel=(0, 1.0, 0), drag=0.8, colors=["#fff3c400", "#fff3c4ff", "#e9c15acc", "#c9a24a00"])
    fx.effect("dw6_stream", None, sprites=gl, count=2, life=(0.6, 1.0), size=(0.32, 0.08), shape=("sphere", 0.35),
              speed=(0.1, 0.4), colors=["#ffffffff", "#fff3c4ff", "#e9c15a00"])
    fx.effect("dw6_trail", "glow", count=1, life=(0.45, 0.6), size=(0.8, 0.05),
              colors=["#ffffffff", "#fff3c4cc", "#e9c15a00"])
    fx.effect("dw6_quill", "spark", count=4, life=(0.25, 0.45), size=(0.75, 0.0), shape=("sphere", 0.4), speed=(1.0, 3.0),
              drag=2.0, spin=(360, 400), colors=["#ffffffff", "#fff3c4ff", "#e9c15a00"])
    fx.effect("dw6_fountain", None, sprites=gl, rate=26, emit_time=1.0, life=(1.0, 1.6), size=(0.38, 0.1),
              shape=("disc", 1.0), direction=(0, 1, 0), speed=(2.0, 3.6), drag=0.6,
              colors=["#ffffffff", "#fff3c4ff", "#e9c15acc", "#c9a24a00"])
    fx.effect("dw6_converge", None, sprites=gl, count=8, life=(0.6, 0.7), size=(0.38, 0.1), shape=("sphere", 4.0, "surface"),
              direction="inwards", speed=(5.0, 6.5), colors=["#fff3c400", "#fff3c4ff", "#ffffffff"])
    # ---- light and impact
    fx.effect("dw6_seam", "spark", count=5, life=(0.3, 0.6), size=(0.34, 0.0), shape=("sphere", 0.5), speed=(0.5, 2.0),
              drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#c9a24a00"], spin=(360, 300))
    fx.effect("dw6_dust", "puff", count=12, life=(0.8, 1.6), size=(0.5, 1.3), shape=("disc", 2.2), speed=(1.0, 2.6),
              accel=(0, 0.3, 0), drag=1.6, colors=["#f6f1e4dd", "#e3d8bf88", "#d8cdb000"], blend="blend", spin=(360, 40))
    fx.effect("dw6_quake", "ringthin", count=1, life=(0.6, 0.7), size=(0.6, 9.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#ffe9a3dd", "#c9a24a00"])
    fx.effect("dw6_wave", "ringthin", count=1, life=(1.0, 1.1), size=(1.0, 18.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#fff3c4dd", "#e9c15a66", "#c9a24a00"])
    fx.effect("dw6_wave_s", "ringthin", count=1, life=(1.8, 2.0), size=(1.0, 20.0), facing="emitter_transform_xz",
              colors=["#ffffffff", "#dfe6ffdd", "#8a9ad866", "#2b3f8f00"])
    fx.effect("dw6_rays", "beam", count=12, life=(0.5, 0.9), size=(0.2, 0.02), size_y=(2.5, 5.0), shape=("disc", 2.5),
              direction=(0, 1, 0), speed=(8, 14), colors=["#ffffffff", "#fff3c4ff", "#ffd76a00"], facing="lookat_y")
    fx.effect("dw6_pillar", "beam", count=1, life=(0.8, 1.0), size=(1.0, 0.15), size_y=(11.0, 13.0), facing="lookat_y",
              colors=["#ffffffff", "#fff3c4ee", "#e9c15a00"])
    fx.effect("dw6_bell", "ring", count=1, life=(2.2, 2.4), size=(0.5, 7.0), colors=["#fff3c466", "#d8dde322", "#d8dde300"])
    fx.effect("dw6_halo", "ring", count=1, life=(0.6, 0.8), size=(0.6, 5.0), colors=["#ffffffff", "#fff3c4cc", "#e9c15a00"])
    fx.effect("dw6_flare", "glow", count=1, life=(0.4, 0.5), size=(2.0, 5.5), colors=["#ffffffff", "#fff3c4aa", "#fff3c400"])
    fx.effect("dw6_flash", "glow", count=1, life=(0.6, 0.7), size=(4.0, 14.0), colors=["#ffffffff", "#fff3c4bb", "#fff3c400"])
    fx.effect("dw6_blue", "diamond", count=6, life=(0.8, 1.4), size=(0.24, 0.0), shape=("sphere", 1.2), speed=(0.4, 1.2),
              drag=1.0, colors=["#dfe6ffff", "#2b3f8fcc", "#2b3f8f00"], spin=(360, 120))
    fx.effect("dw6_silver", "star", count=3, life=(1.4, 2.2), size=(0.42, 0.1), shape=("sphere", 0.9), speed=(0.0, 0.15),
              colors=["#ffffff00", "#ffffffff", "#d8dde3cc", "#2b3f8f00"], spin=(360, 20))


# ---------------------------------------------------------------- sounds (original synthesis)
def _chord(root, dur, vowel="ah", ratios=(1.0, 1.25, 1.5), bright=1.0, voices=4, attack=0.25, release=0.6):
    return sy.mixdown([sy.choir(root * r, dur, vowel, voices=voices, bright=bright, attack=attack, release=release)
                       * (1.0 if i == 0 else 0.7) for i, r in enumerate(ratios)])


def _flutter(dur, n=10, f=2600):
    """Paper riffle: short airy flaps."""
    out = np.zeros(int(sy.SR * dur))
    for k in range(n):
        at = dur * (k / n) ** 1.3 * 0.9
        L = 0.05 + 0.03 * (k % 3)
        seg = sy.bandpass(sy.noise(L), f * (0.7 + 0.1 * (k % 4)), 1.2) * np.hanning(int(sy.SR * L))
        i = int(sy.SR * at)
        out[i:i + len(seg)] += seg[:len(out) - i]
    return sy.norm(out)


def build_sounds(pack):
    rv = sy.reverb
    # Phase I -- near silence: a low breath, a far bell, a sub-audible floor
    breath = sy.lowpass(sy.wind(6.0, 140, 260, 1.4, gust=0.7), 420)
    silence = sy.at(6.0, (0.0, breath * 0.28), (0.0, sy.pad(55.0, 6.0, cutoff=180, attack=1.5, release=2.0) * 0.12),
                    (1.6, sy.lowpass(sy.bell(196.0, 3.5, bright=0.4), 1800) * 0.32))
    sy.save(pack, "dw6_silence", rv(silence, 3.5, 0.55, tone=2400), volume=0.65, max_distance=96)
    book = sy.at(2.6, (0.0, sy.whoosh(1.2, 200, 1400) * 0.4), (0.9, _flutter(1.4, 12) * 0.5),
                 (0.4, sy.choir(130.8, 2.0, "oo", voices=3, attack=0.6) * 0.35), (1.9, sy.thump(0.5, 90, 50, 0.1) * 0.3))
    sy.save(pack, "dw6_book", rv(book, 2.0, 0.4), max_distance=64)
    unbind = sy.at(2.4, (0.0, sy.shimmer(1.6, 1400, 14)[::-1] * 0.4), (0.2, _flutter(2.0, 16, 3200) * 0.45),
                   (0.0, sy.whoosh(2.2, 600, 2400) * 0.25))
    sy.save(pack, "dw6_unbind", rv(unbind, 2.0, 0.45), max_distance=64)
    page = sy.at(3.0, (0.0, sy.pad(110.0, 3.0, cutoff=900, attack=1.2) * 0.35), (0.3, sy.choir(440.0, 2.5, "oo", voices=3, attack=1.0) * 0.25),
                 (0.8, sy.shimmer(2.0, 2400, 16) * 0.2), (0.0, sy.whoosh(2.6, 300, 1800, 1.0) * 0.3))
    sy.save(pack, "dw6_page", rv(page, 3.0, 0.5), max_distance=128)
    # the codex glides (page riffle riding an airy swell)
    glide = sy.at(1.8, (0.0, sy.whoosh(1.6, 250, 1600, 1.2) * 0.5), (0.15, _flutter(1.3, 9, 2300) * 0.35),
                  (0.2, sy.choir(196.0, 1.4, "oo", voices=3, attack=0.5, release=0.7) * 0.22))
    sy.save(pack, "dw6_glide", rv(glide, 1.8, 0.4), max_distance=96)
    # a soft choir bed that keeps the long middle of the spell from ever going silent (played every ~4.5 s)
    def bed(root, vowel):
        return rv(sy.at(5.0, (0.0, _chord(root, 5.0, vowel, (1.0, 1.5, 2.0), voices=3, attack=1.6, release=1.8) * 0.5),
                        (0.0, sy.pad(root / 2, 5.0, cutoff=500, attack=1.8, release=1.8) * 0.25),
                        (1.2, sy.shimmer(3.0, 2600, 10) * 0.08)), 3.0, 0.5, tone=3000)
    sy.save(pack, "dw6_bed", bed(130.8, "oo"), variants=[bed(146.8, "ah"), bed(116.5, "oo")], volume=0.7, max_distance=96)
    # Phase II -- the first utterance: strokes, falls, landings
    def stroke(p1, p2):
        return rv(sy.at(1.2, (0.0, sy.scribble(1.0, 5) * 0.5), (0.05, sy.pluck(p1, 0.9, 0.7) * 0.35),
                        (0.6, sy.pluck(p2, 0.6, 0.7) * 0.3), (0.0, sy.choir(p1 / 4, 1.1, "ah", voices=3) * 0.3)), 1.5, 0.4)
    sy.save(pack, "dw6_stroke", stroke(784.0, 1046.5), variants=[stroke(659.3, 987.8), stroke(880.0, 1174.7)], max_distance=128)
    fall = sy.at(0.9, (0.0, sy.whoosh(0.85, 2600, 260, 1.4) * 0.6), (0.0, sy.shimmer(0.6, 2000, 6) * 0.2))
    sy.save(pack, "dw6_fall", rv(fall, 1.0, 0.3), max_distance=96)
    def land(r):
        return rv(sy.at(1.6, (0.0, sy.thump(1.0, 120 * r, 34, 0.6)), (0.0, sy.crack(0.5, 4200, 18) * 0.4),
                        (0.03, _chord(146.8 * r, 1.4, "ah", (1.0, 1.5, 2.0), attack=0.03) * 0.55),
                        (0.05, sy.bell(587.3 * r, 1.3) * 0.25)), 2.0, 0.42)
    sy.save(pack, "dw6_land", land(1.0), variants=[land(1.12), land(0.89)], max_distance=96)
    swing = sy.at(1.6, (0.0, sy.whoosh(1.4, 180, 900, 1.2) * 0.7), (0.1, sy.creak(1.2, 70, 110, 0.15) * 0.3),
                  (1.1, sy.thump(0.5, 90, 40, 0.3) * 0.6))
    sy.save(pack, "dw6_swing", rv(swing, 1.5, 0.35), max_distance=96)
    # Phase III -- the page divides, seven laws
    split = sy.at(2.4, (0.0, sy.crack(1.0, 5200, 30) * 0.45), (0.1, sy.shimmer(1.6, 2000, 20) * 0.35),
                  (0.25, _chord(220.0, 2.0, "eh", (1.0, 1.335, 2.0)) * 0.5))
    sy.save(pack, "dw6_split", rv(split, 2.5, 0.45), max_distance=128)
    laws = [
        sy.at(2.0, (0.0, sy.rumble(1.6, 60, 2.0) * 0.6), (0.2, _chord(110.0, 1.6, "oh", (1.0, 1.5)) * 0.6),
              (0.9, sy.thump(0.6, 80, 36, 0.2) * 0.5)),                                                   # I containment
        sy.at(2.0, (0.0, sy.creak(1.4, 60, 90, 0.1) * 0.35), (0.0, sy.whoosh(1.5, 150, 600) * 0.4),
              (0.3, _chord(164.8, 1.5, "ah", (1.0, 1.26)) * 0.45)),                                      # II station
        sy.at(2.0, (0.0, sy.whoosh(0.7, 400, 4200, 2.0) * 0.6), (0.25, sy.whoosh(0.7, 500, 4600, 2.0) * 0.5),
              (0.5, sy.whoosh(0.7, 600, 5000, 2.0) * 0.45), (0.0, sy.scribble(1.2, 8) * 0.3),
              (0.1, sy.choir(293.7, 1.4, "ee", voices=3) * 0.35)),                                       # III direction
        sy.at(2.2, (0.0, sy.bell(1318.5, 2.0, bright=0.6) * 0.4), (0.0, sy.osc(1975.5, 2.0) * sy.env(2.0, 0.6, 0.1, 0.8, 0.9) * 0.12),
              (0.0, sy.pad(98.0, 2.2, cutoff=500, attack=0.8) * 0.3)),                                  # IV stillness
        sy.at(2.4, (0.0, _chord(196.0, 2.2, "oo", (1.0, 1.25, 1.5, 2.0), attack=0.5) * 0.7),
              (0.4, sy.shimmer(1.6, 1600, 12) * 0.25)),                                                  # V refuge
        sy.at(2.0, *[(0.18 * k, sy.bell(f, 0.9) * 0.3) for k, f in enumerate((392.0, 466.2, 523.3, 622.3, 698.5, 830.6))],
              (0.0, sy.choir(196.0, 1.6, "ah", voices=3) * 0.3)),                                         # VI sequence
        sy.at(2.6, (0.0, sy.thump(1.4, 70, 28, 0.4) * 0.8), (0.05, _chord(73.4, 2.2, "oh", (1.0, 1.5, 2.0, 3.0), bright=1.4) * 0.8),
              (0.4, sy.bell(220.0, 2.0) * 0.4)),                                                         # VII judgment
    ]
    for i, s in enumerate(laws):
        sy.save(pack, f"dw6_law{i + 1}", rv(s, 2.4, 0.45), max_distance=128)
    # Phase IV -- let it be written
    rise = sy.at(2.6, (0.0, sy.choir(sy.sweep(146.8, 293.7, 2.4, 0.7).mean(), 2.4, "ah", voices=4, attack=0.8) * 0.4),
                 (0.0, sy.osc(sy.sweep(220, 660, 2.4, 0.6)) * sy.env(2.4, 0.8, 0.1, 0.8, 0.6) * 0.12),
                 (0.0, sy.whoosh(2.4, 200, 3000, 1.0) * 0.4))
    sy.save(pack, "dw6_rise", rv(rise, 2.5, 0.45), max_distance=128)
    form = sy.at(1.6, (0.0, sy.scribble(1.2, 9) * 0.4), (0.1, sy.shimmer(1.3, 2600, 18) * 0.35),
                 (0.0, sy.choir(392.0, 1.4, "ee", voices=3, attack=0.4) * 0.25))
    sy.save(pack, "dw6_form", rv(form, 1.8, 0.4), max_distance=96)
    def strike(r):
        return rv(sy.at(1.4, (0.0, sy.whoosh(0.3, 3000, 500) * 0.5), (0.22, sy.thump(1.0, 140 * r, 32, 0.5)),
                        (0.22, sy.crack(0.4, 5000, 12) * 0.35), (0.24, sy.bell(440.0 * r, 1.1) * 0.35),
                        (0.24, sy.choir(220.0 * r, 0.9, "ah", voices=3, attack=0.02, release=0.6) * 0.4)), 1.8, 0.4)
    sy.save(pack, "dw6_strike", strike(1.0), variants=[strike(1.19), strike(0.84), strike(1.33)], max_distance=96)
    # the finale build-up: every written thing is drawn into the last line (a 3.4 s crescendo into the strike)
    n = int(sy.SR * 3.4)
    swell = np.linspace(0.0, 1.0, n) ** 2.2
    riser = sy.highpass(sy.noise(3.4), 900) * swell * 0.22
    tone = sy.osc(sy.sweep(110.0, 440.0, 3.4, 1.6)) * swell * 0.18
    voices = sy.mixdown([sy.choir(f, 3.4, "ah", voices=4, attack=2.6, release=0.1, bright=1.2) for f in (98.0, 146.8, 196.0, 293.7)])
    gather = sy.at(3.4, (0.0, riser), (0.0, tone), (0.0, voices * swell * 0.7), (1.6, sy.shimmer(1.8, 2600, 26) * 0.25),
                   (0.4, sy.scribble(2.8, 14) * 0.18))
    sy.save(pack, "dw6_gather", rv(gather, 2.0, 0.35), max_distance=128)
    finale = sy.at(4.5, (0.0, sy.whoosh(0.9, 4000, 300, 1.2) * 0.5), (0.8, sy.thump(2.0, 110, 22, 0.8)),
                   (0.8, sy.crack(1.0, 6000, 40) * 0.5),
                   (0.82, _chord(98.0, 3.4, "ah", (1.0, 1.5, 2.0, 2.5, 3.0), bright=1.5, attack=0.02, release=1.6)),
                   (0.85, sy.bell(196.0, 3.0) * 0.5), (0.9, sy.bell(783.99, 2.4) * 0.3), (1.0, sy.shimmer(3.0, 2400, 30) * 0.3))
    sy.save(pack, "dw6_finale", rv(finale, 3.5, 0.5), max_distance=128)
    # Phase V -- the final amen
    unwrite = sy.at(2.2, (0.0, sy.shimmer(2.0, 1800, 24)[::-1] * 0.45), (0.0, sy.whoosh(2.0, 2400, 400, 1.2) * 0.35),
                    (0.3, sy.scribble(1.4, 7)[::-1] * 0.25))
    sy.save(pack, "dw6_unwrite", rv(unwrite, 2.0, 0.45), max_distance=128)
    def fold(r):
        return rv(sy.at(0.8, (0.0, sy.whoosh(0.45, 600 * r, 2600 * r, 1.4) * 0.5), (0.38, sy.thump(0.3, 160 * r, 80, 0.4) * 0.35),
                        (0.38, _flutter(0.3, 3, 1800 * r) * 0.3)), 0.9, 0.3)
    sy.save(pack, "dw6_fold", fold(1.0), variants=[fold(1.1), fold(1.22), fold(1.36)], max_distance=128)
    close = sy.at(1.6, (0.0, sy.whoosh(0.6, 300, 1200) * 0.3), (0.5, sy.thump(0.7, 100, 45, 0.3) * 0.7),
                  (0.52, sy.bell(261.6, 1.0) * 0.3))
    sy.save(pack, "dw6_close", rv(close, 1.6, 0.4), max_distance=96)
    amen = sy.at(5.5, (0.0, _chord(174.6, 2.4, "ah", (1.0, 1.26, 1.5), attack=0.5, release=1.0) * 0.6),
                 (2.1, _chord(130.8, 3.2, "oo", (1.0, 1.25, 1.5, 2.0), attack=0.6, release=1.8) * 0.65),
                 (2.2, sy.bell(523.3, 2.6, bright=0.5) * 0.18))
    sy.save(pack, "dw6_amen", rv(amen, 3.5, 0.55), max_distance=128)
    # the closed codex dissolves into light: high bells settle over a soft "oo", the last breath of the spell
    seal = sy.at(3.6, (0.0, sy.bell(1046.5, 2.6, bright=0.5) * 0.28), (0.12, sy.bell(784.0, 2.6, bright=0.5) * 0.24),
                 (0.24, sy.bell(659.3, 2.8, bright=0.45) * 0.2), (0.0, sy.shimmer(2.4, 3000, 22)[::-1] * 0.22),
                 (0.3, _chord(261.6, 3.2, "oo", (1.0, 1.5, 2.0), voices=3, attack=0.7, release=1.6) * 0.42))
    sy.save(pack, "dw6_seal", rv(seal, 3.5, 0.55), max_distance=128)


def build(pack):
    build_particles(pack)
    build_sounds(pack)
