"""v1.4 ability effects for Expansion 02 (races 007-009), in the v1.3 "spectacular glow" style:
charge -> release -> impact -> linger, layered through particle events, every layer drawn from
the shared white atlas (tinted per race) so nothing new has to be loaded except seven sprites.

Identifiers are the ones the scripts and attachables spawn (src/races/{dinosauroid,bathyas,
octamyces}.ts, tools/anims/<race>.py).  Effects that read script variables (direction, length)
draw those layers themselves, because child emitters do not inherit variables.
"""
from __future__ import annotations

from vfx import atlas
from vfx import lib as L
from vfx.lib import AGE, FADE, IN_OUT, billboard, tint, tint_grad, uv_flip, uv_frame, uv_sprite

DINO = {"teal": "#3fe8c4", "amber": "#ffb347", "violet": "#b98cff", "bone": "#f1e8d4", "dust": "#a89272", "crest": "#ff6a4d"}
BATH = {"sun": "#fff6d2", "gold": "#ffd56a", "white": "#ffffff", "abyss": "#07121e", "deep": "#123047", "teal": "#4fd1c5"}
OCTA = {"violet": "#a46bff", "cyan": "#5ff5d2", "pink": "#ff7ad9", "pale": "#f4e9ff", "void": "#1a0b2e"}


def own_once(n, active=0.05):
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": active},
            "minecraft:emitter_shape_point": {}}


def marker(name, sprite, color, size=0.42, life=0.85, spin=40.0, material="particles_add", drift=0.0):
    """One sprite floating over a creature's head (status markers)."""
    comps = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": life},
             "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": spin},
             **billboard([f"{size} * {IN_OUT}", f"{size} * {IN_OUT}"], uv_sprite(sprite)),
             "minecraft:particle_appearance_tinting": tint(color, IN_OUT)}
    if drift:
        comps["minecraft:particle_motion_parametric"] = {"relative_position": [f"math.sin(v.particle_age * 360) * {drift}", 0, 0]}
    return L.effect(name, material, comps)


def line(name, color_a, color_b, n=30, width=0.08, length=0.7, life=0.7):
    """Particles strung along the script's vector (v.dx, v.dy, v.dz), shooting out from the origin."""
    comps = {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
             "minecraft:emitter_shape_point": {}, "minecraft:particle_lifetime_expression": {"max_lifetime": f"{life} + v.particle_random_2 * 0.3"},
             "minecraft:particle_motion_parametric": {"relative_position": [
                 "v.dx * v.particle_random_1 * math.min(1, v.particle_age * 8)",
                 "v.dy * v.particle_random_1 * math.min(1, v.particle_age * 8)",
                 "v.dz * v.particle_random_1 * math.min(1, v.particle_age * 8)"]},
             **billboard([f"{width} * {FADE}", f"{length} * {FADE}"], uv_sprite("streak"), "lookat_direction",
                         {"mode": "custom", "custom_direction": ["v.dx", "v.dy", "v.dz"]}),
             "minecraft:particle_appearance_tinting": tint_grad([(0.0, "#ffffff", 1.0), (0.3, color_a, 1.0), (1.0, color_b, 0.0)])}
    return L.effect(name, "particles_add", comps)


# ============================================================================= 007 the Unknown Dinosauroid

