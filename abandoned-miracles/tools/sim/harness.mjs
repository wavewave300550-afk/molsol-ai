/**
 * Simulation harness: loads the SHIPPED script bundle against the strict mock,
 * and provides bots that play the encounter the way a person would - they only
 * know about hazards that have been telegraphed, they react after a delay, and
 * they move at walking speed.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import * as mc from "./mock-server.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, "..", "..");
/** ABM_OUT selects a development build (see tools/build.py); default is the committed full build. */
const BASE = process.env.ABM_OUT ? path.resolve(process.env.ABM_OUT) : ROOT;
export const PACKS = path.join(BASE, "packs");
const OUT = path.join(BASE, "build", "sim");
export const { sim } = mc;

export const WALK = 4.317 / 20; // blocks per tick
export const SPRINT = 5.612 / 20;

let generation = 0;
export const log = { events: [], hazards: [], errors: [] };

let seedBase = 12345;
export function setSeed(n) {
  seedBase = n >>> 0;
}

/** Deterministic Math.random per world, so a failing scenario can be replayed exactly. */
function seedRandom(seed) {
  let s = seed >>> 0;
  Math.random = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A fresh world with a fresh instance of the add-on's script. */
export async function freshWorld() {
  generation++;
  seedRandom(seedBase + generation * 7919);
  sim.reset();
  sim.intervals.length = 0;
  sim.commands.clear();
  sim.enums.clear();
  for (const group of [mc.world.afterEvents, mc.world.beforeEvents, mc.system.beforeEvents, mc.system.afterEvents]) {
    for (const s of Object.values(group)) s.subs = [];
  }
  sim.loadPacks(PACKS);
  log.events = [];
  log.hazards = [];
  log.errors = [];
  globalThis.__abm = undefined;
  globalThis.__abmTrace = (kind, data) => {
    if (kind === "hazard") log.hazards.push({ ...data, seen: sim.tick });
    else if (kind === "error") log.errors.push(`tick ${sim.tick}: ${data.where}: ${data.msg}`);
    else log.events.push({ ...data, kind, at: sim.tick });
  };
  const bp = path.join(PACKS, "behavior_packs");
  const main = path.join(bp, fs.readdirSync(bp)[0], "scripts", "main.js");
  let src = fs.readFileSync(main, "utf8");
  const server = pathToFileURL(path.join(HERE, "mock-server.mjs")).href;
  const ui = pathToFileURL(path.join(HERE, "mock-server-ui.mjs")).href;
  src = src.replaceAll('"@minecraft/server-ui"', JSON.stringify(ui)).replaceAll('"@minecraft/server"', JSON.stringify(server));
  fs.mkdirSync(OUT, { recursive: true });
  const file = path.join(OUT, `main_${process.pid}_${generation}.mjs`);
  fs.writeFileSync(file, src);
  const realWarn = console.warn;
  console.warn = (...a) => {
    const m = a.join(" ");
    if (!m.startsWith("[abm] error")) log.events.push({ kind: "warn", at: sim.tick, msg: m });
  };
  try {
    await import(pathToFileURL(file).href);
  } finally {
    fs.unlinkSync(file);
  }
  mc.boot();
  console.warn = realWarn;
  globalThis.console.warn = (...a) => {
    const m = a.join(" ");
    if (!m.startsWith("[abm] error")) log.events.push({ kind: "warn", at: sim.tick, msg: m });
  };
  const api = globalThis.__abm;
  if (!api) throw new Error("bundle did not expose the test hook");
  return { manager: api.manager, CONFIG: api.CONFIG, mc };
}

export function count(kind, pred = () => true) {
  return log.events.filter((e) => e.kind === kind && pred(e)).length;
}

export function events(kind, pred = () => true) {
  return log.events.filter((e) => e.kind === kind && pred(e));
}

/** Will a point be struck by a telegraphed hazard at a given encounter tick? */
function strikes(h, t, x, z) {
  if (h.kind === "strike") return t === h.at && h.shape.contains(x, z);
  const rel = t - h.start;
  if (rel < 0 || rel > h.duration || rel % h.every !== 0) return false;
  return h.shapeAt(rel).contains(x, z);
}

function lastTick(h) {
  return h.kind === "strike" ? h.at : h.start + h.duration;
}

export class Bot {
  /**
   * mode: "stand" never moves; "dodge" avoids telegraphed hazards; "fight" dodges and attacks.
   * reaction: ticks between a telegraph appearing and the bot acting on it.
   */
  constructor(player, enc, opts = {}) {
    this.p = player;
    this.enc = enc;
    this.mode = opts.mode ?? "dodge";
    this.speed = opts.speed ?? WALK;
    this.reaction = opts.reaction ?? 6;
    this.damage = opts.damage ?? 13;
    this.swingEvery = opts.swingEvery ?? 12;
    this.reach = opts.reach ?? 3.4;
    this.prefer = opts.prefer ?? 3.0;
    /** Where on the boss to aim: fn(enc) -> {x,y,z}; default is body centre. */
    this.aimAt = opts.aimAt;
    /** Side to approach from, as an offset angle (degrees) relative to the boss's facing. */
    this.side = opts.side ?? 0;
    /** Natural regeneration: one health point every `regen` ticks (0 = none). */
    this.regen = opts.regen ?? 0;
    this.nextSwing = 0;
    this.swings = 0;
    this.landed = 0;
    this.moved = 0;
  }

  known() {
    const now = sim.tick;
    const et = this.enc.timeline.now;
    return log.hazards.filter((h) => h.enc === this.enc && now - h.seen >= this.reaction && lastTick(h) >= et);
  }

  /** Hits the bot would take walking straight to (tx, tz) at its speed and then waiting there. */
  risk(tx, tz, hazards) {
    const l = this.p._loc;
    const et = this.enc.timeline.now;
    const dx = tx - l.x;
    const dz = tz - l.z;
    const d = Math.hypot(dx, dz);
    const steps = d / this.speed;
    let hits = 0;
    for (const h of hazards) {
      const end = lastTick(h);
      const begin = h.kind === "strike" ? h.at : h.start;
      const stepT = h.kind === "strike" ? 1 : h.every;
      // a sweep is only live on its own grid (start, start + every, ...): start sampling on that grid
      let first = Math.max(begin, et + 1);
      if (h.kind !== "strike") first = begin + Math.ceil((first - begin) / stepT) * stepT;
      for (let t = first; t <= end; t += stepT) {
        const k = Math.min(1, steps > 0 ? (t - et) / steps : 1);
        if (strikes(h, t, l.x + dx * k, l.z + dz * k)) {
          hits++;
          break;
        }
      }
    }
    return hits;
  }

  desired() {
    const b = this.enc.boss;
    if (!b.isValid || this.mode !== "fight") return { x: this.p._loc.x, z: this.p._loc.z };
    const bl = b._loc;
    const yaw = (this.enc.loco.yaw + this.side) * (Math.PI / 180);
    return { x: bl.x - Math.sin(yaw) * this.prefer, z: bl.z + Math.cos(yaw) * this.prefer };
  }

  tick() {
    const p = this.p;
    if (!p.isValid || p._health.currentValue <= 0) return;
    if (this.regen && sim.tick % this.regen === 0) p._health.currentValue = Math.min(20, p._health.currentValue + 1);
    // knockback
    p._loc.x += p._vel.x;
    p._loc.z += p._vel.z;
    p._vel.x *= 0.5;
    p._vel.z *= 0.5;
    if (this.mode === "stand") return this.attack();
    const a = this.enc.arena;
    const want = this.desired();
    const hz = this.known();
    const cands = [want, { x: p._loc.x, z: p._loc.z }];
    for (let i = 0; i < 16; i++) {
      const th = (i / 16) * Math.PI * 2;
      for (const r of [1.5, 3, 5, 8, 12]) cands.push({ x: p._loc.x + Math.cos(th) * r, z: p._loc.z + Math.sin(th) * r });
    }
    let best = null;
    let bestScore = Infinity;
    for (const c of cands) {
      const q = a.clampInside(c.x, c.z, 0.8);
      const hits = this.risk(q.x, q.z, hz);
      const score = hits * 1000 + Math.hypot(q.x - want.x, q.z - want.z) + Math.hypot(q.x - p._loc.x, q.z - p._loc.z) * 0.05;
      if (score < bestScore) {
        bestScore = score;
        best = q;
      }
    }
    const dx = best.x - p._loc.x;
    const dz = best.z - p._loc.z;
    const d = Math.hypot(dx, dz);
    if (d > 0.02) {
      const s = Math.min(this.speed, d);
      p._loc.x += (dx / d) * s;
      p._loc.z += (dz / d) * s;
      this.moved += s;
    }
    this.attack();
  }

  attack() {
    if (this.mode !== "fight" && !this.forceAttack) return;
    const b = this.enc.boss;
    if (!b.isValid || sim.tick < this.nextSwing) return;
    const bl = b._loc;
    const l = this.p._loc;
    if (Math.hypot(bl.x - l.x, bl.z - l.z) > this.reach + 1.5) return;
    const aim = this.aimAt ? this.aimAt(this.enc) : { x: bl.x, y: bl.y + 3.4, z: bl.z };
    const eye = { x: l.x, y: l.y + 1.62, z: l.z };
    const v = { x: aim.x - eye.x, y: aim.y - eye.y, z: aim.z - eye.z };
    const n = Math.hypot(v.x, v.y, v.z) || 1;
    this.p._aim = { x: v.x / n, y: v.y / n, z: v.z / n };
    this.nextSwing = sim.tick + this.swingEvery;
    this.swings++;
    if (b.applyDamage(this.damage, { cause: "entityAttack", damagingEntity: this.p })) this.landed++;
  }
}

/** Run the world for n ticks, ticking bots first (players act, then the server ticks). */
export function run(n, bots = [], until = () => false) {
  for (let i = 0; i < n; i++) {
    for (const b of bots) b.tick();
    sim.step();
    if (until()) return i + 1;
  }
  return n;
}

export function useSeal(mcApi, player, key, floor) {
  const block = { x: Math.floor(floor.x), y: Math.floor(floor.y) - 1, z: Math.floor(floor.z) };
  const stack = new mcApi.ItemStack({ vesperra: "abm:seal_vesperra", cantor: "abm:seal_cantor", nomos: "abm:seal_nomos", orison: "abm:seal_orison" }[key]);
  player._held = stack;
  mcApi.world.afterEvents.playerInteractWithBlock._fire({ player, block, isFirstEvent: true, beforeItemStack: stack, itemStack: stack, blockFace: "Up", faceLocation: floor });
  sim.flush();
}
