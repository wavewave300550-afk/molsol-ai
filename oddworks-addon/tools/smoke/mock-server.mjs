// Strict, minimal emulation of the @minecraft/server 2.11 surface used by ODDWORKS.
// Every identifier (particle, sound, effect, entity, block, item, animation, spawn event,
// block state, molang variable) is checked against the built packs + vanilla reference,
// so wrong ids fail the smoke test instead of silently doing nothing in game.
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.ODD_MOCK_DATA, "utf8"));
const SETS = {
  particles: new Set(DATA.particles), sounds: new Set(DATA.sounds), effects: new Set(DATA.effects),
  blocks: new Set(DATA.blocks), items: new Set(DATA.items), animations: new Set(DATA.animations),
};
export const __issues = [];
export const __log = { particles: [], sounds: [], anims: [], cooldowns: [], actionbar: [], commands: [], damage: [], shakes: 0, fades: 0 };
function issue(msg) {
  __issues.push(msg);
}

// ------------------------------------------------------------------ enums
const E = (keys) => Object.fromEntries(keys.map((k) => [k, k]));
export const EntityDamageCause = E(["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack",
  "entityExplosion", "fall", "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning",
  "maceSmash", "magic", "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom",
  "soulCampfire", "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"]);
export const WeatherType = E(["Clear", "Rain", "Thunder"]);
export const Direction = E(["Down", "Up", "North", "South", "East", "West"]);
export const EquipmentSlot = E(["Chest", "Feet", "Head", "Legs", "Mainhand", "Offhand"]);
export const CameraShakeType = E(["Positional", "Rotational"]);
export const GameMode = E(["Adventure", "Creative", "Spectator", "Survival"]);
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const EntityComponentTypes = {
  Inventory: "minecraft:inventory", Health: "minecraft:health", OnFire: "minecraft:onfire", Tameable: "minecraft:tameable",
  Rideable: "minecraft:rideable", Riding: "minecraft:riding", Equippable: "minecraft:equippable", Projectile: "minecraft:projectile",
  Item: "minecraft:item", TypeFamily: "minecraft:type_family",
};
export const ItemComponentTypes = { Durability: "minecraft:durability", Enchantable: "minecraft:enchantable" };

const finite = (v) => Number.isFinite(v);
const finiteV = (v) => v && finite(v.x) && finite(v.y) && finite(v.z);
const vec = (x, y, z) => ({ x, y, z });
const add = (a, b) => vec(a.x + b.x, a.y + b.y, a.z + b.z);
const sub = (a, b) => vec(a.x - b.x, a.y - b.y, a.z - b.z);
const mul = (a, k) => vec(a.x * k, a.y * k, a.z * k);
const len = (a) => Math.hypot(a.x, a.y, a.z);

// ------------------------------------------------------------------ scheduler + signals
let tick = 0;
let nextId = 1;
const timers = new Map();
function schedule(fn, delay, interval) {
  const id = nextId++;
  timers.set(id, { fn, due: tick + Math.max(0, delay), interval });
  return id;
}
class Signal {
  constructor(name, restricted = false) {
    this.name = name;
    this.handlers = [];
    this.restricted = restricted;
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
      const prev = restricted;
      restricted = this.restricted;
      try {
        h(ev);
      } catch (e) {
        issue(`handler for ${this.name} threw: ${e && e.stack ? e.stack : e}`);
      } finally {
        restricted = prev;
      }
    }
    return ev;
  }
}
let restricted = false;
function writeGuard(what) {
  if (restricted) issue(`${what} called inside a before-event (restricted execution)`);
}

export const system = {
  get currentTick() {
    return tick;
  },
  run: (fn) => schedule(fn, 0),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, i),
  clearRun: (id) => timers.delete(id),
  beforeEvents: { startup: new Signal("startup") },
  afterEvents: {},
};

// ------------------------------------------------------------------ blocks
const KNOWN_STATES = {
  "minecraft:water": { liquid_depth: 0 }, "minecraft:flowing_water": { liquid_depth: 1 }, "minecraft:lava": { liquid_depth: 0 },
  "minecraft:flowing_lava": { liquid_depth: 1 }, "minecraft:campfire": { extinguished: false }, "minecraft:soul_campfire": { extinguished: false },
  "minecraft:lever": { open_bit: false }, "minecraft:oak_door": { open_bit: false, upper_block_bit: false }, "minecraft:frosted_ice": { age: 0 },
};
const PASSABLE = (id) => id.startsWith("minecraft:light_block") || ["minecraft:short_grass", "minecraft:tall_grass", "minecraft:fire",
  "minecraft:soul_fire", "minecraft:snow_layer", "minecraft:lever"].includes(id);

