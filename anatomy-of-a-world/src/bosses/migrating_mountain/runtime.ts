/**
 * In-game access to the pre-generated mountain (tools/export_mountain.mjs) and
 * the routines that place it into the arena dimension.
 */
import { Dimension, StructureAnimationMode, StructureSaveMode, world } from "@minecraft/server";
import { BlockWriter, fillBox, perm } from "../../core/blocks.js";
import { Co } from "../../core/tasks.js";
import { forEachRun, unpack } from "../../gen/codec.js";
import { ColFlag, MM, MountainModel } from "../../gen/mountain.js";
import { AIR } from "../../gen/palette.js";
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

/** Clear the arena box (time-sliced). */
export function* clearArena(dim: Dimension, perTick = 6): Co {
  const g = MM.grid;
  let n = 0;
  for (let x = g.x0; x < g.x0 + g.sx; x += 16)
    for (let z = g.z0; z < g.z0 + g.sz; z += 16) {
      fillBox(dim, x, g.y0, z, Math.min(x + 15, g.x0 + g.sx - 1), g.y0 + g.sy - 1, Math.min(z + 15, g.z0 + g.sz - 1), AIR);
      if (++n % perTick === 0) yield 1;
    }
  // the rim waterfall falls through the cloud sea: clear its column too
  for (const wf of mountain().waterfalls) if (wf.kind === "void") fillBox(dim, wf.source.x - 3, -64, wf.source.z - 3, wf.source.x + 3, g.y0 - 1, wf.source.z + 3, AIR);
}

const TILE = 48;

/**
 * Place the Phase 1 body. Tries in-memory structures placed with the native
 * layer-by-layer animation; falls back to direct budgeted writes.
 * `sliceMs` bounds the script time spent per tick.
 */
export function* placeBody(dim: Dimension, writer: BlockWriter, animateSeconds: number, sliceMs = 25, only?: (cx: number, cz: number) => boolean): Co {
  const g = MM.grid;
  const data = body();
  const tilesX = Math.ceil(g.sx / TILE);
  const tilesZ = Math.ceil(g.sz / TILE);
  const sm = world.structureManager;
  const tiles: (import("@minecraft/server").Structure | undefined)[] = [];
  let useStructures = true;
  try {
    for (let tx = 0; tx < tilesX; tx++)
      for (let tz = 0; tz < tilesZ; tz++) {
        const id = `anatomy:mm_body_${tx}_${tz}`;
        try {
          sm.delete(id);
        } catch {
          /* not present */
        }
        tiles.push(sm.createEmpty(id, { x: Math.min(TILE, g.sx - tx * TILE), y: g.sy, z: Math.min(TILE, g.sz - tz * TILE) }, StructureSaveMode.Memory));
      }
  } catch (e) {
    console.warn(`[anatomy] structure tiles unavailable (${String(e)}), using direct block writes`);
    useStructures = false;
  }
  let t0 = Date.now();
  let i = 0;
  for (let cx = 0; cx < g.sx; cx++) {
    for (let cz = 0; cz < g.sz; cz++) {
      const n = data[i++];
      const skip = only ? !only(cx, cz) : false;
      for (let r = 0; r < n; r++) {
        const y0 = data[i];
        const len = data[i + 1];
        const b = data[i + 2];
        i += 3;
        if (skip) continue;
        if (useStructures) {
          const s = tiles[Math.floor(cx / TILE) * tilesZ + Math.floor(cz / TILE)]!;
          const p = perm(b);
          const lx = cx % TILE;
          const lz = cz % TILE;
          try {
            for (let k = 0; k < len; k++) s.setBlockPermutation({ x: lx, y: y0 + k, z: lz }, p);
          } catch (e) {
            console.warn(`[anatomy] structure write failed (${String(e)}), switching to direct writes`);
            useStructures = false;
          }
        }
        if (!useStructures) for (let k = 0; k < len; k++) writer.set(g.x0 + cx, g.y0 + y0 + k, g.z0 + cz, b);
      }
    }
    if (Date.now() - t0 > sliceMs) {
      yield 1;
      t0 = Date.now();
    }
  }
  if (useStructures) {
    let k = 0;
    for (let tx = 0; tx < tilesX; tx++)
      for (let tz = 0; tz < tilesZ; tz++) {
        const s = tiles[k++]!;
        try {
          sm.place(s, dim, { x: g.x0 + tx * TILE, y: g.y0, z: g.z0 + tz * TILE }, animateSeconds > 0 ? { animationMode: StructureAnimationMode.Layers, animationSeconds: animateSeconds } : {});
        } catch (e) {
          console.warn(`[anatomy] structure place failed: ${String(e)}`);
        }
      }
  }
  while (writer.pending > 0) yield 1;
}

