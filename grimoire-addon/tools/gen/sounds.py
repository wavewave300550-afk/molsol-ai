"""Original procedural sound design (numpy DSP -> mono Ogg Vorbis via ffmpeg). No external assets."""
import os
import subprocess
import wave
import numpy as np
from .fxdefs import dump

SR = 32000


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def rng(seed):
    return np.random.RandomState(seed)


def band(x, lo, hi, soft=0.15):
    """FFT band-pass with soft edges (lo/hi in Hz; lo=0 low-pass, hi=None high-pass)."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + np.exp(np.clip(-(f - lo) / max(1.0, lo * soft), -60, 60)))
    if hi:
        m *= 1 / (1 + np.exp(np.clip((f - hi) / max(1.0, hi * soft), -60, 60)))
    return np.fft.irfft(X * m, n)


def sweep_band(x, f0, f1, width=0.5):
    """Time-varying band emphasis by crossfading 6 static bands (cheap 'moving filter')."""
    out = np.zeros_like(x)
    n = len(x)
    steps = 6
    for i in range(steps):
        fc = f0 * (f1 / f0) ** (i / (steps - 1))
        b = band(x, fc * (1 - width / 2), fc * (1 + width / 2))
        w = np.clip(1 - np.abs(np.linspace(0, steps - 1, n) - i), 0, 1)
        out += b * w
    return out


def env(n, a=0.01, d=0.3, curve=3.0):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * curve / 3)
    return e


def swell(n, peak=0.7, sharp=2.0):
    x = np.linspace(0, 1, n)
    return np.where(x < peak, (x / peak) ** sharp, ((1 - x) / (1 - peak)) ** 1.2)


def tone(freq, dur, kind="sine", phase=0.0):
    t = t_(dur)
    if callable(freq):
        f = freq(t)
        ph = 2 * np.pi * np.cumsum(f) / SR + phase
    else:
        ph = 2 * np.pi * freq * t + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if kind == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1
    return np.sign(np.sin(ph))


def noise(dur, seed=1):
    return rng(seed).randn(int(SR * dur))


def bell(freq, dur, seed=0, inharm=(1, 2.76, 5.4, 8.93), decay=1.0):
    t = t_(dur)
    out = np.zeros_like(t)
    for i, k in enumerate(inharm):
        out += np.sin(2 * np.pi * freq * k * t + i) * np.exp(-t * (2.5 + i * 2.0) / decay) / (1 + i)
    return out


def boom(dur=1.5, f0=70, f1=32, seed=3, noise_amt=0.6):
    t = t_(dur)
    body = tone(lambda tt: f1 + (f0 - f1) * np.exp(-tt * 6), dur) * np.exp(-t * 2.2)
    n = band(noise(dur, seed), 20, 900) * np.exp(-t * 5) * noise_amt
    rumble = band(noise(dur, seed + 1), 20, 140) * np.exp(-t * 1.6) * 0.8
    return body * 1.2 + n + rumble


def whoosh(dur=0.6, f0=600, f1=2400, seed=5, peak=0.6):
    n = noise(dur, seed)
    return sweep_band(n, f0, f1, 0.8) * swell(len(n), peak, 1.6)


def crackle(dur=0.6, density=60, seed=7, hi=6000):
    r = rng(seed)
    n = int(SR * dur)
    out = np.zeros(n)
    for _ in range(int(density * dur)):
        p = r.randint(0, n - 200)
        L = r.randint(20, 160)
        out[p:p + L] += r.randn(L) * np.exp(-np.arange(L) / (L / 4)) * r.rand()
    return band(out, 900, hi)


def gurgle(dur=0.8, seed=9, rate=14):
    t = t_(dur)
    r = rng(seed)
    out = np.zeros_like(t)
    for _ in range(int(dur * rate)):
        st = r.rand() * dur
        f = 180 + r.rand() * 500
        seg = (t > st) & (t < st + 0.09)
        tt = t[seg] - st
        out[seg] += np.sin(2 * np.pi * (f + 900 * tt) * tt) * np.exp(-tt * 40)
    return out + band(noise(dur, seed), 80, 900) * 0.15


def shatter(dur=0.9, seed=11, base=2200):
    r = rng(seed)
    out = crackle(dur, 140, seed, 11000) * 0.6
    t = t_(dur)
    for _ in range(18):
        st = r.rand() * dur * 0.35
        f = base * (0.6 + r.rand() * 1.8)
        seg = t >= st
        tt = t[seg] - st
        out[seg] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * (12 + r.rand() * 20)) * 0.25
    return out * env(len(out), 0.002, dur * 0.5)


def reverb(x, tail=0.6, mix=0.3, seed=13):
    n = int(SR * tail)
    ir = rng(seed).randn(n) * np.exp(-np.arange(n) / SR * 6 / tail)
    ir = band(ir, 200, 7000)
    wet = np.convolve(x, ir)[:len(x) + n] if len(x) < 5000 else np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n), len(x) + n)
    out = np.zeros(len(x) + n)
    out[:len(x)] += x
    out += wet / (np.abs(wet).max() + 1e-9) * np.abs(x).max() * mix
    return out


def heartbeat(dur=0.8, f=48, seed=15, strength=1.0):
    t = t_(dur)
    out = np.zeros_like(t)
    for st, a in ((0.0, 1.0), (0.22, 0.75)):
        seg = t >= st
        tt = t[seg] - st
        out[seg] += np.sin(2 * np.pi * (f + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * a
    out += band(noise(dur, seed), 30, 200) * env(len(t), 0.002, 0.15) * 0.3
    return out * strength


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def pad(x, dur):
    n = int(SR * dur)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def norm(x, peak=0.85):
    x = x - np.mean(x)
    m = np.abs(x).max() + 1e-9
    x = x / m * peak
    fade = min(len(x), int(SR * 0.02))
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


# ------------------------------------------------------------------------------------- library
def library():
    S = {}
    # UI ---------------------------------------------------------------------------------
    S["ui.page"] = mix(band(noise(0.28, 1), 1200, 7000) * (env(int(SR * 0.28), 0.005, 0.05) + np.roll(env(int(SR * 0.28), 0.005, 0.04), int(SR * 0.08)) * 0.8),
                       band(noise(0.28, 2), 300, 1500) * env(int(SR * 0.28), 0.01, 0.08) * 0.3)
    S["ui.ready"] = reverb(bell(1046, 0.7, decay=0.6) * 0.6 + bell(1568, 0.7, decay=0.5) * 0.3, 0.4, 0.25)
    S["ui.fizzle"] = mix(whoosh(0.45, 1800, 400, 3, 0.2) * 0.8, crackle(0.45, 40, 4) * 0.4)
    # Pressure -----------------------------------------------------------------------------
    S["pressure.charge"] = mix(sweep_band(noise(1.0, 21), 300, 2600, 0.6) * swell(SR, 0.8, 1.2) * 0.7,
                               tone(lambda t: 90 + 40 * t, 1.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t_(1.0))) * 0.35)
    S["pressure.release"] = mix(whoosh(0.5, 300, 3000, 22, 0.25), boom(0.6, 110, 50, 23, 0.4) * 0.7)
    S["pressure.lance"] = mix(sweep_band(noise(0.9, 24), 2500, 500, 0.7) * env(int(SR * 0.9), 0.02, 0.35), boom(0.9, 140, 60, 25, 0.8) * 0.6,
                              tone(lambda t: 1800 - 1200 * t, 0.9, "saw") * env(int(SR * 0.9), 0.001, 0.12) * 0.12)
    S["pressure.boom"] = reverb(boom(1.6, 80, 28, 26, 1.0), 0.8, 0.35)
    S["pressure.thud"] = boom(0.6, 120, 55, 27, 0.7)
    S["pressure.whoosh"] = whoosh(0.6, 400, 2200, 28, 0.55)
    S["pressure.slam"] = reverb(mix(boom(1.6, 70, 30, 29, 1.2), bell(220, 1.6, 0, (1, 2.4, 3.9, 6.1), 1.4) * 0.35), 0.9, 0.3)
    S["pressure.hum"] = mix(tone(110, 1.0) * 0.5, tone(165, 1.0) * 0.25, band(noise(1.0, 30), 200, 900) * 0.25) * (0.8 + 0.2 * np.sin(2 * np.pi * 4 * t_(1.0)))
    S["pressure.pulse"] = mix(tone(lambda t: 70 + 90 * np.exp(-t * 6), 0.8) * env(int(SR * 0.8), 0.01, 0.4), band(noise(0.8, 31), 100, 700) * env(int(SR * 0.8), 0.005, 0.2) * 0.6)
    S["pressure.disc"] = mix(boom(0.35, 160, 90, 32, 0.5) * 0.7, whoosh(0.35, 900, 2600, 33, 0.3) * 0.6)
    S["pressure.dash"] = mix(boom(0.55, 130, 60, 34, 0.9), whoosh(0.55, 300, 2800, 35, 0.15))
    S["pressure.ring"] = mix(whoosh(0.4, 600, 2000, 36, 0.3) * 0.6, bell(740, 0.4, decay=0.4) * 0.25)
    S["pressure.sonar"] = reverb(mix(tone(lambda t: 420 + 900 * t, 0.5) * env(int(SR * 0.5), 0.01, 0.25) * 0.6,
                                     band(noise(0.5, 37), 300, 1200) * env(int(SR * 0.5), 0.01, 0.2) * 0.3), 0.9, 0.5)
    S["pressure.crystal"] = mix(tone(330, 0.9) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t_(0.9))) * env(int(SR * 0.9), 0.05, 0.6), bell(1320, 0.9, decay=0.7) * 0.2)
    S["pressure.rise"] = mix(band(noise(2.2, 38), 25, 220) * swell(int(SR * 2.2), 0.7, 1.3), tone(lambda t: 45 + 20 * t, 2.2) * swell(int(SR * 2.2), 0.7, 1.3) * 0.6)
    S["pressure.grind"] = mix(band(noise(0.8, 39), 150, 1400) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * t_(0.8))), boom(0.8, 90, 40, 40, 0.3) * 0.5)
    S["pressure.edict"] = reverb(mix(boom(3.0, 60, 22, 41, 1.4) * 1.2, pad(boom(1.4, 120, 40, 42, 1.0), 3.0) * 0.6,
                                     whoosh(3.0, 150, 3200, 43, 0.12) * 0.5), 1.2, 0.4)
    # Ice ----------------------------------------------------------------------------------
    r = rng(50)
    tink = np.zeros(int(SR * 1.0))
    for i in range(26):
        st = int(SR * (i / 26) * 0.9)
        b = bell(1500 + r.rand() * 2500, 0.35, i, decay=0.25) * (0.3 + 0.7 * i / 26)
        tink[st:st + len(b)] += b[:len(tink) - st]
    S["ice.charge"] = mix(tink * 0.5, band(noise(1.0, 51), 3000, 9000) * swell(SR, 0.8) * 0.2)
    S["ice.release"] = mix(shatter(0.6, 52, 2600) * 0.7, bell(1760, 0.6, decay=0.5) * 0.3)
    S["ice.form"] = reverb(tink * 0.8, 0.5, 0.3)
    S["ice.shatter"] = reverb(shatter(0.9, 53), 0.5, 0.25)
    S["ice.crack"] = mix(crackle(0.4, 120, 54, 9000), boom(0.4, 200, 120, 55, 0.2) * 0.3)
    S["ice.freeze"] = mix(crackle(0.8, 90, 56, 8000) * swell(int(SR * 0.8), 0.4), band(noise(0.8, 57), 2000, 8000) * swell(int(SR * 0.8), 0.5) * 0.3)
    growl = tone(lambda t: 85 + 25 * np.sin(2 * np.pi * 3 * t), 1.6, "saw") * swell(int(SR * 1.6), 0.25)
    S["ice.roar"] = reverb(mix(band(growl, 60, 900) * 0.8, band(noise(1.6, 58), 300, 2500) * swell(int(SR * 1.6), 0.3) * 0.6), 0.7, 0.35)
    S["ice.breath"] = mix(sweep_band(noise(1.0, 59), 800, 4000, 0.9) * 0.8, band(noise(1.0, 60), 3000, 10000) * 0.3)
    S["ice.fall"] = mix(tone(lambda t: 2400 - 1800 * t, 0.8) * env(int(SR * 0.8), 0.05, 0.7) * 0.25, whoosh(0.8, 2500, 500, 61, 0.8) * 0.8)
    S["ice.impact"] = reverb(mix(boom(1.0, 120, 50, 62, 0.8), shatter(1.0, 63) * 0.7), 0.6, 0.3)
    S["ice.chime"] = reverb(mix(bell(880, 1.2, decay=1.2) * 0.4, bell(1320, 1.2, decay=1.0) * 0.3, bell(1760, 1.2, decay=0.8) * 0.2), 1.0, 0.4)
    S["ice.reflect"] = mix(bell(2093, 0.5, decay=0.4) * 0.5, crackle(0.3, 40, 64) * 0.3)
    r = rng(65)
    chain = np.zeros(int(SR * 0.8))
    for i in range(14):
        st = int(SR * r.rand() * 0.7)
        b = bell(900 + r.rand() * 900, 0.12, i, (1, 2.1, 3.7), 0.2)
        chain[st:st + len(b)] += b[:len(chain) - st] * r.rand()
    S["ice.chain"] = chain
    S["ice.wall"] = mix(band(noise(0.8, 66), 100, 1800) * swell(int(SR * 0.8), 0.6), crackle(0.8, 60, 67) * 0.5)
    S["ice.blizzard"] = mix(sweep_band(noise(1.6, 68), 400, 1800, 1.0) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.8 * t_(1.6))), band(noise(1.6, 69), 3000, 9000) * 0.25)
    S["ice.mirror"] = reverb(mix(tink[:int(SR * 0.6)] * 0.5, tone(lambda t: 600 + 1400 * t, 0.6) * env(int(SR * 0.6), 0.05, 0.4) * 0.2), 0.5, 0.4)
    S["ice.wing"] = whoosh(0.5, 300, 1400, 70, 0.4)
    S["ice.summon"] = reverb(mix(*[tone(f, 1.8) * swell(int(SR * 1.8), 0.6, 1.5) * 0.25 for f in (220, 277, 330, 440)], tink[:int(SR * 1.0)] * 0.3), 1.0, 0.45)
    S["ice.slash"] = mix(whoosh(0.35, 1200, 5000, 71, 0.35), bell(2400, 0.3, decay=0.3) * 0.2)
    S["ice.tick"] = bell(3200, 0.2, decay=0.15) * 0.6
    S["ice.pulse"] = reverb(mix(boom(1.8, 90, 30, 72, 0.7), shatter(1.8, 73, 1800) * 0.6, band(noise(1.8, 74), 2000, 8000) * env(int(SR * 1.8), 0.01, 0.8) * 0.4), 1.0, 0.4)
    S["ice.beam"] = mix(tone(880, 1.0) * 0.2, tone(1320, 1.0) * 0.12, band(noise(1.0, 75), 1500, 6000) * 0.3) * (0.7 + 0.3 * np.sin(2 * np.pi * 12 * t_(1.0)))
    S["ice.descent"] = reverb(mix(tone(lambda t: 120 - 70 * t / 2.6, 2.6) * swell(int(SR * 2.6), 0.85, 1.2) * 0.8, band(noise(2.6, 76), 30, 400) * swell(int(SR * 2.6), 0.9, 1.4)), 1.0, 0.3)
    # Blood --------------------------------------------------------------------------------
    S["blood.charge"] = mix(heartbeat(1.0, 46, 80, 0.9), gurgle(1.0, 81, 10) * 0.35)
    S["blood.release"] = mix(gurgle(0.5, 82, 30) * 0.6, whoosh(0.5, 400, 2000, 83, 0.25) * 0.6)
    S["blood.splash"] = mix(band(noise(0.6, 84), 300, 4000) * env(int(SR * 0.6), 0.002, 0.18), gurgle(0.6, 85, 25) * 0.5)
    S["blood.form"] = gurgle(0.8, 86, 18)
    S["blood.slice"] = mix(whoosh(0.35, 900, 4200, 87, 0.3), gurgle(0.35, 88, 20) * 0.3)
    clang = bell(330, 0.3, 0, (1, 2.4, 4.1), 0.5) * 0.4 + boom(0.3, 120, 60, 90, 0.5) * 0.6
    S["blood.drop"] = reverb(mix(whoosh(1.0, 2000, 400, 89, 0.7), pad(np.concatenate([np.zeros(int(SR * 0.7)), clang]), 1.0)), 0.6, 0.3)
    S["blood.hiss"] = mix(band(noise(1.2, 91), 2500, 9000) * swell(int(SR * 1.2), 0.3), band(tone(lambda t: 70 + 15 * np.sin(2 * np.pi * 4 * t), 1.2, "saw"), 50, 700) * swell(int(SR * 1.2), 0.5) * 0.5)
    S["blood.bite"] = mix(crackle(0.4, 160, 92, 5000) * 0.8, boom(0.4, 140, 70, 93, 0.4) * 0.6)
    S["blood.crown"] = reverb(mix(bell(523, 1.0, 0, (1, 2.5, 4.2, 6.3), 0.9) * 0.5, bell(784, 1.0, 1, (1, 2.5, 4.2), 0.7) * 0.3), 0.8, 0.4)
    S["blood.bloom"] = mix(band(noise(0.9, 94), 300, 2500) * swell(int(SR * 0.9), 0.5) * 0.5, bell(660, 0.9, decay=0.8) * 0.2, gurgle(0.9, 95, 8) * 0.3)
    S["blood.absorb"] = mix(boom(0.5, 100, 50, 96, 0.4), gurgle(0.5, 97, 20) * 0.5)
    S["blood.lance"] = mix(whoosh(0.4, 800, 3500, 98, 0.2), gurgle(0.4, 99, 25) * 0.3)
    S["blood.snap"] = mix(band(noise(0.3, 100), 2000, 8000) * env(int(SR * 0.3), 0.001, 0.03), bell(1400, 0.3, decay=0.2) * 0.2)
    S["blood.thorn"] = mix(crackle(0.5, 100, 101, 7000) * 0.6, whoosh(0.5, 500, 2500, 102, 0.15) * 0.5)
    S["blood.whirl"] = mix(sweep_band(noise(1.5, 103), 200, 900, 0.8) * (0.7 + 0.3 * np.sin(2 * np.pi * 3 * t_(1.5))), gurgle(1.5, 104, 16) * 0.5)
    S["blood.burst"] = reverb(mix(boom(1.4, 90, 35, 105, 0.6), gurgle(1.4, 106, 40) * 0.6, band(noise(1.4, 107), 400, 5000) * env(int(SR * 1.4), 0.005, 0.4) * 0.6), 0.8, 0.3)
    S["blood.step"] = mix(gurgle(0.6, 108, 30) * 0.6, shatter(0.6, 109, 1600) * 0.4)
    S["blood.flow"] = mix(gurgle(1.0, 110, 22) * 0.6, sweep_band(noise(1.0, 111), 300, 1200, 0.8) * 0.4)
    bell_low = band(tone(lambda t: 95 + 40 * np.sin(np.pi * t / 1.4), 1.4, "saw"), 60, 1200) * swell(int(SR * 1.4), 0.35, 1.2)
    S["blood.stag"] = reverb(mix(bell_low * 0.8, band(noise(1.4, 112), 400, 2200) * swell(int(SR * 1.4), 0.35) * 0.3), 1.0, 0.4)
    S["blood.hoof"] = boom(0.15, 180, 90, 113, 0.5)
    S["blood.heart"] = heartbeat(0.8, 46, 114)
    S["blood.heart_big"] = reverb(heartbeat(1.2, 34, 115, 1.4), 1.0, 0.45)
    S["blood.storm"] = reverb(mix(boom(2.5, 60, 25, 116, 1.0) * 0.8, band(noise(2.5, 117), 800, 6000) * 0.25, crackle(2.5, 30, 118, 3000) * 0.5), 0.8, 0.3)
    S["blood.shatter"] = reverb(mix(shatter(1.6, 119, 1400), boom(1.6, 70, 30, 120, 0.6) * 0.8), 0.9, 0.35)
    return S


VOLUMES = {"pressure.edict": 1.0, "ice.descent": 1.0, "blood.storm": 1.0}


def write_sounds(rp):
    os.makedirs(f"{rp}/sounds/grimoire", exist_ok=True)
    defs = {}
    tmp = f"{rp}/sounds/grimoire/_tmp.wav"
    for name, data in library().items():
        x = norm(np.asarray(data, np.float64))
        pcm = (x * 32767).astype('<i2')
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        fn = name.replace('.', '_')
        out = f"{rp}/sounds/grimoire/{fn}.ogg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", "3", out], check=True)
        cat = "ui" if name.startswith("ui.") else "player"
        defs[f"grimoire.{name}"] = {
            "category": cat,
            "min_distance": 1.0 if cat == "ui" else 6.0,
            "max_distance": 16.0 if cat == "ui" else 64.0,
            "sounds": [{"name": f"sounds/grimoire/{fn}", "volume": VOLUMES.get(name, 0.9), "load_on_low_memory": True}],
        }
    os.remove(tmp)
    dump(f"{rp}/sounds/sound_definitions.json", {"format_version": "1.20.20", "sound_definitions": defs})
    return sorted(defs)