export class BlockPermutation {
  constructor(typeId, states) {
    this.type = { id: typeId };
    this.states = { ...(KNOWN_STATES[typeId] ?? {}), ...(states ?? {}) };
  }
  getState(name) {
    if (!(name in this.states)) {
      issue(`getState('${name}') on ${this.type.id}: no such state`);
      return undefined;
    }
    return this.states[name];
  }
  withState(name, value) {
    if (!(name in this.states)) issue(`withState('${name}') on ${this.type.id}: no such state`);
    return new BlockPermutation(this.type.id, { ...this.states, [name]: value });
  }
  getAllStates() {
    return { ...this.states };
  }
  matches(id) {
    return id === this.type.id;
  }
  static resolve(id, states) {
    if (!SETS.blocks.has(id)) issue(`BlockPermutation.resolve unknown block ${id}`);
    return new BlockPermutation(id, states);
  }
}

class Block {
  constructor(dim, x, y, z) {
    this.dimension = dim;
    this.location = vec(x, y, z);
    this.x = x;
    this.y = y;
    this.z = z;
    this.isValid = true;
  }
  get permutation() {
    return this.dimension.__perm(this.x, this.y, this.z);
  }
  get typeId() {
    return this.permutation.type.id;
  }
  get isAir() {
    return this.typeId === "minecraft:air";
  }
  get isLiquid() {
    return /water|lava/.test(this.typeId);
  }
  get isWaterlogged() {
    return false;
  }
  setType(id) {
    writeGuard("Block.setType");
    if (!SETS.blocks.has(id)) issue(`setType unknown block ${id}`);
    this.dimension.__set(this.x, this.y, this.z, new BlockPermutation(id));
  }
  setPermutation(p) {
    writeGuard("Block.setPermutation");
    this.dimension.__set(this.x, this.y, this.z, p);
  }
  above(n = 1) {
    return this.dimension.getBlock(vec(this.x, this.y + n, this.z));
  }
  below(n = 1) {
    return this.dimension.getBlock(vec(this.x, this.y - n, this.z));
  }
  center() {
    return vec(this.x + 0.5, this.y + 0.5, this.z + 0.5);
  }
  bottomCenter() {
    return vec(this.x + 0.5, this.y, this.z + 0.5);
  }
}

