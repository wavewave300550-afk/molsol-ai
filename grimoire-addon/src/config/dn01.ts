/** DN01 Reverie Procession: Parade of the Sleeping Moon -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN01 = {
  // ---------------------------------------------------------------- targeting / the dream-road
  /** Radius around the focus point in which the procession looks for enemies. */
  radius: 14,
  /** How far from the aim point the spell snaps onto the nearest hostile. */
  snap: 10,
  /** Road starts this many blocks behind the caster, this high above the caster's feet. */
  startBehind: 3,
  startHeight: 2.5,
  /** Forward reach of the road end (blocks from the caster), clamped to this range. */
  minReach: 9,
  maxReach: 22,
  /** The road ends this many blocks short of the focus, this high above the ground there. */
  endBack: 4,
  endHeight: 1.2,
  /** Height of the road's arc above the straight line, and its sideways S-curve amplitude. */
  apex: 8,
  curve: 3.5,
  /** Desired spacing of road segments (blocks) and the maximum number of segments. */
  segSpacing: 3.3,
  maxSegments: 12,
  /** Ticks between successive segments unrolling / rolling up. */
  unrollStep: 2,

  // ---------------------------------------------------------------- the procession
  /** Ticks at which the horse, stag, bird and doll appear at the road's gate. */
  spawnAt: [12, 20, 28, 36],
  /** Ticks each creature holds at the gate (arrival animation) before it starts to walk. */
  gateHold: 14,
  /** Parade speed along the road (blocks per second). */
  paradeSpeed: 14,

  // ---------------------------------------------------------------- stacking bonus (the core mechanic)
  /** Bonus damage per different creature that already struck the same enemy (2nd hit +k, 3rd +2k, 4th +3k). */
  stackBonus: 3,
  /** Share of the stack bonus a creature gets on its own repeated hits (doll pulses, later swoops). */
  repeatBonusShare: 0.35,
  /** Extra burst when all four creatures have struck the same enemy ("full moon"). */
  fullMoonBonus: 8,
  fullMoonRadius: 2.5,
  /** Height of the crescent mark above a struck enemy. */
  markHeight: 2.6,

  // ---------------------------------------------------------------- porcelain horse: straight gallop line
  horseDamage: 7,
  /** Length of the charge line and gallop speed (blocks / second). */
  horseLength: 16,
  horseSpeed: 16,
  /** Half-width of the line: enemies this close to the horse are trampled (pierce). */
  horseHitRadius: 1.9,
  horseKnockback: 1.3,
  horseLift: 0.45,

  // ---------------------------------------------------------------- mist-glass stag: three bounding impacts
  stagDamage: 6,
  stagBounds: 3,
  /** Landing blast radius (each landing is telegraphed). */
  stagRadius: 2.6,
  /** Peak height of a bound above the straight line (blocks) plus a share of its length. */
  stagHop: 3.5,
  stagHopPerBlock: 0.15,
  /** Without targets the stag bounds this far each time. */
  stagIdleStride: 4.5,

  // ---------------------------------------------------------------- curtain-winged bird: swooping arcs
  birdDamage: 5,
  birdSwoops: 3,
  /** Enemies this close to the bird during the low part of a swoop are struck. */
  birdHitRadius: 2.0,
  /** Height the bird climbs back to between swoops, and its skim height. */
  birdAir: 6,
  birdSkim: 1.1,
  /** A second target this close to the first is included in the same swoop. */
  birdPairRange: 7,

  // ---------------------------------------------------------------- floating star doll: drift then rhythmic starburst
  /** Ticks the doll takes to drift (in hesitant steps) to its pulse point. */
  dollDrift: 28,
  /** Syncopated pulse offsets in ticks (short-short-long-short-long). */
  dollPulses: [0, 6, 16, 22, 34],
  dollDamage: 2.5,
  dollRadius: 4.5,
  /** Hover height of the doll above the ground at its pulse point. */
  dollHover: 1.4,
  /** Slowness applied by each pulse (ticks, amplifier). */
  dollSlowTicks: 30,
  dollSlowAmp: 1,

  // ---------------------------------------------------------------- staging
  /** The Sleeping Moon hangs this far above the road's apex. */
  moonAbove: 6,
  /** Light blocks placed every n-th road segment while the road exists. */
  lightEvery: 3,
};
