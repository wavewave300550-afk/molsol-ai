import { Player } from "@minecraft/server";
import { CASTS } from "./abilities/index.js";
import { ABILITIES, ABILITY_ORDER, AbilityId, CONTROLS, DP, HUD, Mode, MODES } from "./config.js";
import { S } from "./core/fx.js";
import { addHeat } from "./heat.js";
import { setMode } from "./modes.js";
import { isOverheated, isOwner, notice, now, setActive, state } from "./state.js";
import { showHud } from "./hud.js";
import { holdingValve } from "./power.js";

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

/**
 * Make `index` the selected ability WITHOUT casting it. Plain Use is ignored for a short
 * moment afterwards so the tap that switched skills can never fire one.
 */
export function selectAbility(p: Player, index: number): void {
  const s = state(p);
  const n = ABILITY_ORDER.length;
  s.selected = ((Math.round(index) % n) + n) % n;
  p.setDynamicProperty(DP.selected, s.selected);
  const t = now();
  s.castGuardUntil = t + CONTROLS.castGuard;
  const id = ABILITY_ORDER[s.selected];
  const a = ABILITIES[id];
  const left = cooldownLeft(p, id);
  const status = isOverheated(s) ? "§4locked" : left > 0 ? `§7${(left / 20).toFixed(1)}s` : "§aready";
  notice(s, `§eSelected: §f${a.name} §8(${s.selected + 1}/${n}) ${status}`, 40);
  p.onScreenDisplay.setTitle(" ", {
    subtitle: `${id === "redline" ? "§4" : "§6"}> ${a.name} <`,
    fadeInDuration: 0,
    stayDuration: 18,
    fadeOutDuration: 6,
  });
  try {
    p.playSound(S.click, { volume: 0.5, pitch: 1.0 + s.selected * 0.06 });
  } catch {
    // cosmetic
  }
  showHud(p);
}

/**
 * Called every tick for each steam user: every new Sneak press while holding the valve switches to
 * the NEXT skill (the PREVIOUS one while looking up). Nothing has to be held and nothing is cast.
 */
export function tickSkillSwitch(p: Player): void {
  const s = state(p);
  const sneaking = p.isSneaking;
  const pressed = sneaking && !s.wasSneaking;
  s.wasSneaking = sneaking;
  if (!pressed || !holdingValve(p)) return;
  s.stepFrom = s.selected;
  s.lastStep = now();
  selectAbility(p, s.selected + (p.getViewDirection().y >= CONTROLS.lookUp ? -1 : 1));
}

/**
 * Holding the Steam Valve:
 *   Use            = fire the selected ability
 *   Press Sneak    = next skill, looking up = previous (see tickSkillSwitch)
 *   Sneak + Use    = open the Steam Console
 */
export function useValve(p: Player, openConsole: (p: Player) => void): void {
  const s = state(p);
  const t = now();
  if (!isOwner(p)) {
    if (t - s.lastAction < DEBOUNCE_TICKS) return;
    s.lastAction = t;
    openConsole(p);
    return;
  }
  if (p.isSneaking) {
    if (t - s.lastAction < DEBOUNCE_TICKS) return;
    s.lastAction = t;
    // the player crouched only to open the console: undo the skill step that crouch made
    if (s.lastStep >= 0 && p.isSneaking && t - s.lastStep < 100) {
      s.selected = s.stepFrom;
      p.setDynamicProperty(DP.selected, s.selected);
      s.noticeUntil = 0;
    }
    s.lastStep = -1;
    s.castGuardUntil = t + CONTROLS.castGuard;
    openConsole(p);
    return;
  }
  // the tap that just switched skills (or closed the console) must not fire one
  if (t < s.castGuardUntil) return;
  if (t - s.lastAction < DEBOUNCE_TICKS) return;
  s.lastAction = t;
  tryCast(p, ABILITY_ORDER[s.selected] ?? "boost");
}
