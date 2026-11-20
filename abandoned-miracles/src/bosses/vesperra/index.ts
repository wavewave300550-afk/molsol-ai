/**
 * Boss 001 - Vesperra, The Ivory Succession.
 *
 * A close-to-medium range anatomical fight. Her signature system is targeted
 * armour destruction: two exterior shells and the crown/face shield each have
 * their own plate health; breaking them exposes weak points and staggers her.
 * Phase II (The True Empress) opens the porcelain dress: intact shells still
 * guard their flank, broken ones are open wounds, and the Heirs gather there.
 */
import { Player } from "@minecraft/server";
import T from "../../../shared/vesperra.timings.json";
import { BossKey } from "../../config";
import { setYaw } from "../../core/facing";
import { AttackDef, AttackRun, BossController, BossModule, IncomingInfo } from "../../core/boss";
import type { Encounter } from "../../core/encounter";
import type { Helper } from "../../core/helpers";
import { V3, XZ, angDiff, dirToTheta, distXZ, localToWorld, thetaToDir, yawToTheta } from "../../core/math";
import { Circle, Lane, Polygon, Ring, sector } from "../../core/shapes";
import { trace } from "../../core/trace";
import { TelegraphStyle } from "../../core/visuals";
import { ArmorSystem, REGIONS, Region } from "./armor";
import { VESPERRA as V } from "./tuning";

const S = (id: string): string => `abm.vesperra.${id}`;
const P = (id: string): string => `abm:vesperra_${id}`;

/** Needle Procession lane orders; the index is synced to the client as the animation variant. */
const LANE_ORDERS: ReadonlyArray<readonly [number, number, number]> = [
  [-1, 0, 1], [-1, 1, 0], [0, -1, 1], [0, 1, -1], [1, -1, 0], [1, 0, -1],
];

type Beats = Record<string, number>;
const beats = (name: keyof typeof T, phase: 1 | 2): Beats =>
  (T[name] as unknown as Record<string, Beats>)[phase === 2 ? "p2" : "p1"];

export class VesperraController extends BossController {
  readonly key: BossKey = "vesperra";
  readonly displayName = "Vesperra";
  readonly phase2Name = "The True Empress";
  readonly trophyItem = "abm:ivory_diadem";
  readonly style: TelegraphStyle = {
    line: P("tg_line"), arc: P("tg_arc"), disc: P("tg_disc"),
    safeLine: P("safe_line"), safeArc: P("safe_arc"), strike: P("strike"),
  };
  readonly armor: ArmorSystem;
  readonly attacks: readonly AttackDef[];
  /** Royal Moltings performed so far (drives the shed look; capped). */
  private molts = 0;
  /** While the encounter clock is below this, she is stuck after a failed thrust and takes bonus damage. */
  private exposedUntil = 0;
  private nextIdleSound = 120;

  constructor(enc: Encounter) {
    super(enc);
    this.armor = new ArmorSystem(enc);
    this.attacks = [
      this.ivoryScythe(), this.needleProcession(), this.royalMolting(), this.cocoonEdict(),
      this.falseSubmission(), this.theHeirs(), this.coronation(),
    ];
  }

  // ------------------------------------------------------------------ framework hooks

  configure(phase: 1 | 2): void {
    const m = phase === 2 ? V.move.p2 : V.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }

  intro(): number {
    const e = this.enc;
    e.audio.play(S("intro_rise"), e.boss.location);
    return T.intro.total;
  }

