/** ED01 Genesis Colossus: The Walking Continent -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const ED01 = {
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  focusSnap: 12,
  /** Heading of the walk relative to the caster: mostly across the view (profile), slightly away. */
  walkAcross: 0.8,
  walkAway: 0.6,
  /** Degrees the dragon's heading curves over its walk (the "short arc"). */
  walkTurnDeg: 20,

  // ---- Stage I: Awakening of the Living Earth
  /** Damage and radius when the emerging body lands its forefeet. */
  landDamage: 6,
  landRadius: 5,
  /** Geological shockwave of every footfall: damage, radius, horizontal / vertical knockback. */
  stepDamage: 3,
  stepRadius: 3.4,
  stepKnockH: 0.7,
  stepKnockV: 0.35,
  /** Size (grimoire:size) of the footfall fissure decal (radius = 2 * size blocks). */
  stepQuakeSize: 1.5,

  // ---- Stage II: The Forest Upon Its Back
  /** Radius around the focus in which roots seek enemies, and how many they take. */
  rootRadius: 14,
  maxRoots: 6,
  /** Decorative roots sent toward the focus when nobody is there. */
  idleRoots: 4,
  /** Root size range (size 1 = 6 blocks long). */
  rootMinSize: 0.45,
  rootMaxSize: 2.6,
  /** Enemies clustered within this distance share one pillar ring; maximum rings. */
  groupRadius: 5,
  maxRings: 2,
  /** Pillars per ring, ring radius limits (blocks) and barrier height of each pillar. */
  pillarsPerRing: 5,
  ringMin: 4,
  ringMax: 7,
  pillarBarrierHeight: 4,
  pillarSize: 0.95,

  // ---- Stage III: Continental Descent
  /** Forelimb slam: radius (also the telegraph), damage, knockback (a jolt; the roots still hold). */
  slamRadius: 7,
  slamDamage: 12,
  slamKnockH: 0.4,
  slamKnockV: 0.55,
  /** Strata structures erupting: damage and radius per structure. */
  strataDamage: 8,
  strataRadius: 4,
  /** Each root tearing out of the ground: damage around its grip and upward throw. */
  rootDamage: 8,
  rootEruptRadius: 2.6,
  rootKnockV: 0.9,
  /** Each toppling pillar crushes enemies within this width of its fall line. */
  pillarDamage: 6,
  pillarWidth: 2.2,
  /** Ring convergence: the finishing blow at each ring centre, with strong knockback. */
  convergeDamage: 9,
  convergeKnockH: 2.4,
  convergeKnockV: 0.8,
};
