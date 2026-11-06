// Gharvok balance & behaviour configuration. Every tunable number of the fight lives here.
// Distances are blocks, times are seconds, damage is half-hearts (player HP = 20).
// These are starting values, not proven balance.

export const GHARVOK_ID = "dragon_dominion:gharvok";
export const SIGIL_ID = "dragon_dominion:cliff_sigil";
export const REWARD_ID = "dragon_dominion:fractured_crownplate";

export const CONFIG = Object.freeze({
  health: {
    base: 500,
    perExtraPlayer: 120,
    maxPlayers: 4,
    // HP tiers live in the entity file as component groups (500 / 620 / 740 / 860); validate.mjs checks they match.
    participationRadius: 40, // players counted when the fight starts (fixed for the whole fight)
  },
  phases: {
    // phase 2 below 70 %, phase 3 below 35 % (each transition happens once per fight)
    thresholds: [0.7, 0.35],
    names: ["Territorial Guardian", "Cliff Hunter", "Desperate Predator"],
    gapAfterMove: [1.4, 0.9, 0.6], // decision delay after an attack's recovery
    cooldownScale: [1.0, 0.85, 0.72],
    runSpeed: [6.0, 7.0, 7.6], // blocks / second
    walkSpeed: 2.6,
    turnRate: [5, 6, 7], // degrees / tick while pursuing
  },
  detection: {
    radius: 24, // players closer than this wake it up
    targetRadius: 40, // how far it keeps chasing a target
    boundary: 44, // combat boundary around the spot where the fight began (leash)
    loseTargetAfter: 8, // seconds with no valid target before the boss resets
    retargetEvery: 8, // seconds between multiplayer target re-evaluations
    switchChance: 0.35, // chance to switch to another participant on re-evaluation
  },
  idle: {
    actEvery: [9, 16], // seconds between idle behaviours
    roarChance: 0.3,
  },
  attacks: {
    twin_claw: { damage: [6, 8], range: 6.2, halfAngle: 55, cooldown: 3.5, knockback: { h: 1.1, v: 0.35 } },
    crushing_charge: {
      damage: 10, knockback: { h: 2.6, v: 0.7 }, cooldown: 9, minRange: 8, maxRange: 26,
      speed: 0.85, // blocks / tick at full speed (17 b/s)
      accelTicks: 8, maxTicks: 40, hitRadius: 2.4, lockAt: 1.0, // seconds into the windup when the direction commits
      skullDamageOnWall: 45, // crown fracture points gained by hitting a wall
    },
    rudder_sweep: { damage: 8, radius: 8.5, minAngle: 60, cooldown: 6, knockback: { h: 1.8, v: 0.5 } },
    wing_pressure: {
      damage: [2, 4], range: 12, halfAngle: 65, cooldown: 12, knockback: { h: 3.2, v: 0.55 },
      pushRadius: 5, pushKnockback: { h: 1.8, v: 0.35 }, minPhase: 2,
    },
    cliff_dive: {
      damage: 12, outerDamage: 6, innerRadius: 3.5, outerRadius: 6.5, knockback: { h: 2.0, v: 0.8 }, cooldown: 16,
      minRange: 9, maxRange: 30, height: 9, warning: 1.1, // seconds the landing zone is marked before impact
      riseTime: 1.0, diveTime: 0.75, maxAirTime: 8, minPhase: 2,
    },
    skullbreaker: {
      damage: [14, 12], coreRadius: 3, waveDamage: 7, waveMax: 10, waveTicks: 10, cooldown: 11, range: 9,
      halfAngle: 45, warningFrom: 0.6, extraRecovery: 1.0, knockback: { h: 1.6, v: 0.9 }, minPhase: 3,
    },
    reposition_leap: { cooldown: 7, distance: 6, minPhase: 2 },
  },
  skull: {
    // crown fracture points: CRACKED at 60, BROKEN at 140
    cracked: 60,
    broken: 140,
    headRange: 3.6, // attacker distance to the head point that counts as a head hit
    headHalfAngle: 60, // attacker must be in front of the dragon
    headRate: 0.35, // points per damage of a head hit outside a vulnerable window
    vulnerableRate: 1.0, // points per damage of a head hit while stunned / exhausted / recovering
    staggerDamageBonus: 1.25, // damage taken while staggered once the crown is cracked
    brokenHeadBonus: 1.5, // head hits on the exposed weak point once the crown is broken
    impactStun: [2.4, 3.4, 3.4], // stagger seconds after a wall hit, by crown state
    brokenChargeScale: 0.8, // charge speed & damage once broken
    exhaustAfterMajor: [0, 0.35, 1.0], // chance to become exhausted after a major attack, by crown state
    exhaustSeconds: [2.4, 3.0, 3.6], // by phase
  },
  geometry: {
    // measured from the model at in-game scale 0.8 (see tools/gen_model.py)
    headForward: 4.3,
    headHeight: 3.3,
    mouthForward: 5.0,
    clawForward: 3.4,
    tailBack: 6.5,
    bodyRadius: 2.2,
  },
  reset: { walkBack: 8, invulnerable: true },
  rewards: { crownplates: 1, bonusIfBroken: 1, xpOrbs: 12, minPlayerDamageShare: 0.5 },
  summon: { distance: 12, cooldown: 5, searchRadius: 160 },
});

/** HP for a given participant count (1..4). */
export function hpFor(players) {
  const n = Math.max(1, Math.min(CONFIG.health.maxPlayers, players));
  return CONFIG.health.base + CONFIG.health.perExtraPlayer * (n - 1);
}
