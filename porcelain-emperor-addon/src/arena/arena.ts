/**
 * Runtime side of the Fractured Mandate: builds the palace in the custom
 * dimension, keeps its chunks loaded during a fight, and changes it as the
 * Emperor breaks (cracks spread, pillars shed their tops, the court splits
 * into islands, temporary holes and gilded tiles) and mends it with gold
 * when the Emperor falls.
 */
import { BlockPermutation, BlockVolume, Dimension, system, Vector3, world } from "@minecraft/server";
import { ARENA, BLOCK, DIM_ID, FX, SND } from "../config.js";
import { crackDecal, particle, sound } from "../core/fx.js";
import { spawnTask, wait } from "../core/tasks.js";
import { clamp, v } from "../core/vec.js";
import { Blueprint, buildBlueprint, Fill, key, PILLAR_TOP, unkey } from "./blueprint.js";

const TICKING_ID = "porcelain:mandate_arena";

const permCache = new Map<string, BlockPermutation>();
export function perm(id: string, states?: Record<string, boolean | number | string>): BlockPermutation {
  const k = states ? `${id}|${JSON.stringify(states)}` : id;
  let p = permCache.get(k);
  if (!p) {
    p = BlockPermutation.resolve(id, states);
    permCache.set(k, p);
  }
  return p;
}

type CellState = "floor" | "hole" | "gap" | "gilded";

export class Arena {
  readonly bp: Blueprint;
  readonly dim: Dimension;
  readonly origin: Vector3;
  readonly cells = new Map<number, CellState>();
  private restores = new Map<number, { at: number; block: string }>();
  fractured = false;
  cracked = false;

  constructor() {
    this.bp = buildBlueprint();
    this.dim = world.getDimension(DIM_ID);
    let fy: number = ARENA.preferredFloorY;
    try {
      const hr = this.dim.heightRange;
      fy = clamp(fy, hr.min - this.bp.bottom + 4, hr.max - 40);
    } catch {
      // keep the preferred height
    }
    this.origin = v(0, Math.floor(fy), 0);
  }

  /** World position of an arena-local block coordinate. */
  w(x: number, y: number, z: number): Vector3 {
    return { x: this.origin.x + x, y: this.origin.y + y, z: this.origin.z + z };
  }

  /** Centre of the block a player stands on top of (local floor cell -> world feet position). */
  standAt(x: number, z: number): Vector3 {
    return { x: this.origin.x + x + 0.5, y: this.origin.y + 1, z: this.origin.z + z + 0.5 };
  }

  get floorY(): number {
    return this.origin.y + 1;
  }

  get center(): Vector3 {
    return { x: this.origin.x + 0.5, y: this.origin.y + 1, z: this.origin.z + 0.5 };
  }

  local(p: Vector3): { x: number; z: number } {
    return { x: Math.floor(p.x - this.origin.x), z: Math.floor(p.z - this.origin.z) };
  }

  /** Is there walkable court under this world position (by the arena's own bookkeeping)? */
  hasFloor(p: Vector3): boolean {
    const l = this.local(p);
    const st = this.cells.get(key(l.x, l.z));
    return st === "floor" || st === "gilded";
  }

  isInside(p: Vector3, margin = 0): boolean {
    return Math.hypot(p.x - this.center.x, p.z - this.center.z) <= ARENA.radius + margin;
  }

  // ------------------------------------------------------------------ chunks

  async load(): Promise<boolean> {
    const mgr = world.tickingAreaManager;
    const half = ARENA.tickingHalf;
    const opts = {
      dimension: this.dim,
      from: this.w(-half, this.bp.bottom - 2, -half),
      to: this.w(half, PILLAR_TOP + 8, half),
    };
    try {
      if (mgr.hasTickingArea(TICKING_ID)) return true;
      if (!mgr.hasCapacity(opts)) {
        const small = { ...opts, from: this.w(-30, this.bp.bottom - 2, -30), to: this.w(30, PILLAR_TOP + 8, 30) };
        await mgr.createTickingArea(TICKING_ID, small);
      } else {
        await mgr.createTickingArea(TICKING_ID, opts);
      }
      return true;
    } catch (e) {
      console.warn(`[porcelain] could not create the arena ticking area: ${e}`);
      return false;
    }
  }

