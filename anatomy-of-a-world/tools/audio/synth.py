"""Procedural sound design + music for THE ANATOMY OF A WORLD (Boss 001).

Everything is synthesised with numpy/scipy (no samples), then encoded to OGG
Vorbis with ffmpeg. SFX are mono (Bedrock positions mono sounds in 3D);
music is stereo.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from scipy import signal

SR = 44100
RNG = np.random.default_rng(1001)


# ----------------------------------------------------------------------------- primitives
def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def noise(dur: float, color: str = "white", seed: int | None = None) -> np.ndarray:
    r = np.random.default_rng(seed) if seed is not None else RNG
    n = r.standard_normal(int(dur * SR))
    if color == "brown":
        n = np.cumsum(n)
        n = signal.lfilter([1, -1], [1, -0.995], n)
    elif color == "pink":
        b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
        n = signal.lfilter(b, a, n)
    return n / (np.max(np.abs(n)) + 1e-9)


def lp(x, f, order=4):
    b, a = signal.butter(order, min(f / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x)


def hp(x, f, order=2):
    b, a = signal.butter(order, max(f / (SR / 2), 1e-4), "high")
    return signal.lfilter(b, a, x)


def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [max(f1 / (SR / 2), 1e-4), min(f2 / (SR / 2), 0.99)], "band")
    return signal.lfilter(b, a, x)


def sweep_bp(x, f_start, f_end, q=4.0, steps=64):
    """Time-varying band-pass by crossfading short filtered blocks."""
    out = np.zeros_like(x)
    n = len(x)
    edges = np.linspace(0, n, steps + 1).astype(int)
    for i in range(steps):
        a, b = edges[i], edges[i + 1]
        fc = f_start * (f_end / f_start) ** (i / max(1, steps - 1))
        bw = fc / q
        seg = bp(x[max(0, a - 2048):b], max(20, fc - bw), fc + bw)
        out[a:b] = seg[-(b - a):]
    return out


def env_adsr(n, a, d, s, r, sustain_level=0.7):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    s_len = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, max(1, a)), np.linspace(1, sustain_level, max(1, d)), np.full(s_len, sustain_level), np.linspace(sustain_level, 0, max(1, r))])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def env_exp(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def sine_sweep(dur, f0, f1, curve="exp"):
    t = t_axis(dur)
    if curve == "exp":
        f = f0 * (f1 / f0) ** (t / dur)
    else:
        f = f0 + (f1 - f0) * t / dur
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)


def kick(dur=1.2, f0=80, f1=28, decay=0.35):
    x = sine_sweep(dur, f0, f1) * env_exp(int(dur * SR), decay)
    click = hp(noise(0.02), 2000) * 0.3
    x[: len(click)] += click
    return x


def impulses(dur, rate, decay=0.004, seed=0, band=(400, 4000)):
    """Sparse crackle: random clicks filtered to a band."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = np.zeros(n)
    k = int(dur * rate)
    pos = r.integers(0, n, k)
    amp = r.random(k) ** 2
    x[pos] = amp * r.choice([-1, 1], k)
    ker = np.exp(-np.arange(int(decay * SR * 6)) / (decay * SR))
    x = np.convolve(x, ker)[:n]
    return bp(x, *band)


def reverb(x, seconds=2.2, mix=0.3, damp=3000, seed=5):
    n = int(seconds * SR)
    r = np.random.default_rng(seed)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / (seconds * SR / 6.5))
    ir = lp(ir, damp, 2)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    wet = signal.fftconvolve(x, ir)
    total = len(x) + n
    wet = np.pad(wet, (0, max(0, total - len(wet))))[:total]
    dry = np.pad(x, (0, n))[:total]
    return dry * (1 - mix) + wet * mix * 1.6


def bell(dur, f, partials=((1, 1.0), (2.76, 0.5), (5.4, 0.28), (8.93, 0.12)), decay=1.2):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for ratio, amp in partials:
        x += amp * np.sin(2 * np.pi * f * ratio * t + RNG.random() * 6) * np.exp(-t / (decay / ratio ** 0.6))
    return x


