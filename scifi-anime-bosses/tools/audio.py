"""
audio.py - original procedural sound design for VESPER-0 (numpy synthesis -> OGG Vorbis).

Every sound is synthesised from scratch: band-limited oscillators, formant-filtered
"choir" voices, inharmonic bells, filtered noise, FM metal, STFT filter sweeps and a
synthetic cathedral reverb.  Encoded with ffmpeg/libvorbis (mono, 44.1 kHz).
"""
from __future__ import annotations

import math
import os
import subprocess
import wave
from typing import Callable, Dict, List, Tuple

import numpy as np

SR = 44100
RNG = np.random.default_rng(1234)


# ----------------------------------------------------------------------------- primitives

def tvec(dur):
    return np.arange(int(dur * SR), dtype=np.float64) / SR


def phase_from_freq(freq):
    return 2 * np.pi * np.cumsum(freq) / SR


def sine(freq, dur=None, phase0=0.0):
    if np.isscalar(freq):
        return np.sin(2 * np.pi * freq * tvec(dur) + phase0)
    return np.sin(phase_from_freq(freq) + phase0)


def saw(freq, dur=None, harmonics=None):
    """Band-limited sawtooth via additive synthesis (freq may be an array)."""
    f = np.full(int(dur * SR), float(freq)) if np.isscalar(freq) else np.asarray(freq, np.float64)
    ph = phase_from_freq(f)
    fmax = float(np.max(f))
    n = harmonics or max(1, min(60, int((SR / 2 - 200) / max(fmax, 1))))
    out = np.zeros_like(ph)
    for k in range(1, n + 1):
        out += np.sin(k * ph) / k
    return out * (2 / np.pi)


def square(freq, dur=None):
    f = np.full(int(dur * SR), float(freq)) if np.isscalar(freq) else np.asarray(freq, np.float64)
    ph = phase_from_freq(f)
    n = max(1, min(40, int((SR / 2 - 200) / max(float(np.max(f)), 1))))
    out = np.zeros_like(ph)
    for k in range(1, n + 1, 2):
        out += np.sin(k * ph) / k
    return out * (4 / np.pi)


def noise(dur):
    return RNG.standard_normal(int(dur * SR))


def env_adsr(n, a, d, s, r, peak=1.0):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.full(n, s, np.float64)
    e[t < a] = (t[t < a] / max(a, 1e-6)) * peak
    m = (t >= a) & (t < a + d)
    e[m] = peak + (s - peak) * ((t[m] - a) / max(d, 1e-6))
    rel = t > dur - r
    e[rel] *= np.clip((dur - t[rel]) / max(r, 1e-6), 0, 1)
    return e


def env_exp(n, decay, attack=0.005):
    t = np.arange(n) / SR
    e = np.exp(-t / max(decay, 1e-6))
    a = t < attack
    e[a] *= t[a] / attack
    return e


def curve(n, points: List[Tuple[float, float]]):
    """Piecewise-linear curve over normalised time [0,1]."""
    xs = np.linspace(0, 1, n)
    px, py = zip(*points)
    return np.interp(xs, px, py)


def fade(x, fi=0.004, fo=0.02):
    n = len(x)
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def at(x, t, total):
    """Place signal x at time t inside a buffer of `total` seconds."""
    out = np.zeros(int(total * SR))
    i = int(t * SR)
    j = min(len(out), i + len(x))
    if i < len(out):
        out[i:j] += x[:j - i]
    return out


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def soft_clip(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


# ----------------------------------------------------------------------------- filtering (FFT based)

def fft_filter(x, response: Callable[[np.ndarray], np.ndarray]):
    n = len(x)
    N = 1 << int(math.ceil(math.log2(n + 1)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    X *= response(f)
    return np.fft.irfft(X, N)[:n]


def lowpass(x, fc, order=2):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def highpass(x, fc, order=2):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))


def bandpass(x, fc, q=2.0):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (q * (f / fc - fc / np.maximum(f, 1e-3))) ** 2))


