// Strict emulation of the parts of @minecraft/server 2.11.0 used by the add-on.
// Every identifier (entities, properties, events, particles, molang variables,
// sounds, items) is checked against the built packs / vanilla reference, entity
// methods throw on removed entities, and world-modifying calls made while a
// before-event is being dispatched are reported (the real engine forbids them).
// A tiny physics step (velocity, gravity, ground at y=64, walls) lets the road
// engine be observed actually moving players, mobs and projectiles.
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.JOAN_MOCK_DATA, "utf8"));
export const __issues = [];
export const __log = { particles: [], sounds: [], spawned: [], items: [], titles: [], damage: [], events: [] };
function issue(msg) {
  if (__issues.length < 400) __issues.push(msg);
}

let restricted = 0;
function privileged(what) {
  if (restricted > 0) issue(`privileged call ${what} during a before-event (throws in the real game)`);
}

// ------------------------------------------------------------------ enums
const mk = (names) => Object.fromEntries(names.map((k) => [k, k]));
export const EntityDamageCause = mk(["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack",
  "entityExplosion", "fall", "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning",
  "maceSmash", "magic", "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom",
  "soulCampfire", "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"]);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const Difficulty = { Peaceful: "Peaceful", Easy: "Easy", Normal: "Normal", Hard: "Hard" };
export const CameraShakeType = { Positional: "Positional", Rotational: "Rotational" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = mk(["BlockType", "Boolean", "EntitySelector", "EntityType", "Enum", "Float", "Integer", "Location", "PlayerSelector", "String"]);
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const EntityInitializationCause = { Born: "Born", Event: "Event", Loaded: "Loaded", Spawned: "Spawned", Transformed: "Transformed" };

// ------------------------------------------------------------------ scheduler
let currentTick = 0;
let nextId = 1;
const timers = new Map();
function schedule(fn, delay, interval) {
  if (typeof fn !== "function") issue("scheduled a non-function");
  if (!Number.isFinite(delay) || delay < 0) issue(`bad delay ${delay}`);
  const id = nextId++;
  timers.set(id, { fn, due: currentTick + Math.max(0, Math.floor(delay)), interval });
  return id;
}
class Signal {
  constructor(name, before = false) {
    this.name = name;
    this.before = before;
    this.handlers = [];
  }
  subscribe(fn) {
    this.handlers.push(fn);
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h !== fn);
  }
  fire(ev) {
    if (this.before) restricted++;
    try {
      for (const h of this.handlers) {
        try {
          h(ev);
        } catch (e) {
          issue(`handler for ${this.name} threw: ${e && e.stack ? e.stack.split("\n").slice(0, 3).join(" | ") : e}`);
        }
      }
    } finally {
      if (this.before) restricted--;
    }
    return ev;
  }
}
export const system = {
  get currentTick() {
    return currentTick;
  },
  run: (fn) => schedule(fn, 0),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, i),
  clearRun: (id) => timers.delete(id),
  beforeEvents: { startup: new Signal("startup", false), shutdown: new Signal("shutdown", false) },
  afterEvents: {},
};

export const __perf = { scriptMs: 0, ticks: 0, maxTickMs: 0 };
export async function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    currentTick++;
    physics();
    const t0 = performance.now();
    for (const [id, t] of [...timers.entries()]) {
      if (t.due > currentTick || !timers.has(id)) continue;
      if (t.interval) t.due = currentTick + t.interval;
      else timers.delete(id);
      try {
        t.fn();
      } catch (e) {
        issue(`uncaught error in scheduled callback: ${e && e.stack ? e.stack.split("\n").slice(0, 4).join(" | ") : e}`);
      }
    }
    const dt = performance.now() - t0;
    __perf.scriptMs += dt;
    __perf.ticks++;
    __perf.maxTickMs = Math.max(__perf.maxTickMs, dt);
    await Promise.resolve();
  }
}

