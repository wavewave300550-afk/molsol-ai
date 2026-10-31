// Strict, minimal emulation of the @minecraft/server API surface used by the add-on.
// Every identifier (effects, particles, sounds, entity types, events, properties)
// is checked against the real pack data / vanilla reference so wrong ids fail loudly.
import fs from "node:fs";
import path from "node:path";

const DATA = JSON.parse(fs.readFileSync(process.env.TRIBES_MOCK_DATA, "utf8"));
export const __issues = [];
function issue(msg) {
  __issues.push(msg);
}

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack", "entityExplosion", "fall",
   "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning", "maceSmash", "magic",
   "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom", "soulCampfire",
   "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"].map((k) => [k, k]),
);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = { Enum: "Enum", String: "String", Integer: "Integer" };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const Difficulty = { Peaceful: "Peaceful", Easy: "Easy", Normal: "Normal", Hard: "Hard" };
export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(k, v) {
    if (!k.startsWith("variable.") || !Number.isFinite(v)) issue(`bad molang float ${k}=${v}`);
    this.vars[k] = v;
  }
  setColorRGB(k, c) {
    if (!k.startsWith("variable.") || !c || ![c.red, c.green, c.blue].every((x) => Number.isFinite(x) && x >= 0 && x <= 1)) issue(`bad molang colour ${k}=${JSON.stringify(c)}`);
    this.vars[k] = c;
  }
  setColorRGBA(k, c) {
    if (!k.startsWith("variable.") || !c || ![c.red, c.green, c.blue, c.alpha].every((x) => Number.isFinite(x) && x >= 0 && x <= 1)) issue(`bad molang colour ${k}=${JSON.stringify(c)}`);
    this.vars[k] = c;
  }
  setSpeedAndDirection(k, speed, dir) {
    if (!k.startsWith("variable.") || !Number.isFinite(speed) || !dir || ![dir.x, dir.y, dir.z].every(Number.isFinite)) issue(`bad molang speed/direction ${k}`);
    this.vars[k] = { speed, dir };
  }
  setVector3(k, v) {
    if (!k.startsWith("variable.") || !v || ![v.x, v.y, v.z].every(Number.isFinite)) issue(`bad molang vector ${k}`);
    this.vars[k] = v;
  }
}

// ------------------------------------------------------------------ scheduler
let currentTick = 0;
let nextId = 1;
const timers = new Map();
function schedule(fn, delay, interval) {
  const id = nextId++;
  timers.set(id, { fn, due: currentTick + Math.max(0, delay), interval });
  return id;
}

class Signal {
  constructor(name) {
    this.name = name;
    this.handlers = [];
  }
  subscribe(fn, opts) {
    // honour entityFilter.families like the real API (hurtEntity / deadEntity / entity)
    const fam = opts?.entityFilter?.families;
    if (fam) {
      const wrapped = (ev) => {
        const e = ev.hurtEntity ?? ev.deadEntity ?? ev.entity;
        if (e && fam.every((f) => e.__families?.has(f))) fn(ev);
      };
      this.handlers.push(wrapped);
      return fn;
    }
    this.handlers.push(fn);
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h !== fn);
  }
  fire(ev) {
    for (const h of this.handlers) h(ev);
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
  beforeEvents: { startup: new Signal("startup"), shutdown: new Signal("shutdown") },
  afterEvents: {},
};

export async function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    currentTick++;
    for (const e of [...world.__entities.values()]) e.__step();
    for (const [id, t] of [...timers.entries()]) {
      if (t.due > currentTick || !timers.has(id)) continue;
      if (t.interval) t.due = currentTick + t.interval;
      else timers.delete(id);
      try {
        t.fn();
      } catch (e) {
        issue(`uncaught error in scheduled callback: ${e && e.stack ? e.stack : e}`);
      }
    }
    await Promise.resolve();
  }
}

