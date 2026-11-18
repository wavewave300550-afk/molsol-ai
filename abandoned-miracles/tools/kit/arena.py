"""
arena.py - helpers for authoring demonstration arenas as `.mcstructure` files.

Arenas are OPTIONAL scenery. The bosses never need them: an encounter only uses
a logical circle/square on whatever floor it was summoned on. These structures
are placed solely by an explicit, confirmed player action (or pre-placed in the
separate test world).

Only blocks whose identifiers and states have been stable since the structure
block-state version stamped in nbt.BLOCK_VERSION are used, so the game's own
upgrade path fills in any state added later.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, Iterable, Optional, Tuple

from .nbt import Structure

B = Tuple[str, Optional[dict]]


def blk(name: str, **states) -> B:
    return (name, states or None)


def pillar(name: str, axis: str = "y") -> B:
    return (name, {"pillar_axis": axis})


def bone(axis: str = "y") -> B:
    return ("bone_block", {"deprecated": 0, "pillar_axis": axis})


def stairs(name: str, facing: str = "east", upside_down: bool = False) -> B:
    """facing = the direction the full-height back of the stair points to."""
    return (name, {"weirdo_direction": {"east": 0, "west": 1, "south": 2, "north": 3}[facing],
                   "upside_down_bit": bool(upside_down)})


def slab(name: str, top: bool = False) -> B:
    return (name, {"minecraft:vertical_half": "top" if top else "bottom"})


def lantern(name: str = "soul_lantern", hanging: bool = False) -> B:
    return (name, {"hanging": bool(hanging)})


def candle(name: str = "white_candle", count: int = 3, lit: bool = True) -> B:
    return (name, {"candles": max(0, min(3, count - 1)), "lit": bool(lit)})


def froglight(kind: str = "pearlescent") -> B:
    return (f"{kind}_froglight", {"pillar_axis": "y"})


AIR: B = ("air", None)


class Arena(Structure):
    """A structure with a centre and drawing helpers. The walking surface is the top of layer `floor`."""

    def __init__(self, size: int, height: int, floor: int = 0, seed: int = 1):
        super().__init__(size, height, size)
        self.c = size // 2
        self.floor = floor
        self.rng = random.Random(seed)

    def put(self, x, y, z, b: B) -> None:
        self.set(int(round(x)), int(y), int(round(z)), b[0], b[1])

    def box(self, x0, y0, z0, x1, y1, z1, b: B) -> None:
        self.fill(x0, y0, z0, x1, y1, z1, b[0], b[1])

    def annulus(self, r0: float, r1: float) -> Iterable[Tuple[int, int, float, float]]:
        """Grid cells whose centre lies in the annulus [r0, r1): (x, z, radius, theta degrees)."""
        n = int(math.ceil(r1)) + 1
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                r = math.hypot(dx, dz)
                if r0 <= r < r1:
                    yield self.c + dx, self.c + dz, r, math.degrees(math.atan2(dz, dx)) % 360

    def disc(self, r0: float, r1: float, y: int, pick: Callable[[float, float], Optional[B]]) -> None:
        """Fill an annulus on layer y; `pick(radius, theta)` chooses the block (None = leave)."""
        for x, z, r, th in self.annulus(r0, r1):
            b = pick(r, th)
            if b:
                self.put(x, y, z, b)

    def square(self, half: int, y: int, pick: Callable[[int, int], Optional[B]]) -> None:
        """Fill a centred square on layer y; `pick(dx, dz)` chooses the block."""
        for dx in range(-half, half + 1):
            for dz in range(-half, half + 1):
                b = pick(dx, dz)
                if b:
                    self.put(self.c + dx, y, self.c + dz, b)

    def polar(self, r: float, theta: float) -> Tuple[int, int]:
        a = math.radians(theta)
        return int(round(self.c + r * math.cos(a))), int(round(self.c + r * math.sin(a)))

    def column(self, x: int, z: int, y0: int, h: int, b: B, cap: Optional[B] = None, base: Optional[B] = None,
               wide: int = 1) -> None:
        for dx in range(wide):
            for dz in range(wide):
                for i in range(h):
                    self.put(x + dx, y0 + i, z + dz, base if (i == 0 and base) else cap if (i == h - 1 and cap) else b)

    def clear_above_floor(self, radius: float, height: int) -> None:
        """Carve the playable volume: air above the floor inside `radius`."""
        for x, z, _, _ in self.annulus(0, radius):
            for y in range(self.floor + 1, min(self.size[1], self.floor + 1 + height)):
                self.put(x, y, z, AIR)

    def validate(self) -> list:
        from . import vanilla
        errs = []
        for name, st in self.palette:
            msg = vanilla.check_block(name, dict(st))
            if msg:
                errs.append(msg)
        return errs
