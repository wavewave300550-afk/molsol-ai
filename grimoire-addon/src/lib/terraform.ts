import { Block, BlockPermutation, Dimension, Vector3, system, world } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { Scene } from "./scene";

/**
 * Temporary living ground: a spell may turn the NATURAL surface around the caster into another
 * ground (moss, podzol, basalt...) and put plants in the air above it - and everything goes back
 * exactly as it was.  The only module (with tempblocks.ts) allowed to change existing blocks.
 *
 *   * only natural surface blocks are replaced (REPLACEABLE); a column next to anything that is not
 *     natural (a player's build) is skipped; nothing with a block entity, no liquids, no falling
 *     blocks over air
 *   * every change is written to a ledger in world dynamic properties BEFORE the block changes
 *     (write-ahead), so a crash or quit mid-cast is repaired on the next world load
 *   * changes are applied in paced pulses (a band sweeping around the caster) so the client rebuilds
 *     each chunk section a few times, not every tick
 *   * a plant is never left on a ground that cannot hold it (it would break and drop an item):
 *     applying clears the natural plant first, restoring clears our plant first, puts the ground
 *     back, then the natural plant
 *   * a cell a player changed in the meantime is left alone; while the spell runs our blocks cannot
 *     be broken or blown up
 */

/** Natural surface blocks that may be replaced. */
export const REPLACEABLE = new Set([
  "minecraft:grass_block", "minecraft:dirt", "minecraft:coarse_dirt", "minecraft:podzol", "minecraft:mycelium",
  "minecraft:dirt_with_roots", "minecraft:mud", "minecraft:sand", "minecraft:red_sand", "minecraft:gravel",
  "minecraft:stone", "minecraft:andesite", "minecraft:diorite", "minecraft:granite", "minecraft:tuff", "minecraft:moss_block",
]);
/** Natural single-block plants that may sit on a replaced cell (taken away and put back). */
export const NATURAL_PLANTS = new Set([
  "minecraft:short_grass", "minecraft:fern", "minecraft:dandelion", "minecraft:poppy", "minecraft:azure_bluet",
  "minecraft:oxeye_daisy", "minecraft:cornflower", "minecraft:red_tulip", "minecraft:orange_tulip", "minecraft:white_tulip",
  "minecraft:pink_tulip", "minecraft:allium", "minecraft:lily_of_the_valley", "minecraft:blue_orchid", "minecraft:wildflowers",
  "minecraft:pink_petals", "minecraft:leaf_litter", "minecraft:moss_carpet", "minecraft:deadbush", "minecraft:bush",
]);
/** Other natural blocks a column may border (anything else next to it reads as a player's build). */
const NATURAL_OTHER = new Set([
  "minecraft:air", "minecraft:snow_layer", "minecraft:snow", "minecraft:ice", "minecraft:packed_ice", "minecraft:blue_ice",
  "minecraft:sandstone", "minecraft:red_sandstone", "minecraft:clay", "minecraft:calcite", "minecraft:dripstone_block",
  "minecraft:pointed_dripstone", "minecraft:coal_ore", "minecraft:iron_ore", "minecraft:copper_ore", "minecraft:deepslate",
  "minecraft:bedrock", "minecraft:tall_grass", "minecraft:large_fern", "minecraft:sunflower", "minecraft:lilac",
  "minecraft:rose_bush", "minecraft:peony", "minecraft:sweet_berry_bush", "minecraft:firefly_bush",
]);
const NATURAL_RE = /_leaves$|_log$|^minecraft:(water|flowing_water|lava|flowing_lava)$/;
const LIQUID_RE = /water|lava/;
const FALLING = new Set(["minecraft:sand", "minecraft:red_sand", "minecraft:gravel"]);
/** Temporary spell blocks (tempblocks.ts) that may stand for a while in a cell we emptied. */
const TEMP_RE = /^minecraft:(barrier|light_block_\d+)$/;

/** A surface column found by scan(): the ground block, what sits above it, and where it is relative to the centre. */
export interface SurfaceCell {
  x: number; y: number; z: number;
  ground: string;
  /** natural plant above the ground (undefined = air) */
  above?: string;
  dist: number;
  /** angle around the centre in degrees, 0 = +z, 90 = +x */
  ang: number;
  /** liquid within 1 block: no plant here (flowing water would break it and drop an item) */
  wet: boolean;
}
/** What to put on a surface cell: a new ground block and / or a plant above it. */
export interface GroundChange {
  ground?: string;
  states?: Record<string, string | number | boolean>;
  plant?: string;
  plantStates?: Record<string, string | number | boolean>;
}