  phaseTransition(): number {
    const e = this.enc;
    const t = T.transition;
    // the split throws everyone near her back a step: space for the new silhouette, no damage
    e.timeline.after(t.split, () => {
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 5.5))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: ((p.location.x - c.x) / d) * 1.6, z: ((p.location.z - c.z) / d) * 1.6 }, 0.35);
        } catch {
          /* player left */
        }
      }
      for (const r of REGIONS) e.visuals.decor(P("molt"), this.armor.anchor(r));
    }, "phase");
    return t.total;
  }

  phase2Ready(): void {
    // every Heir is recalled to the open wounds
    this.exposedUntil = 0;
  }

  death(): number {
    const e = this.enc;
    const t = T.death;
    e.timeline.after(t.crown, () => {
      this.armor.hp.c = 0;
      this.armor.sync();
      e.visuals.spawn(P("shards"), this.armor.anchor("c"));
    }, "death");
    e.timeline.after(t.collapse, () => e.visuals.scatter(P("dust"), new Circle(e.boss.location.x, e.boss.location.z, 3).sample(e.rng, 8), e.arena.floorY + 0.4), "death");
    return t.total;
  }

  position(target: Player | undefined): boolean {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const m = e.phase === 2 ? V.move.p2 : V.move.p1;
    const d = distXZ(e.boss.location, target.location);
    if (d > m.chase) {
      // stop at holding distance in front of the target, not on top of it
      const k = (d - m.hold) / d;
      const b = e.boss.location;
      e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }

  tick(): void {
    const e = this.enc;
    const now = e.timeline.now;
    if (e.sm.inCombat) this.tickHeirs(now);
    if (now >= this.nextIdleSound && e.sm.inCombat && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 140 + e.rng.int(0, 120);
    }
  }

  incoming(damage: number, info: IncomingInfo): number {
    const e = this.enc;
    const region = this.armor.classify(info);
    const out = this.armor.apply(damage, region);
    let dmg = out.damage;
    if (e.timeline.now < this.exposedUntil) dmg *= V.feint.exposedBonus;
    trace("armor_hit", { region: region ?? "body", plate: out.plateHit, broke: out.broke, damage: dmg });
    // before-event context: everything visible is deferred to the next tick
    e.defer(() => {
      this.armor.sync();
      const at: V3 = region ? this.armor.anchor(region) : localToWorld(e.boss.location, e.loco.yaw, 0, 3.6, 0.8);
      if (out.broke) {
        e.visuals.spawn(P("shards"), at);
        e.visuals.spawn(P("molt"), at);
        e.audio.play(S("armor_break"), at);
        e.stagger(V.armor.breakStagger);
        e.save();
      } else if (out.plateHit) {
        e.visuals.decor(P("strike"), at);
        e.audio.play(S("armor_hit"), at, 0.8);
      } else {
        if (region) e.visuals.decor(P("drip"), at);
        e.audio.play(S("body_hit"), at, 0.7);
      }
    });
    return dmg;
  }

  onHelperGone(h: Helper): void {
    if (h.kind === "anchor" && h.killed) {
      this.enc.audio.play(S("anchor_break"), h.entity.isValid ? h.entity.location : this.enc.boss.location);
    }
    this.enc.timeline.cancel(`heir${h.id}`);
  }

  onAttackCancelled(def: AttackDef): void {
    if (def.id === "cocoon_edict") this.enc.helpers.removeKind("anchor");
  }

  extra(): Record<string, number> {
    return { ...this.armor.save(), molt: this.molts };
  }

  restore(extra: Record<string, number>): void {
    this.armor.load(extra);
    this.molts = typeof extra.molt === "number" ? extra.molt : 0;
    this.armor.sync();
    this.enc.setProp("abm:molt", Math.min(2, this.molts));
  }

  // ------------------------------------------------------------------ shared helpers

  private dist(e: Encounter): number {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }

  private front(): number {
    return yawToTheta(this.enc.loco.yaw);
  }

  /** Chord of the arena through `p` along bearing `theta` (clipped to the arena circle). */
  private chord(p: XZ, theta: number, halfWidth: number): Lane {
    const a = this.enc.arena;
    const d = thetaToDir(theta);
    const ox = p.x - a.cx;
    const oz = p.z - a.cz;
    const b = ox * d.x + oz * d.z;
    const R = a.radius + 1;
    const disc = Math.max(0.01, b * b - (ox * ox + oz * oz - R * R));
    const t0 = -b - Math.sqrt(disc);
    const t1 = -b + Math.sqrt(disc);
    return new Lane(p.x + d.x * t0, p.z + d.z * t0, p.x + d.x * t1, p.z + d.z * t1, halfWidth);
  }

  // ------------------------------------------------------------------ 01 Ivory Scythe

  private ivoryScythe(): AttackDef {
    const self = this;
    return {
      id: "ivory_scythe", name: "Ivory Scythe", index: 1, cooldown: V.scythe.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d < 9 ? 3.2 : d < 13 ? 1.2 : 0.3;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("ivory_scythe", run.phase);
        const p2 = run.phase === 2;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const front = self.front();
        const sweep = (theta: number) => sector(b.x, b.z, 1.2, V.scythe.reach, theta, V.scythe.halfAngle);
        // first sweep: the wide frontal arc
        run.strike(t.hit1, { shape: sweep(front), warn: t.hit1 - 2, damage: V.scythe.damage, blockable: true, knock: 1.1, knockUp: 0.25, fx: 8, label: "scythe_1" });
        // second beat is chosen from where the target went, and shown before it lands
        run.at(t.decide, () => {
          const tgt = e.targeting.primary(e.timeline.now) ?? run.target;
          const warn = t.hit2 - t.decide;
          let turn = e.rng.chance(0.5);
          let aim = front + 180;
          if (tgt) {
            const d = distXZ(tgt.location, b);
            aim = dirToTheta(tgt.location.x - b.x, tgt.location.z - b.z);
            const behind = Math.abs(angDiff(front, aim)) > 95;
            if (behind || d < 5) turn = true;
            else if (d > 6.5) turn = false;
          }
          if (turn) {
            // she wheels round and sweeps the sector the target fled into
            run.variant(1);
            const yaw = aim - 90;
            for (let i = 1; i <= 8; i++) run.at(t.decide + i, () => e.loco.turnToward(yaw, 1, 24));
            run.at(t.decide + 9, () => e.loco.face(yaw));
            e.hazards.strike({ shape: sweep(aim), warn, tag: run.tag, damage: V.scythe.damage, blockable: true, knock: 1.1, knockUp: 0.25, fx: 8, label: "scythe_turn" });
          } else {
            // a cast-off crescent of shards punishes simply backing away; it flies in five
            // blades with gaps between them, so a sidestep into a gap is the answer
            run.variant(2);
            const gaps: Array<[number, number]> = [];
            for (let g = 0; g < 4; g++) gaps.push([front - 100 + 28 + g * 43, 15]);
            const band = (r: number) => new Ring(b.x, b.z, Math.max(0.5, r - 1.1), r + 1.1, front - 100, 200, gaps);
            e.hazards.telegraph(new Ring(b.x, b.z, 5.0, 13.8, front - 100, 200, gaps), warn);
            e.hazards.sweep({
              tag: run.tag, warn, duration: 12, every: 2, draw: false, shapeAt: (tt) => band(6 + tt * 0.6),
              damage: V.scythe.castDamage, blockable: true, knock: 0.8, label: "scythe_cast", fx: 3,
            });
            run.at(t.hit2, () => {
              for (let i = 0; i < 6; i++) {
                e.timeline.after(1 + i * 2, () => e.hazards.telegraphWith(P("crescent"), band(6 + i * 1.2), 6), run.tag);
              }
            });
          }
          if (p2) {
            // Phase II follow-up: a two-needle thrust down a lane fixed on the target
            run.at(t.hit2 + 2, () => {
              const tg = e.targeting.primary(e.timeline.now) ?? run.target;
              const o = e.boss.location;
              let th = yawToTheta(e.loco.yaw);
              if (tg) {
                const want = dirToTheta(tg.location.x - o.x, tg.location.z - o.z);
                if (Math.abs(angDiff(th, want)) <= 70) {
                  th = want;
                  e.loco.face(th - 90);
                }
              }
              const d = thetaToDir(th);
              const lane = new Lane(o.x + d.x * 1.5, o.z + d.z * 1.5, o.x + d.x * 12.5, o.z + d.z * 12.5, 1.3);
              e.hazards.strike({ shape: lane, warn: t.hit3 - t.hit2 - 2, tag: run.tag, damage: V.scythe.thrustDamage, blockable: true, knock: 1.4, fx: 8, label: "scythe_thrust" });
            });
          }
        });
        const last = p2 ? t.hit3 : t.hit2 + 12;
        run.windows(t.hit1, last - t.hit1 + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 02 Needle Procession

  private needleProcession(): AttackDef {
    const self = this;
    return {
      id: "needle_procession", name: "Needle Procession", index: 2, cooldown: V.procession.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 5 && d <= 17 ? 3.0 : 0.9;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("needle_procession", run.phase);
        const p2 = run.phase === 2;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const yaw = e.loco.yaw;
        const orderIndex = e.rng.int(0, LANE_ORDERS.length - 1);
        const order = LANE_ORDERS[orderIndex];
        run.variant(orderIndex);
        const C = V.procession;
        let last = 0;
        order.forEach((lane, k) => {
          const hit = t.first + k * t.gap;
          last = hit;
          let shape: Lane;
          if (p2) {
            // Phase II: the three lanes fan out from her instead of running parallel
            const d = thetaToDir(yawToTheta(yaw) + lane * C.fan);
            shape = new Lane(b.x + d.x * 1.5, b.z + d.z * 1.5, b.x + d.x * (1.5 + C.length), b.z + d.z * (1.5 + C.length), C.halfWidth);
          } else {
            const a0 = localToWorld(b, yaw, lane * C.spacing, 0, 1.5);
            const a1 = localToWorld(b, yaw, lane * C.spacing, 0, 1.5 + C.length);
            shape = new Lane(a0.x, a0.z, a1.x, a1.z, C.halfWidth);
          }
          // lanes are marked one after another in firing order, so the order can be read
          run.strike(hit, { shape, warn: hit - (t.plant + k * 4), damage: C.damage, fx: 9, sound: S("lane_erupt"), knockUp: 0.3, label: `procession_${k}` });
        });
        if (p2) {
          // ... then two lanes cross at the spot the target was standing on
          run.at(t.cross - 18, () => {
            const tg = e.targeting.primary(e.timeline.now) ?? run.target;
            const c = tg ? tg.location : localToWorld(b, yaw, 0, 0, 8);
            const th = yawToTheta(yaw);
            for (const off of [0, 90]) {
              const d = thetaToDir(th + off + 45);
              e.hazards.strike({
                shape: new Lane(c.x - d.x * 7, c.z - d.z * 7, c.x + d.x * 7, c.z + d.z * 7, C.halfWidth),
                warn: 18, tag: run.tag, damage: C.damage, fx: 8, sound: S("lane_erupt"), knockUp: 0.3, label: "procession_cross",
              });
            }
          });
          last = t.cross;
        }
        run.windows(t.plant, last - t.plant + 2, Math.max(8, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 03 Royal Molting

  private royalMolting(): AttackDef {
    const self = this;
    return {
      id: "royal_molting", name: "Royal Molting", index: 3, cooldown: V.molting.cooldown,
      weight: (e) => {
        const near = e.targeting.participants().filter((p) => distXZ(p.location, e.boss.location) < 7).length;
        return 1.6 + near * 1.1;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("royal_molting", run.phase);
        const p2 = run.phase === 2;
        const b = e.boss.location;
        const M = V.molting;
        const base = self.front() + (e.rng.chance(0.5) ? 0 : 180 / M.plates);
        const wave = (at: number, offset: number, markFrom: number) => {
          for (let i = 0; i < M.plates; i++) {
            const d = thetaToDir(base + offset + (i * 360) / M.plates);
            const from = { x: b.x + d.x * 2, y: e.arena.floorY + 1.3, z: b.z + d.z * 2 };
            // the flight path of every plate is drawn on the floor from `markFrom`; the gaps between paths are safe
            run.at(markFrom, () => e.hazards.projectile({
              tag: run.tag, delay: at - markFrom, from, dir: d, speed: M.speed, range: M.range, radius: M.radius,
              particle: P("plate"), damage: M.damage, blockable: true, knock: 0.7, label: "molting_plate",
            }));
          }
        };
        wave(t.launch, 0, 2);
        let last = t.launch;
        if (p2) {
          // Phase II: a second ring of barbed tissue fills the gaps the first one left
          wave(t.second, 180 / M.plates, t.launch + 2);
          last = t.second;
        }
        run.at(t.launch, () => {
          self.molts++;
          e.setProp("abm:molt", Math.min(2, self.molts));
          e.save();
        });
        const flight = Math.ceil(M.range / M.speed);
        run.windows(t.launch, last - t.launch + flight, Math.max(8, t.end - last - flight));
      },
    };
  }

  // ------------------------------------------------------------------ 04 Cocoon Edict

  private cocoonEdict(): AttackDef {
    const self = this;
    return {
      id: "cocoon_edict", name: "Cocoon Edict", index: 4, cooldown: V.cocoon.cooldown,
      weight: (e) => {
        if (e.helpers.count("anchor") > 0) return 0;
        const d = self.dist(e);
        return d > 8 ? 2.6 : 1.1;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("cocoon_edict", run.phase);
        const i = run.phase - 1;
        const n = V.cocoon.anchors[i];
        const radius = V.cocoon.radius[i];
        const hold = t.constrict - t.spawn;
        let pts: XZ[] = [];
        run.at(t.spawn, () => {
          // in a group she sometimes binds someone other than her main target
          const who = (e.targeting.count() > 1 && e.rng.chance(0.5) ? e.targeting.other(e.rng, run.target) : run.target) ?? run.target;
          const c = who ? e.arena.clampInside(who.location.x, who.location.z, radius + 1) : { x: e.arena.cx, z: e.arena.cz };
          const a0 = e.rng.range(0, 360);
          pts = [];
          for (let k = 0; k < n; k++) {
            const d = thetaToDir(a0 + (k * 360) / n);
            const p = { x: c.x + d.x * radius, z: c.z + d.z * radius };
            pts.push(p);
            e.helpers.spawn("abm:cocoon_anchor", e.arena.at(p, 0.05), "anchor", { lifetime: hold + 24, data: { run: run.seq } });
          }
          const y = e.arena.floorY + 1.3;
          const pen = e.visuals.pen(P("thread"), P("tg_arc"), undefined, y, hold / 20);
          for (let k = 0; k < n; k++) {
            const a = pts[k];
            const q2 = pts[(k + 1) % n];
            pen.line(a.x, a.z, q2.x, q2.z);
          }
          // the web only closes if every anchor is still standing when the time comes
          e.hazards.strike({
            shape: new Polygon(pts), warn: hold, tag: run.tag, damage: V.cocoon.damage, label: "cocoon_constrict",
            effects: [{ id: "slowness", ticks: V.cocoon.slowTicks, amp: 1 }], sound: S("cocoon_snap"),
            condition: () => {
              const alive = e.helpers.of("anchor").filter((h) => h.data.run === run.seq).length;
              if (alive < n) trace("cocoon_broken", { alive, needed: n });
              return alive >= n;
            },
          });
        });
        run.at(t.constrict + 8, () => e.helpers.removeKind("anchor"));
        run.windows(t.spawn, hold + 2, Math.max(8, t.end - t.constrict - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 05 False Submission

  private falseSubmission(): AttackDef {
    const self = this;
    return {
      id: "false_submission", name: "False Submission", index: 5, cooldown: V.feint.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d < 10 ? 1.9 : 0.5;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("false_submission", run.phase);
        const F = V.feint;
        if (run.target) e.loco.facePoint(run.target.location);
        const thrust = (cue: number, at: number, reaim: boolean) => {
          run.at(cue, () => {
            if (reaim) {
              const tg = e.targeting.primary(e.timeline.now) ?? run.target;
              if (tg) e.loco.facePoint(tg.location);
            }
            const o = e.boss.location;
            const d = thetaToDir(yawToTheta(e.loco.yaw));
            // The marked lane IS the cue: a genuine stagger never draws one.
            const lane = new Lane(o.x + d.x * 1.0, o.z + d.z * 1.0, o.x + d.x * (F.reach + 3.5), o.z + d.z * (F.reach + 3.5), F.halfWidth);
            e.hazards.strike({ shape: lane, warn: at + 3 - cue, tag: run.tag, damage: F.damage, blockable: true, knock: 1.6, knockUp: 0.3, fx: 10, label: "feint_thrust" });
            for (let k = 1; k <= t.dash; k++) {
              run.at(at + k, () => {
                e.loco.relocate({ x: o.x + d.x * F.reach * (k / t.dash), z: o.z + d.z * F.reach * (k / t.dash) });
              });
            }
          });
        };
        thrust(t.cue, t.thrust, false);
        let last = t.thrust + t.dash;
        if (run.phase === 2) {
          // Phase II: she tears herself free and thrusts again at wherever the target went
          thrust(t.cue2, t.thrust2, true);
          last = t.thrust2 + t.dash;
        }
        // needles buried: a real opening, and hits land harder while it lasts
        run.at(last, () => {
          self.exposedUntil = e.timeline.now + (t.end - last - 12);
        });
        run.windows(t.thrust, last - t.thrust + 2, Math.max(10, t.end - last - 2));
      },
    };
  }

  // ------------------------------------------------------------------ 06 The Heirs

  private theHeirs(): AttackDef {
    const self = this;
    return {
      id: "the_heirs", name: "The Heirs", index: 6, cooldown: V.heirs.cooldown,
      weight: (e) => {
        if (e.helpers.count("heir") >= V.heirs.max) return 0;
        return self.armor.anyBroken() || e.phase === 2 ? 2.4 : 0.7;
      },
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("the_heirs", run.phase);
        run.at(t.detach, () => {
          const b = e.boss.location;
          const need = V.heirs.max - e.helpers.count("heir");
          const sides = [-1, 1];
          for (let k = 0; k < need; k++) {
            const side = sides[k % 2];
            const at = localToWorld(b, e.loco.yaw, side * 2.4, 0, 0.6);
            const pos = e.arena.clampInside(at.x, at.z, 1);
            const h = e.helpers.spawn("abm:vesperra_heir", e.arena.at(pos, 0.05), "heir", {
              lifetime: V.heirs.lifetime, yaw: e.loco.yaw, data: { side, nextBite: e.timeline.now + 40, biting: 0 },
            });
            if (h) e.visuals.decor(P("molt"), { x: pos.x, y: e.arena.floorY + 0.8, z: pos.z });
          }
        });
        run.windows(t.detach, 4, Math.max(8, t.end - t.detach - 4));
      },
    };
  }

  /** Heirs stand between the attackers and whatever is exposed, and snap at anyone who closes in. */
  private tickHeirs(now: number): void {
    const e = this.enc;
    const heirs = e.helpers.of("heir");
    if (heirs.length === 0) return;
    const open = (["l", "r"] as Region[]).filter((r) => this.armor.broken(r));
    const b = e.boss.location;
    heirs.forEach((h, i) => {
      // active weak points first; otherwise escort one flank each
      const region: Region = open.length > 0 ? open[i % open.length] : h.data.side < 0 ? "l" : "r";
      const post = this.armor.anchor(region);
      const threat = e.targeting.nearest(post);
      let goal: XZ = { x: post.x, z: post.z };
      if (threat) {
        const d = distXZ(threat.location, post) || 1;
        const k = Math.min(1.4, d * 0.4) / d;
        goal = { x: post.x + (threat.location.x - post.x) * k, z: post.z + (threat.location.z - post.z) * k };
      }
      const l = h.entity.location;
      const dx = goal.x - l.x;
      const dz = goal.z - l.z;
      const d = Math.hypot(dx, dz);
      try {
        if (h.data.biting <= now && d > 0.35) {
          const step = Math.min(V.heirs.speed, d);
          const v = h.entity.getVelocity();
          h.entity.applyImpulse({ x: (dx / d) * step - v.x, y: 0, z: (dz / d) * step - v.z });
        }
        const face = threat ? threat.location : b;
        setYaw(h.entity, (Math.atan2(-(face.x - l.x), face.z - l.z) * 180) / Math.PI);
      } catch {
        return;
      }
      if (threat && now >= h.data.nextBite && distXZ(threat.location, l) <= V.heirs.biteRange) {
        h.data.nextBite = now + V.heirs.biteCooldown;
        h.data.biting = now + V.heirs.biteWarn + 6;
        try {
          h.entity.setProperty("abm:anim", 1);
        } catch {
          return;
        }
        const tag = `heir${h.id}`;
        const at = h.entity.location;
        // the rear-up and the mark under it are the warning; the snap lands where the Heir stands
        e.hazards.strike({
          shape: new Circle(at.x, at.z, V.heirs.biteRange), warn: V.heirs.biteWarn, tag, damage: V.heirs.bite, blockable: true,
          knock: 1.0, knockUp: 0.2, from: b, label: "heir_bite", condition: () => h.entity.isValid,
        });
        e.timeline.after(V.heirs.biteWarn + 6, () => {
          try {
            if (h.entity.isValid) h.entity.setProperty("abm:anim", 0);
          } catch {
            /* gone */
          }
        }, tag);
      }
    });
  }

  // ------------------------------------------------------------------ 07 Coronation of Fracture

  private coronation(): AttackDef {
    const self = this;
    return {
      id: "coronation", name: "Coronation of Fracture", index: 7, ultimate: true, interruptible: false,
      cooldown: V.coronation.cooldown,
      weight: (e) => (e.healthFraction() < 0.9 ? 5 : 0),
      run(run: AttackRun): void {
        const e = run.enc;
        const t = beats("coronation", run.phase);
        const p2 = run.phase === 2;
        const base = e.rng.range(0, 360);
        const step = 360 / 7;
        let last = 0;
        for (let i = 0; i < t.count; i++) {
          const mark = t.first + i * t.interval;
          last = mark + t.warn;
          run.at(mark, () => {
            // each path is laid through where a fighter is standing when it is marked
            const ps = e.targeting.participants();
            const who = ps.length > 0 ? ps[i % ps.length] : undefined;
            const aim: XZ = who ? { x: who.location.x, z: who.location.z } : e.arena.randomPoint(e.rng, 4);
            const theta = base + i * step;
            const paths = [self.chord(aim, theta, V.coronation.halfWidth)];
            // Phase II: every mark is a crossing pair
            if (p2) paths.push(self.chord(aim, theta + 90, V.coronation.halfWidth));
            for (const lane of paths) {
              e.hazards.strike({
                shape: lane, warn: t.warn, tag: run.tag, damage: V.coronation.damage, fx: 12,
                sound: S("fracture_erupt"), knockUp: 0.35, label: `coronation_${i}`,
                onStrike: () => e.visuals.scatter(P("fracture"), lane.sample(e.rng, 8), e.arena.floorY + 0.06),
              });
            }
          });
        }
        run.windows(t.first, last - t.first + 2, Math.max(10, t.end - last - 2));
      },
    };
  }
}

export const MODULE: BossModule = {
  create: (enc: Encounter): BossController => new VesperraController(enc),
  arena: { structure: "abm:hall_of_endless_succession", size: 45, height: 14, nameKey: "abm.arena.vesperra" },
  helpers: ["abm:vesperra_heir", "abm:cocoon_anchor"],
};
