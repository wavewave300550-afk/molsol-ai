"""v1.3 ability effects for all six races ("spectacular glow": charge -> release -> impact -> linger).

Each script-spawned identifier stays the same; its JSON becomes an entry effect that fires
layers (flash, shockwave, magic circle, sparks, debris, pillars, motes...) on a timeline.
Entry effects that read variables the script passes (direction, length, colour, size...)
draw those layers themselves, because child emitters do not inherit the variables.
"""
from __future__ import annotations

import fx_ex
from vfx import atlas
from vfx import lib as L
from vfx.lib import AGE, FADE, IN_OUT, billboard, tint, tint_grad, uv_flip, uv_frame, uv_sprite

# ----------------------------------------------------------------------------- palettes
SAL = {"leaf": "#5dff9a", "deep": "#1fae5a", "bloom": "#ff5fa8", "dew": "#9ff6ff", "sap": "#d7ff6a", "soil": "#7a5a3a"}
GOL = {"amber": "#ffb547", "gold": "#ffd77a", "ember": "#ff7a2a", "stone": "#8a7f72", "dust": "#c2b29c"}
JAK = {"crimson": "#ff2a4f", "moon": "#e4ebff", "silver": "#c9d4ff", "violet": "#a07bff", "blood": "#a3132c"}
XEN = {"violet": "#b89cff", "lilac": "#e6dcff", "ivory": "#f1ead9", "nerve": "#8f6bff", "fluid": "#d6e8c6"}
FSM = {"gold": "#ffd36a", "sauce": "#d93a2b", "sauce_dk": "#8a1a12", "steam": "#fff6e8", "noodle": "#f2ca68", "holy": "#fff1b0"}
NUR = {"gold": "#ffd677", "warm": "#ffe9b0", "verm": "#e0442c", "petal": "#ffc4d6", "shadow": "#140c10"}
DUST = "#cbb9a2"

EX = fx_ex.TEX


def exuv(name):
    return fx_ex._uv(name)


def _strip(d):
    return {k: v for k, v in d.items()}


def own_once(n, active=0.05):
    return {"minecraft:emitter_rate_instant": {"num_particles": n}, "minecraft:emitter_lifetime_once": {"active_time": active},
            "minecraft:emitter_shape_point": {}}


# ============================================================================= shared
def shared():
    # rite of transformation: a magic circle in the race colour, a pillar of light, falling sparks
    L.flash("vx_rite_flash", "#ffffff", size=3.2, life=0.4, offset=(0, 1.1, 0))
    L.pillar("vx_rite_pillar", "#fff4d6", height=6.0, width=1.1, life=1.1)
    L.ring("vx_rite_ring", "#fff4d6", size=7.0, life=0.8)
    L.motes("vx_rite_fall", "#ffffff", n=24, radius=1.6, rise=-1.2, life=(0.9, 1.5), size=0.1, sprite="star4", offset=(0, 3.0, 0), spin=90)
    rite_own = {"minecraft:emitter_rate_steady": {"spawn_rate": 30, "max_particles": 40}, "minecraft:emitter_lifetime_once": {"active_time": 1.4},
                "minecraft:emitter_shape_disc": {"radius": 1.3, "plane_normal": "y"}, "minecraft:particle_initial_speed": 0,
                "minecraft:particle_lifetime_expression": {"max_lifetime": 1.2},
                "minecraft:particle_motion_dynamic": {"linear_acceleration": [0, 2.2, 0], "linear_drag_coefficient": 0.8},
                **billboard([f"0.12 * {IN_OUT}", f"0.12 * {IN_OUT}"], uv_sprite("dot")),
                "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", f"{IN_OUT}"]}}
    L.effect("vx_rite_circle", "particles_add", {**own_once(1), "minecraft:particle_lifetime_expression": {"max_lifetime": 1.8},
                                                 "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 30},
                                                 **billboard([4.2, 4.2], uv_flip("circle", fps=atlas.FRAMES / 0.5), "emitter_transform_xz"),
                                                 "minecraft:particle_appearance_tinting": tint("#ffffff", f"0.85 * {FADE}")})
    L.compose("rite_aura", [(0.0, "vx_rite_circle"), (0.5, "vx_rite_flash"), (0.5, "vx_rite_ring"), (0.55, "vx_rite_pillar"),
                            (0.7, "vx_rite_fall")], own=rite_own)

    # the aim reticle (private, re-spawned every 0.4 s: lives 0.45 s so it never blinks)
    L.effect("target_reticle", "particles_add", {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.45},
                                                 "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 90},
                                                 **billboard(["0.7", "0.7"], uv_sprite("glyphring")),
                                                 "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", "0.95"]}})

    # generic footfall / landing dust (golem steps, xenentoma glide, heavy landings)
    L.smoke("step_dust", DUST, n=4, radius=0.25, size=(0.3, 0.7), life=(0.5, 0.8), rise=0.3, alpha=0.5, speed=0.9)
    L.smoke("vx_land_puffs", DUST, n=7, radius=0.4, size=(0.4, 1.0), life=(0.6, 1.0), rise=0.3, alpha=0.55, speed=1.6)
    L.ring("vx_land_ring", "#e8dcc8", size=2.6, life=0.45, alpha=0.6, material="particles_blend")
    L.compose("land_dust", [(0.0, "vx_land_puffs"), (0.0, "vx_land_ring")])

    # impact on the ground (golem slam / fall crack, jackalope thump)
    L.ring("vx_impact_ring", "#fff1d8", size=4.2, life=0.5, alpha=0.9)
    L.flash("vx_impact_flash", "#fff1d8", size=1.8, life=0.25, offset=(0, 0.3, 0))
    L.debris("vx_impact_debris", "#9a8c7c", n=8, speed=(2.5, 4.0))
    L.smoke("vx_impact_dust", DUST, n=5, radius=0.5, size=(0.6, 1.3), life=(0.6, 1.0), rise=0.2, alpha=0.5, speed=1.4)
    L.compose("impact_ring", [(0.0, "vx_impact_flash"), (0.0, "vx_impact_ring"), (0.0, "vx_impact_debris"), (0.05, "vx_impact_dust")])


