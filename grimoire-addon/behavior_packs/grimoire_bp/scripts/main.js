// src/config/global.ts
var CONFIG = {
  /** Give every player the three Grimoires the first time they join a world with the add-on. */
  starterKit: true,
  input: {
    /** Minimum ticks Use must be held before a release counts as a cast (20 ticks = 1 s). */
    minHoldTicks: 6,
    /** Ticks after a cast/cancel during which a new hold is ignored (guards duplicate callbacks). */
    rearmTicks: 2,
    /**
     * Compatibility fallback, OFF by default.  If a platform never raises itemStartUse for the
     * Grimoire, hold/release can be inferred from the repeating itemUse heartbeat instead.
     * Toggle in game with:  /scriptevent grimoire:config heartbeat on|off
     */
    heartbeatFallback: false,
    heartbeatGapTicks: 7
  },
  hud: {
    /** Ticks between action-bar refreshes while a Grimoire is held. */
    refreshTicks: 10
  },
  targeting: {
    /** Entity families treated as hostile spell targets. */
    hostileFamilies: ["monster"],
    /** Any entity carrying this tag is also treated as hostile (handy for test dummies). */
    testTag: "grimoire_target",
    /** When true other players are hostile targets instead of allies. */
    pvp: false,
    /** How far the caster's aim ray reaches when picking a target point. */
    aimRange: 40,
    /** A spell is never centred closer to its caster than this (blocks), e.g. when looking at your feet. */
    minAimDistance: 9,
    /** Hard cap on targets a single query returns. */
    maxTargets: 24
  },
  limits: {
    /** Maximum spell entities alive at once across the whole world. */
    maxActors: 220,
    /** Maximum temporary blocks (barriers / lights) alive at once. */
    maxTempBlocks: 1400,
    /** Maximum script-spawned particles per tick. */
    maxParticlesPerTick: 90
  }
};
var RUNTIME = CONFIG;

// src/config/version.ts
var VERSION = "1.1.1";

// src/main.ts
import { CommandPermissionLevel, CustomCommandStatus, ItemStack as ItemStack2, Player as Player4, system as system4, world as world5 } from "@minecraft/server";

// src/core/input.ts
import { EquipmentSlot, system, world as world2 } from "@minecraft/server";

// src/lib/scene.ts
import { world } from "@minecraft/server";

// src/config/ground.ts
var GROUND_ACTORS = {
  // Divine Word
  dw_column: 0,
  dw6_wall: 0,
  dw6_dome: 5.4,
  dw6_boundary: 8,
  // Dream & Nightmare
  dn_guest: 0,
  dn_guest_door: 0,
  dn_lull_wave: 1.1,
  dn_city_corridor: 0,
  dn_city_stair: 0,
  dn_city_stairfall: 0,
  dn_city_street: 0,
  dn_city_wave: 1.1,
  dn_dreamer_codex: 0,
  dn_dreamer_domain: 2.1,
  dn_dreamer_dream: 0,
  dn_dreamer_night: 0,
  dn_dreamer_stairs: 0,
  dn_dreamer_wheel: 0,
  // Elemental Dragon
  dragon_nature: 0,
  dragon_heat: 0,
  ed_nature_pillar: 0,
  ed_nature_quake: 2,
  ed_nature_root: 0,
  ed_nature_strata: 0,
  ed_heat_glass: 1.8,
  ed_heat_lane: 0,
  ed_heat_shimmer: 0,
  ed_heat_wave: 0,
  ed_tide_crown: 0,
  ed_tide_current: 0,
  ed_tide_frozen: 0,
  ed_air_shock: 1.3,
  ed_air_vortex: 0,
  ed5_gust: 1.6,
  ed5_icefan: 0,
  ed5_spike: 0,
  ed5_trail: 0,
  ed5_imprint_nature: 7.8,
  ed5_imprint_heat: 7.8,
  ed5_imprint_tide: 7.8,
  ed5_imprint_air: 7.8,
  ed5_inscription_nature: 1.9,
  ed5_inscription_heat: 1.9,
  ed5_inscription_tide: 1.9,
  ed5_inscription_air: 1.9,
  ed6_blast: 0,
  ed6_bridge: 0,
  ed6_emblem: 2,
  ed6_flora: 0,
  ed6_fog: 8,
  ed6_horizon: 0,
  ed6_iceshell: 0,
  ed6_ring: 0,
  ed6_spiral: 0,
  ed6_stone: 0
};
var GROUND_NEAR = { telegraph: 1, dw_circle: 2 };
var GROUND_NEAR_TOLERANCE = 6;
var FLOOR_ACTORS = /* @__PURE__ */ new Set([
  "cherub",
  "ophanim",
  "dw5_letter",
  "dw6_edifice",
  "dn_parade_bird",
  "dn_parade_doll",
  "dn_parade_horse",
  "dn_parade_stag",
  "dn_city_fragment",
  "dn_dreamer_pillow",
  "dn_dreamer_shard",
  "dn_dreamer_roomcube",
  "dragon_air",
  "dragon_tide",
  "ed_tide_shard",
  "ed5_skel_nature",
  "ed5_skel_heat",
  "ed5_skel_tide",
  "ed5_skel_air",
  "ed5_tablet_nature",
  "ed5_tablet_heat",
  "ed5_tablet_tide",
  "ed5_tablet_air",
  "ed6_spirit"
]);

// src/lib/bounds.ts
var LIMITS = /* @__PURE__ */ new Map();
function limits(dim) {
  let b = LIMITS.get(dim.id);
  if (!b) {
    try {
      const r = dim.heightRange;
      b = { min: r.min, max: r.max };
    } catch {
      b = { min: -64, max: 320 };
    }
    LIMITS.set(dim.id, b);
  }
  return b;
}
function inWorld(dim, loc) {
  const b = limits(dim);
  if (loc.y >= b.min + 0.01 && loc.y <= b.max - 0.01) return loc;
  return { x: loc.x, y: Math.min(Math.max(loc.y, b.min + 0.01), b.max - 0.01), z: loc.z };
}

// src/lib/vec.ts
var v = (x, y, z) => ({ x, y, z });
var add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
var sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
var mul = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
var dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
var len = (a) => Math.hypot(a.x, a.y, a.z);
var dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
var distXZ = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
var lerp = (a, b, t) => ({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
var up = (a, h) => ({ x: a.x, y: a.y + h, z: a.z });
function norm(a) {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 1 } : { x: a.x / l, y: a.y / l, z: a.z / l };
}
var flat = (a) => ({ x: a.x, y: 0, z: a.z });
function fromYaw(yawDeg) {
  const r = yawDeg * Math.PI / 180;
  return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
}
function yawOf(d) {
  return Math.atan2(-d.x, d.z) * 180 / Math.PI;
}
function right(d) {
  const f = norm(flat(d));
  return { x: -f.z, y: 0, z: f.x };
}
function polar(center, radius, angleDeg, dy = 0) {
  const r = angleDeg * Math.PI / 180;
  return { x: center.x + Math.cos(r) * radius, y: center.y + dy, z: center.z + Math.sin(r) * radius };
}
var clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
var smooth = (t) => {
  const c = clamp(t, 0, 1);
  return c * c * (3 - 2 * c);
};
var easeOut = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
var easeIn = (t) => Math.pow(clamp(t, 0, 1), 3);
function bezier(a, b, c, t) {
  return lerp(lerp(a, b, t), lerp(b, c, t), t);
}
function spline(pts, t) {
  const n = pts.length - 1;
  const f = clamp(t, 0, 1) * n;
  const i = Math.min(Math.floor(f), n - 1);
  const u = f - i;
  const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(i + 2, n)];
  const c = (a, b, cc, d) => 0.5 * (2 * b + (-a + cc) * u + (2 * a - 5 * b + 4 * cc - d) * u * u + (-a + 3 * b - 3 * cc + d) * u * u * u);
  return { x: c(p0.x, p1.x, p2.x, p3.x), y: c(p0.y, p1.y, p2.y, p3.y), z: c(p0.z, p1.z, p2.z, p3.z) };
}
function angleDelta(a, b) {
  let d = (b - a) % 360;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
function distToSegment(p, a, b) {
  const ab = sub(b, a);
  const t = clamp(dot(sub(p, a), ab) / Math.max(dot(ab, ab), 1e-9), 0, 1);
  return dist(p, add(a, mul(ab, t)));
}

// src/lib/targeting.ts
var NEVER = [
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:arrow",
  "minecraft:armor_stand",
  "minecraft:painting",
  "minecraft:leash_knot",
  "minecraft:fishing_hook",
  "minecraft:lightning_bolt",
  "minecraft:npc"
];
function isAlive(e) {
  if (!e || !e.isValid) return false;
  try {
    const h = e.getComponent("minecraft:health");
    return h === void 0 || h.currentValue > 0;
  } catch {
    return false;
  }
}
function isHostile(e, caster) {
  if (!isAlive(e) || e.id === caster.id) return false;
  try {
    if (e.matches({ families: ["grimoire_construct"] })) return false;
    if (e.typeId === "minecraft:player") return CONFIG.targeting.pvp;
    if (e.hasTag(CONFIG.targeting.testTag)) return true;
    for (const f of CONFIG.targeting.hostileFamilies) if (e.matches({ families: [f] })) return true;
  } catch {
  }
  return false;
}
function hostiles(dim, center, radius, caster, max = CONFIG.targeting.maxTargets) {
  let found = [];
  try {
    found = dim.getEntities({ location: center, maxDistance: radius, excludeTypes: NEVER, excludeFamilies: ["grimoire_construct"] });
  } catch {
    return [];
  }
  const out = found.filter((e) => isHostile(e, caster));
  out.sort((a, b) => dist(a.location, center) - dist(b.location, center));
  return out.slice(0, max);
}
function allies(dim, center, radius, caster) {
  if (CONFIG.targeting.pvp) return caster.isValid && dist(caster.location, center) <= radius ? [caster] : [];
  try {
    return dim.getPlayers({ location: center, maxDistance: radius }).filter((p) => isAlive(p));
  } catch {
    return [];
  }
}
var GHOST = ["minecraft:barrier", "minecraft:light_block_15"];
var TREE = /leaves|_log|_wood|_stem|hyphae|mushroom_block|mangrove_roots|azalea|bamboo|vine/;
function groundBelow(dim, loc, maxDrop = 40) {
  try {
    let y = loc.y;
    for (let i = 0; i < 24; i++) {
      const b = dim.getBlock({ x: loc.x, y: y + 0.01, z: loc.z });
      if (!b || b.isAir || b.isLiquid || GHOST.includes(b.typeId) || TREE.test(b.typeId)) break;
      y = Math.floor(y) + 1;
    }
    const opts = { maxDistance: maxDrop + 2, includePassableBlocks: false, includeLiquidBlocks: true, excludeTypes: GHOST };
    let hit = dim.getBlockFromRay({ x: loc.x, y: y + 1.5, z: loc.z }, { x: 0, y: -1, z: 0 }, opts);
    for (let i = 0; i < 14 && hit && TREE.test(hit.block.typeId); i++) {
      hit = dim.getBlockFromRay({ x: loc.x, y: hit.block.location.y - 0.01, z: loc.z }, { x: 0, y: -1, z: 0 }, opts);
    }
    if (hit) return { x: loc.x, y: hit.block.location.y + 1, z: loc.z };
  } catch {
  }
  return { x: loc.x, y: loc.y, z: loc.z };
}
function terrainTop(dim, loc, maxClimb = 12) {
  try {
    let y = loc.y, inside = false;
    for (let i = 0; i < maxClimb; i++) {
      const b = dim.getBlock({ x: loc.x, y: y + 0.05, z: loc.z });
      if (!b || b.isAir || b.isLiquid || GHOST.includes(b.typeId) || TREE.test(b.typeId)) break;
      inside = true;
      y = Math.floor(y + 0.05) + 1;
    }
    return inside ? y : void 0;
  } catch {
    return void 0;
  }
}
function plateau(dim, center, radius, maxRise = 2.5) {
  const base = groundBelow(dim, center);
  const r = Math.min(radius, 8) * 0.6;
  if (r < 1.2) return base;
  let y = base.y;
  for (let i = 0; i < 6; i++) {
    const a = i * Math.PI / 3;
    const g = groundBelow(dim, { x: base.x + Math.cos(a) * r, y: base.y + maxRise, z: base.z + Math.sin(a) * r }, 8);
    if (g.y > y && g.y <= base.y + maxRise + 0.01) y = g.y;
  }
  return { x: base.x, y, z: base.z };
}
function takeAim(caster, range = CONFIG.targeting.aimRange) {
  const dir = caster.getViewDirection();
  const head = caster.getHeadLocation();
  const dim = caster.dimension;
  let point;
  let entity;
  try {
    for (const h of caster.getEntitiesFromViewDirection({ maxDistance: range, excludeFamilies: ["grimoire_construct"] })) {
      if (isHostile(h.entity, caster)) {
        entity = h.entity;
        point = { ...h.entity.location };
        break;
      }
    }
  } catch {
  }
  if (!point) {
    try {
      const b = caster.getBlockFromViewDirection({ maxDistance: range, includePassableBlocks: false });
      if (b) {
        point = {
          x: b.block.location.x + b.faceLocation.x - dir.x * 0.6,
          y: b.block.location.y + b.faceLocation.y - dir.y * 0.6,
          z: b.block.location.z + b.faceLocation.z - dir.z * 0.6
        };
      }
    } catch {
    }
  }
  if (!point) point = add(head, mul(dir, range * 0.55));
  let forward = norm(flat(dir));
  try {
    forward = fromYaw(caster.getRotation().y);
  } catch {
  }
  const feet = caster.location;
  const minD = CONFIG.targeting.minAimDistance;
  if (!entity && Math.hypot(point.x - feet.x, point.z - feet.z) < minD) {
    point = { x: feet.x + forward.x * minD, y: feet.y + 1, z: feet.z + forward.z * minD };
  }
  return { point, ground: groundBelow(dim, point), entity, dir, forward, yaw: yawOf(forward), from: { ...caster.location } };
}
function focus(caster, aim, snap = 10) {
  if (aim.entity && isAlive(aim.entity)) return { center: groundBelow(caster.dimension, aim.entity.location), target: aim.entity };
  const near = hostiles(caster.dimension, aim.ground, snap, caster, 1);
  if (near.length) return { center: groundBelow(caster.dimension, near[0].location), target: near[0] };
  return { center: aim.ground };
}

// src/lib/scene.ts
var NS = "grimoire";
var secs = (s) => Math.max(0, Math.round(s * 20));
var warned = /* @__PURE__ */ new Set();
function warnOnce(key, msg) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`[grimoire] ${msg}`);
}
function settledY(dim, key, loc, size) {
  let radius = GROUND_ACTORS[key];
  let tolerance = 24;
  if (radius === void 0) {
    radius = GROUND_NEAR[key];
    if (radius === void 0) return void 0;
    tolerance = GROUND_NEAR_TOLERANCE;
  }
  const g = groundBelow(dim, loc);
  if (Math.abs(g.y - loc.y) > tolerance) return void 0;
  return radius * size >= 2 ? plateau(dim, g, radius * size).y : g.y;
}
var isBound = (key) => GROUND_ACTORS[key] !== void 0 || GROUND_NEAR[key] !== void 0;
var Actor = class {
  constructor(entity, typeId) {
    this.entity = entity;
    this.typeId = typeId;
    this.key = typeId.startsWith(`${NS}:`) ? typeId.slice(NS.length + 1) : typeId;
  }
  lastYaw = 0;
  sz = 1;
  gKey = "";
  gY;
  key;
  /**
   * Terrain handling for a requested position.  Ground-bound actors follow the surface (eased, so
   * walking over steps is not a jolt); free-moving ones are only lifted out of terrain they would
   * otherwise sink into.
   */
  settle(loc) {
    const bound = isBound(this.key);
    if (!bound && !FLOOR_ACTORS.has(this.key)) return loc;
    const k2 = `${Math.floor(loc.x)},${Math.floor(loc.z)},${Math.round(loc.y * 4)}`;
    if (k2 !== this.gKey) {
      this.gKey = k2;
      const dim = this.entity.dimension;
      this.gTarget = bound ? settledY(dim, this.key, loc, this.sz) : terrainTop(dim, loc);
      if (this.gTarget !== void 0 && this.gY === void 0) this.gY = bound ? this.gTarget : Math.max(loc.y, this.gTarget - 1.5);
    }
    if (this.gTarget === void 0) {
      if (this.gY === void 0) return loc;
      this.gY += (loc.y - this.gY) * 0.35;
      if (Math.abs(loc.y - this.gY) < 0.05) {
        this.gY = void 0;
        return loc;
      }
      return { x: loc.x, y: this.gY, z: loc.z };
    }
    const cur = this.gY ?? this.gTarget;
    const next = cur + (this.gTarget - cur) * (this.gTarget > cur ? 0.6 : 0.3);
    this.gY = Math.abs(this.gTarget - next) < 0.02 ? this.gTarget : next;
    return { x: loc.x, y: this.gY, z: loc.z };
  }
  gTarget;
  get valid() {
    return this.entity !== void 0 && this.entity.isValid;
  }
  get loc() {
    return this.valid ? this.entity.location : { x: 0, y: 0, z: 0 };
  }
  get yaw() {
    return this.lastYaw;
  }
  prop(name, value) {
    if (!this.valid) return this;
    try {
      this.entity.setProperty(`${NS}:${name}`, value);
    } catch (e) {
      warnOnce(`${this.typeId}.${name}`, `cannot set ${name}=${value} on ${this.typeId}: ${e}`);
    }
    return this;
  }
  state(n) {
    return this.prop("state", n);
  }
  kind(n) {
    return this.prop("kind", n);
  }
  size(n) {
    this.sz = n;
    return this.prop("size", n);
  }
  skin(n) {
    return this.prop("skin", n);
  }
  /**
   * The facing the model is drawn with.  The entity rotation alone is not enough (the game steers a
   * mob's body yaw by its own rules), so the wanted yaw is also sent as the synced property
   * grimoire:yaw, which the client uses to turn the model (see kit/pack.py, "Facing").
   */
  sentYaw = 0;
  setYaw(yaw) {
    this.lastYaw = yaw;
    let y = ((yaw + 180) % 360 + 360) % 360 - 180;
    if (y === -180) y = 180;
    y = Math.round(y * 100) / 100;
    if (y !== this.sentYaw) {
      this.sentYaw = y;
      this.prop("yaw", y);
    }
  }
  /** Teleport (and optionally face a yaw).  Called every tick this gives smooth motion. */
  move(loc, yaw) {
    if (!this.valid) return this;
    if (yaw !== void 0) this.setYaw(yaw);
    try {
      this.entity.teleport(inWorld(this.entity.dimension, this.settle(loc)), { rotation: { x: 0, y: this.lastYaw } });
    } catch {
    }
    return this;
  }
  face(yaw) {
    if (!this.valid) return this;
    this.setYaw(yaw);
    try {
      this.entity.teleport(this.entity.location, { rotation: { x: 0, y: yaw } });
    } catch {
    }
    return this;
  }
  anim(name) {
    if (!this.valid) return this;
    try {
      this.entity.playAnimation(name);
    } catch {
    }
    return this;
  }
  remove() {
    if (!this.valid) return;
    try {
      this.entity.remove();
    } catch {
    }
  }
};
var Scene = class {
  constructor(spellId, caster) {
    this.spellId = spellId;
    this.caster = caster;
    this.dim = caster.dimension;
    this.dimId = caster.dimension.id;
    this.origin = { ...caster.location };
  }
  tick = 0;
  ended = false;
  dim;
  dimId;
  origin;
  actors = /* @__PURE__ */ new Set();
  timeline = [];
  loops = [];
  endHooks = [];
  endTick = Number.POSITIVE_INFINITY;
  /** Run fn once at an absolute scene tick. */
  at(t, fn) {
    this.timeline.push({ t: Math.max(Math.round(t), this.tick), fn });
    return this;
  }
  /** Run fn once `delay` ticks from now. */
  after(delay, fn) {
    return this.at(this.tick + Math.max(0, Math.round(delay)), fn);
  }
  /** Run fn every `every` ticks while from <= tick < to.  fn receives ticks elapsed since `from`. */
  every(every, fn, from = 0, to = Number.POSITIVE_INFINITY) {
    this.loops.push({ from: Math.round(from), to: Math.round(to), every: Math.max(1, Math.round(every)), fn });
    return this;
  }
  /** Run fn each tick in [from, to) with progress 0..1. */
  span(from, to, fn) {
    const a = Math.round(from), b = Math.max(a + 1, Math.round(to));
    return this.every(1, (e) => fn(Math.min(1, e / (b - a - 1 || 1)), e), a, b);
  }
  /** Spawn a spell entity that is removed automatically when the scene ends. */
  spawn(typeId, loc, opts = {}) {
    const id = typeId.includes(":") ? typeId : `${NS}:${typeId}`;
    if (this.ended || Scenes.actorCount() >= CONFIG.limits.maxActors) return new Actor(void 0, id);
    let e;
    try {
      const key = id.slice(NS.length + 1);
      const gy = isBound(key) ? settledY(this.dim, key, loc, opts.size ?? 1) : FLOOR_ACTORS.has(key) ? terrainTop(this.dim, loc) : void 0;
      if (gy !== void 0) loc = { x: loc.x, y: gy, z: loc.z };
    } catch {
    }
    loc = inWorld(this.dim, loc);
    try {
      e = this.dim.spawnEntity(id, loc, opts.yaw !== void 0 ? { initialRotation: opts.yaw } : void 0);
    } catch (err) {
      warnOnce(`spawn.${id}`, `cannot spawn ${id}: ${err}`);
    }
    const a = new Actor(e, id);
    if (e) {
      this.actors.add(a);
      try {
        e.addTag("grimoire_scene");
      } catch {
      }
      if (opts.kind !== void 0) a.kind(opts.kind);
      if (opts.size !== void 0) a.size(opts.size);
      if (opts.skin !== void 0) a.skin(opts.skin);
      if (opts.state !== void 0) a.state(opts.state);
      if (opts.yaw !== void 0) a.move(loc, opts.yaw);
    }
    return a;
  }
  /** Remove one actor now. */
  despawn(a) {
    a.remove();
    this.actors.delete(a);
  }
  /** Keep an actor glued to a moving entity; the actor is removed when the target is gone. */
  follow(a, target, dy = 0, until = Number.POSITIVE_INFINITY) {
    return this.every(1, () => {
      if (!a.valid) return;
      if (!target.isValid) {
        this.despawn(a);
        return;
      }
      const l = target.location;
      a.move({ x: l.x, y: l.y + dy, z: l.z });
    }, this.tick, until);
  }
  onEnd(fn) {
    this.endHooks.push(fn);
    return this;
  }
  /** Schedule the scene to finish (and clean up) at an absolute tick. */
  endAt(t) {
    this.endTick = Math.round(t);
    return this;
  }
  get casterOk() {
    return this.caster.isValid && this.caster.dimension.id === this.dimId;
  }
  /** Finish now: runs end hooks, removes every actor. Safe to call repeatedly. */
  end() {
    if (this.ended) return;
    this.ended = true;
    for (const h of this.endHooks) {
      try {
        h();
      } catch (e) {
        console.warn(`[grimoire] ${this.spellId} end hook: ${e}`);
      }
    }
    for (const a of this.actors) a.remove();
    this.actors.clear();
    this.timeline.length = 0;
    this.loops.length = 0;
    Scenes.active.delete(this);
  }
  /** @internal advance one tick */
  step() {
    if (this.ended) return;
    if (!this.casterOk || this.tick >= this.endTick) {
      this.end();
      return;
    }
    try {
      for (const l of this.loops) {
        if (this.tick >= l.from && this.tick < l.to && (this.tick - l.from) % l.every === 0) l.fn(this.tick - l.from);
        if (this.ended) return;
      }
      if (this.timeline.length) {
        const due = this.timeline.filter((e) => e.t <= this.tick);
        if (due.length) {
          this.timeline = this.timeline.filter((e) => e.t > this.tick);
          due.sort((a, b) => a.t - b.t);
          for (const e of due) {
            e.fn();
            if (this.ended) return;
          }
        }
      }
      this.loops = this.loops.filter((l) => this.tick < l.to);
    } catch (e) {
      console.warn(`[grimoire] ${this.spellId} failed at tick ${this.tick}: ${e} ${e?.stack ?? ""}`);
      this.end();
      return;
    }
    this.tick++;
  }
};
var Scenes = {
  active: /* @__PURE__ */ new Set(),
  start(spellId, caster) {
    const s = new Scene(spellId, caster);
    this.active.add(s);
    return s;
  },
  actorCount() {
    let n = 0;
    for (const s of this.active) n += s.actors.size;
    return n;
  },
  tickAll() {
    for (const s of [...this.active]) s.step();
  },
  endFor(player) {
    for (const s of [...this.active]) if (s.caster.id === player.id) s.end();
  },
  endAll() {
    for (const s of [...this.active]) s.end();
  },
  /** Remove spell entities left behind by a previous script session. */
  sweepOrphans() {
    for (const id of ["overworld", "nether", "the_end"]) {
      try {
        for (const e of world.getDimension(id).getEntities({ families: ["grimoire_construct"] })) {
          try {
            e.remove();
          } catch {
          }
        }
      } catch {
      }
    }
  }
};

// src/core/registry.ts
var GRIMOIRES = {
  divine_word: { id: "divine_word", item: "grimoire:divine_word", name: "Codex of the First Word", short: "Divine Word", color: "\xA76" },
  dream_nightmare: { id: "dream_nightmare", item: "grimoire:dream_nightmare", name: "The Unawakened Codex", short: "Dream & Nightmare", color: "\xA7d" },
  elemental_dragon: { id: "elemental_dragon", item: "grimoire:elemental_dragon", name: "Codex of the Four Primordial Dragons", short: "Elemental Dragon", color: "\xA7a" }
};
var GRIMOIRE_BY_ITEM = Object.fromEntries(Object.values(GRIMOIRES).map((g) => [g.item, g]));
var GRIMOIRE_ORDER = ["divine_word", "dream_nightmare", "elemental_dragon"];
var SPELL_META = [
  { id: "dw01", grimoire: "divine_word", index: 0, cooldown: 15, tier: "signature", name: "Seraphic Litany: The Sixfold Sanctus", short: "Seraphic Litany" },
  { id: "dw02", grimoire: "divine_word", index: 1, cooldown: 28, tier: "signature", name: "Cherubic Testament: The Four Living Witnesses", short: "Cherubic Testament" },
  { id: "dw03", grimoire: "divine_word", index: 2, cooldown: 35, tier: "signature", name: "Ophanim: The Unblinking Judgment", short: "Ophanim" },
  { id: "dw04", grimoire: "divine_word", index: 3, cooldown: 45, tier: "signature", name: "Divine Edict: Let There Be Sanctuary", short: "Let There Be Sanctuary" },
  { id: "dw05", grimoire: "divine_word", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Threefold Heavenly Throne", short: "Threefold Heavenly Throne" },
  { id: "dw06", grimoire: "divine_word", index: 5, cooldown: 360, tier: "extra", name: "The Word Before Creation", short: "Word Before Creation" },
  { id: "dn01", grimoire: "dream_nightmare", index: 0, cooldown: 16, tier: "signature", name: "Reverie Procession: Parade of the Sleeping Moon", short: "Reverie Procession" },
  { id: "dn02", grimoire: "dream_nightmare", index: 1, cooldown: 24, tier: "signature", name: "Nightmare Intrusion: The Guest Behind the Door", short: "Nightmare Intrusion" },
  { id: "dn03", grimoire: "dream_nightmare", index: 2, cooldown: 38, tier: "signature", name: "House of Shifting Sleep", short: "House of Shifting Sleep" },
  { id: "dn04", grimoire: "dream_nightmare", index: 3, cooldown: 46, tier: "signature", name: "Lullaby and Scream", short: "Lullaby and Scream" },
  { id: "dn05", grimoire: "dream_nightmare", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The City That Sleeps Above the World", short: "City That Sleeps" },
  { id: "dn06", grimoire: "dream_nightmare", index: 5, cooldown: 360, tier: "extra", name: "The Dreamer Who Never Wakes", short: "Dreamer Who Never Wakes" },
  { id: "ed01", grimoire: "elemental_dragon", index: 0, cooldown: 28, tier: "signature", name: "Genesis Colossus: The Walking Continent", short: "Genesis Colossus" },
  { id: "ed02", grimoire: "elemental_dragon", index: 1, cooldown: 24, tier: "signature", name: "Thermal Tyrant: Furnace of the Carnotaur", short: "Thermal Tyrant" },
  { id: "ed03", grimoire: "elemental_dragon", index: 2, cooldown: 32, tier: "signature", name: "Abyssal Cryotitan: The Frozen Tidal Crown", short: "Abyssal Cryotitan" },
  { id: "ed04", grimoire: "elemental_dragon", index: 3, cooldown: 20, tier: "signature", name: "Aether Raptor: Symphony of the Four Wings", short: "Aether Raptor" },
  { id: "ed05", grimoire: "elemental_dragon", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Chronicle of Buried Kingdoms", short: "Chronicle of Buried Kingdoms" },
  { id: "ed06", grimoire: "elemental_dragon", index: 5, cooldown: 360, tier: "extra", name: "The World Before Names", short: "World Before Names" }
];
var META_BY_ID = Object.fromEntries(SPELL_META.map((m) => [m.id, m]));
function metaFor(grimoire, index) {
  const m = SPELL_META.find((s) => s.grimoire === grimoire && s.index === index);
  if (!m) throw new Error(`no spell ${grimoire}#${index}`);
  return m;
}
var SPELLS = /* @__PURE__ */ new Map();
function defineSpell(id, cast) {
  const meta = META_BY_ID[id];
  if (!meta) throw new Error(`unknown spell id ${id}`);
  return { ...meta, cast };
}
function registerSpell(def) {
  SPELLS.set(def.id, def);
}
function getSpell(id) {
  return SPELLS.get(id);
}

// src/core/state.ts
var SEL = "grim:sel";
var CD = "grim:cd";
var cache = /* @__PURE__ */ new Map();
function load(p) {
  let c = cache.get(p.id);
  if (c) return c;
  c = { sel: [0, 0, 0], cd: {} };
  try {
    const s = p.getDynamicProperty(SEL);
    if (typeof s === "string") {
      const parts = s.split(",").map((x) => Number(x));
      for (let i = 0; i < 3; i++) if (Number.isInteger(parts[i]) && parts[i] >= 0 && parts[i] < 6) c.sel[i] = parts[i];
    }
    const d = p.getDynamicProperty(CD);
    if (typeof d === "string") {
      const obj = JSON.parse(d);
      const now = Date.now();
      for (const [k2, v2] of Object.entries(obj)) if (typeof v2 === "number" && v2 > now) c.cd[k2] = v2;
    }
  } catch {
  }
  cache.set(p.id, c);
  return c;
}
function saveCd(p, c) {
  const now = Date.now();
  for (const k2 of Object.keys(c.cd)) if (c.cd[k2] <= now) delete c.cd[k2];
  try {
    p.setDynamicProperty(CD, JSON.stringify(c.cd));
  } catch {
  }
}
function getSelection(p, g) {
  return load(p).sel[GRIMOIRE_ORDER.indexOf(g)];
}
function setSelection(p, g, index) {
  const c = load(p);
  c.sel[GRIMOIRE_ORDER.indexOf(g)] = (index % 6 + 6) % 6;
  try {
    p.setDynamicProperty(SEL, c.sel.join(","));
  } catch {
  }
}
function cooldownLeft(p, spellId) {
  const until = load(p).cd[spellId];
  if (!until) return 0;
  return Math.max(0, (until - Date.now()) / 1e3);
}
function startCooldown(p, spellId, seconds) {
  const c = load(p);
  c.cd[spellId] = Date.now() + seconds * 1e3;
  saveCd(p, c);
}
function clearCooldowns(p) {
  const c = load(p);
  c.cd = {};
  saveCd(p, c);
}
function forget(playerId) {
  cache.delete(playerId);
}

// src/core/hud.ts
var pad2 = (n) => n < 10 ? `0${n}` : `${n}`;
function fmt(sec) {
  const s = Math.ceil(sec);
  return s >= 60 ? `${Math.floor(s / 60)}:${pad2(s % 60)}` : `${s}s`;
}
function drawHud(p, g, index, note2) {
  const spells = SPELL_META.filter((m) => m.grimoire === g.id);
  const cur = spells[index];
  const left = cooldownLeft(p, cur.id);
  const status = note2 ?? (left > 0 ? `\xA7c${fmt(left)}` : "\xA7aREADY");
  const tierMark = cur.tier === "imperial" ? "\xA76*" : cur.tier === "extra" ? "\xA7d**" : "";
  let pips = "";
  for (const s of spells) {
    const c = cooldownLeft(p, s.id) > 0 ? "\xA7c" : "\xA7a";
    pips += s.index === index ? `\xA7f[${c}${s.index + 1}\xA7f] ` : `${c}${s.index + 1} `;
  }
  try {
    p.onScreenDisplay.setActionBar(`${g.color}${g.short} \xA78| \xA7f${pad2(index + 1)} \xA7e${cur.short}${tierMark} \xA78| ${status}
${pips.trimEnd()}`);
  } catch {
  }
}

// src/core/presentation.ts
var NOOP = { tick() {
}, release() {
}, cancel() {
} };
var presenter = { select() {
}, prepStart: () => NOOP, deny() {
} };
function setPresenter(p) {
  presenter = p;
}
function present() {
  return presenter;
}

// src/core/input.ts
var states = /* @__PURE__ */ new Map();
function st(p) {
  let s = states.get(p.id);
  if (!s) {
    s = { wasSneaking: p.isSneaking, rearmAt: 0, session: 0, lastHud: -999, hudDirty: true, lastStartTick: -999 };
    states.set(p.id, s);
  }
  return s;
}
function heldGrimoire(p) {
  try {
    const it = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
    return it ? GRIMOIRE_BY_ITEM[it.typeId] : void 0;
  } catch {
    return void 0;
  }
}
function note(s, text, ticks = 30) {
  s.note = { text, until: system.currentTick + ticks };
  s.hudDirty = true;
}
function cancel(s, why, quiet = false) {
  const prep = s.prep;
  if (!prep) return;
  s.prep = void 0;
  s.rearmAt = system.currentTick + CONFIG.input.rearmTicks;
  try {
    prep.handle.cancel();
  } catch (e) {
    console.warn(`[grimoire] cancel fx: ${e}`);
  }
  if (!quiet) note(s, `\xA77${why}`);
}
function begin(p, g, mode) {
  const s = st(p);
  const now = system.currentTick;
  if (s.prep) {
    if (s.prep.mode === "heartbeat" && mode === "charge") {
      s.prep.mode = "charge";
      return;
    }
    cancel(s, "Interrupted", true);
  }
  if (now < s.rearmAt) return;
  if (p.isSneaking) {
    note(s, "\xA77Stand up to cast");
    return;
  }
  const meta = metaFor(g.id, getSelection(p, g.id));
  if (cooldownLeft(p, meta.id) > 0) {
    s.hudDirty = true;
    try {
      present().deny(p, g);
    } catch {
    }
    return;
  }
  if (!getSpell(meta.id)) {
    note(s, "\xA7cSpell unavailable");
    return;
  }
  let handle;
  try {
    handle = present().prepStart(p, g, meta);
  } catch (e) {
    console.warn(`[grimoire] prep fx: ${e}`);
    handle = { tick() {
    }, release() {
    }, cancel() {
    } };
  }
  s.prep = { g, meta, startTick: now, slot: p.selectedSlotIndex, session: ++s.session, handle, mode, lastBeat: now };
  note(s, "\xA7bPreparing... \xA77release to cast", 60);
}
function release(p) {
  const s = st(p);
  const prep = s.prep;
  if (!prep) return;
  const now = system.currentTick;
  const held = now - prep.startTick;
  if (heldGrimoire(p)?.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) {
    cancel(s, "Cancelled");
    return;
  }
  if (p.isSneaking) {
    cancel(s, "Cancelled (crouching)");
    return;
  }
  if (held < CONFIG.input.minHoldTicks) {
    cancel(s, "Hold Use longer, then release");
    return;
  }
  if (cooldownLeft(p, prep.meta.id) > 0) {
    cancel(s, "On cooldown");
    return;
  }
  s.prep = void 0;
  s.rearmAt = now + CONFIG.input.rearmTicks;
  const spell = getSpell(prep.meta.id);
  if (!spell) {
    try {
      prep.handle.cancel();
    } catch {
    }
    return;
  }
  const scene = Scenes.start(spell.id, p);
  let ok = false;
  try {
    ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: held });
  } catch (e) {
    console.warn(`[grimoire] ${spell.id} cast failed: ${e} ${e?.stack ?? ""}`);
    ok = false;
  }
  if (ok === false) {
    scene.end();
    try {
      prep.handle.cancel();
    } catch {
    }
    note(s, "\xA77No valid target");
    return;
  }
  startCooldown(p, spell.id, spell.cooldown);
  try {
    prep.handle.release();
  } catch (e) {
    console.warn(`[grimoire] release fx: ${e}`);
  }
  s.note = void 0;
  s.hudDirty = true;
}
function tickPlayer(p, now) {
  const s = st(p);
  const g = heldGrimoire(p);
  if (g?.id !== s.held?.id) {
    s.held = g;
    s.hudDirty = true;
  }
  const sneaking = p.isSneaking;
  const entered = sneaking && !s.wasSneaking;
  s.wasSneaking = sneaking;
  if (s.prep) {
    const prep = s.prep;
    if (sneaking) cancel(s, "Cancelled (crouching)");
    else if (!g || g.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) cancel(s, "Cancelled");
    else if (prep.stopTick !== void 0 && now > prep.stopTick) cancel(s, "Cancelled");
    else if (prep.mode === "heartbeat" && now - prep.lastBeat > CONFIG.input.heartbeatGapTicks) release(p);
    else {
      try {
        prep.handle.tick(now - prep.startTick);
      } catch (e) {
        console.warn(`[grimoire] prep tick: ${e}`);
      }
    }
  } else if (entered && g) {
    const next = (getSelection(p, g.id) + 1) % 6;
    setSelection(p, g.id, next);
    s.note = void 0;
    s.hudDirty = true;
    try {
      present().select(p, g, metaFor(g.id, next));
    } catch (e) {
      console.warn(`[grimoire] select fx: ${e}`);
    }
  }
  if (s.pendingBeat !== void 0 && now > s.pendingBeat) {
    const beat = s.pendingBeat;
    s.pendingBeat = void 0;
    if (CONFIG.input.heartbeatFallback && s.lastStartTick < beat && g) {
      if (s.prep?.mode === "heartbeat") s.prep.lastBeat = beat;
      else if (!s.prep) begin(p, g, "heartbeat");
    }
  }
  if (g) {
    if (s.note && now > s.note.until) {
      s.note = void 0;
      s.hudDirty = true;
    }
    if (s.hudDirty || now - s.lastHud >= CONFIG.hud.refreshTicks) {
      s.lastHud = now;
      s.hudDirty = false;
      drawHud(p, g, getSelection(p, g.id), s.note?.text);
    }
  }
}
function isGrimoire(item) {
  return item ? GRIMOIRE_BY_ITEM[item.typeId] : void 0;
}
function installInput() {
  world2.afterEvents.itemStartUse.subscribe((ev) => {
    const g = isGrimoire(ev.itemStack);
    if (!g) return;
    st(ev.source).lastStartTick = system.currentTick;
    begin(ev.source, g, "charge");
  });
  world2.afterEvents.itemReleaseUse.subscribe((ev) => {
    const s = states.get(ev.source.id);
    if (s?.prep?.mode === "charge") release(ev.source);
  });
  const stop = (p) => {
    const s = states.get(p.id);
    if (s?.prep && s.prep.mode === "charge" && s.prep.stopTick === void 0) s.prep.stopTick = system.currentTick;
  };
  world2.afterEvents.itemStopUse.subscribe((ev) => stop(ev.source));
  world2.afterEvents.itemCompleteUse.subscribe((ev) => stop(ev.source));
  world2.afterEvents.itemUse.subscribe((ev) => {
    if (!CONFIG.input.heartbeatFallback || !isGrimoire(ev.itemStack)) return;
    st(ev.source).pendingBeat = system.currentTick;
  });
  world2.afterEvents.entityDie.subscribe((ev) => {
    if (ev.deadEntity.typeId !== "minecraft:player") return;
    const s = states.get(ev.deadEntity.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.deadEntity);
  });
  world2.afterEvents.playerDimensionChange.subscribe((ev) => {
    const s = states.get(ev.player.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.player);
  });
  world2.beforeEvents.playerLeave.subscribe((ev) => {
    const id = ev.player.id;
    const s = states.get(id);
    system.run(() => {
      if (s) cancel(s, "Cancelled", true);
      states.delete(id);
      forget(id);
      for (const sc of [...Scenes.active]) if (!sc.caster.isValid) sc.end();
    });
  });
}
function tickInput() {
  const now = system.currentTick;
  for (const p of world2.getAllPlayers()) {
    try {
      if (p.isValid) tickPlayer(p, now);
    } catch (e) {
      console.warn(`[grimoire] input tick: ${e}`);
    }
  }
}

// src/config/books.ts
var VISION_STATE = { hidden: 0, show: 1 };
var CHARGE_STATE = { hidden: 0, form: 1, loop: 2, release: 3, cancel: 4 };
var BOOKS = {
  /** Asset prefix per Grimoire: actors book_<g>_vision / book_<g>_charge, sounds and particles book_<g>_*. */
  prefix: { divine_word: "dw", dream_nightmare: "dn", elemental_dragon: "ed" },
  vision: {
    /**
     * Spawn the selection vision entity in front of the eyes.  Off: on an iPhone a world entity never
     * lined up with the first-person book (different cameras, and it trails when turning); the held
     * book now flares its own built-in magic circle on crouch instead (tools/assets/_book_aura.py).
     * The page-turn sound still plays.
     */
    entity: false,
    /** Life of the selection vision; its one-shot "show" animation lasts exactly 1.2 s. */
    ticks: 24,
    /**
     * Placement from the eyes: along the view, to the right, and vertical offset.  A small emblem sitting
     * on top of the held book on an iPhone screen (measured from screenshots; the first-person book is
     * drawn over the world, so a vision behind it is hidden).  Its size is EFFECT_SCALE in books_<g>.py.
     */
    ahead: 1.3,
    right: 0.62,
    up: 0.11,
    /** Volume of the page-turn + motif sound. */
    volume: 0.8
  },
  charge: {
    /**
     * Spawn the charge construct entity ahead of the eyes (and its motes).  Off for the same reason as
     * vision.entity: the held book itself opens and spins its built-in circle while Use is held.  The
     * charge / release sounds and the release burst still play.
     */
    entity: false,
    /** Ticks of the one-shot "form" animation (1.5 s) before switching to the "loop" state. */
    formTicks: 30,
    /** The release flare (0.5 s) and the quiet cancel fold (0.4 s) before the construct is removed. */
    releaseTicks: 10,
    cancelTicks: 8,
    /**
     * Placement from the eyes: ahead along the view, to the right (keeps the crosshair clear), above eye
     * line - so on screen it rises out of the held book, which lifts and opens toward it.  Its size is
     * EFFECT_SCALE in books_<g>.py.
     */
    ahead: 2.2,
    right: 0.85,
    up: 0.35,
    /** The view direction's vertical part is clamped so the construct stays in front when looking up or down. */
    minDirY: -0.45,
    maxDirY: 0.55,
    /** Fraction of the way to the new place moved each tick (1 = rigid, lower = floats behind the view). */
    follow: 0.5,
    /** Ambient mote particle every N ticks while held. */
    moteEvery: 4,
    /** The ~2 s charge swell is retriggered every N held ticks (quieter after the first time). */
    soundEvery: 44,
    soundVolume: 0.75,
    soundRepeatVolume: 0.5,
    /** Particle bursts on release (spread around the construct). */
    burstCount: 3,
    burstRadius: 0.6,
    /** Watchdog: a preparation that receives no tick for this many ticks folds itself away. */
    stallTicks: 10
  },
  deny: {
    volume: 0.7
  }
};

// src/lib/fx.ts
import { MolangVariableMap, system as system2 } from "@minecraft/server";
var budgetTick = -1;
var budget = 0;
function take(n = 1) {
  if (system2.currentTick !== budgetTick) {
    budgetTick = system2.currentTick;
    budget = CONFIG.limits.maxParticlesPerTick;
  }
  if (budget < n) return false;
  budget -= n;
  return true;
}
function particle(dim, id, loc, vars) {
  if (!take()) return;
  try {
    dim.spawnParticle(id.includes(":") ? id : `${NS}:${id}`, inWorld(dim, loc), vars);
  } catch {
  }
}
function ring(dim, id, center, radius, n, phaseDeg = 0) {
  for (let i = 0; i < n; i++) {
    const a = (phaseDeg + 360 * i / n) * Math.PI / 180;
    particle(dim, id, { x: center.x + Math.cos(a) * radius, y: center.y, z: center.z + Math.sin(a) * radius });
  }
}
function line(dim, id, a, b, n) {
  for (let i = 0; i < n; i++) {
    const t = n === 1 ? 0.5 : i / (n - 1);
    particle(dim, id, { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t });
  }
}
function burst(dim, id, center, radius, n) {
  for (let i = 0; i < n; i++) {
    const y = 1 - 2 * (i + 0.5) / n;
    const r = Math.sqrt(1 - y * y) * radius;
    const a = i * 2.39996;
    particle(dim, id, { x: center.x + Math.cos(a) * r, y: center.y + y * radius, z: center.z + Math.sin(a) * r });
  }
}
function sound(dim, id, loc, volume = 1, pitch = 1) {
  try {
    dim.playSound(id.includes(".") ? id : `${NS}.${id}`, inWorld(dim, loc), { volume, pitch });
  } catch {
  }
}

// src/core/books.ts
var visions = /* @__PURE__ */ new Map();
var charges = /* @__PURE__ */ new Map();
function frame(p, ahead, rightOff, upOff, minY = -1, maxY = 1) {
  const head = p.getHeadLocation();
  const raw = p.getViewDirection();
  const d = norm({ x: raw.x, y: clamp(raw.y, minY, maxY), z: raw.z });
  const r = right(d);
  const loc = add(add(add(head, mul(d, ahead)), mul(r, rightOff)), { x: 0, y: upOff, z: 0 });
  return { loc, yaw: yawOf({ x: -d.x, y: 0, z: -d.z }) };
}
function endIn(map, id) {
  const s = map.get(id);
  map.delete(id);
  if (s && !s.ended) s.end();
}
function track(map, p, scene) {
  map.set(p.id, scene);
  scene.onEnd(() => {
    if (map.get(p.id) === scene) map.delete(p.id);
  });
}
function select(p, g, meta) {
  const pre = BOOKS.prefix[g.id];
  const cfg = BOOKS.vision;
  endIn(visions, p.id);
  if (!cfg.entity) {
    sound(p.dimension, `book_${pre}_select`, p.getHeadLocation(), cfg.volume);
    return;
  }
  const scene = Scenes.start("book", p);
  track(visions, p, scene);
  const f = frame(p, cfg.ahead, cfg.right, cfg.up);
  const vision = scene.spawn(`book_${pre}_vision`, f.loc, { yaw: f.yaw, kind: meta.index, state: VISION_STATE.show });
  sound(p.dimension, `book_${pre}_select`, f.loc, cfg.volume);
  scene.every(1, () => {
    if (!vision.valid) return;
    const n = frame(p, cfg.ahead, cfg.right, cfg.up);
    vision.move(n.loc, n.yaw);
  }, 1);
  scene.endAt(cfg.ticks);
}
function prepStart(p, g, meta) {
  const pre = BOOKS.prefix[g.id];
  const cfg = BOOKS.charge;
  const id = `book_${pre}_charge`;
  endIn(charges, p.id);
  if (!cfg.entity) return prepSound(p, pre);
  const scene = Scenes.start("book", p);
  track(charges, p, scene);
  const where = () => frame(p, cfg.ahead, cfg.right, cfg.up, cfg.minDirY, cfg.maxDirY);
  let place = where();
  let state = CHARGE_STATE.form;
  let done = false;
  let lastSeen = 0;
  let retryAt = 0;
  const spawn = (st2) => scene.spawn(id, place.loc, { yaw: place.yaw, kind: meta.index, state: st2 });
  let actor = spawn(state);
  sound(p.dimension, `book_${pre}_charge`, place.loc, cfg.soundVolume);
  const finish2 = (st2, ticks) => {
    if (done) return;
    done = true;
    actor.state(st2);
    scene.endAt(scene.tick + ticks);
  };
  const handle = {
    tick(held) {
      if (done || scene.ended) return;
      lastSeen = scene.tick;
      const target = where();
      place = { loc: lerp(place.loc, target.loc, cfg.follow), yaw: target.yaw };
      const want = held >= cfg.formTicks ? CHARGE_STATE.loop : CHARGE_STATE.form;
      if (!actor.valid) {
        if (scene.tick < retryAt) return;
        retryAt = scene.tick + 10;
        scene.despawn(actor);
        actor = spawn(want);
        state = want;
      } else if (want !== state) {
        state = want;
        actor.state(state);
      }
      actor.move(place.loc, place.yaw);
      if (held % cfg.moteEvery === 0) particle(p.dimension, `book_${pre}_mote`, place.loc);
      if (held > 0 && held % cfg.soundEvery === 0) sound(p.dimension, `book_${pre}_charge`, place.loc, cfg.soundRepeatVolume);
    },
    release() {
      if (done || scene.ended) return;
      const at = actor.valid ? actor.loc : place.loc;
      burst(p.dimension, `book_${pre}_burst`, at, cfg.burstRadius, cfg.burstCount);
      sound(p.dimension, `book_${pre}_release`, at);
      finish2(CHARGE_STATE.release, cfg.releaseTicks);
    },
    cancel() {
      if (done || scene.ended) return;
      finish2(CHARGE_STATE.cancel, cfg.cancelTicks);
    }
  };
  scene.every(1, () => {
    if (!done && scene.tick - lastSeen > cfg.stallTicks) handle.cancel();
  }, 1);
  return handle;
}
function prepSound(p, pre) {
  const cfg = BOOKS.charge;
  let done = false;
  sound(p.dimension, `book_${pre}_charge`, p.getHeadLocation(), cfg.soundVolume);
  return {
    tick(held) {
      if (done || !p.isValid) return;
      if (held > 0 && held % cfg.soundEvery === 0) sound(p.dimension, `book_${pre}_charge`, p.getHeadLocation(), cfg.soundRepeatVolume);
    },
    release() {
      if (done || !p.isValid) return;
      done = true;
      const at = frame(p, cfg.ahead, cfg.right, cfg.up, cfg.minDirY, cfg.maxDirY).loc;
      burst(p.dimension, `book_${pre}_burst`, at, cfg.burstRadius, cfg.burstCount);
      sound(p.dimension, `book_${pre}_release`, at);
    },
    cancel() {
      done = true;
    }
  };
}
function deny(p, g) {
  sound(p.dimension, `book_${BOOKS.prefix[g.id]}_deny`, p.getHeadLocation(), BOOKS.deny.volume);
}
function installBooks() {
  setPresenter({ select, prepStart, deny });
}

// src/lib/combat.ts
import { EntityDamageCause, system as system3, world as world3 } from "@minecraft/server";
function damage(target, amount, caster, cause = EntityDamageCause.magic) {
  if (!isAlive(target) || amount <= 0) return false;
  try {
    return target.applyDamage(amount, { cause, damagingEntity: caster.isValid ? caster : void 0 });
  } catch {
    return false;
  }
}
function knockback(target, from, h, v2) {
  if (!isAlive(target)) return;
  const d = norm(flat(sub(target.location, from)));
  try {
    target.applyKnockback({ x: d.x * h, z: d.z * h }, v2);
  } catch {
    try {
      target.applyImpulse({ x: d.x * h * 0.4, y: v2 * 0.4, z: d.z * h * 0.4 });
    } catch {
    }
  }
}
function shove(target, dir, h, v2) {
  if (!isAlive(target)) return;
  const d = norm(flat(dir));
  try {
    target.applyKnockback({ x: d.x * h, z: d.z * h }, v2);
  } catch {
  }
}
function heal(e, amount) {
  if (!isAlive(e)) return 0;
  try {
    const h = e.getComponent("minecraft:health");
    if (!h) return 0;
    const before = h.currentValue;
    h.setCurrentValue(Math.min(h.effectiveMax, before + amount));
    return h.currentValue - before;
  } catch {
    return 0;
  }
}
function effect(e, id, ticks, amplifier = 0, particles = false) {
  if (!isAlive(e)) return;
  try {
    e.addEffect(id, Math.max(1, Math.round(ticks)), { amplifier, showParticles: particles });
  } catch {
  }
}
function restrain(scene, target, ticks, anchor) {
  let on = true;
  const hold = anchor ? { ...anchor } : { ...target.location };
  const until = scene.tick + ticks;
  effect(target, "slowness", ticks + 2, 6);
  scene.every(1, () => {
    if (!on || !isAlive(target)) return;
    try {
      target.teleport(hold, { keepVelocity: false });
      target.clearVelocity();
    } catch {
    }
  }, scene.tick, until);
  const release2 = () => {
    if (!on) return;
    on = false;
    try {
      if (target.isValid) target.removeEffect("slowness");
    } catch {
    }
  };
  scene.at(until, release2);
  scene.onEnd(release2);
  return release2;
}
function drag(target, to) {
  if (!isAlive(target)) return;
  try {
    target.teleport(to, { keepVelocity: false });
  } catch {
  }
}
var wards = /* @__PURE__ */ new Set();
function addWard(w) {
  wards.add(w);
  w.scene.onEnd(() => wards.delete(w));
  return w;
}
function removeWard(w) {
  wards.delete(w);
}
var wardHooked = false;
function installWards() {
  if (wardHooked) return;
  wardHooked = true;
  world3.beforeEvents.entityHurt.subscribe((ev) => {
    if (wards.size === 0) return;
    for (const w of wards) {
      if (w.scene.ended || w.broken) {
        continue;
      }
      let ok = false;
      try {
        ok = w.protects(ev.hurtEntity);
      } catch {
        ok = false;
      }
      if (!ok) continue;
      let absorbed = ev.damage * (1 - w.factor);
      if (w.pool !== void 0) {
        absorbed = Math.min(absorbed, w.pool);
        w.pool -= absorbed;
      }
      if (absorbed <= 0) continue;
      ev.damage = Math.max(0, ev.damage - absorbed);
      if (ev.damage < 0.05) ev.cancel = true;
      const attacker = ev.damageSource.damagingEntity;
      const victim = ev.hurtEntity;
      const breakNow = w.pool !== void 0 && w.pool <= 1e-4 && !w.broken;
      if (breakNow) w.broken = true;
      system3.run(() => {
        if (w.scene.ended) return;
        try {
          w.onAbsorb?.(absorbed, attacker, victim);
        } catch (e) {
          console.warn(`[grimoire] ward: ${e}`);
        }
        if (breakNow) {
          try {
            w.onBreak?.();
          } catch (e) {
            console.warn(`[grimoire] ward break: ${e}`);
          }
        }
      });
    }
  });
}
var PROJECTILES = [
  "minecraft:arrow",
  "minecraft:fireball",
  "minecraft:small_fireball",
  "minecraft:shulker_bullet",
  "minecraft:wither_skull",
  "minecraft:wither_skull_dangerous",
  "minecraft:dragon_fireball",
  "minecraft:llama_spit",
  "minecraft:thrown_trident",
  "minecraft:snowball",
  "minecraft:wind_charge_projectile",
  "minecraft:breeze_wind_charge_projectile",
  "minecraft:splash_potion",
  "minecraft:lingering_potion"
];
function dissolveProjectiles(scene, center, radius) {
  const out = [];
  for (const type of PROJECTILES) {
    let found = [];
    try {
      found = scene.dim.getEntities({ location: center, maxDistance: radius, type });
    } catch {
      continue;
    }
    for (const p of found) {
      try {
        const owner = p.getComponent("minecraft:projectile")?.owner;
        if (owner && owner.typeId === "minecraft:player") continue;
        out.push({ ...p.location });
        p.remove();
      } catch {
      }
    }
  }
  return out;
}

// src/lib/tempblocks.ts
import { world as world4 } from "@minecraft/server";
var BARRIER = "minecraft:barrier";
var LIGHT = "minecraft:light_block_15";
var live = /* @__PURE__ */ new Map();
var dirty = false;
var KEY = "grim:tb";
var CHUNK = 3e4;
var k = (d, x, y, z) => `${d}|${x}|${y}|${z}`;
function saveLedger() {
  dirty = false;
  const parts = [];
  for (const e of live.values()) parts.push(`${e.d},${e.x},${e.y},${e.z},${e.t}`);
  const s = parts.join(";");
  let i = 0;
  for (let off = 0; off < s.length || i === 0; off += CHUNK, i++) world4.setDynamicProperty(`${KEY}${i}`, s.slice(off, off + CHUNK));
  for (; i < 8; i++) if (world4.getDynamicProperty(`${KEY}${i}`) !== void 0) world4.setDynamicProperty(`${KEY}${i}`, void 0);
}
function flushLedger() {
  if (dirty) {
    try {
      saveLedger();
    } catch (e) {
      console.warn(`[grimoire] ledger: ${e}`);
    }
  }
}
function restoreLedger() {
  let s = "";
  for (let i = 0; i < 8; i++) {
    const p = world4.getDynamicProperty(`${KEY}${i}`);
    if (typeof p === "string") s += p;
  }
  if (!s) return;
  let pending = 0;
  for (const rec of s.split(";")) {
    const [d, xs, ys, zs, t] = rec.split(",");
    if (!d || t === void 0) continue;
    const e = { d, x: Number(xs), y: Number(ys), z: Number(zs), t };
    if (!clear(e)) {
      live.set(k(e.d, e.x, e.y, e.z), e);
      pending++;
    }
  }
  dirty = true;
  if (pending) console.warn(`[grimoire] ${pending} temporary blocks are in unloaded chunks; they will be removed when loaded.`);
}
function retryOrphans(owned) {
  for (const [key, e] of [...live]) {
    if (owned(key)) continue;
    if (clear(e)) {
      live.delete(key);
      dirty = true;
    }
  }
}
function clear(e) {
  try {
    const b = world4.getDimension(e.d).getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b) return false;
    if (b.typeId === e.t) b.setType("minecraft:air");
    return true;
  } catch {
    return false;
  }
}
var BlockSet = class {
  constructor(scene) {
    this.scene = scene;
    scene.onEnd(() => this.clearAll());
  }
  mine = /* @__PURE__ */ new Set();
  get size() {
    return this.mine.size;
  }
  has(loc) {
    return this.mine.has(k(this.scene.dimId, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z)));
  }
  /** Place a temporary block if the cell is air and not occupied by a player. */
  place(loc, type = BARRIER) {
    const x = Math.floor(loc.x), y = Math.floor(loc.y), z = Math.floor(loc.z);
    const key = k(this.scene.dimId, x, y, z);
    if (this.mine.has(key) || live.has(key) || live.size >= CONFIG.limits.maxTempBlocks) return false;
    const dim = this.scene.dim;
    try {
      const b = dim.getBlock({ x, y, z });
      if (!b || !b.isAir) return false;
      if (type === BARRIER) {
        for (const p of dim.getPlayers({ location: { x: x + 0.5, y, z: z + 0.5 }, maxDistance: 2.5 })) {
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
  remove(loc) {
    const key = k(this.scene.dimId, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
    this.removeKey(key);
  }
  removeKey(key) {
    const e = live.get(key);
    if (!e || !this.mine.has(key)) return;
    if (clear(e)) live.delete(key);
    this.mine.delete(key);
    dirty = true;
  }
  /** Vertical wall segment of barriers: column at (x, z) from y to y+h-1. */
  column(x, y, z, h, type = BARRIER) {
    let n = 0;
    for (let i = 0; i < h; i++) if (this.place({ x, y: y + i, z }, type)) n++;
    return n;
  }
  removeColumn(x, y, z, h) {
    for (let i = 0; i < h; i++) this.remove({ x, y: y + i, z });
  }
  clearAll() {
    for (const key of [...this.mine]) this.removeKey(key);
  }
  owns(key) {
    return this.mine.has(key);
  }
};
var sets = /* @__PURE__ */ new Set();
function blocksFor(scene) {
  const s = new BlockSet(scene);
  sets.add(s);
  scene.onEnd(() => sets.delete(s));
  return s;
}
function anySetOwns(key) {
  for (const s of sets) if (s.owns(key)) return true;
  return false;
}

// src/config/dw01.ts
var DW01 = {
  /** Radius around the focus point in which enemies are judged. */
  radius: 14,
  /** Maximum enemies struck by each chant. */
  maxTargets: 6,
  /** Damage of the first, second and third judgment column. */
  chantDamage: [8, 9, 11],
  /** Blast radius of a judgment column (blocks). */
  columnRadius: 2.6,
  /** Extra damage for an enemy struck by all three judgments. */
  verdictBonus: 16,
  verdictRadius: 3.4,
  verdictKnockback: 1.6,
  /** Height of the Seraphim above the battlefield and how far beyond the focus it hovers. */
  hoverHeight: 8,
  hoverBack: 6,
  /** Ticks from a chant gesture to its columns landing (the warning window). */
  warnTicks: 16
};

// src/spells/dw01_seraphic_litany.ts
var S = { hidden: 0, arrive: 1, veiled: 2, unfurl: 3, open: 4, chant1: 5, chant2: 6, chant3: 7, verdict: 8, depart: 9 };
var dw01_seraphic_litany_default = defineSpell("dw01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 12);
  const hover = up(add(center, mul(aim.forward, DW01.hoverBack)), DW01.hoverHeight);
  const faceCaster = yawOf(sub(caster.location, hover));
  const lights = blocksFor(scene);
  const hits = /* @__PURE__ */ new Map();
  const ground = scene.spawn("dw_circle", center, { size: DW01.radius / 2.6, state: 1 });
  const sky = scene.spawn("dw_circle", up(hover, 13), { size: 3.2, state: 1 });
  sound(dim, "dw_circle", center, 1);
  scene.at(8, () => {
    ground.state(2);
    sky.state(2);
  });
  const seraph = scene.spawn("seraph", hover, { yaw: faceCaster, state: S.arrive });
  sound(dim, "dw_seraph_arrive", hover, 1.2);
  scene.every(4, () => particle(dim, "dw_mote", up(hover, 4)), 0, secs(8));
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), DW01.radius * 0.5, 6));
  lights.place(up(center, 2), LIGHT);
  const tUnfurl = secs(1.5);
  scene.at(tUnfurl, () => {
    seraph.state(S.unfurl);
    sound(dim, "dw_unfurl", hover, 1);
    burst(dim, "dw_feather", up(hover, 5), 5, 8);
  });
  const chantAt = [tUnfurl + secs(1.3), tUnfurl + secs(2.7), tUnfurl + secs(4.1)];
  const gestureLead = [18, 19, 19];
  chantAt.forEach((t0, i) => {
    scene.at(t0, () => {
      seraph.state(S.chant1 + i).skin(1);
      sound(dim, `dw_chant${i + 1}`, hover, 1.3);
      ring(dim, "dw_glyph_rise", up(hover, 4), 5, 8, i * 20);
    });
    scene.at(t0 + gestureLead[i] - DW01.warnTicks + 8, () => judge(i));
  });
  function pickTargets() {
    const found = hostiles(dim, center, DW01.radius, caster, DW01.maxTargets);
    if (found.length) return found.map((e) => ({ loc: groundBelow(dim, e.location), e }));
    return [0, 1, 2].map((k2) => ({ loc: polar(center, 4, k2 * 120 + 30) }));
  }
  function judge(i) {
    for (const t of pickTargets()) {
      const size = DW01.columnRadius / 1.3 * (1 + i * 0.12);
      const warn = scene.spawn("telegraph", t.loc, { kind: 0, size: DW01.columnRadius * (1 + i * 0.1), state: 1 });
      let at = t.loc;
      scene.every(1, () => {
        if (t.e && isAlive(t.e)) {
          at = groundBelow(dim, t.e.location);
          warn.move(at);
        }
      }, scene.tick, scene.tick + DW01.warnTicks - 4);
      scene.after(DW01.warnTicks - 6, () => {
        const col = scene.spawn("dw_column", at, { kind: i === 1 ? 1 : 0, size, state: 1 });
        sound(dim, "dw_column", at, 1, 0.95 + i * 0.08);
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      });
      scene.after(DW01.warnTicks, () => {
        warn.state(3);
        scene.after(8, () => scene.despawn(warn));
        strike(at, i);
      });
    }
  }
  function strike(at, i) {
    particle(dim, "dw_ring", up(at, 0.2));
    particle(dim, "dw_pillar_burst", up(at, 0.3));
    particle(dim, "dw_spark", up(at, 1));
    particle(dim, "fx_flash", up(at, 1.5));
    for (const e of hostiles(dim, at, DW01.columnRadius * (1 + i * 0.1), caster)) {
      let h = hits.get(e.id);
      if (!h) {
        h = { e, n: 0, last: -1 };
        hits.set(e.id, h);
      }
      if (h.last >= i) continue;
      if (!damage(e, DW01.chantDamage[i], caster)) continue;
      h.last = i;
      h.n++;
      if (isAlive(e)) {
        if (!h.mark || !h.mark.valid) {
          h.mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1 });
          scene.follow(h.mark, e, 2.4);
          sound(dim, "dw_mark", e.location, 0.7, 1 + i * 0.12);
        }
        h.mark.skin(Math.min(2, h.n - 1));
      }
    }
  }
  const tVerdict = chantAt[2] + secs(1.75);
  scene.at(tVerdict, () => {
    seraph.state(S.verdict);
    const judged = [...hits.values()].filter((h) => h.n >= 3 && isAlive(h.e));
    sound(dim, "dw_verdict", judged.length ? judged[0].e.location : center, 1.4);
    scene.after(9, () => {
      const spots = judged.length ? judged.map((h) => groundBelow(dim, h.e.location)) : [center];
      const sentenced = /* @__PURE__ */ new Set();
      for (const at of spots) {
        const col = scene.spawn("dw_column", at, { kind: 2, size: 2.2, state: 1 });
        scene.after(10, () => col.state(2));
        scene.after(24, () => col.state(3));
        scene.after(38, () => scene.despawn(col));
        scene.after(6, () => {
          particle(dim, "dw_ring", up(at, 0.2));
          particle(dim, "fx_shock", up(at, 0.3));
          burst(dim, "dw_spark", up(at, 1.2), 1.5, 3);
          ring(dim, "dw_glyph_fall", up(at, 6), 2.5, 6);
          for (const e of hostiles(dim, at, DW01.verdictRadius, caster)) {
            const h = hits.get(e.id);
            if (h && h.n >= 3 && !sentenced.has(e.id)) {
              sentenced.add(e.id);
              damage(e, DW01.verdictBonus, caster);
            }
            knockback(e, at, DW01.verdictKnockback, 0.5);
          }
        });
      }
      for (const h of hits.values()) if (h.mark?.valid) {
        h.mark.state(3);
        const m = h.mark;
        scene.after(8, () => scene.despawn(m));
      }
    });
  });
  const tDepart = tVerdict + secs(1.5);
  scene.at(tDepart, () => {
    seraph.state(S.depart).skin(0);
    ground.state(3);
    sky.state(3);
    sound(dim, "dw_depart", hover, 1);
    ring(dim, "dw_feather", up(hover, 5), 4, 8);
  });
  scene.at(tDepart + secs(1.2), () => burst(dim, "dw_glyph_rise", up(hover, 8), 3, 8));
  scene.endAt(tDepart + secs(1.7));
});

// src/config/dw02.ts
var DW02 = {
  // ---- placement
  /** How far ahead of the caster (along the aim) the Cherubim manifests, in blocks. */
  standForward: 4.5,
  /** Sideways offset to the caster's left so the caster sees the witness in three-quarter view. */
  standSide: 5.5,
  /** Snap distance used to pick the fight centre around the aim point. */
  focusSnap: 12,
  // ---- FIRST - HUMAN WITNESS: sacred glyphs mark enemies
  /** Radius around the fight centre searched for enemies to mark. */
  markRadius: 16,
  /** Maximum enemies marked by the human witness. */
  maxMarks: 6,
  /** Small searing damage as a glyph is written onto an enemy. */
  markDamage: 2,
  /** Damage multiplier marked enemies suffer from the ox retaliation and the lion roar. */
  markBonus: 1.35,
  // ---- SECOND - OX WITNESS: wing-wall ward, absorb and retaliate
  /** Ticks the wing wall (real damage ward) holds (3.5 s). */
  wardTicks: 70,
  /** Allied players within this radius of the Cherubim are shielded (the caster always is). */
  wardRadius: 10,
  /** Total damage the wall can absorb before it cracks. */
  wardPool: 40,
  /** Fraction of incoming damage the wall stops (0 = all of it gets through, 1 = immune). */
  wardStrength: 1,
  /** Absorbed damage without a known attacker (falls, fire...) still charges the retaliation at this share. */
  envAbsorbShare: 0.5,
  /** Each hostile projectile dissolved by the wall adds this much to the stored retaliation. */
  projectileCharge: 2,
  /** Retaliatory shockwave: base damage + absorbed * scale, capped. */
  retaliateBase: 8,
  retaliateScale: 1,
  retaliateMax: 32,
  /** Shockwave radius around the Cherubim and its knockback. */
  retaliateRadius: 8,
  retaliateKnock: 1.8,
  retaliateLift: 0.5,
  // ---- THIRD - LION WITNESS: the sacred roar
  /** Damage of the roar (once per enemy). */
  roarDamage: 10,
  /** Reach of the roar cone and its half-angle in degrees. */
  roarRange: 16,
  roarHalfAngle: 55,
  /** Everything this close to the Cherubim is struck by the roar regardless of direction. */
  roarNear: 5,
  /** Knockback of the roar (horizontal / vertical). */
  roarKnock: 2.4,
  roarLift: 0.6,
  /** Extra push from the second and third ring of letters (no damage). */
  roarEchoPush: 0.8,
  /** Speed of the rings of letters (blocks per tick); the damage front travels with them. */
  roarSpeed: 0.8,
  /** Ticks between the three rings. */
  roarRingGap: 4,
  /** Height and forward offset of the lion's mouth relative to the Cherubim origin (blocks). */
  mouthHeight: 9.5,
  mouthForward: 1.8,
  // ---- FOURTH - EAGLE WITNESS: feather-blades from above
  /** Damage of one feather-blade. */
  bladeDamage: 14,
  /** Multiplier against marked enemies. */
  bladeMarkBonus: 1.5,
  /** Impact radius of a blade and its knockback. */
  bladeRadius: 2.2,
  bladeKnock: 0.6,
  /** Height above the target a blade forms at. */
  bladeHeight: 10,
  /** Ticks of telegraph (the warning sigil fills) before a blade dives. */
  bladeWarn: 20,
  /** Ticks a blade takes to fall from its height to the ground. */
  diveTicks: 5,
  /** Blades per wave (two waves). */
  bladesPerWave: 5,
  /** Radius around the fight centre in which the second wave may pick unmarked enemies. */
  bladeSearch: 16
};

// src/spells/dw02_cherubic_testament.ts
var S2 = { hidden: 0, arrive: 1, idle: 2, human: 3, ox: 4, oxRetaliate: 5, lion: 6, eagle: 7, verdict: 8, depart: 9 };
var BLADE = { hidden: 0, form: 1, aim: 2, dive: 3, shatter: 4 };
var MARK = { appear: 1, hold: 2, burst: 3 };
var T = {
  arrive: 1.6,
  humanCast: 1.05,
  human: 1.6,
  oxLock: 0.75,
  ox: 1,
  retBlast: 0.3,
  retaliate: 1,
  lionRoar: 0.95,
  lion: 1.8,
  eagleThrust: [1.6, 2.5],
  eagle: 2.8,
  depart: 1.8,
  bladeForm: 0.6,
  bladeShatter: 0.5,
  roarLife: 1
};
var dw02_cherubic_testament_default = defineSpell("dw02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, DW02.focusSnap);
  const left = mul(right(aim.forward), -1);
  const anchor = groundBelow(dim, add(add(caster.location, mul(aim.forward, DW02.standForward)), mul(left, DW02.standSide)));
  const toward = flat(sub(center, anchor));
  const fwd = Math.hypot(toward.x, toward.z) > 2 ? norm(toward) : aim.forward;
  const yaw = yawOf(fwd);
  const side = right(fwd);
  const lights = blocksFor(scene);
  const witnessed = /* @__PURE__ */ new Map();
  const phantoms = [];
  const circle = scene.spawn("dw_circle", anchor, { size: 2.4, state: 1 });
  const cherub = scene.spawn("cherub", anchor, { yaw, state: S2.arrive });
  sound(dim, "dw_cherub_arrive", anchor, 1.3);
  sound(dim, "dw_circle", anchor, 0.8);
  ring(dim, "dw_glyph_rise", up(anchor, 0.5), 3.5, 8);
  scene.at(8, () => circle.state(2));
  scene.at(14, () => {
    particle(dim, "fx_flash", up(anchor, 7));
    burst(dim, "dw_glyph_rise", up(anchor, 5), 3, 8);
  });
  lights.place(up(anchor, 3), LIGHT);
  const censer = add(up(anchor, 7.6), mul(fwd, -1.5));
  scene.every(6, () => particle(dim, "dw_cherub_ember", censer), 20, 9999);
  const tHuman = secs(T.arrive) - 2;
  const tOx = tHuman + secs(T.human) - 2;
  const tWard = tOx + secs(T.oxLock);
  const tRet = tWard + DW02.wardTicks;
  const tLion = tRet + secs(T.retaliate) - 2;
  const tRoar2 = tLion + secs(T.lionRoar);
  const tEagle = tRoar2 + 15;
  const dives = T.eagleThrust.map((s) => tEagle + secs(s));
  const tDepart = dives[1] + DW02.diveTicks + 8;
  function turn() {
    sound(dim, "dw_cherub_turn", up(anchor, 10), 1);
  }
  function boost(e, base, bonus) {
    return witnessed.get(e.id)?.mark ? base * bonus : base;
  }
  scene.at(tHuman, () => {
    cherub.state(S2.human);
    sound(dim, "dw_cherub_human", up(anchor, 10), 1.3);
  });
  const hand = add(add(up(anchor, 12.5), mul(side, 1.8)), mul(fwd, 0.8));
  let markTargets = [];
  scene.at(tHuman + 6, () => {
    markTargets = hostiles(dim, center, DW02.markRadius, caster, DW02.maxMarks);
  });
  scene.every(3, (el) => {
    particle(dim, "dw_cherub_glyph", hand);
    const p = Math.min(1, el / 14);
    for (const e of markTargets) {
      if (!isAlive(e)) continue;
      const to = up(e.location, 1.6);
      particle(dim, "dw_cherub_glyph", lerp(hand, to, p));
      if (p > 0.3) particle(dim, "dw_cherub_glyph", lerp(hand, to, p - 0.25));
    }
  }, tHuman + 7, tHuman + secs(T.humanCast));
  scene.at(tHuman + secs(T.humanCast), () => {
    const found = markTargets.filter((e) => isAlive(e));
    for (const e of found) {
      const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK.appear, skin: 0 });
      scene.follow(mark, e, 2.4);
      scene.after(6, () => mark.state(MARK.hold));
      witnessed.set(e.id, { e, mark, n: 0 });
      damage(e, DW02.markDamage, caster);
      particle(dim, "dw_halo", up(e.location, 1.2));
      sound(dim, "dw_cherub_glyph", e.location, 0.8, 1 + witnessed.size * 0.05);
    }
    if (!found.length) {
      for (let k2 = 0; k2 < 3; k2++) {
        const at = groundBelow(dim, polar(center, 3.5, k2 * 120 + yaw));
        phantoms.push(scene.spawn("dw_mark", up(at, 1.4), { state: MARK.appear, skin: 0 }));
        sound(dim, "dw_cherub_glyph", at, 0.7, 0.9 + k2 * 0.1);
      }
      scene.after(6, () => phantoms.forEach((m) => m.state(MARK.hold)));
    }
    line(dim, "dw_cherub_glyph", hand, up(center, 2), 6);
  });
  let stored = 0;
  scene.at(tOx, () => {
    cherub.state(S2.ox);
    turn();
    sound(dim, "dw_cherub_ox", up(anchor, 9), 1.3);
  });
  scene.at(tWard, () => {
    sound(dim, "dw_cherub_shield", add(up(anchor, 5), mul(fwd, 2)), 1.2);
    burst(dim, "dw_cherub_feather", add(up(anchor, 6), mul(fwd, 2.5)), 2.5, 5);
    particle(dim, "dw_cherub_shield", up(caster.location, 1));
    const ward = addWard({
      scene,
      factor: 1 - DW02.wardStrength,
      pool: DW02.wardPool,
      protects: (e) => e.id === caster.id || e.typeId === "minecraft:player" && !CONFIG.targeting.pvp && distXZ(e.location, anchor) <= DW02.wardRadius,
      onAbsorb: (amount, attacker, victim) => {
        stored += attacker ? amount : amount * DW02.envAbsorbShare;
        if (victim.isValid) particle(dim, "dw_cherub_absorb", up(victim.location, 1));
        sound(dim, "dw_cherub_absorb", victim.isValid ? victim.location : anchor, 0.9);
      },
      onBreak: () => {
        sound(dim, "dw_cherub_retaliate", up(anchor, 4), 0.6, 1.3);
        burst(dim, "dw_cherub_shatter", add(up(anchor, 5), mul(fwd, 2.5)), 1.5, 3);
      }
    });
    scene.at(tRet, () => removeWard(ward));
  });
  scene.every(4, () => {
    const gone = [...dissolveProjectiles(scene, anchor, DW02.wardRadius), ...dissolveProjectiles(scene, caster.location, 4)];
    for (const p of gone) {
      stored += DW02.projectileCharge;
      particle(dim, "dw_cherub_absorb", p);
    }
  }, tWard, tRet);
  scene.every(8, (el) => {
    const a = el * 23 % 120 - 60;
    particle(dim, "dw_cherub_shield", add(up(anchor, 4 + el % 3), mul(fromYaw(yaw + a), 3)));
    if (caster.isValid) particle(dim, "dw_cherub_shield", up(caster.location, 1));
  }, tWard, tRet);
  let quakeSigil;
  scene.at(tRet - 40, () => {
    quakeSigil = scene.spawn("telegraph", anchor, { kind: 0, size: DW02.retaliateRadius, state: 4 });
  });
  scene.at(tRet, () => {
    cherub.state(S2.oxRetaliate);
  });
  scene.at(tRet + secs(T.retBlast), () => {
    const dmg = Math.min(DW02.retaliateMax, DW02.retaliateBase + stored * DW02.retaliateScale);
    sound(dim, "dw_cherub_retaliate", up(anchor, 3), 1.4, stored > 0 ? 0.9 : 1);
    particle(dim, "dw_cherub_quake", up(anchor, 0.2));
    particle(dim, "fx_shock", up(anchor, 0.4));
    particle(dim, "dw_cherub_dust", up(anchor, 0.3));
    ring(dim, "dw_cherub_feather", up(anchor, 5), 4, 6);
    if (quakeSigil) {
      quakeSigil.state(3);
      const q = quakeSigil;
      scene.after(8, () => scene.despawn(q));
    }
    for (const e of hostiles(dim, anchor, DW02.retaliateRadius, caster)) {
      damage(e, boost(e, dmg, DW02.markBonus), caster);
      knockback(e, anchor, DW02.retaliateKnock, DW02.retaliateLift);
    }
  });
  const mouth = add(up(anchor, DW02.mouthHeight), mul(fwd, DW02.mouthForward));
  const cone = [];
  scene.at(tLion, () => {
    cherub.state(S2.lion);
    turn();
    for (const d of [5, 10]) cone.push(scene.spawn("telegraph", groundBelow(dim, add(anchor, mul(fwd, d))), { kind: 0, size: 2 + d * 0.25, state: 1 }));
  });
  scene.at(tRoar2 - 4, () => sound(dim, "dw_cherub_lion", mouth, 1.6));
  const roared = /* @__PURE__ */ new Set();
  function inCone(e) {
    const v2 = flat(sub(e.location, anchor));
    const d = Math.hypot(v2.x, v2.z);
    const along = dot(v2, fwd);
    if (d > DW02.roarRange || d < 0.01) return void 0;
    if (along / d < Math.cos(DW02.roarHalfAngle * Math.PI / 180)) return void 0;
    return along;
  }
  function roarHit(e) {
    if (roared.has(e.id)) return;
    roared.add(e.id);
    damage(e, boost(e, DW02.roarDamage, DW02.markBonus), caster);
    shove(e, norm(add(fwd, mul(norm(flat(sub(e.location, anchor))), 0.6))), DW02.roarKnock, DW02.roarLift);
    particle(dim, "dw_spark", up(e.location, 1));
  }
  scene.at(tRoar2, () => {
    particle(dim, "dw_cherub_breath", mouth);
    particle(dim, "dw_cherub_roar", mouth);
    particle(dim, "dw_cherub_dust", anchor);
    cone.forEach((t) => t.state(3));
    scene.after(8, () => cone.forEach((t) => scene.despawn(t)));
    for (const e of hostiles(dim, anchor, DW02.roarNear, caster)) {
      roarHit(e);
      knockback(e, anchor, DW02.roarKnock, DW02.roarLift);
    }
  });
  const travel = Math.round(DW02.roarRange / DW02.roarSpeed);
  for (let k2 = 0; k2 < 3; k2++) {
    const t0 = tRoar2 + k2 * DW02.roarRingGap;
    const end = groundBelow(dim, add(anchor, mul(fwd, DW02.roarRange)));
    let ringActor;
    scene.at(t0, () => {
      ringActor = scene.spawn("dw_cherub_roar", mouth, { yaw, state: 1 });
      sound(dim, "dw_cherub_ring", mouth, 0.9, 0.9 + k2 * 0.1);
    });
    scene.span(t0, t0 + travel, (p, el) => {
      const pos = lerp(mouth, up(end, 2.5), p);
      ringActor?.move(pos, yaw);
      if (el % 3 === 0) particle(dim, "dw_cherub_roar", pos);
      const front = DW02.roarSpeed * (el + 1), back = front - DW02.roarSpeed - 1.2;
      for (const e of hostiles(dim, anchor, DW02.roarRange + 1, caster)) {
        const along = inCone(e);
        if (along === void 0 || along > front || along < back) continue;
        if (k2 === 0) roarHit(e);
        else shove(e, fwd, DW02.roarEchoPush, 0.2);
      }
    });
    scene.at(t0 + travel, () => {
      if (ringActor) {
        ring(dim, "dw_glyph_rise", ringActor.loc, 2.5, 6);
        scene.despawn(ringActor);
      }
    });
  }
  scene.at(tEagle, () => {
    cherub.state(S2.eagle).skin(1);
    turn();
    burst(dim, "dw_cherub_feather", up(anchor, 9), 4, 6);
  });
  scene.at(tEagle + 10, () => sound(dim, "dw_cherub_eagle", up(anchor, 11), 1.5));
  function waveTargets(wave) {
    const out = [];
    const used = /* @__PURE__ */ new Set();
    for (const w of witnessed.values()) {
      if (out.length >= DW02.bladesPerWave) break;
      if (isAlive(w.e)) {
        out.push({ e: w.e, at: groundBelow(dim, w.e.location) });
        used.add(w.e.id);
      }
    }
    if (wave === 1 || !out.length) {
      for (const e of hostiles(dim, center, DW02.bladeSearch, caster)) {
        if (out.length >= DW02.bladesPerWave) break;
        if (!used.has(e.id)) out.push({ e, at: groundBelow(dim, e.location) });
      }
    }
    if (!out.length) {
      const spots = phantoms.length ? phantoms.map((m) => groundBelow(dim, m.loc)) : [0, 1, 2].map((k2) => polar(center, 3, k2 * 120));
      spots.slice(0, wave === 0 ? 3 : 2).forEach((at, k2) => out.push({ at: wave ? polar(at, 1.5, k2 * 90 + 45) : at }));
    }
    return out;
  }
  function blade(target, diveAt, idx) {
    let at = target.at;
    const bladeYaw = yaw + idx * 47;
    const b = scene.spawn("dw_cherub_blade", up(at, DW02.bladeHeight), { yaw: bladeYaw, state: BLADE.form });
    const sigil = scene.spawn("telegraph", at, { kind: 0, size: DW02.bladeRadius, state: 1 });
    sound(dim, "dw_cherub_blade", up(at, DW02.bladeHeight), 0.9, 0.95 + idx * 0.04);
    particle(dim, "dw_cherub_glyph", up(at, DW02.bladeHeight));
    scene.after(secs(T.bladeForm), () => b.state(BLADE.aim));
    scene.every(1, () => {
      if (target.e && isAlive(target.e)) {
        at = groundBelow(dim, target.e.location);
        sigil.move(at);
      }
      b.move(up(at, DW02.bladeHeight), bladeYaw);
    }, scene.tick + 1, diveAt);
    scene.at(diveAt, () => {
      b.state(BLADE.dive);
      sound(dim, "dw_cherub_dive", up(at, DW02.bladeHeight * 0.5), 1);
    });
    scene.span(diveAt, diveAt + DW02.diveTicks, (p) => {
      const pos = up(at, DW02.bladeHeight * (1 - easeIn(p)));
      b.move(pos, bladeYaw);
      particle(dim, "dw_cherub_trail", up(pos, 1.5));
    });
    scene.at(diveAt + DW02.diveTicks, () => {
      b.move(at, bladeYaw).state(BLADE.shatter);
      sigil.state(3);
      sound(dim, "dw_cherub_impact", at, 1.1);
      particle(dim, "dw_cherub_shatter", up(at, 0.6));
      particle(dim, "dw_ring", up(at, 0.2));
      particle(dim, "fx_flash", up(at, 1));
      for (const e of hostiles(dim, at, DW02.bladeRadius, caster)) {
        const w = witnessed.get(e.id);
        if (!damage(e, boost(e, DW02.bladeDamage, DW02.bladeMarkBonus), caster)) continue;
        knockback(e, at, DW02.bladeKnock, 0.3);
        if (w?.mark?.valid) {
          w.n++;
          w.mark.skin(Math.min(2, w.n));
        }
      }
      scene.after(secs(T.bladeShatter) + 2, () => {
        scene.despawn(b);
        scene.despawn(sigil);
      });
    });
  }
  dives.forEach((diveAt, wave) => {
    scene.at(diveAt - DW02.bladeWarn, () => waveTargets(wave).forEach((t, i) => blade(t, diveAt, i + wave * 3)));
  });
  scene.at(tDepart, () => {
    cherub.state(S2.depart).skin(0);
    circle.state(3);
    sound(dim, "dw_cherub_depart", up(anchor, 8), 1.2);
    ring(dim, "dw_glyph_rise", up(anchor, 2), 3, 8);
    for (const w of witnessed.values()) if (w.mark?.valid) {
      w.mark.state(MARK.burst);
    }
    phantoms.forEach((m) => m.state(MARK.burst));
  });
  scene.at(tDepart + 8, () => {
    for (const w of witnessed.values()) if (w.mark) scene.despawn(w.mark);
    phantoms.forEach((m) => scene.despawn(m));
  });
  scene.at(tDepart + 24, () => {
    burst(dim, "dw_glyph_rise", up(anchor, 12), 3, 8);
    scene.despawn(circle);
  });
  scene.endAt(tDepart + secs(T.depart) + 2);
});

// src/config/dw03.ts
var DW03 = {
  // ---- survey
  /** Radius of the rotating-sector scan around the focus point (blocks). */
  surveyRadius: 18,
  /** Ticks for the scan beam to complete one full revolution. */
  scanTicks: 36,
  /** Scan pings per revolution (one per sector). */
  scanSectors: 6,
  /** Maximum enemies the Ophanim can mark. */
  maxMarks: 8,
  /** Height of the wheel centre above the focus while it arrives and surveys. */
  hoverHeight: 9,
  // ---- sweeping passes
  /** Number of geometric passes (polygon, star, figure-eight, polygon...). */
  passes: 3,
  /** Ticks of route telegraph + repositioning before each pass (the warning window). */
  lockTicks: 12,
  /** Ticks the wheel needs to run one whole route. */
  passTicks: 36,
  /** Height of the wheel centre above the ground during a pass: the rim grazes the ground. */
  sweepAltitude: 5.6,
  /** Half-length along the path of the rim's ground-contact chord (blocks). */
  rimChord: 4.2,
  /** Lateral reach of the rim from the wheel plane (blocks, enemy hitbox slack included). */
  rimHalfWidth: 2,
  /** Height above the ground the rim reaches (blocks). */
  rimHeight: 3.2,
  /** Route size limits around the marked enemies (blocks). */
  routeMinRadius: 5,
  routeMaxRadius: 11,
  /** Route radius used when nothing is marked. */
  noTargetRadius: 6,
  /** Rim damage per pass to unmarked / marked enemies (one hit per enemy per pass). */
  damage: 6,
  markedDamage: 10,
  /** Sideways knockback away from the wheel plane, and lift. */
  knockback: 0.9,
  lift: 0.35,
  // ---- verdict
  /** Final judgment damage on every surviving marked enemy. */
  verdictDamage: 12,
  /** Radius of the verdict shock around the wheel (pushes unmarked enemies). */
  verdictPushRadius: 5,
  verdictKnockback: 1.2
};

// src/spells/dw03_ophanim.ts
var S3 = { hidden: 0, arrive: 1, survey: 2, lock: 3, sweep: 4, verdict: 5, depart: 6 };
var A = { arrive: 2, lock: 0.6, verdict: 1.1, depart: 1.8 };
var VERDICT_HIT = secs(0.55);
var SKIN_JUDGING = 1;
var dw03_ophanim_default = defineSpell("dw03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 12);
  const hover = up(center, DW03.hoverHeight);
  const faceCaster = yawOf(sub(caster.location, hover));
  const marks = /* @__PURE__ */ new Map();
  const circle = scene.spawn("dw_circle", center, { size: 4.5, state: 1 });
  scene.at(16, () => circle.state(2));
  const oph = scene.spawn("ophanim", hover, { yaw: faceCaster, state: S3.arrive, skin: 0 });
  let pos = hover;
  let yaw = faceCaster;
  sound(dim, "dw_ophan_arrive", hover, 1.3);
  sound(dim, "dw_circle", center, 0.9);
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), 4, 6));
  scene.at(secs(1.62), () => burst(dim, "dw_ophan_impact", hover, 3, 4));
  const tSurvey = secs(A.arrive);
  const tScan = tSurvey + 4;
  const tScanEnd = tScan + DW03.scanTicks;
  const scan0 = (aim.yaw + 90) % 360;
  scene.at(tSurvey, () => {
    oph.state(S3.survey);
    sound(dim, "dw_ophan_hum", hover, 0.8, 0.6);
    particle(dim, "dw_ophan_ping", up(center, 0.2));
  });
  scene.every(30, () => sound(dim, "dw_ophan_hum", hover, 0.7, 0.62), tSurvey + 30, tScanEnd + 4);
  let prevAngle = scan0;
  scene.every(1, (e) => {
    const ang = scan0 + 360 * (e + 1) / DW03.scanTicks;
    const dir = v(Math.cos(ang * Math.PI / 180), 0, Math.sin(ang * Math.PI / 180));
    const tip = add(center, mul(dir, DW03.surveyRadius));
    line(dim, "dw_ophan_scan", up(add(center, mul(dir, 2)), 0.25), up(tip, 0.25), 7);
    if (e % 3 === 0) line(dim, "dw_ophan_scan", up(hover, -1), up(tip, 0.4), 4);
    const per = Math.max(1, Math.round(DW03.scanTicks / DW03.scanSectors));
    if (e % per === 0) {
      sound(dim, "dw_ophan_scan", center, 0.9, 0.9 + e / DW03.scanTicks * 0.3);
      particle(dim, "dw_ophan_ping", up(center, 0.25));
    }
    for (const h of hostiles(dim, center, DW03.surveyRadius, caster)) {
      const a = Math.atan2(h.location.z - center.z, h.location.x - center.x) * 180 / Math.PI;
      if (swept(a, prevAngle, ang)) markEnemy(h);
    }
    prevAngle = ang;
  }, tScan, tScanEnd);
  scene.at(tScanEnd, () => {
    for (const h of hostiles(dim, center, DW03.surveyRadius, caster)) markEnemy(h);
  });
  function swept(a, from, to) {
    const d = ((a - from) % 360 + 360) % 360;
    return d <= to - from;
  }
  function markEnemy(e) {
    if (marks.has(e.id) || marks.size >= DW03.maxMarks || !isAlive(e)) return;
    const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1, skin: 0 });
    scene.follow(mark, e, 2.4);
    scene.after(6, () => mark.state(2));
    marks.set(e.id, { e, mark, hits: 0 });
    sound(dim, "dw_ophan_mark", e.location, 0.8, 1 + marks.size * 0.04);
    particle(dim, "dw_ophan_eye", up(e.location, 3.4));
    particle(dim, "dw_ophan_ping", up(e.location, 0.2));
    line(dim, "dw_ophan_scan", up(hover, -1), up(e.location, 1.2), 6);
  }
  function liveMarks() {
    return [...marks.values()].filter((m) => isAlive(m.e));
  }
  let lastCentre = center;
  function routeFor(k2) {
    const live2 = liveMarks();
    let P6 = live2.map((m) => flat(m.e.location));
    const c0 = P6.length ? mul(P6.reduce((s, p) => add(s, p), v(0, 0, 0)), 1 / P6.length) : flat(lastCentre);
    const c = v(c0.x, 0, c0.z);
    lastCentre = v(c.x, center.y, c.z);
    if (!P6.length) P6 = [0, 1, 2, 3, 4].map((i) => polar(c, DW03.noTargetRadius, aim.yaw + 90 + i * 72));
    let far = P6[0];
    for (const p of P6) if (distXZ(p, c) > distXZ(far, c)) far = p;
    const R2 = clamp(distXZ(far, c) + 1.5, DW03.routeMinRadius, DW03.routeMaxRadius);
    const u = distXZ(far, c) > 0.5 ? norm(flat(sub(far, c))) : fromYaw(aim.yaw);
    const a0 = Math.atan2(u.z, u.x) * 180 / Math.PI;
    let corners;
    let name;
    const kind = k2 % 3;
    if (kind === 0) {
      name = "polygon";
      if (P6.length >= 3) {
        corners = [...P6].sort((p, q) => Math.atan2(p.z - c.z, p.x - c.x) - Math.atan2(q.z - c.z, q.x - c.x));
      } else if (P6.length === 2) {
        const mid = lerp(P6[0], P6[1], 0.5);
        const side = right(sub(P6[1], P6[0]));
        corners = [P6[0], add(mid, mul(side, R2 * 0.9)), P6[1], add(mid, mul(side, -R2 * 0.9))];
      } else {
        const q = sub(P6[0], mul(u, R2));
        corners = [0, 1, 2].map((i) => polar(q, R2, a0 + i * 120));
      }
      corners.push(corners[0]);
    } else if (kind === 1) {
      name = "star";
      corners = [0, 2, 4, 1, 3, 0].map((i) => polar(c, R2, a0 + i * 72));
    } else {
      name = "figure-eight";
      const w = right(u);
      corners = [];
      for (let i = 0; i <= 20; i++) {
        const t = i / 20 * Math.PI * 2;
        corners.push(add(c, add(mul(u, R2 * Math.sin(t)), mul(w, R2 * 0.8 * Math.sin(t) * Math.cos(t)))));
      }
    }
    const pts = corners.map((p) => up(groundBelow(dim, v(p.x, center.y + 4, p.z), 24), DW03.sweepAltitude));
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1], pts[i]));
    const keys = kind === 2 ? [0, 5, 10, 15].map((i) => pts[i]) : pts.slice(0, -1);
    return { pts, corners: keys.map((p) => up(p, -DW03.sweepAltitude)), cum, total: Math.max(cum[cum.length - 1], 1), name };
  }
  function pointAt(r, s) {
    const d = clamp(s, 0, r.total);
    let i = 1;
    while (i < r.pts.length - 1 && r.cum[i] < d) i++;
    const seg = r.cum[i] - r.cum[i - 1];
    const f = seg > 1e-6 ? (d - r.cum[i - 1]) / seg : 0;
    return { p: lerp(r.pts[i - 1], r.pts[i], f), dir: sub(r.pts[i], r.pts[i - 1]) };
  }
  const tPass0 = tScanEnd + 4;
  const passLen = DW03.lockTicks + DW03.passTicks;
  for (let k2 = 0; k2 < DW03.passes; k2++) {
    const tLock = tPass0 + k2 * passLen;
    const tRun = tLock + DW03.lockTicks;
    let route;
    let tele = [];
    scene.at(tLock, () => {
      route = routeFor(k2);
      const r = route;
      oph.state(S3.lock).skin(SKIN_JUDGING);
      sound(dim, "dw_ophan_lock", pos, 1.1, 1 + k2 * 0.06);
      if (k2 === 0) sound(dim, "dw_ophan_eyes", pos, 0.9, 0.8);
      tele = r.corners.map((p) => scene.spawn("telegraph", p, { kind: 0, size: DW03.rimHalfWidth + 0.6, state: 1 }));
      const from = pos;
      const to = r.pts[0];
      const ctrl = up(lerp(from, to, 0.5), 4);
      const yawTo = yawOf(sub(r.pts[1], r.pts[0]));
      scene.span(tLock, tRun, (p) => {
        pos = bezier(from, ctrl, to, p);
        yaw += angleDelta(yaw, yawTo) * 0.3;
        oph.move(pos, yaw);
      });
      scene.every(1, (e) => {
        for (let i = 1; i < r.pts.length; i++) {
          if ((i + e) % 4 !== 0) continue;
          const a = up(r.pts[i - 1], 0.3 - DW03.sweepAltitude), b = up(r.pts[i], 0.3 - DW03.sweepAltitude);
          line(dim, "dw_ophan_route", a, b, Math.min(12, Math.max(2, Math.ceil(dist(a, b) / 1.6))));
        }
      }, tLock, tRun);
    });
    const hit = /* @__PURE__ */ new Set();
    let flashed = 0;
    const strike = (h, fwd, pass) => {
      const m = marks.get(h.id);
      if (!damage(h, m ? DW03.markedDamage : DW03.damage, caster)) return;
      hit.add(h.id);
      const side = right(fwd);
      const sign = (h.location.x - pos.x) * side.x + (h.location.z - pos.z) * side.z >= 0 ? 1 : -1;
      shove(h, mul(side, sign), DW03.knockback, DW03.lift);
      particle(dim, "dw_ophan_impact", up(h.location, 1));
      particle(dim, "dw_ophan_sparks", up(h.location, 1));
      sound(dim, "dw_ophan_bell", h.location, 1, m ? 1 + pass * 0.08 : 0.85);
      if (m) {
        m.hits++;
        m.mark.skin(Math.min(2, m.hits));
        particle(dim, "dw_ophan_eye", up(h.location, 3.4));
      }
    };
    scene.at(tRun, () => {
      oph.state(S3.sweep);
      sound(dim, "dw_ophan_sweep", pos, 1.2, 0.95 + k2 * 0.08);
    });
    scene.every(1, (e) => {
      const r = route;
      if (!r) return;
      const s = (e + 1) / DW03.passTicks * r.total;
      const { p, dir } = pointAt(r, s);
      pos = p;
      yaw += angleDelta(yaw, yawOf(dir)) * 0.45;
      oph.move(pos, yaw);
      const fwd = fromYaw(yaw);
      const ground = up(pos, -DW03.sweepAltitude);
      const chordA = add(ground, mul(fwd, DW03.rimChord)), chordB = add(ground, mul(fwd, -DW03.rimChord));
      while (flashed < tele.length && distXZ(tele[flashed].loc, pos) < DW03.rimChord) {
        const t = tele[flashed++];
        t.state(3);
        scene.after(8, () => scene.despawn(t));
      }
      particle(dim, "dw_ophan_rim", up(chordA, 0.8));
      particle(dim, "dw_ophan_rim", up(ground, 0.4));
      if (e % 2 === 0) particle(dim, "dw_ophan_sparks", up(ground, 0.3));
      if (e % 6 === 0) particle(dim, "dw_ophan_rim", up(pos, DW03.sweepAltitude - 0.5));
      if (e % 12 === 0) sound(dim, "dw_ophan_hum", pos, 0.9, 0.85 + k2 * 0.15 + e / DW03.passTicks * 0.25);
      for (const h of hostiles(dim, pos, DW03.rimChord + DW03.sweepAltitude + 2, caster)) {
        if (hit.has(h.id)) continue;
        const l = h.location;
        if (l.y < ground.y - 1.5 || l.y > ground.y + DW03.rimHeight) continue;
        if (distToSegment(v(l.x, 0, l.z), v(chordA.x, 0, chordA.z), v(chordB.x, 0, chordB.z)) > DW03.rimHalfWidth) continue;
        strike(h, fwd, k2);
      }
    }, tRun, tRun + DW03.passTicks);
    scene.at(tRun + DW03.passTicks, () => {
      for (const t of tele) if (t.valid) {
        t.state(3);
        scene.after(8, () => scene.despawn(t));
      }
    });
  }
  const tVerdict = tPass0 + DW03.passes * passLen;
  scene.at(tVerdict, () => {
    const live2 = liveMarks();
    const c = live2.length ? mul(live2.reduce((s, m) => add(s, flat(m.e.location)), v(0, 0, 0)), 1 / live2.length) : flat(lastCentre);
    const top = up(groundBelow(dim, v(c.x, center.y + 4, c.z), 24), DW03.hoverHeight - 2);
    const from = pos;
    oph.state(S3.verdict);
    sound(dim, "dw_ophan_verdict", top, 1.4);
    scene.span(tVerdict, tVerdict + VERDICT_HIT, (p) => {
      pos = lerp(from, top, p * p * (3 - 2 * p));
      oph.move(pos, yaw);
    });
    scene.after(VERDICT_HIT, () => {
      particle(dim, "fx_flash", pos);
      ring(dim, "dw_ophan_letters", up(pos, -2), 3, 6);
      burst(dim, "dw_ophan_impact", pos, 3, 5);
      for (const m of liveMarks()) {
        line(dim, "dw_ophan_scan", pos, up(m.e.location, 1.2), 8);
        damage(m.e, DW03.verdictDamage, caster);
        particle(dim, "dw_ophan_impact", up(m.e.location, 1.2));
        particle(dim, "dw_ophan_ping", up(m.e.location, 0.2));
        sound(dim, "dw_ophan_bell", m.e.location, 1, 1.25);
      }
      for (const h of hostiles(dim, up(pos, -DW03.hoverHeight + 2), DW03.verdictPushRadius, caster)) {
        if (!marks.has(h.id)) knockback(h, pos, DW03.verdictKnockback, 0.5);
      }
      for (const m of marks.values()) {
        if (!m.mark.valid) continue;
        m.mark.state(3);
        const mk = m.mark;
        scene.after(8, () => scene.despawn(mk));
      }
    });
  });
  const tDepart = tVerdict + secs(A.verdict) + 2;
  scene.at(tDepart, () => {
    oph.state(S3.depart).skin(0);
    circle.state(3);
    sound(dim, "dw_ophan_depart", pos, 1.2);
    ring(dim, "dw_ophan_rim", pos, 4, 6);
  });
  scene.at(tDepart + secs(1), () => ring(dim, "dw_ophan_letters", pos, 2.5, 6));
  scene.at(tDepart + secs(1.4), () => {
    burst(dim, "dw_glyph_rise", up(pos, 2), 3, 6);
    particle(dim, "fx_flash", up(pos, 2));
  });
  scene.endAt(tDepart + secs(A.depart) + 2);
});

// src/config/dw04.ts
var DW04 = {
  // ---- architecture (blocks).  Changing these also needs the asset module (tools/assets/dw_sanctuary.py).
  /** Distance from the caster to each of the eight corner pillars (octagon circumradius). */
  cornerRadius: 9.5,
  /** Height at which the vault ribs spring from the pillar capitals. */
  ribSpring: 11.75,
  /** Height of the floating galleries above the wall panels. */
  bridgeHeight: 10,
  /** Height of the keystone crown at the centre (rib spring + rib rise). */
  crownHeight: 16.5,
  // ---- defences
  /** Total durability of the sanctuary: absorbed damage, repelled intruders and dissolved shots all spend it. */
  durability: 90,
  /** Fraction of incoming damage allies inside still take (0.2 = 80 % absorbed by the ward). */
  wardFactor: 0.2,
  /** Allies count as inside within this horizontal distance of the centre. */
  innerRadius: 8.2,
  /** ...and within this vertical band relative to the floor. */
  insideBelow: 2,
  insideAbove: 18,
  /** Hostiles that cross this radius are repelled by the threshold law. */
  thresholdRadius: 8,
  /** Ticks between threshold checks, and per-intruder immunity after being repelled. */
  thresholdEvery: 4,
  repelCooldown: 14,
  /** Repel strength (horizontal, vertical), slowness and a small smite. */
  repelH: 1.5,
  repelV: 0.4,
  repelSlowTicks: 40,
  repelSlowAmp: 2,
  repelDamage: 2,
  /** Durability spent per repelled intruder. */
  repelCost: 4,
  /** Durability spent per dissolved hostile projectile. */
  projectileCost: 3,
  /** Ticks between projectile sweeps. */
  projectileEvery: 2,
  /** Durability fractions at which one wall section breaks back into letters (walls first, then gates). */
  breakAt: [0.75, 0.5, 0.25],
  /** Barrier column height under walls, gates and pillars (blocks). */
  barrierHeight: 7,
  /** Half width of the open doorway kept free of barriers in each gate (blocks). */
  doorHalf: 1.5,
  /** Gentle regeneration for allies inside: amount every N ticks. */
  regenAmount: 1,
  regenEvery: 40,
  // ---- timing (ticks)
  /** How long the finished sanctuary stands before it is unwritten (12 s active duration). */
  activeTicks: 240,
  /** Construction pacing: first launch tick and the gap between letters of each course. */
  pillarsAt: 24,
  pillarGap: 2,
  wallsAt: 42,
  wallGap: 3,
  bridgesAt: 68,
  bridgeGap: 3,
  ribsAt: 76,
  ribGap: 2,
  crownAt: 94,
  /** Ticks between pieces during the final unwriting. */
  unwriteGap: 1
};

// src/spells/dw04_sanctuary.ts
var P = { hidden: 0, letter: 1, form: 2, stand: 3, break: 4, unwrite: 5, flare: 6 };
var LS = { hidden: 0, write: 1, hold: 2, peel: 3, fade: 4 };
var FLY = 14;
var FORM = 20;
var BREAK = 26;
var UNWRITE = 30;
var FLARE = 10;
var WRITE = 24;
var FADE = 14;
var ACTOR = {
  pillar: "dw_sanct_pillar",
  gate: "dw_sanct_gate",
  wall: "dw_sanct_wall",
  bridge: "dw_sanct_bridge",
  rib: "dw_sanct_rib",
  crown: "dw_sanct_crown"
};
var LETTER_REST = {
  pillar: [6, 0],
  wall: [4.25, 0],
  gate: [6.25, 0],
  bridge: [1.5, 0],
  rib: [2, 0.75],
  crown: [0.25, 0]
};
var LINE_OF = { pillar: 0, wall: 1, gate: 1, bridge: 1, rib: 2, crown: 2 };
var LINES = [{ size: 1, h: 1.7 }, { size: 1.25, h: 2.9 }, { size: 1.5, h: 4.1 }];
var MID = { pillar: 6, wall: 4.5, gate: 6, bridge: 1.5, rib: 2.5, crown: 0 };
var dw04_sanctuary_default = defineSpell("dw04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const center = groundBelow(dim, caster.location);
  const fwd = aim.forward;
  const base = Math.atan2(fwd.z, fwd.x) * 180 / Math.PI;
  const book = add(up(caster.location, 1.2), mul(fwd, 0.7));
  const walls = blocksFor(scene);
  const lights = blocksFor(scene);
  const R2 = DW04.cornerRadius;
  const apothem = R2 * Math.cos(Math.PI / 8);
  const pieces = [];
  const mk = (kind, pos, angle, launch2, variant = 0) => {
    const pc = { kind, pos, angle, launch: launch2, variant, yaw: 0, cells: [], standing: false, broken: false, flareUntil: 0 };
    pieces.push(pc);
    return pc;
  };
  const claimed = /* @__PURE__ */ new Set();
  const claim = (pc, x, z) => {
    const key = `${x},${z}`;
    if (claimed.has(key)) return;
    claimed.add(key);
    pc.cells.push({ x, z });
  };
  const opposite = [0, 4, 2, 6, 1, 5, 3, 7];
  const pillars = [];
  for (let k2 = 0; k2 < 8; k2++) {
    const a = base + 22.5 + 45 * k2;
    const pc = mk("pillar", polar(center, R2, a), a, DW04.pillarsAt + DW04.pillarGap * opposite.indexOf(k2), k2 % 2);
    claim(pc, Math.floor(pc.pos.x), Math.floor(pc.pos.z));
    pillars.push(pc);
  }
  const gates = [];
  const sides = [];
  let bi = 0;
  for (let k2 = 0; k2 < 8; k2++) {
    const a = base + 45 * k2;
    const isGate = k2 % 2 === 0;
    const pc = mk(isGate ? "gate" : "wall", polar(center, apothem, a), a, DW04.wallsAt + DW04.wallGap * k2);
    (isGate ? gates : sides).push(pc);
    const ca = polar(center, R2, a - 22.5), cb = polar(center, R2, a + 22.5);
    const len2 = dist(ca, cb);
    const n = Math.ceil(len2 / 0.25);
    for (let i = 0; i <= n; i++) {
      const p = lerp(ca, cb, i / n);
      const x = Math.floor(p.x), z = Math.floor(p.z);
      const along = ((x + 0.5 - ca.x) * (cb.x - ca.x) + (z + 0.5 - ca.z) * (cb.z - ca.z)) / len2;
      if (isGate && Math.abs(along - len2 / 2) < DW04.doorHalf) continue;
      claim(pc, x, z);
    }
    if (!isGate) pc.bridge = mk("bridge", polar(center, apothem, a, DW04.bridgeHeight), a, DW04.bridgesAt + DW04.bridgeGap * bi++);
  }
  const ribs = [];
  for (let k2 = 0; k2 < 8; k2++) {
    const a = base + 22.5 + 45 * k2;
    ribs.push(mk("rib", polar(center, R2, a, DW04.ribSpring), a, DW04.ribsAt + DW04.ribGap * opposite.indexOf(k2)));
  }
  const crown = mk("crown", up(center, DW04.crownHeight), base, DW04.crownAt);
  const tDefend = DW04.pillarsAt + FLY + FORM;
  const tComplete = DW04.crownAt + FLY + FORM;
  const tUnwrite = tComplete + DW04.activeTicks;
  const unwriteOrder = [crown, ...ribs, ...pieces.filter((p) => p.kind === "bridge"), ...gates, ...sides, ...pillars];
  scene.endAt(tUnwrite + unwriteOrder.length * DW04.unwriteGap + UNWRITE + 10);
  let active = false, collapsed = false, finished = false;
  const circle = scene.spawn("dw_circle", up(center, 0.05), { size: R2 / 2, state: 1 });
  scene.at(16, () => circle.state(2));
  sound(dim, "dw_sanct_write", book, 1.1);
  const lines = [];
  const firstOf = [DW04.pillarsAt, DW04.wallsAt, DW04.ribsAt];
  LINES.forEach((ln, i) => {
    scene.at(i * 3, () => {
      const at = up(center, ln.h);
      lines[i] = scene.spawn("dw_sanct_script", at, { yaw: aim.yaw + i * 40, size: ln.size, state: LS.write });
      line(dim, "dw_sanct_ink", book, polar(center, 3.5 * ln.size, base + 180 + i * 30, ln.h), 4);
    });
    scene.at(i * 3 + WRITE, () => lines[i]?.state(LS.hold));
    scene.at(firstOf[i], () => lines[i]?.state(LS.peel));
    scene.at(DW04.crownAt + 2, () => lines[i]?.state(LS.fade));
    scene.at(DW04.crownAt + 2 + FADE, () => {
      if (lines[i]) scene.despawn(lines[i]);
    });
  });
  scene.every(5, () => particle(dim, "dw_sanct_ink", book), 0, DW04.crownAt);
  for (const pc of pieces) scene.at(pc.launch, () => launch(pc));
  function launch(pc) {
    if (collapsed || pc.broken) return;
    const ln = LINES[LINE_OF[pc.kind]];
    const yaw = pc.kind === "crown" ? aim.yaw : yawOf(sub(center, pc.pos));
    pc.yaw = yaw;
    const toward = pc.kind === "crown" ? { x: 0, y: 0, z: 0 } : norm(flat(sub(center, pc.pos)));
    const [ru, rf] = LETTER_REST[pc.kind];
    const off = add({ x: 0, y: ru, z: 0 }, mul(toward, rf));
    const glyphAt = polar(center, 3.5 * ln.size, pc.angle, ln.h);
    const start = sub(glyphAt, off);
    const end = pc.pos;
    const ctrl = up(lerp(start, end, 0.45), 3 + (end.y - center.y) * 0.25);
    const a = scene.spawn(ACTOR[pc.kind], start, { yaw, state: P.letter, kind: pc.kind === "pillar" ? pc.variant : void 0 });
    pc.actor = a;
    particle(dim, "dw_sanct_peel", glyphAt);
    sound(dim, "dw_sanct_letter", glyphAt, 0.7, 0.9 + pc.launch % 5 * 0.05);
    const t0 = scene.tick;
    scene.span(t0, t0 + FLY, (p) => {
      if (!pc.broken) a.move(bezier(start, ctrl, end, easeOut(p)), yaw);
    });
    scene.every(3, () => {
      if (!pc.broken && a.valid) particle(dim, "dw_sanct_ink", add(a.loc, off));
    }, t0 + 1, t0 + FLY);
    scene.at(t0 + FLY, () => {
      if (pc.broken) return;
      a.move(end, yaw).state(P.form);
      particle(dim, "dw_sanct_quill", up(end, pc.kind === "rib" || pc.kind === "crown" ? 0.5 : 0.3));
    });
    scene.at(t0 + FLY + FORM, () => {
      if (pc.broken) return;
      a.state(P.stand);
      pc.standing = true;
      const mid = add(up(end, MID[pc.kind]), mul(toward, pc.kind === "rib" ? 3 : 0));
      if (pc.kind === "pillar" || pc.kind === "wall" || pc.kind === "gate") particle(dim, "dw_sanct_settle", up(end, 0.2));
      particle(dim, "dw_sanct_gild", mid);
      const pitch = { pillar: 0.95, wall: 1, gate: 0.85, bridge: 1.1, rib: 1.15, crown: 0.8 }[pc.kind];
      sound(dim, "dw_sanct_settle", mid, 0.9, pitch);
      raise(pc);
    });
  }
  function occupied(x, z, y) {
    let found = [];
    try {
      found = dim.getEntities({
        location: { x: x + 0.5, y: y + 1, z: z + 0.5 },
        maxDistance: 2.2,
        excludeFamilies: ["grimoire_construct"],
        excludeTypes: ["minecraft:item", "minecraft:xp_orb", "minecraft:player"]
      });
    } catch {
      return false;
    }
    return found.some((e) => {
      const l = e.location;
      return Math.abs(l.x - (x + 0.5)) < 0.95 && Math.abs(l.z - (z + 0.5)) < 0.95;
    });
  }
  function raise(pc) {
    for (const c of pc.cells) {
      const floor = groundBelow(dim, { x: c.x + 0.5, y: center.y + 2.5, z: c.z + 0.5 }, 8).y;
      if (Math.abs(floor - center.y) > 3 || occupied(c.x, c.z, floor)) continue;
      c.y = Math.floor(floor);
      c.h = DW04.barrierHeight;
      walls.column(c.x, c.y, c.z, c.h);
    }
  }
  function lower(pc) {
    for (const c of pc.cells) if (c.y !== void 0 && c.h) {
      walls.removeColumn(c.x, c.y, c.z, c.h);
      c.y = void 0;
    }
  }
  const inside = (l) => distXZ(l, center) <= DW04.innerRadius && l.y >= center.y - DW04.insideBelow && l.y <= center.y + DW04.insideAbove;
  const safeLoc = (e) => {
    try {
      return e && e.isValid ? { ...e.location } : void 0;
    } catch {
      return void 0;
    }
  };
  const ward = addWard({
    scene,
    factor: DW04.wardFactor,
    pool: DW04.durability,
    protects: (e) => active && e.typeId === "minecraft:player" && (!CONFIG.targeting.pvp || e.id === caster.id) && inside(e.location),
    onAbsorb: (_amount, attacker, victim) => {
      const vl = safeLoc(victim);
      if (vl) {
        particle(dim, "dw_sanct_ward", up(vl, 1));
        sound(dim, "dw_sanct_absorb", vl, 0.8);
        flare(nearest([...sides, ...gates], vl));
      }
      checkDurability(safeLoc(attacker) ?? vl ?? center);
    },
    onBreak: () => collapse()
  });
  function spend(cost, at) {
    ward.pool = Math.max(0, (ward.pool ?? 0) - cost);
    checkDurability(at);
  }
  let nextBreak = 0;
  function checkDurability(at) {
    if (collapsed || finished) return;
    const frac = (ward.pool ?? 0) / DW04.durability;
    while (nextBreak < DW04.breakAt.length && frac <= DW04.breakAt[nextBreak]) {
      nextBreak++;
      breakSection(at);
    }
    if ((ward.pool ?? 0) <= 1e-4) {
      ward.broken = true;
      collapse();
    }
  }
  function nearest(list, at) {
    let best, bd = Infinity;
    for (const p of list) {
      const d = distXZ(p.pos, at);
      if (d < bd) {
        bd = d;
        best = p;
      }
    }
    return best;
  }
  function flare(pc) {
    if (!pc || !pc.standing || pc.broken || !pc.actor?.valid) return;
    pc.actor.state(P.flare);
    pc.flareUntil = scene.tick + FLARE;
    const a = pc.actor;
    scene.after(FLARE, () => {
      if (pc.standing && !pc.broken && scene.tick >= pc.flareUntil) a.state(P.stand);
    });
  }
  function breakPiece(pc, loud = true) {
    if (pc.broken) return;
    pc.broken = true;
    pc.standing = false;
    lower(pc);
    const a = pc.actor;
    if (!a || !a.valid) return;
    a.state(P.break);
    const mid = up(pc.pos, MID[pc.kind]);
    particle(dim, "dw_sanct_shard", mid);
    if (loud) sound(dim, "dw_sanct_break", mid, 1);
    scene.after(BREAK, () => scene.despawn(a));
  }
  function breakSection(at) {
    const pick = nearest(sides.filter((p) => p.standing), at) ?? nearest(gates.filter((p) => p.standing), at);
    if (!pick) return;
    breakPiece(pick);
    if (pick.bridge) {
      const b = pick.bridge;
      scene.after(4, () => breakPiece(b, false));
    }
  }
  function collapse() {
    if (collapsed || finished) return;
    collapsed = true;
    active = false;
    ward.broken = true;
    sound(dim, "dw_sanct_break", up(center, 6), 1.4, 0.8);
    const order = unwriteOrder.filter((p) => !p.broken);
    order.forEach((pc, i) => {
      if (!pc.actor) {
        pc.broken = true;
        return;
      }
      scene.after(i, () => breakPiece(pc, i % 6 === 0));
    });
    scene.after(order.length + 6, () => {
      circle.state(3);
      sound(dim, "dw_sanct_unwrite", up(center, 4), 1, 0.9);
      lights.clearAll();
    });
    scene.after(order.length + 18, () => scene.despawn(circle));
    scene.endAt(scene.tick + order.length + BREAK + 22);
  }
  const lastRepel = /* @__PURE__ */ new Map();
  scene.every(DW04.thresholdEvery, () => {
    if (!active) return;
    for (const e of hostiles(dim, center, DW04.thresholdRadius + 2, caster)) {
      const l = e.location;
      if (!inside(l) || distXZ(l, center) > DW04.thresholdRadius) continue;
      if (scene.tick - (lastRepel.get(e.id) ?? -999) < DW04.repelCooldown) continue;
      lastRepel.set(e.id, scene.tick);
      const gate = nearest(gates, l);
      const dir = distXZ(l, gate.pos) < 1.6 ? sub(l, center) : sub(gate.pos, l);
      shove(e, dir, DW04.repelH, DW04.repelV);
      effect(e, "slowness", DW04.repelSlowTicks, DW04.repelSlowAmp);
      damage(e, DW04.repelDamage, caster);
      particle(dim, "dw_sanct_edict", up(l, 0.15));
      particle(dim, "dw_sanct_law", up(l, 1));
      particle(dim, "dw_sanct_edict", up(gate.pos, 0.2));
      flare(gate);
      sound(dim, "dw_sanct_repel", l, 1);
      spend(DW04.repelCost, l);
      if (!active) return;
    }
  }, tDefend, tUnwrite);
  scene.every(DW04.projectileEvery, () => {
    if (!active) return;
    const gone = dissolveProjectiles(scene, up(center, 6), R2 + 2);
    if (!gone.length) return;
    for (const l of gone.slice(0, 4)) particle(dim, "dw_sanct_dissolve", l);
    sound(dim, "dw_sanct_dissolve", gone[0], 0.8);
    flare(nearest([...sides, ...gates], gone[0]));
    spend(DW04.projectileCost * gone.length, gone[0]);
  }, tDefend, tUnwrite);
  scene.every(DW04.regenEvery, () => {
    if (!active) return;
    for (const p of allies(dim, center, DW04.innerRadius + 3, caster)) {
      if (inside(p.location) && heal(p, DW04.regenAmount) > 0) particle(dim, "dw_sanct_gild", up(p.location, 0.6));
    }
  }, tDefend, tUnwrite);
  scene.at(tDefend, () => {
    active = true;
    lights.place(up(center, 2), LIGHT);
    for (let k2 = 0; k2 < 4; k2++) lights.place(polar(center, 5, base + 45 + 90 * k2, 3), LIGHT);
  });
  scene.at(tComplete, () => {
    if (collapsed) return;
    sound(dim, "dw_sanct_complete", up(center, 8), 1.4);
    for (const pc of [...gates, ...sides]) flare(pc);
    ring(dim, "dw_sanct_beam", up(center, 0.2), R2, 8, base + 22.5);
    burst(dim, "dw_sanct_gild", up(center, DW04.crownHeight), 2, 6);
    particle(dim, "dw_sanct_edict", up(center, 0.3));
  });
  scene.every(8, () => {
    if (active) particle(dim, "dw_sanct_mote", up(center, 2.5));
  }, tComplete, tUnwrite);
  scene.every(60, () => {
    if (active) sound(dim, "dw_sanct_bed", up(center, 4), 0.6);
  }, tComplete, tUnwrite);
  scene.at(tUnwrite, () => {
    if (collapsed) return;
    finished = true;
    active = false;
    ward.broken = true;
    sound(dim, "dw_sanct_unwrite", up(center, 6), 1.3);
    unwriteOrder.forEach((pc, i) => {
      scene.after(i * DW04.unwriteGap, () => {
        if (pc.broken) return;
        pc.standing = false;
        lower(pc);
        const a = pc.actor;
        if (!a || !a.valid) return;
        a.state(P.unwrite);
        if (i % 2 === 0) particle(dim, "dw_sanct_stream", up(pc.pos, MID[pc.kind]));
        scene.after(UNWRITE, () => scene.despawn(a));
      });
    });
    const n = unwriteOrder.length * DW04.unwriteGap;
    scene.after(n + 12, () => {
      circle.state(3);
      lights.clearAll();
      burst(dim, "dw_sanct_stream", up(center, 3), 3, 6);
    });
    scene.after(n + 24, () => scene.despawn(circle));
  });
});

// src/config/dw05.ts
var DW05 = {
  // ---- stage layout (blocks, relative to the fight centre; "forward" points away from the caster)
  /** Snap distance used to pick the fight centre around the aim point. */
  focusSnap: 14,
  /** Radius of the judged region: every search for enemies uses it. */
  regionRadius: 18,
  /** Seraph gate (lancet arch): forward distance and base height. */
  seraphGate: { forward: 21, side: 0, up: 12 },
  /** Cherub gate (tetrapylon): forward, sideways (negative = caster's left) and base height. */
  cherubGate: { forward: 15, side: -17, up: 4 },
  /** Ophanim gate (wheel portal): forward, sideways and centre height. */
  ophanGate: { forward: 15, side: 17, up: 9 },
  /** Phase II stations: the Seraph highest and centred, the Cherub in the middle on the left. */
  seraphStation: { forward: 12, side: 0, up: 18 },
  cherubStation: { forward: 7, side: -11, up: 8 },
  /** Where the Ophanim hovers while it scans (centre height above the ground). */
  ophanStation: { forward: 3, side: 6, up: 7 },
  /** Phase III posts around the throne: Seraph above it, Cherub and Ophanim at its flanks. */
  seraphPost: { forward: 16, side: 0, up: 27 },
  cherubPost: { forward: 9, side: -12, up: 8 },
  ophanPost: { forward: 9, side: 12, up: 7 },
  /** The empty throne: forward distance and dais height. */
  throne: { forward: 12, side: 0, up: 10 },
  /** Giant sentences: radius (blocks) and height of the three concentric bands. */
  sentences: [
    { radius: 8, up: 1.2 },
    { radius: 11, up: 5.5 },
    { radius: 14, up: 10 }
  ],
  // ---- PHASE I: the sentence pronounced over the region (a temporary law of judgment)
  /** Damage as the third sentence closes over every enemy in the region. */
  domainDamage: 3,
  /** Slowness the pronounced law lays on enemies (ticks, amplifier). */
  domainSlowTicks: 300,
  domainSlowAmp: 1,
  // ---- OPHANIM: detection, marking, directional sweeping passes
  /** Ticks for the scanning gaze to sweep a full circle. */
  scanTicks: 36,
  /** Maximum enemies the witnesses can mark. */
  maxMarks: 8,
  /** Searing damage as a mark is burned onto an enemy. */
  markDamage: 2,
  /** Number of straight sweeping passes and their timing. */
  passes: 3,
  lockTicks: 12,
  passTicks: 32,
  /** Half-length of a pass line through the marked (min / max). */
  passHalfMin: 8,
  passHalfMax: 13,
  /** Centre height of the wheel during a pass (its rim grazes the ground). */
  sweepAltitude: 5.6,
  /** Rim contact: half chord length, lateral reach and height (blocks). */
  rimChord: 4.2,
  rimHalfWidth: 2,
  rimHeight: 3.2,
  /** Rim damage per pass to unmarked / marked enemies (one hit per enemy per pass). */
  passDamage: 7,
  passMarkedDamage: 11,
  passKnock: 0.9,
  passLift: 0.35,
  // ---- CHERUBIM: four faces
  /** Human face: damage of the testament glyph written on each enemy (also marks the unmarked). */
  testamentDamage: 3,
  /** Ox face: ward that protects the caster and allied players within wardRadius of the caster. */
  wardRadius: 14,
  /** Total damage the ward can absorb before it breaks. */
  wardPool: 60,
  /** Fraction of incoming damage the ward stops while it holds (1 = everything). */
  wardStrength: 1,
  /** Lion face: roar damage (once per enemy), multiplier vs. marked, reach and cone width. */
  roarDamage: 12,
  markBonus: 1.35,
  roarHalfWidthNear: 2.5,
  roarHalfWidthFar: 6,
  roarKnock: 2,
  roarLift: 0.5,
  /** Blocks per tick the roar rings travel. */
  roarSpeed: 1,
  /** Eagle face: feather-blade damage, multiplier vs. marked, radius, height, telegraph and fall ticks. */
  bladeDamage: 14,
  bladeMarkBonus: 1.5,
  bladeRadius: 2.2,
  bladeHeight: 10,
  bladeWarn: 20,
  diveTicks: 5,
  bladesPerWave: 4,
  // ---- SERAPHIM: chants of judgment columns
  /** Damage of the columns of the first, second and third chant. */
  chantDamage: [9, 10, 12],
  /** Blast radius of a column (blocks). */
  columnRadius: 2.8,
  /** Maximum columns per chant. */
  maxColumns: 6,
  /** Ticks of warning before a column lands. */
  columnWarn: 16,
  // ---- PHASE III: the verdict
  /** Letters per verdict line (three lines are written before the throne). */
  lettersPerLine: 5,
  /** Height of the three verdict lines above the ground and their distance in front of the throne. */
  lineHeights: [20, 15.5, 11],
  lineForward: 4,
  /** Spacing of letters within a line (blocks). */
  letterSpacing: 3.8,
  /** Damage of one descending verdict letter and its blast radius. */
  verdictDamage: 22,
  verdictRadius: 3.5,
  /** Extra damage (once per enemy) for enemies that bear a sacred mark. */
  verdictMarkBonus: 14,
  /** An enemy can be struck by at most this many letters. */
  maxLetterHits: 2,
  verdictKnock: 1.4,
  verdictLift: 0.6,
  /** Telegraph radius of a designated hostile area (blocks); areas closer than this are merged. */
  areaRadius: 3.5,
  /** Ophanim's finishing gaze on every surviving marked enemy. */
  gazeDamage: 8,
  /** Seraph's finishing column over the densest area: damage and radius. */
  finalColumnDamage: 10,
  finalColumnRadius: 4,
  /** Ticks a letter needs to fall from its line to the ground, and the stagger between letters. */
  plungeTicks: 8,
  plungeStagger: 2
};

// src/spells/dw05_heavenly_throne.ts
var GATE = { hidden: 0, manifest: 1, closed: 2, open: 3, opened: 4, close: 5, fold: 6 };
var SEN = { hidden: 0, unfold: 1, idle: 2, gather: 3 };
var THR = { hidden: 0, assemble: 1, idle: 2, declare: 3, unmake: 4 };
var LET = { hidden: 0, ignite: 1, hold: 2, plunge: 3, impact: 4 };
var SER = { hidden: 0, arrive: 1, veiled: 2, unfurl: 3, open: 4, chant1: 5, chant2: 6, chant3: 7, verdict: 8, depart: 9 };
var CHE = { hidden: 0, arrive: 1, idle: 2, human: 3, ox: 4, oxRetaliate: 5, lion: 6, eagle: 7, verdict: 8, depart: 9 };
var OPH = { hidden: 0, arrive: 1, survey: 2, lock: 3, sweep: 4, verdict: 5, depart: 6 };
var BLADE2 = { form: 1, aim: 2, dive: 3, shatter: 4 };
var MARK2 = { appear: 1, hold: 2, burst: 3 };
var LETTER_KINDS = 6;
var T2 = {
  manifest: 1.6,
  open: { seraph: 1.5, cherub: 2.4, ophan: 1.6 },
  close: 1,
  fold: 1.4,
  unfold: 1.6,
  gather: 1.4,
  assemble: 3,
  declare: 1,
  unmake: 2,
  ignite: 0.5,
  impact: 0.6,
  // dw_seraph.py (DW01 lands its verdict 15 ticks after the gesture starts)
  seraph: { arrive: 1.5, unfurl: 1.3, chantLead: [18, 19, 19], depart: 1.6, verdictHitTicks: 15 },
  // dw_cherub.py
  cherub: {
    arrive: 1.6,
    human: 1.6,
    humanCast: 1.05,
    oxLock: 0.75,
    ox: 1,
    lion: 1.8,
    lionRoar: 0.95,
    eagle: 2.8,
    eagleThrust: [1.6, 2.5],
    verdictHit: 0.8,
    depart: 1.8,
    bladeForm: 0.6,
    bladeShatter: 0.5,
    roarLife: 1
  },
  // dw_ophanim.py
  ophan: { arrive: 2, lock: 0.6, verdict: 1.1, verdictHit: 0.55, depart: 1.8 }
};
var dw05_heavenly_throne_default = defineSpell("dw05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, DW05.focusSnap);
  const tow = flat(sub(center, caster.location));
  const fwd = Math.hypot(tow.x, tow.z) > 2 ? norm(tow) : aim.forward;
  const side = right(fwd);
  const at = (p) => add(add(up(center, p.up), mul(fwd, p.forward)), mul(side, p.side));
  const view = sub(center, mul(fwd, 6));
  const yawTo = (from, to) => yawOf(flat(sub(to, from)));
  const lights = blocksFor(scene);
  const marks = /* @__PURE__ */ new Map();
  function region(max) {
    return hostiles(dim, center, DW05.regionRadius, caster, max);
  }
  function liveMarks() {
    return [...marks.values()].filter((m) => isAlive(m.e));
  }
  function cluster() {
    let pts = liveMarks().map((m) => m.e.location);
    if (!pts.length) pts = region(8).map((e) => e.location);
    if (!pts.length) return center;
    const c = mul(pts.reduce((s, p) => add(s, p), v(0, 0, 0)), 1 / pts.length);
    return groundBelow(dim, v(c.x, center.y + 4, c.z), 24);
  }
  function markEnemy(e) {
    if (!isAlive(e)) return void 0;
    const old = marks.get(e.id);
    if (old) return old;
    if (marks.size >= DW05.maxMarks) return void 0;
    const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK2.appear, skin: 0 });
    scene.follow(mark, e, 2.4);
    scene.after(6, () => mark.state(MARK2.hold));
    const m = { e, mark, n: 0 };
    marks.set(e.id, m);
    damage(e, DW05.markDamage, caster);
    return m;
  }
  function testify(e) {
    const m = marks.get(e.id);
    if (m && m.mark.valid) {
      m.n++;
      m.mark.skin(Math.min(2, m.n));
    }
  }
  function boost(e, base, bonus) {
    return marks.has(e.id) ? base * bonus : base;
  }
  function flashOut(a, after = 8) {
    if (!a || !a.valid) return;
    a.state(3);
    scene.after(after, () => scene.despawn(a));
  }
  const circle = scene.spawn("dw_circle", center, { size: 6, state: 1 });
  scene.at(16, () => circle.state(2));
  sound(dim, "dw5_manifest", up(center, 8), 1.6);
  sound(dim, "dw_circle", center, 1);
  lights.place(up(center, 2), LIGHT);
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), 5, 8));
  function makeGate(id, spot, mouthUp, t, open, snd, openLen) {
    const pos = at(spot);
    const yaw = yawTo(pos, view);
    return { a: scene.spawn(id, pos, { yaw, state: GATE.hidden }), pos, mouth: up(pos, mouthUp), yaw, t, open, snd, openLen };
  }
  const gO = makeGate("dw5_gate_ophan", DW05.ophanGate, 0, 0, 50, "dw5_gate_ophan", T2.open.ophan);
  const gC = makeGate("dw5_gate_cherub", DW05.cherubGate, 5.5, 8, 80, "dw5_gate_cherub", T2.open.cherub);
  const gS = makeGate("dw5_gate_seraph", DW05.seraphGate, 9.5, 16, 110, "dw5_gate_seraph", T2.open.seraph);
  for (const g of [gO, gC, gS]) {
    scene.at(g.t, () => {
      g.a.state(GATE.manifest);
      line(dim, "dw5_fold", add(g.mouth, mul(right(fromYaw(g.yaw)), -5)), add(g.mouth, mul(right(fromYaw(g.yaw)), 5)), 4);
      sound(dim, "dw_circle", g.mouth, 1.2, 0.8);
    });
    scene.at(g.t + secs(T2.manifest), () => g.a.state(GATE.closed));
    scene.at(g.open, () => {
      g.a.state(GATE.open);
      sound(dim, g.snd, g.mouth, 2);
      burst(dim, "dw5_gate_dust", g.mouth, 3, 4);
    });
    scene.at(g.open + secs(g.openLen), () => {
      g.a.state(GATE.opened);
      particle(dim, "fx_flash", g.mouth);
      particle(dim, "dw5_gate_rays", g.mouth);
    });
  }
  scene.every(12, (el) => {
    for (const g of [gO, gC, gS]) if (scene.tick > g.open + 30 && scene.tick < 560) particle(dim, el % 24 ? "dw5_gate_rays" : "dw_mote", g.mouth);
  }, 60, 640);
  const sentences = DW05.sentences.map((b, k2) => scene.spawn("dw5_sentence", up(center, b.up), { kind: k2, size: b.radius / 8, state: SEN.hidden, yaw: yawOf(fwd) + k2 * 40 }));
  sentences.forEach((s, k2) => {
    const t0 = 24 + k2 * 16;
    scene.at(t0, () => {
      s.state(SEN.unfold);
      sound(dim, "dw5_sentence", up(center, DW05.sentences[k2].up + 1), 1.4, 0.9 + k2 * 0.12);
      ring(dim, "dw_glyph_rise", up(center, DW05.sentences[k2].up), DW05.sentences[k2].radius, 8, k2 * 15);
    });
    scene.at(t0 + secs(T2.unfold), () => s.state(SEN.idle));
  });
  scene.at(100, () => {
    sound(dim, "dw5_domain", up(center, 3), 1.6);
    particle(dim, "dw5_domain", up(center, 0.3));
    particle(dim, "fx_shock", up(center, 0.4));
    ring(dim, "dw_glyph_fall", up(center, 6), 7, 8);
    for (const e of region()) {
      damage(e, DW05.domainDamage, caster);
      effect(e, "slowness", DW05.domainSlowTicks, DW05.domainSlowAmp);
      particle(dim, "dw_halo", up(e.location, 1.2));
    }
  });
  for (const t of [120, 220, 320]) scene.at(t, () => sound(dim, "dw5_bed", up(center, 8), 1.2));
  const tO = 130;
  const oStart = add(gO.pos, mul(fwd, 1.5));
  const oStation = at(DW05.ophanStation);
  let oPos = oStart;
  let oYaw = gO.yaw;
  const oph = scene.spawn("ophanim", oStart, { yaw: oYaw, state: OPH.hidden, skin: 0 });
  scene.at(tO, () => {
    oph.state(OPH.arrive);
    sound(dim, "dw_ophan_arrive", oStart, 1.5);
    particle(dim, "fx_flash", gO.mouth);
  });
  scene.span(tO, tO + secs(T2.ophan.arrive), (p) => {
    oPos = bezier(oStart, up(lerp(oStart, oStation, 0.5), 2), oStation, smooth(p));
    oph.move(oPos, oYaw);
  });
  const tSurvey = tO + secs(T2.ophan.arrive);
  const tScan = tSurvey + 2;
  const scan0 = yawOf(fwd) + 90;
  scene.at(tSurvey, () => {
    oph.state(OPH.survey);
    sound(dim, "dw_ophan_hum", oPos, 0.9, 0.6);
    particle(dim, "dw_ophan_ping", up(center, 0.2));
  });
  let prevAng = scan0;
  scene.every(1, (e) => {
    const ang = scan0 + 360 * (e + 1) / DW05.scanTicks;
    const dir = v(Math.cos(ang * Math.PI / 180), 0, Math.sin(ang * Math.PI / 180));
    const tip = add(center, mul(dir, DW05.regionRadius));
    line(dim, "dw_ophan_scan", up(add(center, mul(dir, 2)), 0.25), up(tip, 0.25), 6);
    if (e % 3 === 0) line(dim, "dw_ophan_scan", up(oPos, -1), up(tip, 0.4), 4);
    if (e % 6 === 0) {
      sound(dim, "dw_ophan_scan", center, 0.9, 0.9 + e / DW05.scanTicks * 0.3);
      particle(dim, "dw_ophan_ping", up(center, 0.25));
    }
    for (const h of region()) {
      const a = Math.atan2(h.location.z - center.z, h.location.x - center.x) * 180 / Math.PI;
      const d = ((a - prevAng) % 360 + 360) % 360;
      if (d <= ang - prevAng && !marks.has(h.id) && markEnemy(h)) {
        sound(dim, "dw_ophan_mark", h.location, 0.9, 1 + marks.size * 0.04);
        particle(dim, "dw_ophan_eye", up(h.location, 3.4));
        line(dim, "dw_ophan_scan", up(oPos, -1), up(h.location, 1.2), 6);
      }
    }
    prevAng = ang;
  }, tScan, tScan + DW05.scanTicks);
  scene.at(tScan + DW05.scanTicks, () => {
    for (const h of region()) if (!marks.has(h.id) && markEnemy(h)) particle(dim, "dw_ophan_eye", up(h.location, 3.4));
  });
  const tPass0 = tScan + DW05.scanTicks + 4;
  const passLen = DW05.lockTicks + DW05.passTicks;
  for (let k2 = 0; k2 < DW05.passes; k2++) {
    const tLock = tPass0 + k2 * passLen;
    const tRun = tLock + DW05.lockTicks;
    let a = oPos, b = oPos, dir = fwd;
    let tele = [];
    const hit = /* @__PURE__ */ new Set();
    scene.at(tLock, () => {
      const c = cluster();
      const base = flat(sub(c, oPos));
      dir = fromYaw((Math.hypot(base.x, base.z) > 1 ? yawOf(base) : yawOf(fwd)) + k2 * 60);
      let spread = 0;
      for (const m of liveMarks()) spread = Math.max(spread, distXZ(m.e.location, c));
      const half = clamp(spread + 4, DW05.passHalfMin, DW05.passHalfMax);
      const ga = groundBelow(dim, up(sub(c, mul(dir, half)), 4), 24), gb = groundBelow(dim, up(add(c, mul(dir, half)), 4), 24);
      a = up(ga, DW05.sweepAltitude);
      b = up(gb, DW05.sweepAltitude);
      oph.state(OPH.lock).skin(1);
      sound(dim, "dw_ophan_lock", oPos, 1.2, 1 + k2 * 0.06);
      tele = [ga, lerp(ga, gb, 0.5), gb].map((p) => scene.spawn("telegraph", p, { kind: 0, size: DW05.rimHalfWidth + 0.6, state: 1 }));
      const from = oPos, ctrl = up(lerp(oPos, a, 0.5), 4), yawGoal = yawOf(dir);
      scene.span(tLock, tRun, (p) => {
        oPos = bezier(from, ctrl, a, p);
        oYaw += angleDelta(oYaw, yawGoal) * 0.3;
        oph.move(oPos, oYaw);
        if (Math.round(p * 12) % 2 === 0) line(dim, "dw_ophan_route", up(a, 0.3 - DW05.sweepAltitude), up(b, 0.3 - DW05.sweepAltitude), 8);
      });
    });
    scene.at(tRun, () => {
      oph.state(OPH.sweep);
      sound(dim, "dw_ophan_sweep", oPos, 1.3, 0.95 + k2 * 0.08);
    });
    scene.every(1, (e) => {
      oPos = lerp(a, b, (e + 1) / DW05.passTicks);
      oYaw = yawOf(dir);
      oph.move(oPos, oYaw);
      const ground = up(oPos, -DW05.sweepAltitude);
      const ca = add(ground, mul(dir, DW05.rimChord)), cb = add(ground, mul(dir, -DW05.rimChord));
      for (const t of tele) if (t.valid && distXZ(t.loc, oPos) < DW05.rimChord * 0.6) flashOut(t);
      particle(dim, "dw_ophan_rim", up(ca, 0.8));
      if (e % 2 === 0) particle(dim, "dw_ophan_sparks", up(ground, 0.3));
      if (e % 10 === 0) sound(dim, "dw_ophan_hum", oPos, 1, 0.85 + k2 * 0.15);
      for (const h of hostiles(dim, oPos, DW05.rimChord + DW05.sweepAltitude + 2, caster)) {
        if (hit.has(h.id)) continue;
        const l = h.location;
        if (l.y < ground.y - 1.5 || l.y > ground.y + DW05.rimHeight) continue;
        if (distToSegment(v(l.x, 0, l.z), v(ca.x, 0, ca.z), v(cb.x, 0, cb.z)) > DW05.rimHalfWidth) continue;
        const m = marks.get(h.id);
        if (!damage(h, m ? DW05.passMarkedDamage : DW05.passDamage, caster)) continue;
        hit.add(h.id);
        const sd = right(dir);
        const sign = (l.x - oPos.x) * sd.x + (l.z - oPos.z) * sd.z >= 0 ? 1 : -1;
        shove(h, mul(sd, sign), DW05.passKnock, DW05.passLift);
        particle(dim, "dw_ophan_impact", up(l, 1));
        sound(dim, "dw_ophan_bell", l, 1, m ? 1 + k2 * 0.08 : 0.85);
        if (m) testify(h);
      }
    }, tRun, tRun + DW05.passTicks);
    scene.at(tRun + DW05.passTicks, () => {
      for (const t of tele) flashOut(t);
    });
  }
  const tOphDone = tPass0 + DW05.passes * passLen;
  scene.at(tOphDone, () => {
    oph.state(OPH.survey);
  });
  const tC = 160;
  const cStart = up(add(gC.pos, mul(fwd, 1.5)), 1);
  const cStation = at(DW05.cherubStation);
  let cPos = cStart;
  let cYaw = gC.yaw;
  const cherub = scene.spawn("cherub", cStart, { yaw: cYaw, state: CHE.hidden });
  scene.at(tC, () => {
    cherub.state(CHE.arrive);
    sound(dim, "dw_cherub_arrive", gC.mouth, 1.5);
    particle(dim, "fx_flash", gC.mouth);
  });
  scene.span(tC, tC + 36, (p) => {
    cPos = bezier(cStart, up(lerp(cStart, cStation, 0.5), 2), cStation, smooth(p));
    cherub.move(cPos, cYaw);
  });
  function cherubFace(goal, from, ticks = 10) {
    scene.span(from, from + ticks, () => {
      cYaw += angleDelta(cYaw, goal) * 0.35;
      cherub.move(cPos, cYaw);
    });
  }
  const turn = () => sound(dim, "dw_cherub_turn", up(cPos, 10), 1.1);
  const tHuman = tC + secs(T2.cherub.arrive) - 2;
  let testimony = [];
  scene.at(tHuman, () => {
    cherub.state(CHE.human);
    cherubFace(yawTo(cPos, cluster()), scene.tick);
    sound(dim, "dw_cherub_human", up(cPos, 10), 1.4);
    testimony = region(DW05.maxMarks);
  });
  scene.every(3, (el) => {
    const hand = up(cPos, 12.5);
    particle(dim, "dw_cherub_glyph", hand);
    const p = Math.min(1, el / 14);
    for (const e of testimony) if (isAlive(e)) particle(dim, "dw_cherub_glyph", lerp(hand, up(e.location, 1.6), p));
  }, tHuman + 7, tHuman + secs(T2.cherub.humanCast));
  scene.at(tHuman + secs(T2.cherub.humanCast), () => {
    testimony.forEach((e, i) => {
      if (!isAlive(e)) return;
      const fresh = !marks.has(e.id);
      if (fresh) markEnemy(e);
      else testify(e);
      damage(e, DW05.testamentDamage, caster);
      particle(dim, "dw_halo", up(e.location, 1.2));
      sound(dim, "dw_cherub_glyph", e.location, 0.8, 1 + i * 0.05);
    });
    if (!testimony.length) for (let k2 = 0; k2 < 3; k2++) particle(dim, "dw_halo", up(polar(center, 3.5, k2 * 120), 1));
    line(dim, "dw_cherub_glyph", up(cPos, 12.5), up(center, 2), 6);
  });
  const tOx = tHuman + secs(T2.cherub.human) - 2;
  const tWard = tOx + secs(T2.cherub.oxLock);
  const tVerdict = 500;
  scene.at(tOx, () => {
    cherub.state(CHE.ox);
    turn();
    cherubFace(yawTo(cPos, caster.location), scene.tick);
    sound(dim, "dw_cherub_ox", up(cPos, 9), 1.4);
  });
  scene.at(tWard, () => {
    sound(dim, "dw_cherub_shield", caster.location, 1.2);
    burst(dim, "dw_cherub_feather", up(cPos, 6), 3, 6);
    line(dim, "dw_cherub_shield", up(cPos, 6), up(caster.location, 1), 6);
    const ward = addWard({
      scene,
      factor: 1 - DW05.wardStrength,
      pool: DW05.wardPool,
      protects: (e) => e.id === caster.id || e.typeId === "minecraft:player" && !CONFIG.targeting.pvp && distXZ(e.location, caster.location) <= DW05.wardRadius,
      onAbsorb: (_amount, _attacker, victim) => {
        if (victim.isValid) particle(dim, "dw_cherub_absorb", up(victim.location, 1));
        sound(dim, "dw_cherub_absorb", victim.isValid ? victim.location : caster.location, 0.9);
      },
      onBreak: () => {
        sound(dim, "dw_cherub_retaliate", caster.location, 0.6, 1.3);
        particle(dim, "dw_cherub_shatter", up(caster.location, 1));
      }
    });
    scene.at(tVerdict + 40, () => removeWard(ward));
  });
  scene.every(10, () => {
    if (!caster.isValid) return;
    particle(dim, "dw_cherub_shield", up(caster.location, 1));
    for (const p of dissolveProjectiles(scene, caster.location, 5)) particle(dim, "dw_cherub_absorb", p);
  }, tWard, tVerdict + 40);
  const tLion = tOx + secs(T2.cherub.ox) + 22;
  const tRoar2 = tLion + secs(T2.cherub.lionRoar);
  let roarFrom = cPos, roarTo = center;
  const cone = [];
  scene.at(tLion, () => {
    cherub.state(CHE.lion);
    turn();
    roarTo = cluster();
    cherubFace(yawTo(cPos, roarTo), scene.tick);
    const g0 = groundBelow(dim, up(cPos, -4), 24);
    for (const f of [0.45, 0.85]) cone.push(scene.spawn("telegraph", lerp(g0, roarTo, f), { kind: 0, size: 2.5 + f * 3, state: 1 }));
  });
  scene.at(tRoar2 - 4, () => sound(dim, "dw_cherub_lion", up(cPos, 9.5), 1.8));
  const roared = /* @__PURE__ */ new Set();
  scene.at(tRoar2, () => {
    roarFrom = add(up(cPos, 9.5), mul(fromYaw(cYaw), 1.8));
    particle(dim, "dw_cherub_breath", roarFrom);
    particle(dim, "dw_cherub_roar", roarFrom);
    cone.forEach((t) => flashOut(t));
  });
  for (let k2 = 0; k2 < 3; k2++) {
    const t0 = tRoar2 + k2 * 4;
    let ringA;
    let travel = 20;
    scene.at(t0, () => {
      const end = up(add(roarTo, mul(norm(flat(sub(roarTo, roarFrom))), 4)), 1.5);
      travel = Math.max(8, Math.round(dist(roarFrom, end) / DW05.roarSpeed));
      const yaw = yawTo(roarFrom, end);
      ringA = scene.spawn("dw_cherub_roar", roarFrom, { yaw, state: 1 });
      sound(dim, "dw_cherub_ring", roarFrom, 1, 0.9 + k2 * 0.1);
      const from = roarFrom;
      const ground0 = flat(from);
      const dirXZ = norm(flat(sub(end, from)));
      const reach = distXZ(from, end);
      scene.span(t0, t0 + travel, (p, el) => {
        const pos = lerp(from, end, p);
        ringA?.move(pos, yaw);
        if (el % 3 === 0) particle(dim, "dw_cherub_roar", pos);
        if (k2 > 0) return;
        const front = reach * p;
        for (const e of region()) {
          if (roared.has(e.id)) continue;
          const rel = sub(flat(e.location), ground0);
          const along = dot(rel, dirXZ);
          if (along > front + 0.5 || along < front - 3) continue;
          const lat = Math.hypot(rel.x - dirXZ.x * along, rel.z - dirXZ.z * along);
          if (lat > DW05.roarHalfWidthNear + (DW05.roarHalfWidthFar - DW05.roarHalfWidthNear) * clamp(along / Math.max(reach, 1), 0, 1)) continue;
          roared.add(e.id);
          damage(e, boost(e, DW05.roarDamage, DW05.markBonus), caster);
          shove(e, dirXZ, DW05.roarKnock, DW05.roarLift);
          particle(dim, "dw_spark", up(e.location, 1));
          testify(e);
        }
      });
      scene.at(t0 + travel, () => {
        if (ringA) {
          ring(dim, "dw_glyph_rise", ringA.loc, 2.5, 6);
          scene.despawn(ringA);
        }
      });
    });
  }
  const tEagle = tRoar2 + 15;
  const dives = T2.cherub.eagleThrust.map((s) => tEagle + secs(s));
  scene.at(tEagle, () => {
    cherub.state(CHE.eagle).skin(1);
    turn();
    cherubFace(yawTo(cPos, cluster()), scene.tick);
    burst(dim, "dw_cherub_feather", up(cPos, 9), 4, 6);
  });
  scene.at(tEagle + 10, () => sound(dim, "dw_cherub_eagle", up(cPos, 11), 1.6));
  function bladeTargets(wave) {
    const out = [];
    const used = /* @__PURE__ */ new Set();
    for (const m of liveMarks()) {
      if (out.length >= DW05.bladesPerWave) break;
      out.push({ e: m.e, at: groundBelow(dim, m.e.location) });
      used.add(m.e.id);
    }
    for (const e of region()) {
      if (out.length >= DW05.bladesPerWave) break;
      if (!used.has(e.id)) out.push({ e, at: groundBelow(dim, e.location) });
    }
    if (!out.length) {
      const c = cluster();
      [0, 1, 2].forEach((k2) => out.push({ at: polar(c, 3 + wave * 2, k2 * 120 + wave * 60) }));
    }
    return out;
  }
  function blade(target, diveAt, idx) {
    let p0 = target.at;
    const bYaw = cYaw + idx * 47;
    const b = scene.spawn("dw_cherub_blade", up(p0, DW05.bladeHeight), { yaw: bYaw, state: BLADE2.form });
    const sigil = scene.spawn("telegraph", p0, { kind: 0, size: DW05.bladeRadius, state: 1 });
    sound(dim, "dw_cherub_blade", up(p0, DW05.bladeHeight), 0.9, 0.95 + idx * 0.04);
    line(dim, "dw_cherub_glyph", up(cPos, 11), up(p0, DW05.bladeHeight), 5);
    scene.after(secs(T2.cherub.bladeForm), () => b.state(BLADE2.aim));
    scene.every(1, () => {
      if (target.e && isAlive(target.e)) {
        p0 = groundBelow(dim, target.e.location);
        sigil.move(p0);
      }
      b.move(up(p0, DW05.bladeHeight), bYaw);
    }, scene.tick + 1, diveAt);
    scene.at(diveAt, () => {
      b.state(BLADE2.dive);
      sound(dim, "dw_cherub_dive", up(p0, DW05.bladeHeight * 0.5), 1);
    });
    scene.span(diveAt, diveAt + DW05.diveTicks, (p) => {
      const pos = up(p0, DW05.bladeHeight * (1 - easeIn(p)));
      b.move(pos, bYaw);
      particle(dim, "dw_cherub_trail", up(pos, 1.5));
    });
    scene.at(diveAt + DW05.diveTicks, () => {
      b.move(p0, bYaw).state(BLADE2.shatter);
      sigil.state(3);
      sound(dim, "dw_cherub_impact", p0, 1.1);
      particle(dim, "dw_cherub_shatter", up(p0, 0.6));
      particle(dim, "dw_ring", up(p0, 0.2));
      for (const e of hostiles(dim, p0, DW05.bladeRadius, caster)) {
        if (!damage(e, boost(e, DW05.bladeDamage, DW05.bladeMarkBonus), caster)) continue;
        knockback(e, p0, 0.6, 0.3);
        testify(e);
      }
      scene.after(secs(T2.cherub.bladeShatter) + 2, () => {
        scene.despawn(b);
        scene.despawn(sigil);
      });
    });
  }
  dives.forEach((diveAt, wave) => {
    scene.at(diveAt - DW05.bladeWarn, () => bladeTargets(wave).forEach((t, i) => blade(t, diveAt, i + wave * 3)));
  });
  scene.at(tEagle + secs(T2.cherub.eagle), () => cherub.state(CHE.idle));
  const tS = 190;
  const sStart = up(add(gS.pos, mul(fwd, 1.5)), 1.5);
  const sStation = at(DW05.seraphStation);
  let sPos = sStart;
  const sYaw = yawTo(sStation, view);
  const seraph = scene.spawn("seraph", sStart, { yaw: sYaw, state: SER.hidden });
  scene.at(tS, () => {
    seraph.state(SER.arrive);
    sound(dim, "dw_seraph_arrive", gS.mouth, 1.5);
    particle(dim, "fx_flash", gS.mouth);
  });
  scene.span(tS, tS + secs(T2.seraph.arrive), (p) => {
    sPos = bezier(sStart, up(lerp(sStart, sStation, 0.5), 3), sStation, smooth(p));
    seraph.move(sPos, sYaw);
  });
  scene.at(tS + secs(T2.seraph.arrive), () => seraph.state(SER.veiled));
  const tUnfurl = tS + secs(T2.seraph.arrive) + 6;
  scene.at(tUnfurl, () => {
    seraph.state(SER.unfurl);
    sound(dim, "dw_unfurl", sPos, 1.2);
    burst(dim, "dw_feather", up(sPos, 7), 6, 8);
  });
  scene.at(tUnfurl + secs(T2.seraph.unfurl), () => seraph.state(SER.open));
  const chantAt = [262, 296, 330];
  const chanted = [/* @__PURE__ */ new Set(), /* @__PURE__ */ new Set(), /* @__PURE__ */ new Set()];
  chantAt.forEach((t0, i) => {
    scene.at(t0, () => {
      seraph.state(SER.chant1 + i).skin(1);
      sound(dim, `dw_chant${i + 1}`, sPos, 1.5);
      ring(dim, "dw_glyph_rise", up(sPos, 7), 5, 8, i * 20);
    });
    scene.at(t0 + T2.seraph.chantLead[i] - DW05.columnWarn + 8, () => judge(i));
  });
  function judge(i) {
    const spots = [];
    for (const m of liveMarks()) if (spots.length < DW05.maxColumns) spots.push({ e: m.e, loc: groundBelow(dim, m.e.location) });
    for (const e of region()) {
      if (spots.length >= DW05.maxColumns) break;
      if (!marks.has(e.id)) spots.push({ e, loc: groundBelow(dim, e.location) });
    }
    if (!spots.length) {
      const c = cluster();
      [0, 1, 2].forEach((k2) => spots.push({ loc: polar(c, 4, k2 * 120 + 30 + i * 40) }));
    }
    for (const s of spots) {
      const r = DW05.columnRadius * (1 + i * 0.1);
      const warn = scene.spawn("telegraph", s.loc, { kind: 0, size: r, state: 1 });
      let p0 = s.loc;
      line(dim, "dw_glyph_fall", up(sPos, 6), up(p0, 8), 4);
      scene.every(1, () => {
        if (s.e && isAlive(s.e)) {
          p0 = groundBelow(dim, s.e.location);
          warn.move(p0);
        }
      }, scene.tick, scene.tick + DW05.columnWarn - 4);
      scene.after(DW05.columnWarn - 6, () => {
        const col = scene.spawn("dw_column", p0, { kind: i === 1 ? 1 : 0, size: r / 1.3 * 1.15, state: 1 });
        sound(dim, "dw_column", p0, 1.1, 0.95 + i * 0.08);
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      });
      scene.after(DW05.columnWarn, () => {
        flashOut(warn);
        particle(dim, "dw_ring", up(p0, 0.2));
        particle(dim, "dw_pillar_burst", up(p0, 0.3));
        particle(dim, "dw_spark", up(p0, 1));
        for (const e of hostiles(dim, p0, r, caster)) {
          if (chanted[i].has(e.id)) continue;
          if (!damage(e, DW05.chantDamage[i], caster)) continue;
          chanted[i].add(e.id);
          if (!marks.has(e.id)) markEnemy(e);
          else testify(e);
        }
      });
    }
  }
  scene.at(chantAt[2] + 32, () => seraph.state(SER.open));
  const tIII = 370;
  const thP = at(DW05.throne);
  const seat = up(thP, 5.6);
  const throne = scene.spawn("dw5_throne", thP, { yaw: yawTo(thP, view), state: THR.hidden });
  const sPost = at(DW05.seraphPost), cPost = at(DW05.cherubPost), oPost = at(DW05.ophanPost);
  scene.at(tIII, () => {
    oph.state(OPH.survey);
    cherub.state(CHE.idle);
    const s0 = sPos, c0 = cPos, o0 = oPos;
    scene.span(tIII, tIII + 30, (p) => {
      const q2 = smooth(p);
      sPos = bezier(s0, up(lerp(s0, sPost, 0.5), 3), sPost, q2);
      seraph.move(sPos, yawTo(sPost, view));
      cPos = lerp(c0, cPost, q2);
      cYaw += angleDelta(cYaw, yawTo(cPost, view)) * 0.2;
      cherub.move(cPos, cYaw);
      oPos = bezier(o0, up(lerp(o0, oPost, 0.5), 3), oPost, q2);
      oYaw += angleDelta(oYaw, yawTo(oPost, view)) * 0.2;
      oph.move(oPos, oYaw);
    });
  });
  sentences.forEach((s, k2) => {
    scene.at(tIII + k2 * 6, () => {
      s.state(SEN.gather);
      sound(dim, "dw5_fold", up(center, DW05.sentences[k2].up), 1, 0.9 + k2 * 0.1);
    });
    scene.at(tIII + k2 * 6 + secs(T2.gather) + 2, () => scene.despawn(s));
  });
  const tThrone = tIII + 10;
  scene.at(tThrone, () => {
    throne.state(THR.assemble);
    sound(dim, "dw5_throne_form", seat, 2);
    seraph.skin(1);
    cherub.skin(1);
    oph.skin(1);
    lights.place(up(thP, 7), LIGHT);
  });
  scene.every(2, (el) => {
    const src = [up(sPos, 7), up(cPos, 10), oPos];
    const ph = el / 2 % 8 / 8;
    for (const s of src) {
      particle(dim, "dw5_stream", lerp(s, seat, ph));
      particle(dim, "dw5_stream", lerp(s, seat, (ph + 0.5) % 1));
    }
  }, tThrone, tThrone + 50);
  scene.at(tThrone + secs(T2.assemble), () => {
    throne.state(THR.idle);
    particle(dim, "dw5_seat_glow", seat);
    burst(dim, "dw_glyph_rise", up(thP, 8), 5, 8);
  });
  const tSpeak = tThrone + secs(T2.assemble) + 4;
  scene.at(tSpeak, () => {
    throne.state(THR.declare);
    particle(dim, "dw5_seat_glow", seat);
  });
  const letters = [];
  const lineBase = add(center, mul(fwd, DW05.throne.forward - DW05.lineForward));
  const lYaw = yawTo(lineBase, view);
  DW05.lineHeights.forEach((h, l) => {
    letters.push([]);
    const t0 = tSpeak + 4 + l * 12;
    scene.at(t0, () => sound(dim, "dw5_speak", up(lineBase, h), 1.8, 1 + l * 0.12));
    for (let j = 0; j < DW05.lettersPerLine; j++) {
      const off = (j - (DW05.lettersPerLine - 1) / 2) * DW05.letterSpacing;
      const p = up(add(lineBase, mul(side, off)), h);
      scene.at(t0 + j * 2, () => {
        const a = scene.spawn("dw5_letter", p, { yaw: lYaw, kind: (l * 5 + j * 2) % LETTER_KINDS, state: LET.ignite });
        letters[l][j] = a;
        particle(dim, "fx_flash", up(p, 2));
        if (j % 2 === 0) sound(dim, "dw5_ignite", p, 1, 0.9 + j * 0.06);
        scene.after(secs(T2.ignite), () => a.state(LET.hold));
      });
    }
  });
  const areas = [];
  scene.at(tSpeak + 8, () => {
    const pick = [...liveMarks().map((m) => m.e), ...region().filter((e) => !marks.has(e.id))];
    for (const e of pick) {
      if (areas.length >= DW05.lineHeights.length * DW05.lettersPerLine) break;
      const g = groundBelow(dim, e.location);
      if (areas.some((a) => distXZ(a.at, g) < DW05.areaRadius)) continue;
      areas.push({ at: g, e, letters: 0, landed: 0 });
    }
    if (!areas.length) {
      const c = cluster();
      areas.push({ at: c, letters: 0, landed: 0 });
      for (let k2 = 0; k2 < 4; k2++) areas.push({ at: groundBelow(dim, up(polar(c, 6, k2 * 90 + 45), 3), 12), letters: 0, landed: 0 });
    }
    for (const a of areas) a.sigil = scene.spawn("telegraph", a.at, { kind: 0, size: DW05.areaRadius, state: 4 });
    scene.after(40, () => areas.forEach((a) => a.sigil?.state(2)));
  });
  scene.every(1, () => {
    for (const a of areas) if (a.e && isAlive(a.e)) {
      a.at = groundBelow(dim, a.e.location);
      a.sigil?.move(a.at);
    }
  }, tSpeak + 9, tVerdict - DW05.plungeTicks);
  scene.at(tVerdict - secs(T2.cherub.verdictHit), () => {
    cherub.state(CHE.verdict);
    sound(dim, "dw_cherub_turn", up(cPos, 10), 1.2);
  });
  scene.at(tVerdict - T2.seraph.verdictHitTicks, () => seraph.state(SER.verdict));
  scene.at(tVerdict - secs(T2.ophan.verdictHit), () => {
    oph.state(OPH.verdict);
    sound(dim, "dw_ophan_verdict", oPos, 1.4);
  });
  scene.at(tVerdict - 3, () => sound(dim, "dw5_verdict", up(center, 6), 2.2));
  const struck = /* @__PURE__ */ new Map();
  const bonused = /* @__PURE__ */ new Set();
  let q = 0;
  for (let l = 0; l < DW05.lineHeights.length; l++) {
    for (let j = 0; j < DW05.lettersPerLine; j++, q++) {
      const idx = q;
      const tPl = tVerdict - DW05.plungeTicks + idx * DW05.plungeStagger;
      let from = center, target, a;
      scene.at(tPl, () => {
        a = letters[l]?.[j];
        if (!a || !a.valid || !areas.length) return;
        target = areas[idx % areas.length];
        target.letters++;
        from = a.loc;
        a.state(LET.plunge);
        sound(dim, "dw5_letter_fall", from, 1.3, 0.92 + idx % 5 * 0.05);
      });
      scene.span(tPl, tPl + DW05.plungeTicks, (p) => {
        if (!a || !target) return;
        const pos = lerp(from, target.at, easeIn(p));
        a.move(pos);
        particle(dim, "dw5_edict_trail", up(pos, 3));
      });
      scene.at(tPl + DW05.plungeTicks, () => {
        if (!a || !target) return;
        const ar = target, letter = a;
        letter.move(ar.at).state(LET.impact);
        scene.after(secs(T2.impact) + 2, () => scene.despawn(letter));
        particle(dim, "dw5_edict_impact", up(ar.at, 0.2));
        particle(dim, "dw5_edict_letters", up(ar.at, 1));
        particle(dim, "dw_pillar_burst", up(ar.at, 0.3));
        particle(dim, "fx_flash", up(ar.at, 1.5));
        for (const e of hostiles(dim, ar.at, DW05.verdictRadius, caster)) {
          const n = struck.get(e.id) ?? 0;
          if (n >= DW05.maxLetterHits) continue;
          let dmg = DW05.verdictDamage;
          if (marks.has(e.id) && !bonused.has(e.id)) {
            dmg += DW05.verdictMarkBonus;
            bonused.add(e.id);
          }
          if (!damage(e, dmg, caster)) continue;
          struck.set(e.id, n + 1);
          knockback(e, ar.at, DW05.verdictKnock, DW05.verdictLift);
        }
        ar.landed++;
        if (ar.landed >= ar.letters) flashOut(ar.sigil);
      });
    }
  }
  scene.at(tVerdict, () => {
    const fc = areas.length ? areas[0].at : center;
    const col = scene.spawn("dw_column", fc, { kind: 2, size: 2.6, state: 1 });
    scene.after(10, () => col.state(2));
    scene.after(26, () => col.state(3));
    scene.after(40, () => scene.despawn(col));
    ring(dim, "dw_glyph_fall", up(fc, 7), 3, 8);
    for (const e of hostiles(dim, fc, DW05.finalColumnRadius, caster)) damage(e, DW05.finalColumnDamage, caster);
    particle(dim, "fx_flash", oPos);
    burst(dim, "dw_ophan_impact", oPos, 3, 4);
    for (const m of liveMarks()) {
      line(dim, "dw_ophan_scan", oPos, up(m.e.location, 1.2), 8);
      damage(m.e, DW05.gazeDamage, caster);
      particle(dim, "dw_ophan_eye", up(m.e.location, 3.4));
    }
    const cg = groundBelow(dim, cPos, 24);
    particle(dim, "dw_cherub_quake", up(cg, 0.2));
    particle(dim, "dw_cherub_roar", up(cPos, 9.5));
    ring(dim, "dw_cherub_feather", up(cPos, 6), 4, 6);
    particle(dim, "fx_shock", up(center, 0.4));
  });
  const tAfter = tVerdict + q * DW05.plungeStagger + 4;
  scene.at(tAfter, () => {
    for (const m of marks.values()) if (m.mark.valid) {
      const mk = m.mark;
      mk.state(MARK2.burst);
      scene.after(8, () => scene.despawn(mk));
    }
    for (const a of areas) flashOut(a.sigil);
  });
  scene.at(tVerdict + secs(T2.ophan.verdict), () => oph.state(OPH.survey));
  const tW = Math.max(540, tAfter + 4);
  scene.at(tW, () => sound(dim, "dw5_withdraw", up(center, 12), 1.8));
  function withdraw(actor, getPos, setPos, g, start, departState, departLen, yawOfMove) {
    const into = up(add(g.pos, mul(fwd, 1.5)), g === gO ? 0 : 1.5);
    scene.at(start, () => {
      actor.skin(0);
      const p0 = getPos();
      scene.span(start, start + 20, (p) => {
        const pos = bezier(p0, up(lerp(p0, into, 0.5), 2), into, smooth(p));
        setPos(pos);
        actor.move(pos, yawOfMove());
      });
    });
    const tDep = start + 16;
    scene.at(tDep, () => {
      actor.state(departState);
      particle(dim, "fx_flash", g.mouth);
      burst(dim, "dw_glyph_rise", g.mouth, 2.5, 6);
    });
    scene.at(tDep + secs(departLen) + 2, () => scene.despawn(actor));
    const tClose = tDep + secs(departLen) - 4;
    scene.at(tClose, () => {
      g.a.state(GATE.close);
      sound(dim, "dw5_gate_close", g.mouth, 1.6);
    });
    scene.at(tClose + secs(T2.close), () => {
      g.a.state(GATE.fold);
      sound(dim, "dw5_fold", g.mouth, 1.4);
      particle(dim, "dw5_fold", g.mouth);
    });
    scene.at(tClose + secs(T2.close) + secs(T2.fold) + 2, () => {
      burst(dim, "dw_glyph_rise", up(g.mouth, 3), 3, 6);
      scene.despawn(g.a);
    });
    return tClose + secs(T2.close) + secs(T2.fold) + 2;
  }
  withdraw(seraph, () => sPos, (p) => {
    sPos = p;
  }, gS, tW, SER.depart, T2.seraph.depart, () => yawTo(sPos, view));
  withdraw(cherub, () => cPos, (p) => {
    cPos = p;
  }, gC, tW + 16, CHE.depart, T2.cherub.depart, () => cYaw);
  const tLastGate = withdraw(oph, () => oPos, (p) => {
    oPos = p;
  }, gO, tW + 32, OPH.depart, T2.ophan.depart, () => oYaw);
  const tUnmake = tLastGate - 20;
  scene.at(tUnmake, () => {
    throne.state(THR.unmake);
    sound(dim, "dw5_unmake", seat, 1.8);
    burst(dim, "dw_glyph_rise", up(thP, 6), 6, 10);
  });
  scene.at(tUnmake + 20, () => ring(dim, "dw5_stream", up(thP, 12), 5, 10));
  scene.at(tUnmake + secs(T2.unmake) + 2, () => {
    scene.despawn(throne);
    circle.state(3);
  });
  scene.at(tUnmake + secs(T2.unmake) + 16, () => scene.despawn(circle));
  scene.endAt(tUnmake + secs(T2.unmake) + 22);
});

// src/config/dw06.ts
var DW06 = {
  // ---- Phase I: the silence before all things
  /** Radius of the spell's domain around its centre (blocks).  The centre is the aimed point, kept 14-20 blocks ahead. */
  domainRadius: 19,
  /** How far the focus may snap from the aim point to an enemy. */
  focusSnap: 14,
  /** Most enemies that receive a sacred mark. */
  maxMarks: 8,
  // ---- Phase II: the first utterance (letters land as structures)
  /** Impact radius / damage / knockback of each structure kind when it lands:
   *  0 column, 1 arch (per pier), 2 bridge (swing sweep), 3 gate, 4 platform (shove only), 5 celestial. */
  landRadius: [2.6, 2.2, 6.5, 4, 3.2, 4],
  landDamage: [10, 8, 8, 12, 0, 7],
  landKnock: [1.2, 1, 1.6, 1.8, 1, 0.8],
  /** Every landing also sends a shock along the ground: lighter damage out to this radius. */
  landShockRadius: 7,
  landShockDamage: 4,
  /** Columns and celestial formations land on an enemy if one is within this distance of their slot... */
  seekRadius: 7,
  /** ...and at least this far from the caster (nothing tall is built next to the caster). */
  seekMinDist: 10,
  /** Height (blocks, at full size) of barrier obstruction for columns, arch piers and gate pylons. */
  barrierHeight: [9, 8, 0, 10, 0, 0],
  /** Allies within this horizontal distance of a platform or bridge take reduced damage (cover). */
  coverRadius: 4.5,
  coverFactor: 0.6,
  /** Celestial formations fire a ray at (up to two) enemies within this radius every pulse while they stand. */
  celestialPulseRadius: 12,
  celestialPulseDamage: 3,
  celestialPulseEvery: 20,
  // ---- Phase III: the seven laws
  /** I Containment: ring of written walls around the densest hostile region (kept this far from the caster). */
  containRadius: 6,
  containMinDist: 14,
  containPull: 13,
  containPullStrength: 0.9,
  /** How long the containment walls (and their barriers) stand, in ticks. */
  containTicks: 220,
  /** II Station: the platforms glide to a defensive line just in front of the enemy, no nearer than this to the
   *  caster (blocks), this far either side of its middle, and settle at this size; a two-high barrier bar spans it. */
  stationMin: 10.5,
  stationSpread: 7.5,
  stationSize: 0.45,
  /** Once the line stands, allies within this radius of the caster's place are behind it (cover). */
  stationCover: 7,
  /** III Direction: moving text walls -- damage, half-length of the wall, half-depth of the hit band. */
  directionDamage: 7,
  directionHalfWidth: 3,
  directionBand: 1.6,
  directionTicks: 32,
  /** IV Stillness: restraint duration, then lingering slowness (amplifier). */
  stillTicks: 60,
  stillSlowTicks: 100,
  stillSlowAmp: 3,
  /** V Refuge: allied zone radius, damage factor inside it, instant heal and regen per 2 s. */
  refugeRadius: 6,
  refugeFactor: 0.4,
  refugeHeal: 6,
  refugeRegen: 2,
  /** VI Sequence: each structure strikes the enemies around it in turn, and looses a bolt at the nearest enemy
   *  beyond that (within sequenceReach). */
  sequenceRadius: 4.5,
  sequenceReach: 12,
  sequenceDamage: 5,
  /** VII Judgment: radius of the designated finale region (and its telegraph), kept this far from the caster. */
  finalRadius: 7,
  finalMinDist: 14,
  // ---- Phase IV: let it be written (descending lines)
  sweepDamage: 10,
  /** Half-length of the sweeping line (blocks) and how far it rolls away from the caster. */
  sweepHalfLength: 6.5,
  sweepTravel: 7,
  ringDamage: 10,
  ringMaxRadius: 12,
  latticeDamage: 9,
  latticeRadius: 2.4,
  spiralTickDamage: 3,
  spiralFinalDamage: 10,
  spiralPull: 0.55,
  /** Finale: immense white-gold formation. */
  finalDamage: 32,
  /** Extra finale damage for enemies judged by Law VII. */
  judgedBonus: 14,
  finalKnockback: 2.2
};

// src/spells/dw06_word_before_creation.ts
var BOOK = { arrive: 1, open: 2, unbind: 3, layered: 4, gather: 5, close: 6, vanish: 7 };
var PAGE = { manifest: 1, idle: 2, split: 3, reform: 4, fold: 5, slip: 6 };
var GLYPH = { draw: 1, fall: 2, land: 3 };
var ED = { assemble: 1, hold: 2, swing: 3, strike: 4, unwrite: 5 };
var WALL = { rise: 1, hold: 2, sink: 3 };
var DOME = { form: 1, hold: 2, fade: 3 };
var BOUND = { inscribe: 1, hold: 2, unwrite: 3 };
var TAB = { form: 1, idle: 2, declare: 3, shed: 4, ret: 5 };
var LINE = { assemble: 1, hold: 2, strike: 3, unwrite: 4 };
var TEL = { warn: 1, hold: 2, flash: 3, slow: 4 };
var LIGHTCOL = { descend: 1, hold: 2, dissolve: 3 };
var CIRCLE = { form: 1, hold: 2, fade: 3 };
var MARK3 = { appear: 1, burst: 3 };
var DEG = Math.PI / 180;
var UPV = { x: 0, y: 1, z: 0 };
var EYE = 1.62;
var PAGE_U = 2.4 / 16;
var PAGE_TILT = 7 * DEG;
var ED_U = 2 / 16;
var COLUMN = 0;
var ARCH = 1;
var BRIDGE = 2;
var GATE2 = 3;
var PLATFORM = 4;
var CELESTIAL = 5;
var ED_H = [11, 11.4, 7, 13.9, 6, 11];
var STAGE_MIN = 14;
var STAGE_MAX = 20;
var PAGE_BACK = 26;
var PAGE_LIFT = 0.6;
var BOOK_HOVER = 1.2;
var BOOK_START = 0.8;
var BOOK_LECTERN = 1;
var BOOK_FINAL = 1;
var TAB_LIFT = 3.4;
var TAB_RISE = 15;
var TAB_BACK = 6;
var FX_CAP = 88;
var T_OPEN = 56;
var T_UNBIND = 64;
var T_SEAM = 84;
var T_LAYERED = 104;
var T_GLIDE = 100;
var GLIDE = 46;
var T_WRITE0 = 140;
var WRITE_AT = [0, 26, 50, 72, 92, 110, 126, 141, 155, 168];
var DRAW = 20;
var FALL = 18;
var T_SPLIT = 384;
var T_TAB = T_SPLIT + 8;
var TAB_FLY = 28;
var T_LAW0 = 444;
var LAW_STEP = 22;
var T_RISE = T_LAW0 + 7 * LAW_STEP;
var T_FINAL = T_RISE + 238;
var T_UNW = T_FINAL + 14;
var T_TABRET = T_FINAL + 12;
var TAB_RET = 24;
var T_REFORM = T_TABRET + TAB_RET - 2;
var T_FOLD = T_REFORM + 22;
var T_FLY = T_FOLD + 50;
var FLY2 = 20;
var T_SLIP = T_FLY + FLY2;
var T_CLOSE = T_SLIP + 2;
var T_VANISH = T_CLOSE + 36;
var T_END = T_VANISH + 40;
var PLAN = [
  { kind: COLUMN, u: -5, v: 0.5, elev: 13, cap: 0.7, seek: true, a: -14, b: 34 },
  { kind: COLUMN, u: 5, v: 0.5, elev: 13, cap: 0.7, seek: true, a: 26, b: 34 },
  { kind: ARCH, u: -9.8, v: 4, elev: 12, cap: 0.75, a: -34, b: 34 },
  { kind: ARCH, u: 9.8, v: 4, elev: 12, cap: 0.75, a: 46, b: 34 },
  { kind: GATE2, u: -9, v: 10.5, elev: 12, cap: 0.75, a: 6, b: 34 },
  { kind: BRIDGE, u: 0, v: 13, elev: 7, cap: 0.7, a: 6, b: 63 },
  { kind: PLATFORM, u: -8.8, v: -3.6, elev: 10, cap: 0.55, a: -34, b: 63 },
  { kind: PLATFORM, u: 8.8, v: -3.6, elev: 10, cap: 0.55, a: 46, b: 63 },
  { kind: CELESTIAL, u: 8, v: 10, elev: 11, cap: 0.75, seek: true, a: 26, b: 63 },
  { kind: COLUMN, u: 13, v: 8, elev: 12, cap: 0.75, seek: true, a: -14, b: 63 }
];
var rnd = (k2) => {
  const x = Math.sin(k2 * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};
var dw06_word_before_creation_default = defineSpell("dw06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center: aimC0, target } = focus(caster, aim, DW06.focusSnap);
  const c0 = { ...caster.location };
  const aimC = groundBelow(dim, aimC0);
  let fwd = norm(flat(sub(aimC, c0)));
  if (distXZ(aimC, c0) < 3) fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);
  const ground = (p) => groundBelow(dim, up(p, 3), 12);
  const Ds = clamp(distXZ(aimC, c0), STAGE_MIN, STAGE_MAX);
  const at = (f, r, y = c0.y) => ({ x: c0.x + fwd.x * f + rt.x * r, y, z: c0.z + fwd.z * f + rt.z * r });
  const G = (f, r, h = 0) => up(ground(at(f, r)), h);
  const center = G(Ds, 0);
  const yb = Math.max(c0.y, center.y);
  const SKY = (f, r, h) => at(f, r, yb + h);
  const faceOrigin = (p) => yawOf(sub(c0, p));
  const casterPos = () => caster.isValid ? caster.location : c0;
  const domain = () => hostiles(dim, center, DW06.domainRadius, caster);
  const isAlly = (e) => e.typeId === "minecraft:player" && (e.id === caster.id || !CONFIG.targeting.pvp);
  const lateral = (p) => (p.x - c0.x) * rt.x + (p.z - c0.z) * rt.z;
  const depth = (p) => (p.x - c0.x) * fwd.x + (p.z - c0.z) * fwd.z;
  const awayFrom = (p, minD) => {
    const d = distXZ(p, c0);
    if (d >= minD) return p;
    const dir = d < 0.5 ? fwd : norm(flat(sub(p, c0)));
    return ground(add(c0, mul(dir, minD)));
  };
  const centroid = (es, fallback) => {
    if (!es.length) return fallback;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return mul(s, 1 / es.length);
  };
  const enemyFront = () => {
    const es = domain();
    if (!es.length) return { E: G(Ds + 2, 0), near: Ds };
    return { E: ground(centroid(es, center)), near: Math.min(...es.map((e) => depth(e.location))) };
  };
  const clampDist = (p, lo, hi) => {
    const d = distXZ(p, c0);
    const dir = d < 0.5 ? fwd : norm(flat(sub(p, c0)));
    return ground(add(c0, mul(dir, clamp(d, lo, hi))));
  };
  let fxT = -1, fxN = 0;
  const fx = (id, p) => {
    if (scene.tick !== fxT) {
      fxT = scene.tick;
      fxN = 0;
    }
    if (fxN >= FX_CAP) return;
    fxN++;
    particle(dim, id, p);
  };
  const fxLine = (id, a, b, n) => {
    for (let i = 0; i < n; i++) fx(id, lerp(a, b, n === 1 ? 0.5 : i / (n - 1)));
  };
  const fxRing = (id, c, r, n, phase = 0) => {
    for (let i = 0; i < n; i++) {
      const a = (phase + 360 * i / n) * DEG;
      fx(id, { x: c.x + Math.cos(a) * r, y: c.y, z: c.z + Math.sin(a) * r });
    }
  };
  const fxBurst = (id, c, r, n) => {
    for (let i = 0; i < n; i++) {
      const y = 1 - 2 * (i + 0.5) / n, rr = Math.sqrt(1 - y * y) * r, a = i * 2.39996;
      fx(id, { x: c.x + Math.cos(a) * rr, y: c.y + y * r, z: c.z + Math.sin(a) * rr });
    }
  };
  const fxFlow = (id, path, e, n, speed = 0.05) => {
    for (let j = 0; j < n; j++) fx(id, path((e * speed + j / n) % 1));
  };
  const snd = (id, p, vol = 1, pitch = 1) => sound(dim, id, p, vol, pitch);
  const edifices = [];
  const tablets = [];
  const hovering = [];
  let page;
  let pageGlitter = false;
  let tabletsShown = true;
  let boundaryOn = false;
  let refugeOn = false;
  let refugeAt = c0;
  let finalAt = awayFrom(center, DW06.finalMinDist);
  let stD = Ds - 2;
  const Lp = clamp(Ds + PAGE_BACK, 38, 46);
  const pageO = SKY(Lp, 0, PAGE_LIFT);
  const pd = norm(flat(sub(c0, pageO)));
  const pageYaw = yawOf(pd);
  const pr = right(pd);
  const pageUp = add(mul(UPV, Math.cos(PAGE_TILT)), mul(pd, -Math.sin(PAGE_TILT)));
  const pageN = add(mul(pd, Math.cos(PAGE_TILT)), mul(UPV, Math.sin(PAGE_TILT)));
  const pagePt = (a, b, off = 0) => add(add(add(pageO, mul(pr, -a * PAGE_U)), mul(pageUp, b * PAGE_U)), mul(pageN, off));
  const BR = 18.75;
  const ringPt = (bbDeg, h = 0.4) => {
    const a = bbDeg * DEG;
    return up(add(add(center, mul(rt, -Math.cos(a) * BR)), mul(fwd, Math.sin(a) * BR)), h);
  };
  const b1 = G(Ds - 1, 0, BOOK_HOVER);
  const b2 = SKY(Lp - 3.2, 0, 0.9);
  const bF = G(Ds + 0.5, 0, 1.6);
  let bookAt = b1;
  let bookShows = true;
  scene.every(1, () => {
    const t = scene.tick;
    const lively = t >= T_WRITE0 && t < T_UNW;
    const nm = t < T_WRITE0 ? 9 : lively ? 13 : 8;
    for (let i = 0; i < nm; i++) {
      const k2 = t * 13 + i * 3.7;
      const a = rnd(k2) * 2 * Math.PI, r = Math.sqrt(rnd(k2 + 1.3)) * DW06.domainRadius;
      const p = { x: center.x + Math.cos(a) * r, y: center.y + 0.5 + rnd(k2 + 2.1) * 7, z: center.z + Math.sin(a) * r };
      if (distXZ(p, c0) > 3) fx("dw6_motes", p);
    }
    if (lively) {
      for (let i = 0; i < 6; i++) {
        const k2 = t * 5.3 + i * 1.9;
        fx("dw6_script", { x: center.x + (rnd(k2) - 0.5) * 28, y: center.y + 4 + rnd(k2 + 0.7) * 6, z: center.z + (rnd(k2 + 1.4) - 0.2) * 22 });
      }
    }
    if (boundaryOn) {
      fx("dw6_script", ringPt(rnd(t * 3.1) * 360, 0.3));
      if (lively) fx("dw6_script", ringPt(rnd(t * 4.3 + 0.5) * 360, 0.3));
      if (t % 3 === 0) fx("dw6_glint", ringPt(rnd(t * 5.7) * 360, 1));
    }
    for (let j = 0; j < edifices.length; j++) {
      const ed = edifices[j];
      if (!ed.alive) continue;
      const hgt = ED_H[ed.kind] * ed.size, k2 = t * 1.7 + j * 9.1, w = 2.6 * ed.size;
      fx("dw6_script", { x: ed.at.x + (rnd(k2) - 0.5) * w, y: ed.at.y + 0.3 + rnd(k2 + 0.4) * hgt, z: ed.at.z + (rnd(k2 + 0.8) - 0.5) * w });
      if ((t + j) % 2 === 0) fx("dw6_motes", { x: ed.at.x + (rnd(k2 + 3) - 0.5) * w * 1.6, y: ed.at.y + 0.4, z: ed.at.z + (rnd(k2 + 3.5) - 0.5) * w * 1.6 });
      if ((t + j * 3) % 7 === 0) fx("dw6_glint", up(ed.at, hgt * (0.55 + rnd(k2 + 2) * 0.4)));
    }
    if (pageGlitter && page && page.valid) {
      for (let i = 0; i < 3; i++) {
        const k2 = t * 2.3 + i * 0.37;
        fx(i ? "dw6_glint" : "dw6_script", pagePt(-58 + rnd(k2) * 116, 3 + rnd(k2 + 0.5) * 82, 0.4));
      }
    }
    for (let k2 = 0; k2 < tablets.length && tabletsShown; k2++) {
      const tab = tablets[k2];
      if (!tab.valid) continue;
      fx((t + k2) % 3 ? "dw6_script" : "dw6_glint", add(tab.loc, { x: (rnd(t + k2) - 0.5) * 4, y: 1 + rnd(t * 1.1 + k2) * 7, z: (rnd(t * 0.7 + k2) - 0.5) * 3 }));
    }
    if (bookShows) {
      for (let i = 0; i < 2; i++) {
        const k2 = t * 1.9 + i * 0.41;
        fx((t + i) % 5 ? "dw6_script" : "dw6_glint", add(bookAt, { x: (rnd(k2) - 0.5) * 4.5, y: 0.2 + rnd(k2 + 0.3) * 3.5, z: (rnd(k2 + 0.6) - 0.5) * 4 }));
      }
    }
    for (let j = 0; j < hovering.length; j++) {
      const ln = hovering[j];
      if (ln.valid) fx((t + j) % 3 ? "dw6_glint" : "dw6_stream", add(ln.loc, { x: (rnd(t + j * 3) - 0.5) * 10, y: (rnd(t * 1.3 + j) - 0.5) * 1.5, z: (rnd(t * 0.9 + j) - 0.5) * 10 }));
    }
    if (refugeOn && t % 2 === 0) {
      const a = (35 + rnd(t * 0.77) * 290) * DEG;
      const dir = add(mul(fwd, Math.cos(a)), mul(rt, Math.sin(a)));
      const p = add(refugeAt, add(mul(dir, 6.4), { x: 0, y: 0.3 + rnd(t + 1) * 1.6, z: 0 }));
      fx(t % 6 === 0 ? "dw6_feather" : t % 4 === 0 ? "dw6_letters" : "dw6_motes", p);
    }
  }, 0, T_END - 4);
  scene.every(90, () => snd("dw6_bed", center, 0.85), T_WRITE0 - 20, T_FINAL - 60);
  const marks = /* @__PURE__ */ new Map();
  function mark(e, skin = 0) {
    let m = marks.get(e.id);
    if (!m || !m.a.valid) {
      let live2 = 0;
      for (const x of marks.values()) if (x.a.valid) live2++;
      if (live2 >= DW06.maxMarks || !isAlive(e)) return;
      const a = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK3.appear });
      scene.follow(a, e, 2.4);
      m = { e, a };
      marks.set(e.id, m);
      fx("dw6_quill", up(e.location, 2.4));
    }
    m.a.skin(skin);
  }
  const book = scene.spawn("dw6_book", b1, { yaw: faceOrigin(b1), state: BOOK.arrive, size: BOOK_START });
  snd("dw6_silence", c0, 1);
  scene.at(4, () => snd("dw6_book", b1, 1.1));
  tb.place(G(Ds - 1, 0, 0.5), LIGHT);
  const boundary = scene.spawn("dw6_boundary", up(center, 0.05), { yaw: faceOrigin(center), state: BOUND.inscribe });
  scene.at(40, () => {
    boundary.state(BOUND.hold);
    boundaryOn = true;
  });
  scene.every(1, (e) => {
    const off = clamp((e / 20 - 0.1) / 0.36, 0, 4) * 45;
    for (const s of [-1, 1]) {
      fx("dw6_quill", ringPt(90 + s * off, 0.5));
      fx("dw6_script", ringPt(90 + s * (off - 8), 0.3));
    }
  }, 2, 34);
  scene.every(1, (e) => {
    for (const ph of [0, 180]) {
      const a = (e * 19 + ph) * DEG;
      fx("dw6_stream", add(b1, { x: Math.cos(a) * 2.6, y: -1.2 + e / T_OPEN * 2.8, z: Math.sin(a) * 2.6 }));
    }
    if (e % 3 === 0) fx("dw6_motes", up(b1, -1.2));
    if (e % 8 === 0) fx("dw6_halo", up(b1, -1));
  }, 4, T_OPEN);
  scene.at(12, () => domain().slice(0, DW06.maxMarks).forEach((e, i) => scene.after(i * 3, () => mark(e))));
  scene.at(T_OPEN, () => {
    book.state(BOOK.open);
    fx("dw6_halo", up(b1, 0.6));
  });
  scene.at(T_UNBIND, () => {
    book.state(BOOK.unbind).skin(1);
    snd("dw6_unbind", b1, 1.1);
    fxBurst("dw6_letters", up(b1, 1), 1.6, 6);
  });
  scene.at(T_LAYERED, () => book.state(BOOK.layered));
  const pageMid = pagePt(6, 40, 0.5);
  const inkPath = (q) => bezier(up(b1, 1.2), up(lerp(b1, pageMid, 0.35), 9), pageMid, q);
  scene.every(1, (e) => {
    fxFlow("dw6_stream", inkPath, e, 5, 0.045);
    if (e % 3 === 0) fx("dw6_trail", inkPath(e * 0.045 % 1));
    if (e < 36 && e % 2 === 0) fx("dw6_letters", add(b1, { x: (rnd(e) - 0.5) * 4.5, y: 0.6, z: (rnd(e + 0.5) - 0.5) * 3 }));
  }, T_UNBIND, T_SEAM + 14);
  scene.at(T_SEAM, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.manifest });
    snd("dw6_page", pagePt(0, 44), 1.8);
    fxLine("dw6_trail", pagePt(0, 0, 0.4), pagePt(0, 88, 0.4), 12);
    fx("dw6_flare", pagePt(0, 44, 1));
    fx("dw6_bell", pagePt(0, 44, 1));
  });
  scene.every(1, (e) => {
    const w = 60 * clamp((e - 12) / 22, 0, 1);
    for (const s of [-1, 1]) {
      fx("dw6_glint", pagePt(s * w, 4 + rnd(e * 1.3 + s) * 80, 0.4));
      fx("dw6_quill", pagePt(s * w, 4 + rnd(e * 2.1 + s) * 80, 0.4));
    }
    fx("dw6_seam", pagePt((rnd(e) - 0.5) * 2 * w, 2 + rnd(e + 3) * 84, 0.5));
  }, T_SEAM + 4, T_SEAM + 44);
  scene.at(T_SEAM + 50, () => {
    page?.state(PAGE.idle);
    pageGlitter = true;
  });
  scene.at(T_GLIDE, () => snd("dw6_glide", b1, 1.3));
  scene.span(T_GLIDE, T_GLIDE + GLIDE, (p) => {
    const q = smooth(p);
    bookAt = bezier(b1, up(lerp(b1, b2, 0.5), 5), b2, q);
    book.move(bookAt, faceOrigin(bookAt));
    if (scene.tick % 2 === 0) book.size(BOOK_START + (BOOK_LECTERN - BOOK_START) * q);
    fx("dw6_stream", up(bookAt, -0.6));
    fx("dw6_script", add(bookAt, { x: (rnd(scene.tick) - 0.5) * 4, y: rnd(scene.tick + 0.5) * 2, z: (rnd(scene.tick + 0.9) - 0.5) * 4 }));
    if (scene.tick % 3 === 0) fx("dw6_trail", up(bookAt, 0.8));
  });
  const claimed = /* @__PURE__ */ new Set();
  const cover = [];
  addWard({
    scene,
    factor: DW06.coverFactor,
    protects: (e) => isAlly(e) && cover.some((z) => distXZ(z.p, e.location) <= z.r)
  });
  function fitSize(kind, p, elevDeg, cap) {
    const d = Math.max(6, distXZ(p, c0));
    return clamp((c0.y + EYE + d * Math.tan(elevDeg * DEG) - p.y) / ED_H[kind], 0.42, cap);
  }
  function landingSpot(i) {
    const s = PLAN[i];
    let p = G(Ds + s.v, s.u);
    if (s.seek) {
      const near = hostiles(dim, p, DW06.seekRadius, caster).filter((e) => !claimed.has(e.id) && distXZ(e.location, c0) >= DW06.seekMinDist && dist(e.location, center) <= DW06.domainRadius && edifices.every((ed) => distXZ(ed.at, e.location) >= 4.5));
      if (near.length) {
        claimed.add(near[0].id);
        p = ground(near[0].location);
      }
    }
    return p;
  }
  function cellsFor(kind, p, size) {
    const r = right(norm(flat(sub(c0, p))));
    const offs = kind === COLUMN ? [0] : kind === ARCH ? [-22 * ED_U * size, 22 * ED_U * size] : kind === GATE2 ? [-1, 1].flatMap((s) => [s * (27 * ED_U * size - 0.5), s * (27 * ED_U * size + 0.5)]) : [];
    return offs.map((o) => add(p, mul(r, o)));
  }
  function raiseBarriers(ed) {
    for (const c of ed.cells) {
      for (const e of hostiles(dim, c, 1.3, caster)) knockback(e, c, 0.8, 0.2);
      scene.after(2, () => tb.column(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), ed.h));
    }
  }
  function dropBarriers(ed) {
    for (const c of ed.cells) tb.removeColumn(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), ed.h);
  }
  function impact(kind, p, size, cellPts) {
    const spots = kind === ARCH ? cellPts : [p];
    fx("dw6_quake", up(p, 0.2));
    fx("dw6_wave", up(p, 0.15));
    fx("dw6_dust", up(p, 0.4));
    fx("dw6_flare", up(p, 2));
    fx("dw6_pillar", up(p, 6));
    fx("dw6_fountain", up(p, 0.3));
    fxBurst("dw6_ink", up(p, 2.5), 2.2, 6);
    fxRing("dw6_letters", up(p, 0.4), 2.6 * size + 0.8, 5, p.x * 31);
    snd("dw6_land", p, 1.4, 1 - kind * 0.03);
    const hit = /* @__PURE__ */ new Set();
    scene.after(3, () => {
      for (const e of hostiles(dim, p, DW06.landShockRadius, caster)) {
        if (distXZ(e.location, p) <= DW06.landRadius[kind]) continue;
        damage(e, DW06.landShockDamage, caster);
        knockback(e, p, 0.5, 0.2);
      }
    });
    if (DW06.landDamage[kind] <= 0 && kind !== PLATFORM) return;
    for (const s of spots) {
      for (const e of hostiles(dim, s, DW06.landRadius[kind], caster)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        if (DW06.landDamage[kind] > 0) damage(e, DW06.landDamage[kind], caster);
        knockback(e, s, DW06.landKnock[kind], 0.4);
      }
    }
  }
  function writeLetter(i, t0) {
    const s = PLAN[i];
    let land = G(Ds + s.v, s.u);
    let size = 0.8;
    let warn;
    let glyph;
    const slot = pagePt(s.a, s.b, 0.6);
    scene.at(t0, () => {
      land = landingSpot(i);
      size = fitSize(s.kind, land, s.elev, s.cap);
      glyph = scene.spawn("dw6_glyph", slot, { yaw: pageYaw, kind: s.kind, state: GLYPH.draw });
      snd("dw6_stroke", slot, 1.6, 0.95 + i * 0.02);
      warn = scene.spawn("telegraph", land, { kind: 0, size: Math.max(2, DW06.landRadius[s.kind] * (s.kind === BRIDGE ? 1 : 0.9)), state: TEL.slow });
    });
    scene.every(1, (e) => {
      const k2 = Math.min(4, Math.floor(e / 4));
      const sp = pagePt(s.a + (rnd(t0 + e) - 0.5) * 14, s.b + 12 - k2 * 6, 0.8);
      fx("dw6_quill", sp);
      fx(e % 2 ? "dw6_glint" : "dw6_ink", sp);
      fxFlow("dw6_stream", (q) => bezier(up(bookAt, 1.5), up(lerp(bookAt, sp, 0.5), 3), sp, q), e, 3, 0.12);
    }, t0 + 1, t0 + DRAW);
    scene.at(t0 + DRAW - 2, () => {
      fx("dw6_halo", slot);
      fxBurst("dw6_letters", slot, 2.2, 5);
    });
    scene.at(t0 + DRAW, () => {
      glyph?.state(GLYPH.fall);
      snd("dw6_fall", slot, 1.4);
    });
    scene.span(t0 + DRAW, t0 + DRAW + FALL, (p) => {
      const to = up(land, 2.4 * size + 1);
      const mid = up(lerp(slot, to, 0.45), 6);
      const q = 0.25 * p + 0.75 * p * p;
      const pos = bezier(slot, mid, to, q);
      glyph?.move(pos, pageYaw);
      fx("dw6_trail", pos);
      fx("dw6_stream", bezier(slot, mid, to, Math.max(0, q - 0.06)));
      fx("dw6_stream", bezier(slot, mid, to, Math.max(0, q - 0.13)));
      if (scene.tick % 3 === 0) fx("dw6_letters", bezier(slot, mid, to, Math.max(0, q - 0.1)));
    });
    scene.at(t0 + DRAW + FALL, () => {
      if (glyph) {
        glyph.state(GLYPH.land);
        const g = glyph;
        scene.after(10, () => scene.despawn(g));
      }
      if (warn) {
        warn.state(TEL.flash);
        const w = warn;
        scene.after(8, () => scene.despawn(w));
      }
      const yaw = faceOrigin(land);
      const a = scene.spawn("dw6_edifice", land, { yaw, kind: s.kind, size, state: s.kind === BRIDGE ? ED.swing : ED.assemble });
      const ed = {
        a,
        kind: s.kind,
        at: land,
        yaw,
        size,
        cells: cellsFor(s.kind, land, size),
        h: Math.max(3, Math.round(DW06.barrierHeight[s.kind] * size)),
        alive: true
      };
      edifices.push(ed);
      tb.place(up(add(land, mul(norm(flat(sub(c0, land))), 2)), 0.6), LIGHT);
      const hgt = ED_H[s.kind] * size;
      scene.every(1, (e) => {
        for (const ph of [0, 120, 240]) {
          const a2 = (e * 23 + ph) * DEG, r = 1.9 * size + 0.6;
          fx("dw6_stream", { x: land.x + Math.cos(a2) * r, y: land.y + 0.3 + e / 30 * hgt, z: land.z + Math.sin(a2) * r });
        }
      }, scene.tick + 1, scene.tick + 30);
      if (s.kind === BRIDGE) {
        snd("dw6_swing", land, 1.3);
        scene.after(21, () => impact(BRIDGE, land, size, []));
      } else impact(s.kind, land, size, ed.cells);
      if (ed.cells.length) raiseBarriers(ed);
      if (s.kind === PLATFORM || s.kind === BRIDGE) cover.push({ p: land, r: DW06.coverRadius });
      if (s.kind === CELESTIAL) {
        scene.every(DW06.celestialPulseEvery, () => {
          if (!ed.alive) return;
          const core = up(ed.at, 46 * ED_U * ed.size);
          fx("dw6_rays", up(ed.at, 0.3));
          fx("dw6_halo", core);
          for (const e of hostiles(dim, ed.at, DW06.celestialPulseRadius, caster).slice(0, 2)) {
            fxLine("dw6_trail", core, up(e.location, 1), 6);
            fx("dw6_seam", up(e.location, 1));
            damage(e, DW06.celestialPulseDamage, caster);
          }
        }, scene.tick + 20, T_UNW);
      }
      scene.after(s.kind === BRIDGE ? 28 : 32, () => {
        if (ed.alive) a.state(ED.hold);
      });
      for (const e of hostiles(dim, land, DW06.landRadius[s.kind] + 1, caster)) if (dist(e.location, center) <= DW06.domainRadius) mark(e);
    });
  }
  PLAN.forEach((_, i) => writeLetter(i, T_WRITE0 + WRITE_AT[i]));
  const TAB_D = Lp - 7;
  const tabAng = [-30, -20, -10, 0, 10, 20, 30];
  const stations = tabAng.map((ang) => SKY(TAB_D * Math.cos(ang * DEG), TAB_D * Math.sin(ang * DEG), TAB_LIFT + 0.5 * Math.cos(ang * 3 * DEG)));
  const ruleA = (k2) => -45 + 102 / 7 * (k2 + 0.5);
  const tabLoc = (k2) => tablets[k2]?.valid ? tablets[k2].loc : stations[k2];
  const emblem = (k2) => up(tabLoc(k2), 3.1);
  scene.at(T_SPLIT, () => {
    page?.state(PAGE.split);
    pageGlitter = false;
    snd("dw6_split", pagePt(0, 44), 1.8);
    fx("dw6_flash", pagePt(6, 44, 1));
    for (let k2 = 1; k2 < 7; k2++) fxLine("dw6_seam", pagePt(-45 + 102 / 7 * k2, 4, 0.5), pagePt(-45 + 102 / 7 * k2, 84, 0.5), 7);
  });
  scene.at(T_TAB, () => {
    for (let k2 = 0; k2 < 7; k2++) {
      const from = pagePt(ruleA(k2), 18, 0.4);
      tablets.push(scene.spawn("dw6_tablet", from, { yaw: pageYaw, kind: k2, state: TAB.form }));
    }
  });
  scene.at(T_TAB + 24, () => {
    if (page) scene.despawn(page);
    page = void 0;
  });
  for (let k2 = 0; k2 < 7; k2++) {
    const t0 = T_TAB + 2 + k2 * 3;
    scene.span(t0, t0 + TAB_FLY, (p) => {
      const tab = tablets[k2];
      if (!tab) return;
      const from = pagePt(ruleA(k2), 18, 0.4), to = stations[k2];
      const pos = bezier(from, up(lerp(from, to, 0.5), 3), to, smooth(p));
      tab.move(pos, faceOrigin(pos));
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 4.5));
      if (scene.tick % 3 === 0) fx("dw6_stream", up(pos, 2 + rnd(scene.tick + k2) * 6));
    });
    scene.at(t0 + TAB_FLY, () => {
      tablets[k2]?.state(TAB.idle);
      fx("dw6_halo", emblem(k2));
    });
  }
  const walls = [];
  let refuge;
  addWard({ scene, factor: DW06.refugeFactor, protects: (e) => refugeOn && isAlly(e) && distXZ(e.location, refugeAt) <= DW06.refugeRadius });
  let finalWarn;
  const judged = /* @__PURE__ */ new Set();
  const judgedWarn = [];
  function declare(k2, target2) {
    const t = tablets[k2];
    if (!t) return;
    t.state(TAB.declare);
    snd(`dw6_law${k2 + 1}`, target2, 1.6);
    const onto = distXZ(target2, c0) < 7 ? G(7, 0) : target2;
    const from = emblem(k2);
    fx("dw6_halo", from);
    fx("dw6_flare", from);
    scene.span(scene.tick, scene.tick + 12, (p, e) => {
      const path = (q) => bezier(from, up(lerp(from, onto, 0.5), 5), up(onto, 1), q);
      fxFlow("dw6_stream", path, e, 3, 0.07);
      fx("dw6_trail", path(Math.min(1, p * 1.1)));
    });
    scene.after(10, () => {
      fx("dw6_quake", up(onto, 0.3));
      fx("dw6_halo", up(onto, 1.5));
    });
    scene.after(32, () => {
      if (scene.tick < T_RISE) t.state(TAB.idle);
    });
  }
  const laws = [
    // I Containment: written walls close the far side of the densest hostile region and draw it in; the side facing
    // the caster is closed by a low line of script (and barriers), so the view into the region stays open
    () => {
      const H2 = awayFrom(ground(centroid(domain(), G(Ds + 3, 0))), DW06.containMinDist);
      declare(0, H2);
      const R2 = DW06.containRadius;
      const inside = allies(dim, H2, R2 + 1.5, caster).length > 0;
      const toC = yawOf(sub(c0, H2));
      for (let i = 0; i < 6; i++) {
        const ang = i * 60 + 30;
        const p = ground({ x: H2.x + Math.cos(ang * DEG) * R2, y: H2.y, z: H2.z + Math.sin(ang * DEG) * R2 });
        if (Math.abs(angleDelta(ang - 90, toC)) < 50) continue;
        const w = scene.spawn("dw6_wall", p, { yaw: yawOf(sub(H2, p)), kind: 0, size: 1, state: WALL.rise });
        walls.push(w);
        scene.after(20, () => w.state(WALL.hold));
        scene.after(DW06.containTicks, () => {
          w.state(WALL.sink);
          scene.after(20, () => scene.despawn(w));
        });
        scene.after(2, () => {
          fx("dw6_dust", up(p, 0.3));
          fx("dw6_fountain", up(p, 0.3));
        });
      }
      fxRing("dw6_quill", up(H2, 0.3), R2, 12);
      fx("dw6_wave", up(H2, 0.2));
      for (const d of [2, 8]) {
        scene.after(d, () => {
          for (const e of hostiles(dim, H2, DW06.containPull, caster)) if (distXZ(e.location, H2) > R2 - 1.5) shove(e, sub(H2, e.location), DW06.containPullStrength, 0.25);
        });
      }
      const cells = [];
      scene.after(16, () => {
        for (let s = 0; s < 48; s++) {
          const a = s * 360 / 48;
          if (inside && Math.abs(angleDelta(a - 90, toC)) < 30) continue;
          const p = ground({ x: H2.x + Math.cos(a * DEG) * R2, y: H2.y, z: H2.z + Math.sin(a * DEG) * R2 });
          tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3);
          cells.push(p);
        }
      });
      scene.every(2, (e) => {
        const a = (toC + 90 + (rnd(e * 1.7) - 0.5) * 100) * DEG;
        const p = { x: H2.x + Math.cos(a) * R2, y: H2.y + 0.3, z: H2.z + Math.sin(a) * R2 };
        fx(e % 4 ? "dw6_script" : "dw6_quill", p);
      }, scene.tick + 16, scene.tick + DW06.containTicks);
      scene.after(DW06.containTicks + 4, () => {
        for (const p of cells) tb.removeColumn(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3);
      });
    },
    // II Station: the two platforms glide in from the flanks and settle low across the front of the enemy, a written
    // bar (barriers two high) spans the line between them, and allies behind it are covered
    () => {
      const { E, near } = enemyFront();
      const toE = distXZ(E, c0) < 1 ? fwd : norm(flat(sub(E, c0)));
      const side = right(toE);
      stD = clamp(near - 1.5, DW06.stationMin, Ds - 1);
      const mid = ground(add(c0, mul(toE, stD)));
      declare(1, mid);
      cover.push({ p: c0, r: DW06.stationCover });
      for (const ed of edifices.filter((e) => e.kind === PLATFORM && e.alive)) {
        const dest = ground(add(mid, mul(side, (lateral(ed.at) < 0 ? -1 : 1) * DW06.stationSpread)));
        const from = ed.at, s0 = ed.size, cv = cover.find((z) => z.p === from);
        ed.a.state(ED.strike);
        scene.span(scene.tick + 4, scene.tick + 34, (p) => {
          const q = smooth(p);
          const pos = up(lerp(from, dest, q), Math.sin(q * Math.PI) * 0.8);
          ed.a.move(pos, faceOrigin(pos));
          ed.at = lerp(from, dest, q);
          if (scene.tick % 2 === 0) {
            ed.size = s0 + (DW06.stationSize - s0) * q;
            ed.a.size(ed.size);
            fx("dw6_dust", up(ed.at, 0.3));
          }
        });
        scene.after(35, () => {
          ed.at = dest;
          ed.size = DW06.stationSize;
          ed.a.size(ed.size);
          if (ed.alive) ed.a.state(ED.hold);
          fx("dw6_quake", up(dest, 0.2));
          fx("dw6_halo", up(dest, 1.5));
          if (cv) cv.p = dest;
          for (const e of hostiles(dim, dest, 2.4, caster)) knockback(e, dest, 0.9, 0.3);
        });
      }
      scene.after(36, () => {
        const half = DW06.stationSpread + 2;
        for (let j = -half; j <= half; j++) {
          const c = ground(add(mid, mul(side, j)));
          tb.column(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), 2);
        }
        fxLine("dw6_seam", add(up(mid, 0.6), mul(side, -half)), add(up(mid, 0.6), mul(side, half)), 12);
      });
      scene.every(2, (e) => {
        const p = add(up(mid, 0.4 + e % 3 * 0.5), mul(side, (rnd(e * 2.9) - 0.5) * 2 * (DW06.stationSpread + 2)));
        fx(e % 6 ? "dw6_script" : "dw6_glint", p);
      }, scene.tick + 36, T_UNW);
    },
    // III Direction: three banners of text are fired across the field, one lane after another
    () => {
      const ed0 = clamp(depth(enemyFront().E), 13, Ds + 4);
      declare(2, G(ed0, 0));
      const lanes = [{ d: ed0 - 2.5, dir: 1 }, { d: ed0 + 0.5, dir: -1 }, { d: ed0 + 4, dir: 1 }];
      lanes.forEach((ln, j) => {
        const from = G(ln.d, -16 * ln.dir), to = G(ln.d, 16 * ln.dir);
        const along = mul(rt, ln.dir);
        const w = scene.spawn("dw6_wall", from, { yaw: faceOrigin(from), kind: 1, size: 0.9, state: WALL.rise });
        walls.push(w);
        const hit = /* @__PURE__ */ new Set();
        const t0 = scene.tick + 12 + j * 8;
        scene.at(t0 - 10, () => fxLine("dw6_seam", up(from, 0.4), up(to, 0.4), 12));
        scene.at(t0, () => w.state(WALL.hold));
        scene.span(t0, t0 + DW06.directionTicks, (p) => {
          const pos = lerp(from, to, smooth(p));
          w.move(pos, faceOrigin(pos));
          fx("dw6_trail", up(pos, 1.4));
          if (scene.tick % 2 === 0) fx("dw6_ink", up(pos, 1.2));
          for (const e of hostiles(dim, pos, DW06.directionHalfWidth + 2, caster)) {
            const rel = sub(e.location, pos);
            const al = rel.x * rt.x + rel.z * rt.z, lat = rel.x * fwd.x + rel.z * fwd.z;
            if (Math.abs(al) > DW06.directionHalfWidth || Math.abs(lat) > DW06.directionBand || hit.has(e.id)) continue;
            hit.add(e.id);
            damage(e, DW06.directionDamage, caster);
            shove(e, along, 1.1, 0.3);
            fx("dw6_seam", up(e.location, 1));
          }
        });
        scene.at(t0 + DW06.directionTicks, () => {
          w.state(WALL.sink);
          scene.after(20, () => scene.despawn(w));
        });
      });
    },
    // IV Stillness: hostile movement is bound in place, then dragged slow
    () => {
      declare(3, center);
      fx("dw6_wave_s", up(center, 0.3));
      scene.after(6, () => fx("dw6_wave_s", up(center, 0.5)));
      let n = 0;
      for (const e of domain()) {
        restrain(scene, e, DW06.stillTicks);
        effect(e, "slowness", DW06.stillTicks + DW06.stillSlowTicks, DW06.stillSlowAmp);
        fx("dw6_blue", up(e.location, 1));
        fx("dw6_silver", up(e.location, 2.2));
        if (n++ < 6) {
          const g = ground(e.location);
          const ci = scene.spawn("dw_circle", g, { size: 0.6, state: CIRCLE.form });
          scene.after(16, () => ci.state(CIRCLE.hold));
          scene.after(DW06.stillTicks, () => ci.state(CIRCLE.fade));
          scene.after(DW06.stillTicks + 14, () => scene.despawn(ci));
          scene.every(6, () => {
            if (isAlive(e)) fx("dw6_silver", up(e.location, 2.1));
          }, scene.tick + 6, scene.tick + DW06.stillTicks);
        }
      }
    },
    // V Refuge: the allied zone is shielded and restored
    () => {
      refugeAt = ground(casterPos());
      declare(4, refugeAt);
      refuge = scene.spawn("dw6_dome", refugeAt, { state: DOME.form });
      refugeOn = true;
      scene.after(24, () => refuge?.state(DOME.hold));
      for (const p of allies(dim, refugeAt, DW06.refugeRadius, caster)) heal(p, DW06.refugeHeal);
      fxRing("dw6_letters", up(refugeAt, 0.4), DW06.refugeRadius + 0.6, 10);
      fxRing("dw6_feather", up(refugeAt, 3.2), DW06.refugeRadius, 6, 15);
    },
    // VI Sequence: each written structure strikes in turn, read from left to right
    () => {
      declare(5, center);
      [...edifices].filter((e) => e.alive).sort((a, b) => lateral(a.at) - lateral(b.at)).forEach((ed, j) => {
        scene.after(6 + j * 4, () => {
          if (!ed.alive) return;
          ed.a.state(ED.strike);
          scene.after(16, () => {
            if (ed.alive) ed.a.state(ED.hold);
          });
          const p = ed.at, hgt = ED_H[ed.kind] * ed.size, top = up(p, hgt * 0.8);
          fx("dw6_pillar", up(p, 6));
          fx("dw6_quake", up(p, 0.2));
          fx("dw6_flare", top);
          fx("dw6_halo", up(p, hgt * 0.5));
          fxBurst("dw6_ink", up(p, hgt * 0.6), 1.8, 5);
          snd("dw6_strike", p, 0.8, 1 + j * 0.05);
          const hit = /* @__PURE__ */ new Set();
          for (const e of hostiles(dim, p, DW06.sequenceRadius, caster)) {
            hit.add(e.id);
            damage(e, DW06.sequenceDamage, caster);
            knockback(e, p, 0.6, 0.3);
          }
          const far = hostiles(dim, p, DW06.sequenceReach, caster).find((e) => !hit.has(e.id));
          if (far) {
            fxLine("dw6_trail", top, up(far.location, 1), 8);
            fxLine("dw6_stream", top, up(far.location, 1), 5);
            fx("dw6_flare", up(far.location, 1));
            damage(far, DW06.sequenceDamage, caster);
            knockback(far, p, 0.5, 0.25);
          }
        });
      });
    },
    // VII Judgment: every surviving enemy is marked and the finale's region is designated
    () => {
      const es = domain();
      const fa = target && isAlive(target) && dist(target.location, center) <= DW06.domainRadius ? target.location : centroid(es, G(Ds + 2, 0));
      finalAt = awayFrom(ground(fa), DW06.finalMinDist);
      declare(6, finalAt);
      for (const e of es) {
        mark(e, 2);
        judged.add(e.id);
      }
      finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: DW06.finalRadius, state: TEL.slow });
      scene.after(40, () => finalWarn?.state(TEL.hold));
      fx("dw6_pillar", up(finalAt, 6));
      fx("dw6_rays", up(finalAt, 0.3));
      for (const e of es.slice(0, 4)) {
        const w = scene.spawn("telegraph", ground(e.location), { kind: 0, size: 1.6, state: TEL.warn });
        scene.after(20, () => w.state(TEL.hold));
        scene.follow(w, e, 0.05);
        judgedWarn.push(w);
      }
    }
  ];
  laws.forEach((fn, k2) => scene.at(T_LAW0 + k2 * LAW_STEP, fn));
  const T_REF = T_LAW0 + 4 * LAW_STEP;
  scene.every(40, () => {
    if (refugeOn) for (const p of allies(dim, refugeAt, DW06.refugeRadius, caster)) heal(p, DW06.refugeRegen);
  }, T_REF + 40, T_UNW);
  scene.every(10, () => {
    if (refugeOn) dissolveProjectiles(scene, up(refugeAt, 2), DW06.refugeRadius);
  }, T_REF, T_UNW);
  scene.at(T_RISE, () => {
    tablets.forEach((t) => t.state(TAB.shed));
    snd("dw6_rise", SKY(TAB_D, 0, 8), 1.8);
    fx("dw6_flash", SKY(TAB_D, 0, 11));
    fx("dw6_wave", up(center, 0.3));
    fxLine("dw6_seam", SKY(TAB_D, -16, 9), SKY(TAB_D, 16, 9), 14);
  });
  const raised = (k2) => up(add(stations[k2], mul(norm(flat(sub(stations[k2], c0))), TAB_BACK)), TAB_RISE);
  for (let k2 = 0; k2 < 7; k2++) {
    const t0 = T_RISE + 8 + Math.abs(k2 - 3) * 4;
    scene.span(t0, t0 + 44, (p) => {
      const tab = tablets[k2];
      if (!tab) return;
      const pos = lerp(stations[k2], raised(k2), easeIn(p) * 0.7 + smooth(p) * 0.3);
      tab.move(pos);
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 2));
      if (scene.tick % 3 === 0) fx("dw6_letters", up(pos, 1));
    });
    scene.at(t0, () => {
      fx("dw6_halo", emblem(k2));
      fxBurst("dw6_ink", emblem(k2), 2.5, 5);
    });
  }
  scene.at(T_RISE + 40, () => tablets.forEach((t) => t.state(TAB.idle)));
  scene.at(T_RISE + 56, () => {
    tabletsShown = false;
  });
  function spawnLine(kind, p, size) {
    const a = scene.spawn("dw6_line", p, { yaw: faceOrigin(p), kind, size, state: LINE.assemble });
    snd("dw6_form", p, 1.4, 1 + kind * 0.06);
    hovering.push(a);
    scene.span(scene.tick, scene.tick + 24, (_q, e) => {
      for (let k2 = e % 2; k2 < tablets.length; k2 += 2) {
        const from = up(tabLoc(k2), 6);
        fxFlow("dw6_stream", (q) => bezier(from, up(lerp(from, p, 0.5), 2), p, q), e + k2 * 2, 1, 0.08);
      }
    });
    scene.after(30, () => a.state(LINE.hold));
    return a;
  }
  const descend = (a, from, to, t0, t1) => {
    scene.span(t0, t1, (p) => a.move(lerp(from, to, easeIn(p) * 0.6 + smooth(p) * 0.4)));
  };
  const leave = (a) => {
    const i = hovering.indexOf(a);
    if (i >= 0) hovering.splice(i, 1);
  };
  const L1 = { form: T_RISE + 14, desc: T_RISE + 42 };
  let l1;
  const l1Hi = SKY(Ds + 4, 0, 5);
  let sweepD = Ds;
  const sweepAt = (p) => G(sweepD + DW06.sweepTravel * smooth(p), 0, 0.95);
  scene.at(L1.form, () => {
    l1 = spawnLine(0, l1Hi, DW06.sweepHalfLength * 2 / 24.4);
  });
  const sweepWarn = [];
  scene.at(L1.desc - 22, () => {
    sweepD = clamp(Math.max(enemyFront().near - 1, stD + 2.2), 12, Ds + 3);
    for (const v2 of [0.5, 3.5, 6.5]) sweepWarn.push(scene.spawn("telegraph", G(sweepD + v2, 0), { kind: 0, size: 2.6, state: TEL.warn }));
  });
  scene.at(L1.desc, () => {
    if (l1) {
      leave(l1);
      descend(l1, l1Hi, sweepAt(0), L1.desc, L1.desc + 16);
    }
  });
  scene.at(L1.desc + 16, () => {
    const lo = sweepAt(0);
    l1?.state(LINE.strike);
    snd("dw6_strike", lo, 1.5);
    fx("dw6_flare", lo);
    for (let j = -2; j <= 2; j++) {
      fx("dw6_quake", add(up(lo, -0.8), mul(rt, j * 2.6)));
      fx("dw6_dust", add(up(lo, -0.7), mul(rt, j * 2.6)));
    }
  });
  {
    const hit = /* @__PURE__ */ new Set();
    scene.span(L1.desc + 16, L1.desc + 48, (p) => {
      const pos = sweepAt(p);
      l1?.move(pos);
      if (scene.tick % 2 === 0) fxLine("dw6_seam", add(pos, mul(rt, -DW06.sweepHalfLength)), add(pos, mul(rt, DW06.sweepHalfLength)), 6);
      fx("dw6_dust", add(up(pos, -0.7), mul(rt, (rnd(scene.tick) - 0.5) * 2 * DW06.sweepHalfLength)));
      for (const e of hostiles(dim, pos, DW06.sweepHalfLength + 1.5, caster)) {
        const rel = sub(e.location, pos);
        if (hit.has(e.id) || Math.abs(rel.x * fwd.x + rel.z * fwd.z) > 1.8 || Math.abs(rel.x * rt.x + rel.z * rt.z) > DW06.sweepHalfLength) continue;
        hit.add(e.id);
        damage(e, DW06.sweepDamage, caster);
        shove(e, fwd, 1, 0.35);
      }
    });
  }
  scene.at(L1.desc + 48, () => sweepWarn.forEach((w) => {
    w.state(TEL.flash);
    scene.after(8, () => scene.despawn(w));
  }));
  scene.at(L1.desc + 50, () => {
    l1?.state(LINE.unwrite);
    if (l1) fxBurst("dw6_letters", up(l1.loc, 1), 3, 6);
  });
  scene.at(L1.desc + 70, () => {
    if (l1) scene.despawn(l1);
  });
  const L22 = { form: T_RISE + 26, desc: T_RISE + 78 };
  let l2;
  let ringC = G(Ds + 2, 0);
  let ringMax = 6;
  const l2Hi = SKY(Ds + 5, 0, 6);
  let ringWarn;
  scene.at(L22.form, () => {
    l2 = spawnLine(1, l2Hi, 0.5);
  });
  scene.at(L22.desc - 20, () => {
    ringC = clampDist(enemyFront().E, 13, Ds + 5);
    ringMax = clamp(distXZ(ringC, c0) - 7.5, 4.5, DW06.ringMaxRadius);
    ringWarn = scene.spawn("telegraph", ringC, { kind: 0, size: ringMax, state: TEL.warn });
  });
  scene.at(L22.desc, () => {
    if (l2) {
      leave(l2);
      descend(l2, l2Hi, up(ringC, 1), L22.desc, L22.desc + 16);
    }
  });
  scene.at(L22.desc + 16, () => {
    l2?.state(LINE.strike);
    snd("dw6_strike", ringC, 1.5, 0.85);
    fx("dw6_quake", up(ringC, 0.2));
    fx("dw6_flare", up(ringC, 1));
  });
  {
    const hit = /* @__PURE__ */ new Set();
    scene.span(L22.desc + 16, L22.desc + 44, (p) => {
      const rad = 2.5 + (ringMax - 2.5) * easeOut(p);
      l2?.size(rad / 7.5);
      if (scene.tick % 2 === 0) fxRing("dw6_seam", up(ringC, 0.6), rad, 12, scene.tick * 7);
      if (scene.tick % 4 === 0) fxRing("dw6_ink", up(ringC, 1.4), rad, 6, scene.tick * 11);
      for (const e of hostiles(dim, ringC, rad + 1.5, caster)) {
        if (hit.has(e.id) || Math.abs(distXZ(e.location, ringC) - rad) > 1.8) continue;
        hit.add(e.id);
        damage(e, DW06.ringDamage, caster);
        knockback(e, ringC, 1, 0.4);
      }
    });
  }
  scene.at(L22.desc + 44, () => {
    if (ringWarn) {
      ringWarn.state(TEL.flash);
      const w = ringWarn;
      scene.after(8, () => scene.despawn(w));
    }
    fx("dw6_wave", up(ringC, 0.3));
  });
  scene.at(L22.desc + 46, () => l2?.state(LINE.unwrite));
  scene.at(L22.desc + 66, () => {
    if (l2) scene.despawn(l2);
  });
  const L3 = { form: T_RISE + 84, desc: T_RISE + 118 };
  let l3;
  let latC = G(Ds + 3, 0);
  const l3Hi = SKY(Ds + 7, 0, 6.6);
  scene.at(L3.form, () => {
    l3 = spawnLine(2, l3Hi, 0.83);
  });
  scene.at(L3.desc - 2, () => {
    latC = clampDist(enemyFront().E, 15, Ds + 6);
  });
  scene.at(L3.desc, () => {
    if (l3) {
      leave(l3);
      descend(l3, l3Hi, up(latC, 4.6), L3.desc, L3.desc + 16);
    }
  });
  const cell = (gx, gz) => ground(add(add(latC, mul(rt, gx * 5)), mul(fwd, gz * 5)));
  const waves = [[[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], [[0, -1], [-1, 0], [1, 0], [0, 1]]];
  waves.forEach((cells, w) => {
    const tw = L3.desc + 32 + w * 22;
    const spots = [];
    const warns = [];
    scene.at(tw - 20, () => {
      for (const [gx, gz] of cells) {
        const s = cell(gx, gz);
        spots.push(s);
        warns.push(scene.spawn("telegraph", s, { kind: 0, size: DW06.latticeRadius, state: TEL.warn }));
      }
    });
    scene.at(tw - 6, () => {
      l3?.state(LINE.strike);
      for (const s of spots) {
        const col = scene.spawn("dw_column", s, { kind: w === 0 ? 0 : 2, size: 0.85, state: LIGHTCOL.descend });
        scene.after(10, () => col.state(LIGHTCOL.hold));
        scene.after(22, () => col.state(LIGHTCOL.dissolve));
        scene.after(36, () => scene.despawn(col));
      }
      snd("dw6_strike", latC, 1.4, 1.1 + w * 0.15);
    });
    scene.at(tw, () => {
      const hit = /* @__PURE__ */ new Set();
      warns.forEach((x) => {
        x.state(TEL.flash);
        scene.after(8, () => scene.despawn(x));
      });
      for (const s of spots) {
        fx("dw6_quake", up(s, 0.2));
        fx("dw6_rays", up(s, 0.3));
        fx("dw6_flare", up(s, 1));
        for (const e of hostiles(dim, s, DW06.latticeRadius, caster)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, DW06.latticeDamage, caster);
          knockback(e, s, 0.8, 0.5);
        }
      }
    });
  });
  scene.at(L3.desc + 70, () => l3?.state(LINE.unwrite));
  scene.at(L3.desc + 90, () => {
    if (l3) scene.despawn(l3);
  });
  const L4 = { form: T_RISE + 102, desc: T_RISE + 150 };
  let l4;
  const l4Hi = SKY(Ds + 9, 0, 7.4);
  let spiralWarn;
  let spiralR = 9;
  scene.at(L4.form, () => {
    l4 = spawnLine(3, l4Hi, 0.7);
  });
  scene.at(L4.desc - 20, () => {
    spiralR = clamp(distXZ(finalAt, c0) - 8.5, 4.5, 10);
    spiralWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: spiralR, state: TEL.warn });
  });
  scene.at(L4.desc, () => {
    if (l4) {
      leave(l4);
      descend(l4, l4Hi, up(finalAt, 1.4), L4.desc, L4.desc + 16);
    }
  });
  scene.at(L4.desc + 16, () => {
    l4?.state(LINE.strike);
    snd("dw6_strike", finalAt, 1.4, 0.75);
    fx("dw6_quake", up(finalAt, 0.2));
  });
  scene.span(L4.desc + 16, L4.desc + 56, (p, el) => {
    const rad = spiralR * (1 - smooth(p)) + 1.2;
    l4?.size(Math.max(0.15, rad / 8.6));
    if (el % 2 === 0) fxRing("dw6_stream", up(finalAt, 0.8 + p * 1.5), rad, 8, el * 21);
    if (el % 5 === 0) {
      for (const e of hostiles(dim, finalAt, rad + 1, caster)) {
        shove(e, sub(finalAt, e.location), DW06.spiralPull, 0.1);
        if (el % 10 === 0) damage(e, DW06.spiralTickDamage, caster);
      }
    }
  });
  scene.at(L4.desc + 56, () => {
    l4?.state(LINE.strike);
    spiralWarn?.state(TEL.flash);
    fx("dw6_flare", up(finalAt, 1.5));
    fx("dw6_quake", up(finalAt, 0.3));
    for (const e of hostiles(dim, finalAt, 3.5, caster)) damage(e, DW06.spiralFinalDamage, caster);
  });
  scene.at(L4.desc + 64, () => {
    if (spiralWarn) scene.despawn(spiralWarn);
    l4?.state(LINE.unwrite);
  });
  scene.at(L4.desc + 84, () => {
    if (l4) scene.despawn(l4);
  });
  const T_FORM = T_RISE + 160;
  const fSize = DW06.finalRadius / 12.4;
  let form;
  let formAt = up(finalAt, 4.3);
  scene.at(T_FORM, () => {
    formAt = up(finalAt, 4.3);
    form = spawnLine(4, formAt, fSize);
    leave(form);
    snd("dw6_form", formAt, 1.8, 0.7);
    fx("dw6_halo", formAt);
  });
  scene.at(T_FINAL - 68, () => snd("dw6_gather", finalAt, 2));
  scene.at(T_FINAL - 44, () => {
    if (finalWarn?.valid) finalWarn.state(TEL.warn);
    else finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: DW06.finalRadius, state: TEL.warn });
  });
  scene.span(T_FINAL - 44, T_FINAL - 8, (p, e) => {
    const pos = up(finalAt, 4.3 - 0.7 * smooth(p));
    form?.move(pos);
    formAt = pos;
    if (e % 4 === 0) fx("dw6_converge", pos);
    if (e % 3 === 0) fxRing("dw6_ink", up(finalAt, 0.4), DW06.finalRadius, 6, e * 9);
    const srcs = edifices.filter((x) => x.alive);
    for (let j = e % 3; j < srcs.length; j += 3) {
      const s = up(srcs[j].at, ED_H[srcs[j].kind] * srcs[j].size * 0.7);
      fxFlow("dw6_stream", (q) => bezier(s, up(lerp(s, pos, 0.5), 3), pos, q), e + j, 1, 0.06);
    }
    for (let k2 = e % 2; k2 < tablets.length; k2 += 2) {
      const s = up(tabLoc(k2), 6);
      fxFlow("dw6_trail", (q) => bezier(s, up(lerp(s, pos, 0.5), 4), pos, q), e + k2, 1, 0.05);
    }
  });
  scene.at(T_FINAL - 40, () => tablets.forEach((t) => t.state(TAB.declare)));
  scene.at(T_FINAL - 16, () => snd("dw6_finale", finalAt, 2.4));
  scene.span(T_FINAL - 8, T_FINAL, (p) => {
    const pos = p < 0.5 ? up(finalAt, 3.6 + 0.6 * smooth(p * 2)) : up(finalAt, 4.2 - 2.4 * easeIn((p - 0.5) * 2));
    form?.move(pos);
    formAt = pos;
  });
  scene.at(T_FINAL, () => {
    form?.state(LINE.strike);
    finalWarn?.state(TEL.flash);
    for (const w of judgedWarn) w.state(TEL.flash);
    fx("dw6_flash", up(finalAt, 2));
    fx("dw6_flare", up(finalAt, 1));
    fx("dw6_pillar", up(finalAt, 6));
    fx("dw6_wave", up(finalAt, 0.2));
    fx("dw6_quake", up(finalAt, 0.3));
    fx("dw6_fountain", up(finalAt, 0.4));
    fxRing("dw6_rays", up(finalAt, 0.4), DW06.finalRadius * 0.55, 8);
    fxRing("dw6_dust", up(finalAt, 0.4), DW06.finalRadius * 0.75, 10);
    fxBurst("dw6_ink", up(finalAt, 2.5), DW06.finalRadius * 0.5, 16);
    fxRing("dw6_pillar", up(finalAt, 6), DW06.finalRadius * 0.9, 8, 30);
    fxRing("dw6_letters", up(finalAt, 1), DW06.finalRadius, 12, 15);
    fxRing("dw6_halo", up(finalAt, 2), DW06.finalRadius * 0.6, 6);
    for (let i = 0; i < 6; i++) tb.place(up(add(finalAt, { x: Math.cos(i) * 3, y: 0, z: Math.sin(i) * 3 }), 1), LIGHT);
    for (const e of hostiles(dim, finalAt, DW06.finalRadius, caster)) {
      damage(e, DW06.finalDamage + (judged.has(e.id) ? DW06.judgedBonus : 0), caster);
      knockback(e, finalAt, DW06.finalKnockback, 0.7);
    }
    for (const m of marks.values()) {
      m.a.state(MARK3.burst);
      const a = m.a;
      scene.after(8, () => scene.despawn(a));
    }
  });
  scene.at(T_FINAL + 3, () => {
    fx("dw6_wave", up(finalAt, 0.3));
    fxRing("dw6_letters", up(finalAt, 0.6), DW06.finalRadius * 0.6, 8);
  });
  scene.at(T_FINAL + 7, () => {
    fx("dw6_wave", up(finalAt, 0.4));
    fx("dw6_flare", up(finalAt, 3));
  });
  scene.every(1, (e) => {
    const k2 = e * 7.3;
    const a = rnd(k2) * 2 * Math.PI, r = Math.sqrt(rnd(k2 + 0.5)) * DW06.finalRadius;
    fx("dw6_ember", { x: finalAt.x + Math.cos(a) * r, y: finalAt.y + 4 + rnd(k2 + 1) * 4, z: finalAt.z + Math.sin(a) * r });
    if (e % 2 === 0) fx("dw6_script", { x: finalAt.x - Math.cos(a) * r, y: finalAt.y + 0.5 + rnd(k2 + 2) * 3, z: finalAt.z - Math.sin(a) * r });
  }, T_FINAL + 1, T_FINAL + 50);
  scene.at(T_FINAL + 10, () => {
    if (finalWarn) scene.despawn(finalWarn);
    judgedWarn.forEach((w) => scene.despawn(w));
  });
  scene.at(T_FINAL + 24, () => {
    form?.state(LINE.unwrite);
    fxBurst("dw6_letters", up(finalAt, 3), 5, 8);
  });
  scene.at(T_FINAL + 44, () => {
    if (form) scene.despawn(form);
  });
  scene.at(T_UNW, () => {
    refugeOn = false;
    refuge?.state(DOME.fade);
    for (const w of walls) if (w.valid) w.state(WALL.sink);
    tb.clearAll();
    snd("dw6_unwrite", center, 1.6);
  });
  scene.at(T_UNW + 20, () => {
    if (refuge) scene.despawn(refuge);
    walls.forEach((w) => scene.despawn(w));
  });
  scene.at(T_UNW + 2, () => {
    [...edifices].sort((a, b) => distXZ(a.at, c0) - distXZ(b.at, c0)).forEach((ed, j) => {
      const t0 = scene.tick + j * 3;
      scene.at(t0, () => {
        ed.alive = false;
        ed.a.state(ED.unwrite);
        fx("dw6_fountain", up(ed.at, 0.5));
        fx("dw6_halo", up(ed.at, ED_H[ed.kind] * ed.size * 0.5));
        if (j % 3 === 0) snd("dw6_unwrite", ed.at, 0.9, 1.1 + j * 0.03);
      });
      scene.at(t0 + 42, () => scene.despawn(ed.a));
      const top = up(ed.at, ED_H[ed.kind] * ed.size * 0.6);
      scene.every(1, (e) => {
        const to = up(bookAt, 1);
        const path = (q) => bezier(top, up(lerp(top, to, 0.5), 7), to, q);
        fxFlow("dw6_stream", path, e, 2, 0.04);
        if (e % 3 === 0) fx("dw6_script", path(rnd(e + j) * 0.3));
      }, t0 + 10, t0 + 40);
    });
  });
  scene.at(T_FINAL + 10, () => {
    snd("dw6_glide", b2, 1.4, 0.9);
    bookShows = true;
  });
  scene.span(T_FINAL + 10, T_FINAL + 54, (p) => {
    const q = smooth(p);
    bookAt = bezier(b2, up(lerp(b2, bF, 0.5), 8), bF, q);
    book.move(bookAt, faceOrigin(bookAt));
    if (scene.tick % 2 === 0) book.size(BOOK_LECTERN + (BOOK_FINAL - BOOK_LECTERN) * q);
    fx("dw6_stream", up(bookAt, -0.6));
  });
  scene.at(T_FINAL + 56, () => tb.place(up(bF, -1.4), LIGHT));
  scene.at(T_TABRET, () => {
    tablets.forEach((t) => t.state(TAB.ret));
    tabletsShown = true;
  });
  scene.span(T_TABRET, T_TABRET + TAB_RET, (p) => {
    tablets.forEach((t, k2) => {
      const from = raised(k2), to = pagePt(ruleA(k2), 18, 0.3);
      const pos = bezier(from, up(lerp(from, to, 0.5), 3), to, smooth(p));
      t.move(pos, pageYaw);
      if (scene.tick % 2 === 0) fx("dw6_trail", up(pos, 4));
    });
  });
  scene.at(T_REFORM, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.reform });
    snd("dw6_page", pagePt(0, 44), 1.4, 1.2);
    fx("dw6_flash", pagePt(6, 44, 1));
    for (let k2 = 0; k2 < 7; k2++) fx("dw6_halo", pagePt(ruleA(k2), 40, 0.6));
  });
  scene.at(T_REFORM + 8, () => tablets.forEach((t) => scene.despawn(t)));
  scene.at(T_FOLD, () => page?.state(PAGE.fold));
  [14, 25, 36, 47].forEach((d, k2) => scene.at(T_FOLD + d, () => {
    snd("dw6_fold", pageO, 1.6, 1 + k2 * 0.08);
    const edge = [pagePt(0, 44, 0.5), pagePt(0, 44, 0.5), pagePt(-30, 22, 0.5), pagePt(-45, 22, 0.5)][k2];
    fxBurst("dw6_ink", edge, 3 - k2 * 0.5, 7);
    fx("dw6_halo", edge);
  }));
  scene.every(1, (e) => {
    const p = Math.min(1, e / 48), w = 58 * (1 - 0.86 * p), h = 42 * (1 - 0.86 * p), bc = 44 * (1 - p) + 4 * p;
    for (let i = 0; i < 3; i++) {
      const k2 = e * 3.3 + i;
      fx(i ? "dw6_glint" : "dw6_script", pagePt((rnd(k2) - 0.5) * 2 * w, bc + (rnd(k2 + 0.4) - 0.5) * 2 * h, 0.6));
    }
  }, T_FOLD + 2, T_FOLD + 50);
  const leafAt = () => up(bookAt, 1.2);
  scene.at(T_FLY - 12, () => {
    book.state(BOOK.gather).skin(0);
    fxBurst("dw6_letters", up(bookAt, 1.5), 1.6, 5);
  });
  scene.span(T_FLY, T_FLY + FLY2, (p) => {
    const from = pageO, to = leafAt();
    const pos = bezier(from, up(lerp(from, to, 0.5), 4), to, smooth(p));
    page?.move(pos, faceOrigin(pos));
    fx("dw6_trail", up(pos, 0.6));
    fx("dw6_stream", up(pos, 0.6));
    fx("dw6_stream", bezier(from, up(lerp(from, to, 0.5), 4), to, Math.max(0, smooth(p) - 0.05)));
    if (scene.tick % 2 === 0) fx("dw6_script", up(pos, 0.3 + rnd(scene.tick)));
  });
  scene.every(1, (e) => {
    for (const ph of [0, 120, 240]) {
      const r = 4.5 * (1 - e % 20 / 20) + 0.6, a = (e * 17 + ph) * DEG;
      fx("dw6_stream", add(bookAt, { x: Math.cos(a) * r, y: 0.3 + r / 5 * 2, z: Math.sin(a) * r }));
    }
  }, T_FLY - 12, T_CLOSE + 18);
  scene.at(T_SLIP, () => {
    page?.state(PAGE.slip);
    fx("dw6_flare", up(bookAt, 1));
    fx("dw6_halo", up(bookAt, 1.2));
  });
  scene.at(T_SLIP + 16, () => {
    if (page) scene.despawn(page);
    page = void 0;
  });
  scene.at(T_CLOSE, () => {
    book.state(BOOK.close);
    snd("dw6_close", bookAt, 1.3);
  });
  scene.at(T_CLOSE + 19, () => {
    fx("dw6_flare", bookAt);
    fx("dw6_wave", up(bookAt, -2.2));
    fxRing("dw6_letters", up(bookAt, -1.6), 3, 6);
    snd("dw6_amen", bookAt, 1.5);
    boundary.state(BOUND.unwrite);
    boundaryOn = false;
  });
  scene.every(1, (e) => {
    for (let i = 0; i < 4; i++) fx("dw6_letters", ringPt(rnd(e * 3 + i) * 360, 0.4));
  }, T_CLOSE + 19, T_CLOSE + 49);
  const returnSrc = [-100, -60, -20, 20, 60, 100].map((th) => G(Ds + 15 * Math.cos(th * DEG), 15 * Math.sin(th * DEG), 1));
  scene.every(1, (e) => {
    returnSrc.forEach((src, j) => {
      const to = up(bookAt, 0.8);
      fx("dw6_stream", bezier(src, up(lerp(src, to, 0.5), 6), to, (e * 0.035 + j * 0.17) % 1));
    });
  }, T_FOLD - 30, T_CLOSE + 10);
  scene.at(T_CLOSE + 51, () => scene.despawn(boundary));
  scene.at(T_VANISH, () => {
    book.state(BOOK.vanish);
    bookShows = false;
    snd("dw6_seal", bookAt, 1.6);
    fx("dw6_pillar", up(bookAt, 4));
    fx("dw6_fountain", up(bookAt, -1));
    fx("dw6_halo", up(bookAt, 1));
  });
  scene.every(1, (e) => {
    const h = 0.6 + e * 0.09;
    fxRing("dw6_stream", up(bookAt, h), 1.4 + e * 0.035, 4, e * 23);
    if (e % 3 === 0) fx("dw6_glint", up(bookAt, h + 1.2));
  }, T_VANISH + 2, T_VANISH + 30);
  scene.at(T_VANISH + 24, () => {
    fx("dw6_flare", up(bookAt, 3));
    fx("dw6_wave", up(bF, -2.4));
    fxBurst("dw6_letters", up(bookAt, 3), 2.5, 8);
  });
  scene.at(T_VANISH + 30, () => scene.despawn(book));
  scene.every(1, (e) => {
    const n = e < 30 ? 4 : 2;
    for (let i = 0; i < n; i++) {
      const k2 = e * 5.1 + i * 1.7;
      const a = rnd(k2) * 2 * Math.PI, r = 2 + Math.sqrt(rnd(k2 + 1)) * 14;
      const p = { x: bF.x + Math.cos(a) * r, y: bF.y + 1 + rnd(k2 + 2) * 6, z: bF.z + Math.sin(a) * r };
      if (distXZ(p, c0) > 6) fx(i % 2 ? "dw6_ember" : (e + i) % 3 ? "dw6_motes" : "dw6_script", p);
    }
  }, T_CLOSE + 20, T_END - 2);
  scene.endAt(T_END);
});

// src/config/dn01.ts
var DN01 = {
  // ---------------------------------------------------------------- targeting / the dream-road
  /** Radius around the focus point in which the procession looks for enemies. */
  radius: 14,
  /** How far from the aim point the spell snaps onto the nearest hostile. */
  snap: 10,
  /** Road starts this many blocks behind the caster, this high above the caster's feet. */
  startBehind: 3,
  startHeight: 2.5,
  /** Forward reach of the road end (blocks from the caster), clamped to this range. */
  minReach: 9,
  maxReach: 22,
  /** The road ends this many blocks short of the focus, this high above the ground there. */
  endBack: 4,
  endHeight: 1.2,
  /** Height of the road's arc above the straight line, and its sideways S-curve amplitude. */
  apex: 8,
  curve: 3.5,
  /** Desired spacing of road segments (blocks) and the maximum number of segments. */
  segSpacing: 3.3,
  maxSegments: 12,
  /** Ticks between successive segments unrolling / rolling up. */
  unrollStep: 2,
  // ---------------------------------------------------------------- the procession
  /** Ticks at which the horse, stag, bird and doll appear at the road's gate. */
  spawnAt: [12, 20, 28, 36],
  /** Ticks each creature holds at the gate (arrival animation) before it starts to walk. */
  gateHold: 14,
  /** Parade speed along the road (blocks per second). */
  paradeSpeed: 14,
  // ---------------------------------------------------------------- stacking bonus (the core mechanic)
  /** Bonus damage per different creature that already struck the same enemy (2nd hit +k, 3rd +2k, 4th +3k). */
  stackBonus: 3,
  /** Share of the stack bonus a creature gets on its own repeated hits (doll pulses, later swoops). */
  repeatBonusShare: 0.35,
  /** Extra burst when all four creatures have struck the same enemy ("full moon"). */
  fullMoonBonus: 8,
  fullMoonRadius: 2.5,
  /** Height of the crescent mark above a struck enemy. */
  markHeight: 2.6,
  // ---------------------------------------------------------------- porcelain horse: straight gallop line
  horseDamage: 7,
  /** Length of the charge line and gallop speed (blocks / second). */
  horseLength: 16,
  horseSpeed: 16,
  /** Half-width of the line: enemies this close to the horse are trampled (pierce). */
  horseHitRadius: 1.9,
  horseKnockback: 1.3,
  horseLift: 0.45,
  // ---------------------------------------------------------------- mist-glass stag: three bounding impacts
  stagDamage: 6,
  stagBounds: 3,
  /** Landing blast radius (each landing is telegraphed). */
  stagRadius: 2.6,
  /** Peak height of a bound above the straight line (blocks) plus a share of its length. */
  stagHop: 3.5,
  stagHopPerBlock: 0.15,
  /** Without targets the stag bounds this far each time. */
  stagIdleStride: 4.5,
  // ---------------------------------------------------------------- curtain-winged bird: swooping arcs
  birdDamage: 5,
  birdSwoops: 3,
  /** Enemies this close to the bird during the low part of a swoop are struck. */
  birdHitRadius: 2,
  /** Height the bird climbs back to between swoops, and its skim height. */
  birdAir: 6,
  birdSkim: 1.1,
  /** A second target this close to the first is included in the same swoop. */
  birdPairRange: 7,
  // ---------------------------------------------------------------- floating star doll: drift then rhythmic starburst
  /** Ticks the doll takes to drift (in hesitant steps) to its pulse point. */
  dollDrift: 28,
  /** Syncopated pulse offsets in ticks (short-short-long-short-long). */
  dollPulses: [0, 6, 16, 22, 34],
  dollDamage: 2.5,
  dollRadius: 4.5,
  /** Hover height of the doll above the ground at its pulse point. */
  dollHover: 1.4,
  /** Slowness applied by each pulse (ticks, amplifier). */
  dollSlowTicks: 30,
  dollSlowAmp: 1,
  // ---------------------------------------------------------------- staging
  /** The Sleeping Moon hangs this far above the road's apex. */
  moonAbove: 6,
  /** Light blocks placed every n-th road segment while the road exists. */
  lightEvery: 3
};

// src/spells/dn01_reverie_procession.ts
var HORSE = { hidden: 0, arrive: 1, parade: 2, charge: 3, depart: 4 };
var STAG = { hidden: 0, arrive: 1, parade: 2, leapA: 3, leapB: 4, depart: 5 };
var BIRD = { hidden: 0, arrive: 1, glide: 2, swoopA: 3, swoopB: 4, depart: 5 };
var DOLL = { hidden: 0, arrive: 1, float: 2, pulseA: 3, pulseB: 4, depart: 5 };
var ROAD = { hidden: 0, unroll: 1, hold: 2, rollup: 3 };
var MOON = { hidden: 0, rise: 1, sleep: 2, set: 3 };
var MARK4 = { hidden: 0, appear: 1, hold: 2, flare: 3, vanish: 4 };
var T3 = {
  roadAnim: 16,
  moonRise: 28,
  moonSet: 28,
  markAppear: 7,
  markFlare: 8,
  markVanish: 8,
  horseDepart: 22,
  stagLeap: 22,
  stagLaunch: 6,
  stagLand: 17,
  stagDepart: 24,
  birdSwoop: 24,
  birdLowFrom: 8,
  birdLowTo: 16,
  birdDepart: 24,
  dollPulsePeak: 3,
  dollDepart: 24
};
var ROAD_MODEL_LEN = 3.3;
var ORDER = ["horse", "stag", "bird", "doll"];
var ACTOR2 = { horse: "dn_parade_horse", stag: "dn_parade_stag", bird: "dn_parade_bird", doll: "dn_parade_doll" };
var dn01_reverie_procession_default = defineSpell("dn01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, DN01.snap);
  const fwd = aim.forward;
  const side = right(fwd);
  const base = { ...caster.location };
  const reach = clamp(dot(flat(sub(center, base)), fwd), DN01.minReach, DN01.maxReach);
  const endXZ = add(base, mul(fwd, reach - DN01.endBack));
  const endGround = groundBelow(dim, { x: endXZ.x, y: Math.max(center.y, base.y) + 3, z: endXZ.z });
  const start = up(add(base, mul(fwd, -DN01.startBehind)), DN01.startHeight);
  const end = up(endGround, DN01.endHeight);
  const ctrl = [start];
  for (const f of [0.25, 0.5, 0.75]) {
    const p = lerp(start, end, f);
    ctrl.push(add(up(p, DN01.apex * Math.pow(Math.sin(Math.PI * f), 0.8)), mul(side, DN01.curve * Math.sin(2 * Math.PI * f))));
  }
  ctrl.push(end);
  const N3 = 96;
  const P6 = [];
  const S6 = [];
  for (let i = 0; i <= N3; i++) {
    P6.push(spline(ctrl, i / N3));
    S6.push(i ? S6[i - 1] + dist(P6[i], P6[i - 1]) : 0);
  }
  const L3 = S6[N3];
  function road(s) {
    const x = clamp(s, 0, L3);
    let i = 1;
    while (i < N3 && S6[i] < x) i++;
    const f = (x - S6[i - 1]) / Math.max(1e-6, S6[i] - S6[i - 1]);
    return { p: lerp(P6[i - 1], P6[i], f), d: norm(sub(P6[i], P6[i - 1])) };
  }
  const pitch = (d) => Math.atan2(d.y, Math.hypot(d.x, d.z)) * 180 / Math.PI;
  const tilts = /* @__PURE__ */ new Map();
  function setTilt(a, deg) {
    const v2 = clamp(Math.round(deg), -55, 55);
    if (tilts.get(a) === v2) return;
    tilts.set(a, v2);
    a.prop("tilt", v2);
  }
  const n = clamp(Math.round(L3 / DN01.segSpacing), 5, DN01.maxSegments);
  const spacing = L3 / n;
  const travel = Math.max(20, Math.ceil(L3 / DN01.paradeSpeed * 20));
  const arrive = DN01.spawnAt.map((t) => t + DN01.gateHold + travel + 1);
  const horseRun = Math.max(10, Math.round(DN01.horseLength / DN01.horseSpeed * 20));
  const birdDone = arrive[2] + DN01.birdSwoops * T3.birdSwoop + 1;
  const dollLast = arrive[3] + 1 + DN01.dollDrift + DN01.dollPulses[DN01.dollPulses.length - 1] + 10;
  const stagDone = arrive[1] + DN01.stagBounds * T3.stagLeap + 2;
  const horseDone = arrive[0] + horseRun + 2;
  const tRoll = Math.max(birdDone, dollLast, stagDone, horseDone) + 4;
  const tEnd = tRoll + (n - 1) * DN01.unrollStep + T3.roadAnim + 8;
  const segs = [];
  const lights = blocksFor(scene);
  sound(dim, "dn_parade_open", start, 1.2);
  for (let i = 0; i < n; i++) {
    const { p, d } = road((i + 0.5) * spacing);
    const kind = i === 0 ? 2 : i === n - 1 ? 1 : i % 4 === 2 ? 1 : i % 4 === 0 ? i % 8 === 0 ? 2 : 3 : 0;
    scene.at(2 + i * DN01.unrollStep, () => {
      const a = scene.spawn("dn_parade_road", p, { yaw: yawOf(d), kind, size: spacing / ROAD_MODEL_LEN, state: ROAD.unroll });
      setTilt(a, pitch(d));
      segs[i] = a;
      particle(dim, "dn_parade_confetti", up(p, 1.2));
      if (i % DN01.lightEvery === 1) lights.place(up(p, 1.5), LIGHT);
      scene.after(T3.roadAnim, () => a.state(ROAD.hold));
    });
  }
  let apexI = 0;
  for (let i = 0; i <= N3; i++) if (P6[i].y > P6[apexI].y) apexI = i;
  const moonAt = add(up(P6[apexI], DN01.moonAbove), mul(side, -1.5));
  let moon;
  scene.at(4, () => {
    moon = scene.spawn("dn_parade_moon", moonAt, { yaw: yawOf(sub(base, moonAt)), state: MOON.rise });
    sound(dim, "dn_parade_moon", moonAt, 1);
    burst(dim, "dn_parade_trail", moonAt, 3, 8);
  });
  scene.at(4 + T3.moonRise, () => moon?.state(MOON.sleep));
  scene.at(8, () => sound(dim, "dn_parade_theme", P6[apexI], 1.1));
  scene.every(10, () => particle(dim, "dn_parade_note", up(moonAt, -3)), 30, tRoll);
  const hits = /* @__PURE__ */ new Map();
  function strike(e, who, amount) {
    if (!isAlive(e)) return;
    let h = hits.get(e.id);
    if (!h) {
      h = { e, by: /* @__PURE__ */ new Set(), full: false };
      hits.set(e.id, h);
    }
    const first = !h.by.has(who);
    const others = h.by.size - (first ? 0 : 1);
    const bonus = DN01.stackBonus * others * (first ? 1 : DN01.repeatBonusShare);
    if (!damage(e, amount + bonus, caster)) return;
    h.by.add(who);
    const at = e.location;
    particle(dim, "dn_parade_crescent", up(at, 1.2));
    particle(dim, "dn_parade_groundmoon", up(groundBelow(dim, at), 0.12));
    particle(dim, "dn_parade_shard", up(at, 1));
    sound(dim, "dn_parade_hit", at, 0.9, 0.9 + 0.12 * h.by.size);
    if (!first || !isAlive(e)) return;
    const count = h.by.size;
    if (!h.mark || !h.mark.valid) {
      const mk = scene.spawn("dn_parade_mark", up(at, DN01.markHeight), { state: MARK4.appear, skin: count - 1 });
      h.mark = mk;
      scene.follow(mk, e, DN01.markHeight);
      scene.after(T3.markAppear, () => mk.state(MARK4.hold));
    } else {
      const mk = h.mark;
      mk.skin(count - 1).state(MARK4.flare);
      scene.after(T3.markFlare, () => mk.state(MARK4.hold));
    }
    if (count === ORDER.length && !h.full) {
      h.full = true;
      const hh = h;
      scene.after(4, () => {
        if (!isAlive(hh.e)) return;
        const c = hh.e.location;
        sound(dim, "dn_parade_fullmoon", c, 1.3);
        particle(dim, "fx_flash", up(c, 1.5));
        particle(dim, "dn_parade_pulse", up(groundBelow(dim, c), 0.2));
        ring(dim, "dn_parade_crescent", up(c, 1.5), 1.5, 6);
        damage(hh.e, DN01.fullMoonBonus, caster);
        for (const o of hostiles(dim, c, DN01.fullMoonRadius, caster)) if (o.id !== hh.e.id) damage(o, DN01.fullMoonBonus * 0.5, caster);
      });
    }
  }
  function parade(who, idx, lift, sway, tiltShare, onArrive) {
    const t0 = DN01.spawnAt[idx];
    let a;
    scene.at(t0, () => {
      const { p, d } = road(0);
      a = scene.spawn(ACTOR2[who], up(p, lift(0)), { yaw: yawOf(d), state: 1 });
      sound(dim, "dn_parade_arrive", p, 0.9, 0.85 + idx * 0.12);
      sound(dim, `dn_parade_voice_${who}`, p, 1);
      burst(dim, "dn_parade_confetti", up(p, 1.5), 1.2, 3);
    });
    scene.at(t0 + DN01.gateHold, () => a?.state(2));
    scene.span(t0 + DN01.gateHold, arrive[idx], (_p, e) => {
      if (!a) return;
      const { p, d } = road(e / travel * L3);
      const off = mul(side, sway * Math.sin(e * 0.15 + idx));
      a.move(add(up(p, lift(e)), off), yawOf(d));
      setTilt(a, pitch(d) * tiltShare);
      if (e % 12 === idx * 3) particle(dim, "dn_parade_note", up(p, 2.8));
    });
    scene.at(arrive[idx], () => {
      if (a && a.valid) {
        setTilt(a, 0);
        onArrive(a);
      }
    });
  }
  parade("horse", 0, () => 0, 0, 0.85, horseCharge);
  parade("stag", 1, () => 0, 0, 0.85, stagBounds);
  parade("bird", 2, (e) => 2 + 0.4 * Math.sin(e * 0.2), 0.8, 0.5, birdSwoops);
  parade("doll", 3, (e) => 1 + 0.3 * Math.sin(e * 0.13), 0.5, 0, dollDance);
  function horseCharge(h) {
    const from = h.loc;
    const foes = hostiles(dim, center, DN01.radius, caster);
    let dir = fwd;
    let best = -1;
    for (const f of foes) {
      const d = norm(flat(sub(f.location, from)));
      const tip = add(from, mul(d, DN01.horseLength));
      const cnt = foes.filter((o) => distToSegment({ ...o.location, y: from.y }, from, { ...tip, y: from.y }) < DN01.horseHitRadius + 0.6).length;
      if (cnt > best) {
        best = cnt;
        dir = d;
      }
    }
    const t0 = scene.tick;
    const yaw = yawOf(dir);
    h.state(HORSE.charge).face(yaw);
    sound(dim, "dn_parade_charge", from, 1.2);
    for (let k2 = 1; k2 <= 6; k2++) {
      particle(dim, "dn_parade_lane", up(groundBelow(dim, up(add(from, mul(dir, k2 * DN01.horseLength / 6)), 2)), 0.15));
    }
    const hit = /* @__PURE__ */ new Set();
    scene.span(t0 + 1, t0 + 1 + horseRun, (p, e) => {
      const xz = add(from, mul(dir, DN01.horseLength * p));
      const g = groundBelow(dim, { x: xz.x, y: from.y + 1, z: xz.z });
      const pos = { x: xz.x, y: from.y + (g.y - from.y) * Math.min(1, p * 4), z: xz.z };
      h.move(pos, yaw);
      if (e % 3 === 0) particle(dim, "dn_parade_trail", up(pos, 1.6));
      for (const f of hostiles(dim, up(pos, 0.8), DN01.horseHitRadius + 1.2, caster)) {
        if (hit.has(f.id) || distXZ(f.location, pos) > DN01.horseHitRadius) continue;
        hit.add(f.id);
        strike(f, "horse", DN01.horseDamage);
        shove(f, add(dir, mul(norm(flat(sub(f.location, pos))), 0.6)), DN01.horseKnockback, DN01.horseLift);
      }
    });
    scene.at(t0 + horseRun + 2, () => {
      h.state(HORSE.depart);
      sound(dim, "dn_parade_depart", h.loc, 0.9, 1.1);
      burst(dim, "dn_parade_shard", up(h.loc, 2), 1, 4);
    });
    scene.at(t0 + horseRun + 2 + T3.horseDepart, () => scene.despawn(h));
  }
  function stagBounds(st2) {
    const t0 = scene.tick;
    const struck = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < DN01.stagBounds; k2++) {
      const tk = t0 + k2 * T3.stagLeap;
      scene.at(tk, () => {
        if (!st2.valid) return;
        const from = st2.loc;
        const all = hostiles(dim, center, DN01.radius, caster);
        const fresh = all.filter((e) => !struck.has(e.id));
        const pool = fresh.length ? fresh : all;
        pool.sort((a, b) => distXZ(a.location, from) - distXZ(b.location, from));
        const target = pool[0];
        let land = target ? groundBelow(dim, target.location) : groundBelow(dim, up(add(add(from, mul(fwd, DN01.stagIdleStride)), mul(side, (k2 % 2 ? -1 : 1) * 2)), 3));
        const warn = scene.spawn("telegraph", land, { kind: 1, size: DN01.stagRadius, state: 1 });
        st2.state(k2 % 2 ? STAG.leapB : STAG.leapA).face(yawOf(sub(land, from)));
        scene.every(1, () => {
          if (target && isAlive(target)) {
            land = groundBelow(dim, target.location);
            warn.move(land);
          }
        }, tk + 1, tk + T3.stagLaunch);
        let a0 = from;
        let hop = DN01.stagHop;
        scene.at(tk + T3.stagLaunch, () => {
          a0 = st2.loc;
          hop = DN01.stagHop + DN01.stagHopPerBlock * distXZ(a0, land);
          sound(dim, "dn_parade_step", a0, 0.8, 1.1);
        });
        scene.span(tk + T3.stagLaunch, tk + T3.stagLand + 1, (p, e) => {
          const q = lerp(a0, land, p);
          st2.move(up(q, hop * 4 * p * (1 - p)), yawOf(flat(sub(land, a0))));
          if (e % 3 === 1) particle(dim, "dn_parade_mistpuff", up(q, hop * 4 * p * (1 - p) + 1.5));
        });
        scene.at(tk + T3.stagLand, () => {
          particle(dim, "dn_parade_groundmoon", up(land, 0.15));
          particle(dim, "dn_parade_mistpuff", up(land, 0.3));
          burst(dim, "dn_parade_shard", up(land, 0.8), 1, 3);
          sound(dim, "dn_parade_land", land, 1.1);
          for (const e of hostiles(dim, land, DN01.stagRadius, caster)) {
            struck.add(e.id);
            strike(e, "stag", DN01.stagDamage);
            knockback(e, land, 0.5, 0.35);
          }
          warn.state(3);
          scene.after(8, () => scene.despawn(warn));
        });
      });
    }
    const tDep = t0 + DN01.stagBounds * T3.stagLeap + 2;
    scene.at(tDep, () => {
      st2.state(STAG.depart);
      sound(dim, "dn_parade_depart", st2.loc, 0.9, 0.95);
      burst(dim, "dn_parade_mistpuff", up(st2.loc, 2), 1.2, 4);
    });
    scene.at(tDep + T3.stagDepart, () => scene.despawn(st2));
  }
  function birdSwoops(b) {
    const t0 = scene.tick;
    const everHit = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < DN01.birdSwoops; k2++) {
      const tk = t0 + k2 * T3.birdSwoop;
      scene.at(tk, () => {
        if (!b.valid) return;
        const p0 = b.loc;
        const foes = hostiles(dim, center, DN01.radius, caster);
        foes.sort((x, y) => (everHit.has(x.id) ? 1 : 0) - (everHit.has(y.id) ? 1 : 0) || distXZ(x.location, p0) - distXZ(y.location, p0));
        let la;
        let lb;
        if (foes.length) {
          la = groundBelow(dim, foes[0].location);
          const second = foes.slice(1).find((e) => distXZ(e.location, foes[0].location) <= DN01.birdPairRange);
          lb = second ? groundBelow(dim, second.location) : groundBelow(dim, up(add(la, mul(norm(flat(sub(la, p0))), 4)), 2));
        } else {
          la = groundBelow(dim, up(add(center, mul(side, (k2 - 1) * 3.5)), 3));
          lb = groundBelow(dim, up(add(la, mul(fwd, 4)), 3));
        }
        la = up(la, DN01.birdSkim);
        lb = up(lb, DN01.birdSkim);
        const away = distXZ(la, lb) > 0.5 ? norm(flat(sub(lb, la))) : fwd;
        const path = [p0, la, lb, up(add(lb, mul(away, 6)), DN01.birdAir)];
        b.state(k2 % 2 ? BIRD.swoopB : BIRD.swoopA);
        sound(dim, "dn_parade_swoop", p0, 1);
        const hit = /* @__PURE__ */ new Set();
        let prev = p0;
        scene.span(tk + 1, tk + T3.birdSwoop + 1, (p, e) => {
          const pos = spline(path, p);
          const d = sub(pos, prev);
          prev = pos;
          b.move(pos, yawOf(d.x * d.x + d.z * d.z > 1e-6 ? d : away));
          setTilt(b, pitch(d) * 0.6);
          if (e % 4 === 0) particle(dim, "dn_parade_trail", pos);
          if (e < T3.birdLowFrom - 2 || e > T3.birdLowTo + 2) return;
          for (const f of hostiles(dim, pos, DN01.birdHitRadius + 2, caster)) {
            if (hit.has(f.id) || dist(up(f.location, 0.9), pos) > DN01.birdHitRadius + 0.6) continue;
            hit.add(f.id);
            everHit.add(f.id);
            strike(f, "bird", DN01.birdDamage);
            shove(f, d, 0.5, 0.3);
          }
        });
      });
    }
    const tDep = t0 + DN01.birdSwoops * T3.birdSwoop + 1;
    scene.at(tDep, () => {
      b.state(BIRD.depart);
      setTilt(b, 0);
      sound(dim, "dn_parade_depart", b.loc, 0.9, 1.25);
    });
    scene.at(tDep + T3.birdDepart, () => scene.despawn(b));
  }
  function dollDance(dl) {
    const t0 = scene.tick;
    const from = dl.loc;
    const foes = hostiles(dim, center, DN01.radius, caster, 6);
    let spot = center;
    if (foes.length) {
      let sx = 0;
      let sz = 0;
      for (const f of foes) {
        sx += f.location.x;
        sz += f.location.z;
      }
      spot = groundBelow(dim, { x: sx / foes.length, y: center.y + 3, z: sz / foes.length });
    }
    const hover = up(spot, DN01.dollHover);
    const warn = scene.spawn("telegraph", spot, { kind: 1, size: DN01.dollRadius, state: 4 });
    scene.span(t0 + 1, t0 + 1 + DN01.dollDrift, (p) => {
      const k2 = Math.min(3, Math.floor(p * 4));
      const q = Math.min(1, (k2 + smooth(Math.min(1, (p * 4 - k2) * 1.6))) / 4);
      dl.move(lerp(from, hover, q));
    });
    const tp = t0 + 1 + DN01.dollDrift;
    scene.at(tp, () => warn.state(2));
    const pitches = [1, 1.12, 0.89, 1, 1.26];
    DN01.dollPulses.forEach((off, k2) => {
      scene.at(tp + off, () => {
        dl.state(k2 % 2 ? DOLL.pulseB : DOLL.pulseA);
        sound(dim, "dn_parade_pulse", hover, 1, pitches[k2 % pitches.length]);
      });
      scene.at(tp + off + T3.dollPulsePeak, () => {
        particle(dim, "dn_parade_pulse", up(spot, 0.2));
        ring(dim, "dn_parade_glint", up(spot, 0.8), DN01.dollRadius * 0.8, 6, k2 * 30);
        for (const e of hostiles(dim, spot, DN01.dollRadius, caster)) {
          strike(e, "doll", DN01.dollDamage);
          effect(e, "slowness", DN01.dollSlowTicks, DN01.dollSlowAmp);
        }
      });
    });
    const last = tp + DN01.dollPulses[DN01.dollPulses.length - 1] + 10;
    scene.at(last, () => {
      warn.state(3);
      dl.state(DOLL.depart);
      sound(dim, "dn_parade_depart", hover, 0.9, 1.4);
      burst(dim, "dn_parade_trail", hover, 1.2, 6);
    });
    scene.at(last + 8, () => scene.despawn(warn));
    scene.at(last + T3.dollDepart, () => scene.despawn(dl));
  }
  scene.at(tRoll, () => {
    sound(dim, "dn_parade_rollup", P6[apexI], 1.1);
    for (const h of hits.values()) {
      const mk = h.mark;
      if (mk && mk.valid) {
        mk.state(MARK4.vanish);
        scene.after(T3.markVanish, () => scene.despawn(mk));
      }
    }
    moon?.state(MOON.set);
    scene.after(T3.moonSet, () => {
      if (moon) scene.despawn(moon);
    });
  });
  for (let i = 0; i < n; i++) {
    const t = tRoll + (n - 1 - i) * DN01.unrollStep;
    scene.at(t, () => {
      const a = segs[i];
      if (!a) return;
      a.state(ROAD.rollup);
      particle(dim, "dn_parade_confetti", up(a.loc, 1));
      scene.after(T3.roadAnim, () => scene.despawn(a));
    });
  }
  scene.endAt(tEnd);
});

// src/config/dn02.ts
var DN02 = {
  /** How far from the aim point the spell looks for a victim when nothing is under the crosshair (blocks). */
  snapRadius: 10,
  /**
   * Distance from the door plane to the victim's grip point (blocks).  Must match GRAB_Z in
   * tools/assets/dn_guest.py (56/16): the Guest's stretched hands close exactly there.
   */
  standoff: 3.5,
  /** Where the drag ends, measured from the door plane (blocks).  Matches PULL_Z (18/16) in dn_guest.py. */
  pullStop: 1.125,
  /** If the victim has wandered farther than this from the grip point when the hands close, the Guest grasps air. */
  grabRange: 2.4,
  /**
   * The Guest only reaches for someone who is really there: an enemy within this distance of the grip
   * point when it has leaned out of the doorway.  It is pulled into the closing hands.
   */
  reachRadius: 5.5,
  /** With nobody in reach the Guest waits this long at the threshold for someone to come close, then goes back inside. */
  waitSeconds: 2.5,
  /** Slowness amplifier while the door creaks open (the dread beat) and while the arms reach. */
  dreadSlowAmp: 1,
  reachSlowAmp: 3,
  /** Squeeze damage dealt every `squeezeEvery` ticks while the victim is held (restraint lasts 2.4 s). */
  squeezeEvery: 12,
  squeezeDamage: 3,
  /** The slam: radius around the drag end point, damage to everything inside, and the finisher bonus for the held victim. */
  slamRadius: 3,
  slamDamage: 16,
  finisherBonus: 14,
  /** Knockback away from the door (horizontal strength, lift). */
  slamKnock: 2.4,
  slamLift: 0.55
};

// src/spells/dn02_nightmare_intrusion.ts
var DOOR = { hidden: 0, manifest: 1, closed: 2, handle: 3, open: 4, held: 5, slam: 6, vanish: 7 };
var GUEST = { hidden: 0, emerge: 1, reach: 2, grab: 3, pull: 4, withdraw: 5, miss: 6 };
var A2 = { manifest: 24, handle: 28, open: 24, slamShut: 3, vanish: 20, emerge: 52, reach: 24, grab: 12, pull: 32, withdraw: 22 };
var T_CLOSED = A2.manifest;
var T_HANDLE = T_CLOSED + 6;
var T_OPEN2 = T_HANDLE + A2.handle;
var T_EMERGE = T_OPEN2 + 6;
var T_HELD = T_OPEN2 + A2.open;
var T_REACH = T_EMERGE + A2.emerge;
var dn02_nightmare_intrusion_default = defineSpell("dn02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center, target } = focus(caster, aim, DN02.snapRadius);
  let victim = target && isAlive(target) ? target : void 0;
  const spot = victim ? groundBelow(dim, victim.location) : center;
  let dir = flat(sub(spot, caster.location));
  dir = len(dir) < 0.5 ? aim.forward : norm(dir);
  const door = groundBelow(dim, add(spot, mul(dir, DN02.standoff)));
  const facing = mul(dir, -1);
  const yaw = yawOf(facing);
  const rgt = right(facing);
  const L3 = (x, y, z) => add(add(up(door, y / 16), mul(facing, -z / 16)), mul(rgt, x / 16));
  const gripAt = L3(0, 0, -DN02.standoff * 16);
  const dragEnd = L3(0, 0, -DN02.pullStop * 16);
  const keyhole = L3(-14, 32.6, -2.5);
  const lights = blocksFor(scene);
  const d = scene.spawn("dn_guest_door", door, { yaw, state: DOOR.manifest, skin: 0 });
  const warn = scene.spawn("telegraph", up(dragEnd, 0.05), { kind: 1, size: DN02.slamRadius, state: 4 });
  scene.at(40, () => warn.state(2));
  sound(dim, "dn_guest_manifest", door, 1.1);
  burst(dim, "dn_guest_mote", L3(0, 44, 0), 2.2, 6);
  scene.at(6, () => particle(dim, "dn_guest_dust", up(door, 0.2)));
  scene.at(14, () => burst(dim, "dn_guest_scrap", L3(0, 82, -2), 1.2, 3));
  scene.at(T_CLOSED, () => d.state(DOOR.closed));
  scene.at(T_HANDLE, () => {
    d.state(DOOR.handle);
    sound(dim, "dn_guest_handle", keyhole, 1);
    if (victim && isAlive(victim)) effect(victim, "slowness", T_REACH - T_HANDLE, DN02.dreadSlowAmp);
  });
  scene.at(T_HANDLE + 4, () => particle(dim, "dn_guest_mote", keyhole));
  scene.at(T_HANDLE + 22, () => particle(dim, "dn_guest_cracklight", L3(-14, 32, -2)));
  scene.at(T_OPEN2, () => {
    d.state(DOOR.open);
    sound(dim, "dn_guest_creak", door, 1.1);
    lights.place(L3(0, 40, -12), LIGHT);
    particle(dim, "dn_guest_dust", L3(0, 2, -6));
  });
  scene.at(T_OPEN2 + 8, () => sound(dim, "dn_guest_drone", L3(0, 30, 6), 1));
  let lamps = true;
  scene.every(7, () => {
    if (lamps && d.valid) particle(dim, "dn_guest_lamp", L3(0, 36, -3));
  }, T_OPEN2 + 10, T_REACH + 200);
  scene.at(T_HELD, () => d.state(DOOR.held));
  let guest;
  scene.at(T_EMERGE, () => {
    guest = scene.spawn("dn_guest", door, { yaw, state: GUEST.emerge });
    sound(dim, "dn_guest_approach", L3(0, 30, 10), 1);
  });
  scene.at(T_EMERGE + 29, () => {
    sound(dim, "dn_guest_clicks", L3(-20, 50, -4), 1);
    particle(dim, "dn_guest_dust", L3(-20, 52, -5));
  });
  scene.at(T_EMERGE + 40, () => {
    sound(dim, "dn_guest_voice", L3(-20, 70, -14), 1);
    particle(dim, "dn_guest_breath", L3(-24, 70, -22));
  });
  const inReach = (e) => distXZ(e.location, gripAt) <= DN02.reachRadius && Math.abs(e.location.y - door.y) <= 5;
  const pick = () => {
    if (victim && isAlive(victim) && inReach(victim)) return victim;
    return hostiles(dim, gripAt, DN02.reachRadius, caster).find(inReach);
  };
  let decided = false;
  const deadline = T_REACH + secs(DN02.waitSeconds);
  scene.every(4, () => {
    if (decided) return;
    const v2 = pick();
    if (v2) {
      decided = true;
      victim = v2;
      take2(scene.tick, v2);
    } else if (scene.tick >= deadline) {
      decided = true;
      goBack(scene.tick);
    }
  }, T_REACH, deadline + 5);
  scene.every(22, () => {
    if (!decided) {
      sound(dim, "dn_guest_clicks", L3(-20, 50, -4), 0.8, 0.9);
      particle(dim, "dn_guest_breath", L3(-24, 70, -22));
    }
  }, T_REACH + 10, deadline);
  function goBack(t0) {
    guest?.state(GUEST.withdraw);
    sound(dim, "dn_guest_clicks", L3(0, 40, -6), 0.9, 1.35);
    warn.state(3);
    scene.at(t0 + 8, () => scene.despawn(warn));
    scene.at(t0 + A2.withdraw, () => {
      if (guest) scene.despawn(guest);
    });
    scene.at(t0 + A2.withdraw + 2, () => {
      lamps = false;
      d.state(DOOR.slam);
      sound(dim, "dn_guest_slam", L3(0, 40, -2), 0.7, 1.2);
    });
    scene.at(t0 + A2.withdraw + 2 + A2.slamShut, () => {
      lights.remove(L3(0, 40, -12));
      particle(dim, "dn_guest_dust", L3(0, 2, -4));
    });
    vanishAt(t0 + A2.withdraw + 2 + A2.slamShut + 14);
  }
  function take2(t0, v2) {
    const tGrab = t0 + A2.reach, tGrip = tGrab + 2, tPull = tGrab + A2.grab, tWithdraw = tPull + A2.pull;
    const tSlam = tWithdraw + 5, tImpact = tSlam + A2.slamShut;
    let caught = false;
    let release2;
    guest?.state(GUEST.reach);
    sound(dim, "dn_guest_voice", L3(0, 74, -30), 1.1, 0.9);
    effect(v2, "slowness", A2.reach + 4, DN02.reachSlowAmp);
    scene.at(t0 + 10, () => sound(dim, "dn_guest_clicks", L3(0, 50, -30), 1, 1.2));
    scene.at(tGrab, () => {
      caught = isAlive(v2) && distXZ(v2.location, gripAt) <= DN02.reachRadius + 1.5;
      guest?.state(caught ? GUEST.grab : GUEST.withdraw);
      if (!caught) {
        decided = true;
        goBackAfterMiss(tGrab);
      }
    });
    scene.at(tGrip, () => {
      if (!caught || !isAlive(v2)) {
        caught = false;
        return;
      }
      const from = { ...v2.location };
      const anchor = { x: gripAt.x, y: v2.location.y, z: gripAt.z };
      const end = { x: dragEnd.x, y: v2.location.y, z: dragEnd.z };
      release2 = restrain(scene, v2, tImpact - tGrip, anchor);
      scene.every(1, () => {
        if (!isAlive(v2)) return;
        const t = scene.tick;
        if (t < tPull) {
          drag(v2, lerp(from, anchor, smooth((t - tGrip) / 6)));
          return;
        }
        drag(v2, lerp(anchor, end, smooth((t - tPull) / (A2.pull - 1))));
        if (t < tWithdraw && (t - tPull) % 3 === 0) particle(dim, "dn_guest_drag", v2.location);
      }, tGrip, tImpact);
      sound(dim, "dn_guest_grab", v2.location, 1.1);
      particle(dim, "dn_guest_grip", up(v2.location, 1));
      particle(dim, "dn_guest_squeeze", up(v2.location, 1));
      scene.every(DN02.squeezeEvery, () => {
        if (!isAlive(v2)) return;
        damage(v2, DN02.squeezeDamage, caster);
        particle(dim, "dn_guest_squeeze", up(v2.location, 1.1));
      }, tGrip + 4, tImpact);
    });
    scene.at(tPull, () => {
      if (!caught) return;
      guest?.state(GUEST.pull);
      sound(dim, "dn_guest_drag", isAlive(v2) ? v2.location : gripAt, 1);
    });
    scene.at(tWithdraw, () => {
      if (!caught) return;
      guest?.state(GUEST.withdraw);
      sound(dim, "dn_guest_clicks", L3(0, 40, -6), 1, 1.35);
    });
    scene.at(tSlam, () => {
      if (!caught) return;
      lamps = false;
      d.state(DOOR.slam);
      sound(dim, "dn_guest_slam", L3(0, 40, -2), 1.8);
    });
    scene.at(tImpact, () => {
      if (!caught) return;
      release2?.();
      d.skin(1);
      lights.remove(L3(0, 40, -12));
      warn.state(3);
      scene.after(8, () => scene.despawn(warn));
      particle(dim, "dn_guest_shock", up(dragEnd, 0.15));
      particle(dim, "dn_guest_shock_v", L3(0, 36, -6));
      particle(dim, "fx_flash", L3(0, 40, -4));
      particle(dim, "dn_guest_doors", L3(0, 40, -6));
      particle(dim, "dn_guest_splinter", L3(0, 44, -3));
      particle(dim, "dn_guest_splinter", L3(-10, 20, -3));
      particle(dim, "dn_guest_cracklight", L3(0, 40, -2));
      ring(dim, "fx_dust", up(door, 0.2), 1.6, 6);
      burst(dim, "dn_guest_scrap", L3(0, 60, -4), 2, 5);
      for (const e of hostiles(dim, dragEnd, DN02.slamRadius, caster)) {
        damage(e, DN02.slamDamage + (e.id === v2.id ? DN02.finisherBonus : 0), caster);
        knockback(e, door, DN02.slamKnock, DN02.slamLift);
      }
      scene.after(8, () => {
        if (guest) scene.despawn(guest);
      });
      scene.after(6, () => particle(dim, "dn_guest_dust", L3(0, 2, -4)));
      scene.after(12, () => particle(dim, "dn_guest_cracklight", L3(0, 40, -2)));
      vanishAt(tImpact + 24);
    });
  }
  function goBackAfterMiss(t0) {
    sound(dim, "dn_guest_voice", L3(0, 60, -40), 0.9, 1.15);
    warn.state(3);
    scene.at(t0 + 8, () => scene.despawn(warn));
    scene.at(t0 + A2.withdraw, () => {
      if (guest) scene.despawn(guest);
    });
    scene.at(t0 + A2.withdraw + 2, () => {
      lamps = false;
      d.state(DOOR.slam);
      sound(dim, "dn_guest_slam", L3(0, 40, -2), 0.7, 1.2);
    });
    scene.at(t0 + A2.withdraw + 2 + A2.slamShut, () => lights.remove(L3(0, 40, -12)));
    vanishAt(t0 + A2.withdraw + 2 + A2.slamShut + 14);
  }
  function vanishAt(t) {
    scene.at(t, () => {
      d.state(DOOR.vanish);
      sound(dim, "dn_guest_hush", keyhole, 1);
    });
    scene.at(t + 8, () => particle(dim, "dn_guest_keyhole", keyhole));
    scene.at(t + 17, () => particle(dim, "fx_flash", keyhole));
    scene.at(t + A2.vanish, () => scene.despawn(d));
    scene.endAt(t + A2.vanish + 4);
  }
  scene.endAt(deadline + 400);
});

// src/config/dn03.ts
var DN03 = {
  // ---- the maze grid (centred on the fight, pushed away from the caster so the caster starts outside it)
  /** Cells per side of the square grid. 6 cells x 4 blocks = 24 blocks across. */
  gridCells: 6,
  /** Cell size in blocks (must be even: a door is the middle column of a wall). One wall segment spans one cell side. */
  cellSize: 4,
  /** Gap kept between the caster and the grid edge when the grid is placed. */
  casterMargin: 2,
  /** Maximum distance the grid may be pushed away from the aimed point to leave the caster outside. */
  maxGridShift: 10,
  /** Ground under a column may differ from the grid's ground by this much before the column is skipped. */
  maxColumnStep: 3,
  // ---- wall segments
  /** Wall-segment actors that make up the maze (also the number of walls in every layout). */
  wallCount: 18,
  /** Height of the barrier collision under each wall (players cannot jump 3, mobs cannot climb it). */
  wallBlocks: 3,
  // ---- timing (ticks)
  /** Active battlefield-control duration: from the first layout to the fold-back (12 s). */
  activeTicks: 240,
  /** The house rearranges its layout this often while active (2.5 s). */
  shiftEvery: 50,
  /** At most this many walls travel per rearrangement (the rest stay, so the change stays readable). */
  maxMovesPerShift: 8,
  /** Delay between successive walls starting to move in one rearrangement. */
  moveStagger: 2,
  /** Chalk lines appear where a wall will arrive this many ticks before it starts moving. */
  telegraphTicks: 10,
  // ---- layout logic weights (higher = more likely to get a wall)
  score: {
    /** Wall between two cells that belong to different hostile groups (splits the pack). */
    separate: 10,
    /** Wall on the side of a hostile's cell that faces the caster (forces a detour away from the caster). */
    blockApproach: 6,
    /** Side walls of the controllable corridor that leads away from the caster. */
    corridor: 5,
    /** Outer edge on the caster's side of the maze (a front line between caster and enemies). */
    frontLine: 3,
    /** Any other outer edge. */
    perimeter: 1,
    /** Edge next to a cell holding a player (allowed only as a door). */
    nearAlly: -2,
    /** Random variation per rearrangement so the house never repeats itself exactly. */
    jitter: 3
  },
  /** Length of the controllable corridor in cells; its far end is the looping door. */
  routeLen: 3,
  /** Hostile groups the layout tries to keep apart. */
  maxGroups: 3,
  /** Search radius for hostiles around the grid centre. */
  radius: 20,
  // ---- collision safety
  /** No new wall may arrive on a column within this distance (blocks) of a player. */
  playerClear: 1,
  /** A column is "occupied" (barrier deferred) while any creature stands this close to its centre. */
  occupyRadius: 0.8,
  /** Push given to enemies standing where a wall is arriving (horizontal, vertical). */
  pushH: 0.7,
  pushV: 0.3,
  /** Deferred barrier columns are retried this often. */
  retryEvery: 4,
  // ---- the corridor that loops unexpectedly
  /** Enemies this close to the looping door's gap are carried back to the corridor's start. */
  loopRadius: 1.1,
  /** One loop per enemy at most this often. */
  loopCooldown: 30,
  /** Disorientation after being looped: slowness ticks. */
  loopSlowTicks: 30,
  // ---- living furniture (light control, this is not a damage spell)
  /** The breathing bed makes nearby enemies drowsy: radius, slowness amplifier and ticks. */
  bedRadius: 3,
  bedSlowAmp: 1,
  bedSlowTicks: 40,
  /** The thirteen-hour clock drags time around it: radius and slowness ticks (amplifier 0). */
  clockRadius: 3.5,
  clockSlowTicks: 30,
  /** The chandelier drops its crystals once per rearrangement: blast radius and damage. */
  crystalRadius: 1.8,
  crystalDamage: 4,
  /** The upside-down table bumps enemies it scuttles into: reach, damage and push. */
  tableRadius: 1.4,
  tableDamage: 2,
  tablePush: 0.8,
  // ---- the house itself
  /** Height of the opened house above the maze while it rearranges the battlefield. */
  hoverHeight: 11
};

// src/spells/dn03_shifting_house.ts
var HS = { hidden: 0, land: 1, closed: 2, open: 3, opened: 4, unfold: 5, spread: 6, shiftA: 7, shiftB: 8, fold: 9, close: 10, vanish: 11 };
var WS = { hidden: 0, rise: 1, idle: 2, slide: 3, settle: 4, fold: 5, fly: 6 };
var FS = { hidden: 0, appear: 1, idle: 2, move: 3, act: 4, vanish: 5 };
var DS = { hidden: 0, hop: 1, pop: 2 };
var KIND_DOOR = 1;
var BASE_KINDS = [0, 2, 0, 3];
var L = {
  land: 1,
  open: 1.6,
  unfold: 1,
  shift: 0.8,
  fold: 1,
  close: 1,
  vanish: 0.8,
  wRise: 0.8,
  wSettle: 0.5,
  wFold: 0.5,
  fAppear: 0.6,
  fAct: 0.8,
  fVanish: 0.5,
  doorPop: 0.4
};
var ek = (e) => `${e.o},${e.i},${e.j}`;
var pk = (e) => {
  const [o, i, j] = e.split(",").map(Number);
  return { o, i, j };
};
function hash01(a, s) {
  let h = (2166136261 ^ a * 7919) >>> 0;
  for (let k2 = 0; k2 < s.length; k2++) h = Math.imul(h ^ s.charCodeAt(k2), 16777619) >>> 0;
  return h % 1e3 / 1e3;
}
var dn03_shifting_house_default = defineSpell("dn03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const N3 = DN03.gridCells, CS = DN03.cellSize, HALF = N3 * CS / 2, GAP = CS / 2, H2 = DN03.wallBlocks;
  const tb = blocksFor(scene);
  const { center } = focus(caster, aim, 12);
  let away = norm(flat(sub(center, caster.location)));
  if (distXZ(center, caster.location) < 0.5) away = aim.forward;
  const d0 = distXZ(center, caster.location);
  const shift = clamp(HALF + DN03.casterMargin - d0, 0, DN03.maxGridShift);
  const gc = plateau(dim, up(add(center, mul(away, shift)), 4), HALF);
  const gy = gc.y;
  const X0 = Math.floor(gc.x) - HALF, Z0 = Math.floor(gc.z) - HALF;
  const mid = (gx, gz) => ({ x: X0 + gx * CS + GAP + 0.5, y: gy, z: Z0 + gz * CS + GAP + 0.5 });
  const gridMid = mid(N3 / 2 - 0.5, N3 / 2 - 0.5);
  const hover = up(gridMid, DN03.hoverHeight);
  const inside = (c) => c[0] >= 0 && c[0] < N3 && c[1] >= 0 && c[1] < N3;
  const cellCenter = (c) => ({ x: X0 + c[0] * CS + GAP + 0.5, y: gy, z: Z0 + c[1] * CS + GAP + 0.5 });
  const cellOf = (p) => [Math.floor((p.x - X0) / CS), Math.floor((p.z - Z0) / CS)];
  const ck = (c) => `${c[0]},${c[1]}`;
  const edgeMid = (e) => e.o === 0 ? { x: X0 + e.i * CS + GAP + 0.5, y: gy, z: Z0 + e.j * CS + 0.5 } : { x: X0 + e.i * CS + 0.5, y: gy, z: Z0 + e.j * CS + GAP + 0.5 };
  const edgeCells = (e) => e.o === 0 ? [[e.i, e.j - 1], [e.i, e.j]] : [[e.i - 1, e.j], [e.i, e.j]];
  const edgeNormal = (e) => e.o === 0 ? { x: 0, y: 0, z: 1 } : { x: 1, y: 0, z: 0 };
  const colsOf = (e, door) => {
    const out = [];
    for (let k2 = 0; k2 <= CS; k2++) {
      if (door && k2 === GAP) continue;
      out.push(e.o === 0 ? `${X0 + e.i * CS + k2},${Z0 + e.j * CS}` : `${X0 + e.i * CS},${Z0 + e.j * CS + k2}`);
    }
    return out;
  };
  const gapCenter = (e) => {
    const [x, z] = colsOf(e, false)[GAP].split(",").map(Number);
    return { x: x + 0.5, y: gy, z: z + 0.5 };
  };
  const between = (a, b) => a[0] === b[0] ? { o: 0, i: a[0], j: Math.max(a[1], b[1]) } : { o: 1, i: Math.max(a[0], b[0]), j: a[1] };
  const ALL = [];
  for (let i = 0; i < N3; i++) for (let j = 0; j <= N3; j++) ALL.push({ o: 0, i, j });
  for (let i = 0; i <= N3; i++) for (let j = 0; j < N3; j++) ALL.push({ o: 1, i, j });
  const yawsOf = (e) => e.o === 0 ? [0, 180] : [-90, 90];
  const frontYaw = (e, toward) => {
    const m = edgeMid(e);
    return e.o === 0 ? toward.z > m.z ? 0 : 180 : toward.x > m.x ? -90 : 90;
  };
  const nearestYaw = (e, cur) => {
    const [a, b] = yawsOf(e);
    return Math.abs(angleDelta(cur, a)) <= Math.abs(angleDelta(cur, b)) ? a : b;
  };
  const alongZ = Math.abs(away.z) >= Math.abs(away.x);
  const farPos = alongZ ? away.z > 0 : away.x > 0;
  const cellAt = (lat, dep) => {
    const d = farPos ? N3 - 1 - dep : dep;
    return alongZ ? [lat, d] : [d, lat];
  };
  const farEdge = (lat, dep) => {
    const g = farPos ? N3 - dep : dep;
    return alongZ ? { o: 0, i: lat, j: g } : { o: 1, i: g, j: lat };
  };
  const sideEdges = (lat, dep) => {
    const c = cellAt(lat, dep);
    return alongZ ? [{ o: 1, i: c[0], j: c[1] }, { o: 1, i: c[0] + 1, j: c[1] }] : [{ o: 0, i: c[0], j: c[1] }, { o: 0, i: c[0], j: c[1] + 1 }];
  };
  const refs = /* @__PURE__ */ new Map();
  const placed = /* @__PURE__ */ new Set();
  const pending = /* @__PURE__ */ new Set();
  const colY = /* @__PURE__ */ new Map();
  function baseY(k2) {
    if (colY.has(k2)) return colY.get(k2);
    const [x, z] = k2.split(",").map(Number);
    const y = groundBelow(dim, { x: x + 0.5, y: gy + 4, z: z + 0.5 }, 12).y;
    const v2 = Math.abs(y - gy) > DN03.maxColumnStep ? null : Math.floor(y);
    colY.set(k2, v2);
    return v2;
  }
  function occupants(k2) {
    const [x, z] = k2.split(",").map(Number);
    let found = [];
    try {
      found = dim.getEntities({ location: { x: x + 0.5, y: gy + 1, z: z + 0.5 }, maxDistance: 3, excludeFamilies: ["grimoire_construct"] });
    } catch {
      return [];
    }
    return found.filter((e) => isAlive(e) && e.typeId !== "minecraft:item" && Math.abs(e.location.x - (x + 0.5)) < DN03.occupyRadius + 0.3 && Math.abs(e.location.z - (z + 0.5)) < DN03.occupyRadius + 0.3);
  }
  function tryPlace(k2) {
    const y = baseY(k2);
    if (y === null || placed.has(k2)) {
      pending.delete(k2);
      return;
    }
    const occ = occupants(k2);
    if (occ.length) {
      pending.add(k2);
      const [x2, z2] = k2.split(",").map(Number);
      for (const e of occ) if (e.typeId !== "minecraft:player") shove(e, sub(e.location, { x: x2 + 0.5, y: e.location.y, z: z2 + 0.5 }), DN03.pushH, DN03.pushV);
      return;
    }
    const [x, z] = k2.split(",").map(Number);
    tb.column(x, y, z, H2);
    placed.add(k2);
    pending.delete(k2);
  }
  function claim(k2) {
    const n = (refs.get(k2) ?? 0) + 1;
    refs.set(k2, n);
    if (n === 1) tryPlace(k2);
  }
  function release2(k2) {
    const n = (refs.get(k2) ?? 0) - 1;
    if (n > 0) {
      refs.set(k2, n);
      return;
    }
    refs.delete(k2);
    pending.delete(k2);
    if (placed.delete(k2)) {
      const [x, z] = k2.split(",").map(Number);
      tb.removeColumn(x, baseY(k2) ?? gy, z, H2);
    }
  }
  function setCols(w, cols) {
    const next = new Set(cols);
    for (const k2 of w.cols) if (!next.has(k2)) release2(k2);
    const prev = new Set(w.cols);
    for (const k2 of cols) if (!prev.has(k2)) claim(k2);
    w.cols = cols;
  }
  function clearLine(e) {
    const m = edgeMid(e), n = edgeNormal(e);
    for (const h of hostiles(dim, m, GAP + 1.5, caster)) {
      const rel = sub(h.location, m);
      const along = e.o === 0 ? Math.abs(rel.x) : Math.abs(rel.z);
      const perp = e.o === 0 ? rel.z : rel.x;
      if (along > GAP + 0.8 || Math.abs(perp) > 1.4) continue;
      shove(h, mul(n, perp >= 0 ? 1 : -1), DN03.pushH, DN03.pushV);
    }
  }
  function survey() {
    const foes = hostiles(dim, gridMid, DN03.radius, caster).filter((e) => inside(cellOf(e.location)));
    const foeCells = /* @__PURE__ */ new Map();
    for (const e of foes) {
      const k2 = ck(cellOf(e.location));
      foeCells.set(k2, (foeCells.get(k2) ?? 0) + 1);
    }
    const players = allies(dim, gridMid, DN03.radius, caster);
    const allyCells = /* @__PURE__ */ new Set();
    for (const p of players) {
      const c = cellOf(p.location);
      if (inside(c)) allyCells.add(ck(c));
      for (const [dx, dz] of [[0.9, 0], [-0.9, 0], [0, 0.9], [0, -0.9]]) {
        const c2 = cellOf({ x: p.location.x + dx, y: 0, z: p.location.z + dz });
        if (inside(c2)) allyCells.add(ck(c2));
      }
    }
    return { foes, foeCells, allyCells, players };
  }
  function plan(round) {
    const { foeCells, allyCells, players } = survey();
    const W2 = DN03.score;
    const occ = [...foeCells.keys()].map((k2) => k2.split(",").map(Number));
    const seeds = [];
    if (occ.length) {
      occ.sort((a, b) => distXZ(cellCenter(a), caster.location) - distXZ(cellCenter(b), caster.location));
      seeds.push(occ[0]);
      while (seeds.length < DN03.maxGroups) {
        let best = null, bd = 2.5;
        for (const c of occ) {
          const d = Math.min(...seeds.map((s) => Math.abs(s[0] - c[0]) + Math.abs(s[1] - c[1])));
          if (d > bd) {
            bd = d;
            best = c;
          }
        }
        if (!best) break;
        seeds.push(best);
      }
    }
    const region = (c) => {
      let r = -1, bd = 1e9;
      seeds.forEach((s, k2) => {
        const d = Math.abs(s[0] - c[0]) + Math.abs(s[1] - c[1]);
        if (d < bd) {
          bd = d;
          r = k2;
        }
      });
      return r;
    };
    const lat = clamp(Math.floor(N3 / 2) - 1 + round % 2, 0, N3 - 1);
    const loopEdge = farEdge(lat, 0);
    const start = cellAt(lat, DN03.routeLen - 1);
    const corridor2 = /* @__PURE__ */ new Set(), keepOpen = /* @__PURE__ */ new Set();
    for (let d = 0; d < DN03.routeLen; d++) for (const s of sideEdges(lat, d)) corridor2.add(ek(s));
    for (let d = 1; d <= DN03.routeLen; d++) keepOpen.add(ek(farEdge(lat, d)));
    const toCaster = mul(away, -1);
    const score = /* @__PURE__ */ new Map();
    const cand = [];
    for (const e of ALL) {
      const key = ek(e);
      if (keepOpen.has(key)) continue;
      const nearPlayer = colsOf(e, false).some((k2) => {
        const [x, z] = k2.split(",").map(Number);
        return players.some((p) => Math.abs(p.location.x - (x + 0.5)) < DN03.playerClear + 0.5 && Math.abs(p.location.z - (z + 0.5)) < DN03.playerClear + 0.5);
      });
      if (nearPlayer) continue;
      const [a, b] = edgeCells(e);
      const n = edgeNormal(e);
      let s = hash01(round + 1, key) * W2.jitter;
      if (inside(a) && inside(b) && seeds.length > 1 && region(a) !== region(b)) s += W2.separate;
      for (const [c, sign] of [[a, 1], [b, -1]]) {
        if (!inside(c) || !foeCells.has(ck(c))) continue;
        const out = mul(n, sign);
        if (out.x * toCaster.x + out.z * toCaster.z > 0.5) s += W2.blockApproach;
      }
      if (corridor2.has(key)) s += W2.corridor;
      if (!inside(a) || !inside(b)) {
        const out = inside(a) ? n : mul(n, -1);
        s += out.x * toCaster.x + out.z * toCaster.z > 0.7 ? W2.frontLine : W2.perimeter;
      }
      if (inside(a) && allyCells.has(ck(a)) || inside(b) && allyCells.has(ck(b))) s += W2.nearAlly;
      if (key === ek(loopEdge)) s = 1e3;
      score.set(key, s);
      cand.push({ e, s });
    }
    cand.sort((p, q) => q.s - p.s);
    const walls2 = /* @__PURE__ */ new Map();
    for (const c of cand.slice(0, DN03.wallCount)) walls2.set(ek(c.e), { e: c.e, door: false });
    return { walls: walls2, loopKey: ek(loopEdge), start, score };
  }
  function assignDoors(walls2, loopKey2) {
    const { allyCells } = survey();
    for (const [key, w] of walls2) {
      const [a, b] = edgeCells(w.e);
      w.door = key === loopKey2 || inside(a) && allyCells.has(ck(a)) || inside(b) && allyCells.has(ck(b));
    }
    for (let guard = 0; guard < 40; guard++) {
      const blocked = (e) => {
        const w = walls2.get(ek(e));
        return !!w && !w.door;
      };
      const seen = /* @__PURE__ */ new Set();
      const queue = [];
      for (let k2 = 0; k2 < N3; k2++) {
        const per = [[[k2, 0], { o: 0, i: k2, j: 0 }], [[k2, N3 - 1], { o: 0, i: k2, j: N3 }], [[0, k2], { o: 1, i: 0, j: k2 }], [[N3 - 1, k2], { o: 1, i: N3, j: k2 }]];
        for (const [c, e] of per) if (!blocked(e) && !seen.has(ck(c))) {
          seen.add(ck(c));
          queue.push(c);
        }
      }
      while (queue.length) {
        const c = queue.pop();
        for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const n = [c[0] + dx, c[1] + dz];
          if (!inside(n) || seen.has(ck(n)) || blocked(between(c, n))) continue;
          seen.add(ck(n));
          queue.push(n);
        }
      }
      if (seen.size >= N3 * N3) return;
      let best = null;
      for (const w of walls2.values()) {
        if (w.door) continue;
        const [a, b] = edgeCells(w.e);
        const ia = inside(a) && !seen.has(ck(a)), ib = inside(b) && !seen.has(ck(b));
        if (ia === ib) continue;
        const out = mul(edgeNormal(w.e), ia ? 1 : -1);
        const s = out.x * away.x + out.z * away.z;
        if (!best || s > best.s) best = { w, s };
      }
      if (!best) return;
      best.w.door = true;
    }
  }
  const T9 = {
    open: secs(L.land),
    opened: secs(L.land + L.open),
    unfold: secs(L.land + L.open) + 4,
    wallsOut: secs(L.land + L.open) + 8,
    active: secs(L.land + L.open) + 24
  };
  T9.active = Math.max(T9.active, T9.wallsOut + Math.ceil(DN03.wallCount / 2) + 18);
  const tFold = T9.active + DN03.activeTicks;
  const tClose = tFold + 34;
  const tVanish = tClose + secs(L.close);
  const tEnd = tVanish + secs(L.vanish) + 4;
  const faceCaster = yawOf(sub(caster.location, gc));
  const house = scene.spawn("dn_house_doll", gc, { yaw: faceCaster, state: HS.land });
  let houseYaw = faceCaster;
  let housePos = { ...gc };
  sound(dim, "dn_house_land", gc, 1.2);
  scene.at(9, () => {
    particle(dim, "fx_dust", up(gc, 0.3));
    burst(dim, "dn_house_dust", up(gc, 0.5), 3, 6);
  });
  scene.at(T9.open, () => {
    house.state(HS.open);
    sound(dim, "dn_house_windup", gc, 1);
    sound(dim, "dn_house_open", gc, 1);
  });
  scene.at(T9.open + 18, () => burst(dim, "dn_house_key", up(gc, 5), 3, 8));
  scene.at(T9.opened, () => house.state(HS.opened));
  scene.at(T9.unfold, () => {
    house.state(HS.unfold);
    sound(dim, "dn_house_unfold", gc, 1.2);
    burst(dim, "dn_house_scrap", up(gc, 5), 3, 6);
  });
  scene.at(T9.unfold + secs(L.unfold), () => house.state(HS.spread));
  scene.span(T9.unfold, T9.unfold + 24, (p) => {
    housePos = lerp(gc, hover, smooth(p));
    house.move(housePos);
  });
  const first = plan(0);
  assignDoors(first.walls, first.loopKey);
  let loopKey = first.loopKey;
  let loopStart = first.start;
  const walls = [];
  [...first.walls.values()].forEach((t, k2) => {
    const at = T9.wallsOut + Math.floor(k2 / 2);
    scene.at(at, () => {
      const base = BASE_KINDS[k2 % BASE_KINDS.length];
      const yaw = frontYaw(t.e, caster.isValid ? caster.location : gc);
      const a = scene.spawn("dn_house_wall", housePos, { yaw, state: WS.fly, kind: t.door ? KIND_DOOR : base });
      const w = { a, key: ek(t.e), e: t.e, door: t.door, base, cols: [], pos: { ...housePos }, yaw, arrived: false };
      walls.push(w);
      const from = { ...housePos }, to = edgeMid(t.e);
      const ctrl = up(lerp(from, to, 0.5), 5);
      scene.span(at, at + 16, (p) => {
        w.pos = bezier(from, ctrl, to, smooth(p));
        w.a.move(w.pos, yaw + (1 - p) * 360);
      });
      scene.at(at + 13, () => clearLine(t.e));
      scene.at(at + 16, () => {
        w.a.state(WS.rise);
        w.arrived = true;
        setCols(w, colsOf(t.e, t.door));
        line(dim, "dn_house_dust", up(edgeMid(t.e), 0.2), up(edgeMid(t.e), 0.3), 1);
        if (k2 % 3 === 0) sound(dim, "dn_house_settle", to, 0.8, 0.9 + k2 % 5 * 0.06);
      });
      scene.at(at + 16 + secs(L.wRise), () => {
        if (!w.a.valid) return;
        w.a.state(WS.idle);
      });
    });
  });
  const FURN = ["dn_house_bed", "dn_house_clock", "dn_house_chandelier", "dn_house_table"];
  const furn = [];
  function furnitureCells(round) {
    const { foeCells, allyCells } = survey();
    const used = new Set(allyCells);
    const pick = (c) => c && inside(c) && !used.has(ck(c)) ? (used.add(ck(c)), c) : null;
    const busy = [...foeCells.entries()].sort((a, b) => b[1] - a[1]).map(([k2]) => k2.split(",").map(Number));
    const pattern = [];
    for (let k2 = 0; k2 < N3 * N3; k2++) {
      const h = Math.floor(hash01(round * 31 + k2, "furn") * N3 * N3);
      pattern.push([h % N3, Math.floor(h / N3)]);
    }
    const next = () => {
      for (const c of pattern) {
        const p = pick(c);
        if (p) return p;
      }
      return [0, 0];
    };
    const chand = pick(busy[0] ?? null) ?? next();
    const bed = pick(busy[1] ?? null) ?? next();
    const clock = pick(loopStart) ?? next();
    const table = next();
    return [bed, clock, chand, table];
  }
  const fcells0 = furnitureCells(0);
  FURN.forEach((id, k2) => {
    const at = T9.wallsOut + 10 + k2 * 3;
    scene.at(at, () => {
      const f = { a: scene.spawn(id, housePos, { yaw: faceCaster, state: FS.appear }), id, pos: { ...housePos }, cell: fcells0[k2] };
      furn.push(f);
      const from = { ...housePos }, to = cellCenter(fcells0[k2]);
      scene.at(at + 8, () => f.a.state(FS.move));
      scene.span(at, at + 22, (p) => {
        f.pos = bezier(from, up(lerp(from, to, 0.5), 6), to, smooth(p));
        f.a.move(f.pos, faceCaster + p * 180);
      });
      scene.at(at + 22, () => {
        f.a.state(FS.idle);
        particle(dim, "dn_house_glow", up(to, 1));
        burst(dim, "dn_house_dust", up(to, 0.4), 1, 2);
      });
    });
  });
  const F = (id) => furn.find((f) => f.id === id);
  function moveWall(w, to, door, t0) {
    const from = { ...w.pos }, fromYaw2 = w.yaw, dest = edgeMid(to);
    let pivot = null;
    if (w.e && w.e.o !== to.o) {
      const corners = (e) => e.o === 0 ? [[e.i, e.j], [e.i + 1, e.j]] : [[e.i, e.j], [e.i, e.j + 1]];
      const shared = corners(w.e).find((c) => corners(to).some((d) => d[0] === c[0] && d[1] === c[1]));
      if (shared) pivot = { x: X0 + shared[0] * CS + 0.5, y: gy, z: Z0 + shared[1] * CS + 0.5 };
    }
    const toYaw = nearestYaw(to, fromYaw2);
    const dist2 = distXZ(from, dest);
    const dur = pivot ? 14 : Math.round(clamp(10 + dist2 * 1.1, 12, 26));
    let a0 = 0, da = 0;
    if (pivot) {
      a0 = Math.atan2(from.z - pivot.z, from.x - pivot.x);
      da = Math.atan2(dest.z - pivot.z, dest.x - pivot.x) - a0;
      while (da > Math.PI) da -= 2 * Math.PI;
      while (da < -Math.PI) da += 2 * Math.PI;
    }
    const yawSpan = pivot ? da * 180 / Math.PI : angleDelta(fromYaw2, toYaw);
    w.arrived = false;
    scene.at(t0 - DN03.telegraphTicks, () => line(dim, "dn_house_chalk", up(edgeMid(to), 0.15), up(gapCenter(to), 0.15), 2));
    scene.at(t0 - DN03.telegraphTicks, () => {
      const cs = colsOf(to, false);
      const [x1, z1] = cs[0].split(",").map(Number), [x2, z2] = cs[cs.length - 1].split(",").map(Number);
      line(dim, "dn_house_chalk", { x: x1 + 0.5, y: gy + 0.15, z: z1 + 0.5 }, { x: x2 + 0.5, y: gy + 0.15, z: z2 + 0.5 }, 4);
    });
    scene.at(t0, () => {
      setCols(w, []);
      w.a.state(WS.slide);
      sound(dim, "dn_house_slide", from, 0.9, 0.9 + hash01(t0, "s") * 0.25);
      particle(dim, "dn_house_dust", up(from, 0.3));
    });
    scene.span(t0, t0 + dur, (p) => {
      const q = smooth(p);
      if (pivot) {
        const ang = a0 + da * q;
        w.pos = { x: pivot.x + Math.cos(ang) * GAP, y: gy, z: pivot.z + Math.sin(ang) * GAP };
      } else {
        w.pos = up(lerp(from, dest, q), Math.sin(Math.PI * q) * (dist2 > CS + 1 ? 0.8 : 0));
      }
      w.yaw = fromYaw2 + yawSpan * q;
      w.a.move(w.pos, w.yaw);
    });
    scene.at(t0 + dur - 3, () => clearLine(to));
    scene.at(t0 + dur, () => {
      w.yaw = toYaw;
      w.pos = dest;
      w.a.move(dest, toYaw);
      w.door = door;
      w.a.kind(door ? KIND_DOOR : w.base);
      setCols(w, colsOf(to, door));
      w.arrived = true;
      w.a.state(WS.settle);
      sound(dim, "dn_house_settle", dest, 0.9, 0.9 + hash01(t0, "k") * 0.3);
      particle(dim, "dn_house_dust", up(dest, 0.3));
    });
    scene.at(t0 + dur + secs(L.wSettle), () => {
      if (w.arrived) w.a.state(WS.idle);
    });
  }
  function hopDoor(fromW, toW, t0) {
    scene.at(t0, () => {
      if (!fromW.e || !toW.e) return;
      const a = gapCenter(fromW.e), b = gapCenter(toW.e);
      fromW.door = false;
      fromW.a.kind(fromW.base);
      setCols(fromW, colsOf(fromW.e, false));
      sound(dim, "dn_house_pop", a, 1, 1.1);
      particle(dim, "dn_house_glow", up(a, 1.4));
      const d = scene.spawn("dn_house_door", a, { yaw: fromW.yaw, state: DS.hop });
      const dur = Math.round(clamp(10 + distXZ(a, b) * 0.6, 12, 20));
      const ctrl = up(lerp(a, b, 0.5), 4 + distXZ(a, b) * 0.2);
      scene.span(scene.tick, scene.tick + dur, (p) => d.move(bezier(a, ctrl, b, p), fromW.yaw + p * 180));
      scene.after(dur, () => {
        if (toW.e) {
          toW.door = true;
          toW.a.kind(KIND_DOOR);
          setCols(toW, colsOf(toW.e, true));
        }
        d.state(DS.pop);
        sound(dim, "dn_house_pop", b, 1, 0.85);
        burst(dim, "dn_house_key", up(b, 1.2), 0.8, 3);
      });
      scene.after(dur + secs(L.doorPop), () => scene.despawn(d));
    });
  }
  function rearrange(round, t) {
    const p = plan(round);
    const target = p.walls;
    let leaving = walls.filter((w) => w.key === null || !target.has(w.key));
    const occupied = new Set(walls.map((w) => w.key));
    let arriving = [...target.keys()].filter((k2) => !occupied.has(k2));
    arriving.sort((a, b) => (p.score.get(b) ?? 0) - (p.score.get(a) ?? 0));
    leaving.sort((a, b) => (p.score.get(a.key ?? "") ?? -99) - (p.score.get(b.key ?? "") ?? -99));
    const nMoves = Math.min(leaving.length, arriving.length, DN03.maxMovesPerShift);
    arriving = arriving.slice(0, nMoves);
    leaving = leaving.slice(0, nMoves);
    const moves = [];
    for (const key of arriving) {
      const e = pk(key), m = edgeMid(e);
      let bi = 0, bd = 1e9;
      leaving.forEach((w, k2) => {
        let d = distXZ(w.pos, m);
        if (w.e && w.e.o !== e.o && d < GAP * 1.5 + 0.1) d -= 2;
        if (d < bd) {
          bd = d;
          bi = k2;
        }
      });
      moves.push({ w: leaving[bi], e });
      leaving.splice(bi, 1);
    }
    const final = /* @__PURE__ */ new Map();
    for (const w of walls) if (w.e && !moves.some((m) => m.w === w)) final.set(w.key, { e: w.e, door: false });
    for (const m of moves) final.set(ek(m.e), { e: m.e, door: false });
    assignDoors(final, p.loopKey);
    loopKey = final.has(p.loopKey) ? p.loopKey : loopKey;
    loopStart = p.start;
    const gain = walls.filter((w) => !moves.some((m) => m.w === w) && w.key && final.get(w.key).door && !w.door);
    const lose = walls.filter((w) => !moves.some((m) => m.w === w) && w.key && !final.get(w.key).door && w.door);
    for (let k2 = 0; k2 < Math.max(gain.length, lose.length); k2++) {
      const g = gain[k2], l = lose[k2];
      if (g && l) {
        hopDoor(l, g, t + 4 + k2 * 3);
        continue;
      }
      const w = g ?? l;
      scene.at(t + 4 + k2 * 3, () => {
        if (!w.e) return;
        w.door = !!g;
        w.a.kind(w.door ? KIND_DOOR : w.base);
        setCols(w, colsOf(w.e, w.door));
        sound(dim, "dn_house_pop", gapCenter(w.e), 0.8, w.door ? 1.2 : 0.8);
        particle(dim, "dn_house_glow", up(gapCenter(w.e), 1.4));
      });
    }
    moves.forEach((m, k2) => {
      m.w.key = ek(m.e);
      moveWall(m.w, m.e, final.get(ek(m.e)).door, t + k2 * DN03.moveStagger);
      m.w.e = m.e;
    });
  }
  const shiftTicks = [];
  for (let t = T9.active + DN03.shiftEvery; t < tFold - 10; t += DN03.shiftEvery) shiftTicks.push(t);
  scene.at(T9.active, () => {
    sound(dim, "dn_house_lullaby", hover, 1);
    ring(dim, "dn_house_note", up(hover, 2), 4, 6);
  });
  shiftTicks.forEach((t, r) => {
    scene.at(t - DN03.telegraphTicks, () => rearrange(r + 1, t));
    scene.at(t, () => {
      house.state(r % 2 === 0 ? HS.shiftA : HS.shiftB);
      sound(dim, "dn_house_lullaby_warp", hover, 1, 1 - r * 0.05);
      burst(dim, "dn_house_scrap", up(hover, 3), 3, 6);
    });
    const y0 = houseYaw;
    houseYaw += 90;
    scene.span(t, t + 14, (p) => house.move(hover, y0 + 90 * smooth(p)));
    scene.at(t, () => {
      const cells = furnitureCells(r + 1);
      FURN.forEach((id, k2) => relocate(F(id), cells[k2], t + k2 * 2));
      F("dn_house_bed")?.a.state(FS.act);
      const clock = F("dn_house_clock");
      if (clock) sound(dim, "dn_house_chime", clock.pos, 0.9);
    });
    scene.at(t + 20, () => {
      const ch = F("dn_house_chandelier");
      if (!ch?.a.valid) return;
      const at = { ...ch.pos };
      const warn = scene.spawn("telegraph", up(at, 0.05), { kind: 1, size: DN03.crystalRadius, state: 1 });
      scene.after(10, () => ch.a.state(FS.act));
      scene.after(19, () => {
        warn.state(3);
        sound(dim, "dn_house_crystal", at, 1);
        particle(dim, "dn_house_crystal", up(at, 0.6));
        particle(dim, "dn_house_tick", up(at, 0.1));
        for (const e of hostiles(dim, at, DN03.crystalRadius + 0.5, caster)) damage(e, DN03.crystalDamage, caster);
      });
      scene.after(27, () => scene.despawn(warn));
      scene.after(10 + secs(L.fAct), () => ch.a.state(FS.idle));
    });
  });
  function relocate(f, cell, t0) {
    if (!f) return;
    const dur = 18;
    scene.at(t0, () => {
      if (!f.a.valid) return;
      const from = { ...f.pos }, to = cellCenter(cell);
      const dir = sub(to, from);
      const yaw = distXZ(from, to) > 0.3 ? yawOf(dir) : void 0;
      f.cell = cell;
      f.a.state(FS.move);
      if (f.id === "dn_house_table") sound(dim, "dn_house_scuttle", from, 0.9);
      const bumped = /* @__PURE__ */ new Set();
      scene.span(scene.tick, scene.tick + dur, (p) => {
        f.pos = up(lerp(from, to, smooth(p)), f.id === "dn_house_clock" ? 0 : Math.sin(Math.PI * p) * 0.6);
        f.a.move(f.pos, yaw);
        if (f.id !== "dn_house_table") return;
        for (const e of hostiles(dim, f.pos, DN03.tableRadius, caster)) {
          if (bumped.has(e.id)) continue;
          bumped.add(e.id);
          damage(e, DN03.tableDamage, caster);
          shove(e, dir, DN03.tablePush, 0.3);
        }
      });
      scene.after(dur, () => {
        if (f.a.valid) f.a.state(FS.idle);
      });
    });
  }
  scene.every(20, (el) => {
    const bed = F("dn_house_bed");
    if (bed?.a.valid) {
      for (const e of hostiles(dim, bed.pos, DN03.bedRadius, caster)) effect(e, "slowness", DN03.bedSlowTicks, DN03.bedSlowAmp);
      particle(dim, "dn_house_sleep", up(bed.pos, 2.2));
      if (el % 60 === 0) sound(dim, "dn_house_bed", bed.pos, 0.7, 0.9 + (el % 120 === 0 ? 0.1 : 0));
    }
    const clock = F("dn_house_clock");
    if (clock?.a.valid) for (const e of hostiles(dim, clock.pos, DN03.clockRadius, caster)) effect(e, "slowness", DN03.clockSlowTicks, 0);
  }, T9.active, tFold);
  for (let t = T9.active, k2 = 0; t < tFold; k2++) {
    const tick = t;
    scene.at(tick, () => {
      const clock = F("dn_house_clock");
      if (!clock?.a.valid) return;
      sound(dim, "dn_house_tick", clock.pos, 0.7, 1 - k2 % 7 * 0.03);
      if (k2 % 3 === 0) particle(dim, "dn_house_tick", up(clock.pos, 0.1));
    });
    t += 10 + Math.round(4 * Math.sin(k2 * 0.9));
  }
  const looped = /* @__PURE__ */ new Map();
  scene.every(2, () => {
    const w = walls.find((x) => x.key === loopKey && x.arrived && x.door && x.e);
    if (!w || !w.e) return;
    const g = gapCenter(w.e);
    for (const e of hostiles(dim, up(g, 1), DN03.loopRadius + 1, caster)) {
      if (distXZ(e.location, g) > DN03.loopRadius || Math.abs(e.location.y - gy) > 2.5) continue;
      if ((looped.get(e.id) ?? -999) > scene.tick - DN03.loopCooldown) continue;
      let dest = cellCenter(loopStart);
      if (allies(dim, dest, 2, caster).length) dest = cellCenter(cellOf(gridMid));
      looped.set(e.id, scene.tick);
      particle(dim, "dn_house_loop", up(g, 1));
      drag(e, up(dest, 0.1));
      effect(e, "slowness", DN03.loopSlowTicks, 1);
      particle(dim, "dn_house_loop", up(dest, 1));
      sound(dim, "dn_house_loop", dest, 1);
      sound(dim, "dn_house_loop", g, 0.7, 1.15);
    }
    if (scene.tick % 10 === 0) particle(dim, "dn_house_chalk", up(g, 1.5));
  }, T9.active, tFold);
  scene.every(DN03.retryEvery, () => {
    for (const k2 of [...pending]) if (refs.has(k2)) tryPlace(k2);
    else pending.delete(k2);
  }, T9.wallsOut, tFold);
  scene.at(tFold, () => {
    for (const w of walls) {
      setCols(w, []);
      w.arrived = false;
      w.a.state(WS.fold);
    }
    pending.clear();
    house.state(HS.fold);
    sound(dim, "dn_house_fold", hover, 1.2);
    sound(dim, "dn_house_lullaby", hover, 0.8, 0.9);
    for (const f of furn) f.a.state(FS.move);
  });
  scene.span(tFold + 4, tClose - 2, (p) => {
    housePos = lerp(hover, gc, smooth(p));
    house.move(housePos);
  });
  scene.at(tFold + secs(L.wFold), () => {
    walls.forEach((w, k2) => {
      const t0 = tFold + secs(L.wFold) + Math.floor(k2 / 2);
      scene.at(t0, () => w.a.state(WS.fly));
      const from = { ...w.pos };
      scene.span(t0, t0 + 14, (p) => w.a.move(bezier(from, up(lerp(from, housePos, 0.5), 5), up(housePos, 3), smooth(p)), w.yaw + p * 270));
      scene.at(t0 + 14, () => {
        particle(dim, "dn_house_scrap", up(housePos, 3));
        scene.despawn(w.a);
      });
    });
    furn.forEach((f, k2) => {
      const t0 = tFold + 2 + k2 * 2;
      const from = { ...f.pos };
      scene.span(t0, t0 + 18, (p) => f.a.move(bezier(from, up(lerp(from, housePos, 0.5), 6), up(housePos, 2), smooth(p))));
      scene.at(t0 + 18 - secs(L.fVanish), () => f.a.state(FS.vanish));
      scene.at(t0 + 18, () => scene.despawn(f.a));
    });
  });
  scene.at(tClose, () => {
    house.move(gc, faceCaster);
    house.state(HS.close);
    sound(dim, "dn_house_open", gc, 0.8, 0.85);
  });
  scene.at(tClose + 13, () => {
    sound(dim, "dn_house_clack", gc, 1.2);
    particle(dim, "fx_dust", up(gc, 0.3));
  });
  scene.at(tVanish, () => {
    house.state(HS.vanish);
    burst(dim, "dn_house_note", up(gc, 3), 2.5, 6);
  });
  scene.at(tVanish + secs(L.vanish) - 2, () => {
    particle(dim, "dn_house_glow", up(gc, 1.5));
    burst(dim, "dn_house_key", up(gc, 1.5), 1.2, 5);
  });
  scene.endAt(tEnd);
});

// src/config/dn04.ts
var DN04 = {
  // ---- timing (the music is cut into 2.0 s phrases; every phase starts on a phrase downbeat)
  /** Active duration in seconds: from the cast until the tapestry starts to unravel.  Rounded down to whole phrases. */
  activeSeconds: 12,
  /** Length of one lullaby phrase in ticks (the sound clips are composed to exactly 2.0 s). */
  phraseTicks: 40,
  /** Phrases of pure lullaby before dissonance creeps in. */
  lullabyPhrases: 1,
  /** Phrases of creeping dissonance (one faint wave) before the full dual composition. */
  dissonancePhrases: 1,
  // ---- tapestry placement
  /** How far in front of the caster and how high above their feet the tapestry hovers. */
  hoverForward: 2.6,
  hoverHeight: 2.4,
  /** Fraction of the remaining distance the tapestry closes each tick while following the caster. */
  followLerp: 0.12,
  // ---- dream half: ribbons, healing, resistance
  /** Players within this radius of the caster are wrapped in dream ribbons (the caster always is). */
  allyRadius: 10,
  /** A wrapped ally further than this from the caster loses their ribbon. */
  ribbonLoseRadius: 15,
  /** Maximum allies wrapped at once. */
  maxAllies: 6,
  /** Ticks between checks for newly arrived allies. */
  allyCheckEvery: 20,
  /** Ticks a ribbon takes to spool from the tapestry to an ally. */
  ribbonTravelTicks: 16,
  /** HP restored to every wrapped ally on each heal pulse (does not cost the caster anything). */
  healAmount: 2,
  /** Ticks between heal pulses (one per phrase, on the second bar's downbeat). */
  healEvery: 40,
  healOffset: 20,
  /** Fraction of incoming damage that still reaches a wrapped ally (0.65 = 35 % resistance). */
  wardFactor: 0.65,
  // ---- nightmare half: scream waves
  /** Final radius of a full scream wave (blocks) and the radius it starts from. */
  waveRadius: 10,
  waveStartRadius: 1.2,
  /** Ticks for the wave front to travel from start to final radius (damage lands as the front arrives). */
  waveTicks: 16,
  /** Damage of a full scream wave. */
  waveDamage: 6,
  /** The first, faint wave of the dissonance phase: radius and damage multipliers. */
  faintRadius: 0.65,
  faintDamage: 0.5,
  /** Ticks from the scream gesture to the wave leaving the tapestry (matches the scream animation peak). */
  screamLead: 6,
  /** Slowness applied by each wave. */
  slowTicks: 60,
  slowAmp: 1,
  /** Weakness applied by each wave (enemies hit less hard while disoriented). */
  weaknessTicks: 80,
  weaknessAmp: 0,
  /** Disorientation: ticks the enemy's facing is forcibly spun, degrees per tick, and the sideways stagger. */
  disorientTicks: 14,
  disorientSpin: 32,
  disorientShove: 0.55,
  /** Maximum enemies one wave can strike. */
  maxTargets: 16
};

// src/spells/dn04_lullaby_and_scream.ts
var T4 = { hidden: 0, unfurl: 1, lullaby: 2, dissonance: 3, dual: 4, scream: 5, unravel: 6 };
var R = { hidden: 0, travel: 1, wrap: 2, orbit: 3, recoil: 4, unwind: 5 };
var W = { hidden: 0, scream: 1, faint: 2, fade: 3 };
var L2 = { unfurl: 30, dissonance: 32, scream: 18, unravel: 36, wrap: 16, recoil: 12, unwind: 20, fade: 7 };
var dn04_lullaby_and_scream_default = defineSpell("dn04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  let facing = norm(flat(aim.forward));
  const hoverTarget = () => up(add(caster.location, mul(facing, DN04.hoverForward)), DN04.hoverHeight);
  const bookAt = () => up(add(caster.location, mul(facing, 0.6)), 1.1);
  const P6 = DN04.phraseTicks;
  const tLull = L2.unfurl;
  const phrases = Math.max(DN04.lullabyPhrases + DN04.dissonancePhrases + 1, Math.floor((secs(DN04.activeSeconds) - tLull) / P6));
  const tDis = tLull + DN04.lullabyPhrases * P6;
  const tDual = tDis + DN04.dissonancePhrases * P6;
  const tUnravel = tLull + phrases * P6;
  const tEnd = tUnravel + L2.unravel + 4;
  const book0 = bookAt();
  let hover = book0;
  const tap = scene.spawn("dn_lull_tapestry", book0, { yaw: yawOf(mul(facing, -1)), state: T4.unfurl, skin: 0 });
  sound(dim, "dn_lull_open", book0, 1);
  burst(dim, "dn_lull_mote", up(book0, 0.4), 0.6, 4);
  scene.at(14, () => burst(dim, "dn_lull_note", up(hover, 2.2), 1.5, 3));
  scene.every(1, () => {
    const t = scene.tick;
    const view = caster.getViewDirection();
    const want = norm(flat(view));
    if (Math.hypot(want.x, want.z) > 0.1) facing = norm(lerp(facing, want, 0.05));
    if (t < tLull) {
      const f = smooth(t / tLull);
      const goal = hoverTarget();
      hover = bezier(book0, up(lerp(book0, goal, 0.5), 1.6), goal, f);
    } else if (t < tUnravel + 10) {
      hover = lerp(hover, hoverTarget(), DN04.followLerp);
    } else {
      hover = lerp(hover, bookAt(), 0.14);
    }
    tap.move(hover, yawOf(mul(facing, -1)));
    if (tele?.valid) tele.move(groundBelow(dim, hover));
    updateRibbons(t);
    updateDizzy(t);
  }, 0, tEnd);
  for (let k2 = 0; k2 < phrases; k2++) {
    const t0 = tLull + k2 * P6;
    const kind = k2 < DN04.lullabyPhrases ? "lull" : k2 < DN04.lullabyPhrases + DN04.dissonancePhrases ? "dis" : "dual";
    scene.at(t0, () => sound(dim, `dn_lull_${kind}${k2 % 2 + 1}`, hover, 1));
    if (kind === "dual") {
      scene.at(t0, () => {
        tap.state(T4.scream);
        sound(dim, "dn_lull_scream", hover, 1.2);
        burst(dim, "dn_lull_thread", up(hover, 2.2), 1.2, 3);
      });
      scene.at(t0 + DN04.screamLead, () => launchWave(false));
      scene.at(t0 + L2.scream, () => tap.state(T4.dual));
    }
  }
  scene.at(tLull, () => tap.state(T4.lullaby));
  scene.every(10, () => particle(dim, "dn_lull_note", up(hover, 2.4)), tLull, tDual);
  let tele;
  scene.at(tDis, () => {
    tap.state(T4.dissonance);
    sound(dim, "dn_lull_tear", hover, 1.1);
    tele = scene.spawn("telegraph", groundBelow(dim, hover), { kind: 1, size: DN04.waveRadius, state: 4 });
  });
  scene.at(tDis + 6, () => tap.skin(1));
  scene.at(tDis + P6 / 2, () => {
    sound(dim, "dn_lull_faint", hover, 0.9);
    launchWave(true);
  });
  scene.at(tDis + L2.dissonance, () => {
    tap.state(T4.dual);
    tele?.state(2);
  });
  scene.every(8, () => particle(dim, "dn_lull_thread", up(hover, 1)), tDis, tUnravel);
  const wraps = /* @__PURE__ */ new Map();
  const lastWardFx = /* @__PURE__ */ new Map();
  addWard({
    scene,
    factor: DN04.wardFactor,
    protects: (e) => {
      const w = wraps.get(e.id);
      return !!w && w.wrapped;
    },
    onAbsorb: (_amount, _attacker, victim) => {
      const last = lastWardFx.get(victim.id) ?? -99;
      if (scene.tick - last < 8 || !victim.isValid) return;
      lastWardFx.set(victim.id, scene.tick);
      particle(dim, "dn_lull_ward", up(victim.location, 1));
      sound(dim, "dn_lull_ward", victim.location, 0.8);
      const w = wraps.get(victim.id);
      if (w && scene.tick >= w.busyUntil) recoil(w);
    }
  });
  function checkAllies() {
    const near = allies(dim, caster.location, DN04.allyRadius, caster);
    if (!near.some((p) => p.id === caster.id) && isAlive(caster)) near.unshift(caster);
    for (const p of near) {
      if (wraps.has(p.id) || wraps.size >= DN04.maxAllies) continue;
      const from = up(hover, 1.6);
      const rib = scene.spawn("dn_lull_ribbon", from, { state: R.travel });
      if (!rib.valid) continue;
      wraps.set(p.id, { p, rib, from, t0: scene.tick, wrapped: false, busyUntil: 0 });
      sound(dim, "dn_lull_ribbon", from, 0.9, 0.95 + wraps.size * 0.05);
    }
    for (const w of [...wraps.values()]) {
      if (!isAlive(w.p) || w.p.dimension.id !== dim.id || distXZ(w.p.location, caster.location) > DN04.ribbonLoseRadius) release2(w);
    }
  }
  scene.every(DN04.allyCheckEvery, checkAllies, 12, tUnravel);
  function updateRibbons(t) {
    for (const w of wraps.values()) {
      if (!w.rib.valid) continue;
      if (!w.p.isValid) continue;
      const target = w.p.location;
      if (!w.wrapped) {
        const f = (t - w.t0) / DN04.ribbonTravelTicks;
        const pos = bezier(w.from, up(lerp(w.from, target, 0.5), 2.5), target, easeOut(Math.min(1, f)));
        w.rib.move(pos, yawOf(sub(target, w.from)));
        if (f >= 1) {
          w.wrapped = true;
          w.busyUntil = t + L2.wrap;
          w.rib.state(R.wrap);
          sound(dim, "dn_lull_calm", target, 0.7, 1.1);
          ring(dim, "dn_lull_mote", up(target, 0.8), 0.8, 4);
          const rib = w.rib;
          scene.after(L2.wrap, () => {
            if (wraps.get(w.p.id) === w) rib.state(R.orbit);
          });
        }
      } else {
        w.rib.move(target);
      }
    }
  }
  function recoil(w) {
    w.busyUntil = scene.tick + L2.recoil;
    w.rib.state(R.recoil);
    const rib = w.rib;
    scene.after(L2.recoil, () => {
      if (wraps.get(w.p.id) === w) rib.state(R.orbit);
    });
  }
  function release2(w) {
    wraps.delete(w.p.id);
    const rib = w.rib;
    rib.state(R.unwind);
    scene.after(L2.unwind, () => scene.despawn(rib));
  }
  scene.every(DN04.healEvery, (e) => {
    const pitch = [1, 1.12, 1.26][Math.floor(e / DN04.healEvery) % 3];
    for (const w of wraps.values()) {
      if (!w.wrapped || !isAlive(w.p)) continue;
      heal(w.p, DN04.healAmount);
      particle(dim, "dn_lull_heal", up(w.p.location, 0.2));
      sound(dim, "dn_lull_heal", w.p.location, 0.8, pitch);
    }
  }, tLull + DN04.healOffset, tUnravel);
  scene.every(16, () => {
    for (const w of wraps.values()) if (w.wrapped && w.p.isValid) particle(dim, "dn_lull_mote", up(w.p.location, 1.2));
  }, tLull, tUnravel);
  const dizzy = /* @__PURE__ */ new Map();
  function launchWave(faint) {
    const center = groundBelow(dim, hover);
    const maxR = DN04.waveRadius * (faint ? DN04.faintRadius : 1);
    const dmg = DN04.waveDamage * (faint ? DN04.faintDamage : 1);
    const wv = scene.spawn("dn_lull_wave", center, { size: DN04.waveStartRadius, state: faint ? W.faint : W.scream });
    if (!faint) particle(dim, "dn_lull_scream_ring", up(center, 0.15));
    const hit = /* @__PURE__ */ new Set();
    const soothed = /* @__PURE__ */ new Set();
    const t0 = scene.tick;
    scene.span(t0, t0 + DN04.waveTicks, (p, el) => {
      const r = DN04.waveStartRadius + (maxR - DN04.waveStartRadius) * easeOut(p);
      wv.size(r);
      if (el % 3 === 0) ring(dim, "dn_lull_front", up(center, 1.2), r, faint ? 4 : 7, el * 17);
      for (const e of hostiles(dim, center, r + 1.5, caster, DN04.maxTargets)) {
        if (hit.has(e.id) || distXZ(e.location, center) > r) continue;
        hit.add(e.id);
        strike(e, center, dmg, faint);
      }
      for (const w of wraps.values()) {
        if (!w.wrapped || soothed.has(w.p.id) || !w.p.isValid || distXZ(w.p.location, center) > r) continue;
        soothed.add(w.p.id);
        recoil(w);
        particle(dim, "dn_lull_calm", up(w.p.location, 1.2));
        if (!faint) sound(dim, "dn_lull_calm", w.p.location, 0.6);
      }
    });
    scene.at(t0 + DN04.waveTicks, () => wv.state(W.fade));
    scene.at(t0 + DN04.waveTicks + L2.fade, () => scene.despawn(wv));
  }
  function strike(e, center, dmg, faint) {
    damage(e, dmg, caster);
    particle(dim, "dn_lull_eye", up(e.location, 1.6));
    sound(dim, "dn_lull_hit", e.location, faint ? 0.6 : 0.9);
    if (!isAlive(e)) return;
    effect(e, "slowness", DN04.slowTicks, faint ? 0 : DN04.slowAmp);
    effect(e, "weakness", DN04.weaknessTicks, DN04.weaknessAmp);
    const out = norm(flat(sub(e.location, center)));
    const dir = (e.id.charCodeAt(e.id.length - 1) ?? 0) % 2 === 0 ? 1 : -1;
    shove(e, add(mul(right(out), dir), mul(out, 0.5)), DN04.disorientShove * (faint ? 0.6 : 1), 0.12);
    dizzy.set(e.id, { e, until: scene.tick + DN04.disorientTicks, yaw: yawOf(out), dir, t0: scene.tick });
  }
  function updateDizzy(t) {
    for (const [id, d] of dizzy) {
      if (t > d.until || !isAlive(d.e)) {
        dizzy.delete(id);
        continue;
      }
      try {
        d.e.setRotation({ x: 0, y: d.yaw + d.dir * DN04.disorientSpin * (t - d.t0) });
      } catch {
      }
    }
  }
  scene.at(tUnravel, () => {
    tap.state(T4.unravel);
    sound(dim, "dn_lull_unravel", hover, 1);
    particle(dim, "dn_lull_unravel", up(hover, 2.2));
    if (tele?.valid) {
      tele.state(3);
      const tl = tele;
      scene.after(8, () => scene.despawn(tl));
    }
    for (const w of [...wraps.values()]) release2(w);
  });
  scene.at(tUnravel + 14, () => tap.skin(0));
  scene.at(tUnravel + L2.unravel - 6, () => burst(dim, "dn_lull_mote", bookAt(), 0.5, 4));
  scene.endAt(tEnd);
});

// src/config/dn05.ts
var DN05 = {
  // ---- geometry (must match tools/assets/dn_city.py: R_QUARTER 120 units x scale 2 / 16 = 15 blocks)
  /** Height of the city's islands above the focus point (blocks). */
  cityHeight: 18,
  /** Distance of the four quarters from the central spire (blocks; fixed by the causeway model). */
  quarterDistance: 15,
  /** Small dream-logic height offsets of the four quarters (blocks). */
  quarterLift: [0, 0.6, -0.4, 0.4],
  /** Radius of the designated target area that constructs hunt in (blocks). */
  areaRadius: 22,
  /** How far the focus snaps to a hostile near the aim point. */
  focusSnap: 12,
  // ---- Phase I: The Gentle Arrival (allied defense)
  /** Fraction of incoming damage that still reaches protected allies (0.65 = 35% resistance). */
  wardFactor: 0.65,
  /** Allies within this distance of the focus (or the caster) are protected. */
  wardRadius: 34,
  /** Regeneration granted to allies when the city has assembled (ticks, amplifier). */
  regenTicks: 200,
  regenAmp: 0,
  // ---- Phase II: The Streets Begin to Move
  /** Maximum sky-stairs that descend beside allies as cover. */
  maxStairs: 3,
  /** Damage factor for allies sheltering under a stair pavilion (stacks with the ward). */
  coverFactor: 0.6,
  /** Radius around a pavilion that counts as cover, and that hostile projectiles dissolve in. */
  coverRadius: 3.5,
  /** Ticks between Phase II architectural attacks (balcony / rolling street, alternating). */
  attackEvery: 22,
  /** Telegraph lead time before a balcony lands (ticks). */
  balconyWarn: 20,
  balconyDamage: 11,
  balconyRadius: 2.8,
  /** Slowness ticks applied by a balcony impact. */
  balconySlowTicks: 50,
  streetDamage: 8,
  /** Rolling street: half-width of its crushing path, travel length and speed (blocks, blocks/tick). */
  streetWidth: 1.8,
  streetLength: 15,
  streetSpeed: 0.55,
  streetShove: 1.3,
  // ---- Phase III: The Nightmare Under the Facade (hunters)
  doorCount: 3,
  /** Passes each flying doorframe makes. */
  doorPasses: 2,
  doorDamage: 9,
  /** Radius of the doorway around its threshold that catches enemies. */
  doorReach: 1.8,
  /** Throw out the far side of the door (horizontal, vertical). */
  doorThrowH: 1.6,
  doorThrowV: 0.55,
  windowCount: 2,
  /** Stares per window before it shatters. */
  windowStares: 2,
  stareDamage: 7,
  /** Half-width of the stare line. */
  stareWidth: 1.3,
  stareSlowTicks: 40,
  glassDamage: 9,
  glassRadius: 2.6,
  corridorDamage: 10,
  /** Enemies within this distance of the corridor's end are caught when it snaps shut. */
  corridorCatch: 3,
  /** Ticks the corridor holds its catch (real restraint). */
  corridorHold: 50,
  stairfallDamage: 9,
  stairfallRadius: 2.2,
  fragmentCount: 4,
  biteDamage: 5,
  /** Fragment bites when the target is closer than this; otherwise it hops up to hopDistance. */
  biteRange: 1.9,
  hopDistance: 2.4,
  // ---- Phase IV: The Sleeping Collapse (finisher)
  waveRadius: 24,
  /** Each enemy struck takes waveBase + waveConcentrate / (enemies in area): the fewer sleepers, the deeper the dream. */
  waveBase: 16,
  waveConcentrate: 30,
  waveKnockH: 1.8,
  waveKnockV: 0.6
};

// src/spells/_dn05_hunters.ts
var BAL = { hidden: 0, drop: 1, impact: 2 };
var STREET = { hidden: 0, appear: 1, roll: 2, crumble: 3 };
var STAIR = { hidden: 0, descend: 1, stand: 2, retract: 3 };
var DOOR2 = { hidden: 0, arrive: 1, fly: 2, swoop: 3, depart: 4 };
var WIN = { hidden: 0, arrive: 1, hover: 2, blink: 3, stare: 4, shatter: 5 };
var COR = { hidden: 0, unfold: 1, snap: 2, clamp: 3, fold: 4 };
var SF = { hidden: 0, slam: 1, rest: 2, sink: 3 };
var FR = { hidden: 0, arrive: 1, idle: 2, hop: 3, bite: 4, crumble: 5 };
var T5 = {
  stairDown: secs(1.6),
  stairUp: secs(1.2),
  balDrop: secs(0.8),
  balHit: secs(0.9),
  stAppear: secs(0.6),
  stCrumble: secs(0.6),
  doorArrive: secs(1),
  doorSwoop: secs(0.8),
  doorSlam: secs(0.38),
  doorDepart: secs(0.8),
  winArrive: secs(0.8),
  winBlink: secs(0.8),
  winStare: secs(1),
  winFire: secs(0.45),
  winShatter: secs(0.7),
  corUnfold: secs(1),
  corSnap: secs(0.35),
  corFold: secs(0.8),
  sfFirst: secs(0.45),
  sfStep: secs(0.3),
  sfSink: secs(0.8),
  frArrive: secs(0.8),
  frHop: secs(0.6),
  frBite: secs(0.5),
  frBiteHit: secs(0.27),
  frCrumble: secs(0.7)
};
var CORRIDOR_LEN = 5 * 16 * 1.5 / 16;
var SF_CHUNKS = 5;
var SF_CHUNK = 32 * 1.5 / 16;
function aimAt(c, from, seed) {
  const f = c.foes(from);
  if (f.length) {
    const e = f[seed % Math.min(f.length, 3)];
    return { loc: groundBelow(c.dim, e.location), e };
  }
  return { loc: c.spot(seed) };
}
function finish(c, a, state, ticks) {
  if (!a.valid) return;
  a.state(state);
  c.scene.after(ticks, () => {
    c.scene.despawn(a);
    c.hunters.delete(a);
  });
}
function doorframe(c, i, until) {
  const { scene, dim } = c;
  const home = c.sky(i + 1);
  const door = scene.spawn("dn_city_door", home, { state: DOOR2.arrive, yaw: yawOf(sub(c.center, home)) });
  c.hunters.add(door);
  sound(dim, "dn_city_door", home, 1, 0.8);
  burst(dim, "dn_city_door", up(home, 2), 2, 6);
  let pos = home;
  let t0 = scene.tick + T5.doorArrive;
  scene.at(t0, () => door.state(DOOR2.fly));
  const passLen = 36;
  for (let p = 0; p < DN05.doorPasses; p++) {
    const start = t0 + 6 + p * (passLen + 10);
    if (start + passLen > until) break;
    scene.at(start, () => {
      if (!door.valid) return;
      const tgt = aimAt(c, pos, i + p);
      const T0 = up(tgt.loc, 0.1);
      const d = norm(flat(sub(T0, pos)));
      const path = [pos, add(up(T0, 2.5), mul(d, -5)), T0, add(up(T0, 2), mul(d, 5)), add(up(T0, 8), mul(d, 9))];
      const yaw = yawOf(d);
      scene.span(start, start + passLen, (q) => {
        pos = spline(path, q);
        door.move(pos, yaw);
      });
      const hitAt = start + Math.round(passLen / 2);
      scene.at(hitAt - T5.doorSlam, () => {
        door.state(DOOR2.swoop);
        sound(dim, "dn_city_door", T0, 1.2);
      });
      scene.at(hitAt, () => {
        particle(dim, "dn_city_door", up(T0, 1.5));
        particle(dim, "dn_city_dust_n", T0);
        for (const e of c.foes(T0)) {
          if (dist(e.location, T0) > DN05.doorReach + 0.6) continue;
          damage(e, DN05.doorDamage, c.caster);
          shove(e, d, DN05.doorThrowH, DN05.doorThrowV);
        }
      });
      scene.at(start + passLen, () => door.state(DOOR2.fly));
    });
  }
  scene.at(Math.min(until, t0 + 6 + DN05.doorPasses * (passLen + 10)), () => finish(c, door, DOOR2.depart, T5.doorDepart));
}
function windowEye(c, i, until) {
  const { scene, dim } = c;
  let pos = c.sky(i + 2);
  const win = scene.spawn("dn_city_window", pos, { state: WIN.arrive });
  c.hunters.add(win);
  sound(dim, "dn_city_groan", pos, 0.7, 1.3);
  let t = scene.tick + T5.winArrive;
  scene.at(t, () => win.state(WIN.hover));
  const glide = (to, from, ticks, look) => {
    const a = pos;
    scene.span(from, from + ticks, (q) => {
      pos = lerp(a, to, smooth(q));
      win.move(pos, yawOf(sub(look(), pos)));
    });
  };
  for (let k2 = 0; k2 < DN05.windowStares; k2++) {
    const t1 = t;
    const cycle = 16 + T5.winBlink + T5.winStare;
    if (t1 + cycle > until - 40) break;
    scene.at(t1, () => {
      const tgt = aimAt(c, pos, i * 2 + k2);
      let goal = tgt.loc;
      const side = norm(flat(sub(c.caster.location, goal)));
      const hov = up(add(goal, mul(add(side, mul(right(side), k2 % 2 ? 1 : -1)), 2.6)), 3.6);
      const look = () => tgt.e && isAlive(tgt.e) ? tgt.e.location : goal;
      glide(hov, t1, 16, look);
      scene.at(t1 + 16, () => {
        win.state(WIN.blink);
        line(dim, "dn_city_eye", pos, up(look(), 1), 4);
      });
      scene.at(t1 + 16 + T5.winBlink, () => {
        win.state(WIN.stare);
        sound(dim, "dn_city_stare", pos, 1);
      });
      scene.at(t1 + 16 + T5.winBlink + T5.winFire, () => {
        if (tgt.e && isAlive(tgt.e)) goal = tgt.e.location;
        const from = pos, dir = norm(sub(up(goal, 1), from));
        const end = add(from, mul(dir, dist(from, goal) + 3));
        line(dim, "dn_city_stare", from, end, 10);
        particle(dim, "dn_city_eye", up(goal, 1));
        for (const e of c.foes(goal)) {
          if (distToSegment(add(e.location, { x: 0, y: 1, z: 0 }), from, end) > DN05.stareWidth) continue;
          damage(e, DN05.stareDamage, c.caster);
          effect(e, "slowness", DN05.stareSlowTicks, 1);
        }
      });
      scene.at(t1 + cycle, () => win.state(WIN.hover));
    });
    t += cycle;
  }
  const tEnd = Math.min(t, until - 32);
  scene.at(tEnd, () => {
    const tgt = aimAt(c, pos, i + 7);
    const below = tgt.loc;
    const warn = scene.spawn("telegraph", below, { kind: 1, size: DN05.glassRadius, state: 1 });
    glide(up(below, 4.5), tEnd, 16, () => below);
    scene.at(tEnd + 16, () => {
      win.state(WIN.shatter);
      sound(dim, "dn_city_balcony", below, 0.8, 1.4);
    });
    scene.at(tEnd + 20, () => {
      warn.state(3);
      burst(dim, "dn_city_glass", up(below, 3.5), 1.5, 5);
      particle(dim, "dn_city_ring", up(below, 0.2));
      for (const e of c.foes(below)) if (dist(e.location, below) <= DN05.glassRadius) damage(e, DN05.glassDamage, c.caster);
    });
    scene.at(tEnd + 28, () => scene.despawn(warn));
    scene.at(tEnd + 16 + T5.winShatter, () => {
      scene.despawn(win);
      c.hunters.delete(win);
    });
  });
}
function corridor(c, i) {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, i);
  const end = tgt.loc;
  let dir = norm(flat(sub(end, c.caster.location)));
  dir = i % 2 ? right(dir) : mul(right(dir), -1);
  const origin = groundBelow(dim, add(end, mul(dir, -CORRIDOR_LEN)));
  const warn = scene.spawn("telegraph", end, { kind: 1, size: DN05.corridorCatch * 0.8, state: 1 });
  const cor = scene.spawn("dn_city_corridor", origin, { state: COR.unfold, yaw: yawOf(dir) });
  c.hunters.add(cor);
  sound(dim, "dn_city_corridor", lerp(origin, end, 0.5), 1.2);
  const t0 = scene.tick;
  scene.at(t0 + T5.corUnfold, () => {
    cor.state(COR.snap);
    warn.state(3);
    particle(dim, "dn_city_dust_n", end);
    burst(dim, "dn_city_door", up(end, 1.5), 1.2, 4);
    for (const e of c.foes(end)) {
      const inEnd = dist(e.location, end) <= DN05.corridorCatch;
      const inHall = distToSegment(e.location, origin, end) <= 1.5;
      if (!inEnd && !inHall) continue;
      damage(e, DN05.corridorDamage, c.caster);
      if (inEnd) restrain(scene, e, DN05.corridorHold, end);
    }
  });
  scene.at(t0 + T5.corUnfold + 8, () => scene.despawn(warn));
  scene.at(t0 + T5.corUnfold + T5.corSnap, () => cor.state(COR.clamp));
  scene.at(t0 + T5.corUnfold + DN05.corridorHold, () => {
    sound(dim, "dn_city_groan", end, 0.6, 1.4);
    finish(c, cor, COR.fold, T5.corFold);
  });
}
function stairfall(c, i) {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, i + 1);
  const dir = norm(flat(sub(tgt.loc, c.caster.location)));
  const start = groundBelow(dim, add(tgt.loc, mul(dir, -SF_CHUNK * 2.5)));
  const centers = Array.from({ length: SF_CHUNKS }, (_, k2) => add(start, mul(dir, SF_CHUNK * (k2 + 0.5))));
  const warns = centers.map((p) => scene.spawn("telegraph", p, { kind: 1, size: DN05.stairfallRadius * 0.8, state: 1 }));
  const t0 = scene.tick + 12;
  let sf;
  scene.at(t0, () => {
    sf = scene.spawn("dn_city_stairfall", start, { state: SF.slam, yaw: yawOf(dir) });
    c.hunters.add(sf);
    sound(dim, "dn_city_groan", up(start, 6), 0.8, 1.1);
  });
  centers.forEach((p, k2) => {
    scene.at(t0 + T5.sfFirst + k2 * T5.sfStep, () => {
      warns[k2].state(3);
      sound(dim, "dn_city_stairfall", p, 1, 1 - k2 * 0.04);
      particle(dim, "dn_city_dust_n", p);
      particle(dim, "dn_city_ring", up(p, 0.2));
      for (const e of c.foes(p)) {
        if (dist(e.location, p) > DN05.stairfallRadius) continue;
        damage(e, DN05.stairfallDamage, c.caster);
        knockback(e, p, 0.6, 0.45);
      }
    });
    scene.at(t0 + T5.sfFirst + k2 * T5.sfStep + 8, () => scene.despawn(warns[k2]));
  });
  const tRest = t0 + T5.sfFirst + SF_CHUNKS * T5.sfStep;
  scene.at(tRest, () => sf?.state(SF.rest));
  scene.at(tRest + 16, () => {
    if (sf) finish(c, sf, SF.sink, T5.sfSink);
  });
}
function fragment(c, i, until) {
  const { scene, dim } = c;
  let pos = groundBelow(dim, c.spot(i * 3 + 11));
  const fr = scene.spawn("dn_city_fragment", pos, { state: FR.arrive, yaw: yawOf(sub(c.center, pos)) });
  c.hunters.add(fr);
  scene.after(7, () => {
    particle(dim, "dn_city_dust_n", pos);
    sound(dim, "dn_city_fragment", pos, 0.9, 0.8);
  });
  let yaw = 0;
  const step = 15;
  scene.every(step, (el) => {
    if (!fr.valid) return;
    const f = c.foes(pos);
    const target = f.length ? f[i % Math.min(f.length, 2)] : void 0;
    const goal = target ? target.location : c.spot(i * 5 + el);
    const d = sub(goal, pos);
    yaw = yawOf(d);
    if (target && dist(target.location, pos) <= DN05.biteRange + 0.6) {
      fr.state(FR.bite).face(yaw);
      scene.after(T5.frBiteHit, () => {
        sound(dim, "dn_city_bite", pos, 1);
        particle(dim, "dn_city_shard", up(pos, 1.2));
        if (isAlive(target) && dist(target.location, pos) <= DN05.biteRange + 1) damage(target, DN05.biteDamage, c.caster);
      });
    } else {
      const len2 = Math.min(DN05.hopDistance, Math.max(0.5, Math.hypot(d.x, d.z) - DN05.biteRange * 0.7));
      const from = pos;
      const to = groundBelow(dim, add(up(from, 1), mul(norm(flat(d)), len2)));
      fr.state(FR.hop);
      scene.span(scene.tick + 2, scene.tick + 11, (q) => {
        pos = up(lerp(from, to, q), Math.sin(q * Math.PI) * 1.1);
        fr.move(pos, yaw);
      });
      scene.after(11, () => {
        pos = to;
        particle(dim, "dn_city_dust_n", to);
      });
    }
    scene.after(T5.frHop, () => fr.state(FR.idle));
  }, scene.tick + T5.frArrive, until);
  scene.at(until, () => {
    sound(dim, "dn_city_bite", pos, 0.6, 0.7);
    finish(c, fr, FR.crumble, T5.frCrumble);
  });
}
function balcony(c, seed) {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, seed);
  let at = tgt.loc;
  const warn = scene.spawn("telegraph", at, { kind: 1, size: DN05.balconyRadius, state: 1 });
  const sky = c.sky(seed);
  const t0 = scene.tick;
  const bal = scene.spawn("dn_city_balcony", up(sky, -2), { state: BAL.drop, yaw: seed * 77 });
  sound(dim, "dn_city_balcony", at, 1.1);
  scene.every(1, () => {
    if (tgt.e && isAlive(tgt.e)) {
      at = groundBelow(dim, tgt.e.location);
      warn.move(at);
    }
  }, t0, t0 + DN05.balconyWarn - 8);
  const fallFrom = t0 + DN05.balconyWarn - 16;
  let top = up(sky, -2);
  scene.at(fallFrom, () => {
    top = bal.loc;
  });
  scene.span(fallFrom, t0 + DN05.balconyWarn, (q) => bal.move(lerp(top, at, easeIn(q))));
  scene.at(t0 + DN05.balconyWarn, () => {
    bal.state(BAL.impact);
    warn.state(3);
    particle(dim, "dn_city_dust", at);
    particle(dim, "dn_city_ring", up(at, 0.2));
    burst(dim, "dn_city_shard", up(at, 1), 1, 3);
    for (const e of c.foes(at)) {
      if (dist(e.location, at) > DN05.balconyRadius) continue;
      damage(e, DN05.balconyDamage, c.caster);
      effect(e, "slowness", DN05.balconySlowTicks, 1);
    }
  });
  scene.at(t0 + DN05.balconyWarn + 8, () => scene.despawn(warn));
  scene.at(t0 + DN05.balconyWarn + T5.balHit, () => scene.despawn(bal));
}
function rollingStreet(c, seed) {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, seed);
  const dir = norm(flat(sub(tgt.loc, c.caster.location)));
  const a = groundBelow(dim, add(tgt.loc, mul(dir, -DN05.streetLength * 0.4)));
  const b = add(a, mul(dir, DN05.streetLength));
  const warn = scene.spawn("telegraph", a, { kind: 1, size: 1.4, state: 1 });
  scene.every(4, () => line(dim, "dn_city_chime", up(a, 0.3), up(b, 0.3), 7), scene.tick, scene.tick + 20);
  const t0 = scene.tick;
  const yaw = yawOf(dir);
  let st2;
  scene.at(t0 + 8, () => {
    st2 = scene.spawn("dn_city_street", a, { state: STREET.appear, yaw });
  });
  const rollTicks = Math.round(DN05.streetLength / DN05.streetSpeed);
  const hit = /* @__PURE__ */ new Set();
  scene.at(t0 + 8 + T5.stAppear, () => {
    st2?.state(STREET.roll);
    warn.state(3);
    sound(dim, "dn_city_street", a, 1.1);
  });
  scene.at(t0 + 8 + T5.stAppear + 8, () => scene.despawn(warn));
  scene.span(t0 + 8 + T5.stAppear, t0 + 8 + T5.stAppear + rollTicks, (q) => {
    const p = lerp(a, b, q);
    st2?.move(p, yaw);
    for (const e of c.foes(p)) {
      if (hit.has(e.id) || dist(flat(e.location), flat(p)) > DN05.streetWidth) continue;
      hit.add(e.id);
      damage(e, DN05.streetDamage, c.caster);
      shove(e, dir, DN05.streetShove, 0.5);
      particle(dim, "dn_city_dust", e.location);
    }
  });
  scene.at(t0 + 8 + T5.stAppear + rollTicks, () => {
    if (!st2) return;
    st2.state(STREET.crumble);
    particle(dim, "dn_city_dust", b);
    const s = st2;
    scene.after(T5.stCrumble, () => scene.despawn(s));
  });
}

// src/spells/dn05_sleeping_city.ts
var D = { hidden: 0, assemble: 1, dream: 2, living: 3, warp: 4, nightmare: 5, collapse: 6 };
var MINI = { hidden: 0, form: 1, idle: 2, charge: 3, release: 4, wink: 5 };
var WAVE = { hidden: 0, expand: 1, fade: 2 };
var T_ASM = secs(5);
var T_WARP = secs(2);
var T_COL = secs(3);
var T_MINI_FORM = secs(1.2);
var T_MINI_CHARGE = secs(1.6);
var T_MINI_WINK = secs(0.6);
var T_WAVE = secs(1.4);
var WAVE_KEYS = [[0, 0.03], [0.35, 0.42], [0.7, 0.74], [1, 0.92], [1.4, 1]];
var PAVILION_UNITS = 8;
var P2 = secs(7);
var P3 = secs(16);
var P4 = secs(27);
function waveFrac(sec) {
  for (let i = 1; i < WAVE_KEYS.length; i++) {
    const [t0, v0] = WAVE_KEYS[i - 1], [t1, v1] = WAVE_KEYS[i];
    if (sec <= t1) return v0 + (v1 - v0) * ((sec - t0) / (t1 - t0));
  }
  return 1;
}
var dn05_sleeping_city_default = defineSpell("dn05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, DN05.focusSnap);
  const H2 = DN05.cityHeight;
  const spirePos = up(center, H2);
  const qAngles = [45, 135, 225, 315];
  const qPos = qAngles.map((a, k2) => polar(center, DN05.quarterDistance, a, H2 + DN05.quarterLift[k2]));
  const anchors = [spirePos, ...qPos];
  const tb = blocksFor(scene);
  const hunters = /* @__PURE__ */ new Set();
  const ctx = {
    scene,
    caster,
    dim,
    center,
    hunters,
    sky: (i) => up(anchors[(i % anchors.length + anchors.length) % anchors.length], -3),
    foes: (from) => {
      const f = hostiles(dim, center, DN05.areaRadius + 6, caster);
      return f.sort((a, b) => dist(a.location, from) - dist(b.location, from));
    },
    spot: (seed) => groundBelow(dim, polar(center, 3 + seed * 5.3 % 10, seed * 137.5))
  };
  const districts = [];
  const spire = scene.spawn("dn_city_spire", spirePos, { state: D.assemble, yaw: 0 });
  districts.push({ a: spire, pos: spirePos });
  sound(dim, "dn_city_arrive", up(center, 6), 1.4);
  qPos.forEach((p, k2) => {
    scene.at(8 + k2 * 8, () => {
      const q = scene.spawn(k2 % 2 ? "dn_city_quarter_b" : "dn_city_quarter_a", p, { state: D.assemble, yaw: yawOf(sub(spirePos, p)) });
      districts.push({ a: q, pos: p });
      particle(dim, "dn_city_cloud", up(p, -1));
      sound(dim, "dn_city_rise", p, 0.8, 0.95 + k2 * 0.05);
    });
  });
  let ringA;
  scene.at(30, () => {
    ringA = scene.spawn("dn_city_ring", spirePos, { state: D.assemble, yaw: 0 });
    districts.push({ a: ringA, pos: spirePos });
  });
  scene.every(6, (el) => particle(dim, "dn_city_cloud", up(anchors[el / 6 % anchors.length], -1.5)), 0, secs(3));
  scene.at(secs(1.8), () => sound(dim, "dn_city_rise", spirePos, 1));
  for (let k2 = 0; k2 < 5; k2++) {
    scene.at(secs(3.7) + k2 * 9, () => {
      const p = anchors[k2 % anchors.length];
      sound(dim, "dn_city_window", p, 0.8, 1 + k2 * 0.04);
      burst(dim, "dn_city_window", up(p, 5), 3, 3);
      particle(dim, "dn_city_chime", up(p, 7));
    });
  }
  const allySet = /* @__PURE__ */ new Set([caster.id]);
  const refreshAllies = () => {
    for (const p of allies(dim, center, DN05.wardRadius, caster)) allySet.add(p.id);
    for (const p of allies(dim, caster.location, 8, caster)) allySet.add(p.id);
  };
  refreshAllies();
  scene.every(20, refreshAllies, 0, P4 + secs(6));
  const ward = addWard({
    scene,
    factor: DN05.wardFactor,
    protects: (e) => e.typeId === "minecraft:player" && allySet.has(e.id),
    onAbsorb: (_amt, _att, victim) => particle(dim, "dn_city_ward", up(victim.location, 1))
  });
  scene.at(40, () => {
    refreshAllies();
    sound(dim, "dn_city_ward", caster.location, 1);
    for (const p of allies(dim, center, DN05.wardRadius, caster).concat(isAlive(caster) ? [caster] : [])) {
      effect(p, "regeneration", DN05.regenTicks, DN05.regenAmp);
      particle(dim, "dn_city_ward", up(p.location, 1));
    }
  });
  scene.at(P2 - 1, () => districts.forEach((d) => d.a.state(D.dream)));
  scene.at(P2, () => {
    districts.forEach((d) => d.a.state(D.living));
    sound(dim, "dn_city_move", spirePos, 1.4);
  });
  scene.every(
    secs(3),
    () => sound(dim, "dn_city_move", anchors[Math.floor(scene.tick / 7) % anchors.length], 1.1, 0.95),
    P2 + secs(3),
    P3 - 10
  );
  scene.every(8, (el) => particle(dim, "dn_city_mote", up(anchors[el / 8 % anchors.length], -4)), P2, P3);
  const coverWards = [];
  scene.at(P2 + 10, () => {
    const sheltered = allies(dim, center, DN05.wardRadius, caster).filter((p) => isAlive(p));
    if (!sheltered.some((p) => p.id === caster.id) && isAlive(caster)) sheltered.unshift(caster);
    sheltered.slice(0, DN05.maxStairs).forEach((ally, k2) => {
      let away = norm(flat(sub(ally.location, center)));
      if (dist(flat(ally.location), flat(center)) < 2) away = norm(flat(mul(aim.forward, -1)));
      const size = (H2 - 2) / 12;
      const unit = 2 * size / 16;
      const foot = groundBelow(dim, add(ally.location, mul(away, -PAVILION_UNITS * unit)));
      const pav = add(foot, mul(away, PAVILION_UNITS * unit));
      scene.after(k2 * 6, () => {
        const st2 = scene.spawn("dn_city_stair", foot, { state: STAIR.descend, size, yaw: yawOf(away) });
        sound(dim, "dn_city_stair", up(foot, 6), 1.1, 1 + k2 * 0.06);
        scene.after(T5.stairDown, () => {
          st2.state(STAIR.stand);
          particle(dim, "dn_city_dust", foot);
          ring(dim, "dn_city_ward", up(pav, 0.5), 1.5, 4, k2 * 30);
          const side = right(away);
          for (let s = -1; s <= 1; s++) {
            const b = add(add(foot, mul(away, -1.1)), mul(side, s));
            tb.column(Math.floor(b.x), Math.floor(foot.y), Math.floor(b.z), 2, BARRIER);
          }
          for (const s of [-1, 1]) {
            const col = add(foot, mul(side, s * 11 * unit));
            tb.column(Math.floor(col.x), Math.floor(foot.y), Math.floor(col.z), 4, BARRIER);
          }
          coverWards.push(addWard({
            scene,
            factor: DN05.coverFactor,
            protects: (e) => e.typeId === "minecraft:player" && allySet.has(e.id) && dist(e.location, pav) <= DN05.coverRadius
          }));
          scene.every(10, () => {
            for (const at of dissolveProjectiles(scene, pav, DN05.coverRadius + 1)) particle(dim, "dn_city_chime", at);
          }, scene.tick, P3 - 30);
        });
        scene.at(P3 - 26, () => {
          st2.state(STAIR.retract);
          sound(dim, "dn_city_stair", up(foot, 6), 0.8, 1.2);
          const side = right(away);
          for (let s = -1; s <= 1; s++) {
            const b = add(add(foot, mul(away, -1.1)), mul(side, s));
            tb.removeColumn(Math.floor(b.x), Math.floor(foot.y), Math.floor(b.z), 2);
          }
          for (const s of [-1, 1]) {
            const col = add(foot, mul(side, s * 11 * unit));
            tb.removeColumn(Math.floor(col.x), Math.floor(foot.y), Math.floor(col.z), 4);
          }
        });
        scene.at(P3 - 26 + T5.stairUp, () => scene.despawn(st2));
      });
    });
  });
  scene.at(P3 - 26, () => coverWards.forEach((w) => removeWard(w)));
  let attack = 0;
  scene.every(DN05.attackEvery, () => {
    if (attack % 2 === 0) balcony(ctx, attack + 1);
    else rollingStreet(ctx, attack + 2);
    attack++;
  }, P2 + 25, P3 - 45);
  scene.at(P3, () => {
    districts.forEach((d) => d.a.state(D.warp).skin(1));
    sound(dim, "dn_city_warp", spirePos, 1.5);
    burst(dim, "dn_city_night", spirePos, 6, 6);
  });
  scene.at(P3 + T_WARP, () => districts.forEach((d) => d.a.state(D.nightmare)));
  scene.every(
    secs(2.4),
    (el) => sound(dim, "dn_city_groan", anchors[el / 48 % anchors.length], 1, 0.9),
    P3 + 20,
    P4 - 10
  );
  scene.every(9, (el) => particle(dim, "dn_city_cloud_n", up(anchors[el / 9 % anchors.length], -2)), P3, P4);
  const huntEnd = P4 - 6;
  for (let i = 0; i < DN05.doorCount; i++) scene.at(P3 + 20 + i * 10, () => doorframe(ctx, i, huntEnd));
  for (let i = 0; i < DN05.windowCount; i++) scene.at(P3 + 26 + i * 30, () => windowEye(ctx, i, huntEnd));
  for (let i = 0; i < DN05.fragmentCount; i++) scene.at(P3 + 40 + i * 4, () => fragment(ctx, i, huntEnd - 10));
  scene.at(P3 + 60, () => corridor(ctx, 0));
  scene.at(P3 + 130, () => corridor(ctx, 1));
  scene.at(P3 + 80, () => stairfall(ctx, 0));
  scene.at(P3 + 150, () => stairfall(ctx, 1));
  const miniAt = () => {
    let f = aim.forward;
    try {
      const v2 = caster.getViewDirection();
      if (Number.isFinite(v2.x) && Math.hypot(v2.x, v2.z) > 0.05) f = norm(flat(v2));
    } catch {
    }
    const base = isAlive(caster) ? caster.location : scene.origin;
    return up(add(add(base, mul(f, 0.9)), mul(right(f), 0.35)), 2.3);
  };
  scene.at(P4, () => {
    for (const h of [...hunters]) {
      scene.despawn(h);
      hunters.delete(h);
    }
    sound(dim, "dn_city_collapse", spirePos, 1.5);
  });
  const order = () => {
    const r = districts.filter((d) => d.a === ringA);
    const q = districts.filter((d) => d.a !== ringA && d.a !== spire);
    return [...r, ...q, ...districts.filter((d) => d.a === spire)];
  };
  scene.at(P4, () => {
    order().forEach((d, k2) => {
      const t0 = scene.tick + k2 * 10;
      scene.at(t0, () => {
        d.a.state(D.collapse);
        particle(dim, "dn_city_fold", d.pos);
      });
      scene.span(t0 + 15, t0 + T_COL, (q) => d.a.move(lerp(d.pos, miniAt(), easeIn(q) * 0.85)));
      scene.at(t0 + T_COL, () => scene.despawn(d.a));
    });
  });
  const tMini = P4 + 60;
  let mini;
  scene.at(tMini, () => {
    mini = scene.spawn("dn_city_mini", miniAt(), { state: MINI.form });
    sound(dim, "dn_city_mini", miniAt(), 1);
    burst(dim, "dn_city_key", miniAt(), 0.8, 5);
  });
  scene.every(1, () => mini?.move(miniAt()), tMini, tMini + 120);
  scene.at(tMini + T_MINI_FORM, () => mini?.state(MINI.idle));
  const tCharge = tMini + T_MINI_FORM + 6;
  const tWave = tCharge + T_MINI_CHARGE;
  let warn;
  scene.at(tCharge - 10, () => {
    warn = scene.spawn("telegraph", center, { kind: 1, size: DN05.waveRadius, state: 4 });
  });
  scene.at(tCharge, () => {
    mini?.state(MINI.charge);
    sound(dim, "dn_city_charge", miniAt(), 1.2);
  });
  scene.every(3, () => line(dim, "dn_city_streak", up(miniAt(), 1.2), up(center, 2), 6), tWave - 12, tWave);
  scene.at(tWave - 7, () => sound(dim, "dn_city_wave", center, 1.6));
  let wave;
  let enemiesAtLaunch = 1;
  const struck = /* @__PURE__ */ new Set();
  scene.at(tWave, () => {
    mini?.state(MINI.release);
    warn?.state(3);
    wave = scene.spawn("dn_city_wave", up(center, 0.1), { state: WAVE.expand, size: DN05.waveRadius });
    particle(dim, "fx_flash", up(center, 2));
    enemiesAtLaunch = Math.max(1, hostiles(dim, center, DN05.waveRadius, caster).length);
  });
  scene.at(tWave + 8, () => {
    if (warn) scene.despawn(warn);
  });
  scene.span(tWave, tWave + T_WAVE, (_q, el) => {
    const r = DN05.waveRadius * waveFrac(el / 20);
    if (el % 3 === 0) ring(dim, "dn_city_wave", up(center, 0.5), r, 10, el * 7);
    for (const e of hostiles(dim, center, r + 0.5, caster)) {
      if (struck.has(e.id)) continue;
      struck.add(e.id);
      damage(e, DN05.waveBase + DN05.waveConcentrate / enemiesAtLaunch, caster);
      knockback(e, center, DN05.waveKnockH, DN05.waveKnockV);
      particle(dim, "dn_city_key", up(e.location, 1));
    }
  });
  scene.at(tWave + T_WAVE, () => wave?.state(WAVE.fade));
  scene.at(tWave + T_WAVE + 10, () => {
    if (wave) scene.despawn(wave);
  });
  const tWink = tWave + T_WAVE + 4;
  scene.at(tWink, () => {
    mini?.state(MINI.wink);
    sound(dim, "dn_city_wink", miniAt(), 1);
  });
  scene.at(tWink + T_MINI_WINK, () => {
    burst(dim, "dn_city_chime", miniAt(), 0.5, 3);
    if (mini) scene.despawn(mini);
  });
  scene.onEnd(() => removeWard(ward));
  scene.endAt(tWink + T_MINI_WINK + 4);
});

// src/config/dn06.ts
var DN06 = {
  // ---- domain & staging (blocks)
  /** Radius of the spell domain around the focus point: marks, zones and strikes stay inside it. */
  radius: 20,
  /** Maximum enemies carrying a sleeping-moon mark (marked enemies are the targets of every strike). */
  maxMarks: 8,
  /**
   * Where the Dreamer stands, measured from the caster along the view: this far beyond the focus point,
   * but never nearer than stageMin (so the whole figure stays inside the first-person view) nor farther
   * than stageMax.
   */
  stageBeyond: 20,
  stageMin: 34,
  stageMax: 44,
  /** The bed hangs this far beyond the Dreamer (but never farther than bedMax from the caster, so it stays within
   *  entity view range on a phone), its mattress this high above the ground, tilted toward the caster. */
  bedBeyond: 16,
  bedMax: 55,
  bedHeight: 10.3,
  /** Nothing tall comes nearer the caster than this (zones, formations, the pendulum). */
  clearZone: 8,
  /** Largest body turn (deg) the Dreamer makes toward the main enemy group for the finale, and how far it may
   *  glide forward so that the beam from its face-door lands on that group. */
  finaleTurn: 35,
  finaleAdvance: 9,
  // ---- Phase II: giant-body attacks
  /** Dropped pillow: damage, blast radius and knockback. */
  pillowDamage: 10,
  pillowRadius: 3.5,
  pillowKnock: 1.4,
  /** Hand sweep: damage, reach of the hand around its path, sideways knockback, furthest lunge forward. */
  sweepDamage: 14,
  sweepRadius: 3.4,
  sweepKnock: 2.2,
  sweepLunge: 9,
  /** Spilled stairs: damage per enemy, width of the cascade. */
  stairsDamage: 9,
  stairsRadius: 2.4,
  // ---- Phase III: zones (all zones have this radius)
  zoneRadius: 4.5,
  /** Dream zones: heal per pulse (every zonePulse ticks), supportive effect duration, ward strength. */
  zonePulse: 20,
  dreamHeal: 2,
  dreamEffectTicks: 50,
  /** Fraction of damage that still reaches an ally standing in a dream zone, and the ward's total pool. */
  wardFactor: 0.55,
  wardPool: 40,
  /** Distance of the two flanking dream gardens from the caster, and their angle off the view (deg). */
  dreamFlank: 8.5,
  dreamFlankAngle: 48,
  /** Nightmare zones: damage per pulse, slowness/weakness strength, and the stronger "bite" every 2 pulses. */
  nightDamage: 3,
  nightSlowAmp: 2,
  biteDamage: 5,
  /** Ticks an enemy is swallowed (held) by the predatory corridor; levitation of the upside-down room. */
  corridorHold: 20,
  roomLift: 12,
  // ---- Phase IV: the Great Unreality
  /** Wheel of doors: damage, hit radius, rolling speed (blocks/tick). */
  wheelDamage: 16,
  wheelRadius: 3.2,
  wheelSpeed: 0.42,
  /** Window shards released by the arcade forearms: count and damage. */
  shards: 6,
  shardDamage: 10,
  /** Spiral-stair drill: impact damage/radius, damage per boring pulse, slowness ticks. */
  drillDamage: 18,
  drillRadius: 4,
  drillTick: 4,
  /** Bed pendulum: damage and hit radius around the cradle while it sweeps low, rope length. */
  pendulumDamage: 20,
  pendulumRadius: 5,
  pendulumLength: 12,
  /** Expanding room-cubes fired from the chest: count, damage, hold ticks, capture radius. */
  rooms: 3,
  roomDamage: 14,
  roomHold: 24,
  roomRadius: 3,
  /** Face-door finale: pull radius, pull speed (blocks/tick), beam damage every 12 ticks, final strike. */
  beamRadius: 9,
  beamPull: 0.2,
  beamDamage: 3,
  finalDamage: 32,
  finalRadius: 8,
  finalKnock: 2.6,
  /** Ticks of warning before every telegraphed giant strike (pillow, stairs, shards...). */
  warnShort: 20,
  warnLong: 40
};

// src/spells/dn06_the_dreamer.ts
var DS2 = {
  hidden: 0,
  manifest: 1,
  sit: 2,
  awaken: 3,
  rise: 4,
  hover: 5,
  sweep: 6,
  cabinet: 7,
  raise: 8,
  conjure: 9,
  conduct: 10,
  fireArms: 11,
  fireRooms: 12,
  finale: 13,
  slam: 14,
  forget: 15
};
var BED = { arrive: 1, float: 2, occupied: 3, dip: 4, empty: 5, fold: 6, swing: 7, vanish: 8, rest: 9, hang: 10 };
var CODEX = { open: 1, hold: 2, gather: 3, close: 4 };
var ZONE = { bloom: 1, idle: 2, fold: 3, fade: 4, bite: 5 };
var LAMP = { rise: 1, hold: 2, sink: 3 };
var TG = { warn: 1, hold: 2, flash: 3, warnSlow: 4 };
var LEN = {
  manifest: 72,
  sit: 52,
  awaken: 30,
  rise: 60,
  sweep: 60,
  cabinet: 40,
  raise: 40,
  fireArms: 32,
  fireRooms: 32,
  finale: 60,
  slam: 28,
  forget: 110
};
var HOVER_LIFT = 0.5;
var SWEEP_PATH = [
  [12.99, -0.38, 8.99],
  [8.46, -0.66, 13.33],
  [2.73, -0.17, 15.62],
  [-3.17, -1.06, 14.56],
  [-8.2, -1.17, 11.35]
];
var SWEEP_HIT = [25, 40];
var CHEST = [0, 4.9, 2.4];
var DOOR3 = [0, 9.37, 2.86];
var DOOR_FIN = [0, 7.89, 5.89];
var BEAM_LAND = 17.17;
var ARM = [2.8, 3.29, 9.16];
var PALM_R = [9.21, 9.34, 3.11];
var PALM_L = [-9.35, 8.97, 2.9];
var HAND_SLAM = [2.45, -1.47, 13.31];
var LIE = { feet: 4.27, crown: 6.63 };
var BED_SCALE = 1.4;
var PIVOT = { up: 7.4 * BED_SCALE / 16, fwd: 11.4 * BED_SCALE / 16 };
var PILLOW = { r: 22, y: -7.4, z: 63.4 };
var TILT_A = 40;
var SWING_T = 48;
var SWING_A = 58;
var DIP = [[0, 0], [7, -5], [16, -3], [28, -4.5], [44, -4]];
var STEP_LAND = (k2) => 8 + Math.round(k2 * 2.4);
var STEP = (k2) => 0.625 + k2 * 1.25;
var BOOK2 = [-1.28, 0.46, 2.19];
var LAMPS = 8;
var dn06_the_dreamer_default = defineSpell("dn06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 14);
  const fwd = norm({ x: aim.forward.x, y: 0, z: aim.forward.z });
  const rt = right(fwd);
  const C0 = { ...caster.location };
  const g0 = C0.y;
  const lights = blocksFor(scene);
  const faceYaw = yawOf(mul(fwd, -1));
  const at = (base, yaw, r, u, f) => {
    const fd = fromYaw(yaw), rr = right(fd);
    return { x: base.x + rr.x * r + fd.x * f, y: base.y + u, z: base.z + rr.z * r + fd.z * f };
  };
  const atR = (base, yaw, p, k2 = 1) => at(base, yaw, p[0] * k2, p[1] * k2, p[2] * k2);
  const rel = (r, u, f) => at(C0, aim.yaw, r, u, f);
  const ground = (p) => groundBelow(dim, { x: p.x, y: Math.max(p.y, g0 + 4), z: p.z }, 50);
  const clear2 = (p, minD = DN06.clearZone) => {
    const d = distXZ(p, C0);
    if (d >= minD) return p;
    const dir = d > 0.5 ? norm({ x: p.x - C0.x, y: 0, z: p.z - C0.z }) : fwd;
    return ground({ x: C0.x + dir.x * minD, y: p.y, z: C0.z + dir.z * minD });
  };
  const cd = distXZ(C0, center);
  const stageD = clamp(cd + DN06.stageBeyond, DN06.stageMin, DN06.stageMax);
  const stageG = ground(rel(0, 0, stageD));
  const stage = up(stageG, HOVER_LIFT);
  const bedD = Math.min(stageD + DN06.bedBeyond, DN06.bedMax);
  const bedG = ground(rel(0, 0, bedD));
  const bedRest = { x: bedG.x, y: Math.max(bedG.y, g0 - 2) + DN06.bedHeight, z: bedG.z };
  let seed = 7919;
  const rnd2 = () => {
    seed = seed * 16807 % 2147483647;
    return seed / 2147483647;
  };
  const scatter = (c, r, h0, h1) => {
    const a = rnd2() * Math.PI * 2, d = Math.sqrt(rnd2()) * r;
    return { x: c.x + Math.cos(a) * d, y: c.y + h0 + rnd2() * (h1 - h0), z: c.z + Math.sin(a) * d };
  };
  const fx = (id, p) => particle(dim, `dn_dreamer_${id}`, p);
  const sfx = (id, p, vol = 1, pitch = 1) => sound(dim, `dn_dreamer_${id}`, p, vol, pitch);
  const puff = (id, c, r, n) => {
    for (let i = 0; i < n; i++) {
      const y = 1 - 2 * (i + 0.5) / n, rr = Math.sqrt(1 - y * y) * r, a = i * 2.39996;
      fx(id, { x: c.x + Math.cos(a) * rr, y: c.y + y * r, z: c.z + Math.sin(a) * rr });
    }
  };
  const hoop = (id, c, r, n, ph = 0) => {
    for (let i = 0; i < n; i++) {
      const a = (ph + 360 * i / n) * Math.PI / 180;
      fx(id, { x: c.x + Math.cos(a) * r, y: c.y, z: c.z + Math.sin(a) * r });
    }
  };
  const streak = (id, a, b, n) => {
    for (let i = 0; i < n; i++) fx(id, lerp(a, b, n === 1 ? 0.5 : i / (n - 1)));
  };
  const hushed = /* @__PURE__ */ new Set();
  const hush = (t) => {
    hushed.add(t);
  };
  const layer = (from, to, fn) => {
    scene.every(1, (e) => {
      if (!hushed.has(scene.tick)) fn(e);
    }, from, to);
  };
  const times = (k2, fn) => {
    const n = Math.floor(k2) + (rnd2() < k2 - Math.floor(k2) ? 1 : 0);
    for (let i = 0; i < n; i++) fn();
  };
  const marks = /* @__PURE__ */ new Map();
  function markNew(limit = DN06.maxMarks) {
    for (const e of hostiles(dim, center, DN06.radius, caster)) {
      if (marks.size >= limit) break;
      if (marks.has(e.id)) continue;
      const a = scene.spawn("dn_dreamer_mark", up(e.location, 2.6), { state: 1 });
      scene.follow(a, e, 2.6);
      scene.after(10, () => a.state(2));
      marks.set(e.id, { e, a });
      sfx("mark", e.location, 0.6, 0.9 + marks.size * 0.06);
      const top = up(e.location, 2.6);
      fx("moon", top);
      fx("glow", top);
      streak("thread", up(top, 7), top, 4);
      fx("ring", up(groundBelow(dim, e.location), 0.1));
      return;
    }
  }
  function marked() {
    const out = [];
    for (const m of marks.values()) if (isAlive(m.e) && distXZ(m.e.location, center) < DN06.radius + 6) out.push(m.e);
    if (out.length) return out;
    return hostiles(dim, center, DN06.radius, caster);
  }
  function targets(n, spread = 6) {
    const es = marked();
    const out = [];
    for (let i = 0; i < n; i++) {
      if (es.length) {
        const e = es[i % es.length];
        out.push({ loc: groundBelow(dim, e.location), e });
      } else out.push({ loc: clear2(ground(at(center, aim.yaw, i === 0 ? 0 : spread * Math.cos(i * 2.1), 0, i === 0 ? 0 : spread * 0.6 * Math.sin(i * 2.1)))) });
    }
    return out;
  }
  function groups(n) {
    const es = marked();
    const out = [];
    for (const e of es) {
      if (out.length >= n) break;
      const g = clear2(groundBelow(dim, e.location), DN06.clearZone + 0.5);
      if (out.every((c) => distXZ(c, g) > DN06.zoneRadius * 1.6)) out.push(g);
    }
    const base = out.length ? out[0] : center;
    for (let i = out.length; i < n; i++) out.push(clear2(ground(at(base, aim.yaw, (i % 2 ? 1 : -1) * 8, 0, i * 2)), DN06.clearZone + 0.5));
    return out;
  }
  function centroid() {
    const es = marked();
    if (!es.length) return clear2(center);
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return clear2(groundBelow(dim, mul(s, 1 / es.length)));
  }
  function warn(loc, size, slow, life) {
    const t = scene.spawn("telegraph", up(loc, 0.05), { kind: 1, size, state: slow ? TG.warnSlow : TG.warn });
    scene.after(life, () => t.state(TG.flash));
    scene.after(life + 8, () => scene.despawn(t));
    return t;
  }
  function hitOnce(set, loc, r, dmg, after) {
    let n = 0;
    for (const e of hostiles(dim, loc, r, caster)) {
      if (set.has(e.id)) continue;
      set.add(e.id);
      if (damage(e, dmg, caster)) n++;
      after?.(e);
    }
    return n;
  }
  function impact(p, big = false) {
    fx("dust", up(p, 0.3));
    fx(big ? "dwave" : "ring", up(p, 0.15));
    puff("streak", up(p, 0.8), 0.6, big ? 6 : 3);
    if (big) {
      fx("flash", up(p, 1.5));
      fx("dust", up(p, 0.6));
      puff("shardbig", up(p, 1), 1, 4);
    }
  }
  const T23 = 130;
  const T_SIT = T23 + LEN.manifest;
  const T_RISE2 = T_SIT + LEN.sit;
  const T_AWAKE = T_RISE2 + LEN.rise;
  const T_HOV = T_AWAKE + LEN.awaken;
  const T_SWEEP = T_HOV + 4;
  const T_CAB = T_SWEEP + LEN.sweep + 2;
  const T33 = T_CAB + LEN.cabinet;
  const ZONE_FROM = T33 + 48, ZONE_TO = T33 + 208;
  const T43 = ZONE_TO + 2;
  const T_WHEEL = T43 + 14, T_ARMS = T43 + 50, T_DRILL = T43 + 86, T_SWING = T43 + 138, T_ROOMS = T43 + 150;
  const T_FIN = T43 + 200;
  const T_SLAM = T_FIN + LEN.finale;
  const T_PEAK = T_SLAM + 6;
  const T53 = T_SLAM + 24;
  const T_ROOM = T53 + 16, T_CLOSE2 = T53 + 88;
  const T_END4 = T_CLOSE2 + 56;
  const domain = scene.spawn("dn_dreamer_domain", up(center, 0.05), { size: DN06.radius / 2, state: 1 });
  scene.at(32, () => domain.state(2));
  lights.place(up(center, 2), LIGHT);
  lights.place(up(stageG, 3), LIGHT);
  fx("dwave", up(center, 0.15));
  hoop("mote", up(center, 0.4), 6, 12);
  layer(0, 40, (e) => {
    const r = 2 + smooth(e / 39) * DN06.radius;
    for (let i = 0; i < 7; i++) {
      const a = rnd2() * Math.PI * 2;
      fx(i % 3 === 0 ? "sparkle" : "mote", { x: center.x + Math.cos(a) * r, y: center.y + 0.2 + rnd2() * 0.6, z: center.z + Math.sin(a) * r });
    }
  });
  const lamps = [];
  const back = Math.atan2(-fwd.z, -fwd.x) * 180 / Math.PI;
  for (let k2 = 0; k2 < LAMPS; k2++) {
    const a = (back + 22.5 + k2 * 45) * Math.PI / 180;
    const p = ground({ x: center.x + Math.cos(a) * DN06.radius * 0.96, y: center.y, z: center.z + Math.sin(a) * DN06.radius * 0.96 });
    scene.at(8 + k2 * 4, () => {
      const l = scene.spawn("dn_dreamer_lamp", p, { yaw: yawOf(sub(center, p)), state: LAMP.rise });
      lamps.push(l);
      scene.after(20, () => l.state(LAMP.hold));
      fx("glow", up(p, 6));
      fx("ring", up(p, 0.1));
      puff("sparkle", up(p, 5.5), 0.8, 4);
    });
  }
  let codexYaw = aim.yaw;
  const codex = scene.spawn("dn_dreamer_codex", C0, { yaw: codexYaw, state: CODEX.open });
  scene.every(1, () => {
    if (!caster.isValid) return;
    try {
      codexYaw = caster.getRotation().y;
    } catch {
    }
    codex.move(caster.location, codexYaw);
  }, 1, T_END4);
  const bookAt = () => atR(codex.valid ? codex.loc : C0, codexYaw, BOOK2);
  scene.at(60, () => codex.state(CODEX.hold));
  sfx("book", C0, 0.9);
  sfx("musicbox", C0, 0.8);
  scene.at(18, () => puff("paper", bookAt(), 0.4, 8));
  scene.at(28, () => {
    fx("glow", bookAt());
    puff("sparkle", bookAt(), 0.6, 6);
  });
  const bedFrom = rel(18, 26, bedD + 2);
  const bedMid = rel(11, 18, bedD + 1);
  let bedPos = { ...bedFrom };
  const bed = scene.spawn("dn_dreamer_bed", bedFrom, { yaw: faceYaw, state: BED.arrive });
  sfx("bed", bedRest, 1.1);
  scene.span(0, 60, (p) => {
    bedPos = bezier(bedFrom, bedMid, bedRest, easeOut(p));
    bed.move(bedPos, faceYaw);
  });
  hush(60);
  scene.at(60, () => {
    bed.state(BED.float);
    puff("star", up(bedPos, 2), 7, 22);
    puff("glow", up(bedPos, 2), 3, 4);
    fx("flash", up(bedPos, 2));
    hoop("feather", up(bedPos, -2), 6, 10);
    sfx("swell", bedPos, 0.9);
  });
  const pivotAt = () => at(bedPos, faceYaw, 0, PIVOT.up, PIVOT.fwd);
  scene.every(6, () => markNew(), 16, 120);
  scene.every(30, () => markNew(), 120, T53);
  scene.at(100, () => sfx("breath", bedPos, 1));
  layer(0, T43, () => {
    times(9, () => fx("mote", scatter(center, DN06.radius * 0.85, 0.2, 2.8)));
    times(3.5, () => fx("sparkle", scatter(center, 18, 2, 11)));
    times(2.5, () => fx("mote", scatter(C0, 4.5, 0.1, 0.7)));
  });
  layer(40, T43, () => {
    times(2, () => fx("petal", lerp(scatter(bedPos, 6, -4, 2), scatter(C0, 6, 1, 4), rnd2() * 0.85)));
    times(1, () => fx("feather", lerp(scatter(bedPos, 6, -4, 2), scatter(C0, 6, 1, 4), rnd2() * 0.85)));
  });
  layer(0, 60, () => {
    times(5, () => fx("star", scatter(bedPos, 4, -2, 2)));
    times(1.5, () => fx("feather", scatter(bedPos, 4, -3, 0)));
    times(1.5, () => fx("petal", scatter(bedPos, 4, -3, 0)));
  });
  layer(60, T43, () => {
    times(6, () => fx("star", scatter(pivotAt(), 9, -5, 7)));
    times(2, () => fx("petal", scatter(bedPos, 8, -6, 0)));
    times(2, () => fx("feather", scatter(bedPos, 8, -6, 0)));
    times(0.5, () => fx("mist", scatter(bedPos, 7, -8, -4)));
  });
  layer(60, T_RISE2 + 20, () => {
    const top = pivotAt();
    times(5, () => fx("thread", lerp(top, up(center, 1), rnd2())));
  });
  layer(10, T23 + 40, () => {
    times(0.4, () => fx("note", add(bookAt(), { x: (rnd2() - 0.5) * 0.6, y: 0.3 + rnd2() * 0.4, z: (rnd2() - 0.5) * 0.6 })));
    times(1.2, () => fx("paper", scatter(C0, 3.8, 0.2, 1.1)));
    times(0.6, () => fx("sparkle", scatter(bookAt(), 0.6, 0, 0.6)));
  });
  scene.at(T23 - 14, () => {
    const p = pivotAt();
    for (let i = 0; i < 8; i++) fx("column", up(p, -3 + i * 1.6));
    sfx("swell", p, 1.1, 0.9);
  });
  hush(T23 - 2);
  scene.at(T23 - 2, () => {
    const p = pivotAt();
    fx("flash", p);
    hoop("star", p, 9, 26);
    puff("moon", p, 5, 12);
    hoop("glow", p, 6, 6);
  });
  let dreamer = new Actor(void 0, "grimoire:dreamer");
  let dPos = pivotAt();
  let dYaw = faceYaw;
  let doorRel = DOOR3;
  const doorAt = () => atR(dPos, dYaw, doorRel);
  const look = (p) => {
    if (!p) {
      dreamer.prop("look", 0);
      return;
    }
    const d = angleDelta(dYaw, yawOf(sub(p, dPos)));
    dreamer.prop("look", clamp(-d, -60, 60));
  };
  scene.at(T23, () => {
    dPos = pivotAt();
    dreamer = scene.spawn("dreamer", dPos, { yaw: faceYaw, state: DS2.manifest });
    bed.state(BED.occupied);
    sfx("manifest", dPos, 1.3);
    sfx("breath", dPos, 1, 0.8);
  });
  const tiltR = TILT_A * Math.PI / 180;
  const bodyAlong = (f) => {
    const fd = fromYaw(faceYaw), s = -LIE.feet + f * (LIE.feet + LIE.crown);
    return add(pivotAt(), { x: -fd.x * Math.cos(tiltR) * s, y: Math.sin(tiltR) * s, z: -fd.z * Math.cos(tiltR) * s });
  };
  layer(T23, T_SIT, (e) => {
    const f = clamp(e / LEN.manifest, 0, 1);
    times(5, () => fx("porcelain", add(bodyAlong(clamp(f + (rnd2() - 0.5) * 0.14, 0, 1)), { x: rnd2() - 0.5, y: rnd2() * 0.8, z: rnd2() - 0.5 })));
    times(2, () => fx("sparkle", bodyAlong(rnd2() * f)));
    times(1, () => fx("trail", bodyAlong(clamp(f + (rnd2() - 0.5) * 0.1, 0, 1))));
    if (e % 12 === 0) {
      fx("glow", bodyAlong(f));
      sfx("mark", bodyAlong(f), 0.35, 1.4 + f * 0.4);
    }
  });
  const dipAt = (e) => {
    for (let i = 1; i < DIP.length; i++) {
      if (e <= DIP[i][0]) {
        const [t0, v0] = DIP[i - 1], [t1, v1] = DIP[i];
        return v0 + (v1 - v0) * ((e - t0) / (t1 - t0));
      }
    }
    return DIP[DIP.length - 1][1];
  };
  scene.at(T_SIT, () => {
    dreamer.state(DS2.sit);
    bed.state(BED.dip);
    sfx("groan", dPos, 1.3);
    sfx("inhale", dPos, 1.1);
    puff("feather", pivotAt(), 5, 14);
  });
  scene.span(T_SIT, T_RISE2 + 10, (_p, e) => {
    dPos = up(pivotAt(), dipAt(e) * BED_SCALE / 16);
    dreamer.move(dPos, faceYaw);
  });
  layer(T_SIT, T_RISE2, () => {
    times(3, () => fx("feather", scatter(bedPos, 6, -4, 1)));
    times(2, () => fx("porcelain", scatter(dPos, 2.5, 0, 5)));
  });
  const pillowTarget = targets(1)[0];
  let pLand = pillowTarget.loc;
  scene.at(T_SIT + 11, () => {
    pLand = clear2(targets(1)[0].loc, DN06.clearZone - 1);
    const w = warn(pLand, DN06.pillowRadius, true, DN06.warnLong);
    const a = -(TILT_A + 3) * Math.PI / 180;
    const yy = PILLOW.y * Math.cos(-a) + PILLOW.z * Math.sin(-a), zz = -PILLOW.y * Math.sin(-a) + PILLOW.z * Math.cos(-a);
    const from = at(pivotAt(), faceYaw, PILLOW.r * BED_SCALE / 16, yy * BED_SCALE / 16, -zz * BED_SCALE / 16);
    const pil = scene.spawn("dn_dreamer_pillow", from, { yaw: faceYaw, state: 1 });
    const top = up(lerp(from, pLand, 0.3), 5);
    sfx("pillow", from, 0.6, 1.3);
    scene.span(scene.tick, scene.tick + DN06.warnLong, (p) => {
      const tgt = pillowTarget.e && isAlive(pillowTarget.e) && p < 0.7 ? clear2(groundBelow(dim, pillowTarget.e.location), DN06.clearZone - 1) : pLand;
      pLand = tgt;
      w.move(up(tgt, 0.05));
      const pos = bezier(from, top, tgt, easeIn(p) * 0.6 + p * 0.4);
      pil.move(pos);
      fx("feather", pos);
      fx("trail", pos);
    });
    scene.after(DN06.warnLong, () => {
      pil.state(2);
      sfx("pillow", pLand, 1.3);
      impact(pLand, true);
      puff("feather", up(pLand, 1.2), 2.5, 16);
      hitOnce(/* @__PURE__ */ new Set(), pLand, DN06.pillowRadius, DN06.pillowDamage, (e) => knockback(e, pLand, DN06.pillowKnock, 0.45));
      scene.after(14, () => pil.state(3));
      scene.after(32, () => scene.despawn(pil));
    });
  });
  scene.at(T_RISE2, () => {
    dreamer.state(DS2.rise);
    bed.state(BED.empty);
    sfx("groan", dPos, 1.5, 0.85);
    sfx("inhale", dPos, 1.3, 0.8);
    puff("feather", pivotAt(), 6, 16);
  });
  scene.at(T_RISE2 + 60, () => bed.state(BED.rest));
  let riseFrom = dPos;
  scene.at(T_RISE2 + 9, () => {
    riseFrom = { ...dPos };
  });
  scene.span(T_RISE2 + 10, T_RISE2 + 56, (p) => {
    const mid = up(lerp(riseFrom, stage, 0.45), 3.5);
    dPos = bezier(riseFrom, mid, stage, smooth(p));
    dreamer.move(dPos, faceYaw);
    times(4, () => fx("porcelain", scatter(dPos, 3, 0, 9)));
    times(2, () => fx("trail", scatter(dPos, 1.5, 3, 9)));
    times(0.5, () => fx("mist", scatter(dPos, 3, 0, 3)));
    times(2, () => fx("feather", scatter(lerp(riseFrom, dPos, rnd2()), 2, 0, 3)));
  });
  hush(T_RISE2 + 52);
  scene.at(T_RISE2 + 52, () => {
    impact(stageG, true);
    hoop("pool", up(stageG, 0.15), 3, 8);
    hoop("mist", up(stageG, 0.4), 6, 12, 15);
    hoop("dust", up(stageG, 0.3), 5, 8);
    sfx("land", stageG, 1.4);
  });
  scene.at(T_AWAKE - 1, () => {
    dPos = stage;
  });
  scene.at(T_AWAKE, () => {
    dreamer.move(stage, faceYaw).state(DS2.awaken);
    sfx("hum", dPos, 1.3);
    look(centroid());
  });
  scene.at(T_AWAKE + 14, () => {
    sfx("door", doorAt(), 1.3);
    look();
  });
  hush(T_AWAKE + 24);
  scene.at(T_AWAKE + 24, () => {
    const p = doorAt();
    fx("flash", p);
    fx("glow", p);
    fx("column", up(p, 2));
    puff("star", p, 1.6, 14);
    puff("moon", p, 1.3, 6);
    hoop("glow", p, 1.6, 6);
    sfx("swell", p, 0.9, 1.2);
  });
  layer(T_AWAKE + 24, T_FIN, () => {
    times(1.2, () => fx(rnd2() < 0.3 ? "moon" : "star", doorAt()));
    times(0.4, () => fx("sparkle", scatter(doorAt(), 0.8, -0.4, 0.4)));
  });
  scene.at(T_HOV, () => dreamer.state(DS2.hover));
  layer(T_AWAKE, T53, (e) => {
    times(4, () => fx("sparkle", scatter(dPos, 3.5, 1, 11)));
    times(2, () => fx("porcelain", scatter(dPos, 4, 2, 10)));
    times(0.6, () => fx("pool", scatter(stageG, 5, 0.1, 0.2)));
    times(0.5, () => fx("mist", scatter(stageG, 6.5, 0.2, 1.2)));
    const head = atR(dPos, dYaw, DOOR3);
    for (let i = 0; i < 2; i++) {
      const a = e * 0.12 + i * Math.PI;
      fx("trail", { x: head.x + Math.cos(a) * 2.6, y: head.y + 0.6 + Math.sin(e * 0.07 + i) * 0.8, z: head.z + Math.sin(a) * 2.6 });
    }
  });
  const lunge = clamp(distXZ(stage, center) - SWEEP_PATH[2][2], 0, DN06.sweepLunge);
  const sweepBase = () => at(stage, faceYaw, 0, 0, lunge);
  const sweepPt = (i) => atR(sweepBase(), faceYaw, SWEEP_PATH[i]);
  scene.at(T_SWEEP + SWEEP_HIT[0] - DN06.warnLong - 2, () => {
    for (let i = 0; i < SWEEP_PATH.length; i++) warn(clear2(ground(sweepPt(i))), DN06.sweepRadius, true, DN06.warnLong + 4 + i * 3);
    look(ground(sweepPt(0)));
  });
  scene.at(T_SWEEP, () => {
    dreamer.state(DS2.sweep);
    sfx("groan", dPos, 1, 1.1);
  });
  scene.span(T_SWEEP + 6, T_SWEEP + 24, (p) => {
    dPos = lerp(stage, sweepBase(), smooth(p));
    dreamer.move(dPos, faceYaw);
  });
  scene.span(T_SWEEP + 44, T_SWEEP + LEN.sweep, (p) => {
    dPos = lerp(sweepBase(), stage, smooth(p));
    dreamer.move(dPos, faceYaw);
  });
  scene.at(T_SWEEP + 18, () => sfx("sweep", ground(sweepPt(2)), 1.6));
  const swept = /* @__PURE__ */ new Set();
  scene.span(T_SWEEP + SWEEP_HIT[0], T_SWEEP + SWEEP_HIT[1], (p) => {
    const f = p * (SWEEP_PATH.length - 1);
    const i = Math.min(Math.floor(f), SWEEP_PATH.length - 2);
    const hand = ground(lerp(sweepPt(i), sweepPt(i + 1), f - i));
    const along = norm(sub(sweepPt(i + 1), sweepPt(i)));
    look(hand);
    fx("dust", up(hand, 0.3));
    times(3, () => fx("streak", scatter(hand, 1.5, 0.3, 1.5)));
    times(3, () => fx("petal", scatter(hand, 2, 0.5, 2)));
    times(2, () => fx("porcelain", scatter(hand, 1.5, 0.5, 2)));
    if (Math.round(p * 15) % 3 === 0) fx("ring", up(hand, 0.1));
    hitOnce(swept, hand, DN06.sweepRadius, DN06.sweepDamage, (e) => shove(e, along, DN06.sweepKnock, 0.5));
  });
  scene.at(T_SWEEP + LEN.sweep, () => {
    dreamer.state(DS2.hover);
    look();
  });
  let stairDir = mul(fwd, -1);
  let stairFrom = stageG;
  scene.at(T_CAB - 8, () => {
    const t = clear2(targets(1)[0].loc, DN06.clearZone + 2);
    look(t);
    stairDir = norm({ x: t.x - stage.x, y: 0, z: t.z - stage.z });
    stairFrom = ground({ x: t.x - stairDir.x * STEP(9), y: t.y, z: t.z - stairDir.z * STEP(9) });
    for (let k2 = 2; k2 < 10; k2 += 3) warn(ground(add(stairFrom, mul(stairDir, STEP(k2)))), DN06.stairsRadius, false, 18 + STEP_LAND(k2));
  });
  scene.at(T_CAB, () => {
    dreamer.state(DS2.cabinet);
    sfx("door", atR(dPos, dYaw, CHEST), 1.1, 0.7);
  });
  scene.at(T_CAB + 10, () => {
    const chest = atR(dPos, dYaw, CHEST);
    streak("trailbig", chest, up(stairFrom, 4), 12);
    fx("flash", chest);
    puff("glint", chest, 1, 4);
    const st2 = scene.spawn("dn_dreamer_stairs", stairFrom, { yaw: yawOf(stairDir), state: 1 });
    sfx("stairs", stairFrom, 1.3);
    const hit = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < 10; k2++) {
      scene.after(STEP_LAND(k2), () => {
        const p = ground(add(stairFrom, mul(stairDir, STEP(k2))));
        fx("dust", up(p, 0.2));
        puff("streak", up(p, 0.4), 0.4, 2);
        if (k2 % 2 === 0) fx("ring", up(p, 0.1));
        hitOnce(hit, p, DN06.stairsRadius, DN06.stairsDamage, (e) => shove(e, stairDir, 0.8, 0.35));
      });
    }
    scene.after(50, () => st2.state(2));
    scene.after(72, () => scene.despawn(st2));
  });
  layer(T_CAB + 10, T_CAB + 40, () => times(3, () => fx("trail", lerp(atR(dPos, dYaw, CHEST), up(stairFrom, 4), rnd2()))));
  scene.at(T_CAB + LEN.cabinet + 2, () => {
    dreamer.state(DS2.hover);
    look();
  });
  const dreamZones = [];
  const nightZones = [];
  let ward;
  const palm = (p) => atR(dPos, dYaw, p);
  scene.at(T33, () => {
    dreamer.state(DS2.raise).skin(1);
    sfx("raise", up(dPos, 8), 1.5);
    puff("porcelain", up(dPos, 6), 3, 12);
  });
  hush(T33 + 28);
  scene.at(T33 + 28, () => {
    const r = palm(PALM_R), l = palm(PALM_L);
    fx("flash", r);
    fx("flash", l);
    fx("column", up(r, 3));
    fx("column", up(l, 3));
    puff("star", r, 2, 14);
    puff("eye", l, 2, 8);
    puff("ember", l, 2, 10);
    fx("dwave", up(C0, 0.2));
    fx("nwave", up(center, 0.2));
    sfx("swell", up(dPos, 8), 1.2, 0.8);
  });
  scene.at(T33 + 26, () => {
    const spots = [];
    for (const p of allies(dim, C0, 24, caster)) {
      if (p.id === caster.id || spots.length >= 2) continue;
      const loc = groundBelow(dim, p.location);
      spots.push({ loc, kind: distXZ(loc, C0) < DN06.clearZone ? 3 : spots.length });
    }
    const flank = (s) => ground(rel(
      s * Math.sin(DN06.dreamFlankAngle * Math.PI / 180) * DN06.dreamFlank,
      0,
      Math.cos(DN06.dreamFlankAngle * Math.PI / 180) * DN06.dreamFlank
    ));
    if (spots.length < 3) spots.push({ loc: flank(-1), kind: 2 });
    if (spots.length < 3) spots.push({ loc: flank(1), kind: 0 });
    if (spots.length < 3) spots.push({ loc: ground(rel(0, 0, -DN06.dreamFlank)), kind: 1 });
    const hand = palm(PALM_R);
    const sanct = scene.spawn("dn_dreamer_sanctum", groundBelow(dim, C0), { yaw: aim.yaw, state: ZONE.bloom });
    dreamZones.push({ a: sanct, loc: groundBelow(dim, C0), kind: 3 });
    scene.after(30, () => sanct.state(ZONE.idle));
    hoop("petal", up(C0, 0.6), DN06.zoneRadius, 10);
    spots.forEach((s, i) => {
      const a = s.kind === 3 ? scene.spawn("dn_dreamer_sanctum", s.loc, { yaw: aim.yaw, state: ZONE.bloom }) : scene.spawn("dn_dreamer_dream", s.loc, { kind: s.kind, yaw: yawOf(sub(C0, s.loc)), state: ZONE.bloom });
      dreamZones.push({ a, loc: s.loc, kind: s.kind });
      streak("trailbig", hand, up(s.loc, 3), 12);
      hoop("petal", up(s.loc, 1), DN06.zoneRadius, 8, i * 30);
      fx("dwave", up(s.loc, 0.15));
      fx("column", up(s.loc, 4));
      if (s.kind !== 3) lights.place(up(s.loc, 2), LIGHT);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sfx("bloom", C0, 1);
    ward = addWard({
      scene,
      factor: DN06.wardFactor,
      pool: DN06.wardPool,
      protects: (e) => e.typeId === "minecraft:player" && dreamZones.some((z) => distXZ(z.loc, e.location) <= DN06.zoneRadius),
      onAbsorb: (_n, _a, v2) => {
        fx("ring", up(v2.location, 0.2));
        fx("glow", up(v2.location, 1));
      }
    });
  });
  scene.at(T33 + 34, () => {
    const hand = palm(PALM_L);
    const lat = (p) => Math.abs((p.x - C0.x) * rt.x + (p.z - C0.z) * rt.z);
    const gs = groups(3).sort((a, b) => lat(b) - lat(a));
    gs.forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_night", loc, { kind: i, yaw: yawOf(sub(C0, loc)), state: ZONE.bloom });
      nightZones.push({ a, loc, kind: i });
      streak("ntrail", hand, up(loc, 3), 12);
      fx("nwave", up(loc, 0.15));
      puff("nmist", up(loc, 1), 2.5, 4);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sfx("emerge", nightZones.length ? nightZones[0].loc : center, 1.3);
    look(centroid());
  });
  scene.at(T33 + LEN.raise, () => dreamer.state(DS2.conjure));
  layer(T33 + 30, T43 + 20, () => {
    for (const z of dreamZones) {
      times(z.kind === 3 ? 2 : 2.5, () => fx("bloom", scatter(z.loc, 3.8, 0.2, z.kind === 3 ? 0.8 : 2.8)));
      times(0.6, () => fx(z.kind === 3 ? "mote" : "key", scatter(z.loc, 3, 0.4, z.kind === 3 ? 1 : 3.5)));
    }
  });
  layer(T33 + 38, T43 + 20, () => {
    for (const z of nightZones) {
      times(2.5, () => fx("ember", scatter(z.loc, 3.8, 0.2, 2.4)));
      times(0.6, () => fx("nmist", scatter(z.loc, 3.6, 0.2, 1)));
      times(0.3, () => fx("eye", scatter(z.loc, 3, 1, 3.5)));
    }
  });
  layer(T33 + 30, T43, (e) => {
    const r = palm(PALM_R), l = palm(PALM_L);
    dreamZones.forEach((z, i) => fx("trail", lerp(r, up(z.loc, z.kind === 3 ? 1.5 : 3), (e * 0.045 + i * 0.37) % 1)));
    nightZones.forEach((z, i) => fx("ntrail", lerp(l, up(z.loc, 3), (e * 0.045 + i * 0.29) % 1)));
    dreamZones.forEach((z, i) => fx("sparkle", lerp(r, up(z.loc, z.kind === 3 ? 1.5 : 3), (e * 0.045 + i * 0.37 + 0.5) % 1)));
    nightZones.forEach((z, i) => fx("ember", lerp(l, up(z.loc, 3), (e * 0.045 + i * 0.29 + 0.5) % 1)));
    times(0.5, () => fx("glow", r));
    times(0.5, () => fx("nglow", l));
  });
  scene.every(DN06.zonePulse, (e) => {
    const k2 = e / DN06.zonePulse;
    for (const z of dreamZones) {
      fx("heal", up(z.loc, 0.5));
      if (k2 % 2 === 0) {
        fx("ring", up(z.loc, 0.15));
        fx("column", up(z.loc, 4));
      }
      for (const p of allies(dim, z.loc, DN06.zoneRadius, caster)) {
        if (heal(p, DN06.dreamHeal) > 0) {
          sfx("heal", p.location, 0.5, 1 + z.kind * 0.1);
          fx("heal", up(p.location, 1));
        }
        if (z.kind === 0 || z.kind === 3) effect(p, "regeneration", DN06.dreamEffectTicks, 0);
        if (z.kind === 1 || z.kind === 3) {
          effect(p, "resistance", DN06.dreamEffectTicks, 0);
          effect(p, "slow_falling", DN06.dreamEffectTicks, 0);
        }
        if (z.kind === 2) {
          effect(p, "speed", DN06.dreamEffectTicks, 1);
          effect(p, "jump_boost", DN06.dreamEffectTicks, 0);
        }
      }
    }
    if (k2 % 2 === 0 && dreamZones.length) sfx("sweet", dreamZones[0].loc, 0.75);
  }, ZONE_FROM, ZONE_TO);
  scene.every(DN06.zonePulse, (e) => {
    const big = e / DN06.zonePulse % 2 === 1;
    for (const z of nightZones) {
      fx(big ? "eye" : "nring", up(z.loc, big ? 2 : 0.2));
      if (big) {
        z.a.state(ZONE.bite);
        scene.after(14, () => z.a.state(ZONE.idle));
        sfx("bite", z.loc, 0.9);
        fx("nwave", up(z.loc, 0.15));
        puff("ember", up(z.loc, 1.5), 2, 8);
      }
      for (const e2 of hostiles(dim, z.loc, DN06.zoneRadius, caster)) {
        damage(e2, big ? DN06.biteDamage : DN06.nightDamage, caster);
        effect(e2, "slowness", DN06.zonePulse + 10, DN06.nightSlowAmp);
        effect(e2, "weakness", DN06.zonePulse * 2, 1);
        if (!big) continue;
        if (z.kind === 0) {
          effect(e2, "levitation", DN06.roomLift, 1);
          try {
            const r = e2.getRotation();
            e2.setRotation({ x: r.x, y: r.y + 180 });
          } catch {
          }
        } else if (z.kind === 1) {
          restrain(scene, e2, DN06.corridorHold, up(z.loc, 0.1));
        } else {
          knockback(e2, z.loc, 1.4, 0.4);
        }
      }
    }
    if (!big && nightZones.length) sfx("sour", nightZones[0].loc, 0.75);
  }, ZONE_FROM + DN06.zonePulse / 2, ZONE_TO);
  let pivot = up(center, DN06.pendulumLength + 3.5);
  const swingAxis = rt;
  const swingPos = (deg) => {
    const r = deg * Math.PI / 180;
    return add(pivot, { x: swingAxis.x * DN06.pendulumLength * Math.sin(r), y: -DN06.pendulumLength * Math.cos(r), z: swingAxis.z * DN06.pendulumLength * Math.sin(r) });
  };
  let bedFold = bedPos;
  scene.at(T43 - 1, () => {
    const c = centroid();
    const d = Math.max(distXZ(c, C0), DN06.clearZone + 4);
    const dir = norm({ x: c.x - C0.x, y: 0, z: c.z - C0.z });
    pivot = { x: C0.x + dir.x * d, y: Math.max(c.y, g0) + DN06.pendulumLength + 3.5, z: C0.z + dir.z * d };
    bedFold = { ...bedPos };
  });
  hush(T43);
  scene.at(T43, () => {
    dreamer.state(DS2.conduct);
    domain.skin(1);
    for (const l of lamps) l.skin(1);
    for (const m of marks.values()) m.a.skin(1);
    sfx("unreality", up(dPos, 8), 1.7);
    if (ward) removeWard(ward);
    dreamZones.concat(nightZones).forEach((z, i) => {
      const dreamy = dreamZones.includes(z);
      scene.after(i * 3, () => {
        z.a.state(ZONE.fold);
        puff(dreamy ? "bloom" : "ember", up(z.loc, 2), 2.5, 8);
        fx(dreamy ? "dwave" : "nwave", up(z.loc, 0.15));
      });
      const a = z.a;
      scene.after(i * 3 + 26, () => scene.despawn(a));
    });
    for (const z of dreamZones) if (z.kind !== 3) lights.remove(up(z.loc, 2));
    bed.state(BED.fold);
    fx("nwave", up(center, 0.2));
    fx("shock", up(center, 0.25));
    fx("flash", up(dPos, 6));
    hoop("nmist", up(center, 0.5), 10, 14);
    hoop("glyph", up(center, 2), 8, 12);
  });
  layer(T43, T_SLAM + 10, () => {
    times(5, () => fx("glyph", scatter(center, 16, 1, 10)));
    times(8, () => fx("ember", scatter(center, DN06.radius * 0.85, 0.2, 2.2)));
    times(0.7, () => fx("nmist", scatter(center, DN06.radius * 0.8, 0.2, 1)));
    times(4, () => fx("ember", scatter(dPos, 4, 1, 11)));
    times(3, () => fx("sparkle", scatter(center, 18, 3, 12)));
    times(2, () => fx("porcelain", scatter(center, DN06.radius * 0.7, 0.2, 1.5)));
    times(1, () => fx("mote", scatter(C0, 4.5, 0.1, 0.7)));
  });
  scene.span(T43, T_SWING - 4, (p) => {
    const tgt = swingPos(SWING_A);
    bedPos = bezier(bedFold, up(lerp(bedFold, tgt, 0.5), 8), tgt, smooth(p));
    bed.move(bedPos, faceYaw);
    times(2, () => fx("feather", scatter(bedPos, 3, -2, 1)));
  });
  scene.at(T_WHEEL, () => {
    const ts = targets(3).map((t) => clear2(t.loc, DN06.clearZone + 1.5));
    const lat = (p) => (p.x - C0.x) * rt.x + (p.z - C0.z) * rt.z;
    ts.sort((a, b) => lat(b) - lat(a));
    const depth = ts.reduce((s, p) => s + distXZ(p, C0), 0) / Math.max(1, ts.length);
    const start = clear2(ground(rel(14, 0, depth)), DN06.clearZone + 1.5);
    const end = clear2(ground(rel(-14, 0, depth + 2)), DN06.clearZone + 1.5);
    const pts = [start, ...ts, end];
    let len2 = 0;
    for (let i = 1; i < pts.length; i++) len2 += distXZ(pts[i - 1], pts[i]);
    const dur = Math.round(clamp(len2 / DN06.wheelSpeed, 40, 90));
    const w = scene.spawn("dn_dreamer_wheel", start, { yaw: yawOf(sub(pts[1], start)), state: 1 });
    for (let i = 1; i < pts.length - 1; i++) warn(pts[i], DN06.wheelRadius, false, 20 + Math.round(dur * i / pts.length));
    puff("glyph", up(start, 3), 3, 12);
    fx("flash", up(start, 3));
    const hit = /* @__PURE__ */ new Set();
    scene.after(20, () => {
      w.state(2);
      sfx("wheel", start, 1.5);
    });
    let prev = start;
    scene.span(scene.tick + 20, scene.tick + 20 + dur, (p) => {
      const pos = ground(spline(pts, smooth(p) * 0.3 + p * 0.7));
      const dir = sub(pos, prev);
      w.move(pos, Math.abs(dir.x) + Math.abs(dir.z) > 1e-3 ? yawOf(dir) : void 0);
      prev = pos;
      fx("dust", up(pos, 0.3));
      times(2, () => fx("door", scatter(pos, 1.5, 1.5, 5)));
      times(2, () => fx("streak", scatter(pos, 2, 0.3, 1.5)));
      if (Math.round(p * dur) % 4 === 0) fx("ring", up(pos, 0.1));
      look(pos);
      hitOnce(hit, pos, DN06.wheelRadius, DN06.wheelDamage, (e) => shove(e, dir, 1.6, 0.6));
    });
    scene.after(20 + dur, () => {
      w.state(3);
      puff("door", up(prev, 3), 2.5, 10);
      impact(prev, true);
    });
    scene.after(40 + dur, () => scene.despawn(w));
  });
  scene.at(T_ARMS - 6, () => {
    const ts = targets(DN06.shards, 5);
    ts.forEach((t) => warn(t.loc, 1.6, false, 25));
    look(centroid());
    scene.at(T_ARMS, () => dreamer.state(DS2.fireArms));
    scene.at(T_ARMS + 13, () => {
      sfx("glass", up(dPos, 6), 1.4);
      ts.forEach((t, i) => {
        const from = atR(dPos, dYaw, [i % 2 ? -ARM[0] : ARM[0], ARM[1], ARM[2]]);
        fx("glint", from);
        fx("glow", from);
        const s = scene.spawn("dn_dreamer_shard", from, { yaw: yawOf(sub(t.loc, from)), state: 1 });
        const mid = up(lerp(from, t.loc, 0.5), 3);
        scene.span(scene.tick, scene.tick + 12, (p) => {
          const tg = t.e && isAlive(t.e) ? groundBelow(dim, t.e.location) : t.loc;
          const pos = bezier(from, mid, up(tg, 0.8), p);
          s.move(pos);
          fx("glint", pos);
          fx("trail", pos);
          if (p > 0.95) t.loc = tg;
        });
        scene.after(12, () => {
          s.state(2);
          fx("glint", up(t.loc, 1));
          puff("shardbig", up(t.loc, 1), 0.6, 4);
          fx("ring", up(t.loc, 0.1));
          for (const e of hostiles(dim, t.loc, 1.8, caster)) damage(e, DN06.shardDamage, caster);
          if (i === 0) sfx("glass", t.loc, 1.2, 1.15);
        });
        scene.after(22, () => scene.despawn(s));
      });
    });
    scene.at(T_ARMS + LEN.fireArms, () => dreamer.state(DS2.conduct));
  });
  scene.at(T_DRILL, () => {
    const tgt = groups(1)[0];
    warn(tgt, DN06.drillRadius, true, DN06.warnLong);
    look(tgt);
    const top = up(tgt, 9);
    const d = scene.spawn("dn_dreamer_drill", up(top, 4), { yaw: faceYaw, state: 1 });
    streak("trailbig", up(dPos, 10), up(top, 6), 12);
    scene.span(scene.tick, scene.tick + 20, (p) => d.move(lerp(up(top, 4), top, easeOut(p))));
    scene.after(20, () => {
      d.state(3);
      sfx("drill", tgt, 1.5);
    });
    scene.span(scene.tick + 20, scene.tick + DN06.warnLong, (p) => {
      const pos = lerp(top, tgt, easeIn(p));
      d.move(pos);
      const a = scene.tick * 37 % 360;
      times(2, () => fx("streak", add(pos, { x: Math.cos(a * Math.PI / 180) * 2.2, y: 2 + rnd2() * 4, z: Math.sin(a * Math.PI / 180) * 2.2 })));
      times(2, () => fx("sparkle", scatter(pos, 2, 0, 6)));
    });
    scene.after(DN06.warnLong, () => {
      impact(tgt, true);
      fx("shock", up(tgt, 0.2));
      for (const e of hostiles(dim, tgt, DN06.drillRadius, caster)) {
        damage(e, DN06.drillDamage, caster);
        effect(e, "slowness", 40, 3);
      }
    });
    scene.every(10, () => {
      for (const e of hostiles(dim, tgt, DN06.drillRadius, caster)) {
        damage(e, DN06.drillTick, caster);
        drag(e, lerp(e.location, up(tgt, 0.1), 0.3));
      }
      fx("porcelain", up(tgt, 1));
      fx("dust", up(tgt, 0.3));
    }, scene.tick + DN06.warnLong + 10, scene.tick + DN06.warnLong + 31);
    scene.span(scene.tick + DN06.warnLong, scene.tick + DN06.warnLong + 30, (p) => {
      d.move(up(tgt, -2.5 * p));
      times(2, () => fx("dust", scatter(tgt, 2, 0.2, 0.6)));
    });
    scene.after(DN06.warnLong + 30, () => d.state(4));
    scene.after(DN06.warnLong + 46, () => scene.despawn(d));
  });
  scene.at(T_SWING - DN06.warnLong, () => {
    for (const a of [-30, -10, 10, 30]) warn(clear2(ground(swingPos(a))), 3, true, DN06.warnLong + 10);
  });
  const swung = /* @__PURE__ */ new Set();
  scene.at(T_SWING, () => {
    bed.state(BED.swing);
    sfx("pendulum", pivot, 1.7);
    look(swingPos(0));
  });
  scene.span(T_SWING, T_SWING + SWING_T, (p) => {
    const th = SWING_A * Math.cos(Math.PI * p);
    bedPos = swingPos(th);
    bed.move(bedPos, faceYaw);
    times(2, () => fx("feather", scatter(bedPos, 2, -1, 1)));
    if (Math.abs(th) < 28) {
      const g = ground(bedPos);
      fx("petal", up(g, 1));
      fx("dust", up(g, 0.3));
      times(2, () => fx("streak", scatter(bedPos, 2, -1, 1)));
      hitOnce(swung, g, DN06.pendulumRadius, DN06.pendulumDamage, (e) => shove(e, mul(swingAxis, -1), 2, 0.7));
    }
  });
  scene.at(T_SWING + SWING_T, () => bed.state(BED.hang));
  scene.span(T_SWING + SWING_T, T53, (p) => {
    bedPos = lerp(swingPos(-SWING_A), up(lerp(swingPos(-SWING_A), bedRest, 0.6), 2), smooth(p));
    bed.move(bedPos, faceYaw);
  });
  scene.at(T_ROOMS, () => {
    dreamer.state(DS2.fireRooms);
    sfx("door", atR(dPos, dYaw, CHEST), 1.2, 0.6);
    look(centroid());
  });
  scene.at(T_ROOMS + 12, () => {
    const from = atR(dPos, dYaw, CHEST);
    fx("flash", from);
    targets(DN06.rooms, 6).forEach((t, i) => {
      const r = scene.spawn("dn_dreamer_roomcube", from, { yaw: faceYaw + i * 40, state: 1 });
      const top = up(lerp(from, t.loc, 0.5), 5);
      scene.span(scene.tick, scene.tick + 16, (p) => {
        if (t.e && isAlive(t.e) && p < 0.8) t.loc = clear2(groundBelow(dim, t.e.location), DN06.clearZone - 1);
        const pos = bezier(from, top, t.loc, p);
        r.move(pos);
        fx("trailbig", pos);
        fx("sparkle", scatter(pos, 1, 0, 1));
      });
      scene.after(16, () => {
        r.state(2);
        sfx("room", t.loc, 1.1);
        impact(t.loc);
        for (const e of hostiles(dim, t.loc, DN06.roomRadius, caster)) restrain(scene, e, DN06.roomHold, { ...e.location });
      });
      scene.after(32, () => {
        r.state(3);
        impact(t.loc, true);
        for (const e of hostiles(dim, t.loc, DN06.roomRadius + 0.5, caster)) damage(e, DN06.roomDamage, caster);
      });
      scene.after(42, () => r.state(4));
      scene.after(58, () => scene.despawn(r));
    });
  });
  scene.at(T_ROOMS + LEN.fireRooms, () => dreamer.state(DS2.conduct));
  let land = ground(at(stage, faceYaw, 0, 0, BEAM_LAND));
  let finFrom = stage, finTo = stage;
  scene.at(T_FIN - 25, () => {
    const c = centroid();
    const want = yawOf(sub(c, stage));
    dYaw = faceYaw + clamp(angleDelta(faceYaw, want), -DN06.finaleTurn, DN06.finaleTurn);
    const adv = clamp(distXZ(stage, c) - BEAM_LAND, 0, DN06.finaleAdvance);
    finFrom = { ...dPos };
    finTo = at(stage, dYaw, 0, 0, adv);
    finTo = { x: finTo.x, y: ground(finTo).y + HOVER_LIFT, z: finTo.z };
    dYaw = faceYaw;
  });
  scene.span(T_FIN - 24, T_FIN, (p) => {
    const c = centroid();
    const want = yawOf(sub(c, stage));
    const yaw = faceYaw + clamp(angleDelta(faceYaw, want), -DN06.finaleTurn, DN06.finaleTurn) * smooth(p);
    dYaw = yaw;
    dPos = lerp(finFrom, finTo, smooth(p));
    dreamer.move(dPos, dYaw);
    look();
  });
  scene.at(T_FIN - 24, () => sfx("riser", up(dPos, 8), 1.6));
  layer(T_FIN - 24, T_FIN + 22, (e) => {
    times(3 + e / 9, () => fx("gather", doorAt()));
    fx("glow", doorAt());
    times(1, () => fx("gather", atR(dPos, dYaw, PALM_R)));
    times(1, () => fx("sparkle", scatter(dPos, 6, 2, 12)));
  });
  scene.at(T_FIN, () => {
    doorRel = DOOR_FIN;
    land = clear2(ground(at(dPos, dYaw, 0, 0, BEAM_LAND)), DN06.clearZone + 1);
    dreamer.state(DS2.finale);
    warn(land, DN06.beamRadius, true, LEN.finale + 5);
  });
  scene.at(T_FIN + 8, () => sfx("beam", land, 1.8));
  scene.at(T_FIN + 20, () => {
    fx("flash", doorAt());
    fx("dwave", up(land, 0.2));
    puff("moon", up(land, 2), 3, 12);
  });
  layer(T_FIN + 22, T_SLAM, (e) => {
    const a = doorAt();
    times(5, () => fx("beam", lerp(a, up(land, 1), rnd2())));
    times(2, () => fx("star", lerp(a, up(land, 1), rnd2())));
    const ang = e * 0.35;
    for (let i = 0; i < 4; i++) {
      const rr = DN06.beamRadius * (0.3 + 0.6 * rnd2());
      fx(i % 2 === 0 ? "moon" : "star", { x: land.x + Math.cos(ang + i * 1.57) * rr, y: land.y + 0.5 + rnd2() * 2, z: land.z + Math.sin(ang + i * 1.57) * rr });
    }
    if (e % 8 === 0) fx("dwave", up(land, 0.15));
    if (e % 4 === 0) fx("column", up(land, 5));
  });
  scene.every(4, (e) => {
    for (const x of hostiles(dim, land, DN06.beamRadius, caster)) {
      const d = distXZ(x.location, land);
      if (d > 1.2) {
        const step = mul(norm({ x: land.x - x.location.x, y: 0, z: land.z - x.location.z }), Math.min(DN06.beamPull * 4, d - 1));
        drag(x, add(x.location, step));
      }
      if (e % 12 === 0) damage(x, DN06.beamDamage, caster);
    }
  }, T_FIN + 22, T_SLAM);
  scene.at(T_SLAM, () => {
    dreamer.state(DS2.slam);
    sfx("door", doorAt(), 1.4, 0.55);
  });
  hush(T_PEAK);
  scene.at(T_PEAK, () => {
    sfx("final", land, 2);
    sfx("final", C0, 0.7, 0.8);
    fx("flash", up(land, 2));
    fx("flash", doorAt());
    particle(dim, "fx_flash", up(land, 2));
    fx("shock", up(land, 0.2));
    fx("dwave", up(land, 0.25));
    fx("nwave", up(land, 0.3));
    puff("shardbig", up(land, 2), 3, 14);
    puff("moon", up(land, 2.5), 4, 12);
    puff("streak", up(land, 1), 1.5, 12);
    hoop("dust", up(land, 0.3), 4, 10);
    hoop("star", up(land, 0.5), DN06.finalRadius, 16);
    for (const s of [-1, 1]) impact(atR(dPos, dYaw, [s * HAND_SLAM[0], 0, HAND_SLAM[2]]), true);
    for (const e of hostiles(dim, land, DN06.finalRadius, caster)) {
      damage(e, DN06.finalDamage, caster);
      knockback(e, land, DN06.finalKnock, 0.6);
    }
  });
  scene.at(T_PEAK + 4, () => {
    fx("shock", up(land, 0.2));
    hoop("ring", up(land, 0.15), DN06.finalRadius * 0.6, 8);
  });
  scene.at(T_PEAK + 9, () => {
    fx("dwave", up(land, 0.2));
    hoop("mist", up(land, 0.5), 6, 12);
  });
  layer(T_PEAK + 1, T53 + 40, (e) => {
    times(e < 20 ? 6 : 3, () => fx("shardbig", scatter(land, 7, 2, 10)));
    times(2, () => fx("star", scatter(land, 9, 0.5, 6)));
    times(0.5, () => fx("mist", scatter(land, 7, 0.2, 1.2)));
    times(e < 20 ? 3 : 1, () => fx("dust", scatter(land, 6, 0.2, 0.6)));
  });
  scene.at(T53, () => {
    dreamer.state(DS2.forget).skin(0);
    dreamer.prop("look", 0);
    sfx("break", up(dPos, 8), 1.6);
    sfx("after", C0, 1);
    bed.state(BED.vanish);
    puff("feather", bedPos, 4, 16);
    let i = 0;
    for (const m of marks.values()) {
      const a = m.a;
      scene.after(i * 3, () => a.state(3));
      scene.after(i * 3 + 9, () => scene.despawn(a));
      i++;
    }
  });
  layer(T53, T53 + 52, () => {
    times(3, () => fx("feather", scatter(bedPos, 3, -1, 1)));
    times(2, () => fx("star", scatter(bedPos, 3, -1, 2)));
  });
  layer(T53, T53 + 100, (e) => {
    times(e < 50 ? 5 : 2, () => fx("shardbig", scatter(dPos, 5, 2, 12)));
    times(1.5, () => fx("porcelain", scatter(dPos, 4, 4, 12)));
    times(2, () => fx("sparkle", scatter(dPos, 6, 1, 12)));
  });
  layer(T53, T_END4, (e) => {
    times(e < 60 ? 10 : e < 100 ? 6 : 3, () => fx("morning", scatter(lerp(C0, center, 0.6), 13, 0.2, 2.8)));
    times(e < 80 ? 2 : 1, () => fx("sparkle", scatter(lerp(C0, center, 0.5), 12, 1, 8)));
    times(e < 60 ? 1.5 : 0.5, () => fx("petal", scatter(lerp(C0, center, 0.5), 10, 2, 6)));
  });
  scene.at(T53 + 52, () => scene.despawn(bed));
  scene.at(T53 + 10, () => {
    domain.state(3);
    codex.state(CODEX.gather);
  });
  scene.at(T53 + 42, () => scene.despawn(domain));
  scene.at(T53 + 14, () => {
    lamps.forEach((l, k2) => {
      scene.after(k2 * 4, () => {
        l.state(LAMP.sink);
        fx("glow", up(l.loc, 6));
      });
      scene.after(k2 * 4 + 22, () => scene.despawn(l));
    });
  });
  scene.at(T53 + 24, () => sfx("morning", C0, 1));
  scene.at(T_ROOM, () => {
    const from = atR(dPos, dYaw, CHEST);
    const room = scene.spawn("dn_dreamer_bedroom", from, { yaw: faceYaw, size: 5, state: 1 });
    fx("flash", from);
    puff("star", from, 3, 12);
    scene.after(16, () => room.state(2));
    const fromSize = 5;
    scene.span(scene.tick + 18, T_CLOSE2 - 2, (p) => {
      const b = bookAt();
      const mid = add(up(lerp(from, b, 0.55), 7), mul(rt, -4));
      const e = smooth(p);
      room.move(bezier(from, mid, up(b, 0.35), e)).size(fromSize + (0.3 - fromSize) * Math.min(1, e * 1.25));
      times(2, () => fx("trail", room.loc));
      times(1, () => fx("morning", room.loc));
    });
    scene.at(T_CLOSE2 - 2, () => room.state(3));
    scene.at(T_CLOSE2 + 16, () => scene.despawn(room));
  });
  scene.at(T53 + LEN.forget, () => scene.despawn(dreamer));
  scene.at(T_CLOSE2, () => {
    codex.state(CODEX.close);
    const b = bookAt();
    fx("glow", b);
    puff("sparkle", b, 0.5, 8);
  });
  scene.at(T_CLOSE2 + 22, () => {
    sfx("click", bookAt(), 0.8);
    fx("star", bookAt());
  });
  scene.at(T_CLOSE2 + 40, () => puff("morning", bookAt(), 0.6, 6));
  scene.endAt(T_END4);
});

// src/config/ed01.ts
var ED01 = {
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  focusSnap: 12,
  /** Heading of the walk relative to the caster: mostly across the view (profile), slightly away. */
  walkAcross: 0.8,
  walkAway: 0.6,
  /** Degrees the dragon's heading curves over its walk (the "short arc"). */
  walkTurnDeg: 20,
  // ---- Stage I: Awakening of the Living Earth
  /** Damage and radius when the emerging body lands its forefeet. */
  landDamage: 6,
  landRadius: 5,
  /** Geological shockwave of every footfall: damage, radius, horizontal / vertical knockback. */
  stepDamage: 3,
  stepRadius: 3.4,
  stepKnockH: 0.7,
  stepKnockV: 0.35,
  /** Size (grimoire:size) of the footfall fissure decal (radius = 2 * size blocks). */
  stepQuakeSize: 1.5,
  // ---- Stage II: The Forest Upon Its Back
  /** Radius around the focus in which roots seek enemies, and how many they take. */
  rootRadius: 14,
  maxRoots: 6,
  /** Decorative roots sent toward the focus when nobody is there. */
  idleRoots: 4,
  /** Root size range (size 1 = 6 blocks long). */
  rootMinSize: 0.45,
  rootMaxSize: 2.6,
  /** Enemies clustered within this distance share one pillar ring; maximum rings. */
  groupRadius: 5,
  maxRings: 2,
  /** Pillars per ring, ring radius limits (blocks) and barrier height of each pillar. */
  pillarsPerRing: 5,
  ringMin: 4,
  ringMax: 7,
  pillarBarrierHeight: 4,
  pillarSize: 0.95,
  // ---- Stage III: Continental Descent
  /** Forelimb slam: radius (also the telegraph), damage, knockback (a jolt; the roots still hold). */
  slamRadius: 7,
  slamDamage: 12,
  slamKnockH: 0.4,
  slamKnockV: 0.55,
  /** Strata structures erupting: damage and radius per structure. */
  strataDamage: 8,
  strataRadius: 4,
  /** Each root tearing out of the ground: damage around its grip and upward throw. */
  rootDamage: 8,
  rootEruptRadius: 2.6,
  rootKnockV: 0.9,
  /** Each toppling pillar crushes enemies within this width of its fall line. */
  pillarDamage: 6,
  pillarWidth: 2.2,
  /** Ring convergence: the finishing blow at each ring centre, with strong knockback. */
  convergeDamage: 9,
  convergeKnockH: 2.4,
  convergeKnockV: 0.8
};

// src/spells/ed01_genesis_colossus.ts
var N = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10, depart: 11 };
var ACTOR3 = "dragon_nature";
var SCALE = 2;
var WALK_SPEED = 1.5;
var WALK_CYCLE = 64;
var STEPS = [
  { t: 0, x: -3, z: -1.9 },
  { t: 16, x: -3, z: 5.5 },
  { t: 32, x: 3, z: -1.9 },
  { t: 48, x: 3, z: 5.5 }
];
var ARRIVE_LAND = 50;
var ATTACK_A_HIT = 44;
var DEPART_PETRIFY = 14;
var DEPART_LEN = 56;
var SLAM_OFS = { x: 3, z: 4.5 };
var SKIN = { normal: 0, bloom: 1, stone: 2 };
var STRATA = { hidden: 0, rise: 1, hold: 2, part: 3, erupt: 4, crumble: 5 };
var PILLAR = { hidden: 0, rise: 1, hold: 2, erupt: 3, crumble: 4 };
var PILLAR_IMPACT = 12;
var ROOT = { hidden: 0, grow: 1, hold: 2, erupt: 3, wither: 4 };
var ROOT_LEN = 6;
var ROOT_BIND = 21;
var T_ARRIVE = 8;
var T_WALK = 72;
var T_POWER = T_WALK + WALK_CYCLE;
var T_ROOTS = T_POWER + 10;
var T_PILLARS = T_POWER + 28;
var T_ATTACK = T_POWER + 48;
var T_HIT = T_ATTACK + ATTACK_A_HIT;
var T_DEPART = T_HIT + 22;
var T_END2 = T_DEPART + DEPART_LEN + 4;
function local(p, yaw, x, z) {
  const f = fromYaw(yaw);
  return add(add(p, mul(f, z)), mul(right(f), x));
}
var ed01_genesis_colossus_default = defineSpell("ed01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, ED01.focusSnap);
  const fwd = aim.forward;
  const fe = norm(add(mul(right(fwd), ED01.walkAcross), mul(fwd, ED01.walkAway)));
  const yawEnd = yawOf(fe);
  const yawStart = yawEnd + ED01.walkTurnDeg;
  const slamAt = { ...center };
  const pEnd = up(local(center, yawEnd, -SLAM_OFS.x, -SLAM_OFS.z), 0);
  pEnd.y = center.y;
  const step = WALK_SPEED / 20;
  const path = new Array(WALK_CYCLE + 1);
  const yaws = new Array(WALK_CYCLE + 1);
  path[WALK_CYCLE] = pEnd;
  yaws[WALK_CYCLE] = yawEnd;
  for (let i = WALK_CYCLE; i > 0; i--) {
    const h = yawStart + (yawEnd - yawStart) * ((i - 0.5) / WALK_CYCLE);
    path[i - 1] = sub(path[i], mul(fromYaw(h), step));
    yaws[i - 1] = yawStart + (yawEnd - yawStart) * ((i - 1) / WALK_CYCLE);
  }
  const pStart = path[0];
  const tb = blocksFor(scene);
  const footprints = [];
  const sigil = scene.spawn("telegraph", up(pStart, 0.05), { kind: 2, size: 9, state: 1 });
  scene.at(20, () => sigil.state(2));
  scene.at(T_ARRIVE + 52, () => sigil.state(3));
  scene.at(T_ARRIVE + 60, () => scene.despawn(sigil));
  sound(dim, "ed_nature_rumble", pStart, 1.6);
  const strataSpots = [[0, 9, 1.8], [5, 3, 1.6], [-5, 3, 1.6], [5.5, -6, 1.5], [-5.5, -6, 1.5]];
  const strata = [];
  strataSpots.forEach(([x, z, size], k2) => {
    scene.at(k2 * 3, () => {
      const at = groundBelow(dim, up(local(pStart, yawStart, x, z), 3));
      const a = scene.spawn("ed_nature_strata", at, { yaw: yawOf(sub(at, pStart)) + k2 * 37, size, state: STRATA.rise });
      strata.push({ a, at, size });
      burst(dim, "ed_nature_dust", up(at, 1), 2.5, 3);
      particle(dim, "ed_nature_rise", at);
      if (k2 % 2 === 0) sound(dim, "ed_nature_strata", at, 1.2, 0.9 + k2 * 0.05);
    });
  });
  scene.at(18, () => strata.forEach((s) => s.a.state(STRATA.hold)));
  let dragon;
  scene.at(T_ARRIVE, () => {
    dragon = scene.spawn(ACTOR3, pStart, { yaw: yawStart, state: N.arrive, skin: SKIN.normal });
    ring(dim, "ed_nature_rock", up(pStart, 0.5), 4, 6);
  });
  scene.at(T_ARRIVE + 20, () => {
    strata.forEach((s) => s.a.state(STRATA.part));
    sound(dim, "ed_nature_strata", pStart, 1.4, 0.8);
  });
  scene.every(6, () => burst(dim, "ed_nature_dust", up(pStart, 1.5), 5, 3), T_ARRIVE, T_ARRIVE + ARRIVE_LAND);
  scene.at(T_ARRIVE + ARRIVE_LAND, () => {
    for (const x of [-3, 3]) {
      const at = groundBelow(dim, up(local(pStart, yawStart, x, 5.5), 3));
      quake(at, 1.7);
      footprints.push(at);
    }
    for (const e of hostiles(dim, local(pStart, yawStart, 0, 5), ED01.landRadius, caster)) {
      damage(e, ED01.landDamage, caster);
      knockback(e, pStart, ED01.stepKnockH * 1.5, ED01.stepKnockV);
    }
  });
  scene.at(T_WALK, () => dragon?.state(N.move));
  scene.every(1, (e) => {
    dragon?.move(path[Math.min(e, WALK_CYCLE)], yaws[Math.min(e, WALK_CYCLE)]);
  }, T_WALK, T_POWER + 1);
  for (const s of STEPS) {
    scene.at(T_WALK + s.t, () => {
      const at = groundBelow(dim, up(local(path[s.t], yaws[s.t], s.x, s.z), 3));
      footprints.push(at);
      quake(at, ED01.stepQuakeSize);
      for (const e of hostiles(dim, at, ED01.stepRadius, caster)) {
        damage(e, ED01.stepDamage, caster);
        knockback(e, at, ED01.stepKnockH, ED01.stepKnockV);
      }
    });
  }
  function quake(at, size) {
    const q = scene.spawn("ed_nature_quake", up(at, 0.02), { size, state: 1, yaw: scene.tick * 47 % 360 });
    scene.after(27, () => scene.despawn(q));
    particle(dim, "ed_nature_shock", up(at, 0.15));
    particle(dim, "ed_nature_dust", up(at, 0.4));
    particle(dim, "ed_nature_rock", up(at, 0.3));
    sound(dim, "ed_nature_quake", at, 1);
  }
  const back = up(pEnd, 11);
  scene.at(T_POWER, () => {
    dragon?.state(N.power);
    sound(dim, "ed_nature_grow", back, 1.4);
  });
  scene.at(T_POWER + 20, () => dragon?.skin(SKIN.bloom));
  scene.every(6, (e) => {
    burst(dim, e % 12 === 0 ? "ed_nature_leaf" : "ed_nature_petal", back, 4, 2);
    particle(dim, "ed_nature_pollen", up(back, 2));
  }, T_POWER + 12, T_ATTACK);
  const binds = [];
  scene.at(T_ROOTS, () => {
    const from = footprints.length ? footprints : [pEnd];
    const nearestPrint = (p) => from.reduce((b, f) => distXZ(f, p) < distXZ(b, p) ? f : b, from[0]);
    const found = hostiles(dim, center, ED01.rootRadius, caster, ED01.maxRoots);
    const goals = found.length ? found.map((e) => ({ e, at: { ...e.location } })) : Array.from({ length: ED01.idleRoots }, (_, k2) => ({ at: polar(center, 3, k2 * (360 / ED01.idleRoots) + 20) }));
    goals.forEach((g, k2) => {
      scene.after(k2 * 3, () => {
        const target = g.e && isAlive(g.e) ? { ...g.e.location } : g.at;
        const fp = nearestPrint(target);
        const d = Math.max(0.5, distXZ(fp, target));
        const size = clamp(d / ROOT_LEN, ED01.rootMinSize, ED01.rootMaxSize);
        const yaw = yawOf(sub(target, fp));
        const tip = groundBelow(dim, up(add(fp, mul(fromYaw(yaw), ROOT_LEN * size)), 2));
        const a = scene.spawn("ed_nature_root", up(fp, 0.05), { yaw, size, state: ROOT.grow });
        const b = { e: g.e, a, tip };
        binds.push(b);
        sound(dim, "ed_nature_root", fp, 1);
        line(dim, "ed_nature_dust", fp, tip, 3);
        scene.after(ROOT_BIND - 3, () => {
          particle(dim, "ed_nature_spore", up(tip, 1));
          sound(dim, "ed_nature_bind", tip, 1);
          if (b.e && isAlive(b.e)) {
            b.release = restrain(scene, b.e, T_HIT - scene.tick + 4, { x: tip.x, y: Math.max(tip.y, b.e.location.y - 0.5), z: tip.z });
          }
        });
        scene.after(26, () => a.state(ROOT.hold));
      });
    });
  });
  const rings = [];
  scene.at(T_PILLARS, () => {
    const pool = hostiles(dim, center, ED01.rootRadius + 2, caster);
    const groups = [];
    const used = /* @__PURE__ */ new Set();
    for (const e of pool) {
      if (used.has(e.id) || groups.length >= ED01.maxRings) continue;
      const g = pool.filter((o) => !used.has(o.id) && dist(o.location, e.location) <= ED01.groupRadius);
      g.forEach((o) => used.add(o.id));
      groups.push(g);
    }
    const specs = groups.length ? groups.map((g) => {
      const c = mul(g.reduce((s, e) => add(s, e.location), { x: 0, y: 0, z: 0 }), 1 / g.length);
      const spread = Math.max(...g.map((e) => distXZ(e.location, c)));
      return { c: groundBelow(dim, up(c, 2)), r: clamp(spread + 2.5, ED01.ringMin, ED01.ringMax) };
    }) : [{ c: center, r: ED01.ringMin }];
    specs.forEach((sp, gi) => {
      const rg = { c: sp.c, r: sp.r, pillars: [] };
      rings.push(rg);
      const fp = footprints.length ? footprints.reduce((b, f) => distXZ(f, sp.c) < distXZ(b, sp.c) ? f : b) : pEnd;
      const a0 = Math.atan2(fp.z - sp.c.z, fp.x - sp.c.x) * 180 / Math.PI;
      for (let k2 = 0; k2 < ED01.pillarsPerRing; k2++) {
        scene.after(gi * 4 + k2 * 3, () => {
          const ang = a0 + 360 * k2 / ED01.pillarsPerRing;
          const at = groundBelow(dim, up(polar(sp.c, sp.r, ang), 3));
          const yaw = yawOf(sub(sp.c, at));
          const a = scene.spawn("ed_nature_pillar", at, { yaw, size: ED01.pillarSize, state: PILLAR.rise });
          const tan = right(sub(sp.c, at));
          const cells = [at, add(at, tan), sub(at, tan)];
          rg.pillars.push({ a, at, cells });
          particle(dim, "ed_nature_rise", at);
          particle(dim, "ed_nature_dust", up(at, 0.5));
          particle(dim, "ed_nature_rock", up(at, 1));
          sound(dim, "ed_nature_pillar", at, 1, 0.92 + k2 * 0.04);
          scene.after(8, () => cells.forEach((c) => tb.column(c.x, c.y, c.z, ED01.pillarBarrierHeight)));
          scene.after(16, () => a.state(PILLAR.hold));
          for (const e of hostiles(dim, at, 1.6, caster)) shove(e, sub(sp.c, at), 0.8, 0.4);
        });
      }
    });
  });
  let warn;
  scene.at(T_ATTACK, () => {
    dragon?.state(N.attack_a);
    warn = scene.spawn("telegraph", up(slamAt, 0.05), { kind: 2, size: ED01.slamRadius, state: 4 });
    sound(dim, "ed_nature_rumble", slamAt, 1.2, 1.15);
  });
  scene.every(8, () => ring(dim, "ed_nature_mote", up(slamAt, 0.3), ED01.slamRadius * 0.7, 5, scene.tick * 7), T_ATTACK, T_HIT);
  scene.at(T_HIT, () => {
    warn?.state(3);
    const w = warn;
    scene.after(8, () => {
      if (w) scene.despawn(w);
    });
    const qa = scene.spawn("ed_nature_quake", up(slamAt, 0.03), { size: 3.4, state: 1 });
    scene.after(27, () => scene.despawn(qa));
    sound(dim, "ed_nature_slam", slamAt, 2);
    particle(dim, "ed_nature_shock_big", up(slamAt, 0.2));
    particle(dim, "fx_flash", up(slamAt, 1));
    burst(dim, "ed_nature_dust", up(slamAt, 1), 4, 6);
    ring(dim, "ed_nature_rock", up(slamAt, 0.5), 3, 6);
    for (const e of hostiles(dim, slamAt, ED01.slamRadius, caster)) {
      damage(e, ED01.slamDamage, caster);
      knockback(e, slamAt, ED01.slamKnockH, ED01.slamKnockV);
    }
  });
  scene.at(T_HIT + 2, () => {
    for (const s of strata) {
      s.a.state(STRATA.erupt);
      particle(dim, "ed_nature_rise", s.at);
      particle(dim, "ed_nature_rock", up(s.at, 1));
      for (const e of hostiles(dim, s.at, ED01.strataRadius * (s.size / 1.6), caster)) {
        damage(e, ED01.strataDamage, caster);
        knockback(e, s.at, 1, 0.7);
      }
    }
    sound(dim, "ed_nature_erupt", pStart, 1.4, 0.8);
  });
  scene.at(T_HIT + 20, () => strata.forEach((s) => s.a.state(STRATA.crumble)));
  scene.at(T_HIT + 44, () => {
    strata.forEach((s) => scene.despawn(s.a));
  });
  scene.at(T_HIT + 1, () => {
    for (const b of binds) {
      const delay = 3 + Math.min(14, Math.round(dist(b.tip, slamAt) * 0.6));
      scene.after(delay, () => {
        b.release?.();
        b.a.state(ROOT.erupt);
        particle(dim, "ed_nature_splinter", up(b.tip, 1));
        particle(dim, "ed_nature_spore", up(b.tip, 1.2));
        sound(dim, "ed_nature_erupt", b.tip, 1, 1.1);
        for (const e of hostiles(dim, b.tip, ED01.rootEruptRadius, caster)) {
          damage(e, ED01.rootDamage, caster);
          knockback(e, b.tip, 0.3, ED01.rootKnockV);
        }
        scene.after(17, () => scene.despawn(b.a));
      });
    }
  });
  scene.at(T_HIT + 6, () => {
    rings.forEach((rg, gi) => {
      const crushed = /* @__PURE__ */ new Set();
      rg.pillars.forEach((p, k2) => {
        scene.after(gi * 2 + k2 * 2, () => {
          p.cells.forEach((c) => tb.removeColumn(c.x, c.y, c.z, ED01.pillarBarrierHeight));
          p.a.state(PILLAR.erupt);
          sound(dim, "ed_nature_topple", p.at, 1, 0.95 + k2 * 0.03);
          scene.after(PILLAR_IMPACT, () => {
            line(dim, "ed_nature_dust", p.at, rg.c, 3);
            particle(dim, "ed_nature_rock", up(rg.c, 0.6));
            for (const e of hostiles(dim, rg.c, rg.r + 1.5, caster)) {
              if (crushed.has(e.id) || distToSegment(e.location, p.at, rg.c) > ED01.pillarWidth) continue;
              crushed.add(e.id);
              damage(e, ED01.pillarDamage, caster);
            }
          });
          scene.after(23, () => scene.despawn(p.a));
        });
      });
      scene.after(gi * 2 + rg.pillars.length * 2 + PILLAR_IMPACT + 2, () => {
        particle(dim, "ed_nature_shock_big", up(rg.c, 0.2));
        burst(dim, "ed_nature_spore", up(rg.c, 1), 2, 4);
        burst(dim, "ed_nature_leaf", up(rg.c, 1.5), 2.5, 3);
        sound(dim, "ed_nature_erupt", rg.c, 1.6, 0.75);
        for (const e of hostiles(dim, rg.c, rg.r + 1, caster)) {
          damage(e, ED01.convergeDamage, caster);
          knockback(e, rg.c, ED01.convergeKnockH, ED01.convergeKnockV);
        }
      });
    });
  });
  scene.at(T_DEPART, () => dragon?.state(N.depart));
  scene.at(T_DEPART + DEPART_PETRIFY, () => {
    dragon?.skin(SKIN.stone);
    burst(dim, "ed_nature_dust", back, 5, 4);
  });
  scene.every(8, () => {
    ring(dim, "ed_nature_dust", up(pEnd, 0.4), 6, 5, scene.tick * 11);
    particle(dim, "ed_nature_rock", up(pEnd, 2));
  }, T_DEPART + 20, T_DEPART + DEPART_LEN);
  scene.at(T_DEPART + 22, () => sound(dim, "ed_nature_rumble", pEnd, 1.4, 0.85));
  scene.at(T_DEPART + DEPART_LEN, () => {
    burst(dim, "ed_nature_leaf", up(pEnd, 1), 6, 4);
    if (dragon) scene.despawn(dragon);
  });
  scene.endAt(T_END2);
  void SCALE;
});

// src/config/ed02.ts
var ED02 = {
  // ---- staging (blocks)
  /** The charge lane starts this far behind the caster... */
  laneBack: 3,
  /** ...and this far to the caster's right, so the 17-block dragon emerges beside them, not on them. */
  laneSide: 5,
  /** If the focus point is closer than this to the caster, the lane is aimed straight ahead instead. */
  minFocus: 9,
  /** The hips run this far past the focus point before skidding (the horns lead by ~8 blocks). */
  overshoot: 5,
  /** Clamp of the hips' charge distance (lane length incl. horns and skid ends up ~26-34 blocks). */
  chargeMin: 16,
  chargeMax: 24,
  /** Heat-shimmer wall stands this far ahead of the dragon's spawn point. */
  wallAhead: 1,
  // ---- Stage I: Internal Ignition (heat shock when the dragon bellows)
  igniteRadius: 6,
  igniteDamage: 4,
  igniteKnock: 0.7,
  // ---- Stage II: The Carnotaur's Rampage
  /** Sprint starts at this fraction of full speed and reaches full speed after accelTicks. */
  startSpeed: 0.55,
  accelTicks: 6,
  /** Horn strike zone: centred hornReach blocks ahead of the hips, hornDepth deep, hornRadius to either side. */
  hornReach: 7,
  hornDepth: 2.2,
  hornRadius: 2.6,
  hornDamage: 9,
  /** Horn toss throws enemies sideways out of the lane (horizontal / vertical strength). */
  hornKnockH: 1.5,
  hornKnockV: 0.6,
  /** Body slam zone along the flanks (blocks behind / ahead of the hips, half width). */
  bodyBack: 2.5,
  bodyFront: 5,
  bodyRadius: 2.5,
  bodyDamage: 6,
  bodyKnockH: 1.1,
  bodyKnockV: 0.35,
  /** Minimum ticks between a horn hit and a body hit on the same enemy. */
  bodyDelay: 4,
  /** Search radius around the dragon for melee checks. */
  scanRadius: 10,
  // ---- Stage III: The Furnace Opens
  /** Point-blank thermal discharge around the dragon when the vents release. */
  dischargeRadius: 6,
  dischargeDamage: 8,
  dischargeKnock: 1.4,
  /** The superheated wave runs back along the charge lane at this speed (blocks/s). */
  waveSpeed: 18,
  /** Half width of the wave (blocks either side of the lane centre). */
  waveHalfWidth: 3.6,
  waveDamage: 11,
  waveKnockH: 0.6,
  waveKnockV: 0.25,
  /** Wave starts this far in front of the hips (at the chest) and stops this far from the lane start. */
  waveStartBack: 2.5,
  waveStopShort: 3,
  /** Burning and weakness left by the wave and the discharge. */
  burnSeconds: 3,
  weaknessTicks: 80,
  /** Vitrified-ground decals every N blocks behind the wave; they cool and fade on these delays (ticks). */
  glassEvery: 3.2,
  glassCoolTicks: 24,
  glassFadeTicks: 40,
  /** Heavy breathing between cooling and dissolution (ticks). */
  pantTicks: 16
};

// src/spells/ed02_thermal_tyrant.ts
var ACTOR4 = "dragon_heat";
var S4 = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  turn_l: 4,
  turn_r: 5,
  attack_a: 6,
  attack_b: 7,
  power: 8,
  react: 9,
  rest: 10,
  depart: 11,
  ignite: 12,
  charge: 13,
  skid: 14,
  pant: 15,
  cool: 16,
  roar: 17,
  walk: 18
};
var SKIN2 = { cool: 0, ignited: 1, whitehot: 2 };
var RUN_SPEED = 10.02;
var WALK_SPEED2 = 3.53;
var TURN_RATE = 225;
var T6 = {
  arriveWalk: secs(1.2),
  arrive: secs(1.6),
  ignite: secs(1.6),
  igniteRoar: secs(1.1),
  skid: secs(0.7),
  powerOpen: secs(1),
  cool: secs(1.2),
  depart: secs(2)
};
var WALL2 = { form: 1, hold: 2, part: 3, fade: 4 };
var WAVE2 = { rise: 1, travel: 2, burst: 3 };
var GLASS = { appear: 1, hold: 2, fade: 3 };
var LANE = { appear: 1, armed: 2, surge: 3, fade: 4 };
var ed02_thermal_tyrant_default = defineSpell("ed02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  let F = focus(caster, aim, 12).center;
  let d0 = flat(sub(F, caster.location));
  if (len(d0) < ED02.minFocus) {
    F = groundBelow(dim, add(caster.location, mul(aim.forward, ED02.minFocus + 4)));
    d0 = flat(sub(F, caster.location));
  }
  d0 = norm(len(d0) < 0.01 ? aim.forward : d0);
  const W2 = groundBelow(dim, add(add(caster.location, mul(d0, -ED02.laneBack)), mul(right(d0), ED02.laneSide)));
  const d = norm(flat(sub(F, W2)));
  const rv = right(d);
  const yaw = yawOf(d);
  const back = mul(d, -1);
  const chargeDist = clamp(dot(flat(sub(F, W2)), d) + ED02.overshoot, ED02.chargeMin, ED02.chargeMax);
  const skidDist = RUN_SPEED / 20 * (T6.skid - 1) / 2;
  const lanePoint = (s2, lat = 0) => groundBelow(dim, add(add(W2, mul(d, s2)), mul(rv, lat)));
  const arriveDist = WALK_SPEED2 * T6.arriveWalk / 20;
  const W0 = add(W2, mul(d, -arriveDist));
  let s = -arriveDist;
  let y = groundBelow(dim, W0).y;
  let curYaw = yaw;
  let facing = d;
  let pos = { x: W0.x, y, z: W0.z };
  const place = (yawNow = curYaw) => {
    const p = add(W2, mul(d, s));
    const g = groundBelow(dim, p).y;
    y += clamp(g - y, -0.35, 0.35);
    pos = { x: p.x, y, z: p.z };
    curYaw = yawNow;
    dragon.move(pos, curYaw);
  };
  const chest = () => up(add(pos, mul(facing, 2.2)), 4.6);
  const wallAt = groundBelow(dim, add(W0, mul(d, ED02.wallAhead)));
  const wall = scene.spawn("ed_heat_shimmer", wallAt, { yaw, state: WALL2.form });
  const dragon = scene.spawn(ACTOR4, pos, { yaw, state: S4.arrive, skin: SKIN2.cool });
  sound(dim, "ed_heat_shimmer", wallAt, 1.1);
  scene.at(10, () => wall.state(WALL2.part));
  scene.at(30, () => wall.state(WALL2.fade));
  scene.at(44, () => scene.despawn(wall));
  scene.every(4, (e) => {
    particle(dim, "ed_heat_haze", up(add(wallAt, mul(rv, e % 3 * 2.5 - 2.5)), 1.5));
    particle(dim, "ed_heat_ember", up(wallAt, 3));
  }, 0, 32);
  scene.span(0, T6.arriveWalk + 1, (p) => {
    s = -arriveDist * (1 - p);
    place();
  });
  const tI = T6.arrive;
  let lane;
  const laneLen = clamp(chargeDist + skidDist + 8.5 - 4, 4, 32);
  scene.at(tI, () => {
    dragon.state(S4.ignite);
    sound(dim, "ed_heat_ignite", chest(), 1.2);
  });
  scene.at(tI + 4, () => {
    lane = scene.spawn("ed_heat_lane", lanePoint(4), { yaw, state: LANE.appear });
    lane.prop("len", laneLen);
    sound(dim, "ed_heat_lane", lanePoint(10), 1);
  });
  scene.at(tI + 10, () => {
    dragon.skin(SKIN2.ignited);
    burst(dim, "ed_heat_ember", chest(), 2.2, 4);
  });
  scene.at(tI + 22, () => lane?.state(LANE.armed));
  scene.at(tI + T6.igniteRoar, () => {
    const c = chest();
    particle(dim, "ed_heat_ring", up(pos, 0.3));
    particle(dim, "fx_flash", c);
    ring(dim, "ed_heat_vent", up(pos, 3.5), 2.8, 5);
    for (const e of hostiles(dim, c, ED02.igniteRadius, caster)) {
      if (damage(e, ED02.igniteDamage, caster)) knockback(e, pos, ED02.igniteKnock, 0.35);
    }
  });
  const tC = tI + T6.ignite;
  const hits = /* @__PURE__ */ new Map();
  let phase = "wait";
  let k2 = 0;
  function strikes() {
    for (const e of hostiles(dim, add(pos, mul(d, 3)), ED02.scanRadius, caster)) {
      const dy = e.location.y - pos.y;
      if (dy > 7 || dy < -3) continue;
      const rel = flat(sub(e.location, pos));
      const along = dot(rel, d);
      const latS = dot(rel, rv);
      const lat = Math.abs(latS);
      let h = hits.get(e.id);
      if (!h) {
        h = { horn: -1, body: false };
        hits.set(e.id, h);
      }
      const away = norm(add(mul(rv, latS >= 0 ? 1 : -1), mul(d, 0.45)));
      if (h.horn < 0 && along > ED02.hornReach - ED02.hornDepth && along < ED02.hornReach + 1.5 && lat < ED02.hornRadius) {
        h.horn = scene.tick;
        if (damage(e, ED02.hornDamage, caster)) shove(e, away, ED02.hornKnockH, ED02.hornKnockV);
        impact(e, 1);
      } else if (!h.body && along > -ED02.bodyBack && along < ED02.bodyFront && lat < ED02.bodyRadius && (h.horn < 0 || scene.tick - h.horn >= ED02.bodyDelay)) {
        h.body = true;
        if (damage(e, ED02.bodyDamage, caster)) shove(e, away, ED02.bodyKnockH, ED02.bodyKnockV);
        impact(e, 0.8);
      }
    }
  }
  function impact(e, pitch) {
    const at = up(e.location, 1.1);
    particle(dim, "ed_heat_spark", at);
    particle(dim, "ed_heat_ember", at);
    sound(dim, "ed_heat_hit", at, 1, pitch);
  }
  scene.at(tC, () => {
    phase = "run";
    dragon.state(S4.charge);
    lane?.state(LANE.armed);
  });
  scene.every(1, () => {
    if (phase === "run") {
      const f = k2 < ED02.accelTicks ? ED02.startSpeed + (1 - ED02.startSpeed) * k2 / ED02.accelTicks : 1;
      k2++;
      s = Math.min(chargeDist, s + RUN_SPEED / 20 * f);
      place();
      strikes();
      if (k2 % 3 === 0) particle(dim, "ed_heat_haze", up(add(pos, mul(d, -3)), 1.2));
      if (k2 % 4 === 0) particle(dim, "ed_heat_ember", up(add(pos, mul(d, 1)), 5));
      if (s >= chargeDist) {
        phase = "skid";
        k2 = 0;
        dragon.state(S4.skid);
        particle(dim, "ed_heat_skid", up(add(pos, mul(d, 1)), 0.3));
      }
    } else if (phase === "skid") {
      k2++;
      s += RUN_SPEED / 20 * Math.max(0, 1 - k2 / T6.skid);
      place();
      strikes();
      if (k2 % 3 === 0) particle(dim, "ed_heat_skid", up(add(pos, mul(d, 1)), 0.3));
      if (k2 >= T6.skid) {
        phase = "done";
        stage3(scene.tick + 1);
      }
    }
  }, tC, tC + 200);
  scene.endAt(tC + 320);
  function burn(e) {
    effect(e, "weakness", ED02.weaknessTicks, 0);
    try {
      e.setOnFire(ED02.burnSeconds, true);
    } catch {
    }
  }
  function stage3(t0) {
    const turnDir = dot(flat(sub(caster.location, pos)), rv) > 0 ? -1 : 1;
    const turnTicks = Math.round(180 / TURN_RATE * 20);
    scene.at(t0, () => dragon.state(turnDir > 0 ? S4.turn_r : S4.turn_l));
    scene.span(t0, t0 + turnTicks, (p) => dragon.move(pos, yaw + turnDir * 180 * p));
    const tP = t0 + turnTicks;
    scene.at(tP, () => {
      curYaw = yaw + turnDir * 180;
      facing = back;
      dragon.state(S4.power);
      lane?.state(LANE.surge).skin(1);
      sound(dim, "ed_heat_lane", chest(), 1.2, 1.25);
    });
    scene.at(tP + 8, () => {
      dragon.skin(SKIN2.whitehot);
      particle(dim, "fx_flash", chest());
    });
    scene.every(3, () => particle(dim, "ed_heat_vent", up(pos, 4.2)), tP + 6, tP + T6.powerOpen);
    const tR = tP + T6.powerOpen;
    const sStart = s - ED02.waveStartBack;
    const sEnd = Math.min(ED02.waveStopShort, sStart - 1);
    const step = ED02.waveSpeed / 20;
    const waveTicks = Math.ceil((sStart - sEnd) / step);
    const waveYaw = yawOf(back);
    let sf = sStart;
    let wave;
    let nextGlass = sStart - 1;
    let glassN = 0;
    const waved = /* @__PURE__ */ new Set();
    function spawnGlass(at) {
      glassN++;
      const g = scene.spawn("ed_heat_glass", lanePoint(at, (glassN % 2 ? 1 : -1) * 0.9), { yaw: glassN * 67, state: GLASS.appear });
      if (glassN % 3 === 1) sound(dim, "ed_heat_glass", g.loc, 0.8, 0.9 + glassN % 4 * 0.08);
      scene.after(6, () => g.state(GLASS.hold));
      scene.after(ED02.glassCoolTicks, () => g.skin(1));
      scene.after(ED02.glassFadeTicks, () => g.state(GLASS.fade));
      scene.after(ED02.glassFadeTicks + 17, () => scene.despawn(g));
    }
    scene.at(tR, () => {
      const c = chest();
      sound(dim, "ed_heat_wave", c, 1.5);
      particle(dim, "ed_heat_ring", up(pos, 0.3));
      particle(dim, "fx_flash", c);
      burst(dim, "ed_heat_ember", c, 3, 6);
      ring(dim, "ed_heat_steam", up(pos, 1), 3.5, 5);
      for (const e of hostiles(dim, add(pos, mul(back, 2)), ED02.dischargeRadius, caster)) {
        if (damage(e, ED02.dischargeDamage, caster)) {
          knockback(e, pos, ED02.dischargeKnock, 0.5);
          burn(e);
        }
      }
      wave = scene.spawn("ed_heat_wave", lanePoint(sf), { yaw: waveYaw, state: WAVE2.rise });
      scene.after(7, () => wave?.state(WAVE2.travel));
    });
    scene.every(1, (e) => {
      sf = Math.max(sEnd, sf - step);
      const fp = lanePoint(sf);
      wave?.move(fp, waveYaw);
      if (e % 2 === 0) particle(dim, "ed_heat_wavefront", up(fp, 1.2));
      if (e % 3 === 1) particle(dim, "ed_heat_haze", up(add(fp, mul(d, 1.5)), 0.8));
      while (sf <= nextGlass && nextGlass >= sEnd) {
        spawnGlass(nextGlass);
        nextGlass -= ED02.glassEvery;
      }
      for (const t of hostiles(dim, fp, ED02.waveHalfWidth + 2.5, caster)) {
        if (waved.has(t.id) || !isAlive(t)) continue;
        const rel = flat(sub(t.location, W2));
        const along = dot(rel, d);
        if (Math.abs(dot(rel, rv)) > ED02.waveHalfWidth || along < sf - 1 || along > sStart + 2.5) continue;
        waved.add(t.id);
        if (damage(t, ED02.waveDamage, caster)) {
          shove(t, back, ED02.waveKnockH, ED02.waveKnockV);
          burn(t);
        }
        particle(dim, "ed_heat_ember", up(t.location, 1));
      }
    }, tR + 1, tR + 1 + waveTicks);
    scene.at(tR + 1 + waveTicks, () => {
      wave?.state(WAVE2.burst);
      particle(dim, "ed_heat_wavefront", up(lanePoint(sEnd), 1));
      const w = wave;
      scene.after(12, () => {
        if (w) scene.despawn(w);
      });
    });
    const tCool = tR + Math.max(10, waveTicks - 4);
    scene.at(tCool, () => {
      dragon.state(S4.cool).skin(SKIN2.ignited);
      lane?.state(LANE.fade);
      ring(dim, "ed_heat_steam", up(pos, 4), 2.5, 4);
    });
    scene.at(tCool + 10, () => {
      if (lane) scene.despawn(lane);
    });
    scene.at(tCool + 12, () => dragon.skin(SKIN2.cool));
    const tPant = tCool + T6.cool;
    scene.at(tPant, () => dragon.state(S4.pant));
    const tDep = tPant + ED02.pantTicks;
    scene.at(tDep, () => {
      dragon.state(S4.depart);
      particle(dim, "ed_heat_steam", up(pos, 3));
    });
    scene.at(tDep + 14, () => burst(dim, "ed_heat_slag", up(pos, 2.5), 2.5, 4));
    scene.at(tDep + 26, () => {
      burst(dim, "ed_heat_slag", up(pos, 1), 2, 3);
      particle(dim, "ed_heat_steam", up(pos, 1));
    });
    scene.at(tDep + T6.depart, () => scene.despawn(dragon));
    scene.endAt(tDep + T6.depart + 2);
  }
});

// src/config/ed03.ts
var ED03 = {
  /** How far from the aim point the spell snaps onto the nearest enemy (blocks). */
  snap: 12,
  /** Radius around the focus in which the enemy group is gathered. */
  radius: 12,
  /** Maximum enemies used to define the group (and shard targets per wave). */
  maxTargets: 8,
  // ---- Stage I: The Rising Deep
  /** The dragon lands this far beyond the focus point, its flank (right side) toward the caster. */
  landBeyond: 9,
  /** Radius and sweep (degrees) of the descending spiral it swims from the water mass to its landing. */
  spiralRadius: 6.5,
  spiralSweep: 240,
  /** Height of the suspended water mass above the landing ground and its rendered size multiplier. */
  massHeight: 12,
  massSize: 1.2,
  /** Landing wave: enemies within this radius of the dragon are washed away (knockback) and take damage. */
  landRadius: 6,
  landDamage: 3,
  landKnockH: 0.9,
  landKnockV: 0.3,
  // ---- Stage II: The Cryogenic Sail
  /** Current radius = group spread + pad, clamped (blocks).  Each tail sweep throws two currents. */
  currentPad: 1.5,
  currentMin: 2.5,
  currentMax: 7,
  /** Radius multipliers of the four currents (two per sweep). */
  currentScale: [1, 0.72, 1.18, 0.55],
  /** Half-width of a current's water band: enemies inside are carried along it. */
  currentWidth: 1.8,
  /** Water-based displacement: push strength along the current, applied every `shoveEvery` ticks. */
  currentShove: 0.5,
  shoveEvery: 3,
  /** Damage when a current first catches an enemy. */
  currentDamage: 3,
  /** Freezing front: enemies within this distance of a current when the front passes are frozen. */
  freezeWidth: 2.3,
  freezeDamage: 5,
  /** Freezing is temporary: it lasts until the crown's third fracture wave (plus slowness afterwards). */
  thawSlowTicks: 60,
  thawSlowAmp: 1,
  /** Height of the barrier columns raised under the ice spirals (real obstacles, every other segment). */
  barrierHeight: 2,
  // ---- Stage III: The Frozen Crown
  /** Crown radius = group spread + pad, clamped. */
  crownPad: 2.5,
  crownMin: 3.5,
  crownMax: 7.5,
  /** Damage of each of the three fracture waves (sharp ice formations that hit each enemy). */
  shardDamage: [5, 6, 8],
  /** Ticks a shard needs to reach its enemy. */
  shardFlight: 6,
  /** Finishing area damage around the crown centre: radius = crown radius + finalExtra. */
  finalDamage: 14,
  finalExtra: 2.5,
  finalKnockH: 1.4,
  finalKnockV: 0.5,
  // ---- dragon anatomy used to place effects (rendered blocks)
  /** Distance from the dragon origin back to its hips, and hip-to-tail-tip length. */
  hipBack: 2.4,
  tailReach: 11
};

// src/spells/ed03_abyssal_cryotitan.ts
var DRAGON = { actor: "dragon_tide", scale: 2 };
var D2 = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  turn_l: 4,
  turn_r: 5,
  attack_a: 6,
  attack_b: 7,
  power: 8,
  react: 9,
  rest: 10,
  depart: 11,
  swim: 12,
  land: 13,
  roar: 14,
  attack_c: 15
};
var T7 = {
  arrive: 20,
  land: 16,
  landHit: 5,
  power: 30,
  sweep: 30,
  sweepHit: [10, 21],
  flare: 22,
  flareHit: 9,
  roar: 28,
  strike: 34,
  strikeHit: 18,
  depart: 32
};
var STREAM = { hidden: 0, form: 1, hold: 2, fade: 3 };
var MASS = { hidden: 0, gather: 1, hold: 2, burst: 3, disperse: 4 };
var CUR = { hidden: 0, form: 1, flow: 2, freeze: 3, spiral: 4, ice: 5, rise: 6, shatter: 7 };
var CROWN = { hidden: 0, assemble: 1, hold: 2, frac1: 3, frac2: 4, frac3: 5 };
var SHARD = { hidden: 0, launch: 1, hit: 2 };
var FROZEN = { hidden: 0, encase: 1, hold: 2, shatter: 3 };
var CUR_R = 4;
var CROWN_R = 4;
var CUR_SWEEP = 160;
var tMass = 4;
var tArrive = 18;
var tSwim = tArrive + T7.arrive;
var tLand = 70;
var tPower = tLand + T7.land;
var tSweep = 114;
var tFlare = tSweep + T7.sweep;
var tFreeze = tFlare + T7.flareHit + 2;
var tSpiral = 174;
var tRoar = 182;
var tCrown = 188;
var tRise = 190;
var tStrike = tRoar + T7.roar - 2;
var tHit = tStrike + T7.strikeHit;
var WAVE_GAP = 9;
var ed03_abyssal_cryotitan_default = defineSpell("ed03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, ED03.snap);
  const fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);
  const group = hostiles(dim, center, ED03.radius, caster, ED03.maxTargets);
  let G = center;
  if (group.length) {
    let x = 0, z = 0;
    for (const e of group) {
      x += e.location.x;
      z += e.location.z;
    }
    G = groundBelow(dim, { x: x / group.length, y: center.y + 1, z: z / group.length });
  }
  const spread = group.reduce((m, e) => Math.max(m, distXZ(e.location, G)), 0);
  const L3 = groundBelow(dim, up(add(center, mul(fwd, ED03.landBeyond)), 2));
  const roomR = Math.max(ED03.currentMin, distXZ(G, L3) - 2.5);
  const Rcur = clamp(spread + ED03.currentPad, ED03.currentMin, Math.min(ED03.currentMax, roomR));
  const Rc = clamp(spread + ED03.crownPad, ED03.crownMin, Math.min(ED03.crownMax, Math.max(ED03.crownMin, roomR)));
  const yawLand = yawOf(rt);
  const Q = sub(L3, mul(fwd, ED03.spiralRadius));
  const pathPos = (p) => {
    const phi = (90 + ED03.spiralSweep * (1 - p)) * Math.PI / 180;
    const h = add(Q, add(mul(rt, Math.cos(phi) * ED03.spiralRadius), mul(fwd, Math.sin(phi) * ED03.spiralRadius)));
    return { x: h.x, y: L3.y + ED03.massHeight * (1 - smooth(p)), z: h.z };
  };
  const pathYaw = (p) => yawOf(flat(sub(pathPos(Math.min(1, p + 0.01)), pathPos(Math.max(0, p - 0.01)))));
  const M = pathPos(0);
  const hip = sub(L3, mul(rt, ED03.hipBack));
  const tailTip = (alphaDeg) => {
    const a = alphaDeg * Math.PI / 180;
    return up(add(hip, mul(add(mul(rt, -Math.cos(a)), mul(fwd, -Math.sin(a))), ED03.tailReach)), 1);
  };
  const sailPeak = up(sub(L3, mul(rt, 0.9)), 9);
  sound(dim, "ed_tide_currents", M, 1.2);
  const streams = [];
  for (let k2 = 0; k2 < 5; k2++) {
    const ang = k2 * 72 + 15, dy = -5 + k2 % 3 * 2.5;
    const p0 = up(add(M, add(mul(rt, Math.cos(ang * Math.PI / 180) * 11), mul(fwd, Math.sin(ang * Math.PI / 180) * 11))), dy);
    const a = scene.spawn("ed_tide_stream", p0, { state: STREAM.form, size: 1.4, yaw: yawOf(sub(M, p0)) });
    streams.push({ a, ang, dy, prev: p0 });
  }
  scene.at(8, () => streams.forEach((s) => s.a.state(STREAM.hold)));
  scene.span(1, 24, (p) => {
    const e = smooth(p);
    for (const s of streams) {
      const ang = (s.ang + 200 * e) * Math.PI / 180, r = 11 * (1 - e) + 0.4;
      const pos = up(add(M, add(mul(rt, Math.cos(ang) * r), mul(fwd, Math.sin(ang) * r))), s.dy * (1 - e));
      s.a.move(pos, yawOf(flat(sub(pos, s.prev))));
      s.prev = pos;
    }
  });
  scene.every(6, (el) => {
    const s = streams[el / 6 % 5];
    particle(dim, "ed_tide_spray", s.prev);
  }, 2, 24);
  scene.at(22, () => {
    streams.forEach((s) => s.a.state(STREAM.fade));
    burst(dim, "ed_tide_bubble", M, 3, 6);
  });
  scene.at(27, () => streams.forEach((s) => scene.despawn(s.a)));
  let mass;
  scene.at(tMass, () => {
    mass = scene.spawn("ed_tide_mass", M, { state: MASS.gather, size: ED03.massSize });
    sound(dim, "ed_tide_mass", M, 1.3);
  });
  scene.at(tMass + 20, () => mass?.state(MASS.hold));
  scene.every(5, () => {
    particle(dim, "ed_tide_bubble", M);
    particle(dim, "ed_tide_mist", up(M, -4));
  }, tMass + 6, 44);
  const dragon = scene.spawn(DRAGON.actor, M, { state: D2.hidden, yaw: pathYaw(0) });
  scene.at(tArrive, () => dragon.state(D2.arrive).move(M, pathYaw(0)));
  scene.span(tArrive, tSwim, (p) => {
    const q = 0.1 * easeIn(p);
    dragon.move(pathPos(q), pathYaw(q));
  });
  scene.at(30, () => {
    mass?.state(MASS.burst);
    burst(dim, "ed_tide_splash", M, 4, 6);
  });
  scene.at(tSwim, () => dragon.state(D2.swim));
  scene.span(tSwim, tLand, (p) => {
    const q = 0.1 + 0.9 * p;
    dragon.move(pathPos(q), pathYaw(q));
  });
  scene.every(4, (el) => particle(dim, "ed_tide_trail", pathPos(0.1 + 0.9 * el / (tLand - tSwim))), tSwim, tLand);
  scene.at(42, () => {
    mass?.state(MASS.disperse);
    sound(dim, "ed_tide_splash", M, 1.2, 0.7);
  });
  scene.every(4, () => particle(dim, "ed_tide_rain", up(M, -3)), 42, 62);
  scene.at(63, () => {
    if (mass) scene.despawn(mass);
  });
  scene.at(tLand, () => dragon.state(D2.land).move(L3, yawLand));
  scene.at(tLand + T7.landHit, () => {
    sound(dim, "ed_tide_splash", L3, 1.4, 0.85);
    particle(dim, "ed_tide_frost_ring", up(L3, 0.2));
    ring(dim, "ed_tide_splash", up(L3, 0.3), 3, 6);
    for (const e of hostiles(dim, L3, ED03.landRadius, caster)) {
      damage(e, ED03.landDamage, caster);
      knockback(e, L3, ED03.landKnockH, ED03.landKnockV);
    }
  });
  scene.at(tPower, () => {
    dragon.state(D2.power).skin(1);
    particle(dim, "ed_tide_mist", sailPeak);
  });
  scene.every(5, (el) => {
    const f = el / 5 % 4 / 3;
    particle(dim, "ed_tide_flake", up(sub(L3, mul(rt, -1.5 + 3.5 * f)), 7 + f));
  }, tPower + 6, tRoar);
  scene.at(tPower + T7.power, () => dragon.state(D2.idle));
  const currents = [];
  scene.at(tSweep, () => dragon.state(D2.attack_a));
  T7.sweepHit.forEach((h, w) => scene.at(tSweep + h, () => throwCurrents(w * 2, w === 0 ? 55 : 28)));
  function throwCurrents(k0, alpha) {
    const tip = tailTip(alpha);
    let dir = norm(flat(sub(tip, G)));
    if (distXZ(tip, G) < 0.5) dir = mul(fwd, -1);
    sound(dim, "ed_tide_flow", tip, 1.2, 0.95 + k0 * 0.05);
    for (let k2 = k0; k2 < k0 + 2; k2++) {
      const R2 = Math.max(ED03.currentMin * 0.7, Rcur * ED03.currentScale[k2]);
      const kind = k2 % 2;
      const side = kind === 0 ? right(dir) : mul(right(dir), -1);
      const a = scene.spawn("ed_tide_current", G, { kind, size: R2 / CUR_R, state: CUR.form, yaw: yawOf(dir) });
      const c = { a, R: R2, dir, side, born: scene.tick, touched: /* @__PURE__ */ new Set() };
      currents.push(c);
      line(dim, "ed_tide_spray", tip, arcPoint(c, 0, 1), 5);
      scene.after(16, () => a.state(CUR.flow));
    }
  }
  function arcPoint(c, deg, dy = 0) {
    const r = deg * Math.PI / 180;
    return {
      x: G.x + c.R * (Math.cos(r) * c.dir.x + Math.sin(r) * c.side.x),
      y: G.y + dy,
      z: G.z + c.R * (Math.cos(r) * c.dir.z + Math.sin(r) * c.side.z)
    };
  }
  function arcOf(c, p) {
    const v2 = flat(sub(p, G));
    return { r: Math.hypot(v2.x, v2.z), deg: Math.atan2(dot(v2, c.side), dot(v2, c.dir)) * 180 / Math.PI };
  }
  const reach = () => Math.max(Rcur * 1.2, ED03.currentMin) + ED03.freezeWidth + 1;
  scene.every(ED03.shoveEvery, () => {
    if (!currents.length) return;
    for (const e of hostiles(dim, G, reach(), caster)) {
      for (const c of currents) {
        const extent = Math.min(CUR_SWEEP, (scene.tick - c.born) * 17);
        const { r, deg } = arcOf(c, e.location);
        if (Math.abs(r - c.R) > ED03.currentWidth || deg < -12 || deg > extent) continue;
        const a = deg * Math.PI / 180;
        const tangent = add(mul(c.dir, -Math.sin(a)), mul(c.side, Math.cos(a)));
        const inward = norm(flat(sub(G, e.location)));
        shove(e, add(tangent, mul(inward, (r - c.R) * 0.25)), ED03.currentShove, 0.06);
        if (!c.touched.has(e.id)) {
          c.touched.add(e.id);
          damage(e, ED03.currentDamage, caster);
          particle(dim, "ed_tide_spray", e.location);
        }
        break;
      }
    }
  }, tSweep + T7.sweepHit[0], tFreeze + 4);
  scene.every(4, (el) => {
    for (const c of currents) if (scene.tick - c.born > 6) particle(dim, "ed_tide_spray", arcPoint(c, el * 37 % CUR_SWEEP, 0.6));
  }, tSweep + T7.sweepHit[0] + 4, tFreeze);
  scene.at(tFlare, () => dragon.state(D2.attack_c));
  scene.at(tFlare + T7.flareHit, () => {
    sound(dim, "ed_tide_freeze", G, 1.4);
    burst(dim, "ed_tide_glint", sailPeak, 2, 6);
    const tip = tailTip(10);
    for (const c of currents) {
      line(dim, "ed_tide_frostline", sailPeak, arcPoint(c, 0, 1), 8);
      line(dim, "ed_tide_frostline", tip, arcPoint(c, 0, 0.6), 4);
    }
  });
  scene.at(tFlare + T7.flare, () => dragon.state(D2.idle));
  const frozen = /* @__PURE__ */ new Map();
  const tShatter = tHit + 2 * WAVE_GAP + ED03.shardFlight;
  function freeze(e) {
    if (frozen.has(e.id) || !isAlive(e)) return;
    damage(e, ED03.freezeDamage, caster);
    if (!isAlive(e)) return;
    const at = { ...e.location };
    const release2 = restrain(scene, e, Math.max(10, tShatter - scene.tick + 2), at);
    const ice = scene.spawn("ed_tide_frozen", at, { state: FROZEN.encase });
    scene.after(10, () => ice.state(FROZEN.hold));
    frozen.set(e.id, { e, release: release2, ice });
    particle(dim, "ed_tide_flake", up(at, 1));
    particle(dim, "ed_tide_splinter", up(at, 0.6));
    sound(dim, "ed_tide_shatter", at, 0.6, 1.3);
  }
  scene.at(tFreeze, () => currents.forEach((c) => c.a.state(CUR.freeze)));
  scene.every(1, (el) => {
    const front = 12.5 * el - 10;
    for (const c of currents) particle(dim, "ed_tide_frostline", arcPoint(c, clamp(front, 0, CUR_SWEEP), 0.8));
    for (const e of hostiles(dim, G, reach(), caster)) {
      if (frozen.has(e.id)) continue;
      for (const c of currents) {
        const { r, deg } = arcOf(c, e.location);
        if (Math.abs(r - c.R) <= ED03.freezeWidth && deg >= -15 && deg <= front) {
          freeze(e);
          break;
        }
      }
    }
  }, tFreeze, tFreeze + 18);
  const barriers = [];
  scene.at(tSpiral, () => {
    sound(dim, "ed_tide_spiral", G, 1.3);
    currents.forEach((c) => c.a.state(CUR.spiral));
    const foes = hostiles(dim, G, reach() + 2, caster);
    for (const c of currents) {
      for (let k2 = 1; k2 < 8; k2 += 2) {
        const p = groundBelow(dim, up(arcPoint(c, (k2 + 0.5) * (CUR_SWEEP / 8)), 2));
        if (foes.some((e) => distXZ(e.location, p) < 1.4) || distXZ(caster.location, p) < 1.6) continue;
        const x = Math.floor(p.x), y = Math.floor(p.y), z = Math.floor(p.z);
        if (tb.column(x, y, z, ED03.barrierHeight) > 0) barriers.push({ x, y, z });
        particle(dim, "ed_tide_glint", up(p, 1.5));
      }
    }
  });
  scene.at(tSpiral + 12, () => currents.forEach((c) => c.a.state(CUR.ice)));
  scene.at(tRoar, () => {
    dragon.state(D2.roar);
    particle(dim, "ed_tide_frost_ring", up(G, 0.3));
    ring(dim, "ed_tide_mist", up(G, 1), Rc, 6);
  });
  let crown;
  scene.at(tCrown, () => {
    crown = scene.spawn("ed_tide_crown", G, { state: CROWN.assemble, size: Rc / CROWN_R });
    sound(dim, "ed_tide_crown", G, 1.5);
    tb.place(up(G, 3), LIGHT);
    ring(dim, "ed_tide_rune", up(G, 2), Rc, 6);
  });
  scene.at(tCrown + 24, () => crown?.state(CROWN.hold));
  scene.at(tRise, () => {
    currents.forEach((c) => {
      c.a.state(CUR.rise);
      particle(dim, "ed_tide_glint", arcPoint(c, 80, 3));
    });
    for (const b of barriers) tb.removeColumn(b.x, b.y, b.z, ED03.barrierHeight);
  });
  scene.at(tRise + 16, () => currents.forEach((c) => scene.despawn(c.a)));
  scene.at(tRoar + T7.roar, () => dragon.state(D2.idle));
  let warn;
  scene.at(tHit - 20, () => {
    warn = scene.spawn("telegraph", G, { kind: 2, size: Rc + ED03.finalExtra, state: 1 });
  });
  scene.at(tStrike, () => dragon.state(D2.attack_b));
  scene.at(tHit, () => {
    warn?.state(2);
    const imp = groundBelow(dim, tailTip(70));
    sound(dim, "ed_tide_impact", imp, 1.5);
    particle(dim, "ed_tide_splash", imp);
    particle(dim, "fx_shock", up(imp, 0.2));
  });
  for (let w = 0; w < 3; w++) {
    scene.at(tHit + w * WAVE_GAP, () => {
      crown?.state(CROWN.frac1 + w);
      sound(dim, "ed_tide_fracture", G, 1.4, 0.9 + w * 0.12);
      ring(dim, "ed_tide_splinter", up(G, 2 + w), Rc, 8, w * 20);
      launchShards(w);
    });
  }
  function launchShards(w) {
    const foes = hostiles(dim, G, Rc + 3, caster, ED03.maxTargets);
    const goals = foes.map((e) => {
      const v2 = flat(sub(e.location, G));
      return { e, at: e.location, dir: Math.hypot(v2.x, v2.z) > 0.3 ? norm(v2) : fwd };
    });
    if (!goals.length) for (let k2 = 0; k2 < 4; k2++) {
      const at = polar(G, 1.2, k2 * 90 + w * 30);
      goals.push({ at, dir: norm(flat(sub(polar(G, 1, k2 * 90 + w * 30), G))) });
    }
    for (const g of goals) {
      const start = up(add(G, mul(g.dir, Rc)), 2.5 + w * 0.8);
      const target = () => up(g.e && isAlive(g.e) ? g.e.location : g.at, 1);
      const s = scene.spawn("ed_tide_shard", start, { state: SHARD.launch, size: 1.3, yaw: yawOf(sub(target(), start)) });
      scene.span(scene.tick + 1, scene.tick + 1 + ED03.shardFlight, (p) => {
        const to = target();
        s.move(lerp(start, to, easeIn(p) * 0.85 + p * 0.15), yawOf(flat(sub(to, start))));
      });
      scene.after(ED03.shardFlight + 1, () => {
        s.state(SHARD.hit);
        const at = target();
        particle(dim, "ed_tide_splinter", at);
        sound(dim, "ed_tide_shatter", at, 0.9, 0.9 + w * 0.15);
        if (g.e && isAlive(g.e)) damage(g.e, ED03.shardDamage[w], caster);
        for (const e of hostiles(dim, at, 1.4, caster)) if (e !== g.e) damage(e, ED03.shardDamage[w] * 0.5, caster);
      });
      scene.after(ED03.shardFlight + 8, () => scene.despawn(s));
    }
  }
  scene.at(tShatter, () => {
    for (const f of frozen.values()) {
      f.release();
      f.ice.state(FROZEN.shatter);
      const ice = f.ice;
      scene.after(8, () => scene.despawn(ice));
      if (isAlive(f.e)) {
        effect(f.e, "slowness", ED03.thawSlowTicks, ED03.thawSlowAmp);
        particle(dim, "ed_tide_splinter", up(f.e.location, 1));
      }
    }
  });
  const tFinal = tShatter + 6;
  scene.at(tFinal, () => {
    warn?.state(3);
    sound(dim, "ed_tide_finale", G, 1.6);
    particle(dim, "ed_tide_shock", up(G, 0.3));
    particle(dim, "fx_flash", up(G, 2));
    burst(dim, "ed_tide_splinter", up(G, 2), Rc * 0.6, 8);
    ring(dim, "ed_tide_mist", up(G, 0.8), Rc, 8);
    for (const e of hostiles(dim, G, Rc + ED03.finalExtra, caster)) {
      damage(e, ED03.finalDamage, caster);
      knockback(e, G, ED03.finalKnockH, ED03.finalKnockV);
    }
  });
  scene.at(tFinal + 6, () => {
    if (crown) scene.despawn(crown);
  });
  scene.at(tFinal + 8, () => {
    if (warn) scene.despawn(warn);
  });
  const tDepart = tFinal + 4;
  scene.at(tDepart, () => dragon.state(D2.depart));
  scene.every(6, (el) => particle(dim, "ed_tide_mist", up(sub(L3, mul(rt, -2 + el * 0.2)), 2 + el * 0.08)), tDepart + 6, tDepart + T7.depart);
  scene.at(tDepart + 20, () => ring(dim, "ed_tide_splash", up(L3, 0.3), 3.5, 6));
  scene.at(tDepart + T7.depart, () => scene.despawn(dragon));
  scene.endAt(tDepart + T7.depart + 4);
});

// src/config/ed04.ts
var ED04 = {
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  snap: 12,
  // ---- Stage I: The Fourfold Ascent
  /** Height of the parting cloud bank above the battlefield (blocks). */
  cloudHeight: 19,
  /** Height the dragon emerges at, and the start / end radius of its descending spiral. */
  descentHeight: 17,
  spiralR0: 4,
  /** Degrees the descent spiral turns before the first pass begins. */
  spiralTurn: 290,
  // ---- Stage II: The Skyborne Symphony (four passes along a pentagram, hairpin turns between)
  /** Radius of the pentagram the passes are drawn on (blocks around the focus). */
  passRadius: 9,
  /** Height of the dragon's flight origin above the ground during passes (body rides ~0.85 higher). */
  passHeight: 1.3,
  /** Sideways S-bend of each pass (blocks). */
  passBend: 2,
  /** Flight speed during passes and during the banked hairpin turns (blocks/second). */
  passSpeed: 24,
  turnSpeed: 24,
  /** Size of the climbing hairpin loop at each pentagram vertex (blocks). */
  hairpinSize: 2.6,
  hairpinLift: 3,
  /** Yaw change per tick above which the dragon banks into the turn. */
  bankRate: 2,
  /** Wing-slash: radius around the flight path, damage and sideways knockback of each pass. */
  slashRadius: 3.4,
  slashDamage: 7,
  slashKnockH: 1.1,
  slashKnockV: 0.35,
  /** Air-current ribbons: segment length (blocks) and how long each stays suspended (ticks). */
  ribbonSeg: 4.2,
  ribbonLife: 80,
  /** Wind vortex born where two live ribbons cross. */
  maxVortices: 4,
  vortexMerge: 3.5,
  vortexRadius: 4.2,
  /** Ticks a vortex stays active after spinning up, and how often it pulls / damages. */
  vortexTicks: 40,
  vortexEvery: 8,
  vortexDamage: 2.5,
  /** Horizontal pull strength toward the vortex eye per pulse. */
  vortexPull: 0.45,
  /** Final burst of each vortex: damage and upward launch. */
  vortexBurstDamage: 6,
  vortexLaunch: 0.9,
  // ---- Stage III: Supersonic Cadenza
  /** Hold point of the full-spread beat: height above ground and distance behind the formation. */
  holdHeight: 13,
  holdBack: 15,
  climbSpeed: 24,
  holdTicks: 16,
  /** Dive: duration (ticks), where it bottoms out before the focus and how far it runs past it. */
  diveTicks: 20,
  diveLead: 7,
  diveRun: 9,
  /** Direct contact of the high-speed dive. */
  diveContactRadius: 2.6,
  diveDamage: 10,
  diveKnockH: 1.4,
  diveKnockV: 0.5,
  /** Delayed shockwaves along the route: count, radius, damage, timing and outward knockback. */
  shockCount: 5,
  shockRadius: 3.6,
  shockDamage: 8,
  /** Ticks after the dragon passes before the first shock detonates, and the gap between shocks. */
  shockDelay: 10,
  shockStagger: 4,
  shockKnockH: 1.9,
  shockKnockV: 0.6,
  /** An enemy can be struck by at most this many shockwaves. */
  maxShockHits: 2,
  /** Braking flare, landing and the perched beat before the dissolution (ticks). */
  flareTicks: 12,
  landTicks: 20,
  perchTicks: 8
};

// src/spells/ed04_aether_raptor.ts
var ACTOR5 = "dragon_air";
var S5 = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  glide: 4,
  turn_l: 5,
  turn_r: 6,
  roll: 7,
  stoop: 8,
  flare: 9,
  land: 10,
  attack_a: 11,
  attack_b: 12,
  power: 13,
  react: 14,
  rest: 15,
  depart: 16,
  flutter: 17
};
var ARRIVE_TICKS = 48;
var ATTACK_A_HIT2 = 6;
var ATTACK_B_HIT = 7;
var DEPART_TICKS = 32;
var BODY_DY = 0.85;
var RIBBON_LEN = 4.5;
var CLOUD = { form: 1, part: 2, fade: 3 };
var RIBBON = { draw: 1, hold: 2, fray: 3 };
var VORTEX = { form: 1, hold: 2, burst: 3 };
var SHOCK = { charge: 1, blast: 2 };
function cross2(a, b, c, d) {
  const r = { x: b.x - a.x, z: b.z - a.z }, s = { x: d.x - c.x, z: d.z - c.z };
  const den = r.x * s.z - r.z * s.x;
  if (Math.abs(den) < 1e-6) return void 0;
  const t = ((c.x - a.x) * s.z - (c.z - a.z) * s.x) / den;
  const u = ((c.x - a.x) * r.z - (c.z - a.z) * r.x) / den;
  if (t < 0 || t > 1 || u < 0 || u > 1) return void 0;
  return { x: a.x + r.x * t, y: (a.y + c.y) / 2, z: a.z + r.z * t };
}
function pathLen(pts) {
  let L3 = 0, prev = spline(pts, 0);
  for (let i = 1; i <= 16; i++) {
    const p = spline(pts, i / 16);
    L3 += Math.hypot(p.x - prev.x, p.y - prev.y, p.z - prev.z);
    prev = p;
  }
  return L3;
}
var ed04_aether_raptor_default = defineSpell("ed04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, ED04.snap);
  const gy = (p) => groundBelow(dim, up(p, 6), 30).y;
  let toCaster = flat(sub(caster.location, center));
  if (Math.hypot(toCaster.x, toCaster.z) < 0.5) toCaster = mul(aim.forward, -1);
  toCaster = norm(toCaster);
  const baseAng = Math.atan2(toCaster.z, toCaster.x) * 180 / Math.PI + 36;
  const legs = [];
  let cursor = 8;
  const addLeg = (kind, ticks, at, idx = 0, pilot) => {
    const leg = { from: cursor, to: cursor + Math.max(4, Math.round(ticks)), at, kind, idx, pilot };
    legs.push(leg);
    cursor = leg.to;
    return leg;
  };
  const splineLeg = (kind, pts, speed, idx = 0, pilot, ease) => addLeg(kind, pathLen(pts) / speed * 20, (p) => spline(pts, ease ? ease(p) : p), idx, pilot);
  const verts = [0, 1, 2, 3, 4].map((i) => {
    const p = polar(center, ED04.passRadius, baseAng + i * 72);
    return { x: p.x, y: gy(p) + ED04.passHeight, z: p.z };
  });
  const order = [0, 2, 4, 1, 3];
  const passes = [];
  for (let k2 = 0; k2 < 4; k2++) {
    const a = verts[order[k2]], b = verts[order[k2 + 1]];
    const side = mul(right(sub(b, a)), ED04.passBend * (k2 % 2 ? -1 : 1));
    passes.push([a, add(lerp(a, b, 0.33), side), add(lerp(a, b, 0.66), mul(side, -1)), b]);
  }
  const a0 = baseAng;
  const v0 = verts[0];
  const arriveLeg = addLeg("arrive", ARRIVE_TICKS, (p) => {
    const e = smooth(p);
    const ang = a0 - ED04.spiralTurn * (1 - e);
    const r = ED04.spiralR0 + (ED04.passRadius - ED04.spiralR0) * e;
    const q = polar(center, r, ang);
    return { x: q.x, y: v0.y + (ED04.descentHeight - ED04.passHeight) * Math.pow(1 - p, 1.3), z: q.z };
  }, 0, S5.arrive);
  const passLegs = [];
  for (let k2 = 0; k2 < 4; k2++) {
    passLegs.push(splineLeg("pass", passes[k2], ED04.passSpeed, k2));
    if (k2 < 3) {
      const P6 = passes[k2][3];
      const dIn = norm(flat(sub(P6, spline(passes[k2], 0.94))));
      const dOut = norm(flat(sub(spline(passes[k2 + 1], 0.06), P6)));
      const outward = norm(sub(dIn, dOut));
      const hs = ED04.hairpinSize;
      splineLeg("turn", [
        P6,
        up(add(P6, mul(dIn, hs * 1.4)), ED04.hairpinLift * 0.7),
        up(add(P6, mul(outward, hs * 2.2)), ED04.hairpinLift),
        up(sub(P6, mul(dOut, hs * 1.4)), ED04.hairpinLift * 0.6),
        P6
      ], ED04.turnSpeed, k2);
    }
  }
  const lastP = passes[3][3];
  let diveDir = norm(right(toCaster));
  if (distXZ(sub(center, mul(diveDir, ED04.holdBack)), lastP) > distXZ(add(center, mul(diveDir, ED04.holdBack)), lastP)) diveDir = mul(diveDir, -1);
  const g0 = center.y;
  const hold = up(sub(center, mul(diveDir, ED04.holdBack)), ED04.holdHeight);
  const lowA = { ...sub(center, mul(diveDir, ED04.diveLead)), y: gy(sub(center, mul(diveDir, ED04.diveLead))) + ED04.passHeight * 0.8 };
  const lowM = { ...center, y: g0 + ED04.passHeight * 0.8 };
  const lowB = { ...add(center, mul(diveDir, ED04.diveRun)), y: gy(add(center, mul(diveDir, ED04.diveRun))) + ED04.passHeight };
  const flareEnd = up(add(center, mul(diveDir, ED04.diveRun + 4)), 2.6);
  const landAt = groundBelow(dim, up(add(center, mul(diveDir, ED04.diveRun + 6)), 6), 30);
  const climbLeg = splineLeg("climb", [lastP, up(lerp(lastP, hold, 0.5), 4), hold], ED04.climbSpeed);
  const holdLeg = addLeg("hold", ED04.holdTicks, (p) => add(hold, { x: -diveDir.x * 1.2 * smooth(p), y: 0.8 * Math.sin(p * Math.PI), z: -diveDir.z * 1.2 * smooth(p) }), 0, S5.power);
  const holdEnd = holdLeg.at(1);
  const divePts = [holdEnd, lerp(holdEnd, lowA, 0.6), lowA, lowM, lowB];
  const diveLeg = addLeg("dive", ED04.diveTicks, (p) => spline(divePts, Math.pow(p, 1.45)), 0, S5.stoop);
  const flareLeg = addLeg("flare", ED04.flareTicks, (p) => lerp(lowB, flareEnd, easeOut(p)), 0, S5.flare);
  const landLeg = addLeg("land", ED04.landTicks, (p) => lerp(flareEnd, landAt, smooth(p)), 0, S5.land);
  const tFlightEnd = landLeg.to;
  const tDepart = tFlightEnd + ED04.perchTicks;
  const diveYaw = yawOf(diveDir);
  const posAt = (t) => {
    if (t <= legs[0].from) return legs[0].at(0);
    for (const l of legs) if (t < l.to) return l.at((t - l.from) / Math.max(1, l.to - l.from));
    return legs[legs.length - 1].at(1);
  };
  const legAt = (t) => legs.find((l) => t >= l.from && t < l.to);
  const cloudA = scene.spawn("ed_air_cloud", up(center, ED04.cloudHeight), { yaw: yawOf(toCaster) + 90, size: 1.4, state: CLOUD.form });
  const cloudB = scene.spawn("ed_air_cloud", up(polar(center, 10, baseAng + 180), ED04.cloudHeight + 4), { yaw: yawOf(toCaster), size: 0.9, state: CLOUD.form });
  sound(dim, "ed_air_cloud", up(center, ED04.cloudHeight), 1.4);
  scene.at(2, () => burst(dim, "ed_air_cloud", up(center, ED04.cloudHeight), 5, 6));
  scene.at(8, () => {
    cloudA.state(CLOUD.part);
    cloudB.state(CLOUD.part);
    burst(dim, "ed_air_motes", up(center, ED04.cloudHeight - 3), 3, 3);
  });
  scene.at(arriveLeg.to + 4, () => {
    cloudA.state(CLOUD.fade);
    cloudB.state(CLOUD.fade);
  });
  scene.at(arriveLeg.to + 26, () => {
    scene.despawn(cloudA);
    scene.despawn(cloudB);
  });
  const dragon = scene.spawn(ACTOR5, posAt(8), { yaw: yawOf(sub(posAt(9), posAt(8))), state: S5.arrive });
  scene.at(9, () => burst(dim, "ed_air_feather", up(posAt(9), 1), 1.5, 3));
  scene.at(arriveLeg.from + 30, () => burst(dim, "ed_air_feather", up(posAt(scene.tick), 1), 2, 4));
  let cur = S5.arrive, lockUntil = arriveLeg.to, dwellUntil = 0, yaw = dragon.yaw, dyawF = 0;
  let legIdx = -1;
  const setState = (n, lock = 0) => {
    if (n !== cur) {
      dragon.state(n);
      cur = n;
      dwellUntil = scene.tick + 6;
    }
    if (lock) lockUntil = scene.tick + lock;
  };
  const passHits = [/* @__PURE__ */ new Set(), /* @__PURE__ */ new Set(), /* @__PURE__ */ new Set(), /* @__PURE__ */ new Set()];
  const diveHits = /* @__PURE__ */ new Set();
  const segs = [];
  const vortexAt = [];
  let anchor;
  scene.every(1, () => {
    const t = scene.tick;
    const pos = posAt(t);
    const nxt = posAt(t + 1);
    const d = sub(nxt, pos);
    const leg = legAt(t);
    if (leg && leg.kind !== "flare" && leg.kind !== "land" && Math.hypot(d.x, d.z) > 0.04) {
      const ny = yawOf(d);
      dyawF = dyawF * 0.55 + angleDelta(yaw, ny) * 0.45;
      yaw = ny;
    } else if (leg && (leg.kind === "flare" || leg.kind === "land")) {
      yaw = diveYaw;
      dyawF = 0;
    }
    dragon.move(pos, yaw);
    if (!leg) return;
    const li = legs.indexOf(leg);
    if (li !== legIdx) {
      legIdx = li;
      onLegStart(leg, pos);
    }
    if (leg.pilot !== void 0) {
      if (t >= lockUntil) setState(leg.pilot);
    } else if (t >= lockUntil && t >= dwellUntil) {
      let want = S5.glide;
      if (dyawF > ED04.bankRate) want = S5.turn_r;
      else if (dyawF < -ED04.bankRate) want = S5.turn_l;
      else if (d.y > 0.12) want = S5.move;
      setState(want);
    }
    if (leg.kind === "pass") passTick(leg, pos, d);
    if (leg.kind === "dive") diveTick(pos);
  }, arriveLeg.from, tFlightEnd);
  function onLegStart(leg, pos) {
    if (leg.kind === "pass") {
      const talon = leg.idx % 2 === 1;
      setState(S5.glide);
      scene.after(1, () => setState(talon ? S5.attack_b : S5.attack_a, 14));
      sound(dim, "ed_air_ribbon", pos, 1.1, 0.9 + leg.idx * 0.07);
      sound(dim, talon ? "ed_air_chirr" : "ed_air_whistle", pos, 1, 1 + leg.idx * 0.05);
      anchor = { ...pos };
    } else if (leg.kind === "turn") {
      sound(dim, "ed_air_flap", pos, 1, 1.1);
      if (leg.idx === 1) setState(S5.roll, 18);
      burst(dim, "ed_air_feather", up(pos, 1), 1.2, 2);
    } else if (leg.kind === "climb") {
      startCadenza();
    } else if (leg.kind === "hold") {
      dragon.skin(1);
      sound(dim, "ed_air_call", pos, 1.6);
      ring(dim, "ed_air_spark", up(pos, 1), 4, 8);
      burst(dim, "ed_air_motes", up(pos, 1), 4, 4);
    } else if (leg.kind === "dive") {
      sound(dim, "ed_air_dive", pos, 1.6);
      particle(dim, "ed_air_boom", up(pos, 1));
      burst(dim, "ed_air_feather", up(pos, 1), 1.5, 3);
    } else if (leg.kind === "flare") {
      sound(dim, "ed_air_flare", pos, 1.3);
      burst(dim, "ed_air_gust", up(pos, 1), 1, 3);
      burst(dim, "ed_air_feather", up(pos, 1.5), 2, 5);
    } else if (leg.kind === "land") {
      dragon.skin(0);
      scene.at(leg.to - 4, () => {
        particle(dim, "fx_dust", landAt);
        particle(dim, "ed_air_gust", up(landAt, 0.3));
      });
    }
  }
  function passTick(leg, pos, d) {
    const k2 = leg.idx;
    if (anchor && (distXZ(anchor, pos) >= ED04.ribbonSeg || scene.tick === leg.to - 1)) {
      if (distXZ(anchor, pos) > 1.2) layRibbon(anchor, pos, k2);
      anchor = { ...pos };
    }
    const hitFrame = k2 % 2 === 1 ? ATTACK_B_HIT : ATTACK_A_HIT2;
    if (scene.tick < leg.from + 1 + hitFrame || (scene.tick - leg.from) % 2) return;
    const side = right(d);
    for (const e of hostiles(dim, pos, ED04.slashRadius + 2.5, caster)) {
      if (passHits[k2].has(e.id)) continue;
      const l = e.location;
      if (distXZ(l, pos) > ED04.slashRadius || Math.abs(l.y - pos.y) > 4) continue;
      passHits[k2].add(e.id);
      if (!damage(e, ED04.slashDamage, caster)) continue;
      const s = dot(sub(l, pos), side) >= 0 ? 1 : -1;
      shove(e, mul(side, s), ED04.slashKnockH, ED04.slashKnockV);
      particle(dim, "ed_air_streak", up(l, 1));
      particle(dim, "ed_air_spark", up(l, 1.2));
      sound(dim, "ed_air_slash", l, 0.9, 0.95 + k2 * 0.06);
    }
  }
  function layRibbon(a, b, k2) {
    const len2 = distXZ(a, b);
    const mid = up(lerp(a, b, 0.5), BODY_DY);
    const rib = scene.spawn("ed_air_ribbon", mid, { yaw: yawOf(sub(b, a)), size: len2 / RIBBON_LEN * 1.08, state: RIBBON.draw });
    scene.after(10, () => rib.state(RIBBON.hold));
    scene.after(ED04.ribbonLife, () => rib.state(RIBBON.fray));
    scene.after(ED04.ribbonLife + 17, () => scene.despawn(rib));
    particle(dim, "ed_air_streak", mid);
    const seg = { a: { ...a }, b: { ...b }, pass: k2, born: scene.tick };
    for (const o of segs) {
      if (o.pass === k2 || scene.tick - o.born > ED04.ribbonLife) continue;
      const x = cross2(seg.a, seg.b, o.a, o.b);
      if (!x || vortexAt.length >= ED04.maxVortices || vortexAt.some((v2) => distXZ(v2, x) < ED04.vortexMerge)) continue;
      vortexAt.push(x);
      spawnVortex(x);
    }
    segs.push(seg);
  }
  function spawnVortex(x) {
    const at = groundBelow(dim, up(x, 4), 20);
    const vx = scene.spawn("ed_air_vortex", at, { size: 1, state: VORTEX.form, yaw: Math.random() * 360 });
    sound(dim, "ed_air_vortex", at, 1.3);
    ring(dim, "ed_air_gust", up(at, 0.5), 2.5, 6);
    const on = scene.tick + 8;
    scene.at(on, () => vx.state(VORTEX.hold));
    scene.every(ED04.vortexEvery, () => {
      particle(dim, "ed_air_streak", up(at, 2));
      for (const e of hostiles(dim, at, ED04.vortexRadius, caster)) {
        const pull = flat(sub(at, e.location));
        if (Math.hypot(pull.x, pull.z) > 0.6) shove(e, pull, ED04.vortexPull, 0.12);
        damage(e, ED04.vortexDamage, caster);
      }
    }, on, on + ED04.vortexTicks);
    scene.at(on + ED04.vortexTicks, () => {
      vx.state(VORTEX.burst);
      sound(dim, "ed_air_boom", at, 0.8, 1.3);
      burst(dim, "ed_air_feather_burst", up(at, 2.5), 1.5, 2);
      particle(dim, "ed_air_shock", up(at, 0.3));
      for (const e of hostiles(dim, at, ED04.vortexRadius + 0.8, caster)) {
        damage(e, ED04.vortexBurstDamage, caster);
        knockback(e, at, 0.4, ED04.vortexLaunch);
      }
    });
    scene.at(on + ED04.vortexTicks + 13, () => scene.despawn(vx));
  }
  const shocks = [];
  const shockHits = /* @__PURE__ */ new Map();
  const s0 = dot(sub(lowA, center), diveDir), s1 = dot(sub(lowB, center), diveDir);
  function startCadenza() {
    for (let i = 0; i < ED04.shockCount; i++) {
      const f = ED04.shockCount === 1 ? 0.5 : i / (ED04.shockCount - 1);
      const s = s0 + (s1 - s0) * (0.1 + 0.85 * f);
      const p = add(center, mul(diveDir, s));
      const at = groundBelow(dim, up(p, 6), 30);
      shocks.push({ at, s, tele: scene.spawn("telegraph", at, { kind: 2, size: ED04.shockRadius, state: 4 }), fired: false });
    }
    line(dim, "ed_air_motes", up(shocks[0].at, 0.5), up(shocks[shocks.length - 1].at, 0.5), 4);
  }
  let passOrder = 0;
  function diveTick(pos) {
    const sNow = dot(sub(pos, center), diveDir);
    for (const sh of shocks) {
      if (sh.fired || sNow < sh.s) continue;
      sh.fired = true;
      const order2 = passOrder++;
      const knot = scene.spawn("ed_air_shock", sh.at, { yaw: diveYaw, size: 1.4, state: SHOCK.charge });
      particle(dim, "ed_air_boom", up(sh.at, 1.2));
      const tBlast = Math.max(diveLeg.to + 2, scene.tick + ED04.shockDelay) + order2 * ED04.shockStagger;
      scene.at(tBlast - 8, () => sh.tele?.state(2));
      scene.at(tBlast, () => detonate(sh.at, knot, sh.tele));
    }
    for (const e of hostiles(dim, pos, ED04.diveContactRadius + 2, caster)) {
      if (diveHits.has(e.id) || distXZ(e.location, pos) > ED04.diveContactRadius || Math.abs(e.location.y - pos.y) > 3.5) continue;
      diveHits.add(e.id);
      if (damage(e, ED04.diveDamage, caster)) {
        knockback(e, pos, ED04.diveKnockH, ED04.diveKnockV);
        particle(dim, "ed_air_spark", up(e.location, 1));
      }
    }
    if (scene.tick % 2 === 0) particle(dim, "ed_air_streak", up(pos, BODY_DY));
  }
  function detonate(at, knot, tele) {
    knot.state(SHOCK.blast);
    if (tele) {
      tele.state(3);
      scene.after(8, () => scene.despawn(tele));
    }
    scene.after(13, () => scene.despawn(knot));
    sound(dim, "ed_air_boom", at, 1.4);
    particle(dim, "ed_air_shock", up(at, 0.25));
    particle(dim, "ed_air_boom", up(at, 1.5));
    burst(dim, "ed_air_gust", up(at, 0.6), 1.5, 3);
    for (const e of hostiles(dim, at, ED04.shockRadius, caster)) {
      const n = shockHits.get(e.id) ?? 0;
      if (n >= ED04.maxShockHits) continue;
      shockHits.set(e.id, n + 1);
      if (!damage(e, ED04.shockDamage, caster)) continue;
      const rel = flat(sub(e.location, at));
      const along = dot(rel, diveDir);
      const out = sub(rel, mul(diveDir, along));
      const dir = Math.hypot(out.x, out.z) > 0.2 ? out : right(diveDir);
      shove(e, dir, ED04.shockKnockH, ED04.shockKnockV);
    }
  }
  scene.at(tFlightEnd, () => {
    dragon.move(landAt, diveYaw);
    dragon.state(S5.idle);
    sound(dim, "ed_air_chirr", landAt, 1);
  });
  scene.at(tDepart, () => {
    dragon.state(S5.depart);
    sound(dim, "ed_air_depart", up(landAt, 2), 1.3);
  });
  scene.at(tDepart + 10, () => {
    burst(dim, "ed_air_feather_burst", up(landAt, 3), 2, 3);
    burst(dim, "ed_air_feather", up(landAt, 3), 3, 4);
  });
  scene.at(tDepart + 20, () => {
    burst(dim, "ed_air_cloud", up(landAt, 4), 2, 2);
    burst(dim, "ed_air_motes", up(landAt, 4), 3, 3);
  });
  scene.endAt(tDepart + DEPART_TICKS + 4);
});

// src/config/ed05.ts
var ED05 = {
  /** How far from the aim point the monument snaps onto the nearest enemy. */
  focusSnap: 14,
  /** Radius around the monument in which the spell looks for enemies. */
  areaRadius: 22,
  // ---- Phase I: The Buried Testament
  /** Distance of the four rise sites from the centre (they sit on the diagonals of the caster's view). */
  riseRadius: 11,
  /** First inscription column, and the stagger between the four sites. */
  inscribeAt: 0.2,
  riseStagger: 0.25,
  /** Tablets break out of the ground this long after their inscription began to fall. */
  riseDelay: 1.8,
  /** Rising slab: shove + damage around its site when it breaks the surface. */
  riseDamage: 5,
  riseRadiusHit: 4,
  riseKnock: 1.3,
  /** Tablets lift and orbit into the memorial from this time, over gatherTime seconds. */
  gatherAt: 5,
  gatherTime: 3,
  /** Height of the tablets' lower edge above the ground in the memorial (blocks). */
  memorialHeight: 9.5,
  /** Total turn of the monument while it assembles and turns (degrees) and when it halts. */
  memorialTurn: 225,
  haltAt: 8.8,
  /** The memorial locks: grinding shock under the monument. */
  lockDamage: 7,
  lockRadius: 10,
  lockSlowTicks: 50,
  lockSlowAmp: 1,
  // ---- Phase II: The Fossils That Remember
  /** Emergence of each skeleton (nature, heat, tide, air); its tablet awakens awakenLead earlier. */
  emergeAt: { nature: 9, heat: 9.8, tide: 10.6, air: 11.4 },
  awakenLead: 0.7,
  /** Where the skeletons land, measured from the monument centre (blocks, outward from their tablet). */
  landDistance: { nature: 12.5, heat: 11.5, tide: 10.5 },
  // Nature (titanosaur): forelimb slam with radiating stone spikes, then a low neck sweep
  slamDamage: 14,
  slamRadius: 4.2,
  slamKnock: 1.4,
  /** Spikes rise along this many shock lines from the slam point, spikesPerLine each, spaced (blocks). */
  slamLines: 3,
  spikesPerLine: 3,
  spikeSpacing: 2.6,
  spikeFirst: 3,
  spikeDamage: 7,
  spikeRadius: 1.9,
  spikeLift: 0.7,
  /** Neck sweep: frontal sector (half angle, degrees) between minReach and maxReach blocks of the body. */
  sweepDamage: 12,
  sweepHalfAngle: 75,
  sweepMinReach: 5,
  sweepMaxReach: 19,
  sweepKnock: 1.6,
  // Heat (carnotaur): two telegraphed charges that leave burning trackways
  /** Ticks the lane is shown before each charge. */
  laneWarn: 1,
  /** Half length of each lane through the centre region (blocks). */
  laneReach: 11,
  /** Second lane passes this far beside the centre. */
  laneOffset: 3,
  chargeDamage: 11,
  chargeRadius: 2.3,
  chargeKnock: 1.5,
  /** Burning trail: damage every burnEvery ticks to enemies within burnRadius of the scorched track. */
  burnDamage: 2.5,
  burnEvery: 10,
  burnRadius: 1.6,
  burnSeconds: 3,
  burnFireSeconds: 3,
  // Tide (spinosaur): tail lash and sail flare throwing fans of ice crystals
  tideWalk: 1.2,
  fanDamage: 10,
  /** Crystal fans: size multiplier (1 = 2.9 block reach), sector half angle, slowness. */
  fanSize: 2.6,
  fanHalfAngle: 55,
  fanSlowTicks: 60,
  fanSlowAmp: 2,
  flareDamage: 11,
  // Air (microraptor): three low sweeps; each downstroke sends a wind shockwave ring
  flySpeed: 19,
  passRadius: 12,
  passHeight: 4,
  cruiseHeight: 8,
  ringDamage: 6,
  ringRadius: 3.8,
  ringKnock: 1.5,
  /** Rings only fire when the raptor is within this horizontal distance of the centre. */
  ringReach: 11,
  // ---- Phase III: The Eternal Imprint
  phase3At: 23.6,
  /** Fan formation above the battlefield: radius from the centre, lower-edge height and fan angles. */
  fanRadius: 10,
  formationHeight: { nature: 15, heat: 13, tide: 13, air: 15 },
  formationAngle: { heat: 54, nature: 18, air: -18, tide: -54 },
  formationTime: 2,
  /** Each imprint lands at these times; the projection warns warnTime seconds before. */
  projectAt: { nature: 26, heat: 27.6, tide: 29.2, air: 30.8 },
  projectWarn: 1.2,
  allAt: 32.6,
  /** Imprint size multiplier (1 = 15.6 x 11.7 blocks). */
  imprintSize: 1,
  /** Nature: root-and-stone eruption along the sauropod outline. */
  p3SpikeDamage: 12,
  p3SpikeRadius: 2.2,
  /** Heat: horned heat-brand burns for brandSeconds. */
  brandDamage: 4,
  brandEvery: 8,
  brandRadius: 2.2,
  brandSeconds: 2,
  brandFireSeconds: 4,
  /** Tide: sail-shaped ice fan. */
  p3FanDamage: 15,
  p3FanSize: 4.2,
  p3FanSlowTicks: 80,
  p3FanSlowAmp: 3,
  /** Air: four-winged gale. */
  galeDamage: 12,
  galeRadius: 4.5,
  galeKnock: 2,
  galeLevitate: 16,
  /** All four together. */
  finaleDamage: 22,
  finaleRadius: 9,
  finaleKnock: 1.8,
  fractureAt: 34.8,
  endAt: 37.2,
  /** Seconds between replays of the museum hush bed. */
  hushEvery: 4.5
};

// src/spells/_ed05_assets.ts
var ED5_SKEL = { "nature": { "actor": "ed5_skel_nature", "scale": 2, "states": { "hidden": 0, "emerge": 1, "idle": 2, "move": 3, "attack_a": 4, "attack_b": 5, "return": 6, "turn_l": 7, "turn_r": 8, "power": 9 }, "emerge": 2.6, "ret": 2.2, "yawOff": 180, "living": { "walkSpeed": 1.5, "turnRate": 20, "attackA": 3.2, "hitA": 2.2, "attackB": 2.4, "hitB": 1.35, "power": 2.6 } }, "heat": { "actor": "ed5_skel_heat", "scale": 1.85, "states": { "hidden": 0, "emerge": 1, "idle": 2, "walk": 3, "charge": 4, "skid": 5, "attack_a": 6, "attack_b": 7, "roar": 8, "return": 9, "turn_l": 10, "turn_r": 11, "move": 12 }, "emerge": 2.4, "ret": 2, "yawOff": 180, "living": { "runSpeed": 10.021, "walkSpeed": 3.533, "turnRate": 225, "turn": 0.8, "skid": 0.7, "roar": 1.4, "attackA": 1.2, "hitA": 0.55, "attackB": 1.3, "hitB": 0.6 } }, "tide": { "actor": "ed5_skel_tide", "scale": 2, "states": { "hidden": 0, "emerge": 1, "idle": 2, "move": 3, "attack_a": 4, "attack_b": 5, "attack_c": 6, "roar": 7, "return": 8, "turn_l": 9, "turn_r": 10 }, "emerge": 2.4, "ret": 2, "yawOff": 180, "living": { "walkSpeed": 2.5, "attackA": 1.5, "hitsA": [0.5, 1.05], "attackB": 1.7, "hitB": 0.9, "attackC": 1.1, "hitC": 0.45, "roar": 1.4, "turn": 1 } }, "air": { "actor": "ed5_skel_air", "scale": 1.5, "states": { "hidden": 0, "emerge": 1, "idle": 2, "move": 3, "glide": 4, "flutter": 5, "stoop": 6, "attack_a": 7, "attack_b": 8, "roll": 9, "flare": 10, "return": 11, "turn_l": 12, "turn_r": 13 }, "emerge": 2, "ret": 1.8, "yawOff": 0, "living": { "flyDy": -22, "flap": 0.8, "attackA": 0.7, "hitA": 0.3, "roll": 1, "flare": 0.5 } } };
var ED5_TABLET = { "actors": { "nature": "ed5_tablet_nature", "heat": "ed5_tablet_heat", "tide": "ed5_tablet_tide", "air": "ed5_tablet_air" }, "states": { "hidden": 0, "rise": 1, "stand": 2, "memorial": 3, "awaken": 4, "empty": 5, "receive": 6, "formation": 7, "aim": 8, "project": 9, "project_all": 10, "fracture": 11 }, "len": { "rise": 2.2, "memorial": 0.6, "awaken": 1.2, "empty": 0.6, "receive": 0.9, "formation": 2, "fracture": 1.8 }, "tilt": 60, "relief": [0, 4.5, -0.7], "width": 12, "height": 9, "front": 0.625, "back": 0.75 };
var ED5_IMPRINT = { "actors": { "nature": "ed5_imprint_nature", "heat": "ed5_imprint_heat", "tide": "ed5_imprint_tide", "air": "ed5_imprint_air" }, "scale": 1.3, "states": { "hidden": 0, "warn": 1, "brand": 2, "pulse": 3, "fade": 4 }, "outline": { "nature": { "rim": [[6.3, -2.23], [-6.3, 3.53], [-2.15, -4.27], [1.5, 3.86], [-2.23, 0.69], [-5.48, -1.75], [3.21, 0.28], [0.45, -0.45], [-4.59, 1.58], [-0.12, 1.99], [-4.1, -3.45], [-4.27, 4.02], [5.16, -0.45], [-0.45, 4.51], [-3.78, -0.61], [-2.72, 2.56]], "fill": [[4.1, 0.12], [-5.48, 3.45], [-2.64, -3.78], [0.45, 4.02], [-0.28, -0.2], [-5.4, -0.69], [-2.88, 0.37], [-0.93, 1.99], [1.99, 0.69], [-4.43, 1.67], [-4.75, -2.56], [0.93, 2.15], [-4.27, 0.2], [-1.5, 0.28], [0.37, 0.93], [-3.78, -3.37], [3.05, 0.61], [-4.59, 3.94]] }, "heat": { "rim": [[5.48, -1.58], [-5.4, 1.42], [-4.43, -4.43], [0.28, 0.69], [-2.32, 4.51], [-3.05, -1.18], [3.13, 0.04], [-2.48, 1.67], [-5.48, -1.02], [-1.1, -0.77], [-4.02, 2.8], [-2.97, -3.21], [-4.75, -2.64], [-0.77, 1.99], [-4.27, 0.2], [-1.75, 3.13]], "fill": [[3.86, -0.53], [-5.24, -1.02], [-1.75, 3.37], [-0.61, -0.45], [-3.45, -3.62], [-3.13, 0.85], [1.83, 0.2], [-3.37, -1.5], [-5, 1.02], [-2.23, -0.45], [-4.59, -2.4], [-2.64, 2.23], [-4.1, -0.2], [-1.91, 0.77], [0.2, 0.45], [2.88, -0.04], [-3.62, -2.64], [-3.13, -0.12]] }, "tide": { "rim": [[6.13, -3.7], [-6.13, 4.27], [-4.92, -4.51], [0.69, 1.26], [-5, -0.04], [-1.58, -2.23], [-1.83, 4.27], [2.8, -1.91], [-2.32, 1.18], [5.32, -1.02], [-4.02, 2.97], [-4.02, -2.23], [2.8, 0.37], [-0.04, -0.77], [4.27, -3.21], [-3.21, -3.94]], "fill": [[5.32, -3.53], [-4.51, 2.48], [-3.62, -3.62], [1.1, 0.85], [-2.23, -0.37], [-5.24, -0.2], [3.45, -0.37], [-1.34, 1.91], [-0.28, -0.93], [-3.62, -1.67], [-3.45, 1.02], [-1.75, -2.07], [4.75, -2.07], [-0.45, 0.61], [-5, 1.18], [-3.86, -0.28], [2.48, 0.37], [-1.75, 0.77]] }, "air": { "rim": [[-4.67, -4.1], [4.59, 1.67], [-1.42, 3.7], [1.18, -2.97], [-3.05, -0.2], [1.1, 0.69], [-1.75, -3.62], [-0.61, -1.18], [3.29, -0.45], [-0.69, 1.75], [0.61, 3.37], [-3.45, -2.48], [2.97, -2.32], [2.72, 1.5], [-1.99, -1.91], [-3.13, -4.18]], "fill": [[-4.43, -3.94], [4.27, 1.58], [-1.1, 3.7], [0.69, -2.4], [-2.72, -0.45], [0.85, 0.93], [-1.91, -3.05], [2.88, -0.53], [-1.1, -1.26], [2.4, -2.72], [1.18, -0.77], [2.64, 1.1], [-3.45, -2.72], [0.37, 3.37], [-0.61, -2.72], [-3.05, -3.94], [3.86, 0.37], [0.12, -1.34]] } } };
var ED5_PROPS = { "memorial": { "actor": "ed5_memorial", "scale": 2, "states": { "hidden": 0, "assemble": 1, "hold": 2, "dissolve": 3 }, "assemble": 3, "dissolve": 1.6, "half": 6.75 }, "inscription": { "actors": { "nature": "ed5_inscription_nature", "heat": "ed5_inscription_heat", "tide": "ed5_inscription_tide", "air": "ed5_inscription_air" }, "states": { "hidden": 0, "descend": 1 }, "descend": 2.2 }, "spike": { "actor": "ed5_spike", "states": { "hidden": 0, "rise": 1, "hold": 2, "sink": 3 }, "rise": 0.6, "sink": 0.7 }, "trail": { "actor": "ed5_trail", "states": { "hidden": 0, "warn": 1, "burn": 2, "fade": 3 }, "segment": 2, "fade": 0.8 }, "icefan": { "actor": "ed5_icefan", "states": { "hidden": 0, "burst": 1, "hold": 2, "shatter": 3 }, "burst": 0.7, "shatter": 0.5, "reach": 2.875, "halfAngle": 50 }, "gust": { "actor": "ed5_gust", "states": { "hidden": 0, "burst": 1 }, "burst": 0.8 } };

// src/spells/_ed05_kit.ts
var SPECIES = ["nature", "heat", "tide", "air"];
var SLOT = { nature: 0, heat: 1, air: 2, tide: 3 };
function local2(o, yaw, bx, by, bz) {
  const f = fromYaw(yaw), r = right(f);
  return { x: o.x + r.x * bx - f.x * bz, y: o.y + by, z: o.z + r.z * bx - f.z * bz };
}
function yawLerp(a, b, t) {
  return a + angleDelta(a, b) * clamp(t, 0, 1);
}
function polarOf(d) {
  return Math.atan2(d.z, d.x) * 180 / Math.PI;
}
function inSector(p, o, dirYaw, half, rMin, rMax) {
  const d = sub(p, o);
  const h = Math.hypot(d.x, d.z);
  if (h < rMin || h > rMax) return false;
  return Math.abs(angleDelta(dirYaw, yawOf(d))) <= half;
}
var Path = class {
  pts = [];
  cum = [0];
  length;
  constructor(ctrl, samples = 240) {
    for (let i = 0; i <= samples; i++) this.pts.push(spline(ctrl, i / samples));
    for (let i = 1; i < this.pts.length; i++) this.cum.push(this.cum[i - 1] + dist(this.pts[i - 1], this.pts[i]));
    this.length = this.cum[this.cum.length - 1];
  }
  at(s) {
    const t = clamp(s, 0, this.length);
    let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) {
      const mid = lo + hi >> 1;
      if (this.cum[mid] <= t) lo = mid;
      else hi = mid;
    }
    const seg = this.cum[hi] - this.cum[lo] || 1;
    return lerp(this.pts[lo], this.pts[hi], (t - this.cum[lo]) / seg);
  }
  dir(s) {
    const a = this.at(s - 0.4), b = this.at(s + 0.4);
    return sub(b, a);
  }
};
var midUp = (a, b, h) => add(lerp(a, b, 0.5), { x: 0, y: h, z: 0 });

// src/spells/ed05_buried_kingdoms.ts
var T8 = ED5_TABLET.states;
var P5 = ED5_PROPS;
var SK = ED5_SKEL;
var IMP = ED5_IMPRINT.states;
var ed05_buried_kingdoms_default = defineSpell("ed05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, ED05.focusSnap);
  const fwd = norm(flat(aim.forward));
  const phiF = polarOf(fwd);
  const at = (s) => secs(s);
  const gnd = (p) => groundBelow(dim, { x: p.x, y: center.y + 6, z: p.z }, 24);
  const dirOf = (deg) => ({ x: Math.cos(deg * Math.PI / 180), y: 0, z: Math.sin(deg * Math.PI / 180) });
  const tabs = {};
  const rel = ED5_TABLET.relief;
  const reliefAt = (tb) => local2(tb.pos, tb.yaw, rel[0], rel[1], rel[2]);
  const faceAt = (tb) => up(tb.pos, ED5_TABLET.height / 2);
  const rSlot = P5.memorial.half;
  const theta0 = phiF - ED05.memorialTurn;
  const slotAngle = (sp, th) => th + 90 * SLOT[sp];
  let ti = 0;
  function hit(c, radius, dmg, o = {}) {
    let n = 0;
    for (const e of hostiles(dim, c, radius, caster)) {
      if (o.test && !o.test(e)) continue;
      if (o.once) {
        if (o.once.has(e.id)) continue;
        o.once.add(e.id);
      }
      if (damage(e, dmg, caster)) n++;
      if (o.kb) knockback(e, o.from ?? c, o.kb, o.kv ?? 0.3);
      if (o.slow) effect(e, "slowness", o.slow[0], o.slow[1]);
      if (o.lev) effect(e, "levitation", o.lev, 0);
      if (o.fire) {
        try {
          if (e.isValid) e.setOnFire(o.fire, true);
        } catch {
        }
      }
    }
    return n;
  }
  function warnAt(p, radius, ticks, slow = false) {
    const t = scene.spawn("telegraph", gnd(p), { kind: 2, size: radius, state: slow ? 4 : 1 });
    scene.after(ticks, () => t.state(3));
    scene.after(ticks + 8, () => scene.despawn(t));
  }
  function spikeAt(p, dmg, radius, lift, once, holdS = 1.5, size = 1) {
    const g = gnd(p);
    const s = scene.spawn(P5.spike.actor, g, { yaw: ti++ * 67 % 360, size, state: P5.spike.states.rise });
    sound(dim, "ed5_spike", g, 0.75, 0.88 + ti % 5 * 0.06);
    particle(dim, "ed5_rock", up(g, 0.4));
    if (ti % 2) particle(dim, "ed5_moss", up(g, 1.2));
    scene.after(4, () => hit(g, radius, dmg, { once, from: g, kb: 0.25, kv: lift }));
    scene.after(secs(holdS), () => s.state(P5.spike.states.sink));
    scene.after(secs(holdS + P5.spike.sink) + 1, () => scene.despawn(s));
  }
  function iceFan(o, yaw, size, dmg, slow, once, holdS = 1.3) {
    const g = gnd(o);
    const f = scene.spawn(P5.icefan.actor, g, { yaw, size, state: P5.icefan.states.burst });
    sound(dim, "ed5_ice", g, 1, 1.15 - size * 0.04);
    particle(dim, "ed5_ring_tide", up(g, 0.2));
    burst(dim, "ed5_shard", up(g, 1), 1.2, 3);
    const reach = P5.icefan.reach * size + 0.8;
    scene.after(3, () => {
      for (const p of [0.35, 0.7, 1]) particle(dim, "ed5_frost", up(local2(g, yaw, 0, 0, -reach * p), 1));
      hit(g, reach + 1, dmg, {
        once,
        slow,
        kb: 0.9,
        kv: 0.35,
        from: g,
        test: (e) => inSector(e.location, g, yaw, ED05.fanHalfAngle, 0, reach)
      });
    });
    scene.after(secs(holdS), () => f.state(P5.icefan.states.shatter));
    scene.after(secs(holdS + P5.icefan.shatter) + 1, () => scene.despawn(f));
  }
  function gust(p, size, dmg, radius, kb, once, lev = 0) {
    const g = gnd(p);
    const a = scene.spawn(P5.gust.actor, g, { yaw: ti++ * 53 % 360, size, state: P5.gust.states.burst });
    sound(dim, "ed5_gust", g, 0.9, 0.95 + ti % 4 * 0.05);
    particle(dim, "ed5_ring_air", up(g, 0.3));
    particle(dim, "ed5_wind", up(g, 1));
    hit(g, radius, dmg, { once, from: g, kb, kv: 0.45, lev });
    scene.after(secs(P5.gust.burst) + 1, () => scene.despawn(a));
  }
  sound(dim, "ed5_open", caster.location, 1);
  burst(dim, "ed5_rune", up(caster.location, 1.4), 1.2, 6);
  scene.every(secs(ED05.hushEvery), () => sound(dim, "ed5_hush", up(center, 3), 1), 0, at(ED05.endAt - 2));
  scene.every(10, () => particle(dim, "ed5_glow_mote", up(center, 5)), at(2), at(ED05.fractureAt));
  blocksFor(scene).place(up(center, 1), LIGHT);
  SPECIES.forEach((sp, i) => {
    const site = gnd(polar(center, ED05.riseRadius, slotAngle(sp, theta0)));
    const t0 = at(ED05.inscribeAt + i * ED05.riseStagger);
    scene.at(t0, () => {
      const ins = scene.spawn(P5.inscription.actors[sp], site, { state: P5.inscription.states.descend, size: 2.2 });
      sound(dim, "ed5_inscribe", site, 0.9, 0.92 + i * 0.06);
      scene.every(5, () => particle(dim, "ed5_rune_fall", up(site, 7)), scene.tick, scene.tick + 30);
      scene.after(secs(P5.inscription.descend) + 2, () => scene.despawn(ins));
    });
    scene.at(t0 + at(ED05.riseDelay), () => {
      const yaw = yawOf(sub(site, center));
      const a = scene.spawn(ED5_TABLET.actors[sp], site, { yaw, state: T8.rise, skin: 0 });
      tabs[sp] = { sp, a, pos: site, yaw, baseY: site.y };
      sound(dim, "ed5_rise", site, 1.1, 0.95 + i * 0.04);
      particle(dim, "ed5_crack", up(site, 0.3));
      particle(dim, "ed5_dust", up(site, 0.5));
      scene.after(secs(1.5), () => {
        particle(dim, `ed5_ring_${sp}`, up(site, 0.2));
        burst(dim, "ed5_rock", up(site, 0.6), 2.5, 3);
        particle(dim, "ed5_dust", up(site, 1));
        hit(site, ED05.riseRadiusHit, ED05.riseDamage, { kb: ED05.riseKnock, kv: 0.45 });
      });
      scene.after(secs(ED5_TABLET.len.rise), () => a.state(T8.stand));
    });
  });
  const tG0 = at(ED05.gatherAt), tG1 = at(ED05.gatherAt + ED05.gatherTime), tHalt = at(ED05.haltAt);
  const theta = (tk) => theta0 + ED05.memorialTurn * smooth((tk - tG0) / (tHalt - tG0));
  let memorial;
  scene.at(tG0, () => {
    memorial = scene.spawn(P5.memorial.actor, up(center, ED05.memorialHeight), { yaw: yawOf(dirOf(theta0)), state: P5.memorial.states.assemble });
    sound(dim, "ed5_grind", up(center, 4), 1.2);
    for (const sp of SPECIES) tabs[sp]?.a.state(T8.memorial);
  });
  scene.every(1, (e) => {
    const tk = tG0 + e;
    const th = theta(tk);
    const lin = clamp((tk - tG0) / (tG1 - tG0), 0, 1);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      const a = slotAngle(sp, th);
      const rad = ED05.riseRadius + (rSlot - ED05.riseRadius) * smooth(lin);
      const y = tb.baseY + (center.y + ED05.memorialHeight - tb.baseY) * easeOut(lin);
      tb.pos = { ...polar(center, rad, a), y };
      tb.yaw = yawOf(dirOf(a));
      tb.a.move(tb.pos, tb.yaw);
      if (e % 6 === 0 && lin < 1) particle(dim, "ed5_dust", up(tb.pos, 0.2));
    }
    memorial?.move(up(center, ED05.memorialHeight), yawOf(dirOf(th)));
  }, tG0, tHalt + 1);
  scene.at(tG1, () => {
    memorial?.state(P5.memorial.states.hold);
    sound(dim, "ed5_lock", up(center, 2), 1.4);
    for (const sp of SPECIES) particle(dim, `ed5_ring_${sp}`, up(center, 0.2 + SLOT[sp] * 0.1));
    ring(dim, "ed5_crack", up(center, 0.3), ED05.lockRadius * 0.6, 8);
    hit(center, ED05.lockRadius, ED05.lockDamage, { kb: 0.8, kv: 0.3, slow: [ED05.lockSlowTicks, ED05.lockSlowAmp] });
  });
  function outward(sp) {
    return dirOf(slotAngle(sp, theta0 + ED05.memorialTurn));
  }
  function emerge(sp, land, done) {
    const tb = tabs[sp];
    if (!tb) return;
    const s = SK[sp];
    const rc = reliefAt(tb);
    const yaw = tb.yaw + s.yawOff;
    tb.a.state(T8.empty);
    const sk = scene.spawn(s.actor, rc, { yaw, state: s.states.emerge });
    sound(dim, "ed5_peel", rc, 1.2);
    burst(dim, `ed5_burst_${sp}`, rc, 1.5, 4);
    particle(dim, "ed5_bonedust", rc);
    const out = outward(sp);
    const t0 = scene.tick;
    if (land) {
      const drift = add(rc, out);
      scene.span(t0, t0 + secs(2.15), (p) => {
        const tt = p * 2.15;
        const pos = tt < 0.7 ? lerp(rc, drift, smooth(tt / 0.7)) : bezier(drift, midUp(drift, land, 3), land, smooth((tt - 0.7) / 1.45));
        sk.move(pos, yaw);
      });
      scene.at(t0 + secs(2.1), () => {
        particle(dim, "ed5_bonedust", up(land, 0.3));
        particle(dim, `ed5_ring_${sp}`, up(land, 0.2));
      });
    } else {
      const exit = up(add(rc, mul(out, 5)), 1.5);
      scene.span(t0, t0 + secs(s.emerge), (p) => {
        const tt = p * s.emerge;
        sk.move(tt < 0.5 ? rc : bezier(rc, add(rc, mul(out, 3.5)), exit, smooth((tt - 0.5) / (s.emerge - 0.5))), yaw);
      });
    }
    scene.at(t0 + secs(s.emerge), () => done(sk));
  }
  function returnHome(sp, sk) {
    const tb = tabs[sp];
    if (!tb) return;
    const s = SK[sp];
    const rc = reliefAt(tb);
    const from = sk.loc;
    const yaw0 = sk.yaw, yaw1 = tb.yaw + s.yawOff;
    const airy = sp === "air";
    sk.state(s.states.return);
    const ctl = midUp(from, rc, airy ? 2 : 6);
    const t0 = scene.tick, n = secs(s.ret);
    const a0 = airy ? 0.1 : 0.45, a1 = airy ? 1.3 : 1.55;
    scene.span(t0, t0 + n, (p) => {
      const tt = p * s.ret;
      sk.move(bezier(from, ctl, rc, smooth((tt - a0) / (a1 - a0))), yawLerp(yaw0, yaw1, smooth(tt / (airy ? 0.9 : 0.6))));
    });
    scene.at(t0 + n, () => {
      tb.a.state(T8.receive);
      sound(dim, "ed5_settle", rc, 1.1);
      burst(dim, `ed5_burst_${sp}`, rc, 1.2, 4);
    });
    scene.at(t0 + n + 1, () => scene.despawn(sk));
  }
  function awaken(sp) {
    const tb = tabs[sp];
    if (!tb) return;
    tb.a.skin(1).state(T8.awaken);
    sound(dim, "ed5_awaken", faceAt(tb), 1.2, 0.9 + SLOT[sp] * 0.07);
    burst(dim, `ed5_mote_${sp}`, faceAt(tb), 3, 3);
  }
  for (const sp of SPECIES) {
    const tE = at(ED05.emergeAt[sp]);
    scene.at(tE - at(ED05.awakenLead), () => awaken(sp));
    scene.at(tE, () => {
      const tb = tabs[sp];
      if (!tb) return;
      if (sp === "air") {
        emerge(sp, void 0, (sk) => actAir(sk));
        return;
      }
      const land = gnd(add(center, mul(outward(sp), ED05.landDistance[sp])));
      const yaw = tb.yaw + SK[sp].yawOff;
      emerge(sp, land, (sk) => {
        if (sp === "nature") actNature(sk, land, yaw);
        else if (sp === "heat") actHeat(sk, land, yaw);
        else actTide(sk, land, yaw);
      });
    });
  }
  function actNature(sk, L3, yaw) {
    const s = SK.nature, lv = s.living;
    const slamPt = local2(L3, yaw, 3, 0, -5);
    sk.state(s.states.attack_a);
    warnAt(slamPt, ED05.slamRadius, secs(lv.hitA), true);
    scene.after(secs(lv.hitA), () => {
      sound(dim, "ed5_slam", slamPt, 1.5);
      particle(dim, "ed5_ring_nature", up(slamPt, 0.2));
      particle(dim, "fx_shock", up(slamPt, 0.3));
      burst(dim, "ed5_rock", up(slamPt, 0.8), 2, 4);
      particle(dim, "ed5_dust", up(slamPt, 0.6));
      hit(slamPt, ED05.slamRadius, ED05.slamDamage, { kb: ED05.slamKnock, kv: 0.5 });
      const foes = hostiles(dim, slamPt, 13, caster, ED05.slamLines);
      const dirs = foes.map((e) => yawOf(sub(e.location, slamPt)));
      const spread = [0, -38, 38, -70, 70];
      for (let k2 = 0; dirs.length < ED05.slamLines; k2++) dirs.push(yaw + spread[k2 % spread.length]);
      const once = /* @__PURE__ */ new Set();
      dirs.forEach((dy, li) => {
        const d = fromYaw(dy);
        for (let j = 0; j < ED05.spikesPerLine; j++) {
          const p = add(slamPt, mul(d, ED05.spikeFirst + j * ED05.spikeSpacing));
          scene.after(2 + j * 3 + li, () => {
            particle(dim, "ed5_line", up(gnd(p), 0.25));
            spikeAt(p, ED05.spikeDamage, ED05.spikeRadius, ED05.spikeLift, once);
          });
        }
      });
    });
    const tB = secs(lv.attackA) + 2;
    const sweepC = local2(L3, yaw, 0, 0, -12);
    scene.after(tB, () => {
      sk.state(s.states.attack_b);
      warnAt(sweepC, 7, secs(lv.hitB));
    });
    scene.after(tB + secs(lv.hitB), () => {
      sound(dim, "ed5_slam", sweepC, 1, 1.25);
      const left = mul(right(fromYaw(yaw)), -1);
      const once = /* @__PURE__ */ new Set();
      hit(L3, ED05.sweepMaxReach + 1, ED05.sweepDamage, {
        once,
        kb: ED05.sweepKnock,
        kv: 0.4,
        from: add(sweepC, mul(left, -6)),
        test: (e) => inSector(e.location, L3, yaw, ED05.sweepHalfAngle, ED05.sweepMinReach, ED05.sweepMaxReach)
      });
      [60, 25, -10, -45].forEach((a, k2) => scene.after(k2 * 2, () => {
        const p = add(L3, mul(fromYaw(yaw + a), 12));
        particle(dim, "ed5_line", up(gnd(p), 0.25));
        spikeAt(p, ED05.spikeDamage, ED05.spikeRadius, ED05.spikeLift, once, 1.2, 0.8);
      }));
    });
    scene.after(tB + secs(lv.attackB) + 2, () => returnHome("nature", sk));
  }
  function actHeat(sk, L3, yaw0) {
    const s = SK.heat, lv = s.living;
    sk.state(s.states.roar);
    const len1 = Math.min(24, 2 * ED05.laneReach);
    const trail1 = scene.spawn(P5.trail.actor, L3, { yaw: yaw0, state: P5.trail.states.warn });
    trail1.prop("len", len1);
    sound(dim, "ed5_burn", L3, 0.6, 0.8);
    scene.after(secs(lv.roar), () => charge(sk, L3, yaw0, len1, trail1, (end) => {
      skidTurn(sk, end, yaw0, (pos, yaw1) => {
        const trail2 = scene.spawn(P5.trail.actor, pos, { yaw: yaw1, state: P5.trail.states.warn });
        const target = add(center, mul(right(fromYaw(yaw0)), ED05.laneOffset));
        const len2 = Math.min(24, dist(flat(pos), flat(target)) + ED05.laneReach);
        trail2.prop("len", len2);
        scene.after(secs(lv.turn) + 2, () => charge(sk, pos, yaw1, len2, trail2, (end2) => {
          skidTurn(sk, end2, yaw1, () => returnHome("heat", sk), false);
        }));
      }, true);
    }));
  }
  function charge(sk, from, yaw, length, trail, done) {
    const s = SK.heat;
    const n = Math.max(4, secs(length / s.living.runSpeed));
    const dir = fromYaw(yaw);
    const end = add(from, mul(dir, length));
    sk.state(s.states.charge);
    trail.state(P5.trail.states.burn);
    sound(dim, "ed5_burn", from, 1);
    const once = /* @__PURE__ */ new Set();
    let reached = from;
    const t0 = scene.tick;
    scene.span(t0, t0 + n, (p, e) => {
      const pos = lerp(from, end, p);
      reached = pos;
      sk.move(pos, yaw);
      hit(pos, ED05.chargeRadius, ED05.chargeDamage, { once, from: sub(pos, mul(dir, 2)), kb: ED05.chargeKnock, kv: 0.45 });
      if (e % 2 === 0) particle(dim, "ed5_haze", up(pos, 0.6));
      if (e % 3 === 0) particle(dim, "ed5_ember", up(pos, 2.5));
    });
    scene.every(ED05.burnEvery, () => {
      const mid = lerp(from, reached, 0.5);
      for (const e of hostiles(dim, mid, dist(from, reached) / 2 + ED05.burnRadius + 1, caster)) {
        if (distToSegment(e.location, from, reached) > ED05.burnRadius) continue;
        damage(e, ED05.burnDamage, caster);
        try {
          if (e.isValid) e.setOnFire(ED05.burnFireSeconds, true);
        } catch {
        }
      }
      for (const f of [0.2, 0.5, 0.8]) particle(dim, "ed5_haze", up(lerp(from, reached, f), 0.4));
    }, t0 + 2, t0 + n + secs(ED05.burnSeconds));
    scene.at(t0 + n, () => done(end));
    scene.at(t0 + n + secs(ED05.burnSeconds), () => trail.state(P5.trail.states.fade));
    scene.at(t0 + n + secs(ED05.burnSeconds + P5.trail.fade) + 1, () => scene.despawn(trail));
  }
  function skidTurn(sk, from, yaw, next, turn) {
    const s = SK.heat, lv = s.living;
    const to = add(from, mul(fromYaw(yaw), 2));
    sk.state(s.states.skid);
    sound(dim, "ed5_skid", from, 1);
    burst(dim, "ed5_bonedust", up(from, 0.3), 1.2, 3);
    const t0 = scene.tick, n = secs(lv.skid);
    scene.span(t0, t0 + n, (p) => sk.move(lerp(from, to, easeOut(p)), yaw));
    if (!turn) {
      scene.at(t0 + n, () => next(to, yaw));
      return;
    }
    scene.at(t0 + n, () => {
      const target = add(center, mul(right(fromYaw(yaw)), ED05.laneOffset));
      const yaw1 = yawOf(sub(target, to));
      const dy = angleDelta(yaw, yaw1);
      sk.state(dy >= 0 ? s.states.turn_r : s.states.turn_l);
      const n2 = secs(lv.turn);
      scene.span(scene.tick, scene.tick + n2, (p) => sk.move(to, yawLerp(yaw, yaw1, p)));
      next(to, yaw1);
    });
  }
  function actTide(sk, L3, yaw) {
    const s = SK.tide, lv = s.living;
    const walkTo = add(L3, mul(fromYaw(yaw), lv.walkSpeed * ED05.tideWalk));
    sk.state(s.states.move);
    const t0 = scene.tick, nW = secs(ED05.tideWalk);
    scene.span(t0, t0 + nW, (p) => sk.move(lerp(L3, walkTo, p), yaw));
    const yaw1 = yaw + 90;
    const tTurn = t0 + nW;
    scene.at(tTurn, () => {
      sk.state(s.states.turn_r);
      scene.span(scene.tick, scene.tick + secs(lv.turn), (p) => sk.move(walkTo, yawLerp(yaw, yaw1, smooth(p))));
      for (const sx of [2.5, -2.5]) warnAt(fanTarget(walkTo, yaw1, sx), 3.5, secs(lv.turn) + secs(lv.hitsA[0]));
    });
    const tA = tTurn + secs(lv.turn) + 1;
    scene.at(tA, () => sk.state(s.states.attack_a));
    lv.hitsA.forEach((h, k2) => scene.at(tA + secs(h), () => {
      const o = local2(walkTo, yaw1, k2 === 0 ? 2.5 : -2.5, 0, 7.5);
      iceFan(o, yawOf(sub(fanTarget(walkTo, yaw1, k2 === 0 ? 2.5 : -2.5), o)), ED05.fanSize, ED05.fanDamage, [ED05.fanSlowTicks, ED05.fanSlowAmp]);
    }));
    const tC = tA + secs(lv.attackA) + 2;
    scene.at(tC, () => sk.state(s.states.attack_c));
    scene.at(tC + secs(lv.hitC), () => {
      const once = /* @__PURE__ */ new Set();
      for (const side of [90, -90]) iceFan(
        local2(walkTo, yaw1, side > 0 ? -1.5 : 1.5, 0, 0),
        yaw1 + side,
        ED05.fanSize,
        ED05.flareDamage,
        [ED05.fanSlowTicks, ED05.fanSlowAmp],
        once
      );
      burst(dim, "ed5_frost", up(walkTo, 5), 2.5, 5);
    });
    const tB = tC + secs(lv.attackC) + 2;
    scene.at(tB, () => sk.state(s.states.attack_b));
    scene.at(tB + secs(lv.hitB), () => {
      const tip = local2(walkTo, yaw1, 0, 0, 10);
      iceFan(tip, yaw1 + 180, ED05.fanSize * 0.8, ED05.fanDamage, [ED05.fanSlowTicks, ED05.fanSlowAmp]);
      particle(dim, "ed5_ring_tide", up(gnd(tip), 0.2));
    });
    scene.at(tB + secs(lv.attackB) + 2, () => returnHome("tide", sk));
  }
  function fanTarget(pos, yaw, sx) {
    const toC = sub(center, pos);
    return distXZ(pos, center) > 2 ? add(center, mul(right(fromYaw(yaw)), sx * 0.4)) : add(local2(pos, yaw, sx, 0, 6), toC);
  }
  function actAir(sk) {
    const s = SK.air;
    const tb = tabs.air;
    if (!tb) return;
    const out = outward("air");
    const start = sk.loc;
    const psi0 = polarOf(out) + 55;
    const R2 = ED05.passRadius, cy = center.y;
    const pts = [start];
    for (let k2 = 0; k2 < 3; k2++) {
      const psi = psi0 + 120 * k2;
      pts.push(polar(center, R2, psi, ED05.cruiseHeight));
      pts.push(polar(center, 1.5, psi + 90, ED05.passHeight));
      pts.push(polar(center, R2, psi + 180, ED05.cruiseHeight - 1));
      if (k2 < 2) pts.push(polar(center, R2 * 1.25, psi + 150, ED05.cruiseHeight + 2));
    }
    const home = add(up(reliefAt(tb), 3), mul(out, 6));
    pts.push(home);
    const path = new Path(pts.map((p) => ({ ...p, y: Math.max(p.y, cy + 2) })));
    const n = secs(path.length / ED05.flySpeed);
    let state = s.states.move, want = state, wantN = 0, lastYaw = sk.yaw, ringCd = 6;
    sk.state(state);
    const t0 = scene.tick;
    scene.span(t0, t0 + n, (p, e) => {
      const sPos = p * path.length;
      const pos = path.at(sPos);
      const yaw = yawOf(path.dir(sPos));
      const dy = angleDelta(lastYaw, yaw);
      lastYaw = yaw;
      const near = distXZ(pos, center) < ED05.ringReach;
      const w = near ? s.states.move : Math.abs(dy) > 2 ? dy > 0 ? s.states.turn_r : s.states.turn_l : s.states.glide;
      if (w === want) wantN++;
      else {
        want = w;
        wantN = 0;
      }
      if (want !== state && wantN >= 3) {
        state = want;
        sk.state(state);
      }
      sk.move(pos, yaw);
      if (e % 4 === 0) particle(dim, "ed5_feather", pos);
      if (state === s.states.move && near) {
        if (--ringCd <= 0) {
          ringCd = secs(s.living.flap);
          gust(pos, 1, ED05.ringDamage, ED05.ringRadius, ED05.ringKnock);
        }
      } else ringCd = 6;
    });
    scene.at(t0 + n, () => returnHome("air", sk));
  }
  const formation = {};
  scene.at(at(ED05.phase3At), () => {
    if (memorial) {
      memorial.state(P5.memorial.states.dissolve);
      const m = memorial;
      scene.after(secs(P5.memorial.dissolve) + 1, () => scene.despawn(m));
    }
    sound(dim, "ed5_blaze", up(center, ED05.memorialHeight + 4), 1.4);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      const fpos = polar(center, ED05.fanRadius, phiF + ED05.formationAngle[sp], ED05.formationHeight[sp]);
      const fyaw = yawOf(sub(center, fpos));
      formation[sp] = { pos: fpos, yaw: fyaw };
      tb.a.skin(2).state(T8.formation);
      const from = tb.pos, y0 = tb.yaw, ctl = midUp(from, fpos, 6);
      const t0 = scene.tick, n = secs(ED05.formationTime);
      scene.span(t0, t0 + n, (p) => {
        tb.pos = bezier(from, ctl, fpos, smooth(p));
        tb.yaw = yawLerp(y0, fyaw, smooth(p));
        tb.a.move(tb.pos, tb.yaw);
      });
      scene.at(t0 + n, () => tb.a.state(T8.aim));
      burst(dim, `ed5_mote_${sp}`, faceAt(tb), 3, 3);
    }
  });
  function imprintEffect(sp, imp, yaw, size, once) {
    const o = ED5_IMPRINT.outline[sp];
    const toW = (q) => local2(imp, yaw, q[0] * size, 0, q[1] * size);
    if (sp === "nature") {
      o.rim.forEach((q, k2) => scene.after(k2, () => spikeAt(toW(q), ED05.p3SpikeDamage, ED05.p3SpikeRadius, 0.8, once, 1.3, 1.1)));
    } else if (sp === "heat") {
      const pts = [...o.rim, ...o.fill].map(toW);
      scene.every(ED05.brandEvery, (e) => {
        const seen = /* @__PURE__ */ new Set();
        for (const e2 of hostiles(dim, imp, 12, caster)) {
          if (seen.has(e2.id) || !pts.some((p) => distXZ(p, e2.location) < ED05.brandRadius)) continue;
          seen.add(e2.id);
          damage(e2, ED05.brandDamage, caster);
          try {
            if (e2.isValid) e2.setOnFire(ED05.brandFireSeconds, true);
          } catch {
          }
        }
        particle(dim, "ed5_ember", up(pts[e * 3 % pts.length], 0.4));
        particle(dim, "ed5_haze", up(pts[(e * 7 + 5) % pts.length], 0.3));
      }, scene.tick, scene.tick + secs(ED05.brandSeconds));
      sound(dim, "ed5_burn", imp, 1.2, 0.8);
    } else if (sp === "tide") {
      iceFan(
        local2(imp, yaw, 0, 0, P5.icefan.reach * ED05.p3FanSize * 0.45),
        yaw,
        ED05.p3FanSize,
        ED05.p3FanDamage,
        [ED05.p3FanSlowTicks, ED05.p3FanSlowAmp],
        once,
        1.4
      );
      for (const q of o.fill.slice(0, 6)) particle(dim, "ed5_frost", up(toW(q), 0.8));
    } else {
      for (const q of o.rim.slice(0, 4)) gust(toW(q), 1.3, ED05.galeDamage, ED05.galeRadius, ED05.galeKnock, once, ED05.galeLevitate);
      gust(imp, 1.6, ED05.galeDamage, ED05.galeRadius, ED05.galeKnock, once, ED05.galeLevitate);
    }
  }
  function projectFrom(sp, tHit2, imp, yaw, all) {
    const tW = tHit2 - at(ED05.projectWarn);
    let im;
    scene.at(tW, () => {
      const tb = tabs[sp];
      if (!tb) return;
      tb.a.state(all ? T8.project_all : T8.project);
      im = scene.spawn(ED5_IMPRINT.actors[sp], imp, { yaw, size: ED05.imprintSize, state: IMP.warn });
      if (!all) sound(dim, "ed5_project", up(imp, 2), 1.3, 0.92 + SLOT[sp] * 0.05);
      scene.every(3, () => line(dim, `ed5_ray_${sp}`, faceAt(tb), up(imp, 0.4), all ? 5 : 8), scene.tick, tHit2 + 4);
    });
    scene.at(tHit2, () => {
      im?.state(IMP.brand);
      particle(dim, `ed5_ring_${sp}`, up(imp, 0.3));
      if (!all) imprintEffect(sp, imp, yaw, ED05.imprintSize, /* @__PURE__ */ new Set());
    });
    scene.at(tHit2 + 10, () => im?.state(IMP.pulse));
    const hold = sp === "heat" ? ED05.brandSeconds : 1.4;
    scene.at(tHit2 + secs(hold), () => {
      im?.state(IMP.fade);
      tabs[sp]?.a.state(T8.aim);
    });
    scene.at(tHit2 + secs(hold + 0.6) + 1, () => {
      if (im) scene.despawn(im);
    });
  }
  for (const sp of SPECIES) {
    scene.at(at(ED05.projectAt[sp]) - at(ED05.projectWarn) - 1, () => {
      const f = formation[sp];
      const imp = gnd(f ? add(center, mul(norm(flat(sub(f.pos, center))), 1.5)) : center);
      projectFrom(sp, at(ED05.projectAt[sp]), imp, f ? f.yaw : 0, false);
    });
  }
  const tAll = at(ED05.allAt);
  scene.at(tAll - at(ED05.projectWarn) - 1, () => {
    const g = gnd(center);
    SPECIES.forEach((sp, k2) => projectFrom(sp, tAll, g, (formation[sp]?.yaw ?? 0) + k2 * 12, true));
  });
  scene.at(tAll - secs(0.8), () => sound(dim, "ed5_finale", up(center, 2), 1.6));
  scene.at(tAll, () => {
    const g = gnd(center);
    const once = /* @__PURE__ */ new Set();
    hit(g, ED05.finaleRadius, ED05.finaleDamage, { once, kb: ED05.finaleKnock, kv: 0.6, slow: [ED05.p3FanSlowTicks, ED05.p3FanSlowAmp], fire: 2 });
    const o = ED5_IMPRINT.outline.nature;
    o.rim.slice(0, 8).forEach((q, k2) => scene.after(k2, () => spikeAt(local2(g, phiF, q[0], 0, q[1]), 0, 1, 0.5, once, 1.2, 1.2)));
    iceFan(g, yawOf(fwd), ED05.p3FanSize * 0.8, 0, [ED05.p3FanSlowTicks, ED05.p3FanSlowAmp], once, 1.2);
    for (let k2 = 0; k2 < 4; k2++) scene.after(3 + k2 * 2, () => gust(polar(g, 4.5, phiF + 45 + k2 * 90), 1.4, 0, 4, ED05.finaleKnock, once));
    burst(dim, "ed5_frag", up(g, 3), 3, 6);
    particle(dim, "fx_flash", up(g, 2));
  });
  const tF = at(ED05.fractureAt);
  scene.at(tF, () => {
    sound(dim, "ed5_fracture", up(center, 10), 1.6);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      tb.a.state(T8.fracture);
      burst(dim, "ed5_frag_big", faceAt(tb), 2.5, 4);
      burst(dim, `ed5_burst_${sp}`, faceAt(tb), 2, 4);
    }
  });
  scene.at(tF + 8, () => sound(dim, "ed5_rain", up(center, 6), 1));
  scene.every(4, (e) => {
    const a = e * 2.39996, r = 2 + e * 7 % 10;
    particle(dim, "ed5_frag", { x: center.x + Math.cos(a) * r, y: center.y + 12, z: center.z + Math.sin(a) * r });
  }, tF + 4, tF + secs(2.4));
  scene.at(tF + secs(ED5_TABLET.len.fracture) + 2, () => {
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (tb) scene.despawn(tb.a);
    }
  });
  scene.endAt(at(ED05.endAt));
});

// src/config/ed06.ts
var ED06 = {
  // ---- domain
  /** How far from the aim point the spell snaps onto the nearest enemy. */
  snap: 12,
  /**
   * The designated hostile zone (the Concord's target) is the enemy group, kept inside the stage in
   * front of the caster: at least / at most this far ahead (blocks) and within this many degrees of
   * the caster's facing.  Without enemies it sits `zoneDefault` blocks ahead.
   */
  zoneMinAhead: 14,
  zoneMaxAhead: 24,
  zoneMaxDeg: 26,
  zoneDefault: 16,
  /** Search radius for the enemy group and how far a member may be from the group's seed. */
  zoneSearch: 20,
  zoneGroup: 7,
  // ---- Phase I: The Four Ancient Heartbeats
  /** Each heartbeat shakes the domain: enemies within this radius of the zone take damage and are slowed. */
  beatRadius: 16,
  beatDamage: 2,
  beatSlowTicks: 40,
  beatSlowAmp: 1,
  beatKnock: 0.35,
  // ---- Phase II: The Sovereigns Awaken
  /** Nature Dragon: forefeet landing (damage, radius) and every footfall shockwave. */
  natureLandDamage: 8,
  natureLandRadius: 6,
  stepDamage: 3,
  stepRadius: 3.6,
  stepKnockH: 0.7,
  stepKnockV: 0.35,
  /** Heat Dragon charge: horn strike and body slam damage, lateral reach, shove. */
  hornDamage: 7,
  bodyDamage: 4,
  chargeHalfWidth: 2.6,
  chargeKnockH: 1.3,
  chargeKnockV: 0.45,
  /** Seconds enemies struck by the Heat Dragon keep burning. */
  burnSeconds: 3,
  /** Air Dragon's pull-up gust after its stoop over the hostile zone: damage, radius, knockback. */
  gustDamage: 5,
  gustRadius: 7,
  gustKnock: 1,
  // ---- Phase III: The Primordial Dominion
  /** Roots break out of the ground toward enemies: how many, how long they hold, damage at the bind. */
  maxRoots: 4,
  rootRadius: 18,
  rootHoldTicks: 70,
  rootDamage: 4,
  /** A root-bound pillar rises behind the first bound enemies (how many, damage when it erupts, barrier height). */
  maxPillars: 2,
  pillarDamage: 4,
  pillarBarrierHeight: 3,
  /** Neck lash: damage and radius of the low sweep in front of the Nature Dragon. */
  lashDamage: 8,
  lashRadius: 6,
  /** Superheated wave the Heat Dragon roars across the ground into the hostile zone (once in Phase III). */
  heatWaveDamage: 6,
  /** Ground vitrified behind each charge: a glass patch every N blocks, burning enemies on it. */
  glassEvery: 3.5,
  glassLifeTicks: 140,
  glassBurnDamage: 1,
  glassBurnRadius: 1.8,
  /** Standing stones within this distance of a charge turn to glowing glass and flash heat around them. */
  vitrifyReach: 4.6,
  vitrifyDamage: 4,
  vitrifyRadius: 3,
  /** Water & Ice Dragon: currents under its swim path shove enemies (once-per-pass damage). */
  currentReach: 3.5,
  currentShove: 0.55,
  currentDamage: 3,
  /** Crystalline bridges: enemies under a forming bridge are frost-bitten and slowed. */
  bridgeDamage: 4,
  bridgeWidth: 2.6,
  bridgeSlowTicks: 60,
  bridgeSlowAmp: 2,
  /** Air Dragon: aerial formations; their updraft lifts enemies below them, falling debris on release. */
  updraftRadius: 4.5,
  updraftDamage: 3,
  updraftLift: 0.9,
  updraftEvery: 30,
  debrisDamage: 6,
  debrisRadius: 5,
  // ---- Phase IV: The Fourfold Concord
  /** Radius of the Nature Dragon's enclosing pillar ring (barrier columns except two doorways). */
  ringRadius: 6,
  ringBarrierHeight: 4,
  /** Half-width of each doorway (degrees) on the Heat Dragon's lane. */
  doorwayDeg: 20,
  /** 1. Geological shockwaves: forelimb slam, the travelling quake, then three pulses from the pillars. */
  slamDamage: 10,
  slamRadius: 6,
  quakeDamage: 4,
  quakeRadius: 2.8,
  shockPulseDamage: [6, 6, 8],
  shockSlowTicks: 60,
  /** 2. Moving water and freezing: current damage, shove, then each crystallising ice layer. */
  concordCurrentDamage: 3,
  concordCurrentShove: 0.6,
  iceLayerDamage: 4,
  /** 3. Spiral of ice and wind: damage every N ticks while enemies are carried round, final lift. */
  spiralDamage: 2,
  spiralEvery: 8,
  spiralShove: 0.55,
  spiralLift: 0.22,
  spiralFinalLift: 0.95,
  /** 4. The Heat Dragon's final charge: run-up distance, horn hit, thermal detonation at the zone. */
  finalRunUp: 18,
  finalHornDamage: 10,
  detonationDamage: 22,
  detonationExtra: 2,
  detonationKnockH: 2.6,
  detonationKnockV: 0.9,
  detonationBurnSeconds: 5
};

// src/spells/_ed06_motion.ts
var Mover = class {
  constructor(actor, start, yaw, t0, ground) {
    this.actor = actor;
    this.ground = ground;
    this.cursor = t0;
    this.last = { ...start };
    this.lastYaw = yaw;
  }
  segs = [];
  cursor;
  last;
  lastYaw;
  /** Signed, smoothed yaw rate (deg / tick) -- used by flyers to pick banking states. */
  yawRate = 0;
  /** Optional cap on how fast the facing may change (deg / tick, 0 = none): sharp path corners become turns. */
  maxTurn = 0;
  ySmooth;
  /** Measured horizontal and 3D speed (blocks / s) and turn rate (deg / s, + = yaw increasing). */
  speed = 0;
  speed3 = 0;
  turnRate = 0;
  prevP;
  gov;
  active = false;
  /**
   * Locomotion governor.  From now on the creature's visible state follows what its body actually does,
   * whatever the choreography asked for: a standing or acting state never slides over the ground (while
   * travelling the creature shows the travelling loop closest to its real speed), a travelling loop is
   * never shown standing still (idle, or the in-place turn while it pivots), and the asked-for state
   * returns as soon as the motion allows.  `actor.state(n)` keeps working; it records the request.
   */
  govern(g) {
    const actor = this.actor;
    const raw = actor.state.bind(actor);
    this.gov = { g, raw, want: 0, shown: 0, moving: false, since: 0 };
    actor.state = (n) => {
      const v2 = this.gov;
      v2.want = n;
      if (!this.active || n === 0 || g.free.includes(n)) {
        v2.shown = n;
        raw(n);
      }
      return actor;
    };
    return this;
  }
  decide(t, p) {
    const v2 = this.gov;
    const w = v2.want;
    if (w === 0 || v2.g.free.includes(w)) {
      if (v2.shown !== w) {
        v2.shown = w;
        v2.raw(w);
      }
      return;
    }
    const sp = v2.g.swims ? this.speed3 : this.speed;
    v2.moving = v2.moving ? sp > 0.45 : sp > 0.9;
    const gait = (s) => v2.g.gaits.find((x) => x.state === s);
    const isTurn = (s) => !!v2.g.turn && (s === v2.g.turn.left || s === v2.g.turn.right);
    let show = w;
    if (v2.moving) {
      if (!gait(w)) {
        let best = v2.g.gaits[0], bd = Infinity;
        for (const x of v2.g.gaits) {
          const d = Math.abs(Math.log(Math.max(sp, 0.1) / x.speed));
          if (d < bd) {
            bd = d;
            best = x;
          }
        }
        show = best.state;
      }
    } else if (v2.g.turn && Math.abs(this.turnRate) > v2.g.turn.above) {
      show = this.turnRate > 0 ? v2.g.turn.right : v2.g.turn.left;
    } else if (gait(w) || isTurn(w)) {
      show = v2.g.idle;
    }
    if (show !== v2.shown && t - v2.since >= 4) {
      v2.shown = show;
      v2.since = t;
      v2.raw(show);
    }
    void p;
  }
  /**
   * Walk from a to b at `speed` (blocks / s) with short starts and stops (`ramp` seconds each) - a
   * trapezoid of speed, so the gait's own speed holds for the whole stretch instead of an ease curve
   * that is too slow at the ends and too fast in the middle.
   */
  walk(a, b, speed, opts = {}) {
    const D4 = Math.hypot(b.x - a.x, b.z - a.z);
    const ramp = Math.min(opts.ramp ?? 0.25, D4 / speed / 2);
    const cruise = Math.max(0, D4 / speed - ramp);
    const T9 = cruise + 2 * ramp;
    const ticks = Math.max(2, Math.round(T9 * 20));
    const dist2 = (s) => {
      if (s < ramp) return speed * s * s / (2 * ramp);
      if (s < ramp + cruise) return speed * ramp / 2 + speed * (s - ramp);
      const r = T9 - s;
      return D4 - speed * r * r / (2 * ramp);
    };
    return this.add(ticks, (p) => lerp(a, b, D4 > 1e-6 ? clamp(dist2(p * T9) / D4, 0, 1) : 1), { tag: opts.tag, yaw: opts.yaw ?? yawOf({ x: b.x - a.x, y: 0, z: b.z - a.z }) });
  }
  add(ticks, at, opts = {}) {
    const from = this.cursor, to = this.cursor + Math.max(1, Math.round(ticks));
    const seg = { from, to, at: (t) => at(clamp((t - from) / (to - from), 0, 1), t), yaw: opts.yaw, tag: opts.tag };
    this.segs.push(seg);
    this.cursor = to;
    this.last = seg.at(to);
    return seg;
  }
  /** Stay where the last segment ended. */
  hold(ticks, yaw, tag) {
    const p = { ...this.last };
    return this.add(ticks, () => p, { yaw: yaw ?? this.lastYawAt(this.cursor), tag });
  }
  /** Catmull-Rom through pts (pts[0] should be the current position) at `speed` blocks / s. */
  path(pts, speed, opts = {}) {
    const L3 = new ArcPath((u) => spline(pts, u), 48);
    const ticks = Math.max(2, Math.round(L3.length / speed * 20));
    const ease = opts.ease ?? ((p) => p);
    return this.add(ticks, (p) => L3.at(ease(p) * L3.length), { tag: opts.tag, yaw: opts.yaw });
  }
  /** Catmull-Rom through pts covered in exactly `ticks` ticks (arc-length paced, optional easing). */
  pathIn(pts, ticks, opts = {}) {
    const L3 = new ArcPath((u) => spline(pts, u), 48);
    const ease = opts.ease ?? ((p) => p);
    return this.add(ticks, (p) => L3.at(ease(p) * L3.length), { tag: opts.tag, yaw: opts.yaw });
  }
  /** End the segment active at tick t (and drop later ones) so new plans can start there. */
  truncate(t) {
    this.segs = this.segs.filter((s2) => s2.from < t);
    const s = this.segs[this.segs.length - 1];
    if (s && s.to > t) s.to = t;
    this.cursor = t;
    this.last = this.posAt(t);
    this.lastYaw = this.lastYawAt(t);
  }
  segAt(t) {
    for (const s of this.segs) if (t >= s.from && t < s.to) return s;
    return void 0;
  }
  posAt(t) {
    const s = this.segAt(t);
    if (s) return s.at(t);
    let best;
    for (const x of this.segs) if (x.to <= t && (!best || x.to > best.to)) best = x;
    return best ? best.at(best.to) : this.last;
  }
  lastYawAt(t) {
    const s = this.segAt(t - 1) ?? this.segAt(t);
    if (s && s.yaw !== void 0) return typeof s.yaw === "number" ? s.yaw : s.yaw(t);
    return this.lastYaw;
  }
  /** Advance the actor to tick t (call every tick). */
  step(t) {
    const s = this.segAt(t);
    let p = s ? s.at(t) : this.posAt(t);
    let want = this.lastYaw;
    if (s && s.yaw !== void 0) {
      this.yawRate *= 0.7;
      want = typeof s.yaw === "number" ? s.yaw : s.yaw(t);
    } else {
      const n = s ? s.at(Math.min(t + 1, s.to)) : p;
      const dx = n.x - p.x, dz = n.z - p.z;
      if (Math.hypot(dx, dz) > 0.02) {
        want = yawOf({ x: dx, y: 0, z: dz });
        this.yawRate = this.yawRate * 0.6 + angleDelta(this.lastYaw, want) * 0.4;
      } else this.yawRate *= 0.7;
    }
    if (this.maxTurn > 0) want = this.lastYaw + clamp(angleDelta(this.lastYaw, want), -this.maxTurn, this.maxTurn);
    const dYaw = angleDelta(this.lastYaw, want) * 20;
    this.lastYaw = want;
    if (this.ground) {
      const g = this.ground(p);
      this.ySmooth = this.ySmooth === void 0 ? g : this.ySmooth + clamp(g - this.ySmooth, -0.35, 0.35);
      p = { x: p.x, y: this.ySmooth, z: p.z };
    }
    const sp = this.prevP ? Math.hypot(p.x - this.prevP.x, p.z - this.prevP.z) * 20 : 0;
    const sp3 = this.prevP ? Math.hypot(p.x - this.prevP.x, p.y - this.prevP.y, p.z - this.prevP.z) * 20 : 0;
    this.speed = this.active ? this.speed * 0.35 + sp * 0.65 : 0;
    this.speed3 = this.active ? this.speed3 * 0.35 + sp3 * 0.65 : 0;
    this.turnRate = this.active ? this.turnRate * 0.35 + dYaw * 0.65 : 0;
    this.prevP = p;
    this.active = true;
    if (this.gov) this.decide(t, p);
    this.actor.move(p, this.lastYaw);
    return p;
  }
};
var ArcPath = class {
  constructor(f, n = 64, loop = false) {
    this.loop = loop;
    let L3 = 0;
    for (let i = 0; i <= n; i++) {
      const p = f(i / n);
      if (i) L3 += Math.hypot(p.x - this.pts[i - 1].x, p.y - this.pts[i - 1].y, p.z - this.pts[i - 1].z);
      this.pts.push(p);
      this.cum.push(L3);
    }
    this.length = Math.max(L3, 1e-3);
  }
  length;
  pts = [];
  cum = [];
  at(s) {
    let d = this.loop ? (s % this.length + this.length) % this.length : clamp(s, 0, this.length);
    let lo = 0, hi = this.cum.length - 1;
    while (hi - lo > 1) {
      const mid = lo + hi >> 1;
      if (this.cum[mid] <= d) lo = mid;
      else hi = mid;
    }
    const seg = this.cum[hi] - this.cum[lo];
    d = seg > 1e-6 ? (d - this.cum[lo]) / seg : 0;
    return lerp(this.pts[lo], this.pts[hi], d);
  }
};
var Frame = class {
  constructor(c, F, R2) {
    this.c = c;
    this.F = F;
    this.R = R2;
  }
  p(f, r, h = 0) {
    return { x: this.c.x + this.F.x * f + this.R.x * r, y: this.c.y + h, z: this.c.z + this.F.z * f + this.R.z * r };
  }
  polar(radius, deg, h = 0, from) {
    const a = deg * Math.PI / 180;
    const f = Math.cos(a) * radius, r = Math.sin(a) * radius;
    const o = from ?? this.c;
    return { x: o.x + this.F.x * f + this.R.x * r, y: o.y + h, z: o.z + this.F.z * f + this.R.z * r };
  }
  /** Horizontal unit direction for a frame angle. */
  dir(deg) {
    const a = deg * Math.PI / 180;
    return { x: this.F.x * Math.cos(a) + this.R.x * Math.sin(a), y: 0, z: this.F.z * Math.cos(a) + this.R.z * Math.sin(a) };
  }
};
function hash012(a, b = 0) {
  const x = Math.sin(a * 12.9898 + b * 78.233 + 0.5) * 43758.5453;
  return x - Math.floor(x);
}
function stadium(c, R2, F, L3, rho) {
  const P6 = 2 * L3 + 2 * Math.PI * rho;
  const at = (x, y) => ({ x: c.x + R2.x * x + F.x * y, y: c.y, z: c.z + R2.z * x + F.z * y });
  return (u) => {
    let s = (u % 1 + 1) % 1 * P6;
    if (s < L3) return at(-L3 / 2 + s, rho);
    s -= L3;
    if (s < Math.PI * rho) {
      const a2 = s / rho;
      return at(L3 / 2 + rho * Math.sin(a2), rho * Math.cos(a2));
    }
    s -= Math.PI * rho;
    if (s < L3) return at(L3 / 2 - s, -rho);
    s -= L3;
    const a = s / rho;
    return at(-L3 / 2 - rho * Math.sin(a), -rho * Math.cos(a));
  };
}

// src/spells/ed06_world_before_names.ts
var NATURE = { actor: "dragon_nature", scale: 2 };
var N2 = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10, depart: 11 };
var N_WALK = 1.5;
var N_CYCLE = 64;
var N_TURN = 20;
var N_STEPS = [{ t: 0, x: -3, z: -1.9 }, { t: 16, x: -3, z: 5.5 }, { t: 32, x: 3, z: -1.9 }, { t: 48, x: 3, z: 5.5 }];
var N_T = { arriveLand: 50, power: 52, attackA: 64, attackAHit: 44, attackB: 48, attackBHit: 27, depart: 56 };
var N_SKIN = { normal: 0, bloom: 1 };
var N_SLAM = { x: 3, z: 4.5 };
var N_HEAD = { ahead: 16, up: 12.5 };
var STRATA2 = { rise: 1, hold: 2, part: 3, erupt: 4, crumble: 5 };
var PILLAR2 = { rise: 1, hold: 2, erupt: 3, crumble: 4 };
var ROOT2 = { grow: 1, hold: 2, erupt: 3, wither: 4 };
var ROOT_LEN2 = 6;
var ROOT_BIND2 = 21;
var HEAT = { actor: "dragon_heat", scale: 1.85 };
var H = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  turn_l: 4,
  turn_r: 5,
  attack_a: 6,
  attack_b: 7,
  power: 8,
  react: 9,
  rest: 10,
  depart: 11,
  ignite: 12,
  charge: 13,
  skid: 14,
  pant: 15,
  cool: 16,
  roar: 17,
  walk: 18
};
var H_RUN = 10.02;
var H_WALK = 3.53;
var H_TURN = 225;
var H_T = { arriveWalk: 24, ignite: 32, igniteRoar: 22, skid: 14, roar: 28, cool: 24, depart: 40 };
var H_SKIN = { cool: 0, ignited: 1, whitehot: 2 };
var H_HORN = 7.9;
var WALL3 = { form: 1, part: 3, fade: 4 };
var GLASS2 = { appear: 1, hold: 2, fade: 3 };
var LANE2 = { appear: 1, armed: 2, surge: 3, fade: 4 };
var TIDE = { actor: "dragon_tide", scale: 2 };
var D3 = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  turn_l: 4,
  turn_r: 5,
  attack_a: 6,
  attack_b: 7,
  power: 8,
  react: 9,
  rest: 10,
  depart: 11,
  swim: 12,
  land: 13,
  roar: 14,
  attack_c: 15
};
var D_SWIM = 14;
var D_T = { arrive: 20, land: 16, landHit: 5, sweep: 30, sweepHit: [10, 21], flare: 22, flareHit: 9, power: 30, depart: 32 };
var MASS2 = { gather: 1, hold: 2, burst: 3, disperse: 4 };
var STREAM2 = { form: 1, hold: 2, fade: 3 };
var CUR2 = { form: 1, flow: 2, freeze: 3, spiral: 4, ice: 5, rise: 6, shatter: 7 };
var CUR_R2 = 4;
var CUR_SWEEP2 = 160;
var AIR = { actor: "dragon_air", scale: 1.5 };
var A3 = {
  hidden: 0,
  arrive: 1,
  idle: 2,
  move: 3,
  glide: 4,
  turn_l: 5,
  turn_r: 6,
  roll: 7,
  stoop: 8,
  flare: 9,
  land: 10,
  attack_a: 11,
  attack_b: 12,
  power: 13,
  react: 14,
  rest: 15,
  depart: 16,
  flutter: 17
};
var A_T = { arrive: 48, roll: 20, stoop: 12, land: 20, power: 18, flare: 10, depart: 32 };
var A_BANK = 1.4;
var CLOUD2 = { form: 1, part: 2, fade: 3 };
var CODEX2 = { rise: 1, hover: 2, beat: 3, absorb: 4, vanish: 5 };
var CODEX_CORE = 24 / 16 * 1.3;
var EMBLEM = { appear: 1, beat: 2, glow: 3, fade: 4 };
var EMBLEM_C = 34 / 16;
var EMBLEM_DOMAIN = 4;
var SPIRIT = { form: 1, hold: 2, stream: 3 };
var FOG_CLEAR = 5;
var HORIZON = { rise: 1, hold: 2, sink: 3 };
var FLORA = { sprout: 1, sway: 2, wither: 3 };
var STONE = { rise: 1, hold: 2, sink: 3, flare: 4 };
var STONE_SKIN = { stone: 0, glass: 1, obsidian: 2 };
var BRIDGE2 = { form: 1, hold: 2, shatter: 3 };
var BRIDGE_LEN = 12;
var DEBRIS = { lift: 1, orbit: 2, scatter: 3 };
var RING = { rise: 1, hold: 2, quake: 3, burst: 4, sink: 5 };
var RING_SKIN = { frost: 1, glass: 2 };
var RING_R = 6;
var SHELL = { grow: 1, hold: 2, shatter: 3 };
var SHELL_LAYERS = [{ t: 13, r: 2.2 }, { t: 28, r: 3.6 }, { t: 44, r: 5 }];
var SPIRAL = { form: 1, spin: 2, burst: 3 };
var BLAST = { blast: 1, hold: 2, fade: 3 };
var LINEAGE = ["nature", "heat", "tide", "air"];
var BEATS = [44, 70, 96, 122];
var T_ALL = 132;
var T22 = 140;
var T32 = 390;
var T42 = 630;
var T52 = 930;
var T_NATURE = 150;
var T_HEAT = 206;
var T_TIDE = 262;
var T_AIR = 304;
var T_SEAL = T52 + 168;
var T_END3 = T_SEAL + 78;
var ST = {
  codexK1: [30, 0, 6.3],
  codexK2: [46, -20, 11],
  codexK3: [26, -1, 4.8],
  emblems: [[50, -6, 2.4], [30, 17, 1.4], [33, -12, 1.6], [36, 6, 1.5]],
  natureLane: 56,
  natureFrom: -6,
  heatA: [30, 18.5],
  heatB: [22, 12],
  stones: [[27.5, 10.8], [23.5, 15.7], [20.6, 13.6]],
  // racetrack lanes (straight L, ends of radius rho): the 25-block Tide Dragon never turns tighter than 11 blocks,
  // the Air Dragon banks on 12 (checked by tools/motion_check.py)
  tideC: [30, -20],
  tideL: 2,
  tideRho: 11,
  tideH: 1.6,
  airC: [33, 0],
  airL: 12,
  airRho: 11,
  airH: 14,
  groves: [[20, -21, 0], [17, 21, 1], [31, -27, 2], [29, 25, 3], [53, -20, 0], [56, 15, 1], [12, -15, 3], [13, 15, 2]]
};
function local3(p, yaw, x, z) {
  const f = fromYaw(yaw);
  return add(add(p, mul(f, z)), mul(right(f), x));
}
var ed06_world_before_names_default = defineSpell("ed06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const C0 = { ...caster.location };
  const F = norm(flat(aim.forward));
  const R2 = right(F);
  const W2 = new Frame(C0, F, R2);
  const gy = (p) => groundBelow(dim, { x: p.x, y: Math.max(p.y, C0.y) + 8, z: p.z }, 30).y;
  const ground = (p) => ({ x: p.x, y: gy(p), z: p.z });
  const at = (f, r, h = 0) => up(ground(W2.p(f, r)), h);
  const sky = (f, r, h) => {
    const p = W2.p(f, r);
    return { x: p.x, y: Math.max(C0.y + h, gy(p) + h * 0.75), z: p.z };
  };
  const skyA = (v2) => sky(v2[0], v2[1], v2[2]);
  const awayCaster = (p) => yawOf(flat(sub(p, C0)));
  const faceCaster = (p) => yawOf(flat(sub(C0, p)));
  const foes = (p, r, max) => hostiles(dim, p, r, caster, max);
  const tb = blocksFor(scene);
  const burnT = (e, s) => {
    try {
      e.setOnFire(s, true);
    } catch {
    }
  };
  const movers = [];
  scene.every(1, () => {
    for (const m of movers) m.step(scene.tick);
  }, 0, T_END3);
  const lights = [];
  const light = (p, ticks) => {
    if (!tb.place(p, LIGHT)) return;
    lights.push(p);
    scene.after(ticks, () => tb.remove(p));
  };
  function stream(a, b, ticks, ids, lift = 3, per = 2) {
    const ctl = up(lerp(a, b, 0.5), lift);
    for (let i = 0; i < ticks; i++) {
      scene.after(i, () => {
        for (let j = 0; j < per; j++) {
          const u = clamp((i + j / per) / Math.max(1, ticks - 1), 0, 1);
          particle(dim, ids[(i + j) % ids.length], bezier(a, ctl, b, smooth(u)));
        }
      });
    }
  }
  let Z;
  function zoneNow() {
    let found = [];
    try {
      found = foes(focus(caster, aim, ED06.snap).center, ED06.zoneGroup + 4);
    } catch {
      found = [];
    }
    if (!found.length) found = foes(at(ED06.zoneDefault, 0), ED06.zoneSearch);
    let f = ED06.zoneDefault, r = 0;
    if (found.length) {
      const s0 = found[0];
      const grp = found.filter((e) => distXZ(e.location, s0.location) <= ED06.zoneGroup);
      const m = mul(grp.reduce((s, e) => add(s, e.location), { x: 0, y: 0, z: 0 }), 1 / grp.length);
      const rel = sub(m, C0);
      f = dot(rel, F);
      r = dot(rel, R2);
    }
    f = clamp(f, ED06.zoneMinAhead, ED06.zoneMaxAhead);
    const rm = f * Math.tan(ED06.zoneMaxDeg * Math.PI / 180);
    return at(f, clamp(r, -rm, rm));
  }
  function zone() {
    if (Z) return Z;
    const G = zoneNow();
    const SF2 = ground(add(add(G, mul(R2, ED06.finalRunUp * 0.82)), mul(F, ED06.finalRunUp * 0.4)));
    const L3 = norm(flat(sub(G, SF2)));
    const yawL = yawOf(L3);
    const ringYaw = dot(sub(C0, G), right(L3)) < 0 ? yawL : yawL + 180;
    const TL = ground(loop.at(S_TL_LEN));
    Z = { G, L: L3, yawL, SF: SF2, TL, tideYaw: yawOf(flat(sub(loop.at(S_TL_LEN + 1), loop.at(S_TL_LEN - 1)))), ringYaw };
    return Z;
  }
  const K1 = skyA(ST.codexK1), K2 = skyA(ST.codexK2), K3 = skyA(ST.codexK3);
  const BOOK3 = up(add(add(C0, mul(F, 0.6)), mul(R2, 0.45)), 1.15);
  const codex = scene.spawn("ed6_codex", K1, { yaw: awayCaster(K1), state: CODEX2.rise, skin: 0 });
  const cxMv = new Mover(codex, K1, awayCaster(K1), 0);
  cxMv.maxTurn = 6;
  let cxFlip = false;
  const cxYaw = (t) => {
    const p = cxMv.posAt(t);
    return cxFlip ? faceCaster(p) : awayCaster(p);
  };
  const drift = (P6, amp = 0.45) => (_p, t) => add(P6, { x: amp * Math.sin(t * 0.045), y: 0.3 * Math.sin(t * 0.07 + 1), z: amp * Math.cos(t * 0.045) });
  movers.push(cxMv);
  cxMv.add(T22 - 16, drift(K1), { yaw: cxYaw });
  cxMv.pathIn([K1, sky(34, -8, 11), K2], 54, { ease: smooth, yaw: cxYaw });
  cxMv.add(T52 - cxMv.cursor, drift(K2, 0.8), { yaw: cxYaw });
  const cxAt = () => cxMv.posAt(scene.tick);
  sound(dim, "ed6_codex_rise", BOOK3, 1);
  sound(dim, "ed6_codex_rise", K1, 1.6);
  stream(BOOK3, up(K1, CODEX_CORE), 16, ["ed6_stream", "ed6_codex_rune", "ed6_codex_glint"], 5, 3);
  scene.every(2, (e) => particle(dim, e % 4 ? "ed6_codex_glint" : "ed6_codex_rune", up(cxAt(), 1.5 + e % 3)), 10, 50);
  scene.at(28, () => {
    codex.prop("sep", 1);
    sound(dim, "ed6_codex_unbind", cxAt(), 1.4);
    burst(dim, "ed6_codex_glint", up(cxAt(), 2), 3.5, 8);
    particle(dim, "ed6_ring_v", up(cxAt(), 2.2));
  });
  scene.at(40, () => codex.state(CODEX2.hover));
  const codexBeat = () => {
    codex.state(CODEX2.beat);
    scene.after(12, () => codex.state(CODEX2.hover));
  };
  const cxCore = () => up(cxAt(), CODEX_CORE);
  const EM = ST.emblems.map(([f, r, s]) => ({ at: at(f, r), size: s, c: at(f, r, EMBLEM_C * s) }));
  const emblems = [];
  let level = 0;
  let fog, horizon;
  const flora = [];
  const stones = [];
  function sprout(p, kind, yaw) {
    const a = scene.spawn("ed6_flora", p, { kind, yaw, state: FLORA.sprout });
    scene.after(40, () => a.state(FLORA.sway));
    flora.push({ a, at: p });
    burst(dim, "ed6_pollen_drift", up(p, 3), 2.5, 3);
    sound(dim, "ed6_sprout", p, 1, 0.9 + kind % 3 * 0.08);
  }
  function atmosphere(k2) {
    if (k2 === 0) {
      const hc = at(18, 0);
      horizon = scene.spawn("ed6_horizon", hc, { yaw: yawOf(F), state: HORIZON.rise });
      scene.after(60, () => horizon?.state(HORIZON.hold));
      fog = scene.spawn("ed6_fog", up(at(16, 0), 0.05), { state: 1 });
      sound(dim, "ed6_world_fade", hc, 1, 0.8);
    } else fog?.state(k2 + 1);
    if (k2 === 1) {
      ST.stones.forEach(([f, r], i) => scene.after(i * 5, () => {
        const p = at(f, r);
        stones.push({ a: scene.spawn("ed6_stone", p, { yaw: i * 97 + 20, state: STONE.rise, skin: STONE_SKIN.stone }), at: p, hotUntil: 0 });
        const s = stones[stones.length - 1];
        sound(dim, "ed6_stone_rise", p, 1, 0.9 + i * 0.05);
        particle(dim, "fx_dust", up(p, 0.5));
        particle(dim, "ed6_trail_nature", up(p, 0.4));
        scene.after(26, () => s.a.state(STONE.hold));
      }));
    }
    for (let j = 0; j < 2; j++) {
      const [f, r, kind] = ST.groves[k2 * 2 + j];
      scene.after(4 + j * 7, () => sprout(at(f, r), kind, f * 37 + r * 11));
    }
  }
  let domain;
  scene.at(16, () => {
    domain = scene.spawn("ed6_emblem", ground(C0), { kind: EMBLEM_DOMAIN, size: 2, yaw: yawOf(mul(R2, -1)), state: EMBLEM.appear });
    scene.after(24, () => domain?.state(EMBLEM.glow));
    particle(dim, "ed6_wave", up(ground(C0), 0.2));
    ring(dim, "ed6_rune_rise", up(ground(C0), 0.2), 3.8, 8);
    sound(dim, "ed6_codex_unbind", up(C0, 1), 0.7, 0.8);
  });
  const domainBeat = () => {
    domain?.state(EMBLEM.beat);
    scene.after(16, () => domain?.state(EMBLEM.glow));
  };
  BEATS.forEach((t, k2) => scene.at(t, () => heartbeat(k2)));
  function heartbeat(k2) {
    const e = EM[k2], n = LINEAGE[k2];
    level = k2 + 1;
    const Kc = cxCore();
    sound(dim, `ed6_heart_${n}`, Kc, 1.2);
    sound(dim, `ed6_heart_${n}`, e.c, 1.8);
    codexBeat();
    domainBeat();
    codex.skin(k2 + 1);
    burst(dim, "ed6_codex_glint", Kc, 2.5, 6);
    stream(Kc, e.c, 9, ["ed6_stream", "ed6_codex_rune"], 4, 3);
    scene.after(8, () => {
      const em = scene.spawn("ed6_emblem", e.at, { kind: k2, size: e.size, yaw: faceCaster(e.at), state: EMBLEM.appear });
      emblems[k2] = em;
      scene.after(24, () => em.state(EMBLEM.glow));
      particle(dim, `ed6_flash_${n}`, e.c);
      particle(dim, `ed6_beat_${n}`, up(e.at, 0.2));
      ring(dim, `ed6_rise_${n}`, up(e.at, 0.3), e.size * 2.2, 6, k2 * 30);
      burst(dim, `ed6_burst_${n}`, e.c, 1.5, 4);
      light(up(e.at, 1.5), T42 - scene.tick);
    });
    for (let j = 0; j < k2; j++) {
      const o = emblems[j];
      if (!o?.valid) continue;
      o.state(EMBLEM.beat);
      scene.after(16, () => o.state(EMBLEM.glow));
      particle(dim, `ed6_beat_${LINEAGE[j]}`, up(EM[j].at, 0.2));
      particle(dim, `ed6_flash_${LINEAGE[j]}`, EM[j].c);
    }
    atmosphere(k2);
    const G = zoneNow();
    particle(dim, "ed6_geo_shock", up(G, 0.2));
    for (const f of foes(G, ED06.beatRadius)) {
      damage(f, ED06.beatDamage, caster);
      effect(f, "slowness", ED06.beatSlowTicks, ED06.beatSlowAmp);
      knockback(f, G, ED06.beatKnock, 0.25);
    }
  }
  scene.every(1, (e) => {
    const c = cxCore(), a = e * 23 * Math.PI / 180, r = 3.2 + 0.6 * Math.sin(e * 0.3);
    particle(dim, e % 3 ? "ed6_stream" : "ed6_codex_rune", add(c, add(mul(R2, Math.cos(a) * r), { x: 0, y: Math.sin(a) * r, z: 0 })));
    if (e % 2 === 0) particle(dim, "ed6_codex_glint", add(c, add(mul(R2, Math.cos(a + 3.1) * r * 0.8), { x: 0, y: Math.sin(a + 3.1) * r * 0.8, z: 0 })));
  }, 16, T22 + 20);
  scene.at(T_ALL, () => {
    const Kc = cxCore();
    sound(dim, "ed6_heart_all", Kc, 1.6);
    codexBeat();
    domainBeat();
    particle(dim, "ed6_ring_v", Kc);
    particle(dim, "ed6_wave", up(at(20, 0), 0.3));
    particle(dim, "ed6_wave", up(at(30, 0), 0.3));
    EM.forEach((e, k2) => scene.after(k2 * 2, () => {
      const o = emblems[k2];
      if (!o?.valid) return;
      o.state(EMBLEM.beat);
      scene.after(16, () => o.state(EMBLEM.glow));
      particle(dim, `ed6_flash_${LINEAGE[k2]}`, e.c);
      particle(dim, `ed6_beat_${LINEAGE[k2]}`, up(e.at, 0.2));
      particle(dim, "ed6_column", up(e.at, 0.3));
      ring(dim, `ed6_rise_${LINEAGE[k2]}`, up(e.at, 0.3), e.size * 2, 5, k2 * 20);
      burst(dim, `ed6_burst_${LINEAGE[k2]}`, e.c, 1.5, 4);
      line(dim, "ed6_stream", Kc, e.c, 6);
    }));
  });
  function fadeEmblem(k2) {
    const e = emblems[k2];
    if (!e?.valid) return;
    emblems[k2] = void 0;
    e.state(EMBLEM.fade);
    particle(dim, `ed6_beat_${LINEAGE[k2]}`, up(EM[k2].at, 0.2));
    burst(dim, "ed6_rune_rise", EM[k2].c, 2, 4);
    scene.after(26, () => scene.despawn(e));
  }
  scene.every(100, () => sound(dim, "ed6_ambience", up(at(14, 0), 2), 0.4 + 0.15 * level), BEATS[0], T52 + 120);
  const ZONE_HEAT = { f: 25, r: 13, w: 7, d: 7 }, ZONE_TIDE = { f: 33, r: -12, w: 10, d: 5 }, ZONE_NAT = { f: 50, r: 2, w: 22, d: 6 };
  const inBox = (b, i, s, h) => at(b.f + (hash012(i, s) * 2 - 1) * b.d, b.r + (hash012(i, s + 1) * 2 - 1) * b.w, h);
  let fading = 1;
  scene.every(1, (t) => {
    if (level === 0) return;
    const q = Math.min(4, level) / 4 * fading;
    const h = (k2) => hash012(t, k2);
    if (h(1) < q) particle(dim, "ed6_spore", at(2.5 + h(2) * 7, (h(3) - 0.5) * 14, 0.4 + h(4) * 1.8));
    if (h(5) < q) particle(dim, t % 3 ? "ed6_mote" : "ed6_pollen_drift", at(3 + h(6) * 7, (h(7) - 0.5) * 14, 0.8 + h(8) * 2.4));
    if (t % 4 === 0 && h(9) < q) particle(dim, "ed6_mist", at(3 + h(10) * 6, (h(11) - 0.5) * 12, 0.15));
    for (let j = 0; j < 8; j++) {
      if (h(12 + j) < q) particle(
        dim,
        j % 3 === 2 ? "ed6_spore" : j % 2 ? "ed6_mote" : "ed6_pollen_drift",
        at(9 + h(70 + j) * 23, (h(80 + j) - 0.5) * 46, 0.8 + h(90 + j) * 6)
      );
    }
    if (t % 2 === 1 && h(35) < q) particle(dim, "ed6_rune_rise", at(10 + h(36) * 30, (h(37) - 0.5) * 40, 0.3));
    if (t % 2 === 0 && h(28) < q) particle(dim, "ed6_mist", at(9 + h(29) * 38, (h(30) - 0.5) * 52, 0.3));
    if (h(31) < 0.8 * q) particle(dim, "ed6_mote", at(32 + h(32) * 22, (h(33) - 0.5) * 60, 2 + h(34) * 10));
    for (let j = 0; j < 4; j++) {
      const k2 = 40 + j * 10;
      if (level >= 1) particle(dim, (t + j) % 2 ? "ed6_leaf_fall" : "ed_nature_pollen", inBox(ZONE_NAT, t * 2 + j, k2, 3 + h(k2 + 2) * 9));
      if (level >= 2 && h(k2 + 3) < q) particle(dim, (t + j) % 3 ? "ed6_ember_mote" : "ed6_haze", inBox(ZONE_HEAT, t * 2 + j, k2 + 4, 0.4 + h(k2 + 5) * 4));
      if (level >= 3 && h(k2 + 6) < q) particle(dim, (t + j) % 3 ? "ed6_droplet" : "ed6_snow", inBox(ZONE_TIDE, t * 2 + j, k2 + 7, 1.5 + h(k2 + 8) * 7));
    }
    if (level >= 4 && h(60) < q) particle(dim, t % 3 ? "ed6_wind" : "ed6_mote", sky(24 + h(61) * 26, (h(62) - 0.5) * 46, 10 + h(63) * 8));
    for (let k2 = 0; k2 < 4; k2++) if (emblems[k2]?.valid && (t + k2) % 2 === 0) particle(dim, "ed6_rune_rise", up(EM[k2].at, 0.5));
    if (t % 2 === 0) particle(dim, t % 6 === 0 ? "ed6_codex_glint" : "ed6_codex_rune", up(cxAt(), 1.2 + h(64) * 2.5));
  }, 0, T_END3 - 20);
  const nYaw0 = yawOf(R2);
  const nPos = (r) => W2.p(ST.natureLane, r);
  let nR = ST.natureFrom;
  const N0 = ground(nPos(nR));
  const nature = scene.spawn(NATURE.actor, N0, { yaw: nYaw0, state: N2.hidden, skin: N_SKIN.normal });
  const natMv = new Mover(nature, N0, nYaw0, T_NATURE, gy).govern({
    gaits: [{ state: N2.move, speed: N_WALK }],
    free: [N2.arrive, N2.depart],
    turn: { left: N2.turn_l, right: N2.turn_r, above: 7 },
    idle: N2.idle
  });
  const footprints = [];
  let nWalking = false;
  const DR_ = N_WALK / 20;
  const nWalk = (cycles) => {
    const r0 = nR, from = natMv.cursor, ticks = cycles * N_CYCLE;
    natMv.add(ticks, (p) => nPos(r0 + DR_ * p * ticks), { yaw: nYaw0, tag: "walk" });
    scene.at(from, () => {
      nature.state(N2.move);
      nWalking = true;
    });
    for (let c = 0; c < cycles; c++) {
      for (const s of N_STEPS) {
        const tt = from + c * N_CYCLE + s.t;
        const rAt = r0 + DR_ * (c * N_CYCLE + s.t);
        scene.at(tt, () => footfall(ground(local3(nPos(rAt), nYaw0, s.x, s.z))));
      }
    }
    nR = r0 + DR_ * ticks;
    scene.at(from + ticks, () => {
      nature.state(N2.idle);
      nWalking = false;
    });
  };
  function footfall(p) {
    footprints.push(p);
    if (footprints.length > 12) footprints.shift();
    const q = scene.spawn("ed_nature_quake", up(p, 0.02), { size: 1.6, state: 1, yaw: scene.tick * 47 % 360 });
    scene.after(27, () => scene.despawn(q));
    particle(dim, "ed_nature_shock", up(p, 0.15));
    particle(dim, "ed6_trail_nature", up(p, 0.5));
    particle(dim, "ed6_trail_nature", up(p, 1.2));
    particle(dim, "ed_nature_rock", up(p, 0.4));
    sound(dim, "ed_nature_step", p, 1.4);
    for (const e of foes(p, ED06.stepRadius)) {
      damage(e, ED06.stepDamage, caster);
      knockback(e, p, ED06.stepKnockH, ED06.stepKnockV);
    }
  }
  const nHold = (ticks, yaw) => {
    natMv.hold(ticks, yaw ?? nYaw0);
  };
  const nHead = () => up(local3(natMv.posAt(scene.tick), natMv.lastYaw, 0, N_HEAD.ahead), N_HEAD.up);
  const nBack = () => up(natMv.posAt(scene.tick), 10);
  const strataI = [];
  scene.at(T_NATURE - 12, () => {
    sound(dim, "ed_nature_rumble", N0, 2);
    [[0, 10, 2], [6, 3, 1.8], [-6, 3, 1.7], [0, -8, 1.6]].forEach(([x, z, size], k2) => scene.after(k2 * 3, () => {
      const p = ground(local3(N0, nYaw0, x, z));
      strataI.push(scene.spawn("ed_nature_strata", p, { yaw: k2 * 83, size, state: STRATA2.rise }));
      burst(dim, "ed6_trail_nature", up(p, 1), 3, 3);
      particle(dim, "ed_nature_rise", p);
      if (k2 % 2 === 0) sound(dim, "ed_nature_strata", p, 1.5, 0.9 + k2 * 0.05);
    }));
  });
  scene.at(T_NATURE + 6, () => strataI.forEach((s) => s.state(STRATA2.hold)));
  scene.at(T_NATURE, () => {
    nature.state(N2.arrive);
    movers.push(natMv);
    sound(dim, "ed_nature_call", up(N0, 10), 2);
    particle(dim, "ed6_flash_nature", up(N0, 3));
  });
  scene.at(T_NATURE + 14, () => fadeEmblem(0));
  scene.at(T_NATURE + 18, () => {
    strataI.forEach((s) => s.state(STRATA2.part));
    sound(dim, "ed_nature_erupt", N0, 1.6);
  });
  scene.every(1, (e) => {
    const p = local3(N0, nYaw0, (hash012(e, 40) - 0.5) * 10, (hash012(e, 41) - 0.5) * 24);
    particle(dim, "ed6_trail_nature", up(ground(p), 1 + hash012(e, 42) * 5));
    particle(dim, e % 2 ? "ed_nature_rock" : "ed6_leaf_fall", up(ground(p), 2 + hash012(e, 43) * 6));
  }, T_NATURE + 4, T_NATURE + 56);
  scene.at(T_NATURE + N_T.arriveLand, () => {
    for (const x of [-3, 3]) {
      const p = ground(local3(N0, nYaw0, x, 5.5));
      footprints.push(p);
      const q = scene.spawn("ed_nature_quake", up(p, 0.02), { size: 2.2, state: 1 });
      scene.after(27, () => scene.despawn(q));
      particle(dim, "ed_nature_shock_big", up(p, 0.2));
      burst(dim, "ed6_trail_nature", up(p, 1), 2.5, 4);
      sound(dim, "ed_nature_quake", p, 1.8);
    }
    particle(dim, "ed6_wave", up(N0, 0.3));
    for (const e of foes(local3(N0, nYaw0, 0, 5), ED06.natureLandRadius)) {
      damage(e, ED06.natureLandDamage, caster);
      knockback(e, N0, ED06.stepKnockH * 1.5, ED06.stepKnockV);
    }
  });
  scene.at(T_NATURE + 70, () => strataI.forEach((s) => s.state(STRATA2.crumble)));
  scene.at(T_NATURE + 94, () => strataI.forEach((s) => scene.despawn(s)));
  const tPow = T_NATURE + 66;
  scene.at(tPow, () => {
    nature.state(N2.power);
    sound(dim, "ed_nature_grow", nBack(), 1.8);
  });
  scene.at(tPow + 20, () => {
    nature.skin(N_SKIN.bloom);
    particle(dim, "ed6_flash_nature", nBack());
  });
  scene.every(6, (e) => {
    burst(dim, "ed_nature_leaf", up(nBack(), 1), 5, 3);
    particle(dim, "ed_nature_pollen", up(nBack(), 3));
    particle(dim, "ed6_leaf_fall", local3(nBack(), nYaw0, 0, (hash012(e, 44) - 0.5) * 14));
  }, tPow + 10, tPow + 54);
  nHold(tPow + N_T.power - T_NATURE);
  nWalk(1);
  nHold(T32 - natMv.cursor);
  const natStructs = [];
  const T3w = natMv.cursor, r3 = nR;
  nWalk(2);
  [0, 1].forEach((c) => scene.at(T3w + c * N_CYCLE + 10, () => {
    const rr = r3 + DR_ * (c * N_CYCLE + 10);
    const p = nPos(rr);
    const out = ground(local3(p, nYaw0, -7.5, 3 + c * 4));
    const s = scene.spawn("ed_nature_strata", out, { yaw: c * 97 + 40, size: 1.5, state: STRATA2.rise });
    natStructs.push(s);
    scene.after(18, () => s.state(STRATA2.hold));
    sound(dim, "ed_nature_strata", out, 1.4, 0.95);
    burst(dim, "ed6_trail_nature", up(out, 1), 3, 3);
    const inn = ground(local3(p, nYaw0, 7, -4 + c * 9));
    sprout(inn, c === 0 ? 0 : 3, c * 140 + 30);
    burst(dim, "ed_nature_leaf", up(inn, 2), 2, 3);
  }));
  const tLash = natMv.cursor + 8;
  nHold(8);
  nHold(N_T.attackB);
  scene.at(tLash, () => {
    nature.state(N2.attack_b);
    sound(dim, "ed_nature_lash", nHead(), 1.6);
  });
  scene.at(tLash + N_T.attackBHit, () => {
    const p = natMv.posAt(scene.tick);
    const hit = ground(local3(p, nYaw0, 3, 12));
    particle(dim, "ed_nature_shock_big", up(hit, 0.2));
    burst(dim, "ed6_trail_nature", up(hit, 1), 3, 4);
    burst(dim, "ed_nature_leaf", up(hit, 2), 3, 3);
    for (const e of foes(hit, ED06.lashRadius)) {
      damage(e, ED06.lashDamage, caster);
      knockback(e, p, 1.6, 0.5);
    }
  });
  scene.at(tLash + N_T.attackB, () => nature.state(N2.idle));
  nHold(T42 - natMv.cursor);
  const binds = [];
  scene.at(T32 + 26, () => {
    const from = footprints.length ? footprints.slice(-4) : [N0];
    const found = foes(zoneNow(), ED06.rootRadius, ED06.maxRoots);
    const goals = found.length ? found.map((e) => ({ e, at: { ...e.location } })) : [-4, 0, 4].map((r) => ({ at: at(ED06.zoneDefault + 1, r) }));
    goals.forEach((g, k2) => scene.after(k2 * 4, () => {
      const target = g.e && isAlive(g.e) ? { ...g.e.location } : g.at;
      const fp = from[k2 % from.length];
      const dirIn = norm(flat(sub(target, fp)));
      const reach = Math.min(9, Math.max(3, distXZ(fp, target)));
      const start = ground(sub(target, mul(dirIn, reach)));
      const runT = 16;
      for (let i = 0; i <= runT; i += 2) {
        scene.after(i, () => {
          const q = lerp(fp, start, i / runT);
          particle(dim, "ed6_trail_nature", up(ground(q), 0.4));
          if (i % 4 === 0) particle(dim, "ed_nature_rock", up(ground(q), 0.3));
        });
      }
      scene.after(runT, () => {
        const size = clamp(reach / ROOT_LEN2, 0.5, 1.6);
        const yaw = yawOf(sub(target, start));
        const tip = ground(add(start, mul(fromYaw(yaw), ROOT_LEN2 * size)));
        const root = scene.spawn("ed_nature_root", up(start, 0.05), { yaw, size, state: ROOT2.grow });
        const b = { e: g.e, root, tip };
        binds.push(b);
        sound(dim, "ed_nature_root", start, 1.2);
        particle(dim, "ed_nature_shock", up(start, 0.2));
        scene.after(ROOT_BIND2 - 3, () => {
          particle(dim, "ed_nature_spore", up(tip, 1));
          particle(dim, "ed6_burst_nature", up(tip, 1));
          sound(dim, "ed_nature_bind", tip, 1.2);
          if (b.e && isAlive(b.e)) {
            damage(b.e, ED06.rootDamage, caster);
            restrain(scene, b.e, ED06.rootHoldTicks, { x: tip.x, y: Math.max(tip.y, b.e.location.y - 0.5), z: tip.z });
          }
        });
        scene.after(26, () => root.state(ROOT2.hold));
        if (k2 < ED06.maxPillars) scene.after(30, () => {
          const side = norm(flat(sub(tip, C0)));
          const p = ground(add(tip, mul(side, 2.6)));
          const pil = scene.spawn("ed_nature_pillar", p, { yaw: yawOf(sub(tip, p)), size: 0.72, state: PILLAR2.rise });
          b.pillar = pil;
          sound(dim, "ed_nature_pillar", p, 1.2);
          particle(dim, "ed_nature_rise", p);
          particle(dim, "ed_nature_rock", up(p, 1));
          burst(dim, "ed6_trail_nature", up(p, 0.8), 1.5, 2);
          for (const e of foes(p, 1.8)) {
            damage(e, ED06.pillarDamage, caster);
            shove(e, sub(tip, p), 0.7, 0.4);
          }
          scene.after(8, () => {
            b.cells = [p];
            tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), ED06.pillarBarrierHeight);
          });
          scene.after(16, () => pil.state(PILLAR2.hold));
        });
        scene.after(ROOT_BIND2 + ED06.rootHoldTicks, () => {
          root.state(ROOT2.wither);
          scene.after(22, () => scene.despawn(root));
        });
      });
    }));
  });
  scene.at(T42 - 30, () => {
    binds.forEach((b, i) => scene.after(i * 3, () => {
      if (b.cells) for (const c of b.cells) tb.removeColumn(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), ED06.pillarBarrierHeight);
      if (b.pillar) {
        b.pillar.state(PILLAR2.crumble);
        particle(dim, "ed6_trail_nature", up(b.pillar.loc, 1));
        const p = b.pillar;
        scene.after(20, () => scene.despawn(p));
      }
    }));
  });
  const HA = at(ST.heatA[0], ST.heatA[1]), HB = at(ST.heatB[0], ST.heatB[1]);
  const dAB = norm(flat(sub(HB, HA)));
  const wallAt = EM[1].at;
  const H1 = ground(sub(wallAt, mul(dAB, 7)));
  const H0 = ground(sub(H1, mul(dAB, H_WALK / 20 * H_T.arriveWalk)));
  const yawIn = yawOf(dAB);
  const heat = scene.spawn(HEAT.actor, H0, { yaw: yawIn, state: H.hidden, skin: H_SKIN.cool });
  const heatMv = new Mover(heat, H0, yawIn, T_HEAT, gy).govern({
    gaits: [{ state: H.walk, speed: H_WALK }, { state: H.move, speed: H_RUN }, { state: H.charge, speed: H_RUN }],
    free: [H.arrive, H.skid, H.depart],
    turn: { left: H.turn_l, right: H.turn_r, above: 40 },
    idle: H.idle
  });
  let planYaw = yawIn;
  let hHits = /* @__PURE__ */ new Set();
  let hDir = dAB;
  let hFinal = false, detonated = false;
  let hStart = H0;
  const glasses = [];
  let glassNext = 0;
  function hTurn(yawTo) {
    const d = angleDelta(planYaw, yawTo);
    planYaw = yawTo;
    if (Math.abs(d) < 6) return;
    const ticks = Math.max(6, Math.round(Math.abs(d) / (H_TURN / 1.5) * 20));
    const y0 = yawTo - d, t0 = heatMv.cursor;
    scene.at(t0, () => heat.state(d > 0 ? H.turn_r : H.turn_l));
    heatMv.hold(ticks, void 0, "turn");
    heatMv.segs[heatMv.segs.length - 1].yaw = (t) => y0 + d * smooth((t - t0) / ticks);
  }
  function hCharge(to, opts = {}) {
    const from = { ...heatMv.last };
    const dir = norm(flat(sub(to, from)));
    hTurn(yawOf(dir));
    const D_ = distXZ(from, to);
    const skidD = H_RUN / 20 * (H_T.skid - 1) / 2;
    const runD = Math.max(0.5, D_ - skidD);
    const prof = [0];
    for (let s = 0, k2 = 0; s < runD; k2++) {
      s = Math.min(runD, s + H_RUN / 20 * (k2 < 6 ? 0.45 + 0.55 * k2 / 6 : 1));
      prof.push(s);
    }
    const n = prof.length - 1;
    const t0 = heatMv.cursor;
    const yaw = yawOf(dir);
    const runEnd = add(from, mul(dir, runD));
    heatMv.add(n, (p) => {
      const f = p * n, i = Math.min(n - 1, Math.floor(f));
      return add(from, mul(dir, prof[i] + (prof[i + 1] - prof[i]) * (f - i)));
    }, { yaw, tag: opts.run ? "run" : "charge" });
    heatMv.add(H_T.skid, (p) => add(runEnd, mul(dir, skidD * (1 - (1 - p) * (1 - p)))), { yaw, tag: opts.run ? "skidrun" : "skid" });
    const tEnd = heatMv.cursor;
    let lane;
    if (opts.lane) {
      scene.at(Math.max(scene.tick, t0 - 16), () => {
        lane = scene.spawn("ed_heat_lane", ground(add(from, mul(dir, 3.5))), { yaw, state: LANE2.appear });
        lane.prop("len", clamp(D_ + 2, 4, 40));
        sound(dim, "ed_heat_lane", from, 1.1);
      });
      scene.at(t0, () => lane?.state(opts.final ? LANE2.surge : LANE2.armed));
      scene.at(tEnd, () => {
        lane?.state(LANE2.fade);
        const l = lane;
        scene.after(10, () => {
          if (l) scene.despawn(l);
        });
      });
    }
    scene.at(t0, () => {
      heat.state(opts.run ? H.move : H.charge);
      hHits = /* @__PURE__ */ new Set();
      hDir = dir;
      hFinal = !!opts.final;
      hStart = from;
      glassNext = 0;
      if (!opts.run) sound(dim, "ed_heat_roar", up(from, 4), 1.6, 1.05);
    });
    scene.at(t0 + n, () => {
      heat.state(H.skid);
      sound(dim, "ed_heat_skid", runEnd, 1.3);
      particle(dim, "ed_heat_skid", up(runEnd, 0.3));
      burst(dim, "ed6_trail_nature", up(runEnd, 0.6), 1.5, 3);
    });
    return tEnd;
  }
  function heatTick(t) {
    const seg = heatMv.segAt(t);
    if (!seg || !seg.tag || seg.tag === "turn") return;
    const pos = heatMv.posAt(t);
    const moving = seg.tag === "charge" || seg.tag === "skid";
    for (const s of stones) {
      if (hFinal && !s.gone && distXZ(s.at, pos) < 3.6) {
        s.gone = true;
        s.a.skin(STONE_SKIN.glass).state(STONE.sink);
        sound(dim, "ed6_vitrify", s.at, 1.6, 0.8);
        burst(dim, "ed6_glass_shard", up(s.at, 2), 1.5, 3);
        particle(dim, "ed6_thermal", up(s.at, 1.5));
        particle(dim, "ed6_flash_heat", up(s.at, 2));
        for (const e of foes(s.at, ED06.vitrifyRadius)) {
          damage(e, ED06.vitrifyDamage, caster);
          burnT(e, ED06.burnSeconds);
        }
      }
      if (s.gone || t < s.hotUntil || distXZ(s.at, pos) > ED06.vitrifyReach) continue;
      s.hotUntil = t + 130;
      s.a.skin(STONE_SKIN.glass).state(STONE.flare);
      scene.after(10, () => s.a.state(STONE.hold));
      scene.after(120, () => s.a.skin(STONE_SKIN.obsidian));
      sound(dim, "ed6_vitrify", s.at, 1.3);
      particle(dim, "ed6_sizzle", up(s.at, 2));
      particle(dim, "ed6_glass_shard", up(s.at, 2.5));
      particle(dim, "ed6_flash_heat", up(s.at, 2));
      light(up(s.at, 4), 120);
      for (const e of foes(s.at, ED06.vitrifyRadius)) {
        damage(e, ED06.vitrifyDamage, caster);
        burnT(e, ED06.burnSeconds);
      }
    }
    if (!moving) return;
    if (t % 2 === 0) particle(dim, "ed6_trail_heat", up(add(pos, mul(hDir, -2)), 0.4));
    const along = dot(sub(pos, hStart), hDir);
    if (seg.tag === "charge" && along >= glassNext) {
      glassNext = along + ED06.glassEvery;
      const g = scene.spawn(
        "ed_heat_glass",
        ground(add(pos, mul(right(hDir), glasses.length % 2 ? 0.8 : -0.8))),
        { yaw: glasses.length * 67, state: GLASS2.appear }
      );
      const rec = { a: g, at: g.loc, born: t };
      glasses.push(rec);
      if (glasses.length % 3 === 1) sound(dim, "ed_heat_glass", rec.at, 1);
      scene.after(6, () => g.state(GLASS2.hold));
      scene.after(80, () => g.skin(1));
      scene.after(ED06.glassLifeTicks, () => g.state(GLASS2.fade));
      scene.after(ED06.glassLifeTicks + 17, () => {
        scene.despawn(g);
        glasses.splice(glasses.indexOf(rec), 1);
      });
    }
    const rv = right(hDir);
    for (const e of foes(add(pos, mul(hDir, 3)), 10)) {
      if (hHits.has(e.id)) continue;
      const dy = e.location.y - pos.y;
      if (dy > 7 || dy < -3) continue;
      const rel = flat(sub(e.location, pos));
      const a = dot(rel, hDir), lat = Math.abs(dot(rel, rv));
      const away = norm(add(mul(rv, dot(rel, rv) >= 0 ? 1 : -1), mul(hDir, 0.45)));
      if (a > 2 && a < H_HORN + 1.5 && lat < ED06.chargeHalfWidth) {
        hHits.add(e.id);
        if (damage(e, hFinal ? ED06.finalHornDamage : ED06.hornDamage, caster)) shove(e, away, ED06.chargeKnockH, ED06.chargeKnockV);
        burnT(e, ED06.burnSeconds);
        particle(dim, "ed_heat_spark", up(e.location, 1.1));
        particle(dim, "ed6_burst_heat", up(e.location, 1.2));
        sound(dim, "ed_heat_hit", e.location, 1.2);
      } else if (a > -3 && a <= 2 && lat < ED06.chargeHalfWidth + 0.6) {
        hHits.add(e.id);
        if (damage(e, ED06.bodyDamage, caster)) shove(e, away, ED06.chargeKnockH * 0.8, ED06.chargeKnockV);
        burnT(e, ED06.burnSeconds);
        particle(dim, "ed_heat_ember", up(e.location, 1));
      }
    }
    if (hFinal && !detonated && Z && dot(sub(pos, Z.G), Z.L) >= -0.5) detonate();
  }
  scene.every(1, () => heatTick(scene.tick), T_HEAT, T52);
  scene.every(20, () => {
    for (const g of glasses) {
      if (scene.tick - g.born > 80) continue;
      for (const e of foes(g.at, ED06.glassBurnRadius)) {
        damage(e, ED06.glassBurnDamage, caster);
        burnT(e, 1);
      }
    }
  }, T_HEAT, T52);
  let wall;
  scene.at(T_HEAT - 4, () => {
    fadeEmblem(1);
    wall = scene.spawn("ed_heat_shimmer", wallAt, { yaw: yawIn, state: WALL3.form });
    sound(dim, "ed_heat_shimmer", wallAt, 1.5);
    particle(dim, "ed6_flash_heat", up(wallAt, 3));
  });
  scene.every(1, (e) => {
    particle(dim, e % 4 ? "ed6_haze" : "ed_heat_haze", up(add(wallAt, mul(right(dAB), e * 7 % 9 - 4)), 0.5 + e % 4));
    particle(dim, e % 2 ? "ed6_ember_mote" : "ed6_trail_heat", up(add(wallAt, mul(right(dAB), e * 5 % 9 - 4)), 1 + e % 5));
  }, T_HEAT - 4, T_HEAT + 76);
  scene.at(T_HEAT, () => {
    heat.state(H.arrive);
    movers.push(heatMv);
    sound(dim, "ed_heat_snarl", up(H0, 3), 1.4);
  });
  heatMv.add(H_T.arriveWalk, (p) => lerp(H0, H1, p), { yaw: yawIn, tag: "walk" });
  heatMv.hold(H_T.ignite + 6, yawIn);
  const tIgn = T_HEAT + H_T.arriveWalk + 6;
  scene.at(tIgn, () => {
    heat.state(H.ignite);
    sound(dim, "ed_heat_ignite", up(H1, 4), 1.6);
  });
  scene.at(tIgn + 10, () => {
    heat.skin(H_SKIN.ignited);
    burst(dim, "ed6_trail_heat", up(H1, 4), 2.4, 5);
  });
  scene.at(tIgn + H_T.igniteRoar, () => {
    particle(dim, "ed_heat_ring", up(H1, 0.3));
    particle(dim, "ed6_flash_heat", up(H1, 4));
    ring(dim, "ed_heat_vent", up(H1, 3.5), 2.8, 6);
    for (const e of foes(H1, 5)) {
      damage(e, ED06.bodyDamage, caster);
      knockback(e, H1, 0.8, 0.35);
    }
  });
  const tArrEnd = hCharge(HB, { lane: true });
  const tArrRun = tIgn + H_T.ignite;
  scene.at(tArrRun - 2, () => wall?.state(WALL3.part));
  scene.at(tArrRun + 10, () => {
    heat.skin(H_SKIN.whitehot);
    particle(dim, "ed6_flash_heat", up(heatMv.posAt(scene.tick), 4));
  });
  scene.at(tArrRun + 18, () => wall?.state(WALL3.fade));
  scene.at(tArrRun + 34, () => {
    if (wall) scene.despawn(wall);
  });
  scene.at(tArrEnd, () => {
    heat.state(H.pant).skin(H_SKIN.ignited);
  });
  heatMv.hold(Math.max(1, T32 - 6 - heatMv.cursor));
  let atA = false, chords = 0, waved = false;
  function heatPlan() {
    if (heatMv.cursor + 80 > T42 + 30) {
      heatToFinal();
      return;
    }
    if (!atA && chords >= 2 && !waved) {
      heatWave();
      return;
    }
    const to = atA ? HB : HA;
    const end = hCharge(to);
    atA = !atA;
    chords++;
    scene.at(end, () => {
      heat.state(H.pant);
      particle(dim, "ed_heat_steam", up(heatMv.posAt(scene.tick), 3));
    });
    heatMv.hold(10);
    scene.at(heatMv.cursor, heatPlan);
  }
  function heatWave() {
    waved = true;
    const from = { ...heatMv.last };
    const G = zoneNow();
    const dir = norm(flat(sub(G, from)));
    hTurn(yawOf(dir));
    const tR = heatMv.cursor;
    heatMv.hold(H_T.roar + 6, yawOf(dir));
    scene.at(tR, () => {
      heat.state(H.roar);
      sound(dim, "ed_heat_roar", up(from, 4), 1.8, 0.95);
    });
    const s0 = ground(add(from, mul(dir, 4))), dist2 = Math.max(4, distXZ(s0, G) + 2);
    const ticks = Math.round(dist2 / 9 * 20);
    let wave;
    const hitW = /* @__PURE__ */ new Set();
    scene.at(tR + 12, () => {
      sound(dim, "ed_heat_wave", s0, 1.8);
      particle(dim, "ed6_flash_heat", up(from, 4));
      particle(dim, "ed_heat_ring", up(from, 0.3));
      wave = scene.spawn("ed_heat_wave", s0, { yaw: yawOf(dir), state: 1 });
      scene.after(7, () => wave?.state(2));
    });
    scene.span(tR + 13, tR + 13 + ticks, (p, e) => {
      const fp = ground(add(s0, mul(dir, dist2 * p)));
      wave?.move(fp, yawOf(dir));
      if (e % 2 === 0) particle(dim, "ed_heat_wavefront", up(fp, 1.2));
      if (e % 2 === 1) particle(dim, "ed6_trail_heat", up(fp, 0.8));
      if (e % 3 === 0) particle(dim, "ed6_haze", up(fp, 0.5));
      for (const t of foes(fp, 4.5)) {
        if (hitW.has(t.id)) continue;
        hitW.add(t.id);
        if (damage(t, ED06.heatWaveDamage, caster)) {
          shove(t, dir, 0.9, 0.35);
          burnT(t, ED06.burnSeconds);
        }
        particle(dim, "ed_heat_ember", up(t.location, 1));
      }
    });
    scene.at(tR + 13 + ticks, () => {
      wave?.state(3);
      particle(dim, "ed_heat_wavefront", up(G, 1));
      particle(dim, "ed6_burst_heat", up(G, 1.5));
      const w = wave;
      scene.after(12, () => {
        if (w) scene.despawn(w);
      });
    });
    scene.at(heatMv.cursor, () => heat.state(H.pant));
    heatMv.hold(8);
    scene.at(heatMv.cursor, heatPlan);
  }
  scene.at(T32 - 6, () => {
    heatMv.truncate(T32 - 6);
    planYaw = heatMv.lastYaw;
    heatPlan();
  });
  const TC = sky(ST.tideC[0], ST.tideC[1], ST.tideH);
  const tideLane = stadium(TC, R2, F, ST.tideL, ST.tideRho);
  const S_TL = (ST.tideL + ST.tideRho * (120 * Math.PI / 180)) / (2 * ST.tideL + 2 * Math.PI * ST.tideRho);
  const loop = new ArcPath((u) => {
    const p = tideLane(u);
    return { x: p.x, y: TC.y + 1.3 * Math.sin(u * 4 * Math.PI + 0.6), z: p.z };
  }, 160, true);
  const loopTan = (s) => yawOf(sub(loop.at(s + 0.5), loop.at(s - 0.5)));
  const S_TL_LEN = S_TL * loop.length;
  const M0 = loop.at(0);
  const tide = scene.spawn(TIDE.actor, M0, { yaw: loopTan(0), state: D3.hidden, skin: 0 });
  const tideMv = new Mover(tide, M0, loopTan(0), T_TIDE).govern({
    gaits: [{ state: D3.move, speed: 2.5 }, { state: D3.swim, speed: D_SWIM }],
    free: [D3.arrive, D3.land, D3.depart],
    turn: { left: D3.turn_l, right: D3.turn_r, above: 30 },
    idle: D3.idle,
    swims: true
  });
  tideMv.maxTurn = 12;
  const tSwim2 = T_TIDE + D_T.arrive;
  tideMv.hold(D_T.arrive, loopTan(0));
  tideMv.add(T42 - tSwim2 + 200, (_p, t) => loop.at(D_SWIM / 20 * (t - tSwim2)), { tag: "swim" });
  const tideS = (t) => D_SWIM / 20 * Math.max(0, t - tSwim2);
  let mass;
  const streamsIn = [];
  scene.at(T_TIDE - 20, () => {
    fadeEmblem(2);
    mass = scene.spawn("ed_tide_mass", M0, { state: MASS2.gather, size: 1.2 });
    sound(dim, "ed_tide_mass", M0, 1.6);
    sound(dim, "ed_tide_currents", M0, 1.3);
    for (let k2 = 0; k2 < 4; k2++) {
      const ang = k2 * 90 + 20;
      const p0 = up(W2.polar(9, ang, 0, M0), -0.8 + k2 % 2 * 2.5);
      streamsIn.push({ a: scene.spawn("ed_tide_stream", p0, { state: STREAM2.form, size: 1.3, yaw: yawOf(sub(M0, p0)) }), ang, prev: p0 });
    }
  });
  scene.at(T_TIDE - 12, () => streamsIn.forEach((s) => s.a.state(STREAM2.hold)));
  scene.span(T_TIDE - 19, T_TIDE + 4, (p) => {
    const e = smooth(p);
    for (const s of streamsIn) {
      const pos = up(W2.polar(9 * (1 - e) + 0.4, s.ang + 200 * e, 0, M0), (-0.8 + streamsIn.indexOf(s) % 2 * 2.5) * (1 - e));
      s.a.move(pos, yawOf(flat(sub(pos, s.prev))));
      s.prev = pos;
      particle(dim, "ed6_trail_tide", pos);
    }
  });
  scene.at(T_TIDE + 2, () => {
    streamsIn.forEach((s) => s.a.state(STREAM2.fade));
    burst(dim, "ed_tide_bubble", M0, 3, 5);
  });
  scene.at(T_TIDE + 8, () => streamsIn.forEach((s) => scene.despawn(s.a)));
  scene.at(T_TIDE + 2, () => mass?.state(MASS2.hold));
  scene.at(T_TIDE, () => {
    tide.state(D3.arrive);
    movers.push(tideMv);
    sound(dim, "ed_tide_emerge", M0, 1.6);
    particle(dim, "ed6_flash_tide", M0);
  });
  scene.at(tSwim2, () => {
    tide.state(D3.swim);
    burst(dim, "ed_tide_splash", M0, 3, 6);
    sound(dim, "ed_tide_roar", M0, 1.4);
  });
  scene.at(tSwim2 + 40, () => mass?.state(MASS2.disperse));
  scene.at(tSwim2 + 62, () => {
    if (mass) scene.despawn(mass);
    mass = void 0;
  });
  for (let k2 = 1; k2 <= 10; k2++) scene.at(tSwim2 + k2 * 7, () => tide.prop("frost", k2 / 10));
  scene.at(tSwim2 + 30, () => {
    tide.skin(1);
    sound(dim, "ed_tide_freeze", tideMv.posAt(scene.tick), 1.3, 1.2);
  });
  const wake = [];
  scene.at(tSwim2 + 20, () => {
    for (const lag of [16, 21]) wake.push(scene.spawn("ed_tide_stream", loop.at(-lag), { state: STREAM2.form, size: 1.2 }));
  });
  scene.at(tSwim2 + 28, () => wake.forEach((w) => w.state(STREAM2.hold)));
  scene.every(1, () => {
    const s = tideS(scene.tick);
    [16, 21].forEach((lag, i) => wake[i]?.move(loop.at(s - lag), loopTan(s - lag)));
  }, tSwim2 + 20, T42 + 40);
  scene.at(T42 + 40, () => wake.forEach((w) => w.state(STREAM2.fade)));
  scene.at(T42 + 50, () => wake.forEach((w) => scene.despawn(w)));
  const tideHit = /* @__PURE__ */ new Map();
  scene.every(4, () => {
    const t = scene.tick, s = tideS(t);
    const p = ground(loop.at(s)), back = ground(loop.at(s - 10));
    const dir = norm(flat(sub(p, back)));
    if (t % 8 === 0) particle(dim, "ed_tide_spray", up(back, 0.5));
    for (const e of foes(lerp(p, back, 0.5), 8)) {
      if (distToSegment(e.location, p, back) > ED06.currentReach) continue;
      shove(e, dir, ED06.currentShove, 0.1);
      const last = tideHit.get(e.id) ?? -999;
      if (t - last > 50) {
        tideHit.set(e.id, t);
        damage(e, ED06.currentDamage, caster);
        particle(dim, "ed_tide_spray", e.location);
      }
    }
  }, tSwim2 + 10, T42 + 40);
  const lobes = [];
  scene.at(T32 - 12, () => {
    for (const u of [0.25, 0.75]) {
      const p = up(loop.at(loop.length * u), 0.5);
      lobes.push(scene.spawn("ed_tide_mass", p, { state: MASS2.gather, size: 0.8 }));
      sound(dim, "ed_tide_mass", p, 1.2, 1.2);
    }
  });
  scene.at(T32 + 8, () => lobes.forEach((l) => l.state(MASS2.hold)));
  scene.at(T42 + 20, () => lobes.forEach((l) => l.state(MASS2.disperse)));
  scene.at(T42 + 40, () => lobes.forEach((l) => scene.despawn(l)));
  const bridges = [];
  function bridge(a, b) {
    const L_ = distXZ(a, b);
    if (L_ < 5) return void 0;
    const br = scene.spawn("ed6_bridge", up(a, 0.1), { yaw: yawOf(sub(b, a)), size: L_ / BRIDGE_LEN, state: BRIDGE2.form });
    bridges.push(br);
    sound(dim, "ed6_bridge", lerp(a, b, 0.5), 1.5);
    line(dim, "ed6_snow", up(a, 2), up(b, 2), 5);
    scene.after(26, () => br.state(BRIDGE2.hold));
    scene.after(12, () => {
      line(dim, "ed_tide_frostline", up(a, 3), up(b, 3), 6);
      for (const e of foes(lerp(a, b, 0.5), L_ / 2 + ED06.bridgeWidth)) {
        if (distToSegment(e.location, a, b) > ED06.bridgeWidth) continue;
        damage(e, ED06.bridgeDamage, caster);
        effect(e, "slowness", ED06.bridgeSlowTicks, ED06.bridgeSlowAmp);
        particle(dim, "ed_tide_splinter", up(e.location, 1));
      }
    });
    return br;
  }
  [T32 + 24, T32 + 150].forEach((t) => scene.at(t, () => {
    const s = tideS(t);
    bridge(ground(loop.at(s - 14)), ground(loop.at(s)));
  }));
  scene.at(T32 + 90, () => {
    const G = zoneNow(), a = at(23, -10);
    const br = bridge(a, ground(add(G, mul(norm(flat(sub(G, a))), 1.5))));
    sound(dim, "ed_tide_roar", tideMv.posAt(scene.tick), 1.6, 1.1);
    if (!br) return;
    scene.at(T42 - 14, () => {
      br.state(BRIDGE2.shatter);
      sound(dim, "ed_tide_shatter", br.loc, 1.3);
      burst(dim, "ed6_snow", up(lerp(br.loc, G, 0.5), 3), 3, 4);
      burst(dim, "ed_tide_splinter", up(lerp(br.loc, G, 0.5), 3), 3, 3);
    });
    scene.at(T42 + 4, () => {
      bridges.splice(bridges.indexOf(br), 1);
      scene.despawn(br);
    });
  });
  const airC = sky(ST.airC[0], ST.airC[1], ST.airH);
  const airLane = stadium(airC, R2, F, ST.airL, ST.airRho);
  const ellipse = (deg, t) => {
    const p = airLane(deg / 360);
    return { x: p.x, y: airC.y + 0.8 * Math.sin(t * 0.06), z: p.z };
  };
  const ELLIPSE = new ArcPath((u) => ellipse(u * 360, 0), 120, true);
  const OMEGA = 16 / 20 / ELLIPSE.length * 360;
  const laneTan = (d) => norm(flat(sub(ellipse(d + 1, 0), ellipse(d - 1, 0))));
  const laneJoin = (from, dir) => {
    let best = 0, bs = Infinity;
    for (let d = 0; d < 360; d += 2) {
      const q = ellipse(d, 0), t = laneTan(d), P1 = sub(q, mul(t, 12));
      const to = flat(sub(P1, from)), L_ = Math.hypot(to.x, to.z);
      if (L_ < 10 || L_ > 45) continue;
      const sc = Math.abs(angleDelta(yawOf(dir), yawOf(to))) * 2 + Math.abs(angleDelta(yawOf(to), yawOf(t))) * 2 + Math.abs(L_ - 16) * 0.4;
      if (sc < bs) {
        bs = sc;
        best = d;
      }
    }
    return best;
  };
  const joinLane = (from, dir, speed) => {
    const e = laneJoin(from, dir);
    const q = ellipse(e, airMv.cursor + 30), P1 = sub(q, mul(laneTan(e), 12));
    airMv.path([from, ...steer(from, yawOf(flat(dir)), P1, 10), P1, q], speed);
    airOrbit(e, 4e3);
  };
  const steer = (from, yaw0, target, rad, climb = 0) => {
    let deg = angleDelta(yaw0, yawOf(flat(sub(target, from))));
    if (Math.abs(deg) < 12) return [];
    let pts = arcPts(from, yaw0, deg, rad, climb);
    for (let k2 = 0; k2 < 2; k2++) {
      const end = pts[pts.length - 1], yEnd = yaw0 + deg;
      deg += angleDelta(yEnd, yawOf(flat(sub(target, end))));
      pts = arcPts(from, yaw0, deg, rad, climb);
    }
    return pts;
  };
  const arcPts = (p, yaw0, deg, rad, climb) => {
    const n = Math.max(3, Math.ceil(Math.abs(deg) / 10));
    const dTh = deg / n, ds = rad * Math.abs(dTh) * Math.PI / 180;
    const pts = [];
    let q = { ...p }, y = yaw0;
    for (let i = 0; i < n; i++) {
      y += dTh / 2;
      q = add(q, mul(fromYaw(y), ds));
      y += dTh / 2;
      q = { x: q.x, y: q.y + climb / n, z: q.z };
      pts.push(q);
    }
    return pts;
  };
  const ellDegAt = (p) => {
    let best = 0, bd = Infinity;
    for (let d = 0; d < 360; d += 4) {
      const q = ellipse(d, 0);
      const dd = distXZ(q, p);
      if (dd < bd) {
        bd = dd;
        best = d;
      }
    }
    return best;
  };
  const airStart = sky(58, 12, 25);
  const air = scene.spawn(AIR.actor, airStart, { yaw: yawOf(sub(sky(50, 8, 17), airStart)), state: A3.hidden });
  const airMv = new Mover(air, airStart, air.yaw, T_AIR);
  airMv.maxTurn = 12;
  const airForce = [];
  const force = (from, ticks, s) => {
    airForce.push({ from, to: from + ticks, s });
  };
  let airState = A3.hidden, airDwell = 0;
  function airOrbit(deg0, ticks) {
    const from = airMv.cursor;
    airMv.add(ticks, (_p, t) => ellipse(deg0 + OMEGA * (t - from), t), { tag: "circle" });
  }
  function airBreak(t) {
    airMv.truncate(t);
    return airMv.last;
  }
  const cloudAt = sky(50, 6, 16);
  let clouds = [];
  scene.at(T_AIR - 24, () => {
    clouds = [
      scene.spawn("ed_air_cloud", cloudAt, { yaw: yawOf(F) + 90, size: 1.5, state: CLOUD2.form }),
      scene.spawn("ed_air_cloud", sky(56, -4, 18), { yaw: yawOf(F), size: 1.1, state: CLOUD2.form })
    ];
    sound(dim, "ed_air_cloud", cloudAt, 1.8);
    burst(dim, "ed_air_cloud", cloudAt, 6, 6);
  });
  scene.at(T_AIR - 4, () => {
    clouds.forEach((c) => c.state(CLOUD2.part));
    fadeEmblem(3);
  });
  scene.every(1, (e) => {
    particle(dim, e % 3 ? "ed6_wind" : "ed_air_cloud", add(cloudAt, { x: (hash012(e, 70) - 0.5) * 12, y: (hash012(e, 71) - 0.5) * 4, z: (hash012(e, 72) - 0.5) * 12 }));
  }, T_AIR - 24, T_AIR + 66);
  scene.at(T_AIR + 66, () => clouds.forEach((c) => c.state(CLOUD2.fade)));
  scene.at(T_AIR + 90, () => clouds.forEach((c) => scene.despawn(c)));
  const AR1 = sky(46, 5, 18), AR2 = sky(38.5, 1.5, 16.5);
  airMv.add(A_T.arrive, (p) => bezier3([airStart, sky(55, 10, 23), sky(50, 7.5, 19.5), AR1], smooth(p)));
  force(T_AIR, A_T.arrive, A3.arrive);
  const tRoll = airMv.cursor;
  airMv.add(A_T.roll, (p) => lerp(AR1, AR2, p));
  force(tRoll, A_T.roll, A3.roll);
  const tGlide = airMv.cursor;
  let tStoop = 0, tFlap = 0;
  scene.at(tGlide - 2, () => {
    const G = zoneNow();
    const rel = sub(G, C0);
    const gf = dot(rel, F), gr = dot(rel, R2);
    airMv.truncate(tGlide);
    const s0 = sky(gf + 13, gr - 3, 15.5), s1 = sky(gf + 2.5, gr - 3.5, 3.4);
    airMv.path([AR2, lerp(AR2, s0, 0.5), s0], 16);
    tStoop = airMv.cursor;
    airMv.add(A_T.stoop, (p) => lerp(s0, s1, (16 * p + 12 * p * p) / 28));
    force(tStoop, A_T.stoop, A3.stoop);
    tFlap = airMv.cursor;
    const yS = yawOf(flat(sub(s1, s0)));
    const turn = arcPts(s1, yS, 180, 9.5, 11);
    const w4 = turn[turn.length - 1], w5 = up(add(w4, mul(fromYaw(yS + 180), 8)), 1.5);
    airMv.path([s1, ...turn, w5], 13);
    force(tFlap, airMv.cursor - tFlap, A3.move);
    joinLane(w5, fromYaw(yS + 180), 14);
    scene.at(tStoop, () => {
      sound(dim, "ed_air_dive", s0, 1.8);
      particle(dim, "ed_air_boom", s0);
      particle(dim, "ed6_ring_v", s0);
    });
    scene.at(tFlap, () => {
      const g = ground(s1);
      sound(dim, "ed_air_flare", s1, 1.6);
      particle(dim, "ed_air_shock", up(g, 0.3));
      particle(dim, "ed6_flash_air", up(g, 2));
      burst(dim, "ed_air_gust", up(g, 0.8), 3, 6);
      burst(dim, "ed_air_feather_burst", up(s1, 1), 1.5, 2);
      for (const e of foes(g, ED06.gustRadius)) {
        damage(e, ED06.gustDamage, caster);
        knockback(e, g, ED06.gustKnock, 0.45);
      }
    });
  });
  scene.at(T_AIR, () => {
    air.state(A3.arrive);
    airState = A3.arrive;
    movers.push(airMv);
    sound(dim, "ed_air_call", cloudAt, 2);
    particle(dim, "ed6_flash_air", cloudAt);
  });
  scene.at(T_AIR + 30, () => burst(dim, "ed_air_feather", up(airMv.posAt(scene.tick), 1), 2, 4));
  scene.at(tRoll, () => {
    sound(dim, "ed_air_flap", airMv.posAt(tRoll), 1.5);
    burst(dim, "ed_air_feather", up(airMv.posAt(tRoll), 1), 1.5, 3);
  });
  function airTick(t) {
    const seg = airMv.segAt(t);
    const f = airForce.find((x) => t >= x.from && t < x.to);
    let want;
    if (f) want = f.s;
    else if (seg?.tag === "perch" || !seg) want = A3.idle;
    else if ((seg.tag === "circle" || seg.tag === "helix") && (t - seg.from) % 96 >= 70 && (t - seg.from) % 96 < 86) want = A3.move;
    else {
      const vy = airMv.posAt(t + 1).y - airMv.posAt(t).y;
      const q0 = airMv.posAt(t), q1 = airMv.posAt(t + 1);
      const sp = Math.hypot(q1.x - q0.x, q1.y - q0.y, q1.z - q0.z) * 20;
      want = sp < 4.5 ? A3.flutter : sp < 13 ? A3.move : airMv.yawRate > A_BANK ? A3.turn_r : airMv.yawRate < -A_BANK ? A3.turn_l : vy > 0.1 || sp < 15 ? A3.move : A3.glide;
    }
    if (want !== airState && (f || t >= airDwell)) {
      air.state(want);
      airState = want;
      airDwell = t + 5;
    }
  }
  scene.every(1, () => airTick(scene.tick), T_AIR + 1, T_END3);
  const debris = [];
  const AH = sky(34, -2, 11);
  scene.at(T32 + 130, () => {
    const y0 = yawOf(flat(sub(airMv.posAt(T32 + 131), airMv.posAt(T32 + 130))));
    const p0 = airBreak(T32 + 130);
    airMv.path([p0, ...steer(p0, y0, AH, 10), AH], 14);
    const tP = airMv.cursor;
    airMv.add(A_T.power + 10, (p) => add(AH, mul(F, -1.2 * smooth(p))), { yaw: yawOf(mul(F, -1)) });
    force(tP, A_T.power + 10, A3.power);
    const back = airMv.last;
    joinLane(back, mul(F, -1), 14);
    scene.at(tP, () => {
      air.skin(1);
      sound(dim, "ed_air_call", AH, 1.8);
      ring(dim, "ed_air_spark", AH, 4, 6);
      particle(dim, "ed6_flash_air", AH);
      particle(dim, "ed6_ring_v", AH);
    });
    scene.at(tP + 12, () => {
      const G = zoneNow();
      const spots = [G, at(26, -15), at(25, 13)];
      spots.forEach((g, k2) => scene.after(k2 * 6, () => {
        const d = scene.spawn("ed6_debris", g, { yaw: k2 * 120, size: k2 === 0 ? 1 : 0.85, state: DEBRIS.lift });
        debris.push({ a: d, at: g });
        scene.after(32, () => d.state(DEBRIS.orbit));
        sound(dim, "ed6_debris_lift", g, 1.5, 0.95 + k2 * 0.05);
        burst(dim, "ed_nature_rock", up(g, 0.5), 2, 3);
        particle(dim, "ed6_updraft", up(g, 0.2));
        stream(AH, up(g, 6), 8, ["ed6_wind", "ed_air_streak"], 2, 1);
      }));
    });
    scene.at(tP + 36, () => air.skin(0));
  });
  scene.every(ED06.updraftEvery, () => {
    for (const d of debris) {
      particle(dim, "ed6_updraft", up(d.at, 0.3));
      particle(dim, "ed_air_gust", up(d.at, 1));
      for (const e of foes(d.at, ED06.updraftRadius)) {
        damage(e, ED06.updraftDamage, caster);
        knockback(e, d.at, 0.15, ED06.updraftLift);
      }
    }
  }, T32 + 170, T42 - 10);
  scene.every(1, (e) => {
    debris.forEach((d, i) => {
      if ((e + i) % 2) return;
      const a = (e * 37 + i * 120) * Math.PI / 180, r = 2.5 + e % 3;
      particle(dim, e % 3 ? "ed6_spiral_debris" : "ed6_wind", add(up(d.at, 4 + e % 6), { x: Math.cos(a) * r, y: 0, z: Math.sin(a) * r }));
    });
  }, T32 + 150, T42 + 6);
  scene.every(2, (e) => {
    lobes.forEach((l, i) => {
      if ((e / 2 + i) % 2 === 0) particle(dim, e % 4 ? "ed6_droplet" : "ed_tide_mist", add(l.loc, { x: 0, y: -1 + e % 3, z: 0 }));
    });
    bridges.forEach((b, i) => {
      if ((e / 2 + i) % 3 === 0) particle(dim, e % 6 ? "ed6_snow" : "ed_tide_glint", up(b.loc, 2 + e % 4));
    });
    glasses.forEach((g, i) => {
      if ((e / 2 + i) % 4 === 0) particle(dim, (e + i) % 3 ? "ed6_ember_mote" : "ed6_haze", up(g.at, 0.3));
    });
    stones.forEach((st2, i) => {
      if (!st2.gone && scene.tick < st2.hotUntil && (e / 2 + i) % 2 === 0) particle(dim, "ed6_sizzle", up(st2.at, 3));
    });
  }, T32 - 10, T42 + 40);
  scene.at(T42 + 4, () => {
    debris.forEach((d, i) => scene.after(i * 4, () => {
      d.a.state(DEBRIS.scatter);
      sound(dim, "ed6_debris_fall", d.at, 1.5);
      scene.after(10, () => {
        particle(dim, "ed6_debris_fall", up(d.at, 8));
        particle(dim, "ed6_trail_nature", up(d.at, 0.5));
        for (const e of foes(d.at, ED06.debrisRadius)) {
          damage(e, ED06.debrisDamage, caster);
          knockback(e, d.at, 0.6, 0.3);
        }
      });
      scene.after(22, () => scene.despawn(d.a));
    }));
  });
  scene.at(T32, () => {
    const pts = [
      [nature, nHead(), "ed_nature_call", "nature"],
      [heat, up(heatMv.posAt(scene.tick), 5), "ed_heat_roar", "heat"],
      [tide, up(tideMv.posAt(scene.tick), 4), "ed_tide_roar", "tide"],
      [air, up(airMv.posAt(scene.tick), 1), "ed_air_call", "air"]
    ];
    pts.forEach(([a, p, snd, n], k2) => {
      if (!a.valid) return;
      scene.after(k2 * 3, () => {
        sound(dim, snd, p, 1.8);
        particle(dim, `ed6_flash_${n}`, p);
        particle(dim, "ed6_ring_v", p);
        burst(dim, `ed6_burst_${n}`, p, 2, 4);
      });
    });
    sound(dim, "ed6_heart_all", cxCore(), 1.6);
    codexBeat();
    particle(dim, "ed6_wave", up(at(24, 0), 0.3));
    particle(dim, "ed6_ring_v", cxCore());
    for (let k2 = 0; k2 < 4; k2++) stream(cxCore(), pts[k2][1], 10, ["ed6_stream", "ed6_codex_rune"], 4, 2);
  });
  const DOMAIN_R = 4;
  const leyEnd = (k2, t) => {
    const a = [nature, heat, tide, air][k2];
    const arrived = t >= [T_NATURE + 10, T_HEAT + 4, T_TIDE + 4, T_AIR + 30][k2];
    if (!arrived) return emblems[k2]?.valid ? EM[k2].at : void 0;
    if (!a.valid) return void 0;
    const p = [natMv, heatMv, tideMv, airMv][k2].posAt(t);
    return ground(p);
  };
  scene.every(1, (t) => {
    if (t >= T52) return;
    for (let k2 = 0; k2 < 4; k2++) {
      const end = leyEnd(k2, t);
      if (!end) continue;
      const concord = t >= T42 + 10;
      const from = concord ? end : add(C0, mul(norm(flat(sub(end, C0))), DOMAIN_R));
      const to = concord ? zone().G : end;
      const u = (t * 1.5 + k2 * 9) % 30 / 30;
      const p = lerp(from, to, concord ? u : u * u);
      particle(dim, `ed6_ley_${LINEAGE[k2]}`, up(ground(p), 0.25));
    }
  }, BEATS[0] + 8, T52);
  scene.every(1, (t) => {
    if (nature.valid && t >= T_NATURE + 20 && t < T52 + 96) {
      const p = natMv.posAt(t), y = natMv.lastYaw;
      const st2 = N_STEPS[t % 4];
      particle(dim, nWalking || t % 2 ? "ed6_trail_nature" : "ed_nature_mote", up(ground(local3(p, y, st2.x * 1.1, st2.z)), 0.3));
      particle(dim, t % 3 ? "ed6_leaf_fall" : "ed_nature_leaf", up(local3(p, y, (hash012(t, 60) - 0.5) * 5, (hash012(t, 61) - 0.5) * 16), 9 + hash012(t, 62) * 3));
      particle(dim, t % 2 ? "ed_nature_pollen" : "ed6_mote", up(local3(p, y, (hash012(t, 65) - 0.5) * 6, (hash012(t, 63) - 0.4) * 14), 10 + hash012(t, 66) * 3));
    }
    if (heat.valid && t >= T_HEAT + 4 && t < T52 + 96) {
      const p = heatMv.posAt(t), y = heatMv.lastYaw;
      const pts = [local3(up(p, 5.4), y, 0, H_HORN - 1.5), up(p, 5), local3(up(p, 4), y, 0, -5)];
      particle(dim, "ed6_trail_heat", pts[t % 3]);
      particle(dim, "ed6_trail_heat", local3(up(p, 3 + t % 3), y, (hash012(t, 67) - 0.5) * 2.5, (hash012(t, 68) - 0.4) * 12));
      particle(dim, t % 2 ? "ed6_haze" : "ed6_ember_mote", up(p, 1 + t % 4));
      particle(dim, "ed6_ember_mote", local3(up(p, 1 + t % 5), y, (hash012(t, 75) - 0.5) * 4, (hash012(t, 76) - 0.5) * 14));
      if (t % 6 === 0) particle(dim, "ed_heat_horn", local3(up(p, 5.6), y, 0, H_HORN - 1));
    }
    if (tide.valid && t >= T_TIDE && t < T52 + 70) {
      const p = tideMv.posAt(t), y = tideMv.lastYaw;
      const pts = [local3(up(p, 3), y, 0, 9), up(p, 6.5), local3(up(p, 2.5), y, 0, -12)];
      particle(dim, "ed6_trail_tide", pts[t % 3]);
      particle(dim, "ed6_droplet", local3(up(p, 3), y, 0, (hash012(t, 64) - 0.5) * 20));
      particle(dim, t % 3 ? "ed6_trail_tide" : "ed6_snow", local3(up(p, 5 + t % 4), y, 0, (hash012(t, 69) - 0.5) * 8));
      particle(dim, t % 2 ? "ed6_droplet" : "ed_tide_bubble", local3(up(p, 1 + t % 3), y, (hash012(t, 77) - 0.5) * 3, (hash012(t, 78) - 0.5) * 22));
    }
    if (air.valid && t > T_AIR + 2 && airState !== A3.idle && airState !== A3.rest && airState !== A3.depart) {
      const p = airMv.posAt(t), y = airMv.lastYaw;
      particle(dim, "ed6_trail_air", local3(up(p, 0.9), y, 8, -1));
      particle(dim, "ed6_trail_air", local3(up(p, 0.9), y, -8, -1));
      particle(dim, t % 9 === 0 ? "ed_air_feather" : t % 2 ? "ed6_wind" : "ed6_trail_air", local3(up(p, 1), y, 0, -4 - t % 5));
    }
  }, T_NATURE, T_END3);
  function heatToFinal() {
    const z = zone();
    const from = heatMv.last;
    const mid = ground(lerp(from, z.SF, 0.5));
    const side = norm(flat(sub(z.SF, from)));
    const pts = [from, add(mid, mul(right(side), 1)), z.SF];
    const t0 = heatMv.cursor;
    planYaw = yawOf(side);
    heatMv.path(pts, H_RUN, { tag: "run" });
    scene.at(t0, () => heat.state(H.move));
    const tStop = heatMv.cursor;
    heatMv.hold(H_T.skid, yawOf(sub(pts[2], pts[1])), "skidstop");
    scene.at(tStop, () => {
      heat.state(H.skid);
      particle(dim, "ed_heat_skid", up(z.SF, 0.3));
    });
    planYaw = yawOf(sub(pts[2], pts[1]));
    const P6 = right(z.L);
    const pa = ground(add(z.SF, mul(P6, 3.5))), pb = ground(sub(z.SF, mul(P6, 3.5)));
    for (const [a, b] of [[z.SF, pa], [pa, pb], [pb, z.SF]]) {
      hTurn(yawOf(sub(b, a)));
      const ts = heatMv.cursor;
      heatMv.walk(a, b, H_WALK, { tag: "pace" });
      scene.at(ts, () => {
        heat.state(H.walk);
        sound(dim, "ed_heat_snort", up(a, 3), 1.2);
      });
      if (heatMv.cursor > T42 + 190) break;
    }
    hTurn(z.yawL);
    const tWait = heatMv.cursor;
    scene.at(tWait, () => heat.state(H.pant));
    heatMv.hold(Math.max(1, T42 + 238 - heatMv.cursor), z.yawL);
  }
  let tele;
  let ringA;
  const ringCells = [];
  scene.at(T42, () => {
    const z = zone();
    tele = scene.spawn("telegraph", up(z.G, 0.05), { kind: 2, size: ED06.ringRadius + 1, state: 4 });
    sound(dim, "ed6_concord", z.G, 2);
    sound(dim, "ed6_heart_all", cxCore(), 1.6);
    codexBeat();
    particle(dim, "ed6_concord", up(z.G, 3));
    particle(dim, "ed6_column", up(z.G, 0.3));
    particle(dim, "ed6_wave", up(z.G, 0.3));
    burst(dim, "ed6_rune_rise", up(z.G, 0.5), 4, 6);
    particle(dim, "ed6_ring_v", cxCore());
    stream(cxCore(), up(z.G, 2), 12, ["ed6_stream", "ed6_codex_rune"], 5, 3);
    light(up(z.G, 2), T52 + 20 - T42);
  });
  scene.at(T42 + 40, () => tele?.state(2));
  scene.every(1, (e) => {
    const z = zone();
    if (e < 12) return;
    const a = e * 53, r = ED06.ringRadius + 0.3;
    if (e < 150) particle(dim, e % 2 ? "ed6_trail_nature" : "ed_nature_rock", up(W2.polar(r, a, 0, z.G), 1 + e % 4 * 1.5));
    else if (e < 216) particle(dim, e % 2 ? "ed6_snow" : "ed_tide_mist", up(W2.polar(r * (0.4 + e % 3 * 0.25), a, 0, z.G), 0.5 + e % 4));
  }, T42, T42 + 300);
  scene.every(1, (e) => {
    const z = zone();
    const step = e < 90 ? "ed_nature_mote" : e < 200 ? "ed6_trail_tide" : e < 236 ? "ed6_wind" : "ed6_trail_heat";
    for (let j = 0; j < 2; j++) {
      const a = e * 9 + j * 180;
      particle(dim, j ? step : "ed6_stream", up(W2.polar(ED06.ringRadius + 0.8, a, 0, z.G), 0.5 + 0.5 * Math.sin(e * 0.2 + j)));
    }
  }, T42 + 4, T42 + 300);
  const yN = nYaw0, N_TURN_DEG = 30, nTurnT = Math.round(N_TURN_DEG / (N_TURN / 1.5) * 20);
  natMv.hold(nTurnT, void 0);
  natMv.segs[natMv.segs.length - 1].yaw = (t) => yN + N_TURN_DEG * smooth((t - T42) / nTurnT);
  nHold(T52 - natMv.cursor, yN + N_TURN_DEG);
  scene.at(T42, () => {
    nature.state(N2.turn_r);
    sound(dim, "ed_nature_bellow", nHead(), 2);
  });
  scene.at(T42 + nTurnT, () => nature.state(N2.idle));
  scene.at(T42 + 12, () => {
    const z = zone();
    ringA = scene.spawn("ed6_ring", z.G, { yaw: z.ringYaw, size: ED06.ringRadius / RING_R, state: RING.rise });
    sound(dim, "ed6_ring_rise", z.G, 2);
    ring(dim, "ed_nature_rise", z.G, ED06.ringRadius, 8);
    ring(dim, "ed6_trail_nature", up(z.G, 0.6), ED06.ringRadius, 8, 22);
    particle(dim, "ed6_geo_shock", up(z.G, 0.2));
    for (const e of foes(z.G, ED06.ringRadius + 1.5)) {
      const d = distXZ(e.location, z.G);
      if (Math.abs(d - ED06.ringRadius) < 1.6) shove(e, sub(z.G, e.location), 0.9, 0.35);
    }
  });
  scene.at(T42 + 36, () => {
    const z = zone();
    const seen = /* @__PURE__ */ new Set();
    const n = Math.ceil(2 * Math.PI * ED06.ringRadius);
    const doorA = yawToFrame(z.yawL), doorB = doorA + 180;
    for (let i = 0; i < n; i++) {
      const a = i * 360 / n;
      if (Math.abs(angleDelta(a, doorA)) < ED06.doorwayDeg || Math.abs(angleDelta(a, doorB)) < ED06.doorwayDeg) continue;
      const p = W2.polar(ED06.ringRadius, a, 0, z.G);
      const c = { x: Math.floor(p.x), y: Math.floor(gy(p)), z: Math.floor(p.z) };
      const key = `${c.x},${c.z}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (tb.column(c.x, c.y, c.z, ED06.ringBarrierHeight) > 0) ringCells.push(c);
    }
  });
  scene.at(T42 + 44, () => ringA?.state(RING.hold));
  const tSlam = T42 + 20;
  scene.at(tSlam, () => {
    nature.state(N2.attack_a);
    sound(dim, "ed_nature_rumble", natMv.posAt(tSlam), 1.8, 1.1);
  });
  scene.at(tSlam + N_T.attackAHit, () => {
    const z = zone();
    const p = ground(natMv.posAt(scene.tick)), y = yN + N_TURN_DEG;
    const SL = ground(local3(p, y, N_SLAM.x, N_SLAM.z));
    const q = scene.spawn("ed_nature_quake", up(SL, 0.03), { size: 3.4, state: 1 });
    scene.after(27, () => scene.despawn(q));
    sound(dim, "ed_nature_slam", SL, 2.4);
    particle(dim, "ed_nature_shock_big", up(SL, 0.2));
    particle(dim, "ed6_wave", up(SL, 0.3));
    particle(dim, "ed6_flash_nature", up(SL, 2));
    burst(dim, "ed6_trail_nature", up(SL, 1), 4, 5);
    for (const e of foes(SL, ED06.slamRadius)) {
      damage(e, ED06.slamDamage, caster);
      knockback(e, SL, 1.2, 0.5);
    }
    const D_ = distXZ(SL, z.G);
    const steps = Math.max(2, Math.floor((D_ - ED06.ringRadius) / 3));
    const hit = /* @__PURE__ */ new Set();
    for (let i = 1; i <= steps; i++) {
      scene.after(i * 2, () => {
        const pt = ground(lerp(SL, z.G, i * 3 / D_));
        if (i % 2 === 1) {
          const qq = scene.spawn("ed_nature_quake", up(pt, 0.02), { size: 1.5, state: 1, yaw: i * 61 });
          scene.after(27, () => scene.despawn(qq));
        }
        particle(dim, "ed6_geo_shock", up(pt, 0.2));
        particle(dim, "ed6_trail_nature", up(pt, 0.6));
        particle(dim, "ed_nature_rock", up(pt, 0.4));
        if (i % 2) sound(dim, "ed_nature_quake", pt, 1.3, 0.9 + i * 0.04);
        for (const e of foes(pt, ED06.quakeRadius)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, ED06.quakeDamage, caster);
          knockback(e, pt, 0.4, 0.45);
        }
      });
    }
    ED06.shockPulseDamage.forEach((dmg, k2) => scene.after(steps * 2 + 3 + k2 * 10, () => {
      ringA?.state(RING.quake);
      scene.after(10, () => ringA?.state(RING.hold));
      sound(dim, "ed6_geo_shock", z.G, 2, 0.9 + k2 * 0.1);
      particle(dim, "ed6_geo_shock", up(z.G, 0.25));
      particle(dim, "ed_nature_shock_big", up(z.G, 0.3));
      ring(dim, "ed_nature_rock", up(z.G, 0.5), ED06.ringRadius * 0.8, 6, k2 * 20);
      ring(dim, "ed6_trail_nature", up(z.G, 0.4), ED06.ringRadius * 0.9, 6, k2 * 20 + 30);
      for (const e of foes(z.G, ED06.ringRadius + 0.5)) {
        damage(e, dmg, caster);
        effect(e, "slowness", ED06.shockSlowTicks, 1);
        knockback(e, e.location, 0, 0.45);
      }
    }));
  });
  scene.at(tSlam + N_T.attackA, () => nature.state(N2.idle));
  scene.at(T42 - 70, () => {
    const z = zone();
    const sNow = tideS(T42 - 70), lap = loop.length;
    let sLand = Math.floor(sNow / lap) * lap + S_TL_LEN;
    while (sLand < sNow + 14) sLand += lap;
    const tb2 = tSwim2 + Math.round((sLand - 6) / (D_SWIM / 20));
    tideMv.truncate(tb2);
    const s0 = sLand - 6;
    const tLand2 = tideMv.cursor;
    tideMv.add(D_T.land, (p) => {
      const q = loop.at(s0 + 6 * easeOut(p));
      return { x: q.x, y: lerp(q, z.TL, smooth(p)).y, z: q.z };
    });
    tideMv.hold(T52 + 40 - tideMv.cursor, z.tideYaw);
    scene.at(tLand2, () => {
      tide.state(D3.land);
      sound(dim, "ed_tide_land", z.TL, 1.6);
    });
    scene.at(tLand2 + D_T.landHit, () => {
      ring(dim, "ed_tide_splash", up(z.TL, 0.3), 3, 6);
      particle(dim, "ed_tide_frost_ring", up(z.TL, 0.2));
      particle(dim, "ed6_flash_tide", up(z.TL, 3));
      for (const e of foes(z.TL, 4)) {
        damage(e, ED06.currentDamage, caster);
        knockback(e, z.TL, 0.8, 0.3);
      }
    });
    scene.at(tLand2 + D_T.land, () => tide.state(D3.idle));
  });
  const currents = [];
  const frozen = /* @__PURE__ */ new Map();
  let shell;
  const tSweep2 = T42 + 104;
  scene.at(tSweep2, () => {
    tide.state(D3.attack_a);
    sound(dim, "ed_tide_sweep", zone().TL, 1.6);
  });
  D_T.sweepHit.forEach((hh, w) => scene.at(tSweep2 + hh, () => {
    const z = zone();
    const tail = up(local3(z.TL, z.tideYaw, 0, -9), 2);
    let dir = norm(flat(sub(tail, z.G)));
    if (w === 1) dir = mul(dir, -1);
    sound(dim, "ed_tide_flow", tail, 1.5, 0.95 + w * 0.08);
    particle(dim, "ed6_flash_tide", up(tail, 2));
    for (let k2 = 0; k2 < 2; k2++) {
      const R_ = ED06.ringRadius * (k2 === 0 ? 0.78 : 0.5);
      const side = k2 === 0 ? right(dir) : mul(right(dir), -1);
      const a = scene.spawn("ed_tide_current", z.G, { kind: k2, size: R_ / CUR_R2, state: CUR2.form, yaw: yawOf(dir) });
      currents.push({ a, R: R_, dir, side, born: scene.tick, touched: /* @__PURE__ */ new Set() });
      stream(up(tail, 1), up(add(z.G, mul(dir, R_)), 1), 8, ["ed6_trail_tide", "ed_tide_spray"], 2, 2);
      scene.after(16, () => a.state(CUR2.flow));
    }
  }));
  scene.every(4, () => {
    const z = zone();
    for (const e of foes(z.G, ED06.ringRadius + 1)) {
      if (frozen.has(e.id)) continue;
      for (const c of currents) {
        const v2 = flat(sub(e.location, z.G));
        const r = Math.hypot(v2.x, v2.z);
        const deg = Math.atan2(dot(v2, c.side), dot(v2, c.dir)) * 180 / Math.PI;
        if (Math.abs(r - c.R) > 1.4 || deg < -12 || deg > Math.min(CUR_SWEEP2, (scene.tick - c.born) * 17)) continue;
        const a = deg * Math.PI / 180;
        const tangent = add(mul(c.dir, -Math.sin(a)), mul(c.side, Math.cos(a)));
        shove(e, add(tangent, mul(norm(flat(sub(z.G, e.location))), (r - c.R) * 0.25)), ED06.concordCurrentShove, 0.06);
        if (!c.touched.has(e.id)) {
          c.touched.add(e.id);
          damage(e, ED06.concordCurrentDamage, caster);
          particle(dim, "ed_tide_spray", e.location);
        }
        break;
      }
    }
  }, tSweep2 + 10, T42 + 160);
  scene.every(2, (e) => {
    const z = zone();
    if (!currents.length) return;
    particle(dim, "ed6_trail_tide", up(W2.polar(ED06.ringRadius * 0.7, e * 23, 0, z.G), 0.6));
  }, tSweep2 + 12, T42 + 166);
  const tFlare2 = T42 + 142;
  scene.at(tFlare2, () => tide.state(D3.attack_c));
  scene.at(tFlare2 + D_T.flareHit, () => {
    const z = zone();
    const sail = up(z.TL, 9);
    sound(dim, "ed_tide_freeze", z.G, 1.8);
    tide.prop("frost", 1);
    burst(dim, "ed_tide_glint", sail, 2, 5);
    particle(dim, "ed6_flash_tide", sail);
    for (const c of currents) {
      line(dim, "ed_tide_frostline", sail, up(add(z.G, mul(c.dir, c.R)), 1), 6);
      c.a.state(CUR2.freeze);
    }
    shell = scene.spawn("ed6_iceshell", up(z.G, 0.04), { size: ED06.ringRadius / RING_R, state: SHELL.grow, yaw: z.ringYaw });
    sound(dim, "ed6_ice_layers", z.G, 1.8);
    ringA?.skin(RING_SKIN.frost);
    SHELL_LAYERS.forEach((ly, i) => scene.after(ly.t, () => {
      particle(dim, "ed6_frost_layer", up(z.G, 0.3 + i * 0.4));
      ring(dim, "ed6_snow", up(z.G, 1.5 + i), ly.r * (ED06.ringRadius / RING_R), 6, i * 25);
      ring(dim, "ed_tide_glint", up(z.G, 2 + i), ly.r * (ED06.ringRadius / RING_R), 4, i * 25 + 40);
      for (const e of foes(z.G, ly.r * (ED06.ringRadius / RING_R) + 0.8)) {
        if (frozen.has(e.id)) continue;
        damage(e, ED06.iceLayerDamage, caster);
        if (!isAlive(e)) continue;
        frozen.set(e.id, restrain(scene, e, Math.max(10, T42 + 222 - scene.tick), { ...e.location }));
        particle(dim, "ed_tide_splinter", up(e.location, 0.8));
      }
    }));
  });
  scene.at(tFlare2 + D_T.flare, () => tide.state(D3.idle));
  scene.at(T42 + 186, () => {
    shell?.state(SHELL.hold);
    currents.forEach((c) => c.a.state(CUR2.ice));
  });
  let spiral;
  scene.at(T42 + 120, () => {
    const z = zone();
    const HC = add(z.G, mul(F, 6));
    const hs = up(add(HC, mul(F, -3)), 9);
    let tb2 = T42 + 168, best = Infinity;
    for (let t = T42 + 124; t <= T42 + 200; t += 2) {
      const p = airMv.posAt(t), q = airMv.posAt(t + 1);
      const to = sub(hs, p), d = Math.hypot(to.x, to.z);
      if (d < 12) continue;
      const off = Math.abs(angleDelta(yawOf(flat(sub(q, p))), yawOf(to)));
      const score = off + Math.abs(t - (T42 + 168)) * 0.25;
      if (score < best) {
        best = score;
        tb2 = t;
      }
    }
    const y0 = yawOf(flat(sub(airMv.posAt(tb2 + 1), airMv.posAt(tb2))));
    const p0 = airBreak(tb2);
    airMv.path([p0, ...steer(p0, y0, hs, 10), hs], 16);
    const tPw = airMv.cursor;
    airMv.add(A_T.power + 66, (p) => add(hs, mul(R2, -1.5 * smooth(p))), { yaw: yawOf(mul(R2, -1)) });
    force(tPw, A_T.power + 66, A3.power);
    scene.at(tPw, () => {
      air.skin(1);
      sound(dim, "ed_air_call", hs, 2);
      ring(dim, "ed_air_spark", hs, 3, 6);
      particle(dim, "ed6_flash_air", hs);
      burst(dim, "ed_air_feather", hs, 2, 4);
    });
    const tHx = tPw + A_T.power;
    const back = airMv.last;
    joinLane(back, mul(R2, -1), 14);
    scene.at(tHx, () => sound(dim, "ed_air_vortex", z.G, 1.8));
  });
  scene.at(T42 + 206, () => {
    const z = zone();
    spiral = scene.spawn("ed6_spiral", up(z.G, 0.05), { size: ED06.ringRadius / RING_R, state: SPIRAL.form });
    sound(dim, "ed6_spiral", z.G, 2);
    scene.after(20, () => spiral?.state(SPIRAL.spin));
  });
  scene.at(T42 + 216, () => {
    const z = zone();
    shell?.state(SHELL.shatter);
    currents.forEach((c) => c.a.state(CUR2.shatter));
    for (const rel of frozen.values()) rel();
    frozen.clear();
    sound(dim, "ed_tide_fracture", z.G, 1.8);
    burst(dim, "ed_tide_splinter", up(z.G, 2), 3, 6);
    burst(dim, "ed6_spiral_debris", up(z.G, 3), 2.5, 4);
    particle(dim, "ed6_flash_tide", up(z.G, 2));
  });
  scene.at(T42 + 230, () => {
    if (shell) scene.despawn(shell);
    currents.forEach((c) => scene.despawn(c.a));
    currents.length = 0;
  });
  const spun = /* @__PURE__ */ new Map();
  scene.every(ED06.spiralEvery, (el) => {
    const z = zone();
    for (const e of foes(z.G, ED06.ringRadius + 0.5)) {
      const n = spun.get(e.id) ?? 0;
      if (n >= 8) continue;
      spun.set(e.id, n + 1);
      damage(e, ED06.spiralDamage, caster);
      const v2 = flat(sub(e.location, z.G));
      const tan = norm({ x: -v2.z, y: 0, z: v2.x });
      shove(e, add(tan, mul(norm(mul(v2, -1)), 0.3)), ED06.spiralShove, ED06.spiralLift);
    }
    void el;
  }, T42 + 218, T42 + 276);
  scene.every(1, (e) => {
    const z = zone();
    const a = e * 31, h = 1 + e % 9 * 1.2;
    particle(
      dim,
      e % 3 === 0 ? "ed6_spiral_debris" : e % 3 === 1 ? "ed6_wind" : "ed6_snow",
      up(W2.polar(ED06.ringRadius * (0.5 + 0.08 * (e % 5)), a, 0, z.G), h)
    );
  }, T42 + 210, T42 + 290);
  scene.at(T42 + 276, () => {
    const z = zone();
    for (const e of foes(z.G, ED06.ringRadius + 0.5)) knockback(e, e.location, 0, ED06.spiralFinalLift);
    particle(dim, "ed6_updraft", up(z.G, 0.3));
  });
  scene.at(T42 + 300, () => air.skin(0));
  scene.at(T42 + 204, () => {
    const z = zone();
    if (distXZ(heatMv.posAt(T42 + 204), z.SF) > 4) return;
    const lane = scene.spawn("ed_heat_lane", ground(add(z.SF, mul(z.L, 3.5))), { yaw: z.yawL, state: LANE2.appear });
    lane.prop("len", clamp(ED06.finalRunUp + 4, 4, 40));
    sound(dim, "ed_heat_lane", z.SF, 1.5, 0.85);
    scene.after(16, () => lane.state(LANE2.armed));
    scene.at(T42 + 232, () => {
      lane.state(LANE2.surge).skin(1);
      for (const s of stones) {
        if (s.gone || distToSegment(s.at, z.SF, z.G) > 4) continue;
        s.a.skin(STONE_SKIN.glass).state(STONE.flare);
        s.hotUntil = T42 + 400;
        particle(dim, "ed6_sizzle", up(s.at, 2));
      }
    });
    scene.at(T42 + 292, () => lane.state(LANE2.fade));
    scene.at(T42 + 304, () => scene.despawn(lane));
  });
  scene.at(T42 + 206, () => sound(dim, "ed6_swell", zone().G, 2));
  scene.every(2, (e) => {
    const z = zone();
    const u = e * 0.07 % 1;
    particle(dim, e % 4 === 0 ? "ed6_haze" : "ed6_trail_heat", up(lerp(z.SF, z.G, u), 0.4 + e % 3 * 0.6));
  }, T42 + 210, T42 + 238);
  scene.at(T42 + 210, () => {
    heat.state(H.roar);
    sound(dim, "ed6_final_charge", up(zone().SF, 4), 2);
  });
  scene.at(T42 + 226, () => {
    const z = zone();
    heat.skin(H_SKIN.whitehot);
    particle(dim, "ed6_flash_heat", up(z.SF, 4));
    ring(dim, "ed_heat_vent", up(z.SF, 3.5), 3, 8);
    particle(dim, "ed_heat_ring", up(z.SF, 0.3));
    codexBeat();
  });
  scene.at(T42 + 238, () => {
    const z = zone();
    heatMv.truncate(T42 + 238);
    heatMv.last = { ...heatMv.posAt(T42 + 237) };
    planYaw = z.yawL;
    const end = hCharge(add(z.G, mul(z.L, 1 + H_RUN / 20 * (H_T.skid - 1) / 2)), { final: true });
    scene.at(end, () => heat.state(H.pant));
    heatMv.hold(16, z.yawL);
    const E = { ...heatMv.last }, E2 = ground(add(add(z.G, mul(F, 9)), mul(R2, 3)));
    const toE2 = yawOf(sub(E2, E));
    hTurn(toE2);
    const tw = heatMv.cursor;
    heatMv.walk(E, E2, H_WALK, { tag: "walkback" });
    scene.at(tw, () => {
      heat.state(H.walk);
      sound(dim, "ed_heat_snort", up(E, 3), 1.4);
    });
    hTurn(yawOf(mul(R2, -1)));
    scene.at(heatMv.cursor, () => heat.state(H.pant));
    heatMv.hold(Math.max(1, T52 + 300 - heatMv.cursor), yawOf(mul(R2, -1)));
  });
  function detonate() {
    detonated = true;
    const z = zone();
    const G = z.G;
    spiral?.state(SPIRAL.burst);
    tele?.state(3);
    ringA?.skin(RING_SKIN.glass);
    for (const c of ringCells) tb.removeColumn(c.x, c.y, c.z, ED06.ringBarrierHeight);
    ringCells.length = 0;
    const bl = scene.spawn("ed6_blast", up(G, 0.05), { size: (ED06.ringRadius + ED06.detonationExtra) / 6, state: BLAST.blast });
    sound(dim, "ed6_detonation", G, 3);
    sound(dim, "ed_heat_roar", up(G, 3), 2, 0.8);
    particle(dim, "ed6_thermal_ring", up(G, 0.3));
    particle(dim, "ed6_wave", up(G, 0.4));
    particle(dim, "fx_flash", up(G, 2));
    particle(dim, "ed6_flash_heat", up(G, 3));
    particle(dim, "ed6_ring_v", up(G, 3));
    particle(dim, "ed6_column", up(G, 0.5));
    burst(dim, "ed6_thermal", up(G, 2), 3, 8);
    burst(dim, "ed6_glass_shard", up(G, 2), 4, 5);
    burst(dim, "ed6_burst_heat", up(G, 3), 3, 5);
    ring(dim, "ed6_trail_heat", up(G, 0.6), ED06.ringRadius, 8);
    ring(dim, "ed6_sizzle", up(G, 0.4), ED06.ringRadius * 0.7, 5, 20);
    for (let k2 = 0; k2 < 4; k2++) particle(dim, `ed6_flash_${LINEAGE[k2]}`, up(W2.polar(ED06.ringRadius, k2 * 90 + 45, 0, G), 3));
    for (const e of foes(G, ED06.ringRadius + ED06.detonationExtra)) {
      damage(e, ED06.detonationDamage, caster);
      knockback(e, G, ED06.detonationKnockH, ED06.detonationKnockV);
      burnT(e, ED06.detonationBurnSeconds);
    }
    scene.after(4, () => {
      ringA?.state(RING.burst);
      sound(dim, "ed_nature_erupt", G, 2, 0.8);
      burst(dim, "ed6_trail_nature", up(G, 2), 6, 6);
    });
    scene.after(6, () => {
      particle(dim, "ed6_thermal_ring", up(G, 0.5));
      burst(dim, "ed6_thermal", up(G, 3), 4, 6);
    });
    for (let i = 0; i < 6; i++) scene.after(8 + i * 5, () => burst(dim, "ed6_smoke", up(G, 2 + i), 3 + i * 0.6, 3));
    scene.after(26, () => bl.state(BLAST.hold).skin(1));
    scene.after(50, () => bl.state(BLAST.fade));
    scene.after(72, () => {
      scene.despawn(bl);
      if (ringA) scene.despawn(ringA);
      if (spiral) scene.despawn(spiral);
      if (tele) scene.despawn(tele);
    });
  }
  scene.at(T42 + 292, () => {
    if (!detonated && Z) detonate();
  });
  const spirits = [];
  function remember(k2, at_, size, tForm, tStream) {
    scene.at(tForm, () => {
      const { p, yaw } = at_();
      const s = scene.spawn("ed6_spirit", p, { kind: k2, yaw, size, state: SPIRIT.form });
      spirits[k2] = s;
      sound(dim, "ed6_inscribe", up(p, 4), 1.6, 0.9 + k2 * 0.06);
      burst(dim, "ed6_bone_dust", up(p, 3), 3.5, 6);
      particle(dim, `ed6_flash_${LINEAGE[k2]}`, up(p, 3));
      scene.after(24, () => s.state(SPIRIT.hold));
    });
    scene.at(tStream, () => {
      const s = spirits[k2];
      if (!s?.valid) return;
      const from = { ...s.loc }, yaw = s.yaw;
      s.state(SPIRIT.stream);
      sound(dim, "ed6_stream", up(from, 3), 1.5);
      const ctl = up(lerp(from, K3, 0.5), 9);
      scene.span(scene.tick + 1, scene.tick + 28, (p, e) => {
        const q = bezier(from, ctl, K3, smooth(p));
        s.move(q, yaw + 200 * smooth(p));
        if (e % 2 === 0) particle(dim, "ed6_stream", up(q, 2));
        if (e % 3 === 0) particle(dim, "ed6_inscribe", up(q, 3));
      });
      scene.after(28, () => {
        codex.state(CODEX2.absorb);
        sound(dim, "ed6_absorb", K3, 1.6, 0.9 + k2 * 0.08);
        burst(dim, "ed6_codex_glint", up(K3, 2), 2.5, 5);
        particle(dim, `ed6_flash_${LINEAGE[k2]}`, up(K3, CODEX_CORE));
        particle(dim, "ed6_ring_v", up(K3, CODEX_CORE));
        scene.despawn(s);
      });
    });
  }
  scene.every(1, (e) => {
    for (let k2 = 0; k2 < 4; k2++) {
      const sp = spirits[k2];
      if (!sp?.valid || (e + k2) % 2) continue;
      const len_ = [30, 14, 22, 12][k2];
      particle(
        dim,
        (e >> 1) % 2 ? "ed6_bone_dust" : "ed6_inscribe",
        local3(up(sp.loc, 2 + hash012(e, 90 + k2) * 5), sp.yaw, (hash012(e, 94 + k2) - 0.5) * 3, (hash012(e, 98 + k2) - 0.5) * len_)
      );
    }
  }, T52 + 40, T_SEAL);
  scene.at(T52 + 2, () => {
    particle(dim, "ed6_ring_v", cxCore());
    particle(dim, "ed6_light_wave", up(zone().G, 0.3));
    burst(dim, "ed6_codex_glint", cxCore(), 3, 6);
    codexBeat();
  });
  scene.at(T52, () => {
    sound(dim, "ed6_hush", up(at(16, 0), 2), 2);
    cxMv.truncate(T52);
    cxFlip = true;
    cxMv.pathIn([cxMv.last, sky(32, -10, 10.5), K3], 40, { ease: smooth, yaw: cxYaw });
    cxMv.add(T_END3 - cxMv.cursor, drift(K3, 0.25), { yaw: cxYaw });
    codex.prop("open", 1);
    sound(dim, "ed6_codex_open", K3, 1.6);
  });
  scene.at(T52 + 40, () => codex.state(CODEX2.absorb));
  const PL = at(30, 22);
  scene.at(T52 + 12, () => {
    let tb2 = T52 + 30, best = Infinity;
    for (let t = T52 + 16; t <= T52 + 70; t += 2) {
      const p = airMv.posAt(t), q = airMv.posAt(t + 1);
      const to = flat(sub(PL, p)), d = Math.hypot(to.x, to.z);
      if (d < 14 || d > 32) continue;
      const sc = Math.abs(angleDelta(yawOf(flat(sub(q, p))), yawOf(to))) * 2 + Math.abs(d - 20) * 0.5 + Math.abs(t - (T52 + 30)) * 0.1;
      if (sc < best) {
        best = sc;
        tb2 = t;
      }
    }
    const y0 = yawOf(flat(sub(airMv.posAt(tb2 + 1), airMv.posAt(tb2))));
    const p0 = airBreak(tb2);
    const arcIn = steer(p0, y0, PL, 10);
    const from = arcIn.length ? arcIn[arcIn.length - 1] : p0;
    const dirL = norm(flat(sub(PL, from)));
    const app = up(add(PL, mul(dirL, -9)), 3.5);
    airMv.path([p0, ...arcIn, app], 14);
    const tF = airMv.cursor;
    airMv.add(A_T.flare, (p) => lerp(app, up(add(PL, mul(dirL, -1.5)), 1.4), easeOut(p)), { yaw: yawOf(dirL) });
    force(tF, A_T.flare, A3.flare);
    const tL = airMv.cursor;
    airMv.add(A_T.land, (p) => lerp(up(add(PL, mul(dirL, -1.5)), 1.4), PL, smooth(p)), { yaw: yawOf(dirL) });
    force(tL, A_T.land, A3.land);
    airMv.add(400, () => PL, { yaw: yawOf(dirL), tag: "perch" });
    scene.at(tF, () => sound(dim, "ed_air_flare", app, 1.6));
    scene.at(tL + A_T.land - 2, () => {
      particle(dim, "fx_dust", PL);
      particle(dim, "ed_air_shock", up(PL, 0.2));
      sound(dim, "ed_air_land", PL, 1.3);
    });
    scene.at(tL + A_T.land + 8, () => {
      force(scene.tick, 400, A3.rest);
    });
    const tD = Math.max(tL + A_T.land + 20, T52 + 56);
    scene.at(tD, () => {
      force(scene.tick, 400, A3.depart);
      sound(dim, "ed_air_depart", up(PL, 2), 1.6);
      burst(dim, "ed_air_feather_burst", up(PL, 1.5), 2, 3);
    });
    scene.at(tD + A_T.depart, () => scene.despawn(air));
    remember(3, () => ({ p: PL, yaw: yawOf(dirL) }), AIR.scale, tD + 4, Math.max(T52 + 82, tD + 30));
  });
  let massV;
  scene.at(T52, () => {
    tide.prop("frost", 0).skin(0);
    sound(dim, "ed_tide_sail", up(tideMv.last, 6), 1.3);
    tide.state(D3.rest);
  });
  scene.at(T52 + 10, () => {
    const z = zone();
    massV = scene.spawn("ed_tide_mass", up(z.TL, 3.8), { state: MASS2.gather, size: 1 });
    sound(dim, "ed_tide_mass", up(z.TL, 3.8), 1.5);
  });
  scene.at(T52 + 30, () => massV?.state(MASS2.hold));
  scene.at(T52 + 40, () => {
    const z = zone();
    tideMv.truncate(T52 + 40);
    tideMv.pathIn([z.TL, up(z.TL, 1.8), up(z.TL, 3.5)], 24, { tag: "swim", ease: smooth, yaw: z.tideYaw });
    tideMv.hold(300, z.tideYaw);
    tide.state(D3.swim);
  });
  scene.at(T52 + 64, () => {
    tide.state(D3.depart);
    sound(dim, "ed_tide_depart", up(zone().TL, 3.5), 1.6);
  });
  scene.at(T52 + 64 + D_T.depart, () => scene.despawn(tide));
  remember(2, () => ({ p: up(zone().TL, 3.5), yaw: zone().tideYaw }), TIDE.scale, T52 + 68, T52 + 100);
  scene.at(T52 + 112, () => massV?.state(MASS2.disperse));
  scene.at(T52 + 134, () => {
    if (massV) scene.despawn(massV);
  });
  scene.at(T52 + 22, () => {
    heat.state(H.cool).skin(H_SKIN.ignited);
    sound(dim, "ed_heat_cool", up(heatMv.last, 3), 1.6);
    ring(dim, "ed_heat_steam", up(heatMv.last, 3), 2.5, 6);
  });
  scene.at(T52 + 34, () => heat.skin(H_SKIN.cool));
  scene.every(4, (e) => particle(dim, e % 8 ? "ed6_sizzle" : "ed_heat_steam", up(heatMv.posAt(scene.tick), 3 + e % 3)), T52 + 22, T52 + 84);
  scene.at(T52 + 22 + H_T.cool, () => heat.state(H.pant));
  scene.at(T52 + 60, () => heat.state(H.rest));
  scene.at(T52 + 84, () => {
    heat.state(H.depart);
    sound(dim, "ed_heat_depart", up(heatMv.posAt(scene.tick), 3), 1.5);
  });
  scene.at(T52 + 84 + H_T.depart, () => scene.despawn(heat));
  remember(1, () => ({ p: heatMv.posAt(scene.tick), yaw: heatMv.lastYaw }), HEAT.scale, T52 + 88, T52 + 118);
  scene.at(T52, () => {
    nature.state(N2.rest);
    sound(dim, "ed_nature_moan", nHead(), 1.8);
  });
  scene.at(T52 + 92, () => nature.state(N2.depart));
  scene.at(T52 + 92 + N_T.depart, () => scene.despawn(nature));
  remember(0, () => ({ p: ground(natMv.posAt(scene.tick)), yaw: natMv.lastYaw }), NATURE.scale, T52 + 96, T52 + 136);
  scene.every(3, (e) => {
    const p = natMv.posAt(scene.tick);
    particle(dim, e % 2 ? "ed6_bone_dust" : "ed6_rune_rise", local3(
      up(p, 3 + e % 4 * 2),
      natMv.lastYaw,
      (hash012(e, 50) - 0.5) * 6,
      (hash012(e, 51) - 0.5) * 28
    ));
  }, T52 + 92, T52 + 140);
  scene.at(T_SEAL - 26, () => sound(dim, "ed6_swell", K3, 1.2, 1.3));
  scene.every(2, (e) => {
    const a = e * 47, r = 6 - e % 6 * 0.8;
    particle(dim, e % 3 ? "ed6_stream" : "ed6_codex_rune", add(up(K3, CODEX_CORE), { x: Math.cos(a * Math.PI / 180) * r, y: e % 5 - 2, z: Math.sin(a * Math.PI / 180) * r }));
  }, T_SEAL - 24, T_SEAL);
  scene.at(T_SEAL, () => {
    codex.prop("sep", 0).prop("open", 0).state(CODEX2.beat);
    scene.after(12, () => codex.state(CODEX2.hover));
    codex.skin(4);
    const Kc = up(K3, CODEX_CORE);
    sound(dim, "ed6_seal", Kc, 2.4);
    sound(dim, "ed6_codex_close", Kc, 1.8);
    particle(dim, "fx_flash", Kc);
    particle(dim, "ed6_ring_v", Kc);
    particle(dim, "ed6_column", ground(K3));
    burst(dim, "ed6_seal", Kc, 1, 3);
    burst(dim, "ed6_codex_glint", Kc, 3, 6);
    for (let k2 = 0; k2 < 4; k2++) particle(dim, `ed6_flash_${LINEAGE[k2]}`, add(Kc, mul(W2.dir(k2 * 90 + 45), 1.6)));
    light(up(K3, 0.5), 60);
  });
  const restoreAt = (p) => T_SEAL + 6 + Math.round(distXZ(p, ground(K3)) * 0.9);
  scene.at(T_SEAL + 4, () => {
    sound(dim, "ed6_restore", up(ground(K3), 2), 2.2);
    sound(dim, "ed6_world_fade", up(at(16, 0), 2), 1.8);
    particle(dim, "ed6_light_wave", up(ground(K3), 0.3));
    particle(dim, "ed6_wave", up(ground(K3), 0.4));
  });
  scene.at(T_SEAL + 16, () => particle(dim, "ed6_light_wave", up(ground(K3), 0.3)));
  scene.at(T_SEAL + 4, () => {
    fading = 0.6;
    for (const b of bridges) scene.at(restoreAt(b.loc), () => {
      b.state(BRIDGE2.shatter);
      sound(dim, "ed_tide_shatter", b.loc, 1);
      burst(dim, "ed6_snow", up(b.loc, 2), 2, 3);
    });
    for (const s of natStructs) scene.at(restoreAt(s.loc), () => {
      s.state(STRATA2.crumble);
      particle(dim, "ed6_trail_nature", up(s.loc, 1));
    });
    for (const s of stones) scene.at(restoreAt(s.at), () => {
      if (!s.gone) {
        s.a.state(STONE.sink);
        particle(dim, "fx_dust", up(s.at, 0.5));
        particle(dim, "ed6_rune_rise", up(s.at, 1));
      }
    });
    for (const f of flora) scene.at(restoreAt(f.at), () => {
      f.a.state(FLORA.wither);
      burst(dim, "ed6_pollen_drift", up(f.at, 2), 2, 2);
      particle(dim, "ed6_mote", up(f.at, 3));
    });
    for (const g of glasses) scene.at(restoreAt(g.at), () => g.a.state(GLASS2.fade));
  });
  scene.at(T_SEAL + 26, () => {
    fading = 0.3;
    fog?.state(FOG_CLEAR);
    horizon?.state(HORIZON.sink);
  });
  scene.at(T_SEAL + 40, () => {
    domain?.state(EMBLEM.fade);
    burst(dim, "ed6_rune_rise", up(ground(C0), 0.4), 5, 6);
  });
  scene.at(T_SEAL + 66, () => {
    if (domain) scene.despawn(domain);
  });
  scene.at(T_SEAL + 50, () => {
    fading = 0.12;
  });
  scene.at(T_SEAL + 58, () => {
    for (const b of bridges) scene.despawn(b);
    for (const s of natStructs) scene.despawn(s);
    for (const s of stones) scene.despawn(s.a);
    for (const f of flora) scene.despawn(f.a);
  });
  scene.at(T_SEAL + 76, () => {
    if (horizon) scene.despawn(horizon);
    if (fog) scene.despawn(fog);
  });
  scene.at(T_SEAL + 30, () => {
    cxFlip = false;
  });
  scene.every(2, (e) => particle(dim, e % 4 ? "ed6_stream" : "ed6_codex_rune", up(cxMv.posAt(scene.tick), 1.6 + e % 3)), T_SEAL + 20, T_SEAL + 62);
  scene.at(T_SEAL + 44, () => {
    codex.state(CODEX2.vanish);
    sound(dim, "ed6_absorb", cxAt(), 1.6, 0.8);
  });
  scene.at(T_SEAL + 62, () => {
    const p = up(cxAt(), 3.2);
    burst(dim, "ed6_codex_glint", p, 1.5, 6);
    particle(dim, "ed6_ring_v", p);
    stream(p, BOOK3, 14, ["ed6_stream", "ed6_inscribe", "ed6_codex_glint"], 4, 3);
    sound(dim, "ed6_codex_close", p, 1.6, 1.3);
  });
  scene.at(T_SEAL + 76, () => {
    sound(dim, "ed6_absorb", BOOK3, 0.9, 1.2);
    burst(dim, "ed6_codex_glint", BOOK3, 0.4, 3);
  });
  scene.at(T_SEAL + 70, () => scene.despawn(codex));
  scene.onEnd(() => {
    for (const p of lights) tb.remove(p);
  });
  scene.endAt(T_END3);
  function yawToFrame(yaw) {
    const d = fromYaw(yaw);
    return Math.atan2(dot(d, R2), dot(d, F)) * 180 / Math.PI;
  }
});
function bezier3(pts, p) {
  const n = pts.length - 1;
  const f = clamp(p, 0, 1) * n, i = Math.min(n - 1, Math.floor(f)), u = f - i;
  const a = pts[Math.max(0, i - 1)], b = pts[i], c = pts[i + 1], d = pts[Math.min(n, i + 2)];
  const k2 = (x0, x1, x2, x3) => 0.5 * (2 * x1 + (-x0 + x2) * u + (2 * x0 - 5 * x1 + 4 * x2 - x3) * u * u + (-x0 + 3 * x1 - 3 * x2 + x3) * u * u * u);
  return { x: k2(a.x, b.x, c.x, d.x), y: k2(a.y, b.y, c.y, d.y), z: k2(a.z, b.z, c.z, d.z) };
}

// src/spells/index.ts
function registerAllSpells() {
  for (const s of [dw01_seraphic_litany_default, dw02_cherubic_testament_default, dw03_ophanim_default, dw04_sanctuary_default, dw05_heavenly_throne_default, dw06_word_before_creation_default, dn01_reverie_procession_default, dn02_nightmare_intrusion_default, dn03_shifting_house_default, dn04_lullaby_and_scream_default, dn05_sleeping_city_default, dn06_the_dreamer_default, ed01_genesis_colossus_default, ed02_thermal_tyrant_default, ed03_abyssal_cryotitan_default, ed04_aether_raptor_default, ed05_buried_kingdoms_default, ed06_world_before_names_default]) registerSpell(s);
}

// src/main.ts
registerAllSpells();
function giveBooks(p) {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (const g of Object.values(GRIMOIRES)) inv.addItem(new ItemStack2(g.item, 1));
}
function forceCast(p, id) {
  const spell = getSpell(id);
  if (!spell) return `unknown spell '${id}' (use dw01..dw06, dn01..dn06, ed01..ed06)`;
  const scene = Scenes.start(spell.id, p);
  let ok;
  try {
    ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: 20 });
  } catch (e) {
    scene.end();
    return `error: ${e}`;
  }
  if (ok === false) {
    scene.end();
    return `${id}: no valid target`;
  }
  startCooldown(p, spell.id, spell.cooldown);
  return `cast ${id} (${META_BY_ID[id].name})`;
}
system4.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  reg.registerCommand(
    { name: "grimoire:give", description: "Give yourself the three Grimoires", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player4)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system4.run(() => giveBooks(p));
      return { status: CustomCommandStatus.Success, message: "Three Grimoires added to your inventory" };
    }
  );
  reg.registerCommand(
    { name: "grimoire:reset", description: "Clear all of your Grimoire spell cooldowns", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player4)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system4.run(() => clearCooldowns(p));
      return { status: CustomCommandStatus.Success, message: "Grimoire cooldowns cleared" };
    }
  );
  reg.registerCommand(
    { name: "grimoire:cleanup", description: "End every active Grimoire spell and remove its constructs", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
    () => {
      system4.run(() => {
        Scenes.endAll();
        Scenes.sweepOrphans();
      });
      return { status: CustomCommandStatus.Success, message: "Grimoire spells ended" };
    }
  );
});
system4.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity instanceof Player4 ? ev.sourceEntity : void 0;
  const arg = ev.message.trim().toLowerCase();
  switch (ev.id) {
    case "grimoire:give":
      if (p) giveBooks(p);
      break;
    case "grimoire:reset":
      if (p) {
        clearCooldowns(p);
        p.sendMessage("Grimoire cooldowns cleared");
      }
      break;
    case "grimoire:cast":
      if (p) p.sendMessage(`[grimoire] ${forceCast(p, arg)}`);
      break;
    case "grimoire:cleanup":
      Scenes.endAll();
      Scenes.sweepOrphans();
      break;
    case "grimoire:show": {
      if (!p) break;
      const [id, st2, kd, sk, sz] = ev.message.trim().split(/\s+/);
      if (!id) {
        p.sendMessage("[grimoire] usage: /scriptevent grimoire:show <actor> [state] [kind] [skin] [size]");
        break;
      }
      const sc = Scenes.start("show", p);
      const a = takeAim(p);
      const at = groundBelow(p.dimension, { x: p.location.x + a.forward.x * 8, y: p.location.y + 1, z: p.location.z + a.forward.z * 8 });
      const actor = sc.spawn(id, at, {
        yaw: a.yaw + 180,
        state: st2 !== void 0 ? Number(st2) : 1,
        kind: kd !== void 0 ? Number(kd) : void 0,
        skin: sk !== void 0 ? Number(sk) : void 0,
        size: sz !== void 0 ? Number(sz) : void 0
      });
      sc.endAt(400);
      p.sendMessage(actor.valid ? `[grimoire] showing ${id} for 20 s` : `[grimoire] cannot spawn '${id}'`);
      if (!actor.valid) sc.end();
      break;
    }
    case "grimoire:config": {
      const [key, val] = arg.split(/\s+/);
      const on = val === "on" || val === "true" || val === "1";
      if (key === "heartbeat") RUNTIME.input.heartbeatFallback = on;
      else if (key === "pvp") RUNTIME.targeting.pvp = on;
      p?.sendMessage(`[grimoire] ${key} = ${on}`);
      break;
    }
  }
}, { namespaces: ["grimoire"] });
world5.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const p = ev.player;
  system4.runTimeout(() => {
    try {
      if (!p.isValid) return;
      p.sendMessage(`\xA76Grimoire: Rebirth of the Arcane \xA7f${VERSION}`);
      if (CONFIG.starterKit && p.getDynamicProperty("grim:kit") !== 1) {
        p.setDynamicProperty("grim:kit", 1);
        giveBooks(p);
        p.sendMessage("\xA77The three Grimoires are in your inventory.  Crouch: next spell.  Hold Use, release: cast.");
      }
    } catch {
    }
  }, 60);
});
world5.afterEvents.worldLoad.subscribe(() => {
  installWards();
  installInput();
  installBooks();
  restoreLedger();
  Scenes.sweepOrphans();
  let n = 0;
  system4.runInterval(() => {
    tickInput();
    Scenes.tickAll();
    flushLedger();
    if (++n % 100 === 0) retryOrphans(anySetOwns);
  }, 1);
});
