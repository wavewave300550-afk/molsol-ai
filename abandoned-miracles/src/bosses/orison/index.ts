/**
 * Boss 004 - Orison, The Witness of Tomorrow.
 *
 * A mid-range fight about memory and consequence. Orison keeps a small, bounded
 * record of where each fighter has recently stood (history.ts) and builds its
 * attacks from it: it detonates the trail you left, extrapolates where you are
 * heading, and shows three patterns it will only perform later. Nothing here
 * touches time itself - every "temporal" effect is a stored position, a locked
 * prediction, or an event scheduled on the encounter timeline.
 *
 * Phase II (Tomorrow Has Already Happened) breaks the hourglass and frees the
 * shadow: from then on the shadow moves first and the body follows the same
 * path a moment later.
 */
import { Player, world } from "@minecraft/server";
import T from "../../../shared/orison.timings.json";
import { BossKey } from "../../config";
import { AttackDef, AttackRun, BossController, BossModule, IncomingInfo } from "../../core/boss";
import type { Encounter } from "../../core/encounter";
import type { Helper } from "../../core/helpers";
import { V3, XZ, dirToTheta, dirToYaw, distXZ, localToWorld, thetaToDir, yawToTheta } from "../../core/math";
import { Circle, Ring, sector } from "../../core/shapes";
import { isAlivePlayer } from "../../core/targeting";
import { trace } from "../../core/trace";
import { TelegraphStyle } from "../../core/visuals";
import { PositionHistory } from "./history";
import { Pattern, PatternShape, choosePatterns, patternLabel } from "./patterns";
import { ORISON as O } from "./tuning";

const S = (id: string): string => `abm.orison.${id}`;
const P = (id: string): string => `abm:orison_${id}`;
const NUMERAL = [P("numeral_1"), P("numeral_2"), P("numeral_3")];

type Beats = Record<string, number>;
const beats = (name: keyof typeof T, phase: 1 | 2): Beats =>
  (T[name] as unknown as Record<string, Beats>)[phase === 2 ? "p2" : "p1"];

const live = (p: Player | undefined): Player | undefined => (isAlivePlayer(p) ? p : undefined);

/** Shadow animation states (synced as abm:anim on the shadow entity). */
const enum Shade {
  Idle = 0,
  Strike = 1,
  Point = 2,
  Sink = 3,
}

export class OrisonController extends BossController {
  readonly key: BossKey = "orison";
  readonly displayName = "Orison";
  readonly phase2Name = "Tomorrow Has Already Happened";
  readonly trophyItem = "abm:unlived_hourglass";
  readonly style: TelegraphStyle = {
    line: P("tg_line"), arc: P("tg_arc"), disc: P("tg_disc"),
    safeLine: P("safe_line"), safeArc: P("safe_arc"), strike: P("strike"),
  };
  readonly attacks: readonly AttackDef[];
  /** Recent positions of the participants. Bounded; see history.ts. */
  readonly history = new PositionHistory();
  /** The three patterns of the most recent ultimate, and what was actually executed. */
  lastHour: { previewed: string[]; executed: string[] } = { previewed: [], executed: [] };
  /** The spots locked by the most recent Tomorrow's Witness. */
  lastPrediction: XZ[] = [];

  /** 1 once the chest hourglass has shattered (Phase II). */
  private glass = 0;
  /** Phase II: positions the shadow has walked through, oldest first (a delay line of `lead` ticks). */
  private trail: XZ[] = [];
  /** While the encounter clock is below this the shadow is on an errand and does not lead. */
  private shadowBusyUntil = 0;
  private shadowAt: XZ | undefined;
  private nextIdleSound = 100;
  private readonly onLeave: (ev: { playerId: string }) => void;

  constructor(enc: Encounter) {
    super(enc);
    this.attacks = [
      this.footstepEcho(), this.pendulumVerdict(), this.deferredWound(), this.hourglassDrain(),
      this.tomorrowsWitness(), this.secondhandExchange(), this.hourThatNeverOccurred(),
    ];
    // a player who leaves the world is forgotten immediately
    this.onLeave = (ev) => this.history.forget(ev.playerId);
    world.afterEvents.playerLeave.subscribe(this.onLeave);
  }

  // ------------------------------------------------------------------ framework hooks

  configure(phase: 1 | 2): void {
    const m = phase === 2 ? O.move.p2 : O.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }

  intro(): number {
    return T.intro.total;
  }

