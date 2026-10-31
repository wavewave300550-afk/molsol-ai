/**
 * Being = a script-driven creature (boss or choir follower).
 *
 * Behaviour is written as coroutines (generators) that yield the number of
 * ticks to wait, so a skill reads like a timeline:
 *     this.act("claw"); tele...; yield A.claw.marks[0]; hit...; yield ...
 * Movement is fully scripted (teleport each tick, terrain-following on the
 * ground, free in the air) because vanilla path-finding cannot handle
 * creatures five to fifteen blocks long.
 */
import { Dimension, Entity, Player, Vector3 } from "@minecraft/server";
import { ActInfo } from "../generated/data.js";
import { fightersNear, healthOf, isFighter } from "../core/combat.js";
import { groundY } from "../core/terrain.js";
import { add, angleDiff, clamp, dist, flatDir, flatDist, lerp, norm, scale, sub, yawOf, pitchOf } from "../core/vec.js";

export type Co = Generator<number | void, void, unknown>;

export interface SkillDef {
  name: string;
  phases: number[];
  cd: number;
  weight: number;
  min?: number;
  max?: number;
  when?: () => boolean;
  run: (t: Player) => Co;
}

export const beings = new Map<string, Being>();

export abstract class Being {
  readonly entity: Entity;
  readonly id: string;
  dim: Dimension;
  pos: Vector3;
  yaw = 0;
  pitch = 0;
  t = 0;
  co?: Co;
  coName = "";
  wait = 0;
  rest = 20;
  cds = new Map<string, number>();
  target?: Player;
  fighters: Player[] = [];
  flying = false;
  hp = 1;
  maxHp = 1;
  invuln = false;
  takenMul = 1;
  lastAttacker?: Player;
  removed = false;
  protected moving = 0;
  private lastMove = -1;
  private lastAct = 0;
  private pendingAct = 0;

  abstract readonly acts: Record<string, ActInfo>;
  abstract readonly walkSpeed: number; // blocks per tick at legends:move == 1

  constructor(entity: Entity) {
    this.entity = entity;
    this.id = entity.id;
    this.dim = entity.dimension;
    this.pos = { ...entity.location };
    try {
      this.yaw = entity.getRotation().y;
    } catch {
      this.yaw = 0;
    }
    const h = healthOf(entity);
    this.hp = h.cur;
    this.maxHp = h.max;
    beings.set(this.id, this);
  }

  get valid(): boolean {
    return !this.removed && this.entity.isValid;
  }

  // ---------------------------------------------------------------- properties & acts
  prop(name: string, value: number): void {
    try {
      this.entity.setProperty(`legends:${name}`, value);
    } catch {
      // entity gone
    }
  }

  act(name: string): ActInfo {
    const a = this.acts[name];
    if (!a) throw new Error(`${this.entity.typeId}: unknown act ${name}`);
    if (this.lastAct === a.id) {
      // re-trigger the same animation: drop to 0 for one tick, re-apply next tick
      this.prop("act", 0);
      this.pendingAct = a.id;
    } else {
      this.prop("act", a.id);
    }
    this.lastAct = a.id;
    return a;
  }

  endAct(): void {
    if (this.lastAct !== 0) this.prop("act", 0);
    this.lastAct = 0;
    this.pendingAct = 0;
  }

  /** Play an act to its end. */
  *play(name: string): Co {
    const a = this.act(name);
    yield a.ticks;
    this.endAct();
  }

  fx(state: number): void {
    this.prop("fx", state);
  }

  // ---------------------------------------------------------------- movement
  place(p: Vector3, yaw = this.yaw, pitch = this.pitch): void {
    this.pos = p;
    this.yaw = yaw;
    this.pitch = pitch;
    try {
      this.entity.teleport(p, { rotation: { x: pitch, y: yaw }, keepVelocity: false });
    } catch {
      // unloaded chunk
    }
  }

  face(p: Vector3, maxTurn = 25): void {
    const want = yawOf(flatDir(this.pos, p));
    const d = clamp(angleDiff(this.yaw, want), -maxTurn, maxTurn);
    if (Math.abs(d) > 0.5) this.place(this.pos, this.yaw + d, this.pitch);
  }

  faceNow(p: Vector3): void {
    this.place(this.pos, yawOf(flatDir(this.pos, p)), this.pitch);
  }

  ground(p: Vector3): Vector3 {
    return { x: p.x, y: groundY(this.dim, p.x, p.z, p.y), z: p.z };
  }

