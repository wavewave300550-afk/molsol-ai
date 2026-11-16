// Strict, minimal emulation of the @minecraft/server 2.11.0 surface used by the add-on.
// Identifiers (animations, controllers, sounds, particles, components) are checked against
// the built packs / vanilla reference so wrong names fail the smoke test.
import fs from "node:fs";

const DATA = JSON.parse(fs.readFileSync(process.env.RWW_MOCK_DATA, "utf8"));
export const __issues = [];
export const __log = { animations: [], sounds: [], particles: [], damage: [], knockback: [], cooldowns: [] };
const issue = (m) => __issues.push(m);

// ------------------------------------------------------------------ enums
export const EntityDamageCause = Object.fromEntries(
  ["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack", "entityExplosion", "fall",
   "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning", "maceSmash", "magic",
   "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom", "soulCampfire",
   "stalactite", "stalagmite", "starve", "suffocation", "temperature", "thorns", "void", "wither"].map((k) => [k, k]),
);
export const EquipmentSlot = { Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet", Mainhand: "Mainhand", Offhand: "Offhand", Body: "Body" };
export const EntityComponentTypes = { Equippable: "minecraft:equippable", Health: "minecraft:health", Tameable: "minecraft:tameable" };
export const ItemComponentTypes = { Cooldown: "minecraft:cooldown" };

// ------------------------------------------------------------------ scheduler
let tick = 0;
let nextId = 1;
const timers = new Map();
const schedule = (fn, delay, interval) => {
  const id = nextId++;
  timers.set(id, { fn, due: tick + Math.max(0, delay), interval });
  return id;
};
class Signal {
  constructor(name) { this.name = name; this.handlers = []; }
  subscribe(fn, options) { this.handlers.push({ fn, options }); return fn; }
  unsubscribe(fn) { this.handlers = this.handlers.filter((h) => h.fn !== fn); }
  fire(ev) { for (const h of this.handlers) h.fn(ev); return ev; }
}
let restricted = false;
const guard = (what) => { if (restricted) issue(`${what} called in restricted-execution (before event)`); };

export const system = {
  get currentTick() { return tick; },
  run: (fn) => schedule(fn, 0),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, i),
  clearRun: (id) => timers.delete(id),
  beforeEvents: { startup: new Signal("startup") },
};
export function __tick(n = 1) {
  for (let k = 0; k < n; k++) {
    tick++;
    for (const [id, t] of [...timers]) {
      if (t.due <= tick) {
        if (t.interval) t.due = tick + t.interval; else timers.delete(id);
        t.fn();
      }
    }
  }
}

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!DATA.items[typeId] && !typeId.startsWith("minecraft:")) issue(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
  }
  getComponent(id) {
    const def = DATA.items[this.typeId];
    if (id === "rww:weapon") {
      if (!def) return undefined;
      return { customComponentParameters: { params: def.params } };
    }
    if (id === "minecraft:cooldown") {
      if (!def) return undefined;
      const stack = this;
      return {
        cooldownCategory: def.cooldown.category,
        cooldownTicks: Math.round(def.cooldown.duration * 20),
        startCooldown(player) { guard("startCooldown"); __log.cooldowns.push({ player: player.name, item: stack.typeId }); },
      };
    }
    issue(`ItemStack.getComponent unknown id ${id}`);
    return undefined;
  }
  getTags() { return DATA.items[this.typeId]?.tags ?? []; }
  hasTag(t) { return this.getTags().includes(t); }
}

// ------------------------------------------------------------------ entities
const entities = new Map();
class Dimension {
  constructor(id) { this.id = id; }
  getEntities(opt = {}) {
    guard("getEntities");
    return [...entities.values()].filter((e) => e.isValid && e.dimension === this && (!opt.location || !opt.maxDistance ||
      Math.hypot(e.location.x - opt.location.x, e.location.y - opt.location.y, e.location.z - opt.location.z) <= opt.maxDistance));
  }
  spawnParticle(id, loc) {
    guard("spawnParticle");
    if (!DATA.particles.includes(id)) issue(`unknown particle ${id}`);
    __log.particles.push({ id, loc });
  }
  playSound(id, loc, opts) {
    guard("playSound");
    if (!DATA.sounds.includes(id)) issue(`unknown sound event ${id}`);
    __log.sounds.push({ id, loc, opts });
  }
}
export const __dims = { overworld: new Dimension("minecraft:overworld"), nether: new Dimension("minecraft:nether") };

