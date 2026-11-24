/**
 * The Porcelain Emperor - boss controller.
 *
 * The entity has no data-driven AI. Every tick this controller steers it
 * through the sky of the Fractured Mandate, runs one skill at a time (each a
 * generator that yields once per tick, so its choreography reads top to
 * bottom), and mirrors its state to the client through entity properties
 * (phase -> damage texture, action -> animation, plates/claw -> missing parts,
 * bend/tilt -> how the serpentine body curves).
 *
 * "The more it breaks, the more dangerous it becomes": every phase adds
 * skills built from its own broken anatomy (tablets, claw, shards, rubble)
 * and shortens its pauses, while the porcelain itself gets easier to hurt.
 */
import { Entity, EntityHealthComponent, EntityHurtBeforeEvent, Player, system, Vector3 } from "@minecraft/server";
import { Arena } from "../arena/arena.js";
import { ACT, BOSS, DMG, ENT, FX, PROP, SND } from "../config.js";
import { breathPuff, crackDecal, GOLD, goldLine, IVORY, particle, ring, ringWave, sound, telegraph } from "../core/fx.js";
import {
  add, angleDiff, clamp, dirYaw, dist, distToSegment, distXZ, flat, len, lerp, norm, scale, sub, v, yawDir,
} from "../core/vec.js";
import * as F from "./fragments.js";

type Gen = Generator<void, void, void>;

export interface BossHooks {
  players(): Player[];
  hurt(p: Player, amount: number, from?: Vector3, push?: number, lift?: number): void;
  title(text: string, sub?: string, stay?: number): void;
  actionbar(text: string): void;
  onDefeated(): void;
  onPhase(phase: number): void;
}

interface Skill {
  name: string;
  phases: number[];
  weight: number[];
  cooldown: number;
  cond?: (b: Emperor) => boolean;
  run: (b: Emperor) => Gen;
}

const SKILLS: Skill[] = [
  { name: "procession", phases: [1, 2, 3], weight: [3, 2, 2], cooldown: 220, run: (b) => b.procession() },
  { name: "edict", phases: [1, 2, 3], weight: [3, 2, 2], cooldown: 260, cond: (b) => b.plates >= 2, run: (b) => b.edictBarrage() },
  { name: "breath", phases: [1, 2, 3], weight: [3, 2, 1], cooldown: 280, run: (b) => b.gildedBreath() },
  { name: "repair", phases: [1, 2], weight: [6, 6], cooldown: 520, cond: () => F.embeddedCount() >= 3, run: (b) => b.goldenRepair() },
  { name: "dive", phases: [2, 3], weight: [3, 2], cooldown: 280, run: (b) => b.shatterDive() },
  { name: "rubble", phases: [2, 3], weight: [3, 1], cooldown: 380, run: (b) => b.rubbleAscension() },
  { name: "claw", phases: [2, 3], weight: [2, 2], cooldown: 620, cond: (b) => !b.clawLost, run: (b) => b.severedClaw() },
  { name: "storm", phases: [3], weight: [3], cooldown: 520, run: (b) => b.shardStorm() },
  { name: "kowtow", phases: [3], weight: [3], cooldown: 900, run: (b) => b.kowtow() },
  { name: "rush", phases: [3], weight: [3], cooldown: 320, run: (b) => b.fragmentRush() },
];

const PLAYER_SCALE = [1, 1, 0.8, 0.67, 0.58, 0.5];

export class Emperor {
  readonly e: Entity;
  readonly A: Arena;
  readonly h: BossHooks;
  pos: Vector3;
  yaw: number;
  vel: Vector3 = v(0, 0, 0);
  phase = 1;
  plates: number = BOSS.plates;
  clawLost = false;
  clawEntity?: Entity;
  invulnerable = true;
  dying = false;
  battle = false;
  repairing = false;
  repairDamage = 0;
  vulnerableUntil = 0;
  tiltOverride?: number;
  readonly aggro = new Map<string, number>();
  readonly log: string[] = [];
  private gen?: Gen;
  private genName = "";
  private recent: string[] = [];
  private readonly cd = new Map<string, number>();
  private readonly props = new Map<string, number | boolean>();
  private prevYaw: number;
  private bendS = 0;
  private tiltS = 0;
  private breatherNext = false;
  private nextPlateAt = 0;
  private transitioning = false;
  private lastTarget = "";
  private t = 0;
  private fighters = 1;

  constructor(e: Entity, A: Arena, h: BossHooks, yaw: number) {
    this.e = e;
    this.A = A;
    this.h = h;
    this.pos = { ...e.location };
    this.yaw = yaw;
    this.prevYaw = yaw;
  }

  // ------------------------------------------------------------------ state helpers

  get health(): EntityHealthComponent | undefined {
    try {
      return this.e.getComponent("minecraft:health") as EntityHealthComponent | undefined;
    } catch {
      return undefined;
    }
  }
  get hp(): number {
    return this.health?.currentValue ?? 0;
  }
  get hpFrac(): number {
    return this.hp / BOSS.maxHp;
  }
  get vulnerable(): boolean {
    return system.currentTick < this.vulnerableUntil;
  }
  get skill(): string {
    return this.genName;
  }
  get valid(): boolean {
    return this.e.isValid;
  }

  setProp(id: string, value: number | boolean): void {
    if (this.props.get(id) === value) return;
    this.props.set(id, value);
    try {
      this.e.setProperty(id, value);
    } catch {
      // entity gone
    }
  }
  setAction(a: number): void {
    this.setProp(PROP.action, a);
  }
  setPlates(n: number): void {
    this.plates = clamp(n, 0, BOSS.plates);
    this.setProp(PROP.plates, this.plates);
  }

  dir(): Vector3 {
    return yawDir(this.yaw);
  }
  chest(): Vector3 {
    return add(this.pos, v(0, 1.9, 0));
  }
  mouth(): Vector3 {
    return add(add(this.pos, scale(this.dir(), 4.4)), v(0, 2.8, 0));
  }
  heart(): Vector3 {
    return add(add(this.pos, scale(this.dir(), 0.8)), v(0, 1.6, 0));
  }
  spine(i: number): Vector3 {
    return add(add(this.pos, scale(this.dir(), -(1.2 + i * 1.3))), v(0, 3.2, 0));
  }
  private note(s: string): void {
    this.log.push(`${system.currentTick}:${s}`);
    if (this.log.length > 200) this.log.shift();
  }

  // ------------------------------------------------------------------ movement

