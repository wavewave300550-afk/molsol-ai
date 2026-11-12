import { CommandPermissionLevel, CustomCommandStatus, system } from "@minecraft/server";
import { nsId } from "./config.js";

/**
 * Registers /dragon_dominion:status, a read-only diagnostic that confirms the
 * scripts loaded and reports what is registered. It changes nothing in the world.
 */
export function registerStatusCommand(statusText: () => string): void {
  system.beforeEvents.startup.subscribe(({ customCommandRegistry }) => {
    customCommandRegistry.registerCommand(
      {
        name: nsId("status"),
        description: "Shows the Dragon Dominion version and registered content.",
        permissionLevel: CommandPermissionLevel.Any,
        cheatsRequired: false,
      },
      () => ({ status: CustomCommandStatus.Success, message: statusText() }),
    );
  });
}
