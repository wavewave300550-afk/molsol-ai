/**
 * Region patterns used by Nomos's arena-wide attacks, as hazard Shapes:
 * the telegraph and the hit test are the same object (see core/shapes.ts).
 *
 *   Stripes   parallel corridors (axis-aligned for Folded Country, oblique for
 *             the "oblique projection" of The Great Recalculation), clipped to a box;
 *   Checker   a chessboard of square cells clipped to a box (the "Cartesian" configuration);
 *   Marks     drawing-only marks for the SAFE regions (never damages).
 */
import { Rng, XZ, thetaToDir } from "../../core/math";
import { Pen, Shape } from "../../core/shapes";
import type { Bounds } from "./grid";

function inBounds(b: Bounds, x: number, z: number): boolean {
  return x >= b.x0 && x <= b.x1 && z >= b.z0 && z <= b.z1;
}

function sampleBounds(shape: Shape, b: Bounds, rng: Rng, n: number): XZ[] {
  const out: XZ[] = [];
  let guard = n * 24;
  while (out.length < n && guard-- > 0) {
    const x = rng.range(b.x0, b.x1);
    const z = rng.range(b.z0, b.z1);
    if (shape.contains(x, z)) out.push({ x, z });
  }
  return out;
}

/** Liang-Barsky: the part of the infinite line through (px, pz) along (dx, dz) that lies in the box. */
function clipLine(b: Bounds, px: number, pz: number, dx: number, dz: number): [number, number, number, number] | undefined {
  let t0 = -1e9;
  let t1 = 1e9;
  for (const [o, d, lo, hi] of [[px, dx, b.x0, b.x1], [pz, dz, b.z0, b.z1]] as const) {
    if (Math.abs(d) < 1e-9) {
      if (o < lo || o > hi) return undefined;
      continue;
    }
    let a = (lo - o) / d;
    let c = (hi - o) / d;
    if (a > c) [a, c] = [c, a];
    t0 = Math.max(t0, a);
    t1 = Math.min(t1, c);
  }
  if (t1 - t0 < 0.2) return undefined;
  return [px + dx * t0, pz + dz * t0, px + dx * t1, pz + dz * t1];
}

/**
 * Parallel corridors inside a box. `theta` is the direction the corridors RUN;
 * measured across them, a corridor of `width` repeats every `period`, starting at `offset`
 * (distance from the box's (x0, z0) corner along the perpendicular).
 */
export class Stripes implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;
  private readonly ux: number;
  private readonly uz: number;
  private readonly nx: number;
  private readonly nz: number;

  constructor(readonly b: Bounds, readonly theta: number, readonly period: number, readonly width: number, readonly offset = 0, private readonly centreOnly = false) {
    this.cx = (b.x0 + b.x1) / 2;
    this.cz = (b.z0 + b.z1) / 2;
    this.reach = Math.hypot(b.x1 - b.x0, b.z1 - b.z0) / 2;
    const d = thetaToDir(theta);
    this.ux = d.x;
    this.uz = d.z;
    this.nx = -d.z;
    this.nz = d.x;
  }

  /** Signed distance across the corridors, from the box corner. */
  across(x: number, z: number): number {
    return (x - this.b.x0) * this.nx + (z - this.b.z0) * this.nz;
  }

  /** Index of the period that a point falls in (used to pick the corridor a player stands in). */
  bandIndex(x: number, z: number): number {
    return Math.floor((this.across(x, z) - this.offset) / this.period);
  }

  contains(x: number, z: number): boolean {
    if (!inBounds(this.b, x, z)) return false;
    const s = this.across(x, z) - this.offset;
    const m = ((s % this.period) + this.period) % this.period;
    return m < this.width;
  }

  /** The complementary corridors (what is safe when this is dangerous). */
  complement(centreOnly = true): Stripes {
    return new Stripes(this.b, this.theta, this.period, this.period - this.width, this.offset + this.width, centreOnly);
  }

  draw(pen: Pen): void {
    // corridors that can touch the box: project the four corners
    const cs = [this.across(this.b.x0, this.b.z0), this.across(this.b.x1, this.b.z0), this.across(this.b.x0, this.b.z1), this.across(this.b.x1, this.b.z1)];
    const lo = Math.floor((Math.min(...cs) - this.offset) / this.period) - 1;
    const hi = Math.ceil((Math.max(...cs) - this.offset) / this.period) + 1;
    for (let k = lo; k <= hi; k++) {
      const s0 = this.offset + k * this.period;
      const lines = this.centreOnly ? [s0 + this.width / 2] : this.width >= 3.2 ? [s0, s0 + this.width / 2, s0 + this.width] : [s0, s0 + this.width];
      for (const s of lines) {
        const px = this.b.x0 + this.nx * s;
        const pz = this.b.z0 + this.nz * s;
        const seg = clipLine(this.b, px, pz, this.ux, this.uz);
        if (seg) pen.line(seg[0], seg[1], seg[2], seg[3]);
      }
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    return sampleBounds(this, this.b, rng, n);
  }
}

/** A chessboard of `cell`-sized squares inside a box; squares of the given parity are covered. */
export class Checker implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;

  constructor(readonly b: Bounds, readonly cell: number, readonly parity: 0 | 1) {
    this.cx = (b.x0 + b.x1) / 2;
    this.cz = (b.z0 + b.z1) / 2;
    this.reach = Math.hypot(b.x1 - b.x0, b.z1 - b.z0) / 2;
  }

  private squareOf(x: number, z: number): [number, number] {
    return [Math.floor((x - this.b.x0) / this.cell), Math.floor((z - this.b.z0) / this.cell)];
  }

  contains(x: number, z: number): boolean {
    if (!inBounds(this.b, x, z)) return false;
    const [i, j] = this.squareOf(Math.min(x, this.b.x1 - 1e-6), Math.min(z, this.b.z1 - 1e-6));
    return (((i + j) % 2) + 2) % 2 === this.parity;
  }

  /** Centres of the covered squares (parity) or of the others (1 - parity). */
  centres(parity: 0 | 1 = this.parity): XZ[] {
    const out: XZ[] = [];
    const nx = Math.round((this.b.x1 - this.b.x0) / this.cell);
    const nz = Math.round((this.b.z1 - this.b.z0) / this.cell);
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < nz; j++) {
        if ((i + j) % 2 === parity) out.push({ x: this.b.x0 + (i + 0.5) * this.cell, z: this.b.z0 + (j + 0.5) * this.cell });
      }
    }
    return out;
  }

  draw(pen: Pen): void {
    const h = this.cell / 2;
    for (const c of this.centres()) {
      // outline plus one diagonal: a struck-out square reads as danger without relying on colour
      pen.line(c.x - h, c.z - h, c.x + h, c.z - h);
      pen.line(c.x + h, c.z - h, c.x + h, c.z + h);
      pen.line(c.x + h, c.z + h, c.x - h, c.z + h);
      pen.line(c.x - h, c.z + h, c.x - h, c.z - h);
      pen.line(c.x - h, c.z - h, c.x + h, c.z + h);
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    return sampleBounds(this, this.b, rng, n);
  }
}

/** Drawing-only marks (safe-region benchmarks). Covers nothing, so it can never deal damage. */
export class Marks implements Shape {
  readonly reach = 0;

  constructor(readonly cx: number, readonly cz: number, private readonly paint: (pen: Pen) => void) {}

  contains(): boolean {
    return false;
  }

  draw(pen: Pen): void {
    this.paint(pen);
  }

  sample(): XZ[] {
    return [];
  }
}
