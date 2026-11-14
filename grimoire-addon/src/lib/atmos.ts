import { Player, world } from "@minecraft/server";
import { CONFIG } from "../config/global";
import { Scene } from "./scene";

/**
 * Atmosphere for a spell that turns the world around the caster into another age:
 *
 *   * FOG - per player, through the player's fog stack with one tagged entry (never setStack, which
 *     would wipe the fogs of other packs).  The stack survives a world save, so it is also cleared
 *     on the next join (recoverPlayer) and on world load.
 *   * TIME OF DAY - one world-wide lease shared by overlapping casts: the clock sweeps to the target
 *     (the shortest way round), is held there, and sweeps back to where the world clock would be had
 *     nothing happened (the original time, plus the elapsed ticks when the daylight cycle runs).
 *     Only when every other overworld player is near the caster; it yields for good if anything else
 *     changes the time (a command, players sleeping); a crash record restores it on world load.
 *     The daylight-cycle game rule itself is never written.
 */

export const FOG_TAG = "grimoire_ed6";
const FOG_FLAG = "grim:fog";
const TOD_KEY = "grim:tod";

// ---------------------------------------------------------------------------------------------- fog
/** The fog of one cast: applied to the caster and to the players near them; removed on scene end. */
export class SceneFog {
  private players = new Set<Player>();
  private current?: string;
  constructor(private scene: Scene) {
    scene.onEnd(() => this.clear());
  }
  /** Switch everyone near the caster to fog `id` (a fogs/*.json identifier). */
  step(id: string, radius = CONFIG.atmosphere.fogRadius): void {
    if (!CONFIG.atmosphere.fog || this.scene.ended) return;
    this.current = id;
    for (const p of this.near(radius)) this.apply(p, id);
  }
  /** Take the fog away from everyone it was given to. */
  clear(): void {
    this.current = undefined;
    for (const p of this.players) clearFog(p);
    this.players.clear();
  }
  private apply(p: Player, id: string): void {
    try {
      p.fogSettings.remove(FOG_TAG);
      p.fogSettings.push(id, FOG_TAG);
      p.setDynamicProperty(FOG_FLAG, 1);
      this.players.add(p);
    } catch { /* gone, or the stack is full of other packs' fogs */ }
  }
  private near(radius: number): Player[] {
    const out: Player[] = [];
    const c = this.scene.caster;
    if (!this.scene.casterOk) return out;
    out.push(c);
    try {
      for (const p of this.scene.dim.getPlayers({ location: c.location, maxDistance: radius })) if (p.id !== c.id) out.push(p);
    } catch { /* ignore */ }
    return out;
  }
}
function clearFog(p: Player): void {
  try {
    if (!p.isValid) return;
    p.fogSettings.remove(FOG_TAG);
    p.setDynamicProperty(FOG_FLAG, undefined);
  } catch { /* gone */ }
}
export function fogFor(scene: Scene): SceneFog { return new SceneFog(scene); }

// ---------------------------------------------------------------------------------------------- time
interface Lease {
  holders: Set<Scene>;
  /** absolute time and daylight cycle when the first cast began */
  abs0: number;
  cycle: boolean;
  /** ticks since the lease began (what the world clock would have advanced) */
  t: number;
  phase: "in" | "hold" | "out";
  /** sweep from -> to over [k, n) ticks of the current phase */
  from: number;
  to: number;
  k: number;
  n: number;
  /** what we last set and when (lease tick), to notice anyone else changing the time */
  lastSet: number;
  lastAt: number;
}
let lease: Lease | undefined;

const ease = (p: number) => (p <= 0 ? 0 : p >= 1 ? 1 : p * p * (3 - 2 * p));
const natural = (l: Lease) => l.abs0 + (l.cycle ? l.t : 0);

function setAbs(l: Lease, v: number): void {
  const a = Math.max(0, Math.round(v));
  world.setAbsoluteTime(a);
  l.lastSet = a;
  l.lastAt = l.t;
}
function record(l: Lease | undefined): void {
  try { world.setDynamicProperty(TOD_KEY, l ? JSON.stringify({ a: l.abs0, c: l.cycle, e: l.t }) : undefined); } catch { /* ignore */ }
}
function finish(restore: boolean): void {
  const l = lease;
  lease = undefined;
  if (l && restore) { try { setAbs(l, natural(l)); } catch { /* ignore */ } }
  record(undefined);
}
/** Signed shortest way from time-of-day `a` to `b` (ticks, -12000..12000). */
function shortest(a: number, b: number): number {
  return ((((b - a) % 24000) + 36000) % 24000) - 12000;
}
/** May this cast change the world's clock?  Only in the overworld, with every other player near. */
function mayChangeTime(caster: Player): boolean {
  if (CONFIG.atmosphere.time === "off") return false;
  try {
    if (caster.dimension.id !== "minecraft:overworld") return false;
    for (const p of world.getAllPlayers()) {
      if (p.id === caster.id) continue;
      if (p.dimension.id !== caster.dimension.id) return false;
      const d = Math.hypot(p.location.x - caster.location.x, p.location.z - caster.location.z);
      if (d > CONFIG.atmosphere.timeRadius || p.isSleeping) return false;
    }
    return true;
  } catch { return false; }
}

