// Boss registry: adopts boss entities as they spawn / load, ticks each one from a single interval, routes
// damage events, and forgets them when they unload or die. No per-tick world scans: bosses are discovered
// through spawn/load events (plus one scan of loaded entities when the scripts start).
import { system, world } from "@minecraft/server";
import { safe } from "./util.js";

const TYPES = new Map(); // typeId -> factory(entity) => controller
export const ACTIVE = new Map(); // entity id -> controller
let started = false;
let intervalId;

export function registerBoss(typeId, factory) {
  TYPES.set(typeId, factory);
  start();
}

export function controllerOf(entity) {
  return entity ? ACTIVE.get(entity.id) : undefined;
}

export function activeOfType(typeId) {
  return [...ACTIVE.values()].filter((c) => c.typeId === typeId && c.isValid());
}

function adopt(entity) {
  if (!entity || ACTIVE.has(entity.id)) return;
  const typeId = safe(() => entity.typeId);
  const f = TYPES.get(typeId);
  if (!f) return;
  const c = f(entity);
  ACTIVE.set(entity.id, c);
  ensureInterval();
}

function drop(id, reason) {
  const c = ACTIVE.get(id);
  if (!c) return;
  ACTIVE.delete(id);
  safe(() => c.dispose(reason));
  if (ACTIVE.size === 0 && intervalId !== undefined) {
    system.clearRun(intervalId);
    intervalId = undefined;
  }
}

function ensureInterval() {
  if (intervalId !== undefined) return;
  intervalId = system.runInterval(() => {
    for (const [id, c] of [...ACTIVE]) {
      if (!c.isValid()) {
        drop(id, "unloaded");
        continue;
      }
      let keep = true;
      try {
        keep = c.tick() !== false;
      } catch (err) {
        console.warn(`[dragon_dominion] ${c.typeId} tick error: ${err}`);
      }
      if (!keep) drop(id, "finished");
    }
  }, 1);
}

function start() {
  if (started) return;
  started = true;
  world.afterEvents.entitySpawn.subscribe((ev) => adopt(ev.entity));
  world.afterEvents.entityLoad.subscribe((ev) => adopt(ev.entity));
  world.beforeEvents.entityRemove.subscribe((ev) => {
    const id = safe(() => ev.removedEntity.id);
    if (id && ACTIVE.has(id)) system.run(() => drop(id, "removed"));
  });
  world.afterEvents.entityDie.subscribe((ev) => {
    const c = controllerOf(ev.deadEntity);
    if (c) {
      safe(() => c.onDie?.(ev));
      drop(ev.deadEntity.id, "died");
    }
  });
  world.beforeEvents.entityHurt.subscribe((ev) => {
    const c = controllerOf(ev.hurtEntity);
    if (c) c.onBeforeHurt?.(ev);
  });
  world.afterEvents.entityHurt.subscribe((ev) => {
    const c = controllerOf(ev.hurtEntity);
    if (c) safe(() => c.onHurt?.(ev));
  });
  world.afterEvents.playerLeave.subscribe((ev) => {
    for (const c of ACTIVE.values()) safe(() => c.onPlayerLeave?.(ev.playerId));
  });
  // bosses that were already loaded when the scripts (re)started
  system.run(() => {
    for (const dimId of ["overworld", "nether", "the_end"]) {
      for (const typeId of TYPES.keys()) {
        for (const e of safe(() => world.getDimension(dimId).getEntities({ type: typeId })) ?? []) adopt(e);
      }
    }
  });
}
