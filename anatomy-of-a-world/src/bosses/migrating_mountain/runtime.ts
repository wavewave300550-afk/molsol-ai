/**
 * In-game access to the pre-generated mountain (tools/export_mountain.mjs) and
 * the routines that place it into the arena dimension.
 */
import { Dimension, Structure, StructureAnimationMode, StructureSaveMode, world } from "@minecraft/server";
import { BlockWriter, perm } from "../../core/blocks.js";
import { ChunkRect, chunkOf, rectLoaded, rectOf } from "../../core/chunks.js";
import { Co } from "../../core/tasks.js";
import { forEachRun, unpack } from "../../gen/codec.js";
import { ColFlag, MM, MountainModel } from "../../gen/mountain.js";
import { AIR } from "../../gen/palette.js";
import * as P from "../../gen/palette.js";
import { MM_DATA } from "./mm_data.js";

let model: MountainModel | undefined;
let bodyCols: Uint8Array | undefined;
const diskCols: (Uint8Array | undefined)[] = [];

export function mountain(): MountainModel {
  if (!model) {
    model = MountainModel.fromData({
      seed: MM_DATA.seed,
      top: unpack(MM_DATA.top),
      under: unpack(MM_DATA.under),
      caveTop: unpack(MM_DATA.caveTop),
      flags: unpack(MM_DATA.flags),
      trees: MM_DATA.trees,
      nodes: MM_DATA.nodes,
      legs: MM_DATA.legs,
      waterfalls: MM_DATA.waterfalls,
      pathPoints: MM_DATA.pathPoints,
      summit: MM_DATA.summit,
      tunnelMouth: MM_DATA.tunnelMouth,
    });
  }
  return model;
}

function body(): Uint8Array {
  if (!bodyCols) bodyCols = unpack(MM_DATA.cols);
  return bodyCols;
}

function disk(layout: number): Uint8Array {
  let d = diskCols[layout];
  if (!d) {
    d = unpack(layout ? MM_DATA.p2b : MM_DATA.p2a);
    diskCols[layout] = d;
  }
  return d;
}

/** Whole arena bounds (blocks) incl. legs reaching into the clouds. */
export function arenaBounds(): { from: { x: number; y: number; z: number }; to: { x: number; y: number; z: number } } {
  const g = MM.grid;
  return { from: { x: g.x0, y: -64, z: g.z0 }, to: { x: g.x0 + g.sx - 1, y: g.y0 + g.sy - 1, z: g.z0 + g.sz - 1 } };
}

/** Chunks of the whole arena (grid), for ticking-area planning. */
export function arenaChunks(): ChunkRect {
  const g = MM.grid;
  return { cx0: chunkOf(g.x0), cz0: chunkOf(g.z0), cx1: chunkOf(g.x0 + g.sx - 1), cz1: chunkOf(g.z0 + g.sz - 1) };
}

/**
 * Clear the arena box (time-sliced, one chunk column per fill). Chunks that are
 * not loaded are cleared as soon as they are (the writer defers those fills).
 */
export function* clearArena(writer: BlockWriter, perTick = 6): Co {
  const g = MM.grid;
  const x1 = g.x0 + g.sx - 1;
  const z1 = g.z0 + g.sz - 1;
  let n = 0;
  for (let cx = chunkOf(g.x0); cx <= chunkOf(x1); cx++)
    for (let cz = chunkOf(g.z0); cz <= chunkOf(z1); cz++) {
      writer.fill(Math.max(g.x0, cx * 16), g.y0, Math.max(g.z0, cz * 16), Math.min(x1, cx * 16 + 15), g.y0 + g.sy - 1, Math.min(z1, cz * 16 + 15), AIR);
      if (++n % perTick === 0) yield 1;
    }
  // the rim waterfall falls through the cloud sea: clear its column too
  for (const wf of mountain().waterfalls) if (wf.kind === "void") writer.fill(wf.source.x - 3, -64, wf.source.z - 3, wf.source.x + 3, g.y0 - 1, wf.source.z + 3, AIR);
}

const TILE = 48;

/**
 * Place the Phase 1 body. Tiles go in as in-memory structures placed with the
 * native layer-by-layer animation where possible; every other tile is written
 * through the (budgeted, order-keeping) writer.
 * `sliceMs` bounds the script time spent per tick.
 */
