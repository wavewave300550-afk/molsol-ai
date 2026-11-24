import { Entity, RGBA } from "@minecraft/server";
import { add, clamp, dist, len, lerp, norm, scale, sub, v, V3 } from "../core/vec.js";

/**
 * A Divine Path: a directed, sampled curve that exists in the world for a while
 * and physically carries what touches it.
 */
export type PathKind =
  | "road"
  | "trail"
  | "loop"
  | "exit"
  | "false"
  | "orbit"
  | "stake"
  | "procession"
  | "player"
  | "ring"
  | "spoke"
  | "arc"
  | "ascend"
  | "converge";

export type PathState = "forming" | "active" | "fading" | "dead";

export interface PathOpts {
  kind: PathKind;
  owner: string;
  speed: number; // carry speed, blocks per tick
  radius: number; // capture radius (horizontal for ground roads, 3D for aerial ones)
  band?: [number, number]; // vertical capture band of the feet relative to the road (ground roads)
  aerial?: boolean;
  form: number; // telegraph ticks
  life: number; // active ticks
  loop?: boolean;
  burning?: boolean;
  carryPlayers?: boolean;
  carryMobs?: boolean;
  carryProjectiles?: boolean;
  pull?: number; // lateral correction towards the centre line
  restless?: number; // automatic reversal period in ticks (phase II), 0 = never
  switching?: boolean; // steals riders at crossings
  memory?: boolean; // leaves a scar that Martyr's Procession can wake
  ownerIsPlayer?: boolean;
  falseRoad?: boolean;
  fling?: number; // exit speed multiplier
  damage?: number; // damage per second while carried (burning roads)
  color?: RGBA;
  chevron?: RGBA;
  visible?: boolean;
  tag?: string;
  crossings?: boolean; // check for crossings when it activates (phase II pyres)
  maxRide?: number; // ticks a rider may stay before being flung (orbits)
  renderEvery?: number; // ticks between flow emitters (default 10); large decorative roads use more
  chevrons?: boolean; // draw direction chevrons (default true)
  /** Called when a rider reaches the end of the flow and there is no continuation. */
  onEnd?: (e: Entity, p: Path) => void;
  /** Where riders are flung at the end of the flow (projectiles get aimed). */
  aim?: (e: Entity, p: Path) => V3 | undefined;
}

export interface Junction {
  s: number; // where on this path the junction is
  to: Path;
  toS: number; // entry point on the target path
}

export interface Nearest {
  s: number;
  d: number; // full 3D distance
  dh: number; // horizontal distance
  dy: number; // query.y - curve.y
  c: V3;
}

let NEXT_ID = 1;

export class Path {
  readonly id = NEXT_ID++;
  pts: V3[];
  cum: number[];
  length: number;
  o: PathOpts;
  flow: 1 | -1 = 1;
  state: PathState = "forming";
  born: number;
  activeAt: number;
  endAt: number;
  next: Path[] = [];
  branchCounter = 0;
  junctions: Junction[] = [];
  reverseAt = -1;
  nextRestless = -1;
  min: V3;
  max: V3;
  segs: number[] = []; // render segment break indices
  riders = 0;
  data: Record<string, unknown> = {};

  constructor(points: V3[], o: PathOpts, now: number) {
    this.o = { carryPlayers: true, carryMobs: true, carryProjectiles: true, pull: 0.18, visible: true, ...o };
    this.pts = resample(points, 0.5, !!o.loop);
    if (this.pts.length < 2) this.pts = [points[0], add(points[0], v(0.01, 0, 0))];
    this.cum = [0];
    for (let i = 1; i < this.pts.length; i++) this.cum.push(this.cum[i - 1] + dist(this.pts[i - 1], this.pts[i]));
    if (o.loop) this.cum.push(this.cum[this.cum.length - 1] + dist(this.pts[this.pts.length - 1], this.pts[0]));
    this.length = this.cum[this.cum.length - 1];
    this.born = now;
    this.activeAt = now + o.form;
    this.endAt = this.activeAt + o.life;
    this.min = { x: Infinity, y: Infinity, z: Infinity };
    this.max = { x: -Infinity, y: -Infinity, z: -Infinity };
    for (const p of this.pts) {
      this.min = { x: Math.min(this.min.x, p.x), y: Math.min(this.min.y, p.y), z: Math.min(this.min.z, p.z) };
      this.max = { x: Math.max(this.max.x, p.x), y: Math.max(this.max.y, p.y), z: Math.max(this.max.z, p.z) };
    }
    this.segs = renderBreaks(this.pts, !!o.loop);
    if (o.restless) this.nextRestless = this.activeAt + o.restless;
  }

  get isActive(): boolean {
    return this.state === "active" || this.state === "fading";
  }

