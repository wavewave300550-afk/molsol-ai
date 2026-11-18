/**
 * RewardManager - what a defeated Miracle leaves behind.
 * One trophy per contributing player (up to four), bonus loot from the boss's
 * loot table, and experience granted directly to the players who fought.
 */
import { ItemStack, world } from "@minecraft/server";
import type { Encounter } from "./encounter";
import { report, trace } from "./trace";

export function grantRewards(enc: Encounter): void {
  const c = enc.controller;
  const centre = enc.arena.at({ x: enc.arena.cx, z: enc.arena.cz }, 1.2);
  const fighters = world.getAllPlayers().filter((p) => enc.targeting.contributors.has(p.id) || enc.targeting.everSeen.has(p.id));
  const trophies = Math.max(1, Math.min(4, enc.targeting.contributors.size || 1));
  try {
    for (let i = 0; i < trophies; i++) {
      enc.dim.spawnItem(new ItemStack(c.trophyItem, 1), { x: centre.x + (i - (trophies - 1) / 2) * 0.6, y: centre.y, z: centre.z });
    }
  } catch (e) {
    report("rewards.trophy", e);
  }
  try {
    enc.dim.runCommand(`loot spawn ${centre.x.toFixed(1)} ${centre.y.toFixed(1)} ${centre.z.toFixed(1)} loot "abm/${enc.key}"`);
  } catch (e) {
    report("rewards.loot", e);
  }
  for (const p of fighters) {
    try {
      p.addExperience(c.experience);
      p.sendMessage({ rawtext: [{ translate: `abm.defeat.${enc.key}` }] });
    } catch {
      /* player left */
    }
  }
  trace("rewards", { boss: enc.key, trophies, fighters: fighters.length });
}
