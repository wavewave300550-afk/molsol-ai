/**
 * THE MIGRATING MOUNTAIN — encounter state machine.
 *
 *   loading -> intro -> phase1 (The Sleeping Continent: destroy 3 Resonance Nodes)
 *           -> unfolding (07 The Great Unfolding) -> phase2 (The Unfolded World: the Lithic Heart)
 *           -> victory -> aftermath -> ending -> finished        (or -> ending on defeat/abort)
 */
import {
  Difficulty,
  Dimension,
  EasingType,
  Entity,
  EnchantmentType,
  EntityDamageCause,
  EntityHurtAfterEvent,
  EntityHurtBeforeEvent,
  GameMode,
  HudVisibility,
  InputPermissionCategory,
  ItemStack,
  LocationWaypoint,
  Player,
  ProjectileHitBlockAfterEvent,
  ProjectileHitEntityAfterEvent,
  system,
  WaypointTexture,
  world,
} from "@minecraft/server";
import { combatants, enterArena, hurt, knock, leaveArena, playersIn } from "../../core/arena.js";
import { BlockWriter } from "../../core/blocks.js";
import { AreaKeeper, awaitPromise, chunkBudget, ChunkRect, rectOf, sweepDeferred } from "../../core/chunks.js";
import { actionbar, particle, quake, shake, sound, titleFor } from "../../core/fx.js";
import { tr } from "../../core/lang.js";
import { manager } from "../../core/manager.js";
import { missingEntityTypes, PartReport, Parts } from "../../core/parts.js";
import { BossDefinition, BossEncounter, SavedEncounter } from "../../core/registry.js";
import { Co, TaskRunner } from "../../core/tasks.js";
import { angleDiffDeg, V3 } from "../../core/vec.js";
import { ColFlag, MM, MountainModel, NodeSite } from "../../gen/mountain.js";
import { Rng } from "../../gen/noise.js";
import * as P from "../../gen/palette.js";
import { ABILITY_IDS, AbilityId, slabImpact } from "./abilities.js";
import { AnchorInfo, ArenaKind, LivingNode, MMContext, Zone } from "./context.js";
import { Director } from "./director.js";
import { ANIM, DIMENSION, ENT, FOG, ITEM, MUSIC, PROP, PX, SND, TAG } from "./ids.js";
import { ANCHORS, anchorSite, HOVER_Y, marchWave, mountainFalls, Phase3Hooks, refoldToMigration, SLAM_Y, slamRings } from "./phase3.js";
import { arenaChunks, clearArena, cutColumns, Island, islandAt, islandLayout, mountain, placeBody, placeDisk, pristineBlock, restoreDisk, sectorColumns, shatterDisk } from "./runtime.js";
import { DorsalTerrain } from "./terrain.js";
import { greatUnfolding, PETALS, petalSite, rebloom, ringSpot, victorySequence } from "./unfolding.js";

type State =
  | "loading"
  | "intro"
  | "phase1"
  | "unfolding"
  | "phase2"
  | "refolding"
  | "phase3a"
  | "falling"
  | "phase3b"
  | "victory"
  | "aftermath"
  | "ending"
  | "finished";

/** States in which the boss fights back. */
const FIGHTING: State[] = ["phase1", "phase2", "phase3a", "phase3b"];

const D = MM.disk;
/** Health attribute of the heart (kept at 1000; incoming damage is halved for a 2000-point fight). */
const HEART_MAX = 1000;
const HEART_DAMAGE = 0.5;
const NODE_SHARE = 0.1333;
/** Phase 2 mid-fight re-bloom, and the health floors that end Phase 2 and Phase 3A. */
const REBLOOM_AT = 0.47;
const FLOOR_P2 = 0.35;
const FLOOR_P3A = 0.2;
/** Heart window after a severed Anchorage Root (ticks). */
const ANCHOR_WINDOW = 160;
/** Phase 3A soft enrage: the mountain marches faster after this long (ticks). */
const P3A_ENRAGE = 4800;
/** Phase 3B: hover between slams, then down on the centre island (ticks). */
const SLAM_EVERY = 440;
const SLAM_DOWN = 120;
const AREA_PREFIX = "anatomy_mm_area";
const SWEEP_ID = "anatomy_mm_sweep";
const ANCHOR_SITES = Array.from({ length: ANCHORS }, (_, k) => anchorSite(k).pos);
/** Thai names of the Resonance Nodes. */
const NODE_TH: Record<string, string> = { dorsal: "ผลึกยอดเขา", cavern: "ผลึกในถ้ำ", root: "ผลึกใต้ราก" };
const NODE_COLOR = { red: 0.78, green: 0.38, blue: 1 };
const ANCHOR_COLOR = { red: 1, green: 0.55, blue: 0.2 };
/** Shown on the boss bar. */
const HEART_NAME = "The Migrating Mountain";
/** Player dynamic property: has this player had the mountain's gear (first victory guarantees it)? */
const GEAR_KEY = "anatomy:gear_migrating_mountain";

export class MigratingMountainEncounter implements BossEncounter, MMContext {
  readonly dim: Dimension;
  readonly m: MountainModel;
  readonly writer: BlockWriter;
  readonly terrain: DorsalTerrain;
  readonly tasks = new TaskRunner();
  readonly director: Director;
  state: State = "loading";
  phase: 1 | 2 | 3 = 1;
  /** The mountain walks this way in Phase 3A (and the wind comes from it). */
  readonly walkDir = { x: 1, z: 0 };
  private anchorsCut = new Set<number>();
  private anchorsDying = new Set<number>();
  private islandsBuilt = false;
  private p3aStart = 0;
  private nextStep = 0;
  private steps = 0;
  /** Phase 3B heart cycle. */
  private slam: "hover" | "warn" | "falling" | "down" | "rising" = "hover";
  private slamAt = 0;
  private slamUntil = 0;
  private fallAfter = -1;
  now = 0;
  layout = 0;
  /** Every boss part entity (legs, nodes, heart, petals): spawned when loaded, re-bound after reloads. */
  readonly parts: Parts;
  /** Keeps the arena's chunks ticking as far as the pack's budget allows. */
  readonly keeper: AreaKeeper;
  private heartHpCache = HEART_MAX;
  private waypoints = new Map<string, LocationWaypoint>();
  private waypointsBroken = false;
  private briefed = new Set<string>();
  private nodeDead = new Set<string>();
  private nodeDying = new Set<string>();
  private exposedUntil = 0;
  private rebloomed = false;
  private emptySince = -1;
  private known = new Set<string>();
  private slabs: { e: Entity; target: V3; land: number; power: number }[] = [];
  private pocketCache: V3[] | undefined;
  private startedAt = 0;
  private stopReason: "victory" | "defeat" | "abort" | undefined;
  private lootSpot: V3 = { x: MM.heart.x, y: D.y + 1, z: MM.heart.z };
  private heartHpDebt = 0;
  private focusing = false;
  private readonly random: Rng;
  readonly rng: () => number;

  constructor(
    readonly def: BossDefinition,
    private party: Player[],
  ) {
    this.dim = world.getDimension(DIMENSION);
    this.m = mountain();
    this.writer = new BlockWriter(this.dim, 1500);
    this.writer.guard = (x, y, z, b) => this.writeAllowed(x, y, z, b);
    this.terrain = new DorsalTerrain(this.m, this.dim, this.writer, pristineBlock);
    this.random = new Rng((Date.now() & 0xffff) ^ 0x5eed);
    this.rng = () => this.random.next();
    this.director = new Director(this, () => this.pockets());
    this.parts = new Parts(this.dim, TAG);
    this.keeper = new AreaKeeper(AREA_PREFIX, this.dim);
  }

  get heart(): Entity | undefined {
    return this.parts.get("heart");
  }

  get legs(): Entity[] {
    return this.parts.list("leg:");
  }

  get petals(): Entity[] {
    return this.parts.list("petal:");
  }

  // ------------------------------------------------------------------ BossEncounter
  status(): string {
    const hp = this.heartHp();
    const n = this.parts.summary("node:");
    const l = this.parts.summary("leg:");
    const h = this.parts.summary("heart");
    const b = chunkBudget();
    const sites = this.remainingSites()
      .map((s) => `${s.id}@${Math.floor(s.pos.x)},${Math.floor(s.pos.y)},${Math.floor(s.pos.z)}${this.parts.get(`node:${s.id}`) ? "" : this.parts.summary(`node:${s.id}`).spawned ? "(unloaded)" : "(waiting for chunk)"}`)
      .join(" ");
    return (
      `${this.def.id}: state=${this.state} phase=${this.phase} nodes=${3 - this.nodeDead.size}/3 heart=${hp.toFixed(0)}/${HEART_MAX} layout=${this.layout}\n` +
      `parts: nodes ${n.loaded}/${n.spawned}/${n.total} legs ${l.loaded}/${l.spawned}/${l.total} heart ${h.loaded}/${h.spawned}/${h.total} (loaded/spawned/wanted) respawns=${this.parts.respawns}\n` +
      `remaining: ${sites || "-"}${this.phase === 3 ? ` · anchors ${ANCHORS - this.anchorsCut.size}/${ANCHORS} · islands ${this.islandsBuilt ? "yes" : "no"} · heart ${this.slam}` : ""}\n` +
      `chunks: kept ${this.keeper.kept}/${this.keeper.wanted} ticking, budget ${b.used}/${b.max ?? "?"}; writer queued=${this.writer.pending} deferred=${this.writer.deferredOps} failed=${this.writer.failures}; tasks=${this.tasks.count()}`
    );
  }

  begin(saved?: SavedEncounter): void {
    this.tasks.start("mm:setup", this.setup(saved), (e) => {
      console.error(`[anatomy] setup failed: ${String(e)}${e instanceof Error ? "\n" + e.stack : ""}`);
      this.stop("abort");
    });
  }

  isFinished(): boolean {
    return this.state === "finished";
  }

  entryPoint(): { pos: V3; facing: V3 } {
    if (this.arena() === "islands") return this.islandSpot();
    if (this.phase >= 2) return this.safeRingSpot();
    const ar = MM.arrival;
    return { pos: { x: ar.x + 0.5, y: ar.y + 1.05, z: ar.z + 0.5 }, facing: { x: 0, y: 150, z: 0 } };
  }

  serialize(): SavedEncounter {
    return {
      boss: this.def.id,
      phase: this.phase,
      data: {
        nodeDead: [...this.nodeDead],
        heartHp: this.heartHp(),
        layout: this.layout,
        rebloomed: this.rebloomed,
        stage: this.phase === 3 ? (this.arena() === "islands" ? "3b" : "3a") : undefined,
        anchorsCut: [...this.anchorsCut, ...this.anchorsDying],
      },
    };
  }

  /**
   * Skip ahead (test command / Atlas): 2 = destroy the nodes, 3 = end Phase 2 (the refold),
   * 4 = sever every Anchorage Root (the fall). 0 = whatever comes next.
   */
  forcePhase(phase: number): boolean {
    const next = phase === 0 ? ({ phase1: 2, phase2: 3, phase3a: 4 } as Record<string, number>)[this.state] : phase;
    if (next === 2 && this.state === "phase1") {
      for (const site of this.remainingSites()) this.destroyNode(site.id, this.parts.get(`node:${site.id}`), true);
      return true;
    }
    if (next === 3 && this.state === "phase2") {
      const h = this.heart?.getComponent("minecraft:health");
      if (h && h.currentValue > HEART_MAX * FLOOR_P2) h.setCurrentValue(HEART_MAX * FLOOR_P2);
      this.heartHpCache = Math.min(this.heartHpCache, HEART_MAX * FLOOR_P2);
      this.startRefold();
      return true;
    }
    if (next === 4 && this.state === "phase3a") {
      for (let k = 0; k < ANCHORS; k++) if (!this.anchorsCut.has(k) && !this.anchorsDying.has(k)) this.severAnchor(k, this.parts.get(`anchor:${k}`), true);
      return true;
    }
    return false;
  }

