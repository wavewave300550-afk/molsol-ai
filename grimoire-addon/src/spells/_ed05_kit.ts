import { add, angleDelta, clamp, dist, fromYaw, lerp, right, spline, sub, V3, yawOf } from "../lib/vec";

/** Species of the four fossil lineages, in emergence order. */
export type Species = "nature" | "heat" | "tide" | "air";
export const SPECIES: Species[] = ["nature", "heat", "tide", "air"];
/** Memorial slot of each species (slot k sits at monument angle + 90 k; matches the memorial's gems). */
export const SLOT: Record<Species, number> = { nature: 0, heat: 1, air: 2, tide: 3 };

/**
 * World point of a model-space offset (blocks) for an actor at `o` facing `yaw`:
 * bb +X = the actor's right, +Y up, -Z = its front.
 */
export function local(o: V3, yaw: number, bx: number, by: number, bz: number): V3 {
  const f = fromYaw(yaw), r = right(f);
  return { x: o.x + r.x * bx - f.x * bz, y: o.y + by, z: o.z + r.z * bx - f.z * bz };
}

export function yawLerp(a: number, b: number, t: number): number {
  return a + angleDelta(a, b) * clamp(t, 0, 1);
}

/** Polar angle (degrees, 0 = +X, as lib/vec polar) of a horizontal direction. */
export function polarOf(d: V3): number {
  return (Math.atan2(d.z, d.x) * 180) / Math.PI;
}

/** True when p lies in the horizontal sector from o around dirYaw (half angle, radii in blocks). */
export function inSector(p: V3, o: V3, dirYaw: number, half: number, rMin: number, rMax: number): boolean {
  const d = sub(p, o);
  const h = Math.hypot(d.x, d.z);
  if (h < rMin || h > rMax) return false;
  return Math.abs(angleDelta(dirYaw, yawOf(d))) <= half;
}

/** Arc-length parametrised Catmull-Rom path (constant-speed flight). */
export class Path {
  private pts: V3[] = [];
  private cum: number[] = [0];
  readonly length: number;
  constructor(ctrl: V3[], samples = 240) {
    for (let i = 0; i <= samples; i++) this.pts.push(spline(ctrl, i / samples));
    for (let i = 1; i < this.pts.length; i++) this.cum.push(this.cum[i - 1] + dist(this.pts[i - 1], this.pts[i]));
    this.length = this.cum[this.cum.length - 1];
  }
  at(s: number): V3 {
    const t = clamp(s, 0, this.length);
    let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (this.cum[mid] <= t) lo = mid; else hi = mid;
    }
    const seg = this.cum[hi] - this.cum[lo] || 1;
    return lerp(this.pts[lo], this.pts[hi], (t - this.cum[lo]) / seg);
  }
  dir(s: number): V3 {
    const a = this.at(s - 0.4), b = this.at(s + 0.4);
    return sub(b, a);
  }
}

export const midUp = (a: V3, b: V3, h: number): V3 => add(lerp(a, b, 0.5), { x: 0, y: h, z: 0 });