def saw(t, f):
    return 2 * ((t * f) % 1.0) - 1


def pad(dur, freqs, detune=0.004, cutoff=900, lfo=0.08):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for f in freqs:
        for d in (-detune, 0, detune):
            x += saw(t, f * (1 + d)) * 0.33
    x = lp(x, cutoff, 2)
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * lfo * t)
    return x / (len(freqs) + 1e-9)


def formant_choir(dur, freqs, vowel="ah"):
    t = t_axis(dur)
    src = np.zeros_like(t)
    for f in freqs:
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t + RNG.random() * 6)
        src += saw(t, f * vib)
    forms = {"ah": [(700, 110), (1220, 120), (2600, 160)], "oo": [(300, 80), (870, 100), (2240, 140)]}[vowel]
    out = np.zeros_like(t)
    for fc, bw in forms:
        out += bp(src, fc - bw, fc + bw, 2)
    return out / (len(freqs) + 1e-9)


def pluck(dur, f, decay=0.996):
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = RNG.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = decay * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def fade_edges(x, fin=0.005, fout=0.05):
    n = len(x)
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def at(x, offset, total):
    out = np.zeros(int(total * SR))
    o = int(offset * SR)
    seg = x[: max(0, len(out) - o)]
    out[o:o + len(seg)] += seg
    return out


# ----------------------------------------------------------------------------- sound effects
def sfx_groan():
    d = 3.8
    t = t_axis(d)
    f = 46 * (0.72 + 0.28 * np.exp(-t / 1.6)) * (1 + 0.04 * np.sin(2 * np.pi * 0.7 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.5 * np.sin(2 * ph + 0.3) + 0.25 * np.sin(3 * ph + 1.1) + 0.15 * np.sign(np.sin(ph)) * 0.3
    tone = lp(tone, 420)
    rub = lp(noise(d, "brown", 3), 260) * 0.8
    creak = impulses(d, 90, 0.003, 4, (250, 1400)) * 2.5
    e = env_adsr(len(t), 0.35, 0.8, 0.85, 1.6)
    return reverb(normalize((tone * 0.9 + rub + creak * np.linspace(0.3, 1, len(t))) * e), 2.8, 0.35)


def sfx_rumble():
    d = 4.2
    t = t_axis(d)
    x = lp(noise(d, "brown", 7), 140) * (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t) * np.sin(2 * np.pi * 0.9 * t))
    x += lp(noise(d, "white", 8), 900) * 0.08
    thumps = mix(*[at(kick(0.8, 60, 30, 0.2) * 0.6, o, d) for o in (0.3, 1.4, 2.3, 3.1)])
    return reverb(normalize((x + thumps) * env_adsr(len(t), 0.4, 0.5, 0.9, 1.4)), 2.5, 0.25)


def sfx_quake():
    d = 2.8
    k = kick(1.6, 75, 26, 0.55)
    burst = lp(noise(d, "white", 9), 1600) * env_exp(int(d * SR), 0.18) * 0.9
    debris = impulses(d, 220, 0.004, 10, (500, 5000)) * np.linspace(1, 0, int(d * SR)) * 2.2
    return reverb(normalize(mix(k * 1.4, burst, debris)), 2.0, 0.3)


def sfx_crack():
    d = 1.4
    n = int(d * SR)
    snap = hp(noise(0.03, "white", 11), 1500) * 2
    body = np.sin(2 * np.pi * 190 * t_axis(d)) * env_exp(n, 0.08) * 0.6
    crackle = impulses(d, 400, 0.0025, 12, (800, 7000)) * env_exp(n, 0.35) * 3
    return reverb(normalize(mix(snap, body, crackle)), 1.4, 0.25)


def sfx_grind():
    d = 3.2
    t = t_axis(d)
    base = bp(noise(d, "pink", 13), 120, 900)
    fr = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * (7 + 3 * np.sin(2 * np.pi * 0.4 * t)) * t))
    grit = impulses(d, 600, 0.002, 14, (300, 2500)) * 1.5
    low = lp(noise(d, "brown", 15), 90) * 0.8
    return reverb(normalize((base * fr + grit + low) * env_adsr(len(t), 0.25, 0.4, 0.85, 0.9)), 1.8, 0.3)


