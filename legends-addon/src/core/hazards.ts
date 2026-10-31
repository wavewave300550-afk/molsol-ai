/**
 * Script-driven props (models), projectiles, particle bullets and lingering
 * ground zones. Everything here is stepped once per tick from main.ts.
 */
import { Dimension, Entity, EntityDamageCause, MolangVariableMap, Player, Vector3 } from "@minecraft/server";
import { fightersNear, hurt, isFighter } from "./combat.js";
import { bullet, C, Col, deco, mote, spawn } from "./fx.js";
import { addTask } from "./tasks.js";
import { add, dist, len, norm, pitchOf, scale, sub, yawOf } from "./vec.js";
import { groundY } from "./terrain.js";

// ------------------------------------------------------------------ props

const props = new Set<Entity>();

export function spawnProp(dim: Dimension, type: string, at: Vector3, yaw = 0, owner?: Entity): Entity | undefined {
  try {
    const e = dim.spawnEntity(`legends:${type}`, at);
    try {
      e.setRotation({ x: 0, y: yaw });
    } catch {
      // rotation not applicable
    }
    if (owner) e.setDynamicProperty("legends:owner", owner.id);
    props.add(e);
    return e;
  } catch (err) {
    console.warn(`[legends] cannot spawn prop ${type}: ${err}`);
    return undefined;
  }
}

export function moveProp(e: Entity | undefined, p: Vector3, yaw?: number, pitch = 0): void {
  if (!e || !e.isValid) return;
  try {
    if (yaw === undefined) e.teleport(p);
    else e.teleport(p, { rotation: { x: pitch, y: yaw } });
  } catch {
    // chunk unloaded
  }
}

export function removeProp(e: Entity | undefined): void {
  if (!e) return;
  props.delete(e);
  try {
    if (e.isValid) e.remove();
  } catch {
    // already gone
  }
}

export function propAct(e: Entity | undefined, n: number): void {
  if (!e || !e.isValid) return;
  try {
    e.setProperty("legends:act", n);
  } catch {
    // ignore
  }
}

export function clearProps(ownerId?: string): void {
  for (const e of [...props]) {
    if (!e.isValid) {
      props.delete(e);
      continue;
    }
    if (ownerId === undefined || e.getDynamicProperty("legends:owner") === ownerId) removeProp(e);
  }
}

// ------------------------------------------------------------------ projectiles (model or particle)

export interface Shot {
  dim: Dimension;
  pos: Vector3;
  vel: Vector3; // blocks per tick
  life: number; // ticks
  radius: number;
  dmg: number;
  owner?: Entity;
  entity?: Entity; // optional model
  homing?: { target: Player; turn: number; until?: number };
  gravity?: number;
  ground?: boolean; // ends when it reaches the ground
  pierce?: boolean;
  col?: Col;
  trail?: (s: Shot) => void;
  onHit?: (p: Player, s: Shot) => void;
  onEnd?: (s: Shot) => void;
  cause?: EntityDamageCause;
  hit?: Set<string>;
  age?: number;
}

const shots: Shot[] = [];

export function fire(s: Shot): Shot {
  s.hit = new Set();
  s.age = 0;
  shots.push(s);
  return s;
}

export function stepShots(): void {
  for (let i = shots.length - 1; i >= 0; i--) {
    const s = shots[i];
    let done = false;
    try {
      done = stepShot(s);
    } catch (e) {
      console.warn(`[legends] projectile failed: ${e}`);
      done = true;
    }
    if (done) {
      shots.splice(i, 1);
      try {
        s.onEnd?.(s);
      } catch (e) {
        console.warn(`[legends] projectile end failed: ${e}`);
      }
      removeProp(s.entity);
    }
  }
}

