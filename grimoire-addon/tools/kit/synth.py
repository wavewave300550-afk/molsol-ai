"""Original sound synthesis (numpy -> OGG Vorbis via ffmpeg).  No samples, no copyrighted melodies.

All generators return mono float arrays at SR.  Typical use inside an asset module:

    from kit import synth as sy
    sig = sy.mixdown([sy.choir(220, 2.0, "ah"), sy.bell(880, 1.5) * 0.4])
    sy.save(pack, "dw_chant1", sy.reverb(sig, 1.6, 0.35), volume=1.0, max_distance=48)

which registers the sound id  grimoire.dw_chant1  (played from scripts as sound(dim, "dw_chant1", loc)).
"""
from __future__ import annotations

import os
import subprocess
import wave

import numpy as np

SR = 32000
_rng = np.random.default_rng(20261113)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env(dur, a=0.01, d=0.1, s=0.7, r=0.2, hold=None):
    """ADSR envelope; hold defaults to the remaining time."""
    n = int(SR * dur)
    a_n, d_n, r_n = int(SR * a), int(SR * d), int(SR * r)
    s_n = max(0, n - a_n - d_n - r_n) if hold is None else int(SR * hold)
    e = np.concatenate([np.linspace(0, 1, max(a_n, 1)), np.linspace(1, s, max(d_n, 1)), np.full(s_n, s),
                        np.linspace(s, 0, max(r_n, 1))])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def decay(dur, tau):
    return np.exp(-t_axis(dur) / tau)


def fade(sig, a=0.005, r=0.02):
    n = len(sig)
    e = np.ones(n)
    an, rn = min(n, int(SR * a)), min(n, int(SR * r))
    if an:
        e[:an] = np.linspace(0, 1, an)
    if rn:
        e[-rn:] *= np.linspace(1, 0, rn)
    return sig * e


def sweep(f0, f1, dur, curve=1.0):
    """Instantaneous-frequency array from f0 to f1."""
    x = np.linspace(0, 1, int(SR * dur)) ** curve
    return f0 + (f1 - f0) * x


def osc(freq, dur=None, wave_="sine", phase=0.0):
    """Oscillator; freq may be a number or an array of instantaneous frequency."""
    f = np.full(int(SR * dur), float(freq)) if np.isscalar(freq) else np.asarray(freq, dtype=float)
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if wave_ == "sine":
        return np.sin(ph)
    if wave_ == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if wave_ == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    if wave_ == "square":
        return np.sign(np.sin(ph))
    raise ValueError(wave_)


def noise(dur):
    return _rng.standard_normal(int(SR * dur))


def shape(sig, gain_fn):
    """FFT-domain filter: gain_fn(freqs_hz) -> gain array."""
    spec = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    return np.fft.irfft(spec * gain_fn(f), len(sig))


