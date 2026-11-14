import { Actor } from "../lib/scene";
import { V3, angleDelta, clamp, lerp, spline, yawOf } from "../lib/vec";

/**
 * How a creature travels: the looping states that carry it and the speed (blocks / s) each loop was
 * authored for (its feet stay planted only at that speed), the states whose own animation travels or
 * must never be replaced (one-shots: arrivals, skids, attacks...), the in-place turn states, and idle.
 */
export interface Gaits {
  gaits: { state: number; speed: number }[];
  free: number[];
  /** in-place turns: left / right (right = yaw increasing), shown above `above` deg / s */
  turn?: { left: number; right: number; above: number };
  idle: number;
  /** a swimmer also travels when it only rises or sinks (its speed is measured in 3D) */
  swims?: boolean;
}

/**
 * ED06 choreography helpers: a timeline of motion segments per dragon (script-moved actors),
 * arc-length paths so creatures travel at their species' documented speeds, a frame of reference
 * anchored on the caster (the stage), and a tiny deterministic hash for scattering ambient effects.
 */

/** One stretch of motion between absolute scene ticks.  `at(t)` gives the position at tick t. */
export interface Seg {
  from: number;
  to: number;
  at: (t: number) => V3;
  /** Fixed facing for the whole segment (else the facing follows the motion). */
  yaw?: number | ((t: number) => number);
  /** Optional tag so per-tick hooks know what the creature is doing. */
  tag?: string;
}

export class Mover {
  segs: Seg[] = [];
  cursor: number;
  last: V3;
  lastYaw: number;
  /** Signed, smoothed yaw rate (deg / tick) -- used by flyers to pick banking states. */
  yawRate = 0;
  /** Optional cap on how fast the facing may change (deg / tick, 0 = none): sharp path corners become turns. */
  maxTurn = 0;
  private ySmooth: number | undefined;
  /** Measured horizontal and 3D speed (blocks / s) and turn rate (deg / s, + = yaw increasing). */
  speed = 0;
  speed3 = 0;
  turnRate = 0;
  private prevP: V3 | undefined;
  private gov: { g: Gaits; raw: (n: number) => Actor; want: number; shown: number; moving: boolean; since: number } | undefined;
  private active = false;

  constructor(public actor: Actor, start: V3, yaw: number, t0: number, private ground?: (p: V3) => number) {
    this.cursor = t0;
    this.last = { ...start };
    this.lastYaw = yaw;
  }

  /**
   * Locomotion governor.  From now on the creature's visible state follows what its body actually does,
   * whatever the choreography asked for: a standing or acting state never slides over the ground (while
   * travelling the creature shows the travelling loop closest to its real speed), a travelling loop is
   * never shown standing still (idle, or the in-place turn while it pivots), and the asked-for state
   * returns as soon as the motion allows.  `actor.state(n)` keeps working; it records the request.
   */
  govern(g: Gaits): this {
    const actor = this.actor;
    const raw = actor.state.bind(actor) as (n: number) => Actor;
    this.gov = { g, raw, want: 0, shown: 0, moving: false, since: 0 };
    actor.state = (n: number) => {
      const v = this.gov!;
      v.want = n;
      if (!this.active || n === 0 || g.free.includes(n)) { v.shown = n; raw(n); }   // one-shots start on their tick
      return actor;
    };
    return this;
  }
  private decide(t: number, p: V3): void {
    const v = this.gov!;
    const w = v.want;
    if (w === 0 || v.g.free.includes(w)) {
      if (v.shown !== w) { v.shown = w; v.raw(w); }
      return;
    }
    const sp = v.g.swims ? this.speed3 : this.speed;
    v.moving = v.moving ? sp > 0.45 : sp > 0.9;
    const gait = (s: number) => v.g.gaits.find((x) => x.state === s);
    const isTurn = (s: number) => !!v.g.turn && (s === v.g.turn.left || s === v.g.turn.right);
    let show = w;
    if (v.moving) {
      if (!gait(w)) {
        let best = v.g.gaits[0], bd = Infinity;
        for (const x of v.g.gaits) {
          const d = Math.abs(Math.log(Math.max(sp, 0.1) / x.speed));
          if (d < bd) { bd = d; best = x; }
        }
        show = best.state;
      }
    } else if (v.g.turn && Math.abs(this.turnRate) > v.g.turn.above) {
      show = this.turnRate > 0 ? v.g.turn.right : v.g.turn.left;
    } else if (gait(w) || isTurn(w)) {
      show = v.g.idle;
    }
    if (show !== v.shown && t - v.since >= 4) { v.shown = show; v.since = t; v.raw(show); }
    void p;
  }

