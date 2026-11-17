import { Dimension, Entity, EntityDamageCause, Player, system, Vector3 } from "@minecraft/server";
import { CFG } from "../config.js";
import { ENT } from "../generated/ids.js";
import { clock, minions as registry, throttle } from "../registry.js";
import { COLORS, lineTelegraph, particle, ringTelegraph, shockwave, sound } from "../util/fx.js";
import {
  add, clamp, dist, distToSegment, flat, hdist, len, lerp, mul, norm, rand, sub, V3, yawOf,
} from "../util/vec.js";
import {
  areaVictims, blockedBetween, chest, Cover, groundY, hurt, isPlayer, knock, push, safeRemove, setProp,
} from "../util/world.js";
import type { Vesper } from "./controller.js";

export interface HurtResult {
  cancel: boolean;
  damage?: number;
}

export abstract class Minion {
  entity?: Entity;
  age = 0;
  dead = false;
  abstract readonly kind: string;

  /** Return false to be removed. */
  abstract update(v: Vesper): boolean;

  /** Called from the before-hurt event (restricted mode: no world mutation here). */
  hurt(_damage: number, _source: Entity | undefined, _cause: EntityDamageCause): HurtResult {
    return { cancel: true };
  }

  dispose(): void {
    if (this.entity) registry.delete(this.entity.id);
    safeRemove(this.entity);
    this.dead = true;
  }

  protected bind(e: Entity, owner: Vesper): void {
    this.entity = e;
    try {
      e.setDynamicProperty("sab:owner", owner.id);
    } catch {
      /* ignore */
    }
    registry.set(e.id, this);
  }

  protected move(to: V3, keep = false): void {
    try {
      if (this.entity?.isValid) this.entity.teleport(to, { keepVelocity: keep });
    } catch {
      /* ignore */
    }
  }
}

export class MinionSet {
  private list: Minion[] = [];

  add(m: Minion): void {
    this.list.push(m);
  }

  of<T extends Minion>(kind: string): T[] {
    return this.list.filter((m) => m.kind === kind && !m.dead) as T[];
  }

  tick(v: Vesper): void {
    const keep: Minion[] = [];
    for (const m of this.list) {
      if (m.dead) continue;
      let alive = false;
      try {
        if (m.entity && !m.entity.isValid) alive = false;
        else {
          m.age++;
          alive = m.update(v);
        }
      } catch (e) {
        console.warn(`[VESPER-0] minion ${m.kind} failed: ${e}`);
        alive = false;
      }
      if (alive) keep.push(m);
      else m.dispose();
    }
    this.list = keep;
  }

  clear(kind?: string): void {
    for (const m of this.list) if (!kind || m.kind === kind) m.dispose();
    this.list = this.list.filter((m) => !m.dead);
  }

  covers(): Cover[] {
    return this.of<Plate>("plate").filter((p) => p.entity?.isValid).map((p) => p.cover());
  }
}

function spawn(dim: Dimension, id: string, at: V3, event?: string, rotation?: number): Entity | undefined {
  try {
    return dim.spawnEntity(id, at, { spawnEvent: event, initialRotation: rotation });
  } catch {
    return undefined;
  }
}

// =====================================================================================================
// Choir of Satellites: Cherub drones + plasma orbs
// =====================================================================================================

export class Drone extends Minion {
  readonly kind = "drone";
  private target?: Player;
  private phaseOffset = Math.random() * 360;
  private nextShot: number;
  private charging = -1;
  private life: number;

  constructor(v: Vesper, at: V3, index: number) {
    super();
    const e = spawn(v.dim, ENT.cherub, at);
    if (e) this.bind(e, v);
    this.nextShot = 40 + index * 18;
    this.life = CFG.choir.life;
  }

