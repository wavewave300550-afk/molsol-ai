/**
 * Locomotion - script-driven boss movement.
 *
 * Bosses carry no native AI goals; the encounter steers them. That keeps
 * positioning deterministic (the scripted target is always the one being
 * approached) and avoids pathfinding with very large collision boxes.
 *
 *   impulse  mode sets the horizontal velocity each tick; the engine's own
 *            physics handles gravity, stepping and collision.
 *   teleport mode moves in small validated steps (fallback, selectable in game).
 *
 * The body turns at a limited rate; a boss walks along its facing, so large
 * direction changes are visibly "turn, then walk".
 */
import { CONFIG } from "../config";
import type { Encounter } from "./encounter";
import { XZ, angDiff, approachAngle, dirToYaw, wrapDeg, yawToDir } from "./math";

export const enum MoveAnim {
  Idle = 0,
  Walk = 1,
  TurnLeft = 2,
  TurnRight = 3,
}

export class Locomotion {
  /** Authoritative body yaw (degrees). */
  yaw: number;
  /** Blocks per tick while walking. */
  speed = 0.1;
  /** Degrees per tick. */
  turnRate = 4;
  private anim: MoveAnim = MoveAnim.Idle;
  private moving = false;
  private progress = { x: 0, z: 0, tick: 0 };

  constructor(private readonly enc: Encounter) {
    let y = 0;
    try {
      y = enc.boss.getRotation().y;
    } catch {
      y = 0;
    }
    this.yaw = wrapDeg(y);
    const l = enc.boss.location;
    this.progress = { x: l.x, z: l.z, tick: 0 };
  }

  private setAnim(a: MoveAnim): void {
    if (a === this.anim) return;
    this.anim = a;
    this.enc.setProp("abm:move", a);
  }

  private applyYaw(): void {
    try {
      this.enc.boss.setRotation({ x: 0, y: this.yaw });
    } catch {
      /* invalid entity: the encounter tick will notice */
    }
  }

  /** Turn towards `yaw`; returns true once aligned within `tolerance` degrees. */
  turnToward(yaw: number, tolerance = 2, rate = this.turnRate): boolean {
    const d = angDiff(this.yaw, yaw);
    if (Math.abs(d) <= tolerance) {
      if (!this.moving) this.setAnim(MoveAnim.Idle);
      return true;
    }
    this.yaw = approachAngle(this.yaw, yaw, rate);
    this.applyYaw();
    if (!this.moving) this.setAnim(d > 0 ? MoveAnim.TurnRight : MoveAnim.TurnLeft);
    return Math.abs(angDiff(this.yaw, yaw)) <= tolerance;
  }

  /** Snap the body to face a yaw exactly (used when an attack commits to a direction). */
  face(yaw: number): void {
    this.yaw = wrapDeg(yaw);
    try {
      this.enc.boss.teleport(this.enc.boss.location, { rotation: { x: 0, y: this.yaw }, keepVelocity: false });
    } catch {
      this.applyYaw();
    }
  }

  facePoint(p: XZ): void {
    const l = this.enc.boss.location;
    if (Math.hypot(p.x - l.x, p.z - l.z) > 0.01) this.face(dirToYaw(p.x - l.x, p.z - l.z));
  }

  yawTo(p: XZ): number {
    const l = this.enc.boss.location;
    return dirToYaw(p.x - l.x, p.z - l.z);
  }

  /**
   * Walk towards `goal` (clamped to the boss leash). Call every tick while positioning.
   * Returns the remaining distance.
   */
  goTo(goal: XZ, stopWithin = 0.5): number {
    const boss = this.enc.boss;
    const g = this.enc.arena.clampInside(goal.x, goal.z, this.enc.stats.leashInset);
    const l = boss.location;
    const dx = g.x - l.x;
    const dz = g.z - l.z;
    const d = Math.hypot(dx, dz);
    if (d <= stopWithin) {
      this.halt();
      return d;
    }
    const want = dirToYaw(dx, dz);
    const off = Math.abs(angDiff(this.yaw, want));
    this.yaw = approachAngle(this.yaw, want, this.turnRate);
    this.applyYaw();
    if (off > 55) {
      // turn on the spot first: deliberate, readable
      this.stopVelocity();
      this.moving = false;
      this.setAnim(angDiff(this.yaw, want) > 0 ? MoveAnim.TurnRight : MoveAnim.TurnLeft);
      return d;
    }
    const k = off > 25 ? 0.55 : 1;
    const f = yawToDir(this.yaw);
    const step = Math.min(this.speed * k, d);
    this.moving = true;
    this.setAnim(MoveAnim.Walk);
    try {
      if (CONFIG.movement.mode === "impulse") {
        const v = boss.getVelocity();
        boss.applyImpulse({ x: f.x * step - v.x, y: 0, z: f.z * step - v.z });
      } else {
        boss.tryTeleport(
          { x: l.x + f.x * step, y: l.y, z: l.z + f.z * step },
          { rotation: { x: 0, y: this.yaw }, checkForBlocks: true },
        );
      }
    } catch {
      /* invalid entity */
    }
    this.watchProgress(g);
    return d;
  }

