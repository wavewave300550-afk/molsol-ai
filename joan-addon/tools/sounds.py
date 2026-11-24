"""
Procedural sound design for the add-on (numpy synthesis -> mono OGG Vorbis via ffmpeg).

Every sound is generated from code (deterministic seeds), so the pack carries
no third-party audio. Mono files keep the sounds positional in Bedrock.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave
from typing import Callable, Dict, List

import numpy as np

SR = 44100


def t_axis(sec: float) -> np.ndarray:
    return np.arange(int(SR * sec)) / SR


def env_adsr(n: int, a: float, d: float, s: float, r: float, sus_len: float) -> np.ndarray:
    A, D, S, R = int(a * SR), int(d * SR), int(sus_len * SR), int(r * SR)
    e = np.concatenate([np.linspace(0, 1, max(1, A)), np.linspace(1, s, max(1, D)), np.full(max(0, S), s),
                        np.linspace(s, 0, max(1, R))])
    if len(e) < n:
        e = np.concatenate([e, np.zeros(n - len(e))])
    return e[:n]


def env_exp(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(0, t - attack) / decay)


def noise(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def onepole_lp(x: np.ndarray, cutoff) -> np.ndarray:
    """One-pole low-pass; cutoff may be an array (time-varying)."""
    y = np.zeros_like(x)
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def bandpass(x: np.ndarray, center, q: float = 2.0) -> np.ndarray:
    """State-variable band-pass, center may vary over time."""
    c = np.broadcast_to(np.asarray(center, dtype=float), x.shape)
    low = band = 0.0
    y = np.zeros_like(x)
    damp = 1.0 / q
    for i in range(len(x)):
        f = 2 * np.sin(np.pi * min(c[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        y[i] = band
    return y


def reverb(x: np.ndarray, seconds: float = 1.6, mix: float = 0.3, seed: int = 9, predelay: float = 0.012) -> np.ndarray:
    n = int(seconds * SR)
    ir = noise(n, seed) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir = onepole_lp(ir, 5200.0)
    ir[: int(predelay * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    m = len(x) + n - 1
    size = 1 << (m - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x) + n]
    dry = np.concatenate([x, np.zeros(n)])
    return dry * (1 - mix) + wet * mix * 1.4


def add_at(dst: np.ndarray, src: np.ndarray, start: int, gain: float = 1.0) -> np.ndarray:
    """dst[start:] += src (clipped to dst)."""
    if start >= len(dst):
        return dst
    k = min(len(src), len(dst) - start)
    dst[start:start + k] += src[:k] * gain
    return dst


def normalize(x: np.ndarray, peak: float = 0.89) -> np.ndarray:
    m = np.max(np.abs(x)) or 1.0
    y = x / m * peak
    loud = np.nonzero(np.abs(y) > 0.003)[0]
    if len(loud):
        y = y[: min(len(y), loud[-1] + int(0.05 * SR))]
    fade = min(len(y), int(0.01 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def tone(freqs, amps, decays, sec, detune=0.0, seed=0):
    t = t_axis(sec)
    out = np.zeros_like(t)
    rng = np.random.default_rng(seed)
    for f, a, dcy in zip(freqs, amps, decays):
        ph = rng.uniform(0, 2 * np.pi)
        out += a * np.sin(2 * np.pi * f * (1 + detune * rng.uniform(-1, 1)) * t + ph) * np.exp(-t / dcy)
    return out


# =========================================================================== instruments
def bell(f0=196.0, sec=4.5, bright=1.0, seed=1):
    ratios = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166, 5.433]
    amps = [0.55, 1.0, 0.75, 0.45, 0.6, 0.35 * bright, 0.25 * bright, 0.3 * bright, 0.18 * bright, 0.1 * bright]
    decays = [3.8, 2.8, 2.0, 1.6, 1.4, 0.9, 0.8, 0.6, 0.4, 0.3]
    x = tone([f0 * r for r in ratios], amps, decays, sec, detune=0.0015, seed=seed)
    strike = bandpass(noise(len(x), seed + 7), 2500, 1.2) * env_exp(len(x), 0.001, 0.02) * 0.6
    return x + strike


def choir(chord=(146.83, 220.0, 293.66, 369.99, 440.0), sec=3.0, vowel="a", attack=0.9, seed=3):
    t = t_axis(sec)
    rng = np.random.default_rng(seed)
    formants = {"a": [(730, 1.0, 80), (1090, 0.5, 90), (2440, 0.25, 120)],
                "o": [(570, 1.0, 70), (840, 0.45, 80), (2410, 0.2, 120)]}[vowel]
    voices = np.zeros_like(t)
    for f in chord:
        for k in range(3):                          # three singers per note
            vib = 1 + 0.006 * np.sin(2 * np.pi * (5.0 + rng.uniform(-0.6, 0.6)) * t + rng.uniform(0, 6))
            ph = 2 * np.pi * np.cumsum(f * (1 + rng.uniform(-0.004, 0.004)) * vib) / SR
            src = np.zeros_like(t)
            for h in range(1, 18):                  # band-limited saw
                if f * h > 7000:
                    break
                src += np.sin(h * ph) / h
            voices += src
    out = np.zeros_like(t)
    for fc, amp, bw in formants:
        out += amp * bandpass(voices, fc, q=fc / bw)
    breath = bandpass(noise(len(t), seed + 1), 2600, 1.0) * 0.04
    e = env_adsr(len(t), attack, 0.4, 0.85, sec * 0.35, sec - attack - 0.4 - sec * 0.35)
    return (out + breath) * e


def cloth_whoosh(sec=0.45, f_lo=300, f_hi=1500, seed=11, snap=True):
    n = int(sec * SR)
    x = noise(n, seed)
    tt = np.linspace(0, 1, n)
    center = f_lo + (f_hi - f_lo) * np.sin(np.pi * np.clip(tt * 1.1, 0, 1)) ** 1.5
    y = bandpass(x, center, q=1.1)
    flap = 1 + 0.55 * np.sin(2 * np.pi * (14 + 10 * tt) * tt * sec)
    y *= env_exp(n, sec * 0.35, sec * 0.25) * flap
    if snap:
        k = int(n * 0.62)
        crack = bandpass(noise(n - k, seed + 3), 2200, 0.8) * env_exp(n - k, 0.002, 0.035) * 2.2
        y[k:] += crack
    return y


def thump(f0=90, f1=42, sec=0.5, seed=4):
    t = t_axis(sec)
    f = f1 + (f0 - f1) * np.exp(-t * 14)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(len(t), 0.002, 0.16)
    dirt = onepole_lp(noise(len(t), seed), 900) * env_exp(len(t), 0.001, 0.07) * 1.5
    return body * 1.2 + dirt


def crackle(sec=1.5, density=40, seed=21):
    n = int(sec * SR)
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    for _ in range(int(density * sec)):
        p = rng.integers(0, n - 800)
        ln = rng.integers(80, 700)
        y[p:p + ln] += bandpass(rng.standard_normal(ln), rng.uniform(1500, 5000), 1.5) * np.exp(-np.arange(ln) / (ln * 0.25)) * rng.uniform(0.3, 1.0)
    return y


def fire_roar(sec=2.0, seed=31):
    n = int(sec * SR)
    base = onepole_lp(noise(n, seed), 600) * 2.0
    mid = bandpass(noise(n, seed + 1), 900, 0.7) * 0.6
    mod = 1 + 0.35 * onepole_lp(noise(n, seed + 2), 6) * 8
    return add_at((base + mid) * mod, crackle(sec, 55, seed + 3), 0, 0.8)


# =========================================================================== the sound set
def s_swing(v: int):
    return lambda: reverb(cloth_whoosh(0.42 + 0.05 * v, 260 + 60 * v, 1400 + 200 * v, seed=11 + v), 0.6, 0.12)


def s_snap():
    n = int(0.25 * SR)
    y = bandpass(noise(n, 5), 2600, 0.7) * env_exp(n, 0.001, 0.03) * 2
    add_at(y, cloth_whoosh(0.25, 600, 2400, seed=6, snap=False), 0, 0.5)
    return reverb(y, 0.5, 0.1)


def s_plant():
    y = thump(95, 40, 0.7)
    add_at(y, tone([823, 1247, 1968, 2650], [0.35, 0.28, 0.2, 0.12], [0.9, 0.7, 0.5, 0.3], 0.7, seed=8), 0)
    return reverb(y, 1.4, 0.28)


def s_path_form():
    notes = [587.33, 739.99, 880.0, 1174.66, 1479.98]
    sec = 1.4
    out = np.zeros(int(sec * SR))
    for i, f in enumerate(notes):
        start = int(i * 0.055 * SR)
        b = tone([f, f * 2.76, f * 5.4], [1.0, 0.35, 0.12], [0.6, 0.25, 0.1], sec - i * 0.055, seed=40 + i)
        b *= env_exp(len(b), 0.002, 0.5)
        add_at(out, b, start, 0.8 - i * 0.08)
    shimmer = bandpass(noise(len(out), 44), 6000, 1.5) * env_adsr(len(out), 0.2, 0.3, 0.3, 0.6, 0.3) * 0.08
    return reverb(out + shimmer, 2.2, 0.38)


def s_path_active():
    n = int(0.9 * SR)
    sw = bandpass(noise(n, 50), np.linspace(500, 3000, n), 1.4) * env_adsr(n, 0.25, 0.2, 0.5, 0.4, 0.05)
    gl = tone([1318.5, 1975.5], [0.3, 0.2], [0.5, 0.4], 0.9, seed=51)
    return reverb(sw + gl, 1.6, 0.3)


def s_path_reverse():
    n = int(1.1 * SR)
    tt = np.linspace(0, 1, n)
    swell = bandpass(noise(n, 60), 800 + 2500 * tt ** 2, 1.2) * tt ** 2.2
    f = 520 * (1 - 0.35 * np.sin(np.pi * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR
    bend = np.sin(ph) * 0.35 * env_adsr(n, 0.3, 0.2, 0.7, 0.3, 0.3)
    creak = np.zeros(n)
    for k in range(9):
        p = int((0.1 + k * 0.09) * n)
        ln = int(0.03 * SR)
        if p + ln < n:
            creak[p:p + ln] += bandpass(noise(ln, 61 + k), 300, 3) * np.hanning(ln) * 0.8
    return reverb(swell + bend + creak, 1.4, 0.3)


def s_bell_toll():
    return reverb(bell(146.83, 5.0, 1.0, 2), 3.2, 0.4)


def s_bell_high():
    return reverb(bell(392.0, 2.5, 0.8, 3), 2.0, 0.35)


def s_choir_light():
    return reverb(choir((146.83, 220.0, 293.66, 369.99, 440.0), 3.4, "a", 1.0, 3), 3.5, 0.45)


def s_choir_dark():
    return reverb(choir((110.0, 164.81, 220.0, 261.63, 329.63), 3.8, "o", 1.2, 5), 3.8, 0.5)


def s_fire_ignite():
    n = int(1.1 * SR)
    wh = onepole_lp(noise(n, 70), np.linspace(400, 3500, n)) * env_exp(n, 0.12, 0.35) * 2.2
    return reverb(add_at(wh, crackle(1.1, 50, 71), 0, 0.7), 1.0, 0.2)


def s_fire_roar():
    y = fire_roar(2.6, 80)
    y = y * env_adsr(len(y), 0.25, 0.4, 0.8, 0.9, 1.05)
    return reverb(y, 1.6, 0.25)


def s_impact():
    n = int(1.2 * SR)
    y = np.zeros(n)
    th = thump(80, 32, 1.0, 90)
    add_at(y, th, 0, 1.3)
    sh = tone([1567.98, 2349.32, 3135.96], [0.4, 0.3, 0.2], [0.8, 0.6, 0.4], 1.2, seed=91)
    y += sh * env_exp(n, 0.005, 0.5)
    y += bandpass(noise(n, 92), 3000, 0.9) * env_exp(n, 0.001, 0.06)
    return reverb(y, 2.0, 0.35)


def s_step(v: int):
    def f():
        n = int(0.22 * SR)
        clink = tone([1900 + 150 * v, 2870 + 120 * v, 4100], [0.5, 0.35, 0.2], [0.07, 0.05, 0.03], 0.22, seed=100 + v)
        th = thump(140, 70, 0.22, 101 + v) * 0.6
        return reverb(add_at(clink, th, 0), 0.5, 0.1)
    return f


def s_stake_rise():
    n = int(2.2 * SR)
    rumble = onepole_lp(noise(n, 110), 120) * 6 * env_adsr(n, 0.4, 0.4, 0.8, 0.6, 0.8)
    creak = np.zeros(n)
    for k in range(6):
        p = int((0.15 + k * 0.13) * n)
        ln = int(0.18 * SR)
        f = np.linspace(180 + 30 * k, 120, ln)
        creak[p:p + ln] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(ln) * 0.4 * (1 + np.sign(np.sin(np.arange(ln) * 0.31)))
    return reverb(rumble + creak, 1.4, 0.25)


def s_waystone():
    n = int(1.3 * SR)
    tt = np.linspace(0, 1, n)
    f = 900 + 900 * tt
    ph = 2 * np.pi * np.cumsum(f) / SR
    glide = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3.01 * ph)) * env_adsr(n, 0.02, 0.3, 0.4, 0.6, 0.3) * 0.5
    ch = tone([1760, 2637], [0.4, 0.25], [0.6, 0.5], 1.3, seed=120) * (tt > 0.45)
    return reverb(glide + ch, 1.8, 0.35)


def s_seraph():
    n = int(0.6 * SR)
    flut = bandpass(noise(n, 130), 1800, 2) * (0.6 + 0.4 * np.sign(np.sin(np.arange(n) / SR * 2 * np.pi * 22)))
    flut *= env_adsr(n, 0.05, 0.1, 0.6, 0.3, 0.15)
    hum = tone([1046.5, 1568.0], [0.25, 0.15], [0.6, 0.5], 0.6, seed=131)
    return reverb(flut * 0.6 + hum, 1.2, 0.3)


def s_seraph_burst():
    n = int(0.7 * SR)
    y = bandpass(noise(n, 140), 2400, 0.8) * env_exp(n, 0.002, 0.08) * 1.5
    y += tone([1318.5, 1975.5, 2637.0], [0.4, 0.3, 0.2], [0.4, 0.3, 0.2], 0.7, seed=141)
    return reverb(y, 1.2, 0.3)


def s_surge():
    n = int(1.0 * SR)
    tt = np.linspace(0, 1, n)
    y = bandpass(noise(n, 150), 400 + 2200 * np.sin(np.pi * tt), 1.2) * np.sin(np.pi * tt) ** 1.2 * 1.6
    tone_ = np.sin(2 * np.pi * np.cumsum(300 + 500 * np.sin(np.pi * tt)) / SR) * 0.15 * np.sin(np.pi * tt)
    return reverb(y + tone_, 1.0, 0.2)


def s_drag():
    n = int(1.0 * SR)
    y = bandpass(noise(n, 160), 700, 1.6) * (0.55 + 0.45 * np.abs(np.sin(np.arange(n) / SR * 2 * np.pi * 7)))
    y *= env_adsr(n, 0.05, 0.1, 0.9, 0.2, 0.65)
    return reverb(y, 0.8, 0.15)


def s_verdict():
    n = int(3.2 * SR)
    y = np.zeros(n)
    r = fire_roar(3.0, 170)
    r = r * env_exp(len(r), 0.05, 1.0) * 1.4
    add_at(y, r, 0)
    add_at(y, bell(110.0, 3.2, 1.2, 171), 0, 0.9)
    add_at(y, thump(70, 28, 1.0, 172), 0, 1.6)
    return reverb(y, 3.0, 0.35)


def s_death():
    sec = 5.5
    n = int(sec * SR)
    y = np.zeros(n)
    add_at(y, choir((146.83, 220.0, 293.66, 369.99, 440.0, 587.33), sec, "a", 1.6, 9), 0, 0.9)
    for i, f in enumerate((587.33, 739.99, 880.0, 1174.66)):
        b = bell(f, sec - 1.0 - i * 0.4, 0.6, 180 + i) * 0.25
        add_at(y, b, int((1.0 + i * 0.4) * SR))
    return reverb(y, 4.0, 0.5)


def s_phase():
    sec = 4.0
    n = int(sec * SR)
    y = np.zeros(n)
    add_at(y, choir((110.0, 164.81, 220.0, 261.63, 329.63), sec, "o", 0.7, 7), 0)
    r = fire_roar(sec - 1.2, 190)
    r = r * env_adsr(len(r), 0.6, 0.4, 0.8, 0.8, sec - 3.0) * 0.6
    add_at(y, r, int(1.2 * SR))
    add_at(y, bell(98.0, 3.5, 1.0, 191), 0, 0.7)
    return reverb(y, 3.5, 0.45)


def s_heart():
    n = int(1.6 * SR)
    y = np.zeros(n)
    for k, p in enumerate((0.0, 0.28, 0.9, 1.18)):
        th = thump(70, 40, 0.3, 200 + k) * (0.9 if k % 2 == 0 else 0.6)
        add_at(y, th, int(p * SR))
    return reverb(y, 1.2, 0.25)


SOUNDS: Dict[str, List[Callable[[], np.ndarray]]] = {
    "joan.banner.swing": [s_swing(0), s_swing(1), s_swing(2)],
    "joan.banner.snap": [s_snap],
    "joan.banner.plant": [s_plant],
    "joan.path.form": [s_path_form],
    "joan.path.active": [s_path_active],
    "joan.path.reverse": [s_path_reverse],
    "joan.bell.toll": [s_bell_toll],
    "joan.bell.high": [s_bell_high],
    "joan.choir.light": [s_choir_light],
    "joan.choir.dark": [s_choir_dark],
    "joan.fire.ignite": [s_fire_ignite],
    "joan.fire.roar": [s_fire_roar],
    "joan.impact": [s_impact],
    "joan.step": [s_step(0), s_step(1), s_step(2)],
    "joan.stake.rise": [s_stake_rise],
    "joan.waystone.turn": [s_waystone],
    "joan.seraph.fly": [s_seraph],
    "joan.seraph.burst": [s_seraph_burst],
    "joan.surge": [s_surge],
    "joan.drag": [s_drag],
    "joan.verdict": [s_verdict],
    "joan.death": [s_death],
    "joan.phase": [s_phase],
    "joan.heart": [s_heart],
}

# volume / pitch / distance settings per sound event
SETTINGS = {
    "joan.bell.toll": {"volume": 1.0, "max_distance": 64.0},
    "joan.choir.light": {"volume": 0.9, "max_distance": 64.0},
    "joan.choir.dark": {"volume": 0.9, "max_distance": 64.0},
    "joan.phase": {"volume": 1.0, "max_distance": 72.0},
    "joan.death": {"volume": 1.0, "max_distance": 72.0},
    "joan.verdict": {"volume": 1.0, "max_distance": 64.0},
    "joan.step": {"volume": 0.45, "max_distance": 16.0},
}


def write_wav(path: str, x: np.ndarray):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def build(rp_dir: str, cache_dir: str) -> Dict[str, List[str]]:
    """Render every sound to <rp>/sounds/joan/*.ogg (cached by name) and return name -> file stems."""
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to encode the sounds")
    os.makedirs(cache_dir, exist_ok=True)
    out_dir = os.path.join(rp_dir, "sounds", "joan")
    os.makedirs(out_dir, exist_ok=True)
    files: Dict[str, List[str]] = {}
    for name, gens in SOUNDS.items():
        stems = []
        for i, gen in enumerate(gens):
            stem = name.replace("joan.", "").replace(".", "_") + (f"_{i + 1}" if len(gens) > 1 else "")
            ogg_cache = os.path.join(cache_dir, stem + ".ogg")
            if not os.path.exists(ogg_cache):
                wav = os.path.join(cache_dir, stem + ".wav")
                write_wav(wav, normalize(gen()))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-c:a", "libvorbis",
                                "-q:a", "4", ogg_cache], check=True)
                os.remove(wav)
            shutil.copy(ogg_cache, os.path.join(out_dir, stem + ".ogg"))
            stems.append(f"sounds/joan/{stem}")
        files[name] = stems
    return files


def sound_definitions(files: Dict[str, List[str]]) -> dict:
    defs = {}
    for name, stems in files.items():
        st = SETTINGS.get(name, {})
        defs[name] = {
            "category": "hostile",
            "min_distance": 1.0,
            "max_distance": st.get("max_distance", 40.0),
            "sounds": [{"name": s, "volume": st.get("volume", 1.0), "load_on_low_memory": True} for s in stems],
        }
    return {"format_version": "1.20.20", "sound_definitions": defs}


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    f = build(sys.argv[1] if len(sys.argv) > 1 else "build/sound_test", "build/.soundcache")
    print(len(f), "sounds", round(time.time() - t0, 1), "s")
