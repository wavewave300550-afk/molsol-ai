"""
Orison - particles and sound.

Visual language: pale spectral-blue clock marks edged in near-black for danger,
small hollow rings for safety, footprints that light where someone has been,
falling sand, counted numerals (I, II, III) and thin shadow wisps.
Sound language: escapement ticks, a heavy pendulum, a judge's gavel, and
everything said twice - once dry, once again a moment later.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from PIL import Image, ImageDraw

from kit import particles as PT
from kit import sfx as S

TEX = "textures/particle/abm/orison"
SHEET = 64
CELL = 16


def sprite_sheet() -> Image.Image:
    img = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pale, blue, dark, gold, sand = (223, 233, 255), (143, 166, 216), (10, 14, 32), (203, 189, 138), (226, 214, 160)

    def cell(i):
        return (i % 4) * CELL, (i // 4) * CELL

    # 0 danger mark: a clock-hand lozenge, pale core in a dark rim (reads on light and dark floors)
    x, y = cell(0)
    d.polygon([(x + 8, y + 1), (x + 13, y + 8), (x + 8, y + 15), (x + 3, y + 8)], fill=dark + (255,))
    d.polygon([(x + 8, y + 3), (x + 11, y + 8), (x + 8, y + 13), (x + 5, y + 8)], fill=pale + (255,))
    d.line([(x + 8, y + 5), (x + 8, y + 11)], fill=blue + (255,))
    # 1 fill disc: a faint dial that fills as time runs out
    x, y = cell(1)
    for r, a in ((7, 60), (6, 95), (4, 130), (2, 170)):
        d.ellipse([x + 8 - r, y + 8 - r, x + 7 + r, y + 7 + r], fill=blue + (a,))
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=pale + (230,))
    for (px, py) in ((7, 2), (8, 2), (13, 7), (13, 8), (7, 13), (8, 13), (2, 7), (2, 8)):
        d.point((x + px, y + py), fill=dark + (255,))
    # 2 safe mark: small hollow ring
    x, y = cell(2)
    d.ellipse([x + 4, y + 4, x + 11, y + 11], outline=(214, 240, 222, 255))
    d.point((x + 7, y + 7), fill=(240, 252, 244, 255))
    # 3 footprint echo
    x, y = cell(3)
    d.ellipse([x + 5, y + 2, x + 10, y + 9], fill=pale + (235,), outline=dark + (255,))
    d.ellipse([x + 6, y + 10, x + 9, y + 14], fill=pale + (235,), outline=dark + (255,))
    # 4 sand grains
    x, y = cell(4)
    for (px, py) in ((3, 4), (7, 2), (11, 5), (5, 8), (9, 9), (12, 11), (4, 12), (8, 13)):
        d.point((x + px, y + py), fill=sand + (255,))
        d.point((x + px + 1, y + py), fill=gold + (220,))
    # 5..7 numerals I, II, III
    for k in range(3):
        x, y = cell(5 + k)
        n = k + 1
        w = n * 3 - 1
        sx = x + 8 - w // 2 - 1
        d.rectangle([sx - 1, y + 2, sx + w + 1, y + 3], fill=pale + (255,))
        d.rectangle([sx - 1, y + 12, sx + w + 1, y + 13], fill=pale + (255,))
        for i in range(n):
            d.rectangle([sx + i * 3, y + 3, sx + i * 3 + 1, y + 12], fill=pale + (255,))
        d.rectangle([sx - 2, y + 1, sx + w + 2, y + 1], fill=dark + (200,))
        d.rectangle([sx - 2, y + 14, sx + w + 2, y + 14], fill=dark + (200,))
    # 8 shadow wisp
    x, y = cell(8)
    d.line([(x + 8, y + 14), (x + 6, y + 9), (x + 9, y + 5), (x + 7, y + 1)], fill=dark + (230,), width=2)
    d.line([(x + 9, y + 13), (x + 7, y + 9), (x + 10, y + 5)], fill=(40, 52, 96, 170))
    # 9 glass shard
    x, y = cell(9)
    d.polygon([(x + 3, y + 12), (x + 7, y + 2), (x + 12, y + 10)], fill=(185, 201, 230, 150), outline=(244, 248, 255, 255))
    d.line([(x + 6, y + 9), (x + 8, y + 5)], fill=(255, 255, 255, 255))
    # 10 glint
    x, y = cell(10)
    d.line([(x + 8, y + 1), (x + 8, y + 14)], fill=pale + (255,))
    d.line([(x + 1, y + 8), (x + 14, y + 8)], fill=pale + (255,))
    d.rectangle([x + 7, y + 7, x + 9, y + 9], fill=(255, 255, 255, 255))
    # 11 spark (jammed mechanism)
    x, y = cell(11)
    d.line([(x + 3, y + 12), (x + 8, y + 7), (x + 6, y + 6), (x + 12, y + 2)], fill=gold + (255,))
    d.point((x + 12, y + 2), fill=(255, 255, 255, 255))
    # 12 echo ghost: a vertical afterimage streak
    x, y = cell(12)
    d.rectangle([x + 6, y + 1, x + 9, y + 14], fill=blue + (120,))
    d.rectangle([x + 7, y + 2, x + 8, y + 13], fill=pale + (200,))
    # 13 pulse ring (hourglass drain)
    x, y = cell(13)
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=sand + (255,), width=1)
    d.ellipse([x + 3, y + 3, x + 12, y + 12], outline=gold + (150,), width=1)
    return img


def sp(i: int) -> PT.Sprite:
    return PT.Sprite(TEX, SHEET, (i % 4) * CELL, (i // 4) * CELL, CELL, CELL)


def particles() -> Dict[str, dict]:
    pale = (0.92, 0.95, 1.0)
    flat_decal = lambda ident, sprite, size, life, spin=0: PT.effect(ident, sprite, PT.merge(      # noqa: E731
        PT.once(1), PT.point(), PT.speed(0), PT.spin("v.particle_random_1 * 360" if spin else 0, 0), PT.life(life),
        PT.billboard([size, size], PT.FLAT), PT.tint(1, 1, 1, PT.FADE_IN_OUT)), material="particles_blend")
    out = {
        "orison_tg_line": PT.tg_line("abm:orison_tg_line", sp(0), pale, width=0.34, density=1.8),
        "orison_tg_arc": PT.tg_arc("abm:orison_tg_arc", sp(0), pale, width=0.34, density=1.6),
        "orison_tg_disc": PT.tg_disc("abm:orison_tg_disc", sp(1), (0.8, 0.88, 1.0), alpha=0.5),
        "orison_safe_line": PT.tg_line("abm:orison_safe_line", sp(2), (0.86, 1.0, 0.9), width=0.3, density=1.2, pulse=0.0),
        "orison_safe_arc": PT.tg_arc("abm:orison_safe_arc", sp(2), (0.86, 1.0, 0.9), width=0.3, density=1.1, pulse=0.0),
        "orison_strike": PT.burst("abm:orison_strike", sp(12), count=6, radius=0.3, vel=3.5, size=0.26,
                                  lifetime="0.35 + v.particle_random_1 * 0.3", gravity=-2.0, drag=2.0,
                                  color=(0.9, 0.94, 1.0), material="particles_blend"),
        "orison_footprint": flat_decal("abm:orison_footprint", sp(3), 0.45, 1.6, spin=1),
        "orison_sand": PT.burst("abm:orison_sand", sp(4), count=14, radius=0.35, vel=1.6, size=0.2,
                                lifetime="0.7 + v.particle_random_1 * 0.6", gravity=9, drag=0.6),
        "orison_numeral_1": PT.mote("abm:orison_numeral_1", sp(5), size=0.5, lifetime=0.9, rise=0.5, drift=0.0, material="particles_alpha"),
        "orison_numeral_2": PT.mote("abm:orison_numeral_2", sp(6), size=0.5, lifetime=0.9, rise=0.5, drift=0.0, material="particles_alpha"),
        "orison_numeral_3": PT.mote("abm:orison_numeral_3", sp(7), size=0.5, lifetime=0.9, rise=0.5, drift=0.0, material="particles_alpha"),
        "orison_wisp": PT.burst("abm:orison_wisp", sp(8), count=10, radius=0.6, vel=0.9, size=0.4,
                                lifetime="0.8 + v.particle_random_1 * 0.7", gravity=-1.6, drag=1.2, shrink=True,
                                color=(1, 1, 1), material="particles_blend"),
        "orison_shard": PT.burst("abm:orison_shard", sp(9), count=14, radius=0.3, vel=5, size=0.18,
                                 gravity=14, drag=1.0, spin_rate=640, material="particles_blend"),
        "orison_glint": PT.mote("abm:orison_glint", sp(10), size=0.7, lifetime=0.5, rise=0.0, drift=0.0,
                                color=(0.9, 0.95, 1.0), material="particles_add"),
        "orison_spark": PT.burst("abm:orison_spark", sp(11), count=8, radius=0.2, vel=4, size=0.16, gravity=10, drag=1.4,
                                 material="particles_add"),
        "orison_echo": PT.mote("abm:orison_echo", sp(12), size=0.9, lifetime=0.7, rise=0.25, drift=0.05,
                               color=(0.85, 0.92, 1.0), material="particles_blend"),
        "orison_pulse": flat_decal("abm:orison_pulse", sp(13), 2.2, 0.8),
    }
    return out


def client_particles() -> Dict[str, str]:
    return {"sand": "abm:orison_sand", "wisp": "abm:orison_wisp", "shard": "abm:orison_shard",
            "glint": "abm:orison_glint", "spark": "abm:orison_spark"}


# --------------------------------------------------------------------------- sound

def _tick(seed, f=2600, dur=0.05):
    return S.mixdown((S.click(dur, f, seed, 6), 0, 1.0), (S.click(dur * 0.6, f * 1.9, (seed, 2), 8), 0.002, 0.5))


def _echoed(x, delay=0.22, gain=0.45, taps=2):
    """Everything Orison does is heard again a moment later."""
    return S.delay_mix(x, [(delay * (i + 1), gain ** (i + 1)) for i in range(taps)])


def _gavel(seed):
    wood = S.resonate(S.noise(0.2, seed), [(420, 5, 1.0), (910, 6, 0.6), (1700, 4, 0.3)]) * S.env_exp(0.2, 0.035, 0.0006)
    return S.mixdown((wood, 0, 1.0), (S.thud(96, 0.3, 0.5, seed), 0, 0.9), (S.click(0.02, 3000, seed, 3), 0, 0.4))


def _whoosh(seed, dur=0.6, f0=120, f1=900):
    return S.sweep_bandpass(S.noise(dur, seed, "pink"), f0, f1, 1.4) * np.sin(np.pi * S.t_axis(dur) / dur) ** 1.4


def _hiss(seed, dur=1.0, f=5200):
    """Running sand."""
    return S.highpass(S.noise(dur, seed), f * 0.6) * S.env_adsr(dur, 0.08, 0.1, 0.8, 0.3) * 0.6


def _ratchet(seed, dur=0.8, rate=22, accel=0.0):
    return S.grains(dur, rate, lambda i: _tick((seed, i), 1800 + (i % 3) * 500, 0.03), seed, jitter=0.1, accel=accel)


def _low_bell(freq, dur, seed):
    return S.bell(freq, dur, seed=seed, bright=0.7,
                  partials=[(0.5, 0.7, 1.0), (1, 1.0, 0.8), (1.48, 0.5, 0.5), (2.02, 0.5, 0.4), (2.9, 0.25, 0.22), (4.1, 0.12, 0.12)])


def _breath(seed, dur=1.2, f=700):
    """A restrained spectral exhale."""
    n = S.bandpass(S.noise(dur, seed, "pink"), f, 2.2)
    return n * S.env_adsr(dur, dur * 0.4, 0.1, 0.7, dur * 0.4)


def _glass_break(seed, dur=0.9):
    body = S.resonate(S.noise(dur, seed), [(3100, 7, 1.0), (4700, 8, 0.8), (7300, 6, 0.5)]) * S.env_exp(dur, 0.08, 0.001)
    tinkle = S.grains(dur, 30, lambda i: S.bell(2800 + S.rng("gb", seed, i).random() * 3600, 0.14, seed=(seed, i)) * 0.25, seed, jitter=0.9)
    return S.mixdown((body, 0, 1.0), (tinkle * np.linspace(1, 0, len(tinkle)) ** 1.3, 0.03, 0.8))


def sounds() -> Dict[str, dict]:
    def ev(clips, volume=1.0, lo=6.0, hi=48.0):
        return {"clips": clips, "volume": volume, "min": lo, "max": hi}

    o: Dict[str, dict] = {}
    o["tick"] = ev({f"tick{i}": _tick(("tk", i), 2400 + i * 500) for i in range(2)}, 0.6, 4, 28)
    o["tap"] = ev({f"tap{i}": S.mixdown((_gavel(("tp", i)) * 0.6, 0, 1.0), (_tick(("tp", i), 3200), 0, 0.5)) for i in range(2)}, 0.7, 6, 40)
    o["step"] = ev({f"step{i}": S.mixdown((_tick(("st", i), 1500 + i * 300, 0.04), 0, 1.0), (S.thud(170 - i * 20, 0.1, 0.3, ("st", i)), 0.003, 0.5),
                                          (_tick(("st2", i), 1500 + i * 300, 0.04), 0.14, 0.3)) for i in range(2)}, 0.55, 4, 30)
    o["idle"] = ev({f"idle{i}": S.reverb(S.mixdown(*[(_tick(("id", i, k), 2200 if k % 2 == 0 else 1700), k * 0.5, 0.5 if k % 2 == 0 else 0.4) for k in range(4)],
                                                   (_breath(("id", i), 1.6, 520), 0.3, 0.25)), 1.0, 0.3, ("id", i)) for i in range(2)}, 0.4, 5, 30)
    o["hurt"] = ev({f"hurt{i}": S.mixdown((S.resonate(S.noise(0.25, ("hu", i)), [(760 + i * 140, 9, 1.0), (1900, 7, 0.5)]) * S.env_exp(0.25, 0.05), 0, 1.0),
                                          (_tick(("hu", i), 3000), 0, 0.5)) for i in range(2)}, 0.7, 4, 24)
    o["gavel"] = ev({"gavel": S.reverb(_echoed(_gavel("gv"), 0.24, 0.4, 2), 1.0, 0.22, "gv")}, 1.0, 8, 60)
    o["echo_read"] = ev({"echo_read": S.mixdown((_ratchet("er", 0.7, 16), 0, 0.5), (_breath("er", 0.9, 900), 0.05, 0.6))}, 0.8)
    o["echo_mark"] = ev({"echo_mark": S.reverb(S.mixdown((_low_bell(392, 1.0, "em")[::-1].copy() * 0.6, 0, 0.8), (_tick("em", 2800), 0.95, 0.8),
                                                         (_breath("em", 1.0, 1100), 0, 0.4)), 1.0, 0.3, "em")}, 0.9, 8, 56)
    o["echo_burst"] = ev({f"echo_burst{i}": _echoed(S.mixdown((S.thud(70 + i * 8, 0.4, 0.5, ("eb", i)), 0, 1.0), (_breath(("eb", i), 0.4, 1500), 0, 0.5),
                                                              (_tick(("eb", i), 2000), 0, 0.5)), 0.18, 0.5, 2) for i in range(2)}, 0.95, 8, 56)
    o["verdict_wind"] = ev({"verdict_wind": S.mixdown((_whoosh("vw", 1.4, 60, 500)[::-1].copy(), 0, 0.8), (_ratchet("vw", 1.3, 9, 2.0), 0, 0.5))}, 0.95, 8, 60)
    o["verdict_swing"] = ev({"verdict_swing": S.reverb(S.mixdown((_whoosh("vs", 0.8, 90, 1400), 0, 1.0), (_low_bell(98, 1.6, "vs"), 0.3, 0.8)), 1.4, 0.3, "vs")}, 1.0, 10, 64)
    o["wound_mark"] = ev({f"wound_mark{i}": S.mixdown((_ratchet(("wm", i), 0.3, 26), 0, 0.7), (_low_bell(523 + i * 98, 0.5, ("wm", i)), 0.0, 0.3)) for i in range(2)}, 0.8, 6, 48)
    o["wound_burst"] = ev({f"wound_burst{i}": S.reverb(_echoed(S.mixdown((S.thud(62 + i * 7, 0.5, 0.6, ("wb", i)), 0, 1.0), (_tick(("wb", i), 2400, 0.06), 0, 0.7),
                                                                         (_low_bell(196, 0.8, ("wb", i)), 0, 0.4)), 0.2, 0.4, 1), 0.9, 0.2, ("wb", i)) for i in range(2)}, 1.0, 8, 60)
    o["drain_wind"] = ev({"drain_wind": S.mixdown((_hiss("dw", 0.9), 0, 0.6), (_ratchet("dw", 0.8, 12, 1.0), 0, 0.5))}, 0.8)
    o["drain_cast"] = ev({"drain_cast": S.reverb(S.mixdown((_hiss("dc", 1.4), 0, 0.8), (_low_bell(1175, 0.9, "dc"), 0, 0.35), (S.thud(110, 0.3, 0.4, "dc"), 0, 0.6)), 1.0, 0.25, "dc")}, 0.95, 8, 56)
    o["drain_pulse"] = ev({"drain_pulse": _echoed(S.mixdown((_hiss("dp", 0.5), 0, 0.7), (S.thud(84, 0.35, 0.5, "dp"), 0.02, 0.8)), 0.2, 0.4, 1)}, 0.85, 6, 40)
    o["hourglass_break"] = ev({"hourglass_break": S.mixdown((_glass_break("hb", 0.7), 0, 0.9), (_hiss("hb", 0.8), 0.05, 0.6))}, 0.9, 6, 40)
    o["witness_hush"] = ev({"witness_hush": S.mixdown((_breath("wh", 0.7, 400), 0, 0.7), (_ratchet("wh", 0.5, 14, -0.9), 0, 0.5))}, 0.8)
    o["witness_lock"] = ev({"witness_lock": S.mixdown((_tick("wl", 3400, 0.06), 0, 1.0), (_low_bell(1568, 0.5, "wl"), 0, 0.35), (S.click(0.03, 900, "wl", 4), 0.004, 0.7))}, 1.0, 8, 60)
    o["shadow_strike"] = ev({"shadow_strike": S.reverb(S.mixdown((_whoosh("ss", 0.35, 300, 2600), 0, 0.9), (_breath("ss", 0.5, 1900), 0.05, 0.6),
                                                                 (S.thud(76, 0.4, 0.5, "ss"), 0.2, 0.8)), 0.9, 0.25, "ss")}, 0.95, 8, 56)
    o["exchange_mark"] = ev({"exchange_mark": S.reverb(S.mixdown((_low_bell(659, 1.0, "xm")[::-1].copy() * 0.7, 0, 0.8), (_breath("xm", 0.9, 1400), 0.1, 0.5)), 1.0, 0.3, "xm")}, 0.9, 8, 60)
    o["exchange_swap"] = ev({"exchange_swap": _echoed(S.mixdown((_whoosh("xs", 0.3, 2400, 200), 0, 1.0), (_tick("xs", 3000, 0.05), 0.28, 0.9),
                                                                (_whoosh("xs2", 0.3, 200, 2400), 0.3, 0.9)), 0.26, 0.4, 1)}, 1.0, 10, 64)
    o["hour_call"] = ev({"hour_call": S.reverb(S.mixdown((_low_bell(131, 2.4, "hc"), 0, 0.9), (_ratchet("hc", 1.6, 10, 1.6), 0.1, 0.4),
                                                         (_breath("hc", 1.8, 600), 0.2, 0.4)), 1.8, 0.35, "hc")}, 1.0, 12, 72)
    o["hour_chime"] = ev({f"hour_chime{i}": S.reverb(_low_bell((523, 659, 784)[i], 1.1, ("hch", i)), 1.0, 0.3, ("hch", i)) for i in range(3)}, 0.9, 10, 72)
    o["hour_strike"] = ev({f"hour_strike{i}": S.reverb(_echoed(S.mixdown((_low_bell(87 + i * 11, 1.8, ("hs", i)), 0, 1.0), (S.thud(52, 0.7, 0.6, ("hs", i)), 0, 1.0),
                                                                         (_tick(("hs", i), 2200, 0.07), 0, 0.5)), 0.3, 0.45, 2), 1.4, 0.3, ("hs", i)) for i in range(2)}, 1.0, 12, 72)
    o["stagger"] = ev({"stagger": S.mixdown((_ratchet("sg", 0.6, 30, -0.8), 0, 0.9), (S.thud(80, 0.5, 0.5, "sg"), 0.2, 0.8),
                                            (S.resonate(S.noise(0.5, "sg"), [(640, 8, 1.0), (1400, 6, 0.5)]) * S.env_exp(0.5, 0.12), 0.05, 0.6))}, 1.0)
    o["transition_crack"] = ev({"transition_crack": S.reverb(S.mixdown((S.grains(1.3, 16, lambda i: S.click(0.02, 4200 + (i % 4) * 600, ("tc", i), 4) * 0.8, "tc", accel=2.2), 0, 0.9),
                                                                       (_breath("tc", 1.3, 800), 0, 0.5)), 1.0, 0.25, "tc")}, 1.0, 12, 72)
    o["transition_shatter"] = ev({"transition_shatter": S.reverb(S.mixdown((_glass_break("tsh", 1.3), 0, 1.0), (_hiss("tsh", 2.0), 0.1, 0.8),
                                                                           (_low_bell(65, 2.4, "tsh"), 0, 0.8), (S.thud(46, 0.9, 0.6, "tsh"), 0, 1.0)), 1.8, 0.3, "tsh")}, 1.0, 14, 80)
    o["shadow_emerge"] = ev({"shadow_emerge": S.reverb(S.mixdown((_breath("se", 1.8, 300)[::-1].copy(), 0, 0.9), (_low_bell(110, 2.0, "se")[::-1].copy() * 0.5, 0, 0.7),
                                                                 (_tick("se", 1900, 0.06), 1.8, 0.8), (_tick("se2", 1900, 0.06), 1.62, 0.5)), 1.6, 0.35, "se")}, 1.0, 12, 72)
    o["intro_wind"] = ev({"intro_wind": S.reverb(S.mixdown((_ratchet("iw", 2.4, 7, 2.4), 0, 0.8), (_breath("iw", 2.0, 500), 0.2, 0.4)), 1.2, 0.3, "iw")}, 0.95, 12, 72)
    o["intro_strike"] = ev({"intro_strike": S.reverb(_echoed(S.mixdown((_low_bell(147, 2.2, "is"), 0, 1.0), (_tick("is", 2400, 0.06), 0, 0.7)), 0.3, 0.4, 2), 1.6, 0.35, "is")}, 1.0, 14, 80)
    slow = S.mixdown(*[(_tick(("ds", k), 2300 if k % 2 == 0 else 1750), t, 0.9 - k * 0.1) for k, t in enumerate((0.0, 0.35, 0.8, 1.4, 2.2))])
    o["death_stop"] = ev({"death_stop": S.reverb(S.mixdown((slow, 0, 1.0), (_breath("ds", 2.4, 420), 0.2, 0.4)), 1.4, 0.3, "ds")}, 1.0, 12, 72)
    o["ribbon_fall"] = ev({f"ribbon_fall{i}": S.mixdown((S.resonate(S.noise(0.5, ("rf", i)), [(1800 + i * 300, 9, 1.0), (3300, 8, 0.6)]) * S.env_exp(0.5, 0.09), 0, 0.9),
                                                        (S.grains(0.4, 18, lambda k: _tick(("rf", i, k), 3000, 0.02) * 0.6, ("rf", i)), 0.05, 0.6)) for i in range(2)}, 0.8, 6, 48)
    o["death_empty"] = ev({"death_empty": S.reverb(S.mixdown((_hiss("de", 2.2), 0, 0.9), (_breath("de", 2.0, 350), 0.3, 0.4)), 1.4, 0.3, "de")}, 0.95, 12, 72)
    o["death_fall"] = ev({"death_fall": S.reverb(S.mixdown((S.thud(48, 0.9, 0.6, "df"), 0, 1.0), (S.grains(0.9, 20, lambda k: _tick(("df", k), 1400 + (k % 5) * 400, 0.04), "df", accel=-0.8), 0.05, 0.8),
                                                           (_low_bell(73, 2.0, "df"), 0.1, 0.6)), 1.8, 0.3, "df")}, 1.0, 12, 72)
    o["trophy"] = ev({"trophy": S.reverb(S.mixdown((_low_bell(784, 1.4, "tr"), 0, 0.7), (_tick("tr", 2400), 0.5, 0.6), (_tick("tr2", 1800), 1.0, 0.5), (_hiss("tr", 0.8), 0.2, 0.25)), 1.2, 0.35, "tr")}, 0.8, 4, 16)
    return o