def dinosauroid():
    C = DINO
    # attachable idle effects: loose feathers, display motes
    L.motes("dino_feathers", "#ffffff", n=5, radius=0.5, rise=-0.5, life=(0.9, 1.4), size=0.16, sprite="feather",
            material="particles_blend", spin=120, speed=0.9, drag=2.0)
    L.motes("dino_display", C["teal"], n=6, radius=0.6, rise=0.6, life=(0.7, 1.1), size=0.07, sprite=["dot", "star4"])
    # Hindwing Veer: a ring of dust, feathers thrown back, teal display flecks
    L.ring("vx_veer_ring", C["dust"], size=2.6, life=0.4, material="particles_blend", alpha=0.7)
    L.motes("vx_veer_feathers", "#ffffff", n=8, radius=0.4, rise=-1.0, life=(0.7, 1.1), size=0.18, sprite="feather",
            material="particles_blend", spin=200, speed=2.2, drag=2.5)
    L.flash("vx_veer_flash", C["teal"], size=1.2, life=0.2, offset=(0, 0.6, 0))
    L.compose("veer_burst", [(0.0, "vx_veer_flash"), (0.0, "vx_veer_ring"), (0.02, "vx_veer_feathers")])
    L.motes("veer_trail", C["teal"], n=3, radius=0.35, rise=-0.2, life=(0.4, 0.7), size=0.12, sprite="feather", spin=90)
    # Misclassified: a broken cladogram over the head
    marker("misclass_mark", "clade", C["teal"], size=0.44, life=0.9, spin=0)
    # Crest of Misclassification: an impossible display - fans of colour, a two-tone shockwave
    L.flash("vx_crest_flash", C["crest"], size=2.4, life=0.3, offset=(0, 1.7, 0))
    L.ring("vx_crest_ring_g", C["teal"], size=9.0, life=0.6)
    L.ring("vx_crest_ring_v", C["amber"], size=4.0, life=0.45, ground=False, offset=(0, 1.4, 0), alpha=0.8)
    L.motes("vx_crest_fans", "#ffffff", n=8, radius=0.6, rise=0.4, life=(0.6, 0.9), size=0.34, sprite="fan", speed=2.6, drag=3.0,
            offset=(0, 1.6, 0), spin=60)
    L.motes("vx_crest_flecks", C["violet"], n=10, radius=1.2, rise=0.8, life=(0.6, 1.0), size=0.08, sprite="star4", offset=(0, 1.2, 0))
    L.compose("crest_wave", [(0.0, "vx_crest_flash"), (0.0, "vx_crest_ring_v"), (0.05, "vx_crest_ring_g"), (0.05, "vx_crest_fans"),
                             (0.1, "vx_crest_flecks")])
    # Sickle Testament: a bone-white arc (flipbook) and sparks; v.spin = 1 adds the full-circle sweep
    L.slash("vx_sickle_slash", C["bone"], size=2.6, life=0.26, rot=-25)
    L.slash("vx_sickle_slash2", C["amber"], size=2.2, life=0.24, rot=155)
    L.sparks("vx_sickle_sparks", C["bone"], n=8, speed=(2.5, 4.5), hot="#ffffff", gravity=-6)
    L.ring("vx_sickle_spin", C["amber"], size=4.2, life=0.35, offset=(0, -0.55, 0), alpha=0.8)
    spin = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.01},
            **billboard(["0.01", "0.01"], uv_sprite("dot")), "minecraft:particle_appearance_tinting": tint("#ffffff", 0.0)}
    L.compose("sickle_arc", [(0.0, "vx_sickle_slash"), (0.06, "vx_sickle_slash2"), (0.02, "vx_sickle_sparks"), (0.0, "vx_sickle_spin")], own=spin)
    # Taxonomic Error: every display at once
    L.flash("vx_err_flash", C["violet"], size=3.0, life=0.4, offset=(0, 1.2, 0))
    L.circle("vx_err_circle", C["teal"], size=5.0, life=1.2, draw=0.35, spin=40)
    L.ring("vx_err_ring", C["crest"], size=7.0, life=0.6)
    L.motes("vx_err_feathers", "#ffffff", n=12, radius=0.8, rise=0.6, life=(0.9, 1.4), size=0.18, sprite="feather", material="particles_blend",
            spin=160, speed=1.8, offset=(0, 1.0, 0))
    L.motes("vx_err_fans", C["amber"], n=6, radius=0.5, rise=0.8, life=(0.7, 1.0), size=0.3, sprite="fan", speed=2.0, offset=(0, 1.5, 0))
    L.compose("overflow_aura", [(0.0, "vx_err_flash"), (0.0, "vx_err_circle"), (0.05, "vx_err_ring"), (0.1, "vx_err_feathers"),
                                (0.15, "vx_err_fans")])


# ============================================================================= 008 Bathyas

