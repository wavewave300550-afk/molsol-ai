// Strict mock of the parts of @minecraft/server 2.11.0 used by the add-on.
// Identifiers (particles, sounds, effects, items, entities, animations, commands) are
// validated against the generated packs and the vanilla 1.26.60 reference index, and
// using a removed/dead entity throws like the real API.  This lets tests run the
// compiled scripts through real gameplay scenarios outside Minecraft.
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const BP = path.join(ROOT, "packs/PlayableRaces_BP");
const RP = path.join(ROOT, "packs/PlayableRaces_RP");
const REF = JSON.parse(fs.readFileSync(path.join(ROOT, "tools/vanilla/reference.json"), "utf8"));

function walk(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}
const readJson = (p) => JSON.parse(fs.readFileSync(p, "utf8"));

export const defs = { items: new Map(), entities: new Set(REF.entities), particles: new Set(REF.particles), sounds: new Set(REF.sounds), anims: new Set() };
for (const f of walk(path.join(BP, "items"))) {
  const d = readJson(f)["minecraft:item"];
  defs.items.set(d.description.identifier, d.components["minecraft:tags"]?.tags ?? []);
}
defs.entityInfo = new Map();
for (const f of walk(path.join(BP, "entities"))) {
  const d = readJson(f)["minecraft:entity"];
  defs.entities.add(d.description.identifier);
  defs.entityInfo.set(d.description.identifier, {
    families: d.components["minecraft:type_family"]?.family ?? ["mob"],
    health: d.components["minecraft:health"]?.value ?? 20,
    events: Object.keys(d.events ?? {}),
  });
}
for (const f of walk(path.join(RP, "particles"))) defs.particles.add(readJson(f).particle_effect.description.identifier);
for (const f of walk(path.join(RP, "animations"))) for (const k of Object.keys(readJson(f).animations)) defs.anims.add(k);
defs.fogs = new Set(walk(path.join(RP, "fogs")).map((f) => readJson(f)["minecraft:fog_settings"].description.identifier));
const EFFECTS = new Set(["speed", "slowness", "haste", "mining_fatigue", "strength", "instant_health", "instant_damage", "jump_boost", "nausea", "regeneration", "resistance", "fire_resistance", "water_breathing", "invisibility", "blindness", "night_vision", "hunger", "weakness", "poison", "wither", "health_boost", "absorption", "saturation", "levitation", "fatal_poison", "conduit_power", "slow_falling", "bad_omen", "village_hero", "darkness", "wind_charged", "weaving", "oozing", "infested", "trial_omen", "raid_omen"]);

// ------------------------------------------------------------------ enums
export const EquipmentSlot = { Chest: "Chest", Feet: "Feet", Head: "Head", Legs: "Legs", Mainhand: "Mainhand", Offhand: "Offhand" };
export const ItemLockMode = { inventory: "inventory", none: "none", slot: "slot" };
export const InputPermissionCategory = { Camera: 1, Movement: 2, LateralMovement: 4, Sneak: 5, Jump: 6, Mount: 7, Dismount: 8, MoveForward: 9, MoveBackward: 10, MoveLeft: 11, MoveRight: 12 };
export const InputButton = { Jump: "Jump", Sneak: "Sneak" };
export const ButtonState = { Pressed: "Pressed", Released: "Released" };
export const MoonPhase = { FullMoon: 0, WaningGibbous: 1, FirstQuarter: 2, WaningCrescent: 3, NewMoon: 4, WaxingCrescent: 5, LastQuarter: 6, WaxingGibbous: 7 };
for (const [k, v] of Object.entries({ ...MoonPhase })) MoonPhase[v] = k;
export const WeatherType = { Clear: "Clear", Rain: "Rain", Thunder: "Thunder" };
export const GameMode = { Survival: "Survival", Creative: "Creative", Adventure: "Adventure", Spectator: "Spectator" };
export const EntityDamageCause = Object.fromEntries(["anvil", "blockExplosion", "campfire", "charging", "contact", "drowning", "entityAttack", "entityExplosion", "fall", "fallingBlock", "fire", "fireTick", "fireworks", "flyIntoWall", "freezing", "lava", "lightning", "maceSmash", "magic", "magma", "none", "override", "piston", "projectile", "ramAttack", "selfDestruct", "sonicBoom", "soulCampfire", "stalactite", "stalagmite", "starve", "suffocation"].map((k) => [k, k]));
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const PlayerPermissionLevel = { Visitor: 0, Member: 1, Operator: 2, Custom: 3 };
export const CustomCommandParamType = { BlockType: "BlockType", Boolean: "Boolean", EntitySelector: "EntitySelector", EntityType: "EntityType", Enum: "Enum", Float: "Float", Integer: "Integer", ItemType: "ItemType", Location: "Location", PlayerSelector: "PlayerSelector", String: "String" };
export const CustomCommandStatus = { Success: 0, Failure: 1 };

