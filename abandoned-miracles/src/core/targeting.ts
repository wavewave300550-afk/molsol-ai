/**
 * TargetingSystem - who is in the fight and who the boss is focused on.
 *
 * Participants are recomputed from a single bounded query around the arena
 * every few ticks. Threat accrues from damage dealt and decays over time; the
 * primary target only changes when another player clearly out-threatens it or
 * it becomes invalid, so the boss does not flicker between players.
 */
import { Dimension, EntityHealthComponent, GameMode, Player } from "@minecraft/server";
import { CONFIG } from "../config";
import { Arena } from "./arena";
import { Rng, XZ, distXZ } from "./math";

const REFRESH_TICKS = 5;
const SWITCH_DWELL_TICKS = 100;
const SWITCH_RATIO = 1.3;

export function isAlivePlayer(p: Player | undefined): p is Player {
  if (!p || !p.isValid) return false;
  const h = p.getComponent("minecraft:health") as EntityHealthComponent | undefined;
  return !!h && h.currentValue > 0;
}

export class Targeting {
  private list: Player[] = [];
  private threat = new Map<string, number>();
  private primaryId: string | undefined;
  private lastSwitch = -9999;
  private lastRefresh = -9999;
  /** Highest number of simultaneous participants seen (drives health scaling). */
  peak = 0;
  /** Every player id that has been a participant (for rewards). */
  readonly everSeen = new Set<string>();
  /** Players who actually damaged the boss. */
  readonly contributors = new Set<string>();

  constructor(private readonly dim: Dimension, private readonly arena: Arena) {}

  refresh(now: number, force = false): void {
    if (!force && now - this.lastRefresh < REFRESH_TICKS) return;
    this.lastRefresh = now;
    const reach = (this.arena.square ? this.arena.radius * Math.SQRT2 : this.arena.radius) + CONFIG.encounter.arenaMargin;
    let found: Player[] = [];
    try {
      found = this.dim.getPlayers({ location: this.arena.centre, maxDistance: reach + CONFIG.encounter.floorAbove });
    } catch {
      found = [];
    }
    this.list = found.filter((p) => this.isParticipant(p));
    for (const p of this.list) this.everSeen.add(p.id);
    if (this.list.length > this.peak) this.peak = this.list.length;
    // threat decay (~3% per second) and pruning
    for (const [id, t] of this.threat) {
      const nt = t * 0.992;
      if (nt < 0.05) this.threat.delete(id);
      else this.threat.set(id, nt);
    }
  }

  isParticipant(p: Player): boolean {
    if (!isAlivePlayer(p)) return false;
    let mode: GameMode;
    try {
      mode = p.getGameMode();
    } catch {
      return false;
    }
    if (mode === GameMode.Spectator) return false;
    const l = p.location;
    return this.arena.contains(l.x, l.z, -CONFIG.encounter.arenaMargin) && this.arena.inBand(l.y);
  }

  /** Live participants (validity re-checked, because players can leave between refreshes). */
  participants(): Player[] {
    return this.list.filter((p) => isAlivePlayer(p));
  }

  count(): number {
    return this.participants().length;
  }

  addThreat(playerId: string, amount: number): void {
    this.threat.set(playerId, (this.threat.get(playerId) ?? 0) + amount);
    this.contributors.add(playerId);
  }

  /** Current focus; re-evaluated with hysteresis. */
  primary(now: number): Player | undefined {
    const ps = this.participants();
    if (ps.length === 0) {
      this.primaryId = undefined;
      return undefined;
    }
    let cur = ps.find((p) => p.id === this.primaryId);
    const best = ps.reduce((a, b) => ((this.threat.get(b.id) ?? 0) > (this.threat.get(a.id) ?? 0) ? b : a));
    if (!cur) {
      cur = best;
      this.primaryId = cur.id;
      this.lastSwitch = now;
    } else if (best.id !== cur.id && now - this.lastSwitch >= SWITCH_DWELL_TICKS) {
      const tc = this.threat.get(cur.id) ?? 0;
      const tb = this.threat.get(best.id) ?? 0;
      if (tb > tc * SWITCH_RATIO + 2) {
        cur = best;
        this.primaryId = cur.id;
        this.lastSwitch = now;
      }
    }
    return cur;
  }

  /** Force a different focus (used by attacks that deliberately retarget in multiplayer). */
  focus(p: Player, now: number): void {
    this.primaryId = p.id;
    this.lastSwitch = now;
  }

  nearest(to: XZ): Player | undefined {
    const ps = this.participants();
    if (ps.length === 0) return undefined;
    return ps.reduce((a, b) => (distXZ(b.location, to) < distXZ(a.location, to) ? b : a));
  }

  farthest(to: XZ): Player | undefined {
    const ps = this.participants();
    if (ps.length === 0) return undefined;
    return ps.reduce((a, b) => (distXZ(b.location, to) > distXZ(a.location, to) ? b : a));
  }

  /** A participant other than `not`, falling back to `not` when alone. */
  other(rng: Rng, not: Player | undefined): Player | undefined {
    const ps = this.participants();
    const rest = ps.filter((p) => p.id !== not?.id);
    if (rest.length > 0) return rng.pick(rest);
    return ps[0];
  }

  /** Up to `n` distinct participants, primary first. */
  several(rng: Rng, n: number, now: number): Player[] {
    const first = this.primary(now);
    const rest = rng.shuffle(this.participants().filter((p) => p.id !== first?.id));
    return (first ? [first, ...rest] : rest).slice(0, n);
  }
}