def sfx_wave():
    d = 1.8
    n = int(d * SR)
    wh = sweep_bp(noise(d, "white", 16), 180, 1100, 3.0) * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    th = at(kick(1.0, 55, 30, 0.25), 0.55, d)
    return reverb(normalize(mix(wh * 1.2, th * 0.9)), 1.6, 0.3)


def sfx_resonance():
    d = 3.4
    t = t_axis(d)
    chord = [146.83, 220.0, 293.66, 349.23, 440.0]
    x = np.zeros_like(t)
    for i, f in enumerate(chord):
        x += np.sin(2 * np.pi * f * t) * (0.7 / (i + 1) ** 0.4) + np.sin(2 * np.pi * f * 1.003 * t) * 0.3
    shimmer = sum(np.sin(2 * np.pi * f * t + RNG.random() * 6) for f in (1760, 2093, 2637)) * 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * 6 * t))
    e = env_adsr(len(t), 0.9, 0.6, 0.8, 1.4)
    return reverb(normalize((x + shimmer) * e), 3.0, 0.45, 6000)


def sfx_chime():
    d = 2.2
    x = bell(d, 880, decay=0.9) + bell(d, 1318.5, decay=0.7) * 0.5
    return reverb(normalize(x), 2.4, 0.4, 7000)


def sfx_heartbeat():
    d = 1.5
    lub = kick(0.6, 62, 34, 0.12)
    dub = kick(0.6, 55, 30, 0.1) * 0.75
    body = lp(noise(0.3, "brown", 17), 200) * env_exp(int(0.3 * SR), 0.06) * 0.6
    return reverb(normalize(mix(lub, body, at(dub, 0.26, d), at(body, 0.26, d))), 1.2, 0.2, 2000)


def sfx_heart_open():
    d = 2.0
    t = t_axis(d)
    scrape = bp(noise(d, "pink", 18), 300, 1300) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 9 * t))) * env_adsr(len(t), 0.05, 0.5, 0.6, 0.8)
    shimmer = sum(np.sin(2 * np.pi * f * t) for f in (987.8, 1318.5, 1975.5)) * np.linspace(0, 1, len(t)) ** 2 * 0.25
    return reverb(normalize(mix(scrape, shimmer, at(kick(0.5, 90, 50, 0.1) * 0.5, 0.0, d))), 2.0, 0.35, 6500)


def sfx_heart_close():
    d = 1.5
    t = t_axis(d)
    shimmer = sum(np.sin(2 * np.pi * f * t) for f in (1975.5, 1318.5)) * np.linspace(1, 0, len(t)) ** 2 * 0.2
    clunk = at(mix(kick(0.8, 110, 40, 0.12), lp(noise(0.3, "white", 19), 1200) * env_exp(int(0.3 * SR), 0.05) * 0.6), 0.35, d)
    return reverb(normalize(shimmer + clunk), 1.6, 0.3)


def sfx_shatter():
    d = 3.0
    n = int(d * SR)
    x = np.zeros(n)
    r = np.random.default_rng(20)
    for _ in range(70):
        f = r.uniform(1800, 8500)
        o = r.uniform(0, 0.35)
        x += at(np.sin(2 * np.pi * f * t_axis(0.5)) * env_exp(int(0.5 * SR), r.uniform(0.02, 0.15)) * r.uniform(0.2, 1), o, d)
    burst = hp(noise(0.4, "white", 21), 2500) * env_exp(int(0.4 * SR), 0.06)
    boom = kick(2.0, 70, 28, 0.6) * 0.9
    return reverb(normalize(mix(x * 0.8, burst, boom)), 2.6, 0.4, 8000)


