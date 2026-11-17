/** DN02 Nightmare Intrusion: The Guest Behind the Door -- tunable gameplay values (cooldown lives in core/registry.ts). */
export const DN02 = {
  /** How far from the aim point the spell looks for a victim when nothing is under the crosshair (blocks). */
  snapRadius: 10,
  /**
   * Distance from the door plane to the victim's grip point (blocks).  Must match GRAB_Z in
   * tools/assets/dn_guest.py (56/16): the Guest's stretched hands close exactly there.
   */
  standoff: 3.5,
  /** Where the drag ends, measured from the door plane (blocks).  Matches PULL_Z (18/16) in dn_guest.py. */
  pullStop: 1.125,
  /** If the victim has wandered farther than this from the grip point when the hands close, the Guest grasps air. */
  grabRange: 2.4,
  /**
   * The Guest only reaches for someone who is really there: an enemy within this distance of the grip
   * point when it has leaned out of the doorway.  It is pulled into the closing hands.
   */
  reachRadius: 5.5,
  /** With nobody in reach the Guest waits this long at the threshold for someone to come close, then goes back inside. */
  waitSeconds: 2.5,
  /** Slowness amplifier while the door creaks open (the dread beat) and while the arms reach. */
  dreadSlowAmp: 1,
  reachSlowAmp: 3,
  /** Squeeze damage dealt every `squeezeEvery` ticks while the victim is held (restraint lasts 2.4 s). */
  squeezeEvery: 12,
  squeezeDamage: 3,
  /** The slam: radius around the drag end point, damage to everything inside, and the finisher bonus for the held victim. */
  slamRadius: 3.0,
  slamDamage: 16,
  finisherBonus: 14,
  /** Knockback away from the door (horizontal strength, lift). */
  slamKnock: 2.4,
  slamLift: 0.55,
};
