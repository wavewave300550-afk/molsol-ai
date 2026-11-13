/** DW02 Cherubic Testament: The Four Living Witnesses -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DW02 = {
  // ---- placement
  /** How far ahead of the caster (along the aim) the Cherubim manifests, in blocks. */
  standForward: 4.5,
  /** Sideways offset to the caster's left so the caster sees the witness in three-quarter view. */
  standSide: 5.5,
  /** Snap distance used to pick the fight centre around the aim point. */
  focusSnap: 12,

  // ---- FIRST - HUMAN WITNESS: sacred glyphs mark enemies
  /** Radius around the fight centre searched for enemies to mark. */
  markRadius: 16,
  /** Maximum enemies marked by the human witness. */
  maxMarks: 6,
  /** Small searing damage as a glyph is written onto an enemy. */
  markDamage: 2,
  /** Damage multiplier marked enemies suffer from the ox retaliation and the lion roar. */
  markBonus: 1.35,

  // ---- SECOND - OX WITNESS: wing-wall ward, absorb and retaliate
  /** Ticks the wing wall (real damage ward) holds (3.5 s). */
  wardTicks: 70,
  /** Allied players within this radius of the Cherubim are shielded (the caster always is). */
  wardRadius: 10,
  /** Total damage the wall can absorb before it cracks. */
  wardPool: 40,
  /** Fraction of incoming damage the wall stops (0 = all of it gets through, 1 = immune). */
  wardStrength: 1.0,
  /** Absorbed damage without a known attacker (falls, fire...) still charges the retaliation at this share. */
  envAbsorbShare: 0.5,
  /** Each hostile projectile dissolved by the wall adds this much to the stored retaliation. */
  projectileCharge: 2,
  /** Retaliatory shockwave: base damage + absorbed * scale, capped. */
  retaliateBase: 8,
  retaliateScale: 1.0,
  retaliateMax: 32,
  /** Shockwave radius around the Cherubim and its knockback. */
  retaliateRadius: 8,
  retaliateKnock: 1.8,
  retaliateLift: 0.5,

  // ---- THIRD - LION WITNESS: the sacred roar
  /** Damage of the roar (once per enemy). */
  roarDamage: 10,
  /** Reach of the roar cone and its half-angle in degrees. */
  roarRange: 16,
  roarHalfAngle: 55,
  /** Everything this close to the Cherubim is struck by the roar regardless of direction. */
  roarNear: 5,
  /** Knockback of the roar (horizontal / vertical). */
  roarKnock: 2.4,
  roarLift: 0.6,
  /** Extra push from the second and third ring of letters (no damage). */
  roarEchoPush: 0.8,
  /** Speed of the rings of letters (blocks per tick); the damage front travels with them. */
  roarSpeed: 0.8,
  /** Ticks between the three rings. */
  roarRingGap: 4,
  /** Height and forward offset of the lion's mouth relative to the Cherubim origin (blocks). */
  mouthHeight: 9.5,
  mouthForward: 1.8,

  // ---- FOURTH - EAGLE WITNESS: feather-blades from above
  /** Damage of one feather-blade. */
  bladeDamage: 14,
  /** Multiplier against marked enemies. */
  bladeMarkBonus: 1.5,
  /** Impact radius of a blade and its knockback. */
  bladeRadius: 2.2,
  bladeKnock: 0.6,
  /** Height above the target a blade forms at. */
  bladeHeight: 10,
  /** Ticks of telegraph (the warning sigil fills) before a blade dives. */
  bladeWarn: 20,
  /** Ticks a blade takes to fall from its height to the ground. */
  diveTicks: 5,
  /** Blades per wave (two waves). */
  bladesPerWave: 5,
  /** Radius around the fight centre in which the second wave may pick unmarked enemies. */
  bladeSearch: 16,
};
