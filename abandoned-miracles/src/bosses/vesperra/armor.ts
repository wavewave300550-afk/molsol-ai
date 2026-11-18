/**
 * Vesperra's armour regions.
 *
 * Bedrock gives an entity one damageable volume: neither minecraft:collision_box
 * nor minecraft:custom_hit_test tells a script WHICH part was struck. So the
 * regions are scripted. When Vesperra is about to take damage, the hit is
 * classified geometrically against three oriented boxes that follow her
 * position and facing exactly (they are computed from them, not attached
 * entities, so they cannot lag, desync, unload or be orphaned):
 *
 *   melee      the attacker's eye ray is intersected with the region boxes and
 *              with her core; the first box the ray enters is the region hit;
 *   projectile the projectile's impact position is tested against the boxes.
 *
 * Each region has its own plate health and three visible states (intact,
 * cracked, destroyed) mirrored to the client through synced properties.
 */
import { Entity, Player } from "@minecraft/server";
import type { IncomingInfo } from "../../core/boss";
import type { Encounter } from "../../core/encounter";
import { V3, localToWorld, worldToLocal, yawToDir } from "../../core/math";
import { VESPERRA } from "./tuning";

export type Region = "l" | "r" | "c";
export const REGIONS: readonly Region[] = ["l", "r", "c"];

interface Box {
  r0: number; r1: number; // right (negative = her left)
  u0: number; u1: number; // up
  f0: number; f1: number; // forward
}

/** Region volumes in Vesperra's own frame, in blocks. Phase II shells stand open, so they reach further. */
function boxes(phase: 1 | 2): Record<Region | "core" | "chest", Box> {
  const wing = phase === 2;
  return {
    l: wing ? { r0: -3.7, r1: -0.45, u0: 2.5, u1: 6.5, f0: -2.3, f1: 1.3 } : { r0: -2.2, r1: -0.45, u0: 2.3, u1: 5.5, f0: -1.4, f1: 1.4 },
    r: wing ? { r0: 0.45, r1: 3.7, u0: 2.5, u1: 6.5, f0: -2.3, f1: 1.3 } : { r0: 0.45, r1: 2.2, u0: 2.3, u1: 5.5, f0: -1.4, f1: 1.4 },
    c: { r0: -0.65, r1: 0.65, u0: 5.3, u1: 7.5, f0: -0.3, f1: 1.0 },
    // what is NOT a region but still stops a blade: the skirt and abdomen, and the slim upper chest
    core: { r0: -0.45, r1: 0.45, u0: 2.3, u1: 4.3, f0: -1.3, f1: 1.3 },
    chest: { r0: -0.45, r1: 0.45, u0: 4.3, u1: 5.3, f0: -0.45, f1: 0.45 },
  };
}

/** Distance along a ray to the point where it enters a box, or Infinity. */
function rayBox(o: [number, number, number], d: [number, number, number], b: Box, pad: number): number {
  const lo = [b.r0 - pad, b.u0 - pad, b.f0 - pad];
  const hi = [b.r1 + pad, b.u1 + pad, b.f1 + pad];
  let tmin = 0;
  let tmax = 9;
  for (let i = 0; i < 3; i++) {
    if (Math.abs(d[i]) < 1e-9) {
      if (o[i] < lo[i] || o[i] > hi[i]) return Infinity;
      continue;
    }
    let t1 = (lo[i] - o[i]) / d[i];
    let t2 = (hi[i] - o[i]) / d[i];
    if (t1 > t2) [t1, t2] = [t2, t1];
    tmin = Math.max(tmin, t1);
    tmax = Math.min(tmax, t2);
    if (tmin > tmax) return Infinity;
  }
  return tmin;
}

function inBox(p: [number, number, number], b: Box, pad: number): boolean {
  return p[0] >= b.r0 - pad && p[0] <= b.r1 + pad && p[1] >= b.u0 - pad && p[1] <= b.u1 + pad && p[2] >= b.f0 - pad && p[2] <= b.f1 + pad;
}

export interface ArmorOutcome {
  damage: number;
  region: Region | undefined;
  broke: boolean;
  plateHit: boolean;
}

export class ArmorSystem {
  /** Remaining plate health per region. */
  hp: Record<Region, number> = { ...VESPERRA.armor.plate };

  constructor(private readonly enc: Encounter) {}