  forceAbility(id: string): boolean {
    if (!["phase1", "phase2", "phase3a", "phase3b"].includes(this.state)) return false;
    if (!ABILITY_IDS.includes(id as AbilityId)) return false;
    if (id === "great_unfolding") {
      if (this.state === "phase1") return this.forcePhase(2);
      if (this.state === "phase2") return this.startRebloom() || this.forcePhase(3);
      if (this.state === "phase3a") return this.forcePhase(4);
      return false;
    }
    return this.director.force(id as AbilityId, undefined);
  }

  killBoss(): boolean {
    if (this.state === "phase1") this.forcePhase(2);
    if (this.state === "phase2" || this.state === "phase3a" || this.state === "phase3b") {
      this.startVictory();
      return true;
    }
    return false;
  }

  // ------------------------------------------------------------------ Phase 3 queries (MMContext)
  arena(): ArenaKind {
    if (this.islandsBuilt) return "islands";
    return this.phase >= 2 ? "disk" : "body";
  }

  anchors(): AnchorInfo[] {
    const out: AnchorInfo[] = [];
    if (this.phase !== 3) return out;
    for (let k = 0; k < ANCHORS; k++) {
      if (this.anchorsCut.has(k) || this.anchorsDying.has(k)) continue;
      out.push({ k, pos: anchorSite(k).pos, entity: this.parts.get(`anchor:${k}`) });
    }
    return out;
  }

  islands(): Island[] {
    return this.islandsBuilt ? islandLayout() : [];
  }

  heartSlamming(): boolean {
    return this.state === "phase3b" && (this.slam === "falling" || this.slam === "down");
  }

  /** A spot on a ring island whose cells are free (Phase 3B rescue / rejoin). */
  private islandSpot(): { pos: V3; facing: V3 } {
    const ring = islandLayout().filter((s) => s.i > 0);
    const start = Math.floor(this.rng() * ring.length);
    const facing = { x: MM.heart.x, y: HOVER_Y + 3, z: MM.heart.z };
    for (let k = 0; k < ring.length; k++) {
      const s = ring[(start + k) % ring.length];
      if (this.writer.hasDeferredIn(Math.floor(s.cx), Math.floor(s.cz), Math.floor(s.cx), Math.floor(s.cz))) continue;
      try {
        const feet = this.dim.getBlock({ x: s.cx, y: s.top + 1, z: s.cz });
        const below = this.dim.getBlock({ x: s.cx, y: s.top, z: s.cz });
        if (feet?.isAir && below && !below.isAir) return { pos: { x: s.cx, y: s.top + 1.05, z: s.cz }, facing };
      } catch {
        /* unloaded */
      }
    }
    const c = islandLayout()[0];
    return { pos: { x: c.cx + 4, y: c.top + 1.05, z: c.cz }, facing };
  }

  stop(reason: "victory" | "defeat" | "abort"): void {
    if (this.state === "ending" || this.state === "finished") return;
    this.stopReason = reason;
    this.tasks.cancelAll();
    this.state = "ending";
    this.tasks.start("mm:ending", this.ending(reason), () => this.finishNow());
  }

  /** A ring spot whose feet and head cells are free (abilities may have raised flesh or rubble). */
  private safeRingSpot(): { pos: V3; facing: V3 } {
    const start = Math.floor(this.rng() * 16);
    let first: { pos: V3; facing: V3 } | undefined;
    for (let k = 0; k < 16; k++) {
      const s = ringSpot((start + k) % 16, 16);
      first ??= s;
      const bx = Math.floor(s.pos.x);
      const bz = Math.floor(s.pos.z);
      // edits still waiting for this chunk (e.g. the cut of the shell) would land on the player
      if (this.writer.hasDeferredIn(bx, bz, bx, bz)) continue;
      try {
        const feet = this.dim.getBlock(s.pos);
        const head = this.dim.getBlock({ x: s.pos.x, y: s.pos.y + 1, z: s.pos.z });
        if (feet?.isAir && head?.isAir) return s;
        if (!feet || !head) first = s; // not loaded yet: a usable fallback, nothing known in the way
      } catch {
        /* unloaded */
      }
    }
    const f = first!;
    return { pos: { x: f.pos.x, y: f.pos.y + 3, z: f.pos.z }, facing: f.facing };
  }

  // ------------------------------------------------------------------ MMContext
  livingNodes(): LivingNode[] {
    const out: LivingNode[] = [];
    for (const site of this.remainingSites()) {
      const e = this.parts.get(`node:${site.id}`);
      if (e) out.push({ site, entity: e });
    }
    return out;
  }

  /** Nodes not destroyed yet (whether or not their entity is loaded right now). */
  remainingSites(): NodeSite[] {
    return this.m.nodes.filter((s) => !this.nodeDead.has(s.id) && !this.nodeDying.has(s.id));
  }

  combatants(): Player[] {
    return combatants(DIMENSION).filter((p) => {
      try {
        const h = p.getComponent("minecraft:health");
        return !h || h.currentValue > 0;
      } catch {
        return false;
      }
    });
  }

  audience(): Player[] {
    return playersIn(DIMENSION);
  }

  zoneOf(p: Player): Zone {
    const { x, y, z } = p.location;
    if (this.arena() === "islands") {
      const s = islandAt(x, z, this.islands());
      return s && y >= s.top - 2 ? "disk" : "other";
    }
    if (this.phase >= 2) {
      const r = Math.hypot(x - MM.heart.x, z - MM.heart.z);
      if (r <= D.outerR + 0.5) return y >= D.y - 0.5 ? "disk" : "mantle";
      return "shelf";
    }
    const ar = MM.arrival;
    if (Math.hypot(x - ar.x, z - ar.z) < ar.r + 3 && y > ar.y - 14) return "arrival";
    const cx = Math.floor(x);
    const cz = Math.floor(z);
    if (!this.m.inCols(cx, cz)) return "other";
    const c = this.m.col(cx, cz);
    const fl = this.m.flags[c];
    const cv = MM.cavern;
    const q = Math.hypot((x - cv.x) / cv.rx, (z - cv.z) / cv.rz);
    if (q < 1.05 && y >= cv.floorY && y <= cv.y + cv.ry + 1) return "cavern";
    if (fl & ColFlag.CAVE && y < this.terrain.topAt(cx, cz) - 2 && y >= this.m.under[c]) return "cavern";
    if (!(fl & ColFlag.BODY)) return y < MM.rimUnderY ? "under" : "other";
    if (y < this.m.under[c]) return "under";
    return "dorsal";
  }

  hurt(p: Player, amount: number, cause: EntityDamageCause): void {
    hurt(p, amount * this.difficultyMult(), cause, this.heart);
  }

  enraged(): boolean {
    const hp = this.heartHp();
    if (this.phase === 2) return this.rebloomed && hp < HEART_MAX * 0.42;
    if (this.phase === 3) return (this.state === "phase3a" && this.now - this.p3aStart > P3A_ENRAGE) || hp < HEART_MAX * 0.1;
    return false;
  }

  exposeHeart(ticks: number): void {
    if (this.state !== "phase2" && this.state !== "phase3a") return;
    this.exposedUntil = this.now + ticks;
    this.director.lastExposure = this.now;
    this.heartProp(PROP.open, true);
    sound(this.dim, SND.heartOpen, this.heartCentre(), 1, 1);
    titleFor(this.audience(), (p) => ["", tr(p, "§a◆ The Lithic Heart is EXPOSED — strike it now!", "§a◆ หัวใจศิลาเปิดออกแล้ว — โจมตีเลย!")], 40, 4, 10);
  }

  isWalkway(x: number, z: number): boolean {
    const b = this.m.phase2Block(x, D.y, z, this.layout);
    return b >= 2;
  }

  originalBlock(x: number, y: number, z: number): number {
    return pristineBlock(x, y, z);
  }

  trackSlab(e: Entity, target: V3, land: number, power: number): void {
    e.addTag(TAG);
    this.slabs.push({ e, target, land, power });
  }

  partProp(e: Entity, name: string, value: boolean | number): void {
    this.parts.propOf(e, name, value);
  }

  setLegPose(pose: number): void {
    this.parts.propAll("leg:", PROP.pose, pose);
  }

  petal(k: number, state: number): Entity | undefined {
    const key = `petal:${k}`;
    if (!this.parts.has(key)) {
      const s = petalSite(k);
      return this.parts.want(key, { type: ENT.petal, pos: s.pos, yaw: s.yaw, props: { [PROP.petalIndex]: k, [PROP.petalState]: state } });
    }
    this.parts.prop(key, PROP.petalState, state);
    return this.parts.get(key);
  }

  setPetals(state: number): void {
    this.parts.propAll("petal:", PROP.petalState, state);
  }

  heartProp(name: string, value: boolean | number): void {
    this.parts.prop("heart", name, value);
  }

  removeHeart(): void {
    this.parts.drop("heart");
  }

  *settleArea(x0: number, z0: number, x1: number, z1: number, timeout: number): Co {
    const t0 = this.now;
    this.focusing = true; // the background sweep steps aside so this one gets the chunk budget
    try {
      while (this.now - t0 < timeout && (this.writer.pending > 0 || this.writer.hasDeferredIn(x0, z0, x1, z1))) {
        if (this.writer.pending > 0) {
          yield 1;
          continue;
        }
        yield* sweepDeferred(this.writer, `${SWEEP_ID}_focus`, Math.max(20, timeout - (this.now - t0)), { focus: rectOf(x0, z0, x1, z1) });
        yield 1;
      }
    } finally {
      this.focusing = false;
    }
  }

  /** world.afterEvents.entityLoad (routed by the manager). */
  onEntityLoad(e: Entity): void {
    try {
      if (e.dimension.id !== DIMENSION) return;
    } catch {
      return;
    }
    this.parts.onLoad(e);
  }

  // ------------------------------------------------------------------ setup
  /**
   * Regions kept ticking, most important first: the nodes and the heart, the
   * arrival shelf, the Organ Cavern, the Phase 2 disk, then the whole body.
   * Whatever does not fit in the pack's budget loads around the players.
   */
  private areaPlan(): ChunkRect[] {
    const pts: V3[] = [MM.heart, ...this.m.nodes.map((n) => n.pos)];
    const xs = pts.map((q) => q.x);
    const zs = pts.map((q) => q.z);
    const ar = MM.arrival;
    const cv = MM.cavern;
    return [
      rectOf(Math.min(...xs), Math.min(...zs), Math.max(...xs), Math.max(...zs)),
      rectOf(ar.x - ar.r - 3, ar.z - ar.r - 3, ar.x + ar.r + 3, ar.z + ar.r + 3),
      rectOf(cv.x - cv.rx, cv.z - cv.rz, cv.x + cv.rx, cv.z + cv.rz),
      rectOf(MM.heart.x - D.outerR, MM.heart.z - D.outerR, MM.heart.x + D.outerR, MM.heart.z + D.outerR),
      arenaChunks(),
    ];
  }