  steer(target: Vector3, maxSpeed: number, accel = 0.09): number {
    const to = sub(target, this.pos);
    const d = len(to);
    const want = Math.min(maxSpeed, d * 0.12 + 0.02);
    const desired = d > 1e-3 ? scale(to, want / d) : v(0, 0, 0);
    let dv = sub(desired, this.vel);
    const dl = len(dv);
    if (dl > accel) dv = scale(dv, accel / dl);
    this.vel = add(this.vel, dv);
    this.pos = add(this.pos, this.vel);
    return d;
  }
  brake(k = 0.85): void {
    this.vel = scale(this.vel, k);
    this.pos = add(this.pos, this.vel);
  }
  turnTo(yawTarget: number, rate: number): void {
    this.yaw += clamp(angleDiff(this.yaw, yawTarget), -rate, rate);
    if (this.yaw > 180) this.yaw -= 360;
    if (this.yaw <= -180) this.yaw += 360;
  }
  facePoint(p: Vector3, rate: number): void {
    const d = flat(sub(p, this.pos));
    if (len(d) > 0.05) this.turnTo(dirYaw(d), rate);
  }
  faceTravel(rate: number): void {
    if (len(flat(this.vel)) > 0.05) this.turnTo(dirYaw(this.vel), rate);
  }
  alt(h: number): number {
    return this.A.floorY + h;
  }

  *flyTo(target: Vector3, speed: number, maxTicks: number, face?: Vector3, near = 1.2): Gen {
    for (let t = 0; t < maxTicks; t++) {
      const d = this.steer(target, speed);
      if (face) this.facePoint(face, 6);
      else this.faceTravel(5);
      if (d < near) return;
      yield;
    }
  }

  *hover(ticks: number, face?: () => Vector3 | undefined): Gen {
    const base = { ...this.pos };
    for (let t = 0; t < ticks; t++) {
      this.steer(add(base, v(Math.sin(t * 0.05) * 1.5, Math.sin(t * 0.08) * 0.6, Math.cos(t * 0.05) * 1.5)), 0.15, 0.03);
      const f = face?.();
      if (f) this.facePoint(f, 4);
      yield;
    }
  }

  /** Mirror position/rotation to the entity and update the body-curve properties. */
  commit(): void {
    const c = this.A.center;
    const dx = this.pos.x - c.x;
    const dz = this.pos.z - c.z;
    const r = Math.hypot(dx, dz);
    if (r > 36) {
      this.pos.x = c.x + (dx / r) * 36;
      this.pos.z = c.z + (dz / r) * 36;
    }
    this.pos.y = clamp(this.pos.y, this.A.floorY - 2.5, this.A.floorY + 24);
    try {
      this.e.teleport(this.pos, { rotation: { x: 0, y: this.yaw }, keepVelocity: false, checkForBlocks: false });
    } catch {
      // unloaded
    }
    const dy = angleDiff(this.prevYaw, this.yaw);
    this.prevYaw = this.yaw;
    this.bendS += (clamp(dy / 6, -1, 1) - this.bendS) * 0.18;
    const tiltTarget = this.tiltOverride ?? clamp(this.vel.y / 0.5, -1, 1);
    this.tiltS += (tiltTarget - this.tiltS) * 0.2;
    const bend = Math.round(this.bendS * 20) / 20;
    const tilt = Math.round(this.tiltS * 20) / 20;
    this.setProp(PROP.bend, bend);
    this.setProp(PROP.tilt, tilt);
  }

  // ------------------------------------------------------------------ targets

  targets(): Player[] {
    return this.h.players();
  }

  pickTarget(): Player | undefined {
    const ps = this.targets();
    if (!ps.length) return undefined;
    let total = 0;
    const w = ps.map((p) => {
      let x = 1 + Math.min(4, (this.aggro.get(p.id) ?? 0) * 0.04);
      if (p.id === this.lastTarget && ps.length > 1) x *= 0.5;
      total += x;
      return x;
    });
    let r = Math.random() * total;
    for (let i = 0; i < ps.length; i++) {
      r -= w[i];
      if (r <= 0) {
        this.lastTarget = ps[i].id;
        return ps[i];
      }
    }
    return ps[ps.length - 1];
  }

  nearest(from: Vector3): Player | undefined {
    let best: Player | undefined;
    let bd = Infinity;
    for (const p of this.targets()) {
      const d = dist(p.location, from);
      if (d < bd) {
        bd = d;
        best = p;
      }
    }
    return best;
  }

  private hurtSafe(p: Player, amount: number, from?: Vector3, push = 0.8, lift = 0.3): void {
    this.h.hurt(p, amount, from, push, lift);
  }

  // ------------------------------------------------------------------ damage rules (called from world.beforeEvents.entityHurt)

  onHurtBefore(ev: EntityHurtBeforeEvent): void {
    const src = ev.damageSource.damagingEntity;
    if (src && src.typeId.startsWith("porcelain:")) {
      ev.cancel = true;
      return;
    }
    if (this.invulnerable || this.dying) {
      ev.cancel = true;
      return;
    }
    const n = Math.max(1, Math.min(5, this.fighters));
    let mult = BOSS.phaseArmor[this.phase] * PLAYER_SCALE[n];
    if (this.vulnerable) mult *= BOSS.vulnerableMult;
    if (this.repairing) mult *= 1.5;
    let dmg = ev.damage * mult;
    const hp = this.hp;
    if (hp - dmg < 1) {
      dmg = Math.max(0, hp - 1);
      system.run(() => this.beginDeath());
    }
    ev.damage = dmg;
    const sid = src?.id;
    system.run(() => this.afterHurt(dmg, sid));
  }

  private afterHurt(dmg: number, sourceId?: string): void {
    if (sourceId) this.aggro.set(sourceId, (this.aggro.get(sourceId) ?? 0) + dmg);
    if (this.repairing) this.repairDamage += dmg;
    if (this.vulnerable && this.valid) particle(this.A.dim, FX.goldBurst, this.heart());
  }

  /** Damage that bypasses the hurt pipeline (severed claw mirroring, broken claw). */
  dealDirect(amount: number): void {
    const h = this.health;
    if (!h || this.invulnerable || this.dying) return;
    const next = h.currentValue - amount;
    if (next < 1) {
      h.setCurrentValue(1);
      this.beginDeath();
      return;
    }
    h.setCurrentValue(next);
  }

  private heal(amount: number): void {
    const h = this.health;
    if (!h || this.dying) return;
    h.setCurrentValue(Math.min(BOSS.maxHp, h.currentValue + amount));
  }

  // ------------------------------------------------------------------ main loop