// ---------------------------------------------------------------------------------------------- the ledger
type Entry = { d: string; x: number; y: number; z: number; o: number; p: number; owner?: GroundSet };
const KEY = "grim:gl";
const CHUNK = 30000;
const MAX_CHUNKS = 8;
const AIR = "minecraft:air";
const DIMS: Record<string, string> = { "minecraft:overworld": "o", "minecraft:nether": "n", "minecraft:the_end": "e" };
const DIM_IDS: Record<string, string> = { o: "minecraft:overworld", n: "minecraft:nether", e: "minecraft:the_end" };
const live = new Map<string, Entry>();
let palette: string[] = [];
let palIndex = new Map<string, number>();
let dirty = false;
let pulseTick = -1;
/** One pulse a tick world-wide (every cast shares it): a pulse that finds the tick taken waits for the next. */
function takePulse(): boolean {
  if (system.currentTick === pulseTick) return false;
  pulseTick = system.currentTick;
  return true;
}

const key = (d: string, x: number, y: number, z: number) => `${d}|${x}|${y}|${z}`;
const keyOf = (e: Entry) => key(e.d, e.x, e.y, e.z);
function pal(type: string, states: Record<string, unknown> = {}): number {
  const ks = Object.keys(states).sort();
  const s = `${type}|${ks.length ? JSON.stringify(Object.fromEntries(ks.map((k) => [k, states[k]]))) : ""}`;
  let i = palIndex.get(s);
  if (i === undefined) { i = palette.length; palette.push(s); palIndex.set(s, i); }
  return i;
}
function unpal(i: number): { t: string; s: Record<string, string | number | boolean> } {
  const e = palette[i] ?? `${AIR}|`;
  const bar = e.indexOf("|");
  const js = e.slice(bar + 1);
  return { t: e.slice(0, bar), s: js ? JSON.parse(js) : {} };
}
const typeOf = (i: number) => unpal(i).t;
/** Ground entries replaced a natural ground block; the others hold the cell above (a plant or air). */
const isGround = (e: Entry) => REPLACEABLE.has(typeOf(e.o));

function save(): void {
  dirty = false;
  const parts: string[] = [];
  for (const e of live.values()) parts.push(`${e.d},${e.x},${e.y},${e.z},${e.o},${e.p}`);
  const data = parts.join(";");
  if (!data) {
    for (const id of world.getDynamicPropertyIds()) if (id === KEY || id.startsWith(`${KEY}.`)) world.setDynamicProperty(id, undefined);
    palette = []; palIndex = new Map();
    return;
  }
  if (data.length > CHUNK * MAX_CHUNKS) throw new Error("ground ledger full");
  world.setDynamicProperty(KEY, JSON.stringify({ v: 2, pal: palette }));
  let i = 0;
  for (let off = 0; off < data.length; off += CHUNK, i++) world.setDynamicProperty(`${KEY}.${i}`, data.slice(off, off + CHUNK));
  for (; i < MAX_CHUNKS; i++) if (world.getDynamicProperty(`${KEY}.${i}`) !== undefined) world.setDynamicProperty(`${KEY}.${i}`, undefined);
}
/** Persist the ledger when it changed (called once per tick from main.ts). */
export function flushGround(): void {
  if (dirty) { try { save(); } catch (e) { console.warn(`[grimoire] ground ledger: ${e}`); } }
}
/** Cells held world-wide right now. */
export function groundCount(): number { return live.size; }

function blockAt(e: Entry): Block | undefined {
  try { return world.getDimension(DIM_IDS[e.d]).getBlock({ x: e.x, y: e.y, z: e.z }); } catch { return undefined; }
}
function setTo(b: Block, i: number): void {
  const { t, s } = unpal(i);
  if (Object.keys(s).length) b.setPermutation(BlockPermutation.resolve(t, s));
  else b.setType(t);
}

/**
 * Put cells back, in an order that never leaves a plant on a ground that cannot hold it:
 * 1. our plants -> air (only where the cell still holds what we placed),
 * 2. ground -> the original (where it still holds what we placed, or became air),
 * 3. the natural plants that were there before (onto natural ground only).
 * A cell holding anything else was changed by someone else and is left alone.
 * Returns the cells that could not be reached (chunk not loaded) - they are kept for a retry.
 */
