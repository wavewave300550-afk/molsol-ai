/**
 * Central tuning file for The Abandoned Miracles.
 *
 * Everything a designer is likely to rebalance lives here: boss health and
 * phase thresholds, global damage/health multipliers, multiplayer scaling,
 * the player-damage model, encounter rules, HUD and VFX density.
 * Per-attack numbers (damage, cooldown, weights) live next to each boss in
 * `src/bosses/<boss>/tuning.ts`; beat timings shared with the animations live
 * in `shared/<boss>.timings.json`.
 *
 * Units: time in game ticks (20 per second nominal), distance in blocks,
 * damage in health points (2 = one heart).
 */

export type BossKey = "vesperra" | "cantor" | "nomos" | "orison";
export const BOSS_KEYS: readonly BossKey[] = ["vesperra", "cantor", "nomos", "orison"];

export interface BossBaseStats {
  /** Health for a single player. Must equal the entity's minecraft:health max. */
  health: number;
  /** Phase II begins at this fraction of maximum health. */
  phase2At: number;
  /** Arena radius (circular arenas) or half-size (square arenas), in blocks. */
  arenaRadius: number;
  arenaShape: "circle" | "square";
  /** Free height the boss needs above the floor. */
  clearance: number;
  /** How far inside the arena edge the boss itself stays. */
  leashInset: number;
  /**
   * Share of incoming weapon damage that actually reaches the boss. An enchanted
   * diamond sword removes ~25 health per second from an undefended target, which
   * would end a 480-health fight in twenty seconds; this is what stretches the
   * brief's base health to its 4-7 minute target. Tuned with the simulation.
   */
  damageTaken: number;
}

export interface DifficultyPreset {
  /** Multiplies every hazard's design damage. */
  damage: number;
  /** Multiplies effective boss health. */
  health: number;
  /** Multiplies the idle gap between attacks. */
  attackGap: number;
}

export const CONFIG = {
  /** Extra console output and on-screen state. Toggle in game with /abm:debug. */
  debug: false,

  difficulty: "normal" as "story" | "normal" | "hard",
  difficulties: {
    story: { damage: 0.6, health: 0.75, attackGap: 1.35 },
    normal: { damage: 1.0, health: 1.0, attackGap: 1.0 },
    hard: { damage: 1.3, health: 1.25, attackGap: 0.8 },
  } as Record<string, DifficultyPreset>,

  bosses: {
    vesperra: { health: 480, phase2At: 0.45, arenaRadius: 17, arenaShape: "circle", clearance: 9, leashInset: 4, damageTaken: 0.1 },
    cantor: { health: 520, phase2At: 0.5, arenaRadius: 19, arenaShape: "circle", clearance: 11, leashInset: 6, damageTaken: 0.125 },
    nomos: { health: 560, phase2At: 0.4, arenaRadius: 20, arenaShape: "square", clearance: 9, leashInset: 4, damageTaken: 0.125 },
    orison: { health: 600, phase2At: 0.35, arenaRadius: 18, arenaShape: "circle", clearance: 10, leashInset: 4, damageTaken: 0.128 },
  } as Record<BossKey, BossBaseStats>,

  encounter: {
    /** Players beyond this count do not add health. */
    maxScaledPlayers: 4,
    /** Effective HP = base * (1 + hpPerExtraPlayer * (players - 1)). */
    hpPerExtraPlayer: 0.45,
    /** Largest share of maximum health one hit may remove (anti one-shot). */
    maxHitFraction: 0.04,
    /** Players further than arena radius + this margin are not participants. */
    arenaMargin: 5,
    /** Vertical band, relative to the arena floor, in which players count as inside. */
    floorBelow: 4,
    floorAbove: 14,
    /** Damage dealt from outside the arena is ignored (stops ranged cheese). */
    blockOutsideDamage: true,
    /** With nobody left in the arena, the encounter resets after this long. */
    resetGraceTicks: 400,
    /** On reset the summoning seal is dropped at the arena centre. */
    refundSealOnReset: true,
    /** Minimum share of sampled floor cells that must be solid + clear to allow a summon. */
    minFloorCoverage: 0.7,
    /** A player cannot be damaged by the same encounter more often than this. */
    playerHitIntervalTicks: 10,
    /** How long the lifeless remnant stays before it crumbles. */
    remnantTicks: 600,
    /** Helpers (minions, bells, anchors, ...) alive at once, per encounter. */
    maxHelpers: 12,
    /** Idle ticks between attacks before difficulty scaling. */
    baseAttackGap: 26,
  },

  /**
   * Player damage model. Hazards deal `design damage * difficulty * (1 - mitigation)`.
   * Vanilla Bedrock armour removes up to ~96% of a hit in enchanted diamond, which would
   * make every telegraphed attack irrelevant, so mitigation is computed here with a
   * gentler, documented curve and applied exactly (see core/damage.ts).
   */
  damage: {
    armorPerPoint: 0.02, // 20 armour points (full diamond) -> 40%
    armorCap: 0.4,
    protectionPerLevel: 0.0125, // 16 levels (4 x Protection IV) -> 20%
    protectionCap: 0.2,
    resistancePerLevel: 0.15,
    resistanceCap: 0.6,
    /** A hit can never be reduced below this share of its design damage. */
    minShare: 0.25,
  },

  movement: {
    /** "impulse": velocity steering (smooth). "teleport": stepwise fallback. */
    mode: "impulse" as "impulse" | "teleport",
  },

  hud: {
    actionBar: true,
    intervalTicks: 10,
  },

  vfx: {
    /** 1 = full decoration. Telegraph outlines are never reduced. */
    density: 1.0,
  },
};

export function difficulty(): DifficultyPreset {
  return CONFIG.difficulties[CONFIG.difficulty] ?? CONFIG.difficulties.normal;
}

/** Settings that can be changed in game and are persisted with the world. */
export interface PersistedSettings {
  difficulty: "story" | "normal" | "hard";
  vfxDensity: number;
  debug: boolean;
  movementMode: "impulse" | "teleport";
  actionBar: boolean;
}

export function exportSettings(): PersistedSettings {
  return {
    difficulty: CONFIG.difficulty,
    vfxDensity: CONFIG.vfx.density,
    debug: CONFIG.debug,
    movementMode: CONFIG.movement.mode,
    actionBar: CONFIG.hud.actionBar,
  };
}

export function applySettings(s: Partial<PersistedSettings>): void {
  if (s.difficulty && s.difficulty in CONFIG.difficulties) CONFIG.difficulty = s.difficulty;
  if (typeof s.vfxDensity === "number") CONFIG.vfx.density = Math.max(0.25, Math.min(1, s.vfxDensity));
  if (typeof s.debug === "boolean") CONFIG.debug = s.debug;
  if (s.movementMode === "impulse" || s.movementMode === "teleport") CONFIG.movement.mode = s.movementMode;
  if (typeof s.actionBar === "boolean") CONFIG.hud.actionBar = s.actionBar;
}