export class Entity {
  constructor(typeId, location, opts = {}) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this.location = { ...location };
    this.dimension = opts.dimension ?? __dims.overworld;
    this.health = opts.health ?? (DATA.mobs[typeId]?.health);
    this.tamed = !!opts.tamed;
    this.isValid = true;
    this.isSleeping = false;
    entities.set(this.id, this);
  }
  getComponent(id) {
    if (id === "minecraft:health") return this.health === undefined ? undefined : { currentValue: this.health };
    if (id === "minecraft:tameable") return DATA.mobs[this.typeId]?.tameable ? { isTamed: this.tamed } : undefined;
    if (id === "minecraft:equippable") return undefined;
    issue(`Entity.getComponent unknown id ${id}`);
    return undefined;
  }
  applyDamage(amount, options) {
    guard("applyDamage");
    if (!this.isValid) issue("applyDamage on removed entity");
    if (options && !EntityDamageCause[options.cause]) issue(`bad damage cause ${options.cause}`);
    __log.damage.push({ target: this.id, typeId: this.typeId, amount, options });
    if (amount > 0 && world.__hurt(this, amount, options)) {
      this.health = Math.max(0, (this.health ?? 0) - amount);
    }
    return true;
  }
  applyKnockback(h, v) {
    guard("applyKnockback");
    if (typeof h !== "object" || typeof v !== "number" || !Number.isFinite(h.x) || !Number.isFinite(h.z)) issue("applyKnockback signature (VectorXZ, number)");
    __log.knockback.push({ target: this.id, h, v });
  }
  playAnimation(name, opts = {}) {
    guard("playAnimation");
    if (!DATA.animations.includes(name)) issue(`playAnimation: animation ${name} is not defined in the resource pack`);
    if (opts.controller && !/^controller\.animation\.rww\./.test(opts.controller)) issue(`playAnimation: unexpected controller ${opts.controller}`);
    if (opts.players && !opts.players.every((p) => p instanceof Player)) issue("playAnimation: players must be Player[]");
    __log.animations.push({ holder: this.name ?? this.id, name, opts, tick });
  }
}

export class Player extends Entity {
  constructor(name, location, opts = {}) {
    super("minecraft:player", location, { ...opts, health: 20 });
    this.name = name;
    this.mainhand = undefined;
    this.isEmoting = false;
    this.view = { x: 0, y: 0, z: 1 };
  }
  getComponent(id) {
    if (id === "minecraft:equippable") {
      const p = this;
      return { getEquipment(slot) { if (!EquipmentSlot[slot]) issue(`bad slot ${slot}`); return slot === "Mainhand" ? p.mainhand : undefined; } };
    }
    return super.getComponent(id);
  }
  getViewDirection() { return { ...this.view }; }
}

// ------------------------------------------------------------------ world
export const world = {
  gameRules: { pvp: false },
  afterEvents: { playerSpawn: new Signal("playerSpawn"), playerDimensionChange: new Signal("playerDimensionChange") },
  beforeEvents: { entityHurt: new Signal("entityHurt"), playerLeave: new Signal("playerLeave") },
  getAllPlayers() { return [...entities.values()].filter((e) => e instanceof Player && e.isValid); },
  /** Run the entityHurt before-event chain like the engine; returns false when cancelled. */
  __hurt(target, damage, options) {
    const ev = {
      cancel: false,
      damage,
      hurtEntity: target,
      damageSource: { cause: options?.cause ?? "none", damagingEntity: options?.damagingEntity, damagingProjectile: options?.damagingProjectile },
    };
    for (const h of world.beforeEvents.entityHurt.handlers) {
      const allowed = h.options?.allowedDamageCauses;
      if (allowed && !allowed.includes(ev.damageSource.cause)) continue;
      restricted = true;
      try { h.fn(ev); } finally { restricted = false; }
    }
    __log.lastHurt = ev;
    return !ev.cancel;
  },
};
export function __remove(e) { e.isValid = false; entities.delete(e.id); }
