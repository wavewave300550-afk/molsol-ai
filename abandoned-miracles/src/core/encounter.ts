/**
 * Encounter - one boss fight, from summoning to remnant.
 *
 * An Encounter owns every piece of transient state a fight has: its timeline,
 * hazards, participants, helper entities, RNG and state machine. Nothing about
 * a fight lives in module-level variables, which is what keeps simultaneous
 * encounters independent and makes "end the encounter" a complete cleanup.
 */
import { Dimension, Entity, EntityHealthComponent, EntityHurtBeforeEvent, Player } from "@minecraft/server";
import { BossBaseStats, BossKey, CONFIG, difficulty } from "../config";
import { Arena } from "./arena";
import { Audio } from "./audio";
import { AnimState, AttackDef, AttackRun, BossController, ControllerFactory } from "./boss";
import { DamageSystem } from "./damage";
import { HazardSystem } from "./hazards";
import { Helpers } from "./helpers";
import { clearHud, renderHud } from "./hud";
import { Locomotion } from "./locomotion";
import { Rng, hashString } from "./math";
import { BossRecord, REMNANT_TAG, saveRecord } from "./persistence";
import { grantRewards } from "./rewards";
import { AttackScheduler } from "./scheduler";
import { BossStateMachine, Sub, Top } from "./stateMachine";
import { Targeting } from "./targeting";
import { Timeline } from "./timeline";
import { report, trace } from "./trace";
import { Visuals } from "./visuals";

/** Damage causes a Miracle simply ignores. */
const IGNORED_CAUSES = new Set<string>([
  "fall", "suffocation", "drowning", "contact", "fire", "fireTick", "lava", "magma", "freezing",
  "lightning", "stalactite", "stalagmite", "flyIntoWall", "fallingBlock", "anvil", "campfire",
  "soulCampfire", "temperature", "piston", "starve", "wither",
]);
const EXPLOSION_CAUSES = new Set<string>(["blockExplosion", "entityExplosion", "fireworks"]);

export type EndReason = "defeated" | "abandoned" | "unloaded" | "killed" | "cancelled";

export interface EncounterHost {
  /** The encounter is over; forget it. */
  release(enc: Encounter, reason: EndReason): void;
  /** Nobody is left: despawn the boss and (optionally) return the seal. */
  abandon(enc: Encounter): void;
}

export class Encounter {
  readonly stats: BossBaseStats;
  readonly dim: Dimension;
  readonly arena: Arena;
  readonly timeline = new Timeline();
  readonly sm: BossStateMachine;
  readonly rng: Rng;
  readonly visuals: Visuals;
  readonly audio: Audio;
  readonly hazards: HazardSystem;
  readonly damage: DamageSystem;
  readonly targeting: Targeting;
  readonly helpers: Helpers;
  readonly scheduler: AttackScheduler;
  readonly loco: Locomotion;
  readonly controller: BossController;
  /** Entity id, kept separately so it stays readable after the entity is gone. */
  readonly bossId: string;

  phase: 1 | 2 = 1;
  /** Effective HP = native HP * hpScale (multiplayer and difficulty). */
  hpScale = 1;
  currentAttackName = "";
  nextAttackAt = 0;
  ended = false;
  /** While true every hit on the boss is refused (intro, phase change, death). */
  invulnerable = true;

  private run: AttackRun | undefined;
  private runSeq = 0;
  private pendingTransition = false;
  private pendingDeath = false;
  private emptySince = -1;
  private staggerUntil = 0;
  private deferred: Array<() => void> = [];
  private props = new Map<string, number | boolean | string>();
  private outsiderNote = new Map<string, number>();
  private record: BossRecord;

  constructor(
    readonly boss: Entity,
    readonly key: BossKey,
    private readonly host: EncounterHost,
    factory: ControllerFactory,
    record?: BossRecord,
  ) {
    this.stats = CONFIG.bosses[key];
    this.bossId = boss.id;
    this.dim = boss.dimension;
    const l = boss.location;
    this.record = record ?? {
      v: 1, boss: key, cx: l.x, cy: l.y, cz: l.z, phase: 1, scale: 1,
      seed: hashString(boss.id) ^ ((Math.random() * 0xffffffff) >>> 0), engaged: false, extra: {},
    };
    this.arena = new Arena({ x: this.record.cx, y: this.record.cy, z: this.record.cz }, this.stats);
    this.sm = new BossStateMachine(key);
    this.rng = new Rng(this.record.seed);
    this.visuals = new Visuals(this.dim);
    this.audio = new Audio(this.dim);
    this.targeting = new Targeting(this.dim, this.arena);
    this.damage = new DamageSystem(() => (this.boss.isValid ? this.boss : undefined));
    this.hazards = new HazardSystem(this);
    this.helpers = new Helpers(this);
    this.scheduler = new AttackScheduler(this);
    this.loco = new Locomotion(this);
    this.controller = factory(this);
    this.hpScale = this.record.scale > 0 ? this.record.scale : 1;
  }

