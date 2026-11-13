"""Procedural Bedrock geometry kit.

Authoring space ("bb space") is right-handed like Blockbench / the world:
  +X = east, +Y = up, +Z = south.  A model's FRONT faces -Z (north).
  Units are 1/16 block.  Rotations are degrees, right-handed, applied X then Y then Z.
Export applies the same conversion Blockbench's Bedrock codec uses
(flip X of origins/pivots, negate X/Y rotations, flip up/down face UVs).

Textures: every cube face asks its material for a tile; identical requests are
shared, tiles are packed into one atlas per model, faces get per-face UVs.
Tile pixel layout (row 0 = top, col 0 = left, as seen from OUTSIDE the face):
  north: u -> -X, v -> -Y     south: u -> +X, v -> -Y
  east : u -> -Z, v -> -Y     west : u -> +Z, v -> -Y
  up   : u -> +X, v -> +Z     down : u -> +X, v -> -Z
Tiles are float arrays (h, w, 5): r, g, b, alpha(0..1 cutout/opacity), glow(0..1).
"""
from __future__ import annotations

import json
import math
import os
import zlib

import numpy as np
from PIL import Image

FACES = ("north", "south", "east", "west", "up", "down")
GROUP = {"north": "side", "south": "side", "east": "side", "west": "side", "up": "up", "down": "down"}
NORMALS = {
    "north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0),
    "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0),
}


def _seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode()) & 0x7FFFFFFF


class Mat:
    """A material: a painter callback plus sharing/blend metadata.

    fn(ctx) -> float array (h, w, 5).  mode: 'solid' (cutout + glow, rendered with
    entity_emissive_alpha) or 'blend' (alpha = opacity, rendered with entity_alphablend).
    spatial=True means the painter reads ctx.X/Y/Z so tiles are never shared.
    directional=True keys tiles by exact face instead of side/up/down group.
    """

    _n = 0

    def __init__(self, fn, key=None, *, mode="solid", spatial=False, directional=False, density=None):
        Mat._n += 1
        self.fn = fn
        self.key = key if key is not None else f"mat{Mat._n}"
        self.mode = mode
        self.spatial = spatial
        self.directional = directional
        self.density = density

    def but(self, **kw):
        m = Mat(self.fn, kw.pop("key", self.key + "+" + repr(sorted(kw.items()))), mode=self.mode,
                spatial=self.spatial, directional=self.directional, density=self.density)
        for k, v in kw.items():
            setattr(m, k, v)
        return m


class FaceCtx:
    __slots__ = ("w", "h", "face", "group", "X", "Y", "Z", "size", "rng", "variant", "U", "V", "alt")


class Cube:
    def __init__(self, bone, origin, size, mat, rot=None, pivot=None, inflate=0.0, density=None,
                 faces=None, variant=0, mats=None, tint=None):
        self.bone = bone
        self.origin = tuple(float(v) for v in origin)
        self.size = tuple(float(v) for v in size)
        self.mat = mat
        self.rot = tuple(rot) if rot else None
        self.pivot = tuple(pivot) if pivot else None
        self.inflate = float(inflate)
        self.density = density
        self.variant = variant
        self.mats = mats or {}
        if faces is None:
            sx, sy, sz = self.size
            if sx == 0:
                faces = ("east", "west")
            elif sy == 0:
                faces = ("up", "down")
            elif sz == 0:
                faces = ("north", "south")
            else:
                faces = FACES
        self.faces = tuple(faces)
        self.uv = {}  # face -> (u, v, w, h) in atlas pixels
        sx, sy, sz = self.size
        self.plane = "x" if sx == 0 else "y" if sy == 0 else "z" if sz == 0 else None

    FRONT = {"x": "east", "y": "up", "z": "north"}
    BACK = {"x": "west", "y": "down", "z": "south"}

    def paint_faces(self):
        """Faces that get their own quad.  A zero-thickness plane is ONE sheet: when both of its
        sides are requested only the front (north / east / up) is painted, and the sheet is seen
        mirrored from behind.  This avoids two coincident, differently-mapped faces fighting each
        other under the double-sided entity materials."""
        if self.plane and self.FRONT[self.plane] in self.faces and self.BACK[self.plane] in self.faces:
            return tuple(f for f in self.faces if f != self.BACK[self.plane])
        return self.faces

    def face_dims(self, face):
        sx, sy, sz = self.size
        if face in ("north", "south"):
            return sx, sy
        if face in ("east", "west"):
            return sz, sy
        return sx, sz

    def corners(self, face):
        """TL, TR, BR, BL of a face in bone-local bb coordinates (inflated)."""
        i = self.inflate
        x0, y0, z0 = (self.origin[0] - i, self.origin[1] - i, self.origin[2] - i)
        x1, y1, z1 = (x0 + self.size[0] + 2 * i, y0 + self.size[1] + 2 * i, z0 + self.size[2] + 2 * i)
        if face == "north":
            return (x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)
        if face == "south":
            return (x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)
        if face == "east":
            return (x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)
        if face == "west":
            return (x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)
        if face == "up":
            return (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)
        return (x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)