// ------------------------------------------------------------------ data helpers
const PARTICLES = new Set(DATA.particles);
const SOUNDS = new Set(DATA.sounds);
const ENTITY_DEFS = DATA.entities;
const ITEMS = new Set(DATA.items);
const MOLANG_VARS = new Set(DATA.molangVars);
const GROUND = 64;
export const __walls = []; // {x0,x1,z0,z1,y1} solid boxes standing on the ground
export const __plants = new Set(); // "x,z" cells with a passable plant at y = GROUND (short grass, flowers...)
// How applyKnockback combines with the current motion. The 2.11 typings describe it as an impulse added to
// the velocity; the classic engine halves the old motion first. The smoke test runs under all three.
const KB = process.env.JOAN_KB || "halve";
const plantAt = (x, y, z) => Math.floor(y) === GROUND && __plants.has(`${Math.floor(x)},${Math.floor(z)}`);
function finite(v, what) {
  if (!v || !Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) issue(`non-finite vector for ${what}: ${JSON.stringify(v)}`);
}
function wallAt(x, y, z) {
  return __walls.some((w) => x >= w.x0 && x <= w.x1 && z >= w.z0 && z <= w.z1 && y < w.y1 && y >= GROUND);
}

// ------------------------------------------------------------------ molang / items
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  #name(n) {
    if (!/^variable\.[a-z_0-9]+$/.test(n)) issue(`bad molang variable name ${n}`);
    if (!MOLANG_VARS.has(n)) issue(`molang variable ${n} is never read by our particles`);
  }
  setFloat(n, v) {
    this.#name(n);
    if (!Number.isFinite(v)) issue(`molang ${n} = ${v}`);
    this.vars[n] = v;
  }
  setVector3(n, v) {
    this.#name(n);
    finite(v, n);
    this.vars[n] = v;
  }
  setColorRGBA(n, c) {
    this.#name(n);
    for (const k of ["red", "green", "blue", "alpha"]) if (!(c[k] >= 0 && c[k] <= 1)) issue(`color ${n}.${k} = ${c[k]}`);
    this.vars[n] = c;
  }
  setColorRGB(n, c) {
    this.setColorRGBA(n, { ...c, alpha: 1 });
  }
  setSpeedAndDirection(n, s, d) {
    this.#name(n);
    this.vars[n] = { s, d };
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.includes(":")) typeId = "minecraft:" + typeId;
    if (!ITEMS.has(typeId) && !typeId.startsWith("minecraft:")) issue(`unknown item ${typeId}`);
    if (!Number.isInteger(amount) || amount < 1 || amount > 64) issue(`bad item amount ${amount}`);
    this.typeId = typeId;
    this.amount = amount;
  }
}
class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i];
  }
  setItem(i, it) {
    this.slots[i] = it;
  }
}
export class EntityInventoryComponent {
  static componentId = "minecraft:inventory";
}

