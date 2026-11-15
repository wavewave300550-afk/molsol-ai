/**
 * Arena helpers: the bosses live in their own void dimensions (BP dimensions/),
 * so encounters never touch the player's world. Players are moved in and out
 * with a remembered return point.
 */
import { Dimension, EntityDamageCause, GameMode, Player, system, world } from "@minecraft/server";
import { V3 } from "./vec.js";

const RETURN_KEY = "anatomy:return";

interface ReturnPoint {
  d: string;
  x: number;
  y: number;
  z: number;
}

export function arenaDimension(id: string): Dimension {
  return world.getDimension(id);
}

export function setReturnPoint(p: Player): void {
  if (p.getDynamicProperty(RETURN_KEY) !== undefined && p.dimension.id.startsWith("anatomy:")) return;
  const rp: ReturnPoint = { d: p.dimension.id, x: p.location.x, y: p.location.y, z: p.location.z };
  p.setDynamicProperty(RETURN_KEY, JSON.stringify(rp));
}

export function getReturnPoint(p: Player): ReturnPoint | undefined {
  const raw = p.getDynamicProperty(RETURN_KEY);
  if (typeof raw !== "string") return undefined;
  try {
    return JSON.parse(raw) as ReturnPoint;
  } catch {
    return undefined;
  }
}

export function enterArena(p: Player, dim: Dimension, pos: V3, facing: V3): boolean {
  setReturnPoint(p);
  try {
    p.teleport(pos, { dimension: dim, facingLocation: facing, keepVelocity: false });
    return true;
  } catch (e) {
    console.warn(`[anatomy] could not move ${p.name} into ${dim.id}: ${String(e)}`);
    return false;
  }
}

export function leaveArena(p: Player): void {
  const rp = getReturnPoint(p);
  p.setDynamicProperty(RETURN_KEY, undefined);
  try {
    if (rp && !rp.d.startsWith("anatomy:")) {
      p.teleport({ x: rp.x, y: rp.y, z: rp.z }, { dimension: world.getDimension(rp.d) });
    } else {
      const sp = p.getSpawnPoint();
      if (sp) p.teleport({ x: sp.x + 0.5, y: sp.y, z: sp.z + 0.5 }, { dimension: sp.dimension });
      else p.teleport(world.getDefaultSpawnLocation(), { dimension: world.getDimension("minecraft:overworld") });
    }
  } catch (e) {
    console.warn(`[anatomy] could not return ${p.name}: ${String(e)}`);
  }
}

export function playersIn(dimId: string): Player[] {
  return world.getAllPlayers().filter((p) => p.isValid && p.dimension.id === dimId);
}

/** Combat-relevant players: survival/adventure, alive. */
export function combatants(dimId: string): Player[] {
  return playersIn(dimId).filter((p) => {
    try {
      const gm = p.getGameMode();
      return gm === GameMode.Survival || gm === GameMode.Adventure;
    } catch {
      return false;
    }
  });
}

/**
 * Keeps a rectangular area loaded via the TickingAreaManager (async: resolves once loaded).
 * Falls back to splitting the area if a single area is too large.
 */
export async function loadArea(id: string, dim: Dimension, from: V3, to: V3): Promise<boolean> {
  const tam = world.tickingAreaManager;
  try {
    if (tam.hasTickingArea(id)) tam.removeTickingArea(id);
    const opts = { dimension: dim, from, to };
    if (!tam.hasCapacity(opts)) {
      console.warn(`[anatomy] ticking area ${id} exceeds capacity (${tam.chunkCount}/${tam.maxChunkCount} chunks used)`);
      // try two halves
      const midX = Math.floor((from.x + to.x) / 2);
      const a = { dimension: dim, from, to: { x: midX, y: to.y, z: to.z } };
      const b = { dimension: dim, from: { x: midX + 1, y: from.y, z: from.z }, to };
      if (!tam.hasCapacity(a)) return false;
      await tam.createTickingArea(id, a);
      if (tam.hasCapacity(b)) await tam.createTickingArea(id + "_b", b);
      return true;
    }
    await tam.createTickingArea(id, opts);
    return true;
  } catch (e) {
    console.warn(`[anatomy] ticking area ${id} failed: ${String(e)}`);
    return false;
  }
}

export function unloadArea(id: string): void {
  const tam = world.tickingAreaManager;
  for (const n of [id, id + "_b"]) {
    try {
      if (tam.hasTickingArea(n)) tam.removeTickingArea(n);
    } catch {
      /* ignore */
    }
  }
}

/** Damage a player with the boss as the source when possible (death messages, armour). */
export function hurt(p: Player, amount: number, cause: EntityDamageCause, source?: import("@minecraft/server").Entity): boolean {
  if (amount <= 0 || !p.isValid) return false;
  try {
    return p.applyDamage(amount, source && source.isValid ? { cause, damagingEntity: source } : { cause });
  } catch {
    try {
      return p.applyDamage(amount, { cause });
    } catch {
      return false;
    }
  }
}

export function knock(p: Player, dx: number, dz: number, horizontal: number, vertical: number): void {
  const l = Math.hypot(dx, dz) || 1;
  try {
    p.applyKnockback({ x: (dx / l) * horizontal, z: (dz / l) * horizontal }, vertical);
  } catch {
    /* ignore */
  }
}

export function after(ticks: number, fn: () => void): void {
  system.runTimeout(fn, ticks);
}
