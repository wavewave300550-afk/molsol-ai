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
import { LivingNode, MMContext, Zone } from "./context.js";
import { Director } from "./director.js";
import { ANIM, DIMENSION, ENT, FOG, MUSIC, PROP, PX, SND, TAG } from "./ids.js";
import { arenaChunks, clearArena, cutColumns, mountain, placeBody, placeDisk, pristineBlock, sectorColumns } from "./runtime.js";
import { DorsalTerrain } from "./terrain.js";
import { greatUnfolding, PETALS, petalSite, rebloom, ringSpot, victorySequence } from "./unfolding.js";

type State = "loading" | "intro" | "phase1" | "unfolding" | "phase2" | "victory" | "aftermath" | "ending" | "finished";

const D = MM.disk;
/** Health attribute of the heart (kept at 1000; incoming damage is halved for a 2000-point fight). */
const HEART_MAX = 1000;
const HEART_DAMAGE = 0.5;
const NODE_SHARE = 0.1333;
const REBLOOM_AT = 0.3;
const AREA_PREFIX = "anatomy_mm_area";
const SWEEP_ID = "anatomy_mm_sweep";
/** Thai names of the Resonance Nodes. */
const NODE_TH: Record<string, string> = { dorsal: "ผลึกยอดเขา", cavern: "ผลึกในถ้ำ", root: "ผลึกใต้ราก" };
const NODE_COLOR = { red: 0.78, green: 0.38, blue: 1 };
/** Shown on the boss bar. */
const HEART_NAME = "The Migrating Mountain";

export class MigratingMountainEncounter implements BossEncounter, MMContext {
  readonly dim: Dimension;
  readonly m: MountainModel;
  readonly writer: BlockWriter;
  readonly terrain: DorsalTerrain;
  readonly tasks = new TaskRunner();
  readonly director: Director;
  state: State = "loading";
  phase: 1 | 2 = 1;
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
      `remaining: ${sites || "-"}\n` +
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
    if (this.phase === 2) return this.safeRingSpot();
    const ar = MM.arrival;
    return { pos: { x: ar.x + 0.5, y: ar.y + 1.05, z: ar.z + 0.5 }, facing: { x: 0, y: 150, z: 0 } };
  }

  serialize(): SavedEncounter {
    return {
      boss: this.def.id,
      phase: this.phase,
      data: { nodeDead: [...this.nodeDead], heartHp: this.heartHp(), layout: this.layout, rebloomed: this.rebloomed },
    };
  }

  forcePhase(phase: number): boolean {
    if (phase === 2 && this.state === "phase1") {
      for (const site of this.remainingSites()) this.destroyNode(site.id, this.parts.get(`node:${site.id}`), true);
      return true;
    }
    return false;
  }

  forceAbility(id: string): boolean {
    if (this.state !== "phase1" && this.state !== "phase2") return false;
    if (!ABILITY_IDS.includes(id as AbilityId)) return false;
    if (id === "great_unfolding") return this.state === "phase1" ? this.forcePhase(2) : this.startRebloom();
    return this.director.force(id as AbilityId, undefined);
  }

  killBoss(): boolean {
    if (this.state === "phase1") this.forcePhase(2);
    if (this.state === "phase2") {
      this.startVictory();
      return true;
    }
    return false;
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
    if (this.phase === 2) {
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
    return this.phase === 2 && this.heartHp() < HEART_MAX * 0.2;
  }

  exposeHeart(ticks: number): void {
    if (this.state !== "phase2") return;
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
    if (saved && saved.phase === 2) {
      this.layout = Number(saved.data.layout ?? 0);
      this.rebloomed = Boolean(saved.data.rebloomed);
      const all = sectorColumns(1, 0)[0];
      for (let i = 0; i < all.length; i += 400) {
        cutColumns(this.writer, all.slice(i, i + 400));
        yield 1;
      }
      while (this.writer.pending > 0) yield 1;
      placeDisk(this.dim, this.writer, this.layout, 0);
      for (let k = 0; k < PETALS; k++) this.petal(k, 1);
      this.setLegPose(1);
      this.terrain.enabled = false;
      const inside = this.audience();
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
      this.enterPhase2(false);
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
    if (saved && saved.phase === 2) return;
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
    if (this.state !== "phase1" || this.briefed.has(p.id)) return;
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
    const fighting = this.state === "phase1" || this.state === "phase2";
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
      if (this.phase === 2) to = this.safeRingSpot().pos;
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
      if (this.state !== "phase2" || this.now >= this.exposedUntil) {
        ev.cancel = true;
        const src = ev.damageSource.damagingEntity;
        system.run(() => this.deflect(e, src));
        return;
      }
      ev.damage *= this.partyScale(0.55) * HEART_DAMAGE;
      const hp = e.getComponent("minecraft:health")?.currentValue ?? HEART_MAX;
      if (hp - ev.damage <= 1) {
        ev.cancel = true;
        system.run(() => this.startVictory());
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
    } else if (e.typeId === ENT.node) {
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

  // ------------------------------------------------------------------ victory & cleanup
  private aftermathEnd = 0;

  private startVictory(): void {
    if (this.state !== "phase2") return;
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

  private dropLoot(): void {
    const n = Math.max(1, this.combatants().length);
    const at = { x: MM.heart.x, y: D.y + 1.5, z: MM.heart.z + 6 };
    this.lootSpot = at;
    const drops: [string, number][] = [
      ["anatomy:lithic_heart_shard", 1 + n],
      ["minecraft:amethyst_shard", 16 + Math.floor(this.rng() * 9)],
      ["minecraft:diamond", 2 + Math.floor(this.rng() * 3)],
      ["minecraft:emerald", 4 + Math.floor(this.rng() * 5)],
      ["minecraft:moss_block", 8],
    ];
    for (const [id, count] of drops) {
      try {
        this.dim.spawnItem(new ItemStack(id, count), at);
      } catch (e) {
        console.warn(`[anatomy] loot ${id} failed: ${String(e)}`);
      }
    }
    try {
      this.dim.spawnXp(at, 600);
    } catch {
      /* ignore */
    }
    particle(this.dim, PX.pillar, at, { radius: 1.5, life: 20 });
    sound(this.dim, SND.chime, at, 1, 1.2);
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
    if (this.state !== "phase1") {
      if (this.waypoints.size) this.clearWaypoints();
      return;
    }
    if (this.waypointsBroken) return;
    for (const site of this.remainingSites()) {
      let wp = this.waypoints.get(site.id);
      if (!wp) {
        try {
          wp = new LocationWaypoint(
            { dimension: this.dim, x: site.pos.x, y: site.pos.y + (site.id === "root" ? 0 : 1.7), z: site.pos.z },
            { textureBoundsList: [{ lowerBound: 0, texture: WaypointTexture.SmallStar }] },
            NODE_COLOR,
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