# ============================================================================= 001 salamander
def salamander():
    C = SAL
    # Sundew Snare: spores gather at the hand, a glowing nectar filament shoots out along (dx,dy,dz,len)
    L.converge("vx_snare_charge", C["leaf"], n=12, radius=0.9, life=0.25, size=0.05)
    L.flash("vx_snare_flash", C["bloom"], size=0.9, life=0.22)
    strand = {"minecraft:emitter_rate_instant": {"num_particles": 30}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
              "minecraft:emitter_shape_point": {}, "minecraft:particle_lifetime_expression": {"max_lifetime": "0.7 + v.particle_random_2 * 0.4"},
              "minecraft:particle_motion_parametric": {"relative_position": [
                  "v.dx * v.len * v.particle_random_1 * math.min(1, v.particle_age * 8)",
                  "v.dy * v.len * v.particle_random_1 * math.min(1, v.particle_age * 8) + math.sin(v.particle_random_1 * 180) * 0.2 - v.particle_age * 0.4 * v.particle_random_1",
                  "v.dz * v.len * v.particle_random_1 * math.min(1, v.particle_age * 8)"]},
              **billboard([f"0.09 * {FADE}", f"0.75 * {FADE}"], uv_sprite("streak"), "lookat_direction",
                          {"mode": "custom", "custom_direction": ["v.dx", "v.dy", "v.dz"]}),
              "minecraft:particle_appearance_tinting": tint_grad([(0.0, "#ffffff", 1.0), (0.3, C["bloom"], 1.0), (1.0, C["leaf"], 0.0)])}
    strand["minecraft:emitter_rate_instant"] = {"num_particles": 40}
    L.compose("snare_strand", [(0.0, "vx_snare_charge"), (0.0, "vx_snare_flash")], own=strand)
    # Ensnared: a sundew blossom pulsing on the ground under the target, nectar dew rising
    L.ring("vx_ens_ring", C["bloom"], size=2.2, life=0.6, alpha=0.9)
    L.effect("vx_ens_petals", "particles_add", {**own_once(6), "minecraft:emitter_shape_disc": {"radius": 0.55, "plane_normal": "y", "surface_only": True},
                                                "minecraft:particle_lifetime_expression": {"max_lifetime": 0.55},
                                                "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 40},
                                                **billboard([f"0.35 * {IN_OUT}", f"0.35 * {IN_OUT}"], uv_sprite("petal"), "emitter_transform_xz"),
                                                "minecraft:particle_appearance_tinting": tint(C["bloom"], 0.9)})
    L.motes("vx_ens_dew", C["bloom"], n=4, radius=0.45, rise=0.8, life=(0.5, 0.8), size=0.09, sprite="droplet")
    L.compose("ensnared", [(0.0, "vx_ens_ring"), (0.0, "vx_ens_petals"), (0.0, "vx_ens_dew")])
    # Carnivorous Embrace: two green jaws snap shut, a pink burst, leaves and nectar
    L.slash("vx_trap_jaw_a", C["leaf"], size=2.2, life=0.28, rot=-30)
    L.slash("vx_trap_jaw_b", C["leaf"], size=2.2, life=0.28, rot=150)
    L.flash("vx_trap_flash", C["bloom"], size=1.9, life=0.3)
    L.sparks("vx_trap_sparks", C["bloom"], n=12, speed=(2.5, 4.5), hot="#fff0f8")
    L.debris("vx_trap_leaves", C["deep"], n=7, speed=(1.5, 3.0), sprite="leaf", size=0.18, gravity=-5, bounce=0.1, lit=False)
    L.compose("trap_snap", [(0.0, "vx_trap_jaw_a"), (0.0, "vx_trap_jaw_b"), (0.06, "vx_trap_flash"), (0.06, "vx_trap_sparks"), (0.08, "vx_trap_leaves")])
    # life stream / photosynthesis: leaves and little hearts drifting up
    L.motes("heal_leaf", C["leaf"], n=5, radius=0.5, rise=0.9, life=(0.9, 1.3), size=0.14, sprite=["petal", "leaf", "droplet"], spin=60)
    # Root Metamorphosis: roots crack open the ground in a ring, sap rises in columns
    L.crack("vx_root_crack", C["sap"], size=3.2, life=1.0)
    L.ring("vx_root_ring", C["leaf"], size=3.6, life=0.6)
    L.debris("vx_root_soil", C["soil"], n=10, speed=(2.0, 3.5))
    L.pillar("vx_root_sap", C["sap"], height=2.4, width=0.45, life=0.9, offset=(0.6, 0, 0.2))
    L.pillar("vx_root_sap2", C["leaf"], height=1.8, width=0.35, life=0.8, offset=(-0.5, 0, -0.4))
    L.motes("vx_root_leaves", C["leaf"], n=8, radius=1.2, rise=-0.6, life=(1.0, 1.6), size=0.15, sprite="leaf", offset=(0, 2.2, 0), spin=120)
    L.compose("root_burst", [(0.0, "vx_root_crack"), (0.0, "vx_root_ring"), (0.0, "vx_root_soil"), (0.1, "vx_root_sap"), (0.18, "vx_root_sap2"),
                             (0.2, "vx_root_leaves")])
    # Bladder Jet: water shock ring, streaking spray, bubbles
    L.ring("vx_jet_wave", C["dew"], size=3.0, life=0.4, ground=False)
    L.sparks("vx_jet_spray", C["dew"], n=16, speed=(3.0, 6.0), gravity=-4, hot="#ffffff", width=0.05, length=0.4)
    L.motes("vx_jet_bubbles", C["dew"], n=10, radius=0.6, rise=1.2, life=(0.6, 1.0), size=0.12, sprite="dot")
    L.compose("jet_ring", [(0.0, "vx_jet_wave"), (0.0, "vx_jet_spray"), (0.05, "vx_jet_bubbles")])
    L.motes("jet_trail", C["dew"], n=6, radius=0.35, rise=1.0, life=(0.4, 0.7), size=0.1, sprite="dot", rate=24, active=0.4)
    L.splash("vx_dew_splash", C["dew"], size=1.4, life=0.4, alpha=0.9)
    L.sparks("vx_dew_drops", C["dew"], n=12, speed=(2.0, 3.5), gravity=-9, hot="#ffffff", material="particles_blend")
    L.compose("dew_burst", [(0.0, "vx_dew_splash"), (0.0, "vx_dew_drops")])
    L.motes("dry_flake", "#b78e5a", n=8, radius=0.6, rise=-1.2, life=(0.8, 1.2), size=0.12, sprite="leaf", spin=200, material="particles_blend")
    L.ring("vx_hyd_ring", C["dew"], size=1.8, life=0.5, ground=False, alpha=0.8)
    L.motes("vx_hyd_drops", C["dew"], n=8, radius=0.5, rise=1.4, life=(0.6, 0.9), size=0.09, sprite="droplet")
    L.compose("hydrate", [(0.0, "vx_hyd_ring"), (0.0, "vx_hyd_drops")])


