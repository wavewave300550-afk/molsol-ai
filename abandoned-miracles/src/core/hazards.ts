/**
 * HazardSystem - telegraphed danger regions.
 *
 * Every hazard is a Shape. The telegraph is drawn from the shape, and when the
 * warning time elapses the SAME shape is tested against the participants, so a
 * marked region and a damaging region can never disagree.
 *
 * All delayed work is scheduled on the encounter Timeline under the caller's
 * tag; cancelling the tag (attack interrupted, boss died, encounter reset)
 * removes strikes that have not happened yet.
 */
import { Player } from "@minecraft/server";
import { HitSpec } from "./damage";
import type { Encounter } from "./encounter";
import { V3, XZ } from "./math";
import { Circle, Lane, Shape } from "./shapes";
import { trace, tracing } from "./trace";

export interface StrikeOptions extends HitSpec {
  shape: Shape;
  /** Ticks between the telegraph appearing and the strike. */
  warn: number;
  /** Cancellation tag (normally the attack run's tag). */
  tag: string;
  /** Draw the shape's own outline in the SAFE style (for `Except` shapes). */
  safe?: boolean;
  /** Do not draw a telegraph (it was drawn separately, e.g. during a preview). */
  quiet?: boolean;
  /** Strike burst particles sampled inside the shape (0 = none). */
  fx?: number;
  /** Sound cue played at the shape centre when it strikes. */
  sound?: string;
  onStrike?: (victims: Player[]) => void;
  filter?: (p: Player) => boolean;
  /** Checked at strike time; when it returns false the strike fizzles (e.g. its source was destroyed). */
  condition?: () => boolean;
}

export interface SweepOptions extends HitSpec {
  tag: string;
  /** Ticks until the sweep begins (its first shape is telegraphed during this time). */
  warn: number;
  /** How long the sweep stays live, in ticks. */
  duration: number;
  /** Re-evaluate every this many ticks. */
  every?: number;
  /** Region at sweep-relative time t (0..duration). */
  shapeAt: (t: number) => Shape;
  /** Each player can be hit only once by the whole sweep (default true). */
  once?: boolean;
  /** Redraw the moving shape while live (default true). */
  draw?: boolean;
  fx?: number;
  sound?: string;
  onHit?: (p: Player) => void;
}

export interface ProjectileOptions extends HitSpec {
  tag: string;
  /** Ticks until launch. */
  delay: number;
  from: V3;
  dir: XZ;
  /** Blocks per tick. */
  speed: number;
  range: number;
  radius: number;
  /** Flyer particle id (see particles.flyer). */
  particle: string;
  /** Trail / launch sound. */
  sound?: string;
  onHit?: (p: Player) => void;
  /** Draw the whole flight path on the floor while waiting to launch (default true). */
  markPath?: boolean;
}

export class HazardSystem {
  /** Strikes resolved so far (telemetry). */
  resolved = 0;

  constructor(private readonly enc: Encounter) {}

  private get y(): number {
    return this.enc.arena.floorY + 0.08;
  }

  /** Draw a region on the floor for `ticks`, without any damage. */
  telegraph(shape: Shape, ticks: number, safe = false): void {
    const v = this.enc.visuals;
    const style = this.enc.controller.style;
    shape.draw(safe ? v.safePen(style, this.y, ticks / 20) : v.dangerPen(style, this.y, ticks / 20));
  }

  /** Draw a region with a specific arc particle (decorative variants of a telegraph). */
  telegraphWith(arcParticle: string, shape: Shape, ticks: number): void {
    const style = this.enc.controller.style;
    shape.draw(this.enc.visuals.pen(style.line, arcParticle, undefined, this.y, ticks / 20));
  }

  /** Players standing in `shape` right now. */
  inside(shape: Shape, filter?: (p: Player) => boolean): Player[] {
    const out: Player[] = [];
    for (const p of this.enc.targeting.participants()) {
      const l = p.location;
      if (!this.enc.arena.inBand(l.y)) continue;
      if (filter && !filter(p)) continue;
      if (shape.contains(l.x, l.z)) out.push(p);
    }
    return out;
  }

  /** Damage everyone inside `shape` immediately. */
  resolve(shape: Shape, spec: HitSpec, filter?: (p: Player) => boolean): Player[] {
    const victims: Player[] = [];
    for (const p of this.inside(shape, filter)) {
      if (this.enc.damage.hit(p, spec, this.enc.timeline.now) > 0) victims.push(p);
    }
    this.resolved++;
    return victims;
  }