  get alive(): boolean {
    return this.state !== "dead";
  }

  get center(): V3 {
    return lerp(this.min, this.max, 0.5);
  }

  get radiusBound(): number {
    return dist(this.min, this.max) / 2 + 2;
  }

  /** Point at arc length s (s wraps on loops). */
  pointAt(s: number): V3 {
    const n = this.pts.length;
    if (this.o.loop) s = ((s % this.length) + this.length) % this.length;
    else s = clamp(s, 0, this.length);
    let lo = 0;
    let hi = this.cum.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (this.cum[mid] <= s) lo = mid;
      else hi = mid;
    }
    const a = this.pts[lo % n];
    const b = this.pts[(lo + 1) % n];
    const segLen = this.cum[lo + 1] - this.cum[lo] || 1e-6;
    return lerp(a, b, (s - this.cum[lo]) / segLen);
  }

  /** Unit tangent in POINT order at s. */
  tangentAt(s: number): V3 {
    const a = this.pointAt(s - 0.35);
    const b = this.pointAt(s + 0.35);
    const t = norm(sub(b, a));
    return len(t) > 0 ? t : v(1, 0, 0);
  }

  /** Unit direction of the current at s. */
  dirAt(s: number): V3 {
    return scale(this.tangentAt(s), this.flow);
  }

  /** Arc length where the flow starts / ends. */
  get startS(): number {
    return this.flow > 0 ? 0 : this.length;
  }

  get endS(): number {
    return this.flow > 0 ? this.length : 0;
  }

  /** Distance still to travel along the flow from s. */
  remaining(s: number): number {
    if (this.o.loop) return Infinity;
    return this.flow > 0 ? this.length - s : s;
  }

  inBounds(p: V3, margin: number): boolean {
    return (
      p.x >= this.min.x - margin &&
      p.x <= this.max.x + margin &&
      p.y >= this.min.y - margin - 3 &&
      p.y <= this.max.y + margin + 3 &&
      p.z >= this.min.z - margin &&
      p.z <= this.max.z + margin
    );
  }

  /** Nearest point of the curve to p (brute force over segments; paths are short). */
  nearest(p: V3): Nearest {
    const n = this.pts.length;
    const segCount = this.o.loop ? n : n - 1;
    let best: Nearest = { s: 0, d: Infinity, dh: Infinity, dy: 0, c: this.pts[0] };
    for (let i = 0; i < segCount; i++) {
      const a = this.pts[i];
      const b = this.pts[(i + 1) % n];
      const ab = sub(b, a);
      const l2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z || 1e-9;
      let t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y + (p.z - a.z) * ab.z) / l2;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const c = { x: a.x + ab.x * t, y: a.y + ab.y * t, z: a.z + ab.z * t };
      const dx = p.x - c.x;
      const dy = p.y - c.y;
      const dz = p.z - c.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (d < best.d) best = { s: this.cum[i] + Math.sqrt(l2) * t, d, dh: Math.sqrt(dx * dx + dz * dz), dy, c };
    }
    return best;
  }
}

/** Uniformly resample a polyline. */
export function resample(points: V3[], step: number, loop: boolean): V3[] {
  if (points.length < 2) return points.slice();
  const src = loop ? [...points, points[0]] : points;
  const out: V3[] = [src[0]];
  let carry = 0;
  for (let i = 1; i < src.length; i++) {
    const a = src[i - 1];
    const b = src[i];
    const d = dist(a, b);
    if (d < 1e-6) continue;
    let t = step - carry;
    while (t <= d) {
      out.push(lerp(a, b, t / d));
      t += step;
    }
    carry = d - (t - step);
  }
  const last = src[src.length - 1];
  if (!loop && dist(out[out.length - 1], last) > step * 0.3) out.push(last);
  if (loop && out.length > 2 && dist(out[out.length - 1], out[0]) < step * 0.5) out.pop();
  return out;
}

/** Indices where render segments break: at most 2.4 blocks and 24 degrees of turn per segment. */
function renderBreaks(pts: V3[], loop: boolean): number[] {
  const out = [0];
  let acc = 0;
  let dir0 = norm(sub(pts[Math.min(1, pts.length - 1)], pts[0]));
  for (let i = 1; i < pts.length; i++) {
    acc += dist(pts[i - 1], pts[i]);
    const d = norm(sub(pts[i], pts[i - 1]));
    const turn = Math.acos(clamp(d.x * dir0.x + d.y * dir0.y + d.z * dir0.z, -1, 1));
    if (acc >= 2.4 || turn > 0.42 || i === pts.length - 1) {
      out.push(i);
      acc = 0;
      dir0 = d;
    }
  }
  if (loop) out.push(0);
  return out;
}