# ============================================================================= 002 golem
def golem():
    C = GOL
    # Titan's Edict: each step of the shockwave tears the ground (molten crack, rocks, dust) and raises a rune pillar
    L.crack("vx_rupt_crack", C["ember"], size=2.4, life=0.8)
    L.debris("vx_rupt_rocks", C["stone"], n=6, speed=(3.0, 5.0), size=0.16)
    L.smoke("vx_rupt_dust", DUST, n=3, radius=0.4, size=(0.6, 1.2), life=(0.6, 0.9), rise=0.3, alpha=0.45, speed=1.2)
    L.compose("shock_rupture", [(0.0, "vx_rupt_crack"), (0.0, "vx_rupt_rocks"), (0.03, "vx_rupt_dust")])
    L.pillar("vx_glow_pillar", C["amber"], height=1.8, width=0.5, life=0.5)
    L.glyphs("vx_glow_rune", C["gold"], n=2, radius=0.4, rise=1.6, life=(0.6, 0.8), size=0.3)
    L.compose("shock_glow", [(0.0, "vx_glow_pillar"), (0.0, "vx_glow_rune")])
    # Runic Bastion: a hexagonal rune shield flashes where a blow lands
    L.motes("vx_bast_hex", C["gold"], n=7, radius=0.55, rise=0.0, life=(0.35, 0.5), size=0.42, sprite="hexagon", speed=0.0)
    L.flash("vx_bast_flash", C["gold"], size=1.6, life=0.25)
    L.sparks("vx_bast_sparks", C["amber"], n=10, speed=(2.5, 4.5), hot="#fff6dc")
    L.compose("bastion_flash", [(0.0, "vx_bast_hex"), (0.0, "vx_bast_flash"), (0.0, "vx_bast_sparks")])
    # Glyph Dominion: the great circle draws itself (radius / life from the script), runes rise
    circle_own = {"minecraft:emitter_rate_instant": {"num_particles": 1}, "minecraft:emitter_lifetime_once": {"active_time": 0.1},
                  "minecraft:emitter_shape_point": {}, "minecraft:particle_lifetime_expression": {"max_lifetime": "v.life"},
                  "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 12},
                  **billboard(["v.radius * 2.25", "v.radius * 2.25"], uv_flip("circle", fps=atlas.FRAMES / 0.6), "emitter_transform_xz"),
                  "minecraft:particle_appearance_tinting": {"color": [*L.rgb(C["amber"]), "0.95 * math.clamp((v.life - v.particle_age) * 2, 0, 1)"]}}
    L.flash("vx_dom_flash", C["gold"], size=3.0, life=0.4, offset=(0, 0.5, 0))
    L.ring("vx_dom_ring", C["gold"], size=12.0, life=0.7)
    L.glyphs("vx_dom_runes", C["gold"], n=10, radius=5.5, rise=1.0, life=(1.0, 1.6), size=0.35)
    L.compose("glyph_circle", [(0.0, "vx_dom_flash"), (0.0, "vx_dom_ring"), (0.3, "vx_dom_runes")], own=circle_own)
    L.pillar("vx_gpil_pillar", C["amber"], height=2.6, width=0.45, life=0.9, alpha=0.8)
    L.glyphs("vx_gpil_rune", C["gold"], n=1, radius=0.1, rise=1.2, life=(0.8, 1.0), size=0.32)
    L.compose("glyph_pillar", [(0.0, "vx_gpil_pillar"), (0.0, "vx_gpil_rune")])
    L.flash("vx_rspark_flash", C["gold"], size=1.2, life=0.22)
    L.sparks("vx_rspark_sparks", C["amber"], n=9, speed=(2.5, 4.5), hot="#fff6dc")
    L.compose("rune_spark", [(0.0, "vx_rspark_flash"), (0.0, "vx_rspark_sparks")])
    # Colossus Reassembly: burst apart, a stream of glowing stone along (dx,dy,dz,len), reform with a blast
    stream = {"minecraft:emitter_rate_instant": {"num_particles": 22}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
              "minecraft:emitter_shape_point": {}, "minecraft:particle_lifetime_expression": {"max_lifetime": "0.5 + v.particle_random_2 * 0.15"},
              "minecraft:particle_motion_parametric": {"relative_position": [
                  "v.dx * v.len * math.pow(math.min(1, v.particle_age / 0.55), 1.4) + math.sin(v.particle_age * 600 + v.particle_random_1 * 360) * 0.3",
                  "v.dy * v.len * math.pow(math.min(1, v.particle_age / 0.55), 1.4) + math.sin(math.min(1, v.particle_age / 0.55) * 180) * 1.2",
                  "v.dz * v.len * math.pow(math.min(1, v.particle_age / 0.55), 1.4) + math.cos(v.particle_age * 600 + v.particle_random_1 * 360) * 0.3"]},
              "minecraft:particle_initial_spin": {"rotation": "v.particle_random_1 * 360", "rotation_rate": 500},
              **billboard(["0.22", "0.22"], uv_sprite("chunk")),
              "minecraft:particle_appearance_tinting": tint_grad([(0.0, "#fff1c8", 1.0), (0.4, C["amber"], 1.0), (1.0, C["ember"], 1.0)])}
    L.flash("vx_shard_flash", C["gold"], size=2.4, life=0.3)
    L.debris("vx_shard_rocks", C["stone"], n=8, speed=(2.5, 4.5))
    L.compose("shard_stream", [(0.0, "vx_shard_flash"), (0.0, "vx_shard_rocks")], own=stream, material="particles_add")
    L.flash("vx_rburst_flash", C["gold"], size=2.6, life=0.32)
    L.ring("vx_rburst_ring", C["amber"], size=3.4, life=0.45, ground=False)
    L.glyphs("vx_rburst_runes", C["gold"], n=6, radius=0.8, rise=1.4, life=(0.7, 1.0), size=0.3)
    L.sparks("vx_rburst_sparks", C["amber"], n=12, speed=(3.0, 5.5), hot="#fff6dc")
    L.compose("rune_burst", [(0.0, "vx_rburst_flash"), (0.0, "vx_rburst_ring"), (0.0, "vx_rburst_sparks"), (0.05, "vx_rburst_runes")])
    L.ring("vx_rpulse_ring", C["amber"], size=2.4, life=0.5, alpha=0.85)
    L.glyphs("vx_rpulse_rune", C["gold"], n=2, radius=0.5, rise=0.8, life=(0.6, 0.9), size=0.26)
    L.compose("rune_pulse", [(0.0, "vx_rpulse_ring"), (0.0, "vx_rpulse_rune")])