// ------------------------------------------------------------------ dimensions
class Dimension {
  constructor(id) {
    this.id = id;
    this.blocks = new Map();
    this.__sky = undefined;
    this.__light = 0;
    this.__biome = "minecraft:plains";
    this.__biomeTags = [];
  }
  __key(x, y, z) {
    return `${x},${y},${z}`;
  }
  __perm(x, y, z) {
    const p = this.blocks.get(this.__key(x, y, z));
    if (p) return p;
    return new BlockPermutation(y < 63 ? "minecraft:stone" : y === 63 ? "minecraft:grass_block" : "minecraft:air");
  }
  __set(x, y, z, perm) {
    this.blocks.set(this.__key(x, y, z), perm);
  }
  getBlock(loc) {
    if (!finiteV(loc)) issue(`getBlock with non-finite location ${JSON.stringify(loc)}`);
    return new Block(this, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
  }
  __solid(b, opts) {
    if (b.isAir) return false;
    if (b.isLiquid) return !!opts?.includeLiquidBlocks;
    if (PASSABLE(b.typeId)) return !!opts?.includePassableBlocks;
    return true;
  }
  getBlockFromRay(origin, dir, opts = {}) {
    if (!finiteV(origin) || !finiteV(dir)) issue("getBlockFromRay with non-finite input");
    const max = opts.maxDistance ?? 64;
    const d = mul(dir, 1 / (len(dir) || 1));
    let prev = vec(Math.floor(origin.x), Math.floor(origin.y), Math.floor(origin.z));
    for (let t = 0; t <= max; t += 0.02) {
      const p = add(origin, mul(d, t));
      const b = this.getBlock(p);
      if (b.x === prev.x && b.y === prev.y && b.z === prev.z && t > 0) continue;
      const moved = vec(b.x - prev.x, b.y - prev.y, b.z - prev.z);
      prev = vec(b.x, b.y, b.z);
      if (this.__solid(b, opts)) {
        const face = moved.y > 0 ? "Down" : moved.y < 0 ? "Up" : moved.x > 0 ? "West" : moved.x < 0 ? "East" : moved.z > 0 ? "North" : "South";
        return { block: b, face, faceLocation: vec(p.x - b.x, p.y - b.y, p.z - b.z) };
      }
    }
    return undefined;
  }
  getBlockBelow(loc, opts = {}) {
    const max = opts.maxDistance ?? 64;
    for (let i = 1; i <= Math.ceil(max); i++) {
      const b = this.getBlock(vec(loc.x, loc.y - i, loc.z));
      if (!b.isAir && !PASSABLE(b.typeId)) return b;
    }
    return undefined;
  }
  getEntities(opts = {}) {
    let list = [...world.__entities.values()].filter((e) => e.isValid && e.dimension === this);
    if (opts.type) list = list.filter((e) => e.typeId === opts.type);
    if (opts.families) list = list.filter((e) => opts.families.every((f) => e.__families.includes(f)));
    if (opts.location && opts.maxDistance !== undefined) list = list.filter((e) => len(sub(e.location, opts.location)) <= opts.maxDistance);
    return list;
  }
  getEntitiesFromRay(origin, dir, opts = {}) {
    const max = opts.maxDistance ?? 64;
    const out = [];
    for (const e of world.__entities.values()) {
      if (!e.isValid || e.dimension !== this || e instanceof Player && e.__isRayOrigin) continue;
      const bb = e.getAABB();
      const inf = opts.__inflate ?? 0;
      bb.extent = vec(bb.extent.x + inf, bb.extent.y + inf, bb.extent.z + inf);
      // slab test
      let t0 = 0;
      let t1 = max;
      let hit = true;
      for (const ax of ["x", "y", "z"]) {
        const lo = bb.center[ax] - bb.extent[ax];
        const hi = bb.center[ax] + bb.extent[ax];
        if (Math.abs(dir[ax]) < 1e-9) {
          if (origin[ax] < lo || origin[ax] > hi) hit = false;
        } else {
          let a = (lo - origin[ax]) / dir[ax];
          let b = (hi - origin[ax]) / dir[ax];
          if (a > b) [a, b] = [b, a];
          t0 = Math.max(t0, a);
          t1 = Math.min(t1, b);
        }
      }
      if (hit && t0 <= t1) out.push({ entity: e, distance: t0 });
    }
    return out.sort((a, b) => a.distance - b.distance);
  }
  spawnParticle(id, loc, molang) {
    writeGuard("spawnParticle");
    if (!SETS.particles.has(id)) issue(`spawnParticle unknown particle ${id}`);
    if (!finiteV(loc)) issue(`spawnParticle ${id} at non-finite location`);
    if (molang && !(molang instanceof MolangVariableMap)) issue("spawnParticle molang is not a MolangVariableMap");
    __log.particles.push(id);
  }
  playSound(id, loc, opts = {}) {
    writeGuard("playSound");
    if (!SETS.sounds.has(id)) issue(`playSound unknown sound ${id}`);
    if (!finiteV(loc)) issue(`playSound ${id} at non-finite location`);
    if (opts.pitch !== undefined && !(opts.pitch > 0 && opts.pitch <= 4)) issue(`playSound ${id} bad pitch ${opts.pitch}`);
    if (opts.volume !== undefined && !(opts.volume >= 0)) issue(`playSound ${id} bad volume ${opts.volume}`);
    __log.sounds.push(id);
  }
  spawnEntity(id, loc, opts = {}) {
    writeGuard("spawnEntity");
    const def = DATA.entities[id];
    if (!def) {
      issue(`spawnEntity unknown entity ${id}`);
      throw new Error(`unknown entity ${id}`);
    }
    if (opts.spawnEvent && !(def.events ?? []).includes(opts.spawnEvent)) issue(`spawnEntity ${id}: unknown spawn event ${opts.spawnEvent}`);
    if (!finiteV(loc)) issue(`spawnEntity ${id} at non-finite location`);
    return world.__add(new Entity(id, this, loc));
  }
  spawnItem(stack, loc) {
    writeGuard("spawnItem");
    if (!(stack instanceof ItemStack)) issue("spawnItem without ItemStack");
    const e = world.__add(new Entity("minecraft:item", this, loc));
    e.__item = stack;
    system.run(() => world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" }));
    return e;
  }
  spawnXp(loc, amount) {
    if (!(amount > 0)) issue("spawnXp amount");
  }
  getSkyLightLevel(loc) {
    if (this.__sky !== undefined) return this.__sky;
    for (let y = Math.floor(loc.y) + 1; y < Math.floor(loc.y) + 24; y++) {
      if (!this.getBlock(vec(loc.x, y, loc.z)).isAir) return 0;
    }
    return 15;
  }
  getLightLevel() {
    return this.__light;
  }
  getBiome() {
    const tags = this.__biomeTags;
    return { id: this.__biome, getTags: () => [...tags], hasTags: (t) => t.every((x) => tags.includes(x)) };
  }
  runCommand(cmd) {
    __log.commands.push(cmd);
    return { successCount: 0 };
  }
}

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!SETS.items.has(typeId)) issue(`ItemStack unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.nameTag = undefined;
    this.keepOnDeath = false;
    this.lockMode = "none";
    this.__lore = [];
    this.__props = new Map();
    const def = DATA.itemDefs[typeId];
    this.__dur = def?.durability ? { damage: 0, maxDurability: def.durability } : undefined;
    this.__ench = def?.enchantable ? [] : undefined;
  }
  get type() {
    return { id: this.typeId };
  }
  getComponent(id) {
    if (id === "minecraft:durability" && this.__dur) {
      const d = this.__dur;
      return {
        get damage() { return d.damage; },
        set damage(v) {
          if (!Number.isInteger(v) || v < 0 || v > d.maxDurability) issue(`durability damage out of range ${v}`);
          d.damage = v;
        },
        maxDurability: d.maxDurability,
        getDamageChance: () => 100,
      };
    }
    if (id === "minecraft:enchantable" && this.__ench) {
      const list = this.__ench;
      return {
        getEnchantments: () => list.map((e) => ({ ...e })),
        getEnchantment: (t) => list.find((e) => e.type.id === t || e.type.id === `minecraft:${t}`),
        canAddEnchantment: () => true,
        addEnchantment: (e) => list.push({ ...e }),
        hasEnchantment: (t) => list.some((e) => e.type.id === t),
      };
    }
    return undefined;
  }
  getLore() {
    return [...this.__lore];
  }
  setLore(l) {
    if ((l ?? []).length > 20) issue("lore too long");
    this.__lore = [...(l ?? [])];
  }
  getDynamicPropertyIds() {
    return [...this.__props.keys()];
  }
  getDynamicProperty(k) {
    return this.__props.get(k);
  }
  setDynamicProperty(k, v) {
    this.__props.set(k, v);
  }
  clone() {
    const c = new ItemStack(this.typeId, this.amount);
    c.nameTag = this.nameTag;
    c.__lore = [...this.__lore];
    if (this.__dur) c.__dur = { ...this.__dur };
    if (this.__ench) c.__ench = this.__ench.map((e) => ({ ...e }));
    c.__props = new Map(this.__props);
    return c;
  }
}

class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
    this.isValid = true;
  }
  getItem(i) {
    return this.slots[i] ? this.slots[i].clone() : undefined;
  }
  setItem(i, st) {
    writeGuard("Container.setItem");
    if (i < 0 || i >= this.size) issue(`setItem slot ${i} out of range`);
    this.slots[i] = st ? st.clone() : undefined;
  }
}

export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  __name(n) {
    if (!/^variable\.[a-z_]+$/.test(n)) issue(`molang variable name ${n}`);
  }
  setVector3(n, v) {
    this.__name(n);
    if (!finiteV(v)) issue(`molang ${n} non-finite vector`);
    this.vars[n] = v;
  }
  setFloat(n, v) {
    this.__name(n);
    if (!finite(v)) issue(`molang ${n} non-finite float ${v}`);
    this.vars[n] = v;
  }
  setColorRGBA(n, c) {
    this.__name(n);
    for (const k of ["red", "green", "blue", "alpha"]) if (!(c[k] >= 0 && c[k] <= 1)) issue(`molang ${n}.${k} out of range ${c[k]}`);
    this.vars[n] = c;
  }
  setColorRGB(n, c) {
    this.setColorRGBA(n, { ...c, alpha: 1 });
  }
  setSpeedAndDirection(n, s, d) {
    this.__name(n);
    if (!finite(s) || !finiteV(d)) issue(`molang ${n} non-finite speed/dir`);
  }
}

// ------------------------------------------------------------------ entities
const SIZE = (id) => DATA.entities[id]?.size ?? [0.6, 1.8];

export class Entity {
  constructor(typeId, dim, loc) {
    this.id = String(nextId++ * 7 + 1000);
    this.typeId = typeId;
    this.dimension = dim;
    this.location = { ...loc };
    this.__rot = { x: 0, y: 180 };
    this.__vel = vec(0, 0, 0);
    this.isValid = true;
    const def = DATA.entities[typeId];
    this.__families = def?.families ?? [];
    this.__maxHealth = def?.health;
    this.__health = def?.health;
    this.__effects = new Map();
    this.__fire = 0;
    this.__props = new Map();
    this.__equip = {};
    this.__projectile = def?.projectile ? { owner: undefined, shot: false } : undefined;
    this.__tamedTo = undefined;
    this.__riding = undefined;
    this.__riders = [];
    this.isSneaking = false;
    this.isOnGround = true;
    this.isInWater = false;
    this.isFalling = false;
    this.nameTag = "";
  }
  get localizationKey() {
    return `entity.${this.typeId}.name`;
  }
  __check(what) {
    if (!this.isValid) {
      const frames = (new Error().stack ?? "").split("\n").filter((l) => l.includes("/scripts/")).slice(0, 3).map((l) => l.trim());
      issue(`${what} on removed entity ${this.typeId} ${frames.join(" <- ")}`);
    }
    return this.isValid;
  }
  getHeadLocation() {
    this.__check("getHeadLocation");
    const h = this instanceof Player ? 1.62 : SIZE(this.typeId)[1] * 0.85;
    return vec(this.location.x, this.location.y + h, this.location.z);
  }
  getRotation() {
    return { ...this.__rot };
  }
  setRotation(r) {
    this.__rot = { ...r };
  }
  getViewDirection() {
    const yaw = (this.__rot.y * Math.PI) / 180;
    const pitch = (this.__rot.x * Math.PI) / 180;
    return vec(-Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
  }
  getVelocity() {
    return { ...this.__vel };
  }
  clearVelocity() {
    this.__vel = vec(0, 0, 0);
  }
  applyImpulse(v) {
    writeGuard("applyImpulse");
    this.__check("applyImpulse");
    if (this instanceof Player) {
      issue("applyImpulse called on a player (throws in game)");
      throw new Error("applyImpulse not supported on players");
    }
    if (!finiteV(v)) issue(`applyImpulse non-finite ${JSON.stringify(v)}`);
    this.__vel = add(this.__vel, v);
  }
  applyKnockback(h, vy) {
    writeGuard("applyKnockback");
    this.__check("applyKnockback");
    if (!h || !finite(h.x) || !finite(h.z) || !finite(vy)) issue("applyKnockback non-finite");
    this.__vel = vec(h.x, vy, h.z);
  }
  teleport(loc) {
    writeGuard("teleport");
    if (!this.__check("teleport")) return;
    if (!finiteV(loc)) issue(`teleport non-finite ${JSON.stringify(loc)}`);
    this.location = { ...loc };
  }
  tryTeleport(loc) {
    this.teleport(loc);
    return true;
  }
  remove() {
    writeGuard("remove");
    if (!this.isValid) issue(`remove() on already removed ${this.typeId}`);
    this.isValid = false;
  }
  kill() {
    this.__die();
    return true;
  }
  addEffect(id, dur, opts = {}) {
    writeGuard("addEffect");
    this.__check("addEffect");
    if (!SETS.effects.has(id)) issue(`addEffect unknown effect ${id}`);
    if (!Number.isInteger(dur) || dur <= 0 || dur > 20000000) issue(`addEffect ${id} bad duration ${dur}`);
    const amp = opts.amplifier ?? 0;
    if (!Number.isInteger(amp) || amp < 0 || amp > 255) issue(`addEffect ${id} bad amplifier ${amp}`);
    this.__effects.set(id, { typeId: id, duration: dur, amplifier: amp });
    return this.__effects.get(id);
  }
  getEffect(id) {
    if (!SETS.effects.has(id)) issue(`getEffect unknown effect ${id}`);
    return this.__effects.get(id);
  }
  removeEffect(id) {
    if (!SETS.effects.has(id)) issue(`removeEffect unknown effect ${id}`);
    return this.__effects.delete(id);
  }
  setOnFire(sec) {
    writeGuard("setOnFire");
    if (!(sec > 0)) issue(`setOnFire bad seconds ${sec}`);
    this.__fire = Math.max(this.__fire, Math.round(sec * 20));
    return true;
  }
  extinguishFire() {
    this.__fire = 0;
    return true;
  }
  getAABB() {
    const [w, h] = SIZE(this.typeId);
    return { center: vec(this.location.x, this.location.y + h / 2, this.location.z), extent: vec(w / 2, h / 2, w / 2) };
  }
  applyDamage(amount, opts = {}) {
    writeGuard("applyDamage");
    if (!this.__check("applyDamage")) return false;
    if (!(amount > 0) || !finite(amount)) issue(`applyDamage bad amount ${amount}`);
    if (!EntityDamageCause[opts.cause]) issue(`applyDamage bad cause ${opts.cause}`);
    if (this.__health === undefined) return false;
    const ev = { hurtEntity: this, damage: amount, cancel: false, damageSource: { cause: opts.cause, damagingEntity: opts.damagingEntity } };
    world.beforeEvents.entityHurt.fire(ev);
    if (ev.cancel) return false;
    this.__hurt(ev.damage, ev.damageSource);
    return true;
  }
  __hurt(amount, source) {
    this.__health -= amount;
    __log.damage.push({ target: this.typeId, amount, cause: source.cause });
    world.afterEvents.entityHurt.fire({ hurtEntity: this, damage: amount, damageSource: source });
    if (this.__health <= 0) this.__die(source);
  }
  __die(source) {
    if (!this.isValid) return;
    world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: source ?? { cause: "none" } });
    if (!(this instanceof Player)) this.isValid = false;
    else this.__health = this.__maxHealth;
  }
  getComponent(id) {
    const self = this;
    switch (id) {
      case "minecraft:health":
        if (this.__health === undefined) return undefined;
        return {
          get currentValue() { return self.__health; }, effectiveMax: this.__maxHealth, defaultValue: this.__maxHealth,
          setCurrentValue: (v) => { self.__health = v; return true; },
        };
      case "minecraft:onfire":
        return this.__fire > 0 ? { onFireTicksRemaining: this.__fire } : undefined;
      case "minecraft:tameable":
        return this.__tamedTo !== undefined ? { isTamed: true, tamedToPlayerId: this.__tamedTo } : undefined;
      case "minecraft:riding":
        return this.__riding ? { entityRidingOn: this.__riding } : undefined;
      case "minecraft:rideable":
        return this.__families.includes("boat") ? { getRiders: () => [...this.__riders] } : undefined;
      case "minecraft:equippable":
        if (!(this instanceof Player) && !this.__hasEquippable) return undefined;
        return {
          totalArmor: this.__armor ?? 0, totalToughness: this.__tough ?? 0,
          getEquipment: (slot) => this.__equip[slot],
          setEquipment: (slot, st) => { this.__equip[slot] = st; return true; },
        };
      case "minecraft:projectile":
        if (!this.__projectile) return undefined;
        return {
          get owner() { return self.__projectile.owner; },
          set owner(o) { self.__projectile.owner = o; },
          shoot(v) {
            if (!finiteV(v)) issue("projectile.shoot non-finite");
            self.__vel = { ...v };
            self.__projectile.shot = true;
          },
        };
      case "minecraft:item":
        return this.__item ? { itemStack: this.__item } : undefined;
      case "minecraft:type_family":
        return { getTypeFamilies: () => [...this.__families], hasTypeFamily: (f) => this.__families.includes(f) };
      default:
        return undefined;
    }
  }
  hasComponent(id) {
    return !!this.getComponent(id);
  }
  getDynamicProperty(k) {
    return this.__props.get(k);
  }
  setDynamicProperty(k, v) {
    this.__props.set(k, v);
  }
  playAnimation(name, opts = {}) {
    writeGuard("playAnimation");
    if (!SETS.animations.has(name)) issue(`playAnimation unknown animation ${name}`);
    __log.anims.push(name);
  }
  runCommand(cmd) {
    writeGuard("runCommand");
    __log.commands.push(cmd);
    let m = cmd.match(/^testfor @s\[hasitem=\{item=([a-z0-9_:]+),location=(slot\.[a-z.]+)\}\]$/);
    if (m) {
      const slot = { "slot.weapon.mainhand": "Mainhand", "slot.armor.chest": "Chest", "slot.armor.head": "Head" }[m[2]];
      if (!slot) issue(`testfor unknown slot ${m[2]}`);
      if (!SETS.items.has(m[1])) issue(`testfor unknown item ${m[1]}`);
      return { successCount: this.__equip[slot]?.typeId === m[1] ? 1 : 0 };
    }
    if (cmd === "replaceitem entity @s slot.weapon.mainhand 0 air") {
      delete this.__equip.Mainhand;
      return { successCount: 1 };
    }
    m = cmd.match(/^camera @s (fov_set (\d+(\.\d+)?) (\d+(\.\d+)?) ([a-z_]+)|fov_clear (\d+(\.\d+)?) ([a-z_]+))$/);
    if (m) {
      const ease = m[6] ?? m[9];
      if (!["linear", "in_out_sine", "out_sine", "in_sine"].includes(ease)) issue(`camera command bad easing ${ease}`);
      return { successCount: 1 };
    }
    issue(`unexpected command: ${cmd}`);
    return { successCount: 0 };
  }
  matches() {
    return true;
  }
}

export class Player extends Entity {
  constructor(name, dim, loc) {
    super("minecraft:player", dim, loc);
    this.name = name;
    this.selectedSlotIndex = 0;
    this.__inv = new Container(36);
    this.__mode = "Survival";
    this.__health = this.__maxHealth = 20;
    this.__cooldowns = new Map();
    this.onScreenDisplay = { setActionBar: (t) => __log.actionbar.push(t), setTitle: () => undefined };
    this.camera = {
      addShake: (o) => {
        if (!(o.intensity > 0 && o.intensity <= 4) || !(o.duration > 0) || !CameraShakeType[o.type]) issue(`camera.addShake bad options ${JSON.stringify(o)}`);
        __log.shakes++;
      },
      fade: (o) => {
        const c = o.fadeColor;
        if (c && ![c.red, c.green, c.blue].every((x) => x >= 0 && x <= 1)) issue("camera.fade colour out of range");
        __log.fades++;
      },
    };
  }
  get isJumping() {
    return false;
  }
  getGameMode() {
    return this.__mode;
  }
  getComponent(id) {
    if (id === "minecraft:inventory") return { container: this.__inv };
    return super.getComponent(id);
  }
  playSound(id, opts = {}) {
    if (!SETS.sounds.has(id)) issue(`player.playSound unknown sound ${id}`);
    if (opts.pitch !== undefined && !(opts.pitch > 0 && opts.pitch <= 4)) issue(`player.playSound ${id} bad pitch ${opts.pitch}`);
    __log.sounds.push(id);
  }
  spawnParticle(id, loc, molang) {
    if (!SETS.particles.has(id)) issue(`player.spawnParticle unknown particle ${id}`);
    if (!finiteV(loc)) issue(`player.spawnParticle ${id} non-finite`);
    __log.particles.push(id);
  }
  startItemCooldown(cat, ticks) {
    writeGuard("startItemCooldown");
    if (typeof cat !== "string" || !cat.includes(":")) issue(`startItemCooldown bad category ${cat}`);
    if (!Number.isInteger(ticks) || ticks < 0 || ticks > 32767) issue(`startItemCooldown bad ticks ${ticks}`);
    this.__cooldowns.set(cat, tick + ticks);
    __log.cooldowns.push([cat, ticks]);
  }
  getItemCooldown(cat) {
    return Math.max(0, (this.__cooldowns.get(cat) ?? 0) - tick);
  }
  sendMessage() {}
}

// ------------------------------------------------------------------ world
const dims = { "minecraft:overworld": new Dimension("minecraft:overworld"), "minecraft:nether": new Dimension("minecraft:nether"), "minecraft:the_end": new Dimension("minecraft:the_end") };
export const world = {
  __entities: new Map(),
  __time: 6000,
  __moon: 0,
  __props: new Map(),
  __add(e) {
    this.__entities.set(e.id, e);
    return e;
  },
  afterEvents: Object.fromEntries(["itemStartUse", "itemReleaseUse", "itemStopUse", "projectileHitBlock", "projectileHitEntity",
    "entityDie", "playerDimensionChange", "entitySpawn", "playerSpawn", "weatherChange", "entityHurt"].map((n) => [n, new Signal(n)])),
  beforeEvents: { entityHurt: new Signal("beforeEvents.entityHurt", true), playerLeave: new Signal("beforeEvents.playerLeave", true) },
  gameRules: { pvp: true },
  getAllPlayers() {
    return [...this.__entities.values()].filter((e) => e instanceof Player && e.isValid);
  },
  getDimension(id) {
    if (!dims[id]) issue(`getDimension unknown ${id}`);
    return dims[id];
  },
  getDynamicProperty(k) {
    return this.__props.get(k);
  },
  setDynamicProperty(k, v) {
    if (typeof v === "string" && v.length > 32000) issue("dynamic property too large");
    this.__props.set(k, v);
  },
  getTimeOfDay() {
    return this.__time;
  },
  getMoonPhase() {
    return this.__moon;
  },
  getLootTableManager() {
    return {
      getLootTable: (path) => {
        if (!DATA.lootTables.includes(`loot_tables/${path}.json`)) {
          issue(`getLootTable unknown ${path}`);
          return undefined;
        }
        return { path };
      },
      generateLootFromTable: (table) => {
        if (!table?.path) issue("generateLootFromTable without table");
        return [new ItemStack("minecraft:salmon", 1)];
      },
    };
  },
};

export function __dimension(id = "minecraft:overworld") {
  return dims[id];
}

/** Advance the simulation: scheduled callbacks, then a crude projectile/physics step. */
export async function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    tick++;
    for (const e of [...world.__entities.values()]) {
      if (!e.isValid) continue;
      if (e.__projectile && e.__projectile.shot && !e.__stuck) stepProjectile(e);
      if (e.__fire > 0) e.__fire--;
      for (const [id, eff] of e.__effects) {
        eff.duration--;
        if (eff.duration <= 0) e.__effects.delete(id);
      }
    }
    for (const [id, t] of [...timers.entries()]) {
      if (t.due > tick || !timers.has(id)) continue;
      if (t.interval) t.due = tick + t.interval;
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

function stepProjectile(e) {
  const from = e.location;
  const to = add(from, e.__vel);
  const d = len(e.__vel);
  if (d > 0) {
    const dir = mul(e.__vel, 1 / d);
    // entity hit first
    const hits = e.dimension.getEntitiesFromRay(from, dir, { maxDistance: d, __inflate: 0.125 }).filter((h) => h.entity !== e && h.entity !== e.__projectile.owner
      && h.entity.typeId !== "minecraft:item");
    const bh = e.dimension.getBlockFromRay(from, dir, { maxDistance: d, includeLiquidBlocks: false });
    if (hits.length && (!bh || hits[0].distance < len(sub(add(bh.block.location, bh.faceLocation), from)))) {
      const target = hits[0].entity;
      e.location = add(from, mul(dir, hits[0].distance));
      world.afterEvents.projectileHitEntity.fire({
        dimension: e.dimension, projectile: e, source: e.__projectile.owner, location: e.location, hitVector: dir,
        getEntityHit: () => ({ entity: target }),
      });
      if (e.isValid) e.isValid = false; // destroy_on_hit
      return;
    }
    if (bh) {
      e.location = add(bh.block.location, bh.faceLocation);
      e.__stuck = true;
      world.afterEvents.projectileHitBlock.fire({
        dimension: e.dimension, projectile: e, source: e.__projectile.owner, location: e.location, hitVector: dir,
        getBlockHit: () => bh,
      });
      return;
    }
  }
  e.location = to;
  e.__vel = vec(e.__vel.x * 0.985, e.__vel.y * 0.985 - 0.045, e.__vel.z * 0.985);
  const b = e.dimension.getBlock(e.location);
  e.isInWater = /water/.test(b.typeId);
}
