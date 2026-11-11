import { Dimension, Entity, Player, system } from "@minecraft/server";
import { Fx, FxInit, ParticleVars, Rgb, flash, particle, shake, sound, spawnFx } from "../core/fx";
import { HitOptions, bodyCenter, enemiesAlong, enemiesNear, hit as busHit, isEnemy } from "../core/combat";
import { Ward, addWard, removeWard } from "../core/defense";
import { TempBlockSet } from "../core/blocks";
import { Bind, BindOptions, bind as bindTarget, endBind } from "../core/status";
import { Routine, RoutineHandle, start } from "../core/tasks";
import { V3, add, dist, dot, mul, norm, sub, v3 } from "../core/vec";
import type { SpellDef } from "./types";

export interface Aim {
  /** Point the player is aiming at (entity body, block face or max distance point). */
  point: V3;
  /** Enemy under (or very near) the crosshair, if any. */
  entity?: Entity;
  /** True when the ray stopped on a block. */
  block: boolean;
  /** Distance from the eye. */
  distance: number;
}

/** Shared helpers available to both preparation visuals and cast routines. */
abstract class SpellScope {
  readonly fxs: Fx[] = [];
  protected cleanups: (() => void)[] = [];
  constructor(
    readonly player: Player,
    readonly spell: SpellDef,
    readonly dim: Dimension,
  ) {}

  get ownerId(): string {
    return this.player.id;
  }

  /** Spawn a construct owned by this spell (auto-dissolved at cleanup). */
  fx(type: string, loc: V3, init: FxInit = {}): Fx | undefined {
    const f = spawnFx(this.player.id, this.dim, type, loc, init);
    if (f) this.fxs.push(f);
    return f;
  }

  particle(id: string, at: V3, vars: ParticleVars = {}): void {
    particle(this.dim, id, at, vars);
  }

  sound(id: string, at: V3 = this.player.location, volume = 1, pitch = 1): void {
    sound(this.dim, id, at, volume, pitch);
  }

  shake(at: V3, radius: number, intensity: number, seconds: number): void {
    shake(this.dim, at, radius, intensity, seconds);
  }

  flash(at: V3, radius: number, color: Rgb, hold = 0.1): void {
    flash(this.dim, at, radius, color, hold);
  }

  onCleanup(fn: () => void): void {
    this.cleanups.push(fn);
  }

  cleanup(dissolveTicks = 12): void {
    for (const f of this.fxs) f.dissolve(dissolveTicks);
    this.fxs.length = 0;
    const fns = this.cleanups.splice(0);
    for (const fn of fns) {
      try {
        fn();
      } catch {
        /* never let one cleanup block the others */
      }
    }
  }
}

/** Context while the player holds Use (formation visuals only, no gameplay effects). */
export class Prep extends SpellScope {
  /** Optional value handed to the cast (e.g. adopted formation constructs). */
  handoff?: Fx[];
  constructor(player: Player, spell: SpellDef) {
    super(player, spell, player.dimension);
  }
  /** Keep these constructs alive for the cast (it becomes responsible for them). */
  adopt(): Fx[] {
    const list = [...this.fxs];
    this.fxs.length = 0;
    return list;
  }
}

/** Context for an activated spell. */
export class Cast extends SpellScope {
  readonly origin: V3;
  readonly feet: V3;
  readonly dir: V3;
  readonly yaw: number;
  readonly pitch: number;
  readonly startTick = system.currentTick;
  readonly dimensionId: string;
  handle?: RoutineHandle;
  private wards: Ward[] = [];
  private tempBlocks?: TempBlockSet;
  /** Constructs handed over from the preparation phase (formation already visible). */
  adopted: Fx[] = [];
  private subs: RoutineHandle[] = [];

  /** Run a parallel routine owned by this cast (cancelled with the spell). */
  run(gen: Routine, label = "sub"): RoutineHandle {
    const h = start(gen, `${this.spell.code}:${label}`, this.player.id, 20 * 120);
    this.subs.push(h);
    return h;
  }

  /** Wait until all parallel routines finished (use inside the main routine). */
  *join(maxTicks = 20 * 30): Routine {
    for (let i = 0; i < maxTicks && this.subs.some((h) => h.alive); i++) yield 1;
  }

  constructor(
    player: Player,
    spell: SpellDef,
    /** Damage / strength multiplier (1.6 when empowered by Equilibrium Theft). */
    readonly power: number,
    readonly empowered: boolean,
  ) {
    super(player, spell, player.dimension);
    this.origin = player.getHeadLocation();
    this.feet = player.location;
    this.dir = player.getViewDirection();
    const r = player.getRotation();
    this.yaw = r.y;
    this.pitch = r.x;
    this.dimensionId = player.dimension.id;
  }

  /** Area multiplier when empowered. */
  get area(): number {
    return this.empowered ? 1.25 : 1;
  }

  /** True while the caster is online, alive-ish and in the dimension the spell was cast in. */
  get ok(): boolean {
    try {
      return this.player.isValid && this.player.dimension.id === this.dimensionId;
    } catch {
      return false;
    }
  }

  p(name: string): number {
    const v = this.spell.params[name];
    if (v === undefined) throw new Error(`${this.spell.code}: missing param ${name}`);
    return v;
  }

