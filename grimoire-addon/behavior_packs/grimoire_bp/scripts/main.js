// src/main.ts
import { CommandPermissionLevel, CustomCommandStatus, ItemStack as ItemStack2, Player as Player4, system as system4, world as world5 } from "@minecraft/server";

// src/config/global.ts
var CONFIG = {
  input: {
    /** Minimum ticks Use must be held before a release counts as a cast (20 ticks = 1 s). */
    minHoldTicks: 6,
    /** Ticks after a cast/cancel during which a new hold is ignored (guards duplicate callbacks). */
    rearmTicks: 2,
    /**
     * Compatibility fallback, OFF by default.  If a platform never raises itemStartUse for the
     * Grimoire, hold/release can be inferred from the repeating itemUse heartbeat instead.
     * Toggle in game with:  /scriptevent grimoire:config heartbeat on|off
     */
    heartbeatFallback: false,
    heartbeatGapTicks: 7
  },
  hud: {
    /** Ticks between action-bar refreshes while a Grimoire is held. */
    refreshTicks: 10
  },
  targeting: {
    /** Entity families treated as hostile spell targets. */
    hostileFamilies: ["monster"],
    /** Any entity carrying this tag is also treated as hostile (handy for test dummies). */
    testTag: "grimoire_target",
    /** When true other players are hostile targets instead of allies. */
    pvp: false,
    /** How far the caster's aim ray reaches when picking a target point. */
    aimRange: 40,
    /** Hard cap on targets a single query returns. */
    maxTargets: 24
  },
  limits: {
    /** Maximum spell entities alive at once across the whole world. */
    maxActors: 220,
    /** Maximum temporary blocks (barriers / lights) alive at once. */
    maxTempBlocks: 1400,
    /** Maximum script-spawned particles per tick. */
    maxParticlesPerTick: 90
  }
};
var RUNTIME = CONFIG;

// src/core/input.ts
import { EquipmentSlot, system, world as world2 } from "@minecraft/server";

