import {
  Dimension,
  Entity,
  EntityDamageCause,
  HudVisibility,
  Player,
  world,
} from "@minecraft/server";
import { CFG } from "../config.js";
import { ACT, ENT, FOGS, MUSIC, PHASE } from "../generated/ids.js";
import { bosses, clock, ledgerAdd, parts, PartKind } from "../registry.js";
import { particle, sound } from "../util/fx.js";
import {
  add, approachAngle, clamp, dist, hdist, len, modelToWorld, mul, norm, pitchOf, rand, sub, V3, wrapAngle, yawOf,
} from "../util/vec.js";
import { combatants, groundY, safeRemove, setProp, spectators } from "../util/world.js";
import { Minion, MinionSet, Seraph } from "./minions.js";
import * as A from "./actions.js";
import * as S from "./sequences.js";

export type Step = Generator<number, void, unknown>;

export interface Action {
  name: string;
  gen: Step;
  wait: number;
  started: number;
  interruptible: boolean;
  cleanup?: () => void;
}

export interface Goal {
  pos?: V3; // world position to steer to (y = absolute), overrides orbit
  alt?: number; // altitude above ground (used when pos is undefined or pos.y < 0)
  face?: V3; // world point to face; default: current target
  speed: number;
  turn: number;
  accel: number;
}

interface Participant {
  name: string;
  damage: number;
}

const PART_OFFSET: { [k in PartKind]: [number, number, number, number] } = {
  // model x, y, z of the box centre, half height (blocks)
  prow: [0, 66, -150, 2.0],
  stern: [0, 62, 128, 1.8],
  heart: [0, 62, -2, 1.6],
};

export class Vesper {
  readonly boss: Entity;
  readonly id: string;
  dim: Dimension;
  arena: V3;
  phase: number = PHASE.p1;
  t = 0; // ticks since adoption
  heading = 0;
  pitch = 0;
  bank = 0;
  lookYaw = 0;
  lookPitch = 0;
  charge = 0;
  ground = 0;
  goal: Goal = { speed: CFG.maxSpeedP1, turn: CFG.turnRateP1, accel: 0.03 };
  action?: Action;
  cooldowns = new Map<string, number>();
  gcdUntil = 60;
  lastAction = "";
  lastVulnerable = 0;
  invulnerable = false;
  heartOpen = false;
  heartMult: number = CFG.heartMult;
  heartDrop = 0; // model units the heart is lowered by the current pose
  prayers = 0; // bit 1: 75 % prayer done, bit 2: 25 % prayer done
  enraged = false;
  dying = false;
  departing = false;
  pendingDispose = false; // set by sequences; the main loop disposes after the tick
  moodP2 = false; // music / fog already switched to phase II
  pendingThreshold?: "prayer1" | "transform" | "prayer2" | "death";
  pendingLevel = 0;
  readonly participants = new Map<string, Participant>();
  players: Player[] = [];
  target?: Player;
  readonly partEntities: { [k in PartKind]?: Entity } = {};
  readonly minions = new MinionSet();
  noTargetTicks = 0;
  private lastVel: V3 = { x: 0, y: 0, z: 0 };
  private expected?: V3;
  private stuckTicks = 0;
  useTeleport = false;
  private propCache = new Map<string, number | boolean>();
  private orbitAngle = Math.random() * 360;
  readonly audience = new Set<string>(); // players currently given music + fog
  cinematic = new Map<string, number>(); // player id -> camera release tick
  private hullState = "p1";
  // pooled damage: every player's hits count (per-attacker invulnerability frames), applied every 11 ticks
  private pool = 0;
  private poolBy?: Entity;
  private poolCause: EntityDamageCause = EntityDamageCause.entityAttack;
  private lastFlush = 0;
  private attackerFrames = new Map<string, { t: number; dmg: number }>();

