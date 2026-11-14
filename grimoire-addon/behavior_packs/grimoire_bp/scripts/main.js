// src/main.ts
import { CommandPermissionLevel, CustomCommandStatus, ItemStack as ItemStack2, Player as Player4, system as system4, world as world5 } from "@minecraft/server";

// src/config/global.ts
var CONFIG = {
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

// src/core/input.ts
import { EquipmentSlot, system, world as world2 } from "@minecraft/server";

// src/lib/scene.ts
import { world } from "@minecraft/server";
var NS = "grimoire";
var secs = (s) => Math.max(0, Math.round(s * 20));
var warned = /* @__PURE__ */ new Set();
function warnOnce(key, msg) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`[grimoire] ${msg}`);
}
var Actor = class {
  constructor(entity, typeId) {
    this.entity = entity;
    this.typeId = typeId;
  }
  lastYaw = 0;
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
    return this.prop("size", n);
  }
  skin(n) {
    return this.prop("skin", n);
  }
  /** Teleport (and optionally face a yaw).  Called every tick this gives smooth motion. */
  move(loc, yaw) {
    if (!this.valid) return this;
    if (yaw !== void 0) this.lastYaw = yaw;
    try {
      this.entity.teleport(loc, { rotation: { x: 0, y: this.lastYaw } });
    } catch {
    }
    return this;
  }
  face(yaw) {
    if (!this.valid) return this;
    this.lastYaw = yaw;
    try {
      this.entity.setRotation({ x: 0, y: yaw });
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
      if (opts.yaw !== void 0) a.face(opts.yaw);
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
function groundBelow(dim, loc, maxDrop = 40) {
  try {
    const hit = dim.getBlockFromRay(
      { x: loc.x, y: loc.y + 1.5, z: loc.z },
      { x: 0, y: -1, z: 0 },
      { maxDistance: maxDrop, includePassableBlocks: false, includeLiquidBlocks: true }
    );
    if (hit) return { x: loc.x, y: hit.block.location.y + 1, z: loc.z };
  } catch {
  }
  return { x: loc.x, y: loc.y, z: loc.z };
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
      if (b) point = { x: b.block.location.x + b.faceLocation.x, y: b.block.location.y + b.faceLocation.y, z: b.block.location.z + b.faceLocation.z };
    } catch {
    }
  }
  if (!point) point = add(head, mul(dir, range * 0.55));
  const forward = norm(flat(dir));
  return { point, ground: groundBelow(dim, point), entity, dir, forward, yaw: yawOf(forward), from: { ...caster.location } };
}
function focus(caster, aim, snap = 10) {
  if (aim.entity && isAlive(aim.entity)) return { center: groundBelow(caster.dimension, aim.entity.location), target: aim.entity };
  const near = hostiles(caster.dimension, aim.ground, snap, caster, 1);
  if (near.length) return { center: groundBelow(caster.dimension, near[0].location), target: near[0] };
  return { center: aim.ground };
}

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
    /** Life of the selection vision; its one-shot "show" animation lasts exactly 1.2 s. */
    ticks: 24,
    /** Placement from the eyes: along the view, to the right, and vertical offset.  Sits above the book hand. */
    ahead: 1.3,
    right: 0.55,
    up: -0.2,
    /** Volume of the page-turn + motif sound. */
    volume: 0.8
  },
  charge: {
    /** Ticks of the one-shot "form" animation (1.5 s) before switching to the "loop" state. */
    formTicks: 30,
    /** The release flare (0.5 s) and the quiet cancel fold (0.4 s) before the construct is removed. */
    releaseTicks: 10,
    cancelTicks: 8,
    /** Placement from the eyes: ahead along the view, to the right (keeps the crosshair clear), above eye line. */
    ahead: 2.2,
    right: 0.8,
    up: 0.4,
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
    dim.spawnParticle(id.includes(":") ? id : `${NS}:${id}`, loc, vars);
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
    dim.playSound(id.includes(".") ? id : `${NS}.${id}`, loc, { volume, pitch });
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
    let P5 = live2.map((m) => flat(m.e.location));
    const c0 = P5.length ? mul(P5.reduce((s, p) => add(s, p), v(0, 0, 0)), 1 / P5.length) : flat(lastCentre);
    const c = v(c0.x, 0, c0.z);
    lastCentre = v(c.x, center.y, c.z);
    if (!P5.length) P5 = [0, 1, 2, 3, 4].map((i) => polar(c, DW03.noTargetRadius, aim.yaw + 90 + i * 72));
    let far = P5[0];
    for (const p of P5) if (distXZ(p, c) > distXZ(far, c)) far = p;
    const R2 = clamp(distXZ(far, c) + 1.5, DW03.routeMinRadius, DW03.routeMaxRadius);
    const u = distXZ(far, c) > 0.5 ? norm(flat(sub(far, c))) : fromYaw(aim.yaw);
    const a0 = Math.atan2(u.z, u.x) * 180 / Math.PI;
    let corners;
    let name;
    const kind = k2 % 3;
    if (kind === 0) {
      name = "polygon";
      if (P5.length >= 3) {
        corners = [...P5].sort((p, q) => Math.atan2(p.z - c.z, p.x - c.x) - Math.atan2(q.z - c.z, q.x - c.x));
      } else if (P5.length === 2) {
        const mid = lerp(P5[0], P5[1], 0.5);
        const side = right(sub(P5[1], P5[0]));
        corners = [P5[0], add(mid, mul(side, R2 * 0.9)), P5[1], add(mid, mul(side, -R2 * 0.9))];
      } else {
        const q = sub(P5[0], mul(u, R2));
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

// src/spells/dw05_heavenly_throne.ts
var dw05_heavenly_throne_default = defineSpell("dw05", (ctx) => {
  ctx.caster.sendMessage("dw05 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/config/dw06.ts
var DW06 = {
  // ---- Phase I: the silence before all things
  /** Radius of the spell's domain around the focus point (blocks). */
  domainRadius: 19,
  /** How far the focus may snap from the aim point to an enemy. */
  focusSnap: 14,
  /** Most enemies that receive a sacred mark. */
  maxMarks: 10,
  // ---- Phase II: the first utterance (letters land as structures)
  /** Impact radius / damage / knockback of each structure kind when it lands:
   *  0 column, 1 arch (per pier), 2 bridge (swing sweep), 3 gate, 4 platform (shove only), 5 celestial. */
  landRadius: [2.6, 2.2, 7.5, 4, 3.2, 4],
  landDamage: [10, 8, 8, 12, 0, 7],
  landKnock: [1.2, 1, 1.6, 1.8, 1, 0.8],
  /** Columns and celestial formations land on an enemy if one is within this distance of their slot. */
  seekRadius: 9,
  /** Height (blocks) of barrier obstruction for columns, arch piers and gate pylons. */
  barrierHeight: [9, 8, 0, 10, 0, 0],
  /** Allies within this horizontal distance of a platform or bridge take reduced damage (cover). */
  coverRadius: 4.5,
  coverFactor: 0.6,
  /** Celestial formations pulse damage on enemies beneath them while they stand. */
  celestialPulseRadius: 4.5,
  celestialPulseDamage: 3,
  celestialPulseEvery: 20,
  // ---- Phase III: the seven laws
  /** I Containment: ring of written walls around the densest hostile region. */
  containRadius: 6,
  containPull: 13,
  containPullStrength: 0.9,
  /** II Station: how many structures slide to defend, and how far in front of the caster. */
  stationCount: 3,
  stationDistance: 6,
  /** III Direction: moving text walls -- damage, half-width of the wall, half-depth of the hit band. */
  directionDamage: 7,
  directionHalfWidth: 3.6,
  directionBand: 1.6,
  directionTicks: 40,
  /** IV Stillness: restraint duration, then lingering slowness (amplifier). */
  stillTicks: 60,
  stillSlowTicks: 100,
  stillSlowAmp: 3,
  /** V Refuge: allied zone radius, damage factor inside it, instant heal and regen per 2 s. */
  refugeRadius: 5,
  refugeFactor: 0.4,
  refugeHeal: 6,
  refugeRegen: 2,
  /** VI Sequence: each structure strikes the enemies around it in turn. */
  sequenceRadius: 4.5,
  sequenceDamage: 5,
  /** VII Judgment: radius of the designated finale region (and its telegraph). */
  finalRadius: 7,
  // ---- Phase IV: let it be written (descending lines)
  sweepDamage: 10,
  sweepHalfLength: 12,
  ringDamage: 10,
  ringMaxRadius: 17,
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
var BOOK = { hidden: 0, arrive: 1, open: 2, unbind: 3, layered: 4, gather: 5, close: 6 };
var PAGE = { hidden: 0, manifest: 1, idle: 2, split: 3, reform: 4, fold: 5, slip: 6 };
var GLYPH = { draw: 1, fall: 2, land: 3 };
var ED = { assemble: 1, hold: 2, swing: 3, strike: 4, unwrite: 5 };
var WALL = { rise: 1, hold: 2, sink: 3 };
var DOME = { form: 1, hold: 2, fade: 3 };
var BOUND = { inscribe: 1, hold: 2, unwrite: 3 };
var TAB = { form: 1, idle: 2, declare: 3, shed: 4, ret: 5 };
var LINE = { assemble: 1, hold: 2, strike: 3, unwrite: 4 };
var PAGE_TILT = 32 * (Math.PI / 180);
var PAGE_SCALE = 4 / 16;
var ED_SCALE = 2 / 16;
var COLUMN = 0;
var ARCH = 1;
var BRIDGE = 2;
var GATE = 3;
var PLATFORM = 4;
var CELESTIAL = 5;
var dw06_word_before_creation_default = defineSpell("dw06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center: C0, target } = focus(caster, aim, DW06.focusSnap);
  const center = groundBelow(dim, C0);
  const c0 = caster.location;
  let fwd = norm(flat(sub(center, c0)));
  if (distXZ(center, c0) < 3) fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);
  const P5 = (a, b, h = 0) => up(add(add(center, mul(rt, a)), mul(fwd, b)), h);
  const ground = (p) => groundBelow(dim, up(p, 3), 12);
  const faceCaster = (p) => yawOf(sub(caster.isValid ? caster.location : c0, p));
  const domain = () => hostiles(dim, center, DW06.domainRadius, caster);
  const isAlly = (e) => e.typeId === "minecraft:player" && (e.id === caster.id || !CONFIG.targeting.pvp);
  const marks = /* @__PURE__ */ new Map();
  function mark(e, skin = 0) {
    let m = marks.get(e.id);
    if (!m || !m.a.valid) {
      if (marks.size >= DW06.maxMarks || !isAlive(e)) return;
      const a = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1 });
      scene.follow(a, e, 2.4);
      m = { e, a };
      marks.set(e.id, m);
      sound(dim, "dw_mark", e.location, 0.6, 0.9 + skin * 0.1);
    }
    m.a.skin(skin);
  }
  const bookAt = up(add(add(c0, mul(rt, 3.4)), mul(fwd, 1.6)), 1.3);
  const book = scene.spawn("dw6_book", bookAt, { yaw: faceCaster(bookAt), state: BOOK.arrive });
  sound(dim, "dw6_silence", c0, 1);
  sound(dim, "dw6_book", bookAt, 0.9);
  const boundary = scene.spawn("dw6_boundary", up(center, 0.05), { state: BOUND.inscribe });
  scene.at(40, () => boundary.state(BOUND.hold));
  scene.every(20, () => particle(dim, "dw6_motes", P5(0, 0, 6)), 0, 140);
  scene.at(18, () => particle(dim, "dw6_bell", P5(0, 0, 10)));
  tb.place(up(bookAt, 1), LIGHT);
  scene.at(14, () => {
    for (const e of domain()) mark(e);
  });
  scene.at(60, () => book.state(BOOK.open));
  scene.at(70, () => {
    book.state(BOOK.unbind).skin(1);
    sound(dim, "dw6_unbind", bookAt, 0.9);
  });
  scene.every(5, () => burst(dim, "dw6_letters", up(bookAt, 1.2), 1.4, 2), 72, 104);
  scene.at(110, () => book.state(BOOK.layered));
  const pageO = P5(0, 5, 9);
  const pd = norm(flat(sub(c0, pageO)));
  const pageYaw = yawOf(pd);
  const pr = right(pd);
  const pageUp = add(mul(up({ x: 0, y: 0, z: 0 }, 1), Math.cos(PAGE_TILT)), mul(pd, -Math.sin(PAGE_TILT)));
  const pageN = add(mul(pd, Math.cos(PAGE_TILT)), up({ x: 0, y: 0, z: 0 }, Math.sin(PAGE_TILT)));
  const pagePt = (a, y, off = 0) => add(add(add(pageO, mul(pr, -a * PAGE_SCALE)), mul(pageUp, y * PAGE_SCALE)), mul(pageN, off));
  let page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.hidden });
  scene.at(75, () => {
    page.state(PAGE.manifest);
    sound(dim, "dw6_page", pagePt(0, 44), 1.2);
    line(dim, "dw6_seam", pagePt(0, 0, 0.3), pagePt(0, 88, 0.3), 10);
  });
  scene.at(125, () => page.state(PAGE.idle));
  const tWrite0 = 140, tWriteStep = 28;
  const plan = [
    { kind: COLUMN, a: -7, b: 1 },
    { kind: COLUMN, a: 7, b: 1 },
    { kind: ARCH, a: 0, b: -5 },
    { kind: PLATFORM, a: -4.5, b: -99 },
    { kind: BRIDGE, a: 0, b: 4.5 },
    { kind: GATE, a: 0, b: 13 },
    { kind: COLUMN, a: -11, b: 9 },
    { kind: CELESTIAL, a: 6, b: 9 },
    { kind: PLATFORM, a: 4.5, b: -99 },
    { kind: ARCH, a: 12, b: 3 }
  ];
  const edifices = [];
  const claimed = /* @__PURE__ */ new Set();
  const cover = [];
  addWard({
    scene,
    factor: DW06.coverFactor,
    protects: (e) => isAlly(e) && cover.some((p) => distXZ(p, e.location) <= DW06.coverRadius)
  });
  function landingSpot(i) {
    const s = plan[i];
    let p = s.b === -99 ? up(add(add(c0, mul(rt, s.a)), mul(fwd, 2.5)), 0) : P5(s.a, s.b);
    if (s.kind === COLUMN || s.kind === CELESTIAL) {
      const near = hostiles(dim, p, DW06.seekRadius, caster).filter((e) => !claimed.has(e.id) && dist(e.location, center) <= DW06.domainRadius);
      if (near.length) {
        claimed.add(near[0].id);
        p = near[0].location;
      }
    }
    return ground(p);
  }
  function cellsFor(kind, at) {
    const r = right(norm(flat(sub(c0, at))));
    const offs = kind === COLUMN ? [0] : kind === ARCH ? [-22 * ED_SCALE, 22 * ED_SCALE] : kind === GATE ? [-3.9, -2.9, 2.9, 3.9] : [];
    return offs.map((o) => add(at, mul(r, o)));
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
  function impact(kind, at, cellPts) {
    const spots = kind === ARCH ? cellPts : [at];
    particle(dim, "dw6_quake", up(at, 0.2));
    particle(dim, "dw6_dust", up(at, 0.4));
    particle(dim, "dw6_flare", up(at, 2));
    burst(dim, "dw6_ink", up(at, 3), 2.5, 3);
    sound(dim, "dw6_land", at, 1.3, 1 - kind * 0.03);
    if (DW06.landDamage[kind] <= 0 && kind !== PLATFORM) return;
    const hit = /* @__PURE__ */ new Set();
    for (const s of spots) {
      for (const e of hostiles(dim, s, DW06.landRadius[kind], caster)) {
        if (hit.has(e.id)) continue;
        hit.add(e.id);
        if (DW06.landDamage[kind] > 0) damage(e, DW06.landDamage[kind], caster);
        knockback(e, s, DW06.landKnock[kind], 0.4);
      }
    }
  }
  function writeLetter(i) {
    const t0 = tWrite0 + i * tWriteStep;
    const s = plan[i];
    const slotA = -36 + i % 5 * 19, slotY = i < 5 ? 63 : 25;
    let land = P5(0, 0);
    let warn;
    let glyph;
    scene.at(t0, () => {
      land = landingSpot(i);
      const at = pagePt(slotA, slotY, 0.6);
      glyph = scene.spawn("dw6_glyph", at, { yaw: pageYaw, kind: s.kind, state: GLYPH.draw });
      sound(dim, "dw6_stroke", at, 1.2);
      warn = scene.spawn("telegraph", land, { kind: 0, size: s.kind === BRIDGE ? DW06.landRadius[BRIDGE] : Math.max(2, DW06.landRadius[s.kind]), state: 4 });
    });
    scene.every(4, (e) => particle(dim, "dw6_ink", pagePt(slotA + e % 8 - 4, slotY + 12 - e * 1.1, 0.8)), t0 + 2, t0 + 24);
    scene.at(t0 + 24, () => {
      glyph?.state(GLYPH.fall);
      sound(dim, "dw6_fall", pagePt(slotA, slotY), 1);
    });
    scene.span(t0 + 24, t0 + 40, (p) => {
      const from = pagePt(slotA, slotY, 0.6);
      const to = up(land, 3.5);
      const mid = up(lerp(from, to, 0.5), 3);
      glyph?.move(bezier(from, mid, to, p * p), pageYaw);
      if (glyph && scene.tick % 2 === 0) particle(dim, "dw6_stream", glyph.loc);
    });
    scene.at(t0 + 40, () => {
      if (glyph) {
        glyph.state(GLYPH.land);
        const g = glyph;
        scene.after(10, () => scene.despawn(g));
      }
      if (warn) {
        warn.state(3);
        const w = warn;
        scene.after(8, () => scene.despawn(w));
      }
      const yaw = faceCaster(land);
      const a = scene.spawn("dw6_edifice", land, { yaw, kind: s.kind, state: s.kind === BRIDGE ? ED.swing : ED.assemble });
      const ed = { a, kind: s.kind, at: land, yaw, cells: cellsFor(s.kind, land), h: DW06.barrierHeight[s.kind] };
      edifices.push(ed);
      if (s.kind === BRIDGE) {
        sound(dim, "dw6_swing", land, 1.2);
        scene.after(21, () => impact(BRIDGE, land, []));
      } else impact(s.kind, land, ed.cells);
      if (ed.cells.length) raiseBarriers(ed);
      if (s.kind === PLATFORM || s.kind === BRIDGE) cover.push(land);
      if (s.kind === CELESTIAL) {
        scene.every(DW06.celestialPulseEvery, () => {
          if (!a.valid) return;
          particle(dim, "dw6_rays", up(ed.at, 0.3));
          for (const e of hostiles(dim, ed.at, DW06.celestialPulseRadius, caster)) damage(e, DW06.celestialPulseDamage, caster);
        }, scene.tick + 20, tPhase5);
      }
      scene.after(s.kind === BRIDGE ? 28 : 32, () => a.state(ED.hold));
      for (const e of hostiles(dim, land, DW06.landRadius[s.kind] + 1, caster)) if (dist(e.location, center) <= DW06.domainRadius) mark(e);
    });
  }
  for (let i = 0; i < plan.length; i++) writeLetter(i);
  const tSplit = tWrite0 + tWriteStep * plan.length + 30;
  const tablets = [];
  const stations = [];
  for (let k2 = 0; k2 < 7; k2++) {
    const th = (-66 + 22 * k2) * Math.PI / 180;
    const dir = add(mul(fwd, Math.cos(th)), mul(rt, Math.sin(th)));
    stations.push(up(add(center, mul(dir, 17)), 7));
  }
  const ruleA = (k2) => -45 + 102 / 7 * (k2 + 0.5);
  scene.at(tSplit, () => {
    page.state(PAGE.split);
    sound(dim, "dw6_split", pagePt(0, 44), 1.3);
    for (let k2 = 1; k2 < 7; k2++) line(dim, "dw6_seam", pagePt(-45 + 102 / 7 * k2, 6, 0.5), pagePt(-45 + 102 / 7 * k2, 82, 0.5), 6);
  });
  scene.at(tSplit + 6, () => {
    for (let k2 = 0; k2 < 7; k2++) {
      const from = pagePt(ruleA(k2), 44, 0.4);
      tablets.push(scene.spawn("dw6_tablet", from, { yaw: pageYaw, kind: k2, state: TAB.form }));
    }
  });
  scene.span(tSplit + 6, tSplit + 36, (p) => {
    tablets.forEach((t, k2) => {
      const from = pagePt(ruleA(k2), 44, 0.4);
      const to = stations[k2];
      t.move(bezier(from, up(lerp(from, to, 0.5), 4), to, p * p * (3 - 2 * p)), faceCaster(to));
    });
  });
  scene.at(tSplit + 30, () => {
    scene.despawn(page);
  });
  scene.at(tSplit + 36, () => tablets.forEach((t) => t.state(TAB.idle)));
  const tLaw0 = tSplit + 50, tLawStep = 34;
  const walls = [];
  let refuge;
  let refugeAt = c0;
  let refugeOn = false;
  addWard({ scene, factor: DW06.refugeFactor, protects: (e) => refugeOn && isAlly(e) && distXZ(e.location, refugeAt) <= DW06.refugeRadius });
  let finalAt = center;
  let finalWarn;
  const judged = /* @__PURE__ */ new Set();
  const judgedWarn = [];
  function centroid(es, fallback) {
    if (!es.length) return fallback;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return mul(s, 1 / es.length);
  }
  function declare(k2, at) {
    const t = tablets[k2];
    t.state(TAB.declare);
    sound(dim, `dw6_law${k2 + 1}`, t.loc, 1.4);
    line(dim, "dw6_stream", up(t.loc, 3), up(at, 1), 10);
    particle(dim, "dw6_quake", up(at, 0.3));
    scene.after(34, () => t.state(TAB.idle));
  }
  const laws = [
    // I Containment: a ring of written walls closes around the densest hostile region and draws it in
    () => {
      const es = domain();
      const H = ground(centroid(es, P5(0, 5)));
      declare(0, H);
      const R2 = DW06.containRadius;
      const players = allies(dim, H, R2 + 1.5, caster);
      const door = yawOf(sub(c0, H));
      for (let i = 0; i < 8; i++) {
        const ang = i * 45 + 22.5;
        const rad = ang * Math.PI / 180;
        const p = ground({ x: H.x + Math.cos(rad) * R2, y: H.y, z: H.z + Math.sin(rad) * R2 });
        walls.push(scene.spawn("dw6_wall", p, { yaw: yawOf(sub(H, p)), kind: 0, size: 1.2, state: WALL.rise }));
      }
      scene.after(20, () => walls.forEach((w) => w.state(WALL.hold)));
      for (const d of [2, 8]) {
        scene.after(d, () => {
          for (const e of hostiles(dim, H, DW06.containPull, caster)) if (distXZ(e.location, H) > R2 - 1.5) shove(e, sub(H, e.location), DW06.containPullStrength, 0.25);
        });
      }
      scene.after(16, () => {
        for (let s = 0; s < 64; s++) {
          const a = s * 360 / 64;
          if (players.length && Math.abs(((a - (door + 90)) % 360 + 540) % 360 - 180) < 22) continue;
          const rad = a * Math.PI / 180;
          const p = ground({ x: H.x + Math.cos(rad) * R2, y: H.y, z: H.z + Math.sin(rad) * R2 });
          tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), 3);
        }
      });
    },
    // II Station: written structures slide between the allies and the enemy
    () => {
      const E = centroid(domain(), center);
      const A3 = caster.isValid ? caster.location : c0;
      const toE = norm(flat(sub(E, A3)));
      const side = right(toE);
      const d = Math.min(DW06.stationDistance, Math.max(3, distXZ(E, A3) / 2));
      const movers = edifices.filter((e) => e.kind === COLUMN || e.kind === ARCH).slice(0, DW06.stationCount);
      declare(1, add(A3, mul(toE, d)));
      movers.forEach((ed, j) => {
        const dest = ground(add(add(A3, mul(toE, d)), mul(side, (j - (movers.length - 1) / 2) * 4.5)));
        const from = ed.at;
        dropBarriers(ed);
        ed.a.state(ED.strike);
        scene.span(scene.tick + 2, scene.tick + 32, (p) => {
          const q = p * p * (3 - 2 * p);
          ed.a.move(up(lerp(from, dest, q), Math.sin(q * Math.PI) * 1.5));
          if (scene.tick % 3 === 0) particle(dim, "dw6_dust", up(lerp(from, dest, q), 0.3));
        });
        scene.after(33, () => {
          ed.at = dest;
          ed.cells = cellsFor(ed.kind, dest);
          ed.a.state(ED.hold);
          raiseBarriers(ed);
          particle(dim, "dw6_quake", up(dest, 0.2));
        });
      });
    },
    // III Direction: three lines of text fire across the field as moving walls
    () => {
      declare(2, P5(0, 4));
      const lanes = [-2, 4, 10];
      lanes.forEach((b, j) => {
        const from = ground(P5(-17, b)), to = ground(P5(17, b));
        line(dim, "dw6_ink", up(from, 0.5), up(to, 0.5), 8);
        const w = scene.spawn("dw6_wall", from, { yaw: yawOf(rt), kind: 1, size: 1.4, state: WALL.rise });
        walls.push(w);
        const hit = /* @__PURE__ */ new Set();
        const t0 = scene.tick + 14 + j * 6;
        scene.at(t0, () => w.state(WALL.hold));
        scene.span(t0, t0 + DW06.directionTicks, (p) => {
          const at = lerp(from, to, p);
          w.move(at);
          for (const e of hostiles(dim, at, DW06.directionHalfWidth + 1, caster)) {
            const rel = sub(e.location, at);
            const along = rel.x * rt.x + rel.z * rt.z;
            const lat = rel.x * fwd.x + rel.z * fwd.z;
            if (Math.abs(along) > DW06.directionBand || Math.abs(lat) > DW06.directionHalfWidth || hit.has(e.id)) continue;
            hit.add(e.id);
            damage(e, DW06.directionDamage, caster);
            shove(e, rt, 1.1, 0.3);
            particle(dim, "dw6_seam", up(e.location, 1));
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
      let n = 0;
      for (const e of domain()) {
        restrain(scene, e, DW06.stillTicks);
        effect(e, "slowness", DW06.stillTicks + DW06.stillSlowTicks, DW06.stillSlowAmp);
        particle(dim, "dw6_blue", up(e.location, 1));
        if (n++ < 8) {
          const g = ground(e.location);
          const ci = scene.spawn("dw_circle", g, { size: 0.6, state: 1 });
          scene.after(8, () => ci.state(2));
          scene.after(DW06.stillTicks, () => ci.state(3));
          scene.after(DW06.stillTicks + 14, () => scene.despawn(ci));
        }
      }
    },
    // V Refuge: the allied zone is shielded and restored
    () => {
      refugeAt = ground(caster.isValid ? caster.location : c0);
      declare(4, refugeAt);
      refuge = scene.spawn("dw6_dome", refugeAt, { state: DOME.form });
      refugeOn = true;
      scene.after(24, () => refuge?.state(DOME.hold));
      for (const p of allies(dim, refugeAt, DW06.refugeRadius, caster)) heal(p, DW06.refugeHeal);
      ring(dim, "dw6_letters", up(refugeAt, 0.5), DW06.refugeRadius, 8);
    },
    // VI Sequence: each written structure strikes in turn
    () => {
      declare(5, center);
      edifices.forEach((ed, j) => {
        scene.after(6 + j * 5, () => {
          ed.a.state(ED.strike);
          scene.after(16, () => ed.a.state(ED.hold));
          const at = ed.at;
          if (ed.kind === COLUMN || ed.kind === GATE) particle(dim, "dw_pillar_burst", up(at, 0.3));
          else if (ed.kind === ARCH) ring(dim, "dw_glyph_fall", up(at, 6), 2.5, 5);
          else particle(dim, "dw6_rays", up(at, 0.3));
          particle(dim, "dw6_quake", up(at, 0.2));
          sound(dim, "dw6_strike", at, 0.7, 1.1 + j * 0.04);
          for (const e of hostiles(dim, at, DW06.sequenceRadius, caster)) {
            damage(e, DW06.sequenceDamage, caster);
            knockback(e, at, 0.6, 0.3);
          }
        });
      });
    },
    // VII Judgment: every surviving enemy is marked and the finale's telegraphs are raised
    () => {
      const es = domain();
      finalAt = ground(target && isAlive(target) && dist(target.location, center) <= DW06.domainRadius ? target.location : centroid(es, center));
      declare(6, finalAt);
      for (const e of es) {
        mark(e, 2);
        judged.add(e.id);
      }
      finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: DW06.finalRadius, state: 4 });
      scene.after(40, () => finalWarn?.state(2));
      for (const e of es.slice(0, 6)) {
        const w = scene.spawn("telegraph", ground(e.location), { kind: 0, size: 1.6, state: 1 });
        scene.after(20, () => w.state(2));
        scene.follow(w, e, 0.05);
        judgedWarn.push(w);
      }
    }
  ];
  laws.forEach((fn, k2) => scene.at(tLaw0 + k2 * tLawStep, fn));
  scene.every(40, () => {
    if (!refugeOn) return;
    for (const p of allies(dim, refugeAt, DW06.refugeRadius, caster)) heal(p, DW06.refugeRegen);
  }, tLaw0 + 4 * tLawStep + 40, tLaw0 + 4 * tLawStep + 600);
  scene.every(10, () => {
    if (refugeOn) dissolveProjectiles(scene, up(refugeAt, 2), DW06.refugeRadius);
  }, tLaw0 + 4 * tLawStep, tLaw0 + 4 * tLawStep + 600);
  const tRise2 = tLaw0 + 7 * tLawStep + 26;
  scene.at(tRise2, () => {
    tablets.forEach((t) => t.state(TAB.shed));
    sound(dim, "dw6_rise", P5(0, 10, 10), 1.4);
  });
  scene.span(tRise2, tRise2 + 40, (p) => tablets.forEach((t, k2) => t.move(up(stations[k2], 10 * p * p * (3 - 2 * p)))));
  scene.every(4, (e) => {
    const t = tablets[e / 4 % 7];
    if (t) particle(dim, "dw6_letters", t.loc);
  }, tRise2, tRise2 + 40);
  scene.at(tRise2 + 40, () => tablets.forEach((t) => t.state(TAB.idle)));
  function spawnLine(kind, at, size = 1) {
    const a = scene.spawn("dw6_line", at, { yaw: faceCaster(at), kind, size, state: LINE.assemble });
    sound(dim, "dw6_form", at, 1.2, 1 + kind * 0.06);
    tablets.forEach((tab, k2) => {
      if (k2 % 2 === kind % 2) line(dim, "dw6_stream", tab.loc, at, 4);
    });
    scene.after(30, () => a.state(LINE.hold));
    return a;
  }
  function descend(a, from, to, t0, t1) {
    scene.span(t0, t1, (p) => a.move(lerp(from, to, p * p)));
  }
  const L1 = { form: tRise2 + 10, desc: tRise2 + 50 };
  let l1 = new Actor(void 0, "");
  const l1Hi = P5(0, 16, 15), l1Lo = up(ground(P5(0, 16)), 1.6);
  scene.at(L1.form, () => {
    l1 = spawnLine(0, l1Hi);
  });
  const sweepWarn = [];
  scene.at(L1.desc - 20, () => {
    for (const b of [12, 4, -4]) sweepWarn.push(scene.spawn("telegraph", ground(P5(0, b)), { kind: 0, size: 3, state: 1 }));
  });
  scene.at(L1.desc, () => descend(l1, l1Hi, l1Lo, L1.desc, L1.desc + 16));
  scene.at(L1.desc + 16, () => {
    l1.state(LINE.strike);
    sound(dim, "dw6_strike", l1Lo, 1.3);
    particle(dim, "dw6_quake", l1Lo);
  });
  {
    const hit = /* @__PURE__ */ new Set();
    scene.span(L1.desc + 16, L1.desc + 52, (p) => {
      const at = up(ground(P5(0, 16 - 23 * p)), 1.6);
      l1.move(at);
      if (scene.tick % 3 === 0) line(dim, "dw6_seam", add(at, mul(rt, -DW06.sweepHalfLength)), add(at, mul(rt, DW06.sweepHalfLength)), 5);
      for (const e of hostiles(dim, at, DW06.sweepHalfLength + 1, caster)) {
        const rel = sub(e.location, at);
        if (hit.has(e.id) || Math.abs(rel.x * fwd.x + rel.z * fwd.z) > 1.6 || Math.abs(rel.x * rt.x + rel.z * rt.z) > DW06.sweepHalfLength) continue;
        hit.add(e.id);
        damage(e, DW06.sweepDamage, caster);
        shove(e, mul(fwd, -1), 0.9, 0.35);
      }
    });
  }
  scene.at(L1.desc + 52, () => sweepWarn.forEach((w) => {
    w.state(3);
    scene.after(8, () => scene.despawn(w));
  }));
  scene.at(L1.desc + 54, () => {
    l1.state(LINE.unwrite);
    burst(dim, "dw6_letters", l1.loc, 3, 4);
  });
  scene.at(L1.desc + 74, () => scene.despawn(l1));
  const L22 = { form: tRise2 + 20, desc: L1.desc + 50 };
  let l2 = new Actor(void 0, "");
  const l2Hi = P5(0, 2, 19), l2Lo = up(center, 1.2);
  let ringWarn;
  scene.at(L22.form, () => {
    l2 = spawnLine(1, l2Hi, 0.6);
  });
  scene.at(L22.desc - 20, () => {
    ringWarn = scene.spawn("telegraph", center, { kind: 0, size: DW06.ringMaxRadius, state: 1 });
  });
  scene.at(L22.desc, () => descend(l2, l2Hi, l2Lo, L22.desc, L22.desc + 16));
  scene.at(L22.desc + 16, () => {
    l2.state(LINE.strike);
    sound(dim, "dw6_strike", center, 1.3, 0.85);
    particle(dim, "dw6_quake", up(center, 0.2));
  });
  {
    const hit = /* @__PURE__ */ new Set();
    scene.span(L22.desc + 16, L22.desc + 46, (p) => {
      const rad = 2 + (DW06.ringMaxRadius - 2) * p;
      l2.size(rad / 7.5);
      if (scene.tick % 4 === 0) ring(dim, "dw6_seam", up(center, 0.6), rad, 10, scene.tick * 7);
      for (const e of hostiles(dim, center, rad + 1.5, caster)) {
        if (hit.has(e.id) || Math.abs(distXZ(e.location, center) - rad) > 1.6) continue;
        hit.add(e.id);
        damage(e, DW06.ringDamage, caster);
        knockback(e, center, 1, 0.4);
      }
    });
  }
  scene.at(L22.desc + 46, () => {
    if (ringWarn) {
      ringWarn.state(3);
      const w = ringWarn;
      scene.after(8, () => scene.despawn(w));
    }
  });
  scene.at(L22.desc + 48, () => {
    l2.state(LINE.unwrite);
  });
  scene.at(L22.desc + 68, () => scene.despawn(l2));
  const L3 = { form: tRise2 + 30, desc: L22.desc + 50 };
  let l3 = new Actor(void 0, "");
  const l3Hi = P5(0, 3, 21), l3Lo = P5(0, 3, 9);
  scene.at(L3.form, () => {
    l3 = spawnLine(2, l3Hi);
  });
  scene.at(L3.desc, () => descend(l3, l3Hi, l3Lo, L3.desc, L3.desc + 16));
  const cell = (gx, gz) => {
    const d = norm(flat(sub(c0, l3Lo)));
    return ground(add(add(l3Lo, mul(right(d), gx * 6)), mul(d, -gz * 6)));
  };
  const waves = [[[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]], [[0, -1], [-1, 0], [1, 0], [0, 1]]];
  waves.forEach((cells, w) => {
    const tw = L3.desc + 20 + w * 22;
    const spots = [];
    const warns = [];
    scene.at(tw - 20, () => {
      for (const [gx, gz] of cells) {
        const s = cell(gx, gz);
        spots.push(s);
        warns.push(scene.spawn("telegraph", s, { kind: 0, size: DW06.latticeRadius, state: 1 }));
      }
    });
    scene.at(tw - 6, () => {
      l3.state(LINE.strike);
      for (const s of spots) {
        const col = scene.spawn("dw_column", s, { kind: w === 0 ? 0 : 2, size: 1.5, state: 1 });
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      }
      sound(dim, "dw6_strike", l3Lo, 1.3, 1.1 + w * 0.15);
    });
    scene.at(tw, () => {
      const hit = /* @__PURE__ */ new Set();
      warns.forEach((x) => {
        x.state(3);
        scene.after(8, () => scene.despawn(x));
      });
      for (const s of spots) {
        particle(dim, "dw_ring", up(s, 0.2));
        particle(dim, "dw_pillar_burst", up(s, 0.3));
        for (const e of hostiles(dim, s, DW06.latticeRadius, caster)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, DW06.latticeDamage, caster);
          knockback(e, s, 0.8, 0.5);
        }
      }
    });
  });
  scene.at(L3.desc + 66, () => l3.state(LINE.unwrite));
  scene.at(L3.desc + 86, () => scene.despawn(l3));
  const L4 = { form: tRise2 + 40, desc: L3.desc + 62 };
  let l4 = new Actor(void 0, "");
  const l4Hi = P5(0, 0, 23), l4Lo = up(center, 1.4);
  let spiralWarn;
  scene.at(L4.form, () => {
    l4 = spawnLine(3, l4Hi, 1.8);
  });
  scene.at(L4.desc - 20, () => {
    spiralWarn = scene.spawn("telegraph", center, { kind: 0, size: 15, state: 1 });
  });
  scene.at(L4.desc, () => descend(l4, l4Hi, l4Lo, L4.desc, L4.desc + 16));
  scene.at(L4.desc + 16, () => {
    l4.state(LINE.strike);
    sound(dim, "dw6_strike", center, 1.2, 0.75);
  });
  scene.span(L4.desc + 16, L4.desc + 56, (p, el) => {
    const rad = 15 * (1 - p) + 1;
    l4.size(rad / 8.6);
    if (el % 5 === 0) {
      ring(dim, "dw6_stream", up(center, 0.8), rad, 8, el * 21);
      for (const e of hostiles(dim, center, rad + 1, caster)) {
        shove(e, sub(center, e.location), DW06.spiralPull, 0.1);
        if (el % 10 === 0) damage(e, DW06.spiralTickDamage, caster);
      }
    }
  });
  scene.at(L4.desc + 56, () => {
    l4.state(LINE.strike);
    spiralWarn?.state(3);
    particle(dim, "dw6_flare", up(center, 1.5));
    particle(dim, "dw6_quake", up(center, 0.3));
    for (const e of hostiles(dim, center, 3.5, caster)) damage(e, DW06.spiralFinalDamage, caster);
  });
  scene.at(L4.desc + 64, () => {
    if (spiralWarn) scene.despawn(spiralWarn);
    l4.state(LINE.unwrite);
  });
  scene.at(L4.desc + 84, () => scene.despawn(l4));
  const tFinal = L4.desc + 76;
  let form = new Actor(void 0, "");
  let formHi = up(finalAt, 26);
  scene.at(tRise2 + 60, () => {
    formHi = up(finalAt, 26);
    form = spawnLine(4, formHi, 1);
    sound(dim, "dw6_form", formHi, 1.6, 0.7);
  });
  scene.at(tFinal - 40, () => {
    if (!finalWarn?.valid) finalWarn = scene.spawn("telegraph", finalAt, { kind: 0, size: DW06.finalRadius, state: 4 });
    else finalWarn.state(1);
  });
  scene.at(tFinal - 24, () => {
    const from = formHi, to = up(finalAt, 1.2);
    descend(form, from, to, tFinal - 24, tFinal);
    sound(dim, "dw6_finale", finalAt, 2);
  });
  scene.every(3, () => ring(dim, "dw6_ink", up(finalAt, 0.4), DW06.finalRadius, 6, scene.tick * 9), tFinal - 24, tFinal);
  scene.at(tFinal, () => {
    form.state(LINE.strike);
    finalWarn?.state(3);
    for (const w of judgedWarn) w.state(3);
    particle(dim, "dw6_flare", up(finalAt, 2));
    particle(dim, "dw6_quake", up(finalAt, 0.3));
    particle(dim, "fx_shock", up(finalAt, 0.4));
    burst(dim, "dw6_rays", up(finalAt, 0.5), DW06.finalRadius * 0.6, 6);
    ring(dim, "dw6_dust", up(finalAt, 0.4), DW06.finalRadius * 0.7, 8);
    for (const e of hostiles(dim, finalAt, DW06.finalRadius, caster)) {
      damage(e, DW06.finalDamage + (judged.has(e.id) ? DW06.judgedBonus : 0), caster);
      knockback(e, finalAt, DW06.finalKnockback, 0.7);
    }
    for (const m of marks.values()) {
      m.a.state(3);
      const a = m.a;
      scene.after(8, () => scene.despawn(a));
    }
  });
  scene.at(tFinal + 10, () => {
    if (finalWarn) scene.despawn(finalWarn);
    judgedWarn.forEach((w) => scene.despawn(w));
  });
  scene.at(tFinal + 26, () => {
    form.state(LINE.unwrite);
    burst(dim, "dw6_letters", up(finalAt, 3), 5, 8);
  });
  scene.at(tFinal + 46, () => scene.despawn(form));
  const tPhase5 = tFinal + 20;
  scene.at(tPhase5, () => {
    refugeOn = false;
    refuge?.state(DOME.fade);
    for (const w of walls) if (w.valid) w.state(WALL.sink);
    tb.clearAll();
    tb.place(up(bookAt, 1), LIGHT);
    sound(dim, "dw6_unwrite", center, 1.4);
  });
  scene.at(tPhase5 + 20, () => {
    if (refuge) scene.despawn(refuge);
    walls.forEach((w) => scene.despawn(w));
  });
  scene.at(tPhase5 + 2, () => {
    edifices.forEach((ed, j) => {
      scene.after(j * 4, () => ed.a.state(ED.unwrite));
      scene.after(j * 4 + 40, () => scene.despawn(ed.a));
      const from = up(ed.at, 4), mid = up(lerp(ed.at, bookAt, 0.5), 9);
      scene.span(scene.tick + j * 4 + 14, scene.tick + j * 4 + 44, (p) => {
        particle(dim, "dw6_stream", bezier(from, mid, up(bookAt, 1), p));
      });
    });
  });
  scene.at(tPhase5 + 6, () => tablets.forEach((t) => t.state(TAB.ret)));
  scene.span(tPhase5 + 6, tPhase5 + 34, (p) => {
    tablets.forEach((t, k2) => {
      const from = up(stations[k2], 10);
      const to = pagePt(ruleA(k2), 44, 0.3);
      t.move(bezier(from, up(lerp(from, to, 0.5), 5), to, p * p * (3 - 2 * p)), pageYaw);
    });
  });
  const tReform = tPhase5 + 32;
  scene.at(tReform, () => {
    page = scene.spawn("dw6_page", pageO, { yaw: pageYaw, state: PAGE.reform });
    sound(dim, "dw6_page", pagePt(0, 44), 0.9, 1.2);
  });
  scene.at(tReform + 6, () => tablets.forEach((t) => scene.despawn(t)));
  const tFold = tReform + 30;
  scene.at(tFold, () => page.state(PAGE.fold));
  [16, 36, 56, 74].forEach((d, k2) => scene.at(tFold + d, () => {
    sound(dim, "dw6_fold", page.loc, 1.2, 1 + k2 * 0.08);
    burst(dim, "dw6_ink", pagePt(-30 + k2 * 7, 44 - k2 * 9, 0.5), 2, 3);
  }));
  scene.at(tFold + 60, () => {
    book.state(BOOK.gather).skin(0);
    burst(dim, "dw6_letters", up(bookAt, 1.5), 1.5, 4);
  });
  scene.at(tPhase5 + 40, () => boundary.state(BOUND.unwrite));
  scene.at(tPhase5 + 70, () => scene.despawn(boundary));
  const tSlide = tFold + 100;
  scene.span(tSlide, tSlide + 20, (p) => page.move(lerp(pageO, up(bookAt, 0.8), p * p * (3 - 2 * p)), pageYaw));
  scene.at(tSlide + 20, () => {
    page.state(PAGE.slip);
    particle(dim, "dw6_flare", up(bookAt, 1));
  });
  scene.at(tSlide + 36, () => scene.despawn(page));
  scene.at(tSlide + 30, () => {
    book.state(BOOK.close);
    sound(dim, "dw6_close", bookAt, 1.1);
  });
  scene.at(tSlide + 40, () => sound(dim, "dw6_amen", bookAt, 1.2));
  scene.at(tSlide + 76, () => {
    burst(dim, "dw6_letters", up(bookAt, 1), 1.2, 6);
    particle(dim, "dw6_bell", up(bookAt, 1));
  });
  scene.at(tSlide + 80, () => scene.despawn(book));
  scene.endAt(tSlide + secs(4.3));
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
var MARK2 = { hidden: 0, appear: 1, hold: 2, flare: 3, vanish: 4 };
var T2 = {
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
  const N2 = 96;
  const P5 = [];
  const S6 = [];
  for (let i = 0; i <= N2; i++) {
    P5.push(spline(ctrl, i / N2));
    S6.push(i ? S6[i - 1] + dist(P5[i], P5[i - 1]) : 0);
  }
  const L3 = S6[N2];
  function road(s) {
    const x = clamp(s, 0, L3);
    let i = 1;
    while (i < N2 && S6[i] < x) i++;
    const f = (x - S6[i - 1]) / Math.max(1e-6, S6[i] - S6[i - 1]);
    return { p: lerp(P5[i - 1], P5[i], f), d: norm(sub(P5[i], P5[i - 1])) };
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
  const birdDone = arrive[2] + DN01.birdSwoops * T2.birdSwoop + 1;
  const dollLast = arrive[3] + 1 + DN01.dollDrift + DN01.dollPulses[DN01.dollPulses.length - 1] + 10;
  const stagDone = arrive[1] + DN01.stagBounds * T2.stagLeap + 2;
  const horseDone = arrive[0] + horseRun + 2;
  const tRoll = Math.max(birdDone, dollLast, stagDone, horseDone) + 4;
  const tEnd = tRoll + (n - 1) * DN01.unrollStep + T2.roadAnim + 8;
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
      scene.after(T2.roadAnim, () => a.state(ROAD.hold));
    });
  }
  let apexI = 0;
  for (let i = 0; i <= N2; i++) if (P5[i].y > P5[apexI].y) apexI = i;
  const moonAt = add(up(P5[apexI], DN01.moonAbove), mul(side, -1.5));
  let moon;
  scene.at(4, () => {
    moon = scene.spawn("dn_parade_moon", moonAt, { yaw: yawOf(sub(base, moonAt)), state: MOON.rise });
    sound(dim, "dn_parade_moon", moonAt, 1);
    burst(dim, "dn_parade_trail", moonAt, 3, 8);
  });
  scene.at(4 + T2.moonRise, () => moon?.state(MOON.sleep));
  scene.at(8, () => sound(dim, "dn_parade_theme", P5[apexI], 1.1));
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
      const mk = scene.spawn("dn_parade_mark", up(at, DN01.markHeight), { state: MARK2.appear, skin: count - 1 });
      h.mark = mk;
      scene.follow(mk, e, DN01.markHeight);
      scene.after(T2.markAppear, () => mk.state(MARK2.hold));
    } else {
      const mk = h.mark;
      mk.skin(count - 1).state(MARK2.flare);
      scene.after(T2.markFlare, () => mk.state(MARK2.hold));
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
    scene.at(t0 + horseRun + 2 + T2.horseDepart, () => scene.despawn(h));
  }
  function stagBounds(st2) {
    const t0 = scene.tick;
    const struck = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < DN01.stagBounds; k2++) {
      const tk = t0 + k2 * T2.stagLeap;
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
        }, tk + 1, tk + T2.stagLaunch);
        let a0 = from;
        let hop = DN01.stagHop;
        scene.at(tk + T2.stagLaunch, () => {
          a0 = st2.loc;
          hop = DN01.stagHop + DN01.stagHopPerBlock * distXZ(a0, land);
          sound(dim, "dn_parade_step", a0, 0.8, 1.1);
        });
        scene.span(tk + T2.stagLaunch, tk + T2.stagLand + 1, (p, e) => {
          const q = lerp(a0, land, p);
          st2.move(up(q, hop * 4 * p * (1 - p)), yawOf(flat(sub(land, a0))));
          if (e % 3 === 1) particle(dim, "dn_parade_mistpuff", up(q, hop * 4 * p * (1 - p) + 1.5));
        });
        scene.at(tk + T2.stagLand, () => {
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
    const tDep = t0 + DN01.stagBounds * T2.stagLeap + 2;
    scene.at(tDep, () => {
      st2.state(STAG.depart);
      sound(dim, "dn_parade_depart", st2.loc, 0.9, 0.95);
      burst(dim, "dn_parade_mistpuff", up(st2.loc, 2), 1.2, 4);
    });
    scene.at(tDep + T2.stagDepart, () => scene.despawn(st2));
  }
  function birdSwoops(b) {
    const t0 = scene.tick;
    const everHit = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < DN01.birdSwoops; k2++) {
      const tk = t0 + k2 * T2.birdSwoop;
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
        scene.span(tk + 1, tk + T2.birdSwoop + 1, (p, e) => {
          const pos = spline(path, p);
          const d = sub(pos, prev);
          prev = pos;
          b.move(pos, yawOf(d.x * d.x + d.z * d.z > 1e-6 ? d : away));
          setTilt(b, pitch(d) * 0.6);
          if (e % 4 === 0) particle(dim, "dn_parade_trail", pos);
          if (e < T2.birdLowFrom - 2 || e > T2.birdLowTo + 2) return;
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
    const tDep = t0 + DN01.birdSwoops * T2.birdSwoop + 1;
    scene.at(tDep, () => {
      b.state(BIRD.depart);
      setTilt(b, 0);
      sound(dim, "dn_parade_depart", b.loc, 0.9, 1.25);
    });
    scene.at(tDep + T2.birdDepart, () => scene.despawn(b));
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
      scene.at(tp + off + T2.dollPulsePeak, () => {
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
    scene.at(last + T2.dollDepart, () => scene.despawn(dl));
  }
  scene.at(tRoll, () => {
    sound(dim, "dn_parade_rollup", P5[apexI], 1.1);
    for (const h of hits.values()) {
      const mk = h.mark;
      if (mk && mk.valid) {
        mk.state(MARK2.vanish);
        scene.after(T2.markVanish, () => scene.despawn(mk));
      }
    }
    moon?.state(MOON.set);
    scene.after(T2.moonSet, () => {
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
      scene.after(T2.roadAnim, () => scene.despawn(a));
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
var T_OPEN = T_HANDLE + A2.handle;
var T_EMERGE = T_OPEN + 6;
var T_HELD = T_OPEN + A2.open;
var T_REACH = T_EMERGE + A2.emerge;
var T_GRAB = T_REACH + A2.reach;
var T_GRIP = T_GRAB + 2;
var T_PULL = T_GRAB + A2.grab;
var T_WITHDRAW = T_PULL + A2.pull;
var T_SLAM = T_WITHDRAW + 5;
var T_IMPACT = T_SLAM + A2.slamShut;
var T_GUEST_GONE = T_IMPACT + 8;
var T_VANISH = T_IMPACT + 24;
var T_END = T_VANISH + A2.vanish + 4;
var dn02_nightmare_intrusion_default = defineSpell("dn02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center, target } = focus(caster, aim, DN02.snapRadius);
  const victim = target && isAlive(target) ? target : void 0;
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
    if (victim) effect(victim, "slowness", T_REACH - T_HANDLE, DN02.dreadSlowAmp);
  });
  scene.at(T_HANDLE + 4, () => particle(dim, "dn_guest_mote", keyhole));
  scene.at(T_HANDLE + 22, () => particle(dim, "dn_guest_cracklight", L3(-14, 32, -2)));
  scene.at(T_OPEN, () => {
    d.state(DOOR.open);
    sound(dim, "dn_guest_creak", door, 1.1);
    lights.place(L3(0, 40, -12), LIGHT);
    particle(dim, "dn_guest_dust", L3(0, 2, -6));
  });
  scene.at(T_OPEN + 8, () => sound(dim, "dn_guest_drone", L3(0, 30, 6), 1));
  scene.every(7, () => particle(dim, "dn_guest_lamp", L3(0, 36, -3)), T_OPEN + 10, T_SLAM);
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
  scene.at(T_REACH, () => {
    guest?.state(GUEST.reach);
    sound(dim, "dn_guest_voice", L3(0, 74, -30), 1.1, 0.9);
    if (victim && isAlive(victim)) effect(victim, "slowness", A2.reach + 4, DN02.reachSlowAmp);
  });
  scene.at(T_REACH + 10, () => sound(dim, "dn_guest_clicks", L3(0, 50, -30), 1, 1.2));
  let caught = false;
  let release2;
  scene.at(T_GRAB, () => {
    caught = !!victim && isAlive(victim) && distXZ(victim.location, gripAt) <= DN02.grabRange;
    guest?.state(caught ? GUEST.grab : GUEST.miss);
    if (!caught) {
      sound(dim, "dn_guest_voice", L3(0, 60, -40), 0.9, 1.15);
      scene.after(4, () => particle(dim, "dn_guest_breath", L3(0, 24, -56)));
    }
  });
  scene.at(T_GRIP, () => {
    if (!caught || !victim || !isAlive(victim)) {
      caught = false;
      return;
    }
    const v2 = victim;
    const anchor = { x: gripAt.x, y: v2.location.y, z: gripAt.z };
    const end = { x: dragEnd.x, y: v2.location.y, z: dragEnd.z };
    release2 = restrain(scene, v2, T_IMPACT - T_GRIP, anchor);
    scene.every(1, () => {
      if (!isAlive(v2)) return;
      const t = scene.tick;
      const p = t < T_PULL ? 0 : smooth((t - T_PULL) / (A2.pull - 1));
      drag(v2, lerp(anchor, end, p));
      if (t >= T_PULL && t < T_WITHDRAW && (t - T_PULL) % 3 === 0) particle(dim, "dn_guest_drag", v2.location);
    }, T_GRIP, T_IMPACT);
    sound(dim, "dn_guest_grab", v2.location, 1.1);
    particle(dim, "dn_guest_grip", up(v2.location, 1));
    particle(dim, "dn_guest_squeeze", up(v2.location, 1));
    scene.every(DN02.squeezeEvery, () => {
      if (!isAlive(v2)) return;
      damage(v2, DN02.squeezeDamage, caster);
      particle(dim, "dn_guest_squeeze", up(v2.location, 1.1));
    }, T_GRIP + 4, T_IMPACT);
  });
  scene.at(T_PULL, () => {
    guest?.state(GUEST.pull);
    sound(dim, "dn_guest_drag", caught && victim ? victim.location : gripAt, 1);
  });
  scene.at(T_WITHDRAW, () => {
    guest?.state(GUEST.withdraw);
    sound(dim, "dn_guest_clicks", L3(0, 40, -6), 1, 1.35);
  });
  scene.at(T_SLAM, () => {
    d.state(DOOR.slam);
    sound(dim, "dn_guest_slam", L3(0, 40, -2), 1.8);
  });
  scene.at(T_IMPACT, () => {
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
      const held = caught && victim !== void 0 && e.id === victim.id;
      damage(e, DN02.slamDamage + (held ? DN02.finisherBonus : 0), caster);
      knockback(e, door, DN02.slamKnock, DN02.slamLift);
    }
  });
  scene.at(T_GUEST_GONE, () => {
    if (guest) scene.despawn(guest);
  });
  scene.at(T_IMPACT + 6, () => particle(dim, "dn_guest_dust", L3(0, 2, -4)));
  scene.at(T_IMPACT + 12, () => particle(dim, "dn_guest_cracklight", L3(0, 40, -2)));
  scene.at(T_VANISH, () => {
    d.state(DOOR.vanish);
    sound(dim, "dn_guest_hush", keyhole, 1);
  });
  scene.at(T_VANISH + 8, () => particle(dim, "dn_guest_keyhole", keyhole));
  scene.at(T_VANISH + 17, () => particle(dim, "fx_flash", keyhole));
  scene.at(T_VANISH + A2.vanish, () => scene.despawn(d));
  scene.endAt(T_END);
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
  const N2 = DN03.gridCells, CS = DN03.cellSize, HALF = N2 * CS / 2, GAP = CS / 2, H = DN03.wallBlocks;
  const tb = blocksFor(scene);
  const { center } = focus(caster, aim, 12);
  let away = norm(flat(sub(center, caster.location)));
  if (distXZ(center, caster.location) < 0.5) away = aim.forward;
  const d0 = distXZ(center, caster.location);
  const shift = clamp(HALF + DN03.casterMargin - d0, 0, DN03.maxGridShift);
  const gc = groundBelow(dim, up(add(center, mul(away, shift)), 4), 16);
  const gy = gc.y;
  const X0 = Math.floor(gc.x) - HALF, Z0 = Math.floor(gc.z) - HALF;
  const mid = (gx, gz) => ({ x: X0 + gx * CS + GAP + 0.5, y: gy, z: Z0 + gz * CS + GAP + 0.5 });
  const gridMid = mid(N2 / 2 - 0.5, N2 / 2 - 0.5);
  const hover = up(gridMid, DN03.hoverHeight);
  const inside = (c) => c[0] >= 0 && c[0] < N2 && c[1] >= 0 && c[1] < N2;
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
  for (let i = 0; i < N2; i++) for (let j = 0; j <= N2; j++) ALL.push({ o: 0, i, j });
  for (let i = 0; i <= N2; i++) for (let j = 0; j < N2; j++) ALL.push({ o: 1, i, j });
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
    const d = farPos ? N2 - 1 - dep : dep;
    return alongZ ? [lat, d] : [d, lat];
  };
  const farEdge = (lat, dep) => {
    const g = farPos ? N2 - dep : dep;
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
    tb.column(x, y, z, H);
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
      tb.removeColumn(x, baseY(k2) ?? gy, z, H);
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
    const lat = clamp(Math.floor(N2 / 2) - 1 + round % 2, 0, N2 - 1);
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
      for (let k2 = 0; k2 < N2; k2++) {
        const per = [[[k2, 0], { o: 0, i: k2, j: 0 }], [[k2, N2 - 1], { o: 0, i: k2, j: N2 }], [[0, k2], { o: 1, i: 0, j: k2 }], [[N2 - 1, k2], { o: 1, i: N2, j: k2 }]];
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
      if (seen.size >= N2 * N2) return;
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
  const T7 = {
    open: secs(L.land),
    opened: secs(L.land + L.open),
    unfold: secs(L.land + L.open) + 4,
    wallsOut: secs(L.land + L.open) + 8,
    active: secs(L.land + L.open) + 24
  };
  T7.active = Math.max(T7.active, T7.wallsOut + Math.ceil(DN03.wallCount / 2) + 18);
  const tFold = T7.active + DN03.activeTicks;
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
  scene.at(T7.open, () => {
    house.state(HS.open);
    sound(dim, "dn_house_windup", gc, 1);
    sound(dim, "dn_house_open", gc, 1);
  });
  scene.at(T7.open + 18, () => burst(dim, "dn_house_key", up(gc, 5), 3, 8));
  scene.at(T7.opened, () => house.state(HS.opened));
  scene.at(T7.unfold, () => {
    house.state(HS.unfold);
    sound(dim, "dn_house_unfold", gc, 1.2);
    burst(dim, "dn_house_scrap", up(gc, 5), 3, 6);
  });
  scene.at(T7.unfold + secs(L.unfold), () => house.state(HS.spread));
  scene.span(T7.unfold, T7.unfold + 24, (p) => {
    housePos = lerp(gc, hover, smooth(p));
    house.move(housePos);
  });
  const first = plan(0);
  assignDoors(first.walls, first.loopKey);
  let loopKey = first.loopKey;
  let loopStart = first.start;
  const walls = [];
  [...first.walls.values()].forEach((t, k2) => {
    const at = T7.wallsOut + Math.floor(k2 / 2);
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
    for (let k2 = 0; k2 < N2 * N2; k2++) {
      const h = Math.floor(hash01(round * 31 + k2, "furn") * N2 * N2);
      pattern.push([h % N2, Math.floor(h / N2)]);
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
    const at = T7.wallsOut + 10 + k2 * 3;
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
  for (let t = T7.active + DN03.shiftEvery; t < tFold - 10; t += DN03.shiftEvery) shiftTicks.push(t);
  scene.at(T7.active, () => {
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
  }, T7.active, tFold);
  for (let t = T7.active, k2 = 0; t < tFold; k2++) {
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
  }, T7.active, tFold);
  scene.every(DN03.retryEvery, () => {
    for (const k2 of [...pending]) if (refs.has(k2)) tryPlace(k2);
    else pending.delete(k2);
  }, T7.wallsOut, tFold);
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
var T3 = { hidden: 0, unfurl: 1, lullaby: 2, dissonance: 3, dual: 4, scream: 5, unravel: 6 };
var R = { hidden: 0, travel: 1, wrap: 2, orbit: 3, recoil: 4, unwind: 5 };
var W = { hidden: 0, scream: 1, faint: 2, fade: 3 };
var L2 = { unfurl: 30, dissonance: 32, scream: 18, unravel: 36, wrap: 16, recoil: 12, unwind: 20, fade: 7 };
var dn04_lullaby_and_scream_default = defineSpell("dn04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  let facing = norm(flat(aim.forward));
  const hoverTarget = () => up(add(caster.location, mul(facing, DN04.hoverForward)), DN04.hoverHeight);
  const bookAt = () => up(add(caster.location, mul(facing, 0.6)), 1.1);
  const P5 = DN04.phraseTicks;
  const tLull = L2.unfurl;
  const phrases = Math.max(DN04.lullabyPhrases + DN04.dissonancePhrases + 1, Math.floor((secs(DN04.activeSeconds) - tLull) / P5));
  const tDis = tLull + DN04.lullabyPhrases * P5;
  const tDual = tDis + DN04.dissonancePhrases * P5;
  const tUnravel = tLull + phrases * P5;
  const tEnd = tUnravel + L2.unravel + 4;
  const book0 = bookAt();
  let hover = book0;
  const tap = scene.spawn("dn_lull_tapestry", book0, { yaw: yawOf(mul(facing, -1)), state: T3.unfurl, skin: 0 });
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
    const t0 = tLull + k2 * P5;
    const kind = k2 < DN04.lullabyPhrases ? "lull" : k2 < DN04.lullabyPhrases + DN04.dissonancePhrases ? "dis" : "dual";
    scene.at(t0, () => sound(dim, `dn_lull_${kind}${k2 % 2 + 1}`, hover, 1));
    if (kind === "dual") {
      scene.at(t0, () => {
        tap.state(T3.scream);
        sound(dim, "dn_lull_scream", hover, 1.2);
        burst(dim, "dn_lull_thread", up(hover, 2.2), 1.2, 3);
      });
      scene.at(t0 + DN04.screamLead, () => launchWave(false));
      scene.at(t0 + L2.scream, () => tap.state(T3.dual));
    }
  }
  scene.at(tLull, () => tap.state(T3.lullaby));
  scene.every(10, () => particle(dim, "dn_lull_note", up(hover, 2.4)), tLull, tDual);
  let tele;
  scene.at(tDis, () => {
    tap.state(T3.dissonance);
    sound(dim, "dn_lull_tear", hover, 1.1);
    tele = scene.spawn("telegraph", groundBelow(dim, hover), { kind: 1, size: DN04.waveRadius, state: 4 });
  });
  scene.at(tDis + 6, () => tap.skin(1));
  scene.at(tDis + P5 / 2, () => {
    sound(dim, "dn_lull_faint", hover, 0.9);
    launchWave(true);
  });
  scene.at(tDis + L2.dissonance, () => {
    tap.state(T3.dual);
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
    tap.state(T3.unravel);
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
var T4 = {
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
  let t0 = scene.tick + T4.doorArrive;
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
      scene.at(hitAt - T4.doorSlam, () => {
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
  scene.at(Math.min(until, t0 + 6 + DN05.doorPasses * (passLen + 10)), () => finish(c, door, DOOR2.depart, T4.doorDepart));
}
function windowEye(c, i, until) {
  const { scene, dim } = c;
  let pos = c.sky(i + 2);
  const win = scene.spawn("dn_city_window", pos, { state: WIN.arrive });
  c.hunters.add(win);
  sound(dim, "dn_city_groan", pos, 0.7, 1.3);
  let t = scene.tick + T4.winArrive;
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
    const cycle = 16 + T4.winBlink + T4.winStare;
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
      scene.at(t1 + 16 + T4.winBlink, () => {
        win.state(WIN.stare);
        sound(dim, "dn_city_stare", pos, 1);
      });
      scene.at(t1 + 16 + T4.winBlink + T4.winFire, () => {
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
    scene.at(tEnd + 16 + T4.winShatter, () => {
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
  scene.at(t0 + T4.corUnfold, () => {
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
  scene.at(t0 + T4.corUnfold + 8, () => scene.despawn(warn));
  scene.at(t0 + T4.corUnfold + T4.corSnap, () => cor.state(COR.clamp));
  scene.at(t0 + T4.corUnfold + DN05.corridorHold, () => {
    sound(dim, "dn_city_groan", end, 0.6, 1.4);
    finish(c, cor, COR.fold, T4.corFold);
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
    scene.at(t0 + T4.sfFirst + k2 * T4.sfStep, () => {
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
    scene.at(t0 + T4.sfFirst + k2 * T4.sfStep + 8, () => scene.despawn(warns[k2]));
  });
  const tRest = t0 + T4.sfFirst + SF_CHUNKS * T4.sfStep;
  scene.at(tRest, () => sf?.state(SF.rest));
  scene.at(tRest + 16, () => {
    if (sf) finish(c, sf, SF.sink, T4.sfSink);
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
      scene.after(T4.frBiteHit, () => {
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
    scene.after(T4.frHop, () => fr.state(FR.idle));
  }, scene.tick + T4.frArrive, until);
  scene.at(until, () => {
    sound(dim, "dn_city_bite", pos, 0.6, 0.7);
    finish(c, fr, FR.crumble, T4.frCrumble);
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
  scene.at(t0 + DN05.balconyWarn + T4.balHit, () => scene.despawn(bal));
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
  scene.at(t0 + 8 + T4.stAppear, () => {
    st2?.state(STREET.roll);
    warn.state(3);
    sound(dim, "dn_city_street", a, 1.1);
  });
  scene.at(t0 + 8 + T4.stAppear + 8, () => scene.despawn(warn));
  scene.span(t0 + 8 + T4.stAppear, t0 + 8 + T4.stAppear + rollTicks, (q) => {
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
  scene.at(t0 + 8 + T4.stAppear + rollTicks, () => {
    if (!st2) return;
    st2.state(STREET.crumble);
    particle(dim, "dn_city_dust", b);
    const s = st2;
    scene.after(T4.stCrumble, () => scene.despawn(s));
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
  const H = DN05.cityHeight;
  const spirePos = up(center, H);
  const qAngles = [45, 135, 225, 315];
  const qPos = qAngles.map((a, k2) => polar(center, DN05.quarterDistance, a, H + DN05.quarterLift[k2]));
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
      const size = (H - 2) / 12;
      const unit = 2 * size / 16;
      const foot = groundBelow(dim, add(ally.location, mul(away, -PAVILION_UNITS * unit)));
      const pav = add(foot, mul(away, PAVILION_UNITS * unit));
      scene.after(k2 * 6, () => {
        const st2 = scene.spawn("dn_city_stair", foot, { state: STAIR.descend, size, yaw: yawOf(away) });
        sound(dim, "dn_city_stair", up(foot, 6), 1.1, 1 + k2 * 0.06);
        scene.after(T4.stairDown, () => {
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
        scene.at(P3 - 26 + T4.stairUp, () => scene.despawn(st2));
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
  /** How far beyond the focus point the bed floats, and its height (mattress top) above the ground. */
  bedBack: 20,
  bedHeight: 18,
  /** Where the risen Dreamer hovers (beyond the focus) and its pelvis height above the ground. */
  hoverBack: 12,
  hoverHeight: 12.5,
  /** Largest head/body turn (deg) the Dreamer makes toward the main enemy group for the finale. */
  finaleTurn: 35,
  // ---- Phase II: giant-body attacks
  /** Dropped pillow: damage, blast radius and knockback. */
  pillowDamage: 10,
  pillowRadius: 3.5,
  pillowKnock: 1.4,
  /** Hand sweep: damage, reach of the hand around its path, sideways knockback. */
  sweepDamage: 14,
  sweepRadius: 3.2,
  sweepKnock: 2.2,
  /** Spilled stairs: damage per enemy, width of the cascade. */
  stairsDamage: 9,
  stairsRadius: 2.2,
  // ---- Phase III: zones (all zones have this radius)
  zoneRadius: 4.5,
  /** Dream zones: heal per pulse (every zonePulse ticks), supportive effect duration, ward strength. */
  zonePulse: 20,
  dreamHeal: 2,
  dreamEffectTicks: 50,
  /** Fraction of damage that still reaches an ally standing in a dream zone, and the ward's total pool. */
  wardFactor: 0.55,
  wardPool: 40,
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
  wheelRadius: 3.6,
  wheelSpeed: 0.38,
  /** Window shards released by the arcade forearms: count and damage. */
  shards: 6,
  shardDamage: 10,
  /** Spiral-stair drill: impact damage/radius, damage per boring pulse, slowness ticks. */
  drillDamage: 18,
  drillRadius: 4,
  drillTick: 4,
  /** Bed pendulum: damage and hit radius around the bed while it sweeps low. */
  pendulumDamage: 20,
  pendulumRadius: 6,
  pendulumLength: 14,
  /** Expanding room-cubes fired from the chest: count, damage, hold ticks, capture radius. */
  rooms: 3,
  roomDamage: 14,
  roomHold: 24,
  roomRadius: 3,
  /** Face-door finale: pull radius, pull speed (blocks/tick), beam damage every 10 ticks, final strike. */
  beamRadius: 9,
  beamPull: 0.2,
  beamDamage: 3,
  finalDamage: 32,
  finalRadius: 7,
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
var BED = { arrive: 1, float: 2, occupied: 3, dip: 4, empty: 5, fold: 6, swing: 7, vanish: 8 };
var CODEX = { open: 1, hold: 2, gather: 3, close: 4 };
var ZONE = { bloom: 1, idle: 2, fold: 3, fade: 4, bite: 5 };
var TG = { warn: 1, hold: 2, flash: 3, warnSlow: 4 };
var LEN = {
  manifest: 90,
  sit: 60,
  awaken: 30,
  rise: 60,
  sweep: 60,
  cabinet: 40,
  raise: 40,
  fireArms: 32,
  fireRooms: 32,
  finale: 60,
  slam: 20,
  forget: 100
};
var LIE = { fwd: 1.67, up: 1 };
var SWEEP_PATH = [
  [11.88, -11.35, 11.29],
  [8.8, -12.59, 12.67],
  [2.43, -13.84, 14.05],
  [-4.19, -13.67, 13.78],
  [-7.61, -12.98, 12.95]
];
var SWEEP_HIT = [25, 40];
var CHEST = { up: 7.8, fwd: 5.1 };
var ARM = { right: 4.2, up: 5.9, fwd: 17.2 };
var BEAM_LAND = 11.84;
var BED_PILLOW = { right: 2.75, fwd: -6.5, up: 0.75 };
var BOOK2 = { right: -0.94, up: 1.5, fwd: 0.81 };
var SWING_T = 48;
var SWING_A = 58;
var STEP_LAND = (k2) => 8 + Math.round(k2 * 2.4);
var dn06_the_dreamer_default = defineSpell("dn06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 14);
  const fwd = norm({ x: aim.forward.x, y: 0, z: aim.forward.z });
  const g0 = center.y;
  const lights = blocksFor(scene);
  const faceYaw = yawOf(mul(fwd, -1));
  const at = (base, yaw, r, u, f) => {
    const fd = fromYaw(yaw), rt = right(fd);
    return { x: base.x + rt.x * r + fd.x * f, y: base.y + u, z: base.z + rt.z * r + fd.z * f };
  };
  const ground = (p) => groundBelow(dim, { x: p.x, y: Math.max(p.y, g0 + 4), z: p.z }, 50);
  const marks = /* @__PURE__ */ new Map();
  function markNew(limit = DN06.maxMarks) {
    for (const e of hostiles(dim, center, DN06.radius, caster)) {
      if (marks.size >= limit) break;
      if (marks.has(e.id)) continue;
      const a = scene.spawn("dn_dreamer_mark", up(e.location, 2.5), { state: 1 });
      scene.follow(a, e, 2.5);
      scene.after(10, () => a.state(2));
      marks.set(e.id, { e, a });
      sound(dim, "dn_dreamer_mark", e.location, 0.6, 0.9 + marks.size * 0.06);
      particle(dim, "dn_dreamer_moon", up(e.location, 2.5));
      return;
    }
  }
  function marked() {
    const out = [];
    for (const m of marks.values()) if (isAlive(m.e) && distXZ(m.e.location, center) < DN06.radius + 6) out.push(m.e);
    if (out.length) return out;
    return hostiles(dim, center, DN06.radius, caster);
  }
  function targets(n, spread = 7) {
    const es = marked();
    const out = [];
    for (let i = 0; i < n; i++) {
      if (es.length) {
        const e = es[i % es.length];
        out.push({ loc: groundBelow(dim, e.location), e });
      } else out.push({ loc: ground(polar(center, i === 0 ? 0 : spread, i * (360 / Math.max(1, n - 1)) + 20)) });
    }
    return out;
  }
  function groups(n) {
    const es = marked();
    const out = [];
    for (const e of es) {
      if (out.length >= n) break;
      if (out.every((c) => distXZ(c, e.location) > DN06.zoneRadius * 1.5)) out.push(groundBelow(dim, e.location));
    }
    const base = out.length ? out[0] : center;
    for (let i = out.length; i < n; i++) out.push(ground(polar(base, 7, i * 120 + yawOf(fwd))));
    return out;
  }
  function centroid() {
    const es = marked();
    if (!es.length) return center;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return groundBelow(dim, mul(s, 1 / es.length));
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
  const domain = scene.spawn("dn_dreamer_domain", up(center, 0.05), { size: DN06.radius / 2, state: 1 });
  scene.at(32, () => domain.state(2));
  lights.place(up(center, 2), LIGHT);
  const codex = scene.spawn("dn_dreamer_codex", caster.location, { yaw: aim.yaw, state: CODEX.open });
  scene.follow(codex, caster, 0);
  scene.at(60, () => codex.state(CODEX.hold));
  sound(dim, "dn_dreamer_book", caster.location, 0.9);
  sound(dim, "dn_dreamer_musicbox", caster.location, 0.8);
  const bedRest = up(add(center, mul(fwd, DN06.bedBack)), DN06.bedHeight);
  const bedFrom = up(add(center, mul(fwd, DN06.bedBack + 18)), DN06.bedHeight + 14);
  const bedMid = up(add(add(center, mul(fwd, DN06.bedBack + 6)), mul(right(fwd), 10)), DN06.bedHeight + 10);
  let bedPos = { ...bedFrom };
  const bed = scene.spawn("dn_dreamer_bed", bedFrom, { yaw: faceYaw, state: BED.arrive });
  sound(dim, "dn_dreamer_bed", bedFrom, 1);
  scene.span(0, 50, (p) => {
    bedPos = bezier(bedFrom, bedMid, bedRest, smooth(p));
    bed.move(bedPos, faceYaw);
  });
  scene.at(50, () => bed.state(BED.float));
  scene.every(8, () => markNew(), 40, 140);
  scene.every(6, (e) => {
    particle(dim, "dn_dreamer_mote", up(polar(center, 6 + e % 4 * 3, e * 23), 2));
    if (e % 12 === 0) particle(dim, "dn_dreamer_petal", up(bedPos, 3));
  }, 0, 760);
  scene.at(100, () => {
    burst(dim, "dn_dreamer_star", up(bedPos, 4), 6, 6);
    sound(dim, "dn_dreamer_breath", bedPos, 0.9);
  });
  scene.every(40, () => markNew(), 150, 760);
  const T22 = 150;
  const lieAt = () => at(bedPos, faceYaw, 0, LIE.up, LIE.fwd);
  let dreamer = new Actor(void 0, "grimoire:dreamer");
  let dPos = lieAt();
  let dYaw = faceYaw;
  scene.at(T22, () => {
    dPos = lieAt();
    dreamer = scene.spawn("dreamer", dPos, { yaw: faceYaw, state: DS2.manifest });
    bed.state(BED.occupied);
    sound(dim, "dn_dreamer_manifest", dPos, 1.2);
    sound(dim, "dn_dreamer_breath", dPos, 1, 0.8);
  });
  scene.every(15, (e) => particle(dim, "dn_dreamer_porcelain", at(bedPos, faceYaw, 0, 1.5, 6 - e / 15 * 2.2)), T22, T22 + 90);
  const T_SIT = T22 + LEN.manifest;
  scene.at(T_SIT, () => {
    dreamer.state(DS2.sit);
    bed.state(BED.dip);
    sound(dim, "dn_dreamer_groan", dPos, 1.3);
    sound(dim, "dn_dreamer_inhale", dPos, 1.1);
  });
  scene.span(T_SIT, T_SIT + 20, (p) => dreamer.move(up(lieAt(), -1.25 * smooth(p)), faceYaw));
  const pillowTarget = targets(1)[0];
  let pLand = pillowTarget.loc;
  scene.at(T_SIT + 10, () => {
    pLand = targets(1)[0].loc;
    const w = warn(pLand, DN06.pillowRadius, true, DN06.warnLong);
    const from = at(bedPos, faceYaw, BED_PILLOW.right, BED_PILLOW.up - 1.2, BED_PILLOW.fwd);
    const pil = scene.spawn("dn_dreamer_pillow", from, { yaw: faceYaw, state: 1 });
    const top = up(lerp(from, pLand, 0.35), 4);
    scene.span(scene.tick, scene.tick + DN06.warnLong, (p) => {
      const tgt = pillowTarget.e && isAlive(pillowTarget.e) && p < 0.7 ? groundBelow(dim, pillowTarget.e.location) : pLand;
      pLand = tgt;
      w.move(up(tgt, 0.05));
      pil.move(bezier(from, top, tgt, p * p));
    });
    scene.after(DN06.warnLong, () => {
      pil.state(2);
      sound(dim, "dn_dreamer_pillow", pLand, 1.2);
      burst(dim, "dn_dreamer_feather", up(pLand, 1), 2.5, 8);
      particle(dim, "dn_dreamer_dust", up(pLand, 0.3));
      particle(dim, "dn_dreamer_ring", up(pLand, 0.2));
      hitOnce(/* @__PURE__ */ new Set(), pLand, DN06.pillowRadius, DN06.pillowDamage, (e) => knockback(e, pLand, DN06.pillowKnock, 0.45));
      scene.after(14, () => pil.state(3));
      scene.after(32, () => scene.despawn(pil));
    });
  });
  const T_AWAKE = T_SIT + LEN.sit;
  scene.at(T_AWAKE, () => {
    dreamer.state(DS2.awaken);
    sound(dim, "dn_dreamer_door", dPos, 1.2);
    sound(dim, "dn_dreamer_hum", dPos, 1.2);
  });
  scene.at(T_AWAKE + 22, () => burst(dim, "dn_dreamer_star", up(dPos, 4), 2, 8));
  const T_RISE = T_AWAKE + LEN.awaken;
  const hover = up(add(center, mul(fwd, DN06.hoverBack)), DN06.hoverHeight);
  scene.at(T_RISE, () => {
    dreamer.state(DS2.rise);
    bed.state(BED.empty);
    sound(dim, "dn_dreamer_groan", dPos, 1.5, 0.85);
    sound(dim, "dn_dreamer_inhale", dPos, 1.3, 0.8);
  });
  scene.span(T_RISE + 12, T_RISE + LEN.rise, (p) => {
    const a = up(lieAt(), -1.25);
    dPos = bezier(a, up(lerp(a, hover, 0.5), 5), hover, smooth(p));
    dreamer.move(dPos, faceYaw);
    if (Math.round(p * 48) % 8 === 0) particle(dim, "dn_dreamer_porcelain", up(dPos, 6));
  });
  const T_HOV = T_RISE + LEN.rise;
  scene.at(T_HOV, () => {
    dPos = hover;
    dreamer.move(hover, faceYaw).state(DS2.hover);
  });
  const T_SWEEP = T_HOV + 10;
  const sweepPt = (i) => {
    const s = SWEEP_PATH[i];
    return at(hover, faceYaw, s[0], s[1], s[2]);
  };
  scene.at(T_SWEEP - DN06.warnLong + SWEEP_HIT[0] - 5, () => {
    for (let i = 0; i < SWEEP_PATH.length; i++) warn(ground(sweepPt(i)), DN06.sweepRadius, true, DN06.warnLong + 5 + i * 3);
  });
  scene.at(T_SWEEP, () => dreamer.state(DS2.sweep));
  scene.at(T_SWEEP + 18, () => sound(dim, "dn_dreamer_sweep", ground(sweepPt(2)), 1.5));
  const swept = /* @__PURE__ */ new Set();
  scene.span(T_SWEEP + SWEEP_HIT[0], T_SWEEP + SWEEP_HIT[1], (p) => {
    const f = p * (SWEEP_PATH.length - 1);
    const i = Math.min(Math.floor(f), SWEEP_PATH.length - 2);
    const hand = ground(lerp(sweepPt(i), sweepPt(i + 1), f - i));
    const along = norm(sub(sweepPt(i + 1), sweepPt(i)));
    particle(dim, "dn_dreamer_dust", up(hand, 0.3));
    hitOnce(swept, hand, DN06.sweepRadius, DN06.sweepDamage, (e) => shove(e, along, DN06.sweepKnock, 0.5));
  });
  scene.at(T_SWEEP + LEN.sweep, () => dreamer.state(DS2.hover));
  const T_CAB = T_SWEEP + LEN.sweep + 4;
  const stairFrom = ground(at(hover, faceYaw, 0, 0, 4));
  let stairDir = fwd;
  scene.at(T_CAB - 6, () => {
    const t = targets(1)[0].loc;
    stairDir = norm({ x: t.x - stairFrom.x, y: 0, z: t.z - stairFrom.z });
    for (let k2 = 0; k2 < 10; k2 += 3) warn(ground(add(stairFrom, mul(stairDir, 0.6 + k2 * 1.25))), DN06.stairsRadius, false, 20 + k2 * 2);
  });
  scene.at(T_CAB, () => {
    dreamer.state(DS2.cabinet);
    sound(dim, "dn_dreamer_door", up(hover, 8), 1, 0.7);
  });
  scene.at(T_CAB + 10, () => {
    line(dim, "dn_dreamer_trail", at(hover, faceYaw, 0, CHEST.up, CHEST.fwd), up(stairFrom, 4), 6);
    const st2 = scene.spawn("dn_dreamer_stairs", stairFrom, { yaw: yawOf(stairDir), state: 1 });
    sound(dim, "dn_dreamer_stairs", stairFrom, 1.2);
    const hit = /* @__PURE__ */ new Set();
    for (let k2 = 0; k2 < 10; k2++) {
      scene.after(STEP_LAND(k2), () => {
        const p = ground(add(stairFrom, mul(stairDir, 0.62 + k2 * 1.25)));
        if (k2 % 2 === 0) particle(dim, "dn_dreamer_dust", up(p, 0.2));
        hitOnce(hit, p, DN06.stairsRadius, DN06.stairsDamage, (e) => shove(e, stairDir, 0.8, 0.35));
      });
    }
    scene.after(50, () => st2.state(2));
    scene.after(72, () => scene.despawn(st2));
  });
  scene.at(T_CAB + LEN.cabinet + 8, () => dreamer.state(DS2.hover));
  const T32 = T_CAB + LEN.cabinet + 16;
  const dreamZones = [];
  const nightZones = [];
  let ward;
  scene.at(T32, () => {
    dreamer.state(DS2.raise).skin(1);
    sound(dim, "dn_dreamer_raise", up(hover, 10), 1.4);
  });
  scene.at(T32 + 25, () => {
    const fr = allies(dim, caster.location, 24, caster);
    const spots = [];
    if (fr.length > 1) for (const a of fr.slice(0, 3)) spots.push(groundBelow(dim, a.location));
    const cl = groundBelow(dim, caster.location);
    if (!spots.length) spots.push(cl);
    const cy = yawOf(fwd);
    while (spots.length < 3) spots.push(ground(polar(cl, 6, cy + 90 + (spots.length === 1 ? 10 : 160) + 90)));
    const hand = at(hover, faceYaw, -2, 26, 6);
    spots.forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_dream", loc, { kind: i, yaw: faceYaw, state: ZONE.bloom });
      dreamZones.push({ a, loc, kind: i });
      line(dim, "dn_dreamer_trail", hand, up(loc, 3), 8);
      ring(dim, "dn_dreamer_petal", up(loc, 1), DN06.zoneRadius, 6, i * 30);
      lights.place(up(loc, 2), LIGHT);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sound(dim, "dn_dreamer_bloom", cl, 1);
    ward = addWard({
      scene,
      factor: DN06.wardFactor,
      pool: DN06.wardPool,
      protects: (e) => e.typeId === "minecraft:player" && dreamZones.some((z) => distXZ(z.loc, e.location) <= DN06.zoneRadius),
      onAbsorb: (_n, _a, v2) => particle(dim, "dn_dreamer_ring", up(v2.location, 0.2))
    });
  });
  scene.at(T32 + 35, () => {
    const hand = at(hover, faceYaw, 2, 26, 6);
    groups(3).forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_night", loc, { kind: i, yaw: yawOf(sub(hover, loc)), state: ZONE.bloom });
      nightZones.push({ a, loc, kind: i });
      line(dim, "dn_dreamer_ntrail", hand, up(loc, 3), 8);
      particle(dim, "dn_dreamer_smoke", up(loc, 0.5));
      scene.after(30, () => a.state(ZONE.idle));
    });
    sound(dim, "dn_dreamer_emerge", nightZones.length ? nightZones[0].loc : center, 1.2);
  });
  scene.at(T32 + LEN.raise, () => dreamer.state(DS2.conjure));
  const ZONE_FROM = T32 + 70, ZONE_TO = T32 + 250;
  scene.every(DN06.zonePulse, (e) => {
    for (const z of dreamZones) {
      particle(dim, "dn_dreamer_heal", up(z.loc, 0.5));
      if (e / DN06.zonePulse % 2 === 0) particle(dim, "dn_dreamer_key", up(z.loc, 4));
      for (const p of allies(dim, z.loc, DN06.zoneRadius, caster)) {
        if (heal(p, DN06.dreamHeal) > 0) sound(dim, "dn_dreamer_heal", p.location, 0.5, 1 + z.kind * 0.1);
        if (z.kind === 0) effect(p, "regeneration", DN06.dreamEffectTicks, 0);
        else if (z.kind === 1) {
          effect(p, "resistance", DN06.dreamEffectTicks, 0);
          effect(p, "slow_falling", DN06.dreamEffectTicks, 0);
        } else {
          effect(p, "speed", DN06.dreamEffectTicks, 1);
          effect(p, "jump_boost", DN06.dreamEffectTicks, 0);
        }
      }
    }
    if (e / DN06.zonePulse % 2 === 0 && dreamZones.length) sound(dim, "dn_dreamer_sweet", dreamZones[0].loc, 0.7);
  }, ZONE_FROM, ZONE_TO);
  scene.every(DN06.zonePulse, (e) => {
    const big = e / DN06.zonePulse % 2 === 1;
    for (const z of nightZones) {
      particle(dim, big ? "dn_dreamer_eye" : "dn_dreamer_nring", up(z.loc, big ? 2 : 0.2));
      if (big) {
        z.a.state(ZONE.bite);
        scene.after(14, () => z.a.state(ZONE.idle));
        sound(dim, "dn_dreamer_bite", z.loc, 0.9);
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
    if (!big && nightZones.length) sound(dim, "dn_dreamer_sour", nightZones[0].loc, 0.7);
  }, ZONE_FROM + DN06.zonePulse / 2, ZONE_TO);
  const T42 = ZONE_TO + 10;
  scene.at(T42, () => {
    dreamer.state(DS2.conduct);
    domain.skin(1);
    for (const m of marks.values()) m.a.skin(1);
    sound(dim, "dn_dreamer_unreality", up(hover, 8), 1.6);
    if (ward) removeWard(ward);
    for (const z of [...dreamZones, ...nightZones]) {
      z.a.state(ZONE.fold);
      const a = z.a;
      scene.after(26, () => scene.despawn(a));
    }
    for (const z of dreamZones) lights.remove(up(z.loc, 2));
    bed.state(BED.fold);
  });
  const pivot = up(center, DN06.pendulumLength + 6.5);
  const swingAxis = right(fromYaw(faceYaw));
  const swingPos = (deg) => {
    const r = deg * Math.PI / 180;
    return add(pivot, { x: swingAxis.x * DN06.pendulumLength * Math.sin(r), y: -DN06.pendulumLength * Math.cos(r), z: swingAxis.z * DN06.pendulumLength * Math.sin(r) });
  };
  scene.span(T42, T42 + 70, (p) => {
    bedPos = lerp(bedRest, swingPos(SWING_A), smooth(p));
    bed.move(bedPos, faceYaw);
  });
  const T_WHEEL = T42 + 20;
  scene.at(T_WHEEL, () => {
    const start = nightZones.length ? nightZones[nightZones.length - 1].loc : ground(polar(center, 9, yawOf(fwd)));
    const pts = [start, ...targets(3).map((t) => t.loc)];
    const last = pts[pts.length - 1];
    pts.push(ground(add(last, mul(norm(sub(last, pts[pts.length - 2])), 6))));
    let len2 = 0;
    for (let i = 1; i < pts.length; i++) len2 += distXZ(pts[i - 1], pts[i]);
    const dur = Math.round(clamp(len2 / DN06.wheelSpeed, 40, 90));
    const w = scene.spawn("dn_dreamer_wheel", start, { yaw: yawOf(sub(pts[1], start)), state: 1 });
    for (let i = 1; i < pts.length - 1; i++) warn(pts[i], DN06.wheelRadius, false, 20 + Math.round(dur * i / pts.length));
    const hit = /* @__PURE__ */ new Set();
    scene.after(20, () => {
      w.state(2);
      sound(dim, "dn_dreamer_wheel", start, 1.4);
    });
    let prev = start;
    scene.span(scene.tick + 20, scene.tick + 20 + dur, (p) => {
      const pos = ground(spline(pts, p));
      const dir = sub(pos, prev);
      w.move(pos, Math.abs(dir.x) + Math.abs(dir.z) > 1e-3 ? yawOf(dir) : void 0);
      prev = pos;
      if (Math.round(p * dur) % 6 === 0) particle(dim, "dn_dreamer_door", up(pos, 1.5));
      hitOnce(hit, pos, DN06.wheelRadius, DN06.wheelDamage, (e) => shove(e, dir, 1.6, 0.6));
    });
    scene.after(20 + dur, () => {
      w.state(3);
      burst(dim, "dn_dreamer_door", up(prev, 3), 2.5, 6);
    });
    scene.after(40 + dur, () => scene.despawn(w));
  });
  const T_ARMS = T_WHEEL + 50;
  scene.at(T_ARMS - 6, () => {
    const ts = targets(DN06.shards, 5);
    ts.forEach((t) => warn(t.loc, 1.6, false, 25));
    scene.at(T_ARMS, () => dreamer.state(DS2.fireArms));
    scene.at(T_ARMS + 13, () => {
      sound(dim, "dn_dreamer_glass", up(hover, 6), 1.3);
      ts.forEach((t, i) => {
        const from = at(hover, faceYaw, i % 2 ? -ARM.right : ARM.right, ARM.up, ARM.fwd * 0.6);
        const s = scene.spawn("dn_dreamer_shard", from, { yaw: yawOf(sub(t.loc, from)), state: 1 });
        const mid = up(lerp(from, t.loc, 0.5), 3);
        scene.span(scene.tick, scene.tick + 12, (p) => {
          const tg = t.e && isAlive(t.e) ? groundBelow(dim, t.e.location) : t.loc;
          s.move(bezier(from, mid, up(tg, 0.8), p));
          if (p > 0.95) t.loc = tg;
        });
        scene.after(12, () => {
          s.state(2);
          particle(dim, "dn_dreamer_glint", up(t.loc, 1));
          for (const e of hostiles(dim, t.loc, 1.8, caster)) damage(e, DN06.shardDamage, caster);
          if (i === 0) sound(dim, "dn_dreamer_glass", t.loc, 1.2, 1.15);
        });
        scene.after(22, () => scene.despawn(s));
      });
    });
    scene.at(T_ARMS + LEN.fireArms, () => dreamer.state(DS2.conduct));
  });
  const T_DRILL = T_ARMS + 40;
  scene.at(T_DRILL, () => {
    const tgt = groups(1)[0];
    warn(tgt, DN06.drillRadius, true, DN06.warnLong);
    const top = up(tgt, 16);
    const d = scene.spawn("dn_dreamer_drill", top, { yaw: faceYaw, state: 1 });
    line(dim, "dn_dreamer_trail", up(hover, 20), up(top, 10), 6);
    scene.after(20, () => {
      d.state(3);
      sound(dim, "dn_dreamer_drill", tgt, 1.4);
    });
    scene.span(scene.tick + 20, scene.tick + DN06.warnLong, (p) => d.move(lerp(top, tgt, p * p)));
    scene.after(DN06.warnLong, () => {
      particle(dim, "dn_dreamer_shock", up(tgt, 0.2));
      particle(dim, "dn_dreamer_dust", up(tgt, 0.3));
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
      particle(dim, "dn_dreamer_porcelain", up(tgt, 1));
    }, scene.tick + DN06.warnLong + 10, scene.tick + DN06.warnLong + 31);
    scene.span(scene.tick + DN06.warnLong, scene.tick + DN06.warnLong + 30, (p) => d.move(up(tgt, -2.5 * p)));
    scene.after(DN06.warnLong + 30, () => d.state(4));
    scene.after(DN06.warnLong + 46, () => scene.despawn(d));
  });
  const T_SWING = T_DRILL + 70;
  scene.at(T_SWING - DN06.warnLong, () => {
    for (const a of [-30, -10, 10, 30]) warn(ground(swingPos(a)), 3, true, DN06.warnLong + 10);
  });
  const swung = /* @__PURE__ */ new Set();
  scene.at(T_SWING, () => {
    bed.state(BED.swing);
    sound(dim, "dn_dreamer_pendulum", pivot, 1.6);
  });
  scene.span(T_SWING, T_SWING + SWING_T, (p) => {
    const th = SWING_A * Math.cos(Math.PI * p);
    bedPos = swingPos(th);
    bed.move(bedPos, faceYaw);
    if (Math.abs(th) < 26) {
      const g = ground(bedPos);
      particle(dim, "dn_dreamer_petal", up(g, 1));
      hitOnce(swung, g, DN06.pendulumRadius, DN06.pendulumDamage, (e) => shove(e, mul(swingAxis, -1), 2, 0.7));
    }
  });
  const T_ROOMS = T_SWING + 14;
  scene.at(T_ROOMS, () => {
    dreamer.state(DS2.fireRooms);
    sound(dim, "dn_dreamer_door", up(hover, 8), 1.2, 0.6);
  });
  scene.at(T_ROOMS + 12, () => {
    const from = at(hover, faceYaw, 0, CHEST.up, CHEST.fwd);
    targets(DN06.rooms, 6).forEach((t, i) => {
      const r = scene.spawn("dn_dreamer_roomcube", from, { yaw: faceYaw + i * 40, state: 1 });
      const top = up(lerp(from, t.loc, 0.5), 4);
      scene.span(scene.tick, scene.tick + 16, (p) => {
        if (t.e && isAlive(t.e) && p < 0.8) t.loc = groundBelow(dim, t.e.location);
        r.move(bezier(from, top, t.loc, p));
      });
      scene.after(16, () => {
        r.state(2);
        sound(dim, "dn_dreamer_room", t.loc, 1.1);
        for (const e of hostiles(dim, t.loc, DN06.roomRadius, caster)) restrain(scene, e, DN06.roomHold, { ...e.location });
      });
      scene.after(32, () => {
        r.state(3);
        particle(dim, "dn_dreamer_dust", up(t.loc, 0.3));
        for (const e of hostiles(dim, t.loc, DN06.roomRadius + 0.5, caster)) damage(e, DN06.roomDamage, caster);
      });
      scene.after(42, () => r.state(4));
      scene.after(58, () => scene.despawn(r));
    });
  });
  scene.at(T_ROOMS + LEN.fireRooms, () => dreamer.state(DS2.conduct));
  const T_FIN = T_ROOMS + LEN.fireRooms + 18;
  let land = ground(at(hover, faceYaw, 0, 0, BEAM_LAND));
  scene.span(T_FIN - 18, T_FIN, (p) => {
    const want = yawOf(sub(centroid(), hover));
    const turn = clamp(angleDelta(faceYaw, want), -DN06.finaleTurn, DN06.finaleTurn);
    dYaw = faceYaw + turn * smooth(p);
    dreamer.move(hover, dYaw);
  });
  scene.at(T_FIN, () => {
    land = ground(at(hover, dYaw, 0, 0, BEAM_LAND));
    dreamer.state(DS2.finale);
    warn(land, DN06.beamRadius, true, LEN.finale + 5);
  });
  scene.at(T_FIN + 8, () => sound(dim, "dn_dreamer_beam", land, 1.7));
  scene.every(4, (e) => {
    particle(dim, "dn_dreamer_beam", up(land, 12));
    if (e % 8 === 0) burst(dim, "dn_dreamer_moon", up(land, 2), DN06.beamRadius * 0.5, 3);
    for (const x of hostiles(dim, land, DN06.beamRadius, caster)) {
      const d = distXZ(x.location, land);
      if (d > 1.2) {
        const step = mul(norm({ x: land.x - x.location.x, y: 0, z: land.z - x.location.z }), Math.min(DN06.beamPull * 4, d - 1));
        drag(x, add(x.location, step));
      }
      if (e % 12 === 0) damage(x, DN06.beamDamage, caster);
    }
  }, T_FIN + 22, T_FIN + LEN.finale);
  const T_SLAM2 = T_FIN + LEN.finale;
  scene.at(T_SLAM2, () => dreamer.state(DS2.slam));
  scene.at(T_SLAM2 + 3, () => {
    sound(dim, "dn_dreamer_final", land, 1.8);
    particle(dim, "dn_dreamer_shock", up(land, 0.2));
    particle(dim, "fx_flash", up(land, 2));
    ring(dim, "dn_dreamer_porcelain", up(land, 1), 4, 6);
    for (const e of hostiles(dim, land, DN06.finalRadius, caster)) {
      damage(e, DN06.finalDamage, caster);
      knockback(e, land, DN06.finalKnock, 0.6);
    }
  });
  const T52 = T_SLAM2 + LEN.slam + 10;
  const bookAt = () => at(caster.isValid ? caster.location : scene.origin, aim.yaw, BOOK2.right, BOOK2.up, BOOK2.fwd);
  scene.at(T52, () => {
    dreamer.state(DS2.forget).skin(0);
    sound(dim, "dn_dreamer_break", up(hover, 8), 1.5);
    bed.state(BED.vanish);
    for (const m of marks.values()) {
      m.a.state(3);
      const a = m.a;
      scene.after(8, () => scene.despawn(a));
    }
  });
  scene.every(10, (e) => burst(dim, "dn_dreamer_porcelain", up(hover, 4 + e / 10), 5, 4), T52 + 6, T52 + 70);
  const bedStart = { ...bedPos };
  scene.span(T52, T52 + 50, (p) => bed.move(lerp(bedStart, up(bookAt(), 2), smooth(p)), faceYaw + p * 90));
  scene.at(T52 + 52, () => scene.despawn(bed));
  scene.at(T52 + 10, () => {
    domain.state(3);
    codex.state(CODEX.gather);
  });
  scene.at(T52 + 42, () => scene.despawn(domain));
  scene.at(T52 + 20, () => sound(dim, "dn_dreamer_morning", caster.location, 1));
  scene.at(T52 + 30, () => {
    const from = at(hover, faceYaw, 0, CHEST.up, CHEST.fwd * 0.5);
    const room = scene.spawn("dn_dreamer_bedroom", from, { yaw: faceYaw, size: 6, state: 1 });
    scene.after(16, () => room.state(2));
    const mid = up(lerp(from, bookAt(), 0.5), 6);
    scene.span(scene.tick + 20, scene.tick + 70, (p) => {
      room.move(bezier(from, mid, bookAt(), smooth(p))).size(6 + (0.35 - 6) * smooth(p));
      if (Math.round(p * 50) % 10 === 0) particle(dim, "dn_dreamer_mote", room.loc);
    });
    scene.after(70, () => room.state(3));
    scene.after(88, () => scene.despawn(room));
  });
  scene.at(T52 + LEN.forget, () => scene.despawn(dreamer));
  const T_CLOSE = T52 + 104;
  scene.at(T_CLOSE, () => {
    codex.state(CODEX.close);
    particle(dim, "dn_dreamer_star", bookAt());
  });
  scene.at(T_CLOSE + 23, () => sound(dim, "dn_dreamer_click", bookAt(), 0.8));
  scene.endAt(T_CLOSE + 54);
  void dist;
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
var T5 = {
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
  const skidDist = RUN_SPEED / 20 * (T5.skid - 1) / 2;
  const lanePoint = (s2, lat = 0) => groundBelow(dim, add(add(W2, mul(d, s2)), mul(rv, lat)));
  const arriveDist = WALK_SPEED2 * T5.arriveWalk / 20;
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
  scene.span(0, T5.arriveWalk + 1, (p) => {
    s = -arriveDist * (1 - p);
    place();
  });
  const tI = T5.arrive;
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
  scene.at(tI + T5.igniteRoar, () => {
    const c = chest();
    particle(dim, "ed_heat_ring", up(pos, 0.3));
    particle(dim, "fx_flash", c);
    ring(dim, "ed_heat_vent", up(pos, 3.5), 2.8, 5);
    for (const e of hostiles(dim, c, ED02.igniteRadius, caster)) {
      if (damage(e, ED02.igniteDamage, caster)) knockback(e, pos, ED02.igniteKnock, 0.35);
    }
  });
  const tC = tI + T5.ignite;
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
      s += RUN_SPEED / 20 * Math.max(0, 1 - k2 / T5.skid);
      place();
      strikes();
      if (k2 % 3 === 0) particle(dim, "ed_heat_skid", up(add(pos, mul(d, 1)), 0.3));
      if (k2 >= T5.skid) {
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
    scene.every(3, () => particle(dim, "ed_heat_vent", up(pos, 4.2)), tP + 6, tP + T5.powerOpen);
    const tR = tP + T5.powerOpen;
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
    const tPant = tCool + T5.cool;
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
    scene.at(tDep + T5.depart, () => scene.despawn(dragon));
    scene.endAt(tDep + T5.depart + 2);
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
var T6 = {
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
var tSwim = tArrive + T6.arrive;
var tLand = 70;
var tPower = tLand + T6.land;
var tSweep = 114;
var tFlare = tSweep + T6.sweep;
var tFreeze = tFlare + T6.flareHit + 2;
var tSpiral = 174;
var tRoar = 182;
var tCrown = 188;
var tRise = 190;
var tStrike = tRoar + T6.roar - 2;
var tHit = tStrike + T6.strikeHit;
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
  scene.at(tLand + T6.landHit, () => {
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
  scene.at(tPower + T6.power, () => dragon.state(D2.idle));
  const currents = [];
  scene.at(tSweep, () => dragon.state(D2.attack_a));
  T6.sweepHit.forEach((h, w) => scene.at(tSweep + h, () => throwCurrents(w * 2, w === 0 ? 55 : 28)));
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
  }, tSweep + T6.sweepHit[0], tFreeze + 4);
  scene.every(4, (el) => {
    for (const c of currents) if (scene.tick - c.born > 6) particle(dim, "ed_tide_spray", arcPoint(c, el * 37 % CUR_SWEEP, 0.6));
  }, tSweep + T6.sweepHit[0] + 4, tFreeze);
  scene.at(tFlare, () => dragon.state(D2.attack_c));
  scene.at(tFlare + T6.flareHit, () => {
    sound(dim, "ed_tide_freeze", G, 1.4);
    burst(dim, "ed_tide_glint", sailPeak, 2, 6);
    const tip = tailTip(10);
    for (const c of currents) {
      line(dim, "ed_tide_frostline", sailPeak, arcPoint(c, 0, 1), 8);
      line(dim, "ed_tide_frostline", tip, arcPoint(c, 0, 0.6), 4);
    }
  });
  scene.at(tFlare + T6.flare, () => dragon.state(D2.idle));
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
  scene.at(tRoar + T6.roar, () => dragon.state(D2.idle));
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
  scene.every(6, (el) => particle(dim, "ed_tide_mist", up(sub(L3, mul(rt, -2 + el * 0.2)), 2 + el * 0.08)), tDepart + 6, tDepart + T6.depart);
  scene.at(tDepart + 20, () => ring(dim, "ed_tide_splash", up(L3, 0.3), 3.5, 6));
  scene.at(tDepart + T6.depart, () => scene.despawn(dragon));
  scene.endAt(tDepart + T6.depart + 4);
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
      const P5 = passes[k2][3];
      const dIn = norm(flat(sub(P5, spline(passes[k2], 0.94))));
      const dOut = norm(flat(sub(spline(passes[k2 + 1], 0.06), P5)));
      const outward = norm(sub(dIn, dOut));
      const hs = ED04.hairpinSize;
      splineLeg("turn", [
        P5,
        up(add(P5, mul(dIn, hs * 1.4)), ED04.hairpinLift * 0.7),
        up(add(P5, mul(outward, hs * 2.2)), ED04.hairpinLift),
        up(sub(P5, mul(dOut, hs * 1.4)), ED04.hairpinLift * 0.6),
        P5
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

// src/spells/ed05_buried_kingdoms.ts
var ed05_buried_kingdoms_default = defineSpell("ed05", (ctx) => {
  ctx.caster.sendMessage("ed05 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed06_world_before_names.ts
var ed06_world_before_names_default = defineSpell("ed06", (ctx) => {
  ctx.caster.sendMessage("ed06 is not implemented yet");
  ctx.scene.endAt(1);
});

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
