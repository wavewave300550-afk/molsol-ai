import { Dimension } from "@minecraft/server";
import { bodyClear, groundY, lineClear } from "../core/terrain.js";
import { add, dist, flatDir, lerp, norm, perpXZ, scale, sub, v, V3 } from "../core/vec.js";

/** Curve builders. All return dense point lists (resampled later by Path). */

export function line(a: V3, b: V3, step = 0.5): V3[] {
  const n = Math.max(1, Math.ceil(dist(a, b) / step));
  const out: V3[] = [];
  for (let i = 0; i <= n; i++) out.push(lerp(a, b, i / n));
  return out;
}

export function polyline(points: V3[]): V3[] {
  const out: V3[] = [];
  for (let i = 1; i < points.length; i++) {
    const seg = line(points[i - 1], points[i]);
    if (i > 1) seg.shift();
    out.push(...seg);
  }
  return out;
}

export function bezier(p0: V3, p1: V3, p2: V3, p3: V3, n = 40): V3[] {
  const out: V3[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = (1 - t) ** 3;
    const b = 3 * (1 - t) ** 2 * t;
    const c = 3 * (1 - t) * t * t;
    const d = t ** 3;
    out.push({
      x: a * p0.x + b * p1.x + c * p2.x + d * p3.x,
      y: a * p0.y + b * p1.y + c * p2.y + d * p3.y,
      z: a * p0.z + b * p1.z + c * p2.z + d * p3.z,
    });
  }
  return out;
}

/** Smooth curve through the given points (Catmull-Rom). */
export function catmull(points: V3[], perSeg = 8): V3[] {
  if (points.length < 3) return polyline(points);
  const out: V3[] = [];
  const P = [points[0], ...points, points[points.length - 1]];
  for (let i = 1; i < P.length - 2; i++) {
    const p0 = P[i - 1];
    const p1 = P[i];
    const p2 = P[i + 1];
    const p3 = P[i + 2];
    for (let k = 0; k < perSeg; k++) {
      const t = k / perSeg;
      const t2 = t * t;
      const t3 = t2 * t;
      const f = (a: number, b: number, c: number, d: number) =>
        0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      out.push({ x: f(p0.x, p1.x, p2.x, p3.x), y: f(p0.y, p1.y, p2.y, p3.y), z: f(p0.z, p1.z, p2.z, p3.z) });
    }
  }
  out.push(points[points.length - 1]);
  return out;
}

/** Horizontal circle. a0 in radians, turns may be fractional; ccw=false runs clockwise seen from above. */
export function circle(c: V3, r: number, a0 = 0, turns = 1, ccw = true): V3[] {
  const n = Math.max(12, Math.ceil((2 * Math.PI * r * Math.abs(turns)) / 0.5));
  const out: V3[] = [];
  const sgn = ccw ? 1 : -1;
  const lastI = Math.abs(turns) >= 1 ? n - 1 : n;
  for (let i = 0; i <= lastI; i++) {
    const a = a0 + sgn * (i / n) * turns * 2 * Math.PI;
    out.push(v(c.x + Math.cos(a) * r, c.y, c.z + Math.sin(a) * r));
  }
  return out;
}

/** Horizontal spiral from radius r0 to r1. */
export function spiral(c: V3, r0: number, r1: number, a0: number, turns: number, ccw = true): V3[] {
  const n = Math.max(20, Math.ceil((Math.PI * (r0 + r1) * Math.abs(turns)) / 0.5));
  const out: V3[] = [];
  const sgn = ccw ? 1 : -1;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = a0 + sgn * t * turns * 2 * Math.PI;
    const r = r0 + (r1 - r0) * t;
    out.push(v(c.x + Math.cos(a) * r, c.y, c.z + Math.sin(a) * r));
  }
  return out;
}