  constructor(boss: Entity, arena?: V3) {
    this.boss = boss;
    this.id = boss.id;
    this.dim = boss.dimension;
    this.arena = arena ?? this.restoreArena() ?? { ...boss.location };
    this.heading = boss.getRotation().y;
    this.ground = groundY(this.dim, this.arena.x, this.arena.z, this.arena.y - 1);
    const ph = boss.getProperty("sab:phase");
    this.phase = typeof ph === "number" ? ph : PHASE.p1;
    this.restoreFlags();
    bosses.set(this.id, this);
  }

  // ------------------------------------------------------------------ persistence
  private restoreArena(): V3 | undefined {
    try {
      const raw = this.boss.getDynamicProperty("sab:arena");
      if (typeof raw === "string") return JSON.parse(raw) as V3;
    } catch {
      /* ignore */
    }
    return undefined;
  }

  private restoreFlags(): void {
    try {
      const raw = this.boss.getDynamicProperty("sab:flags");
      if (typeof raw === "string") {
        const f = JSON.parse(raw) as { prayers?: number; participants?: [string, Participant][] };
        this.prayers = f.prayers ?? 0;
        for (const [k, p] of f.participants ?? []) this.participants.set(k, p);
      }
    } catch {
      /* ignore */
    }
  }

  persist(): void {
    try {
      this.boss.setDynamicProperty("sab:arena", JSON.stringify(this.arena));
      const top = [...this.participants.entries()].sort((a, b) => b[1].damage - a[1].damage).slice(0, 12);
      this.boss.setDynamicProperty("sab:flags", JSON.stringify({ prayers: this.prayers, participants: top }));
    } catch {
      /* ignore */
    }
  }

  // ------------------------------------------------------------------ properties
  prop(id: string, value: number | boolean, eps = 0): void {
    const old = this.propCache.get(id);
    if (old !== undefined) {
      if (typeof value === "number" && typeof old === "number" && Math.abs(old - value) <= eps) return;
      if (old === value) return;
    }
    this.propCache.set(id, value);
    setProp(this.boss, id, value);
  }

  setAct(name: keyof typeof ACT): void {
    this.prop("sab:act", ACT[name]);
  }

  setPhase(p: number): void {
    this.phase = p;
    this.prop("sab:phase", p);
  }

  setHull(state: "p1" | "p2" | "open"): void {
    if (this.hullState === state) return;
    this.hullState = state;
    try {
      this.boss.triggerEvent(state === "open" ? "sab:set_hull_open" : state === "p2" ? "sab:set_hull_p2" : "sab:set_hull_p1");
    } catch {
      /* ignore */
    }
  }

  openHeart(mult: number, drop: number): void {
    this.heartOpen = true;
    this.heartMult = mult;
    this.heartDrop = drop;
    this.lastVulnerable = this.t;
    this.setHull("open");
  }

  closeHeart(): void {
    this.heartOpen = false;
    this.heartDrop = this.phase >= PHASE.p2 ? 8 : 0;
    this.setHull(this.phase >= PHASE.p2 ? "p2" : "p1");
  }

  // ------------------------------------------------------------------ geometry helpers
  get pos(): V3 {
    return this.boss.location;
  }

  /** World position of a model-space point on the boss (ignores pitch/bank). */
  at(mx: number, my: number, mz: number): V3 {
    return modelToWorld(this.pos, this.heading, mx, my, mz);
  }

  core(): V3 {
    return this.at(0, 62 - this.heartDrop, -2);
  }

  prow(): V3 {
    return this.at(0, 64 - this.heartDrop * 0.5, -206);
  }

  groundPoint(): V3 {
    const p = this.pos;
    return { x: p.x, y: groundY(this.dim, p.x, p.z, this.ground, p.y), z: p.z };
  }

  health(): number {
    return this.boss.getComponent("minecraft:health")?.currentValue ?? 0;
  }

  // ------------------------------------------------------------------ participants / targeting
  credit(player: Entity | undefined, amount: number): void {
    if (!player || player.typeId !== "minecraft:player") return;
    const p = player as Player;
    const e = this.participants.get(p.id) ?? { name: p.name, damage: 0 };
    e.damage += amount;
    this.participants.set(p.id, e);
  }