# ============================================================================= 003 jackalope
def jackalope():
    C = JAK
    # Lunar Bound: crescent afterimages in the moon colour (script tint), silver glints
    crescent = {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.6},
                "minecraft:particle_initial_spin": {"rotation": "v.particle_random_1 * 360", "rotation_rate": 120},
                **billboard([f"0.8 * (1 - {AGE} * 0.4)", f"0.8 * (1 - {AGE} * 0.4)"], uv_sprite("crescent")),
                "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", f"0.95 * {FADE}"]}}
    L.motes("vx_bound_glint", C["moon"], n=3, radius=0.4, rise=0.2, life=(0.35, 0.55), size=0.12, sprite="star4", spin=200)
    L.compose("crescent_trail", [(0.0, "vx_bound_glint")], own=crescent)
    # Antler Brand / Lunar Sigil: a turning moon sigil over the branded head (script tint), light enough to repeat
    sigil = {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.5},
             "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 140},
             **billboard(["0.8", "0.8"], uv_sprite("glyphring")),
             "minecraft:particle_appearance_tinting": {"color": ["v.red", "v.green", "v.blue", f"0.9 * {IN_OUT}"]}}
    L.effect("moon_sigil", "particles_add", sigil)
    # Crimson Waltz: a huge crimson arc (spin / scale from the script), flash, sparks
    slash_own = {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.32},
                 "minecraft:particle_initial_spin": {"rotation": "v.spin", "rotation_rate": 0},
                 **billboard(["2.6 * v.scale", "2.6 * v.scale"], uv_flip("slash")),
                 "minecraft:particle_appearance_tinting": tint_grad([(0.0, "#ffffff", 1.0), (0.25, C["crimson"], 1.0), (1.0, C["blood"], 0.0)])}
    L.flash("vx_waltz_flash", C["crimson"], size=1.8, life=0.25)
    L.sparks("vx_waltz_sparks", C["crimson"], n=12, speed=(3.0, 6.0), hot="#ffe0e6")
    L.ring("vx_waltz_ring", C["moon"], size=2.4, life=0.35, ground=False, alpha=0.7)
    L.compose("crimson_slash", [(0.0, "vx_waltz_flash"), (0.0, "vx_waltz_sparks"), (0.04, "vx_waltz_ring")], own=slash_own)
    # Velvet Mirage: silver-violet smoke with star glints; the shimmer of the decoy
    L.smoke("vx_velvet_smoke", "#cfc6ff", n=6, radius=0.5, size=(0.6, 1.4), life=(0.6, 1.0), rise=0.6, alpha=0.6, speed=1.2)
    L.motes("vx_velvet_stars", C["moon"], n=10, radius=0.8, rise=0.4, life=(0.5, 0.9), size=0.16, sprite="star4", spin=180)
    L.flash("vx_velvet_flash", C["silver"], size=2.0, life=0.3)
    L.compose("velvet_burst", [(0.0, "vx_velvet_flash"), (0.0, "vx_velvet_smoke"), (0.03, "vx_velvet_stars")])
    L.motes("velvet_shimmer", C["silver"], n=4, radius=0.5, rise=0.7, life=(0.6, 0.9), size=0.11, sprite="star4", spin=200)


