/**
 * PersistenceManager - the small amount of state that must survive a reload.
 *
 * The boss entity itself is the save file: one JSON dynamic property holds the
 * arena centre, phase, health scale and boss-specific extras (armour states).
 * In-flight attacks are deliberately NOT persisted; after a reload the boss
 * resumes from an idle stance in the correct phase with no hazards pending.
 * World-level settings live in one world dynamic property.
 */
import { Entity, world } from "@minecraft/server";
import { BossKey, PersistedSettings, applySettings, exportSettings } from "../config";
import { report } from "./trace";

const REC_PROP = "abm:rec";
const SETTINGS_PROP = "abm:settings";
export const REMNANT_TAG = "abm_remnant";

export interface BossRecord {
  v: 1;
  boss: BossKey;
  cx: number;
  cy: number;
  cz: number;
  phase: 1 | 2;
  /** Health scale (multiplayer + difficulty) fixed for this fight. */
  scale: number;
  seed: number;
  /** True once the intro has finished (a reload mid-intro restarts it). */
  engaged: boolean;
  extra: Record<string, number>;
}

export function saveRecord(boss: Entity, rec: BossRecord): void {
  try {
    boss.setDynamicProperty(REC_PROP, JSON.stringify(rec));
  } catch (e) {
    report("saveRecord", e);
  }
}

export function loadRecord(boss: Entity): BossRecord | undefined {
  try {
    const raw = boss.getDynamicProperty(REC_PROP);
    if (typeof raw !== "string") return undefined;
    const rec = JSON.parse(raw) as BossRecord;
    if (rec && rec.v === 1 && typeof rec.cx === "number") return rec;
  } catch {
    /* corrupt record: treat as a fresh spawn */
  }
  return undefined;
}

export function loadSettings(): void {
  try {
    const raw = world.getDynamicProperty(SETTINGS_PROP);
    if (typeof raw === "string") applySettings(JSON.parse(raw) as Partial<PersistedSettings>);
  } catch (e) {
    report("loadSettings", e);
  }
}

export function saveSettings(): void {
  try {
    world.setDynamicProperty(SETTINGS_PROP, JSON.stringify(exportSettings()));
  } catch (e) {
    report("saveSettings", e);
  }
}
