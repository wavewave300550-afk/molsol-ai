"""Procedural Bedrock geometry builder.

Conventions (derived from vanilla 1.26.60 resource files, see README "Implementation notes"):
  * model forward is -Z, up is +Y, raw +X is the entity's left side;
  * bone rotation +Y turns the part right (same sense as Minecraft yaw);
  * bone rotation +X pitches a forward-pointing part downward (same sense as Minecraft pitch);
  * Z rotations are only used for symmetric spins (their sign never matters for the look);
  * cube origins / bone pivots are absolute model-space pixels (16 px = 1 block) in bind pose.
Rings and discs are therefore always built in the horizontal XZ plane and re-oriented by an
X rotation on a parent bone, which keeps tangent alignment independent of the Z sign.
"""
import math
import re
from .texkit import Atlas

PX = 16.0


def r6(v):
    return round(float(v), 4)


class Bone:
    def __init__(self, model, name, parent=None, pivot=(0, 0, 0), rotation=None, binding=None):
        self.model = model
        self.name = name
        self.parent = parent
        self.pivot = [r6(x) for x in pivot]
        self.rotation = [r6(x) for x in rotation] if rotation else None
        self.binding = binding
        self.cubes = []

    # ------------------------------------------------------------------ primitive
    def box(self, origin, size, style, rotation=None, pivot=None, inflate=0.0, faces=None, tile=None, mirror_uv=False):
        """Axis aligned box. `style` names a texture painter (see texkit.STYLES).
        `faces` optionally maps face names to alternative styles; `tile` forces a tile size."""
        size = [max(0.0, float(s)) for s in size]
        cube = {"origin": [r6(x) for x in origin], "size": [r6(s) for s in size]}
        if rotation and any(abs(a) > 1e-6 for a in rotation):
            cube["rotation"] = [r6(a) for a in rotation]
            cx = origin[0] + size[0] / 2
            cy = origin[1] + size[1] / 2
            cz = origin[2] + size[2] / 2
            cube["pivot"] = [r6(x) for x in (pivot if pivot is not None else (cx, cy, cz))]
        if inflate:
            cube["inflate"] = r6(inflate)
        uv = {}
        w, h, d = size
        dims = {
            "north": (w, h), "south": (w, h), "east": (d, h), "west": (d, h), "up": (w, d), "down": (w, d),
        }
        for face, (fw, fh) in dims.items():
            if fw <= 0 and fh <= 0:
                continue
            st = (faces or {}).get(face, style)
            if st is None:
                continue
            if isinstance(st, tuple) and st[0] == 'rect':
                _, u, v, tw, th = st
            else:
                n = self.name.lower()
                mat = "g" if n.startswith("g_") or n.startswith("flow_") else "t" if n.startswith("t_") else "default"
                u, v, tw, th = self.model.atlas.tile(st, fw, fh, tile, lit=mat == "default", mat=mat)
            if mirror_uv:
                uv[face] = {"uv": [u + tw, v], "uv_size": [-tw, th]}
            else:
                uv[face] = {"uv": [u, v], "uv_size": [tw, th]}
        cube["uv"] = uv
        self.cubes.append(cube)
        return cube

    def cbox(self, center, size, style, rotation=None, **kw):
        """Box defined by its center (rotation pivots around the center)."""
        o = (center[0] - size[0] / 2, center[1] - size[1] / 2, center[2] - size[2] / 2)
        return self.box(o, size, style, rotation=rotation, pivot=center if rotation else None, **kw)

    # ------------------------------------------------------------------ composite (all in pixels)
    def ring(self, center, radius, thickness, height, segments, style, start=0.0, arc=360.0, gap=0.0, faces=None):
        """Ring in the XZ plane (axis +Y). Segments are tangent boxes; `gap` in degrees between them."""
        step = arc / segments
        chord = 2 * radius * math.tan(math.radians(max(0.5, step - gap) / 2)) + 0.02
        for i in range(segments):
            th = start + step * i + step / 2
            x = center[0] + radius * math.cos(math.radians(th))
            z = center[2] + radius * math.sin(math.radians(th))
            self.cbox((x, center[1], z), (chord, height, thickness), style, rotation=(0, 90 - th, 0), faces=faces)

    def cylinder(self, center, radius, height, segments, style, thickness=None, faces=None):
        """Hollow cylinder wall (axis +Y) from center.y to center.y+height."""
        t = thickness if thickness is not None else max(0.6, radius * 0.25)
        self.ring((center[0], center[1] + height / 2, center[2]), radius, t, height, segments, style, faces=faces)

    def solid_cylinder(self, center, radius, height, style, layers=3, faces=None):
        """Filled cylinder approximation: overlapping boxes rotated around Y."""
        side = radius * math.sqrt(2)
        for i in range(layers):
            self.cbox((center[0], center[1] + height / 2, center[2]), (side, height, side), style,
                      rotation=(0, (90.0 / layers) * i, 0), faces=faces)

    def disc(self, center, radius, style, thickness=0.0, tile=None):
        """Flat square plane (both faces visible) used for textured circles."""
        return self.cbox(center, (radius * 2, thickness, radius * 2), style, tile=tile,
                         faces={"north": None, "south": None, "east": None, "west": None} if thickness == 0 else None)

    def cone(self, base, radius, height, steps, style, segments=8, tip=0.15):
        """Stepped cone pointing +Y."""
        for i in range(steps):
            k0 = i / steps
            rr = radius * (1 - k0 * (1 - tip))
            hh = height / steps
            self.solid_cylinder((base[0], base[1] + hh * i, base[2]), rr, hh * 1.02, style, layers=2)

    def crystal(self, base, length, width, style, tip_style=None, axis_rot=0.0, tip=0.45):
        """Hexagonal-looking crystal along +Y: 3 rotated prisms and a 3-step tapered tip."""
        tip_style = tip_style or style
        body = length * (1 - tip)
        for a in (0, 60, 120):
            self.cbox((base[0], base[1] + body / 2, base[2]), (width * 0.87, body, width * 0.5), style,
                      rotation=(0, a + axis_rot, 0))
        th = length * tip
        for j, k in enumerate((0.72, 0.45, 0.2)):
            hh = th / 3
            y = base[1] + body + hh * j + hh / 2
            for a in (0, 60, 120):
                self.cbox((base[0], y, base[2]), (width * 0.87 * k, hh * 1.05, width * 0.5 * k), tip_style,
                          rotation=(0, a + axis_rot + 30 * j, 0))

    def blade(self, base, length, width, thickness, style, edge_style=None, taper_steps=4, curve=0.0):
        """Flat blade along +Y with a tapered point; optional glowing edge strips."""
        body = length * 0.72
        self.cbox((base[0], base[1] + body / 2, base[2]), (width, body, thickness), style)
        if edge_style:
            self.cbox((base[0] - width / 2 - 0.15, base[1] + body / 2, base[2]), (0.3, body, thickness * 1.2), edge_style)
            self.cbox((base[0] + width / 2 + 0.15, base[1] + body / 2, base[2]), (0.3, body, thickness * 1.2), edge_style)
        rest = length - body
        for i in range(taper_steps):
            k = 1 - (i + 1) / (taper_steps + 1)
            hh = rest / taper_steps
            self.cbox((base[0], base[1] + body + hh * i + hh / 2, base[2]), (width * k, hh * 1.02, thickness * (0.6 + 0.4 * k)),
                      edge_style if (edge_style and i == taper_steps - 1) else style)

    def chain(self, start, links, link_len, link_w, wire, style, along="y"):
        """Alternating chain links along +Y (or +Z)."""
        for i in range(links):
            c = [start[0], start[1], start[2]]
            if along == "y":
                c[1] += link_len * 0.82 * i + link_len / 2
            else:
                c[2] -= link_len * 0.82 * i + link_len / 2
            rot = 90 if i % 2 else 0
            if along == "y":
                # link: two long sides + two short ends, rotated about Y for alternation
                for sx in (-1, 1):
                    off = (link_w / 2 - wire / 2) * sx
                    dx, dz = (off, 0) if rot == 0 else (0, off)
                    self.cbox((c[0] + dx, c[1], c[2] + dz), (wire, link_len, wire), style)
                for sy in (-1, 1):
                    self.cbox((c[0], c[1] + sy * (link_len / 2 - wire / 2), c[2]),
                              (link_w if rot == 0 else wire, wire, wire if rot == 0 else link_w), style)
            else:
                for sx in (-1, 1):
                    off = (link_w / 2 - wire / 2) * sx
                    dx, dy = (off, 0) if rot == 0 else (0, off)
                    self.cbox((c[0] + dx, c[1] + dy, c[2]), (wire, wire, link_len), style)
                for sz in (-1, 1):
                    self.cbox((c[0], c[1], c[2] + sz * (link_len / 2 - wire / 2)),
                              (link_w if rot == 0 else wire, wire if rot == 0 else link_w, wire), style)

    def hexagon(self, center, radius, thickness, height, style, start=0.0):
        self.ring(center, radius, thickness, height, 6, style, start=start)

    def hexplate(self, center, radius, height, style, edge_style=None):
        """Filled hexagonal plate (3 rotated boxes) in XZ, optional rim."""
        w = radius * 2 * 0.866
        for a in (0, 60, 120):
            self.cbox(center, (w, height, radius), style, rotation=(0, a, 0))
        if edge_style:
            self.hexagon(center, radius * 0.97, 0.8, height * 1.15, edge_style, start=30)

    def sphere_shell(self, center, radius, style, rings=5, segs=12, thickness=0.6, band=1.2):
        """Latitude bands approximating a sphere (or dome when used with lat range)."""
        for i in range(rings):
            lat = -80 + 160 * (i + 0.5) / rings
            rr = radius * math.cos(math.radians(lat))
            y = center[1] + radius * math.sin(math.radians(lat))
            self.ring((center[0], y, center[2]), rr, thickness, band, max(6, int(segs * rr / radius + 0.5)), style)

    def dome(self, center, radius, style, bands=5, segs=16, thickness=0.6, band=1.2, cap=True):
        for i in range(bands):
            lat = 90 * i / bands
            rr = radius * math.cos(math.radians(lat))
            y = center[1] + radius * math.sin(math.radians(lat))
            self.ring((center[0], y, center[2]), rr, thickness, band, max(6, int(segs * rr / radius + 0.5)), style)
        if cap:
            self.cbox((center[0], center[1] + radius - band / 2, center[2]), (radius * 0.35, band, radius * 0.35), style)