// src/lib/scene.ts
import { world } from "@minecraft/server";
var NS = "grimoire";
var warned = /* @__PURE__ */ new Set();
function warnOnce(key, msg) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn(`[grimoire] ${msg}`);
}
var Actor = class {
  constructor(entity, typeId) {
    this.entity = entity;
    this.typeId = typeId;
  }
  lastYaw = 0;
  get valid() {
    return this.entity !== void 0 && this.entity.isValid;
  }
  get loc() {
    return this.valid ? this.entity.location : { x: 0, y: 0, z: 0 };
  }
  get yaw() {
    return this.lastYaw;
  }
  prop(name, value) {
    if (!this.valid) return this;
    try {
      this.entity.setProperty(`${NS}:${name}`, value);
    } catch (e) {
      warnOnce(`${this.typeId}.${name}`, `cannot set ${name}=${value} on ${this.typeId}: ${e}`);
    }
    return this;
  }
  state(n) {
    return this.prop("state", n);
  }
  kind(n) {
    return this.prop("kind", n);
  }
  size(n) {
    return this.prop("size", n);
  }
  skin(n) {
    return this.prop("skin", n);
  }
  /** Teleport (and optionally face a yaw).  Called every tick this gives smooth motion. */
  move(loc, yaw) {
    if (!this.valid) return this;
    if (yaw !== void 0) this.lastYaw = yaw;
    try {
      this.entity.teleport(loc, { rotation: { x: 0, y: this.lastYaw } });
    } catch {
    }
    return this;
  }
  face(yaw) {
    if (!this.valid) return this;
    this.lastYaw = yaw;
    try {
      this.entity.setRotation({ x: 0, y: yaw });
    } catch {
    }
    return this;
  }
  anim(name) {
    if (!this.valid) return this;
    try {
      this.entity.playAnimation(name);
    } catch {
    }
    return this;
  }
  remove() {
    if (!this.valid) return;
    try {
      this.entity.remove();
    } catch {
    }
  }
};
var Scene = class {
  constructor(spellId, caster) {
    this.spellId = spellId;
    this.caster = caster;
    this.dim = caster.dimension;
    this.dimId = caster.dimension.id;
    this.origin = { ...caster.location };
  }
  tick = 0;
  ended = false;
  dim;
  dimId;
  origin;
  actors = /* @__PURE__ */ new Set();
  timeline = [];
  loops = [];
  endHooks = [];
  endTick = Number.POSITIVE_INFINITY;
  /** Run fn once at an absolute scene tick. */
  at(t, fn) {
    this.timeline.push({ t: Math.max(Math.round(t), this.tick), fn });
    return this;
  }
  /** Run fn once `delay` ticks from now. */
  after(delay, fn) {
    return this.at(this.tick + Math.max(0, Math.round(delay)), fn);
  }
  /** Run fn every `every` ticks while from <= tick < to.  fn receives ticks elapsed since `from`. */
  every(every, fn, from = 0, to = Number.POSITIVE_INFINITY) {
    this.loops.push({ from: Math.round(from), to: Math.round(to), every: Math.max(1, Math.round(every)), fn });
    return this;
  }
  /** Run fn each tick in [from, to) with progress 0..1. */
  span(from, to, fn) {
    const a = Math.round(from), b = Math.max(a + 1, Math.round(to));
    return this.every(1, (e) => fn(Math.min(1, e / (b - a - 1 || 1)), e), a, b);
  }
  /** Spawn a spell entity that is removed automatically when the scene ends. */
  spawn(typeId, loc, opts = {}) {
    const id = typeId.includes(":") ? typeId : `${NS}:${typeId}`;
    if (this.ended || Scenes.actorCount() >= CONFIG.limits.maxActors) return new Actor(void 0, id);
    let e;
    try {
      e = this.dim.spawnEntity(id, loc, opts.yaw !== void 0 ? { initialRotation: opts.yaw } : void 0);
    } catch (err) {
      warnOnce(`spawn.${id}`, `cannot spawn ${id}: ${err}`);
    }
    const a = new Actor(e, id);
    if (e) {
      this.actors.add(a);
      try {
        e.addTag("grimoire_scene");
      } catch {
      }
      if (opts.kind !== void 0) a.kind(opts.kind);
      if (opts.size !== void 0) a.size(opts.size);
      if (opts.skin !== void 0) a.skin(opts.skin);
      if (opts.state !== void 0) a.state(opts.state);
      if (opts.yaw !== void 0) a.face(opts.yaw);
    }
    return a;
  }
  /** Remove one actor now. */
  despawn(a) {
    a.remove();
    this.actors.delete(a);
  }
  /** Keep an actor glued to a moving entity; the actor is removed when the target is gone. */
  follow(a, target, dy = 0, until = Number.POSITIVE_INFINITY) {
    return this.every(1, () => {
      if (!a.valid) return;
      if (!target.isValid) {
        this.despawn(a);
        return;
      }
      const l = target.location;
      a.move({ x: l.x, y: l.y + dy, z: l.z });
    }, this.tick, until);
  }
  onEnd(fn) {
    this.endHooks.push(fn);
    return this;
  }
  /** Schedule the scene to finish (and clean up) at an absolute tick. */
  endAt(t) {
    this.endTick = Math.round(t);
    return this;
  }
  get casterOk() {
    return this.caster.isValid && this.caster.dimension.id === this.dimId;
  }
  /** Finish now: runs end hooks, removes every actor. Safe to call repeatedly. */
  end() {
    if (this.ended) return;
    this.ended = true;
    for (const h of this.endHooks) {
      try {
        h();
      } catch (e) {
        console.warn(`[grimoire] ${this.spellId} end hook: ${e}`);
      }
    }
    for (const a of this.actors) a.remove();
    this.actors.clear();
    this.timeline.length = 0;
    this.loops.length = 0;
    Scenes.active.delete(this);
  }
  /** @internal advance one tick */
  step() {
    if (this.ended) return;
    if (!this.casterOk || this.tick >= this.endTick) {
      this.end();
      return;
    }
    try {
      for (const l of this.loops) {
        if (this.tick >= l.from && this.tick < l.to && (this.tick - l.from) % l.every === 0) l.fn(this.tick - l.from);
        if (this.ended) return;
      }
      if (this.timeline.length) {
        const due = this.timeline.filter((e) => e.t <= this.tick);
        if (due.length) {
          this.timeline = this.timeline.filter((e) => e.t > this.tick);
          due.sort((a, b) => a.t - b.t);
          for (const e of due) {
            e.fn();
            if (this.ended) return;
          }
        }
      }
      this.loops = this.loops.filter((l) => this.tick < l.to);
    } catch (e) {
      console.warn(`[grimoire] ${this.spellId} failed at tick ${this.tick}: ${e} ${e?.stack ?? ""}`);
      this.end();
      return;
    }
    this.tick++;
  }
};
var Scenes = {
  active: /* @__PURE__ */ new Set(),
  start(spellId, caster) {
    const s = new Scene(spellId, caster);
    this.active.add(s);
    return s;
  },
  actorCount() {
    let n = 0;
    for (const s of this.active) n += s.actors.size;
    return n;
  },
  tickAll() {
    for (const s of [...this.active]) s.step();
  },
  endFor(player) {
    for (const s of [...this.active]) if (s.caster.id === player.id) s.end();
  },
  endAll() {
    for (const s of [...this.active]) s.end();
  },
  /** Remove spell entities left behind by a previous script session. */
  sweepOrphans() {
    for (const id of ["overworld", "nether", "the_end"]) {
      try {
        for (const e of world.getDimension(id).getEntities({ families: ["grimoire_construct"] })) {
          try {
            e.remove();
          } catch {
          }
        }
      } catch {
      }
    }
  }
};

// src/lib/vec.ts
var add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
var mul = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
var len = (a) => Math.hypot(a.x, a.y, a.z);
function norm(a) {
  const l = len(a);
  return l < 1e-6 ? { x: 0, y: 0, z: 1 } : { x: a.x / l, y: a.y / l, z: a.z / l };
}
var flat = (a) => ({ x: a.x, y: 0, z: a.z });
function yawOf(d) {
  return Math.atan2(-d.x, d.z) * 180 / Math.PI;
}

