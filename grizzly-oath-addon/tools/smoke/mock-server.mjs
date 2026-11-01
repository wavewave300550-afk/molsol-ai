// Strict, minimal emulation of the @minecraft/server 2.11.0 surface that Grizzly's Oath uses.
// Every id the script hands to the engine (particles, sounds, animations, entities, items,
// effects, molang variables, commands) is checked against the real pack files, so a typo or a
// missing asset fails the smoke test instead of silently doing nothing in game.
import fs from "node:fs";
import path from "node:path";

const ADDON = process.env.GO_ADDON;
const RP = path.join(ADDON, "resource_packs", "grizzly_oath");
const BP = path.join(ADDON, "behavior_packs", "grizzly_oath");
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const listJson = (dir) => fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => readJson(path.join(dir, f)));

const PARTICLES = new Map(); // id -> raw json text
for (const f of fs.readdirSync(path.join(RP, "particles"))) {
  const text = fs.readFileSync(path.join(RP, "particles", f), "utf8");
  PARTICLES.set(JSON.parse(text).particle_effect.description.identifier, text);
}
const SOUNDS = new Set(Object.keys(readJson(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions));
const VANILLA_SOUNDS = new Set(["game.player.attack.strong"]);
const ANIMATIONS = new Map();
for (const a of listJson(path.join(RP, "animations"))) for (const [k, v] of Object.entries(a.animations)) ANIMATIONS.set(k, v);
const ENTITY_DEFS = new Map(listJson(path.join(BP, "entities")).map((e) => [e["minecraft:entity"].description.identifier, e]));
const ITEM_DEFS = new Map(listJson(path.join(BP, "items")).map((i) => [i["minecraft:item"].description.identifier, i]));
const VANILLA_ITEMS = new Set(["minecraft:stone", "minecraft:diamond_sword"]);
const EFFECTS = new Set(["resistance", "slowness", "regeneration", "speed", "strength", "weakness"]);

export const __issues = [];
export const __log = { particles: [], sounds: [], anims: [], commands: [], damage: [], knockback: [], effects: [], actionbar: [], messages: [], spawned: [], perTick: new Map() };
const issue = (m) => __issues.push(m);

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["entityAttack", "magic", "fall", "override", "contact", "projectile", "none"].map((k) => [k, k]),
);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const EntitySwingSource = { Attack: "Attack", Build: "Build", DropItem: "DropItem", Event: "Event", Interact: "Interact", Mine: "Mine", None: "None", ThrowItem: "ThrowItem", UseItem: "UseItem" };
export const EntityComponentTypes = { Inventory: "minecraft:inventory", Equippable: "minecraft:equippable", Health: "minecraft:health" };
export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };
export const ItemLockMode = { none: "none", inventory: "inventory", slot: "slot" };

// ------------------------------------------------------------------ scheduler + events
let tick = 0;
let nextTimer = 1;
const timers = new Map();
class Signal {
  constructor() {
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
const sched = (fn, delay, interval) => {
  if (typeof fn !== "function") issue("scheduled a non-function");
  const id = nextTimer++;
  timers.set(id, { fn, due: tick + Math.max(0, delay), interval });
  return id;
};
export const system = {
  get currentTick() {
    return tick;
  },
  run: (fn) => sched(fn, 0),
  runTimeout: (fn, d = 1) => sched(fn, d),
  runInterval: (fn, i = 1) => sched(fn, i, i),
  clearRun: (id) => timers.delete(id),
};
export function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    tick++;
    for (const [id, t] of [...timers]) {
      if (!timers.has(id) || t.due > tick) continue;
      if (t.interval) t.due = tick + t.interval;
      else timers.delete(id);
      try {
        t.fn();
      } catch (e) {
        issue(`uncaught error in scheduled callback: ${e && e.stack ? e.stack : e}`);
      }
    }
  }
}
export const __now = () => tick;

