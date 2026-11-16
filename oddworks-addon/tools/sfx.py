"""
Procedural sound design for ODDWORKS (numpy synthesis -> 44.1 kHz mono -> OGG Vorbis via ffmpeg).

Every sound is built from a few physical ideas rather than generic beeps:
  * ice / crystal  : inharmonic bell partials (ratios of a free bar) + crackle clicks
  * sunlight       : slow-beating harmonic stacks rising in pitch (the lenses "drink" light)
  * line / reel    : band-passed air noise with Doppler-like sweeps, ratchet click trains
  * steel / bamboo : struck-bar resonances (blade ring), hollow tube modes (bamboo knock)
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 44100
RNG = np.random.default_rng(1729)


# =========================================================================== primitives

def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env_adsr(n, a=0.005, d=0.05, s=0.6, r=0.1, dur=None):
    dur = dur or n / SR
    t = np.arange(n) / SR
    e = np.ones(n)
    e[t < a] = t[t < a] / max(a, 1e-6)
    m = (t >= a) & (t < a + d)
    e[m] = 1 - (1 - s) * (t[m] - a) / max(d, 1e-6)
    m = (t >= a + d) & (t < dur - r)
    e[m] = s
    m = t >= dur - r
    e[m] = s * np.clip((dur - t[m]) / max(r, 1e-6), 0, 1)
    return e


def env_exp(n, decay, attack=0.002):
    t = np.arange(n) / SR
    e = np.exp(-t / decay)
    if attack > 0:
        e *= np.clip(t / attack, 0, 1)
    return e


def noise(n):
    return RNG.standard_normal(n)


def fft_filter(x, lo=None, hi=None, slope=4):
    """Smooth band-pass by spectral weighting (zero phase)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    w = np.ones_like(f)
    if lo:
        w *= 1 / (1 + (lo / np.maximum(f, 1)) ** slope)
    if hi:
        w *= 1 / (1 + (f / hi) ** slope)
    return np.fft.irfft(X * w, len(x))


def sweep_filter(x, f_start, f_end, q=6.0, block=512):
    """Time-varying band-pass via overlapped FFT blocks (for whooshes)."""
    out = np.zeros(len(x) + block * 3)
    win = np.hanning(block * 2)
    nb = max(1, len(x) // block)
    for i in range(nb + 1):
        s = i * block
        seg = x[s:s + block * 2]
        if len(seg) < 8:
            break
        seg = np.pad(seg, (0, block * 2 - len(seg)))
        frac = min(1.0, i / max(1, nb))
        fc = f_start * (f_end / f_start) ** frac
        X = np.fft.rfft(seg * win)
        f = np.fft.rfftfreq(len(seg), 1 / SR)
        bw = fc / q
        w = np.exp(-0.5 * ((f - fc) / bw) ** 2)
        y = np.fft.irfft(X * w, len(seg))
        out[s:s + block * 2] += y
    return out[:len(x)]


def osc(freq, dur, phase=0.0, kind="sine"):
    t = t_axis(dur)
    if callable(freq):
        f = freq(t)
        ph = 2 * np.pi * np.cumsum(f) / SR + phase
    else:
        ph = 2 * np.pi * freq * t + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    raise ValueError(kind)


def bell(f0, dur, ratios=(1.0, 2.756, 5.404, 8.933), decays=(1.0, 0.55, 0.32, 0.2), amps=(1, 0.55, 0.35, 0.2)):
    """Free-bar / crystal partials (inharmonic) with per-partial exponential decay."""
    n = int(SR * dur)
    y = np.zeros(n)
    for r, d, a in zip(ratios, decays, amps):
        y += a * osc(f0 * r, dur, phase=RNG.random() * 6.28) * env_exp(n, dur * d * 0.6)
    return y


def clicks(dur, rate_fn, width=0.0015, bright=6000):
    """Crackle / ratchet train; rate_fn(t) clicks per second."""
    n = int(SR * dur)
    y = np.zeros(n)
    t = 0.0
    while t < dur:
        r = max(1.0, rate_fn(t))
        i = int(t * SR)
        L = int(width * SR)
        if i + L < n:
            burst = noise(L) * np.exp(-np.arange(L) / (L / 4))
            y[i:i + L] += burst * (0.5 + 0.5 * RNG.random())
        t += (1.0 / r) * (0.6 + 0.8 * RNG.random())
    return fft_filter(y, lo=bright * 0.3, hi=bright * 2.5, slope=2)


def mixdown(*parts):
    n = max(len(p) for p in parts)
    y = np.zeros(n)
    for p in parts:
        y[:len(p)] += p
    return y


def pad(x, dur):
    n = int(SR * dur)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


DRIVE = {"oddworks.line.snap": 5.0, "oddworks.goggles.discharge": 3.5, "oddworks.line.break": 4.0,
         "oddworks.goggles.freeze": 2.6, "oddworks.goggles.rime": 2.6, "oddworks.line.cast": 2.6,
         "oddworks.line.reel": 2.2, "oddworks.cane.clang": 2.0, "oddworks.line.hook_block": 2.2}


def normalize(x, peak=0.89, drive=1.5):
    """Peak-normalise after a soft tanh limiter so transient-heavy sounds keep their body."""
    m = np.max(np.abs(x)) or 1.0
    y = np.tanh(drive * x / m) / math.tanh(drive)
    y = y * peak
    fade = min(len(y) // 4, int(0.006 * SR))
    if fade:
        y[-fade:] *= np.linspace(1, 0, fade)
    return y


# =========================================================================== sound catalogue

def goggles_charge():
    """Lenses drinking sunlight: shimmering harmonic stack swelling upward (~0.6 s, re-triggered
    with rising pitch by the script while charging)."""
    dur = 0.65
    n = int(SR * dur)
    f = lambda t: 520 * (1 + 0.35 * t / dur)
    y = sum(osc(lambda t, k=k: f(t) * k * (1 + 0.004 * np.sin(2 * np.pi * (5 + k) * t)), dur) / k ** 1.3
            for k in (1, 2, 3, 4, 6))
    shimmer = fft_filter(noise(n), lo=5000, hi=12000) * 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * t_axis(dur)))
    return (y + shimmer) * env_adsr(n, 0.12, 0.2, 0.75, 0.25, dur)


