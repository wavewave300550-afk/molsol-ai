/**
 * The survey grid: Nomos's logical coordinate system.
 *
 * The square arena is ruled into 8 x 8 cells (5 blocks each, columns A-H west
 * to east, rows 1-8 north to south) and four quadrants. Every Nomos attack is
 * expressed on this grid as ordinary hazard shapes; nothing in the world is
 * moved, rotated or rewritten. The grid also answers the fairness question for
 * arena-wide patterns: how far is the worst-placed player from a safe spot?
 */
import type { Arena } from "../../core/arena";
import { XZ, thetaToDir } from "../../core/math";
import { Lane, Polygon, Shape, rect } from "../../core/shapes";

export const GRID_N = 8;

export interface Bounds {
  x0: number;
  z0: number;
  x1: number;
  z1: number;
}

/** Quadrants: 0 = north-west (-x, -z), 1 = north-east, 2 = south-west, 3 = south-east. */
export const QUADRANTS = [0, 1, 2, 3] as const;
/** Start bearing (theta) of each quadrant's 90-degree sector around the arena centre. */
export const QUADRANT_THETA = [180, 270, 90, 0] as const;

export class SurveyGrid {
  readonly cx: number;
  readonly cz: number;
  readonly half: number;
  readonly cell: number;

  constructor(arena: Arena) {
    this.cx = arena.cx;
    this.cz = arena.cz;
    this.half = arena.radius;
    this.cell = (this.half * 2) / GRID_N;
  }

  bounds(): Bounds {
    return { x0: this.cx - this.half, z0: this.cz - this.half, x1: this.cx + this.half, z1: this.cz + this.half };
  }

  /** Column / row of a world position (clamped into the grid). */
  cellOf(x: number, z: number): { c: number; r: number } {
    const c = Math.min(GRID_N - 1, Math.max(0, Math.floor((x - (this.cx - this.half)) / this.cell)));
    const r = Math.min(GRID_N - 1, Math.max(0, Math.floor((z - (this.cz - this.half)) / this.cell)));
    return { c, r };
  }

  cellCentre(c: number, r: number): XZ {
    return { x: this.cx - this.half + (c + 0.5) * this.cell, z: this.cz - this.half + (r + 0.5) * this.cell };
  }

  cellRect(c: number, r: number): Polygon {
    const x0 = this.cx - this.half + c * this.cell;
    const z0 = this.cz - this.half + r * this.cell;
    return rect(x0, z0, x0 + this.cell, z0 + this.cell);
  }

  /** "C5"-style name of a cell, for messages and docs. */
  cellName(c: number, r: number): string {
    return "ABCDEFGH"[c] + String(r + 1);
  }

  quadrantOf(x: number, z: number): number {
    return (x >= this.cx ? 1 : 0) + (z >= this.cz ? 2 : 0);
  }

  quadrantBounds(q: number): Bounds {
    const east = (q & 1) === 1;
    const south = (q & 2) === 2;
    return {
      x0: east ? this.cx : this.cx - this.half, x1: east ? this.cx + this.half : this.cx,
      z0: south ? this.cz : this.cz - this.half, z1: south ? this.cz + this.half : this.cz,
    };
  }

  quadrantCentre(q: number): XZ {
    const b = this.quadrantBounds(q);
    return { x: (b.x0 + b.x1) / 2, z: (b.z0 + b.z1) / 2 };
  }

  /** Nearest ruled line (cell boundary) to a coordinate on one axis. */
  snapLine(v: number, axis: "x" | "z"): number {
    const o = axis === "x" ? this.cx - this.half : this.cz - this.half;
    return o + Math.round((v - o) / this.cell) * this.cell;
  }

  inside(p: XZ, inset = 0): boolean {
    return Math.abs(p.x - this.cx) <= this.half - inset && Math.abs(p.z - this.cz) <= this.half - inset;
  }

  /** Clip the infinite line through `p` along `theta` to a box; undefined when it misses. */
  clip(p: XZ, theta: number, b: Bounds = this.bounds()): [XZ, XZ] | undefined {
    const d = thetaToDir(theta);
    let t0 = -1e9;
    let t1 = 1e9;
    for (const [o, dd, lo, hi] of [[p.x, d.x, b.x0, b.x1], [p.z, d.z, b.z0, b.z1]] as const) {
      if (Math.abs(dd) < 1e-9) {
        if (o < lo || o > hi) return undefined;
        continue;
      }
      let a = (lo - o) / dd;
      let c = (hi - o) / dd;
      if (a > c) [a, c] = [c, a];
      t0 = Math.max(t0, a);
      t1 = Math.min(t1, c);
    }
    if (t0 >= t1) return undefined;
    return [{ x: p.x + d.x * t0, z: p.z + d.z * t0 }, { x: p.x + d.x * t1, z: p.z + d.z * t1 }];
  }

  /** A straight incision across the whole arena through `p` along `theta`. */
  chord(p: XZ, theta: number, halfWidth: number): Lane {
    const q = { x: Math.min(this.cx + this.half - 0.1, Math.max(this.cx - this.half + 0.1, p.x)), z: Math.min(this.cz + this.half - 0.1, Math.max(this.cz - this.half + 0.1, p.z)) };
    const seg = this.clip(q, theta) ?? [q, q];
    return new Lane(seg[0].x, seg[0].z, seg[1].x, seg[1].z, halfWidth);
  }

  /**
   * How far (blocks) the worst-placed point of the arena is from the nearest
   * point that `danger` does not cover. A two-pass chamfer distance transform on
   * a one-block lattice: cheap enough to run before every arena-wide pattern.
   * Returns Infinity when the pattern leaves no safe point at all.
   */
  maxDistanceToSafety(danger: Shape, step = 1): number {
    const n = Math.round((this.half * 2) / step);
    const d = new Float32Array(n * n);
    const BIG = 1e6;
    let anySafe = false;
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const x = this.cx - this.half + (i + 0.5) * step;
        const z = this.cz - this.half + (j + 0.5) * step;
        const safe = !danger.contains(x, z);
        d[j * n + i] = safe ? 0 : BIG;
        anySafe = anySafe || safe;
      }
    }
    if (!anySafe) return Infinity;
    const A = step;
    const B = step * Math.SQRT2;
    const at = (i: number, j: number) => (i < 0 || j < 0 || i >= n || j >= n ? BIG : d[j * n + i]);
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const k = j * n + i;
        d[k] = Math.min(d[k], at(i - 1, j) + A, at(i, j - 1) + A, at(i - 1, j - 1) + B, at(i + 1, j - 1) + B);
      }
    }
    let worst = 0;
    for (let j = n - 1; j >= 0; j--) {
      for (let i = n - 1; i >= 0; i--) {
        const k = j * n + i;
        d[k] = Math.min(d[k], at(i + 1, j) + A, at(i, j + 1) + A, at(i + 1, j + 1) + B, at(i - 1, j + 1) + B);
        if (d[k] > worst) worst = d[k];
      }
    }
    return worst;
  }

  /** Can a walking player always get clear of `danger` within `warnTicks`? */
  reachable(danger: Shape, warnTicks: number, walk: number, reaction: number): boolean {
    return this.maxDistanceToSafety(danger) <= Math.max(0, warnTicks - reaction) * walk;
  }
}
