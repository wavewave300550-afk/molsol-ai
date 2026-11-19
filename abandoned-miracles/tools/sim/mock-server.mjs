/**
 * A strict stand-in for @minecraft/server, for running the shipped script bundle in Node.
 *
 * It is NOT Minecraft. It models just enough of the world for encounters to run
 * (a floor, entities with health/velocity/properties, players, ticks, events) and
 * it is deliberately unforgiving about everything that can be checked against
 * the real pack files:
 *
 *   - spawnEntity / setProperty / triggerEvent are validated against the behaviour
 *     pack's entity definitions (identifier, property name, type and range, event name);
 *   - spawnParticle must name a particle that exists in the resource pack AND supply
 *     every script-provided Molang variable that particle reads;
 *   - playSound must name a defined sound event; spawnItem a defined item;
 *     structure placement and loot commands must reference real files;
 *   - world-changing calls made inside a before-event callback throw, as they do in game;
 *   - any attempt to change a block fails the run (the add-on must never edit terrain
 *     except through the explicit arena command).
 */
import fs from "node:fs";
import path from "node:path";

export const EntityDamageCause = new Proxy({}, { get: (_, k) => String(k) });
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };
export const EquipmentSlot = { Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet", Mainhand: "Mainhand", Offhand: "Offhand" };
export const EntityComponentTypes = { Equippable: "minecraft:equippable", Health: "minecraft:health", Inventory: "minecraft:inventory" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = new Proxy({}, { get: (_, k) => String(k) });
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const PlayerPermissionLevel = { Visitor: 0, Member: 1, Operator: 2, Custom: 3 };

const BUILTIN_PARTICLE_VARS = new Set([
  "particle_age", "particle_lifetime", "particle_random_1", "particle_random_2", "particle_random_3",
  "particle_random_4", "emitter_age", "emitter_lifetime", "emitter_random_1", "emitter_random_2",
  "emitter_random_3", "emitter_random_4", "entity_scale",
]);

class Signal {
  constructor() {
    this.subs = [];
  }
  subscribe(cb, options) {
    this.subs.push({ cb, options });
    return cb;
  }
  unsubscribe(cb) {
    this.subs = this.subs.filter((s) => s.cb !== cb);
  }
}

/** Simulation state. Reset with sim.reset(packsDir). */
export const sim = {
  tick: 0,
  floorY: 64,
  defs: { entities: new Map(), particles: new Map(), sounds: new Set(), items: new Set(), structures: new Set(), loot: new Set() },
  entities: new Map(),
  players: [],
  restricted: false,
  errors: [],
  after: [],
  runs: [],
  intervals: [],
  commands: new Map(),
  enums: new Map(),
  worldProps: new Map(),
  stats: null,
  /** Optional override: (x, y, z) => "solid" | "air" | "liquid" | undefined (unloaded). */
  blockAt: null,
  nextId: 1,

  reset() {
    this.tick = 0;
    this.entities.clear();
    this.players = [];
    this.restricted = false;
    this.errors = [];
    this.after = [];
    this.runs = [];
    this.blockAt = null;
    this.worldProps.clear();
    this.stats = { particles: 0, particlesByTick: new Map(), maxParticlesPerTick: 0, sounds: 0, items: [], messages: [],
      commands: [], structures: [], spawned: [], maxEntities: 0, actionBars: 0, blockWrites: 0 };
  },

  fail(msg) {
    this.errors.push(`tick ${this.tick}: ${msg}`);
    throw new Error(msg);
  },

  guard(what) {
    if (this.restricted) this.fail(`${what} called in restricted (before-event) context`);
  },

  /** As in the game: while the script module is being evaluated the world cannot be read or changed. */
  early: false,
  needWorld(what) {
    if (this.early) this.fail(`${what} called in early execution (before worldLoad)`);
  },

  loadPacks(root) {
    const bp = firstDir(path.join(root, "behavior_packs"));
    const rp = firstDir(path.join(root, "resource_packs"));
    const d = this.defs;
    for (const k of Object.keys(d)) d[k].clear();
    for (const f of walk(path.join(bp, "entities"))) {
      const j = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
      const fam = j.components?.["minecraft:type_family"]?.family ?? [];
      d.entities.set(j.description.identifier, {
        props: j.description.properties ?? {}, events: new Set(Object.keys(j.events ?? {})), families: fam,
        health: j.components?.["minecraft:health"]?.max ?? 20, summonable: j.description.is_summonable !== false,
      });
    }
    for (const f of walk(path.join(rp, "particles"))) {
      const j = JSON.parse(fs.readFileSync(f, "utf8")).particle_effect;
      const text = JSON.stringify(j.components) + JSON.stringify(j.curves ?? {});
      const vars = new Set();
      for (const m of text.matchAll(/\b(?:v|variable)\.([a-z_0-9]+(?:\.[a-z_0-9]+)?)/g)) {
        if (!BUILTIN_PARTICLE_VARS.has(m[1].split(".")[0])) vars.add(m[1]);
      }
      d.particles.set(j.description.identifier, vars);
    }
    const sd = path.join(rp, "sounds", "sound_definitions.json");
    if (fs.existsSync(sd)) for (const k of Object.keys(JSON.parse(fs.readFileSync(sd, "utf8")).sound_definitions)) d.sounds.add(k);
    for (const f of walk(path.join(bp, "items"))) d.items.add(JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);
    for (const f of walk(path.join(bp, "structures"))) {
      const rel = path.relative(path.join(bp, "structures"), f).replace(/\\/g, "/").replace(/\.mcstructure$/, "");
      const [ns, ...rest] = rel.split("/");
      d.structures.add(rest.length ? `${ns}:${rest.join("/")}` : `mystructure:${ns}`);
    }
    for (const f of walk(path.join(bp, "loot_tables"))) {
      d.loot.add(path.relative(path.join(bp, "loot_tables"), f).replace(/\\/g, "/").replace(/\.json$/, ""));
    }
  },

  block(x, y, z) {
    if (this.blockAt) {
      const r = this.blockAt(Math.floor(x), Math.floor(y), Math.floor(z));
      if (r !== null) return r;
    }
    return y < this.floorY ? "solid" : "air";
  },

  queue(fn) {
    this.after.push(fn);
  },

  flush() {
    let guard = 1000;
    while (this.after.length && guard-- > 0) {
      const q = this.after;
      this.after = [];
      for (const f of q) f();
    }
  },

  /** Run callbacks queued with system.run (the game runs them at the start of the next tick). */
  drainRuns() {
    const runs = this.runs;
    this.runs = [];
    for (const cb of runs) cb();
    this.flush();
  },

  /** Advance the world by one tick. */
  step() {
    this.tick++;
    system.currentTick = this.tick;
    const runs = this.runs;
    this.runs = [];
    for (const f of runs) f();
    for (const it of this.intervals) if (this.tick % it.n === 0) it.cb();
    for (const e of this.entities.values()) e._physics();
    this.flush();
    const n = this.stats.particlesByTick.get(this.tick) ?? 0;
    if (n > this.stats.maxParticlesPerTick) this.stats.maxParticlesPerTick = n;
    this.stats.particlesByTick.clear();
    let live = 0;
    for (const e of this.entities.values()) if (e.isValid && !(e instanceof Player)) live++;
    if (live > this.stats.maxEntities) this.stats.maxEntities = live;
  },

  runCommand(name, source, ...args) {
    const c = this.commands.get(name);
    if (!c) throw new Error(`unknown command ${name}`);
    this.restricted = true;
    let res;
    try {
      res = c.cb({ sourceEntity: source, sourceType: "Entity" }, ...args);
    } finally {
      this.restricted = false;
    }
    return res;
  },
};

function firstDir(p) {
  const d = fs.readdirSync(p).filter((n) => fs.statSync(path.join(p, n)).isDirectory());
  return path.join(p, d[0]);
}

function* walk(dir) {
  if (!fs.existsSync(dir)) return;
  for (const n of fs.readdirSync(dir)) {
    const f = path.join(dir, n);
    if (fs.statSync(f).isDirectory()) yield* walk(f);
    else yield f;
  }
}

// --------------------------------------------------------------------------- components

class Health {
  constructor(owner, max) {
    this.owner = owner;
    this.effectiveMax = max;
    this.currentValue = max;
    this.defaultValue = max;
  }
  setCurrentValue(v) {
    sim.guard("health.setCurrentValue");
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    if (this.currentValue <= 0) this.owner._die({ cause: "none" });
    return true;
  }
  resetToMaxValue() {
    this.currentValue = this.effectiveMax;
  }
}

const KNOWN_ENCHANTS = new Set(["protection", "unbreaking", "sharpness", "mending", "feather_falling", "thorns"]);
export const EnchantmentTypes = { get: (id) => (KNOWN_ENCHANTS.has(id.replace("minecraft:", "")) ? { id: id.replace("minecraft:", "") } : undefined) };
export const ItemComponentTypes = { Enchantable: "minecraft:enchantable" };

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.startsWith("minecraft:") && !sim.defs.items.has(typeId)) sim.fail(`ItemStack: unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.enchants = {};
  }
  getComponent(id) {
    if (id === "minecraft:enchantable") {
      return {
        getEnchantment: (n) => (this.enchants[n] ? { level: this.enchants[n] } : undefined),
        addEnchantment: (e) => {
          if (!e || !e.type || !KNOWN_ENCHANTS.has(e.type.id)) sim.fail(`addEnchantment: bad enchantment ${JSON.stringify(e)}`);
          if (!Number.isInteger(e.level) || e.level < 1 || e.level > 5) sim.fail(`addEnchantment: level ${e.level}`);
          this.enchants[e.type.id] = e.level;
        },
      };
    }
    return undefined;
  }
}

export class MolangVariableMap {
  constructor() {
    this.vars = new Set();
  }
  _add(name, subs = [""]) {
    const base = name.replace(/^variable\./, "").replace(/^v\./, "");
    for (const s of subs) this.vars.add(base + s);
  }
  setFloat(n, v) {
    if (typeof v !== "number" || !Number.isFinite(v)) sim.fail(`MolangVariableMap.setFloat(${n}) with ${v}`);
    this._add(n);
  }
  setVector3(n) {
    this._add(n, [".x", ".y", ".z"]);
  }
  setColorRGB(n) {
    this._add(n, [".r", ".g", ".b"]);
  }
  setColorRGBA(n) {
    this._add(n, [".r", ".g", ".b", ".a"]);
  }
  setSpeedAndDirection(n, speed, dir) {
    if (!Number.isFinite(speed) || !dir) sim.fail(`setSpeedAndDirection(${n}) invalid`);
    this._add(n, [".speed", ".direction_x", ".direction_y", ".direction_z"]);
  }
}

// --------------------------------------------------------------------------- entities

export class Entity {
  constructor(typeId, dimension, location) {
    this.id = String(-(sim.nextId++) * 4294967297);
    this.typeId = typeId;
    this.dimension = dimension;
    this._loc = { ...location };
    this._vel = { x: 0, y: 0, z: 0 };
    this._rot = { x: 0, y: 0 };
    this._valid = true;
    this._tags = new Set();
    this._dyn = new Map();
    this._props = new Map();
    this._effects = new Map();
    this._hurtAt = -100;
    this._events = [];
    const def = sim.defs.entities.get(typeId);
    this._def = def;
    this._health = new Health(this, def ? def.health : 20);
    if (def) for (const [k, p] of Object.entries(def.props)) this._props.set(k, p.default);
    this.nameTag = "";
  }
  get isValid() {
    return this._valid;
  }
  get location() {
    this._need();
    return { ...this._loc };
  }
  _need() {
    if (!this._valid) throw new Error(`entity ${this.typeId} is invalid`);
  }
  getRotation() {
    this._need();
    return { ...this._rot };
  }
  setRotation(r) {
    this._need();
    sim.guard("setRotation");
    if (!Number.isFinite(r.y)) sim.fail("setRotation with non-finite yaw");
    this._rot = { x: r.x, y: r.y };
  }
  getVelocity() {
    this._need();
    return { ...this._vel };
  }
  applyImpulse(v) {
    this._need();
    sim.guard("applyImpulse");
    if (![v.x, v.y, v.z].every(Number.isFinite)) sim.fail("applyImpulse with non-finite vector");
    this._vel.x += v.x;
    this._vel.y += v.y;
    this._vel.z += v.z;
  }
  clearVelocity() {
    sim.guard("clearVelocity");
    this._vel = { x: 0, y: 0, z: 0 };
  }
  applyKnockback(h, v) {
    this._need();
    sim.guard("applyKnockback");
    if (typeof h !== "object" || !Number.isFinite(h.x) || !Number.isFinite(h.z)) sim.fail("applyKnockback: horizontalForce must be {x,z}");
    this._vel.x += h.x * 0.4;
    this._vel.z += h.z * 0.4;
    this._knock = (this._knock ?? 0) + 1;
  }
  teleport(loc, opts = {}) {
    this._need();
    sim.guard("teleport");
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) sim.fail("teleport to non-finite location");
    this._loc = { x: loc.x, y: loc.y, z: loc.z };
    if (opts.rotation) this._rot = { ...opts.rotation };
    if (!opts.keepVelocity) this._vel = { x: 0, y: 0, z: 0 };
    this._teleports = (this._teleports ?? 0) + 1;
  }
  tryTeleport(loc, opts = {}) {
    if (opts.checkForBlocks && sim.block(loc.x, loc.y + 0.5, loc.z) !== "air") return false;
    this.teleport(loc, opts);
    return true;
  }
  getHeadLocation() {
    this._need();
    return { x: this._loc.x, y: this._loc.y + (this._eye ?? 1.0), z: this._loc.z };
  }
  getViewDirection() {
    this._need();
    if (this._aim) return { ...this._aim };
    const y = (this._rot.y * Math.PI) / 180;
    const p = (this._rot.x * Math.PI) / 180;
    return { x: -Math.sin(y) * Math.cos(p), y: -Math.sin(p), z: Math.cos(y) * Math.cos(p) };
  }
  getComponent(id) {
    this._need();
    if (id === "minecraft:health" || id === "health") return this._health;
    if (id === "minecraft:equippable") return this._equip;
    if (id === "minecraft:inventory") return this._inventory;
    return undefined;
  }
  setProperty(name, value) {
    this._need();
    sim.guard("setProperty");
    const p = this._def?.props?.[name];
    if (!p) sim.fail(`${this.typeId}: unknown property ${name}`);
    if (p.type === "int" || p.type === "float") {
      if (typeof value !== "number" || value < p.range[0] || value > p.range[1] || (p.type === "int" && !Number.isInteger(value))) {
        sim.fail(`${this.typeId}: property ${name}=${value} outside ${p.type} range ${JSON.stringify(p.range)}`);
      }
    } else if (p.type === "bool" && typeof value !== "boolean") sim.fail(`${this.typeId}: property ${name} must be boolean`);
    this._props.set(name, value);
  }
  getProperty(name) {
    return this._props.get(name);
  }
  triggerEvent(name) {
    this._need();
    sim.guard("triggerEvent");
    if (!this._def?.events.has(name)) sim.fail(`${this.typeId}: unknown event ${name}`);
    this._events.push(name);
    if (name === "abm:despawn") this._remove();
    if (name === "abm:become_remnant") this._remnantAt = sim.tick;
  }
  setDynamicProperty(k, v) {
    sim.guard("setDynamicProperty");
    if (v === undefined) this._dyn.delete(k);
    else this._dyn.set(k, v);
  }
  getDynamicProperty(k) {
    return this._dyn.get(k);
  }
  addTag(t) {
    sim.guard("addTag");
    this._tags.add(t);
    return true;
  }
  hasTag(t) {
    return this._tags.has(t);
  }
  addEffect(id, ticks, opts = {}) {
    sim.guard("addEffect");
    this._effects.set(String(id), { until: sim.tick + ticks, amplifier: opts.amplifier ?? 0 });
  }
  getEffect(id) {
    const e = this._effects.get(String(id));
    return e && e.until > sim.tick ? { amplifier: e.amplifier, duration: e.until - sim.tick } : undefined;
  }
  remove() {
    this._need();
    sim.guard("entity.remove");
    this._remove();
  }
  kill() {
    sim.guard("entity.kill");
    this._die({ cause: "selfDestruct" });
    return true;
  }
  _remove() {
    this._valid = false;
    sim.entities.delete(this.id);
  }
  _die(source) {
    if (this._dead) return;
    this._dead = true;
    const self = this;
    world.afterEvents.entityDie._fire({ deadEntity: self, damageSource: source }, self.typeId);
    if (!(this instanceof Player)) sim.queue(() => self._remove());
  }
  /** Damage entry point shared by scripts and test bots. */
  applyDamage(amount, opts = {}) {
    this._need();
    sim.guard("applyDamage");
    return this._hurt(amount, { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity, damagingProjectile: opts.damagingProjectile });
  }
  _hurt(amount, source) {
    if (this._dead || sim.tick - this._hurtAt < 10) return false;
    const fam = this._def?.families ?? [];
    const ev = { hurtEntity: this, damage: amount, damageSource: source, cancel: false };
    sim.restricted = true;
    try {
      for (const s of world.beforeEvents.entityHurt.subs) {
        const f = s.options?.entityFilter?.families;
        if (f && !f.every((x) => fam.includes(x))) continue;
        s.cb(ev);
      }
    } finally {
      sim.restricted = false;
    }
    if (ev.cancel || !(ev.damage > 0)) return false;
    this._hurtAt = sim.tick;
    this._health.currentValue = Math.max(0, this._health.currentValue - ev.damage);
    this._damageTaken = (this._damageTaken ?? 0) + ev.damage;
    if (this._health.currentValue <= 0) this._die(source);
    return true;
  }
  _physics() {
    if (!this._valid || this instanceof Player) return;
    this._loc.x += this._vel.x;
    this._loc.z += this._vel.z;
    this._vel.x *= 0.5;
    this._vel.z *= 0.5;
    if (this._remnantAt !== undefined && sim.tick - this._remnantAt >= 600) this._remove();
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this._health = new Health(this, 20);
    this._mode = GameMode.Survival;
    this._eye = 1.62;
    this._armor = 0;
    this._prot = 0;
    this._shield = false;
    this._held = undefined;
    this._xp = 0;
    this.playerPermissionLevel = PlayerPermissionLevel.Operator;
    const self = this;
    this._worn = new Map();
    this._bag = [];
    this._inventory = { container: { addItem: (st) => {
      sim.guard("container.addItem");
      if (!(st instanceof ItemStack)) sim.fail("container.addItem: not an ItemStack");
      self._bag.push(st);
      return undefined;
    } } };
    this._equip = {
      get totalArmor() {
        return self._armor;
      },
      totalToughness: 0,
      getEquipment: (slot) => {
        if (slot === EquipmentSlot.Mainhand) return self._held;
        if (slot === EquipmentSlot.Offhand) return undefined;
        const it = new ItemStack("minecraft:diamond_chestplate");
        it.enchants.protection = self._prot / 4;
        return self._armor > 0 ? it : undefined;
      },
      setEquipment: (slot, item) => {
        sim.guard("setEquipment");
        if (!Object.values(EquipmentSlot).includes(slot)) sim.fail(`setEquipment: unknown slot ${slot}`);
        if (slot === EquipmentSlot.Mainhand) self._held = item;
        else if (item) self._worn.set(slot, item);
        return true;
      },
    };
    this.onScreenDisplay = {
      setActionBar: () => {
        sim.guard("setActionBar");
        sim.stats.actionBars++;
      },
      setTitle: () => sim.guard("setTitle"),
    };
  }
  getGameMode() {
    return this._mode;
  }
  sendMessage(m) {
    sim.guard("sendMessage");
    sim.stats.messages.push({ to: this.name, text: typeof m === "string" ? m : JSON.stringify(m) });
  }
  addExperience(n) {
    sim.guard("addExperience");
    this._xp += n;
  }
  getBlockFromViewDirection() {
    return undefined;
  }
  /** Engine-side damage to a player, with vanilla-like armour so the script's exact-damage logic is exercised. */
  applyDamage(amount, opts = {}) {
    this._need();
    sim.guard("applyDamage");
    if (this._mode === GameMode.Creative || this._mode === GameMode.Spectator) return false;
    if (this._health.currentValue <= 0 || sim.tick - this._hurtAt < 10) return false;
    const cause = opts.cause ?? "none";
    if (this._shield && cause === "entityAttack") return false;
    let d = amount;
    if (cause === "entityAttack") d *= 1 - Math.min(0.8, this._armor * 0.04);
    d *= 1 - Math.min(0.8, this._prot * 0.05);
    this._hurtAt = sim.tick;
    this._health.currentValue = Math.max(0, this._health.currentValue - d);
    this._lastSource = opts.damagingEntity;
    this._hits = (this._hits ?? 0) + 1;
    if (this._health.currentValue <= 0) {
      this._deaths = (this._deaths ?? 0) + 1;
      world.afterEvents.entityDie._fire({ deadEntity: this, damageSource: { cause, damagingEntity: opts.damagingEntity } }, this.typeId);
    }
    return true;
  }
  _disconnect() {
    this._valid = false;
    sim.entities.delete(this.id);
    sim.players = sim.players.filter((p) => p !== this);
    const id = this.id;
    const name = this.name;
    sim.queue(() => world.afterEvents.playerLeave._fire({ playerId: id, playerName: name }));
  }
}

// --------------------------------------------------------------------------- dimension / world / system

class Dimension {
  constructor(id) {
    this.id = id;
  }
  getBlock(loc) {
    const k = sim.block(loc.x, loc.y, loc.z);
    if (k === undefined) return undefined;
    return { isAir: k === "air", isLiquid: k === "liquid", isValid: true, x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z),
      typeId: k === "air" ? "minecraft:air" : "minecraft:stone", setType: () => sim.fail("a block was modified"), setPermutation: () => sim.fail("a block was modified") };
  }
  setBlockType() {
    sim.stats.blockWrites++;
    sim.fail("a block was modified (setBlockType)");
  }
  setBlockPermutation() {
    sim.stats.blockWrites++;
    sim.fail("a block was modified (setBlockPermutation)");
  }
  fillBlocks() {
    sim.stats.blockWrites++;
    sim.fail("blocks were modified (fillBlocks)");
  }
  spawnEntity(typeId, loc, opts = {}) {
    sim.guard("spawnEntity");
    const def = sim.defs.entities.get(typeId);
    if (!def) sim.fail(`spawnEntity: unknown entity ${typeId}`);
    if (!def.summonable) sim.fail(`spawnEntity: ${typeId} is not summonable`);
    if (sim.block(loc.x, loc.y, loc.z) === undefined) throw new Error("LocationInUnloadedChunkError");
    const e = new Entity(typeId, this, loc);
    if (opts.initialRotation !== undefined) e._rot.y = opts.initialRotation;
    sim.entities.set(e.id, e);
    sim.stats.spawned.push(typeId);
    if (def.events.has("minecraft:entity_spawned")) e._events.push("minecraft:entity_spawned");
    sim.queue(() => world.afterEvents.entitySpawn._fire({ entity: e, cause: "Spawned" }));
    return e;
  }
  spawnItem(stack, loc) {
    sim.guard("spawnItem");
    sim.stats.items.push({ typeId: stack.typeId, amount: stack.amount, at: { ...loc } });
    return { isValid: true };
  }
  spawnParticle(id, loc, vars) {
    sim.guard("spawnParticle");
    const need = sim.defs.particles.get(id);
    if (!need && !id.startsWith("minecraft:")) sim.fail(`spawnParticle: unknown particle ${id}`);
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) sim.fail(`spawnParticle ${id}: non-finite location`);
    if (need) for (const v of need) if (!vars || !vars.vars.has(v)) sim.fail(`spawnParticle ${id}: Molang variable '${v}' was not supplied`);
    sim.stats.particles++;
    sim.stats.particlesByTick.set(sim.tick, (sim.stats.particlesByTick.get(sim.tick) ?? 0) + 1);
  }
  playSound(id, loc, opts) {
    sim.guard("playSound");
    if (!sim.defs.sounds.has(id) && !/^[a-z]+\.[a-z_.]+$/.test(id)) sim.fail(`playSound: bad id ${id}`);
    if (id.startsWith("abm.") && !sim.defs.sounds.has(id)) sim.fail(`playSound: undefined sound ${id}`);
    sim.stats.sounds++;
  }
  getPlayers(q = {}) {
    return sim.players.filter((p) => p.isValid && p.dimension === this && near(p, q));
  }
  getEntities(q = {}) {
    const out = [];
    for (const e of sim.entities.values()) {
      if (!e.isValid || e.dimension !== this || !near(e, q)) continue;
      if (q.families && !q.families.every((f) => (e._def?.families ?? []).includes(f))) continue;
      if (q.tags && !q.tags.every((t) => e.hasTag(t))) continue;
      if (q.type && e.typeId !== q.type) continue;
      out.push(e);
    }
    return out;
  }
  runCommand(cmd) {
    sim.guard("runCommand");
    sim.stats.commands.push(cmd);
    const m = /^loot spawn .* loot "([^"]+)"$/.exec(cmd);
    if (m && !sim.defs.loot.has(m[1])) sim.fail(`loot command references missing table ${m[1]}`);
    if (!m && !/^(tickingarea|playsound|title)/.test(cmd)) sim.fail(`unexpected command: ${cmd}`);
    return { successCount: 1 };
  }
}

function near(e, q) {
  if (!q.location || q.maxDistance === undefined) return true;
  const l = e._loc;
  return Math.hypot(l.x - q.location.x, l.y - q.location.y, l.z - q.location.z) <= q.maxDistance;
}

function afterSignal() {
  const s = new Signal();
  s._fire = (ev, typeId) => {
    for (const sub of [...s.subs]) {
      const types = sub.options?.entityTypes;
      if (types && typeId && !types.includes(typeId)) continue;
      sub.cb(ev);
    }
  };
  return s;
}

const dims = new Map();

export const world = {
  afterEvents: {
    worldLoad: afterSignal(), entitySpawn: afterSignal(), entityLoad: afterSignal(), entityDie: afterSignal(),
    playerLeave: afterSignal(), playerInteractWithBlock: afterSignal(), itemUse: afterSignal(), playerSpawn: afterSignal(),
    entityHurt: afterSignal(), entityRemove: afterSignal(),
  },
  beforeEvents: { entityHurt: new Signal(), entityRemove: new Signal(), playerInteractWithBlock: new Signal() },
  getDimension(id) {
    sim.needWorld("world.getDimension");
    const key = id.replace("minecraft:", "");
    if (!["overworld", "nether", "the_end"].includes(key)) throw new Error(`no dimension ${id}`);
    if (!dims.has(key)) dims.set(key, new Dimension("minecraft:" + key));
    return dims.get(key);
  },
  getAllPlayers: () => (sim.needWorld("world.getAllPlayers"), sim.players.filter((p) => p.isValid)),
  getPlayers: () => (sim.needWorld("world.getPlayers"), sim.players.filter((p) => p.isValid)),
  getEntity: (id) => (sim.needWorld("world.getEntity"), sim.entities.get(id)),
  getDynamicProperty: (k) => (sim.needWorld("world.getDynamicProperty"), sim.worldProps.get(k)),
  setDynamicProperty: (k, v) => {
    sim.needWorld("world.setDynamicProperty");
    sim.guard("world.setDynamicProperty");
    sim.worldProps.set(k, v);
  },
  structureManager: {
    place(id, dim, loc) {
      sim.guard("structureManager.place");
      const name = typeof id === "string" ? id : id.id;
      if (!sim.defs.structures.has(name)) sim.fail(`structureManager.place: unknown structure ${name}`);
      sim.stats.structures.push({ id: name, at: { ...loc } });
    },
  },
  sendMessage: (m) => {
    sim.needWorld("world.sendMessage");
    sim.guard("world.sendMessage");
    if (sim.stats) sim.stats.messages.push({ to: "*", text: typeof m === "string" ? m : JSON.stringify(m) });
  },
};

export const system = {
  currentTick: 0,
  beforeEvents: { startup: new Signal(), watchdogTerminate: new Signal() },
  afterEvents: { scriptEventReceive: afterSignal() },
  run(cb) {
    sim.runs.push(cb);
    return sim.runs.length;
  },
  runInterval(cb, n = 1) {
    sim.intervals.push({ cb, n: Math.max(1, n) });
    return sim.intervals.length;
  },
  runTimeout(cb, n = 1) {
    const at = sim.tick + Math.max(1, n);
    const it = { n: 1, cb: () => {
      if (sim.tick >= at && !it.done) {
        it.done = true;
        cb();
      }
    } };
    sim.intervals.push(it);
    return sim.intervals.length;
  },
  clearRun() {},
};

const VANILLA_COMMANDS = new Set(["summon", "kill", "give", "tp", "teleport", "clear", "effect", "enchant", "execute", "fill", "function",
  "gamemode", "gamerule", "help", "list", "locate", "loot", "me", "msg", "tell", "w", "say", "scoreboard", "setblock", "spawnpoint", "structure",
  "tag", "tellraw", "time", "title", "weather", "xp", "clone", "damage", "difficulty", "event", "music", "particle", "playsound", "replaceitem",
  "ride", "schedule", "stopsound", "testfor", "tickingarea", "camera", "dialogue", "fog", "inputpermission", "reload", "scriptevent", "hud",
  "place", "recipe", "transfer", "kick", "op", "deop", "stop", "save", "whitelist", "allowlist", "permission", "setworldspawn", "spreadplayers",
  "daylock", "alwaysday", "mobevent", "ability", "immutableworld", "worldbuilder", "wb", "toggledownfall", "setmaxplayers", "playanimation",
  "camerashake", "clearspawnpoint", "controlscheme", "aimassist", "gametest", "script", "wsserver", "connect", "home", "sethome"]);

/** Called by the harness once the bundle has been imported. */
export function boot() {
  const reg = {
    registerEnum: (name, values) => sim.enums.set(name, values),
    registerCommand: (def, cb) => {
      if (!/^[a-z]+:[a-z_]+$/.test(def.name)) sim.fail(`command name ${def.name} needs a namespace`);
      // the game also registers the part after the colon as an alias and warns when that is a vanilla command
      if (VANILLA_COMMANDS.has(def.name.split(":")[1])) sim.fail(`command alias ${def.name.split(":")[1]} is already a vanilla command`);
      for (const p of [...(def.mandatoryParameters ?? []), ...(def.optionalParameters ?? [])]) {
        if (p.type === "Enum" && !sim.enums.has(p.name)) sim.fail(`command ${def.name}: enum ${p.name} not registered`);
      }
      sim.commands.set(def.name, { def, cb });
    },
  };
  sim.restricted = true;
  try {
    for (const s of system.beforeEvents.startup.subs) s.cb({ customCommandRegistry: reg, itemComponentRegistry: { registerCustomComponent() {} }, blockComponentRegistry: { registerCustomComponent() {} } });
  } finally {
    sim.restricted = false;
  }
  sim.early = false;
  world.afterEvents.worldLoad._fire({});
}

/**
 * A player taps a block with whatever they hold. As in the game, the BEFORE event fires for any block
 * (restricted context); the after event fires only when the block itself reacted, which a floor never does.
 */
export function tapBlock(player, block, stack, interactive = false) {
  sim.restricted = true;
  try {
    for (const sub of world.beforeEvents.playerInteractWithBlock.subs) {
      sub.cb({ player, block, isFirstEvent: true, itemStack: stack, cancel: false, blockFace: "Up", faceLocation: { x: 0.5, y: 1, z: 0.5 } });
    }
  } finally {
    sim.restricted = false;
  }
  if (interactive) world.afterEvents.playerInteractWithBlock._fire({ player, block, isFirstEvent: true, beforeItemStack: stack, itemStack: stack, blockFace: "Up", faceLocation: { x: 0.5, y: 1, z: 0.5 } });
}

export function addPlayer(name, loc, dim = "overworld") {
  const p = new Player(name, world.getDimension(dim), loc);
  sim.entities.set(p.id, p);
  sim.players.push(p);
  return p;
}