function restoreEntries(list: Entry[]): Set<Entry> {
  const failed = new Set<Entry>();
  const plants = list.filter((e) => !isGround(e)), grounds = list.filter(isGround);
  for (const e of plants) {
    const b = blockAt(e);
    if (!b) { failed.add(e); continue; }
    try { if (b.typeId === typeOf(e.p) && !b.isAir) b.setType(AIR); } catch { failed.add(e); }
  }
  for (const e of grounds) {
    const b = blockAt(e);
    if (!b) { failed.add(e); continue; }
    try { const cur = b.typeId; if (cur === typeOf(e.p) || cur === AIR) setTo(b, e.o); } catch { failed.add(e); }
  }
  for (const e of plants) {
    if (failed.has(e) || typeOf(e.o) === AIR) continue;
    const b = blockAt(e);
    if (!b) { failed.add(e); continue; }
    try {
      if (TEMP_RE.test(b.typeId)) { failed.add(e); continue; }   // a spell barrier stands there for now: retry later
      const under = b.below();
      if (b.isAir && under && REPLACEABLE.has(under.typeId)) setTo(b, e.o);
    } catch { failed.add(e); }
  }
  return failed;
}

function load(): Entry[] {
  const meta = world.getDynamicProperty(KEY);
  if (typeof meta !== "string") return [];
  try {
    const m = JSON.parse(meta) as { v: number; pal: string[] };
    palette = Array.isArray(m.pal) ? m.pal : [];
  } catch { palette = []; }
  palIndex = new Map(palette.map((s, i) => [s, i]));
  let s = "";
  for (let i = 0; i < MAX_CHUNKS; i++) {
    const p = world.getDynamicProperty(`${KEY}.${i}`);
    if (typeof p === "string") s += p;
  }
  const out: Entry[] = [];
  for (const rec of s.split(";")) {
    const f = rec.split(",");
    if (f.length !== 6 || !DIM_IDS[f[0]]) continue;
    const [x, y, z, o, p] = f.slice(1).map(Number);
    if ([x, y, z, o, p].some((n) => !Number.isFinite(n))) continue;
    out.push({ d: f[0], x, y, z, o, p });
  }
  return out;
}

/** Repair ground left behind by an interrupted session (world load, cleanup command). */
export function restoreGround(): void {
  if (live.size) { retryGround(); return; }                       // this session's state is the truth
  const entries = load();
  if (!entries.length) { if (palette.length) dirty = true; return; }
  const failed = restoreEntries(entries);
  for (const e of failed) live.set(keyOf(e), e);
  dirty = true;
  if (failed.size) console.log(`[grimoire] ${failed.size} ground blocks are in unloaded chunks; they will be restored when loaded.`);
}
/** Retry cells nobody owns any more (their chunk was unloaded); every 100 ticks from main.ts. */
export function retryGround(): void {
  const orphans = [...live.values()].filter((e) => !e.owner);
  if (!orphans.length) return;
  const failed = restoreEntries(orphans);
  for (const e of orphans) if (!failed.has(e)) live.delete(keyOf(e));
  if (failed.size !== orphans.length) dirty = true;
}
/** True when a cell is held by a living-ground change (used to protect it). */
export function claimed(dimId: string, loc: Vector3): boolean {
  if (!live.size) return false;
  return live.has(key(DIMS[dimId] ?? "o", Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z)));
}

let guarded = false;
/** Our blocks cannot be broken (no item duplication, no lost originals) or blown up while a spell holds them. */
export function installGroundGuards(): void {
  if (guarded) return;
  guarded = true;
  try {
    world.beforeEvents.playerBreakBlock.subscribe((ev) => {
      if (claimed(ev.block.dimension.id, ev.block.location)) ev.cancel = true;
    });
  } catch { /* event missing */ }
  try {
    world.beforeEvents.explosion.subscribe((ev) => {
      if (!live.size) return;
      const blocks = ev.getImpactedBlocks();
      const keep = blocks.filter((b) => !claimed(b.dimension.id, b.location));
      if (keep.length !== blocks.length) ev.setImpactedBlocks(keep);
    });
  } catch { /* event missing */ }
}

// ---------------------------------------------------------------------------------------------- one cast
interface Planned { cell: SurfaceCell; change: GroundChange }

