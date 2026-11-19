/**
 * EncounterManager - creates, finds and retires encounters.
 *
 * Server-authoritative and single-instance: one tick loop advances every
 * active encounter, so no attack can be scheduled twice however many players
 * are present. Encounters are keyed by boss entity id and bounded to their own
 * arena, so several can run at once in different places or dimensions.
 */
import {
  Dimension, Entity, EntityHurtBeforeEvent, ItemStack, system, world,
} from "@minecraft/server";
import { BOSS_KEYS, BossKey, CONFIG } from "../config";
import { Arena } from "./arena";
import { ControllerFactory } from "./boss";
import { Encounter, EncounterHost, EndReason } from "./encounter";
import { HELPER_TAG, OWNER_PROP } from "./helpers";
import { V3, dirToYaw } from "./math";
import { REMNANT_TAG, loadRecord, loadSettings } from "./persistence";
import { report, trace } from "./trace";

export const BOSS_TYPE: Record<BossKey, string> = {
  vesperra: "abm:vesperra",
  cantor: "abm:cantor_xiii",
  nomos: "abm:nomos",
  orison: "abm:orison",
};
export const SEAL_ITEM: Record<BossKey, string> = {
  vesperra: "abm:seal_vesperra",
  cantor: "abm:seal_cantor",
  nomos: "abm:seal_nomos",
  orison: "abm:seal_orison",
};
const TYPE_TO_KEY = new Map<string, BossKey>(BOSS_KEYS.map((k) => [BOSS_TYPE[k], k]));
const DIMENSIONS = ["overworld", "nether", "the_end"];

export type SummonFailure = "unknown" | "overlap" | "floor" | "ceiling" | "unloaded" | "spawn";

/** Whoever asks for a summon: a player, or a command block / NPC standing in for one. */
export interface SummonSource {
  dimension: Dimension;
  location: V3;
  name?: string;
}

export interface SummonResult {
  ok: boolean;
  reason?: SummonFailure;
  coverage?: number;
  encounter?: Encounter;
}

export class EncounterManager implements EncounterHost {
  private encounters = new Map<string, Encounter>();
  private factories = new Map<BossKey, ControllerFactory>();
  private ticks = 0;
  private started = false;

  register(key: BossKey, factory: ControllerFactory): void {
    this.factories.set(key, factory);
  }

  has(key: BossKey): boolean {
    return this.factories.has(key);
  }

  list(): Encounter[] {
    return [...this.encounters.values()];
  }

  get(bossId: string): Encounter | undefined {
    return this.encounters.get(bossId);
  }

  /** Closest active encounter to a location in the same dimension. */
  nearest(dim: Dimension, at: V3, maxDist = 96): Encounter | undefined {
    let best: Encounter | undefined;
    let bd = maxDist;
    for (const e of this.encounters.values()) {
      if (e.dim.id !== dim.id) continue;
      const d = Math.hypot(e.arena.cx - at.x, e.arena.cz - at.z);
      if (d < bd) {
        bd = d;
        best = e;
      }
    }
    return best;
  }

  // ------------------------------------------------------------------ wiring

  /**
   * Subscribe to world events and start the tick loop. Call once at module load.
   * `helperTypes` are the helper entity identifiers of the installed bosses.
   */
  init(helperTypes: readonly string[] = []): void {
    if (this.started) return;
    this.started = true;
    const bossTypes = [...TYPE_TO_KEY.keys()];

    world.afterEvents.worldLoad.subscribe(() => {
      loadSettings();
      this.adoptLoaded();
      this.sweepOrphans();
    });
    world.afterEvents.entitySpawn.subscribe((ev) => {
      if (TYPE_TO_KEY.has(ev.entity.typeId)) system.run(() => this.adopt(ev.entity, true));
    });
    world.afterEvents.entityLoad.subscribe((ev) => {
      if (TYPE_TO_KEY.has(ev.entity.typeId)) system.run(() => this.adopt(ev.entity, false));
    });
    world.beforeEvents.entityHurt.subscribe(
      (ev: EntityHurtBeforeEvent) => {
        const enc = this.encounters.get(ev.hurtEntity.id);
        if (enc) {
          try {
            enc.onHurtBefore(ev);
          } catch (e) {
            report("onHurtBefore", e);
          }
        } else if (ev.hurtEntity.hasTag(REMNANT_TAG)) {
          ev.cancel = true;
        }
      },
      { entityFilter: { families: ["abm_boss"] } },
    );
    world.afterEvents.entityDie.subscribe(
      (ev) => {
        const id = ev.deadEntity.id;
        const enc = this.encounters.get(id);
        if (enc) enc.onNativeDeath();
        else for (const e of this.encounters.values()) e.helpers.notifyDied(id);
      },
      { entityTypes: [...bossTypes, ...helperTypes] },
    );
    world.afterEvents.playerLeave.subscribe((ev) => {
      for (const e of this.encounters.values()) e.damage.forget(ev.playerId);
    });
    system.runInterval(() => this.tick(), 1);
  }

  /** Encounters whose whole tick threw, with the number of consecutive failures. */
  private readonly failing = new Map<Encounter, number>();

  tick(): void {
    this.ticks++;
    for (const e of [...this.encounters.values()]) {
      try {
        e.tick();
        this.failing.delete(e);
      } catch (err) {
        report(`encounter ${e.key}`, err);
        const n = (this.failing.get(e) ?? 0) + 1;
        this.failing.set(e, n);
        if (n >= 60) {
          this.failing.delete(e);
          try {
            this.abandon(e);
          } catch (err2) {
            report(`abandon ${e.key}`, err2);
          }
        }
      }
    }
    if (this.ticks % 200 === 0) this.sweepOrphans();
  }

