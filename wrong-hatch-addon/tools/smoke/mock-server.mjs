// Strict, minimal emulation of the @minecraft/server API surface used by the add-on.
// Every identifier (particles, sounds, effects, entity types, events, properties,
// commands) is checked against the built packs / vanilla reference, and any misuse
// is recorded in __issues so the smoke test fails loudly.
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.WH_MOCK_DATA, "utf8"));
export const __issues = [];
export const __log = { anims: [], sounds: new Map(), particles: new Map(), commands: [], titles: [], spawned: new Map(), damage: [] };
function issue(msg) {
  if (__issues.length < 200) __issues.push(msg);
}
const finite = (v) => v && Number.isFinite(v.x) && Number.isFinite(v.y) && Number.isFinite(v.z);
const count = (m, k) => m.set(k, (m.get(k) ?? 0) + 1);

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack", "entityExplosion", "fall", "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning", "maceSmash", "magic", "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom", "soulCampfire", "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"].map((k) => [k, k]),
);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const Difficulty = { Peaceful: "Peaceful", Easy: "Easy", Normal: "Normal", Hard: "Hard" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = { Enum: "Enum", String: "String", Integer: "Integer", Float: "Float" };
export const CustomCommandStatus = { Success: 0, Failure: 1 };

// ------------------------------------------------------------------ scheduler / signals
let currentTick = 0;
let nextId = 1;
const timers = new Map();
function schedule(fn, delay, interval) {
  const id = nextId++;
  timers.set(id, { fn, due: currentTick + Math.max(1, delay), interval });
  return id;
}
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
    for (const h of this.handlers) {
      try {
        h(ev);
      } catch (e) {
        issue(`uncaught error in event handler: ${e && e.stack ? e.stack : e}`);
      }
    }
    return ev;
  }
}
export const system = {
  get currentTick() {
    return currentTick;
  },
  run: (fn) => schedule(fn, 1),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, i),
  clearRun: (id) => timers.delete(id),
  beforeEvents: { startup: new Signal() },
  afterEvents: {},
};
const pendingSpawnEvents = [];

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
    while (pendingSpawnEvents.length) {
      const e = pendingSpawnEvents.shift();
      if (e.isValid) world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" });
    }
  }
}

// ------------------------------------------------------------------ values
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(n, v) {
    if (!n.startsWith("variable.") || !Number.isFinite(v)) issue(`bad molang float ${n}=${v}`);
    this.vars[n] = v;
  }
  setColorRGB(n, c) {
    this.vars[n] = c;
  }
  setVector3(n, v) {
    this.vars[n] = v;
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!DATA.items.includes(typeId)) issue(`unknown item ${typeId}`);
    if (!Number.isInteger(amount) || amount < 1 || amount > 64) issue(`bad item amount ${amount}`);
    this.typeId = typeId;
    this.amount = amount;
  }
  getComponent(id) {
    if (id === "minecraft:cooldown") {
      if (!DATA.itemCooldowns.includes(this.typeId)) return undefined;
      return { startCooldown: () => {}, getCooldownTicksRemaining: () => 0 };
    }
    return undefined;
  }
}

class Container {
  constructor(size) {
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i];
  }
  setItem(i, it) {
    this.slots[i] = it;
  }
}

// ------------------------------------------------------------------ terrain
// ground: every block with y < 0 is solid; plus optional wall boxes
export const __terrain = { walls: [] };
function solidAt(x, y, z) {
  const bx = Math.floor(x), by = Math.floor(y), bz = Math.floor(z);
  if (by < 0) return true;
  for (const w of __terrain.walls) if (bx >= w.x0 && bx <= w.x1 && by >= w.y0 && by <= w.y1 && bz >= w.z0 && bz <= w.z1) return true;
  return false;
}
class Block {
  constructor(dim, x, y, z) {
    this.dimension = dim;
    this.location = { x, y, z };
    const s = solidAt(x, y, z);
    this.typeId = s ? "minecraft:stone" : "minecraft:air";
    this.isAir = !s;
    this.isLiquid = false;
    this.isValid = true;
  }
}

