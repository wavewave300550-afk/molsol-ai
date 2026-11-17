"""Minimal little-endian NBT (Bedrock level.dat) reader / writer.

level.dat = 8-byte header (int32 storage version, int32 payload length) + one named root compound.
Values are kept as (tag_type, value) pairs so a file round-trips byte for byte; compounds are lists
of (name, tag_type, value) so the key order is preserved.

    from kit import nbt
    root = nbt.load(open("level.dat", "rb").read())
    nbt.set(root, "LevelName", nbt.STRING, "My world")
    data = nbt.dump(root)
"""
from __future__ import annotations

import struct

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY, LONG_ARRAY = range(13)
_FMT = {BYTE: "<b", SHORT: "<h", INT: "<i", LONG: "<q", FLOAT: "<f", DOUBLE: "<d"}


class _R:
    def __init__(self, b, i=0):
        self.b, self.i = b, i

    def take(self, n):
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def num(self, fmt):
        v = struct.unpack_from(fmt, self.b, self.i)[0]
        self.i += struct.calcsize(fmt)
        return v

    def string(self):
        n = self.num("<H")
        return self.take(n).decode("utf-8")


def _read(r, t):
    if t in _FMT:
        return r.num(_FMT[t])
    if t == BYTE_ARRAY:
        return bytes(r.take(r.num("<i")))
    if t == STRING:
        return r.string()
    if t == LIST:
        et, n = r.num("<b"), r.num("<i")
        return (et, [_read(r, et) for _ in range(n)])
    if t == COMPOUND:
        out = []
        while True:
            ct = r.num("<b")
            if ct == END:
                return out
            name = r.string()
            out.append((name, ct, _read(r, ct)))
    if t == INT_ARRAY:
        return [r.num("<i") for _ in range(r.num("<i"))]
    if t == LONG_ARRAY:
        return [r.num("<q") for _ in range(r.num("<i"))]
    raise ValueError(f"unknown NBT tag type {t}")


def _write(out, t, v):
    if t in _FMT:
        out += struct.pack(_FMT[t], v)
    elif t == BYTE_ARRAY:
        out += struct.pack("<i", len(v)) + bytes(v)
    elif t == STRING:
        b = v.encode("utf-8")
        out += struct.pack("<H", len(b)) + b
    elif t == LIST:
        et, items = v
        out += struct.pack("<bi", et, len(items))
        for x in items:
            _write(out, et, x)
    elif t == COMPOUND:
        for name, ct, cv in v:
            out += struct.pack("<b", ct)
            _write(out, STRING, name)
            _write(out, ct, cv)
        out += b"\x00"
    elif t == INT_ARRAY:
        out += struct.pack("<i", len(v)) + b"".join(struct.pack("<i", x) for x in v)
    elif t == LONG_ARRAY:
        out += struct.pack("<i", len(v)) + b"".join(struct.pack("<q", x) for x in v)
    else:
        raise ValueError(f"unknown NBT tag type {t}")


def load(data: bytes):
    """level.dat bytes -> {'version': int, 'name': str, 'root': compound list}."""
    version = struct.unpack_from("<i", data, 0)[0]
    r = _R(data, 8)
    if r.num("<b") != COMPOUND:
        raise ValueError("level.dat: root is not a compound")
    name = r.string()
    return {"version": version, "name": name, "root": _read(r, COMPOUND)}


def dump(doc) -> bytes:
    body = bytearray()
    body += struct.pack("<b", COMPOUND)
    _write(body, STRING, doc["name"])
    _write(body, COMPOUND, doc["root"])
    return struct.pack("<ii", doc["version"], len(body)) + bytes(body)


def get(compound, name, default=None):
    for n, t, v in compound:
        if n == name:
            return t, v
    return default


def set(compound, name, t, v):  # noqa: A001 - mirrors get()
    for i, (n, _t, _v) in enumerate(compound):
        if n == name:
            compound[i] = (name, t, v)
            return
    compound.append((name, t, v))
