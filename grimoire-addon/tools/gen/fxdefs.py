"""FX construct framework: one registration emits every file a spell construct needs."""
import json
import os
from .modelkit import Model, geometry_file
from .anim import Anim, anim_file, controller_file, phase_controller, pulse_controller

REGISTRY = []
# constructs that sit on (follow) the caster: see Fx.eye_guard
WORN = {"fx_pl_molt", "fx_d_velvet", "fx_p_mantle", "fx_b_rose_aegis", "fx_pr_benediction", "fx_i_wings", "fx_p_salvo",
        "fx_pl_stellarator", "fx_pr_sail", "fx_d_double", "fx_d_silhouette", "fx_pr_afterimage", "fx_pl_tail",
        "fx_pl_skates", "fx_d_lock", "fx_p_sonar", "fx_i_lotus"}

FX_PROPERTIES = {
    "grimoire:phase": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
    "grimoire:yaw": {"type": "float", "range": [-720.0, 720.0], "default": 0.0, "client_sync": True},
    "grimoire:pitch": {"type": "float", "range": [-90.0, 90.0], "default": 0.0, "client_sync": True},
    "grimoire:size": {"type": "float", "range": [0.0, 64.0], "default": 1.0, "client_sync": True},
    "grimoire:len": {"type": "float", "range": [0.0, 128.0], "default": 1.0, "client_sync": True},
    "grimoire:variant": {"type": "int", "range": [0, 15], "default": 0, "client_sync": True},
    "grimoire:aux": {"type": "int", "range": [0, 255], "default": 0, "client_sync": True},
}

PRE_ANIMATION = [
    "v.ty = q.property('grimoire:yaw') - q.body_y_rotation;",
    "v.dy = math.mod(math.mod(v.ty - v.yaw, 360) + 540, 360) - 180;",
    "v.first = q.life_time < 0.1;",
    "v.yaw = v.first ? v.ty : v.yaw + v.dy * 0.4;",
    "v.pitch = v.first ? q.property('grimoire:pitch') : math.lerp(v.pitch, q.property('grimoire:pitch'), 0.4);",
    "v.size = v.first ? q.property('grimoire:size') : math.lerp(v.size, q.property('grimoire:size'), 0.25);",
    "v.len = v.first ? q.property('grimoire:len') : math.lerp(v.len, q.property('grimoire:len'), 0.35);",
    "v.ph = q.property('grimoire:phase');",
    "v.var = q.property('grimoire:variant');",
]

MATERIALS = {"default": "entity_emissive_alpha", "trans": "entity_alphablend", "glow": "entity_beam_additive"}


