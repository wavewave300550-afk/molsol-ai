import { Player } from "@minecraft/server";
import { GrimoireDef, SPELL_META } from "./registry";
import { cooldownLeft } from "./state";

const pad2 = (n: number) => (n < 10 ? `0${n}` : `${n}`);

function fmt(sec: number): string {
  const s = Math.ceil(sec);
  return s >= 60 ? `${Math.floor(s / 60)}:${pad2(s % 60)}` : `${s}s`;
}

/**
 * Compact two-line action bar:
 *   Divine Word | 03 Ophanim | READY
 *   1 2 [3] 4 5 6     (green = ready, red = cooling down)
 */
export function drawHud(p: Player, g: GrimoireDef, index: number, note?: string): void {
  const spells = SPELL_META.filter((m) => m.grimoire === g.id);
  const cur = spells[index];
  const left = cooldownLeft(p, cur.id);
  const status = note ?? (left > 0 ? `§c${fmt(left)}` : "§aREADY");
  const tierMark = cur.tier === "imperial" ? "§6*" : cur.tier === "extra" ? "§d**" : "";
  let pips = "";
  for (const s of spells) {
    const c = cooldownLeft(p, s.id) > 0 ? "§c" : "§a";
    pips += s.index === index ? `§f[${c}${s.index + 1}§f] ` : `${c}${s.index + 1} `;
  }
  try {
    p.onScreenDisplay.setActionBar(`${g.color}${g.short} §8| §f${pad2(index + 1)} §e${cur.short}${tierMark} §8| ${status}\n${pips.trimEnd()}`);
  } catch { /* player not ready */ }
}
