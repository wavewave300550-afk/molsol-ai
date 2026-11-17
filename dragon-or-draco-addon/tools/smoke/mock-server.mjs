// Strict, minimal emulation of the @minecraft/server 2.11.0 surface used by the Red Dragon scripts.
// Everything the script hands to the engine is checked against the real pack files:
//   particle ids (+ the molang variables they read), sound events, entity property names/values
//   (enum values, int ranges), entity events and the component groups they switch.
// World: flat ground (solid below y = 64) plus test-defined solid boxes; simple physics
// (gravity only while the dod:ground group is active; velocity applied every tick).
import fs from "node:fs";
import path from "node:path";

const ADDON = process.env.DOD_ADDON;
const RP = path.join(ADDON, "resource_packs", "dragon_or_draco");
const BP = path.join(ADDON, "behavior_packs", "dragon_or_draco");
const readJson = (f) => JSON.parse(fs.readFileSync(f, "utf8"));

const PARTICLES = new Map();
for (const f of fs.readdirSync(path.join(RP, "particles"))) {
  const text = fs.readFileSync(path.join(RP, "particles", f), "utf8");
  PARTICLES.set(JSON.parse(text).particle_effect.description.identifier, text);
}
const SOUNDS = new Set(Object.keys(readJson(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions));
const DRAGON_DEF = readJson(path.join(BP, "entities", "red_dragon.json"))["minecraft:entity"];

export const __issues = [];
export const __log = { particles: [], sounds: [], damage: [], knockback: [], fire: [], events: [], props: [], died: [] };
const issue = (m) => {
  if (!__issues.includes(m)) __issues.push(m);
};

// ------------------------------------------------------------------------------------------ enums
export const EntityDamageCause = new Proxy({}, { get: (_, k) => String(k) });
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };

export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setSpeedAndDirection(name, speed, dir) {
    this.vars[`${name}.speed`] = speed;
    this.vars[`${name}.direction_x`] = dir.x;
    this.vars[`${name}.direction_y`] = dir.y;
    this.vars[`${name}.direction_z`] = dir.z;
  }
  setFloat(name, v) {
    this.vars[name] = v;
  }
  setVector3(name, v) {
    this.vars[`${name}.x`] = v.x;
    this.vars[`${name}.y`] = v.y;
    this.vars[`${name}.z`] = v.z;
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
function topAt(x, z) {
  let top = GROUND;
  for (const b of __solids) if (x >= b.min.x && x < b.max.x && z >= b.min.z && z < b.max.z) top = Math.max(top, b.max.y);
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
    this.onFire = 0;
    this.dead = false;
    allEntities.add(this);
  }
  get isOnGround() {
    return this.location.y <= topAt(this.location.x, this.location.z) + 0.01;
  }
  get isInWater() {
    return false;
  }
  getComponent(id) {
    if (id === "minecraft:health" || id === "health") return this.dead ? undefined : this.health;
    issue(`getComponent(${id}) not emulated`);
    return undefined;
  }
  getRotation() {
    return { ...this.rotation };
  }
  setRotation(r) {
    this.rotation = { x: r.x, y: r.y };
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
  setOnFire(seconds) {
    this.onFire = seconds;
    __log.fire.push({ tick: tickNo, target: this, seconds });
    return true;
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
    if (this.typeId !== "dod:red_dragon") return issue(`setProperty on ${this.typeId}`);
    const def = DRAGON_DEF.description.properties[k];
    if (!def) return issue(`unknown property ${k}`);
    if (def.type === "enum" && !def.values.includes(v)) return issue(`property ${k}: '${v}' not in enum`);
    if (def.type === "int" && (!Number.isInteger(v) || v < def.range[0] || v > def.range[1])) return issue(`property ${k}: ${v} outside ${def.range}`);
    if (def.type === "bool" && typeof v !== "boolean") return issue(`property ${k}: ${v} not bool`);
    if (this.props[k] !== v) __log.props.push({ tick: tickNo, entity: this, key: k, value: v });
    this.props[k] = v;
  }
  triggerEvent(name) {
    if (this.typeId !== "dod:red_dragon") return;
    const ev = DRAGON_DEF.events[name];
    if (!ev) return issue(`unknown entity event ${name}`);
    __log.events.push({ tick: tickNo, entity: this, name });
    const apply = (spec) => {
      for (const g of spec.remove?.component_groups ?? []) this.groups.delete(g);
      for (const g of spec.add?.component_groups ?? []) {
        if (!DRAGON_DEF.component_groups[g]) issue(`unknown component group ${g}`);
        this.groups.add(g);
      }
    };
    if (ev.randomize) apply(ev.randomize[0]);
    else apply(ev);
  }
  applyDamage(amount, opts = {}) {
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
    __log.died.push({ tick: tickNo, entity: this });
    for (const s of world.afterEvents.entityDie.subs) s.fn({ deadEntity: this, damageSource: src });
  }
  remove() {
    this.isValid = false;
    allEntities.delete(this);
    for (const s of world.afterEvents.entityRemove.subs) s.fn({ removedEntityId: this.id, typeId: this.typeId });
  }
}

class Player extends Entity {
  constructor(name, loc, dim, gm = "Survival") {
    super("minecraft:player", loc, dim);
    this.name = name;
    this.gm = gm;
    this.families = ["player"];
  }
  getGameMode() {
    return this.gm;
  }
}

let restricted = false;

// ------------------------------------------------------------------------------------------ dimension
class Dimension {
  constructor(id) {
    this.id = id;
  }
  getEntities(q = {}) {
    if (q.type && q.type !== "dod:red_dragon" && q.type !== "minecraft:player") issue(`getEntities type ${q.type}`);
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
  spawnParticle(id, at, vars) {
    if (restricted) issue("spawnParticle in restricted mode");
    const text = PARTICLES.get(id);
    if (!text) return issue(`unknown particle ${id}`);
    if (vars) {
      for (const k of Object.keys(vars.vars)) {
        const base = k.replace(/^variable\./, "");
        if (!text.includes(`variable.${base}`) && !text.includes(`v.${base}`)) issue(`particle ${id} never reads ${k}`);
      }
    }
    if (text.includes("variable.jet.direction") && !vars) issue(`particle ${id} spawned without variable.jet`);
    __log.particles.push({ tick: tickNo, id, at: { ...at }, vars: vars ? { ...vars.vars } : undefined });
  }
  playSound(id, at, opts) {
    if (!SOUNDS.has(id)) issue(`unknown sound ${id}`);
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
  getTopmostBlock(xz) {
    return { location: { x: Math.floor(xz.x), y: topAt(xz.x, xz.z) - 1, z: Math.floor(xz.z) } };
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
  afterEvents: { entitySpawn: signal(), entityLoad: signal(), entityRemove: signal(), entityDie: signal(), entityHurt: signal() },
  beforeEvents: { entityHurt: signal() },
};

// ------------------------------------------------------------------------------------------ test helpers
export function __spawnDragon(loc, yaw = 0, { natural = false, load = false } = {}) {
  const e = new Entity("dod:red_dragon", loc, dims.overworld);
  e.families = [...DRAGON_DEF.components["minecraft:type_family"].family];
  const hp = DRAGON_DEF.components["minecraft:health"].value;
  e.health = { currentValue: hp, effectiveMax: hp };
  e.rotation = { x: 0, y: yaw };
  for (const [k, def] of Object.entries(DRAGON_DEF.description.properties)) e.props[k] = def.default;
  if (load) {
    for (const s of world.afterEvents.entityLoad.subs) s.fn({ entity: e });
  } else {
    e.triggerEvent(natural ? "dod:natural_spawn" : "minecraft:entity_spawned");
    for (const s of world.afterEvents.entitySpawn.subs) s.fn({ entity: e, cause: "Spawned" });
  }
  return e;
}
export function __spawnPlayer(name, loc, gm = "Survival") {
  return new Player(name, loc, dims.overworld, gm);
}
export function __spawnMob(typeId, loc, families = ["mob"]) {
  const e = new Entity(typeId, loc, dims.overworld);
  e.families = families;
  return e;
}

function physics(e) {
  if (e.typeId === "minecraft:player" || e.dead) return;
  const air = e.groups.has("dod:air");
  const ground = e.groups.has("dod:ground");
  if (!air && ground) e.velocity.y -= 0.08;
  e.location = { x: e.location.x + e.velocity.x, y: e.location.y + e.velocity.y, z: e.location.z + e.velocity.z };
  const top = topAt(e.location.x, e.location.z);
  if (e.location.y < top) {
    e.location.y = top;
    if (e.velocity.y < 0) e.velocity.y = 0;
  }
  const f = air ? 0.91 : 0.6;
  e.velocity = { x: e.velocity.x * f, y: air ? e.velocity.y * 0.91 : e.velocity.y * 0.98, z: e.velocity.z * f };
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
