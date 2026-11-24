import { Dimension, Entity, Player, RGBA, system } from "@minecraft/server";
import { COLORS, PROJECTILES, TUNING, UNTOUCHABLE } from "../config.js";
import { emitSegment, sound } from "../core/fx.js";
import { burn, hurt, isFighter, isJoanSide, isPlayer } from "../core/targets.js";
import { add, dist, dot, len, norm, scale, sub, v, V3 } from "../core/vec.js";
import { Path, PathKind, PathOpts } from "./path.js";

/**
 * PathField - the Divine Pathway engine.
 *
 * Owns every road a caster has written, advances their life cycle, and every
 * tick physically moves whatever touches them:
 *   players     -> applyKnockback along the current (knockback resistance counts)
 *   mobs        -> velocity along the current
 *   projectiles -> re-aimed along the current, keeping their speed
 * Handles continuations (link / merge / split), mid-road junctions, reversals,
 * restless roads, crossing detection, burning contact damage and road memory.
 */
interface Rider {
  path: Path;
  s: number;
  since: number;
  lastSwitch: number;
  lastBurn: number;
}

export interface Scar {
  pts: V3[];
  flow: 1 | -1;
  kind: PathKind;
  until: number;
  nextDraw: number;
  burning: boolean;
}

export interface FieldHooks {
  onCrossing?(at: V3, a: Path, b: Path): void;
  onCaptured?(e: Entity, p: Path): void;
  onProjectile?(proj: Entity, p: Path): void;
  onReverse?(p: Path): void;
}

export const fieldStats = { carried: 0, redirected: 0, crossings: 0 };

export class PathField {
  readonly dim: Dimension;
  readonly owner: string;
  paths: Path[] = [];
  scars: Scar[] = [];
  riders = new Map<string, Rider>();
  exitCooldown = new Map<string, { pathId: number; until: number }>();
  hooks: FieldHooks = {};
  private lastSound = new Map<string, number>();
  private tickNow = 0;
  /** Projectiles that have ridden one of these roads: id -> path kind & whether it flowed towards the owner. */
  touchedProjectiles = new Map<string, { pathId: number; until: number }>();

  /** A caster's own roads never move the caster - except a player's, which exist to carry them. */
  readonly carryOwner: boolean;

  constructor(dim: Dimension, owner: string, carryOwner = false) {
    this.dim = dim;
    this.owner = owner;
    this.carryOwner = carryOwner;
  }

  // ------------------------------------------------------------------ authoring
  add(points: V3[], o: PathOpts, now: number): Path | undefined {
    if (points.length < 2) return undefined;
    const p = new Path(points, o, now);
    if (p.length < 1.0) return undefined;
    const live = this.paths.filter((q) => q.alive);
    if (live.length >= TUNING.maxPaths) {
      const oldest = live.filter((q) => q.o.kind !== "stake" && q.o.kind !== "ring").sort((a, b) => a.born - b.born)[0];
      if (oldest) oldest.endAt = Math.min(oldest.endAt, now + 5);
    }
    this.paths.push(p);
    if (p.o.visible !== false) this.drawForming(p);
    return p;
  }

  /** Reverse the current after a visible warning. */
  reverse(p: Path, warn: number, now: number): void {
    if (!p.alive || p.reverseAt >= 0) return;
    p.reverseAt = now + Math.max(1, warn);
    if (p.o.visible !== false) this.drawReverseWarn(p, warn);
  }

  /** Riders reaching the end of `a` continue on `b` (merge when several roads link to one). */
  link(a: Path, b: Path): void {
    a.next = [b];
  }

  /** Riders reaching the end of `a` are distributed over several roads. */
  split(a: Path, bs: Path[]): void {
    a.next = bs;
  }

  /** Riders passing arc length `s` of `a` are diverted onto `b`. */
  junction(a: Path, s: number, b: Path, bs: number): void {
    a.junctions.push({ s, to: b, toS: bs });
  }

  retire(p: Path, now: number, delay = 10): void {
    p.endAt = Math.min(p.endAt, Math.max(now, p.activeAt) + delay);
  }

  retireAll(now: number, delay = 10): void {
    for (const p of this.paths) this.retire(p, now, delay);
  }

  activePaths(): Path[] {
    return this.paths.filter((p) => p.isActive);
  }

  livePaths(): Path[] {
    return this.paths.filter((p) => p.alive);
  }

  riderPath(e: Entity): Path | undefined {
    return this.riders.get(e.id)?.path;
  }

