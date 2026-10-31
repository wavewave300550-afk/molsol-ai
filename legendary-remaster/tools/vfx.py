"""
vfx - client-side visual effects for the remastered legends.

Two kinds of effects, both played by the client (no script cost, perfectly attached to the models):
  * AURAS  - looping emitters bound to model locators, switched by an animation controller
             (`ctrl_fx`) per phase: hungry smoke from Taotie's maw, venom dripping from Nidhogg's
             jaws, Hanuman's burning tail, Alicorn's aurora mane, Tenko's foxfire tail tips, the
             Word's holy motes...
  * BURSTS - one-shot emitters keyed into the act animations at their impact marks: ground dust and
             debris on slams, slash flashes on claws and blades, roar vapour, wingbeat feathers,
             fire / holy / venom bursts.
Particles reuse the pack atlas textures/particle/legends_fx (128x128, 32px cells).
"""
import json
import os

ATLAS = "textures/particle/legends_fx"
UV = {"glow": (0, 0), "star": (32, 0), "ring": (64, 0), "disc": (96, 0), "flame": (64, 32), "diamond": (96, 32),
      "streak": (0, 32), "slash": (32, 32), "leaf": (0, 64), "rune": (32, 64), "smoke": (64, 64), "shard": (96, 64), "twinkle": (0, 96), "crescent": (32, 96),
      "drip": (64, 96), "spiral": (96, 96), "feather": (96, 32)}
AGE = "(variable.particle_age / variable.particle_lifetime)"


def _lerp_color(c0, c1):
    return [f"{c0[i]} + ({c1[i]} - {c0[i]}) * {AGE}" for i in range(4)]


def particle(ident, *, tex="glow", material="particles_add", loop=None, burst=None, shape=("sphere", 0.3, "outwards"),
             speed="0", accel=(0, 0, 0), drag=0.0, life="1.0", size=(0.4, 0.1), c0=(1, 1, 1, 1), c1=(1, 1, 1, 0),
             spin=False, facing="lookat_xyz", local=False, rand_color=None):
    comps = {}
    if loop:
        rate, mx = loop
        comps["minecraft:emitter_lifetime_looping"] = {"active_time": 1}
        comps["minecraft:emitter_rate_steady"] = {"spawn_rate": rate, "max_particles": mx}
    else:
        comps["minecraft:emitter_lifetime_once"] = {"active_time": 0.05}
        comps["minecraft:emitter_rate_instant"] = {"num_particles": burst}
    kind = shape[0]
    if kind == "sphere":
        comps["minecraft:emitter_shape_sphere"] = {"radius": shape[1], "surface_only": len(shape) > 3 and shape[3], "direction": shape[2]}
    elif kind == "disc":
        comps["minecraft:emitter_shape_disc"] = {"radius": shape[1], "plane_normal": "y", "surface_only": len(shape) > 3 and shape[3], "direction": shape[2]}
    elif kind == "box":
        comps["minecraft:emitter_shape_box"] = {"half_dimensions": list(shape[1]), "direction": shape[2]}
    else:
        comps["minecraft:emitter_shape_point"] = {"direction": list(shape[1])}
    if local:
        comps["minecraft:emitter_local_space"] = {"position": True, "rotation": False}
    comps["minecraft:particle_lifetime_expression"] = {"max_lifetime": life}
    comps["minecraft:particle_initial_speed"] = speed
    comps["minecraft:particle_motion_dynamic"] = {"linear_acceleration": list(accel), "linear_drag_coefficient": drag}
    if spin:
        comps["minecraft:particle_initial_spin"] = {"rotation": "variable.particle_random_2 * 360", "rotation_rate": "(variable.particle_random_3 - 0.5) * 360"}
    if rand_color:
        # pick between up to three colours with particle_random_1, fade alpha over life
        a, b, c = rand_color
        r = "variable.particle_random_1"
        col = [f"({r} < 0.33 ? {a[i]} : ({r} < 0.66 ? {b[i]} : {c[i]}))" for i in range(3)] + [f"{c0[3]} + ({c1[3]} - {c0[3]}) * {AGE}"]
    else:
        col = _lerp_color(c0, c1)
    comps["minecraft:particle_appearance_tinting"] = {"color": col}
    u, v = UV[tex]
    s0, s1 = size
    sz = f"{s0} + ({s1} - {s0}) * {AGE}"
    comps["minecraft:particle_appearance_billboard"] = {"facing_camera_mode": facing, "size": [sz, sz],
                                                         "uv": {"texture_width": 128, "texture_height": 128, "uv": [u, v], "uv_size": [32, 32]}}
    return {"format_version": "1.10.0", "particle_effect": {
        "description": {"identifier": ident, "basic_render_parameters": {"material": material, "texture": ATLAS}},
        "components": comps}}