  unload(): void {
    try {
      const mgr = world.tickingAreaManager;
      if (mgr.hasTickingArea(TICKING_ID)) mgr.removeTickingArea(TICKING_ID);
    } catch {
      // ignore
    }
  }

  // ------------------------------------------------------------------ building

  private fill(f: Fill): void {
    try {
      this.dim.fillBlocks(new BlockVolume(this.w(f.a.x, f.a.y, f.a.z), this.w(f.b.x, f.b.y, f.b.z)), perm(f.block, f.states),
        { ignoreChunkBoundErrors: true });
    } catch (e) {
      console.warn(`[porcelain] fill failed at ${JSON.stringify(f.a)}: ${e}`);
    }
  }

  setLocal(x: number, y: number, z: number, block: string, states?: Record<string, boolean | number | string>): void {
    try {
      this.dim.setBlockPermutation(this.w(x, y, z), perm(block, states));
    } catch {
      // unloaded chunk: cosmetic
    }
  }

  /** Build (or restore) the whole palace. Idempotent: every block of the blueprint is rewritten. */
  build(): Promise<void> {
    this.fractured = false;
    this.cracked = false;
    this.restores.clear();
    for (const k of this.bp.floor) this.cells.set(k, "floor");
    const self = this;
    return new Promise((resolve) => {
      function* job(): Generator<void, void, void> {
        // clear what a previous fight may have left above the floor and in the chasms
        for (let y = 1; y <= PILLAR_TOP + 2; y += 4) {
          self.fill({ a: { x: -30, y, z: -30 }, b: { x: 30, y: Math.min(y + 3, PILLAR_TOP + 2), z: 30 }, block: BLOCK.air });
          yield;
        }
        let n = 0;
        for (const f of self.bp.fills) {
          self.fill(f);
          if (++n % 24 === 0) yield;
        }
        for (const l of self.bp.lanterns) self.setLocal(l.x, l.y, l.z, BLOCK.lantern, { hanging: true });
        resolve();
      }
      system.runJob(job());
    });
  }

  // ------------------------------------------------------------------ phase 2: the court cracks

  crackCourt(): void {
    if (this.cracked) return;
    this.cracked = true;
    const near: number[] = [];
    const faults = this.bp.faults;
    for (const k of this.bp.floor) {
      if (faults.has(k) || this.bp.minorSeams.has(k)) continue;
      const b = this.bp.floorBlock.get(k);
      if (b !== BLOCK.tile && b !== BLOCK.marble) continue;
      const { x, z } = unkey(k);
      let close = false;
      for (let dx = -2; dx <= 2 && !close; dx++) for (let dz = -2; dz <= 2 && !close; dz++) if (faults.has(key(x + dx, z + dz))) close = true;
      if (close && (x * 7 + z * 13) % 5 !== 0) near.push(k);
    }
    near.sort((a, b) => {
      const pa = unkey(a);
      const pb = unkey(b);
      return Math.hypot(pa.x, pa.z) - Math.hypot(pb.x, pb.z);
    });
    const self = this;
    spawnTask("arena:crack", (function* () {
      let i = 0;
      while (i < near.length) {
        for (let n = 0; n < 18 && i < near.length; n++, i++) {
          const k = near[i];
          if (self.cells.get(k) !== "floor") continue;
          const { x, z } = unkey(k);
          self.setLocal(x, 0, z, BLOCK.cracked);
          if (n % 6 === 0) crackDecal(self.dim, self.standAt(x, z), 2.2, 6);
        }
        if (i % 72 < 18) sound(self.dim, SND.crack, self.center, 1.2, 0.8 + Math.random() * 0.3);
        yield;
      }
    })());
    // two pillars shed their crowns
    for (const idx of [1, 5]) this.breakPillar(idx, 10);
  }

  /** Remove a pillar above `fromY`; returns world positions of the biggest pieces (for floating rubble). */
  breakPillar(index: number, fromY: number): Vector3[] {
    const p = this.bp.pillars[index];
    if (!p) return [];
    const pieces: Vector3[] = [];
    this.fill({ a: { x: p.x - 2, y: fromY, z: p.z - 2 }, b: { x: p.x + 2, y: PILLAR_TOP, z: p.z + 2 }, block: BLOCK.air });
    for (let y = fromY; y <= PILLAR_TOP; y += 4) {
      const at = this.w(p.x + 0.5, y, p.z + 0.5);
      pieces.push(at);
      particle(this.dim, FX.dust, at);
      particle(this.dim, FX.chipBurst, at);
    }
    sound(this.dim, SND.crack, this.w(p.x, fromY, p.z), 1.5, 0.7);
    return pieces;
  }