VOWELS = {  # formant centre frequencies (Hz), bandwidths (Hz), gains (dB)
    "a": ((800, 1150, 2900, 3900), (80, 90, 120, 130), (0, -6, -32, -20)),
    "o": ((450, 800, 2830, 3800), (70, 80, 100, 130), (0, -11, -21, -20)),
    "u": ((325, 700, 2530, 3500), (50, 60, 170, 180), (0, -16, -35, -40)),
    "e": ((400, 1600, 2700, 3300), (60, 80, 120, 150), (0, -24, -30, -35)),
    "i": ((350, 1700, 2700, 3700), (50, 100, 120, 150), (0, -20, -30, -36)),
}


def formant(x, vowel="a", shift=1.0):
    fcs, bws, gains = VOWELS[vowel]

    def resp(f):
        r = np.zeros_like(f)
        for fc, bw, g in zip(fcs, bws, gains):
            fc *= shift
            r += 10 ** (g / 20) / (1 + ((f - fc) / (bw * 1.6)) ** 2)
        return r
    return fft_filter(x, resp)


def sweep_filter(x, cutoff: np.ndarray, kind="low", q=0.7, block=2048):
    """Time-varying filter via overlap-add STFT; cutoff is an array (Hz) per sample."""
    hop = block // 2
    win = np.hanning(block)
    n = len(x)
    pad = np.concatenate([np.zeros(block), x, np.zeros(block)])
    cpad = np.concatenate([np.full(block, cutoff[0]), cutoff, np.full(block, cutoff[-1])])
    out = np.zeros_like(pad)
    f = np.fft.rfftfreq(block, 1 / SR)
    for i in range(0, len(pad) - block, hop):
        seg = pad[i:i + block] * win
        fc = float(cpad[i + hop])
        X = np.fft.rfft(seg)
        if kind == "low":
            H = 1 / np.sqrt(1 + (f / max(fc, 20)) ** 4)
        elif kind == "high":
            H = 1 / np.sqrt(1 + (max(fc, 20) / np.maximum(f, 1e-3)) ** 4)
        else:
            H = 1 / np.sqrt(1 + (q * (f / max(fc, 20) - max(fc, 20) / np.maximum(f, 1e-3))) ** 2)
        out[i:i + block] += np.fft.irfft(X * H, block)
    return out[block:block + n]


def reverb(x, rt60=3.0, wet=0.35, predelay=0.02, bright=4000, tail=True):
    """Synthetic hall: exponentially decaying filtered noise IR + early reflections."""
    n_ir = int(min(rt60 * 1.2, 8.0) * SR)
    t = np.arange(n_ir) / SR
    ir = RNG.standard_normal(n_ir) * np.exp(-6.9 * t / rt60)
    ir = lowpass(ir, bright, 1)
    for d, g in ((0.011, 0.6), (0.019, 0.45), (0.027, 0.35), (0.041, 0.3), (0.053, 0.22)):
        k = int(d * SR)
        if k < n_ir:
            ir[k] += g * 8
    ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    n = len(x) + (len(ir) if tail else 0)
    N = 1 << int(math.ceil(math.log2(n + 1)))
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n]
    dry = np.zeros(n)
    dry[:len(x)] = x
    return dry * (1 - wet) + y * wet * 3.0


# ----------------------------------------------------------------------------- instruments

