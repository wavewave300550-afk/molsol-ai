"""Minimal Bedrock (little-endian) NBT reader/writer for level.dat (tools/test_world.py)."""
import struct

TAGS = {1: "byte", 2: "short", 3: "int", 4: "long", 5: "float", 6: "double", 7: "byte_array", 8: "string", 9: "list", 10: "compound", 11: "int_array", 12: "long_array"}


class Reader:
    def __init__(self, b):
        self.b, self.i = b, 0

    def take(self, n):
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def u8(self): return struct.unpack("<b", self.take(1))[0]
    def i16(self): return struct.unpack("<h", self.take(2))[0]
    def i32(self): return struct.unpack("<i", self.take(4))[0]
    def i64(self): return struct.unpack("<q", self.take(8))[0]
    def f32(self): return struct.unpack("<f", self.take(4))[0]
    def f64(self): return struct.unpack("<d", self.take(8))[0]
    def s(self):
        n = struct.unpack("<H", self.take(2))[0]
        return self.take(n).decode("utf-8")

    def payload(self, t):
        if t == 1: return self.u8()
        if t == 2: return self.i16()
        if t == 3: return self.i32()
        if t == 4: return self.i64()
        if t == 5: return self.f32()
        if t == 6: return self.f64()
        if t == 7: return list(self.take(self.i32()))
        if t == 8: return self.s()
        if t == 9:
            et = self.u8(); n = self.i32()
            return ("list", et, [self.payload(et) for _ in range(n)])
        if t == 10:
            out = {}
            while True:
                tt = self.u8()
                if tt == 0: return ("compound", out)
                name = self.s()
                out[name] = (tt, self.payload(tt))
        if t == 11: return [self.i32() for _ in range(self.i32())]
        if t == 12: return [self.i64() for _ in range(self.i32())]
        raise ValueError(t)


def read_level(path):
    b = open(path, "rb").read()
    ver, ln = struct.unpack("<ii", b[:8])
    r = Reader(b[8:])
    t = r.u8(); name = r.s()
    return ver, name, r.payload(t)


class Writer:
    def __init__(self): self.o = bytearray()
    def w(self, fmt, v): self.o += struct.pack(fmt, v)
    def s(self, v):
        e = v.encode("utf-8"); self.w("<H", len(e)); self.o += e
    def payload(self, t, v):
        if t == 1: self.w("<b", v)
        elif t == 2: self.w("<h", v)
        elif t == 3: self.w("<i", v)
        elif t == 4: self.w("<q", v)
        elif t == 5: self.w("<f", v)
        elif t == 6: self.w("<d", v)
        elif t == 7: self.w("<i", len(v)); self.o += bytes(x & 0xff for x in v)
        elif t == 8: self.s(v)
        elif t == 9:
            _, et, items = v; self.w("<b", et); self.w("<i", len(items))
            for x in items: self.payload(et, x)
        elif t == 10:
            _, d = v
            for name, (tt, pv) in d.items():
                self.w("<b", tt); self.s(name); self.payload(tt, pv)
            self.w("<b", 0)
        elif t == 11: self.w("<i", len(v)); [self.w("<i", x) for x in v]
        elif t == 12: self.w("<i", len(v)); [self.w("<q", x) for x in v]


def write_level(path, ver, name, root):
    w = Writer(); w.w("<b", 10); w.s(name); w.payload(10, root)
    body = bytes(w.o)
    open(path, "wb").write(struct.pack("<ii", ver, len(body)) + body)


def plain(v):
    if isinstance(v, tuple) and v and v[0] == "compound":
        return {k: plain(pv) for k, (tt, pv) in v[1].items()}
    if isinstance(v, tuple) and v and v[0] == "list":
        return [plain(x) for x in v[2]]
    return v
