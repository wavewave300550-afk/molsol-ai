"""
nbt.py - little-endian NBT writer plus Bedrock `.mcstructure` and `level.dat` builders.

Values are tagged explicitly so the on-disk types are exactly what Bedrock expects.
"""
from __future__ import annotations

import struct
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTES, STRING, LIST, COMPOUND, INTS = range(12)


class T:
    """A typed NBT value."""
    __slots__ = ("tag", "v", "elem")

    def __init__(self, tag: int, v, elem: int = END):
        self.tag, self.v, self.elem = tag, v, elem


def byte(v): return T(BYTE, int(v))
def short(v): return T(SHORT, int(v))
def int_(v): return T(INT, int(v))
def long_(v): return T(LONG, int(v))
def float_(v): return T(FLOAT, float(v))
def string(v): return T(STRING, str(v))
def compound(d: dict): return T(COMPOUND, d)
def list_(elem: int, items: Sequence): return T(LIST, list(items), elem)


def auto(v) -> T:
    """Python value -> NBT (bool -> byte, int -> int, str -> string, dict -> compound)."""
    if isinstance(v, T):
        return v
    if isinstance(v, bool):
        return byte(1 if v else 0)
    if isinstance(v, int):
        return int_(v)
    if isinstance(v, float):
        return float_(v)
    if isinstance(v, str):
        return string(v)
    if isinstance(v, dict):
        return compound({k: auto(x) for k, x in v.items()})
    raise TypeError(type(v))


def _payload(t: T) -> bytes:
    if t.tag == BYTE:
        return struct.pack("<b", t.v)
    if t.tag == SHORT:
        return struct.pack("<h", t.v)
    if t.tag == INT:
        return struct.pack("<i", t.v)
    if t.tag == LONG:
        return struct.pack("<q", t.v)
    if t.tag == FLOAT:
        return struct.pack("<f", t.v)
    if t.tag == STRING:
        b = t.v.encode("utf-8")
        return struct.pack("<H", len(b)) + b
    if t.tag == LIST:
        if t.elem == INT:                                   # fast path for big index arrays
            return struct.pack("<bi", INT, len(t.v)) + struct.pack(f"<{len(t.v)}i", *t.v)
        return struct.pack("<bi", t.elem if t.v else END, len(t.v)) + b"".join(_payload(auto(x)) for x in t.v)
    if t.tag == COMPOUND:
        out = []
        for k, x in t.v.items():
            x = auto(x)
            kb = k.encode("utf-8")
            out.append(struct.pack("<bH", x.tag, len(kb)) + kb + _payload(x))
        return b"".join(out) + b"\x00"
    raise ValueError(t.tag)


def dumps(root: T, name: str = "") -> bytes:
    nb = name.encode("utf-8")
    return struct.pack("<bH", root.tag, len(nb)) + nb + _payload(root)


# --------------------------------------------------------------------------- mcstructure

BLOCK_VERSION = 18161159      # block-state version stamped by Minecraft Creator Tools 0.21 (1.21.30.7)


class Structure:
    """A block volume. Unset cells are structure void (the world keeps its block);
    cells set to air carve space."""

    def __init__(self, sx: int, sy: int, sz: int):
        self.size = (sx, sy, sz)
        self.cells: List[int] = [-1] * (sx * sy * sz)
        self.palette: List[Tuple[str, Tuple]] = []
        self._index: Dict[Tuple[str, Tuple], int] = {}

    def _pid(self, name: str, states: Optional[dict]) -> int:
        if ":" not in name:
            name = "minecraft:" + name
        key = (name, tuple(sorted((states or {}).items())))
        i = self._index.get(key)
        if i is None:
            i = self._index[key] = len(self.palette)
            self.palette.append(key)
        return i

    def inside(self, x: int, y: int, z: int) -> bool:
        return 0 <= x < self.size[0] and 0 <= y < self.size[1] and 0 <= z < self.size[2]

    def set(self, x: int, y: int, z: int, name: str, states: Optional[dict] = None) -> None:
        x, y, z = int(x), int(y), int(z)
        if self.inside(x, y, z):
            # Bedrock structure index order: X outermost, then Y, then Z
            self.cells[(x * self.size[1] + y) * self.size[2] + z] = self._pid(name, states)

    def get(self, x: int, y: int, z: int) -> Optional[str]:
        if not self.inside(x, y, z):
            return None
        i = self.cells[(x * self.size[1] + y) * self.size[2] + z]
        return None if i < 0 else self.palette[i][0]

    def fill(self, x0, y0, z0, x1, y1, z1, name: str, states: Optional[dict] = None) -> None:
        for x in range(int(min(x0, x1)), int(max(x0, x1)) + 1):
            for y in range(int(min(y0, y1)), int(max(y0, y1)) + 1):
                for z in range(int(min(z0, z1)), int(max(z0, z1)) + 1):
                    self.set(x, y, z, name, states)

    def blocks(self) -> Iterable[Tuple[int, int, int, str, dict]]:
        sx, sy, sz = self.size
        for x in range(sx):
            for y in range(sy):
                for z in range(sz):
                    i = self.cells[(x * sy + y) * sz + z]
                    if i >= 0:
                        yield x, y, z, self.palette[i][0], dict(self.palette[i][1])

    def count(self) -> int:
        return sum(1 for c in self.cells if c >= 0)

    def to_bytes(self) -> bytes:
        pal = [compound({"name": string(n), "states": compound({k: auto(v) for k, v in st}),
                         "version": int_(BLOCK_VERSION)}) for n, st in self.palette]
        root = compound({
            "format_version": int_(1),
            "size": list_(INT, list(self.size)),
            "structure": compound({
                "block_indices": list_(LIST, [list_(INT, self.cells), list_(INT, [-1] * len(self.cells))]),
                "entities": list_(COMPOUND, []),
                "palette": compound({"default": compound({
                    "block_palette": list_(COMPOUND, pal),
                    "block_position_data": compound({}),
                })}),
            }),
            "structure_world_origin": list_(INT, [0, 0, 0]),
        })
        return dumps(root)


def level_dat(root: T, storage_version: int = 10) -> bytes:
    """Bedrock level.dat = 8-byte header (storage version, payload length) + little-endian NBT."""
    body = dumps(root)
    return struct.pack("<ii", storage_version, len(body)) + body
