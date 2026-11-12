// Minimal, strict stand-in for @minecraft/server covering the API surface the
// foundation uses, so compiled scripts can run under Node for tests. It enforces
// the early-execution rule: world queries throw until the world has loaded.
// Test control lives in the `__mock` export.

export const EntityInitializationCause = { Born: "Born", Event: "Event", Loaded: "Loaded", Spawned: "Spawned", Transformed: "Transformed" };
export const CommandPermissionLevel = { Any: 0, GameDirectors: 1, Admin: 2, Host: 3, Owner: 4 };
export const CustomCommandStatus = { Success: 0, Failure: 1 };

class Signal {
  constructor(name) {
    this.name = name;
    this.subs = [];
  }
  subscribe(callback, options) {
    if (typeof callback !== "function") throw new TypeError(`${this.name}.subscribe needs a function`);
    this.subs.push({ callback, options });
    return callback;
  }
  unsubscribe(callback) {
    this.subs = this.subs.filter((s) => s.callback !== callback);
  }
  fire(event, typeId) {
    for (const { callback, options } of [...this.subs]) {
      if (options?.entityTypes && !options.entityTypes.includes(typeId)) continue;
      callback(event);
    }
  }
}

const state = {};
const dimensions = {};

function assertWorldLoaded(api) {
  if (!state.worldLoaded) throw new Error(`${api} cannot be called in early-execution mode`);
}

class Dimension {
  constructor(id) {
    this.id = id;
    this.entities = new Set();
  }
  getEntities(options = {}) {
    assertWorldLoaded("Dimension.getEntities");
    return [...this.entities].filter((e) => e.isValid && (!options.type || e.typeId === options.type));
  }
  getPlayers(options = {}) {
    assertWorldLoaded("Dimension.getPlayers");
    return [...this.entities].filter((e) => {
      if (!(e instanceof Player) || !e.isValid) return false;
      if (!options.location || options.maxDistance === undefined) return true;
      const d = Math.hypot(e.location.x - options.location.x, e.location.y - options.location.y, e.location.z - options.location.z);
      return d <= options.maxDistance;
    });
  }
}

export class Entity {
  constructor(typeId, { dimension = "minecraft:overworld", location = { x: 0, y: 64, z: 0 }, properties = [] } = {}) {
    this.id = String(state.nextEntityId++);
    this.typeId = typeId;
    this.isValid = true;
    this.location = location;
    this.dimensionId = dimension;
    this.dynamicProperties = new Map();
    this.declaredProperties = new Set(properties);
    this.properties = new Map();
  }
  assertValid() {
    if (!this.isValid) throw new Error(`entity ${this.id} is no longer valid`);
  }
  get dimension() {
    this.assertValid();
    return dimensions[this.dimensionId];
  }
  getDynamicProperty(key) {
    this.assertValid();
    return this.dynamicProperties.get(key);
  }
  setDynamicProperty(key, value) {
    this.assertValid();
    if (value === undefined) this.dynamicProperties.delete(key);
    else this.dynamicProperties.set(key, value);
  }
  setProperty(key, value) {
    this.assertValid();
    if (!this.declaredProperties.has(key)) throw new Error(`property "${key}" is not declared on ${this.typeId}`);
    this.properties.set(key, value);
  }
  getProperty(key) {
    return this.properties.get(key);
  }
}

export class Player extends Entity {
  constructor(name, options) {
    super("minecraft:player", options);
    this.name = name;
    this.actionBar = [];
    this.titles = [];
    this.onScreenDisplay = {
      setActionBar: (message) => {
        this.assertValid();
        this.actionBar.push(message);
      },
      setTitle: (title) => {
        this.assertValid();
        this.titles.push(title);
      },
    };
  }
}

