import type { Player, RawMessage, TitleDisplayOptions } from "@minecraft/server";

/**
 * On-screen encounter messages for a group of players (usually
 * EncounterState.participants()). Players who left mid-call are skipped.
 * The boss health bar itself comes from the entity's `minecraft:boss` component.
 */
export function showActionBar(players: readonly Player[], message: string | RawMessage): void {
  for (const player of players) {
    if (player.isValid) player.onScreenDisplay.setActionBar(message);
  }
}

export function showTitle(players: readonly Player[], title: string | RawMessage, options?: TitleDisplayOptions): void {
  for (const player of players) {
    if (player.isValid) player.onScreenDisplay.setTitle(title, options);
  }
}
