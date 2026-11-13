/** DW01 Seraphic Litany: The Sixfold Sanctus -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DW01 = {
  /** Radius around the focus point in which enemies are judged. */
  radius: 14,
  /** Maximum enemies struck by each chant. */
  maxTargets: 6,
  /** Damage of the first, second and third judgment column. */
  chantDamage: [8, 9, 11],
  /** Blast radius of a judgment column (blocks). */
  columnRadius: 2.6,
  /** Extra damage for an enemy struck by all three judgments. */
  verdictBonus: 16,
  verdictRadius: 3.4,
  verdictKnockback: 1.6,
  /** Height of the Seraphim above the battlefield and how far beyond the focus it hovers. */
  hoverHeight: 8,
  hoverBack: 6,
  /** Ticks from a chant gesture to its columns landing (the warning window). */
  warnTicks: 16,
};
