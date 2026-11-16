/** Tuning for the VESPER-0 encounter. Damage values are Normal difficulty, before armour. */
export const CFG = {
  maxHealth: 1000,
  arenaRange: 64, // players within this distance of the arena centre take part
  leashRange: 46, // the boss stays within this distance of the arena centre
  departAfterTicks: 600, // no combatants for 30 s -> VESPER-0 leaves (Psalter refunded)

  // damage taken by the boss
  hullMultP1: 0.55,
  hullMultP2: 0.8,
  heartMult: 1.75,
  heartMultStunned: 2.0,
  explosionMult: 0.5,
  perHitCap: 60,
  groupScale: (players: number) => 1 / (1 + 0.5 * Math.max(0, Math.min(players, 8) - 1)),

  // thresholds (fraction of max health)
  thresholds: { prayer1: 0.75, transform: 0.5, prayer2: 0.25, enrage: 0.12 },

  // movement
  altitudeP1: 11,
  altitudeP2: 4.5,
  orbitRadiusP1: 15,
  orbitRadiusP2: 10,
  maxSpeedP1: 0.32,
  maxSpeedP2: 0.5,
  turnRateP1: 2.4,
  turnRateP2: 5.5,

  // abilities
  lance: { charge: 36, fire: 50, sweepDeg: 34, range: 48, radius: 1.35, damage: 10, burn: 3, hitEvery: 10, cooldown: 280 },
  rite: { waves: [24, 42, 60], speed: 0.5, maxRadius: 30, band: 0.9, damage: 8, cooldown: 320 },
  horizon: { warn: 50, active: 80, radius: 9, crushRadius: 2.5, crushDamage: 3, implodeRadius: 4.5, implodeDamage: 10, cooldown: 240 },
  choir: { drones: 3, droneHealth: 16, life: 600, fireEvery: 70, orbSpeed: 0.45, orbDamage: 6, orbLife: 130,
    reflectSpeed: 0.95, reflectDamage: 30, cooldown: 560 },
  genuflect: { descend: 30, window: 140, flare: 30, burstRadius: 6.5, burstDamage: 9, forceAfter: 500 },
  prayer: { durationP1: 400, durationP2: 320, censersP1: 3, censersP2: 4, censerHealth: 24, pulseEvery: 80,
    pulseDamage: 3, stun: 160, benedictionP1: 14, benedictionP2: 18, healPerCenser: 0.06 },
  transform: { length: 180, ringsAt: 60, limbsAt: 70, platesAt: 78, skinAt: 132, roarAt: 154, plates: 6, plateDamage: 10 },
  lunge: { windup: 26, lockAt: 14, dash: 16, speed: 1.4, radius: 3.4, damage: 14, anchored: 70, cooldown: 200 },
  talons: { strikes: 5, interval: 10, warn: 18, radius: 2.4, damage: 11, cooldown: 180 },
  nova: { charge: 60, range: 48, damage: 18, cooldown: 440 },
  seraph: { health: 40, dormant: 400, unhaloed: 120 },
  death: { length: 160 },

  rewards: { alloyMin: 8, alloyMax: 12, xp: 1500, blessing: 600, blessRadius: 16 },
  gcdP1: [50, 70] as const,
  gcdP2: [30, 46] as const,
};

export type Config = typeof CFG;