// src/lib/targeting.ts
function isAlive(e) {
  if (!e || !e.isValid) return false;
  try {
    const h = e.getComponent("minecraft:health");
    return h === void 0 || h.currentValue > 0;
  } catch {
    return false;
  }
}
function isHostile(e, caster) {
  if (!isAlive(e) || e.id === caster.id) return false;
  try {
    if (e.matches({ families: ["grimoire_construct"] })) return false;
    if (e.typeId === "minecraft:player") return CONFIG.targeting.pvp;
    if (e.hasTag(CONFIG.targeting.testTag)) return true;
    for (const f of CONFIG.targeting.hostileFamilies) if (e.matches({ families: [f] })) return true;
  } catch {
  }
  return false;
}
function groundBelow(dim, loc, maxDrop = 40) {
  try {
    const hit = dim.getBlockFromRay(
      { x: loc.x, y: loc.y + 1.5, z: loc.z },
      { x: 0, y: -1, z: 0 },
      { maxDistance: maxDrop, includePassableBlocks: false, includeLiquidBlocks: true }
    );
    if (hit) return { x: loc.x, y: hit.block.location.y + 1, z: loc.z };
  } catch {
  }
  return { x: loc.x, y: loc.y, z: loc.z };
}
function takeAim(caster, range = CONFIG.targeting.aimRange) {
  const dir = caster.getViewDirection();
  const head = caster.getHeadLocation();
  const dim = caster.dimension;
  let point;
  let entity;
  try {
    for (const h of caster.getEntitiesFromViewDirection({ maxDistance: range, excludeFamilies: ["grimoire_construct"] })) {
      if (isHostile(h.entity, caster)) {
        entity = h.entity;
        point = { ...h.entity.location };
        break;
      }
    }
  } catch {
  }
  if (!point) {
    try {
      const b = caster.getBlockFromViewDirection({ maxDistance: range, includePassableBlocks: false });
      if (b) point = { x: b.block.location.x + b.faceLocation.x, y: b.block.location.y + b.faceLocation.y, z: b.block.location.z + b.faceLocation.z };
    } catch {
    }
  }
  if (!point) point = add(head, mul(dir, range * 0.55));
  const forward = norm(flat(dir));
  return { point, ground: groundBelow(dim, point), entity, dir, forward, yaw: yawOf(forward), from: { ...caster.location } };
}