  // ------------------------------------------------------------------ small utilities

  /** Set a synced entity property (skipped when unchanged). */
  setProp(name: string, value: number | boolean | string): void {
    if (this.props.get(name) === value) return;
    this.props.set(name, value);
    try {
      this.boss.setProperty(name, value);
    } catch (e) {
      report(`setProperty ${name}`, e);
    }
  }

  setAnim(state: number, variant = 0): void {
    this.setProp("abm:variant", variant);
    this.setProp("abm:anim", state);
  }

  /** Queue a world-changing action from a restricted (before-event) context. */
  defer(fn: () => void): void {
    this.deferred.push(fn);
  }

  private health(): EntityHealthComponent | undefined {
    return this.boss.getComponent("minecraft:health") as EntityHealthComponent | undefined;
  }

  effectiveHealth(): number {
    if (this.pendingDeath || this.sm.top === Top.Death) return 0;
    return (this.health()?.currentValue ?? 0) * this.hpScale;
  }

  effectiveMaxHealth(): number {
    return (this.health()?.effectiveMax ?? this.stats.health) * this.hpScale;
  }

  healthFraction(): number {
    const h = this.health();
    return h ? h.currentValue / Math.max(1, h.effectiveMax) : 0;
  }

  get currentAttack(): AttackDef | undefined {
    return this.run?.def;
  }

  save(): void {
    this.record.phase = this.phase;
    this.record.scale = this.hpScale;
    this.record.extra = this.controller.extra();
    saveRecord(this.boss, this.record);
  }

  /** Multiplayer scaling: grows with the peak participant count, never shrinks mid-fight. */
  private updateScale(): void {
    const n = Math.min(CONFIG.encounter.maxScaledPlayers, Math.max(1, this.targeting.peak));
    const want = difficulty().health * (1 + CONFIG.encounter.hpPerExtraPlayer * (n - 1));
    if (want > this.hpScale + 1e-6 || (!this.record.engaged && Math.abs(want - this.hpScale) > 1e-6)) {
      this.hpScale = want;
      trace("scale", { boss: this.key, players: n, scale: want });
    }
  }

  // ------------------------------------------------------------------ lifecycle

  /** Begin (or resume) the fight. */
  start(): void {
    this.setProp("abm:phase", this.record.phase);
    this.controller.restore(this.record.extra ?? {});
    this.targeting.refresh(0, true);
    if (this.record.engaged) {
      // resumed after a reload: no intro, no hazards pending, correct phase
      this.phase = this.record.phase;
      this.controller.configure(this.phase);
      this.sm.restore(this.phase, 0);
      this.invulnerable = false;
      this.setAnim(AnimState.None);
      this.nextAttackAt = 40;
      trace("resume", { boss: this.key, phase: this.phase });
      return;
    }
    this.updateScale();
    this.controller.configure(1);
    this.invulnerable = true;
    this.setAnim(AnimState.Intro);
    const ticks = this.controller.intro();
    trace("intro", { boss: this.key, ticks });
    this.timeline.after(ticks, () => {
      this.sm.setTop(Top.Phase1, this.timeline.now);
      this.invulnerable = false;
      this.setAnim(AnimState.None);
      this.record.engaged = true;
      this.nextAttackAt = this.timeline.now + 30;
      for (const a of this.controller.attacks) if (a.ultimate) this.scheduler.hold(a, 420);
      this.save();
    }, "intro");
  }

  tick(): void {
    if (this.ended) return;
    if (!this.boss.isValid) {
      this.host.release(this, "unloaded");
      return;
    }
    this.timeline.step();
    if (this.ended) return;
    if (this.deferred.length > 0) {
      const d = this.deferred;
      this.deferred = [];
      for (const f of d) {
        try {
          f();
        } catch (e) {
          report("deferred", e);
        }
      }
    }
    const now = this.timeline.now;
    this.targeting.refresh(now);
    this.updateScale();
    this.helpers.tick();
    try {
      this.controller.tick();
      if (this.sm.inCombat) this.combat(now);
    } catch (e) {
      report(`${this.key} tick`, e);
    }
    if (now % CONFIG.hud.intervalTicks === 0) renderHud(this);
    if (now % 100 === 0 && this.sm.inCombat) this.save();
  }

