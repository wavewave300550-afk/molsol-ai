// Strict emulation of the @minecraft/server 2.11.0 surface used by the Porcelain Emperor.
// Wrong identifiers (entities, blocks, items, particles, sounds, effects, fogs, properties),
// out-of-range property values, writes to unloaded chunks, calls on removed entities and
// non-finite vectors are reported as issues (and fail the smoke test).
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.PORCELAIN_MOCK_DATA, "utf8"));
export const __issues = [];
function issue(msg) {
  __issues.push(msg);
}
const EFFECTS = new Set(DATA.effects);
const PARTICLES = new Set(DATA.particles);
const SOUNDS = new Set(DATA.sounds);
const BLOCKS = new Set(DATA.blocks);
const ITEMS = new Set(DATA.items);
const FOGS = new Set(DATA.fogs);
const ENTITY_DEFS = DATA.entities;
const stripNs = (id) => id.replace(/^minecraft:/, "");
function finite(v, what) {
  if (!v || !Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) issue(`non-finite vector for ${what}: ${JSON.stringify(v)}`);
}

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["anvil", "blockExplosion", "contact", "drowning", "entityAttack", "entityExplosion", "fall", "fire", "fireTick", "lava",
   "lightning", "magic", "none", "override", "projectile", "suffocation", "void", "wither"].map((k) => [k, k]),
);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const Difficulty = { Peaceful: "Peaceful", Easy: "Easy", Normal: "Normal", Hard: "Hard" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = { Enum: "Enum", String: "String", Integer: "Integer" };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const EasingType = { InOutSine: "InOutSine", Linear: "Linear" };
export const InputPermissionCategory = { Movement: 2, Camera: 1 };
export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };

// ------------------------------------------------------------------ scheduler
let currentTick = 0;
let nextId = 1;
const timers = new Map();
const jobs = [];
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
  subscribe(fn) {
    this.handlers.push(fn);
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h !== fn);
  }
  fire(ev) {
    for (const h of this.handlers) {
      try {
        h(ev);
      } catch (e) {
        issue(`uncaught error in ${this.name} handler: ${e && e.stack ? e.stack : e}`);
      }
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
  runJob(gen) {
    if (!gen || typeof gen.next !== "function") issue("runJob needs a generator");
    const id = nextId++;
    jobs.push({ id, gen });
    return id;
  },
  beforeEvents: { startup: new Signal("startup") },
  afterEvents: {},
};

export async function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    currentTick++;
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
    // jobs get a budget of steps per tick, like the real time-sliced runner
    for (let j = jobs.length - 1; j >= 0; j--) {
      let done = false;
      try {
        for (let s = 0; s < 60 && !done; s++) done = !!jobs[j].gen.next().done;
      } catch (e) {
        issue(`job failed: ${e && e.stack ? e.stack : e}`);
        done = true;
      }
      if (done) jobs.splice(j, 1);
    }
    for (const e of [...world.__entities.values()]) e.__step();
    for (const ta of world.tickingAreaManager.__pending.splice(0)) ta();
    await Promise.resolve();
  }
}

