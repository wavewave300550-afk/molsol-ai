import { Dimension, Player } from "@minecraft/server";
import { PlayerState, Race } from "../core/state.js";

export interface CastContext {
  player: Player;
  state: PlayerState;
  dim: Dimension;
  tick: number;
}

export interface Ability {
  id: string;
  name: string;
  /** Compact label for the HUD. */
  short: string;
  /** Energy cost (ultimates cost the full 100). */
  cost: number;
  /** Cooldown in ticks. */
  cooldown: number;
  ultimate?: boolean;
  description: string;
  /** Returns false when nothing happened (no cost / cooldown applied). */
  cast(ctx: CastContext): boolean;
}

export interface PassiveEffect {
  effect: string;
  amplifier: number;
}

export interface Tribe {
  race: Race;
  key: string;
  name: string;
  epithet: string;
  /** Minecraft formatting colour code, e.g. "§a". */
  color: string;
  energyName: string;
  /** Energy regenerated per second (before situational bonuses). */
  regen: number;
  relic: string;
  icon: string;
  lore: string;
  passiveText: string[];
  /** Permanent effects kept on the player while in this tribe. */
  passiveEffects: PassiveEffect[];
  abilities: Ability[];
  /** Extra regen multiplier / situational passives, called every 10 ticks. */
  regenMultiplier?(player: Player): number;
  /** Called every 40 ticks for situational passives. */
  slowPassive?(player: Player, state: PlayerState): void;
  /** Called every 2 ticks for movement passives. */
  fastPassive?(player: Player, state: PlayerState): void;
  /** Energy gained when this player lands a melee hit / gets a kill. */
  hitGain: number;
  killGain: number;
}
