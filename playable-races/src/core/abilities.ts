/**
 * Ability engine: selection, cooldowns/charges, casting pipeline, channels and the
 * visual-form state machine.  Races only describe *what* their abilities do.
 */
import { Player, system } from "@minecraft/server";
import { CANCEL_GRACE, GLOBAL_CAST_LOCK } from "../config.js";
import { raceByCode } from "../races/registry.js";
import { AbilityDef, CastContext, RaceDef } from "../races/types.js";
import { privateSound } from "./fx.js";
import { showForm } from "./forms.js";
import { Channel, EndReason, Session, save } from "./session.js";
import { secs, warn } from "./util.js";

export function raceOf(s: Session): RaceDef | undefined {
  return s.data.race ? raceByCode(s.data.race) : undefined;
}

export function selected(s: Session, race: RaceDef): AbilityDef {
  const i = ((s.data.sel % race.abilities.length) + race.abilities.length) % race.abilities.length;
  return race.abilities[i];
}

function ctxOf(p: Player, s: Session, race: RaceDef, ability: AbilityDef): CastContext {
  return { p, s, race, ability };
}

export function maxCharges(p: Player, s: Session, race: RaceDef, a: AbilityDef): number {
  return Math.max(1, a.maxCharges ? a.maxCharges(ctxOf(p, s, race, a)) : a.charges ?? 1);
}

function cdTicks(p: Player, s: Session, race: RaceDef, a: AbilityDef): number {
  return Math.max(10, Math.round(a.cooldown * 20 * race.cooldownMul(p, s)));
}

/** Process charge regeneration; returns available charges. */
export function charges(p: Player, s: Session, race: RaceDef, a: AbilityDef): number {
  const max = maxCharges(p, s, race, a);
  const now = system.currentTick;
  if (max <= 1) return (s.readyAt.get(a.id) ?? 0) <= now ? 1 : 0;
  let have = s.data.res[`chg:${a.id}`] ?? max;
  let at = s.chargeAt.get(a.id);
  while (at !== undefined && at <= now && have < max) {
    have++;
    at = have < max ? at + cdTicks(p, s, race, a) : undefined;
  }
  if (have >= max) {
    have = max;
    at = undefined;
  }
  if (at === undefined) s.chargeAt.delete(a.id);
  else s.chargeAt.set(a.id, at);
  if (s.data.res[`chg:${a.id}`] !== have) {
    s.data.res[`chg:${a.id}`] = have;
    s.dirty = true;
  }
  return have;
}

/** Ticks until the ability (or its next charge) is ready. 0 = ready. */
export function remaining(p: Player, s: Session, race: RaceDef, a: AbilityDef): number {
  const now = system.currentTick;
  if (maxCharges(p, s, race, a) <= 1) return Math.max(0, (s.readyAt.get(a.id) ?? 0) - now);
  if (charges(p, s, race, a) > 0) return 0;
  return Math.max(0, (s.chargeAt.get(a.id) ?? now) - now);
}

function spend(p: Player, s: Session, race: RaceDef, a: AbilityDef): void {
  const now = system.currentTick;
  const max = maxCharges(p, s, race, a);
  if (max <= 1) {
    s.readyAt.set(a.id, now + cdTicks(p, s, race, a));
    return;
  }
  const have = charges(p, s, race, a);
  s.data.res[`chg:${a.id}`] = Math.max(0, have - 1);
  if (!s.chargeAt.has(a.id)) s.chargeAt.set(a.id, now + cdTicks(p, s, race, a));
}

/** Reduce remaining cooldowns (e.g. a lunar sigil kill). */
export function refund(s: Session, ticks: number, except?: string): void {
  const now = system.currentTick;
  for (const [id, at] of s.readyAt) if (id !== except) s.readyAt.set(id, Math.max(now, at - ticks));
  for (const [id, at] of s.chargeAt) if (id !== except) s.chargeAt.set(id, Math.max(now, at - ticks));
  s.dirty = true;
}

export function resetCooldowns(s: Session): void {
  s.readyAt.clear();
  s.chargeAt.clear();
  for (const k of Object.keys(s.data.res)) if (k.startsWith("chg:")) delete s.data.res[k];
  s.dirty = true;
}

export function message(s: Session, text: string, ticks = 40): void {
  s.hudMsg = { text, until: system.currentTick + ticks };
  s.hudUntil = Math.max(s.hudUntil, system.currentTick + ticks);
}

export function fail(p: Player, s: Session, reason: string): void {
  message(s, `§c${reason}`);
  privateSound(p, "note.bass", 0.6, 0.6);
}

