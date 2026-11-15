/** World-level settings, editable by operators from the Lineage Codex (persisted). */
import { world } from "@minecraft/server";
import { WORLD_SETTINGS } from "../config.js";
import { safeJson, warn } from "./util.js";

export type ChangePolicy = "free" | "cooldown" | "operators";

export interface Settings {
  pvp: boolean; // abilities may harm other players (also requires the pvp game rule)
  change: ChangePolicy; // how players may change lineage after choosing
  changeDays: number; // in-game days between changes for the "cooldown" policy
  bloodChance: number; // % chance per full moon that a Blood Moon rises
  bloodFog: boolean; // crimson fog during the Blood Moon
  autoOpen: boolean; // open the selection menu automatically for new players
  hudAlways: boolean; // show the ability HUD even when the focus is not held
}

const DEFAULTS: Settings = { pvp: true, change: "cooldown", changeDays: 3, bloodChance: 34, bloodFog: true, autoOpen: true, hudAlways: false };

let cache: Settings | undefined;

export function settings(): Settings {
  if (!cache) {
    let raw: unknown;
    try {
      raw = world.getDynamicProperty(WORLD_SETTINGS);
    } catch {
      raw = undefined;
    }
    cache = { ...DEFAULTS, ...safeJson<Partial<Settings>>(raw, {}) };
  }
  return cache;
}

export function updateSettings(patch: Partial<Settings>): void {
  cache = { ...settings(), ...patch };
  try {
    world.setDynamicProperty(WORLD_SETTINGS, JSON.stringify(cache));
  } catch (e) {
    warn("could not save settings", e);
  }
}

export function pvpAllowed(): boolean {
  let rule = true;
  try {
    rule = world.gameRules.pvp;
  } catch {
    rule = true;
  }
  return rule && settings().pvp;
}
