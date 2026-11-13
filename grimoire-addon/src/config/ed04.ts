/** ED04 Aether Raptor: Symphony of the Four Wings -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const ED04 = {
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  snap: 12,

  // ---- Stage I: The Fourfold Ascent
  /** Height of the parting cloud bank above the battlefield (blocks). */
  cloudHeight: 19,
  /** Height the dragon emerges at, and the start / end radius of its descending spiral. */
  descentHeight: 17,
  spiralR0: 4,
  /** Degrees the descent spiral turns before the first pass begins. */
  spiralTurn: 290,

  // ---- Stage II: The Skyborne Symphony (four passes along a pentagram, hairpin turns between)
  /** Radius of the pentagram the passes are drawn on (blocks around the focus). */
  passRadius: 9,
  /** Height of the dragon's flight origin above the ground during passes (body rides ~0.85 higher). */
  passHeight: 1.3,
  /** Sideways S-bend of each pass (blocks). */
  passBend: 2.0,
  /** Flight speed during passes and during the banked hairpin turns (blocks/second). */
  passSpeed: 24,
  turnSpeed: 20,
  /** Size of the climbing hairpin loop at each pentagram vertex (blocks). */
  hairpinSize: 2.6,
  hairpinLift: 3.0,
  /** Yaw change per tick above which the dragon banks into the turn. */
  bankRate: 2.0,
  /** Wing-slash: radius around the flight path, damage and sideways knockback of each pass. */
  slashRadius: 3.4,
  slashDamage: 7,
  slashKnockH: 1.1,
  slashKnockV: 0.35,
  /** Air-current ribbons: segment length (blocks) and how long each stays suspended (ticks). */
  ribbonSeg: 4.2,
  ribbonLife: 80,
  /** Wind vortex born where two live ribbons cross. */
  maxVortices: 4,
  vortexMerge: 3.5,
  vortexRadius: 4.2,
  /** Ticks a vortex stays active after spinning up, and how often it pulls / damages. */
  vortexTicks: 40,
  vortexEvery: 8,
  vortexDamage: 2.5,
  /** Horizontal pull strength toward the vortex eye per pulse. */
  vortexPull: 0.45,
  /** Final burst of each vortex: damage and upward launch. */
  vortexBurstDamage: 6,
  vortexLaunch: 0.9,

  // ---- Stage III: Supersonic Cadenza
  /** Hold point of the full-spread beat: height above ground and distance behind the formation. */
  holdHeight: 13,
  holdBack: 15,
  climbSpeed: 20,
  holdTicks: 18,
  /** Dive: duration (ticks), where it bottoms out before the focus and how far it runs past it. */
  diveTicks: 20,
  diveLead: 7,
  diveRun: 9,
  /** Direct contact of the high-speed dive. */
  diveContactRadius: 2.6,
  diveDamage: 10,
  diveKnockH: 1.4,
  diveKnockV: 0.5,
  /** Delayed shockwaves along the route: count, radius, damage, timing and outward knockback. */
  shockCount: 5,
  shockRadius: 3.6,
  shockDamage: 8,
  /** Ticks after the dragon passes before the first shock detonates, and the gap between shocks. */
  shockDelay: 10,
  shockStagger: 4,
  shockKnockH: 1.9,
  shockKnockV: 0.6,
  /** An enemy can be struck by at most this many shockwaves. */
  maxShockHits: 2,
  /** Braking flare, landing and the perched beat before the dissolution (ticks). */
  flareTicks: 12,
  landTicks: 20,
  perchTicks: 8,
};
