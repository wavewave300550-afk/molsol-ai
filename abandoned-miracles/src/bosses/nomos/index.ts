/**
 * Boss 003 - Nomos, The Unmapped Sovereign.
 *
 * An arena-control fight. Nomos does not chase; it measures. Every attack is a
 * statement about the floor - a line, a band, a border, a destination, a
 * bearing, a set of corridors, a whole projection - expressed on a logical
 * 8 x 8 survey grid (see grid.ts) and drawn before it takes effect. Nothing in
 * the world is rotated or rewritten: the "new geometry" is made of telegraphs,
 * hazards and where the boss chooses to stand.
 *
 * Phase II (There Is No North): the compass comes apart into four indicators,
 * one per quadrant. Patterns stop being anchored to where Nomos faces - they
 * arrive from other bearings, cross each other, and differ quadrant by quadrant.
 */
import { Player } from "@minecraft/server";
import T from "../../../shared/nomos.timings.json";
import { BossKey } from "../../config";
import { AttackDef, AttackRun, BossController, BossModule, IncomingInfo } from "../../core/boss";
import type { Encounter } from "../../core/encounter";
import { V3, XZ, dirToTheta, distXZ, localToWorld, normXZ, thetaToDir, wrapDeg, yawToTheta } from "../../core/math";
import { Circle, Lane, Polygon, Ring, Shape, Union } from "../../core/shapes";
import { trace } from "../../core/trace";
import { TelegraphStyle } from "../../core/visuals";
import { Bounds, QUADRANTS, QUADRANT_THETA, SurveyGrid } from "./grid";
import { Checker, Marks, Stripes } from "./patterns";
import { NOMOS as V } from "./tuning";

const S = (id: string): string => `abm.nomos.${id}`;
const P = (id: string): string => `abm:nomos_${id}`;

type Beats = Record<string, number>;
const beats = (name: keyof typeof T, phase: 1 | 2): Beats =>
  (T[name] as unknown as Record<string, Beats>)[phase === 2 ? "p2" : "p1"];

/** Bearing (theta, degrees) -> one of eight indicator steps. */
const dir8 = (theta: number): number => ((Math.round(theta / 45) % 8) + 8) % 8;

interface Config {
  danger: Shape;
  safe: Shape;
  system: number;
}

export class NomosController extends BossController {
  readonly key: BossKey = "nomos";
  readonly displayName = "Nomos";
  readonly phase2Name = "There Is No North";
  readonly trophyItem = "abm:sovereign_needle";
  readonly style: TelegraphStyle = {
    line: P("tg_line"), arc: P("tg_arc"), disc: P("tg_disc"),
    safeLine: P("safe_line"), safeArc: P("safe_arc"), strike: P("strike"),
  };
  readonly grid: SurveyGrid;
  readonly attacks: readonly AttackDef[];
  /** Encounter tick until which ink borders stand (0 = none). */
  bordersUntil = 0;
  /** Every dart direction ever locked, in order (read by tests: a locked dart never re-aims). */
  readonly dartLocks: Array<{ tick: number; ox: number; oz: number; dx: number; dz: number }> = [];
  /** Where each Unmapped Gate tried to arrive, and whether it could (read by tests). */
  readonly gateLog: Array<{ x: number; z: number; ok: boolean }> = [];
  private station: XZ | undefined;
  private stationAt = 0;
  private foldedUntil = 0;
  private poise = 0;
  private poiseSince = 0;
  private poiseLocked = 0;
  private nextIdleSound = 140;

  constructor(enc: Encounter) {
    super(enc);
    this.grid = new SurveyGrid(enc.arena);
    this.attacks = [
      this.meridianIncision(), this.latitudeShear(), this.inkBorders(), this.unmappedGate(),
      this.compassDarts(), this.foldedCountry(), this.greatRecalculation(),
    ];
  }

  // ------------------------------------------------------------------ framework hooks

  configure(phase: 1 | 2): void {
    const m = phase === 2 ? V.move.p2 : V.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }

  intro(): number {
    for (const q of QUADRANTS) this.indicate(q, 0);
    return T.intro.total;
  }