  // ------------------------------------------------------------------ creating encounters

  /**
   * Summon a boss at a floor position chosen by a player. Never edits terrain:
   * if the place cannot host the arena the summon is refused with a reason.
   */
  trySummon(by: SummonSource, key: BossKey, floor: V3, force = false): SummonResult {
    if (!this.factories.has(key)) return { ok: false, reason: "unknown" };
    const stats = CONFIG.bosses[key];
    const dim = by.dimension;
    for (const e of this.encounters.values()) {
      if (e.dim.id !== dim.id) continue;
      const d = Math.hypot(e.arena.cx - floor.x, e.arena.cz - floor.z);
      if (d < e.arena.radius * 1.5 + stats.arenaRadius * 1.5 + 6) return { ok: false, reason: "overlap" };
    }
    const scan = Arena.scan(dim, floor, stats);
    if (!scan.ok && !(force && scan.loaded)) {
      return { ok: false, reason: (scan.reason as SummonFailure) ?? "floor", coverage: scan.coverage };
    }
    let boss: Entity;
    try {
      const yaw = dirToYaw(by.location.x - floor.x, by.location.z - floor.z);
      boss = dim.spawnEntity(BOSS_TYPE[key], { x: floor.x, y: floor.y + 0.05, z: floor.z }, { initialRotation: yaw });
    } catch (e) {
      report("spawn boss", e);
      return { ok: false, reason: "spawn" };
    }
    const enc = this.create(boss, key, floor);
    trace("summon", { boss: key, by: by.name ?? "", coverage: scan.coverage });
    return { ok: !!enc, encounter: enc, coverage: scan.coverage, reason: enc ? undefined : "spawn" };
  }

  private create(boss: Entity, key: BossKey, centre?: V3): Encounter | undefined {
    const factory = this.factories.get(key);
    if (!factory || this.encounters.has(boss.id)) return this.encounters.get(boss.id);
    try {
      const rec = loadRecord(boss);
      const enc = new Encounter(boss, key, this, factory, rec ?? (centre ? {
        v: 1, boss: key, cx: centre.x, cy: centre.y, cz: centre.z, phase: 1, scale: 1,
        seed: (Math.random() * 0xffffffff) >>> 0, engaged: false, extra: {},
      } : undefined));
      this.encounters.set(boss.id, enc);
      enc.start();
      return enc;
    } catch (e) {
      report(`create encounter ${key}`, e);
      this.encounters.delete(boss.id);
      return undefined;
    }
  }

  /** Take charge of a boss entity that appeared without going through trySummon. */
  adopt(boss: Entity, fresh: boolean): void {
    try {
      if (!boss.isValid || this.encounters.has(boss.id)) return;
      const key = TYPE_TO_KEY.get(boss.typeId);
      if (!key) return;
      if (boss.hasTag(REMNANT_TAG)) return;
      const enc = this.create(boss, key);
      if (enc && fresh) {
        const scan = Arena.scan(boss.dimension, enc.arena.centre, enc.stats);
        if (!scan.ok) {
          for (const p of boss.dimension.getPlayers({ location: boss.location, maxDistance: 48 })) {
            p.sendMessage({ rawtext: [{ translate: "abm.summon.warn.space" }] });
          }
        }
      }
    } catch (e) {
      report("adopt", e);
    }
  }

  private adoptLoaded(): void {
    for (const id of DIMENSIONS) {
      try {
        for (const e of world.getDimension(id).getEntities({ families: ["abm_boss"] })) this.adopt(e, false);
      } catch {
        /* dimension not available yet */
      }
    }
  }

  // ------------------------------------------------------------------ ending encounters

  release(enc: Encounter, reason: EndReason): void {
    enc.end(reason);
    this.encounters.delete(enc.bossId);
  }

  abandon(enc: Encounter): void {
    const centre = enc.arena.at({ x: enc.arena.cx, z: enc.arena.cz }, 1);
    const dim = enc.dim;
    this.release(enc, "abandoned");
    try {
      if (enc.boss.isValid) enc.boss.remove();
      if (CONFIG.encounter.refundSealOnReset) dim.spawnItem(new ItemStack(SEAL_ITEM[enc.key], 1), centre);
      for (const p of dim.getPlayers({ location: centre, maxDistance: 96 })) {
        p.sendMessage({ rawtext: [{ translate: "abm.msg.abandoned" }] });
      }
    } catch (e) {
      report("abandon", e);
    }
  }

  /** Cancel an encounter on request (command / UI): same as abandoning it. */
  cancel(enc: Encounter): void {
    this.abandon(enc);
  }

  /** Remove helper entities whose encounter no longer exists (crash, reload, unload). */
  sweepOrphans(): void {
    for (const id of DIMENSIONS) {
      let found: Entity[] = [];
      try {
        found = world.getDimension(id).getEntities({ tags: [HELPER_TAG] });
      } catch {
        continue;
      }
      for (const e of found) {
        try {
          const owner = e.getDynamicProperty(OWNER_PROP);
          const enc = typeof owner === "string" ? this.encounters.get(owner) : undefined;
          if (!enc || !enc.helpers.owns(e.id)) e.remove();
        } catch {
          /* already gone */
        }
      }
    }
  }
}

export const manager = new EncounterManager();
