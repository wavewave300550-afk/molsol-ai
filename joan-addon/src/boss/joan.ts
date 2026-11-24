import { Dimension, Entity, EntityDamageCause, Player, RGBA, system } from "@minecraft/server";
import { COLORS, JOAN, PROP_ACTION, PROP_PHASE, PROP_SEQ, TUNING, difficultyScale } from "../config.js";
import { burst, emit, ring, sigil, sound } from "../core/fx.js";
import { fightersNear, foesNear, hurt, isPlayer, push } from "../core/targets.js";
import { lineClear } from "../core/terrain.js";
import { add, dist, flatDir, hdist, len, norm, scale, sub, v, V3, yawOf } from "../core/vec.js";
import { ACT, ActName } from "../generated/anims.js";
import { PathField } from "../paths/field.js";
import { Path, PathOpts } from "../paths/path.js";
import { clipAir, conform } from "../paths/shapes.js";
import { Brain } from "./brain.js";
import { removeQuietly } from "./minions.js";

export type SkillGen = Generator<number, void, unknown>;

export interface RunningAction {
  name: string;
  gen: SkillGen;
  wait: number;
  started: number;
  interruptible: boolean;
}

export type Mode = "intro" | "fight" | "transition" | "dying" | "dead";

/** A background job owned by the boss (moving lights, echoes, flame runs...). Return false when finished. */
export interface BossTask {
  name: string;
  step(now: number): boolean;
  cleanup?(): void;
}

/**
 * One Joan of Arc encounter. Owns the entity, its road field, the brain and the
 * currently running action (a generator that yields the ticks it waits).
 */
export class JoanBoss {
  e: Entity;
  readonly id: string;
  dim: Dimension;
  field: PathField;
  brain: Brain;
  home: V3;
  phase: 0 | 1 | 2 | 3 = 0;
  mode: Mode = "intro";
  action?: RunningAction;
  now = 0;
  seq = 0;
  cooldowns = new Map<string, number>();
  history: string[] = [];
  gcdUntil = 0;
  chainLinks = 0;
  invulnerable = true;
  stunUntil = 0;
  vulnerableUntil = 0;
  idleSince = 0;
  noTargetSince = -1;
  minions = new Set<string>();
  tasks: BossTask[] = [];
  participants = new Map<string, number>();
  /** Behaviour counters (debug + tests): road reuse, combos, skills chosen by the brain. */
  stats = { reused: 0, combos: 0, chosen: {} as Record<string, number> };
  flags = {
    bell: new Set<number>(),
    martyrEcho: false,
    ultCount: 0,
    lastUlt: -99999,
    turnedRoadAt: -99999,
    pendingTransition: false,
    pendingDeath: false,
    pendingUlt: false,
    tutorial: new Set<string>(),
  };

  constructor(e: Entity, now: number) {
    this.e = e;
    this.id = e.id;
    this.dim = e.dimension;
    this.now = now;
    this.home = { ...e.location };
    this.field = new PathField(this.dim, e.id);
    this.brain = new Brain(this);
  }

  // ------------------------------------------------------------------ properties & animation
  get valid(): boolean {
    return this.e.isValid;
  }

  get pos(): V3 {
    return this.e.location;
  }

  get hp(): number {
    return this.e.getComponent("minecraft:health")?.currentValue ?? 0;
  }

  get hpFrac(): number {
    const h = this.e.getComponent("minecraft:health");
    return h ? h.currentValue / h.effectiveMax : 0;
  }

  setPhase(p: 0 | 1 | 2 | 3): void {
    this.phase = p;
    try {
      this.e.setProperty(PROP_PHASE, p);
      this.e.setDynamicProperty("joan:phase", p);
    } catch {
      // ignore
    }
  }

  /** Play an action animation (re-triggers even when the same action repeats). */
  anim(name: ActName): void {
    this.seq = (this.seq + 1) % 16;
    try {
      this.e.setProperty(PROP_ACTION, ACT[name]);
      this.e.setProperty(PROP_SEQ, this.seq);
    } catch {
      // ignore
    }
  }

  freeze(on: boolean): void {
    try {
      const mv = this.e.getComponent("minecraft:movement");
      if (!mv) return;
      if (on) mv.setCurrentValue(0);
      else mv.resetToDefaultValue();
    } catch {
      // ignore
    }
  }

