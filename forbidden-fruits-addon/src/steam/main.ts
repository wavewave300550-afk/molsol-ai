/**
 * Jōki Jōki no Mi — Steam Pressure. Gameplay entry point.
 *
 * Event wiring, custom commands and the server loops. Abilities live in ./abilities,
 * balance values in ./config.ts.
 */
import {
  CommandPermissionLevel,
  CustomCommandStatus,
  EntityDamageCause,
  Player,
  system,
  world,
} from "@minecraft/server";
import { blockedBy, refund, refusal } from "../shared/fruits.js";
import { knucklePunch } from "./abilities/knuckle.js";
import { tickSkillSwitch, useValve } from "./casting.js";
import { HUD, IDS, Mode, MODES } from "./config.js";
import { isEnemy, knockAlong } from "./core/combat.js";
import { center, P, particle, S, sound } from "./core/fx.js";
import { runTasks } from "./core/tasks.js";
import { flatDir } from "./core/vec.js";
import { tickHeat } from "./heat.js";
import { showHud } from "./hud.js";
import { movementFx, refreshEffects } from "./modes.js";
import { giveValve, grantPower, hasValve, holdingValve, resetRuntime, revokePower, syncProperties } from "./power.js";
import { dropState, isOverheated, isOwner, now, state } from "./state.js";
import { openConsole } from "./ui.js";

// --------------------------------------------------------------------------- commands

function playerOnly(origin: { sourceEntity?: unknown }): Player | undefined {
  return origin.sourceEntity instanceof Player ? origin.sourceEntity : undefined;
}

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  const fail = { status: CustomCommandStatus.Failure, message: "Players only." };
  try {
    reg.registerCommand(
      { name: "joki:valve", description: "Get a new Steam Valve (Jōki Jōki users only)", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = playerOnly(origin);
        if (!p) return fail;
        system.run(() => {
          if (!isOwner(p)) p.sendMessage("§7Only a Jōki Jōki no Mi user can use the valve.");
          else if (!giveValve(p)) p.sendMessage("§7You already carry a Steam Valve.");
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "joki:console", description: "Open the Steam Console", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = playerOnly(origin);
        if (!p) return fail;
        system.run(() => void openConsole(p));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "joki:grant", description: "Grant yourself the Steam Pressure power (testing)", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = playerOnly(origin);
        if (!p) return fail;
        system.run(() => {
          if (!grantPower(p)) p.sendMessage("§7You already own the power.");
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "joki:revoke", description: "Remove the Steam Pressure power from yourself", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = playerOnly(origin);
        if (!p) return fail;
        system.run(() => {
          revokePower(p);
          p.sendMessage("§7The steam in your blood cools for good. (power removed)");
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "joki:cool", description: "Reset heat, overheat and cooldowns (testing)", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = playerOnly(origin);
        if (!p) return fail;
        system.run(() => {
          resetRuntime(p);
          state(p).cooldowns.clear();
          refreshEffects(p, state(p));
        });
        return { status: CustomCommandStatus.Success, message: "Heat, overheat and cooldowns reset." };
      },
    );
  } catch (e) {
    console.warn(`[joki] custom commands unavailable: ${e}`);
  }
});

// --------------------------------------------------------------------------- the fruit

// A user who already owns the power cannot eat a second fruit: the bite is refused and the fruit kept.
world.beforeEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack.typeId !== IDS.fruit) return;
  const p = ev.source;
  if (!isOwner(p)) return;
  ev.cancel = true;
  system.run(() => {
    if (!p.isValid) return;
    p.sendMessage("§7Your body already runs on steam. A second fruit would do nothing.");
    try {
      p.playSound(S.deny, { volume: 0.6 });
    } catch {
      // cosmetic
    }
  });
});

world.afterEvents.itemStartUse.subscribe((ev) => {
  if (ev.itemStack?.typeId !== IDS.fruit) return;
  particle(ev.source.dimension, P.handSteam, center(ev.source));
});

world.afterEvents.itemCompleteUse.subscribe((ev) => {
  if (ev.itemStack.typeId !== IDS.fruit) return;
  const p = ev.source;
  system.run(() => {
    if (!p.isValid) return;
    const other = blockedBy(p, IDS.fruit);
    if (other) {
      p.sendMessage(refusal(other));
      refund(p, IDS.fruit);
      return;
    }
    if (!grantPower(p)) {
      // Raced past the before-event guard: hand the fruit back so nothing is lost or duplicated.
      p.sendMessage("§7Your body already runs on steam. The fruit was returned.");
      try {
        p.getComponent("minecraft:inventory")?.container?.addItem(ev.itemStack.clone());
      } catch {
        // inventory full: nothing else we can do safely
      }
    }
  });
});

// --------------------------------------------------------------------------- the valve

world.afterEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack.typeId === IDS.valve) useValve(ev.source, (p) => void openConsole(p));
});

