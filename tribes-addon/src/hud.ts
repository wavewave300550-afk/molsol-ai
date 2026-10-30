import { Player } from "@minecraft/server";
import { getRace, now, state } from "./core/state.js";
import { tribeOf } from "./tribes/index.js";
import { Ability, Tribe } from "./tribes/types.js";

const BAR = 20;

function bar(tribe: Tribe, energy: number): string {
  const filled = Math.round((energy / 100) * BAR);
  return `§8[${tribe.color}${"|".repeat(filled)}§8${"|".repeat(BAR - filled)}§8]`;
}

function abilityLabel(tribe: Tribe, a: Ability, selected: boolean, energy: number, tick: number, readyAt: number): string {
  const cd = Math.max(0, readyAt - tick);
  let col: string;
  let suffix = "";
  if (cd > 0) {
    col = "§8";
    suffix = ` ${(cd / 20).toFixed(cd < 200 ? 1 : 0)}s`;
  } else if (energy < a.cost) {
    col = "§7";
  } else {
    col = a.ultimate ? "§d" : tribe.color;
  }
  const label = `${col}${a.short}${suffix}`;
  return selected ? `§f>> ${label}§f <<` : label;
}

export function hudText(player: Player): string | undefined {
  const tribe = tribeOf(getRace(player));
  if (!tribe) return undefined;
  const s = state(player);
  const tick = now();
  const line1 = `${tribe.color}§l${tribe.name.toUpperCase()}§r  ${bar(tribe, s.energy)} §f${Math.floor(s.energy)}§7/100 ${tribe.color}${tribe.energyName}`;
  const line2 = tribe.abilities
    .map((a, i) => abilityLabel(tribe, a, i === s.selected, s.energy, tick, s.cooldowns.get(a.id) ?? 0))
    .join("§8 | ");
  return `${line1}\n${line2}`;
}

export function showHud(player: Player): void {
  const text = hudText(player);
  if (text) player.onScreenDisplay.setActionBar(text);
}
