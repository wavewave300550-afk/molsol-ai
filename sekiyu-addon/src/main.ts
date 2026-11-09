/**
 * Sekiyu Sekiyu no Mi — Petroleum (Logia). Gameplay entry point: events, commands, loops.
 */
import { CommandPermissionLevel, CustomCommandStatus, Player, system, world } from "@minecraft/server";
import { clearInfernoFog } from "./abilities/inferno.js";
import { tickSkillSwitch, useCore } from "./casting.js";
import { DP, Form, IDS, TUNING } from "./config.js";
import { hurt, ignite, isEnemy } from "./core/combat.js";
import { center, P, particle, S, sound } from "./core/fx.js";
import { runTasks } from "./core/tasks.js";
import { removeOwned, sweepOrphans } from "./constructs.js";
import { showHud } from "./hud.js";
import { deferDecision, judgeDamage, tickLogia } from "./logia.js";
import { tickPools } from "./pools.js";
import { giveCore, grantPower, hasCore, holdingCore, resetRuntime, revokePower, syncProperties } from "./power.js";
import { dropState, isOwner, now, state } from "./state.js";
import { openConsole } from "./ui.js";

// --------------------------------------------------------------------------- commands

const playerOf = (o: { sourceEntity?: unknown }): Player | undefined => (o.sourceEntity instanceof Player ? o.sourceEntity : undefined);
const FAIL = { status: CustomCommandStatus.Failure, message: "Players only." };

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  const cmd = (name: string, description: string, op: boolean, fn: (p: Player) => string | void) =>
    reg.registerCommand(
      { name, description, permissionLevel: op ? CommandPermissionLevel.GameDirectors : CommandPermissionLevel.Any, cheatsRequired: op },
      (origin) => {
        const p = playerOf(origin);
        if (!p) return FAIL;
        system.run(() => {
          const msg = fn(p);
          if (msg) p.sendMessage(msg);
        });
        return { status: CustomCommandStatus.Success };
      },
    );
  try {
    cmd("sekiyu:core", "Get a new Crude Core (petroleum users only)", false, (p) =>
      !isOwner(p) ? "§7Only a Sekiyu Sekiyu no Mi user can hold the core." : giveCore(p) ? undefined : "§7You already carry a Crude Core.");
    cmd("sekiyu:console", "Open the Oil Console", false, (p) => void openConsole(p));
    cmd("sekiyu:grant", "Grant yourself the petroleum power (testing)", true, (p) => (grantPower(p) ? undefined : "§7You already own the power."));
    cmd("sekiyu:revoke", "Remove the petroleum power from yourself", true, (p) => {
      revokePower(p);
      return "§7The oil drains from your body for good. (power removed)";
    });
    cmd("sekiyu:reset", "Reset cooldowns and form (testing)", true, (p) => {
      resetRuntime(p);
      state(p).cooldowns.clear();
      return "§7Cooldowns and form reset.";
    });
  } catch (e) {
    console.warn(`[sekiyu] custom commands unavailable: ${e}`);
  }
});

// --------------------------------------------------------------------------- the fruit

world.beforeEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack.typeId !== IDS.fruit || !isOwner(ev.source)) return;
  ev.cancel = true; // a second fruit is refused and kept
  const p = ev.source;
  system.run(() => p.isValid && p.sendMessage("§7Your body is already petroleum. A second fruit would do nothing."));
});

world.afterEvents.itemCompleteUse.subscribe((ev) => {
  if (ev.itemStack.typeId !== IDS.fruit) return;
  const p = ev.source;
  system.run(() => {
    if (!p.isValid || grantPower(p)) return;
    p.sendMessage("§7Your body is already petroleum. The fruit was returned.");
    try {
      p.getComponent("minecraft:inventory")?.container?.addItem(ev.itemStack.clone());
    } catch {
      // full inventory
    }
  });
});

// --------------------------------------------------------------------------- the core

world.afterEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack.typeId === IDS.core) useCore(ev.source, (p) => void openConsole(p));
});
world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (ev.beforeItemStack?.typeId === IDS.core && ev.isFirstEvent) useCore(ev.player, (p) => void openConsole(p));
});

