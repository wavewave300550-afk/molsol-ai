import { world } from "@minecraft/server";

/**
 * Explicit, world-configurable rules. Stored in world dynamic properties so that
 * operators can change them in-game with `/grimoire:config <rule> <value>`
 * (or `/scriptevent grimoire:config <rule> <value>`).
 */
export interface Rules {
  /** Spells may damage other players (and other players' summons). Default off. */
  pvp: boolean;
  /** When PvP is on, players sharing a `grimoire_team:<name>` tag are still allies unless this is on. */
  friendlyFire: boolean;
  /** Area spells also hit passive animals (cows, sheep...). Default off: spells hit enemies, not farms. */
  harmPassiveMobs: boolean;
  /** Labyrinth / citadel walls may place temporary barrier blocks (only into air, always removed). */
  temporaryBlocks: boolean;
  /** Multiplier for all spell damage against mobs. */
  damagePvE: number;
  /** Multiplier for all spell damage against players (only when pvp is on). */
  damagePvP: number;
  /** Camera shake / fade feedback for nearby players. */
  cameraEffects: boolean;
}

export const DEFAULT_RULES: Rules = {
  pvp: false,
  friendlyFire: false,
  harmPassiveMobs: false,
  temporaryBlocks: true,
  damagePvE: 1,
  damagePvP: 0.5,
  cameraEffects: true,
};

let cached: Rules | undefined;

export function rules(): Rules {
  if (cached) return cached;
  const r: Rules = { ...DEFAULT_RULES };
  try {
    const raw = world.getDynamicProperty("grimoire:rules");
    if (typeof raw === "string") Object.assign(r, JSON.parse(raw));
  } catch {
    /* corrupted value: fall back to defaults */
  }
  cached = r;
  return r;
}

export function setRule(key: string, value: string): string {
  const r = { ...rules() } as unknown as Record<string, unknown>;
  if (!(key in DEFAULT_RULES)) return `Unknown rule '${key}'. Rules: ${Object.keys(DEFAULT_RULES).join(", ")}`;
  const def = (DEFAULT_RULES as unknown as Record<string, unknown>)[key];
  if (typeof def === "boolean") {
    const v = value.toLowerCase();
    r[key] = v === "true" || v === "on" || v === "1" || v === "yes";
  } else {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || n > 10) return `Rule '${key}' needs a number between 0 and 10`;
    r[key] = n;
  }
  world.setDynamicProperty("grimoire:rules", JSON.stringify(r));
  cached = r as unknown as Rules;
  return `Rule ${key} = ${String(r[key])}`;
}

export const TICKS_PER_SECOND = 20;
