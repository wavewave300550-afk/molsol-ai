/**
 * Per-player state.
 *  - PlayerData is persisted (player dynamic property, JSON) and survives relogs/reloads.
 *  - Session is runtime-only (channels, timers, cached flags) and rebuilt on join.
 * Cooldowns are persisted as *remaining* ticks so they behave the same regardless of
 * /time changes or how long the player was offline.
 */
import { Player, system } from "@minecraft/server";
import { PROP_DATA } from "../config.js";
import { safeJson, warn } from "./util.js";

export interface PlayerData {
  v: number;
  race: string; // "" | "001" | "002" | "003" (permanent race codes)
  sel: number; // selected ability index
  cd: Record<string, number>; // ability id -> remaining cooldown ticks (at save time)
  charges: Record<string, number>;
  res: Record<string, number>; // race resources (hydration, stability ...)
  st: Record<string, string>; // race state machine values (bloom/dormant, aligned/disrupted ...)
  veiled: boolean;
  ench: [string, number][]; // crest enchantments, preserved across form swaps / veiling
  joined: boolean; // first-join guide handled
  lastChange: number; // world day of the last lineage change
  locks: number[]; // InputPermissionCategory values we disabled (restored on join)
  stats: Record<string, number>;
  /** Race codes this player wears as the still (unanimated) body - the Display Check fallback. */
  still?: string[];
}

export function defaultData(): PlayerData {
  return { v: 1, race: "", sel: 0, cd: {}, charges: {}, res: {}, st: {}, veiled: false, ench: [], joined: false,
    lastChange: -999, locks: [], stats: {} };
}

export interface Channel {
  ability: string;
  started: number;
  until: number;
  /** keep: other abilities may be cast meanwhile; interrupt: casting another ends it; block: busy */
  mode?: "keep" | "interrupt" | "block";
  /** Using the same ability again ends it early (only after CANCEL_GRACE ticks). */
  cancelable?: boolean;
  tick?: (s: Session, p: Player, t: number) => void;
  end: (s: Session, p: Player, reason: EndReason) => void;
}
export type EndReason = "complete" | "cancel" | "death" | "leave" | "dimension" | "race" | "interrupt";

export interface Session {
  id: string;
  name: string;
  data: PlayerData;
  dirty: boolean;
  readyAt: Map<string, number>; // ability id -> system tick when ready
  chargeAt: Map<string, number>; // ability id -> system tick when next charge returns
  lastCast: number;
  lastInput: number;
  lastRawInput: number; // every use event, including ignored repeats
  hudUntil: number;
  hudMsg?: { text: string; until: number };
  channel?: Channel;
  tempVariant?: { variant: string; until: number }; // short-lived visual configuration
  shownVariant: string;
  flags: Map<string, number>; // named timed flags -> expiry tick
  num: Map<string, number>; // scratch numbers (still ticks, last warnings ...)
  menuOpen: boolean;
  diag?: boolean; // the display check is borrowing the head slot and camera
}

const sessions = new Map<string, Session>();

export function load(p: Player): Session {
  let s = sessions.get(p.id);
  if (s) return s;
  let data = defaultData();
  try {
    data = { ...defaultData(), ...safeJson<Partial<PlayerData>>(p.getDynamicProperty(PROP_DATA), {}) };
  } catch (e) {
    warn("could not read player data", e);
  }
  s = {
    id: p.id, name: p.name, data, dirty: false, readyAt: new Map(), chargeAt: new Map(), lastCast: -999,
    lastInput: -999, lastRawInput: -999, hudUntil: 0, shownVariant: "", flags: new Map(), num: new Map(), menuOpen: false,
  };
  const t = system.currentTick;
  for (const [id, rem] of Object.entries(data.cd)) if (rem > 0) s.readyAt.set(id, t + rem);
  for (const [id, rem] of Object.entries(data.charges)) if (rem > 0) s.chargeAt.set(id, t + rem);
  sessions.set(p.id, s);
  return s;
}

export function get(p: Player): Session {
  return sessions.get(p.id) ?? load(p);
}

export function peek(id: string): Session | undefined {
  return sessions.get(id);
}

export function all(): IterableIterator<Session> {
  return sessions.values();
}

export function drop(id: string): void {
  sessions.delete(id);
}

export function save(p: Player, s: Session, force = false): void {
  if (!s.dirty && !force) return;
  const t = system.currentTick;
  const cd: Record<string, number> = {};
  for (const [id, at] of s.readyAt) if (at > t) cd[id] = at - t;
  const ch: Record<string, number> = {};
  for (const [id, at] of s.chargeAt) if (at > t) ch[id] = at - t;
  s.data.cd = cd;
  s.data.charges = ch;
  try {
    p.setDynamicProperty(PROP_DATA, JSON.stringify(s.data));
    s.dirty = false;
  } catch (e) {
    warn("could not save player data", e);
  }
}

export function flag(s: Session, name: string, ticks: number): void {
  s.flags.set(name, system.currentTick + ticks);
}

export function hasFlag(s: Session, name: string): boolean {
  const at = s.flags.get(name);
  return at !== undefined && at > system.currentTick;
}

export function clearFlag(s: Session, name: string): void {
  s.flags.delete(name);
}
