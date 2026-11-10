import { Player } from "@minecraft/server";
import { HEAT, Mode, MODES } from "./config.js";
import { add, v } from "./core/vec.js";
import { chest, P, particle, S, shake, sound } from "./core/fx.js";
import { refreshEffects, setMode } from "./modes.js";
import { syncProperties } from "./power.js";
import { isOverheated, notice, now, SteamState } from "./state.js";

/**
 * Add heat from an ability (scaled by the current gear). Triggers OVERHEAT at 100.
 * Returns the heat actually added.
 */
export function addHeat(p: Player, s: SteamState, base: number): number {
  if (isOverheated(s)) return 0;
  const amount = base * MODES[s.mode].heatMult;
  const before = s.heat;
  s.heat = Math.min(HEAT.max, s.heat + amount);
  s.lastAbilityTick = now();
  if (s.heat >= HEAT.max) overheat(p, s);
  else if (before < HEAT.warnAt && s.heat >= HEAT.warnAt) warn(p, s);
  syncProperties(p, s);
  return amount;
}

function warn(p: Player, s: SteamState): void {
  notice(s, "§c§lPRESSURE CRITICAL §r§7- vent or overheat!", 50);
  sound(p.dimension, S.hiss, p.location, 0.9, 1.5);
}

/** OVERHEAT: drop to NORMAL, lock every steam ability, slow the player, vent violently. */
export function overheat(p: Player, s: SteamState): void {
  const t = now();
  s.heat = HEAT.max;
  s.overheatUntil = t + HEAT.lockout;
  s.boostUntil = 0;
  s.knucklePrimedUntil = 0;
  s.igniting = false;
  setMode(p, s, Mode.Normal, { silent: true });
  s.activeSkill = "OVERHEAT";
  s.activeSkillUntil = s.overheatUntil;
  refreshEffects(p, s);
  try {
    p.addEffect("slowness", HEAT.penaltyTicks, { amplifier: HEAT.penaltySlowAmp, showParticles: false });
  } catch {
    // dead
  }
  const dim = p.dimension;
  sound(dim, S.overheat, p.location, 1.2, 1);
  sound(dim, S.release, p.location, 1, 0.8);
  particle(dim, P.ventRelease, p.location);
  particle(dim, P.scaldCloud, chest(p));
  particle(dim, P.ember, chest(p));
  shake(p, 0.35, 0.6);
  p.onScreenDisplay.setTitle("§4§lOVERHEAT", {
    subtitle: "§cSteam systems locked §7- cooling down",
    fadeInDuration: 0,
    stayDuration: 40,
    fadeOutDuration: 10,
  });
  s.hudUntil = s.overheatUntil + 60;
  syncProperties(p, s);
}

/** Called every 5 ticks: cooling, idle heat of higher gears, overheat recovery, timed modes. */
export function tickHeat(p: Player, s: SteamState): void {
  const t = now();
  const dim = p.dimension;
  const dt = 5 / 20;

  if (s.overheatUntil > 0) {
    if (t < s.overheatUntil) {
      // Gauge drains from 100 to lockoutEndHeat over the lockout, with heavy venting.
      const left = (s.overheatUntil - t) / HEAT.lockout;
      s.heat = HEAT.lockoutEndHeat + (HEAT.max - HEAT.lockoutEndHeat) * left;
      if (t % 10 === 0) particle(dim, P.coolWisp, add(p.location, v(0, 1.0, 0)));
      if (t % 30 === 0) sound(dim, S.hiss, p.location, 0.5, 0.7);
      syncProperties(p, s);
      return;
    }
    // lockout finished: systems restored
    s.overheatUntil = 0;
    s.activeSkill = "";
    s.lastAbilityTick = t - HEAT.coolDelay;
    sound(dim, S.cool, p.location, 1, 1);
    particle(dim, P.coolWisp, chest(p));
    notice(s, "§aPressure stabilised §7- steam systems online", 60);
    syncProperties(p, s);
    return;
  }

  // timed states
  if (s.mode === Mode.Redline && t >= s.redlineUntil) {
    setMode(p, s, Mode.Heat, { silent: true });
    sound(dim, S.release, p.location, 1, 1);
    particle(dim, P.ventRelease, p.location);
    notice(s, "§6Redline disengaged §7- back to HEAT", 50);
  }
  if (s.boostUntil > 0 && t >= s.boostUntil) {
    s.boostUntil = 0;
    refreshEffects(p, s);
    sound(dim, S.release, p.location, 0.5, 1.3);
  }

  let rate = MODES[s.mode].idleHeatPerSec;
  if (rate < 0) {
    if (t - s.lastAbilityTick < HEAT.coolDelay) rate = 0;
    else if (p.isInWater) {
      rate *= HEAT.wetCoolMult;
      if (s.heat > 0 && t % 10 === 0) particle(dim, P.coolWisp, add(p.location, v(0, 1.2, 0)));
    }
  }
  const before = s.heat;
  s.heat = Math.max(0, Math.min(HEAT.max, s.heat + rate * dt));
  if (s.heat >= HEAT.max) {
    overheat(p, s);
    return;
  }
  if (before < HEAT.warnAt && s.heat >= HEAT.warnAt) warn(p, s);
  // visible cooling: thin wisps while a hot body sheds heat in NORMAL gear
  if (s.mode === Mode.Normal && s.heat > 15 && rate < 0 && t % 20 === 0) particle(dim, P.coolWisp, add(p.location, v(0, 1.1, 0)));
  syncProperties(p, s);
}
