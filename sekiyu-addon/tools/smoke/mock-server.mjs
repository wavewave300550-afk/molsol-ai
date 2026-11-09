// Strict emulation of the @minecraft/server 2.11.0 surface used by the Sekiyu Sekiyu no Mi scripts
// (adapted from the Jōki add-on mock).
//
// Every identifier handed to the "engine" is checked against the BUILT packs (particles, sounds,
// animations, actor properties, items) or vanilla data (effects), so a typo fails the smoke test
// instead of silently doing nothing in game. Entities get simple vanilla physics (gravity 0.08,
// drag 0.98 / 0.91, ground friction 0.546, fall damage > 3 blocks) on a flat floor at y = 64 with
// optional wall boxes, so dash / jump / kick distances and fall-damage rules are exercised for real.
import fs from "node:fs";
import path from "node:path";

const BUILD = process.env.SEKIYU_BUILD;
const ROOT = process.env.SEKIYU_ROOT;
const BP = path.join(BUILD, "Sekiyu_BP");
const RP = path.join(BUILD, "Sekiyu_RP");
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

const PARTICLES = new Map();
for (const f of walk(path.join(RP, "particles"))) {
  const txt = fs.readFileSync(f, "utf8");
  PARTICLES.set(JSON.parse(txt).particle_effect.description.identifier, txt);
}
const SOUNDS = new Set(Object.keys(readJson(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions));
const ANIMS = new Set();
for (const f of walk(path.join(RP, "animations"))) for (const k of Object.keys(readJson(f).animations)) ANIMS.add(k);
const PLAYER_PROPS = readJson(path.join(BP, "entities", "player.json"))["minecraft:entity"].description.properties;
const CONSTRUCT_DEFS = new Map();
for (const f of walk(path.join(BP, "entities", "sekiyu"))) {
  const e = readJson(f)["minecraft:entity"];
  CONSTRUCT_DEFS.set(e.description.identifier, { families: e.components["minecraft:type_family"].family, properties: e.description.properties ?? {} });
}
const TYPINGS = fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "server", "index.d.ts"), "utf8");
const enumOf = (name) => {
  const body = TYPINGS.slice(TYPINGS.indexOf(`export enum ${name} {`), TYPINGS.indexOf("}", TYPINGS.indexOf(`export enum ${name} {`)));
  return Object.fromEntries([...body.matchAll(/^\s+(\w+) = '(\w+)'/gm)].map((m) => [m[1], m[2]]));
};
const ITEMS = new Set(walk(path.join(BP, "items")).map((f) => readJson(f)["minecraft:item"].description.identifier));
const EFFECTS = new Set([...fs.readFileSync(path.join(ROOT, "node_modules", "@minecraft", "vanilla-data", "lib", "mojang-effect.d.ts"), "utf8").matchAll(/"minecraft:([a-z_]+)"/g)].map((m) => m[1]));
const REF = readJson(path.join(ROOT, "tools", "vanilla", "reference.json"));
const VANILLA_PARTICLES = new Set(REF.particles);

export const __issues = [];
const issue = (m) => __issues.push(m);
export const __stats = { particles: 0, particlesByTick: new Map(), sounds: [], anims: [], commands: [], titles: [] };

// ------------------------------------------------------------------ enums
export const EntityDamageCause = enumOf("EntityDamageCause");
if (Object.keys(EntityDamageCause).length < 30) throw new Error("could not read EntityDamageCause from the typings");
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const CustomCommandParamType = { Enum: "Enum", String: "String", Integer: "Integer" };
export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };

// ------------------------------------------------------------------ scheduler + events
let currentTick = 0;
let nextId = 1;
const timers = new Map();
function schedule(fn, delay, interval) {
  if (typeof fn !== "function") issue("scheduled a non-function");
  const id = nextId++;
  timers.set(id, { fn, due: currentTick + Math.max(0, delay), interval });
  return id;
}
class Signal {
  constructor(name) {
    this.name = name;
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
  beforeEvents: { startup: new Signal("startup") },
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

const finite = (v, what) => {
  if (!v || !Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) issue(`non-finite vector for ${what}: ${JSON.stringify(v)}`);
};
const strip = (id) => id.replace(/^minecraft:/, "");

// ------------------------------------------------------------------ molang + items
export class MolangVariableMap {
  constructor() {
    this.vars = new Map();
  }
  setFloat(name, n) {
    if (!name.startsWith("variable.")) issue(`molang variable without prefix: ${name}`);
    if (!Number.isFinite(n)) issue(`non-finite molang float ${name}`);
    this.vars.set(name, n);
  }
  setVector3(name, v) {
    if (!name.startsWith("variable.")) issue(`molang variable without prefix: ${name}`);
    finite(v, `molang ${name}`);
    this.vars.set(name, v);
  }
  setColorRGB(name, c) {
    this.vars.set(name, c);
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.includes(":")) typeId = "minecraft:" + typeId;
    if (!ITEMS.has(typeId) && !typeId.startsWith("minecraft:")) issue(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
  }
  clone() {
    return new ItemStack(this.typeId, this.amount);
  }
}

class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    if (!Number.isInteger(i) || i < 0 || i >= this.size) throw new Error(`slot ${i} out of range`);
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
  count(typeId) {
    return this.slots.filter((s) => s && s.typeId === typeId).reduce((a, s) => a + s.amount, 0);
  }
}

// ------------------------------------------------------------------ entities
export class EntityHealthComponent {
  static componentId = "minecraft:health";
  constructor(max) {
    this.typeId = "minecraft:health";
    this.currentValue = max;
    this.effectiveMax = max;
    this.defaultValue = max;
  }
  setCurrentValue(v) {
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
}

const GROUND = 64;
const MOB_DEFS = {
  "minecraft:zombie": { families: ["zombie", "undead", "monster", "mob"], health: 20 },
  "minecraft:villager_v2": { families: ["villager", "mob"], health: 20 },
  "minecraft:wolf": { families: ["wolf", "mob"], health: 20, tamed: true },
  "minecraft:item": { families: ["inanimate"] },
  "minecraft:drowned": { families: ["zombie", "undead", "monster", "mob"], health: 20 },
};
for (const [id, d] of CONSTRUCT_DEFS) MOB_DEFS[id] = { families: d.families, health: 100, construct: true, properties: d.properties };

export class Entity {
  constructor(typeId, dimension, location) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.__vel = { x: 0, y: 0, z: 0 };
    this.__valid = true;
    this.__effects = new Map();
    this.__dyn = new Map();
    this.__props = new Map();
    this.__fire = 0;
    this.__hurt = [];
    this.__rot = { x: 0, y: 0 };
    this.__fallStart = location.y;
    this.isSneaking = false;
    const def = MOB_DEFS[typeId];
    this.__families = new Set(def ? def.families : []);
    this.__health = def?.health ? new EntityHealthComponent(def.health) : undefined;
    this.__tamed = !!def?.tamed;
    if (def?.properties) for (const [k, pd] of Object.entries(def.properties)) this.__props.set(k, pd.default);
    this.__construct = !!def?.construct;
    world.__entities.set(this.id, this);
  }
  get isValid() {
    return this.__valid;
  }
  __check(what) {
    if (!this.__valid) throw new Error(`InvalidEntityError: ${what} on removed ${this.typeId}`);
  }
  get isInWater() {
    return world.__waterAt(this.location);
  }
  set isInWater(v) {}
  get isOnGround() {
    return this.location.y <= GROUND + 1e-6 && this.__vel.y <= 0;
  }
  get isFalling() {
    return !this.isOnGround && this.__vel.y < 0;
  }
  __step() {
    if (!this.__valid) return;
    for (const [k, e] of [...this.__effects]) {
      e.duration--;
      if (e.duration <= 0) this.__effects.delete(k);
    }
    if (this.__fire > 0) this.__fire--;
    if (this.typeId === "minecraft:item" || this.__construct) return;
    // vanilla-like physics
    const wasAir = !this.isOnGround;
    const next = { x: this.location.x + this.__vel.x, y: this.location.y + this.__vel.y, z: this.location.z + this.__vel.z };
    if (world.__solidAt(next)) {
      // wall: stop horizontal motion (no tunnelling)
      next.x = this.location.x;
      next.z = this.location.z;
      this.__vel.x = 0;
      this.__vel.z = 0;
    }
    this.location = next;
    if (this.location.y <= GROUND) {
      this.location.y = GROUND;
      if (wasAir) {
        const fell = this.__fallStart - GROUND;
        if (fell > 3 && this.__health) this.applyDamage(Math.floor(fell - 3), { cause: EntityDamageCause.fall });
        world.__landings.push({ id: this.id, fell });
      }
      this.__vel.y = 0;
      this.__fallStart = GROUND;
    } else {
      this.__fallStart = Math.max(this.__fallStart, this.location.y);
    }
    const ground = this.isOnGround;
    this.__vel.x *= ground ? 0.546 : 0.91;
    this.__vel.z *= ground ? 0.546 : 0.91;
    if (!ground) this.__vel.y = (this.__vel.y - 0.08) * 0.98;
    if (Math.abs(this.__vel.x) < 0.003) this.__vel.x = 0;
    if (Math.abs(this.__vel.z) < 0.003) this.__vel.z = 0;
  }
  getComponent(id) {
    this.__check("getComponent");
    if (id === "minecraft:health") return this.__health;
    if (id === "minecraft:inventory") return this.__inv ? { container: this.__inv } : undefined;
    if (id === "minecraft:is_tamed") return this.__tamed ? {} : undefined;
    if (id === "minecraft:equippable") return { getEquipment: (slot) => (slot === EquipmentSlot.Offhand ? this.__offhand : slot === EquipmentSlot.Mainhand ? this.__mainhand : undefined) };
    if (id === "minecraft:onfire") return this.__fire > 0 ? { onFireTicksRemaining: this.__fire } : undefined;
    return undefined;
  }
  addEffect(type, duration, opts = {}) {
    this.__check("addEffect");
    const id = strip(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    if (!Number.isInteger(duration) || duration < 1) issue(`bad effect duration ${duration} for ${type}`);
    const amp = opts.amplifier ?? 0;
    if (!Number.isInteger(amp) || amp < 0 || amp > 255) issue(`bad amplifier ${amp}`);
    const cur = this.__effects.get(id);
    if (cur && cur.amplifier > amp) return cur; // vanilla: weaker effects do not override stronger ones
    this.__effects.set(id, { typeId: id, duration, amplifier: amp });
    return this.__effects.get(id);
  }
  getEffect(type) {
    this.__check("getEffect");
    const id = strip(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    return this.__effects.get(id);
  }
  removeEffect(type) {
    this.__check("removeEffect");
    const id = strip(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    return this.__effects.delete(id);
  }
  applyDamage(amount, opts = {}) {
    this.__check("applyDamage");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage ${amount}`);
    if (opts.cause && !(opts.cause in EntityDamageCause)) issue(`bad cause ${opts.cause}`);
    if (!this.__health) return false;
    const ev = world.beforeEvents.entityHurt.fire({ hurtEntity: this, damage: amount, cancel: false, damageSource: { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity, damagingProjectile: opts.damagingProjectile } });
    if (ev.cancel) return false;
    if (this.__construct) issue(`damaged a construct ${this.typeId}`);
    this.__hurt.push({ amount: ev.damage, cause: opts.cause, by: opts.damagingEntity?.id, tick: currentTick });
    this.__health.currentValue -= ev.damage;
    if (this.__health.currentValue <= 0) {
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: { cause: opts.cause, damagingEntity: opts.damagingEntity } });
      if (!(this instanceof Player)) this.remove();
      else this.__health.currentValue = this.__health.effectiveMax;
    }
    return true;
  }
  applyKnockback(h, vertical) {
    this.__check("applyKnockback");
    if (!h || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vertical)) issue(`bad knockback ${JSON.stringify(h)} ${vertical}`);
    if (Math.hypot(h.x, h.z) > 6 || Math.abs(vertical) > 3) issue(`absurd knockback ${JSON.stringify(h)} ${vertical}`);
    this.__vel = { x: h.x, y: vertical, z: h.z };
    this.__knocks = (this.__knocks ?? 0) + 1;
  }
  getVelocity() {
    this.__check("getVelocity");
    return { ...this.__vel };
  }
  applyImpulse() {
    if (this instanceof Player) throw new Error("UnsupportedFunctionalityError: applyImpulse on players");
  }
  setOnFire(seconds, useEffects) {
    this.__check("setOnFire");
    if (typeof useEffects !== "boolean" && useEffects !== undefined) issue("setOnFire useEffects must be boolean");
    this.__fire = seconds * 20;
    return true;
  }
  extinguishFire(useEffects) {
    this.__check("extinguishFire");
    if (typeof useEffects !== "boolean" && useEffects !== undefined) issue("extinguishFire useEffects must be boolean");
    this.__fire = 0;
    return true;
  }
  playAnimation(name, opts = {}) {
    this.__check("playAnimation");
    if (!ANIMS.has(name)) issue(`unknown animation ${name}`);
    if (opts.blendOutTime !== undefined && !(opts.blendOutTime >= 0)) issue("bad blendOutTime");
    __stats.anims.push(name);
    if (!(this instanceof Player) && !this.__construct) issue(`playAnimation on ${this.typeId}`);
  }
  getRotation() {
    return { ...this.__rot };
  }
  teleport(loc, opts = {}) {
    this.__check("teleport");
    finite(loc, `teleport ${this.typeId}`);
    if (loc.y < -64 || loc.y > 320) issue(`teleport outside the world: ${JSON.stringify(loc)}`);
    if (!this.__construct && world.__solidAt({ x: loc.x, y: loc.y + 0.5, z: loc.z })) issue(`teleported ${this.typeId} into a solid block`);
    if (opts.rotation) {
      if (!Number.isFinite(opts.rotation.x) || !Number.isFinite(opts.rotation.y)) issue("bad teleport rotation");
      this.__rot = { ...opts.rotation };
    }
    this.location = { ...loc };
    if (opts.keepVelocity === false) this.__vel = { x: 0, y: 0, z: 0 };
    this.__teleports = (this.__teleports ?? 0) + 1;
  }
  setRotation(r) {
    this.__rot = { ...r };
  }
  getViewDirection() {
    const yaw = (this.__rot.y * Math.PI) / 180;
    const pitch = (this.__rot.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getDynamicProperty(k) {
    this.__check("getDynamicProperty");
    return this.__dyn.get(k);
  }
  setDynamicProperty(k, v) {
    this.__check("setDynamicProperty");
    if (v !== undefined && !["boolean", "number", "string"].includes(typeof v)) issue(`bad dynamic property value for ${k}`);
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
    const def = this instanceof Player ? PLAYER_PROPS[k] : MOB_DEFS[this.typeId]?.properties?.[k];
    if (!def) throw new Error(`property ${k} is not defined on ${this.typeId}`);
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) issue(`property ${k} out of range: ${v}`);
    if (def.type === "bool" && typeof v !== "boolean") issue(`property ${k} must be boolean, got ${v}`);
    if (def.type === "float" && (!Number.isFinite(v) || v < def.range[0] || v > def.range[1])) issue(`property ${k} out of range: ${v}`);
    this.__props.set(k, v);
    this.__propWrites = (this.__propWrites ?? 0) + 1;
  }
  getEntitiesFromViewDirection(o = {}) {
    const eye = this.getHeadLocation();
    const d = this.getViewDirection();
    const max = o.maxDistance ?? 64;
    const out = [];
    for (const e of this.dimension.__all()) {
      if (e === this || e.typeId === "minecraft:item") continue;
      const c = { x: e.location.x - eye.x, y: e.location.y + 0.9 - eye.y, z: e.location.z - eye.z };
      const dist = Math.hypot(c.x, c.y, c.z);
      const t = c.x * d.x + c.y * d.y + c.z * d.z;
      if (t <= 0 || dist > max) continue;
      const perp = Math.sqrt(Math.max(0, dist * dist - t * t));
      if (perp < 0.9) out.push({ entity: e, distance: t });
    }
    return out;
  }
  remove() {
    this.__check("remove");
    this.__valid = false;
    world.__entities.delete(this.id);
  }
  getGameMode() {
    return this.__gm ?? GameMode.Survival;
  }
}

class ScreenDisplay {
  constructor() {
    this.actionbar = "";
    this.titles = [];
  }
  setActionBar(t) {
    if (typeof t !== "string") issue("actionbar must be a string");
    if (/%(?! |$)/.test(t)) issue(`actionbar contains a formatter-like % token: ${JSON.stringify(t)}`);
    this.actionbar = t;
  }
  setTitle(t, o) {
    this.titles.push({ t, o });
    __stats.titles.push(o?.subtitle ?? t);
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__inv = new Container(36);
    this.__health = new EntityHealthComponent(20);
    for (const [k, d] of Object.entries(PLAYER_PROPS)) this.__props.set(k, d.default);
    this.selectedSlotIndex = 0;
    this.onScreenDisplay = new ScreenDisplay();
    this.messages = [];
    this.sounds = [];
    this.commandPermissionLevel = CommandPermissionLevel.Admin;
    this.__families.add("player");
  }
  sendMessage(m) {
    this.messages.push(typeof m === "string" ? m : JSON.stringify(m));
  }
  playSound(id, opts) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    this.sounds.push(id);
  }
  spawnParticle(id, loc, vars) {
    this.dimension.spawnParticle(id, loc, vars);
  }
  runCommand(cmd) {
    __stats.commands.push(cmd);
    if (/^fog @s push sekiyu:inferno_fog sekiyu_inferno$/.test(cmd)) {
      this.__fog = true;
      return { successCount: 1 };
    }
    if (/^fog @s remove sekiyu_inferno$/.test(cmd)) {
      this.__fog = false;
      return { successCount: 1 };
    }
    if (!/^camerashake add @s \d+\.\d{2} \d+\.\d{2} positional$/.test(cmd)) issue(`unexpected command: ${cmd}`);
    const m = cmd.match(/add @s ([\d.]+) ([\d.]+)/);
    if (m && (+m[1] > 4 || +m[1] <= 0 || +m[2] <= 0)) issue(`camerashake out of range: ${cmd}`);
    return { successCount: 1 };
  }
}

// ------------------------------------------------------------------ dimension / world
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
    if (o.families) list = list.filter((e) => o.families.every((f) => e.__families.has(f)));
    if (o.excludeFamilies) list = list.filter((e) => !o.excludeFamilies.some((f) => e.__families.has(f)));
    if (o.location && o.maxDistance !== undefined) {
      finite(o.location, "getEntities");
      if (!(o.maxDistance > 0)) issue(`bad maxDistance ${o.maxDistance}`);
      list = list.filter((e) => Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z) <= o.maxDistance);
    }
    return list;
  }
  getPlayers(o = {}) {
    return this.getEntities(o).filter((e) => e instanceof Player);
  }
  get heightRange() {
    return { min: -64, max: 320 };
  }
  spawnEntity(id, loc) {
    finite(loc, "spawnEntity");
    if (!MOB_DEFS[id]) throw new Error(`unknown entity ${id}`);
    const e = new Entity(id, this, loc);
    if (e.__construct) world.__constructSpawns++;
    return e;
  }
  getBlock(loc) {
    finite(loc, "getBlock");
    const p = { x: Math.floor(loc.x) + 0.5, y: Math.floor(loc.y) + 0.5, z: Math.floor(loc.z) + 0.5 };
    const b = { x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) };
    if (world.__waterAt(p)) return { location: b, typeId: "minecraft:water", isAir: false, isLiquid: true };
    if (p.y < GROUND || world.__solidAt(p)) return { location: b, typeId: world.__blockType(p) ?? "minecraft:stone", isAir: false, isLiquid: false };
    return { location: b, typeId: "minecraft:air", isAir: true, isLiquid: false };
  }
  spawnItem(item, loc) {
    finite(loc, "spawnItem");
    const e = new Entity("minecraft:item", this, loc);
    e.__item = item;
    return e;
  }
  spawnParticle(id, loc, vars) {
    finite(loc, `particle ${id}`);
    const txt = PARTICLES.get(id);
    if (!txt && !VANILLA_PARTICLES.has(id)) issue(`unknown particle ${id}`);
    if (vars && txt) {
      if (!(vars instanceof MolangVariableMap)) issue("molang vars must be a MolangVariableMap");
      for (const name of vars.vars.keys()) if (!txt.includes(name)) issue(`particle ${id} ignores molang ${name}`);
    }
    __stats.particles++;
    __stats.particlesByTick.set(currentTick, (__stats.particlesByTick.get(currentTick) ?? 0) + 1);
  }
  playSound(id, loc, opts = {}) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    finite(loc, `sound ${id}`);
    if (opts.volume !== undefined && !(opts.volume > 0)) issue(`bad volume for ${id}`);
    __stats.sounds.push(id);
  }
  getBlockFromRay(origin, dir, opts = {}) {
    finite(origin, "ray origin");
    finite(dir, "ray dir");
    const max = opts.maxDistance ?? 64;
    let best;
    for (let t = 0; t <= max; t += 0.05) {
      const p = { x: origin.x + dir.x * t, y: origin.y + dir.y * t, z: origin.z + dir.z * t };
      const water = opts.includeLiquidBlocks && world.__waterAt(p);
      if (water || p.y < GROUND || world.__solidAt(p)) {
        const b = { x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) };
        const typeId = water ? "minecraft:water" : world.__blockType(p) ?? "minecraft:stone";
        best = { block: { location: b, typeId }, face: "Up", faceLocation: { x: p.x - b.x, y: p.y - b.y, z: p.z - b.z } };
        break;
      }
    }
    return best;
  }
}

const afterNames = ["worldLoad", "itemUse", "itemStartUse", "itemCompleteUse", "playerInteractWithBlock", "entityHitEntity", "entityDie", "playerSpawn"];
const beforeNames = ["entityHurt", "playerLeave", "itemUse"];

export const world = {
  __entities: new Map(),
  __dyn: new Map(),
  __walls: [],
  __landings: [],
  __dims: {},
  __water: [],
  __constructSpawns: 0,
  __solidAt(p) {
    return this.__walls.some((w) => p.x >= w.min.x && p.x <= w.max.x && p.y >= w.min.y && p.y <= w.max.y && p.z >= w.min.z && p.z <= w.max.z);
  },
  __blockType(p) {
    const w = this.__walls.find((w) => p.x >= w.min.x && p.x <= w.max.x && p.y >= w.min.y && p.y <= w.max.y && p.z >= w.min.z && p.z <= w.max.z);
    return w?.typeId;
  },
  __waterAt(p) {
    return this.__water.some((w) => p.x >= w.min.x && p.x <= w.max.x && p.y >= w.min.y && p.y <= w.max.y && p.z >= w.min.z && p.z <= w.max.z);
  },
  getEntity(id) {
    const e = this.__entities.get(id);
    return e && e.__valid ? e : undefined;
  },
  afterEvents: Object.fromEntries(afterNames.map((n) => [n, new Signal(n)])),
  beforeEvents: Object.fromEntries(beforeNames.map((n) => [n, new Signal(n)])),
  getDimension(id) {
    if (!this.__dims[id]) this.__dims[id] = new Dimension(id);
    return this.__dims[id];
  },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player && e.__valid);
  },
  getDynamicProperty(k) {
    return this.__dyn.get(k);
  },
  setDynamicProperty(k, v) {
    this.__dyn.set(k, v);
  },
  sendMessage(m) {
    this.__broadcast = (this.__broadcast ?? []).concat([m]);
  },
};

export { Container, Dimension };
