/**
 * The Fractured Mandate - procedural blueprint of the palace arena.
 *
 * Pure data (no Minecraft calls) so it can be unit-tested and previewed.
 * Coordinates are relative to the arena centre; y = 0 is the floor layer and
 * players stand at y = 1.
 *
 * The floor is a porcelain plate already mended with gold: six jagged fault
 * lines run from a ring around the central dais to the rim. They are inlaid
 * gold seams while the Emperor is whole; when the Emperor fractures (phase 3)
 * the same seams open into chasms and the court splits into seven floating
 * islands. When the Emperor dies the chasms are filled with gold (kintsugi).
 */
import { BLOCK } from "../config.js";
import { clamp, rng } from "../core/vec.js";

export type V3 = { x: number; y: number; z: number };
export type States = Record<string, boolean | number | string>;
export interface Fill {
  a: V3;
  b: V3;
  block: string;
  states?: States;
}
export interface Island {
  id: number;
  cells: number[];
  safe: { x: number; z: number };
}
export interface Pillar {
  index: number;
  x: number;
  z: number;
}
export interface Blueprint {
  fills: Fill[];
  lanterns: V3[];
  floor: Set<number>;
  floorBlock: Map<number, string>;
  faults: Set<number>;
  gaps: Set<number>;
  minorSeams: Set<number>;
  islands: Island[];
  islandOf: Map<number, number>;
  pillars: Pillar[];
  screen: Fill[];
  bottom: number;
  blockCount: number;
}

export const R = 26;
export const PILLAR_R = 21;
export const PILLAR_TOP = 17;
export const UNDERSIDE_LAYERS = 11;

export const key = (x: number, z: number): number => (x + 128) * 256 + (z + 128);
export const unkey = (k: number): { x: number; z: number } => ({ x: Math.floor(k / 256) - 128, z: (k % 256) - 128 });

const dOf = (x: number, z: number): number => Math.hypot(x, z);

function connect4(out: Set<number>, from: { x: number; z: number }, to: { x: number; z: number }): void {
  let x = from.x;
  let z = from.z;
  out.add(key(x, z));
  while (x !== to.x || z !== to.z) {
    if (x !== to.x) {
      x += Math.sign(to.x - x);
      out.add(key(x, z));
    }
    if (z !== to.z) {
      z += Math.sign(to.z - z);
      out.add(key(x, z));
    }
  }
}

function boxFill(fills: Fill[], a: V3, b: V3, block: string, states?: States): void {
  fills.push({
    a: { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), z: Math.min(a.z, b.z) },
    b: { x: Math.max(a.x, b.x), y: Math.max(a.y, b.y), z: Math.max(a.z, b.z) },
    block,
    states,
  });
}

/** Run-length encode one horizontal layer (cell -> block) into row fills. */
function layerFills(fills: Fill[], y: number, cells: Map<number, string>): void {
  const rows = new Map<number, { x: number; b: string }[]>();
  for (const [k, b] of cells) {
    const { x, z } = unkey(k);
    if (!rows.has(z)) rows.set(z, []);
    rows.get(z)!.push({ x, b });
  }
  for (const [z, row] of [...rows.entries()].sort((p, q) => p[0] - q[0])) {
    row.sort((p, q) => p.x - q.x);
    let start = row[0];
    let prev = row[0];
    for (let i = 1; i <= row.length; i++) {
      const cur = row[i];
      if (!cur || cur.b !== start.b || cur.x !== prev.x + 1) {
        boxFill(fills, { x: start.x, y, z }, { x: prev.x, y, z }, start.b);
        if (cur) start = cur;
      }
      if (cur) prev = cur;
    }
  }
}