  hurt(damage: number, source: Entity | undefined): HurtResult {
    if (source && source.typeId === ENT.cherub) return { cancel: true };
    return { cancel: false, damage };
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid) return false;
    if (this.age > this.life || v.dying) {
      particle(v.dim, "drone_launch", e.location);
      return false;
    }
    if (!this.target || !this.target.isValid || !v.players.includes(this.target)) {
      this.target = v.players.length ? v.players[Math.floor(Math.random() * v.players.length)] : undefined;
    }
    const tgt = this.target;
    const center = tgt ? tgt.location : v.arena;
    const ang = ((this.age * 2.2 + this.phaseOffset) * Math.PI) / 180;
    const goal = { x: center.x + Math.cos(ang) * 7, y: center.y + 4 + Math.sin(this.age / 15) * 0.8, z: center.z + Math.sin(ang) * 7 };
    const pos = e.location;
    const step = sub(goal, pos);
    const l = len(step);
    const next = l > 0.42 ? add(pos, mul(step, 0.42 / l)) : goal;
    this.move(next);
    if (tgt) setProp(e, "sab:heading", Math.round(yawOf(sub(tgt.location, pos))));
    // firing cycle: 14 tick telegraph (glow + whine) then shot
    if (tgt && this.charging < 0 && this.age >= this.nextShot) {
      this.charging = 0;
      sound(v.dim, "drone_charge", pos, 0.8, 1.0 + Math.random() * 0.2);
    }
    if (this.charging >= 0) {
      this.charging++;
      setProp(e, "sab:charge", Math.min(1, this.charging / 14));
      if (this.charging >= 14) {
        this.charging = -1;
        setProp(e, "sab:charge", 0);
        this.nextShot = this.age + CFG.choir.fireEvery + Math.floor(Math.random() * 20);
        if (tgt && tgt.isValid) {
          const muzzle = add(pos, { x: 0, y: 0.75, z: 0 });
          const dir = norm(sub(chest(tgt), muzzle));
          v.addMinion(new Orb(v, muzzle, dir, tgt));
          sound(v.dim, "plasma_fire", muzzle, 0.9);
        }
      }
    }
    return true;
  }
}

export class Orb extends Minion {
  readonly kind = "orb";
  private dir: V3;
  private speed = CFG.choir.orbSpeed;
  reflected = false;
  private by?: Entity;
  private target?: Player;

  constructor(v: Vesper, at: V3, dir: V3, target?: Player) {
    super();
    this.dir = dir;
    this.target = target;
    const e = spawn(v.dim, ENT.orb, at);
    if (e) this.bind(e, v);
  }

  hurt(_d: number, source: Entity | undefined, cause: EntityDamageCause): HurtResult {
    // parry: any player hit (melee or projectile) reflects the orb back at VESPER-0
    const attacker = source;
    if (!this.reflected && isPlayer(attacker) && (cause === EntityDamageCause.entityAttack || cause === EntityDamageCause.projectile)) {
      system.run(() => this.reflect(attacker));
    }
    return { cancel: true };
  }

  private reflect(by: Entity): void {
    const e = this.entity;
    if (!e || !e.isValid || this.reflected) return;
    this.reflected = true;
    this.by = by;
    this.speed = CFG.choir.reflectSpeed;
    setProp(e, "sab:reflected", true);
    sound(e.dimension, "parry", e.location, 1.0, 1.0);
    particle(e.dimension, "plasma_pop_gold", e.location);
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid) return false;
    if (this.age > CFG.choir.orbLife) {
      particle(v.dim, "plasma_pop", e.location);
      return false;
    }
    const pos = e.location;
    if (this.reflected) {
      // home on the nearest drone (if close) or on the boss heart
      let goal = v.core();
      let gd = dist(goal, pos);
      let drone: Drone | undefined;
      for (const d of v.minions.of<Drone>("drone")) {
        if (d.entity?.isValid) {
          const dd = dist(d.entity.location, pos);
          if (dd < gd && dd < 10) {
            goal = add(d.entity.location, { x: 0, y: 0.7, z: 0 });
            gd = dd;
            drone = d;
          }
        }
      }
      this.dir = norm(lerp(this.dir, norm(sub(goal, pos)), 0.35));
      if (gd < 2.6) {
        particle(v.dim, "holy_blast", pos);
        sound(v.dim, "parry", pos, 1.2, 0.7);
        if (drone && drone.entity?.isValid) {
          try {
            drone.entity.applyDamage(100, { cause: EntityDamageCause.projectile, damagingEntity: this.by });
          } catch {
            /* ignore */
          }
        } else {
          v.forwardDamage(CFG.choir.reflectDamage * v.groupScale(), this.by, EntityDamageCause.projectile);
        }
        return false;
      }
    } else if (this.target && this.target.isValid && this.age < 40) {
      const want = norm(sub(chest(this.target), pos));
      this.dir = norm(lerp(this.dir, want, 0.06));
    }
    const next = add(pos, mul(this.dir, this.speed));
    if (blockedBetween(v.dim, pos, next)) {
      particle(v.dim, "plasma_pop", pos);
      return false;
    }
    this.move(next);
    if (!this.reflected) {
      for (const p of v.players) {
        if (dist(chest(p), next) < 1.05) {
          hurt(p, CFG.choir.orbDamage, v.boss, EntityDamageCause.projectile);
          knock(p, next, 0.6, 0.25);
          particle(v.dim, "plasma_pop", next);
          return false;
        }
      }
    }
    return true;
  }
}