class Bone:
    def __init__(self, model, name, parent=None, pivot=(0, 0, 0), rot=(0, 0, 0)):
        self.model = model
        self.name = name
        self.parent = parent
        self.pivot = tuple(float(v) for v in pivot)
        self.rot = tuple(float(v) for v in rot)
        self.cubes = []
        self.locators = {}
        self.binding = None

    def cube(self, origin, size, mat, **kw):
        c = Cube(self, origin, size, mat, **kw)
        self.cubes.append(c)
        return c

    def box(self, center, size, mat, **kw):
        """Cube given by its center."""
        o = tuple(center[i] - size[i] / 2 for i in range(3))
        return self.cube(o, size, mat, **kw)

    def plane(self, axis, center, w, h, mat, **kw):
        """Zero-thickness quad. axis = normal axis 'x'|'y'|'z'; (w, h) in-plane size."""
        cx, cy, cz = center
        if axis == "z":
            return self.cube((cx - w / 2, cy - h / 2, cz), (w, h, 0), mat, **kw)
        if axis == "x":
            return self.cube((cx, cy - h / 2, cz - w / 2), (0, h, w), mat, **kw)
        return self.cube((cx - w / 2, cy, cz - h / 2), (w, 0, h), mat, **kw)

    def locator(self, name, pos):
        self.locators[name] = tuple(float(v) for v in pos)
        return self


def rot_matrix(rx, ry, rz):
    """Right-handed rotation, X applied first, then Y, then Z (degrees)."""
    ax, ay, az = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def _trs(pivot, rot, pos=(0, 0, 0), scale=(1, 1, 1)):
    m = np.eye(4)
    r = rot_matrix(*rot) @ np.diag(scale)
    p = np.array(pivot, dtype=float)
    m[:3, :3] = r
    m[:3, 3] = p + np.array(pos, dtype=float) - r @ p
    return m