export function* placeBody(dim: Dimension, writer: BlockWriter, animateSeconds: number, sliceMs = 25): Co {
  const g = MM.grid;
  const data = body();
  const tilesX = Math.ceil(g.sx / TILE);
  const tilesZ = Math.ceil(g.sz / TILE);
  const sm = world.structureManager;
  const tileRect = (tx: number, tz: number) => {
    const x0 = g.x0 + tx * TILE;
    const z0 = g.z0 + tz * TILE;
    return { x0, z0, x1: Math.min(x0 + TILE, g.x0 + g.sx) - 1, z1: Math.min(z0 + TILE, g.z0 + g.sz) - 1 };
  };
  // A structure is only placed over chunks that are loaded and have no edits waiting: a placement the
  // engine queues for unloaded chunks would not be ordered with the writer's deferred edits.
  const placeable = (tx: number, tz: number) => {
    const r = tileRect(tx, tz);
    return !writer.hasDeferredIn(r.x0, r.z0, r.x1, r.z1) && rectLoaded(dim, rectOf(r.x0, r.z0, r.x1, r.z1));
  };
  const tiles: (Structure | undefined)[] = [];
  let warned = false;
  for (let tx = 0; tx < tilesX; tx++)
    for (let tz = 0; tz < tilesZ; tz++) {
      let st: Structure | undefined;
      if (placeable(tx, tz)) {
        const id = `anatomy:mm_body_${tx}_${tz}`;
        try {
          sm.delete(id);
        } catch {
          /* not present */
        }
        try {
          st = sm.createEmpty(id, { x: Math.min(TILE, g.sx - tx * TILE), y: g.sy, z: Math.min(TILE, g.sz - tz * TILE) }, StructureSaveMode.Memory);
        } catch (e) {
          if (!warned) console.warn(`[anatomy] structure tiles unavailable (${String(e)}), using direct block writes`);
          warned = true;
        }
      }
      tiles.push(st);
    }
  let t0 = Date.now();
  let i = 0;
  for (let cx = 0; cx < g.sx; cx++) {
    const tx = Math.floor(cx / TILE);
    for (let cz = 0; cz < g.sz; cz++) {
      const n = data[i++];
      const ti = tx * tilesZ + Math.floor(cz / TILE);
      const st = tiles[ti];
      if (!st) {
        i += n * 3;
        continue;
      }
      const lx = cx % TILE;
      const lz = cz % TILE;
      for (let r = 0; r < n; r++, i += 3) {
        const y0 = data[i];
        const len = data[i + 1];
        const p = perm(data[i + 2]);
        try {
          for (let k = 0; k < len; k++) st.setBlockPermutation({ x: lx, y: y0 + k, z: lz }, p);
        } catch (e) {
          if (!warned) console.warn(`[anatomy] structure write failed (${String(e)}), using direct block writes for that tile`);
          warned = true;
          tiles[ti] = undefined;
          i += (n - r) * 3;
          break;
        }
      }
    }
    if (Date.now() - t0 > sliceMs) {
      yield 1;
      t0 = Date.now();
    }
  }
  let k = 0;
  for (let tx = 0; tx < tilesX; tx++)
    for (let tz = 0; tz < tilesZ; tz++) {
      const st = tiles[k++];
      let placed = false;
      if (st && placeable(tx, tz)) {
        try {
          sm.place(st, dim, { x: g.x0 + tx * TILE, y: g.y0, z: g.z0 + tz * TILE }, animateSeconds > 0 ? { animationMode: StructureAnimationMode.Layers, animationSeconds: animateSeconds } : {});
          placed = true;
        } catch (e) {
          console.warn(`[anatomy] structure place failed: ${String(e)}`);
        }
      }
      if (!placed) {
        writeBodyRect(writer, tileRect(tx, tz));
        yield 1;
      }
    }
  while (writer.pending > 0) yield 1;
}

