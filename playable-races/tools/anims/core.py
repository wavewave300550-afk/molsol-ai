"""Tiny helpers for writing Bedrock animation JSON with Molang."""
from __future__ import annotations

from typing import Dict, Optional

NS = "plrace"

# Vanilla walk swing (animation.player.move.legs / move.arms) recomputed so race
# limbs can cancel or reshape the human stride.
VSWING = "(math.cos(q.modified_distance_moved * 38.17) * q.modified_move_speed * 57.3)"
WALK = "math.clamp(q.modified_move_speed, 0, 1)"
PHASE = "(q.modified_distance_moved * 38.17)"
T = "q.life_time"


def n(x: float) -> str:
    """Format a number for Molang."""
    return f"{x:.4g}"


def osc(freq: float, amp: float, phase: float = 0.0, t: str = T) -> str:
    """amp * sin(t * freq*360 + phase)  (freq in Hz, angles in degrees)."""
    return f"math.sin({t} * {n(freq * 360)} + {n(phase)}) * {n(amp)}"


class Anim:
    def __init__(self, name: str, loop=True, length: Optional[float] = None, override=False):
        self.name = name
        self.loop = loop
        self.length = length
        self.override = override
        self.bones: Dict[str, dict] = {}
        self.particles: Dict[str, list] = {}
        self.sounds: Dict[str, list] = {}

    def bone(self, bone: str, rot=None, pos=None, scale=None):
        b = self.bones.setdefault(bone, {})
        if rot is not None:
            b["rotation"] = _chan(rot)
        if pos is not None:
            b["position"] = _chan(pos)
        if scale is not None:
            b["scale"] = _chan(scale)
        return self

    def particle(self, time: float, effect: str, locator: Optional[str] = None, script: Optional[str] = None):
        e = {"effect": effect}
        if locator:
            e["locator"] = locator
        if script:
            e["pre_effect_script"] = script
        self.particles.setdefault(f"{time:.2f}", []).append(e)
        return self

    def json(self) -> dict:
        out: dict = {}
        if self.loop is True:
            out["loop"] = True
        elif self.loop == "hold":
            out["loop"] = "hold_on_last_frame"
        if self.length is not None:
            out["animation_length"] = self.length
        if self.override:
            out["override_previous_animation"] = True
        if self.bones:
            out["bones"] = self.bones
        if self.particles:
            out["particle_effects"] = {k: (v[0] if len(v) == 1 else v) for k, v in self.particles.items()}
        return out


def _chan(v):
    """Accept a vector/expr list, a scalar, or a {time: vector} keyframe dict."""
    if isinstance(v, dict):
        return {f"{float(k):.4g}" if not isinstance(k, str) else k: _vec(x) for k, x in sorted(v.items(), key=lambda kv: float(kv[0]))}
    return _vec(v)


def _vec(v):
    if isinstance(v, (int, float, str)):
        return v if isinstance(v, str) else round(float(v), 4)
    if isinstance(v, dict):  # explicit keyframe object (lerp_mode etc.)
        return v
    return [x if isinstance(x, str) else round(float(x), 4) for x in v]


def file(anims) -> dict:
    return {"format_version": "1.10.0", "animations": {a.name: a.json() for a in anims}}


def controller_file(ctrls: dict) -> dict:
    return {"format_version": "1.10.0", "animation_controllers": ctrls}