RISE = (0, 1.2, 0)
P = {}


def _def(name, **kw):
    P[f"legends:fx_{name}"] = particle(f"legends:fx_{name}", **kw)


# ---------------------------------------------------------------- auras (looping)
_def("hunger_smoke", tex="smoke", material="particles_blend", loop=(12, 40), shape=("sphere", 0.7, "outwards"), speed="0.5",
     accel=(0, 0.8, 0), drag=0.6, life="1.3 + variable.particle_random_1 * 0.6", size=(0.5, 1.8), c0=(0.42, 0.22, 0.55, 0.75), c1=(0.12, 0.06, 0.18, 0.0), spin=True)
_def("maw_embers", tex="twinkle", loop=(16, 40), shape=("sphere", 0.6, "outwards"), speed="0.8", accel=(0, 1.8, 0), drag=0.4,
     life="0.7 + variable.particle_random_1 * 0.4", size=(0.32, 0.06), c0=(1.0, 0.75, 0.3, 1.0), c1=(1.0, 0.25, 0.05, 0.0))
_def("eye_fire", tex="glow", loop=(10, 24), shape=("sphere", 0.25, "outwards"), speed="0.4", accel=(0, 1.0, 0),
     life="0.5", size=(0.8, 0.15), c0=(1.0, 0.85, 0.4, 0.9), c1=(1.0, 0.3, 0.05, 0.0))
_def("bronze_steam", tex="smoke", material="particles_blend", loop=(7, 30), shape=("box", (1.6, 0.3, 2.0), [0, 1, 0]), speed="0.8",
     accel=(0, 0.9, 0), drag=0.5, life="1.8", size=(0.9, 2.8), c0=(0.55, 0.45, 0.4, 0.5), c1=(0.3, 0.25, 0.25, 0.0), spin=True)
_def("vortex_swirl", tex="smoke", material="particles_blend", loop=(26, 70), shape=("sphere", 2.2, "inwards", True), speed="1.6",
     accel=(0, 1.4, 0), drag=0.8, life="1.0", size=(0.9, 0.2), c0=(0.55, 0.3, 0.75, 0.8), c1=(0.9, 0.5, 1.0, 0.0), spin=True)
_def("venom_drip", tex="drip", material="particles_blend", loop=(6, 16), shape=("sphere", 0.35, "outwards"), speed="0.1",
     accel=(0, -9.0, 0), life="0.9", size=(0.3, 0.22), c0=(0.55, 1.0, 0.3, 1.0), c1=(0.3, 0.8, 0.15, 0.6))
_def("venom_mist", tex="glow", loop=(16, 50), shape=("box", (1.4, 0.5, 2.6), [0, 1, 0]), speed="0.5", accel=(0, 0.8, 0), drag=0.6,
     life="1.2", size=(0.9, 0.0), c0=(0.6, 1.0, 0.35, 0.7), c1=(0.2, 0.8, 0.1, 0.0))
_def("wind_feathers", tex="feather", material="particles_blend", loop=(3, 10), shape=("sphere", 1.6, "outwards"), speed="0.4",
     accel=(0.3, -0.25, 0), drag=0.4, life="2.4", size=(0.42, 0.36), c0=(1.0, 1.0, 1.0, 0.95), c1=(0.85, 1.0, 0.95, 0.0), spin=True)
_def("tail_fire", tex="flame", loop=(34, 50), shape=("sphere", 0.45, "outwards"), speed="0.6", accel=(0, 2.6, 0), drag=0.6,
     life="0.55 + variable.particle_random_1 * 0.25", size=(1.1, 0.2), c0=(1.0, 0.92, 0.5, 1.0), c1=(1.0, 0.25, 0.05, 0.0), spin=True)
_def("tail_embers", tex="twinkle", loop=(12, 30), shape=("sphere", 0.5, "outwards"), speed="1.2", accel=(0, 2.0, 0), drag=0.5,
     life="0.9", size=(0.25, 0.05), c0=(1.0, 0.8, 0.3, 1.0), c1=(1.0, 0.3, 0.1, 0.0))