  // ------------------------------------------------------------------ phase 3: the Mandate fractures

  /** Gold light runs along the fault lines (warning), then they open into chasms. */
  fracture(warnTicks: number, onOpened?: () => void): void {
    if (this.fractured) return;
    const self = this;
    const faultList = [...this.bp.faults];
    const gaps = [...this.bp.gaps].sort((a, b) => {
      const pa = unkey(a);
      const pb = unkey(b);
      return Math.hypot(pa.x, pa.z) - Math.hypot(pb.x, pb.z);
    });
    spawnTask("arena:fracture", (function* () {
      for (let t = 0; t < warnTicks; t++) {
        for (let n = 0; n < 6; n++) {
          const { x, z } = unkey(faultList[Math.floor(Math.random() * faultList.length)]);
          particle(self.dim, FX.goldMote, self.standAt(x, z));
        }
        if (t % 10 === 0) sound(self.dim, SND.crack, self.center, 1.5, 0.6 + t / warnTicks);
        yield;
      }
      self.fractured = true;
      sound(self.dim, SND.shatter, self.center, 2.0, 0.6);
      let i = 0;
      while (i < gaps.length) {
        for (let n = 0; n < 14 && i < gaps.length; n++, i++) {
          const k = gaps[i];
          const { x, z } = unkey(k);
          self.cells.set(k, "gap");
          self.restores.delete(k);
          self.fill({ a: { x, y: self.bp.bottom, z }, b: { x, y: 0, z }, block: BLOCK.air });
          if (n % 4 === 0) {
            particle(self.dim, FX.dust, self.standAt(x, z));
            particle(self.dim, FX.chipBurst, self.w(x + 0.5, 0.5, z + 0.5));
          }
        }
        yield;
      }
      for (const p of self.bp.pillars) self.breakPillar(p.index, 7);
      // the imperial screen splits down the middle
      self.fill({ a: { x: -1, y: 1, z: -27 }, b: { x: 1, y: 14, z: -27 }, block: BLOCK.air });
      sound(self.dim, SND.crack, self.w(0, 6, -27), 1.6, 0.5);
      onOpened?.();
    })());
  }

  // ------------------------------------------------------------------ temporary changes

  /** Knock a hole in the court (rubble torn out, dive craters). Refilled with cracked tile later. */
  punchHole(x: number, z: number, ticks: number): boolean {
    const k = key(x, z);
    const st = this.cells.get(k);
    if (st !== "floor" && st !== "gilded") return false;
    const orig = this.bp.floorBlock.get(k) ?? BLOCK.marble;
    this.cells.set(k, "hole");
    this.setLocal(x, 0, z, BLOCK.air);
    this.setLocal(x, -1, z, BLOCK.air);
    this.restores.set(k, { at: system.currentTick + ticks, block: orig === BLOCK.seam ? BLOCK.seam : BLOCK.cracked });
    return true;
  }

  /** Coat a tile in molten gold (the Gilded Breath). Gilded tiles slow whoever stands on them. */
  gild(x: number, z: number, ticks: number): void {
    const k = key(x, z);
    if (this.cells.get(k) !== "floor") return;
    this.cells.set(k, "gilded");
    this.setLocal(x, 0, z, BLOCK.gilded);
    const orig = this.bp.floorBlock.get(k) ?? BLOCK.marble;
    this.restores.set(k, { at: system.currentTick + ticks, block: this.cracked && orig !== BLOCK.seam && orig !== BLOCK.sealTile ? BLOCK.cracked : orig });
  }

  isGilded(p: Vector3): boolean {
    const l = this.local(p);
    return this.cells.get(key(l.x, l.z)) === "gilded";
  }

  tick(): void {
    if (!this.restores.size) return;
    const now = system.currentTick;
    for (const [k, r] of this.restores) {
      if (r.at > now) continue;
      this.restores.delete(k);
      if (this.cells.get(k) === "gap") continue;
      const { x, z } = unkey(k);
      this.setLocal(x, -1, z, BLOCK.marble);
      this.setLocal(x, 0, z, r.block);
      this.cells.set(k, "floor");
      particle(this.dim, FX.goldMote, this.standAt(x, z));
    }
  }