export function buildBlueprint(seed = 1101): Blueprint {
  const rand = rng(seed);
  const fills: Fill[] = [];
  const lanterns: V3[] = [];

  // ------------------------------------------------------------------ floor cells
  const floor = new Set<number>();
  for (let x = -R; x <= R; x++) for (let z = -R; z <= R; z++) if (dOf(x, z) <= R + 0.3) floor.add(key(x, z));

  // ------------------------------------------------------------------ fault lines
  const faults = new Set<number>();
  const gaps = new Set<number>();
  for (const k of floor) {
    const { x, z } = unkey(k);
    const d = dOf(x, z);
    if (d > 3.2 && d <= 4.4) faults.add(k);
    if (d > 3.2 && d <= 5.0) gaps.add(k);
  }
  const minorSeams = new Set<number>();
  for (let r = 0; r < 6; r++) {
    const base = (r * 60 * Math.PI) / 180 + (rand() - 0.5) * 0.25;
    const cs = Math.cos(base);
    const sn = Math.sin(base);
    // perpendicular unit step used to widen the chasm to two blocks
    const px = Math.abs(sn) > Math.abs(cs) ? -Math.sign(sn) : 0;
    const pz = Math.abs(sn) > Math.abs(cs) ? 0 : Math.sign(cs);
    let wob = 0;
    let prev = { x: Math.round(cs * 4), z: Math.round(sn * 4) };
    const ray = new Set<number>();
    for (let rr = 4.5; rr <= R + 1.5; rr += 0.5) {
      wob = clamp(wob + (rand() - 0.5) * 0.9, -2.6, 2.6);
      const cur = { x: Math.round(cs * rr - sn * wob), z: Math.round(sn * rr + cs * wob) };
      connect4(ray, prev, cur);
      prev = cur;
    }
    for (const k of ray) {
      if (!floor.has(k)) continue;
      faults.add(k);
      gaps.add(k);
      const { x, z } = unkey(k);
      const w = key(x + px, z + pz);
      if (floor.has(w)) gaps.add(w);
    }
    // decorative kintsugi branches that never open
    const rayCells = [...ray].filter((k) => floor.has(k));
    for (let b = 0; b < 3; b++) {
      let { x, z } = unkey(rayCells[Math.floor(rand() * rayCells.length)]);
      let ang = base + (rand() < 0.5 ? 1 : -1) * (0.7 + rand() * 0.5);
      const steps = 3 + Math.floor(rand() * 5);
      for (let s = 0; s < steps; s++) {
        ang += (rand() - 0.5) * 0.6;
        x += Math.round(Math.cos(ang));
        z += Math.round(Math.sin(ang));
        const k = key(x, z);
        if (floor.has(k) && !gaps.has(k) && dOf(x, z) < R - 3.2) minorSeams.add(k);
      }
    }
  }

  // ------------------------------------------------------------------ islands (after the chasms open)
  const islandOf = new Map<number, number>();
  const islands: Island[] = [];
  for (const k of floor) {
    if (gaps.has(k) || islandOf.has(k)) continue;
    const id = islands.length;
    const cells: number[] = [];
    const stack = [k];
    islandOf.set(k, id);
    while (stack.length) {
      const c = stack.pop()!;
      cells.push(c);
      const { x, z } = unkey(c);
      for (const n of [key(x + 1, z), key(x - 1, z), key(x, z + 1), key(x, z - 1)]) {
        if (floor.has(n) && !gaps.has(n) && !islandOf.has(n)) {
          islandOf.set(n, id);
          stack.push(n);
        }
      }
    }
    islands.push({ id, cells, safe: { x: 0, z: 0 } });
  }
  // slivers fall away with the chasms
  for (const isl of islands) {
    if (isl.cells.length < 8) for (const c of isl.cells) gaps.add(c);
  }
  const kept = islands.filter((i) => i.cells.length >= 8);
  islandOf.clear();
  kept.forEach((isl, idx) => {
    isl.id = idx;
    for (const c of isl.cells) islandOf.set(c, idx);
    let sx = 0;
    let sz = 0;
    for (const c of isl.cells) {
      const p = unkey(c);
      sx += p.x;
      sz += p.z;
    }
    const cx = sx / isl.cells.length;
    const cz = sz / isl.cells.length;
    let best = isl.cells[0];
    let bestD = Infinity;
    for (const c of isl.cells) {
      const p = unkey(c);
      const interior = [key(p.x + 1, p.z), key(p.x - 1, p.z), key(p.x, p.z + 1), key(p.x, p.z - 1)].every((n) => islandOf.get(n) === idx);
      const d = Math.hypot(p.x - cx, p.z - cz) + (interior ? 0 : 100);
      if (d < bestD) {
        bestD = d;
        best = c;
      }
    }
    isl.safe = unkey(best);
  });

  // ------------------------------------------------------------------ floor layer (y = 0)
  const floorBlock = new Map<number, string>();
  for (const k of floor) {
    const { x, z } = unkey(k);
    const d = dOf(x, z);
    let b: string;
    if (d <= 1.6) b = BLOCK.sealTile;
    else if (faults.has(k) || minorSeams.has(k)) b = BLOCK.seam;
    else if (d >= R - 2.0) {
      const sector = Math.floor(((Math.atan2(z, x) + Math.PI) / (2 * Math.PI)) * 52);
      b = sector % 4 === 0 && d >= R - 1.2 ? BLOCK.seam : BLOCK.lacquer;
    } else if (d >= R - 3.0) b = BLOCK.seam;
    else b = ((Math.floor(x / 3) + Math.floor(z / 3)) & 1) === 0 ? BLOCK.tile : BLOCK.marble;
    floorBlock.set(k, b);
  }

  // ------------------------------------------------------------------ underside: an inverted porcelain bowl
  {
    const base = new Map<number, string>();
    for (const k of floor) base.set(k, BLOCK.marble);
    layerFills(fills, -1, base);
    for (let layer = 2; layer <= UNDERSIDE_LAYERS + 1; layer++) {
      const rOut = R - 2.3 * (layer - 1);
      const rIn = R - 2.3 * layer;
      const cells = new Map<number, string>();
      for (const k of floor) {
        const { x, z } = unkey(k);
        const d = dOf(x, z);
        if (d <= rOut && (d > rIn || layer === UNDERSIDE_LAYERS + 1)) {
          cells.set(k, layer % 3 === 0 && d > rOut - 1.2 ? BLOCK.seam : BLOCK.marble);
        }
      }
      if (cells.size) layerFills(fills, -layer, cells);
    }
    const tip = -(UNDERSIDE_LAYERS + 1);
    boxFill(fills, { x: 0, y: tip - 4, z: 0 }, { x: 0, y: tip - 1, z: 0 }, BLOCK.seam);
    boxFill(fills, { x: 0, y: tip - 5, z: 0 }, { x: 0, y: tip - 5, z: 0 }, BLOCK.sealTile);
  }
  layerFills(fills, 0, floorBlock);

  // ------------------------------------------------------------------ pillars of the court
  const pillars: Pillar[] = [];
  for (let i = 0; i < 8; i++) {
    const a = ((22.5 + i * 45) * Math.PI) / 180;
    const px = Math.round(Math.cos(a) * PILLAR_R);
    const pz = Math.round(Math.sin(a) * PILLAR_R);
    pillars.push({ index: i, x: px, z: pz });
    boxFill(fills, { x: px - 2, y: 1, z: pz - 2 }, { x: px + 2, y: 1, z: pz + 2 }, BLOCK.marble);
    boxFill(fills, { x: px - 1, y: 2, z: pz - 1 }, { x: px + 1, y: 2, z: pz + 1 }, BLOCK.marble);
    for (let y = 3; y <= 13; y++) {
      const band = y === 6 || y === 10;
      const blk = band ? BLOCK.seam : BLOCK.lacquer;
      boxFill(fills, { x: px - 1, y, z: pz }, { x: px + 1, y, z: pz }, blk);
      boxFill(fills, { x: px, y, z: pz - 1 }, { x: px, y, z: pz + 1 }, blk);
    }
    boxFill(fills, { x: px - 1, y: 14, z: pz - 1 }, { x: px + 1, y: 14, z: pz + 1 }, BLOCK.marble);
    boxFill(fills, { x: px - 2, y: 15, z: pz - 2 }, { x: px + 2, y: 15, z: pz + 2 }, BLOCK.roof);
    for (const [cx, cz] of [[-2, -2], [2, -2], [-2, 2], [2, 2]]) {
      boxFill(fills, { x: px + cx, y: 16, z: pz + cz }, { x: px + cx, y: 16, z: pz + cz }, BLOCK.roof);
      lanterns.push({ x: px + Math.sign(cx), y: 13, z: pz + Math.sign(cz) });
    }
    boxFill(fills, { x: px, y: 16, z: pz }, { x: px, y: 16, z: pz }, BLOCK.roof);
    boxFill(fills, { x: px, y: PILLAR_TOP, z: pz }, { x: px, y: PILLAR_TOP, z: pz }, BLOCK.sealTile);
  }

  // ------------------------------------------------------------------ throne dais and the imperial screen (north, -Z)
  boxFill(fills, { x: -6, y: 1, z: -25 }, { x: 6, y: 1, z: -19 }, BLOCK.marble);
  boxFill(fills, { x: -5, y: 2, z: -25 }, { x: 5, y: 2, z: -21 }, BLOCK.tile);
  boxFill(fills, { x: -4, y: 3, z: -25 }, { x: 4, y: 3, z: -22 }, BLOCK.seam);
  boxFill(fills, { x: -1, y: 4, z: -24 }, { x: 1, y: 4, z: -23 }, BLOCK.lacquer);
  boxFill(fills, { x: -2, y: 4, z: -25 }, { x: 2, y: 8, z: -25 }, BLOCK.marble);
  boxFill(fills, { x: -2, y: 4, z: -24 }, { x: -2, y: 5, z: -23 }, BLOCK.seam);
  boxFill(fills, { x: 2, y: 4, z: -24 }, { x: 2, y: 5, z: -23 }, BLOCK.seam);
  boxFill(fills, { x: 0, y: 9, z: -25 }, { x: 0, y: 9, z: -25 }, BLOCK.sealTile);
  const screen: Fill[] = [];
  for (let x = -9; x <= 9; x++) {
    const top = 13 - Math.round(Math.abs(x) * 0.35);
    for (let y = 1; y <= top; y++) {
      const wave = Math.round(6 + Math.sin(x * 0.55) * 3);
      let b: string = BLOCK.marble;
      if (y === wave || y === top) b = BLOCK.seam;
      if (Math.abs(x) >= 8) b = BLOCK.lacquer;
      if (y >= top - 3 && y < top && Math.abs(x) <= 1) b = BLOCK.sealTile;
      screen.push({ a: { x, y, z: -27 }, b: { x, y, z: -27 }, block: b });
    }
  }
  fills.push(...screen);

  // ------------------------------------------------------------------ moon gate (south, +Z): the way in and out
  for (let x = -6; x <= 6; x++) {
    for (let y = 1; y <= 11; y++) {
      const d = Math.hypot(x, y - 5.5);
      let b: string | undefined;
      if (d >= 3.6 && d <= 5.3) b = BLOCK.lacquer;
      else if (d > 3.1 && d < 3.6) b = BLOCK.seam;
      if (b) boxFill(fills, { x, y, z: 24 }, { x, y, z: 25 }, b);
    }
  }
  lanterns.push({ x: -2, y: 8, z: 24 }, { x: 2, y: 8, z: 24 });

  // ------------------------------------------------------------------ floating ruins of the palace roof
  for (let i = 0; i < 4; i++) {
    const a = ((45 + i * 90) * Math.PI) / 180;
    const cx = Math.round(Math.cos(a) * 33);
    const cz = Math.round(Math.sin(a) * 33);
    const h = 13 + (i % 2) * 3;
    boxFill(fills, { x: cx - 2, y: h, z: cz - 1 }, { x: cx + 2, y: h, z: cz }, BLOCK.roof);
    boxFill(fills, { x: cx - 2, y: h - 1, z: cz + 1 }, { x: cx + 2, y: h - 1, z: cz + 2 }, BLOCK.roof);
    boxFill(fills, { x: cx - 2, y: h - 1, z: cz - 1 }, { x: cx + 2, y: h - 1, z: cz - 1 }, BLOCK.lacquer);
    boxFill(fills, { x: cx, y: h + 1, z: cz - 1 }, { x: cx, y: h + 1, z: cz }, BLOCK.seam);
    lanterns.push({ x: cx - 2, y: h - 2, z: cz - 1 }, { x: cx + 2, y: h - 2, z: cz - 1 });
  }

  let blockCount = lanterns.length;
  for (const f of fills) blockCount += (f.b.x - f.a.x + 1) * (f.b.y - f.a.y + 1) * (f.b.z - f.a.z + 1);
  const bottom = -(UNDERSIDE_LAYERS + 1) - 5;
  return { fills, lanterns, floor, floorBlock, faults, gaps, minorSeams, islands: kept, islandOf, pillars, screen, bottom, blockCount };
}