  /** One tick of ground movement towards goal at `speed` blocks/tick. Returns remaining distance. */
  walk(goal: Vector3, speed = this.walkSpeed, stopAt = 0, turn = 18): number {
    const d = flatDist(this.pos, goal);
    if (d <= stopAt + 0.05) {
      this.face(goal, turn);
      return d;
    }
    const step = Math.min(speed, d - stopAt);
    const dir = flatDir(this.pos, goal);
    const nx = this.pos.x + dir.x * step;
    const nz = this.pos.z + dir.z * step;
    const ny = groundY(this.dim, nx, nz, this.pos.y);
    const want = yawOf(dir);
    const yaw = this.yaw + clamp(angleDiff(this.yaw, want), -turn, turn);
    this.place({ x: nx, y: ny, z: nz }, yaw, 0);
    this.moving = Math.min(1, speed / Math.max(0.01, this.walkSpeed));
    return d - step;
  }

  /** One tick of free flight towards goal. */
  fly(goal: Vector3, speed: number, stopAt = 0, turn = 14): number {
    const d = dist(this.pos, goal);
    if (d <= stopAt + 0.05) {
      this.face(goal, turn);
      return d;
    }
    const dir = norm(sub(goal, this.pos));
    const step = Math.min(speed, d - stopAt);
    const np = add(this.pos, scale(dir, step));
    const fd = flatDist(this.pos, goal) > 0.3 ? yawOf(flatDir(this.pos, goal)) : this.yaw;
    this.place(np, this.yaw + clamp(angleDiff(this.yaw, fd), -turn, turn), clamp(pitchOf(dir) * 0.5, -35, 35));
    this.moving = Math.min(1, speed / Math.max(0.01, this.walkSpeed));
    return d - step;
  }

  /** Parabolic leap to dest over `ticks`, `height` blocks apex. */
  *leap(dest: Vector3, ticks: number, height: number, onTick?: (k: number) => void): Co {
    const from = { ...this.pos };
    const yaw = yawOf(flatDir(from, dest));
    for (let k = 1; k <= ticks; k++) {
      const s = k / ticks;
      const p = lerp(from, dest, s);
      p.y += Math.sin(s * Math.PI) * height;
      this.place(p, yaw, 0);
      onTick?.(k);
      yield 1;
    }
  }

  /** Straight dash along the ground. */
  *dash(dest: Vector3, speed: number, onTick?: () => void): Co {
    let guard = 200;
    while (guard-- > 0 && flatDist(this.pos, dest) > 0.4) {
      const before = flatDist(this.pos, dest);
      this.walk(dest, speed, 0, 40);
      onTick?.();
      if (flatDist(this.pos, dest) >= before - 0.01) break;
      yield 1;
    }
  }

  // ---------------------------------------------------------------- targeting
  refreshFighters(center: Vector3, radius: number): void {
    this.fighters = fightersNear(this.dim, center, radius);
  }

  pickTarget(): Player | undefined {
    const t = this.target;
    if (t && t.isValid && isFighter(t) && this.fighters.some((p) => p.id === t.id) && Math.random() > 0.004) return t;
    let best: Player | undefined;
    let bd = 1e9;
    for (const p of this.fighters) {
      const d = dist(p.location, this.pos) * (p === this.lastAttacker ? 0.7 : 1);
      if (d < bd) {
        bd = d;
        best = p;
      }
    }
    this.target = best;
    return best;
  }

  // ---------------------------------------------------------------- coroutine runner
  start(name: string, co: Co): void {
    this.co = co;
    this.coName = name;
    this.wait = 0;
  }

  interrupt(): void {
    if (this.co) {
      try {
        this.co.return();
      } catch {
        // ignore
      }
    }
    this.co = undefined;
    this.coName = "";
    this.endAct();
  }

  protected stepCo(): void {
    if (this.pendingAct) {
      this.prop("act", this.pendingAct);
      this.pendingAct = 0;
    }
    if (!this.co) return;
    if (this.wait > 0) {
      this.wait--;
      return;
    }
    let r: IteratorResult<number | void, void>;
    try {
      r = this.co.next();
    } catch (e) {
      console.warn(`[legends] ${this.entity.typeId} ${this.coName} failed: ${e}`);
      r = { done: true, value: undefined };
    }
    if (r.done) {
      this.co = undefined;
      this.coName = "";
      this.endAct();
      this.onCoDone();
    } else {
      this.wait = Math.max(0, (typeof r.value === "number" ? r.value : 1) - 1);
    }
  }

  protected onCoDone(): void {}

  syncMove(): void {
    const m = Math.round(this.moving * 10) / 10;
    if (m !== this.lastMove) {
      this.lastMove = m;
      this.prop("move", m);
    }
    this.moving = 0;
  }

  /** Called every tick by the registry. */
  abstract tick(): void;

  onDamaged(amount: number, by?: Player): void {
    if (by) this.lastAttacker = by;
  }

  dispose(): void {
    this.removed = true;
    beings.delete(this.id);
  }

  cdReady(name: string): boolean {
    return (this.cds.get(name) ?? 0) <= this.t;
  }

  setCd(name: string, ticks: number): void {
    this.cds.set(name, this.t + ticks);
  }
}