  face(p: V3): void {
    try {
      const d = flatDir(this.pos, p);
      if (len(d) > 0) this.e.setRotation({ x: 0, y: yawOf(d) });
    } catch {
      // ignore
    }
  }

  /** Drive the body with an exact velocity this tick. */
  drive(vel: V3): void {
    try {
      this.e.clearVelocity();
      this.e.applyImpulse(vel);
    } catch {
      // ignore
    }
  }

  stop(): void {
    try {
      this.e.clearVelocity();
    } catch {
      // ignore
    }
  }

  teleport(p: V3, face?: V3): void {
    try {
      this.e.teleport(p, face ? { facingLocation: face } : undefined);
    } catch {
      // ignore
    }
  }

  // ------------------------------------------------------------------ actions
  start(name: string, gen: SkillGen, interruptible = true): void {
    if (this.action) this.interrupt();
    this.action = { name, gen, wait: 0, started: this.now, interruptible };
    this.freeze(true);
    this.history.push(name);
    if (this.history.length > 12) this.history.shift();
  }

  interrupt(): void {
    const a = this.action;
    if (!a) return;
    try {
      a.gen.return(undefined);
    } catch (err) {
      console.warn(`[joan] cleanup of ${a.name} failed: ${err}`);
    }
    this.endAction();
  }

  private endAction(): void {
    this.action = undefined;
    this.freeze(false);
    if (this.mode === "fight") this.anim("none");
  }

  stepAction(): void {
    const a = this.action;
    if (!a) return;
    if (a.wait > 0) {
      a.wait--;
      return;
    }
    let r: IteratorResult<number, void>;
    try {
      r = a.gen.next();
    } catch (err) {
      console.warn(`[joan] action ${a.name} failed: ${err}`);
      this.endAction();
      return;
    }
    if (this.action !== a) return; // the action started another one
    if (r.done) this.endAction();
    else a.wait = Math.max(0, (r.value ?? 1) - 1);
  }

  cooldown(name: string, ticks: number): void {
    this.cooldowns.set(name, this.now + Math.round(ticks * difficultyScale().cooldown));
  }

  ready(name: string): boolean {
    return (this.cooldowns.get(name) ?? 0) <= this.now;
  }

  // ------------------------------------------------------------------ helpers for skills
  /** Telegraph duration in ticks for the current phase and difficulty (k scales it). */
  tel(k = 1): number {
    const base = TUNING.telegraph[this.phase >= 2 ? 2 : 1] ?? 18;
    return Math.max(10, Math.round(base * k * difficultyScale().telegraph));
  }

  fighters(radius = TUNING.leashRadius + 8): Player[] {
    return fightersNear(this.dim, this.home, radius);
  }

  get target(): Player | undefined {
    return this.brain.target;
  }

  /** Target position predicted `ticks` ahead from its current velocity. */
  predict(p: Entity, ticks: number): V3 {
    let vel = v(0, 0, 0);
    try {
      vel = p.getVelocity();
    } catch {
      // ignore
    }
    const lead = scale(v(vel.x, 0, vel.z), ticks);
    const l = len(lead);
    return add(p.location, l > 6 ? scale(lead, 6 / l) : lead);
  }

  /** Default road options for the current phase. */
  roadOpts(extra: Partial<PathOpts>): PathOpts {
    const p2 = this.phase >= 2;
    return {
      kind: "road",
      owner: this.id,
      speed: 0.42,
      radius: 0.95,
      band: [-0.8, 0.8],
      form: this.tel(),
      life: p2 ? 120 : 160,
      burning: p2,
      damage: p2 ? 1.5 : 0,
      restless: 0,
      switching: p2,
      crossings: p2,
      memory: true,
      ...extra,
    };
  }

  /** Ground road that follows the terrain. */
  groundRoad(points: V3[], extra: Partial<PathOpts>): Path | undefined {
    const pts = conform(this.dim, points, this.pos.y);
    // a closed road that the terrain cut open must not be closed with a chord through walls
    if (extra.loop && pts.length < points.length * 0.97) return undefined;
    return this.field.add(pts, this.roadOpts(extra), this.now);
  }

  /** Aerial road (stops at the first solid block). */
  airRoad(points: V3[], extra: Partial<PathOpts>): Path | undefined {
    const pts = clipAir(this.dim, points);
    return this.field.add(pts, this.roadOpts({ aerial: true, radius: 1.3, ...extra }), this.now);
  }

