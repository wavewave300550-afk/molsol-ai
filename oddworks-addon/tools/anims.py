"""
Attachable poses/animations and third-person player animations (played with Entity.playAnimation).

Static poses are plain dicts {bone: {position, rotation, scale}} so the preview renderer and the
JSON generator share one source of truth. First-person poses are solved from camera-space
targets with rig.solve_bound_pose (camera = player eye, looking down the barrel of the view).
"""
from __future__ import annotations

from functools import lru_cache

import modelkit as mk
import rig

HIDE = {"scale": 0}


def fp_point(right, up, fwd):
    """Camera-space offset (blocks*16) -> player model coordinates in first person."""
    return (right, rig.EYE + up, fwd)


@lru_cache(maxsize=None)
def _player():
    return rig.player_model()


def solve(slot, pivot, cam, rot):
    pos, r = rig.solve_bound_pose(_player(), rig.FIRST_PERSON, slot, pivot, fp_point(*cam), rot)
    return {"position": pos, "rotation": r}


# =========================================================================== goggles

GOG_PIVOT = (0, 28, -4.9)


@lru_cache(maxsize=None)
def goggles_poses():
    held = solve("main_hand", GOG_PIVOT, (5.4, -4.4, 12.0), rig.rot_world(yaw=-26, pitch=-16, roll=-8))
    raised = solve("main_hand", GOG_PIVOT, (0.0, 0.0, 7.0), rig.rot_world(yaw=180))
    lifted = solve("main_hand", GOG_PIVOT, (2.0, -2.5, 8.0), rig.rot_world(yaw=-8, pitch=-6))
    return {
        # third person (bound to the head)
        "tp_up": {"tp_root": {"position": [0, 2.35, 0.55], "rotation": [-13, 0, 0]},
                  "fp_root": HIDE, "fp_mask": HIDE, "tp_glow": HIDE, "tp_glow_full": HIDE},
        "tp_down": {"tp_root": {"position": [0, 0, 0], "rotation": [0, 0, 0]},
                    "fp_root": HIDE, "fp_mask": HIDE, "tp_glow_full": HIDE},
        # first person
        "fp_held": {"fp_root": held, "tp_root": HIDE, "fp_mask": HIDE, "fp_glow": HIDE, "fp_glow_full": HIDE},
        "fp_lift": {"fp_root": lifted, "tp_root": HIDE, "fp_mask": HIDE, "fp_glow_full": HIDE},
        "fp_raised": {"fp_mask": raised, "fp_root": HIDE, "tp_root": HIDE},
    }


# =========================================================================== handline

REEL_PIVOT = (0, 24, 0)


@lru_cache(maxsize=None)
def handline_poses():
    fp_idle = solve("main_hand", REEL_PIVOT, (6.0, -6.6, 12.5), rig.rot_world(yaw=-35, pitch=-8, roll=14))
    fp_whirl = solve("main_hand", REEL_PIVOT, (7.0, -2.0, 15.0), rig.rot_world(yaw=-10, pitch=-8, roll=10))
    fp_reel = solve("main_hand", REEL_PIVOT, (5.5, -8.0, 12.5), rig.rot_world(yaw=-60, pitch=-55, roll=10))
    return {
        "tp_idle": {"reel": {"rotation": [62, 0, 0]}, "whirl": {"rotation": [0, 0, 0]}},
        "tp_whirl": {"reel": {"rotation": [178, 0, 0], "position": [0, 0, 0]},
                     "sinker_rig": {"rotation": [-82, 0, 0]},
                     "line": {"scale": [1, 3.6, 1]}, "weight": {"position": [0, -8.45, 0]}},
        "tp_reel": {"reel": {"rotation": [40, 0, 0]}},
        "fp_idle": {"reel": fp_idle},
        "fp_whirl": {"reel": fp_whirl, "sinker_rig": {"rotation": [-82, 0, 0]},
                     "line": {"scale": [1, 3.6, 1]}, "weight": {"position": [0, -8.45, 0]}},
        "fp_reel": {"reel": fp_reel},
    }


# =========================================================================== bamboo sword cane

CANE_PIVOT = (0, 24, 0)


@lru_cache(maxsize=None)
def cane_poses():
    # first person: handle in the fist, cane/blade rising up-left like a held sword.
    # rot_axes maps the model's +Y (towards the handle cap) - the blade/sheath run along -Y.
    up_left = rig.rot_axes((-0.42, -0.84, -0.34), (0.15, 0.3, 1.0))
    fp_guard = solve("main_hand", CANE_PIVOT, (6.0, -6.5, 12.0), up_left)
    # draw stance: cane level across the bottom of the view, sheath pointing left, handle right
    fp_grip = solve("main_hand", CANE_PIVOT, (6.0, -5.6, 11.0), rig.rot_axes((-0.95, -0.12, -0.28), (0, 1, 0)))
    fp_cut_mid = solve("main_hand", CANE_PIVOT, (2.0, -3.5, 12.0), rig.rot_axes((0.75, -0.2, -0.62), (0, 1, 0)))
    fp_deflect = solve("main_hand", CANE_PIVOT, (5.0, 0.2, 11.5), rig.rot_axes((-0.97, -0.05, -0.2), (0, 0.4, 1)))
    fp_flick = solve("main_hand", CANE_PIVOT, (7.0, -6.0, 12.0), rig.rot_axes((0.3, 0.75, -0.6), (0, 0, 1)))
    return {
        "tp_cane": {"cane": {"rotation": [16, 0, 0]}},
        "tp_grip": {"cane": {"rotation": [-38, -30, -18]}},
        "tp_drawn": {"cane": {"rotation": [-112, 0, 6]}, "sheath": HIDE,
                     "hip_sheath": {"position": [0, 3, 0], "rotation": [14, 0, 0]}},
        "tp_deflect": {"cane": {"rotation": [-95, 0, 88]}, "sheath": HIDE,
                       "hip_sheath": {"position": [0, 3, 0], "rotation": [14, 0, 0]}},
        "fp_guard": {"cane": fp_guard, "hip_sheath": HIDE},
        "fp_grip": {"cane": fp_grip, "hip_sheath": HIDE},
        "fp_drawn": {"cane": fp_guard, "sheath": HIDE, "hip_sheath": HIDE},
        "fp_cut_mid": {"cane": fp_cut_mid, "sheath": HIDE, "hip_sheath": HIDE},
        "fp_deflect": {"cane": fp_deflect, "sheath": HIDE, "hip_sheath": HIDE},
        "fp_flick": {"cane": fp_flick, "sheath": HIDE, "hip_sheath": HIDE},
    }