  // ------------------------------------------------------------------ tick
  tick(now: number): void {
    this.tickNow = now;
    for (const p of this.paths) {
      if (p.state === "forming" && now >= p.activeAt) {
        p.state = "active";
        if (p.o.visible !== false) this.drawActivate(p);
        if (p.o.crossings) this.findCrossings(p);
      }
      if (p.state === "active" && now >= p.endAt - 20) p.state = "fading";
      if (p.reverseAt >= 0 && now >= p.reverseAt) {
        p.flow = p.flow > 0 ? -1 : 1;
        p.reverseAt = -1;
        this.hooks.onReverse?.(p);
      }
      if (p.o.restless && p.isActive && p.nextRestless >= 0 && now >= p.nextRestless && p.reverseAt < 0) {
        this.reverse(p, 14, now);
        p.nextRestless = now + p.o.restless;
      }
      if (p.alive && now >= p.endAt) {
        p.state = "dead";
        if (p.o.memory) {
          this.scars.push({ pts: p.pts.slice(), flow: p.flow, kind: p.o.kind, until: now + TUNING.memorySeconds * 20,
            nextDraw: now + 20, burning: !!p.o.burning });
          if (this.scars.length > 8) this.scars.shift();
        }
      }
    }
    if (this.paths.some((p) => !p.alive)) {
      this.paths = this.paths.filter((p) => p.alive);
      for (const [id, r] of this.riders) if (!r.path.alive) this.riders.delete(id);
    }
    this.scars = this.scars.filter((s) => s.until > now);
    const active = this.activePaths();
    if (active.length) this.physics(active, now);
    else this.riders.clear();
    this.render(now);
  }

  // ------------------------------------------------------------------ physics
  private physics(active: Path[], now: number): void {
    let minX = Infinity, minY = Infinity, minZ = Infinity, maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
    for (const p of active) {
      minX = Math.min(minX, p.min.x); minY = Math.min(minY, p.min.y); minZ = Math.min(minZ, p.min.z);
      maxX = Math.max(maxX, p.max.x); maxY = Math.max(maxY, p.max.y); maxZ = Math.max(maxZ, p.max.z);
    }
    const c = v((minX + maxX) / 2, (minY + maxY) / 2, (minZ + maxZ) / 2);
    const r = dist(v(minX, minY, minZ), v(maxX, maxY, maxZ)) / 2 + 4;
    let ents: Entity[] = [];
    try {
      ents = this.dim.getEntities({ location: c, maxDistance: r });
    } catch {
      return;
    }
    const seen = new Set<string>();
    for (const e of ents) {
      if (!e.isValid || (e.id === this.owner && !this.carryOwner)) continue;
      const type = e.typeId;
      const isProj = PROJECTILES.has(type);
      if (!isProj && (UNTOUCHABLE.has(type) || isJoanSide(e))) continue;
      const player = isPlayer(e);
      if (player && !isFighter(e)) continue;
      seen.add(e.id);
      this.carry(e, active, now, isProj, player);
    }
    for (const id of [...this.riders.keys()]) if (!seen.has(id)) this.riders.delete(id);
    for (const [id, cd] of this.exitCooldown) if (cd.until < now) this.exitCooldown.delete(id);
    for (const [id, t] of this.touchedProjectiles) if (t.until < now) this.touchedProjectiles.delete(id);
  }

  private allowed(p: Path, isProj: boolean, player: boolean, e: Entity): boolean {
    if (p.o.accept && !p.o.accept(e)) return false;
    if (isProj) return p.o.carryProjectiles !== false && !(p.o.ownerIsPlayer && this.projectileOwnedByPlayer(e));
    if (player) return p.o.carryPlayers !== false;
    return p.o.carryMobs !== false;
  }

  private projectileOwnedByPlayer(e: Entity): boolean {
    try {
      const owner = e.getComponent("minecraft:projectile")?.owner;
      return !!owner && owner.typeId === "minecraft:player";
    } catch {
      return false;
    }
  }