  private refreshPlayers(): void {
    // whoever is near the arena or near the boss takes part; the arena drifts with the fight
    const seen = new Map<string, Player>();
    for (const p of combatants(this.dim, this.arena, CFG.arenaRange)) seen.set(p.id, p);
    for (const p of combatants(this.dim, this.pos, CFG.arenaRange)) seen.set(p.id, p);
    this.players = [...seen.values()];
    if (this.players.length && this.t % 20 === 1 && !this.dying) {
      let cx = 0;
      let cz = 0;
      for (const p of this.players) {
        cx += p.location.x;
        cz += p.location.z;
      }
      cx /= this.players.length;
      cz /= this.players.length;
      const k = hdist({ x: cx, y: 0, z: cz }, this.arena) > 24 ? 0.12 : 0.04;
      this.arena = { x: this.arena.x + (cx - this.arena.x) * k, y: this.arena.y, z: this.arena.z + (cz - this.arena.z) * k };
      this.arena.y = groundY(this.dim, this.arena.x, this.arena.z, this.arena.y, this.arena.y + 24);
    }
    for (const p of this.players) if (!this.participants.has(p.id)) this.participants.set(p.id, { name: p.name, damage: 0 });
    if (!this.target || !this.target.isValid || !this.players.includes(this.target) || Math.random() < 0.03) {
      this.target = this.pickTarget();
    }
  }

  pickTarget(prefer?: (p: Player) => number): Player | undefined {
    if (!this.players.length) return undefined;
    let best: Player | undefined;
    let bestScore = -Infinity;
    for (const p of this.players) {
      const part = this.participants.get(p.id);
      let s = (part?.damage ?? 0) * 0.02 - dist(p.location, this.pos) * 0.05 + Math.random() * 2;
      if (prefer) s += prefer(p);
      if (s > bestScore) {
        bestScore = s;
        best = p;
      }
    }
    return best;
  }

  groupScale(): number {
    return CFG.groupScale(Math.max(1, this.players.length));
  }

  // ------------------------------------------------------------------ damage model
  /** Multiplier for player damage arriving at a body part (before the per-hit cap). */
  multiplierFor(kind: PartKind | "hull", cause: EntityDamageCause): number {
    let m = this.phase >= PHASE.p2 ? CFG.hullMultP2 : CFG.hullMultP1;
    if (kind === "heart" && this.heartOpen) m = this.heartMult;
    if (cause === EntityDamageCause.blockExplosion || cause === EntityDamageCause.entityExplosion) m *= CFG.explosionMult;
    return m * this.groupScale();
  }

  /** Clamp damage so phase thresholds are never skipped; returns the allowed amount. */
  clampToThreshold(amount: number): number {
    const hp = this.health() - this.pool;
    const max = CFG.maxHealth;
    const stops: [number, "prayer1" | "transform" | "prayer2" | "death"][] = [];
    const th = CFG.thresholds;
    if (!(this.prayers & 1)) stops.push([max * th.prayer1, "prayer1"]);
    if (this.phase === PHASE.p1) stops.push([max * th.transform, "transform"]);
    if (!(this.prayers & 2) && this.phase >= PHASE.p2) stops.push([max * th.prayer2, "prayer2"]);
    stops.push([1, "death"]);
    for (const [level, name] of stops) {
      if (hp > level && hp - amount <= level) {
        this.pendingThreshold = name;
        this.pendingLevel = level;
        return Math.max(0, hp - level);
      }
    }
    if (hp <= 1) return 0;
    return amount;
  }