_def("divine_stars", tex="twinkle", loop=(10, 30), shape=("sphere", 2.4, "outwards", True), speed="0.2", accel=(0, 0.4, 0),
     life="1.3", size=(0.45, 0.0), c0=(1.0, 0.95, 0.6, 1.0), c1=(1.0, 0.8, 0.3, 0.0))
_def("aurora_sparkle", tex="twinkle", loop=(16, 40), shape=("sphere", 0.7, "outwards"), speed="0.3", accel=(0, 0.5, 0), drag=0.3,
     life="1.2 + variable.particle_random_2 * 0.5", size=(0.38, 0.0), c0=(1, 1, 1, 1.0), c1=(1, 1, 1, 0.0),
     rand_color=((1.0, 0.6, 0.9), (0.7, 0.55, 1.0), (0.5, 0.9, 1.0)))
_def("horn_glow", tex="glow", loop=(12, 20), shape=("sphere", 0.2, "outwards"), speed="0.3", life="0.45", size=(0.9, 0.1),
     c0=(1.0, 1.0, 0.95, 0.9), c1=(1.0, 0.9, 0.6, 0.0))
_def("crown_stars", tex="star", loop=(6, 14), shape=("disc", 1.0, "outwards", True), speed="0.2", accel=(0, 0.6, 0),
     life="1.0", size=(0.6, 0.0), c0=(1.0, 0.95, 0.7, 1.0), c1=(1.0, 0.8, 0.3, 0.0), spin=True)
_def("foxfire_tip", tex="flame", loop=(6, 10), shape=("sphere", 0.25, "outwards"), speed="0.4", accel=(0, 1.8, 0), drag=0.5,
     life="0.6 + variable.particle_random_1 * 0.3", size=(0.75, 0.1), c0=(0.75, 0.9, 1.0, 1.0), c1=(0.2, 0.45, 1.0, 0.0), spin=True)
_def("moon_dust", tex="twinkle", loop=(10, 30), shape=("disc", 1.4, "outwards", True), speed="0.2", accel=(0, -0.2, 0),
     life="1.4", size=(0.35, 0.0), c0=(0.9, 0.93, 1.0, 1.0), c1=(0.6, 0.7, 1.0, 0.0))
_def("pearl_glow", tex="glow", loop=(8, 16), shape=("sphere", 0.3, "outwards"), speed="0.3", life="0.6", size=(0.8, 0.1),
     c0=(0.8, 0.95, 1.0, 0.9), c1=(0.3, 0.6, 1.0, 0.0))
_def("holy_motes", tex="glow", loop=(18, 50), shape=("sphere", 3.4, "inwards", True), speed="1.4", drag=0.5,
     life="1.5", size=(0.5, 0.05), c0=(1.0, 0.95, 0.7, 0.0), c1=(1.0, 1.0, 1.0, 1.0))
_def("rune_orbit", tex="rune", loop=(4, 14), shape=("sphere", 5.0, "outwards", True), speed="0.15", accel=(0, 0.3, 0),
     life="2.2", size=(0.9, 0.5), c0=(1.0, 0.85, 0.4, 1.0), c1=(1.0, 0.95, 0.7, 0.0), spin=True)
_def("seraph_fire", tex="flame", loop=(22, 40), shape=("sphere", 1.3, "outwards"), speed="0.5", accel=(0, 2.0, 0), drag=0.5,
     life="0.6", size=(0.9, 0.1), c0=(1.0, 0.95, 0.6, 1.0), c1=(1.0, 0.3, 0.05, 0.0), spin=True)
_def("sword_fire", tex="flame", loop=(18, 30), shape=("box", (0.15, 1.6, 0.15), [0, 1, 0]), speed="0.5", accel=(0, 1.8, 0),
     life="0.45", size=(0.6, 0.1), c0=(1.0, 0.9, 0.5, 1.0), c1=(1.0, 0.3, 0.05, 0.0), spin=True)
_def("ophan_sparks", tex="twinkle", loop=(14, 30), shape=("sphere", 1.0, "outwards"), speed="2.2", drag=1.5, life="0.6",
     size=(0.32, 0.0), c0=(1.0, 0.75, 0.3, 1.0), c1=(0.4, 0.9, 0.8, 0.0))

