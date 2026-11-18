"""
Vesperra - particles and sound.

Visual language: bone-white fracture marks edged in burgundy for danger,
pale hollow lozenges for safety, porcelain shards, silk thread and blood-dark
droplets. Sound language: cracking glaze, shell on shell, chitin scrape, a
single restrained porcelain chime for anything ceremonial.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np
from PIL import Image, ImageDraw

from kit import particles as PT
from kit import sfx as S

TEX = "textures/particle/abm/vesperra"
SHEET = 64
CELL = 16


def sprite_sheet() -> Image.Image:
    img = Image.new("RGBA", (SHEET, SHEET), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ivory, ivory2, shade, wine, dark, gold = (246, 239, 220), (226, 214, 188), (150, 132, 104), (125, 31, 46), (40, 14, 20), (194, 160, 74)

    def cell(i):
        return (i % 4) * CELL, (i // 4) * CELL

    # 0 danger mark: a jagged bone splinter with a wine edge (reads on light and dark floors)
    x, y = cell(0)
    d.polygon([(x + 2, y + 9), (x + 6, y + 4), (x + 13, y + 6), (x + 14, y + 10), (x + 8, y + 12)], fill=wine + (255,))
    d.polygon([(x + 4, y + 9), (x + 7, y + 6), (x + 12, y + 7), (x + 12, y + 9), (x + 8, y + 10)], fill=ivory + (255,))
    d.line([(x + 6, y + 8), (x + 10, y + 8)], fill=shade + (255,))
    # 1 fill disc: soft radial stain
    x, y = cell(1)
    for r, a in ((7, 70), (6, 110), (4, 150), (2, 190)):
        d.ellipse([x + 8 - r, y + 8 - r, x + 7 + r, y + 7 + r], fill=wine + (a,))
    d.ellipse([x + 1, y + 1, x + 14, y + 14], outline=ivory + (230,))
    # 2 safe mark: hollow lozenge
    x, y = cell(2)
    d.polygon([(x + 8, y + 2), (x + 13, y + 8), (x + 8, y + 13), (x + 3, y + 8)], outline=(214, 236, 214, 255))
    d.point((x + 8, y + 8), fill=(240, 250, 240, 255))
    # 3..5 porcelain shards
    for k, pts in enumerate(([(3, 12), (8, 2), (12, 9)], [(2, 5), (13, 4), (9, 13)], [(5, 3), (12, 7), (6, 13), (3, 9)])):
        x, y = cell(3 + k)
        d.polygon([(x + px, y + py) for px, py in pts], fill=ivory + (255,), outline=shade + (255,))
        d.line([(x + pts[0][0] + 1, y + pts[0][1] - 1), (x + pts[1][0], y + pts[1][1] + 2)], fill=ivory2 + (255,))
        if k == 1:
            d.line([(x + 4, y + 6), (x + 11, y + 5)], fill=gold + (255,))
    # 6 bone dust puff
    x, y = cell(6)
    for (px, py, r, a) in ((6, 9, 4, 120), (10, 7, 3, 140), (8, 6, 2, 170)):
        d.ellipse([x + px - r, y + py - r, x + px + r, y + py + r], fill=ivory2 + (a,))
    # 7 silk thread segment
    x, y = cell(7)
    d.line([(x + 1, y + 8), (x + 14, y + 8)], fill=(240, 236, 226, 255))
    d.line([(x + 3, y + 9), (x + 12, y + 9)], fill=(200, 192, 176, 160))
    d.point((x + 8, y + 7), fill=(255, 255, 255, 255))
    # 8 flung plate (projectile)
    x, y = cell(8)
    d.polygon([(x + 2, y + 6), (x + 8, y + 1), (x + 14, y + 6), (x + 12, y + 14), (x + 4, y + 14)], fill=ivory + (255,), outline=shade + (255,))
    d.line([(x + 4, y + 12), (x + 12, y + 12)], fill=gold + (255,))
    d.line([(x + 6, y + 5), (x + 9, y + 9), (x + 8, y + 12)], fill=shade + (255,))
    d.polygon([(x + 7, y + 5), (x + 9, y + 7), (x + 7, y + 9), (x + 5, y + 7)], outline=gold + (255,))
    # 9 crown glint
    x, y = cell(9)
    d.line([(x + 8, y + 1), (x + 8, y + 14)], fill=(255, 244, 214, 255))
    d.line([(x + 1, y + 8), (x + 14, y + 8)], fill=(255, 244, 214, 255))
    d.line([(x + 5, y + 5), (x + 11, y + 11)], fill=(255, 226, 170, 200))
    d.line([(x + 11, y + 5), (x + 5, y + 11)], fill=(255, 226, 170, 200))
    # 10 droplet
    x, y = cell(10)
    d.polygon([(x + 8, y + 3), (x + 11, y + 9), (x + 8, y + 13), (x + 5, y + 9)], fill=wine + (255,), outline=dark + (255,))
    d.point((x + 7, y + 8), fill=(201, 86, 108, 255))
    # 11 fracture decal (lies on the floor after an eruption)
    x, y = cell(11)
    d.line([(x + 1, y + 8), (x + 5, y + 6), (x + 9, y + 9), (x + 14, y + 7)], fill=dark + (255,))
    d.line([(x + 5, y + 6), (x + 6, y + 2)], fill=dark + (255,))
    d.line([(x + 9, y + 9), (x + 10, y + 13)], fill=dark + (255,))
    d.line([(x + 2, y + 9), (x + 5, y + 7), (x + 9, y + 10)], fill=wine + (180,))
    # 12 molt flake
    x, y = cell(12)
    d.polygon([(x + 4, y + 5), (x + 11, y + 4), (x + 12, y + 10), (x + 6, y + 12)], fill=ivory2 + (235,), outline=shade + (255,))
    # 13 crescent segment (cast-off arc)
    x, y = cell(13)
    d.arc([x + 1, y + 3, x + 14, y + 20], 200, 340, fill=ivory + (255,), width=2)
    d.arc([x + 1, y + 5, x + 14, y + 22], 205, 335, fill=wine + (220,), width=1)
    return img


def sp(i: int) -> PT.Sprite:
    return PT.Sprite(TEX, SHEET, (i % 4) * CELL, (i // 4) * CELL, CELL, CELL)


def particles() -> Dict[str, dict]:
    bone = (1.0, 0.97, 0.9)
    out = {
        "vesperra_tg_line": PT.tg_line("abm:vesperra_tg_line", sp(0), bone, width=0.36, density=1.9),
        "vesperra_tg_arc": PT.tg_arc("abm:vesperra_tg_arc", sp(0), bone, width=0.36, density=1.7),
        "vesperra_tg_disc": PT.tg_disc("abm:vesperra_tg_disc", sp(1), (1.0, 0.85, 0.85), alpha=0.5),
        "vesperra_safe_line": PT.tg_line("abm:vesperra_safe_line", sp(2), (0.86, 1.0, 0.88), width=0.3, density=1.2, pulse=0.0),
        "vesperra_safe_arc": PT.tg_arc("abm:vesperra_safe_arc", sp(2), (0.86, 1.0, 0.88), width=0.3, density=1.1, pulse=0.0),
        "vesperra_thread": PT.tg_line("abm:vesperra_thread", sp(7), (1, 1, 1), width=0.3, density=2.6, pulse=0.12,
                                      draw_time=0.35),
        "vesperra_crescent": PT.tg_arc("abm:vesperra_crescent", sp(13), bone, width=0.5, density=1.4, pulse=0.0,
                                       draw_time=0.08),
        "vesperra_strike": PT.burst("abm:vesperra_strike", sp(3), count=7, radius=0.25, vel=5, size=0.2,
                                    gravity=14, drag=1.2, spin_rate=540, frames=3),
        "vesperra_shards": PT.burst("abm:vesperra_shards", sp(3), count=14, radius=0.3, vel=6, size=0.17,
                                    gravity=15, drag=1.0, spin_rate=720, frames=3),
        "vesperra_molt": PT.burst("abm:vesperra_molt", sp(12), count=18, radius=0.8, vel=3.2, size=0.24,
                                  lifetime="1.0 + v.particle_random_1 * 0.9", gravity=3.2, drag=2.2, spin_rate=260),
        "vesperra_dust": PT.burst("abm:vesperra_dust", sp(6), count=9, radius=0.4, vel=1.4, size=0.34,
                                  lifetime="0.6 + v.particle_random_1 * 0.6", gravity=-0.4, drag=2.5, shrink=False,
                                  color=(0.93, 0.89, 0.8), material="particles_blend"),
        "vesperra_drip": PT.burst("abm:vesperra_drip", sp(10), count=10, radius=0.3, vel=2.2, size=0.13,
                                  lifetime="0.7 + v.particle_random_1 * 0.5", gravity=11, drag=0.4),
        "vesperra_glint": PT.mote("abm:vesperra_glint", sp(9), size=0.75, lifetime=0.55, rise=0.0, drift=0.0,
                                  color=(1, 0.96, 0.85), material="particles_add"),
        "vesperra_fracture": PT.effect("abm:vesperra_fracture", sp(11), PT.merge(
            PT.once(1), PT.point(), PT.speed(0), PT.spin("v.particle_random_1 * 360", 0), PT.life(2.4),
            PT.billboard([0.9, 0.9], PT.FLAT), PT.tint(1, 1, 1, f"math.clamp((1 - {PT.AGE}) * 2.5, 0, 1)")),
            material="particles_blend"),
        "vesperra_plate": PT.flyer("abm:vesperra_plate", sp(8), size=(0.62, 0.62), spin_rate=900),
    }
    return out


def client_particles() -> Dict[str, str]:
    """Short names used by animation timelines."""
    return {"shards": "abm:vesperra_shards", "molt": "abm:vesperra_molt", "dust": "abm:vesperra_dust",
            "drip": "abm:vesperra_drip", "glint": "abm:vesperra_glint"}


# --------------------------------------------------------------------------- sound

def _crack(seed, dur=0.35, density=60, bright=5200):
    """Glaze cracking: a spray of tiny resonant clicks, densest at the start."""
    def grain(i):
        r = S.rng("crk", seed, i)
        return S.click(0.012 + r.random() * 0.02, bright * (0.6 + r.random() * 0.9), (seed, i), 2.5) * (0.4 + r.random() * 0.6)
    g = S.grains(dur, density, grain, seed, jitter=0.8, accel=-0.6)
    return g * np.exp(-S.t_axis(dur) / (dur * 0.5))


def _shatter(seed, dur=0.9):
    body = S.resonate(S.noise(dur, seed), [(2600, 6, 1.0), (4100, 8, 0.8), (6900, 5, 0.6), (1300, 4, 0.5)])
    body *= S.env_exp(dur, 0.09, 0.001)
    tinkle = S.grains(dur, 34, lambda i: S.bell(2400 + S.rng("tk", seed, i).random() * 3200, 0.16, seed=(seed, i)) * 0.25,
                      seed, jitter=0.9) * np.linspace(1, 0, int(dur * S.SR)) ** 1.5
    return S.mixdown((body, 0, 1.0), (tinkle, 0.03, 0.8), (S.thud(110, 0.25, 0.5, seed), 0, 0.5))


def _scrape(seed, dur=0.6, f0=900, f1=2600):
    """Chitin stridulation: band-passed noise chopped by a fast ratchet."""
    n = S.sweep_bandpass(S.noise(dur, seed), f0, f1, 5)
    t = S.t_axis(dur)
    ratchet = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * (38 + 30 * t / dur) * t))
    return n * ratchet * S.env_adsr(dur, 0.05, 0.1, 0.8, 0.2)


def _chime(freq, dur=1.4, seed="chime"):
    """One porcelain chime: glassy, short, slightly sour (inharmonic)."""
    return S.bell(freq, dur, seed=seed, bright=0.8, partials=[(1, 1, 0.5), (2.76, 0.5, 0.3), (5.4, 0.3, 0.16), (8.9, 0.14, 0.08)])


def _whoosh(seed, dur=0.4, f0=400, f1=2400):
    return S.sweep_bandpass(S.noise(dur, seed, "pink"), f0, f1, 1.6) * np.sin(np.pi * S.t_axis(dur) / dur) ** 1.5


def _wet(seed, dur=0.5):
    n = S.lowpass(S.noise(dur, seed, "brown"), 900)
    t = S.t_axis(dur)
    blub = n * (0.5 + 0.5 * np.sin(2 * np.pi * (9 + 14 * t) * t)) * S.env_adsr(dur, 0.03, 0.1, 0.7, 0.25)
    return blub + 0.4 * S.grains(dur, 20, lambda i: S.click(0.02, 700 + 500 * (i % 3), (seed, i), 2) * 0.6, seed)


def sounds() -> Dict[str, dict]:
    """event id -> {"clips": {file stem: samples}, "volume", "min", "max"}"""
    def ev(clips, volume=1.0, lo=6.0, hi=48.0, pitch=(0.94, 1.06)):
        return {"clips": clips, "volume": volume, "min": lo, "max": hi, "pitch": pitch}

    out: Dict[str, dict] = {}
    out["step"] = ev({f"step{i}": S.mixdown((S.click(0.03, 1900 + i * 420, ("st", i), 4), 0, 1.0),
                                             (S.thud(150 - i * 14, 0.09, 0.3, ("st", i)), 0.002, 0.45))
                      for i in range(3)}, 0.5, 4, 28, (0.85, 1.2))
    out["idle"] = ev({f"idle{i}": S.reverb(S.mixdown((_crack(("id", i), 0.5, 22, 4200), 0.0, 0.5),
                                                     (_scrape(("id", i), 0.5, 500, 1100), 0.25, 0.25)), 0.8, 0.3, ("id", i))
                      for i in range(2)}, 0.45, 5, 32)
    out["scythe_wind"] = ev({"scythe_wind": S.mixdown((_scrape("sw", 1.1, 600, 3200), 0, 0.8), (_crack("sw", 1.0, 26), 0.1, 0.5))}, 0.9)
    out["scythe_swing"] = ev({"scythe_swing": S.mixdown((_whoosh("ss", 0.34, 500, 4200), 0, 1.0), (_crack("ss2", 0.2, 80), 0.16, 0.6),
                                                        (_chime(1720, 0.5, "ss"), 0.14, 0.25))}, 1.0)
    out["needle_plant"] = ev({"needle_plant": S.mixdown((S.thud(82, 0.4, 0.55, "np"), 0, 1.0), (S.click(0.03, 3400, "np", 3), 0, 0.7),
                                                        (_crack("np", 0.3, 40), 0.03, 0.4))}, 1.0)
    out["needle_stab"] = ev({"needle_stab": S.mixdown((_whoosh("ns", 0.14, 1800, 5200), 0, 0.8), (S.click(0.025, 4200, "ns", 5), 0.1, 1.0),
                                                      (S.thud(120, 0.14, 0.4, "ns"), 0.1, 0.5))}, 0.85)
    out["lane_erupt"] = ev({"lane_erupt": S.mixdown((_shatter("le", 0.6), 0, 0.9), (S.thud(64, 0.5, 0.6, "le"), 0, 0.9))}, 1.0, 8, 56)
    out["molt_wind"] = ev({"molt_wind": S.mixdown((_crack("mw", 1.4, 34, 3600)[::-1].copy(), 0, 0.9), (_wet("mw", 1.2), 0.2, 0.5),
                                                  (_scrape("mw", 1.3, 300, 900), 0.1, 0.35))}, 0.95)
    out["molt_burst"] = ev({"molt_burst": S.reverb(S.mixdown((_shatter("mb", 1.0), 0, 1.0), (_whoosh("mb", 0.4, 300, 3000), 0, 0.7),
                                                             (_wet("mb", 0.4), 0.02, 0.5)), 1.0, 0.22, "mb")}, 1.0, 8, 64)
    out["cocoon_spit"] = ev({"cocoon_spit": S.mixdown((_wet("cs", 0.5), 0, 1.0), (_whoosh("cs", 0.3, 900, 2600), 0.08, 0.5))}, 0.9)
    out["cocoon_weave"] = ev({"cocoon_weave": S.mixdown(*[(S.sine(1500 + 260 * (i % 4) + 40 * np.sin(np.linspace(0, 20, int(0.28 * S.SR))), 0.28)
                                                             * S.env_exp(0.28, 0.07), i * 0.26, 0.35) for i in range(8)],
                                                         (_scrape("cw", 2.2, 1400, 2600), 0, 0.25))}, 0.7)
    out["cocoon_snap"] = ev({"cocoon_snap": S.mixdown((S.sine(np.linspace(2600, 300, int(0.22 * S.SR)), 0.22) * S.env_exp(0.22, 0.05), 0, 0.9),
                                                      (S.click(0.03, 3800, "sn", 2), 0, 1.0), (_wet("sn", 0.35), 0.03, 0.6))}, 1.0)
    out["anchor_break"] = ev({"anchor_break": S.mixdown((_wet("ab", 0.4), 0, 1.0), (_crack("ab", 0.3, 50, 2600), 0, 0.7))}, 0.9, 4, 32)
    out["feint_fall"] = ev({"feint_fall": S.mixdown((_crack("ff", 0.5, 44), 0, 0.8), (S.thud(74, 0.5, 0.5, "ff"), 0.2, 0.9),
                                                    (_scrape("ff", 0.5, 1400, 500), 0.05, 0.4))}, 0.9)
    out["feint_cue"] = ev({"feint_cue": S.mixdown((_chime(2093, 0.9, "fc"), 0, 0.8), (_chime(2217, 0.9, "fc2"), 0.07, 0.7),
                                                  (_scrape("fc", 0.3, 2200, 3600), 0.02, 0.3))}, 1.0)
    out["thrust"] = ev({"thrust": S.mixdown((_whoosh("th", 0.42, 300, 3600), 0, 1.0), (_scrape("th", 0.3, 800, 3000), 0.02, 0.5),
                                            (S.thud(70, 0.5, 0.5, "th"), 0.36, 1.0), (_crack("th", 0.3, 60), 0.38, 0.6))}, 1.0, 8, 56)
    out["heirs_call"] = ev({"heirs_call": S.mixdown((_chime(880, 1.2, "hc"), 0, 0.6), (_chime(1175, 1.2, "hc2"), 0.18, 0.5),
                                                    (_scrape("hc", 0.9, 500, 1500), 0.1, 0.4))}, 0.9)
    out["heirs_detach"] = ev({"heirs_detach": S.mixdown((_shatter("hd", 0.5), 0, 0.8), (_wet("hd", 0.4), 0.05, 0.6),
                                                        (S.grains(0.6, 26, lambda i: S.click(0.02, 2600, ("hd", i), 5), "hd"), 0.2, 0.5))}, 0.95)
    out["heir_bite"] = ev({"heir_bite": S.mixdown((S.click(0.03, 3000, "hb", 4), 0, 1.0), (S.click(0.03, 2400, "hb2", 4), 0.06, 0.9),
                                                  (_scrape("hb", 0.2, 1500, 2800), 0, 0.4))}, 0.8, 3, 20)
    out["crown_raise"] = ev({"crown_raise": S.reverb(S.mixdown((_chime(659, 2.2, "cr"), 0, 0.9), (_chime(988, 2.0, "cr2"), 0.25, 0.7),
                                                               (_chime(1319, 1.8, "cr3"), 0.5, 0.55), (_crack("cr", 1.2, 14), 0.3, 0.3)),
                                                     1.6, 0.35, "cr")}, 1.0, 10, 64)
    out["fracture_mark"] = ev({f"fracture_mark{i}": S.mixdown((_crack(("fm", i), 0.5, 70, 4600), 0, 0.9),
                                                             (_chime(1568 + i * 196, 0.5, ("fm", i)), 0, 0.3))
                               for i in range(3)}, 0.9, 8, 56)
    out["fracture_erupt"] = ev({f"fracture_erupt{i}": S.reverb(S.mixdown((_shatter(("fe", i), 0.8), 0, 1.0),
                                                                         (S.thud(58 + i * 6, 0.6, 0.6, ("fe", i)), 0, 1.0)), 0.9, 0.2, ("fe", i))
                                for i in range(2)}, 1.0, 10, 64)
    out["armor_hit"] = ev({f"armor_hit{i}": S.mixdown((_chime(2500 + i * 330, 0.3, ("ah", i)), 0, 0.8), (S.click(0.02, 5200, ("ah", i), 4), 0, 0.8))
                           for i in range(3)}, 0.8, 4, 28, (0.9, 1.15))
    out["armor_break"] = ev({"armor_break": S.reverb(S.mixdown((_shatter("abk", 1.1), 0, 1.0), (_crack("abk", 0.7, 90), 0.05, 0.7),
                                                               (_wet("abk", 0.5), 0.2, 0.45)), 1.0, 0.25, "abk")}, 1.0, 8, 64)
    out["body_hit"] = ev({f"body_hit{i}": S.mixdown((S.thud(140 + i * 22, 0.16, 0.4, ("bh", i)), 0, 1.0), (_wet(("bh", i), 0.14), 0, 0.5))
                          for i in range(2)}, 0.7, 4, 24, (0.9, 1.1))
    out["stagger"] = ev({"stagger": S.mixdown((_shatter("sg", 0.5), 0, 0.6), (_scrape("sg", 0.8, 2400, 600), 0.05, 0.7),
                                              (S.thud(66, 0.6, 0.5, "sg"), 0.25, 0.9))}, 1.0)
    cry = S.osc(np.linspace(520, 1380, int(1.6 * S.SR)) * (1 + 0.03 * np.sin(np.linspace(0, 260, int(1.6 * S.SR)))), 1.6, "saw", 14)
    cry = S.resonate(cry, [(1200, 6, 1.0), (2600, 8, 0.8), (3900, 6, 0.5)]) * S.env_adsr(1.6, 0.2, 0.2, 0.9, 0.5)
    out["transition_crack"] = ev({"transition_crack": S.reverb(S.mixdown((_crack("tc", 2.4, 46, 3900)[::-1].copy(), 0, 1.0),
                                                                         (_scrape("tc", 2.2, 300, 1200), 0.1, 0.4)), 1.2, 0.25, "tc")}, 1.0, 12, 72)
    out["transition_split"] = ev({"transition_split": S.reverb(S.mixdown((_shatter("ts", 1.4), 0, 1.0), (_wet("ts", 1.2), 0.1, 0.8),
                                                                         (S.thud(48, 0.9, 0.6, "ts"), 0, 1.0)), 1.6, 0.3, "ts")}, 1.0, 12, 72)
    out["transition_cry"] = ev({"transition_cry": S.reverb(S.mixdown((cry, 0, 0.9), (_scrape("tcy", 1.5, 1800, 4200), 0.05, 0.5)), 1.8, 0.35, "tcy")},
                               1.0, 14, 80)
    out["intro_rise"] = ev({"intro_rise": S.reverb(S.mixdown((_crack("ir", 2.8, 20, 3400), 0, 0.8), (_scrape("ir", 2.6, 250, 900), 0.2, 0.45),
                                                             (_chime(523, 2.4, "ir"), 1.4, 0.4)), 1.6, 0.35, "ir")}, 0.95, 12, 72)
    low_cry = S.resonate(S.osc(np.linspace(900, 260, int(1.8 * S.SR)), 1.8, "saw", 16), [(700, 5, 1.0), (1900, 7, 0.6)]) * S.env_adsr(1.8, 0.05, 0.3, 0.7, 0.9)
    out["death_cry"] = ev({"death_cry": S.reverb(S.mixdown((low_cry, 0, 0.9), (_crack("dc", 1.4, 50), 0.1, 0.6)), 1.8, 0.35, "dc")}, 1.0, 14, 80)
    out["death_fail"] = ev({"death_fail": S.reverb(S.mixdown((_wet("df", 1.0), 0, 0.9), (_crack("df", 1.0, 30, 2800), 0.1, 0.7),
                                                             (_chime(415, 1.6, "df"), 0.3, 0.4)), 1.4, 0.3, "df")}, 1.0, 12, 72)
    out["death_fall"] = ev({"death_fall": S.reverb(S.mixdown((S.thud(44, 1.0, 0.6, "dfl"), 0, 1.0), (_shatter("dfl", 1.2), 0.05, 0.8),
                                                             (_scrape("dfl", 0.9, 1200, 300), 0.2, 0.4)), 1.6, 0.3, "dfl")}, 1.0, 12, 72)
    out["trophy"] = ev({"trophy": S.reverb(S.mixdown((_chime(659, 1.8, "tr"), 0, 0.9), (_chime(831, 1.6, "tr2"), 0.3, 0.6)), 1.4, 0.4, "tr")}, 0.8, 4, 16)
    return out
