/**
 * Identifiers and tuning shared by every system. Damage values are for Normal
 * difficulty; see difficultyScale() for Easy / Hard.
 */
import { Difficulty, world } from "@minecraft/server";

export const JOAN = "joan:joan_of_arc";
export const ECHO = "joan:echo";
export const STANDARD = "joan:standard";
export const STAKE = "joan:stake";
export const WAYSTONE = "joan:waystone";
export const SERAPH = "joan:seraph";
export const MINIONS = [ECHO, STANDARD, STAKE, WAYSTONE, SERAPH];

export const ITEM_BANNER = "joan:banner_of_divine_paths";
export const ITEM_HEART = "joan:unburnt_heart";
export const ITEM_STANDARD = "joan:pilgrims_standard";

export const PROP_PHASE = "joan:phase";
export const PROP_ACTION = "joan:action";
export const PROP_SEQ = "joan:seq";

/** Entities our roads redirect as projectiles. */
export const PROJECTILES = new Set<string>([
  "minecraft:arrow",
  "minecraft:thrown_trident",
  "minecraft:snowball",
  "minecraft:egg",
  "minecraft:ender_pearl",
  "minecraft:small_fireball",
  "minecraft:fireball",
  "minecraft:wind_charge_projectile",
  "minecraft:breeze_wind_charge_projectile",
  "minecraft:splash_potion",
  "minecraft:lingering_potion",
  "minecraft:xp_bottle",
  "minecraft:llama_spit",
  "minecraft:shulker_bullet",
  "minecraft:dragon_fireball",
  "minecraft:wither_skull",
  "minecraft:wither_skull_dangerous",
]);

/** Entity types that roads never move and attacks never touch. */
export const UNTOUCHABLE = new Set<string>([
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:armor_stand",
  "minecraft:villager",
  "minecraft:villager_v2",
  "minecraft:wandering_trader",
  "minecraft:npc",
  "minecraft:allay",
  "minecraft:ender_crystal",
  "minecraft:lightning_bolt",
  "minecraft:minecart",
  "minecraft:boat",
  "minecraft:chest_boat",
  "minecraft:ender_dragon",
  "minecraft:wither",
  "minecraft:warden",
  "minecraft:elder_guardian",
  "minecraft:fishing_hook",
]);

export const TUNING = {
  maxHealth: 600,
  arenaRadius: 26,
  leashRadius: 34,
  resetAfterTicks: 20 * 40,
  thinkInterval: 4,
  // telegraph (path forming) durations in ticks
  telegraph: { 1: 18, 2: 12 } as Record<number, number>,
  // minimum ticks between two skills (global cooldown)
  gcd: { 1: 34, 2: 22 } as Record<number, number>,
  phase2At: 0.5,
  ultimateAt: 0.3,
  ultimateRepeat: 20 * 55,
  memorySeconds: 40,
  maxPaths: 14,
};

export interface DifficultyScale {
  damage: number;
  telegraph: number;
  cooldown: number;
}

export function difficultyScale(): DifficultyScale {
  let d: Difficulty = Difficulty.Normal;
  try {
    d = world.getDifficulty();
  } catch {
    // older runtime or unavailable - keep Normal
  }
  switch (d) {
    case Difficulty.Easy:
      return { damage: 0.65, telegraph: 1.3, cooldown: 1.25 };
    case Difficulty.Hard:
      return { damage: 1.25, telegraph: 0.85, cooldown: 0.85 };
    default:
      return { damage: 1.0, telegraph: 1.0, cooldown: 1.0 };
  }
}

/** Road colours (RGBA 0..1). */
export const COLORS = {
  road: { red: 0.72, green: 0.88, blue: 1.0, alpha: 0.95 },
  roadGold: { red: 1.0, green: 0.86, blue: 0.42, alpha: 1.0 },
  trail: { red: 1.0, green: 0.92, blue: 0.66, alpha: 0.9 },
  burning: { red: 1.0, green: 0.52, blue: 0.16, alpha: 1.0 },
  burningGold: { red: 1.0, green: 0.78, blue: 0.3, alpha: 1.0 },
  ink: { red: 1.0, green: 0.9, blue: 0.55, alpha: 1.0 },
  warn: { red: 1.0, green: 0.32, blue: 0.18, alpha: 1.0 },
  false: { red: 1.0, green: 0.74, blue: 0.22, alpha: 1.0 },
  purified: { red: 0.7, green: 0.96, blue: 1.0, alpha: 1.0 },
  player: { red: 0.55, green: 0.78, blue: 1.0, alpha: 0.9 },
  scar: { red: 0.95, green: 0.85, blue: 0.6, alpha: 1.0 },
  white: { red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0 },
  ember: { red: 1.0, green: 0.6, blue: 0.2, alpha: 1.0 },
};