def lowpass(sig, fc, order=2):
    return shape(sig, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def highpass(sig, fc, order=2):
    return shape(sig, lambda f: 1 - 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def bandpass(sig, fc, q=4.0):
    return shape(sig, lambda f: 1 / np.sqrt(1 + (q * (f / fc - fc / np.maximum(f, 1e-3))) ** 2))


def formants(sig, peaks):
    """peaks: [(freq, bandwidth, gain)] vocal-tract style resonances."""
    def g(f):
        out = np.zeros_like(f)
        for fc, bw, gn in peaks:
            out += gn / (1 + ((f - fc) / (bw / 2)) ** 2)
        return out
    return shape(sig, g)


VOWELS = {
    "ah": [(730, 120, 1.0), (1090, 140, 0.5), (2440, 200, 0.25), (3400, 300, 0.1)],
    "oh": [(500, 110, 1.0), (850, 130, 0.45), (2500, 220, 0.2), (3300, 300, 0.08)],
    "oo": [(320, 90, 1.0), (800, 120, 0.3), (2300, 220, 0.12)],
    "ee": [(280, 80, 1.0), (2250, 180, 0.5), (2900, 240, 0.25)],
    "eh": [(530, 110, 1.0), (1840, 170, 0.45), (2480, 220, 0.2)],
}


def choir(freq, dur, vowel="ah", voices=5, vibrato=5.2, depth=0.006, attack=0.25, release=0.5, bright=1.0):
    """Layered wordless voices (formant-shaped harmonics, detuned, with vibrato)."""
    t = t_axis(dur)
    out = np.zeros(len(t))
    for vi in range(voices):
        det = 1 + (vi - (voices - 1) / 2) * 0.0035 + _rng.normal(0, 0.0008)
        vib = 1 + depth * np.sin(2 * np.pi * (vibrato + vi * 0.31) * t + vi)
        f = freq * det * vib
        ph = 2 * np.pi * np.cumsum(f) / SR + vi * 1.3
        sig = np.zeros(len(t))
        for h in range(1, 28):
            if freq * h > SR / 2.2:
                break
            sig += np.sin(ph * h) / (h ** (1.1 / bright))
        out += sig + 0.015 * noise(dur)
    out = formants(out, VOWELS[vowel])
    return norm(out * env(dur, attack, 0.1, 0.9, release))


def bell(freq, dur, bright=1.0, inharm=1.0):
    """Struck bell / chime: inharmonic partials with independent decay."""
    t = t_axis(dur)
    parts = [(0.56, 1.0, 1.6), (0.92, 0.7, 1.3), (1.19, 0.5, 1.0), (1.71, 0.4, 0.7), (2.0, 0.6, 0.9), (2.74, 0.35, 0.5),
             (3.0, 0.25, 0.45), (4.07, 0.2, 0.3), (5.2, 0.12, 0.22)]
    out = np.zeros(len(t))
    for ratio, amp, tau in parts:
        f = freq * (1 + (ratio - 1) * inharm)
        if f < SR / 2.2:
            out += amp * np.sin(2 * np.pi * f * t + ratio) * np.exp(-t / (tau * dur * 0.45)) * (bright if ratio > 2 else 1)
    return norm(fade(out, 0.001, 0.05))


def pluck(freq, dur, bright=0.5):
    """Karplus-like plucked/glassy tone via decaying harmonics."""
    t = t_axis(dur)
    out = np.zeros(len(t))
    for h in range(1, 14):
        if freq * h > SR / 2.2:
            break
        out += np.sin(2 * np.pi * freq * h * t) * np.exp(-t * (2.5 + h * (3.5 - 3 * bright))) / h
    return norm(fade(out, 0.001, 0.03))


def pad(freq, dur, voices=4, wave_="saw", cutoff=1800, attack=0.4, release=0.6):
    out = np.zeros(int(SR * dur))
    for i in range(voices):
        out += osc(freq * (1 + (i - voices / 2) * 0.004), dur, wave_, phase=i * 1.7)
    return norm(lowpass(out, cutoff) * env(dur, attack, 0.1, 0.9, release))


def roar(dur, f0=90, f1=55, growl=28, rough=0.6, formant=(480, 1100), breath=0.35, bend=0.25):
    """Creature vocalisation: pulsed sawtooth through moving formants plus breath noise."""
    t = t_axis(dur)
    x = t / dur
    f = f0 + (f1 - f0) * x + f0 * bend * np.sin(np.pi * x)
    f = f * (1 + 0.04 * np.sin(2 * np.pi * 6.5 * t) + 0.03 * lowpass(noise(dur), 30) * 3)
    src = osc(f, wave_="saw") + 0.5 * osc(f * 0.5, wave_="square")
    src *= 1 - rough * 0.5 * (1 + np.sign(np.sin(2 * np.pi * growl * t + 2 * np.sin(2 * np.pi * 3 * t))))
    voiced = formants(src, [(formant[0], 180, 1.0), (formant[1], 260, 0.6), (2600, 500, 0.25)])
    br = bandpass(noise(dur), formant[1] * 1.3, 1.2) * breath
    e = env(dur, 0.08 * dur, 0.2 * dur, 0.75, 0.35 * dur)
    return norm((norm(voiced) + br) * e)


def wind(dur, f0=400, f1=1400, q=2.0, gust=0.5):
    """Filtered noise with a moving band (wind / whoosh).  The sweep is done in short blocks."""
    n = int(SR * dur)
    src = noise(dur)
    out = np.zeros(n)
    blk = int(SR * 0.05)
    win = np.hanning(blk * 2)
    for i in range(0, n, blk):
        seg = src[max(0, i - blk // 2):i + blk * 2 - blk // 2]
        if len(seg) < blk * 2:
            seg = np.pad(seg, (0, blk * 2 - len(seg)))
        fc = f0 + (f1 - f0) * (i / n)
        y = bandpass(seg * win, fc, q)
        a, b = max(0, i - blk // 2), min(n, i - blk // 2 + blk * 2)
        out[a:b] += y[:b - a]
    t = t_axis(dur)
    out *= 1 + gust * np.sin(2 * np.pi * 0.9 * t + 1.0) * np.sin(2 * np.pi * 0.37 * t)
    return norm(fade(out, 0.03, 0.08))


def whoosh(dur, f0=300, f1=3000, q=1.6):
    w = wind(dur, f0, f1, q, gust=0.0)
    x = np.linspace(0, 1, len(w))
    return norm(w * np.sin(np.pi * x) ** 1.5)


def thump(dur=0.6, f0=110, f1=38, click=0.3):
    """Heavy low impact: pitch-dropping sine + noise burst."""
    t = t_axis(dur)
    body = osc(sweep(f0, f1, dur, 0.4)) * np.exp(-t / (dur * 0.28))
    nz = lowpass(noise(dur), 900) * np.exp(-t / 0.05) * click
    return norm(fade(body + nz, 0.001, 0.05))


def crack(dur=0.5, bright=6000, grains=14):
    """Ice / stone / porcelain fracture: sparse sharp clicks with ringing."""
    n = int(SR * dur)
    out = np.zeros(n)
    for _ in range(grains):
        i = int(_rng.random() ** 1.8 * n * 0.9)
        L = int(SR * _rng.uniform(0.004, 0.03))
        f = _rng.uniform(bright * 0.4, bright)
        tt = np.arange(L) / SR
        g = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.004) * _rng.uniform(0.4, 1.0)
        out[i:i + L] += g[:n - i]
    out += highpass(noise(dur), bright * 0.5) * np.exp(-t_axis(dur) / 0.03) * 0.5
    return norm(fade(out, 0.0, 0.02))


def rumble(dur, fc=70, wobble=3.0):
    t = t_axis(dur)
    out = lowpass(noise(dur), fc * 1.6) * (0.7 + 0.3 * np.sin(2 * np.pi * wobble * t))
    out += 0.5 * np.sin(2 * np.pi * fc * 0.5 * t + np.sin(2 * np.pi * 1.3 * t))
    return norm(out * env(dur, 0.15 * dur, 0.1, 0.9, 0.3 * dur))


def creak(dur, f0=180, f1=320, jitter=0.25):
    """Door / wood creak: stick-slip sawtooth with wandering pitch."""
    t = t_axis(dur)
    wand = np.cumsum(lowpass(noise(dur), 12)) / SR * 60
    f = sweep(f0, f1, dur) * (1 + jitter * np.tanh(wand))
    src = osc(f, wave_="saw") * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * (9 + 6 * np.sin(2 * np.pi * 0.7 * t)) * t)))
    out = formants(src, [(900, 300, 1.0), (2100, 500, 0.6), (3600, 800, 0.3)])
    return norm(out * env(dur, 0.05, 0.1, 0.85, 0.15))


def water(dur, bubbles=40, base=500):
    n = int(SR * dur)
    out = lowpass(noise(dur), 1400) * 0.25
    for _ in range(bubbles):
        i = int(_rng.random() * n * 0.95)
        L = int(SR * _rng.uniform(0.03, 0.12))
        f0 = _rng.uniform(base, base * 4)
        tt = np.arange(L) / SR
        g = np.sin(2 * np.pi * (f0 + f0 * 1.5 * tt / (L / SR)) * tt) * np.exp(-tt / 0.03) * _rng.uniform(0.2, 0.7)
        out[i:i + L] += g[:n - i]
    return norm(fade(out, 0.03, 0.1))


def heartbeat(dur=1.0, f=52):
    out = np.zeros(int(SR * dur))
    for at, amp in ((0.0, 1.0), (0.28, 0.7)):
        b = thump(0.35, f * 1.7, f * 0.7, 0.1) * amp
        i = int(SR * at)
        out[i:i + len(b)] += b[:len(out) - i]
    return norm(out)


def shimmer(dur, base=1800, n=18, spread=2.2):
    """Glittering cloud of tiny chimes."""
    out = np.zeros(int(SR * dur))
    for _ in range(n):
        at = _rng.random() * dur * 0.85
        f = base * (spread ** _rng.random())
        b = pluck(f, min(0.5, dur - at), 0.8) * _rng.uniform(0.2, 0.8)
        i = int(SR * at)
        out[i:i + len(b)] += b[:len(out) - i]
    return norm(out)


def scribble(dur, strokes=6):
    """Quill / chalk writing: short band-limited noise strokes."""
    out = np.zeros(int(SR * dur))
    for k in range(strokes):
        L = dur / strokes * _rng.uniform(0.5, 0.9)
        seg = bandpass(noise(L), _rng.uniform(2500, 5200), 1.5) * np.hanning(int(SR * L))
        i = int(SR * dur * k / strokes)
        out[i:i + len(seg)] += seg[:len(out) - i]
    return norm(out)


def reverb(sig, seconds=1.4, mix=0.3, tone=5000, predelay=0.02):
    """Convolution reverb with a synthetic decaying-noise impulse (cathedral-ish for long tails)."""
    n = int(SR * seconds)
    ir = _rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * seconds / 5.5))
    ir = lowpass(ir, tone)
    ir = np.concatenate([np.zeros(int(SR * predelay)), ir])
    m = len(sig) + len(ir) - 1
    size = 1 << (m - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(sig, size) * np.fft.rfft(ir, size), size)[:m]
    wet = wet / (np.max(np.abs(wet)) + 1e-9) * (np.max(np.abs(sig)) + 1e-9)
    dry = np.pad(sig, (0, m - len(sig)))
    return dry * (1 - mix) + wet * mix