export const system = {
  get currentTick() {
    return state.tick;
  },
  runInterval(callback, interval = 1) {
    const id = state.nextRunId++;
    state.runs.set(id, { callback, interval, next: state.tick + interval, repeat: true });
    return id;
  },
  runTimeout(callback, delay = 1) {
    const id = state.nextRunId++;
    state.runs.set(id, { callback, interval: delay, next: state.tick + delay, repeat: false });
    return id;
  },
  clearRun(id) {
    state.runs.delete(id);
  },
  beforeEvents: {},
  afterEvents: {},
};

export const world = {
  afterEvents: {},
  getDimension(id) {
    assertWorldLoaded("world.getDimension");
    if (!dimensions[id]) throw new Error(`unknown dimension ${id}`);
    return dimensions[id];
  },
};

export const EntityTypes = {
  get(id) {
    assertWorldLoaded("EntityTypes.get");
    return state.entityTypes.has(id) ? { id } : undefined;
  },
};

function reset() {
  Object.assign(state, { tick: 0, runs: new Map(), nextRunId: 1, nextEntityId: 1, worldLoaded: false, entityTypes: new Set(), commands: new Map() });
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) dimensions[id] = new Dimension(id);
  system.beforeEvents.startup = new Signal("startup");
  for (const name of ["worldLoad", "entitySpawn", "entityLoad", "entityRemove", "entityHurt", "entityDie", "dataDrivenEntityTrigger"]) {
    world.afterEvents[name] = new Signal(name);
  }
}
reset();

function place(entity) {
  dimensions[entity.dimensionId].entities.add(entity);
  return entity;
}

export const __mock = {
  reset,
  get commands() {
    return state.commands;
  },
  get runCount() {
    return state.runs.size;
  },
  subscriptions(signal) {
    return (world.afterEvents[signal] ?? system.beforeEvents[signal]).subs;
  },
  defineEntityTypes(...ids) {
    for (const id of ids) state.entityTypes.add(id);
  },
  startup() {
    const customCommandRegistry = {
      registerCommand(definition, callback) {
        if (!/^[a-z0-9_]+:[a-z0-9_]+$/.test(definition.name)) throw new Error(`invalid command name ${definition.name}`);
        state.commands.set(definition.name, { definition, callback });
      },
    };
    system.beforeEvents.startup.fire({ customCommandRegistry });
  },
  loadWorld() {
    state.worldLoaded = true;
    world.afterEvents.worldLoad.fire({});
  },
  /** Places an entity without firing any event (e.g. already in a loaded chunk). */
  addEntity(typeId, options) {
    return place(new Entity(typeId, options));
  },
  addPlayer(name, options) {
    return place(new Player(name, options));
  },
  spawn(typeId, cause = EntityInitializationCause.Spawned, options) {
    const entity = place(new Entity(typeId, options));
    world.afterEvents.entitySpawn.fire({ entity, cause }, typeId);
    return entity;
  },
  load(entity) {
    place(entity);
    world.afterEvents.entityLoad.fire({ entity }, entity.typeId);
  },
  hurt(entity, damage = 1) {
    world.afterEvents.entityHurt.fire({ hurtEntity: entity, damage, damageSource: { cause: "entityAttack" } }, entity.typeId);
  },
  kill(entity) {
    world.afterEvents.entityDie.fire({ deadEntity: entity, damageSource: { cause: "entityAttack" } }, entity.typeId);
  },
  remove(entity) {
    entity.isValid = false;
    dimensions[entity.dimensionId].entities.delete(entity);
    world.afterEvents.entityRemove.fire({ removedEntityId: entity.id, typeId: entity.typeId }, entity.typeId);
  },
  trigger(entity, eventId) {
    world.afterEvents.dataDrivenEntityTrigger.fire({ entity, eventId, getModifiers: () => [] }, entity.typeId);
  },
  tick(count = 1) {
    for (let i = 0; i < count; i++) {
      state.tick++;
      for (const [id, run] of [...state.runs]) {
        if (run.next > state.tick) continue;
        if (run.repeat) run.next = state.tick + run.interval;
        else state.runs.delete(id);
        run.callback();
      }
    }
  },
};
