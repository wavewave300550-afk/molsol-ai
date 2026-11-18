/**
 * Encounter HUD.
 *
 * Health is shown twice on purpose:
 *   - natively, by the engine's boss bar (the `minecraft:boss` component on the entity);
 *   - on the action bar, which also carries what the native bar cannot: the phase
 *     and the name of the attack being telegraphed (a text cue that works with
 *     sound off and for colour-blind players).
 * The action bar line is a scripted indicator, not a native boss bar.
 */
import { CONFIG } from "../config";
import type { Encounter } from "./encounter";
import { Top } from "./stateMachine";

export function renderHud(enc: Encounter): void {
  if (!CONFIG.hud.actionBar) return;
  const hp = Math.max(0, Math.ceil(enc.effectiveHealth()));
  const max = Math.ceil(enc.effectiveMaxHealth());
  let phase: string;
  switch (enc.sm.top) {
    case Top.Intro:
      phase = "§7Awakening";
      break;
    case Top.Phase1:
      phase = "§fPhase I";
      break;
    case Top.Transition:
      phase = "§6" + enc.controller.phase2Name;
      break;
    case Top.Phase2:
      phase = "§cPhase II";
      break;
    default:
      phase = "§8Fallen";
  }
  const act = enc.currentAttackName ? ` §7| §e${enc.currentAttackName}` : "";
  const text = `§l${enc.controller.displayName}§r §7| ${phase} §7| §c${hp}§7/${max}${act}`;
  for (const p of enc.targeting.participants()) {
    try {
      p.onScreenDisplay.setActionBar(text);
    } catch {
      /* player left this tick */
    }
  }
}

export function clearHud(enc: Encounter): void {
  if (!CONFIG.hud.actionBar) return;
  for (const p of enc.targeting.participants()) {
    try {
      p.onScreenDisplay.setActionBar("");
    } catch {
      /* ignore */
    }
  }
}