// =====================================================================================================
// Prayer censers
// =====================================================================================================

export class Censer extends Minion {
  readonly kind = "censer";
  private from: V3;
  private to: V3;
  destroyed = false;

  constructor(v: Vesper, from: V3, to: V3, dark: boolean) {
    super();
    this.from = from;
    this.to = to;
    const e = spawn(v.dim, ENT.censer, from);
    if (e) {
      this.bind(e, v);
      setProp(e, "sab:dark", dark);
      try {
        const h = e.getComponent("minecraft:health");
        h?.setCurrentValue(CFG.prayer.censerHealth);
      } catch {
        /* ignore */
      }
    }
  }

  hurt(damage: number, source: Entity | undefined, cause: EntityDamageCause): HurtResult {
    const playerCaused = isPlayer(source) || cause === EntityDamageCause.projectile;
    if (!playerCaused) return { cancel: true };
    const hp = this.entity?.getComponent("minecraft:health")?.currentValue ?? 0;
    if (damage >= hp) {
      system.run(() => this.shatter());
      return { cancel: true };
    }
    if (this.entity && throttle(`${this.entity.id}|ping`, clock.now, 4)) {
      const at = this.entity.location;
      const dim = this.entity.dimension;
      system.run(() => sound(dim, "censer", at, 0.6, 1.4));
    }
    return { cancel: false, damage };
  }

  shatter(): void {
    const e = this.entity;
    if (!e || !e.isValid || this.destroyed) return;
    this.destroyed = true;
    const at = add(e.location, { x: 0, y: 1.2, z: 0 });
    particle(e.dimension, "censer_break", at);
    sound(e.dimension, "censer_break", at, 1.4);
    this.dispose();
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid || this.destroyed) return false;
    if (this.age <= 40) {
      const t = this.age / 40;
      const p = lerp(this.from, this.to, t * t * (3 - 2 * t));
      p.y += Math.sin(t * Math.PI) * 4;
      this.move(p);
    } else if (this.age % 20 === 0) {
      particle(v.dim, "light_pillar", this.to, { height: 3, life: 0.9 }, v.phase >= 2 ? COLORS.violet : COLORS.gold);
    }
    if (this.age % 60 === 30) sound(v.dim, "censer", e.location, 0.5);
    return true;
  }
}

// =====================================================================================================
// Halo Seraphs (phase II ring weapons)
// =====================================================================================================

const SERAPH_RADIUS = [4.0, 3.0, 2.1];

export class Seraph extends Minion {
  readonly kind = "seraph";
  readonly ring: number;
  mode = 0; // 0 hover, 1 telegraph, 2 attack, 3 dormant
  private modeAge = 0;
  private path?: { from: V3; dir: V3; length: number; speed: number };
  private hitSet = new Set<string>();
  private next: number;
  dormantUntil = 0;
  guard?: V3;
  private tilt = 0;

  constructor(v: Vesper, ring: number, from: V3) {
    super();
    this.ring = ring;
    this.next = 60 + ring * 40;
    const e = spawn(v.dim, ENT.seraph, from);
    if (e) {
      this.bind(e, v);
      setProp(e, "sab:ring", ring);
      this.tilt = ring === 1 ? 90 : 0;
      setProp(e, "sab:tilt", this.tilt);
    }
  }

  get radius(): number {
    return SERAPH_RADIUS[this.ring];
  }

