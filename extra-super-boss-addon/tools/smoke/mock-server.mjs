// Strict, minimal emulation of the @minecraft/server 2.11.0 surface used by the Extra Super Boss scripts
// (adapted from the Dragon or Draco smoke test).  Everything the script hands to the engine is checked
// against the real pack files: particle ids (+ the molang variables they read), entity property names and
// values (enum values, int ranges), entity events and the component groups they switch, spawnable types.
// World: flat ground (solid below y = 64) plus test-defined solid boxes; gravity only while esb:ground is
// active and esb:air is not.  Vanilla AI (walking, the delayed melee) is NOT emulated.
import fs from "node:fs";
import path from "node:path";

const ADDON = process.env.ESB_ADDON;
const RP = path.join(ADDON, "resource_packs", "extra_super_boss");
const BP = path.join(ADDON, "behavior_packs", "extra_super_boss");
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

const PARTICLES = new Map();
for (const f of fs.readdirSync(path.join(RP, "particles"))) {
  const text = fs.readFileSync(path.join(RP, "particles", f), "utf8");
  PARTICLES.set(JSON.parse(text).particle_effect.description.identifier, text);
}
export const DEFS = new Map();
for (const f of fs.readdirSync(path.join(BP, "entities"))) {
  const d = readJson(path.join(BP, "entities", f))["minecraft:entity"];
  DEFS.set(d.description.identifier, d);
}

export const __issues = [];
export const __log = {
  particles: [], sounds: [], damage: [], knockback: [], events: [], props: [], died: [], spawned: [], shots: [],
  teleports: [], messages: [], titles: [], actionbars: [], effects: [],
};
const issue = (m) => {
  if (!__issues.includes(m)) __issues.push(m);
};

// ------------------------------------------------------------------------------------------ enums
export const EntityDamageCause = new Proxy({}, { get: (_, k) => String(k) });
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };
export const EntityInitializationCause = { Born: "Born", Event: "Event", Loaded: "Loaded", Spawned: "Spawned", Transformed: "Transformed" };

export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(name, v) {
    this.vars[name] = v;
  }
}

// ------------------------------------------------------------------------------------------ world geometry
export const __solids = []; // {min:{x,y,z}, max:{x,y,z}} inclusive-exclusive boxes
const GROUND = 64;
function solidAt(x, y, z) {
  if (y < GROUND) return true;
  for (const b of __solids) if (x >= b.min.x && x < b.max.x && y >= b.min.y && y < b.max.y && z >= b.min.z && z < b.max.z) return true;
  return false;
}
function topAt(x, z, below = Infinity) {
  let top = GROUND;
  for (const b of __solids) {
    if (x >= b.min.x && x < b.max.x && z >= b.min.z && z < b.max.z && b.max.y <= below + 0.01) top = Math.max(top, b.max.y);
  }
  return top;
}

// ------------------------------------------------------------------------------------------ system / events
let tickNo = 0;
const intervals = [];
let queue = [];
const timeouts = [];
export const system = {
  get currentTick() {
    return tickNo;
  },
  run(fn) {
    queue.push(fn);
    return queue.length;
  },
  runInterval(fn, every = 1) {
    intervals.push({ fn, every });
    return intervals.length;
  },
  runTimeout(fn, delay = 1) {
    timeouts.push({ fn, at: tickNo + delay });
    return timeouts.length;
  },
};

function signal() {
  const subs = [];
  return {
    subs,
    subscribe(fn, opts) {
      subs.push({ fn, opts });
      return fn;
    },
    unsubscribe(fn) {
      const i = subs.findIndex((s) => s.fn === fn);
      if (i >= 0) subs.splice(i, 1);
    },
  };
}

// ------------------------------------------------------------------------------------------ entities
let nextId = 1;
const allEntities = new Set();
let restricted = false;

