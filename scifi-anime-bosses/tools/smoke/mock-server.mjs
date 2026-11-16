// Strict emulation of the @minecraft/server 2.11.0 surface used by the VESPER-0 scripts.
// Pack data (entities, properties, events, particles + their molang variables, sounds, fogs,
// items) is loaded from the built packs; anything unknown or out of range is reported.
import fs from "node:fs";
import path from "node:path";

const BUILD = process.env.SAB_BUILD;
const BP = path.join(BUILD, "SAB_VESPER_BP");
const RP = path.join(BUILD, "SAB_VESPER_RP");

export const __issues = [];
export const __log = { particles: {}, sounds: {}, warnings: [], titles: [], damage: [], spawned: {}, items: [], xp: 0,
  camera: [], music: [], fog: [], effects: {} };
function issue(msg) {
  if (__issues.length < 500) __issues.push(msg);
}

function readJsonTree(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) out.push(...readJsonTree(p));
    else if (f.name.endsWith(".json")) out.push(JSON.parse(fs.readFileSync(p, "utf8")));
  }
  return out;
}

// ------------------------------------------------------------------ pack data
const ENTITY_DEFS = {};
for (const d of readJsonTree(path.join(BP, "entities"))) {
  const e = d["minecraft:entity"];
  ENTITY_DEFS[e.description.identifier] = {
    props: e.description.properties ?? {},
    events: e.events ?? {},
    health: e.components["minecraft:health"]?.max ?? 20,
    families: e.components["minecraft:type_family"]?.family ?? [],
    box: e.components["minecraft:collision_box"] ?? { width: 0.6, height: 1.8 },
    groups: e.component_groups ?? {},
  };
}
const PARTICLES = {};
for (const d of readJsonTree(path.join(RP, "particles"))) {
  const p = d.particle_effect;
  const vars = new Set([...JSON.stringify(p.components).matchAll(/variable\.([a-z_0-9]+)/g)].map((m) => m[1]));
  PARTICLES[p.description.identifier] = vars;
}
const SOUNDS = JSON.parse(fs.readFileSync(path.join(RP, "sounds", "sound_definitions.json"), "utf8")).sound_definitions;
const VANILLA_SOUNDS = new Set(["note.bass", "random.break"]);
const FOG_IDS = new Set(readJsonTree(path.join(RP, "fogs")).map((f) => f["minecraft:fog_settings"].description.identifier));
const ITEM_IDS = new Set(readJsonTree(path.join(BP, "items")).map((i) => i["minecraft:item"].description.identifier));
const ITEM_DEFS = Object.fromEntries(readJsonTree(path.join(BP, "items")).map((i) => [i["minecraft:item"].description.identifier, i["minecraft:item"].components]));
const VANILLA_EFFECTS = new Set(["resistance", "regeneration", "darkness", "slowness", "speed", "levitation", "slow_falling",
  "weakness", "strength", "absorption", "fire_resistance", "night_vision", "blindness", "nausea", "poison", "wither"]);
const CAMERA_PRESETS = new Set(["minecraft:free", "minecraft:first_person", "minecraft:third_person",
  "minecraft:third_person_front", "minecraft:fixed_boom", "minecraft:follow_orbit", "minecraft:control_scheme_camera"]);

// ------------------------------------------------------------------ enums
const enumOf = (names) => Object.freeze(Object.fromEntries(names.map((n) => [n, n])));
export const EntityDamageCause = enumOf(["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning",
  "entityAttack", "entityExplosion", "fall", "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing",
  "lava", "lightning", "maceSmash", "magic", "magma", "none", "override", "piston", "projectile", "ramAttack",
  "selfDestruct", "sonicBoom", "soulCampfire", "stalactite", "stalagmite", "starve", "suffocation", "temperature",
  "thorns", "void", "wither"]);