def bathyas():
    C = BATH
    # attachable idle effects
    L.motes("sun_motes", C["gold"], n=4, radius=0.25, rise=0.5, life=(0.8, 1.3), size=0.06, sprite=["dot", "star4"])
    L.motes("abyss_bubbles", "#cfe9ff", n=4, radius=0.3, rise=1.6, life=(0.8, 1.2), size=0.07, sprite="dot", material="particles_blend",
            alpha=0.7, drag=0.6)
    L.flash("sun_glare", C["sun"], size=1.6, life=0.28)
    # Lure of the Impaled Sun: a warped, uncomfortable ring of light (two rings out of step) + a dark undertow
    L.flash("vx_lure_flash", C["white"], size=3.4, life=0.35)
    L.ring("vx_lure_ring_a", C["gold"], size=20.0, life=0.9, ground=False, alpha=0.75)
    L.ring("vx_lure_ring_b", C["sun"], size=16.0, life=0.8, ground=False, alpha=0.5, offset=(0.15, -0.1, 0))
    L.ring("vx_lure_floor", C["sun"], size=20.0, life=0.9, offset=(0, -1.15, 0), alpha=0.6)
    L.smoke("vx_lure_undertow", C["abyss"], n=5, radius=1.4, size=(1.2, 2.0), life=(0.9, 1.3), rise=-0.2, alpha=0.45, speed=0.8)
    L.compose("lure_pulse", [(0.0, "vx_lure_flash"), (0.0, "vx_lure_ring_a"), (0.07, "vx_lure_ring_b"), (0.05, "vx_lure_floor"),
                             (0.1, "vx_lure_undertow")])
    marker("sun_mark", "sunsigil", C["gold"], size=0.46, life=0.8, spin=25)
    # Goblin Maw Rush: a dark streak along the rush, then the bite: teeth, a flash, a dark splash
    line("maw_streak", C["teal"], C["abyss"], n=10, width=0.12, length=0.9, life=0.35)
    L.flash("vx_bite_flash", C["white"], size=1.4, life=0.18)
    L.motes("vx_bite_teeth", "#ffffff", n=8, radius=0.35, rise=-2.0, life=(0.35, 0.55), size=0.16, sprite="tooth", speed=2.0, spin=300)
    L.splash("vx_bite_splash", C["deep"], size=1.4, life=0.4, alpha=0.8)
    L.compose("maw_bite", [(0.0, "vx_bite_flash"), (0.0, "vx_bite_teeth"), (0.02, "vx_bite_splash")])
    # Isopod Bastion: thin lines of white-gold light escaping between plates
    seams = {**own_once(10), "minecraft:emitter_shape_sphere": {"radius": 0.7, "surface_only": True, "direction": "outwards"},
             "minecraft:particle_lifetime_expression": {"max_lifetime": "0.35 + v.particle_random_1 * 0.2"},
             "minecraft:particle_initial_speed": 1.2, "minecraft:particle_motion_dynamic": {"linear_drag_coefficient": 4.0},
             **billboard(["0.05", f"0.55 * {FADE}"], uv_sprite("streak"), "lookat_direction",
                         {"mode": "derive_from_velocity", "min_speed_threshold": 0.01}),
             "minecraft:particle_appearance_tinting": tint(C["sun"], FADE)}
    L.effect("vx_seam_lines", "particles_add", seams)
    L.flash("vx_seam_flash", C["gold"], size=1.6, life=0.22)
    L.compose("bastion_seams", [(0.0, "vx_seam_flash"), (0.0, "vx_seam_lines")])
    # Draw the Sun: the chest bursts open with light; Return: light streams back in
    L.flash("vx_draw_flash", C["white"], size=3.2, life=0.4)
    L.sparks("vx_draw_sparks", C["gold"], n=14, speed=(3.0, 6.0), hot="#ffffff", gravity=-3)
    L.ring("vx_draw_ring", C["sun"], size=4.0, life=0.4, ground=False, alpha=0.85)
    L.pillar("vx_draw_pillar", C["sun"], height=2.4, width=0.5, life=0.5, offset=(0, -1.2, 0))
    L.compose("sun_extract", [(0.0, "vx_draw_flash"), (0.0, "vx_draw_ring"), (0.02, "vx_draw_sparks"), (0.05, "vx_draw_pillar")])
    L.converge("vx_return_in", C["gold"], n=16, radius=1.4, life=0.35, size=0.07)
    L.flash("vx_return_flash", C["sun"], size=1.4, life=0.25)
    L.compose("sun_return", [(0.0, "vx_return_in"), (0.33, "vx_return_flash")])
    # the drawn sun's cuts
    L.slash("vx_sun_slash", C["gold"], size=2.0, life=0.22, rot=-35)
    L.sparks("vx_sun_slash_sparks", C["sun"], n=6, speed=(2.0, 3.5), hot="#ffffff", gravity=-4)
    L.compose("sun_slash", [(0.0, "vx_sun_slash"), (0.02, "vx_sun_slash_sparks")])
    # ---- ABYSSAL DAYBREAK
    L.converge("vx_over_in", C["sun"], n=10, radius=1.6, life=0.3, size=0.07)
    L.flash("vx_over_flash", C["gold"], size=1.8, life=0.2)
    L.compose("daybreak_overload", [(0.0, "vx_over_in"), (0.25, "vx_over_flash")])
    L.smoke("abyss_dark", C["abyss"], n=3, radius=0.8, size=(1.4, 2.4), life=(1.4, 2.0), rise=0.25, alpha=0.6, speed=0.2)
    L.pillar("vx_rise_up", C["sun"], height=16.0, width=1.8, life=1.6, alpha=0.95)
    L.pillar("vx_rise_down", C["gold"], height=6.0, width=1.4, life=1.4, alpha=0.8, offset=(0, -6.0, 0))
    L.flash("vx_rise_flash", C["white"], size=5.0, life=0.45, offset=(0, 1.2, 0))
    L.ring("vx_rise_ring", C["sun"], size=14.0, life=0.9)
    L.compose("sunrise_pillar", [(0.0, "vx_rise_flash"), (0.0, "vx_rise_up"), (0.05, "vx_rise_down"), (0.1, "vx_rise_ring")])
    lev = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 3.2},
           "minecraft:particle_motion_parametric": {"relative_position": [
               "v.dx * v.particle_age * 2.4", "math.sin(v.particle_age * 70) * 0.35", "v.dz * v.particle_age * 2.4"]},
           **billboard(["7.2", "2.4"], uv_sprite("leviathan"), "lookat_y"),
           "minecraft:particle_appearance_tinting": tint("#0a1826", f"0.62 * {IN_OUT}")}
    L.effect("leviathan", "particles_blend", lev)
    L.slash("vx_exec_a", C["sun"], size=7.0, life=0.35, rot=-20)
    L.slash("vx_exec_b", C["gold"], size=6.0, life=0.32, rot=160)
    L.ring("vx_exec_ring", C["white"], size=12.0, life=0.5, offset=(0, -0.9, 0))
    L.sparks("vx_exec_sparks", C["gold"], n=16, speed=(4.0, 8.0), hot="#ffffff", gravity=-3)
    L.compose("solar_execution", [(0.0, "vx_exec_a"), (0.06, "vx_exec_b"), (0.05, "vx_exec_ring"), (0.05, "vx_exec_sparks")])
    L.circle("vx_field_circle", C["gold"], size=12.0, life=1.6, draw=0.3, spin=12)
    L.ring("vx_field_ring", C["sun"], size=18.0, life=0.7)
    L.flash("vx_field_flash", C["white"], size=4.0, life=0.35, offset=(0, 1.0, 0))
    L.motes("vx_field_motes", C["gold"], n=16, radius=5.0, rise=1.4, life=(1.0, 1.6), size=0.1, sprite=["dot", "star4"])
    L.smoke("vx_field_dark", C["abyss"], n=4, radius=4.0, size=(1.6, 2.6), life=(1.2, 1.8), rise=0.2, alpha=0.4, speed=0.2)
    L.compose("daybreak_field", [(0.0, "vx_field_flash"), (0.0, "vx_field_circle"), (0.0, "vx_field_ring"), (0.1, "vx_field_motes"),
                                 (0.1, "vx_field_dark")])


