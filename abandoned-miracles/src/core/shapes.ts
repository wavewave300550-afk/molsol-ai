/**
 * Hazard geometry on the arena floor (XZ plane).
 *
 * A Shape answers two questions with the SAME numbers:
 *   contains(x, z)  - used for hit detection at strike time,
 *   draw(pen)       - used to render the telegraph.
 * Because both come from one object, what the player sees is what can hit them.
 */
import { DEG, RAD, Rng, XZ, clamp, thetaToDir, wrapDeg } from "./math";

/** Abstract drawing surface; implemented by the visual controller with particle primitives. */
export interface Pen {
  line(ax: number, az: number, bx: number, bz: number): void;
  arc(cx: number, cz: number, r: number, a0: number, sweep: number): void;
  disc(cx: number, cz: number, r: number): void;
}

export interface Shape {
  contains(x: number, z: number): boolean;
  draw(pen: Pen): void;
  /** Random points inside the shape, for strike effects. */
  sample(rng: Rng, n: number): XZ[];
  /** Coarse bounding circle, for cheap rejection. */
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;
}

export class Circle implements Shape {
  readonly reach: number;

  constructor(readonly cx: number, readonly cz: number, readonly r: number) {
    this.reach = r;
  }

  contains(x: number, z: number): boolean {
    const dx = x - this.cx;
    const dz = z - this.cz;
    return dx * dx + dz * dz <= this.r * this.r;
  }

  draw(pen: Pen): void {
    pen.arc(this.cx, this.cz, this.r, 0, 360);
    pen.disc(this.cx, this.cz, this.r);
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    for (let i = 0; i < n; i++) {
      const a = rng.range(0, Math.PI * 2);
      const d = Math.sqrt(rng.next()) * this.r;
      out.push({ x: this.cx + Math.cos(a) * d, z: this.cz + Math.sin(a) * d });
    }
    return out;
  }
}

/** Angular interval helper: is theta inside [a0, a0 + sweep] (sweep > 0, degrees)? */
export function inSweep(theta: number, a0: number, sweep: number): boolean {
  if (sweep >= 360) return true;
  const d = ((theta - a0) % 360 + 360) % 360;
  return d <= sweep;
}

/**
 * Annulus between r0 and r1 covering [a0, a0 + sweep], minus optional safe gaps.
 * With sweep = 360 this is a shockwave ring; with gaps it is a ring with doors.
 */
export class Ring implements Shape {
  readonly reach: number;

  constructor(
    readonly cx: number,
    readonly cz: number,
    readonly r0: number,
    readonly r1: number,
    readonly a0 = 0,
    readonly sweep = 360,
    /** Safe gaps as [start theta, sweep] pairs. */
    readonly gaps: ReadonlyArray<readonly [number, number]> = [],
  ) {
    this.reach = r1;
  }

  contains(x: number, z: number): boolean {
    const dx = x - this.cx;
    const dz = z - this.cz;
    const d2 = dx * dx + dz * dz;
    if (d2 < this.r0 * this.r0 || d2 > this.r1 * this.r1) return false;
    const th = Math.atan2(dz, dx) * DEG;
    if (!inSweep(th, this.a0, this.sweep)) return false;
    for (const [g0, gs] of this.gaps) if (inSweep(th, g0, gs)) return false;
    return true;
  }

  /** Solid angular spans as [start, sweep], i.e. the sweep with the gaps cut out. */
  spans(): Array<[number, number]> {
    if (this.gaps.length === 0) return [[this.a0, this.sweep]];
    // express gaps relative to a0, clip and sort
    const cuts: Array<[number, number]> = [];
    for (const [g0, gs] of this.gaps) {
      let s = ((g0 - this.a0) % 360 + 360) % 360;
      let e = s + gs;
      if (e > 360 && this.sweep >= 360) {
        cuts.push([0, e - 360]);
        e = 360;
      }
      s = clamp(s, 0, this.sweep);
      e = clamp(e, 0, this.sweep);
      if (e > s) cuts.push([s, e]);
    }
    cuts.sort((a, b) => a[0] - b[0]);
    const out: Array<[number, number]> = [];
    let cur = 0;
    for (const [s, e] of cuts) {
      if (s > cur + 1e-6) out.push([this.a0 + cur, s - cur]);
      cur = Math.max(cur, e);
    }
    if (cur < this.sweep - 1e-6) out.push([this.a0 + cur, this.sweep - cur]);
    return out;
  }