// ------------------------------------------------------------------ entities
function groupComponents(def, groups) {
  const comps = { ...(def.components ?? {}) };
  for (const g of groups) Object.assign(comps, def.component_groups?.[g] ?? {});
  return comps;
}

export class EntityHealthComponent {
  constructor(e) {
    this.entity = e;
  }
  get currentValue() {
    return this.entity.__hp;
  }
  get effectiveMax() {
    return this.entity.__maxHp;
  }
  setCurrentValue(v) {
    if (!Number.isFinite(v)) issue(`setCurrentValue(${v})`);
    this.entity.__hp = Math.max(0, Math.min(this.entity.__maxHp, v));
    return true;
  }
}

export class Entity {
  constructor(typeId, dimension, location) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.rotation = { x: 0, y: 0 };
    this.isValid = true;
    this.nameTag = "";
    this.__groups = new Set();
    this.__props = {};
    this.__dyn = {};
    this.__effects = new Map();
    this.__vel = { x: 0, y: 0, z: 0 };
    this.__def = DATA.entities[typeId];
    const comps = this.__comps();
    const hp = comps["minecraft:health"];
    this.__maxHp = hp ? hp.max ?? hp.value : 20;
    this.__hp = this.__maxHp;
    for (const [k, p] of Object.entries(this.__def?.description?.properties ?? {})) this.__props[k] = p.default;
  }
  __comps() {
    return this.__def ? groupComponents(this.__def, this.__groups) : {};
  }
  get families() {
    return this.__comps()["minecraft:type_family"]?.family ?? [];
  }
  get isOnGround() {
    return this.__jumping ? false : this.location.y <= 0.05 || solidAt(this.location.x, this.location.y - 0.1, this.location.z);
  }
  __step() {
    // crude chase emulation for the boss / chicks so the fight moves around
    const g = this.__groups;
    if (this.typeId === "wh:wrong_hatch" && (g.has("wh:chase") || g.has("wh:chase_fast"))) {
      const t = this.dimension.getPlayers({ location: this.location, maxDistance: 48, excludeGameModes: ["Creative", "Spectator"] })[0];
      if (t) {
        const dx = t.location.x - this.location.x, dz = t.location.z - this.location.z;
        const d = Math.hypot(dx, dz);
        if (d > 3.5) {
          const sp = g.has("wh:chase_fast") ? 0.2 : 0.15;
          this.location = { x: this.location.x + (dx / d) * sp, y: this.location.y, z: this.location.z + (dz / d) * sp };
          this.rotation = { x: 0, y: (Math.atan2(-dx, dz) * 180) / Math.PI };
        }
      }
    }
    for (const [k, v] of this.__effects) {
      if (v.duration-- <= 0) this.__effects.delete(k);
    }
  }
  getComponent(id) {
    const comps = this.__comps();
    if (id === "minecraft:health" || id === "health") return comps["minecraft:health"] || this.typeId === "minecraft:player" ? new EntityHealthComponent(this) : undefined;
    if (id === "minecraft:tameable") {
      if (!comps["minecraft:tameable"]) return undefined;
      return { tame: (p) => {
        if (!(p instanceof Player)) issue("tame() needs a player");
        this.__owner = p.id;
        return true;
      } };
    }
    if (id === "minecraft:inventory" || id === "inventory") return this.__inv ? { container: this.__inv } : undefined;
    return undefined;
  }
  addEffect(type, duration, opts = {}) {
    if (!DATA.effects.includes(type)) issue(`unknown effect ${type}`);
    if (!Number.isInteger(duration) || duration <= 0) issue(`bad effect duration ${type} ${duration}`);
    if (opts.amplifier !== undefined && (!Number.isInteger(opts.amplifier) || opts.amplifier < 0 || opts.amplifier > 255)) issue(`bad amplifier ${opts.amplifier}`);
    this.__effects.set(type, { duration, amplifier: opts.amplifier ?? 0 });
    return {};
  }
  getEffect(t) {
    return this.__effects.get(t);
  }
  applyDamage(amount, opts = {}) {
    if (!this.isValid) throw new Error("applyDamage on invalid entity");
    if (!Number.isFinite(amount) || amount < 0) issue(`bad damage amount ${amount}`);
    if (opts.cause && !EntityDamageCause[opts.cause]) issue(`bad damage cause ${opts.cause}`);
    if (opts.damagingEntity && !opts.damagingEntity.isValid) issue("damagingEntity is invalid");
    const ev = { cancel: false, damage: amount, damageSource: { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity }, hurtEntity: this };
    world.beforeEvents.entityHurt.fire(ev);
    if (!Number.isFinite(ev.damage)) issue(`before-event left non-finite damage ${ev.damage}`);
    if (ev.cancel || ev.damage <= 0) return false;
    // damage_sensor: very small subset (cause all / fall)
    const sensor = this.__comps()["minecraft:damage_sensor"];
    if (sensor) {
      const trig = Array.isArray(sensor.triggers) ? sensor.triggers : [sensor.triggers];
      if (trig.some((t) => t.cause === "all" && t.deals_damage === "no")) return false;
    }
    this.__hp -= ev.damage;
    __log.damage.push({ to: this.typeId, amount: ev.damage, from: opts.damagingEntity?.typeId });
    if (this.__hp <= 0) {
      this.__hp = 0;
      if (this.typeId === "minecraft:player") {
        this.__deaths = (this.__deaths ?? 0) + 1;
        this.__hp = this.__maxHp; // instant respawn in place for the test
      } else {
        this.isValid = false;
        world.__entities.delete(this.id);
        world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: ev.damageSource });
      }
    }
    return true;
  }
  applyKnockback(h, vert) {
    if (!h || !Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue(`bad knockback ${JSON.stringify(h)} ${vert}`);
  }
  applyImpulse(v) {
    if (!finite(v)) issue("bad impulse");
  }
  clearVelocity() {}
  getVelocity() {
    return { ...this.__vel };
  }
  setOnFire(s) {
    if (!Number.isFinite(s)) issue("bad fire seconds");
    return true;
  }
  teleport(loc, opts = {}) {
    if (!this.isValid) throw new Error("teleport on invalid entity");
    if (!finite(loc)) issue(`bad teleport location ${JSON.stringify(loc)}`);
    if (opts.rotation && (!Number.isFinite(opts.rotation.x) || !Number.isFinite(opts.rotation.y))) issue("bad teleport rotation");
    this.location = { ...loc };
    if (opts.rotation) this.rotation = { ...opts.rotation };
  }
  setRotation(r) {
    if (!Number.isFinite(r.x) || !Number.isFinite(r.y)) issue(`bad rotation ${JSON.stringify(r)}`);
    this.rotation = { ...r };
  }
  getRotation() {
    return { ...this.rotation };
  }
  getViewDirection() {
    const yaw = (this.rotation.y * Math.PI) / 180;
    const pitch = (this.rotation.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getDynamicProperty(k) {
    return this.__dyn[k];
  }
  setDynamicProperty(k, v) {
    if (v !== undefined && !["boolean", "number", "string", "object"].includes(typeof v)) issue(`bad dynamic property ${k}`);
    this.__dyn[k] = v;
  }
  getProperty(k) {
    return this.__props[k];
  }
  setProperty(k, v) {
    const def = this.__def?.description?.properties?.[k];
    if (!def) {
      issue(`${this.typeId} has no property ${k}`);
      return;
    }
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) issue(`property ${k}=${v} out of range`);
    if (def.type === "bool" && typeof v !== "boolean") issue(`property ${k} expects bool`);
    if (k === "wh:anim") __log.anims.push(v);
    this.__props[k] = v;
  }
  triggerEvent(name) {
    const ev = this.__def?.events?.[name];
    if (!ev) {
      issue(`${this.typeId} has no event ${name}`);
      return;
    }
    const before = this.__comps()["minecraft:health"];
    for (const g of ev.remove?.component_groups ?? []) this.__groups.delete(g);
    for (const g of ev.add?.component_groups ?? []) {
      if (!this.__def.component_groups?.[g]) issue(`${this.typeId} event ${name} adds unknown group ${g}`);
      this.__groups.add(g);
    }
    const after = this.__comps()["minecraft:health"];
    if (after && after !== before) {
      this.__maxHp = after.max ?? after.value;
      this.__hp = Math.min(this.__hp, this.__maxHp);
      if ((ev.add?.component_groups ?? []).some((g) => this.__def.component_groups[g]["minecraft:health"])) this.__hp = after.value;
    }
    if (this.__comps()["minecraft:instant_despawn"]) this.remove();
  }
  remove() {
    if (!this.isValid) return;
    this.isValid = false;
    world.__entities.delete(this.id);
  }
  kill() {
    this.applyDamage(1e9, { cause: "override" });
    return true;
  }
  runCommand(cmd) {
    __log.commands.push(cmd);
    if (!/^camerashake add @s [0-9.]+ [0-9.]+ positional$/.test(cmd)) issue(`unexpected entity command: ${cmd}`);
    return { successCount: 1 };
  }
}

class Screen {
  constructor(p) {
    this.p = p;
  }
  setActionBar(t) {
    if (typeof t !== "string") issue("actionbar text must be string");
    __log.titles.push(t);
  }
  setTitle(t, o) {
    if (typeof t !== "string") issue("title text must be string");
    if (o && o.subtitle !== undefined && typeof o.subtitle !== "string") issue("subtitle must be string");
    __log.titles.push(t);
  }
}

export class Player extends Entity {
  constructor(name, dimension, location) {
    super("minecraft:player", dimension, location);
    this.name = name;
    this.__gm = "Survival";
    this.isSneaking = false;
    this.selectedSlotIndex = 0;
    this.__inv = new Container(36);
    this.onScreenDisplay = new Screen(this);
    this.__xp = 0;
    this.__maxHp = 20;
    this.__hp = 20;
  }
  getGameMode() {
    return this.__gm;
  }
  addExperience(n) {
    if (!Number.isInteger(n)) issue(`addExperience(${n}) must be an integer`);
    this.__xp += n;
    return this.__xp;
  }
  sendMessage() {}
  playSound(id) {
    if (!DATA.sounds.includes(id)) issue(`unknown sound ${id}`);
  }
}

// ------------------------------------------------------------------ dimension
class Dimension {
  constructor(id) {
    this.id = `minecraft:${id}`;
  }
  __all() {
    return [...world.__entities.values()].filter((e) => e.dimension === this && e.isValid);
  }
  getEntities(o = {}) {
    let list = this.__all();
    if (o.type) list = list.filter((e) => e.typeId === o.type);
    if (o.excludeTypes) list = list.filter((e) => !o.excludeTypes.includes(e.typeId));
    if (o.families) list = list.filter((e) => o.families.every((f) => e.families.includes(f)));
    if (o.excludeFamilies) list = list.filter((e) => !o.excludeFamilies.some((f) => e.families.includes(f)));
    if (o.location) {
      if (!finite(o.location)) issue("getEntities with bad location");
      const d = (e) => Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z);
      if (o.maxDistance !== undefined) list = list.filter((e) => d(e) <= o.maxDistance);
      list.sort((a, b) => d(a) - d(b));
      if (o.closest) list = list.slice(0, o.closest);
    } else if (o.maxDistance !== undefined || o.closest) issue("getEntities distance options need a location");
    return list;
  }
  getPlayers(o = {}) {
    let list = this.getEntities({ ...o, type: "minecraft:player" });
    if (o.excludeGameModes) list = list.filter((p) => !o.excludeGameModes.includes(p.getGameMode()));
    return list;
  }
  spawnEntity(id, loc, opts = {}) {
    if (!DATA.entities[id]) throw new Error(`unknown entity ${id}`);
    if (!finite(loc)) issue(`spawnEntity bad location ${JSON.stringify(loc)}`);
    const e = new Entity(id, this, loc);
    if (opts.initialRotation !== undefined) e.rotation = { x: 0, y: opts.initialRotation };
    world.__entities.set(e.id, e);
    count(__log.spawned, id);
    if (e.__def.events?.["minecraft:entity_spawned"]) e.triggerEvent("minecraft:entity_spawned");
    if (opts.spawnEvent) e.triggerEvent(opts.spawnEvent);
    pendingSpawnEvents.push(e);
    return e;
  }
  spawnItem(item, loc) {
    if (!(item instanceof ItemStack)) issue("spawnItem expects an ItemStack");
    if (!finite(loc)) issue("spawnItem bad location");
    count(__log.spawned, `item:${item.typeId}`);
    return new Entity("minecraft:item", this, loc);
  }
  spawnParticle(id, loc, molang) {
    if (!DATA.particles.includes(id)) issue(`unknown particle ${id}`);
    if (!finite(loc)) issue(`particle ${id} at bad location ${JSON.stringify(loc)}`);
    if (molang && !(molang instanceof MolangVariableMap)) issue("molang must be a MolangVariableMap");
    count(__log.particles, id);
  }
  playSound(id, loc, opts = {}) {
    if (!DATA.sounds.includes(id)) issue(`unknown sound ${id}`);
    if (!finite(loc)) issue(`sound ${id} at bad location`);
    if (opts.volume !== undefined && !(opts.volume > 0)) issue(`bad volume ${opts.volume}`);
    if (opts.pitch !== undefined && !(opts.pitch > 0 && opts.pitch <= 4)) issue(`bad pitch ${id} ${opts.pitch}`);
    count(__log.sounds, id);
    return {};
  }
  getBlock(loc) {
    return new Block(this, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
  }
  getBlockFromRay(loc, dir, opts = {}) {
    if (!finite(loc) || !finite(dir)) issue(`bad ray ${JSON.stringify(loc)} ${JSON.stringify(dir)}`);
    const l = Math.hypot(dir.x, dir.y, dir.z);
    if (!(l > 0)) issue("zero-length ray direction");
    const max = opts.maxDistance ?? 64;
    for (let t = 0; t <= max; t += 0.05) {
      const x = loc.x + (dir.x / l) * t, y = loc.y + (dir.y / l) * t, z = loc.z + (dir.z / l) * t;
      if (solidAt(x, y, z)) {
        const b = new Block(this, Math.floor(x), Math.floor(y), Math.floor(z));
        return { block: b, face: "Up", faceLocation: { x: x - b.location.x, y: y - b.location.y, z: z - b.location.z } };
      }
    }
    return undefined;
  }
  runCommand(cmd) {
    __log.commands.push(cmd);
    const m = /^loot spawn (-?[0-9.]+) (-?[0-9.]+) (-?[0-9.]+) loot "([a-z_/]+)"$/.exec(cmd);
    if (!m) {
      issue(`unexpected dimension command: ${cmd}`);
      return { successCount: 0 };
    }
    if (!DATA.lootTables.includes(m[4])) issue(`unknown loot table ${m[4]}`);
    count(__log.spawned, `loot:${m[4]}`);
    return { successCount: 1 };
  }
}

// ------------------------------------------------------------------ world
const dims = { overworld: new Dimension("overworld"), nether: new Dimension("nether"), the_end: new Dimension("the_end") };
export const world = {
  __entities: new Map(),
  __difficulty: "Normal",
  beforeEvents: { entityHurt: new Signal() },
  afterEvents: {
    entitySpawn: new Signal(), entityLoad: new Signal(), entityDie: new Signal(), entityHurt: new Signal(),
    itemUse: new Signal(), itemCompleteUse: new Signal(), entityHitEntity: new Signal(), playerInteractWithBlock: new Signal(),
  },
  getDimension(id) {
    const d = dims[id.replace("minecraft:", "")];
    if (!d) throw new Error(`unknown dimension ${id}`);
    return d;
  },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player);
  },
  getEntity(id) {
    return this.__entities.get(id);
  },
  getDifficulty() {
    return this.__difficulty;
  },
  sendMessage(m) {
    __log.titles.push(String(m));
  },
};

export const __mc = { dims, Dimension };
