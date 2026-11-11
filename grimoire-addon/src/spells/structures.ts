import type { Cast } from "./context";
import type { TempBlockSet } from "../core/blocks";
import type { Routine } from "../core/tasks";
import { V3, rng } from "../core/vec";

/** Wall columns (x,z) of a randomized maze on an N x N grid of cells (cell walls are 1 block). */
export function mazeColumns(origin: V3, cells: number, cell: number, seed: number, entrances = 2): Map<string, V3> {
  const r = rng(seed);
  const n = cells;
  // passages[x][z] bit flags: 1=east open, 2=south open
  const open = new Map<string, boolean>();
  const seen = new Set<string>();
  const key = (x: number, z: number) => `${x},${z}`;
  const stack: [number, number][] = [[Math.floor(r() * n), Math.floor(r() * n)]];
  seen.add(key(...stack[0]));
  while (stack.length) {
    const [x, z] = stack[stack.length - 1];
    const nb = ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const)
      .map(([dx, dz]) => [x + dx, z + dz] as [number, number])
      .filter(([a, b]) => a >= 0 && b >= 0 && a < n && b < n && !seen.has(key(a, b)));
    if (!nb.length) {
      stack.pop();
      continue;
    }
    const [nx, nz] = nb[Math.floor(r() * nb.length)];
    open.set(`${Math.min(x, nx)},${Math.min(z, nz)},${nx !== x ? "e" : "s"}`, true);
    seen.add(key(nx, nz));
    stack.push([nx, nz]);
  }
  // a few extra openings so the maze has loops (more tactical paths)
  for (let i = 0; i < n; i++) {
    const x = Math.floor(r() * (n - 1)), z = Math.floor(r() * n);
    open.set(`${x},${z},e`, true);
  }
  const cols = new Map<string, V3>();
  const size = n * cell;
  const add = (lx: number, lz: number) => {
    const p = { x: Math.floor(origin.x - size / 2 + lx), y: origin.y, z: Math.floor(origin.z - size / 2 + lz) };
    cols.set(`${p.x},${p.z}`, p);
  };
  for (let i = 0; i <= n; i++) {
    for (let j = 0; j <= n; j++) {
      add(i * cell, j * cell); // nodes
      // horizontal wall (along x) between (i, j-1) and (i, j) for cell i
      if (i < n && !(j > 0 && j < n && open.get(`${i},${j - 1},s`))) for (let k = 1; k < cell; k++) add(i * cell + k, j * cell);
      // vertical wall (along z) between (i-1, j) and (i, j) for cell j
      if (j < n && !(i > 0 && i < n && open.get(`${i - 1},${j},e`))) for (let k = 1; k < cell; k++) add(i * cell, j * cell + k);
    }
  }
  // entrances on opposite sides
  const ent = [Math.floor(r() * n), Math.floor(r() * n)];
  for (let k = 1; k < cell; k++) {
    cols.delete(`${Math.floor(origin.x - size / 2 + ent[0] * cell + k)},${Math.floor(origin.z - size / 2)}`);
    if (entrances > 1) cols.delete(`${Math.floor(origin.x - size / 2 + ent[1] * cell + k)},${Math.floor(origin.z + size / 2)}`);
  }
  return cols;
}

/** Ground height for each column (top of the first solid block below, searched from above). */
export function grounded(c: Cast, cols: Iterable<V3>, probeUp = 4): V3[] {
  const out: V3[] = [];
  for (const p of cols) {
    const g = c.ground({ x: p.x + 0.5, y: p.y + probeUp, z: p.z + 0.5 }, probeUp + 8);
    out.push({ x: p.x, y: Math.floor(g.y), z: p.z });
  }
  return out;
}

/** Raise walls layer by layer (construction animation), only into air. */
export function* raise(set: TempBlockSet, cols: V3[], height: number, blockId: string, perTick = 60, layerDelay = 2): Routine {
  for (let h = 0; h < height; h++) {
    let n = 0;
    for (const p of cols) {
      set.place({ x: p.x, y: p.y + h, z: p.z }, blockId);
      if (++n % perTick === 0) yield 1;
    }
    yield layerDelay;
  }
}

/** Lower walls top-down (dissolution). */
export function* lower(set: TempBlockSet, perTick = 80): Routine {
  const all = set.positions().sort((a, b) => b.y - a.y);
  let n = 0;
  for (const p of all) {
    set.remove(p);
    if (++n % perTick === 0) yield 1;
  }
}

export function columnKey(p: V3): string {
  return `${p.x},${p.z}`;
}