  private stopVelocity(): void {
    if (CONFIG.movement.mode !== "impulse") return;
    try {
      const v = this.enc.boss.getVelocity();
      if (Math.abs(v.x) + Math.abs(v.z) > 1e-4) this.enc.boss.applyImpulse({ x: -v.x, y: 0, z: -v.z });
    } catch {
      /* invalid entity */
    }
  }

  /** Stop walking and settle into the idle stance. */
  halt(): void {
    if (this.moving) this.stopVelocity();
    this.moving = false;
    this.setAnim(MoveAnim.Idle);
  }

  /** Something blocks the way: after ~2 s without progress, hop a short validated step. */
  private watchProgress(goal: XZ): void {
    const now = this.enc.timeline.now;
    const l = this.enc.boss.location;
    if (Math.hypot(l.x - this.progress.x, l.z - this.progress.z) > 0.6) {
      this.progress = { x: l.x, z: l.z, tick: now };
      return;
    }
    if (now - this.progress.tick < 40) return;
    this.progress = { x: l.x, z: l.z, tick: now };
    const d = Math.hypot(goal.x - l.x, goal.z - l.z) || 1;
    this.relocate({ x: l.x + ((goal.x - l.x) / d) * 1.5, z: l.z + ((goal.z - l.z) / d) * 1.5 });
  }

  /** Is there standing room for the boss at (x, z) on the arena floor? */
  canStand(p: XZ): boolean {
    if (!this.enc.arena.contains(p.x, p.z, this.enc.stats.leashInset - 0.5)) return false;
    try {
      const y = Math.floor(this.enc.arena.floorY);
      const x = Math.floor(p.x);
      const z = Math.floor(p.z);
      const floor = this.enc.dim.getBlock({ x, y: y - 1, z });
      const feet = this.enc.dim.getBlock({ x, y, z });
      const head = this.enc.dim.getBlock({ x, y: y + 2, z });
      return !!floor && !!feet && !!head && !floor.isAir && feet.isAir && head.isAir;
    } catch {
      return false;
    }
  }

  /**
   * Place the boss at a validated floor position (gate / exchange arrivals, unstick).
   * Returns false and leaves the boss where it is when the destination is not safe.
   */
  relocate(p: XZ, yaw?: number): boolean {
    const g = this.enc.arena.clampInside(p.x, p.z, this.enc.stats.leashInset);
    if (!this.canStand(g)) return false;
    if (yaw !== undefined) this.yaw = wrapDeg(yaw);
    try {
      this.enc.boss.teleport(
        { x: g.x, y: this.enc.arena.floorY + 0.05, z: g.z },
        { rotation: { x: 0, y: this.yaw }, keepVelocity: false },
      );
    } catch {
      return false;
    }
    const l = this.enc.boss.location;
    this.progress = { x: l.x, z: l.z, tick: this.enc.timeline.now };
    return true;
  }

  /** Per-tick safety net: a boss that left the arena volume is brought back. */
  enforceLeash(): void {
    const l = this.enc.boss.location;
    const a = this.enc.arena;
    const out = !a.contains(l.x, l.z, this.enc.stats.leashInset - 3) || l.y < a.floorY - 4 || l.y > a.floorY + 8;
    if (!out) return;
    const back = a.clampInside(l.x, l.z, this.enc.stats.leashInset + 1);
    if (!this.relocate(back)) this.relocate({ x: a.cx, z: a.cz });
  }
}
