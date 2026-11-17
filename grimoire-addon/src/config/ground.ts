/**
 * Spell entities that always belong on the ground.  The framework settles them onto the terrain
 * under their own position (Scene.spawn / Actor.move), so decals, warning rings, ground effects and
 * walking creatures follow slopes instead of sinking into a hill or hanging over a dip.
 *
 * value = footprint radius in blocks per unit of grimoire:size.  Wide flat pieces (radius > 0) are
 * raised to the highest ground under their footprint (limited rise) so they are not buried;
 * 0 = just stand on the ground under the origin.  `near` types are only settled when they were
 * placed close to the ground (they are also used in the air on purpose).
 */
export const GROUND_ACTORS: Record<string, number> = {
  // Divine Word
  dw_column: 0, dw6_wall: 0, dw6_dome: 5.4, dw6_boundary: 8,
  // Dream & Nightmare
  dn_guest: 0, dn_guest_door: 0, dn_lull_wave: 1.1, dn_city_corridor: 0, dn_city_stair: 0, dn_city_stairfall: 0,
  dn_city_street: 0, dn_city_wave: 1.1, dn_dreamer_codex: 0, dn_dreamer_domain: 2.1, dn_dreamer_dream: 0,
  dn_dreamer_night: 0, dn_dreamer_stairs: 0, dn_dreamer_wheel: 0,
  // Elemental Dragon
  dragon_nature: 0, dragon_heat: 0, ed_nature_pillar: 0, ed_nature_quake: 2.0, ed_nature_root: 0, ed_nature_strata: 0,
  ed_heat_glass: 1.8, ed_heat_lane: 0, ed_heat_shimmer: 0, ed_heat_wave: 0, ed_tide_crown: 0, ed_tide_current: 0,
  ed_tide_frozen: 0, ed_air_shock: 1.3, ed_air_vortex: 0, ed5_gust: 1.6, ed5_icefan: 0, ed5_spike: 0, ed5_trail: 0,
  ed5_imprint_nature: 7.8, ed5_imprint_heat: 7.8, ed5_imprint_tide: 7.8, ed5_imprint_air: 7.8,
  ed5_inscription_nature: 1.9, ed5_inscription_heat: 1.9, ed5_inscription_tide: 1.9, ed5_inscription_air: 1.9,
  ed6_blast: 0, ed6_bridge: 0, ed6_emblem: 2.0, ed6_flora: 0, ed6_fog: 8, ed6_horizon: 0, ed6_iceshell: 0, ed6_ring: 0,
  ed6_spiral: 0, ed6_stone: 0,
};
/** Also used in mid-air: settled only when placed within GROUND_NEAR_TOLERANCE blocks of the ground. */
export const GROUND_NEAR: Record<string, number> = { telegraph: 1.0, dw_circle: 2.0 };
export const GROUND_NEAR_TOLERANCE = 6;

/**
 * Free-moving creatures and projectiles.  They may fly or stand anywhere, but the framework never lets
 * their origin sink into the terrain (a charge or a dive planned on flat ground would otherwise
 * disappear inside a hillside).  Rigid buildings are deliberately not listed: their parts must keep
 * their heights relative to each other.
 */
export const FLOOR_ACTORS = new Set<string>([
  "cherub", "ophanim", "dw5_letter", "dw6_edifice",
  "dn_parade_bird", "dn_parade_doll", "dn_parade_horse", "dn_parade_stag", "dn_city_fragment",
  "dn_dreamer_pillow", "dn_dreamer_shard", "dn_dreamer_roomcube",
  "dragon_air", "dragon_tide", "ed_tide_shard", "ed5_skel_nature", "ed5_skel_heat", "ed5_skel_tide", "ed5_skel_air",
  "ed5_tablet_nature", "ed5_tablet_heat", "ed5_tablet_tide", "ed5_tablet_air", "ed6_spirit",
]);