/** Ring tilted around the horizontal axis `axis` by `tilt` radians (orbits of Heaven's Detour). */
export function tiltedRing(c: V3, r: number, tilt: number, yaw: number, ccw = true): V3[] {
  const out: V3[] = [];
  const n = Math.max(16, Math.ceil((2 * Math.PI * r) / 0.5));
  const sgn = ccw ? 1 : -1;
  for (let i = 0; i < n; i++) {
    const a = sgn * (i / n) * 2 * Math.PI;
    let p = v(Math.cos(a) * r, 0, Math.sin(a) * r);
    // tilt around X, then yaw around Y
    p = v(p.x, -p.z * Math.sin(tilt), p.z * Math.cos(tilt));
    const cy = Math.cos(yaw);
    const sy = Math.sin(yaw);
    p = v(p.x * cy - p.z * sy, p.y, p.x * sy + p.z * cy);
    out.push(add(c, p));
  }
  return out;
}

/** Aerial arc from a to b peaking `apex` blocks above the higher end. */
export function skyArc(a: V3, b: V3, apex: number, n = 40): V3[] {
  const top = Math.max(a.y, b.y) + apex;
  const d = sub(b, a);
  const c1 = add(a, v(d.x * 0.25, top - a.y + apex * 0.3, d.z * 0.25));
  const c2 = add(a, v(d.x * 0.75, top - a.y + apex * 0.3, d.z * 0.75));
  return bezier(a, c1, c2, b, n);
}

/** Aerial road with a vertical loop-de-loop in the middle (Burning Pilgrimage). */
export function loopRoad(a: V3, b: V3, loopR: number): V3[] {
  const dir = flatDir(a, b);
  const mid = lerp(a, b, 0.45);
  const climb = add(mid, v(0, 3.5, 0));
  const entry = sub(climb, scale(dir, loopR * 0.2));
  const out: V3[] = [...bezier(a, lerp(a, entry, 0.4), add(entry, v(0, 1, 0)), entry, 16)];
  // vertical circle in the plane containing dir and up, centred above entry
  const c = add(entry, v(0, loopR, 0));
  const steps = 28;
  for (let i = 1; i <= steps; i++) {
    const ang = -Math.PI / 2 + (i / steps) * 2 * Math.PI;
    const side = scale(perpXZ(dir), (i / steps) * 1.2); // slight sideways drift so the loop does not self-intersect
    out.push(add(add(c, add(scale(dir, Math.cos(ang) * loopR), v(0, Math.sin(ang) * loopR, 0))), side));
  }
  const exit = out[out.length - 1];
  out.push(...bezier(exit, add(exit, scale(dir, 3)), add(b, v(0, 3, 0)), b, 16).slice(1));
  return out;
}

/** Zig-zag through waypoints with rounded corners. */
export function zigzag(points: V3[]): V3[] {
  return catmull(points, 10);
}

/**
 * Make a ground road follow the terrain: every point is dropped onto the
 * walkable surface (searching from refY), heights are smoothed, and the road
 * is cut where it would climb a wall or fall off a cliff.
 */
export function conform(dim: Dimension, pts: V3[], refY: number, maxStep = 1.6): V3[] {
  const out: V3[] = [];
  let prevY = refY;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    const g = groundY(dim, p.x, p.z, Math.max(prevY, p.y), 8);
    let y = g === undefined ? prevY : g;
    if (Math.abs(y - prevY) > maxStep && i > 0) {
      // wall or drop: a cliff edge is bridged in the air, a wall stops the road
      if (y > prevY) break;
      y = prevY;
    }
    if (!bodyClear(dim, v(p.x, y, p.z), 1.7)) break; // a real wall (plants and snow layers are passable)
    out.push(v(p.x, y + 0.05, p.z));
    prevY = y;
  }
  // smooth heights (3-tap)
  for (let k = 0; k < 2; k++) {
    for (let i = 1; i < out.length - 1; i++) {
      out[i] = v(out[i].x, (out[i - 1].y + out[i].y * 2 + out[i + 1].y) / 4, out[i].z);
    }
  }
  return out;
}

/** Clip an aerial curve where a solid block crosses it (passable blocks are ignored). */
export function clipAir(dim: Dimension, pts: V3[], bodyHeight = 2.0): V3[] {
  const out: V3[] = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    if (i > 0 && !lineClear(dim, add(pts[i - 1], v(0, 0.3, 0)), add(p, v(0, 0.3, 0)))) break;
    if (i % 2 === 0 && !bodyClear(dim, p, bodyHeight)) break;
    out.push(p);
  }
  return out;
}

export { norm };
