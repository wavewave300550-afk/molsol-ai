import { Dimension, MolangVariableMap, Vector3 } from "@minecraft/server";

/**
 * Particle and sound helpers.  Every particle the scripts emit goes through `particle()`, which keeps a
 * per-tick budget (phones stay smooth even when several attacks overlap) and counters the smoke test reads.
 */
export const FX_BUDGET_PER_TICK = 14;
export const fxStats = { tick: -1, thisTick: 0, maxPerTick: 0, total: 0, dropped: 0 };

export function fxTick(tick: number): void {
  if (fxStats.tick !== tick) {
    fxStats.tick = tick;
    fxStats.thisTick = 0;
  }
}

export const PFX = {
  spark: "esb:gold_spark",
  steam: "esb:steam_puff",
  pages: "esb:page_burst",
  shockwave: "esb:shockwave",
  dust: "esb:dust_ring",
  sigilEdge: "esb:sigil_edge",
  sigilBurst: "esb:sigil_burst",
  pillar: "esb:summon_pillar",
  voltSpark: "esb:volt_spark",
  zap: "esb:zap",
  glass: "esb:glass_shards",
  telegraph: "esb:telegraph",
  smoke: "esb:blink_smoke",
} as const;

/** radius -> variable.radius (circles); ac -> variable.ac (Edison: 0 = amber DC, 1 = blue AC). */
export function particle(dim: Dimension, id: string, at: Vector3, radius?: number, ac?: number): boolean {
  if (fxStats.thisTick >= FX_BUDGET_PER_TICK) {
    fxStats.dropped++;
    return false;
  }
  try {
    if (radius !== undefined || ac !== undefined) {
      const m = new MolangVariableMap();
      if (radius !== undefined) m.setFloat("variable.radius", radius);
      if (ac !== undefined) m.setFloat("variable.ac", ac);
      dim.spawnParticle(id, at, m);
    } else {
      dim.spawnParticle(id, at);
    }
  } catch {
    return false; // chunk not loaded / outside the world
  }
  fxStats.thisTick++;
  fxStats.total++;
  if (fxStats.thisTick > fxStats.maxPerTick) fxStats.maxPerTick = fxStats.thisTick;
  return true;
}

/** Vanilla sound events only (no custom audio files in the pack). */
export const SND = {
  shot: "mob.blaze.shoot",
  click: "random.click",
  boom: "random.explode",
  anvil: "random.anvil_land",
  anvilBreak: "random.anvil_break",
  charge: "beacon.activate",
  totem: "random.totem",
  flap: "mob.enderdragon.flap",
  bell: "block.bell.hit",
  page: "item.book.page_turn",
  levelup: "random.levelup",
  spell: "mob.evocation_illager.cast_spell",
  summon: "mob.evocation_illager.prepare_summon",
  throw: "random.bow",
  glass: "random.glass",
  portal: "mob.endermen.portal",
  fizz: "random.fizz",
  thunder: "ambient.weather.lightning.impact",
} as const;

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    /* ignore */
  }
}
