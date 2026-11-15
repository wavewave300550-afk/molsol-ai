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
  Player,
  ProjectileHitBlockAfterEvent,
  ProjectileHitEntityAfterEvent,
  system,
  world,
} from "@minecraft/server";
import { combatants, enterArena, hurt, knock, leaveArena, loadArea, playersIn, unloadArea } from "../../core/arena.js";
import { BlockWriter } from "../../core/blocks.js";
import { actionbar, particle, quake, shake, sound, title } from "../../core/fx.js";
import { manager } from "../../core/manager.js";
import { BossDefinition, BossEncounter, SavedEncounter } from "../../core/registry.js";
import { Co, TaskRunner } from "../../core/tasks.js";
import { angleDiffDeg, V3 } from "../../core/vec.js";
import { ColFlag, MM, MountainModel } from "../../gen/mountain.js";
import { Rng } from "../../gen/noise.js";
import * as P from "../../gen/palette.js";
import { ABILITY_IDS, AbilityId, slabImpact } from "./abilities.js";
import { LivingNode, MMContext, Zone } from "./context.js";
import { Director } from "./director.js";
import { ANIM, DIMENSION, ENT, FOG, MUSIC, PROP, PX, SND, TAG } from "./ids.js";
import { arenaBounds, clearArena, cutColumns, mountain, placeBody, placeDisk, pristineBlock, sectorColumns } from "./runtime.js";
import { DorsalTerrain } from "./terrain.js";
import { greatUnfolding, PETALS, rebloom, ringSpot, spawnPetal, victorySequence } from "./unfolding.js";

type State = "loading" | "intro" | "phase1" | "unfolding" | "phase2" | "victory" | "aftermath" | "ending" | "finished";