function stepShot(s: Shot): boolean {
  s.age = (s.age ?? 0) + 1;
  if (s.homing && s.homing.target.isValid && (s.homing.until === undefined || s.age < s.homing.until)) {
    const tp = add(s.homing.target.location, { x: 0, y: 1, z: 0 });
    const want = norm(sub(tp, s.pos));
    const speed = len(s.vel);
    const cur = norm(s.vel);
    const nd = norm(add(cur, scale(sub(want, cur), s.homing.turn)));
    s.vel = scale(nd, speed);
  }
  if (s.gravity) s.vel = { x: s.vel.x, y: s.vel.y - s.gravity, z: s.vel.z };
  s.pos = add(s.pos, s.vel);
  s.life--;
  if (s.entity) moveProp(s.entity, s.pos, yawOf(s.vel), pitchOf(s.vel));
  s.trail?.(s);
  for (const p of fightersNear(s.dim, s.pos, s.radius + 1.5)) {
    if (s.hit!.has(p.id)) continue;
    const c = add(p.location, { x: 0, y: 0.9, z: 0 });
    if (dist(c, s.pos) <= s.radius + 0.5) {
      s.hit!.add(p.id);
      if (s.dmg > 0) hurt(p, s.dmg, s.owner, s.cause);
      s.onHit?.(p, s);
      if (!s.pierce) return true;
    }
  }
  if (s.ground) {
    const gy = groundY(s.dim, s.pos.x, s.pos.z, s.pos.y + 1, 2, 3);
    if (s.pos.y <= gy + 0.1) return true;
  }
  return s.life <= 0;
}

export function shotCount(): number {
  return shots.length;
}

/** A straight particle bullet; the hit test is analytic (cheap). */
export function particleBullet(dim: Dimension, from: Vector3, dir: Vector3, speed: number, ticks: number, dmg: number,
                               col: Col, owner?: Entity, size = 0.4, radius = 0.7, onHit?: (p: Player) => void): void {
  const d = norm(dir);
  bullet(dim, from, d, speed * 20, ticks, col, size);
  fire({ dim, pos: from, vel: scale(d, speed), life: ticks, radius, dmg, owner, col, onHit: onHit ? (p) => onHit(p) : undefined });
}

// ------------------------------------------------------------------ lingering zones

export interface ZoneOpts {
  dmg: number;
  every: number;
  col: Col;
  owner?: Entity;
  kind?: "venom" | "fire" | "acid" | "holy" | "frost";
  onTick?: (p: Player) => void;
  cause?: EntityDamageCause;
}

export function zone(dim: Dimension, center: Vector3, radius: number, ticks: number, o: ZoneOpts): void {
  const decoKind = o.kind === "fire" ? "flame" : o.kind === "holy" ? "rune" : o.kind === "frost" ? "shard" : "drip";
  addTask("zone", (age) => {
    if (age % 10 === 0) {
      spawn(dim, "legends:tele_ring", { x: center.x, y: center.y + 0.06, z: center.z }, ringVars(o.col, radius));
      deco(dim, decoKind, { x: center.x, y: center.y + 0.4, z: center.z }, o.col, Math.round(radius * 2), radius * 0.8, 0.3,
           o.kind === "fire" ? 0.6 : 0.4);
    }
    if (age % o.every === 0) {
      for (const p of fightersNear(dim, center, radius + 1)) {
        const l = p.location;
        if (Math.hypot(l.x - center.x, l.z - center.z) <= radius && Math.abs(l.y - center.y) < 2.5 && isFighter(p)) {
          if (o.dmg > 0) hurt(p, o.dmg, o.owner, o.cause ?? EntityDamageCause.magic);
          o.onTick?.(p);
        }
      }
    }
    return age < ticks;
  });
}

function ringVars(col: Col, r: number): MolangVariableMap {
  const m = new MolangVariableMap();
  m.setColorRGB("variable.color", col);
  m.setFloat("variable.size", r);
  m.setFloat("variable.life", 0.55);
  return m;
}

export function sparkle(dim: Dimension, at: Vector3): void {
  mote(dim, at, C.holy);
}