# ---------------------------------------------------------------- bursts (one-shot, keyed into acts)
_def("dust", tex="smoke", material="particles_blend", burst=26, shape=("disc", 1.2, "outwards"), speed="5.5", accel=(0, 0.6, 0), drag=3.0,
     life="1.0 + variable.particle_random_1 * 0.5", size=(1.0, 2.8), c0=(0.62, 0.55, 0.45, 0.85), c1=(0.45, 0.4, 0.35, 0.0), spin=True)
_def("debris", tex="shard", material="particles_blend", burst=14, shape=("sphere", 0.6, "outwards"), speed="6", accel=(0, -16, 0), drag=0.6,
     life="0.9", size=(0.45, 0.35), c0=(0.35, 0.3, 0.25, 1.0), c1=(0.25, 0.2, 0.18, 1.0), spin=True)
_def("flash", tex="glow", burst=1, shape=("point", (0, 0, 0)), life="0.22", size=(2.6, 6.0), c0=(1.0, 1.0, 0.9, 1.0), c1=(1.0, 0.8, 0.4, 0.0))
_def("slash_bronze", tex="slash", burst=1, shape=("point", (0, 0, 0)), life="0.22", size=(2.4, 4.2), c0=(1.0, 0.85, 0.5, 1.0), c1=(1.0, 0.5, 0.2, 0.0), spin=True)
_def("slash_venom", tex="slash", burst=1, shape=("point", (0, 0, 0)), life="0.22", size=(2.4, 4.4), c0=(0.7, 1.0, 0.4, 1.0), c1=(0.2, 0.8, 0.1, 0.0), spin=True)
_def("slash_wind", tex="slash", burst=2, shape=("point", (0, 0, 0)), life="0.25", size=(2.0, 4.0), c0=(0.9, 1.0, 1.0, 1.0), c1=(0.6, 0.9, 1.0, 0.0), spin=True)
_def("slash_gold", tex="slash", burst=1, shape=("point", (0, 0, 0)), life="0.25", size=(2.4, 4.8), c0=(1.0, 0.95, 0.6, 1.0), c1=(1.0, 0.7, 0.2, 0.0), spin=True)
_def("slash_fox", tex="slash", burst=2, shape=("point", (0, 0, 0)), life="0.25", size=(2.0, 4.0), c0=(0.7, 0.85, 1.0, 1.0), c1=(1.0, 0.4, 0.3, 0.0), spin=True)
_def("roar_vapor", tex="smoke", material="particles_blend", burst=30, shape=("sphere", 0.5, "outwards"), speed="7", drag=4.0,
     life="0.9", size=(0.6, 2.2), c0=(0.9, 0.9, 0.95, 0.6), c1=(0.7, 0.7, 0.8, 0.0), spin=True)
_def("hunger_roar", tex="smoke", material="particles_blend", burst=30, shape=("sphere", 0.6, "outwards"), speed="7", drag=4.0,
     life="1.0", size=(0.7, 2.4), c0=(0.55, 0.3, 0.7, 0.75), c1=(0.2, 0.1, 0.3, 0.0), spin=True)
_def("venom_spray", tex="glow", burst=22, shape=("sphere", 0.4, "outwards"), speed="6", accel=(0, -4, 0), drag=2.0,
     life="0.7", size=(0.7, 0.2), c0=(0.65, 1.0, 0.35, 1.0), c1=(0.6, 0.9, 1.0, 0.0))
_def("feather_burst", tex="feather", material="particles_blend", burst=16, shape=("sphere", 1.0, "outwards"), speed="5", accel=(0, -1.2, 0), drag=2.2,
     life="1.6", size=(0.45, 0.4), c0=(1.0, 1.0, 1.0, 1.0), c1=(1.0, 0.95, 0.85, 0.0), spin=True)
_def("fire_burst", tex="flame", burst=26, shape=("sphere", 0.6, "outwards"), speed="5", accel=(0, 2.0, 0), drag=2.5,
     life="0.7", size=(1.1, 0.2), c0=(1.0, 0.92, 0.5, 1.0), c1=(1.0, 0.25, 0.05, 0.0), spin=True)
_def("holy_burst", tex="glow", burst=26, shape=("sphere", 0.8, "outwards"), speed="6", drag=2.5, life="0.8",
     size=(0.9, 0.1), c0=(1.0, 1.0, 0.85, 1.0), c1=(1.0, 0.8, 0.35, 0.0))