// ------------------------------------------------------------------ simulation state
export const sim = {
  tick: 0, time: 6000, day: 0, moon: null, weather: "Clear", pvp: true,
  log: { particles: [], privateParticles: [], sounds: [], commands: [], anims: [], titles: [], actionbar: new Map(), messages: [], warns: [], fades: [], cameras: [] },
  biomeAt: (_loc) => "minecraft:plains",
  waterAt: (_loc) => false,
  ground: 64,
  solids: new Set(), // "x,y,z" extra solid blocks
};
const restrictedDepth = { n: 0 };
function writeAllowed(what) {
  if (restrictedDepth.n > 0) throw new Error(`restricted execution: ${what} not allowed in a before-event`);
}

class Signal {
  constructor(name) {
    this.name = name;
    this.list = [];
  }
  subscribe(fn, opts) {
    this.list.push({ fn, opts });
    return fn;
  }
  unsubscribe(fn) {
    this.list = this.list.filter((l) => l.fn !== fn);
  }
  fire(ev, restricted = false) {
    for (const { fn, opts } of this.list) {
      if (opts?.buttons && !opts.buttons.includes(ev.button)) continue;
      if (opts?.state && opts.state !== ev.newButtonState) continue;
      if (restricted) restrictedDepth.n++;
      try {
        fn(ev);
      } catch (e) {
        sim.log.warns.push(`listener ${this.name} threw: ${e.stack || e}`);
      } finally {
        if (restricted) restrictedDepth.n--;
      }
    }
  }
}

// ------------------------------------------------------------------ scheduler
const jobs = [];
let nextJob = 1;
export const system = {
  get currentTick() {
    return sim.tick;
  },
  run(fn) {
    return this.runTimeout(fn, 0);
  },
  runTimeout(fn, ticks = 0) {
    const id = nextJob++;
    jobs.push({ id, at: sim.tick + Math.max(0, ticks), fn, every: 0 });
    return id;
  },
  runInterval(fn, every = 1) {
    const id = nextJob++;
    jobs.push({ id, at: sim.tick + every, fn, every: Math.max(1, every) });
    return id;
  },
  clearRun(id) {
    const i = jobs.findIndex((j) => j.id === id);
    if (i >= 0) jobs.splice(i, 1);
  },
  beforeEvents: { startup: new Signal("startup") },
};

export function runDue() {
  let guard = 0;
  for (;;) {
    const due = jobs.filter((j) => j.at <= sim.tick).sort((a, b) => a.at - b.at || a.id - b.id);
    if (due.length === 0 || guard++ > 50) break;
    for (const j of due) {
      if (j.every) j.at = sim.tick + j.every;
      else jobs.splice(jobs.indexOf(j), 1);
      try {
        j.fn();
      } catch (e) {
        sim.log.warns.push(`job threw: ${e.stack || e}`);
      }
    }
    if (due.every((j) => j.every)) break;
  }
}

export function tickN(n = 1) {
  for (let i = 0; i < n; i++) {
    sim.tick++;
    sim.time = (sim.time + 1) % 24000;
    if (sim.time === 0) sim.day++;
    for (const e of [...entities.values()]) e._tick();
    runDue();
  }
}

// ------------------------------------------------------------------ world
const dynamic = new Map();
const entities = new Map();
let nextEntity = 1;

export class Vector {}
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(k, v) {
    if (typeof v !== "number" || Number.isNaN(v)) throw new Error(`molang ${k} not a number`);
    this.vars[k] = v;
  }
  setColorRGB(k, c) {
    this.vars[k] = c;
  }
  setColorRGBA(k, c) {
    this.vars[k] = c;
  }
  setSpeedAndDirection(k, s, d) {
    this.vars[k] = { s, d };
  }
}