export const GameMode = Object.freeze({ Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" });
export const Difficulty = Object.freeze({ Peaceful: "Peaceful", Easy: "Easy", Normal: "Normal", Hard: "Hard" });
export const EquipmentSlot = Object.freeze({ Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" });
export const HudVisibility = Object.freeze({ Hide: 0, Reset: 1 });
export const EasingType = enumOf(["Linear", "InOutSine", "InSine", "OutSine", "InOutCubic", "OutCubic", "InCubic", "Spring"]);
export const CameraShakeType = Object.freeze({ Positional: "Positional", Rotational: "Rotational" });
export const CommandPermissionLevel = Object.freeze({ Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 });
export const CustomCommandParamType = enumOf(["BlockType", "Boolean", "EntitySelector", "EntityType", "Enum", "Float",
  "Integer", "ItemType", "Location", "PlayerSelector", "String"]);
export const CustomCommandStatus = Object.freeze({ Success: 0, Failure: 1 });
export const CustomCommandSource = enumOf(["Block", "Entity", "NPCDialogue", "Server"]);

// ------------------------------------------------------------------ helpers
let tickNo = 0;
let nextId = 1;
const v3 = (o) => ({ x: o.x, y: o.y, z: o.z });
function finite(o, what) {
  if (!o || !Number.isFinite(o.x) || !Number.isFinite(o.y) || !Number.isFinite(o.z)) {
    issue(`${what}: non-finite vector ${JSON.stringify(o)}`);
    return false;
  }
  return true;
}

class Signal {
  constructor(name) {
    this.name = name;
    this.handlers = [];
  }
  subscribe(fn, options) {
    if (typeof fn !== "function") issue(`${this.name}.subscribe without callback`);
    this.handlers.push({ fn, options });
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h.fn !== fn);
  }
  fire(ev, filterFn) {
    for (const h of this.handlers) {
      if (filterFn && !filterFn(h.options)) continue;
      try {
        h.fn(ev);
      } catch (e) {
        issue(`exception in ${this.name} handler: ${e && e.stack ? e.stack.split("\n").slice(0, 3).join(" | ") : e}`);
      }
    }
  }
}

// ------------------------------------------------------------------ terrain: flat ground at y=64 + obstacle boxes
export const terrain = { ground: 64, boxes: [] }; // boxes: {min:{x,y,z}, max:{x,y,z}}
function solidAt(x, y, z) {
  if (y < terrain.ground) return true;
  for (const b of terrain.boxes) {
    if (x >= b.min.x && x < b.max.x && y >= b.min.y && y < b.max.y && z >= b.min.z && z < b.max.z) return true;
  }
  return false;
}
function topAt(x, z) {
  let top = terrain.ground - 1;
  for (const b of terrain.boxes) {
    if (x >= b.min.x && x < b.max.x && z >= b.min.z && z < b.max.z) top = Math.max(top, b.max.y - 1);
  }
  return top;
}

// ------------------------------------------------------------------ components
class HealthComponent {
  constructor(entity, max) {
    this.entity = entity;
    this.effectiveMax = max;
    this.defaultValue = max;
    this._value = max;
  }
  get currentValue() {
    return this._value;
  }
  setCurrentValue(v) {
    if (!Number.isFinite(v)) issue(`setCurrentValue(${v})`);
    this._value = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
  resetToMaxValue() {
    this._value = this.effectiveMax;
  }
}

class Equippable {
  constructor(p) {
    this.p = p;
  }
  getEquipment(slot) {
    if (slot !== EquipmentSlot.Mainhand) return undefined;
    return this.p._hand;
  }
  setEquipment(slot, item) {
    if (slot === EquipmentSlot.Mainhand) this.p._hand = item;
    return true;
  }
}

// ------------------------------------------------------------------ entities
export class Entity {
  constructor(typeId, dim, loc) {
    this.id = String(nextId++);
    this.typeId = typeId;
    this._dim = dim;
    this._loc = v3(loc);
    this._vel = { x: 0, y: 0, z: 0 };
    this._rot = { x: 0, y: 0 };
    this._valid = true;
    this._dyn = {};
    this._tags = new Set();
    const def = ENTITY_DEFS[typeId];
    this._def = def;
    this._props = {};
    if (def) for (const [k, p] of Object.entries(def.props)) this._props[k] = p.default;
    this._health = new HealthComponent(this, def ? def.health : 20);
    this._lastHurt = -100;
    this._lastDamage = 0;
    this._groups = new Set();
    this._effects = {};
    this.nameTag = "";
  }
  get isValid() {
    return this._valid;
  }
  _check(what) {
    if (!this._valid) issue(`${what} on invalid entity ${this.typeId}`);
    return this._valid;
  }
  get location() {
    this._check("location");
    return v3(this._loc);
  }
  get dimension() {
    return this._dim;
  }
  getRotation() {
    return { ...this._rot };
  }
  setRotation(r) {
    if (!Number.isFinite(r.x) || !Number.isFinite(r.y)) issue(`setRotation non-finite ${JSON.stringify(r)}`);
    this._rot = { x: r.x, y: r.y };
  }
  getHeadLocation() {
    return { x: this._loc.x, y: this._loc.y + (this.typeId === "minecraft:player" ? 1.62 : 1), z: this._loc.z };
  }
  getViewDirection() {
    const r = (this._rot.y * Math.PI) / 180;
    return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
  }
  getVelocity() {
    return { ...this._vel };
  }
  clearVelocity() {
    this._vel = { x: 0, y: 0, z: 0 };
  }
  applyImpulse(v) {
    if (!this._check("applyImpulse") || !finite(v, "applyImpulse")) return;
    if (this.typeId === "minecraft:player") throw new Error("applyImpulse is not supported on players");
    this._vel.x += v.x;
    this._vel.y += v.y;
    this._vel.z += v.z;
  }
  applyKnockback(h, vert) {
    if (!this._check("applyKnockback")) return;
    if (!Number.isFinite(h.x) || !Number.isFinite(h.z) || !Number.isFinite(vert)) issue("applyKnockback non-finite");
    this._vel.x = this._vel.x / 2 + h.x;
    this._vel.z = this._vel.z / 2 + h.z;
    this._vel.y = vert;
  }
  teleport(loc, opts) {
    if (!this._check("teleport") || !finite(loc, `teleport ${this.typeId}`)) return;
    this._loc = v3(loc);
    if (!opts || !opts.keepVelocity) this._vel = { x: 0, y: 0, z: 0 };
  }
  getProperty(id) {
    if (!this._def || !(id in this._def.props)) {
      issue(`getProperty unknown ${id} on ${this.typeId}`);
      return undefined;
    }
    return this._props[id];
  }
  setProperty(id, value) {
    if (!this._check(`setProperty ${id}`)) return;
    const p = this._def?.props?.[id];
    if (!p) {
      issue(`setProperty unknown property ${id} on ${this.typeId}`);
      return;
    }
    if (p.type === "bool" && typeof value !== "boolean") issue(`setProperty ${id}: expected bool, got ${value}`);
    if ((p.type === "int" || p.type === "float") && typeof value !== "number") issue(`setProperty ${id}: expected number, got ${value}`);
    if (p.type === "int" && !Number.isInteger(value)) issue(`setProperty ${id}: int property got ${value}`);
    if (p.range && (value < p.range[0] || value > p.range[1])) issue(`setProperty ${id}=${value} outside ${p.range}`);
    if (p.type === "enum" && !p.values.includes(value)) issue(`setProperty ${id}: bad enum ${value}`);
    this._props[id] = value;
    __log.props ??= {};
    (__log.props[id] ??= []).push([tickNo, value]);
  }
  resetProperty(id) {
    return this.getProperty(id);
  }
  triggerEvent(ev) {
    if (!this._check(`triggerEvent ${ev}`)) return;
    const e = this._def?.events?.[ev];
    if (!e) {
      issue(`triggerEvent unknown event ${ev} on ${this.typeId}`);
      return;
    }
    for (const g of e.add?.component_groups ?? []) this._groups.add(g);
    for (const g of e.remove?.component_groups ?? []) this._groups.delete(g);
  }
  getComponent(id) {
    if (id === "minecraft:health" || id === "health") return this._health;
    if ((id === "minecraft:equippable" || id === "equippable") && this.typeId === "minecraft:player") return this._equip;
    if (id === "minecraft:tameable") return undefined;
    issue(`getComponent(${id}) not emulated on ${this.typeId}`);
    return undefined;
  }
  getDynamicProperty(k) {
    return this._dyn[k];
  }
  setDynamicProperty(k, v) {
    if (typeof k !== "string" || !k.includes(":")) issue(`dynamic property key without namespace: ${k}`);
    this._dyn[k] = v;
  }
  addTag(t) {
    this._tags.add(t);
    return true;
  }
  hasTag(t) {
    return this._tags.has(t);
  }
  getAABB() {
    const b = this._box();
    return { center: { x: this._loc.x, y: this._loc.y + b.height / 2, z: this._loc.z },
      extent: { x: b.width / 2, y: b.height / 2, z: b.width / 2 } };
  }
  _box() {
    let box = this._def?.box ?? { width: 0.6, height: 1.8 };
    for (const g of this._groups) {
      const cb = this._def?.groups?.[g]?.["minecraft:collision_box"];
      if (cb) box = cb;
    }
    return box;
  }
  addEffect(effect, duration, opts) {
    const id = typeof effect === "string" ? effect.replace("minecraft:", "") : effect.id;
    if (!VANILLA_EFFECTS.has(id)) issue(`addEffect unknown effect ${effect}`);
    if (!Number.isInteger(duration) || duration <= 0) issue(`addEffect bad duration ${duration}`);
    this._effects[id] = { until: tickNo + duration, amplifier: opts?.amplifier ?? 0 };
    __log.effects[id] = (__log.effects[id] ?? 0) + 1;
    return {};
  }
  setOnFire(seconds) {
    if (!(seconds > 0)) issue(`setOnFire(${seconds})`);
    this._fire = tickNo + seconds * 20;
    return true;
  }
  extinguishFire() {
    this._fire = 0;
    return true;
  }
  applyDamage(amount, opts) {
    if (!this._check("applyDamage")) return false;
    if (!Number.isFinite(amount) || amount < 0) issue(`applyDamage(${amount})`);
    const cause = opts?.cause ?? "none";
    if (!(cause in EntityDamageCause)) issue(`applyDamage unknown cause ${cause}`);
    if (opts?.damagingEntity && !opts.damagingEntity.isValid) issue("applyDamage with invalid damagingEntity");
    return hurtPipeline(this, amount, cause, opts?.damagingEntity);
  }
  kill() {
    return hurtPipeline(this, 1e9, "override", undefined);
  }
  remove() {
    if (!this._valid) {
      issue(`remove() on invalid ${this.typeId}`);
      return;
    }
    this._valid = false;
    this._dim._entities.delete(this.id);
    world.afterEvents.entityRemove.fire({ removedEntityId: this.id, typeId: this.typeId });
  }
  matches() {
    return true;
  }
  runCommand(c) {
    issue(`runCommand not expected: ${c}`);
  }
  _step() {
    if (this.typeId === "minecraft:player") {
      this._loc.x += this._vel.x;
      this._loc.z += this._vel.z;
      this._loc.y += this._vel.y;
      this._vel.x *= 0.6;
      this._vel.z *= 0.6;
      if (this._loc.y > topAt(this._loc.x, this._loc.z) + 1) this._vel.y -= 0.08;
      else {
        this._loc.y = topAt(this._loc.x, this._loc.z) + 1;
        this._vel.y = 0;
      }
      return;
    }
    // our helpers: no gravity / no collision, air drag like the engine
    this._loc.x += this._vel.x;
    this._loc.y += this._vel.y;
    this._loc.z += this._vel.z;
    this._vel.x *= 0.91;
    this._vel.y *= 0.91;
    this._vel.z *= 0.91;
  }
}

function hurtPipeline(entity, amount, cause, source) {
  const ev = { hurtEntity: entity, damage: amount, cancel: false, damageSource: { cause, damagingEntity: source } };
  world.beforeEvents.entityHurt.fire(ev, (opts) => {
    const fam = opts?.entityFilter?.families;
    if (!fam) return true;
    const mine = entity._def?.families ?? (entity.typeId === "minecraft:player" ? ["player"] : []);
    return fam.every((f) => mine.includes(f));
  });
  if (ev.cancel) return false;
  let dmg = ev.damage;
  if (!Number.isFinite(dmg) || dmg < 0) {
    issue(`entityHurt handler produced damage ${dmg}`);
    return false;
  }
  if (cause !== "override" && tickNo - entity._lastHurt < 10) {
    if (dmg <= entity._lastDamage) return false;
    const extra = dmg - entity._lastDamage;
    entity._lastDamage = dmg;
    dmg = extra;
  } else {
    entity._lastHurt = tickNo;
    entity._lastDamage = dmg;
  }
  if (entity.typeId === "minecraft:player") {
    entity._taken = (entity._taken ?? 0) + dmg;
    __log.damage.push([tickNo, entity.name, dmg, cause, source?.typeId ?? "-"]);
    return true; // players are invulnerable in the simulation (damage is only recorded)
  }
  entity._health._value -= dmg;
  if (entity._health._value <= 0) {
    entity._health._value = 0;
    entity.remove();
  }
  return true;
}

class Camera {
  constructor(p) {
    this.p = p;
    this.isValid = true;
  }
  setCamera(preset, opts) {
    if (!CAMERA_PRESETS.has(preset)) issue(`setCamera unknown preset ${preset}`);
    if (opts?.location) finite(opts.location, "camera location");
    if (opts?.facingLocation) finite(opts.facingLocation, "camera facing");
    if (opts?.easeOptions && !(opts.easeOptions.easeType in EasingType)) issue(`bad easeType ${opts.easeOptions.easeType}`);
    __log.camera.push([tickNo, this.p.name, preset]);
  }
  clear() {
    __log.camera.push([tickNo, this.p.name, "clear"]);
  }
  fade(opts) {
    const c = opts?.fadeColor;
    if (c && [c.red, c.green, c.blue].some((x) => !(x >= 0 && x <= 1))) issue("fade colour out of range");
    __log.camera.push([tickNo, this.p.name, "fade"]);
  }
  addShake(o) {
    if (!(o.intensity > 0 && o.intensity <= 4) || !(o.duration > 0)) issue(`addShake bad ${JSON.stringify(o)}`);
    if (!(o.type in CameraShakeType)) issue(`addShake bad type ${o.type}`);
  }
}

class FogSettings {
  constructor(p) {
    this.p = p;
    this.stack = [];
  }
  push(id, tag) {
    if (!FOG_IDS.has(id)) issue(`fog push unknown ${id}`);
    if (this.stack.length >= 16) issue("fog stack overflow");
    this.stack.push([id, tag]);
    __log.fog.push([tickNo, this.p.name, id]);
    return this.stack.length - 1;
  }
  remove(tag) {
    const n = this.stack.length;
    this.stack = this.stack.filter((s) => s[1] !== tag);
    return n !== this.stack.length;
  }
  pop() {
    return this.stack.pop()?.[0];
  }
  getStack() {
    return this.stack.map((s) => s[0]);
  }
}

class ScreenDisplay {
  constructor(p) {
    this.p = p;
    this.isValid = true;
  }
  setTitle(t, o) {
    if (o && (!Number.isInteger(o.fadeInDuration) || !Number.isInteger(o.stayDuration) || !Number.isInteger(o.fadeOutDuration))) {
      issue("setTitle durations must be integer ticks");
    }
    __log.titles.push([tickNo, t]);
  }
  setActionBar() {}
  updateSubtitle() {}
  setHudVisibility(v) {
    if (v !== 0 && v !== 1) issue(`setHudVisibility ${v}`);
  }
}

export class Player extends Entity {
  constructor(name, dim, loc) {
    super("minecraft:player", dim, loc);
    this.name = name;
    this._mode = GameMode.Survival;
    this._equip = new Equippable(this);
    this.camera = new Camera(this);
    this.onScreenDisplay = new ScreenDisplay(this);
    this.fogSettings = new FogSettings(this);
    this._cooldowns = {};
    this._music = undefined;
    this._health = new HealthComponent(this, 20);
  }
  getGameMode() {
    return this._mode;
  }
  sendMessage() {}
  playSound(id) {
    if (!(id in SOUNDS) && !VANILLA_SOUNDS.has(id)) issue(`player.playSound unknown ${id}`);
    __log.sounds[id] = (__log.sounds[id] ?? 0) + 1;
    return {};
  }
  playMusic(id, opts) {
    if (!(id in SOUNDS) || SOUNDS[id].category !== "music") issue(`playMusic unknown/non-music ${id}`);
    this._music = id;
    __log.music.push([tickNo, this.name, id]);
  }
  queueMusic(id) {
    this.playMusic(id);
  }
  stopMusic() {
    this._music = undefined;
  }
  getItemCooldown(cat) {
    return Math.max(0, (this._cooldowns[cat] ?? 0) - tickNo);
  }
  startItemCooldown(cat, ticks) {
    const known = Object.values(ITEM_DEFS).some((c) => c["minecraft:cooldown"]?.category === cat);
    if (!known) issue(`startItemCooldown unknown category ${cat}`);
    this._cooldowns[cat] = tickNo + ticks;
  }
}

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!ITEM_IDS.has(typeId) && !typeId.startsWith("minecraft:")) issue(`ItemStack unknown item ${typeId}`);
    if (!Number.isInteger(amount) || amount < 1 || amount > 255) issue(`ItemStack bad amount ${amount}`);
    this.typeId = typeId;
    this.amount = amount;
    this._dur = { damage: 0, maxDurability: ITEM_DEFS[typeId]?.["minecraft:durability"]?.max_durability ?? 0 };
  }
  getComponent(id) {
    if (id === "minecraft:durability" && this._dur.maxDurability) return this._dur;
    return undefined;
  }
}

export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(name, value) {
    if (!name.startsWith("variable.")) issue(`molang variable without prefix: ${name}`);
    if (!Number.isFinite(value)) issue(`molang ${name} non-finite`);
    this.vars[name] = value;
  }
  setColorRGB(name, c) {
    this.vars[name] = c;
  }
  setColorRGBA(name, c) {
    this.vars[name] = c;
  }
  setVector3(name, v) {
    this.vars[name] = v;
  }
  setSpeedAndDirection(name, s, d) {
    this.vars[name] = [s, d];
  }
}