class Model:
    def __init__(self, name, density=1.0, pad=1, bounds=None, alts=()):
        """alts: names of alternate texture skins.  Every tile is painted once per skin with
        ctx.alt set (None for the default), all skins share one UV layout."""
        self.name = name
        self.alts = tuple(alts)
        self.atlases = {}
        self.density = density
        self.pad = pad
        self.bones = {}
        self.order = []
        self.atlas = None
        self.tex_size = (16, 16)
        self.bounds = bounds  # (width_blocks, height_blocks, (ox, oy, oz) blocks) or None = auto
        self._final = False

    # ---- authoring -------------------------------------------------------
    def bone(self, name, parent=None, pivot=(0, 0, 0), rot=(0, 0, 0)) -> Bone:
        if name in self.bones:
            raise ValueError(f"{self.name}: duplicate bone {name}")
        if isinstance(parent, Bone):
            parent = parent.name
        if parent is not None and parent not in self.bones:
            raise ValueError(f"{self.name}: unknown parent {parent} for {name}")
        b = Bone(self, name, parent, pivot, rot)
        self.bones[name] = b
        self.order.append(name)
        return b

    def __getitem__(self, name) -> Bone:
        return self.bones[name]

    @property
    def blend_bones(self):
        out = []
        for n in self.order:
            modes = {(c.mats.get(f) or c.mat).mode for c in self.bones[n].cubes for f in c.faces}
            if len(modes) > 1:
                raise ValueError(f"{self.name}: bone {n} mixes solid and blend materials")
            if modes == {"blend"}:
                out.append(n)
        return out

    def cube_count(self):
        return sum(len(self.bones[n].cubes) for n in self.order)

    # ---- texturing -------------------------------------------------------
    def finalize(self):
        if self._final:
            return self
        tiles = {}   # key -> (array, mode)
        refs = []    # (cube, face, key)
        uniq = 0
        for bn in self.order:
            for ci, c in enumerate(self.bones[bn].cubes):
                for f in c.paint_faces():
                    mat = c.mats.get(f) or c.mat
                    dens = c.density or mat.density or self.density
                    fw, fh = c.face_dims(f)
                    w = max(1, int(round((fw + 2 * c.inflate) * dens)))
                    h = max(1, int(round((fh + 2 * c.inflate) * dens)))
                    if mat.spatial:
                        uniq += 1
                        key = (mat.key, w, h, f, "u", uniq)
                    else:
                        key = (mat.key, w, h, f if mat.directional else GROUP[f], c.variant)
                    if key not in tiles:
                        tiles[key] = ([self._paint(mat, c, f, w, h, key, alt) for alt in (None,) + self.alts],
                                      mat.mode)
                    refs.append((c, f, key))
        self._pack(tiles, refs)
        self._final = True
        return self

    def _paint(self, mat, c, f, w, h, key, alt=None):
        ctx = FaceCtx()
        ctx.alt = alt
        ctx.w, ctx.h, ctx.face, ctx.group = w, h, f, GROUP[f]
        ctx.size = c.size
        ctx.variant = c.variant
        ctx.rng = np.random.default_rng(_seed(self.name, key[:5]))
        tl, tr, br, bl = [np.array(p, dtype=float) for p in c.corners(f)]
        u = (np.arange(w) + 0.5) / w
        v = (np.arange(h) + 0.5) / h
        U, V = np.meshgrid(u, v)
        P = tl[None, None, :] + U[..., None] * (tr - tl)[None, None, :] + V[..., None] * (bl - tl)[None, None, :]
        ctx.U, ctx.V = U, V
        ctx.X, ctx.Y, ctx.Z = P[..., 0], P[..., 1], P[..., 2]
        t = np.asarray(mat.fn(ctx), dtype=float)
        if t.shape == (h, w, 4):
            t = np.concatenate([t, np.zeros((h, w, 1))], axis=2)
        if t.shape != (h, w, 5):
            raise ValueError(f"{self.name}: material {mat.key} returned {t.shape}, wanted {(h, w, 5)}")
        return np.clip(t, 0, 1)

    def _pack(self, tiles, refs):
        pad = self.pad
        items = sorted(tiles.items(), key=lambda kv: (-kv[1][0][0].shape[0], -kv[1][0][0].shape[1]))
        area = sum((t[0].shape[0] + 2 * pad) * (t[0].shape[1] + 2 * pad) for _, (t, _m) in items)
        maxw = max(t[0].shape[1] + 2 * pad for _, (t, _m) in items)
        sizes = [(w, h) for w in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
                 for h in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096) if h <= w <= 2 * h]
        sizes.sort(key=lambda s: (s[0] * s[1], s[0]))
        placed = None
        for W, H in sizes:
            if W * H < area or W < maxw:
                continue
            pos, x, y, row = {}, 0, 0, 0
            ok = True
            for key, (t, _m) in items:
                tw, th = t[0].shape[1] + 2 * pad, t[0].shape[0] + 2 * pad
                if x + tw > W:
                    x, y, row = 0, y + row, 0
                if y + th > H:
                    ok = False
                    break
                pos[key] = (x + pad, y + pad)
                x += tw
                row = max(row, th)
            if ok:
                placed = (W, H, pos)
                break
        if placed is None:
            raise ValueError(f"{self.name}: texture does not fit in 4096x4096")
        W, H, pos = placed
        for ai, alt in enumerate((None,) + self.alts):
            img = np.zeros((H, W, 4), dtype=np.uint8)
            for key, (ts, mode) in items:
                t = ts[ai]
                x, y = pos[key]
                h, w = t.shape[:2]
                rgba = np.zeros((h, w, 4), dtype=np.uint8)
                rgba[..., :3] = np.round(t[..., :3] * 255)
                if mode == "blend":
                    rgba[..., 3] = np.round(t[..., 3] * 255)
                else:
                    a = np.clip(255 - np.round(t[..., 4] * 250), 5, 255)
                    a[t[..., 3] < 0.5] = 0
                    rgba[..., 3] = a
                if pad:
                    img[y - pad:y + h + pad, x - pad:x + w + pad] = np.pad(rgba, ((pad, pad), (pad, pad), (0, 0)),
                                                                           mode="edge")
                else:
                    img[y:y + h, x:x + w] = rgba
            self.atlases[alt or "default"] = Image.fromarray(img, "RGBA")
        for c, f, key in refs:
            x, y = pos[key]
            t = tiles[key][0][0]
            c.uv[f] = (x, y, t.shape[1], t.shape[0])
        self.atlas = self.atlases["default"]
        self.tex_size = (W, H)

    # ---- kinematics ------------------------------------------------------
    def bone_matrices(self, pose=None):
        pose = pose or {}
        out = {}
        for n in self.order:
            b = self.bones[n]
            pr, pp, ps = pose.get(n, ((0, 0, 0), (0, 0, 0), (1, 1, 1)))
            rot = tuple(b.rot[i] + pr[i] for i in range(3))
            m = _trs(b.pivot, rot, pp, ps)
            out[n] = out[b.parent] @ m if b.parent else m
        return out

    def world_quads(self, pose=None, hide=()):
        """List of (4x3 world verts TL,TR,BR,BL, (u,v,w,h), mode) for rendering."""
        self.finalize()
        mats = self.bone_matrices(pose)
        quads = []
        for n in self.order:
            if any(n.startswith(h) for h in hide):
                continue
            bm = mats[n]
            for c in self.bones[n].cubes:
                m = bm
                if c.rot:
                    m = bm @ _trs(c.pivot or tuple(c.origin[i] + c.size[i] / 2 for i in range(3)), c.rot)
                for f in c.paint_faces():
                    pts = np.array([list(p) + [1.0] for p in c.corners(f)])
                    w = (m @ pts.T).T[:, :3]
                    quads.append((w, c.uv[f], (c.mats.get(f) or c.mat).mode))
        return quads

    def bbox(self, pose=None):
        pts = np.concatenate([q[0] for q in self.world_quads(pose)])
        return pts.min(axis=0), pts.max(axis=0)

    # ---- export ----------------------------------------------------------
    def to_geo(self):
        self.finalize()
        bones = []
        for n in self.order:
            b = self.bones[n]
            jb = {"name": n}
            if b.parent:
                jb["parent"] = b.parent
            jb["pivot"] = _r3((-b.pivot[0], b.pivot[1], b.pivot[2]))
            if any(b.rot):
                jb["rotation"] = _r3((-b.rot[0], -b.rot[1], b.rot[2]))
            if b.binding:
                jb["binding"] = b.binding
            if b.locators:
                jb["locators"] = {k: _r3((-v[0], v[1], v[2])) for k, v in b.locators.items()}
            if b.cubes:
                jb["cubes"] = [self._cube_json(c) for c in b.cubes]
            bones.append(jb)
        if self.bounds:
            bw, bh, bo = self.bounds
        else:
            lo, hi = self.bbox()
            ext = max(abs(lo[0]), abs(hi[0]), abs(lo[2]), abs(hi[2])) / 16.0
            bw = math.ceil(ext * 2 * 1.6 + 2)
            bh = math.ceil((hi[1] - min(lo[1], 0)) / 16.0 * 1.4 + 2)
            bo = (0, round((hi[1] + min(lo[1], 0)) / 32.0, 2), 0)
        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": f"geometry.grimoire.{self.name}",
                    "texture_width": self.tex_size[0],
                    "texture_height": self.tex_size[1],
                    "visible_bounds_width": bw,
                    "visible_bounds_height": bh,
                    "visible_bounds_offset": list(bo),
                },
                "bones": bones,
            }],
        }

    def _cube_json(self, c):
        ox = -(c.origin[0] + c.size[0])
        j = {"origin": _r3((ox, c.origin[1], c.origin[2])), "size": _r3(c.size)}
        if c.inflate:
            j["inflate"] = round(c.inflate, 4)
        if c.rot:
            pv = c.pivot or tuple(c.origin[i] + c.size[i] / 2 for i in range(3))
            j["pivot"] = _r3((-pv[0], pv[1], pv[2]))
            j["rotation"] = _r3((-c.rot[0], -c.rot[1], c.rot[2]))
        uv = {}
        painted = c.paint_faces()
        for f in painted:
            u, v, w, h = c.uv[f]
            if f in ("up", "down"):
                uv[f] = {"uv": [u + w, v + h], "uv_size": [-w, -h]}
            else:
                uv[f] = {"uv": [u, v], "uv_size": [w, h]}
        if len(painted) < len(c.faces):
            # the dropped back of a plane: translucent sheets keep a back face (the blend material may
            # cull back faces) mapped so both sides show the same texel at every point of the sheet
            front, back = c.FRONT[c.plane], c.BACK[c.plane]
            if (c.mats.get(front) or c.mat).mode == "blend":
                u, v, w, h = c.uv[front]
                uv[back] = {"uv": [u + w, v], "uv_size": [-w, h]}
        j["uv"] = uv
        return j

    def save(self, rp_dir, sub="entity"):
        """Write geometry + texture into a resource pack. Returns (geo id, texture path)."""
        geo = self.to_geo()
        gp = os.path.join(rp_dir, "models", "entity", f"{self.name}.geo.json")
        tp = os.path.join(rp_dir, "textures", sub, f"{self.name}.png")
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        with open(gp, "w") as fh:
            json.dump(geo, fh, separators=(",", ":"))
        self.atlas.save(tp, optimize=True)
        for alt in self.alts:
            self.atlases[alt].save(tp[:-4] + f"__{alt}.png", optimize=True)
        return f"geometry.grimoire.{self.name}", f"textures/{sub}/{self.name}"


