/** DW03 Ophanim: The Unblinking Judgment -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DW03 = {
  // ---- survey
  /** Radius of the rotating-sector scan around the focus point (blocks). */
  surveyRadius: 18,
  /** Ticks for the scan beam to complete one full revolution. */
  scanTicks: 36,
  /** Scan pings per revolution (one per sector). */
  scanSectors: 6,
  /** Maximum enemies the Ophanim can mark. */
  maxMarks: 8,
  /** Height of the wheel centre above the focus while it arrives and surveys. */
  hoverHeight: 9,

  // ---- sweeping passes
  /** Number of geometric passes (polygon, star, figure-eight, polygon...). */
  passes: 3,
  /** Ticks of route telegraph + repositioning before each pass (the warning window). */
  lockTicks: 12,
  /** Ticks the wheel needs to run one whole route. */
  passTicks: 36,
  /** Height of the wheel centre above the ground during a pass: the rim grazes the ground. */
  sweepAltitude: 5.6,
  /** Half-length along the path of the rim's ground-contact chord (blocks). */
  rimChord: 4.2,
  /** Lateral reach of the rim from the wheel plane (blocks, enemy hitbox slack included). */
  rimHalfWidth: 2.0,
  /** Height above the ground the rim reaches (blocks). */
  rimHeight: 3.2,
  /** Route size limits around the marked enemies (blocks). */
  routeMinRadius: 5,
  routeMaxRadius: 11,
  /** Route radius used when nothing is marked. */
  noTargetRadius: 6,
  /** Rim damage per pass to unmarked / marked enemies (one hit per enemy per pass). */
  damage: 6,
  markedDamage: 10,
  /** Sideways knockback away from the wheel plane, and lift. */
  knockback: 0.9,
  lift: 0.35,

  // ---- verdict
  /** Final judgment damage on every surviving marked enemy. */
  verdictDamage: 12,
  /** Radius of the verdict shock around the wheel (pushes unmarked enemies). */
  verdictPushRadius: 5,
  verdictKnockback: 1.2,
};