// ------------------------------------------------------------------ blocks
export class BlockPermutation {
  constructor(id, states) {
    this.type = { id };
    this.__states = states ?? {};
  }
  static resolve(id, states) {
    if (!id.includes(":")) id = "minecraft:" + id;
    if (!BLOCKS.has(id)) issue(`unknown block ${id}`);
    for (const k of Object.keys(states ?? {})) {
      if (!(id === "minecraft:lantern" && k === "hanging")) issue(`unknown block state ${k} for ${id}`);
    }
    return new BlockPermutation(id, states);
  }
  matches(id) {
    return this.type.id === id;
  }
}
export class BlockVolume {
  constructor(from, to) {
    finite(from, "BlockVolume.from");
    finite(to, "BlockVolume.to");
    this.from = from;
    this.to = to;
  }
}
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(n, v) {
    if (!n.startsWith("variable.")) issue(`molang variable must start with variable.: ${n}`);
    if (!Number.isFinite(v)) issue(`molang ${n} = ${v}`);
    this.vars[n] = v;
  }
  setColorRGB(n, c) {
    if (!c || ![c.red, c.green, c.blue].every(Number.isFinite)) issue(`bad colour for ${n}`);
    this.vars[n] = c;
  }
  setColorRGBA(n, c) {
    this.setColorRGB(n, c);
  }
  setSpeedAndDirection(n, s, d) {
    finite(d, n);
    this.vars[n] = { s, d };
  }
}

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.includes(":")) typeId = "minecraft:" + typeId;
    if (!ITEMS.has(typeId)) issue(`unknown item ${typeId}`);
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
  addItem(it) {
    const same = this.slots.findIndex((s) => s && s.typeId === it.typeId && s.amount + it.amount <= 64 && !it.typeId.endsWith("seal") && !it.typeId.endsWith("heart"));
    if (same >= 0) {
      this.slots[same].amount += it.amount;
      return undefined;
    }
    const i = this.slots.findIndex((s) => !s);
    if (i < 0) return it;
    this.slots[i] = it;
    return undefined;
  }
  count(typeId) {
    return this.slots.reduce((n, s) => n + (s && s.typeId === typeId ? s.amount : 0), 0);
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
    this.__rotation = { x: 0, y: 0 };
    this.__velocity = { x: 0, y: 0, z: 0 };
    this.__teleports = 0;
    this.isSneaking = false;
    if (def && def.health) this.__health = new Health(this, def.health);
    if (def && def.properties) for (const [k, p] of Object.entries(def.properties)) this.__props.set(k, p.default);
    world.__entities.set(this.id, this);
  }
  get isValid() {
    return this.__valid;
  }
  __check(what) {
    if (!this.__valid) throw new Error(`InvalidEntityError: ${what} on removed ${this.typeId}`);
  }
  __step() {
    if (!this.__valid) return;
    for (const [k, e] of [...this.__effects]) {
      e.duration--;
      if (e.duration <= 0) this.__effects.delete(k);
    }
  }
  getComponent(id) {
    this.__check("getComponent");
    if (id === "minecraft:health") return this.__health;
    if (id === "minecraft:inventory") return this.__inv ? { container: this.__inv } : undefined;
    if (id === "minecraft:item") return this.__item ? { itemStack: this.__item } : undefined;
    if (id === "minecraft:equippable") {
      const self = this;
      return this.__inv ? { getEquipment: (slot) => (slot === "Offhand" ? self.__offhand : self.__inv.getItem(self.selectedSlotIndex ?? 0)) } : undefined;
    }
    return undefined;
  }
  addEffect(type, duration, opts = {}) {
    this.__check("addEffect");
    const id = stripNs(type);
    if (!EFFECTS.has(id)) issue(`unknown effect ${type}`);
    if (!Number.isInteger(duration) || duration < 1) issue(`bad effect duration ${duration} for ${type}`);
    const amp = opts.amplifier ?? 0;
    if (!Number.isInteger(amp) || amp < 0 || amp > 255) issue(`bad amplifier ${amp}`);
    this.__effects.set(id, { typeId: id, duration, amplifier: amp });
  }
  getEffect(type) {
    return this.__effects.get(stripNs(type));
  }
  applyDamage(amount, opts) {
    this.__check("applyDamage");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage ${amount}`);
    if (opts && opts.cause && !(opts.cause in EntityDamageCause)) issue(`bad cause ${opts.cause}`);
    if (opts?.damagingEntity && !opts.damagingEntity.isValid) issue("applyDamage with a removed damagingEntity");
    if (!this.__health) return false;
    if (this instanceof Player && (this.__dead || this.__mode === GameMode.Creative)) return false;
    const ev = { hurtEntity: this, damage: amount, cancel: false, damageSource: { cause: opts?.cause ?? "entityAttack", damagingEntity: opts?.damagingEntity } };
    world.beforeEvents.entityHurt.fire(ev);
    if (ev.cancel) return false;
    if (!Number.isFinite(ev.damage) || ev.damage < 0) issue(`hurt handler produced damage ${ev.damage}`);
    let dmg = ev.damage;
    const res = this.__effects.get("resistance");
    if (res) dmg *= Math.max(0, 1 - 0.2 * (res.amplifier + 1));
    this.__hurtLog = this.__hurtLog ?? [];
    this.__hurtLog.push({ t: currentTick, amount: dmg, cause: ev.damageSource.cause, by: opts?.damagingEntity?.typeId });
    this.__health.currentValue -= dmg;
    if (this.__health.currentValue <= 0) {
      this.__health.currentValue = 0;
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: ev.damageSource });
      if (this instanceof Player) this.__die();
      else this.__valid && this.remove();
    }
    return true;
  }
  applyKnockback(h, vert) {
    this.__check("applyKnockback");
    if (!h || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue(`bad knockback ${JSON.stringify(h)} ${vert}`);
    this.location.x += h.x;
    this.location.z += h.z;
  }
  teleport(loc, opts = {}) {
    this.__check("teleport");
    finite(loc, `teleport of ${this.typeId}`);
    if (opts.rotation && (!Number.isFinite(opts.rotation.x) || !Number.isFinite(opts.rotation.y))) issue("bad teleport rotation");
    if (opts.dimension && !(opts.dimension instanceof Dimension)) issue("teleport dimension is not a Dimension");
    this.location = { ...loc };
    if (opts.rotation) this.__rotation = { ...opts.rotation };
    if (opts.dimension) this.dimension = opts.dimension;
    this.__teleports++;
  }
  remove() {
    this.__check("remove");
    this.__valid = false;
    world.__entities.delete(this.id);
  }
  getRotation() {
    return { ...this.__rotation };
  }
  getVelocity() {
    return { ...this.__velocity };
  }
  getViewDirection() {
    const yaw = (this.__rotation.y * Math.PI) / 180;
    return { x: -Math.sin(yaw), y: 0, z: Math.cos(yaw) };
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
    return this.__props.get(k);
  }
  setProperty(k, v) {
    this.__check("setProperty");
    const def = ENTITY_DEFS[this.typeId]?.properties?.[k];
    if (!def) {
      issue(`setProperty unknown property ${k} on ${this.typeId}`);
      throw new Error(`unknown property ${k}`);
    }
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) issue(`${k}=${v} outside int range ${def.range}`);
    if (def.type === "float" && (!Number.isFinite(v) || v < def.range[0] || v > def.range[1])) issue(`${k}=${v} outside float range ${def.range}`);
    if (def.type === "bool" && typeof v !== "boolean") issue(`${k}=${v} is not a bool`);
    this.__props.set(k, v);
    (this.__propLog = this.__propLog ?? []).push([currentTick, k, v]);
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__inv = new Container(36);
    this.selectedSlotIndex = 0;
    this.__mode = GameMode.Survival;
    this.__messages = [];
    this.__titles = [];
    this.__bars = [];
    this.__fog = [];
    this.__music = undefined;
    this.__input = { 2: true, 1: true };
    this.__xp = 0;
    this.__dead = false;
    this.__spawn = undefined;
    this.commandPermissionLevel = CommandPermissionLevel.Any;
    const self = this;
    this.onScreenDisplay = {
      setTitle(t, o) {
        self.__titles.push(o?.subtitle ? `${t} | ${o.subtitle}` : t);
      },
      setActionBar(t) {
        self.__bars.push(t);
      },
      updateSubtitle() {},
    };
    this.camera = {
      fade(o) {
        if (o?.fadeTime && ![o.fadeTime.fadeInTime, o.fadeTime.holdTime, o.fadeTime.fadeOutTime].every((x) => Number.isFinite(x) && x >= 0 && x <= 10)) issue("bad camera fade");
      },
      setCamera(preset, o) {
        if (preset !== "minecraft:free") issue(`unknown camera preset ${preset}`);
        if (o?.location) finite(o.location, "camera location");
        if (o?.facingLocation) finite(o.facingLocation, "camera facing");
        self.__camera = preset;
      },
      clear() {
        self.__camera = undefined;
      },
    };
    this.inputPermissions = {
      setPermissionCategory(cat, on) {
        self.__input[cat] = on;
      },
    };
    this.fogSettings = {
      push(id, tag) {
        if (!FOGS.has(id)) issue(`unknown fog ${id}`);
        if (self.__fog.length >= 16) issue("fog stack overflow");
        self.__fog.push({ id, tag: tag ?? "untagged" });
        return self.__fog.length - 1;
      },
      remove(tag) {
        const n = self.__fog.length;
        self.__fog = tag ? self.__fog.filter((f) => f.tag !== tag) : [];
        return self.__fog.length !== n;
      },
      getStack() {
        return self.__fog.map((f) => f.id);
      },
    };
  }
  getGameMode() {
    return this.__mode;
  }
  getSpawnPoint() {
    return this.__spawn;
  }
  sendMessage(m) {
    this.__messages.push(typeof m === "string" ? m : JSON.stringify(m));
  }
  playSound(id, o) {
    this.__check("playSound");
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
  }
  playMusic(id, o) {
    if (!SOUNDS.has(id)) issue(`unknown music ${id}`);
    this.__music = id;
  }
  stopMusic() {
    this.__music = undefined;
  }
  addExperience(n) {
    if (!Number.isInteger(n)) issue(`bad xp ${n}`);
    this.__xp += n;
    return this.__xp;
  }
  runCommand(cmd) {
    if (!/^camerashake add @s [0-9.]+ [0-9.]+ (rotational|positional)$/.test(cmd)) issue(`unexpected command ${cmd}`);
    return { successCount: 1 };
  }
  __die() {
    this.__dead = true;
    this.__deathTick = currentTick;
  }
  __respawn() {
    this.__dead = false;
    this.__health.currentValue = 20;
    this.__effects.clear();
    this.dimension = world.getDimension("overworld");
    this.location = { x: 0.5, y: 70, z: 0.5 };
    world.afterEvents.playerSpawn.fire({ player: this, initialSpawn: false });
  }
}

// ------------------------------------------------------------------ dimensions
export class Dimension {
  constructor(id, custom = false) {
    this.id = id;
    this.__custom = custom;
    this.heightRange = custom ? { min: -64, max: 320 } : { min: -64, max: 320 };
    this.__blocks = new Map();
    this.__fills = 0;
    this.__particles = new Map();
    this.__sounds = new Map();
  }
  __loaded(x, z) {
    if (!this.__custom) return true;
    for (const ta of world.tickingAreaManager.__areas.values()) {
      if (ta.dimension !== this) continue;
      if (x >= Math.min(ta.from.x, ta.to.x) - 16 && x <= Math.max(ta.from.x, ta.to.x) + 16 && z >= Math.min(ta.from.z, ta.to.z) - 16 && z <= Math.max(ta.from.z, ta.to.z) + 16) return true;
    }
    for (const p of world.getPlayers()) if (p.dimension === this && Math.abs(p.location.x - x) < 64 && Math.abs(p.location.z - z) < 64) return true;
    return false;
  }
  spawnEntity(id, loc, opts) {
    finite(loc, `spawnEntity ${id}`);
    if (!this.__loaded(loc.x, loc.z)) throw new Error(`LocationInUnloadedChunkError: spawnEntity ${id}`);
    return new Entity(id, this, loc);
  }
  spawnItem(stack, loc) {
    finite(loc, "spawnItem");
    if (!(stack instanceof ItemStack)) issue("spawnItem needs an ItemStack");
    const e = new Entity("minecraft:item", this, loc);
    e.__item = stack;
    return e;
  }
  spawnParticle(id, loc, vars) {
    finite(loc, `particle ${id}`);
    if (!PARTICLES.has(id)) issue(`unknown particle ${id}`);
    if (vars && !(vars instanceof MolangVariableMap)) issue("particle variables must be a MolangVariableMap");
    this.__particles.set(id, (this.__particles.get(id) ?? 0) + 1);
  }
  playSound(id, loc, opts) {
    finite(loc, `sound ${id}`);
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
    this.__sounds.set(id, (this.__sounds.get(id) ?? 0) + 1);
  }
  fillBlocks(volume, perm, opts) {
    if (!(volume instanceof BlockVolume)) issue("fillBlocks needs a BlockVolume");
    if (!(perm instanceof BlockPermutation)) issue("fillBlocks needs a BlockPermutation");
    const a = volume.from;
    const b = volume.to;
    const x0 = Math.floor(Math.min(a.x, b.x)), x1 = Math.floor(Math.max(a.x, b.x));
    const y0 = Math.floor(Math.min(a.y, b.y)), y1 = Math.floor(Math.max(a.y, b.y));
    const z0 = Math.floor(Math.min(a.z, b.z)), z1 = Math.floor(Math.max(a.z, b.z));
    const n = (x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1);
    if (n > 32768) issue(`fillBlocks of ${n} blocks exceeds 32768`);
    if (y0 < this.heightRange.min || y1 >= this.heightRange.max) issue(`fillBlocks outside height range ${y0}..${y1}`);
    for (const [x, z] of [[x0, z0], [x1, z1], [x0, z1], [x1, z0]]) {
      if (!this.__loaded(x, z)) throw new Error(`UnloadedChunksError: fill at ${x},${z}`);
    }
    this.__fills++;
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) for (let z = z0; z <= z1; z++) {
      if (perm.type.id === "minecraft:air") this.__blocks.delete(`${x},${y},${z}`);
      else this.__blocks.set(`${x},${y},${z}`, perm.type.id);
    }
    return { getCapacity: () => n };
  }
  setBlockPermutation(loc, perm) {
    finite(loc, "setBlockPermutation");
    if (!this.__loaded(loc.x, loc.z)) throw new Error("LocationInUnloadedChunkError: setBlockPermutation");
    const k = `${Math.floor(loc.x)},${Math.floor(loc.y)},${Math.floor(loc.z)}`;
    if (perm.type.id === "minecraft:air") this.__blocks.delete(k);
    else this.__blocks.set(k, perm.type.id);
  }
  setBlockType(loc, t) {
    this.setBlockPermutation(loc, BlockPermutation.resolve(t));
  }
  __block(x, y, z) {
    return this.__blocks.get(`${Math.floor(x)},${Math.floor(y)},${Math.floor(z)}`);
  }
  getEntities(opts = {}) {
    if (opts.location) finite(opts.location, "getEntities location");
    return [...world.__entities.values()].filter((e) => {
      if (e.dimension !== this || !e.__valid) return false;
      if (opts.type && e.typeId !== opts.type) return false;
      if (opts.families && !opts.families.every((f) => e.__families.has(f))) return false;
      if (opts.location && opts.maxDistance !== undefined) {
        const d = Math.hypot(e.location.x - opts.location.x, e.location.y - opts.location.y, e.location.z - opts.location.z);
        if (d > opts.maxDistance) return false;
      }
      return true;
    });
  }
  getPlayers() {
    return world.getPlayers().filter((p) => p.dimension === this);
  }
}

// ------------------------------------------------------------------ world
const dims = new Map();
for (const id of ["overworld", "nether", "the_end"]) dims.set(id, new Dimension(`minecraft:${id}`));
let startupDone = false;

class TickingAreaManager {
  constructor() {
    this.__areas = new Map();
    this.__pending = [];
    this.maxChunkCount = 100;
  }
  __chunks(o) {
    const cx = Math.abs(Math.floor(o.to.x / 16) - Math.floor(o.from.x / 16)) + 1;
    const cz = Math.abs(Math.floor(o.to.z / 16) - Math.floor(o.from.z / 16)) + 1;
    return cx * cz;
  }
  get chunkCount() {
    let n = 0;
    for (const a of this.__areas.values()) n += this.__chunks(a);
    return n;
  }
  hasCapacity(o) {
    return this.chunkCount + this.__chunks(o) <= this.maxChunkCount;
  }
  hasTickingArea(id) {
    return this.__areas.has(id);
  }
  createTickingArea(id, o) {
    if (!(o.dimension instanceof Dimension)) issue("ticking area needs a Dimension");
    finite(o.from, "ticking from");
    finite(o.to, "ticking to");
    if (this.__areas.has(id)) return Promise.reject(new Error(`TickingAreaError: ${id} exists`));
    if (!this.hasCapacity(o)) return Promise.reject(new Error("TickingAreaError: over capacity"));
    return new Promise((resolve) => {
      // chunks become ready a couple of ticks later
      this.__pending.push(() => {
        this.__areas.set(id, o);
        resolve();
      });
    });
  }
  removeTickingArea(id) {
    if (!this.__areas.has(id)) throw new Error(`TickingAreaError: no ${id}`);
    this.__areas.delete(id);
  }
  getAllTickingAreas() {
    return [...this.__areas.keys()];
  }
}

export const world = {
  __entities: new Map(),
  __players: [],
  __dyn: new Map(),
  __difficulty: Difficulty.Normal,
  tickingAreaManager: new TickingAreaManager(),
  getDimension(id) {
    const short = stripNs(id);
    if (dims.has(short)) return dims.get(short);
    if (dims.has(id)) return dims.get(id);
    throw new Error(`unknown dimension ${id}`);
  },
  getPlayers() {
    return world.__players.filter((p) => p.__valid);
  },
  getAllPlayers() {
    return world.getPlayers();
  },
  getEntity(id) {
    return world.__entities.get(id);
  },
  getDynamicProperty(k) {
    return world.__dyn.get(k);
  },
  setDynamicProperty(k, v) {
    if (v === undefined) world.__dyn.delete(k);
    else world.__dyn.set(k, v);
  },
  getDifficulty() {
    return world.__difficulty;
  },
  getDefaultSpawnLocation() {
    return { x: 0, y: 32767, z: 0 };
  },
  afterEvents: Object.fromEntries(["worldLoad", "itemUse", "entityDie", "playerSpawn", "entitySpawn"].map((n) => [n, new Signal(n)])),
  beforeEvents: Object.fromEntries(["playerBreakBlock", "playerInteractWithBlock", "explosion", "entityHurt"].map((n) => [n, new Signal(n)])),
};

// ------------------------------------------------------------------ harness helpers
export const __commands = new Map();
export const __enums = new Map();
export function __startup() {
  const ev = {
    dimensionRegistry: {
      registerCustomDimension(id) {
        if (startupDone) throw new Error("CustomDimensionInvalidRegistryError");
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(id)) throw new Error("CustomDimensionNameError");
        if (dims.has(id)) throw new Error("CustomDimensionAlreadyRegisteredError");
        dims.set(id, new Dimension(id, true));
      },
    },
    customCommandRegistry: {
      registerEnum(name, values) {
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(name)) issue(`bad enum name ${name}`);
        __enums.set(name, values);
      },
      registerCommand(def, cb) {
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(def.name)) issue(`bad command name ${def.name}`);
        for (const p of def.mandatoryParameters ?? []) {
          if (p.type === "Enum" && !__enums.has(p.name)) issue(`command ${def.name} uses unregistered enum ${p.name}`);
        }
        __commands.set(def.name, { def, cb });
      },
    },
    blockComponentRegistry: {},
    itemComponentRegistry: {},
  };
  system.beforeEvents.startup.fire(ev);
  startupDone = true;
}
export function __runCommand(name, player, ...args) {
  const c = __commands.get(name);
  if (!c) throw new Error(`no command ${name}`);
  if (c.def.permissionLevel > player.commandPermissionLevel) return { status: 1, message: "permission" };
  return c.cb({ sourceEntity: player }, ...args);
}
export function __addPlayer(name, location, op = false) {
  const p = new Player(name, dims.get("overworld"), location);
  if (op) p.commandPermissionLevel = CommandPermissionLevel.Admin;
  world.__players.push(p);
  world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
  return p;
}
export const __dims = dims;
