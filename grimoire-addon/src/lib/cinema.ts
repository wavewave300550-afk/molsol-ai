import { EasingType, InputPermissionCategory, Player, Vector3, system } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { addWard, removeWard, Ward } from "./combat";
import { Scene } from "./scene";
import { hostiles } from "./targeting";

/**
 * Short cinematic camera shots for the caster of a spell (never anyone else):
 *
 *   * at most CONFIG.cinematic.maxShots per cast, each at most CONFIG.cinematic.maxSeconds long
 *   * the camera leaves the caster's eyes with an ease, follows a path of eased keys, and comes back
 *     to the caster's eyes before it is handed back - or cuts inside a flash when the spell asks
 *   * during a shot the caster takes no damage (a full ward) and their look / move / jump / crouch
 *     inputs are paused, so the view comes back exactly where it left; the spell itself carries on
 *   * every way out hands the view back: the shot's end, the scene's end (caster left, died, changed
 *     dimension, cleanup), a watchdog, and the next join (recoverCamera) after a crash
 *   * a shot is skipped when it would not be safe or comfortable: caster in the air, gliding,
 *     riding, sleeping, low on health, or with an enemy close by
 */

const CAM_FLAG = "grim:cam";
const LOCK = [InputPermissionCategory.Camera, InputPermissionCategory.LateralMovement,
  InputPermissionCategory.Jump, InputPermissionCategory.Sneak];

/** Where the camera is and what it looks at, at a moment of a shot. */
export interface CameraPose { at: Vector3; look: Vector3 }
export interface ShotOptions {
  /** ticks between path keys (each key eases linearly into the next); default 10 */
  step?: number;
  /** ticks to ease out of the caster's eyes / back into them; default 12 / 10 */
  enter?: number;
  exit?: number;
  /** end with a cut instead of easing back (hide it inside a flash) */
  cut?: boolean;
}

interface Live { ward: Ward; locked: InputPermissionCategory[]; watchdog: number; until: number }

/** The camera shots of one cast. */
export class Cinema {
  private shots = 0;
  private live?: Live;
  constructor(private scene: Scene) {
    scene.onEnd(() => this.handBack());
  }
  /** True while a shot is playing. */
  get playing(): boolean { return this.live !== undefined; }
  get count(): number { return this.shots; }

  /** Would a shot be safe and comfortable right now? */
  canShoot(): boolean {
    const p = this.scene.caster;
    if (!CONFIG.cinematic.enabled || this.live || this.shots >= CONFIG.cinematic.maxShots || !this.scene.casterOk) return false;
    try {
      if (!p.isOnGround || p.isGliding || p.isSleeping) return false;
      if (p.getComponent("minecraft:riding")) return false;
      const h = p.getComponent("minecraft:health");
      if (h && h.currentValue < h.effectiveMax * CONFIG.cinematic.minHealth) return false;
      if (hostiles(p.dimension, p.location, CONFIG.cinematic.clearRadius, p).length) return false;
      return true;
    } catch { return false; }
  }

  /**
   * Play one shot of `duration` ticks along `path(t)` (t = 0..duration).  Returns false (and does
   * nothing) when a shot cannot be played now; the spell then simply carries on in first person.
   */
  shot(duration: number, path: (t: number) => CameraPose, opts: ShotOptions = {}): boolean {
    const max = Math.round(CONFIG.cinematic.maxSeconds * 20);
    duration = Math.min(Math.round(duration), max);
    if (duration < 20 || !this.canShoot()) return false;
    const p = this.scene.caster;
    const step = Math.max(4, Math.round(opts.step ?? 10));
    const enter = Math.max(4, Math.round(opts.enter ?? 12)), exit = Math.max(4, Math.round(opts.exit ?? 10));
    const locked: InputPermissionCategory[] = [];
    try {
      for (const c of LOCK) {
        if (p.inputPermissions.isPermissionCategoryEnabled(c)) { p.inputPermissions.setPermissionCategory(c, false); locked.push(c); }
      }
      p.setDynamicProperty(CAM_FLAG, JSON.stringify(locked));
      const first = path(0);
      p.camera.setCamera("minecraft:free", { location: first.at, facingLocation: first.look,
        easeOptions: { easeTime: enter / 20, easeType: EasingType.InOutSine } });
    } catch {
      this.restoreInputs(p, locked);
      return false;
    }
    this.shots++;
    const ward = addWard({ scene: this.scene, protects: (e) => e.id === p.id, factor: 0 });
    const t0 = this.scene.tick + enter;                          // the path starts once the camera got there
    const watchdog = system.runTimeout(() => this.handBack(), enter + duration + exit + 20);
    this.live = { ward, locked, watchdog, until: t0 + duration };
    for (let a = 0; a < duration; a += step) {
      const b = Math.min(a + step, duration);
      this.scene.at(t0 + a, () => {
        if (!this.live) return;
        const q = path(b);
        try {
          p.camera.setCamera("minecraft:free", { location: q.at, facingLocation: q.look,
            easeOptions: { easeTime: (b - a) / 20, easeType: EasingType.Linear } });
        } catch { this.handBack(); }
      });
    }
    if (opts.cut) {
      this.scene.at(t0 + duration, () => this.handBack());
    } else {
      this.scene.at(t0 + duration, () => {
        if (!this.live) return;
        try {
          const head = p.getHeadLocation(), v = p.getViewDirection();
          p.camera.setCamera("minecraft:free", { location: head,
            facingLocation: { x: head.x + v.x * 8, y: head.y + v.y * 8, z: head.z + v.z * 8 },
            easeOptions: { easeTime: exit / 20, easeType: EasingType.InOutSine } });
        } catch { this.handBack(); }
      });
      this.scene.at(t0 + duration + exit, () => this.handBack());
    }
    return true;
  }

  /** Give the caster their own view back now (safe to call at any time, any number of times). */
  handBack(): void {
    const l = this.live;
    if (!l) return;
    this.live = undefined;
    try { system.clearRun(l.watchdog); } catch { /* ignore */ }
    removeWard(l.ward);
    const p = this.scene.caster;
    try {
      if (!p.isValid) return;                                    // gone: recoverCamera runs on the next join
      p.camera.clear();
      this.restoreInputs(p, l.locked);
    } catch { /* ignore */ }
  }

  private restoreInputs(p: Player, locked: InputPermissionCategory[]): void {
    try {
      if (!p.isValid) return;
      for (const c of locked) p.inputPermissions.setPermissionCategory(c, true);
      p.setDynamicProperty(CAM_FLAG, undefined);
    } catch { /* ignore */ }
  }
}

export function cinemaFor(scene: Scene): Cinema { return new Cinema(scene); }

/** A player joined or respawned: hand back a camera and inputs a crashed session left behind. */
export function recoverCamera(p: Player): void {
  try {
    const s = p.getDynamicProperty(CAM_FLAG);
    if (typeof s !== "string") return;
    p.camera.clear();
    let locked: InputPermissionCategory[] = LOCK;
    try { const a = JSON.parse(s); if (Array.isArray(a)) locked = a; } catch { /* use all */ }
    for (const c of locked) p.inputPermissions.setPermissionCategory(c, true);
    p.setDynamicProperty(CAM_FLAG, undefined);
  } catch { /* ignore */ }
}
