import { Dimension, Entity, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { add, dist, lerp, v } from "./vec.js";

/** Server-spawned particle effects (resource pack particles/sekiyu/*.json). */
export const P = {
  splash: "sekiyu:oil_splash",
  spray: "sekiyu:oil_spray",
  drip: "sekiyu:oil_drip",
  ring: "sekiyu:oil_ring",
  column: "sekiyu:oil_column",
  bubble: "sekiyu:oil_bubble",
  trail: "sekiyu:oil_trail",
  tendril: "sekiyu:tar_rise",
  dissolve: "sekiyu:dissolve",
  reform: "sekiyu:reform",
  dodge: "sekiyu:logia_splash",
  fire: "sekiyu:fire_burst",
  fireRing: "sekiyu:fire_ring",
  fireColumn: "sekiyu:fire_column",
  poolFire: "sekiyu:pool_fire",
  smoke: "sekiyu:black_smoke",
  ember: "sekiyu:embers",
  flash: "sekiyu:ignite_flash",
} as const;

/** Custom sounds (sounds/sound_definitions.json). */
export const S = {
  splash: "sekiyu.oil.splash",
  gurgle: "sekiyu.oil.gurgle",
  slurp: "sekiyu.oil.slurp",
  reform: "sekiyu.oil.reform",
  tide: "sekiyu.tide.roar",
  rumble: "sekiyu.geyser.rumble",
  erupt: "sekiyu.geyser.erupt",
  squelch: "sekiyu.prison.squelch",
  jet: "sekiyu.jet.whoosh",
  hiss: "sekiyu.serpent.hiss",
  bite: "sekiyu.serpent.bite",
  ignite: "sekiyu.fire.ignite",
  crackle: "sekiyu.fire.crackle",
  infernoRise: "sekiyu.inferno.rise",
  infernoBlast: "sekiyu.inferno.blast",
  dodge: "sekiyu.logia.dodge",
  melt: "sekiyu.logia.melt",
  sealed: "sekiyu.logia.sealed",
  deny: "sekiyu.ui.deny",
  click: "sekiyu.ui.click",
  awaken: "sekiyu.fruit.awaken",
} as const;

export function particle(dim: Dimension, id: string, at: Vector3, vars?: MolangVariableMap): void {
  try {
    dim.spawnParticle(id, at, vars);
  } catch {
    // unloaded chunk / out of world: cosmetic only
  }
}

/** Particle with a travel direction (`variable.direction`) and strength (`variable.power`). */
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

/** Ring / area particle sized by `variable.radius`. */
export function sized(dim: Dimension, id: string, at: Vector3, radius: number): void {
  try {
    const m = new MolangVariableMap();
    m.setFloat("variable.radius", radius);
    dim.spawnParticle(id, at, m);
  } catch {
    // cosmetic
  }
}

export function line(dim: Dimension, id: string, from: Vector3, to: Vector3, step: number): void {
  const n = Math.max(1, Math.floor(dist(from, to) / step));
  for (let i = 0; i <= n; i++) particle(dim, id, lerp(from, to, i / n));
}

export function sound(dim: Dimension, id: string, at: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    // cosmetic
  }
}

export function shake(p: Player, intensity: number, seconds: number): void {
  try {
    p.runCommand(`camerashake add @s ${intensity.toFixed(2)} ${seconds.toFixed(2)} positional`);
  } catch {
    // cosmetic
  }
}

export type PlayerAnim = "tide" | "geyser" | "prison" | "jet" | "serpent" | "inferno" | "ignite" | "melt";

export function anim(p: Player, name: PlayerAnim): void {
  try {
    p.playAnimation(`animation.sekiyu.player.${name}`, { blendOutTime: 0.15 });
  } catch {
    // animation unavailable: gameplay is unaffected
  }
}

export function entityAnim(e: Entity, name: string): void {
  try {
    e.playAnimation(name, { blendOutTime: 0.1 });
  } catch {
    // cosmetic
  }
}

export const center = (e: Entity): Vector3 => add(e.location, v(0, 0.9, 0));