  draw(pen: Pen): void {
    const full = this.sweep >= 360 && this.gaps.length === 0;
    for (const [s, w] of this.spans()) {
      pen.arc(this.cx, this.cz, this.r1, s, w);
      if (this.r0 > 0.5) pen.arc(this.cx, this.cz, this.r0, s, w);
      if (!full) {
        for (const a of [s, s + w]) {
          const d = thetaToDir(a);
          pen.line(this.cx + d.x * this.r0, this.cz + d.z * this.r0, this.cx + d.x * this.r1, this.cz + d.z * this.r1);
        }
      }
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    const spans = this.spans();
    if (spans.length === 0) return out;
    for (let i = 0; i < n; i++) {
      const [s, w] = rng.pick(spans);
      const a = (s + rng.next() * w) * RAD;
      const d = Math.sqrt(rng.range(this.r0 * this.r0, this.r1 * this.r1));
      out.push({ x: this.cx + Math.cos(a) * d, z: this.cz + Math.sin(a) * d });
    }
    return out;
  }
}

/** Convenience: a wedge pointing along `theta` with the given half-angle. */
export function sector(cx: number, cz: number, r0: number, r1: number, theta: number, half: number): Ring {
  return new Ring(cx, cz, r0, r1, wrapDeg(theta - half), half * 2);
}

/** Thick line segment (capsule with flat ends when `flat`), e.g. a lane or an incision. */
export class Lane implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;
  private readonly ux: number;
  private readonly uz: number;
  private readonly length: number;

  constructor(
    readonly ax: number,
    readonly az: number,
    readonly bx: number,
    readonly bz: number,
    readonly halfWidth: number,
    readonly flat = true,
  ) {
    this.cx = (ax + bx) / 2;
    this.cz = (az + bz) / 2;
    this.length = Math.hypot(bx - ax, bz - az);
    this.ux = this.length > 1e-9 ? (bx - ax) / this.length : 1;
    this.uz = this.length > 1e-9 ? (bz - az) / this.length : 0;
    this.reach = this.length / 2 + halfWidth;
  }

  contains(x: number, z: number): boolean {
    const px = x - this.ax;
    const pz = z - this.az;
    const along = px * this.ux + pz * this.uz;
    const across = Math.abs(-px * this.uz + pz * this.ux);
    if (across > this.halfWidth) return false;
    if (along >= 0 && along <= this.length) return true;
    if (this.flat) return false;
    const ex = along < 0 ? px : x - this.bx;
    const ez = along < 0 ? pz : z - this.bz;
    return ex * ex + ez * ez <= this.halfWidth * this.halfWidth;
  }

  draw(pen: Pen): void {
    const nx = -this.uz * this.halfWidth;
    const nz = this.ux * this.halfWidth;
    pen.line(this.ax + nx, this.az + nz, this.bx + nx, this.bz + nz);
    pen.line(this.ax - nx, this.az - nz, this.bx - nx, this.bz - nz);
    // interior strokes so the lane reads as filled even without colour
    const inner = Math.max(0, Math.floor(this.halfWidth / 0.9) - 1);
    for (let i = 0; i <= inner; i++) {
      const k = inner === 0 ? 0 : (i / inner) * 2 - 1;
      const f = k * 0.5;
      pen.line(this.ax + nx * f, this.az + nz * f, this.bx + nx * f, this.bz + nz * f);
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    for (let i = 0; i < n; i++) {
      const t = rng.next() * this.length;
      const w = rng.range(-this.halfWidth, this.halfWidth);
      out.push({ x: this.ax + this.ux * t - this.uz * w, z: this.az + this.uz * t + this.ux * w });
    }
    return out;
  }
}

/** Convex polygon (vertices in order). Used for map-like regions. */
export class Polygon implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;