def sfx_unfold():
    d = 7.0
    t = t_axis(d)
    rum = lp(noise(d, "brown", 22), 160) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.3 * t))
    tear = sweep_bp(noise(d, "pink", 23), 90, 700, 2.5) * 1.4
    groan_f = 38 * (1 + 0.8 * (t / d))
    ph = 2 * np.pi * np.cumsum(groan_f) / SR
    groan = lp(np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph), 500) * 0.8
    crack = impulses(d, 300, 0.003, 24, (400, 6000)) * 2.2
    e = env_adsr(len(t), 1.2, 1.0, 0.95, 2.0)
    return reverb(normalize((rum + tear + groan + crack) * e), 3.2, 0.35)


def sfx_step():
    d = 1.4
    k = kick(1.0, 58, 27, 0.22)
    dirt = lp(noise(0.6, "white", 25), 700) * env_exp(int(0.6 * SR), 0.09) * 0.5
    return reverb(normalize(mix(k * 1.3, dirt)), 1.6, 0.25, 2500)


def sfx_contract():
    d = 3.2
    t = t_axis(d)
    src = noise(d, "pink", 26)
    wet = sweep_bp(src, 150, 600, 2.0) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 11 * t)))
    creak = impulses(d, 120, 0.004, 27, (200, 1200)) * 2
    low = lp(noise(d, "brown", 28), 110)
    return reverb(normalize((wet + creak + low * 0.7) * env_adsr(len(t), 0.4, 0.6, 0.85, 1.0)), 2.0, 0.3)


def sfx_whoosh():
    d = 1.3
    n = int(d * SR)
    x = sweep_bp(noise(d, "white", 29), 300, 1600, 3.5) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return normalize(x)


def sfx_node_hurt():
    d = 0.8
    x = mix(bell(d, 1567.98, decay=0.25), hp(noise(0.05, "white", 30), 2000) * 0.6)
    return reverb(normalize(x), 0.9, 0.25, 7000)


def sfx_heart_hurt():
    d = 1.1
    x = mix(bell(d, 392.0, ((1, 1.0), (2.4, 0.6), (4.1, 0.3), (6.7, 0.15)), decay=0.5), kick(0.6, 70, 40, 0.1) * 0.8)
    return reverb(normalize(x), 1.3, 0.3, 5000)


def sfx_warn():
    d = 1.8
    t = t_axis(d)
    x = sum(lp(saw(t, f), 700, 2) for f in (73.42, 77.78, 110.0)) / 3
    x *= env_adsr(len(t), 0.25, 0.3, 0.8, 0.7)
    return reverb(normalize(x), 1.6, 0.3)


def sfx_deflect():
    d = 0.6
    x = mix(bell(d, 2349.3, ((1, 1.0), (2.1, 0.7), (3.7, 0.4)), decay=0.12), hp(noise(0.03, "white", 31), 3000))
    return normalize(x)


def sfx_vent():
    d = 1.5
    n = int(d * SR)
    x = hp(noise(d, "white", 32), 1800) * env_adsr(n, 0.02, 0.3, 0.5, 0.9) + lp(noise(d, "brown", 33), 200) * env_exp(n, 0.3) * 0.5
    return normalize(x)


# Phase 3 (The Last Migration / The Heart Unbound)
def sfx_root_tear():
    """A root ripping up through the disk: fibrous tearing over a deep strain."""
    d = 3.0
    t = t_axis(d)
    n = len(t)
    fibres = impulses(d, 700, 0.0025, 41, (300, 3500)) * (0.4 + 0.6 * np.sin(np.linspace(0, np.pi, n)))
    tear = sweep_bp(noise(d, "pink", 42), 140, 900, 3.0) * 1.3
    strain_f = 52 * (1 + 0.35 * t / d)
    ph = 2 * np.pi * np.cumsum(strain_f) / SR
    strain = lp(np.sin(ph) + 0.4 * np.sin(2 * ph + 0.5), 380) * 0.7
    e = env_adsr(n, 0.15, 0.5, 0.85, 1.0)
    return reverb(normalize((fibres * 1.8 + tear + strain) * e), 2.2, 0.3)