  /** Damage every foe within radius of `at` (once), with knockback away from `from`. */
  strike(at: V3, radius: number, dmg: number, knock = 0.6, up = 0.35, from?: V3, cause = EntityDamageCause.entityAttack): Entity[] {
    const hit: Entity[] = [];
    for (const e of foesNear(this.dim, at, radius + 0.6)) {
      if (hdist(e.location, at) > radius + 0.3 || Math.abs(e.location.y - at.y) > 3) continue;
      if (hurt(e, dmg, this.e, cause)) hit.push(e);
      push(e, add(scale(flatDir(from ?? at, e.location), knock), v(0, up, 0)));
    }
    return hit;
  }

  /** Damage foes inside a cone in front of `origin`. */
  cone(origin: V3, dir: V3, range: number, halfAngleDeg: number, dmg: number, knockDir?: V3): Entity[] {
    const hit: Entity[] = [];
    const cosA = Math.cos((halfAngleDeg * Math.PI) / 180);
    const d = norm(v(dir.x, 0, dir.z));
    for (const e of foesNear(this.dim, origin, range + 0.8)) {
      const to = flatDir(origin, e.location);
      const dd = hdist(origin, e.location);
      if (dd > range || Math.abs(e.location.y - origin.y) > 3) continue;
      if (dd > 1.2 && to.x * d.x + to.z * d.z < cosA) continue;
      if (hurt(e, dmg, this.e)) hit.push(e);
      const kd = knockDir ?? to;
      push(e, v(kd.x * 0.75, 0.32, kd.z * 0.75));
    }
    return hit;
  }

  /** Damage foes near the segment a-b. */
  lineHit(a: V3, b: V3, width: number, dmg: number, already?: Set<string>): Entity[] {
    const hit: Entity[] = [];
    const ab = sub(b, a);
    const L = len(ab) || 1;
    const dir = scale(ab, 1 / L);
    for (const e of foesNear(this.dim, add(a, scale(ab, 0.5)), L / 2 + width + 1)) {
      if (already?.has(e.id)) continue;
      const ap = sub(e.location, a);
      const t = Math.max(0, Math.min(L, ap.x * dir.x + ap.z * dir.z + ap.y * dir.y));
      const c = add(a, scale(dir, t));
      if (hdist(c, e.location) > width || Math.abs(e.location.y - c.y) > 2.6) continue;
      if (hurt(e, dmg, this.e)) hit.push(e);
      already?.add(e.id);
      const side = flatDir(c, e.location);
      push(e, v(side.x * 0.5 + dir.x * 0.4, 0.3, side.z * 0.5 + dir.z * 0.4));
    }
    return hit;
  }

  /**
   * Ride along a path from s0 to s1 (any direction) at `speed` blocks/tick.
   * Yields every tick; damages foes it passes once (`contact` damage).
   */
  *ride(path: Path, s0: number, s1: number, speed: number, contact = 0, aerial = false): SkillGen {
    const dirSign = s1 >= s0 ? 1 : -1;
    let s = s0;
    const hitSet = new Set<string>();
    let guard = Math.ceil(Math.abs(s1 - s0) / Math.max(0.05, speed)) + 30;
    try {
      while (guard-- > 0 && this.valid) {
        s += dirSign * speed;
        const done = dirSign > 0 ? s >= s1 : s <= s1;
        const target = path.pointAt(done ? s1 : s);
        const here = this.pos;
        let vel = sub(target, here);
        if (len(vel) > 3.2) {
          this.teleport(target);
          vel = v(0, 0, 0);
        }
        if (aerial || path.o.aerial) vel = add(vel, v(0, 0.08, 0));
        this.drive(vel);
        const ahead = path.pointAt(s + dirSign * 2);
        this.face(ahead);
        if (contact > 0) {
          for (const e of foesNear(this.dim, here, 1.8)) {
            if (hitSet.has(e.id)) continue;
            hitSet.add(e.id);
            hurt(e, contact, this.e);
            const d = path.dirAt(s);
            push(e, v(d.x * dirSign * 0.9, 0.45, d.z * dirSign * 0.9));
          }
        }
        if (done) break;
        yield 1;
      }
    } finally {
      // also when a stagger / bell / phase change interrupts the ride: no coasting off the road
      if (this.valid) this.stop();
    }
  }

  /** Telegraphed ground impact: sigil grows for `ticks`, then the caller strikes. */
  markImpact(at: V3, size: number, ticks: number, color: RGBA = COLORS.roadGold, falseMark = false): void {
    sigil(this.dim, v(at.x, at.y + 0.05, at.z), size, ticks / 20, color, falseMark);
  }

