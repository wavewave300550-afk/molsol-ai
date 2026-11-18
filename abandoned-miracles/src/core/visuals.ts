/**
 * VisualEventController - all particle output goes through here.
 *
 * Telegraphs are drawn with parametric emitters: one spawnParticle call draws a
 * whole line or arc on the client, so the network cost of a telegraph is a
 * handful of packets regardless of its size. Decorative effects are thinned by
 * the VFX density setting; telegraphs never are.
 */
import { Dimension, MolangVariableMap } from "@minecraft/server";
import { CONFIG } from "../config";
import { V3 } from "./math";
import { Pen } from "./shapes";

export interface TelegraphStyle {
  /** Parametric ground line / arc / filling disc used for danger. */
  line: string;
  arc: string;
  disc: string;
  /** Same primitives in the "stand here" look. */
  safeLine: string;
  safeArc: string;
  /** Burst played at sampled points when a hazard strikes. */
  strike: string;
}

export class Visuals {
  private thin = 0;

  constructor(private readonly dim: Dimension) {}

  /** Spawn a particle that gameplay depends on (never thinned). */
  spawn(id: string, pos: V3, vars?: MolangVariableMap): void {
    try {
      this.dim.spawnParticle(id, pos, vars);
    } catch {
      /* unloaded chunk or out of range: purely cosmetic, ignore */
    }
  }

  /** Spawn a decorative particle, subject to the VFX density setting. */
  decor(id: string, pos: V3, vars?: MolangVariableMap): void {
    this.thin += CONFIG.vfx.density;
    if (this.thin < 1) return;
    this.thin -= 1;
    this.spawn(id, pos, vars);
  }

  /** Decorative particle at several points. */
  scatter(id: string, points: ReadonlyArray<{ x: number; z: number }>, y: number): void {
    for (const p of points) this.decor(id, { x: p.x, y, z: p.z });
  }

  /** A pen that draws on the floor at height y; marks last `seconds`. */
  pen(line: string, arc: string, disc: string | undefined, y: number, seconds: number): Pen {
    const life = Math.max(0.1, seconds);
    return {
      line: (ax, az, bx, bz) => {
        const len = Math.hypot(bx - ax, bz - az);
        if (len < 0.05) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.dx", (bx - ax) / len);
        m.setFloat("variable.dz", (bz - az) / len);
        m.setFloat("variable.len", len);
        m.setFloat("variable.life", life);
        this.spawn(line, { x: ax, y, z: az }, m);
      },
      arc: (cx, cz, r, a0, sweep) => {
        if (r < 0.05 || Math.abs(sweep) < 0.5) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.r", r);
        m.setFloat("variable.a0", a0);
        m.setFloat("variable.sweep", sweep);
        m.setFloat("variable.life", life);
        this.spawn(arc, { x: cx, y, z: cz }, m);
      },
      disc: (cx, cz, r) => {
        if (!disc || r < 0.05) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.r", r);
        m.setFloat("variable.life", life);
        this.spawn(disc, { x: cx, y: y - 0.02, z: cz }, m);
      },
    };
  }

  dangerPen(style: TelegraphStyle, y: number, seconds: number): Pen {
    return this.pen(style.line, style.arc, style.disc, y, seconds);
  }

  safePen(style: TelegraphStyle, y: number, seconds: number): Pen {
    return this.pen(style.safeLine, style.safeArc, undefined, y, seconds);
  }

  /**
   * Launch a projectile sprite that flies in a straight line at constant speed.
   * The caller mirrors the motion for collision (see HazardSystem.projectile).
   */
  flyer(id: string, from: V3, dir: V3, blocksPerSecond: number, seconds: number): void {
    const m = new MolangVariableMap();
    m.setSpeedAndDirection("variable.dir", blocksPerSecond, dir);
    m.setFloat("variable.life", seconds);
    this.spawn(id, from, m);
  }
}
