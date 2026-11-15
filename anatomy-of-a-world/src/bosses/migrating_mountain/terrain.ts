/**
 * Living strata: the dorsal surface of the Migrating Mountain as a deformable
 * height field. Abilities add deformation fields (folds, peristaltic waves,
 * peeled scars, inverted strips); every tick the affected columns are diffed
 * against what is currently in the world and only changed blocks are written.
 * Trees uproot when the ground under them moves and regrow once it settles,
 * and players are lifted when the strata rise beneath their feet.
 */
import { Dimension, Player } from "@minecraft/server";
import { BlockWriter } from "../../core/blocks.js";
import { particle } from "../../core/fx.js";
import { hash3 } from "../../gen/noise.js";
import { ColFlag, MM, MountainModel, treeBlocks, TreeInfo } from "../../gen/mountain.js";
import * as P from "../../gen/palette.js";
import { PX } from "./ids.js";

const TREE_BLOCKS = new Set<number>([P.SPRUCE_LOG, P.SPRUCE_LEAVES, P.OAK_LOG, P.OAK_LEAVES, P.AZALEA_LEAVES]);

export interface Field {
  /** Column bounds (inclusive) currently influenced. */
  x0: number;
  z0: number;
  x1: number;
  z1: number;
  /** Height delta at a column (0 outside). */
  dh(x: number, z: number): number;
  /** Exposed musculature instead of strata on the columns it lowers. */
  scar?: boolean;
  /** Set to true to remove the field (columns settle back next tick). */
  dead?: boolean;
}

export interface Lift {
  player: Player;
  rise: number;
}

interface TreeState {
  t: TreeInfo;
  up: boolean;
  quietSince: number;
  cols: number[];
}

export class DorsalTerrain {
  readonly g = MM.grid;
  readonly cur: Int16Array;
  private readonly scarred: Uint8Array;
  private readonly stamp: Uint32Array;
  private stampId = 1;
  private fields: Field[] = [];
  /** Bounds of fields removed since the last tick (must be re-evaluated once). */
  private settle: { x0: number; z0: number; x1: number; z1: number }[] = [];
  private trees: TreeState[] = [];
  private colTrees = new Map<number, number[]>();
  private tickNo = 0;
  enabled = true;

  constructor(
    readonly m: MountainModel,
    readonly dim: Dimension,
    readonly writer: BlockWriter,
    /** Pristine body lookup: settled columns are restored exactly (moss, plants, cliff detail). */
    private readonly pristine?: (x: number, y: number, z: number) => number,
  ) {
    this.cur = new Int16Array(m.top);
    this.scarred = new Uint8Array(m.top.length);
    this.stamp = new Uint32Array(m.top.length);
    m.trees.forEach((t, i) => {
      const r = t.kind === 0 ? 3 : 2;
      const cols: number[] = [];
      for (let x = t.x - r; x <= t.x + r; x++) for (let z = t.z - r; z <= t.z + r; z++) if (m.inCols(x, z)) cols.push(m.col(x, z));
      this.trees.push({ t, up: false, quietSince: 0, cols });
      for (const c of cols) {
        const l = this.colTrees.get(c);
        if (l) l.push(i);
        else this.colTrees.set(c, [i]);
      }
    });
  }

  add<T extends Field>(f: T): T {
    this.fields.push(f);
    return f;
  }

  remove(f: Field): void {
    f.dead = true;
  }

  get activeCount(): number {
    return this.fields.length;
  }

  /** Top block y currently rendered for a world column (or -32768 outside). */
  topAt(x: number, z: number): number {
    return this.m.inCols(x, z) ? this.cur[this.m.col(x, z)] : -32768;
  }

  isDeformable(x: number, z: number): boolean {
    if (!this.m.inCols(x, z)) return false;
    const fl = this.m.flags[this.m.col(x, z)];
    return (fl & ColFlag.BODY) !== 0 && (fl & (ColFlag.STATIC | ColFlag.WATER | ColFlag.NODE)) === 0;
  }

  /** Remove all fields and render everything back to the base shape (budgeted). */
  resetAll(): void {
    for (const f of this.fields) {
      f.dead = true;
      this.settle.push({ x0: f.x0, z0: f.z0, x1: f.x1, z1: f.z1 });
    }
    this.fields = [];
  }

