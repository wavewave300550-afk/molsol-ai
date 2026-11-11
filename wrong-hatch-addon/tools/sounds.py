"""
Sound design for The Wrong Hatch.

Signature sounds are synthesised here (numpy -> wav -> ffmpeg/libvorbis .ogg),
the rest re-use vanilla sound files with new pitch/volume in
sound_definitions.json (every vanilla path is checked by tools/validate.py).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _env(n, attack=0.005, decay=0.3):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / max(decay, 1e-4))


def _noise(n, rng):
    return rng.uniform(-1, 1, n)


def _lowpass(x, k):
    """crude one-pole low pass, k in (0,1] (smaller = darker)."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def _norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def crack(rng, dur=0.7, n_snaps=9, deep=False):
    out = np.zeros(int(SR * dur))
    for _ in range(n_snaps):
        start = int(rng.uniform(0, dur * 0.75) * SR)
        ln = int(SR * rng.uniform(0.01, 0.05))
        snap = _noise(ln, rng) * _env(ln, 0.0005, rng.uniform(0.004, 0.015))
        snap = snap - _lowpass(snap, 0.15)          # high-passed: brittle shell
        end = min(len(out), start + ln)
        out[start:end] += snap[:end - start] * rng.uniform(0.4, 1.0)
    if deep:
        t = _t(dur)
        out += np.sin(2 * np.pi * 70 * t) * _env(len(t), 0.002, 0.12) * 0.6
    return _norm(out)


def core_hum(rng, dur=1.4):
    t = _t(dur)
    f = 70 + (230 - 70) * (t / dur) ** 1.6
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3.01 * ph)
    x *= (0.6 + 0.4 * np.sin(2 * np.pi * (6 + 10 * t / dur) * t))
    x *= np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return _norm(x)


def beam(rng, dur=1.0):
    t = _t(dur)
    saw = ((t * 110) % 1.0) * 2 - 1
    x = saw * 0.6 + np.sin(2 * np.pi * 220 * t) * 0.4 + _noise(len(t), rng) * 0.15
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 13 * t)
    fade = np.clip(np.minimum(t, dur - t) / 0.02, 0, 1)
    return _norm(x * fade, 0.7)


def nova(rng, dur=2.6):
    t = _t(dur)
    boom = np.sin(2 * np.pi * (45 + 30 * np.exp(-t * 6)) * t) * _env(len(t), 0.003, 0.7)
    burst = _lowpass(_noise(len(t), rng), 0.08) * _env(len(t), 0.002, 0.35) * 3
    chimes = sum(np.sin(2 * np.pi * f * t) * _env(len(t), 0.01, 0.9) * 0.18 for f in (880, 1320, 1760, 2217))
    return _norm(boom + burst + chimes + crack(rng, dur, 14) * 0.3)


def pulse(rng, dur=0.7):
    t = _t(dur)
    x = (np.sin(2 * np.pi * 660 * t) + 0.6 * np.sin(2 * np.pi * 990 * t)) * _env(len(t), 0.004, 0.25)
    x += np.sin(2 * np.pi * 90 * t) * _env(len(t), 0.002, 0.08)
    return _norm(x)


def whoosh(rng, dur=0.5, k0=0.03, k1=0.35):
    n = int(SR * dur)
    src = _noise(n, rng)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        k = k0 + (k1 - k0) * np.sin(np.pi * i / n)
        acc += k * (src[i] - acc)
        y[i] = acc
    return _norm(y * np.sin(np.pi * np.arange(n) / n))


def slash(rng):
    w = whoosh(rng, 0.45, 0.05, 0.6)
    t = _t(0.45)
    ring = np.sin(2 * np.pi * 1900 * t) * _env(len(t), 0.002, 0.12) * 0.35
    return _norm(w + ring)


def scrape(rng, dur=0.35):
    n = int(SR * dur)
    x = _lowpass(_noise(n, rng), 0.25) * (0.5 + 0.5 * (rng.random(n) > 0.6))
    return _norm(x * np.sin(np.pi * np.arange(n) / n) ** 0.5)


def fluff(rng, dur=0.6):
    return _norm(_lowpass(_noise(int(SR * dur), rng), 0.05) * np.sin(np.pi * _t(dur) / dur), 0.6)