_def("star_burst", tex="star", burst=18, shape=("sphere", 0.6, "outwards"), speed="6", drag=2.5, life="0.9",
     size=(0.8, 0.0), c0=(1.0, 0.97, 0.75, 1.0), c1=(1.0, 0.85, 0.4, 0.0), spin=True)
_def("aurora_burst", tex="twinkle", burst=30, shape=("sphere", 0.8, "outwards"), speed="6", drag=2.0, life="1.1",
     size=(0.6, 0.0), c0=(1, 1, 1, 1), c1=(1, 1, 1, 0), rand_color=((1.0, 0.6, 0.9), (0.7, 0.55, 1.0), (0.5, 0.9, 1.0)))
_def("fox_burst", tex="flame", burst=24, shape=("sphere", 0.6, "outwards"), speed="5", accel=(0, 1.5, 0), drag=2.5, life="0.7",
     size=(0.9, 0.1), c0=(0.75, 0.9, 1.0, 1.0), c1=(0.25, 0.45, 1.0, 0.0), spin=True)
_def("bronze_sparks", tex="twinkle", burst=24, shape=("sphere", 0.5, "outwards"), speed="8", accel=(0, -10, 0), drag=1.0,
     life="0.6", size=(0.3, 0.05), c0=(1.0, 0.85, 0.45, 1.0), c1=(1.0, 0.45, 0.15, 0.0))
_def("vanish", tex="glow", burst=40, shape=("sphere", 2.0, "outwards"), speed="3", accel=(0, 3, 0), drag=1.0, life="1.6",
     size=(1.2, 0.0), c0=(1.0, 0.97, 0.85, 1.0), c1=(1.0, 0.85, 0.5, 0.0))


def write_particles(rp):
    d = os.path.join(rp, "particles", "legends")
    os.makedirs(d, exist_ok=True)
    for ident, js in P.items():
        with open(os.path.join(d, ident.split(":")[1] + ".json"), "w") as f:
            json.dump(js, f, separators=(",", ":"))
    return len(P)


def short(ident):
    return ident.split(":")[1].replace("fx_", "")


def fx_controller(key, auras, death_id=None):
    """Animation controller switching looping auras by phase (and a death state).
    auras: {"p1": [(effect, locator)], "p2": [...], "p3": [...]} - effects are particle ids."""
    def st(name, cond_list, effects):
        s = {"transitions": [{k: c} for k, c in cond_list]}
        if effects:
            s["particle_effects"] = [{"effect": short(e), "locator": loc} for e, loc in effects]
        return s
    if "all" in auras:      # followers: always-on aura, death state
        on = {"particle_effects": [{"effect": short(e), "locator": loc} for e, loc in auras["all"]],
              "transitions": ([{"dying": f"variable.act == {death_id}"}] if death_id else [])}
        states = {"on": on}
        if death_id:
            states["dying"] = st("dying", [("on", f"variable.act != {death_id}")], auras.get("dying", []))
        return {"initial_state": "on", "states": states}
    to = lambda: [("p1", "variable.ph == 1 && variable.act != {d}".format(d=death_id or -1)),
                  ("p2", "variable.ph == 2 && variable.act != {d}".format(d=death_id or -1)),
                  ("p3", "variable.ph >= 3 && variable.act != {d}".format(d=death_id or -1))]
    states = {"none": st("none", to(), [])}
    for ph in ("p1", "p2", "p3"):
        conds = [(k, c) for k, c in to() if k != ph]
        if death_id:
            conds.append(("dying", f"variable.act == {death_id}"))
        conds.append(("none", "variable.ph == 0"))
        states[ph] = st(ph, conds, auras.get(ph, []))
    if death_id:
        states["dying"] = st("dying", [("none", f"variable.act != {death_id}")], auras.get("dying", []))
    return {"initial_state": "none", "states": states}


def used_effects(auras, act_fx):
    ids = set()
    for lst in auras.values():
        ids |= {e for e, _ in lst}
    for lst in act_fx.values():
        ids |= {e for _, e, _ in lst}
    return {short(i): i for i in sorted(ids)}


def add_act_fx(anim_json, events):
    """events: [(tick, effect_id, locator)] -> animation particle_effects timeline."""
    tl = {}
    for tick, eff, loc in events:
        k = f"{tick / 20.0:.2f}"
        tl.setdefault(k, []).append({"effect": short(eff), "locator": loc})
    if tl:
        anim_json["particle_effects"] = tl
    return anim_json
