/**
 * Unique lineages.  A race with rarity "unique" is a signature lineage: more elaborate
 * systems, a fifth (ultimate) ability and - unless operators turn it off - only one
 * holder per world at a time.  The claim is stored with the world; it is released when
 * the holder takes the Rite of Unbecoming, is assigned another lineage, or an operator
 * releases it (/plrace:unique release).
 */
import { Player, world } from "@minecraft/server";
import { WORLD_UNIQUE } from "../config.js";
import { settings } from "../core/settings.js";
import { safeJson, warn } from "../core/util.js";
import { RaceDef } from "../races/types.js";

export interface Holder {
  id: string;
  name: string;
  day: number;
}

let cache: Record<string, Holder> | undefined;

function holders(): Record<string, Holder> {
  if (!cache) {
    let raw: unknown;
    try {
      raw = world.getDynamicProperty(WORLD_UNIQUE);
    } catch {
      raw = undefined;
    }
    cache = safeJson<Record<string, Holder>>(raw, {});
  }
  return cache;
}

function store(): void {
  try {
    world.setDynamicProperty(WORLD_UNIQUE, JSON.stringify(holders()));
  } catch (e) {
    warn("could not save unique holders", e);
  }
}

export const isUnique = (r: RaceDef | undefined): boolean => (r?.rarity ?? "normal") === "unique";

export function holderOf(code: string): Holder | undefined {
  return holders()[code];
}

/** Why `p` may not take `race` right now (undefined = allowed). */
export function uniqueBlocked(p: Player, race: RaceDef): string | undefined {
  if (!isUnique(race) || !settings().uniqueExclusive) return undefined;
  const h = holderOf(race.code);
  if (!h || h.id === p.id) return undefined;
  return `${race.name} is a Unique lineage already held by ${h.name}. Only one may hold it in this world.`;
}

export function claim(p: Player, race: RaceDef, day: number): void {
  if (!isUnique(race)) return;
  const h = holders()[race.code];
  if (h && h.id !== p.id && settings().uniqueExclusive) return;
  holders()[race.code] = { id: p.id, name: p.name, day };
  store();
}

/** The player no longer holds any unique lineage except `keep`. */
export function releasePlayer(id: string, keep?: string): void {
  let changed = false;
  for (const [code, h] of Object.entries(holders())) {
    if (h.id === id && code !== keep) {
      delete holders()[code];
      changed = true;
    }
  }
  if (changed) store();
}

export function releaseCode(code: string): boolean {
  if (!holders()[code]) return false;
  delete holders()[code];
  store();
  return true;
}

export function uniqueStatus(): string {
  const list = Object.entries(holders());
  if (list.length === 0) return "No Unique lineage is held.";
  return list.map(([code, h]) => `${code}: ${h.name}`).join(", ");
}