/** The living ground of one cast: scan the surface, apply it in bands, restore it (always, on scene end). */
export class GroundSet {
  private planned: Planned[] = [];
  private readonly d: string;
  /** set once scan() has finished */
  ready = false;
  private waiting: (() => void)[] = [];
  constructor(private scene: Scene) {
    this.d = DIMS[scene.dimId] ?? "o";
    scene.onEnd(() => this.restoreNow());
  }
  /** Cells (ground + plants) this set holds right now. */
  get size(): number { let n = 0; for (const e of live.values()) if (e.owner === this) n++; return n; }
  get plannedCount(): number { return this.planned.length; }
  /** The planned cells (read only), e.g. to place effects on the new ground. */
  get cells(): readonly Planned[] { return this.planned; }

  /**
   * Find the natural surface around `center` (radius in blocks) and decide what each cell becomes
   * (`choose` returns undefined to leave a cell).  Runs as a background job; `then` runs when done.
   * The plan is trimmed to the world-wide budget, inner cells first.
   */
  scan(center: Vector3, radius: number, choose: (c: SurfaceCell) => GroundChange | undefined, then?: () => void): this {
    if (then) this.waiting.push(then);
    const dim = this.scene.dim;
    const cx = Math.floor(center.x), cz = Math.floor(center.z), cy = Math.floor(center.y);
    const cols: [number, number, number][] = [];
    for (let dx = -radius; dx <= radius; dx++) {
      for (let dz = -radius; dz <= radius; dz++) {
        const d = Math.hypot(dx, dz);
        if (d <= radius) cols.push([cx + dx, cz + dz, d]);
      }
    }
    cols.sort((a, b) => a[2] - b[2]);
    const self = this;
    function* job(): Generator<void, void, void> {
      let n = 0, budget = CONFIG.limits.maxGroundBlocks - live.size;
      for (const [x, z, dist] of cols) {
        if (self.scene.ended) return;
        const c = self.surface(dim, x, z, cy, cx + 0.5, cz + 0.5, dist);
        if (c) {
          const ch = choose(c);
          const cost = ch ? (ch.ground ? 1 : 0) + (ch.plant || (ch.ground && c.above) ? 1 : 0) : 0;
          if (ch && cost && budget >= cost) { self.planned.push({ cell: c, change: ch }); budget -= cost; }
        }
        if (++n % 24 === 0) yield;
      }
      self.ready = true;
      for (const f of self.waiting.splice(0)) { try { f(); } catch (e) { console.warn(`[grimoire] ground: ${e}`); } }
    }
    try { system.runJob(job()); } catch { this.ready = true; }
    return this;
  }
  /** Run `f` once the scan has finished (immediately if it already has). */
  whenReady(f: () => void): void { if (this.ready) f(); else this.waiting.push(f); }

