import type { Player } from "@minecraft/server";
import type { Scene } from "../lib/scene";
import type { Aim } from "../lib/targeting";

export type GrimoireId = "divine_word" | "dream_nightmare" | "elemental_dragon";

export interface GrimoireDef {
  id: GrimoireId;
  item: string;
  name: string;
  short: string;
  color: string; // Minecraft formatting code for the HUD
}

export const GRIMOIRES: Record<GrimoireId, GrimoireDef> = {
  divine_word: { id: "divine_word", item: "grimoire:divine_word", name: "Codex of the First Word", short: "Divine Word", color: "§6" },
  dream_nightmare: { id: "dream_nightmare", item: "grimoire:dream_nightmare", name: "The Unawakened Codex", short: "Dream & Nightmare", color: "§d" },
  elemental_dragon: { id: "elemental_dragon", item: "grimoire:elemental_dragon", name: "Codex of the Four Primordial Dragons", short: "Elemental Dragon", color: "§a" },
};
export const GRIMOIRE_BY_ITEM: Record<string, GrimoireDef> = Object.fromEntries(Object.values(GRIMOIRES).map((g) => [g.item, g]));
export const GRIMOIRE_ORDER: GrimoireId[] = ["divine_word", "dream_nightmare", "elemental_dragon"];

export interface CastContext {
  caster: Player;
  scene: Scene;
  aim: Aim;
  /** Ticks the Use button was held before release. */
  heldTicks: number;
}

export interface SpellMeta {
  /** Stable id, e.g. "dw01". */
  id: string;
  grimoire: GrimoireId;
  /** 0..5 position inside the Grimoire. */
  index: number;
  name: string;
  /** Short HUD label. */
  short: string;
  /** Approved cooldown in seconds. DO NOT CHANGE. */
  cooldown: number;
  tier: "signature" | "imperial" | "extra";
}

export interface SpellDef extends SpellMeta {
  /**
   * Activate the spell.  Return false to refuse activation (no cooldown starts,
   * the scene is discarded).  Everything spawned through ctx.scene is cleaned up
   * automatically when the scene ends or aborts.
   */
  cast(ctx: CastContext): boolean | void;
}

/** The approved cooldown registry (section 12 of the design brief). */
export const SPELL_META: SpellMeta[] = [
  { id: "dw01", grimoire: "divine_word", index: 0, cooldown: 15, tier: "signature", name: "Seraphic Litany: The Sixfold Sanctus", short: "Seraphic Litany" },
  { id: "dw02", grimoire: "divine_word", index: 1, cooldown: 28, tier: "signature", name: "Cherubic Testament: The Four Living Witnesses", short: "Cherubic Testament" },
  { id: "dw03", grimoire: "divine_word", index: 2, cooldown: 35, tier: "signature", name: "Ophanim: The Unblinking Judgment", short: "Ophanim" },
  { id: "dw04", grimoire: "divine_word", index: 3, cooldown: 45, tier: "signature", name: "Divine Edict: Let There Be Sanctuary", short: "Let There Be Sanctuary" },
  { id: "dw05", grimoire: "divine_word", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Threefold Heavenly Throne", short: "Threefold Heavenly Throne" },
  { id: "dw06", grimoire: "divine_word", index: 5, cooldown: 360, tier: "extra", name: "The Word Before Creation", short: "Word Before Creation" },
  { id: "dn01", grimoire: "dream_nightmare", index: 0, cooldown: 16, tier: "signature", name: "Reverie Procession: Parade of the Sleeping Moon", short: "Reverie Procession" },
  { id: "dn02", grimoire: "dream_nightmare", index: 1, cooldown: 24, tier: "signature", name: "Nightmare Intrusion: The Guest Behind the Door", short: "Nightmare Intrusion" },
  { id: "dn03", grimoire: "dream_nightmare", index: 2, cooldown: 38, tier: "signature", name: "House of Shifting Sleep", short: "House of Shifting Sleep" },
  { id: "dn04", grimoire: "dream_nightmare", index: 3, cooldown: 46, tier: "signature", name: "Lullaby and Scream", short: "Lullaby and Scream" },
  { id: "dn05", grimoire: "dream_nightmare", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The City That Sleeps Above the World", short: "City That Sleeps" },
  { id: "dn06", grimoire: "dream_nightmare", index: 5, cooldown: 360, tier: "extra", name: "The Dreamer Who Never Wakes", short: "Dreamer Who Never Wakes" },
  { id: "ed01", grimoire: "elemental_dragon", index: 0, cooldown: 28, tier: "signature", name: "Genesis Colossus: The Walking Continent", short: "Genesis Colossus" },
  { id: "ed02", grimoire: "elemental_dragon", index: 1, cooldown: 24, tier: "signature", name: "Thermal Tyrant: Furnace of the Carnotaur", short: "Thermal Tyrant" },
  { id: "ed03", grimoire: "elemental_dragon", index: 2, cooldown: 32, tier: "signature", name: "Abyssal Cryotitan: The Frozen Tidal Crown", short: "Abyssal Cryotitan" },
  { id: "ed04", grimoire: "elemental_dragon", index: 3, cooldown: 20, tier: "signature", name: "Aether Raptor: Symphony of the Four Wings", short: "Aether Raptor" },
  { id: "ed05", grimoire: "elemental_dragon", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Chronicle of Buried Kingdoms", short: "Chronicle of Buried Kingdoms" },
  { id: "ed06", grimoire: "elemental_dragon", index: 5, cooldown: 360, tier: "extra", name: "The World Before Names", short: "World Before Names" },
];

export const META_BY_ID: Record<string, SpellMeta> = Object.fromEntries(SPELL_META.map((m) => [m.id, m]));

export function metaFor(grimoire: GrimoireId, index: number): SpellMeta {
  const m = SPELL_META.find((s) => s.grimoire === grimoire && s.index === index);
  if (!m) throw new Error(`no spell ${grimoire}#${index}`);
  return m;
}

const SPELLS = new Map<string, SpellDef>();

/** Build a SpellDef from the approved metadata plus an implementation. */
export function defineSpell(id: string, cast: SpellDef["cast"]): SpellDef {
  const meta = META_BY_ID[id];
  if (!meta) throw new Error(`unknown spell id ${id}`);
  return { ...meta, cast };
}

export function registerSpell(def: SpellDef): void {
  SPELLS.set(def.id, def);
}

export function getSpell(id: string): SpellDef | undefined {
  return SPELLS.get(id);
}

export function allSpells(): SpellDef[] {
  return [...SPELLS.values()];
}