  hurt(damage: number, source: Entity | undefined): HurtResult {
    if (this.mode === 3) return { cancel: true };
    if (!isPlayer(source) && !(source && source.typeId === "minecraft:arrow")) {
      if (!source || source.typeId === ENT.seraph || source.typeId === ENT.boss) return { cancel: true };
    }
    const hp = this.entity?.getComponent("minecraft:health")?.currentValue ?? 0;
    if (damage >= hp - 0.5) {
      system.run(() => this.breakRing());
      return { cancel: false, damage: Math.max(0, hp - 1) };
    }
    return { cancel: false, damage };
  }

  breakRing(): void {
    const e = this.entity;
    if (!e || !e.isValid || this.mode === 3) return;
    this.setMode(3);
    this.dormantUntil = clock.now + CFG.seraph.dormant;
    particle(e.dimension, "seraph_break", add(e.location, { x: 0, y: 1, z: 0 }));
    sound(e.dimension, "censer_break", e.location, 1.2, 0.7);
  }

  private setMode(m: number): void {
    this.mode = m;
    this.modeAge = 0;
    if (this.entity) setProp(this.entity, "sab:mode", m);
  }

  private hubHeight(): number {
    return this.ring === 1 ? 0.6 : this.radius + 0.2;
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid) return false;
    if (v.dying) {
      this.breakRing();
      return this.age < 6000;
    }
    this.modeAge++;
    const pos = e.location;
    const gy = groundY(v.dim, pos.x, pos.z, v.ground, pos.y + 3);
    if (this.mode === 3) {
      // dormant: lie on the ground, then reboot with full health
      const rest = { x: pos.x, y: gy + 0.05, z: pos.z };
      this.move(lerp(pos, rest, 0.2));
      if (this.tilt !== 90) {
        this.tilt = Math.min(90, this.tilt + 9);
        setProp(e, "sab:tilt", this.tilt);
      }
      if (clock.now >= this.dormantUntil) {
        try {
          e.getComponent("minecraft:health")?.resetToMaxValue();
        } catch {
          /* ignore */
        }
        this.tilt = this.ring === 1 ? 90 : 0;
        setProp(e, "sab:tilt", this.tilt);
        sound(v.dim, "seraph_whine", pos, 1.0, 0.8);
        particle(v.dim, "ring_spark", add(pos, { x: 0, y: 1, z: 0 }));
        this.setMode(0);
        this.next = this.age + 60;
      }
      return true;
    }
    const tgt = v.target && v.target.isValid ? v.target : v.players[0];
    if (this.mode === 0) {
      // hover station: guard a censer during Requiem, otherwise flank the target
      let anchor: V3 = this.guard ?? (tgt ? tgt.location : v.arena);
      const ang = ((this.age * (this.guard ? 4 : 1.5) + this.ring * 120) * Math.PI) / 180;
      const r = this.guard ? 2.6 + this.radius : 7 + this.ring * 2;
      const goal = { x: anchor.x + Math.cos(ang) * r, y: 0, z: anchor.z + Math.sin(ang) * r };
      goal.y = groundY(v.dim, goal.x, goal.z, gy, pos.y + 4) + this.hubHeight() - 1;
      const d = sub(goal, pos);
      const l = len(d);
      this.move(l > 0.5 ? add(pos, mul(d, 0.5 / l)) : goal);
      if (tgt) this.face(yawOf(sub(tgt.location, pos)));
      if (this.guard) this.contact(v, 5);
      if (!this.guard && tgt && this.age >= this.next && !v.invulnerable) this.beginAttack(v, tgt);
      return true;
    }
    if (this.mode === 1) {
      if (this.modeAge === 1) sound(v.dim, "seraph_whine", pos, 1.1, 1.0 + this.ring * 0.15);
      const warn = this.ring === 2 ? 16 : this.ring === 1 ? 20 : 24;
      if (this.modeAge >= warn) this.setMode(2);
      return true;
    }
    // mode 2: attack along the locked path
    const path = this.path;
    if (!path) {
      this.setMode(0);
      return true;
    }
    const travelled = this.modeAge * path.speed;
    if (travelled > path.length) {
      this.setMode(0);
      this.next = this.age + (this.ring === 0 ? 180 : this.ring === 1 ? 140 : 100) - (v.enraged ? 30 : 0);
      return true;
    }
    const p = add(path.from, mul(path.dir, travelled));
    p.y = groundY(v.dim, p.x, p.z, gy, p.y + 4) + this.hubHeight() - 1;
    this.move(p);
    if (this.modeAge % 6 === 0) sound(v.dim, "seraph_slice", p, 0.7, 1 + this.ring * 0.1);
    this.strike(v, p, path.dir);
    return true;
  }

  private face(yaw: number): void {
    if (this.entity) setProp(this.entity, "sab:heading", Math.round(yaw));
  }

  private beginAttack(v: Vesper, tgt: Player): void {
    const pos = this.entity!.location;
    const tp = tgt.location;
    let dir = flat(sub(tp, pos));
    if (len(dir) < 0.1) dir = { x: 1, y: 0, z: 0 };
    const length = this.ring === 2 ? hdist(tp, pos) + 6 : 26;
    const speed = this.ring === 2 ? 1.15 : this.ring === 1 ? 0.8 : 0.7;
    this.path = { from: { ...pos }, dir, length, speed };
    this.hitSet.clear();
    this.face(yawOf(dir));
    const color = this.ring === 2 ? COLORS.red : COLORS.violet;
    lineTelegraph(v.dim, { x: pos.x, y: groundY(v.dim, pos.x, pos.z, v.ground, pos.y + 3), z: pos.z }, dir, length,
      this.ring === 2 ? 0.8 : 1.2, color);
    this.setMode(1);
  }

  private strike(v: Vesper, at: V3, dir: V3): void {
    const r = this.radius;
    for (const pl of v.players) {
      if (this.hitSet.has(pl.id)) continue;
      const feet = pl.location;
      let hit = false;
      if (this.ring === 1) {
        // flat saw at shin height: the rim band; jump to clear it
        const d = hdist(feet, at);
        hit = Math.abs(d - r) < 0.95 && feet.y < at.y + 0.55 && feet.y > at.y - 1.6;
      } else {
        // vertical wheel / chakram: thin disc along the travel direction
        const rel = sub(chest(pl), { x: at.x, y: at.y + 1, z: at.z });
        const side = Math.abs(rel.x * -dir.z + rel.z * dir.x);
        const inPlane = Math.hypot(rel.x * dir.x + rel.z * dir.z, rel.y);
        hit = side < 1.1 && inPlane < r + 0.6;
      }
      if (hit) {
        this.hitSet.add(pl.id);
        hurt(pl, this.ring === 0 ? 9 : this.ring === 1 ? 7 : 8, v.boss);
        knock(pl, at, 1.0, 0.4);
        particle(v.dim, "hull_spark", chest(pl));
      }
    }
  }

  private contact(v: Vesper, dmg: number): void {
    const e = this.entity!;
    for (const pl of v.players) {
      if (hdist(pl.location, e.location) < this.radius + 0.8 && Math.abs(pl.location.y - e.location.y) < 3 &&
        throttle(`${e.id}|${pl.id}`, clock.now, 20)) {
        hurt(pl, dmg, v.boss);
        knock(pl, e.location, 0.8, 0.3);
      }
    }
  }
}

