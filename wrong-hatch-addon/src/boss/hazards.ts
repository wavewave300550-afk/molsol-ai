/**
 * Persistent combat hazards that outlive the ability that created them:
 * expanding shockwave rings, rotten gas clouds, feather darts and lobbed eggs.
 * All of them are ticked from the main loop and cleaned up with their owner.
 */
import { Dimension, Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { DART_ID, DMG, LOBBED_EGG_ID } from "../config.js";
import { hit, targetsNear } from "../util/combat.js";
import { circle, particle, ring, sound } from "../util/fx.js";
import { add, dirYaw, dist, hdist, mul, norm, segDist, sub, v3 } from "../util/vec.js";

export interface Hazard {
  owner: string; // boss id (or player id for player darts)
  tick(now: number): boolean; // false = finished
  dispose(): void;
}

const hazards: Hazard[] = [];

export function addHazard(h: Hazard): void {
  hazards.push(h);
}

export function tickHazards(now: number): void {
  for (let i = hazards.length - 1; i >= 0; i--) {
    let alive = false;
    try {
      alive = hazards[i].tick(now);
    } catch (e) {
      console.warn(`[wrong_hatch] hazard error: ${e}`);
    }
    if (!alive) {
      try {
        hazards[i].dispose();
      } catch {
        // ignore
      }
      hazards.splice(i, 1);
    }
  }
}

export function clearHazards(owner: string): void {
  for (let i = hazards.length - 1; i >= 0; i--) {
    if (hazards[i].owner === owner) {
      try {
        hazards[i].dispose();
      } catch {
        // ignore
      }
      hazards.splice(i, 1);
    }
  }
}

export function hazardCount(): number {
  return hazards.length;
}

// --------------------------------------------------------------------------- shockwave ring

/** A ring that expands along the ground. Grounded players caught in the band are hit: jump to avoid it. */
export class ShockRing implements Hazard {
  private r: number;
  private hitIds = new Set<string>();
  constructor(
    readonly owner: string,
    private boss: Entity,
    private dim: Dimension,
    private center: Vector3,
    start: number,
    private end: number,
    private speed: number,
    private damage: number,
    private mul: number,
  ) {
    this.r = start;
  }
  tick(now: number): boolean {
    this.r += this.speed;
    if (this.r > this.end) return false;
    if (now % 2 === 0) circle(this.dim, this.center, this.r, "wh:ring_dust", 44, 0.15);
    for (const p of targetsNear(this.dim, this.center, this.r + 1.5)) {
      if (this.hitIds.has(p.id)) continue;
      const d = hdist(p.location, this.center);
      if (Math.abs(d - this.r) < 0.95 && Math.abs(p.location.y - this.center.y) < 1.8 && p.isOnGround) {
        this.hitIds.add(p.id);
        hit(this.boss, p, this.damage, this.mul, { from: this.center, knock: 0.7, lift: 0.55 });
        particle(this.dim, "wh:dust", p.location);
      }
    }
    return true;
  }
  dispose(): void {}
}

// --------------------------------------------------------------------------- rotten cloud

export class RotCloud implements Hazard {
  private age = 0;
  constructor(
    readonly owner: string,
    private dim: Dimension,
    private center: Vector3,
    private radius: number,
    private duration: number,
    private poisonAmp: number,
  ) {
    sound(dim, "wrong_hatch.crack", center, 1, 0.6);
  }
  tick(now: number): boolean {
    this.age++;
    if (this.age > this.duration) return false;
    if (this.age % 5 === 0) {
      const a = Math.random() * Math.PI * 2;
      const rr = Math.sqrt(Math.random()) * this.radius;
      particle(this.dim, "wh:rot_cloud", add(this.center, v3(Math.sin(a) * rr, 0.3, Math.cos(a) * rr)));
    }
    if (this.age % 10 === 0) {
      if (this.age % 40 === 0) ring(this.dim, this.center, this.radius, true);
      for (const p of targetsNear(this.dim, this.center, this.radius + 0.5)) {
        if (Math.abs(p.location.y - this.center.y) > 2.5) continue;
        try {
          p.addEffect("poison", 50, { amplifier: this.poisonAmp, showParticles: true });
          p.addEffect("nausea", 100, { amplifier: 0, showParticles: false });
        } catch {
          // ignore
        }
      }
    }
    return true;
  }
  dispose(): void {}
}

// --------------------------------------------------------------------------- feather darts

/** Script-driven feather dart: deterministic flight, block collision by raycast, hits along its segment. */
export class Dart implements Hazard {
  private age = 0;
  private ent: Entity | undefined;
  private pos: Vector3;
  private dir: Vector3;
  constructor(
    readonly owner: string,
    private shooter: Entity,
    private dim: Dimension,
    from: Vector3,
    dir: Vector3,
    private speed: number,
    private damage: number,
    private mul: number,
    private hostileToPlayers: boolean,
    private life = 40,
  ) {
    this.pos = from;
    this.dir = norm(dir);
    try {
      this.ent = dim.spawnEntity(DART_ID, from);
    } catch {
      this.ent = undefined;
    }
  }
  private victims(a: Vector3, b: Vector3): Entity[] {
    const mid = mul(add(a, b), 0.5);
    const r = this.speed / 2 + 2.5;
    if (this.hostileToPlayers) {
      return targetsNear(this.dim, mid, r).filter((p) => segDist(add(p.location, v3(0, 0.9, 0)), a, b) < 1.0);
    }
    let list: Entity[] = [];
    try {
      list = this.dim.getEntities({ location: mid, maxDistance: r + 3, excludeTypes: ["minecraft:player", "minecraft:item", DART_ID, LOBBED_EGG_ID], excludeFamilies: ["wrong_hatch_pet", "inanimate"] });
    } catch {
      list = [];
    }
    return list.filter((e) => {
      const isBoss = e.typeId === "wh:wrong_hatch";
      const c = add(e.location, v3(0, isBoss ? 2.4 : 0.6, 0));
      return segDist(c, a, b) < (isBoss ? 2.4 : 1.0);
    });
  }
  tick(): boolean {
    this.age++;
    if (this.age > this.life) return false;
    const next = add(this.pos, mul(this.dir, this.speed));
    let blocked = false;
    let end = next;
    try {
      const h = this.dim.getBlockFromRay(this.pos, this.dir, { maxDistance: this.speed, includePassableBlocks: false, includeLiquidBlocks: false });
      if (h) {
        blocked = true;
        end = add(h.block.location, h.faceLocation);
      }
    } catch {
      // outside world
    }
    const victims = this.victims(this.pos, end);
    if (victims.length) {
      const v = victims[0];
      hit(this.shooter, v, this.damage, this.mul, { cause: EntityDamageCause.projectile, from: this.pos, knock: 0.3, lift: 0.15 });
      particle(this.dim, "wh:feather_burst", v.location);
      return false;
    }
    if (blocked) {
      particle(this.dim, "wh:feather_fall", end);
      return false;
    }
    this.pos = next;
    if (this.ent && this.ent.isValid) {
      try {
        this.ent.teleport(next, { rotation: { x: -Math.asin(Math.max(-1, Math.min(1, this.dir.y))) * 57.3, y: dirYaw(this.dir) } });
      } catch {
        // ignore
      }
    }
    if (this.age % 3 === 0) particle(this.dim, "wh:gold_mote", next);
    return true;
  }
  dispose(): void {
    if (this.ent && this.ent.isValid) {
      try {
        this.ent.remove();
      } catch {
        // ignore
      }
    }
  }
}

// --------------------------------------------------------------------------- lobbed eggs

/** Egg lobbed along a parabola to a fixed landing point, with a ground telegraph at the landing spot. */
export class LobbedEgg implements Hazard {
  private age = 0;
  private ent: Entity | undefined;
  constructor(
    readonly owner: string,
    private boss: Entity,
    private dim: Dimension,
    private from: Vector3,
    private to: Vector3,
    private flight: number,
    private mul: number,
    private onLand: (at: Vector3) => void,
    private apex = 6,
  ) {
    try {
      this.ent = dim.spawnEntity(LOBBED_EGG_ID, from);
    } catch {
      this.ent = undefined;
    }
  }
  tick(): boolean {
    this.age++;
    const t = Math.min(1, this.age / this.flight);
    const p = add(add(this.from, mul(sub(this.to, this.from), t)), v3(0, 4 * this.apex * t * (1 - t), 0));
    if (this.age % 4 === 1) ring(this.dim, this.to, 1.6, true);
    if (this.ent && this.ent.isValid) {
      try {
        this.ent.teleport(p);
      } catch {
        // ignore
      }
    }
    if (t >= 1) {
      for (const pl of targetsNear(this.dim, this.to, 1.8)) {
        if (dist(pl.location, this.to) < 1.8) hit(this.boss, pl, DMG.eggImpact, this.mul, { from: this.to, knock: 0.4, lift: 0.3 });
      }
      particle(this.dim, "wh:shell_chip", this.to);
      sound(this.dim, "wrong_hatch.crack", this.to, 1, 1.2);
      try {
        this.onLand(this.to);
      } catch (e) {
        console.warn(`[wrong_hatch] egg landing failed: ${e}`);
      }
      return false;
    }
    return true;
  }
  dispose(): void {
    if (this.ent && this.ent.isValid) {
      try {
        this.ent.remove();
      } catch {
        // ignore
      }
    }
  }
}

export type { Player };
