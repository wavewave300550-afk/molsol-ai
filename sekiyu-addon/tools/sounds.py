"""
Procedural sound design for the Sekiyu Sekiyu no Mi add-on (helpers shared with the Jōki add-on).

Every sound is synthesised from noise and oscillators (no samples are copied from anywhere),
written as WAV and encoded to Ogg Vorbis with ffmpeg.

    python3 tools/sounds.py <out_dir>       -> <out_dir>/<name>.ogg  (+ prints the list)

Building blocks: band-limited noise (FFT-shaped), pitch-swept tones, metallic partials,
and a two-tone steam whistle for the overheat alarm.
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 22050
RNG = np.random.default_rng(1234)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def band_noise(sec, lo, hi, tilt=0.0, seed=None):
    """White noise shaped to a soft band [lo, hi] Hz (gaussian skirts on a log axis)."""
    rng = np.random.default_rng(seed) if seed is not None else RNG
    n = int(SR * sec)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    lf = np.log2(np.maximum(f, 1))
    c = (np.log2(lo) + np.log2(hi)) / 2
    w = (np.log2(hi) - np.log2(lo)) / 2
    gain = np.exp(-((lf - c) / max(w, 0.1)) ** 4) * (np.maximum(f, 1) / 1000.0) ** tilt
    out = np.fft.irfft(spec * gain, n)
    return out / (np.abs(out).max() + 1e-9)


def env(n, attack, release, hold=0.0, curve=2.0):
    """Attack / hold / exponential-ish release envelope (seconds)."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.clip(1 - (t - attack - hold) / max(release, 1e-4), 0, 1) ** curve
    return a * np.where(t < attack + hold, 1.0, r)


def sweep_noise(sec, bands, seed=None):
    """Crossfade between successive noise bands over time: [(lo, hi), ...]."""
    n = int(SR * sec)
    out = np.zeros(n)
    k = len(bands)
    for i, (lo, hi) in enumerate(bands):
        layer = band_noise(sec, lo, hi, seed=None if seed is None else seed + i)
        centre = i / max(1, k - 1)
        w = np.clip(1 - np.abs(np.linspace(0, 1, n) - centre) * (k - 1 if k > 1 else 1), 0, 1)
        out += layer * w
    return out / (np.abs(out).max() + 1e-9)


def tone(sec, f0, f1=None, kind="sine"):
    f1 = f0 if f1 is None else f1
    t = t_axis(sec)
    freq = f0 * (f1 / f0) ** (t / max(sec, 1e-6))
    ph = 2 * np.pi * np.cumsum(freq) / SR
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    return np.sign(np.sin(ph)) * 0.6


def thump(sec=0.35, f0=95, f1=38):
    n = int(SR * sec)
    return tone(sec, f0, f1) * env(n, 0.003, sec - 0.003, curve=3) + band_noise(sec, 800, 4000) * env(n, 0.001, 0.03) * 0.3


def clank(sec=0.5, base=420.0, seed=0):
    """Inharmonic metal partials (bronze pipe / valve wheel)."""
    rng = np.random.default_rng(seed)
    t = t_axis(sec)
    out = np.zeros_like(t)
    for ratio, amp, dec in ((1.0, 1.0, 9), (2.76, 0.6, 14), (5.40, 0.35, 20), (8.93, 0.2, 28)):
        f = base * ratio * rng.uniform(0.98, 1.02)
        out += amp * np.sin(2 * np.pi * f * t) * np.exp(-dec * t)
    out += band_noise(sec, 2000, 7000) * np.exp(-60 * t) * 0.5
    return out / np.abs(out).max()