  /**
   * Queue already-scaled damage (hull hits, proxy hitboxes, reflected orbs, the Orison Halo).
   * Each attacker gets vanilla-like invulnerability frames (10 ticks, stronger hits add the
   * difference) so spam-clicking gains nothing, but several players' hits all count.
   * Safe to call from before-events (no world mutation here).
   */
  queueDamage(amount: number, source: Entity | undefined, cause = EntityDamageCause.entityAttack): number {
    if (this.invulnerable || this.dying) return 0;
    let a = Math.min(CFG.perHitCap, amount);
    const key = source?.id ?? `env:${cause}`;
    const f = this.attackerFrames.get(key);
    if (f && this.t - f.t < 10) {
      if (a <= f.dmg) return 0;
      const extra = a - f.dmg;
      f.dmg = a;
      a = extra;
    } else {
      this.attackerFrames.set(key, { t: this.t, dmg: a });
    }
    a = this.clampToThreshold(a);
    if (a <= 0) return 0;
    this.pool += a;
    if (source) this.poolBy = source;
    this.poolCause = cause;
    this.credit(source, a);
    return a;
  }

  /** Alias kept for helpers that forward hits. */
  forwardDamage(amount: number, source: Entity | undefined, cause = EntityDamageCause.entityAttack): number {
    return this.queueDamage(amount, source, cause);
  }

  private flushDamage(): void {
    if (this.pool <= 0 || this.t - this.lastFlush < 11) return;
    const a = Math.round(this.pool * 100) / 100;
    this.pool = 0;
    this.lastFlush = this.t;
    if (this.attackerFrames.size > 64) this.attackerFrames.clear();
    ledgerAdd(this.id, a, clock.now);
    try {
      const by = this.poolBy && this.poolBy.isValid ? this.poolBy : undefined;
      if (by) this.boss.applyDamage(a, { cause: this.poolCause, damagingEntity: by });
      else this.boss.applyDamage(a, { cause: this.poolCause });
    } catch {
      /* ignore */
    }
  }

  // ------------------------------------------------------------------ actions
  start(name: string, gen: Step, opts: { interruptible?: boolean; cleanup?: () => void; cooldown?: number } = {}): void {
    this.stop();
    this.action = { name, gen, wait: 0, started: this.t, interruptible: opts.interruptible ?? true, cleanup: opts.cleanup };
    this.lastAction = name;
    if (opts.cooldown) this.cooldowns.set(name, this.t + opts.cooldown);
  }

  /** Abort the current action (runs its cleanup). */
  stop(): void {
    const a = this.action;
    this.action = undefined;
    if (a) {
      try {
        a.cleanup?.();
      } catch (e) {
        console.warn(`[VESPER-0] cleanup of ${a.name} failed: ${e}`);
      }
      try {
        a.gen.return(undefined);
      } catch {
        /* ignore */
      }
    }
    this.charge = 0;
    this.setAct("idle");
  }

  ready(name: string): boolean {
    return (this.cooldowns.get(name) ?? 0) <= this.t;
  }

  private runAction(): void {
    const a = this.action;
    if (!a) return;
    if (a.wait > 0) {
      a.wait--;
      return;
    }
    let res: IteratorResult<number, void>;
    try {
      res = a.gen.next();
    } catch (e) {
      console.warn(`[VESPER-0] action ${a.name} crashed: ${e}`);
      this.stop();
      return;
    }
    if (this.action !== a) return; // action replaced itself
    if (res.done) {
      this.action = undefined;
      try {
        a.cleanup?.();
      } catch {
        /* ignore */
      }
      this.setAct("idle");
      this.charge = 0;
      const [lo, hi] = this.phase >= PHASE.p2 ? CFG.gcdP2 : CFG.gcdP1;
      this.gcdUntil = this.t + Math.round(rand(lo, hi) * (this.enraged ? 0.75 : 1));
      return;
    }
    a.wait = Math.max(0, (res.value ?? 1) - 1);
  }

  private chooseAction(): void {
    if (this.action || this.t < this.gcdUntil || !this.players.length || this.dying || this.departing) return;
    const pick = this.phase >= PHASE.p2 ? A.chooseP2(this) : A.chooseP1(this);
    if (pick) pick();
  }