def sfx_sinew_snap():
    """The sinew knot bursting: a hard snap, a twanging release, debris."""
    d = 2.2
    n = int(d * SR)
    snap = hp(noise(0.05, "white", 43), 1200) * 3
    twang_t = t_axis(1.2)
    tw_f = 140 * np.exp(-twang_t / 0.5) + 60
    twang = np.sin(2 * np.pi * np.cumsum(tw_f) / SR) * env_exp(len(twang_t), 0.35) * 0.9
    boom = kick(1.6, 70, 30, 0.4)
    debris = impulses(d, 260, 0.004, 44, (400, 5000)) * np.linspace(1, 0, n) * 2
    return reverb(normalize(mix(snap, at(twang, 0.02, d), boom * 0.9, debris)), 2.0, 0.3)


def sfx_beam_charge():
    """Molten mineral gathering in the heart's veins: a rising whine with crackle."""
    d = 2.0
    t = t_axis(d)
    f = 180 * (1 + 3.5 * (t / d) ** 2)
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + 0.25 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    sizzle = hp(noise(d, "white", 45), 2500) * (t / d) * 0.5
    crackle = impulses(d, 350, 0.002, 46, (1500, 7000)) * (t / d) * 2
    return reverb(normalize((whine + sizzle + crackle) * env_adsr(len(t), 0.4, 0.2, 0.9, 0.1)), 1.2, 0.2)


def sfx_beam_fire():
    """A sweeping beam of molten mineral: roaring, hissing, with a low body."""
    d = 2.6
    t = t_axis(d)
    roar = bp(noise(d, "pink", 47), 120, 1600) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t))
    hiss = hp(noise(d, "white", 48), 3000) * 0.35
    body = lp(noise(d, "brown", 49), 120) * 0.9
    return reverb(normalize((roar + hiss + body) * env_adsr(len(t), 0.05, 0.3, 0.9, 0.7)), 1.6, 0.25)


def sfx_heart_rise():
    """The Lithic Heart tearing free and rising: a deep swell with a crystal choir."""
    d = 5.0
    t = t_axis(d)
    swell = pad(d, [note("D2"), note("A2"), note("D3"), note("F3")], 0.004, 900, 0.2) * env_adsr(len(t), 1.8, 1.0, 0.9, 1.6)
    choir = formant_choir(d, [note("D4"), note("A4"), note("F5")], "ah") * env_adsr(len(t), 2.2, 0.8, 0.8, 1.4) * 0.6
    rum = lp(noise(d, "brown", 50), 140) * env_adsr(len(t), 0.2, 1.5, 0.6, 2.0)
    shards = impulses(d, 80, 0.01, 51, (2500, 9000)) * 1.2
    return reverb(normalize(mix(swell, choir, rum, shards)), 3.0, 0.4)


def sfx_island_break():
    """The disk breaking into islands: cracking, a heavy drop, debris falling away."""
    d = 4.0
    n = int(d * SR)
    cracks = mix(*[at(sfx_crack() * 0.6, o, d) for o in (0.0, 0.35, 0.9, 1.4)])
    drop = at(kick(2.2, 60, 24, 0.7) * 1.2, 0.2, d)
    fall = sweep_bp(noise(d, "pink", 52), 900, 120, 2.0) * np.linspace(0.2, 1, n) * np.linspace(1, 0, n) * 1.4
    return reverb(normalize(mix(cracks, drop, fall)), 2.8, 0.35)