  // ------------------------------------------------------------------ safety

  /** Nearest standing spot on intact court (used to catch players falling into the void). */
  safeSpot(near: Vector3): Vector3 {
    let best: Vector3 | undefined;
    let bestD = Infinity;
    const candidates = this.fractured ? this.bp.islands.map((i) => i.safe) : [ARENA.arrival, ...this.bp.islands.map((i) => i.safe)];
    for (const c of candidates) {
      const st = this.cells.get(key(c.x, c.z));
      if (st !== "floor" && st !== "gilded") continue;
      const p = this.standAt(c.x, c.z);
      const d = Math.hypot(p.x - near.x, p.z - near.z);
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }
    return best ?? this.standAt(0, 0);
  }

  /** A random walkable floor cell (local coords), optionally away from a point. */
  randomFloorCell(avoid?: Vector3, minDist = 0): { x: number; z: number } | undefined {
    const keys = [...this.bp.floor];
    for (let tries = 0; tries < 40; tries++) {
      const k = keys[Math.floor(Math.random() * keys.length)];
      if (this.cells.get(k) !== "floor") continue;
      const c = unkey(k);
      const d = Math.hypot(c.x, c.z);
      if (d < 5 || d > 23) continue;
      if (this.bp.faults.has(k)) continue;
      if (avoid && Math.hypot(this.origin.x + c.x - avoid.x, this.origin.z + c.z - avoid.z) < minDist) continue;
      return c;
    }
    return undefined;
  }

  // ------------------------------------------------------------------ victory: kintsugi

  mend(): void {
    const self = this;
    const gaps = [...this.bp.gaps].sort((a, b) => {
      const pa = unkey(a);
      const pb = unkey(b);
      return Math.hypot(pa.x, pa.z) - Math.hypot(pb.x, pb.z);
    });
    spawnTask("arena:mend", (function* () {
      yield* wait(10);
      let i = 0;
      let pitch = 0.7;
      while (i < gaps.length) {
        for (let n = 0; n < 10 && i < gaps.length; n++, i++) {
          const k = gaps[i];
          const { x, z } = unkey(k);
          self.setLocal(x, -1, z, BLOCK.marble);
          self.setLocal(x, 0, z, BLOCK.seam);
          self.cells.set(k, "floor");
          if (n % 3 === 0) particle(self.dim, FX.goldMote, self.standAt(x, z));
        }
        if (i % 40 < 10) {
          sound(self.dim, SND.chime, self.center, 0.8, pitch);
          pitch = Math.min(1.6, pitch + 0.04);
        }
        yield;
      }
      // every hole and gilded tile heals; cracked tiles keep a seam of gold
      for (const [k] of self.restores) {
        const { x, z } = unkey(k);
        self.setLocal(x, -1, z, BLOCK.marble);
        self.setLocal(x, 0, z, BLOCK.seam);
        self.cells.set(k, "floor");
      }
      self.restores.clear();
      // the pillars rise again, banded with gold where they broke
      for (const f of self.bp.fills) {
        if (f.a.y >= 3 && f.a.y <= PILLAR_TOP && self.bp.pillars.some((p) => Math.abs(f.a.x - p.x) <= 2 && Math.abs(f.a.z - p.z) <= 2)) {
          self.fill(f);
        }
      }
      for (const p of self.bp.pillars) {
        for (const y of [7, 10]) {
          self.fill({ a: { x: p.x - 1, y, z: p.z }, b: { x: p.x + 1, y, z: p.z }, block: BLOCK.seam });
          self.fill({ a: { x: p.x, y, z: p.z - 1 }, b: { x: p.x, y, z: p.z + 1 }, block: BLOCK.seam });
        }
      }
      for (const l of self.bp.lanterns) self.setLocal(l.x, l.y, l.z, BLOCK.lantern, { hanging: true });
      for (const f of self.bp.screen) if (Math.abs(f.a.x) <= 1) self.fill({ ...f, block: f.block === BLOCK.marble ? BLOCK.seam : f.block });
      self.fractured = false;
      sound(self.dim, SND.chimeLow, self.center, 1.5, 1.0);
    })());
  }
}

let current: Arena | undefined;
export function arena(): Arena {
  if (!current) current = new Arena();
  return current;
}
