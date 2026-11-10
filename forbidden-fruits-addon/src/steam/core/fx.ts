import { Dimension, Entity, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { add, dist, lerp, scale, v } from "./vec.js";

/** Server-spawned particle effects shipped in the resource pack (particles/joki/*.json). */
export const P = {
  jet: "joki:jet",
  puff: "joki:puff",
  wake: "joki:wake",
  ring: "joki:shock_ring",
  scaldCloud: "joki:scald_cloud",
  cloudLinger: "joki:cloud_linger",
  mistCloud: "joki:mist_cloud",
  mistFade: "joki:mist_fade",
  impact: "joki:impact",
  cone: "joki:cone_blast",
  boltCore: "joki:bolt_core",
  boltTrail: "joki:bolt_trail",
  downjet: "joki:downjet",
  dashJet: "joki:dash_jet",
  land: "joki:land",
  igniteSwirl: "joki:ignite_swirl",
  redlineBurst: "joki:redline_burst",
  ventRelease: "joki:vent_release",
  ember: "joki:ember",
  coolWisp: "joki:cool_wisp",
  handSteam: "joki:hand_steam",
  fruitAura: "joki:fruit_aura",
} as const;

/** Custom sounds (sounds/sound_definitions.json). */
export const S = {
  hiss: "joki.steam.hiss",
  jet: "joki.steam.jet",
  boost: "joki.steam.boost",
  dash: "joki.steam.dash",
  jump: "joki.steam.jump",
  land: "joki.steam.land",
  cannon: "joki.steam.cannon",
  impact: "joki.steam.impact",
  punch: "joki.steam.punch",
  kick: "joki.steam.kick",
  explode: "joki.steam.explode",
  mist: "joki.steam.mist",
  chug: "joki.engine.chug",
  shift: "joki.engine.shift",
  redlineCharge: "joki.redline.charge",
  redlineEngage: "joki.redline.engage",
  release: "joki.steam.release",
  overheat: "joki.overheat.alarm",
  cool: "joki.overheat.cool",
  deny: "joki.ui.deny",
  click: "joki.ui.click",
  awaken: "joki.fruit.awaken",
} as const;

export function particle(dim: Dimension, id: string, at: Vector3, vars?: MolangVariableMap): void {
  try {
    dim.spawnParticle(id, at, vars);
  } catch {
    // unloaded chunk or outside the world: purely cosmetic
  }
}

/** Particle that takes a travel direction (`variable.direction`) and optional strength (`variable.power`). */
export function directed(dim: Dimension, id: string, at: Vector3, dir: Vector3, power = 1): void {
  try {
    const m = new MolangVariableMap();
    m.setVector3("variable.direction", dir);
    m.setFloat("variable.power", power);
    dim.spawnParticle(id, at, m);
  } catch {
    // cosmetic
  }
}

/** Ring / cloud particle sized by `variable.radius`. */
export function sized(dim: Dimension, id: string, at: Vector3, radius: number): void {
  try {
    const m = new MolangVariableMap();
    m.setFloat("variable.radius", radius);
    dim.spawnParticle(id, at, m);
  } catch {
    // cosmetic
  }
}

/** Evenly spaced directed particles along a line (used for steam streams). */
export function stream(dim: Dimension, id: string, from: Vector3, to: Vector3, step: number, dir: Vector3, power = 1): void {
  const d = dist(from, to);
  const n = Math.max(1, Math.floor(d / step));
  for (let i = 0; i <= n; i++) directed(dim, id, lerp(from, to, i / n), dir, power);
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // cosmetic
  }
}

/** Camera shake for one player (vanilla /camerashake). */
export function shake(p: Player, intensity: number, seconds: number): void {
  try {
    p.runCommand(`camerashake add @s ${intensity.toFixed(2)} ${seconds.toFixed(2)} positional`);
  } catch {
    // command unavailable (e.g. restricted) - cosmetic
  }
}

/** Play one of the add-on's player animations (resource pack animations/joki_player.animation.json). */
export function anim(p: Player, name: "knuckle" | "kick" | "cannon" | "burst" | "ignite" | "jump" | "dash" | "veil" | "boost"): void {
  try {
    p.playAnimation(`animation.joki.player.${name}`, { blendOutTime: 0.15 });
  } catch {
    // animation unavailable: gameplay is unaffected
  }
}

export const center = (e: Entity): Vector3 => add(e.location, v(0, 0.9, 0));
export const chest = (p: Player): Vector3 => add(p.location, v(0, 1.25, 0));

/** Point in front of the player's right hand, used as the muzzle for steam attacks. */
export function rightHand(p: Player, forward = 0.55): Vector3 {
  const d = p.getViewDirection();
  const r = { x: -d.z, y: 0, z: d.x };
  const rl = Math.sqrt(r.x * r.x + r.z * r.z) || 1;
  const head = p.getHeadLocation();
  return add(add(head, scale({ x: r.x / rl, y: 0, z: r.z / rl }, 0.36)), add(scale(d, forward), v(0, -0.38, 0)));
}
