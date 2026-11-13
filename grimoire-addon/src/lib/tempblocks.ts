import { Dimension, Vector3, world } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { Scene } from "./scene";

/**
 * Temporary blocks (invisible barriers for real collision, light blocks for real illumination).
 * Rules that keep worlds safe:
 *   - a block is only ever placed into AIR, and only removed if it is still the block we placed;
 *   - every placement is written to a world ledger, so a crash / quit mid-spell is repaired the
 *     next time the world loads (see restoreLedger);
 *   - never placed inside a player's body.
 */
export const BARRIER = "minecraft:barrier";
export const LIGHT = "minecraft:light_block_15";

type Entry = { d: string; x: number; y: number; z: number; t: string };
const live = new Map<string, Entry>();
let dirty = false;
const KEY = "grim:tb";
const CHUNK = 30000;

const k = (d: string, x: number, y: number, z: number) => `${d}|${x}|${y}|${z}`;

function saveLedger(): void {
  dirty = false;
  const parts: string[] = [];
  for (const e of live.values()) parts.push(`${e.d},${e.x},${e.y},${e.z},${e.t}`);
  const s = parts.join(";");
  let i = 0;
  for (let off = 0; off < s.length || i === 0; off += CHUNK, i++) world.setDynamicProperty(`${KEY}${i}`, s.slice(off, off + CHUNK));
  for (; i < 8; i++) if (world.getDynamicProperty(`${KEY}${i}`) !== undefined) world.setDynamicProperty(`${KEY}${i}`, undefined);
}

/** Call once per tick; persists the ledger when it changed. */
export function flushLedger(): void {
  if (dirty) { try { saveLedger(); } catch (e) { console.warn(`[grimoire] ledger: ${e}`); } }
}

/** Repair blocks left behind by an interrupted session. */
export function restoreLedger(): void {
  let s = "";
  for (let i = 0; i < 8; i++) {
    const p = world.getDynamicProperty(`${KEY}${i}`);
    if (typeof p === "string") s += p;
  }
  if (!s) return;
  let pending = 0;
  for (const rec of s.split(";")) {
    const [d, xs, ys, zs, t] = rec.split(",");
    if (!d || t === undefined) continue;
    const e: Entry = { d, x: Number(xs), y: Number(ys), z: Number(zs), t };
    if (!clear(e)) { live.set(k(e.d, e.x, e.y, e.z), e); pending++; }
  }
  dirty = true;
  if (pending) console.warn(`[grimoire] ${pending} temporary blocks are in unloaded chunks; they will be removed when loaded.`);
}

/** Retry removal of ledger entries that no scene owns (unloaded at restore time). */
export function retryOrphans(owned: (key: string) => boolean): void {
  for (const [key, e] of [...live]) {
    if (owned(key)) continue;
    if (clear(e)) { live.delete(key); dirty = true; }
  }
}

function clear(e: Entry): boolean {
  try {
    const b = world.getDimension(e.d).getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b) return false;
    if (b.typeId === e.t) b.setType("minecraft:air");
    return true;
  } catch {
    return false;
  }
}

export class BlockSet {
  private mine = new Set<string>();
  constructor(private scene: Scene) {
    scene.onEnd(() => this.clearAll());
  }
  get size(): number { return this.mine.size; }
  has(loc: Vector3): boolean {
    return this.mine.has(k(this.scene.dimId, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z)));
  }
  /** Place a temporary block if the cell is air and not occupied by a player. */
  place(loc: Vector3, type: string = BARRIER): boolean {
    const x = Math.floor(loc.x), y = Math.floor(loc.y), z = Math.floor(loc.z);
    const key = k(this.scene.dimId, x, y, z);
    if (this.mine.has(key) || live.has(key) || live.size >= CONFIG.limits.maxTempBlocks) return false;
    const dim: Dimension = this.scene.dim;
    try {
      const b = dim.getBlock({ x, y, z });
      if (!b || !b.isAir) return false;
      if (type === BARRIER) {
        for (const p of dim.getPlayers({ location: { x: x + 0.5, y: y, z: z + 0.5 }, maxDistance: 2.5 })) {
          const l = p.location;
          if (Math.abs(l.x - (x + 0.5)) < 0.85 && Math.abs(l.z - (z + 0.5)) < 0.85 && y >= Math.floor(l.y) - 0 && y <= Math.floor(l.y + 1.9)) return false;
        }
      }
      b.setType(type);
      live.set(key, { d: this.scene.dimId, x, y, z, t: type });
      this.mine.add(key);
      dirty = true;
      return true;
    } catch {
      return false;
    }
  }
  remove(loc: Vector3): void {
    const key = k(this.scene.dimId, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
    this.removeKey(key);
  }
  private removeKey(key: string): void {
    const e = live.get(key);
    if (!e || !this.mine.has(key)) return;
    if (clear(e)) live.delete(key);
    this.mine.delete(key);
    dirty = true;
  }
  /** Vertical wall segment of barriers: column at (x, z) from y to y+h-1. */
  column(x: number, y: number, z: number, h: number, type: string = BARRIER): number {
    let n = 0;
    for (let i = 0; i < h; i++) if (this.place({ x, y: y + i, z }, type)) n++;
    return n;
  }
  removeColumn(x: number, y: number, z: number, h: number): void {
    for (let i = 0; i < h; i++) this.remove({ x, y: y + i, z });
  }
  clearAll(): void {
    for (const key of [...this.mine]) this.removeKey(key);
  }
  owns(key: string): boolean { return this.mine.has(key); }
}

const sets = new Set<BlockSet>();
/** Create the temporary-block set for a scene. */
export function blocksFor(scene: Scene): BlockSet {
  const s = new BlockSet(scene);
  sets.add(s);
  scene.onEnd(() => sets.delete(s));
  return s;
}
export function anySetOwns(key: string): boolean {
  for (const s of sets) if (s.owns(key)) return true;
  return false;
}
