/**
 * Shared identifiers and tuning for The Porcelain Emperor.
 * Every "porcelain:" identifier used here is checked against the built packs by tools/validate.py.
 */

export const DIM_ID = "porcelain:fractured_mandate";

export const ENT = {
  emperor: "porcelain:emperor",
  tablet: "porcelain:edict_tablet",
  shard: "porcelain:shard",
  rubble: "porcelain:rubble",
  claw: "porcelain:severed_claw",
  courtier: "porcelain:courtier",
} as const;

export const ITEM = {
  seal: "porcelain:imperial_seal",
  heart: "porcelain:kintsugi_heart",
  shard: "porcelain:mandate_shard",
} as const;

export const BLOCK = {
  marble: "porcelain:ivory_marble",
  tile: "porcelain:marble_tile",
  seam: "porcelain:kintsugi_seam",
  cracked: "porcelain:cracked_marble",
  lacquer: "porcelain:vermilion_lacquer",
  roof: "porcelain:imperial_roof",
  gilded: "porcelain:gilded_floor",
  sealTile: "porcelain:seal_tile",
  air: "minecraft:air",
  lantern: "minecraft:lantern",
} as const;

export const FX = {
  telegraph: "porcelain:telegraph",
  crackDecal: "porcelain:crack_decal",
  ringWave: "porcelain:ring_wave",
  goldBurst: "porcelain:gold_burst",
  chipBurst: "porcelain:chip_burst",
  flakeBurst: "porcelain:flake_burst",
  dust: "porcelain:dust_puff",
  petals: "porcelain:petals",
  goldMote: "porcelain:gold_mote",
  redMote: "porcelain:red_mote",
  breath: "porcelain:breath",
  gateSwirl: "porcelain:gate_swirl",
} as const;

export const SND = {
  chime: "porcelain.chime",
  chimeLow: "porcelain.chime_low",
  crack: "porcelain.crack",
  shatter: "porcelain.shatter",
  gong: "porcelain.gong",
  stamp: "porcelain.stamp",
  roar: "porcelain.roar",
  hum: "porcelain.hum",
  music: "porcelain.music.mandate",
} as const;

export const FOG = {
  mandate: "porcelain:mandate_fog",
  fractured: "porcelain:mandate_fog_fractured",
  mended: "porcelain:mandate_fog_mended",
  tag: "porcelain_mandate",
} as const;

export const PROP = {
  phase: "porcelain:phase",
  action: "porcelain:action",
  plates: "porcelain:plates",
  claw: "porcelain:claw",
  bend: "porcelain:bend",
  tilt: "porcelain:tilt",
  embedded: "porcelain:embedded",
  strike: "porcelain:strike",
} as const;

/** Animation states of the Emperor (mirrors ACTIONS in tools/assets_rp.py). */
export const ACT = {
  IDLE: 0,
  PROCESSION: 1,
  EDICT: 2,
  BREATH: 3,
  REPAIR: 4,
  DIVE: 5,
  STAGGER: 6,
  RUBBLE: 7,
  CLAW: 8,
  STORM: 9,
  KOWTOW_CALL: 10,
  KOWTOW_BOW: 11,
  RUSH_OUT: 12,
  RUSH_IN: 13,
  ROAR: 14,
  DEATH: 15,
  AWAKEN: 16,
  PERCH: 17,
} as const;

export const WORLD_PROP = {
  fight: "porcelain:fight_active",
  returnPoint: "porcelain:return",
  victories: "porcelain:victories",
} as const;

/** Arena geometry (blocks, relative to the arena centre; y = 0 is the floor layer). */
export const ARENA = {
  preferredFloorY: 100,
  radius: 26,
  pillarRadius: 21,
  arrival: { x: 0, y: 1, z: 19 },
  throne: { x: 0, y: 4, z: -22 },
  gate: { x: 0, y: 5, z: 24 },
  tickingHalf: 44,
  fallLimit: -9,
} as const;

export const BOSS = {
  maxHp: 900,
  phase2At: 0.7,
  phase3At: 0.4,
  plates: 6,
  /** damage the boss takes per phase (porcelain that is still whole is harder to break) */
  phaseArmor: [1, 0.85, 1.0, 1.15] as const,
  vulnerableMult: 1.8,
  repairInterruptFraction: 0.07,
  repairHealPerShard: 0.025,
} as const;

/** Base damage dealt to players on Normal difficulty (scaled for Easy / Hard). */
export const DMG = {
  procession: 7,
  tablet: 6,
  breathTick: 2.5,
  diveCenter: 13,
  diveEdge: 6,
  diveShard: 4,
  rubble: 7,
  claw: 6,
  storm: 6,
  kowtow: 15,
  rush: 9,
  fall: 4,
} as const;