def _r3(v):
    return [round(float(x), 4) + 0.0 for x in v]


# ---- shape helpers --------------------------------------------------------
def ring(bone, center, radius, n, seg_size, mat, axis="y", start=0.0, sweep=360.0, tilt=0.0, **kw):
    """n boxes arranged tangentially around a circle. seg_size = (tangent, radial, thick).

    axis is the ring's normal. Each segment is a rotated cube pivoting on its own center.
    """
    cx, cy, cz = center
    t_len, r_len, th = seg_size
    out = []
    for i in range(n):
        a = start + sweep * (i + 0.5) / n
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        if axis == "y":
            p = (cx + radius * ca, cy, cz + radius * sa)
            size, rot = (r_len, th, t_len), (0, -a, 0)
        elif axis == "z":
            p = (cx + radius * ca, cy + radius * sa, cz)
            size, rot = (r_len, t_len, th), (0, 0, a)
        else:
            p = (cx, cy + radius * sa, cz + radius * ca)
            size, rot = (th, t_len, r_len), (-a, 0, 0)
        if tilt:
            rot = tuple(rot[k] + (tilt if k == {"y": 2, "z": 0, "x": 1}[axis] else 0) for k in range(3))
        out.append(bone.box(p, size, mat, rot=rot, pivot=p, variant=kw.get("variant", 0) + (i % kw.get("cycle", 1)),
                            **{k: v for k, v in kw.items() if k not in ("variant", "cycle")}))
    return out


def chain(model, prefix, parent, start, direction, lengths, **kw):
    """Create a chain of bones along a direction. Returns list of bones; each bone's
    pivot is its joint. direction is a unit-ish vector; lengths per segment."""
    d = np.array(direction, dtype=float)
    d = d / np.linalg.norm(d)
    p = np.array(start, dtype=float)
    bones = []
    par = parent
    for i, L in enumerate(lengths):
        b = model.bone(f"{prefix}{i + 1}", par, pivot=tuple(p))
        bones.append(b)
        par = b.name
        p = p + d * L
    return bones