  /**
   * Walk from a to b at `speed` (blocks / s) with short starts and stops (`ramp` seconds each) - a
   * trapezoid of speed, so the gait's own speed holds for the whole stretch instead of an ease curve
   * that is too slow at the ends and too fast in the middle.
   */
  walk(a: V3, b: V3, speed: number, opts: { ramp?: number; tag?: string; yaw?: Seg["yaw"] } = {}): Seg {
    const D = Math.hypot(b.x - a.x, b.z - a.z);
    const ramp = Math.min(opts.ramp ?? 0.25, (D / speed) / 2);
    const cruise = Math.max(0, D / speed - ramp);             // seconds at full speed (each ramp covers half its time)
    const T = cruise + 2 * ramp;
    const ticks = Math.max(2, Math.round(T * 20));
    const dist = (s: number): number => {                       // metres covered after s seconds
      if (s < ramp) return (speed * s * s) / (2 * ramp);
      if (s < ramp + cruise) return (speed * ramp) / 2 + speed * (s - ramp);
      const r = T - s;
      return D - (speed * r * r) / (2 * ramp);
    };
    return this.add(ticks, (p) => lerp(a, b, D > 1e-6 ? clamp(dist(p * T) / D, 0, 1) : 1), { tag: opts.tag, yaw: opts.yaw ?? yawOf({ x: b.x - a.x, y: 0, z: b.z - a.z }) });
  }

  add(ticks: number, at: (p: number, t: number) => V3, opts: { yaw?: Seg["yaw"]; tag?: string } = {}): Seg {
    const from = this.cursor, to = this.cursor + Math.max(1, Math.round(ticks));
    const seg: Seg = { from, to, at: (t) => at(clamp((t - from) / (to - from), 0, 1), t), yaw: opts.yaw, tag: opts.tag };
    this.segs.push(seg);
    this.cursor = to;
    this.last = seg.at(to);
    return seg;
  }
  /** Stay where the last segment ended. */
  hold(ticks: number, yaw?: number, tag?: string): Seg {
    const p = { ...this.last };
    return this.add(ticks, () => p, { yaw: yaw ?? this.lastYawAt(this.cursor), tag });
  }
  /** Catmull-Rom through pts (pts[0] should be the current position) at `speed` blocks / s. */
  path(pts: V3[], speed: number, opts: { tag?: string; ease?: (p: number) => number; yaw?: Seg["yaw"] } = {}): Seg {
    const L = new ArcPath((u) => spline(pts, u), 48);
    const ticks = Math.max(2, Math.round((L.length / speed) * 20));
    const ease = opts.ease ?? ((p: number) => p);
    return this.add(ticks, (p) => L.at(ease(p) * L.length), { tag: opts.tag, yaw: opts.yaw });
  }
  /** Catmull-Rom through pts covered in exactly `ticks` ticks (arc-length paced, optional easing). */
  pathIn(pts: V3[], ticks: number, opts: { tag?: string; ease?: (p: number) => number; yaw?: Seg["yaw"] } = {}): Seg {
    const L = new ArcPath((u) => spline(pts, u), 48);
    const ease = opts.ease ?? ((p: number) => p);
    return this.add(ticks, (p) => L.at(ease(p) * L.length), { tag: opts.tag, yaw: opts.yaw });
  }
  /** End the segment active at tick t (and drop later ones) so new plans can start there. */
  truncate(t: number): void {
    this.segs = this.segs.filter((s) => s.from < t);
    const s = this.segs[this.segs.length - 1];
    if (s && s.to > t) s.to = t;
    this.cursor = t;
    this.last = this.posAt(t);
    this.lastYaw = this.lastYawAt(t);
  }
  segAt(t: number): Seg | undefined {
    for (const s of this.segs) if (t >= s.from && t < s.to) return s;
    return undefined;
  }
  posAt(t: number): V3 {
    const s = this.segAt(t);
    if (s) return s.at(t);
    let best: Seg | undefined;
    for (const x of this.segs) if (x.to <= t && (!best || x.to > best.to)) best = x;
    return best ? best.at(best.to) : this.last;
  }
  private lastYawAt(t: number): number {
    const s = this.segAt(t - 1) ?? this.segAt(t);
    if (s && s.yaw !== undefined) return typeof s.yaw === "number" ? s.yaw : s.yaw(t);
    return this.lastYaw;
  }
  /** Advance the actor to tick t (call every tick). */
  step(t: number): V3 {
    const s = this.segAt(t);
    let p = s ? s.at(t) : this.posAt(t);
    let want = this.lastYaw;
    if (s && s.yaw !== undefined) {
      this.yawRate *= 0.7;
      want = typeof s.yaw === "number" ? s.yaw : s.yaw(t);
    } else {
      const n = s ? s.at(Math.min(t + 1, s.to)) : p;
      const dx = n.x - p.x, dz = n.z - p.z;
      if (Math.hypot(dx, dz) > 0.02) {
        want = yawOf({ x: dx, y: 0, z: dz });
        this.yawRate = this.yawRate * 0.6 + angleDelta(this.lastYaw, want) * 0.4;
      } else this.yawRate *= 0.7;
    }
    if (this.maxTurn > 0) want = this.lastYaw + clamp(angleDelta(this.lastYaw, want), -this.maxTurn, this.maxTurn);
    const dYaw = angleDelta(this.lastYaw, want) * 20;
    this.lastYaw = want;
    if (this.ground) {
      const g = this.ground(p);
      this.ySmooth = this.ySmooth === undefined ? g : this.ySmooth + clamp(g - this.ySmooth, -0.35, 0.35);
      p = { x: p.x, y: this.ySmooth, z: p.z };
    }
    const sp = this.prevP ? Math.hypot(p.x - this.prevP.x, p.z - this.prevP.z) * 20 : 0;
    const sp3 = this.prevP ? Math.hypot(p.x - this.prevP.x, p.y - this.prevP.y, p.z - this.prevP.z) * 20 : 0;
    this.speed = this.active ? this.speed * 0.35 + sp * 0.65 : 0;
    this.speed3 = this.active ? this.speed3 * 0.35 + sp3 * 0.65 : 0;
    this.turnRate = this.active ? this.turnRate * 0.35 + dYaw * 0.65 : 0;
    this.prevP = p;
    this.active = true;
    if (this.gov) this.decide(t, p);
    this.actor.move(p, this.lastYaw);
    return p;
  }
}

