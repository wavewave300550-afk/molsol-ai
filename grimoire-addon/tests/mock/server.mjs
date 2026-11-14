// Minimal behavioural mock of @minecraft/server for headless spell tests.
// It is deliberately strict about identifiers: spawning an unknown grimoire entity, setting an
// undefined entity property / out-of-range value, or using an unregistered particle / sound id
// is recorded in `problems` so script <-> asset cross references are verified without the game.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const readJson = (p, d) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return d; } };

export const assets = { actors: {}, particles: new Set(), sounds: new Set(), items: new Set() };
export function loadAssets() {
  assets.actors = {};
  const edir = path.join(ROOT, "behavior_packs/grimoire_bp/entities");
  if (fs.existsSync(edir)) for (const f of fs.readdirSync(edir)) {
    const j = readJson(path.join(edir, f), null);
    const d = j?.["minecraft:entity"]?.description;
    if (d) assets.actors[d.identifier] = d.properties ?? {};
  }
  assets.particles = new Set();
  const pdir = path.join(ROOT, "resource_packs/grimoire_rp/particles");
  if (fs.existsSync(pdir)) for (const f of fs.readdirSync(pdir)) {
    const j = readJson(path.join(pdir, f), null);
    const id = j?.particle_effect?.description?.identifier;
    if (id) assets.particles.add(id);
  }
  const sd = readJson(path.join(ROOT, "resource_packs/grimoire_rp/sounds/sound_definitions.json"), {});
  assets.sounds = new Set(Object.keys(sd.sound_definitions ?? {}));
  assets.items = new Set();
  const idir = path.join(ROOT, "behavior_packs/grimoire_bp/items");
  if (fs.existsSync(idir)) for (const f of fs.readdirSync(idir)) {
    const id = readJson(path.join(idir, f), null)?.["minecraft:item"]?.description?.identifier;
    if (id) assets.items.add(id);
  }
}

export const problems = [];
export const stats = { particles: 0, sounds: 0, spawned: {}, damage: 0, heals: 0, peakEntities: 0, effects: 0, knockbacks: 0 };
const problem = (m) => { if (!problems.includes(m)) problems.push(m); };
export const strict = { particles: true, sounds: true };

class Signal {
  constructor() { this.subs = []; }
  subscribe(fn) { this.subs.push(fn); return fn; }
  unsubscribe(fn) { this.subs = this.subs.filter((f) => f !== fn); }
  emit(ev) { for (const fn of [...this.subs]) fn(ev); }
}

export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };
export const EntityDamageCause = new Proxy({}, { get: (_, k) => k });
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const CustomCommandParamType = new Proxy({}, { get: (_, k) => k });
export const InputButton = { Jump: "Jump", Sneak: "Sneak" };
export const ButtonState = { Pressed: "Pressed", Released: "Released" };
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };
export const Direction = { Up: "Up", Down: "Down", North: "North", South: "South", East: "East", West: "West" };
export class MolangVariableMap { setColorRGBA() {} setColorRGB() {} setFloat() {} setVector3() {} setSpeedAndDirection() {} }
export class ItemStack {
  constructor(typeId, amount = 1) { this.typeId = typeof typeId === "string" ? typeId : typeId.id; this.amount = amount; }
}

let nextId = 1;
const GROUND = 64;
/** Terrain height (first air y) per column.  Flat by default; setTerrain() makes hills for placement tests. */
let terrain = () => GROUND;
export function setTerrain(fn) { terrain = fn ?? (() => GROUND); }
export function heightAt(x, z) { return terrain(Math.floor(x), Math.floor(z)); }