  constructor(readonly pts: ReadonlyArray<XZ>) {
    this.cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
    this.cz = pts.reduce((s, p) => s + p.z, 0) / pts.length;
    this.reach = Math.max(...pts.map((p) => Math.hypot(p.x - this.cx, p.z - this.cz)));
  }

  contains(x: number, z: number): boolean {
    let sign = 0;
    for (let i = 0; i < this.pts.length; i++) {
      const a = this.pts[i];
      const b = this.pts[(i + 1) % this.pts.length];
      const c = (b.x - a.x) * (z - a.z) - (b.z - a.z) * (x - a.x);
      if (Math.abs(c) < 1e-9) continue;
      const s = c > 0 ? 1 : -1;
      if (sign === 0) sign = s;
      else if (s !== sign) return false;
    }
    return true;
  }

  draw(pen: Pen): void {
    for (let i = 0; i < this.pts.length; i++) {
      const a = this.pts[i];
      const b = this.pts[(i + 1) % this.pts.length];
      pen.line(a.x, a.z, b.x, b.z);
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    let guard = n * 20;
    while (out.length < n && guard-- > 0) {
      const x = this.cx + rng.range(-this.reach, this.reach);
      const z = this.cz + rng.range(-this.reach, this.reach);
      if (this.contains(x, z)) out.push({ x, z });
    }
    return out;
  }
}

/** Axis-aligned rectangle given by min/max corners. */
export function rect(x0: number, z0: number, x1: number, z1: number): Polygon {
  return new Polygon([
    { x: x0, z: z0 },
    { x: x1, z: z0 },
    { x: x1, z: z1 },
    { x: x0, z: z1 },
  ]);
}

/** Union of shapes. */
export class Union implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;

  constructor(readonly parts: ReadonlyArray<Shape>) {
    this.cx = parts.reduce((s, p) => s + p.cx, 0) / Math.max(1, parts.length);
    this.cz = parts.reduce((s, p) => s + p.cz, 0) / Math.max(1, parts.length);
    this.reach = Math.max(0, ...parts.map((p) => Math.hypot(p.cx - this.cx, p.cz - this.cz) + p.reach));
  }

  contains(x: number, z: number): boolean {
    for (const p of this.parts) if (p.contains(x, z)) return true;
    return false;
  }

  draw(pen: Pen): void {
    for (const p of this.parts) p.draw(pen);
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    if (this.parts.length === 0) return out;
    for (let i = 0; i < n; i++) out.push(...rng.pick(this.parts).sample(rng, 1));
    return out;
  }
}

/**
 * Everything inside `bounds` EXCEPT the `safe` shapes: "the whole floor is lethal, stand here".
 * Drawing renders only the safe shapes; callers draw them with the SAFE telegraph style.
 */
export class Except implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;

  constructor(readonly bounds: Shape, readonly safe: ReadonlyArray<Shape>) {
    this.cx = bounds.cx;
    this.cz = bounds.cz;
    this.reach = bounds.reach;
  }

  contains(x: number, z: number): boolean {
    if (!this.bounds.contains(x, z)) return false;
    for (const s of this.safe) if (s.contains(x, z)) return false;
    return true;
  }

  draw(pen: Pen): void {
    for (const s of this.safe) s.draw(pen);
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    let guard = n * 20;
    while (out.length < n && guard-- > 0) {
      const p = this.bounds.sample(rng, 1)[0];
      if (p && this.contains(p.x, p.z)) out.push(p);
    }
    return out;
  }
}