/** Queue the pristine body inside a block rectangle on the writer. */
export function writeBodyRect(writer: BlockWriter, r: { x0: number; z0: number; x1: number; z1: number }): void {
  const g = MM.grid;
  const data = body();
  const idx = columnIndex();
  for (let x = Math.max(g.x0, r.x0); x <= Math.min(g.x0 + g.sx - 1, r.x1); x++)
    for (let z = Math.max(g.z0, r.z0); z <= Math.min(g.z0 + g.sz - 1, r.z1); z++) {
      let i = idx[(x - g.x0) * g.sz + (z - g.z0)];
      const n = data[i++];
      for (let q = 0; q < n; q++, i += 3) for (let k = 0; k < data[i + 1]; k++) writer.set(x, g.y0 + data[i] + k, z, data[i + 2]);
    }
}

/** Remove everything above the Phase 2 cut for the given columns (sector peel). */
export function cutColumns(writer: BlockWriter, cols: number[]): void {
  const m = mountain();
  const g = MM.grid;
  const cut = m.phase2CutY();
  for (const c of cols) {
    const x = Math.floor(c / g.sz) + g.x0;
    const z = (c % g.sz) + g.z0;
    // everything above the cut goes (trees and decorations on lower columns included)
    writer.fill(x, cut + 1, z, x, g.y0 + g.sy - 1, z, AIR);
    if (m.top[c] > cut) for (let y = cut - 3; y <= cut; y++) writer.set(x, y, z, m.dorsalBlock(x, y, z, cut, 2));
  }
}

/** Body columns grouped into `sectors` angular sectors (for the Great Unfolding peel). */
export function sectorColumns(sectors: number, phase0Deg: number): number[][] {
  const m = mountain();
  const g = MM.grid;
  const out: number[][] = Array.from({ length: sectors }, () => []);
  for (let x = g.x0; x < g.x0 + g.sx; x++)
    for (let z = g.z0; z < g.z0 + g.sz; z++) {
      const c = m.col(x, z);
      const tall = m.top[c] > m.phase2CutY() - 30;
      if (!(m.flags[c] & ColFlag.BODY) && !tall) continue;
      let a = (Math.atan2(z - MM.heart.z, x - MM.heart.x) * 180) / Math.PI - phase0Deg;
      a = ((a % 360) + 360) % 360;
      out[Math.floor(a / (360 / sectors)) % sectors].push(c);
    }
  return out;
}

/** Write the Phase 2 disk (rib layout 0 or 1) through the writer. */
export function writeDisk(writer: BlockWriter, layout: number, filter?: (x: number, y: number, z: number) => boolean): void {
  const b = MM_DATA.p2box;
  forEachRun(disk(layout), b.sx, b.sz, (cx, cz, y0, len, v) => {
    const x = b.x0 + cx;
    const z = b.z0 + cz;
    for (let k = 0; k < len; k++) {
      const y = b.y0 + y0 + k;
      if (filter && !filter(x, y, z)) continue;
      writer.set(x, y, z, v === 255 ? AIR : v);
    }
  });
}

/**
 * Reset the disk to its pristine rib layout: ribs and gaps re-cut from D.y-3 up and everything above the
 * walkway cleared (ridges, rubble and walls that cancelled abilities left behind).
 */
export function restoreDisk(writer: BlockWriter, layout: number, clearAbove = 8): void {
  const D = MM.disk;
  // edits still queued by the cancelled abilities land first, then the clear (fills are immediate)
  writer.flushAll();
  const hx = MM.heart.x - 0.5;
  const hz = MM.heart.z - 0.5;
  const R = D.outerR + 0.5;
  for (let x = Math.ceil(hx - R); x <= Math.floor(hx + R); x++) {
    const half = Math.sqrt(Math.max(0, R * R - (x - hx) * (x - hx)));
    const z0 = Math.ceil(hz - half);
    const z1 = Math.floor(hz + half);
    if (z1 >= z0) writer.fill(x, D.y + 1, z0, x, D.y + clearAbove, z1, AIR);
  }
  writeDisk(writer, layout, (_x, y) => y >= D.y - 3);
}

/**
 * Phase 2 disk as animated structures (it rises layer by layer); falls back to the writer.
 * The disk box is split into tiles no wider than 48 blocks to stay well inside structure limits.
 */