function blockAt(dim, loc) {
  const x = Math.floor(loc.x), y = Math.floor(loc.y), z = Math.floor(loc.z);
  const key = `${x},${y},${z}`;
  let typeId = "minecraft:air";
  if (sim.solids.has(key) || y < sim.ground) typeId = y === sim.ground - 1 ? "minecraft:grass_block" : "minecraft:stone";
  else if (sim.waterAt({ x, y, z })) typeId = "minecraft:water";
  return { typeId, location: { x, y, z }, dimension: dim, isAir: typeId === "minecraft:air", isLiquid: typeId === "minecraft:water", isWaterlogged: false, isValid: true };
}

export class Dimension {
  constructor(id) {
    this.id = id;
  }
  getEntities(o = {}) {
    return [...entities.values()].filter((e) => {
      if (!e.isValid || e.dimension !== this) return false;
      if (o.type && e.typeId !== o.type) return false;
      if (o.excludeTypes?.includes(e.typeId)) return false;
      if (o.families && !o.families.every((f) => e._families.includes(f))) return false;
      if (o.excludeFamilies?.some((f) => e._families.includes(f))) return false;
      if (o.location && o.maxDistance !== undefined) {
        const d = Math.hypot(e.location.x - o.location.x, e.location.y - o.location.y, e.location.z - o.location.z);
        if (d > o.maxDistance) return false;
      }
      return true;
    });
  }
  getPlayers(o = {}) {
    return this.getEntities({ ...o, type: "minecraft:player" }).filter((e) => !e._offline);
  }
  getBlock(loc) {
    return blockAt(this, loc);
  }
  getTopmostBlock(xz) {
    for (let y = 319; y > -64; y--) {
      const b = blockAt(this, { x: xz.x, y, z: xz.z });
      if (!b.isAir && !b.isLiquid) return b;
    }
    return undefined;
  }
  getBlockFromRay(from, dir, o = {}) {
    const max = o.maxDistance ?? 64;
    for (let t = 0; t <= max; t += 0.1) {
      const p = { x: from.x + dir.x * t, y: from.y + dir.y * t, z: from.z + dir.z * t };
      const b = blockAt(this, p);
      if (!b.isAir && !b.isLiquid) return { block: b, face: "Up", faceLocation: { x: p.x - b.location.x, y: p.y - b.location.y, z: p.z - b.location.z } };
    }
    return undefined;
  }
  getLightLevel(_loc) {
    return sim.light ?? 15;
  }
  getSkyLightLevel(_loc) {
    return sim.light ?? 15;
  }
  getBiome(loc) {
    return { id: sim.biomeAt(loc) };
  }
  spawnEntity(typeId, loc, opts) {
    writeAllowed("spawnEntity");
    if (!defs.entities.has(typeId)) throw new Error(`unknown entity ${typeId}`);
    const info = defs.entityInfo.get(typeId);
    const e = new Entity(typeId, this, { ...loc }, info?.families);
    if (info) {
      e._maxHealth = info.health;
      e._health = info.health;
    }
    if (opts?.spawnEvent !== undefined) {
      if (!info || !info.events.includes(opts.spawnEvent)) throw new Error(`unknown spawn event ${opts.spawnEvent} for ${typeId}`);
      e._spawnEvent = opts.spawnEvent;
    }
    if (opts?.initialRotation !== undefined) e._rot.y = opts.initialRotation;
    world.afterEvents.entitySpawn.fire({ entity: e });
    return e;
  }
  spawnItem(item, loc) {
    const e = new Entity("minecraft:item", this, { ...loc });
    e._item = item;
    return e;
  }
  spawnParticle(id, loc, vars) {
    writeAllowed("spawnParticle");
    if (!defs.particles.has(id)) throw new Error(`unknown particle ${id}`);
    for (const [k, v] of Object.entries(vars?.vars ?? {})) if (typeof v === "number" && !Number.isFinite(v)) throw new Error(`bad molang ${k}`);
    sim.log.particles.push({ id, loc: { ...loc }, vars: vars?.vars ?? {} });
  }
  playSound(id, loc, o) {
    if (!defs.sounds.has(id)) throw new Error(`unknown sound ${id}`);
    sim.log.sounds.push({ id, loc, o });
  }
}
const dims = { "minecraft:overworld": new Dimension("minecraft:overworld"), "minecraft:nether": new Dimension("minecraft:nether"), "minecraft:the_end": new Dimension("minecraft:the_end") };

