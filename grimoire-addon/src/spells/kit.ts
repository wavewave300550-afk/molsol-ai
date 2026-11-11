import { Dimension, Entity, Player } from "@minecraft/server";
import type { Cast } from "./context";
import type { Fx, Rgb } from "../core/fx";
import { COLORS } from "../core/fx";
import { bodyCenter, push } from "../core/combat";
import type { Routine } from "../core/tasks";
import { V3, add, dist, flatNorm, len, lerp, mul, norm, sub, v3 } from "../core/vec";

/** applyKnockback horizontal units per (block/tick) of resulting velocity (BDS 1.26.63 calibration). */
export const KB_GAIN = 2.56;

export const SCHOOL_COL: Record<string, { a: Rgb; b: Rgb }> = {
  pressure: { a: COLORS.orange, b: COLORS.gold },
  ice: { a: COLORS.ice, b: COLORS.white },
  blood: { a: COLORS.crimson, b: COLORS.scarlet },
};

/** Approximately set an entity's velocity (players: applied client-side by the game). */
export function drive(e: Entity, vel: V3): void {
  if (!e.isValid) return;
  try {
    e.applyKnockback({ x: vel.x * KB_GAIN, z: vel.z * KB_GAIN }, vel.y);
  } catch {
    /* riding / invalid */
  }
}

/** First solid block along a segment (returns the free distance before it). */
export function freeDistance(dim: Dimension, from: V3, dir: V3, maxDist: number): number {
  try {
    const hit = dim.getBlockFromRay(from, norm(dir), { maxDistance: maxDist, includeLiquidBlocks: false, includePassableBlocks: false });
    if (hit) return Math.max(0, dist(from, add(hit.block.location, hit.faceLocation)));
  } catch {
    /* unloaded */
  }
  return maxDist;
}

export function isPassable(dim: Dimension, l: V3): boolean {
  try {
    const b = dim.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y), z: Math.floor(l.z) });
    if (!b) return false;
    return b.isAir || b.isLiquid || (b.typeId.includes("grass") && !b.typeId.includes("block")) || b.typeId === "minecraft:snow_layer";
  } catch {
    return false;
  }
}

/** A standing spot (feet + head free, solid or liquid support within 3 blocks below). */
export function safeSpot(dim: Dimension, p: V3): V3 | undefined {
  const base = { x: Math.floor(p.x) + 0.5, y: Math.floor(p.y), z: Math.floor(p.z) + 0.5 };
  for (const dy of [0, 1, -1, 2, -2, 3]) {
    const f = { x: base.x, y: base.y + dy, z: base.z };
    if (!isPassable(dim, f) || !isPassable(dim, add(f, v3(0, 1, 0)))) continue;
    for (let k = 1; k <= 4; k++) {
      if (!isPassable(dim, add(f, v3(0, -k, 0)))) return { x: f.x, y: f.y - k + 1, z: f.z };
    }
  }
  return undefined;
}

/** Teleport destination along the aim, never inside blocks (searches back toward the caster). */
export function teleportDestination(c: Cast, maxDist: number): V3 | undefined {
  const eye = c.eye();
  const dir = c.look();
  const free = freeDistance(c.dim, eye, dir, maxDist);
  for (let d = Math.max(1.5, free - 0.8); d >= 1.5; d -= 0.75) {
    const probe = add(eye, mul(dir, d));
    const s = safeSpot(c.dim, { x: probe.x, y: probe.y - 1.2, z: probe.z });
    if (s && dist(s, c.player.location) > 1.5) return s;
  }
  return undefined;
}

export function nearestEnemies(c: Cast, center: V3, radius: number, max: number): Entity[] {
  return c
    .enemies(center, radius)
    .map((e) => [e, dist(bodyCenter(e), center)] as const)
    .sort((a, b) => a[1] - b[1])
    .slice(0, max)
    .map(([e]) => e);
}

export interface ShockOptions {
  knock?: number;
  up?: number;
  color?: Rgb;
  color2?: Rgb;
  sound?: string;
  pitch?: number;
  shake?: number;
  particle?: string;
  inward?: boolean;
  minK?: number;
  ringLife?: number;
}

