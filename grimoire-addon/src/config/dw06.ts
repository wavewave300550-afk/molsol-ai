/** DW06 The Word Before Creation -- tunable gameplay values (cooldown 360 s lives in core/registry.ts). */
export const DW06 = {
  // ---- Phase I: the silence before all things
  /** Radius of the spell's domain around the focus point (blocks). */
  domainRadius: 19,
  /** How far the focus may snap from the aim point to an enemy. */
  focusSnap: 14,
  /** Most enemies that receive a sacred mark. */
  maxMarks: 10,

  // ---- Phase II: the first utterance (letters land as structures)
  /** Impact radius / damage / knockback of each structure kind when it lands:
   *  0 column, 1 arch (per pier), 2 bridge (swing sweep), 3 gate, 4 platform (shove only), 5 celestial. */
  landRadius: [2.6, 2.2, 7.5, 4.0, 3.2, 4.0],
  landDamage: [10, 8, 8, 12, 0, 7],
  landKnock: [1.2, 1.0, 1.6, 1.8, 1.0, 0.8],
  /** Columns and celestial formations land on an enemy if one is within this distance of their slot. */
  seekRadius: 9,
  /** Height (blocks) of barrier obstruction for columns, arch piers and gate pylons. */
  barrierHeight: [9, 8, 0, 10, 0, 0],
  /** Allies within this horizontal distance of a platform or bridge take reduced damage (cover). */
  coverRadius: 4.5,
  coverFactor: 0.6,
  /** Celestial formations pulse damage on enemies beneath them while they stand. */
  celestialPulseRadius: 4.5,
  celestialPulseDamage: 3,
  celestialPulseEvery: 20,

  // ---- Phase III: the seven laws
  /** I Containment: ring of written walls around the densest hostile region. */
  containRadius: 6,
  containPull: 13,
  containPullStrength: 0.9,
  /** II Station: how many structures slide to defend, and how far in front of the caster. */
  stationCount: 3,
  stationDistance: 6,
  /** III Direction: moving text walls -- damage, half-width of the wall, half-depth of the hit band. */
  directionDamage: 7,
  directionHalfWidth: 3.6,
  directionBand: 1.6,
  directionTicks: 40,
  /** IV Stillness: restraint duration, then lingering slowness (amplifier). */
  stillTicks: 60,
  stillSlowTicks: 100,
  stillSlowAmp: 3,
  /** V Refuge: allied zone radius, damage factor inside it, instant heal and regen per 2 s. */
  refugeRadius: 5,
  refugeFactor: 0.4,
  refugeHeal: 6,
  refugeRegen: 2,
  /** VI Sequence: each structure strikes the enemies around it in turn. */
  sequenceRadius: 4.5,
  sequenceDamage: 5,
  /** VII Judgment: radius of the designated finale region (and its telegraph). */
  finalRadius: 7,

  // ---- Phase IV: let it be written (descending lines)
  sweepDamage: 10,
  sweepHalfLength: 12,
  ringDamage: 10,
  ringMaxRadius: 17,
  latticeDamage: 9,
  latticeRadius: 2.4,
  spiralTickDamage: 3,
  spiralFinalDamage: 10,
  spiralPull: 0.55,
  /** Finale: immense white-gold formation. */
  finalDamage: 32,
  /** Extra finale damage for enemies judged by Law VII. */
  judgedBonus: 14,
  finalKnockback: 2.2,
};
