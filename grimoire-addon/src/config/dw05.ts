/** DW05 Imperial Edict: The Threefold Heavenly Throne -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DW05 = {
  // ---- stage layout (blocks, relative to the fight centre; "forward" points away from the caster)
  /** Snap distance used to pick the fight centre around the aim point. */
  focusSnap: 14,
  /** Radius of the judged region: every search for enemies uses it. */
  regionRadius: 18,
  /** Seraph gate (lancet arch): forward distance and base height. */
  seraphGate: { forward: 21, side: 0, up: 12 },
  /** Cherub gate (tetrapylon): forward, sideways (negative = caster's left) and base height. */
  cherubGate: { forward: 15, side: -17, up: 4 },
  /** Ophanim gate (wheel portal): forward, sideways and centre height. */
  ophanGate: { forward: 15, side: 17, up: 9 },
  /** Phase II stations: the Seraph highest and centred, the Cherub in the middle on the left. */
  seraphStation: { forward: 12, side: 0, up: 18 },
  cherubStation: { forward: 7, side: -11, up: 8 },
  /** Where the Ophanim hovers while it scans (centre height above the ground). */
  ophanStation: { forward: 3, side: 6, up: 7 },
  /** Phase III posts around the throne: Seraph above it, Cherub and Ophanim at its flanks. */
  seraphPost: { forward: 16, side: 0, up: 27 },
  cherubPost: { forward: 9, side: -12, up: 8 },
  ophanPost: { forward: 9, side: 12, up: 7 },
  /** The empty throne: forward distance and dais height. */
  throne: { forward: 12, side: 0, up: 10 },
  /** Giant sentences: radius (blocks) and height of the three concentric bands. */
  sentences: [
    { radius: 8, up: 1.2 },
    { radius: 11, up: 5.5 },
    { radius: 14, up: 10 },
  ],

  // ---- PHASE I: the sentence pronounced over the region (a temporary law of judgment)
  /** Damage as the third sentence closes over every enemy in the region. */
  domainDamage: 3,
  /** Slowness the pronounced law lays on enemies (ticks, amplifier). */
  domainSlowTicks: 300,
  domainSlowAmp: 1,

  // ---- OPHANIM: detection, marking, directional sweeping passes
  /** Ticks for the scanning gaze to sweep a full circle. */
  scanTicks: 36,
  /** Maximum enemies the witnesses can mark. */
  maxMarks: 8,
  /** Searing damage as a mark is burned onto an enemy. */
  markDamage: 2,
  /** Number of straight sweeping passes and their timing. */
  passes: 3,
  lockTicks: 12,
  passTicks: 32,
  /** Half-length of a pass line through the marked (min / max). */
  passHalfMin: 8,
  passHalfMax: 13,
  /** Centre height of the wheel during a pass (its rim grazes the ground). */
  sweepAltitude: 5.6,
  /** Rim contact: half chord length, lateral reach and height (blocks). */
  rimChord: 4.2,
  rimHalfWidth: 2.0,
  rimHeight: 3.2,
  /** Rim damage per pass to unmarked / marked enemies (one hit per enemy per pass). */
  passDamage: 7,
  passMarkedDamage: 11,
  passKnock: 0.9,
  passLift: 0.35,

  // ---- CHERUBIM: four faces
  /** Human face: damage of the testament glyph written on each enemy (also marks the unmarked). */
  testamentDamage: 3,
  /** Ox face: ward that protects the caster and allied players within wardRadius of the caster. */
  wardRadius: 14,
  /** Total damage the ward can absorb before it breaks. */
  wardPool: 60,
  /** Fraction of incoming damage the ward stops while it holds (1 = everything). */
  wardStrength: 1.0,
  /** Lion face: roar damage (once per enemy), multiplier vs. marked, reach and cone width. */
  roarDamage: 12,
  markBonus: 1.35,
  roarHalfWidthNear: 2.5,
  roarHalfWidthFar: 6,
  roarKnock: 2.0,
  roarLift: 0.5,
  /** Blocks per tick the roar rings travel. */
  roarSpeed: 1.0,
  /** Eagle face: feather-blade damage, multiplier vs. marked, radius, height, telegraph and fall ticks. */
  bladeDamage: 14,
  bladeMarkBonus: 1.5,
  bladeRadius: 2.2,
  bladeHeight: 10,
  bladeWarn: 20,
  diveTicks: 5,
  bladesPerWave: 4,

  // ---- SERAPHIM: chants of judgment columns
  /** Damage of the columns of the first, second and third chant. */
  chantDamage: [9, 10, 12],
  /** Blast radius of a column (blocks). */
  columnRadius: 2.8,
  /** Maximum columns per chant. */
  maxColumns: 6,
  /** Ticks of warning before a column lands. */
  columnWarn: 16,

  // ---- PHASE III: the verdict
  /** Letters per verdict line (three lines are written before the throne). */
  lettersPerLine: 5,
  /** Height of the three verdict lines above the ground and their distance in front of the throne. */
  lineHeights: [20, 15.5, 11],
  lineForward: 4,
  /** Spacing of letters within a line (blocks). */
  letterSpacing: 3.8,
  /** Damage of one descending verdict letter and its blast radius. */
  verdictDamage: 22,
  verdictRadius: 3.5,
  /** Extra damage (once per enemy) for enemies that bear a sacred mark. */
  verdictMarkBonus: 14,
  /** An enemy can be struck by at most this many letters. */
  maxLetterHits: 2,
  verdictKnock: 1.4,
  verdictLift: 0.6,
  /** Telegraph radius of a designated hostile area (blocks); areas closer than this are merged. */
  areaRadius: 3.5,
  /** Ophanim's finishing gaze on every surviving marked enemy. */
  gazeDamage: 8,
  /** Seraph's finishing column over the densest area: damage and radius. */
  finalColumnDamage: 10,
  finalColumnRadius: 4,
  /** Ticks a letter needs to fall from its line to the ground, and the stagger between letters. */
  plungeTicks: 8,
  plungeStagger: 2,
};
