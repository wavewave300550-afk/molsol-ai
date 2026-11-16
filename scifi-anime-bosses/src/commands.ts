import {
  CommandPermissionLevel, CustomCommandOrigin, CustomCommandParamType, CustomCommandRegistry, CustomCommandResult,
  CustomCommandStatus, system, world,
} from "@minecraft/server";
import { bosses } from "./registry.js";
import { summonNow } from "./summon.js";

function ok(message: string): CustomCommandResult {
  return { status: CustomCommandStatus.Success, message };
}

function fail(message: string): CustomCommandResult {
  return { status: CustomCommandStatus.Failure, message };
}

export function registerCommands(reg: CustomCommandRegistry): void {
  reg.registerEnum("sab:vesper_action", ["summon", "despawn", "status"]);
  reg.registerCommand({
    name: "sab:vesper",
    description: "VESPER-0 admin tools: summon (skip the ritual), despawn, status",
    permissionLevel: CommandPermissionLevel.GameDirectors,
    cheatsRequired: true,
    mandatoryParameters: [{ name: "sab:vesper_action", type: CustomCommandParamType.Enum }],
  }, (origin: CustomCommandOrigin, action: string) => {
    const src = origin.sourceEntity ?? origin.initiator;
    if (action === "status") {
      const lines = [...bosses.values()].map((v) =>
        `VESPER-0 @ ${Math.round(v.pos.x)},${Math.round(v.pos.y)},${Math.round(v.pos.z)} phase=${v.phase} hp=${Math.round(v.health())}`);
      return ok(lines.length ? lines.join("\n") : "No active VESPER-0.");
    }
    if (action === "despawn") {
      const n = bosses.size;
      system.run(() => {
        for (const v of [...bosses.values()]) v.dispose(true);
      });
      return ok(`Despawning ${n} VESPER-0.`);
    }
    if (!src) return fail("Run this command as a player or entity.");
    const dim = src.dimension;
    const at = { ...src.location };
    system.run(() => summonNow(dim, at));
    return ok("VESPER-0 descends...");
  });

  reg.registerEnum("sab:toggle", ["on", "off"]);
  reg.registerCommand({
    name: "sab:vesper_cinematics",
    description: "Enable or disable VESPER-0's cinematic camera during its transformation",
    permissionLevel: CommandPermissionLevel.GameDirectors,
    cheatsRequired: false,
    mandatoryParameters: [{ name: "sab:toggle", type: CustomCommandParamType.Enum }],
  }, (_origin: CustomCommandOrigin, value: string) => {
    system.run(() => world.setDynamicProperty("sab:cinematics", value === "on"));
    return ok(`VESPER-0 cinematics ${value === "on" ? "enabled" : "disabled"}.`);
  });
}
