/**
 * Vesperra - per-attack tuning. Beat timings live in shared/vesperra.timings.json
 * (shared with the animations); everything else a designer would touch is here.
 * Damage is design damage in health points before difficulty and mitigation.
 */
export const VESPERRA = {
  move: {
    p1: { speed: 0.085, turn: 4.5, hold: 5.2, chase: 6.4 },
    p2: { speed: 0.15, turn: 7.5, hold: 3.6, chase: 4.6 },
  },
  scythe: { cooldown: [150, 120] as [number, number], damage: 14, castDamage: 12, thrustDamage: 15, reach: 7.2, halfAngle: 80 },
  procession: { cooldown: [190, 160] as [number, number], damage: 13, length: 15, halfWidth: 1.25, spacing: 2.6, fan: 28 },
  molting: { cooldown: [210, 170] as [number, number], damage: 11, plates: 8, speed: 0.65, range: 13, radius: 1.05 },
  cocoon: { cooldown: [300, 250] as [number, number], damage: 12, radius: [4.6, 5.2], anchors: [3, 4], slowTicks: 60 },
  feint: { cooldown: [330, 280] as [number, number], damage: 17, reach: 8.5, halfWidth: 1.6, exposedBonus: 1.25 },
  heirs: { cooldown: [520, 420] as [number, number], max: 2, lifetime: 500, bite: 5, biteRange: 1.8, biteWarn: 18, biteCooldown: 60, speed: 0.17, guardRange: 3.0 },
  coronation: { cooldown: [760, 700] as [number, number], damage: 16, halfWidth: 1.3 },
  armor: {
    /** Plate health: left shell, right shell, crown/face shield. */
    plate: { l: 70, r: 70, c: 55 },
    /** Share of a hit that reaches the boss through an intact plate (phase I / phase II). */
    through: [0.35, 0.55],
    /** Multiplier on an exposed region. */
    exposed: [1.4, 1.5],
    /** Multiplier for hits that land elsewhere on the carapace. */
    body: [0.75, 1.0],
    /** An Heir standing guard at a flank reduces the exposed multiplier to this. */
    guarded: 0.8,
    breakStagger: 34,
  },
};
