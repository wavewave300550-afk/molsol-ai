// src/boot.ts
import { system as system4 } from "@minecraft/server";

// src/commands.ts
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  Player as Player7,
  system as system3
} from "@minecraft/server";

// src/config.ts
var BOSS_KEYS = ["vesperra", "cantor", "nomos", "orison"];
var CONFIG = {
  /** Extra console output and on-screen state. Toggle in game with /abm:debug. */
  debug: false,
  difficulty: "normal",
  difficulties: {
    story: { damage: 0.6, health: 0.75, attackGap: 1.35 },
    normal: { damage: 1, health: 1, attackGap: 1 },
    hard: { damage: 1.3, health: 1.25, attackGap: 0.8 }
  },
  bosses: {
    vesperra: { health: 480, phase2At: 0.45, arenaRadius: 17, arenaShape: "circle", clearance: 9, leashInset: 4, damageTaken: 0.1 },
    cantor: { health: 520, phase2At: 0.5, arenaRadius: 19, arenaShape: "circle", clearance: 11, leashInset: 6, damageTaken: 0.1 },
    nomos: { health: 560, phase2At: 0.4, arenaRadius: 20, arenaShape: "square", clearance: 9, leashInset: 4, damageTaken: 0.1 },
    orison: { health: 600, phase2At: 0.35, arenaRadius: 18, arenaShape: "circle", clearance: 10, leashInset: 4, damageTaken: 0.1 }
  },
  encounter: {
    /** Players beyond this count do not add health. */
    maxScaledPlayers: 4,
    /** Effective HP = base * (1 + hpPerExtraPlayer * (players - 1)). */
    hpPerExtraPlayer: 0.45,
    /** Largest share of maximum health one hit may remove (anti one-shot). */
    maxHitFraction: 0.04,
    /** Players further than arena radius + this margin are not participants. */
    arenaMargin: 5,
    /** Vertical band, relative to the arena floor, in which players count as inside. */
    floorBelow: 4,
    floorAbove: 14,
    /** Damage dealt from outside the arena is ignored (stops ranged cheese). */
    blockOutsideDamage: true,
    /** With nobody left in the arena, the encounter resets after this long. */
    resetGraceTicks: 400,
    /** On reset the summoning seal is dropped at the arena centre. */
    refundSealOnReset: true,
    /** Minimum share of sampled floor cells that must be solid + clear to allow a summon. */
    minFloorCoverage: 0.7,
    /** A player cannot be damaged by the same encounter more often than this. */
    playerHitIntervalTicks: 10,
    /** How long the lifeless remnant stays before it crumbles. */
    remnantTicks: 600,
    /** Helpers (minions, bells, anchors, ...) alive at once, per encounter. */
    maxHelpers: 12,
    /** Idle ticks between attacks before difficulty scaling. */
    baseAttackGap: 26
  },
  /**
   * Player damage model. Hazards deal `design damage * difficulty * (1 - mitigation)`.
   * Vanilla Bedrock armour removes up to ~96% of a hit in enchanted diamond, which would
   * make every telegraphed attack irrelevant, so mitigation is computed here with a
   * gentler, documented curve and applied exactly (see core/damage.ts).
   */
  damage: {
    armorPerPoint: 0.02,
    // 20 armour points (full diamond) -> 40%
    armorCap: 0.4,
    protectionPerLevel: 0.0125,
    // 16 levels (4 x Protection IV) -> 20%
    protectionCap: 0.2,
    resistancePerLevel: 0.15,
    resistanceCap: 0.6,
    /** A hit can never be reduced below this share of its design damage. */
    minShare: 0.25
  },
  movement: {
    /** "impulse": velocity steering (smooth). "teleport": stepwise fallback. */
    mode: "impulse"
  },
  hud: {
    actionBar: true,
    intervalTicks: 10
  },
  vfx: {
    /** 1 = full decoration. Telegraph outlines are never reduced. */
    density: 1
  }
};
function difficulty() {
  return CONFIG.difficulties[CONFIG.difficulty] ?? CONFIG.difficulties.normal;
}
function exportSettings() {
  return {
    difficulty: CONFIG.difficulty,
    vfxDensity: CONFIG.vfx.density,
    debug: CONFIG.debug,
    movementMode: CONFIG.movement.mode,
    actionBar: CONFIG.hud.actionBar
  };
}
function applySettings(s) {
  if (s.difficulty && s.difficulty in CONFIG.difficulties) CONFIG.difficulty = s.difficulty;
  if (typeof s.vfxDensity === "number") CONFIG.vfx.density = Math.max(0.25, Math.min(1, s.vfxDensity));
  if (typeof s.debug === "boolean") CONFIG.debug = s.debug;
  if (s.movementMode === "impulse" || s.movementMode === "teleport") CONFIG.movement.mode = s.movementMode;
  if (typeof s.actionBar === "boolean") CONFIG.hud.actionBar = s.actionBar;
}

// src/core/manager.ts
import {
  ItemStack as ItemStack2,
  system,
  world as world3
} from "@minecraft/server";

// src/core/math.ts
var DEG = 180 / Math.PI;
var RAD = Math.PI / 180;
var distXZ = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
function normXZ(dx, dz) {
  const l = Math.hypot(dx, dz);
  return l > 1e-9 ? { x: dx / l, z: dz / l } : { x: 0, z: 1 };
}
var clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;
function wrapDeg(a) {
  a = ((a + 180) % 360 + 360) % 360 - 180;
  return a === -180 ? 180 : a;
}
var angDiff = (a, b) => wrapDeg(b - a);
function approachAngle(cur, target, step) {
  const d = angDiff(cur, target);
  return Math.abs(d) <= step ? wrapDeg(target) : wrapDeg(cur + Math.sign(d) * step);
}
var yawToDir = (yaw) => ({ x: -Math.sin(yaw * RAD), z: Math.cos(yaw * RAD) });
var dirToYaw = (dx, dz) => Math.atan2(-dx, dz) * DEG;
var thetaToDir = (theta) => ({ x: Math.cos(theta * RAD), z: Math.sin(theta * RAD) });
var dirToTheta = (dx, dz) => Math.atan2(dz, dx) * DEG;
var yawToTheta = (yaw) => wrapDeg(yaw + 90);
function localToWorld(origin, yaw, right, up, fwd) {
  const f = yawToDir(yaw);
  const r = { x: -f.z, z: f.x };
  return { x: origin.x + r.x * right + f.x * fwd, y: origin.y + up, z: origin.z + r.z * right + f.z * fwd };
}
function worldToLocal(origin, yaw, p) {
  const f = yawToDir(yaw);
  const r = { x: -f.z, z: f.x };
  const dx = p.x - origin.x;
  const dz = p.z - origin.z;
  return { right: dx * r.x + dz * r.z, up: p.y - origin.y, fwd: dx * f.x + dz * f.z };
}
var Rng = class {
  constructor(seed) {
    this.s = seed >>> 0 || 2654435769;
  }
  next() {
    let t = this.s += 1831565813;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
  range(lo, hi) {
    return lo + (hi - lo) * this.next();
  }
  int(lo, hi) {
    return Math.floor(this.range(lo, hi + 1));
  }
  chance(p) {
    return this.next() < p;
  }
  pick(items) {
    return items[Math.min(items.length - 1, Math.floor(this.next() * items.length))];
  }
  shuffle(items) {
    const a = items.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  /** Weighted pick; returns undefined when every weight is zero. */
  weighted(items, weight) {
    const w = items.map((i) => Math.max(0, weight(i)));
    const total = w.reduce((a, b) => a + b, 0);
    if (total <= 0) return void 0;
    let r = this.next() * total;
    for (let i = 0; i < items.length; i++) {
      r -= w[i];
      if (r <= 0) return items[i];
    }
    return items[items.length - 1];
  }
};
function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// src/core/shapes.ts
var Circle = class {
  constructor(cx, cz, r) {
    this.cx = cx;
    this.cz = cz;
    this.r = r;
    this.reach = r;
  }
  contains(x, z) {
    const dx = x - this.cx;
    const dz = z - this.cz;
    return dx * dx + dz * dz <= this.r * this.r;
  }
  draw(pen) {
    pen.arc(this.cx, this.cz, this.r, 0, 360);
    pen.disc(this.cx, this.cz, this.r);
  }
  sample(rng, n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const a = rng.range(0, Math.PI * 2);
      const d = Math.sqrt(rng.next()) * this.r;
      out.push({ x: this.cx + Math.cos(a) * d, z: this.cz + Math.sin(a) * d });
    }
    return out;
  }
};
function inSweep(theta, a0, sweep) {
  if (sweep >= 360) return true;
  const d = ((theta - a0) % 360 + 360) % 360;
  return d <= sweep;
}
var Ring = class {
  constructor(cx, cz, r0, r1, a0 = 0, sweep = 360, gaps = []) {
    this.cx = cx;
    this.cz = cz;
    this.r0 = r0;
    this.r1 = r1;
    this.a0 = a0;
    this.sweep = sweep;
    this.gaps = gaps;
    this.reach = r1;
  }
  contains(x, z) {
    const dx = x - this.cx;
    const dz = z - this.cz;
    const d2 = dx * dx + dz * dz;
    if (d2 < this.r0 * this.r0 || d2 > this.r1 * this.r1) return false;
    const th = Math.atan2(dz, dx) * DEG;
    if (!inSweep(th, this.a0, this.sweep)) return false;
    for (const [g0, gs] of this.gaps) if (inSweep(th, g0, gs)) return false;
    return true;
  }
  /** Solid angular spans as [start, sweep], i.e. the sweep with the gaps cut out. */
  spans() {
    if (this.gaps.length === 0) return [[this.a0, this.sweep]];
    const cuts = [];
    for (const [g0, gs] of this.gaps) {
      let s = ((g0 - this.a0) % 360 + 360) % 360;
      let e = s + gs;
      if (e > 360 && this.sweep >= 360) {
        cuts.push([0, e - 360]);
        e = 360;
      }
      s = clamp(s, 0, this.sweep);
      e = clamp(e, 0, this.sweep);
      if (e > s) cuts.push([s, e]);
    }
    cuts.sort((a, b) => a[0] - b[0]);
    const out = [];
    let cur = 0;
    for (const [s, e] of cuts) {
      if (s > cur + 1e-6) out.push([this.a0 + cur, s - cur]);
      cur = Math.max(cur, e);
    }
    if (cur < this.sweep - 1e-6) out.push([this.a0 + cur, this.sweep - cur]);
    return out;
  }
  draw(pen) {
    const full = this.sweep >= 360 && this.gaps.length === 0;
    for (const [s, w] of this.spans()) {
      pen.arc(this.cx, this.cz, this.r1, s, w);
      if (this.r0 > 0.5) pen.arc(this.cx, this.cz, this.r0, s, w);
      if (!full) {
        for (const a of [s, s + w]) {
          const d = thetaToDir(a);
          pen.line(this.cx + d.x * this.r0, this.cz + d.z * this.r0, this.cx + d.x * this.r1, this.cz + d.z * this.r1);
        }
      }
    }
  }
  sample(rng, n) {
    const out = [];
    const spans = this.spans();
    if (spans.length === 0) return out;
    for (let i = 0; i < n; i++) {
      const [s, w] = rng.pick(spans);
      const a = (s + rng.next() * w) * RAD;
      const d = Math.sqrt(rng.range(this.r0 * this.r0, this.r1 * this.r1));
      out.push({ x: this.cx + Math.cos(a) * d, z: this.cz + Math.sin(a) * d });
    }
    return out;
  }
};
function sector(cx, cz, r0, r1, theta, half) {
  return new Ring(cx, cz, r0, r1, wrapDeg(theta - half), half * 2);
}
var Lane = class {
  constructor(ax, az, bx, bz, halfWidth, flat = true) {
    this.ax = ax;
    this.az = az;
    this.bx = bx;
    this.bz = bz;
    this.halfWidth = halfWidth;
    this.flat = flat;
    this.cx = (ax + bx) / 2;
    this.cz = (az + bz) / 2;
    this.length = Math.hypot(bx - ax, bz - az);
    this.ux = this.length > 1e-9 ? (bx - ax) / this.length : 1;
    this.uz = this.length > 1e-9 ? (bz - az) / this.length : 0;
    this.reach = this.length / 2 + halfWidth;
  }
  contains(x, z) {
    const px = x - this.ax;
    const pz = z - this.az;
    const along = px * this.ux + pz * this.uz;
    const across = Math.abs(-px * this.uz + pz * this.ux);
    if (across > this.halfWidth) return false;
    if (along >= 0 && along <= this.length) return true;
    if (this.flat) return false;
    const ex = along < 0 ? px : x - this.bx;
    const ez = along < 0 ? pz : z - this.bz;
    return ex * ex + ez * ez <= this.halfWidth * this.halfWidth;
  }
  draw(pen) {
    const nx = -this.uz * this.halfWidth;
    const nz = this.ux * this.halfWidth;
    pen.line(this.ax + nx, this.az + nz, this.bx + nx, this.bz + nz);
    pen.line(this.ax - nx, this.az - nz, this.bx - nx, this.bz - nz);
    const inner = Math.max(0, Math.floor(this.halfWidth / 0.9) - 1);
    for (let i = 0; i <= inner; i++) {
      const k = inner === 0 ? 0 : i / inner * 2 - 1;
      const f = k * 0.5;
      pen.line(this.ax + nx * f, this.az + nz * f, this.bx + nx * f, this.bz + nz * f);
    }
  }
  sample(rng, n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const t = rng.next() * this.length;
      const w = rng.range(-this.halfWidth, this.halfWidth);
      out.push({ x: this.ax + this.ux * t - this.uz * w, z: this.az + this.uz * t + this.ux * w });
    }
    return out;
  }
};
var Polygon = class {
  constructor(pts) {
    this.pts = pts;
    this.cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
    this.cz = pts.reduce((s, p) => s + p.z, 0) / pts.length;
    this.reach = Math.max(...pts.map((p) => Math.hypot(p.x - this.cx, p.z - this.cz)));
  }
  contains(x, z) {
    let sign = 0;
    for (let i = 0; i < this.pts.length; i++) {
      const a = this.pts[i];
      const b = this.pts[(i + 1) % this.pts.length];
      const c = (b.x - a.x) * (z - a.z) - (b.z - a.z) * (x - a.x);
      if (Math.abs(c) < 1e-9) continue;
      const s = c > 0 ? 1 : -1;
      if (sign === 0) sign = s;
      else if (s !== sign) return false;
    }
    return true;
  }
  draw(pen) {
    for (let i = 0; i < this.pts.length; i++) {
      const a = this.pts[i];
      const b = this.pts[(i + 1) % this.pts.length];
      pen.line(a.x, a.z, b.x, b.z);
    }
  }
  sample(rng, n) {
    const out = [];
    let guard = n * 20;
    while (out.length < n && guard-- > 0) {
      const x = this.cx + rng.range(-this.reach, this.reach);
      const z = this.cz + rng.range(-this.reach, this.reach);
      if (this.contains(x, z)) out.push({ x, z });
    }
    return out;
  }
};
function rect(x0, z0, x1, z1) {
  return new Polygon([
    { x: x0, z: z0 },
    { x: x1, z: z0 },
    { x: x1, z: z1 },
    { x: x0, z: z1 }
  ]);
}