  /** Advance one tick; returns players lifted by rising strata. */
  tick(players: Player[]): Lift[] {
    this.tickNo++;
    if (!this.enabled) return [];
    const m = this.m;
    const id = ++this.stampId;
    const list: number[] = [];
    const visit = (b: { x0: number; z0: number; x1: number; z1: number }) => {
      const x0 = Math.max(this.g.x0, b.x0);
      const x1 = Math.min(this.g.x0 + this.g.sx - 1, b.x1);
      const z0 = Math.max(this.g.z0, b.z0);
      const z1 = Math.min(this.g.z0 + this.g.sz - 1, b.z1);
      for (let x = x0; x <= x1; x++)
        for (let z = z0; z <= z1; z++) {
          const c = m.col(x, z);
          if (this.stamp[c] === id) continue;
          this.stamp[c] = id;
          list.push(c);
        }
    };
    const live: Field[] = [];
    for (const f of this.fields) {
      if (f.dead) this.settle.push({ x0: f.x0, z0: f.z0, x1: f.x1, z1: f.z1 });
      else live.push(f);
    }
    this.fields = live;
    for (const f of live) visit(f);
    for (const b of this.settle) visit(b);
    this.settle = [];
    if (!list.length) {
      this.regrowTrees();
      return [];
    }

    // 1) targets
    const tgt = new Map<number, number>();
    const scarNow = new Map<number, boolean>();
    for (const c of list) {
      const fl = m.flags[c];
      const base = m.top[c];
      if (!(fl & ColFlag.BODY)) continue;
      const x = Math.floor(c / this.g.sz) + this.g.x0;
      const z = (c % this.g.sz) + this.g.z0;
      let t = base;
      let sc = false;
      if (!(fl & (ColFlag.STATIC | ColFlag.WATER | ColFlag.NODE))) {
        let d = 0;
        for (const f of live) {
          if (x < f.x0 || x > f.x1 || z < f.z0 || z > f.z1) continue;
          const v = f.dh(x, z);
          if (v !== 0) {
            d += v;
            if (f.scar && v < 0) sc = true;
          }
        }
        t = base + Math.round(d);
        const ct = m.caveTop[c];
        if (ct > -32768 && t < ct + 3) t = Math.max(Math.min(base, ct + 3), t);
        if (t > this.g.y0 + this.g.sy - 3) t = this.g.y0 + this.g.sy - 3;
        if (t < m.under[c] + 1) t = m.under[c] + 1;
      }
      tgt.set(c, t);
      scarNow.set(c, sc);
    }

    // 2) trees whose ground moves are uprooted
    for (const [c, t] of tgt) {
      if (t === m.top[c] && !scarNow.get(c)) continue;
      const ts = this.colTrees.get(c);
      if (!ts) continue;
      for (const i of ts) this.uproot(i);
    }

    // 3) render changed columns
    const lifted = new Map<number, number>();
    for (const [c, t] of tgt) {
      const old = this.cur[c];
      const sc = scarNow.get(c) ?? false;
      const scarChanged = (this.scarred[c] === 1) !== sc;
      if (t === old && !scarChanged) continue;
      const x = Math.floor(c / this.g.sz) + this.g.x0;
      const z = (c % this.g.sz) + this.g.z0;
      const drop = this.dropAt(x, z, tgt);
      const lo = Math.min(old, t) - 3;
      const hi = Math.max(old, t) + 1;
      const settled = t === m.top[c] && !sc && this.pristine;
      for (let y = lo; y <= hi; y++) {
        let b: number;
        if (settled) {
          b = this.pristine!(x, y, z);
          if (TREE_BLOCKS.has(b)) b = P.AIR; // trees come back through regrowth
        } else if (y > t) b = P.AIR;
        else if (sc) b = this.scarBlock(x, y, z, t);
        else b = m.dorsalBlock(x, y, z, t, drop);
        this.writer.set(x, y, z, b);
      }
      this.cur[c] = t;
      this.scarred[c] = sc ? 1 : 0;
      if (t > old) lifted.set(c, t);
    }

    // 4) players standing in rising strata are carried up
    const out: Lift[] = [];
    if (lifted.size) {
      for (const p of players) {
        const x = Math.floor(p.location.x);
        const z = Math.floor(p.location.z);
        if (!m.inCols(x, z)) continue;
        const c = m.col(x, z);
        const t = lifted.get(c);
        if (t === undefined) continue;
        const feet = Math.floor(p.location.y);
        if (feet <= t && feet >= t - 6) {
          try {
            p.teleport({ x: p.location.x, y: t + 1.02, z: p.location.z }, { keepVelocity: true });
          } catch {
            /* ignore */
          }
          out.push({ player: p, rise: t + 1 - p.location.y });
        }
      }
    }
    this.regrowTrees();
    return out;
  }

  private dropAt(x: number, z: number, tgt: Map<number, number>): number {
    const m = this.m;
    const topOf = (a: number, b: number) => {
      if (!m.inCols(a, b)) return -32768;
      const c = m.col(a, b);
      if (!(m.flags[c] & ColFlag.BODY)) return -32768;
      return tgt.get(c) ?? this.cur[c];
    };
    return m.dropAt(x, z, topOf);
  }

  private scarBlock(x: number, y: number, z: number, top: number): number {
    const d = top - y;
    const h = hash3(x, y, z, 515);
    if (d === 0) return h < 0.12 ? P.VEIN_GLOW : h < 0.2 ? P.VEIN_HOT : h < 0.6 ? P.FLESH : P.MUSCLE;
    if (d <= 2) return h < 0.5 ? P.MUSCLE : P.MANTLE_ROCK;
    return this.m.strata(x, y, z);
  }

  private uproot(i: number): void {
    const s = this.trees[i];
    s.quietSince = this.tickNo;
    if (s.up) return;
    s.up = true;
    for (const b of treeBlocks(s.t)) {
      if (b.y > this.topAt(b.x, b.z)) this.writer.set(b.x, b.y, b.z, P.AIR);
    }
    particle(this.dim, PX.leaf, { x: s.t.x + 0.5, y: s.t.groundY + s.t.height - 1, z: s.t.z + 0.5 });
  }