// ------------------------------------------------------------------ dimension
class Dimension {
  constructor(id) {
    this.id = id;
    this.heightRange = { min: -64, max: 320 };
    this._entities = new Map();
  }
  _all() {
    return [...this._entities.values()].filter((e) => e.isValid);
  }
  getEntities(opts = {}) {
    let list = this._all();
    if (opts.type) list = list.filter((e) => e.typeId === opts.type);
    if (opts.excludeTypes) list = list.filter((e) => !opts.excludeTypes.includes(e.typeId));
    if (opts.families) list = list.filter((e) => opts.families.every((f) => (e._def?.families ?? []).includes(f)));
    if (opts.excludeFamilies) list = list.filter((e) => !opts.excludeFamilies.some((f) => (e._def?.families ?? []).includes(f)));
    if (opts.location && opts.maxDistance !== undefined) {
      list = list.filter((e) => Math.hypot(e._loc.x - opts.location.x, e._loc.y - opts.location.y, e._loc.z - opts.location.z) <= opts.maxDistance);
    }
    return list;
  }
  getPlayers(opts = {}) {
    return this.getEntities({ ...opts, type: "minecraft:player" });
  }
  spawnEntity(id, loc, opts) {
    if (!(id in ENTITY_DEFS) && !id.startsWith("minecraft:")) {
      issue(`spawnEntity unknown ${id}`);
      throw new Error("unknown entity");
    }
    finite(loc, `spawnEntity ${id}`);
    const e = new Entity(id, this, loc);
    if (opts?.spawnEvent) e.triggerEvent(opts.spawnEvent);
    if (opts?.initialRotation !== undefined) e._rot.y = opts.initialRotation;
    this._entities.set(e.id, e);
    __log.spawned[id] = (__log.spawned[id] ?? 0) + 1;
    pendingSpawnEvents.push(e);
    return e;
  }
  spawnParticle(id, loc, molang) {
    const vars = PARTICLES[id];
    if (!vars) issue(`spawnParticle unknown ${id}`);
    finite(loc, `spawnParticle ${id}`);
    if (molang && vars) {
      for (const k of Object.keys(molang.vars)) {
        const short = k.replace("variable.", "");
        if (!vars.has(short)) issue(`particle ${id}: molang variable ${k} is not read by the effect`);
      }
    }
    __log.particles[id] = (__log.particles[id] ?? 0) + 1;
  }
  playSound(id, loc, opts) {
    if (!(id in SOUNDS) && !VANILLA_SOUNDS.has(id)) issue(`playSound unknown ${id}`);
    finite(loc, `playSound ${id}`);
    __log.sounds[id] = (__log.sounds[id] ?? 0) + 1;
    return {};
  }
  getBlockFromRay(loc, dir, opts = {}) {
    finite(loc, "ray origin");
    finite(dir, "ray dir");
    const max = opts.maxDistance ?? 64;
    for (let d = 0; d <= max; d += 0.25) {
      const x = loc.x + dir.x * d;
      const y = loc.y + dir.y * d;
      const z = loc.z + dir.z * d;
      if (solidAt(x, y, z)) {
        const bl = { x: Math.floor(x), y: Math.floor(y), z: Math.floor(z) };
        return { block: { location: bl, typeId: "minecraft:stone", isValid: true }, face: "Up",
          faceLocation: { x: x - bl.x, y: Math.min(1, y - bl.y + 0.01), z: z - bl.z } };
      }
    }
    return undefined;
  }
  getTopmostBlock(xz) {
    const y = topAt(xz.x, xz.z);
    return { location: { x: Math.floor(xz.x), y, z: Math.floor(xz.z) }, typeId: "minecraft:grass_block" };
  }
  getBlock(loc) {
    return { location: { x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) },
      isAir: !solidAt(loc.x, loc.y, loc.z), typeId: solidAt(loc.x, loc.y, loc.z) ? "minecraft:stone" : "minecraft:air" };
  }
  spawnItem(stack, loc) {
    if (!(stack instanceof ItemStack)) issue("spawnItem without ItemStack");
    finite(loc, "spawnItem");
    __log.items.push([tickNo, stack.typeId, stack.amount]);
    const e = new Entity("minecraft:item", this, loc);
    this._entities.set(e.id, e);
    return e;
  }
  spawnXp(loc, amount) {
    finite(loc, "spawnXp");
    if (!Number.isInteger(amount) || amount <= 0) issue(`spawnXp(${amount})`);
    __log.xp += amount;
  }
  runCommand(c) {
    issue(`dimension.runCommand not expected: ${c}`);
  }
}

