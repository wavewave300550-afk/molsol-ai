/**
 * Nomos - per-attack tuning. Beat timings live in shared/nomos.timings.json
 * (shared with the animations). Damage is design damage in health points
 * before difficulty and mitigation; distances are blocks; times are ticks.
 */
export const NOMOS = {
  move: {
    p1: { speed: 0.07, turn: 3.2, near: 6.5, far: 12.5, station: 9 },
    p2: { speed: 0.1, turn: 4.6, near: 6, far: 13, station: 9 },
  },
  /** Walking speed (blocks/tick) and reaction time assumed by the safe-route validator. */
  fair: { walk: 4.317 / 20, reaction: 8 },
  meridian: { cooldown: [150, 120] as [number, number], damage: 14, halfWidth: 1.4, fan: 60 },
  shear: {
    cooldown: [230, 200] as [number, number], damage: 12, halfWidth: 1.2,
    /** Bands start this far from the arena centre and stop this far from it. */
    from: 15, to: 4.2, speed: 0.18, farCentre: 60, spread: 32,
  },
  borders: {
    cooldown: [340, 300] as [number, number], damage: 6, halfWidth: 0.6, length: 24, slowTicks: 40,
    hitEvery: 4, redrawEvery: 20,
  },
  gate: {
    cooldown: [260, 210] as [number, number], damage: 15, radius: 5, offset: 3.5, minJump: 6,
    crossHalfWidth: 1.6, crossOffset: 4.5,
  },
  darts: { cooldown: [200, 170] as [number, number], damage: 9, speed: 0.9, range: 34, radius: 0.7, height: 1.4 },
  folded: { cooldown: [220, 190] as [number, number], damage: 13, width: 2.5 },
  recalc: { cooldown: [780, 720] as [number, number], damage: 18, cell: 10, stripe: 5, inner: 4, ring: [9, 14] as [number, number] },
  poise: { threshold: 110, window: 100, stagger: 36, lockout: 420 },
};