  /** Telegraph a region now and strike it after `warn` ticks. */
  strike(o: StrikeOptions): void {
    if (!o.quiet) this.telegraph(o.shape, o.warn, o.safe);
    if (tracing()) trace("hazard", { kind: "strike", shape: o.shape, at: this.enc.timeline.now + Math.max(1, Math.round(o.warn)), tag: o.tag, label: o.label ?? "", enc: this.enc });
    this.enc.timeline.after(
      o.warn,
      () => {
        if (o.condition && !o.condition()) {
          trace("strike_fizzled", { tag: o.tag, label: o.label ?? "" });
          return;
        }
        const victims = this.resolve(o.shape, o, o.filter);
        if (o.fx) {
          this.enc.visuals.scatter(this.enc.controller.style.strike, o.shape.sample(this.enc.rng, o.fx), this.y + 0.2);
        }
        if (o.sound) this.enc.audio.play(o.sound, { x: o.shape.cx, y: this.y, z: o.shape.cz });
        trace("strike", { tag: o.tag, label: o.label ?? "", victims: victims.length });
        o.onStrike?.(victims);
      },
      o.tag,
    );
  }

  /** A region that moves or changes over time (waves, sweeping limbs, closing walls). */
  sweep(o: SweepOptions): void {
    const every = Math.max(1, o.every ?? 2);
    const once = o.once !== false;
    const draw = o.draw !== false;
    const hit = new Set<string>();
    if (o.warn > 0) this.telegraph(o.shapeAt(0), o.warn);
    if (tracing()) trace("hazard", { kind: "sweep", shapeAt: o.shapeAt, start: this.enc.timeline.now + o.warn, duration: o.duration, every, tag: o.tag, label: o.label ?? "", enc: this.enc });
    for (let t = 0; t <= o.duration; t += every) {
      this.enc.timeline.after(
        o.warn + t,
        () => {
          const shape = o.shapeAt(t);
          if (draw) this.telegraph(shape, every + 1);
          if (t === 0 && o.sound) this.enc.audio.play(o.sound, { x: shape.cx, y: this.y, z: shape.cz });
          for (const p of this.inside(shape)) {
            if (once && hit.has(p.id)) continue;
            if (this.enc.damage.hit(p, o, this.enc.timeline.now) > 0) {
              hit.add(p.id);
              o.onHit?.(p);
            }
          }
          if (o.fx && t % (every * 2) === 0) {
            this.enc.visuals.scatter(this.enc.controller.style.strike, shape.sample(this.enc.rng, o.fx), this.y + 0.2);
          }
          if (t + every > o.duration) {
            this.resolved++;
            trace("strike", { tag: o.tag, label: o.label ?? "", victims: hit.size });
          }
        },
        o.tag,
      );
    }
  }

  /**
   * A straight-flying projectile. The sprite is a client particle moving at the
   * same constant velocity the server uses for the collision circle.
   */
  projectile(o: ProjectileOptions): void {
    const life = Math.max(1, Math.round(o.range / o.speed));
    const hit = new Set<string>();
    if (o.markPath !== false && o.delay > 2) {
      this.telegraph(new Lane(o.from.x, o.from.z, o.from.x + o.dir.x * o.range, o.from.z + o.dir.z * o.range, o.radius), o.delay);
    }
    if (tracing()) {
      trace("hazard", {
        kind: "sweep", start: this.enc.timeline.now + Math.max(1, o.delay) + 1, duration: life - 1, every: 1, tag: o.tag, label: o.label ?? "", enc: this.enc,
        shapeAt: (t: number) => new Circle(o.from.x + o.dir.x * o.speed * (t + 1), o.from.z + o.dir.z * o.speed * (t + 1), o.radius),
      });
    }
    this.enc.timeline.after(
      Math.max(1, o.delay),
      () => {
        this.enc.visuals.flyer(o.particle, o.from, { x: o.dir.x, y: 0, z: o.dir.z }, o.speed * 20, life / 20);
        if (o.sound) this.enc.audio.play(o.sound, o.from);
      },
      o.tag,
    );
    for (let t = 1; t <= life; t++) {
      this.enc.timeline.after(
        Math.max(1, o.delay) + t,
        () => {
          const c = new Circle(o.from.x + o.dir.x * o.speed * t, o.from.z + o.dir.z * o.speed * t, o.radius);
          if (!this.enc.arena.contains(c.cx, c.cz, -2)) return;
          for (const p of this.inside(c)) {
            if (hit.has(p.id)) continue;
            if (this.enc.damage.hit(p, o, this.enc.timeline.now) > 0) {
              hit.add(p.id);
              o.onHit?.(p);
            }
          }
          if (t === life) {
            this.resolved++;
            trace("strike", { tag: o.tag, label: o.label ?? "", victims: hit.size });
          }
        },
        o.tag,
      );
    }
  }
}