const DIMS = Object.fromEntries(["minecraft:overworld", "minecraft:nether", "minecraft:the_end"].map((d) => [d, new Dimension(d)]));
const pendingSpawnEvents = [];

// ------------------------------------------------------------------ world & system
export const world = {
  afterEvents: {
    entitySpawn: new Signal("entitySpawn"), entityLoad: new Signal("entityLoad"), entityRemove: new Signal("entityRemove"),
    entityDie: new Signal("entityDie"), entityHurt: new Signal("entityHurt"),
  },
  beforeEvents: { entityHurt: new Signal("beforeEntityHurt") },
  _dyn: {},
  _difficulty: Difficulty.Normal,
  getDimension(id) {
    const d = DIMS[id];
    if (!d) throw new Error(`no dimension ${id}`);
    return d;
  },
  getEntity(id) {
    for (const d of Object.values(DIMS)) {
      const e = d._entities.get(id);
      if (e && e.isValid) return e;
    }
    return undefined;
  },
  getAllPlayers() {
    return Object.values(DIMS).flatMap((d) => d.getPlayers());
  },
  getPlayers(o) {
    return this.getAllPlayers();
  },
  getDynamicProperty(k) {
    return this._dyn[k];
  },
  setDynamicProperty(k, v) {
    this._dyn[k] = v;
  },
  getDifficulty() {
    return this._difficulty;
  },
  sendMessage() {},
};