SFX = {
    "groan": sfx_groan, "rumble": sfx_rumble, "quake": sfx_quake, "crack": sfx_crack, "grind": sfx_grind, "wave": sfx_wave,
    "resonance": sfx_resonance, "chime": sfx_chime, "heartbeat": sfx_heartbeat, "heart_open": sfx_heart_open,
    "heart_close": sfx_heart_close, "shatter": sfx_shatter, "unfold": sfx_unfold, "step": sfx_step, "contract": sfx_contract,
    "whoosh": sfx_whoosh, "node_hurt": sfx_node_hurt, "heart_hurt": sfx_heart_hurt, "warn": sfx_warn, "deflect": sfx_deflect,
    "vent": sfx_vent,
    "root_tear": sfx_root_tear, "sinew_snap": sfx_sinew_snap, "beam_charge": sfx_beam_charge, "beam_fire": sfx_beam_fire,
    "heart_rise": sfx_heart_rise, "island_break": sfx_island_break,
}


# ----------------------------------------------------------------------------- music
def note(n: str) -> float:
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    pitch, octave = n[:-1], int(n[-1])
    return 440.0 * 2 ** ((names[pitch] + 12 * (octave + 1) - 69) / 12)


def stereo(x, pan=0.0):
    l = x * np.sqrt(0.5 * (1 - pan))
    r = x * np.sqrt(0.5 * (1 + pan))
    return np.stack([l, r], axis=1)


def place(buf, x, offset):
    o = int(offset * SR)
    if o >= len(buf):
        return
    seg = x[: len(buf) - o]
    buf[o:o + len(seg)] += seg


def taiko(f=62, decay=0.4, seed=0):
    return mix(kick(1.4, f * 1.6, f * 0.7, decay), lp(noise(0.25, "white", seed), 900) * env_exp(int(0.25 * SR), 0.04) * 0.5)


