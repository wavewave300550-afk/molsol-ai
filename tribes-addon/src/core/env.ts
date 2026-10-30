import { Player, world } from "@minecraft/server";

/** True when the player stands under open sky in the overworld during the day. */
export function isDaylight(player: Player): boolean {
  if (player.dimension.id !== "minecraft:overworld") return false;
  const t = world.getTimeOfDay();
  if (t > 12500 && t < 23500) return false;
  try {
    return player.dimension.getSkyLightLevel(player.getHeadLocation()) >= 13;
  } catch {
    return false;
  }
}
