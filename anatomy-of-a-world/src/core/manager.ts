/**
 * EncounterManager: owns the single active boss encounter, persists it across
 * world reloads, routes engine events to it and protects the arena dimensions.
 */
import {
  EntityHurtAfterEvent,
  EntityHurtBeforeEvent,
  EntitySpawnAfterEvent,
  ExplosionBeforeEvent,
  Player,
  PlayerBreakBlockBeforeEvent,
  PlayerPlaceBlockAfterEvent,
  ProjectileHitBlockAfterEvent,
  ProjectileHitEntityAfterEvent,
  system,
  world,
} from "@minecraft/server";
import { getReturnPoint, leaveArena } from "./arena.js";
import { resetFxBudget } from "./fx.js";
import { allBosses, BossDefinition, BossEncounter, getBoss, SavedEncounter } from "./registry.js";

const SAVE_KEY = "anatomy:active";
const STATS_KEY = "anatomy:stats";

class EncounterManager {
  active?: BossEncounter;
  private placedByPlayers = new Set<string>();
  private pendingReturn = new Map<string, number>();

  isArenaDimension(id: string): boolean {
    return allBosses().some((b) => b.dimensionId === id);
  }

  start(def: BossDefinition, initiator: Player): string | undefined {
    if (this.active && !this.active.isFinished()) return "An anatomy encounter is already in progress. Use the Atlas to join it.";
    const party = world
      .getAllPlayers()
      .filter((p) => p.dimension.id === initiator.dimension.id && Math.hypot(p.location.x - initiator.location.x, p.location.z - initiator.location.z) <= 32);
    if (!party.includes(initiator)) party.push(initiator);
    try {
      const enc = def.create(party);
      this.active = enc;
      this.placedByPlayers.clear();
      enc.begin();
      this.save();
      return undefined;
    } catch (e) {
      console.error(`[anatomy] failed to start ${def.id}: ${String(e)}${e instanceof Error ? "\n" + e.stack : ""}`);
      this.active = undefined;
      return "The encounter could not start (see content log).";
    }
  }

  stop(reason: "victory" | "defeat" | "abort"): void {
    const enc = this.active;
    if (!enc) return;
    try {
      enc.stop(reason);
    } catch (e) {
      console.error(`[anatomy] stop failed: ${String(e)}`);
    }
    if (enc.isFinished()) this.finish();
  }

  private finish(): void {
    this.active = undefined;
    world.setDynamicProperty(SAVE_KEY, undefined);
  }

  tick(): void {
    resetFxBudget();
    const enc = this.active;
    if (enc) {
      try {
        enc.tick();
      } catch (e) {
        console.error(`[anatomy] encounter tick error: ${String(e)}${e instanceof Error ? "\n" + e.stack : ""}`);
      }
      if (enc.isFinished()) this.finish();
      else if (system.currentTick % 100 === 0) this.save();
    }
    // players who respawned outside the arena while their fight is still running
    if (system.currentTick % 10 === 0 && this.pendingReturn.size) {
      for (const [id, due] of [...this.pendingReturn]) {
        if (system.currentTick < due) continue;
        this.pendingReturn.delete(id);
        const p = world.getAllPlayers().find((pl) => pl.id === id);
        if (!p) continue;
        if (this.active && !this.active.isFinished()) this.rejoin(p);
        else if (p.dimension.id.startsWith("anatomy:")) leaveArena(p);
      }
    }
  }

  rejoin(p: Player): void {
    const enc = this.active;
    if (!enc) return;
    const { pos, facing } = enc.entryPoint();
    try {
      p.teleport(pos, { dimension: world.getDimension(enc.def.dimensionId), facingLocation: facing });
      p.addEffect("resistance", 60, { amplifier: 4, showParticles: false });
      p.addEffect("slow_falling", 40, { amplifier: 0, showParticles: false });
      enc.onPlayerJoin?.(p);
    } catch (e) {
      console.warn(`[anatomy] rejoin failed for ${p.name}: ${String(e)}`);
    }
  }

  save(): void {
    if (!this.active) return;
    try {
      world.setDynamicProperty(SAVE_KEY, JSON.stringify(this.active.serialize()));
    } catch (e) {
      console.warn(`[anatomy] save failed: ${String(e)}`);
    }
  }