def goggles_full():
    """Full charge 'ting': crystal bell + airy sparkle."""
    dur = 1.4
    sp = fft_filter(noise(int(SR * dur)), lo=7000, hi=14000) * env_exp(int(SR * dur), 0.15) * 0.25
    return mixdown(bell(1760, dur), 0.5 * bell(2637, dur * 0.8), sp)


def goggles_discharge():
    """Cryogenic discharge: sharp ice crack, hiss of super-cold vapour, falling crystalline sweep."""
    dur = 1.35
    n = int(SR * dur)
    crack = noise(n) * env_exp(n, 0.012) * 1.4
    thump = osc(lambda t: 95 * np.exp(-t * 6) + 45, dur) * env_exp(n, 0.09) * 0.9
    hiss = fft_filter(noise(n), lo=2500, hi=11000) * env_exp(n, 0.35, attack=0.01) * 0.55
    fall = osc(lambda t: 3200 * np.exp(-t * 2.2) + 600, dur) * env_exp(n, 0.4) * 0.22
    crackle = clicks(dur, lambda t: 260 * math.exp(-t * 2.5) + 20, bright=7000) * 0.6
    return mixdown(crack, thump, hiss, fall, crackle)


def goggles_freeze():
    """Water / flesh flash-freezing: dense crystal crackle and a glassy settle."""
    dur = 1.0
    n = int(SR * dur)
    crackle = clicks(dur, lambda t: 420 * (1 - t / dur) + 30, bright=6500)
    glass = bell(2950, dur, decays=(0.7, 0.5, 0.3, 0.2)) * 0.35
    body = fft_filter(noise(n), lo=600, hi=2400) * env_exp(n, 0.08) * 0.5
    return mixdown(crackle, glass, body)


def goggles_flash():
    """Snowblind: bright swell of light, a 'shing' and shimmering tail."""
    dur = 1.1
    n = int(SR * dur)
    swell = sweep_filter(noise(n), 900, 9000, q=3) * env_adsr(n, 0.04, 0.2, 0.3, 0.5, dur) * 1.4
    shing = bell(3520, dur, ratios=(1, 1.5, 2.01, 3.0), decays=(1, 0.7, 0.5, 0.3)) * 0.45
    return mixdown(swell, shing)


def goggles_sundog():
    """Sun dog captured: warm detuned choir pad rising into a bright chime."""
    dur = 2.4
    n = int(SR * dur)
    chord = (1.0, 1.25, 1.5, 2.0)
    pad_ = sum(osc(lambda t, r=r, d=d: 330 * r * (1 + d) * (1 + 0.04 * t), dur, kind="saw")
               for r in chord for d in (-0.004, 0.0, 0.005))
    pad_ = fft_filter(pad_, lo=180, hi=2600) * env_adsr(n, 0.5, 0.4, 0.7, 0.9, dur) * 0.18
    chime = pad(np.concatenate([np.zeros(int(SR * 0.9)), bell(1318, 1.5) * 0.5]), dur)
    return mixdown(pad_, chime)


