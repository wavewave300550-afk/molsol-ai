// Strict mock of the @minecraft/server 2.11.0 surface used by THE ANATOMY OF A WORLD.
// It runs the real compiled behaviour-pack scripts against a voxel world and validates
// every identifier (blocks + states, entities, properties, particles, sounds, music, fog,
// animations, effects, items, camera presets) against the built packs and vanilla data.
// Violations are collected in `issues` instead of being silently accepted.
const DATA = globalThis.__SIM_DATA;
export const issues = [];
export const stats = { blockWrites: 0, fills: 0, particles: 0, sounds: 0, maxWritesPerTick: 0, writesThisTick: 0, spawned: {}, animations: {}, titles: [], messages: [], structuresPlaced: 0, refusedWrites: 0, refusedSpawns: 0, unloads: 0, reloads: 0, queuedStructureCells: 0 };
/** Chunk loading emulation for custom dimensions: ticking areas + a circle of `radius` chunks around players. */
export const chunkSim = { enabled: process.env.SIM_CHUNKS !== "0", radius: Number(process.env.SIM_SIM_DISTANCE ?? 4) };
let chunkEpoch = 0;
/** Faults the simulation can inject: types spawnEntity refuses, types the game did not register, a wrong spawn position. */
export const spawnFaults = { refuse: new Set(), missing: new Set(), offset: null };
export const EntityTypes = {
  get: (id) => ((DATA.entities[id] && !spawnFaults.missing.has(id)) || DATA.vanillaEntities.has(id) ? { id } : undefined),
  getAll: () => Object.keys(DATA.entities).filter((id) => !spawnFaults.missing.has(id)).map((id) => ({ id })),
};
function issue(msg) {
  if (issues.length < 400) issues.push(`[t${tick}] ${msg}`);
}
let restricted = false;
function mutating(what) {
  if (restricted) issue(`restricted-execution violation: ${what} called inside a before-event/command callback`);
}

// ------------------------------------------------------------------ enums
const mk = (names) => Object.fromEntries(names.map((n) => [n, n]));
export const EntityDamageCause = mk(["anvil", "blockExplosion", "contact", "entityAttack", "entityExplosion", "fall", "fallingBlock", "fire", "magic", "override", "projectile", "suffocation", "void"]);
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const CameraShakeType = { Positional: "Positional", Rotational: "Rotational" };
export const EasingType = mk(["InOutSine", "Linear", "InOutQuad", "OutBack"]);
export const HudVisibility = { Hide: 0, Reset: 1 };
export const InputPermissionCategory = { Camera: 1, Movement: 2, LateralMovement: 4, Sneak: 5, Jump: 6, Mount: 7, Dismount: 8, MoveForward: 9, MoveBackward: 10, MoveLeft: 11, MoveRight: 12 };
export const StructureAnimationMode = { Blocks: "Blocks", Layers: "Layers", None: "None" };
export const StructureSaveMode = { Memory: "Memory", World: "World" };
export const Difficulty = { Easy: "Easy", Hard: "Hard", Normal: "Normal", Peaceful: "Peaceful" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandParamType = mk(["BlockType", "Boolean", "EntitySelector", "EntityType", "Enum", "Float", "Integer", "ItemType", "Location", "PlayerSelector", "String"]);
export const CustomCommandStatus = { Success: 0, Failure: 1 };
export const PlayerPermissionLevel = { Visitor: 0, Member: 1, Operator: 2, Custom: 3 };
export const WaypointTexture = { Circle: "minecraft:circle", SmallSquare: "minecraft:small_square", SmallStar: "minecraft:small_star", Square: "minecraft:square" };
export class LocationInUnloadedChunkError extends Error {
  constructor(m = "LocationInUnloadedChunkError") {
    super(m);
    this.name = "LocationInUnloadedChunkError";
  }
}
export class LocationWaypoint {
  constructor(dl, sel, color) {
    if (!dl?.dimension || ![dl.x, dl.y, dl.z].every(Number.isFinite)) issue("LocationWaypoint: bad dimension location");
    const list = sel?.textureBoundsList;
    if (!Array.isArray(list) || list.length < 1 || list.length > 16) issue("LocationWaypoint: textureBoundsList needs 1..16 entries");
    for (const b of list ?? []) {
      if (!(b.lowerBound >= 0)) issue("LocationWaypoint: lowerBound must be >= 0");
      if (b.upperBound !== undefined && !(b.upperBound >= b.lowerBound)) issue("LocationWaypoint: upperBound below lowerBound");
      if (!Object.values(WaypointTexture).includes(b.texture)) issue(`LocationWaypoint: unknown texture ${b.texture}`);
    }
    if (color && ![color.red, color.green, color.blue].every((v) => v >= 0 && v <= 1)) issue("LocationWaypoint: colour components must be 0..1");
    this.location = { ...dl };
    this.textureSelector = sel;
    this.color = color;
    this.isEnabled = true;
    this.isValid = true;
    this.bars = new Set();
  }
  getDimensionLocation() {
    return this.location;
  }
  setDimensionLocation(dl) {
    mutating("waypoint.setDimensionLocation");
    this.location = { ...dl };
  }
  remove() {
    for (const b of this.bars) b.list.delete(this);
    this.bars.clear();
  }
}

// ------------------------------------------------------------------ scheduler
let tick = 0;
let nextId = 1;
const timers = new Map();
const jobs = new Map();
function schedule(fn, delay, interval) {
  const id = nextId++;
  timers.set(id, { fn, due: tick + Math.max(0, delay), interval });
  return id;
}
class Signal {
  constructor(name) {
    this.name = name;
    this.handlers = [];
  }
  subscribe(fn) {
    this.handlers.push(fn);
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h !== fn);
  }
  fire(ev, isBefore = false) {
    for (const h of this.handlers) {
      restricted = isBefore;
      try {
        h(ev);
      } catch (e) {
        issue(`handler for ${this.name} threw: ${e?.stack ?? e}`);
      } finally {
        restricted = false;
      }
    }
    return ev;
  }
}
export const system = {
  get currentTick() {
    return tick;
  },
  run: (fn) => schedule(fn, 0),
  runTimeout: (fn, d = 1) => schedule(fn, d),
  runInterval: (fn, i = 1) => schedule(fn, i, Math.max(1, i)),
  clearRun: (id) => timers.delete(id),
  runJob: (gen) => {
    const id = nextId++;
    jobs.set(id, gen);
    return id;
  },
  clearJob: (id) => jobs.delete(id),
  waitTicks: (n) => new Promise((res) => schedule(res, n)),
  sendScriptEvent: () => undefined,
  beforeEvents: { startup: new Signal("startup") },
  afterEvents: { scriptEventReceive: new Signal("scriptEventReceive") },
};
export async function advance(n = 1) {
  for (let i = 0; i < n; i++) {
    tick++;
    stats.writesThisTick = 0;
    for (const [id, t] of [...timers]) {
      if (t.due > tick) continue;
      try {
        t.fn();
      } catch (e) {
        issue(`timer threw: ${e?.stack ?? e}`);
      }
      if (t.interval) t.due = tick + t.interval;
      else timers.delete(id);
    }
    for (const [id, g] of [...jobs]) {
      try {
        if (g.next().done) jobs.delete(id);
      } catch (e) {
        issue(`job threw: ${e}`);
        jobs.delete(id);
      }
    }
    chunkStep();
    physics();
    stats.maxWritesPerTick = Math.max(stats.maxWritesPerTick, stats.writesThisTick);
    await Promise.resolve();
  }
}
export function currentTick() {
  return tick;
}

