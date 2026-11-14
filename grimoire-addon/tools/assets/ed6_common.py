"""ED06 The World Before Names -- shared palette, painters, particles and the synthesized sound set.

Lineage order everywhere in ED06: 0 Nature, 1 Heat, 2 Water & Ice, 3 Air.
Asset modules of this slice: ed6_codex (great codex, dragon emblems, luminous skeletons),
ed6_world (primordial atmosphere set: horizon ring, fog, flora, standing stones) and
ed6_concord (crystalline bridges, aerial debris, pillar ring, ice shells, spiral wind, thermal blast).
"""
import math

import numpy as np

from kit import glyphs, synth as sy, tex
from kit.anim import LIFE, M
from kit.geo import Mat

from .a_fx_common import particles

BRONZE, BRONZE_HI, BRONZE_LO, IVORY, GOLD = "#8a6a3a", "#d8b46a", "#4a361c", "#e9dfc6", "#e8c27a"
MOSS, BASALT, EMBER, SAPPHIRE, ICE, SILVER = "#5a7a34", "#3b3a3c", "#ff8c2c", "#2f6fc6", "#eef9ff", "#a9c4dd"
DR = glyphs.DRACONIC

# per lineage: (bright, mid, deep) colours
LINEAGE = [("#d8ffb0", "#8fd45a", "#3f6a2a"),      # nature: moss green
           ("#ffe2a0", "#ff8c2c", "#a8320c"),      # heat: ember
           ("#dffbff", "#5fc8ff", "#1d4f9c"),      # water & ice: sapphire / ice
           ("#ffffff", "#bfe6ff", "#6f8fc8")]      # air: silver-blue
LINEAGE_NAMES = ["nature", "heat", "tide", "air"]

rgb, mix, px = tex.rgb, tex.mix, tex.px


def spin(rate):
    return M(f"q.life_time*{rate}", lambda t: t * rate)


def T(ctx, col, glow=0.0, a=1.0):
    t = np.zeros((ctx.h, ctx.w, 5))
    t[..., :3] = rgb(col) if isinstance(col, str) else col
    t[..., 3] = a
    t[..., 4] = glow
    return t


def worley(ix, iy, cell, seed):
    """(F1, F2-F1) of a jittered grid Worley pattern (pixel units)."""
    cx, cy = ix // cell, iy // cell
    f1 = np.full(ix.shape, 1e9)
    f2 = np.full(ix.shape, 1e9)
    for ox in (-1, 0, 1):
        for oy in (-1, 0, 1):
            gx, gy = cx + ox, cy + oy
            px_ = (gx + 0.15 + 0.7 * tex._hash(gx, gy, seed)) * cell
            py_ = (gy + 0.15 + 0.7 * tex._hash(gx, gy, seed + 31)) * cell
            d = np.hypot(ix + 0.5 - px_, iy + 0.5 - py_)
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            f1 = np.minimum(f1, d)
    return f1, f2 - f1


# ------------------------------------------------------------------------------------------- stone family
def stone_skins(seed=0, key="ed6st", runes=False):
    """Weathered magical stone with lichen; skin 'glass' = vitrified glowing amber glass with molten
    seams; skin 'obsidian' = cooled dark glass with violet sheen and faint embers in the seams."""
    def fn(ctx):
        ix, iy = px(ctx)
        n = tex.fbm(ix / 4.0 + ctx.variant * 7.1 + seed, iy / 4.0, 41 + seed)
        f1, edge = worley(ix, iy, 6, 17 + seed + ctx.variant)
        crack = edge < 0.9
        f1g, edge_g = worley(ix, iy, 11, 23 + seed + ctx.variant)
        thin = (edge_g < 0.55) & (tex.fbm(ix / 5.0, iy / 5.0, 8 + seed) > 0.42)
        if ctx.alt == "glass":
            base = mix(rgb("#ffb347"), rgb("#c2410c"), np.clip(n * 1.3 - 0.15, 0, 1)[..., None])
            base = mix(base, rgb("#fff1c2"), (np.clip(1.4 - f1 / 3.0, 0, 1) * 0.35)[..., None])
            base = mix(base, rgb("#ffd890"), (np.clip(1 - f1g / 6.0, 0, 1) * 0.4)[..., None])
            t = T(ctx, base, 0.55 + 0.25 * n)
            t[..., :3] = np.where(thin[..., None], rgb("#fffbe8"), t[..., :3])
            t[..., 4] = np.where(thin, 1.0, t[..., 4])
            streak = (np.abs(((ix - iy * 0.6 + ctx.variant * 5) % 11) - 1) < 0.6)
            t[..., :3] = np.where(streak[..., None], np.clip(t[..., :3] + 0.18, 0, 1), t[..., :3])
            return t
        if ctx.alt == "obsidian":
            base = mix(rgb("#1a1424"), rgb("#4a3a66"), np.clip(n * 1.2 - 0.2, 0, 1)[..., None])
            t = T(ctx, base, 0.05)
            sheen = (np.abs(((ix * 0.7 + iy + ctx.variant * 3) % 13) - 2) < 0.7)
            t[..., :3] = np.where(sheen[..., None], rgb("#9a8ac8"), t[..., :3])
            t[..., :3] = np.where(thin[..., None], rgb("#ff7a2a"), t[..., :3])
            t[..., 4] = np.where(thin, 0.6, t[..., 4])
            return t
        base = mix(rgb("#5f5a52"), rgb("#9a9286"), np.clip(n * 1.3 - 0.15, 0, 1)[..., None])
        t = T(ctx, base)
        lich = tex.fbm(ix / 2.5 + 40 + seed, iy / 2.5, 77) > 0.62
        t[..., :3] = np.where(lich[..., None], mix(rgb("#6f8a3a"), rgb("#b8c070"), tex._hash(ix, iy, 3)[..., None] * 0.6),
                              t[..., :3])
        t[..., :3] = np.where(crack[..., None], t[..., :3] * 0.62, t[..., :3])
        t = tex.grain(ctx, t, 0.06)
        return tex.edge(ctx, t, 0.14)
    return Mat(fn, f"{key}{seed}")