  private carry(e: Entity, active: Path[], now: number, isProj: boolean, player: boolean): void {
    const pos = e.location;
    const body = isProj ? pos : add(pos, v(0, 0.6, 0));
    let rider = this.riders.get(e.id);
    const cd = this.exitCooldown.get(e.id);
    let best: { p: Path; s: number; c: V3; score: number } | undefined;
    for (const p of active) {
      if (!this.allowed(p, isProj, player, e)) continue;
      if (cd && cd.pathId === p.id) continue;
      const margin = p.o.radius + (isProj ? 2.5 : 1.5);
      if (!p.inBounds(pos, margin)) continue;
      const n = p.nearest(isProj || p.o.aerial ? body : pos);
      let ok: boolean;
      if (isProj) ok = n.d <= p.o.radius + 0.7;
      else if (p.o.aerial) ok = n.d <= p.o.radius;
      else {
        const band = p.o.band ?? [-0.8, 0.85];
        ok = n.dh <= p.o.radius && n.dy >= band[0] && n.dy <= band[1];
      }
      if (!ok) continue;
      let score = n.d;
      if (rider && rider.path === p) score -= 0.6;
      if (rider && rider.path !== p && p.o.switching && now - rider.lastSwitch > 24) score -= 1.2;
      if (!best || score < best.score) best = { p, s: n.s, c: n.c, score };
    }
    if (!best) {
      if (rider) this.riders.delete(e.id);
      return;
    }
    let p = best.p;
    let s = best.s;
    if (!rider || rider.path !== p) {
      const switched = !!rider;
      rider = { path: p, s, since: now, lastSwitch: switched ? now : -999, lastBurn: now };
      this.riders.set(e.id, rider);
      if (isProj) {
        fieldStats.redirected++;
        this.touchedProjectiles.set(e.id, { pathId: p.id, until: now + 100 });
        this.hooks.onProjectile?.(e, p);
      } else this.hooks.onCaptured?.(e, p);
    }
    rider.s = s;
    if (p.o.maxRide && now - rider.since >= p.o.maxRide) {
      p.o.onEnd?.(e, p);
      if (e.isValid) this.fling(e, p, p.dirAt(s), isProj, isProj ? Math.max(len(this.velocityOf(e)), 1.2) : p.o.speed);
      this.riders.delete(e.id);
      this.exitCooldown.set(e.id, { pathId: p.id, until: now + 16 });
      return;
    }
    const sneaking = player && (e as Player).isSneaking;
    const speed = isProj ? Math.max(len(this.velocityOf(e)), 0.85) : p.o.speed * (sneaking ? 0.4 : 1);
    // mid-road junctions
    const nextS = s + p.flow * Math.max(speed, 0.3);
    for (const j of p.junctions) {
      if (!j.to.isActive) continue;
      const crossed = p.flow > 0 ? s <= j.s && nextS >= j.s : s >= j.s && nextS <= j.s;
      if (crossed) {
        p = j.to;
        s = j.toS;
        rider.path = p;
        rider.s = s;
        rider.lastSwitch = now;
        break;
      }
    }
    // end of the current: continue, split, or release
    if (!p.o.loop && p.remaining(s) < Math.max(0.7, speed * 1.5)) {
      if (p.next.length) {
        const live = p.next.filter((q) => q.alive);
        if (live.length) {
          const nxt = live[p.branchCounter++ % live.length];
          rider.path = nxt;
          rider.s = nxt.startS;
          rider.lastSwitch = now;
          p = nxt;
          s = nxt.startS;
        }
      } else {
        const dir = p.dirAt(s);
        p.o.onEnd?.(e, p);
        if (e.isValid) this.fling(e, p, dir, isProj, speed);
        this.riders.delete(e.id);
        this.exitCooldown.set(e.id, { pathId: p.id, until: now + 14 });
        return;
      }
    }
    // velocity along the current
    const dir = p.dirAt(s);
    const c = p.pointAt(s);
    const ref = isProj || p.o.aerial ? body : pos;
    const toC = sub(c, ref);
    const lat = sub(toC, scale(dir, dot(toC, dir)));
    const pull = sneaking ? 0 : (p.o.pull ?? 0.18);
    let vel = add(scale(dir, speed), scale(lat, isProj ? 0.4 : pull));
    if (!isProj && !p.o.aerial) vel = v(vel.x, Math.max(0, dir.y * speed), vel.z);
    if (!isProj && p.o.aerial) vel = v(vel.x, vel.y + 0.04, vel.z);
    this.setVelocity(e, vel, player);
    fieldStats.carried++;
    // burning roads scorch what they carry
    if (p.o.burning && !isProj && now - rider.lastBurn >= 20) {
      rider.lastBurn = now;
      hurt(e, p.o.damage ?? 1.5, undefined);
      burn(e, 2);
    }
  }