def goggles_rime():
    """Lenses icing over: creeping crackle + breathy frost."""
    dur = 0.9
    n = int(SR * dur)
    return mixdown(clicks(dur, lambda t: 80 + 300 * t, bright=5200) * 0.8,
                   fft_filter(noise(n), lo=1500, hi=6000) * env_adsr(n, 0.2, 0.2, 0.6, 0.3, dur) * 0.35)


def line_whirl():
    """One overhead revolution: air whoosh with a Doppler-like pass (~0.45 s)."""
    dur = 0.48
    n = int(SR * dur)
    w = sweep_filter(noise(n), 350, 1500, q=2.2)
    e = np.sin(np.pi * np.clip(t_axis(dur) / dur, 0, 1)) ** 2
    hum = osc(lambda t: 140 + 160 * np.sin(np.pi * t / dur), dur) * 0.08
    return (w * 1.2 + hum) * e


def line_cast():
    """Release: sharp whoosh then the spool screaming as line pays out (ratchet slowing)."""
    dur = 1.3
    n = int(SR * dur)
    whoosh = sweep_filter(noise(n), 2400, 500, q=2.5) * env_exp(n, 0.18, attack=0.01) * 1.2
    ratchet = clicks(dur, lambda t: 140 * math.exp(-t * 1.8) + 8, width=0.0012, bright=3800) * 0.9
    zing = osc(lambda t: 1900 * np.exp(-t * 1.2) + 300, dur) * env_exp(n, 0.5) * 0.06
    return mixdown(whoosh, ratchet, zing)


def line_hook_block():
    """Hook bites into a surface: woody knock + metal tick."""
    dur = 0.35
    n = int(SR * dur)
    knock = fft_filter(noise(n), lo=250, hi=1600) * env_exp(n, 0.03) * 1.2
    tick = bell(4100, 0.25, decays=(0.4, 0.3, 0.2, 0.1)) * 0.3
    return mixdown(knock, tick)


def line_hook_flesh():
    dur = 0.3
    n = int(SR * dur)
    thud = osc(lambda t: 120 * np.exp(-t * 8) + 60, dur) * env_exp(n, 0.05)
    tear = fft_filter(noise(n), lo=900, hi=3500) * env_exp(n, 0.04) * 0.5
    return mixdown(thud, tear)


def line_reel():
    """Reeling: ratchet clicks of the drum plus line hiss (short, looped by re-triggering)."""
    dur = 0.32
    n = int(SR * dur)
    r = clicks(dur, lambda t: 46, width=0.0016, bright=3200)
    hiss = fft_filter(noise(n), lo=3000, hi=8000) * 0.12
    return mixdown(r, hiss) * env_adsr(n, 0.01, 0.05, 0.9, 0.04, dur)


def line_taut():
    """Strained line: low creak + rising string tension."""
    dur = 0.7
    n = int(SR * dur)
    string = osc(lambda t: 160 + 90 * t / dur, dur, kind="tri") * env_adsr(n, 0.05, 0.1, 0.6, 0.3, dur) * 0.4
    creak = clicks(dur, lambda t: 60 + 40 * np.sin(t * 9), width=0.003, bright=900) * 0.6
    return mixdown(string, creak)


def line_snap_crack():
    """Snap skill: whip crack (supersonic tip) travelling down the line."""
    dur = 0.6
    n = int(SR * dur)
    crack = noise(n) * env_exp(n, 0.004) * 2.0
    air = sweep_filter(noise(n), 3000, 700, q=2.0) * env_exp(n, 0.12, attack=0.004) * 0.6
    twang = osc(lambda t: 420 * np.exp(-t * 3) + 120, dur, kind="tri") * env_exp(n, 0.2) * 0.25
    return mixdown(crack, air, twang)


def line_break():
    dur = 0.8
    n = int(SR * dur)
    twang = osc(lambda t: 900 * np.exp(-t * 4) + 200, dur, kind="tri") * env_exp(n, 0.25) * 0.5
    snap = noise(n) * env_exp(n, 0.006) * 1.6
    whip = sweep_filter(noise(n), 1800, 300, q=2.0) * env_exp(n, 0.15) * 0.6
    return mixdown(snap, twang, whip)


def line_bite():
    """Fish strike on the float: plop + tug twang."""
    dur = 0.5
    n = int(SR * dur)
    plop = osc(lambda t: 700 * np.exp(-t * 18) + 180, dur) * env_exp(n, 0.06)
    tug = osc(lambda t: 260 + 40 * np.exp(-t * 10), dur, kind="tri") * env_exp(n, 0.12) * 0.35
    splash = fft_filter(noise(n), lo=1200, hi=7000) * env_exp(n, 0.07) * 0.4
    return mixdown(plop, tug, splash)