  private *setup(saved?: SavedEncounter): Co {
    this.state = "loading";
    if (!saved) titleFor(this.party, (p) => [tr(p, "§7The ground beneath you begins to migrate…", "§7พื้นดินใต้เท้าเริ่มเคลื่อนย้าย…"), ""], 40, 10, 10);
    AreaKeeper.releaseAll(); // stale areas of an interrupted session
    const loading = yield* awaitPromise(this.keeper.keep(this.areaPlan()), 600);
    if (!loading.done || this.keeper.kept < this.keeper.wanted) {
      const b = chunkBudget();
      console.warn(
        `[anatomy] arena: ${this.keeper.kept}/${this.keeper.wanted} chunks kept ticking (budget ${b.used}/${b.max ?? "?"})${loading.done ? "" : ", still loading"} — the rest loads around players and boss parts appear as it does`,
      );
    }
    this.killLeftovers();
    // players already inside (a resumed fight) are held safely while the body is rebuilt
    const holding = saved ? this.audience() : [];
    for (const p of holding)
      try {
        p.addEffect("slow_falling", 2400, { amplifier: 0, showParticles: false });
        p.addEffect("resistance", 2400, { amplifier: 4, showParticles: false });
      } catch {
        /* ignore */
      }
    yield* clearArena(this.writer);
    this.tasks.start("mm:housekeeping", this.housekeeping());
    // chunks that were not loaded are cleaned before any structure is placed over them
    if (this.writer.deferredOps > 0) yield* sweepDeferred(this.writer, SWEEP_ID, 300);
    // the arrival shelf first, so the party has somewhere to stand
    const ar = MM.arrival;
    for (let x = ar.x - ar.r - 3; x <= ar.x + ar.r + 3; x++)
      for (let z = ar.z - ar.r - 3; z <= ar.z + ar.r + 3; z++)
        for (let y = ar.y - 16; y <= ar.y + 2; y++) {
          const v = pristineBlock(x, y, z);
          if (v >= 2) this.writer.set(x, y, z, v);
        }
    this.writer.flushAll();
    for (const p of holding) {
      const e = this.entryPoint();
      try {
        p.teleport({ x: ar.x + 0.5, y: ar.y + 1.05, z: ar.z + 0.5 }, { facingLocation: e.facing });
      } catch {
        /* ignore */
      }
    }
    this.startedAt = system.currentTick;
    if (!saved) {
      manager.record(this.def.id, "attempts");
      const facing = { x: 0, y: 150, z: 0 };
      this.party.forEach((p, i) => {
        const a = (i / Math.max(1, this.party.length)) * Math.PI * 2;
        enterArena(p, this.dim, { x: ar.x + 0.5 + Math.cos(a) * 3, y: ar.y + 1.05, z: ar.z + 0.5 + Math.sin(a) * 3 }, facing);
        try {
          // the shelf may still be waiting for its chunk to load
          p.addEffect("slow_falling", 200, { amplifier: 0, showParticles: false });
          p.addEffect("resistance", 200, { amplifier: 4, showParticles: false });
        } catch {
          /* ignore */
        }
        this.welcome(p);
      });
      yield 20;
      yield* this.settleOnShelf(this.party);
      this.cinematic(true);
    }
    // the mountain surfaces from the cloud sea
    this.wantLegs();
    sound(this.dim, SND.rumble, { x: 0, y: 130, z: -40 }, 1, 0.7);
    yield* placeBody(this.dim, this.writer, saved ? 0 : 7);
    if (!saved) {
      this.camTo({ x: -98, y: 182, z: -70 }, { x: 0, y: 145, z: 0 }, 7);
      for (let t = 0; t < 140; t += 20) {
        quake(this.audience(), { x: 0, y: 130, z: 0 }, 0.6, 0.6, 200);
        if (t % 40 === 0) sound(this.dim, SND.groan, { x: 0, y: 150, z: 0 }, 1, 0.7 + t / 400);
        yield 20;
      }
    }
    this.wantHeart(saved);
    this.wantNodes(saved);
    if (saved && saved.phase >= 2) {
      this.layout = Number(saved.data.layout ?? 0);
      this.rebloomed = Boolean(saved.data.rebloomed);
      const stage = saved.phase === 3 ? String(saved.data.stage ?? "3a") : "2";
      for (const k of (saved.data.anchorsCut as number[] | undefined) ?? []) this.anchorsCut.add(Number(k));
      const all = sectorColumns(1, 0)[0];
      for (let i = 0; i < all.length; i += 400) {
        cutColumns(this.writer, all.slice(i, i + 400));
        yield 1;
      }
      while (this.writer.pending > 0) yield 1;
      this.terrain.enabled = false;
      const inside = this.audience();
      if (stage === "3b") {
        // the fall already happened: islands, collapsed roots, the heart hovering
        this.phase = 3;
        yield* shatterDisk(this.writer);
        this.islandsBuilt = true;
        this.setLegPose(2);
        this.heartProp(PROP.phase, 3);
        this.moveHeart(HOVER_Y);
        for (const s of islandLayout().filter((q) => q.i > 0).slice(0, Math.max(1, inside.length)))
          yield* this.settleArea(Math.floor(s.cx - s.r), Math.floor(s.cz - s.r), Math.ceil(s.cx + s.r), Math.ceil(s.cz + s.r), 200);
        inside.forEach((p) => {
          const spot = this.islandSpot();
          try {
            p.teleport(spot.pos, { facingLocation: spot.facing });
            p.removeEffect("slow_falling");
            p.removeEffect("resistance");
          } catch {
            /* ignore */
          }
        });
        this.enterPhase3b();
      } else {
        placeDisk(this.dim, this.writer, this.layout, 0);
        for (let k = 0; k < PETALS; k++) this.petal(k, stage === "3a" ? 4 : 1);
        this.setLegPose(stage === "3a" ? 3 : 1);
        if (stage === "3a") this.spawnAnchors();
        for (let i = 0; i < inside.length; i++) {
          const at = ringSpot(i, inside.length).pos;
          yield* this.settleArea(Math.floor(at.x) - 2, Math.floor(at.z) - 2, Math.floor(at.x) + 2, Math.floor(at.z) + 2, 200);
        }
        inside.forEach((p, i) => {
          const r = ringSpot(i, inside.length);
          try {
            p.teleport(r.pos, { facingLocation: r.facing });
            p.removeEffect("slow_falling");
            p.removeEffect("resistance");
          } catch {
            /* ignore */
          }
        });
        if (stage === "3a") this.enterPhase3a();
        else this.enterPhase2(false);
      }
    } else {
      if (!saved) {
        this.camTo({ x: -30, y: 150, z: -96 }, { x: -4, y: 140, z: -50 }, 3);
        titleFor(this.audience(), (p) => ["§f001 · §lTHE MIGRATING MOUNTAIN", tr(p, "§7The Mountain That Never Belonged to the Earth", "§7ภูเขาที่ไม่เคยเป็นของผืนโลก")], 80, 10, 30);
        yield 70;
        this.cinematic(false);
        titleFor(
          this.audience(),
          (p) => [tr(p, "§aPHASE 1", "§aเฟส 1"), tr(p, "§2THE SLEEPING CONTINENT §7— find and destroy the 3 Resonance Nodes", "§2ทวีปที่หลับใหล §7— ตามหาและทำลายผลึกสีม่วงทั้ง 3 จุด")],
          70,
          10,
          20,
        );
      }
      for (const p of holding)
        try {
          p.removeEffect("slow_falling");
          p.removeEffect("resistance");
        } catch {
          /* ignore */
        }
      this.state = "phase1";
      this.phase = 1;
      this.director.reset(this.now, saved ? 100 : 240);
      for (const p of this.audience()) this.brief(p);
      this.tasks.start("mm:selfcheck", this.selfCheck());
    }
  }

  /** If the arrival shelf had to wait for its chunks, it is there now: put the party back on it. */
  private *settleOnShelf(players: Player[]): Co {
    const ar = MM.arrival;
    const r = ar.r + 3;
    for (let i = 0; i < 100 && this.writer.hasDeferredIn(ar.x - r, ar.z - r, ar.x + r, ar.z + r); i++) yield 2;
    players.forEach((p, i) => {
      try {
        if (!p.isValid || p.dimension.id !== DIMENSION) return;
        if (Math.abs(p.location.y - (ar.y + 1.05)) > 0.5) {
          const a = (i / Math.max(1, players.length)) * Math.PI * 2;
          p.teleport({ x: ar.x + 0.5 + Math.cos(a) * 3, y: ar.y + 1.05, z: ar.z + 0.5 + Math.sin(a) * 3 }, { facingLocation: { x: 0, y: 150, z: 0 } });
        }
        p.removeEffect("slow_falling");
      } catch {
        /* ignore */
      }
    });
  }

  /** Background upkeep: finish block edits that wait for chunks nobody is near. */
  private *housekeeping(): Co {
    for (;;) {
      const busy = this.state === "loading" || this.state === "ending" || this.state === "finished";
      if (!busy && !this.focusing && this.writer.deferredOps > 0) yield* sweepDeferred(this.writer, `${SWEEP_ID}_bg`, 600, { abort: () => this.focusing });
      yield 40;
    }
  }

  private killLeftovers(): void {
    try {
      for (const e of this.dim.getEntities()) if (e.typeId.startsWith("anatomy:mm_") || e.hasTag(TAG)) e.remove();
    } catch {
      /* ignore */
    }
  }

  private wantLegs(): void {
    for (const site of this.m.legs)
      this.parts.want(`leg:${site.index}`, { type: ENT.leg, pos: site.pos, yaw: site.yaw, props: { [PROP.legIndex]: site.index, [PROP.pose]: this.phase === 2 ? 1 : 0 } });
  }

  private wantHeart(saved?: SavedEncounter): void {
    this.heartHpCache = saved ? Math.max(1, Math.min(HEART_MAX, Number(saved.data.heartHp ?? HEART_MAX))) : HEART_MAX;
    this.heartHpDebt = 0;
    this.parts.want("heart", {
      type: ENT.heart,
      pos: MM.heart,
      props: { [PROP.phase]: this.phase === 2 ? 2 : 1 },
      init: (e) => {
        e.getComponent("minecraft:health")?.setCurrentValue(this.heartHpCache);
        this.heartHpDebt = 0;
        // the boss bar shows the name tag (the pack's .lang name did not reach it: "Unknown")
        e.nameTag = HEART_NAME;
      },
    });
  }

  private wantNodes(saved?: SavedEncounter): void {
    const dead = new Set<string>(((saved?.data.nodeDead as string[] | undefined) ?? []).map(String));
    for (const id of dead) this.nodeDead.add(id);
    if (saved && saved.phase >= 2) return;
    for (const site of this.m.nodes) {
      if (dead.has(site.id)) continue;
      this.parts.want(`node:${site.id}`, { type: ENT.node, pos: site.pos, props: site.id === "root" ? { [PROP.hanging]: true } : {} });
    }
  }

  // ------------------------------------------------------------------ self-check
  /** Problems worth telling players about (empty when the fight is healthy). */
  private problems(): { missing: string[]; bad: PartReport[]; legsFailed: number } {
    const missing = missingEntityTypes(Object.values(ENT));
    const bad = this.parts.report().filter((r) => (r.key === "heart" || r.key.startsWith("node:")) && (r.state === "failed" || r.offsite));
    const legsFailed = this.parts.report("leg:").filter((r) => r.state === "failed").length;
    return { missing, bad, legsFailed };
  }

  /** 10 s into Phase 1 (and twice more while it lasts): report in chat if boss parts could not be created. */
  private *selfCheck(): Co {
    yield 200;
    for (let round = 0; round < 3 && this.state === "phase1"; round++) {
      const pr = this.problems();
      if (!pr.missing.length && !pr.bad.length && !pr.legsFailed) return;
      console.warn(`[anatomy] self-check: missing types [${pr.missing.join(", ")}]; ${pr.bad.map((r) => `${r.key}: ${r.state} ${r.error ?? ""}${r.offsite ? ` offsite ${r.offsite}` : ""}`).join("; ")}; legs failed ${pr.legsFailed}`);
      for (const p of this.audience())
        try {
          p.sendMessage(this.checkReport(p, true));
        } catch {
          /* ignore */
        }
      yield 1200;
    }
  }

