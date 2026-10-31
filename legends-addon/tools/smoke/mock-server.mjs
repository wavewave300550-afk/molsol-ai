// Strict, minimal emulation of the @minecraft/server API surface used by the add-on.
// Identifiers (effects, particles + their Molang variables, sounds, entity types,
// events, properties and their ranges) are checked against the built packs and the
// vanilla reference, so a wrong id or an out-of-range value fails the smoke test.
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.LEGENDS_MOCK_DATA, "utf8"));
export const __issues = [];
const issue = (m) => __issues.push(m);
export const __stats = { particles: 0, particleById: {}, sounds: 0, titles: 0, actionbars: [], fades: 0, shakes: 0, commands: [] };

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack", "entityExplosion", "fall",
    "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning", "maceSmash", "magic",
    "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom", "soulCampfire",
    "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"].map((k) => [k, k]),
);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const Difficulty = { Easy: "Easy", Hard: "Hard", Normal: "Normal", Peaceful: "Peaceful" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = { Enum: "Enum", String: "String", Integer: "Integer" };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export class EntityHealthComponent {
  static componentId = "minecraft:health";
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
  constructor() {
    this.handlers = [];
  }
  subscribe(fn, opts) {
    this.handlers.push({ fn, opts });
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h.fn !== fn);
  }
  fire(ev, subject) {
    for (const h of this.handlers) {
      const f = h.opts?.entityFilter?.families;
      if (f && subject && !f.every((x) => subject.__families.has(x))) continue;
      h.fn(ev);
    }
    return ev;
  }
}
const commands = {};
const enums = {};
export const system = {
  get currentTick() {
    return currentTick;
  },
  run: (fn) => schedule(fn, 0),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, i),
  clearRun: (id) => timers.delete(id),
  beforeEvents: { startup: new Signal(), shutdown: new Signal() },
  afterEvents: {},
};
export function __startup() {
  system.beforeEvents.startup.fire({
    customCommandRegistry: {
      registerEnum(name, values) {
        if (!/^[a-z_]+:[a-z_]+$/.test(name)) issue(`bad enum name ${name}`);
        enums[name] = values;
      },
      registerCommand(def, fn) {
        if (!/^[a-z_]+:[a-z_]+$/.test(def.name)) issue(`bad command name ${def.name}`);
        for (const p of def.mandatoryParameters ?? []) if (p.type === "Enum" && !enums[p.name]) issue(`command ${def.name} uses unknown enum ${p.name}`);
        commands[def.name] = { def, fn };
      },
    },
  });
}
export const __commands = commands;
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
const SOUNDS = new Set(DATA.sounds);
const ENTITY_DEFS = DATA.entities;
const ITEMS = new Set(DATA.items);
const PARTICLES = DATA.particles; // id -> required variable roots
function finite(v, what) {
  if (!v || !Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) issue(`non-finite vector for ${what}: ${JSON.stringify(v)}`);
}

// ------------------------------------------------------------------ molang map
export class MolangVariableMap {
  constructor() {
    this.vars = new Map();
  }
  setFloat(name, v) {
    if (!name.startsWith("variable.")) issue(`molang var must start with variable.: ${name}`);
    if (!Number.isFinite(v)) issue(`molang ${name} = ${v}`);
    this.vars.set(name, v);
  }
  setColorRGB(name, c) {
    for (const k of ["red", "green", "blue"]) if (!(c[k] >= 0 && c[k] <= 1)) issue(`colour ${name}.${k} out of range: ${c[k]}`);
    for (const s of ["r", "g", "b", "a"]) this.vars.set(`${name}.${s}`, 1);
    this.color = { ...c };
  }
  setColorRGBA(name, c) {
    this.setColorRGB(name, c);
  }
  setSpeedAndDirection(name, speed, dir) {
    finite(dir, "speed dir");
    if (!Number.isFinite(speed)) issue("bad speed");
    for (const s of ["speed", "direction_x", "direction_y", "direction_z"]) this.vars.set(`${name}.${s}`, 1);
  }
  setVector3(name, v) {
    finite(v, name);
    for (const s of ["x", "y", "z"]) this.vars.set(`${name}.${s}`, 1);
  }
}

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.includes(":")) typeId = "minecraft:" + typeId;
    if (!ITEMS.has(typeId) && !typeId.startsWith("minecraft:")) issue(`unknown item ${typeId}`);
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
  addItem(it) {
    const i = this.slots.findIndex((s) => !s);
    if (i < 0) return it;
    this.slots[i] = it;
    return undefined;
  }
}