  phaseTransition(): number {
    const e = this.enc;
    const t = T.transition;
    e.timeline.after(t.shatter, () => {
      this.glass = 1;
      e.setProp("abm:glass", 1);
      const chest = localToWorld(e.boss.location, e.loco.yaw, 0, 5.6, 0.5);
      e.visuals.spawn(P("shard"), chest);
      e.visuals.spawn(P("sand"), chest);
      // the burst pushes everyone near it back a step; no damage
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 5))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: ((p.location.x - c.x) / d) * 1.4, z: ((p.location.z - c.z) / d) * 1.4 }, 0.3);
        } catch {
          /* player left */
        }
      }
    }, "phase");
    e.timeline.after(t.emerge, () => {
      this.ensureShadow();
    }, "phase");
    return t.total;
  }

  phase2Ready(): void {
    this.trail = [];
    this.shadowBusyUntil = 0;
    this.ensureShadow();
  }

  death(): number {
    const e = this.enc;
    const t = T.death;
    // the shadow is already gone (helpers are removed when death begins): it leaves before the body does
    if (this.shadowAt) {
      const at = e.arena.at(this.shadowAt, 1.5);
      e.visuals.spawn(P("wisp"), at);
      e.visuals.spawn(P("wisp"), { x: at.x, y: at.y + 1.5, z: at.z });
    }
    this.shadowAt = undefined;
    // the body repeats its last verdict, but no echo answers it: only a wisp that fails to form
    e.timeline.after(t.repeat, () => {
      const f = localToWorld(e.boss.location, e.loco.yaw, 0, 0.2, 4);
      e.visuals.decor(P("echo"), f);
    }, "death");
    e.timeline.after(t.empty, () => e.visuals.spawn(P("sand"), localToWorld(e.boss.location, e.loco.yaw, 0, 5.2, 0.5)), "death");
    return t.total;
  }

  position(target: Player | undefined): boolean {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const b = e.boss.location;
    const d = distXZ(b, target.location);
    if (e.phase === 2) return this.followShadow(target, d);
    const m = O.move.p1;
    if (d > m.chase) {
      // tick-tock: a few strides, then a held pause, like a second hand
      const beat = e.timeline.now % (m.stride + m.rest);
      if (beat < m.stride) {
        const k = (d - m.hold) / d;
        e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
        return true;
      }
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }

  tick(): void {
    const e = this.enc;
    const now = e.timeline.now;
    this.history.record(e.targeting.participants(), now);
    if (!e.sm.inCombat) return;
    this.tickDrains(now);
    if (e.phase === 2) this.tickShadow(now);
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 150 + e.rng.int(0, 120);
    }
  }

  incoming(damage: number, _info: IncomingInfo): number {
    const e = this.enc;
    e.defer(() => e.audio.play(S("hurt"), e.boss.location, 0.7));
    return damage;
  }

  onHelperGone(h: Helper): void {
    const e = this.enc;
    if (h.kind === "drain") {
      e.timeline.cancel(`hg${h.id}`);
      if (h.killed) {
        const at = e.arena.at({ x: h.data.x, z: h.data.z }, 1.2);
        e.visuals.spawn(P("shard"), at);
        e.visuals.spawn(P("sand"), at);
        e.audio.play(S("hourglass_break"), at);
        // breaking its time jams the mechanism for a moment
        e.stagger(O.drain.breakStagger);
      }
    }
  }

  onAttackCancelled(_def: AttackDef): void {
    this.enc.helpers.removeKind("mark");
    this.shadowBusyUntil = 0;
    this.trail = [];
    const sh = this.shadow();
    if (sh) this.shade(sh, Shade.Idle);
  }

  extra(): Record<string, number> {
    return { glass: this.glass };
  }

  restore(extra: Record<string, number>): void {
    this.glass = extra.glass === 1 ? 1 : 0;
    this.enc.setProp("abm:glass", this.glass);
  }

  cleanup(): void {
    this.history.clear();
    this.trail = [];
    this.lastPrediction = [];
    try {
      world.afterEvents.playerLeave.unsubscribe(this.onLeave);
    } catch {
      /* already unsubscribed */
    }
  }

  // ------------------------------------------------------------------ shared helpers

  private dist(e: Encounter): number {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }

  private front(): number {
    return yawToTheta(this.enc.loco.yaw);
  }

  private floor(lift = 0.07): number {
    return this.enc.arena.floorY + lift;
  }

  /** Rising numeral over a mark: III, II, I. A countdown that does not depend on colour. */
  private numeral(n: number, at: XZ): void {
    if (n < 1 || n > 3) return;
    this.enc.visuals.spawn(NUMERAL[n - 1], { x: at.x, y: this.floor(1.1), z: at.z });
  }

  private shade(h: Helper, state: Shade): void {
    try {
      if (h.entity.isValid) h.entity.setProperty("abm:anim", state);
    } catch {
      /* gone */
    }
  }

  // ------------------------------------------------------------------ the shadow (Phase II)

  /** The persistent shadow, if it currently exists. */
  private shadow(): Helper | undefined {
    return this.enc.helpers.of("shadow")[0];
  }

  private ensureShadow(): Helper | undefined {
    const e = this.enc;
    let sh = this.shadow();
    if (sh) return sh;
    const at = localToWorld(e.boss.location, e.loco.yaw, 2.5, 0, 0);
    const p = e.arena.clampInside(at.x, at.z, 1);
    sh = e.helpers.spawn("abm:orison_shadow", e.arena.at(p, 0.05), "shadow", { yaw: e.loco.yaw });
    if (sh) {
      this.shadowAt = p;
      this.trail = [];
      e.visuals.decor(P("wisp"), e.arena.at(p, 1));
    }
    return sh;
  }

  /** Move a helper towards a point at `speed` blocks per tick (velocity steering, like the boss). */
  private glide(h: Helper, goal: XZ, speed: number): number {
    const l = h.entity.location;
    const dx = goal.x - l.x;
    const dz = goal.z - l.z;
    const d = Math.hypot(dx, dz);
    try {
      const v = h.entity.getVelocity();
      const step = Math.min(speed, d);
      const k = d > 0.05 ? step / d : 0;
      h.entity.applyImpulse({ x: dx * k - v.x, y: 0, z: dz * k - v.z });
      if (d > 0.05) h.entity.setRotation({ x: 0, y: dirToYaw(dx, dz) });
    } catch {
      /* gone */
    }
    return d;
  }

  /** Phase II locomotion: the echo goes first, the body follows where the echo was `lead` ticks ago. */
  private followShadow(target: Player, d: number): boolean {
    const e = this.enc;
    const m = O.move.p2;
    const b = e.boss.location;
    const sh = this.shadow();
    const now = e.timeline.now;
    if (!sh || now < this.shadowBusyUntil) {
      // no shadow to lead (it is on an errand): walk plainly
      if (d > m.chase) {
        const k = (d - m.hold) / d;
        e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
        return true;
      }
      e.loco.halt();
      e.loco.turnToward(e.loco.yawTo(target.location), 3);
      return false;
    }
    const sl = sh.entity.location;
    let goal: XZ = { x: sl.x, z: sl.z };
    const ds = distXZ(sl, target.location);
    if (ds > m.hold + 0.5) {
      const k = (ds - m.hold) / ds;
      goal = { x: sl.x + (target.location.x - sl.x) * k, z: sl.z + (target.location.z - sl.z) * k };
    }
    goal = e.arena.clampInside(goal.x, goal.z, e.stats.leashInset);
    this.glide(sh, goal, m.speed);
    this.shadowAt = { x: sl.x, z: sl.z };
    this.trail.push({ x: sl.x, z: sl.z });
    let follow: XZ | undefined;
    while (this.trail.length > m.lead) follow = this.trail.shift();
    if (follow && Math.hypot(follow.x - b.x, follow.z - b.z) > 0.7) {
      e.loco.goTo(follow, 0.4);
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }

  /** Keep the shadow alive and, while the body is busy, parked at its side. */
  private tickShadow(now: number): void {
    const e = this.enc;
    const sh = this.ensureShadow();
    if (!sh) return;
    const l = sh.entity.location;
    this.shadowAt = { x: l.x, z: l.z };
    if (now < this.shadowBusyUntil) {
      this.glide(sh, { x: l.x, z: l.z }, 0);
      return;
    }
    if (e.sm.busy || e.sm.sub === "STAGGER" || e.sm.sub === "RESET") {
      const side = localToWorld(e.boss.location, e.loco.yaw, 2.6, 0, 0.5);
      this.glide(sh, e.arena.clampInside(side.x, side.z, 1), O.move.p2.speed);
    }
  }

  /**
   * Put a shadow at `spot` for `ticks`. Phase I conjures a temporary one; Phase II sends the
   * real shadow, which is why its errands interrupt its leading.
   */
  private sendShadow(spot: XZ, ticks: number, state: Shade): Helper | undefined {
    const e = this.enc;
    const now = e.timeline.now;
    const at = e.arena.at(spot, 0.05);
    if (e.phase === 2) {
      const sh = this.ensureShadow();
      if (!sh) return undefined;
      try {
        sh.entity.teleport(at, { keepVelocity: false });
      } catch {
        return undefined;
      }
      this.shadowBusyUntil = Math.max(this.shadowBusyUntil, now + ticks);
      this.shadowAt = { x: spot.x, z: spot.z };
      this.trail = [];
      this.shade(sh, state);
      e.visuals.decor(P("wisp"), { x: at.x, y: at.y + 1, z: at.z });
      return sh;
    }
    const h = e.helpers.spawn("abm:orison_shadow", at, "mark", { lifetime: ticks, yaw: e.loco.yaw });
    if (h) {
      this.shade(h, state);
      e.visuals.decor(P("wisp"), { x: at.x, y: at.y + 1, z: at.z });
    }
    return h;
  }

  /** In Phase II the shadow makes each attack's gesture before the body does. */
  private shadowLeads(run: AttackRun): void {
    if (run.phase !== 2) return;
    const sh = this.shadow();
    if (!sh || this.enc.timeline.now < this.shadowBusyUntil) return;
    this.shade(sh, Shade.Strike);
    run.at(12, () => {
      if (this.enc.timeline.now >= this.shadowBusyUntil) this.shade(sh, Shade.Idle);
    });
  }

  // ------------------------------------------------------------------ hourglasses (Drain)

  /** Slowness for players standing in an armed hourglass's area - re-applied in short doses, never stored. */
  private tickDrains(now: number): void {
    const e = this.enc;
    if (now % O.drain.slowEvery !== 0) return;
    const drains = e.helpers.of("drain");
    if (drains.length === 0) return;
    for (const h of drains) {
      if (now < h.data.armed) continue;
      const area = new Circle(h.data.x, h.data.z, O.drain.radius);
      for (const p of e.hazards.inside(area)) {
        try {
          p.addEffect("slowness", O.drain.slowTicks, { amplifier: O.drain.slowAmp, showParticles: true });
          trace("orison_slow", { player: p.name, tick: now });
        } catch {
          /* player left */
        }
      }
      if (now % 40 === 0) {
        e.visuals.pen(this.style.line, this.style.arc, undefined, this.floor(), 2.0).arc(h.data.x, h.data.z, O.drain.radius, 0, 360);
      }
    }
  }

  private armDrain(h: Helper, lifetime: number): void {
    const e = this.enc;
    const D = O.drain;
    const tag = `hg${h.id}`;
    const area = new Circle(h.data.x, h.data.z, D.radius);
    e.visuals.pen(this.style.line, this.style.arc, undefined, this.floor(), D.arm / 20).arc(h.data.x, h.data.z, D.radius, 0, 360);
    for (let at = D.arm; at + D.pulseWarn < lifetime; at += D.pulseEvery) {
      e.timeline.after(at, () => {
        if (!h.entity.isValid) return;
        try {
          h.entity.setProperty("abm:anim", 1);
        } catch {
          return;
        }
        e.hazards.strike({
          shape: area, warn: D.pulseWarn, tag, damage: D.damage, fx: 4, sound: S("drain_pulse"), label: "hourglass_drain",
          condition: () => h.entity.isValid,
          onStrike: () => {
            e.visuals.decor(P("pulse"), { x: h.data.x, y: this.floor(), z: h.data.z });
            try {
              if (h.entity.isValid) h.entity.setProperty("abm:anim", 0);
            } catch {
              /* gone */
            }
          },
        });
      }, tag);
    }
  }

  // ------------------------------------------------------------------ 01 Footstep Echo

  private footstepEcho(): AttackDef {
    const self = this;
    return {
      id: "footstep_echo", name: "Footstep Echo", index: 1, cooldown: O.echo.cooldown,
      weight: (e) => {
        const t = e.targeting.primary(e.timeline.now);
        if (!t) return 0;
        // the more ground the target has covered lately, the more there is to echo
        return self.history.pathLength(t.id, O.history.window[e.phase - 1]) > 6 ? 3.0 : 1.3;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("footstep_echo", run.phase);
        const i = run.phase - 1;
        if (live(run.target)) e.loco.facePoint((run.target as Player).location);
        self.shadowLeads(run);
        const last = t.first + t.gap * (t.count - 1);
        run.at(t.mark, () => {
          const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
          // newest first: where they stand now, then back along the recorded trail
          const trailPts: XZ[] = tgt ? [{ x: tgt.location.x, z: tgt.location.z }, ...self.history.recent(tgt.id, O.history.window[i])] : [];
          const picked: XZ[] = [];
          for (const p of trailPts) {
            if (picked.length >= t.count) break;
            if (picked.every((q) => Math.hypot(q.x - p.x, q.z - p.z) >= O.echo.minSpacing)) picked.push(p);
          }
          if (picked.length === 0) picked.push(e.arena.randomPoint(e.rng, 3));
          trace("orison_echo", { points: picked.map((p) => ({ x: p.x, z: p.z })), player: tgt?.name ?? "" });
          // the oldest footprint goes first, so the echoes walk the trail towards its owner
          const ordered = picked.slice().reverse();
          ordered.forEach((p, k) => {
            const at = t.first + (t.count - ordered.length + k) * t.gap;
            e.visuals.spawn(P("footprint"), { x: p.x, y: self.floor(), z: p.z });
            e.hazards.strike({
              shape: new Circle(p.x, p.z, O.echo.radius[i]), warn: at - t.mark, tag: run.tag, damage: O.echo.damage,
              fx: 4, sound: S("echo_burst"), knockUp: 0.2, label: "footstep_echo",
              onStrike: () => e.visuals.decor(P("echo"), { x: p.x, y: self.floor(0.9), z: p.z }),
            });
          });
        });
        run.windows(t.mark, last - t.mark + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 02 Pendulum Verdict

  private pendulumVerdict(): AttackDef {
    const self = this;
    return {
      id: "pendulum_verdict", name: "Pendulum Verdict", index: 2, cooldown: O.verdict.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d <= O.verdict.outer + 1 ? 3.0 : 0.6;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("pendulum_verdict", run.phase);
        const V = O.verdict;
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint((run.target as Player).location);
        self.shadowLeads(run);
        const b = e.boss.location;
        const front = self.front();
        // variant 0 starts on Orison's left and swings to its right; variant 1 the other way
        const dir = e.rng.chance(0.5) ? 1 : -1;
        run.variant(dir === 1 ? 0 : 1);
        const arc = V.arc[run.phase - 1];
        const a0 = front - (dir * arc) / 2;
        const a1 = front + (dir * arc) / 2;
        const swing = (startTick: number, from: number, to: number, r0: number, r1: number, label: string) => {
          const lo = Math.min(from, to);
          const begin = Math.max(1, startTick - Math.min(startTick - 1, 34));
          run.at(begin, () => {
            const warn = startTick - begin;
            // the whole arc is drawn; the blade itself is drawn at its starting edge and then as it moves
            e.hazards.telegraph(new Ring(b.x, b.z, r0, r1, lo, arc), warn);
            e.hazards.sweep({
              tag: run.tag, warn, duration: t.sweep, every: 1,
              shapeAt: (tt) => sector(b.x, b.z, r0, r1, from + ((to - from) * tt) / t.sweep, V.blade),
              damage: V.damage, blockable: true, knock: 1.3, knockUp: 0.3, label, fx: 2,
            });
          });
        };
        swing(t.swing, a0, a1, V.inner, V.outer, "pendulum_verdict");
        let last = t.swing + t.sweep;
        if (p2) {
          // Phase II: the return swing comes back the other way through the OUTER band
          swing(t.swing2, a1, a0, V.returnBand[0], V.returnBand[1], "pendulum_return");
          last = t.swing2 + t.sweep;
        }
        run.windows(t.swing, last - t.swing + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 03 Deferred Wound

  private deferredWound(): AttackDef {
    const self = this;
    return {
      id: "deferred_wound", name: "Deferred Wound", index: 3, cooldown: O.wound.cooldown,
      weight: (e) => 2.0 + Math.min(1.5, (e.targeting.count() - 1) * 0.6),
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("deferred_wound", run.phase);
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint((run.target as Player).location);
        self.shadowLeads(run);
        let last = 0;
        const countdown = (at: XZ, from: number, fuse: number) => {
          // III, II, I: one numeral per third of the fuse
          for (let n = 3; n >= 1; n--) {
            const when = from + Math.round((fuse * (3 - n)) / 3);
            run.at(when, () => self.numeral(n, at));
          }
        };
        for (let k = 0; k < t.count; k++) {
          const mark = t.first + k * t.gap;
          const boom = mark + t.fuse;
          last = Math.max(last, boom + (p2 ? t.echo : 0));
          run.at(mark, () => {
            const ps = e.targeting.participants();
            const who = ps.length > 0 ? ps[k % ps.length] : undefined;
            let c: XZ;
            if (!who) c = e.arena.randomPoint(e.rng, 3);
            else if (p2 && k % 2 === 1) {
              // Phase II: every other mark is set where they were two seconds ago
              const old = self.history.recent(who.id, 10);
              c = old.length > 0 ? old[old.length - 1] : { x: who.location.x, z: who.location.z };
            } else c = { x: who.location.x, z: who.location.z };
            const shape = new Circle(c.x, c.z, O.wound.radius);
            countdown(c, mark, t.fuse);
            e.hazards.strike({ shape, warn: t.fuse, tag: run.tag, damage: O.wound.damage, fx: 5, sound: S("wound_burst"), knockUp: 0.3, label: "deferred_wound" });
            if (p2) {
              // ... and the wound opens a second time in the same place
              run.at(boom, () => {
                e.hazards.strike({ shape, warn: t.echo, tag: run.tag, damage: O.wound.damage, fx: 5, sound: S("wound_burst"), knockUp: 0.3, label: "deferred_wound_again" });
              });
              countdown(c, boom, t.echo);
            }
          });
        }
        run.windows(t.first, last - t.first + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 04 Hourglass Drain

  private hourglassDrain(): AttackDef {
    const self = this;
    return {
      id: "hourglass_drain", name: "Hourglass Drain", index: 4, cooldown: O.drain.cooldown,
      weight: (e) => {
        if (e.helpers.count("drain") > 0) return 0;
        return self.dist(e) > 9 ? 2.4 : 1.7;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("hourglass_drain", run.phase);
        const i = run.phase - 1;
        self.shadowLeads(run);
        run.at(t.cast, () => {
          const ps = e.targeting.participants();
          const b = e.boss.location;
          const placed: XZ[] = [];
          for (let k = 0; k < O.drain.count[i]; k++) {
            const who = ps.length > 0 ? ps[k % ps.length] : undefined;
            const base: XZ = who ? who.location : { x: e.arena.cx, z: e.arena.cz };
            // set down beside a fighter - close enough that they start inside its reach, never on top of them
            let pos: XZ | undefined;
            for (let attempt = 0; attempt < 8 && !pos; attempt++) {
              const d = thetaToDir(e.rng.range(0, 360));
              const r = 2.2 + e.rng.range(0, 0.8) + (k >= ps.length ? 3 : 0);
              const c = e.arena.clampInside(base.x + d.x * r, base.z + d.z * r, 2);
              const clear = Math.hypot(c.x - b.x, c.z - b.z) >= 2.5 && placed.every((q) => Math.hypot(q.x - c.x, q.z - c.z) >= 3);
              if (clear) pos = c;
            }
            if (!pos) continue;
            placed.push(pos);
            const life = O.drain.lifetime[i];
            const h = e.helpers.spawn("abm:orison_hourglass", e.arena.at(pos, 0.05), "drain", {
              lifetime: life, data: { x: pos.x, z: pos.z, armed: e.timeline.now + O.drain.arm },
            });
            if (h) {
              self.armDrain(h, life);
              e.visuals.decor(P("sand"), e.arena.at(pos, 1.6));
            }
          }
          trace("orison_drain", { count: placed.length });
        });
        run.windows(t.cast, 4, Math.max(8, t.end - t.cast - 4));
      },
    };
  }

  // ------------------------------------------------------------------ 05 Tomorrow's Witness

  private tomorrowsWitness(): AttackDef {
    const self = this;
    return {
      id: "tomorrows_witness", name: "Tomorrow's Witness", index: 5, cooldown: O.witness.cooldown,
      weight: (e) => {
        const t = e.targeting.primary(e.timeline.now);
        if (!t) return 0;
        const v = self.history.velocity(t.id, O.witness.samplesBack);
        return Math.hypot(v.x, v.z) > 0.08 ? 3.0 : 1.4;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("tomorrows_witness", run.phase);
        const i = run.phase - 1;
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint((run.target as Player).location);
        const lead = t.strike - t.lock;
        run.at(t.lock, () => {
          const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
          const here: XZ = tgt ? { x: tgt.location.x, z: tgt.location.z } : e.arena.randomPoint(e.rng, 3);
          const vel = tgt ? self.history.velocity(tgt.id, O.witness.samplesBack) : { x: 0, z: 0 };
          const speed = Math.hypot(vel.x, vel.z);
          // straight-line extrapolation of the recent trajectory - and from this tick on it never changes
          const spots: XZ[] = [e.arena.clampInside(here.x + vel.x * lead, here.z + vel.z * lead, 1)];
          if (p2) {
            // Phase II also expects the obvious answer to being predicted: doubling back
            let back: XZ;
            if (speed > 0.03) back = { x: here.x - vel.x * lead * 0.6, z: here.z - vel.z * lead * 0.6 };
            else {
              const toC = Math.hypot(e.arena.cx - here.x, e.arena.cz - here.z);
              const d = toC > 1 ? { x: (e.arena.cx - here.x) / toC, z: (e.arena.cz - here.z) / toC } : thetaToDir(e.rng.range(0, 360));
              back = { x: here.x + d.x * 3.4, z: here.z + d.z * 3.4 };
            }
            spots.push(e.arena.clampInside(back.x, back.z, 1));
          }
          self.lastPrediction = spots.map((s) => ({ x: s.x, z: s.z }));
          trace("orison_predict", { spots: self.lastPrediction, from: here, vx: vel.x, vz: vel.z, strikeIn: lead });
          // the shadow goes and stands where it expects them, pointing; a line ties it to Orison
          const mark = self.sendShadow(spots[0], lead + 16, Shade.Point);
          const b = e.boss.location;
          const pen = e.visuals.pen(self.style.line, self.style.arc, undefined, self.floor(), lead / 20);
          pen.line(b.x, b.z, spots[0].x, spots[0].z);
          for (const s of spots) {
            e.hazards.strike({
              shape: new Circle(s.x, s.z, O.witness.radius[i]), warn: lead, tag: run.tag, damage: O.witness.damage,
              fx: 6, sound: S("shadow_strike"), knock: 0.8, knockUp: 0.3, label: "tomorrows_witness",
            });
          }
          run.at(t.strike - 6, () => {
            if (mark) self.shade(mark, Shade.Strike);
          });
          run.at(t.strike + 12, () => {
            const sh = self.shadow();
            if (p2 && sh) self.shade(sh, Shade.Idle);
          });
        });
        run.windows(t.lock, lead + 2, Math.max(8, t.end - t.strike - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 06 Secondhand Exchange

  /** A validated place to arrive: near the target, a real distance from where Orison stands now. */
  private pickDestination(tgt: Player | undefined, from: XZ): XZ | undefined {
    const e = this.enc;
    const X = O.exchange;
    const cands: XZ[] = [];
    if (tgt) {
      const away = dirToTheta(tgt.location.x - from.x, tgt.location.z - from.z);
      // behind the target first, then its flanks
      for (const off of [0, 50, -50, 100, -100, 150, -150, 180]) {
        const d = thetaToDir(away + off);
        cands.push({ x: tgt.location.x + d.x * X.offset, z: tgt.location.z + d.z * X.offset });
      }
    }
    for (let k = 0; k < 6; k++) cands.push(e.arena.randomPoint(e.rng, e.stats.leashInset + 1));
    for (const c of cands) {
      const p = e.arena.clampInside(c.x, c.z, e.stats.leashInset + 0.5);
      if (Math.hypot(p.x - from.x, p.z - from.z) < X.minJump) continue;
      if (!e.loco.canStand(p)) continue;
      return p;
    }
    return undefined;
  }

  private secondhandExchange(): AttackDef {
    const self = this;
    return {
      id: "secondhand_exchange", name: "Secondhand Exchange", index: 6, cooldown: O.exchange.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d > 10 ? 3.2 : d > 6 ? 1.6 : 0.9;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("secondhand_exchange", run.phase);
        const X = O.exchange;
        const steps: Array<[number, number, number]> = [[t.mark, t.swap, t.strike]];
        if (run.phase === 2) steps.push([t.mark2, t.swap2, t.strike2]);
        let last = 0;
        for (const [mk, sw, st] of steps) {
          last = st;
          run.at(mk, () => {
            const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
            const bl = e.boss.location;
            const from: XZ = { x: bl.x, z: bl.z };
            const dest = self.pickDestination(tgt, from);
            const arrive = dest ?? from;
            trace("orison_exchange", { from, to: arrive, valid: dest !== undefined });
            // the marker: a shadow stands on the arrival point for the whole warning
            const mark = self.sendShadow(arrive, st - mk + 14, Shade.Point);
            const warn = st - mk;
            // both ends are shown from the start: where it will arrive, and what it leaves behind
            e.hazards.strike({
              shape: new Circle(arrive.x, arrive.z, X.arriveRadius), warn, tag: run.tag, damage: X.arrive,
              knock: 1.2, knockUp: 0.35, fx: 8, label: "exchange_arrive",
            });
            if (dest) {
              e.hazards.strike({
                shape: new Circle(from.x, from.z, X.departRadius), warn, tag: run.tag, damage: X.depart,
                fx: 4, sound: S("shadow_strike"), label: "exchange_depart",
              });
              e.visuals.pen(self.style.safeLine, self.style.safeArc, undefined, self.floor(), warn / 20).line(from.x, from.z, arrive.x, arrive.z);
            }
            run.at(sw, () => {
              if (!dest) return;
              const face = tgt && tgt.isValid ? dirToYaw(tgt.location.x - dest.x, tgt.location.z - dest.z) : e.loco.yaw;
              const ok = e.loco.relocate(dest, face);
              trace("orison_swap", { ok });
              const y = self.floor(1.5);
              e.visuals.spawn(P("wisp"), { x: from.x, y, z: from.z });
              e.visuals.spawn(P("wisp"), { x: dest.x, y, z: dest.z });
              // the shadow takes the place Orison just left, and strikes there
              if (ok && mark && mark.entity.isValid) {
                try {
                  mark.entity.teleport(e.arena.at(from, 0.05), { keepVelocity: false });
                  self.shadowAt = { x: from.x, z: from.z };
                } catch {
                  /* gone */
                }
              }
            });
            run.at(st - 6, () => {
              if (mark) self.shade(mark, Shade.Strike);
            });
          });
        }
        run.at(last + 12, () => {
          const sh = self.shadow();
          if (sh) self.shade(sh, Shade.Idle);
        });
        run.windows(t.mark, last - t.mark + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 07 The Hour That Never Occurred

  private hourThatNeverOccurred(): AttackDef {
    const self = this;
    return {
      id: "hour_never", name: "The Hour That Never Occurred", index: 7, ultimate: true, interruptible: false,
      cooldown: O.hour.cooldown,
      weight: (e) => (e.healthFraction() < 0.92 ? 5 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("hour_never", run.phase);
        const p2 = run.phase === 2;
        const i = run.phase - 1;
        self.shadowLeads(run);
        // The three patterns are decided ONCE, here, and stored. Preview and execution both read this array.
        const patterns: readonly Pattern[] = Object.freeze(choosePatterns(e.rng, run.phase));
        const shapes = patterns.map((p) => new PatternShape(p, e.arena, O.hour.wedges[i], O.hour.band));
        self.lastHour = { previewed: patterns.map(patternLabel), executed: [] };
        trace("orison_preview", { patterns: self.lastHour.previewed.slice() });
        const centre: XZ = { x: e.arena.cx, z: e.arena.cz };
        // preview: I, II, III - each shown alone, in order, with no damage
        patterns.forEach((_p, k) => {
          run.at(t.preview + k * t.step, () => {
            e.hazards.telegraph(shapes[k], t.show);
            self.numeral(k + 1, centre);
            for (const a of [0, 120, 240]) self.numeral(k + 1, e.arena.polar(a + k * 40, 9));
          });
        });
        // execution: the same shapes in the same order
        for (let k = 0; k < patterns.length; k++) {
          const at = t.exec + k * t.gap;
          // the first is committed when it is previewed; each later one when the one before it lands
          const commit = k === 0 ? t.preview : t.exec + (k - 1) * t.gap;
          run.at(commit, () => {
            e.hazards.strike({
              shape: shapes[k], warn: at - commit, quiet: true, tag: run.tag, damage: O.hour.damage, fx: 14,
              sound: S("hour_strike"), knockUp: 0.3, label: `hour_${k + 1}`,
              onStrike: () => {
                self.lastHour.executed.push(patternLabel(patterns[k]));
                trace("orison_execute", { index: k, pattern: patternLabel(patterns[k]) });
              },
            });
          });
          // Phase I flashes each pattern again just before it lands; Phase II leaves it to memory
          if (!p2) run.at(at - 10, () => e.hazards.telegraph(shapes[k], 10));
          run.at(at - 30, () => self.numeral(k + 1, centre));
        }
        const last = t.exec + 2 * t.gap;
        run.windows(t.preview, last - t.preview + 2, Math.max(10, t.end - last - 2));
      },
    };
  }
}

export const MODULE: BossModule = {
  create: (enc: Encounter): BossController => new OrisonController(enc),
  arena: { structure: "abm:court_of_unlived_hours", size: 47, height: 14, nameKey: "abm.arena.orison" },
  helpers: ["abm:orison_hourglass", "abm:orison_shadow"],
};

export type { V3 };
