/**
 * Tribes of the Cosmos - gameplay entry point.
 *
 * Four playable tribes (Dinosauroid, Anunnaki, Flying Spaghetti Monster, Spacer),
 * each with passives, an energy resource, three abilities and an ultimate.
 */
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  EntityDamageCause,
  EntityHealthComponent,
  Player,
  system,
  world,
} from "@minecraft/server";
import { useRelic } from "./casting.js";
import { dropState, getRace, now, Race, state } from "./core/state.js";
import { runTasks } from "./core/tasks.js";
import { showHud } from "./hud.js";
import { applyPassives, giveCodex, joinTribe, resyncPlayer } from "./membership.js";
import { dismissAll, sweepOrphans, tickSummons } from "./summons.js";
import { CODEX_ITEM, TRIBES, tribeByKey, tribeByRelic, tribeOf } from "./tribes/index.js";
import { carbLoading, meatballSplash } from "./tribes/pastafarian.js";
import { openCodex } from "./ui.js";

const RAW_MEATS = new Set([
  "minecraft:beef",
  "minecraft:porkchop",
  "minecraft:chicken",
  "minecraft:mutton",
  "minecraft:rabbit",
  "minecraft:cod",
  "minecraft:salmon",
  "minecraft:rotten_flesh",
]);

// --------------------------------------------------------------------------- commands

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("tribes:tribe", ["dinosauroid", "anunnaki", "pastafarian", "spacer", "none"]);
    reg.registerCommand(
      { name: "tribes:codex", description: "Open the Tribal Codex (choose / study tribes)", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          giveCodex(p);
          void openCodex(p);
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      {
        name: "tribes:settribe",
        description: "Set your tribe directly",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "tribes:tribe", type: CustomCommandParamType.Enum }],
      },
      (origin, key: string) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        const tribe = tribeByKey(key);
        system.run(() => joinTribe(p, tribe));
        return { status: CustomCommandStatus.Success, message: `Tribe set to ${tribe?.name ?? "none"}.` };
      },
    );
    reg.registerCommand(
      { name: "tribes:energy", description: "Refill tribal energy and reset cooldowns", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        const s = state(p);
        s.energy = 100;
        s.cooldowns.clear();
        return { status: CustomCommandStatus.Success, message: "Energy refilled, cooldowns reset." };
      },
    );
  } catch (e) {
    console.warn(`[tribes] custom commands unavailable: ${e}`);
  }
});

// --------------------------------------------------------------------------- item use

world.afterEvents.itemUse.subscribe((ev) => {
  const id = ev.itemStack.typeId;
  if (id === CODEX_ITEM) {
    void openCodex(ev.source);
  } else if (tribeByRelic(id)) {
    useRelic(ev.source, id);
  }
});

world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  const id = ev.beforeItemStack?.typeId;
  if (!id || !ev.isFirstEvent) return;
  if (id === CODEX_ITEM) void openCodex(ev.player);
  else if (tribeByRelic(id)) useRelic(ev.player, id);
});

// --------------------------------------------------------------------------- energy sources

world.afterEvents.entityHitEntity.subscribe((ev) => {
  const p = ev.damagingEntity;
  if (!(p instanceof Player)) return;
  const tribe = tribeOf(getRace(p));
  if (!tribe) return;
  const s = state(p);
  s.energy = Math.min(100, s.energy + tribe.hitGain);
});

world.afterEvents.entityDie.subscribe((ev) => {
  const p = ev.damageSource.damagingEntity;
  if (!(p instanceof Player) || ev.deadEntity.id === p.id) return;
  const tribe = tribeOf(getRace(p));
  if (!tribe) return;
  const s = state(p);
  s.energy = Math.min(100, s.energy + tribe.killGain);
});

world.afterEvents.itemCompleteUse.subscribe((ev) => {
  const p = ev.source;
  const race = getRace(p);
  const id = ev.itemStack.typeId;
  if (race === Race.Dinosauroid && RAW_MEATS.has(id)) {
    system.run(() => {
      p.removeEffect("hunger");
      p.removeEffect("poison");
      p.addEffect("regeneration", 100, { amplifier: 1 });
      p.addEffect("saturation", 1, { amplifier: 1, showParticles: false });
      const s = state(p);
      s.energy = Math.min(100, s.energy + 15);
    });
  } else if (race === Race.Pastafarian && ev.itemStack.getComponent("minecraft:food")) {
    carbLoading(p, state(p));
  }
});

