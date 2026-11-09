import { Dimension, Entity, Player, Vector3, world } from "@minecraft/server";
import { ENT, IGNITERS, POOLS, PROP } from "./config.js";
import { enemiesNear, hurt, ignite, oilSlow, onFire } from "./core/combat.js";
import { P, particle, S, sized, sound } from "./core/fx.js";
import { dist, v } from "./core/vec.js";
import { removeConstruct, setBurning, spawnConstruct } from "./constructs.js";
import { now } from "./state.js";

/**
 * Oil pools: the persistent-looking (but temporary) petroleum every ability leaves behind.
 * - heavy oil: enemies standing in it are slowed
 * - fire: a pool touching fire, lava, a burning entity or a burning pool ignites
 * - burning pools damage and ignite enemies, then the oil is consumed
 * Hard cap POOLS.max for the whole world; the oldest pool evaporates first.
 */
export interface Pool {
  e?: Entity;
  dim: Dimension;
  loc: Vector3;
  radius: number;
  until: number;
  burning: boolean;
  burnUntil: number;
  ownerId: string;
  born: number;
}

const pools: Pool[] = [];
let seq = 0;

const owner = (p: Pool): Player | undefined => {
  try {
    const e = world.getEntity(p.ownerId);
    return e instanceof Player ? e : undefined;
  } catch {
    return undefined;
  }
};

/** Surface under `at` (top of the first solid block within 8 blocks), or undefined over water/void. */
export function groundAt(dim: Dimension, at: Vector3): { loc: Vector3; igniter: boolean } | undefined {
  try {
    const hit = dim.getBlockFromRay(v(at.x, at.y + 1.2, at.z), v(0, -1, 0), { maxDistance: 9, includeLiquidBlocks: true, includePassableBlocks: false });
    if (!hit) return undefined;
    const id = hit.block.typeId;
    if (id === "minecraft:water" || id === "minecraft:flowing_water") return undefined;
    return { loc: v(at.x, hit.block.location.y + 1.02, at.z), igniter: IGNITERS.has(id) };
  } catch {
    return undefined;
  }
}

function setRadius(p: Pool): void {
  try {
    if (p.e?.isValid) p.e.setProperty(PROP.radius, Math.round(p.radius * 10) / 10);
  } catch {
    // ignore
  }
}

export function spawnPool(dim: Dimension, at: Vector3, radius: number, ownerId: string, opts: { burning?: boolean; ticks?: number } = {}): Pool | undefined {
  const g = groundAt(dim, at);
  if (!g) return undefined;
  const t = now();
  const burning = !!opts.burning || g.igniter;
  // merge into an overlapping pool instead of stacking entities
  for (const p of pools) {
    if (p.dim !== dim || Math.abs(p.loc.y - g.loc.y) > 1.5) continue;
    if (dist(p.loc, g.loc) < Math.max(1, Math.min(p.radius, radius) * 0.7)) {
      p.radius = Math.min(6, Math.max(p.radius, radius) + 0.3);
      p.until = Math.max(p.until, t + (opts.ticks ?? POOLS.lifetime));
      setRadius(p);
      if (burning) ignitePool(p);
      return p;
    }
  }
  while (pools.length >= POOLS.max) {
    const idx = pools.findIndex((p) => !p.burning);
    evaporate(pools[idx >= 0 ? idx : 0]);
  }
  const e = spawnConstruct(dim, ENT.pool, g.loc, ownerId, Math.random() * 360);
  if (!e) return undefined;
  const p: Pool = { e, dim, loc: g.loc, radius: Math.min(6, Math.max(0.5, radius)), until: t + (opts.ticks ?? POOLS.lifetime), burning: false, burnUntil: 0, ownerId, born: seq++ };
  pools.push(p);
  setRadius(p);
  particle(dim, P.splash, v(g.loc.x, g.loc.y + 0.2, g.loc.z));
  if (burning) ignitePool(p);
  return p;
}