/** Shockwave: falloff damage, knockback away from (or toward) the center, ring + dust visuals. */
export function shock(c: Cast, center: V3, radius: number, damage: number, o: ShockOptions = {}): Entity[] {
  const col = o.color ?? SCHOOL_COL[c.spell.school].a;
  const hits = c.blast(center, radius, damage, (e, k) => {
    const d = sub(e.location, center);
    const dir = len(flatNorm(d)) > 0 ? flatNorm(d) : c.dir;
    push(e, o.inward ? mul(dir, -1) : dir, (o.knock ?? 1.2) * (0.5 + k), (o.up ?? 0.35) * (0.6 + k * 0.6));
  }, o.minK);
  c.particle(o.particle ?? "grimoire:ring_h", add(center, v3(0, 0.15, 0)), { color: col, color2: o.color2 ?? SCHOOL_COL[c.spell.school].b, radius: radius * 2.2 * c.area, life: o.ringLife ?? 1 });
  c.particle("grimoire:dust_ring", center, { color: { r: 0.75, g: 0.7, b: 0.62 }, radius: Math.min(4, radius * 0.5), size: 1.2, count: 1 });
  if (o.sound) c.sound(o.sound, center, 1.2, o.pitch ?? 1);
  if (o.shake) c.shake(center, radius * 3, o.shake, 0.5);
  return hits;
}

export interface FlyOptions {
  fx?: Fx;
  from: V3;
  dir: V3;
  speed: number;
  range: number;
  radius: number;
  /** Max number of entities hit (Infinity = full pierce). */
  pierce: number;
  homing?: Entity;
  homingRate?: number;
  arc?: V3;
  stopOnBlock?: boolean;
  trail?: string;
  trailColor?: Rgb;
  trailColor2?: Rgb;
  trailEvery?: number;
  onHit: (e: Entity, at: V3) => void;
  onTick?: (pos: V3, step: number) => void;
  onEnd?: (pos: V3, hitBlock: boolean) => void;
}

/** Step a projectile construct along its path: piercing hit sweeps, block stops, homing. */
export function* fly(c: Cast, o: FlyOptions): Routine {
  let pos = o.from;
  let dir = norm(o.dir);
  let travelled = 0;
  const hitIds = new Set<string>();
  let hits = 0;
  let step = 0;
  while (travelled < o.range) {
    if (o.homing && o.homing.isValid) {
      const want = norm(sub(bodyCenter(o.homing), pos));
      dir = norm(lerp(dir, want, o.homingRate ?? 0.25));
    }
    const stepLen = Math.min(o.speed, o.range - travelled);
    let next = add(pos, mul(dir, stepLen));
    if (o.arc) next = add(next, mul(o.arc, Math.sin((travelled / o.range) * Math.PI) * stepLen * 0.2));
    let blocked = false;
    if (o.stopOnBlock !== false) {
      const free = freeDistance(c.dim, pos, sub(next, pos), dist(pos, next) + 0.01);
      if (free < dist(pos, next) - 0.05) {
        next = add(pos, mul(norm(sub(next, pos)), free));
        blocked = true;
      }
    }
    for (const e of c.along(pos, next, o.radius)) {
      if (hitIds.has(e.id)) continue;
      hitIds.add(e.id);
      hits++;
      o.onHit(e, bodyCenter(e));
      if (hits >= o.pierce) {
        o.fx?.move(next);
        o.onEnd?.(bodyCenter(e), false);
        return;
      }
    }
    o.fx?.move(next).aim(sub(next, pos));
    if (o.trail && step % (o.trailEvery ?? 1) === 0) c.particle(o.trail, next, { color: o.trailColor, color2: o.trailColor2, size: 1, count: 1 });
    o.onTick?.(next, step);
    travelled += dist(pos, next);
    pos = next;
    step++;
    if (blocked) {
      o.onEnd?.(pos, true);
      return;
    }
    yield 1;
  }
  o.onEnd?.(pos, false);
}

/** Points evenly spread on a horizontal circle (for formations). */
export function circlePoints(center: V3, radius: number, n: number, y = 0, start = 0): V3[] {
  const out: V3[] = [];
  for (let i = 0; i < n; i++) {
    const a = start + (i / n) * Math.PI * 2;
    out.push({ x: center.x + Math.cos(a) * radius, y: center.y + y, z: center.z + Math.sin(a) * radius });
  }
  return out;
}

/** Offsets relative to the caster: right/up/forward in the caster's horizontal frame. */
export function local(p: Player | { yaw: number }, base: V3, right: number, up: number, fwd: number, yawDeg?: number): V3 {
  const yaw = ((yawDeg ?? (p instanceof Player ? p.getRotation().y : p.yaw)) * Math.PI) / 180;
  const f = { x: -Math.sin(yaw), z: Math.cos(yaw) };
  const r = { x: -f.z, z: f.x }; // right-hand side of the facing direction
  return { x: base.x + f.x * fwd + r.x * right, y: base.y + up, z: base.z + f.z * fwd + r.z * right };
}
