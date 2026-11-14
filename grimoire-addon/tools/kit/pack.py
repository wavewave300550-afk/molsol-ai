"""Pack registry: turns kit models/animations into Bedrock behavior + resource pack files."""
from __future__ import annotations

import contextlib
import fcntl
import json
import math
import os

from .anim import NS, Anim, animations_file, state_controller

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BP = os.path.join(ROOT, "behavior_packs", "grimoire_bp")
RP = os.path.join(ROOT, "resource_packs", "grimoire_rp")
PREVIEW = os.path.join(ROOT, "tools", "_preview")

ENTITY_FORMAT = "1.21.90"


@contextlib.contextmanager
def _locked():
    """Serialise read-merge-write of shared files when several builds run at once."""
    os.makedirs(os.path.join(ROOT, "tools"), exist_ok=True)
    with open(os.path.join(ROOT, "tools", ".build.lock"), "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")


def _merge(path, updates, key=None):
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    tgt = data
    if key:
        for k in key[:-1]:
            tgt = tgt.setdefault(k, {})
        tgt = tgt.setdefault(key[-1], {})
    tgt.update(updates)
    _write(path, data)
    return data


class Pack:
    def __init__(self):
        self.bp, self.rp = BP, RP
        self.actors = {}
        self.models = {}
        self.sound_defs = {}
        self.lang = {}
        self.item_textures = {}
        self.manifest = {}  # id -> info for docs / validation

    # ------------------------------------------------------------------ models
    def model(self, model, sub="entity/grimoire"):
        """Write a model's geometry + texture; returns (geometry id, texture path)."""
        if model.name not in self.models:
            self.models[model.name] = model.save(self.rp, sub=sub)
        return self.models[model.name]

    # ------------------------------------------------------------------ actors
    def actor(self, ident, model, anims=(), states=None, always=(), *, scale=1.0, lifetime=180,
              kinds=None, size_prop=False, visibility=None, sounds=None, particles=None, props=None,
              init=None, pre_anim=None, families=(), display=None, blend=0.2, extra_controllers=None,
              offscreen=True, collision=(0.2, 0.2), kind_materials=None):
        """Register a script-driven prop/creature entity (no AI, no gravity, invulnerable, transient).

        states: {int: [anim names]} mirrored from the int property grimoire:state.
        always: animation names that always play.  kinds: extra Models selectable through the
        int property grimoire:kind (0 = `model`).  size_prop: adds float property grimoire:size
        that multiplies the rendered scale.  visibility: [{bone_pattern: molang}].
        """
        full = f"{NS}:{ident}"
        anims = list(anims)
        models = [model] + list(kinds or [])
        skins = list(model.alts)
        if skins and len(models) > 1:
            raise ValueError(f"{ident}: texture skins and kinds cannot be combined")
        # Visible bounds are in blocks and are NOT multiplied by the render scale.  Too small a box
        # makes a big model vanish whenever its origin leaves the screen, so be generous.
        _sc = float(scale) if not isinstance(scale, str) else 4.0
        for m in models:
            if m.name in self.models:
                continue
            lo, hi = m.bbox()
            reach = max(abs(float(v)) for v in list(lo) + list(hi)) / 16.0 * _sc
            side = 192 if size_prop else int(min(256, max(64, math.ceil(reach * 3 + 32))))
            m.bounds = (side, side, (0, round(min(side / 4, max(2.0, float(hi[1]) / 32.0 * _sc)), 1), 0))
        geo_tex = [self.model(m) for m in models]
        for a in anims:
            a.model = ident
        amap = {a.name: a.full for a in anims}
        animate = []
        controllers = {}
        if states:
            cid, cj = state_controller(ident, states, blend=blend)
            controllers[cid] = cj
            amap["ctl_main"] = cid
            animate.append("ctl_main")
        for cname, cj in (extra_controllers or {}).items():
            cid = f"controller.animation.{NS}.{ident}.{cname}"
            controllers[cid] = cj
            amap[f"ctl_{cname}"] = cid
            animate.append(f"ctl_{cname}")
        for n in always:
            if isinstance(n, dict):
                animate.append(n)
            else:
                if n not in amap:
                    raise ValueError(f"{ident}: always-animation {n} not defined")
                animate.append(n)
        used = set()
        for spec in (states or {}).values():
            for n in (spec if isinstance(spec, (list, tuple)) else spec.get("animations", [])):
                used.add(n if isinstance(n, str) else next(iter(n)))
        for n in used:
            if n not in amap:
                raise ValueError(f"{ident}: state animation {n} not defined")

        # --- resource pack: client entity
        desc = {
            "identifier": full,
            "materials": {"default": "entity_emissive_alpha", "blend": "entity_alphablend"},
            "textures": {**{("default" if i == 0 else f"k{i}"): gt[1] for i, gt in enumerate(geo_tex)},
                         **{f"s{i + 1}": f"{geo_tex[0][1]}__{sk}" for i, sk in enumerate(skins)}},
            "geometry": {("default" if i == 0 else f"k{i}"): gt[0] for i, gt in enumerate(geo_tex)},
            "render_controllers": [f"controller.render.{NS}.{ident}"],
        }
        scripts = {}
        sc = scale if isinstance(scale, str) else repr(float(scale))
        if size_prop:
            sc = f"({sc}) * q.property('{NS}:size')"
        if sc not in ("1.0",):
            scripts["scale"] = sc
        if init:
            scripts["initialize"] = list(init)
        if pre_anim:
            scripts["pre_animation"] = list(pre_anim)
        if animate:
            scripts["animate"] = animate
        if offscreen:
            scripts["should_update_bones_and_effects_offscreen"] = "1.0"   # Molang, as vanilla writes it
        if amap:
            desc["animations"] = amap
        if scripts:
            desc["scripts"] = scripts
        if sounds:
            desc["sound_effects"] = dict(sounds)
        if particles:
            desc["particle_effects"] = dict(particles)
        _write(os.path.join(self.rp, "entity", f"{ident}.entity.json"),
               {"format_version": "1.10.0", "minecraft:client_entity": {"description": desc}})

        # --- render controller
        rc = {"geometry": "Geometry.default", "materials": [{"*": "Material.default"}],
              "textures": ["Texture.default"]}
        blend_bones = sorted({b for m in models for b in m.blend_bones})
        for b in blend_bones:
            rc["materials"].append({b: "Material.blend"})
        if len(models) > 1:
            rc["arrays"] = {
                "geometries": {"Array.geo": ["Geometry.default"] + [f"Geometry.k{i}" for i in range(1, len(models))]},
                "textures": {"Array.tex": ["Texture.default"] + [f"Texture.k{i}" for i in range(1, len(models))]},
            }
            rc["geometry"] = f"Array.geo[q.property('{NS}:kind')]"
            rc["textures"] = [f"Array.tex[q.property('{NS}:kind')]"]
        if skins:
            rc["arrays"] = {"textures": {"Array.skin": ["Texture.default"] + [f"Texture.s{i + 1}" for i in range(len(skins))]}}
            rc["textures"] = [f"Array.skin[q.property('{NS}:skin')]"]
        if visibility:
            rc["part_visibility"] = [{"*": True}] + list(visibility)
        _write(os.path.join(self.rp, "render_controllers", f"{ident}.render_controllers.json"),
               {"format_version": "1.8.0", "render_controllers": {f"controller.render.{NS}.{ident}": rc}})

        # --- animations
        if anims:
            _write(os.path.join(self.rp, "animations", f"{ident}.animation.json"), animations_file(anims))
        if controllers:
            _write(os.path.join(self.rp, "animation_controllers", f"{ident}.animation_controllers.json"),
                   {"format_version": "1.10.0", "animation_controllers": controllers})

        # --- behavior pack entity
        properties = {f"{NS}:state": {"type": "int", "range": [0, 31], "default": 0, "client_sync": True}}
        if len(models) > 1:
            properties[f"{NS}:kind"] = {"type": "int", "range": [0, max(1, len(models) - 1)], "default": 0,
                                        "client_sync": True}
        if skins:
            properties[f"{NS}:skin"] = {"type": "int", "range": [0, len(skins)], "default": 0, "client_sync": True}
        if size_prop:
            properties[f"{NS}:size"] = {"type": "float", "range": [0.0, 64.0], "default": 1.0, "client_sync": True}
        for k, v in (props or {}).items():
            properties[f"{NS}:{k}"] = v
        ent = {
            "format_version": ENTITY_FORMAT,
            "minecraft:entity": {
                "description": {"identifier": full, "is_spawnable": False, "is_summonable": True,
                                "is_experimental": False, "properties": properties},
                "component_groups": {f"{NS}:despawn": {"minecraft:instant_despawn": {}}},
                "components": {
                    "minecraft:type_family": {"family": ["grimoire_construct", "inanimate"] + list(families)},
                    "minecraft:collision_box": {"width": collision[0], "height": collision[1]},
                    "minecraft:health": {"value": 20, "max": 20},
                    "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
                    "minecraft:knockback_resistance": {"value": 1.0},
                    "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
                    "minecraft:fire_immune": {},
                    "minecraft:transient": {},
                    # scripts turn these actors by setting their rotation; without this the body
                    # (and so the whole model) lags behind and can face up to 75 degrees off
                    "minecraft:body_rotation_always_follows_head": {},
                    "minecraft:timer": {"looping": False, "time": float(lifetime),
                                        "time_down_event": {"event": f"{NS}:expire", "target": "self"}},
                },
                "events": {f"{NS}:expire": {"add": {"component_groups": [f"{NS}:despawn"]}}},
            },
        }
        _write(os.path.join(self.bp, "entities", f"{ident}.json"), ent)
        self.lang[f"entity.{full}.name"] = display or ident.replace("_", " ").title()
        self.actors[ident] = {
            "id": full, "states": sorted((states or {}).keys()), "kinds": len(models),
            "size_prop": size_prop, "skins": ["default"] + skins, "anims": {a.name: a.length for a in anims}, "lifetime": lifetime,
            "cubes": [m.cube_count() for m in models], "bones": [len(m.order) for m in models],
            "tex": [m.tex_size for m in models],
        }
        return full

    # ------------------------------------------------------------------ sounds / lang
    def sound(self, sid, files, category="neutral", volume=1.0, pitch=1.0, max_distance=64.0, min_distance=4.0):
        self.sound_defs[sid] = {
            "category": category, "max_distance": max_distance, "min_distance": min_distance,
            "sounds": [{"name": f"sounds/grimoire/{f}", "volume": volume, "pitch": pitch} for f in files],
        }

    def flush(self):
        with _locked():
            self._flush()

    def _flush(self):
        if self.sound_defs:
            p = os.path.join(self.rp, "sounds", "sound_definitions.json")
            data = {"format_version": "1.20.20", "sound_definitions": {}}
            if os.path.exists(p):
                with open(p) as fh:
                    data = json.load(fh)
            data["sound_definitions"].update(self.sound_defs)
            _write(p, data)
        if self.lang:
            p = os.path.join(self.rp, "texts", "en_US.lang")
            cur = {}
            if os.path.exists(p):
                for line in open(p, encoding="utf-8"):
                    if "=" in line and not line.startswith("#"):
                        k, v = line.rstrip("\n").split("=", 1)
                        cur[k] = v
            cur.update(self.lang)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                for k in sorted(cur):
                    fh.write(f"{k}={cur[k]}\n")
            _write(os.path.join(self.rp, "texts", "languages.json"), ["en_US"])
        if self.actors:
            p = os.path.join(ROOT, "tools", "_actors.json")
            _merge(p, self.actors)