  // ------------------------------------------------------------------ thresholds
  private handleThreshold(): void {
    const th = this.pendingThreshold;
    if (!th || this.dying) return;
    if (this.action && !this.action.interruptible) return;
    if (this.pool > 0) return; // wait for the pooled hit to land
    if (this.health() > this.pendingLevel + 0.5) {
      // the clamped hit was absorbed (e.g. invulnerability frames): wait for a real one
      this.pendingThreshold = undefined;
      return;
    }
    this.pendingThreshold = undefined;
    if (th === "prayer1") {
      this.prayers |= 1;
      S.startPrayer(this, 1);
    } else if (th === "prayer2") {
      this.prayers |= 2;
      S.startPrayer(this, 2);
    } else if (th === "transform") {
      S.startTransform(this);
    } else if (th === "death") {
      S.startDeath(this);
    }
    this.persist();
  }

  // ------------------------------------------------------------------ movement
  private defaultGoal(): void {
    const g = this.goal;
    const p2 = this.phase >= PHASE.p2;
    g.speed = p2 ? CFG.maxSpeedP2 : CFG.maxSpeedP1;
    g.turn = p2 ? CFG.turnRateP2 : CFG.turnRateP1;
    g.accel = p2 ? 0.06 : 0.03;
    g.face = undefined;
    const tgt = this.target;
    const center = tgt && tgt.isValid ? tgt.location : this.arena;
    this.orbitAngle += (p2 ? 1.2 : 0.55) * (this.enraged ? 1.4 : 1);
    const r = p2 ? CFG.orbitRadiusP2 : CFG.orbitRadiusP1;
    const a = (this.orbitAngle * Math.PI) / 180;
    let px = center.x + Math.cos(a) * r;
    let pz = center.z + Math.sin(a) * r;
    const dx = px - this.arena.x;
    const dz = pz - this.arena.z;
    const dd = Math.hypot(dx, dz);
    if (dd > CFG.leashRange) {
      px = this.arena.x + (dx / dd) * CFG.leashRange;
      pz = this.arena.z + (dz / dd) * CFG.leashRange;
    }
    g.pos = { x: px, y: -1, z: pz };
    g.alt = p2 ? CFG.altitudeP2 : CFG.altitudeP1 + Math.sin(this.t / 40) * 1.5;
  }

  private move(): void {
    const g = this.goal;
    const pos = this.pos;
    if (this.t % 10 === 0) {
      const gy = groundY(this.dim, pos.x, pos.z, this.ground, pos.y + 2);
      this.ground = this.ground * 0.5 + gy * 0.5;
    }
    let target = g.pos ? { ...g.pos } : { ...pos };
    if (!g.pos || g.pos.y < -0.5) {
      const gy = g.pos ? groundY(this.dim, target.x, target.z, this.ground, pos.y + 4) : this.ground;
      target.y = Math.max(gy, this.ground - 6) + (g.alt ?? CFG.altitudeP1);
    }
    const maxY = this.dim.heightRange.max - 18;
    target.y = Math.min(target.y, maxY);
    const to = sub(target, pos);
    const d = len(to);
    let want = d > 0.04 ? mul(norm(to), Math.min(g.speed, d * 0.14)) : { x: 0, y: 0, z: 0 };
    const dv = sub(want, this.lastVel);
    const dl = len(dv);
    if (dl > g.accel) want = add(this.lastVel, mul(dv, g.accel / dl));
    this.lastVel = want;
    // stuck detection: impulses not taking effect -> fall back to teleport steering
    if (this.expected && !this.useTeleport) {
      if (dist(this.expected, pos) > 0.6 && len(want) > 0.05) this.stuckTicks++;
      else this.stuckTicks = Math.max(0, this.stuckTicks - 1);
      if (this.stuckTicks > 40) {
        this.useTeleport = true;
        console.warn("[VESPER-0] impulse steering ineffective; using teleport steering");
      }
    }
    const far = d > 72; // only when something went badly wrong (e.g. pushed far away while unloaded)
    if (this.useTeleport || far) {
      try {
        this.boss.teleport(add(pos, far ? mul(norm(to), Math.min(d, 4)) : want), { keepVelocity: false });
      } catch {
        /* ignore */
      }
    } else {
      try {
        const cur = this.boss.getVelocity();
        this.boss.applyImpulse(sub(want, cur));
      } catch {
        this.useTeleport = true;
      }
    }
    this.expected = add(pos, want);
    // orientation
    const faceAt = g.face ?? (this.target && this.target.isValid ? this.target.location : undefined);
    let desiredYaw = this.heading;
    if (faceAt && hdist(faceAt, pos) > 1.5) desiredYaw = yawOf(sub(faceAt, pos));
    else if (len(want) > 0.08) desiredYaw = yawOf(want);
    const prev = this.heading;
    this.heading = approachAngle(this.heading, desiredYaw, g.turn);
    const turn = wrapAngle(this.heading - prev);
    this.bank += (clamp(-turn * 7, -24, 24) - this.bank) * 0.15;
    this.pitch += (clamp(-want.y * 55, -18, 18) - this.pitch) * 0.12;
    // head tracking
    if (this.target && this.target.isValid) {
      const head = this.at(0, 76, -140);
      const tv = sub(this.target.getHeadLocation(), head);
      this.lookYaw += (clamp(wrapAngle(yawOf(tv) - this.heading), -55, 55) - this.lookYaw) * 0.2;
      this.lookPitch += (clamp(pitchOf(tv), -40, 40) - this.lookPitch) * 0.2;
    } else {
      this.lookYaw *= 0.9;
      this.lookPitch *= 0.9;
    }
    try {
      this.boss.setRotation({ x: 0, y: this.heading });
    } catch {
      /* ignore */
    }
  }