  private velocityOf(e: Entity): V3 {
    try {
      return e.getVelocity();
    } catch {
      return v(0, 0, 0);
    }
  }

  private setVelocity(e: Entity, vel: V3, player: boolean): void {
    try {
      if (player) (e as Player).applyKnockback({ x: vel.x, z: vel.z }, vel.y);
      else {
        e.clearVelocity();
        e.applyImpulse(vel);
      }
    } catch {
      // entity refuses
    }
  }

  private fling(e: Entity, p: Path, dir: V3, isProj: boolean, speed: number): void {
    const aim = p.o.aim?.(e, p);
    const k = p.o.fling ?? 1;
    if (isProj) {
      const d = aim ? norm(sub(aim, e.location)) : dir;
      this.setVelocity(e, scale(d, Math.max(speed, 1.1) * k), false);
    } else if (p.o.fling) {
      const d = aim ? norm(sub(aim, e.location)) : dir;
      this.setVelocity(e, v(d.x * p.o.speed * k, 0.28, d.z * p.o.speed * k), isPlayer(e));
    }
  }

  /** Was this projectile carried by one of these roads recently? */
  wasRedirected(e: Entity): boolean {
    return this.touchedProjectiles.has(e.id);
  }

  // ------------------------------------------------------------------ crossings
  private findCrossings(p: Path): void {
    const found: V3[] = [];
    for (const q of this.paths) {
      if (q === p || !q.alive || q.state === "forming") continue;
      if (!(p.o.burning || q.o.burning)) continue;
      for (let i = 0; i + 2 < p.pts.length; i += 2) {
        const a1 = p.pts[i];
        const a2 = p.pts[i + 2];
        for (let j = 0; j + 2 < q.pts.length; j += 2) {
          const b1 = q.pts[j];
          const b2 = q.pts[j + 2];
          const hit = segXZ(a1, a2, b1, b2);
          if (!hit) continue;
          if (Math.abs(hit.ya - hit.yb) > 1.6) continue;
          const at = v(hit.x, Math.max(hit.ya, hit.yb), hit.z);
          if (found.some((f) => dist(f, at) < 2.2)) continue;
          found.push(at);
          fieldStats.crossings++;
          this.hooks.onCrossing?.(at, p, q);
          if (found.length >= 4) return;
        }
      }
    }
  }

  // ------------------------------------------------------------------ rendering
  colors(p: Path): { flow: RGBA; chev: RGBA } {
    if (p.o.color) return { flow: p.o.color, chev: p.o.chevron ?? p.o.color };
    if (p.o.burning) return { flow: COLORS.burning, chev: COLORS.burningGold };
    switch (p.o.kind) {
      case "player":
        return { flow: COLORS.player, chev: COLORS.white };
      case "trail":
        return { flow: COLORS.trail, chev: COLORS.roadGold };
      case "false":
        return { flow: COLORS.road, chev: COLORS.false };
      default:
        return { flow: COLORS.road, chev: COLORS.roadGold };
    }
  }

  private segments(p: Path): [V3, V3][] {
    const out: [V3, V3][] = [];
    const n = p.pts.length;
    for (let k = 1; k < p.segs.length; k++) {
      const a = p.pts[p.segs[k - 1] % n];
      const b = p.pts[p.segs[k] % n];
      out.push(p.flow > 0 ? [a, b] : [b, a]);
    }
    return p.flow > 0 ? out : out.reverse();
  }

  private viewers(at: V3): boolean {
    try {
      return this.dim.getPlayers({ location: at, maxDistance: 80 }).length > 0;
    } catch {
      return false;
    }
  }

