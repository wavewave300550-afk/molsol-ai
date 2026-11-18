/**
 * Boss 002 - Cantor XIII, The Walking Requiem.
 *
 * A rhythm-and-pattern fight. Cantor keeps a beat (10 ticks) that the whole
 * encounter is quantised to: attacks begin on a beat, their strikes land on
 * beats, and a ring leaves its feet on every beat so the pulse can be SEEN.
 * Its hazards are waves - rings, wave fronts, cones, shard fans - each with
 * deliberate doors, and the answer to every one of them is to be standing in
 * a door when the wave arrives. Phase II (The Broken Symphony) syncopates the
 * same seven pieces: second rings on the off-beat, perpendicular fronts closer
 * together, an echo after the held note, uneven measures in the requiem.
 */
import { EntityHealthComponent, MolangVariableMap, Player } from "@minecraft/server";
import T from "../../../shared/cantor.timings.json";
import { BossKey } from "../../config";
import { AttackDef, AttackRun, BossController, BossModule, IncomingInfo } from "../../core/boss";
import type { Encounter } from "../../core/encounter";
import type { Helper } from "../../core/helpers";
import { V3, XZ, dirToTheta, distXZ, thetaToDir, yawToTheta } from "../../core/math";
import { Circle, Except, Lane, Ring, Shape, Union, sector } from "../../core/shapes";
import { trace } from "../../core/trace";
import { TelegraphStyle } from "../../core/visuals";
import { CANTOR as C } from "./tuning";

const S = (id: string): string => `abm.cantor.${id}`;
const P = (id: string): string => `abm:cantor_${id}`;
const BEAT = T.beat;
const MEASURE = T.measure;
/** Phase II pulse: the four beats of a measure fall unevenly. */
const BROKEN_BEATS = [0, 12, 20, 32];

type Beats = Record<string, number>;
const beats = (name: keyof typeof T, phase: 1 | 2): Beats =>
  (T[name] as unknown as Record<string, Beats>)[phase === 2 ? "p2" : "p1"];

/** Ring doors as [start bearing, width] pairs, evenly spaced from `base`. */
function doors(base: number, count: number, width: number): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (let k = 0; k < count; k++) out.push([base + (k * 360) / count - width / 2, width]);
  return out;
}

/**
 * A door is never narrower than `min` blocks: close to the centre, where a fixed angle would pinch it
 * shut, it opens up instead (the floor marks stay the narrower, always-safe wedge).
 */
function widen(gaps: ReadonlyArray<readonly [number, number]>, r: number, min: number): Array<[number, number]> {
  const cap = 360 / gaps.length - 8;
  return gaps.map(([g0, gw]): [number, number] => {
    const w = Math.min(cap, Math.max(gw, (min / Math.max(0.5, r)) * (180 / Math.PI)));
    return [g0 + gw / 2 - w / 2, w];
  });
}

interface WaveOptions {
  /** Attack-relative tick at which the wave starts moving. */
  start: number;
  /** Attack-relative tick at which it becomes visible as a telegraph. */
  shown: number;
  duration: number;
  shapeAt: (t: number) => Shape;
  damage: number;
  label: string;
  knock?: number;
  from?: XZ;
}

export class CantorController extends BossController {
  readonly key: BossKey = "cantor";
  readonly displayName = "Cantor XIII";
  readonly phase2Name = "The Broken Symphony";
  readonly trophyItem = "abm:bell_fragment";
  readonly style: TelegraphStyle = {
    line: P("tg_line"), arc: P("tg_arc"), disc: P("tg_disc"),
    safeLine: P("safe_line"), safeArc: P("safe_arc"), strike: P("strike"),
  };
  readonly attacks: readonly AttackDef[];
  /** The beat is withheld (no pulse, dark windows) until this encounter tick. */
  silentUntil = 0;
  /** Rhythmic attacks played since the last Silent Measure. */
  private sinceSilent = 0;
  private nextIdleSound = 160;
  /** Encounter ticks at which attacks started (asserted on by the rhythm test). */
  readonly attackStarts: number[] = [];

