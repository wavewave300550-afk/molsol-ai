/** DN05 Imperial Edict: The City That Sleeps Above the World -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN05 = {
  // ---- geometry (must match tools/assets/dn_city.py: R_QUARTER 120 units x scale 2 / 16 = 15 blocks)
  /** Height of the city's islands above the focus point (blocks). */
  cityHeight: 18,
  /** Distance of the four quarters from the central spire (blocks; fixed by the causeway model). */
  quarterDistance: 15,
  /** Small dream-logic height offsets of the four quarters (blocks). */
  quarterLift: [0, 0.6, -0.4, 0.4],
  /** Radius of the designated target area that constructs hunt in (blocks). */
  areaRadius: 22,
  /** How far the focus snaps to a hostile near the aim point. */
  focusSnap: 12,

  // ---- Phase I: The Gentle Arrival (allied defense)
  /** Fraction of incoming damage that still reaches protected allies (0.65 = 35% resistance). */
  wardFactor: 0.65,
  /** Allies within this distance of the focus (or the caster) are protected. */
  wardRadius: 34,
  /** Regeneration granted to allies when the city has assembled (ticks, amplifier). */
  regenTicks: 200,
  regenAmp: 0,

  // ---- Phase II: The Streets Begin to Move
  /** Maximum sky-stairs that descend beside allies as cover. */
  maxStairs: 3,
  /** Damage factor for allies sheltering under a stair pavilion (stacks with the ward). */
  coverFactor: 0.6,
  /** Radius around a pavilion that counts as cover, and that hostile projectiles dissolve in. */
  coverRadius: 3.5,
  /** Ticks between Phase II architectural attacks (balcony / rolling street, alternating). */
  attackEvery: 22,
  /** Telegraph lead time before a balcony lands (ticks). */
  balconyWarn: 20,
  balconyDamage: 11,
  balconyRadius: 2.8,
  /** Slowness ticks applied by a balcony impact. */
  balconySlowTicks: 50,
  streetDamage: 8,
  /** Rolling street: half-width of its crushing path, travel length and speed (blocks, blocks/tick). */
  streetWidth: 1.8,
  streetLength: 15,
  streetSpeed: 0.55,
  streetShove: 1.3,

  // ---- Phase III: The Nightmare Under the Facade (hunters)
  doorCount: 3,
  /** Passes each flying doorframe makes. */
  doorPasses: 2,
  doorDamage: 9,
  /** Radius of the doorway around its threshold that catches enemies. */
  doorReach: 1.8,
  /** Throw out the far side of the door (horizontal, vertical). */
  doorThrowH: 1.6,
  doorThrowV: 0.55,
  windowCount: 2,
  /** Stares per window before it shatters. */
  windowStares: 2,
  stareDamage: 7,
  /** Half-width of the stare line. */
  stareWidth: 1.3,
  stareSlowTicks: 40,
  glassDamage: 9,
  glassRadius: 2.6,
  corridorDamage: 10,
  /** Enemies within this distance of the corridor's end are caught when it snaps shut. */
  corridorCatch: 3.0,
  /** Ticks the corridor holds its catch (real restraint). */
  corridorHold: 50,
  stairfallDamage: 9,
  stairfallRadius: 2.2,
  fragmentCount: 4,
  biteDamage: 5,
  /** Fragment bites when the target is closer than this; otherwise it hops up to hopDistance. */
  biteRange: 1.9,
  hopDistance: 2.4,

  // ---- Phase IV: The Sleeping Collapse (finisher)
  waveRadius: 24,
  /** Each enemy struck takes waveBase + waveConcentrate / (enemies in area): the fewer sleepers, the deeper the dream. */
  waveBase: 16,
  waveConcentrate: 30,
  waveKnockH: 1.8,
  waveKnockV: 0.6,
};