// src/core/arena.ts
var Arena = class {
  constructor(centre, stats) {
    this.cx = centre.x;
    this.cz = centre.z;
    this.floorY = centre.y;
    this.radius = stats.arenaRadius;
    this.square = stats.arenaShape === "square";
  }
  get centre() {
    return { x: this.cx, y: this.floorY, z: this.cz };
  }
  /** Is (x, z) within the arena, shrunk by `inset` (negative grows it)? */
  contains(x, z, inset = 0) {
    const r = this.radius - inset;
    const dx = x - this.cx;
    const dz = z - this.cz;
    return this.square ? Math.abs(dx) <= r && Math.abs(dz) <= r : dx * dx + dz * dz <= r * r;
  }
  /** Vertical band in which a player counts as "in the fight". */
  inBand(y) {
    return y >= this.floorY - CONFIG.encounter.floorBelow && y <= this.floorY + CONFIG.encounter.floorAbove;
  }
  /** Nearest point inside the arena shrunk by `inset`. */
  clampInside(x, z, inset = 0) {
    const r = Math.max(0, this.radius - inset);
    let dx = x - this.cx;
    let dz = z - this.cz;
    if (this.square) {
      dx = clamp(dx, -r, r);
      dz = clamp(dz, -r, r);
    } else {
      const d = Math.hypot(dx, dz);
      if (d > r && d > 1e-9) {
        dx *= r / d;
        dz *= r / d;
      }
    }
    return { x: this.cx + dx, z: this.cz + dz };
  }
  /** Point at bearing theta, `dist` blocks from the centre (clamped into the arena). */
  polar(theta, dist, inset = 0) {
    const d = thetaToDir(theta);
    return this.clampInside(this.cx + d.x * dist, this.cz + d.z * dist, inset);
  }
  /** Distance from the centre to the arena edge along bearing theta. */
  edgeDistance(theta) {
    if (!this.square) return this.radius;
    const d = thetaToDir(theta);
    const m = Math.max(Math.abs(d.x), Math.abs(d.z));
    return m > 1e-9 ? this.radius / m : this.radius;
  }
  /** Uniform random point inside, at least `inset` from the edge and outside every `avoid` circle. */
  randomPoint(rng, inset = 1, avoid = []) {
    const r = Math.max(0.5, this.radius - inset);
    for (let i = 0; i < 24; i++) {
      let x;
      let z;
      if (this.square) {
        x = this.cx + rng.range(-r, r);
        z = this.cz + rng.range(-r, r);
      } else {
        const a = rng.range(0, Math.PI * 2);
        const d = Math.sqrt(rng.next()) * r;
        x = this.cx + Math.cos(a) * d;
        z = this.cz + Math.sin(a) * d;
      }
      if (avoid.every((c) => Math.hypot(x - c.x, z - c.z) >= c.r)) return { x, z };
    }
    return { x: this.cx, z: this.cz };
  }
  /** The arena footprint as a hazard shape (for "everything except ..." hazards). */
  bounds(inset = 0) {
    const r = this.radius - inset;
    return this.square ? rect(this.cx - r, this.cz - r, this.cx + r, this.cz + r) : new Circle(this.cx, this.cz, r);
  }
  at(p, lift = 0) {
    return { x: p.x, y: this.floorY + lift, z: p.z };
  }
  /**
   * Check that a location can host this boss WITHOUT changing a single block:
   * enough solid floor at one level, free air above it, and head room at the centre.
   */
  static scan(dim, centre, stats) {
    const fy = Math.floor(centre.y);
    const r = stats.arenaRadius;
    const step = 3;
    let total = 0;
    let good = 0;
    try {
      for (let dx = -r; dx <= r; dx += step) {
        for (let dz = -r; dz <= r; dz += step) {
          if (stats.arenaShape === "circle" && dx * dx + dz * dz > r * r) continue;
          total++;
          const x = Math.floor(centre.x + dx);
          const z = Math.floor(centre.z + dz);
          const floor = dim.getBlock({ x, y: fy - 1, z });
          const feet = dim.getBlock({ x, y: fy, z });
          const head = dim.getBlock({ x, y: fy + 1, z });
          if (!floor || !feet || !head) return { ok: false, coverage: 0, ceilingClear: false, loaded: false, reason: "unloaded" };
          if (!floor.isAir && !floor.isLiquid && feet.isAir && head.isAir) good++;
        }
      }
      let clear = true;
      for (let dy = 0; dy < stats.clearance && clear; dy++) {
        for (const [ox, oz] of [[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2]]) {
          const b = dim.getBlock({ x: Math.floor(centre.x) + ox, y: fy + dy, z: Math.floor(centre.z) + oz });
          if (!b || !b.isAir) {
            clear = false;
            break;
          }
        }
      }
      const coverage = total > 0 ? good / total : 0;
      const ok2 = clear && coverage >= CONFIG.encounter.minFloorCoverage;
      return {
        ok: ok2,
        coverage,
        ceilingClear: clear,
        loaded: true,
        reason: ok2 ? void 0 : !clear ? "ceiling" : "floor"
      };
    } catch {
      return { ok: false, coverage: 0, ceilingClear: false, loaded: false, reason: "unloaded" };
    }
  }
};

// src/core/encounter.ts
import { Player as Player3 } from "@minecraft/server";

// src/core/audio.ts
var Audio = class {
  constructor(dim) {
    this.dim = dim;
  }
  play(id, pos, volume = 1, pitch = 1) {
    try {
      this.dim.playSound(id, pos, { volume, pitch });
    } catch {
    }
  }
};

// src/core/trace.ts
var sink;
function current() {
  return sink ?? globalThis.__abmTrace;
}
function trace(kind, data = {}) {
  const s = current();
  if (s) s(kind, data);
  else if (CONFIG.debug && kind !== "hazard") console.warn(`[abm] ${kind} ${JSON.stringify(data)}`);
}
function tracing() {
  return current() !== void 0;
}
function report(where, err) {
  const msg = err instanceof Error ? `${err.message}
${err.stack ?? ""}` : String(err);
  const s = current();
  if (s) s("error", { where, msg });
  console.warn(`[abm] error in ${where}: ${msg}`);
}

// src/core/stateMachine.ts
var TOP_EDGES = {
  ["INTRO" /* Intro */]: ["PHASE_1" /* Phase1 */, "PHASE_2" /* Phase2 */, "DEATH" /* Death */],
  ["PHASE_1" /* Phase1 */]: ["PHASE_TRANSITION" /* Transition */, "DEATH" /* Death */],
  ["PHASE_TRANSITION" /* Transition */]: ["PHASE_2" /* Phase2 */, "DEATH" /* Death */],
  ["PHASE_2" /* Phase2 */]: ["DEATH" /* Death */],
  ["DEATH" /* Death */]: []
};
var SUB_EDGES = {
  ["IDLE" /* Idle */]: ["POSITIONING" /* Positioning */, "TELEGRAPH" /* Telegraph */, "STAGGER" /* Stagger */, "RESET" /* Reset */],
  ["POSITIONING" /* Positioning */]: ["IDLE" /* Idle */, "TELEGRAPH" /* Telegraph */, "STAGGER" /* Stagger */, "RESET" /* Reset */],
  ["TELEGRAPH" /* Telegraph */]: ["ATTACK" /* Attack */, "RECOVERY" /* Recovery */, "IDLE" /* Idle */, "STAGGER" /* Stagger */, "RESET" /* Reset */],
  ["ATTACK" /* Attack */]: ["RECOVERY" /* Recovery */, "IDLE" /* Idle */, "STAGGER" /* Stagger */, "RESET" /* Reset */],
  ["RECOVERY" /* Recovery */]: ["IDLE" /* Idle */, "STAGGER" /* Stagger */, "RESET" /* Reset */],
  ["STAGGER" /* Stagger */]: ["IDLE" /* Idle */, "RESET" /* Reset */],
  ["RESET" /* Reset */]: ["IDLE" /* Idle */]
};
var BossStateMachine = class {
  constructor(label) {
    this.label = label;
    this.top = "INTRO" /* Intro */;
    this.sub = "IDLE" /* Idle */;
    this.topSince = 0;
    this.subSince = 0;
    /** Ordered record of top-level states visited (asserted on by tests). */
    this.history = ["INTRO" /* Intro */];
  }
  get inCombat() {
    return this.top === "PHASE_1" /* Phase1 */ || this.top === "PHASE_2" /* Phase2 */;
  }
  /** Busy executing an attack (cannot start another). */
  get busy() {
    return this.sub === "TELEGRAPH" /* Telegraph */ || this.sub === "ATTACK" /* Attack */ || this.sub === "RECOVERY" /* Recovery */;
  }
  setTop(next, now) {
    if (next === this.top) return true;
    if (!TOP_EDGES[this.top].includes(next)) {
      report("state machine", new Error(`${this.label}: illegal ${this.top} -> ${next}`));
      return false;
    }
    trace("top", { boss: this.label, from: this.top, to: next, tick: now });
    this.top = next;
    this.topSince = now;
    this.history.push(next);
    this.sub = "IDLE" /* Idle */;
    this.subSince = now;
    return true;
  }
  setSub(next, now) {
    if (next === this.sub) return true;
    if (!SUB_EDGES[this.sub].includes(next)) {
      report("state machine", new Error(`${this.label}: illegal substate ${this.sub} -> ${next}`));
      return false;
    }
    this.sub = next;
    this.subSince = now;
    return true;
  }
  /** Restore after a world reload: adopt a phase without replaying the intro. */
  restore(phase, now) {
    this.top = phase === 2 ? "PHASE_2" /* Phase2 */ : "PHASE_1" /* Phase1 */;
    this.sub = "IDLE" /* Idle */;
    this.topSince = this.subSince = now;
    this.history.push(this.top);
  }
};

// src/core/boss.ts
var AttackRun = class {
  constructor(enc, def, seq) {
    this.enc = enc;
    this.def = def;
    this.seq = seq;
    this.cancelled = false;
    this.declared = false;
    /** Total length in ticks, known after windows(). */
    this.total = 0;
    this.tag = `atk${seq}`;
    this.t0 = enc.timeline.now;
    this.target = enc.targeting.primary(this.t0);
  }
  get phase() {
    return this.enc.phase;
  }
  get hasWindows() {
    return this.declared;
  }
  /** Run `fn` `tick` ticks after the attack started (tick 0 runs immediately). */
  at(tick, fn) {
    if (tick <= 0) {
      try {
        fn();
      } catch (e) {
        report(`attack ${this.def.id}`, e);
      }
      return;
    }
    this.enc.timeline.at(this.t0 + tick, fn, this.tag);
  }
  /**
   * Declare the attack's state windows. The boss is in TELEGRAPH for `telegraph`
   * ticks, ATTACK for `active`, RECOVERY for `recovery`, then returns to IDLE.
   */
  windows(telegraph, active, recovery) {
    if (this.declared) throw new Error(`${this.def.id}: windows() called twice`);
    this.declared = true;
    this.total = telegraph + active + recovery;
    const now = () => this.enc.timeline.now;
    this.at(telegraph, () => this.enc.sm.setSub("ATTACK" /* Attack */, now()));
    this.at(telegraph + active, () => this.enc.sm.setSub("RECOVERY" /* Recovery */, now()));
    this.at(this.total, () => this.enc.finishAttack(this));
  }
  /** Telegraph a region at `at - warn` and strike it at `at` (attack-relative ticks). */
  strike(at, o) {
    const begin = Math.max(0, at - o.warn);
    this.at(begin, () => this.enc.hazards.strike({ ...o, warn: at - begin, tag: this.tag, label: o.label ?? this.def.id }));
  }
  /** Pick the client animation variant for this run (0..3). */
  variant(n) {
    this.enc.setProp("abm:variant", n);
  }
};
var BossController = class {
  constructor(enc) {
    this.enc = enc;
    this.experience = 500;
  }
  /** Called every tick in every state (special systems: histories, rhythms, trackers). */
  tick() {
  }
  /** Phase II has just become active. */
  phase2Ready() {
  }
  /**
   * Adjust damage about to be dealt to the boss. Runs inside a before-event:
   * it may read the world and change controller state, but anything that
   * changes the world (particles, properties, sounds) must go through enc.defer().
   */
  incoming(damage, _info) {
    return damage;
  }
  onHelperGone(_h) {
  }
  /** The current attack was cut short (stagger, phase change, reset, death). */
  onAttackCancelled(_def) {
  }
  /** Boss-specific values to persist (e.g. armour states). */
  extra() {
    return {};
  }
  restore(_extra) {
  }
  /** Release everything the controller holds. Called once when the encounter ends. */
  cleanup() {
  }
};

// src/core/damage.ts
import {
  EntityComponentTypes,
  EntityDamageCause,
  EquipmentSlot,
  GameMode
} from "@minecraft/server";
var ARMOR_SLOTS = [EquipmentSlot.Head, EquipmentSlot.Chest, EquipmentSlot.Legs, EquipmentSlot.Feet];
function mitigation(p) {
  const d = CONFIG.damage;
  let armor = 0;
  let prot = 0;
  try {
    const eq = p.getComponent(EntityComponentTypes.Equippable);
    if (eq) {
      armor = eq.totalArmor;
      for (const slot of ARMOR_SLOTS) {
        const item = eq.getEquipment(slot);
        const ench = item?.getComponent("minecraft:enchantable");
        prot += ench?.getEnchantment("protection")?.level ?? 0;
      }
    }
  } catch {
  }
  let m = Math.min(d.armorCap, armor * d.armorPerPoint) + Math.min(d.protectionCap, prot * d.protectionPerLevel);
  let res = 0;
  try {
    const e = p.getEffect("resistance");
    if (e) res = Math.min(d.resistanceCap, (e.amplifier + 1) * d.resistancePerLevel);
  } catch {
    res = 0;
  }
  m = 1 - (1 - m) * (1 - res);
  return Math.min(1 - d.minShare, Math.max(0, m));
}
var DamageSystem = class {
  constructor(source) {
    this.source = source;
    this.lastHit = /* @__PURE__ */ new Map();
    /** Running totals for telemetry / tests. */
    this.hits = 0;
    this.totalDealt = 0;
  }
  canHit(p, now) {
    const last = this.lastHit.get(p.id);
    return last === void 0 || now - last >= CONFIG.encounter.playerHitIntervalTicks;
  }
  /** Apply a hazard hit. Returns the health actually removed (0 when nothing happened). */
  hit(p, spec, now) {
    if (!p.isValid || !this.canHit(p, now)) return 0;
    let mode;
    try {
      mode = p.getGameMode();
    } catch {
      return 0;
    }
    if (mode === GameMode.Creative || mode === GameMode.Spectator) return 0;
    const health = p.getComponent("minecraft:health");
    if (!health || health.currentValue <= 0) return 0;
    const final = Math.max(0.5, spec.damage * difficulty().damage * (1 - mitigation(p)));
    const before = health.currentValue;
    const src = this.source();
    const cause = spec.blockable ? EntityDamageCause.entityAttack : EntityDamageCause.magic;
    const opts = src && src.isValid ? { cause, damagingEntity: src } : { cause };
    let dealt = 0;
    try {
      if (final >= before) {
        if (!p.applyDamage(1e5, opts)) return 0;
        dealt = before;
      } else {
        if (!p.applyDamage(1, opts)) return 0;
        health.setCurrentValue(Math.max(0.5, before - final));
        dealt = final;
      }
    } catch {
      return 0;
    }
    this.lastHit.set(p.id, now);
    this.hits++;
    this.totalDealt += dealt;
    if (spec.knock || spec.knockUp) {
      const o = spec.from ?? (src && src.isValid ? src.location : p.location);
      const d = normXZ(p.location.x - o.x, p.location.z - o.z);
      try {
        p.applyKnockback({ x: d.x * (spec.knock ?? 0), z: d.z * (spec.knock ?? 0) }, spec.knockUp ?? 0);
      } catch {
      }
    }
    if (spec.effects && final < before) {
      for (const e of spec.effects) {
        try {
          p.addEffect(e.id, e.ticks, { amplifier: e.amp ?? 0, showParticles: true });
        } catch {
        }
      }
    }
    trace("player_hit", { player: p.name, dealt, design: spec.damage, label: spec.label ?? "" });
    return dealt;
  }
  forget(playerId) {
    this.lastHit.delete(playerId);
  }
  clear() {
    this.lastHit.clear();
  }
};