  /** Full state of the boss parts, entity types and chunks, in the player's language. */
  checkReport(p: Player, problem = false): string {
    const L = (en: string, th: string) => tr(p, en, th);
    const fmt = (v?: V3) => (v ? `(${Math.floor(v.x)}, ${Math.floor(v.y)}, ${Math.floor(v.z)})` : "");
    const name = (key: string) => {
      if (key === "heart") return L("Lithic Heart", "หัวใจศิลา");
      const id = key.slice(5);
      return L(this.m.nodes.find((n) => n.id === id)?.name ?? id, NODE_TH[id] ?? id);
    };
    const line = (r: PartReport) => {
      const site = r.key === "heart" ? MM.heart : this.m.nodes.find((n) => `node:${n.id}` === r.key)?.pos;
      let st: string;
      if (r.state === "ok") st = `§a✔ §7${L("at", "อยู่ที่")} ${fmt(r.at)}`;
      else if (r.state === "unloaded") st = `§e● §7${L("created; its area is not loaded (no one nearby)", "สร้างแล้ว แต่บริเวณนั้นยังไม่โหลด (ไม่มีใครอยู่ใกล้)")}`;
      else if (r.state === "waiting") st = `§e… §7${L("waits for its area to load", "รอให้บริเวณนั้นโหลด")} ${fmt(site)}`;
      else st = `§c✘ ${L("could not be created", "สร้างไม่ได้")}: §f${r.error ?? "?"}`;
      const extra = r.offsite ? ` §e(${L(`appeared ${r.offsite} blocks away, moved back`, `ไปเกิดห่าง ${r.offsite} บล็อก ย้ายกลับแล้ว`)})` : r.via === "command" ? ` §8(/summon)` : "";
      return `§7• §f${name(r.key)}: ${st}${extra}`;
    };
    const missing = missingEntityTypes(Object.values(ENT));
    const legs = this.parts.report("leg:");
    const b = chunkBudget();
    const out: string[] = [];
    out.push(problem ? L("§6[Anatomy] Problem found — please screenshot this message for the developer:", "§6[Anatomy] พบปัญหา — กรุณาแคปหน้าจอข้อความนี้ส่งให้ผู้พัฒนา:") : L("§6[Anatomy] Fight check:", "§6[Anatomy] ตรวจสอบการต่อสู้:"));
    out.push(`§7${L("state", "สถานะ")}: §f${this.state} §7· ${L("nodes destroyed", "ทำลายผลึกแล้ว")} §f${this.nodeDead.size}/3`);
    for (const r of this.parts.report()) if (r.key === "heart" || r.key.startsWith("node:")) out.push(line(r));
    const legOk = legs.filter((r) => r.state === "ok" || r.state === "unloaded").length;
    const legFail = legs.find((r) => r.state === "failed");
    out.push(`§7• §f${L("Anchorage Roots", "รากยึดเกาะ")}: §f${legOk}/${legs.length}${legFail ? ` §c✘ ${legFail.error}` : ""}`);
    out.push(missing.length ? `§c✘ ${L("entity types the game did not load", "ชนิดเอนทิตีที่เกมไม่ได้โหลด")}: §f${missing.join(", ")}` : `§a✔ §7${L("entity types loaded", "โหลดชนิดเอนทิตีครบ")}`);
    out.push(`§8${L("chunks kept loaded", "ชังก์ที่โหลดค้าง")} ${this.keeper.kept}/${this.keeper.wanted} · ${L("budget", "โควต้า")} ${b.used}/${b.max ?? "?"} · ${L("waiting edits", "งานแก้บล็อกที่รอ")} ${this.writer.deferredOps}`);
    if (problem) out.push(`§8${L("The game's own error text: Settings → Creator → Content Log.", "ข้อความผิดพลาดของเกมเอง: ตั้งค่า → Creator → Content Log")}`);
    return out.join("\n");
  }

  /** Chat briefing: where the remaining nodes are (once per player per fight). */
  private brief(p: Player): void {
    if (this.briefed.has(p.id)) return;
    if (this.state === "phase3a" || this.state === "phase3b") {
      this.briefed.add(p.id);
      const lines =
        this.state === "phase3a"
          ? [
              tr(p, "§6◆ §ePhase 3 — The Last Migration", "§6◆ §eเฟส 3 — การอพยพครั้งสุดท้าย"),
              tr(
                p,
                "§7The mountain walks away across the cloud sea. §fFour Anchorage Roots§7 grip the disk (§6★§7 on the locator bar): break each root's glowing sinew knot — every severed root opens the heart for a few seconds.",
                "§7ภูเขากำลังเดินหนีไปบนทะเลเมฆ §fรากยึดเกาะ 4 ราก§7 จับลานไว้ (§6★§7 บนแถบระบุตำแหน่ง) ตีปมเอ็นเรืองแสงของแต่ละรากให้ขาด ทุกรากที่ขาด หัวใจจะเปิดให้ตีสักพัก",
              ),
              tr(p, "§7Jump the rolling ridges of its march.", "§7กระโดดข้ามคลื่นหินจากการก้าวเดิน"),
            ]
          : [
              tr(p, "§5◆ §dThe Heart Unbound", "§5◆ §dหัวใจหลุดจากร่าง"),
              tr(
                p,
                "§7The heart hovers over the centre island: §fbows and crossbows§7 hurt it (half damage). Every ~20 s it §fslams down§7 — get clear of the centre, then strike it while it is down.",
                "§7หัวใจลอยอยู่เหนือเกาะกลาง §fธนูและหน้าไม้§7 ทำดาเมจได้ (ครึ่งเดียว) ทุก ~20 วินาทีมันจะ§fกระแทกลงมา§7 — หลบออกจากเกาะกลางก่อน แล้วตีตอนมันอยู่บนพื้น",
              ),
              tr(p, "§7Jump between the islands; a fall into the clouds throws you back with a little damage.", "§7กระโดดข้ามเกาะไปมาได้ ตกลงไปในเมฆจะถูกเหวี่ยงกลับมาพร้อมเสียเลือดนิดหน่อย"),
            ];
      try {
        p.sendMessage(lines.join("\n"));
      } catch {
        /* ignore */
      }
      return;
    }
    if (this.state !== "phase1") return;
    const left = this.remainingSites();
    if (!left.length) return;
    this.briefed.add(p.id);
    const where: Record<string, [string, string]> = {
      dorsal: ["on the summit crag — follow the golden motes up the pilgrim path", "บนยอดผาสูงสุด — เดินตามละอองสีทองขึ้นไปตามทางเดิน"],
      cavern: ["inside the Organ Cavern — the tunnel mouth is on the front slope", "ในถ้ำอวัยวะ — ปากอุโมงค์อยู่ที่ลาดเขาด้านหน้า"],
      root: ["hanging under the body — take the spiral shaft down from the cavern", "ห้อยอยู่ใต้ตัวภูเขา — ลงบันไดวนจากในถ้ำลงไปด้านล่าง"],
    };
    const lines = [tr(p, `§5◆ §dDestroy the Resonance Nodes §7(purple crystals) — §f${left.length}§7 left:`, `§5◆ §dทำลาย Resonance Node §7(ผลึกสีม่วง) — เหลือ §f${left.length}§7 จุด:`)];
    for (const s of left) {
      const w = where[s.id];
      lines.push(`§7 • §f${tr(p, s.name, NODE_TH[s.id] ?? s.name)} §7${w ? tr(p, w[0], w[1]) : ""} §8(${Math.floor(s.pos.x)}, ${Math.floor(s.pos.y)}, ${Math.floor(s.pos.z)})`);
    }
    lines.push(
      tr(
        p,
        "§7Purple light pillars and the §d★§7 on the locator bar point to them; the action bar shows the nearest one. §8(Atlas → ภาษาไทย)",
        "§7เสาแสงสีม่วงและ §d★§7 บนแถบระบุตำแหน่งชี้ไปที่ผลึก แถบข้อความด้านล่างบอกระยะของผลึกที่ใกล้ที่สุด §8(Atlas → English)",
      ),
    );
    try {
      p.sendMessage(lines.join("\n"));
    } catch {
      /* ignore */
    }
  }

  private welcome(p: Player): void {
    this.known.add(p.id);
    try {
      p.locatorBar.removeAllWaypoints(); // markers left by an interrupted fight (only this pack's are touched)
    } catch {
      /* ignore */
    }
    try {
      p.fogSettings.push(FOG, "anatomy");
    } catch {
      /* ignore */
    }
    try {
      p.playMusic(this.phase === 2 ? MUSIC.phase2 : MUSIC.phase1, { fade: 3, loop: true, volume: 0.85 });
    } catch {
      /* ignore */
    }
    this.brief(p);
  }

