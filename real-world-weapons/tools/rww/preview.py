"""
Animation preview + verification harness.

Evaluates the generated runtime player animations (frame by frame, through the
Molang evaluator, on top of the emulated vanilla stack), attaches the sword via
the attachable's binding rules, renders first/third-person frames and measures
hand placement errors (left hand vs. grip axis for two-handed weapons).
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from . import anims, bedrock, molang, player, render, swords

SKIN = None


def skin():
    global SKIN
    if SKIN is None:
        SKIN = render.texture_array(player.mannequin_skin())
    return SKIN


@lru_cache(maxsize=None)
def weapon_assets(weapon: str):
    wa = anims.solve_weapon(weapon)
    arms = anims.arms_animation(wa)
    body = anims.body_animation(wa)
    m = swords.BUILDERS[weapon]()
    m.layout()
    gj = m.geometry_json()
    geo = bedrock.load_geometries(gj)[m.identifier]
    att = anims.attachable_animations(weapon)
    return wa, arms, body, m, geo, att


@lru_cache(maxsize=None)
def texture(weapon: str, tier: str):
    _, _, _, m, _, _ = weapon_assets(weapon)
    return render.texture_array(m.paint(swords.painters(weapon, tier)))


def simulate(weapon: str, state: dict, frames: int = 40, dt: float = 1 / 30, variables: Optional[dict] = None,
             attack: Optional[Tuple[int, float]] = None, equip_progress: Optional[float] = None):
    """Run the runtime animations for `frames` frames with a constant state and return the final
    (pose, ctx).  attack=(variant, attack_time) freezes an attack at that progress."""
    wa, arms, body, m, geo, att = weapon_assets(weapon)
    v = dict(variables or {})
    life = 10.0
    st = dict(state)
    tags = ("rww:weapon", f"rww:{weapon}")
    st.setdefault("mainhand_tags", tags)
    for i in range(frames):
        life += dt
        st["life_time"] = life
        st["delta_time"] = dt
        st["distance"] = state.get("distance", 0.0)
        if attack is not None:
            variant, at = attack
            st["attack_time"] = at
            v["rww_combo"] = float(variant)
            v["rww_pat"] = at
            v["rww_lat"] = life - 0.05
        else:
            st["attack_time"] = 0.0
        if equip_progress is not None:
            v[f"rww_hb_{weapon}"] = life - dt
            v[f"rww_eq0_{weapon}"] = life - equip_progress * anims.EQUIP_TIME[weapon]
        else:
            v.setdefault(f"rww_hb_{weapon}", life - dt)
            v[f"rww_hb_{weapon}"] = life - dt
            v.setdefault(f"rww_eq0_{weapon}", life - 100)
        pose, ctx = player.compose(st, runtime_anims=[(arms, life), (body, life)], variables=v)
        v = ctx.variables
    return pose, ctx


def attach(weapon: str, ctx: molang.Context, pmats, first_person: bool):
    wa, arms, body, m, geo, att = weapon_assets(weapon)
    actx = molang.Context(context={"is_first_person": 1.0 if first_person else 0.0, "owning_entity": ctx,
                                   "item_slot": "main_hand"})
    ap = bedrock.rest_pose(geo)
    key = f"animation.rww.{weapon}.hold_{'fp' if first_person else 'tp'}"
    bedrock.apply_animation(att[key], ap, bedrock.rest_pose(geo), actx, 0.0)
    return bedrock.world_matrices(geo, ap, holder=(player.PLAYER_GEO, pmats))


def grip_error(weapon: str, pmats, amats) -> Optional[Tuple[float, float]]:
    """For two-handed weapons: (distance of the left hand from the grip axis, position along the grip
    in model units from the pommel end).  Uses the left arm's item point."""
    if weapon == "rapier":
        return None
    wa, arms, body, m, geo, att = weapon_assets(weapon)
    root = geo.order[0]
    A = amats[root]
    lo = {"katana": 19.4, "zweihander": 18.4}[weapon]
    hi = {"katana": 26.6, "zweihander": 27.0}[weapon]
    p0 = (A @ np.array([0, lo, 0, 1.0]))[:3]
    p1 = (A @ np.array([0, hi, 0, 1.0]))[:3]
    lb = player.PLAYER_GEO.bones["leftitem"]
    hand = (pmats["leftarm"] @ np.r_[bedrock.disp(lb.pivot), 1.0])[:3]
    d = p1 - p0
    t = float(np.clip(np.dot(hand - p0, d) / np.dot(d, d), 0, 1))
    closest = p0 + d * t
    return float(np.linalg.norm(hand - closest)), lo + (hi - lo) * t


def frame(weapon: str, tier: str, state: dict, first_person=False, attack=None, equip=None, camera=None,
          size=(360, 360), bg=(36, 40, 48, 255)):
    pose, ctx = simulate(weapon, dict(state, first_person=first_person), attack=attack, equip_progress=equip)
    pm = player.player_matrices(pose)
    am = attach(weapon, ctx, pm, first_person)
    wa, arms, body, m, geo, att = weapon_assets(weapon)
    vis = (lambda b: False) if first_person else None
    inst = [render.Instance(player.PLAYER_GEO, skin(), pm, vis), render.Instance(geo, texture(weapon, tier), am)]
    if camera is None:
        camera = (render.Camera(eye=(0, 27.41, 0), target=(0, 27.41, 10), fov=70.25) if first_person else
                  render.Camera(eye=(-46, 30, -52), target=(0, 19, -4), fov=44))
    img = render.render(inst, camera, size=size, bg=bg, light=DOC_LIGHT, ambient=0.5)
    return img, grip_error(weapon, pm, am)


def font(size=13):
    """DejaVu Sans when available (umlauts, dashes), else Pillow's built-in font."""
    from PIL import ImageFont
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial Unicode.ttf",
                 "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# camera-side key light for documentation renders
DOC_LIGHT = (-0.45, 0.85, -0.55)


def sheet(tiles: List[Tuple[str, Image.Image]], cols: int) -> Image.Image:
    w, h = tiles[0][1].size
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGBA", (w * cols, (h + 20) * rows), (24, 26, 32, 255))
    d = ImageDraw.Draw(out)
    f = font(13)
    for i, (label, img) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + 20)
        out.paste(img, (x, y + 20))
        d.text((x + 6, y + 3), label, fill=(220, 224, 230, 255), font=f)
    return out