// src/core/hazards.ts
var HazardSystem = class {
  constructor(enc) {
    this.enc = enc;
    /** Strikes resolved so far (telemetry). */
    this.resolved = 0;
  }
  get y() {
    return this.enc.arena.floorY + 0.08;
  }
  /** Draw a region on the floor for `ticks`, without any damage. */
  telegraph(shape, ticks, safe = false) {
    const v = this.enc.visuals;
    const style = this.enc.controller.style;
    shape.draw(safe ? v.safePen(style, this.y, ticks / 20) : v.dangerPen(style, this.y, ticks / 20));
  }
  /** Draw a region with a specific arc particle (decorative variants of a telegraph). */
  telegraphWith(arcParticle, shape, ticks) {
    const style = this.enc.controller.style;
    shape.draw(this.enc.visuals.pen(style.line, arcParticle, void 0, this.y, ticks / 20));
  }
  /** Players standing in `shape` right now. */
  inside(shape, filter) {
    const out = [];
    for (const p of this.enc.targeting.participants()) {
      const l = p.location;
      if (!this.enc.arena.inBand(l.y)) continue;
      if (filter && !filter(p)) continue;
      if (shape.contains(l.x, l.z)) out.push(p);
    }
    return out;
  }
  /** Damage everyone inside `shape` immediately. */
  resolve(shape, spec, filter) {
    const victims = [];
    for (const p of this.inside(shape, filter)) {
      if (this.enc.damage.hit(p, spec, this.enc.timeline.now) > 0) victims.push(p);
    }
    this.resolved++;
    return victims;
  }
  /** Telegraph a region now and strike it after `warn` ticks. */
  strike(o) {
    if (!o.quiet) this.telegraph(o.shape, o.warn, o.safe);
    if (tracing()) trace("hazard", { kind: "strike", shape: o.shape, at: this.enc.timeline.now + Math.max(1, Math.round(o.warn)), tag: o.tag, label: o.label ?? "", enc: this.enc });
    this.enc.timeline.after(
      o.warn,
      () => {
        if (o.condition && !o.condition()) {
          trace("strike_fizzled", { tag: o.tag, label: o.label ?? "" });
          return;
        }
        const victims = this.resolve(o.shape, o, o.filter);
        if (o.fx) {
          this.enc.visuals.scatter(this.enc.controller.style.strike, o.shape.sample(this.enc.rng, o.fx), this.y + 0.2);
        }
        if (o.sound) this.enc.audio.play(o.sound, { x: o.shape.cx, y: this.y, z: o.shape.cz });
        trace("strike", { tag: o.tag, label: o.label ?? "", victims: victims.length });
        o.onStrike?.(victims);
      },
      o.tag
    );
  }
  /** A region that moves or changes over time (waves, sweeping limbs, closing walls). */
  sweep(o) {
    const every = Math.max(1, o.every ?? 2);
    const once = o.once !== false;
    const draw = o.draw !== false;
    const hit = /* @__PURE__ */ new Set();
    if (o.warn > 0) this.telegraph(o.shapeAt(0), o.warn);
    if (tracing()) trace("hazard", { kind: "sweep", shapeAt: o.shapeAt, start: this.enc.timeline.now + o.warn, duration: o.duration, every, tag: o.tag, label: o.label ?? "", enc: this.enc });
    for (let t = 0; t <= o.duration; t += every) {
      this.enc.timeline.after(
        o.warn + t,
        () => {
          const shape = o.shapeAt(t);
          if (draw) this.telegraph(shape, every + 1);
          if (t === 0 && o.sound) this.enc.audio.play(o.sound, { x: shape.cx, y: this.y, z: shape.cz });
          for (const p of this.inside(shape)) {
            if (once && hit.has(p.id)) continue;
            if (this.enc.damage.hit(p, o, this.enc.timeline.now) > 0) {
              hit.add(p.id);
              o.onHit?.(p);
            }
          }
          if (o.fx && t % (every * 2) === 0) {
            this.enc.visuals.scatter(this.enc.controller.style.strike, shape.sample(this.enc.rng, o.fx), this.y + 0.2);
          }
          if (t + every > o.duration) {
            this.resolved++;
            trace("strike", { tag: o.tag, label: o.label ?? "", victims: hit.size });
          }
        },
        o.tag
      );
    }
  }
  /**
   * A straight-flying projectile. The sprite is a client particle moving at the
   * same constant velocity the server uses for the collision circle.
   */
  projectile(o) {
    const life = Math.max(1, Math.round(o.range / o.speed));
    const hit = /* @__PURE__ */ new Set();
    if (o.markPath !== false && o.delay > 2) {
      this.telegraph(new Lane(o.from.x, o.from.z, o.from.x + o.dir.x * o.range, o.from.z + o.dir.z * o.range, o.radius), o.delay);
    }
    if (tracing()) {
      trace("hazard", {
        kind: "sweep",
        start: this.enc.timeline.now + Math.max(1, o.delay) + 1,
        duration: life - 1,
        every: 1,
        tag: o.tag,
        label: o.label ?? "",
        enc: this.enc,
        shapeAt: (t) => new Circle(o.from.x + o.dir.x * o.speed * (t + 1), o.from.z + o.dir.z * o.speed * (t + 1), o.radius)
      });
    }
    this.enc.timeline.after(
      Math.max(1, o.delay),
      () => {
        this.enc.visuals.flyer(o.particle, o.from, { x: o.dir.x, y: 0, z: o.dir.z }, o.speed * 20, life / 20);
        if (o.sound) this.enc.audio.play(o.sound, o.from);
      },
      o.tag
    );
    for (let t = 1; t <= life; t++) {
      this.enc.timeline.after(
        Math.max(1, o.delay) + t,
        () => {
          const c = new Circle(o.from.x + o.dir.x * o.speed * t, o.from.z + o.dir.z * o.speed * t, o.radius);
          if (!this.enc.arena.contains(c.cx, c.cz, -2)) return;
          for (const p of this.inside(c)) {
            if (hit.has(p.id)) continue;
            if (this.enc.damage.hit(p, o, this.enc.timeline.now) > 0) {
              hit.add(p.id);
              o.onHit?.(p);
            }
          }
          if (t === life) {
            this.resolved++;
            trace("strike", { tag: o.tag, label: o.label ?? "", victims: hit.size });
          }
        },
        o.tag
      );
    }
  }
};

// src/core/helpers.ts
var HELPER_TAG = "abm_helper";
var OWNER_PROP = "abm:owner";
var Helpers = class {
  constructor(enc) {
    this.enc = enc;
    this.items = [];
    /** Total helpers ever spawned (telemetry). */
    this.spawned = 0;
  }
  spawn(typeId, pos, kind, opts = {}) {
    if (this.items.length >= CONFIG.encounter.maxHelpers) return void 0;
    let e;
    try {
      e = this.enc.dim.spawnEntity(typeId, pos, { initialRotation: opts.yaw ?? 0 });
      e.addTag(HELPER_TAG);
      e.setDynamicProperty(OWNER_PROP, this.enc.bossId);
    } catch {
      return void 0;
    }
    const now = this.enc.timeline.now;
    const h = {
      entity: e,
      id: e.id,
      kind,
      born: now,
      expires: opts.lifetime ? now + opts.lifetime : Infinity,
      killed: false,
      data: opts.data ?? {}
    };
    this.items.push(h);
    this.spawned++;
    trace("helper_spawn", { boss: this.enc.key, kind });
    return h;
  }
  of(kind) {
    return this.items.filter((h) => h.kind === kind && h.entity.isValid);
  }
  count(kind) {
    return this.items.filter((h) => (kind === void 0 || h.kind === kind) && h.entity.isValid).length;
  }
  /** Called by the manager when any entity dies. */
  notifyDied(entityId) {
    const h = this.items.find((i) => i.id === entityId);
    if (h) h.killed = true;
  }
  owns(entityId) {
    return this.items.some((i) => i.id === entityId);
  }
  discard(h) {
    try {
      if (h.entity.isValid) h.entity.remove();
    } catch {
    }
  }
  remove(h) {
    this.items = this.items.filter((i) => i !== h);
    this.discard(h);
  }
  removeKind(kind) {
    for (const h of this.items.filter((i) => i.kind === kind)) this.remove(h);
  }
  removeAll() {
    for (const h of this.items) this.discard(h);
    this.items = [];
  }
  /** Expire, prune and report losses. */
  tick() {
    const now = this.enc.timeline.now;
    const gone = [];
    this.items = this.items.filter((h) => {
      if (!h.entity.isValid) {
        gone.push(h);
        return false;
      }
      if (now >= h.expires) {
        this.discard(h);
        gone.push(h);
        return false;
      }
      return true;
    });
    for (const h of gone) {
      trace("helper_gone", { boss: this.enc.key, kind: h.kind, killed: h.killed });
      this.enc.controller.onHelperGone(h);
    }
  }
};

// src/core/hud.ts
function renderHud(enc) {
  if (!CONFIG.hud.actionBar) return;
  const hp = Math.max(0, Math.ceil(enc.effectiveHealth()));
  const max = Math.ceil(enc.effectiveMaxHealth());
  let phase;
  switch (enc.sm.top) {
    case "INTRO" /* Intro */:
      phase = "§7Awakening";
      break;
    case "PHASE_1" /* Phase1 */:
      phase = "§fPhase I";
      break;
    case "PHASE_TRANSITION" /* Transition */:
      phase = "§6" + enc.controller.phase2Name;
      break;
    case "PHASE_2" /* Phase2 */:
      phase = "§cPhase II";
      break;
    default:
      phase = "§8Fallen";
  }
  const act = enc.currentAttackName ? ` §7| §e${enc.currentAttackName}` : "";
  const text = `§l${enc.controller.displayName}§r §7| ${phase} §7| §c${hp}§7/${max}${act}`;
  for (const p of enc.targeting.participants()) {
    try {
      p.onScreenDisplay.setActionBar(text);
    } catch {
    }
  }
}
function clearHud(enc) {
  if (!CONFIG.hud.actionBar) return;
  for (const p of enc.targeting.participants()) {
    try {
      p.onScreenDisplay.setActionBar("");
    } catch {
    }
  }
}

// src/core/locomotion.ts
var Locomotion = class {
  constructor(enc) {
    this.enc = enc;
    /** Blocks per tick while walking. */
    this.speed = 0.1;
    /** Degrees per tick. */
    this.turnRate = 4;
    this.anim = 0 /* Idle */;
    this.moving = false;
    this.progress = { x: 0, z: 0, tick: 0 };
    let y = 0;
    try {
      y = enc.boss.getRotation().y;
    } catch {
      y = 0;
    }
    this.yaw = wrapDeg(y);
    const l = enc.boss.location;
    this.progress = { x: l.x, z: l.z, tick: 0 };
  }
  setAnim(a) {
    if (a === this.anim) return;
    this.anim = a;
    this.enc.setProp("abm:move", a);
  }
  applyYaw() {
    try {
      this.enc.boss.setRotation({ x: 0, y: this.yaw });
    } catch {
    }
  }
  /** Turn towards `yaw`; returns true once aligned within `tolerance` degrees. */
  turnToward(yaw, tolerance = 2, rate = this.turnRate) {
    const d = angDiff(this.yaw, yaw);
    if (Math.abs(d) <= tolerance) {
      if (!this.moving) this.setAnim(0 /* Idle */);
      return true;
    }
    this.yaw = approachAngle(this.yaw, yaw, rate);
    this.applyYaw();
    if (!this.moving) this.setAnim(d > 0 ? 3 /* TurnRight */ : 2 /* TurnLeft */);
    return Math.abs(angDiff(this.yaw, yaw)) <= tolerance;
  }
  /** Snap the body to face a yaw exactly (used when an attack commits to a direction). */
  face(yaw) {
    this.yaw = wrapDeg(yaw);
    try {
      this.enc.boss.teleport(this.enc.boss.location, { rotation: { x: 0, y: this.yaw }, keepVelocity: false });
    } catch {
      this.applyYaw();
    }
  }
  facePoint(p) {
    const l = this.enc.boss.location;
    if (Math.hypot(p.x - l.x, p.z - l.z) > 0.01) this.face(dirToYaw(p.x - l.x, p.z - l.z));
  }
  yawTo(p) {
    const l = this.enc.boss.location;
    return dirToYaw(p.x - l.x, p.z - l.z);
  }
  /**
   * Walk towards `goal` (clamped to the boss leash). Call every tick while positioning.
   * Returns the remaining distance.
   */
  goTo(goal, stopWithin = 0.5) {
    const boss = this.enc.boss;
    const g = this.enc.arena.clampInside(goal.x, goal.z, this.enc.stats.leashInset);
    const l = boss.location;
    const dx = g.x - l.x;
    const dz = g.z - l.z;
    const d = Math.hypot(dx, dz);
    if (d <= stopWithin) {
      this.halt();
      return d;
    }
    const want = dirToYaw(dx, dz);
    const off = Math.abs(angDiff(this.yaw, want));
    this.yaw = approachAngle(this.yaw, want, this.turnRate);
    this.applyYaw();
    if (off > 55) {
      this.stopVelocity();
      this.moving = false;
      this.setAnim(angDiff(this.yaw, want) > 0 ? 3 /* TurnRight */ : 2 /* TurnLeft */);
      return d;
    }
    const k = off > 25 ? 0.55 : 1;
    const f = yawToDir(this.yaw);
    const step = Math.min(this.speed * k, d);
    this.moving = true;
    this.setAnim(1 /* Walk */);
    try {
      if (CONFIG.movement.mode === "impulse") {
        const v = boss.getVelocity();
        boss.applyImpulse({ x: f.x * step - v.x, y: 0, z: f.z * step - v.z });
      } else {
        boss.tryTeleport(
          { x: l.x + f.x * step, y: l.y, z: l.z + f.z * step },
          { rotation: { x: 0, y: this.yaw }, checkForBlocks: true }
        );
      }
    } catch {
    }
    this.watchProgress(g);
    return d;
  }
  stopVelocity() {
    if (CONFIG.movement.mode !== "impulse") return;
    try {
      const v = this.enc.boss.getVelocity();
      if (Math.abs(v.x) + Math.abs(v.z) > 1e-4) this.enc.boss.applyImpulse({ x: -v.x, y: 0, z: -v.z });
    } catch {
    }
  }
  /** Stop walking and settle into the idle stance. */
  halt() {
    if (this.moving) this.stopVelocity();
    this.moving = false;
    this.setAnim(0 /* Idle */);
  }
  /** Something blocks the way: after ~2 s without progress, hop a short validated step. */
  watchProgress(goal) {
    const now = this.enc.timeline.now;
    const l = this.enc.boss.location;
    if (Math.hypot(l.x - this.progress.x, l.z - this.progress.z) > 0.6) {
      this.progress = { x: l.x, z: l.z, tick: now };
      return;
    }
    if (now - this.progress.tick < 40) return;
    this.progress = { x: l.x, z: l.z, tick: now };
    const d = Math.hypot(goal.x - l.x, goal.z - l.z) || 1;
    this.relocate({ x: l.x + (goal.x - l.x) / d * 1.5, z: l.z + (goal.z - l.z) / d * 1.5 });
  }
  /** Is there standing room for the boss at (x, z) on the arena floor? */
  canStand(p) {
    if (!this.enc.arena.contains(p.x, p.z, this.enc.stats.leashInset - 0.5)) return false;
    try {
      const y = Math.floor(this.enc.arena.floorY);
      const x = Math.floor(p.x);
      const z = Math.floor(p.z);
      const floor = this.enc.dim.getBlock({ x, y: y - 1, z });
      const feet = this.enc.dim.getBlock({ x, y, z });
      const head = this.enc.dim.getBlock({ x, y: y + 2, z });
      return !!floor && !!feet && !!head && !floor.isAir && feet.isAir && head.isAir;
    } catch {
      return false;
    }
  }
  /**
   * Place the boss at a validated floor position (gate / exchange arrivals, unstick).
   * Returns false and leaves the boss where it is when the destination is not safe.
   */
  relocate(p, yaw) {
    const g = this.enc.arena.clampInside(p.x, p.z, this.enc.stats.leashInset);
    if (!this.canStand(g)) return false;
    if (yaw !== void 0) this.yaw = wrapDeg(yaw);
    try {
      this.enc.boss.teleport(
        { x: g.x, y: this.enc.arena.floorY + 0.05, z: g.z },
        { rotation: { x: 0, y: this.yaw }, keepVelocity: false }
      );
    } catch {
      return false;
    }
    const l = this.enc.boss.location;
    this.progress = { x: l.x, z: l.z, tick: this.enc.timeline.now };
    return true;
  }
  /** Per-tick safety net: a boss that left the arena volume is brought back. */
  enforceLeash() {
    const l = this.enc.boss.location;
    const a = this.enc.arena;
    const out = !a.contains(l.x, l.z, this.enc.stats.leashInset - 3) || l.y < a.floorY - 4 || l.y > a.floorY + 8;
    if (!out) return;
    const back = a.clampInside(l.x, l.z, this.enc.stats.leashInset + 1);
    if (!this.relocate(back)) this.relocate({ x: a.cx, z: a.cz });
  }
};

// src/core/persistence.ts
import { world } from "@minecraft/server";
var REC_PROP = "abm:rec";
var SETTINGS_PROP = "abm:settings";
var REMNANT_TAG = "abm_remnant";
function saveRecord(boss, rec) {
  try {
    boss.setDynamicProperty(REC_PROP, JSON.stringify(rec));
  } catch (e) {
    report("saveRecord", e);
  }
}
function loadRecord(boss) {
  try {
    const raw = boss.getDynamicProperty(REC_PROP);
    if (typeof raw !== "string") return void 0;
    const rec = JSON.parse(raw);
    if (rec && rec.v === 1 && typeof rec.cx === "number") return rec;
  } catch {
  }
  return void 0;
}
function loadSettings() {
  try {
    const raw = world.getDynamicProperty(SETTINGS_PROP);
    if (typeof raw === "string") applySettings(JSON.parse(raw));
  } catch (e) {
    report("loadSettings", e);
  }
}
function saveSettings() {
  try {
    world.setDynamicProperty(SETTINGS_PROP, JSON.stringify(exportSettings()));
  } catch (e) {
    report("saveSettings", e);
  }
}

