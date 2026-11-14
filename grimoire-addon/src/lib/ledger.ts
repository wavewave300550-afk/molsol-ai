import { Dimension, Entity, system, world } from "@minecraft/server";

/**
 * Crash-safe memory of the blocks a spell holds changed (the living ground of src/lib/terraform.ts).
 *
 * Measured on a real 26.62 server killed hard: a chunk's blocks AND the entities inside it are saved
 * together within about 10 s of a change, but world dynamic properties only every half minute or so - a
 * ledger kept in world properties can be missing for blocks that are already on disk.  So the record of
 * each chunk's changed blocks lives on a small invisible marker entity INSIDE that chunk (persistent,
 * not a spell construct), written before the blocks change and saved in the same pass as them.
 *
 * A marker that loads while no running spell holds its chunk - after a crash or a quit, or a chunk that
 * was unloaded when its spell ended - is handed to the owner's restore function, and removed once all
 * of its blocks are back.
 */
export const LEDGER_ENTITY = "grimoire:ledger";
const PARTS = 4, PART_LEN = 30000;

/** One changed block: where, what it was and what the spell put there ("type|{states json}"). */
export interface Rec { x: number; y: number; z: number; o: string; p: string }

interface Chunk { dim: Dimension; cx: number; cz: number; id?: string; recs: Map<string, Rec> }
const chunks = new Map<string, Chunk>();
const ckey = (dimId: string, cx: number, cz: number) => `${dimId}|${cx}|${cz}`;
const rkey = (r: { x: number; y: number; z: number }) => `${r.x}|${r.y}|${r.z}`;
/** Puts the blocks of an orphaned marker back; returns the records it could not restore yet. */
let restorer: ((dim: Dimension, recs: Rec[]) => Rec[]) | undefined;
let warned = false;

function groupByChunk(dim: Dimension, recs: Rec[]): Map<string, { cx: number; cz: number; recs: Rec[] }> {
  const out = new Map<string, { cx: number; cz: number; recs: Rec[] }>();
  for (const r of recs) {
    const cx = r.x >> 4, cz = r.z >> 4, k = ckey(dim.id, cx, cz);
    let g = out.get(k);
    if (!g) { g = { cx, cz, recs: [] }; out.set(k, g); }
    g.recs.push(r);
  }
  return out;
}

function encode(c: Chunk): string {
  const pal: string[] = [], idx = new Map<string, number>();
  const ix = (s: string) => { let i = idx.get(s); if (i === undefined) { i = pal.length; pal.push(s); idx.set(s, i); } return i; };
  const e: string[] = [];
  for (const r of c.recs.values()) e.push(`${r.x - c.cx * 16},${r.y},${r.z - c.cz * 16},${ix(r.o)},${ix(r.p)}`);
  return JSON.stringify({ v: 1, cx: c.cx, cz: c.cz, pal, e: e.join(";") });
}
function decode(s: string): { cx: number; cz: number; recs: Rec[] } | undefined {
  try {
    const j = JSON.parse(s) as { v: number; cx: number; cz: number; pal: string[]; e: string };
    const recs: Rec[] = [];
    for (const t of (j.e ?? "").split(";")) {
      const f = t.split(",").map(Number);
      if (f.length !== 5 || f.some((n) => !Number.isFinite(n)) || !j.pal[f[3]] || !j.pal[f[4]]) continue;
      recs.push({ x: j.cx * 16 + f[0], y: f[1], z: j.cz * 16 + f[2], o: j.pal[f[3]], p: j.pal[f[4]] });
    }
    return { cx: j.cx, cz: j.cz, recs };
  } catch { return undefined; }
}
function readMarker(e: Entity): { cx: number; cz: number; recs: Rec[] } | undefined {
  let s = "";
  for (let i = 0; i < PARTS; i++) {
    const p = e.getDynamicProperty(`gl${i}`);
    if (typeof p !== "string") break;
    s += p;
  }
  return s ? decode(s) : undefined;
}
function writeMarker(e: Entity, s: string): void {
  if (s.length > PARTS * PART_LEN) throw new Error("chunk ledger full");
  let i = 0;
  for (let off = 0; off < s.length; off += PART_LEN, i++) e.setDynamicProperty(`gl${i}`, s.slice(off, off + PART_LEN));
  for (; i < PARTS; i++) if (e.getDynamicProperty(`gl${i}`) !== undefined) e.setDynamicProperty(`gl${i}`, undefined);
}
function markerOf(c: Chunk): Entity | undefined {
  if (!c.id) return undefined;
  try { const e = world.getEntity(c.id); return e?.isValid ? e : undefined; } catch { return undefined; }
}