# ============================================================================= 004 xenentoma
def xenentoma():
    C = XEN
    # vibrations: a violet sonar ring spreading on the ground (private particles)
    L.ring("vibration_ping", C["violet"], size=2.2, life=0.9, alpha=0.95)
    L.ring("vibration_trace", C["nerve"], size=1.4, life=0.7, alpha=0.55)
    # Exuvia Proxy: shimmer, pale fluid, spinning chitin flakes
    L.flash("vx_molt_flash", C["lilac"], size=2.6, life=0.32)
    L.ring("vx_molt_ring", C["violet"], size=2.8, life=0.4, ground=False, alpha=0.8)
    L.splash("vx_molt_splash", C["fluid"], size=1.3, life=0.45, alpha=0.85)
    L.debris("vx_molt_flakes", C["ivory"], n=9, speed=(1.5, 3.0), sprite="shard", size=0.14, gravity=-8, bounce=0.2)
    L.motes("vx_molt_motes", C["violet"], n=8, radius=0.6, rise=0.6, life=(0.6, 1.0), size=0.08)
    L.compose("molt_fluid", [(0.0, "vx_molt_flash"), (0.0, "vx_molt_ring"), (0.0, "vx_molt_splash"), (0.02, "vx_molt_flakes"), (0.1, "vx_molt_motes")])
    L.debris("vx_chit_shards", C["ivory"], n=10, speed=(2.0, 4.0), sprite="shard", size=0.15, gravity=-10, bounce=0.3)
    L.sparks("vx_chit_sparks", C["violet"], n=8, speed=(2.0, 4.0), hot="#ffffff")
    L.compose("chitin_shards", [(0.0, "vx_chit_shards"), (0.0, "vx_chit_sparks")])
    # Anamorphic Surge: violet impact - flash, ring, streaking sparks, a crack of light
    L.flash("vx_surge_flash", C["violet"], size=1.9, life=0.26)
    L.ring("vx_surge_ring", C["lilac"], size=2.6, life=0.35, ground=False)
    L.sparks("vx_surge_sparks", C["violet"], n=12, speed=(3.5, 6.5), hot="#ffffff", length=0.45)
    L.compose("surge_strike", [(0.0, "vx_surge_flash"), (0.0, "vx_surge_ring"), (0.0, "vx_surge_sparks")])


