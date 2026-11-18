"""
Cantor XIII - particles and sound.

Visual language: every danger mark is a struck note - a gilt note-head with a
dark rim that pulses; safety is a pale hollow quatrefoil that does not move.
A soft ring leaves the tower's feet on every beat, so the rhythm can be read
with the sound off; a rest sign hangs over the bell when the rhythm is withheld.
Sound language: one great bronze bell, four small ones, a pipe organ in D minor,
breaking glass - all synthesized here.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from PIL import Image, ImageDraw

from kit import particles as PT
from kit import sfx as S

TEX = "textures/particle/abm/cantor"
SHEET = 64
CELL = 16


def sprite_sheet() -> Image.Image:
    img = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold, gold2, dark, bronze, teal = (232, 208, 126), (194, 160, 74), (22, 18, 14), (134, 96, 47), (76, 148, 130)
    blue, purple, crimson, white = (79, 127, 224), (154, 98, 216), (184, 70, 86), (250, 244, 224)

    def cell(i):
        return (i % 4) * CELL, (i // 4) * CELL

    # 0 danger mark: a note-head, dark rim, gilt body, a short stem
    x, y = cell(0)
    d.ellipse([x + 2, y + 6, x + 11, y + 13], fill=dark + (255,))
    d.ellipse([x + 3, y + 7, x + 10, y + 12], fill=gold + (255,))
    d.line([(x + 11, y + 9), (x + 11, y + 2)], fill=dark + (255,), width=2)
    d.line([(x + 11, y + 2), (x + 14, y + 4)], fill=gold2 + (255,))
    d.point((x + 5, y + 8), fill=white + (255,))
    # 1 fill disc: soft bronze stain with a bright rim
    x, y = cell(1)
    for r, a in ((7, 60), (6, 95), (4, 130), (2, 170)):
        d.ellipse([x + 8 - r, y + 8 - r, x + 7 + r, y + 7 + r], fill=bronze + (a,))
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=gold + (235,))
    # 2 safe mark: hollow quatrefoil
    x, y = cell(2)
    for cx, cy in ((8, 5), (8, 11), (5, 8), (11, 8)):
        d.ellipse([x + cx - 2, y + cy - 2, x + cx + 2, y + cy + 2], outline=(206, 228, 255, 255))
    d.point((x + 8, y + 8), fill=(240, 248, 255, 255))
    # 3..5 glass shards: blue, purple, crimson
    for k, col in enumerate((blue, purple, crimson)):
        x, y = cell(3 + k)
        pts = [(3, 12), (8, 2), (12, 9)] if k == 0 else [(2, 5), (13, 4), (9, 13)] if k == 1 else [(5, 3), (12, 7), (6, 13)]
        d.polygon([(x + px, y + py) for px, py in pts], fill=col + (235,), outline=dark + (255,))
        d.line([(x + pts[0][0] + 2, y + pts[0][1] - 2), (x + pts[1][0], y + pts[1][1] + 3)], fill=white + (220,))
    # 6 dust puff
    x, y = cell(6)
    for (px, py, r, a) in ((6, 9, 4, 110), (10, 7, 3, 130), (8, 6, 2, 160)):
        d.ellipse([x + px - r, y + py - r, x + px + r, y + py + r], fill=(150, 140, 120, a))
    # 7 rising note glyph (beamed pair)
    x, y = cell(7)
    for nx in (3, 9):
        d.ellipse([x + nx, y + 10, x + nx + 4, y + 13], fill=gold + (255,))
        d.line([(x + nx + 4, y + 11), (x + nx + 4, y + 3)], fill=gold + (255,))
    d.line([(x + 7, y + 3), (x + 13, y + 3)], fill=gold + (255,), width=2)
    # 8 beat ring
    x, y = cell(8)
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=gold + (255,), width=2)
    d.ellipse([x + 4, y + 4, x + 11, y + 11], outline=teal + (150,))
    # 9 rest sign (a whole rest hanging from a line)
    x, y = cell(9)
    d.line([(x + 2, y + 6), (x + 13, y + 6)], fill=white + (255,))
    d.rectangle([x + 5, y + 7, x + 10, y + 10], fill=white + (255,))
    d.rectangle([x + 1, y + 1, x + 14, y + 14], outline=(206, 228, 255, 110))
    # 10 gilt spark
    x, y = cell(10)
    d.line([(x + 8, y + 2), (x + 8, y + 13)], fill=gold + (255,))
    d.line([(x + 2, y + 8), (x + 13, y + 8)], fill=gold + (255,))
    d.point((x + 8, y + 8), fill=white + (255,))
    # 11 bronze fragment
    x, y = cell(11)
    d.polygon([(x + 3, y + 4), (x + 12, y + 3), (x + 13, y + 10), (x + 6, y + 13)], fill=bronze + (255,), outline=dark + (255,))
    d.line([(x + 5, y + 6), (x + 10, y + 5)], fill=teal + (255,))
    d.line([(x + 6, y + 11), (x + 11, y + 9)], fill=gold2 + (255,))
    # 12 glass shard projectile: a long sliver, pointing along +X
    x, y = cell(12)
    d.polygon([(x + 1, y + 8), (x + 9, y + 5), (x + 15, y + 8), (x + 9, y + 11)], fill=blue + (240,), outline=dark + (255,))
    d.line([(x + 3, y + 8), (x + 13, y + 8)], fill=white + (230,))
    d.polygon([(x + 5, y + 7), (x + 9, y + 6), (x + 9, y + 8)], fill=purple + (240,))
    # 13 wave mark: a short bright bar with a dark shadow (for moving wave fronts)
    x, y = cell(13)
    d.rectangle([x + 2, y + 6, x + 13, y + 10], fill=dark + (255,))
    d.rectangle([x + 3, y + 7, x + 12, y + 9], fill=gold + (255,))
    d.rectangle([x + 6, y + 7, x + 9, y + 9], fill=white + (255,))
    return img


def sp(i: int) -> PT.Sprite:
    return PT.Sprite(TEX, SHEET, (i % 4) * CELL, (i // 4) * CELL, CELL, CELL)


def particles() -> Dict[str, dict]:
    gilt = (1.0, 0.95, 0.78)
    out = {
        "cantor_tg_line": PT.tg_line("abm:cantor_tg_line", sp(0), gilt, width=0.36, density=1.7, draw_time=0.1),
        "cantor_tg_arc": PT.tg_arc("abm:cantor_tg_arc", sp(0), gilt, width=0.36, density=1.5, draw_time=0.1),
        "cantor_tg_disc": PT.tg_disc("abm:cantor_tg_disc", sp(1), (1.0, 0.86, 0.6), alpha=0.5),
        "cantor_safe_line": PT.tg_line("abm:cantor_safe_line", sp(2), (0.85, 0.93, 1.0), width=0.32, density=1.1, pulse=0.0, draw_time=0.1),
        "cantor_safe_arc": PT.tg_arc("abm:cantor_safe_arc", sp(2), (0.85, 0.93, 1.0), width=0.32, density=1.0, pulse=0.0, draw_time=0.1),
        # moving wave fronts are redrawn every other tick, so they draw at once and carry no pulse
        "cantor_wave_line": PT.tg_line("abm:cantor_wave_line", sp(13), (1, 1, 1), width=0.42, density=1.25, pulse=0.0, draw_time=0.05),
        "cantor_wave_arc": PT.tg_arc("abm:cantor_wave_arc", sp(13), (1, 1, 1), width=0.42, density=1.25, pulse=0.0, draw_time=0.05),
        "cantor_strike": PT.burst("abm:cantor_strike", sp(10), count=6, radius=0.25, vel=4.5, size=0.2, gravity=6, drag=1.6,
                                  material="particles_add"),
        "cantor_spark": PT.burst("abm:cantor_spark", sp(10), count=14, radius=0.5, vel=6, size=0.22, gravity=7, drag=1.4,
                                 material="particles_add"),
        "cantor_dust": PT.burst("abm:cantor_dust", sp(6), count=10, radius=0.6, vel=1.8, size=0.4,
                                lifetime="0.6 + v.particle_random_1 * 0.6", gravity=-0.3, drag=2.4, shrink=False,
                                color=(0.72, 0.68, 0.6), material="particles_blend"),
        "cantor_note": PT.burst("abm:cantor_note", sp(7), count=5, radius=0.5, vel=1.2, size=0.3,
                                lifetime="1.0 + v.particle_random_1 * 0.8", gravity=-1.6, drag=0.8, shrink=False,
                                color=(1.0, 0.92, 0.7), material="particles_blend"),
        "cantor_glass": PT.burst("abm:cantor_glass", sp(3), count=14, radius=0.4, vel=5.5, size=0.17, gravity=13, drag=1.0,
                                 spin_rate=700, frames=3),
        "cantor_fragments": PT.burst("abm:cantor_fragments", sp(11), count=16, radius=0.8, vel=5, size=0.26,
                                     lifetime="0.9 + v.particle_random_1 * 0.7", gravity=14, drag=0.8, spin_rate=500),
        "cantor_beat": PT.effect("abm:cantor_beat", sp(8), PT.merge(
            PT.once(1), PT.point(), PT.speed(0), PT.life(0.45),
            PT.billboard([f"0.7 + {PT.AGE} * 1.9", f"0.7 + {PT.AGE} * 1.9"], PT.FLAT),
            PT.tint(1.0, 0.92, 0.7, f"math.clamp((1 - {PT.AGE}) * 1.6, 0, 1) * 0.8")), material="particles_blend"),
        "cantor_rest": PT.effect("abm:cantor_rest", sp(9), PT.merge(
            PT.once(1), PT.point(), PT.speed(0), PT.life("v.life"),
            PT.billboard([f"0.9 + math.sin(v.particle_age * 300) * 0.06", f"0.9 + math.sin(v.particle_age * 300) * 0.06"]),
            PT.tint(0.9, 0.96, 1.0, PT.FADE_IN_OUT)), material="particles_blend"),
        "cantor_shard": PT.flyer("abm:cantor_shard", sp(12), size=(0.55, 0.28), align=True),
        "cantor_ring_flash": PT.effect("abm:cantor_ring_flash", sp(8), PT.merge(
            PT.once(1), PT.point(), PT.speed(0), PT.life(0.35),
            PT.billboard([f"v.r * (0.2 + {PT.AGE} * 0.8)", f"v.r * (0.2 + {PT.AGE} * 0.8)"], PT.FLAT),
            PT.tint(1.0, 0.9, 0.62, f"math.clamp((1 - {PT.AGE}) * 2, 0, 1)")), material="particles_blend"),
    }
    return out


def client_particles() -> Dict[str, str]:
    return {"spark": "abm:cantor_spark", "dust": "abm:cantor_dust", "note": "abm:cantor_note",
            "glass": "abm:cantor_glass", "fragments": "abm:cantor_fragments"}


# --------------------------------------------------------------------------- sound

D2, A2, D3, F3, G3, A3, BB3, CS4, D4, E4, F4, G4, A4 = 73.42, 110.0, 146.83, 174.61, 196.0, 220.0, 233.08, 277.18, 293.66, 329.63, 349.23, 392.0, 440.0


def _chord(freqs, dur, seed, attack=0.09, release=0.3, chiff=0.2):
    out = np.zeros(int(dur * S.SR))
    for i, f in enumerate(freqs):
        out += S.organ(f, dur, attack=attack, release=release, seed=(seed, i), chiff=chiff)
    return out / max(1, len(freqs))


def _great_bell(dur=3.2, freq=98.0, seed="gb"):
    return S.reverb(S.bell(freq, dur, seed=seed, bright=0.9), 2.2, 0.3, seed, damp=3800)


def _small_bell(freq, dur=1.6, seed="sb"):
    return S.reverb(S.bell(freq, dur, seed=seed, bright=1.1), 1.2, 0.22, seed)


def _clank(seed, dur=0.35, f=900):
    body = S.resonate(S.noise(dur, seed), [(f, 8, 1.0), (f * 2.3, 9, 0.7), (f * 3.7, 7, 0.4)]) * S.env_exp(dur, 0.06, 0.001)
    return S.mixdown((body, 0, 1.0), (S.thud(90, 0.2, 0.5, seed), 0, 0.6))


def _creak(seed, dur=0.9, f0=180, f1=420):
    t = S.t_axis(dur)
    saw = S.osc(np.linspace(f0, f1, len(t)) * (1 + 0.05 * np.sin(2 * np.pi * 9 * t)), dur, "saw", 16)
    grit = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * (22 + 18 * t / dur) * t))
    return S.resonate(saw * grit, [(600, 5, 1.0), (1500, 6, 0.6)]) * S.env_adsr(dur, 0.08, 0.1, 0.8, 0.3)


def _rumble(seed, dur=1.6, cutoff=260):
    t = S.t_axis(dur)
    return S.lowpass(S.noise(dur, seed, "brown"), cutoff) * np.sin(np.pi * t / dur) ** 0.7


def _whoosh(seed, dur=0.5, f0=300, f1=2200):
    return S.sweep_bandpass(S.noise(dur, seed, "pink"), f0, f1, 1.6) * np.sin(np.pi * S.t_axis(dur) / dur) ** 1.5


def _shatter(seed, dur=0.8):
    body = S.resonate(S.noise(dur, seed), [(3100, 7, 1.0), (4700, 8, 0.8), (7400, 6, 0.6), (1700, 4, 0.4)]) * S.env_exp(dur, 0.08, 0.001)
    tinkle = S.grains(dur, 38, lambda i: S.bell(2600 + S.rng("gl", seed, i).random() * 3600, 0.14, seed=(seed, i)) * 0.25,
                      seed, jitter=0.9) * np.linspace(1, 0, int(dur * S.SR)) ** 1.5
    return S.mixdown((body, 0, 1.0), (tinkle, 0.02, 0.9))


def sounds() -> Dict[str, dict]:
    def ev(clips, volume=1.0, lo=8.0, hi=64.0):
        return {"clips": clips, "volume": volume, "min": lo, "max": hi}

    out: Dict[str, dict] = {}
    out["step"] = ev({f"step{i}": S.reverb(S.mixdown((S.thud(52 + i * 5, 0.6, 0.6, ("st", i)), 0, 1.0), (_clank(("st", i), 0.3, 520 + i * 90), 0.01, 0.5),
                                                     (_small_bell(392 + i * 60, 0.6, ("st", i)), 0.05, 0.12)), 0.9, 0.2, ("st", i))
                      for i in range(3)}, 0.9, 8, 56)
    out["idle"] = ev({f"idle{i}": S.reverb(S.mixdown((_chord([D2, A2], 2.6, ("id", i), 0.8, 1.0, 0.05), 0, 0.5),
                                                     (_creak(("id", i), 0.8, 150, 260), 0.9, 0.3),
                                                     (_small_bell(523 + i * 131, 1.2, ("id", i)), 1.3, 0.18)), 1.6, 0.35, ("id", i))
                      for i in range(2)}, 0.5, 8, 48)
    out["creak"] = ev({"creak": S.mixdown((_creak("ck", 1.0), 0, 0.9), (_clank("ck", 0.3, 400), 0.75, 0.5))}, 0.9)
    out["bell_strike"] = ev({"bell_strike": S.mixdown((_great_bell(3.4), 0, 1.0), (S.thud(46, 0.8, 0.5, "bs"), 0, 0.7),
                                                      (_clank("bs", 0.25, 700), 0, 0.4))}, 1.0, 14, 96)
    out["bell_small"] = ev({f"bell_small{i}": _small_bell(f, 1.6, ("bsm", i)) for i, f in enumerate((392.0, 523.25))}, 0.9, 8, 56)
    out["bell_pulse"] = ev({f"bell_pulse{i}": S.mixdown((_small_bell(f, 1.2, ("bp", i)), 0, 1.0), (_whoosh(("bp", i), 0.4, 300, 1400), 0, 0.3))
                            for i, f in enumerate((440.0, 587.33))}, 0.9, 8, 56)
    out["wave"] = ev({"wave": S.reverb(S.mixdown((_rumble("wv", 1.8), 0, 1.0), (_whoosh("wv", 1.2, 200, 1500), 0, 0.5),
                                                 (_chord([D3, A3], 1.4, "wv", 0.02, 0.8, 0.5), 0, 0.5)), 1.2, 0.25, "wv")}, 1.0, 12, 80)
    out["organ_rise"] = ev({"organ_rise": S.mixdown(*[(S.organ(f, 0.5, attack=0.03, release=0.2, seed=("or", i)), i * 0.11, 0.6)
                                                         for i, f in enumerate((D3, F3, A3, D4))])}, 0.9)
    charge = _chord([D3, A3, D4, F4], 3.2, "oc", attack=2.4, release=0.2, chiff=0.1) * np.linspace(0.25, 1.0, int(3.2 * S.SR))
    out["organ_charge"] = ev({"organ_charge": S.reverb(S.mixdown((charge, 0, 1.0), (_rumble("oc", 3.0, 180) * np.linspace(0.1, 1, int(3.0 * S.SR)), 0.1, 0.5)),
                                                       1.4, 0.25, "oc")}, 1.0, 12, 80)
    out["organ_blast"] = ev({"organ_blast": S.reverb(S.soft_clip(S.mixdown((_chord([D2, D3, A3, D4, F4, A4], 1.3, "ob", 0.01, 0.9, 0.6), 0, 1.0),
                                                                            (_rumble("ob", 1.0, 320), 0, 0.8), (_whoosh("ob", 0.5, 400, 3600), 0, 0.6)), 1.8),
                                                     1.6, 0.3, "ob")}, 1.0, 14, 96)
    out["glass_open"] = ev({"glass_open": S.mixdown((_creak("go", 0.7, 300, 700), 0, 0.7), (_clank("go", 0.25, 1300), 0.6, 0.6),
                                                    (S.grains(0.6, 14, lambda i: S.bell(2400 + i * 170, 0.2, seed=("go", i)) * 0.3, "go"), 0.1, 0.5))}, 0.9)
    out["glass_shard"] = ev({f"glass_shard{i}": S.mixdown((_whoosh(("gs", i), 0.3, 1500, 5200), 0, 0.8), (_shatter(("gs", i), 0.35), 0, 0.5),
                                                         (_small_bell(1568 + i * 262, 0.5, ("gs", i)), 0, 0.3)) for i in range(2)}, 0.85, 8, 56)
    out["glass_break"] = ev({"glass_break": _shatter("gb", 0.9)}, 0.8, 6, 40)
    out["silence"] = ev({"silence": S.mixdown((S.click(0.04, 500, "si", 2), 0, 0.8), (_rumble("si", 1.2, 90) * np.linspace(1, 0, int(1.2 * S.SR)), 0.02, 0.9),
                                              (_chord([D3, A3], 0.4, "si", 0.01, 0.35, 0.0)[::-1].copy() * 0.0, 0, 0.0))}, 0.8)
    out["implode"] = ev({"implode": S.reverb(S.mixdown((S.bell(98.0, 1.6, seed="im")[::-1].copy(), 0, 0.9), (_whoosh("im", 1.3, 2600, 200), 0.2, 0.7),
                                                       (_great_bell(2.2, 98.0, "im2"), 1.55, 1.0), (S.thud(44, 0.7, 0.5, "im"), 1.55, 0.8)), 1.6, 0.25, "im")},
                        1.0, 14, 96)
    out["detach"] = ev({"detach": S.mixdown((_clank("dt", 0.4, 800), 0, 1.0), (_small_bell(392.0, 1.0, "dt"), 0.05, 0.6), (_small_bell(523.25, 1.0, "dt2"), 0.15, 0.6),
                                            (_whoosh("dt", 0.5, 400, 1800), 0.05, 0.5))}, 0.95)
    out["bell_destroy"] = ev({"bell_destroy": S.mixdown((_clank("bd", 0.5, 600), 0, 1.0), (_shatter("bd", 0.5), 0.02, 0.4),
                                                        (S.bell(392.0, 0.6, seed="bd", detune=0.03), 0, 0.5))}, 0.95, 6, 40)
    out["requiem_start"] = ev({"requiem_start": S.reverb(S.mixdown((_chord([D2, A2, D3], 2.4, "rs", 1.2, 0.6, 0.1), 0, 1.0),
                                                                   (_small_bell(587.33, 1.4, "rs"), 0.2, 0.3), (_small_bell(440.0, 1.4, "rs2"), 0.8, 0.3)),
                                                         1.8, 0.3, "rs")}, 1.0, 14, 96)
    cadence = [[D3, F3, A3, D4], [G3, BB3, D4, G4], [A2, CS4, E4, A4], [D2, D3, A3, D4, F4]]
    for i, ch in enumerate(cadence):
        out[f"requiem_{i + 1}"] = ev({f"requiem_{i + 1}": S.reverb(S.mixdown((_chord(ch, 1.7, ("rq", i), 0.02, 0.9, 0.4), 0, 0.9),
                                                                             (_great_bell(2.6, [98.0, 110.0, 82.41, 73.42][i], ("rq", i)), 0, 0.9),
                                                                             (S.thud(48, 0.7, 0.5, ("rq", i)), 0, 0.6)), 1.8, 0.28, ("rq", i))}, 1.0, 14, 96)
    ring = S.mixdown(*[(S.bell(98.0 * (1 + 0.01 * k), 0.9, seed=("tr", k)), k * 0.21, 0.5 + k * 0.07) for k in range(7)])
    out["transition_ring"] = ev({"transition_ring": S.reverb(ring, 1.6, 0.3, "tr")}, 1.0, 14, 96)
    out["transition_crack"] = ev({"transition_crack": S.mixdown((_clank("tc", 0.6, 1400), 0, 1.0), (S.bell(98.0, 1.4, seed="tc", detune=0.04), 0, 0.8),
                                                                (S.grains(0.8, 40, lambda i: S.click(0.02, 3000 + i * 40, ("tc", i), 3) * 0.6, "tc"), 0.05, 0.5))}, 1.0, 14, 96)
    out["transition_break"] = ev({"transition_break": S.reverb(S.mixdown((_clank("tb", 0.7, 500), 0, 1.0), (S.thud(40, 1.0, 0.6, "tb"), 0, 1.0),
                                                                         (S.bell(69.3, 2.0, seed="tb", detune=0.05), 0, 0.9), (_rumble("tb", 1.2), 0.1, 0.6)),
                                                               1.8, 0.3, "tb")}, 1.0, 14, 96)
    out["transition_unfold"] = ev({"transition_unfold": S.mixdown((_creak("tu", 1.6, 140, 600), 0, 0.9),
                                                                  *[(S.organ(f, 0.35, attack=0.02, release=0.15, seed=("tu", i)), 0.2 + i * 0.13, 0.5)
                                                                    for i, f in enumerate((D3, 155.56, A3, 207.65, D4, 311.13, A4, 415.3))])}, 1.0, 12, 80)
    out["transition_roar"] = ev({"transition_roar": S.reverb(S.soft_clip(S.mixdown((_chord([D2, 77.78, D3, 207.65, A3, 311.13, D4], 2.2, "trr", 0.03, 1.2, 0.5), 0, 1.0),
                                                                                    (_rumble("trr", 2.0, 300), 0, 0.7)), 2.2), 2.0, 0.32, "trr")}, 1.0, 14, 96)
    out["stagger"] = ev({"stagger": S.mixdown((_clank("sg", 0.5, 420), 0, 1.0), (S.bell(98.0, 1.2, seed="sg", detune=0.03), 0.05, 0.6),
                                              (_creak("sg", 0.9, 500, 160), 0.1, 0.6), (_chord([D3, 155.56], 0.7, "sg", 0.01, 0.6, 0.3), 0.05, 0.4))}, 1.0)
    out["hit"] = ev({f"hit{i}": S.mixdown((_clank(("ht", i), 0.3, 700 + i * 260), 0, 1.0), (S.bell(196.0 * (1 + i * 0.25), 0.5, seed=("ht", i)), 0, 0.35))
                     for i in range(3)}, 0.8, 4, 28)
    out["beat"] = ev({"beat": S.mixdown((S.click(0.03, 1400, "bt", 4), 0, 0.8), (S.thud(110, 0.1, 0.3, "bt"), 0, 0.4))}, 0.35, 6, 32)
    out["death_toll"] = ev({"death_toll": S.reverb(S.mixdown((S.bell(98.0, 1.8, seed="dtl"), 0, 1.0), (S.bell(92.5, 1.8, seed="dtl2"), 0.5, 0.9),
                                                             (S.bell(87.3, 2.2, seed="dtl3", detune=0.03), 1.0, 0.9)), 1.8, 0.3, "dtl")}, 1.0, 14, 96)
    out["death_bell"] = ev({"death_bell": S.reverb(S.mixdown((_clank("db", 0.8, 380), 0, 1.0), (S.bell(61.7, 2.4, seed="db", detune=0.06), 0, 1.0),
                                                             (S.thud(38, 1.2, 0.6, "db"), 0.85, 1.0), (_clank("db2", 0.6, 300), 0.86, 0.8)), 2.0, 0.3, "db")}, 1.0, 14, 96)
    for i, f in enumerate((D4, A3, F3)):
        t = S.t_axis(1.1)
        fall = S.organ(f, 1.1, attack=0.02, release=0.8, seed=("dp", i), chiff=0.3)
        bend = np.sin(2 * np.pi * np.cumsum(f * (1 - 0.18 * (t / 1.1) ** 2)) / S.SR) * S.env_adsr(1.1, 0.02, 0.1, 0.7, 0.8)
        out[f"death_pipe{i + 1}"] = ev({f"death_pipe{i + 1}": S.mixdown((fall * np.linspace(1, 0, len(t)), 0, 0.6), (bend * np.linspace(1, 0, len(t)), 0, 0.5),
                                                                       (_clank(("dp", i), 0.25, 900), 0.45, 0.4))}, 0.85, 10, 64)
    out["death_leg"] = ev({"death_leg": S.reverb(S.mixdown((_creak("dl", 0.5, 400, 120), 0, 0.8), (S.thud(42, 0.9, 0.6, "dl"), 0.35, 1.0),
                                                           (_clank("dl", 0.5, 340), 0.36, 0.8)), 1.0, 0.25, "dl")}, 1.0, 12, 80)
    last = S.organ(D3, 4.0, attack=0.3, release=3.2, seed="df", chiff=0.05) * np.linspace(1, 0, int(4.0 * S.SR)) ** 1.4
    out["death_final"] = ev({"death_final": S.reverb(S.mixdown((last, 0, 1.0), (S.bell(D3, 3.0, seed="df", bright=0.6), 0, 0.3)), 2.4, 0.4, "df")}, 0.9, 14, 96)
    out["intro"] = ev({"intro": S.reverb(S.mixdown((_creak("in", 1.8, 90, 300), 0, 0.8), (_rumble("in", 2.2, 160), 0.2, 0.7),
                                                   (_chord([D2, A2], 2.6, "in", 1.6, 0.8, 0.05), 0.6, 0.6)), 1.8, 0.3, "in")}, 1.0, 14, 96)
    out["trophy"] = ev({"trophy": S.reverb(S.mixdown((S.bell(196.0, 2.2, seed="tp"), 0, 0.9), (S.bell(293.66, 1.8, seed="tp2"), 0.35, 0.5)), 1.6, 0.4, "tp")}, 0.8, 4, 16)
    return out
