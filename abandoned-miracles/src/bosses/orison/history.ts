/**
 * Orison's "temporal memory": a bounded ring buffer of where each participant
 * has recently stood.
 *
 *   - sampled every INTERVAL ticks (not every tick);
 *   - CAPACITY samples per player, overwritten oldest-first (64 samples = 12.8 s);
 *   - at most MAX_PLAYERS players tracked;
 *   - stores X and Z only, keyed by the player's entity id. Nothing else about a
 *     player is kept, and nothing is ever written to disk;
 *   - a player who stops being a participant is dropped after STALE ticks, and the
 *     whole store is cleared when the encounter ends.
 *
 * This is ordinary bookkeeping of past positions. It does not rewind, replay or
 * otherwise manipulate the simulation.
 */
import { Player } from "@minecraft/server";
import { XZ } from "../../core/math";

interface Track {
  x: Float32Array;
  z: Float32Array;
  /** Index the next sample will be written to. */
  head: number;
  size: number;
  lastSeen: number;
}

export class PositionHistory {
  static readonly INTERVAL = 4;
  static readonly CAPACITY = 64;
  static readonly MAX_PLAYERS = 8;
  static readonly STALE = 60;

  private tracks = new Map<string, Track>();

  /** Call every tick with the current participants; samples on the interval. */
  record(players: readonly Player[], now: number): void {
    if (now % PositionHistory.INTERVAL !== 0) return;
    for (const p of players) {
      if (!p.isValid) continue;
      let t = this.tracks.get(p.id);
      if (!t) {
        if (this.tracks.size >= PositionHistory.MAX_PLAYERS) continue;
        t = { x: new Float32Array(PositionHistory.CAPACITY), z: new Float32Array(PositionHistory.CAPACITY), head: 0, size: 0, lastSeen: now };
        this.tracks.set(p.id, t);
      }
      const l = p.location;
      t.x[t.head] = l.x;
      t.z[t.head] = l.z;
      t.head = (t.head + 1) % PositionHistory.CAPACITY;
      if (t.size < PositionHistory.CAPACITY) t.size++;
      t.lastSeen = now;
    }
    for (const [id, t] of this.tracks) if (now - t.lastSeen > PositionHistory.STALE) this.tracks.delete(id);
  }

  /** Up to `n` most recent samples, newest first. */
  recent(id: string, n: number): XZ[] {
    const t = this.tracks.get(id);
    if (!t) return [];
    const out: XZ[] = [];
    const count = Math.min(n, t.size);
    for (let i = 1; i <= count; i++) {
      const k = (t.head - i + PositionHistory.CAPACITY * 2) % PositionHistory.CAPACITY;
      out.push({ x: t.x[k], z: t.z[k] });
    }
    return out;
  }

  /** Average velocity (blocks per tick) over the last `samplesBack` samples. */
  velocity(id: string, samplesBack: number): XZ {
    const r = this.recent(id, samplesBack + 1);
    if (r.length < 2) return { x: 0, z: 0 };
    const a = r[0];
    const b = r[r.length - 1];
    const ticks = (r.length - 1) * PositionHistory.INTERVAL;
    return { x: (a.x - b.x) / ticks, z: (a.z - b.z) / ticks };
  }

  /** Distance walked over the last `n` samples. */
  pathLength(id: string, n: number): number {
    const r = this.recent(id, n);
    let d = 0;
    for (let i = 1; i < r.length; i++) d += Math.hypot(r[i].x - r[i - 1].x, r[i].z - r[i - 1].z);
    return d;
  }

  size(id: string): number {
    return this.tracks.get(id)?.size ?? 0;
  }

  trackedPlayers(): number {
    return this.tracks.size;
  }

  totalSamples(): number {
    let n = 0;
    for (const t of this.tracks.values()) n += t.size;
    return n;
  }

  forget(id: string): void {
    this.tracks.delete(id);
  }

  clear(): void {
    this.tracks.clear();
  }
}