def choir_note(freq, dur, vowel="a", voices=5, detune=0.012, vib=5.2, vib_depth=0.006, attack=0.4, release=0.6,
               breath=0.04, shift=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(voices):
        d = 1 + detune * (v - (voices - 1) / 2) / max(1, voices - 1) * 2
        vib_ph = RNG.uniform(0, 2 * np.pi)
        f = freq * d * (1 + vib_depth * np.sin(2 * np.pi * (vib + RNG.uniform(-0.4, 0.4)) * t + vib_ph))
        out += saw(f)
    out /= voices
    out += lowpass(noise(dur), 3000) * breath
    out = formant(out, vowel, shift)
    return normalize(out, 1.0) * env_adsr(n, attack, 0.2, 0.85, release)


def chord(freqs, dur, vowel="a", **kw):
    return normalize(mix(*[choir_note(f, dur, vowel, **kw) for f in freqs]), 1.0)


BELL_PARTIALS = ((0.5, 1.0, 4.0), (1.0, 0.8, 2.6), (1.183, 0.55, 2.0), (1.506, 0.42, 1.6), (2.0, 0.38, 1.3),
                 (2.514, 0.25, 0.9), (2.662, 0.22, 0.8), (3.011, 0.18, 0.6), (4.166, 0.12, 0.4), (5.433, 0.08, 0.3))


def bell(freq, dur, bright=1.0, decay_scale=1.0):
    n = int(dur * SR)
    out = np.zeros(n)
    for ratio, amp, dec in BELL_PARTIALS:
        f = freq * ratio
        if f > SR / 2 - 500:
            continue
        a = amp * (bright if ratio > 2 else 1.0)
        out += a * np.sin(2 * np.pi * f * np.arange(n) / SR + RNG.uniform(0, 6.28)) * env_exp(n, dec * decay_scale, 0.002)
    return out


def thump(freq0, freq1, dur, decay=0.25):
    n = int(dur * SR)
    f = curve(n, [(0, freq0), (0.15, freq1), (1, freq1 * 0.9)])
    return sine(f) * env_exp(n, decay, 0.001)


def taiko(dur=1.2, pitch=58):
    body = thump(pitch * 2.2, pitch, dur, 0.35)
    skin = bandpass(noise(dur), 900, 1.5) * env_exp(int(dur * SR), 0.05, 0.001) * 0.5
    return normalize(mix(body, skin), 1.0)


def fm_metal(freq, dur, ratio=1.41, index=6.0, decay=0.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * ratio * t) * index * env_exp(n, decay * 0.6)
    return np.sin(2 * np.pi * freq * t + mod) * env_exp(n, decay, 0.001)


def whoosh(dur, f0=300, f1=3000, f2=None, amp_pts=None):
    n = int(dur * SR)
    pts = [(0, f0), (0.5, f1), (1, f2 or f0)]
    x = sweep_filter(noise(dur), curve(n, pts), "band", q=1.8)
    return x * curve(n, amp_pts or [(0, 0), (0.5, 1), (1, 0)])


def riser(dur, f0=200, f1=1600):
    n = int(dur * SR)
    f = np.exp(np.linspace(math.log(f0), math.log(f1), n))
    return saw(f) * 0.4 + sweep_filter(noise(dur), f * 3, "band", q=2.0) * 0.6


# ----------------------------------------------------------------------------- sound recipes

D = {"D2": 73.42, "A2": 110.0, "D3": 146.83, "F3": 174.61, "A3": 220.0, "C4": 261.63, "D4": 293.66,
     "E4": 329.63, "F4": 349.23, "G4": 392.0, "A4": 440.0, "Bb3": 233.08, "Bb2": 116.54, "C3": 130.81,
     "G3": 196.0, "E3": 164.81, "Eb3": 155.56, "Ab3": 207.65, "G2": 98.0, "F2": 87.31, "C5": 523.25, "D5": 587.33}


def s_arrive():
    dur = 6.0
    boom = mix(thump(90, 32, 3.0, 0.9) * 1.4, lowpass(noise(3.0), 400) * env_exp(int(3 * SR), 0.6) * 1.2)
    ch = chord([D["D3"], D["A3"], D["D4"], D["F4"]], 5.0, "a", attack=1.6, release=1.6) * 0.9
    drone = lowpass(saw(curve(int(dur * SR), [(0, 40), (1, 36.7)])), 300) * env_adsr(int(dur * SR), 0.5, 0.5, 0.7, 2.0) * 0.6
    rise = riser(2.4, 120, 900) * env_adsr(int(2.4 * SR), 2.0, 0.1, 0.2, 0.3) * 0.4
    return reverb(mix(at(boom, 0.0, dur), at(ch, 0.9, dur), drone, at(rise, 0.2, dur)), 4.0, 0.45)


def s_roar():
    dur = 3.0
    n = int(dur * SR)
    f = curve(n, [(0, 62), (0.15, 92), (0.6, 80), (1, 48)])
    growl = soft_clip(saw(f) + 0.6 * saw(f * 1.5) + 0.4 * saw(f * 0.5), 2.5)
    growl = formant(growl, "a", 0.8) * 1.4 + lowpass(noise(dur), 900) * 0.4
    amp = curve(n, [(0, 0), (0.08, 1), (0.7, 0.8), (1, 0)])
    am = 1 + 0.35 * np.sin(2 * np.pi * 23 * np.arange(n) / SR)
    voice = chord([D["D3"] * 0.5, D["A3"] * 0.5, D["D3"]], dur, "o", attack=0.1, release=1.2, vib_depth=0.02) * 0.6
    return reverb(mix(normalize(growl) * amp * am, voice * amp), 2.6, 0.35)


def s_hum():
    dur = 4.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    base = 0.6 * sine(41.2, dur) + 0.4 * sine(82.4, dur) + 0.25 * sine(123.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t), dur)
    shimmer = bandpass(noise(dur), 2400, 3) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t)) * 0.12
    x = (base * (0.8 + 0.2 * np.sin(2 * np.pi * 2.0 * t)) + shimmer) * env_adsr(n, 0.6, 0.1, 1.0, 0.8)
    return x


