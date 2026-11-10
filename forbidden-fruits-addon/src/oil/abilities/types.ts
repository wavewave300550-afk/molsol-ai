import { Dimension, Player } from "@minecraft/server";
import { OilState } from "../state.js";

export interface Ctx {
  p: Player;
  s: OilState;
  dim: Dimension;
  tick: number;
}

/** `true` = cast happened (cooldown starts); a string = refused, shown to the player. */
export type CastResult = true | string;
export type Cast = (c: Ctx) => CastResult;
