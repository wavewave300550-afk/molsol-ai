import { Dimension, Player } from "@minecraft/server";
import { Mode } from "../config.js";
import { SteamState } from "../state.js";

export interface Ctx {
  p: Player;
  s: SteamState;
  dim: Dimension;
  tick: number;
  mode: Mode;
  /** Mode power multiplier (damage, knockback, propulsion). */
  power: number;
}

/** `true` = cast succeeded (heat + cooldown are charged); a string = refused, shown to the player. */
export type CastResult = true | string;
export type Cast = (c: Ctx) => CastResult;
