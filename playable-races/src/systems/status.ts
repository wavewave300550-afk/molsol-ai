/**
 * Timed statuses the Expansion 02 races place on other creatures (v1.4.0):
 *   misclassified (007 Dinosauroid) - the creature misreads the Dinosauroid's body,
 *   sunmarked     (008 Bathyas)     - lit by the impaled sun,
 *   observed      (009 Octamyces)   - its path is being recorded by the Undecimal Eye,
 *   parallax      (009 Octamyces)   - its perception of position is displaced.
 * They last seconds, so they live in memory only; each remembers who placed it, draws a
 * marker particle while it lasts, and is removed when it expires, when the creature is gone,
 * or when the player who placed it leaves or changes lineage.
 */
import { Entity, system } from "@minecraft/server";
import { particle } from "../core/fx.js";
import { v3 } from "../core/util.js";

export type StatusKey = "misclassified" | "sunmarked" | "observed" | "parallax";

interface Status {
  until: number;
  by: string;
}

const table = new Map<string, Map<StatusKey, Status>>();
const handles = new Map<string, Entity>();

const MARKER: Record<StatusKey, { id: string; every: number; dy: number }> = {
  misclassified: { id: "plrace:misclass_mark", every: 16, dy: 0.55 },
  sunmarked: { id: "plrace:sun_mark", every: 14, dy: 0.6 },
  observed: { id: "plrace:observed_mark", every: 12, dy: 0.75 },
  parallax: { id: "plrace:parallax_mark", every: 10, dy: 0.3 },
};

const idOf = (e: Entity | string) => (typeof e === "string" ? e : e.id);

export function setStatus(e: Entity, key: StatusKey, ticks: number, by: string): void {
  if (!e.isValid) return;
  let m = table.get(e.id);
  if (!m) table.set(e.id, (m = new Map()));
  const now = system.currentTick;
  const cur = m.get(key);
  m.set(key, { until: Math.max(cur && cur.by === by ? cur.until : 0, now + ticks), by });
  handles.set(e.id, e);
}

export function hasStatus(e: Entity | string, key: StatusKey, by?: string): boolean {
  const st = table.get(idOf(e))?.get(key);
  return !!st && st.until > system.currentTick && (by === undefined || st.by === by);
}

export function statusBy(e: Entity | string, key: StatusKey): string | undefined {
  const st = table.get(idOf(e))?.get(key);
  return st && st.until > system.currentTick ? st.by : undefined;
}

export function clearStatus(e: Entity | string, key: StatusKey): void {
  table.get(idOf(e))?.delete(key);
}

/** Every creature carrying `key` placed by `by` (still loaded). */
export function withStatus(key: StatusKey, by: string): Entity[] {
  const out: Entity[] = [];
  for (const [id, m] of table) {
    const st = m.get(key);
    const e = handles.get(id);
    if (st && st.by === by && st.until > system.currentTick && e?.isValid) out.push(e);
  }
  return out;
}

/** Every creature carrying `key`, whoever placed it (still loaded). */
export function allWithStatus(key: StatusKey): Entity[] {
  const out: Entity[] = [];
  for (const [id, m] of table) {
    const st = m.get(key);
    const e = handles.get(id);
    if (st && st.until > system.currentTick && e?.isValid) out.push(e);
  }
  return out;
}

export function clearStatusesBy(playerId: string): void {
  for (const m of table.values()) for (const [k, st] of m) if (st.by === playerId) m.delete(k);
}

/** Every 4 ticks: markers on their cadence, expired statuses and vanished creatures removed. */
export function tickStatuses(): void {
  const now = system.currentTick;
  for (const [id, m] of table) {
    const e = handles.get(id);
    if (!e || !e.isValid) {
      table.delete(id);
      handles.delete(id);
      continue;
    }
    for (const [k, st] of m) {
      if (st.until <= now) {
        m.delete(k);
        continue;
      }
      const mk = MARKER[k];
      if (Math.floor(now / 4) % Math.max(1, Math.round(mk.every / 4)) === 0) {
        try {
          const h = e.getHeadLocation();
          particle(e.dimension, mk.id, v3(h.x, h.y + mk.dy, h.z));
        } catch {
          /* unloaded this tick */
        }
      }
    }
    if (!m.size) {
      table.delete(id);
      handles.delete(id);
    }
  }
}
