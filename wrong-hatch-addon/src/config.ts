/**
 * Balancing values for The Wrong Hatch. Damage numbers are "Normal difficulty"
 * values; Easy x0.7, Hard x1.3. Ticks are 1/20 s.
 */
export const BOSS_ID = "wh:wrong_hatch";
export const REMAINS_ID = "wh:wrong_hatch_remains";
export const CHICK_ID = "wh:wrong_chick";
export const EGG_ID = "wh:hatch_egg";
export const LOBBED_EGG_ID = "wh:lobbed_egg";
export const SHELL_ID = "wh:brood_shell";
export const DART_ID = "wh:feather_dart";

export const BASE_HP = [600, 900, 1200, 1500]; // by number of players present at spawn (1..4+)

export const PHASE2_AT = 0.65; // health fraction
export const PHASE3_AT = 0.3; // first Final Hatch, then phase III
export const LAST_HATCH_AT = 0.1; // second Final Hatch

export const DMG = {
  peck: 10,
  peckCombo: [8, 8, 12],
  guillotine: 16,
  guillotineRear: 14,
  backScratch: 8,
  sickleSweep: 12,
  broodquakeSlam: 20,
  broodquakeRing: 10,
  eggImpact: 5,
  eggBlast: 8,
  dart: 6,
  fortressBurst: 12,
  crow: 6,
  rush: 14,
  beamTick: 4,
  flash: 4,
  wingHopLand: 8,
  skyDrop: 22,
  skyDropRing: 8,
  moltStormTick: 3,
  moltStormEnd: 8,
  moltBurst: 5,
  yolklingBlast: 9,
  novaBase: 6,
  novaPerShell: 7,
};

/** Pause between two attacks, per phase [min, max] ticks. */
export const RECOVER: Record<number, [number, number]> = { 1: [26, 38], 2: [18, 28], 3: [10, 18] };

export const COOLDOWN: Record<string, number> = {
  peck: 30,
  guillotine: 120,
  back_scratch: 90,
  sickle_sweep: 110,
  broodquake: 320,
  egg_mortar: 300,
  feather_volley: 200,
  shell_fortress: 700,
  rotten_hatch: 560,
  rooster_rush: 280,
  yolk_beam: 420,
  dawn_flash: 620,
  brood_call: 500,
  wing_hop: 160,
  sky_drop: 340,
  molt_storm: 480,
  molt_burst: 240,
};

export const FORTRESS = { duration: 140, breakPerScale: 60, reduction: 0.15, exposedTicks: 80, exposedMul: 1.5 };
export const RUSH_STUN = { ticks: 60, mul: 1.35 };
export const BOTCHED = { ticks: 120, mul: 1.5 };

export const HUD_RANGE = 48;
export const LEASH_RANGE = 40;
export const DESPAWN_AFTER_TICKS = 20 * 180; // no player within 96 blocks for 3 minutes
export const RESET_AFTER_TICKS = 20 * 30; // no target for 30 s -> walk/teleport home and regenerate