class Entity {
  constructor(typeId, loc, dimension) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this.location = { ...loc };
    this.rotation = { x: 0, y: 0 };
    this.velocity = { x: 0, y: 0, z: 0 };
    this.dimension = dimension;
    this.isValid = true;
    this.families = [];
    this.health = { currentValue: 20, effectiveMax: 20 };
    this.dyn = {};
    this.props = {};
    this.groups = new Set();
    this.dead = false;
    const def = DEFS.get(typeId);
    if (def) {
      this.families = [...(def.components["minecraft:type_family"]?.family ?? [])];
      const hp = def.components["minecraft:health"]?.value;
      if (hp) this.health = { currentValue: hp, effectiveMax: hp };
      for (const [k, p] of Object.entries(def.description.properties ?? {})) this.props[k] = p.default;
      if (def.components["minecraft:projectile"]) this.projectile = { owner: undefined, shot: undefined, owner_set: false };
    }
    allEntities.add(this);
  }
  get isOnGround() {
    return this.location.y <= topAt(this.location.x, this.location.z, this.location.y) + 0.01;
  }
  getComponent(id) {
    if (restricted && id !== "minecraft:health") issue(`getComponent(${id}) in restricted mode`);
    if (id === "minecraft:health" || id === "health") return this.dead ? undefined : this.health;
    if (id === "minecraft:projectile" && this.projectile) {
      const self = this;
      return {
        get owner() {
          return self.projectile.owner;
        },
        set owner(v) {
          self.projectile.owner = v;
        },
        shoot(velocity, opts) {
          self.projectile.shot = { velocity, opts, tick: tickNo };
          __log.shots.push({ tick: tickNo, gear: self, velocity, owner: self.projectile.owner, at: { ...self.location } });
        },
      };
    }
    if (id === "minecraft:inventory" && this.container) return { container: this.container };
    issue(`getComponent(${id}) not emulated for ${this.typeId}`);
    return undefined;
  }
  getRotation() {
    return { ...this.rotation };
  }
  setRotation(r) {
    if (restricted) issue("setRotation in restricted mode");
    this.rotation = { x: r.x, y: r.y };
  }
  teleport(p, opts = {}) {
    if (restricted) issue("teleport in restricted mode");
    if (![p.x, p.y, p.z].every(Number.isFinite)) issue("teleport to a non-finite position");
    this.location = { ...p };
    if (opts.rotation) this.rotation = { ...opts.rotation };
    if (opts.keepVelocity === false) this.velocity = { x: 0, y: 0, z: 0 };
    __log.teleports.push({ tick: tickNo, entity: this, at: { ...p } });
  }
  getViewDirection() {
    const y = (this.rotation.y * Math.PI) / 180;
    return { x: -Math.sin(y), y: 0, z: Math.cos(y) };
  }
  getVelocity() {
    return { ...this.velocity };
  }
  clearVelocity() {
    if (this.typeId === "minecraft:player") throw new Error("clearVelocity on player");
    this.velocity = { x: 0, y: 0, z: 0 };
  }
  applyImpulse(v) {
    if (this.typeId === "minecraft:player") throw new Error("applyImpulse on player");
    this.velocity = { x: this.velocity.x + v.x, y: this.velocity.y + v.y, z: this.velocity.z + v.z };
  }
  applyKnockback(h, vertical) {
    if (typeof h !== "object" || !("x" in h) || !("z" in h)) issue("applyKnockback needs a VectorXZ");
    __log.knockback.push({ tick: tickNo, target: this, h, vertical });
  }
  matches(opts) {
    if (opts.families && !opts.families.every((f) => this.families.includes(f))) return false;
    return true;
  }
  getDynamicProperty(k) {
    return this.dyn[k];
  }
  setDynamicProperty(k, v) {
    this.dyn[k] = v;
  }
  getProperty(k) {
    return this.props[k];
  }
  setProperty(k, v) {
    if (restricted) issue("setProperty in restricted mode");
    const def = DEFS.get(this.typeId)?.description.properties?.[k];
    if (!def) return issue(`unknown property ${k} on ${this.typeId}`);
    if (def.type === "enum" && !def.values.includes(v)) return issue(`property ${k}: '${v}' not in enum`);
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) return issue(`property ${k}: ${v} outside ${def.range}`);
    if (this.props[k] !== v) __log.props.push({ tick: tickNo, entity: this, key: k, value: v });
    this.props[k] = v;
  }
  triggerEvent(name) {
    if (restricted) issue("triggerEvent in restricted mode");
    const def = DEFS.get(this.typeId);
    if (!def) return issue(`triggerEvent on ${this.typeId}`);
    const ev = def.events[name];
    if (!ev) return issue(`unknown entity event ${name}`);
    __log.events.push({ tick: tickNo, entity: this, name });
    for (const g of ev.remove?.component_groups ?? []) this.groups.delete(g);
    for (const g of ev.add?.component_groups ?? []) {
      if (!def.component_groups[g]) issue(`unknown component group ${g}`);
      this.groups.add(g);
    }
  }
  addEffect(type, duration, opts) {
    __log.effects.push({ tick: tickNo, target: this, type, duration, opts });
    return {};
  }
  sendMessage(m) {
    __log.messages.push({ tick: tickNo, target: this, m });
  }
  applyDamage(amount, opts = {}) {
    if (restricted) issue("applyDamage in restricted mode");
    if (this.dead || !this.isValid) return false;
    if (this.typeId === "minecraft:player" && (this.gm === "Creative" || this.gm === "Spectator")) return false;
    const ev = { hurtEntity: this, damage: amount, damageSource: { cause: opts.cause, damagingEntity: opts.damagingEntity }, cancel: false };
    for (const s of world.beforeEvents.entityHurt.subs) {
      const f = s.opts?.entityFilter;
      if (f?.type && f.type !== this.typeId) continue;
      restricted = true;
      try {
        s.fn(ev);
      } finally {
        restricted = false;
      }
    }
    if (ev.cancel) return false;
    this.health.currentValue = Math.max(0, this.health.currentValue - ev.damage);
    __log.damage.push({ tick: tickNo, target: this, amount: ev.damage, cause: opts.cause, by: opts.damagingEntity });
    for (const s of world.afterEvents.entityHurt.subs) {
      const types = s.opts?.entityTypes;
      if (types && !types.includes(this.typeId)) continue;
      s.fn({ hurtEntity: this, damage: ev.damage, damageSource: ev.damageSource });
    }
    if (this.health.currentValue <= 0) this.die(ev.damageSource);
    return true;
  }
  kill() {
    return this.applyDamage(this.health.currentValue + 1, { cause: "selfDestruct" });
  }
  die(src) {
    this.dead = true;
    this.deathTick = tickNo;
    __log.died.push({ tick: tickNo, entity: this, src });
    for (const s of world.afterEvents.entityDie.subs) s.fn({ deadEntity: this, damageSource: src });
  }
  remove() {
    if (restricted) issue("remove in restricted mode");
    if (!this.isValid) return;
    this.isValid = false;
    allEntities.delete(this);
    for (const s of world.afterEvents.entityRemove.subs) s.fn({ removedEntityId: this.id, typeId: this.typeId });
  }
}

