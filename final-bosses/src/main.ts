/**
 * FIVE FINAL BOSSES - gameplay entry point.
 * The Void Emperor, the Titan of Creation, the Devouring Star, the World Parasite, the Choir of Mirrors.
 */
import { CommandPermissionLevel, CustomCommandParamType, CustomCommandStatus, Entity, EntityDamageCause, ItemStack, Player, system, world } from "@minecraft/server";
import { CHOIR, mirrorStruck } from "./bosses/choir.js";
import { EMPEROR } from "./bosses/emperor.js";
import { PARASITE } from "./bosses/parasite.js";
import { STAR, struggle } from "./bosses/star.js";
import { TITAN } from "./bosses/titan.js";
import { recoverJournal, tickBlocks } from "./core/blocks.js";
import { runTasks } from "./core/tasks.js";
import { hurt } from "./core/targets.js";
import { adopt, allBosses, BossDef, bossOf, defFor, hud, registerDef, tickBosses } from "./engine.js";
import { illusionOf, sweepOrphans, tickIllusions } from "./minions.js";
import { openSigil, ritual } from "./summoning.js";
import { isTrophy, reflecting, useTrophy } from "./trophies.js";

const SIGIL = "fb:boss_sigil";
const BOSSES: Record<string, BossDef> = { void_emperor: EMPEROR, titan: TITAN, devouring_star: STAR, world_parasite: PARASITE, choir: CHOIR };
for (const d of Object.values(BOSSES)) registerDef(d);
const ILLUSIONS = ["fb:choir_echo"];

// --------------------------------------------------------------------------- commands
system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("fb:boss", Object.keys(BOSSES));
    reg.registerCommand(
      { name: "fb:bosses", description: "Read the bestiary of the five final bosses", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => void openSigil(p, false));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      {
        name: "fb:summon", description: "Summon a final boss in front of you", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true,
        mandatoryParameters: [{ name: "fb:boss", type: CustomCommandParamType.Enum }],
      },
      (origin, key: string) => {
        const p = origin.sourceEntity;
        const def = BOSSES[key];
        if (!(p instanceof Player) || !def) return { status: CustomCommandStatus.Failure, message: "Players only / unknown boss." };
        system.run(() => ritual(p, def));
        return { status: CustomCommandStatus.Success, message: `Summoning ${def.name}...` };
      },
    );
    reg.registerCommand(
      { name: "fb:sigil", description: "Receive a Sigil of the Final Hour", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(SIGIL, 1)));
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch (e) {
    console.warn(`[fb] custom commands unavailable: ${e}`);
  }
});

// --------------------------------------------------------------------------- items
const lastUse = new Map<string, number>();
function use(p: Player, id: string): void {
  const t = system.currentTick;
  if (t - (lastUse.get(p.id) ?? -10) < 4) return;
  lastUse.set(p.id, t);
  if (id === SIGIL) void openSigil(p, true);
  else if (isTrophy(id)) useTrophy(p, id);
}
world.afterEvents.itemUse.subscribe((ev) => use(ev.source, ev.itemStack.typeId));
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  const id = ev.beforeItemStack?.typeId;
  if (id && ev.isFirstEvent && (id === SIGIL || isTrophy(id))) use(ev.player, id);
});

// --------------------------------------------------------------------------- bosses appear
world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (!e.isValid || !defFor(e.typeId)) return;
  system.runTimeout(() => {
    if (e.isValid && !bossOf(e)) adopt(e, true);
  }, 2);
});
world.afterEvents.entityLoad.subscribe((ev) => {
  if (ev.entity.isValid && defFor(ev.entity.typeId)) adopt(ev.entity, false);
});

// --------------------------------------------------------------------------- damage rules
world.beforeEvents.entityHurt.subscribe((ev) => {
  const victim = ev.hurtEntity;
  const src = ev.damageSource.damagingEntity;
  if (src && src.typeId.startsWith("fb:") && victim.typeId.startsWith("fb:")) {
    ev.cancel = true;
    return;
  }
  if (ILLUSIONS.includes(victim.typeId)) {
    ev.cancel = true;
    if (src instanceof Player && illusionOf(victim)) mirrorStruck(victim, src);
    return;
  }
  if (victim instanceof Player && reflecting(victim) && src && !(src instanceof Player)) {
    const back = ev.damage * 0.5;
    ev.damage = ev.damage * 0.5;
    const attacker: Entity = src;
    system.run(() => hurt(attacker, back, victim.isValid ? victim : undefined, EntityDamageCause.magic));
  }
  const b = bossOf(victim);
  if (!b) return;
  const dmg = b.incoming(ev.damage, ev.damageSource.cause, src);
  if (dmg <= 0) ev.cancel = true;
  else ev.damage = dmg;
});

world.afterEvents.entityHurt.subscribe((ev) => {
  const b = bossOf(ev.hurtEntity);
  if (b) b.damaged(ev.damage, ev.damageSource.damagingEntity);
});

world.afterEvents.entityDie.subscribe((ev) => {
  const killer = ev.damageSource.damagingEntity;
  if (ev.deadEntity instanceof Player && killer) bossOf(killer)?.onKill(ev.deadEntity);
});

world.afterEvents.entityStartSneaking.subscribe((ev) => {
  if (ev.entity instanceof Player) struggle(ev.entity);
});

// --------------------------------------------------------------------------- loops
world.afterEvents.worldLoad.subscribe(() => {
  const restored = recoverJournal();
  sweepOrphans(ILLUSIONS);
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    for (const def of Object.values(BOSSES)) for (const e of world.getDimension(id).getEntities({ type: def.typeId })) adopt(e, false);
  }
  system.runInterval(() => {
    const t = system.currentTick;
    runTasks();
    tickBosses(t);
    tickIllusions(t);
    tickBlocks();
  }, 1);
  system.runInterval(() => hud(system.currentTick), 10);
  console.log(`[fb] Five Final Bosses loaded (${allBosses().length} active, ${restored} journaled blocks restored)`);
});