def s_choir_stab():
    return reverb(chord([D["D4"], D["F4"], D["A4"], D["D3"]], 2.0, "a", attack=0.05, release=1.2), 3.5, 0.5)


def s_lance_charge():
    dur = 1.9
    n = int(dur * SR)
    whine = sine(np.exp(np.linspace(math.log(300), math.log(2400), n))) * curve(n, [(0, 0), (1, 1)]) * 0.5
    ch = choir_note(D["A4"], dur, "i", attack=1.4, release=0.1) * 0.6
    crackle = highpass(noise(dur), 4000) * (RNG.random(n) < 0.02) * 2.0
    return reverb(mix(whine, ch, crackle * curve(n, [(0, 0), (1, 1)])), 1.8, 0.3)


def s_lance_fire():
    dur = 2.9
    n = int(dur * SR)
    t = np.arange(n) / SR
    buzz = saw(110 + 6 * np.sin(2 * np.pi * 7 * t)) + saw(165.5, dur) * 0.6 + saw(220.7, dur) * 0.4
    buzz = lowpass(buzz, 2600)
    roar = bandpass(noise(dur), 900, 0.8)
    x = (buzz * 0.6 + roar * 0.7) * env_adsr(n, 0.02, 0.3, 0.8, 0.5)
    blast = thump(160, 40, 0.8, 0.3) * 1.2
    return reverb(soft_clip(mix(x, blast), 1.6), 2.0, 0.3)


def s_bell(freq, dur):
    return reverb(bell(freq, dur, 1.0) + bell(freq * 2.0, dur, 0.6) * 0.3, 3.0, 0.4)


def s_horizon():
    dur = 3.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    sub = sine(36 + 10 * np.sin(2 * np.pi * (2 + 4 * t / dur) * t)) * 0.9
    rev = highpass(noise(dur), 3000) * curve(n, [(0, 0), (1, 1)]) ** 2 * 0.5
    warble = sine(220 * (1 + 0.3 * np.sin(2 * np.pi * 9 * t))) * 0.15
    return reverb(mix(sub, rev, warble) * env_adsr(n, 0.3, 0.1, 1, 0.3), 2.5, 0.35)


def s_implode():
    dur = 1.6
    n = int(dur * SR)
    suck = sweep_filter(noise(dur), curve(n, [(0, 6000), (0.4, 300), (1, 200)]), "low") * curve(n, [(0, 0), (0.35, 1), (0.42, 0)])
    boom = at(thump(120, 30, 1.0, 0.4) * 1.5, 0.4, dur)
    return reverb(mix(suck, boom), 2.0, 0.3)