// ------------------------------------------------------------------ data helpers
const EFFECTS = new Set(DATA.effects);
const PARTICLES = new Set(DATA.particles);
const SOUNDS = new Set(DATA.sounds);
const ENTITY_DEFS = DATA.entities; // id -> {families, events, properties}
const ITEMS = new Set(DATA.items);

function finite(v, what) {
  if (!v || !Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) issue(`non-finite vector for ${what}: ${JSON.stringify(v)}`);
}
const stripNs = (id) => id.replace(/^minecraft:/, "");

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.includes(":")) typeId = "minecraft:" + typeId;
    if (!ITEMS.has(typeId) && !typeId.startsWith("minecraft:")) issue(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.lore = [];
  }
  setLore(l) {
    if ((l ?? []).some((s) => s.length > 50)) issue(`lore line longer than 50 chars: ${l}`);
    this.lore = l ?? [];
  }
  getLore() {
    return this.lore;
  }
  getComponent(id) {
    if (id === "minecraft:food" && DATA.foods.includes(this.typeId)) return { typeId: "minecraft:food" };
    return undefined;
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
  addItem(it) {
    const i = this.slots.findIndex((s) => !s);
    if (i < 0) return it;
    this.slots[i] = it;
    return undefined;
  }
}

// ------------------------------------------------------------------ entities
export class EntityHealthComponent {
  static componentId = "minecraft:health";
  constructor(e, max) {
    this.entity = e;
    this.typeId = "minecraft:health";
    this.currentValue = max;
    this.defaultValue = max;
    this.__max = max;
  }
  get effectiveMax() {
    const hb = this.entity.getEffect("health_boost");
    return this.__max + (hb ? 4 * (hb.amplifier + 1) : 0);
  }
  setCurrentValue(v) {
    if (!Number.isFinite(v)) issue(`health set to ${v}`);
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
}
export class EntityInventoryComponent {
  static componentId = "minecraft:inventory";
}
export class EntityTameableComponent {
  static componentId = "minecraft:tameable";
  constructor(e) {
    this.entity = e;
    this.isTamed = false;
  }
  tame(player) {
    if (!(player instanceof Player)) issue("tame() needs a player");
    this.isTamed = true;
    this.entity.triggerEvent(ENTITY_DEFS[this.entity.typeId].tameEvent);
    return true;
  }
}

export class Entity {
  constructor(typeId, dimension, location) {
    const def = ENTITY_DEFS[typeId];
    if (!def) issue(`spawned unknown entity ${typeId}`);
    this.id = String(nextId++);
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.__valid = true;
    this.__families = new Set(def ? def.families : []);
    this.__effects = new Map();
    this.__dyn = new Map();
    this.__props = new Map();
    this.__groups = new Set();
    this.__air = 0;
    this.__fire = 0;
    this.__hurtLog = [];
    this.__rotation = { x: 0, y: 0 };
    this.nameTag = "";
    this.isSneaking = false;
    if (def && def.health) this.__health = new EntityHealthComponent(this, def.health);
    if (def && def.tameable) this.__tame = new EntityTameableComponent(this);
    if (def && def.properties) for (const [k, p] of Object.entries(def.properties)) this.__props.set(k, p.default);
    world.__entities.set(this.id, this);
  }
  get isValid() {
    return this.__valid;
  }
  __check(what) {
    if (!this.__valid) throw new Error(`InvalidActorError: ${what} on removed entity ${this.typeId}`);
  }
  __step() {
    if (!this.__valid) return;
    if (this.__air > 0) this.__air--;
    for (const [k, e] of [...this.__effects]) {
      e.duration--;
      if (e.duration <= 0) this.__effects.delete(k);
    }
  }
  get isOnGround() {
    return this.__air <= 0;
  }
  get isFalling() {
    return this.__air > 0 && this.__air < 6;
  }
  getComponent(id) {
    this.__check("getComponent");
    if (id === "minecraft:health") return this.__health;
    if (id === "minecraft:inventory") return this.__inv ? { container: this.__inv } : undefined;
    if (id === "minecraft:tameable") return this.__tame;
    if (id === "minecraft:equippable" && this instanceof Player) {
      const eq = this.__equip;
      return { getEquipment: (slot) => { if (!(slot in EquipmentSlot)) issue(`bad slot ${slot}`); return eq[slot]; } };
    }
    if (id === "minecraft:is_tamed") return this.__groups.has("tamed_marker") ? {} : undefined;
    if (id === "minecraft:projectile" && ENTITY_DEFS[this.typeId]?.projectile) {
      const self = this;
      return {
        owner: undefined,
        shoot(v) {
          finite(v, "shoot");
          self.__velocity = v;
          self.__shot = true;
        },
      };
    }
    return undefined;
  }
  addEffect(type, duration, opts = {}) {
    this.__check("addEffect");
    const id = stripNs(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    if (!Number.isInteger(duration) || duration < 1 || duration > 20000000) issue(`bad effect duration ${duration} for ${type}`);
    const amp = opts.amplifier ?? 0;
    if (!Number.isInteger(amp) || amp < 0 || amp > 255) issue(`bad amplifier ${amp}`);
    this.__effects.set(id, { typeId: id, duration, amplifier: amp });
    return this.__effects.get(id);
  }
  getEffect(type) {
    this.__check("getEffect");
    const id = stripNs(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    return this.__effects.get(id);
  }
  getEffects() {
    return [...this.__effects.values()];
  }
  removeEffect(type) {
    this.__check("removeEffect");
    const id = stripNs(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    return this.__effects.delete(id);
  }
  applyDamage(amount, opts) {
    this.__check("applyDamage");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage ${amount}`);
    if (opts && opts.cause && !(opts.cause in EntityDamageCause)) issue(`bad cause ${opts.cause}`);
    if (!this.__health) return false;
    const before = world.beforeEvents.entityHurt.fire({ hurtEntity: this, damage: amount, cancel: false, damageSource: { cause: opts?.cause ?? "entityAttack", damagingEntity: opts?.damagingEntity } });
    if (before.cancel) return false;
    this.__hurtLog.push({ amount: before.damage, cause: opts?.cause, by: opts?.damagingEntity?.typeId });
    this.__health.currentValue -= before.damage;
    world.afterEvents.entityHurt.fire({ hurtEntity: this, damage: before.damage, damageSource: { cause: opts?.cause ?? "entityAttack", damagingEntity: opts?.damagingEntity } });
    if (this.__health.currentValue <= 0) {
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: { cause: opts?.cause, damagingEntity: opts?.damagingEntity } });
      if (!(this instanceof Player)) this.remove();
      else this.__health.currentValue = this.__health.__max;
    }
    return true;
  }
  applyKnockback(h, vert) {
    this.__check("applyKnockback");
    if (!h || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue(`bad knockback ${JSON.stringify(h)} ${vert}`);
    this.location.x += h.x;
    this.location.z += h.z;
    if (vert > 0.1) this.__air = Math.max(this.__air, 10);
  }
  applyImpulse() {
    if (this instanceof Player) throw new Error("applyImpulse is not supported on players");
  }
  setOnFire(s) {
    this.__check("setOnFire");
    this.__fire = s;
    return true;
  }
  extinguishFire() {
    this.__fire = 0;
    return true;
  }
  teleport(loc, opts = {}) {
    this.__check("teleport");
    finite(loc, "teleport");
    if (opts.facingLocation) finite(opts.facingLocation, "facingLocation");
    if (opts.rotation && (!Number.isFinite(opts.rotation.x) || !Number.isFinite(opts.rotation.y))) issue("bad teleport rotation");
    this.location = { ...loc };
    if (opts.dimension) this.dimension = opts.dimension;
  }
  getRotation() {
    return { ...this.__rotation };
  }
  setRotation(r) {
    this.__check("setRotation");
    if (!r || !Number.isFinite(r.x) || !Number.isFinite(r.y)) issue(`bad rotation ${JSON.stringify(r)}`);
    this.__rotation = { x: r.x, y: r.y };
  }
  getVelocity() {
    return this.__vel ?? { x: 0, y: 0, z: 0 };
  }
  getViewDirection() {
    const yaw = (this.__rotation.y * Math.PI) / 180;
    const pitch = (this.__rotation.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  matches(opts) {
    if (opts.families) return opts.families.every((f) => this.__families.has(f));
    return true;
  }
  getDynamicProperty(k) {
    this.__check("getDynamicProperty");
    return this.__dyn.get(k);
  }
  setDynamicProperty(k, v) {
    this.__check("setDynamicProperty");
    if (v === undefined) this.__dyn.delete(k);
    else this.__dyn.set(k, v);
  }
  getProperty(k) {
    this.__check("getProperty");
    if (!this.__props.has(k)) throw new Error(`property ${k} is not defined on ${this.typeId}`);
    return this.__props.get(k);
  }
  setProperty(k, v) {
    this.__check("setProperty");
    const def = ENTITY_DEFS[this.typeId]?.properties?.[k];
    if (!def) throw new Error(`property ${k} is not defined on ${this.typeId}`);
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) issue(`property ${k} out of range: ${v}`);
    this.__props.set(k, v);
  }
  triggerEvent(name) {
    this.__check("triggerEvent");
    const def = ENTITY_DEFS[this.typeId];
    if (!def || !def.events.includes(name)) issue(`entity ${this.typeId} has no event ${name}`);
    if (name === def?.tameEvent) this.__groups.add("tamed_marker");
  }
  remove() {
    this.__check("remove");
    this.__valid = false;
    world.__entities.delete(this.id);
  }
  kill() {
    this.applyDamage(9999, { cause: "override" });
    return true;
  }
}

class ScreenDisplay {
  constructor() {
    this.actionbar = "";
    this.titles = [];
  }
  setActionBar(t) {
    if (typeof t !== "string") issue("actionbar must be string in tests");
    this.actionbar = t;
  }
  setTitle(t, o) {
    this.titles.push({ t, o });
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__inv = new Container(36);
    this.selectedSlotIndex = 0;
    this.isJumping = false;
    this.isGliding = false;
    this.onScreenDisplay = new ScreenDisplay();
    this.messages = [];
    this.sounds = [];
    this.commandPermissionLevel = CommandPermissionLevel.Admin;
    this.__equip = {};
    this.__cooldowns = {};
    this.fades = 0;
    this.shakes = 0;
    const self = this;
    this.camera = {
      fade(o) {
        const c = o?.fadeColor;
        if (c && [c.red, c.green, c.blue].some((x) => !(x >= 0 && x <= 1))) issue(`fade colour out of range ${JSON.stringify(c)}`);
        const t = o?.fadeTime;
        if (t && [t.fadeInTime, t.holdTime, t.fadeOutTime].some((x) => !(x >= 0 && x <= 10))) issue("fade time out of range");
        self.fades++;
      },
      addShake() {},
      clear() {},
    };
  }
  runCommand(cmd) {
    if (!/^camerashake add @s \d+(\.\d+)? \d+(\.\d+)? (positional|rotational)$/.test(cmd)) issue(`unexpected command: ${cmd}`);
    this.shakes++;
    return { successCount: 1 };
  }
  getItemCooldown(cat) {
    return Math.max(0, (this.__cooldowns[cat] ?? 0) - currentTick);
  }
  startItemCooldown(cat, ticks) {
    if (!DATA.cooldowns.includes(cat)) issue(`cooldown category ${cat} not declared by any item`);
    this.__cooldowns[cat] = currentTick + ticks;
  }
  sendMessage(m) {
    this.messages.push(m);
  }
  playSound(id) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    this.sounds.push(id);
  }
  spawnParticle(id, loc) {
    if (!PARTICLES.has(id)) issue(`unknown particle ${id}`);
    finite(loc, "particle");
  }
  getGameMode() {
    return GameMode.Survival;
  }
}

// ------------------------------------------------------------------ dimension / world
class Dimension {
  constructor(id) {
    this.id = id;
    this.particles = 0;
    this.soundLog = [];
  }
  __all() {
    return [...world.__entities.values()].filter((e) => e.__valid && e.dimension === this);
  }
  getEntities(o = {}) {
    let list = this.__all();
    if (o.type) list = list.filter((e) => e.typeId === o.type);
    if (o.families) list = list.filter((e) => o.families.every((f) => e.__families.has(f)));
    if (o.excludeFamilies) list = list.filter((e) => !o.excludeFamilies.some((f) => e.__families.has(f)));
    if (o.location && o.maxDistance !== undefined) {
      finite(o.location, "getEntities");
      list = list.filter((e) => Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z) <= o.maxDistance);
    }
    return list;
  }
  getPlayers(o = {}) {
    return this.getEntities(o).filter((e) => e instanceof Player);
  }
  spawnEntity(id, loc) {
    finite(loc, "spawnEntity");
    if (!ENTITY_DEFS[id]) throw new Error(`unknown entity type ${id}`);
    const e = new Entity(id, this, loc);
    world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" });
    return e;
  }
  spawnItem(item, loc) {
    finite(loc, "spawnItem");
    const e = new Entity("minecraft:item", this, loc);
    e.__item = item.typeId;
    world.__drops.push(item.typeId);
    return e;
  }
  spawnParticle(id, loc, vars) {
    if (!PARTICLES.has(id)) issue(`unknown particle ${id}`);
    finite(loc, "particle");
    if (vars && !(vars instanceof MolangVariableMap)) issue("molang vars must be a MolangVariableMap");
    this.particles++;
  }
  __blockAt(x, y, z) {
    const k = `${Math.floor(x)}|${Math.floor(y)}|${Math.floor(z)}`;
    if (world.__edits.has(k)) return world.__edits.get(k);
    if (Math.floor(y) === 63) return "minecraft:grass_block";
    if (Math.floor(y) < 63) return "minecraft:dirt";
    return "minecraft:air";
  }
  getBlock(loc) {
    finite(loc, "getBlock");
    const t = this.__blockAt(loc.x, loc.y, loc.z);
    const location = { x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) };
    return { location, typeId: t, isAir: t === "minecraft:air", isLiquid: false, permutation: { __typeId: t } };
  }
  setBlockType(loc, type) {
    finite(loc, "setBlockType");
    if (typeof type !== "string" || !type.startsWith("minecraft:")) issue(`bad block type ${type}`);
    world.__edits.set(`${Math.floor(loc.x)}|${Math.floor(loc.y)}|${Math.floor(loc.z)}`, type);
    world.__blockWrites++;
  }
  setBlockPermutation(loc, perm) {
    finite(loc, "setBlockPermutation");
    const k = `${Math.floor(loc.x)}|${Math.floor(loc.y)}|${Math.floor(loc.z)}`;
    const t = perm.__typeId;
    const natural = Math.floor(loc.y) === 63 ? "minecraft:grass_block" : Math.floor(loc.y) < 63 ? "minecraft:dirt" : "minecraft:air";
    if (t === natural) world.__edits.delete(k);
    else world.__edits.set(k, t);
    world.__blockWrites++;
  }
  getBlockFromRay(loc, dir, o = {}) {
    finite(loc, "ray");
    finite(dir, "ray dir");
    const L = Math.hypot(dir.x, dir.y, dir.z);
    if (Math.abs(L - 1) > 1e-3) issue(`ray direction not normalised (${L})`);
    const max = o.maxDistance ?? 64;
    for (let d = 0; d <= max; d += 0.2) {
      const x = loc.x + dir.x * d, y = loc.y + dir.y * d, z = loc.z + dir.z * d;
      if (this.__blockAt(x, y, z) !== "minecraft:air") return { block: { location: { x: Math.floor(x), y: Math.floor(y), z: Math.floor(z) } }, face: "Up", faceLocation: { x: 0.5, y: 1, z: 0.5 } };
    }
    if (world.__wall && max > 2 && Math.abs(dir.y) < 0.9) return { block: { location: { x: Math.floor(loc.x + dir.x), y: Math.floor(loc.y), z: Math.floor(loc.z + dir.z) } }, face: "North", faceLocation: { x: 0.5, y: 0.5, z: 0 } };
    return undefined;
  }
  playSound(id, loc) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    finite(loc, "sound");
    this.soundLog.push(id);
  }
  getSkyLightLevel() {
    return 15;
  }
}

const afterNames = ["worldLoad", "itemUse", "playerInteractWithBlock", "entityHitEntity", "entityDie", "itemCompleteUse",
  "projectileHitEntity", "projectileHitBlock", "playerSpawn", "entityHurt", "entitySpawn", "entityLoad", "entityStartSneaking"];
const beforeNames = ["entityHurt", "playerLeave", "itemUse"];

export const world = {
  __entities: new Map(),
  __dyn: new Map(),
  __drops: [],
  __edits: new Map(),
  __blockWrites: 0,
  __time: 6000,
  __dims: {},
  afterEvents: Object.fromEntries(afterNames.map((n) => [n, new Signal(n)])),
  beforeEvents: Object.fromEntries(beforeNames.map((n) => [n, new Signal(n)])),
  getDimension(id) {
    if (!this.__dims[id]) this.__dims[id] = new Dimension(id);
    return this.__dims[id];
  },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player && e.__valid);
  },
  getEntity(id) {
    const e = this.__entities.get(id);
    return e && e.__valid ? e : undefined;
  },
  getDynamicProperty(k) {
    return this.__dyn.get(k);
  },
  setDynamicProperty(k, v) {
    this.__dyn.set(k, v);
  },
  getTimeOfDay() {
    return this.__time;
  },
  getDifficulty() {
    return Difficulty.Normal;
  },
  sendMessage() {},
};

// Ray helper used by the player mock (cone of 6 degrees, like a precise crosshair).
Entity.prototype.getEntitiesFromViewDirection = function (o = {}) {
  const eye = this.getHeadLocation();
  const d = this.getViewDirection();
  const max = o.maxDistance ?? 64;
  const out = [];
  for (const e of this.dimension.__all()) {
    if (e === this) continue;
    const c = { x: e.location.x - eye.x, y: e.location.y + 0.9 - eye.y, z: e.location.z - eye.z };
    const dist = Math.hypot(c.x, c.y, c.z);
    const t = c.x * d.x + c.y * d.y + c.z * d.z;
    if (t <= 0 || dist > max) continue;
    const perp = Math.sqrt(Math.max(0, dist * dist - t * t));
    if (perp < 0.9) out.push({ entity: e, distance: t });
  }
  return out;
};
Entity.prototype.getBlockFromViewDirection = function (o = {}) {
  if (!world.__groundAt) return undefined;
  const eye = this.getHeadLocation();
  const d = this.getViewDirection();
  const dist = Math.min(o.maxDistance ?? 64, world.__groundAt);
  if (dist >= (o.maxDistance ?? 64)) return undefined;
  const p = { x: eye.x + d.x * dist, y: eye.y + d.y * dist, z: eye.z + d.z * dist };
  const b = { x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) };
  return { block: { location: b }, face: "Up", faceLocation: { x: p.x - b.x, y: p.y - b.y, z: p.z - b.z } };
};

export { Dimension, Container };
export const __path = path;