class Model:
    def __init__(self, ident, tex_w=128, tex_h=128, bounds=(4, 4, (0, 1, 0)), atlas=None):
        self.ident = ident
        self.atlas = atlas or Atlas(tex_w, tex_h)
        self.bones = []
        self.by_name = {}
        self.bounds = bounds

    def bone(self, name, parent=None, pivot=(0, 0, 0), rotation=None, binding=None):
        if name in self.by_name:
            raise ValueError(f"duplicate bone {name} in {self.ident}")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"unsafe bone name {name!r} in {self.ident}")
        b = Bone(self, name, parent, pivot, rotation, binding)
        self.bones.append(b)
        self.by_name[name] = b
        return b

    def __getitem__(self, name):
        return self.by_name[name]

    def standard_root(self, center=(0, 0, 0)):
        """root > yaw > pitch > (content). root scales with grimoire:size, yaw/pitch orient."""
        self.bone("root", pivot=center)
        self.bone("yaw", "root", pivot=center)
        self.bone("pitch", "yaw", pivot=center)
        return "pitch"

    def to_json(self):
        bones = []
        for b in self.bones:
            d = {"name": b.name, "pivot": b.pivot}
            if b.parent:
                d["parent"] = b.parent
            if b.rotation:
                d["rotation"] = b.rotation
            if b.binding:
                d["binding"] = b.binding
            if b.cubes:
                d["cubes"] = b.cubes
            bones.append(d)
        w, h, off = self.bounds
        return {
            "description": {
                "identifier": self.ident,
                "texture_width": self.atlas.w,
                "texture_height": self.atlas.h,
                "visible_bounds_width": w,
                "visible_bounds_height": h,
                "visible_bounds_offset": list(off),
            },
            "bones": bones,
        }

    def cube_count(self):
        return sum(len(b.cubes) for b in self.bones)


def geometry_file(models):
    return {"format_version": "1.16.0", "minecraft:geometry": [m.to_json() for m in models]}