def s_simple(kind):
    if kind == "drone_launch":
        return reverb(mix(whoosh(0.8, 400, 2500, 600), fm_metal(880, 0.4, 2.0, 3.0, 0.15) * 0.3), 1.0, 0.2)
    if kind == "drone_charge":
        n = int(0.7 * SR)
        return sine(np.exp(np.linspace(math.log(600), math.log(1800), n))) * env_adsr(n, 0.5, 0.05, 0.6, 0.1) * 0.7
    if kind == "plasma_fire":
        n = int(0.6 * SR)
        z = sine(curve(n, [(0, 1600), (1, 300)])) * env_exp(n, 0.15) + bandpass(noise(0.6), 1200, 2) * env_exp(n, 0.1) * 0.5
        return reverb(z, 0.8, 0.2)
    if kind == "parry":
        return reverb(mix(fm_metal(1320, 0.9, 1.414, 4.0, 0.5), bell(2093, 0.9, 0.8) * 0.5), 1.5, 0.35)
    if kind == "vent":
        n = int(1.5 * SR)
        return highpass(noise(1.5), 1800) * env_adsr(n, 0.05, 0.2, 0.7, 0.6) * 0.6
    if kind == "vent_burst":
        return reverb(mix(thump(140, 45, 1.0, 0.35), lowpass(noise(1.2), 1200) * env_exp(int(1.2 * SR), 0.4)), 1.2, 0.25)
    if kind == "lunge":
        return mix(whoosh(1.0, 150, 1400, 200), thump(90, 50, 0.6, 0.2) * 0.6)
    if kind == "talon":
        crack = highpass(noise(0.5), 2500) * env_exp(int(0.5 * SR), 0.05)
        return reverb(mix(thump(110, 38, 0.8, 0.22) * 1.3, crack * 0.6, lowpass(noise(0.8), 500) * env_exp(int(0.8 * SR), 0.25) * 0.5), 1.0, 0.2)
    if kind == "seraph_whine":
        n = int(1.0 * SR)
        f = curve(n, [(0, 400), (1, 1400)])
        return (sine(f) + 0.4 * sine(f * 2.01) + 0.2 * square(f * 0.5)) * curve(n, [(0, 0), (0.8, 1), (1, 0.6)]) * 0.5
    if kind == "seraph_slice":
        return mix(whoosh(0.6, 800, 5000, 1500), fm_metal(660, 0.5, 3.1, 5.0, 0.2) * 0.3)
    if kind == "plate_impact":
        return reverb(mix(thump(80, 30, 1.4, 0.5) * 1.4, fm_metal(180, 1.2, 1.73, 8.0, 0.6) * 0.5,
                          lowpass(noise(1.5), 700) * env_exp(int(1.5 * SR), 0.5)), 1.6, 0.3)
    if kind == "hurt_hull":
        return mix(fm_metal(420, 0.45, 2.76, 7.0, 0.18), fm_metal(611, 0.45, 1.41, 4.0, 0.12) * 0.6)
    if kind == "hurt_flesh":
        n = int(0.5 * SR)
        wet = lowpass(noise(0.5), 700) * env_exp(n, 0.12)
        growl = soft_clip(saw(curve(n, [(0, 90), (1, 60)])), 2.0) * env_exp(n, 0.2) * 0.5
        return mix(wet, formant(growl, "o"))
    if kind == "shield":
        n = int(0.5 * SR)
        return reverb(sine(curve(n, [(0, 1900), (1, 1500)])) * env_exp(n, 0.12) * 0.6 + bell(2637, 0.5, 1.2) * 0.25, 1.0, 0.3)
    if kind == "halo_throw":
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        return whoosh(0.5, 600, 3500, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 28 * t))
    if kind == "halo_catch":
        return fm_metal(990, 0.3, 1.5, 3.0, 0.1)
    if kind == "censer":
        return reverb(mix(bell(1568, 1.5, 1.2) * 0.6, bell(2349, 1.5, 1.0) * 0.4), 2.0, 0.4)
    if kind == "censer_break":
        return reverb(mix(fm_metal(1200, 0.8, 2.2, 9.0, 0.3), highpass(noise(0.8), 3000) * env_exp(int(0.8 * SR), 0.15)), 1.2, 0.3)
    if kind == "psalter":
        notes = [D["D4"], D["F4"], D["A4"], D["D5"], D["A4"], D["F4"]]
        parts = [at(bell(f, 2.2, 1.1) * 0.6, i * 0.18, 3.2) for i, f in enumerate(notes)]
        return reverb(mix(*parts, at(choir_note(D["D4"], 2.4, "o", attack=0.8), 0.6, 3.2) * 0.5), 3.5, 0.5)
    raise KeyError(kind)


