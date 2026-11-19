/**
 * Custom slash commands (cheats + operator), mainly for creators and testers.
 *   /abm:summon <boss>         summon at your feet, bypassing the floor check
 *   /abm:arena <boss>          raise the demonstration arena around you (replaces blocks)
 *   /abm:dismiss               end the nearest encounter
 *   /abm:debug <action> [n]    on | off | phase2 | kill | attack <1-7> | info
 */
import {
  CommandPermissionLevel, CustomCommandParamType, CustomCommandStatus, Player, StartupEvent, system,
} from "@minecraft/server";
import { BOSS_KEYS, BossKey, CONFIG } from "./config";
import { manager } from "./core/manager";
import { saveSettings } from "./core/persistence";
import { useSeal } from "./items";
import { raiseArena } from "./ui";

const fail = (message: string) => ({ status: CustomCommandStatus.Failure, message });
const ok = (message?: string) => ({ status: CustomCommandStatus.Success, message });

export function registerCommands(ev: StartupEvent): void {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("abm:boss", [...BOSS_KEYS]);
    reg.registerEnum("abm:debug_action", ["on", "off", "phase2", "kill", "attack", "info"]);
    const lvl = CommandPermissionLevel.GameDirectors;

    reg.registerCommand(
      { name: "abm:summon", description: "Summon one of the Abandoned Miracles at your position", permissionLevel: lvl, cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:boss", type: CustomCommandParamType.Enum }] },
      (origin, boss: string) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return fail("Players only.");
        const l = p.location;
        system.run(() => useSeal(p, boss as BossKey, { x: Math.floor(l.x) + 0.5, y: Math.floor(l.y), z: Math.floor(l.z) + 0.5 }, true));
        return ok();
      },
    );
    reg.registerCommand(
      { name: "abm:arena", description: "Raise a demonstration arena around you (REPLACES blocks)", permissionLevel: lvl, cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:boss", type: CustomCommandParamType.Enum }] },
      (origin, boss: string) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return fail("Players only.");
        system.run(() => raiseArena(p, boss as BossKey));
        return ok();
      },
    );
    reg.registerCommand(
      { name: "abm:dismiss", description: "End the nearest Abandoned Miracles encounter", permissionLevel: lvl, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return fail("Players only.");
        const enc = manager.nearest(p.dimension, p.location);
        if (!enc) return fail("No encounter nearby.");
        system.run(() => manager.cancel(enc));
        return ok("Encounter dismissed.");
      },
    );
    reg.registerCommand(
      { name: "abm:debug", description: "Abandoned Miracles test controls", permissionLevel: lvl, cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:debug_action", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "value", type: CustomCommandParamType.Integer }] },
      (origin, action: string, value?: number) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return fail("Players only.");
        if (action === "on" || action === "off") {
          CONFIG.debug = action === "on";
          system.run(() => saveSettings());
          return ok(`Debug ${action}.`);
        }
        const enc = manager.nearest(p.dimension, p.location);
        if (!enc) return fail("No encounter nearby.");
        // command callbacks run in the restricted context: anything that changes the world waits a tick
        if (action === "phase2") system.run(() => enc.force("phase2"));
        else if (action === "kill") system.run(() => enc.force("death"));
        else if (action === "attack") {
          const a = enc.controller.attacks.find((x) => x.index === value);
          if (!a) return fail("attack needs a number 1-7.");
          enc.scheduler.forced = a.id;
          enc.nextAttackAt = 0;
          return ok(`Next attack: ${a.name}`);
        } else if (action === "info") {
          const used = [...enc.scheduler.usage.entries()].map(([k, n]) => `${k}:${n}`).join(" ");
          return ok(`${enc.key} ${enc.sm.top}/${enc.sm.sub} hp ${Math.round(enc.effectiveHealth())}/${Math.round(enc.effectiveMaxHealth())} scale ${enc.hpScale.toFixed(2)} players ${enc.targeting.count()} extra ${JSON.stringify(enc.controller.extra())} used ${used}`);
        }
        return ok();
      },
    );
  } catch (e) {
    console.warn(`[abm] custom commands unavailable: ${e}`);
  }
}