# ============================================================================= 009 Octamyces Undecimus

def octamyces():
    C = OCTA
    # attachable idle effects (iridescent, never strobing: three hues per effect, soft fades)
    L.motes("geo_spores", "#ffffff", n=6, radius=0.5, rise=0.25, life=(1.2, 1.8), size=0.1, sprite="polyspore", spin=50, speed=0.4)
    L.motes("parallax_motes", C["cyan"], n=4, radius=0.4, rise=0.3, life=(0.7, 1.0), size=0.06, sprite="dot")
    echo = {**own_once(3), "minecraft:emitter_shape_box": {"half_dimensions": [0.05, 0.6, 0.05]},
            "minecraft:particle_lifetime_expression": {"max_lifetime": "0.6 + v.particle_random_1 * 0.2"},
            "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 60", "rotation_rate": 0},
            "minecraft:particle_motion_parametric": {"relative_position": ["(v.particle_random_3 - 0.5) * 0.3 * v.particle_age", 0, 0]},
            **billboard([f"0.7 * {FADE}", f"0.7 * {FADE}"], uv_sprite("hexagon")),
            "minecraft:particle_appearance_tinting": tint_grad([(0.0, C["cyan"], 0.55), (0.5, C["violet"], 0.4), (1.0, C["pink"], 0.0)])}
    L.effect("parallax_echo", "particles_add", echo)
    # Parallax Sporeveil: a controlled field of geometric spores
    L.flash("vx_veil_flash", C["cyan"], size=1.6, life=0.25)
    L.ring("vx_veil_ring", C["violet"], size=12.0, life=0.7, offset=(0, -0.95, 0), alpha=0.8)
    L.motes("vx_veil_spores", "#ffffff", n=24, radius=0.6, rise=0.05, life=(1.4, 2.0), size=0.13, sprite="polyspore", spin=70,
            speed=3.2, drag=2.4)
    L.smoke("vx_veil_haze", C["pink"], n=4, radius=1.6, size=(1.2, 2.0), life=(1.0, 1.4), rise=0.1, alpha=0.25, material="particles_add")
    L.compose("sporeveil_cloud", [(0.0, "vx_veil_flash"), (0.0, "vx_veil_ring"), (0.05, "vx_veil_spores"), (0.1, "vx_veil_haze")])
    marker("parallax_mark", "polyspore", C["pink"], size=0.36, life=0.6, spin=-60, drift=0.25)
    marker("observed_mark", "eye", C["cyan"], size=0.5, life=0.7, spin=15)
    # The Eye That Records / The Eleventh Frame
    L.flash("vx_point_flash", C["cyan"], size=0.7, life=0.2)
    pt = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 2.6},
          "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 45},
          **billboard([f"0.55 * {IN_OUT}", f"0.55 * {IN_OUT}"], uv_sprite("hexagon")),
          "minecraft:particle_appearance_tinting": tint_grad([(0.0, C["pale"], 0.9), (0.5, C["cyan"], 0.8), (1.0, C["violet"], 0.0)])}
    L.compose("record_point", [(0.0, "vx_point_flash")], own=pt)
    ringp = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
             "minecraft:particle_initial_spin": {"rotation": "v.particle_random_1 * 360", "rotation_rate": 90},
             **billboard([f"0.4 + {AGE} * 2.2", f"0.4 + {AGE} * 2.2"], uv_sprite("glyphring")),
             "minecraft:particle_appearance_tinting": tint_grad([(0.0, C["pale"], 0.9), (0.6, C["violet"], 0.7), (1.0, C["pink"], 0.0)])}
    L.effect("vx_frame_glyph", "particles_add", ringp)
    L.flash("vx_frame_flash", C["violet"], size=1.0, life=0.2)
    L.compose("frame_ring", [(0.0, "vx_frame_flash"), (0.0, "vx_frame_glyph")])
    line("frame_thread", C["cyan"], C["violet"], n=26, width=0.06, length=0.6, life=0.9)
    L.flash("vx_strike_flash", C["pink"], size=1.4, life=0.22)
    L.sparks("vx_strike_sparks", C["cyan"], n=8, speed=(2.0, 4.0), hot="#ffffff", gravity=-4)
    L.motes("vx_strike_polys", "#ffffff", n=5, radius=0.3, rise=0.3, life=(0.4, 0.6), size=0.16, sprite="polyspore", speed=2.0, spin=200)
    L.compose("frame_strike", [(0.0, "vx_strike_flash"), (0.0, "vx_strike_sparks"), (0.02, "vx_strike_polys")])
    L.converge("vx_collapse_in", C["violet"], n=18, radius=2.2, life=0.35, size=0.08)
    L.flash("vx_collapse_flash", C["cyan"], size=1.6, life=0.25)
    L.compose("frame_collapse", [(0.0, "vx_collapse_in"), (0.33, "vx_collapse_flash")])
    # Hyphal Offset: a rift where the body was and where it is
    L.flash("vx_rift_flash", C["violet"], size=1.8, life=0.25)
    L.ring("vx_rift_ring", C["cyan"], size=2.6, life=0.35, ground=False, alpha=0.8)
    rift = {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
            **billboard(["1.4", "2.4"], uv_flip("crack"), "lookat_y"),
            "minecraft:particle_appearance_tinting": tint(C["pink"], FADE)}
    L.effect("vx_rift_tear", "particles_add", rift)
    L.compose("offset_rift", [(0.0, "vx_rift_flash"), (0.0, "vx_rift_tear"), (0.02, "vx_rift_ring")])


def build():
    dinosauroid()
    bathyas()
    octamyces()
