/** DN06 The Dreamer Who Never Wakes -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN06 = {
  // ---- domain & staging (blocks)
  /** Radius of the spell domain around the focus point: marks, zones and strikes stay inside it. */
  radius: 20,
  /** Maximum enemies carrying a sleeping-moon mark (marked enemies are the targets of every strike). */
  maxMarks: 8,
  /** How far beyond the focus point the bed floats, and its height (mattress top) above the ground. */
  bedBack: 20,
  bedHeight: 18,
  /** Where the risen Dreamer hovers (beyond the focus) and its pelvis height above the ground. */
  hoverBack: 12,
  hoverHeight: 12.5,
  /** Largest head/body turn (deg) the Dreamer makes toward the main enemy group for the finale. */
  finaleTurn: 35,

  // ---- Phase II: giant-body attacks
  /** Dropped pillow: damage, blast radius and knockback. */
  pillowDamage: 10,
  pillowRadius: 3.5,
  pillowKnock: 1.4,
  /** Hand sweep: damage, reach of the hand around its path, sideways knockback. */
  sweepDamage: 14,
  sweepRadius: 3.2,
  sweepKnock: 2.2,
  /** Spilled stairs: damage per enemy, width of the cascade. */
  stairsDamage: 9,
  stairsRadius: 2.2,

  // ---- Phase III: zones (all zones have this radius)
  zoneRadius: 4.5,
  /** Dream zones: heal per pulse (every zonePulse ticks), supportive effect duration, ward strength. */
  zonePulse: 20,
  dreamHeal: 2,
  dreamEffectTicks: 50,
  /** Fraction of damage that still reaches an ally standing in a dream zone, and the ward's total pool. */
  wardFactor: 0.55,
  wardPool: 40,
  /** Nightmare zones: damage per pulse, slowness/weakness strength, and the stronger "bite" every 2 pulses. */
  nightDamage: 3,
  nightSlowAmp: 2,
  biteDamage: 5,
  /** Ticks an enemy is swallowed (held) by the predatory corridor; levitation of the upside-down room. */
  corridorHold: 20,
  roomLift: 12,

  // ---- Phase IV: the Great Unreality
  /** Wheel of doors: damage, hit radius, rolling speed (blocks/tick). */
  wheelDamage: 16,
  wheelRadius: 3.6,
  wheelSpeed: 0.38,
  /** Window shards released by the arcade forearms: count and damage. */
  shards: 6,
  shardDamage: 10,
  /** Spiral-stair drill: impact damage/radius, damage per boring pulse, slowness ticks. */
  drillDamage: 18,
  drillRadius: 4,
  drillTick: 4,
  /** Bed pendulum: damage and hit radius around the bed while it sweeps low. */
  pendulumDamage: 20,
  pendulumRadius: 6,
  pendulumLength: 14,
  /** Expanding room-cubes fired from the chest: count, damage, hold ticks, capture radius. */
  rooms: 3,
  roomDamage: 14,
  roomHold: 24,
  roomRadius: 3,
  /** Face-door finale: pull radius, pull speed (blocks/tick), beam damage every 10 ticks, final strike. */
  beamRadius: 9,
  beamPull: 0.2,
  beamDamage: 3,
  finalDamage: 32,
  finalRadius: 7,
  finalKnock: 2.6,

  /** Ticks of warning before every telegraphed giant strike (pillow, stairs, shards...). */
  warnShort: 20,
  warnLong: 40,
};
