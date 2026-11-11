/**
 * BossController: one per living Wrong Hatch.
 *
 * Abilities are generator functions ("timelines") that yield the number of
 * ticks to wait. The controller runs exactly one timeline at a time, picks the
 * next ability with ai.ts, gates phase transitions, filters incoming damage
 * (shell fortress, stuns, invulnerable windows, phase gates, the scripted
 * death) and keeps the boss bar, leash and despawn logic up to date.
 */
import { Dimension, Entity, EntityHealthComponent, EntityHurtBeforeEvent, Player, Vector3 } from "@minecraft/server";
import { BASE_HP, DESPAWN_AFTER_TICKS, FORTRESS, HUD_RANGE, LAST_HATCH_AT, LEASH_RANGE, PHASE2_AT, PHASE3_AT, RECOVER, RESET_AFTER_TICKS } from "../config.js";
import { ACT, ActName } from "../generated/spec.js";
import { targetsNear, viewersNear } from "../util/combat.js";
import { particle, sound } from "../util/fx.js";
import { add, angleDelta, dirYaw, dist, hdist, hnorm, rand, sub, v3, yawDir } from "../util/vec.js";
import { chooseAbility, planCombo, Situation } from "./ai.js";
import { BossLink, chickCount, clearBrood } from "./brood.js";
import { clearHazards } from "./hazards.js";
import { deathSequence, finalHatch, intro, phaseCrack } from "./phases.js";

export type Timeline = Generator<number, void, void>;

const PHASE_NAMES = ["", "Phase I: The Shell", "Phase II: The Crack", "Phase III: The Hatching"];

export class BossController implements BossLink {
  readonly id: string;
  phase = 1;
  now = 0;
  // timeline
  private job: Timeline | null = null;
  jobName = "";
  private wait = 0;
  // ai bookkeeping
  readonly cooldowns = new Map<string, number>();
  readonly lastUsed = new Map<string, number>();
  phaseStart = 0;
  recoverUntil = 0;
  lastAbility = "";
  combo: string | null = null;
  behindTicks = 0;
  crowdTicks = 0;
  // damage state
  invulnerable = true;
  fortress: { absorbed: number; threshold: number; broken: boolean } | null = null;
  exposedUntil = 0;
  exposedMul = 1;
  dying = false;
  private pendingPhase = 0;
  readonly threat = new Map<string, number>();
  private recent: { t: number; amount: number }[] = [];
  // world state
  hpScale = 1;
  home: Vector3;
  targetId: string | undefined;
  private targetLockUntil = 0;
  private noTargetTicks = 0;
  private noPlayerTicks = 0;
  private moveMode = "";
  private lastName = "";
  fh1 = false;
  fh2 = false;
  hatchCountdown = -1;
  readonly participants = new Set<string>();

  constructor(readonly entity: Entity) {
    this.id = entity.id;
    const home = entity.getDynamicProperty("wh:home");
    this.home = typeof home === "object" ? (home as Vector3) : entity.location;
    // A boss initialises exactly once; chunk reloads (entitySpawn cause "Loaded" / entityLoad) restore it.
    if (!entity.getDynamicProperty("wh:init")) {
      this.home = entity.location;
      entity.setDynamicProperty("wh:home", this.home);
      this.initHealth();
      this.start("intro", intro(this));
    } else {
      // restored after a reload / chunk load
      this.phase = Math.max(1, Math.min(3, Number(entity.getDynamicProperty("wh:phase") ?? 1)));
      this.hpScale = Number(entity.getDynamicProperty("wh:hpScale") ?? 1);
      this.fh1 = !!entity.getDynamicProperty("wh:fh1");
      this.fh2 = !!entity.getDynamicProperty("wh:fh2");
      this.invulnerable = false;
      this.setPhaseVisual(this.phase);
      this.setAnim("none");
      this.setMove("chase");
    }
    this.updateName();
  }

