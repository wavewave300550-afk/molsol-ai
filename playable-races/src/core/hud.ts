/** Action-bar HUD: ability wheel with cooldowns + the race's resource line. */
import { Player, system } from "@minecraft/server";
import { RaceDef } from "../races/types.js";
import { charges, maxCharges, raceOf, remaining } from "./abilities.js";
import { holdingFocus } from "./forms.js";
import { Session } from "./session.js";
import { settings } from "./settings.js";
import { secs } from "./util.js";

export function abilityLine(p: Player, s: Session, race: RaceDef): string {
  const parts: string[] = [];
  race.abilities.forEach((a, i) => {
    const sel = i === ((s.data.sel % race.abilities.length) + race.abilities.length) % race.abilities.length;
    const r = remaining(p, s, race, a);
    const max = maxCharges(p, s, race, a);
    const ch = max > 1 ? ` x${charges(p, s, race, a)}` : "";
    const active = s.channel?.ability === a.id;
    let label: string;
    if (active) label = `§d${a.short}`;
    else if (r > 0) label = `§8${a.short} §c${secs(r)}`;
    else label = `§a${a.short}${ch}`;
    parts.push(sel ? `§f[${label}§f]` : label);
  });
  return parts.join(" §8| ");
}

export function updateHud(p: Player, s: Session): void {
  const race = raceOf(s);
  if (!race) return;
  const now = system.currentTick;
  const holding = holdingFocus(p, race);
  if (!holding && s.hudUntil < now && !settings().hudAlways) return;
  const lines: string[] = [];
  if (s.hudMsg && s.hudMsg.until > now) lines.push(s.hudMsg.text);
  else lines.push(abilityLine(p, s, race));
  lines.push(race.hud(p, s));
  try {
    p.onScreenDisplay.setActionBar(lines.join("\n"));
  } catch {
    /* player leaving */
  }
}