/**
 * Hold the world's time of day at `target` for this scene: sweep there over `inTicks`, keep it until
 * releaseTime(scene) (then sweep back over `outTicks`) or until the scene ends (then put it back at once).
 * Returns false when the time is left alone (other players far away, another dimension, setting off).
 */
export function leaseTime(scene: Scene, target: number, inTicks: number): boolean {
  if (!mayChangeTime(scene.caster)) return false;
  try {
    if (!lease) {
      const abs0 = world.getAbsoluteTime();
      const cycle = world.gameRules.doDayLightCycle;
      let delta = shortest(abs0 % 24000, target);
      if (abs0 + delta < 0) delta += 24000;
      lease = { holders: new Set(), abs0, cycle, t: 0, phase: "in", from: abs0, to: abs0 + delta, k: 0, n: Math.max(1, inTicks), lastSet: abs0, lastAt: 0 };
      record(lease);
    } else if (lease.phase === "out") {
      // a new cast while the last one was handing the clock back: sweep to the sunset again
      const cur = world.getAbsoluteTime();
      const delta = shortest(cur % 24000, target);
      lease.phase = "in"; lease.from = cur; lease.to = Math.max(0, cur + delta); lease.k = 0; lease.n = Math.max(1, inTicks);
    }
    lease.holders.add(scene);
  } catch { return false; }
  const held = lease;
  scene.onEnd(() => {
    if (lease !== held || !held.holders.delete(scene)) return;
    if (!held.holders.size) finish(true);                         // aborted (caster left...): put it back now
  });
  return true;
}
/** This scene is done with the time: the clock sweeps back once no other cast holds it. */
export function releaseTime(scene: Scene, outTicks: number): void {
  const l = lease;
  if (!l || !l.holders.delete(scene)) return;
  if (l.holders.size) return;
  try {
    const cur = world.getAbsoluteTime();
    l.phase = "out"; l.from = cur; l.k = 0; l.n = Math.max(1, outTicks);
    l.to = l.abs0 + (l.cycle ? l.t + l.n : 0);
  } catch { finish(true); }
}
/** True while a cast holds the world's time. */
export function timeLeased(): boolean { return lease !== undefined; }

/** Drive the time lease; once per tick from main.ts. */
export function tickAtmos(): void {
  const l = lease;
  if (!l) return;
  try {
    // anyone else changed the time (a command, players sleeping through the night)? let it be, for good
    const expect = l.lastSet + (l.cycle ? l.t - l.lastAt : 0);
    if (Math.abs(world.getAbsoluteTime() - expect) > 40) { finish(false); return; }
    l.t++;
    if (l.phase === "hold") {
      if (l.t - l.lastAt >= 10) setAbs(l, l.to);                  // the cycle would move the sun on: hold it
    } else {
      l.k++;
      setAbs(l, l.from + (l.to - l.from) * ease(l.k / l.n));
      if (l.k >= l.n) {
        if (l.phase === "in") { l.phase = "hold"; }
        else { finish(true); return; }
      }
    }
    if (l.t % 20 === 0) record(l);
  } catch {
    finish(false);
  }
}

// ---------------------------------------------------------------------------------------------- recovery
/** World load: put the clock back after a crash during a lease. */
export function restoreTime(): void {
  const s = world.getDynamicProperty(TOD_KEY);
  if (typeof s !== "string") return;
  try {
    const r = JSON.parse(s) as { a: number; c: boolean; e: number };
    if (Number.isFinite(r.a) && Number.isFinite(r.e)) world.setAbsoluteTime(Math.max(0, Math.round(r.a + (r.c ? r.e : 0))));
  } catch { /* corrupt: drop it */ }
  world.setDynamicProperty(TOD_KEY, undefined);
}
/** A player joined: no spell fog may be left on them from a session that did not end cleanly. */
export function recoverFog(p: Player): void {
  try {
    if (p.getDynamicProperty(FOG_FLAG) !== undefined || p.fogSettings.getTags().includes(FOG_TAG)) clearFog(p);
  } catch { /* ignore */ }
}