// ------------------------------------------------------------------ molang
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  #set(name, value) {
    if (!/^variable\.[a-z_]+$/.test(name)) issue(`bad molang variable name ${name}`);
    this.vars[name] = value;
  }
  setFloat(n, v) {
    if (!Number.isFinite(v)) issue(`molang ${n} not finite`);
    this.#set(n, v);
  }
  setColorRGBA(n, c) {
    for (const k of ["red", "green", "blue", "alpha"]) if (typeof c[k] !== "number") issue(`color ${n} missing ${k}`);
    this.#set(n, c);
  }
  setVector3(n, v) {
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(v[k])) issue(`vector ${n} bad ${k}`);
    this.#set(n, v);
  }
}

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!ITEM_DEFS.has(typeId) && !VANILLA_ITEMS.has(typeId)) issue(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.nameTag = undefined;
    this.keepOnDeath = false;
    this.lockMode = "none";
    this._lore = [];
    this._dp = new Map();
    const comps = ITEM_DEFS.get(typeId)?.["minecraft:item"].components ?? {};
    this._components = {};
    if (comps["minecraft:durability"]) {
      this._components["minecraft:durability"] = { damage: 0, maxDurability: comps["minecraft:durability"].max_durability };
    }
    if (comps["minecraft:enchantable"]) {
      const list = [];
      this._components["minecraft:enchantable"] = {
        getEnchantments: () => list.map((e) => ({ ...e })),
        addEnchantments: (l) => list.push(...l),
      };
    }
  }
  getComponent(id) {
    return this._components[id];
  }
  getLore() {
    return [...this._lore];
  }
  setLore(l) {
    this._lore = [...(l ?? [])];
  }
  getDynamicPropertyIds() {
    return [...this._dp.keys()];
  }
  getDynamicProperty(id) {
    return this._dp.get(id);
  }
  setDynamicProperty(id, v) {
    if (ITEM_DEFS.get(this.typeId)?.["minecraft:item"].components["minecraft:max_stack_size"] !== 1) issue("dynamic property on stackable item");
    this._dp.set(id, v);
  }
}

class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    if (i < 0 || i >= this.size) throw new Error("slot out of range");
    return this.slots[i];
  }
  setItem(i, item) {
    if (i < 0 || i >= this.size) throw new Error("slot out of range");
    this.slots[i] = item;
  }
}

// ------------------------------------------------------------------ entities
let nextEntity = 1;
const vec = (x, y, z) => ({ x, y, z });
export class Entity {
  constructor(typeId, location, dimension, opts = {}) {
    this.id = String(nextEntity++);
    this.typeId = typeId;
    this.location = { ...location };
    this.dimension = dimension;
    this.families = opts.families ?? [];
    this.height = opts.height ?? 1.9;
    this._valid = true;
    this.maxHealth = opts.health ?? 20;
    this.health = this.maxHealth;
    this.tamed = !!opts.tamed;
    this.yaw = opts.yaw ?? 0;
    this.effects = [];
    dimension.entities.add(this);
  }
  get isValid() {
    return this._valid;
  }
  remove() {
    if (!this._valid) throw new Error(`remove() on invalid entity ${this.typeId}`);
    this._valid = false;
    this.dimension.entities.delete(this);
  }
  #alive(what) {
    if (!this._valid) {
      issue(`${what} on removed entity ${this.typeId}`);
      throw new Error("invalid entity");
    }
  }
  getHeadLocation() {
    this.#alive("getHeadLocation");
    return vec(this.location.x, this.location.y + this.height * 0.9, this.location.z);
  }
  getComponent(id) {
    if (id === "minecraft:health") {
      if (this.maxHealth <= 0) return undefined;
      const self = this;
      return {
        get currentValue() {
          return self.health;
        },
        get effectiveMax() {
          return self.maxHealth;
        },
        setCurrentValue(v) {
          if (!Number.isFinite(v)) issue("setCurrentValue not finite");
          self.health = Math.max(0, Math.min(self.maxHealth, v));
          return true;
        },
      };
    }
    if (id === "minecraft:tameable") return this.tamed ? { isTamed: true, tamedToPlayerId: "x" } : undefined;
    return undefined;
  }
  applyDamage(amount, opts) {
    this.#alive("applyDamage");
    if (!Number.isFinite(amount) || amount <= 0) issue(`bad damage ${amount}`);
    if (opts && opts.cause && !EntityDamageCause[opts.cause]) issue(`bad damage cause ${opts.cause}`);
    __log.damage.push({ tick, target: this, amount, cause: opts?.cause, by: opts?.damagingEntity });
    this.health -= amount;
    return true;
  }
  applyKnockback(h, v) {
    this.#alive("applyKnockback");
    if (typeof h !== "object" || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(v)) issue("applyKnockback(VectorXZ, number) misuse");
    __log.knockback.push({ tick, target: this, h, v });
  }
  addEffect(name, duration, opts) {
    this.#alive("addEffect");
    if (!EFFECTS.has(name)) issue(`unknown effect ${name}`);
    if (!Number.isInteger(duration) || duration < 1) issue(`bad effect duration ${duration}`);
    if (opts?.amplifier !== undefined && (!Number.isInteger(opts.amplifier) || opts.amplifier < 0 || opts.amplifier > 255)) issue("bad amplifier");
    this.effects.push({ tick, name, duration, amplifier: opts?.amplifier ?? 0 });
    __log.effects.push({ tick, target: this, name, duration, amplifier: opts?.amplifier ?? 0 });
  }
  getRotation() {
    return { x: 0, y: this.yaw };
  }
  matchesFamilies(list) {
    return list.some((f) => this.families.includes(f));
  }
}

