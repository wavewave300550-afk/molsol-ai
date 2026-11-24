/**
 * The Porcelain Emperor - Dragon Boss 001.
 *
 * Entry point: registers the custom dimension "The Fractured Mandate" and the
 * commands, and wires world events to the fight.
 */
import {
  CommandPermissionLevel, CustomCommandParamType, CustomCommandStatus, Entity, GameMode, ItemStack, Player, system, world,
} from "@minecraft/server";
import { tickCharms } from "./charm.js";
import { DIM_ID, ENT, ITEM } from "./config.js";
import { runTasks } from "./core/tasks.js";
import * as F from "./boss/fragments.js";
import { fight, giveItem } from "./fight/session.js";
import { sealMenu } from "./fight/ui.js";

const SKILL_NAMES = ["procession", "edict", "breath", "repair", "dive", "rubble", "claw", "storm", "kowtow", "rush"];

// --------------------------------------------------------------------------- startup: dimension + commands

system.beforeEvents.startup.subscribe((ev) => {
  try {
    ev.dimensionRegistry.registerCustomDimension(DIM_ID);
  } catch (e) {
    console.warn(`[porcelain] custom dimension registration failed: ${e}`);
  }
  const reg = ev.customCommandRegistry;
  const playerOnly = { status: CustomCommandStatus.Failure, message: "Players only." };
  try {
    reg.registerEnum("porcelain:skill", SKILL_NAMES);
    reg.registerCommand(
      { name: "porcelain:leave", description: "Leave the Fractured Mandate and return to where you entered", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return playerOnly;
        system.run(() => {
          if (fight.inMandate(p)) fight.returnHome(p, "§7You left the Fractured Mandate.");
          else p.sendMessage("§7You are not in the Fractured Mandate.");
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "porcelain:join", description: "Join a battle against the Porcelain Emperor that is in progress", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return playerOnly;
        system.run(() => {
          if (!fight.join(p)) p.sendMessage("§7There is no battle to join right now.");
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "porcelain:summon", description: "Open the Fractured Mandate without a seal (testing)", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return playerOnly;
        system.run(() => void fight.start(p, false));
        return { status: CustomCommandStatus.Success, message: "Opening the Fractured Mandate..." };
      },
    );
    reg.registerCommand(
      { name: "porcelain:seal", description: "Give yourself a Cracked Imperial Seal", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return playerOnly;
        system.run(() => giveItem(p, new ItemStack(ITEM.seal, 1)));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "porcelain:reset", description: "End the current Porcelain Emperor fight and close the Mandate", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      () => {
        system.run(() => fight.cleanup());
        return { status: CustomCommandStatus.Success, message: "The Mandate is closed." };
      },
    );
    reg.registerCommand(
      {
        name: "porcelain:phase",
        description: "Jump the Porcelain Emperor to phase 2 or 3 (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "phase", type: CustomCommandParamType.Integer }],
      },
      (_origin, phase: number) => {
        system.run(() => fight.forcePhase(phase));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      {
        name: "porcelain:skill",
        description: "Make the Porcelain Emperor use a skill next (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "porcelain:skill", type: CustomCommandParamType.Enum }],
      },
      (_origin, skill: string) => {
        system.run(() => {
          if (fight.boss?.valid && fight.state === "battle") fight.boss.forceSkill(skill);
        });
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch (e) {
    console.warn(`[porcelain] command registration failed: ${e}`);
  }
});

// --------------------------------------------------------------------------- main loop

system.runInterval(() => {
  fight.tick();
  runTasks();
  if (system.currentTick % 20 === 0) tickCharms();
}, 1);

world.afterEvents.worldLoad.subscribe(() => fight.recoverAfterLoad());

// --------------------------------------------------------------------------- items

world.afterEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack?.typeId === ITEM.seal) void sealMenu(ev.source);
});

// --------------------------------------------------------------------------- protecting the palace

const isBuilder = (p: Player): boolean => {
  try {
    return p.getGameMode() === GameMode.Creative;
  } catch {
    return false;
  }
};

world.beforeEvents.playerBreakBlock.subscribe((ev) => {
  if (fight.inMandate(ev.player) && !isBuilder(ev.player)) ev.cancel = true;
});

world.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
  const p = ev.player;
  // on touch screens a tap with the seal usually lands on a block: open the seal there too
  if (ev.itemStack?.typeId === ITEM.seal) {
    ev.cancel = true;
    if (ev.isFirstEvent) system.run(() => void sealMenu(p));
    return;
  }
  if (fight.inMandate(p) && !isBuilder(p)) ev.cancel = true;
});

world.beforeEvents.explosion.subscribe((ev) => {
  try {
    if (ev.dimension.id === fight.mandate().id) ev.setImpactedBlocks([]);
  } catch {
    // ignore
  }
});

// --------------------------------------------------------------------------- damage

world.beforeEvents.entityHurt.subscribe((ev) => {
  const e = ev.hurtEntity;
  const t = e.typeId;
  if (!t.startsWith("porcelain:")) return;
  const boss = fight.boss;
  if (t === ENT.emperor) {
    if (boss && boss.e.id === e.id) boss.onHurtBefore(ev);
    return;
  }
  if (t === ENT.claw && boss) {
    const src = ev.damageSource.damagingEntity;
    if (src && src.typeId.startsWith("porcelain:")) {
      ev.cancel = true;
      return;
    }
    boss.onClawHurt(ev.damage);
  }
});

world.afterEvents.entityDie.subscribe((ev) => {
  const e = ev.deadEntity;
  let t: string;
  try {
    t = e.typeId;
  } catch {
    return;
  }
  if (e instanceof Player) {
    fight.onPlayerDeath(e);
    return;
  }
  if (t === ENT.tablet || t === ENT.shard || t === ENT.rubble) {
    F.onFragmentDestroyed(e, ev.damageSource.damagingEntity);
    return;
  }
  if (t === ENT.emperor && fight.boss && fight.boss.e.id === e.id && !fight.boss.dying) {
    fight.onBossDefeated(ev.damageSource.damagingEntity instanceof Player);
  }
});

world.afterEvents.playerSpawn.subscribe((ev) => fight.onPlayerSpawn(ev.player, ev.initialSpawn));

// keep the Mandate free of anything that does not belong to the Emperor's court
world.afterEvents.entitySpawn.subscribe((ev) => {
  const e: Entity = ev.entity;
  try {
    if (!e.isValid || e.typeId.startsWith("porcelain:") || e instanceof Player) return;
    if (!fight.inMandate(e)) return;
    if (e.matches({ families: ["monster"] })) e.remove();
  } catch {
    // ignore
  }
});
