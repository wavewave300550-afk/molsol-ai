import { Player } from "@minecraft/server";
import { ABILITIES, ABILITY_ORDER, HEAT, Mode, MODES } from "./config.js";
import { isOverheated, now, state } from "./state.js";

const BAR = 20;

export function heatBar(heat: number, over: boolean, tick: number): string {
  const filled = Math.round((Math.max(0, Math.min(100, heat)) / 100) * BAR);
  let out = "§8[";
  for (let i = 0; i < BAR; i++) {
    if (i >= filled) {
      out += "§8|";
      continue;
    }
    const frac = i / BAR;
    const col = over ? (tick % 8 < 4 ? "§4" : "§c") : frac < 0.4 ? "§e" : frac < 0.7 ? "§6" : frac < 0.85 ? "§c" : "§4";
    out += col + "|";
  }
  return out + "§8]";
}

export function hudText(p: Player): string {
  const s = state(p);
  const t = now();
  const over = isOverheated(s);
  const spec = MODES[s.mode];
  const pct = Math.floor(s.heat);
  let line1: string;
  if (over) {
    const flash = t % 10 < 5 ? "§4" : "§c";
    line1 = `${flash}§l!! OVERHEAT !!§r ${heatBar(s.heat, true, t)} §f${pct}% §7locked §f${((s.overheatUntil - t) / 20).toFixed(1)}s`;
  } else {
    const warn = s.heat >= HEAT.warnAt ? (t % 10 < 5 ? "§c§lCRITICAL" : "§4§lCRITICAL") : "";
    const timer = s.mode === Mode.Redline ? ` §4${Math.max(0, (s.redlineUntil - t) / 20).toFixed(1)}s` : "";
    line1 = `${spec.color}§l${spec.name}§r${timer} ${heatBar(s.heat, false, t)} §f${pct}% ${warn}`;
  }
  const sel = ABILITY_ORDER[s.selected] ?? "boost";
  let line2 = `§7Selected: §e${ABILITIES[sel].name}`;
  if (s.noticeUntil > t && s.notice) line2 = s.notice;
  else if (s.activeSkillUntil > t && s.activeSkill) {
    const left = (s.activeSkillUntil - t) / 20;
    line2 += `  §8|  §bActive: §f${s.activeSkill}${left > 1 ? ` §7${left.toFixed(0)}s` : ""}`;
  }
  const cds = ABILITY_ORDER.map((id, i) => {
    const a = ABILITIES[id];
    const left = Math.max(0, (s.cooldowns.get(id) ?? 0) - t);
    let label: string;
    if (over) label = `§8${a.short}`;
    else if (left > 0) label = `§7${a.short}§8${Math.ceil(left / 20)}`;
    else label = `${id === "redline" ? "§c" : "§a"}${a.short}`;
    return i === s.selected ? `§f[${label}§f]` : label;
  }).join(" ");
  // A "%" is always followed by a space so no client formatter can read it as a "%s"-style token.
  return `${line1}\n${line2}\n${cds}`;
}

export function showHud(p: Player): void {
  try {
    p.onScreenDisplay.setActionBar(hudText(p));
  } catch {
    // player left
  }
}