  private combat(now: number): void {
    if (this.pendingDeath) {
      this.beginDeath();
      return;
    }
    if (this.targeting.count() === 0) {
      if (this.sm.sub !== Sub.Reset) {
        this.cancelAttack();
        this.sm.setSub(Sub.Reset, now);
        this.setAnim(AnimState.None);
        this.emptySince = now;
        trace("reset_wait", { boss: this.key });
      } else if (now - this.emptySince >= CONFIG.encounter.resetGraceTicks) {
        this.host.abandon(this);
        return;
      }
      this.loco.goTo({ x: this.arena.cx, z: this.arena.cz }, 1.2);
      return;
    }
    if (this.sm.sub === Sub.Reset) {
      this.sm.setSub(Sub.Idle, now);
      this.nextAttackAt = now + 30;
    }
    if (this.pendingTransition && this.sm.top === Top.Phase1) {
      if (!this.run || this.run.def.interruptible !== false) {
        this.beginTransition();
        return;
      }
    }
    switch (this.sm.sub) {
      case Sub.Stagger:
        if (now >= this.staggerUntil) {
          this.sm.setSub(Sub.Idle, now);
          this.setAnim(AnimState.None);
          this.nextAttackAt = Math.max(this.nextAttackAt, now + 10);
        }
        break;
      case Sub.Idle:
      case Sub.Positioning: {
        if (now % 20 === 0) this.loco.enforceLeash();
        const target = this.targeting.primary(now);
        const moving = this.controller.position(target);
        this.sm.setSub(moving ? Sub.Positioning : Sub.Idle, now);
        if (now >= this.nextAttackAt) {
          const atk = this.scheduler.choose(this.controller.attacks);
          if (atk) this.startAttack(atk);
          else this.nextAttackAt = now + 8;
        }
        break;
      }
      default:
        break; // an attack is running; its timeline drives the substate
    }
  }

  // ------------------------------------------------------------------ attacks

  startAttack(def: AttackDef): boolean {
    if (!this.sm.inCombat || this.sm.busy || this.sm.sub === Sub.Stagger) return false;
    const now = this.timeline.now;
    this.loco.halt();
    const run = new AttackRun(this, def, ++this.runSeq);
    this.run = run;
    this.currentAttackName = def.name;
    this.scheduler.commit(def);
    this.setAnim(def.index, 0);
    this.sm.setSub(Sub.Telegraph, now);
    try {
      def.run(run);
      if (!run.hasWindows) throw new Error(`${def.id} did not declare its windows`);
    } catch (e) {
      report(`attack ${def.id}`, e);
      this.cancelAttack();
      this.nextAttackAt = now + 20;
      return false;
    }
    return true;
  }

  finishAttack(run: AttackRun): void {
    if (this.run !== run) return;
    const now = this.timeline.now;
    this.run = undefined;
    this.currentAttackName = "";
    this.scheduler.release(run.def);
    this.setAnim(AnimState.None);
    this.sm.setSub(Sub.Idle, now);
    this.nextAttackAt = now + Math.round(CONFIG.encounter.baseAttackGap * difficulty().attackGap * (this.phase === 2 ? 0.8 : 1));
  }

  /** Abort the running attack: every pending strike of it is removed. */
  cancelAttack(): void {
    const run = this.run;
    if (!run) return;
    run.cancelled = true;
    this.timeline.cancel(run.tag);
    this.run = undefined;
    this.currentAttackName = "";
    this.scheduler.release(run.def);
    try {
      this.controller.onAttackCancelled(run.def);
    } catch (e) {
      report("onAttackCancelled", e);
    }
    this.setAnim(AnimState.None);
    if (this.sm.busy) this.sm.setSub(Sub.Idle, this.timeline.now);
    trace("attack_cancelled", { boss: this.key, id: run.def.id });
  }

  /** Knock the boss out of what it is doing for `ticks`. Returns false if it could not be staggered. */
  stagger(ticks: number): boolean {
    if (!this.sm.inCombat || this.sm.sub === Sub.Reset) return false;
    if (this.run && this.run.def.interruptible === false) return false;
    const now = this.timeline.now;
    this.cancelAttack();
    this.loco.halt();
    this.sm.setSub(Sub.Stagger, now);
    this.staggerUntil = now + ticks;
    this.setAnim(AnimState.Stagger);
    trace("stagger", { boss: this.key, ticks });
    return true;
  }

  // ------------------------------------------------------------------ phase change and death

  private beginTransition(): void {
    const now = this.timeline.now;
    this.pendingTransition = false;
    this.cancelAttack();
    if (!this.sm.setTop(Top.Transition, now)) return;
    this.invulnerable = true;
    this.loco.halt();
    this.setAnim(AnimState.Transition);
    const ticks = this.controller.phaseTransition();
    this.timeline.after(ticks, () => {
      const t = this.timeline.now;
      this.phase = 2;
      this.setProp("abm:phase", 2);
      this.sm.setTop(Top.Phase2, t);
      this.invulnerable = false;
      this.setAnim(AnimState.None);
      this.controller.configure(2);
      this.controller.phase2Ready();
      this.scheduler.refresh(60);
      this.nextAttackAt = t + 24;
      this.save();
    }, "phase");
  }