def whistle(sec, f=880.0, vibrato=5.5, rise=0.12):
    """Two-tone steam whistle (a minor-third chord) with breath noise and a pitch scoop."""
    t = t_axis(sec)
    scoop = 1 - 0.06 * np.exp(-t / rise)
    vib = 1 + 0.006 * np.sin(2 * np.pi * vibrato * t)
    out = np.zeros_like(t)
    for ratio, amp in ((1.0, 1.0), (1.19, 0.8), (2.0, 0.25), (2.38, 0.18)):
        ph = 2 * np.pi * np.cumsum(f * ratio * scoop * vib) / SR
        out += amp * np.sin(ph)
    out = out / np.abs(out).max()
    breath = band_noise(sec, f * 0.8, f * 3.5)
    return out * 0.8 + breath * 0.35


def norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak


def fade(x, ms=12):
    k = min(len(x) // 2, int(SR * ms / 1000))
    x = x.copy()
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    return x


# --------------------------------------------------------------------------- the sound set


def fit(x, n):
    """Pad / trim a sound to n samples so layers of different lengths can be mixed."""
    out = np.zeros(n)
    out[: min(n, len(x))] = x[:n]
    return out


def glop(sec=0.35, f0=320, f1=90, seed=0):
    """Viscous oil 'glop': a fast downward pitch sweep with a wet noise burst."""
    n = int(SR * sec)
    t = t_axis(sec)
    bub = tone(sec, f0, f1) * np.exp(-t * 14)
    wet = band_noise(sec, 300, 2600, seed=seed) * env(n, 0.002, sec * 0.6, curve=2.4)
    return bub * 0.8 + wet * 0.5


def s_splash(v):
    sec = 0.6
    out = np.zeros(int(SR * sec))
    rng = np.random.default_rng(200 + v)
    for k in range(5):
        g = glop(0.3, rng.uniform(250, 520), rng.uniform(70, 140), seed=210 + v * 7 + k)
        a = int(SR * rng.uniform(0, 0.22))
        out[a:a + len(g)] += g[: len(out) - a] * rng.uniform(0.5, 1)
    return out


def s_gurgle(v):
    sec = 0.9
    out = band_noise(sec, 120, 700, seed=220 + v) * 0.4 * env(int(SR * sec), 0.05, 0.6, hold=0.2)
    rng = np.random.default_rng(221 + v)
    for k in range(7):
        g = glop(0.22, rng.uniform(180, 380), rng.uniform(60, 120), seed=230 + k)
        a = int(SR * rng.uniform(0, 0.65))
        out[a:a + len(g)] += g[: len(out) - a] * 0.6
    return out


def s_slurp(v):
    sec = 0.8
    n = int(SR * sec)
    return sweep_noise(sec, [(1800, 5000), (400, 1600), (120, 500)], seed=240) * env(n, 0.02, 0.7, curve=1.6) + glop(sec, 500, 60, 241) * 0.6


def s_reform(v):
    sec = 0.9
    n = int(SR * sec)
    return sweep_noise(sec, [(150, 500), (500, 1800), (1500, 5000)], seed=250) * env(n, 0.05, 0.4, hold=0.4) + glop(sec, 90, 380, 251) * 0.5


def s_tide(v):
    sec = 2.0
    n = int(SR * sec)
    roar = sweep_noise(sec, [(80, 400), (200, 1400), (300, 2400)], seed=260) * env(n, 0.25, 1.2, hold=0.4, curve=1.4)
    g = np.zeros(n)
    gl = s_gurgle(0)
    g[: min(n, len(gl))] = gl[:n]
    return roar + g * 0.5


def s_rumble(v):
    sec = 0.9
    n = int(SR * sec)
    return band_noise(sec, 30, 160, seed=270) * env(n, 0.3, 0.3, hold=0.3) + fit(s_gurgle(1), n) * 0.4


def s_erupt(v):
    sec = 1.4
    n = int(SR * sec)
    boom = tone(sec, 70, 30) * env(n, 0.003, 0.9, curve=2.4)
    blast = sweep_noise(sec, [(200, 1500), (600, 4000), (300, 2000)], seed=280) * env(n, 0.01, 1.2, hold=0.1, curve=1.5)
    sp = np.zeros(n)
    ss = s_splash(1)
    sp[: min(n, len(ss))] = ss[:n]
    return boom + blast * 0.8 + sp * 0.4


def s_squelch(v):
    sec = 0.7
    n = int(SR * sec)
    return glop(sec, 260, 50, 290) + band_noise(sec, 200, 1200, seed=291) * env(n, 0.01, 0.6, curve=1.5) * 0.6


def s_jet(v):
    sec = 0.6
    n = int(SR * sec)
    whoosh = sweep_noise(sec, [(300, 1500), (900, 4500)], seed=300 + v) * env(n, 0.005, 0.5, curve=2)
    g = np.zeros(n)
    gl = glop(0.3, 300, 80, 301)
    g[: len(gl)] = gl
    return whoosh + g * 0.6


def s_hiss(v):
    sec = 1.1
    n = int(SR * sec)
    t = t_axis(sec)
    hiss = band_noise(sec, 2500, 8500, seed=310 + v) * env(n, 0.08, 0.8, hold=0.15, curve=1.4)
    rattle = band_noise(sec, 400, 1500, seed=311) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 22 * t))) * env(n, 0.05, 0.9) * 0.25
    return hiss + rattle


