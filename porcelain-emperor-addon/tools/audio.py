"""
Procedural sound design for the Porcelain Emperor (numpy synthesis -> OGG Vorbis).

    python3 tools/audio.py <out_dir>

Every sound is synthesised from scratch (no samples):
  chime    struck porcelain bowl: inharmonic partials with beating
  crack    ceramic fracture: sharp filtered transients + low thunk
  shatter  big break: a burst of clicks, glassy noise and falling shards
  gong     court gong: low inharmonic partials with a slow swell
  roar     a ringing ceramic roar: growl through formants + metallic overtones
  hum      the Mandate's drone (repair channel)
  stamp    the imperial seal stamping down (telegraph lock)
  music    "Mandate of Heaven": 64 s pentatonic battle loop (plucked zither,
           taiko-like drums, gong, drone)
"""
from __future__ import annotations

import os
import subprocess
import sys
import wave

import numpy as np

SR = 44100
RNG = np.random.default_rng(20261124)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def env_exp(sec, tau, attack=0.002):
    t = t_axis(sec)
    e = np.exp(-t / tau)
    a = np.clip(t / attack, 0, 1) if attack > 0 else 1
    return e * a


def lowpass(x, cutoff):
    """One-pole low-pass."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def bandpass_fft(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    mask = ((f >= lo) & (f <= hi)).astype(float)
    # soft edges
    mask = np.convolve(mask, np.ones(32) / 32, mode="same")
    return np.fft.irfft(X * mask, n=len(x))


def norm(x, peak=0.89):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def place(buf, snd, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n]


# --------------------------------------------------------------------------- one-shots

def chime(f0=880.0, sec=2.6, bright=1.0):
    t = t_axis(sec)
    ratios = [1.0, 2.32, 4.25, 6.63, 9.38]
    amps = [1.0, 0.55, 0.32 * bright, 0.18 * bright, 0.09 * bright]
    taus = [1.1, 0.7, 0.4, 0.25, 0.15]
    out = np.zeros_like(t)
    for r, a, tau in zip(ratios, amps, taus):
        f = f0 * r
        beat = 1 + 0.004 * np.sin(2 * np.pi * 3.1 * t)
        out += a * np.sin(2 * np.pi * f * t * beat + RNG.uniform(0, 6)) * np.exp(-t / tau)
    click = bandpass_fft(RNG.normal(0, 1, len(t)), 3000, 9000) * np.exp(-t / 0.004)
    return norm(out + 0.4 * click)


def crack(sec=0.7):
    out = np.zeros(int(SR * sec))
    n = int(SR * 0.03)
    for k in range(7):
        burst = RNG.normal(0, 1, n) * np.exp(-np.arange(n) / (SR * RNG.uniform(0.002, 0.008)))
        burst = bandpass_fft(burst, 1500, 8000)
        place(out, burst * RNG.uniform(0.4, 1.0), 0.005 + k * RNG.uniform(0.02, 0.07))
    th = t_axis(0.25)
    thunk = np.sin(2 * np.pi * (140 - 60 * th) * th) * np.exp(-th / 0.05)
    place(out, thunk * 0.8, 0.0)
    return norm(out)


def shatter(sec=2.2):
    out = np.zeros(int(SR * sec))
    t = t_axis(sec)
    noise = bandpass_fft(RNG.normal(0, 1, len(t)), 2500, 12000) * np.exp(-t / 0.18)
    out += noise * 0.9
    for _ in range(60):
        at = abs(RNG.normal(0.0, 0.45))
        f = RNG.uniform(1800, 5200)
        place(out, chime(f, 0.35, 0.6) * RNG.uniform(0.05, 0.25), at)
    th = t_axis(0.5)
    boom = np.sin(2 * np.pi * (90 - 40 * th) * th) * np.exp(-th / 0.12)
    place(out, boom, 0.0)
    return norm(out)


def gong(f0=98.0, sec=5.5):
    t = t_axis(sec)
    ratios = [1.0, 1.52, 2.0, 2.71, 3.4, 4.12, 5.3]
    out = np.zeros_like(t)
    for i, r in enumerate(ratios):
        swell = (1 - np.exp(-t / (0.08 + 0.05 * i))) * np.exp(-t / (2.6 - 0.25 * i))
        bend = 1 - 0.006 * np.exp(-t / 0.4)
        out += np.sin(2 * np.pi * f0 * r * bend * t + i) * swell / (1 + i * 0.5)
    strike = lowpass(RNG.normal(0, 1, len(t)), 900) * np.exp(-t / 0.03)
    return norm(out + strike * 0.6)


def stamp(sec=0.9):
    t = t_axis(sec)
    body = np.sin(2 * np.pi * (180 - 120 * t) * t) * np.exp(-t / 0.09)
    wood = bandpass_fft(RNG.normal(0, 1, len(t)), 300, 2500) * np.exp(-t / 0.02)
    ring = chime(1320, sec, 0.5) * 0.25
    return norm(body + 0.6 * wood + ring)


def roar(sec=3.2):
    t = t_axis(sec)
    vib = 1 + 0.03 * np.sin(2 * np.pi * 5.5 * t) + 0.02 * RNG.normal(0, 1, len(t)).cumsum() / SR
    f = 62 * vib * (1 + 0.25 * np.sin(np.pi * np.clip(t / sec, 0, 1)))
    phase = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((phase / (2 * np.pi)) % 1) - 1
    growl = lowpass(saw + 0.4 * RNG.normal(0, 1, len(t)), 1200)
    formant = bandpass_fft(growl, 300, 900) + 0.5 * bandpass_fft(growl, 1100, 2000)
    amp = np.clip(t / 0.25, 0, 1) * np.clip((sec - t) / 0.8, 0, 1)
    metal = np.zeros_like(t)
    for r in (7.1, 11.3, 15.8):
        metal += np.sin(2 * np.pi * 62 * r * t) * 0.15
    return norm((formant * 1.2 + metal * growl * 0.3) * amp)


def hum(sec=6.0):
    t = t_axis(sec)
    out = np.zeros_like(t)
    for f, a in ((110, 1.0), (165, 0.7), (220, 0.4), (330, 0.25), (440, 0.12)):
        out += a * np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * 0.37 * t))
    shimmer = sum(np.sin(2 * np.pi * f * t) * 0.05 for f in (1760, 2217))
    amp = np.clip(t / 0.8, 0, 1) * np.clip((sec - t) / 0.8, 0, 1)
    return norm((out + shimmer * (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t))) * amp, 0.7)


# --------------------------------------------------------------------------- music

def pluck(freq, sec=1.6, bright=0.5, slide=0.0):
    """Karplus-Strong plucked string (zither-like), optional upward slide."""
    n = int(SR * sec)
    period = int(SR / freq)
    buf = RNG.uniform(-1, 1, period)
    out = np.empty(n)
    decay = 0.996
    idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % period
        buf[idx] = decay * (bright * buf[idx] + (1 - bright) * buf[nxt])
        idx = nxt
    if slide:
        t = t_axis(sec)
        k = 1 + slide * (1 - np.exp(-t / 0.08))
        pos = np.cumsum(k)
        pos = pos[pos < n - 1]
        out = np.interp(pos, np.arange(n), out)
    return out * np.exp(-np.arange(len(out)) / SR / 1.4)


def drum(sec=0.8, f_hi=130, f_lo=48):
    t = t_axis(sec)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    skin = lowpass(RNG.normal(0, 1, len(t)), 2000) * np.exp(-t / 0.015)
    return body + 0.35 * skin


def music(sec=64.0, bpm=96):
    out = np.zeros(int(SR * sec))
    beat = 60 / bpm
    # D gong-mode pentatonic: D E F# A B
    scale = [146.83, 164.81, 185.00, 220.00, 246.94]

    def note(deg, octave=1):
        return scale[deg % 5] * (2 ** (deg // 5)) * octave
    # drone (D + A)
    t = t_axis(sec)
    drone = (np.sin(2 * np.pi * 73.42 * t) + 0.6 * np.sin(2 * np.pi * 110.0 * t)
             + 0.2 * np.sin(2 * np.pi * 146.83 * t + np.sin(2 * np.pi * 0.2 * t)))
    out += drone * 0.11
    bars = int(sec / (beat * 4))
    motif_a = [0, 2, 3, 4, 3, 2, 0, -1]
    motif_b = [4, 5, 7, 5, 4, 3, 2, 0]
    motif_c = [7, 6, 4, 3, 4, 2, 3, 0]
    rhythm = [0, 0.75, 1.0, 1.5, 2.0, 2.75, 3.0, 3.5]
    for bar in range(bars):
        t0 = bar * beat * 4
        section = (bar // 4) % 4
        motif = [motif_a, motif_b, motif_a, motif_c][section]
        for k, (deg, r) in enumerate(zip(motif, rhythm)):
            if bar % 2 == 1 and k % 2 == 1:
                continue
            slide = 0.059 if (k == 0 and bar % 4 == 3) else 0.0
            place(out, pluck(note(deg, 2), 1.4, 0.45, slide) * 0.34, t0 + r * beat)
        # bass pluck on beats 1 and 3
        place(out, pluck(note(motif[0] - 5, 1), 1.8, 0.6) * 0.3, t0)
        place(out, pluck(note(motif[4] - 5, 1), 1.8, 0.6) * 0.25, t0 + 2 * beat)
        # drums: big hit on 1, answer on the "and" of 2, rolls at phrase ends
        place(out, drum() * 0.55, t0)
        place(out, drum(0.5, 160, 70) * 0.3, t0 + 1.5 * beat)
        place(out, drum(0.6, 120, 50) * 0.4, t0 + 2 * beat)
        if bar % 4 == 3:
            for k in range(6):
                place(out, drum(0.3, 200, 90) * (0.18 + 0.05 * k), t0 + 3 * beat + k * beat / 6)
        if bar % 8 == 0:
            place(out, gong(73.4, 6.0) * 0.32, t0)
        # temple-block ticks
        for k in range(8):
            if (bar + k) % 3 == 0:
                tick = bandpass_fft(RNG.normal(0, 1, 1500), 1800, 4200) * np.exp(-np.arange(1500) / 120)
                place(out, tick * 0.05, t0 + k * beat / 2)
    # make the loop seamless: crossfade the tail into the head
    fade = int(SR * 0.5)
    out[:fade] = out[:fade] * np.linspace(0, 1, fade) + out[-fade:] * np.linspace(1, 0, fade)
    out = out[:-fade]
    return norm(out, 0.8)


# --------------------------------------------------------------------------- io

def write_ogg(path, data, quality=4):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wav = path[:-4] + ".tmp.wav"
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality), path],
                   check=True)
    os.remove(wav)


SOUNDS = {
    # file name: (generator, quality)
    "chime": (lambda: chime(880), 4),
    "chime_low": (lambda: chime(587.3, 3.0, 0.8), 4),
    "crack": (crack, 4),
    "shatter": (shatter, 4),
    "gong": (gong, 4),
    "stamp": (stamp, 4),
    "roar": (roar, 4),
    "hum": (hum, 3),
    "music_mandate": (music, 3),
}


def build(out_dir):
    for name, (fn, q) in SOUNDS.items():
        write_ogg(os.path.join(out_dir, f"{name}.ogg"), fn(), q)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "build/sounds")