// Tapping a block on touch screens fires a block interaction instead of an item use.
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (ev.beforeItemStack?.typeId === IDS.valve && ev.isFirstEvent) useValve(ev.player, (p) => void openConsole(p));
});

// --------------------------------------------------------------------------- melee enhancement

world.afterEvents.entityHitEntity.subscribe((ev) => {
  const p = ev.damagingEntity;
  const target = ev.hitEntity;
  if (!(p instanceof Player) || !target.isValid || !isOwner(p)) return;
  const s = state(p);
  if (isOverheated(s)) return;
  const t = now();
  if (s.knucklePrimedUntil > t && isEnemy(target, p)) {
    knucklePunch(p, s, target);
    return;
  }
  const spec = MODES[s.mode];
  const boost = s.boostUntil > t;
  if (s.mode === Mode.Normal && !boost) return;
  // Strength (from the gear) already raises the damage; add a steam-driven shove and a scald puff.
  const knock = spec.meleeKnock + (boost ? 0.35 : 0);
  if (knock > 0 && isEnemy(target, p)) knockAlong(target, flatDir(p.location, target.location), 0.4 + knock, 0.3);
  particle(p.dimension, P.puff, center(target));
  if (s.mode >= Mode.Pressure) particle(p.dimension, P.ember, center(target));
  sound(p.dimension, S.hiss, target.location, 0.5, 1.6);
  if (s.mode === Mode.Redline && isEnemy(target, p)) {
    try {
      target.setOnFire(2, true);
    } catch {
      // fire immune
    }
  }
});

// --------------------------------------------------------------------------- damage rules

world.beforeEvents.entityHurt.subscribe((ev) => {
  const victim = ev.hurtEntity;
  if (!(victim instanceof Player)) return;
  if (ev.damageSource.cause !== EntityDamageCause.fall) return;
  if (!isOwner(victim)) return;
  if (state(victim).fallGuardUntil >= now()) ev.cancel = true;
});

// --------------------------------------------------------------------------- lifecycle

world.afterEvents.entityDie.subscribe((ev) => {
  const p = ev.deadEntity;
  if (!(p instanceof Player) || !isOwner(p)) return;
  // Death vents the boiler: heat, gear, overheat and active skills reset. The power itself stays.
  resetRuntime(p);
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  system.runTimeout(() => {
    if (!p.isValid) return;
    if (isOwner(p)) {
      if (!ev.initialSpawn) resetRuntime(p);
      state(p).synced = { mode: -1, heat: -1, overheat: false };
      syncProperties(p);
      if (!hasValve(p)) {
        giveValve(p);
        p.sendMessage("§7A fresh §6Steam Valve§7 hisses into your hands.");
      }
    } else {
      syncProperties(p); // the pack-wide welcome lives in shared/fruits.ts
    }
  }, 20);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  const id = ev.player.id;
  system.run(() => dropState(id));
});

// --------------------------------------------------------------------------- loops

function eachOwner(fn: (p: Player) => void): void {
  for (const p of world.getAllPlayers()) {
    if (!p.isValid || !isOwner(p)) continue;
    try {
      fn(p);
    } catch (e) {
      console.warn(`[joki] player tick failed: ${e}`);
    }
  }
}

world.afterEvents.worldLoad.subscribe(() => {
  for (const p of world.getAllPlayers()) syncProperties(p);

  system.runInterval(runTasks, 1);

  // every Sneak press with the valve in hand = next skill (checked each tick so quick taps count)
  system.runInterval(() => eachOwner(tickSkillSwitch), 1);

  system.runInterval(() => {
    const t = now();
    eachOwner((p) => {
      const s = state(p);
      if (p.isOnGround) s.airJumpsUsed = 0;
      movementFx(p, s, t);
    });
  }, 2);

  // heat, cooling, overheat recovery and timed gears (tickHeat assumes a 5-tick step)
  system.runInterval(() => eachOwner((p) => tickHeat(p, state(p))), 5);

  system.runInterval(() => {
    const t = now();
    eachOwner((p) => {
      const s = state(p);
      if (!s.hudEnabled) return;
      if (holdingValve(p) || s.mode !== Mode.Normal || s.heat >= 1 || isOverheated(s) || s.hudUntil > t) showHud(p);
    });
  }, HUD.period);

  system.runInterval(() => {
    eachOwner((p) => refreshEffects(p, state(p)));
  }, 20);

  console.log("[joki] Jōki Jōki no Mi - Steam Pressure loaded");
});