export function placeDisk(dim: Dimension, writer: BlockWriter, layout: number, seconds: number): void {
  const b = MM_DATA.p2box;
  if (writer.hasDeferredIn(b.x0, b.z0, b.x0 + b.sx - 1, b.z0 + b.sz - 1) || !rectLoaded(dim, rectOf(b.x0, b.z0, b.x0 + b.sx - 1, b.z0 + b.sz - 1))) {
    // part of the disk is not loaded or still has edits waiting: the writer keeps the order
    writeDisk(writer, layout);
    return;
  }
  const sm = world.structureManager;
  const T = 36;
  const tx = Math.ceil(b.sx / T);
  const tz = Math.ceil(b.sz / T);
  try {
    const tiles: import("@minecraft/server").Structure[] = [];
    const covered: Uint8Array[] = [];
    for (let i = 0; i < tx; i++)
      for (let k = 0; k < tz; k++) {
        const id = `anatomy:mm_disk_${layout}_${i}_${k}`;
        try {
          sm.delete(id);
        } catch {
          /* none */
        }
        const sx = Math.min(T, b.sx - i * T);
        const sz = Math.min(T, b.sz - k * T);
        tiles.push(sm.createEmpty(id, { x: sx, y: b.sy, z: sz }, StructureSaveMode.Memory));
        covered.push(new Uint8Array(sx * sz * b.sy));
      }
    forEachRun(disk(layout), b.sx, b.sz, (cx, cz, y0, len, v) => {
      const ti = Math.floor(cx / T) * tz + Math.floor(cz / T);
      const s = tiles[ti];
      const lx = cx % T;
      const lz = cz % T;
      const sz = s.size.z;
      const p = perm(v === 255 ? AIR : v);
      for (let k = 0; k < len; k++) {
        s.setBlockPermutation({ x: lx, y: y0 + k, z: lz }, p);
        covered[ti][(lx * sz + lz) * b.sy + y0 + k] = 1;
      }
    });
    // everything outside the disk cylinder stays structure void (never overwrite the rim shelf)
    tiles.forEach((s, ti) => {
      const { x: sx, z: sz } = s.size;
      for (let lx = 0; lx < sx; lx++)
        for (let lz = 0; lz < sz; lz++)
          for (let y = 0; y < b.sy; y++) if (!covered[ti][(lx * sz + lz) * b.sy + y]) s.setBlockPermutation({ x: lx, y, z: lz }, undefined);
    });
    tiles.forEach((s, ti) => {
      const i = Math.floor(ti / tz);
      const k = ti % tz;
      sm.place(s, dim, { x: b.x0 + i * T, y: b.y0, z: b.z0 + k * T }, seconds > 0 ? { animationMode: StructureAnimationMode.Layers, animationSeconds: seconds } : {});
    });
  } catch (e) {
    console.warn(`[anatomy] disk structure failed (${String(e)}), writing directly`);
    writeDisk(writer, layout);
  }
}

/** The disk box (for player safety checks). */
export function diskBox() {
  return MM_DATA.p2box;
}

// ----------------------------------------------------------------------------- pristine block lookup
let colIndex: Int32Array | undefined;

/** Start offset of every column in the body stream. */
function columnIndex(): Int32Array {
  if (!colIndex) {
    const g = MM.grid;
    const data = body();
    colIndex = new Int32Array(g.sx * g.sz);
    let i = 0;
    for (let c = 0; c < g.sx * g.sz; c++) {
      colIndex[c] = i;
      i += 1 + data[i] * 3;
    }
  }
  return colIndex;
}

/** Palette index of the pristine Phase 1 body at a world position (AIR when empty). */
export function pristineBlock(x: number, y: number, z: number): number {
  const g = MM.grid;
  const cx = x - g.x0;
  const cz = z - g.z0;
  const cy = y - g.y0;
  if (cx < 0 || cz < 0 || cy < 0 || cx >= g.sx || cz >= g.sz || cy >= g.sy) return AIR;
  const data = body();
  let i = columnIndex()[cx * g.sz + cz];
  const n = data[i++];
  for (let r = 0; r < n; r++, i += 3) {
    const y0 = data[i];
    if (cy >= y0 && cy < y0 + data[i + 1]) return data[i + 2];
  }
  return AIR;
}

/** Write the pristine body for a set of columns (used when restoring after a resume). */
export function writeColumns(writer: BlockWriter, filter: (x: number, z: number) => boolean): void {
  const g = MM.grid;
  forEachRun(body(), g.sx, g.sz, (cx, cz, y0, len, b) => {
    const x = g.x0 + cx;
    const z = g.z0 + cz;
    if (!filter(x, z)) return;
    for (let k = 0; k < len; k++) writer.set(x, g.y0 + y0 + k, z, b);
  });
}