# =========================================================================== JSON generation

def _bones_json(pose: dict, fp_gate: bool | None = None) -> dict:
    out = {}
    for bone, ch in pose.items():
        jb = {}
        for k in ("position", "rotation"):
            if k in ch:
                jb[k] = [round(float(v), 3) for v in ch[k]]
        if "scale" in ch:
            s = ch["scale"]
            jb["scale"] = [round(float(v), 3) for v in s] if isinstance(s, (list, tuple)) else round(float(s), 3)
        out[bone] = jb
    return out


def static_anim(pose: dict) -> dict:
    return {"loop": True, "bones": _bones_json(pose)}


def keyframed(frames: list, length: float, loop=False, bones_override=None) -> dict:
    """frames: [(time, pose_dict)] -> animation with per-bone keyframes (linear)."""
    bones: dict = {}
    for t, pose in frames:
        for bone, ch in pose.items():
            for k in ("position", "rotation", "scale"):
                if k in ch:
                    v = ch[k]
                    if isinstance(v, (int, float)):
                        v = [v, v, v]
                    bones.setdefault(bone, {}).setdefault(k, {})[f"{t:.3f}".rstrip("0").rstrip(".") or "0"] = [
                        round(float(x), 3) for x in v]
    if bones_override:
        for b, d in bones_override.items():
            bones.setdefault(b, {}).update(d)
    a = {"loop": loop, "animation_length": length, "bones": bones}
    return a


def fp_gated(expr_tp: str) -> str:
    return f"variable.is_first_person ? 0.0 : ({expr_tp})"


def player_anims() -> dict:
    """Third-person arm/body poses. Additive (vanilla holding pose stays underneath) and
    zeroed in first person so the first-person arm is never disturbed."""
    def arm(frames, length, loop=False, body=None):
        bones = {"rightarm": {"rotation": {}}}
        for t, (rx, ry, rz) in frames:
            bones["rightarm"]["rotation"][f"{t:g}"] = [fp_gated(str(rx)), fp_gated(str(ry)), fp_gated(str(rz))]
        if body:
            bones["body"] = {"rotation": {f"{t:g}": [0, fp_gated(str(y)), 0] for t, y in body}}
        a = {"loop": loop, "bones": bones}
        if not loop:
            a["animation_length"] = length
        return a
    return {
        "animation.oddworks.player.goggles_adjust": arm([(0, (0, 0, 0)), (0.1, (-128, 8, -12)), (0.28, (0, 0, 0))], 0.28),
        "animation.oddworks.player.sun_reach": arm([(0, (-150, -12, -6))], 0, loop=True),
        "animation.oddworks.player.glare": arm([(0, (0, 0, 0)), (0.06, (-110, 0, 6)), (0.4, (0, 0, 0))], 0.4),
        "animation.oddworks.player.cast_throw": arm([(0, (-150, 0, 0)), (0.08, (-40, 0, 0)), (0.3, (0, 0, 0))], 0.3),
        "animation.oddworks.player.snap": arm([(0, (0, 0, 0)), (0.05, (-105, 0, 0)), (0.12, (-20, 0, 0)), (0.3, (0, 0, 0))], 0.3),
        "animation.oddworks.player.cane_grip": arm([(0, (-28, -12, -26))], 0, loop=True, body=[(0, 14)]),
        "animation.oddworks.player.iai_cut": arm([(0, (-28, -12, -26)), (0.1, (-92, 34, 16)), (0.22, (-60, 30, 22)),
                                                  (0.4, (0, 0, 0))], 0.4, body=[(0, 14), (0.1, -22), (0.4, 0)]),
        "animation.oddworks.player.deflect": arm([(0, (0, 0, 0)), (0.05, (-118, 12, -34)), (0.35, (-118, 12, -34)),
                                                  (0.5, (0, 0, 0))], 0.5),
        "animation.oddworks.player.noto": arm([(0, (0, 0, 0)), (0.1, (-62, 0, 26)), (0.18, (-18, 0, 12)),
                                               (0.36, (-28, -12, -26)), (0.55, (0, 0, 0))], 0.55,
                                              body=[(0, 0), (0.36, 12), (0.55, 0)]),
    }
