/**
 * Temporary helper entities ("proxies") owned by a player: Xenentoma's shed exuviae,
 * the Spaghetti Monster's meatballs, Nurariten's gates, heralds and processions.
 *
 * Every proxy has an owner, a lifetime and optional behaviour callbacks.  All of a
 * player's proxies are removed on death, logout, dimension change and lineage change,
 * and any proxy entity left in a world after a reload or crash is purged (family
 * plrace_proxy).  Proxy entities also carry a behavior-pack timer that despawns them on
 * their own, so nothing can be left behind even if scripts stop running.
 */
import { Dimension, Entity, Player, Vector3, system, world } from "@minecraft/server";
import { FAMILY_PROXY } from "../config.js";
import { warn } from "../core/util.js";

export type ProxyEnd = "expired" | "killed" | "owner" | "removed";

export interface Proxy {
  id: string;
  entity: Entity;
  owner: string;
  kind: string;
  born: number;
  until: number;
  /** every tick while alive; `age` = ticks since spawn */
  tick?: (px: Proxy, age: number) => void;
  /** struck (after-event); return true to end the proxy */
  hurt?: (px: Proxy, damage: number, attacker?: Entity) => boolean | void;
  /** the proxy is ending (entity is removed afterwards) */
  end?: (px: Proxy, reason: ProxyEnd) => void;
  data: Record<string, unknown>;
}

export interface ProxyOptions {
  kind: string;
  ticks: number;
  yaw?: number;
  event?: string;
  dim?: Dimension;
  tick?: Proxy["tick"];
  hurt?: Proxy["hurt"];
  end?: Proxy["end"];
  data?: Record<string, unknown>;
}

const proxies = new Map<string, Proxy>();

export function spawnProxy(owner: Player, typeId: string, loc: Vector3, o: ProxyOptions): Proxy | undefined {
  let e: Entity;
  try {
    e = (o.dim ?? owner.dimension).spawnEntity(typeId, loc, { initialRotation: o.yaw ?? 0, spawnEvent: o.event });
  } catch {
    return undefined; // unloaded chunk / outside the world
  }
  const now = system.currentTick;
  const px: Proxy = { id: e.id, entity: e, owner: owner.id, kind: o.kind, born: now, until: now + Math.max(1, o.ticks),
    tick: o.tick, hurt: o.hurt, end: o.end, data: o.data ?? {} };
  proxies.set(e.id, px);
  return px;
}

export function endProxy(px: Proxy, reason: ProxyEnd): void {
  if (!proxies.delete(px.id)) return;
  try {
    px.end?.(px, reason);
  } catch (err) {
    warn(`proxy ${px.kind} end failed`, err);
  }
  const e = px.entity;
  system.run(() => {
    try {
      if (e.isValid) e.remove();
    } catch {
      /* already gone */
    }
  });
}

export function isProxy(e: Entity): boolean {
  return proxies.has(e.id);
}

export function proxyOf(e: Entity): Proxy | undefined {
  return proxies.get(e.id);
}

export function proxiesOf(owner: string, kind?: string): Proxy[] {
  return [...proxies.values()].filter((px) => px.owner === owner && (kind === undefined || px.kind === kind));
}

export function removeProxiesOf(owner: string, kind?: string): void {
  for (const px of proxiesOf(owner, kind)) endProxy(px, "owner");
}

/** Every tick: lifetimes and behaviours.  Costs one size check when nothing is active. */
export function tickProxies(): void {
  if (proxies.size === 0) return;
  const now = system.currentTick;
  for (const px of [...proxies.values()]) {
    if (!px.entity.isValid) {
      endProxy(px, "removed");
      continue;
    }
    if (px.until <= now) {
      endProxy(px, "expired");
      continue;
    }
    try {
      px.tick?.(px, now - px.born);
    } catch (err) {
      warn(`proxy ${px.kind} tick failed`, err);
      endProxy(px, "removed");
    }
  }
}

export function proxyHurt(e: Entity, damage: number, attacker?: Entity): void {
  const px = proxies.get(e.id);
  if (!px) return;
  try {
    if (px.hurt?.(px, damage, attacker)) endProxy(px, "killed");
  } catch (err) {
    warn(`proxy ${px.kind} hurt failed`, err);
  }
}

export function proxyDied(e: Entity): void {
  const px = proxies.get(e.id);
  if (px) endProxy(px, "killed");
}

/** Remove proxy entities nobody owns any more (left over from a reload, crash or /reload). */
export function purgeOrphans(): number {
  let n = 0;
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let list: Entity[] = [];
    try {
      list = world.getDimension(id).getEntities({ families: [FAMILY_PROXY] });
    } catch {
      continue;
    }
    for (const e of list) {
      if (proxies.has(e.id)) continue;
      try {
        e.remove();
        n++;
      } catch {
        /* ignore */
      }
    }
  }
  return n;
}