export class Entity {
  constructor(dim, typeId, loc) {
    this.id = `e${nextId++}`; this.typeId = typeId; this.dimension = dim; this.location = { ...loc };
    this.isValid = true; this.tags = new Set(); this.props = {}; this.dyn = new Map(); this.families = [];
    this.health = 20; this.maxHealth = 20; this.rotation = { x: 0, y: 0 }; this.effects = new Map(); this.velocity = { x: 0, y: 0, z: 0 };
    this.nameTag = ""; this.hurtLog = [];
  }
  getComponent(id) {
    const self = this;
    if (id === "minecraft:health" || id === "health") return {
      get currentValue() { return self.health; }, get effectiveMax() { return self.maxHealth; }, effectiveMin: 0, defaultValue: self.maxHealth,
      setCurrentValue(v) { if (v > self.health) stats.heals += v - self.health; self.health = Math.max(0, Math.min(self.maxHealth, v)); return true; },
      resetToMaxValue() { self.health = self.maxHealth; },
    };
    if (id === "minecraft:projectile" || id === "projectile") return this.projectile;
    return undefined;
  }
  matches(o = {}) {
    if (o.families && !o.families.every((f) => this.families.includes(f))) return false;
    if (o.type && o.type !== this.typeId) return false;
    if (o.tags && !o.tags.every((t) => this.tags.has(t))) return false;
    return true;
  }
  hasTag(t) { return this.tags.has(t); }
  addTag(t) { this.tags.add(t); return true; }
  removeTag(t) { return this.tags.delete(t); }
  getTags() { return [...this.tags]; }
  setProperty(name, value) {
    const defs = assets.actors[this.typeId];
    if (defs) {
      const d = defs[name];
      if (!d) { problem(`${this.typeId}: property ${name} is not defined`); throw new Error(`no property ${name}`); }
      if ((d.type === "int" || d.type === "float") && (typeof value !== "number" || value < d.range[0] || value > d.range[1])) {
        problem(`${this.typeId}: ${name}=${value} outside range ${JSON.stringify(d.range)}`); throw new Error("range");
      }
      if (d.type === "int" && !Number.isInteger(value)) { problem(`${this.typeId}: ${name}=${value} is not an integer`); throw new Error("int"); }
    }
    this.props[name] = value;
  }
  getProperty(name) { return this.props[name]; }
  getDynamicProperty(k) { return this.dyn.get(k); }
  setDynamicProperty(k, v) { if (v === undefined) this.dyn.delete(k); else this.dyn.set(k, v); }
  teleport(loc, o = {}) {
    if (!this.isValid) throw new Error("invalid entity");
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) { problem(`${this.typeId}: teleport to non-finite ${JSON.stringify(loc)}`); throw new Error("NaN teleport"); }
    if (this.dimension.outside(loc)) { problem(`${this.typeId}: teleport outside the world to y=${loc.y.toFixed(2)}`); throw new Error("LocationOutOfWorldBoundariesError"); }
    this.location = { x: loc.x, y: loc.y, z: loc.z };
    if (o.rotation) this.rotation = { ...o.rotation };
  }
  tryTeleport(loc, o) { this.teleport(loc, o); return true; }
  setRotation(r) { if (!Number.isFinite(r.y)) problem(`${this.typeId}: non-finite rotation`); this.rotation = { ...r }; }
  getRotation() { return { ...this.rotation }; }
  getVelocity() { return { ...this.velocity }; }
  clearVelocity() { this.velocity = { x: 0, y: 0, z: 0 }; }
  getHeadLocation() { return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z }; }
  getViewDirection() {
    const yaw = (this.rotation.y * Math.PI) / 180, pitch = (this.rotation.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  applyDamage(amount, o = {}) {
    if (!this.isValid || this.health <= 0) return false;
    if (!Number.isFinite(amount)) { problem(`${this.typeId}: non-finite damage`); return false; }
    if (this.invulnerable) return false;
    const ev = { cancel: false, damage: amount, hurtEntity: this, damageSource: { cause: o.cause, damagingEntity: o.damagingEntity } };
    world.beforeEvents.entityHurt.emit(ev);
    if (ev.cancel || ev.damage <= 0) return false;
    this.health = Math.max(0, this.health - ev.damage);
    this.hurtLog.push({ tick: system.currentTick, amount: ev.damage, by: o.damagingEntity?.id });
    stats.damage += ev.damage;
    world.afterEvents.entityHurt.emit({ hurtEntity: this, damage: ev.damage, damageSource: ev.damageSource });
    if (this.health <= 0) {
      world.afterEvents.entityDie.emit({ deadEntity: this, damageSource: ev.damageSource });
      if (this.typeId !== "minecraft:player") this.remove();
    }
    return true;
  }
  applyKnockback(h, v) {
    if (typeof h !== "object" || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(v)) { problem(`${this.typeId}: bad knockback args`); throw new Error("knockback"); }
    stats.knockbacks++;
    this.location = { x: this.location.x + h.x * 0.6, y: this.location.y, z: this.location.z + h.z * 0.6 };
  }
  applyImpulse(vv) { if (this.typeId === "minecraft:player") throw new Error("impulse on player"); stats.knockbacks++; }
  addEffect(id, ticks, o = {}) {
    if (!Number.isInteger(ticks) || ticks < 1 || ticks > 20000000) { problem(`effect ${id}: bad duration ${ticks}`); throw new Error("duration"); }
    if (o.amplifier !== undefined && (!Number.isInteger(o.amplifier) || o.amplifier < 0 || o.amplifier > 255)) { problem(`effect ${id}: bad amplifier ${o.amplifier}`); throw new Error("amp"); }
    const known = ["slowness", "speed", "resistance", "regeneration", "absorption", "weakness", "levitation", "slow_falling", "blindness", "darkness",
      "nausea", "instant_health", "strength", "fire_resistance", "glowing", "wither", "poison", "mining_fatigue", "jump_boost", "night_vision", "invisibility", "health_boost", "saturation"];
    const bare = String(id).replace("minecraft:", "");
    if (!known.includes(bare)) problem(`unknown effect id ${id}`);
    stats.effects++;
    this.effects.set(bare, { until: system.currentTick + ticks, amplifier: o.amplifier ?? 0 });
    return {};
  }
  removeEffect(id) { return this.effects.delete(String(id).replace("minecraft:", "")); }
  getEffect(id) { return this.effects.get(String(id).replace("minecraft:", "")); }
  playAnimation() {}
  triggerEvent() {}
  extinguishFire() { return true; }
  setOnFire() { return true; }
  kill() { this.health = 0; this.remove(); return true; }
  remove() {
    if (!this.isValid) return;
    this.isValid = false;
    this.dimension.entities.delete(this);
  }
}

export class Player extends Entity {
  constructor(dim, name, loc) {
    super(dim, "minecraft:player", loc);
    this.name = name; this.families = ["player"]; this.isSneaking = false; this.selectedSlotIndex = 0;
    this.hotbar = new Array(9).fill(undefined); this.actionBar = ""; this.messages = [];
    const self = this;
    this.onScreenDisplay = { setActionBar(t) { self.actionBar = typeof t === "string" ? t : JSON.stringify(t); }, setTitle() {}, updateSubtitle() {} };
    this.inputInfo = { getButtonState: () => ButtonState.Released };
    this.playerPermissionLevel = 2;
  }
  getComponent(id) {
    const self = this;
    if (id === "minecraft:equippable" || id === "equippable") return {
      getEquipment(slot) { return slot === EquipmentSlot.Mainhand ? self.hotbar[self.selectedSlotIndex] : undefined; },
      setEquipment(slot, item) { if (slot === EquipmentSlot.Mainhand) self.hotbar[self.selectedSlotIndex] = item; return true; },
    };
    if (id === "minecraft:inventory" || id === "inventory") return { container: {
      size: 9, addItem(it) { const i = self.hotbar.findIndex((x) => !x); if (i >= 0) self.hotbar[i] = it; return undefined; },
      getItem(i) { return self.hotbar[i]; }, setItem(i, it) { self.hotbar[i] = it; },
    } };
    return super.getComponent(id);
  }
  sendMessage(m) { this.messages.push(typeof m === "string" ? m : JSON.stringify(m)); }
  playSound(id) { checkSound(id); return {}; }
  getEntitiesFromViewDirection(o = {}) {
    const head = this.getHeadLocation(), d = this.getViewDirection(), out = [];
    for (const e of this.dimension.entities) {
      if (e === this || !e.isValid) continue;
      if (o.excludeFamilies && o.excludeFamilies.some((f) => e.families.includes(f))) continue;
      const rel = { x: e.location.x - head.x, y: e.location.y + 0.9 - head.y, z: e.location.z - head.z };
      const t = rel.x * d.x + rel.y * d.y + rel.z * d.z;
      if (t < 0 || t > (o.maxDistance ?? 64)) continue;
      const px = rel.x - d.x * t, py = rel.y - d.y * t, pz = rel.z - d.z * t;
      if (Math.hypot(px, py, pz) < 1.0) out.push({ entity: e, distance: t });
    }
    return out.sort((a, b) => a.distance - b.distance);
  }
  getBlockFromViewDirection(o = {}) { return this.dimension.getBlockFromRay(this.getHeadLocation(), this.getViewDirection(), o); }
  startItemCooldown() {}
}

class Block {
  constructor(dim, x, y, z) { this.dimension = dim; this.location = { x, y, z }; this.x = x; this.y = y; this.z = z; }
  get typeId() { return this.dimension.blockAt(this.x, this.y, this.z); }
  get isAir() { return this.typeId === "minecraft:air"; }
  get isValid() { return true; }
  get isLiquid() { return false; }
  get isSolid() { return !this.isAir; }
  setType(t) { this.dimension.setBlockType(this.location, t); }
  matches(n) { return this.typeId === n; }
  above(n = 1) { return new Block(this.dimension, this.x, this.y + n, this.z); }
  below(n = 1) { return new Block(this.dimension, this.x, this.y - n, this.z); }
}

export class Dimension {
  constructor(id) { this.id = id; this.entities = new Set(); this.blocks = new Map(); this.heightRange = { min: -64, max: 320 }; }
  blockAt(x, y, z) {
    const k = `${x},${y},${z}`;
    if (this.blocks.has(k)) return this.blocks.get(k);
    return y < terrain(x, z) ? "minecraft:stone" : "minecraft:air";
  }
  getBlock(loc) {
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) { problem("getBlock with non-finite location"); return undefined; }
    return new Block(this, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
  }
  setBlockType(loc, t) {
    const id = typeof t === "string" ? t : t.id;
    const k = `${Math.floor(loc.x)},${Math.floor(loc.y)},${Math.floor(loc.z)}`;
    if (Math.floor(loc.y) < terrain(Math.floor(loc.x), Math.floor(loc.z)) && id !== "minecraft:stone") problem(`world terrain modified at ${k} -> ${id}`);
    if (id === "minecraft:air") this.blocks.delete(k); else this.blocks.set(k, id);
  }
  getBlockFromRay(loc, dir, o = {}) {
    const max = o.maxDistance ?? 64;
    for (let t = 0; t <= max; t += 0.25) {
      const p = { x: loc.x + dir.x * t, y: loc.y + dir.y * t, z: loc.z + dir.z * t };
      const b = this.getBlock(p);
      if (b && !b.isAir && b.typeId !== "minecraft:light_block_15" && !(o.excludeTypes ?? []).includes(b.typeId)) {
        return { block: b, face: "Up", faceLocation: { x: p.x - Math.floor(p.x), y: 1, z: p.z - Math.floor(p.z) } };
      }
    }
    return undefined;
  }
  getTopmostBlock(xz) { return new Block(this, Math.floor(xz.x), terrain(Math.floor(xz.x), Math.floor(xz.z)) - 1, Math.floor(xz.z)); }
  outside(loc) { return loc.y < this.heightRange.min || loc.y >= this.heightRange.max; }
  spawnEntity(typeId, loc, o = {}) {
    const id = typeof typeId === "string" ? typeId : typeId.id;
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) { problem(`spawn ${id} at non-finite location`); throw new Error("NaN spawn"); }
    if (this.outside(loc)) { problem(`spawn ${id} outside the world at y=${loc.y.toFixed(2)}`); throw new Error("LocationOutOfWorldBoundariesError"); }
    if (id.startsWith("grimoire:") && !assets.actors[id]) { problem(`spawnEntity: unknown entity ${id}`); throw new Error(`unknown entity ${id}`); }
    const e = new Entity(this, id, loc);
    if (id.startsWith("grimoire:")) { e.families = ["grimoire_construct", "inanimate"]; e.invulnerable = true; }
    if (o.initialRotation !== undefined) e.rotation.y = o.initialRotation;
    this.entities.add(e);
    stats.spawned[id] = (stats.spawned[id] ?? 0) + 1;
    stats.peakEntities = Math.max(stats.peakEntities, [...this.entities].filter((x) => x.typeId.startsWith("grimoire:")).length);
    return e;
  }
  getEntities(o = {}) {
    const out = [];
    for (const e of this.entities) {
      if (!e.isValid) continue;
      if (o.type && e.typeId !== o.type) continue;
      if (o.excludeTypes && o.excludeTypes.includes(e.typeId)) continue;
      if (o.families && !o.families.every((f) => e.families.includes(f))) continue;
      if (o.excludeFamilies && o.excludeFamilies.some((f) => e.families.includes(f))) continue;
      if (o.tags && !o.tags.every((t) => e.tags.has(t))) continue;
      if (o.excludeTags && o.excludeTags.some((t) => e.tags.has(t))) continue;
      if (o.location && o.maxDistance !== undefined) {
        const d = Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z);
        if (d > o.maxDistance || (o.minDistance !== undefined && d < o.minDistance)) continue;
      }
      out.push(e);
    }
    return o.closest ? out.slice(0, o.closest) : out;
  }
  getPlayers(o = {}) { return this.getEntities({ ...o, type: "minecraft:player" }); }
  spawnParticle(id, loc) {
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) { problem(`particle ${id} at non-finite location`); throw new Error("NaN particle"); }
    if (this.outside(loc)) { problem(`particle ${id} outside the world at y=${loc.y.toFixed(2)}`); throw new Error("LocationOutOfWorldBoundariesError"); }
    if (strict.particles && id.startsWith("grimoire:") && !assets.particles.has(id)) problem(`spawnParticle: unknown particle ${id}`);
    stats.particles++;
  }
  playSound(id, loc, o = {}) {
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) { problem(`sound ${id} at non-finite location`); throw new Error("NaN sound"); }
    checkSound(id);
    return {};
  }
  runCommand() { return { successCount: 1 }; }
}
function checkSound(id) {
  if (strict.sounds && String(id).startsWith("grimoire.") && !assets.sounds.has(id)) problem(`playSound: unknown sound ${id}`);
  stats.sounds++;
}

