"""Minimal Bedrock (little-endian) NBT reader/writer for level.dat editing."""
import struct, io

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = range(13)

class Tag:
    def __init__(self, t, v): self.t, self.v = t, v
    def __repr__(self): return f"Tag({self.t},{self.v!r})"

def _rs(f):
    n, = struct.unpack('<H', f.read(2)); return f.read(n).decode('utf-8')

def _read_payload(f, t):
    if t == TAG_BYTE: return struct.unpack('<b', f.read(1))[0]
    if t == TAG_SHORT: return struct.unpack('<h', f.read(2))[0]
    if t == TAG_INT: return struct.unpack('<i', f.read(4))[0]
    if t == TAG_LONG: return struct.unpack('<q', f.read(8))[0]
    if t == TAG_FLOAT: return struct.unpack('<f', f.read(4))[0]
    if t == TAG_DOUBLE: return struct.unpack('<d', f.read(8))[0]
    if t == TAG_BYTE_ARRAY:
        n, = struct.unpack('<i', f.read(4)); return f.read(n)
    if t == TAG_STRING: return _rs(f)
    if t == TAG_LIST:
        et, = struct.unpack('<b', f.read(1)); n, = struct.unpack('<i', f.read(4))
        return (et, [_read_payload(f, et) for _ in range(n)])
    if t == TAG_COMPOUND:
        d = {}
        while True:
            ct, = struct.unpack('<b', f.read(1))
            if ct == TAG_END: return d
            name = _rs(f); d[name] = Tag(ct, _read_payload(f, ct))
    if t == TAG_INT_ARRAY:
        n, = struct.unpack('<i', f.read(4)); return list(struct.unpack(f'<{n}i', f.read(4*n)))
    if t == TAG_LONG_ARRAY:
        n, = struct.unpack('<i', f.read(4)); return list(struct.unpack(f'<{n}q', f.read(8*n)))
    raise ValueError(t)

def _ws(f, s):
    b = s.encode('utf-8'); f.write(struct.pack('<H', len(b))); f.write(b)

def _write_payload(f, t, v):
    if t == TAG_BYTE: f.write(struct.pack('<b', v))
    elif t == TAG_SHORT: f.write(struct.pack('<h', v))
    elif t == TAG_INT: f.write(struct.pack('<i', v))
    elif t == TAG_LONG: f.write(struct.pack('<q', v))
    elif t == TAG_FLOAT: f.write(struct.pack('<f', v))
    elif t == TAG_DOUBLE: f.write(struct.pack('<d', v))
    elif t == TAG_BYTE_ARRAY: f.write(struct.pack('<i', len(v))); f.write(v)
    elif t == TAG_STRING: _ws(f, v)
    elif t == TAG_LIST:
        et, items = v; f.write(struct.pack('<b', et)); f.write(struct.pack('<i', len(items)))
        for it in items: _write_payload(f, et, it)
    elif t == TAG_COMPOUND:
        for name, tag in v.items():
            f.write(struct.pack('<b', tag.t)); _ws(f, name); _write_payload(f, tag.t, tag.v)
        f.write(struct.pack('<b', TAG_END))
    elif t == TAG_INT_ARRAY: f.write(struct.pack('<i', len(v))); f.write(struct.pack(f'<{len(v)}i', *v))
    elif t == TAG_LONG_ARRAY: f.write(struct.pack('<i', len(v))); f.write(struct.pack(f'<{len(v)}q', *v))

def read_level_dat(path):
    data = open(path, 'rb').read()
    ver, ln = struct.unpack_from('<ii', data, 0)
    f = io.BytesIO(data[8:8+ln])
    t, = struct.unpack('<b', f.read(1)); name = _rs(f)
    return ver, name, _read_payload(f, t)

def write_level_dat(path, ver, name, root):
    f = io.BytesIO(); f.write(struct.pack('<b', TAG_COMPOUND)); _ws(f, name); _write_payload(f, TAG_COMPOUND, root)
    body = f.getvalue()
    open(path, 'wb').write(struct.pack('<ii', ver, len(body)) + body)