// =====================================================================================================
// Fallen hull plates (cover from the Black Sun Nova / Benediction)
// =====================================================================================================

export class Plate extends Minion {
  readonly kind = "plate";
  private from: V3;
  private to: V3;
  private fall: number;
  landed = false;
  cracks = 0;

  constructor(v: Vesper, from: V3, to: V3, delay: number, existing?: Entity) {
    super();
    this.from = from;
    this.to = to;
    this.fall = 26;
    if (existing) {
      // re-adopted after a reload: already landed, keeps its cracks
      this.landed = true;
      const c = existing.getProperty("sab:cracks");
      this.cracks = typeof c === "number" ? c : 0;
      this.bind(existing, v);
      return;
    }
    this.age = -delay;
    const e = spawn(v.dim, ENT.plate, from, undefined, Math.random() * 360);
    if (e) this.bind(e, v);
    ringTelegraph(v.dim, to, 2.4, (delay + this.fall) / 20, COLORS.red);
  }

  cover(): Cover {
    return { location: this.entity!.location, radius: 1.7, height: 4.4 };
  }

  crack(): void {
    const e = this.entity;
    if (!e || !e.isValid) return;
    this.cracks++;
    setProp(e, "sab:cracks", Math.min(3, this.cracks));
    particle(e.dimension, "debris", add(e.location, { x: 0, y: 2, z: 0 }));
    if (this.cracks >= 3) {
      sound(e.dimension, "plate_impact", e.location, 1.0, 1.3);
      this.dispose();
    }
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid) return false;
    if (this.age < 0) {
      this.move(this.from);
      return true;
    }
    if (!this.landed) {
      const t = Math.min(1, this.age / this.fall);
      const p = lerp(this.from, this.to, t);
      p.y = this.from.y + (this.to.y - this.from.y) * t * t;
      this.move(p);
      if (t >= 1) {
        this.landed = true;
        sound(v.dim, "plate_impact", this.to, 1.4);
        particle(v.dim, "dust", this.to);
        particle(v.dim, "debris", add(this.to, { x: 0, y: 1, z: 0 }));
        for (const pl of v.players) {
          if (hdist(pl.location, this.to) < 2.6 && Math.abs(pl.location.y - this.to.y) < 3) {
            hurt(pl, CFG.transform.plateDamage, v.boss);
            knock(pl, this.to, 1.0, 0.45);
          }
        }
      }
    }
    return true;
  }
}

