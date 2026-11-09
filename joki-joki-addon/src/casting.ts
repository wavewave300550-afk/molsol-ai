import { Player } from "@minecraft/server";
import { CASTS } from "./abilities/index.js";
import { ABILITIES, ABILITY_ORDER, AbilityId, HUD, Mode, MODES } from "./config.js";
import { S } from "./core/fx.js";
import { addHeat } from "./heat.js";
import { setMode } from "./modes.js";
import { isOverheated, isOwner, notice, now, setActive, state } from "./state.js";
import { showHud } from "./hud.js";

const DEBOUNCE_TICKS = 4;

function deny(p: Player, text: string): void {
  notice(state(p), `§c${text}`, 40);
  try {
    p.playSound(S.deny, { volume: 0.6, pitch: 1 });
  } catch {
    // cosmetic
  }
  showHud(p);
}

export function cooldownLeft(p: Player, id: AbilityId): number {
  return Math.max(0, (state(p).cooldowns.get(id) ?? 0) - now());
}

/** Try to cast an ability: ownership, overheat lockout and cooldown are enforced here. */
export function tryCast(p: Player, id: AbilityId): boolean {
  if (!isOwner(p)) {
    p.sendMessage("§7The valve is cold. Only someone who ate the §cJōki Jōki no Mi§7 can build steam pressure.");
    return false;
  }
  const s = state(p);
  const t = now();
  const spec = ABILITIES[id];
  s.hudUntil = t + HUD.linger;
  if (isOverheated(s)) {
    deny(p, `OVERHEATED §7- systems locked ${((s.overheatUntil - t) / 20).toFixed(1)}s`);
    return false;
  }
  const left = cooldownLeft(p, id);
  if (left > 0) {
    deny(p, `${spec.name} recharging §f${(left / 20).toFixed(1)}s`);
    return false;
  }
  // Any steam technique from NORMAL fires up the boiler (auto-shift to HEAT).
  if (s.mode === Mode.Normal && id !== "redline") setMode(p, s, Mode.Heat);
  const mode = s.mode;
  // a fresh cast replaces any stale HUD notice (abilities may set their own, e.g. "Fist primed")
  const prevNotice = s.noticeUntil;
  s.noticeUntil = 0;
  let result: true | string;
  try {
    result = CASTS[id]({ p, s, dim: p.dimension, tick: t, mode, power: MODES[mode].power });
  } catch (e) {
    console.warn(`[joki] ${id} failed: ${e}`);
    result = "The valve jammed (script error)";
  }
  if (result !== true) {
    s.noticeUntil = prevNotice;
    deny(p, result);
    return false;
  }
  s.cooldowns.set(id, t + Math.max(1, Math.round(spec.cooldown * MODES[mode].cooldownMult)));
  if (s.activeSkillUntil <= t) setActive(s, spec.name, 30);
  addHeat(p, s, spec.heat);
  showHud(p);
  return true;
}

/** Holding the Steam Valve: Use = fire the selected ability, Sneak + Use = open the Steam Console. */
export function useValve(p: Player, openConsole: (p: Player) => void): void {
  const s = state(p);
  const t = now();
  if (t - s.lastAction < DEBOUNCE_TICKS) return;
  s.lastAction = t;
  if (p.isSneaking || !isOwner(p)) {
    openConsole(p);
    return;
  }
  tryCast(p, ABILITY_ORDER[s.selected] ?? "boost");
}
