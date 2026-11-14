/** ED06 The World Before Names -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const ED06 = {
  // ---- domain
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  snap: 12,
  /**
   * The designated hostile zone (the Concord's target) is the enemy group, kept inside the stage in
   * front of the caster: at least / at most this far ahead (blocks) and within this many degrees of
   * the caster's facing.  Without enemies it sits `zoneDefault` blocks ahead.
   */
  zoneMinAhead: 14,
  zoneMaxAhead: 24,
  zoneMaxDeg: 26,
  zoneDefault: 16,
  /** Search radius for the enemy group and how far a member may be from the group's seed. */
  zoneSearch: 20,
  zoneGroup: 7,

  // ---- Phase I: The Four Ancient Heartbeats
  /** Each heartbeat shakes the domain: enemies within this radius of the zone take damage and are slowed. */
  beatRadius: 16,
  beatDamage: 2,
  beatSlowTicks: 40,
  beatSlowAmp: 1,
  beatKnock: 0.35,

  // ---- Phase II: The Sovereigns Awaken
  /** Nature Dragon: forefeet landing (damage, radius) and every footfall shockwave. */
  natureLandDamage: 8,
  natureLandRadius: 6,
  stepDamage: 3,
  stepRadius: 3.6,
  stepKnockH: 0.7,
  stepKnockV: 0.35,
  /** Heat Dragon charge: horn strike and body slam damage, lateral reach, shove. */
  hornDamage: 7,
  bodyDamage: 4,
  chargeHalfWidth: 2.6,
  chargeKnockH: 1.3,
  chargeKnockV: 0.45,
  /** Seconds enemies struck by the Heat Dragon keep burning. */
  burnSeconds: 3,
  /** Air Dragon's pull-up gust after its stoop over the hostile zone: damage, radius, knockback. */
  gustDamage: 5,
  gustRadius: 7,
  gustKnock: 1.0,

  // ---- Phase III: The Primordial Dominion
  /** Roots break out of the ground toward enemies: how many, how long they hold, damage at the bind. */
  maxRoots: 4,
  rootRadius: 18,
  rootHoldTicks: 70,
  rootDamage: 4,
  /** A root-bound pillar rises behind the first bound enemies (how many, damage when it erupts, barrier height). */
  maxPillars: 2,
  pillarDamage: 4,
  pillarBarrierHeight: 3,
  /** Neck lash: damage and radius of the low sweep in front of the Nature Dragon. */
  lashDamage: 8,
  lashRadius: 6,
  /** Superheated wave the Heat Dragon roars across the ground into the hostile zone (once in Phase III). */
  heatWaveDamage: 6,
  /** Ground vitrified behind each charge: a glass patch every N blocks, burning enemies on it. */
  glassEvery: 3.5,
  glassLifeTicks: 140,
  glassBurnDamage: 1,
  glassBurnRadius: 1.8,
  /** Standing stones within this distance of a charge turn to glowing glass and flash heat around them. */
  vitrifyReach: 4.6,
  vitrifyDamage: 4,
  vitrifyRadius: 3,
  /** Water & Ice Dragon: currents under its swim path shove enemies (once-per-pass damage). */
  currentReach: 3.5,
  currentShove: 0.55,
  currentDamage: 3,
  /** Crystalline bridges: enemies under a forming bridge are frost-bitten and slowed. */
  bridgeDamage: 4,
  bridgeWidth: 2.6,
  bridgeSlowTicks: 60,
  bridgeSlowAmp: 2,
  /** Air Dragon: aerial formations; their updraft lifts enemies below them, falling debris on release. */
  updraftRadius: 4.5,
  updraftDamage: 3,
  updraftLift: 0.9,
  updraftEvery: 30,
  debrisDamage: 6,
  debrisRadius: 5,

  // ---- Phase IV: The Fourfold Concord
  /** Radius of the Nature Dragon's enclosing pillar ring (barrier columns except two doorways). */
  ringRadius: 6,
  ringBarrierHeight: 4,
  /** Half-width of each doorway (degrees) on the Heat Dragon's lane. */
  doorwayDeg: 20,
  /** 1. Geological shockwaves: forelimb slam, the travelling quake, then three pulses from the pillars. */
  slamDamage: 10,
  slamRadius: 6,
  quakeDamage: 4,
  quakeRadius: 2.8,
  shockPulseDamage: [6, 6, 8],
  shockSlowTicks: 60,
  /** 2. Moving water and freezing: current damage, shove, then each crystallising ice layer. */
  concordCurrentDamage: 3,
  concordCurrentShove: 0.6,
  iceLayerDamage: 4,
  /** 3. Spiral of ice and wind: damage every N ticks while enemies are carried round, final lift. */
  spiralDamage: 2,
  spiralEvery: 8,
  spiralShove: 0.55,
  spiralLift: 0.22,
  spiralFinalLift: 0.95,
  /** 4. The Heat Dragon's final charge: run-up distance, horn hit, thermal detonation at the zone. */
  finalRunUp: 18,
  finalHornDamage: 10,
  detonationDamage: 22,
  detonationExtra: 2,
  detonationKnockH: 2.6,
  detonationKnockV: 0.9,
  detonationBurnSeconds: 5,
};