def s_bite(v):
    sec = 0.5
    n = int(SR * sec)
    snap = band_noise(sec, 800, 6000, seed=320) * env(n, 0.001, 0.05, curve=3)
    return snap + thump(sec, 120, 45) * 0.8 + glop(sec, 300, 70, 321) * 0.5 * env(n, 0.05, 0.4)


def s_ignite(v):
    """The 'whoomp' of crude catching fire."""
    sec = 1.1
    n = int(SR * sec)
    whoomp = sweep_noise(sec, [(60, 300), (200, 1200), (600, 3000)], seed=330 + v) * env(n, 0.06, 0.9, hold=0.05, curve=1.6)
    return whoomp + tone(sec, 50, 90) * env(n, 0.05, 0.6) * 0.6


def s_crackle(v):
    sec = 1.6
    n = int(SR * sec)
    rng = np.random.default_rng(340 + v)
    clicks = (rng.random(n) > 0.997).astype(float) * rng.uniform(0.3, 1, n)
    clicks = np.convolve(clicks, np.exp(-np.arange(80) / 12), mode="same")
    bed = band_noise(sec, 200, 2500, seed=341 + v) * 0.35
    return (clicks * 0.9 + bed) * env(n, 0.1, 0.4, hold=1.0)


def s_inferno_rise(v):
    sec = 1.4
    n = int(SR * sec)
    rumble = band_noise(sec, 30, 200, seed=350) * np.linspace(0.3, 1, n)
    rise = sweep_noise(sec, [(100, 500), (300, 1500), (800, 4000)], seed=351) * np.linspace(0, 1, n) ** 2
    return (rumble + rise * 0.8 + fit(s_gurgle(2), n) * 0.4) * env(n, 0.05, 0.1, hold=1.2)


def s_inferno_blast(v):
    sec = 2.6
    n = int(SR * sec)
    boom = tone(sec, 55, 22) * env(n, 0.003, 1.6, curve=2.2)
    blast = band_noise(sec, 80, 6000, seed=360) * env(n, 0.002, 1.2, curve=2)
    roar = sweep_noise(sec, [(100, 900), (300, 2400), (150, 1200)], seed=361) * env(n, 0.1, 2.2, hold=0.2, curve=1.2)
    return boom * 1.2 + blast * 0.9 + roar * 0.8


def s_dodge(v):
    sec = 0.45
    n = int(SR * sec)
    return glop(sec, 600, 120, 370 + v) * 0.8 + sweep_noise(sec, [(3000, 8000), (800, 3000)], seed=371) * env(n, 0.003, 0.35) * 0.5


def s_melt(v):
    sec = 1.2
    n = int(SR * sec)
    return sweep_noise(sec, [(2000, 6000), (500, 2000), (100, 600)], seed=380) * env(n, 0.05, 1.0, hold=0.1, curve=1.3) + fit(s_gurgle(3), n) * 0.5


