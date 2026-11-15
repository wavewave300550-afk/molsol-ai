/** Identifiers used by Boss 001 (checked against the generated packs by tools/validate.py). */
export const ENT = {
  leg: "anatomy:mm_root_leg",
  node: "anatomy:mm_resonance_node",
  heart: "anatomy:mm_lithic_heart",
  slab: "anatomy:mm_strata_slab",
  petal: "anatomy:mm_petal",
  plate: "anatomy:mm_strata_plate",
  anchor: "anatomy:mm_anchor_root",
} as const;

/** Boss reward items. */
export const ITEM = {
  shard: "anatomy:lithic_heart_shard",
  breaker: "anatomy:strata_breaker",
  greaves: "anatomy:anchorage_greaves",
} as const;

export const PROP = {
  legIndex: "anatomy:leg_index",
  pose: "anatomy:pose",
  hanging: "anatomy:hanging",
  charging: "anatomy:charging",
  dying: "anatomy:dying",
  open: "anatomy:open",
  phase: "anatomy:phase",
  petalState: "anatomy:petal_state",
  petalIndex: "anatomy:petal_index",
  variant: "anatomy:variant",
  flip: "anatomy:flip",
} as const;

export const ANIM = {
  legStomp: "animation.anatomy.mm_root_leg.stomp",
  legFlinch: "animation.anatomy.mm_root_leg.flinch",
  heartHurt: "animation.anatomy.mm_lithic_heart.hurt",
} as const;

export const PX = {
  dust: "anatomy:mm_dust",
  debris: "anatomy:mm_debris",
  crack: "anatomy:mm_crack",
  fault: "anatomy:mm_fault",
  target: "anatomy:mm_target",
  ring: "anatomy:mm_resonance_ring",
  wave: "anatomy:mm_resonance_wave",
  beam: "anatomy:mm_beam",
  mist: "anatomy:mm_mist",
  shard: "anatomy:mm_shard",
  heartGlow: "anatomy:mm_heart_glow",
  shield: "anatomy:mm_shield",
  safe: "anatomy:mm_safe",
  vent: "anatomy:mm_vent",
  leaf: "anatomy:mm_leaf",
  guide: "anatomy:mm_guide",
  pillar: "anatomy:mm_pillar",
  nodeBeacon: "anatomy:mm_node_beacon",
  mineralBeam: "anatomy:mm_mineral_beam",
  cloudStream: "anatomy:mm_cloud_stream",
} as const;

export const SND = {
  groan: "anatomy.mm.groan",
  rumble: "anatomy.mm.rumble",
  quake: "anatomy.mm.quake",
  crack: "anatomy.mm.crack",
  grind: "anatomy.mm.grind",
  wave: "anatomy.mm.wave",
  resonance: "anatomy.mm.resonance",
  chime: "anatomy.mm.chime",
  heartbeat: "anatomy.mm.heartbeat",
  heartOpen: "anatomy.mm.heart_open",
  heartClose: "anatomy.mm.heart_close",
  shatter: "anatomy.mm.shatter",
  unfold: "anatomy.mm.unfold",
  step: "anatomy.mm.step",
  contract: "anatomy.mm.contract",
  whoosh: "anatomy.mm.whoosh",
  warn: "anatomy.mm.warn",
  deflect: "anatomy.mm.deflect",
  vent: "anatomy.mm.vent",
  rootTear: "anatomy.mm.root_tear",
  sinewSnap: "anatomy.mm.sinew_snap",
  beamCharge: "anatomy.mm.beam_charge",
  beamFire: "anatomy.mm.beam_fire",
  heartRise: "anatomy.mm.heart_rise",
  islandBreak: "anatomy.mm.island_break",
} as const;

export const MUSIC = {
  phase1: "anatomy.music.mm_phase1",
  phase2: "anatomy.music.mm_phase2",
  victory: "anatomy.music.mm_victory",
  phase3: "anatomy.music.mm_phase3",
} as const;

export const FOG = "anatomy:migration_mist";
export const TAG = "anatomy_mm";
export const DIMENSION = "anatomy:migration_path";