// src/core/registry.ts
var GRIMOIRES = {
  divine_word: { id: "divine_word", item: "grimoire:divine_word", name: "Codex of the First Word", short: "Divine Word", color: "\xA76" },
  dream_nightmare: { id: "dream_nightmare", item: "grimoire:dream_nightmare", name: "The Unawakened Codex", short: "Dream & Nightmare", color: "\xA7d" },
  elemental_dragon: { id: "elemental_dragon", item: "grimoire:elemental_dragon", name: "Codex of the Four Primordial Dragons", short: "Elemental Dragon", color: "\xA7a" }
};
var GRIMOIRE_BY_ITEM = Object.fromEntries(Object.values(GRIMOIRES).map((g) => [g.item, g]));
var GRIMOIRE_ORDER = ["divine_word", "dream_nightmare", "elemental_dragon"];
var SPELL_META = [
  { id: "dw01", grimoire: "divine_word", index: 0, cooldown: 15, tier: "signature", name: "Seraphic Litany: The Sixfold Sanctus", short: "Seraphic Litany" },
  { id: "dw02", grimoire: "divine_word", index: 1, cooldown: 28, tier: "signature", name: "Cherubic Testament: The Four Living Witnesses", short: "Cherubic Testament" },
  { id: "dw03", grimoire: "divine_word", index: 2, cooldown: 35, tier: "signature", name: "Ophanim: The Unblinking Judgment", short: "Ophanim" },
  { id: "dw04", grimoire: "divine_word", index: 3, cooldown: 45, tier: "signature", name: "Divine Edict: Let There Be Sanctuary", short: "Let There Be Sanctuary" },
  { id: "dw05", grimoire: "divine_word", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Threefold Heavenly Throne", short: "Threefold Heavenly Throne" },
  { id: "dw06", grimoire: "divine_word", index: 5, cooldown: 360, tier: "extra", name: "The Word Before Creation", short: "Word Before Creation" },
  { id: "dn01", grimoire: "dream_nightmare", index: 0, cooldown: 16, tier: "signature", name: "Reverie Procession: Parade of the Sleeping Moon", short: "Reverie Procession" },
  { id: "dn02", grimoire: "dream_nightmare", index: 1, cooldown: 24, tier: "signature", name: "Nightmare Intrusion: The Guest Behind the Door", short: "Nightmare Intrusion" },
  { id: "dn03", grimoire: "dream_nightmare", index: 2, cooldown: 38, tier: "signature", name: "House of Shifting Sleep", short: "House of Shifting Sleep" },
  { id: "dn04", grimoire: "dream_nightmare", index: 3, cooldown: 46, tier: "signature", name: "Lullaby and Scream", short: "Lullaby and Scream" },
  { id: "dn05", grimoire: "dream_nightmare", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The City That Sleeps Above the World", short: "City That Sleeps" },
  { id: "dn06", grimoire: "dream_nightmare", index: 5, cooldown: 360, tier: "extra", name: "The Dreamer Who Never Wakes", short: "Dreamer Who Never Wakes" },
  { id: "ed01", grimoire: "elemental_dragon", index: 0, cooldown: 28, tier: "signature", name: "Genesis Colossus: The Walking Continent", short: "Genesis Colossus" },
  { id: "ed02", grimoire: "elemental_dragon", index: 1, cooldown: 24, tier: "signature", name: "Thermal Tyrant: Furnace of the Carnotaur", short: "Thermal Tyrant" },
  { id: "ed03", grimoire: "elemental_dragon", index: 2, cooldown: 32, tier: "signature", name: "Abyssal Cryotitan: The Frozen Tidal Crown", short: "Abyssal Cryotitan" },
  { id: "ed04", grimoire: "elemental_dragon", index: 3, cooldown: 20, tier: "signature", name: "Aether Raptor: Symphony of the Four Wings", short: "Aether Raptor" },
  { id: "ed05", grimoire: "elemental_dragon", index: 4, cooldown: 180, tier: "imperial", name: "Imperial Edict: The Chronicle of Buried Kingdoms", short: "Chronicle of Buried Kingdoms" },
  { id: "ed06", grimoire: "elemental_dragon", index: 5, cooldown: 360, tier: "extra", name: "The World Before Names", short: "World Before Names" }
];
var META_BY_ID = Object.fromEntries(SPELL_META.map((m) => [m.id, m]));
function metaFor(grimoire, index) {
  const m = SPELL_META.find((s) => s.grimoire === grimoire && s.index === index);
  if (!m) throw new Error(`no spell ${grimoire}#${index}`);
  return m;
}
var SPELLS = /* @__PURE__ */ new Map();
function defineSpell(id, cast) {
  const meta = META_BY_ID[id];
  if (!meta) throw new Error(`unknown spell id ${id}`);
  return { ...meta, cast };
}
function registerSpell(def) {
  SPELLS.set(def.id, def);
}
function getSpell(id) {
  return SPELLS.get(id);
}

// src/core/state.ts
var SEL = "grim:sel";
var CD = "grim:cd";
var cache = /* @__PURE__ */ new Map();
function load(p) {
  let c = cache.get(p.id);
  if (c) return c;
  c = { sel: [0, 0, 0], cd: {} };
  try {
    const s = p.getDynamicProperty(SEL);
    if (typeof s === "string") {
      const parts = s.split(",").map((x) => Number(x));
      for (let i = 0; i < 3; i++) if (Number.isInteger(parts[i]) && parts[i] >= 0 && parts[i] < 6) c.sel[i] = parts[i];
    }
    const d = p.getDynamicProperty(CD);
    if (typeof d === "string") {
      const obj = JSON.parse(d);
      const now = Date.now();
      for (const [k2, v] of Object.entries(obj)) if (typeof v === "number" && v > now) c.cd[k2] = v;
    }
  } catch {
  }
  cache.set(p.id, c);
  return c;
}
function saveCd(p, c) {
  const now = Date.now();
  for (const k2 of Object.keys(c.cd)) if (c.cd[k2] <= now) delete c.cd[k2];
  try {
    p.setDynamicProperty(CD, JSON.stringify(c.cd));
  } catch {
  }
}
function getSelection(p, g) {
  return load(p).sel[GRIMOIRE_ORDER.indexOf(g)];
}
function setSelection(p, g, index) {
  const c = load(p);
  c.sel[GRIMOIRE_ORDER.indexOf(g)] = (index % 6 + 6) % 6;
  try {
    p.setDynamicProperty(SEL, c.sel.join(","));
  } catch {
  }
}
function cooldownLeft(p, spellId) {
  const until = load(p).cd[spellId];
  if (!until) return 0;
  return Math.max(0, (until - Date.now()) / 1e3);
}
function startCooldown(p, spellId, seconds) {
  const c = load(p);
  c.cd[spellId] = Date.now() + seconds * 1e3;
  saveCd(p, c);
}
function clearCooldowns(p) {
  const c = load(p);
  c.cd = {};
  saveCd(p, c);
}
function forget(playerId) {
  cache.delete(playerId);
}

// src/core/hud.ts
var pad2 = (n) => n < 10 ? `0${n}` : `${n}`;
function fmt(sec) {
  const s = Math.ceil(sec);
  return s >= 60 ? `${Math.floor(s / 60)}:${pad2(s % 60)}` : `${s}s`;
}
function drawHud(p, g, index, note2) {
  const spells = SPELL_META.filter((m) => m.grimoire === g.id);
  const cur = spells[index];
  const left = cooldownLeft(p, cur.id);
  const status = note2 ?? (left > 0 ? `\xA7c${fmt(left)}` : "\xA7aREADY");
  const tierMark = cur.tier === "imperial" ? "\xA76*" : cur.tier === "extra" ? "\xA7d**" : "";
  let pips = "";
  for (const s of spells) {
    const c = cooldownLeft(p, s.id) > 0 ? "\xA7c" : "\xA7a";
    pips += s.index === index ? `\xA7f[${c}${s.index + 1}\xA7f] ` : `${c}${s.index + 1} `;
  }
  try {
    p.onScreenDisplay.setActionBar(`${g.color}${g.short} \xA78| \xA7f${pad2(index + 1)} \xA7e${cur.short}${tierMark} \xA78| ${status}
${pips.trimEnd()}`);
  } catch {
  }
}

// src/core/presentation.ts
var NOOP = { tick() {
}, release() {
}, cancel() {
} };
var presenter = { select() {
}, prepStart: () => NOOP, deny() {
} };
function setPresenter(p) {
  presenter = p;
}
function present() {
  return presenter;
}

// src/core/input.ts
var states = /* @__PURE__ */ new Map();
function st(p) {
  let s = states.get(p.id);
  if (!s) {
    s = { wasSneaking: p.isSneaking, rearmAt: 0, session: 0, lastHud: -999, hudDirty: true, lastStartTick: -999 };
    states.set(p.id, s);
  }
  return s;
}
function heldGrimoire(p) {
  try {
    const it = p.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);
    return it ? GRIMOIRE_BY_ITEM[it.typeId] : void 0;
  } catch {
    return void 0;
  }
}
function note(s, text, ticks = 30) {
  s.note = { text, until: system.currentTick + ticks };
  s.hudDirty = true;
}
function cancel(s, why, quiet = false) {
  const prep = s.prep;
  if (!prep) return;
  s.prep = void 0;
  s.rearmAt = system.currentTick + CONFIG.input.rearmTicks;
  try {
    prep.handle.cancel();
  } catch (e) {
    console.warn(`[grimoire] cancel fx: ${e}`);
  }
  if (!quiet) note(s, `\xA77${why}`);
}
function begin(p, g, mode) {
  const s = st(p);
  const now = system.currentTick;
  if (s.prep) {
    if (s.prep.mode === "heartbeat" && mode === "charge") {
      s.prep.mode = "charge";
      return;
    }
    cancel(s, "Interrupted", true);
  }
  if (now < s.rearmAt) return;
  if (p.isSneaking) {
    note(s, "\xA77Stand up to cast");
    return;
  }
  const meta = metaFor(g.id, getSelection(p, g.id));
  if (cooldownLeft(p, meta.id) > 0) {
    s.hudDirty = true;
    try {
      present().deny(p, g);
    } catch {
    }
    return;
  }
  if (!getSpell(meta.id)) {
    note(s, "\xA7cSpell unavailable");
    return;
  }
  let handle;
  try {
    handle = present().prepStart(p, g, meta);
  } catch (e) {
    console.warn(`[grimoire] prep fx: ${e}`);
    handle = { tick() {
    }, release() {
    }, cancel() {
    } };
  }
  s.prep = { g, meta, startTick: now, slot: p.selectedSlotIndex, session: ++s.session, handle, mode, lastBeat: now };
  note(s, "\xA7bPreparing... \xA77release to cast", 60);
}
function release(p) {
  const s = st(p);
  const prep = s.prep;
  if (!prep) return;
  const now = system.currentTick;
  const held = now - prep.startTick;
  if (heldGrimoire(p)?.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) {
    cancel(s, "Cancelled");
    return;
  }
  if (p.isSneaking) {
    cancel(s, "Cancelled (crouching)");
    return;
  }
  if (held < CONFIG.input.minHoldTicks) {
    cancel(s, "Hold Use longer, then release");
    return;
  }
  if (cooldownLeft(p, prep.meta.id) > 0) {
    cancel(s, "On cooldown");
    return;
  }
  s.prep = void 0;
  s.rearmAt = now + CONFIG.input.rearmTicks;
  const spell = getSpell(prep.meta.id);
  if (!spell) {
    try {
      prep.handle.cancel();
    } catch {
    }
    return;
  }
  const scene = Scenes.start(spell.id, p);
  let ok = false;
  try {
    ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: held });
  } catch (e) {
    console.warn(`[grimoire] ${spell.id} cast failed: ${e} ${e?.stack ?? ""}`);
    ok = false;
  }
  if (ok === false) {
    scene.end();
    try {
      prep.handle.cancel();
    } catch {
    }
    note(s, "\xA77No valid target");
    return;
  }
  startCooldown(p, spell.id, spell.cooldown);
  try {
    prep.handle.release();
  } catch (e) {
    console.warn(`[grimoire] release fx: ${e}`);
  }
  s.note = void 0;
  s.hudDirty = true;
}
function tickPlayer(p, now) {
  const s = st(p);
  const g = heldGrimoire(p);
  if (g?.id !== s.held?.id) {
    s.held = g;
    s.hudDirty = true;
  }
  const sneaking = p.isSneaking;
  const entered = sneaking && !s.wasSneaking;
  s.wasSneaking = sneaking;
  if (s.prep) {
    const prep = s.prep;
    if (sneaking) cancel(s, "Cancelled (crouching)");
    else if (!g || g.id !== prep.g.id || p.selectedSlotIndex !== prep.slot) cancel(s, "Cancelled");
    else if (prep.stopTick !== void 0 && now > prep.stopTick) cancel(s, "Cancelled");
    else if (prep.mode === "heartbeat" && now - prep.lastBeat > CONFIG.input.heartbeatGapTicks) release(p);
    else {
      try {
        prep.handle.tick(now - prep.startTick);
      } catch (e) {
        console.warn(`[grimoire] prep tick: ${e}`);
      }
    }
  } else if (entered && g) {
    const next = (getSelection(p, g.id) + 1) % 6;
    setSelection(p, g.id, next);
    s.note = void 0;
    s.hudDirty = true;
    try {
      present().select(p, g, metaFor(g.id, next));
    } catch (e) {
      console.warn(`[grimoire] select fx: ${e}`);
    }
  }
  if (s.pendingBeat !== void 0 && now > s.pendingBeat) {
    const beat = s.pendingBeat;
    s.pendingBeat = void 0;
    if (CONFIG.input.heartbeatFallback && s.lastStartTick < beat && g) {
      if (s.prep?.mode === "heartbeat") s.prep.lastBeat = beat;
      else if (!s.prep) begin(p, g, "heartbeat");
    }
  }
  if (g) {
    if (s.note && now > s.note.until) {
      s.note = void 0;
      s.hudDirty = true;
    }
    if (s.hudDirty || now - s.lastHud >= CONFIG.hud.refreshTicks) {
      s.lastHud = now;
      s.hudDirty = false;
      drawHud(p, g, getSelection(p, g.id), s.note?.text);
    }
  }
}
function isGrimoire(item) {
  return item ? GRIMOIRE_BY_ITEM[item.typeId] : void 0;
}
function installInput() {
  world2.afterEvents.itemStartUse.subscribe((ev) => {
    const g = isGrimoire(ev.itemStack);
    if (!g) return;
    st(ev.source).lastStartTick = system.currentTick;
    begin(ev.source, g, "charge");
  });
  world2.afterEvents.itemReleaseUse.subscribe((ev) => {
    const s = states.get(ev.source.id);
    if (s?.prep?.mode === "charge") release(ev.source);
  });
  const stop = (p) => {
    const s = states.get(p.id);
    if (s?.prep && s.prep.mode === "charge" && s.prep.stopTick === void 0) s.prep.stopTick = system.currentTick;
  };
  world2.afterEvents.itemStopUse.subscribe((ev) => stop(ev.source));
  world2.afterEvents.itemCompleteUse.subscribe((ev) => stop(ev.source));
  world2.afterEvents.itemUse.subscribe((ev) => {
    if (!CONFIG.input.heartbeatFallback || !isGrimoire(ev.itemStack)) return;
    st(ev.source).pendingBeat = system.currentTick;
  });
  world2.afterEvents.entityDie.subscribe((ev) => {
    if (ev.deadEntity.typeId !== "minecraft:player") return;
    const s = states.get(ev.deadEntity.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.deadEntity);
  });
  world2.afterEvents.playerDimensionChange.subscribe((ev) => {
    const s = states.get(ev.player.id);
    if (s) cancel(s, "Cancelled", true);
    Scenes.endFor(ev.player);
  });
  world2.beforeEvents.playerLeave.subscribe((ev) => {
    const id = ev.player.id;
    const s = states.get(id);
    system.run(() => {
      if (s) cancel(s, "Cancelled", true);
      states.delete(id);
      forget(id);
      for (const sc of [...Scenes.active]) if (!sc.caster.isValid) sc.end();
    });
  });
}
function tickInput() {
  const now = system.currentTick;
  for (const p of world2.getAllPlayers()) {
    try {
      if (p.isValid) tickPlayer(p, now);
    } catch (e) {
      console.warn(`[grimoire] input tick: ${e}`);
    }
  }
}

