/**
 * Intelligent Beings of the 11th Dimension - gameplay entry point.
 */
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  ItemStack,
  Player,
  system,
  world,
} from "@minecraft/server";
import { ARCHON } from "./beings/archon.js";
import { OBSERVER } from "./beings/observer.js";
import { SOVEREIGN } from "./beings/sovereign.js";
import { runTasks } from "./core/tasks.js";
import { adopt, beingOf, defFor, hud, registerDef, tickBeings, allBeings } from "./engine.js";
import { sweepOrphans, tickMinions } from "./minions.js";
import { isRelic, tickRelics, useRelic } from "./relics.js";
import { openResonator, ritual } from "./summoning.js";

const RESONATOR = "dim11:resonator";
const BEING_KEYS: Record<string, typeof ARCHON> = { archon: ARCHON, sovereign: SOVEREIGN, observer: OBSERVER };
for (const def of Object.values(BEING_KEYS)) registerDef(def);

// --------------------------------------------------------------------------- commands

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("dim11:being", Object.keys(BEING_KEYS));
    reg.registerCommand(
      { name: "dim11:bestiary", description: "Read about the beings of the 11th dimension", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => void openResonator(p, false));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      {
        name: "dim11:summon",
        description: "Perform the summoning ritual for a being (in front of you)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "dim11:being", type: CustomCommandParamType.Enum }],
      },
      (origin, key: string) => {
        const p = origin.sourceEntity;
        const def = BEING_KEYS[key];
        if (!(p instanceof Player) || !def) return { status: CustomCommandStatus.Failure, message: "Players only / unknown being." };
        system.run(() => ritual(p, def));
        return { status: CustomCommandStatus.Success, message: `Ritual for ${def.name} begins.` };
      },
    );
    reg.registerCommand(
      { name: "dim11:resonator", description: "Receive an Eleventh-Dimensional Resonator", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(RESONATOR, 1)));
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch (e) {
    console.warn(`[dim11] custom commands unavailable: ${e}`);
  }
});

// --------------------------------------------------------------------------- items

const lastUse = new Map<string, number>();
function use(p: Player, id: string): void {
  const t = system.currentTick;
  if (t - (lastUse.get(p.id) ?? -10) < 4) return;
  lastUse.set(p.id, t);
  if (id === RESONATOR) void openResonator(p, true);
  else if (isRelic(id)) useRelic(p, id);
}

world.afterEvents.itemUse.subscribe((ev) => use(ev.source, ev.itemStack.typeId));
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  const id = ev.beforeItemStack?.typeId;
  if (id && ev.isFirstEvent && (id === RESONATOR || isRelic(id))) use(ev.player, id);
});

// --------------------------------------------------------------------------- beings appear / load

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (!e.isValid || !defFor(e.typeId)) return;
  system.runTimeout(() => {
    if (!e.isValid || beingOf(e)) return;
    const b = adopt(e);
    b?.say(b.def.lines.intro[0], true);
  }, 2);
});

world.afterEvents.entityLoad.subscribe((ev) => {
  if (ev.entity.isValid && defFor(ev.entity.typeId)) adopt(ev.entity);
});

// --------------------------------------------------------------------------- damage

world.beforeEvents.entityHurt.subscribe((ev) => {
  const victim = ev.hurtEntity;
  const src = ev.damageSource.damagingEntity;
  if (src && src.typeId.startsWith("dim11:") && victim.typeId.startsWith("dim11:")) {
    ev.cancel = true; // beings never hurt each other or their helpers
    return;
  }
  const b = beingOf(victim);
  if (!b) return;
  const dmg = b.incoming(ev.damage, ev.damageSource.cause);
  if (dmg <= 0) ev.cancel = true;
  else ev.damage = dmg;
});

world.afterEvents.entityHurt.subscribe((ev) => {
  const b = beingOf(ev.hurtEntity);
  if (b) b.damaged(ev.damage, ev.damageSource.cause, ev.damageSource.damagingEntity);
});

world.afterEvents.entityDie.subscribe((ev) => {
  const dead = ev.deadEntity;
  const killer = ev.damageSource.damagingEntity;
  if (dead instanceof Player && killer) {
    const b = beingOf(killer);
    if (b) b.onKill(dead);
  }
});

// --------------------------------------------------------------------------- loops

world.afterEvents.worldLoad.subscribe(() => {
  sweepOrphans();
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    for (const type of Object.values(BEING_KEYS).map((d) => d.typeId)) {
      for (const e of world.getDimension(id).getEntities({ type })) adopt(e);
    }
  }
  system.runInterval(() => {
    const t = system.currentTick;
    runTasks();
    tickBeings(t);
    tickMinions(t);
  }, 1);
  system.runInterval(() => {
    const t = system.currentTick;
    hud(t);
    tickRelics(world.getAllPlayers(), t);
  }, 10);
  console.log(`[dim11] Intelligent Beings of the 11th Dimension loaded (${allBeings().length} active)`);
});