  // ------------------------------------------------------------------ BossLink
  dim(): Dimension {
    return this.entity.dimension;
  }
  dmgMul(): number {
    return this.phase >= 3 ? 1.15 : 1;
  }
  chickCap(): number {
    return Math.min(10, 4 + this.phase + 2 * (this.hpScale - 1));
  }
  healFraction(f: number): void {
    const h = this.health();
    if (!h || this.dying) return;
    try {
      h.setCurrentValue(Math.min(h.effectiveMax, h.currentValue + h.effectiveMax * f));
    } catch {
      // ignore
    }
  }

  // ------------------------------------------------------------------ setup
  private initHealth(): void {
    const n = Math.max(1, Math.min(4, targetsNear(this.dim(), this.entity.location, HUD_RANGE).length));
    this.hpScale = n;
    try {
      this.entity.triggerEvent(`wh:hp_${n}`);
    } catch {
      // ignore
    }
    this.entity.setDynamicProperty("wh:init", true);
    this.entity.setDynamicProperty("wh:hpScale", n);
    this.entity.setDynamicProperty("wh:phase", 1);
    // the health component group applies next tick; top the boss up then
    this.deferred.push(() => {
      const h = this.health();
      if (h) h.setCurrentValue(Math.min(h.effectiveMax, BASE_HP[n - 1]));
    });
  }
  private deferred: (() => void)[] = [];

  health(): EntityHealthComponent | undefined {
    try {
      return this.entity.getComponent("minecraft:health") as EntityHealthComponent | undefined;
    } catch {
      return undefined;
    }
  }
  hpFrac(): number {
    const h = this.health();
    if (!h) return 1;
    return h.currentValue / Math.max(1, h.effectiveMax);
  }