// =====================================================================================================
// Event Horizon singularity
// =====================================================================================================

export class Well extends Minion {
  readonly kind = "well";
  private center: V3;
  private warn: number;
  private active: number;
  private radius: number;

  constructor(v: Vesper, center: V3, radius = CFG.horizon.radius, warn = CFG.horizon.warn) {
    super();
    this.center = center;
    this.radius = radius;
    this.warn = warn;
    this.active = CFG.horizon.active;
    const e = spawn(v.dim, ENT.singularity, add(center, { x: 0, y: 1.0, z: 0 }));
    if (e) {
      this.bind(e, v);
      setProp(e, "sab:radius", radius);
      setProp(e, "sab:stage", 0);
    }
    ringTelegraph(v.dim, center, radius, warn / 20, COLORS.violet);
    particle(v.dim, "spiral_in", add(center, { x: 0, y: 0.2, z: 0 }), { radius, life: warn / 20 }, COLORS.violet);
    sound(v.dim, "horizon", center, 1.4);
  }

  update(v: Vesper): boolean {
    const e = this.entity;
    if (!e || !e.isValid) return false;
    const c = this.center;
    if (this.age === this.warn) {
      setProp(e, "sab:stage", 1);
      particle(v.dim, "spiral_in", add(c, { x: 0, y: 0.2, z: 0 }), { radius: this.radius, life: this.active / 20 }, COLORS.magenta);
    }
    if (this.age > this.warn && this.age < this.warn + this.active) {
      if (this.age % 4 === 0) {
        for (const ent of areaVictims(v.dim, c, this.radius)) {
          const d = hdist(ent.location, c);
          const s = 0.16 + 0.24 * (1 - d / this.radius);
          const dir = flat(sub(c, ent.location));
          push(ent, { x: dir.x * s, y: 0.04, z: dir.z * s });
        }
        try {
          for (const item of v.dim.getEntities({ location: c, maxDistance: this.radius, type: "minecraft:item" })) {
            const dir = norm(sub(c, item.location));
            item.applyImpulse(mul(dir, 0.12));
          }
        } catch {
          /* ignore */
        }
      }
      if (this.age % 10 === 0) {
        for (const pl of v.players) {
          if (hdist(pl.location, c) < CFG.horizon.crushRadius) hurt(pl, CFG.horizon.crushDamage, v.boss, EntityDamageCause.magic);
        }
      }
    }
    if (this.age === this.warn + this.active) {
      setProp(e, "sab:stage", 2);
      particle(v.dim, "implosion", add(c, { x: 0, y: 1, z: 0 }), { radius: 5, life: 0.4 }, COLORS.violet);
      sound(v.dim, "implode", c, 1.6);
    }
    if (this.age === this.warn + this.active + 8) {
      particle(v.dim, "nova_blast", add(c, { x: 0, y: 1, z: 0 }));
      shockwave(v.dim, add(c, { x: 0, y: 0.3, z: 0 }), 10, 0.6, COLORS.violet);
      for (const pl of v.players) {
        if (dist(chest(pl), add(c, { x: 0, y: 1, z: 0 })) < CFG.horizon.implodeRadius) {
          hurt(pl, CFG.horizon.implodeDamage, v.boss, EntityDamageCause.entityExplosion);
          knock(pl, c, 1.5, 0.7);
        }
      }
    }
    return this.age < this.warn + this.active + 16;
  }
}