// src/lib/fx.ts
import { MolangVariableMap, system as system2 } from "@minecraft/server";
var budgetTick = -1;
var budget = 0;
function take(n = 1) {
  if (system2.currentTick !== budgetTick) {
    budgetTick = system2.currentTick;
    budget = CONFIG.limits.maxParticlesPerTick;
  }
  if (budget < n) return false;
  budget -= n;
  return true;
}
function particle(dim, id, loc, vars) {
  if (!take()) return;
  try {
    dim.spawnParticle(id.includes(":") ? id : `${NS}:${id}`, loc, vars);
  } catch {
  }
}
function sound(dim, id, loc, volume = 1, pitch = 1) {
  try {
    dim.playSound(id.includes(".") ? id : `${NS}.${id}`, loc, { volume, pitch });
  } catch {
  }
}

// src/core/books.ts
function installBooks() {
  setPresenter({
    select(p, g, _m) {
      sound(p.dimension, `${g.id}.select`, p.location, 0.8);
    },
    prepStart(p, g, _m) {
      sound(p.dimension, `${g.id}.charge`, p.location, 0.8);
      return {
        tick(t) {
          if (t % 4 === 0 && p.isValid) particle(p.dimension, `${g.id}_charge`, { x: p.location.x, y: p.location.y + 1.6, z: p.location.z });
        },
        release() {
          if (p.isValid) sound(p.dimension, `${g.id}.release`, p.location, 1);
        },
        cancel() {
        }
      };
    },
    deny(p, g) {
      sound(p.dimension, `${g.id}.deny`, p.location, 0.6);
    }
  });
}