/** Remove everything above the Phase 2 cut for the given columns (sector peel). */
export function cutColumns(dim: Dimension, writer: BlockWriter, cols: number[]): void {
  const m = mountain();
  const g = MM.grid;
  const cut = m.phase2CutY();
  for (const c of cols) {
    const x = Math.floor(c / g.sz) + g.x0;
    const z = (c % g.sz) + g.z0;
    if (m.top[c] > cut) {
      fillBox(dim, x, cut + 1, z, x, g.y0 + g.sy - 1, z, AIR);
      for (let y = cut - 3; y <= cut; y++) writer.set(x, y, z, m.dorsalBlock(x, y, z, cut, 2));
    } else {
      // trees and decorations on lower columns that reach above the cut
      fillBox(dim, x, cut + 1, z, x, g.y0 + g.sy - 1, z, AIR);
    }
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

/** Phase 2 disk as an animated structure (rises layer by layer); falls back to the writer. */
export function placeDisk(dim: Dimension, writer: BlockWriter, layout: number, seconds: number): void {
  const b = MM_DATA.p2box;
  const sm = world.structureManager;
  const id = `anatomy:mm_disk_${layout}`;
  try {
    try {
      sm.delete(id);
    } catch {
      /* none */
    }
    const s = sm.createEmpty(id, { x: b.sx, y: b.sy, z: b.sz }, StructureSaveMode.Memory);
    const covered = new Uint8Array(b.sx * b.sz * b.sy);
    forEachRun(disk(layout), b.sx, b.sz, (cx, cz, y0, len, v) => {
      const p = perm(v === 255 ? AIR : v);
      for (let k = 0; k < len; k++) {
        s.setBlockPermutation({ x: cx, y: y0 + k, z: cz }, p);
        covered[(cx * b.sz + cz) * b.sy + y0 + k] = 1;
      }
    });
    // everything outside the disk cylinder must stay structure void (never overwrite the rim shelf)
    for (let cx = 0; cx < b.sx; cx++)
      for (let cz = 0; cz < b.sz; cz++)
        for (let y = 0; y < b.sy; y++) if (!covered[(cx * b.sz + cz) * b.sy + y]) s.setBlockPermutation({ x: cx, y, z: cz }, undefined);
    sm.place(s, dim, { x: b.x0, y: b.y0, z: b.z0 }, seconds > 0 ? { animationMode: StructureAnimationMode.Layers, animationSeconds: seconds } : {});
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

/** Palette index of the pristine Phase 1 body at a world position (AIR when empty). */
export function pristineBlock(x: number, y: number, z: number): number {
  const g = MM.grid;
  const cx = x - g.x0;
  const cz = z - g.z0;
  const cy = y - g.y0;
  if (cx < 0 || cz < 0 || cy < 0 || cx >= g.sx || cz >= g.sz || cy >= g.sy) return AIR;
  const data = body();
  if (!colIndex) {
    colIndex = new Int32Array(g.sx * g.sz);
    let i = 0;
    for (let c = 0; c < g.sx * g.sz; c++) {
      colIndex[c] = i;
      i += 1 + data[i] * 3;
    }
  }
  let i = colIndex[cx * g.sz + cz];
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