def cane_grip():
    """Hand settling on the hilt: bamboo creak + a soft collar click."""
    dur = 0.35
    n = int(SR * dur)
    creak = clicks(dur, lambda t: 90, width=0.002, bright=1500) * env_adsr(n, 0.02, 0.1, 0.4, 0.1, dur) * 0.6
    click = bell(2600, 0.2, decays=(0.3, 0.2, 0.1, 0.1)) * 0.25
    return mixdown(creak, pad(np.concatenate([np.zeros(int(SR * 0.12)), click]), dur))


def cane_glint():
    """Perfect-draw window: tiny high steel 'tink'."""
    return bell(4700, 0.6, ratios=(1, 2.32, 4.25, 6.63), decays=(1, 0.6, 0.4, 0.2), amps=(1, 0.4, 0.2, 0.1)) * 0.6


def cane_draw():
    """Blade leaving the bamboo: rising metallic scrape ending in a ringing 'shing'."""
    dur = 0.9
    n = int(SR * dur)
    scrape = sweep_filter(noise(n), 1800, 7500, q=4) * env_adsr(n, 0.01, 0.1, 0.7, 0.05, 0.28) * 1.1
    ring = pad(np.concatenate([np.zeros(int(SR * 0.22)),
                               bell(2480, 0.68, ratios=(1, 2.76, 5.4, 8.93), decays=(1, 0.7, 0.45, 0.3))]), dur) * 0.55
    return mixdown(scrape, ring)


def cane_swish():
    dur = 0.28
    n = int(SR * dur)
    return sweep_filter(noise(n), 900, 3600, q=2.6) * np.sin(np.pi * t_axis(dur) / dur) ** 1.5 * 1.2


def cane_slash():
    """Iai cut: fast high air-slice."""
    dur = 0.4
    n = int(SR * dur)
    s = sweep_filter(noise(n), 5000, 1400, q=3) * env_exp(n, 0.07, attack=0.003) * 1.4
    edge = osc(lambda t: 6000 * np.exp(-t * 9) + 1200, dur) * env_exp(n, 0.05) * 0.12
    return mixdown(s, edge)


def cane_cut():
    dur = 0.32
    n = int(SR * dur)
    slice_ = sweep_filter(noise(n), 3800, 1200, q=3) * env_exp(n, 0.05, attack=0.002)
    body = fft_filter(noise(n), lo=150, hi=900) * env_exp(n, 0.04) * 0.6
    return mixdown(slice_, body)


def cane_cut_crit():
    return mixdown(cane_cut(), cane_glint() * 0.6)


def cane_clang():
    """Blade glancing off armour / bone / iron: inharmonic metal clang with buzz."""
    dur = 0.9
    n = int(SR * dur)
    ring = bell(1180, dur, ratios=(1, 1.47, 2.09, 2.56, 3.9), decays=(1, 0.8, 0.6, 0.4, 0.3),
                amps=(1, 0.8, 0.6, 0.4, 0.3)) * 0.7
    hit = noise(n) * env_exp(n, 0.006) * 1.2
    return mixdown(ring, hit)


def cane_deflect():
    """Parry: bright ringing 'ting' with a sharp spark transient."""
    dur = 1.1
    n = int(SR * dur)
    ring = bell(2093, dur, ratios=(1, 2.76, 5.4), decays=(1, 0.6, 0.35), amps=(1, 0.5, 0.25)) * 0.8
    spark = fft_filter(noise(n), lo=4000, hi=12000) * env_exp(n, 0.02) * 0.8
    return mixdown(ring, spark)


def cane_sheathe():
    """Noto: descending scrape into the bamboo, then the hollow 'tok' of the collar seating."""
    dur = 0.75
    n = int(SR * dur)
    slide = sweep_filter(noise(n), 6500, 1600, q=4) * env_adsr(n, 0.01, 0.1, 0.7, 0.05, 0.42) * 0.7
    tok_n = int(SR * 0.3)
    tok = (osc(820, 0.3) * 0.7 + osc(1640 * 1.02, 0.3) * 0.3 + osc(410, 0.3) * 0.4) * env_exp(tok_n, 0.035)
    tok += fft_filter(noise(tok_n), lo=600, hi=3000) * env_exp(tok_n, 0.01) * 0.6
    return mixdown(slide, pad(np.concatenate([np.zeros(int(SR * 0.44)), tok]), dur))


