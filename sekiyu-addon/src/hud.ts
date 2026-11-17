import { Player } from "@minecraft/server";
import { ABILITIES, ABILITY_ORDER, Form, spec } from "./config.js";
import { now, state } from "./state.js";

export function hudText(p: Player): string {
  const s = state(p);
  const t = now();
  const burning = s.burningUntil > t ? " §c§l(ablaze)" : "";
  let line1: string;
  if (s.sealed) line1 = "§b§lSUBMERGED §r§7- petroleum sealed, no Logia defence";
  else if (s.form === Form.Body) line1 = `§8§lPETROLEUM BODY§r${burning} §7- physical hits pass through`;
  else if (s.form === Form.Dissolved) line1 = `§8§lDISSOLVED §f${Math.max(0, (s.dissolvedUntil - t) / 20).toFixed(1)}s§r${burning} §7- seeping`;
  else {
    const flow = t >= s.reflexReadyAt ? "§aREADY" : `§7${((s.reflexReadyAt - t) / 20).toFixed(1)}s`;
    line1 = `§6§lPETROLEUM§r${burning} §8| §7Flow ${flow}`;
  }
  const sel = ABILITY_ORDER[s.selected] ?? "tide";
  let line2 = `§7Selected: §e${ABILITIES[sel].name}`;
  const fu = s.followUp;
  if (s.noticeUntil > t && s.notice) line2 = s.notice;
  else if (fu && fu.until > t && fu.id === sel) line2 += `  §8|  §c§lUSE: ${spec(sel).followUp ?? ""}§r §7${((fu.until - t) / 20).toFixed(1)}s`;
  else if (s.activeSkillUntil > t && s.activeSkill) line2 += `  §8|  §bActive: §f${s.activeSkill}`;
  const cds = ABILITY_ORDER.map((id, i) => {
    const a = ABILITIES[id];
    const left = Math.max(0, (s.cooldowns.get(id) ?? 0) - t);
    const label = left > 0 ? `§7${a.short}§8${Math.ceil(left / 20)}` : `${id === "inferno" ? "§c" : "§a"}${a.short}`;
    return i === s.selected ? `§f[${label}§f]` : label;
  }).join(" ");
  return `${line1}\n${line2}\n${cds}`;
}

export function showHud(p: Player): void {
  try {
    p.onScreenDisplay.setActionBar(hudText(p));
  } catch {
    // left
  }
}
