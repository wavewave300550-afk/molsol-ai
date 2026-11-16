import { Player } from "@minecraft/server";

/** Third-person arm poses (defined in the resource pack, zeroed in first person). One shared
 *  controller slot so a new pose cleanly replaces the previous one. */
export function pose(p: Player, name: string, stopWhenNotUsing = false): void {
  try {
    p.playAnimation(`animation.oddworks.player.${name}`, {
      controller: "oddworks_arm_pose",
      blendOutTime: 0.12,
      stopExpression: stopWhenNotUsing ? "!query.is_using_item" : "query.any_animation_finished",
    });
  } catch {
    /* animation API unavailable for this entity right now */
  }
}

/** Script -> attachable signal: a cooldown category no item uses, read by Molang
 *  query.cooldown_time_remaining in the item's attachable to play draw / sheathe / deflect poses. */
export function signal(p: Player, category: string, ticks: number): void {
  try {
    p.startItemCooldown(category, Math.max(0, Math.min(32767, Math.round(ticks))));
  } catch {
    /* ignore */
  }
}