// src/core/rewards.ts
import { ItemStack, world as world2 } from "@minecraft/server";
function grantRewards(enc) {
  const c = enc.controller;
  const centre = enc.arena.at({ x: enc.arena.cx, z: enc.arena.cz }, 1.2);
  const fighters = world2.getAllPlayers().filter((p) => enc.targeting.contributors.has(p.id) || enc.targeting.everSeen.has(p.id));
  const trophies = Math.max(1, Math.min(4, enc.targeting.contributors.size || 1));
  try {
    for (let i = 0; i < trophies; i++) {
      enc.dim.spawnItem(new ItemStack(c.trophyItem, 1), { x: centre.x + (i - (trophies - 1) / 2) * 0.6, y: centre.y, z: centre.z });
    }
  } catch (e) {
    report("rewards.trophy", e);
  }
  try {
    enc.dim.runCommand(`loot spawn ${centre.x.toFixed(1)} ${centre.y.toFixed(1)} ${centre.z.toFixed(1)} loot "abm/${enc.key}"`);
  } catch (e) {
    report("rewards.loot", e);
  }
  for (const p of fighters) {
    try {
      p.addExperience(c.experience);
      p.sendMessage({ rawtext: [{ translate: `abm.defeat.${enc.key}` }] });
    } catch {
    }
  }
  trace("rewards", { boss: enc.key, trophies, fighters: fighters.length });
}

// src/core/scheduler.ts
var HISTORY = 4;
var AttackScheduler = class {
  constructor(enc) {
    this.enc = enc;
    this.readyAt = /* @__PURE__ */ new Map();
    this.lastUsed = /* @__PURE__ */ new Map();
    this.recent = [];
    /** Executions per attack id (asserted on by tests). */
    this.usage = /* @__PURE__ */ new Map();
  }
  cooldownOf(a) {
    const cd = typeof a.cooldown === "number" ? a.cooldown : a.cooldown[this.enc.phase - 1];
    return Math.round(cd * (a.ultimate ? 1 : difficulty().attackGap));
  }
  ready(a) {
    return this.enc.timeline.now >= (this.readyAt.get(a.id) ?? 0);
  }
  /** Delay the first use of an attack (e.g. ultimates at fight start and after a phase change). */
  hold(a, ticks) {
    this.readyAt.set(a.id, Math.max(this.readyAt.get(a.id) ?? 0, this.enc.timeline.now + ticks));
  }
  choose(attacks) {
    const now = this.enc.timeline.now;
    if (this.forced) {
      const f = attacks.find((a) => a.id === this.forced);
      this.forced = void 0;
      if (f) return f;
    }
    const pick = this.enc.rng.weighted(attacks, (a) => {
      if (!this.ready(a)) return 0;
      let w = a.weight(this.enc);
      if (w <= 0) return 0;
      const last = this.recent[this.recent.length - 1];
      if (a.id === last) w *= 0.12;
      else if (this.recent.includes(a.id)) w *= 0.55;
      const idle = now - (this.lastUsed.get(a.id) ?? -600);
      w *= 1 + Math.min(1.5, idle / 800);
      return w;
    });
    return pick;
  }
  commit(a) {
    const now = this.enc.timeline.now;
    this.readyAt.set(a.id, now + this.cooldownOf(a));
    this.lastUsed.set(a.id, now);
    this.recent.push(a.id);
    if (this.recent.length > HISTORY) this.recent.shift();
    this.usage.set(a.id, (this.usage.get(a.id) ?? 0) + 1);
    trace("attack", { boss: this.enc.key, id: a.id, phase: this.enc.phase, tick: now });
  }
  /** The attack has ended (finished or cancelled): its cooldown runs from now. */
  release(a) {
    this.readyAt.set(a.id, this.enc.timeline.now + this.cooldownOf(a));
  }
  /** After a phase change: shorten remaining cooldowns so the new phase opens actively. */
  refresh(maxRemaining) {
    const now = this.enc.timeline.now;
    for (const [id, at] of this.readyAt) this.readyAt.set(id, Math.min(at, now + maxRemaining));
    this.recent = [];
  }
};

