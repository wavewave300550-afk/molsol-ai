// Minimal behavioural mock of @minecraft/server for headless spell tests.
// It is deliberately strict about identifiers: spawning an unknown grimoire entity, setting an
// undefined entity property / out-of-range value, or using an unregistered particle / sound id
// is recorded in `problems` so script <-> asset cross references are verified without the game.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const readJson = (p, d) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return d; } };

export const assets = { actors: {}, families: {}, persistent: new Set(), particles: new Set(), sounds: new Set(), items: new Set(), fogs: new Set(), blocks: new Set() };
export function loadAssets() {
  assets.actors = {}; assets.families = {}; assets.persistent = new Set();
  const edir = path.join(ROOT, "behavior_packs/grimoire_bp/entities");
  if (fs.existsSync(edir)) for (const f of fs.readdirSync(edir)) {
    const j = readJson(path.join(edir, f), null);
    const d = j?.["minecraft:entity"]?.description;
    if (!d) continue;
    assets.actors[d.identifier] = d.properties ?? {};
    const comps = j["minecraft:entity"].components ?? {};
    assets.families[d.identifier] = comps["minecraft:type_family"]?.family ?? [];
    if (!comps["minecraft:transient"]) assets.persistent.add(d.identifier);   // saved with its chunk
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
  assets.fogs = new Set();
  const fdir = path.join(ROOT, "resource_packs/grimoire_rp/fogs");
  if (fs.existsSync(fdir)) for (const f of fs.readdirSync(fdir)) {
    const id = readJson(path.join(fdir, f), null)?.["minecraft:fog_settings"]?.description?.identifier;
    if (id) assets.fogs.add(id);
  }
  assets.blocks = new Set();
  try {
    const src = fs.readFileSync(path.join(ROOT, "node_modules/@minecraft/vanilla-data/lib/mojang-block.d.ts"), "utf8");
    for (const m of src.matchAll(/"(minecraft:[a-z0-9_]+)"/g)) assets.blocks.add(m[1]);
  } catch { /* vanilla-data missing: block ids are not checked */ }
  assets.items = new Set();
  const idir = path.join(ROOT, "behavior_packs/grimoire_bp/items");
  if (fs.existsSync(idir)) for (const f of fs.readdirSync(idir)) {
    const id = readJson(path.join(idir, f), null)?.["minecraft:item"]?.description?.identifier;
    if (id) assets.items.add(id);
  }
}

export const problems = [];
export const stats = { particles: 0, sounds: 0, spawned: {}, damage: 0, heals: 0, peakEntities: 0, effects: 0, knockbacks: 0,
  blockEdits: 0, maxEditsPerTick: 0, maxSubchunksPerTick: 0, maxGroundEditsPerTick: 0, maxGroundSubchunksPerTick: 0 };
const tickEdits = { n: 0, sub: new Set(), g: 0, gsub: new Set() };
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
export const InputPermissionCategory = { Camera: 1, Movement: 2, LateralMovement: 4, Sneak: 5, Jump: 6, Mount: 7, Dismount: 8, MoveForward: 9, MoveBackward: 10, MoveLeft: 11, MoveRight: 12 };
export const EasingType = new Proxy({}, { get: (_, k) => k });
export const TimeOfDay = { Day: 1000, Noon: 6000, Sunset: 12000, Night: 13000, Midnight: 18000, Sunrise: 23000 };
export const MemoryTier = { SuperLow: 0, Low: 1, Mid: 2, High: 3, SuperHigh: 4 };
export const PlatformType = { Console: "Console", Desktop: "Desktop", Mobile: "Mobile" };
/** Block permutation: a block type plus its states (resolve() checks the id against vanilla-data). */
class Perm {
  constructor(t, s) { this.type = { id: t }; this.s = { ...(s ?? {}) }; }
  getAllStates() { return { ...this.s }; }
  getState(n) { return this.s[n]; }
  withState(n, v) { return new Perm(this.type.id, { ...this.s, [n]: v }); }
  matches(t, s) { return t === this.type.id && Object.entries(s ?? {}).every(([k, v]) => this.s[k] === v); }
}
export const BlockPermutation = {
  resolve(t, s) {
    if (assets.blocks.size && !assets.blocks.has(t)) { problem(`BlockPermutation.resolve: unknown block ${t}`); throw new Error(`unknown block ${t}`); }
    return new Perm(t, s);
  },
};
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
/** Natural column: surface block (grass by default) at the top, 3 dirt, then stone. */
let surface = () => "minecraft:grass_block";
export function setSurface(fn) { surface = fn ?? (() => "minecraft:grass_block"); }
/** Natural plant on top of some columns (e.g. short grass in a meadow): it sits in the first air cell. */
let cover = () => undefined;
export function setCover(fn) { cover = fn ?? (() => undefined); }
/** Columns whose chunk is not loaded (getBlock returns undefined there, as in the engine). */
let unloaded = () => false;
export function setUnloaded(fn) {
  const was = unloaded;
  unloaded = fn ?? (() => false);
  for (const d of Object.values(dims)) for (const e of d.entities) {
    const x = Math.floor(e.location.x), z = Math.floor(e.location.z);
    if (e.isValid && was(x, z) && !unloaded(x, z)) world.afterEvents.entityLoad.emit({ entity: e });
  }
}
export function natural(x, y, z) {
  const h = terrain(x, z);
  if (y === h) { const c = cover(x, z); if (c) return c; }
  if (y >= h) return "minecraft:air";
  if (y === h - 1) return surface(x, z);
  if (y >= h - 4) return "minecraft:dirt";
  return "minecraft:stone";
}
/** Ground types a terraforming spell may put on the natural surface layer (restored before the test ends). */
export const TERRAFORM = new Set(["minecraft:moss_block", "minecraft:podzol", "minecraft:dirt_with_roots", "minecraft:mud",
  "minecraft:coarse_dirt", "minecraft:gravel", "minecraft:basalt", "minecraft:smooth_basalt", "minecraft:blackstone",
  "minecraft:magma", "minecraft:packed_mud"]);
/** Plants that need dirt-like ground under them, and the ground that holds them (a plant on anything else breaks and drops). */
export const PLANTS = new Set(["minecraft:short_grass", "minecraft:fern", "minecraft:wildflowers", "minecraft:pink_petals",
  "minecraft:leaf_litter", "minecraft:firefly_bush", "minecraft:dandelion", "minecraft:poppy", "minecraft:bush"]);
const SOIL = new Set(["minecraft:grass_block", "minecraft:dirt", "minecraft:coarse_dirt", "minecraft:podzol", "minecraft:mycelium",
  "minecraft:dirt_with_roots", "minecraft:moss_block", "minecraft:mud", "minecraft:farmland"]);
/** Blocks a ray passes through (plants, carpets, light blocks) - like includePassableBlocks: false in the engine. */
// (a carpet is NOT passable: it has a thin collision box, so a ray stops on it unless the type is excluded)
export const PASSABLE = new Set([...PLANTS, ...Array.from({ length: 16 }, (_, i) => `minecraft:light_block_${i}`)]);
const LIQUID = new Set(["minecraft:water", "minecraft:flowing_water", "minecraft:lava", "minecraft:flowing_lava"]);
const CONTAINER = new Set(["minecraft:chest", "minecraft:barrel", "minecraft:trapped_chest", "minecraft:hopper", "minecraft:furnace"]);

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
    this.commands = []; this.fades = [];
    this.isSleeping = false; this.isGliding = false; this.isOnGround = true;
    const live = () => { if (!self.isValid) throw new Error("InvalidEntityError: the player is gone"); };
    this.fog = [];
    this.fogSettings = {
      push(id, tag) {
        live();
        if (!assets.fogs.has(id)) { problem(`fogSettings.push: unknown fog ${id}`); throw new Error("FogSettingsError: unknown fog"); }
        if (self.fog.length >= 16) { problem("fogSettings: stack over 16"); throw new Error("FogSettingsError: full"); }
        self.fog.push({ id, tag });
        return self.fog.length - 1;
      },
      pop(tag) { live(); for (let i = self.fog.length - 1; i >= 0; i--) if (tag === undefined || self.fog[i].tag === tag) { self.fog.splice(i, 1); return true; } return false; },
      remove(tag) { live(); const n = self.fog.length; self.fog = tag === undefined ? [] : self.fog.filter((f) => f.tag !== tag); return n !== self.fog.length; },
      getStack() { live(); return self.fog.map((f) => f.id); },
      getTags() { live(); return self.fog.map((f) => f.tag); },
      setStack() { live(); problem("fogSettings.setStack wipes other packs' fogs"); },
    };
    this.cam = { active: false, sets: 0, clears: 0, anims: 0 };
    const finite = (v) => v && ["x", "y", "z"].every((k) => Number.isFinite(v[k]));
    this.camera = {
      isValid: true,
      fade(o) { live(); self.fades.push(o ?? {}); },
      clear() { live(); self.cam.active = false; self.cam.clears++; },
      setCamera(preset, o = {}) {
        live();
        if (preset !== "minecraft:free" && preset !== "minecraft:first_person") problem(`camera preset ${preset}`);
        if ((o.location && !finite(o.location)) || (o.facingLocation && !finite(o.facingLocation))) problem("camera at a non-finite location");
        if (o.easeOptions && !(o.easeOptions.easeTime > 0)) problem("camera ease time must be > 0");
        self.cam.active = true; self.cam.sets++;
      },
      playAnimation(spline, o = {}) {
        live();
        if (!(o.totalTimeSeconds > 0) || !spline?.controlPoints?.length) problem("camera animation without points or time");
        self.cam.active = true; self.cam.anims++;
      },
    };
    this.inputPerm = new Map();
    this.inputPermissions = {
      setPermissionCategory(c, on) { live(); self.inputPerm.set(c, on); },
      isPermissionCategoryEnabled(c) { live(); return self.inputPerm.get(c) ?? true; },
    };
    this.clientSystemInfo = { platformType: PlatformType.Desktop, memoryTier: MemoryTier.High, maxRenderDistance: 16 };
  }
  runCommand(c) {
    if (typeof c !== "string" || !c.length) throw new Error("runCommand: empty command");
    this.commands.push(c);
    return { successCount: 1 };
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
  get isLiquid() { return LIQUID.has(this.typeId); }
  get isWaterlogged() { return false; }
  get isSolid() { return !this.isAir && !PASSABLE.has(this.typeId) && !LIQUID.has(this.typeId); }
  get permutation() { return new Perm(this.typeId, this.dimension.bstates.get(`${this.x},${this.y},${this.z}`)); }
  getComponent(id) { return CONTAINER.has(this.typeId) && /inventory/.test(id) ? { container: {} } : undefined; }
  setType(t) { this.dimension.setBlockType(this.location, t); }
  setPermutation(p) { this.dimension.setBlockType(this.location, p.type.id, p.getAllStates()); }
  matches(n) { return this.typeId === n; }
  above(n = 1) { return new Block(this.dimension, this.x, this.y + n, this.z); }
  below(n = 1) { return new Block(this.dimension, this.x, this.y - n, this.z); }
}