export function ignitePool(p: Pool): void {
  if (p.burning) return;
  p.burning = true;
  p.burnUntil = now() + POOLS.burnTicks;
  setBurning(p.e, true);
  particle(p.dim, P.flash, v(p.loc.x, p.loc.y + 0.3, p.loc.z));
  sized(p.dim, P.poolFire, p.loc, p.radius);
  sound(p.dim, S.ignite, p.loc, 0.8, 0.9 + Math.random() * 0.3);
}

/** Ignite every pool touching the circle (at, radius). Returns how many caught fire. */
export function ignitePoolsNear(dim: Dimension, at: Vector3, radius: number): number {
  let n = 0;
  for (const p of pools) {
    if (p.dim !== dim || p.burning) continue;
    if (dist(p.loc, at) <= radius + p.radius && Math.abs(p.loc.y - at.y) < 4) {
      ignitePool(p);
      n++;
    }
  }
  return n;
}

export function burningPoolAt(dim: Dimension, at: Vector3): boolean {
  return pools.some((p) => p.burning && p.dim === dim && dist(p.loc, at) <= p.radius + 0.5 && Math.abs(p.loc.y - at.y) < 2);
}

function evaporate(p: Pool | undefined, smoke = false): void {
  if (!p) return;
  const i = pools.indexOf(p);
  if (i >= 0) pools.splice(i, 1);
  if (smoke) particle(p.dim, P.smoke, v(p.loc.x, p.loc.y + 0.4, p.loc.z));
  removeConstruct(p.e);
}

/** Every 5 ticks. */
export function tickPools(): void {
  const t = now();
  for (const p of [...pools]) {
    if (!p.e || !p.e.isValid) {
      evaporate(p);
      continue;
    }
    const ow = owner(p);
    if (p.burning) {
      if (t >= p.burnUntil) {
        evaporate(p, true); // the oil burned away
        continue;
      }
      if (t % 10 === 0) sized(p.dim, P.poolFire, p.loc, p.radius);
      if (t % 20 === 0) particle(p.dim, P.smoke, v(p.loc.x, p.loc.y + 0.6, p.loc.z));
      if (t % 40 === 0) sound(p.dim, S.crackle, p.loc, 0.5, 0.9 + Math.random() * 0.2);
      // fire spreads along connected oil
      for (const q of pools) if (!q.burning && q.dim === p.dim && dist(q.loc, p.loc) <= p.radius + q.radius + 0.5) ignitePool(q);
      if (t % POOLS.burnEvery === 0) {
        for (const e of enemiesNear(p.dim, p.loc, p.radius + 0.4, ow)) {
          if (Math.abs(e.location.y - p.loc.y) > 1.6) continue;
          hurt(e, POOLS.burnDamage, ow);
          ignite(e, 3);
        }
      }
      continue;
    }
    if (t >= p.until) {
      evaporate(p);
      continue;
    }
    for (const e of enemiesNear(p.dim, p.loc, p.radius + 0.3, ow)) {
      if (Math.abs(e.location.y - p.loc.y) > 1.2) continue;
      oilSlow(e, 15, POOLS.slowAmp);
      if (onFire(e)) ignitePool(p); // a burning creature walks into the oil
    }
    if (t % 20 === 0) {
      try {
        const below = p.dim.getBlock(v(p.loc.x, p.loc.y - 0.5, p.loc.z));
        const at = p.dim.getBlock(p.loc);
        if ((below && IGNITERS.has(below.typeId)) || (at && IGNITERS.has(at.typeId))) ignitePool(p);
      } catch {
        // unloaded
      }
    }
    if (t % 30 === 0) particle(p.dim, P.bubble, v(p.loc.x + (Math.random() - 0.5) * p.radius, p.loc.y + 0.1, p.loc.z + (Math.random() - 0.5) * p.radius));
  }
}

export const poolCount = (): number => pools.length;
export const poolsSnapshot = (): readonly Pool[] => pools;
export function clearPools(): void {
  for (const p of [...pools]) evaporate(p);
}
