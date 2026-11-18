/**
 * Start-up wiring shared by every build of the add-on.
 */
import { system } from "@minecraft/server";
import { registerCommands } from "./commands";
import { BossKey, CONFIG } from "./config";
import type { BossModule } from "./core/boss";
import { manager } from "./core/manager";
import { initItems } from "./items";
import { install, installed, moduleOf } from "./registry";
import { initScriptEvents } from "./scriptevents";

export function boot(mods: Partial<Record<BossKey, BossModule | undefined>>): void {
  install(mods);
  system.beforeEvents.startup.subscribe((ev) => registerCommands(ev));
  const helpers: string[] = [];
  for (const k of installed()) {
    const m = moduleOf(k) as BossModule;
    manager.register(k, m.create);
    helpers.push(...m.helpers);
  }
  manager.init(helpers);
  initItems();
  initScriptEvents();
  // Test harness hook: the headless simulation (tools/sim) reaches the manager through this.
  const g = globalThis as { __abmTrace?: unknown; __abm?: unknown };
  if (g.__abmTrace) g.__abm = { manager, CONFIG };
}
