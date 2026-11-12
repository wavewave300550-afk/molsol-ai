import type { Routine } from "../core/tasks";
import type { Cast, Prep } from "./context";

export type School = "pressure" | "ice" | "blood" | "plasma" | "darkness" | "prism_light";
export const SCHOOLS: School[] = ["pressure", "ice", "blood", "plasma", "darkness", "prism_light"];

/** Spell code prefix per Grimoire (P01, I01, B01, PL01, D01, PR01). */
export const CODE_PREFIX: Record<School, string> = { pressure: "P", ice: "I", blood: "B", plasma: "PL", darkness: "D", prism_light: "PR" };

export const GRIMOIRE_ITEMS: Record<School, string> = {
  pressure: "grimoire:pressure",
  ice: "grimoire:ice",
  blood: "grimoire:blood",
  plasma: "grimoire:plasma",
  darkness: "grimoire:darkness",
  prism_light: "grimoire:prism_light",
};

export const SCHOOL_NAMES: Record<School, string> = {
  pressure: "Pressure Grimoire",
  ice: "Ice Grimoire",
  blood: "Blood Grimoire",
  plasma: "Plasma Grimoire",
  darkness: "Darkness Grimoire",
  prism_light: "Prism Light Grimoire",
};

export const SCHOOL_COLOR: Record<School, string> = { pressure: "§6", ice: "§b", blood: "§c", plasma: "§d", darkness: "§2", prism_light: "§f" };

export function schoolOfItem(typeId: string | undefined): School | undefined {
  if (!typeId) return undefined;
  for (const s of SCHOOLS) if (GRIMOIRE_ITEMS[s] === typeId) return s;
  return undefined;
}

export interface SpellDef {
  /** Display code, e.g. "P01". */
  code: string;
  /** Stable unique id used for cooldowns and saved state, e.g. "pressure.lance". */
  id: string;
  school: School;
  name: string;
  /** Cooldown in seconds (the only casting restriction; there is no mana). */
  cooldown: number;
  /** Minimum preparation (hold) in ticks before a release activates the spell. */
  charge: number;
  /** Whether Equilibrium Theft's single-use empowerment applies to (and is consumed by) this spell. */
  enhanceable: boolean;
  /** Cooldown starts when the spell ends instead of on activation (only Wings of the Winter Seraph). */
  cooldownAfterEnd?: boolean;
  /** Configurable gameplay values (damage, radius, duration ...). */
  params: Record<string, number>;
  /** Short description shown in the guide. */
  blurb: string;
  /** Optional formation visuals while the player holds Use (dissolved if cancelled). */
  prepare?: (p: Prep) => void;
  /** Activation: returns the spell's timeline routine. Throw Fizzle to abort without cooldown. */
  cast: (c: Cast) => Routine | void;
}

/** Thrown by a spell's cast() to cancel activation (no cooldown is consumed). */
export class Fizzle extends Error {
  constructor(readonly reason: string) {
    super(reason);
  }
}