/** A parametric curve f(u), u in 0..1, resampled by arc length. */
export class ArcPath {
  readonly length: number;
  private pts: V3[] = [];
  private cum: number[] = [];
  constructor(f: (u: number) => V3, n = 64, private loop = false) {
    let L = 0;
    for (let i = 0; i <= n; i++) {
      const p = f(i / n);
      if (i) L += Math.hypot(p.x - this.pts[i - 1].x, p.y - this.pts[i - 1].y, p.z - this.pts[i - 1].z);
      this.pts.push(p);
      this.cum.push(L);
    }
    this.length = Math.max(L, 1e-3);
  }
  at(s: number): V3 {
    let d = this.loop ? ((s % this.length) + this.length) % this.length : clamp(s, 0, this.length);
    let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (this.cum[mid] <= d) lo = mid; else hi = mid; }
    const seg = this.cum[hi] - this.cum[lo];
    d = seg > 1e-6 ? (d - this.cum[lo]) / seg : 0;
    return lerp(this.pts[lo], this.pts[hi], d);
  }
}

/** Stage frame: F = away from the caster, R = to its right; angles measured from F toward R. */
export class Frame {
  constructor(public readonly c: V3, public readonly F: V3, public readonly R: V3) {}
  p(f: number, r: number, h = 0): V3 {
    return { x: this.c.x + this.F.x * f + this.R.x * r, y: this.c.y + h, z: this.c.z + this.F.z * f + this.R.z * r };
  }
  polar(radius: number, deg: number, h = 0, from?: V3): V3 {
    const a = (deg * Math.PI) / 180;
    const f = Math.cos(a) * radius, r = Math.sin(a) * radius;
    const o = from ?? this.c;
    return { x: o.x + this.F.x * f + this.R.x * r, y: o.y + h, z: o.z + this.F.z * f + this.R.z * r };
  }
  /** Horizontal unit direction for a frame angle. */
  dir(deg: number): V3 {
    const a = (deg * Math.PI) / 180;
    return { x: this.F.x * Math.cos(a) + this.R.x * Math.sin(a), y: 0, z: this.F.z * Math.cos(a) + this.R.z * Math.sin(a) };
  }
}

/** Deterministic pseudo-random number in [0, 1) for a pair of integers (no RNG spikes, same every cast). */
export function hash01(a: number, b = 0): number {
  const x = Math.sin(a * 12.9898 + b * 78.233 + 0.5) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * A racetrack (stadium) lane: two straights of length L joined by half circles of radius rho, so the
 * tightest turn anywhere on it is rho.  u in 0..1 is arc length (constant speed); lateral axis R, depth F
 * around centre c (y = c.y).  Figure-eights built from sine curves were replaced by this: their lobe
 * shoulders turn on a 2-4 block radius whatever their size, far too tight for a 13-25 block dragon.
 */
export function stadium(c: V3, R: V3, F: V3, L: number, rho: number): (u: number) => V3 {
  const P = 2 * L + 2 * Math.PI * rho;
  const at = (x: number, y: number): V3 => ({ x: c.x + R.x * x + F.x * y, y: c.y, z: c.z + R.z * x + F.z * y });
  return (u: number): V3 => {
    let s = (((u % 1) + 1) % 1) * P;
    if (s < L) return at(-L / 2 + s, rho);                                  // far straight, toward +R
    s -= L;
    if (s < Math.PI * rho) { const a = s / rho; return at(L / 2 + rho * Math.sin(a), rho * Math.cos(a)); }   // right end
    s -= Math.PI * rho;
    if (s < L) return at(L / 2 - s, -rho);                                  // near straight, toward -R
    s -= L;
    const a = s / rho;
    return at(-L / 2 - rho * Math.sin(a), -rho * Math.cos(a));              // left end
  };
}