const timers = new Map();
let timerId = 1;
const startup = new Signal("startup");
export const system = {
  get currentTick() {
    return tickNo;
  },
  beforeEvents: { startup, shutdown: new Signal("shutdown") },
  afterEvents: { scriptEventReceive: new Signal("scriptEventReceive") },
  run(fn) {
    const id = timerId++;
    timers.set(id, { fn, due: tickNo, interval: 0 });
    return id;
  },
  runTimeout(fn, d = 1) {
    const id = timerId++;
    timers.set(id, { fn, due: tickNo + d, interval: 0 });
    return id;
  },
  runInterval(fn, i = 1) {
    const id = timerId++;
    timers.set(id, { fn, due: tickNo + i, interval: i });
    return id;
  },
  clearRun(id) {
    timers.delete(id);
  },
};

// ------------------------------------------------------------------ test driver API
export const __registries = { components: {}, commands: {}, enums: {} };

export function __startup() {
  const itemComponentRegistry = {
    registerCustomComponent(name, handlers) {
      const declared = Object.values(ITEM_DEFS).some((c) => name in c);
      if (!declared) issue(`custom component ${name} not used by any item`);
      __registries.components[name] = handlers;
    },
  };
  const customCommandRegistry = {
    registerEnum(name, values) {
      if (!name.includes(":")) issue(`enum ${name} needs a namespace`);
      __registries.enums[name] = values;
    },
    registerCommand(def, cb) {
      if (!def.name.includes(":")) issue(`command ${def.name} needs a namespace`);
      for (const p of [...(def.mandatoryParameters ?? []), ...(def.optionalParameters ?? [])]) {
        if (p.type === "Enum" && !(p.name in __registries.enums)) issue(`command ${def.name}: enum ${p.name} not registered`);
      }
      __registries.commands[def.name] = { def, cb };
    },
  };
  startup.fire({ itemComponentRegistry, customCommandRegistry, blockComponentRegistry: {} });
}