  private farewell(p: Player): void {
    this.known.delete(p.id);
    this.briefed.delete(p.id);
    try {
      p.locatorBar.removeAllWaypoints();
    } catch {
      /* ignore */
    }
    try {
      p.fogSettings.remove("anatomy");
      p.stopMusic();
      p.camera.clear();
      p.onScreenDisplay.setHudVisibility(HudVisibility.Reset);
      p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, true);
      p.inputPermissions.setPermissionCategory(InputPermissionCategory.Jump, true);
    } catch {
      /* ignore */
    }
  }

  private cinematic(on: boolean): void {
    for (const p of this.audience()) {
      try {
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, !on);
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Jump, !on);
        p.onScreenDisplay.setHudVisibility(on ? HudVisibility.Hide : HudVisibility.Reset);
        if (on) p.camera.setCamera("minecraft:free", { location: { x: -22, y: 128, z: -112 }, facingLocation: { x: 0, y: 132, z: 0 } });
        else p.camera.clear();
      } catch {
        /* ignore */
      }
    }
  }

  private camTo(at: V3, look: V3, seconds: number): void {
    for (const p of this.audience()) {
      try {
        p.camera.setCamera("minecraft:free", { location: at, facingLocation: look, easeOptions: { easeTime: seconds, easeType: EasingType.InOutSine } });
      } catch {
        /* ignore */
      }
    }
  }

  // ------------------------------------------------------------------ tick
  tick(): void {
    this.now++;
    this.tasks.tick();
    if (this.now % 5 === 0) this.parts.tick(this.now);
    if (this.writer.deferredOps > 0) {
      // edits waiting where a player stands come first, with a bigger budget: they are about to be seen or stood in
      const here = this.audience().map((p) => [Math.floor(p.location.x) >> 4, Math.floor(p.location.z) >> 4] as [number, number]);
      const urgent = here.some(([cx, cz]) => this.writer.hasDeferredIn(cx * 16, cz * 16, cx * 16, cz * 16));
      this.writer.retryDeferred(urgent ? 2500 : this.writer.pending > 0 ? 300 : 1200, here);
    }
    if (this.now % 10 === 0) this.syncHeartHp();
    const fighting = FIGHTING.includes(this.state);
    const everyone = this.audience();
    if (this.state === "phase1" && this.terrain.enabled) {
      const lifts = this.terrain.tick(everyone);
      for (const l of lifts) if (l.rise > 2.5) shake([l.player], 0.4, 0.3);
    }
    this.writer.flush();
    if (fighting) this.director.update();
    this.trackSlabs();
    this.environment(everyone);
    if (this.now % 10 === 0) this.hud(everyone);
    if (this.now % 20 === 0) this.syncWaypoints(everyone);
    if (this.now % 4 === 0) this.rescue(everyone);
    if (this.state === "phase2") this.phase2Upkeep(everyone);
    if (this.state === "phase1") this.phase1Upkeep(everyone);
    if (this.state === "phase3a") this.phase3aUpkeep(everyone);
    if (this.state === "phase3b") this.phase3bUpkeep(everyone);
    if (fighting) this.checkDefeat();
  }

  private environment(everyone: Player[]): void {
    if (this.now % 20 !== 0) return;
    for (const p of everyone) if (!this.known.has(p.id)) this.welcome(p);
    for (const id of [...this.known]) {
      if (everyone.some((p) => p.id === id)) continue;
      const p = world.getAllPlayers().find((pl) => pl.id === id);
      if (p) this.farewell(p);
      else this.known.delete(id);
    }
    if (this.now % 200 === 0) {
      const t = world.getTimeOfDay();
      if (t > 12800 && t < 23200)
        for (const p of everyone)
          try {
            p.addEffect("night_vision", 420, { amplifier: 0, showParticles: false });
          } catch {
            /* ignore */
          }
    }
  }

  private hud(everyone: Player[]): void {
    if (this.state === "phase1") {
      const sites = this.remainingSites();
      for (const p of everyone) {
        let hint = "";
        if (sites.length) {
          const n = sites.reduce((a, b) => (dist3(a.pos, p.location) < dist3(b.pos, p.location) ? a : b));
          const d = Math.round(dist3(n.pos, p.location));
          hint = tr(p, ` §8| §7nearest: §f${n.name} §7${d}m ${arrow(p, n.pos, "en")}`, ` §8| §7ใกล้สุด: §f${NODE_TH[n.id] ?? n.name} §7${d} ม. ${arrow(p, n.pos, "th")}`);
        }
        actionbar([p], tr(p, `§5◆ §dResonance Nodes destroyed §f${this.nodeDead.size}/3`, `§5◆ §dทำลายผลึกแล้ว §f${this.nodeDead.size}/3`) + hint);
      }
    } else if (this.state === "phase2") {
      const left = Math.max(0, this.exposedUntil - this.now);
      const zoneHint = (p: Player) => (this.zoneOf(p) === "mantle" ? tr(p, " §8| §6stand on a steam vent to be thrown back up", " §8| §6ยืนบนช่องไอน้ำเพื่อให้ถูกดีดกลับขึ้นไป") : "");
      for (const p of everyone)
        actionbar(
          [p],
          left > 0
            ? tr(p, `§5◆ §dLithic Heart §aEXPOSED §f${Math.ceil(left / 20)}s`, `§5◆ §dหัวใจศิลา §aเปิดออกแล้ว §f${Math.ceil(left / 20)} วิ`) + zoneHint(p)
            : tr(p, "§5◆ §dLithic Heart §7sealed — survive its attacks to make it open", "§5◆ §dหัวใจศิลา §7ปิดอยู่ — เอาตัวรอดจากการโจมตีจนกว่ามันจะเปิด") + zoneHint(p),
        );
    } else if (this.state === "phase3a") {
      const left = Math.max(0, this.exposedUntil - this.now);
      const anchors = this.anchors();
      for (const p of everyone) {
        let line = tr(p, `§6◆ §eAnchorage Roots severed §f${ANCHORS - anchors.length}/${ANCHORS}`, `§6◆ §eตัดรากยึดเกาะแล้ว §f${ANCHORS - anchors.length}/${ANCHORS}`);
        if (left > 0) line += tr(p, ` §8| §aHEART EXPOSED §f${Math.ceil(left / 20)}s`, ` §8| §aหัวใจเปิด §f${Math.ceil(left / 20)} วิ`);
        else if (anchors.length) {
          const n = anchors.reduce((a, b) => (dist3(a.pos, p.location) < dist3(b.pos, p.location) ? a : b));
          const d = Math.round(dist3(n.pos, p.location));
          line += tr(p, ` §8| §7nearest root §f${d}m ${arrow(p, n.pos, "en")}`, ` §8| §7รากใกล้สุด §f${d} ม. ${arrow(p, n.pos, "th")}`);
        }
        actionbar([p], line);
      }
    } else if (this.state === "phase3b") {
      const down = this.heartSlamming();
      const left = Math.max(0, this.slamUntil - this.now);
      for (const p of everyone)
        actionbar(
          [p],
          down
            ? tr(p, `§5◆ §dThe Heart Unbound §aDOWN — strike it! §f${Math.ceil(left / 20)}s`, `§5◆ §dหัวใจหลุดจากร่าง §aตกลงมาแล้ว — ตีเลย! §f${Math.ceil(left / 20)} วิ`)
            : tr(p, "§5◆ §dThe Heart Unbound §7hovering — shoot it, or wait for it to slam down", "§5◆ §dหัวใจหลุดจากร่าง §7กำลังลอย — ยิงมัน หรือรอให้มันกระแทกลงมา"),
        );
    } else if (this.state === "aftermath") {
      const left = Math.max(0, this.aftermathEnd - this.now);
      for (const p of everyone)
        actionbar([p], tr(p, `§aThe mountain has settled. §7Returning home in §f${Math.ceil(left / 20)}s §8(Atlas: leave now)`, `§aภูเขาสงบลงแล้ว §7กลับบ้านใน §f${Math.ceil(left / 20)} วิ §8(ใช้ Atlas เพื่อออกทันที)`));
    }
  }

  private phase1Upkeep(everyone: Player[]): void {
    const heartC = this.heartCentre();
    if (this.now % 20 === 0) {
      // a tall purple light pillar over every remaining node (downwards for the hanging one)
      for (const s of this.remainingSites()) {
        const hanging = s.id === "root";
        particle(this.dim, PX.nodeBeacon, { x: s.pos.x, y: s.pos.y + (hanging ? -1 : 3.6), z: s.pos.z }, { up: hanging ? -1 : 1 });
      }
    }
    if (this.now % 30 === 0) {
      // the resonance network: beams from every remaining node into the shielded heart
      for (const s of this.remainingSites()) {
        const at = this.parts.get(`node:${s.id}`)?.location ?? s.pos;
        const from = { x: at.x, y: at.y + (s.id === "root" ? 1.5 : 2), z: at.z };
        const v = { x: heartC.x - from.x, y: heartC.y - from.y, z: heartC.z - from.z };
        const L = Math.hypot(v.x, v.y, v.z) || 1;
        particle(this.dim, PX.beam, from, { dir: { x: v.x / L, y: v.y / L, z: v.z / L }, speed: L / 1.5, life: 1.5 });
      }
      particle(this.dim, PX.shield, heartC, { radius: 4.2 });
    }
    if (this.now % 40 === 0) {
      // golden motes guide players along the pilgrim path toward the summit
      const pts = this.m.pathPoints;
      for (const p of everyone) {
        const z = this.zoneOf(p);
        if (z !== "dorsal" && z !== "arrival") continue;
        let bi = 0;
        let bd = 1e9;
        pts.forEach((q, i) => {
          const d = Math.hypot(q.x - p.location.x, q.z - p.location.z);
          if (d < bd) {
            bd = d;
            bi = i;
          }
        });
        if (bd > 30) continue;
        for (let k = 1; k <= 3 && bi + k < pts.length; k++) particle(this.dim, PX.guide, pts[bi + k]);
      }
    }
    if (this.now % 100 === 0) sound(this.dim, SND.heartbeat, heartC, 0.6, 0.85);
  }

  private phase2Upkeep(everyone: Player[]): void {
    const heartC = this.heartCentre();
    if (this.exposedUntil > 0 && this.now >= this.exposedUntil) {
      this.exposedUntil = 0;
      this.heartProp(PROP.open, false);
      sound(this.dim, SND.heartClose, heartC, 1, 1);
    }
    if (this.now % 10 === 0) particle(this.dim, PX.heartGlow, heartC, { intensity: this.exposedUntil > this.now ? 1 : 0 });
    if (this.now % 64 === 0) sound(this.dim, SND.heartbeat, heartC, 0.9, this.enraged() ? 1.25 : 1);
    // Mineral Circulation vents on the mantle floor throw fallen players back up
    if (this.now % 40 === 0) {
      for (let k = 0; k < 4; k++) {
        const a = ((45 + 90 * k) * Math.PI) / 180;
        const v = { x: MM.heart.x + Math.cos(a) * (D.ribEnd - 3), y: D.mantleY + 1, z: MM.heart.z + Math.sin(a) * (D.ribEnd - 3) };
        particle(this.dim, PX.vent, v);
        for (const p of everyone) {
          if (Math.hypot(p.location.x - v.x, p.location.z - v.z) > 3.2 || p.location.y > D.y - 1) continue;
          sound(this.dim, SND.vent, v, 1, 1);
          knock(p, Math.cos(a), Math.sin(a), 0.45, 2.3);
          try {
            p.addEffect("slow_falling", 40, { amplifier: 0, showParticles: false });
          } catch {
            /* ignore */
          }
        }
      }
    }
    if (!this.rebloomed && this.heartHp() < HEART_MAX * REBLOOM_AT && !this.director.busy) this.startRebloom();
    // at the Phase 2 floor the heart can take no more: the mountain refolds and starts to walk
    if (this.heartHp() <= HEART_MAX * FLOOR_P2 + 1 && this.now >= this.exposedUntil && !this.tasks.count("mm:ability:great_unfolding")) this.startRefold();
  }

  private trackSlabs(): void {
    if (!this.slabs.length) return;
    this.slabs = this.slabs.filter((s) => {
      if (!s.e.isValid) return false;
      if (this.now < s.land) return true;
      slabImpact(this, s.e.location, s.power);
      try {
        s.e.remove();
      } catch {
        /* ignore */
      }
      return false;
    });
  }

  private rescue(everyone: Player[]): void {
    if (this.state === "loading" || this.state === "ending" || this.state === "finished") return;
    for (const p of everyone) {
      if (p.location.y > 108) continue;
      let to: V3;
      if (this.arena() === "islands") to = this.islandSpot().pos;
      else if (this.phase >= 2) to = this.safeRingSpot().pos;
      else {
        const pts = this.m.pathPoints;
        let best = pts[0];
        let bd = 1e9;
        for (const q of pts) {
          const d = Math.hypot(q.x - p.location.x, q.z - p.location.z);
          if (d < bd) {
            bd = d;
            best = q;
          }
        }
        to = best ? { x: best.x, y: this.terrain.topAt(Math.floor(best.x), Math.floor(best.z)) + 1.05, z: best.z } : this.entryPoint().pos;
      }
      try {
        p.teleport(to, { keepVelocity: false });
        p.addEffect("slow_falling", 60, { amplifier: 0, showParticles: false });
        p.addEffect("resistance", 30, { amplifier: 2, showParticles: false });
      } catch {
        /* ignore */
      }
      if (p.getGameMode() !== GameMode.Creative) hurt(p, 4, EntityDamageCause.void, this.heart);
      p.sendMessage(tr(p, "§7The mist of the cloud sea hurls you back onto the mountain.", "§7หมอกแห่งทะเลเมฆเหวี่ยงคุณกลับขึ้นไปบนภูเขา"));
    }
  }

  private checkDefeat(): void {
    if (this.combatants().length > 0) {
      this.emptySince = -1;
      return;
    }
    if (this.emptySince < 0) this.emptySince = this.now;
    else if (this.now - this.emptySince > 600) {
      world.sendMessage("§7The Migrating Mountain wanders on through the cloud sea, unchallenged…");
      this.stop("defeat");
    }
  }

  // ------------------------------------------------------------------ damage
  onHurtBefore(ev: EntityHurtBeforeEvent): void {
    const e = ev.hurtEntity;
    if (!e.typeId.startsWith("anatomy:mm_")) return;
    if (e.typeId === ENT.heart) {
      const open = this.state === "phase3b" || ((this.state === "phase2" || this.state === "phase3a") && this.now < this.exposedUntil);
      if (!open) {
        ev.cancel = true;
        const src = ev.damageSource.damagingEntity;
        system.run(() => this.deflect(e, src));
        return;
      }
      let dmg = ev.damage * this.partyScale(0.55) * HEART_DAMAGE;
      // Phase 3B: half damage while it hovers (bows and crossbows), full when it is down on the centre island
      if (this.state === "phase3b" && !this.heartSlamming()) dmg *= 0.5;
      const hp = e.getComponent("minecraft:health")?.currentValue ?? HEART_MAX;
      const floor = this.state === "phase2" ? HEART_MAX * FLOOR_P2 : this.state === "phase3a" ? HEART_MAX * FLOOR_P3A : 0;
      if (floor > 0 && hp - dmg <= floor) {
        // a phase ends at its floor: the heart can take no more until the next one
        ev.damage = Math.max(0, hp - floor);
        if (ev.damage <= 0) ev.cancel = true;
        return;
      }
      ev.damage = dmg;
      if (floor === 0 && hp - dmg <= 1) {
        ev.cancel = true;
        system.run(() => this.startVictory());
      }
      return;
    }
    if (e.typeId === ENT.anchor) {
      const key = this.parts.keyOf(e);
      const k = key?.startsWith("anchor:") ? Number(key.slice(7)) : NaN;
      if (this.state !== "phase3a" || !Number.isFinite(k) || this.anchorsDying.has(k) || this.anchorsCut.has(k)) {
        ev.cancel = true;
        return;
      }
      ev.damage *= this.partyScale(0.45);
      const hp = e.getComponent("minecraft:health")?.currentValue ?? 0;
      if (hp - ev.damage <= 0.5) {
        ev.cancel = true;
        system.run(() => this.severAnchor(k, e, false));
      }
      return;
    }
    if (e.typeId === ENT.node) {
      // matched by entity id: a node whose chunk reloaded has a new handle
      const key = this.parts.keyOf(e);
      const site = key?.startsWith("node:") ? key.slice(5) : undefined;
      if (this.state !== "phase1" || !site || this.nodeDying.has(site) || this.nodeDead.has(site)) {
        ev.cancel = true;
        return;
      }
      ev.damage *= this.partyScale(0.45);
      const hp = e.getComponent("minecraft:health")?.currentValue ?? 0;
      if (hp - ev.damage <= 0.5) {
        ev.cancel = true;
        system.run(() => this.destroyNode(site, e, false));
      }
      return;
    }
    ev.cancel = true; // legs, petals, plates and slabs are scenery
  }

  onHurt(ev: EntityHurtAfterEvent): void {
    const e = ev.hurtEntity;
    if (!e.isValid) return;
    if (e.typeId === ENT.heart) {
      try {
        e.playAnimation(ANIM.heartHurt, { blendOutTime: 0.2 });
      } catch {
        /* ignore */
      }
      particle(this.dim, PX.shard, this.heartCentre(), { size: 0.8 });
    } else if (e.typeId === ENT.node || e.typeId === ENT.anchor) {
      particle(this.dim, PX.shard, { x: e.location.x, y: e.location.y + 1.6, z: e.location.z }, { size: 0.5 });
    }
  }

  onProjectileHitBlock(ev: ProjectileHitBlockAfterEvent): void {
    if (ev.projectile.typeId !== ENT.slab) return;
    this.impactSlab(ev.projectile, ev.location);
  }

  onProjectileHitEntity(ev: ProjectileHitEntityAfterEvent): void {
    if (ev.projectile.typeId !== ENT.slab) return;
    const hit = ev.getEntityHit()?.entity;
    if (hit && hit instanceof Player) this.hurt(hit, 3, EntityDamageCause.fallingBlock);
    this.impactSlab(ev.projectile, ev.location);
  }

  private impactSlab(e: Entity, at: V3): void {
    const s = this.slabs.find((x) => x.e === e);
    this.slabs = this.slabs.filter((x) => x.e !== e);
    slabImpact(this, at, s?.power ?? 9);
    try {
      if (e.isValid) e.remove();
    } catch {
      /* ignore */
    }
  }

  private deflect(e: Entity, src: Entity | undefined): void {
    if (!e.isValid) return;
    const c = this.heartCentre();
    sound(this.dim, SND.deflect, c, 1, 0.9 + this.rng() * 0.2);
    particle(this.dim, PX.shield, c, { radius: 3.6 });
    if (src instanceof Player) {
      const left = 3 - this.nodeDead.size;
      const msg =
        this.state === "phase1"
          ? tr(src, `§dThe Resonance Network shields the Lithic Heart §7(${left} nodes remain)`, `§dเครือข่ายกังวานปกป้องหัวใจศิลาอยู่ §7(เหลือผลึกอีก ${left} จุด)`)
          : tr(src, "§7The heart's iris is sealed — survive its attack and wait for it to open", "§7ม่านตาของหัวใจปิดอยู่ — เอาตัวรอดแล้วรอให้มันเปิด");
      src.onScreenDisplay.setActionBar(msg);
    }
  }

  private partyScale(per: number): number {
    const n = Math.max(1, this.combatants().length);
    return 1 / (1 + per * (n - 1));
  }

  private difficultyMult(): number {
    switch (world.getDifficulty()) {
      case Difficulty.Peaceful:
        return 0.5;
      case Difficulty.Easy:
        return 0.65;
      case Difficulty.Hard:
        return 1.35;
      default:
        return 1;
    }
  }

  private heartHp(): number {
    try {
      const h = this.heart;
      return h ? Math.max(1, (h.getComponent("minecraft:health")?.currentValue ?? this.heartHpCache) - this.heartHpDebt) : this.heartHpCache;
    } catch {
      return this.heartHpCache;
    }
  }

  /** Keep the last known heart health (and apply node damage dealt while its chunk was unloaded). */
  private syncHeartHp(): void {
    const h = this.heart;
    if (!h) return;
    try {
      const c = h.getComponent("minecraft:health");
      if (!c) return;
      if (this.heartHpDebt > 0) {
        c.setCurrentValue(Math.max(1, c.currentValue - this.heartHpDebt));
        this.heartHpDebt = 0;
      }
      this.heartHpCache = c.currentValue;
    } catch {
      /* stale */
    }
  }

  private heartCentre(): V3 {
    const y = this.heart?.isValid ? this.heart.location.y : MM.heart.y;
    return { x: MM.heart.x, y: y + 3, z: MM.heart.z };
  }

  // ------------------------------------------------------------------ nodes & phase change
  private destroyNode(id: string, e: Entity | undefined, silent: boolean): void {
    if (this.nodeDying.has(id) || this.nodeDead.has(id)) return;
    this.nodeDying.add(id);
    const site = this.m.nodes.find((n) => n.id === id);
    // no longer a tracked part: it plays its death animation and is removed (or removed when its chunk loads)
    const released = this.parts.release(`node:${id}`);
    const ent = released ?? (e?.isValid ? e : undefined);
    const base = ent?.isValid ? ent.location : (site?.pos ?? MM.heart);
    const at = { x: base.x, y: base.y + 1.6, z: base.z };
    try {
      ent?.setProperty(PROP.dying, true);
    } catch {
      /* ignore */
    }
    this.removeWaypoint(id);
    sound(this.dim, SND.shatter, at, 1, 1.1);
    particle(this.dim, PX.shard, at, { size: 2.5 });
    particle(this.dim, PX.dust, at, { size: 1.5 });
    for (const l of this.legs)
      try {
        l.playAnimation(ANIM.legFlinch, { blendOutTime: 0.4 });
      } catch {
        /* ignore */
      }
    quake(this.audience(), at, 1.5, 1.0, 200);
    sound(this.dim, SND.groan, this.heartCentre(), 1, 0.8);
    this.tasks.start(`mm:node:${id}`, this.nodeDeath(id, ent, site?.name ?? "Resonance Node", silent));
  }

  private *nodeDeath(id: string, e: Entity | undefined, name: string, silent: boolean): Co {
    yield 32;
    try {
      if (e?.isValid) e.remove();
    } catch {
      /* ignore */
    }
    this.nodeDying.delete(id);
    this.nodeDead.add(id);
    // each node strips part of the heart's health (applied when the heart is loaded)
    this.heartHpCache = Math.max(1, this.heartHpCache - HEART_MAX * NODE_SHARE);
    this.heartHpDebt += HEART_MAX * NODE_SHARE;
    this.syncHeartHp();
    this.director.aggression = 1 + this.nodeDead.size * 0.12;
    const n = this.nodeDead.size;
    if (!silent) titleFor(this.audience(), (p) => ["", tr(p, `§d${name} destroyed §f(${n}/3)`, `§dทำลาย${NODE_TH[id] ?? name}แล้ว §f(${n}/3)`)], 40, 5, 15);
    manager.save();
    if (this.nodeDead.size >= 3 && this.state === "phase1") {
      yield 40;
      this.startUnfolding();
    }
  }

  private startUnfolding(): void {
    if (this.state !== "phase1") return;
    this.state = "unfolding";
    this.director.reset(this.now, 9999);
    this.tasks.cancelAll("mm:ability");
    for (const s of this.slabs) if (s.e.isValid) s.e.remove();
    this.slabs = [];
    try {
      for (const e of this.dim.getEntities({ type: ENT.plate })) e.remove();
    } catch {
      /* ignore */
    }
    this.tasks.start(
      "mm:unfolding",
      greatUnfolding(this, {
        setPhase: () => this.enterPhase2(true),
        setLayout: (l) => (this.layout = l),
        onFinished: () => {
          /* enterPhase2 already switched state */
        },
      }),
      (err) => {
        console.error(`[anatomy] unfolding failed: ${String(err)}`);
        this.enterPhase2(true);
      },
    );
  }

  private enterPhase2(announce: boolean): void {
    this.phase = 2;
    this.state = "phase2";
    this.terrain.enabled = false;
    this.heartProp(PROP.phase, 2);
    this.clearWaypoints();
    for (const p of this.audience())
      try {
        p.playMusic(MUSIC.phase2, { fade: 2, loop: true, volume: 0.9 });
      } catch {
        /* ignore */
      }
    this.director.reset(this.now, announce ? 120 : 80);
    manager.save();
  }

  private startRebloom(): boolean {
    if (this.state !== "phase2" || this.rebloomed) return false;
    this.rebloomed = true;
    this.director.reset(this.now, 9999);
    this.tasks.cancelAll("mm:ability");
    this.tasks.start(
      "mm:ability:great_unfolding",
      rebloom(this, {
        setPhase: () => undefined,
        setLayout: (l) => (this.layout = l),
        onFinished: () => this.director.reset(this.now, 60),
      }),
    );
    return true;
  }

  // ------------------------------------------------------------------ Phase 3
  private phase3Hooks(): Phase3Hooks {
    return {
      spawnAnchors: () => this.spawnAnchors(),
      enterPhase3a: () => this.enterPhase3a(),
      shatter: () => this.shatter(),
      moveHeart: (y) => this.moveHeart(y),
      removePetals: () => this.parts.propAll("petal:", PROP.petalState, 3),
      enterPhase3b: () => this.enterPhase3b(),
    };
  }

  /** Phase 2 -> 3A: The Last Migration. */
  private startRefold(): void {
    if (this.state !== "phase2") return;
    this.state = "refolding";
    this.exposedUntil = 0;
    this.heartProp(PROP.open, false);
    this.director.reset(this.now, 9999);
    this.tasks.cancelAll("mm:ability");
    for (const sl of this.slabs) if (sl.e.isValid) sl.e.remove();
    this.slabs = [];
    try {
      for (const e of this.dim.getEntities({ type: ENT.plate })) e.remove();
    } catch {
      /* ignore */
    }
    // cancelled abilities leave ridges, walls and carved ribs behind: the disk the roots seize is pristine
    restoreDisk(this.writer, this.layout);
    this.tasks.start("mm:refold", refoldToMigration(this, this.phase3Hooks()), (err) => {
      console.error(`[anatomy] refold failed: ${String(err)}`);
      this.spawnAnchors();
      this.enterPhase3a();
    });
  }

  private spawnAnchors(): void {
    for (let k = 0; k < ANCHORS; k++) {
      if (this.anchorsCut.has(k) || this.parts.has(`anchor:${k}`)) continue;
      const s = anchorSite(k);
      this.parts.want(`anchor:${k}`, { type: ENT.anchor, pos: s.pos, yaw: s.yaw });
    }
  }

  private enterPhase3a(): void {
    this.phase = 3;
    this.state = "phase3a";
    this.p3aStart = this.now;
    this.nextStep = this.now + 40;
    this.terrain.enabled = false;
    this.heartProp(PROP.phase, 2);
    for (const p of this.audience())
      try {
        p.playMusic(MUSIC.phase3, { fade: 2, loop: true, volume: 0.9 });
      } catch {
        /* ignore */
      }
    this.director.reset(this.now, 100);
    this.briefed.clear();
    for (const p of this.audience()) this.brief(p);
    manager.save();
  }

  /**
   * Phase 3A: nothing solid grows over a live Anchorage Root's foot (waves, ridges and rubble pass around
   * it) - an entity is lit by the block at its anchor, and a root inside a block renders black.
   */
  private writeAllowed(x: number, y: number, z: number, b: number): boolean {
    if (b === P.AIR || this.phase !== 3 || this.islandsBuilt || y < D.y + 1 || y > D.y + 4) return true;
    for (let k = 0; k < ANCHORS; k++) {
      if (this.anchorsCut.has(k)) continue;
      const a = ANCHOR_SITES[k];
      if (Math.abs(x + 0.5 - a.x) <= 1.6 && Math.abs(z + 0.5 - a.z) <= 1.6) return false;
    }
    return true;
  }

  /** An Anchorage Root's sinew snaps: the mountain staggers and the heart opens. */
  private severAnchor(k: number, e: Entity | undefined, silent: boolean): void {
    if (this.anchorsDying.has(k) || this.anchorsCut.has(k)) return;
    this.anchorsDying.add(k);
    const ent = this.parts.release(`anchor:${k}`) ?? (e?.isValid ? e : undefined);
    const at = anchorSite(k).pos;
    try {
      ent?.setProperty(PROP.dying, true);
    } catch {
      /* ignore */
    }
    this.removeWaypoint(`anchor:${k}`);
    sound(this.dim, SND.sinewSnap, at, 1, 1);
    sound(this.dim, SND.rootTear, at, 1, 0.7);
    particle(this.dim, PX.shard, { x: at.x, y: at.y + 2, z: at.z }, { size: 2.2 });
    particle(this.dim, PX.debris, at, { size: 2.5 });
    quake(this.audience(), at, 1.8, 1.2, 80);
    sound(this.dim, SND.groan, this.heartCentre(), 1, 0.75);
    // the mountain staggers toward the lost root
    for (const p of this.combatants()) knock(p, at.x - MM.heart.x, at.z - MM.heart.z, 0.35, 0.3);
    if (!silent) this.exposeHeart(ANCHOR_WINDOW);
    this.tasks.start(`mm:anchor:${k}`, this.anchorDeath(k, ent, silent));
  }

  private *anchorDeath(k: number, e: Entity | undefined, silent: boolean): Co {
    yield 56;
    try {
      if (e?.isValid) e.remove();
    } catch {
      /* ignore */
    }
    this.anchorsDying.delete(k);
    this.anchorsCut.add(k);
    const n = this.anchorsCut.size;
    if (!silent) titleFor(this.audience(), (p) => ["", tr(p, `§6Anchorage Root severed §f(${n}/${ANCHORS})`, `§6ตัดรากยึดเกาะแล้ว §f(${n}/${ANCHORS})`)], 40, 5, 15);
    manager.save();
    if (n >= ANCHORS && this.state === "phase3a") this.fallAfter = Math.max(this.now, this.exposedUntil);
  }

  private phase3aUpkeep(everyone: Player[]): void {
    const heartC = this.heartCentre();
    if (this.exposedUntil > 0 && this.now >= this.exposedUntil) {
      this.exposedUntil = 0;
      this.heartProp(PROP.open, false);
      sound(this.dim, SND.heartClose, heartC, 1, 1);
    }
    if (this.now % 10 === 0) particle(this.dim, PX.heartGlow, heartC, { intensity: this.exposedUntil > this.now ? 1 : 0 });
    // the march: a heavy footfall every few seconds, a rolling ridge every third one
    if (this.now >= this.nextStep) {
      this.steps++;
      this.nextStep = this.now + (this.enraged() ? 40 : 60);
      sound(this.dim, SND.step, { x: MM.heart.x - this.walkDir.x * 30, y: D.y - 8, z: MM.heart.z - this.walkDir.z * 30 }, 1, 0.7);
      quake(everyone, heartC, 0.45, 0.35, 90);
      if (this.steps % 3 === 0 && !this.tasks.count("mm:gait")) this.tasks.start("mm:gait", marchWave(this, this.enraged() ? 2 : 1, 3, false));
    }
    // the cloud sea streams past the walking body
    if (this.now % 8 === 0)
      for (const p of everyone)
        particle(
          this.dim,
          PX.cloudStream,
          { x: p.location.x + this.walkDir.x * 14, y: p.location.y + 1, z: p.location.z + this.walkDir.z * 14 },
          { dir: { x: -this.walkDir.x, y: 0, z: -this.walkDir.z }, speed: 16 },
        );
    if (this.now % 64 === 0) sound(this.dim, SND.heartbeat, heartC, 0.9, this.enraged() ? 1.3 : 1.1);
    if (this.now - this.p3aStart === P3A_ENRAGE) for (const p of everyone) p.sendMessage(tr(p, "§c⚠ The mountain gathers speed — it is escaping!", "§c⚠ ภูเขาเร่งฝีเท้า — มันกำลังหนี!"));
    if (this.fallAfter >= 0 && this.now >= this.fallAfter) {
      this.fallAfter = -1;
      this.startFall();
    }
  }

  /** 3A -> 3B: The Mountain Falls. */
  private startFall(): void {
    if (this.state !== "phase3a") return;
    this.state = "falling";
    this.exposedUntil = 0;
    this.director.reset(this.now, 9999);
    this.tasks.cancelAll("mm:ability");
    this.tasks.cancelAll("mm:gait");
    for (const sl of this.slabs) if (sl.e.isValid) sl.e.remove();
    this.slabs = [];
    this.clearWaypoints();
    this.tasks.start("mm:fall", mountainFalls(this, this.phase3Hooks()), (err) => {
      console.error(`[anatomy] fall failed: ${String(err)}`);
      if (!this.islandsBuilt) this.tasks.start("mm:shatter", this.shatter());
      this.heartProp(PROP.phase, 3);
      this.moveHeart(HOVER_Y);
      this.enterPhase3b();
    });
  }

  private *shatter(): Co {
    // plates and rubble of the last abilities go with the disk
    try {
      for (const e of this.dim.getEntities({ type: ENT.plate })) e.remove();
    } catch {
      /* ignore */
    }
    this.islandsBuilt = true;
    yield* shatterDisk(this.writer);
  }

  private moveHeart(y: number): void {
    const h = this.heart;
    if (!h) return;
    try {
      h.teleport({ x: MM.heart.x, y, z: MM.heart.z });
    } catch {
      /* stale */
    }
  }

  private enterPhase3b(): void {
    this.phase = 3;
    this.state = "phase3b";
    this.islandsBuilt = true;
    this.heartProp(PROP.phase, 3);
    this.heartProp(PROP.open, true);
    this.slam = "hover";
    this.slamAt = this.now + 260;
    for (let k = 0; k < PETALS; k++) this.parts.drop(`petal:${k}`);
    for (let k = 0; k < ANCHORS; k++) this.parts.drop(`anchor:${k}`);
    this.director.reset(this.now, 80);
    this.briefed.clear();
    for (const p of this.audience()) this.brief(p);
    manager.save();
  }

  /** The heart hovers, warns, slams down on the centre island, stays down for a melee window, rises. */
  private phase3bUpkeep(everyone: Player[]): void {
    const c = { x: MM.heart.x, y: D.y + 1, z: MM.heart.z };
    const h = this.heart;
    const hy = h?.location.y ?? HOVER_Y;
    if (this.now % 10 === 0) particle(this.dim, PX.heartGlow, { x: c.x, y: hy + 3, z: c.z }, { intensity: this.heartSlamming() ? 1 : 0.4 });
    if (this.now % 48 === 0) sound(this.dim, SND.heartbeat, { x: c.x, y: hy + 3, z: c.z }, 1, this.enraged() ? 1.35 : 1.15);
    switch (this.slam) {
      case "hover":
        if (this.now % 4 === 0) this.moveHeart(HOVER_Y + Math.sin(this.now / 18) * 0.6);
        if (this.now >= this.slamAt - 40 && !this.director.busy) {
          this.slam = "warn";
          titleFor(everyone, (p) => ["", tr(p, "§c⚠ The heart is about to slam down — clear the centre!", "§c⚠ หัวใจกำลังจะกระแทกลงมา — ออกจากเกาะกลาง!")], 30, 4, 8);
          sound(this.dim, SND.warn, c, 1, 0.8);
        }
        break;
      case "warn":
        if (this.now % 4 === 0) particle(this.dim, PX.target, c, { radius: 4.5, life: 0.4 });
        if (this.now >= this.slamAt) {
          this.slam = "falling";
          this.slamUntil = this.now + 8;
        }
        break;
      case "falling": {
        const k = 1 - (this.slamUntil - this.now) / 8;
        this.moveHeart(HOVER_Y + (SLAM_Y - HOVER_Y) * Math.min(1, k * k));
        if (this.now >= this.slamUntil) {
          this.moveHeart(SLAM_Y);
          this.slam = "down";
          this.slamUntil = this.now + SLAM_DOWN;
          sound(this.dim, SND.quake, c, 1, 0.7);
          sound(this.dim, SND.heartOpen, c, 1, 0.9);
          quake(everyone, c, 2.2, 0.9, 60);
          particle(this.dim, PX.debris, c, { size: 3 });
          for (const p of this.combatants()) {
            const r = Math.hypot(p.location.x - c.x, p.location.z - c.z);
            if (r < 4.5 && Math.abs(p.location.y - c.y) < 4) {
              this.hurt(p, 9, EntityDamageCause.entityAttack);
              knock(p, p.location.x - c.x || 1, p.location.z - c.z, 1.1, 0.5);
            }
          }
          this.tasks.start("mm:slam", slamRings(this, this.enraged() ? 3 : 2));
          titleFor(everyone, (p) => ["", tr(p, "§a◆ The heart is DOWN — strike it now!", "§a◆ หัวใจตกลงมาแล้ว — ตีเลย!")], 40, 4, 10);
        }
        break;
      }
      case "down":
        if (this.now >= this.slamUntil) {
          this.slam = "rising";
          this.slamUntil = this.now + 30;
          sound(this.dim, SND.heartRise, c, 0.8, 1.3);
        }
        break;
      case "rising": {
        const k = 1 - (this.slamUntil - this.now) / 30;
        this.moveHeart(SLAM_Y + (HOVER_Y - SLAM_Y) * Math.min(1, k));
        if (this.now >= this.slamUntil) {
          this.slam = "hover";
          this.slamAt = this.now + (this.enraged() ? SLAM_EVERY - 100 : SLAM_EVERY);
        }
        break;
      }
    }
  }

  // ------------------------------------------------------------------ victory & cleanup
  private aftermathEnd = 0;

  private startVictory(): void {
    if (this.state !== "phase2" && this.state !== "phase3a" && this.state !== "phase3b") return;
    this.state = "victory";
    this.director.reset(this.now, 999999);
    this.tasks.cancelAll("mm:ability");
    if (this.heart?.isValid) this.heart.getComponent("minecraft:health")?.setCurrentValue(1);
    const seconds = (system.currentTick - this.startedAt) / 20;
    manager.record(this.def.id, "victories");
    manager.record(this.def.id, "bestSeconds", seconds);
    this.tasks.start(
      "mm:victory",
      (function* (self: MigratingMountainEncounter): Co {
        yield* victorySequence(self, () => self.dropLoot());
        self.state = "aftermath";
        self.aftermathEnd = self.now + 900;
        while (self.now < self.aftermathEnd) yield 10;
        self.stop("victory");
      })(this),
    );
  }

  /** Rewards: a bundle into every player's inventory, a shared pile at the heart, and the mountain's gear. */
  private dropLoot(): void {
    const n = Math.max(1, this.combatants().length);
    const at = { x: MM.heart.x, y: D.y + 1.5, z: MM.heart.z + 5 };
    this.lootSpot = at;
    for (const p of this.audience()) this.givePersonalLoot(p);
    const shared: [string, number][] = [
      ["minecraft:amethyst_shard", 64],
      ["minecraft:diamond", 6 + 2 * n],
      ["minecraft:emerald", 12 + 4 * n],
      ["minecraft:netherite_ingot", 1 + Math.floor(n / 2)],
    ];
    for (const [id, count] of shared) {
      try {
        this.dim.spawnItem(new ItemStack(id, count), at);
      } catch (e) {
        console.warn(`[anatomy] loot ${id} failed: ${String(e)}`);
      }
    }
    try {
      this.dim.spawnXp(at, 1500);
    } catch {
      /* ignore */
    }
    particle(this.dim, PX.pillar, at, { radius: 1.5, life: 20 });
    sound(this.dim, SND.chime, at, 1, 1.2);
  }

  private givePersonalLoot(p: Player): void {
    const r = (a: number, b: number) => a + Math.floor(this.rng() * (b - a + 1));
    const stacks: ItemStack[] = [
      new ItemStack(ITEM.shard, 3),
      new ItemStack("minecraft:diamond", r(8, 12)),
      new ItemStack("minecraft:emerald", r(16, 24)),
      new ItemStack("minecraft:netherite_scrap", r(2, 3)),
      new ItemStack("minecraft:gold_ingot", 16),
      new ItemStack("minecraft:golden_apple", 4),
      new ItemStack("minecraft:experience_bottle", 32),
      this.enchantedBook(),
      this.enchantedBook(),
    ];
    // the mountain's own gear: certain on a player's first victory, then 40% each
    let first = true;
    try {
      first = p.getDynamicProperty(GEAR_KEY) !== true;
    } catch {
      /* ignore */
    }
    const gear: string[] = [];
    for (const id of [ITEM.breaker, ITEM.greaves])
      if (first || this.rng() < 0.4) {
        stacks.push(new ItemStack(id, 1));
        gear.push(id);
      }
    try {
      if (first) p.setDynamicProperty(GEAR_KEY, true);
    } catch {
      /* ignore */
    }
    const inv = p.getComponent("minecraft:inventory")?.container;
    for (const st of stacks) {
      let left: ItemStack | undefined = st;
      try {
        if (inv) left = inv.addItem(st);
      } catch {
        left = st;
      }
      // a full inventory: the rest lands at their feet (and is carried home if left behind)
      if (left)
        try {
          this.dim.spawnItem(left, p.location);
        } catch {
          /* ignore */
        }
    }
    const names: Record<string, [string, string]> = { [ITEM.breaker]: ["Strata Breaker", "ค้อนชั้นหิน"], [ITEM.greaves]: ["Anchorage Greaves", "รองเท้ารากยึด"] };
    const gearText = gear.map((g) => tr(p, names[g][0], names[g][1])).join(", ");
    try {
      p.sendMessage(
        tr(p, "§d◆ The mountain's spoils are in your inventory", "§d◆ ของจากภูเขาเข้ากระเป๋าแล้ว") +
          (gear.length ? tr(p, ` §7— and §6${gearText}§7!`, ` §7— และ §6${gearText}§7!`) : ""),
      );
    } catch {
      /* ignore */
    }
  }

  private enchantedBook(): ItemStack {
    const options: [string, number][] = [
      ["mending", 1],
      ["unbreaking", 3],
      ["protection", 4],
      ["sharpness", 5],
      ["efficiency", 5],
      ["fortune", 3],
      ["feather_falling", 4],
      ["power", 5],
    ];
    const [id, level] = options[Math.floor(this.rng() * options.length)];
    const book = new ItemStack("minecraft:enchanted_book", 1);
    try {
      book.getComponent("minecraft:enchantable")?.addEnchantment({ type: new EnchantmentType(id), level });
    } catch (e) {
      console.warn(`[anatomy] enchanted book ${id} failed: ${String(e)}`);
    }
    return book;
  }

  private *ending(reason: "victory" | "defeat" | "abort"): Co {
    const players = this.audience();
    // anything players dropped (or loot they left behind) is carried home with them
    let strays: Entity[] = [];
    try {
      strays = this.dim.getEntities({ type: "minecraft:item" }).concat(this.dim.getEntities({ type: "minecraft:xp_orb" }));
    } catch {
      strays = [];
    }
    for (const p of players)
      try {
        p.camera.fade({ fadeColor: { red: 0, green: 0, blue: 0 }, fadeTime: { fadeInTime: 0.6, holdTime: 0.8, fadeOutTime: 1.0 } });
      } catch {
        /* ignore */
      }
    if (reason !== "victory") titleFor(players, (p) => [tr(p, "§7The mountain migrates on…", "§7ภูเขาอพยพต่อไป…"), ""], 40, 10, 20);
    yield 14;
    for (const p of players) {
      this.farewell(p);
      leaveArena(p);
    }
    const home = players.find((p) => p.isValid && p.dimension.id !== DIMENSION) ?? world.getAllPlayers().find((p) => p.getDynamicProperty("anatomy:return") === undefined);
    for (const e of strays) {
      try {
        if (!e.isValid) continue;
        if (home) e.teleport({ x: home.location.x, y: home.location.y + 0.5, z: home.location.z }, { dimension: home.dimension });
        else e.teleport(world.getDefaultSpawnLocation(), { dimension: world.getDimension("minecraft:overworld") });
      } catch {
        /* ignore */
      }
    }
    for (const id of [...this.known]) {
      const p = world.getAllPlayers().find((pl) => pl.id === id);
      if (p) this.farewell(p);
    }
    this.known.clear();
    this.clearWaypoints();
    this.parts.clear();
    this.killLeftovers();
    this.writer.clear();
    yield* clearArena(this.writer, 4);
    // the chunks the fight kept loaded are clean now; the whole budget goes to the rest
    this.keeper.release();
    if (this.writer.deferredOps > 0) yield* sweepDeferred(this.writer, SWEEP_ID, 2400);
    if (this.writer.deferredOps > 0) console.warn(`[anatomy] arena clean-up: ${this.writer.deferredOps} edits wait for chunks that could not be loaded; the next fight clears them`);
    yield 40;
    this.killLeftovers();
    AreaKeeper.releaseAll();
    this.finishNow();
  }

  private finishNow(): void {
    this.state = "finished";
    void this.stopReason;
    void this.lootSpot;
  }

  // ------------------------------------------------------------------ locator bar
  /** Purple ★ markers on every player's locator bar, one per remaining node (Phase 1 only). */
  private syncWaypoints(everyone: Player[]): void {
    const targets: { id: string; pos: V3; color: { red: number; green: number; blue: number } }[] =
      this.state === "phase1"
        ? this.remainingSites().map((s) => ({ id: s.id, pos: { x: s.pos.x, y: s.pos.y + (s.id === "root" ? 0 : 1.7), z: s.pos.z }, color: NODE_COLOR }))
        : this.state === "phase3a"
          ? this.anchors().map((a) => ({ id: `anchor:${a.k}`, pos: { x: a.pos.x, y: a.pos.y + 2, z: a.pos.z }, color: ANCHOR_COLOR }))
          : [];
    for (const id of [...this.waypoints.keys()]) if (!targets.some((t) => t.id === id)) this.removeWaypoint(id);
    if (!targets.length || this.waypointsBroken) return;
    for (const site of targets) {
      let wp = this.waypoints.get(site.id);
      if (!wp) {
        try {
          wp = new LocationWaypoint(
            { dimension: this.dim, x: site.pos.x, y: site.pos.y, z: site.pos.z },
            { textureBoundsList: [{ lowerBound: 0, texture: WaypointTexture.SmallStar }] },
            site.color,
          );
        } catch (e) {
          this.waypointsBroken = true;
          console.warn(`[anatomy] locator bar waypoints unavailable: ${String(e)}`);
          return;
        }
        this.waypoints.set(site.id, wp);
      }
      for (const p of everyone)
        try {
          if (!p.locatorBar.hasWaypoint(wp)) p.locatorBar.addWaypoint(wp);
        } catch {
          /* bar full or locator bar disabled */
        }
    }
  }

  private removeWaypoint(id: string): void {
    const wp = this.waypoints.get(id);
    if (!wp) return;
    this.waypoints.delete(id);
    try {
      wp.remove();
    } catch {
      /* ignore */
    }
  }

  private clearWaypoints(): void {
    for (const id of [...this.waypoints.keys()]) this.removeWaypoint(id);
  }

  private pockets(): V3[] {
    if (this.pocketCache) return this.pocketCache;
    const cv = MM.cavern;
    const out: V3[] = [];
    const cavernNode = this.m.nodes.find((n) => n.id === "cavern");
    for (let k = 0; k < 10 && out.length < 5; k++) {
      const a = (k / 10) * Math.PI * 2 + 0.4;
      for (const q of [0.62, 0.72, 0.52]) {
        const x = Math.floor(cv.x + Math.cos(a) * cv.rx * q);
        const z = Math.floor(cv.z + Math.sin(a) * cv.rz * q);
        if (pristineBlock(x, cv.floorY + 1, z) !== P.AIR || pristineBlock(x, cv.floorY + 2, z) !== P.AIR) continue;
        if (pristineBlock(x, cv.floorY, z) < 2) continue;
        if (Math.hypot(x - MM.heart.x, z - MM.heart.z) < 9.5) continue;
        if (cavernNode && Math.hypot(x - cavernNode.pos.x, z - cavernNode.pos.z) < 5) continue;
        if (out.some((o) => Math.hypot(o.x - x, o.z - z) < 9)) continue;
        out.push({ x: x + 0.5, y: cv.floorY + 1, z: z + 0.5 });
        break;
      }
    }
    this.pocketCache = out;
    return out;
  }
}

function dist3(a: V3, b: V3): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

const ARROWS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"];

/** Screen-relative arrow from the player's facing toward a location. */
function arrow(p: Player, to: V3, lang: "en" | "th" = "en"): string {
  const yaw = p.getRotation().y;
  const fwd = Math.atan2(-Math.sin((yaw * Math.PI) / 180), Math.cos((yaw * Math.PI) / 180));
  const dir = Math.atan2(to.x - p.location.x, to.z - p.location.z);
  const d = angleDiffDeg((dir * 180) / Math.PI, (fwd * 180) / Math.PI);
  const up = to.y - p.location.y;
  const idx = Math.round(((-d % 360) + 360) % 360 / 45) % 8;
  const above = lang === "th" ? " §7(ด้านบน)" : " §7(above)";
  const below = lang === "th" ? " §7(ด้านล่าง)" : " §7(below)";
  return `${ARROWS[idx]}${up > 6 ? above : up < -6 ? below : ""}`;
}
