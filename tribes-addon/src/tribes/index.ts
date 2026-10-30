import { Race } from "../core/state.js";
import { anunnaki } from "./anunnaki.js";
import { dinosauroid } from "./dinosauroid.js";
import { pastafarian } from "./pastafarian.js";
import { spacer } from "./spacer.js";
import { Tribe } from "./types.js";

export const TRIBES: Tribe[] = [dinosauroid, anunnaki, pastafarian, spacer];

export function tribeOf(race: Race): Tribe | undefined {
  return TRIBES.find((t) => t.race === race);
}

export function tribeByRelic(itemId: string): Tribe | undefined {
  return TRIBES.find((t) => t.relic === itemId);
}

export function tribeByKey(key: string): Tribe | undefined {
  return TRIBES.find((t) => t.key === key);
}

export const CODEX_ITEM = "tribes:tribal_codex";

/** Every effect type used as a permanent passive by any tribe. */
export const ALL_PASSIVE_EFFECTS = [...new Set(TRIBES.flatMap((t) => t.passiveEffects.map((p) => p.effect)))];