// ----------------------------------------------------------------------------- Phase 3B: floating islands
/** A floating island of the shattered disk (Phase 3B). Island 0 is the centre, under the heart. */
export interface Island {
  i: number;
  cx: number;
  cz: number;
  r: number;
  /** y of the walkable top layer */
  top: number;
}

/**
 * The centre island (radius 8) under the heart and a ring of eight (radius 5) at 16 blocks: gaps of
 * about 2 blocks between ring islands and 3 to the centre, neighbours differ by at most one block.
 */
export function islandLayout(): Island[] {
  const D = MM.disk;
  const out: Island[] = [{ i: 0, cx: MM.heart.x, cz: MM.heart.z, r: 8, top: D.y }];
  const rise = [0, 1, 1, 0, -1, 0, 1, 0];
  for (let k = 0; k < 8; k++) {
    const a = ((22.5 + 45 * k) * Math.PI) / 180;
    out.push({ i: k + 1, cx: MM.heart.x + Math.cos(a) * 16, cz: MM.heart.z + Math.sin(a) * 16, r: 5, top: D.y + rise[k] });
  }
  return out;
}

export function islandAt(x: number, z: number, islands: Island[] = islandLayout()): Island | undefined {
  return islands.find((s) => Math.hypot(x - s.cx, z - s.cz) <= s.r + 0.5);
}

/** Columns of an island as [x, z, depth] (an inverted cone: deep in the middle, thin at the rim). */
export function islandColumns(s: Island): [number, number, number][] {
  const out: [number, number, number][] = [];
  for (let x = Math.floor(s.cx - s.r); x <= Math.ceil(s.cx + s.r); x++)
    for (let z = Math.floor(s.cz - s.r); z <= Math.ceil(s.cz + s.r); z++) {
      const d = Math.hypot(x + 0.5 - s.cx, z + 0.5 - s.cz);
      if (d > s.r) continue;
      out.push([x, z, Math.max(2, Math.round((1 - (d / s.r) ** 2) * 8))]);
    }
  return out;
}

/** Queue an island's blocks (optionally only the columns `filter` accepts). */
export function writeIsland(writer: BlockWriter, s: Island, filter?: (x: number, z: number) => boolean): void {
  const m = mountain();
  for (const [x, z, depth] of islandColumns(s)) {
    if (filter && !filter(x, z)) continue;
    for (let y = s.top - depth + 1; y <= s.top; y++) {
      let v = m.strata(x, y, z);
      if (y === s.top) v = (x * 7 + z * 13) % 9 === 0 ? P.MOSSY_COBBLE : P.MOSS;
      else if (y === s.top - depth + 1 && (x + z) % 3 === 0) v = P.MUSCLE;
      writer.set(x, y, z, v);
    }
  }
}

/** Remove an island's blocks (optionally only the columns `filter` accepts). */
export function clearIsland(writer: BlockWriter, s: Island, filter?: (x: number, z: number) => boolean): void {
  for (const [x, z, depth] of islandColumns(s)) {
    if (filter && !filter(x, z)) continue;
    writer.fill(x, s.top - depth - 1, z, x, s.top + 2, z, AIR);
  }
}

/**
 * The disk breaks apart: a cylinder through the whole body around the heart is emptied (down to the
 * underside, so a fall goes to the cloud sea) and the islands are written. Time-sliced.
 */
export function* shatterDisk(writer: BlockWriter): Co {
  const D = MM.disk;
  const R = D.outerR + 2;
  const y0 = MM.baseY - 2;
  const y1 = D.y + 8;
  let n = 0;
  for (let x = Math.floor(MM.heart.x - R); x <= Math.ceil(MM.heart.x + R); x++) {
    const dx = x + 0.5 - MM.heart.x;
    const h = Math.sqrt(Math.max(0, R * R - dx * dx));
    if (h <= 0) continue;
    writer.fill(x, y0, Math.floor(MM.heart.z - h), x, y1, Math.ceil(MM.heart.z + h), AIR);
    if (++n % 6 === 0) yield 1;
  }
  for (const s of islandLayout()) {
    writeIsland(writer, s);
    yield 1;
  }
}
