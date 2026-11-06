// Strict, minimal emulation of the @minecraft/server 2.11.0 surface the Dragon Dominion scripts use.
// Everything the scripts hand to the "engine" is checked against the real pack files: particle ids, entity
// property names + int ranges, entity events (and the HP component groups they switch), item ids.
// World: flat stone below y = 64 plus test-defined solid boxes. Vanilla mob AI is NOT emulated.
import fs from "node:fs";
import path from "node:path";

const ADDON = process.env.DD_ADDON;
const RP = path.join(ADDON, "resource_packs", "dragon_dominion");
const BP = path.join(ADDON, "behavior_packs", "dragon_dominion");
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

const PARTICLES = new Set(fs.readdirSync(path.join(RP, "particles")).map((f) =>
  readJson(path.join(RP, "particles", f)).particle_effect.description.identifier));
export const DEFS = new Map();
for (const f of fs.readdirSync(path.join(BP, "entities"))) {
  const d = readJson(path.join(BP, "entities", f))["minecraft:entity"];
  DEFS.set(d.description.identifier, d);
}
const ITEMS = new Set(fs.readdirSync(path.join(BP, "items")).map((f) =>
  readJson(path.join(BP, "items", f))["minecraft:item"].description.identifier));

export const __issues = [];
const issue = (m) => {
  if (!__issues.includes(m)) __issues.push(m);
};
export const __log = { particles: [], sounds: [], damage: [], knockback: [], events: [], props: [], messages: [],
  titles: [], actionbars: [], commands: [], items: [], spawned: [] };

export const EntityDamageCause = new Proxy({}, { get: (_, k) => String(k) });
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };

export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(k, v) {
    if (typeof v !== "number" || !Number.isFinite(v)) issue(`molang var ${k} not finite`);
    this.vars[k] = v;
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!typeId.startsWith("minecraft:") && !ITEMS.has(typeId)) issue(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
  }
}

// ------------------------------------------------------------------------------------------ events
function signal() {
  const subs = [];
  return { subscribe: (f) => (subs.push(f), f), unsubscribe: (f) => subs.splice(subs.indexOf(f), 1), fire: (ev) => subs.forEach((f) => f(ev)), subs };
}
export const world = {
  afterEvents: { entitySpawn: signal(), entityLoad: signal(), entityDie: signal(), entityHurt: signal(), playerLeave: signal(), itemUse: signal() },
  beforeEvents: { entityRemove: signal(), entityHurt: signal() },
  getDimension: (id) => dims[id.replace("minecraft:", "")],
};

// ------------------------------------------------------------------------------------------ system
let tickNo = 0;
let runId = 0;
const runs = new Map();
export const system = {
  get currentTick() {
    return tickNo;
  },
  run(fn) {
    return this.runTimeout(fn, 0);
  },
  runTimeout(fn, d = 1) {
    const id = ++runId;
    runs.set(id, { fn, at: tickNo + Math.max(0, d), every: 0 });
    return id;
  },
  runInterval(fn, every = 1) {
    const id = ++runId;
    runs.set(id, { fn, at: tickNo + every, every });
    return id;
  },
  clearRun(id) {
    runs.delete(id);
  },
};
export const __runCount = () => runs.size;
export function __tick(n = 1) {
  for (let i = 0; i < n; i++) {
    tickNo++;
    for (const [id, r] of [...runs]) {
      if (!runs.has(id) || r.at > tickNo) continue;
      if (r.every) r.at = tickNo + r.every;
      else runs.delete(id);
      r.fn();
    }
    for (const e of allEntities()) e.__physics();
  }
}
export const __now = () => tickNo;

// ------------------------------------------------------------------------------------------ terrain
export const __solids = [];
const GROUND = 64;
export function __solidAt(x, y, z) {
  if (y < GROUND) return true;
  for (const b of __solids) if (x >= b.min.x && x < b.max.x && y >= b.min.y && y < b.max.y && z >= b.min.z && z < b.max.z) return true;
  return false;
}
class Block {
  constructor(x, y, z) {
    this.location = { x, y, z };
    const s = __solidAt(x + 0.5, y + 0.5, z + 0.5);
    this.typeId = s ? "minecraft:stone" : "minecraft:air";
    this.isAir = !s;
    this.isLiquid = false;
  }
}