  /** 0 intact, 1 cracked, 2 destroyed - the value synced to the client. */
  state(r: Region): 0 | 1 | 2 {
    const max = VESPERRA.armor.plate[r];
    return this.hp[r] <= 0 ? 2 : this.hp[r] <= max * 0.5 ? 1 : 0;
  }

  broken(r: Region): boolean {
    return this.hp[r] <= 0;
  }

  anyBroken(): boolean {
    return REGIONS.some((r) => this.broken(r));
  }

  /** World position of a region's centre (for effects and Heir guard posts). */
  anchor(r: Region): V3 {
    const o = this.enc.boss.location;
    const yaw = this.enc.loco.yaw;
    if (r === "c") return localToWorld(o, yaw, 0, 6.3, 0.5);
    return localToWorld(o, yaw, r === "l" ? -1.6 : 1.6, 3.8, 0);
  }

  private toLocal(p: V3): [number, number, number] {
    const l = worldToLocal(this.enc.boss.location, this.enc.loco.yaw, p);
    return [l.right, l.up, l.fwd];
  }

  /** Which region does this hit land on? Pure geometry; safe inside a before-event. */
  classify(info: IncomingInfo): Region | undefined {
    const bx = boxes(this.enc.phase);
    if (info.projectile && info.projectile.isValid) {
      return this.classifyPoint(this.toLocal(info.projectile.location), bx);
    }
    const a = info.attacker;
    if (!a || !a.isValid) return undefined;
    let eye: V3;
    let view: V3;
    try {
      eye = a instanceof Player ? a.getHeadLocation() : this.headOf(a);
      view = a.getViewDirection();
    } catch {
      return undefined;
    }
    const o = this.toLocal(eye);
    const f = yawToDir(this.enc.loco.yaw);
    const rgt = { x: -f.z, z: f.x };
    const d: [number, number, number] = [view.x * rgt.x + view.z * rgt.z, view.y, view.x * f.x + view.z * f.z];
    let best: Region | undefined;
    let bt = Math.min(rayBox(o, d, bx.core, 0), rayBox(o, d, bx.chest, 0));
    for (const r of REGIONS) {
      const t = rayBox(o, d, bx[r], 0.2);
      if (t < bt) {
        bt = t;
        best = r;
      }
    }
    return best;
  }

  private headOf(e: Entity): V3 {
    try {
      return e.getHeadLocation();
    } catch {
      return e.location;
    }
  }

  private classifyPoint(p: [number, number, number], bx: Record<Region | "core" | "chest", Box>): Region | undefined {
    for (const r of REGIONS) if (inBox(p, bx[r], 0.6)) return r;
    return undefined;
  }

  /** Is an Heir standing guard at this region right now? */
  guarded(r: Region): boolean {
    if (r === "c") return false;
    const post = this.anchor(r);
    for (const h of this.enc.helpers.of("heir")) {
      const l = h.entity.location;
      if (Math.hypot(l.x - post.x, l.z - post.z) <= VESPERRA.heirs.guardRange) return true;
    }
    return false;
  }

  /** Apply a hit to the armour model; returns what reaches the boss. No world changes here. */
  apply(damage: number, region: Region | undefined): ArmorOutcome {
    const A = VESPERRA.armor;
    const i = this.enc.phase - 1;
    if (!region) return { damage: damage * A.body[i], region, broke: false, plateHit: false };
    if (this.hp[region] > 0) {
      const before = this.state(region);
      this.hp[region] = Math.max(0, this.hp[region] - damage);
      const broke = this.hp[region] <= 0 && before !== 2;
      return { damage: damage * A.through[i], region, broke, plateHit: true };
    }
    const mult = this.guarded(region) ? A.guarded : A.exposed[i];
    return { damage: damage * mult, region, broke: false, plateHit: false };
  }

  /** Push the visible states to the client (call from an unrestricted context). */
  sync(): void {
    for (const r of REGIONS) this.enc.setProp(`abm:armor_${r}`, this.state(r));
  }

  save(): Record<string, number> {
    return { al: this.hp.l, ar: this.hp.r, ac: this.hp.c };
  }

  load(extra: Record<string, number>): void {
    if (typeof extra.al === "number") this.hp.l = extra.al;
    if (typeof extra.ar === "number") this.hp.r = extra.ar;
    if (typeof extra.ac === "number") this.hp.c = extra.ac;
  }
}
