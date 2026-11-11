/**
 * BOSS 001: The Wrong Hatch - gameplay entry point.
 *
 * A monstrous chicken grown inside a living eggshell. Three phases, seventeen
 * regular abilities plus scripted set pieces (hatching intro, First Crack,
 * Final Hatch x2, death sequence), a hidden-outcome egg system, minions,
 * multiplayer health scaling and boss rewards.
 */
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  Player,
  system,
  world,
} from "@minecraft/server";
import { BOSS_ID, EGG_ID, LAST_HATCH_AT, PHASE2_AT, PHASE3_AT, SHELL_ID } from "./config.js";
import { isTrackedEgg, smashEgg, tickBrood } from "./boss/brood.js";
import { tickHazards } from "./boss/hazards.js";
import { onShellBroken } from "./boss/phases.js";
import { allControllers, attach, controllerFor, detach, discover, onBeforeHurt, tickControllers } from "./boss/registry.js";
import { onItemCompleteUse, onItemUse, onPlayerHit, startRitual, tickRituals } from "./rewards.js";

// --------------------------------------------------------------------------- commands (testing helpers)

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerCommand(
      { name: "wh:summon", description: "Summon The Wrong Hatch at your position", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          p.dimension.spawnEntity(BOSS_ID, p.location);
        });
        return { status: CustomCommandStatus.Success, message: "The egg is hatching..." };
      },
    );
    reg.registerCommand(
      {
        name: "wh:phase",
        description: "Jump the nearest Wrong Hatch to phase 2 or 3 (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "phase", type: CustomCommandParamType.Integer }],
      },
      (origin, phase: number) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          const boss = p.dimension.getEntities({ type: BOSS_ID, location: p.location, closest: 1, maxDistance: 64 })[0];
          const c = controllerFor(boss);
          const h = c?.health();
          if (!c || !h) return;
          const frac = phase >= 3 ? PHASE3_AT - 0.01 : phase === 2 ? PHASE2_AT - 0.01 : LAST_HATCH_AT;
          h.setCurrentValue(Math.max(2, h.effectiveMax * frac));
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "wh:clear", description: "Remove every Wrong Hatch and its brood", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      () => {
        system.run(() => {
          for (const c of allControllers()) {
            c.despawn();
            detach(c.id, false);
          }
        });
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch (e) {
    console.warn(`[wrong_hatch] command registration failed: ${e}`);
  }
});

// --------------------------------------------------------------------------- events

world.beforeEvents.entityHurt.subscribe((ev) => onBeforeHurt(ev));

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (e.isValid && e.typeId === BOSS_ID) attach(e);
});

world.afterEvents.entityLoad.subscribe((ev) => {
  const e = ev.entity;
  if (e.isValid && e.typeId === BOSS_ID) attach(e);
});

world.afterEvents.entityDie.subscribe((ev) => {
  const dead = ev.deadEntity;
  const killer = ev.damageSource.damagingEntity;
  if (dead.typeId === EGG_ID) {
    if (isTrackedEgg(dead.id)) smashEgg(dead.id, killer);
  } else if (dead.typeId === SHELL_ID) {
    for (const c of allControllers()) {
      if (c.shells.some((s) => s.id === dead.id)) onShellBroken(c, dead);
    }
  } else if (dead.typeId === BOSS_ID) {
    // only reachable through /kill or similar: the scripted death never lets health hit 0
    detach(dead.id, true);
  }
});

world.afterEvents.itemUse.subscribe((ev) => onItemUse(ev.source, ev.itemStack));
world.afterEvents.itemCompleteUse.subscribe((ev) => onItemCompleteUse(ev.source, ev.itemStack));
world.afterEvents.entityHitEntity.subscribe((ev) => {
  if (ev.damagingEntity instanceof Player) onPlayerHit(ev.damagingEntity, ev.hitEntity);
});
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (!ev.isFirstEvent || ev.itemStack?.typeId !== "wh:suspicious_egg") return;
  const b = ev.block;
  startRitual(ev.player, { x: b.location.x + 0.5, y: b.location.y + 1, z: b.location.z + 0.5 });
});

// --------------------------------------------------------------------------- main loop

system.runInterval(() => {
  const now = system.currentTick;
  tickControllers(now);
  tickHazards(now);
  tickBrood(now);
  tickRituals();
  if (now % 40 === 0) discover();
}, 1);