// ------------------------------------------------------------------ entities
class Health {
  constructor(e, max) {
    this.entity = e;
    this.typeId = "minecraft:health";
    this.currentValue = max;
    this.effectiveMax = max;
  }
  setCurrentValue(v) {
    if (!Number.isFinite(v)) issue(`health set to ${v}`);
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
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
    this.__rot = { x: 0, y: 0 };
    this.__vel = { x: 0, y: 0, z: 0 };
    this.__hurt = [];
    this.__events = [];
    this.__propWrites = 0;
    if (def && def.health) this.__health = new Health(this, def.health);
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
    for (const [k, e] of [...this.__effects]) if (--e.duration <= 0) this.__effects.delete(k);
  }
  getComponent(id) {
    this.__check("getComponent");
    if (id === "minecraft:health") return this.__health;
    if (id === "minecraft:inventory") return this.__inv ? { container: this.__inv } : undefined;
    return undefined;
  }
  getRotation() {
    this.__check("getRotation");
    return { ...this.__rot };
  }
  setRotation(r) {
    this.__check("setRotation");
    if (!Number.isFinite(r.x) || !Number.isFinite(r.y)) issue("bad rotation");
    this.__rot = { ...r };
  }
  teleport(loc, opts = {}) {
    this.__check("teleport");
    finite(loc, `teleport ${this.typeId}`);
    if (opts.rotation) this.setRotation(opts.rotation);
    this.location = { ...loc };
    this.__teleports = (this.__teleports ?? 0) + 1;
  }
  getVelocity() {
    return { ...this.__vel };
  }
  addEffect(type, duration, opts = {}) {
    this.__check("addEffect");
    const id = type.replace(/^minecraft:/, "");
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    if (!Number.isInteger(duration) || duration < 1) issue(`bad effect duration ${duration}`);
    const amp = opts.amplifier ?? 0;
    if (!Number.isInteger(amp) || amp < 0 || amp > 255) issue(`bad amplifier ${amp}`);
    this.__effects.set(id, { typeId: id, duration, amplifier: amp });
  }
  getEffect(t) {
    return this.__effects.get(t.replace(/^minecraft:/, ""));
  }
  applyDamage(amount, opts = {}) {
    this.__check("applyDamage");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage ${amount}`);
    if (opts.cause && !(opts.cause in EntityDamageCause)) issue(`bad cause ${opts.cause}`);
    if (!this.__health) return false;
    const src = { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity };
    const before = world.beforeEvents.entityHurt.fire({ hurtEntity: this, damage: amount, cancel: false, damageSource: src }, this);
    if (before.cancel) return false;
    const dmg = before.damage;
    this.__hurt.push({ amount: dmg, cause: src.cause, by: src.damagingEntity?.typeId, tick: currentTick });
    this.__health.currentValue = Math.max(0, this.__health.currentValue - dmg);
    world.afterEvents.entityHurt.fire({ hurtEntity: this, damage: dmg, damageSource: src }, this);
    if (this.__health.currentValue <= 0) {
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: src });
      if (this instanceof Player) this.__health.currentValue = this.__health.effectiveMax;
      else this.remove();
    }
    return true;
  }
  applyKnockback(h, vert) {
    this.__check("applyKnockback");
    if (!h || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue(`bad knockback ${JSON.stringify(h)} ${vert}`);
    this.location.x += h.x * 0.5;
    this.location.z += h.z * 0.5;
  }
  setOnFire(s) {
    this.__check("setOnFire");
    if (!Number.isFinite(s)) issue("bad fire seconds");
    return true;
  }
  matches(o) {
    if (o.families) return o.families.every((f) => this.__families.has(f));
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
    if ((def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) ||
        (def.type === "float" && (!Number.isFinite(v) || v < def.range[0] || v > def.range[1]))) issue(`property ${k} out of range on ${this.typeId}: ${v}`);
    this.__props.set(k, v);
    this.__propWrites++;
  }
  triggerEvent(name) {
    this.__check("triggerEvent");
    if (!ENTITY_DEFS[this.typeId]?.events.includes(name)) issue(`entity ${this.typeId} has no event ${name}`);
    this.__events.push(name);
  }
  remove() {
    this.__check("remove");
    this.__valid = false;
    world.__entities.delete(this.id);
  }
  kill() {
    this.__check("kill");
    this.applyDamage(1e6, { cause: "override" });
    return true;
  }
  getViewDirection() {
    const yaw = (this.__rot.y * Math.PI) / 180;
    const pitch = (this.__rot.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getBlockFromViewDirection() {
    return undefined;
  }
  runCommand(cmd) {
    __stats.commands.push(cmd);
    if (cmd.startsWith("camerashake")) {
      if (!/^camerashake add @s \d+(\.\d+)? \d+(\.\d+)? positional$/.test(cmd)) issue(`bad camerashake command ${cmd}`);
      __stats.shakes++;
    } else issue(`unexpected command ${cmd}`);
    return { successCount: 1 };
  }
}

class ScreenDisplay {
  constructor(p) {
    this.p = p;
  }
  setActionBar(t) {
    if (typeof t !== "string") issue("actionbar must be a string");
    __stats.actionbars.push({ player: this.p.name, text: t, tick: currentTick });
  }
  setTitle() {
    __stats.titles++;
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__inv = new Container(36);
    this.selectedSlotIndex = 0;
    this.onScreenDisplay = new ScreenDisplay(this);
    this.camera = { fade: () => __stats.fades++ };
    this.__gm = GameMode.Survival;
    this.__ground = true;
  }
  get isOnGround() {
    return this.__ground;
  }
  getGameMode() {
    return this.__gm;
  }
  playSound(id) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
  }
  remove() {
    issue("players cannot be removed");
  }
}

// ------------------------------------------------------------------ dimension / world
class Dimension {
  constructor(id) {
    this.id = id;
    this.ground = 64;
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
    finite(loc, `spawnEntity ${id}`);
    if (!ENTITY_DEFS[id]) throw new Error(`unknown entity type ${id}`);
    return new Entity(id, this, loc);
  }
  spawnItem(item, loc) {
    finite(loc, "spawnItem");
    const e = new Entity("minecraft:item", this, loc);
    e.__item = item;
    return e;
  }
  spawnParticle(id, loc, map) {
    finite(loc, `particle ${id}`);
    const need = PARTICLES[id];
    if (!need) {
      issue(`unknown particle ${id}`);
      return;
    }
    for (const v of need) if (!map || !map.vars.has(v)) issue(`particle ${id} needs ${v} but the script did not set it`);
    __stats.particles++;
    __stats.particleById[id] = (__stats.particleById[id] ?? 0) + 1;
    (world.__particleLog ??= []).push({ id, loc: { ...loc }, tick: currentTick, vars: map ? Object.fromEntries(map.vars) : {}, color: map?.color });
    if (world.__particleLog.length > 4000) world.__particleLog.splice(0, 1000);
  }
  playSound(id, loc) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    finite(loc, "sound");
    __stats.sounds++;
  }
  getBlock(p) {
    if (!Number.isFinite(p.x) || !Number.isFinite(p.y) || !Number.isFinite(p.z)) issue("bad getBlock");
    const solid = p.y < this.ground || (world.__walls ?? []).some((w) => w.x === p.x && w.z === p.z && p.y < w.top);
    return { isAir: !solid, isLiquid: false, typeId: solid ? "minecraft:stone" : "minecraft:air", location: p };
  }
}

const afterNames = ["itemUse", "entityHurt", "entityDie", "playerSpawn"];
const beforeNames = ["entityHurt", "playerLeave"];
export const world = {
  __entities: new Map(),
  __dims: {},
  __difficulty: Difficulty.Normal,
  afterEvents: Object.fromEntries(afterNames.map((n) => [n, new Signal()])),
  beforeEvents: Object.fromEntries(beforeNames.map((n) => [n, new Signal()])),
  getDimension(id) {
    if (!this.__dims[id]) this.__dims[id] = new Dimension(id);
    return this.__dims[id];
  },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player && e.__valid);
  },
  getDifficulty() {
    return this.__difficulty;
  },
  getEntity(id) {
    return this.__entities.get(id);
  },
};