// src/core/targeting.ts
import { GameMode as GameMode2 } from "@minecraft/server";
var REFRESH_TICKS = 5;
var SWITCH_DWELL_TICKS = 100;
var SWITCH_RATIO = 1.3;
function isAlivePlayer(p) {
  if (!p || !p.isValid) return false;
  const h = p.getComponent("minecraft:health");
  return !!h && h.currentValue > 0;
}
var Targeting = class {
  constructor(dim, arena) {
    this.dim = dim;
    this.arena = arena;
    this.list = [];
    this.threat = /* @__PURE__ */ new Map();
    this.lastSwitch = -9999;
    this.lastRefresh = -9999;
    /** Highest number of simultaneous participants seen (drives health scaling). */
    this.peak = 0;
    /** Every player id that has been a participant (for rewards). */
    this.everSeen = /* @__PURE__ */ new Set();
    /** Players who actually damaged the boss. */
    this.contributors = /* @__PURE__ */ new Set();
  }
  refresh(now, force = false) {
    if (!force && now - this.lastRefresh < REFRESH_TICKS) return;
    this.lastRefresh = now;
    const reach = (this.arena.square ? this.arena.radius * Math.SQRT2 : this.arena.radius) + CONFIG.encounter.arenaMargin;
    let found = [];
    try {
      found = this.dim.getPlayers({ location: this.arena.centre, maxDistance: reach + CONFIG.encounter.floorAbove });
    } catch {
      found = [];
    }
    this.list = found.filter((p) => this.isParticipant(p));
    for (const p of this.list) this.everSeen.add(p.id);
    if (this.list.length > this.peak) this.peak = this.list.length;
    for (const [id, t] of this.threat) {
      const nt = t * 0.992;
      if (nt < 0.05) this.threat.delete(id);
      else this.threat.set(id, nt);
    }
  }
  isParticipant(p) {
    if (!isAlivePlayer(p)) return false;
    let mode;
    try {
      mode = p.getGameMode();
    } catch {
      return false;
    }
    if (mode === GameMode2.Spectator) return false;
    const l = p.location;
    return this.arena.contains(l.x, l.z, -CONFIG.encounter.arenaMargin) && this.arena.inBand(l.y);
  }
  /** Live participants (validity re-checked, because players can leave between refreshes). */
  participants() {
    return this.list.filter((p) => isAlivePlayer(p));
  }
  count() {
    return this.participants().length;
  }
  addThreat(playerId, amount) {
    this.threat.set(playerId, (this.threat.get(playerId) ?? 0) + amount);
    this.contributors.add(playerId);
  }
  /** Current focus; re-evaluated with hysteresis. */
  primary(now) {
    const ps = this.participants();
    if (ps.length === 0) {
      this.primaryId = void 0;
      return void 0;
    }
    let cur = ps.find((p) => p.id === this.primaryId);
    const best = ps.reduce((a, b) => (this.threat.get(b.id) ?? 0) > (this.threat.get(a.id) ?? 0) ? b : a);
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
  focus(p, now) {
    this.primaryId = p.id;
    this.lastSwitch = now;
  }
  nearest(to) {
    const ps = this.participants();
    if (ps.length === 0) return void 0;
    return ps.reduce((a, b) => distXZ(b.location, to) < distXZ(a.location, to) ? b : a);
  }
  farthest(to) {
    const ps = this.participants();
    if (ps.length === 0) return void 0;
    return ps.reduce((a, b) => distXZ(b.location, to) > distXZ(a.location, to) ? b : a);
  }
  /** A participant other than `not`, falling back to `not` when alone. */
  other(rng, not) {
    const ps = this.participants();
    const rest = ps.filter((p) => p.id !== not?.id);
    if (rest.length > 0) return rng.pick(rest);
    return ps[0];
  }
  /** Up to `n` distinct participants, primary first. */
  several(rng, n, now) {
    const first = this.primary(now);
    const rest = rng.shuffle(this.participants().filter((p) => p.id !== first?.id));
    return (first ? [first, ...rest] : rest).slice(0, n);
  }
};

// src/core/timeline.ts
var Timeline = class {
  constructor() {
    /** Ticks processed by this encounter (not world time). */
    this.now = 0;
    this.tasks = [];
    this.seq = 0;
  }
  at(tick, fn, tag = "") {
    const t = { at: Math.max(this.now + 1, Math.round(tick)), seq: this.seq++, tag, fn };
    let i = this.tasks.length;
    while (i > 0 && this.tasks[i - 1].at > t.at) i--;
    this.tasks.splice(i, 0, t);
  }
  after(delay, fn, tag = "") {
    this.at(this.now + Math.max(1, Math.round(delay)), fn, tag);
  }
  /** Cancel every task whose tag equals `tag` or starts with `tag + ":"`. */
  cancel(tag) {
    const before = this.tasks.length;
    const prefix = tag + ":";
    this.tasks = this.tasks.filter((t) => t.tag !== tag && !t.tag.startsWith(prefix));
    return before - this.tasks.length;
  }
  cancelAll() {
    const n = this.tasks.length;
    this.tasks = [];
    return n;
  }
  pending(tag) {
    if (tag === void 0) return this.tasks.length;
    const prefix = tag + ":";
    return this.tasks.filter((t) => t.tag === tag || t.tag.startsWith(prefix)).length;
  }
  /** Advance one tick and run everything that is due. */
  step() {
    this.now++;
    let guard = 4096;
    while (this.tasks.length > 0 && this.tasks[0].at <= this.now && guard-- > 0) {
      const t = this.tasks.shift();
      try {
        t.fn();
      } catch (e) {
        report(`timeline task ${t.tag}`, e);
      }
    }
  }
};

// src/core/visuals.ts
import { MolangVariableMap } from "@minecraft/server";
var Visuals = class {
  constructor(dim) {
    this.dim = dim;
    this.thin = 0;
  }
  /** Spawn a particle that gameplay depends on (never thinned). */
  spawn(id, pos, vars) {
    try {
      this.dim.spawnParticle(id, pos, vars);
    } catch {
    }
  }
  /** Spawn a decorative particle, subject to the VFX density setting. */
  decor(id, pos, vars) {
    this.thin += CONFIG.vfx.density;
    if (this.thin < 1) return;
    this.thin -= 1;
    this.spawn(id, pos, vars);
  }
  /** Decorative particle at several points. */
  scatter(id, points, y) {
    for (const p of points) this.decor(id, { x: p.x, y, z: p.z });
  }
  /** A pen that draws on the floor at height y; marks last `seconds`. */
  pen(line, arc, disc, y, seconds) {
    const life = Math.max(0.1, seconds);
    return {
      line: (ax, az, bx, bz) => {
        const len = Math.hypot(bx - ax, bz - az);
        if (len < 0.05) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.dx", (bx - ax) / len);
        m.setFloat("variable.dz", (bz - az) / len);
        m.setFloat("variable.len", len);
        m.setFloat("variable.life", life);
        this.spawn(line, { x: ax, y, z: az }, m);
      },
      arc: (cx, cz, r, a0, sweep) => {
        if (r < 0.05 || Math.abs(sweep) < 0.5) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.r", r);
        m.setFloat("variable.a0", a0);
        m.setFloat("variable.sweep", sweep);
        m.setFloat("variable.life", life);
        this.spawn(arc, { x: cx, y, z: cz }, m);
      },
      disc: (cx, cz, r) => {
        if (!disc || r < 0.05) return;
        const m = new MolangVariableMap();
        m.setFloat("variable.r", r);
        m.setFloat("variable.life", life);
        this.spawn(disc, { x: cx, y: y - 0.02, z: cz }, m);
      }
    };
  }
  dangerPen(style, y, seconds) {
    return this.pen(style.line, style.arc, style.disc, y, seconds);
  }
  safePen(style, y, seconds) {
    return this.pen(style.safeLine, style.safeArc, void 0, y, seconds);
  }
  /**
   * Launch a projectile sprite that flies in a straight line at constant speed.
   * The caller mirrors the motion for collision (see HazardSystem.projectile).
   */
  flyer(id, from, dir, blocksPerSecond, seconds) {
    const m = new MolangVariableMap();
    m.setSpeedAndDirection("variable.dir", blocksPerSecond, dir);
    m.setFloat("variable.life", seconds);
    this.spawn(id, from, m);
  }
};

// src/core/encounter.ts
var IGNORED_CAUSES = /* @__PURE__ */ new Set([
  "fall",
  "suffocation",
  "drowning",
  "contact",
  "fire",
  "fireTick",
  "lava",
  "magma",
  "freezing",
  "lightning",
  "stalactite",
  "stalagmite",
  "flyIntoWall",
  "fallingBlock",
  "anvil",
  "campfire",
  "soulCampfire",
  "temperature",
  "piston",
  "starve",
  "wither"
]);
var EXPLOSION_CAUSES = /* @__PURE__ */ new Set(["blockExplosion", "entityExplosion", "fireworks"]);
var Encounter = class {
  constructor(boss, key, host, factory, record) {
    this.boss = boss;
    this.key = key;
    this.host = host;
    this.timeline = new Timeline();
    this.phase = 1;
    /** Effective HP = native HP * hpScale (multiplayer and difficulty). */
    this.hpScale = 1;
    this.currentAttackName = "";
    this.nextAttackAt = 0;
    this.ended = false;
    /** While true every hit on the boss is refused (intro, phase change, death). */
    this.invulnerable = true;
    this.runSeq = 0;
    this.pendingTransition = false;
    this.pendingDeath = false;
    this.emptySince = -1;
    this.staggerUntil = 0;
    this.deferred = [];
    this.props = /* @__PURE__ */ new Map();
    this.outsiderNote = /* @__PURE__ */ new Map();
    this.stats = CONFIG.bosses[key];
    this.bossId = boss.id;
    this.dim = boss.dimension;
    const l = boss.location;
    this.record = record ?? {
      v: 1,
      boss: key,
      cx: l.x,
      cy: l.y,
      cz: l.z,
      phase: 1,
      scale: 1,
      seed: hashString(boss.id) ^ Math.random() * 4294967295 >>> 0,
      engaged: false,
      extra: {}
    };
    this.arena = new Arena({ x: this.record.cx, y: this.record.cy, z: this.record.cz }, this.stats);
    this.sm = new BossStateMachine(key);
    this.rng = new Rng(this.record.seed);
    this.visuals = new Visuals(this.dim);
    this.audio = new Audio(this.dim);
    this.targeting = new Targeting(this.dim, this.arena);
    this.damage = new DamageSystem(() => this.boss.isValid ? this.boss : void 0);
    this.hazards = new HazardSystem(this);
    this.helpers = new Helpers(this);
    this.scheduler = new AttackScheduler(this);
    this.loco = new Locomotion(this);
    this.controller = factory(this);
    this.hpScale = this.record.scale > 0 ? this.record.scale : 1;
  }
  // ------------------------------------------------------------------ small utilities
  /** Set a synced entity property (skipped when unchanged). */
  setProp(name, value) {
    if (this.props.get(name) === value) return;
    this.props.set(name, value);
    try {
      this.boss.setProperty(name, value);
    } catch (e) {
      report(`setProperty ${name}`, e);
    }
  }
  setAnim(state, variant = 0) {
    this.setProp("abm:variant", variant);
    this.setProp("abm:anim", state);
  }
  /** Queue a world-changing action from a restricted (before-event) context. */
  defer(fn) {
    this.deferred.push(fn);
  }
  health() {
    return this.boss.getComponent("minecraft:health");
  }
  effectiveHealth() {
    if (this.pendingDeath || this.sm.top === "DEATH" /* Death */) return 0;
    return (this.health()?.currentValue ?? 0) * this.hpScale;
  }
  effectiveMaxHealth() {
    return (this.health()?.effectiveMax ?? this.stats.health) * this.hpScale;
  }
  healthFraction() {
    const h = this.health();
    return h ? h.currentValue / Math.max(1, h.effectiveMax) : 0;
  }
  get currentAttack() {
    return this.run?.def;
  }
  save() {
    this.record.phase = this.phase;
    this.record.scale = this.hpScale;
    this.record.extra = this.controller.extra();
    saveRecord(this.boss, this.record);
  }
  /** Multiplayer scaling: grows with the peak participant count, never shrinks mid-fight. */
  updateScale() {
    const n = Math.min(CONFIG.encounter.maxScaledPlayers, Math.max(1, this.targeting.peak));
    const want = difficulty().health * (1 + CONFIG.encounter.hpPerExtraPlayer * (n - 1));
    if (want > this.hpScale + 1e-6 || !this.record.engaged && Math.abs(want - this.hpScale) > 1e-6) {
      this.hpScale = want;
      trace("scale", { boss: this.key, players: n, scale: want });
    }
  }
  // ------------------------------------------------------------------ lifecycle
  /** Begin (or resume) the fight. */
  start() {
    this.setProp("abm:phase", this.record.phase);
    this.controller.restore(this.record.extra ?? {});
    this.targeting.refresh(0, true);
    if (this.record.engaged) {
      this.phase = this.record.phase;
      this.controller.configure(this.phase);
      this.sm.restore(this.phase, 0);
      this.invulnerable = false;
      this.setAnim(0 /* None */);
      this.nextAttackAt = 40;
      trace("resume", { boss: this.key, phase: this.phase });
      return;
    }
    this.updateScale();
    this.controller.configure(1);
    this.invulnerable = true;
    this.setAnim(11 /* Intro */);
    const ticks = this.controller.intro();
    trace("intro", { boss: this.key, ticks });
    this.timeline.after(ticks, () => {
      this.sm.setTop("PHASE_1" /* Phase1 */, this.timeline.now);
      this.invulnerable = false;
      this.setAnim(0 /* None */);
      this.record.engaged = true;
      this.nextAttackAt = this.timeline.now + 30;
      for (const a of this.controller.attacks) if (a.ultimate) this.scheduler.hold(a, 420);
      this.save();
    }, "intro");
  }
  tick() {
    if (this.ended) return;
    if (!this.boss.isValid) {
      this.host.release(this, "unloaded");
      return;
    }
    this.timeline.step();
    if (this.ended) return;
    if (this.deferred.length > 0) {
      const d = this.deferred;
      this.deferred = [];
      for (const f of d) {
        try {
          f();
        } catch (e) {
          report("deferred", e);
        }
      }
    }
    const now = this.timeline.now;
    this.targeting.refresh(now);
    this.updateScale();
    this.helpers.tick();
    try {
      this.controller.tick();
      if (this.sm.inCombat) this.combat(now);
    } catch (e) {
      report(`${this.key} tick`, e);
    }
    if (now % CONFIG.hud.intervalTicks === 0) renderHud(this);
    if (now % 100 === 0 && this.sm.inCombat) this.save();
  }
  combat(now) {
    if (this.pendingDeath) {
      this.beginDeath();
      return;
    }
    if (this.targeting.count() === 0) {
      if (this.sm.sub !== "RESET" /* Reset */) {
        this.cancelAttack();
        this.sm.setSub("RESET" /* Reset */, now);
        this.setAnim(0 /* None */);
        this.emptySince = now;
        trace("reset_wait", { boss: this.key });
      } else if (now - this.emptySince >= CONFIG.encounter.resetGraceTicks) {
        this.host.abandon(this);
        return;
      }
      this.loco.goTo({ x: this.arena.cx, z: this.arena.cz }, 1.2);
      return;
    }
    if (this.sm.sub === "RESET" /* Reset */) {
      this.sm.setSub("IDLE" /* Idle */, now);
      this.nextAttackAt = now + 30;
    }
    if (this.pendingTransition && this.sm.top === "PHASE_1" /* Phase1 */) {
      if (!this.run || this.run.def.interruptible !== false) {
        this.beginTransition();
        return;
      }
    }
    switch (this.sm.sub) {
      case "STAGGER" /* Stagger */:
        if (now >= this.staggerUntil) {
          this.sm.setSub("IDLE" /* Idle */, now);
          this.setAnim(0 /* None */);
          this.nextAttackAt = Math.max(this.nextAttackAt, now + 10);
        }
        break;
      case "IDLE" /* Idle */:
      case "POSITIONING" /* Positioning */: {
        if (now % 20 === 0) this.loco.enforceLeash();
        const target = this.targeting.primary(now);
        const moving = this.controller.position(target);
        this.sm.setSub(moving ? "POSITIONING" /* Positioning */ : "IDLE" /* Idle */, now);
        if (now >= this.nextAttackAt) {
          const atk = this.scheduler.choose(this.controller.attacks);
          if (atk) this.startAttack(atk);
          else this.nextAttackAt = now + 8;
        }
        break;
      }
      default:
        break;
    }
  }
  // ------------------------------------------------------------------ attacks
  startAttack(def) {
    if (!this.sm.inCombat || this.sm.busy || this.sm.sub === "STAGGER" /* Stagger */) return false;
    const now = this.timeline.now;
    this.loco.halt();
    const run = new AttackRun(this, def, ++this.runSeq);
    this.run = run;
    this.currentAttackName = def.name;
    this.scheduler.commit(def);
    this.setAnim(def.index, 0);
    this.sm.setSub("TELEGRAPH" /* Telegraph */, now);
    try {
      def.run(run);
      if (!run.hasWindows) throw new Error(`${def.id} did not declare its windows`);
    } catch (e) {
      report(`attack ${def.id}`, e);
      this.cancelAttack();
      this.nextAttackAt = now + 20;
      return false;
    }
    return true;
  }
  finishAttack(run) {
    if (this.run !== run) return;
    const now = this.timeline.now;
    this.run = void 0;
    this.currentAttackName = "";
    this.scheduler.release(run.def);
    this.setAnim(0 /* None */);
    this.sm.setSub("IDLE" /* Idle */, now);
    this.nextAttackAt = now + Math.round(CONFIG.encounter.baseAttackGap * difficulty().attackGap * (this.phase === 2 ? 0.8 : 1));
  }
  /** Abort the running attack: every pending strike of it is removed. */
  cancelAttack() {
    const run = this.run;
    if (!run) return;
    run.cancelled = true;
    this.timeline.cancel(run.tag);
    this.run = void 0;
    this.currentAttackName = "";
    this.scheduler.release(run.def);
    try {
      this.controller.onAttackCancelled(run.def);
    } catch (e) {
      report("onAttackCancelled", e);
    }
    this.setAnim(0 /* None */);
    if (this.sm.busy) this.sm.setSub("IDLE" /* Idle */, this.timeline.now);
    trace("attack_cancelled", { boss: this.key, id: run.def.id });
  }
  /** Knock the boss out of what it is doing for `ticks`. Returns false if it could not be staggered. */
  stagger(ticks) {
    if (!this.sm.inCombat || this.sm.sub === "RESET" /* Reset */) return false;
    if (this.run && this.run.def.interruptible === false) return false;
    const now = this.timeline.now;
    this.cancelAttack();
    this.loco.halt();
    this.sm.setSub("STAGGER" /* Stagger */, now);
    this.staggerUntil = now + ticks;
    this.setAnim(9 /* Stagger */);
    trace("stagger", { boss: this.key, ticks });
    return true;
  }
  // ------------------------------------------------------------------ phase change and death
  beginTransition() {
    const now = this.timeline.now;
    this.pendingTransition = false;
    this.cancelAttack();
    if (!this.sm.setTop("PHASE_TRANSITION" /* Transition */, now)) return;
    this.invulnerable = true;
    this.loco.halt();
    this.setAnim(8 /* Transition */);
    const ticks = this.controller.phaseTransition();
    this.timeline.after(ticks, () => {
      const t = this.timeline.now;
      this.phase = 2;
      this.setProp("abm:phase", 2);
      this.sm.setTop("PHASE_2" /* Phase2 */, t);
      this.invulnerable = false;
      this.setAnim(0 /* None */);
      this.controller.configure(2);
      this.controller.phase2Ready();
      this.scheduler.refresh(60);
      this.nextAttackAt = t + 24;
      this.save();
    }, "phase");
  }
  beginDeath() {
    const now = this.timeline.now;
    this.pendingDeath = false;
    this.cancelAttack();
    this.timeline.cancelAll();
    this.helpers.removeAll();
    if (!this.sm.setTop("DEATH" /* Death */, now)) return;
    this.invulnerable = true;
    this.loco.halt();
    this.setAnim(10 /* Death */);
    try {
      this.boss.triggerEvent("abm:hide_bar");
    } catch (e) {
      report("hide_bar", e);
    }
    const ticks = this.controller.death();
    this.timeline.after(ticks, () => {
      grantRewards(this);
      try {
        this.boss.addTag(REMNANT_TAG);
        this.boss.triggerEvent("abm:become_remnant");
      } catch (e) {
        report("remnant", e);
      }
      this.host.release(this, "defeated");
    }, "death");
  }
  /** The boss entity died natively (e.g. /kill): skip the sequence, still clean up. */
  onNativeDeath() {
    if (this.ended) return;
    trace("native_death", { boss: this.key });
    this.host.release(this, "killed");
  }
  /** Final cleanup. Idempotent. */
  end(reason) {
    if (this.ended) return;
    this.ended = true;
    this.timeline.cancelAll();
    this.deferred = [];
    this.helpers.removeAll();
    try {
      this.controller.cleanup();
    } catch (e) {
      report("controller.cleanup", e);
    }
    clearHud(this);
    this.damage.clear();
    trace("end", { boss: this.key, reason, pendingTasks: this.timeline.pending() });
  }
  // ------------------------------------------------------------------ damage intake (before-event: read-only context)
  onHurtBefore(ev) {
    if (this.ended) return;
    if (this.invulnerable || !this.sm.inCombat || this.pendingDeath) {
      ev.cancel = true;
      return;
    }
    const src = ev.damageSource;
    const cause = String(src.cause);
    if (IGNORED_CAUSES.has(cause)) {
      ev.cancel = true;
      return;
    }
    const attacker = src.damagingEntity;
    const player = attacker instanceof Player3 ? attacker : void 0;
    if (attacker && this.helpers.owns(attacker.id)) {
      ev.cancel = true;
      return;
    }
    if (player && CONFIG.encounter.blockOutsideDamage && !this.targeting.isParticipant(player)) {
      ev.cancel = true;
      this.noteOutsider(player);
      return;
    }
    let dmg = ev.damage;
    if (EXPLOSION_CAUSES.has(cause)) dmg *= 0.3;
    dmg = this.controller.incoming(dmg, { attacker, player, projectile: src.damagingProjectile, cause });
    const h = this.health();
    if (!h || dmg <= 0) {
      ev.cancel = true;
      return;
    }
    dmg = Math.min(dmg * this.stats.damageTaken / this.hpScale, h.effectiveMax * CONFIG.encounter.maxHitFraction);
    const hp = h.currentValue;
    if (this.phase === 1) {
      const gate = h.effectiveMax * this.stats.phase2At;
      if (hp - dmg <= gate) {
        dmg = Math.max(0, hp - gate);
        this.pendingTransition = true;
      }
    } else if (hp - dmg <= 0.5) {
      this.pendingDeath = true;
      if (player) this.targeting.addThreat(player.id, hp * this.hpScale);
      ev.cancel = true;
      return;
    }
    if (dmg < 1e-3) {
      ev.cancel = true;
      return;
    }
    ev.damage = dmg;
    if (player) this.targeting.addThreat(player.id, dmg * this.hpScale);
  }
  noteOutsider(p) {
    const now = this.timeline.now;
    if (now - (this.outsiderNote.get(p.id) ?? -999) < 100) return;
    this.outsiderNote.set(p.id, now);
    this.defer(() => {
      try {
        p.sendMessage({ rawtext: [{ translate: "abm.msg.outside" }] });
      } catch {
      }
    });
  }
  /** Debug / test hook: request the phase change or the death without dealing damage. */
  force(what) {
    if (what === "phase2" && this.sm.top === "PHASE_1" /* Phase1 */) this.pendingTransition = true;
    if (what === "death" && this.sm.inCombat) this.pendingDeath = true;
  }
};

// src/core/manager.ts
var BOSS_TYPE = {
  vesperra: "abm:vesperra",
  cantor: "abm:cantor_xiii",
  nomos: "abm:nomos",
  orison: "abm:orison"
};
var SEAL_ITEM = {
  vesperra: "abm:seal_vesperra",
  cantor: "abm:seal_cantor",
  nomos: "abm:seal_nomos",
  orison: "abm:seal_orison"
};
var TYPE_TO_KEY = new Map(BOSS_KEYS.map((k) => [BOSS_TYPE[k], k]));
var DIMENSIONS = ["overworld", "nether", "the_end"];
var EncounterManager = class {
  constructor() {
    this.encounters = /* @__PURE__ */ new Map();
    this.factories = /* @__PURE__ */ new Map();
    this.ticks = 0;
    this.started = false;
  }
  register(key, factory) {
    this.factories.set(key, factory);
  }
  has(key) {
    return this.factories.has(key);
  }
  list() {
    return [...this.encounters.values()];
  }
  get(bossId) {
    return this.encounters.get(bossId);
  }
  /** Closest active encounter to a location in the same dimension. */
  nearest(dim, at, maxDist = 96) {
    let best;
    let bd = maxDist;
    for (const e of this.encounters.values()) {
      if (e.dim.id !== dim.id) continue;
      const d = Math.hypot(e.arena.cx - at.x, e.arena.cz - at.z);
      if (d < bd) {
        bd = d;
        best = e;
      }
    }
    return best;
  }
  // ------------------------------------------------------------------ wiring
  /**
   * Subscribe to world events and start the tick loop. Call once at module load.
   * `helperTypes` are the helper entity identifiers of the installed bosses.
   */
  init(helperTypes = []) {
    if (this.started) return;
    this.started = true;
    const bossTypes = [...TYPE_TO_KEY.keys()];
    world3.afterEvents.worldLoad.subscribe(() => {
      loadSettings();
      this.adoptLoaded();
      this.sweepOrphans();
    });
    world3.afterEvents.entitySpawn.subscribe((ev) => {
      if (TYPE_TO_KEY.has(ev.entity.typeId)) system.run(() => this.adopt(ev.entity, true));
    });
    world3.afterEvents.entityLoad.subscribe((ev) => {
      if (TYPE_TO_KEY.has(ev.entity.typeId)) system.run(() => this.adopt(ev.entity, false));
    });
    world3.beforeEvents.entityHurt.subscribe(
      (ev) => {
        const enc = this.encounters.get(ev.hurtEntity.id);
        if (enc) {
          try {
            enc.onHurtBefore(ev);
          } catch (e) {
            report("onHurtBefore", e);
          }
        } else if (ev.hurtEntity.hasTag(REMNANT_TAG)) {
          ev.cancel = true;
        }
      },
      { entityFilter: { families: ["abm_boss"] } }
    );
    world3.afterEvents.entityDie.subscribe(
      (ev) => {
        const id = ev.deadEntity.id;
        const enc = this.encounters.get(id);
        if (enc) enc.onNativeDeath();
        else for (const e of this.encounters.values()) e.helpers.notifyDied(id);
      },
      { entityTypes: [...bossTypes, ...helperTypes] }
    );
    world3.afterEvents.playerLeave.subscribe((ev) => {
      for (const e of this.encounters.values()) e.damage.forget(ev.playerId);
    });
    system.runInterval(() => this.tick(), 1);
  }
  tick() {
    this.ticks++;
    for (const e of [...this.encounters.values()]) {
      try {
        e.tick();
      } catch (err) {
        report(`encounter ${e.key}`, err);
      }
    }
    if (this.ticks % 200 === 0) this.sweepOrphans();
  }
  // ------------------------------------------------------------------ creating encounters
  /**
   * Summon a boss at a floor position chosen by a player. Never edits terrain:
   * if the place cannot host the arena the summon is refused with a reason.
   */
  trySummon(player, key, floor, force = false) {
    if (!this.factories.has(key)) return { ok: false, reason: "unknown" };
    const stats = CONFIG.bosses[key];
    const dim = player.dimension;
    for (const e of this.encounters.values()) {
      if (e.dim.id !== dim.id) continue;
      const d = Math.hypot(e.arena.cx - floor.x, e.arena.cz - floor.z);
      if (d < e.arena.radius * 1.5 + stats.arenaRadius * 1.5 + 6) return { ok: false, reason: "overlap" };
    }
    const scan = Arena.scan(dim, floor, stats);
    if (!scan.ok && !(force && scan.loaded)) {
      return { ok: false, reason: scan.reason ?? "floor", coverage: scan.coverage };
    }
    let boss;
    try {
      const yaw = dirToYaw(player.location.x - floor.x, player.location.z - floor.z);
      boss = dim.spawnEntity(BOSS_TYPE[key], { x: floor.x, y: floor.y + 0.05, z: floor.z }, { initialRotation: yaw });
    } catch (e) {
      report("spawn boss", e);
      return { ok: false, reason: "spawn" };
    }
    const enc = this.create(boss, key, floor);
    trace("summon", { boss: key, by: player.name, coverage: scan.coverage });
    return { ok: !!enc, encounter: enc, coverage: scan.coverage, reason: enc ? void 0 : "spawn" };
  }
  create(boss, key, centre) {
    const factory = this.factories.get(key);
    if (!factory || this.encounters.has(boss.id)) return this.encounters.get(boss.id);
    try {
      const rec = loadRecord(boss);
      const enc = new Encounter(boss, key, this, factory, rec ?? (centre ? {
        v: 1,
        boss: key,
        cx: centre.x,
        cy: centre.y,
        cz: centre.z,
        phase: 1,
        scale: 1,
        seed: Math.random() * 4294967295 >>> 0,
        engaged: false,
        extra: {}
      } : void 0));
      this.encounters.set(boss.id, enc);
      enc.start();
      return enc;
    } catch (e) {
      report(`create encounter ${key}`, e);
      this.encounters.delete(boss.id);
      return void 0;
    }
  }
  /** Take charge of a boss entity that appeared without going through trySummon. */
  adopt(boss, fresh) {
    try {
      if (!boss.isValid || this.encounters.has(boss.id)) return;
      const key = TYPE_TO_KEY.get(boss.typeId);
      if (!key) return;
      if (boss.hasTag(REMNANT_TAG)) return;
      const enc = this.create(boss, key);
      if (enc && fresh) {
        const scan = Arena.scan(boss.dimension, enc.arena.centre, enc.stats);
        if (!scan.ok) {
          for (const p of boss.dimension.getPlayers({ location: boss.location, maxDistance: 48 })) {
            p.sendMessage({ rawtext: [{ translate: "abm.summon.warn.space" }] });
          }
        }
      }
    } catch (e) {
      report("adopt", e);
    }
  }
  adoptLoaded() {
    for (const id of DIMENSIONS) {
      try {
        for (const e of world3.getDimension(id).getEntities({ families: ["abm_boss"] })) this.adopt(e, false);
      } catch {
      }
    }
  }
  // ------------------------------------------------------------------ ending encounters
  release(enc, reason) {
    enc.end(reason);
    this.encounters.delete(enc.bossId);
  }
  abandon(enc) {
    const centre = enc.arena.at({ x: enc.arena.cx, z: enc.arena.cz }, 1);
    const dim = enc.dim;
    this.release(enc, "abandoned");
    try {
      if (enc.boss.isValid) enc.boss.remove();
      if (CONFIG.encounter.refundSealOnReset) dim.spawnItem(new ItemStack2(SEAL_ITEM[enc.key], 1), centre);
      for (const p of dim.getPlayers({ location: centre, maxDistance: 96 })) {
        p.sendMessage({ rawtext: [{ translate: "abm.msg.abandoned" }] });
      }
    } catch (e) {
      report("abandon", e);
    }
  }
  /** Cancel an encounter on request (command / UI): same as abandoning it. */
  cancel(enc) {
    this.abandon(enc);
  }
  /** Remove helper entities whose encounter no longer exists (crash, reload, unload). */
  sweepOrphans() {
    for (const id of DIMENSIONS) {
      let found = [];
      try {
        found = world3.getDimension(id).getEntities({ tags: [HELPER_TAG] });
      } catch {
        continue;
      }
      for (const e of found) {
        try {
          const owner = e.getDynamicProperty(OWNER_PROP);
          const enc = typeof owner === "string" ? this.encounters.get(owner) : void 0;
          if (!enc || !enc.helpers.owns(e.id)) e.remove();
        } catch {
        }
      }
    }
  }
};
var manager = new EncounterManager();

// src/items.ts
import {
  EntityComponentTypes as EntityComponentTypes2,
  EquipmentSlot as EquipmentSlot2,
  GameMode as GameMode3,
  system as system2,
  world as world5
} from "@minecraft/server";

// src/ui.ts
import { PlayerPermissionLevel, world as world4 } from "@minecraft/server";
import { ActionFormData, MessageFormData, ModalFormData } from "@minecraft/server-ui";

// src/registry.ts
var modules = {};
function install(mods) {
  for (const k of BOSS_KEYS) {
    const m = mods[k];
    if (m) modules[k] = m;
  }
}
function installed() {
  return BOSS_KEYS.filter((k) => modules[k] !== void 0);
}
function moduleOf(k) {
  return modules[k];
}
function arenaOf(k) {
  return modules[k]?.arena;
}

// src/ui.ts
var DIFFICULTIES = ["story", "normal", "hard"];
var tr = (key, ...w) => ({ rawtext: [{ translate: key, with: w }] });
function isOperator(p) {
  try {
    return p.playerPermissionLevel >= PlayerPermissionLevel.Operator;
  } catch {
    return false;
  }
}
function raiseArena(p, key) {
  const info = arenaOf(key);
  if (!info) return false;
  const l = p.location;
  const half = Math.floor(info.size / 2);
  try {
    world4.structureManager.place(info.structure, p.dimension, {
      x: Math.floor(l.x) - half,
      y: Math.floor(l.y) - 1,
      z: Math.floor(l.z) - half
    });
    p.sendMessage(tr("abm.arena.built"));
    return true;
  } catch (e) {
    report("raiseArena", e);
    return false;
  }
}
async function arenaMenu(p) {
  const keys = BOSS_KEYS.filter((k) => arenaOf(k));
  const form = new ActionFormData().title(tr("abm.ui.arena"));
  for (const k of keys) form.button(tr(arenaOf(k).nameKey));
  const r = await form.show(p);
  if (r.canceled || r.selection === void 0) return;
  const key = keys[r.selection];
  const info = arenaOf(key);
  const ok2 = await new MessageFormData().title(tr(info.nameKey)).body(tr("abm.ui.arena.warn", String(info.size), String(info.size))).button1(tr("abm.ui.cancel")).button2(tr("abm.ui.confirm")).show(p);
  if (!ok2.canceled && ok2.selection === 1) raiseArena(p, key);
}
async function settingsMenu(p) {
  const r = await new ModalFormData().title(tr("abm.ui.settings")).dropdown(tr("abm.ui.difficulty"), ["Story", "Normal", "Hard"], { defaultValueIndex: DIFFICULTIES.indexOf(CONFIG.difficulty) }).toggle(tr("abm.ui.vfx"), { defaultValue: CONFIG.vfx.density < 1 }).toggle(tr("abm.ui.actionbar"), { defaultValue: CONFIG.hud.actionBar }).toggle(tr("abm.ui.movement"), { defaultValue: CONFIG.movement.mode === "teleport" }).show(p);
  if (r.canceled || !r.formValues) return;
  const [d, vfx, bar, tele] = r.formValues;
  applySettings({
    difficulty: DIFFICULTIES[typeof d === "number" ? d : 1],
    vfxDensity: vfx ? 0.5 : 1,
    actionBar: !!bar,
    movementMode: tele ? "teleport" : "impulse"
  });
  saveSettings();
  p.sendMessage(tr("abm.ui.saved"));
}
async function openCodex(p) {
  try {
    const op = isOperator(p);
    const keys = BOSS_KEYS.filter((k) => manager.has(k));
    const form = new ActionFormData().title(tr("abm.ui.title")).body({ rawtext: [{ translate: "abm.ui.body1" }, { text: "\n\n" }, { translate: "abm.ui.body2" }] });
    for (const k of keys) form.button(tr(`entity.${bossType(k)}.name`));
    if (op) form.button(tr("abm.ui.settings")).button(tr("abm.ui.arena")).button(tr("abm.ui.dismiss"));
    const r = await form.show(p);
    if (r.canceled || r.selection === void 0) return;
    if (r.selection < keys.length) {
      const k = keys[r.selection];
      const s = CONFIG.bosses[k];
      await new MessageFormData().title(tr(`entity.${bossType(k)}.name`)).body({ rawtext: [{ translate: `abm.lore.${k}` }, { text: "\n\n" }, { translate: "abm.summon.need", with: [String(s.arenaRadius * 2 + 1), String(s.clearance)] }] }).button1(tr("abm.ui.cancel")).button2(tr("abm.ui.title")).show(p);
      return;
    }
    const extra = r.selection - keys.length;
    if (extra === 0) await settingsMenu(p);
    else if (extra === 1) await arenaMenu(p);
    else if (extra === 2) {
      const enc = manager.nearest(p.dimension, p.location);
      if (enc) manager.cancel(enc);
      p.sendMessage(tr("abm.msg.cancelled"));
    }
  } catch (e) {
    report("codex", e);
  }
}
function bossType(k) {
  return { vesperra: "abm:vesperra", cantor: "abm:cantor_xiii", nomos: "abm:nomos", orison: "abm:orison" }[k];
}

// src/items.ts
var CODEX_ITEM = "abm:codex";
var TROPHY = {
  vesperra: "abm:ivory_diadem",
  cantor: "abm:bell_fragment",
  nomos: "abm:sovereign_needle",
  orison: "abm:unlived_hourglass"
};
var SEAL_TO_KEY = new Map(BOSS_KEYS.map((k) => [SEAL_ITEM[k], k]));
var TROPHY_TO_KEY = new Map(BOSS_KEYS.map((k) => [TROPHY[k], k]));
var TROPHY_SOUND = {
  vesperra: "abm.vesperra.trophy",
  cantor: "abm.cantor.trophy",
  nomos: "abm.nomos.trophy",
  orison: "abm.orison.trophy"
};
var lastUse = /* @__PURE__ */ new Map();
function debounce(p) {
  const now = system2.currentTick;
  if (now - (lastUse.get(p.id) ?? -100) < 10) return false;
  lastUse.set(p.id, now);
  return true;
}
function consumeHeld(p, typeId) {
  try {
    if (p.getGameMode() === GameMode3.Creative) return;
    const eq = p.getComponent(EntityComponentTypes2.Equippable);
    const held = eq?.getEquipment(EquipmentSlot2.Mainhand);
    if (!eq || !held || held.typeId !== typeId) return;
    if (held.amount > 1) {
      held.amount -= 1;
      eq.setEquipment(EquipmentSlot2.Mainhand, held);
    } else {
      eq.setEquipment(EquipmentSlot2.Mainhand, void 0);
    }
  } catch (e) {
    report("consumeHeld", e);
  }
}
function useSeal(p, key, floor, force = false) {
  const stats = CONFIG.bosses[key];
  const res = manager.trySummon(p, key, floor, force);
  if (res.ok) {
    consumeHeld(p, SEAL_ITEM[key]);
    for (const q of p.dimension.getPlayers({ location: floor, maxDistance: 64 })) {
      q.sendMessage({ rawtext: [{ translate: `abm.summon.ok.${key}` }] });
    }
    return true;
  }
  const pct = String(Math.round((res.coverage ?? 0) * 100));
  p.sendMessage({ rawtext: [{ translate: `abm.summon.fail.${res.reason ?? "unknown"}`, with: [pct] }] });
  if (res.reason === "floor" || res.reason === "ceiling") {
    p.sendMessage({ rawtext: [{ translate: "abm.summon.need", with: [String(stats.arenaRadius * 2 + 1), String(stats.clearance)] }] });
  }
  return false;
}
function initItems() {
  world5.afterEvents.playerInteractWithBlock.subscribe((ev) => {
    if (!ev.isFirstEvent) return;
    const id = ev.beforeItemStack?.typeId ?? ev.itemStack?.typeId;
    const key = id ? SEAL_TO_KEY.get(id) : void 0;
    if (!key || !debounce(ev.player)) return;
    const b = ev.block;
    useSeal(ev.player, key, { x: b.x + 0.5, y: b.y + 1, z: b.z + 0.5 });
  });
  world5.afterEvents.itemUse.subscribe((ev) => {
    const id = ev.itemStack.typeId;
    const p = ev.source;
    if (id === CODEX_ITEM) {
      if (debounce(p)) void openCodex(p);
      return;
    }
    const seal = SEAL_TO_KEY.get(id);
    if (seal) {
      if (!debounce(p)) return;
      try {
        const hit = p.getBlockFromViewDirection({ maxDistance: 10 });
        if (hit) {
          const b = hit.block;
          useSeal(p, seal, { x: b.x + 0.5, y: b.y + 1, z: b.z + 0.5 });
        }
      } catch (e) {
        report("seal raycast", e);
      }
      return;
    }
    const trophy = TROPHY_TO_KEY.get(id);
    if (trophy && debounce(p)) {
      try {
        p.dimension.playSound(TROPHY_SOUND[trophy], p.location, { volume: 0.8 });
        p.onScreenDisplay.setActionBar({ rawtext: [{ translate: `abm.trophy.${trophy}` }] });
      } catch (e) {
        report("trophy", e);
      }
    }
  });
  world5.afterEvents.playerLeave.subscribe((ev) => lastUse.delete(ev.playerId));
}

// src/commands.ts
var fail = (message) => ({ status: CustomCommandStatus.Failure, message });
var ok = (message) => ({ status: CustomCommandStatus.Success, message });
function registerCommands(ev) {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("abm:boss", [...BOSS_KEYS]);
    reg.registerEnum("abm:debug_action", ["on", "off", "phase2", "kill", "attack", "info"]);
    const lvl = CommandPermissionLevel.GameDirectors;
    reg.registerCommand(
      {
        name: "abm:summon",
        description: "Summon one of the Abandoned Miracles at your position",
        permissionLevel: lvl,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:boss", type: CustomCommandParamType.Enum }]
      },
      (origin, boss) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player7)) return fail("Players only.");
        const l = p.location;
        system3.run(() => useSeal(p, boss, { x: Math.floor(l.x) + 0.5, y: Math.floor(l.y), z: Math.floor(l.z) + 0.5 }, true));
        return ok();
      }
    );
    reg.registerCommand(
      {
        name: "abm:arena",
        description: "Raise a demonstration arena around you (REPLACES blocks)",
        permissionLevel: lvl,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:boss", type: CustomCommandParamType.Enum }]
      },
      (origin, boss) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player7)) return fail("Players only.");
        system3.run(() => raiseArena(p, boss));
        return ok();
      }
    );
    reg.registerCommand(
      { name: "abm:dismiss", description: "End the nearest Abandoned Miracles encounter", permissionLevel: lvl, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player7)) return fail("Players only.");
        const enc = manager.nearest(p.dimension, p.location);
        if (!enc) return fail("No encounter nearby.");
        system3.run(() => manager.cancel(enc));
        return ok("Encounter dismissed.");
      }
    );
    reg.registerCommand(
      {
        name: "abm:debug",
        description: "Abandoned Miracles test controls",
        permissionLevel: lvl,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "abm:debug_action", type: CustomCommandParamType.Enum }],
        optionalParameters: [{ name: "value", type: CustomCommandParamType.Integer }]
      },
      (origin, action, value) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player7)) return fail("Players only.");
        if (action === "on" || action === "off") {
          CONFIG.debug = action === "on";
          system3.run(() => saveSettings());
          return ok(`Debug ${action}.`);
        }
        const enc = manager.nearest(p.dimension, p.location);
        if (!enc) return fail("No encounter nearby.");
        if (action === "phase2") enc.force("phase2");
        else if (action === "kill") enc.force("death");
        else if (action === "attack") {
          const a = enc.controller.attacks.find((x) => x.index === value);
          if (!a) return fail("attack needs a number 1-7.");
          enc.scheduler.forced = a.id;
          enc.nextAttackAt = 0;
          return ok(`Next attack: ${a.name}`);
        } else if (action === "info") {
          const used = [...enc.scheduler.usage.entries()].map(([k, n]) => `${k}:${n}`).join(" ");
          return ok(`${enc.key} ${enc.sm.top}/${enc.sm.sub} hp ${Math.round(enc.effectiveHealth())}/${Math.round(enc.effectiveMaxHealth())} scale ${enc.hpScale.toFixed(2)} players ${enc.targeting.count()} extra ${JSON.stringify(enc.controller.extra())} used ${used}`);
        }
        return ok();
      }
    );
  } catch (e) {
    console.warn(`[abm] custom commands unavailable: ${e}`);
  }
}

