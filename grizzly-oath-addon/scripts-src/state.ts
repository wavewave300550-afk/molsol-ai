import { Entity, Player, system } from "@minecraft/server";
import { PROP_SKILL, SKILLS } from "./config.js";

export interface PlayerState {
  skill: number; // selected special skill (0..3)
  readyAt: number[]; // tick at which each skill is off cooldown
  lastUse: number; // debounce for the use button
  parity: number; // alternates left / right cleave
  busyUntil: number;
  flashUntil: number;
  flashText: string;
  willUntil: number;
  willTier: number;
  nextPulse: number;
  ultUntil: number;
}

const states = new Map<string, PlayerState>();

export const now = (): number => system.currentTick;

export function state(p: Player): PlayerState {
  let s = states.get(p.id);
  if (!s) {
    let skill = 0;
    try {
      const saved = p.getDynamicProperty(PROP_SKILL);
      if (typeof saved === "number" && saved >= 0 && saved < SKILLS.length) skill = Math.floor(saved);
    } catch {
      // keep default
    }
    s = {
      skill,
      readyAt: SKILLS.map(() => 0),
      lastUse: -100,
      parity: 0,
      busyUntil: 0,
      flashUntil: 0,
      flashText: "",
      willUntil: 0,
      willTier: 0,
      nextPulse: 0,
      ultUntil: 0,
    };
    states.set(p.id, s);
  }
  return s;
}

export const dropState = (id: string) => states.delete(id);

/** Visual entities (grizzlies) spawned by skills, removed when their time is up. */
export interface FxEntity {
  entity: Entity;
  owner: string;
  removeAt: number;
}

export const fxEntities = new Map<string, FxEntity>();
