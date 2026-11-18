/**
 * Orison - per-attack tuning. Beat timings live in shared/orison.timings.json
 * (shared with the animations); everything else a designer would touch is here.
 * Damage is design damage in health points before difficulty and mitigation.
 */
export const ORISON = {
  move: {
    /** Phase I walks in a tick-tock: `stride` ticks moving, `rest` ticks held. */
    p1: { speed: 0.11, turn: 5, hold: 8, chase: 9.5, stride: 12, rest: 8 },
    /** Phase II: the shadow walks first and the body follows the same path `lead` ticks later. */
    p2: { speed: 0.15, turn: 7, hold: 6.5, chase: 7.5, lead: 10 },
  },
  history: {
    /** Samples used by the attacks, [phase I, phase II]: 5 s and 10 s of movement. */
    window: [25, 50] as [number, number],
  },
  echo: { cooldown: [170, 140] as [number, number], damage: 12, radius: [1.6, 1.8] as [number, number], minSpacing: 2.0 },
  verdict: {
    cooldown: [150, 120] as [number, number], damage: 16, inner: 2.2, outer: 11, arc: [140, 200] as [number, number],
    /** Angular half-width of the blade, degrees. */
    blade: 9,
    /** Phase II return swing covers this outer band instead. */
    returnBand: [5.5, 14] as [number, number],
  },
  wound: { cooldown: [200, 170] as [number, number], damage: 13, radius: 2.2 },
  drain: {
    cooldown: [420, 360] as [number, number], count: [2, 3] as [number, number], radius: 4.0,
    lifetime: [240, 300] as [number, number],
    /** Ticks after appearing before an hourglass starts to act. */
    arm: 30,
    pulseWarn: 40, pulseEvery: 70, damage: 8,
    /** Slowness is re-applied every `slowEvery` ticks for `slowTicks`, only to players inside the area. */
    slowTicks: 30, slowEvery: 10, slowAmp: 1,
    /** Destroying an hourglass jams Orison for this long. */
    breakStagger: 36,
  },
  witness: { cooldown: [190, 150] as [number, number], damage: 15, radius: [3.0, 2.6] as [number, number], samplesBack: 5 },
  exchange: { cooldown: [260, 220] as [number, number], arrive: 15, depart: 8, arriveRadius: 4.5, departRadius: 3.0, offset: 3.5, minJump: 6 },
  hour: { cooldown: [780, 720] as [number, number], damage: 18, band: 4, wedges: [8, 12] as [number, number] },
};