  tick(): void {
    if (!this.valid) return;
    this.t++;
    this.fighters = this.targets().length;
    if (this.battle && !this.dying && !this.transitioning) {
      const f = this.hpFrac;
      const want = f <= BOSS.phase3At ? 3 : f <= BOSS.phase2At ? 2 : 1;
      if (want > this.phase) {
        this.interrupt();
        this.run(`phase${this.phase + 1}`, this.transition(this.phase + 1));
      }
      if (!this.targets().length && this.t % 20 === 0) this.heal(BOSS.maxHp * 0.002);
      if (system.currentTick >= this.nextPlateAt && this.plates < BOSS.plates) {
        if (this.nextPlateAt > 0) this.setPlates(this.plates + 1);
        this.nextPlateAt = system.currentTick + (this.phase >= 3 ? 240 : 400);
      }
    }
    if (!this.gen && this.battle && !this.dying) this.chooseNext();
    if (this.gen) {
      let done = true;
      try {
        done = !!this.gen.next().done;
      } catch (e) {
        console.warn(`[porcelain] skill ${this.genName} failed: ${e}`);
        done = true;
      }
      if (done) {
        this.gen = undefined;
        this.note(`end ${this.genName}`);
        this.genName = "";
      }
    }
    if (this.valid) this.commit();
  }

  run(name: string, g: Gen): void {
    this.gen = g;
    this.genName = name;
    this.note(`start ${name}`);
  }

  interrupt(): void {
    if (this.gen) {
      try {
        this.gen.return();
      } catch {
        // ignore
      }
      this.note(`interrupt ${this.genName}`);
    }
    this.gen = undefined;
    this.genName = "";
  }

  private chooseNext(): void {
    if (!this.targets().length) {
      this.run("idle", this.idleHover(40));
      return;
    }
    if (this.breatherNext) {
      this.breatherNext = false;
      this.run("breather", this.breather());
      return;
    }
    const now = system.currentTick;
    const ok = SKILLS.filter((s) => s.phases.includes(this.phase) && (this.cd.get(s.name) ?? 0) <= now && (!s.cond || s.cond(this)) && s.name !== this.recent[0]);
    const pool = ok.length ? ok : SKILLS.filter((s) => s.phases.includes(this.phase) && (!s.cond || s.cond(this)) && s.name !== this.recent[0]);
    let total = 0;
    const weights = pool.map((s) => {
      const w = s.weight[s.phases.indexOf(this.phase)];
      total += w;
      return w;
    });
    let r = Math.random() * total;
    let chosen = pool[0];
    for (let i = 0; i < pool.length; i++) {
      r -= weights[i];
      if (r <= 0) {
        chosen = pool[i];
        break;
      }
    }
    this.cd.set(chosen.name, now + chosen.cooldown);
    this.recent.unshift(chosen.name);
    this.recent.length = Math.min(this.recent.length, 3);
    this.breatherNext = true;
    this.run(chosen.name, chosen.run(this));
  }

  /** Force a specific skill next (testing commands and the opening move). */
  forceSkill(name: string): boolean {
    const s = SKILLS.find((k) => k.name === name);
    if (!s || this.dying || this.transitioning || !this.battle) return false;
    this.interrupt();
    this.cd.set(s.name, system.currentTick + s.cooldown);
    this.recent.unshift(s.name);
    this.breatherNext = true;
    this.run(s.name, s.run(this));
    return true;
  }

  // ------------------------------------------------------------------ pauses