// ------------------------------------------------------------------------------------------ entities
let nextId = 1;
const entities = new Map();
const allEntities = () => [...entities.values()];

class Health {
  constructor(e, v) {
    this.e = e;
    this.currentValue = v;
    this.effectiveMax = v;
    this.effectiveMin = 0;
    this.defaultValue = v;
  }
  resetToMaxValue() {
    this.currentValue = this.effectiveMax;
  }
  setCurrentValue(v) {
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
}

export class Entity {
  constructor(typeId, loc, dim) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this.location = { ...loc };
    this.dimension = dim;
    this.isValid = true;
    this.rot = { x: 0, y: 0 };
    this.props = {};
    this.dyn = {};
    this.groups = new Set();
    this.isOnGround = true;
    this.def = DEFS.get(typeId);
    const hp = this.def?.components?.["minecraft:health"]?.value ?? 20;
    this.health = new Health(this, hp);
    if (this.def) for (const [k, p] of Object.entries(this.def.description.properties ?? {})) this.props[k] = p.default;
    entities.set(this.id, this);
  }
  getRotation() {
    return { ...this.rot };
  }
  setRotation(r) {
    if (!Number.isFinite(r.y)) issue("setRotation NaN");
    this.rot = { x: r.x, y: r.y };
  }
  teleport(p, o = {}) {
    if (![p.x, p.y, p.z].every(Number.isFinite)) issue("teleport to NaN");
    this.location = { ...p };
    if (o.rotation) this.setRotation(o.rotation);
  }
  getComponent(id) {
    if (id === "minecraft:health") return this.health;
    if (id === "minecraft:inventory") return this.inv;
    return undefined;
  }
  triggerEvent(name) {
    const ev = this.def?.events?.[name];
    if (!ev) {
      issue(`${this.typeId}: unknown event ${name}`);
      return;
    }
    __log.events.push({ entity: this, name, tick: tickNo });
    for (const g of ev.remove?.component_groups ?? []) this.groups.delete(g);
    for (const g of ev.add?.component_groups ?? []) {
      const cg = this.def.component_groups[g];
      if (!cg) issue(`missing group ${g}`);
      this.groups.add(g);
      const h = cg?.["minecraft:health"];
      if (h) {
        this.health.effectiveMax = h.max;
        this.health.currentValue = h.value;
      }
    }
  }
  setProperty(k, v) {
    const p = this.def?.description?.properties?.[k];
    if (!p) issue(`unknown property ${k}`);
    else if (p.type === "int" && (!Number.isInteger(v) || v < p.range[0] || v > p.range[1])) issue(`property ${k}=${v} out of range`);
    this.props[k] = v;
    __log.props.push({ entity: this, key: k, value: v, tick: tickNo });
  }
  getProperty(k) {
    return this.props[k];
  }
  setDynamicProperty(k, v) {
    if (v === undefined) delete this.dyn[k];
    else this.dyn[k] = v;
  }
  getDynamicProperty(k) {
    return this.dyn[k];
  }
  applyDamage(amount, opts = {}) {
    if (!this.isValid) throw new Error("invalid entity");
    const src = { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity, damagingProjectile: opts.damagingProjectile };
    const before = { damage: amount, cancel: false, damageSource: src, hurtEntity: this };
    world.beforeEvents.entityHurt.fire(before);
    if (before.cancel || before.damage <= 0) return false;
    this.health.currentValue -= before.damage;
    __log.damage.push({ target: this, amount: before.damage, source: src.damagingEntity, tick: tickNo });
    world.afterEvents.entityHurt.fire({ damage: before.damage, damageSource: src, hurtEntity: this });
    if (this.health.currentValue <= 0 && this.isValid) {
      this.isValid = false;
      entities.delete(this.id);
      world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: src });
    }
    return true;
  }
  applyKnockback(h, v) {
    if (!Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(v)) issue("knockback NaN");
    __log.knockback.push({ target: this, h, v, tick: tickNo });
  }
  runCommand(cmd) {
    __log.commands.push({ entity: this, cmd, tick: tickNo });
    return { successCount: 1 };
  }
  sendMessage(m) {
    __log.messages.push({ to: this, text: m, tick: tickNo });
  }
  remove() {
    if (!this.isValid) throw new Error("invalid entity");
    world.beforeEvents.entityRemove.fire({ removedEntity: this });
    this.isValid = false;
    entities.delete(this.id);
  }
  __physics() {
    if (this.typeId === "minecraft:player") return;
    // gravity only for non-script-placed bosses on the ground group; scripts teleport every tick in combat
  }
  __unload() {
    this.isValid = false;
    entities.delete(this.id);
  }
}