def rune_plate(gi, color, glow=1.0, key=None):
    return tex.bitmap_cut(DR[gi % len(DR)], color, glow=glow, color2="#ffffff", key=key)


# ------------------------------------------------------------------------------------------- particles
def build_particles(pack):
    """Every ED06 effect is sized to read at 10-45 blocks from the caster (big sprites, long lives)."""
    fx = particles(pack)
    E = fx.effect
    # ---- the primordial atmosphere (continuous ambient layers)
    E("ed6_spore", "dot", count=2, life=(3.0, 5.0), size=(0.14, 0.03), shape=("sphere", 3.5), speed=(0.05, 0.3),
      accel=(0, 0.15, 0), drag=0.4, colors=["#f4ffc8ff", "#c8f07acc", "#9cd45a00"])
    E("ed6_mote", "glow", count=1, life=(3.5, 5.5), size=(0.26, 0.04), shape=("sphere", 4.0), speed=(0.1, 0.35),
      accel=(0, 0.12, 0), drag=0.5, colors=["#fff6d8ff", "#ffe2a0cc", "#e8c27a00"])
    E("ed6_ember_mote", "ember", count=2, life=(2.2, 3.6), size=(0.2, 0.03), shape=("sphere", 3.0), speed=(0.2, 0.7),
      accel=(0, 0.55, 0), drag=0.5, colors=["#fff0b0ff", "#ff9a3add", "#a8320c00"])
    E("ed6_mist", "smoke", count=2, life=(4.0, 6.0), size=(2.4, 4.6), shape=("disc", 4.0), speed=(0.05, 0.25),
      accel=(0, 0.04, 0), drag=0.6, colors=["#cfd8c400", "#c4d0bc55", "#b8c4b03a", "#a8b4a000"], blend="blend", spin=(360, 6))
    E("ed6_pollen_drift", None, sprites=["dot", "leaf"], count=2, life=(2.6, 4.0), size=(0.17, 0.08), shape=("sphere", 3.0),
      speed=(0.2, 0.6), accel=(0.3, -0.1, 0.1), drag=0.5, colors=["#e8ffb8ff", "#8fd45acc", "#4f8a3a00"], blend="alpha",
      spin=(360, 60))
    E("ed6_leaf_fall", "leaf", count=2, life=(2.5, 4.0), size=(0.28, 0.2), shape=("sphere", 3.0), speed=(0.2, 0.6),
      accel=(0.3, -0.8, 0.15), drag=0.8, colors=["#a8d860ff", "#5f9a34ff", "#3f6a2a00"], blend="alpha", spin=(360, 140))
    E("ed6_snow", "flake", count=2, life=(2.5, 4.0), size=(0.22, 0.12), shape=("sphere", 3.0), speed=(0.1, 0.4),
      accel=(0.1, -0.55, 0), drag=0.8, colors=["#ffffffff", "#dff6ffdd", "#9fd8ff00"], spin=(360, 90))
    E("ed6_droplet", None, sprites=["drop", "dot"], count=2, life=(1.2, 2.0), size=(0.22, 0.08), shape=("sphere", 2.5),
      speed=(0.3, 0.9), accel=(0, -2.5, 0), drag=0.6, colors=["#f0fcffff", "#7fd8ffdd", "#2a6fb000"])
    E("ed6_haze", "wave", count=2, life=(1.2, 2.0), size=(0.9, 1.9), shape=("box", (2.0, 0.3, 2.0)), direction=(0, 1, 0),
      speed=(0.6, 1.4), colors=["#fff2d000", "#ffd8a038", "#ffb06a26", "#ff8a4000"], blend="blend")
    E("ed6_wind", None, sprites=["wave", "slash", "arc"], count=1, life=(0.9, 1.5), size=(1.5, 0.4), shape=("sphere", 3.0),
      speed=(1.0, 3.0), drag=0.4, colors=["#ffffffcc", "#e4f7ff88", "#bfe6ff00"], spin=(360, 40))
    E("ed6_rune_rise", None, sprites=[f"rune{i}" for i in range(1, 7)], count=2, life=(2.0, 3.2), size=(0.38, 0.1),
      shape=("disc", 3.0), direction=(0, 1, 0), speed=(0.6, 1.4), drag=0.3, colors=["#fff6dcff", "#ffe2a0ee", "#e8c27a00"])
    # ---- per-dragon trails (big enough to follow a creature 15-45 blocks away)
    E("ed6_trail_nature", "puff", count=2, life=(1.2, 2.2), size=(0.9, 2.4), shape=("disc", 1.5), speed=(0.4, 1.2),
      accel=(0, 0.25, 0), drag=1.2, colors=["#c8bca4aa", "#8a7f6a55", "#6a604f00"], blend="blend", spin=(360, 30))
    E("ed6_trail_heat", None, sprites=["ember", "glow", "spark"], count=3, life=(0.5, 1.0), size=(0.42, 0.04),
      shape=("sphere", 1.2), speed=(0.5, 2.0), accel=(0, 1.5, 0), drag=0.8,
      colors=["#ffffffff", "#ffd27aff", "#ff6a1acc", "#5a1a0a00"])
    E("ed6_trail_tide", None, sprites=["drop", "ring", "dot"], count=3, life=(0.8, 1.4), size=(0.32, 0.05),
      shape=("sphere", 1.0), speed=(0.2, 0.8), accel=(0, -1.5, 0), drag=0.6, colors=["#ffffffff", "#9fe6ffee", "#3f8fd000"])
    E("ed6_trail_air", "dot", count=2, life=(0.8, 1.3), size=(0.34, 0.0), shape=("sphere", 0.3), speed=(0.0, 0.2),
      colors=["#ffffffee", "#d8f0ffaa", "#a8c8ff00"])
    # ---- heartbeats: a flat ground ring, rising beams, a coloured flash and a spark burst per lineage
    for i, n in enumerate(LINEAGE_NAMES):
        b, m, d = LINEAGE[i]
        E(f"ed6_beat_{n}", "ring", count=1, life=(0.8, 0.9), size=(0.6, 9.0), facing="emitter_transform_xz",
          colors=[b + "ff", m + "cc", d + "00"])
        E(f"ed6_rise_{n}", "beam", count=8, life=(0.6, 1.0), size=(0.16, 0.03), size_y=(1.4, 3.4), shape=("disc", 3.5),
          direction=(0, 1, 0), speed=(3, 7), colors=[b + "ff", m + "cc", d + "00"], facing="lookat_y")
        E(f"ed6_flash_{n}", "glow", count=1, life=(0.4, 0.55), size=(2.2, 7.5), colors=[b + "ff", m + "aa", d + "00"])
        extra = ["leaf", "ember", "flake", "feather"][i]
        E(f"ed6_burst_{n}", None, sprites=["star", "spark", extra], count=18, life=(0.6, 1.2), size=(0.42, 0.05),
          shape=("sphere", 0.8), speed=(5, 11), drag=1.4, colors=["#ffffffff", b + "ff", m + "cc", d + "00"], spin=(360, 200))
    for i, n in enumerate(LINEAGE_NAMES):                      # leyline sparks running over the ground
        b, m, d = LINEAGE[i]
        E(f"ed6_ley_{n}", None, sprites=["glow", "dot"], count=2, life=(0.5, 0.9), size=(0.36, 0.05), shape=("sphere", 0.25),
          speed=(0.1, 0.4), accel=(0, 0.5, 0), colors=["#ffffffff", b + "ff", m + "aa", d + "00"])
    E("ed6_wave", "ring", count=1, life=(1.0, 1.1), size=(1.0, 22.0), facing="emitter_transform_xz",
      colors=["#ffffffff", "#ffe2a0cc", "#e8c27a55", "#8a6a3a00"])
    E("ed6_column", "beam", count=8, life=(0.7, 1.2), size=(0.28, 0.05), size_y=(3.0, 9.0), shape=("disc", 1.0),
      direction=(0, 1, 0), speed=(6, 12), colors=["#ffffffff", "#fff3c4ee", "#e8c27a00"], facing="lookat_y")
    E("ed6_ring_v", "ringthin", count=1, life=(0.5, 0.6), size=(0.8, 8.0), colors=["#ffffffff", "#ffe2a0aa", "#e8c27a00"])
    # ---- codex
    E("ed6_codex_rune", None, sprites=[f"rune{i}" for i in range(1, 7)], count=5, life=(1.2, 2.0), size=(0.32, 0.1),
      shape=("sphere", 2.0), speed=(0.3, 0.9), accel=(0, 0.5, 0), drag=0.6, colors=["#fff3c4ff", "#e8c27aff", "#8a6a3a00"])
    E("ed6_codex_glint", None, sprites=["star", "spark"], count=10, life=(0.4, 0.9), size=(0.3, 0.0), shape=("sphere", 1.8),
      speed=(1.5, 4.0), drag=1.5, colors=["#ffffffff", "#ffe2a0ff", "#8a6a3a00"], spin=(360, 300))
    E("ed6_stream", None, sprites=["glow", "rune2", "rune4", "rune6"], count=3, life=(0.5, 0.9), size=(0.42, 0.05),
      shape=("sphere", 0.4), speed=(0.1, 0.5), drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#e8c27a00"])
    # ---- luminous skeleton and inscription streams, the seal of the codex, the restoring wave
    E("ed6_bone_dust", None, sprites=["bone", "dot", "rune3", "rune5"], count=8, life=(1.0, 1.8), size=(0.26, 0.05),
      shape=("sphere", 2.2), speed=(0.3, 1.2), accel=(0, 0.6, 0), drag=0.8, colors=["#fffbe8ff", "#ffe2a0cc", "#e8c27a00"],
      spin=(360, 120))
    E("ed6_inscribe", None, sprites=[f"rune{i}" for i in range(1, 7)], count=3, life=(0.7, 1.2), size=(0.34, 0.1),
      shape=("sphere", 0.6), speed=(0.1, 0.4), drag=1.0, colors=["#ffffffff", "#fff3c4ff", "#e8c27a00"])
    E("ed6_seal", None, sprites=["star", "glow", "spark"], count=30, life=(0.8, 1.4), size=(0.55, 0.05), shape=("sphere", 1.0),
      speed=(8, 16), drag=1.6, colors=["#ffffffff", "#fff3c4ff", "#ffd27acc", "#e8c27a00"], spin=(360, 300))
    E("ed6_light_wave", "ring", count=1, life=(1.4, 1.5), size=(1.0, 30.0), facing="emitter_transform_xz",
      colors=["#ffffffff", "#fff3c4dd", "#ffe2a066", "#e8c27a00"])
    # ---- the dominion and the concord
    E("ed6_updraft", "beam", count=10, life=(0.7, 1.2), size=(0.16, 0.03), size_y=(1.6, 3.4), shape=("disc", 2.4),
      direction=(0, 1, 0), speed=(6, 12), colors=["#ffffffcc", "#d8f4ffaa", "#9fd8ff00"], facing="lookat_y")
    E("ed6_debris_fall", None, sprites=["rock", "leaf", "shard"], count=12, life=(0.8, 1.4), size=(0.26, 0.16),
      shape=("disc", 3.0), direction=(0, -1, 0), speed=(1, 3), accel=(0, -14, 0), colors=["#7a7064ff", "#5a8a3aff", "#cfefffff"],
      blend="alpha", spin=(360, 260), collide=True)
    E("ed6_glass_shard", "shard", count=12, life=(0.6, 1.1), size=(0.26, 0.08), shape=("sphere", 0.8), speed=(4, 9),
      accel=(0, -10, 0), drag=0.4, colors=["#fff6d0ff", "#ffa040ff", "#5a1a0a00"], spin=(360, 400))
    E("ed6_sizzle", "smoke", count=6, life=(0.9, 1.6), size=(0.5, 1.6), shape=("disc", 1.2), direction=(0, 1, 0),
      speed=(0.8, 2.0), drag=1.0, colors=["#ffe8c8aa", "#c8b8a855", "#9a8a7a00"], blend="blend", spin=(360, 40))
    E("ed6_thermal", None, sprites=["ember", "glow", "spark"], count=24, life=(0.6, 1.3), size=(0.55, 0.05),
      shape=("sphere", 1.5), speed=(5, 12), accel=(0, 2, 0), drag=1.4, colors=["#ffffffff", "#ffe08aff", "#ff6a1aff", "#5a1a0a00"])
    E("ed6_thermal_ring", "ring", count=1, life=(0.8, 0.9), size=(1.0, 16.0), facing="emitter_transform_xz",
      colors=["#ffffffff", "#ffd27aee", "#ff6a1a00"])
    E("ed6_smoke", "smoke", count=4, life=(2.0, 3.5), size=(1.4, 4.0), shape=("sphere", 2.0), speed=(0.3, 1.0),
      accel=(0, 0.8, 0), drag=0.8, colors=["#5a504888", "#3a343066", "#2a262400"], blend="blend", spin=(360, 20))
    E("ed6_geo_shock", "ringthin", count=1, life=(0.6, 0.7), size=(0.8, 10.0), facing="emitter_transform_xz",
      colors=["#fff6dcff", "#c8ff9ad0", "#8a6a3a00"])
    E("ed6_frost_layer", "ringthin", count=1, life=(0.6, 0.7), size=(0.5, 7.0), facing="emitter_transform_xz",
      colors=["#ffffffff", "#bfeaffdd", "#5fc8ff00"])
    E("ed6_spiral_debris", None, sprites=["shard", "leaf", "flake", "puff"], count=10, life=(1.0, 1.8), size=(0.26, 0.12),
      shape=("disc", 4.0), speed=(1, 3), accel=(0, 4, 0), drag=0.6, colors=["#ffffffff", "#cfe8f0ee", "#9ab8c800"],
      blend="alpha", spin=(360, 420))
    E("ed6_concord", None, sprites=["rune1", "rune2", "rune4", "star"], count=12, life=(1.0, 1.6), size=(0.4, 0.05),
      shape=("sphere", 2.5, "surface"), direction="inwards", speed=(1.5, 3.0), drag=0.3,
      colors=["#ffffffff", "#ffe2a0ff", "#e8c27a00"])


# ------------------------------------------------------------------------------------------- sounds
def _beat(f, dur=1.6):
    return sy.heartbeat(dur, f)


def build_sounds(pack):
    rv = sy.reverb
    # ---- four ancient heartbeats, each coloured by its lineage
    hb_n = sy.at(2.2, (0.0, _beat(38) * 1.0), (0.0, sy.rumble(2.0, 34, 1.4) * 0.5),
                 (0.05, sy.lowpass(sy.creak(1.4, 40, 60, 0.4), 500) * 0.35), (0.3, sy.lowpass(sy.crack(1.2, 700, 30), 1200) * 0.25))
    sy.save(pack, "ed6_heart_nature", rv(hb_n, 2.2, 0.4), max_distance=96)
    hb_h = sy.at(2.0, (0.0, _beat(46) * 1.0), (0.02, sy.bandpass(sy.noise(1.6), 2400, 1.0) * sy.env(1.6, 0.05, 0.2, 0.5, 0.8) * 0.3),
                 (0.0, sy.lowpass(sy.roar(1.2, 70, 50, 22, 0.8, (300, 700), 0.6, 0.1), 900) * 0.3))
    sy.save(pack, "ed6_heart_heat", rv(hb_h, 1.8, 0.35), max_distance=96)
    hb_t = sy.at(2.2, (0.0, _beat(42) * 1.0), (0.05, sy.lowpass(sy.water(1.8, 26, 380), 1800) * 0.4),
                 (0.3, sy.bell(1568, 1.2, 0.6) * 0.18), (0.58, sy.bell(2093, 1.0, 0.6) * 0.12))
    sy.save(pack, "ed6_heart_tide", rv(hb_t, 2.6, 0.45), max_distance=96)
    hb_a = sy.at(2.0, (0.0, _beat(50) * 0.95), (0.0, sy.wind(1.9, 300, 1600, 2.0, 0.6) * 0.35),
                 (0.25, sy.whoosh(0.5, 600, 2400) * 0.3), (0.55, sy.whoosh(0.4, 900, 3000) * 0.22))
    sy.save(pack, "ed6_heart_air", rv(hb_a, 2.0, 0.4), max_distance=96)
    all4 = sy.at(2.6, (0.0, _beat(38)), (0.08, _beat(46) * 0.8), (0.16, _beat(42) * 0.7), (0.24, _beat(50) * 0.6),
                 (0.0, sy.rumble(2.4, 30, 1.0) * 0.5))
    sy.save(pack, "ed6_heart_all", rv(all4, 2.6, 0.45), max_distance=128)

    # ---- primordial ambience bed: insects, warm wind, deep earth, a far call (5 s, retriggered)
    def bed(seed, call_f):
        rng = np.random.default_rng(seed)
        d = 5.2
        parts = [(0.0, sy.lowpass(sy.wind(d, 180, 520, 1.4, 0.7), 900) * 0.55), (0.0, sy.rumble(d, 32, 0.6) * 0.45)]
        for k in range(9):                                     # insect chirr pulses
            f = rng.uniform(3800, 6200)
            ch = sy.osc(f, 0.35) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rng.uniform(28, 46) * sy.t_axis(0.35))))
            parts.append((rng.uniform(0, d - 0.4), sy.bandpass(ch, f, 6) * sy.env(0.35, 0.02, 0.05, 0.8, 0.1) * 0.06))
        call = sy.lowpass(sy.roar(1.8, call_f, call_f * 0.7, 9, 0.2, (260, 640), 0.2, 0.3), 700) * 0.22
        parts.append((rng.uniform(1.0, 2.4), call))
        for k in range(5):                                     # dripping / bubbling earth
            parts.append((rng.uniform(0, d - 0.3), sy.lowpass(sy.water(0.3, 4, 220), 900) * 0.12))
        return rv(sy.at(d, *parts), 2.0, 0.4)
    sy.save(pack, "ed6_ambience", bed(3, 70), variants=[bed(5, 58), bed(9, 82)], max_distance=96, volume=0.85)

    # ---- the codex
    rise = sy.at(2.4, (0.0, sy.pad(73.4, 2.3, cutoff=900) * 0.5), (0.2, sy.bell(293.7, 1.8, 0.7, 1.3) * 0.4),
                 (0.5, sy.bell(220, 1.6, 0.6, 1.4) * 0.3), (0.3, sy.shimmer(1.6, 1600, 14) * 0.2),
                 (0.0, sy.whoosh(1.4, 120, 900) * 0.3))
    sy.save(pack, "ed6_codex_rise", rv(rise, 2.4, 0.45), max_distance=80)
    clinks = [(0.0, sy.lowpass(sy.creak(1.6, 70, 120, 0.4), 1400) * 0.4), (0.0, sy.whoosh(1.6, 200, 1400) * 0.3)]
    for k in range(10):
        clinks.append((0.08 + k * 0.13, sy.bell(900 + 137 * ((k * 5) % 7), 0.35, 1.2, 1.6) * (0.25 - k * 0.012)))
    sy.save(pack, "ed6_codex_unbind", rv(sy.at(2.0, *clinks), 1.6, 0.35), max_distance=80)
    opn = sy.at(1.6, (0.0, sy.lowpass(sy.creak(1.0, 60, 140, 0.3), 1200) * 0.5), (0.4, sy.whoosh(0.8, 400, 2600) * 0.45),
                (0.7, sy.scribble(0.8, 6) * 0.3), (0.5, sy.choir(146.8, 1.0, "oh", voices=3) * 0.3))
    sy.save(pack, "ed6_codex_open", rv(opn, 1.8, 0.4), max_distance=80)
    absorb = sy.at(1.4, (0.0, sy.whoosh(1.0, 2600, 300) * 0.5), (0.5, sy.bell(587.3, 0.9, 0.8, 1.2) * 0.35),
                   (0.55, sy.choir(293.7, 0.8, "oo", voices=3) * 0.3), (0.2, sy.scribble(1.0, 8) * 0.25))
    sy.save(pack, "ed6_absorb", rv(absorb, 1.6, 0.4), variants=[rv(sy.pitch(absorb, 1.12), 1.6, 0.4),
                                                               rv(sy.pitch(absorb, 0.9), 1.6, 0.4)], max_distance=80)
    close = sy.at(2.4, (0.0, sy.thump(0.9, 90, 40, 0.5) * 0.6), (0.0, sy.bell(146.8, 2.2, 0.6, 1.2) * 0.45),
                  (0.05, sy.bell(220, 2.0, 0.6, 1.25) * 0.3), (0.3, sy.pad(110, 2.0, cutoff=700) * 0.35),
                  (0.6, sy.shimmer(1.6, 2400, 12)[::-1] * 0.2))
    sy.save(pack, "ed6_codex_close", rv(close, 2.6, 0.45), max_distance=96)

    # ---- atmosphere set
    rust = sy.at(2.2, (0.0, sy.bandpass(sy.noise(2.0), 3200, 0.8) * sy.env(2.0, 0.3, 0.4, 0.6, 0.8) * 0.4),
                 (0.2, sy.creak(0.9, 160, 330, 0.3) * 0.25), (0.8, sy.creak(0.8, 120, 260, 0.3) * 0.2),
                 (0.4, sy.shimmer(1.4, 1400, 10) * 0.12))
    sy.save(pack, "ed6_sprout", rv(rust, 1.4, 0.35), variants=[rv(sy.pitch(rust, 1.15), 1.4, 0.35)], max_distance=56)
    grind = sy.at(1.8, (0.0, sy.lowpass(sy.creak(1.6, 45, 75, 0.5), 700) * 0.6), (0.0, sy.rumble(1.6, 46, 3) * 0.6),
                  (0.6, sy.lowpass(sy.crack(1.0, 1200, 30), 1800) * 0.3))
    sy.save(pack, "ed6_stone_rise", rv(grind, 1.4, 0.3), variants=[rv(sy.pitch(grind, 0.9), 1.4, 0.3)], max_distance=64)
    vit = sy.at(1.8, (0.0, sy.bandpass(sy.noise(1.5), 4200, 0.9) * sy.env(1.5, 0.02, 0.3, 0.5, 0.9) * 0.5),
                (0.1, sy.crack(1.2, 6500, 26) * 0.35), (0.2, sy.bell(1760, 1.2, 1.4, 1.8) * 0.2),
                (0.0, sy.thump(0.5, 140, 60, 0.4) * 0.4))
    sy.save(pack, "ed6_vitrify", rv(vit, 1.3, 0.3), variants=[rv(sy.pitch(vit, 1.15), 1.3, 0.3)], max_distance=56)
    hush_bed = sy.at(4.4, (0.0, sy.lowpass(sy.wind(4.2, 200, 420, 1.2, 0.3), 700) * 0.5), (0.0, sy.pad(98, 4.2, cutoff=600, attack=1.2, release=2.0) * 0.4),
                     (0.6, sy.choir(196, 3.4, "oo", voices=4, attack=1.0, release=1.6) * 0.3), (1.6, sy.shimmer(2.4, 2600, 14) * 0.12))
    sy.save(pack, "ed6_hush", rv(hush_bed, 3.0, 0.5), max_distance=128)
    clear = sy.at(3.0, (0.0, sy.whoosh(2.6, 1800, 200) * 0.4), (0.0, sy.lowpass(sy.rumble(2.8, 40, 1.0), 300) * 0.5),
                  (0.8, sy.shimmer(2.0, 1200, 10)[::-1] * 0.15))
    sy.save(pack, "ed6_world_fade", rv(clear, 2.0, 0.4), max_distance=128)

    # ---- dominion and concord set-pieces
    cry = [(0.0, sy.crack(1.4, 7000, 30) * 0.4), (0.0, sy.lowpass(sy.water(1.2, 20, 700), 2400) * 0.3)]
    for k in range(7):
        cry.append((0.05 + k * 0.14, sy.pluck(1200 * (1.12 ** k), 0.5, 0.9) * 0.16))
    br = sy.at(1.8, *cry)
    sy.save(pack, "ed6_bridge", rv(br, 1.6, 0.4), variants=[rv(sy.pitch(br, 0.9), 1.6, 0.4)], max_distance=64)
    lift = sy.at(2.0, (0.0, sy.rumble(1.8, 50, 3) * 0.6), (0.0, sy.wind(2.0, 200, 1400, 1.6, 0.5) * 0.5),
                 (0.3, sy.lowpass(sy.crack(1.4, 900, 40), 1500) * 0.35), (0.6, sy.bandpass(sy.noise(1.2), 3000, 1.0) * 0.12))
    sy.save(pack, "ed6_debris_lift", rv(lift, 1.6, 0.35), max_distance=80)
    fall = sy.at(1.6, (0.0, sy.whoosh(0.6, 1600, 200) * 0.4), (0.4, sy.thump(0.8, 80, 30, 0.6) * 0.6),
                 (0.42, sy.crack(1.0, 1800, 50) * 0.45))
    sy.save(pack, "ed6_debris_fall", rv(fall, 1.2, 0.3), max_distance=72)
    ringr = sy.at(3.0, (0.0, sy.rumble(2.8, 36, 1.4) * 0.8), (0.0, sy.lowpass(sy.creak(2.4, 35, 60, 0.6), 600) * 0.6),
                  (0.5, sy.thump(1.0, 70, 26, 0.6) * 0.6), (1.1, sy.thump(1.0, 64, 24, 0.6) * 0.5),
                  (1.6, sy.lowpass(sy.crack(1.2, 1100, 60), 1600) * 0.4))
    sy.save(pack, "ed6_ring_rise", rv(ringr, 2.4, 0.45), max_distance=128)
    shock = sy.at(2.0, (0.0, sy.thump(1.4, 75, 20, 0.8)), (0.0, sy.crack(1.0, 2600, 40) * 0.6),
                  (0.08, sy.rumble(1.8, 40, 2.0) * 0.7), (0.25, sy.lowpass(sy.crack(1.6, 700, 70), 1300) * 0.4))
    sy.save(pack, "ed6_geo_shock", rv(shock, 1.8, 0.4), variants=[rv(sy.pitch(shock, 0.88), 1.8, 0.4)], max_distance=128)
    layers = [(0.0, sy.lowpass(sy.water(0.8, 22, 600), 2000) * 0.4)]
    for k in range(3):
        layers += [(0.25 + k * 0.6, sy.crack(0.9, 5200 + 900 * k, 24) * 0.45), (0.27 + k * 0.6, sy.bell(988 * (1.26 ** k), 0.8, 1.3, 1.7) * 0.2)]
    sy.save(pack, "ed6_ice_layers", rv(sy.at(2.6, *layers), 1.8, 0.4), max_distance=96)
    spiral = sy.at(3.0, (0.0, sy.wind(3.0, 250, 2600, 2.4, 0.7) * 0.8), (0.0, sy.whoosh(1.2, 200, 1800) * 0.4),
                   (1.0, sy.whoosh(1.0, 400, 2600) * 0.35), (0.6, sy.crack(2.0, 6000, 30) * 0.15),
                   (0.0, sy.lowpass(sy.rumble(3.0, 50, 6), 200) * 0.3))
    sy.save(pack, "ed6_spiral", rv(spiral, 1.8, 0.35), max_distance=112)
    det = sy.at(3.0, (0.0, sy.thump(2.0, 60, 16, 1.0)), (0.0, sy.crack(1.2, 4000, 60) * 0.6),
                (0.02, sy.bandpass(sy.noise(2.6), 900, 0.6) * sy.env(2.6, 0.01, 0.4, 0.4, 1.8) * 0.8),
                (0.05, sy.rumble(2.8, 30, 1.0) * 0.8), (0.2, sy.crack(2.0, 7000, 80) * 0.3),
                (0.1, sy.lowpass(sy.roar(1.6, 80, 40, 30, 0.9, (300, 800), 0.8, 0.0), 1200) * 0.4))
    sy.save(pack, "ed6_detonation", rv(det, 2.8, 0.45), max_distance=160)
    charge = sy.at(2.4, (0.0, sy.roar(2.2, 120, 70, 34, 0.75, (520, 1250), 0.45, 0.35) * 0.8),
                   (0.0, sy.bandpass(sy.noise(2.2), 1800, 0.8) * sy.env(2.2, 0.3, 0.4, 0.7, 0.6) * 0.4),
                   (0.0, sy.whoosh(2.2, 150, 2200) * 0.35))
    sy.save(pack, "ed6_final_charge", rv(charge, 1.6, 0.35), max_distance=128)

    # ---- the concord motif: built from the four voices (deep horn, growl, resonant glass, whistle) stacking
    horn = sy.lowpass(sy.roar(2.6, 55, 52, 8, 0.1, (300, 700), 0.1, 0.05), 900)
    growl = sy.lowpass(sy.roar(2.2, 98, 92, 30, 0.7, (480, 1100), 0.35, 0.05), 2400)
    glass = sy.mixdown([sy.bell(659.3, 2.0, 0.6, 1.0), sy.bell(987.8, 1.8, 0.5, 1.0) * 0.6])
    whistle = sy.osc(sy.sweep(1318, 1480, 1.6, 0.5), wave_="sine") * sy.env(1.6, 0.2, 0.3, 0.7, 0.6)
    motif = sy.at(3.6, (0.0, horn * 0.55), (0.5, growl * 0.35), (1.0, glass * 0.35), (1.5, whistle * 0.18),
                  (1.5, sy.pad(110, 2.0, cutoff=900) * 0.3))
    sy.save(pack, "ed6_concord", rv(motif, 2.8, 0.45), max_distance=160)
    insc = sy.at(1.6, (0.0, sy.scribble(1.2, 9) * 0.45), (0.0, sy.shimmer(1.4, 2000, 16) * 0.3),
                 (0.3, sy.choir(392, 1.1, "ah", voices=3, attack=0.3) * 0.3))
    sy.save(pack, "ed6_inscribe", rv(insc, 1.8, 0.45), variants=[rv(sy.pitch(insc, 0.84), 1.8, 0.45)], max_distance=80)
    strm = sy.at(1.8, (0.0, sy.whoosh(1.4, 300, 3200) * 0.5), (0.2, sy.choir(523.3, 1.2, "oo", voices=3) * 0.3),
                 (0.5, sy.shimmer(1.2, 2600, 12) * 0.25))
    sy.save(pack, "ed6_stream", rv(strm, 1.8, 0.45), variants=[rv(sy.pitch(strm, 0.89), 1.8, 0.45)], max_distance=96)

    # ---- the finale: a rising swell under the final charge, the seal of the codex, the restoring wave
    sw_d = 4.2
    swell = sy.at(sw_d, (0.0, sy.rumble(sw_d, 30, 1.6) * sy.env(sw_d, 2.6, 0.2, 1.0, 0.3) * 0.8),
                  (0.0, sy.pad(55, sw_d, cutoff=500, attack=2.8, release=0.3) * 0.45),
                  (0.6, sy.choir(110, 3.4, "ah", voices=5, attack=2.4, release=0.3) * 0.3),
                  (1.4, sy.wind(2.6, 300, 2400, 2.0, 0.6) * sy.env(2.6, 1.6, 0.2, 1.0, 0.2) * 0.35),
                  (2.4, sy.shimmer(1.6, 1800, 16) * 0.18))
    sy.save(pack, "ed6_swell", rv(swell, 1.8, 0.35), max_distance=160)
    seal = sy.at(3.4, (0.0, sy.thump(1.6, 70, 22, 0.9)), (0.0, sy.crack(0.6, 3000, 30) * 0.3),
                 (0.02, sy.bell(146.8, 3.0, 0.7, 1.15) * 0.55), (0.04, sy.bell(220.0, 2.8, 0.7, 1.2) * 0.4),
                 (0.06, sy.bell(293.7, 2.6, 0.8, 1.25) * 0.3), (0.0, sy.choir(146.8, 3.0, "oh", voices=5, attack=0.05) * 0.3),
                 (0.1, sy.shimmer(2.6, 2400, 20) * 0.25), (0.0, sy.rumble(2.6, 34, 1.2) * 0.5))
    sy.save(pack, "ed6_seal", rv(seal, 3.0, 0.5), max_distance=160)
    rest = sy.at(3.2, (0.0, sy.whoosh(2.8, 2400, 260) * 0.45), (0.2, sy.shimmer(2.6, 1500, 18)[::-1] * 0.2),
                 (0.0, sy.lowpass(sy.wind(3.0, 200, 700, 1.4, 0.3), 900) * 0.35),
                 (0.6, sy.choir(196, 2.4, "oo", voices=4, attack=0.6, release=1.2) * 0.22))
    sy.save(pack, "ed6_restore", rv(rest, 2.4, 0.45), max_distance=160)


def build(pack):
    build_particles(pack)
    build_sounds(pack)