// --------------------------------------------------------------------------- combat

// Petroleum Body: your melee blows flare with controlled fire.
world.afterEvents.entityHitEntity.subscribe((ev) => {
  const p = ev.damagingEntity;
  const target = ev.hitEntity;
  if (!(p instanceof Player) || !isOwner(p) || !target.isValid) return;
  const s = state(p);
  if (s.form !== Form.Body || s.sealed || !isEnemy(target, p)) return;
  const t = now();
  if (t - s.lastFlare < TUNING.body.flareCooldown) return;
  s.lastFlare = t;
  s.burningUntil = Math.max(s.burningUntil, t + 16);
  syncProperties(p, s);
  hurt(target, TUNING.body.flareDamage, p);
  ignite(target, TUNING.body.flareFireSeconds);
  particle(p.dimension, P.fire, center(target));
  sound(p.dimension, S.ignite, target.location, 0.6, 1.4);
});

// Logia defence, weaknesses and fire vulnerability.
world.beforeEvents.entityHurt.subscribe((ev) => {
  const p = ev.hurtEntity;
  if (!(p instanceof Player)) return;
  const src = ev.damageSource;
  const d = judgeDamage(p, src.cause, ev.damage, src.damagingEntity, src.damagingProjectile);
  if (d.cancel) ev.cancel = true;
  else if (d.damage !== undefined) ev.damage = d.damage;
  deferDecision(p, d, src.damagingEntity);
});

// --------------------------------------------------------------------------- lifecycle

world.afterEvents.entityDie.subscribe((ev) => {
  const p = ev.deadEntity;
  if (p instanceof Player && isOwner(p)) resetRuntime(p); // the power stays; forms and constructs end
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  system.runTimeout(() => {
    if (!p.isValid) return;
    clearInfernoFog(p);
    if (isOwner(p)) {
      if (!ev.initialSpawn) resetRuntime(p);
      state(p).synced = { form: -1, burning: false };
      syncProperties(p);
      if (!hasCore(p)) {
        giveCore(p);
        p.sendMessage("§7The §6Crude Core§7 oozes back into your hands.");
      }
    } else {
      syncProperties(p);
      if (ev.initialSpawn && p.getDynamicProperty(DP.welcomed) !== true) {
        p.setDynamicProperty(DP.welcomed, true);
        p.sendMessage("§6§lSekiyu Sekiyu no Mi§r §7add-on active. Find the fruit in the creative inventory or use §f/give @s sekiyu:sekiyu_fruit§7.");
      }
    }
  }, 20);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  const id = ev.player.id;
  system.run(() => {
    removeOwned(id);
    dropState(id);
  });
});

// --------------------------------------------------------------------------- loops

function eachOwner(fn: (p: Player) => void): void {
  for (const p of world.getAllPlayers()) {
    if (!p.isValid || !isOwner(p)) continue;
    try {
      fn(p);
    } catch (e) {
      console.warn(`[sekiyu] player tick failed: ${e}`);
    }
  }
}

world.afterEvents.worldLoad.subscribe(() => {
  const swept = sweepOrphans();
  if (swept) console.log(`[sekiyu] removed ${swept} leftover petroleum constructs`);
  for (const p of world.getAllPlayers()) syncProperties(p);
  system.runInterval(runTasks, 1);
  system.runInterval(() => eachOwner(tickSkillSwitch), 1);
  system.runInterval(() => {
    const t = now();
    eachOwner((p) => tickLogia(p, state(p), t));
  }, 2);
  system.runInterval(tickPools, 5);
  system.runInterval(() => {
    const t = now();
    eachOwner((p) => {
      const s = state(p);
      if (!s.hudEnabled) return;
      if (holdingCore(p) || s.form !== Form.Human || s.hudUntil > t || (s.followUp && s.followUp.until > t) || s.sealed) showHud(p);
    });
  }, 4);
  console.log("[sekiyu] Sekiyu Sekiyu no Mi - Petroleum loaded");
});
