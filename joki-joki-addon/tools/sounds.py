"""
Procedural sound design for the Jōki Jōki no Mi add-on.

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


def s_hiss(v):
    sec = 0.55 + 0.15 * v
    n = int(SR * sec)
    return band_noise(sec, 2500 + 400 * v, 9000, tilt=0.2, seed=10 + v) * env(n, 0.02, sec - 0.12, hold=0.1, curve=1.6)


def s_jet(v):
    sec = 0.6
    n = int(SR * sec)
    body = sweep_noise(sec, [(400, 1500), (900, 4000), (2500, 9000)], seed=20 + v)
    return body * env(n, 0.01, 0.5, hold=0.05, curve=1.8) + thump(sec, 140, 60) * 0.35


def s_boost(v):
    sec = 1.1
    n = int(SR * sec)
    rise = sweep_noise(sec, [(200, 700), (500, 2000), (1500, 6000)], seed=30) * np.linspace(0.2, 1, n) ** 2
    hum = tone(sec, 70, 140, "tri") * np.linspace(0.1, 0.5, n)
    rel = np.zeros(n)
    k = int(SR * 0.72)
    rel[k:] = band_noise(sec - k / SR, 2000, 9000, seed=31) * env(n - k, 0.005, 0.38, curve=1.4)
    return rise * env(n, 0.05, 0.4, hold=0.6) * 0.6 + hum * env(n, 0.05, 0.3, hold=0.7) + rel * 0.9


def s_dash(v):
    sec = 0.45
    n = int(SR * sec)
    return band_noise(sec, 700, 6500, seed=40 + v) * env(n, 0.004, 0.4, curve=2.2) + thump(sec, 120, 50) * 0.5


def s_jump(v):
    sec = 0.9
    n = int(SR * sec)
    roar = sweep_noise(sec, [(150, 900), (600, 3500), (2000, 8000)], seed=50) * env(n, 0.01, 0.75, hold=0.1, curve=1.6)
    return roar + thump(sec, 80, 30) * 0.9


def s_land(v):
    sec = 0.5
    n = int(SR * sec)
    return thump(sec, 70, 35) * 0.8 + band_noise(sec, 1500, 7000, seed=60) * env(n, 0.005, 0.45, curve=2) * 0.6


def s_cannon(v):
    sec = 0.55
    n = int(SR * sec)
    crack = band_noise(sec, 1500, 9000, seed=70 + v) * env(n, 0.001, 0.08, curve=3)
    jet = sweep_noise(sec, [(3000, 9000), (800, 3000)], seed=71 + v) * env(n, 0.005, 0.5, curve=1.8)
    return crack * 0.8 + jet + thump(sec, 160, 70) * 0.4


def s_impact(v):
    sec = 0.6
    n = int(SR * sec)
    return thump(sec, 110, 40) + band_noise(sec, 900, 7000, seed=80 + v) * env(n, 0.002, 0.5, curve=2.2) * 0.8


def s_punch(v):
    sec = 0.7
    n = int(SR * sec)
    whoomp = thump(sec, 130, 35) * 1.1
    burst = band_noise(sec, 600, 8000, seed=90) * env(n, 0.001, 0.6, curve=1.8)
    return whoomp + burst * 0.9 + clank(sec, 260, seed=3) * 0.25


def s_kick(v):
    sec = 0.55
    n = int(SR * sec)
    return sweep_noise(sec, [(500, 2500), (2000, 8000)], seed=95) * env(n, 0.003, 0.5, curve=1.9) + thump(sec, 100, 45) * 0.7


def s_explode(v):
    sec = 1.8
    n = int(SR * sec)
    boom = tone(sec, 60, 25) * env(n, 0.004, 1.0, curve=2.5)
    blast = band_noise(sec, 200, 6000, seed=100) * env(n, 0.002, 0.5, curve=2.4)
    long_hiss = band_noise(sec, 2500, 9500, seed=101) * env(n, 0.05, 1.6, hold=0.15, curve=1.3)
    return boom * 1.1 + blast + long_hiss * 0.7


def s_mist(v):
    sec = 2.2
    n = int(SR * sec)
    return band_noise(sec, 1200, 7000, seed=110) * env(n, 0.25, 1.6, hold=0.3, curve=1.2) + band_noise(sec, 150, 600, seed=111) * env(n, 0.3, 1.5, hold=0.3) * 0.4


def s_chug(v):
    sec = 0.28
    n = int(SR * sec)
    puff = band_noise(sec, 350 + 120 * v, 2200, seed=120 + v) * env(n, 0.004, 0.24, curve=2.5)
    return puff + thump(sec, 70 + 10 * v, 40) * 0.45


def s_shift(v):
    sec = 0.6
    n = int(SR * sec)
    k = int(SR * 0.08)
    hiss = np.zeros(n)
    hiss[k:] = band_noise(sec - k / SR, 2500, 9000, seed=130) * env(n - k, 0.01, 0.45, curve=1.8)
    return clank(sec, 380, seed=1) * 0.9 + hiss * 0.7


def s_redline_charge(v):
    sec = 1.0
    n = int(SR * sec)
    rumble = band_noise(sec, 40, 180, seed=140) * np.linspace(0.3, 1, n)
    rise = tone(sec, 120, 520, "tri") * np.linspace(0, 0.7, n) ** 1.5
    pressure = band_noise(sec, 1500, 8000, seed=141) * np.linspace(0, 1, n) ** 3
    return (rumble * 0.9 + rise * 0.6 + pressure * 0.7) * env(n, 0.05, 0.06, hold=0.89)


def s_redline_engage(v):
    sec = 1.9
    n = int(SR * sec)
    boom = tone(sec, 75, 30) * env(n, 0.003, 1.2, curve=2.2)
    w = whistle(sec, 660) * env(n, 0.03, 1.2, hold=0.4, curve=1.4)
    blast = band_noise(sec, 300, 9000, seed=150) * env(n, 0.002, 1.4, curve=1.8)
    return boom + w * 0.55 + blast * 0.8


def s_release(v):
    sec = 1.3
    n = int(SR * sec)
    return band_noise(sec, 1800, 9500, seed=160) * env(n, 0.01, 1.2, hold=0.05, curve=1.2) + band_noise(sec, 200, 900, seed=161) * env(n, 0.02, 0.6) * 0.3


def s_overheat(v):
    """Overheat alarm: two blasts of a steam whistle over violent venting."""
    sec = 2.2
    n = int(SR * sec)
    out = np.zeros(n)
    for start, length in ((0.0, 0.7), (0.85, 1.1)):
        a = int(SR * start)
        m = int(SR * length)
        out[a:a + m] += whistle(length, 1040) * env(m, 0.02, 0.25, hold=length - 0.27, curve=1.5)
    vent = band_noise(sec, 1500, 9500, seed=170) * env(n, 0.01, 2.0, hold=0.1, curve=1.1)
    return out * 0.75 + vent * 0.55 + clank(sec, 300, seed=4) * 0.2


def s_cool(v):
    """Cooling: fading sizzle with metallic ticks as the body contracts."""
    sec = 1.6
    n = int(SR * sec)
    sizzle = band_noise(sec, 3000, 9500, seed=180) * env(n, 0.02, 1.5, curve=1.5)
    crackle = (np.random.default_rng(181).random(n) > 0.9985) * 1.0
    ticks = np.zeros(n)
    for pos in (0.35, 0.8, 1.2):
        k = int(SR * pos)
        c = clank(0.3, 900 + pos * 300, seed=int(pos * 10)) * 0.4
        ticks[k:k + len(c)] += c[: max(0, min(len(c), n - k))]
    return sizzle * 0.7 + crackle * 0.5 + ticks


def s_deny(v):
    sec = 0.3
    n = int(SR * sec)
    return clank(sec, 180, seed=5) * 0.7 + band_noise(sec, 300, 1200, seed=190) * env(n, 0.002, 0.15) * 0.4


def s_click(v):
    sec = 0.15
    return clank(sec, 900, seed=6)


def s_awaken(v):
    sec = 3.0
    n = int(SR * sec)
    heartbeat = np.zeros(n)
    for pos in (0.0, 0.32, 0.9, 1.2):
        k = int(SR * pos)
        b = thump(0.3, 70, 32)
        heartbeat[k:k + len(b)] += b[: n - k]
    rise = sweep_noise(sec, [(100, 400), (400, 2000), (2000, 9000)], seed=200) * np.linspace(0, 1, n) ** 2
    w = np.zeros(n)
    k = int(SR * 1.7)
    w[k:] = whistle(sec - k / SR, 520) * env(n - k, 0.05, 1.0, hold=0.2, curve=1.5)
    return heartbeat * 0.9 + rise * 0.6 * env(n, 0.1, 0.6, hold=2.2) + w * 0.5


SOUNDS = {
    # sound event id: (synth function, variants, volume, category)
    "joki.steam.hiss": (s_hiss, 3, 0.8),
    "joki.steam.jet": (s_jet, 2, 1.0),
    "joki.steam.boost": (s_boost, 1, 1.0),
    "joki.steam.dash": (s_dash, 2, 1.0),
    "joki.steam.jump": (s_jump, 1, 1.0),
    "joki.steam.land": (s_land, 1, 0.9),
    "joki.steam.cannon": (s_cannon, 2, 1.0),
    "joki.steam.impact": (s_impact, 2, 1.0),
    "joki.steam.punch": (s_punch, 1, 1.0),
    "joki.steam.kick": (s_kick, 1, 1.0),
    "joki.steam.explode": (s_explode, 1, 1.0),
    "joki.steam.mist": (s_mist, 1, 0.9),
    "joki.engine.chug": (s_chug, 3, 0.7),
    "joki.engine.shift": (s_shift, 1, 0.9),
    "joki.redline.charge": (s_redline_charge, 1, 1.0),
    "joki.redline.engage": (s_redline_engage, 1, 1.0),
    "joki.steam.release": (s_release, 1, 0.9),
    "joki.overheat.alarm": (s_overheat, 1, 1.0),
    "joki.overheat.cool": (s_cool, 1, 0.9),
    "joki.ui.deny": (s_deny, 1, 0.7),
    "joki.ui.click": (s_click, 1, 0.6),
    "joki.fruit.awaken": (s_awaken, 1, 1.0),
}


def file_stem(event, variant):
    base = event.replace("joki.", "").replace(".", "_")
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