// ------------------------------------------------------------------ entities
class Attr {
  constructor(value, max) {
    this.currentValue = value;
    this.defaultValue = value;
    this.effectiveMax = max;
  }
  setCurrentValue(v) {
    privileged("setCurrentValue");
    if (!Number.isFinite(v)) issue(`attribute set to ${v}`);
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
  resetToDefaultValue() {
    privileged("resetToDefaultValue");
    this.currentValue = this.defaultValue;
  }
  resetToMaxValue() {
    privileged("resetToMaxValue");
    this.currentValue = this.effectiveMax;
  }
}

export class Entity {
  constructor(typeId, dimension, location) {
    const def = ENTITY_DEFS[typeId];
    if (!def) issue(`spawned unknown entity ${typeId}`);
    this.id = String(-(1e9 + nextId++));
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.__valid = true;
    this.__def = def || { families: [], events: [], properties: {}, gravity: true };
    this.__vel = { x: 0, y: 0, z: 0 };
    this.__rot = { x: 0, y: 0 };
    this.__dyn = new Map();
    this.__props = new Map();
    this.__fire = 0;
    this.__hurt = [];
    this.__events = [];
    this.__knock = 0;
    this.isSneaking = false;
    this.nameTag = "";
    if (def && def.health) this.__health = new Attr(def.health, def.health);
    if (def && def.movement !== undefined) this.__move = new Attr(def.movement, def.movement);
    for (const [k, p] of Object.entries(this.__def.properties || {})) this.__props.set(k, p.default);
    world.__entities.set(this.id, this);
  }
  get isValid() {
    return this.__valid;
  }
  #c(what) {
    if (!this.__valid) throw new Error(`InvalidEntityError: ${what} on removed ${this.typeId}`);
  }
  get isOnGround() {
    this.#c("isOnGround");
    return this.location.y <= GROUND + 1e-6;
  }
  getComponent(id) {
    this.#c("getComponent");
    if (id === "minecraft:health" || id === "health") return this.__health;
    if (id === "minecraft:movement") return this.__move;
    if (id === "minecraft:inventory" || id === "inventory") return this.__inv ? { container: this.__inv } : undefined;
    if (id === "minecraft:projectile" && this.__def.projectile) return { owner: this.__owner };
    return undefined;
  }
  getVelocity() {
    this.#c("getVelocity");
    return { ...this.__vel };
  }
  clearVelocity() {
    this.#c("clearVelocity");
    privileged("clearVelocity");
    this.__vel = { x: 0, y: 0, z: 0 };
  }
  applyImpulse(v) {
    this.#c("applyImpulse");
    privileged("applyImpulse");
    if (this.typeId === "minecraft:player") throw new Error("UnsupportedFunctionalityError: applyImpulse on players");
    finite(v, "impulse");
    if (Math.hypot(v.x, v.y, v.z) > 6) issue(`absurd impulse ${JSON.stringify(v)} on ${this.typeId}`);
    this.__vel = { x: this.__vel.x + v.x, y: this.__vel.y + v.y, z: this.__vel.z + v.z };
  }
  applyKnockback(h, vert) {
    this.#c("applyKnockback");
    privileged("applyKnockback");
    if (!h || typeof h !== "object" || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue(`bad knockback ${JSON.stringify(h)} ${vert}`);
    if (Math.hypot(h.x, h.z) > 4 || vert > 3) issue(`absurd knockback ${JSON.stringify(h)} ${vert}`);
    const k = KB === "set" ? 0 : KB === "halve" ? 0.5 : 1;
    this.__vel = { x: this.__vel.x * k + h.x, y: vert > 0 ? vert : this.__vel.y, z: this.__vel.z * k + h.z };
    this.__knock++;
  }
  applyDamage(amount, opts = {}) {
    this.#c("applyDamage");
    privileged("applyDamage");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage ${amount}`);
    if (opts.cause && !(opts.cause in EntityDamageCause)) issue(`bad cause ${opts.cause}`);
    if (!this.__health) return false;
    if (this.typeId === "minecraft:player" && [GameMode.Creative, GameMode.Spectator].includes(this.__gm)) issue("damaged a creative/spectator player");
    const src = { cause: opts.cause ?? "entityAttack", damagingEntity: opts.damagingEntity, damagingProjectile: opts.damagingProjectile };
    const before = world.beforeEvents.entityHurt.fire({ hurtEntity: this, damage: amount, cancel: false, damageSource: src });
    if (before.cancel) return false;
    const dmg = before.damage;
    this.__hurt.push({ amount: dmg, cause: src.cause, by: src.damagingEntity?.typeId, tick: currentTick });
    __log.damage.push({ to: this.typeId, amount: dmg, by: src.damagingEntity?.typeId });
    this.__health.currentValue -= dmg;
    world.afterEvents.entityHurt.fire({ hurtEntity: this, damage: dmg, damageSource: src });
    if (this.__health.currentValue <= 0) {
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: src });
      if (this.typeId !== "minecraft:player") this.remove();
      else this.__health.currentValue = this.__health.effectiveMax;
    }
    return true;
  }
  setOnFire(s) {
    this.#c("setOnFire");
    privileged("setOnFire");
    this.__fire = s;
    return true;
  }
  teleport(loc, opts = {}) {
    this.#c("teleport");
    privileged("teleport");
    finite(loc, "teleport");
    if (opts.facingLocation) finite(opts.facingLocation, "facing");
    this.location = { ...loc };
  }
  setRotation(r) {
    this.#c("setRotation");
    privileged("setRotation");
    if (!Number.isFinite(r.x) || !Number.isFinite(r.y)) issue(`bad rotation ${JSON.stringify(r)}`);
    this.__rot = { ...r };
  }
  getRotation() {
    this.#c("getRotation");
    return { ...this.__rot };
  }
  lookAt(p) {
    finite(p, "lookAt");
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getDynamicProperty(k) {
    this.#c("getDynamicProperty");
    return this.__dyn.get(k);
  }
  setDynamicProperty(k, v) {
    this.#c("setDynamicProperty");
    privileged("setDynamicProperty");
    if (!/^[a-z_]+:[a-z_]+$/.test(k)) issue(`dynamic property ${k} should be namespaced`);
    if (v === undefined) this.__dyn.delete(k);
    else this.__dyn.set(k, v);
  }
  getProperty(k) {
    this.#c("getProperty");
    if (!this.__props.has(k)) throw new Error(`property ${k} not defined on ${this.typeId}`);
    return this.__props.get(k);
  }
  setProperty(k, v) {
    this.#c("setProperty");
    privileged("setProperty");
    const def = this.__def.properties?.[k];
    if (!def) throw new Error(`property ${k} is not defined on ${this.typeId}`);
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) issue(`int property ${k} out of range: ${v}`);
    if (def.type === "float" && (typeof v !== "number" || v < def.range[0] || v > def.range[1])) issue(`float property ${k} out of range: ${v}`);
    if (def.type === "bool" && typeof v !== "boolean") issue(`bool property ${k} given ${v}`);
    this.__props.set(k, v);
  }
  triggerEvent(name) {
    this.#c("triggerEvent");
    privileged("triggerEvent");
    if (!this.__def.events.includes(name)) issue(`entity ${this.typeId} has no event ${name}`);
    this.__events.push(name);
  }
  matches() {
    return true;
  }
  remove() {
    this.#c("remove");
    privileged("remove");
    this.__valid = false;
    world.__entities.delete(this.id);
  }
  kill() {
    this.applyDamage(99999, { cause: "override" });
    return true;
  }
  hasTag() {
    return false;
  }
}

class Screen {
  constructor(p) {
    this.p = p;
    this.actionbar = [];
  }
  setActionBar(t) {
    privileged("setActionBar");
    if (typeof t !== "string") issue("actionbar must be a string");
    this.actionbar.push(t);
  }
  setTitle(t, o) {
    privileged("setTitle");
    if (!o || !Number.isFinite(o.stayDuration) || !Number.isFinite(o.fadeInDuration) || !Number.isFinite(o.fadeOutDuration)) issue("title options incomplete");
    __log.titles.push({ t, sub: o?.subtitle, to: this.p.name });
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__inv = new Container(36);
    this.selectedSlotIndex = 0;
    this.onScreenDisplay = new Screen(this);
    this.camera = { addShake: (o) => {
      if (!o || !Number.isFinite(o.intensity) || !Number.isFinite(o.duration) || !(o.type in CameraShakeType)) issue(`bad shake ${JSON.stringify(o)}`);
      this.__shakes = (this.__shakes || 0) + 1;
    } };
    this.messages = [];
    this.__gm = GameMode.Survival;
    this.__xp = 0;
    this.__cooldowns = {};
  }
  sendMessage(m) {
    this.messages.push(String(m));
  }
  getGameMode() {
    return this.__gm;
  }
  addExperience(n) {
    privileged("addExperience");
    this.__xp += n;
    return this.__xp;
  }
  startItemCooldown(cat, ticks) {
    if (!/^[a-z_]+:[a-z_]+$/.test(cat)) issue(`cooldown category ${cat}`);
    this.__cooldowns[cat] = ticks;
  }
  playSound(id) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
  }
}

// ------------------------------------------------------------------ physics
function physics() {
  for (const e of world.__entities.values()) {
    if (!e.__valid) continue;
    const grav = e.__def.gravity !== false && !e.__def.projectile;
    const v = e.__vel;
    const nx = e.location.x + v.x;
    const nz = e.location.z + v.z;
    let ny = e.location.y + v.y;
    if (!wallAt(nx, e.location.y + 0.5, nz)) {
      e.location.x = nx;
      e.location.z = nz;
    } else {
      v.x = 0;
      v.z = 0;
    }
    if (grav && ny < GROUND) ny = GROUND;
    e.location.y = ny;
    if (grav) {
      if (e.location.y > GROUND) v.y -= 0.08;
      else v.y = Math.max(0, v.y);
      const f = e.location.y <= GROUND ? 0.55 : 0.91;
      v.x *= f;
      v.z *= f;
    }
    if (e.__def.projectile) {
      if (e.location.y <= GROUND - 0.5 || Math.abs(e.location.x) > 300) e.remove();
    }
  }
}

// ------------------------------------------------------------------ dimension / world
class Block {
  constructor(loc) {
    this.location = loc;
    const plant = plantAt(loc.x + 0.5, loc.y + 0.5, loc.z + 0.5);
    this.isAir = loc.y >= GROUND && !plant && !wallAt(loc.x + 0.5, loc.y + 0.5, loc.z + 0.5);
    this.isLiquid = false;
    this.typeId = plant ? "minecraft:short_grass" : this.isAir ? "minecraft:air" : "minecraft:stone";
  }
}
class Dimension {
  constructor(id) {
    this.id = id;
  }
  __all() {
    return [...world.__entities.values()].filter((e) => e.__valid && e.dimension === this);
  }
  getEntities(o = {}) {
    let list = this.__all();
    if (o.type) list = list.filter((e) => e.typeId === o.type);
    if (o.families) list = list.filter((e) => o.families.every((f) => e.__def.families.includes(f)));
    if (o.excludeTypes) list = list.filter((e) => !o.excludeTypes.includes(e.typeId));
    if (o.excludeFamilies) list = list.filter((e) => !o.excludeFamilies.some((f) => e.__def.families.includes(f)));
    if (o.location) {
      finite(o.location, "getEntities");
      if (o.maxDistance !== undefined) {
        if (!Number.isFinite(o.maxDistance) || o.maxDistance < 0) issue(`bad maxDistance ${o.maxDistance}`);
        list = list.filter((e) => Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z) <= o.maxDistance);
      }
    }
    world.__queries++;
    return list;
  }
  getPlayers(o = {}) {
    return this.getEntities(o).filter((e) => e instanceof Player);
  }
  spawnEntity(id, loc) {
    privileged("spawnEntity");
    finite(loc, "spawnEntity");
    if (!ENTITY_DEFS[id]) throw new Error(`unknown entity type ${id}`);
    const e = new Entity(id, this, loc);
    __log.spawned.push(id);
    world.afterEvents.entitySpawn.fire({ entity: e, cause: EntityInitializationCause.Spawned });
    return e;
  }
  spawnItem(item, loc) {
    privileged("spawnItem");
    finite(loc, "spawnItem");
    if (!(item instanceof ItemStack)) issue("spawnItem needs an ItemStack");
    __log.items.push(item.typeId);
    return new Entity("minecraft:item", this, loc);
  }
  spawnParticle(id, loc, vars) {
    privileged("spawnParticle");
    if (!PARTICLES.has(id)) issue(`unknown particle ${id}`);
    finite(loc, "particle");
    if (vars && !(vars instanceof MolangVariableMap)) issue("particle variables must be a MolangVariableMap");
    world.__particles++;
  }
  playSound(id, loc, opts) {
    privileged("playSound");
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    finite(loc, "sound");
    if (opts && (!Number.isFinite(opts.volume ?? 1) || !Number.isFinite(opts.pitch ?? 1))) issue("bad sound options");
    __log.sounds.push(id);
  }
  getBlock(loc) {
    finite(loc, "getBlock");
    return new Block({ x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) });
  }
  getBlockFromRay(from, dir, o = {}) {
    finite(from, "ray");
    finite(dir, "ray dir");
    const max = o.maxDistance ?? 64;
    for (let t = 0; t <= max; t += 0.25) {
      const p = { x: from.x + dir.x * t, y: from.y + dir.y * t, z: from.z + dir.z * t };
      if (o.includePassableBlocks && plantAt(p.x, p.y, p.z)) {
        const b = { x: Math.floor(p.x), y: GROUND, z: Math.floor(p.z) };
        return { block: new Block(b), face: "Up", faceLocation: { x: p.x - b.x, y: 0.4, z: p.z - b.z } };
      }
      if (p.y < GROUND || wallAt(p.x, p.y, p.z)) {
        const b = { x: Math.floor(p.x), y: Math.floor(Math.min(p.y, GROUND - 0.001)), z: Math.floor(p.z) };
        if (p.y < GROUND) return { block: new Block({ ...b, y: GROUND - 1 }), face: "Up", faceLocation: { x: p.x - b.x, y: 1, z: p.z - b.z } };
        return { block: new Block(b), face: "North", faceLocation: { x: 0.5, y: p.y - b.y, z: 0 } };
      }
    }
    return undefined;
  }
}

const afterNames = ["worldLoad", "entitySpawn", "entityLoad", "entityHitEntity", "projectileHitEntity", "itemStartUse",
  "itemReleaseUse", "itemUse", "playerInteractWithBlock", "entityHurt", "entityDie"];
export const world = {
  __entities: new Map(),
  __dims: {},
  __particles: 0,
  __queries: 0,
  __difficulty: Difficulty.Normal,
  afterEvents: Object.fromEntries(afterNames.map((n) => [n, new Signal(n, false)])),
  beforeEvents: { entityHurt: new Signal("entityHurt(before)", true) },
  getDimension(id) {
    if (!["minecraft:overworld", "minecraft:nether", "minecraft:the_end"].includes(id)) throw new Error(`no dimension ${id}`);
    if (!this.__dims[id]) this.__dims[id] = new Dimension(id);
    return this.__dims[id];
  },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player && e.__valid);
  },
  getDifficulty() {
    return this.__difficulty;
  },
};

export { Dimension, Container, Block };