  private render(now: number): void {
    for (const p of this.paths) {
      if (p.o.visible === false || !p.isActive) continue;
      const every = p.o.renderEvery ?? 10;
      const flowNow = (now + p.id) % every === 0;
      const chevNow = p.o.chevrons !== false && (now + p.id * 7) % (every * 2) === 0;
      const fireNow = !!p.o.burning && (now + p.id) % 10 === 5;
      if (!flowNow && !chevNow && !fireNow) continue;
      if (!this.viewers(p.center)) continue;
      const col = this.colors(p);
      const visSpeed = Math.max(3, p.o.speed * 20 * 0.9);
      const fade = p.state === "fading" ? 0.55 : 1;
      const flowCol = { ...col.flow, alpha: col.flow.alpha * fade };
      const segs = this.segments(p);
      if (flowNow) {
        const life = Math.max(0.6, every / 20 + 0.1);
        for (const [a, b] of segs) emitSegment(this.dim, "joan:road_flow", a, b, { speed: visSpeed, life, color: flowCol, size: p.o.aerial ? 1.2 : 1 });
      }
      if (chevNow && p.reverseAt < 0) {
        for (const [a, b] of segs) emitSegment(this.dim, "joan:road_chevron", a, b, { speed: visSpeed, life: 1.1, color: { ...col.chev, alpha: fade }, size: 1 });
      }
      if (fireNow) {
        segs.forEach(([a, b], i) => {
          if (i % 2 === 0) emitSegment(this.dim, "joan:road_fire", a, b, { life: 0.55, size: 1 });
        });
      }
    }
    for (const s of this.scars) {
      if (now < s.nextDraw) continue;
      s.nextDraw = now + 30;
      if (!this.viewers(s.pts[Math.floor(s.pts.length / 2)])) continue;
      for (let i = 0; i + 4 < s.pts.length; i += 4) {
        emitSegment(this.dim, "joan:road_scar", s.pts[i], s.pts[i + 4], { life: 1.6, color: s.burning ? COLORS.ember : COLORS.scar, size: 1 });
      }
    }
  }

  private drawForming(p: Path): void {
    const segs = this.segments(p);
    const lifeS = Math.max(0.3, (p.activeAt - p.born) / 20 + 0.15);
    const writeTicks = Math.max(1, Math.floor((p.activeAt - p.born) * 0.45));
    const col = p.o.kind === "player" ? COLORS.player : COLORS.ink;
    const center = p.center;
    if (!this.viewers(center)) return;
    this.throttledSound("joan.path.form", p.pts[0], 0.8, p.o.burning ? 0.8 : 1.0);
    segs.forEach(([a, b], i) => {
      const delay = Math.floor((i / Math.max(1, segs.length)) * writeTicks);
      const remaining = Math.max(0.2, lifeS - delay / 20);
      const go = () => {
        emitSegment(this.dim, "joan:road_ink", a, b, { life: remaining, color: col, size: 1 });
        emitSegment(this.dim, "joan:road_ink_chevron", a, b, { life: remaining, color: col, size: 1 });
      };
      if (delay <= 0) go();
      else system.runTimeout(go, delay);
    });
  }

  private drawActivate(p: Path): void {
    const segs = this.segments(p);
    if (!this.viewers(p.center)) return;
    const col = this.colors(p);
    for (const [a, b] of segs) emitSegment(this.dim, "joan:road_flow", a, b, { speed: 14, life: 0.35, color: col.chev, size: 1.4 });
    this.throttledSound("joan.path.active", p.pointAt(p.length / 2), 0.7, p.o.burning ? 0.75 : 1);
  }

  private drawReverseWarn(p: Path, warn: number): void {
    // still chevrons pointing the NEW way, in warning red-gold
    const segs = this.segments(p).map(([a, b]) => [b, a] as [V3, V3]);
    for (const [a, b] of segs) emitSegment(this.dim, "joan:road_ink_chevron", a, b, { life: warn / 20 + 0.1, color: COLORS.warn, size: 1.3 });
    this.throttledSound("joan.path.reverse", p.pointAt(p.length / 2), 0.8, 1);
  }

  /** Several roads written at once share one sound cue. */
  private throttledSound(id: string, at: V3, volume: number, pitch: number): void {
    const last = this.lastSound.get(id) ?? -999;
    if (this.tickNow - last < 5) return;
    this.lastSound.set(id, this.tickNow);
    sound(this.dim, id, at, volume, pitch);
  }
}

function segXZ(a1: V3, a2: V3, b1: V3, b2: V3): { x: number; z: number; ya: number; yb: number } | undefined {
  const d1x = a2.x - a1.x;
  const d1z = a2.z - a1.z;
  const d2x = b2.x - b1.x;
  const d2z = b2.z - b1.z;
  const den = d1x * d2z - d1z * d2x;
  if (Math.abs(den) < 1e-9) return undefined;
  const t = ((b1.x - a1.x) * d2z - (b1.z - a1.z) * d2x) / den;
  const u = ((b1.x - a1.x) * d1z - (b1.z - a1.z) * d1x) / den;
  if (t < 0 || t > 1 || u < 0 || u > 1) return undefined;
  return { x: a1.x + d1x * t, z: a1.z + d1z * t, ya: a1.y + (a2.y - a1.y) * t, yb: b1.y + (b2.y - b1.y) * u };
}
