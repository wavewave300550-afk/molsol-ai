/**
 * The pattern library for "The Hour That Never Occurred".
 *
 * Every pattern is laid on a polar grid around the arena centre: rings `band`
 * blocks wide and wedges of 360/n degrees. A pattern is fully described by
 * (kind, parity), so the three that are previewed can be stored and then
 * executed exactly as shown.
 */
import type { Arena } from "../../core/arena";
import { DEG, Rng, XZ, thetaToDir } from "../../core/math";
import { Pen, Shape } from "../../core/shapes";

export type PatternKind = "rings" | "wedges" | "checker";

export interface Pattern {
  kind: PatternKind;
  parity: 0 | 1;
}

export const patternLabel = (p: Pattern): string => `${p.kind}:${p.parity}`;

/** The danger region of one pattern. Hit test and drawing share the same cell rule. */
export class PatternShape implements Shape {
  readonly cx: number;
  readonly cz: number;
  readonly reach: number;

  constructor(readonly pattern: Pattern, arena: Arena, private readonly wedges: number, private readonly band: number) {
    this.cx = arena.cx;
    this.cz = arena.cz;
    this.reach = arena.radius + 1;
  }

  private bandOf(r: number): number {
    return Math.floor(r / this.band);
  }

  private wedgeOf(theta: number): number {
    const w = 360 / this.wedges;
    return Math.floor((((theta + w / 2) % 360) + 360) % 360 / w);
  }

  /** Is the cell (band i, wedge j) dangerous in this pattern? */
  danger(i: number, j: number): boolean {
    const p = this.pattern;
    if (p.kind === "rings") return i % 2 === p.parity;
    if (p.kind === "wedges") return j % 2 === p.parity;
    return (i + j) % 2 === p.parity;
  }

  contains(x: number, z: number): boolean {
    const dx = x - this.cx;
    const dz = z - this.cz;
    const r = Math.hypot(dx, dz);
    if (r > this.reach) return false;
    return this.danger(this.bandOf(r), this.wedgeOf(Math.atan2(dz, dx) * DEG));
  }

  draw(pen: Pen): void {
    const bands = Math.ceil(this.reach / this.band);
    const w = 360 / this.wedges;
    const p = this.pattern;
    if (p.kind !== "wedges") {
      for (let i = 1; i <= bands; i++) pen.arc(this.cx, this.cz, Math.min(this.reach, i * this.band), 0, 360);
    }
    if (p.kind !== "rings") {
      for (let j = 0; j < this.wedges; j++) {
        const d = thetaToDir(j * w + w / 2);
        const r0 = p.kind === "checker" ? 0.5 : 0.5;
        pen.line(this.cx + d.x * r0, this.cz + d.z * r0, this.cx + d.x * this.reach, this.cz + d.z * this.reach);
      }
    }
    // every dangerous cell carries a filling mark at its centre, so the pattern is not read from lines alone
    for (let i = 0; i < bands; i++) {
      const rm = Math.min(this.reach, (i + 0.5) * this.band);
      const step = p.kind === "rings" ? Math.max(1, Math.round(this.wedges / 4)) : 1;
      for (let j = 0; j < this.wedges; j += step) {
        if (!this.danger(i, j)) continue;
        if (p.kind === "wedges" && i % 2 === 1) continue;
        const d = thetaToDir(j * w);
        pen.disc(this.cx + d.x * rm, this.cz + d.z * rm, Math.min(1.5, this.band * 0.36));
      }
    }
  }

  sample(rng: Rng, n: number): XZ[] {
    const out: XZ[] = [];
    let guard = n * 30;
    while (out.length < n && guard-- > 0) {
      const a = rng.range(0, Math.PI * 2);
      const d = Math.sqrt(rng.next()) * this.reach;
      const x = this.cx + Math.cos(a) * d;
      const z = this.cz + Math.sin(a) * d;
      if (this.contains(x, z)) out.push({ x, z });
    }
    return out;
  }
}

/**
 * Three patterns for one performance. The first and the third are always exact
 * complements (so no single spot is safe for the whole sequence) and the second
 * is of a different kind (so the answer is never "step back where you were").
 */
export function choosePatterns(rng: Rng, phase: 1 | 2): Pattern[] {
  const a: 0 | 1 = rng.chance(0.5) ? 0 : 1;
  const b: 0 | 1 = rng.chance(0.5) ? 0 : 1;
  if (phase === 1) {
    const first: PatternKind = rng.chance(0.5) ? "rings" : "wedges";
    const other: PatternKind = first === "rings" ? "wedges" : "rings";
    return [{ kind: first, parity: a }, { kind: other, parity: b }, { kind: first, parity: a === 0 ? 1 : 0 }];
  }
  const mid: PatternKind = rng.chance(0.5) ? "rings" : "wedges";
  return [{ kind: "checker", parity: a }, { kind: mid, parity: b }, { kind: "checker", parity: a === 0 ? 1 : 0 }];
}