  private syncProps(): void {
    this.prop("sab:heading", Math.round(this.heading * 4) / 4, 0.2);
    this.prop("sab:pitch", Math.round(this.pitch * 4) / 4, 0.2);
    this.prop("sab:bank", Math.round(this.bank * 4) / 4, 0.2);
    this.prop("sab:look_yaw", Math.round(this.lookYaw * 2) / 2, 0.4);
    this.prop("sab:look_pitch", Math.round(this.lookPitch * 2) / 2, 0.4);
    this.prop("sab:charge", Math.round(clamp(this.charge, 0, 1) * 50) / 50, 0.01);
    this.prop("sab:shield", this.invulnerable);
    this.prop("sab:enrage", this.enraged);
  }

  // ------------------------------------------------------------------ proxy hitboxes
  private syncParts(): void {
    for (const kind of ["prow", "stern", "heart"] as PartKind[]) {
      let e = this.partEntities[kind];
      const [mx, my, mz, half] = PART_OFFSET[kind];
      const drop = kind === "heart" ? this.heartDrop : this.heartDrop * 0.6;
      const c = this.at(mx, my - drop, mz);
      const loc = { x: c.x, y: c.y - half, z: c.z };
      if (!e || !e.isValid) {
        if (this.t % 20 !== 0) continue;
        try {
          e = this.dim.spawnEntity(ENT.part, loc, { spawnEvent: `sab:as_${kind}` });
          e.setDynamicProperty("sab:owner", this.id);
          this.partEntities[kind] = e;
          parts.set(e.id, { owner: this, kind });
        } catch {
          continue;
        }
      }
      try {
        if (dist(e.location, loc) > 0.05) e.teleport(loc, { keepVelocity: false });
      } catch {
        /* ignore */
      }
    }
  }

  removeParts(): void {
    for (const kind of ["prow", "stern", "heart"] as PartKind[]) {
      const e = this.partEntities[kind];
      if (e) parts.delete(e.id);
      safeRemove(e);
      this.partEntities[kind] = undefined;
    }
  }

  // ------------------------------------------------------------------ audience: music, fog, cinematic
  private syncAudience(): void {
    if (this.t % 20 !== 0) return;
    const near = spectators(this.dim, this.pos, CFG.arenaRange + 16);
    const ids = new Set(near.map((p) => p.id));
    for (const p of near) {
      if (!this.audience.has(p.id)) {
        this.audience.add(p.id);
        this.applyMood(p);
      }
    }
    for (const id of [...this.audience]) {
      if (!ids.has(id)) {
        this.audience.delete(id);
        const p = world.getEntity(id);
        if (p && p.typeId === "minecraft:player") this.clearMood(p as Player);
      }
    }
  }

