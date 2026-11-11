import { Player, system } from "@minecraft/server";
import type { School } from "../spells/types";
import { log } from "./log";

/**
 * Per-player state. Cooldowns are keyed by player id + spell id, never by item stack, so
 * switching items, dropping the book or obtaining another copy of it cannot reset them.
 * Selected spells and remaining cooldowns persist across relogs in a player dynamic property.
 */
export interface Preparation {
  school: School;
  spellIndex: number;
  spellId: string;
  slot: number;
  itemType: string;
  dimensionId: string;
  startTick: number;
  /** Set when the spell becomes ready to release (min charge reached). */
  readyAnnounced: boolean;
  /** Formation constructs spawned while charging, adopted or dissolved on release. */
  cleanup?: () => void;
  adoptable?: unknown;
}

export interface PlayerState {
  id: string;
  name: string;
  selected: Record<School, number>;
  readyAt: Map<string, number>;
  /** Spells whose cooldown waits for their own end (Wings of the Winter Seraph). */
  activeUntilEnd: Set<string>;
  prep?: Preparation;
  sneaking: boolean;
  empowered?: { until: number; source: string };
  hudKey: string;
  hudTick: number;
  messageUntil: number;
  message: string;
  dirty: boolean;
}

const PROP = "grimoire:state";
const states = new Map<string, PlayerState>();

interface Saved {
  s?: Partial<Record<School, number>>;
  c?: Record<string, number>;
}

export function stateOf(p: Player): PlayerState {
  let st = states.get(p.id);
  if (st) return st;
  st = {
    id: p.id,
    name: p.name,
    selected: { pressure: 0, ice: 0, blood: 0 },
    readyAt: new Map(),
    activeUntilEnd: new Set(),
    sneaking: p.isSneaking,
    hudKey: "",
    hudTick: 0,
    messageUntil: 0,
    message: "",
    dirty: false,
  };
  try {
    const raw = p.getDynamicProperty(PROP);
    if (typeof raw === "string") {
      const saved = JSON.parse(raw) as Saved;
      for (const k of ["pressure", "ice", "blood"] as School[]) {
        const v = saved.s?.[k];
        if (typeof v === "number" && v >= 0 && v < 15) st.selected[k] = Math.floor(v);
      }
      const now = system.currentTick;
      for (const [id, remaining] of Object.entries(saved.c ?? {})) {
        if (typeof remaining === "number" && remaining > 0) st.readyAt.set(id, now + Math.min(remaining, 20 * 600));
      }
    }
  } catch (e) {
    log.warn("could not read saved grimoire state", e);
  }
  states.set(p.id, st);
  return st;
}

export function save(p: Player, st: PlayerState): void {
  const now = system.currentTick;
  const c: Record<string, number> = {};
  for (const [id, t] of st.readyAt) if (t > now) c[id] = t - now;
  const data: Saved = { s: st.selected, c };
  try {
    p.setDynamicProperty(PROP, JSON.stringify(data));
    st.dirty = false;
  } catch (e) {
    log.warn("could not save grimoire state", e);
  }
}

export function forget(playerId: string): void {
  states.delete(playerId);
}

export function allStates(): IterableIterator<PlayerState> {
  return states.values();
}

export function remainingTicks(st: PlayerState, spellId: string): number {
  if (st.activeUntilEnd.has(spellId)) return Number.POSITIVE_INFINITY;
  const t = st.readyAt.get(spellId);
  return t === undefined ? 0 : Math.max(0, t - system.currentTick);
}

export function startCooldown(st: PlayerState, spellId: string, seconds: number): void {
  st.activeUntilEnd.delete(spellId);
  st.readyAt.set(spellId, system.currentTick + Math.round(seconds * 20));
  st.dirty = true;
}

export function clearCooldowns(st: PlayerState): void {
  st.readyAt.clear();
  st.activeUntilEnd.clear();
  st.dirty = true;
}

export function flash(st: PlayerState, msg: string, ticks = 30): void {
  st.message = msg;
  st.messageUntil = system.currentTick + ticks;
  st.hudKey = "";
}