// src/lib/combat.ts
import { EntityDamageCause, system as system3, world as world3 } from "@minecraft/server";
var wards = /* @__PURE__ */ new Set();
var wardHooked = false;
function installWards() {
  if (wardHooked) return;
  wardHooked = true;
  world3.beforeEvents.entityHurt.subscribe((ev) => {
    if (wards.size === 0) return;
    for (const w of wards) {
      if (w.scene.ended || w.broken) {
        continue;
      }
      let ok = false;
      try {
        ok = w.protects(ev.hurtEntity);
      } catch {
        ok = false;
      }
      if (!ok) continue;
      let absorbed = ev.damage * (1 - w.factor);
      if (w.pool !== void 0) {
        absorbed = Math.min(absorbed, w.pool);
        w.pool -= absorbed;
      }
      if (absorbed <= 0) continue;
      ev.damage = Math.max(0, ev.damage - absorbed);
      if (ev.damage < 0.05) ev.cancel = true;
      const attacker = ev.damageSource.damagingEntity;
      const victim = ev.hurtEntity;
      const breakNow = w.pool !== void 0 && w.pool <= 1e-4 && !w.broken;
      if (breakNow) w.broken = true;
      system3.run(() => {
        if (w.scene.ended) return;
        try {
          w.onAbsorb?.(absorbed, attacker, victim);
        } catch (e) {
          console.warn(`[grimoire] ward: ${e}`);
        }
        if (breakNow) {
          try {
            w.onBreak?.();
          } catch (e) {
            console.warn(`[grimoire] ward break: ${e}`);
          }
        }
      });
    }
  });
}

