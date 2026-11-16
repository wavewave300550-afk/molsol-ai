"""Animated previews of every ability effect, rendered from the particle files in the pack.

Each scenario re-enacts what the script does for one ability (which identifiers it spawns,
where, when and with which variables - see the inventory in docs/CREATIVE.md) next to the
race's model.  One GIF per race (2 x 2 abilities); --sheets adds a 4-frame contact sheet.

    python3 tools/vfx_gifs.py --races nurariten,spaghetti --out docs/images
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

from kit.tex import paint  # noqa: E402
from models import bathyas, dinosauroid, golem, jackalope, nurariten, octamyces, salamander, spaghetti, xenentoma  # noqa: E402
from vfx import preview  # noqa: E402

RP = os.path.join(ROOT, "packs", "PlayableRaces_RP")
MODS = {"salamander": salamander, "golem": golem, "jackalope": jackalope, "xenentoma": xenentoma, "spaghetti": spaghetti,
        "nurariten": nurariten, "dinosauroid": dinosauroid, "bathyas": bathyas, "octamyces": octamyces}
TEXKEY = {"salamander": "bloom", "golem": "base", "jackalope": "base", "xenentoma": "base", "spaghetti": "base", "nurariten": "base",
          "dinosauroid": "base", "bathyas": "base", "octamyces": "base"}


def load_effects():
    eff = {}
    for f in glob.glob(os.path.join(RP, "particles", "plrace", "*.json")):
        d = json.load(open(f))
        eff[d["particle_effect"]["description"]["identifier"].split(":")[1]] = d
    atl = {}
    for name in ("particles", "particles_ex", "particles_vfx"):
        atl[f"textures/plrace/races/particles/{name}"] = Image.open(os.path.join(RP, "textures/plrace/races/particles", f"{name}.png")).convert("RGBA")
    return eff, atl


def line(a, b):
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    return {"dx": dx / L, "dy": dy / L, "dz": dz / L, "len": L}


def ring_pts(c, r, n, a0=0.0):
    return [(c[0] + math.cos(math.radians(a0 + k * 360 / n)) * r, c[1], c[2] + math.sin(math.radians(a0 + k * 360 / n)) * r) for k in range(n)]


SILVER = {"red": 0.85, "green": 0.88, "blue": 1.0}
FRAME_PATH = [(math.sin(k / 2.2) * 2.5, 0, -4 - 0.5 * k) for k in range(8)]   # a recorded walk for the Eleventh Frame preview
CRIMSON = {"red": 1.0, "green": 0.16, "blue": 0.24}

# (label, spawns [(t, effect, origin, vars)], camera overrides)
SCEN = {
    "salamander": [
        ("Sundew Snare", [(0.0, "snare_strand", (-0.38, 1.25, -0.35), line((-0.38, 1.25, -0.35), (0, 1.1, -6)))]
         + [(0.05 + 0.5 * k, "ensnared", (0, 0, -6), {}) for k in range(3)], {}),
        ("Carnivorous Embrace", [(0.0, "trap_snap", (0, 1.2, -2.4), {}), (0.15, "heal_leaf", (0, 1.0, 0), {})], {}),
        ("Root Metamorphosis", [(0.0, "root_burst", (0, 0, 0), {}), (0.9, "heal_leaf", (0, 1.2, 0), {})], {}),
        ("Bladder Jet", [(0.0, "jet_ring", (0, 0.8, 0), {})] + [(0.05 + 0.1 * k, "jet_trail", (0, 0.6, -0.8 * k), {}) for k in range(6)]
         + [(0.9, "dew_burst", (0, 1.4, -5), {})], {}),
    ],
    "golem": [
        ("Titan's Edict", [(0.0, "impact_ring", (0, 0.1, -1.5), {})]
         + [(0.05 + 0.1 * k, e, (0, 0.1 if e == "shock_rupture" else 0.05, -(1.6 + 1.1 * k)), {}) for k in range(7) for e in ("shock_rupture", "shock_glow")], {}),
        ("Runic Bastion", [(0.1, "bastion_flash", (0, 1.6, -1.2), {}), (0.7, "bastion_flash", (0.3, 1.4, -1.2), {})], {}),
        ("Glyph Dominion", [(0.0, "glyph_circle", (0, 0.06, 0), {"radius": 6.2, "life": 8})]
         + [(0.5 + 0.9 * j, "glyph_pillar", p, {}) for j in range(2) for p in ring_pts((0, 0, 0), 6.2, 8, 12 * j)], {"scale": 2.6, "center": (0, 10, 0)}),
        ("Colossus Reassembly", [(0.0, "shard_stream", (0, 1, 0), line((0, 1, 0), (0, 0.2, -9))), (0.0, "rune_burst", (0, 1, 0), {}),
                                 (1.0, "rune_burst", (0, 1, -9), {}), (1.0, "impact_ring", (0, 0.1, -9), {})], {"scale": 3.0, "center": (0, 14, -70)}),
    ],
    "jackalope": [
        ("Lunar Bound", [(0.05 + 0.1 * k, "crescent_trail", (0, 0.5 + math.sin(k / 7 * math.pi) * 1.5, -k), SILVER) for k in range(8)], {"center": (0, 18, -50)}),
        ("Antler Brand", [(0.05 + 0.4 * k, "moon_sigil", (0, 2.2, -3), CRIMSON) for k in range(4)], {}),
        ("Velvet Mirage", [(0.0, "velvet_burst", (0, 1, 0), {})] + [(0.3 + 0.8 * k, "velvet_shimmer", (1.5, 0, -1.5), {}) for k in range(2)], {}),
        ("Crimson Waltz", [(0.05 + 0.25 * k, "crimson_slash", (0, 1.2, -3), {"spin": (k * 97) % 360, "scale": 1.0}) for k in range(4)]
         + [(1.1, "crimson_slash", (0, 1.2, -3), {"spin": 45, "scale": 1.6})], {}),
    ],
    "xenentoma": [
        ("Foretarsal Survey", [(0.1 + 0.5 * j, "vibration_ping", p, {}) for j in range(3) for p in ((2, 0.06, -4), (-3, 0.06, -3), (1, 0.06, -6))], {}),
        ("Exuvia Proxy", [(0.0, "molt_fluid", (0, 1.2, 0), {}), (0.8, "chitin_shards", (0, 1.0, 0), {})], {}),
        ("Interstitial Glide", [(0.1 * k, "step_dust", (0, 0, -0.5 * k), {}) for k in range(6)], {}),
        ("Anamorphic Surge", [(0.2 + 0.3 * k, "surge_strike", (0, 1.1, -3), {}) for k in range(3)], {}),
    ],
    "spaghetti": [
        ("His Noodly Touch", [(0.0, "noodle_strand", (0, 1.2, 0), {"dx": 0, "dy": 0, "dz": -6})], {}),
        ("Al Dente Reversal", [(0.0, "dente_crack", (0, 1, 0), {}), (0.8, "dente_crack", (0, 1.2, -2), {})], {}),
        ("Meatball Ricochet", [(0.0, "sauce_splash", (0, 1, 0), {}), (0.4, "sauce_splash", (2, 1.2, -4), {}), (0.8, "sauce_splash", (-3, 1.2, -3), {})], {}),
        ("Great Pasta Revelation", [(0.4 * k, "pasta_vortex", (0, 0.1, 0), {}) for k in range(4)]
         + [(1.4, "sauce_wave", (0, 0.2, 0), {}), (1.4, "sauce_splash", (0, 1.2, 0), {})], {"scale": 2.8, "center": (0, 12, 0)}),
    ],
    "nurariten": [
        ("Unannounced Arrival", [(0.0, "arrival_gate", (0, 1.2, 0), {}), (0.0, "dissolve_light", (0, 0.6, 0), {}),
                                 (0.05, "arrival_gate", (0, 1.2, -5), {})], {"center": (0, 18, -40)}),
        ("Edict of the Lowered Gaze", [(0.0, "decree_burst", (0, 1.5, -0.9), {})]
         + [(0.15, e, p, {"stacks": 1}) for p in ((2, 1.7, -5), (-2, 1.7, -6)) for e in ("decree_burst", "judgment_seal")], {}),
        ("The Uninvited Temple", [(0.0, "heaven_ring", (0, 0, 0), {}), (1.0, "court_ring", (0, 0.06, 0), {"size": 14})]
         + [(0.9 + 0.4 * j, "court_pillar", p, {}) for j in range(2) for p in ring_pts((0, 0, 0), 7, 8, 7 * j)], {"scale": 2.4, "center": (0, 12, 0)}),
        ("Imperial Expulsion", [(0.0, "arrival_gate", (0, 1.2, -4), {}), (0.0, "decree_burst", (0, 1.2, -4), {})], {"center": (0, 16, -32)}),
    ],
    # ---- Expansion 02 (v1.4)
    "dinosauroid": [
        ("Hindwing Veer", [(0.0, "veer_burst", (0, 0.1, 0), {})] + [(0.15 + 0.09 * k, "veer_trail", (0, 0.6 + 0.2 * math.sin(k / 6 * math.pi), -1.0 * k), {})
                                                                     for k in range(7)], {"center": (0, 16, -40)}),
        ("Crest of Misclassification", [(0.0, "crest_wave", (0, 0.15, 0), {})]
         + [(0.15, "misclass_mark", p, {}) for p in ((2, 2.4, -4), (-3, 2.4, -5))], {"scale": 3.4, "center": (0, 14, -10)}),
        ("Sickle Testament", [(0.2, "sickle_arc", (0, 0.7, -1.4), {"spin": 0}), (0.25, "misclass_mark", (0, 2.4, -2.6), {})], {}),
        ("Taxonomic Error", [(0.0, "overflow_aura", (0, 0.1, 0), {}), (0.9, "dino_display", (0, 1.6, 0), {}),
                             (1.2, "dino_feathers", (0, 1.1, 0), {})], {}),
    ],
    "bathyas": [
        ("Lure of the Impaled Sun", [(0.0, "lure_pulse", (0, 1.2, 0), {})] + [(0.3, "sun_mark", p, {}) for p in ((2, 2.4, -6), (-3, 2.4, -5))],
         {"scale": 2.8, "center": (0, 14, -10)}),
        ("Goblin Maw Rush", [(0.05 * k, "maw_streak", (0, 1.0, -0.9 * k), {"dx": 0, "dy": 0, "dz": -1.2}) for k in range(6)]
         + [(0.35, "maw_bite", (0, 1.2, -6), {})], {"center": (0, 16, -40)}),
        ("Draw the Sun", [(0.0, "daybreak_overload", (0, 1.25, 0), {}), (0.7, "sun_extract", (0, 1.25, 0), {}), (1.2, "sun_slash", (0.4, 1.2, -1.6), {}),
                          (1.5, "sun_return", (0, 1.2, 0), {})], {}),
        ("Abyssal Daybreak", [(0.1 * k, "daybreak_overload", (0, 1.25, 0), {}) for k in range(3)]
         + [(0.35 + 0.05 * k, "abyss_dark", p, {}) for k, p in enumerate(ring_pts((0, 0.2, 0), 5.0, 6))]
         + [(0.6, "sunrise_pillar", (0, 0, 0), {}), (0.9, "leviathan", (-8, 4, -4), {"dx": 1, "dy": 0, "dz": 0}),
            (1.2, "solar_execution", (0, 1.0, 0), {}), (1.4, "daybreak_field", (0, 0.1, 0), {})], {"scale": 2.2, "center": (0, 14, 0)}),
    ],
    "octamyces": [
        ("Parallax Sporeveil", [(0.0, "sporeveil_cloud", (0, 1.0, 0), {})] + [(0.3, "parallax_mark", p, {}) for p in ((2, 2.2, -4), (-3, 2.2, -3))]
         + [(0.6 + 0.3 * k, "parallax_echo", (2 + 0.4 * k, 0.9, -4), {}) for k in range(3)], {"scale": 3.2, "center": (0, 14, -10)}),
        ("The Eye That Records", [(0.0, "observed_mark", (0, 2.7, -6), {})] + [(0.15 + 0.08 * k, "record_point", (math.sin(k / 3) * 2, 0.9, -6 + 0.4 * k), {})
                                                                              for k in range(8)], {"center": (0, 14, -40)}),
        ("Hyphal Offset", [(0.0, "offset_rift", (0, 1.0, 0), {}), (0.05, "offset_rift", (0, 1.0, -5), {}), (0.1, "parallax_echo", (0, 1.0, 0), {}),
                           (1.2, "geo_spores", (0, 1.0, 0), {})], {"center": (0, 16, -36)}),
        ("The Eleventh Frame", [(0.0 + 0.3 * k, "frame_ring", (0, 1.7, -0.6), {}) for k in range(4)]
         + [(0.3 + 0.1 * k, "record_point", p, {}) for k, p in enumerate(FRAME_PATH)]
         + [(0.7, "frame_thread", (0, 1.7, 0), {"dx": p[0], "dy": p[1] + 0.9 - 1.7, "dz": p[2]}) for p in FRAME_PATH]
         + [(1.0 + 0.1 * k, "frame_strike", (p[0], p[1] + 0.7, p[2]), {}) for k, p in enumerate(FRAME_PATH)]
         + [(1.7, "frame_collapse", (0, 1.7, 0), {})], {"scale": 3.0, "center": (0, 14, -30)}),
    ],
    "rite": [
        ("Rite of transformation", [(0.0, "rite_aura", (0, 0.1, 0), {"red": 1.0, "green": 0.78, "blue": 0.3})], {}),
    ],
}


def scenario_frames(race, label, spawns, cam, effects, atlases, model, tex, seconds=1.8, size=(400, 340)):
    t0, e0, o0, v0 = spawns[0]
    extra = [(t, e, o, v) for t, e, o, v in spawns[1:]]
    kw = dict(yaw=32, pitch=20, size=size, scale=4.2, center=(0, 15, -24))
    kw.update(cam)
    return preview.run(effects, atlases, e0, vars_=v0, origin=o0, extra=extra, model=model, texture=tex, seconds=seconds, fps=20,
                       label=label, **kw)


def grid(cols, title):
    n = max(len(c) for c in cols)
    w, h = cols[0][0].size
    out = []
    nc = 2
    nr = (len(cols) + 1) // 2
    for i in range(n):
        im = Image.new("RGB", (w * nc, h * nr + 24), (20, 22, 28))
        ImageDraw.Draw(im).text((8, 6), title, fill=(230, 230, 236))
        for k, c in enumerate(cols):
            im.paste(c[min(i, len(c) - 1)], ((k % nc) * w, 24 + (k // nc) * h))
        out.append(im)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", default="nurariten,spaghetti,xenentoma,salamander,golem,jackalope,dinosauroid,bathyas,octamyces")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "images"))
    ap.add_argument("--seconds", type=float, default=1.8)
    ap.add_argument("--sheets", action="store_true", help="also write a 4-frame contact sheet per race")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    effects, atlases = load_effects()
    for race in args.races.split(","):
        mod = MODS["golem" if race == "rite" else race]
        m = mod.build()
        tex = paint(m, mod.materials(), mod.TEXTURES[TEXKEY["golem" if race == "rite" else race]])
        cols = []
        for label, spawns, cam in SCEN[race]:
            cols.append(scenario_frames(race, label, spawns, cam, effects, atlases, m, tex, seconds=args.seconds))
            print(f"{race}: {label}")
        title = {"rite": "Rite of transformation"}.get(race, f"{race.title()} - ability effects (v1.3, rendered from the pack's particle files)")
        frames = grid(cols, title)
        path = os.path.join(args.out, f"vfx_{race}.gif")
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=50, loop=0, optimize=True)
        if args.sheets:
            preview.sheet_strip(frames, [4, 10, 16, 24], cols=4).save(os.path.join(args.out, f"vfx_{race}_sheet.png"))
        print("  ->", os.path.relpath(path, ROOT), os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main()