// src/boot.ts
function boot(mods) {
  install(mods);
  system4.beforeEvents.startup.subscribe((ev) => registerCommands(ev));
  const helpers = [];
  for (const k of installed()) {
    const m = moduleOf(k);
    manager.register(k, m.create);
    helpers.push(...m.helpers);
  }
  manager.init(helpers);
  initItems();
  const g = globalThis;
  if (g.__abmTrace) g.__abm = { manager, CONFIG };
}

// src/bosses/cantor/index.ts
var MODULE = void 0;

// src/bosses/nomos/index.ts
var MODULE2 = void 0;

// src/bosses/orison/index.ts
var MODULE3 = void 0;

// shared/vesperra.timings.json
var vesperra_timings_default = {
  _comment: "Beat timings for Vesperra, in game ticks from the start of each action. Shared by the script (hit windows) and the animation generator (keyframes), so they cannot drift apart.",
  intro: {
    rise: 30,
    crown: 70,
    total: 110
  },
  transition: {
    crack: 24,
    split: 56,
    unfold: 96,
    total: 130
  },
  stagger: {
    total: 36
  },
  death: {
    crown: 30,
    molt: 70,
    fail: 110,
    collapse: 140,
    total: 176
  },
  ivory_scythe: {
    p1: {
      hit1: 26,
      decide: 30,
      hit2: 56,
      end: 86
    },
    p2: {
      hit1: 24,
      decide: 28,
      hit2: 52,
      hit3: 70,
      end: 100
    }
  },
  needle_procession: {
    p1: {
      plant: 14,
      first: 36,
      gap: 13,
      end: 92
    },
    p2: {
      plant: 12,
      first: 30,
      gap: 10,
      cross: 68,
      end: 108
    }
  },
  royal_molting: {
    p1: {
      launch: 30,
      end: 76
    },
    p2: {
      launch: 24,
      second: 46,
      end: 92
    }
  },
  cocoon_edict: {
    p1: {
      spawn: 12,
      constrict: 60,
      end: 84
    },
    p2: {
      spawn: 10,
      constrict: 50,
      end: 74
    }
  },
  false_submission: {
    p1: {
      cue: 32,
      thrust: 48,
      dash: 8,
      end: 104
    },
    p2: {
      cue: 24,
      thrust: 38,
      dash: 8,
      cue2: 54,
      thrust2: 68,
      end: 124
    }
  },
  the_heirs: {
    p1: {
      detach: 26,
      end: 52
    },
    p2: {
      detach: 20,
      end: 44
    }
  },
  coronation: {
    p1: {
      first: 26,
      interval: 11,
      warn: 34,
      count: 7,
      end: 160
    },
    p2: {
      first: 22,
      interval: 12,
      warn: 30,
      count: 7,
      end: 158
    }
  }
};