// src/lib/tempblocks.ts
import { world as world4 } from "@minecraft/server";
var live = /* @__PURE__ */ new Map();
var dirty = false;
var KEY = "grim:tb";
var CHUNK = 3e4;
var k = (d, x, y, z) => `${d}|${x}|${y}|${z}`;
function saveLedger() {
  dirty = false;
  const parts = [];
  for (const e of live.values()) parts.push(`${e.d},${e.x},${e.y},${e.z},${e.t}`);
  const s = parts.join(";");
  let i = 0;
  for (let off = 0; off < s.length || i === 0; off += CHUNK, i++) world4.setDynamicProperty(`${KEY}${i}`, s.slice(off, off + CHUNK));
  for (; i < 8; i++) if (world4.getDynamicProperty(`${KEY}${i}`) !== void 0) world4.setDynamicProperty(`${KEY}${i}`, void 0);
}
function flushLedger() {
  if (dirty) {
    try {
      saveLedger();
    } catch (e) {
      console.warn(`[grimoire] ledger: ${e}`);
    }
  }
}
function restoreLedger() {
  let s = "";
  for (let i = 0; i < 8; i++) {
    const p = world4.getDynamicProperty(`${KEY}${i}`);
    if (typeof p === "string") s += p;
  }
  if (!s) return;
  let pending = 0;
  for (const rec of s.split(";")) {
    const [d, xs, ys, zs, t] = rec.split(",");
    if (!d || t === void 0) continue;
    const e = { d, x: Number(xs), y: Number(ys), z: Number(zs), t };
    if (!clear(e)) {
      live.set(k(e.d, e.x, e.y, e.z), e);
      pending++;
    }
  }
  dirty = true;
  if (pending) console.warn(`[grimoire] ${pending} temporary blocks are in unloaded chunks; they will be removed when loaded.`);
}
function retryOrphans(owned) {
  for (const [key, e] of [...live]) {
    if (owned(key)) continue;
    if (clear(e)) {
      live.delete(key);
      dirty = true;
    }
  }
}
function clear(e) {
  try {
    const b = world4.getDimension(e.d).getBlock({ x: e.x, y: e.y, z: e.z });
    if (!b) return false;
    if (b.typeId === e.t) b.setType("minecraft:air");
    return true;
  } catch {
    return false;
  }
}
var sets = /* @__PURE__ */ new Set();
function anySetOwns(key) {
  for (const s of sets) if (s.owns(key)) return true;
  return false;
}