/** Bring a chunk's marker up to date with its records (spawn it, rewrite it, or remove it when empty). */
function sync(k: string, c: Chunk): void {
  let e = markerOf(c);
  if (!c.recs.size) {
    if (e) e.remove();
    chunks.delete(k);
    return;
  }
  if (!e) {
    let y = 0;
    for (const r of c.recs.values()) { y = r.y + 1; break; }
    const hr = c.dim.heightRange;
    y = Math.min(hr.max - 2, Math.max(hr.min + 1, y));
    e = c.dim.spawnEntity(LEDGER_ENTITY, { x: c.cx * 16 + 8, y, z: c.cz * 16 + 8 });
    c.id = e.id;
  }
  writeMarker(e, encode(c));
}

export const Ledger = {
  /**
   * Record blocks before they change (write-ahead).  False when the record could not be written:
   * then nothing is recorded and the caller must not change those blocks.
   */
  write(dim: Dimension, recs: Rec[]): boolean {
    const touched: [string, Chunk, Rec[]][] = [];
    for (const [k, g] of groupByChunk(dim, recs)) {
      let c = chunks.get(k);
      if (!c) { c = { dim, cx: g.cx, cz: g.cz, recs: new Map() }; chunks.set(k, c); }
      for (const r of g.recs) c.recs.set(rkey(r), r);
      touched.push([k, c, g.recs]);
    }
    try {
      for (const [k, c] of touched) sync(k, c);
      return true;
    } catch (err) {
      for (const [k, c, rs] of touched) {
        for (const r of rs) c.recs.delete(rkey(r));
        try { sync(k, c); } catch { /* leave it */ }
      }
      if (!warned) { warned = true; console.warn(`[grimoire] block ledger could not be written (changes skipped): ${err}`); }
      return false;
    }
  },
  /** These blocks are back as they were: forget them (a chunk's marker goes with its last record). */
  drop(dim: Dimension, recs: Rec[]): void {
    for (const [k, g] of groupByChunk(dim, recs)) {
      const c = chunks.get(k);
      if (!c) continue;
      for (const r of g.recs) c.recs.delete(rkey(r));
      try { sync(k, c); } catch { /* the chunk went away: its marker restores the rest when it loads */ }
    }
  },
  /**
   * The spell can no longer put these back now (their chunk is not loaded): let go of them.  Their
   * marker still lists them, and restores them when the chunk loads.
   */
  release(dim: Dimension, recs: Rec[]): void {
    for (const k of groupByChunk(dim, recs).keys()) chunks.delete(k);
  },
  /** Blocks a marker restores when it loads unheld are put back by `fn` (it returns those it could not). */
  onOrphans(fn: (dim: Dimension, recs: Rec[]) => Rec[]): void { restorer = fn; },
  /** A marker entity loaded or was found: restore its blocks unless a running spell holds its chunk. */
  adopt(e: Entity): void {
    try {
      if (!e.isValid || e.typeId !== LEDGER_ENTITY) return;
      const m = readMarker(e);
      const dim = e.dimension;
      if (!m) { e.remove(); return; }
      const k = ckey(dim.id, m.cx, m.cz);
      const held = chunks.get(k);
      if (held) { held.id = e.id; return; }                        // a running spell's chunk came back
      const left = restorer ? restorer(dim, m.recs) : m.recs;
      if (!left.length) { e.remove(); return; }
      if (left.length !== m.recs.length) {
        const c: Chunk = { dim, cx: m.cx, cz: m.cz, id: e.id, recs: new Map(left.map((r) => [rkey(r), r])) };
        writeMarker(e, encode(c));
      }
    } catch (err) {
      console.warn(`[grimoire] block ledger marker: ${err}`);
    }
  },
  /** Every marker in loaded chunks (world load, cleanup); the rest arrive through entityLoad. */
  scan(): void {
    for (const id of ["overworld", "nether", "the_end"]) {
      try {
        for (const e of world.getDimension(id).getEntities({ type: LEDGER_ENTITY })) Ledger.adopt(e);
      } catch { /* dimension not loaded */ }
    }
  },
  /** Markers that load with their chunk later (a player walks back to where a spell was cut short). */
  install(): void {
    world.afterEvents.entityLoad.subscribe((ev) => {
      const e = ev.entity;
      if (e.typeId === LEDGER_ENTITY) system.run(() => Ledger.adopt(e));
    });
  },
  /** Chunks a running spell holds (for tests and diagnostics). */
  heldChunks(): number { return chunks.size; },
};
