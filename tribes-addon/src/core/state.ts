import { Player, system } from "@minecraft/server";

export const RACE_PROPERTY = "tribes:race";

export enum Race {
  None = 0,
  Dinosauroid = 1,
  Anunnaki = 2,
  Pastafarian = 3,
  Spacer = 4,
}

export interface PlayerState {
  energy: number;
  selected: number;
  cooldowns: Map<string, number>;
  /** Tick until which fall damage is ignored (leaps, jetpack). */
  fallImmuneUntil: number;
  /** Debounce: last tick an ability or menu action fired. */
  lastAction: number;
  /** Tick until which the HUD stays visible even without holding the relic. */
  hudUntil: number;
  hudEnabled: boolean;
}

const states = new Map<string, PlayerState>();

export function state(player: Player): PlayerState {
  let s = states.get(player.id);
  if (!s) {
    const savedHud = player.getDynamicProperty("tribes:hud");
    s = {
      energy: 50,
      selected: 0,
      cooldowns: new Map(),
      fallImmuneUntil: 0,
      lastAction: -100,
      hudUntil: 0,
      hudEnabled: savedHud !== false,
    };
    states.set(player.id, s);
  }
  return s;
}

export function dropState(playerId: string): void {
  states.delete(playerId);
}

export function getRace(player: Player): Race {
  const r = player.getDynamicProperty(RACE_PROPERTY);
  return typeof r === "number" && r >= 0 && r <= 4 ? (r as Race) : Race.None;
}

/** Persist the race and mirror it into the synced entity property that drives the player model. */
export function setRace(player: Player, race: Race): void {
  player.setDynamicProperty(RACE_PROPERTY, race);
  syncRaceProperty(player);
  const s = state(player);
  s.selected = 0;
  s.cooldowns.clear();
  s.energy = 50;
}

export function syncRaceProperty(player: Player): void {
  const race = getRace(player);
  try {
    if (player.getProperty(RACE_PROPERTY) !== race) player.setProperty(RACE_PROPERTY, race);
  } catch (e) {
    console.warn(`[tribes] could not set player property (is the behavior pack player.json active?): ${e}`);
  }
}

export const now = (): number => system.currentTick;