// =====================================================================================================
// entity-less hazards: Halo Rite waves, Lance scorch, Hymn pulses, talon strikes
// =====================================================================================================

export class Wave extends Minion {
  readonly kind = "wave";
  private hit = new Set<string>();

  constructor(v: Vesper, private origin: V3, private high: boolean, private speed: number, private maxR: number,
    private damage: number, color = COLORS.gold) {
    super();
    const y = origin.y + (high ? 2.4 : 0.35);
    shockwave(v.dim, { x: origin.x, y, z: origin.z }, speed * 20, maxR / (speed * 20), color);
    if (high) shockwave(v.dim, { x: origin.x, y: y + 0.5, z: origin.z }, speed * 20, maxR / (speed * 20), color);
  }

  update(v: Vesper): boolean {
    const R = this.age * this.speed;
    for (const pl of v.players) {
      if (this.hit.has(pl.id)) continue;
      const d = hdist(pl.location, this.origin);
      if (Math.abs(d - R) > CFG.rite.band) continue;
      const feet = pl.location.y - this.origin.y;
      const struck = this.high ? feet + 1.8 > 1.95 && feet < 3.2 : feet < 0.8 && feet > -1.6;
      if (struck) {
        this.hit.add(pl.id);
        hurt(pl, this.damage, v.boss);
        knock(pl, this.origin, 0.9, 0.35);
        particle(v.dim, "hull_spark", chest(pl));
      }
    }
    return R < this.maxR;
  }
}

export class Scorch extends Minion {
  readonly kind = "scorch";

  constructor(v: Vesper, private at: V3, private life = 80) {
    super();
    particle(v.dim, "scorch", { x: at.x, y: at.y + 0.1, z: at.z }, { life: life / 20 });
  }

  update(v: Vesper): boolean {
    if (this.age % 10 === 0) {
      for (const pl of v.players) {
        if (hdist(pl.location, this.at) < 1.3 && Math.abs(pl.location.y - this.at.y) < 1.2) {
          hurt(pl, 2, v.boss, EntityDamageCause.fire);
          try {
            pl.setOnFire(2, true);
          } catch {
            /* ignore */
          }
        }
      }
    }
    return this.age < this.life;
  }
}

export class Strike extends Minion {
  readonly kind = "strike";

  constructor(v: Vesper, private at: V3, private warn: number, private radius: number, private damage: number) {
    super();
    ringTelegraph(v.dim, at, radius, warn / 20, COLORS.magenta);
  }

  update(v: Vesper): boolean {
    if (this.age === this.warn) {
      particle(v.dim, "dust", this.at);
      particle(v.dim, "heart_hit", add(this.at, { x: 0, y: 0.5, z: 0 }));
      sound(v.dim, "talon", this.at, 1.3, 0.9 + Math.random() * 0.2);
      for (const pl of v.players) {
        if (hdist(pl.location, this.at) < this.radius + 0.3 && Math.abs(pl.location.y - this.at.y) < 2.5) {
          hurt(pl, this.damage, v.boss);
          push(pl, { x: 0, y: 0.62, z: 0 });
        }
      }
      return false;
    }
    return true;
  }
}

/** Keeps a visual-only entity alive for `ticks`, then removes it. */
export class Expire extends Minion {
  readonly kind = "expire";

  constructor(e: Entity, private ticks: number) {
    super();
    this.entity = e;
  }

  update(): boolean {
    return this.age < this.ticks;
  }
}

export function clamp01(x: number): number {
  return clamp(x, 0, 1);
}

export function rndAround(c: V3, rmin: number, rmax: number): V3 {
  const a = Math.random() * Math.PI * 2;
  const r = rand(rmin, rmax);
  return { x: c.x + Math.cos(a) * r, y: c.y, z: c.z + Math.sin(a) * r };
}

export function segmentDist(p: V3, a: V3, b: V3): number {
  return distToSegment(p, a, b);
}

export type { Vector3 };