// ------------------------------------------------------------------ blocks
const NON_SOLID = new Set(["minecraft:air", "minecraft:short_grass", "minecraft:fern", "minecraft:poppy", "minecraft:cornflower", "minecraft:azure_bluet", "minecraft:moss_carpet", "minecraft:snow_layer", "minecraft:water", "minecraft:flowing_water", "minecraft:cave_vines_body_with_berries", "minecraft:cave_vines_head_with_berries", "minecraft:spore_blossom", "minecraft:hanging_roots", "minecraft:light_block_12", "minecraft:pointed_dripstone", "minecraft:amethyst_cluster", "minecraft:structure_void"]);
export class BlockPermutation {
  constructor(id, states) {
    this.type = { id };
    this.typeId = id;
    this.states = states ?? {};
    this.key = id + JSON.stringify(Object.entries(this.states).sort());
  }
  static resolve(id, states) {
    const vb = DATA.blocks.blocks[id];
    if (!vb) {
      issue(`BlockPermutation.resolve: unknown block ${id}`);
      throw new Error("unknown block " + id);
    }
    for (const [k, v] of Object.entries(states ?? {})) {
      if (!vb.includes(k)) issue(`BlockPermutation.resolve: ${id} has no state ${k}`);
      const t = DATA.blocks.state_types[k];
      if (t && typeof v !== t) issue(`BlockPermutation.resolve: ${id} state ${k} expects ${t}`);
    }
    return new BlockPermutation(id, states);
  }
}
export class BlockVolume {
  constructor(from, to) {
    this.from = from;
    this.to = to;
  }
}
export class MolangVariableMap {
  constructor() {
    this.vars = {};
  }
  setFloat(n, v) {
    if (!n.startsWith("variable.")) issue(`molang var ${n} must start with variable.`);
    if (!Number.isFinite(v)) issue(`molang ${n} not finite`);
    this.vars[n] = v;
  }
  setSpeedAndDirection(n, s, d) {
    if (!Number.isFinite(s) || !Number.isFinite(d.x + d.y + d.z)) issue(`molang ${n} not finite`);
    this.vars[n] = { s, d };
  }
  setColorRGBA(n, c) {
    this.vars[n] = c;
  }
  setColorRGB(n, c) {
    this.vars[n] = c;
  }
}
export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!DATA.items.has(typeId) && !typeId.startsWith("minecraft:")) issue(`ItemStack: unknown item ${typeId}`);
    if (typeId.startsWith("minecraft:") && !DATA.vanillaItems.has(typeId)) issue(`ItemStack: unknown vanilla item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
  }
}

// ------------------------------------------------------------------ dimensions
const kb = (x, y, z) => `${x},${y},${z}`;
class MockDimension {
  constructor(id) {
    this.id = id;
    this.blocks = new Map();
    this.heightRange = { min: -64, max: 320 };
    this.lc = undefined;
    this.lcKey = "";
  }
  /** Loaded chunks: finished ticking areas + a circle of `chunkSim.radius` chunks around each player. */
  loadedChunks() {
    const k = `${tick}:${chunkEpoch}`;
    if (this.lc && this.lcKey === k) return this.lc;
    const set = new Set();
    for (const a of tickingAreas.values()) {
      if (!a.loaded || a.dimension !== this) continue;
      for (let cx = Math.floor(a.from.x / 16); cx <= Math.floor(a.to.x / 16); cx++) for (let cz = Math.floor(a.from.z / 16); cz <= Math.floor(a.to.z / 16); cz++) set.add(`${cx},${cz}`);
    }
    const R = chunkSim.radius;
    for (const p of players) {
      if (!p.isValid || p.dimension !== this) continue;
      const pcx = Math.floor(p.location.x / 16);
      const pcz = Math.floor(p.location.z / 16);
      for (let dx = -R; dx <= R; dx++) for (let dz = -R; dz <= R; dz++) if (dx * dx + dz * dz <= R * R) set.add(`${pcx + dx},${pcz + dz}`);
    }
    this.lc = set;
    this.lcKey = k;
    return set;
  }
  chunkLoadedAt(x, z) {
    if (!chunkSim.enabled || this.id.startsWith("minecraft:")) return true;
    return this.loadedChunks().has(`${Math.floor(x / 16)},${Math.floor(z / 16)}`);
  }
  isChunkLoaded(loc) {
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) issue("isChunkLoaded non-finite location");
    return this.chunkLoadedAt(loc.x, loc.z);
  }
  setBlockPermutation(loc, perm) {
    mutating("setBlockPermutation");
    if (!(perm instanceof BlockPermutation)) issue("setBlockPermutation without a permutation");
    if (![loc.x, loc.y, loc.z].every(Number.isInteger)) issue(`setBlockPermutation non-integer location ${JSON.stringify(loc)}`);
    if (loc.y < -64 || loc.y > 319) throw new Error("LocationOutOfWorldBoundariesError");
    if (!this.chunkLoadedAt(loc.x, loc.z)) {
      stats.refusedWrites++;
      throw new LocationInUnloadedChunkError();
    }
    stats.blockWrites++;
    stats.writesThisTick++;
    if (perm.typeId === "minecraft:air") this.blocks.delete(kb(loc.x, loc.y, loc.z));
    else this.blocks.set(kb(loc.x, loc.y, loc.z), perm);
  }
  setBlockType(loc, id) {
    this.setBlockPermutation(loc, BlockPermutation.resolve(id));
  }
  fillBlocks(vol, perm, opts) {
    mutating("fillBlocks");
    const { from: a, to: b } = vol;
    const n = (Math.abs(b.x - a.x) + 1) * (Math.abs(b.y - a.y) + 1) * (Math.abs(b.z - a.z) + 1);
    if (n > 32768) {
      issue(`fillBlocks volume ${n} exceeds 32768`);
      throw new Error("fill too large");
    }
    let unloaded = false;
    for (let cx = Math.floor(Math.min(a.x, b.x) / 16); cx <= Math.floor(Math.max(a.x, b.x) / 16); cx++)
      for (let cz = Math.floor(Math.min(a.z, b.z) / 16); cz <= Math.floor(Math.max(a.z, b.z) / 16); cz++) if (!this.chunkLoadedAt(cx * 16, cz * 16)) unloaded = true;
    if (unloaded && !opts?.ignoreChunkBoundErrors) {
      stats.refusedWrites++;
      throw new LocationInUnloadedChunkError("UnloadedChunksError");
    }
    stats.fills++;
    for (let x = Math.min(a.x, b.x); x <= Math.max(a.x, b.x); x++)
      for (let z = Math.min(a.z, b.z); z <= Math.max(a.z, b.z); z++) {
        if (unloaded && !this.chunkLoadedAt(x, z)) continue; // ignoreChunkBoundErrors: unloaded parts are skipped
        for (let y = Math.min(a.y, b.y); y <= Math.max(a.y, b.y); y++) {
          if (perm.typeId === "minecraft:air") this.blocks.delete(kb(x, y, z));
          else this.blocks.set(kb(x, y, z), perm);
        }
      }
    return {};
  }
  getBlockId(x, y, z) {
    return this.blocks.get(kb(x, y, z))?.typeId ?? "minecraft:air";
  }
  isSolidAt(x, y, z) {
    return !NON_SOLID.has(this.getBlockId(Math.floor(x), Math.floor(y), Math.floor(z)));
  }
  getBlock(loc) {
    if (!this.chunkLoadedAt(loc.x, loc.z)) return undefined;
    const id = this.getBlockId(Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z));
    return { typeId: id, isAir: id === "minecraft:air", isLiquid: id.includes("water"), x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z), dimension: this, permutation: this.blocks.get(kb(Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z))) };
  }
  spawnEntity(id, loc, opts) {
    mutating("spawnEntity");
    if (!DATA.entities[id] && !DATA.vanillaEntities.has(id)) issue(`spawnEntity unknown ${id}`);
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) issue(`spawnEntity ${id} at non-finite location`);
    if (!this.chunkLoadedAt(loc.x, loc.z)) {
      stats.refusedSpawns++;
      throw new LocationInUnloadedChunkError();
    }
    if (spawnFaults.missing.has(id)) throw new Error(`InvalidArgumentError: Invalid entity identifier '${id}'`);
    if (spawnFaults.refuse.has(id)) throw new Error("EntitySpawnError: the entity could not be spawned");
    return this.createEntity(id, loc, opts);
  }
  createEntity(id, loc, opts) {
    if (spawnFaults.offset) loc = { x: loc.x + spawnFaults.offset.x, y: loc.y + spawnFaults.offset.y, z: loc.z + spawnFaults.offset.z };
    const e = new MockEntity(id, { ...loc }, this);
    if (opts?.initialRotation !== undefined) e.rot.y = opts.initialRotation;
    stats.spawned[id] = (stats.spawned[id] ?? 0) + 1;
    entities.add(e);
    world.afterEvents.entitySpawn.fire({ entity: e, cause: "Spawned" });
    return e;
  }
  spawnItem(stack, loc) {
    mutating("spawnItem");
    if (!this.chunkLoadedAt(loc.x, loc.z)) throw new LocationInUnloadedChunkError();
    const e = new MockEntity("minecraft:item", { ...loc }, this);
    e.item = stack;
    entities.add(e);
    return e;
  }
  spawnXp(loc, n) {
    if (!(n > 0)) issue("spawnXp amount");
  }
  spawnParticle(id, loc, molang) {
    if (!DATA.particles[id] && !DATA.vanillaParticles.has(id.replace("minecraft:", ""))) issue(`spawnParticle unknown ${id}`);
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) issue(`spawnParticle ${id} non-finite location`);
    const p = DATA.particles[id];
    if (p && molang) {
      // every variable the effect reads must be provided (or deliberately default to 0)
      for (const v of p.vars) if (!(v in molang.vars) && !(p.optional ?? []).includes(v)) issue(`particle ${id} reads ${v} but it was not set`);
    }
    stats.particles++;
  }
  playSound(id, loc, opts) {
    if (!DATA.sounds.has(id)) issue(`playSound unknown ${id}`);
    if (opts?.volume !== undefined && !(opts.volume >= 0)) issue(`playSound ${id} bad volume`);
    stats.sounds++;
    return {};
  }
  getEntities(opts = {}) {
    const near = (e) => !opts.location || opts.maxDistance === undefined || Math.hypot(e.location.x - opts.location.x, e.location.y - opts.location.y, e.location.z - opts.location.z) <= opts.maxDistance;
    return [...entities].filter((e) => e.isValid && e.dimension === this && (!opts.type || e.typeId === opts.type) && (!opts.families || opts.families.every((f) => e.families().includes(f))) && (!opts.tags || opts.tags.every((t) => e.tags.has(t))) && near(e));
  }
  getPlayers() {
    return players.filter((p) => p.dimension === this);
  }
  runCommand(cmd) {
    mutating("runCommand");
    const m = /^summon (\S+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)$/.exec(String(cmd).trim());
    if (m) {
      const [, id, x, y, z] = m;
      if (spawnFaults.missing.has(id) || (!DATA.entities[id] && !DATA.vanillaEntities.has(id))) throw new Error(`CommandError: Unknown entity type ${id}`);
      if (!this.chunkLoadedAt(+x, +z)) return { successCount: 0 };
      stats.summons = (stats.summons ?? 0) + 1;
      this.createEntity(id, { x: +x, y: +y, z: +z }, {});
      return { successCount: 1 };
    }
    return { successCount: 1 };
  }
}
const dims = new Map();
function dimension(id) {
  if (!dims.has(id)) {
    const known = ["minecraft:overworld", "minecraft:nether", "minecraft:the_end", "overworld"].includes(id) || DATA.dimensions.has(id);
    if (!known) issue(`getDimension unknown ${id}`);
    dims.set(id, new MockDimension(id));
  }
  return dims.get(id);
}
export function dimensionFor(id) {
  return dimension(id);
}

// ------------------------------------------------------------------ entities
const entities = new Set();
let entityCounter = 1;
class HealthComponent {
  constructor(e, max) {
    this.e = e;
    this.effectiveMax = max;
    this.defaultValue = max;
    this.currentValue = max;
    this.effectiveMin = 0;
  }
  setCurrentValue(v) {
    mutating("setCurrentValue");
    if (!Number.isFinite(v)) issue(`setCurrentValue non-finite on ${this.e.typeId}`);
    this.currentValue = Math.max(0, Math.min(this.effectiveMax, v));
    return true;
  }
  resetToMaxValue() {
    this.currentValue = this.effectiveMax;
  }
}
export class Entity {
  constructor(typeId, location, dim) {
    this.id = String(entityCounter++);
    this.typeId = typeId;
    this.location = location;
    this.dimension = dim;
    this.isValid = true;
    this.tags = new Set();
    this.vel = { x: 0, y: 0, z: 0 };
    this.rot = { x: 0, y: 0 };
    this.dyn = new Map();
    const def = DATA.entities[typeId];
    this.props = {};
    this.propDefs = def?.properties ?? {};
    for (const [k, p] of Object.entries(this.propDefs)) this.props[k] = p.default;
    this.health = def?.health !== undefined ? new HealthComponent(this, def.health) : typeId === "minecraft:player" ? new HealthComponent(this, 20) : undefined;
    this.projectile = def?.projectile ? { owner: undefined, gravity: def.gravity ?? 0.05, shoot: (v) => this.shoot(v) } : undefined;
    this.flying = false;
  }
  families() {
    return DATA.entities[this.typeId]?.families ?? (this.typeId === "minecraft:player" ? ["player", "mob"] : []);
  }
  get isOnGround() {
    return this.dimension.isSolidAt(this.location.x, this.location.y - 0.05, this.location.z);
  }
  get isSneaking() {
    return false;
  }
  setProperty(name, value) {
    mutating("setProperty");
    if (!this.isValid) throw new Error(`InvalidEntityError: setProperty ${name} on an unloaded/removed ${this.typeId}`);
    const d = this.propDefs[name];
    if (!d) {
      issue(`setProperty ${name} not declared on ${this.typeId}`);
      return;
    }
    if (d.type === "int" && (!Number.isInteger(value) || value < d.range[0] || value > d.range[1])) issue(`setProperty ${name}=${value} out of range on ${this.typeId}`);
    if (d.type === "bool" && typeof value !== "boolean") issue(`setProperty ${name} expects bool on ${this.typeId}`);
    this.props[name] = value;
  }
  getProperty(name) {
    return this.props[name];
  }
  getComponent(name) {
    if (!this.isValid) throw new Error("InvalidEntityError");
    if (name === "minecraft:health" || name === "health") return this.health;
    if (name === "minecraft:projectile") return this.projectile;
    if (name === "minecraft:inventory") return this.inventory;
    return undefined;
  }
  hasComponent(name) {
    return !!this.getComponent(name);
  }
  addTag(t) {
    this.tags.add(t);
    return true;
  }
  hasTag(t) {
    return this.tags.has(t);
  }
  removeTag(t) {
    return this.tags.delete(t);
  }
  getTags() {
    return [...this.tags];
  }
  matches(opts) {
    return (opts.families ?? []).every((f) => this.families().includes(f));
  }
  teleport(loc, opts = {}) {
    mutating("teleport");
    if (!this.isValid) throw new Error("InvalidEntityError");
    if (![loc.x, loc.y, loc.z].every(Number.isFinite)) issue(`teleport ${this.typeId} to non-finite location`);
    if (opts.dimension) this.dimension = opts.dimension;
    if (this instanceof Player) {
      this.lastTeleport = { tick, to: { ...loc }, stack: new Error().stack.split("\n").slice(2, 6).map((l) => l.trim().replace(/file:\/\/\S*\//, "")).join(" < ") };
      chunkEpoch++;
    }
    this.location = { ...loc };
    if (!opts.keepVelocity) this.vel = { x: 0, y: 0, z: 0 };
  }
  tryTeleport(loc, opts) {
    this.teleport(loc, opts);
    return true;
  }
  applyKnockback(h, v) {
    mutating("applyKnockback");
    if (!Number.isFinite(h.x + h.z + v)) issue("applyKnockback non-finite");
    this.vel = { x: h.x, y: v, z: h.z };
  }
  applyImpulse(v) {
    mutating("applyImpulse");
    this.vel = { x: this.vel.x + v.x, y: this.vel.y + v.y, z: this.vel.z + v.z };
    this.flying = true;
  }
  clearVelocity() {
    this.vel = { x: 0, y: 0, z: 0 };
  }
  getVelocity() {
    return { ...this.vel };
  }
  getRotation() {
    return { ...this.rot };
  }
  setRotation(r) {
    this.rot = { ...r };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  getViewDirection() {
    return { x: -Math.sin((this.rot.y * Math.PI) / 180), y: 0, z: Math.cos((this.rot.y * Math.PI) / 180) };
  }
  addEffect(id, dur, opts) {
    mutating("addEffect");
    if (!DATA.effects.has(id.replace("minecraft:", ""))) issue(`addEffect unknown ${id}`);
    if (!(dur > 0)) issue(`addEffect ${id} bad duration`);
    void opts;
    return {};
  }
  removeEffect() {
    return true;
  }
  playAnimation(name, opts) {
    mutating("playAnimation");
    if (!this.isValid) throw new Error(`InvalidEntityError: playAnimation on an unloaded/removed ${this.typeId}`);
    if (!DATA.animations.has(name)) issue(`playAnimation unknown ${name}`);
    const users = DATA.animUsers[name] ?? [];
    if (!users.includes(this.typeId)) issue(`playAnimation ${name} on ${this.typeId}, whose geometry it was not made for`);
    stats.animations[name] = (stats.animations[name] ?? 0) + 1;
    void opts;
  }
  applyDamage(amount, opts) {
    mutating("applyDamage");
    if (!Number.isFinite(amount)) issue("applyDamage non-finite");
    return dealDamage(this, amount, opts?.cause ?? "none", opts?.damagingEntity);
  }
  remove() {
    mutating("remove");
    if (!this.isValid) throw new Error("InvalidEntityError: remove on removed entity");
    this.isValid = false;
    entities.delete(this);
  }
  kill() {
    this.remove();
    return true;
  }
  getDynamicProperty(k) {
    return this.dyn.get(k);
  }
  setDynamicProperty(k, v) {
    if (v === undefined) this.dyn.delete(k);
    else this.dyn.set(k, v);
  }
  shoot(v) {
    if (!Number.isFinite(v.x + v.y + v.z)) issue("projectile shoot non-finite");
    this.vel = { ...v };
    this.flying = true;
  }
  get nameTag() {
    return this._nameTag ?? "";
  }
  set nameTag(v) {
    mutating("nameTag");
    if (!this.isValid) throw new Error("InvalidEntityError: nameTag on an unloaded/removed entity");
    if (typeof v !== "string") issue("nameTag must be a string");
    this._nameTag = v;
  }
}
const MockEntity = Entity;

function dealDamage(target, amount, cause, damager) {
  if (!target.isValid || !target.health) return false;
  const ev = { hurtEntity: target, damage: amount, cancel: false, damageSource: { cause, damagingEntity: damager } };
  world.beforeEvents.entityHurt.fire(ev, true);
  if (ev.cancel) return false;
  target.health.currentValue = Math.max(0, target.health.currentValue - ev.damage);
  world.afterEvents.entityHurt.fire({ hurtEntity: target, damage: ev.damage, damageSource: ev.damageSource });
  if (target.health.currentValue <= 0) {
    world.afterEvents.entityDie.fire({ deadEntity: target, damageSource: ev.damageSource });
    if (target instanceof Player) target.die();
    else if (target.isValid) {
      target.isValid = false;
      entities.delete(target);
    }
  }
  return true;
}

// ------------------------------------------------------------------ players
const players = [];
class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i];
  }
  setItem(i, it) {
    this.slots[i] = it;
  }
  addItem(it) {
    const i = this.slots.findIndex((s) => !s);
    if (i >= 0) this.slots[i] = it;
    return undefined;
  }
}
export class Player extends Entity {
  constructor(name, dim, loc) {
    super("minecraft:player", loc, dim);
    this.name = name;
    this.gameMode = GameMode.Survival;
    this.inventory = { container: new Container(36) };
    this.fogStack = [];
    this.music = undefined;
    this.cameraState = "default";
    this.hud = HudVisibility.Reset;
    this.inputs = {};
    this.playerPermissionLevel = PlayerPermissionLevel.Operator;
    this.deaths = 0;
    this.titles = [];
    const self = this;
    this.camera = {
      setCamera(preset, opts) {
        mutating("camera.setCamera");
        if (!DATA.cameraPresets.has(preset)) issue(`setCamera unknown preset ${preset}`);
        if (opts?.location && !Number.isFinite(opts.location.x + opts.location.y + opts.location.z)) issue("setCamera non-finite");
        self.cameraState = preset;
      },
      clear() {
        self.cameraState = "default";
      },
      fade() {},
      addShake(o) {
        if (!(o.intensity >= 0 && o.intensity <= 4)) issue(`addShake intensity ${o.intensity}`);
      },
      stopShaking() {},
    };
    this.onScreenDisplay = {
      setTitle(t, o) {
        self.titles.push(String(t) + " | " + String(o?.subtitle ?? ""));
        stats.titles.push(String(t) + " | " + String(o?.subtitle ?? ""));
      },
      setActionBar(t) {
        self.actionbar = String(t);
      },
      setHudVisibility(v) {
        self.hud = v;
      },
      updateSubtitle() {},
    };
    this.locatorBar = {
      list: new Set(),
      maxCount: 64,
      get count() {
        return this.list.size;
      },
      addWaypoint(w) {
        mutating("locatorBar.addWaypoint");
        if (!(w instanceof LocationWaypoint)) issue("addWaypoint: not a waypoint");
        if (this.list.has(w)) throw new Error("LocatorBarError: waypoint already in the locator bar");
        if (this.list.size >= this.maxCount) throw new Error("LocatorBarError: locator bar full");
        this.list.add(w);
        w.bars.add(this);
      },
      hasWaypoint(w) {
        return this.list.has(w);
      },
      removeWaypoint(w) {
        if (!this.list.has(w)) throw new Error("LocatorBarError: waypoint not in the locator bar");
        this.list.delete(w);
        w.bars.delete(this);
      },
      removeAllWaypoints() {
        for (const w of this.list) w.bars.delete(this);
        this.list.clear();
      },
      getAllWaypoints() {
        return [...this.list];
      },
    };
    this.inputPermissions = {
      setPermissionCategory(c, en) {
        self.inputs[c] = en;
      },
      isPermissionCategoryEnabled(c) {
        return self.inputs[c] !== false;
      },
    };
    this.fogSettings = {
      push(id, tag) {
        if (!DATA.fogs.has(id)) issue(`fog push unknown ${id}`);
        self.fogStack.push({ id, tag });
        return self.fogStack.length;
      },
      remove(tag) {
        const n = self.fogStack.length;
        self.fogStack = self.fogStack.filter((f) => f.tag !== tag);
        return n !== self.fogStack.length;
      },
      getStack() {
        return self.fogStack.map((f) => f.id);
      },
    };
  }
  families() {
    return ["player", "mob"];
  }
  getGameMode() {
    return this.gameMode;
  }
  setGameMode(m) {
    this.gameMode = m;
  }
  playMusic(id, opts) {
    if (!DATA.sounds.has(id) || !DATA.music.has(id)) issue(`playMusic unknown or non-music ${id}`);
    this.music = id;
    void opts;
  }
  stopMusic() {
    this.music = undefined;
  }
  sendMessage(m) {
    stats.messages.push(`${this.name}: ${typeof m === "string" ? m : JSON.stringify(m)}`);
  }
  getSpawnPoint() {
    return undefined;
  }
  die() {
    this.deaths++;
    // respawn in the overworld at world spawn with full health
    this.dimension = dimension("minecraft:overworld");
    this.location = { x: 0.5, y: 65, z: 0.5 };
    this.health.currentValue = this.health.effectiveMax;
    this.vel = { x: 0, y: 0, z: 0 };
    world.afterEvents.playerSpawn.fire({ player: this, initialSpawn: false });
  }
}

/** Simple player/projectile physics: gravity, ground collision. */
function physics() {
  for (const p of players) {
    if (!p.isValid || p.gameMode === GameMode.Creative) continue;
    const d = p.dimension;
    const l = p.location;
    // suffocation check: feet/head inside a solid block
    if (d.isSolidAt(l.x, l.y + 0.1, l.z) && d.isSolidAt(l.x, l.y + 1.2, l.z)) p.suffocatingTicks = (p.suffocatingTicks ?? 0) + 1;
    else p.suffocatingTicks = 0;
    if (p.suffocatingTicks === 20) issue(`${p.name} stuck inside blocks at ${l.x.toFixed(1)},${l.y.toFixed(1)},${l.z.toFixed(1)} (${d.getBlockId(Math.floor(l.x), Math.floor(l.y), Math.floor(l.z))}); last teleport t${p.lastTeleport?.tick}: ${p.lastTeleport?.stack}`);
    p.vel.y -= 0.08;
    p.vel.y *= 0.98;
    const ny = l.y + p.vel.y;
    if (p.vel.y < 0 && d.isSolidAt(l.x, ny, l.z)) {
      p.location = { x: l.x, y: Math.floor(ny) + 1, z: l.z };
      p.vel.y = 0;
    } else p.location = { x: l.x, y: ny, z: l.z };
    const nx = p.location.x + p.vel.x;
    const nz = p.location.z + p.vel.z;
    if (!d.isSolidAt(nx, p.location.y + 0.1, nz)) p.location = { ...p.location, x: nx, z: nz };
    p.vel.x *= 0.6;
    p.vel.z *= 0.6;
    if (p.location.y < -70) p.applyDamage(1000, { cause: "void" });
  }
  for (const e of [...entities]) {
    if (!e.isValid || !e.flying) continue;
    const g = e.projectile ? e.projectile.gravity : 0.08;
    e.location = { x: e.location.x + e.vel.x, y: e.location.y + e.vel.y, z: e.location.z + e.vel.z };
    e.vel.y -= g;
    const hitPlayer = players.find((p) => p.dimension === e.dimension && Math.abs(p.location.x - e.location.x) < 1.3 && Math.abs(p.location.z - e.location.z) < 1.3 && e.location.y >= p.location.y - 0.5 && e.location.y <= p.location.y + 1.8);
    if (e.projectile && hitPlayer) {
      e.flying = false;
      world.afterEvents.projectileHitEntity.fire({ projectile: e, location: { ...e.location }, dimension: e.dimension, getEntityHit: () => ({ entity: hitPlayer }) });
      if (e.isValid) e.remove();
      continue;
    }
    if (e.dimension.isSolidAt(e.location.x, e.location.y, e.location.z) || e.location.y < -64) {
      e.flying = false;
      if (e.projectile) {
        world.afterEvents.projectileHitBlock.fire({ projectile: e, location: { ...e.location }, dimension: e.dimension, getBlockHit: () => ({}) });
        if (e.isValid) e.remove();
      }
    }
  }
}

// ------------------------------------------------------------------ structures / ticking areas
class MockStructure {
  constructor(id, size) {
    this.id = id;
    this.size = { ...size };
    this.cells = new Map();
    this.isValid = true;
  }
  setBlockPermutation(loc, perm) {
    if (loc.x < 0 || loc.y < 0 || loc.z < 0 || loc.x >= this.size.x || loc.y >= this.size.y || loc.z >= this.size.z) {
      issue(`structure ${this.id}: write outside bounds ${JSON.stringify(loc)}`);
      throw new Error("outside structure bounds");
    }
    const k = kb(loc.x, loc.y, loc.z);
    if (perm === undefined) this.cells.delete(k);
    else this.cells.set(k, perm);
  }
  getBlockPermutation(loc) {
    return this.cells.get(kb(loc.x, loc.y, loc.z));
  }
}
const structures = new Map();
const queuedCells = new Map();
const structureManager = {
  createEmpty(id, size, mode) {
    mutating("structureManager.createEmpty");
    if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(id)) issue(`structure id ${id} invalid`);
    if (structures.has(id)) throw new Error("structure id in use");
    if (size.x > 64 || size.z > 64 || size.y > 384) {
      issue(`structure ${id} size ${JSON.stringify(size)} exceeds 64x384x64`);
      throw new Error("structure too large");
    }
    void mode;
    const s = new MockStructure(id, size);
    structures.set(id, s);
    return s;
  },
  delete(id) {
    const k = typeof id === "string" ? id : id.id;
    return structures.delete(k);
  },
  get(id) {
    return structures.get(id);
  },
  place(s, dim, loc, opts) {
    mutating("structureManager.place");
    const st = typeof s === "string" ? structures.get(s) : s;
    if (!st) throw new Error("no structure");
    if (opts?.animationMode && !["Blocks", "Layers", "None"].includes(opts.animationMode)) issue("bad animationMode");
    stats.structuresPlaced++;
    // "Structures placed in unloaded chunks will be queued for loading": cells of unloaded chunks wait
    for (const [k, perm] of st.cells) {
      const [x, y, z] = k.split(",").map(Number);
      const wx = loc.x + x;
      const wy = loc.y + y;
      const wz = loc.z + z;
      if (!dim.chunkLoadedAt(wx, wz)) {
        const ck = `${dim.id}|${Math.floor(wx / 16)},${Math.floor(wz / 16)}`;
        if (!queuedCells.has(ck)) queuedCells.set(ck, []);
        queuedCells.get(ck).push([wx, wy, wz, perm]);
        stats.queuedStructureCells++;
        continue;
      }
      if (perm.typeId === "minecraft:air") dim.blocks.delete(kb(wx, wy, wz));
      else dim.blocks.set(kb(wx, wy, wz), perm);
    }
  },
};
const tickingAreas = new Map();
const tickingAreaManager = {
  maxChunkCount: Number(process.env.SIM_MAX_CHUNKS ?? 300),
  get chunkCount() {
    let n = 0;
    for (const a of tickingAreas.values()) n += a.chunks;
    return n;
  },
  chunksOf(o) {
    const cx = Math.floor(o.to.x / 16) - Math.floor(o.from.x / 16) + 1;
    const cz = Math.floor(o.to.z / 16) - Math.floor(o.from.z / 16) + 1;
    return cx * cz;
  },
  hasCapacity(o) {
    const cx = Math.floor(o.to.x / 16) - Math.floor(o.from.x / 16) + 1;
    const cz = Math.floor(o.to.z / 16) - Math.floor(o.from.z / 16) + 1;
    if (cx > 255 || cz > 255 || cx < 1 || cz < 1) return false;
    return this.chunkCount + this.chunksOf(o) <= this.maxChunkCount;
  },
  createTickingArea(id, o) {
    mutating("createTickingArea");
    if (!o?.dimension || !o.from || !o.to) issue("createTickingArea: options need dimension/from/to");
    if (tickingAreas.has(id)) throw new Error(`TickingAreaError: identifier ${id} already used`);
    if (!this.hasCapacity(o)) return Promise.reject(new Error("TickingAreaError: not enough chunk capacity"));
    const area = { ...o, id, chunks: this.chunksOf(o), loaded: false };
    tickingAreas.set(id, area);
    return new Promise((res) =>
      schedule(() => {
        if (tickingAreas.get(id) === area) {
          area.loaded = true;
          chunkEpoch++;
        }
        res();
      }, 3),
    );
  },
  hasTickingArea(id) {
    return tickingAreas.has(id);
  },
  getTickingArea(id) {
    const a = tickingAreas.get(typeof id === "string" ? id : id.identifier);
    return a ? { identifier: a.id, chunkCount: a.chunks, dimension: a.dimension, isFullyLoaded: a.loaded } : undefined;
  },
  removeTickingArea(id) {
    const k = typeof id === "string" ? id : id.identifier;
    if (!tickingAreas.has(k)) throw new Error(`TickingAreaError: no ticking area ${k}`);
    tickingAreas.delete(k);
    chunkEpoch++;
  },
  getAllTickingAreas() {
    return [...tickingAreas.values()].map((a) => ({ identifier: a.id, chunkCount: a.chunks, dimension: a.dimension, isFullyLoaded: a.loaded }));
  },
  removeAllTickingAreas() {
    tickingAreas.clear();
    chunkEpoch++;
  },
};

// ------------------------------------------------------------------ chunk loading: entities + queued structure cells
const stored = [];
function snapshot(e) {
  return { id: e.id, typeId: e.typeId, dimension: e.dimension, location: { ...e.location }, rot: { ...e.rot }, props: { ...e.props }, tags: [...e.tags], hp: e.health?.currentValue, dyn: [...e.dyn], item: e.item, vel: { ...e.vel }, flying: e.flying, nameTag: e._nameTag };
}
function restore(sn) {
  const e = new Entity(sn.typeId, { ...sn.location }, sn.dimension);
  e.id = sn.id;
  e.rot = { ...sn.rot };
  e.props = { ...sn.props };
  e.tags = new Set(sn.tags);
  if (e.health && sn.hp !== undefined) e.health.currentValue = sn.hp;
  e.dyn = new Map(sn.dyn);
  e.item = sn.item;
  e.vel = { ...sn.vel };
  e.flying = sn.flying;
  e._nameTag = sn.nameTag;
  return e;
}
/** Unload entities whose chunk is no longer loaded; reload stored ones (new handles, entityLoad fires). */
function chunkStep() {
  if (!chunkSim.enabled) return;
  for (const e of [...entities]) {
    if (!e.isValid || e instanceof Player || e.dimension.id.startsWith("minecraft:")) continue;
    if (e.dimension.chunkLoadedAt(e.location.x, e.location.z)) continue;
    stored.push(snapshot(e));
    e.isValid = false;
    entities.delete(e);
    stats.unloads++;
  }
  for (let i = stored.length - 1; i >= 0; i--) {
    const sn = stored[i];
    if (!sn.dimension.chunkLoadedAt(sn.location.x, sn.location.z)) continue;
    stored.splice(i, 1);
    const e = restore(sn);
    entities.add(e);
    stats.reloads++;
    world.afterEvents.entityLoad.fire({ entity: e });
  }
  for (const [ck, cells] of [...queuedCells]) {
    const [did, c] = ck.split("|");
    const dim = dims.get(did);
    const [cx, cz] = c.split(",").map(Number);
    if (!dim || !dim.chunkLoadedAt(cx * 16, cz * 16)) continue;
    queuedCells.delete(ck);
    for (const [x, y, z, perm] of cells) {
      if (perm.typeId === "minecraft:air") dim.blocks.delete(kb(x, y, z));
      else dim.blocks.set(kb(x, y, z), perm);
    }
  }
}
export function storedEntities() {
  return stored.map((s) => ({ ...s }));
}
/** Put an entity straight into storage (as if a chunk was saved with it). */
export function storeEntity(typeId, dim, location, tags = []) {
  const e = new Entity(typeId, { ...location }, dim);
  e.tags = new Set(tags);
  stored.push(snapshot(e));
  return e.id;
}
export function queuedStructureCells() {
  let n = 0;
  for (const c of queuedCells.values()) n += c.length;
  return n;
}
export function tickingAreaIds() {
  return [...tickingAreas.keys()];
}
export function tickingAreaChunks() {
  return tickingAreaManager.chunkCount;
}

// ------------------------------------------------------------------ world
const worldDyn = new Map();
const sig = (n) => new Signal(n);
export const world = {
  afterEvents: {
    worldLoad: sig("worldLoad"),
    playerSpawn: sig("playerSpawn"),
    itemUse: sig("itemUse"),
    entityHurt: sig("entityHurt"),
    entityDie: sig("entityDie"),
    projectileHitBlock: sig("projectileHitBlock"),
    projectileHitEntity: sig("projectileHitEntity"),
    playerPlaceBlock: sig("playerPlaceBlock"),
    entitySpawn: sig("entitySpawn"),
    entityLoad: sig("entityLoad"),
  },
  beforeEvents: { entityHurt: sig("entityHurt(before)"), playerBreakBlock: sig("playerBreakBlock(before)"), explosion: sig("explosion(before)") },
  structureManager,
  tickingAreaManager,
  getDimension: (id) => dimension(id),
  getAllPlayers: () => players.filter((p) => p.isValid),
  getPlayers: () => players.filter((p) => p.isValid),
  getDynamicProperty: (k) => worldDyn.get(k),
  setDynamicProperty: (k, v) => {
    if (v === undefined) worldDyn.delete(k);
    else {
      if (typeof v === "string" && v.length > 32000) issue(`world dynamic property ${k} too long (${v.length})`);
      worldDyn.set(k, v);
    }
  },
  sendMessage: (m) => stats.messages.push(`[world] ${m}`),
  getDifficulty: () => Difficulty.Normal,
  getTimeOfDay: () => 6000,
  getDefaultSpawnLocation: () => ({ x: 0, y: 65, z: 0 }),
  getEntity: (id) => [...entities].find((e) => e.id === id),
};

export function addPlayer(name, loc = { x: 0.5, y: 65, z: 0.5 }) {
  const p = new Player(name, dimension("minecraft:overworld"), { ...loc });
  players.push(p);
  return p;
}
export function allEntities() {
  return [...entities].filter((e) => e.isValid);
}
export function resetWorldDyn() {
  worldDyn.clear();
}
export function playerAttack(p, target, damage) {
  return dealDamage(target, damage, "entityAttack", p);
}