export class Player extends Entity {
  constructor(name, location, dimension) {
    super("minecraft:player", location, dimension, { families: ["player"], height: 1.8 });
    this.name = name;
    this.isSneaking = false;
    this.selectedSlotIndex = 0;
    this.view = vec(0, 0, 1);
    this.gameMode = GameMode.Survival;
    this._dp = new Map();
    this.inventory = new Container(36);
    this.offhand = undefined;
    const self = this;
    this.onScreenDisplay = {
      setActionBar(text) {
        if (typeof text !== "string") issue("actionbar text must be a string");
        __log.actionbar.push({ tick, player: self, text });
      },
    };
  }
  getComponent(id) {
    if (id === "minecraft:inventory") return { container: this.inventory };
    if (id === "minecraft:equippable") {
      const self = this;
      return {
        getEquipment: (slot) => (slot === "Offhand" ? self.offhand : self.inventory.getItem(self.selectedSlotIndex)),
        setEquipment: (slot, item) => {
          if (slot === "Offhand") self.offhand = item;
          return true;
        },
      };
    }
    return super.getComponent(id);
  }
  getViewDirection() {
    return { ...this.view };
  }
  getGameMode() {
    return this.gameMode;
  }
  getDynamicProperty(id) {
    return this._dp.get(id);
  }
  setDynamicProperty(id, v) {
    if (!id.includes(":")) issue(`dynamic property without namespace: ${id}`);
    this._dp.set(id, v);
  }
  sendMessage(m) {
    __log.messages.push({ tick, player: this, text: String(m) });
  }
  playAnimation(name, opts) {
    if (!ANIMATIONS.has(name)) issue(`unknown animation ${name}`);
    if (opts && opts.blendOutTime !== undefined && !(opts.blendOutTime >= 0)) issue("bad blendOutTime");
    __log.anims.push({ tick, player: this, name });
  }
  teleport(loc, opts) {
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) issue("teleport to non-finite location");
    if (opts && "rotation" in opts && !opts.rotation) issue("bad teleport rotation");
    this.location = { ...loc };
  }
  clearVelocity() {}
  runCommand(cmd) {
    if (!/^camerashake add @a\[r=\d+\] [\d.]+ [\d.]+ (positional|rotational)$/.test(cmd)) issue(`unexpected command: ${cmd}`);
    __log.commands.push({ tick, cmd });
    return { successCount: 1 };
  }
}