  private surface(dim: Dimension, x: number, z: number, cy: number, cx: number, cz: number, dist: number): SurfaceCell | undefined {
    try {
      // first non-air block going down from 6 above the caster's feet
      let y = cy + 6, top: Block | undefined;
      for (; y >= cy - 6; y--) {
        const b = dim.getBlock({ x, y, z });
        if (!b) return undefined;
        if (!b.isAir) { top = b; break; }
      }
      if (!top) return undefined;
      let ground = top, above: string | undefined;
      if (NATURAL_PLANTS.has(top.typeId)) {                       // a natural plant on the ground: taken too
        above = top.typeId;
        y -= 1;
        const g = dim.getBlock({ x, y, z });
        if (!g) return undefined;
        ground = g;
      }
      if (!REPLACEABLE.has(ground.typeId) || ground.isWaterlogged || ground.getComponent("minecraft:inventory")) return undefined;
      if (FALLING.has(ground.typeId)) {                           // sand over a cave would fall when put back
        const under = dim.getBlock({ x, y: y - 1, z });
        if (!under || under.isAir || under.isLiquid || NATURAL_PLANTS.has(under.typeId)) return undefined;
      }
      // next to a player's build (anything that is not natural)? leave the column alone
      let wet = false;
      for (const [ox, oz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        for (const oy of [0, 1]) {
          const n = dim.getBlock({ x: x + ox, y: y + oy, z: z + oz });
          if (!n) return undefined;
          const t = n.typeId;
          if (LIQUID_RE.test(t)) wet = true;
          if (REPLACEABLE.has(t) || NATURAL_PLANTS.has(t) || NATURAL_OTHER.has(t) || NATURAL_RE.test(t)) continue;
          if (claimed(dim.id, n.location)) continue;
          return undefined;
        }
      }
      return { x, y, z, ground: ground.typeId, above, dist, ang: (Math.atan2(x + 0.5 - cx, z + 0.5 - cz) * 180) / Math.PI, wet };
    } catch {
      return undefined;
    }
  }

  /** Apply every planned cell with r0 <= dist < r1, sweeping around the centre from `startAng` in paced pulses. */
  applyBand(r0: number, r1: number, opts: { perPulse?: number; every?: number; startAng?: number } = {}): void {
    this.whenReady(() => {
      const band = sweep(this.planned.filter((p) => p.cell.dist >= r0 && p.cell.dist < r1), opts.startAng ?? 0);
      this.pace(band, opts.perPulse ?? CONFIG.ground.perPulse, opts.every ?? CONFIG.ground.every, (batch) => this.applyBatch(batch));
    });
  }
  /** Put back every cell of this set with r0 <= dist < r1, sweeping round from `startAng` in paced pulses. */
  restoreBand(r0: number, r1: number, opts: { perPulse?: number; every?: number; startAng?: number } = {}): void {
    const band = sweep(this.planned.filter((p) => p.cell.dist >= r0 && p.cell.dist < r1), opts.startAng ?? 0);
    this.pace(band, opts.perPulse ?? CONFIG.ground.perPulse, opts.every ?? CONFIG.ground.every, (batch) => this.restoreBatch(batch));
  }
  /**
   * Take this set's plants off the ground within `radius` of `center` (the ground stays changed), e.g.
   * so a ring of temporary barriers can stand there; the natural plants that were there come back.
   */
  clearPlants(center: Vector3, radius: number): void {
    const cells: Entry[] = [];
    for (const { cell } of this.planned) {
      if (Math.hypot(cell.x + 0.5 - center.x, cell.z + 0.5 - center.z) > radius) continue;
      const e = live.get(key(this.d, cell.x, cell.y + 1, cell.z));
      // only our own plants: a natural plant taken off a ground that cannot hold it waits for that ground to go
      if (e && e.owner === this && typeOf(e.p) !== AIR) cells.push(e);
    }
    if (!cells.length) return;
    const failed = restoreEntries(cells);
    for (const e of cells) if (!failed.has(e)) live.delete(keyOf(e));
    dirty = true;
  }
  /** Put back everything now (scene end, caster gone): one tick. */
  restoreNow(): void {
    this.restoreBatch(this.planned);
  }

  /**
   * Split a sweep into pulses of at most `perPulse` block changes touching at most CONFIG.ground.maxSections
   * chunk sections (each one the client has to rebuild), one pulse every `every` ticks.
   */
  private pace(list: Planned[], perPulse: number, every: number, fn: (b: Planned[]) => void): void {
    const batches: Planned[][] = [];
    const maxSec = CONFIG.ground.maxSections;
    let batch: Planned[] = [], n = 0, secs = new Set<string>();
    for (const p of list) {
      const c = (p.change.ground ? 1 : 0) + (p.change.plant || p.cell.above ? 1 : 0);
      const sx = p.cell.x >> 4, sz = p.cell.z >> 4;
      const mine = [`${sx},${p.cell.y >> 4},${sz}`, `${sx},${(p.cell.y + 1) >> 4},${sz}`];
      const grown = new Set([...secs, ...mine]);
      if (batch.length && (n + c > perPulse || grown.size > maxSec)) { batches.push(batch); batch = []; n = 0; secs = new Set(mine); }
      else secs = grown;
      batch.push(p); n += c;
    }
    if (batch.length) batches.push(batch);
    const go = (b: Planned[]): void => {
      if (this.scene.ended) return;
      if (!takePulse()) { this.scene.after(1, () => go(b)); return; }
      fn(b);
    };
    batches.forEach((b, i) => { if (i === 0) go(b); else this.scene.after(i * every, () => go(b)); });
  }

  private applyBatch(batch: Planned[]): void {
    if (this.scene.ended) return;
    const dim = this.scene.dim;
    // claim and record every cell of this pulse first (write-ahead), then change the blocks
    const todo: { e: Entry; b: Block; to: number; plant: boolean }[] = [];
    let budget = CONFIG.limits.maxGroundBlocks - live.size;
    for (const { cell, change } of batch) {
      if (budget < 2) break;
      try {
        const g = dim.getBlock({ x: cell.x, y: cell.y, z: cell.z });
        const a = dim.getBlock({ x: cell.x, y: cell.y + 1, z: cell.z });
        if (!g || !a) continue;
        const gk = key(this.d, cell.x, cell.y, cell.z), ak = key(this.d, cell.x, cell.y + 1, cell.z);
        if (live.has(gk) || live.has(ak)) continue;
        const aType = a.typeId;
        if (aType !== AIR && aType !== cell.above) continue;      // something new sits there: leave the column
        if (change.ground && g.typeId !== cell.ground) continue;
        const plant = change.plant && !cell.wet ? change.plant : undefined;
        // the cell above: our plant, or air where a natural plant would be left on a ground that cannot hold it
        const upTo = plant ?? (aType !== AIR && change.ground ? AIR : undefined);
        if (upTo !== undefined) {
          const e: Entry = { d: this.d, x: cell.x, y: cell.y + 1, z: cell.z, o: pal(aType, a.permutation.getAllStates()), p: pal(upTo, plant ? change.plantStates : undefined), owner: this };
          live.set(ak, e); budget--;
          todo.push({ e, b: a, to: e.p, plant: true });
        }
        if (change.ground) {
          const e: Entry = { d: this.d, x: cell.x, y: cell.y, z: cell.z, o: pal(g.typeId, g.permutation.getAllStates()), p: pal(change.ground, change.states), owner: this };
          live.set(gk, e); budget--;
          todo.push({ e, b: g, to: e.p, plant: false });
        }
      } catch { /* unloaded: skip */ }
    }
    if (!todo.length) return;
    try { save(); } catch (err) {
      // the ledger could not be written: change nothing we could not put back after a crash
      for (const t of todo) live.delete(keyOf(t.e));
      console.warn(`[grimoire] ground ledger: ${err}`);
      return;
    }
    // natural plants come off first, then the ground changes, then our plants go on the new ground
    const order = [
      ...todo.filter((t) => t.plant && typeOf(t.to) === AIR),
      ...todo.filter((t) => !t.plant),
      ...todo.filter((t) => t.plant && typeOf(t.to) !== AIR),
    ];
    for (const t of order) {
      try { setTo(t.b, t.to); } catch { live.delete(keyOf(t.e)); dirty = true; }
    }
  }

  private restoreBatch(batch: Planned[]): void {
    const cells: Entry[] = [];
    for (const { cell } of batch) {
      for (const y of [cell.y + 1, cell.y]) {
        const e = live.get(key(this.d, cell.x, y, cell.z));
        if (e && e.owner === this) cells.push(e);
      }
    }
    if (!cells.length) return;
    const failed = restoreEntries(cells);
    for (const e of cells) {
      if (failed.has(e)) e.owner = undefined;                    // unloaded: an orphan for retryGround()
      else live.delete(keyOf(e));
    }
    dirty = true;
  }
}

/**
 * Order cells for a sweep round the centre that the client can rebuild cheaply: whole chunk columns at a
 * time (a pulse then touches one or two of them, not a thin wedge through many), the columns in order of
 * their angle from `start`, and the cells inside a column by angle too.
 */
function sweep(list: Planned[], start: number): Planned[] {
  const rel = (a: number) => ((a - start + 720) % 360);
  const groups = new Map<string, Planned[]>();
  for (const p of list) {
    const k = `${p.cell.x >> 4},${p.cell.z >> 4}`;
    let g = groups.get(k);
    if (!g) { g = []; groups.set(k, g); }
    g.push(p);
  }
  const mean = (g: Planned[]) => {
    let sx = 0, sz = 0;
    for (const p of g) { const a = (rel(p.cell.ang) * Math.PI) / 180; sx += Math.sin(a); sz += Math.cos(a); }
    return ((Math.atan2(sx, sz) * 180) / Math.PI + 360) % 360;
  };
  return [...groups.values()].map((g) => ({ g, a: mean(g) })).sort((x, y) => x.a - y.a)
    .flatMap(({ g }) => g.sort((x, y) => rel(x.cell.ang) - rel(y.cell.ang)));
}

/** The living-ground set for a scene (one per cast; restored when the scene ends, whatever happens). */
export function groundFor(scene: Scene): GroundSet {
  return new GroundSet(scene);
}
