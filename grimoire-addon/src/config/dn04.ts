/** DN04 Lullaby and Scream -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN04 = {
  // ---- timing (the music is cut into 2.0 s phrases; every phase starts on a phrase downbeat)
  /** Active duration in seconds: from the cast until the tapestry starts to unravel.  Rounded down to whole phrases. */
  activeSeconds: 12,
  /** Length of one lullaby phrase in ticks (the sound clips are composed to exactly 2.0 s). */
  phraseTicks: 40,
  /** Phrases of pure lullaby before dissonance creeps in. */
  lullabyPhrases: 1,
  /** Phrases of creeping dissonance (one faint wave) before the full dual composition. */
  dissonancePhrases: 1,

  // ---- tapestry placement
  /** How far in front of the caster and how high above their feet the tapestry hovers. */
  hoverForward: 2.6,
  hoverHeight: 2.4,
  /** Fraction of the remaining distance the tapestry closes each tick while following the caster. */
  followLerp: 0.12,

  // ---- dream half: ribbons, healing, resistance
  /** Players within this radius of the caster are wrapped in dream ribbons (the caster always is). */
  allyRadius: 10,
  /** A wrapped ally further than this from the caster loses their ribbon. */
  ribbonLoseRadius: 15,
  /** Maximum allies wrapped at once. */
  maxAllies: 6,
  /** Ticks between checks for newly arrived allies. */
  allyCheckEvery: 20,
  /** Ticks a ribbon takes to spool from the tapestry to an ally. */
  ribbonTravelTicks: 16,
  /** HP restored to every wrapped ally on each heal pulse (does not cost the caster anything). */
  healAmount: 2,
  /** Ticks between heal pulses (one per phrase, on the second bar's downbeat). */
  healEvery: 40,
  healOffset: 20,
  /** Fraction of incoming damage that still reaches a wrapped ally (0.65 = 35 % resistance). */
  wardFactor: 0.65,

  // ---- nightmare half: scream waves
  /** Final radius of a full scream wave (blocks) and the radius it starts from. */
  waveRadius: 10,
  waveStartRadius: 1.2,
  /** Ticks for the wave front to travel from start to final radius (damage lands as the front arrives). */
  waveTicks: 16,
  /** Damage of a full scream wave. */
  waveDamage: 6,
  /** The first, faint wave of the dissonance phase: radius and damage multipliers. */
  faintRadius: 0.65,
  faintDamage: 0.5,
  /** Ticks from the scream gesture to the wave leaving the tapestry (matches the scream animation peak). */
  screamLead: 6,
  /** Slowness applied by each wave. */
  slowTicks: 60,
  slowAmp: 1,
  /** Weakness applied by each wave (enemies hit less hard while disoriented). */
  weaknessTicks: 80,
  weaknessAmp: 0,
  /** Disorientation: ticks the enemy's facing is forcibly spun, degrees per tick, and the sideways stagger. */
  disorientTicks: 14,
  disorientSpin: 32,
  disorientShove: 0.55,
  /** Maximum enemies one wave can strike. */
  maxTargets: 16,
};
