import { Dimension, Entity, MolangVariableMap, Player, system, world } from "@minecraft/server";
import { rules } from "../config";
import { log } from "./log";
import { OWNER_PROP } from "./combat";
import { V3, add, dist2, yawPitchOf } from "./vec";

/**
 * Constructs are lightweight, non-colliding, invulnerable entities that carry the 3D models
 * of spells. Their client animation controllers react to synced entity properties:
 *  - grimoire:phase    0..15 (spell-defined timeline step; 15 = dissolve)
 *  - grimoire:yaw / grimoire:pitch   orientation (degrees, Minecraft convention)
 *  - grimoire:size     uniform scale multiplier
 *  - grimoire:len      stretch along the model's forward axis (beams, threads, chains)
 *  - grimoire:variant  model/texture variant inside one construct type
 *  - grimoire:aux      pulse counter: every increment replays a short "pulse" reaction
 */
export const PHASE_DISSOLVE = 15;
export const SESSION_PROP = "grimoire:session";
export const SESSION = `${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;

export interface FxInit {
  yaw?: number;
  pitch?: number;
  size?: number;
  len?: number;
  variant?: number;
  phase?: number;
  aux?: number;
  dir?: V3;
}

const registry = new Map<string, Fx>();

export class Fx {
  private props = new Map<string, number>();
  private lastPos: V3;
  private dying = false;
  constructor(
    readonly entity: Entity,
    readonly type: string,
    readonly ownerId: string,
    loc: V3,
  ) {
    this.lastPos = loc;
  }

  get ok(): boolean {
    return !this.dying && this.entity.isValid;
  }

  get location(): V3 {
    return this.lastPos;
  }

  private set(name: string, value: number): this {
    if (!this.entity.isValid) return this;
    if (this.props.get(name) === value) return this;
    this.props.set(name, value);
    try {
      this.entity.setProperty(`grimoire:${name}`, value);
    } catch (e) {
      log.debug(`setProperty ${name} on ${this.type}`, String(e));
    }
    return this;
  }

  phase(n: number): this {
    return this.set("phase", Math.max(0, Math.min(15, Math.round(n))));
  }
  getPhase(): number {
    return this.props.get("phase") ?? 0;
  }
  yaw(deg: number): this {
    // keep within the property's range while preserving continuity for smoothing
    let d = deg;
    while (d > 360) d -= 360;
    while (d < -360) d += 360;
    return this.set("yaw", Math.round(d * 10) / 10);
  }
  pitch(deg: number): this {
    return this.set("pitch", Math.round(Math.max(-90, Math.min(90, deg)) * 10) / 10);
  }
  size(s: number): this {
    return this.set("size", Math.round(Math.max(0, Math.min(64, s)) * 100) / 100);
  }
  length(l: number): this {
    return this.set("len", Math.round(Math.max(0, Math.min(128, l)) * 100) / 100);
  }
  variant(v: number): this {
    return this.set("variant", Math.max(0, Math.min(15, Math.round(v))));
  }
  pulse(): this {
    return this.set("aux", ((this.props.get("aux") ?? 0) + 1) % 250);
  }
  aux(n: number): this {
    return this.set("aux", Math.max(0, Math.min(255, Math.round(n))));
  }
  aim(dir: V3): this {
    const { yaw, pitch } = yawPitchOf(dir);
    return this.yaw(yaw).pitch(pitch);
  }

  /** Move the construct (no-op for sub-millimetre changes). */
  move(loc: V3): this {
    if (!this.entity.isValid) return this;
    if (dist2(loc, this.lastPos) < 1e-6) return this;
    this.lastPos = loc;
    try {
      this.entity.teleport(loc, { keepVelocity: false, checkForBlocks: false });
    } catch {
      /* target chunk unloaded: construct stays put */
    }
    return this;
  }

  /** Follow an entity with an offset; predicts one tick of velocity to hide server lag. */
  follow(target: Entity, offset: V3 = { x: 0, y: 0, z: 0 }, predict = 1): this {
    if (!target.isValid) return this;
    let p = add(target.location, offset);
    if (predict > 0) {
      try {
        const v = target.getVelocity();
        p = { x: p.x + v.x * predict, y: p.y + v.y * predict * 0.5, z: p.z + v.z * predict };
      } catch {
        /* velocity unavailable */
      }
    }
    return this.move(p);
  }

  /** Play the dissolve phase, then remove after `ticks`. Safe to call repeatedly. */
  dissolve(ticks = 12): void {
    if (this.dying) return;
    this.dying = true;
    if (!this.entity.isValid) {
      registry.delete(this.entity.id);
      return;
    }
    this.props.delete("phase");
    try {
      this.entity.setProperty("grimoire:phase", PHASE_DISSOLVE);
    } catch {
      /* ignore */
    }
    const ent = this.entity;
    system.runTimeout(() => removeEntity(ent), Math.max(1, ticks));
  }

  remove(): void {
    this.dying = true;
    removeEntity(this.entity);
  }
}

function removeEntity(e: Entity): void {
  registry.delete(e.id);
  try {
    if (e.isValid) e.remove();
  } catch {
    /* already gone */
  }
}

export function spawnFx(owner: Player | string, dim: Dimension, type: string, loc: V3, init: FxInit = {}): Fx | undefined {
  const ownerId = typeof owner === "string" ? owner : owner.id;
  let e: Entity;
  try {
    e = dim.spawnEntity(type, loc, { initialRotation: 0, initialPersistence: false });
  } catch (err) {
    log.debug(`spawn ${type} failed`, String(err));
    return undefined;
  }
  const fx = new Fx(e, type, ownerId, loc);
  try {
    e.setDynamicProperty(OWNER_PROP, ownerId);
    e.setDynamicProperty(SESSION_PROP, SESSION);
  } catch {
    /* ignore */
  }
  if (init.dir) fx.aim(init.dir);
  if (init.yaw !== undefined) fx.yaw(init.yaw);
  if (init.pitch !== undefined) fx.pitch(init.pitch);
  if (init.size !== undefined) fx.size(init.size);
  if (init.len !== undefined) fx.length(init.len);
  if (init.variant !== undefined) fx.variant(init.variant);
  if (init.aux !== undefined) fx.aux(init.aux);
  fx.phase(init.phase ?? 1);
  registry.set(e.id, fx);
  return fx;
}

export function fxCount(): number {
  return registry.size;
}

export function removeAllFxOf(ownerId: string): void {
  for (const fx of [...registry.values()]) if (fx.ownerId === ownerId) fx.dissolve(6);
}

/** Remove constructs left behind by an earlier script session (world reload / crash). */
export function isStaleConstruct(e: Entity): boolean {
  if (registry.has(e.id)) return false;
  try {
    return e.getDynamicProperty(SESSION_PROP) !== SESSION;
  } catch {
    return true;
  }
}

// ---------------------------------------------------------------------------------------------
// Particles, sounds and camera feedback
// ---------------------------------------------------------------------------------------------

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

export const COLORS = {
  orange: { r: 1.0, g: 0.55, b: 0.12 },
  gold: { r: 1.0, g: 0.78, b: 0.3 },
  copper: { r: 0.78, g: 0.42, b: 0.22 },
  white: { r: 1.0, g: 0.97, b: 0.9 },
  sapphire: { r: 0.12, g: 0.32, b: 0.85 },
  ice: { r: 0.62, g: 0.86, b: 1.0 },
  cyan: { r: 0.35, g: 0.95, b: 1.0 },
  silver: { r: 0.82, g: 0.87, b: 0.95 },
  crimson: { r: 0.78, g: 0.04, b: 0.12 },
  scarlet: { r: 1.0, g: 0.14, b: 0.12 },
  burgundy: { r: 0.42, g: 0.02, b: 0.08 },
  bloodglow: { r: 1.0, g: 0.22, b: 0.25 },
  redgold: { r: 1.0, g: 0.5, b: 0.25 },
} satisfies Record<string, Rgb>;

export interface ParticleVars {
  color?: Rgb;
  color2?: Rgb;
  size?: number;
  radius?: number;
  dir?: V3;
  speed?: number;
  count?: number;
  life?: number;
}

export function particle(dim: Dimension, id: string, at: V3, vars: ParticleVars = {}, onlyFor?: Player): void {
  const m = new MolangVariableMap();
  const c = vars.color ?? COLORS.white;
  m.setColorRGBA("variable.color", { red: c.r, green: c.g, blue: c.b, alpha: 1 });
  const c2 = vars.color2 ?? c;
  m.setColorRGBA("variable.color2", { red: c2.r, green: c2.g, blue: c2.b, alpha: 1 });
  m.setFloat("variable.size", vars.size ?? 1);
  m.setFloat("variable.radius", vars.radius ?? 1);
  m.setFloat("variable.count", vars.count ?? 1);
  m.setFloat("variable.life", vars.life ?? 1);
  const d = vars.dir ?? { x: 0, y: 1, z: 0 };
  m.setSpeedAndDirection("variable.dir", vars.speed ?? 1, d);
  try {
    if (onlyFor) onlyFor.spawnParticle(id, at, m);
    else dim.spawnParticle(id, at, m);
  } catch {
    /* unloaded chunk */
  }
}

export function sound(dim: Dimension, id: string, at: V3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
    /* ignore */
  }
}

/** Camera shake for players near a point (bounded radius and intensity). */
export function shake(dim: Dimension, at: V3, radius: number, intensity: number, seconds: number): void {
  if (!rules().cameraEffects) return;
  const players = dim.getPlayers({ location: at, maxDistance: radius });
  for (const p of players) {
    const d = Math.sqrt(dist2(p.location, at));
    const k = Math.max(0.05, Math.min(1, intensity * (1 - d / (radius * 1.2))));
    try {
      p.runCommand(`camerashake add @s ${k.toFixed(2)} ${seconds.toFixed(2)} positional`);
    } catch {
      /* ignore */
    }
  }
}

/** Short coloured screen flash for players near a point. */
export function flash(dim: Dimension, at: V3, radius: number, color: Rgb, hold = 0.1): void {
  if (!rules().cameraEffects) return;
  for (const p of dim.getPlayers({ location: at, maxDistance: radius })) {
    try {
      p.camera.fade({
        fadeColor: { red: color.r, green: color.g, blue: color.b },
        fadeTime: { fadeInTime: 0.05, holdTime: hold, fadeOutTime: 0.45 },
      });
    } catch {
      /* ignore */
    }
  }
}

export function allPlayers(): Player[] {
  return world.getAllPlayers();
}
