import { Player } from "@minecraft/server";
import { HEAT, Mode, MODES } from "./config.js";
import { add, flat, scale, v } from "./core/vec.js";
import { chest, directed, P, particle, S, sized, sound } from "./core/fx.js";
import { syncProperties } from "./power.js";
import { isOverheated, now, SteamState } from "./state.js";

const OUR_EFFECT_MAX = 60;

function ensureEffect(p: Player, id: "speed" | "strength", amp: number): void {
  if (amp < 0) {
    // Only strip the short effects we granted ourselves, never a long potion the player drank.
    const e = p.getEffect(id);
    if (e && e.duration <= OUR_EFFECT_MAX) p.removeEffect(id);
    return;
  }
  const cur = p.getEffect(id);
  if (cur && cur.amplifier > amp) {
    if (cur.duration > OUR_EFFECT_MAX) return; // a stronger potion the player drank: leave it
    // our own stronger buff (e.g. Steam Boost just ended): vanilla never lets a weaker level
    // replace a stronger one, so remove it first
    p.removeEffect(id);
  } else if (cur && cur.amplifier === amp && cur.duration > 30) return;
  p.addEffect(id, 50, { amplifier: amp, showParticles: false });
}

/** Apply the mode's movement / melee buffs (short, self-refreshing effects so nothing can get stuck). */
export function refreshEffects(p: Player, s: SteamState): void {
  const spec = MODES[s.mode];
  const boost = s.boostUntil > now();
  let speed = spec.speed;
  let strength = spec.strength;
  if (boost) {
    speed = Math.max(0, speed + 1);
    strength = Math.max(0, strength + 1);
  }
  if (isOverheated(s)) {
    speed = -1;
    strength = -1;
  }
  try {
    ensureEffect(p, "speed", speed);
    ensureEffect(p, "strength", strength);
  } catch {
    // player dead / respawning
  }
}

export const isPowered = (s: SteamState): boolean => s.mode !== Mode.Normal;

/**
 * Change gear. Up-shifts cost a little heat and release a pressure burst; down-shifts vent steam.
 * Returns false if the change is not allowed (overheated).
 */
export function setMode(p: Player, s: SteamState, mode: Mode, opts: { silent?: boolean } = {}): boolean {
  if (s.mode === mode) return true;
  if (mode !== Mode.Normal && isOverheated(s)) return false;
  const prev = s.mode;
  s.mode = mode;
  if (mode !== Mode.Redline) s.redlineUntil = 0;
  const shiftHeat = HEAT.shiftHeat[mode] ?? 0;
  if (mode > prev && shiftHeat > 0) s.heat = Math.min(HEAT.max - 1, s.heat + shiftHeat);
  refreshEffects(p, s);
  syncProperties(p, s);
  if (opts.silent) return true;
  const dim = p.dimension;
  const spec = MODES[mode];
  if (mode > prev) {
    sound(dim, S.shift, p.location, 0.9, 0.9 + mode * 0.08);
    sound(dim, S.hiss, p.location, 0.7, 1.1);
    sized(dim, P.ring, add(p.location, v(0, 0.1, 0)), 1.2 + mode * 0.4);
    particle(dim, P.puff, chest(p));
    const back = scale(flat(p.getViewDirection()), -1);
    directed(dim, P.dashJet, add(p.location, v(0, 1.1, 0)), add(back, v(0, 0.4, 0)), 0.8);
  } else {
    sound(dim, S.release, p.location, 0.8, 1.2);
    particle(dim, P.ventRelease, p.location);
  }
  p.onScreenDisplay.setTitle(" ", {
    subtitle: `${spec.color}§l${spec.name} ${mode === Mode.Normal ? "§r§7(vented)" : "MODE"}`,
    fadeInDuration: 0,
    stayDuration: 20,
    fadeOutDuration: 8,
  });
  return true;
}

/** Steam trail, pressure pulses and engine sounds. Called every 2 ticks for each steam user. */
export function movementFx(p: Player, s: SteamState, tick: number): void {
  const loc = p.location;
  if (s.lastPos) {
    const dx = loc.x - s.lastPos.x;
    const dz = loc.z - s.lastPos.z;
    const inst = Math.sqrt(dx * dx + dz * dz) / 2;
    s.speed = s.speed * 0.5 + inst * 0.5;
  }
  s.lastPos = { x: loc.x, y: loc.y, z: loc.z };
  if (isOverheated(s)) return;
  const boost = s.boostUntil > tick;
  if (s.mode === Mode.Normal && !boost) return;
  const dim = p.dimension;
  const moving = s.speed > 0.08;
  const back = scale(flat(p.getViewDirection()), -1);
  if (moving) {
    // world-space steam left behind the body: denser at higher gears and during Steam Boost
    const density = (s.mode - 1) + (boost ? 2 : 0);
    if (density >= 1 && tick % 4 === 0) particle(dim, P.wake, add(add(loc, scale(back, 0.35)), v(0, 1.0, 0)));
    if (density >= 2 && tick % 4 === 2) particle(dim, P.wake, add(add(loc, scale(back, 0.3)), v(0, 0.35, 0)));
    if (density >= 3 && tick % 4 === 0) directed(dim, P.dashJet, add(add(loc, scale(back, 0.25)), v(0, 1.25, 0)), add(back, v(0, 0.25, 0)), 0.6);
  }
  // pressure-release pulses
  const pulseEvery = boost ? 6 : s.mode === Mode.Redline ? 8 : s.mode === Mode.Pressure ? 16 : 0;
  if (pulseEvery && tick % pulseEvery === 0 && (moving || s.mode === Mode.Redline)) {
    sized(dim, P.ring, add(loc, v(0, 0.08, 0)), s.mode === Mode.Redline ? 1.6 : 1.1);
    if (s.mode === Mode.Redline) particle(dim, P.ember, add(loc, v(0, 1.0, 0)));
  }
  // low mechanical engine sounds
  const chugEvery = s.mode === Mode.Redline ? 10 : s.mode === Mode.Pressure ? 20 : boost ? 14 : 40;
  if (tick % chugEvery === 0) sound(dim, S.chug, loc, s.mode === Mode.Redline ? 0.55 : 0.35, 0.8 + s.mode * 0.12);
}