def music_phase1(bars=24, bpm=58):
    beat = 60 / bpm
    bar = beat * 4
    dur = bars * bar
    buf = np.zeros((int(dur * SR), 2))
    t = t_axis(dur)
    # drones: D2 + A2, slowly breathing filter
    drone = pad(dur, [note("D2"), note("A2"), note("D3")], 0.003, 500, 0.05)
    drone *= 0.7 + 0.3 * np.sin(2 * np.pi * t / (bar * 4))
    buf += stereo(drone * 0.55, -0.15) + stereo(np.roll(drone, 2000) * 0.5, 0.15)
    # chord pads every 4 bars: Dm - Bb - F - C (modal, vast)
    prog = [["D3", "F3", "A3"], ["A#2", "D3", "F3"], ["F2", "A2", "C3"], ["C3", "E3", "G3"]]
    for i in range(bars // 4):
        ch = prog[i % 4]
        p = pad(bar * 4 + 2, [note(n) for n in ch], 0.005, 1200, 0.1) * env_adsr(int((bar * 4 + 2) * SR), 1.5, 1.0, 0.8, 2.0)
        place(buf, stereo(p * 0.35, -0.3 + 0.6 * (i % 2)), i * bar * 4)
    # migration footsteps: slow taiko on beats 1 and 3, with occasional double
    for b in range(bars):
        place(buf, stereo(taiko(55, 0.5, b) * 0.6, 0.0), b * bar)
        if b % 2 == 1:
            place(buf, stereo(taiko(48, 0.6, b + 100) * 0.5, 0.0), b * bar + beat * 2)
        if b % 8 == 7:
            place(buf, stereo(taiko(70, 0.25, b + 200) * 0.35, 0.2), b * bar + beat * 3.5)
    # crystal motif (D dorian pentatonic) every 4 bars, answering phrase
    motif = ["A4", "D5", "E5", "A5", "G5", "E5", "D5", "C5"]
    for i in range(2, bars, 4):
        for k, n in enumerate(motif):
            bl = bell(2.5, note(n), decay=1.4) * 0.16
            place(buf, stereo(bl, -0.5 + k * 0.14), i * bar + k * beat * 0.75)
    # wind
    wind = sweep_bp(noise(dur, "pink", 40), 300, 1400, 1.5) * 0.08
    wind *= 0.6 + 0.4 * np.sin(2 * np.pi * t / (bar * 3))
    buf += stereo(wind, 0.4) + stereo(np.roll(wind, 30000), -0.4)
    return buf


def music_phase2(bars=32, bpm=96):
    beat = 60 / bpm
    bar = beat * 4
    dur = bars * bar
    buf = np.zeros((int(dur * SR), 2))
    # ostinato bass in D minor
    bass_pat = ["D2", "D2", "F2", "D2", "A#1", "A#1", "C2", "A1"]
    for b in range(bars):
        for k in range(8):
            n = bass_pat[(k + (b % 4) * 0) % 8]
            x = lp(saw(t_axis(beat * 0.5), note(n)) + 0.5 * saw(t_axis(beat * 0.5), note(n) * 1.005), 520) * env_adsr(int(beat * 0.5 * SR), 0.005, 0.1, 0.6, 0.12) * 0.32
            place(buf, stereo(x, 0.0), b * bar + k * beat * 0.5)
    # drums: heartbeat-driven taiko pattern
    for b in range(bars):
        for k, (pos, f, amp) in enumerate([(0, 58, 0.9), (0.75, 70, 0.4), (1.0, 58, 0.6), (2.0, 52, 0.85), (2.5, 80, 0.35), (3.0, 58, 0.6), (3.5, 90, 0.3 if b % 2 else 0.5)]):
            place(buf, stereo(taiko(f, 0.3, b * 10 + k) * amp, (k % 3 - 1) * 0.25), b * bar + pos * beat)
        if b % 4 == 3:
            for r in range(4):
                place(buf, stereo(taiko(95, 0.12, b * 31 + r) * 0.4, 0.3 - r * 0.2), b * bar + (3 + r * 0.25) * beat)
    # choir chords (rising tension): Dm - Bb - Gm - A
    prog = [["D3", "A3", "F4"], ["A#2", "F3", "D4"], ["G2", "D3", "A#3"], ["A2", "E3", "C#4"]]
    for i in range(bars // 2):
        ch = prog[i % 4]
        c = formant_choir(bar * 2 + 0.5, [note(n) for n in ch], "ah" if i % 2 == 0 else "oo") * env_adsr(int((bar * 2 + 0.5) * SR), 0.6, 0.6, 0.8, 0.8) * 0.5
        place(buf, stereo(c, -0.25 if i % 2 else 0.25), i * bar * 2)
    # high crystal stabs on the off-bars
    for b in range(2, bars, 2):
        for k, n in enumerate(["D6", "A5", "F5"]):
            place(buf, stereo(bell(1.4, note(n), decay=0.6) * 0.1, 0.5 - k * 0.5), b * bar + beat * (1.5 + k * 0.25))
    return buf


def music_phase3(bars=32, bpm=112):
    """The Last Migration / The Heart Unbound: a driving march in D minor, footfalls on every beat."""
    beat = 60 / bpm
    bar = beat * 4
    dur = bars * bar
    buf = np.zeros((int(dur * SR), 2))
    # pulsing low ostinato: the gait
    bass_pat = ["D2", "D2", "D2", "F2", "A#1", "A#1", "C2", "C2"]
    for b in range(bars):
        for k in range(8):
            n = bass_pat[k] if b % 8 < 4 else ["G1", "G1", "A#1", "G1", "A1", "A1", "C#2", "A1"][k]
            x = lp(saw(t_axis(beat * 0.5), note(n)) + 0.6 * saw(t_axis(beat * 0.5), note(n) * 1.004), 600) * env_adsr(int(beat * 0.5 * SR), 0.004, 0.08, 0.6, 0.1) * 0.33
            place(buf, stereo(x, 0.0), b * bar + k * beat * 0.5)
    # march: heavy footfalls on every beat, accents on 1 and 3, rolls into each 4th bar
    for b in range(bars):
        for k in range(4):
            amp = 0.95 if k in (0, 2) else 0.55
            place(buf, stereo(taiko(50 if k in (0, 2) else 66, 0.35, b * 7 + k) * amp, (k - 1.5) * 0.12), b * bar + k * beat)
        if b % 4 == 3:
            for r in range(6):
                place(buf, stereo(taiko(88, 0.1, b * 13 + r) * 0.38, 0.4 - r * 0.15), b * bar + (2.5 + r * 0.25) * beat)
    # choir: Dm - Gm - Bb - A (darker, urgent)
    prog = [["D3", "A3", "F4"], ["G2", "D3", "A#3"], ["A#2", "F3", "D4"], ["A2", "E3", "C#4"]]
    for i in range(bars // 2):
        ch = prog[i % 4]
        c = formant_choir(bar * 2 + 0.4, [note(x) for x in ch], "ah" if i % 2 else "oo") * env_adsr(int((bar * 2 + 0.4) * SR), 0.4, 0.5, 0.85, 0.6) * 0.48
        place(buf, stereo(c, 0.25 if i % 2 else -0.25), i * bar * 2)
    # molten crystal: falling bell figure every 2 bars
    for b in range(1, bars, 2):
        for k, n in enumerate(["F6", "D6", "A5", "F5", "D5"]):
            place(buf, stereo(bell(1.2, note(n), decay=0.5) * 0.09, 0.6 - k * 0.3), b * bar + beat * (2 + k * 0.33))
    return buf


def music_victory():
    dur = 22.0
    buf = np.zeros((int(dur * SR), 2))
    chords = [(["D3", "F#3", "A3", "D4"], 0), (["G2", "B3", "D4", "G4"], 5.5), (["A2", "C#4", "E4", "A4"], 11), (["D3", "F#4", "A4", "D5"], 15)]
    for ch, o in chords:
        ln = 7.5 if o < 15 else 7.0
        p = pad(ln, [note(n) for n in ch], 0.004, 1600, 0.15) * env_adsr(int(ln * SR), 1.2, 1.0, 0.8, 2.5) * 0.6
        place(buf, stereo(p, 0.0), o)
    for k, n in enumerate(["D5", "F#5", "A5", "D6", "A5", "F#5", "A5", "D6", "E6", "F#6"]):
        place(buf, stereo(bell(3.0, note(n), decay=1.6) * 0.18, -0.4 + 0.08 * k), 2 + k * 1.3)
    place(buf, stereo(taiko(50, 0.8, 1) * 0.7, 0), 0.0)
    place(buf, stereo(taiko(50, 0.8, 2) * 0.7, 0), 15.0)
    return buf


# ----------------------------------------------------------------------------- encoding
def write_ogg(path: str, data: np.ndarray, quality: int = 4) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if data.ndim == 1:
        data = fade_edges(normalize(data.copy()))
        ch = 1
    else:
        data = data / (np.max(np.abs(data)) + 1e-9) * 0.9
        ch = 2
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "x.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(ch)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality), path], check=True)


def main(out_rp: str, only_sfx: bool = False) -> None:
    base = os.path.join(out_rp, "sounds", "anatomy", "mm")
    for name, fn in SFX.items():
        write_ogg(os.path.join(base, f"{name}.ogg"), fn(), 4)
    print(f"sfx: {len(SFX)} sounds")
    if not only_sfx:
        mb = os.path.join(out_rp, "sounds", "anatomy", "music")
        write_ogg(os.path.join(mb, "mm_phase1.ogg"), music_phase1(), 3)
        write_ogg(os.path.join(mb, "mm_phase2.ogg"), music_phase2(), 3)
        write_ogg(os.path.join(mb, "mm_victory.ogg"), music_victory(), 3)
        write_ogg(os.path.join(mb, "mm_phase3.ogg"), music_phase3(), 3)
        print("music: 4 tracks")


if __name__ == "__main__":
    main(sys.argv[1], "--sfx-only" in sys.argv)
