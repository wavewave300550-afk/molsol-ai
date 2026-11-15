/**
 * Per-player language for in-fight guidance (HUD, titles, chat briefings).
 * Bedrock does not load a Thai .lang file from packs, so the few lines that
 * guide players during a fight carry their Thai text here. Players switch in
 * the Anatomical Atlas.
 */
import { Player } from "@minecraft/server";

const KEY = "anatomy:lang";
export type Lang = "en" | "th";

export function langOf(p: Player): Lang {
  try {
    return p.getDynamicProperty(KEY) === "th" ? "th" : "en";
  } catch {
    return "en";
  }
}

export function setLang(p: Player, l: Lang): void {
  try {
    p.setDynamicProperty(KEY, l);
  } catch {
    /* ignore */
  }
}

/** Pick the player's language. */
export function tr(p: Player, en: string, th: string): string {
  return langOf(p) === "th" ? th : en;
}
