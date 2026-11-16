import { Player, system, Vector3 } from "@minecraft/server";

export type LinePhase = "idle" | "whirl" | "flight" | "anchored" | "hooked" | "bobber" | "snagged";

export interface LineState {
  phase: LinePhase;
  whirlStart: number;
  revsDone: number;
  hookId?: string;
  bobberId?: string;
  targetId?: string;
  anchor?: Vector3;
  anchorBlock?: Vector3;
  anchorType?: string;
  sticky: boolean;
  bends: Vector3[];
  length: number;
  strain: number;
  reeling: boolean;
  lastHookPos?: Vector3;
  lastHookVel?: Vector3;
  castTick: number;
  slot: number;
  nextBite: number;
  biteUntil: number;
  deep: boolean;
  yanked: boolean;
  whirlHit: Map<string, number>;
}

export interface GogglesState {
  mode: "none" | "charge" | "sundog" | "spent";
  start: number;
  charge: number;
  cap: number;
  fullSince: number;
  lastChime: number;
  fovOn: boolean;
}

export interface CaneState {
  gripStart: number;
  gripping: boolean;
  glintShown: boolean;
  deflectStart: number;
  deflectUntil: number;
  deflected: boolean;
  notoAt: number;
  lastBlood?: { r: number; g: number; b: number };
}

export interface SunDogState {
  id: string;
  until: number;
  light: number;
  lightPos?: Vector3;
  dim: string;
}

export interface PlayerState {
  id: string;
  using: boolean;
  usingItem?: string;
  lastHud: string;
  lastHudTick: number;
  cd: Map<string, number>;
  hint?: { text: string; until: number };
  lastHeld?: string;
  lastSlot: number;
  goggles: GogglesState;
  line: LineState;
  cane: CaneState;
  sunDog?: SunDogState;
  loreChecked: Set<string>;
}

const states = new Map<string, PlayerState>();

export function freshLine(): LineState {
  return {
    phase: "idle", whirlStart: 0, revsDone: 0, sticky: false, bends: [], length: 0, strain: 0, reeling: false,
    castTick: 0, slot: -1, nextBite: 0, biteUntil: 0, deep: false, yanked: false, whirlHit: new Map(),
  };
}

export function stateOf(p: Player): PlayerState {
  let s = states.get(p.id);
  if (!s) {
    s = {
      id: p.id,
      using: false,
      lastHud: "",
      lastHudTick: 0,
      cd: new Map(),
      lastSlot: p.selectedSlotIndex,
      goggles: { mode: "none", start: 0, charge: 0, cap: 0, fullSince: -1, lastChime: 0, fovOn: false },
      line: freshLine(),
      cane: { gripStart: 0, gripping: false, glintShown: false, deflectStart: -100, deflectUntil: -100, deflected: false, notoAt: -1 },
      loreChecked: new Set(),
    };
    states.set(p.id, s);
  }
  return s;
}

export function dropState(id: string): void {
  states.delete(id);
}

export function allStates(): IterableIterator<PlayerState> {
  return states.values();
}

export const now = (): number => system.currentTick;

export function ready(s: PlayerState, key: string): boolean {
  return (s.cd.get(key) ?? 0) <= now();
}

export function remaining(s: PlayerState, key: string): number {
  return Math.max(0, (s.cd.get(key) ?? 0) - now());
}

export function startCd(s: PlayerState, key: string, ticks: number): void {
  s.cd.set(key, now() + Math.max(0, Math.round(ticks)));
}

export function hint(s: PlayerState, text: string, ticks = 40): void {
  s.hint = { text, until: now() + ticks };
}