  phaseTransition(): number {
    const e = this.enc;
    const t = T.transition;
    // each quadrant is handed to its own indicator as the compass comes apart
    for (const q of QUADRANTS) {
      e.timeline.after(t.unfold + q * 6, () => {
        const c = this.grid.quadrantCentre(q);
        this.indicate(q, dir8(dirToTheta(c.x - this.grid.cx, c.z - this.grid.cz)));
        e.visuals.decor(P("grid"), e.arena.at(c, 0.1));
        e.hazards.telegraph(new Marks(c.x, c.z, (pen) => pen.arc(c.x, c.z, 2.2, 0, 360)), 30, true);
      }, "phase");
    }
    return t.total;
  }

  death(): number {
    const e = this.enc;
    e.timeline.after(T.death.collapse + 16, () => {
      const b = e.boss.location;
      e.visuals.scatter(P("dust"), new Circle(b.x, b.z, 3.5).sample(e.rng, 8), e.arena.floorY + 0.4);
    }, "death");
    return T.death.total;
  }

  /**
   * Nomos keeps its distance and works from "stations" - cell centres about nine
   * blocks from its target, on the arena-centre side - rather than closing in.
   */
  position(target: Player | undefined): boolean {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const m = e.phase === 2 ? V.move.p2 : V.move.p1;
    const now = e.timeline.now;
    const b = e.boss.location;
    const d = distXZ(b, target.location);
    if (!this.station && (d < m.near || d > m.far)) {
      const t = target.location;
      let dx = this.grid.cx - t.x;
      let dz = this.grid.cz - t.z;
      let l = Math.hypot(dx, dz);
      if (l < 2) {
        dx = b.x - t.x;
        dz = b.z - t.z;
        l = Math.hypot(dx, dz) || 1;
      }
      const want = e.arena.clampInside(t.x + (dx / l) * m.station, t.z + (dz / l) * m.station, e.stats.leashInset);
      const cell = this.grid.cellOf(want.x, want.z);
      this.station = this.grid.cellCentre(cell.c, cell.r);
      this.stationAt = now;
    }
    if (this.station) {
      const left = e.loco.goTo(this.station, 0.7);
      if (left <= 0.7 || now - this.stationAt > 160) this.station = undefined;
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }

  tick(): void {
    const e = this.enc;
    const now = e.timeline.now;
    if (!e.sm.inCombat) return;
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.5);
      this.nextIdleSound = now + 150 + e.rng.int(0, 100);
    }
    // Phase II, between attacks: every indicator watches the target from its own quadrant
    if (e.phase === 2 && !e.sm.busy && now % 20 === 0) {
      const t = e.targeting.primary(now);
      if (t) {
        for (const q of QUADRANTS) {
          const c = this.grid.quadrantCentre(q);
          if (distXZ(c, t.location) > 0.5) this.indicate(q, dir8(dirToTheta(t.location.x - c.x, t.location.z - c.z)));
        }
      }
    }
    if (now - this.poiseSince > V.poise.window) {
      this.poise = 0;
      this.poiseSince = now;
    }
  }

  incoming(damage: number, info: IncomingInfo): number {
    const e = this.enc;
    const now = e.timeline.now;
    // while it is folded out of the map there is nothing to strike
    if (now < this.foldedUntil) return 0;
    this.poise += damage;
    const tip = this.poise >= V.poise.threshold && now >= this.poiseLocked;
    if (tip) {
      this.poise = 0;
      this.poiseLocked = now + V.poise.lockout;
    }
    const at: V3 = info.projectile && info.projectile.isValid ? info.projectile.location : localToWorld(e.boss.location, e.loco.yaw, 0, 4.2, 1.2);
    e.defer(() => {
      e.audio.play(S("hit_metal"), at, 0.75);
      e.visuals.decor(P("spark"), at);
      if (tip) e.stagger(V.poise.stagger);
    });
    return damage;
  }

  onAttackCancelled(def: AttackDef): void {
    if (def.id === "ink_borders") this.bordersUntil = 0;
    this.foldedUntil = 0;
  }

  cleanup(): void {
    this.bordersUntil = 0;
    this.station = undefined;
  }

  // ------------------------------------------------------------------ shared helpers

  /** Point the indicator of quadrant q (0..3) along one of eight bearings. */
  private indicate(q: number, step: number): void {
    this.enc.setProp(`abm:q${q + 1}`, ((step % 8) + 8) % 8);
  }

  private front(): number {
    return yawToTheta(this.enc.loco.yaw);
  }

  private dist(e: Encounter): number {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }

  /** Where the given (or primary) target stands now; a point ahead of Nomos when nobody is left. */
  private aim(run: AttackRun, index = 0): XZ {
    const e = this.enc;
    const ps = e.targeting.participants();
    const who = ps.length > 0 ? ps[index % ps.length] : undefined;
    const p = index === 0 ? e.targeting.primary(e.timeline.now) ?? who ?? run.target : who;
    if (p && p.isValid) return { x: p.location.x, z: p.location.z };
    const b = e.boss.location;
    const d = thetaToDir(this.front());
    return e.arena.clampInside(b.x + d.x * 8, b.z + d.z * 8, 1);
  }

  private floorPen(line: string, ticks: number) {
    return this.enc.visuals.pen(line, P("tg_arc"), undefined, this.enc.arena.floorY + 0.08, ticks / 20);
  }

  // ------------------------------------------------------------------ 01 Meridian Incision

  private meridianIncision(): AttackDef {
    const self = this;
    return {
      id: "meridian_incision", name: "Meridian Incision", index: 1, cooldown: V.meridian.cooldown,
      weight: (e) => (self.dist(e) >= 7 ? 3.0 : 1.7),
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const M = V.meridian;
        const cut = (p: XZ, theta: number, warn: number, label: string) => {
          e.hazards.strike({ shape: g.chord(p, theta, M.halfWidth), warn, tag: run.tag, damage: M.damage, knockUp: 0.3, fx: 10, label });
        };
        if (run.phase === 1) {
          const t = beats("meridian_incision", 1);
          const p0 = self.aim(run);
          e.loco.facePoint(p0);
          let theta = self.front();
          // the meridian: from Nomos through the target, edge to edge
          run.at(t.draw1, () => {
            const p = self.aim(run);
            const b = e.boss.location;
            if (distXZ(p, b) > 0.5) theta = dirToTheta(p.x - b.x, p.z - b.z);
            cut(p, theta, t.hit1 - t.draw1, "meridian_1");
          });
          // the parallel: at right angles, through wherever the target went
          run.at(t.draw2, () => cut(self.aim(run), theta + 90, t.hit2 - t.draw2, "meridian_2"));
          run.windows(t.hit1, t.hit2 - t.hit1 + 2, Math.max(8, t.end - t.hit2 - 2));
          return;
        }
        // Phase II: three incisions on three bearings, none of them through Nomos itself
        const t = beats("meridian_incision", 2);
        const base = e.rng.int(0, 7) * 45;
        for (let i = 0; i < t.count; i++) {
          run.at(t.draw1 + i * t.gap, () => {
            const p = self.aim(run, i);
            const theta = base + i * M.fan;
            self.indicate(g.quadrantOf(p.x, p.z), dir8(theta));
            cut(p, theta, t.hit1 - t.draw1, `meridian_${i + 1}`);
          });
        }
        const last = t.hit1 + (t.count - 1) * t.gap;
        run.windows(t.hit1, last - t.hit1 + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 02 Latitude Shear

  /** Two curved bands, `o` blocks either side of the arena centre along bearing `phi`. */
  private shearBands(phi: number, o: number): Shape {
    const g = this.grid;
    const C = V.shear;
    const u = thetaToDir(phi);
    const band = (sign: number) => new Ring(g.cx + sign * u.x * C.farCentre, g.cz + sign * u.z * C.farCentre,
      C.farCentre - o - C.halfWidth, C.farCentre - o + C.halfWidth, wrapDeg(phi + (sign > 0 ? 180 : 0) - C.spread), C.spread * 2);
    return new Union([band(1), band(-1)]);
  }

  private latitudeShear(): AttackDef {
    const self = this;
    return {
      id: "latitude_shear", name: "Latitude Shear", index: 2, cooldown: V.shear.cooldown,
      weight: (e) => 1.9 + Math.min(1.2, (e.targeting.count() - 1) * 0.6),
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const C = V.shear;
        const t = beats("latitude_shear", run.phase);
        const p2 = run.phase === 2;
        const tg = self.aim(run);
        // The axis is calculated, not random: the bands close along the line on which the
        // target stands furthest from the centre, so the target is always between them.
        let phi = distXZ(tg, { x: g.cx, z: g.cz }) > 3 ? dirToTheta(tg.x - g.cx, tg.z - g.cz) : self.front();
        if (p2) phi = Math.round(phi / 45) * 45;
        const safeHalf = C.to - C.halfWidth - 0.2;
        const close = (axis: number, warn: number, label: string) => {
          e.hazards.sweep({
            tag: run.tag, warn, duration: t.duration, every: 2, shapeAt: (tt) => self.shearBands(axis, C.from - C.speed * tt),
            damage: C.damage, knockUp: 0.25, label, fx: 2, onHit: (p) => e.audio.play(S("shear_hit"), p.location, 0.9),
          });
        };
        run.at(t.mark, () => {
          for (const q of QUADRANTS) self.indicate(q, dir8(phi + (q % 2 ? 180 : 0)));
          close(phi, t.start - t.mark, "shear_1");
          // where the bands will stop is marked from the start: the lane between them
          if (!p2) e.hazards.telegraph(g.chord({ x: g.cx, z: g.cz }, phi + 90, safeHalf), t.start - t.mark + t.duration, true);
        });
        let end = t.start + t.duration;
        if (p2) {
          // Phase II: a second pair closes at right angles while the first is still moving;
          // what is left is a square at the centre (or the ground outside both pairs)
          run.at(t.start, () => {
            close(phi + 90, t.start2 - t.start, "shear_2");
            const u = thetaToDir(phi);
            const n = thetaToDir(phi + 90);
            const sq = [[1, 1], [1, -1], [-1, -1], [-1, 1]].map(([a, b]) => ({ x: g.cx + (u.x * a + n.x * b) * safeHalf, z: g.cz + (u.z * a + n.z * b) * safeHalf }));
            e.hazards.telegraph(new Polygon(sq), t.start2 - t.start + t.duration, true);
          });
          end = t.start2 + t.duration;
        }
        run.windows(t.start, end - t.start + 2, Math.max(8, t.end - end - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 03 Ink Borders

  private inkBorders(): AttackDef {
    const self = this;
    return {
      id: "ink_borders", name: "Ink Borders", index: 3, cooldown: V.borders.cooldown,
      weight: (e) => (e.timeline.now < self.bordersUntil ? 0 : 1.8),
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const B = V.borders;
        const t = beats("ink_borders", run.phase);
        const p2 = run.phase === 2;
        run.at(t.mark, () => {
          const tg = self.aim(run);
          const b = e.boss.location;
          const bb = g.bounds();
          const half = B.length / 2;
          const alongZ = (x: number, zc: number) => new Lane(x, Math.max(bb.z0 + 0.5, zc - half), x, Math.min(bb.z1 - 0.5, zc + half), B.halfWidth);
          const alongX = (z: number, xc: number) => new Lane(Math.max(bb.x0 + 0.5, xc - half), z, Math.min(bb.x1 - 0.5, xc + half), z, B.halfWidth);
          const clampX = (x: number) => Math.min(bb.x1 - 1, Math.max(bb.x0 + 1, x));
          const clampZ = (z: number) => Math.min(bb.z1 - 1, Math.max(bb.z0 + 1, z));
          // a ruled line at least two blocks from the target, on the side away from Nomos
          const ruled = (v: number, axis: "x" | "z", away: number) => {
            let line = g.snapLine(v, axis);
            if (Math.abs(line - v) < 2) line += (away >= 0 ? 1 : -1) * g.cell;
            return axis === "x" ? clampX(line) : clampZ(line);
          };
          const lanes: Lane[] = [];
          const mostlyX = Math.abs(tg.x - b.x) >= Math.abs(tg.z - b.z);
          if (!p2) {
            // one border drawn through the very spot the target stands on, across Nomos's line of approach,
            // and one along the nearest ruled line: a corner of new territory
            if (mostlyX) {
              lanes.push(alongZ(clampX(tg.x), tg.z), alongX(ruled(tg.z, "z", tg.z - b.z), tg.x));
            } else {
              lanes.push(alongX(clampZ(tg.z), tg.x), alongZ(ruled(tg.x, "x", tg.x - b.x), tg.z));
            }
          } else {
            // Phase II: four borders, a "#" around the target; every one has open ends
            const sx = tg.x <= g.cx ? 1 : -1;
            const sz = tg.z <= g.cz ? 1 : -1;
            const xa = clampX(tg.x);
            const xb = clampX(tg.x + sx * 7.5);
            const za = clampZ(tg.z - sz * 3.75);
            const zb = clampZ(tg.z + sz * 3.75);
            const xc = (xa + xb) / 2;
            lanes.push(alongZ(xa, tg.z), alongZ(xb, tg.z), alongX(za, xc), alongX(zb, xc));
            for (const q of QUADRANTS) self.indicate(q, q % 2 ? 2 : 0);
          }
          const shape = new Union(lanes);
          const warn = t.active - t.mark;
          self.bordersUntil = e.timeline.now + warn + t.life;
          trace("ink_borders", { lanes: lanes.length, until: self.bordersUntil });
          // a border is a standing hazard: touching it stings and slows, standing in it keeps stinging
          e.hazards.sweep({
            tag: run.tag, warn, duration: t.life, every: B.hitEvery, once: false, draw: false, shapeAt: () => shape,
            damage: B.damage, label: "ink_border", effects: [{ id: "slowness", ticks: B.slowTicks, amp: 0 }],
            onHit: (p) => e.audio.play(S("border_touch"), p.location, 0.8),
          });
          for (let tt = 0; tt < t.life; tt += B.redrawEvery) {
            e.timeline.after(warn + tt, () => {
              const pen = self.floorPen(P("border_line"), B.redrawEvery + 3);
              for (const l of lanes) pen.line(l.ax, l.az, l.bx, l.bz);
            }, run.tag);
          }
          e.timeline.after(warn + t.life + 1, () => {
            self.bordersUntil = 0;
          }, run.tag);
        });
        run.windows(t.active, 8, Math.max(8, t.end - t.active - 8));
      },
    };
  }

  // ------------------------------------------------------------------ 04 Unmapped Gate

  /** A validated arrival point about `offset` blocks from the target; undefined when none is safe. */
  private gateDestination(tg: XZ, from: XZ, offsets: ReadonlyArray<number>, dist: number): XZ | undefined {
    const e = this.enc;
    const base = distXZ(tg, from) > 0.5 ? dirToTheta(tg.x - from.x, tg.z - from.z) : this.front();
    for (const off of offsets) {
      const d = thetaToDir(base + off);
      const p = { x: tg.x + d.x * dist, z: tg.z + d.z * dist };
      if (!e.arena.contains(p.x, p.z, e.stats.leashInset + 0.5)) continue;
      if (distXZ(p, from) < V.gate.minJump) continue;
      if (!e.loco.canStand(p)) continue;
      return p;
    }
    return undefined;
  }

  private unmappedGate(): AttackDef {
    const self = this;
    return {
      id: "unmapped_gate", name: "Unmapped Gate", index: 4, cooldown: V.gate.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        const b = e.boss.location;
        const cornered = !e.arena.contains(b.x, b.z, 9);
        return (d > 12 ? 2.8 : 1.2) + (cornered ? 1.2 : 0);
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const G = V.gate;
        const t = beats("unmapped_gate", run.phase);
        const y = e.arena.floorY;
        const jump = (mark: number, fold: number, relocate: number, strike: number, cross: boolean) => {
          run.at(mark, () => {
            const from = e.boss.location;
            const tg = self.aim(run);
            // first choice: just beyond the target; then round it; a cross arrival sits on the target's own row or column
            const dest = cross
              ? self.gateDestination(tg, from, [0, 90, -90, 180].map((a) => a - (dirToTheta(tg.x - from.x, tg.z - from.z) % 90)), G.crossOffset)
              : self.gateDestination(tg, from, [0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180], G.offset);
            const at: XZ = dest ?? { x: from.x, z: from.z };
            self.gateLog.push({ x: at.x, z: at.z, ok: !!dest });
            trace("gate", { ok: !!dest, x: at.x, z: at.z });
            // departure coordinate: a benchmark ring where it stands
            e.hazards.telegraph(new Marks(from.x, from.z, (pen) => {
              pen.arc(from.x, from.z, 2.4, 0, 360);
              pen.line(from.x - 2.4, from.z, from.x + 2.4, from.z);
              pen.line(from.x, from.z - 2.4, from.x, from.z + 2.4);
            }), relocate - mark, true);
            e.visuals.decor(P("grid"), { x: at.x, y: y + 0.1, z: at.z });
            self.indicate(g.quadrantOf(at.x, at.z), dir8(dirToTheta(at.x - from.x, at.z - from.z)));
            // destination coordinate and what arrives with it
            const shape: Shape = cross
              ? new Union([g.chord(at, 0, G.crossHalfWidth), g.chord(at, 90, G.crossHalfWidth)])
              : new Circle(at.x, at.z, G.radius);
            e.hazards.strike({ shape, warn: strike - mark, tag: run.tag, damage: G.damage, knock: cross ? 0 : 1.2, knockUp: 0.3, from: at, fx: 12, label: cross ? "gate_cross" : "gate_arrival" });
            run.at(fold, () => {
              self.foldedUntil = e.timeline.now + (strike - fold);
            });
            run.at(relocate, () => {
              if (!dest) return;
              const now = self.aim(run);
              const ok = e.loco.relocate(dest, e.loco.yaw);
              if (ok) e.loco.facePoint(now);
              else trace("gate_blocked", { x: dest.x, z: dest.z });
            });
            run.at(strike + 1, () => {
              self.foldedUntil = 0;
            });
          });
        };
        jump(t.mark, t.fold, t.relocate, t.strike, false);
        let last = t.strike;
        if (run.phase === 2) {
          jump(t.mark2, t.fold2, t.relocate2, t.strike2, true);
          last = t.strike2;
        }
        run.windows(t.fold, last - t.fold + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 05 Compass Darts

  private compassDarts(): AttackDef {
    const self = this;
    return {
      id: "compass_darts", name: "Compass Darts", index: 5, cooldown: V.darts.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 6 ? (e.phase === 2 ? 2.9 : 2.5) : 1.2;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const D = V.darts;
        const t = beats("compass_darts", run.phase);
        const p2 = run.phase === 2;
        const b = e.boss.location;
        const yaw = e.loco.yaw;
        if (run.target) e.loco.facePoint(run.target.location);
        const volleys: Array<{ lock: number; origins: XZ[] }> = [];
        if (!p2) {
          volleys.push({ lock: t.lock, origins: [-2.7, -0.9, 0.9, 2.7].map((r) => localToWorld(b, e.loco.yaw, r, 0, 2.4)) });
        } else {
          // Phase II: the needles stand at survey stations out in the arena, not at Nomos
          volleys.push({ lock: t.lock, origins: QUADRANTS.map((q) => g.quadrantCentre(q)) });
          const r = g.half - 2;
          volleys.push({ lock: t.lock2, origins: [{ x: g.cx, z: g.cz - r }, { x: g.cx + r, z: g.cz }, { x: g.cx, z: g.cz + r }, { x: g.cx - r, z: g.cz }] });
        }
        let last = 0;
        let n = 0;
        for (const v of volleys) {
          v.origins.forEach((o, i) => {
            const index = n++;
            const lockAt = v.lock + i * t.interval;
            last = Math.max(last, lockAt + t.warn);
            const who = (): Player | undefined => {
              const ps = e.targeting.participants();
              return ps.length > 0 ? ps[index % ps.length] : undefined;
            };
            // tracking: a thin sight-line follows the target until the needle locks
            const firstTrack = Math.max(t.appear, v.lock - 26);
            for (let tt = firstTrack; tt < lockAt; tt += 4) {
              run.at(tt, () => {
                const p = who();
                if (!p) return;
                if (tt === firstTrack) e.visuals.decor(P("grid"), { x: o.x, y: e.arena.floorY + 0.1, z: o.z });
                self.floorPen(P("aim_line"), 5).line(o.x, o.z, p.location.x, p.location.z);
              });
            }
            // lock: the bearing is fixed here and is never corrected afterwards
            run.at(lockAt, () => {
              const p = who();
              const d = p && distXZ(p.location, o) > 0.3 ? normXZ(p.location.x - o.x, p.location.z - o.z) : thetaToDir(yawToTheta(yaw));
              self.dartLocks.push({ tick: e.timeline.now, ox: o.x, oz: o.z, dx: d.x, dz: d.z });
              trace("dart_lock", { index, dx: d.x, dz: d.z });
              if (p2) self.indicate(i % 4, dir8(dirToTheta(d.x, d.z)));
              e.hazards.projectile({
                tag: run.tag, delay: t.warn, from: { x: o.x, y: e.arena.floorY + D.height, z: o.z }, dir: d, speed: D.speed,
                range: D.range, radius: D.radius, particle: P("dart"), damage: D.damage, blockable: true, knock: 0.5,
                label: "compass_dart", sound: p2 ? S("dart_fire") : undefined,
              });
            });
          });
        }
        run.windows(t.lock, last - t.lock + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 06 Folded Country

  private foldedCountry(): AttackDef {
    const self = this;
    return {
      id: "folded_country", name: "Folded Country", index: 6, cooldown: V.folded.cooldown,
      weight: (e) => (self.dist(e) > 13 ? 3.1 : 2.0),
      run(run: AttackRun): void {
        const e = run.enc;
        const g = self.grid;
        const F = V.folded;
        const t = beats("folded_country", run.phase);
        const p2 = run.phase === 2;
        const tg = self.aim(run);
        const b = e.boss.location;
        e.loco.facePoint(tg);
        // corridors run ALONG the line from Nomos to its target, so backing away never leaves them
        const along = Math.abs(tg.x - b.x) >= Math.abs(tg.z - b.z) ? 0 : 90;
        const period = F.width * 2;
        const bb = g.bounds();
        const startOffset = (theta: number): number => {
          const probe = new Stripes(bb, theta, period, F.width, 0);
          const s = probe.across(tg.x, tg.z);
          return ((s % period) + period) % period < F.width ? 0 : F.width;
        };
        const offA = startOffset(along);
        const offB = startOffset(along + 90);
        let last = 0;
        for (let i = 0; i < t.count; i++) {
          const mark = t.mark + i * t.interval;
          const hit = t.hit + i * t.interval;
          last = hit;
          // Phase I: this set, the other set, this set again. Phase II: the axis turns every beat.
          const theta = p2 && i % 2 === 1 ? along + 90 : along;
          const flip = p2 ? Math.floor(i / 2) % 2 : i % 2;
          const offset = (theta === along ? offA : offB) + flip * F.width;
          const shape = new Stripes(bb, theta, period, F.width, offset);
          run.at(mark, () => {
            if (p2) for (const q of QUADRANTS) self.indicate(q, dir8(theta));
            e.hazards.telegraph(shape.complement(true), hit - mark, true);
            e.hazards.strike({ shape, warn: hit - mark, tag: run.tag, damage: F.damage, knockUp: 0.3, fx: 14, label: `folded_${i + 1}` });
          });
        }
        run.windows(t.hit, last - t.hit + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 07 The Great Recalculation

  /**
   * One "projection" of the floor inside a box. Three systems exist:
   *   0 Cartesian  a chessboard of 10-block squares, alternate squares struck out;
   *   1 polar      a disc round the arena centre and a ring further out;
   *   2 oblique    diagonal corridors.
   * `sector` (start theta) restricts the polar system to one quadrant.
   */
  private projection(system: number, b: Bounds, variant: number, sector?: number): Config {
    const g = this.grid;
    const R = V.recalc;
    if (system === 0) {
      const d = new Checker(b, R.cell, (variant % 2) as 0 | 1);
      const safe = new Marks(d.cx, d.cz, (pen) => {
        for (const c of d.centres((1 - d.parity) as 0 | 1)) pen.arc(c.x, c.z, 1.6, 0, 360);
      });
      return { danger: d, safe, system };
    }
    if (system === 1) {
      const a0 = sector ?? 0;
      const sweep = sector === undefined ? 360 : 90;
      const danger = new Union([new Ring(g.cx, g.cz, 0, R.inner, a0, sweep), new Ring(g.cx, g.cz, R.ring[0], R.ring[1], a0, sweep)]);
      const safe = new Marks(g.cx, g.cz, (pen) => {
        pen.arc(g.cx, g.cz, (R.inner + R.ring[0]) / 2, a0, sweep);
        pen.arc(g.cx, g.cz, R.ring[1] + 2.5, a0, sweep);
      });
      return { danger, safe, system };
    }
    const d = new Stripes(b, variant % 2 ? 45 : 135, R.stripe * 2, R.stripe, (variant % 4) * (R.stripe / 2));
    return { danger: d, safe: d.complement(true), system };
  }

  /** The three configurations of one Great Recalculation, fixed before anything is shown. */
  buildConfigurations(phase: 1 | 2, warn: number): Config[] {
    const e = this.enc;
    const g = this.grid;
    const order = e.rng.shuffle([0, 1, 2]);
    const out: Config[] = [];
    for (let k = 0; k < 3; k++) {
      const variant = e.rng.int(0, 7);
      let cfg: Config;
      if (phase === 1) {
        cfg = this.projection(order[k], g.bounds(), variant);
      } else {
        // Phase II: every quadrant is redrawn in a different system
        const parts = QUADRANTS.map((q) => this.projection((order[k] + q) % 3, g.quadrantBounds(q), variant + q, QUADRANT_THETA[q]));
        cfg = { danger: new Union(parts.map((p) => p.danger)), safe: new Union(parts.map((p) => p.safe)), system: order[k] };
      }
      // every state must leave a safe place a walking player can reach in the time given
      if (!g.reachable(cfg.danger, warn, V.fair.walk, V.fair.reaction)) {
        trace("unsafe_pattern", { k, system: order[k], worst: g.maxDistanceToSafety(cfg.danger) });
        cfg = this.projection(1, g.bounds(), 0);
      }
      out.push(cfg);
    }
    return out;
  }

  private greatRecalculation(): AttackDef {
    const self = this;
    return {
      id: "great_recalculation", name: "The Great Recalculation", index: 7, ultimate: true, interruptible: false,
      cooldown: V.recalc.cooldown,
      weight: (e) => (e.healthFraction() < 0.9 ? 5 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("great_recalculation", run.phase);
        const configs = self.buildConfigurations(run.phase, t.warn);
        trace("recalculation", { systems: configs.map((c) => c.system) });
        configs.forEach((cfg, k) => {
          // preview: each configuration is shown once, in order, before any of them is applied
          run.at(t.preview + k * t.previewGap, () => e.hazards.telegraph(cfg.danger, t.previewGap - 2));
          const at = t.strike + k * t.interval;
          run.at(at - t.warn, () => {
            if (run.phase === 2) for (const q of QUADRANTS) self.indicate(q, ((cfg.system + q) % 3) * 2 + k);
            e.hazards.telegraph(cfg.safe, t.warn, true);
          });
          run.strike(at, { shape: cfg.danger, warn: t.warn, damage: V.recalc.damage, knockUp: 0.35, fx: 22, label: `recalculation_${k + 1}` });
        });
        const first = t.strike - t.warn;
        const last = t.strike + 2 * t.interval;
        run.windows(first, last - first + 2, Math.max(10, t.end - last - 2));
      },
    };
  }
}

export const MODULE: BossModule = {
  create: (enc: Encounter): BossController => new NomosController(enc),
  arena: { structure: "abm:observatory_of_unwritten_borders", size: 47, height: 15, nameKey: "abm.arena.nomos" },
  helpers: [],
};