  applyMood(p: Player): void {
    try {
      p.playMusic(this.moodP2 || this.phase >= PHASE.p2 ? MUSIC.vesper_p2 : MUSIC.vesper_p1, { loop: true, fade: 2.0, volume: 0.7 });
    } catch {
      /* ignore */
    }
    try {
      p.fogSettings.remove("sab_vesper");
      p.fogSettings.push(this.moodP2 || this.phase >= PHASE.p2 ? FOGS.p2 : FOGS.p1, "sab_vesper");
    } catch {
      /* ignore */
    }
  }

  clearMood(p: Player): void {
    try {
      p.stopMusic();
    } catch {
      /* ignore */
    }
    try {
      p.fogSettings.remove("sab_vesper");
    } catch {
      /* ignore */
    }
    this.releaseCamera(p);
  }

  refreshMood(): void {
    for (const id of this.audience) {
      const p = world.getEntity(id);
      if (p && p.typeId === "minecraft:player") this.applyMood(p as Player);
    }
  }

  releaseCamera(p: Player): void {
    if (!this.cinematic.has(p.id)) return;
    this.cinematic.delete(p.id);
    try {
      p.camera.clear();
      p.onScreenDisplay.setHudVisibility(HudVisibility.Reset);
    } catch {
      /* ignore */
    }
  }

  // ------------------------------------------------------------------ main tick
  tick(): void {
    if (!this.boss.isValid) {
      this.dispose(false);
      return;
    }
    this.t++;
    this.dim = this.boss.dimension;
    if (this.t % 5 === 1) this.refreshPlayers();
    else this.players = this.players.filter((p) => p.isValid);
    if (this.target && !this.target.isValid) this.target = this.players[0];
    if (this.t === 1) this.closeHeart();
    this.flushDamage();
    this.handleThreshold();
    // leaving when nobody fights
    if (!this.players.length && !this.dying) {
      this.noTargetTicks++;
      if (this.noTargetTicks > CFG.departAfterTicks && !this.departing) S.startDepart(this);
    } else {
      this.noTargetTicks = 0;
    }
    if (!this.action) this.chooseAction();
    if (!this.action) this.defaultGoal();
    this.runAction();
    this.move();
    this.syncProps();
    this.syncParts();
    this.minions.tick(this);
    this.checkUnhaloed();
    this.syncAudience();
    for (const [pid, until] of this.cinematic) {
      if (this.t >= until) {
        const p = world.getEntity(pid);
        if (p && p.typeId === "minecraft:player") this.releaseCamera(p as Player);
        else this.cinematic.delete(pid);
      }
    }
    if (!this.enraged && this.phase >= PHASE.p2 && this.health() < CFG.maxHealth * CFG.thresholds.enrage) {
      this.enraged = true;
      sound(this.dim, "roar", this.pos, 2.0, 0.8);
    }
    if (this.t % 100 === 0) this.persist();
    if (this.t % 40 === 0 && this.phase >= PHASE.p2 && !this.dying) particle(this.dim, "ember_drip", this.core());
  }

  private checkUnhaloed(): void {
    if (this.phase !== PHASE.p2 || this.dying || this.invulnerable || !this.ready("unhaloed")) return;
    if (this.action && !this.action.interruptible) return;
    const ser = this.minions.of<Seraph>("seraph");
    if (ser.length >= 3 && ser.every((s) => s.mode === 3)) S.startUnhaloed(this);
  }

  /** Remove the controller (and optionally the entity). */
  dispose(removeEntity: boolean): void {
    this.stop();
    this.minions.clear();
    this.removeParts();
    for (const id of this.audience) {
      const p = world.getEntity(id);
      if (p && p.typeId === "minecraft:player") this.clearMood(p as Player);
    }
    this.audience.clear();
    if (removeEntity) safeRemove(this.boss);
    bosses.delete(this.id);
  }

  addMinion(m: Minion): void {
    this.minions.add(m);
  }
}
