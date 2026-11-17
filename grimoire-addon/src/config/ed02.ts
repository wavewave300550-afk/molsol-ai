/** ED02 Thermal Tyrant: Furnace of the Carnotaur -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const ED02 = {
  // ---- staging (blocks)
  /** The charge lane starts this far behind the caster... */
  laneBack: 3,
  /** ...and this far to the caster's right, so the 17-block dragon emerges beside them, not on them. */
  laneSide: 5,
  /** If the focus point is closer than this to the caster, the lane is aimed straight ahead instead. */
  minFocus: 9,
  /** The hips run this far past the focus point before skidding (the horns lead by ~8 blocks). */
  overshoot: 5,
  /** Clamp of the hips' charge distance (lane length incl. horns and skid ends up ~26-34 blocks). */
  chargeMin: 16,
  chargeMax: 24,
  /** Heat-shimmer wall stands this far ahead of the dragon's spawn point. */
  wallAhead: 1,

  // ---- Stage I: Internal Ignition (heat shock when the dragon bellows)
  igniteRadius: 6,
  igniteDamage: 4,
  igniteKnock: 0.7,

  // ---- Stage II: The Carnotaur's Rampage
  /** Sprint starts at this fraction of full speed and reaches full speed after accelTicks. */
  startSpeed: 0.55,
  accelTicks: 6,
  /** Horn strike zone: centred hornReach blocks ahead of the hips, hornDepth deep, hornRadius to either side. */
  hornReach: 7,
  hornDepth: 2.2,
  hornRadius: 2.6,
  hornDamage: 9,
  /** Horn toss throws enemies sideways out of the lane (horizontal / vertical strength). */
  hornKnockH: 1.5,
  hornKnockV: 0.6,
  /** Body slam zone along the flanks (blocks behind / ahead of the hips, half width). */
  bodyBack: 2.5,
  bodyFront: 5,
  bodyRadius: 2.5,
  bodyDamage: 6,
  bodyKnockH: 1.1,
  bodyKnockV: 0.35,
  /** Minimum ticks between a horn hit and a body hit on the same enemy. */
  bodyDelay: 4,
  /** Search radius around the dragon for melee checks. */
  scanRadius: 10,

  // ---- Stage III: The Furnace Opens
  /** Point-blank thermal discharge around the dragon when the vents release. */
  dischargeRadius: 6,
  dischargeDamage: 8,
  dischargeKnock: 1.4,
  /** The superheated wave runs back along the charge lane at this speed (blocks/s). */
  waveSpeed: 18,
  /** Half width of the wave (blocks either side of the lane centre). */
  waveHalfWidth: 3.6,
  waveDamage: 11,
  waveKnockH: 0.6,
  waveKnockV: 0.25,
  /** Wave starts this far in front of the hips (at the chest) and stops this far from the lane start. */
  waveStartBack: 2.5,
  waveStopShort: 3,
  /** Burning and weakness left by the wave and the discharge. */
  burnSeconds: 3,
  weaknessTicks: 80,
  /** Vitrified-ground decals every N blocks behind the wave; they cool and fade on these delays (ticks). */
  glassEvery: 3.2,
  glassCoolTicks: 24,
  glassFadeTicks: 40,
  /** Heavy breathing between cooling and dissolution (ticks). */
  pantTicks: 16,
};
