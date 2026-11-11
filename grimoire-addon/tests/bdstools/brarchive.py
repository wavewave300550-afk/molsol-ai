"""Extract Mojang .brarchive files (BDS vanilla packs) into plain folders."""
import struct, sys, os, pathlib

def read_archive(path):
    d = open(path, 'rb').read()
    magic, count, ver = struct.unpack_from('<QII', d, 0)
    entries = []
    off = 16
    for _ in range(count):
        n = d[off]
        name = d[off+1:off+1+n].decode('utf-8')
        doff, dlen = struct.unpack_from('<II', d, off + 248)
        entries.append((name, doff, dlen))
        off += 256
    base = off
    return [(name, d[base+doff: base+doff+dlen]) for name, doff, dlen in entries]

def extract_tree(src_dir, out_dir):
    src = pathlib.Path(src_dir)
    for arc in src.rglob('*.brarchive'):
        rel = arc.relative_to(src).with_suffix('')  # e.g. entities
        for name, blob in read_archive(arc):
            target = pathlib.Path(out_dir) / rel / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)

if __name__ == '__main__':
    extract_tree(sys.argv[1], sys.argv[2])