const dims = { overworld: new Dimension("minecraft:overworld"), nether: new Dimension("minecraft:nether"), the_end: new Dimension("minecraft:the_end") };
const worldDyn = new Map();
const mk = (names) => Object.fromEntries(names.map((n) => [n, new Signal()]));

export const world = {
  afterEvents: mk(["itemStartUse", "itemReleaseUse", "itemStopUse", "itemCompleteUse", "itemUse", "entityDie", "entityHurt", "playerSpawn",
    "playerLeave", "playerDimensionChange", "worldLoad", "entitySpawn", "entityRemove", "playerButtonInput", "playerHotbarSelectedSlotChange",
    "projectileHitEntity", "projectileHitBlock", "entityHitEntity", "playerInventoryItemChange", "entityLoad", "entityHealthChanged", "itemStartUseOn"]),
  beforeEvents: mk(["entityHurt", "playerLeave", "itemUse", "playerInteractWithBlock", "playerInteractWithEntity", "entityRemove", "playerBreakBlock"]),
  getAllPlayers() { return Object.values(dims).flatMap((d) => d.getPlayers()); },
  getPlayers(o) { return Object.values(dims).flatMap((d) => d.getPlayers(o)); },
  getDimension(id) { const d = dims[String(id).replace("minecraft:", "")]; if (!d) throw new Error(`no dimension ${id}`); return d; },
  getDynamicProperty(k) { return worldDyn.get(k); },
  setDynamicProperty(k, v) {
    if (typeof v === "string" && v.length > 32767) { problem(`world dynamic property ${k} too long (${v.length})`); throw new Error("too long"); }
    if (v === undefined) worldDyn.delete(k); else worldDyn.set(k, v);
  },
  getAbsoluteTime() { return system.currentTick; },
  sendMessage() {},
  gameRules: { pvp: true },
};
export const worldDynamic = worldDyn;