  impactFx(at: V3, radius: number, color: RGBA = COLORS.roadGold): void {
    burst(this.dim, add(at, v(0, 0.3, 0)), color, 1.2);
    ring(this.dim, at, 0.3, radius, 0.45, color);
    emit(this.dim, "joan:flash", add(at, v(0, 0.6, 0)), { size: radius * 1.2, life: 0.3, color });
    sound(this.dim, "joan.impact", at, 1, this.phase >= 2 ? 0.85 : 1);
  }

  /** Is there open sky / air above p (for aerial roads and descents)? */
  airAbove(p: V3, h: number): boolean {
    return lineClear(this.dim, add(p, v(0, 0.5, 0)), add(p, v(0, h, 0)));
  }

  // ------------------------------------------------------------------ background tasks
  addTask(t: BossTask): void {
    this.tasks.push(t);
  }

  runTasks(): void {
    for (let i = this.tasks.length - 1; i >= 0; i--) {
      const t = this.tasks[i];
      let keep = false;
      try {
        keep = t.step(this.now);
      } catch (err) {
        console.warn(`[joan] task ${t.name} failed: ${err}`);
      }
      if (!keep) {
        try {
          t.cleanup?.();
        } catch {
          // ignore
        }
        this.tasks.splice(i, 1);
      }
    }
  }

  clearTasks(): void {
    for (const t of this.tasks) {
      try {
        t.cleanup?.();
      } catch {
        // ignore
      }
    }
    this.tasks = [];
  }

  // ------------------------------------------------------------------ minions
  track(e: Entity | undefined): Entity | undefined {
    if (e) this.minions.add(e.id);
    return e;
  }

  untrack(e: Entity | undefined): void {
    if (!e) return;
    this.minions.delete(e.id);
    removeQuietly(e);
  }

  // ------------------------------------------------------------------ damage intake (called from beforeEvents)
  /** Returns the adjusted damage (0 = cancel). Runs in restricted (before-event) context: no world writes. */
  filterDamage(amount: number, cause: string, attacker?: Entity, projectile?: Entity): number {
    if (this.invulnerable || this.mode === "dying" || this.mode === "dead") return 0;
    if (cause === "fire" || cause === "fireTick" || cause === "lava") {
      if (this.phase >= 2) return 0; // the Saint of the Burning Road does not burn
    }
    let dmg = amount;
    const fighters = Math.max(1, this.brain.engaged);
    dmg /= 1 + 0.45 * (fighters - 1); // multiplayer scaling
    if (this.phase >= 2) dmg *= 0.9;
    if (this.now < this.vulnerableUntil) dmg *= 1.5;
    if (projectile && this.field.wasRedirected(projectile)) dmg *= 2; // Turned Road
    const hp = this.hp;
    if (this.phase === 1 && hp - dmg <= this.maxHp * TUNING.phase2At) {
      dmg = Math.max(0, hp - this.maxHp * TUNING.phase2At);
      this.flags.pendingTransition = true;
    }
    if (hp - dmg <= 1) {
      dmg = Math.max(0, hp - 1);
      this.flags.pendingDeath = true;
    }
    if (attacker && isPlayer(attacker)) this.participants.set(attacker.id, (this.participants.get(attacker.id) ?? 0) + dmg);
    if (projectile && this.field.wasRedirected(projectile)) this.flags.turnedRoadAt = this.now;
    return dmg;
  }

  get maxHp(): number {
    return this.e.getComponent("minecraft:health")?.effectiveMax ?? TUNING.maxHealth;
  }

  // ------------------------------------------------------------------ cleanup
  dispose(): void {
    this.interrupt();
    this.clearTasks();
    this.field.retireAll(this.now, 1);
    for (const id of this.minions) {
      for (const e of this.dim.getEntities({ families: ["joan_minion"] })) if (e.id === id) removeQuietly(e);
    }
    this.minions.clear();
  }

  isJoan(e: Entity): boolean {
    return e.typeId === JOAN && e.id === this.id;
  }

  distTo(p: V3): number {
    return dist(this.pos, p);
  }

  later(ticks: number, fn: () => void): void {
    system.runTimeout(() => {
      try {
        fn();
      } catch (err) {
        console.warn(`[joan] delayed effect failed: ${err}`);
      }
    }, Math.max(1, Math.round(ticks)));
  }
}
