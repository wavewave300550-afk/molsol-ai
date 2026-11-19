/**
 * Start-up wiring shared by every build of the add-on.
 */
import { system, world } from "@minecraft/server";
import { registerCommands } from "./commands";
import { BossKey, CONFIG } from "./config";
import type { BossModule } from "./core/boss";
import { manager } from "./core/manager";
import { initItems } from "./items";
import { install, installed, moduleOf } from "./registry";
import { initScriptEvents } from "./scriptevents";
import { setErrorNotifier } from "./core/trace";

export function boot(mods: Partial<Record<BossKey, BossModule | undefined>>): void {
  install(mods);
  // The first occurrence of an internal failure is shown in chat (deferred: it may be raised in a
  // restricted callback, and never before the world has loaded).
  setErrorNotifier((line) => {
    system.run(() => {
      try {
        world.sendMessage(line);
      } catch {
        /* world not ready */
      }
    });
  });
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
