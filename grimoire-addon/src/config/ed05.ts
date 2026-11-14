/**
 * ED05 Imperial Edict: The Chronicle of Buried Kingdoms -- tunable gameplay values
 * (cooldown lives in core/registry.ts).  Times are seconds from the cast unless noted;
 * animation lengths come from src/spells/_ed05_assets.ts (generated with the models).
 */
export const ED05 = {
  /** How far from the aim point the monument snaps onto the nearest enemy. */
  focusSnap: 14,
  /** Radius around the monument in which the spell looks for enemies. */
  areaRadius: 22,

  // ---- Phase I: The Buried Testament
  /** Distance of the four rise sites from the centre (they sit on the diagonals of the caster's view). */
  riseRadius: 11,
  /** First inscription column, and the stagger between the four sites. */
  inscribeAt: 0.2,
  riseStagger: 0.25,
  /** Tablets break out of the ground this long after their inscription began to fall. */
  riseDelay: 1.8,
  /** Rising slab: shove + damage around its site when it breaks the surface. */
  riseDamage: 5,
  riseRadiusHit: 4.0,
  riseKnock: 1.3,
  /** Tablets lift and orbit into the memorial from this time, over gatherTime seconds. */
  gatherAt: 5.0,
  gatherTime: 3.0,
  /** Height of the tablets' lower edge above the ground in the memorial (blocks). */
  memorialHeight: 9.5,
  /** Total turn of the monument while it assembles and turns (degrees) and when it halts. */
  memorialTurn: 225,
  haltAt: 8.8,
  /** The memorial locks: grinding shock under the monument. */
  lockDamage: 7,
  lockRadius: 10,
  lockSlowTicks: 50,
  lockSlowAmp: 1,

  // ---- Phase II: The Fossils That Remember
  /** Emergence of each skeleton (nature, heat, tide, air); its tablet awakens awakenLead earlier. */
  emergeAt: { nature: 9.0, heat: 9.8, tide: 10.6, air: 11.4 } as Record<string, number>,
  awakenLead: 0.7,
  /** Where the skeletons land, measured from the monument centre (blocks, outward from their tablet). */
  landDistance: { nature: 12.5, heat: 11.5, tide: 10.5 } as Record<string, number>,

  // Nature (titanosaur): forelimb slam with radiating stone spikes, then a low neck sweep
  slamDamage: 14,
  slamRadius: 4.2,
  slamKnock: 1.4,
  /** Spikes rise along this many shock lines from the slam point, spikesPerLine each, spaced (blocks). */
  slamLines: 3,
  spikesPerLine: 3,
  spikeSpacing: 2.6,
  spikeFirst: 3.0,
  spikeDamage: 7,
  spikeRadius: 1.9,
  spikeLift: 0.7,
  /** Neck sweep: frontal sector (half angle, degrees) between minReach and maxReach blocks of the body. */
  sweepDamage: 12,
  sweepHalfAngle: 75,
  sweepMinReach: 5,
  sweepMaxReach: 19,
  sweepKnock: 1.6,

  // Heat (carnotaur): two telegraphed charges that leave burning trackways
  /** Ticks the lane is shown before each charge. */
  laneWarn: 1.0,
  /** Half length of each lane through the centre region (blocks). */
  laneReach: 11,
  /** Second lane passes this far beside the centre. */
  laneOffset: 3,
  chargeDamage: 11,
  chargeRadius: 2.3,
  chargeKnock: 1.5,
  /** Burning trail: damage every burnEvery ticks to enemies within burnRadius of the scorched track. */
  burnDamage: 2.5,
  burnEvery: 10,
  burnRadius: 1.6,
  burnSeconds: 3.0,
  burnFireSeconds: 3,

  // Tide (spinosaur): tail lash and sail flare throwing fans of ice crystals
  tideWalk: 1.2,
  fanDamage: 10,
  /** Crystal fans: size multiplier (1 = 2.9 block reach), sector half angle, slowness. */
  fanSize: 2.6,
  fanHalfAngle: 55,
  fanSlowTicks: 60,
  fanSlowAmp: 2,
  flareDamage: 11,

  // Air (microraptor): three low sweeps; each downstroke sends a wind shockwave ring
  flySpeed: 17,
  passRadius: 13,
  passHeight: 4.0,
  cruiseHeight: 8.0,
  ringDamage: 6,
  ringRadius: 3.8,
  ringKnock: 1.5,
  /** Rings only fire when the raptor is within this horizontal distance of the centre. */
  ringReach: 11,

  // ---- Phase III: The Eternal Imprint
  phase3At: 22.6,
  /** Fan formation above the battlefield: radius from the centre, lower-edge height and fan angles. */
  fanRadius: 10,
  formationHeight: { nature: 15, heat: 13, tide: 13, air: 15 } as Record<string, number>,
  formationAngle: { heat: 54, nature: 18, air: -18, tide: -54 } as Record<string, number>,
  formationTime: 2.0,
  /** Each imprint lands at these times; the projection warns warnTime seconds before. */
  projectAt: { nature: 25.0, heat: 26.6, tide: 28.2, air: 29.8 } as Record<string, number>,
  projectWarn: 1.2,
  allAt: 31.6,
  /** Imprint size multiplier (1 = 15.6 x 11.7 blocks). */
  imprintSize: 1.0,
  /** Nature: root-and-stone eruption along the sauropod outline. */
  p3SpikeDamage: 12,
  p3SpikeRadius: 2.2,
  /** Heat: horned heat-brand burns for brandSeconds. */
  brandDamage: 4,
  brandEvery: 8,
  brandRadius: 2.2,
  brandSeconds: 2.0,
  brandFireSeconds: 4,
  /** Tide: sail-shaped ice fan. */
  p3FanDamage: 15,
  p3FanSize: 4.2,
  p3FanSlowTicks: 80,
  p3FanSlowAmp: 3,
  /** Air: four-winged gale. */
  galeDamage: 12,
  galeRadius: 4.5,
  galeKnock: 2.0,
  galeLevitate: 16,
  /** All four together. */
  finaleDamage: 22,
  finaleRadius: 9,
  finaleKnock: 1.8,
  fractureAt: 33.8,
  endAt: 36.2,

  /** Seconds between replays of the museum hush bed. */
  hushEvery: 4.5,
};