  /** On world load: resume an interrupted encounter (rebuilt deterministically at its phase). */
  restore(): void {
    const raw = world.getDynamicProperty(SAVE_KEY);
    if (typeof raw !== "string") return;
    let saved: SavedEncounter | undefined;
    try {
      saved = JSON.parse(raw) as SavedEncounter;
    } catch {
      saved = undefined;
    }
    const def = saved ? getBoss(saved.boss) : undefined;
    if (!saved || !def) {
      world.setDynamicProperty(SAVE_KEY, undefined);
      return;
    }
    try {
      const enc = def.create([]);
      this.active = enc;
      enc.begin(saved);
      console.warn(`[anatomy] resumed ${def.id} at phase ${saved.phase}`);
    } catch (e) {
      console.error(`[anatomy] resume failed: ${String(e)}`);
      this.finish();
    }
  }

  // ------------------------------------------------------------------ stats (Atlas records)
  record(bossId: string, field: "attempts" | "victories" | "bestSeconds", value?: number): void {
    const stats = this.stats();
    const s = (stats[bossId] ??= { attempts: 0, victories: 0, bestSeconds: 0 });
    if (field === "bestSeconds") {
      if (value !== undefined && (s.bestSeconds === 0 || value < s.bestSeconds)) s.bestSeconds = Math.round(value);
    } else s[field]++;
    world.setDynamicProperty(STATS_KEY, JSON.stringify(stats));
  }

  stats(): Record<string, { attempts: number; victories: number; bestSeconds: number }> {
    const raw = world.getDynamicProperty(STATS_KEY);
    try {
      return typeof raw === "string" ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  // ------------------------------------------------------------------ event routing
  onHurtBefore(ev: EntityHurtBeforeEvent): void {
    this.active?.onHurtBefore?.(ev);
  }
  onHurt(ev: EntityHurtAfterEvent): void {
    this.active?.onHurt?.(ev);
  }
  onProjectileHitBlock(ev: ProjectileHitBlockAfterEvent): void {
    this.active?.onProjectileHitBlock?.(ev);
  }
  onProjectileHitEntity(ev: ProjectileHitEntityAfterEvent): void {
    this.active?.onProjectileHitEntity?.(ev);
  }

  onPlayerRespawn(p: Player): void {
    const rp = getReturnPoint(p);
    if (!rp) return;
    if (this.active && !this.active.isFinished()) {
      if (p.dimension.id !== this.active.def.dimensionId) {
        p.sendMessage("§7The fight goes on. You are pulled back in a moment… §8(open the Anatomical Atlas to leave instead)");
        this.pendingReturn.set(p.id, system.currentTick + 50);
      }
    } else if (!p.dimension.id.startsWith("anatomy:")) {
      p.setDynamicProperty("anatomy:return", undefined);
    }
  }

  cancelReturn(p: Player): void {
    this.pendingReturn.delete(p.id);
  }

  // ------------------------------------------------------------------ arena protection
  onBreakBefore(ev: PlayerBreakBlockBeforeEvent): void {
    const d = ev.block.dimension.id;
    if (!this.isArenaDimension(d)) return;
    const k = `${ev.block.x},${ev.block.y},${ev.block.z}`;
    if (this.placedByPlayers.has(k)) {
      this.placedByPlayers.delete(k);
      return;
    }
    ev.cancel = true;
  }

  onPlace(ev: PlayerPlaceBlockAfterEvent): void {
    if (!this.isArenaDimension(ev.block.dimension.id)) return;
    this.placedByPlayers.add(`${ev.block.x},${ev.block.y},${ev.block.z}`);
  }

  onExplosionBefore(ev: ExplosionBeforeEvent): void {
    if (this.isArenaDimension(ev.dimension.id)) ev.setImpactedBlocks([]);
  }

  onEntitySpawn(ev: EntitySpawnAfterEvent): void {
    const e = ev.entity;
    try {
      if (!e.isValid || !this.isArenaDimension(e.dimension.id)) return;
      if (e.typeId.startsWith("anatomy:")) return;
      if (e.matches({ families: ["mob"] }) && !e.matches({ families: ["player"] })) {
        const tameable = e.getComponent("minecraft:is_tamed");
        if (!tameable) e.remove();
      }
    } catch {
      /* entity vanished */
    }
  }
}

export const manager = new EncounterManager();
