/**
 * Cantor XIII - per-attack tuning. Beat timings live in shared/cantor.timings.json
 * (shared with the animations); everything else a designer would touch is here.
 * Damage is design damage in health points before difficulty and mitigation.
 * Speeds are blocks per tick; a walking player covers about 0.216.
 */
export const CANTOR = {
  move: {
    p1: { speed: 0.06, turn: 2.6, home: 5, settle: 2.5 },
    p2: { speed: 0.085, turn: 3.6, home: 6.5, settle: 1.5 },
  },
  downbeat: {
    cooldown: [70, 60] as [number, number], damage: 13, secondDamage: 6, speed: 0.3, thickness: 1.6, minDoor: 3.4,
    /** Safe doors in the ring: count, width (degrees). */
    gaps: 3, gapWidth: 40,
    /** Phase II second ring: doors turned by this much and this wide, so the doors overlap. */
    secondShift: 20, secondWidth: 44,
  },
  counterpoint: {
    cooldown: [220, 190] as [number, number], damage: 9, speed: [0.3, 0.34], thickness: 1.4,
    doorHalf: 2.5, doorSpacing: 13,
  },
  aria: {
    cooldown: [160, 130] as [number, number], damage: 9, speed: 0.55, range: 20, radius: 0.55, warn: 24,
    fans: [[-40, -20, 0, 20, 40], [-30, -10, 10, 30]],
    /** Phase II positional wave: a half ring towards the aim with two doors. */
    waveSpeed: 0.3, waveReach: 16, waveArc: 200, waveGap: 34,
  },
  heldNote: {
    cooldown: [200, 170] as [number, number], damage: 18, echoDamage: 14, halfAngle: 42, echoHalf: 30,
    inner: 3.2, range: 15,
  },
  silent: {
    cooldown: [300, 260] as [number, number], damage: 14, secondDamage: 5, speed: 0.4, thickness: 1.6, gaps: 4, gapWidth: 34,
    secondShift: 14, secondWidth: 40, minDoor: 3.4,
    /** Rhythmic attacks that must have been played since the last Silent Measure. */
    needsRhythm: 2,
  },
  twin: {
    cooldown: [480, 400] as [number, number], damage: 9, radius: 4.5, warn: 34,
    intervals: [[70, 90], [50, 70]], lifetime: [320, 400], firstDelay: 20, health: 24,
    /** Destroying both bells staggers Cantor for this many ticks. */
    staggerTicks: 40,
  },
  requiem: {
    cooldown: [720, 680] as [number, number], damage: 17,
    /** Floor ring radii (they match the copper rings laid into the basilica floor). */
    inner: 6, middle: 12, outer: 13, far: 9,
  },
};