const D = MM.disk;
/** Health attribute of the heart (kept at 1000; incoming damage is halved for a 2000-point fight). */
const HEART_MAX = 1000;
const HEART_DAMAGE = 0.5;
const NODE_SHARE = 0.1333;
const REBLOOM_AT = 0.3;
const AREA_ID = "anatomy_mm_arena";

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
  heart: Entity | undefined;
  legs: Entity[] = [];
  petals: Entity[] = [];
  private nodeEnts = new Map<string, Entity>();
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
  }

  // ------------------------------------------------------------------ BossEncounter
  status(): string {
    const hp = this.heartHp();
    return `${this.def.id}: state=${this.state} phase=${this.phase} nodes=${3 - this.nodeDead.size}/3 heart=${hp.toFixed(0)}/${HEART_MAX} layout=${this.layout} writer=${this.writer.pending} tasks=${this.tasks.count()}`;
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
      for (const [id, e] of this.nodeEnts) if (!this.nodeDead.has(id) && e.isValid) this.destroyNode(id, e, true);
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
      try {
        const feet = this.dim.getBlock(s.pos);
        const head = this.dim.getBlock({ x: s.pos.x, y: s.pos.y + 1, z: s.pos.z });
        if ((feet?.isAir ?? true) && (head?.isAir ?? true)) return s;
      } catch {
        return s;
      }
    }
    const f = first!;
    return { pos: { x: f.pos.x, y: f.pos.y + 3, z: f.pos.z }, facing: f.facing };
  }

  // ------------------------------------------------------------------ MMContext
  livingNodes(): LivingNode[] {
    const out: LivingNode[] = [];
    for (const site of this.m.nodes) {
      const e = this.nodeEnts.get(site.id);
      if (e && e.isValid && !this.nodeDead.has(site.id) && !this.nodeDying.has(site.id)) out.push({ site, entity: e });
    }
    return out;
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
    if (this.state !== "phase2" || !this.heart?.isValid) return;
    this.exposedUntil = this.now + ticks;
    this.director.lastExposure = this.now;
    this.heart.setProperty(PROP.open, true);
    sound(this.dim, SND.heartOpen, this.heartCentre(), 1, 1);
    title(this.audience(), "", "§a◆ The Lithic Heart is EXPOSED — strike it now!", 40, 4, 10);
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

  // ------------------------------------------------------------------ setup
  private *setup(saved?: SavedEncounter): Co {
    this.state = "loading";
    if (!saved) title(this.party, "§7The ground beneath you begins to migrate…", "", 40, 10, 10);
    const b = arenaBounds();
    let loaded: boolean | undefined;
    loadArea(AREA_ID, this.dim, b.from, b.to).then(
      (ok) => (loaded = ok),
      () => (loaded = false),
    );
    for (let i = 0; i < 600 && loaded === undefined; i++) yield 2;
    if (!loaded) console.warn("[anatomy] arena ticking area not confirmed; continuing (chunks may load as players arrive)");
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
    yield* clearArena(this.dim);
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
        this.welcome(p);
      });
      yield 20;
      this.cinematic(true);
    }
    // the mountain surfaces from the cloud sea
    this.spawnLegs();
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
    this.spawnHeart(saved);
    this.spawnNodes(saved);
    if (saved && saved.phase === 2) {
      this.layout = Number(saved.data.layout ?? 0);
      this.rebloomed = Boolean(saved.data.rebloomed);
      const all = sectorColumns(1, 0)[0];
      for (let i = 0; i < all.length; i += 400) {
        cutColumns(this.dim, this.writer, all.slice(i, i + 400));
        yield 1;
      }
      while (this.writer.pending > 0) yield 1;
      placeDisk(this.dim, this.writer, this.layout, 0);
      for (let k = 0; k < PETALS; k++) {
        const e = spawnPetal(this, k, 1);
        if (e) this.petals.push(e);
      }
      for (const e of this.legs) if (e.isValid) e.setProperty(PROP.pose, 1);
      this.terrain.enabled = false;
      for (let i = 0; i < 80 && this.writer.pending > 0; i++) yield 1;
      const inside = this.audience();
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
        title(this.audience(), "§f001 · §lTHE MIGRATING MOUNTAIN", "§7The Mountain That Never Belonged to the Earth", 80, 10, 30);
        yield 70;
        this.cinematic(false);
        title(this.audience(), "§aPHASE 1", "§2THE SLEEPING CONTINENT §7— find and destroy the 3 Resonance Nodes", 70, 10, 20);
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
    }
  }

  private killLeftovers(): void {
    try {
      for (const e of this.dim.getEntities()) if (e.typeId.startsWith("anatomy:mm_") || e.hasTag(TAG)) e.remove();
    } catch {
      /* ignore */
    }
  }

  private spawnLegs(): void {
    this.legs = [];
    for (const site of this.m.legs) {
      try {
        const e = this.dim.spawnEntity(ENT.leg, site.pos, { initialRotation: site.yaw });
        e.setProperty(PROP.legIndex, site.index);
        e.setProperty(PROP.pose, this.phase === 2 ? 1 : 0);
        e.addTag(TAG);
        this.legs.push(e);
      } catch (err) {
        console.warn(`[anatomy] leg ${site.index} spawn failed: ${String(err)}`);
      }
    }
  }

  private spawnHeart(saved?: SavedEncounter): void {
    try {
      const e = this.dim.spawnEntity(ENT.heart, MM.heart, { initialRotation: 0 });
      e.addTag(TAG);
      e.setProperty(PROP.phase, 1);
      this.heart = e;
      const hp = saved ? Number(saved.data.heartHp ?? HEART_MAX) : HEART_MAX;
      e.getComponent("minecraft:health")?.setCurrentValue(Math.max(1, Math.min(HEART_MAX, hp)));
    } catch (err) {
      console.warn(`[anatomy] heart spawn failed: ${String(err)}`);
    }
  }

  private spawnNodes(saved?: SavedEncounter): void {
    const dead = new Set<string>(((saved?.data.nodeDead as string[] | undefined) ?? []).map(String));
    for (const id of dead) this.nodeDead.add(id);
    if (saved && saved.phase === 2) return;
    for (const site of this.m.nodes) {
      if (dead.has(site.id)) continue;
      try {
        const e = this.dim.spawnEntity(ENT.node, site.pos, { initialRotation: 0 });
        e.addTag(TAG);
        if (site.id === "root") e.setProperty(PROP.hanging, true);
        this.nodeEnts.set(site.id, e);
      } catch (err) {
        console.warn(`[anatomy] node ${site.id} spawn failed: ${String(err)}`);
      }
    }
  }

  private welcome(p: Player): void {
    this.known.add(p.id);
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
  }

  private farewell(p: Player): void {
    this.known.delete(p.id);
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
      const live = this.livingNodes();
      for (const p of everyone) {
        let hint = "";
        if (live.length) {
          const n = live.reduce((a, b) => (dist3(a.entity.location, p.location) < dist3(b.entity.location, p.location) ? a : b));
          const d = Math.round(dist3(n.entity.location, p.location));
          hint = ` §8| §7nearest: §f${n.site.name} §7${d}m ${arrow(p, n.entity.location)}`;
        }
        actionbar([p], `§5◆ §dResonance Nodes destroyed §f${this.nodeDead.size}/3${hint}`);
      }
    } else if (this.state === "phase2") {
      const left = Math.max(0, this.exposedUntil - this.now);
      const zoneHint = (p: Player) => (this.zoneOf(p) === "mantle" ? " §8| §6stand on a steam vent to be thrown back up" : "");
      for (const p of everyone)
        actionbar([p], left > 0 ? `§5◆ §dLithic Heart §aEXPOSED §f${Math.ceil(left / 20)}s${zoneHint(p)}` : `§5◆ §dLithic Heart §7sealed — survive its attacks to make it open${zoneHint(p)}`);
    } else if (this.state === "aftermath") {
      const left = Math.max(0, this.aftermathEnd - this.now);
      actionbar(everyone, `§aThe mountain has settled. §7Returning home in §f${Math.ceil(left / 20)}s §8(Atlas: leave now)`);
    }
  }

  private phase1Upkeep(everyone: Player[]): void {
    const heartC = this.heartCentre();
    if (this.now % 30 === 0) {
      // the resonance network: beams from every living node into the shielded heart
      for (const n of this.livingNodes()) {
        const from = { x: n.entity.location.x, y: n.entity.location.y + (n.site.id === "root" ? 1.5 : 2), z: n.entity.location.z };
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
    if (this.heart?.isValid && this.exposedUntil > 0 && this.now >= this.exposedUntil) {
      this.exposedUntil = 0;
      this.heart.setProperty(PROP.open, false);
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
      p.sendMessage("§7The mist of the cloud sea hurls you back onto the mountain.");
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
      const site = [...this.nodeEnts.entries()].find(([, n]) => n === e)?.[0];
      if (this.state !== "phase1" || !site || this.nodeDying.has(site)) {
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
      const msg =
        this.state === "phase1"
          ? `§dThe Resonance Network shields the Lithic Heart §7(${3 - this.nodeDead.size} nodes remain)`
          : "§7The heart's iris is sealed — survive its attack and wait for it to open";
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
      return this.heart?.isValid ? (this.heart.getComponent("minecraft:health")?.currentValue ?? HEART_MAX) : HEART_MAX;
    } catch {
      return HEART_MAX;
    }
  }

  private heartCentre(): V3 {
    const y = this.heart?.isValid ? this.heart.location.y : MM.heart.y;
    return { x: MM.heart.x, y: y + 3, z: MM.heart.z };
  }

  // ------------------------------------------------------------------ nodes & phase change
  private destroyNode(id: string, e: Entity, silent: boolean): void {
    if (this.nodeDying.has(id) || this.nodeDead.has(id)) return;
    this.nodeDying.add(id);
    const at = { x: e.location.x, y: e.location.y + 1.6, z: e.location.z };
    try {
      e.setProperty(PROP.dying, true);
    } catch {
      /* ignore */
    }
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
    const site = this.m.nodes.find((n) => n.id === id);
    this.tasks.start(`mm:node:${id}`, this.nodeDeath(id, e, site?.name ?? "Resonance Node", silent));
  }

  private *nodeDeath(id: string, e: Entity, name: string, silent: boolean): Co {
    yield 32;
    if (e.isValid) e.remove();
    this.nodeDying.delete(id);
    this.nodeDead.add(id);
    if (this.heart?.isValid) {
      const h = this.heart.getComponent("minecraft:health");
      if (h) h.setCurrentValue(Math.max(1, h.currentValue - HEART_MAX * NODE_SHARE));
    }
    this.director.aggression = 1 + this.nodeDead.size * 0.12;
    if (!silent) title(this.audience(), "", `§d${name} destroyed §f(${this.nodeDead.size}/3)`, 40, 5, 15);
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
        addPetal: (e) => this.petals.push(e),
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
    if (this.heart?.isValid) this.heart.setProperty(PROP.phase, 2);
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
        addPetal: () => undefined,
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
    if (reason !== "victory") title(players, "§7The mountain migrates on…", "", 40, 10, 20);
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
    this.killLeftovers();
    this.writer.clear();
    yield* clearArena(this.dim, 4);
    yield 40;
    this.killLeftovers();
    unloadArea(AREA_ID);
    this.finishNow();
  }

  private finishNow(): void {
    this.state = "finished";
    void this.stopReason;
    void this.lootSpot;
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
function arrow(p: Player, to: V3): string {
  const yaw = p.getRotation().y;
  const fwd = Math.atan2(-Math.sin((yaw * Math.PI) / 180), Math.cos((yaw * Math.PI) / 180));
  const dir = Math.atan2(to.x - p.location.x, to.z - p.location.z);
  const d = angleDiffDeg((dir * 180) / Math.PI, (fwd * 180) / Math.PI);
  const up = to.y - p.location.y;
  const idx = Math.round(((-d % 360) + 360) % 360 / 45) % 8;
  return `${ARROWS[idx]}${up > 6 ? " §7(above)" : up < -6 ? " §7(below)" : ""}`;
}
