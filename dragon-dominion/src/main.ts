import { world } from "@minecraft/server";
import { registerStatusCommand } from "./commands.js";
import { ADDON_NAME, VERSION } from "./config.js";
import { logError, logInfo } from "./core/log.js";
import { CREATURES } from "./creatures/index.js";
import { CreatureRegistry } from "./creatures/registry.js";
import { CreatureRuntime } from "./creatures/runtime.js";
import { TierRegistry } from "./tiers/registry.js";
import { TIERS } from "./tiers/tiers.js";

const tiers = new TierRegistry(TIERS);
const creatures = new CreatureRegistry(CREATURES, tiers);
const problems = [...tiers.problems, ...creatures.problems];
const runtime = new CreatureRuntime(creatures, (id) => tiers.get(id));

// Content with configuration errors is not started: fail loudly instead of half-working.
if (problems.length === 0) runtime.start();
else for (const problem of problems) logError(`configuration error: ${problem}`);

function statusText(): string {
  const lines = [
    `${ADDON_NAME} v${VERSION}`,
    `tiers: ${tiers.size}, creatures: ${creatures.size}, loaded creature entities: ${runtime.activeCount}`,
  ];
  if (problems.length > 0) lines.push(`configuration errors: ${problems.length} (creature runtime disabled, see Content Log)`);
  return lines.join("\n");
}

registerStatusCommand(statusText);

world.afterEvents.worldLoad.subscribe(() => {
  logInfo(`v${VERSION} loaded (tiers: ${tiers.size}, creatures: ${creatures.size}, configuration errors: ${problems.length})`);
});