def cane_tap():
    """Sheathed cane strike: hollow bamboo knock."""
    dur = 0.3
    n = int(SR * dur)
    return (osc(640, dur) * 0.6 + osc(1310, dur) * 0.3) * env_exp(n, 0.03) + \
        fft_filter(noise(n), lo=400, hi=2500) * env_exp(n, 0.012) * 0.5


def cane_hemorrhage():
    """Wounds opening at the click: low thump + wet spray burst (stylised, not gory)."""
    dur = 0.7
    n = int(SR * dur)
    thump = osc(lambda t: 90 * np.exp(-t * 7) + 40, dur) * env_exp(n, 0.12)
    spray = fft_filter(noise(n), lo=500, hi=4000) * env_exp(n, 0.09, attack=0.008) * 0.6
    return mixdown(thump, spray)


def cane_bleed():
    """Bleed tick: small drip."""
    dur = 0.25
    n = int(SR * dur)
    return osc(lambda t: 1300 * np.exp(-t * 30) + 400, dur) * env_exp(n, 0.03) * 0.6


SOUNDS = {
    # id (sound event)            fn                 category  volume  max_dist
    "oddworks.goggles.charge":   (goggles_charge,    "player", 0.55, 16),
    "oddworks.goggles.full":     (goggles_full,      "player", 0.8, 16),
    "oddworks.goggles.discharge": (goggles_discharge, "player", 1.0, 32),
    "oddworks.goggles.freeze":   (goggles_freeze,    "player", 0.9, 24),
    "oddworks.goggles.flash":    (goggles_flash,     "player", 0.9, 24),
    "oddworks.goggles.sundog":   (goggles_sundog,    "player", 0.9, 24),
    "oddworks.goggles.rime":     (goggles_rime,      "player", 0.8, 12),
    "oddworks.line.whirl":       (line_whirl,        "player", 0.7, 16),
    "oddworks.line.cast":        (line_cast,         "player", 0.9, 24),
    "oddworks.line.hook_block":  (line_hook_block,   "player", 0.8, 24),
    "oddworks.line.hook_flesh":  (line_hook_flesh,   "player", 0.8, 24),
    "oddworks.line.reel":        (line_reel,         "player", 0.5, 12),
    "oddworks.line.taut":        (line_taut,         "player", 0.6, 16),
    "oddworks.line.snap":        (line_snap_crack,   "player", 1.0, 32),
    "oddworks.line.break":       (line_break,        "player", 0.9, 24),
    "oddworks.line.bite":        (line_bite,         "player", 0.9, 24),
    "oddworks.cane.grip":        (cane_grip,         "player", 0.6, 12),
    "oddworks.cane.glint":       (cane_glint,        "player", 0.7, 12),
    "oddworks.cane.draw":        (cane_draw,         "player", 0.9, 20),
    "oddworks.cane.swish":       (cane_swish,        "player", 0.6, 12),
    "oddworks.cane.slash":       (cane_slash,        "player", 1.0, 24),
    "oddworks.cane.cut":         (cane_cut,          "player", 0.8, 16),
    "oddworks.cane.cut_crit":    (cane_cut_crit,     "player", 0.9, 16),
    "oddworks.cane.clang":       (cane_clang,        "player", 0.9, 20),
    "oddworks.cane.deflect":     (cane_deflect,      "player", 1.0, 24),
    "oddworks.cane.sheathe":     (cane_sheathe,      "player", 0.9, 16),
    "oddworks.cane.tap":         (cane_tap,          "player", 0.7, 12),
    "oddworks.cane.hemorrhage":  (cane_hemorrhage,   "player", 0.9, 24),
    "oddworks.cane.bleed":       (cane_bleed,        "player", 0.45, 10),
}


def _write_wav(path, y):
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def render_all(out_dir: str) -> dict:
    """Renders every sound to <out_dir>/<group>/<name>.ogg; returns sound_definitions entries."""
    defs = {}
    with tempfile.TemporaryDirectory() as tmp:
        for sid, (fn, cat, vol, maxd) in SOUNDS.items():
            _, group, name = sid.split(".")
            rel = f"sounds/oddworks/{group}/{name}"
            dst = os.path.join(out_dir, rel + ".ogg")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            y = normalize(fn(), drive=DRIVE.get(sid, 1.5))
            wav = os.path.join(tmp, f"{group}_{name}.wav")
            _write_wav(wav, y)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", dst],
                           check=True)
            defs[sid] = {"category": cat, "min_distance": 1.0, "max_distance": float(maxd),
                         "sounds": [{"name": rel, "volume": vol, "load_on_low_memory": True}]}
    return defs


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "build/sfx_test"
    d = render_all(out)
    print(len(d), "sounds ->", out)