export class Dimension {
  constructor(id) { this.id = id; this.entities = new Set(); this.blocks = new Map(); this.bstates = new Map(); this.heightRange = { min: -64, max: 320 }; }
  blockAt(x, y, z) {
    const k = `${x},${y},${z}`;
    if (this.blocks.has(k)) return this.blocks.get(k);
    return natural(x, y, z);
  }
  getBlock(loc) {
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) { problem("getBlock with non-finite location"); return undefined; }
    if (unloaded(Math.floor(loc.x), Math.floor(loc.z))) return undefined;
    return new Block(this, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
  }
  /** A plant on ground that cannot hold it breaks in the engine and drops an item: never allowed. */
  checkSupport(x, y, z) {
    const t = this.blockAt(x, y, z), under = this.blockAt(x, y - 1, z);
    if (PLANTS.has(t) && !SOIL.has(under)) problem(`${t} at ${x},${y},${z} left on ${under} (it would break and drop an item)`);
    if (t === "minecraft:moss_carpet" && (under === "minecraft:air" || PLANTS.has(under) || LIQUID.has(under))) problem(`moss carpet at ${x},${y},${z} on ${under}`);
  }
  setBlockType(loc, t, states) {
    const id = typeof t === "string" ? t : t.id;
    const x = Math.floor(loc.x), y = Math.floor(loc.y), z = Math.floor(loc.z);
    const k = `${x},${y},${z}`;
    if (assets.blocks.size && !assets.blocks.has(id)) { problem(`setType: unknown block ${id}`); throw new Error(`unknown block ${id}`); }
    // edit pacing (how many blocks and chunk sections a spell changes in one tick)
    stats.blockEdits++; tickEdits.n++; tickEdits.sub.add(`${x >> 4},${y >> 4},${z >> 4}`);
    stats.maxEditsPerTick = Math.max(stats.maxEditsPerTick, tickEdits.n);
    stats.maxSubchunksPerTick = Math.max(stats.maxSubchunksPerTick, tickEdits.sub.size);
    if (!/barrier|light_block/.test(id) && !/barrier|light_block/.test(this.blockAt(x, y, z))) {   // living ground, not a spell's barrier / light
      tickEdits.g++; tickEdits.gsub.add(`${x >> 4},${y >> 4},${z >> 4}`);
      stats.maxGroundEditsPerTick = Math.max(stats.maxGroundEditsPerTick, tickEdits.g);
      stats.maxGroundSubchunksPerTick = Math.max(stats.maxGroundSubchunksPerTick, tickEdits.gsub.size);
    }
    const nat = natural(x, y, z);
    if (id === nat && !(states && Object.keys(states).length)) {   // back to natural
      this.blocks.delete(k); this.bstates.delete(k);
      this.checkSupport(x, y, z); this.checkSupport(x, y + 1, z);
      return;
    }
    const h = terrain(x, z);
    if (y < h && !(y === h - 1 && TERRAFORM.has(id))) problem(`world terrain modified at ${k} -> ${id}`);
    this.blocks.set(k, id);
    if (states && Object.keys(states).length) this.bstates.set(k, { ...states }); else this.bstates.delete(k);
    this.checkSupport(x, y, z);
    this.checkSupport(x, y + 1, z);
  }
  /** Test fixture: put a block without the terrain rules (e.g. a player build to check that spells leave it alone). */
  fixture(loc, id) { const k = `${Math.floor(loc.x)},${Math.floor(loc.y)},${Math.floor(loc.z)}`; this.blocks.set(k, id); }
  getBlockFromRay(loc, dir, o = {}) {
    const max = o.maxDistance ?? 64;
    for (let t = 0; t <= max; t += 0.25) {
      const p = { x: loc.x + dir.x * t, y: loc.y + dir.y * t, z: loc.z + dir.z * t };
      const b = this.getBlock(p);
      if (b && !b.isAir && !PASSABLE.has(b.typeId) && !(o.excludeTypes ?? []).includes(b.typeId) && (o.includeLiquidBlocks || !b.isLiquid)) {
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
    if (id.startsWith("grimoire:")) { e.families = [...(assets.families[id] ?? ["grimoire_construct", "inanimate"])]; e.invulnerable = true; }
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
      if (unloaded(Math.floor(e.location.x), Math.floor(e.location.z))) continue;
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
  beforeEvents: mk(["entityHurt", "playerLeave", "itemUse", "playerInteractWithBlock", "playerInteractWithEntity", "entityRemove", "playerBreakBlock", "explosion"]),
  getAllPlayers() { return Object.values(dims).flatMap((d) => d.getPlayers()); },
  getPlayers(o) { return Object.values(dims).flatMap((d) => d.getPlayers(o)); },
  getDimension(id) { const d = dims[String(id).replace("minecraft:", "")]; if (!d) throw new Error(`no dimension ${id}`); return d; },
  getEntity(id) {
    for (const d of Object.values(dims)) for (const e of d.entities) {
      if (e.id === id && e.isValid && !unloaded(Math.floor(e.location.x), Math.floor(e.location.z))) return e;
    }
    return undefined;
  },
  getDynamicProperty(k) { return worldDyn.get(k); },
  setDynamicProperty(k, v) {
    if (typeof v === "string" && v.length > 32767) { problem(`world dynamic property ${k} too long (${v.length})`); throw new Error("too long"); }
    if (v === undefined) worldDyn.delete(k); else worldDyn.set(k, v);
  },
  getDynamicPropertyIds() { return [...worldDyn.keys()]; },
  getAbsoluteTime() { return absNow(); },
  setAbsoluteTime(t) {
    if (!Number.isFinite(t) || t < 0) { problem(`setAbsoluteTime(${t})`); throw new Error("bad time"); }
    clock.abs = Math.round(t); clock.at = system.currentTick; clock.sets++;
  },
  getTimeOfDay() { return absNow() % 24000; },
  setTimeOfDay(t) {
    const v = typeof t === "number" ? t : TimeOfDay[t];
    if (!Number.isFinite(v) || v < 0 || v > 24000) { problem(`setTimeOfDay(${t})`); throw new Error("bad time of day"); }
    const a = absNow(); clock.abs = a - (a % 24000) + Math.round(v); clock.at = system.currentTick; clock.sets++;
  },
  sendMessage() {},
  gameRules: { pvp: true, doDayLightCycle: true },
};
/** World clock: absolute time `abs` at tick `at`; it runs on while the daylight cycle is on. */
export const clock = { abs: 6000, at: 0, sets: 0 };
function absNow() { return world.gameRules.doDayLightCycle ? clock.abs + (system.currentTick - clock.at) : clock.abs; }
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
    tickEdits.n = 0; tickEdits.sub.clear(); tickEdits.g = 0; tickEdits.gsub.clear();
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
  for (const d of Object.values(dims)) { for (const e of d.entities) e.isValid = false; d.entities.clear(); }
  tick(2); // let scenes owned by the previous test's (now invalid) players end and clean up
  for (const d of Object.values(dims)) { d.entities.clear(); d.blocks.clear(); d.bstates.clear(); }
  surface = () => "minecraft:grass_block";
  cover = () => undefined;
  unloaded = () => false;
  world.gameRules.doDayLightCycle = true;
  clock.abs = 6000; clock.at = system.currentTick; clock.sets = 0;
  problems.length = 0;
  for (const k of Object.keys(stats)) stats[k] = typeof stats[k] === "number" ? 0 : {};
}
/** Blocks that differ from the natural world (spell leftovers, or fixtures a test placed). */
export function changedBlocks(dim = "overworld") { return [...dims[dim].blocks.entries()]; }
/** Save / bring back blocks, world dynamic properties and the clock (a world save and reload after a crash). */
export function snapshotWorld() {
  const ents = (d) => [...d.entities].filter((e) => e.isValid && assets.persistent.has(e.typeId))
    .map((e) => ({ id: e.id, typeId: e.typeId, loc: { ...e.location }, dyn: new Map(e.dyn), families: [...e.families] }));
  return {
    dims: Object.fromEntries(Object.entries(dims).map(([n, d]) => [n, { b: new Map(d.blocks), s: new Map(d.bstates), e: ents(d) }])),
    dyn: new Map(worldDyn), clock: { ...clock }, now: absNow(),
  };
}
/**
 * Load a saved world again after a crash: blocks and the persistent entities in them come from `snap`;
 * world dynamic properties and the clock from `levelSnap` (default: the same) - on a real server those are
 * saved on a slower timer, so after a hard crash they can be older than the chunks.
 */
export function restoreWorld(snap, levelSnap = snap) {
  for (const [n, d] of Object.entries(dims)) {
    d.blocks = new Map(snap.dims[n].b); d.bstates = new Map(snap.dims[n].s);
    for (const e of [...d.entities]) if (assets.persistent.has(e.typeId)) { e.isValid = false; d.entities.delete(e); }
    for (const x of snap.dims[n].e ?? []) {
      const e = new Entity(d, x.typeId, x.loc);
      e.id = x.id; e.families = [...x.families]; e.invulnerable = true;
      for (const [k, v] of x.dyn) e.dyn.set(k, v);
      d.entities.add(e);
    }
  }
  worldDyn.clear();
  for (const [k, v] of levelSnap.dyn) worldDyn.set(k, v);
  clock.abs = levelSnap.now; clock.at = system.currentTick;
}
export function getDimension(n = "overworld") { return dims[n]; }
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
