import { Player, system, Vector3 } from "@minecraft/server";
import { AbilityId, DP, Form } from "./config.js";

/** Follow-up window of an active ability (second Use = ignite / reform / afterburn). */
export interface FollowUp {
  id: AbilityId;
  until: number;
  run: () => void;
}

/** Runtime (non-persistent) state of one petroleum user. */
export interface OilState {
  form: Form;
  burningUntil: number;
  cooldowns: Map<AbilityId, number>;
  followUp?: FollowUp;
  dissolvedUntil: number;
  reflexReadyAt: number;
  fallGuardUntil: number;
  lastFlare: number;
  lastTrail: number;
  selected: number;
  lastAction: number;
  castGuardUntil: number;
  wasSneaking: boolean;
  lastStep: number;
  stepFrom: number;
  hudUntil: number;
  hudEnabled: boolean;
  activeSkill: string;
  activeSkillUntil: number;
  notice: string;
  noticeUntil: number;
  sealed: boolean;
  synced: { form: number; burning: boolean };
  lastPos?: Vector3;
  speed: number;
  /** players currently tinted by this caster's Black Inferno fog (to remove it later) */
  fogged: Set<string>;
}

const states = new Map<string, OilState>();

export const now = (): number => system.currentTick;

export function isOwner(p: Player): boolean {
  try {
    return p.getDynamicProperty(DP.owner) === true;
  } catch {
    return false;
  }
}

export function state(p: Player): OilState {
  let s = states.get(p.id);
  if (!s) {
    const sel = p.getDynamicProperty(DP.selected);
    s = {
      form: Form.Human,
      burningUntil: 0,
      cooldowns: new Map(),
      dissolvedUntil: 0,
      reflexReadyAt: 0,
      fallGuardUntil: 0,
      lastFlare: -100,
      lastTrail: -100,
      selected: typeof sel === "number" && sel >= 0 && sel < 8 ? Math.floor(sel) : 0,
      lastAction: -100,
      castGuardUntil: 0,
      wasSneaking: false,
      lastStep: -1,
      stepFrom: 0,
      hudUntil: 0,
      hudEnabled: p.getDynamicProperty(DP.hud) !== false,
      activeSkill: "",
      activeSkillUntil: 0,
      notice: "",
      noticeUntil: 0,
      sealed: false,
      synced: { form: -1, burning: false },
      speed: 0,
      fogged: new Set(),
    };
    states.set(p.id, s);
  }
  return s;
}

export function dropState(id: string): void {
  states.delete(id);
}

export function allStates(): IterableIterator<[string, OilState]> {
  return states.entries();
}

export function notice(s: OilState, text: string, ticks = 40): void {
  s.notice = text;
  s.noticeUntil = now() + ticks;
  s.hudUntil = Math.max(s.hudUntil, now() + ticks);
}

export function setActive(s: OilState, name: string, ticks: number): void {
  s.activeSkill = name;
  s.activeSkillUntil = now() + ticks;
}

export function setFollowUp(s: OilState, id: AbilityId, ticks: number, run: () => void): void {
  s.followUp = { id, until: now() + ticks, run };
}

export function clearFollowUp(s: OilState, id?: AbilityId): void {
  if (!id || s.followUp?.id === id) s.followUp = undefined;
}

export const isLiquidForm = (s: OilState): boolean => s.form === Form.Body || s.form === Form.Dissolved;
