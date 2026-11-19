// src/boot.ts
import { system as system5, world as world6 } from "@minecraft/server";

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
    cantor: { health: 520, phase2At: 0.5, arenaRadius: 19, arenaShape: "circle", clearance: 11, leashInset: 6, damageTaken: 0.125 },
    nomos: { health: 560, phase2At: 0.4, arenaRadius: 20, arenaShape: "square", clearance: 9, leashInset: 4, damageTaken: 0.125 },
    orison: { health: 600, phase2At: 0.35, arenaRadius: 18, arenaShape: "circle", clearance: 10, leashInset: 4, damageTaken: 0.128 }
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
var Union = class {
  constructor(parts) {
    this.parts = parts;
    this.cx = parts.reduce((s, p) => s + p.cx, 0) / Math.max(1, parts.length);
    this.cz = parts.reduce((s, p) => s + p.cz, 0) / Math.max(1, parts.length);
    this.reach = Math.max(0, ...parts.map((p) => Math.hypot(p.cx - this.cx, p.cz - this.cz) + p.reach));
  }
  contains(x, z) {
    for (const p of this.parts) if (p.contains(x, z)) return true;
    return false;
  }
  draw(pen) {
    for (const p of this.parts) p.draw(pen);
  }
  sample(rng, n) {
    const out = [];
    if (this.parts.length === 0) return out;
    for (let i = 0; i < n; i++) out.push(...rng.pick(this.parts).sample(rng, 1));
    return out;
  }
};
var Except = class {
  constructor(bounds, safe) {
    this.bounds = bounds;
    this.safe = safe;
    this.cx = bounds.cx;
    this.cz = bounds.cz;
    this.reach = bounds.reach;
  }
  contains(x, z) {
    if (!this.bounds.contains(x, z)) return false;
    for (const s of this.safe) if (s.contains(x, z)) return false;
    return true;
  }
  draw(pen) {
    for (const s of this.safe) s.draw(pen);
  }
  sample(rng, n) {
    const out = [];
    let guard = n * 20;
    while (out.length < n && guard-- > 0) {
      const p = this.bounds.sample(rng, 1)[0];
      if (p && this.contains(p.x, p.z)) out.push(p);
    }
    return out;
  }
};

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
var seenErrors = /* @__PURE__ */ new Map();
var announced = 0;
var notifier;
function setErrorNotifier(f) {
  notifier = f;
}
function report(where, err) {
  const head = (err instanceof Error ? err.message : String(err)).split("\n")[0];
  const msg = err instanceof Error ? `${err.message}
${err.stack ?? ""}` : String(err);
  const s = current();
  if (s) s("error", { where, msg });
  const key = `${where}|${head}`;
  const n = (seenErrors.get(key) ?? 0) + 1;
  seenErrors.set(key, n);
  if (n === 1) {
    console.warn(`[abm] error in ${where}: ${msg}`);
    if (notifier && announced < 6) {
      announced++;
      try {
        notifier(`§7[The Abandoned Miracles] internal problem in §f${where}§7: ${head}`);
      } catch {
      }
    }
  } else if (n % 200 === 0) {
    console.warn(`[abm] error in ${where} (x${n}): ${head}`);
  }
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
          if (this.enc.arena.contains(c.cx, c.cz, -2)) {
            for (const p of this.inside(c)) {
              if (hit.has(p.id)) continue;
              if (this.enc.damage.hit(p, o, this.enc.timeline.now) > 0) {
                hit.add(p.id);
                o.onHit?.(p);
              }
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
    this.yawMisses = 0;
    this.yawByTeleport = false;
    /** Set when velocity impulses turn out not to move this entity: walk in validated steps instead. */
    this.stepwise = false;
    this.stalls = 0;
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
  /**
   * Turn the entity. setRotation is the cheap way; if the engine does not keep the yaw it was given
   * (the entity's own body control can win), this notices and turns by teleporting in place instead.
   */
  applyYaw() {
    const boss = this.enc.boss;
    try {
      if (!this.yawByTeleport && this.lastApplied !== void 0) {
        const got = boss.getRotation().y;
        if (Math.abs(angDiff(got, this.lastApplied)) > 12) {
          if (++this.yawMisses >= 6) {
            this.yawByTeleport = true;
            trace("yaw_fallback", { boss: this.enc.key });
          }
        } else {
          this.yawMisses = 0;
        }
      }
      if (this.yawByTeleport) boss.teleport(boss.location, { rotation: { x: 0, y: this.yaw }, keepVelocity: true });
      else boss.setRotation({ x: 0, y: this.yaw });
      this.lastApplied = this.yaw;
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
      if (this.impulses()) {
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
  impulses() {
    return CONFIG.movement.mode === "impulse" && !this.stepwise;
  }
  stopVelocity() {
    if (!this.impulses()) return;
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
      this.stalls = 0;
      return;
    }
    if (now - this.progress.tick < 40) return;
    this.progress = { x: l.x, z: l.z, tick: now };
    if (this.impulses() && ++this.stalls >= 2) {
      this.stepwise = true;
      trace("step_fallback", { boss: this.enc.key });
    }
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
var STARVED = 900;
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
      if (idle > STARVED) w *= 1 + (idle - STARVED) / 150;
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
    /** Consecutive ticks whose combat logic threw. */
    this.faults = 0;
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
    if (!this.boss.isValid) return void 0;
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
      this.faults = 0;
    } catch (e) {
      report(`${this.key} tick`, e);
      if (++this.faults >= 60) {
        this.faults = 0;
        this.host.abandon(this);
        return;
      }
    }
    if (this.ended) return;
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
    /** Encounters whose whole tick threw, with the number of consecutive failures. */
    this.failing = /* @__PURE__ */ new Map();
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
        this.failing.delete(e);
      } catch (err) {
        report(`encounter ${e.key}`, err);
        const n = (this.failing.get(e) ?? 0) + 1;
        this.failing.set(e, n);
        if (n >= 60) {
          this.failing.delete(e);
          try {
            this.abandon(e);
          } catch (err2) {
            report(`abandon ${e.key}`, err2);
          }
        }
      }
    }
    if (this.ticks % 200 === 0) this.sweepOrphans();
  }
  // ------------------------------------------------------------------ creating encounters
  /**
   * Summon a boss at a floor position chosen by a player. Never edits terrain:
   * if the place cannot host the arena the summon is refused with a reason.
   */
  trySummon(by, key, floor, force = false) {
    if (!this.factories.has(key)) return { ok: false, reason: "unknown" };
    const stats = CONFIG.bosses[key];
    const dim = by.dimension;
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
      const yaw = dirToYaw(by.location.x - floor.x, by.location.z - floor.z);
      boss = dim.spawnEntity(BOSS_TYPE[key], { x: floor.x, y: floor.y + 0.05, z: floor.z }, { initialRotation: yaw });
    } catch (e) {
      report("spawn boss", e);
      return { ok: false, reason: "spawn" };
    }
    const enc = this.create(boss, key, floor);
    trace("summon", { boss: key, by: by.name ?? "", coverage: scan.coverage });
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
  EntityComponentTypes as EntityComponentTypes3,
  EquipmentSlot as EquipmentSlot3,
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

// src/kit.ts
import {
  EnchantmentTypes,
  EntityComponentTypes as EntityComponentTypes2,
  EquipmentSlot as EquipmentSlot2,
  ItemComponentTypes,
  ItemStack as ItemStack3
} from "@minecraft/server";
function enchanted(id, enchantments, amount = 1) {
  const stack = new ItemStack3(id, amount);
  try {
    const c = stack.getComponent(ItemComponentTypes.Enchantable);
    if (c) {
      for (const [name, level] of Object.entries(enchantments)) {
        const type = EnchantmentTypes.get(name);
        if (!type) continue;
        try {
          c.addEnchantment({ type, level });
        } catch {
        }
      }
    }
  } catch (e) {
    report("kit enchant", e);
  }
  return stack;
}
function giveKit(p) {
  try {
    const eq = p.getComponent(EntityComponentTypes2.Equippable);
    const inv = p.getComponent(EntityComponentTypes2.Inventory)?.container;
    const stow = (stack) => {
      const left = inv ? inv.addItem(stack) : stack;
      if (left) p.dimension.spawnItem(left, p.location);
    };
    const wear = (slot, stack) => {
      if (eq && !eq.getEquipment(slot)) eq.setEquipment(slot, stack);
      else stow(stack);
    };
    const armour = { protection: 4, unbreaking: 3 };
    wear(EquipmentSlot2.Head, enchanted("minecraft:diamond_helmet", armour));
    wear(EquipmentSlot2.Chest, enchanted("minecraft:diamond_chestplate", armour));
    wear(EquipmentSlot2.Legs, enchanted("minecraft:diamond_leggings", armour));
    wear(EquipmentSlot2.Feet, enchanted("minecraft:diamond_boots", armour));
    wear(EquipmentSlot2.Offhand, new ItemStack3("minecraft:shield", 1));
    stow(enchanted("minecraft:diamond_sword", { sharpness: 5, unbreaking: 3 }));
    stow(new ItemStack3("minecraft:cooked_beef", 32));
    stow(new ItemStack3("minecraft:golden_apple", 8));
    p.sendMessage({ rawtext: [{ translate: "abm.kit.given" }] });
  } catch (e) {
    report("kit", e);
  }
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
function raiseArenaAt(dim, floor, key) {
  const info = arenaOf(key);
  if (!info) return false;
  const half = Math.floor(info.size / 2);
  try {
    world4.structureManager.place(info.structure, dim, {
      x: Math.floor(floor.x) - half,
      y: Math.floor(floor.y) - 1,
      z: Math.floor(floor.z) - half
    });
    return true;
  } catch (e) {
    report("raiseArena", e);
    return false;
  }
}
function raiseArena(p, key) {
  const ok2 = raiseArenaAt(p.dimension, p.location, key);
  if (ok2) p.sendMessage(tr("abm.arena.built"));
  return ok2;
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
var summonHere = () => void 0;
function setSummonHandler(fn) {
  summonHere = fn;
}
async function openCodex(p) {
  try {
    const op = isOperator(p);
    const keys = BOSS_KEYS.filter((k) => manager.has(k));
    const form = new ActionFormData().title(tr("abm.ui.title")).body({ rawtext: [{ translate: "abm.ui.body1" }, { text: "\n\n" }, { translate: "abm.ui.body2" }] });
    for (const k of keys) form.button(tr(`entity.${bossType(k)}.name`));
    if (op) form.button(tr("abm.ui.settings")).button(tr("abm.ui.arena")).button(tr("abm.ui.dismiss")).button(tr("abm.ui.kit"));
    const r = await form.show(p);
    if (r.canceled || r.selection === void 0) return;
    if (r.selection < keys.length) {
      const k = keys[r.selection];
      const s = CONFIG.bosses[k];
      const info = await new MessageFormData().title(tr(`entity.${bossType(k)}.name`)).body({ rawtext: [{ translate: `abm.lore.${k}` }, { text: "\n\n" }, { translate: "abm.summon.need", with: [String(s.arenaRadius * 2 + 1), String(s.clearance)] }] }).button1(tr("abm.ui.cancel")).button2(tr(op ? "abm.ui.summon_here" : "abm.ui.ok")).show(p);
      if (op && !info.canceled && info.selection === 1) {
        const l = p.location;
        summonHere(p, k, { x: Math.floor(l.x) + 0.5, y: Math.floor(l.y), z: Math.floor(l.z) + 0.5 });
      }
      return;
    }
    const extra = r.selection - keys.length;
    if (extra === 0) await settingsMenu(p);
    else if (extra === 1) await arenaMenu(p);
    else if (extra === 2) {
      const enc = manager.nearest(p.dimension, p.location);
      if (enc) manager.cancel(enc);
      p.sendMessage(tr("abm.msg.cancelled"));
    } else if (extra === 3) {
      giveKit(p);
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
    const eq = p.getComponent(EntityComponentTypes3.Equippable);
    const held = eq?.getEquipment(EquipmentSlot3.Mainhand);
    if (!eq || !held || held.typeId !== typeId) return;
    if (held.amount > 1) {
      held.amount -= 1;
      eq.setEquipment(EquipmentSlot3.Mainhand, held);
    } else {
      eq.setEquipment(EquipmentSlot3.Mainhand, void 0);
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
function flourish(p, key) {
  try {
    p.dimension.playSound(TROPHY_SOUND[key], p.location, { volume: 0.8 });
    p.onScreenDisplay.setActionBar({ rawtext: [{ translate: `abm.trophy.${key}` }] });
  } catch (e) {
    report("trophy", e);
  }
}
function initItems() {
  setSummonHandler((p, key, floor) => {
    useSeal(p, key, floor);
  });
  const onBlock = (player, id, at) => {
    if (!id || !player.isValid) return;
    const key = SEAL_TO_KEY.get(id);
    if (key) {
      if (!debounce(player)) return;
      useSeal(player, key, { x: at.x + 0.5, y: at.y + 1, z: at.z + 0.5 });
    } else if (id === CODEX_ITEM) {
      if (debounce(player)) void openCodex(player);
    } else {
      const trophy = TROPHY_TO_KEY.get(id);
      if (trophy && debounce(player)) flourish(player, trophy);
    }
  };
  world5.beforeEvents.playerInteractWithBlock.subscribe((ev) => {
    if (!ev.isFirstEvent) return;
    const id = ev.itemStack?.typeId;
    if (!id || !(SEAL_TO_KEY.has(id) || id === CODEX_ITEM || TROPHY_TO_KEY.has(id))) return;
    const player = ev.player;
    const at = { x: ev.block.x, y: ev.block.y, z: ev.block.z };
    system2.run(() => {
      try {
        onBlock(player, id, at);
      } catch (e) {
        report("item on block", e);
      }
    });
  });
  world5.afterEvents.playerInteractWithBlock.subscribe((ev) => {
    if (!ev.isFirstEvent) return;
    onBlock(ev.player, ev.beforeItemStack?.typeId ?? ev.itemStack?.typeId, ev.block);
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
    if (trophy && debounce(p)) flourish(p, trophy);
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
        if (action === "phase2") system3.run(() => enc.force("phase2"));
        else if (action === "kill") system3.run(() => enc.force("death"));
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

// src/scriptevents.ts
import { Player as Player8, system as system4 } from "@minecraft/server";
function parseBoss(word) {
  return BOSS_KEYS.find((k) => k === word);
}
function initScriptEvents() {
  system4.afterEvents.scriptEventReceive.subscribe(
    (ev) => {
      try {
        const words = ev.message.trim().split(/\s+/).filter((w) => w.length > 0);
        let dim;
        let at;
        let name = "command";
        if (ev.sourceEntity && ev.sourceEntity.isValid) {
          dim = ev.sourceEntity.dimension;
          at = ev.sourceEntity.location;
          if (ev.sourceEntity instanceof Player8) name = ev.sourceEntity.name;
        } else if (ev.sourceBlock) {
          dim = ev.sourceBlock.dimension;
          at = { x: ev.sourceBlock.x + 0.5, y: ev.sourceBlock.y + 1, z: ev.sourceBlock.z + 0.5 };
        } else {
          return;
        }
        const floor = { x: Math.floor(at.x) + 0.5, y: Math.floor(at.y), z: Math.floor(at.z) + 0.5 };
        if (ev.id === "abm:summon") {
          const key = parseBoss(words[0]);
          if (!key || !manager.has(key)) return;
          const res = manager.trySummon({ dimension: dim, location: at, name }, key, floor, words[1] === "force");
          if (!res.ok && ev.sourceEntity instanceof Player8) {
            ev.sourceEntity.sendMessage({ rawtext: [{ translate: `abm.summon.fail.${res.reason ?? "unknown"}`, with: [String(Math.round((res.coverage ?? 0) * 100))] }] });
          }
        } else if (ev.id === "abm:dismiss") {
          const enc = manager.nearest(dim, at);
          if (enc) manager.cancel(enc);
        } else if (ev.id === "abm:kit") {
          if (ev.sourceEntity instanceof Player8) giveKit(ev.sourceEntity);
        } else if (ev.id === "abm:arena") {
          const key = parseBoss(words[0]);
          if (key && arenaOf(key)) raiseArenaAt(dim, floor, key);
        }
      } catch (e) {
        report("scriptevent", e);
      }
    },
    { namespaces: ["abm"] }
  );
}

// src/boot.ts
function boot(mods) {
  install(mods);
  setErrorNotifier((line) => {
    system5.run(() => {
      try {
        world6.sendMessage(line);
      } catch {
      }
    });
  });
  system5.beforeEvents.startup.subscribe((ev) => registerCommands(ev));
  const helpers = [];
  for (const k of installed()) {
    const m = moduleOf(k);
    manager.register(k, m.create);
    helpers.push(...m.helpers);
  }
  manager.init(helpers);
  initItems();
  initScriptEvents();
  const g = globalThis;
  if (g.__abmTrace) g.__abm = { manager, CONFIG };
}

// src/bosses/cantor/index.ts
import { MolangVariableMap as MolangVariableMap2 } from "@minecraft/server";

// shared/cantor.timings.json
var cantor_timings_default = {
  _comment: "Beat timings for Cantor XIII in game ticks from the start of each action. One beat = 10 ticks, one measure = 40 ticks. Shared by the script (hit windows) and the animation generator (keyframes).",
  beat: 10,
  measure: 40,
  intro: {
    wake: 40,
    toll: 80,
    total: 120
  },
  transition: {
    crack: 30,
    break: 60,
    unfold: 100,
    total: 140
  },
  stagger: {
    total: 40
  },
  death: {
    bell: 30,
    pipes: 60,
    pipeStep: 8,
    legs: 150,
    legStep: 16,
    total: 220
  },
  prime_downbeat: {
    p1: {
      strike: 30,
      end: 110
    },
    p2: {
      strike: 30,
      second: 54,
      end: 134
    }
  },
  counterpoint: {
    p1: {
      first: 40,
      second: 80,
      end: 220
    },
    p2: {
      first: 40,
      second: 64,
      end: 204
    }
  },
  glass_aria: {
    p1: {
      open: 16,
      first: 40,
      gap: 20,
      volleys: 3,
      end: 130
    },
    p2: {
      open: 14,
      first: 36,
      gap: 16,
      volleys: 4,
      wave: 52,
      end: 144
    }
  },
  held_note: {
    p1: {
      blast: 60,
      end: 100
    },
    p2: {
      blast: 52,
      echo: 84,
      end: 120
    }
  },
  silent_measure: {
    p1: {
      freeze: 20,
      strike: 80,
      end: 160
    },
    p2: {
      freeze: 16,
      strike: 72,
      second: 96,
      end: 176
    }
  },
  twin_resonance: {
    p1: {
      detach: 30,
      end: 60
    },
    p2: {
      detach: 24,
      end: 52
    }
  },
  final_requiem: {
    p1: {
      strikes: [
        60,
        100,
        140,
        180
      ],
      end: 224
    },
    p2: {
      strikes: [
        60,
        104,
        144,
        188
      ],
      end: 232
    }
  }
};

// src/bosses/cantor/tuning.ts
var CANTOR = {
  move: {
    p1: { speed: 0.06, turn: 2.6, home: 5, settle: 2.5 },
    p2: { speed: 0.085, turn: 3.6, home: 6.5, settle: 1.5 }
  },
  downbeat: {
    cooldown: [70, 60],
    damage: 13,
    secondDamage: 6,
    speed: 0.3,
    thickness: 1.6,
    minDoor: 3.4,
    /** Safe doors in the ring: count, width (degrees). */
    gaps: 3,
    gapWidth: 40,
    /** Phase II second ring: doors turned by this much and this wide, so the doors overlap. */
    secondShift: 20,
    secondWidth: 44
  },
  counterpoint: {
    cooldown: [220, 190],
    damage: 9,
    speed: [0.3, 0.34],
    thickness: 1.4,
    doorHalf: 2.5,
    doorSpacing: 13
  },
  aria: {
    cooldown: [160, 130],
    damage: 9,
    speed: 0.55,
    range: 20,
    radius: 0.55,
    warn: 24,
    fans: [[-40, -20, 0, 20, 40], [-30, -10, 10, 30]],
    /** Phase II positional wave: a half ring towards the aim with two doors. */
    waveSpeed: 0.3,
    waveReach: 16,
    waveArc: 200,
    waveGap: 34
  },
  heldNote: {
    cooldown: [200, 170],
    damage: 18,
    echoDamage: 14,
    halfAngle: 42,
    echoHalf: 30,
    inner: 3.2,
    range: 15
  },
  silent: {
    cooldown: [300, 260],
    damage: 14,
    secondDamage: 5,
    speed: 0.4,
    thickness: 1.6,
    gaps: 4,
    gapWidth: 34,
    secondShift: 14,
    secondWidth: 40,
    minDoor: 3.4,
    /** Rhythmic attacks that must have been played since the last Silent Measure. */
    needsRhythm: 2
  },
  twin: {
    cooldown: [480, 400],
    damage: 9,
    radius: 4.5,
    warn: 34,
    intervals: [[70, 90], [50, 70]],
    lifetime: [320, 400],
    firstDelay: 20,
    health: 24,
    /** Destroying both bells staggers Cantor for this many ticks. */
    staggerTicks: 40
  },
  requiem: {
    cooldown: [720, 680],
    damage: 17,
    /** Floor ring radii (they match the copper rings laid into the basilica floor). */
    inner: 6,
    middle: 12,
    outer: 13,
    far: 9
  }
};

// src/bosses/cantor/index.ts
var S = (id) => `abm.cantor.${id}`;
var P = (id) => `abm:cantor_${id}`;
var BEAT = cantor_timings_default.beat;
var MEASURE = cantor_timings_default.measure;
var BROKEN_BEATS = [0, 12, 20, 32];
var beats = (name, phase) => cantor_timings_default[name][phase === 2 ? "p2" : "p1"];
function doors(base, count, width) {
  const out = [];
  for (let k = 0; k < count; k++) out.push([base + k * 360 / count - width / 2, width]);
  return out;
}
function widen(gaps, r, min) {
  const cap = 360 / gaps.length - 8;
  return gaps.map(([g0, gw]) => {
    const w = Math.min(cap, Math.max(gw, min / Math.max(0.5, r) * (180 / Math.PI)));
    return [g0 + gw / 2 - w / 2, w];
  });
}
var CantorController = class extends BossController {
  constructor(enc) {
    super(enc);
    this.key = "cantor";
    this.displayName = "Cantor XIII";
    this.phase2Name = "The Broken Symphony";
    this.trophyItem = "abm:bell_fragment";
    this.style = {
      line: P("tg_line"),
      arc: P("tg_arc"),
      disc: P("tg_disc"),
      safeLine: P("safe_line"),
      safeArc: P("safe_arc"),
      strike: P("strike")
    };
    /** The beat is withheld (no pulse, dark windows) until this encounter tick. */
    this.silentUntil = 0;
    /** Rhythmic attacks played since the last Silent Measure. */
    this.sinceSilent = 0;
    this.nextIdleSound = 160;
    /** Encounter ticks at which attacks started (asserted on by the rhythm test). */
    this.attackStarts = [];
    this.attacks = [
      this.primeDownbeat(),
      this.counterpoint(),
      this.glassAria(),
      this.heldNote(),
      this.silentMeasure(),
      this.twinResonance(),
      this.finalRequiem()
    ];
  }
  // ------------------------------------------------------------------ framework hooks
  configure(phase) {
    const m = phase === 2 ? CANTOR.move.p2 : CANTOR.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }
  intro() {
    return cantor_timings_default.intro.total;
  }
  phaseTransition() {
    const e = this.enc;
    const t = cantor_timings_default.transition;
    e.helpers.removeKind("bell");
    e.setProp("abm:bells_out", 0);
    this.endSilence();
    this.silentUntil = e.timeline.now + t.total;
    e.timeline.after(t.break, () => {
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 6))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: (p.location.x - c.x) / d * 1.5, z: (p.location.z - c.z) / d * 1.5 }, 0.3);
        } catch {
        }
      }
      e.visuals.decor(P("dust"), { x: c.x, y: e.arena.floorY + 0.4, z: c.z });
    }, "phase");
    return t.total;
  }
  phase2Ready() {
    this.silentUntil = 0;
    this.sinceSilent = 0;
  }
  death() {
    const e = this.enc;
    const t = cantor_timings_default.death;
    this.endSilence();
    this.silentUntil = e.timeline.now + t.total + 1e3;
    e.setProp("abm:bells_out", 0);
    for (let i = 0; i < 3; i++) {
      e.timeline.after(t.legs + i * t.legStep + 9, () => {
        const c = e.boss.location;
        e.visuals.scatter(P("dust"), new Circle(c.x, c.z, 3.5).sample(e.rng, 4), e.arena.floorY + 0.4);
      }, "death");
    }
    return t.total;
  }
  /** Cantor holds the middle of its hall and turns, deliberately, to face whoever it is playing to. */
  position(target) {
    const e = this.enc;
    const m = e.phase === 2 ? CANTOR.move.p2 : CANTOR.move.p1;
    const b = e.boss.location;
    let anchor = { x: e.arena.cx, z: e.arena.cz };
    if (e.phase === 2 && target) {
      const dx = target.location.x - e.arena.cx;
      const dz = target.location.z - e.arena.cz;
      const d = Math.hypot(dx, dz) || 1;
      const k = Math.min(m.home - 1.5, d * 0.35) / d;
      anchor = { x: e.arena.cx + dx * k, z: e.arena.cz + dz * k };
    }
    const off = distXZ(b, anchor);
    if (off > (e.phase === 2 ? m.settle + 1.2 : m.home)) {
      e.loco.goTo(anchor, m.settle);
      return true;
    }
    e.loco.halt();
    if (target) e.loco.turnToward(e.loco.yawTo(target.location), 4);
    return false;
  }
  tick() {
    const e = this.enc;
    const now = e.timeline.now;
    if (!e.sm.inCombat) return;
    if (!e.sm.busy) {
      const due = Math.max(e.nextAttackAt, now);
      e.nextAttackAt = Math.ceil(due / BEAT) * BEAT;
    }
    if (now >= this.silentUntil) {
      const onBeat = e.phase === 2 ? BROKEN_BEATS.includes(now % MEASURE) : now % BEAT === 0;
      if (onBeat) {
        const b = e.boss.location;
        e.visuals.decor(P("beat"), { x: b.x, y: e.arena.floorY + 0.1, z: b.z });
        if (now % MEASURE === 0) e.audio.play(S("beat"), b, 0.5);
      }
    }
    this.tickBells(now);
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 200 + e.rng.int(0, 160);
    }
  }
  incoming(damage, _info) {
    const e = this.enc;
    e.defer(() => {
      const b = e.boss.location;
      e.audio.play(S("hit"), b, 0.7);
      e.visuals.decor(P("strike"), { x: b.x, y: b.y + 4, z: b.z });
    });
    return damage;
  }
  onHelperGone(h) {
    if (h.kind !== "bell") return;
    const e = this.enc;
    e.timeline.cancel(`bell${h.id}`);
    const left = e.helpers.count("bell");
    if (left === 0) e.setProp("abm:bells_out", 0);
    if (h.killed) {
      e.audio.play(S("bell_destroy"), e.boss.location);
      trace("bell_destroyed", { left });
      if (left === 0 && e.sm.inCombat) e.stagger(CANTOR.twin.staggerTicks);
    }
  }
  onAttackCancelled(def) {
    if (def.id === "silent_measure") this.endSilence();
  }
  cleanup() {
    this.silentUntil = 0;
  }
  // ------------------------------------------------------------------ shared helpers
  dist(e) {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }
  begin(run, rhythmic = true) {
    this.attackStarts.push(run.t0);
    if (rhythmic) this.sinceSilent++;
  }
  /** Distance from a point to the far side of the arena (how far a ring must travel to clear it). */
  reach(p) {
    const a = this.enc.arena;
    return a.radius * (a.square ? Math.SQRT2 : 1) + Math.hypot(p.x - a.cx, p.z - a.cz) + 1;
  }
  get floor() {
    return this.enc.arena.floorY + 0.08;
  }
  /**
   * A moving wave. Collision and picture come from the same shapeAt(t) on the
   * same ticks: this draws it on even ticks with marks that live exactly until
   * the next redraw, and the hazard system tests that same drawn shape.
   */
  wave(run, o) {
    const e = run.enc;
    run.at(o.shown, () => e.hazards.sweep({
      tag: run.tag,
      warn: o.start - o.shown,
      duration: o.duration,
      every: 1,
      draw: false,
      shapeAt: (tt) => o.shapeAt(tt - tt % 2),
      damage: o.damage,
      label: o.label,
      knock: o.knock ?? 0.6,
      knockUp: 0.2,
      from: o.from,
      fx: 2,
      sound: S("wave")
    }));
    for (let tt = 0; tt <= o.duration; tt += 2) {
      run.at(o.start + tt, () => o.shapeAt(tt).draw(e.visuals.pen(P("wave_line"), P("wave_arc"), void 0, this.floor, 3 / 20)));
    }
  }
  /** Mark the doors of a ring as safe wedges for `ticks`. */
  markDoors(c, gaps, r0, r1, ticks) {
    for (const [g0, gw] of gaps) this.enc.hazards.telegraph(new Ring(c.x, c.z, r0, r1, g0, gw), ticks, true);
  }
  flash(c, r) {
    const m = new MolangVariableMap2();
    m.setFloat("variable.r", r);
    this.enc.visuals.spawn(P("ring_flash"), { x: c.x, y: this.floor, z: c.z }, m);
  }
  endSilence() {
    this.enc.setProp("abm:silent", 0);
  }
  // ------------------------------------------------------------------ 01 Prime Downbeat
  primeDownbeat() {
    const self = this;
    return {
      id: "prime_downbeat",
      name: "Prime Downbeat",
      index: 1,
      cooldown: CANTOR.downbeat.cooldown,
      weight: (e) => self.dist(e) < 11 ? 3.2 : 2,
      run(run) {
        const e = run.enc;
        self.begin(run);
        const t = beats("prime_downbeat", run.phase);
        const D = CANTOR.downbeat;
        const b = e.boss.location;
        const c = { x: b.x, z: b.z };
        const R = self.reach(c);
        const duration = Math.ceil((R - 2) / D.speed);
        const base = e.rng.range(0, 360);
        const ringAt = (gaps) => (tt) => {
          const r = 2 + tt * D.speed;
          const r0 = Math.max(0.3, r - D.thickness / 2);
          return new Ring(c.x, c.z, r0, r + D.thickness / 2, 0, 360, widen(gaps, r0, D.minDoor));
        };
        const g1 = doors(base, D.gaps, D.gapWidth);
        self.markDoors(c, g1, 2.5, R, t.strike + duration);
        run.at(t.strike, () => self.flash(c, 3));
        let last = t.strike;
        self.wave(run, { shown: 0, start: t.strike, duration, shapeAt: ringAt(g1), damage: D.damage, label: "downbeat", from: c });
        if (run.phase === 2) {
          const g2 = doors(base + (e.rng.chance(0.5) ? 1 : -1) * D.secondShift, D.gaps, D.secondWidth);
          self.markDoors(c, g2, 2.5, R, t.second + duration);
          self.wave(run, { shown: 0, start: t.second, duration, shapeAt: ringAt(g2), damage: D.secondDamage, label: "downbeat_echo", from: c });
          run.at(t.second, () => self.flash(c, 3));
          last = t.second;
        }
        run.windows(t.strike, last - t.strike + duration, Math.max(10, t.end - last - duration));
      }
    };
  }
  // ------------------------------------------------------------------ 02 Counterpoint
  counterpoint() {
    const self = this;
    return {
      id: "counterpoint",
      name: "Counterpoint",
      index: 2,
      cooldown: CANTOR.counterpoint.cooldown,
      weight: (e) => (self.dist(e) > 7 ? 2.6 : 1.6) + (e.targeting.count() > 1 ? 0.8 : 0),
      run(run) {
        const e = run.enc;
        self.begin(run);
        const t = beats("counterpoint", run.phase);
        const K = CANTOR.counterpoint;
        const a = e.arena;
        const R = a.radius;
        const speed = K.speed[run.phase - 1];
        const duration = Math.ceil((2 * R + 2) / speed);
        const theta = e.rng.pick([0, 45, 90, 135, 180, 225, 270, 315]);
        const who = run.target;
        const voices = [
          { theta, start: t.first },
          { theta: theta + (e.rng.chance(0.5) ? 90 : -90), start: t.second }
        ];
        const fronts = [];
        for (const v of voices) {
          const d = thetaToDir(v.theta);
          const n = { x: -d.z, z: d.x };
          const u = who ? (who.location.x - a.cx) * n.x + (who.location.z - a.cz) * n.z : 0;
          let d1 = u - K.doorSpacing / 2 + e.rng.range(-1.2, 1.2);
          while (d1 > -2) d1 -= K.doorSpacing;
          while (d1 < -K.doorSpacing - 2) d1 += K.doorSpacing;
          const doorsAt = [d1, d1 + K.doorSpacing].filter((x) => Math.abs(x) < R - 3.5);
          if (doorsAt.length === 0) doorsAt.push(0);
          fronts.push((tt) => {
            const s = -(R + 1) + speed * tt;
            const h2 = R * R - s * s;
            if (tt < 0 || tt > duration || h2 <= 1) return new Union([]);
            const h = Math.sqrt(h2);
            const px = a.cx + d.x * s;
            const pz = a.cz + d.z * s;
            const cuts = doorsAt.map((x) => [x - K.doorHalf, x + K.doorHalf]).sort((p, q) => p[0] - q[0]);
            const parts = [];
            let from = -h;
            for (const [c0, c1] of [...cuts, [h, h]]) {
              const to = Math.min(h, c0);
              if (to - from > 0.4) parts.push(new Lane(px + n.x * from, pz + n.z * from, px + n.x * to, pz + n.z * to, K.thickness / 2));
              from = Math.max(from, c1);
            }
            return new Union(parts);
          });
          for (const x of doorsAt) {
            const half = Math.sqrt(Math.max(1, R * R - x * x));
            const cx = a.cx + n.x * x;
            const cz = a.cz + n.z * x;
            e.hazards.telegraph(new Lane(cx - d.x * half, cz - d.z * half, cx + d.x * half, cz + d.z * half, K.doorHalf - 0.3), v.start + duration, true);
          }
        }
        voices.forEach((v, i) => self.wave(run, {
          shown: 0,
          start: v.start,
          duration,
          damage: K.damage,
          label: `counterpoint_${i + 1}`,
          knock: 0.9,
          shapeAt: fronts[i]
        }));
        run.windows(t.first, t.second - t.first + duration, Math.max(8, t.end - t.second - duration));
      }
    };
  }
  // ------------------------------------------------------------------ 03 Glass Aria
  glassAria() {
    const self = this;
    return {
      id: "glass_aria",
      name: "Glass Aria",
      index: 3,
      cooldown: CANTOR.aria.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 4 && d <= 17 ? 2.8 : 1.2;
      },
      run(run) {
        const e = run.enc;
        self.begin(run);
        const t = beats("glass_aria", run.phase);
        const G = CANTOR.aria;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const aim = yawToTheta(e.loco.yaw);
        const ad = thetaToDir(aim);
        const from = { x: b.x + ad.x * 2.2, y: e.arena.floorY + 1.6, z: b.z + ad.z * 2.2 };
        const flight = Math.ceil(G.range / G.speed);
        let last = t.first;
        const groups = [[], []];
        for (let k = 0; k < t.volleys; k++) {
          const at = t.first + k * t.gap;
          last = at;
          const dirs = G.fans[k % 2].map((off) => thetaToDir(aim + off));
          groups[k % 2].push({ at, dirs });
          const shown = Math.max(2, at - G.warn);
          run.at(shown, () => {
            for (const d of dirs) e.hazards.telegraph(new Lane(from.x, from.z, from.x + d.x * G.range, from.z + d.z * G.range, G.radius), at - shown);
          });
          run.at(at, () => {
            for (const d of dirs) e.visuals.flyer(P("shard"), from, { x: d.x, y: 0, z: d.z }, G.speed * 20, flight / 20);
            e.audio.play(S("glass_shard"), from);
          });
        }
        let waveAt;
        let waveEnd = 0;
        if (run.phase === 2) {
          const gaps = [[aim - 50 - G.waveGap / 2, G.waveGap], [aim + 50 - G.waveGap / 2, G.waveGap]];
          const c = { x: b.x, z: b.z };
          const duration = Math.ceil((G.waveReach - 2) / G.waveSpeed);
          self.markDoors(c, gaps, 2.5, G.waveReach, t.wave + duration);
          waveEnd = t.wave + duration;
          waveAt = (tt) => new Ring(c.x, c.z, Math.max(0.3, 2 + tt * G.waveSpeed - 0.8), 2 + tt * G.waveSpeed + 0.8, aim - G.waveArc / 2, G.waveArc, gaps);
          for (let tt = 0; tt <= duration; tt += 2) {
            run.at(t.wave + tt, () => waveAt(tt).draw(e.visuals.pen(P("wave_line"), P("wave_arc"), void 0, self.floor, 3 / 20)));
          }
        }
        groups.forEach((volleys, gi) => {
          if (volleys.length === 0) return;
          const start = volleys[0].at;
          const end = Math.max(volleys[volleys.length - 1].at + flight, gi === 1 ? waveEnd : 0);
          const begin = gi === 1 && waveAt ? Math.min(start, t.wave) : start;
          const shown = Math.max(2, begin - G.warn);
          run.at(shown, () => e.hazards.sweep({
            tag: run.tag,
            warn: begin - shown,
            duration: end - begin,
            every: 1,
            draw: false,
            damage: G.damage,
            blockable: true,
            knock: 0.5,
            label: gi === 0 ? "aria_shards_a" : "aria_shards_b",
            shapeAt: (tt) => {
              const now = begin + tt;
              const parts = [];
              for (const v of volleys) {
                const f = now - v.at;
                if (f < 1 || f > flight) continue;
                for (const d of v.dirs) parts.push(new Circle(from.x + d.x * G.speed * f, from.z + d.z * G.speed * f, G.radius));
              }
              if (gi === 1 && waveAt && now >= t.wave && now <= waveEnd && (now - t.wave) % 2 === 0) parts.push(waveAt(now - t.wave));
              return new Union(parts);
            }
          }));
        });
        if (waveEnd) last = Math.max(last, waveEnd - flight);
        run.windows(t.first, last - t.first + flight, Math.max(8, t.end - last - flight));
      }
    };
  }
  // ------------------------------------------------------------------ 04 Held Note
  heldNote() {
    const self = this;
    return {
      id: "held_note",
      name: "Held Note",
      index: 4,
      cooldown: CANTOR.heldNote.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 3 && d <= 15 ? 2.4 : 0.6;
      },
      run(run) {
        const e = run.enc;
        self.begin(run);
        const t = beats("held_note", run.phase);
        const H = CANTOR.heldNote;
        if (run.target) e.loco.facePoint(run.target.location);
        const b = e.boss.location;
        const c = { x: b.x, z: b.z };
        const aim = yawToTheta(e.loco.yaw);
        e.hazards.strike({
          shape: sector(c.x, c.z, H.inner, H.range, aim, H.halfAngle),
          warn: t.blast,
          tag: run.tag,
          damage: H.damage,
          knock: 1.5,
          knockUp: 0.3,
          from: c,
          fx: 14,
          label: "held_note"
        });
        e.hazards.telegraph(new Circle(c.x, c.z, H.inner - 0.3), t.blast, true);
        const steps = Math.floor(t.blast / BEAT) - 1;
        for (let i = 1; i <= steps; i++) {
          run.at(i * BEAT, () => e.hazards.telegraph(sector(c.x, c.z, H.inner, H.range, aim, H.halfAngle * i / (steps + 1)), BEAT));
        }
        let last = t.blast;
        if (run.phase === 2) {
          run.at(t.blast, () => {
            const tg = e.targeting.primary(e.timeline.now) ?? run.target;
            const a2 = tg ? dirToTheta(tg.location.x - c.x, tg.location.z - c.z) : aim;
            e.hazards.strike({
              shape: sector(c.x, c.z, H.inner, H.range, a2, H.echoHalf),
              warn: t.echo - t.blast,
              tag: run.tag,
              damage: H.echoDamage,
              knock: 1.2,
              knockUp: 0.3,
              from: c,
              fx: 10,
              label: "held_echo"
            });
            e.hazards.telegraph(new Circle(c.x, c.z, H.inner - 0.3), t.echo - t.blast, true);
            run.at(t.blast + 4, () => e.loco.face(a2 - 90));
          });
          last = t.echo;
        }
        run.windows(t.blast, last - t.blast + 2, Math.max(10, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 05 The Silent Measure
  silentMeasure() {
    const self = this;
    return {
      id: "silent_measure",
      name: "The Silent Measure",
      index: 5,
      cooldown: CANTOR.silent.cooldown,
      // there has to be a rhythm before it can be withheld
      weight: () => self.sinceSilent >= CANTOR.silent.needsRhythm ? 2.2 : 0,
      run(run) {
        const e = run.enc;
        self.begin(run, false);
        self.sinceSilent = 0;
        const t = beats("silent_measure", run.phase);
        const Q = CANTOR.silent;
        const b = e.boss.location;
        const c = { x: b.x, z: b.z };
        const R = self.reach(c);
        const duration = Math.ceil((R - 1.5) / Q.speed);
        const base = e.rng.range(0, 360);
        const ringAt = (gaps) => (tt) => {
          const r = Math.max(1.5, R - tt * Q.speed);
          const r0 = Math.max(0.3, r - Q.thickness / 2);
          return new Ring(c.x, c.z, r0, r + Q.thickness / 2, 0, 360, widen(gaps, r0, Q.minDoor));
        };
        run.at(t.freeze, () => {
          self.silentUntil = e.timeline.now + (t.strike - t.freeze);
          e.setProp("abm:silent", 1);
          const m = new MolangVariableMap2();
          m.setFloat("variable.life", (t.strike - t.freeze) / 20);
          e.visuals.spawn(P("rest"), { x: b.x, y: b.y + 10.6, z: b.z }, m);
        });
        const g1 = doors(base, Q.gaps, Q.gapWidth);
        self.markDoors(c, g1, 2, R, t.strike + duration);
        run.at(t.strike, () => {
          self.endSilence();
          self.flash(c, R * 0.5);
        });
        let last = t.strike;
        self.wave(run, { shown: 0, start: t.strike, duration, shapeAt: ringAt(g1), damage: Q.damage, label: "silent_ring", from: c });
        if (run.phase === 2) {
          const g2 = doors(base + (e.rng.chance(0.5) ? 1 : -1) * Q.secondShift, Q.gaps, Q.secondWidth);
          self.markDoors(c, g2, 2, R, t.second + duration);
          self.wave(run, { shown: 0, start: t.second, duration, shapeAt: ringAt(g2), damage: Q.secondDamage, label: "silent_echo", from: c });
          last = t.second;
        }
        run.windows(t.strike, last - t.strike + duration, Math.max(10, t.end - last - duration));
      }
    };
  }
  // ------------------------------------------------------------------ 06 Twin Resonance
  twinResonance() {
    const self = this;
    return {
      id: "twin_resonance",
      name: "Twin Resonance",
      index: 6,
      cooldown: CANTOR.twin.cooldown,
      weight: (e) => e.helpers.count("bell") > 0 ? 0 : 2,
      run(run) {
        const e = run.enc;
        self.begin(run);
        const t = beats("twin_resonance", run.phase);
        const W = CANTOR.twin;
        const i = run.phase - 1;
        run.at(t.detach, () => {
          const a = e.arena;
          const b = e.boss.location;
          const tg = e.targeting.primary(e.timeline.now) ?? run.target;
          const near = tg ? a.clampInside(tg.location.x + (a.cx - tg.location.x) * 0.2, tg.location.z + (a.cz - tg.location.z) * 0.2, 2.5) : a.polar(e.rng.range(0, 360), 9, 2.5);
          const far = a.clampInside(2 * a.cx - near.x, 2 * a.cz - near.z, 2.5);
          const spots = [near, far].map((p) => {
            const d = Math.hypot(p.x - b.x, p.z - b.z);
            if (d >= 4) return p;
            const th = d > 0.1 ? dirToTheta(p.x - b.x, p.z - b.z) : e.rng.range(0, 360);
            const dir = thetaToDir(th);
            return a.clampInside(b.x + dir.x * 4.5, b.z + dir.z * 4.5, 2.5);
          });
          const now = e.timeline.now;
          spots.forEach((p, k) => {
            e.helpers.spawn("abm:cantor_bell", a.at(p, 0.05), "bell", {
              lifetime: W.lifetime[i],
              data: { interval: W.intervals[i][k], next: now + W.firstDelay + k * 20, hp: W.health, busyUntil: 0 }
            });
            e.visuals.decor(P("dust"), a.at(p, 0.4));
          });
          if (e.helpers.count("bell") > 0) e.setProp("abm:bells_out", 1);
        });
        run.windows(t.detach, 4, Math.max(8, t.end - t.detach - 4));
      }
    };
  }
  /** Each detached bell keeps its own interval. Striking a bell interrupts the pulse it is winding up. */
  tickBells(now) {
    const e = this.enc;
    const W = CANTOR.twin;
    for (const h of e.helpers.of("bell")) {
      const tag = `bell${h.id}`;
      let hp = h.data.hp;
      try {
        hp = h.entity.getComponent("minecraft:health")?.currentValue ?? hp;
      } catch {
        continue;
      }
      if (hp < h.data.hp - 0.01) {
        h.data.hp = hp;
        if (e.timeline.cancel(tag) > 0) {
          h.data.next = now + h.data.interval;
          h.data.busyUntil = 0;
          this.setBellAnim(h, 0);
          trace("bell_interrupted", { id: h.id });
        }
      }
      if (now < h.data.next || now < h.data.busyUntil) continue;
      const at = h.entity.location;
      h.data.next = now + h.data.interval;
      h.data.busyUntil = now + W.warn + 4;
      this.setBellAnim(h, 1);
      e.hazards.strike({
        shape: new Circle(at.x, at.z, W.radius),
        warn: W.warn,
        tag,
        damage: W.damage,
        label: "bell_pulse",
        knock: 0.7,
        from: at,
        sound: S("bell_pulse"),
        fx: 5,
        condition: () => h.entity.isValid,
        onStrike: () => this.flash(at, W.radius)
      });
      e.timeline.after(W.warn + 2, () => this.setBellAnim(h, 0), tag);
    }
  }
  setBellAnim(h, v) {
    try {
      if (h.entity.isValid) h.entity.setProperty("abm:anim", v);
    } catch {
    }
  }
  // ------------------------------------------------------------------ 07 The Final Requiem
  finalRequiem() {
    const self = this;
    return {
      id: "final_requiem",
      name: "The Final Requiem",
      index: 7,
      ultimate: true,
      interruptible: false,
      cooldown: CANTOR.requiem.cooldown,
      weight: (e) => e.healthFraction() < 0.9 ? 5 : 0,
      run(run) {
        const e = run.enc;
        self.begin(run);
        const strikes = cantor_timings_default.final_requiem[run.phase === 2 ? "p2" : "p1"];
        const Q = CANTOR.requiem;
        const a = e.arena;
        const R = a.radius;
        const k0 = e.rng.int(0, 5);
        const sixths = (odd, r0, r1) => [0, 2, 4].map((j) => new Ring(a.cx, a.cz, r0, r1, (k0 + odd + j) * 60, 60));
        const band = (r0, r1) => [new Ring(a.cx, a.cz, r0, r1)];
        const measures = run.phase === 1 ? [sixths(0, 2.5, R + 1), band(Q.inner, Q.middle), sixths(1, 2.5, Q.middle), [new Circle(a.cx, a.cz, Q.inner)]] : [band(Q.inner, Q.middle), sixths(0, 2.5, Q.middle), sixths(1, Q.far, R + 1), band(Q.outer, R + 1)];
        strikes.strikes.forEach((at, i) => {
          const shown = i === 0 ? 1 : strikes.strikes[i - 1];
          run.at(shown, () => {
            e.hazards.strike({
              shape: new Except(a.bounds(-1), measures[i]),
              warn: at - shown,
              tag: run.tag,
              safe: true,
              damage: Q.damage,
              fx: 16,
              knockUp: 0.3,
              label: `requiem_${i + 1}`
            });
            e.hazards.telegraph(new Ring(a.cx, a.cz, R - 0.4, R + 0.4), at - shown);
          });
        });
        const first = strikes.strikes[0];
        const last = strikes.strikes[strikes.strikes.length - 1];
        run.windows(first, last - first + 2, Math.max(10, strikes.end - last - 2));
      }
    };
  }
};
var MODULE = {
  create: (enc) => new CantorController(enc),
  arena: { structure: "abm:basilica_of_the_last_note", size: 51, height: 16, nameKey: "abm.arena.cantor" },
  helpers: ["abm:cantor_bell"]
};

// shared/nomos.timings.json
var nomos_timings_default = {
  _comment: "Beat timings for Nomos, in game ticks from the start of each action. Shared by the script (telegraphs, hit windows) and the animation generator (keyframes).",
  intro: { unfold: 40, align: 80, total: 120 },
  transition: { scatter: 30, rise: 70, unfold: 110, total: 150 },
  stagger: { total: 36 },
  death: { misalign: 40, fold: 90, collapse: 140, needle: 170, total: 190 },
  meridian_incision: {
    p1: { draw1: 4, hit1: 36, draw2: 40, hit2: 70, end: 96 },
    p2: { draw1: 4, hit1: 32, gap: 14, count: 3, end: 92 }
  },
  latitude_shear: {
    p1: { mark: 2, start: 36, duration: 60, end: 122 },
    p2: { mark: 2, start: 30, duration: 54, start2: 56, end: 134 }
  },
  ink_borders: {
    p1: { mark: 6, active: 40, life: 160, end: 70 },
    p2: { mark: 6, active: 36, life: 220, end: 66 }
  },
  unmapped_gate: {
    p1: { mark: 6, fold: 24, relocate: 38, strike: 44, end: 76 },
    p2: { mark: 6, fold: 20, relocate: 32, strike: 38, mark2: 42, fold2: 56, relocate2: 68, strike2: 74, end: 104 }
  },
  compass_darts: {
    p1: { appear: 4, lock: 30, interval: 9, warn: 15, end: 100 },
    p2: { appear: 4, lock: 26, interval: 7, warn: 14, lock2: 68, end: 122 }
  },
  folded_country: {
    p1: { mark: 4, hit: 34, interval: 18, count: 3, end: 96 },
    p2: { mark: 4, hit: 32, interval: 16, count: 4, end: 106 }
  },
  great_recalculation: {
    p1: { preview: 10, previewGap: 14, strike: 96, interval: 46, warn: 40, end: 214 },
    p2: { preview: 8, previewGap: 12, strike: 82, interval: 40, warn: 34, end: 186 }
  }
};

// src/bosses/nomos/grid.ts
var GRID_N = 8;
var QUADRANTS = [0, 1, 2, 3];
var QUADRANT_THETA = [180, 270, 90, 0];
var SurveyGrid = class {
  constructor(arena) {
    this.cx = arena.cx;
    this.cz = arena.cz;
    this.half = arena.radius;
    this.cell = this.half * 2 / GRID_N;
  }
  bounds() {
    return { x0: this.cx - this.half, z0: this.cz - this.half, x1: this.cx + this.half, z1: this.cz + this.half };
  }
  /** Column / row of a world position (clamped into the grid). */
  cellOf(x, z) {
    const c = Math.min(GRID_N - 1, Math.max(0, Math.floor((x - (this.cx - this.half)) / this.cell)));
    const r = Math.min(GRID_N - 1, Math.max(0, Math.floor((z - (this.cz - this.half)) / this.cell)));
    return { c, r };
  }
  cellCentre(c, r) {
    return { x: this.cx - this.half + (c + 0.5) * this.cell, z: this.cz - this.half + (r + 0.5) * this.cell };
  }
  cellRect(c, r) {
    const x0 = this.cx - this.half + c * this.cell;
    const z0 = this.cz - this.half + r * this.cell;
    return rect(x0, z0, x0 + this.cell, z0 + this.cell);
  }
  /** "C5"-style name of a cell, for messages and docs. */
  cellName(c, r) {
    return "ABCDEFGH"[c] + String(r + 1);
  }
  quadrantOf(x, z) {
    return (x >= this.cx ? 1 : 0) + (z >= this.cz ? 2 : 0);
  }
  quadrantBounds(q) {
    const east = (q & 1) === 1;
    const south = (q & 2) === 2;
    return {
      x0: east ? this.cx : this.cx - this.half,
      x1: east ? this.cx + this.half : this.cx,
      z0: south ? this.cz : this.cz - this.half,
      z1: south ? this.cz + this.half : this.cz
    };
  }
  quadrantCentre(q) {
    const b = this.quadrantBounds(q);
    return { x: (b.x0 + b.x1) / 2, z: (b.z0 + b.z1) / 2 };
  }
  /** Nearest ruled line (cell boundary) to a coordinate on one axis. */
  snapLine(v, axis) {
    const o = axis === "x" ? this.cx - this.half : this.cz - this.half;
    return o + Math.round((v - o) / this.cell) * this.cell;
  }
  inside(p, inset = 0) {
    return Math.abs(p.x - this.cx) <= this.half - inset && Math.abs(p.z - this.cz) <= this.half - inset;
  }
  /** Clip the infinite line through `p` along `theta` to a box; undefined when it misses. */
  clip(p, theta, b = this.bounds()) {
    const d = thetaToDir(theta);
    let t0 = -1e9;
    let t1 = 1e9;
    for (const [o, dd, lo, hi] of [[p.x, d.x, b.x0, b.x1], [p.z, d.z, b.z0, b.z1]]) {
      if (Math.abs(dd) < 1e-9) {
        if (o < lo || o > hi) return void 0;
        continue;
      }
      let a = (lo - o) / dd;
      let c = (hi - o) / dd;
      if (a > c) [a, c] = [c, a];
      t0 = Math.max(t0, a);
      t1 = Math.min(t1, c);
    }
    if (t0 >= t1) return void 0;
    return [{ x: p.x + d.x * t0, z: p.z + d.z * t0 }, { x: p.x + d.x * t1, z: p.z + d.z * t1 }];
  }
  /** A straight incision across the whole arena through `p` along `theta`. */
  chord(p, theta, halfWidth) {
    const q = { x: Math.min(this.cx + this.half - 0.1, Math.max(this.cx - this.half + 0.1, p.x)), z: Math.min(this.cz + this.half - 0.1, Math.max(this.cz - this.half + 0.1, p.z)) };
    const seg = this.clip(q, theta) ?? [q, q];
    return new Lane(seg[0].x, seg[0].z, seg[1].x, seg[1].z, halfWidth);
  }
  /**
   * How far (blocks) the worst-placed point of the arena is from the nearest
   * point that `danger` does not cover. A two-pass chamfer distance transform on
   * a one-block lattice: cheap enough to run before every arena-wide pattern.
   * Returns Infinity when the pattern leaves no safe point at all.
   */
  maxDistanceToSafety(danger, step = 1) {
    const n = Math.round(this.half * 2 / step);
    const d = new Float32Array(n * n);
    const BIG = 1e6;
    let anySafe = false;
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const x = this.cx - this.half + (i + 0.5) * step;
        const z = this.cz - this.half + (j + 0.5) * step;
        const safe = !danger.contains(x, z);
        d[j * n + i] = safe ? 0 : BIG;
        anySafe = anySafe || safe;
      }
    }
    if (!anySafe) return Infinity;
    const A = step;
    const B = step * Math.SQRT2;
    const at = (i, j) => i < 0 || j < 0 || i >= n || j >= n ? BIG : d[j * n + i];
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const k = j * n + i;
        d[k] = Math.min(d[k], at(i - 1, j) + A, at(i, j - 1) + A, at(i - 1, j - 1) + B, at(i + 1, j - 1) + B);
      }
    }
    let worst = 0;
    for (let j = n - 1; j >= 0; j--) {
      for (let i = n - 1; i >= 0; i--) {
        const k = j * n + i;
        d[k] = Math.min(d[k], at(i + 1, j) + A, at(i, j + 1) + A, at(i + 1, j + 1) + B, at(i - 1, j + 1) + B);
        if (d[k] > worst) worst = d[k];
      }
    }
    return worst;
  }
  /** Can a walking player always get clear of `danger` within `warnTicks`? */
  reachable(danger, warnTicks, walk, reaction) {
    return this.maxDistanceToSafety(danger) <= Math.max(0, warnTicks - reaction) * walk;
  }
};

// src/bosses/nomos/patterns.ts
function inBounds(b, x, z) {
  return x >= b.x0 && x <= b.x1 && z >= b.z0 && z <= b.z1;
}
function sampleBounds(shape, b, rng, n) {
  const out = [];
  let guard = n * 24;
  while (out.length < n && guard-- > 0) {
    const x = rng.range(b.x0, b.x1);
    const z = rng.range(b.z0, b.z1);
    if (shape.contains(x, z)) out.push({ x, z });
  }
  return out;
}
function clipLine(b, px, pz, dx, dz) {
  let t0 = -1e9;
  let t1 = 1e9;
  for (const [o, d, lo, hi] of [[px, dx, b.x0, b.x1], [pz, dz, b.z0, b.z1]]) {
    if (Math.abs(d) < 1e-9) {
      if (o < lo || o > hi) return void 0;
      continue;
    }
    let a = (lo - o) / d;
    let c = (hi - o) / d;
    if (a > c) [a, c] = [c, a];
    t0 = Math.max(t0, a);
    t1 = Math.min(t1, c);
  }
  if (t1 - t0 < 0.2) return void 0;
  return [px + dx * t0, pz + dz * t0, px + dx * t1, pz + dz * t1];
}
var Stripes = class _Stripes {
  constructor(b, theta, period, width, offset = 0, centreOnly = false) {
    this.b = b;
    this.theta = theta;
    this.period = period;
    this.width = width;
    this.offset = offset;
    this.centreOnly = centreOnly;
    this.cx = (b.x0 + b.x1) / 2;
    this.cz = (b.z0 + b.z1) / 2;
    this.reach = Math.hypot(b.x1 - b.x0, b.z1 - b.z0) / 2;
    const d = thetaToDir(theta);
    this.ux = d.x;
    this.uz = d.z;
    this.nx = -d.z;
    this.nz = d.x;
  }
  /** Signed distance across the corridors, from the box corner. */
  across(x, z) {
    return (x - this.b.x0) * this.nx + (z - this.b.z0) * this.nz;
  }
  /** Index of the period that a point falls in (used to pick the corridor a player stands in). */
  bandIndex(x, z) {
    return Math.floor((this.across(x, z) - this.offset) / this.period);
  }
  contains(x, z) {
    if (!inBounds(this.b, x, z)) return false;
    const s = this.across(x, z) - this.offset;
    const m = (s % this.period + this.period) % this.period;
    return m < this.width;
  }
  /** The complementary corridors (what is safe when this is dangerous). */
  complement(centreOnly = true) {
    return new _Stripes(this.b, this.theta, this.period, this.period - this.width, this.offset + this.width, centreOnly);
  }
  draw(pen) {
    const cs = [this.across(this.b.x0, this.b.z0), this.across(this.b.x1, this.b.z0), this.across(this.b.x0, this.b.z1), this.across(this.b.x1, this.b.z1)];
    const lo = Math.floor((Math.min(...cs) - this.offset) / this.period) - 1;
    const hi = Math.ceil((Math.max(...cs) - this.offset) / this.period) + 1;
    for (let k = lo; k <= hi; k++) {
      const s0 = this.offset + k * this.period;
      const lines = this.centreOnly ? [s0 + this.width / 2] : this.width >= 3.2 ? [s0, s0 + this.width / 2, s0 + this.width] : [s0, s0 + this.width];
      for (const s of lines) {
        const px = this.b.x0 + this.nx * s;
        const pz = this.b.z0 + this.nz * s;
        const seg = clipLine(this.b, px, pz, this.ux, this.uz);
        if (seg) pen.line(seg[0], seg[1], seg[2], seg[3]);
      }
    }
  }
  sample(rng, n) {
    return sampleBounds(this, this.b, rng, n);
  }
};
var Checker = class {
  constructor(b, cell, parity, ox = 0, oz = 0) {
    this.b = b;
    this.cell = cell;
    this.parity = parity;
    this.ox = ox;
    this.oz = oz;
    this.cx = (b.x0 + b.x1) / 2;
    this.cz = (b.z0 + b.z1) / 2;
    this.reach = Math.hypot(b.x1 - b.x0, b.z1 - b.z0) / 2;
  }
  squareOf(x, z) {
    return [Math.floor((x - this.b.x0 + this.ox) / this.cell), Math.floor((z - this.b.z0 + this.oz) / this.cell)];
  }
  contains(x, z) {
    if (!inBounds(this.b, x, z)) return false;
    const [i, j] = this.squareOf(Math.min(x, this.b.x1 - 1e-6), Math.min(z, this.b.z1 - 1e-6));
    return ((i + j) % 2 + 2) % 2 === this.parity;
  }
  /** The covered squares (parity) or the others (1 - parity), clipped to the box. */
  squares(parity = this.parity) {
    const out = [];
    const b = this.b;
    const [i1, j1] = this.squareOf(b.x1 - 1e-6, b.z1 - 1e-6);
    for (let i = 0; i <= i1; i++) {
      for (let j = 0; j <= j1; j++) {
        if ((i + j) % 2 !== parity) continue;
        const x0 = Math.max(b.x0, b.x0 - this.ox + i * this.cell);
        const x1 = Math.min(b.x1, b.x0 - this.ox + (i + 1) * this.cell);
        const z0 = Math.max(b.z0, b.z0 - this.oz + j * this.cell);
        const z1 = Math.min(b.z1, b.z0 - this.oz + (j + 1) * this.cell);
        if (x1 - x0 > 0.01 && z1 - z0 > 0.01) out.push({ x0, z0, x1, z1 });
      }
    }
    return out;
  }
  /** Centres of the covered squares (parity) or of the others (1 - parity). */
  centres(parity = this.parity) {
    return this.squares(parity).map((q) => ({ x: (q.x0 + q.x1) / 2, z: (q.z0 + q.z1) / 2 }));
  }
  draw(pen) {
    for (const q of this.squares()) {
      pen.line(q.x0, q.z0, q.x1, q.z0);
      pen.line(q.x1, q.z0, q.x1, q.z1);
      pen.line(q.x1, q.z1, q.x0, q.z1);
      pen.line(q.x0, q.z1, q.x0, q.z0);
      pen.line(q.x0, q.z0, q.x1, q.z1);
    }
  }
  sample(rng, n) {
    return sampleBounds(this, this.b, rng, n);
  }
};
var Marks = class {
  constructor(cx, cz, paint) {
    this.cx = cx;
    this.cz = cz;
    this.paint = paint;
    this.reach = 0;
  }
  contains() {
    return false;
  }
  draw(pen) {
    this.paint(pen);
  }
  sample() {
    return [];
  }
};

// src/bosses/nomos/tuning.ts
var NOMOS = {
  move: {
    p1: { speed: 0.07, turn: 3.2, near: 6.5, far: 12.5, station: 9 },
    p2: { speed: 0.1, turn: 4.6, near: 6, far: 13, station: 9 }
  },
  /** Walking speed (blocks/tick) and reaction time assumed by the safe-route validator. */
  fair: { walk: 4.317 / 20, reaction: 8 },
  meridian: { cooldown: [150, 120], damage: 14, halfWidth: 1.4, fan: 60 },
  shear: {
    cooldown: [230, 200],
    damage: 12,
    halfWidth: 1.2,
    /** Bands start this far from the arena centre and stop this far from it. */
    from: 15,
    to: 4.2,
    speed: 0.18,
    farCentre: 60,
    spread: 32
  },
  borders: {
    cooldown: [340, 300],
    damage: 10,
    halfWidth: 0.6,
    length: 24,
    slowTicks: 40,
    redrawEvery: 20
  },
  gate: {
    cooldown: [260, 210],
    damage: 15,
    radius: 5,
    offset: 3.5,
    minJump: 6,
    crossHalfWidth: 1.6,
    crossOffset: 4.5
  },
  darts: { cooldown: [200, 170], damage: 9, speed: 0.9, range: 34, radius: 0.7, height: 1.4, mount: 1.1, mountDamage: 5 },
  folded: { cooldown: [220, 190], damage: 13, width: 2.5 },
  recalc: { cooldown: [780, 720], damage: 18, cell: 10, stripe: 5, inner: 4, ring: [9, 14] },
  poise: { threshold: 110, window: 100, stagger: 36, lockout: 420 }
};

// src/bosses/nomos/index.ts
var S2 = (id) => `abm.nomos.${id}`;
var P2 = (id) => `abm:nomos_${id}`;
var beats2 = (name, phase) => nomos_timings_default[name][phase === 2 ? "p2" : "p1"];
var dir8 = (theta) => (Math.round(theta / 45) % 8 + 8) % 8;
var NomosController = class extends BossController {
  constructor(enc) {
    super(enc);
    this.key = "nomos";
    this.displayName = "Nomos";
    this.phase2Name = "There Is No North";
    this.trophyItem = "abm:sovereign_needle";
    this.style = {
      line: P2("tg_line"),
      arc: P2("tg_arc"),
      disc: P2("tg_disc"),
      safeLine: P2("safe_line"),
      safeArc: P2("safe_arc"),
      strike: P2("strike")
    };
    /** Encounter tick until which ink borders stand (0 = none). */
    this.bordersUntil = 0;
    /** Bumped whenever the standing borders are wiped; their scheduled work checks it. */
    this.borderEpoch = 0;
    this.inked = /* @__PURE__ */ new Map();
    /** Every dart direction ever locked, in order (read by tests: a locked dart never re-aims). */
    this.dartLocks = [];
    /** Where each Unmapped Gate tried to arrive, and whether it could (read by tests). */
    this.gateLog = [];
    this.stationAt = 0;
    this.foldedUntil = 0;
    this.poise = 0;
    this.poiseSince = 0;
    this.poiseLocked = 0;
    this.nextIdleSound = 140;
    this.grid = new SurveyGrid(enc.arena);
    this.attacks = [
      this.meridianIncision(),
      this.latitudeShear(),
      this.inkBorders(),
      this.unmappedGate(),
      this.compassDarts(),
      this.foldedCountry(),
      this.greatRecalculation()
    ];
  }
  // ------------------------------------------------------------------ framework hooks
  configure(phase) {
    const m = phase === 2 ? NOMOS.move.p2 : NOMOS.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }
  intro() {
    for (const q of QUADRANTS) this.indicate(q, 0);
    return nomos_timings_default.intro.total;
  }
  phaseTransition() {
    const e = this.enc;
    this.wipeBorders();
    const t = nomos_timings_default.transition;
    for (const q of QUADRANTS) {
      e.timeline.after(t.unfold + q * 6, () => {
        const c = this.grid.quadrantCentre(q);
        this.indicate(q, dir8(dirToTheta(c.x - this.grid.cx, c.z - this.grid.cz)));
        e.visuals.decor(P2("grid"), e.arena.at(c, 0.1));
        e.hazards.telegraph(new Marks(c.x, c.z, (pen) => pen.arc(c.x, c.z, 2.2, 0, 360)), 30, true);
      }, "phase");
    }
    return t.total;
  }
  death() {
    const e = this.enc;
    this.wipeBorders();
    e.timeline.after(nomos_timings_default.death.collapse + 16, () => {
      const b = e.boss.location;
      e.visuals.scatter(P2("dust"), new Circle(b.x, b.z, 3.5).sample(e.rng, 8), e.arena.floorY + 0.4);
    }, "death");
    return nomos_timings_default.death.total;
  }
  /**
   * Nomos keeps its distance and works from fixed stations - cell centres about nine
   * blocks from its target, on the arena-centre side - rather than closing in.
   */
  position(target) {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const m = e.phase === 2 ? NOMOS.move.p2 : NOMOS.move.p1;
    const now = e.timeline.now;
    const b = e.boss.location;
    const d = distXZ(b, target.location);
    if (!this.station && (d < m.near || d > m.far)) {
      const t = target.location;
      let dx = this.grid.cx - t.x;
      let dz = this.grid.cz - t.z;
      let l = Math.hypot(dx, dz);
      if (l < 2) {
        dx = b.x - t.x;
        dz = b.z - t.z;
        l = Math.hypot(dx, dz) || 1;
      }
      const want = e.arena.clampInside(t.x + dx / l * m.station, t.z + dz / l * m.station, e.stats.leashInset);
      const cell = this.grid.cellOf(want.x, want.z);
      this.station = this.grid.cellCentre(cell.c, cell.r);
      this.stationAt = now;
    }
    if (this.station) {
      const left = e.loco.goTo(this.station, 0.7);
      if (left <= 0.7 || now - this.stationAt > 160) this.station = void 0;
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }
  tick() {
    const e = this.enc;
    const now = e.timeline.now;
    if (!e.sm.inCombat) return;
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S2("idle"), e.boss.location, 0.5);
      this.nextIdleSound = now + 150 + e.rng.int(0, 100);
    }
    if (e.phase === 2 && !e.sm.busy && now % 20 === 0) {
      const t = e.targeting.primary(now);
      if (t) {
        for (const q of QUADRANTS) {
          const c = this.grid.quadrantCentre(q);
          if (distXZ(c, t.location) > 0.5) this.indicate(q, dir8(dirToTheta(t.location.x - c.x, t.location.z - c.z)));
        }
      }
    }
    if (now - this.poiseSince > NOMOS.poise.window) {
      this.poise = 0;
      this.poiseSince = now;
    }
  }
  incoming(damage, info) {
    const e = this.enc;
    const now = e.timeline.now;
    if (now < this.foldedUntil) return 0;
    this.poise += damage;
    const tip = this.poise >= NOMOS.poise.threshold && now >= this.poiseLocked;
    if (tip) {
      this.poise = 0;
      this.poiseLocked = now + NOMOS.poise.lockout;
    }
    const at = info.projectile && info.projectile.isValid ? info.projectile.location : localToWorld(e.boss.location, e.loco.yaw, 0, 4.2, 1.2);
    e.defer(() => {
      e.audio.play(S2("hit_metal"), at, 0.75);
      e.visuals.decor(P2("spark"), at);
      if (tip) e.stagger(NOMOS.poise.stagger);
    });
    return damage;
  }
  onAttackCancelled(def) {
    if (def.id === "ink_borders") this.wipeBorders();
    this.foldedUntil = 0;
  }
  cleanup() {
    this.wipeBorders();
    this.station = void 0;
  }
  // ------------------------------------------------------------------ shared helpers
  /** Standing ink borders dry up at once (phase change, death, reset, interrupted stamp). */
  wipeBorders() {
    this.borderEpoch++;
    this.bordersUntil = 0;
  }
  /** Point the indicator of quadrant q (0..3) along one of eight bearings. */
  indicate(q, step) {
    this.enc.setProp(`abm:q${q + 1}`, (step % 8 + 8) % 8);
  }
  front() {
    return yawToTheta(this.enc.loco.yaw);
  }
  dist(e) {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }
  /** Where the given (or primary) target stands now; a point ahead of Nomos when nobody is left. */
  aim(run, index = 0) {
    const e = this.enc;
    const ps = e.targeting.participants();
    const who = ps.length > 0 ? ps[index % ps.length] : void 0;
    const p = index === 0 ? e.targeting.primary(e.timeline.now) ?? who ?? run.target : who;
    if (p && p.isValid) return { x: p.location.x, z: p.location.z };
    const b = e.boss.location;
    const d = thetaToDir(this.front());
    return e.arena.clampInside(b.x + d.x * 8, b.z + d.z * 8, 1);
  }
  floorPen(line, ticks) {
    return this.enc.visuals.pen(line, P2("tg_arc"), void 0, this.enc.arena.floorY + 0.08, ticks / 20);
  }
  // ------------------------------------------------------------------ 01 Meridian Incision
  meridianIncision() {
    const self = this;
    return {
      id: "meridian_incision",
      name: "Meridian Incision",
      index: 1,
      cooldown: NOMOS.meridian.cooldown,
      weight: (e) => self.dist(e) >= 7 ? 3 : 1.7,
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const M = NOMOS.meridian;
        const cut = (p, theta, warn, label) => {
          e.hazards.strike({ shape: g.chord(p, theta, M.halfWidth), warn, tag: run.tag, damage: M.damage, knockUp: 0.3, fx: 10, label });
        };
        if (run.phase === 1) {
          const t2 = beats2("meridian_incision", 1);
          const p0 = self.aim(run);
          e.loco.facePoint(p0);
          let theta = self.front();
          run.at(t2.draw1, () => {
            const p = self.aim(run);
            const b = e.boss.location;
            if (distXZ(p, b) > 0.5) theta = dirToTheta(p.x - b.x, p.z - b.z);
            cut(p, theta, t2.hit1 - t2.draw1, "meridian_1");
          });
          run.at(t2.draw2, () => cut(self.aim(run), theta + 90, t2.hit2 - t2.draw2, "meridian_2"));
          run.windows(t2.hit1, t2.hit2 - t2.hit1 + 2, Math.max(8, t2.end - t2.hit2 - 2));
          return;
        }
        const t = beats2("meridian_incision", 2);
        const base = e.rng.int(0, 7) * 45;
        for (let i = 0; i < t.count; i++) {
          run.at(t.draw1 + i * t.gap, () => {
            const p = self.aim(run, i);
            const theta = base + i * M.fan;
            self.indicate(g.quadrantOf(p.x, p.z), dir8(theta));
            cut(p, theta, t.hit1 - t.draw1, `meridian_${i + 1}`);
          });
        }
        const last = t.hit1 + (t.count - 1) * t.gap;
        run.windows(t.hit1, last - t.hit1 + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 02 Latitude Shear
  /** Two curved bands, `o` blocks either side of the arena centre along bearing `phi`. */
  shearBands(phi, o) {
    const g = this.grid;
    const C = NOMOS.shear;
    const u = thetaToDir(phi);
    const band = (sign) => new Ring(
      g.cx + sign * u.x * C.farCentre,
      g.cz + sign * u.z * C.farCentre,
      C.farCentre - o - C.halfWidth,
      C.farCentre - o + C.halfWidth,
      wrapDeg(phi + (sign > 0 ? 180 : 0) - C.spread),
      C.spread * 2
    );
    return new Union([band(1), band(-1)]);
  }
  latitudeShear() {
    const self = this;
    return {
      id: "latitude_shear",
      name: "Latitude Shear",
      index: 2,
      cooldown: NOMOS.shear.cooldown,
      weight: (e) => 1.9 + Math.min(1.2, (e.targeting.count() - 1) * 0.6),
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const C = NOMOS.shear;
        const t = beats2("latitude_shear", run.phase);
        const p2 = run.phase === 2;
        const tg = self.aim(run);
        let phi = distXZ(tg, { x: g.cx, z: g.cz }) > 3 ? dirToTheta(tg.x - g.cx, tg.z - g.cz) : self.front();
        if (p2) phi = Math.round(phi / 45) * 45;
        const safeHalf = C.to - C.halfWidth - 0.2;
        const close = (axis, warn, label) => {
          e.hazards.sweep({
            tag: run.tag,
            warn,
            duration: t.duration,
            every: 2,
            shapeAt: (tt) => self.shearBands(axis, C.from - C.speed * tt),
            damage: C.damage,
            knockUp: 0.25,
            label,
            fx: 2,
            onHit: (p) => e.audio.play(S2("shear_hit"), p.location, 0.9)
          });
        };
        run.at(t.mark, () => {
          for (const q of QUADRANTS) self.indicate(q, dir8(phi + (q % 2 ? 180 : 0)));
          close(phi, t.start - t.mark, "shear_1");
          if (!p2) e.hazards.telegraph(g.chord({ x: g.cx, z: g.cz }, phi + 90, safeHalf), t.start - t.mark + t.duration, true);
        });
        let end = t.start + t.duration;
        if (p2) {
          run.at(t.start, () => {
            close(phi + 90, t.start2 - t.start, "shear_2");
            const u = thetaToDir(phi);
            const n = thetaToDir(phi + 90);
            const sq = [[1, 1], [1, -1], [-1, -1], [-1, 1]].map(([a, b]) => ({ x: g.cx + (u.x * a + n.x * b) * safeHalf, z: g.cz + (u.z * a + n.z * b) * safeHalf }));
            e.hazards.telegraph(new Polygon(sq), t.start2 - t.start + t.duration, true);
          });
          end = t.start2 + t.duration;
        }
        run.windows(t.start, end - t.start + 2, Math.max(8, t.end - end - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 03 Ink Borders
  inkBorders() {
    const self = this;
    return {
      id: "ink_borders",
      name: "Ink Borders",
      index: 3,
      cooldown: NOMOS.borders.cooldown,
      weight: (e) => e.timeline.now < self.bordersUntil ? 0 : 1.8,
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const B = NOMOS.borders;
        const t = beats2("ink_borders", run.phase);
        const p2 = run.phase === 2;
        run.at(t.mark, () => {
          const tg = self.aim(run);
          const b = e.boss.location;
          const bb = g.bounds();
          const half = B.length / 2;
          const alongZ = (x, zc) => new Lane(x, Math.max(bb.z0 + 0.5, zc - half), x, Math.min(bb.z1 - 0.5, zc + half), B.halfWidth);
          const alongX = (z, xc) => new Lane(Math.max(bb.x0 + 0.5, xc - half), z, Math.min(bb.x1 - 0.5, xc + half), z, B.halfWidth);
          const clampX = (x) => Math.min(bb.x1 - 1, Math.max(bb.x0 + 1, x));
          const clampZ = (z) => Math.min(bb.z1 - 1, Math.max(bb.z0 + 1, z));
          const ruled = (v, axis, away) => {
            let line = g.snapLine(v, axis);
            if (Math.abs(line - v) < 2) line += (away >= 0 ? 1 : -1) * g.cell;
            return axis === "x" ? clampX(line) : clampZ(line);
          };
          const lanes = [];
          const mostlyX = Math.abs(tg.x - b.x) >= Math.abs(tg.z - b.z);
          if (!p2) {
            if (mostlyX) {
              lanes.push(alongZ(clampX(tg.x), tg.z), alongX(ruled(tg.z, "z", tg.z - b.z), tg.x));
            } else {
              lanes.push(alongX(clampZ(tg.z), tg.x), alongZ(ruled(tg.x, "x", tg.x - b.x), tg.z));
            }
          } else {
            const sx = tg.x <= g.cx ? 1 : -1;
            const sz = tg.z <= g.cz ? 1 : -1;
            const xa = clampX(tg.x);
            const xb = clampX(tg.x + sx * 7.5);
            const za = clampZ(tg.z - sz * 3.75);
            const zb = clampZ(tg.z + sz * 3.75);
            const xm = (xa + xb) / 2;
            lanes.push(
              alongZ(xa, tg.z),
              alongZ(xb, tg.z),
              new Lane(xa, za, xm, za, B.halfWidth),
              new Lane(xm, zb, xb, zb, B.halfWidth)
            );
            for (const q of QUADRANTS) self.indicate(q, q % 2 ? 2 : 0);
          }
          const shape = new Union(lanes);
          const warn = t.active - t.mark;
          const epoch = ++self.borderEpoch;
          self.bordersUntil = e.timeline.now + warn + t.life;
          trace("ink_borders", { lanes: lanes.length, until: self.bordersUntil });
          e.hazards.strike({
            tag: run.tag,
            shape,
            warn,
            damage: B.damage,
            label: "ink_border",
            fx: 10,
            effects: [{ id: "slowness", ticks: B.slowTicks, amp: 0 }]
          });
          const amp = p2 ? 1 : 0;
          for (let tt = 2; tt <= t.life; tt += 2) {
            e.timeline.after(warn + tt, () => {
              if (epoch === self.borderEpoch) for (const p of e.hazards.inside(shape)) self.inkTouch(p, amp);
            }, run.tag);
          }
          for (let tt = 0; tt < t.life; tt += B.redrawEvery) {
            e.timeline.after(warn + tt, () => {
              if (epoch !== self.borderEpoch) return;
              const pen = self.floorPen(P2("border_line"), B.redrawEvery + 3);
              for (const l of lanes) pen.line(l.ax, l.az, l.bx, l.bz);
            }, run.tag);
          }
          e.timeline.after(warn + t.life + 1, () => {
            if (epoch === self.borderEpoch) self.bordersUntil = 0;
          }, run.tag);
        });
        run.windows(t.active, 8, Math.max(8, t.end - t.active - 8));
      }
    };
  }
  // ------------------------------------------------------------------ 04 Unmapped Gate
  /** A validated arrival point about `offset` blocks from the target; undefined when none is safe. */
  gateDestination(tg, from, offsets, dist) {
    const e = this.enc;
    const base = distXZ(tg, from) > 0.5 ? dirToTheta(tg.x - from.x, tg.z - from.z) : this.front();
    for (const off of offsets) {
      const d = thetaToDir(base + off);
      const p = { x: tg.x + d.x * dist, z: tg.z + d.z * dist };
      if (!e.arena.contains(p.x, p.z, e.stats.leashInset + 0.5)) continue;
      if (distXZ(p, from) < NOMOS.gate.minJump) continue;
      if (!e.loco.canStand(p)) continue;
      return p;
    }
    const lim = e.arena.radius - (e.stats.leashInset + 0.5);
    const c = {
      x: Math.min(e.arena.cx + lim, Math.max(e.arena.cx - lim, tg.x)),
      z: Math.min(e.arena.cz + lim, Math.max(e.arena.cz - lim, tg.z))
    };
    if (distXZ(c, from) >= NOMOS.gate.minJump && e.loco.canStand(c)) return c;
    return void 0;
  }
  unmappedGate() {
    const self = this;
    return {
      id: "unmapped_gate",
      name: "Unmapped Gate",
      index: 4,
      cooldown: NOMOS.gate.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        const b = e.boss.location;
        const cornered = !e.arena.contains(b.x, b.z, 9);
        return (d > 12 ? 2.8 : 1.2) + (cornered ? 1.2 : 0);
      },
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const G = NOMOS.gate;
        const t = beats2("unmapped_gate", run.phase);
        const y = e.arena.floorY;
        const jump = (mark, fold, relocate, strike, cross) => {
          run.at(mark, () => {
            const from = e.boss.location;
            const tg = self.aim(run);
            const dest = cross ? self.gateDestination(tg, from, [0, 90, -90, 180].map((a) => a - dirToTheta(tg.x - from.x, tg.z - from.z) % 90), G.crossOffset) : self.gateDestination(tg, from, [0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180], G.offset);
            const at = dest ?? { x: from.x, z: from.z };
            self.gateLog.push({ x: at.x, z: at.z, ok: !!dest });
            trace("gate", { ok: !!dest, x: at.x, z: at.z });
            e.hazards.telegraph(new Marks(from.x, from.z, (pen) => {
              pen.arc(from.x, from.z, 2.4, 0, 360);
              pen.line(from.x - 2.4, from.z, from.x + 2.4, from.z);
              pen.line(from.x, from.z - 2.4, from.x, from.z + 2.4);
            }), relocate - mark, true);
            e.visuals.decor(P2("grid"), { x: at.x, y: y + 0.1, z: at.z });
            self.indicate(g.quadrantOf(at.x, at.z), dir8(dirToTheta(at.x - from.x, at.z - from.z)));
            const shape = cross ? new Union([g.chord(at, 0, G.crossHalfWidth), g.chord(at, 90, G.crossHalfWidth)]) : new Circle(at.x, at.z, G.radius);
            e.hazards.strike({ shape, warn: strike - mark, tag: run.tag, damage: G.damage, knock: cross ? 0 : 1.2, knockUp: 0.3, from: at, fx: 12, label: cross ? "gate_cross" : "gate_arrival" });
            run.at(fold, () => {
              self.foldedUntil = e.timeline.now + (strike - fold);
            });
            run.at(relocate, () => {
              if (!dest) return;
              const now = self.aim(run);
              const ok2 = e.loco.relocate(dest, e.loco.yaw);
              if (ok2) e.loco.facePoint(now);
              else trace("gate_blocked", { x: dest.x, z: dest.z });
            });
            run.at(strike + 1, () => {
              self.foldedUntil = 0;
            });
          });
        };
        jump(t.mark, t.fold, t.relocate, t.strike, false);
        let last = t.strike;
        if (run.phase === 2) {
          jump(t.mark2, t.fold2, t.relocate2, t.strike2, true);
          last = t.strike2;
        }
        run.windows(t.fold, last - t.fold + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 05 Compass Darts
  compassDarts() {
    const self = this;
    return {
      id: "compass_darts",
      name: "Compass Darts",
      index: 5,
      cooldown: NOMOS.darts.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d >= 6 ? e.phase === 2 ? 2.9 : 2.5 : 1.2;
      },
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const D = NOMOS.darts;
        const t = beats2("compass_darts", run.phase);
        const p2 = run.phase === 2;
        const b = e.boss.location;
        const yaw = e.loco.yaw;
        if (run.target) e.loco.facePoint(run.target.location);
        const volleys = [];
        if (!p2) {
          volleys.push({ lock: t.lock, origins: [-2.7, -0.9, 0.9, 2.7].map((r) => localToWorld(b, e.loco.yaw, r, 0, 2.4)) });
        } else {
          volleys.push({ lock: t.lock, origins: QUADRANTS.map((q) => g.quadrantCentre(q)) });
          const r = g.half - 2;
          volleys.push({ lock: t.lock2, origins: [{ x: g.cx, z: g.cz - r }, { x: g.cx + r, z: g.cz }, { x: g.cx, z: g.cz + r }, { x: g.cx - r, z: g.cz }] });
        }
        let last = 0;
        let n = 0;
        for (const v of volleys) {
          v.origins.forEach((o, i) => {
            const index = n++;
            const lockAt = v.lock + i * t.interval;
            last = Math.max(last, lockAt + t.warn);
            const who = () => {
              const ps = e.targeting.participants();
              return ps.length > 0 ? ps[index % ps.length] : void 0;
            };
            const firstTrack = Math.max(t.appear, v.lock - 26);
            for (let tt = firstTrack; tt < lockAt; tt += 4) {
              run.at(tt, () => {
                const p = who();
                if (!p) return;
                if (tt === firstTrack) e.visuals.decor(P2("grid"), { x: o.x, y: e.arena.floorY + 0.1, z: o.z });
                self.floorPen(P2("aim_line"), 5).line(o.x, o.z, p.location.x, p.location.z);
              });
            }
            run.at(lockAt, () => {
              const p = who();
              const d = p && distXZ(p.location, o) > 0.3 ? normXZ(p.location.x - o.x, p.location.z - o.z) : thetaToDir(yawToTheta(yaw));
              self.dartLocks.push({ tick: e.timeline.now, ox: o.x, oz: o.z, dx: d.x, dz: d.z });
              trace("dart_lock", { index, dx: d.x, dz: d.z });
              if (p2) self.indicate(i % 4, dir8(dirToTheta(d.x, d.z)));
              const bb = g.bounds();
              const ex = d.x > 1e-6 ? (bb.x1 - o.x) / d.x : d.x < -1e-6 ? (bb.x0 - o.x) / d.x : Infinity;
              const ez = d.z > 1e-6 ? (bb.z1 - o.z) / d.z : d.z < -1e-6 ? (bb.z0 - o.z) / d.z : Infinity;
              const range = Math.max(3, Math.min(D.range, Math.min(ex, ez) - 0.4));
              e.hazards.strike({
                tag: run.tag,
                shape: new Circle(o.x, o.z, D.mount),
                warn: t.warn,
                damage: D.mountDamage,
                label: "dart_release"
              });
              e.hazards.projectile({
                tag: run.tag,
                delay: t.warn,
                from: { x: o.x, y: e.arena.floorY + D.height, z: o.z },
                dir: d,
                speed: D.speed,
                range,
                radius: D.radius,
                particle: P2("dart"),
                damage: D.damage,
                blockable: true,
                knock: 0.5,
                label: "compass_dart",
                sound: p2 ? S2("dart_fire") : void 0
              });
            });
          });
        }
        run.windows(t.lock, last - t.lock + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  /** Wet ink: slow whoever stands on a standing border (no damage). */
  inkTouch(p, amp) {
    const now = this.enc.timeline.now;
    try {
      p.addEffect("slowness", NOMOS.borders.slowTicks, { amplifier: amp, showParticles: false });
    } catch {
      return;
    }
    if (now - (this.inked.get(p.id) ?? -100) >= 20) {
      this.inked.set(p.id, now);
      this.enc.audio.play(S2("border_touch"), p.location, 0.8);
      trace("border_touch", { player: p.id });
    }
  }
  // ------------------------------------------------------------------ 06 Folded Country
  foldedCountry() {
    const self = this;
    return {
      id: "folded_country",
      name: "Folded Country",
      index: 6,
      cooldown: NOMOS.folded.cooldown,
      weight: (e) => self.dist(e) > 13 ? 3.1 : 2,
      run(run) {
        const e = run.enc;
        const g = self.grid;
        const F = NOMOS.folded;
        const t = beats2("folded_country", run.phase);
        const p2 = run.phase === 2;
        const tg = self.aim(run);
        const b = e.boss.location;
        e.loco.facePoint(tg);
        const along = Math.abs(tg.x - b.x) >= Math.abs(tg.z - b.z) ? 0 : 90;
        const period = F.width * 2;
        const bb = g.bounds();
        const startOffset = (theta) => {
          const probe = new Stripes(bb, theta, period, F.width, 0);
          const s = probe.across(tg.x, tg.z);
          return (s % period + period) % period < F.width ? 0 : F.width;
        };
        const offA = startOffset(along);
        const offB = startOffset(along + 90);
        let last = 0;
        for (let i = 0; i < t.count; i++) {
          const mark = t.mark + i * t.interval;
          const hit = t.hit + i * t.interval;
          last = hit;
          const theta = p2 && i % 2 === 1 ? along + 90 : along;
          const flip = p2 ? Math.floor(i / 2) % 2 : i % 2;
          const offset = (theta === along ? offA : offB) + flip * F.width;
          const shape = new Stripes(bb, theta, period, F.width, offset);
          run.at(mark, () => {
            if (p2) for (const q of QUADRANTS) self.indicate(q, dir8(theta));
            e.hazards.telegraph(shape.complement(true), hit - mark, true);
            e.hazards.strike({ shape, warn: hit - mark, tag: run.tag, damage: F.damage, knockUp: 0.3, fx: 14, label: `folded_${i + 1}` });
          });
        }
        run.windows(t.hit, last - t.hit + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 07 The Great Recalculation
  /**
   * One "projection" of the floor inside a box. Three systems exist:
   *   0 Cartesian  a chessboard of 10-block squares, alternate squares struck out;
   *   1 polar      a disc round the arena centre and a ring further out;
   *   2 oblique    diagonal corridors.
   * `sector` (start theta) restricts the polar system to one quadrant.
   */
  projection(system6, b, variant, sector2) {
    const g = this.grid;
    const R = NOMOS.recalc;
    if (system6 === 0) {
      const shift = [[1, 1], [1, 0], [0, 1]][(variant >> 1) % 3];
      const d2 = new Checker(b, R.cell, variant % 2, shift[0] * R.cell / 2, shift[1] * R.cell / 2);
      const safe = new Marks(d2.cx, d2.cz, (pen) => {
        for (const q of d2.squares(1 - d2.parity)) {
          pen.arc((q.x0 + q.x1) / 2, (q.z0 + q.z1) / 2, Math.min(1.6, (q.x1 - q.x0) / 2 - 0.6, (q.z1 - q.z0) / 2 - 0.6), 0, 360);
        }
      });
      return { danger: d2, safe, system: system6 };
    }
    if (system6 === 1) {
      const a0 = sector2 ?? 0;
      const sweep = sector2 === void 0 ? 360 : 90;
      const danger = new Union([new Ring(g.cx, g.cz, 0, R.inner, a0, sweep), new Ring(g.cx, g.cz, R.ring[0], R.ring[1], a0, sweep)]);
      const safe = new Marks(g.cx, g.cz, (pen) => {
        pen.arc(g.cx, g.cz, (R.inner + R.ring[0]) / 2, a0, sweep);
        pen.arc(g.cx, g.cz, R.ring[1] + 2.5, a0, sweep);
      });
      return { danger, safe, system: system6 };
    }
    const d = new Stripes(b, variant % 2 ? 45 : 135, R.stripe * 2, R.stripe, variant % 4 * (R.stripe / 2));
    return { danger: d, safe: d.complement(true), system: system6 };
  }
  /** The three configurations of one Great Recalculation, fixed before anything is shown. */
  buildConfigurations(phase, warn) {
    const e = this.enc;
    const g = this.grid;
    const order = e.rng.shuffle([0, 1, 2]);
    const out = [];
    for (let k = 0; k < 3; k++) {
      const variant = e.rng.int(0, 7);
      let cfg;
      if (phase === 1) {
        cfg = this.projection(order[k], g.bounds(), variant);
      } else {
        const parts = QUADRANTS.map((q) => this.projection((order[k] + q) % 3, g.quadrantBounds(q), variant + q, QUADRANT_THETA[q]));
        cfg = { danger: new Union(parts.map((p) => p.danger)), safe: new Union(parts.map((p) => p.safe)), system: order[k] };
      }
      if (!g.reachable(cfg.danger, warn, NOMOS.fair.walk, NOMOS.fair.reaction)) {
        trace("unsafe_pattern", { k, system: order[k], worst: g.maxDistanceToSafety(cfg.danger) });
        cfg = this.projection(1, g.bounds(), 0);
      }
      out.push(cfg);
    }
    return out;
  }
  greatRecalculation() {
    const self = this;
    return {
      id: "great_recalculation",
      name: "The Great Recalculation",
      index: 7,
      ultimate: true,
      interruptible: false,
      cooldown: NOMOS.recalc.cooldown,
      weight: (e) => e.healthFraction() < 0.9 ? 5 : 0,
      run(run) {
        const e = run.enc;
        const t = beats2("great_recalculation", run.phase);
        const configs = self.buildConfigurations(run.phase, t.warn);
        trace("recalculation", { systems: configs.map((c) => c.system) });
        configs.forEach((cfg, k) => {
          run.at(t.preview + k * t.previewGap, () => e.hazards.telegraph(cfg.danger, t.previewGap - 2));
          const at = t.strike + k * t.interval;
          run.at(at - t.warn, () => {
            if (run.phase === 2) for (const q of QUADRANTS) self.indicate(q, (cfg.system + q) % 3 * 2 + k);
            e.hazards.telegraph(cfg.safe, t.warn, true);
          });
          run.strike(at, { shape: cfg.danger, warn: t.warn, damage: NOMOS.recalc.damage, knockUp: 0.35, fx: 22, label: `recalculation_${k + 1}` });
        });
        const first = t.strike - t.warn;
        const last = t.strike + 2 * t.interval;
        run.windows(first, last - first + 2, Math.max(10, t.end - last - 2));
      }
    };
  }
};
var MODULE2 = {
  create: (enc) => new NomosController(enc),
  arena: { structure: "abm:observatory_of_unwritten_borders", size: 47, height: 15, nameKey: "abm.arena.nomos" },
  helpers: []
};

// src/bosses/orison/index.ts
import { world as world7 } from "@minecraft/server";

// shared/orison.timings.json
var orison_timings_default = {
  _comment: "Beat timings for Orison, in game ticks from the start of each action. Shared by the script (hit windows) and the animation generator (keyframes), so they cannot drift apart.",
  intro: { wake: 30, swing: 70, total: 116 },
  transition: { crack: 26, shatter: 60, emerge: 100, total: 136 },
  stagger: { total: 36 },
  death: { stop: 34, repeat: 74, ribbons: 112, empty: 142, total: 184 },
  footstep_echo: {
    p1: { mark: 14, first: 46, gap: 6, count: 5, end: 100 },
    p2: { mark: 12, first: 42, gap: 5, count: 8, end: 108 }
  },
  pendulum_verdict: {
    p1: { swing: 36, sweep: 14, end: 82 },
    p2: { swing: 30, sweep: 14, swing2: 66, end: 112 }
  },
  deferred_wound: {
    p1: { first: 12, gap: 8, count: 4, fuse: 40, end: 102 },
    p2: { first: 10, gap: 7, count: 6, fuse: 36, echo: 28, end: 134 }
  },
  hourglass_drain: {
    p1: { cast: 22, end: 52 },
    p2: { cast: 18, end: 46 }
  },
  tomorrows_witness: {
    p1: { lock: 14, strike: 44, end: 76 },
    p2: { lock: 12, strike: 40, end: 72 }
  },
  secondhand_exchange: {
    p1: { mark: 8, swap: 44, strike: 58, end: 92 },
    p2: { mark: 6, swap: 36, strike: 50, mark2: 54, swap2: 84, strike2: 98, end: 130 }
  },
  hour_never: {
    p1: { preview: 20, show: 26, step: 30, exec: 134, gap: 40, end: 250 },
    p2: { preview: 18, show: 20, step: 24, exec: 112, gap: 34, end: 216 }
  }
};

// src/bosses/orison/history.ts
var _PositionHistory = class _PositionHistory {
  constructor() {
    this.tracks = /* @__PURE__ */ new Map();
  }
  /** Call every tick with the current participants; samples on the interval. */
  record(players, now) {
    if (now % _PositionHistory.INTERVAL !== 0) return;
    for (const p of players) {
      if (!p.isValid) continue;
      let t = this.tracks.get(p.id);
      if (!t) {
        if (this.tracks.size >= _PositionHistory.MAX_PLAYERS) continue;
        t = { x: new Float32Array(_PositionHistory.CAPACITY), z: new Float32Array(_PositionHistory.CAPACITY), head: 0, size: 0, lastSeen: now };
        this.tracks.set(p.id, t);
      }
      const l = p.location;
      t.x[t.head] = l.x;
      t.z[t.head] = l.z;
      t.head = (t.head + 1) % _PositionHistory.CAPACITY;
      if (t.size < _PositionHistory.CAPACITY) t.size++;
      t.lastSeen = now;
    }
    for (const [id, t] of this.tracks) if (now - t.lastSeen > _PositionHistory.STALE) this.tracks.delete(id);
  }
  /** Up to `n` most recent samples, newest first. */
  recent(id, n) {
    const t = this.tracks.get(id);
    if (!t) return [];
    const out = [];
    const count = Math.min(n, t.size);
    for (let i = 1; i <= count; i++) {
      const k = (t.head - i + _PositionHistory.CAPACITY * 2) % _PositionHistory.CAPACITY;
      out.push({ x: t.x[k], z: t.z[k] });
    }
    return out;
  }
  /** Average velocity (blocks per tick) over the last `samplesBack` samples. */
  velocity(id, samplesBack) {
    const r = this.recent(id, samplesBack + 1);
    if (r.length < 2) return { x: 0, z: 0 };
    const a = r[0];
    const b = r[r.length - 1];
    const ticks = (r.length - 1) * _PositionHistory.INTERVAL;
    return { x: (a.x - b.x) / ticks, z: (a.z - b.z) / ticks };
  }
  /** Distance walked over the last `n` samples. */
  pathLength(id, n) {
    const r = this.recent(id, n);
    let d = 0;
    for (let i = 1; i < r.length; i++) d += Math.hypot(r[i].x - r[i - 1].x, r[i].z - r[i - 1].z);
    return d;
  }
  size(id) {
    return this.tracks.get(id)?.size ?? 0;
  }
  trackedPlayers() {
    return this.tracks.size;
  }
  totalSamples() {
    let n = 0;
    for (const t of this.tracks.values()) n += t.size;
    return n;
  }
  forget(id) {
    this.tracks.delete(id);
  }
  clear() {
    this.tracks.clear();
  }
};
_PositionHistory.INTERVAL = 4;
_PositionHistory.CAPACITY = 64;
_PositionHistory.MAX_PLAYERS = 8;
_PositionHistory.STALE = 60;
var PositionHistory = _PositionHistory;

// src/bosses/orison/patterns.ts
var patternLabel = (p) => `${p.kind}:${p.parity}`;
var PatternShape = class {
  constructor(pattern, arena, wedges, band) {
    this.pattern = pattern;
    this.wedges = wedges;
    this.band = band;
    this.cx = arena.cx;
    this.cz = arena.cz;
    this.reach = arena.radius + 1;
  }
  bandOf(r) {
    return Math.floor(r / this.band);
  }
  wedgeOf(theta) {
    const w = 360 / this.wedges;
    return Math.floor(((theta + w / 2) % 360 + 360) % 360 / w);
  }
  /** Is the cell (band i, wedge j) dangerous in this pattern? */
  danger(i, j) {
    const p = this.pattern;
    if (p.kind === "rings") return i % 2 === p.parity;
    if (p.kind === "wedges") return j % 2 === p.parity;
    return (i + j) % 2 === p.parity;
  }
  contains(x, z) {
    const dx = x - this.cx;
    const dz = z - this.cz;
    const r = Math.hypot(dx, dz);
    if (r > this.reach) return false;
    return this.danger(this.bandOf(r), this.wedgeOf(Math.atan2(dz, dx) * DEG));
  }
  draw(pen) {
    const bands = Math.ceil(this.reach / this.band);
    const w = 360 / this.wedges;
    const p = this.pattern;
    if (p.kind !== "wedges") {
      for (let i = 1; i <= bands; i++) pen.arc(this.cx, this.cz, Math.min(this.reach, i * this.band), 0, 360);
    }
    if (p.kind !== "rings") {
      for (let j = 0; j < this.wedges; j++) {
        const d = thetaToDir(j * w + w / 2);
        const r0 = p.kind === "checker" ? 0.5 : 0.5;
        pen.line(this.cx + d.x * r0, this.cz + d.z * r0, this.cx + d.x * this.reach, this.cz + d.z * this.reach);
      }
    }
    for (let i = 0; i < bands; i++) {
      const rm = Math.min(this.reach, (i + 0.5) * this.band);
      const step = p.kind === "rings" ? Math.max(1, Math.round(this.wedges / 4)) : 1;
      for (let j = 0; j < this.wedges; j += step) {
        if (!this.danger(i, j)) continue;
        if (p.kind === "wedges" && i % 2 === 1) continue;
        const d = thetaToDir(j * w);
        pen.disc(this.cx + d.x * rm, this.cz + d.z * rm, Math.min(1.5, this.band * 0.36));
      }
    }
  }
  sample(rng, n) {
    const out = [];
    let guard = n * 30;
    while (out.length < n && guard-- > 0) {
      const a = rng.range(0, Math.PI * 2);
      const d = Math.sqrt(rng.next()) * this.reach;
      const x = this.cx + Math.cos(a) * d;
      const z = this.cz + Math.sin(a) * d;
      if (this.contains(x, z)) out.push({ x, z });
    }
    return out;
  }
};
function choosePatterns(rng, phase) {
  const a = rng.chance(0.5) ? 0 : 1;
  const b = rng.chance(0.5) ? 0 : 1;
  if (phase === 1) {
    const first = rng.chance(0.5) ? "rings" : "wedges";
    const other = first === "rings" ? "wedges" : "rings";
    return [{ kind: first, parity: a }, { kind: other, parity: b }, { kind: first, parity: a === 0 ? 1 : 0 }];
  }
  const mid = rng.chance(0.5) ? "rings" : "wedges";
  return [{ kind: "checker", parity: a }, { kind: mid, parity: b }, { kind: "checker", parity: a === 0 ? 1 : 0 }];
}

// src/bosses/orison/tuning.ts
var ORISON = {
  move: {
    /** Phase I walks in a tick-tock: `stride` ticks moving, `rest` ticks held. */
    p1: { speed: 0.11, turn: 5, hold: 8, chase: 9.5, stride: 12, rest: 8 },
    /** Phase II: the shadow walks first and the body follows the same path `lead` ticks later. */
    p2: { speed: 0.15, turn: 7, hold: 6.5, chase: 7.5, lead: 10 }
  },
  history: {
    /** Samples used by the attacks, [phase I, phase II]: 5 s and 10 s of movement. */
    window: [25, 50]
  },
  echo: { cooldown: [170, 140], damage: 12, radius: [1.6, 1.8], minSpacing: 2 },
  verdict: {
    cooldown: [150, 120],
    damage: 16,
    inner: 2.2,
    outer: 11,
    arc: [140, 200],
    /** Angular half-width of the blade, degrees. */
    blade: 9,
    /** Phase II return swing covers this outer band instead. */
    returnBand: [5.5, 14]
  },
  wound: { cooldown: [200, 170], damage: 13, radius: 2.2 },
  drain: {
    cooldown: [420, 360],
    count: [2, 3],
    radius: 4,
    lifetime: [240, 300],
    /** Ticks after appearing before an hourglass starts to act. */
    arm: 30,
    pulseWarn: 40,
    pulseEvery: 70,
    damage: 8,
    /** Slowness is re-applied every `slowEvery` ticks for `slowTicks`, only to players inside the area. */
    slowTicks: 30,
    slowEvery: 10,
    slowAmp: 1,
    /** Destroying an hourglass jams Orison for this long. */
    breakStagger: 36
  },
  witness: { cooldown: [190, 150], damage: 15, radius: [3, 2.6], samplesBack: 5 },
  exchange: { cooldown: [260, 220], arrive: 15, depart: 8, arriveRadius: 4.5, departRadius: 3, offset: 3.5, minJump: 6 },
  hour: { cooldown: [780, 720], damage: 18, band: 4, wedges: [8, 12] }
};

// src/bosses/orison/index.ts
var S3 = (id) => `abm.orison.${id}`;
var P3 = (id) => `abm:orison_${id}`;
var NUMERAL = [P3("numeral_1"), P3("numeral_2"), P3("numeral_3")];
var beats3 = (name, phase) => orison_timings_default[name][phase === 2 ? "p2" : "p1"];
var live = (p) => isAlivePlayer(p) ? p : void 0;
var OrisonController = class extends BossController {
  constructor(enc) {
    super(enc);
    this.key = "orison";
    this.displayName = "Orison";
    this.phase2Name = "Tomorrow Has Already Happened";
    this.trophyItem = "abm:unlived_hourglass";
    this.style = {
      line: P3("tg_line"),
      arc: P3("tg_arc"),
      disc: P3("tg_disc"),
      safeLine: P3("safe_line"),
      safeArc: P3("safe_arc"),
      strike: P3("strike")
    };
    /** Recent positions of the participants. Bounded; see history.ts. */
    this.history = new PositionHistory();
    /** The three patterns of the most recent ultimate, and what was actually executed. */
    this.lastHour = { previewed: [], executed: [] };
    /** The spots locked by the most recent Tomorrow's Witness. */
    this.lastPrediction = [];
    /** 1 once the chest hourglass has shattered (Phase II). */
    this.glass = 0;
    /** Phase II: positions the shadow has walked through, oldest first (a delay line of `lead` ticks). */
    this.trail = [];
    /** While the encounter clock is below this the shadow is on an errand and does not lead. */
    this.shadowBusyUntil = 0;
    /** Encounter tick until which an hourglass pulse is announced but has not yet struck. */
    this.pulseUntil = 0;
    this.nextIdleSound = 100;
    this.attacks = [
      this.footstepEcho(),
      this.pendulumVerdict(),
      this.deferredWound(),
      this.hourglassDrain(),
      this.tomorrowsWitness(),
      this.secondhandExchange(),
      this.hourThatNeverOccurred()
    ];
    this.onLeave = (ev) => this.history.forget(ev.playerId);
    world7.afterEvents.playerLeave.subscribe(this.onLeave);
  }
  // ------------------------------------------------------------------ framework hooks
  configure(phase) {
    const m = phase === 2 ? ORISON.move.p2 : ORISON.move.p1;
    this.enc.loco.speed = m.speed;
    this.enc.loco.turnRate = m.turn;
  }
  intro() {
    return orison_timings_default.intro.total;
  }
  phaseTransition() {
    const e = this.enc;
    const t = orison_timings_default.transition;
    e.timeline.after(t.shatter, () => {
      this.glass = 1;
      e.setProp("abm:glass", 1);
      const chest = localToWorld(e.boss.location, e.loco.yaw, 0, 5.6, 0.5);
      e.visuals.spawn(P3("shard"), chest);
      e.visuals.spawn(P3("sand"), chest);
      const c = e.boss.location;
      for (const p of e.hazards.inside(new Circle(c.x, c.z, 5))) {
        const d = Math.hypot(p.location.x - c.x, p.location.z - c.z) || 1;
        try {
          p.applyKnockback({ x: (p.location.x - c.x) / d * 1.4, z: (p.location.z - c.z) / d * 1.4 }, 0.3);
        } catch {
        }
      }
    }, "phase");
    e.timeline.after(t.emerge, () => {
      this.ensureShadow();
    }, "phase");
    return t.total;
  }
  phase2Ready() {
    this.trail = [];
    this.shadowBusyUntil = 0;
    this.ensureShadow();
  }
  death() {
    const e = this.enc;
    const t = orison_timings_default.death;
    if (this.shadowAt) {
      const at = e.arena.at(this.shadowAt, 1.5);
      e.visuals.spawn(P3("wisp"), at);
      e.visuals.spawn(P3("wisp"), { x: at.x, y: at.y + 1.5, z: at.z });
    }
    this.shadowAt = void 0;
    e.timeline.after(t.repeat, () => {
      const f = localToWorld(e.boss.location, e.loco.yaw, 0, 0.2, 4);
      e.visuals.decor(P3("echo"), f);
    }, "death");
    e.timeline.after(t.empty, () => e.visuals.spawn(P3("sand"), localToWorld(e.boss.location, e.loco.yaw, 0, 5.2, 0.5)), "death");
    return t.total;
  }
  position(target) {
    const e = this.enc;
    if (!target) {
      e.loco.halt();
      return false;
    }
    const b = e.boss.location;
    const d = distXZ(b, target.location);
    if (e.phase === 2) return this.followShadow(target, d);
    const m = ORISON.move.p1;
    if (d > m.chase) {
      const beat = e.timeline.now % (m.stride + m.rest);
      if (beat < m.stride) {
        const k = (d - m.hold) / d;
        e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
        return true;
      }
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }
  tick() {
    const e = this.enc;
    const now = e.timeline.now;
    this.history.record(e.targeting.participants(), now);
    if (!e.sm.inCombat) return;
    this.tickDrains(now);
    if (e.phase === 2) this.tickShadow(now);
    if (now >= this.nextIdleSound && !e.sm.busy) {
      e.audio.play(S3("idle"), e.boss.location, 0.6);
      this.nextIdleSound = now + 150 + e.rng.int(0, 120);
    }
  }
  incoming(damage, _info) {
    const e = this.enc;
    e.defer(() => e.audio.play(S3("hurt"), e.boss.location, 0.7));
    return damage;
  }
  onHelperGone(h) {
    const e = this.enc;
    if (h.kind === "drain") {
      e.timeline.cancel(`hg${h.id}`);
      if (h.killed) {
        const at = e.arena.at({ x: h.data.x, z: h.data.z }, 1.2);
        e.visuals.spawn(P3("shard"), at);
        e.visuals.spawn(P3("sand"), at);
        e.audio.play(S3("hourglass_break"), at);
        e.stagger(ORISON.drain.breakStagger);
      }
    }
  }
  onAttackCancelled(_def) {
    this.enc.helpers.removeKind("mark");
    this.shadowBusyUntil = 0;
    this.trail = [];
    const sh = this.shadow();
    if (sh) this.shade(sh, 0 /* Idle */);
  }
  extra() {
    return { glass: this.glass };
  }
  restore(extra) {
    this.glass = extra.glass === 1 ? 1 : 0;
    this.enc.setProp("abm:glass", this.glass);
  }
  cleanup() {
    this.history.clear();
    this.trail = [];
    this.lastPrediction = [];
    this.pulseUntil = 0;
    try {
      world7.afterEvents.playerLeave.unsubscribe(this.onLeave);
    } catch {
    }
  }
  // ------------------------------------------------------------------ shared helpers
  dist(e) {
    const t = e.targeting.primary(e.timeline.now);
    return t ? distXZ(e.boss.location, t.location) : 99;
  }
  front() {
    return yawToTheta(this.enc.loco.yaw);
  }
  floor(lift = 0.07) {
    return this.enc.arena.floorY + lift;
  }
  /** Rising numeral over a mark: III, II, I. A countdown that does not depend on colour. */
  numeral(n, at) {
    if (n < 1 || n > 3) return;
    this.enc.visuals.spawn(NUMERAL[n - 1], { x: at.x, y: this.floor(1.1), z: at.z });
  }
  shade(h, state) {
    try {
      if (h.entity.isValid) h.entity.setProperty("abm:anim", state);
    } catch {
    }
  }
  // ------------------------------------------------------------------ the shadow (Phase II)
  /** The persistent shadow, if it currently exists. */
  shadow() {
    return this.enc.helpers.of("shadow")[0];
  }
  ensureShadow() {
    const e = this.enc;
    let sh = this.shadow();
    if (sh) return sh;
    const at = localToWorld(e.boss.location, e.loco.yaw, 2.5, 0, 0);
    const p = e.arena.clampInside(at.x, at.z, 1);
    sh = e.helpers.spawn("abm:orison_shadow", e.arena.at(p, 0.05), "shadow", { yaw: e.loco.yaw });
    if (sh) {
      this.shadowAt = p;
      this.trail = [];
      e.visuals.decor(P3("wisp"), e.arena.at(p, 1));
    }
    return sh;
  }
  /** Move a helper towards a point at `speed` blocks per tick (velocity steering, like the boss). */
  glide(h, goal, speed) {
    const l = h.entity.location;
    const dx = goal.x - l.x;
    const dz = goal.z - l.z;
    const d = Math.hypot(dx, dz);
    try {
      const v = h.entity.getVelocity();
      const step = Math.min(speed, d);
      const k = d > 0.05 ? step / d : 0;
      h.entity.applyImpulse({ x: dx * k - v.x, y: 0, z: dz * k - v.z });
      if (d > 0.05) h.entity.setRotation({ x: 0, y: dirToYaw(dx, dz) });
    } catch {
    }
    return d;
  }
  /** Phase II locomotion: the echo goes first, the body follows where the echo was `lead` ticks ago. */
  followShadow(target, d) {
    const e = this.enc;
    const m = ORISON.move.p2;
    const b = e.boss.location;
    const sh = this.shadow();
    const now = e.timeline.now;
    if (!sh || now < this.shadowBusyUntil) {
      if (d > m.chase) {
        const k = (d - m.hold) / d;
        e.loco.goTo({ x: b.x + (target.location.x - b.x) * k, z: b.z + (target.location.z - b.z) * k }, 0.4);
        return true;
      }
      e.loco.halt();
      e.loco.turnToward(e.loco.yawTo(target.location), 3);
      return false;
    }
    const sl = sh.entity.location;
    let goal = { x: sl.x, z: sl.z };
    const ds = distXZ(sl, target.location);
    if (ds > m.hold + 0.5) {
      const k = (ds - m.hold) / ds;
      goal = { x: sl.x + (target.location.x - sl.x) * k, z: sl.z + (target.location.z - sl.z) * k };
    }
    goal = e.arena.clampInside(goal.x, goal.z, e.stats.leashInset);
    this.glide(sh, goal, m.speed);
    this.shadowAt = { x: sl.x, z: sl.z };
    this.trail.push({ x: sl.x, z: sl.z });
    let follow;
    while (this.trail.length > m.lead) follow = this.trail.shift();
    if (follow && Math.hypot(follow.x - b.x, follow.z - b.z) > 0.7) {
      e.loco.goTo(follow, 0.4);
      return true;
    }
    e.loco.halt();
    e.loco.turnToward(e.loco.yawTo(target.location), 3);
    return false;
  }
  /** Keep the shadow alive and, while the body is busy, parked at its side. */
  tickShadow(now) {
    const e = this.enc;
    const sh = this.ensureShadow();
    if (!sh) return;
    const l = sh.entity.location;
    this.shadowAt = { x: l.x, z: l.z };
    if (now < this.shadowBusyUntil) {
      this.glide(sh, { x: l.x, z: l.z }, 0);
      return;
    }
    if (e.sm.busy || e.sm.sub === "STAGGER" || e.sm.sub === "RESET") {
      const side = localToWorld(e.boss.location, e.loco.yaw, 2.6, 0, 0.5);
      this.glide(sh, e.arena.clampInside(side.x, side.z, 1), ORISON.move.p2.speed);
    }
  }
  /**
   * Put a shadow at `spot` for `ticks`. Phase I conjures a temporary one; Phase II sends the
   * real shadow, which is why its errands interrupt its leading.
   */
  sendShadow(spot, ticks, state) {
    const e = this.enc;
    const now = e.timeline.now;
    const at = e.arena.at(spot, 0.05);
    if (e.phase === 2) {
      const sh = this.ensureShadow();
      if (!sh) return void 0;
      try {
        sh.entity.teleport(at, { keepVelocity: false });
      } catch {
        return void 0;
      }
      this.shadowBusyUntil = Math.max(this.shadowBusyUntil, now + ticks);
      this.shadowAt = { x: spot.x, z: spot.z };
      this.trail = [];
      this.shade(sh, state);
      e.visuals.decor(P3("wisp"), { x: at.x, y: at.y + 1, z: at.z });
      return sh;
    }
    const h = e.helpers.spawn("abm:orison_shadow", at, "mark", { lifetime: ticks, yaw: e.loco.yaw });
    if (h) {
      this.shade(h, state);
      e.visuals.decor(P3("wisp"), { x: at.x, y: at.y + 1, z: at.z });
    }
    return h;
  }
  /** In Phase II the shadow makes each attack's gesture before the body does. */
  shadowLeads(run) {
    if (run.phase !== 2) return;
    const sh = this.shadow();
    if (!sh || this.enc.timeline.now < this.shadowBusyUntil) return;
    this.shade(sh, 1 /* Strike */);
    run.at(12, () => {
      if (this.enc.timeline.now >= this.shadowBusyUntil) this.shade(sh, 0 /* Idle */);
    });
  }
  // ------------------------------------------------------------------ hourglasses (Drain)
  /** Slowness for players standing in an armed hourglass's area - re-applied in short doses, never stored. */
  tickDrains(now) {
    const e = this.enc;
    if (now % ORISON.drain.slowEvery !== 0) return;
    const drains = e.helpers.of("drain");
    if (drains.length === 0) return;
    for (const h of drains) {
      if (now < h.data.armed) continue;
      const area = new Circle(h.data.x, h.data.z, ORISON.drain.radius);
      for (const p of e.hazards.inside(area)) {
        try {
          p.addEffect("slowness", ORISON.drain.slowTicks, { amplifier: ORISON.drain.slowAmp, showParticles: true });
          trace("orison_slow", { player: p.name, tick: now });
        } catch {
        }
      }
      if (now % 40 === 0) {
        e.visuals.pen(this.style.line, this.style.arc, void 0, this.floor(), 2).arc(h.data.x, h.data.z, ORISON.drain.radius, 0, 360);
      }
    }
  }
  /** True while Orison is performing one of its two arena-wide attacks. */
  wideAttack() {
    const id = this.enc.currentAttack?.id;
    return id === "pendulum_verdict" || id === "hour_never";
  }
  /**
   * An hourglass pulses on its own clock, with one rule of fairness: a pulse is never announced
   * while an arena-wide attack is in progress, and (see the weights of those attacks) an arena-wide
   * attack never begins while a pulse is announced. The two are always a full warning apart.
   */
  armDrain(h, lifetime) {
    const e = this.enc;
    const D = ORISON.drain;
    const tag = `hg${h.id}`;
    const area = new Circle(h.data.x, h.data.z, D.radius);
    const dies = e.timeline.now + lifetime;
    e.visuals.pen(this.style.line, this.style.arc, void 0, this.floor(), D.arm / 20).arc(h.data.x, h.data.z, D.radius, 0, 360);
    const pulse = () => {
      if (!h.entity.isValid) return;
      const now = e.timeline.now;
      if (now + D.pulseWarn + 2 >= dies) return;
      if (this.wideAttack()) {
        e.timeline.after(10, pulse, tag);
        return;
      }
      try {
        h.entity.setProperty("abm:anim", 1);
      } catch {
        return;
      }
      this.pulseUntil = Math.max(this.pulseUntil, now + D.pulseWarn);
      e.hazards.strike({
        shape: area,
        warn: D.pulseWarn,
        tag,
        damage: D.damage,
        fx: 4,
        sound: S3("drain_pulse"),
        label: "hourglass_drain",
        condition: () => h.entity.isValid,
        onStrike: () => {
          e.visuals.decor(P3("pulse"), { x: h.data.x, y: this.floor(), z: h.data.z });
          try {
            if (h.entity.isValid) h.entity.setProperty("abm:anim", 0);
          } catch {
          }
        }
      });
      e.timeline.after(D.pulseEvery, pulse, tag);
    };
    e.timeline.after(D.arm, pulse, tag);
  }
  // ------------------------------------------------------------------ 01 Footstep Echo
  footstepEcho() {
    const self = this;
    return {
      id: "footstep_echo",
      name: "Footstep Echo",
      index: 1,
      cooldown: ORISON.echo.cooldown,
      weight: (e) => {
        const t = e.targeting.primary(e.timeline.now);
        if (!t) return 0;
        return self.history.pathLength(t.id, ORISON.history.window[e.phase - 1]) > 6 ? 3 : 1.3;
      },
      run(run) {
        const e = run.enc;
        const t = beats3("footstep_echo", run.phase);
        const i = run.phase - 1;
        if (live(run.target)) e.loco.facePoint(run.target.location);
        self.shadowLeads(run);
        const last = t.first + t.gap * (t.count - 1);
        run.at(t.mark, () => {
          const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
          const trailPts = tgt ? [{ x: tgt.location.x, z: tgt.location.z }, ...self.history.recent(tgt.id, ORISON.history.window[i])] : [];
          const picked = [];
          for (const p of trailPts) {
            if (picked.length >= t.count) break;
            if (picked.every((q) => Math.hypot(q.x - p.x, q.z - p.z) >= ORISON.echo.minSpacing)) picked.push(p);
          }
          if (picked.length === 0) picked.push(e.arena.randomPoint(e.rng, 3));
          trace("orison_echo", { points: picked.map((p) => ({ x: p.x, z: p.z })), player: tgt?.name ?? "" });
          const ordered = picked.slice().reverse();
          ordered.forEach((p, k) => {
            const at = t.first + (t.count - ordered.length + k) * t.gap;
            e.visuals.spawn(P3("footprint"), { x: p.x, y: self.floor(), z: p.z });
            e.hazards.strike({
              shape: new Circle(p.x, p.z, ORISON.echo.radius[i]),
              warn: at - t.mark,
              tag: run.tag,
              damage: ORISON.echo.damage,
              fx: 4,
              sound: S3("echo_burst"),
              knockUp: 0.2,
              label: "footstep_echo",
              onStrike: () => e.visuals.decor(P3("echo"), { x: p.x, y: self.floor(0.9), z: p.z })
            });
          });
        });
        run.windows(t.mark, last - t.mark + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 02 Pendulum Verdict
  pendulumVerdict() {
    const self = this;
    return {
      id: "pendulum_verdict",
      name: "Pendulum Verdict",
      index: 2,
      cooldown: ORISON.verdict.cooldown,
      weight: (e) => {
        if (e.timeline.now <= self.pulseUntil) return 0;
        const d = self.dist(e);
        return d <= ORISON.verdict.outer + 1 ? 3 : 0.6;
      },
      run(run) {
        const e = run.enc;
        const t = beats3("pendulum_verdict", run.phase);
        const V = ORISON.verdict;
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint(run.target.location);
        self.shadowLeads(run);
        const b = e.boss.location;
        const front = self.front();
        const dir = e.rng.chance(0.5) ? 1 : -1;
        run.variant(dir === 1 ? 0 : 1);
        const arc = V.arc[run.phase - 1];
        const a0 = front - dir * arc / 2;
        const a1 = front + dir * arc / 2;
        const swing = (startTick, from, to, r0, r1, label) => {
          const lo = Math.min(from, to);
          const begin = Math.max(1, startTick - Math.min(startTick - 1, 34));
          run.at(begin, () => {
            const warn = startTick - begin;
            e.hazards.telegraph(new Ring(b.x, b.z, r0, r1, lo, arc), warn);
            e.hazards.sweep({
              tag: run.tag,
              warn,
              duration: t.sweep,
              every: 1,
              shapeAt: (tt) => sector(b.x, b.z, r0, r1, from + (to - from) * tt / t.sweep, V.blade),
              damage: V.damage,
              blockable: true,
              knock: 1.3,
              knockUp: 0.3,
              label,
              fx: 2
            });
          });
        };
        swing(t.swing, a0, a1, V.inner, V.outer, "pendulum_verdict");
        let last = t.swing + t.sweep;
        if (p2) {
          swing(t.swing2, a1, a0, V.returnBand[0], V.returnBand[1], "pendulum_return");
          last = t.swing2 + t.sweep;
        }
        run.windows(t.swing, last - t.swing + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 03 Deferred Wound
  deferredWound() {
    const self = this;
    return {
      id: "deferred_wound",
      name: "Deferred Wound",
      index: 3,
      cooldown: ORISON.wound.cooldown,
      weight: (e) => 2 + Math.min(1.5, (e.targeting.count() - 1) * 0.6),
      run(run) {
        const e = run.enc;
        const t = beats3("deferred_wound", run.phase);
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint(run.target.location);
        self.shadowLeads(run);
        let last = 0;
        const countdown = (at, from, fuse) => {
          for (let n = 3; n >= 1; n--) {
            const when = from + Math.round(fuse * (3 - n) / 3);
            run.at(when, () => self.numeral(n, at));
          }
        };
        for (let k = 0; k < t.count; k++) {
          const mark = t.first + k * t.gap;
          const boom = mark + t.fuse;
          last = Math.max(last, boom + (p2 ? t.echo : 0));
          run.at(mark, () => {
            const ps = e.targeting.participants();
            const who = ps.length > 0 ? ps[k % ps.length] : void 0;
            let c;
            if (!who) c = e.arena.randomPoint(e.rng, 3);
            else if (p2 && k % 2 === 1) {
              const old = self.history.recent(who.id, 10);
              c = old.length > 0 ? old[old.length - 1] : { x: who.location.x, z: who.location.z };
            } else c = { x: who.location.x, z: who.location.z };
            const shape = new Circle(c.x, c.z, ORISON.wound.radius);
            countdown(c, mark, t.fuse);
            e.hazards.strike({ shape, warn: t.fuse, tag: run.tag, damage: ORISON.wound.damage, fx: 5, sound: S3("wound_burst"), knockUp: 0.3, label: "deferred_wound" });
            if (p2) {
              run.at(boom, () => {
                e.hazards.strike({ shape, warn: t.echo, tag: run.tag, damage: ORISON.wound.damage, fx: 5, sound: S3("wound_burst"), knockUp: 0.3, label: "deferred_wound_again" });
              });
              countdown(c, boom, t.echo);
            }
          });
        }
        run.windows(t.first, last - t.first + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 04 Hourglass Drain
  hourglassDrain() {
    const self = this;
    return {
      id: "hourglass_drain",
      name: "Hourglass Drain",
      index: 4,
      cooldown: ORISON.drain.cooldown,
      weight: (e) => {
        if (e.helpers.count("drain") > 0) return 0;
        return self.dist(e) > 9 ? 2.4 : 1.7;
      },
      run(run) {
        const e = run.enc;
        const t = beats3("hourglass_drain", run.phase);
        const i = run.phase - 1;
        self.shadowLeads(run);
        run.at(t.cast, () => {
          const ps = e.targeting.participants();
          const b = e.boss.location;
          const placed = [];
          for (let k = 0; k < ORISON.drain.count[i]; k++) {
            const who = ps.length > 0 ? ps[k % ps.length] : void 0;
            const base = who ? who.location : { x: e.arena.cx, z: e.arena.cz };
            let pos;
            for (let attempt = 0; attempt < 8 && !pos; attempt++) {
              const d = thetaToDir(e.rng.range(0, 360));
              const r = 2.2 + e.rng.range(0, 0.8) + (k >= ps.length ? 3 : 0);
              const c = e.arena.clampInside(base.x + d.x * r, base.z + d.z * r, 2);
              const clear = Math.hypot(c.x - b.x, c.z - b.z) >= 2.5 && placed.every((q) => Math.hypot(q.x - c.x, q.z - c.z) >= 3);
              if (clear) pos = c;
            }
            if (!pos) continue;
            placed.push(pos);
            const life = ORISON.drain.lifetime[i];
            const h = e.helpers.spawn("abm:orison_hourglass", e.arena.at(pos, 0.05), "drain", {
              lifetime: life,
              data: { x: pos.x, z: pos.z, armed: e.timeline.now + ORISON.drain.arm }
            });
            if (h) {
              self.armDrain(h, life);
              e.visuals.decor(P3("sand"), e.arena.at(pos, 1.6));
            }
          }
          trace("orison_drain", { count: placed.length });
        });
        run.windows(t.cast, 4, Math.max(8, t.end - t.cast - 4));
      }
    };
  }
  // ------------------------------------------------------------------ 05 Tomorrow's Witness
  tomorrowsWitness() {
    const self = this;
    return {
      id: "tomorrows_witness",
      name: "Tomorrow's Witness",
      index: 5,
      cooldown: ORISON.witness.cooldown,
      weight: (e) => {
        const t = e.targeting.primary(e.timeline.now);
        if (!t) return 0;
        const v = self.history.velocity(t.id, ORISON.witness.samplesBack);
        return Math.hypot(v.x, v.z) > 0.08 ? 3 : 1.4;
      },
      run(run) {
        const e = run.enc;
        const t = beats3("tomorrows_witness", run.phase);
        const i = run.phase - 1;
        const p2 = run.phase === 2;
        if (live(run.target)) e.loco.facePoint(run.target.location);
        const lead = t.strike - t.lock;
        run.at(t.lock, () => {
          const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
          const here = tgt ? { x: tgt.location.x, z: tgt.location.z } : e.arena.randomPoint(e.rng, 3);
          const vel = tgt ? self.history.velocity(tgt.id, ORISON.witness.samplesBack) : { x: 0, z: 0 };
          const speed = Math.hypot(vel.x, vel.z);
          const spots = [e.arena.clampInside(here.x + vel.x * lead, here.z + vel.z * lead, 1)];
          if (p2) {
            let back;
            if (speed > 0.03) back = { x: here.x - vel.x * lead * 0.6, z: here.z - vel.z * lead * 0.6 };
            else {
              const toC = Math.hypot(e.arena.cx - here.x, e.arena.cz - here.z);
              const d = toC > 1 ? { x: (e.arena.cx - here.x) / toC, z: (e.arena.cz - here.z) / toC } : thetaToDir(e.rng.range(0, 360));
              back = { x: here.x + d.x * 3.4, z: here.z + d.z * 3.4 };
            }
            spots.push(e.arena.clampInside(back.x, back.z, 1));
          }
          self.lastPrediction = spots.map((s) => ({ x: s.x, z: s.z }));
          trace("orison_predict", { spots: self.lastPrediction, from: here, vx: vel.x, vz: vel.z, strikeIn: lead });
          const mark = self.sendShadow(spots[0], lead + 16, 2 /* Point */);
          const b = e.boss.location;
          const pen = e.visuals.pen(self.style.line, self.style.arc, void 0, self.floor(), lead / 20);
          pen.line(b.x, b.z, spots[0].x, spots[0].z);
          for (const s of spots) {
            e.hazards.strike({
              shape: new Circle(s.x, s.z, ORISON.witness.radius[i]),
              warn: lead,
              tag: run.tag,
              damage: ORISON.witness.damage,
              fx: 6,
              sound: S3("shadow_strike"),
              knock: 0.8,
              knockUp: 0.3,
              label: "tomorrows_witness"
            });
          }
          run.at(t.strike - 6, () => {
            if (mark) self.shade(mark, 1 /* Strike */);
          });
          run.at(t.strike + 12, () => {
            const sh = self.shadow();
            if (p2 && sh) self.shade(sh, 0 /* Idle */);
          });
        });
        run.windows(t.lock, lead + 2, Math.max(8, t.end - t.strike - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 06 Secondhand Exchange
  /** A validated place to arrive: near the target, a real distance from where Orison stands now. */
  pickDestination(tgt, from) {
    const e = this.enc;
    const X = ORISON.exchange;
    const cands = [];
    if (tgt) {
      const away = dirToTheta(tgt.location.x - from.x, tgt.location.z - from.z);
      for (const off of [0, 50, -50, 100, -100, 150, -150, 180]) {
        const d = thetaToDir(away + off);
        cands.push({ x: tgt.location.x + d.x * X.offset, z: tgt.location.z + d.z * X.offset });
      }
    }
    for (let k = 0; k < 6; k++) cands.push(e.arena.randomPoint(e.rng, e.stats.leashInset + 1));
    for (const c of cands) {
      const p = e.arena.clampInside(c.x, c.z, e.stats.leashInset + 0.5);
      if (Math.hypot(p.x - from.x, p.z - from.z) < X.minJump) continue;
      if (!e.loco.canStand(p)) continue;
      return p;
    }
    return void 0;
  }
  secondhandExchange() {
    const self = this;
    return {
      id: "secondhand_exchange",
      name: "Secondhand Exchange",
      index: 6,
      cooldown: ORISON.exchange.cooldown,
      weight: (e) => {
        const d = self.dist(e);
        return d > 10 ? 3.2 : d > 6 ? 1.6 : 0.9;
      },
      run(run) {
        const e = run.enc;
        const t = beats3("secondhand_exchange", run.phase);
        const X = ORISON.exchange;
        const steps = [[t.mark, t.swap, t.strike]];
        if (run.phase === 2) steps.push([t.mark2, t.swap2, t.strike2]);
        let last = 0;
        for (const [mk, sw, st] of steps) {
          last = st;
          run.at(mk, () => {
            const tgt = live(run.target) ?? e.targeting.primary(e.timeline.now);
            const bl = e.boss.location;
            const from = { x: bl.x, z: bl.z };
            const dest = self.pickDestination(tgt, from);
            const arrive = dest ?? from;
            trace("orison_exchange", { from, to: arrive, valid: dest !== void 0 });
            const mark = self.sendShadow(arrive, st - mk + 14, 2 /* Point */);
            const warn = st - mk;
            e.hazards.strike({
              shape: new Circle(arrive.x, arrive.z, X.arriveRadius),
              warn,
              tag: run.tag,
              damage: X.arrive,
              knock: 1.2,
              knockUp: 0.35,
              fx: 8,
              label: "exchange_arrive"
            });
            if (dest) {
              e.hazards.strike({
                shape: new Circle(from.x, from.z, X.departRadius),
                warn,
                tag: run.tag,
                damage: X.depart,
                fx: 4,
                sound: S3("shadow_strike"),
                label: "exchange_depart"
              });
              e.visuals.pen(self.style.safeLine, self.style.safeArc, void 0, self.floor(), warn / 20).line(from.x, from.z, arrive.x, arrive.z);
            }
            run.at(sw, () => {
              if (!dest) return;
              const face = tgt && tgt.isValid ? dirToYaw(tgt.location.x - dest.x, tgt.location.z - dest.z) : e.loco.yaw;
              const ok2 = e.loco.relocate(dest, face);
              trace("orison_swap", { ok: ok2 });
              const y = self.floor(1.5);
              e.visuals.spawn(P3("wisp"), { x: from.x, y, z: from.z });
              e.visuals.spawn(P3("wisp"), { x: dest.x, y, z: dest.z });
              if (ok2 && mark && mark.entity.isValid) {
                try {
                  mark.entity.teleport(e.arena.at(from, 0.05), { keepVelocity: false });
                  self.shadowAt = { x: from.x, z: from.z };
                } catch {
                }
              }
            });
            run.at(st - 6, () => {
              if (mark) self.shade(mark, 1 /* Strike */);
            });
          });
        }
        run.at(last + 12, () => {
          const sh = self.shadow();
          if (sh) self.shade(sh, 0 /* Idle */);
        });
        run.windows(t.mark, last - t.mark + 2, Math.max(8, t.end - last - 2));
      }
    };
  }
  // ------------------------------------------------------------------ 07 The Hour That Never Occurred
  hourThatNeverOccurred() {
    const self = this;
    return {
      id: "hour_never",
      name: "The Hour That Never Occurred",
      index: 7,
      ultimate: true,
      interruptible: false,
      cooldown: ORISON.hour.cooldown,
      weight: (e) => e.healthFraction() < 0.92 && e.timeline.now > self.pulseUntil ? 5 : 0,
      run(run) {
        const e = run.enc;
        const t = beats3("hour_never", run.phase);
        const p2 = run.phase === 2;
        const i = run.phase - 1;
        self.shadowLeads(run);
        const patterns = Object.freeze(choosePatterns(e.rng, run.phase));
        const shapes = patterns.map((p) => new PatternShape(p, e.arena, ORISON.hour.wedges[i], ORISON.hour.band));
        self.lastHour = { previewed: patterns.map(patternLabel), executed: [] };
        trace("orison_preview", { patterns: self.lastHour.previewed.slice() });
        const centre = { x: e.arena.cx, z: e.arena.cz };
        patterns.forEach((_p, k) => {
          run.at(t.preview + k * t.step, () => {
            e.hazards.telegraph(shapes[k], t.show);
            self.numeral(k + 1, centre);
            for (const a of [0, 120, 240]) self.numeral(k + 1, e.arena.polar(a + k * 40, 9));
          });
        });
        for (let k = 0; k < patterns.length; k++) {
          const at = t.exec + k * t.gap;
          const commit = k === 0 ? t.preview : t.exec + (k - 1) * t.gap;
          run.at(commit, () => {
            e.hazards.strike({
              shape: shapes[k],
              warn: at - commit,
              quiet: true,
              tag: run.tag,
              damage: ORISON.hour.damage,
              fx: 14,
              sound: S3("hour_strike"),
              knockUp: 0.3,
              label: `hour_${k + 1}`,
              onStrike: () => {
                self.lastHour.executed.push(patternLabel(patterns[k]));
                trace("orison_execute", { index: k, pattern: patternLabel(patterns[k]) });
              }
            });
          });
          if (!p2) run.at(at - 10, () => e.hazards.telegraph(shapes[k], 10));
          run.at(at - 30, () => self.numeral(k + 1, centre));
        }
        const last = t.exec + 2 * t.gap;
        run.windows(t.preview, last - t.preview + 2, Math.max(10, t.end - last - 2));
      }
    };
  }
};
var MODULE3 = {
  create: (enc) => new OrisonController(enc),
  arena: { structure: "abm:court_of_unlived_hours", size: 47, height: 14, nameKey: "abm.arena.orison" },
  helpers: ["abm:orison_hourglass", "abm:orison_shadow"]
};

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
      interval: 13,
      warn: 36,
      count: 7,
      end: 168
    }
  }
};

// src/bosses/vesperra/armor.ts
import { Player as Player11 } from "@minecraft/server";

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
      eye = a instanceof Player11 ? a.getHeadLocation() : this.headOf(a);
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
var S4 = (id) => `abm.vesperra.${id}`;
var P4 = (id) => `abm:vesperra_${id}`;
var LANE_ORDERS = [
  [-1, 0, 1],
  [-1, 1, 0],
  [0, -1, 1],
  [0, 1, -1],
  [1, -1, 0],
  [1, 0, -1]
];
var beats4 = (name, phase) => vesperra_timings_default[name][phase === 2 ? "p2" : "p1"];
var VesperraController = class extends BossController {
  constructor(enc) {
    super(enc);
    this.key = "vesperra";
    this.displayName = "Vesperra";
    this.phase2Name = "The True Empress";
    this.trophyItem = "abm:ivory_diadem";
    this.style = {
      line: P4("tg_line"),
      arc: P4("tg_arc"),
      disc: P4("tg_disc"),
      safeLine: P4("safe_line"),
      safeArc: P4("safe_arc"),
      strike: P4("strike")
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
    e.audio.play(S4("intro_rise"), e.boss.location);
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
      for (const r of REGIONS) e.visuals.decor(P4("molt"), this.armor.anchor(r));
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
      e.visuals.spawn(P4("shards"), this.armor.anchor("c"));
    }, "death");
    e.timeline.after(t.collapse, () => e.visuals.scatter(P4("dust"), new Circle(e.boss.location.x, e.boss.location.z, 3).sample(e.rng, 8), e.arena.floorY + 0.4), "death");
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
      e.audio.play(S4("idle"), e.boss.location, 0.6);
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
        e.visuals.spawn(P4("shards"), at);
        e.visuals.spawn(P4("molt"), at);
        e.audio.play(S4("armor_break"), at);
        e.stagger(VESPERRA.armor.breakStagger);
        e.save();
      } else if (out.plateHit) {
        e.visuals.decor(P4("strike"), at);
        e.audio.play(S4("armor_hit"), at, 0.8);
      } else {
        if (region) e.visuals.decor(P4("drip"), at);
        e.audio.play(S4("body_hit"), at, 0.7);
      }
    });
    return dmg;
  }
  onHelperGone(h) {
    if (h.kind === "anchor" && h.killed) {
      this.enc.audio.play(S4("anchor_break"), h.entity.isValid ? h.entity.location : this.enc.boss.location);
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
        const t = beats4("ivory_scythe", run.phase);
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
                e.timeline.after(1 + i * 2, () => e.hazards.telegraphWith(P4("crescent"), band(6 + i * 1.2), 6), run.tag);
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
        const t = beats4("needle_procession", run.phase);
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
          run.strike(hit, { shape, warn: hit - (t.plant + k * 4), damage: C.damage, fx: 9, sound: S4("lane_erupt"), knockUp: 0.3, label: `procession_${k}` });
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
                sound: S4("lane_erupt"),
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
        const t = beats4("royal_molting", run.phase);
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
              particle: P4("plate"),
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
        const t = beats4("cocoon_edict", run.phase);
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
          const pen = e.visuals.pen(P4("thread"), P4("tg_arc"), void 0, y, hold / 20);
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
            sound: S4("cocoon_snap"),
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
        const t = beats4("false_submission", run.phase);
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
        const t = beats4("the_heirs", run.phase);
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
            if (h) e.visuals.decor(P4("molt"), { x: pos.x, y: e.arena.floorY + 0.8, z: pos.z });
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
        const t = beats4("coronation", run.phase);
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
                sound: S4("fracture_erupt"),
                knockUp: 0.35,
                label: `coronation_${i}`,
                onStrike: () => e.visuals.scatter(P4("fracture"), lane.sample(e.rng, 8), e.arena.floorY + 0.06)
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