def s_prayer():
    dur = 6.0
    seq = [([D["D3"], D["F3"], D["A3"]], "o"), ([D["Bb2"], D["D3"], D["F3"]], "a"),
           ([D["C3"], D["E3"], D["G3"]], "o"), ([D["A2"], D["E3"], D["A3"]], "u")]
    parts = []
    for i, (fs, v) in enumerate(seq):
        parts.append(at(chord(fs, 1.9, v, attack=0.5, release=0.7) * 0.8, i * 1.5, dur))
    bells = at(bell(D["D4"] * 2, 3.0, 0.9) * 0.3, 0.0, dur)
    return reverb(mix(*parts, bells), 3.5, 0.45, tail=False)


def s_prayer_broken():
    dur = 2.2
    n = int(dur * SR)
    shatter = mix(*[at(fm_metal(RNG.uniform(1500, 4200), 0.6, RNG.uniform(1.3, 3.7), 6.0, 0.18) * 0.4, RNG.uniform(0, 0.25), dur) for _ in range(9)])
    glass = highpass(noise(dur), 3500) * env_exp(n, 0.35) * 0.6
    cut = chord([D["D4"], D["F4"], D["A4"]], 0.6, "a", attack=0.01, release=0.3) * 0.7
    down = sine(curve(int(1.2 * SR), [(0, 300), (1, 60)])) * env_exp(int(1.2 * SR), 0.5)
    return reverb(mix(cut, shatter, glass, at(down, 0.15, dur)), 2.5, 0.4)


def s_benediction():
    dur = 3.2
    n = int(dur * SR)
    ch = chord([D["D3"], D["A3"], D["D4"], D["F4"], D["A4"]], dur, "a", attack=0.02, release=1.6) * 1.0
    boom = thump(100, 28, 2.2, 0.8) * 1.6
    air = lowpass(noise(dur), 2500) * env_exp(n, 0.9) * 0.7
    return reverb(soft_clip(mix(ch, boom, air), 1.4), 4.5, 0.5)


def s_transform():
    dur = 5.5
    n = int(dur * SR)
    creak = mix(*[at(fm_metal(RNG.uniform(60, 140), 1.2, RNG.uniform(1.1, 1.9), 12.0, 0.7) * 0.5, RNG.uniform(0, 4.0), dur) for _ in range(8)])
    tear = sweep_filter(noise(dur), curve(n, [(0, 300), (0.4, 2500), (0.7, 800), (1, 400)]), "band", 1.2) * curve(n, [(0, 0.2), (0.45, 1), (1, 0.3)])
    squelch = mix(*[at(lowpass(noise(0.4), 600) * env_exp(int(0.4 * SR), 0.1), RNG.uniform(1.0, 5.0), dur) for _ in range(10)])
    drone = lowpass(saw(curve(n, [(0, 55), (1, 36)])), 400) * 0.5
    return reverb(mix(creak, tear * 0.8, squelch * 0.7, drone), 3.0, 0.35)


def s_nova_charge():
    dur = 3.3
    n = int(dur * SR)
    clus = chord([D["D3"], D["Eb3"], D["Ab3"], D["A3"]], dur, "u", attack=2.5, release=0.2, vib_depth=0.02) * 0.8
    rumble = lowpass(noise(dur), 160) * curve(n, [(0, 0.2), (1, 1.2)])
    rise = riser(dur, 80, 1200) * curve(n, [(0, 0), (1, 0.6)])
    return reverb(soft_clip(mix(clus, rumble, rise), 1.3), 2.5, 0.35, tail=False)


def s_nova():
    dur = 2.8
    n = int(dur * SR)
    boom = thump(120, 24, 2.4, 0.9) * 1.6
    blast = lowpass(noise(dur), 1800) * env_exp(n, 0.7)
    ch = chord([D["D3"] * 0.5, D["Ab3"] * 0.5, D["D3"]], dur, "a", attack=0.01, release=1.6, vib_depth=0.03) * 0.7
    return reverb(soft_clip(mix(boom, blast, ch), 1.8), 4.0, 0.45)