// src/bosses/vesperra/armor.ts
import { Player as Player8 } from "@minecraft/server";

// src/bosses/vesperra/tuning.ts
var VESPERRA = {
  move: {
    p1: { speed: 0.085, turn: 4.5, hold: 5.2, chase: 6.4 },
    p2: { speed: 0.15, turn: 7.5, hold: 3.6, chase: 4.6 }
  },
  scythe: { cooldown: [150, 120], damage: 14, castDamage: 12, thrustDamage: 15, reach: 7.2, halfAngle: 80 },
  procession: { cooldown: [190, 160], damage: 13, length: 15, halfWidth: 1.25, spacing: 2.6, fan: 28 },
  molting: { cooldown: [210, 170], damage: 11, plates: 8, speed: 0.65, range: 13, radius: 1.05 },
  cocoon: { cooldown: [300, 250], damage: 12, radius: [4.6, 5.2], anchors: [3, 4], slowTicks: 60 },
  feint: { cooldown: [330, 280], damage: 17, reach: 8.5, halfWidth: 1.6, exposedBonus: 1.25 },
  heirs: { cooldown: [520, 420], max: 2, lifetime: 500, bite: 5, biteRange: 1.8, biteWarn: 18, biteCooldown: 60, speed: 0.17, guardRange: 3 },
  coronation: { cooldown: [760, 700], damage: 16, halfWidth: 1.3 },
  armor: {
    /** Plate health: left shell, right shell, crown/face shield. */
    plate: { l: 70, r: 70, c: 55 },
    /** Share of a hit that reaches the boss through an intact plate (phase I / phase II). */
    through: [0.35, 0.55],
    /** Multiplier on an exposed region. */
    exposed: [1.4, 1.5],
    /** Multiplier for hits that land elsewhere on the carapace. */
    body: [0.75, 1],
    /** An Heir standing guard at a flank reduces the exposed multiplier to this. */
    guarded: 0.8,
    breakStagger: 34
  }
};

// src/bosses/vesperra/armor.ts
var REGIONS = ["l", "r", "c"];
function boxes(phase) {
  const wing = phase === 2;
  return {
    l: wing ? { r0: -3.7, r1: -0.45, u0: 2.5, u1: 6.5, f0: -2.3, f1: 1.3 } : { r0: -2.2, r1: -0.45, u0: 2.3, u1: 5.5, f0: -1.4, f1: 1.4 },
    r: wing ? { r0: 0.45, r1: 3.7, u0: 2.5, u1: 6.5, f0: -2.3, f1: 1.3 } : { r0: 0.45, r1: 2.2, u0: 2.3, u1: 5.5, f0: -1.4, f1: 1.4 },
    c: { r0: -0.65, r1: 0.65, u0: 5.3, u1: 7.5, f0: -0.3, f1: 1 },
    // what is NOT a region but still stops a blade: the skirt and abdomen, and the slim upper chest
    core: { r0: -0.45, r1: 0.45, u0: 2.3, u1: 4.3, f0: -1.3, f1: 1.3 },
    chest: { r0: -0.45, r1: 0.45, u0: 4.3, u1: 5.3, f0: -0.45, f1: 0.45 }
  };
}
function rayBox(o, d, b, pad) {
  const lo = [b.r0 - pad, b.u0 - pad, b.f0 - pad];
  const hi = [b.r1 + pad, b.u1 + pad, b.f1 + pad];
  let tmin = 0;
  let tmax = 9;
  for (let i = 0; i < 3; i++) {
    if (Math.abs(d[i]) < 1e-9) {
      if (o[i] < lo[i] || o[i] > hi[i]) return Infinity;
      continue;
    }
    let t1 = (lo[i] - o[i]) / d[i];
    let t2 = (hi[i] - o[i]) / d[i];
    if (t1 > t2) [t1, t2] = [t2, t1];
    tmin = Math.max(tmin, t1);
    tmax = Math.min(tmax, t2);
    if (tmin > tmax) return Infinity;
  }
  return tmin;
}
function inBox(p, b, pad) {
  return p[0] >= b.r0 - pad && p[0] <= b.r1 + pad && p[1] >= b.u0 - pad && p[1] <= b.u1 + pad && p[2] >= b.f0 - pad && p[2] <= b.f1 + pad;
}
var ArmorSystem = class {
  constructor(enc) {
    this.enc = enc;
    /** Remaining plate health per region. */
    this.hp = { ...VESPERRA.armor.plate };
  }
  /** 0 intact, 1 cracked, 2 destroyed - the value synced to the client. */
  state(r) {
    const max = VESPERRA.armor.plate[r];
    return this.hp[r] <= 0 ? 2 : this.hp[r] <= max * 0.5 ? 1 : 0;
  }
  broken(r) {
    return this.hp[r] <= 0;
  }
  anyBroken() {
    return REGIONS.some((r) => this.broken(r));
  }
  /** World position of a region's centre (for effects and Heir guard posts). */
  anchor(r) {
    const o = this.enc.boss.location;
    const yaw = this.enc.loco.yaw;
    if (r === "c") return localToWorld(o, yaw, 0, 6.3, 0.5);
    return localToWorld(o, yaw, r === "l" ? -1.6 : 1.6, 3.8, 0);
  }
  toLocal(p) {
    const l = worldToLocal(this.enc.boss.location, this.enc.loco.yaw, p);
    return [l.right, l.up, l.fwd];
  }
  /** Which region does this hit land on? Pure geometry; safe inside a before-event. */
  classify(info) {
    const bx = boxes(this.enc.phase);
    if (info.projectile && info.projectile.isValid) {
      return this.classifyPoint(this.toLocal(info.projectile.location), bx);
    }
    const a = info.attacker;
    if (!a || !a.isValid) return void 0;
    let eye;
    let view;
    try {
      eye = a instanceof Player8 ? a.getHeadLocation() : this.headOf(a);
      view = a.getViewDirection();
    } catch {
      return void 0;
    }
    const o = this.toLocal(eye);
    const f = yawToDir(this.enc.loco.yaw);
    const rgt = { x: -f.z, z: f.x };
    const d = [view.x * rgt.x + view.z * rgt.z, view.y, view.x * f.x + view.z * f.z];
    let best;
    let bt = Math.min(rayBox(o, d, bx.core, 0), rayBox(o, d, bx.chest, 0));
    for (const r of REGIONS) {
      const t = rayBox(o, d, bx[r], 0.2);
      if (t < bt) {
        bt = t;
        best = r;
      }
    }
    return best;
  }
  headOf(e) {
    try {
      return e.getHeadLocation();
    } catch {
      return e.location;
    }
  }
  classifyPoint(p, bx) {
    for (const r of REGIONS) if (inBox(p, bx[r], 0.6)) return r;
    return void 0;
  }
  /** Is an Heir standing guard at this region right now? */
  guarded(r) {
    if (r === "c") return false;
    const post = this.anchor(r);
    for (const h of this.enc.helpers.of("heir")) {
      const l = h.entity.location;
      if (Math.hypot(l.x - post.x, l.z - post.z) <= VESPERRA.heirs.guardRange) return true;
    }
    return false;
  }
  /** Apply a hit to the armour model; returns what reaches the boss. No world changes here. */
  apply(damage, region) {
    const A = VESPERRA.armor;
    const i = this.enc.phase - 1;
    if (!region) return { damage: damage * A.body[i], region, broke: false, plateHit: false };
    if (this.hp[region] > 0) {
      const before = this.state(region);
      this.hp[region] = Math.max(0, this.hp[region] - damage);
      const broke = this.hp[region] <= 0 && before !== 2;
      return { damage: damage * A.through[i], region, broke, plateHit: true };
    }
    const mult = this.guarded(region) ? A.guarded : A.exposed[i];
    return { damage: damage * mult, region, broke: false, plateHit: false };
  }
  /** Push the visible states to the client (call from an unrestricted context). */
  sync() {
    for (const r of REGIONS) this.enc.setProp(`abm:armor_${r}`, this.state(r));
  }
  save() {
    return { al: this.hp.l, ar: this.hp.r, ac: this.hp.c };
  }
  load(extra) {
    if (typeof extra.al === "number") this.hp.l = extra.al;
    if (typeof extra.ar === "number") this.hp.r = extra.ar;
    if (typeof extra.ac === "number") this.hp.c = extra.ac;
  }
};