// --------------------------------------------------------------------------- damage rules

world.beforeEvents.entityHurt.subscribe((ev) => {
  const victim = ev.hurtEntity;
  const cause = ev.damageSource.cause;
  if (victim instanceof Player) {
    const race = getRace(victim);
    if (cause === EntityDamageCause.fall) {
      if (race === Race.Pastafarian) {
        ev.cancel = true;
        return;
      }
      if (state(victim).fallImmuneUntil >= now()) {
        ev.cancel = true;
        return;
      }
      if (race === Race.Spacer) ev.damage = ev.damage * 0.5;
    }
    // Your own guardians and lightning never hurt you.
    const src = ev.damageSource.damagingEntity;
    if (src && src.getDynamicProperty("tribes:owner") === victim.id) ev.cancel = true;
    if (cause === EntityDamageCause.lightning && race === Race.Anunnaki) ev.cancel = true;
  }
});

// --------------------------------------------------------------------------- projectiles

world.afterEvents.projectileHitEntity.subscribe((ev) => {
  if (ev.projectile.typeId !== "tribes:meatball") return;
  meatballSplash(ev.dimension, ev.location, ev.source instanceof Player ? ev.source : undefined);
});

world.afterEvents.projectileHitBlock.subscribe((ev) => {
  if (ev.projectile.typeId !== "tribes:meatball") return;
  meatballSplash(ev.dimension, ev.location, ev.source instanceof Player ? ev.source : undefined);
  try {
    if (ev.projectile.isValid) ev.projectile.remove();
  } catch {
    // already removed
  }
});

// --------------------------------------------------------------------------- lifecycle

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  system.runTimeout(() => {
    if (!p.isValid) return;
    resyncPlayer(p);
    if (ev.initialSpawn && p.getDynamicProperty("tribes:welcomed") !== true) {
      p.setDynamicProperty("tribes:welcomed", true);
      giveCodex(p);
      p.sendMessage(
        "§d§lTribes of the Cosmos§r\n§7Four tribes await: §aDinosauroid§7, §6Anunnaki§7, §eFlying Spaghetti Monster§7 and §bSpacer§7.\n" +
          "§7Use the §dTribal Codex§7 in your inventory (or type §f/tribes:codex§7) to choose your tribe.",
      );
    }
  }, 20);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  const p = ev.player;
  const id = p.id;
  // Before-events run in restricted mode: defer world changes.
  dismissAllLater(p);
  system.run(() => dropState(id));
});

function dismissAllLater(p: Player): void {
  system.run(() => {
    try {
      dismissAll(p);
    } catch {
      // player object already invalid; summons expire on their own timer
    }
  });
}

// --------------------------------------------------------------------------- main loop

function eachTribal(fn: (p: Player) => void): void {
  for (const p of world.getAllPlayers()) {
    if (!p.isValid) continue;
    try {
      fn(p);
    } catch (e) {
      console.warn(`[tribes] player tick failed: ${e}`);
    }
  }
}

world.afterEvents.worldLoad.subscribe(() => {
  sweepOrphans();
  for (const p of world.getAllPlayers()) resyncPlayer(p);

  system.runInterval(() => {
    runTasks();
    tickSummons();
  }, 1);

  // movement passives (glide / noodle flight)
  system.runInterval(() => {
    eachTribal((p) => {
      const tribe = tribeOf(getRace(p));
      tribe?.fastPassive?.(p, state(p));
    });
  }, 2);

  // energy regeneration + HUD
  system.runInterval(() => {
    const tick = now();
    eachTribal((p) => {
      const tribe = tribeOf(getRace(p));
      if (!tribe) return;
      const s = state(p);
      const mult = tribe.regenMultiplier?.(p) ?? 1;
      s.energy = Math.min(100, s.energy + tribe.regen * mult * 0.25);
      if (!s.hudEnabled) return;
      const held = p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex)?.typeId;
      if (held === tribe.relic || s.hudUntil > tick) showHud(p);
    });
  }, 5);

  // permanent and situational passives
  system.runInterval(() => {
    eachTribal((p) => {
      const tribe = tribeOf(getRace(p));
      applyPassives(p);
      if (!tribe) return;
      const health = p.getComponent(EntityHealthComponent.componentId);
      if (health && health.currentValue <= 0) return;
      tribe.slowPassive?.(p, state(p));
    });
  }, 40);

  console.log(`[tribes] Tribes of the Cosmos loaded: ${TRIBES.map((t) => t.name).join(", ")}`);
});