export function __tick() {
  tickNo++;
  for (const d of Object.values(DIMS)) for (const e of d._all()) e._step();
  const spawned = pendingSpawnEvents.splice(0);
  for (const e of spawned) if (e.isValid) world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" });
  for (const [id, t] of [...timers.entries()]) {
    if (!timers.has(id) || t.due > tickNo) continue;
    if (t.interval) t.due = tickNo + t.interval;
    else timers.delete(id);
    try {
      t.fn();
    } catch (e) {
      issue(`uncaught error in scheduled callback: ${e && e.stack ? e.stack.split("\n").slice(0, 4).join(" | ") : e}`);
    }
  }
}

export function __addPlayer(name, loc, dim = "minecraft:overworld") {
  const d = DIMS[dim];
  const p = new Player(name, d, loc);
  d._entities.set(p.id, p);
  return p;
}

export function __addEntity(typeId, loc, dim = "minecraft:overworld") {
  const d = DIMS[dim];
  const e = new Entity(typeId, d, loc);
  d._entities.set(e.id, e);
  return e;
}

export function __hit(target, attacker, amount, cause = "entityAttack") {
  return hurtPipeline(target, amount, cause, attacker);
}

export function __entities(dim = "minecraft:overworld") {
  return DIMS[dim]._all();
}

export const __now = () => tickNo;
export const __dims = DIMS;

// console capture
const realWarn = console.warn;
console.warn = (...a) => {
  __log.warnings.push(a.join(" "));
  if (process.env.SAB_VERBOSE) realWarn(...a);
};