// ------------------------------------------------------------------ items
export class EnchantmentType {
  constructor(id) {
    const ok = ["protection", "fire_protection", "blast_protection", "projectile_protection", "respiration", "aqua_affinity", "thorns", "unbreaking", "mending", "sharpness"];
    const bare = String(id).replace("minecraft:", "");
    if (!ok.includes(bare)) throw new Error(`unknown enchantment ${id}`);
    this.id = bare;
    this.maxLevel = bare === "aqua_affinity" || bare === "mending" ? 1 : bare === "respiration" || bare === "thorns" || bare === "unbreaking" ? 3 : 4;
  }
}
const PROT = ["protection", "fire_protection", "blast_protection", "projectile_protection"];
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!defs.items.has(typeId) && !typeId.startsWith("minecraft:")) throw new Error(`unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.lockMode = "none";
    this.keepOnDeath = false;
    this._ench = [];
  }
  hasTag(t) {
    return (defs.items.get(this.typeId) ?? []).includes(t);
  }
  clone() {
    const c = new ItemStack(this.typeId, this.amount);
    c.lockMode = this.lockMode;
    c.keepOnDeath = this.keepOnDeath;
    c._ench = this._ench.map((e) => ({ ...e }));
    return c;
  }
  getComponent(id) {
    if (id === "minecraft:enchantable") {
      const st = this;
      return {
        getEnchantments: () => st._ench.map((e) => ({ type: { id: e.id, maxLevel: 4 }, level: e.level })),
        getEnchantment: (t) => {
          const e = st._ench.find((x) => x.id === t.id);
          return e ? { type: t, level: e.level } : undefined;
        },
        removeEnchantment: (t) => {
          st._ench = st._ench.filter((x) => x.id !== t.id);
        },
        canAddEnchantment: (e) => !(PROT.includes(e.type.id) && st._ench.some((x) => PROT.includes(x.id) && x.id !== e.type.id)),
        addEnchantment: (e) => {
          if (PROT.includes(e.type.id) && st._ench.some((x) => PROT.includes(x.id) && x.id !== e.type.id)) throw new Error("incompatible");
          st._ench = st._ench.filter((x) => x.id !== e.type.id);
          st._ench.push({ id: e.type.id, level: e.level });
        },
      };
    }
    return undefined;
  }
}

class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  get emptySlotsCount() {
    return this.slots.filter((s) => !s).length;
  }
  getItem(i) {
    return this.slots[i]?.clone();
  }
  setItem(i, it) {
    this.slots[i] = it ? it.clone() : undefined;
  }
  addItem(it) {
    const i = this.slots.findIndex((s) => !s);
    if (i < 0) return it;
    this.slots[i] = it.clone();
    return undefined;
  }
}

// ------------------------------------------------------------------ entities
export class Entity {
  constructor(typeId, dim, loc, families) {
    this.id = String(nextEntity++);
    this.typeId = typeId;
    this.dimension = dim;
    this.location = loc;
    this._valid = true;
    this._rot = { x: 0, y: 0 };
    this._vel = { x: 0, y: 0, z: 0 };
    this._effects = new Map();
    this._dyn = new Map();
    this._tags = new Set();
    this._families = families ?? (typeId === "minecraft:player" ? ["player", "mob"] : typeId === "minecraft:villager_v2" ? ["villager", "mob"] : typeId === "plrace:velvet_mirage" ? ["plrace_mirage", "player", "mob"] : ["monster", "mob"]);
    this._maxHealth = typeId === "minecraft:player" ? 20 : typeId === "plrace:velvet_mirage" ? 1 : 20;
    this._health = this._maxHealth;
    this.isOnGround = true;
    this.isSneaking = false;
    this.isSprinting = false;
    this.isSwimming = false;
    this.isFalling = false;
    this.nameTag = "";
    this._fire = 0;
    this._hits = [];
    entities.set(this.id, this);
  }
  _check() {
    if (!this._valid) throw new Error(`InvalidEntityError: ${this.typeId} ${this.id}`);
  }
  get isValid() {
    return this._valid;
  }
  get isInWater() {
    return sim.waterAt(this.location);
  }
  _tick() {
    if (!this._valid) return;
    for (const [k, e] of this._effects) {
      e.duration--;
      if (e.duration <= 0) this._effects.delete(k);
    }
  }
  getHeadLocation() {
    this._check();
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getRotation() {
    this._check();
    return { ...this._rot };
  }
  setRotation(r) {
    this._rot = { ...r };
  }
  getViewDirection() {
    this._check();
    const yaw = (this._rot.y * Math.PI) / 180;
    const pitch = (this._rot.x * Math.PI) / 180;
    return { x: -Math.sin(yaw) * Math.cos(pitch), y: -Math.sin(pitch), z: Math.cos(yaw) * Math.cos(pitch) };
  }
  getVelocity() {
    this._check();
    return { ...this._vel };
  }
  applyKnockback(h, v) {
    this._check();
    writeAllowed("applyKnockback");
    this._vel = { x: h.x, y: v, z: h.z };
    this.location = { x: this.location.x + h.x * 2.5, y: Math.max(sim.ground, this.location.y + Math.max(0, v) * 2), z: this.location.z + h.z * 2.5 };
  }
  applyImpulse(v) {
    this._check();
    if (this.typeId === "minecraft:player") throw new Error("applyImpulse is not supported on players");
    this._vel = { ...v };
  }
  clearVelocity() {
    this._check();
    this._vel = { x: 0, y: 0, z: 0 };
  }
  teleport(loc, o) {
    this._check();
    writeAllowed("teleport");
    this.location = { ...loc };
    if (o?.dimension) this.dimension = o.dimension;
  }
  tryTeleport(loc, o) {
    this._check();
    const b = blockAt(this.dimension, loc);
    if (o?.checkForBlocks && !b.isAir && !b.isLiquid) return false;
    this.location = { ...loc };
    return true;
  }
  applyDamage(amount, opts = {}) {
    this._check();
    writeAllowed("applyDamage");
    if (typeof amount !== "number" || Number.isNaN(amount)) throw new Error("bad damage");
    const ev = { hurtEntity: this, damage: amount, cancel: false, damageSource: { cause: opts.cause ?? "none", damagingEntity: opts.damagingEntity, damagingProjectile: opts.damagingProjectile } };
    world.beforeEvents.entityHurt.fire(ev, true);
    if (ev.cancel || ev.damage <= 0) return false;
    this._hits.push({ amount: ev.damage, cause: ev.damageSource.cause, by: opts.damagingEntity?.id });
    this._health -= ev.damage;
    world.afterEvents.entityHurt.fire({ hurtEntity: this, damage: ev.damage, damageSource: ev.damageSource });
    if (this._health <= 0 && this._valid) this._die(ev.damageSource);
    return true;
  }
  _die(src) {
    world.afterEvents.entityDie.fire({ deadEntity: this, damageSource: src });
    if (this.typeId === "minecraft:player") {
      this._health = this._maxHealth;
      this._effects.clear();
      this._dead = true;
    } else this.remove();
  }
  remove() {
    this._check();
    writeAllowed("remove");
    this._valid = false;
    entities.delete(this.id);
  }
  kill() {
    this._die({ cause: "override" });
  }
  addEffect(id, duration, o = {}) {
    this._check();
    writeAllowed("addEffect");
    if (!EFFECTS.has(id)) throw new Error(`unknown effect ${id}`);
    if (!(duration > 0)) throw new Error("bad duration");
    const cur = this._effects.get(id);
    // like Bedrock: a weaker effect never replaces a stronger one; the same strength refreshes the duration
    const amp = o.amplifier ?? 0;
    if (!cur || cur.amplifier < amp || (cur.amplifier === amp && cur.duration < duration)) this._effects.set(id, { typeId: id, duration, amplifier: amp });
  }
  getEffect(id) {
    this._check();
    return this._effects.get(id);
  }
  getEffects() {
    return [...this._effects.values()];
  }
  removeEffect(id) {
    this._check();
    return this._effects.delete(id);
  }
  extinguishFire() {
    this._fire = 0;
    return true;
  }
  setOnFire(s) {
    this._fire = s;
  }
  getDynamicProperty(k) {
    return this._dyn.get(k);
  }
  setDynamicProperty(k, v) {
    writeAllowed("setDynamicProperty");
    if (typeof v === "string" && v.length > 32000) throw new Error("dynamic property too large");
    this._dyn.set(k, v);
  }
  hasTag(t) {
    return this._tags.has(t);
  }
  addTag(t) {
    this._tags.add(t);
  }
  playAnimation(name, o) {
    this._check();
    if (!defs.anims.has(name)) throw new Error(`unknown animation ${name}`);
    sim.log.anims.push({ entity: this.id, name, o });
  }
  getComponent(id) {
    this._check();
    const e = this;
    switch (id) {
      case "minecraft:health":
        return {
          get currentValue() {
            return e._health;
          },
          effectiveMax: this._maxHealth + (this._effects.get("health_boost") ? 4 * (this._effects.get("health_boost").amplifier + 1) : 0),
          defaultValue: this._maxHealth,
          setCurrentValue(v) {
            writeAllowed("health");
            e._health = Math.max(0, Math.min(this.effectiveMax, v));
          },
          resetToDefaultValue() {
            e._health = e._maxHealth;
          },
        };
      case "minecraft:type_family":
        return { hasTypeFamily: (f) => e._families.includes(f), getTypeFamilies: () => [...e._families] };
      case "minecraft:tameable":
        return e._tamed ? { isTamed: true, tamedToPlayerId: e._tamed } : undefined;
      case "minecraft:is_tamed":
        return e._tamed ? {} : undefined;
      case "minecraft:onfire":
        return e._fire > 0 ? { onFireTicksRemaining: e._fire } : undefined;
      default:
        return this._extraComponent?.(id);
    }
  }
}

export class Player extends Entity {
  constructor(name, dim, loc) {
    super("minecraft:player", dim, loc);
    this.name = name;
    this.selectedSlotIndex = 0;
    this._inv = new Container(36);
    this._equip = {};
    this._perms = new Map();
    this._move = { x: 0, y: 0 };
    this._uw = 0.02;
    this._hunger = 20;
    this._gameMode = "Survival";
    this.playerPermissionLevel = 2;
    this.commandPermissionLevel = 1;
    this._fog = [];
    const p = this;
    this.onScreenDisplay = {
      setActionBar: (t) => sim.log.actionbar.set(p.id, String(t)),
      setTitle: (t, o) => sim.log.titles.push({ p: p.id, t, o }),
    };
    this.camera = {
      fade: (o) => sim.log.fades.push({ p: p.id, o }),
      setCamera: (preset, o) => sim.log.cameras.push({ p: p.id, preset, o }),
      clear: () => sim.log.cameras.push({ p: p.id, clear: true }),
    };
    this.inputPermissions = {
      setPermissionCategory: (c, en) => p._perms.set(c, en),
      isPermissionCategoryEnabled: (c) => p._perms.get(c) ?? true,
    };
    this.inputInfo = { getMovementVector: () => ({ ...p._move }), getButtonState: () => "Released", lastInputModeUsed: "Touch", touchOnlyAffectsHotbar: false };
  }
  get isInWater() {
    return sim.waterAt(this.location);
  }
  getGameMode() {
    return this._gameMode;
  }
  sendMessage(m) {
    // RawMessage: text parts joined, translated keys shown as %key% (the client resolves them)
    const flat = (x) => (typeof x === "string" ? x : x?.rawtext ? x.rawtext.map(flat).join("") : x?.translate ? `%${x.translate}%` : x?.text ?? String(x));
    sim.log.messages.push({ p: this.id, m: flat(m) });
  }
  playSound(id, o) {
    if (!defs.sounds.has(id)) throw new Error(`unknown sound ${id}`);
    sim.log.sounds.push({ id, p: this.id, o });
  }
  spawnParticle(id, loc, vars) {
    if (!defs.particles.has(id)) throw new Error(`unknown particle ${id}`);
    sim.log.privateParticles.push({ id, p: this.id, loc, vars: vars?.vars ?? {} });
  }
  runCommand(cmd) {
    this._check();
    const m = /^fog @s (push|remove) ([a-z_:]+)(?: ([a-z_]+))?$/.exec(cmd);
    if (!m) throw new Error(`unexpected command ${cmd}`);
    if (m[1] === "push") {
      if (!defs.fogs.has(m[2])) throw new Error(`unknown fog ${m[2]}`);
      this._fog.push(m[3]);
    } else {
      const i = this._fog.indexOf(m[2]);
      if (i < 0) throw new Error("no such fog");
      this._fog.splice(i, 1);
    }
    sim.log.commands.push({ p: this.id, cmd });
    return { successCount: 1 };
  }
  _extraComponent(id) {
    const p = this;
    switch (id) {
      case "minecraft:inventory":
        return { container: p._inv };
      case "minecraft:equippable":
        return {
          getEquipment: (slot) => p._equip[slot]?.clone(),
          setEquipment: (slot, it) => {
            writeAllowed("setEquipment");
            p._equip[slot] = it ? it.clone() : undefined;
            return true;
          },
        };
      case "minecraft:player.hunger":
        return {
          get currentValue() {
            return p._hunger;
          },
          effectiveMax: 20,
          setCurrentValue(v) {
            p._hunger = v;
          },
        };
      case "minecraft:underwater_movement":
        return {
          get currentValue() {
            return p._uw;
          },
          defaultValue: 0.02,
          setCurrentValue(v) {
            p._uw = v;
          },
          resetToDefaultValue() {
            p._uw = 0.02;
          },
        };
      default:
        return undefined;
    }
  }
}

// ------------------------------------------------------------------ world object
export const world = {
  afterEvents: Object.fromEntries(["playerSpawn", "playerLeave", "playerDimensionChange", "entityHurt", "entityDie", "itemCompleteUse", "weatherChange", "entitySpawn", "playerButtonInput", "worldLoad", "explosion"].map((k) => [k, new Signal(k)])),
  beforeEvents: Object.fromEntries(["entityHurt", "playerInteractWithBlock", "playerLeave"].map((k) => [k, new Signal(k)])),
  gameRules: {
    get pvp() {
      return sim.pvp;
    },
  },
  getPlayers() {
    return [...entities.values()].filter((e) => e instanceof Player && e._valid && !e._offline);
  },
  getDimension(id) {
    return dims[id.includes(":") ? id : `minecraft:${id}`];
  },
  getEntity(id) {
    const e = entities.get(id);
    return e && e._valid ? e : undefined;
  },
  getTimeOfDay() {
    return sim.time;
  },
  getDay() {
    return sim.day;
  },
  getMoonPhase() {
    return sim.moon ?? sim.day % 8;
  },
  getAbsoluteTime() {
    return sim.day * 24000 + sim.time;
  },
  getDynamicProperty(k) {
    return dynamic.get(k);
  },
  setDynamicProperty(k, v) {
    writeAllowed("world.setDynamicProperty");
    dynamic.set(k, v);
  },
  sendMessage(m) {
    sim.log.messages.push({ p: "*", m });
  },
};

// ------------------------------------------------------------------ test helpers
export const harness = {
  dims,
  entities,
  dynamic,
  jobs,
  spawnMob(typeId, loc, dim = dims["minecraft:overworld"], families) {
    return new Entity(typeId, dim, { ...loc }, families);
  },
  join(name, loc = { x: 0.5, y: 64, z: 0.5 }) {
    const p = new Player(name, dims["minecraft:overworld"], { ...loc });
    world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
    return p;
  },
  /** Simulate logout + login of the same player (keeps dynamic properties and inventory). */
  leave(p) {
    world.beforeEvents.playerLeave.fire({ player: p }, true);
    p._offline = true;
    world.afterEvents.playerLeave.fire({ playerId: p.id, playerName: p.name });
  },
  rejoin(p) {
    p._offline = false;
    world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
  },
  respawn(p) {
    p._dead = false;
    world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: false });
  },
  changeDimension(p, id) {
    const from = p.dimension;
    p.dimension = dims[id];
    world.afterEvents.playerDimensionChange.fire({ player: p, fromDimension: from, toDimension: p.dimension, fromLocation: p.location, toLocation: p.location });
  },
};
