/**
 * ArenaController - the logical battlefield around a summoning point.
 *
 * The arena is pure data: a centre, a floor height and a radius (or half-size
 * for square arenas). Nothing here edits blocks. Boss movement is leashed to it,
 * hazards are confined to it, and players are participants only while inside.
 */
import { Dimension } from "@minecraft/server";
import { BossBaseStats, CONFIG } from "../config";
import { Rng, V3, XZ, clamp, thetaToDir } from "./math";
import { Circle, Shape, rect } from "./shapes";

export interface ArenaScan {
  ok: boolean;
  coverage: number;
  ceilingClear: boolean;
  loaded: boolean;
  reason?: string;
}

export class Arena {
  readonly cx: number;
  readonly cz: number;
  /** Y of the walking surface (top of the floor blocks). */
  readonly floorY: number;
  readonly radius: number;
  readonly square: boolean;

  constructor(centre: V3, stats: BossBaseStats) {
    this.cx = centre.x;
    this.cz = centre.z;
    this.floorY = centre.y;
    this.radius = stats.arenaRadius;
    this.square = stats.arenaShape === "square";
  }

  get centre(): V3 {
    return { x: this.cx, y: this.floorY, z: this.cz };
  }

  /** Is (x, z) within the arena, shrunk by `inset` (negative grows it)? */
  contains(x: number, z: number, inset = 0): boolean {
    const r = this.radius - inset;
    const dx = x - this.cx;
    const dz = z - this.cz;
    return this.square ? Math.abs(dx) <= r && Math.abs(dz) <= r : dx * dx + dz * dz <= r * r;
  }

  /** Vertical band in which a player counts as "in the fight". */
  inBand(y: number): boolean {
    return y >= this.floorY - CONFIG.encounter.floorBelow && y <= this.floorY + CONFIG.encounter.floorAbove;
  }

  /** Nearest point inside the arena shrunk by `inset`. */
  clampInside(x: number, z: number, inset = 0): XZ {
    const r = Math.max(0, this.radius - inset);
    let dx = x - this.cx;
    let dz = z - this.cz;
    if (this.square) {
      dx = clamp(dx, -r, r);
      dz = clamp(dz, -r, r);
    } else {
      const d = Math.hypot(dx, dz);
      if (d > r && d > 1e-9) {
        dx *= r / d;
        dz *= r / d;
      }
    }
    return { x: this.cx + dx, z: this.cz + dz };
  }

  /** Point at bearing theta, `dist` blocks from the centre (clamped into the arena). */
  polar(theta: number, dist: number, inset = 0): XZ {
    const d = thetaToDir(theta);
    return this.clampInside(this.cx + d.x * dist, this.cz + d.z * dist, inset);
  }

  /** Distance from the centre to the arena edge along bearing theta. */
  edgeDistance(theta: number): number {
    if (!this.square) return this.radius;
    const d = thetaToDir(theta);
    const m = Math.max(Math.abs(d.x), Math.abs(d.z));
    return m > 1e-9 ? this.radius / m : this.radius;
  }

  /** Uniform random point inside, at least `inset` from the edge and outside every `avoid` circle. */
  randomPoint(rng: Rng, inset = 1, avoid: ReadonlyArray<{ x: number; z: number; r: number }> = []): XZ {
    const r = Math.max(0.5, this.radius - inset);
    for (let i = 0; i < 24; i++) {
      let x: number;
      let z: number;
      if (this.square) {
        x = this.cx + rng.range(-r, r);
        z = this.cz + rng.range(-r, r);
      } else {
        const a = rng.range(0, Math.PI * 2);
        const d = Math.sqrt(rng.next()) * r;
        x = this.cx + Math.cos(a) * d;
        z = this.cz + Math.sin(a) * d;
      }
      if (avoid.every((c) => Math.hypot(x - c.x, z - c.z) >= c.r)) return { x, z };
    }
    return { x: this.cx, z: this.cz };
  }

  /** The arena footprint as a hazard shape (for "everything except ..." hazards). */
  bounds(inset = 0): Shape {
    const r = this.radius - inset;
    return this.square ? rect(this.cx - r, this.cz - r, this.cx + r, this.cz + r) : new Circle(this.cx, this.cz, r);
  }

  at(p: XZ, lift = 0): V3 {
    return { x: p.x, y: this.floorY + lift, z: p.z };
  }

  /**
   * Check that a location can host this boss WITHOUT changing a single block:
   * enough solid floor at one level, free air above it, and head room at the centre.
   */
  static scan(dim: Dimension, centre: V3, stats: BossBaseStats): ArenaScan {
    const fy = Math.floor(centre.y);
    const r = stats.arenaRadius;
    const step = 3;
    let total = 0;
    let good = 0;
    try {
      for (let dx = -r; dx <= r; dx += step) {
        for (let dz = -r; dz <= r; dz += step) {
          if (stats.arenaShape === "circle" && dx * dx + dz * dz > r * r) continue;
          total++;
          const x = Math.floor(centre.x + dx);
          const z = Math.floor(centre.z + dz);
          const floor = dim.getBlock({ x, y: fy - 1, z });
          const feet = dim.getBlock({ x, y: fy, z });
          const head = dim.getBlock({ x, y: fy + 1, z });
          if (!floor || !feet || !head) return { ok: false, coverage: 0, ceilingClear: false, loaded: false, reason: "unloaded" };
          if (!floor.isAir && !floor.isLiquid && feet.isAir && head.isAir) good++;
        }
      }
      let clear = true;
      for (let dy = 0; dy < stats.clearance && clear; dy++) {
        for (const [ox, oz] of [[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2]]) {
          const b = dim.getBlock({ x: Math.floor(centre.x) + ox, y: fy + dy, z: Math.floor(centre.z) + oz });
          if (!b || !b.isAir) {
            clear = false;
            break;
          }
        }
      }
      const coverage = total > 0 ? good / total : 0;
      const ok = clear && coverage >= CONFIG.encounter.minFloorCoverage;
      return {
        ok,
        coverage,
        ceilingClear: clear,
        loaded: true,
        reason: ok ? undefined : !clear ? "ceiling" : "floor",
      };
    } catch {
      return { ok: false, coverage: 0, ceilingClear: false, loaded: false, reason: "unloaded" };
    }
  }
}
