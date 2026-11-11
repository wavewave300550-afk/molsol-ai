/**
 * Keeps one BossController per Wrong Hatch entity, re-attaches controllers
 * after chunk / world reloads, and routes engine events to them.
 */
import { Entity, EntityHurtAfterEvent, world } from "@minecraft/server";
import { BOSS_ID } from "../config.js";
import { BossController } from "./controller.js";

const controllers = new Map<string, BossController>();
const missingSince = new Map<string, number>();

export function controllerFor(e: Entity | undefined): BossController | undefined {
  return e ? controllers.get(e.id) : undefined;
}

export function allControllers(): BossController[] {
  return [...controllers.values()];
}

export function attach(e: Entity): BossController | undefined {
  if (e.typeId !== BOSS_ID || !e.isValid) return undefined;
  let c = controllers.get(e.id);
  if (c && c.entity.isValid) return c;
  if (c && !c.entity.isValid) controllers.delete(e.id);
  try {
    c = new BossController(e);
  } catch (err) {
    console.warn(`[wrong_hatch] could not attach controller: ${err}`);
    return undefined;
  }
  controllers.set(e.id, c);
  missingSince.delete(e.id);
  return c;
}

export function detach(id: string, cleanup = true): void {
  const c = controllers.get(id);
  if (!c) return;
  if (cleanup) c.cleanup();
  controllers.delete(id);
  missingSince.delete(id);
}

/** Boss damage bookkeeping (phase gates, threat, scripted death). */
export function onAfterHurt(ev: EntityHurtAfterEvent): void {
  const victim = ev.hurtEntity;
  if (victim.typeId !== BOSS_ID) return;
  const c = controllers.get(victim.id);
  if (c && c.entity.id === victim.id) c.onHurt(ev);
}

export function tickControllers(now: number): void {
  for (const [id, c] of controllers) {
    if (!c.entity.isValid) {
      // unloaded or gone: re-resolve by id for a while, then forget (state lives in dynamic properties)
      const again = world.getEntity(id);
      if (again && again.isValid) {
        controllers.delete(id);
        attach(again);
        continue;
      }
      const since = missingSince.get(id) ?? now;
      missingSince.set(id, since);
      if (now - since > 200) detach(id, true);
      continue;
    }
    try {
      c.tick(now);
    } catch (e) {
      console.warn(`[wrong_hatch] boss tick failed: ${e}`);
    }
  }
}

/** Find bosses that exist in the world but have no controller (e.g. after a reload). */
export function discover(): void {
  for (const dimId of ["overworld", "nether", "the_end"]) {
    let list: Entity[] = [];
    try {
      list = world.getDimension(dimId).getEntities({ type: BOSS_ID });
    } catch {
      list = [];
    }
    for (const e of list) if (!controllers.has(e.id)) attach(e);
  }
}