def peck(rng):
    t = _t(0.12)
    x = _noise(len(t), rng) * _env(len(t), 0.0005, 0.01) + np.sin(2 * np.pi * 300 * t) * _env(len(t), 0.001, 0.03)
    return _norm(x)


SYNTH = {
    "crack": lambda r: crack(r),
    "crack_big": lambda r: crack(r, 1.2, 22, deep=True),
    "core_hum": core_hum,
    "beam": beam,
    "nova": nova,
    "pulse": pulse,
    "whoosh": lambda r: whoosh(r),
    "slash": slash,
    "scrape": scrape,
    "fluff": fluff,
    "peck": peck,
}


def write_ogg(samples: np.ndarray, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "s.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(samples, -1, 1) * 32000).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "4", path],
                       check=True)


def build(rp_root: str) -> dict:
    """Write the .ogg files into the RP and return the sound_definitions dict."""
    rng = np.random.default_rng(2026)
    for name, fn in SYNTH.items():
        write_ogg(fn(rng), os.path.join(rp_root, "sounds", "wrong_hatch", f"{name}.ogg"))

    def own(*names, **kw):
        return [dict({"name": f"sounds/wrong_hatch/{n}"}, **kw) for n in names]

    def van(*paths, **kw):
        return [dict({"name": p}, **kw) for p in paths]

    chicken = ("sounds/mob/chicken/say1", "sounds/mob/chicken/say2")
    defs = {
        "wrong_hatch.crow": {"category": "hostile", "max_distance": 72,
                             "sounds": van(*chicken, pitch=0.48, volume=1.0)},
        "wrong_hatch.cluck": {"category": "hostile", "max_distance": 32,
                              "sounds": van(*chicken, pitch=0.62, volume=0.8)},
        "wrong_hatch.hurt": {"category": "hostile", "max_distance": 32,
                             "sounds": van("sounds/mob/chicken/hurt1", "sounds/mob/chicken/hurt2", pitch=0.55)},
        "wrong_hatch.step": {"category": "hostile", "max_distance": 24,
                             "sounds": van("sounds/mob/ravager/step1", "sounds/mob/ravager/step2",
                                           "sounds/mob/ravager/step3", pitch=0.85, volume=0.55)},
        "wrong_hatch.flap": {"category": "hostile", "max_distance": 48,
                             "sounds": van("sounds/mob/enderdragon/wings1", "sounds/mob/enderdragon/wings2",
                                           "sounds/mob/enderdragon/wings3", pitch=1.15, volume=1.6)},
        "wrong_hatch.chick": {"category": "hostile", "max_distance": 16,
                              "sounds": van("sounds/mob/baby_chicken/ambient1", "sounds/mob/baby_chicken/ambient2",
                                            pitch=0.8, volume=0.8)},
        "wrong_hatch.crack": {"category": "hostile", "max_distance": 32, "sounds": own("crack")},
        "wrong_hatch.crack_big": {"category": "hostile", "max_distance": 64, "sounds": own("crack_big", volume=1.0)},
        "wrong_hatch.charge": {"category": "hostile", "max_distance": 48, "sounds": own("core_hum")},
        "wrong_hatch.beam": {"category": "hostile", "max_distance": 40, "sounds": own("beam", volume=0.7)},
        "wrong_hatch.nova": {"category": "hostile", "max_distance": 96, "sounds": own("nova")},
        "wrong_hatch.pulse": {"category": "hostile", "max_distance": 48, "sounds": own("pulse")},
        "wrong_hatch.wing_whoosh": {"category": "hostile", "max_distance": 32, "sounds": own("whoosh")},
        "wrong_hatch.guillotine": {"category": "hostile", "max_distance": 40, "sounds": own("slash")},
        "wrong_hatch.scratch": {"category": "hostile", "max_distance": 24, "sounds": own("scrape")},
        "wrong_hatch.fluff": {"category": "hostile", "max_distance": 24, "sounds": own("fluff")},
        "wrong_hatch.molt": {"category": "hostile", "max_distance": 32, "sounds": own("fluff", pitch=0.7, volume=1.0)},
        "wrong_hatch.peck": {"category": "hostile", "max_distance": 24, "sounds": own("peck")},
        "wrong_hatch.shell_close": {"category": "hostile", "max_distance": 32, "sounds": own("crack", pitch=0.6)},
    }
    return {"format_version": "1.20.20", "sound_definitions": defs}