def norm(sig, peak=0.92):
    m = np.max(np.abs(sig)) + 1e-9
    return sig / m * peak


def at(base_len, *parts):
    """Mix (offset_seconds, signal[, gain]) parts into one buffer of base_len seconds (auto-extends)."""
    n = int(SR * base_len)
    for p in parts:
        n = max(n, int(SR * p[0]) + len(p[1]))
    out = np.zeros(n)
    for p in parts:
        i = int(SR * p[0])
        out[i:i + len(p[1])] += p[1] * (p[2] if len(p) > 2 else 1.0)
    return out


def mixdown(sigs, gains=None):
    n = max(len(s) for s in sigs)
    out = np.zeros(n)
    for i, s in enumerate(sigs):
        out[:len(s)] += s * (gains[i] if gains else 1.0)
    return norm(out)


def pitch(sig, ratio):
    """Resample (changes pitch and length together)."""
    n = int(len(sig) / ratio)
    return np.interp(np.linspace(0, len(sig) - 1, n), np.arange(len(sig)), sig)


def save(pack, name, sig, volume=1.0, pitch_=1.0, max_distance=48.0, min_distance=3.0, category="neutral",
         variants=None, quality=3):
    """Encode and register sound id grimoire.<name>.  variants: extra signals as random alternates."""
    files = []
    for i, s in enumerate([sig] + list(variants or [])):
        fn = name if i == 0 else f"{name}_{i + 1}"
        d = os.path.join(pack.rp, "sounds", "grimoire")
        os.makedirs(d, exist_ok=True)
        wav = os.path.join(d, fn + ".wav")
        s = fade(norm(np.asarray(s, dtype=float)), 0.003, 0.02)
        pcm = (np.clip(s, -1, 1) * 32767).astype("<i2")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality),
                        "-ac", "1", os.path.join(d, fn + ".ogg")], check=True)
        os.remove(wav)
        files.append(fn)
    pack.sound(f"grimoire.{name}", files, category=category, volume=volume, pitch=pitch_, max_distance=max_distance,
               min_distance=min_distance)
    return f"grimoire.{name}"
