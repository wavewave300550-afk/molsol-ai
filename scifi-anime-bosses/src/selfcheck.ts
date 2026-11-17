import { EntityTypes, Player, world } from "@minecraft/server";
import { ENT } from "./generated/ids.js";

/**
 * Which of the add-on's entity types the game failed to register (the game rejects an entity file it cannot
 * load; items and scripts still work, so this would otherwise only show up as a boss that never appears).
 */
export function missingEntityTypes(): string[] {
  const out: string[] = [];
  for (const id of Object.values(ENT)) {
    try {
      if (!EntityTypes.get(id)) out.push(id);
    } catch {
      return []; // not answerable yet (early execution)
    }
  }
  return out;
}

export function reportMissing(players: Player[]): void {
  const missing = missingEntityTypes();
  if (!missing.length) return;
  const msg = `§c[VESPER-0] §fMinecraft could not load these add-on entities: §e${missing.join(", ")}§f. ` +
    "VESPER-0 cannot appear in this world. §7Open Settings > Creator > Content Log History and report the red lines " +
    "that mention sab:.";
  for (const p of players) {
    try {
      p.sendMessage(msg);
    } catch {
      /* ignore */
    }
  }
  console.warn(`[VESPER-0] entity types missing: ${missing.join(", ")}`);
}

export function reportMissingToAll(): void {
  try {
    reportMissing(world.getAllPlayers());
  } catch {
    /* ignore */
  }
}