def s_sealed(v):
    sec = 0.8
    n = int(SR * sec)
    return band_noise(sec, 200, 900, seed=390) * env(n, 0.01, 0.6) + tone(sec, 300, 120) * env(n, 0.01, 0.5) * 0.4


def s_deny(v):
    sec = 0.3
    n = int(SR * sec)
    return glop(sec, 200, 80, 400) * 0.7 + band_noise(sec, 300, 900, seed=401) * env(n, 0.002, 0.15) * 0.3


def s_click(v):
    return glop(0.16, 900, 400, 410)


def s_awaken(v):
    sec = 3.0
    n = int(SR * sec)
    hb = np.zeros(n)
    for pos in (0.0, 0.35, 1.0, 1.3):
        k = int(SR * pos)
        b = thump(0.3, 70, 30)
        hb[k:k + len(b)] += b[: n - k]
    flood = sweep_noise(sec, [(60, 300), (200, 1200), (300, 2000)], seed=420) * np.linspace(0, 1, n) ** 2
    ign = np.zeros(n)
    k = int(SR * 2.0)
    w = s_ignite(1)
    ign[k:k + len(w)] += w[: n - k]
    return hb * 0.9 + flood * 0.6 * env(n, 0.1, 0.5, hold=2.3) + ign * 0.7


SOUNDS = {
    "sekiyu.oil.splash": (s_splash, 3, 0.9),
    "sekiyu.oil.gurgle": (s_gurgle, 2, 0.8),
    "sekiyu.oil.slurp": (s_slurp, 1, 0.9),
    "sekiyu.oil.reform": (s_reform, 1, 0.9),
    "sekiyu.tide.roar": (s_tide, 1, 1.0),
    "sekiyu.geyser.rumble": (s_rumble, 1, 1.0),
    "sekiyu.geyser.erupt": (s_erupt, 1, 1.0),
    "sekiyu.prison.squelch": (s_squelch, 1, 1.0),
    "sekiyu.jet.whoosh": (s_jet, 2, 1.0),
    "sekiyu.serpent.hiss": (s_hiss, 2, 1.0),
    "sekiyu.serpent.bite": (s_bite, 1, 1.0),
    "sekiyu.fire.ignite": (s_ignite, 2, 1.0),
    "sekiyu.fire.crackle": (s_crackle, 2, 0.7),
    "sekiyu.inferno.rise": (s_inferno_rise, 1, 1.0),
    "sekiyu.inferno.blast": (s_inferno_blast, 1, 1.0),
    "sekiyu.logia.dodge": (s_dodge, 2, 0.9),
    "sekiyu.logia.melt": (s_melt, 1, 0.9),
    "sekiyu.logia.sealed": (s_sealed, 1, 0.8),
    "sekiyu.ui.deny": (s_deny, 1, 0.7),
    "sekiyu.ui.click": (s_click, 1, 0.6),
    "sekiyu.fruit.awaken": (s_awaken, 1, 1.0),
}


def file_stem(event, variant):
    base = event.replace("sekiyu.", "").replace(".", "_")
    return f"{base}_{variant + 1}"


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def build(out_dir):
    """Render every sound to out_dir; returns {event: [relative stems]} for sound_definitions.json."""
    os.makedirs(out_dir, exist_ok=True)
    table = {}
    with tempfile.TemporaryDirectory() as tmp:
        for event, (fn, variants, _vol) in SOUNDS.items():
            stems = []
            for v in range(variants):
                x = fade(norm(fn(v)))
                stem = file_stem(event, v)
                wav = os.path.join(tmp, stem + ".wav")
                write_wav(wav, x)
                ogg = os.path.join(out_dir, stem + ".ogg")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "4", ogg], check=True)
                stems.append(stem)
            table[event] = stems
    return table


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "sounds_preview")
    t = build(out)
    print(f"{sum(len(v) for v in t.values())} files for {len(t)} sound events -> {out}")