# ============================================================================= 005 flying spaghetti monster
def spaghetti():
    C = FSM
    # His Noodly Touch: golden noodles reach out along (dx,dy,dz) and retract; holy sparkle at the source
    noodle = {"minecraft:emitter_rate_instant": {"num_particles": 26}, "minecraft:emitter_lifetime_once": {"active_time": 0.05},
              "minecraft:emitter_shape_point": {}, "minecraft:particle_lifetime_expression": {"max_lifetime": 0.7},
              "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 0},
              "minecraft:particle_motion_parametric": {"relative_position": [
                  "v.dx * v.particle_random_1 * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))",
                  "v.dy * v.particle_random_1 * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35)) + math.sin(v.particle_random_1 * 900) * 0.12",
                  "v.dz * v.particle_random_1 * math.sin(math.min(v.particle_age / 0.35, 1) * 90) * (v.particle_age < 0.35 ? 1 : (1 - (v.particle_age - 0.35) / 0.35))"]},
              **billboard(["0.34", "0.34"], exuv("f_noodle")), "minecraft:particle_appearance_tinting": tint("#ffffff"),
              "minecraft:particle_appearance_lighting": {}}
    L.flash("vx_touch_flash", C["holy"], size=1.1, life=0.25)
    L.motes("vx_touch_glints", C["gold"], n=6, radius=0.4, rise=0.5, life=(0.5, 0.8), size=0.12, sprite="star4", spin=200)
    L.compose("noodle_strand", [(0.0, "vx_touch_flash"), (0.0, "vx_touch_glints")], own=noodle, material="particles_blend", texture=EX)
    # Al Dente Reversal: the body snaps rigid - a golden crack of light, dry splinters
    L.crack("vx_dente_crack", C["gold"], size=2.0, life=0.6, offset=(0, 0, 0))
    L.REG["vx_dente_crack"]["particle_effect"]["components"]["minecraft:particle_appearance_billboard"]["facing_camera_mode"] = "lookat_xyz"
    L.flash("vx_dente_flash", C["holy"], size=1.6, life=0.25)
    L.debris("vx_dente_splinters", C["noodle"], n=9, speed=(2.0, 4.0), sprite="streak", size=0.18, gravity=-10, bounce=0.2, lit=False)
    L.compose("dente_crack", [(0.0, "vx_dente_flash"), (0.0, "vx_dente_crack"), (0.03, "vx_dente_splinters")])
    # sauce splash: crown of marinara, droplets, a curl of steam
    L.splash("vx_sauce_crown", "#ef4a32", size=2.2, life=0.45)
    L.REG["vx_sauce_crown"]["particle_effect"]["components"].pop("minecraft:particle_appearance_lighting", None)
    L.flash("vx_sauce_flash", "#ffb38a", size=1.4, life=0.22)
    L.debris("vx_sauce_drops", "#ffffff", n=10, speed=(2.2, 4.2), size=0.16, gravity=-12, bounce=0.05, uv=exuv("f_drop"), texture=EX, lit=False)
    L.smoke("vx_sauce_steam", C["steam"], n=2, radius=0.2, size=(0.4, 0.9), life=(0.7, 1.0), rise=0.8, alpha=0.35, speed=0.3)
    L.compose("sauce_splash", [(0.0, "vx_sauce_flash"), (0.0, "vx_sauce_crown"), (0.0, "vx_sauce_drops"), (0.1, "vx_sauce_steam")])
    # Great Pasta Revelation: a golden pasta spiral turning on the ground (repeated), then the sauce shockwave
    vortex = {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 0.75},
              "minecraft:particle_initial_spin": {"rotation": "v.particle_random_1 * 360", "rotation_rate": 260},
              **billboard([f"3.2 + {AGE} * 1.2", f"3.2 + {AGE} * 1.2"], exuv("f_spiral"), "emitter_transform_xz"),
              "minecraft:particle_appearance_tinting": tint("#ffffff", f"0.9 * {IN_OUT}")}
    L.motes("vx_vortex_noodles", "#ffffff", n=3, radius=1.6, rise=1.2, life=(0.6, 0.9), size=0.2, uv=exuv("f_loop"), texture=EX,
            material="particles_blend", spin=200)
    L.compose("pasta_vortex", [(0.0, "vx_vortex_noodles")], own=vortex, material="particles_blend", texture=EX)
    L.ring("vx_wave_ring", C["sauce"], size=11.0, life=0.7, material="particles_blend", alpha=0.9)
    L.flash("vx_wave_flash", C["holy"], size=3.4, life=0.35, offset=(0, 1.0, 0))
    L.pillar("vx_wave_pillar", C["holy"], height=5.0, width=1.2, life=0.8)
    L.debris("vx_wave_drops", "#ffffff", n=16, speed=(4.0, 7.0), size=0.14, gravity=-12, bounce=0.05, uv=exuv("f_blob"), texture=EX, up=0.9)
    L.smoke("vx_wave_steam", C["steam"], n=6, radius=1.2, size=(0.6, 1.4), life=(0.8, 1.3), rise=0.7, alpha=0.4, speed=1.5)
    L.compose("sauce_wave", [(0.0, "vx_wave_flash"), (0.0, "vx_wave_ring"), (0.0, "vx_wave_drops"), (0.02, "vx_wave_pillar"), (0.15, "vx_wave_steam")])
    # the detached meatball drips sauce as it flies (fired every 0.15 s by its own animation: a short burst, never looping)
    L.debris("meatball_trail", "#ffffff", n=2, speed=(0.2, 0.6), life=(0.5, 0.7), size=0.12, gravity=-7, bounce=0.05, uv=exuv("f_drop"),
             texture=EX, lit=False, up=-0.5)