  private regrowTrees(): void {
    if (this.tickNo % 20 !== 0) return;
    for (const s of this.trees) {
      if (!s.up) continue;
      const settled = s.cols.every((c) => this.cur[c] === this.m.top[c] && this.scarred[c] === 0);
      if (!settled) {
        s.quietSince = this.tickNo;
        continue;
      }
      if (this.tickNo - s.quietSince < 140) continue;
      s.up = false;
      for (const b of treeBlocks(s.t)) if (b.y > this.m.topAt(b.x, b.z)) this.writer.set(b.x, b.y, b.z, b.b);
    }
  }
}

// ----------------------------------------------------------------------------- field factories
/** A ridge rising along a segment (Continental Fold). `amp` is animated by the ability. */
export function foldField(ax: number, az: number, bx: number, bz: number, halfWidth: number): Field & { amp: number } {
  const pad = Math.ceil(halfWidth) + 1;
  const f = {
    amp: 0,
    x0: Math.floor(Math.min(ax, bx)) - pad,
    x1: Math.ceil(Math.max(ax, bx)) + pad,
    z0: Math.floor(Math.min(az, bz)) - pad,
    z1: Math.ceil(Math.max(az, bz)) + pad,
    dh(x: number, z: number): number {
      if (f.amp === 0) return 0;
      const dx = bx - ax;
      const dz = bz - az;
      const l2 = dx * dx + dz * dz || 1;
      let t = ((x + 0.5 - ax) * dx + (z + 0.5 - az) * dz) / l2;
      const endFade = t < 0 || t > 1 ? 0 : Math.min(1, Math.min(t, 1 - t) * 6);
      t = Math.max(0, Math.min(1, t));
      const qx = ax + dx * t - (x + 0.5);
      const qz = az + dz * t - (z + 0.5);
      const d = Math.sqrt(qx * qx + qz * qz);
      if (d >= halfWidth) return 0;
      const k = 1 - d / halfWidth;
      return f.amp * Math.pow(k, 1.25) * endFade;
    },
  };
  return f;
}

/** A travelling peristaltic bump. `front` (distance along dir from the origin) is advanced by the ability. */
export function waveField(ox: number, oz: number, dirx: number, dirz: number, amp: number, sigma: number, halfSpan: number): Field & { front: number; amp: number } {
  const l = Math.hypot(dirx, dirz) || 1;
  const ux = dirx / l;
  const uz = dirz / l;
  const f = {
    front: 0,
    amp,
    x0: 0,
    x1: 0,
    z0: 0,
    z1: 0,
    dh(x: number, z: number): number {
      const rx = x + 0.5 - ox;
      const rz = z + 0.5 - oz;
      const s = rx * ux + rz * uz;
      const lat = Math.abs(-rx * uz + rz * ux);
      if (lat > halfSpan) return 0;
      const d = s - f.front;
      if (d > sigma * 3 || d < -sigma * 3) return 0;
      const fade = lat > halfSpan - 4 ? (halfSpan - lat) / 4 : 1;
      return f.amp * Math.exp(-(d * d) / (2 * sigma * sigma)) * fade;
    },
  };
  // the bounds follow the front; recomputed by updateWaveBounds
  return f;
}

export function updateWaveBounds(f: Field & { front: number }, ox: number, oz: number, dirx: number, dirz: number, sigma: number, halfSpan: number): void {
  const l = Math.hypot(dirx, dirz) || 1;
  const ux = dirx / l;
  const uz = dirz / l;
  const cx = ox + ux * f.front;
  const cz = oz + uz * f.front;
  const ex = Math.abs(uz) * halfSpan + Math.abs(ux) * sigma * 3 + 2;
  const ez = Math.abs(ux) * halfSpan + Math.abs(uz) * sigma * 3 + 2;
  // include the trailing area so columns behind the front settle
  const bx = ux * sigma * 4;
  const bz = uz * sigma * 4;
  f.x0 = Math.floor(Math.min(cx - ex, cx - ex - bx));
  f.x1 = Math.ceil(Math.max(cx + ex, cx + ex - bx));
  f.z0 = Math.floor(Math.min(cz - ez, cz - ez - bz));
  f.z1 = Math.ceil(Math.max(cz + ez, cz + ez - bz));
}

/** A rectangular patch lowered by `depth` with exposed musculature (Geological Shedding scar / Inverted Strata bed). */
export function patchField(x0: number, z0: number, x1: number, z1: number, depth: number, round = false): Field {
  const cx = (x0 + x1) / 2;
  const cz = (z0 + z1) / 2;
  const rx = (x1 - x0) / 2 + 0.5;
  const rz = (z1 - z0) / 2 + 0.5;
  return {
    x0,
    z0,
    x1,
    z1,
    scar: true,
    dh(x: number, z: number): number {
      if (round) {
        const q = ((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2;
        if (q > 1) return 0;
      }
      return -depth;
    },
  };
}
