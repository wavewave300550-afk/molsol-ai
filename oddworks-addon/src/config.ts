// Identifiers and every gameplay tunable in one place (ticks unless stated otherwise).

export const ID = {
  goggles: "oddworks:solar_frost_goggles",
  handline: "oddworks:endless_handline",
  handlineCast: "oddworks:endless_handline_cast",
  cane: "oddworks:bamboo_sword_cane",
  caneDrawn: "oddworks:bamboo_sword_cane_drawn",
  hook: "oddworks:handline_hook",
  bobber: "oddworks:handline_bobber",
  sunDog: "oddworks:sun_dog",
  iceShell: "oddworks:ice_shell",
} as const;

export const ODD_ITEMS: ReadonlySet<string> = new Set([ID.goggles, ID.handline, ID.handlineCast, ID.cane, ID.caneDrawn]);
export const FX_ENTITIES: readonly string[] = [ID.hook, ID.bobber, ID.sunDog, ID.iceShell];

/** Cooldown categories used as script -> attachable animation signals (no item uses them). */
export const SIG = {
  gogglesFull: "oddworks:sig_goggles_full",
  caneDraw: "oddworks:sig_cane_draw",
  caneNoto: "oddworks:sig_cane_noto",
  caneDeflect: "oddworks:sig_cane_deflect",
} as const;

export const GOGGLES = {
  chargePerTick: 1 / 30, // at solar power 1.0 a full charge takes 1.5 s
  minCap: 0.25, // in total darkness the lenses can still hold a quarter charge
  overholdTicks: 50, // holding a full charge longer than this frosts the lenses (rime-over)
  rimeLockout: 80,
  minFire: 0.08,
  rangeBase: 12,
  rangePerCharge: 28,
  damageBase: 2,
  damagePerCharge: 10,
  frostBase: 35,
  frostPerCharge: 70,
  cooldownBase: 20,
  cooldownPerCharge: 40,
  flashCooldown: 140,
  flashMinPower: 0.2,
  flashHalfAngle: 35,
  sunDogCooldown: 1000,
  sunDogCapture: 24,
  sunDogLife: 900,
  sunDogLifeSnow: 1200,
  sunDogRadius: 12,
  sunDogMaxAngle: 22,
  wearBeam: 1,
  wearFlash: 1,
  wearSunDog: 3,
} as const;

export const LINE = {
  maxLength: 96,
  revTicks: 9, // one overhead revolution
  maxRevs: 4,
  speedBase: 0.9,
  speedPerRev: 0.45,
  reelSpeed: 0.55,
  payOutSpeed: 0.25,
  strainBreak: 1,
  snapCooldown: 120,
  slingCooldown: 60,
  breakCooldown: 100,
  hookDamage: 2,
  whirlDamage: 2,
  wearCast: 1,
  wearBreak: 6,
  wearSnap: 2,
  biteWindow: 26,
} as const;

export const CANE = {
  gripFull: 20, // focus reaches 100% after 1 s
  perfectFrom: 11,
  perfectTo: 16,
  dashBase: 2.5,
  dashPerFocus: 2.5,
  dashPerfect: 5,
  iaiDamageBase: 4,
  iaiDamagePerFocus: 6,
  iaiCooldown: 60,
  iaiCooldownPerfect: 40,
  deflectWindow: 8,
  deflectPerfect: 4,
  deflectCooldownHit: 12,
  deflectCooldownWhiff: 36,
  ripostDamage: 5,
  notoTicks: 11,
  notoCooldown: 80,
  woundMax: 5,
  woundTicks: 120, // a wound keeps bleeding for 6 s after the last cut
  bleedPerStack: 0.5, // damage per second per stack (before constitution)
  hemorrhageMult: 1.25,
  wearCut: 1,
  wearClang: 2,
  wearHeavyBlock: 8,
} as const;