  private beginDeath(): void {
    const now = this.timeline.now;
    this.pendingDeath = false;
    this.cancelAttack();
    this.timeline.cancelAll();
    this.helpers.removeAll();
    if (!this.sm.setTop(Top.Death, now)) return;
    this.invulnerable = true;
    this.loco.halt();
    this.setAnim(AnimState.Death);
    try {
      this.boss.triggerEvent("abm:hide_bar");
    } catch (e) {
      report("hide_bar", e);
    }
    const ticks = this.controller.death();
    this.timeline.after(ticks, () => {
      grantRewards(this);
      try {
        this.boss.addTag(REMNANT_TAG);
        this.boss.triggerEvent("abm:become_remnant");
      } catch (e) {
        report("remnant", e);
      }
      this.host.release(this, "defeated");
    }, "death");
  }

  /** The boss entity died natively (e.g. /kill): skip the sequence, still clean up. */
  onNativeDeath(): void {
    if (this.ended) return;
    trace("native_death", { boss: this.key });
    this.host.release(this, "killed");
  }

  /** Final cleanup. Idempotent. */
  end(reason: EndReason): void {
    if (this.ended) return;
    this.ended = true;
    this.timeline.cancelAll();
    this.deferred = [];
    this.helpers.removeAll();
    try {
      this.controller.cleanup();
    } catch (e) {
      report("controller.cleanup", e);
    }
    clearHud(this);
    this.damage.clear();
    trace("end", { boss: this.key, reason, pendingTasks: this.timeline.pending() });
  }

  // ------------------------------------------------------------------ damage intake (before-event: read-only context)

  onHurtBefore(ev: EntityHurtBeforeEvent): void {
    if (this.ended) return;
    if (this.invulnerable || !this.sm.inCombat || this.pendingDeath) {
      ev.cancel = true;
      return;
    }
    const src = ev.damageSource;
    const cause = String(src.cause);
    if (IGNORED_CAUSES.has(cause)) {
      ev.cancel = true;
      return;
    }
    const attacker = src.damagingEntity;
    const player = attacker instanceof Player ? attacker : undefined;
    if (attacker && this.helpers.owns(attacker.id)) {
      ev.cancel = true;
      return;
    }
    if (player && CONFIG.encounter.blockOutsideDamage && !this.targeting.isParticipant(player)) {
      ev.cancel = true;
      this.noteOutsider(player);
      return;
    }
    let dmg = ev.damage;
    if (EXPLOSION_CAUSES.has(cause)) dmg *= 0.3;
    dmg = this.controller.incoming(dmg, { attacker, player, projectile: src.damagingProjectile, cause });
    const h = this.health();
    if (!h || dmg <= 0) {
      ev.cancel = true;
      return;
    }
    dmg = Math.min((dmg * this.stats.damageTaken) / this.hpScale, h.effectiveMax * CONFIG.encounter.maxHitFraction);
    const hp = h.currentValue;
    if (this.phase === 1) {
      const gate = h.effectiveMax * this.stats.phase2At;
      if (hp - dmg <= gate) {
        // Phase II can never be skipped: health stops exactly at the threshold
        dmg = Math.max(0, hp - gate);
        this.pendingTransition = true;
      }
    } else if (hp - dmg <= 0.5) {
      // keep the entity alive so the death sequence can play on it
      this.pendingDeath = true;
      if (player) this.targeting.addThreat(player.id, hp * this.hpScale);
      ev.cancel = true;
      return;
    }
    if (dmg < 0.001) {
      ev.cancel = true;
      return;
    }
    ev.damage = dmg;
    if (player) this.targeting.addThreat(player.id, dmg * this.hpScale);
  }

  private noteOutsider(p: Player): void {
    const now = this.timeline.now;
    if (now - (this.outsiderNote.get(p.id) ?? -999) < 100) return;
    this.outsiderNote.set(p.id, now);
    this.defer(() => {
      try {
        p.sendMessage({ rawtext: [{ translate: "abm.msg.outside" }] });
      } catch {
        /* player left */
      }
    });
  }

  /** Debug / test hook: request the phase change or the death without dealing damage. */
  force(what: "phase2" | "death"): void {
    if (what === "phase2" && this.sm.top === Top.Phase1) this.pendingTransition = true;
    if (what === "death" && this.sm.inCombat) this.pendingDeath = true;
  }
}