  /** Current eye position & look direction (live, for channelled spells). */
  eye(): V3 {
    return this.player.isValid ? this.player.getHeadLocation() : this.origin;
  }
  look(): V3 {
    return this.player.isValid ? this.player.getViewDirection() : this.dir;
  }

  enemies(center: V3, radius: number): Entity[] {
    return enemiesNear(this.player, this.dim, center, radius * this.area);
  }

  along(a: V3, b: V3, radius: number): Entity[] {
    return enemiesAlong(this.player, this.dim, a, b, radius);
  }

  isEnemy(e: Entity): boolean {
    return isEnemy(this.player, e);
  }

  /** Spell damage (scaled by empowerment). */
  hit(target: Entity, amount: number, opts: HitOptions = {}): void {
    busHit(this.player, target, amount * this.power, opts);
  }

  /** Damage + falloff by distance from a center. */
  blast(center: V3, radius: number, amount: number, onEach?: (e: Entity, k: number) => void, minK = 0.35): Entity[] {
    const list = this.enemies(center, radius);
    for (const e of list) {
      const k = Math.max(minK, 1 - dist(bodyCenter(e), center) / (radius * this.area + 0.5));
      this.hit(e, amount * k);
      onEach?.(e, k);
    }
    return list;
  }

  /** Raycast aim with soft aim-assist (helps touch players hit moving targets). */
  aim(maxDistance: number, assistDeg = 7): Aim {
    const eye = this.eye();
    const dir = this.look();
    let blockDist = maxDistance;
    let blockHit = false;
    try {
      const b = this.player.getBlockFromViewDirection({ maxDistance, includeLiquidBlocks: false, includePassableBlocks: false });
      if (b) {
        const fl = add(b.block.location, b.faceLocation);
        blockDist = Math.min(maxDistance, dist(eye, fl));
        blockHit = true;
      }
    } catch {
      /* no block */
    }
    try {
      const hits = this.player.getEntitiesFromViewDirection({ maxDistance: blockDist });
      for (const h of hits) {
        if (this.isEnemy(h.entity)) {
          return { point: bodyCenter(h.entity), entity: h.entity, block: false, distance: h.distance };
        }
      }
    } catch {
      /* none */
    }
    // aim assist: enemy closest to the ray inside a narrow cone
    const cos = Math.cos((assistDeg * Math.PI) / 180);
    let best: Entity | undefined;
    let bestScore = -1;
    for (const e of this.enemies(add(eye, mul(dir, blockDist * 0.5)), blockDist * 0.5 + 3)) {
      const c = bodyCenter(e);
      const to = sub(c, eye);
      const d = dist(c, eye);
      if (d > blockDist + 1) continue;
      const k = dot(norm(to), dir);
      if (k > cos && k > bestScore) {
        bestScore = k;
        best = e;
      }
    }
    if (best) {
      const c = bodyCenter(best);
      return { point: c, entity: best, block: false, distance: dist(c, eye) };
    }
    return { point: add(eye, mul(dir, blockDist)), block: blockHit, distance: blockDist };
  }

  /** Top surface below a point (searches down `maxDown` blocks, falls back to the point). */
  ground(p: V3, maxDown = 24): V3 {
    try {
      const hit = this.dim.getBlockFromRay(add(p, v3(0, 0.5, 0)), v3(0, -1, 0), {
        maxDistance: maxDown + 0.5,
        includeLiquidBlocks: true,
        includePassableBlocks: false,
      });
      if (hit) return { x: p.x, y: hit.block.location.y + 1, z: p.z };
    } catch {
      /* unloaded */
    }
    return { x: p.x, y: Math.floor(p.y), z: p.z };
  }

  /** Aimed ground point (where area spells land). */
  aimGround(maxDistance: number): { point: V3; target?: Entity } {
    const a = this.aim(maxDistance);
    const base = a.entity ? a.entity.location : a.point;
    return { point: this.ground(base, 30), target: a.entity };
  }

  private binds: Bind[] = [];

  /** Bind/freeze a target; the bind is released when this spell ends (whatever the reason). */
  bind(target: Entity, ticks: number, o: BindOptions = {}): Bind | undefined {
    const b = bindTarget(this.player.id, this.dim, target, ticks, o);
    if (b) this.binds.push(b);
    return b;
  }

  ward(def: Omit<Ward, "id" | "alive" | "ownerId">): Ward {
    const w = addWard({ ...def, ownerId: this.player.id });
    this.wards.push(w);
    return w;
  }

  blocks(): TempBlockSet {
    if (!this.tempBlocks) this.tempBlocks = new TempBlockSet(this.dim);
    return this.tempBlocks;
  }

  override cleanup(dissolveTicks = 12): void {
    for (const h of this.subs) if (h.alive) h.cancel("spell ended");
    this.subs.length = 0;
    for (const b of this.binds) endBind(b, true);
    this.binds.length = 0;
    for (const w of this.wards) removeWard(w);
    this.wards.length = 0;
    this.tempBlocks?.clear();
    for (const f of this.adopted) f.dissolve(dissolveTicks);
    this.adopted.length = 0;
    super.cleanup(dissolveTicks);
  }
}
