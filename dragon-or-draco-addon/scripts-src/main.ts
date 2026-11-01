/**
 * Dragon or Draco - Phase 1: Red Dragon (dod:red_dragon)
 *
 * Server-side brain: territory + warnings, target tracking, attack choice by range/angle,
 * the five approved attacks, script-steered flight and the death sequence.  Visual state goes
 * to the client through synced entity properties (dod:flight, dod:action, dod:aim, dod:run,
 * dod:jet) which drive the animation controllers.
 */
import { Entity, system, world } from "@minecraft/server";
import { beginDying, becomeHostile, think } from "./brain.js";
import { DRAGON_FAMILY, DRAGON_ID, DragonState, dragons, event, newState, safe, setProp } from "./dragon.js";
import { fxTick } from "./fx.js";

function register(e: Entity): DragonState | undefined {
  if (!e.isValid || e.typeId !== DRAGON_ID) return undefined;
  const known = dragons.get(e.id);
  if (known) {
    known.entity = e;
    return known;
  }
  const s = newState(e);
  dragons.set(e.id, s);
  const action = safe(() => e.getProperty("dod:action"));
  // normalise after a reload: always back on the ground, unlocked, no half-finished action
  event(s, "dod:to_ground");
  event(s, "dod:unlock");
  for (const [k, v] of [["dod:flight", "ground"], ["dod:action", "none"], ["dod:aim", 0], ["dod:run", false],
    ["dod:jet", 12]] as [string, string | number | boolean][]) {
    s.props[k] = "__unset__";
    setProp(s, k, v);
  }
  if (action === "death") beginDying(s); // it was dying when the world was saved: finish it
  return s;
}

function scan(): void {
  for (const id of ["overworld", "nether", "the_end"]) {
    const dim = safe(() => world.getDimension(id));
    const list = dim ? safe(() => dim.getEntities({ type: DRAGON_ID })) ?? [] : [];
    for (const e of list) register(e);
  }
}

world.afterEvents.entitySpawn.subscribe(({ entity }) => {
  if (entity.typeId === DRAGON_ID) register(entity);
});
world.afterEvents.entityLoad.subscribe(({ entity }) => {
  if (entity.typeId === DRAGON_ID) register(entity);
});
world.afterEvents.entityRemove.subscribe(({ removedEntityId }) => {
  dragons.delete(removedEntityId);
});
world.afterEvents.entityDie.subscribe(({ deadEntity }) => {
  dragons.delete(deadEntity.id);
});

// whoever hurts the dragon becomes its target (retaliation)
world.afterEvents.entityHurt.subscribe(({ hurtEntity, damageSource }) => {
  if (hurtEntity.typeId !== DRAGON_ID) return;
  const s = register(hurtEntity);
  const by = damageSource.damagingEntity;
  if (!s || s.dying || !by || !by.isValid) return;
  if (safe(() => by.matches({ families: [DRAGON_FAMILY] }))) return;
  becomeHostile(s, by);
}, { entityTypes: [DRAGON_ID] });

// a hit that would kill the dragon is cancelled and turned into the 2.8 s death sequence;
// while dying it takes no further damage. (restricted mode here: defer all changes)
world.beforeEvents.entityHurt.subscribe((ev) => {
  const e = ev.hurtEntity;
  const s = dragons.get(e.id);
  if (s?.allowKill) return;
  if (s?.dying) {
    ev.cancel = true;
    return;
  }
  const hp = safe(() => (e.getComponent("minecraft:health") as unknown as { currentValue: number }).currentValue);
  if (hp !== undefined && ev.damage >= hp) {
    ev.cancel = true;
    const id = e.id;
    system.run(() => {
      const st = dragons.get(id) ?? (e.isValid ? register(e) : undefined);
      if (st) beginDying(st);
    });
  }
}, { entityFilter: { type: DRAGON_ID } });

let ticks = 0;
system.runInterval(() => {
  ticks++;
  fxTick(system.currentTick);
  if (ticks === 1 || ticks % 40 === 0) scan();
  for (const [id, s] of dragons) {
    if (!s.entity.isValid) {
      dragons.delete(id);
      continue;
    }
    try {
      think(s);
    } catch (err) {
      // never let one bad tick kill the loop; reset the dragon to a safe state
      console.warn(`[Dragon or Draco] ${String(err)}`);
      s.run = undefined;
      setProp(s, "dod:action", "none");
    }
  }
}, 1);
