/** DW04 Divine Edict: Let There Be Sanctuary -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DW04 = {
  // ---- architecture (blocks).  Changing these also needs the asset module (tools/assets/dw_sanctuary.py).
  /** Distance from the caster to each of the eight corner pillars (octagon circumradius). */
  cornerRadius: 9.5,
  /** Height at which the vault ribs spring from the pillar capitals. */
  ribSpring: 11.75,
  /** Height of the floating galleries above the wall panels. */
  bridgeHeight: 10,
  /** Height of the keystone crown at the centre (rib spring + rib rise). */
  crownHeight: 16.5,

  // ---- defences
  /** Total durability of the sanctuary: absorbed damage, repelled intruders and dissolved shots all spend it. */
  durability: 90,
  /** Fraction of incoming damage allies inside still take (0.2 = 80 % absorbed by the ward). */
  wardFactor: 0.2,
  /** Allies count as inside within this horizontal distance of the centre. */
  innerRadius: 8.2,
  /** ...and within this vertical band relative to the floor. */
  insideBelow: 2,
  insideAbove: 18,
  /** Hostiles that cross this radius are repelled by the threshold law. */
  thresholdRadius: 8.0,
  /** Ticks between threshold checks, and per-intruder immunity after being repelled. */
  thresholdEvery: 4,
  repelCooldown: 14,
  /** Repel strength (horizontal, vertical), slowness and a small smite. */
  repelH: 1.5,
  repelV: 0.4,
  repelSlowTicks: 40,
  repelSlowAmp: 2,
  repelDamage: 2,
  /** Durability spent per repelled intruder. */
  repelCost: 4,
  /** Durability spent per dissolved hostile projectile. */
  projectileCost: 3,
  /** Ticks between projectile sweeps. */
  projectileEvery: 2,
  /** Durability fractions at which one wall section breaks back into letters (walls first, then gates). */
  breakAt: [0.75, 0.5, 0.25],
  /** Barrier column height under walls, gates and pillars (blocks). */
  barrierHeight: 7,
  /** Half width of the open doorway kept free of barriers in each gate (blocks). */
  doorHalf: 1.5,
  /** Gentle regeneration for allies inside: amount every N ticks. */
  regenAmount: 1,
  regenEvery: 40,

  // ---- timing (ticks)
  /** How long the finished sanctuary stands before it is unwritten (12 s active duration). */
  activeTicks: 240,
  /** Construction pacing: first launch tick and the gap between letters of each course. */
  pillarsAt: 24, pillarGap: 2,
  wallsAt: 42, wallGap: 3,
  bridgesAt: 68, bridgeGap: 3,
  ribsAt: 76, ribGap: 2,
  crownAt: 94,
  /** Ticks between pieces during the final unwriting. */
  unwriteGap: 1,
};
