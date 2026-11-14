import { Actor } from "../lib/scene";
import { V3, angleDelta, clamp, lerp, spline, yawOf } from "../lib/vec";

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
  private ySmooth: number | undefined;

  constructor(public actor: Actor, start: V3, yaw: number, t0: number, private ground?: (p: V3) => number) {
    this.cursor = t0;
    this.last = { ...start };
    this.lastYaw = yaw;
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
    if (s && s.yaw !== undefined) {
      this.yawRate *= 0.7;
      this.lastYaw = typeof s.yaw === "number" ? s.yaw : s.yaw(t);
    } else {
      const n = s ? s.at(Math.min(t + 1, s.to)) : p;
      const dx = n.x - p.x, dz = n.z - p.z;
      if (Math.hypot(dx, dz) > 0.02) {
        const y = yawOf({ x: dx, y: 0, z: dz });
        this.yawRate = this.yawRate * 0.6 + angleDelta(this.lastYaw, y) * 0.4;
        this.lastYaw = y;
      } else this.yawRate *= 0.7;
    }
    if (this.ground) {
      const g = this.ground(p);
      this.ySmooth = this.ySmooth === undefined ? g : this.ySmooth + clamp(g - this.ySmooth, -0.35, 0.35);
      p = { x: p.x, y: this.ySmooth, z: p.z };
    }
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