# ============================================================================= 006 nurariten
def nurariten():
    C = NUR
    # gates of light: the torii appears with a flash, a pillar of light and petals
    gate = {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 1.0},
            **billboard([f"2.6 * (0.8 + 0.2 * math.min({AGE} * 4, 1))", f"2.6 * (0.8 + 0.2 * math.min({AGE} * 4, 1))"], exuv("n_gate")),
            "minecraft:particle_appearance_tinting": tint("#ffffff", IN_OUT)}
    L.flash("vx_gate_flash", C["warm"], size=2.6, life=0.3)
    L.pillar("vx_gate_pillar", C["gold"], height=4.0, width=1.0, life=0.8, offset=(0, -1.2, 0))
    L.ring("vx_gate_ring", C["gold"], size=4.0, life=0.6, offset=(0, -1.15, 0))
    L.motes("vx_gate_petals", "#ffffff", n=10, radius=1.0, rise=-0.3, life=(1.0, 1.6), size=0.14, uv=exuv("n_petal"), texture=EX,
            material="particles_blend", spin=160, speed=0.6)
    L.compose("arrival_gate", [(0.0, "vx_gate_flash"), (0.0, "vx_gate_ring"), (0.05, "vx_gate_pillar"), (0.1, "vx_gate_petals")], own=gate, texture=EX)
    # light dissolving into petals and gold dust that float away
    L.motes("vx_diss_petals", "#ffffff", n=12, radius=1.0, rise=0.9, life=(1.2, 1.8), size=0.13, uv=exuv("n_petal"), texture=EX,
            material="particles_blend", spin=140)
    L.motes("vx_diss_gold", C["gold"], n=10, radius=1.1, rise=1.1, life=(0.9, 1.4), size=0.08)
    L.flash("vx_diss_flash", C["warm"], size=1.6, life=0.3)
    L.compose("dissolve_light", [(0.0, "vx_diss_flash"), (0.0, "vx_diss_gold"), (0.05, "vx_diss_petals")])
    # decree glyphs burst out, gold sparks, a brief flash
    L.motes("vx_decree_glyphs", "#ffffff", n=8, radius=0.3, rise=0.2, life=(0.7, 1.0), size=0.3, uv=exuv("n_glyph"), texture=EX, speed=1.6,
            drag=2.6)
    L.sparks("vx_decree_sparks", C["gold"], n=8, speed=(2.0, 4.0), hot="#fffbe8", gravity=-2)
    L.flash("vx_decree_flash", C["warm"], size=1.8, life=0.25)
    L.ring("vx_decree_ring", C["gold"], size=2.4, life=0.35, ground=False, alpha=0.8)
    L.compose("decree_burst", [(0.0, "vx_decree_flash"), (0.0, "vx_decree_ring"), (0.0, "vx_decree_glyphs"), (0.02, "vx_decree_sparks")])
    # the court: rings and circles that draw themselves; pillars of light along the rim
    L.circle("vx_heaven_circle", C["gold"], size=9.0, life=1.8, draw=0.5, spin=10)
    L.ring("vx_heaven_ring", C["warm"], size=12.0, life=0.8)
    L.flash("vx_heaven_flash", C["warm"], size=2.6, life=0.35, offset=(0, 0.8, 0))
    L.motes("vx_heaven_glyphs", "#ffffff", n=8, radius=3.5, rise=1.0, life=(1.0, 1.5), size=0.24, uv=exuv("n_glyph"), texture=EX)
    L.compose("heaven_ring", [(0.0, "vx_heaven_flash"), (0.0, "vx_heaven_circle"), (0.0, "vx_heaven_ring"), (0.3, "vx_heaven_glyphs")])
    L.pillar("court_pillar", C["gold"], height=2.8, width=0.5, life=0.75, alpha=0.85)
    L.effect("court_ring", "particles_add", {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 1.3},
                                             "minecraft:particle_initial_spin": {"rotation": 0, "rotation_rate": 8},
                                             **billboard(["v.size", "v.size"], uv_frame("circle", 7), "emitter_transform_xz"),
                                             "minecraft:particle_appearance_tinting": tint(C["gold"], f"0.75 * {IN_OUT}")})
    # sky fracture: a crack of light torn across the sky, with a flash
    L.effect("vx_frac_crack", "particles_add", {**own_once(2), "minecraft:emitter_shape_disc": {"radius": 3.0, "plane_normal": "z"},
                                                "minecraft:particle_lifetime_expression": {"max_lifetime": "0.9 + v.particle_random_1 * 0.4"},
                                                "minecraft:particle_initial_spin": {"rotation": "v.particle_random_2 * 360", "rotation_rate": 0},
                                                **billboard(["3.0 + v.particle_random_3 * 2", "3.0 + v.particle_random_3 * 2"], uv_flip("crack")),
                                                "minecraft:particle_appearance_tinting": tint(C["warm"])})
    L.flash("vx_frac_flash", C["warm"], size=4.0, life=0.35)
    L.compose("sky_fracture", [(0.0, "vx_frac_flash"), (0.0, "vx_frac_crack")])
    # shadows: soft (blend), never cut out
    L.effect("gate_shadow", "particles_blend", {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 2.4},
                                                **billboard(["3.2", "3.2"], exuv("n_gate"), "emitter_transform_xz"),
                                                "minecraft:particle_appearance_tinting": tint(C["shadow"], f"0.45 * {IN_OUT}")}, texture=EX)
    L.effect("procession_shadow", "particles_blend", {**own_once(1, 0.1), "minecraft:particle_lifetime_expression": {"max_lifetime": 3.2},
                                                      "minecraft:particle_motion_parametric": {"relative_position": ["v.particle_age * 0.45 - 0.7", 0, 0]},
                                                      **billboard(["1.6", "0.8"], exuv("n_procession"), "emitter_transform_xz"),
                                                      "minecraft:particle_appearance_tinting": tint(C["shadow"], f"0.45 * {IN_OUT}")}, texture=EX)


REDESIGNED_FROM_EX = {"vibration_ping", "vibration_trace", "molt_fluid", "chitin_shards", "surge_strike", "noodle_strand", "dente_crack",
                      "sauce_splash", "pasta_vortex", "sauce_wave", "arrival_gate", "dissolve_light", "decree_burst", "heaven_ring",
                      "court_pillar", "court_ring", "sky_fracture", "gate_shadow", "procession_shadow"}


def build():
    """Define every v1.3 effect; returns the registry {name: particle JSON}."""
    L.REG.clear()
    shared()
    salamander()
    golem()
    jackalope()
    xenentoma()
    spaghetti()
    nurariten()
    return dict(L.REG)