class Fx:
    def __init__(self, name, school, tex=(128, 128), bounds=(8, 8, (0, 1, 0)), family=("grimoire_fx", "inanimate"),
                 lifetime=120, variants=None, center=(0, 0, 0), components=None):
        self.name = name
        self.school = school
        self.ident = f"grimoire:{name}"
        self.geo_id = f"geometry.grimoire.{name}"
        from .texkit import Atlas
        # constructs are seen up close: one texel per model pixel (was half), like the summoned mobs
        atlas = Atlas(tex[0], tex[1], max_h=2048, density=1.0)
        atlas.lit_glow = True
        self.model = Model(self.geo_id, tex[0], tex[1], bounds, atlas=atlas)
        self.model.standard_root(center)
        self.model.bone("fade", "pitch", pivot=center)
        self.top = "fade"
        self.anims = {}
        self.phases = {}
        self.keep_list = []
        self.pulse_anim = None
        self.family = list(family)
        self.lifetime = lifetime
        self.variants = variants  # list of extra texture paths (generated elsewhere)
        self.custom_bp = None
        self.custom_scripts = None
        self.extra_textures = {}
        self.images = {}  # rp-relative path (no extension) -> RGBA array, saved at write time
        self.center = center
        self.components = components or {}
        self.tints = None  # list of RGB multipliers -> one texture variant each (selected by grimoire:variant)
        REGISTRY.append(self)

    # ---------------------------------------------------------------- model helpers
    def bone(self, name, parent=None, pivot=None, rotation=None):
        return self.model.bone(name, parent or self.top, pivot=pivot if pivot is not None else self.center, rotation=rotation)

    def __getitem__(self, name):
        return self.model[name]

    # ---------------------------------------------------------------- animation helpers
    def anim(self, short, loop=False, length=None):
        a = Anim(f"animation.grimoire.{self.name}.{short}", loop=loop, length=length)
        self.anims[short] = a
        return a

    def phase(self, n, *shorts):
        self.phases.setdefault(n, [])
        self.phases[n].extend(shorts)
        return self

    def keep(self, *shorts):
        self.keep_list.extend(shorts)
        return self

    def pulse(self, short):
        self.pulse_anim = short
        return self

    def default_form(self, t=0.3, overshoot=1.08):
        a = self.anim("form", length=t)
        a.scale("fade", {0: [0.01, 0.01, 0.01], t * 0.7: [overshoot] * 3, t: [1, 1, 1]})
        return "form"

    def default_dissolve(self, t=0.5, spin=40):
        a = self.anim("dissolve", length=t + 0.2)
        a.scale("fade", {0: [1, 1, 1], t * 0.4: [1.06, 1.06, 1.06], t: [0.0, 0.0, 0.0]})
        if spin:
            a.rot("fade", {0: [0, 0, 0], t: [0, spin, 0]})
        return "dissolve"

    # ---------------------------------------------------------------- emit
    def _extents(self):
        xs, ys = [], []
        for b in self.model.bones:
            for c in b.cubes:
                o, sz = c["origin"], c["size"]
                pad = max(sz) * 0.5 if c.get("rotation") else 0.0
                xs += [abs(o[0]) + pad, abs(o[0] + sz[0]) + pad, abs(o[2]) + pad, abs(o[2] + sz[2]) + pad]
                ys += [o[1] - pad, o[1] + sz[1] + pad]
        return xs, ys

    def auto_bounds(self):
        """Culling bounds from the real geometry, doubled for the size property; stretched constructs (beams,
        jets, strings, bands) are lengthened by script, so they get room for 24+ blocks."""
        xs, ys = self._extents()
        if not xs:
            return
        w = max(xs) * 2 / 16 * 2.0 + 1.0
        h = (max(ys) - min(ys)) / 16 * 2.0 + 1.0
        if "stretch" in self.model.by_name:
            w = max(w, 52.0)
            h = max(h, 52.0)
        bw, bh, off = self.model.bounds
        cy = (max(ys) + min(ys)) / 2 / 16
        self.model.bounds = (round(max(bw, w), 2), round(max(bh, h), 2), (off[0], round(cy, 2), off[2]))

    def eye_guard(self):
        """Worn constructs only (they sit on the caster): bones that pass within ~half a block of eye height are
        hidden when the camera is that close - the caster's own first-person view. Everyone else, and the
        caster in third person, still see them."""
        if self.name not in WORN:
            return
        import math
        eye = (0.0, 25.9, 0.0)

        def rot_pt(p, c):
            r = c.get("rotation")
            if not r:
                return p
            pv = c.get("pivot", [c["origin"][i] + c["size"][i] / 2 for i in range(3)])
            x, y, z = p[0] - pv[0], p[1] - pv[1], p[2] - pv[2]
            ax, ay, az = (math.radians(-r[0]), math.radians(r[1]), math.radians(-r[2]))
            y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
            x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
            x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
            return (x + pv[0], y + pv[1], z + pv[2])

        near = []
        for b in self.model.bones:
            hit = False
            for c in b.cubes:
                o, sz = c["origin"], c["size"]
                for fx_ in (0, 0.25, 0.5, 0.75, 1):
                    for fy in (0, 0.25, 0.5, 0.75, 1):
                        for fz in (0, 0.5, 1):
                            q = rot_pt((o[0] + sz[0] * fx_, o[1] + sz[1] * fy, o[2] + sz[2] * fz), c)
                            if sum((q[k] - eye[k]) ** 2 for k in range(3)) < 7.5 ** 2:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        break
                if hit:
                    break
            if hit:
                near.append(b.name)
        if not near:
            return
        a = Anim(f"animation.grimoire.{self.name}.eyeguard", loop=True)
        for n in near:
            a.scale(n, ["q.distance_from_camera > 2.3 ? 1 : 0"] * 3)
        self.anims["eyeguard"] = a
        self.keep("eyeguard")

    def finalize(self):
        if getattr(self, "_finalized", False):
            return
        self._finalized = True
        self.auto_bounds()
        self.eye_guard()
        if 1 not in self.phases:
            self.phase(1, self.default_form())
        if 15 not in self.phases:
            self.phase(15, self.default_dissolve())
        orient = Anim(f"animation.grimoire.{self.name}.orient", loop=True)
        orient.scale("root", "math.max(0.0001, v.size)")
        orient.rot("yaw", [0, "v.yaw", 0])
        orient.rot("pitch", ["v.pitch", 0, 0])
        if "stretch" in self.model.by_name:
            orient.scale("stretch", [1, 1, "math.max(0.0001, v.len)"])
        self.anims["orient"] = orient
        # make sure every bone referenced in animations exists
        for a in self.anims.values():
            for bone in a.bones:
                if bone not in self.model.by_name:
                    raise ValueError(f"{self.name}: animation {a.ident} references missing bone {bone}")

    def client_entity(self):
        anims = {short: a.ident for short, a in self.anims.items()}
        anims["ctrl"] = f"controller.animation.grimoire.{self.name}"
        animate = ["orient", "ctrl"] + self.keep_list
        if self.pulse_anim:
            anims["pulse_ctrl"] = f"controller.animation.grimoire.{self.name}.pulse"
            animate.append("pulse_ctrl")
        textures = {"default": f"textures/entity/grimoire/{self.name}"}
        rc = "controller.render.grimoire.fx"
        if self.variants:
            for i, t in enumerate(self.variants):
                textures[f"v{i}"] = t
            rc = f"controller.render.grimoire.{self.name}"
        scripts = {
            "initialize": ["v.yaw = 0; v.pitch = 0; v.size = 1; v.len = 1; v.last_aux = 0;"],
            "pre_animation": PRE_ANIMATION + (self.custom_scripts or []),
            "animate": animate,
        }
        return {
            "format_version": "1.10.0",
            "minecraft:client_entity": {
                "description": {
                    "identifier": self.ident,
                    "materials": MATERIALS,
                    "textures": textures,
                    "geometry": {"default": self.geo_id},
                    "animations": anims,
                    "scripts": scripts,
                    "render_controllers": [rc],
                }
            },
        }

    def render_controller(self):
        if not self.variants:
            return None
        arr = [f"Texture.v{i}" for i in range(len(self.variants))]
        return {
            "geometry": "Geometry.default",
            "arrays": {"textures": {"Array.tex": arr}},
            "textures": ["Array.tex[math.clamp(q.property('grimoire:variant'), 0, %d)]" % (len(arr) - 1)],
            "materials": [{"*": "Material.default"}, {"t_*": "Material.trans"}, {"g_*": "Material.glow"}],
        }

    def behavior_entity(self):
        if self.custom_bp:
            return self.custom_bp(self)
        return {
            "format_version": "1.26.30",
            "minecraft:entity": {
                "description": {
                    "identifier": self.ident,
                    "is_spawnable": False,
                    "is_summonable": True,
                    "properties": FX_PROPERTIES,
                },
                "component_groups": {"grimoire:despawn": {"minecraft:instant_despawn": {}}},
                "components": {
                    "minecraft:type_family": {"family": self.family},
                    "minecraft:collision_box": {"width": 0.01, "height": 0.01},
                    "minecraft:physics": {"has_collision": False, "has_gravity": False},
                    "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                    "minecraft:health": {"value": 1, "max": 1},
                    "minecraft:knockback_resistance": {"value": 1.0},
                    "minecraft:fire_immune": {},
                    "minecraft:breathable": {"breathes_air": True, "breathes_water": True, "breathes_lava": True, "breathes_solids": True},
                    "minecraft:timer": {"time": self.lifetime, "looping": False,
                                        "time_down_event": {"event": "grimoire:expire", "target": "self"}},
                    **self.components,
                },
                "events": {"grimoire:expire": {"add": {"component_groups": ["grimoire:despawn"]}}},
            },
        }

    def apply_tints(self):
        """Tinted copies of the atlas: only bright, unsaturated (white light / glass) texels take the colour,
        metal frames and dark parts keep theirs."""
        import numpy as np
        base = self.model.atlas.img
        rgb = base[..., :3]
        # every unsaturated (white / grey / glass) texel, dim ones too, so a glow's falloff takes the colour
        # instead of staying grey; saturated metal (gold frames) keeps its colour
        mask = ((rgb.max(-1) > 24) & (rgb.max(-1) - rgb.min(-1) < 70))[..., None]
        self.variants = []
        for i, t in enumerate(self.tints):
            arr = base.copy()
            arr[..., :3] = np.where(mask, np.clip(rgb * np.array(t, np.float32), 0, 255), rgb)
            rel = f"textures/entity/grimoire/{self.name}_t{i}"
            self.images[rel] = arr
            self.variants.append(rel)

    def write(self, rp, bp):
        self.finalize()
        if self.tints:
            self.apply_tints()
        os.makedirs(f"{rp}/models/entity/grimoire", exist_ok=True)
        os.makedirs(f"{rp}/textures/entity/grimoire", exist_ok=True)
        os.makedirs(f"{rp}/animations/grimoire", exist_ok=True)
        os.makedirs(f"{rp}/animation_controllers/grimoire", exist_ok=True)
        os.makedirs(f"{rp}/entity/grimoire", exist_ok=True)
        os.makedirs(f"{bp}/entities/grimoire", exist_ok=True)
        dump(f"{rp}/models/entity/grimoire/{self.name}.geo.json", geometry_file([self.model]))
        self.model.atlas.save(f"{rp}/textures/entity/grimoire/{self.name}.png")
        for rel, arr in self.images.items():
            save_png(arr, f"{rp}/{rel}.png")
        dump(f"{rp}/animations/grimoire/{self.name}.animation.json", anim_file(self.anims.values()))
        ctrls = {f"controller.animation.grimoire.{self.name}": phase_controller(None, self.phases)}
        if self.pulse_anim:
            ctrls[f"controller.animation.grimoire.{self.name}.pulse"] = pulse_controller(self.pulse_anim)
        dump(f"{rp}/animation_controllers/grimoire/{self.name}.ac.json", controller_file(ctrls))
        dump(f"{rp}/entity/grimoire/{self.name}.entity.json", self.client_entity())
        dump(f"{bp}/entities/grimoire/{self.name}.json", self.behavior_entity())


def save_png(arr, path):
    import numpy as np
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(path, optimize=True)


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def shared_render_controller():
    return {
        "format_version": "1.10.0",
        "render_controllers": {
            "controller.render.grimoire.fx": {
                "geometry": "Geometry.default",
                "textures": ["Texture.default"],
                "materials": [{"*": "Material.default"}, {"t_*": "Material.trans"}, {"g_*": "Material.glow"}],
            }
        },
    }
