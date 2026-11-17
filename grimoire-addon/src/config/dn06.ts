/** DN06 The Dreamer Who Never Wakes -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN06 = {
  // ---- domain & staging (blocks)
  /** Radius of the spell domain around the focus point: marks, zones and strikes stay inside it. */
  radius: 20,
  /** Maximum enemies carrying a sleeping-moon mark (marked enemies are the targets of every strike). */
  maxMarks: 8,
  /**
   * Where the Dreamer stands, measured from the caster along the view: this far beyond the focus point,
   * but never nearer than stageMin (so the whole figure stays inside the first-person view) nor farther
   * than stageMax.
   */
  stageBeyond: 20,
  stageMin: 34,
  stageMax: 44,
  /** The bed hangs this far beyond the Dreamer (but never farther than bedMax from the caster, so it stays within
   *  entity view range on a phone), its mattress this high above the ground, tilted toward the caster. */
  bedBeyond: 16,
  bedMax: 55,
  bedHeight: 10.3,
  /** Nothing tall comes nearer the caster than this (zones, formations, the pendulum). */
  clearZone: 8,
  /** Largest body turn (deg) the Dreamer makes toward the main enemy group for the finale, and how far it may
   *  glide forward so that the beam from its face-door lands on that group. */
  finaleTurn: 35,
  finaleAdvance: 9,

  // ---- Phase II: giant-body attacks
  /** Dropped pillow: damage, blast radius and knockback. */
  pillowDamage: 10,
  pillowRadius: 3.5,
  pillowKnock: 1.4,
  /** Hand sweep: damage, reach of the hand around its path, sideways knockback, furthest lunge forward. */
  sweepDamage: 14,
  sweepRadius: 3.4,
  sweepKnock: 2.2,
  sweepLunge: 9,
  /** Spilled stairs: damage per enemy, width of the cascade. */
  stairsDamage: 9,
  stairsRadius: 2.4,

  // ---- Phase III: zones (all zones have this radius)
  zoneRadius: 4.5,
  /** Dream zones: heal per pulse (every zonePulse ticks), supportive effect duration, ward strength. */
  zonePulse: 20,
  dreamHeal: 2,
  dreamEffectTicks: 50,
  /** Fraction of damage that still reaches an ally standing in a dream zone, and the ward's total pool. */
  wardFactor: 0.55,
  wardPool: 40,
  /** Distance of the two flanking dream gardens from the caster, and their angle off the view (deg). */
  dreamFlank: 8.5,
  dreamFlankAngle: 48,
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
  wheelRadius: 3.2,
  wheelSpeed: 0.42,
  /** Window shards released by the arcade forearms: count and damage. */
  shards: 6,
  shardDamage: 10,
  /** Spiral-stair drill: impact damage/radius, damage per boring pulse, slowness ticks. */
  drillDamage: 18,
  drillRadius: 4,
  drillTick: 4,
  /** Bed pendulum: damage and hit radius around the cradle while it sweeps low, rope length. */
  pendulumDamage: 20,
  pendulumRadius: 5,
  pendulumLength: 12,
  /** Expanding room-cubes fired from the chest: count, damage, hold ticks, capture radius. */
  rooms: 3,
  roomDamage: 14,
  roomHold: 24,
  roomRadius: 3,
  /** Face-door finale: pull radius, pull speed (blocks/tick), beam damage every 12 ticks, final strike. */
  beamRadius: 9,
  beamPull: 0.2,
  beamDamage: 3,
  finalDamage: 32,
  finalRadius: 8,
  finalKnock: 2.6,

  /** Ticks of warning before every telegraphed giant strike (pillow, stairs, shards...). */
  warnShort: 20,
  warnLong: 40,
};
