import { Player } from "@minecraft/server";
import { GRIMOIRE_ORDER, GrimoireId } from "./registry";

/**
 * Persistent per-player state: selected spell per Grimoire and per-spell cooldowns.
 * Stored on the player as dynamic properties so it survives relogs and world restarts,
 * and is naturally independent for every player (copies of a book share nothing extra).
 */
const SEL = "grim:sel";
const CD = "grim:cd";

interface Cache { sel: number[]; cd: Record<string, number> }
const cache = new Map<string, Cache>();

function load(p: Player): Cache {
  let c = cache.get(p.id);
  if (c) return c;
  c = { sel: [0, 0, 0], cd: {} };
  try {
    const s = p.getDynamicProperty(SEL);
    if (typeof s === "string") {
      const parts = s.split(",").map((x) => Number(x));
      for (let i = 0; i < 3; i++) if (Number.isInteger(parts[i]) && parts[i] >= 0 && parts[i] < 6) c.sel[i] = parts[i];
    }
    const d = p.getDynamicProperty(CD);
    if (typeof d === "string") {
      const obj = JSON.parse(d) as Record<string, number>;
      const now = Date.now();
      for (const [k, v] of Object.entries(obj)) if (typeof v === "number" && v > now) c.cd[k] = v;
    }
  } catch { /* corrupt data: start fresh */ }
  cache.set(p.id, c);
  return c;
}

function saveCd(p: Player, c: Cache): void {
  const now = Date.now();
  for (const k of Object.keys(c.cd)) if (c.cd[k] <= now) delete c.cd[k];
  try { p.setDynamicProperty(CD, JSON.stringify(c.cd)); } catch { /* ignore */ }
}

export function getSelection(p: Player, g: GrimoireId): number {
  return load(p).sel[GRIMOIRE_ORDER.indexOf(g)];
}

export function setSelection(p: Player, g: GrimoireId, index: number): void {
  const c = load(p);
  c.sel[GRIMOIRE_ORDER.indexOf(g)] = ((index % 6) + 6) % 6;
  try { p.setDynamicProperty(SEL, c.sel.join(",")); } catch { /* ignore */ }
}

/** Seconds until the spell is ready again (0 when ready). */
export function cooldownLeft(p: Player, spellId: string): number {
  const until = load(p).cd[spellId];
  if (!until) return 0;
  return Math.max(0, (until - Date.now()) / 1000);
}

export function startCooldown(p: Player, spellId: string, seconds: number): void {
  const c = load(p);
  c.cd[spellId] = Date.now() + seconds * 1000;
  saveCd(p, c);
}

export function clearCooldowns(p: Player): void {
  const c = load(p);
  c.cd = {};
  saveCd(p, c);
}

export function forget(playerId: string): void {
  cache.delete(playerId);
}
