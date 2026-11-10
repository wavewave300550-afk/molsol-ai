import { Player, system, Vector3 } from "@minecraft/server";
import { AbilityId, DP, Mode } from "./config.js";

/** Runtime (non-persistent) state of one steam user. Lives only while the player is online. */
export interface SteamState {
  heat: number;
  mode: Mode;
  /** Tick at which the overheat lockout ends (0 = not overheated). */
  overheatUntil: number;
  /** Tick of the last ability: passive cooling waits HEAT.coolDelay after it. */
  lastAbilityTick: number;
  cooldowns: Map<AbilityId, number>;
  boostUntil: number;
  redlineUntil: number;
  /** Redline ignition sequence in progress (prevents double activation). */
  igniting: boolean;
  knucklePrimedUntil: number;
  fallGuardUntil: number;
  airJumpsUsed: number;
  selected: number;
  /** Debounce for item use / menu. */
  lastAction: number;
  hudUntil: number;
  hudEnabled: boolean;
  /** Most recent / currently running skill shown on the HUD. */
  activeSkill: string;
  activeSkillUntil: number;
  /** Values last pushed into the client-synced actor properties. */
  synced: { mode: number; heat: number; overheat: boolean };
  lastPos?: Vector3;
  /** Blocks per tick moved horizontally, smoothed. */
  speed: number;
  /** Message flash on the HUD (e.g. "Recharging 2.1s"). */
  notice: string;
  noticeUntil: number;
  /** Plain Use is ignored until this tick (right after switching skills / closing the console). */
  castGuardUntil: number;
  /** Was the player sneaking on the previous check (to detect a new Sneak press). */
  wasSneaking: boolean;
  /** Tick of the last Sneak-press skill step and the selection before it (-1 = none pending). */
  lastStep: number;
  stepFrom: number;
}

const states = new Map<string, SteamState>();

export const now = (): number => system.currentTick;

export function isOwner(p: Player): boolean {
  try {
    return p.getDynamicProperty(DP.owner) === true;
  } catch {
    return false;
  }
}

export function state(p: Player): SteamState {
  let s = states.get(p.id);
  if (!s) {
    const sel = p.getDynamicProperty(DP.selected);
    s = {
      heat: 0,
      mode: Mode.Normal,
      overheatUntil: 0,
      lastAbilityTick: -1000,
      cooldowns: new Map(),
      boostUntil: 0,
      redlineUntil: 0,
      igniting: false,
      knucklePrimedUntil: 0,
      fallGuardUntil: 0,
      airJumpsUsed: 0,
      selected: typeof sel === "number" && sel >= 0 && sel < 9 ? Math.floor(sel) : 0,
      lastAction: -100,
      hudUntil: 0,
      hudEnabled: p.getDynamicProperty(DP.hud) !== false,
      activeSkill: "",
      activeSkillUntil: 0,
      synced: { mode: -1, heat: -1, overheat: false },
      speed: 0,
      notice: "",
      noticeUntil: 0,
      castGuardUntil: 0,
      wasSneaking: false,
      lastStep: -1,
      stepFrom: 0,
    };
    states.set(p.id, s);
  }
  return s;
}

export function dropState(playerId: string): void {
  states.delete(playerId);
}

export const isOverheated = (s: SteamState): boolean => s.overheatUntil > now();

export function notice(s: SteamState, text: string, ticks = 40): void {
  s.notice = text;
  s.noticeUntil = now() + ticks;
  s.hudUntil = Math.max(s.hudUntil, now() + ticks);
}

export function setActive(s: SteamState, name: string, ticks: number): void {
  s.activeSkill = name;
  s.activeSkillUntil = now() + ticks;
}