def s_death():
    dur = 7.5
    n = int(dur * SR)
    groan = soft_clip(saw(curve(n, [(0, 70), (0.5, 55), (1, 30)])), 2.0)
    groan = formant(groan, "o", 0.7) * curve(n, [(0, 0), (0.05, 1), (0.75, 0.6), (0.82, 0), (1, 0)])
    ch = chord([D["D4"], D["F4"], D["A4"]], 5.5, "a", attack=0.6, release=3.0) * 0.6
    ch_fall = ch * curve(len(ch), [(0, 1), (1, 0.2)])
    final = at(mix(thump(160, 26, 1.8, 0.7) * 1.6, lowpass(noise(1.8), 1500) * env_exp(int(1.8 * SR), 0.6)), 6.0, dur)
    suck = at(sweep_filter(noise(0.6), curve(int(0.6 * SR), [(0, 5000), (1, 200)]), "low") * curve(int(0.6 * SR), [(0, 0), (1, 1)]), 5.4, dur)
    return reverb(mix(normalize(groan) * 0.8, ch_fall, final, suck), 5.0, 0.45)


# ----------------------------------------------------------------------------- music

def music_p1():
    """"Hymn of the Sacred Vessel" - 60 BPM, 16 bars of 4/4, D minor, seamless loop."""
    bar = 4.0
    bars = 16
    dur = bar * bars
    prog = [([D["D3"], D["F3"], D["A3"], D["D4"]], "a"), ([D["Bb2"], D["F3"], D["Bb3"], D["D4"]], "o"),
            ([D["F2"] * 2, D["A3"], D["C4"], D["F4"]], "a"), ([D["C3"], D["G3"], D["C4"], D["E4"]], "o"),
            ([D["D3"], D["A3"], D["D4"], D["F4"]], "a"), ([D["G2"] * 2, D["Bb3"], D["D4"], D["G4"]], "u"),
            ([D["A2"] * 2, D["E3"], D["A3"], D["C4"] * 1.0595], "o"), ([D["D3"], D["F3"], D["A3"], D["D4"]], "a")]
    parts = []
    for i in range(bars):
        fs, v = prog[(i // 2) % len(prog)] if i < 8 else prog[i % len(prog)]
        if i % 2 == 0 or i >= 8:
            length = bar * (2 if i < 8 else 1) + 1.0
            parts.append(at(chord(fs, length, v, attack=1.2, release=1.2, voices=4) * 0.55, i * bar, dur + 4))
    drone = mix(lowpass(saw(D["D2"], dur + 4), 500) * 0.25, lowpass(saw(D["A2"], dur + 4), 600) * 0.18)
    drone *= env_adsr(len(drone), 1.0, 0.1, 1.0, 1.0)
    for i in range(bars):
        if i % 2 == 0:
            parts.append(at(bell(D["D4"], 5.0, 0.9) * 0.35, i * bar, dur + 4))
        for b in (0, 2):
            parts.append(at(taiko(1.4, 52) * (0.55 if b == 0 else 0.35), i * bar + b * 1.0, dur + 4))
        if i >= 8:
            arp = [D["D5"], D["A4"], D["F4"], D["A4"]]
            for k, f in enumerate(arp * 2):
                parts.append(at(bell(f, 1.6, 0.7) * 0.12, i * bar + k * 0.5, dur + 4))
    x = mix(drone, *parts)
    x = reverb(x, 4.5, 0.4)
    return loopify(x, dur)


def music_p2():
    """"The False Ascension" - 96 BPM, 16 bars, menacing ostinato, dissonant choir."""
    beat = 60 / 96
    bar = beat * 4
    bars = 16
    dur = bar * bars
    parts = []
    bass_notes = [D["D2"], D["D2"], D["Eb3"] / 2, D["D2"], D["D2"], D["Ab3"] / 4, D["G2"], D["F2"]]
    for i in range(bars * 8):
        f = bass_notes[i % len(bass_notes)]
        n = int(beat / 2 * 1.1 * SR)
        note = soft_clip(lowpass(saw(f, beat / 2 * 1.1) + 0.5 * square(f * 2, beat / 2 * 1.1), 900), 2.0) * env_adsr(n, 0.005, 0.05, 0.7, 0.05)
        parts.append(at(note * 0.32, i * beat / 2, dur + 4))
    for i in range(bars * 4):
        if i % 4 in (0, 2) or (i % 8 == 7):
            parts.append(at(taiko(1.0, 56) * 0.7, i * beat, dur + 4))
        if i % 2 == 1:
            parts.append(at(fm_metal(330, 0.3, 3.7, 9.0, 0.08) * 0.12, i * beat, dur + 4))
    clusters = [([D["D3"], D["Eb3"], D["A3"]], "u"), ([D["D3"], D["Ab3"], D["A3"]], "a"),
                ([D["C3"], D["Eb3"], D["G3"]], "u"), ([D["D3"], D["F3"], D["Ab3"]], "a")]
    for i in range(0, bars, 2):
        fs, v = clusters[(i // 2) % len(clusters)]
        parts.append(at(chord(fs, bar * 2 + 0.6, v, attack=0.6, release=0.6, vib_depth=0.018, voices=4) * 0.42, i * bar, dur + 4))
    for i in range(0, bars, 4):
        parts.append(at(riser(bar, 100, 900) * curve(int(bar * SR), [(0, 0), (1, 0.25)]), i * bar + bar * 3, dur + 4))
    x = mix(*parts)
    x = reverb(x, 2.8, 0.3)
    return loopify(x, dur)


def loopify(x, dur):
    n = int(dur * SR)
    out = x[:n].copy()
    tail = x[n:]
    k = min(len(tail), n)
    out[:k] += tail[:k]
    return normalize(out, 0.8)


# ----------------------------------------------------------------------------- registry & encoding

SOUNDS: Dict[str, Callable[[], np.ndarray]] = {
    "arrive": s_arrive, "roar": s_roar, "hum": s_hum, "choir": s_choir_stab,
    "lance_charge": s_lance_charge, "lance_fire": s_lance_fire,
    "bell_low": lambda: s_bell(D["D3"] * 0.5, 3.0), "bell_high": lambda: s_bell(D["D5"], 2.2),
    "horizon": s_horizon, "implode": s_implode, "prayer": s_prayer, "prayer_broken": s_prayer_broken,
    "benediction": s_benediction, "transform": s_transform, "nova_charge": s_nova_charge, "nova": s_nova,
    "death": s_death,
}
for _k in ("drone_launch", "drone_charge", "plasma_fire", "parry", "vent", "vent_burst", "lunge", "talon",
           "seraph_whine", "seraph_slice", "plate_impact", "hurt_hull", "hurt_flesh", "shield", "halo_throw",
           "halo_catch", "censer", "censer_break", "psalter"):
    SOUNDS[_k] = (lambda k=_k: s_simple(k))

MUSIC = {"vesper_p1": music_p1, "vesper_p2": music_p2}


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def encode_ogg(x, out_path, quality=3, tmp_dir=None):
    tmp_dir = tmp_dir or os.path.dirname(out_path)
    wav = os.path.join(tmp_dir, os.path.basename(out_path) + ".wav")
    write_wav(wav, x)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality), out_path],
                   check=True)
    os.remove(wav)


def render_all(sound_dir, music_dir, only=None):
    os.makedirs(sound_dir, exist_ok=True)
    os.makedirs(music_dir, exist_ok=True)
    info = {}
    for name, fn in SOUNDS.items():
        if only and name not in only:
            continue
        x = fade(normalize(fn(), 0.89))
        p = os.path.join(sound_dir, f"{name}.ogg")
        encode_ogg(x, p, 3)
        info[name] = (len(x) / SR, os.path.getsize(p))
    for name, fn in MUSIC.items():
        if only and name not in only:
            continue
        x = fn()
        p = os.path.join(music_dir, f"{name}.ogg")
        encode_ogg(x, p, 2)
        info[name] = (len(x) / SR, os.path.getsize(p))
    return info


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    info = render_all(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
    for k, (d, s) in info.items():
        print(f"{k:16s} {d:6.2f}s {s / 1024:7.1f} KB")
    print("total KB", sum(s for _, s in info.values()) / 1024, "time", round(time.time() - t0, 1))