// ------------------------------------------------------------------ dimension
export class Dimension {
  constructor(id) {
    this.id = id;
    this.entities = new Set();
    this.solid = new Set(); // "x,y,z" of solid blocks
  }
  getEntities(opts = {}) {
    let list = [...this.entities].filter((e) => e.isValid);
    if (opts.location && opts.maxDistance !== undefined) {
      const L = opts.location;
      list = list.filter((e) => Math.hypot(e.location.x - L.x, e.location.y - L.y, e.location.z - L.z) <= opts.maxDistance);
    }
    if (opts.families) list = list.filter((e) => opts.families.every((f) => e.families.includes(f)));
    if (opts.excludeFamilies) list = list.filter((e) => !e.matchesFamilies(opts.excludeFamilies));
    if (opts.excludeTypes) list = list.filter((e) => !opts.excludeTypes.includes(e.typeId));
    if (opts.type) list = list.filter((e) => e.typeId === opts.type);
    return list;
  }
  spawnEntity(id, loc, opts) {
    const def = ENTITY_DEFS.get(id);
    if (!def) issue(`spawnEntity unknown id ${id}`);
    if (def && !def["minecraft:entity"].description.is_summonable) issue(`${id} is not summonable`);
    if (opts && opts.initialRotation !== undefined && !Number.isFinite(opts.initialRotation)) issue("bad initialRotation");
    const fam = def?.["minecraft:entity"].components["minecraft:type_family"]?.family ?? [];
    const e = new Entity(id, loc, this, { families: fam, yaw: opts?.initialRotation ?? 0 });
    __log.spawned.push({ tick, entity: e });
    return e;
  }
  spawnParticle(id, loc, molang) {
    const text = PARTICLES.get(id);
    if (!text) issue(`unknown particle ${id}`);
    for (const k of ["x", "y", "z"]) if (!Number.isFinite(loc[k])) issue(`particle ${id} at non-finite location`);
    if (text && molang) {
      for (const name of Object.keys(molang.vars)) {
        const short = name.replace("variable.", "");
        if (!text.includes(`v.${short}`) && !text.includes(`variable.${short}`)) issue(`particle ${id} never reads ${name}`);
      }
    }
    const eyes = [...this.entities].filter((e) => e instanceof Player && e.isValid && e.name === "Hugh").map((e) => e.getHeadLocation());
    __log.particles.push({ tick, id, loc: { ...loc }, vars: molang ? { ...molang.vars } : {}, eyes });
    __log.perTick.set(tick, (__log.perTick.get(tick) ?? 0) + 1);
  }
  playSound(id, loc, opts) {
    if (!SOUNDS.has(id) && !VANILLA_SOUNDS.has(id)) issue(`unknown sound ${id}`);
    if (opts && ((opts.volume !== undefined && !(opts.volume > 0)) || (opts.pitch !== undefined && !(opts.pitch > 0)))) issue(`bad sound options for ${id}`);
    __log.sounds.push({ tick, id, loc: { ...loc } });
  }
  getBlockFromRay(from, dir, opts = {}) {
    const max = opts.maxDistance ?? 100;
    const l = Math.hypot(dir.x, dir.y, dir.z);
    for (let s = 0; s <= max; s += 0.05) {
      const p = vec(from.x + (dir.x / l) * s, from.y + (dir.y / l) * s, from.z + (dir.z / l) * s);
      const b = vec(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z));
      if (this.solid.has(`${b.x},${b.y},${b.z}`)) {
        return { block: { location: b, typeId: "minecraft:stone" }, face: "North", faceLocation: vec(p.x - b.x, p.y - b.y, p.z - b.z) };
      }
    }
    return undefined;
  }
}

// ------------------------------------------------------------------ world
const dims = { overworld: new Dimension("minecraft:overworld"), nether: new Dimension("minecraft:nether"), the_end: new Dimension("minecraft:the_end") };
const after = ["itemUse", "playerSwingStart", "entityHitEntity", "playerLeave", "playerSpawn", "worldLoad"];
const before = ["playerInteractWithBlock"];
export const world = {
  afterEvents: Object.fromEntries(after.map((k) => [k, new Signal()])),
  beforeEvents: Object.fromEntries(before.map((k) => [k, new Signal()])),
  gameRules: { pvp: false },
  getDimension: (id) => {
    const d = dims[id.replace("minecraft:", "")];
    if (!d) throw new Error(`unknown dimension ${id}`);
    return d;
  },
  getPlayers: () => [...dims.overworld.entities].filter((e) => e instanceof Player && e.isValid),
};
export const __dims = dims;