  constructor(enc: Encounter) {
    super(enc);
    this.attacks = [
      this.primeDownbeat(), this.counterpoint(), this.glassAria(), this.heldNote(),
      this.silentMeasure(), this.twinResonance(), this.finalRequiem(),
    ];
  }

  // ------------------------------------------------------------------ framework hooks

  configure(phase: 1 | 2): void {
    const m = phase === 2 ? C.move.p2 : C.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }

  intro(): number {
    return T.intro.total;
  }

  phaseTransition(): number {
    const e = this.enc;
    const t = T.transition;
    // the service is interrupted: detached bells are recalled, the beat stops until the new one starts
    e.helpers.removeKind("bell");
    e.setProp("abm:bells_out", 0);
    this.endSilence();
    this.silentUntil = e.timeline.now + t.total;
    e.timeline.after(t.break, () => {
      // the lip of the bell lands at its feet: a shove, not a wound
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 6))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: ((p.location.x - c.x) / d) * 1.5, z: ((p.location.z - c.z) / d) * 1.5 }, 0.3);
        } catch {
          /* player left */
        }
      }
      e.visuals.decor(P("dust"), { x: c.x, y: e.arena.floorY + 0.4, z: c.z });
    }, "phase");
    return t.total;
  }

  phase2Ready(): void {
    this.silentUntil = 0;
    this.sinceSilent = 0;
  }

  death(): number {
    const e = this.enc;
    const t = T.death;
    this.endSilence();
    this.silentUntil = e.timeline.now + t.total + 1000;
    e.setProp("abm:bells_out", 0);
    for (let i = 0; i < 3; i++) {
      e.timeline.after(t.legs + i * t.legStep + 9, () => {
        const c = e.boss.location;
        e.visuals.scatter(P("dust"), new Circle(c.x, c.z, 3.5).sample(e.rng, 4), e.arena.floorY + 0.4);
      }, "death");
    }
    return t.total;
  }

  /** Cantor holds the middle of its hall and turns, deliberately, to face whoever it is playing to. */
  position(target: Player | undefined): boolean {
    const e = this.enc;
    const m = e.phase === 2 ? C.move.p2 : C.move.p1;
    const b = e.boss.location;
    let anchor: XZ = { x: e.arena.cx, z: e.arena.cz };
    if (e.phase === 2 && target) {
      // unstable: it drifts off its mark towards the target, but never far
      const dx = target.location.x - e.arena.cx;
      const dz = target.location.z - e.arena.cz;
      const d = Math.hypot(dx, dz) || 1;
      const k = Math.min(m.home - 1.5, d * 0.35) / d;
      anchor = { x: e.arena.cx + dx * k, z: e.arena.cz + dz * k };
    }
    const off = distXZ(b, anchor);
    if (off > (e.phase === 2 ? m.settle + 1.2 : m.home)) {
      e.loco.goTo(anchor, m.settle);
      return true;
    }
    e.loco.halt();
    if (target) e.loco.turnToward(e.loco.yawTo(target.location), 4);
    return false;
  }

  tick(): void {
    const e = this.enc;
    const now = e.timeline.now;
    if (!e.sm.inCombat) return;
    // quantise: the next attack may only begin on a beat
    if (!e.sm.busy) {
      const due = Math.max(e.nextAttackAt, now);
      e.nextAttackAt = Math.ceil(due / BEAT) * BEAT;
    }
    // the visible pulse
    if (now >= this.silentUntil) {
      const onBeat = e.phase === 2 ? BROKEN_BEATS.includes(now % MEASURE) : now % BEAT === 0;
      if (onBeat) {
        const b = e.boss.location;
        e.visuals.decor(P("beat"), { x: b.x, y: e.arena.floorY + 0.1, z: b.z });
        if (now % MEASURE === 0) e.audio.play(S("beat"), b, 0.5);
      }
    }
    this.tickBells(now);
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 200 + e.rng.int(0, 160);
    }
  }

  incoming(damage: number, _info: IncomingInfo): number {
    const e = this.enc;
    e.defer(() => {
      const b = e.boss.location;
      e.audio.play(S("hit"), b, 0.7);
      e.visuals.decor(P("strike"), { x: b.x, y: b.y + 4, z: b.z });
    });
    return damage;
  }

  onHelperGone(h: Helper): void {
    if (h.kind !== "bell") return;
    const e = this.enc;
    e.timeline.cancel(`bell${h.id}`);
    const left = e.helpers.count("bell");
    if (left === 0) e.setProp("abm:bells_out", 0);
    if (h.killed) {
      e.audio.play(S("bell_destroy"), e.boss.location);
      trace("bell_destroyed", { left });
      // silencing both bells breaks the piece: Cantor loses its place
      if (left === 0 && e.sm.inCombat) e.stagger(C.twin.staggerTicks);
    }
  }

  onAttackCancelled(def: AttackDef): void {
    if (def.id === "silent_measure") this.endSilence();
  }

  cleanup(): void {
    this.silentUntil = 0;
  }

  // ------------------------------------------------------------------ shared helpers

  private dist(e: Encounter): number {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }

  private begin(run: AttackRun, rhythmic = true): void {
    this.attackStarts.push(run.t0);
    if (rhythmic) this.sinceSilent++;
  }

  /** Distance from a point to the far side of the arena (how far a ring must travel to clear it). */
  private reach(p: XZ): number {
    const a = this.enc.arena;
    return a.radius * (a.square ? Math.SQRT2 : 1) + Math.hypot(p.x - a.cx, p.z - a.cz) + 1;
  }

  private get floor(): number {
    return this.enc.arena.floorY + 0.08;
  }

  /**
   * A moving wave. Collision and picture come from the same shapeAt(t) on the
   * same ticks: this draws it on even ticks with marks that live exactly until
   * the next redraw, and the hazard system tests that same drawn shape.
   */
  private wave(run: AttackRun, o: WaveOptions): void {
    const e = run.enc;
    // tested every tick, but against the shape that is on the floor (redrawn on even ticks)
    run.at(o.shown, () => e.hazards.sweep({
      tag: run.tag, warn: o.start - o.shown, duration: o.duration, every: 1, draw: false, shapeAt: (tt) => o.shapeAt(tt - (tt % 2)),
      damage: o.damage, label: o.label, knock: o.knock ?? 0.6, knockUp: 0.2, from: o.from, fx: 2, sound: S("wave"),
    }));
    for (let tt = 0; tt <= o.duration; tt += 2) {
      run.at(o.start + tt, () => o.shapeAt(tt).draw(e.visuals.pen(P("wave_line"), P("wave_arc"), undefined, this.floor, 3 / 20)));
    }
  }

  /** Mark the doors of a ring as safe wedges for `ticks`. */
  private markDoors(c: XZ, gaps: ReadonlyArray<readonly [number, number]>, r0: number, r1: number, ticks: number): void {
    for (const [g0, gw] of gaps) this.enc.hazards.telegraph(new Ring(c.x, c.z, r0, r1, g0, gw), ticks, true);
  }

  private flash(c: XZ, r: number): void {
    const m = new MolangVariableMap();
    m.setFloat("variable.r", r);
    this.enc.visuals.spawn(P("ring_flash"), { x: c.x, y: this.floor, z: c.z }, m);
  }

  private endSilence(): void {
    this.enc.setProp("abm:silent", 0);
  }

  // ------------------------------------------------------------------ 01 Prime Downbeat

  private primeDownbeat(): AttackDef {
    const self = this;
    return {
      id: "prime_downbeat", name: "Prime Downbeat", index: 1, cooldown: C.downbeat.cooldown,
      weight: (e) => (self.dist(e) < 11 ? 3.2 : 2.0),
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const t = beats("prime_downbeat", run.phase);
        const D = C.downbeat;
        const b = e.boss.location;
        const c: XZ = { x: b.x, z: b.z };
        const R = self.reach(c);
        const duration = Math.ceil((R - 2) / D.speed);
        const base = e.rng.range(0, 360);
        const ringAt = (gaps: Array<[number, number]>) => (tt: number) => {
          const r = 2 + tt * D.speed;
          const r0 = Math.max(0.3, r - D.thickness / 2);
          return new Ring(c.x, c.z, r0, r + D.thickness / 2, 0, 360, widen(gaps, r0, D.minDoor));
        };
        // the bell falls on the beat; the doors are shown from the first tick
        const g1 = doors(base, D.gaps, D.gapWidth);
        self.markDoors(c, g1, 2.5, R, t.strike + duration);
        run.at(t.strike, () => self.flash(c, 3));
        let last = t.strike;
        self.wave(run, { shown: 0, start: t.strike, duration, shapeAt: ringAt(g1), damage: D.damage, label: "downbeat", from: c });
        if (run.phase === 2) {
          // Phase II: a second, weaker toll on the off-beat. Its doors are turned but overlap the first
          // set: stand where both sets of marks agree, or step across between the two rings.
          const g2 = doors(base + (e.rng.chance(0.5) ? 1 : -1) * D.secondShift, D.gaps, D.secondWidth);
          self.markDoors(c, g2, 2.5, R, t.second + duration);
          self.wave(run, { shown: 0, start: t.second, duration, shapeAt: ringAt(g2), damage: D.secondDamage, label: "downbeat_echo", from: c });
          run.at(t.second, () => self.flash(c, 3));
          last = t.second;
        }
        run.windows(t.strike, last - t.strike + duration, Math.max(10, t.end - last - duration));
      },
    };
  }

  // ------------------------------------------------------------------ 02 Counterpoint

  private counterpoint(): AttackDef {
    const self = this;
    return {
      id: "counterpoint", name: "Counterpoint", index: 2, cooldown: C.counterpoint.cooldown,
      weight: (e) => (self.dist(e) > 7 ? 2.6 : 1.6) + (e.targeting.count() > 1 ? 0.8 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const t = beats("counterpoint", run.phase);
        const K = C.counterpoint;
        const a = e.arena;
        const R = a.radius;
        const speed = K.speed[run.phase - 1];
        const duration = Math.ceil((2 * R + 2) / speed);
        const theta = e.rng.pick([0, 45, 90, 135, 180, 225, 270, 315]);
        const who = run.target;
        // two voices: the second enters across the first, a measure (Phase II: a little over half) later
        const voices: Array<{ theta: number; start: number }> = [
          { theta, start: t.first },
          { theta: theta + (e.rng.chance(0.5) ? 90 : -90), start: t.second },
        ];
        const fronts: Array<(tt: number) => Shape> = [];
        for (const v of voices) {
          const d = thetaToDir(v.theta);
          const n = { x: -d.z, z: d.x };
          // the doors never open where the target is standing: it has to move to one
          const u = who ? (who.location.x - a.cx) * n.x + (who.location.z - a.cz) * n.z : 0;
          let d1 = u - K.doorSpacing / 2 + e.rng.range(-1.2, 1.2);
          while (d1 > -2) d1 -= K.doorSpacing;
          while (d1 < -K.doorSpacing - 2) d1 += K.doorSpacing;
          const doorsAt = [d1, d1 + K.doorSpacing].filter((x) => Math.abs(x) < R - 3.5);
          if (doorsAt.length === 0) doorsAt.push(0);
          fronts.push((tt: number): Shape => {
            const s = -(R + 1) + speed * tt;
            const h2 = R * R - s * s;
            if (tt < 0 || tt > duration || h2 <= 1) return new Union([]);
            const h = Math.sqrt(h2);
            const px = a.cx + d.x * s;
            const pz = a.cz + d.z * s;
            const cuts = doorsAt.map((x) => [x - K.doorHalf, x + K.doorHalf]).sort((p, q) => p[0] - q[0]);
            const parts: Shape[] = [];
            let from = -h;
            for (const [c0, c1] of [...cuts, [h, h]]) {
              const to = Math.min(h, c0);
              if (to - from > 0.4) parts.push(new Lane(px + n.x * from, pz + n.z * from, px + n.x * to, pz + n.z * to, K.thickness / 2));
              from = Math.max(from, c1);
            }
            return new Union(parts);
          });
          // each door's whole path through the hall is marked as a safe corridor
          for (const x of doorsAt) {
            const half = Math.sqrt(Math.max(1, R * R - x * x));
            const cx = a.cx + n.x * x;
            const cz = a.cz + n.z * x;
            e.hazards.telegraph(new Lane(cx - d.x * half, cz - d.z * half, cx + d.x * half, cz + d.z * half, K.doorHalf - 0.3), v.start + duration, true);
          }
        }
        // two hazards: the first front can be answered at its door, the second at its own
        voices.forEach((v, i) => self.wave(run, {
          shown: 0, start: v.start, duration, damage: K.damage, label: `counterpoint_${i + 1}`, knock: 0.9, shapeAt: fronts[i],
        }));
        run.windows(t.first, t.second - t.first + duration, Math.max(8, t.end - t.second - duration));
      },
    };
  }

  // ------------------------------------------------------------------ 03 Glass Aria

  private glassAria(): AttackDef {
    const self = this;
    return {
      id: "glass_aria", name: "Glass Aria", index: 3, cooldown: C.aria.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 4 && d <= 17 ? 2.8 : 1.2;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const t = beats("glass_aria", run.phase);
        const G = C.aria;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const aim = yawToTheta(e.loco.yaw);
        const ad = thetaToDir(aim);
        const from: V3 = { x: b.x + ad.x * 2.2, y: e.arena.floorY + 1.6, z: b.z + ad.z * 2.2 };
        const flight = Math.ceil(G.range / G.speed);
        let last = t.first;
        // Fixed fans: every shard flies straight down the lane that was drawn for it. The volleys are
        // grouped into two hazards (1st+3rd, 2nd+4th) so one aria can wound a player twice at most.
        const groups: Array<Array<{ at: number; dirs: XZ[] }>> = [[], []];
        for (let k = 0; k < t.volleys; k++) {
          const at = t.first + k * t.gap;
          last = at;
          const dirs = G.fans[k % 2].map((off) => thetaToDir(aim + off));
          groups[k % 2].push({ at, dirs });
          const shown = Math.max(2, at - G.warn);
          run.at(shown, () => {
            for (const d of dirs) e.hazards.telegraph(new Lane(from.x, from.z, from.x + d.x * G.range, from.z + d.z * G.range, G.radius), at - shown);
          });
          run.at(at, () => {
            for (const d of dirs) e.visuals.flyer(P("shard"), from, { x: d.x, y: 0, z: d.z }, G.speed * 20, flight / 20);
            e.audio.play(S("glass_shard"), from);
          });
        }
        let waveAt: ((tt: number) => Shape) | undefined;
        let waveEnd = 0;
        if (run.phase === 2) {
          // Phase II: one limited wave under the second volley - a half ring towards the aim, with two doors
          const gaps: Array<[number, number]> = [[aim - 50 - G.waveGap / 2, G.waveGap], [aim + 50 - G.waveGap / 2, G.waveGap]];
          const c: XZ = { x: b.x, z: b.z };
          const duration = Math.ceil((G.waveReach - 2) / G.waveSpeed);
          self.markDoors(c, gaps, 2.5, G.waveReach, t.wave + duration);
          waveEnd = t.wave + duration;
          waveAt = (tt) => new Ring(c.x, c.z, Math.max(0.3, 2 + tt * G.waveSpeed - 0.8), 2 + tt * G.waveSpeed + 0.8, aim - G.waveArc / 2, G.waveArc, gaps);
          for (let tt = 0; tt <= duration; tt += 2) {
            run.at(t.wave + tt, () => (waveAt as (x: number) => Shape)(tt).draw(e.visuals.pen(P("wave_line"), P("wave_arc"), undefined, self.floor, 3 / 20)));
          }
        }
        groups.forEach((volleys, gi) => {
          if (volleys.length === 0) return;
          const start = volleys[0].at;
          const end = Math.max(volleys[volleys.length - 1].at + flight, gi === 1 ? waveEnd : 0);
          const begin = gi === 1 && waveAt ? Math.min(start, t.wave) : start;
          const shown = Math.max(2, begin - G.warn);
          run.at(shown, () => e.hazards.sweep({
            tag: run.tag, warn: begin - shown, duration: end - begin, every: 1, draw: false, damage: G.damage, blockable: true,
            knock: 0.5, label: gi === 0 ? "aria_shards_a" : "aria_shards_b",
            shapeAt: (tt) => {
              const now = begin + tt;
              const parts: Shape[] = [];
              for (const v of volleys) {
                const f = now - v.at;
                if (f < 1 || f > flight) continue;
                for (const d of v.dirs) parts.push(new Circle(from.x + d.x * G.speed * f, from.z + d.z * G.speed * f, G.radius));
              }
              if (gi === 1 && waveAt && now >= t.wave && now <= waveEnd && (now - t.wave) % 2 === 0) parts.push(waveAt(now - t.wave));
              return new Union(parts);
            },
          }));
        });
        if (waveEnd) last = Math.max(last, waveEnd - flight);
        run.windows(t.first, last - t.first + flight, Math.max(8, t.end - last - flight));
      },
    };
  }

  // ------------------------------------------------------------------ 04 Held Note

  private heldNote(): AttackDef {
    const self = this;
    return {
      id: "held_note", name: "Held Note", index: 4, cooldown: C.heldNote.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 3 && d <= 15 ? 2.4 : 0.6;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const t = beats("held_note", run.phase);
        const H = C.heldNote;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const c: XZ = { x: b.x, z: b.z };
        const aim = yawToTheta(e.loco.yaw);
        // the whole final cone is outlined at once; inside it a brighter cone swells with the note
        e.hazards.strike({
          shape: sector(c.x, c.z, H.inner, H.range, aim, H.halfAngle), warn: t.blast, tag: run.tag, damage: H.damage,
          knock: 1.5, knockUp: 0.3, from: c, fx: 14, label: "held_note",
        });
        e.hazards.telegraph(new Circle(c.x, c.z, H.inner - 0.3), t.blast, true);       // under the pipes is safe
        const steps = Math.floor(t.blast / BEAT) - 1;
        for (let i = 1; i <= steps; i++) {
          run.at(i * BEAT, () => e.hazards.telegraph(sector(c.x, c.z, H.inner, H.range, aim, (H.halfAngle * i) / (steps + 1)), BEAT));
        }
        let last = t.blast;
        if (run.phase === 2) {
          // Phase II: the note breaks and sounds again - a narrower cone at wherever the target went
          run.at(t.blast, () => {
            const tg = e.targeting.primary(e.timeline.now) ?? run.target;
            const a2 = tg ? dirToTheta(tg.location.x - c.x, tg.location.z - c.z) : aim;
            e.hazards.strike({
              shape: sector(c.x, c.z, H.inner, H.range, a2, H.echoHalf), warn: t.echo - t.blast, tag: run.tag, damage: H.echoDamage,
              knock: 1.2, knockUp: 0.3, from: c, fx: 10, label: "held_echo",
            });
            e.hazards.telegraph(new Circle(c.x, c.z, H.inner - 0.3), t.echo - t.blast, true);
            run.at(t.blast + 4, () => e.loco.face(a2 - 90));
          });
          last = t.echo;
        }
        run.windows(t.blast, last - t.blast + 2, Math.max(10, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 05 The Silent Measure

  private silentMeasure(): AttackDef {
    const self = this;
    return {
      id: "silent_measure", name: "The Silent Measure", index: 5, cooldown: C.silent.cooldown,
      // there has to be a rhythm before it can be withheld
      weight: () => (self.sinceSilent >= C.silent.needsRhythm ? 2.2 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run, false);
        self.sinceSilent = 0;
        const t = beats("silent_measure", run.phase);
        const Q = C.silent;
        const b = e.boss.location;
        const c: XZ = { x: b.x, z: b.z };
        const R = self.reach(c);
        const duration = Math.ceil((R - 1.5) / Q.speed);
        const base = e.rng.range(0, 360);
        const ringAt = (gaps: Array<[number, number]>) => (tt: number) => {
          const r = Math.max(1.5, R - tt * Q.speed);
          const r0 = Math.max(0.3, r - Q.thickness / 2);
          return new Ring(c.x, c.z, r0, r + Q.thickness / 2, 0, 360, widen(gaps, r0, Q.minDoor));
        };
        // the bell is arrested mid-swing: no pulse, dark windows, a rest sign over the bell
        run.at(t.freeze, () => {
          self.silentUntil = e.timeline.now + (t.strike - t.freeze);
          e.setProp("abm:silent", 1);
          const m = new MolangVariableMap();
          m.setFloat("variable.life", (t.strike - t.freeze) / 20);
          e.visuals.spawn(P("rest"), { x: b.x, y: b.y + 10.6, z: b.z }, m);
        });
        // ... and what was owed arrives late and from the outside in
        const g1 = doors(base, Q.gaps, Q.gapWidth);
        self.markDoors(c, g1, 2, R, t.strike + duration);
        run.at(t.strike, () => {
          self.endSilence();
          self.flash(c, R * 0.5);
        });
        let last = t.strike;
        self.wave(run, { shown: 0, start: t.strike, duration, shapeAt: ringAt(g1), damage: Q.damage, label: "silent_ring", from: c });
        if (run.phase === 2) {
          const g2 = doors(base + (e.rng.chance(0.5) ? 1 : -1) * Q.secondShift, Q.gaps, Q.secondWidth);
          self.markDoors(c, g2, 2, R, t.second + duration);
          self.wave(run, { shown: 0, start: t.second, duration, shapeAt: ringAt(g2), damage: Q.secondDamage, label: "silent_echo", from: c });
          last = t.second;
        }
        run.windows(t.strike, last - t.strike + duration, Math.max(10, t.end - last - duration));
      },
    };
  }

  // ------------------------------------------------------------------ 06 Twin Resonance

  private twinResonance(): AttackDef {
    const self = this;
    return {
      id: "twin_resonance", name: "Twin Resonance", index: 6, cooldown: C.twin.cooldown,
      weight: (e) => (e.helpers.count("bell") > 0 ? 0 : 2.0),
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const t = beats("twin_resonance", run.phase);
        const W = C.twin;
        const i = run.phase - 1;
        run.at(t.detach, () => {
          const a = e.arena;
          const b = e.boss.location;
          const tg = e.targeting.primary(e.timeline.now) ?? run.target;
          // one bell is set down beside the target, the other across the hall from it
          const near: XZ = tg
            ? a.clampInside(tg.location.x + (a.cx - tg.location.x) * 0.2, tg.location.z + (a.cz - tg.location.z) * 0.2, 2.5)
            : a.polar(e.rng.range(0, 360), 9, 2.5);
          const far: XZ = a.clampInside(2 * a.cx - near.x, 2 * a.cz - near.z, 2.5);
          const spots = [near, far].map((p) => {
            // never on top of Cantor itself
            const d = Math.hypot(p.x - b.x, p.z - b.z);
            if (d >= 4) return p;
            const th = d > 0.1 ? dirToTheta(p.x - b.x, p.z - b.z) : e.rng.range(0, 360);
            const dir = thetaToDir(th);
            return a.clampInside(b.x + dir.x * 4.5, b.z + dir.z * 4.5, 2.5);
          });
          const now = e.timeline.now;
          spots.forEach((p, k) => {
            e.helpers.spawn("abm:cantor_bell", a.at(p, 0.05), "bell", {
              lifetime: W.lifetime[i], data: { interval: W.intervals[i][k], next: now + W.firstDelay + k * 20, hp: W.health, busyUntil: 0 },
            });
            e.visuals.decor(P("dust"), a.at(p, 0.4));
          });
          if (e.helpers.count("bell") > 0) e.setProp("abm:bells_out", 1);
        });
        run.windows(t.detach, 4, Math.max(8, t.end - t.detach - 4));
      },
    };
  }

  /** Each detached bell keeps its own interval. Striking a bell interrupts the pulse it is winding up. */
  private tickBells(now: number): void {
    const e = this.enc;
    const W = C.twin;
    for (const h of e.helpers.of("bell")) {
      const tag = `bell${h.id}`;
      let hp = h.data.hp;
      try {
        hp = (h.entity.getComponent("minecraft:health") as EntityHealthComponent | undefined)?.currentValue ?? hp;
      } catch {
        continue;
      }
      if (hp < h.data.hp - 0.01) {
        h.data.hp = hp;
        if (e.timeline.cancel(tag) > 0) {
          // interrupted: the pulse it owed is lost and it has to start counting again
          h.data.next = now + h.data.interval;
          h.data.busyUntil = 0;
          this.setBellAnim(h, 0);
          trace("bell_interrupted", { id: h.id });
        }
      }
      if (now < h.data.next || now < h.data.busyUntil) continue;
      const at = h.entity.location;
      h.data.next = now + h.data.interval;
      h.data.busyUntil = now + W.warn + 4;
      this.setBellAnim(h, 1);
      // the swinging bell and the filling disc are the warning; the pulse lands on the whole disc at once
      e.hazards.strike({
        shape: new Circle(at.x, at.z, W.radius), warn: W.warn, tag, damage: W.damage, label: "bell_pulse", knock: 0.7,
        from: at, sound: S("bell_pulse"), fx: 5, condition: () => h.entity.isValid,
        onStrike: () => this.flash(at, W.radius),
      });
      e.timeline.after(W.warn + 2, () => this.setBellAnim(h, 0), tag);
    }
  }

  private setBellAnim(h: Helper, v: number): void {
    try {
      if (h.entity.isValid) h.entity.setProperty("abm:anim", v);
    } catch {
      /* gone */
    }
  }

  // ------------------------------------------------------------------ 07 The Final Requiem

  private finalRequiem(): AttackDef {
    const self = this;
    return {
      id: "final_requiem", name: "The Final Requiem", index: 7, ultimate: true, interruptible: false,
      cooldown: C.requiem.cooldown,
      weight: (e) => (e.healthFraction() < 0.9 ? 5 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        self.begin(run);
        const strikes = (T.final_requiem as unknown as Record<string, { strikes: number[]; end: number }>)[run.phase === 2 ? "p2" : "p1"];
        const Q = C.requiem;
        const a = e.arena;
        const R = a.radius;
        const k0 = e.rng.int(0, 5);
        // The hall is the score: six sixths (between the floor spokes) and three bands (between the floor rings).
        const sixths = (odd: number, r0: number, r1: number): Shape[] =>
          [0, 2, 4].map((j) => new Ring(a.cx, a.cz, r0, r1, (k0 + odd + j) * 60, 60));
        const band = (r0: number, r1: number): Shape[] => [new Ring(a.cx, a.cz, r0, r1)];
        // Every measure's answer can be walked to from anywhere in the answer before it.
        // I:  sixths -> the middle band -> the other sixths -> under the bell.
        // II: the middle band -> short sixths -> the other sixths, far half only -> the walls.
        const measures: Shape[][] = run.phase === 1
          ? [sixths(0, 2.5, R + 1), band(Q.inner, Q.middle), sixths(1, 2.5, Q.middle), [new Circle(a.cx, a.cz, Q.inner)]]
          : [band(Q.inner, Q.middle), sixths(0, 2.5, Q.middle), sixths(1, Q.far, R + 1), band(Q.outer, R + 1)];
        strikes.strikes.forEach((at, i) => {
          // each measure is shown when the one before it lands, so only one answer is on the floor at a time
          const shown = i === 0 ? 1 : strikes.strikes[i - 1];
          run.at(shown, () => {
            e.hazards.strike({
              shape: new Except(a.bounds(-1), measures[i]), warn: at - shown, tag: run.tag, safe: true, damage: Q.damage,
              fx: 16, knockUp: 0.3, label: `requiem_${i + 1}`,
            });
            e.hazards.telegraph(new Ring(a.cx, a.cz, R - 0.4, R + 0.4), at - shown);        // the whole floor is in play
          });
        });
        const first = strikes.strikes[0];
        const last = strikes.strikes[strikes.strikes.length - 1];
        run.windows(first, last - first + 2, Math.max(10, strikes.end - last - 2));
      },
    };
  }
}

export const MODULE: BossModule = {
  create: (enc: Encounter): BossController => new CantorController(enc),
  arena: { structure: "abm:basilica_of_the_last_note", size: 51, height: 16, nameKey: "abm.arena.cantor" },
  helpers: ["abm:cantor_bell"],
};