class Container {
  constructor(size = 36) {
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i] ? { ...this.slots[i] } : undefined;
  }
  setItem(i, it) {
    this.slots[i] = it ? { ...it } : undefined;
  }
}

class Player extends Entity {
  constructor(name, loc, dim, gm = "Survival") {
    super("minecraft:player", loc, dim);
    this.name = name;
    this.gm = gm;
    this.families = ["player"];
    this.container = new Container();
    this.selectedSlotIndex = 0;
    const self = this;
    this.onScreenDisplay = {
      setTitle(t, o) {
        __log.titles.push({ tick: tickNo, target: self, t, o });
      },
      setActionBar(t) {
        __log.actionbars.push({ tick: tickNo, target: self, t });
      },
    };
  }
  getGameMode() {
    return this.gm;
  }
}

// ------------------------------------------------------------------------------------------ dimension
class Dimension {
  constructor(id) {
    this.id = id;
  }
  getEntities(q = {}) {
    if (q.type && !DEFS.has(q.type) && q.type !== "minecraft:player") issue(`getEntities type ${q.type}`);
    return [...allEntities].filter((e) => {
      if (!e.isValid || e.dimension !== this) return false;
      if (q.type && e.typeId !== q.type) return false;
      if (q.excludeTypes?.includes(e.typeId)) return false;
      if (q.excludeFamilies && q.excludeFamilies.some((f) => e.families.includes(f))) return false;
      if (q.families && !q.families.every((f) => e.families.includes(f))) return false;
      if (q.location && q.maxDistance !== undefined) {
        const dx = e.location.x - q.location.x;
        const dy = e.location.y - q.location.y;
        const dz = e.location.z - q.location.z;
        if (Math.sqrt(dx * dx + dy * dy + dz * dz) > q.maxDistance) return false;
      }
      return true;
    });
  }
  getPlayers(q = {}) {
    return this.getEntities({ ...q, type: "minecraft:player" });
  }
  spawnEntity(typeId, loc) {
    if (restricted) issue("spawnEntity in restricted mode");
    const def = DEFS.get(typeId);
    if (!def) return issue(`spawnEntity of unknown type ${typeId}`);
    if (!def.description.is_summonable) issue(`spawnEntity of non-summonable ${typeId}`);
    const e = new Entity(typeId, loc, this);
    __log.spawned.push({ tick: tickNo, entity: e, typeId, at: { ...loc } });
    if (def.events["minecraft:entity_spawned"]) e.triggerEvent("minecraft:entity_spawned");
    for (const s of world.afterEvents.entitySpawn.subs) s.fn({ entity: e, cause: "Spawned" });
    return e;
  }
  getBlock(p) {
    return { location: { x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) }, isAir: !solidAt(p.x, p.y, p.z) };
  }
  spawnParticle(id, at, vars) {
    if (restricted) issue("spawnParticle in restricted mode");
    const text = PARTICLES.get(id);
    if (!text) return issue(`unknown particle ${id}`);
    if (![at.x, at.y, at.z].every(Number.isFinite)) issue(`particle ${id} at a non-finite position`);
    if (vars) {
      for (const k of Object.keys(vars.vars)) {
        const base = k.replace(/^variable\./, "");
        if (!text.includes(`variable.${base}`) && !text.includes(`v.${base}`)) issue(`particle ${id} never reads ${k}`);
      }
    }
    __log.particles.push({ tick: tickNo, id, at: { ...at }, vars: vars ? { ...vars.vars } : undefined });
  }
  playSound(id, at, opts) {
    __log.sounds.push({ tick: tickNo, id, at: { ...at }, opts });
  }
  getBlockFromRay(origin, dir, opts = {}) {
    const max = opts.maxDistance ?? 64;
    const l = Math.hypot(dir.x, dir.y, dir.z) || 1;
    const d = { x: dir.x / l, y: dir.y / l, z: dir.z / l };
    for (let t = 0; t <= max; t += 0.05) {
      const x = origin.x + d.x * t;
      const y = origin.y + d.y * t;
      const z = origin.z + d.z * t;
      if (solidAt(x, y, z)) {
        const bl = { x: Math.floor(x), y: Math.floor(y), z: Math.floor(z) };
        return { block: { location: bl, typeId: "minecraft:stone" }, face: "Up", faceLocation: { x: x - bl.x, y: y - bl.y, z: z - bl.z } };
      }
    }
    return undefined;
  }
}

