import type { Routine } from "../core/tasks";
import type { Cast, Prep } from "./context";

export type School = "pressure" | "ice" | "blood";
export const SCHOOLS: School[] = ["pressure", "ice", "blood"];

export const GRIMOIRE_ITEMS: Record<School, string> = {
  pressure: "grimoire:pressure",
  ice: "grimoire:ice",
  blood: "grimoire:blood",
};

export const SCHOOL_NAMES: Record<School, string> = {
  pressure: "Pressure Grimoire",
  ice: "Ice Grimoire",
  blood: "Blood Grimoire",
};

export const SCHOOL_COLOR: Record<School, string> = { pressure: "§6", ice: "§b", blood: "§c" };

export function schoolOfItem(typeId: string | undefined): School | undefined {
  switch (typeId) {
    case "grimoire:pressure":
      return "pressure";
    case "grimoire:ice":
      return "ice";
    case "grimoire:blood":
      return "blood";
    default:
      return undefined;
  }
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