export class Player extends Entity {
  constructor(name, loc, dim, gm = "Survival") {
    super("minecraft:player", loc, dim);
    this.name = name;
    this.gm = gm;
    this.selectedSlotIndex = 0;
    this.inv = { container: { items: [], getItem: (i) => this.inv.container.items[i], setItem: (i, it) => (this.inv.container.items[i] = it) } };
    this.onScreenDisplay = {
      setActionBar: (t) => __log.actionbars.push({ to: this, text: t, tick: tickNo }),
      setTitle: (t, o) => __log.titles.push({ to: this, text: t, sub: o?.subtitle, tick: tickNo }),
    };
  }
  getGameMode() {
    return this.gm;
  }
}

class Dimension {
  constructor(id) {
    this.id = `minecraft:${id}`;
  }
  getBlock(p) {
    return new Block(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z));
  }
  getPlayers(q = {}) {
    return this.getEntities({ ...q, type: "minecraft:player" });
  }
  getEntities(q = {}) {
    return allEntities().filter((e) => e.dimension === this && (!q.type || e.typeId === q.type) &&
      (!q.location || Math.hypot(e.location.x - q.location.x, e.location.y - q.location.y, e.location.z - q.location.z) <= (q.maxDistance ?? Infinity)));
  }
  spawnEntity(typeId, loc) {
    if (!typeId.startsWith("minecraft:") && !DEFS.has(typeId)) issue(`spawn unknown ${typeId}`);
    const e = new Entity(typeId, loc, this);
    __log.spawned.push({ typeId, loc, tick: tickNo });
    if (DEFS.has(typeId)) {
      e.triggerEvent("minecraft:entity_spawned");
      world.afterEvents.entitySpawn.fire({ entity: e });
    }
    return e;
  }
  spawnItem(stack, loc) {
    __log.items.push({ typeId: stack.typeId, amount: stack.amount, loc, tick: tickNo });
    return new Entity("minecraft:item", loc, this);
  }
  spawnParticle(id, loc, vars) {
    if (!PARTICLES.has(id)) issue(`unknown particle ${id}`);
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) issue(`particle ${id} at NaN`);
    __log.particles.push({ id, loc, vars: vars?.vars, tick: tickNo });
  }
  playSound(id, loc, o) {
    __log.sounds.push({ id, loc, tick: tickNo });
  }
}
const dims = { overworld: new Dimension("overworld"), nether: new Dimension("nether"), the_end: new Dimension("the_end") };
export const __dim = dims.overworld;

export function __spawnPlayer(name, loc, gm = "Survival") {
  return new Player(name, loc, dims.overworld, gm);
}
export function __summon(loc, yaw = 0) {
  const e = __dim.spawnEntity("dragon_dominion:gharvok", loc);
  e.setRotation({ x: 0, y: yaw });
  return e;
}
export function __reload(e) {
  // the same entity (same id + dynamic properties) comes back when its chunk reloads
  e.isValid = true;
  entities.set(e.id, e);
  world.afterEvents.entityLoad.fire({ entity: e });
}
export function __clearWorld() {
  for (const e of allEntities()) {
    e.isValid = false;
    entities.delete(e.id);
  }
  __solids.length = 0;
}