  // ------------------------------------------------------------------ presentation
  setAnim(name: ActName): void {
    try {
      this.entity.setProperty("wh:anim", ACT[name]);
    } catch {
      // ignore
    }
  }
  setPhaseVisual(p: number): void {
    try {
      this.entity.setProperty("wh:phase", p);
    } catch {
      // ignore
    }
  }
  setMove(mode: "chase" | "busy"): void {
    const want = mode === "busy" ? "busy" : this.phase >= 3 ? "chase_fast" : "chase";
    if (want === this.moveMode) return;
    this.moveMode = want;
    try {
      this.entity.triggerEvent(`wh:${want}`);
    } catch {
      // ignore
    }
  }
  updateName(): void {
    let name = `§l§6The Wrong Hatch§r §7- §e${PHASE_NAMES[this.phase]}`;
    if (this.hatchCountdown >= 0) name = `§l§6The Wrong Hatch§r §7- §c§lFINAL HATCH ${Math.ceil(this.hatchCountdown / 20)}s`;
    else if (this.fortress) name = `§l§6The Wrong Hatch§r §7- §bShell Fortress`;
    else if (this.now < this.exposedUntil) name = `§l§6The Wrong Hatch§r §7- §a§lEXPOSED!`;
    if (name !== this.lastName) {
      this.lastName = name;
      try {
        this.entity.nameTag = name;
      } catch {
        // ignore
      }
    }
  }
  announce(title: string, sub?: string, actionbarOnly = false): void {
    for (const p of viewersNear(this.dim(), this.entity.location, HUD_RANGE)) {
      try {
        if (actionbarOnly) p.onScreenDisplay.setActionBar(title);
        else p.onScreenDisplay.setTitle(title, { subtitle: sub ?? "", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
      } catch {
        // ignore
      }
    }
  }

  // ------------------------------------------------------------------ geometry
  yaw(): number {
    try {
      return this.entity.getRotation().y;
    } catch {
      return 0;
    }
  }
  forward(): Vector3 {
    return yawDir(this.yaw());
  }
  pos(): Vector3 {
    return this.entity.location;
  }
  center(): Vector3 {
    return add(this.entity.location, v3(0, 2.4, 0));
  }
  chest(): Vector3 {
    return add(add(this.entity.location, v3(0, 2.1, 0)), mul2(this.forward(), 2.2));
  }
  beak(): Vector3 {
    return add(add(this.entity.location, v3(0, 3.5, 0)), mul2(this.forward(), 2.9));
  }
  /** Angle (deg) between boss forward and the direction to `p`: 0 = in front, 180 = behind. */
  angleTo(p: Vector3): number {
    const d = sub(p, this.entity.location);
    return Math.abs(angleDelta(this.yaw(), dirYaw(d)));
  }
  /** Rotate toward a point, at most `maxDeg` this tick. Returns the remaining angle. */
  face(p: Vector3, maxDeg = 12): number {
    const want = dirYaw(sub(p, this.entity.location));
    const cur = this.yaw();
    const d = angleDelta(cur, want);
    const step = Math.max(-maxDeg, Math.min(maxDeg, d));
    try {
      this.entity.setRotation({ x: 0, y: cur + step });
    } catch {
      // ignore
    }
    return Math.abs(d - step);
  }

  // ------------------------------------------------------------------ targeting
  players(r = HUD_RANGE): Player[] {
    return targetsNear(this.dim(), this.entity.location, r);
  }
  target(): Player | undefined {
    const list = this.players(LEASH_RANGE + 8);
    if (!list.length) return undefined;
    let cur = list.find((p) => p.id === this.targetId);
    if (!cur || this.now >= this.targetLockUntil) {
      // threat-weighted choice: recent damage dealers are favoured, distance breaks ties
      let best: Player | undefined;
      let bestScore = -Infinity;
      for (const p of list) {
        const d = dist(p.location, this.entity.location);
        const score = (this.threat.get(p.id) ?? 0) * 0.6 - d + (p.id === this.targetId ? 6 : 0) + Math.random() * 4;
        if (score > bestScore) {
          bestScore = score;
          best = p;
        }
      }
      cur = best;
      this.targetId = cur?.id;
      this.targetLockUntil = this.now + 160;
      for (const [k, v] of this.threat) this.threat.set(k, v * 0.5);
    }
    return cur;
  }

  // ------------------------------------------------------------------ timelines
  start(name: string, job: Timeline): void {
    this.stop();
    this.job = job;
    this.jobName = name;
    this.wait = 0;
  }
  stop(): void {
    if (this.job) {
      try {
        this.job.return();
      } catch (e) {
        console.warn(`[wrong_hatch] cleanup of ${this.jobName} failed: ${e}`);
      }
    }
    this.job = null;
    this.jobName = "";
  }
  busy(): boolean {
    return this.job !== null;
  }
  ready(name: string): boolean {
    return this.now >= (this.cooldowns.get(name) ?? 0);
  }
  cool(name: string, ticks: number): void {
    this.lastUsed.set(name, this.now);
    // faster cooldowns in later phases
    const k = this.phase === 3 ? 0.7 : this.phase === 2 ? 0.85 : 1;
    this.cooldowns.set(name, this.now + Math.round(ticks * k));
  }
  private step(): void {
    if (!this.job) return;
    if (this.wait > 0) {
      this.wait--;
      if (this.wait > 0) return;
    }
    let r: IteratorResult<number, void>;
    try {
      r = this.job.next();
    } catch (e) {
      console.warn(`[wrong_hatch] ability ${this.jobName} crashed: ${e}`);
      this.job = null;
      this.jobName = "";
      this.setAnim("none");
      return;
    }
    if (r.done) {
      this.job = null;
      this.lastAbility = this.jobName;
      this.jobName = "";
      const [a, b] = RECOVER[this.phase];
      this.recoverUntil = Math.max(this.recoverUntil, this.now + Math.round(rand(a, b)));
      if (!this.dying && !this.lastAbility.startsWith("phase") && this.lastAbility !== "intro") planCombo(this, this.lastAbility);
    } else {
      this.wait = Math.max(1, r.value);
    }
  }

  // ------------------------------------------------------------------ damage filter (before event, read-only context)
  filterDamage(ev: EntityHurtBeforeEvent): void {
    const src = ev.damageSource.damagingEntity;
    if (this.invulnerable || this.dying) {
      ev.cancel = true;
      this.deferred.push(() => {
        particle(this.dim(), "wh:gold_ring", this.pos(), 2.2);
        sound(this.dim(), "wrong_hatch.shell_close", this.center(), 0.6, 1.6);
      });
      return;
    }
    let dmg = ev.damage;
    if (this.fortress) {
      this.fortress.absorbed += dmg;
      dmg *= FORTRESS.reduction;
    }
    if (this.now < this.exposedUntil) dmg *= this.exposedMul;
    const h = this.health();
    if (h) {
      const max = h.effectiveMax;
      const after = h.currentValue - dmg;
      // phase gates: damage never skips a phase transition
      let floor = 0;
      if (this.phase === 1) floor = max * PHASE2_AT;
      else if (!this.fh1) floor = max * PHASE3_AT;
      else if (!this.fh2) floor = max * LAST_HATCH_AT;
      if (floor > 0 && after < floor) dmg = Math.max(0, h.currentValue - floor + 0.01);
      if (h.currentValue - dmg <= 1) {
        dmg = Math.max(0, h.currentValue - 1);
        this.dying = true;
        this.invulnerable = true;
      }
    }
    ev.damage = Math.max(0, dmg);
    if (src instanceof Player) {
      this.threat.set(src.id, (this.threat.get(src.id) ?? 0) + ev.damage);
      this.participants.add(src.id);
    } else if (src && src.typeId === "minecraft:player") {
      this.participants.add(src.id);
    }
    this.recent.push({ t: this.now, amount: ev.damage });
  }
  damageInLast(ticks: number): number {
    let s = 0;
    for (const r of this.recent) if (this.now - r.t <= ticks) s += r.amount;
    return s;
  }

  // ------------------------------------------------------------------ main tick
  tick(now: number): void {
    this.now = now;
    const ds = this.deferred.splice(0);
    for (const f of ds) {
      try {
        f();
      } catch {
        // ignore
      }
    }
    if (this.recent.length > 64) this.recent = this.recent.filter((r) => now - r.t < 200);

    if (this.dying && this.jobName !== "death") {
      this.start("death", deathSequence(this));
    } else if (!this.dying && this.jobName !== "intro" && !this.jobName.startsWith("phase")) {
      const f = this.hpFrac();
      if (this.phase === 1 && f <= PHASE2_AT + 0.001) this.pendingPhase = 2;
      else if (this.phase === 2 && !this.fh1 && f <= PHASE3_AT + 0.001) this.pendingPhase = 3;
      else if (this.phase === 3 && !this.fh2 && f <= LAST_HATCH_AT + 0.001) this.pendingPhase = 4;
      if (this.pendingPhase) {
        const p = this.pendingPhase;
        this.pendingPhase = 0;
        this.fortress = null;
        if (p === 2) this.start("phase_crack", phaseCrack(this));
        else this.start(p === 3 ? "phase_hatch1" : "phase_hatch2", finalHatch(this, p === 3 ? 1 : 2));
      }
    }

    this.step();

    if (!this.job && !this.dying) {
      const t = this.target();
      if (t) {
        this.noTargetTicks = 0;
        this.updateAwareness(t);
        if (now >= this.recoverUntil) {
          const s = this.situation(t);
          const pick = chooseAbility(this, s);
          if (pick) {
            this.setMove("busy");
            this.start(pick.id, pick.run(this, s));
            this.step();
          } else {
            this.setMove("chase");
          }
        } else {
          this.setMove("chase");
          // turn toward the target while recovering
          if (hdist(t.location, this.pos()) < 9) this.face(t.location, 6);
        }
      } else {
        this.idleTick();
      }
    }
    if (now % 10 === 0) this.updateName();
    if (now % 20 === 0) this.housekeeping();
  }

  private updateAwareness(t: Player): void {
    const players = this.players(8);
    const behind = players.filter((p) => this.angleTo(p.location) > 115 && hdist(p.location, this.pos()) < 7);
    this.behindTicks = behind.length ? this.behindTicks + 1 : Math.max(0, this.behindTicks - 2);
    const crowd = players.filter((p) => hdist(p.location, this.pos()) < 4.2).length;
    this.crowdTicks = crowd >= 1 ? this.crowdTicks + crowd : Math.max(0, this.crowdTicks - 3);
    void t;
  }

  situation(t: Player): Situation {
    const all = this.players(HUD_RANGE);
    const d = hdist(t.location, this.pos());
    return {
      target: t,
      dist: d,
      angle: this.angleTo(t.location),
      all,
      near: all.filter((p) => hdist(p.location, this.pos()) < 6.5),
      behind: all.filter((p) => this.angleTo(p.location) > 115 && hdist(p.location, this.pos()) < 8),
      far: all.filter((p) => hdist(p.location, this.pos()) > 14),
      chicks: chickCount(this.id),
      recentDamage: this.damageInLast(120),
    };
  }

  private idleTick(): void {
    this.noTargetTicks++;
    this.setMove("busy");
    if (this.noTargetTicks > RESET_AFTER_TICKS) {
      // leash: return home and regenerate (the shell cannot un-crack, so the phase is kept)
      if (dist(this.pos(), this.home) > 6 && this.noTargetTicks % 40 === 0) {
        particle(this.dim(), "wh:feather_burst", this.center());
        try {
          this.entity.teleport(this.home);
        } catch {
          // ignore
        }
        particle(this.dim(), "wh:feather_burst", add(this.home, v3(0, 2, 0)));
      }
      if (this.noTargetTicks % 20 === 0) {
        this.healFraction(0.02);
        this.threat.clear();
      }
    }
  }

  private housekeeping(): void {
    const anyone = viewersNear(this.dim(), this.pos(), 96).length > 0;
    this.noPlayerTicks = anyone ? 0 : this.noPlayerTicks + 20;
    if (this.noPlayerTicks >= DESPAWN_AFTER_TICKS && !this.dying) {
      this.despawn();
      return;
    }
    // leash while fighting: never wander far from the arena
    if (!this.busy() && dist(this.pos(), this.home) > LEASH_RANGE + 16) {
      const dir = hnorm(sub(this.home, this.pos()));
      try {
        this.entity.teleport(add(this.pos(), v3(dir.x * 6, 0.5, dir.z * 6)));
      } catch {
        // ignore
      }
    }
    // vertical safety: fell into the void / far below the arena
    if (this.pos().y < this.home.y - 30) {
      try {
        this.entity.teleport(this.home);
      } catch {
        // ignore
      }
    }
  }

  despawn(): void {
    this.cleanup();
    try {
      this.entity.triggerEvent("wh:despawn");
    } catch {
      try {
        this.entity.remove();
      } catch {
        // ignore
      }
    }
  }

  /** Remove everything that belongs to this boss (hazards, brood, shells). */
  cleanup(stopJob = true): void {
    if (stopJob) this.stop();
    clearHazards(this.id);
    clearBrood(this.id);
    for (const s of this.shells) {
      if (s.isValid) {
        try {
          s.remove();
        } catch {
          // ignore
        }
      }
    }
    this.shells = [];
  }
  shells: Entity[] = [];

  setPhase(p: number): void {
    this.phase = p;
    this.phaseStart = this.now;
    this.entity.setDynamicProperty("wh:phase", p);
    this.setPhaseVisual(p);
    this.moveMode = "";
    this.updateName();
  }
}

function mul2(v: Vector3, k: number): Vector3 {
  return { x: v.x * k, y: v.y * k, z: v.z * k };
}