// src/spells/dw01_seraphic_litany.ts
var dw01_seraphic_litany_default = defineSpell("dw01", (ctx) => {
  ctx.caster.sendMessage("dw01 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dw02_cherubic_testament.ts
var dw02_cherubic_testament_default = defineSpell("dw02", (ctx) => {
  ctx.caster.sendMessage("dw02 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dw03_ophanim.ts
var dw03_ophanim_default = defineSpell("dw03", (ctx) => {
  ctx.caster.sendMessage("dw03 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dw04_sanctuary.ts
var dw04_sanctuary_default = defineSpell("dw04", (ctx) => {
  ctx.caster.sendMessage("dw04 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dw05_heavenly_throne.ts
var dw05_heavenly_throne_default = defineSpell("dw05", (ctx) => {
  ctx.caster.sendMessage("dw05 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dw06_word_before_creation.ts
var dw06_word_before_creation_default = defineSpell("dw06", (ctx) => {
  ctx.caster.sendMessage("dw06 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn01_reverie_procession.ts
var dn01_reverie_procession_default = defineSpell("dn01", (ctx) => {
  ctx.caster.sendMessage("dn01 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn02_nightmare_intrusion.ts
var dn02_nightmare_intrusion_default = defineSpell("dn02", (ctx) => {
  ctx.caster.sendMessage("dn02 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn03_shifting_house.ts
var dn03_shifting_house_default = defineSpell("dn03", (ctx) => {
  ctx.caster.sendMessage("dn03 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn04_lullaby_and_scream.ts
var dn04_lullaby_and_scream_default = defineSpell("dn04", (ctx) => {
  ctx.caster.sendMessage("dn04 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn05_sleeping_city.ts
var dn05_sleeping_city_default = defineSpell("dn05", (ctx) => {
  ctx.caster.sendMessage("dn05 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/dn06_the_dreamer.ts
var dn06_the_dreamer_default = defineSpell("dn06", (ctx) => {
  ctx.caster.sendMessage("dn06 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed01_genesis_colossus.ts
var ed01_genesis_colossus_default = defineSpell("ed01", (ctx) => {
  ctx.caster.sendMessage("ed01 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed02_thermal_tyrant.ts
var ed02_thermal_tyrant_default = defineSpell("ed02", (ctx) => {
  ctx.caster.sendMessage("ed02 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed03_abyssal_cryotitan.ts
var ed03_abyssal_cryotitan_default = defineSpell("ed03", (ctx) => {
  ctx.caster.sendMessage("ed03 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed04_aether_raptor.ts
var ed04_aether_raptor_default = defineSpell("ed04", (ctx) => {
  ctx.caster.sendMessage("ed04 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed05_buried_kingdoms.ts
var ed05_buried_kingdoms_default = defineSpell("ed05", (ctx) => {
  ctx.caster.sendMessage("ed05 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/ed06_world_before_names.ts
var ed06_world_before_names_default = defineSpell("ed06", (ctx) => {
  ctx.caster.sendMessage("ed06 is not implemented yet");
  ctx.scene.endAt(1);
});

// src/spells/index.ts
function registerAllSpells() {
  for (const s of [dw01_seraphic_litany_default, dw02_cherubic_testament_default, dw03_ophanim_default, dw04_sanctuary_default, dw05_heavenly_throne_default, dw06_word_before_creation_default, dn01_reverie_procession_default, dn02_nightmare_intrusion_default, dn03_shifting_house_default, dn04_lullaby_and_scream_default, dn05_sleeping_city_default, dn06_the_dreamer_default, ed01_genesis_colossus_default, ed02_thermal_tyrant_default, ed03_abyssal_cryotitan_default, ed04_aether_raptor_default, ed05_buried_kingdoms_default, ed06_world_before_names_default]) registerSpell(s);
}

// src/main.ts
registerAllSpells();
function giveBooks(p) {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return;
  for (const g of Object.values(GRIMOIRES)) inv.addItem(new ItemStack2(g.item, 1));
}
function forceCast(p, id) {
  const spell = getSpell(id);
  if (!spell) return `unknown spell '${id}' (use dw01..dw06, dn01..dn06, ed01..ed06)`;
  const scene = Scenes.start(spell.id, p);
  let ok;
  try {
    ok = spell.cast({ caster: p, scene, aim: takeAim(p), heldTicks: 20 });
  } catch (e) {
    scene.end();
    return `error: ${e}`;
  }
  if (ok === false) {
    scene.end();
    return `${id}: no valid target`;
  }
  startCooldown(p, spell.id, spell.cooldown);
  return `cast ${id} (${META_BY_ID[id].name})`;
}
system4.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  reg.registerCommand(
    { name: "grimoire:give", description: "Give yourself the three Grimoires", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player4)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system4.run(() => giveBooks(p));
      return { status: CustomCommandStatus.Success, message: "Three Grimoires added to your inventory" };
    }
  );
  reg.registerCommand(
    { name: "grimoire:reset", description: "Clear all of your Grimoire spell cooldowns", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: true },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player4)) return { status: CustomCommandStatus.Failure, message: "Players only" };
      system4.run(() => clearCooldowns(p));
      return { status: CustomCommandStatus.Success, message: "Grimoire cooldowns cleared" };
    }
  );
  reg.registerCommand(
    { name: "grimoire:cleanup", description: "End every active Grimoire spell and remove its constructs", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
    () => {
      system4.run(() => {
        Scenes.endAll();
        Scenes.sweepOrphans();
      });
      return { status: CustomCommandStatus.Success, message: "Grimoire spells ended" };
    }
  );
});
system4.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity instanceof Player4 ? ev.sourceEntity : void 0;
  const arg = ev.message.trim().toLowerCase();
  switch (ev.id) {
    case "grimoire:give":
      if (p) giveBooks(p);
      break;
    case "grimoire:reset":
      if (p) {
        clearCooldowns(p);
        p.sendMessage("Grimoire cooldowns cleared");
      }
      break;
    case "grimoire:cast":
      if (p) p.sendMessage(`[grimoire] ${forceCast(p, arg)}`);
      break;
    case "grimoire:cleanup":
      Scenes.endAll();
      Scenes.sweepOrphans();
      break;
    case "grimoire:config": {
      const [key, val] = arg.split(/\s+/);
      const on = val === "on" || val === "true" || val === "1";
      if (key === "heartbeat") RUNTIME.input.heartbeatFallback = on;
      else if (key === "pvp") RUNTIME.targeting.pvp = on;
      p?.sendMessage(`[grimoire] ${key} = ${on}`);
      break;
    }
  }
}, { namespaces: ["grimoire"] });
world5.afterEvents.worldLoad.subscribe(() => {
  installWards();
  installInput();
  installBooks();
  restoreLedger();
  Scenes.sweepOrphans();
  let n = 0;
  system4.runInterval(() => {
    tickInput();
    Scenes.tickAll();
    flushLedger();
    if (++n % 100 === 0) retryOrphans(anySetOwns);
  }, 1);
});
