"""
sfx.py - original sound synthesis (numpy) -> mono Ogg Vorbis.

Every sound in the add-on is synthesised here from oscillators, noise and
FFT-domain filters; nothing is sampled from existing recordings.
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
import wave
import zlib
from typing import Callable, Iterable, Optional, Sequence, Tuple

import numpy as np

SR = 44100


def rng(*parts) -> np.random.Generator:
    return np.random.default_rng(zlib.crc32("|".join(str(p) for p in parts).encode()))


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR), dtype=np.float64) / SR


def silence(dur: float) -> np.ndarray:
    return np.zeros(int(dur * SR))


# --------------------------------------------------------------------------- sources

def sine(freq, dur: float, phase: float = 0.0) -> np.ndarray:
    """freq may be a number or an array (per-sample Hz) for glides."""
    t = t_axis(dur)
    if np.isscalar(freq):
        return np.sin(2 * np.pi * freq * t + phase)
    f = np.resize(np.asarray(freq, dtype=np.float64), len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def osc(freq, dur: float, shape: str = "saw", harmonics: int = 24) -> np.ndarray:
    """Band-limited additive oscillator."""
    out = np.zeros(int(dur * SR))
    f0 = float(np.mean(freq)) if not np.isscalar(freq) else float(freq)
    for k in range(1, harmonics + 1):
        if k * f0 > SR * 0.45:
            break
        if shape == "saw":
            a = 1.0 / k
        elif shape == "square":
            a = 1.0 / k if k % 2 else 0.0
        elif shape == "tri":
            a = (1.0 / (k * k)) * (1 if (k // 2) % 2 == 0 else -1) if k % 2 else 0.0
        else:
            raise ValueError(shape)
        if a:
            out += a * sine(freq * k if np.isscalar(freq) else np.asarray(freq) * k, dur)
    return out


def noise(dur: float, seed, color: str = "white") -> np.ndarray:
    n = int(dur * SR)
    x = rng("noise", seed).standard_normal(n)
    if color == "white":
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    X *= {"pink": 1 / np.sqrt(f), "brown": 1 / f}[color]
    y = np.fft.irfft(X, n)
    return y / (np.max(np.abs(y)) + 1e-9)


# --------------------------------------------------------------------------- shaping

def env_exp(dur: float, decay: float, attack: float = 0.002) -> np.ndarray:
    """Percussive envelope: linear attack, exponential decay (time constant `decay` seconds)."""
    t = t_axis(dur)
    return np.minimum(1.0, t / max(attack, 1e-5)) * np.exp(-t / decay)


def env_adsr(dur: float, a: float, d: float, s: float, r: float) -> np.ndarray:
    t = t_axis(dur)
    e = np.where(t < a, t / max(a, 1e-5), np.where(t < a + d, 1 - (1 - s) * (t - a) / max(d, 1e-5), s))
    rel = np.clip((dur - t) / max(r, 1e-5), 0, 1)
    return e * rel


def fade(x: np.ndarray, fin: float = 0.004, fout: float = 0.02) -> np.ndarray:
    y = x.copy()
    a, b = min(len(y), int(fin * SR)), min(len(y), int(fout * SR))
    if a:
        y[:a] *= np.linspace(0, 1, a)
    if b:
        y[-b:] *= np.linspace(1, 0, b)
    return y


def filt(x: np.ndarray, response: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Zero-phase FFT filter; `response(freqs)` returns a gain per frequency."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * response(f), len(x))


def lowpass(x, cutoff: float, order: int = 2):
    return filt(x, lambda f: 1 / np.sqrt(1 + (f / cutoff) ** (2 * order)))


def highpass(x, cutoff: float, order: int = 2):
    return filt(x, lambda f: 1 - 1 / np.sqrt(1 + (f / cutoff) ** (2 * order)))


def bandpass(x, centre: float, q: float = 4.0):
    bw = centre / q
    return filt(x, lambda f: 1 / np.sqrt(1 + ((f * f - centre * centre) / (np.maximum(f, 1e-6) * bw)) ** 2))


def resonate(x, peaks: Sequence[Tuple[float, float, float]]):
    """Sum of band-passes: (centre Hz, Q, gain) - gives bodies their material."""
    out = np.zeros_like(x)
    for c, q_, g in peaks:
        out += g * bandpass(x, c, q_)
    return out


def sweep_bandpass(x: np.ndarray, f0: float, f1: float, q: float = 3.0, slices: int = 24) -> np.ndarray:
    """Band-pass whose centre glides from f0 to f1 (overlap-added slices)."""
    n = len(x)
    out = np.zeros(n)
    hop = max(1, n // slices)
    win = np.hanning(hop * 2)
    for i in range(0, n, hop):
        seg = np.zeros(hop * 2)
        chunk = x[i:i + hop * 2]
        seg[:len(chunk)] = chunk
        c = f0 * (f1 / f0) ** (min(1.0, i / max(1, n - hop)))
        y = bandpass(seg * win, c, q)
        out[i:i + hop * 2] += y[:max(0, min(hop * 2, n - i))]
    return out


def reverb(x: np.ndarray, seconds: float = 1.2, mix_: float = 0.25, seed="hall", damp: float = 5000.0,
           predelay: float = 0.012) -> np.ndarray:
    """Convolution reverb with a synthetic decaying-noise impulse (stone hall character)."""
    n = int(seconds * SR)
    ir = rng("ir", seed).standard_normal(n) * np.exp(-np.arange(n) / (seconds * SR / 6.9))
    ir = lowpass(ir, damp, 1)
    ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
    m = len(x) + len(ir) - 1
    size = 1 << (m - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:m]
    wet *= (np.max(np.abs(x)) + 1e-9) / (np.max(np.abs(wet)) + 1e-9)
    out = np.zeros(m)
    out[:len(x)] += x * (1 - mix_)
    return out + wet * mix_


def delay_mix(x: np.ndarray, taps: Sequence[Tuple[float, float]]) -> np.ndarray:
    """Discrete echoes: (delay seconds, gain)."""
    n = len(x) + int(max(d for d, _ in taps) * SR)
    out = np.zeros(n)
    out[:len(x)] += x
    for d, g in taps:
        k = int(d * SR)
        out[k:k + len(x)] += x * g
    return out


def mixdown(*layers: Tuple[np.ndarray, float, float]) -> np.ndarray:
    """Mix (signal, start seconds, gain) layers."""
    n = max(int(s * SR) + len(x) for x, s, _ in layers)
    out = np.zeros(n)
    for x, s, g in layers:
        k = int(s * SR)
        out[k:k + len(x)] += x * g
    return out


def normalize(x: np.ndarray, peak: float = 0.89) -> np.ndarray:
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 1e-9 else x


def soft_clip(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    return np.tanh(x * drive) / math.tanh(drive)


# --------------------------------------------------------------------------- instruments

def bell(freq: float, dur: float, *, seed="bell", bright: float = 1.0, detune: float = 0.004,
         partials: Optional[Sequence[Tuple[float, float, float]]] = None) -> np.ndarray:
    """Inharmonic struck bell. partials: (ratio, amplitude, decay seconds)."""
    partials = partials or [(0.5, 0.55, 1.0), (1.0, 1.0, 0.85), (1.183, 0.7, 0.62), (1.506, 0.55, 0.5),
                            (2.0, 0.75, 0.42), (2.514, 0.38, 0.3), (2.662, 0.3, 0.26), (3.011, 0.26, 0.2),
                            (4.166, 0.2, 0.14), (5.433, 0.14, 0.1), (6.796, 0.1, 0.07)]
    r = rng("bell", seed)
    t = t_axis(dur)
    out = np.zeros_like(t)
    for ratio, amp, dec in partials:
        f = freq * ratio
        if f > SR * 0.45:
            continue
        a = amp * (bright ** math.log2(max(ratio, 0.5) * 2) if bright != 1 else 1)
        for k in (-1, 1):                                    # beating pair = shimmering bronze
            out += 0.5 * a * np.sin(2 * np.pi * f * (1 + k * detune * r.uniform(0.5, 1.5)) * t +
                                    r.uniform(0, 6.28)) * np.exp(-t / (dec * dur))
    strike = bandpass(noise(0.03, seed), min(freq * 6, 9000), 1.5) * env_exp(0.03, 0.006)
    out[:len(strike)] += strike * 0.6
    return out * np.minimum(1.0, t / 0.002)


def organ(freq: float, dur: float, *, stops: Sequence[Tuple[float, float]] = ((1, 1.0), (2, 0.55), (3, 0.3), (4, 0.28), (6, 0.12), (8, 0.1)),
          attack: float = 0.09, release: float = 0.25, seed="organ", chiff: float = 0.25) -> np.ndarray:
    """Pipe-organ tone: summed ranks, slow speech, breath chiff."""
    r = rng("organ", seed, freq)
    t = t_axis(dur)
    out = np.zeros_like(t)
    for mult, amp in stops:
        f = freq * mult
        if f > SR * 0.45:
            continue
        for det in (-0.0015, 0.0015):
            out += 0.5 * amp * np.sin(2 * np.pi * f * (1 + det) * t + r.uniform(0, 6.28))
    out *= env_adsr(dur, attack, 0.05, 0.92, release)
    out *= 1 + 0.035 * np.sin(2 * np.pi * 5.2 * t)          # tremulant
    if chiff:
        c = bandpass(noise(dur, (seed, freq)), freq * 3, 2.0) * env_exp(dur, 0.05, 0.01)
        out += chiff * c
    return out


def click(dur: float = 0.02, freq: float = 2500, seed="click", q: float = 3.0) -> np.ndarray:
    return bandpass(noise(dur, seed), freq, q) * env_exp(dur, dur / 5, 0.0005)


def thud(freq: float = 60, dur: float = 0.4, drop: float = 0.5, seed="thud") -> np.ndarray:
    t = t_axis(dur)
    f = freq * (1 - drop * (1 - np.exp(-t / 0.05)))
    body = sine(f, dur) * env_exp(dur, dur / 4, 0.003)
    return body + 0.3 * lowpass(noise(dur, seed), 400) * env_exp(dur, 0.03)


def grains(dur: float, rate: float, grain: Callable[[int], np.ndarray], seed="grains", jitter: float = 0.4,
           accel: float = 0.0) -> np.ndarray:
    """Scatter short grains over `dur` at ~`rate` per second (crackles, ratchets, shards)."""
    r = rng("grains", seed)
    out = np.zeros(int(dur * SR))
    t, i = 0.0, 0
    while t < dur:
        g = grain(i)
        k = int(t * SR)
        seg = g[:max(0, len(out) - k)]
        out[k:k + len(seg)] += seg
        step = 1.0 / (rate * (1 + accel * t / dur))
        t += step * (1 + jitter * r.uniform(-1, 1))
        i += 1
    return out


# --------------------------------------------------------------------------- output

def save_ogg(x: np.ndarray, path: str, peak: float = 0.89, quality: int = 4) -> float:
    """Write mono Ogg Vorbis; returns duration in seconds."""
    x = fade(normalize(np.asarray(x, dtype=np.float64), peak))
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = f.name
    try:
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-map_metadata", "-1",
                        "-fflags", "+bitexact", "-flags:a", "+bitexact",
                        "-c:a", "libvorbis", "-q:a", str(quality), "-ac", "1", "-ar", str(SR), path],
                       check=True)
    finally:
        os.unlink(wav)
    return len(x) / SR