export function cycle(p: Player, s: Session, dir = 1): void {
  const race = raceOf(s);
  if (!race) return;
  s.data.sel = (((s.data.sel + dir) % race.abilities.length) + race.abilities.length) % race.abilities.length;
  s.dirty = true;
  save(p, s);
  const a = selected(s, race);
  const r = remaining(p, s, race, a);
  message(s, `${race.color}» ${a.name}${r > 0 ? ` §7(${secs(r)})` : " §a(ready)"}`, 30);
  privateSound(p, "random.click", 0.5, 1.5 + 0.1 * s.data.sel);
}

/** Main entry: cast the selected ability. */
export function cast(p: Player, s: Session): void {
  const race = raceOf(s);
  if (!race) {
    fail(p, s, "Choose a lineage first (Lineage Codex)");
    return;
  }
  const a = selected(s, race);
  const now = system.currentTick;
  if (s.channel) {
    const ch = s.channel;
    if (ch.ability === a.id) {
      // the same ability again: a deliberate toggle for cancelable channels, otherwise a
      // repeated/held input that must never interrupt the ability in progress
      if (ch.cancelable && now - ch.started >= CANCEL_GRACE) endChannel(p, s, "cancel");
      return;
    }
    const mode = ch.mode ?? "block";
    if (mode === "interrupt") endChannel(p, s, "interrupt");
    else if (mode === "block") {
      const busy = race.abilities.find((x) => x.id === ch.ability);
      fail(p, s, `Busy: ${busy ? busy.name : "ability in progress"}`);
      return;
    }
  }
  if (now - s.lastCast < GLOBAL_CAST_LOCK) return;
  const r = remaining(p, s, race, a);
  if (r > 0) {
    fail(p, s, `${a.name} recovering: ${secs(r)}`);
    return;
  }
  const ctx = ctxOf(p, s, race, a);
  const reason = a.check ? a.check(ctx) : undefined;
  if (reason) {
    fail(p, s, reason);
    return;
  }
  // asked before the cast changes any state: e.g. the first half of a toggle (Draw the Sun) is free
  const free = a.freeCast?.(ctx) === true;
  let result: true | string;
  try {
    result = a.cast(ctx);
  } catch (e) {
    warn(`${a.id} cast failed`, e);
    result = "The ability faltered";
  }
  if (result !== true) {
    fail(p, s, result);
    return;
  }
  if (!free) spend(p, s, race, a);
  s.lastCast = now;
  s.data.stats.casts = (s.data.stats.casts ?? 0) + 1;
  s.dirty = true;
  s.hudUntil = now + 60;
  save(p, s);
}

// ---------------------------------------------------------------- channels

export function startChannel(p: Player, s: Session, ch: Omit<Channel, "started">): void {
  if (s.channel) endChannel(p, s, "interrupt");
  s.channel = { ...ch, started: system.currentTick };
}

export function endChannel(p: Player, s: Session, reason: EndReason): void {
  const ch = s.channel;
  if (!ch) return;
  s.channel = undefined;
  try {
    ch.end(s, p, reason);
  } catch (e) {
    warn(`channel ${ch.ability} end failed`, e);
  }
}

export function tickChannel(p: Player, s: Session): void {
  const ch = s.channel;
  if (!ch) return;
  const t = system.currentTick;
  if (t >= ch.until) {
    endChannel(p, s, "complete");
    return;
  }
  try {
    ch.tick?.(s, p, t - ch.started);
  } catch (e) {
    warn(`channel ${ch.ability} tick failed`, e);
    endChannel(p, s, "interrupt");
  }
}

// ---------------------------------------------------------------- visual form

/** Temporarily show a configuration (e.g. golem siege hammer) for `ticks`. */
export function tempForm(p: Player, s: Session, variant: string, ticks: number): void {
  s.tempVariant = { variant, until: system.currentTick + ticks };
  refreshForm(p, s);
}

export function clearTempForm(p: Player, s: Session): void {
  s.tempVariant = undefined;
  refreshForm(p, s);
}

export function refreshForm(p: Player, s: Session): void {
  if (s.diag) return; // the display check owns the head slot for a moment
  const race = raceOf(s);
  if (!race || s.data.veiled) return;
  let v = race.variant(p, s);
  if (s.tempVariant) {
    if (s.tempVariant.until > system.currentTick) v = s.tempVariant.variant;
    else s.tempVariant = undefined;
  }
  showForm(p, race, s, v);
}