const dims = { overworld: new Dimension("minecraft:overworld"), nether: new Dimension("minecraft:nether"), the_end: new Dimension("minecraft:the_end") };
export const __dims = dims;

export const world = {
  getDimension(id) {
    return dims[id.replace("minecraft:", "")];
  },
  getAllPlayers() {
    return [...allEntities].filter((e) => e.typeId === "minecraft:player");
  },
  afterEvents: {
    entitySpawn: signal(), entityLoad: signal(), entityRemove: signal(), entityDie: signal(), entityHurt: signal(),
    itemUse: signal(),
  },
  beforeEvents: { entityHurt: signal() },
};

// ------------------------------------------------------------------------------------------ test helpers
export function __spawnBoss(loc, yaw = 0, { load = false } = {}) {
  const e = new Entity("esb:da_vinci", loc, dims.overworld);
  e.rotation = { x: 0, y: yaw };
  if (load) {
    e.groups = new Set(["esb:ground", "esb:free"]);
    for (const s of world.afterEvents.entityLoad.subs) s.fn({ entity: e });
  } else {
    e.triggerEvent("minecraft:entity_spawned");
    for (const s of world.afterEvents.entitySpawn.subs) s.fn({ entity: e, cause: "Spawned" });
  }
  return e;
}
export function __spawnPlayer(name, loc, gm = "Survival") {
  return new Player(name, loc, dims.overworld, gm);
}
export function __useItem(player, typeId) {
  for (const s of world.afterEvents.itemUse.subs) s.fn({ source: player, itemStack: { typeId, amount: 1 } });
}
export function __entities(typeId) {
  return [...allEntities].filter((e) => e.isValid && e.typeId === typeId);
}

function physics(e) {
  if (e.typeId === "minecraft:player" || e.dead) return;
  if (e.projectile) return; // projectiles are not simulated
  const air = e.groups.has("esb:air");
  const ground = e.groups.has("esb:ground");
  const top = topAt(e.location.x, e.location.z, e.location.y + 0.5);
  if (!air && ground) e.velocity.y -= 0.08;
  e.location = { x: e.location.x + e.velocity.x, y: e.location.y + e.velocity.y, z: e.location.z + e.velocity.z };
  if (e.location.y < top && !air) {
    e.location.y = top;
    if (e.velocity.y < 0) e.velocity.y = 0;
  }
  e.velocity = { x: e.velocity.x * 0.6, y: air ? 0 : e.velocity.y * 0.98, z: e.velocity.z * 0.6 };
}

export function __tick(n = 1) {
  for (let i = 0; i < n; i++) {
    tickNo++;
    const q = queue;
    queue = [];
    for (const fn of q) fn();
    for (const t of timeouts.filter((t) => t.at === tickNo)) t.fn();
    for (const it of intervals) if (tickNo % it.every === 0) it.fn();
    for (const e of [...allEntities]) {
      physics(e);
      if (e.dead && tickNo - e.deathTick >= 20 && e.isValid) e.remove();
    }
  }
}
export const __now = () => tickNo;