let timers = [];
let nextTimer = 1;
export const system = {
  currentTick: 0,
  beforeEvents: mk(["startup", "shutdown", "watchdogTerminate"]),
  afterEvents: { scriptEventReceive: new Signal() },
  run(fn) { const id = nextTimer++; timers.push({ id, at: this.currentTick + 1, fn }); return id; },
  runTimeout(fn, t = 1) { const id = nextTimer++; timers.push({ id, at: this.currentTick + Math.max(1, t), fn }); return id; },
  runInterval(fn, t = 1) { const id = nextTimer++; timers.push({ id, at: this.currentTick + Math.max(1, t), fn, every: Math.max(1, t) }); return id; },
  clearRun(id) { timers = timers.filter((x) => x.id !== id); },
  runJob(gen) { for (const _ of gen) { /* drain */ } return 0; },
};

/** Advance the simulated server by n ticks. */
export function tick(n = 1) {
  for (let i = 0; i < n; i++) {
    system.currentTick++;
    const due = timers.filter((t) => t.at <= system.currentTick);
    for (const t of due) {
      if (!timers.includes(t)) continue;
      if (t.every) t.at = system.currentTick + t.every; else timers = timers.filter((x) => x !== t);
      t.fn();
    }
  }
}

// ---- helpers for tests
export function addPlayer(name, loc = { x: 0.5, y: GROUND, z: 0.5 }, dim = "overworld") {
  const p = new Player(dims[dim], name, loc);
  dims[dim].entities.add(p);
  return p;
}
export function addMob(typeId = "minecraft:zombie", loc = { x: 0.5, y: GROUND, z: 8.5 }, health = 20, dim = "overworld") {
  const e = new Entity(dims[dim], typeId, loc);
  e.families = ["monster", "mob", "zombie"]; e.health = health; e.maxHealth = health;
  dims[dim].entities.add(e);
  return e;
}
export function addProjectile(typeId, loc, dim = "overworld") {
  const e = new Entity(dims[dim], typeId, loc);
  e.families = ["projectile"]; e.projectile = { owner: undefined };
  dims[dim].entities.add(e);
  return e;
}
export function reset() {
  for (const d of Object.values(dims)) { for (const e of d.entities) e.isValid = false; d.entities.clear(); d.blocks.clear(); }
  tick(2); // let scenes owned by the previous test's (now invalid) players end and clean up
  for (const d of Object.values(dims)) { d.entities.clear(); d.blocks.clear(); }
  problems.length = 0;
  for (const k of Object.keys(stats)) stats[k] = typeof stats[k] === "number" ? 0 : {};
}
export function constructs(dim = "overworld") { return [...dims[dim].entities].filter((e) => e.typeId.startsWith("grimoire:")); }
export function tempBlocks(dim = "overworld") { return [...dims[dim].blocks.entries()]; }
export const GROUND_Y = GROUND;
export function startup() {
  const cmds = {};
  system.beforeEvents.startup.emit({ customCommandRegistry: { registerCommand(def, cb) { cmds[def.name] = { def, cb }; }, registerEnum() {} },
    itemComponentRegistry: { registerCustomComponent() {} }, blockComponentRegistry: { registerCustomComponent() {} } });
  world.afterEvents.worldLoad.emit({});
  return cmds;
}
