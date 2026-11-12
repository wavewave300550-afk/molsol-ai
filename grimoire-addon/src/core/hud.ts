import { Player, system } from "@minecraft/server";
import { spellAt, spellById } from "../spells/registry";
import { SCHOOL_COLOR, SCHOOL_NAMES, School } from "../spells/types";
import { PlayerState, remainingTicks } from "./state";

/**
 * Mobile-friendly HUD on the action bar (two short lines above the hotbar):
 *   line 1: school glyph · selected number/15 · spell name
 *   line 2: READY / cooldown seconds / preparation bar / release prompt (+ empowerment)
 * Custom glyphs come from textures/font/glyph_E5.png (fall back to plain text if missing).
 */
export const GLYPH = {
  pressure: "",
  ice: "",
  blood: "",
  plasma: "\uE509",
  darkness: "\uE50A",
  prism_light: "\uE50B",
  barFull: "",
  barEmpty: "",
  ready: "",
  lock: "",
  star: "",
  hourglass: "",
};

export function schoolColor(s: School): string {
  return SCHOOL_COLOR[s];
}

function bar(k: number, n = 10): string {
  const full = Math.round(Math.max(0, Math.min(1, k)) * n);
  return GLYPH.barFull.repeat(full) + GLYPH.barEmpty.repeat(n - full);
}

export function renderHud(p: Player, st: PlayerState, school: School): void {
  const now = system.currentTick;
  const idx = st.selected[school];
  const spell = spellAt(school, idx);
  const col = schoolColor(school);
  const num = String(idx + 1).padStart(2, "0");
  const line1 = `${GLYPH[school]} ${col}${SCHOOL_NAMES[school]} §8| §f${num}§7/15 ${col}§l${spell.name}§r`;
  let line2: string;
  const prep = st.prep;
  if (prep && prep.school === school) {
    const sp = spellById(prep.spellId) ?? spell;
    const t = now - prep.startTick;
    const k = t / Math.max(1, sp.charge);
    line2 = k >= 1 ? `${GLYPH.ready} §a§lRelease to cast§r §7(hold is safe)` : `§7Preparing ${col}${bar(k)}`;
  } else {
    const rem = remainingTicks(st, spell.id);
    if (rem === Number.POSITIVE_INFINITY) line2 = `${GLYPH.hourglass} §bActive §7(cooldown starts when it ends)`;
    else if (rem > 0) line2 = `${GLYPH.lock} §cCooldown §f${(rem / 20).toFixed(1)}s §7/ ${spell.cooldown}s`;
    else line2 = `${GLYPH.ready} §aREADY §7· hold §fUse§7 to prepare, release to cast`;
  }
  if (st.empowered && st.empowered.until > now) line2 += ` §6${GLYPH.star}Empowered`;
  if (st.messageUntil > now) line2 = st.message;
  const text = `${line1}\n${line2}`;
  // refresh when content changes, otherwise every 30 ticks to keep it on screen
  if (text === st.hudKey && now - st.hudTick < 30) return;
  st.hudKey = text;
  st.hudTick = now;
  try {
    p.onScreenDisplay.setActionBar(text);
  } catch {
    /* player not ready */
  }
}
