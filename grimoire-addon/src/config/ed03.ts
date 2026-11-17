/** ED03 Abyssal Cryotitan: The Frozen Tidal Crown -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const ED03 = {
  /** How far from the aim point the spell snaps onto the nearest enemy (blocks). */
  snap: 12,
  /** Radius around the focus in which the enemy group is gathered. */
  radius: 12,
  /** Maximum enemies used to define the group (and shard targets per wave). */
  maxTargets: 8,

  // ---- Stage I: The Rising Deep
  /** The dragon lands this far beyond the focus point, its flank (right side) toward the caster. */
  landBeyond: 9,
  /** Radius and sweep (degrees) of the descending spiral it swims from the water mass to its landing. */
  spiralRadius: 6.5,
  spiralSweep: 240,
  /** Height of the suspended water mass above the landing ground and its rendered size multiplier. */
  massHeight: 12,
  massSize: 1.2,
  /** Landing wave: enemies within this radius of the dragon are washed away (knockback) and take damage. */
  landRadius: 6,
  landDamage: 3,
  landKnockH: 0.9,
  landKnockV: 0.3,

  // ---- Stage II: The Cryogenic Sail
  /** Current radius = group spread + pad, clamped (blocks).  Each tail sweep throws two currents. */
  currentPad: 1.5,
  currentMin: 2.5,
  currentMax: 7,
  /** Radius multipliers of the four currents (two per sweep). */
  currentScale: [1.0, 0.72, 1.18, 0.55],
  /** Half-width of a current's water band: enemies inside are carried along it. */
  currentWidth: 1.8,
  /** Water-based displacement: push strength along the current, applied every `shoveEvery` ticks. */
  currentShove: 0.5,
  shoveEvery: 3,
  /** Damage when a current first catches an enemy. */
  currentDamage: 3,
  /** Freezing front: enemies within this distance of a current when the front passes are frozen. */
  freezeWidth: 2.3,
  freezeDamage: 5,
  /** Freezing is temporary: it lasts until the crown's third fracture wave (plus slowness afterwards). */
  thawSlowTicks: 60,
  thawSlowAmp: 1,
  /** Height of the barrier columns raised under the ice spirals (real obstacles, every other segment). */
  barrierHeight: 2,

  // ---- Stage III: The Frozen Crown
  /** Crown radius = group spread + pad, clamped. */
  crownPad: 2.5,
  crownMin: 3.5,
  crownMax: 7.5,
  /** Damage of each of the three fracture waves (sharp ice formations that hit each enemy). */
  shardDamage: [5, 6, 8],
  /** Ticks a shard needs to reach its enemy. */
  shardFlight: 6,
  /** Finishing area damage around the crown centre: radius = crown radius + finalExtra. */
  finalDamage: 14,
  finalExtra: 2.5,
  finalKnockH: 1.4,
  finalKnockV: 0.5,

  // ---- dragon anatomy used to place effects (rendered blocks)
  /** Distance from the dragon origin back to its hips, and hip-to-tail-tip length. */
  hipBack: 2.4,
  tailReach: 11,
};