// src/bosses/vesperra/index.ts
var S = (id) => `abm.vesperra.${id}`;
var P = (id) => `abm:vesperra_${id}`;
var LANE_ORDERS = [
  [-1, 0, 1],
  [-1, 1, 0],
  [0, -1, 1],
  [0, 1, -1],
  [1, -1, 0],
  [1, 0, -1]
];
var beats = (name, phase) => vesperra_timings_default[name][phase === 2 ? "p2" : "p1"];
var VesperraController = class extends BossController {
  constructor(enc) {
    super(enc);
    this.key = "vesperra";
    this.displayName = "Vesperra";
    this.phase2Name = "The True Empress";
    this.trophyItem = "abm:ivory_diadem";
    this.style = {
      line: P("tg_line"),
      arc: P("tg_arc"),
      disc: P("tg_disc"),
      safeLine: P("safe_line"),
      safeArc: P("safe_arc"),
      strike: P("strike")
    };
    /** Royal Moltings performed so far (drives the shed look; capped). */
    this.molts = 0;
    /** While the encounter clock is below this, she is stuck after a failed thrust and takes bonus damage. */
    this.exposedUntil = 0;
    this.nextIdleSound = 120;
    this.armor = new ArmorSystem(enc);
    this.attacks = [
      this.ivoryScythe(),
      this.needleProcession(),
      this.royalMolting(),
      this.cocoonEdict(),
      this.falseSubmission(),
      this.theHeirs(),
      this.coronation()
    ];
  }
  // ------------------------------------------------------------------ framework hooks
  configure(phase) {
    const m = phase === 2 ? VESPERRA.move.p2 : VESPERRA.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }
  intro() {
    const e = this.enc;
    e.audio.play(S("intro_rise"), e.boss.location);
    return vesperra_timings_default.intro.total;
  }
  phaseTransition() {
    const e = this.enc;
    const t = vesperra_timings_default.transition;
    e.timeline.after(t.split, () => {
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 5.5))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: (p.location.x - c.x) / d * 1.6, z: (p.location.z - c.z) / d * 1.6 }, 0.35);
        } catch {
        }
      }
      for (const r of REGIONS) e.visuals.decor(P("molt"), this.armor.anchor(r));
    }, "phase");
    return t.total;
  }
  phase2Ready() {
    this.exposedUntil = 0;
  }
  death() {
    const e = this.enc;
    const t = vesperra_timings_default.death;
    e.timeline.after(t.crown, () => {
      this.armor.hp.c = 0;
      this.armor.sync();
      e.visuals.spawn(P("shards"), this.armor.anchor("c"));
    }, "death");
    e.timeline.after(t.collapse, () => e.visuals.scatter(P("dust"), new Circle(e.boss.location.x, e.boss.location.z, 3).sample(e.rng, 8), e.arena.floorY + 0.4), "death");
    return t.total;
  }
  position(target) {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const m = e.phase === 2 ? VESPERRA.move.p2 : VESPERRA.move.p1;
    const d = distXZ(e.boss.location, target.location);
    if (d > m.chase) {
      const k = (d - m.hold) / d;
      const b = e.boss.location;
      e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }
  tick() {
    const e = this.enc;
    const now = e.timeline.now;
    if (e.sm.inCombat) this.tickHeirs(now);
    if (now >= this.nextIdleSound && e.sm.inCombat && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 140 + e.rng.int(0, 120);
    }
  }
  incoming(damage, info) {
    const e = this.enc;
    const region = this.armor.classify(info);
    const out = this.armor.apply(damage, region);
    let dmg = out.damage;
    if (e.timeline.now < this.exposedUntil) dmg *= VESPERRA.feint.exposedBonus;
    trace("armor_hit", { region: region ?? "body", plate: out.plateHit, broke: out.broke, damage: dmg });
    e.defer(() => {
      this.armor.sync();
      const at = region ? this.armor.anchor(region) : localToWorld(e.boss.location, e.loco.yaw, 0, 3.6, 0.8);
      if (out.broke) {
        e.visuals.spawn(P("shards"), at);
        e.visuals.spawn(P("molt"), at);
        e.audio.play(S("armor_break"), at);
        e.stagger(VESPERRA.armor.breakStagger);
        e.save();
      } else if (out.plateHit) {
        e.visuals.decor(P("strike"), at);
        e.audio.play(S("armor_hit"), at, 0.8);
      } else {
        if (region) e.visuals.decor(P("drip"), at);
        e.audio.play(S("body_hit"), at, 0.7);
      }
    });
    return dmg;
  }
  onHelperGone(h) {
    if (h.kind === "anchor" && h.killed) {
      this.enc.audio.play(S("anchor_break"), h.entity.isValid ? h.entity.location : this.enc.boss.location);
    }
    this.enc.timeline.cancel(`heir${h.id}`);
  }
  onAttackCancelled(def) {
    if (def.id === "cocoon_edict") this.enc.helpers.removeKind("anchor");
  }
  extra() {
    return { ...this.armor.save(), molt: this.molts };
  }
  restore(extra) {
    this.armor.load(extra);
    this.molts = typeof extra.molt === "number" ? extra.molt : 0;
    this.armor.sync();
    this.enc.setProp("abm:molt", Math.min(2, this.molts));
  }
  // ------------------------------------------------------------------ shared helpers
  dist(e) {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }
  front() {
    return yawToTheta(this.enc.loco.yaw);
  }
  /** Chord of the arena through `p` along bearing `theta` (clipped to the arena circle). */
  chord(p, theta, halfWidth) {
    const a = this.enc.arena;
    const d = thetaToDir(theta);
    const ox = p.x - a.cx;
    const oz = p.z - a.cz;
    const b = ox * d.x + oz * d.z;
    const R = a.radius + 1;
    const disc = Math.max(0.01, b * b - (ox * ox + oz * oz - R * R));
    const t0 = -b - Math.sqrt(disc);
    const t1 = -b + Math.sqrt(disc);
    return new Lane(p.x + d.x * t0, p.z + d.z * t0, p.x + d.x * t1, p.z + d.z * t1, halfWidth);
  }
  // ------------------------------------------------------------------ 01 Ivory Scythe
  ivoryScythe() {
    const self = this;
    return {
      id: "ivory_scythe",
      name: "Ivory Scythe",
      index: 1,
      cooldown: VESPERRA.scythe.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d < 9 ? 3.2 : d < 13 ? 1.2 : 0.3;
      },
      run(run) {
        const e = run.enc;
        const t = beats("ivory_scythe", run.phase);
        const p2 = run.phase === 2;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const front = self.front();
        const sweep = (theta) => sector(b.x, b.z, 1.2, VESPERRA.scythe.reach, theta, VESPERRA.scythe.halfAngle);
        run.strike(t.hit1, { shape: sweep(front), warn: t.hit1 - 2, damage: VESPERRA.scythe.damage, blockable: true, knock: 1.1, knockUp: 0.25, fx: 8, label: "scythe_1" });
        run.at(t.decide, () => {
          const tgt = e.targeting.primary(e.timeline.now) ?? run.target;
          const warn = t.hit2 - t.decide;
          let turn = e.rng.chance(0.5);
          let aim = front + 180;
          if (tgt) {
            const d = distXZ(tgt.location, b);
            aim = dirToTheta(tgt.location.x - b.x, tgt.location.z - b.z);
            const behind = Math.abs(angDiff(front, aim)) > 95;
            if (behind || d < 5) turn = true;
            else if (d > 6.5) turn = false;
          }
          if (turn) {
            run.variant(1);
            const yaw = aim - 90;
            for (let i = 1; i <= 8; i++) run.at(t.decide + i, () => e.loco.turnToward(yaw, 1, 24));
            run.at(t.decide + 9, () => e.loco.face(yaw));
            e.hazards.strike({ shape: sweep(aim), warn, tag: run.tag, damage: VESPERRA.scythe.damage, blockable: true, knock: 1.1, knockUp: 0.25, fx: 8, label: "scythe_turn" });
          } else {
            run.variant(2);
            const gaps = [];
            for (let g = 0; g < 4; g++) gaps.push([front - 100 + 28 + g * 43, 15]);
            const band = (r) => new Ring(b.x, b.z, Math.max(0.5, r - 1.1), r + 1.1, front - 100, 200, gaps);
            e.hazards.telegraph(new Ring(b.x, b.z, 5, 13.8, front - 100, 200, gaps), warn);
            e.hazards.sweep({
              tag: run.tag,
              warn,
              duration: 12,
              every: 2,
              draw: false,
              shapeAt: (tt) => band(6 + tt * 0.6),
              damage: VESPERRA.scythe.castDamage,
              blockable: true,
              knock: 0.8,
              label: "scythe_cast",
              fx: 3
            });
            run.at(t.hit2, () => {
              for (let i = 0; i < 6; i++) {
                e.timeline.after(1 + i * 2, () => e.hazards.telegraphWith(P("crescent"), band(6 + i * 1.2), 6), run.tag);
              }
            });
          }
          if (p2) {
            run.at(t.hit2 + 2, () => {
              const tg = e.targeting.primary(e.timeline.now) ?? run.target;
              const o = e.boss.location;
              let th = yawToTheta(e.loco.yaw);
              if (tg) {
                const want = dirToTheta(tg.location.x - o.x, tg.location.z - o.z);
                if (Math.abs(angDiff(th, want)) <= 70) {
                  th = want;
                  e.loco.face(th - 90);
                }
              }
              const d = thetaToDir(th);
              const lane = new Lane(o.x + d.x * 1.5, o.z + d.z * 1.5, o.x + d.x * 12.5, o.z + d.z * 12.5, 1.3);
              e.hazards.strike({ shape: lane, warn: t.hit3 - t.hit2 - 2, tag: run.tag, damage: VESPERRA.scythe.thrustDamage, blockable: true, knock: 1.4, fx: 8, label: "scythe_thrust" });
            });
          }
        });
        const last = p2 ? t.hit3 : t.hit2 + 12;
        run.windows(t.hit1, last - t.hit1 + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 02 Needle Procession
  needleProcession() {
    const self = this;
    return {
      id: "needle_procession",
      name: "Needle Procession",
      index: 2,
      cooldown: VESPERRA.procession.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 5 && d <= 17 ? 3 : 0.9;
      },
      run(run) {
        const e = run.enc;
        const t = beats("needle_procession", run.phase);
        const p2 = run.phase === 2;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const yaw = e.loco.yaw;
        const orderIndex = e.rng.int(0, LANE_ORDERS.length - 1);
        const order = LANE_ORDERS[orderIndex];
        run.variant(orderIndex);
        const C = VESPERRA.procession;
        let last = 0;
        order.forEach((lane, k) => {
          const hit = t.first + k * t.gap;
          last = hit;
          let shape;
          if (p2) {
            const d = thetaToDir(yawToTheta(yaw) + lane * C.fan);
            shape = new Lane(b.x + d.x * 1.5, b.z + d.z * 1.5, b.x + d.x * (1.5 + C.length), b.z + d.z * (1.5 + C.length), C.halfWidth);
          } else {
            const a0 = localToWorld(b, yaw, lane * C.spacing, 0, 1.5);
            const a1 = localToWorld(b, yaw, lane * C.spacing, 0, 1.5 + C.length);
            shape = new Lane(a0.x, a0.z, a1.x, a1.z, C.halfWidth);
          }
          run.strike(hit, { shape, warn: hit - (t.plant + k * 4), damage: C.damage, fx: 9, sound: S("lane_erupt"), knockUp: 0.3, label: `procession_${k}` });
        });
        if (p2) {
          run.at(t.cross - 18, () => {
            const tg = e.targeting.primary(e.timeline.now) ?? run.target;
            const c = tg ? tg.location : localToWorld(b, yaw, 0, 0, 8);
            const th = yawToTheta(yaw);
            for (const off of [0, 90]) {
              const d = thetaToDir(th + off + 45);
              e.hazards.strike({
                shape: new Lane(c.x - d.x * 7, c.z - d.z * 7, c.x + d.x * 7, c.z + d.z * 7, C.halfWidth),
                warn: 18,
                tag: run.tag,
                damage: C.damage,
                fx: 8,
                sound: S("lane_erupt"),
                knockUp: 0.3,
                label: "procession_cross"
              });
            }
          });
          last = t.cross;
        }
        run.windows(t.plant, last - t.plant + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 03 Royal Molting
  royalMolting() {
    const self = this;
    return {
      id: "royal_molting",
      name: "Royal Molting",
      index: 3,
      cooldown: VESPERRA.molting.cooldown,
      weight: (e) => {
        const near = e.targeting.participants().filter((p) => distXZ(p.location, e.boss.location) < 7).length;
        return 1.6 + near * 1.1;
      },
      run(run) {
        const e = run.enc;
        const t = beats("royal_molting", run.phase);
        const p2 = run.phase === 2;
        const b = e.boss.location;
        const M = VESPERRA.molting;
        const base = self.front() + (e.rng.chance(0.5) ? 0 : 180 / M.plates);
        const wave = (at, offset, markFrom) => {
          for (let i = 0; i < M.plates; i++) {
            const d = thetaToDir(base + offset + i * 360 / M.plates);
            const from = { x: b.x + d.x * 2, y: e.arena.floorY + 1.3, z: b.z + d.z * 2 };
            run.at(markFrom, () => e.hazards.projectile({
              tag: run.tag,
              delay: at - markFrom,
              from,
              dir: d,
              speed: M.speed,
              range: M.range,
              radius: M.radius,
              particle: P("plate"),
              damage: M.damage,
              blockable: true,
              knock: 0.7,
              label: "molting_plate"
            }));
          }
        };
        wave(t.launch, 0, 2);
        let last = t.launch;
        if (p2) {
          wave(t.second, 180 / M.plates, t.launch + 2);
          last = t.second;
        }
        run.at(t.launch, () => {
          self.molts++;
          e.setProp("abm:molt", Math.min(2, self.molts));
          e.save();
        });
        const flight = Math.ceil(M.range / M.speed);
        run.windows(t.launch, last - t.launch + flight, Math.max(8, t.end - last - flight));
      }
    };
  }
  // ------------------------------------------------------------------ 04 Cocoon Edict
  cocoonEdict() {
    const self = this;
    return {
      id: "cocoon_edict",
      name: "Cocoon Edict",
      index: 4,
      cooldown: VESPERRA.cocoon.cooldown,
      weight: (e) => {
        if (e.helpers.count("anchor") > 0) return 0;
        const d = self.dist(e);
        return d > 8 ? 2.6 : 1.1;
      },
      run(run) {
        const e = run.enc;
        const t = beats("cocoon_edict", run.phase);
        const i = run.phase - 1;
        const n = VESPERRA.cocoon.anchors[i];
        const radius = VESPERRA.cocoon.radius[i];
        const hold = t.constrict - t.spawn;
        let pts = [];
        run.at(t.spawn, () => {
          const who = (e.targeting.count() > 1 && e.rng.chance(0.5) ? e.targeting.other(e.rng, run.target) : run.target) ?? run.target;
          const c = who ? e.arena.clampInside(who.location.x, who.location.z, radius + 1) : { x: e.arena.cx, z: e.arena.cz };
          const a0 = e.rng.range(0, 360);
          pts = [];
          for (let k = 0; k < n; k++) {
            const d = thetaToDir(a0 + k * 360 / n);
            const p = { x: c.x + d.x * radius, z: c.z + d.z * radius };
            pts.push(p);
            e.helpers.spawn("abm:cocoon_anchor", e.arena.at(p, 0.05), "anchor", { lifetime: hold + 24, data: { run: run.seq } });
          }
          const y = e.arena.floorY + 1.3;
          const pen = e.visuals.pen(P("thread"), P("tg_arc"), void 0, y, hold / 20);
          for (let k = 0; k < n; k++) {
            const a = pts[k];
            const q2 = pts[(k + 1) % n];
            pen.line(a.x, a.z, q2.x, q2.z);
          }
          e.hazards.strike({
            shape: new Polygon(pts),
            warn: hold,
            tag: run.tag,
            damage: VESPERRA.cocoon.damage,
            label: "cocoon_constrict",
            effects: [{ id: "slowness", ticks: VESPERRA.cocoon.slowTicks, amp: 1 }],
            sound: S("cocoon_snap"),
            condition: () => {
              const alive = e.helpers.of("anchor").filter((h) => h.data.run === run.seq).length;
              if (alive < n) trace("cocoon_broken", { alive, needed: n });
              return alive >= n;
            }
          });
        });
        run.at(t.constrict + 8, () => e.helpers.removeKind("anchor"));
        run.windows(t.spawn, hold + 2, Math.max(8, t.end - t.constrict - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 05 False Submission
  falseSubmission() {
    const self = this;
    return {
      id: "false_submission",
      name: "False Submission",
      index: 5,
      cooldown: VESPERRA.feint.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d < 10 ? 1.9 : 0.5;
      },
      run(run) {
        const e = run.enc;
        const t = beats("false_submission", run.phase);
        const F = VESPERRA.feint;
        if (run.target) e.loco.facePoint(run.target.location);
        const thrust = (cue, at, reaim) => {
          run.at(cue, () => {
            if (reaim) {
              const tg = e.targeting.primary(e.timeline.now) ?? run.target;
              if (tg) e.loco.facePoint(tg.location);
            }
            const o = e.boss.location;
            const d = thetaToDir(yawToTheta(e.loco.yaw));
            const lane = new Lane(o.x + d.x * 1, o.z + d.z * 1, o.x + d.x * (F.reach + 3.5), o.z + d.z * (F.reach + 3.5), F.halfWidth);
            e.hazards.strike({ shape: lane, warn: at + 3 - cue, tag: run.tag, damage: F.damage, blockable: true, knock: 1.6, knockUp: 0.3, fx: 10, label: "feint_thrust" });
            for (let k = 1; k <= t.dash; k++) {
              run.at(at + k, () => {
                e.loco.relocate({ x: o.x + d.x * F.reach * (k / t.dash), z: o.z + d.z * F.reach * (k / t.dash) });
              });
            }
          });
        };
        thrust(t.cue, t.thrust, false);
        let last = t.thrust + t.dash;
        if (run.phase === 2) {
          thrust(t.cue2, t.thrust2, true);
          last = t.thrust2 + t.dash;
        }
        run.at(last, () => {
          self.exposedUntil = e.timeline.now + (t.end - last - 12);
        });
        run.windows(t.thrust, last - t.thrust + 2, Math.max(10, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 06 The Heirs
  theHeirs() {
    const self = this;
    return {
      id: "the_heirs",
      name: "The Heirs",
      index: 6,
      cooldown: VESPERRA.heirs.cooldown,
      weight: (e) => {
        if (e.helpers.count("heir") >= VESPERRA.heirs.max) return 0;
        return self.armor.anyBroken() || e.phase === 2 ? 2.4 : 0.7;
      },
      run(run) {
        const e = run.enc;
        const t = beats("the_heirs", run.phase);
        run.at(t.detach, () => {
          const b = e.boss.location;
          const need = VESPERRA.heirs.max - e.helpers.count("heir");
          const sides = [-1, 1];
          for (let k = 0; k < need; k++) {
            const side = sides[k % 2];
            const at = localToWorld(b, e.loco.yaw, side * 2.4, 0, 0.6);
            const pos = e.arena.clampInside(at.x, at.z, 1);
            const h = e.helpers.spawn("abm:vesperra_heir", e.arena.at(pos, 0.05), "heir", {
              lifetime: VESPERRA.heirs.lifetime,
              yaw: e.loco.yaw,
              data: { side, nextBite: e.timeline.now + 40, biting: 0 }
            });
            if (h) e.visuals.decor(P("molt"), { x: pos.x, y: e.arena.floorY + 0.8, z: pos.z });
          }
        });
        run.windows(t.detach, 4, Math.max(8, t.end - t.detach - 4));
      }
    };
  }
  /** Heirs stand between the attackers and whatever is exposed, and snap at anyone who closes in. */
  tickHeirs(now) {
    const e = this.enc;
    const heirs = e.helpers.of("heir");
    if (heirs.length === 0) return;
    const open = ["l", "r"].filter((r) => this.armor.broken(r));
    const b = e.boss.location;
    heirs.forEach((h, i) => {
      const region = open.length > 0 ? open[i % open.length] : h.data.side < 0 ? "l" : "r";
      const post = this.armor.anchor(region);
      const threat = e.targeting.nearest(post);
      let goal = { x: post.x, z: post.z };
      if (threat) {
        const d2 = distXZ(threat.location, post) || 1;
        const k = Math.min(1.4, d2 * 0.4) / d2;
        goal = { x: post.x + (threat.location.x - post.x) * k, z: post.z + (threat.location.z - post.z) * k };
      }
      const l = h.entity.location;
      const dx = goal.x - l.x;
      const dz = goal.z - l.z;
      const d = Math.hypot(dx, dz);
      try {
        if (h.data.biting <= now && d > 0.35) {
          const step = Math.min(VESPERRA.heirs.speed, d);
          const v = h.entity.getVelocity();
          h.entity.applyImpulse({ x: dx / d * step - v.x, y: 0, z: dz / d * step - v.z });
        }
        const face = threat ? threat.location : b;
        h.entity.setRotation({ x: 0, y: Math.atan2(-(face.x - l.x), face.z - l.z) * 180 / Math.PI });
      } catch {
        return;
      }
      if (threat && now >= h.data.nextBite && distXZ(threat.location, l) <= VESPERRA.heirs.biteRange) {
        h.data.nextBite = now + VESPERRA.heirs.biteCooldown;
        h.data.biting = now + VESPERRA.heirs.biteWarn + 6;
        try {
          h.entity.setProperty("abm:anim", 1);
        } catch {
          return;
        }
        const tag = `heir${h.id}`;
        const at = h.entity.location;
        e.hazards.strike({
          shape: new Circle(at.x, at.z, VESPERRA.heirs.biteRange),
          warn: VESPERRA.heirs.biteWarn,
          tag,
          damage: VESPERRA.heirs.bite,
          blockable: true,
          knock: 1,
          knockUp: 0.2,
          from: b,
          label: "heir_bite",
          condition: () => h.entity.isValid
        });
        e.timeline.after(VESPERRA.heirs.biteWarn + 6, () => {
          try {
            if (h.entity.isValid) h.entity.setProperty("abm:anim", 0);
          } catch {
          }
        }, tag);
      }
    });
  }
  // ------------------------------------------------------------------ 07 Coronation of Fracture
  coronation() {
    const self = this;
    return {
      id: "coronation",
      name: "Coronation of Fracture",
      index: 7,
      ultimate: true,
      interruptible: false,
      cooldown: VESPERRA.coronation.cooldown,
      weight: (e) => e.healthFraction() < 0.9 ? 5 : 0,
      run(run) {
        const e = run.enc;
        const t = beats("coronation", run.phase);
        const p2 = run.phase === 2;
        const base = e.rng.range(0, 360);
        const step = 360 / 7;
        let last = 0;
        for (let i = 0; i < t.count; i++) {
          const mark = t.first + i * t.interval;
          last = mark + t.warn;
          run.at(mark, () => {
            const ps = e.targeting.participants();
            const who = ps.length > 0 ? ps[i % ps.length] : void 0;
            const aim = who ? { x: who.location.x, z: who.location.z } : e.arena.randomPoint(e.rng, 4);
            const theta = base + i * step;
            const paths = [self.chord(aim, theta, VESPERRA.coronation.halfWidth)];
            if (p2) paths.push(self.chord(aim, theta + 90, VESPERRA.coronation.halfWidth));
            for (const lane of paths) {
              e.hazards.strike({
                shape: lane,
                warn: t.warn,
                tag: run.tag,
                damage: VESPERRA.coronation.damage,
                fx: 12,
                sound: S("fracture_erupt"),
                knockUp: 0.35,
                label: `coronation_${i}`,
                onStrike: () => e.visuals.scatter(P("fracture"), lane.sample(e.rng, 8), e.arena.floorY + 0.06)
              });
            }
          });
        }
        run.windows(t.first, last - t.first + 2, Math.max(10, t.end - last - 2));
      }
    };
  }
};
var MODULE4 = {
  create: (enc) => new VesperraController(enc),
  arena: { structure: "abm:hall_of_endless_succession", size: 45, height: 14, nameKey: "abm.arena.vesperra" },
  helpers: ["abm:vesperra_heir", "abm:cocoon_anchor"]
};

// src/main.ts
boot({ vesperra: MODULE4, cantor: MODULE, nomos: MODULE2, orison: MODULE3 });
