import { Player } from "@minecraft/server";
import { sound } from "./core/fx.js";
import { getRace, now, state } from "./core/state.js";
import { showHud } from "./hud.js";
import { tribeByRelic, tribeOf } from "./tribes/index.js";

const DEBOUNCE_TICKS = 4;

/** Using a relic: Sneak+Use cycles the selected ability, Use casts it. */
export function useRelic(player: Player, itemId: string): void {
  const relicTribe = tribeByRelic(itemId);
  if (!relicTribe) return;
  const s = state(player);
  const tick = now();
  if (tick - s.lastAction < DEBOUNCE_TICKS) return;
  s.lastAction = tick;
  s.hudUntil = tick + 60;

  const tribe = tribeOf(getRace(player));
  if (!tribe || tribe.race !== relicTribe.race) {
    player.onScreenDisplay.setActionBar(`${relicTribe.color}The ${relicTribe.name} relic does not answer you. §7(Open the Tribal Codex)`);
    sound(player.dimension, "note.bass", player.location, 0.6, 0.6);
    return;
  }

  if (player.isSneaking) {
    s.selected = (s.selected + 1) % tribe.abilities.length;
    const a = tribe.abilities[s.selected];
    player.playSound("random.click", { pitch: 1.4, volume: 0.6 });
    player.onScreenDisplay.setTitle(" ", {
      subtitle: `${a.ultimate ? "§d" : tribe.color}${a.name} §7(${a.cost} ${tribe.energyName})`,
      fadeInDuration: 0,
      stayDuration: 25,
      fadeOutDuration: 5,
    });
    showHud(player);
    return;
  }

  const ability = tribe.abilities[s.selected];
  const readyAt = s.cooldowns.get(ability.id) ?? 0;
  if (readyAt > tick) {
    player.onScreenDisplay.setActionBar(`§c${ability.name} recharging: ${((readyAt - tick) / 20).toFixed(1)}s`);
    player.playSound("note.bass", { pitch: 0.5, volume: 0.5 });
    return;
  }
  if (s.energy < ability.cost) {
    player.onScreenDisplay.setActionBar(`§cNot enough ${tribe.energyName}: ${Math.floor(s.energy)}/${ability.cost}`);
    player.playSound("note.bass", { pitch: 0.5, volume: 0.5 });
    return;
  }
  let ok = false;
  try {
    ok = ability.cast({ player, state: s, dim: player.dimension, tick });
  } catch (e) {
    console.warn(`[tribes] ${ability.id} failed: ${e}`);
  }
  if (ok) {
    s.energy -= ability.cost;
    s.cooldowns.set(ability.id, tick + ability.cooldown);
  }
  showHud(player);
}