  *idleHover(ticks: number): Gen {
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(this.A.center.x, this.alt(9), this.A.center.z), 0.35, ticks);
  }

  *breather(): Gen {
    this.setAction(ACT.IDLE);
    this.tiltOverride = undefined;
    const ticks = this.phase === 1 ? 34 : this.phase === 2 ? 24 : 14;
    const ang = Math.random() * Math.PI * 2;
    const r = 12 + Math.random() * 6;
    const c = this.A.center;
    const p = v(c.x + Math.cos(ang) * r, this.alt(7 + Math.random() * 3), c.z + Math.sin(ang) * r);
    for (let t = 0; t < ticks; t++) {
      this.steer(p, 0.45, 0.05);
      const tgt = this.nearest(this.pos);
      if (tgt) this.facePoint(tgt.location, 5);
      else this.faceTravel(4);
      yield;
    }
  }

  *stagger(ticks: number, low = true): Gen {
    this.setAction(ACT.STAGGER);
    this.vulnerableUntil = system.currentTick + ticks;
    this.tiltOverride = -0.4;
    this.h.actionbar("§c§lThe Emperor is exposed!§r §7- strike the open heart");
    const down = v(this.pos.x, low ? this.alt(-0.2) : this.pos.y, this.pos.z);
    try {
      for (let t = 0; t < ticks; t++) {
        this.steer(down, 0.25, 0.05);
        if (t % 6 === 0) particle(this.A.dim, FX.redMote, add(this.heart(), v(Math.random() - 0.5, Math.random(), Math.random() - 0.5)));
        if (t % 20 === 0) particle(this.A.dim, FX.goldBurst, this.heart());
        yield;
      }
    } finally {
      this.tiltOverride = undefined;
      this.setAction(ACT.IDLE);
    }
  }

  // ------------------------------------------------------------------ skill: Imperial Procession

  *procession(): Gen {
    const passes = this.phase;
    for (let pass = 0; pass < passes; pass++) {
      const target = this.pickTarget();
      if (!target) return;
      const c = this.A.center;
      let d = flat(sub(target.location, this.pos));
      if (len(d) < 3) d = yawDir(Math.random() * 360);
      d = norm(d);
      const y = this.alt(-0.4);
      const tp = target.location;
      const start = v(tp.x - d.x * 26, y, tp.z - d.z * 26);
      const end = v(tp.x + d.x * 26, y, tp.z + d.z * 26);
      // keep the lane over (or just beyond) the court
      for (const p of [start, end]) {
        const r = distXZ(p, c);
        if (r > 32) {
          p.x = c.x + ((p.x - c.x) / r) * 32;
          p.z = c.z + ((p.z - c.z) / r) * 32;
        }
      }
      this.setAction(ACT.IDLE);
      yield* this.flyTo(add(start, v(0, 4, 0)), 0.9, 70);
      // telegraph the lane: imperial banners of light along the procession route
      this.setAction(ACT.PROCESSION);
      const lane = sub(end, start);
      const L = len(lane);
      const ld = norm(lane);
      const windup = this.phase === 1 ? 34 : this.phase === 2 ? 26 : 20;
      for (let s = 2; s < L; s += 3.2) telegraph(this.A.dim, v(start.x + ld.x * s, this.A.floorY, start.z + ld.z * s), 2.2, windup / 20 + 0.6);
      sound(this.A.dim, SND.gong, this.A.center, 1.6, 1.0);
      for (let t = 0; t < windup; t++) {
        this.steer(start, 0.4, 0.06);
        this.turnTo(dirYaw(ld), 9);
        yield;
      }
      // the sweep
      const hit = new Set<string>();
      const speed = this.phase >= 3 ? 1.35 : 1.15;
      this.vel = scale(ld, speed);
      for (let t = 0; t < Math.ceil(L / speed) + 6; t++) {
        this.pos = add(this.pos, this.vel);
        this.pos.y += (y - this.pos.y) * 0.3;
        this.turnTo(dirYaw(ld), 6);
        const head = add(this.chest(), scale(ld, 4));
        const tail = add(this.chest(), scale(ld, -12));
        for (const p of this.targets()) {
          if (hit.has(p.id)) continue;
          if (distToSegment(add(p.location, v(0, 0.9, 0)), head, tail) < 2.1) {
            hit.add(p.id);
            this.hurtSafe(p, DMG.procession, this.chest(), 1.4, 0.45);
          }
        }
        if (t % 2 === 0) particle(this.A.dim, FX.goldMote, tail);
        yield;
      }
      this.vel = scale(ld, 0.4);
      this.setAction(ACT.IDLE);
      for (let t = 0; t < 10; t++) {
        this.brake(0.85);
        yield;
      }
    }
  }

  // ------------------------------------------------------------------ skill: Edict Barrage

  *edictBarrage(): Gen {
    const c = this.A.center;
    const ang = Math.random() * Math.PI * 2;
    const spot = v(c.x + Math.cos(ang) * 10, this.alt(11), c.z + Math.sin(ang) * 10);
    this.setAction(ACT.IDLE);
    yield* this.flyTo(spot, 0.7, 60, c);
    this.setAction(ACT.EDICT);
    sound(this.A.dim, SND.chimeLow, this.pos, 1.4, 0.8);
    for (let t = 0; t < 20; t++) {
      this.brake(0.8);
      const tgt = this.nearest(this.pos);
      if (tgt) this.facePoint(tgt.location, 5);
      if (t % 4 === 0) for (let i = 0; i < this.plates; i++) particle(this.A.dim, FX.goldMote, this.spine(i));
      yield;
    }
    const count = Math.min(this.plates, this.phase === 1 ? 3 : this.phase === 2 ? 4 : 6);
    const gapT = this.phase >= 3 ? 6 : 8;
    for (let i = 0; i < count; i++) {
      const tgt = this.pickTarget();
      if (!tgt) break;
      const flight = 22;
      let aim = tgt.location;
      try {
        const vel = tgt.getVelocity();
        aim = add(aim, scale(v(vel.x, 0, vel.z), flight * 0.6));
      } catch {
        // ignore
      }
      aim = v(Math.floor(aim.x) + 0.5, this.A.floorY, Math.floor(aim.z) + 0.5);
      F.launchTablet(this.spine(this.plates - 1), aim, flight, 6);
      this.setPlates(this.plates - 1);
      sound(this.A.dim, SND.chime, this.pos, 1.2, 0.7 + i * 0.12);
      for (let t = 0; t < gapT; t++) {
        this.brake(0.8);
        this.facePoint(tgt.location, 4);
        yield;
      }
    }
    for (let t = 0; t < 18; t++) {
      this.brake(0.85);
      yield;
    }
    this.setAction(ACT.IDLE);
  }

  // ------------------------------------------------------------------ skill: Gilded Breath

  *gildedBreath(): Gen {
    const target = this.pickTarget();
    if (!target) return;
    this.setAction(ACT.IDLE);
    for (let t = 0; t < 70; t++) {
      const tp = target.location;
      const away = norm(flat(sub(this.pos, tp)));
      const spot = v(tp.x + away.x * 9, this.alt(1.6), tp.z + away.z * 9);
      const d = this.steer(spot, 0.75);
      this.facePoint(tp, 6);
      if (d < 2) break;
      yield;
    }
    this.setAction(ACT.BREATH);
    const aimYaw = dirYaw(flat(sub(target.location, this.pos)));
    // wind-up: the head rears back, the throat fills with molten gold; the cone is marked on the floor
    for (let t = 0; t < 18; t++) {
      this.brake(0.7);
      this.turnTo(aimYaw, 8);
      if (t === 0) {
        const fwd = yawDir(aimYaw);
        for (let k = 1; k <= 4; k++) {
          const at = add(this.pos, scale(fwd, 3 + k * 2.8));
          telegraph(this.A.dim, v(at.x, this.A.floorY, at.z), 1.2 + k * 0.9, 1.5, GOLD);
        }
      }
      if (t % 3 === 0) particle(this.A.dim, FX.goldMote, this.mouth());
      yield;
    }
    const sweep = this.phase >= 3 ? 30 : 20;
    const ticks = 34;
    const cosLimit = Math.cos((22 * Math.PI) / 180);
    for (let t = 0; t < ticks; t++) {
      this.brake(0.7);
      const yaw = aimYaw - sweep + (2 * sweep * t) / ticks;
      this.turnTo(yaw, 6);
      const fwd = yawDir(this.yaw);
      const d3 = norm(v(fwd.x, -0.38, fwd.z));
      const m = this.mouth();
      breathPuff(this.A.dim, m, d3, 11);
      if (t % 2 === 0) breathPuff(this.A.dim, add(m, scale(d3, 2)), d3, 8);
      if (t % 4 === 0) {
        for (const p of this.targets()) {
          const to = sub(add(p.location, v(0, 0.9, 0)), m);
          const dl = len(to);
          if (dl < 14 && dl > 0.1) {
            const cos = (to.x * d3.x + to.y * d3.y + to.z * d3.z) / dl;
            if (cos > cosLimit) {
              this.hurtSafe(p, DMG.breathTick, m, 0.25, 0.05);
              try {
                p.addEffect("slowness", 50, { amplifier: 1, showParticles: true });
              } catch {
                // ignore
              }
            }
          }
        }
      }
      if (t % 3 === 0) {
        const s = 3 + Math.random() * 9;
        const side = (Math.random() - 0.5) * s * 0.7;
        const at = add(add(this.pos, scale(fwd, s)), scale(yawDir(this.yaw + 90), side));
        const l = this.A.local(at);
        this.A.gild(l.x, l.z, 300);
      }
      if (t % 8 === 0) sound(this.A.dim, SND.hum, m, 0.8, 1.6);
      yield;
    }
    for (let t = 0; t < 10; t++) {
      this.brake(0.8);
      yield;
    }
    this.setAction(ACT.IDLE);
  }

  // ------------------------------------------------------------------ skill: Golden Repair (kintsugi)

  *goldenRepair(): Gen {
    const c = this.A.center;
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(c.x, this.alt(6), c.z), 0.8, 60);
    this.setAction(ACT.REPAIR);
    this.repairing = true;
    this.repairDamage = 0;
    this.h.title("§6Golden Repair", "§eShatter the embedded shards - or break the Emperor's focus!", 50);
    sound(this.A.dim, SND.hum, this.pos, 1.5, 0.8);
    const threshold = BOSS.maxHp * BOSS.repairInterruptFraction;
    let interrupted = false;
    try {
      for (let t = 0; t < 80; t++) {
        this.brake(0.8);
        if (t % 3 === 0) for (const f of F.embedded()) goldLine(this.A.dim, add(f.pos, v(0, 0.8, 0)), this.heart(), 1.1);
        if (t % 20 === 0) sound(this.A.dim, SND.hum, this.pos, 1.0, 0.9 + t / 200);
        if (this.repairDamage >= threshold) {
          interrupted = true;
          break;
        }
        yield;
      }
    } finally {
      this.repairing = false;
    }
    if (interrupted) {
      this.h.title("§cThe repair falters!", "§7The Emperor's heart lies open", 40);
      sound(this.A.dim, SND.shatter, this.pos, 1.5, 1.2);
      particle(this.A.dim, FX.chipBurst, this.heart());
      yield* this.stagger(110);
      return;
    }
    let returned = 0;
    F.pullAll((f) => {
      returned++;
      this.heal(BOSS.maxHp * BOSS.repairHealPerShard);
      if (f.kind === "tablet") this.setPlates(this.plates + 1);
      sound(this.A.dim, SND.chime, this.heart(), 1.0, 1.4);
    });
    for (let t = 0; t < 20; t++) {
      this.brake(0.8);
      yield;
    }
    if (returned) this.h.actionbar(`§6The Emperor reclaimed ${returned} shard${returned === 1 ? "" : "s"}`);
    this.setAction(ACT.IDLE);
  }

  // ------------------------------------------------------------------ skill: Shatter Dive

  *shatterDive(): Gen {
    const target = this.pickTarget();
    if (!target) return;
    this.setAction(ACT.IDLE);
    yield* this.flyTo(add(target.location, v(0, 16, 0)), 0.9, 45, target.location, 2);
    this.setAction(ACT.DIVE);
    let aim = v(target.location.x, this.A.floorY, target.location.z);
    for (let t = 0; t < 30; t++) {
      aim = v(target.location.x, this.A.floorY, target.location.z);
      this.steer(add(aim, v(0, 15, 0)), 0.5);
      this.facePoint(aim, 6);
      if (t % 10 === 0) telegraph(this.A.dim, aim, 4.5, 0.6, RED_SEAL);
      yield;
    }
    sound(this.A.dim, SND.stamp, aim, 1.6, 0.9);
    telegraph(this.A.dim, aim, 5.6, 0.9, RED_SEAL);
    for (let t = 0; t < 12; t++) {
      this.brake(0.7);
      this.facePoint(aim, 8);
      yield;
    }
    this.tiltOverride = -1;
    const from = { ...this.pos };
    const to = v(aim.x - this.dir().x * 2.5, this.A.floorY - 1.2, aim.z - this.dir().z * 2.5);
    for (let t = 1; t <= 8; t++) {
      this.pos = lerp(from, to, (t / 8) * (t / 8));
      this.vel = v(0, 0, 0);
      yield;
    }
    // impact
    this.tiltOverride = undefined;
    for (const p of this.targets()) {
      const d = distXZ(p.location, aim);
      if (d <= 2.5 && Math.abs(p.location.y - aim.y) < 3) this.hurtSafe(p, DMG.diveCenter, aim, 1.6, 0.7);
      else if (d <= 5.5 && Math.abs(p.location.y - aim.y) < 3) this.hurtSafe(p, DMG.diveEdge, aim, 1.1, 0.45);
    }
    ringWave(this.A.dim, aim, 6);
    crackDecal(this.A.dim, aim, 7, 8);
    sound(this.A.dim, SND.shatter, aim, 1.8, 0.8);
    particle(this.A.dim, FX.chipBurst, aim);
    particle(this.A.dim, FX.dust, aim);
    const l = this.A.local(aim);
    for (const [dx, dz] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (Math.random() < (dx === 0 && dz === 0 ? 1 : 0.6)) this.A.punchHole(l.x + dx, l.z + dz, 260);
    }
    const n = this.phase >= 3 ? 8 : 6;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + Math.random() * 0.3;
      F.slideShard(add(aim, v(Math.cos(a) * 1.8, 0.2, Math.sin(a) * 1.8)), v(Math.cos(a), 0, Math.sin(a)), 0.55 + Math.random() * 0.2);
    }
    yield* this.stagger(this.phase >= 3 ? 50 : 70, false);
    yield* this.flyTo(v(this.pos.x, this.alt(8), this.pos.z), 0.6, 30);
  }

  // ------------------------------------------------------------------ skill: Rubble Ascension

  *rubbleAscension(): Gen {
    const c = this.A.center;
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(c.x, this.alt(10), c.z), 0.7, 50);
    this.setAction(ACT.RUBBLE);
    this.h.actionbar("§6The palace obeys its Emperor...");
    const k = this.phase >= 3 ? 6 : 4;
    const rubble: F.Frag[] = [];
    for (let i = 0; i < k; i++) {
      const players = this.targets();
      let cell: { x: number; z: number } | undefined;
      for (let tries = 0; tries < 8 && !cell; tries++) {
        const cand = this.A.randomFloorCell();
        if (cand && players.every((p) => distXZ(p.location, this.A.standAt(cand.x, cand.z)) > 3)) cell = cand;
      }
      if (!cell) continue;
      const at = this.A.w(cell.x + 0.5, 0, cell.z + 0.5);
      this.A.punchHole(cell.x, cell.z, 360);
      particle(this.A.dim, FX.dust, at);
      sound(this.A.dim, SND.crack, at, 1.0, 0.7);
      const f = F.raiseRubble(at, 6.5, 6 + i * 0.6, (i / k) * Math.PI * 2);
      if (f) rubble.push(f);
      yield;
      yield;
    }
    for (let t = 0; t < 40; t++) {
      this.brake(0.85);
      yield;
    }
    for (const f of rubble) {
      if (!f.e.isValid) continue;
      const tgt = this.pickTarget();
      if (!tgt) break;
      const aim = v(tgt.location.x, this.A.floorY + 0.5, tgt.location.z);
      telegraph(this.A.dim, v(aim.x, this.A.floorY, aim.z), 2.0, 0.9, RED_SEAL);
      for (let t = 0; t < 14; t++) {
        if (t % 2 === 0) particle(this.A.dim, FX.redMote, f.pos);
        this.facePoint(tgt.location, 4);
        yield;
      }
      if (!f.e.isValid) continue;
      F.hurl(f, add(tgt.location, v(0, 0.6, 0)), 1.05);
      sound(this.A.dim, SND.crack, f.pos, 1.0, 1.3);
      for (let t = 0; t < (this.phase >= 3 ? 6 : 9); t++) yield;
    }
    for (let t = 0; t < 16; t++) {
      this.brake(0.85);
      yield;
    }
    this.setAction(ACT.IDLE);
  }

  // ------------------------------------------------------------------ skill: Severed Claw

  *severedClaw(): Gen {
    this.setAction(ACT.CLAW);
    for (let t = 0; t < 10; t++) {
      this.brake(0.8);
      yield;
    }
    const right = yawDir(this.yaw + 90);
    const at = add(add(this.pos, scale(right, 1.8)), add(scale(this.dir(), 1.2), v(0, 1.2, 0)));
    let claw: Entity | undefined;
    try {
      claw = this.A.dim.spawnEntity(ENT.claw, at);
    } catch {
      return;
    }
    this.clawEntity = claw;
    this.setProp(PROP.claw, 1);
    particle(this.A.dim, FX.goldBurst, at);
    sound(this.A.dim, SND.crack, at, 1.3, 0.6);
    let cpos = { ...at };
    let broken = false;
    const slashes = this.phase >= 3 ? 4 : 3;
    const place = (): void => {
      try {
        if (claw && claw.isValid) claw.teleport(cpos, { keepVelocity: false, checkForBlocks: false });
      } catch {
        // ignore
      }
    };
    try {
      this.setAction(ACT.IDLE);
      for (let s = 0; s < slashes && !broken; s++) {
        const tgt = this.pickTarget();
        if (!tgt) break;
        for (let t = 0; t < 50; t++) {
          if (!claw.isValid) {
            broken = true;
            break;
          }
          const goal = add(tgt.location, v(0, 1.4, 0));
          const to = sub(goal, cpos);
          const d = len(to);
          if (d < 2.2) break;
          cpos = add(cpos, scale(to, Math.min(0.6, d) / d));
          place();
          this.hoverStep();
          if (t % 2 === 0) particle(this.A.dim, FX.goldMote, cpos);
          yield;
        }
        if (broken || !claw.isValid) {
          broken = true;
          break;
        }
        try {
          claw.setProperty(PROP.strike, true);
        } catch {
          // ignore
        }
        telegraph(this.A.dim, v(tgt.location.x, this.A.floorY, tgt.location.z), 1.7, 0.6, RED_SEAL);
        for (let t = 0; t < 10; t++) {
          this.hoverStep();
          yield;
        }
        if (!claw.isValid) {
          broken = true;
          break;
        }
        if (dist(add(tgt.location, v(0, 1, 0)), cpos) < 2.8) this.hurtSafe(tgt, DMG.claw, cpos, 1.0, 0.35);
        sound(this.A.dim, SND.crack, cpos, 0.9, 1.4);
        particle(this.A.dim, FX.flakeBurst, cpos);
        try {
          claw.setProperty(PROP.strike, false);
        } catch {
          // ignore
        }
        for (let t = 0; t < 8; t++) {
          this.hoverStep();
          yield;
        }
      }
      if (!broken && claw.isValid) {
        for (let t = 0; t < 24; t++) {
          const home = add(this.pos, v(0, 1.5, 0));
          cpos = lerp(cpos, home, 0.18);
          place();
          this.hoverStep();
          if (dist(cpos, home) < 1.2) break;
          yield;
        }
      }
    } finally {
      if (claw.isValid) {
        try {
          claw.remove();
        } catch {
          // ignore
        }
      }
      this.clawEntity = undefined;
      if (!broken) this.setProp(PROP.claw, 0);
    }
    if (broken) {
      this.clawLost = true;
      this.h.title("§6The claw shatters!", "§7The Emperor reels", 40);
      sound(this.A.dim, SND.shatter, cpos, 1.6, 1.1);
      sound(this.A.dim, SND.roar, this.pos, 1.4, 1.3);
      this.dealDirect(BOSS.maxHp * 0.06);
      if (!this.dying) yield* this.stagger(90);
    }
  }

  /** Mirror half the damage the claw takes onto the Emperor itself. */
  onClawHurt(amount: number): void {
    system.run(() => this.dealDirect(amount * 0.5));
  }

  private hoverStep(): void {
    this.brake(0.9);
    const tgt = this.nearest(this.pos);
    if (tgt) this.facePoint(tgt.location, 3);
  }

  // ------------------------------------------------------------------ skill: Thousand Shard Storm (phase III)

  *shardStorm(): Gen {
    const c = this.A.center;
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(c.x, this.alt(3.5), c.z), 0.8, 60);
    this.setAction(ACT.STORM);
    this.h.title("§6The Thousand Shards", "§eFind the gap of golden light!", 40);
    sound(this.A.dim, SND.roar, this.pos, 1.5, 0.9);
    const n = 18;
    const shards: F.Frag[] = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const f = F.ringShard(v(c.x + Math.cos(a) * 3, this.A.floorY + 1.1, c.z + Math.sin(a) * 3));
      if (f) shards.push(f);
    }
    try {
      for (const wave of [0, 1]) {
        const from = wave === 0 ? 3 : 27;
        const to = wave === 0 ? 27 : 3;
        let gap = Math.random() * Math.PI * 2;
        const gapHalf = (26 * Math.PI) / 180;
        const dur = this.phase >= 3 ? 100 : 120;
        const hit = new Set<string>();
        // show where the ring will start and the gap before it moves
        for (let t = 0; t < 30; t++) {
          if (t % 6 === 0) {
            ring(this.A.dim, v(c.x, this.A.floorY + 0.4, c.z), from, Math.max(12, Math.floor(from * 3)), FX.redMote);
            for (let h = 0; h < 4; h++) particle(this.A.dim, FX.goldMote, v(c.x + Math.cos(gap) * from, this.A.floorY + 0.5 + h, c.z + Math.sin(gap) * from));
          }
          this.layRing(shards, from, gap, gapHalf, t);
          this.brake(0.8);
          yield;
        }
        for (let t = 0; t <= dur; t++) {
          const r = from + ((to - from) * t) / dur;
          gap += 0.018;
          this.layRing(shards, r, gap, gapHalf, t);
          if (t % 4 === 0) {
            const pts = Math.max(10, Math.floor(r * 2.2));
            for (let i = 0; i < pts; i++) {
              const a = (i / pts) * Math.PI * 2;
              if (Math.abs(angleDiff((a * 180) / Math.PI, (gap * 180) / Math.PI)) < (gapHalf * 180) / Math.PI) continue;
              particle(this.A.dim, FX.redMote, v(c.x + Math.cos(a) * r, this.A.floorY + 0.6, c.z + Math.sin(a) * r));
            }
            for (let h = 0; h < 5; h++) particle(this.A.dim, FX.goldMote, v(c.x + Math.cos(gap) * r, this.A.floorY + 0.4 + h * 0.8, c.z + Math.sin(gap) * r));
          }
          for (const p of this.targets()) {
            if (hit.has(p.id)) continue;
            const pr = distXZ(p.location, c);
            if (Math.abs(pr - r) > 1.1 || p.location.y > this.A.floorY + 2.6) continue;
            const pa = Math.atan2(p.location.z - c.z, p.location.x - c.x);
            if (Math.abs(angleDiff((pa * 180) / Math.PI, (gap * 180) / Math.PI)) < (gapHalf * 180) / Math.PI) continue;
            hit.add(p.id);
            this.hurtSafe(p, DMG.storm, c, wave === 0 ? 1.2 : -0.8, 0.4);
          }
          if (t % 20 === 0) sound(this.A.dim, SND.chime, this.pos, 1.0, 0.6 + t / dur);
          this.brake(0.8);
          yield;
        }
        for (let t = 0; t < 16; t++) yield;
      }
    } finally {
      let embedded = 0;
      for (const f of shards) {
        if (!f.e.isValid) continue;
        if (embedded < 4 && Math.random() < 0.35 && this.A.hasFloor(f.pos)) {
          embedded++;
          f.state = "slide";
          f.vel = v(0, 0, 0);
          f.damage = 0;
        } else F.removeFrag(f, true);
      }
    }
    this.setAction(ACT.IDLE);
  }

  private layRing(shards: F.Frag[], r: number, gap: number, gapHalf: number, t: number): void {
    const c = this.A.center;
    const n = shards.length;
    const span = Math.PI * 2 - gapHalf * 2;
    shards.forEach((f, i) => {
      if (!f.e.isValid) return;
      const a = gap + gapHalf + (span * (i + 0.5)) / n;
      F.moveTo(f, v(c.x + Math.cos(a) * r, this.A.floorY + 1.0 + Math.sin(t * 0.3 + i) * 0.25, c.z + Math.sin(a) * r));
    });
  }

  // ------------------------------------------------------------------ skill: The Kowtow (phase III)

  *kowtow(): Gen {
    const throne = this.A.w(0.5, 0, -15.5);
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(throne.x, this.alt(9), throne.z), 0.8, 60, this.A.center);
    this.setAction(ACT.KOWTOW_CALL);
    this.h.title("§6§lKNEEL", "§eSneak (crouch) when the third gong falls", 70);
    const strikes = [20, 45, 70];
    for (let t = 0; t <= 70; t++) {
      this.brake(0.8);
      this.turnTo(dirYaw(flat(sub(this.A.center, this.pos))), 5);
      const k = strikes.indexOf(t);
      if (k >= 0) {
        sound(this.A.dim, SND.gong, this.A.center, 2.0, 1.0 - k * 0.12);
        ringWave(this.A.dim, this.A.center, 10 + k * 8);
        this.h.actionbar(k < 2 ? `§6${k === 0 ? "One" : "Two"}... §e(sneak on the third gong)` : "§6§lThree!");
      }
      if (t % 5 === 0) particle(this.A.dim, FX.goldMote, this.mouth());
      if (t < 70) yield;
    }
    // judgement
    particle(this.A.dim, FX.goldBurst, this.mouth());
    ringWave(this.A.dim, this.A.center, 30);
    for (const p of this.targets()) {
      if (p.isSneaking) {
        try {
          p.onScreenDisplay.setActionBar("§7You knelt. §6The Emperor lowers its head to inspect you - strike!");
        } catch {
          // ignore
        }
      } else {
        this.hurtSafe(p, DMG.kowtow, this.pos, 0.6, 0.9);
        try {
          p.onScreenDisplay.setActionBar("§cYou refused to kneel.");
        } catch {
          // ignore
        }
      }
    }
    this.setAction(ACT.KOWTOW_BOW);
    this.vulnerableUntil = system.currentTick + 100;
    const bow = v(this.A.center.x, this.alt(-0.6), this.A.center.z - 13);
    for (let t = 0; t < 100; t++) {
      this.steer(bow, 0.35, 0.06);
      this.turnTo(0, 4);
      if (t % 15 === 0) particle(this.A.dim, FX.goldBurst, this.heart());
      yield;
    }
    this.setAction(ACT.IDLE);
    yield* this.flyTo(v(this.pos.x, this.alt(8), this.pos.z), 0.6, 30);
  }

  // ------------------------------------------------------------------ skill: Fragment Rush (phase III)

  *fragmentRush(): Gen {
    for (let k = 0; k < 3; k++) {
      const target = this.pickTarget();
      if (!target) return;
      this.setAction(ACT.RUSH_OUT);
      for (let t = 0; t < 12; t++) {
        this.brake(0.6);
        if (t % 3 === 0) particle(this.A.dim, FX.chipBurst, add(this.chest(), v(Math.random() * 4 - 2, Math.random() * 2, Math.random() * 4 - 2)));
        yield;
      }
      let behind: Vector3;
      try {
        const vd = target.getViewDirection();
        behind = sub(target.location, scale(norm(v(vd.x, 0, vd.z)), 8));
      } catch {
        behind = add(target.location, v(8, 0, 0));
      }
      if (!this.A.isInside(behind, -2)) behind = lerp(target.location, this.A.center, 0.5);
      const dest = v(behind.x, this.alt(0.6), behind.z);
      telegraph(this.A.dim, v(dest.x, this.A.floorY, dest.z), 2.6, 0.9, RED_SEAL);
      for (let t = 0; t < 15; t++) {
        if (t % 3 === 0) goldLine(this.A.dim, add(this.chest(), v(Math.random() * 6 - 3, 0, Math.random() * 6 - 3)), add(dest, v(0, 1.5, 0)), 1.2);
        yield;
      }
      this.pos = { ...dest };
      this.vel = v(0, 0, 0);
      this.yaw = dirYaw(flat(sub(target.location, dest)));
      this.prevYaw = this.yaw;
      this.setAction(ACT.RUSH_IN);
      particle(this.A.dim, FX.goldBurst, this.chest());
      sound(this.A.dim, SND.chime, dest, 1.2, 0.8);
      for (let t = 0; t < 7; t++) yield;
      const lunge = norm(flat(sub(target.location, this.pos)));
      let bit = false;
      for (let t = 0; t < 12; t++) {
        this.pos = add(this.pos, scale(lunge, 0.95));
        if (!bit && dist(add(target.location, v(0, 1, 0)), add(this.mouth(), v(0, -1.2, 0))) < 2.8) {
          bit = true;
          this.hurtSafe(target, DMG.rush, this.pos, 1.3, 0.4);
          sound(this.A.dim, SND.crack, target.location, 1.0, 1.5);
        }
        yield;
      }
      for (let t = 0; t < 12; t++) {
        this.brake(0.75);
        yield;
      }
    }
    this.setAction(ACT.IDLE);
  }

  // ------------------------------------------------------------------ phase transitions

  *transition(next: number): Gen {
    this.transitioning = true;
    this.invulnerable = true;
    this.note(`phase ${next}`);
    try {
      const c = this.A.center;
      this.setAction(ACT.IDLE);
      yield* this.flyTo(v(c.x, this.alt(8), c.z), 1.0, 40);
      this.setAction(ACT.ROAR);
      sound(this.A.dim, SND.roar, this.pos, 2.0, next === 2 ? 1.0 : 0.85);
      for (let t = 0; t < 8; t++) {
        this.brake(0.7);
        yield;
      }
      this.phase = next;
      this.setProp(PROP.phase, next);
      sound(this.A.dim, SND.shatter, this.pos, 2.0, next === 2 ? 1.0 : 0.75);
      particle(this.A.dim, FX.chipBurst, this.chest());
      particle(this.A.dim, FX.flakeBurst, this.chest());
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        F.slideShard(add(v(c.x, this.A.floorY + 0.2, c.z), v(Math.cos(a) * 3, 0, Math.sin(a) * 3)), v(Math.cos(a), 0, Math.sin(a)), 0.7);
      }
      this.h.onPhase(next);
      if (next === 2) {
        this.h.title("§6§lKINTSUGI", "§eThe Emperor cracks - and the cracks are filled with fury", 60);
        this.A.crackCourt();
        for (const idx of [1, 5]) {
          const p = this.A.bp.pillars[idx];
          F.driftRubble(this.A.w(p.x + 0.5, 12, p.z + 0.5));
          F.driftRubble(this.A.w(p.x + 0.5, 15, p.z + 0.5));
        }
      } else {
        this.h.title("§6§lTHE MANDATE FRACTURES", "§cGet off the golden seams!", 70);
        this.A.fracture(70);
        // the remaining tablets are flung off the shattering spine
        for (let i = 0; i < this.plates; i++) {
          const cell = this.A.randomFloorCell();
          if (cell) F.launchTablet(this.spine(i), this.A.standAt(cell.x, cell.z), 24, 7);
        }
        this.setPlates(0);
        this.nextPlateAt = system.currentTick + 400;
        for (const p of this.A.bp.pillars) {
          if (p.index % 2 === 0) F.driftRubble(this.A.w(p.x + 0.5, 10, p.z + 0.5));
        }
      }
      const hold = next === 2 ? 52 : 110;
      for (let t = 0; t < hold; t++) {
        this.brake(0.8);
        if (t % 10 === 0) particle(this.A.dim, FX.goldBurst, add(this.chest(), v(Math.random() * 4 - 2, Math.random() * 2, Math.random() * 4 - 2)));
        yield;
      }
      this.setAction(ACT.IDLE);
    } finally {
      this.invulnerable = false;
      this.transitioning = false;
      this.breatherNext = false;
    }
  }

  // ------------------------------------------------------------------ intro and death

  *awaken(): Gen {
    this.invulnerable = true;
    this.setAction(ACT.AWAKEN);
    for (let t = 0; t < 80; t++) {
      if (t === 58) {
        sound(this.A.dim, SND.roar, this.pos, 2.0, 1.0);
        particle(this.A.dim, FX.goldBurst, this.mouth());
      }
      if (t > 40) this.steer(add(this.pos, v(0, 0.08, 0.05)), 0.08, 0.02);
      yield;
    }
    this.setAction(ACT.IDLE);
    this.invulnerable = false;
    this.battle = true;
    this.nextPlateAt = system.currentTick + 400;
  }

  beginDeath(): void {
    if (this.dying || !this.valid) return;
    this.dying = true;
    this.invulnerable = true;
    this.battle = false;
    this.interrupt();
    this.run("death", this.death());
  }

  *death(): Gen {
    const c = this.A.center;
    this.setAction(ACT.IDLE);
    const from = { ...this.pos };
    const to = v(c.x, this.alt(7), c.z);
    for (let t = 1; t <= 24; t++) {
      this.pos = lerp(from, to, t / 24);
      yield;
    }
    this.setAction(ACT.DEATH);
    this.h.title("§6The Porcelain Emperor", "§7shatters...", 80);
    for (let t = 0; t < 118; t++) {
      if (t % 10 === 0) {
        sound(this.A.dim, SND.crack, this.pos, 1.5, 0.6 + t / 120);
        particle(this.A.dim, FX.chipBurst, add(this.chest(), v(Math.random() * 6 - 3, Math.random() * 3, Math.random() * 6 - 3)));
      }
      if (t % 25 === 0) sound(this.A.dim, SND.chime, this.pos, 1.2, 1.4 - t / 200);
      if (t === 100) {
        sound(this.A.dim, SND.shatter, this.pos, 2.5, 0.7);
        for (let i = 0; i < 4; i++) particle(this.A.dim, FX.goldBurst, add(this.chest(), v(Math.random() * 4 - 2, Math.random() * 2, Math.random() * 4 - 2)));
        particle(this.A.dim, FX.flakeBurst, this.chest());
        ringWave(this.A.dim, v(c.x, this.A.floorY, c.z), 30);
        for (let i = 0; i < 10; i++) {
          const a = (i / 10) * Math.PI * 2;
          const f = F.slideShard(add(this.chest(), v(Math.cos(a), 0, Math.sin(a))), v(Math.cos(a), 0, Math.sin(a)), 0.9);
          if (f) f.damage = 0;
        }
      }
      yield;
    }
    particle(this.A.dim, FX.petals, this.chest());
    try {
      this.e.remove();
    } catch {
      // ignore
    }
    this.h.onDefeated();
  }
}

const RED_SEAL = { red: 1.0, green: 0.22, blue: 0.16 };
export const COLORS = { GOLD, IVORY, RED_SEAL };
