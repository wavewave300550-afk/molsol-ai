/**
 * Boss registry: which boss modules are present in this build.
 * Filled once at boot; everything else (UI, commands) reads from here.
 */
import { BOSS_KEYS, BossKey } from "./config";
import type { ArenaInfo, BossModule } from "./core/boss";

const modules: Partial<Record<BossKey, BossModule>> = {};

export function install(mods: Partial<Record<BossKey, BossModule | undefined>>): void {
  for (const k of BOSS_KEYS) {
    const m = mods[k];
    if (m) modules[k] = m;
  }
}

export function installed(): BossKey[] {
  return BOSS_KEYS.filter((k) => modules[k] !== undefined);
}

export function moduleOf(k: BossKey): BossModule | undefined {
  return modules[k];
}

export function arenaOf(k: BossKey): ArenaInfo | undefined {
  return modules[k]?.arena;
}
