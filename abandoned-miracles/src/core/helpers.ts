/**
 * Helper entities (minions, anchors, bells, hourglasses, shadows).
 *
 * Every helper is spawned through the owning encounter's registry, which
 * enforces the cap, tags the entity so orphans can be found after a crash or
 * reload, expires it after its lifetime and reports its loss to the boss
 * controller exactly once. Helper definitions also carry a native despawn
 * timer, so they cannot outlive the add-on's scripts.
 */
import { Entity } from "@minecraft/server";
import { CONFIG } from "../config";
import type { Encounter } from "./encounter";
import { V3 } from "./math";
import { trace } from "./trace";

export const HELPER_TAG = "abm_helper";
export const OWNER_PROP = "abm:owner";

export interface Helper {
  entity: Entity;
  id: string;
  kind: string;
  born: number;
  /** Encounter tick at which the helper is removed (Infinity = until cleanup). */
  expires: number;
  /** Set when a player or the world killed it (as opposed to expiry / cleanup). */
  killed: boolean;
  data: Record<string, number>;
}

export class Helpers {
  private items: Helper[] = [];
  /** Total helpers ever spawned (telemetry). */
  spawned = 0;

  constructor(private readonly enc: Encounter) {}

  spawn(typeId: string, pos: V3, kind: string, opts: { yaw?: number; lifetime?: number; data?: Record<string, number> } = {}): Helper | undefined {
    if (this.items.length >= CONFIG.encounter.maxHelpers) return undefined;
    let e: Entity;
    try {
      e = this.enc.dim.spawnEntity(typeId, pos, { initialRotation: opts.yaw ?? 0 });
      e.addTag(HELPER_TAG);
      e.setDynamicProperty(OWNER_PROP, this.enc.bossId);
    } catch {
      return undefined;
    }
    const now = this.enc.timeline.now;
    const h: Helper = {
      entity: e,
      id: e.id,
      kind,
      born: now,
      expires: opts.lifetime ? now + opts.lifetime : Infinity,
      killed: false,
      data: opts.data ?? {},
    };
    this.items.push(h);
    this.spawned++;
    trace("helper_spawn", { boss: this.enc.key, kind });
    return h;
  }

  of(kind: string): Helper[] {
    return this.items.filter((h) => h.kind === kind && h.entity.isValid);
  }

  count(kind?: string): number {
    return this.items.filter((h) => (kind === undefined || h.kind === kind) && h.entity.isValid).length;
  }

  /** Called by the manager when any entity dies. */
  notifyDied(entityId: string): void {
    const h = this.items.find((i) => i.id === entityId);
    if (h) h.killed = true;
  }

  owns(entityId: string): boolean {
    return this.items.some((i) => i.id === entityId);
  }

  private discard(h: Helper): void {
    try {
      if (h.entity.isValid) h.entity.remove();
    } catch {
      /* already gone */
    }
  }

  remove(h: Helper): void {
    this.items = this.items.filter((i) => i !== h);
    this.discard(h);
  }

  removeKind(kind: string): void {
    for (const h of this.items.filter((i) => i.kind === kind)) this.remove(h);
  }

  removeAll(): void {
    for (const h of this.items) this.discard(h);
    this.items = [];
  }

  /** Expire, prune and report losses. */
  tick(): void {
    const now = this.enc.timeline.now;
    const gone: Helper[] = [];
    this.items = this.items.filter((h) => {
      if (!h.entity.isValid) {
        gone.push(h);
        return false;
      }
      if (now >= h.expires) {
        this.discard(h);
        gone.push(h);
        return false;
      }
      return true;
    });
    for (const h of gone) {
      trace("helper_gone", { boss: this.enc.key, kind: h.kind, killed: h.killed });
      this.enc.controller.onHelperGone(h);
    }
  }
}
