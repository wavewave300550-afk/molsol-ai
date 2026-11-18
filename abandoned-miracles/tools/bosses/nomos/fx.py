"""
Nomos - particles and sound.

Visual language: everything Nomos does to the floor is DRAWN. Danger is a wet
ink stroke edged in vellum (so it reads on dark and on pale floors alike);
safety is a hollow survey benchmark (a cross inside a ring) in pale emerald.
Sound language: clockwork ratchets, a pen scratching, parchment folding, brass
struck once. Nothing here is sampled; it is all synthesised below.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from PIL import Image, ImageDraw

from kit import particles as PT
from kit import sfx as S

TEX = "textures/particle/abm/nomos"
SHEET = 64
CELL = 16


def sprite_sheet() -> Image.Image:
    img = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    vellum, vellum2, ink, ink2 = (236, 224, 189), (184, 159, 115), (17, 19, 31), (51, 64, 106)
    emerald, emerald2, steel, brass = (47, 174, 116), (182, 255, 214), (154, 162, 174), (169, 138, 52)

    def cell(i):
        return (i % 4) * CELL, (i // 4) * CELL

    # 0 danger stroke: a square-nibbed ink mark on a vellum ground
    x, y = cell(0)
    d.rectangle([x + 2, y + 4, x + 13, y + 11], fill=vellum + (255,), outline=vellum2 + (255,))
    d.rectangle([x + 4, y + 6, x + 11, y + 9], fill=ink + (255,))
    d.line([(x + 5, y + 6), (x + 10, y + 6)], fill=ink2 + (255,))
    # 1 fill: a spreading ink stain with a vellum rim
    x, y = cell(1)
    for r, a in ((7, 60), (6, 100), (4, 140), (2, 180)):
        d.ellipse([x + 8 - r, y + 8 - r, x + 7 + r, y + 7 + r], fill=ink2 + (a,))
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=vellum + (235,))
    # 2 safe: survey benchmark (cross in a ring)
    x, y = cell(2)
    d.ellipse([x + 3, y + 3, x + 12, y + 12], outline=emerald2 + (255,))
    d.line([(x + 7, y + 1), (x + 7, y + 14)], fill=emerald2 + (255,))
    d.line([(x + 1, y + 7), (x + 14, y + 7)], fill=emerald2 + (255,))
    d.point((x + 7, y + 7), fill=emerald + (255,))
    # 3 grid tick
    x, y = cell(3)
    d.line([(x + 7, y + 3), (x + 7, y + 12)], fill=vellum + (255,))
    d.line([(x + 3, y + 7), (x + 12, y + 7)], fill=vellum + (255,))
    d.rectangle([x + 6, y + 6, x + 8, y + 8], outline=ink + (255,))
    # 4 ink drop, 5 ink blot
    x, y = cell(4)
    d.polygon([(x + 8, y + 2), (x + 11, y + 9), (x + 8, y + 13), (x + 5, y + 9)], fill=ink + (255,), outline=ink2 + (255,))
    d.point((x + 7, y + 8), fill=(111, 134, 201, 255))
    x, y = cell(5)
    d.ellipse([x + 3, y + 5, x + 12, y + 12], fill=ink + (255,))
    d.ellipse([x + 9, y + 3, x + 13, y + 7], fill=ink + (255,))
    d.ellipse([x + 2, y + 10, x + 5, y + 13], fill=ink2 + (255,))
    # 6, 7 parchment flakes
    for k, pts in enumerate(([(3, 4), (12, 5), (11, 12), (4, 10)], [(5, 3), (13, 8), (7, 13), (2, 8)])):
        x, y = cell(6 + k)
        d.polygon([(x + px, y + py) for px, py in pts], fill=vellum + (245,), outline=vellum2 + (255,))
        d.line([(x + 5, y + 7), (x + 10, y + 8)], fill=ink + (200,))
        if k == 0:
            d.point((x + 8, y + 10), fill=emerald + (255,))
    # 8 compass dart: drawn along the cell's vertical axis (the billboard aligns that axis with its velocity)
    x, y = cell(8)
    d.polygon([(x + 8, y + 0), (x + 10, y + 7), (x + 8, y + 9), (x + 6, y + 7)], fill=emerald + (255,), outline=emerald2 + (255,))
    d.polygon([(x + 8, y + 15), (x + 10, y + 8), (x + 8, y + 7), (x + 6, y + 8)], fill=steel + (255,), outline=ink + (255,))
    d.rectangle([x + 7, y + 7, x + 8, y + 8], fill=brass + (255,))
    # 9 emerald spark
    x, y = cell(9)
    d.line([(x + 8, y + 1), (x + 8, y + 14)], fill=emerald2 + (255,))
    d.line([(x + 1, y + 8), (x + 14, y + 8)], fill=emerald2 + (255,))
    d.line([(x + 5, y + 5), (x + 11, y + 11)], fill=emerald + (220,))
    d.line([(x + 11, y + 5), (x + 5, y + 11)], fill=emerald + (220,))
    # 10 dust
    x, y = cell(10)
    for (px, py, r, a) in ((6, 9, 4, 110), (10, 7, 3, 130), (8, 6, 2, 160)):
        d.ellipse([x + px - r, y + py - r, x + px + r, y + py + r], fill=vellum2 + (a,))
    # 11 aim mark: a thin open bracket (tracking line, before a needle locks)
    x, y = cell(11)
    d.arc([x + 4, y + 4, x + 11, y + 11], 0, 360, fill=emerald + (230,))
    d.point((x + 7, y + 7), fill=emerald2 + (255,))
    # 12 standing border: a heavy ruled bar
    x, y = cell(12)
    d.rectangle([x + 1, y + 3, x + 14, y + 12], fill=ink + (255,), outline=vellum + (255,))
    d.line([(x + 3, y + 7), (x + 12, y + 7)], fill=ink2 + (255,))
    d.line([(x + 3, y + 9), (x + 12, y + 9)], fill=emerald + (255,))
    return img


def sp(i: int) -> PT.Sprite:
    return PT.Sprite(TEX, SHEET, (i % 4) * CELL, (i // 4) * CELL, CELL, CELL)


def particles() -> Dict[str, dict]:
    white = (1.0, 1.0, 1.0)
    return {
        "nomos_tg_line": PT.tg_line("abm:nomos_tg_line", sp(0), white, width=0.34, density=1.8, draw_time=0.45, pulse=0.2),
        "nomos_tg_arc": PT.tg_arc("abm:nomos_tg_arc", sp(0), white, width=0.34, density=1.6, draw_time=0.4, pulse=0.2),
        "nomos_tg_disc": PT.tg_disc("abm:nomos_tg_disc", sp(1), (0.8, 0.85, 1.0), alpha=0.55),
        "nomos_safe_line": PT.tg_line("abm:nomos_safe_line", sp(2), white, width=0.32, density=0.9, pulse=0.0, draw_time=0.3),
        "nomos_safe_arc": PT.tg_arc("abm:nomos_safe_arc", sp(2), white, width=0.32, density=0.9, pulse=0.0, draw_time=0.3),
        "nomos_aim_line": PT.tg_line("abm:nomos_aim_line", sp(11), white, width=0.2, density=0.8, pulse=0.0, draw_time=0.05),
        "nomos_border_line": PT.tg_line("abm:nomos_border_line", sp(12), white, width=0.42, density=1.5, pulse=0.0, draw_time=0.05),
        "nomos_strike": PT.burst("abm:nomos_strike", sp(4), count=7, radius=0.25, vel=4.5, size=0.18, gravity=13, drag=1.0,
                                 frames=2),
        "nomos_ink": PT.burst("abm:nomos_ink", sp(4), count=10, radius=0.2, vel=3.0, size=0.14,
                              lifetime="0.5 + v.particle_random_1 * 0.5", gravity=12, drag=0.6, frames=2),
        "nomos_flake": PT.burst("abm:nomos_flake", sp(6), count=14, radius=0.7, vel=2.6, size=0.22,
                                lifetime="1.0 + v.particle_random_1 * 1.0", gravity=2.6, drag=2.4, spin_rate=240, frames=2),
        "nomos_spark": PT.mote("abm:nomos_spark", sp(9), size=0.7, lifetime=0.5, rise=0.0, drift=0.0, color=(0.85, 1, 0.92),
                               material="particles_add"),
        "nomos_dust": PT.burst("abm:nomos_dust", sp(10), count=9, radius=0.5, vel=1.4, size=0.34,
                               lifetime="0.6 + v.particle_random_1 * 0.6", gravity=-0.3, drag=2.5, shrink=False,
                               color=(0.92, 0.88, 0.76), material="particles_blend"),
        "nomos_grid": PT.effect("abm:nomos_grid", sp(3), PT.merge(
            PT.once(1), PT.point(), PT.speed(0), PT.life(1.2), PT.billboard([0.3, 0.3], PT.FLAT),
            PT.tint(1, 1, 1, PT.FADE_IN_OUT)), material="particles_blend"),
        "nomos_dart": PT.flyer("abm:nomos_dart", sp(8), size=(0.34, 0.7), align=True),
    }


def client_particles() -> Dict[str, str]:
    return {"ink": "abm:nomos_ink", "flake": "abm:nomos_flake", "spark": "abm:nomos_spark", "dust": "abm:nomos_dust"}


# --------------------------------------------------------------------------- sound building blocks

def _ratchet(seed, dur=0.6, rate=22, f=2600, accel=0.0, q=6.0):
    """Clockwork: evenly spaced pawl clicks, each a tiny struck resonance."""
    def grain(i):
        r = S.rng("rt", seed, i)
        return S.click(0.018, f * (0.92 + r.random() * 0.16), (seed, i), q) * (0.7 + r.random() * 0.3)
    return S.grains(dur, rate, grain, seed, jitter=0.06, accel=accel)


def _scratch(seed, dur=0.8, f0=1800, f1=3200):
    """A ruling pen dragged over stone: stick-slip noise."""
    n = S.sweep_bandpass(S.noise(dur, seed), f0, f1, 3.0)
    t = S.t_axis(dur)
    slip = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * (31 + 9 * np.sin(2 * np.pi * 3 * t)) * t))
    return n * slip * S.env_adsr(dur, 0.03, 0.1, 0.85, 0.15)


def _paper(seed, dur=0.6, density=55, rising=False):
    """Parchment: a dense rustle of soft crackles."""
    def grain(i):
        r = S.rng("pp", seed, i)
        return S.bandpass(S.noise(0.02 + r.random() * 0.03, (seed, i)), 1400 + r.random() * 3600, 1.2) * (0.3 + r.random() * 0.7)
    g = S.grains(dur, density, grain, seed, jitter=0.9)
    env = np.linspace(0.3, 1, len(g)) if rising else np.linspace(1, 0.3, len(g))
    return g * env


def _brass(freq, dur=1.2, seed="brass", bright=1.0):
    """Struck brass plate: fewer, lower partials than a bell, short and dry."""
    return S.bell(freq, dur, seed=seed, bright=bright,
                  partials=[(1, 1, 0.55), (1.47, 0.6, 0.4), (2.09, 0.45, 0.3), (2.56, 0.3, 0.2), (3.87, 0.16, 0.12)])


def _whirr(seed, dur=1.0, f0=90, f1=420):
    """A needle spinning up on its pivot."""
    n = len(S.t_axis(dur))
    f = np.geomspace(f0, f1, n)
    tone = S.osc(f, dur, "square", 9) * 0.4 + S.sine(f * 2.01, dur) * 0.3
    return S.lowpass(tone, 2600) * S.env_adsr(dur, 0.1, 0.1, 0.9, 0.2)


def _splat(seed, dur=0.35):
    n = S.lowpass(S.noise(dur, seed, "brown"), 1100)
    return n * S.env_exp(dur, 0.06, 0.002) + 0.5 * S.grains(dur, 24, lambda i: S.click(0.02, 800 + 300 * (i % 4), (seed, i), 2) * 0.5, seed)


def _zip(seed, dur=0.3, f0=600, f1=5200):
    return S.sweep_bandpass(S.noise(dur, seed), f0, f1, 2.4) * np.linspace(0.2, 1, int(dur * S.SR)) ** 2


def sounds() -> Dict[str, dict]:
    def ev(clips, volume=1.0, lo=6.0, hi=48.0):
        return {"clips": clips, "volume": volume, "min": lo, "max": hi}

    o: Dict[str, dict] = {}
    o["step"] = ev({f"step{i}": S.mixdown((S.click(0.025, 3300 + i * 500, ("st", i), 7), 0, 1.0),
                                           (_brass(1900 + i * 240, 0.18, ("st", i)), 0.002, 0.35),
                                           (S.thud(120, 0.07, 0.3, ("st", i)), 0.0, 0.3)) for i in range(3)}, 0.5, 4, 28)
    o["idle"] = ev({f"idle{i}": S.mixdown((_ratchet(("id", i), 1.4, 9 + i * 3, 2100), 0, 0.5),
                                           (_whirr(("id", i), 1.2, 70, 110) * 0.5, 0.1, 0.4)) for i in range(2)}, 0.4, 5, 30)
    o["scribe"] = ev({f"scribe{i}": S.mixdown((_scratch(("sc", i), 1.1, 1500 + i * 300, 3400), 0, 1.0),
                                               (_ratchet(("sc", i), 0.5, 26, 3000), 0.0, 0.25)) for i in range(2)}, 0.85)
    o["incision"] = ev({f"incision{i}": S.reverb(S.mixdown((_zip(("in", i), 0.22), 0, 1.0), (S.thud(70 + i * 8, 0.45, 0.55, ("in", i)), 0.2, 1.0),
                                                           (_brass(330 + i * 40, 0.8, ("in", i)), 0.2, 0.4)), 0.8, 0.2, ("in", i))
                        for i in range(2)}, 1.0, 8, 64)
    o["calipers"] = ev({"calipers": S.mixdown((_ratchet("cal", 0.9, 30, 2400, accel=-0.5), 0, 0.8), (_scratch("cal", 0.9, 900, 1600), 0.05, 0.4))}, 0.9)
    o["shear"] = ev({"shear": S.reverb(S.mixdown((_scratch("sh", 2.6, 500, 1500), 0, 0.9), (_whirr("sh", 2.6, 60, 150), 0, 0.5),
                                                 (_ratchet("sh", 2.6, 14, 1800), 0.1, 0.35)), 1.0, 0.2, "sh")}, 0.95, 10, 64)
    o["shear_hit"] = ev({"shear_hit": S.mixdown((_zip("shh", 0.16, 900, 4200), 0, 0.9), (S.thud(90, 0.3, 0.5, "shh"), 0.1, 0.9))}, 0.9)
    o["border_stamp"] = ev({"border_stamp": S.mixdown((_splat("bs"), 0, 1.0), (S.thud(64, 0.5, 0.5, "bs"), 0, 1.0),
                                                      (_brass(220, 0.9, "bs"), 0.02, 0.35))}, 1.0, 8, 56)
    o["border_set"] = ev({"border_set": S.reverb(S.mixdown((_brass(196, 1.4, "bst"), 0, 0.8), (_brass(294, 1.2, "bst2"), 0.06, 0.6),
                                                           (_scratch("bst", 0.5, 2400, 900), 0, 0.5)), 1.0, 0.25, "bst")}, 0.95, 10, 64)
    o["border_touch"] = ev({"border_touch": S.mixdown((_splat("bt", 0.25), 0, 0.9), (_zip("bt", 0.18, 2000, 600), 0, 0.5))}, 0.8, 4, 24)
    o["gate_ready"] = ev({"gate_ready": S.mixdown((_ratchet("gr", 0.8, 18, 2200, accel=1.6), 0, 0.9), (_whirr("gr", 0.8, 110, 520), 0, 0.6))}, 0.95)
    o["gate_fold"] = ev({"gate_fold": S.mixdown((_paper("gf", 0.7, 70), 0, 1.0), (_zip("gf", 0.5, 3000, 500)[::-1].copy(), 0.1, 0.5),
                                                (_brass(523, 0.5, "gf"), 0.55, 0.3))}, 1.0, 8, 64)
    o["gate_unfold"] = ev({"gate_unfold": S.mixdown((_paper("gu", 0.35, 80, True), 0, 1.0), (_zip("gu", 0.3, 500, 3600), 0, 0.6))}, 1.0, 8, 64)
    o["gate_arrive"] = ev({"gate_arrive": S.reverb(S.mixdown((S.thud(52, 0.7, 0.6, "ga"), 0, 1.0), (_brass(147, 1.4, "ga"), 0, 0.7),
                                                             (_paper("ga", 0.4, 60), 0.02, 0.5)), 1.0, 0.25, "ga")}, 1.0, 10, 72)
    o["dart_spin"] = ev({"dart_spin": S.mixdown((_whirr("ds", 1.3, 80, 640), 0, 0.9), (_ratchet("ds", 1.3, 12, 3000, accel=2.2), 0, 0.5))}, 0.9)
    o["dart_lock"] = ev({f"dart_lock{i}": S.mixdown((S.click(0.03, 2600 + i * 300, ("dl", i), 8), 0, 1.0),
                                                    (S.click(0.03, 1700 + i * 200, ("dl2", i), 8), 0.07, 0.9),
                                                    (_brass(880 + i * 110, 0.3, ("dl", i)), 0.07, 0.4)) for i in range(2)}, 0.9)
    o["dart_fire"] = ev({f"dart_fire{i}": S.mixdown((S.sine(np.linspace(1500 + i * 200, 260, int(0.2 * S.SR)), 0.2) * S.env_exp(0.2, 0.05), 0, 0.8),
                                                    (_zip(("df", i), 0.25, 900, 5000), 0.01, 0.8)) for i in range(2)}, 0.9, 6, 56)
    o["unfold"] = ev({f"unfold{i}": S.mixdown((_paper(("uf", i), 0.5, 60, True), 0, 1.0), (_zip(("uf", i), 0.3, 400, 1800), 0.05, 0.35))
                      for i in range(2)}, 0.85)
    o["fold_slam"] = ev({f"fold_slam{i}": S.reverb(S.mixdown((_paper(("fs", i), 0.25, 90), 0, 1.0), (S.thud(84 + i * 10, 0.4, 0.5, ("fs", i)), 0.02, 1.0),
                                                            (_zip(("fs", i), 0.12, 2400, 700), 0, 0.5)), 0.7, 0.18, ("fs", i))
                         for i in range(2)}, 1.0, 10, 64)
    o["recalc_begin"] = ev({"recalc_begin": S.reverb(S.mixdown((_ratchet("rb", 1.8, 10, 1500, accel=2.5), 0, 0.8), (_whirr("rb", 1.8, 50, 300), 0, 0.7),
                                                               (_brass(131, 2.2, "rb"), 1.2, 0.8), (_brass(196, 2.0, "rb2"), 1.35, 0.6)), 1.6, 0.3, "rb")},
                           1.0, 14, 80)
    o["recalc_shift"] = ev({f"recalc_shift{i}": S.mixdown((_ratchet(("rs", i), 0.8, 20, 1900 + i * 300, accel=1.4), 0, 0.9),
                                                          (_whirr(("rs", i), 0.8, 120, 480), 0, 0.5), (_paper(("rs", i), 0.5, 40), 0.1, 0.4))
                            for i in range(2)}, 0.95, 12, 72)
    o["recalc_strike"] = ev({f"recalc_strike{i}": S.reverb(S.mixdown((S.thud(46 + i * 6, 0.9, 0.6, ("rk", i)), 0, 1.0),
                                                                    (_brass(110 * (1 + i * 0.19), 1.8, ("rk", i)), 0, 0.9),
                                                                    (_brass(165 * (1 + i * 0.19), 1.6, ("rk2", i)), 0.01, 0.6),
                                                                    (_zip(("rk", i), 0.2), 0, 0.6)), 1.4, 0.28, ("rk", i))
                             for i in range(2)}, 1.0, 14, 80)
    o["stagger"] = ev({"stagger": S.mixdown((_brass(260, 0.9, "sg"), 0, 0.8), (_brass(392, 0.8, "sg2"), 0.09, 0.6),
                                            (_ratchet("sg", 0.9, 30, 2400, accel=-0.8), 0.05, 0.7), (S.thud(70, 0.5, 0.5, "sg"), 0.2, 0.8))}, 1.0)
    o["transition_shudder"] = ev({"transition_shudder": S.reverb(S.mixdown((_ratchet("tsh", 1.4, 34, 2600, accel=-0.4), 0, 0.9),
                                                                          (_brass(208, 1.5, "tsh"), 0.1, 0.6), (_scratch("tsh", 1.2, 700, 2600), 0.1, 0.5)),
                                                                 1.2, 0.25, "tsh")}, 1.0, 12, 72)
    o["transition_wind"] = ev({"transition_wind": S.mixdown((_whirr("tw", 2.0, 60, 900), 0, 0.9), (_ratchet("tw", 2.0, 10, 2000, accel=3.5), 0, 0.6))}, 1.0, 12, 72)
    o["transition_rise"] = ev({"transition_rise": S.reverb(S.mixdown((_ratchet("trr", 2.2, 16, 1500), 0, 0.7), (_whirr("trr", 2.2, 40, 160), 0, 0.8),
                                                                    (_brass(98, 2.4, "trr"), 1.6, 0.9)), 1.6, 0.3, "trr")}, 1.0, 14, 80)
    o["ring_release"] = ev({f"ring_release{i}": S.mixdown((_brass(660 + i * 180, 0.9, ("rr", i), 1.2), 0, 0.8), (_zip(("rr", i), 0.3, 700, 3000), 0, 0.6),
                                                          (S.click(0.03, 2400, ("rr", i), 6), 0, 0.8)) for i in range(2)}, 0.95, 10, 64)
    wob = S.t_axis(1.3)
    o["ring_drop"] = ev({f"ring_drop{i}": S.reverb(S.mixdown((_brass(520 + i * 140, 1.3, ("rd", i)) * (0.6 + 0.4 * np.sin(2 * np.pi * (6 + 14 * wob) * wob)), 0, 1.0),
                                                            (S.thud(110, 0.2, 0.4, ("rd", i)), 0, 0.6)), 0.9, 0.2, ("rd", i))
                         for i in range(2)}, 0.95, 10, 64)
    o["death_crumple"] = ev({"death_crumple": S.mixdown((_paper("dcr", 2.4, 75), 0, 1.0), (_scratch("dcr", 1.6, 2000, 500), 0.3, 0.4),
                                                        (_ratchet("dcr", 2.0, 14, 1600, accel=-0.7), 0.2, 0.5))}, 1.0, 12, 72)
    o["death_fall"] = ev({"death_fall": S.reverb(S.mixdown((S.thud(42, 1.0, 0.6, "dfl"), 0.78, 1.0), (_brass(174, 1.6, "dfl"), 0.8, 0.8),
                                                           (_brass(277, 1.2, "dfl2"), 0.86, 0.6), (_ratchet("dfl", 1.0, 26, 2200, accel=-0.8), 0, 0.7),
                                                           (_paper("dfl", 0.6, 60), 0.8, 0.6)), 1.6, 0.3, "dfl")}, 1.0, 14, 80)
    slow = S.mixdown(*[(S.click(0.03, 2500, ("ns", i), 8), sum(0.09 * 1.32 ** k for k in range(i)), 0.9 - i * 0.07) for i in range(8)])
    o["needle_slow"] = ev({"needle_slow": slow}, 0.9, 8, 48)
    o["needle_stop"] = ev({"needle_stop": S.reverb(S.mixdown((S.click(0.04, 1900, "nst", 9), 0, 1.0), (_brass(1245, 1.6, "nst", 0.7), 0.0, 0.35)), 1.6, 0.4, "nst")},
                          1.0, 8, 56)
    o["intro_unpack"] = ev({"intro_unpack": S.reverb(S.mixdown((_ratchet("iu", 2.4, 12, 1700, accel=0.8), 0, 0.8), (_paper("iu", 1.2, 40, True), 0.6, 0.5),
                                                               (_whirr("iu", 2.2, 40, 140), 0.1, 0.6)), 1.4, 0.3, "iu")}, 0.95, 12, 72)
    o["intro_level"] = ev({"intro_level": S.reverb(S.mixdown((_brass(784, 1.6, "il", 0.9), 0, 0.8), (_brass(1175, 1.4, "il2", 0.9), 0.22, 0.6),
                                                             (S.click(0.03, 2600, "il", 8), 0, 0.6)), 1.4, 0.35, "il")}, 0.95, 12, 72)
    o["hit_metal"] = ev({f"hit_metal{i}": S.mixdown((_brass(700 + i * 160, 0.35, ("hm", i)), 0, 0.8), (S.click(0.02, 4200, ("hm", i), 5), 0, 0.8))
                         for i in range(3)}, 0.75, 4, 28)
    o["trophy"] = ev({"trophy": S.reverb(S.mixdown((S.click(0.03, 2500, "tr", 8), 0, 0.8), (S.click(0.03, 2500, "tr2", 8), 0.35, 0.8),
                                                   (_brass(988, 1.6, "tr", 0.8), 0.7, 0.7)), 1.4, 0.4, "tr")}, 0.8, 4, 16)
    return o
