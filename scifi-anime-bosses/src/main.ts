/**
 * SCI-FI ANIME BOSSES - Boss 001: VESPER-0, The Ship That Learned to Pray.
 * Entry point: registration, event wiring and the main tick loop.
 */
import { Entity, system, world } from "@minecraft/server";
import { afterglow } from "./afterglow.js";
import { Vesper } from "./boss/controller.js";
import { resumeAfterLoad, startArrival } from "./boss/sequences.js";
import { registerCommands } from "./commands.js";
import { registerDamage } from "./damage.js";
import { ENT, PHASE } from "./generated/ids.js";
import { haloInFlight, onHaloUse, tickHalos } from "./halo.js";
import { bosses, clock, ledgerPrune, minions, parts } from "./registry.js";
import { onPsalterUse, tickHeldHints, tickRituals } from "./summon.js";
import { resetFxBudget } from "./util/fx.js";
import { groundY, safeRemove } from "./util/world.js";

const DIMENSIONS = ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"];

system.beforeEvents.startup.subscribe((ev) => {
  ev.itemComponentRegistry.registerCustomComponent("sab:psalter", { onUse: onPsalterUse });
  ev.itemComponentRegistry.registerCustomComponent("sab:orison", { onUse: onHaloUse });
  registerCommands(ev.customCommandRegistry);
});

registerDamage();

/** Take control of a boss entity that has no controller yet (world load, spawn egg, /summon). */
function adopt(e: Entity, fresh: boolean): void {
  if (bosses.has(e.id) || !e.isValid) return;
  const restored = e.getDynamicProperty("sab:arena") !== undefined;
  if (fresh && !restored) {
    // spawned by egg or command: the arena is here; rise and make an entrance
    const at = { ...e.location };
    const gy = groundY(e.dimension, at.x, at.z, at.y);
    const v = new Vesper(e, { x: at.x, y: gy, z: at.z });
    try {
      e.teleport({ x: at.x, y: Math.min(e.dimension.heightRange.max - 20, gy + 40), z: at.z });
    } catch {
      /* ignore */
    }
    v.persist();
    startArrival(v);
    return;
  }
  const v = new Vesper(e);
  resumeAfterLoad(v);
}

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (e.isValid && e.typeId === ENT.boss) system.run(() => adopt(e, true));
});

world.afterEvents.entityLoad.subscribe((ev) => {
  const e = ev.entity;
  if (e.isValid && e.typeId === ENT.boss) system.run(() => adopt(e, false));
});

world.afterEvents.entityRemove.subscribe((ev) => {
  const v = bosses.get(ev.removedEntityId);
  if (v) v.dispose(false);
  parts.delete(ev.removedEntityId);
  minions.delete(ev.removedEntityId);
});

function discover(): void {
  for (const id of DIMENSIONS) {
    try {
      for (const e of world.getDimension(id).getEntities({ type: ENT.boss })) adopt(e, false);
    } catch {
      /* dimension not loaded */
    }
  }
}

/**
 * Remove helper entities nothing controls any more (after a crash, reload or chunk unload). Landed cover plates of
 * a live phase II boss are adopted again instead, and a thrown Orison Halo survives only while it is in flight.
 */
function cleanupOrphans(): void {
  for (const id of DIMENSIONS) {
    let list: Entity[] = [];
    try {
      list = world.getDimension(id).getEntities({ families: ["sab_vesper"], excludeTypes: [ENT.boss] });
    } catch {
      continue;
    }
    for (const e of list) {
      if (parts.has(e.id) || minions.has(e.id)) continue;
      if (e.typeId === ENT.halo) {
        if (!haloInFlight(e.id)) safeRemove(e);
        continue;
      }
      let owner: unknown;
      try {
        owner = e.getDynamicProperty("sab:owner");
      } catch {
        owner = undefined;
      }
      const boss = typeof owner === "string" ? bosses.get(owner) : undefined;
      if (boss && e.typeId === ENT.lance && boss.beamId === e.id) continue; // the beam being fired right now
      if (boss && e.typeId === ENT.plate && boss.phase === PHASE.p2) {
        boss.adoptPlate(e);
        continue;
      }
      safeRemove(e);
    }
  }
}

system.runInterval(() => {
  clock.advance();
  resetFxBudget();
  ledgerPrune(clock.now);
  for (const v of [...bosses.values()]) {
    try {
      v.tick();
    } catch (err) {
      console.warn(`[VESPER-0] tick failed: ${err}`);
    }
    if (v.pendingDispose) v.dispose(true);
  }
  try {
    tickHalos();
    tickRituals();
    tickHeldHints(clock.now);
    afterglow.tick();
  } catch (err) {
    console.warn(`[VESPER-0] helper tick failed: ${err}`);
  }
  if (clock.now % 40 === 0) discover();
  if (clock.now % 200 === 100) cleanupOrphans();
}, 1);
