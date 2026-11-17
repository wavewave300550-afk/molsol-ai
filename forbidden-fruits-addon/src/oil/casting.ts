import { Player } from "@minecraft/server";
import { CASTS } from "./abilities/index.js";
import { ABILITIES, ABILITY_ORDER, AbilityId, CONTROLS, DP, Form, HUD, spec as specOf } from "./config.js";
import { S } from "./core/fx.js";
import { showHud } from "./hud.js";
import { setForm } from "./logia.js";
import { holdingCore } from "./power.js";
import { clearFollowUp, isOwner, notice, now, setActive, state } from "./state.js";

const DEBOUNCE_TICKS = 4;

function deny(p: Player, text: string): void {
  notice(state(p), `§c${text}`, 40);
  try {
    p.playSound(S.deny, { volume: 0.6 });
  } catch {
    // cosmetic
  }
  showHud(p);
}

export function cooldownLeft(p: Player, id: AbilityId): number {
  return Math.max(0, (state(p).cooldowns.get(id) ?? 0) - now());
}

/**
 * Use the ability `id`. Order of rules:
 *   not an owner / submerged -> refused
 *   the ability's follow-up window is open -> run the follow-up (ignite / reform / afterburn), no cooldown
 *   Petroleum Body already active and Body chosen -> reform
 *   dissolved -> only Infiltration's reform is allowed
 *   cooldown -> refused, else cast
 */
export function tryCast(p: Player, id: AbilityId): boolean {
  if (!isOwner(p)) {
    p.sendMessage("§7The core is inert. Only someone who ate the §6Sekiyu Sekiyu no Mi§7 can command petroleum.");
    return false;
  }
  const s = state(p);
  const t = now();
  const spec = ABILITIES[id];
  s.hudUntil = t + HUD.linger;
  if (s.sealed) {
    deny(p, "Submerged - your powers are sealed");
    return false;
  }
  const fu = s.followUp;
  if (fu && fu.id === id) {
    if (fu.until > t) {
      clearFollowUp(s, id);
      try {
        fu.run();
      } catch (e) {
        console.warn(`[sekiyu] ${id} follow-up failed: ${e}`);
      }
      s.noticeUntil = 0;
      setActive(s, `${spec.name}: ${specOf(id).followUp ?? ""}`, 20);
      showHud(p);
      return true;
    }
    clearFollowUp(s, id);
  }
  if (id === "body" && s.form === Form.Body) {
    setForm(p, s, Form.Human);
    showHud(p);
    return true;
  }
  if (s.form === Form.Dissolved && id !== "seep") {
    deny(p, "Dissolved - reform first (Petroleum Infiltration)");
    return false;
  }
  const left = cooldownLeft(p, id);
  if (left > 0) {
    deny(p, `${spec.name} recharging §f${(left / 20).toFixed(1)}s`);
    return false;
  }
  const prevNotice = s.noticeUntil;
  s.noticeUntil = 0;
  let result: true | string;
  try {
    result = CASTS[id]({ p, s, dim: p.dimension, tick: t });
  } catch (e) {
    console.warn(`[sekiyu] ${id} failed: ${e}`);
    result = "The oil would not answer (script error)";
  }
  if (result !== true) {
    s.noticeUntil = prevNotice;
    deny(p, result);
    return false;
  }
  s.cooldowns.set(id, t + spec.cooldown);
  if (s.activeSkillUntil <= t) setActive(s, spec.name, 30);
  showHud(p);
  return true;
}

/** Select an ability WITHOUT casting it; plain Use is ignored briefly afterwards. */
export function selectAbility(p: Player, index: number): void {
  const s = state(p);
  const n = ABILITY_ORDER.length;
  s.selected = ((Math.round(index) % n) + n) % n;
  p.setDynamicProperty(DP.selected, s.selected);
  s.castGuardUntil = now() + CONTROLS.castGuard;
  const id = ABILITY_ORDER[s.selected];
  const a = ABILITIES[id];
  const left = cooldownLeft(p, id);
  notice(s, `§eSelected: §f${a.name} §8(${s.selected + 1}/${n}) ${left > 0 ? `§7${(left / 20).toFixed(1)}s` : "§aready"}`, 40);
  p.onScreenDisplay.setTitle(" ", { subtitle: `${id === "inferno" ? "§c" : "§6"}> ${a.name} <`, fadeInDuration: 0, stayDuration: 18, fadeOutDuration: 6 });
  try {
    p.playSound(S.click, { volume: 0.5, pitch: 0.9 + s.selected * 0.06 });
  } catch {
    // cosmetic
  }
  showHud(p);
}

/** Every tick: each new Sneak press with the core in hand = next ability (previous while looking up). */
export function tickSkillSwitch(p: Player): void {
  const s = state(p);
  const sneaking = p.isSneaking;
  const pressed = sneaking && !s.wasSneaking;
  s.wasSneaking = sneaking;
  if (!pressed || !holdingCore(p)) return;
  s.stepFrom = s.selected;
  s.lastStep = now();
  selectAbility(p, s.selected + (p.getViewDirection().y >= CONTROLS.lookUp ? -1 : 1));
}

/** Holding the Crude Core: Use = cast / follow-up, Sneak + Use = Oil Console. */
export function useCore(p: Player, openConsole: (p: Player) => void): void {
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
    if (s.lastStep >= 0 && t - s.lastStep < 100) {
      s.selected = s.stepFrom; // the crouch was only for the console: undo its skill step
      p.setDynamicProperty(DP.selected, s.selected);
      s.noticeUntil = 0;
    }
    s.lastStep = -1;
    s.castGuardUntil = t + CONTROLS.castGuard;
    openConsole(p);
    return;
  }
  if (t < s.castGuardUntil) return;
  if (t - s.lastAction < DEBOUNCE_TICKS) return;
  s.lastAction = t;
  tryCast(p, ABILITY_ORDER[s.selected] ?? "tide");
}
