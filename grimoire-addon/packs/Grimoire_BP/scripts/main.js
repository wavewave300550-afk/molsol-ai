// src/main.ts
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  EntityInitializationCause,
  ItemStack as ItemStack2,
  Player as Player12,
  system as system16,
  world as world10
} from "@minecraft/server";

// src/config.ts
import { world } from "@minecraft/server";
var DEFAULT_RULES = {
  pvp: false,
  friendlyFire: false,
  harmPassiveMobs: false,
  temporaryBlocks: true,
  damagePvE: 1,
  damagePvP: 0.5,
  cameraEffects: true
};
var cached;
function rules() {
  if (cached) return cached;
  const r = { ...DEFAULT_RULES };
  try {
    const raw = world.getDynamicProperty("grimoire:rules");
    if (typeof raw === "string") Object.assign(r, JSON.parse(raw));
  } catch {
  }
  cached = r;
  return r;
}
function setRule(key2, value) {
  const r = { ...rules() };
  if (!(key2 in DEFAULT_RULES)) return `Unknown rule '${key2}'. Rules: ${Object.keys(DEFAULT_RULES).join(", ")}`;
  const def = DEFAULT_RULES[key2];
  if (typeof def === "boolean") {
    const v = value.toLowerCase();
    r[key2] = v === "true" || v === "on" || v === "1" || v === "yes";
  } else {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || n > 10) return `Rule '${key2}' needs a number between 0 and 10`;
    r[key2] = n;
  }
  world.setDynamicProperty("grimoire:rules", JSON.stringify(r));
  cached = r;
  return `Rule ${key2} = ${String(r[key2])}`;
}

// src/core/blocks.ts
import { world as world2 } from "@minecraft/server";

// src/core/vec.ts
var v3 = (x, y, z) => ({ x, y, z });
var add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
var sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
var mul = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
var dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
var len = (a) => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
var dist = (a, b) => len(sub(a, b));
var dist2 = (a, b) => {
  const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return dx * dx + dy * dy + dz * dz;
};
var hdist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
var norm = (a) => {
  const l = len(a);
  return l < 1e-9 ? { x: 0, y: 0, z: 1 } : mul(a, 1 / l);
};
var lerp = (a, b, t) => add(a, mul(sub(b, a), t));
var flat = (a) => ({ x: a.x, y: 0, z: a.z });
var flatNorm = (a) => norm(flat(a));
var clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;
var floor3 = (l) => ({ x: Math.floor(l.x), y: Math.floor(l.y), z: Math.floor(l.z) });
var DEG = Math.PI / 180;
function dirFromYawPitch(yaw, pitch) {
  const cp = Math.cos(pitch * DEG);
  return { x: -Math.sin(yaw * DEG) * cp, y: -Math.sin(pitch * DEG), z: Math.cos(yaw * DEG) * cp };
}
function yawPitchOf(d) {
  const n = norm(d);
  const yaw = Math.atan2(-n.x, n.z) / DEG;
  const pitch = -Math.asin(clamp(n.y, -1, 1)) / DEG;
  return { yaw, pitch };
}
function rotY(v, deg) {
  const c = Math.cos(deg * DEG), s = Math.sin(deg * DEG);
  return { x: v.x * c - v.z * s, y: v.y, z: v.x * s + v.z * c };
}
function bezier3(a, c1, c2, b, t) {
  const u = 1 - t;
  return add(add(mul(a, u * u * u), mul(c1, 3 * u * u * t)), add(mul(c2, 3 * u * t * t), mul(b, t * t * t)));
}
function segDist(p, a, b) {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  const t = l2 < 1e-9 ? 0 : clamp(dot(sub(p, a), ab) / l2, 0, 1);
  return { d: dist(p, add(a, mul(ab, t))), t };
}
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = a + 1831565813 >>> 0;
    let t = a;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// src/core/blocks.ts
var TEMP_BLOCK_IDS = [
  "grimoire:pressure_barrier",
  "grimoire:frost_wall",
  "grimoire:blood_thornwall",
  "grimoire:shadow_step_low",
  "grimoire:shadow_step_high"
];
var live = /* @__PURE__ */ new Map();
var key = (dimId, l) => `${dimId}|${Math.floor(l.x)}|${Math.floor(l.y)}|${Math.floor(l.z)}`;
var nextSet = 1;
var TempBlockSet = class {
  constructor(dim) {
    this.dim = dim;
  }
  dim;
  id = `s${nextSet++}`;
  placed = /* @__PURE__ */ new Map();
  get enabled() {
    return rules().temporaryBlocks;
  }
  /** Try to place a temporary block; returns false if the space is not air or unloaded. */
  place(loc, typeId) {
    if (!this.enabled) return false;
    const l = floor3(loc);
    const k = key(this.dim.id, l);
    if (live.has(k)) return false;
    try {
      const b = this.dim.getBlock(l);
      if (!b || !b.isValid || !b.isAir) return false;
      b.setType(typeId);
      live.set(k, this.id);
      this.placed.set(k, l);
      return true;
    } catch {
      return false;
    }
  }
  has(loc) {
    return this.placed.has(key(this.dim.id, floor3(loc)));
  }
  /** Remove one of this set's blocks (only if it is still our block). */
  remove(loc) {
    const l = floor3(loc);
    const k = key(this.dim.id, l);
    if (!this.placed.has(k)) return;
    this.placed.delete(k);
    live.delete(k);
    try {
      const b = this.dim.getBlock(l);
      if (b && b.isValid && TEMP_BLOCK_IDS.includes(b.typeId)) b.setType("minecraft:air");
    } catch {
    }
  }
  clear() {
    for (const l of [...this.placed.values()]) this.remove(l);
  }
  positions() {
    return [...this.placed.values()];
  }
};
function registerBlockComponents(ev) {
  ev.blockComponentRegistry.registerCustomComponent("grimoire:temporary", {
    onTick(e) {
      const b = e.block;
      if (!live.has(key(e.dimension.id, b.location))) {
        try {
          b.setType("minecraft:air");
        } catch {
        }
      }
    }
  });
}
function liveTempBlocks() {
  return live.size;
}

// src/core/casting.ts
import { EntityHealthComponent, system as system14, world as world8 } from "@minecraft/server";

// src/spells/context.ts
import { system as system6 } from "@minecraft/server";

// src/core/fx.ts
import { MolangVariableMap, system as system2, world as world4 } from "@minecraft/server";

// src/core/log.ts
var PREFIX = "[Grimoire]";
function fmt(e) {
  if (e instanceof Error) return `${e.name}: ${e.message}${e.stack ? "\n" + e.stack : ""}`;
  return String(e);
}
var log = {
  /** Debug output only when the debug flag is enabled (kept quiet in normal play). */
  debugEnabled: false,
  debug(...parts) {
    if (this.debugEnabled) console.warn(PREFIX, ...parts.map((p) => typeof p === "string" ? p : JSON.stringify(p)));
  },
  warn(...parts) {
    console.warn(PREFIX, ...parts.map((p) => typeof p === "string" ? p : fmt(p)));
  },
  error(msg, e) {
    console.error(PREFIX, msg, e === void 0 ? "" : fmt(e));
  }
};

// src/core/combat.ts
import {
  EntityDamageCause,
  EntityTameableComponent,
  EntityTypeFamilyComponent,
  system,
  world as world3
} from "@minecraft/server";
var ENEMY_FAMILIES = ["monster", "dragon", "hoglin_adult"];
var PROTECTED_FAMILIES = ["villager", "wandering_trader", "irongolem", "snowgolem", "copper_golem", "allay", "npc", "tripodcamera"];
var IGNORED_FAMILIES = ["inanimate", "projectile", "grimoire_fx", "lightning", "armor_stand"];
var IGNORED_TYPES = /* @__PURE__ */ new Set([
  "minecraft:item",
  "minecraft:xp_orb",
  "minecraft:area_effect_cloud",
  "minecraft:ender_crystal",
  "minecraft:eye_of_ender_signal",
  "minecraft:ominous_item_spawner",
  "minecraft:agent",
  "minecraft:painting",
  "minecraft:leash_knot",
  "minecraft:falling_block",
  "minecraft:tnt"
]);
var FX_FAMILY = "grimoire_fx";
var SUMMON_FAMILY = "grimoire_summon";
var OWNER_PROP = "grimoire:owner";
var aggressors = /* @__PURE__ */ new Map();
var AGGRO_TICKS = 20 * 20;
function noteAggressor(victim, attacker) {
  if (!attacker || attacker.id === victim.id) return;
  const ownerId = victim.typeId === "minecraft:player" ? victim.id : ownerOf(victim);
  if (!ownerId) return;
  let m = aggressors.get(ownerId);
  if (!m) aggressors.set(ownerId, m = /* @__PURE__ */ new Map());
  m.set(attacker.id, system.currentTick + AGGRO_TICKS);
}
function isAggressor(casterId, e) {
  const until = aggressors.get(casterId)?.get(e.id);
  return until !== void 0 && until > system.currentTick;
}
function pruneAggressors() {
  const now = system.currentTick;
  for (const [k, m] of aggressors) {
    for (const [id, until] of m) if (until <= now) m.delete(id);
    if (m.size === 0) aggressors.delete(k);
  }
}
function ownerOf(e) {
  try {
    const o = e.getDynamicProperty(OWNER_PROP);
    return typeof o === "string" ? o : void 0;
  } catch {
    return void 0;
  }
}
function families(e) {
  return e.getComponent(EntityTypeFamilyComponent.componentId);
}
function hasAnyFamily(f, list) {
  if (!f) return false;
  for (const x of list) if (f.hasTypeFamily(x)) return true;
  return false;
}
function teamOf(p) {
  for (const t of p.getTags()) if (t.startsWith("grimoire_team:")) return t;
  return void 0;
}
function relation(caster, e) {
  const casterId = typeof caster === "string" ? caster : caster.id;
  if (!e.isValid) return "ignore";
  if (e.id === casterId) return "self";
  if (IGNORED_TYPES.has(e.typeId)) return "ignore";
  const fam = families(e);
  if (hasAnyFamily(fam, IGNORED_FAMILIES)) return "ignore";
  const r = rules();
  if (e.typeId === "minecraft:player") {
    if (!r.pvp) return "ally";
    if (!r.friendlyFire && typeof caster !== "string") {
      const t = teamOf(caster);
      if (t && e.hasTag(t)) return "ally";
    }
    return "enemy";
  }
  if (fam?.hasTypeFamily(SUMMON_FAMILY)) {
    const o = ownerOf(e);
    if (o === casterId) return "ally";
    return r.pvp ? "enemy" : "ally";
  }
  if (isAggressor(casterId, e)) return "enemy";
  if (hasAnyFamily(fam, ENEMY_FAMILIES)) return "enemy";
  if (hasAnyFamily(fam, PROTECTED_FAMILIES)) return "neutral";
  const tame = e.getComponent(EntityTameableComponent.componentId);
  if (tame?.isTamed) return tame.tamedToPlayerId === casterId ? "ally" : "neutral";
  if (e.nameTag && e.nameTag.length > 0) return "neutral";
  if (!e.getComponent("minecraft:health")) return "ignore";
  return r.harmPassiveMobs ? "enemy" : "neutral";
}
var isEnemy = (caster, e) => relation(caster, e) === "enemy";
var isAllyOrSelf = (caster, e) => {
  const rel = relation(caster, e);
  return rel === "self" || rel === "ally";
};
function livingNear(dim, center, radius) {
  try {
    return dim.getEntities({ location: center, maxDistance: radius, excludeFamilies: IGNORED_FAMILIES, excludeTypes: [...IGNORED_TYPES] });
  } catch {
    return [];
  }
}
function enemiesNear(caster, dim, center, radius) {
  return livingNear(dim, center, radius).filter((e) => isEnemy(caster, e));
}
function enemiesAlong(caster, dim, a, b, radius) {
  const mid = mul({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }, 0.5);
  const reach = dist(a, b) / 2 + radius + 2;
  return enemiesNear(caster, dim, mid, reach).filter((e) => {
    const c = bodyCenter(e);
    return segDist(c, a, b).d <= radius + bodyRadius(e);
  });
}
function bodyCenter(e) {
  const l = e.location;
  return { x: l.x, y: l.y + bodyHeight(e) * 0.5, z: l.z };
}
var SIZE_CACHE = /* @__PURE__ */ new Map();
function bodyHeight(e) {
  return entitySize(e)[1];
}
function bodyRadius(e) {
  return entitySize(e)[0] * 0.5;
}
function entitySize(e) {
  const c = SIZE_CACHE.get(e.typeId);
  if (c) return c;
  let h = 1.8;
  try {
    h = Math.max(0.3, (e.getHeadLocation().y - e.location.y) * 1.12);
  } catch {
  }
  const w = Math.min(4, Math.max(0.4, h * 0.45));
  const r = [w, h];
  SIZE_CACHE.set(e.typeId, r);
  return r;
}
var lastApplied = /* @__PURE__ */ new Map();
var pending = /* @__PURE__ */ new Map();
var HURT_COOLDOWN = 10;
var damageInFlight = /* @__PURE__ */ new Map();
function scaleFor(target) {
  const r = rules();
  return target.typeId === "minecraft:player" ? r.damagePvP : r.damagePvE;
}
var vulnerable = /* @__PURE__ */ new Map();
function markVulnerable(target, ownerId, mult, ticks) {
  vulnerable.set(target.id, { ownerId, mult, until: system.currentTick + ticks });
}
function clearVulnerable(targetId, ownerId) {
  if (vulnerable.get(targetId)?.ownerId === ownerId) vulnerable.delete(targetId);
}
function clearVulnerableOf(ownerId) {
  for (const [k, v] of vulnerable) if (v.ownerId === ownerId) vulnerable.delete(k);
}
function vulnerabilityMult(target, attackerId) {
  const v = vulnerable.get(target.id);
  if (!v) return 1;
  if (v.until <= system.currentTick) {
    vulnerable.delete(target.id);
    return 1;
  }
  if (!attackerId) return 1;
  if (attackerId === v.ownerId) return v.mult;
  const attacker = world3.getEntity(attackerId);
  return attacker?.isValid && isAllyOrSelf(v.ownerId, attacker) ? v.mult : 1;
}
function vulnerabilityBonus(victim, damage, attacker) {
  if (!attacker || damageInFlight.has(victim.id) || damage <= 0) return;
  const v = vulnerable.get(victim.id);
  if (!v || v.until <= system.currentTick) return;
  const mult = vulnerabilityMult(victim, attacker.id);
  if (mult <= 1) return;
  const extra = damage * (mult - 1);
  const owner = v.ownerId;
  system.runTimeout(() => hit(owner, victim, extra, { kind: "transfer" }), HURT_COOLDOWN + 1);
}
function hit(caster, target, amount, opts = {}) {
  if (!target.isValid || amount <= 0) return;
  const casterId = typeof caster === "string" ? caster : caster.id;
  const kind = opts.kind ?? "spell";
  if (kind === "spell") amount *= vulnerabilityMult(target, casterId);
  const now = system.currentTick;
  const last = lastApplied.get(target.id) ?? -999;
  const p = pending.get(target.id);
  if (p) {
    p.amount += amount;
    return;
  }
  if (opts.immediate || now - last >= HURT_COOLDOWN) {
    apply(target, casterId, amount, kind);
  } else {
    pending.set(target.id, { target, casterId, amount, kind, due: last + HURT_COOLDOWN });
  }
}
function causeFor(kind) {
  return kind === "reflect" ? EntityDamageCause.thorns : EntityDamageCause.magic;
}
function apply(target, casterId, amount, kind) {
  if (!target.isValid) return;
  const scaled = amount * scaleFor(target);
  if (scaled <= 0) return;
  const caster = world3.getEntity(casterId);
  lastApplied.set(target.id, system.currentTick);
  damageInFlight.set(target.id, kind);
  try {
    target.applyDamage(scaled, { cause: causeFor(kind), damagingEntity: caster?.isValid ? caster : void 0 });
  } catch (e) {
    log.debug("applyDamage failed", String(e));
  } finally {
    damageInFlight.delete(target.id);
  }
}
function flushDamage(tick) {
  for (const [id, p] of pending) {
    if (tick >= p.due) {
      pending.delete(id);
      apply(p.target, p.casterId, p.amount, p.kind);
    }
  }
  if (tick % 200 === 0) {
    for (const [id, t] of lastApplied) if (tick - t > 100) lastApplied.delete(id);
  }
}
function push(e, dir, horizontal, vertical) {
  if (!e.isValid) return;
  const d = flatNorm(dir);
  try {
    e.applyKnockback({ x: d.x * horizontal, z: d.z * horizontal }, vertical);
  } catch {
  }
}
function pullToward(e, point, strength) {
  const d = sub(point, e.location);
  const l = len(d);
  if (l < 0.6) return;
  const n = norm(d);
  push(e, n, Math.min(strength, l * 0.25), Math.max(-0.1, Math.min(0.25, n.y * strength)));
}
function effect(e, id, ticks, amplifier = 0, particles = false) {
  if (!e.isValid) return;
  try {
    e.addEffect(id, ticks, { amplifier, showParticles: particles });
  } catch {
  }
}
function pin(e, anchor, tolerance = 0.35) {
  if (!e.isValid) return;
  const l = e.location;
  const dx = l.x - anchor.x, dz = l.z - anchor.z;
  if (dx * dx + dz * dz > tolerance * tolerance || l.y > anchor.y + 0.8) {
    try {
      e.teleport({ x: anchor.x, y: Math.min(l.y, anchor.y + 0.1), z: anchor.z }, { keepVelocity: false });
    } catch {
    }
  }
}
function release(e) {
  if (!e.isValid) return;
  for (const id of ["slowness", "mining_fatigue", "weakness"]) {
    try {
      e.removeEffect(id);
    } catch {
    }
  }
}

// src/core/fx.ts
var PHASE_DISSOLVE = 15;
var SESSION_PROP = "grimoire:session";
var SESSION = `${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;
var registry = /* @__PURE__ */ new Map();
var Fx = class {
  constructor(entity, type, ownerId, loc) {
    this.entity = entity;
    this.type = type;
    this.ownerId = ownerId;
    this.lastPos = loc;
  }
  entity;
  type;
  ownerId;
  props = /* @__PURE__ */ new Map();
  lastPos;
  dying = false;
  get ok() {
    return !this.dying && this.entity.isValid;
  }
  get location() {
    return this.lastPos;
  }
  set(name, value) {
    if (!this.entity.isValid) return this;
    if (this.props.get(name) === value) return this;
    this.props.set(name, value);
    try {
      this.entity.setProperty(`grimoire:${name}`, value);
    } catch (e) {
      log.debug(`setProperty ${name} on ${this.type}`, String(e));
    }
    return this;
  }
  phase(n) {
    return this.set("phase", Math.max(0, Math.min(15, Math.round(n))));
  }
  getPhase() {
    return this.props.get("phase") ?? 0;
  }
  yaw(deg) {
    let d = deg;
    while (d > 360) d -= 360;
    while (d < -360) d += 360;
    return this.set("yaw", Math.round(d * 10) / 10);
  }
  pitch(deg) {
    return this.set("pitch", Math.round(Math.max(-90, Math.min(90, deg)) * 10) / 10);
  }
  size(s) {
    return this.set("size", Math.round(Math.max(0, Math.min(64, s)) * 100) / 100);
  }
  length(l) {
    return this.set("len", Math.round(Math.max(0, Math.min(128, l)) * 100) / 100);
  }
  variant(v) {
    return this.set("variant", Math.max(0, Math.min(15, Math.round(v))));
  }
  pulse() {
    return this.set("aux", ((this.props.get("aux") ?? 0) + 1) % 250);
  }
  aux(n) {
    return this.set("aux", Math.max(0, Math.min(255, Math.round(n))));
  }
  aim(dir) {
    const { yaw, pitch } = yawPitchOf(dir);
    return this.yaw(yaw).pitch(pitch);
  }
  /** Move the construct (no-op for sub-millimetre changes). */
  move(loc) {
    if (!this.entity.isValid) return this;
    if (dist2(loc, this.lastPos) < 1e-6) return this;
    this.lastPos = loc;
    try {
      this.entity.teleport(loc, { keepVelocity: false, checkForBlocks: false });
    } catch {
    }
    return this;
  }
  /** Follow an entity with an offset; predicts one tick of velocity to hide server lag. */
  follow(target, offset = { x: 0, y: 0, z: 0 }, predict = 1) {
    if (!target.isValid) return this;
    let p = add(target.location, offset);
    if (predict > 0) {
      try {
        const v = target.getVelocity();
        p = { x: p.x + v.x * predict, y: p.y + v.y * predict * 0.5, z: p.z + v.z * predict };
      } catch {
      }
    }
    return this.move(p);
  }
  /** Play the dissolve phase, then remove after `ticks`. Safe to call repeatedly. */
  dissolve(ticks = 12) {
    if (this.dying) return;
    this.dying = true;
    if (!this.entity.isValid) {
      registry.delete(this.entity.id);
      return;
    }
    this.props.delete("phase");
    try {
      this.entity.setProperty("grimoire:phase", PHASE_DISSOLVE);
    } catch {
    }
    const ent = this.entity;
    system2.runTimeout(() => removeEntity(ent), Math.max(1, ticks));
  }
  remove() {
    this.dying = true;
    removeEntity(this.entity);
  }
};
function removeEntity(e) {
  registry.delete(e.id);
  try {
    if (e.isValid) e.remove();
  } catch {
  }
}
function spawnFx(owner, dim, type, loc, init = {}) {
  const ownerId = typeof owner === "string" ? owner : owner.id;
  let e;
  try {
    e = dim.spawnEntity(type, loc, { initialRotation: 0, initialPersistence: false });
  } catch (err) {
    log.debug(`spawn ${type} failed`, String(err));
    return void 0;
  }
  const fx = new Fx(e, type, ownerId, loc);
  try {
    e.setDynamicProperty(OWNER_PROP, ownerId);
    e.setDynamicProperty(SESSION_PROP, SESSION);
  } catch {
  }
  if (init.dir) fx.aim(init.dir);
  if (init.yaw !== void 0) fx.yaw(init.yaw);
  if (init.pitch !== void 0) fx.pitch(init.pitch);
  if (init.size !== void 0) fx.size(init.size);
  if (init.len !== void 0) fx.length(init.len);
  if (init.variant !== void 0) fx.variant(init.variant);
  if (init.aux !== void 0) fx.aux(init.aux);
  fx.phase(init.phase ?? 1);
  registry.set(e.id, fx);
  return fx;
}
function fxCount() {
  return registry.size;
}
function removeAllFxOf(ownerId) {
  for (const fx of [...registry.values()]) if (fx.ownerId === ownerId) fx.dissolve(6);
}
function isStaleConstruct(e) {
  if (registry.has(e.id)) return false;
  try {
    return e.getDynamicProperty(SESSION_PROP) !== SESSION;
  } catch {
    return true;
  }
}
var COLORS = {
  orange: { r: 1, g: 0.55, b: 0.12 },
  gold: { r: 1, g: 0.78, b: 0.3 },
  copper: { r: 0.78, g: 0.42, b: 0.22 },
  white: { r: 1, g: 0.97, b: 0.9 },
  sapphire: { r: 0.12, g: 0.32, b: 0.85 },
  ice: { r: 0.62, g: 0.86, b: 1 },
  cyan: { r: 0.35, g: 0.95, b: 1 },
  silver: { r: 0.82, g: 0.87, b: 0.95 },
  crimson: { r: 0.78, g: 0.04, b: 0.12 },
  scarlet: { r: 1, g: 0.14, b: 0.12 },
  burgundy: { r: 0.42, g: 0.02, b: 0.08 },
  bloodglow: { r: 1, g: 0.22, b: 0.25 },
  redgold: { r: 1, g: 0.5, b: 0.25 },
  // Plasma: deep violet / electric purple / ultraviolet / magenta / indigo / white-hot
  violet: { r: 0.55, g: 0.18, b: 1 },
  magenta: { r: 1, g: 0.25, b: 0.85 },
  ultraviolet: { r: 0.42, g: 0.3, b: 1 },
  indigo: { r: 0.3, g: 0.22, b: 0.95 },
  whitehot: { r: 1, g: 0.92, b: 1 },
  // Darkness: deep forest green / dark emerald / muted jade (never neon)
  darkgreen: { r: 0.04, g: 0.2, b: 0.1 },
  emerald: { r: 0.08, g: 0.38, b: 0.2 },
  jade: { r: 0.42, g: 0.7, b: 0.52 },
  // Prism Light: pearl / champagne gold / the seven spectral colours
  pearl: { r: 1, g: 0.97, b: 0.93 },
  champagne: { r: 0.96, g: 0.84, b: 0.58 },
  sp_red: { r: 1, g: 0.16, b: 0.16 },
  sp_orange: { r: 1, g: 0.55, b: 0.1 },
  sp_yellow: { r: 1, g: 0.93, b: 0.2 },
  sp_green: { r: 0.25, g: 1, b: 0.35 },
  sp_blue: { r: 0.2, g: 0.5, b: 1 },
  sp_indigo: { r: 0.36, g: 0.25, b: 1 },
  sp_violet: { r: 0.72, g: 0.22, b: 1 }
};
function particle(dim, id, at, vars = {}, onlyFor) {
  const m = new MolangVariableMap();
  const c = vars.color ?? COLORS.white;
  m.setColorRGBA("variable.color", { red: c.r, green: c.g, blue: c.b, alpha: 1 });
  const c2 = vars.color2 ?? c;
  m.setColorRGBA("variable.color2", { red: c2.r, green: c2.g, blue: c2.b, alpha: 1 });
  m.setFloat("variable.size", vars.size ?? 1);
  m.setFloat("variable.radius", vars.radius ?? 1);
  m.setFloat("variable.count", vars.count ?? 1);
  m.setFloat("variable.life", vars.life ?? 1);
  const d = vars.dir ?? { x: 0, y: 1, z: 0 };
  m.setSpeedAndDirection("variable.dir", vars.speed ?? 1, d);
  try {
    if (onlyFor) onlyFor.spawnParticle(id, at, m);
    else dim.spawnParticle(id, at, m);
  } catch {
  }
}
function sound(dim, id, at, volume = 1, pitch = 1) {
  try {
    dim.playSound(id, at, { volume, pitch });
  } catch {
  }
}
function shake(dim, at, radius, intensity, seconds) {
  if (!rules().cameraEffects) return;
  const players = dim.getPlayers({ location: at, maxDistance: radius });
  for (const p of players) {
    const d = Math.sqrt(dist2(p.location, at));
    const k = Math.max(0.05, Math.min(1, intensity * (1 - d / (radius * 1.2))));
    try {
      p.runCommand(`camerashake add @s ${k.toFixed(2)} ${seconds.toFixed(2)} positional`);
    } catch {
    }
  }
}
function flash(dim, at, radius, color, hold = 0.1) {
  if (!rules().cameraEffects) return;
  for (const p of dim.getPlayers({ location: at, maxDistance: radius })) {
    try {
      p.camera.fade({
        fadeColor: { red: color.r, green: color.g, blue: color.b },
        fadeTime: { fadeInTime: 0.05, holdTime: hold, fadeOutTime: 0.45 }
      });
    } catch {
    }
  }
}

// src/core/defense.ts
import { EntityDamageCause as EntityDamageCause2, system as system3, world as world5 } from "@minecraft/server";
var wards = [];
var nextWardId = 1;
var PHYSICAL_CAUSES = /* @__PURE__ */ new Set([
  EntityDamageCause2.entityAttack,
  EntityDamageCause2.projectile,
  EntityDamageCause2.entityExplosion,
  EntityDamageCause2.blockExplosion,
  EntityDamageCause2.ramAttack,
  EntityDamageCause2.charging,
  EntityDamageCause2.maceSmash,
  EntityDamageCause2.sonicBoom,
  EntityDamageCause2.fireworks,
  EntityDamageCause2.contact
]);
function addWard(w) {
  const ward = { ...w, id: nextWardId++, alive: true };
  wards.push(ward);
  wards.sort((a, b) => b.priority - a.priority);
  return ward;
}
function removeWard(w) {
  if (!w) return;
  w.alive = false;
  const i = wards.indexOf(w);
  if (i >= 0) wards.splice(i, 1);
}
function removeWardsOf(ownerId) {
  for (const w of [...wards]) if (w.ownerId === ownerId) removeWard(w);
}
var fallImmune = /* @__PURE__ */ new Map();
function grantFallImmunity(entityId, ticks) {
  fallImmune.set(entityId, Math.max(fallImmune.get(entityId) ?? 0, system3.currentTick + ticks));
}
function onBeforeHurt(ev) {
  const hurt = ev.hurtEntity;
  const cause = ev.damageSource.cause;
  if (cause === EntityDamageCause2.fall || cause === EntityDamageCause2.flyIntoWall) {
    const until = fallImmune.get(hurt.id);
    if (until !== void 0 && until >= system3.currentTick) {
      ev.cancel = true;
      return;
    }
  }
  if (wards.length === 0) return;
  let damage = ev.damage;
  const info = {
    hurt,
    damage,
    cause,
    attacker: ev.damageSource.damagingEntity,
    projectile: ev.damageSource.damagingProjectile
  };
  const reactions = [];
  for (const w of wards) {
    if (!w.alive || damage <= 0) continue;
    let protects = false;
    try {
      protects = w.protects(hurt);
    } catch {
      protects = false;
    }
    if (!protects) continue;
    info.damage = damage;
    let remaining = damage;
    try {
      remaining = Math.max(0, w.absorb(info));
    } catch (e) {
      log.error(`ward ${w.label} absorb failed`, e);
      continue;
    }
    if (remaining < damage) {
      reactions.push([w, damage - remaining]);
      damage = remaining;
    }
  }
  if (reactions.length === 0) return;
  if (damage <= 1e-3) ev.cancel = true;
  else ev.damage = damage;
  const snapshot = { ...info, damage: ev.damage };
  system3.run(() => {
    for (const [w, absorbed] of reactions) {
      if (!w.react) continue;
      try {
        w.react(snapshot, absorbed);
      } catch (e) {
        log.error(`ward ${w.label} reaction failed`, e);
      }
    }
  });
}
function initDefense() {
  world5.beforeEvents.entityHurt.subscribe(onBeforeHurt);
  system3.runInterval(() => {
    const now = system3.currentTick;
    for (const [id, t] of fallImmune) if (t < now) fallImmune.delete(id);
  }, 100);
}

// src/core/status.ts
import { system as system4 } from "@minecraft/server";
var binds = /* @__PURE__ */ new Map();
var nextBind = 1;
function bind(ownerId, dim, target, ticks, o = {}) {
  if (!target.isValid) return void 0;
  for (const b2 of binds.values()) {
    if (b2.target.id === target.id && b2.ownerId === ownerId && !b2.ended) {
      b2.until = Math.max(b2.until, system4.currentTick + ticks);
      return b2;
    }
  }
  const b = {
    id: nextBind++,
    ownerId,
    target,
    until: system4.currentTick + ticks,
    anchor: o.pin === false ? void 0 : { ...target.location },
    shellOffset: o.shellOffset ?? { x: 0, y: 0, z: 0 },
    slowAmp: o.slowAmp ?? 7,
    pull: o.pull,
    pullSpeed: o.pullSpeed ?? 0.12,
    ended: false
  };
  if (o.shell) b.shell = spawnFx(ownerId, dim, o.shell, add(target.location, b.shellOffset), { phase: 1, ...o.shellInit ?? {} });
  effect(target, "slowness", Math.min(ticks, 20 * 30), b.slowAmp);
  binds.set(b.id, b);
  return b;
}
function endBind(b, shatter = true) {
  if (!b || b.ended) return;
  b.ended = true;
  binds.delete(b.id);
  if (b.target.isValid) release(b.target);
  if (b.shell) {
    if (shatter) b.shell.phase(3);
    const s = b.shell;
    system4.runTimeout(() => s.dissolve(10), shatter ? 6 : 1);
  }
}
function endBindsOf(ownerId) {
  for (const b of [...binds.values()]) if (b.ownerId === ownerId) endBind(b, false);
}
function tickBinds(tick) {
  for (const b of [...binds.values()]) {
    if (!b.target.isValid || tick >= b.until) {
      endBind(b, b.target.isValid);
      continue;
    }
    if (b.pull && b.anchor) {
      const dx = b.pull.x - b.anchor.x, dz = b.pull.z - b.anchor.z;
      const d = Math.hypot(dx, dz);
      if (d > 0.4) {
        const k = Math.min(b.pullSpeed, d) / d;
        b.anchor = { x: b.anchor.x + dx * k, y: b.anchor.y, z: b.anchor.z + dz * k };
      }
    }
    if (b.anchor) pin(b.target, b.anchor, 0.25);
    if (tick % 20 === 0) effect(b.target, "slowness", 40, b.slowAmp);
    b.shell?.follow(b.target, b.shellOffset, 0);
  }
}

// src/core/tasks.ts
import { system as system5 } from "@minecraft/server";
var entries = /* @__PURE__ */ new Map();
var nextId = 1;
function start(gen, label, ownerId, maxTicks = 20 * 240) {
  const id = nextId++;
  const entry = {
    gen,
    wake: system5.currentTick,
    ends: [],
    started: system5.currentTick,
    maxTicks,
    handle: {
      id,
      label,
      ownerId,
      alive: true,
      cancel: (reason = "cancelled") => finish(entry, reason, true),
      onEnd: (fn) => {
        if (!entry.handle.alive) fn("already-ended");
        else entry.ends.push(fn);
      }
    }
  };
  entries.set(id, entry);
  step(entry, system5.currentTick);
  return entry.handle;
}
function finish(entry, reason, interrupt) {
  if (!entry.handle.alive) return;
  entry.handle.alive = false;
  entries.delete(entry.handle.id);
  if (interrupt) {
    try {
      entry.gen.return(void 0);
    } catch (e) {
      log.error(`routine ${entry.handle.label} failed while cancelling`, e);
    }
  }
  for (const fn of entry.ends) {
    try {
      fn(reason);
    } catch (e) {
      log.error(`cleanup of ${entry.handle.label} failed`, e);
    }
  }
}
function step(entry, tick) {
  if (!entry.handle.alive || tick < entry.wake) return;
  if (tick - entry.started > entry.maxTicks) {
    finish(entry, "timeout", true);
    return;
  }
  try {
    const r = entry.gen.next();
    if (r.done) {
      finish(entry, "done", false);
      return;
    }
    const w = typeof r.value === "number" && r.value > 0 ? Math.floor(r.value) : 1;
    entry.wake = tick + w;
  } catch (e) {
    log.error(`routine ${entry.handle.label} crashed`, e);
    finish(entry, "error", false);
  }
}
function tickRoutines(tick) {
  for (const entry of [...entries.values()]) step(entry, tick);
}
function cancelOwned(ownerId, reason) {
  for (const entry of [...entries.values()]) if (entry.handle.ownerId === ownerId) finish(entry, reason, true);
}
function activeRoutines() {
  return [...entries.values()].map((e) => e.handle);
}

// src/spells/context.ts
var SpellScope = class {
  constructor(player, spell, dim) {
    this.player = player;
    this.spell = spell;
    this.dim = dim;
  }
  player;
  spell;
  dim;
  fxs = [];
  cleanups = [];
  get ownerId() {
    return this.player.id;
  }
  /** Spawn a construct owned by this spell (auto-dissolved at cleanup). */
  fx(type, loc, init = {}) {
    const f = spawnFx(this.player.id, this.dim, type, loc, init);
    if (f) this.fxs.push(f);
    return f;
  }
  particle(id, at, vars = {}) {
    particle(this.dim, id, at, vars);
  }
  sound(id, at = this.player.location, volume = 1, pitch = 1) {
    sound(this.dim, id, at, volume, pitch);
  }
  shake(at, radius, intensity, seconds) {
    shake(this.dim, at, radius, intensity, seconds);
  }
  flash(at, radius, color, hold = 0.1) {
    flash(this.dim, at, radius, color, hold);
  }
  onCleanup(fn) {
    this.cleanups.push(fn);
  }
  cleanup(dissolveTicks = 12) {
    for (const f of this.fxs) f.dissolve(dissolveTicks);
    this.fxs.length = 0;
    const fns = this.cleanups.splice(0);
    for (const fn of fns) {
      try {
        fn();
      } catch {
      }
    }
  }
};
var Prep = class extends SpellScope {
  /** Optional value handed to the cast (e.g. adopted formation constructs). */
  handoff;
  constructor(player, spell) {
    super(player, spell, player.dimension);
  }
  /** Keep these constructs alive for the cast (it becomes responsible for them). */
  adopt() {
    const list = [...this.fxs];
    this.fxs.length = 0;
    return list;
  }
};
var Cast = class extends SpellScope {
  constructor(player, spell, power, empowered) {
    super(player, spell, player.dimension);
    this.power = power;
    this.empowered = empowered;
    this.origin = player.getHeadLocation();
    this.feet = player.location;
    this.dir = player.getViewDirection();
    const r = player.getRotation();
    this.yaw = r.y;
    this.pitch = r.x;
    this.dimensionId = player.dimension.id;
  }
  power;
  empowered;
  origin;
  feet;
  dir;
  yaw;
  pitch;
  startTick = system6.currentTick;
  dimensionId;
  handle;
  wards = [];
  tempBlocks;
  /** Constructs handed over from the preparation phase (formation already visible). */
  adopted = [];
  subs = [];
  /** Run a parallel routine owned by this cast (cancelled with the spell). */
  run(gen, label = "sub") {
    const h = start(gen, `${this.spell.code}:${label}`, this.player.id, 20 * 120);
    this.subs.push(h);
    return h;
  }
  /** Wait until all parallel routines finished (use inside the main routine). */
  *join(maxTicks = 20 * 30) {
    for (let i = 0; i < maxTicks && this.subs.some((h) => h.alive); i++) yield 1;
  }
  /** Area multiplier when empowered. */
  get area() {
    return this.empowered ? 1.25 : 1;
  }
  /** True while the caster is online, alive-ish and in the dimension the spell was cast in. */
  get ok() {
    try {
      return this.player.isValid && this.player.dimension.id === this.dimensionId;
    } catch {
      return false;
    }
  }
  p(name) {
    const v = this.spell.params[name];
    if (v === void 0) throw new Error(`${this.spell.code}: missing param ${name}`);
    return v;
  }
  /** Current eye position & look direction (live, for channelled spells). */
  eye() {
    return this.player.isValid ? this.player.getHeadLocation() : this.origin;
  }
  look() {
    return this.player.isValid ? this.player.getViewDirection() : this.dir;
  }
  enemies(center, radius) {
    return enemiesNear(this.player, this.dim, center, radius * this.area);
  }
  along(a, b, radius) {
    return enemiesAlong(this.player, this.dim, a, b, radius);
  }
  isEnemy(e) {
    return isEnemy(this.player, e);
  }
  /** Spell damage (scaled by empowerment). */
  hit(target, amount, opts = {}) {
    hit(this.player, target, amount * this.power, opts);
  }
  /** Damage + falloff by distance from a center. */
  blast(center, radius, amount, onEach, minK = 0.35) {
    const list = this.enemies(center, radius);
    for (const e of list) {
      const k = Math.max(minK, 1 - dist(bodyCenter(e), center) / (radius * this.area + 0.5));
      this.hit(e, amount * k);
      onEach?.(e, k);
    }
    return list;
  }
  /** Raycast aim with soft aim-assist (helps touch players hit moving targets). */
  aim(maxDistance, assistDeg = 7) {
    const eye = this.eye();
    const dir = this.look();
    let blockDist = maxDistance;
    let blockHit = false;
    try {
      const b = this.player.getBlockFromViewDirection({ maxDistance, includeLiquidBlocks: false, includePassableBlocks: false });
      if (b) {
        const fl = add(b.block.location, b.faceLocation);
        blockDist = Math.min(maxDistance, dist(eye, fl));
        blockHit = true;
      }
    } catch {
    }
    try {
      const hits = this.player.getEntitiesFromViewDirection({ maxDistance: blockDist });
      for (const h of hits) {
        if (this.isEnemy(h.entity)) {
          return { point: bodyCenter(h.entity), entity: h.entity, block: false, distance: h.distance };
        }
      }
    } catch {
    }
    const cos = Math.cos(assistDeg * Math.PI / 180);
    let best;
    let bestScore = -1;
    for (const e of this.enemies(add(eye, mul(dir, blockDist * 0.5)), blockDist * 0.5 + 3)) {
      const c = bodyCenter(e);
      const to = sub(c, eye);
      const d = dist(c, eye);
      if (d > blockDist + 1) continue;
      const k = dot(norm(to), dir);
      if (k > cos && k > bestScore) {
        bestScore = k;
        best = e;
      }
    }
    if (best) {
      const c = bodyCenter(best);
      return { point: c, entity: best, block: false, distance: dist(c, eye) };
    }
    return { point: add(eye, mul(dir, blockDist)), block: blockHit, distance: blockDist };
  }
  /** Top surface below a point (searches down `maxDown` blocks, falls back to the point). */
  ground(p, maxDown = 24) {
    return this.groundHit(p, maxDown) ?? { x: p.x, y: Math.floor(p.y), z: p.z };
  }
  /** Top surface below a point, or undefined when there is none within `maxDown` blocks. */
  groundHit(p, maxDown = 24) {
    try {
      const hit2 = this.dim.getBlockFromRay(add(p, v3(0, 0.5, 0)), v3(0, -1, 0), {
        maxDistance: maxDown + 0.5,
        includeLiquidBlocks: true,
        includePassableBlocks: false
      });
      if (hit2) return { x: p.x, y: hit2.block.location.y + 1, z: p.z };
    } catch {
    }
    return void 0;
  }
  /** Aimed ground point (where area spells land). Aiming at the sky (or past the range over a drop) lands the
   *  spell on the ground ahead of the caster instead of hanging it in the air. */
  aimGround(maxDistance) {
    const a = this.aim(maxDistance);
    if (a.entity) return { point: this.ground(a.entity.location, 30), target: a.entity };
    if (a.block) {
      const g = this.groundHit(add(a.point, v3(0, 0.3, 0)), 30);
      if (g) return { point: g };
    }
    const d = this.player.getViewDirection();
    const f = flatNorm(d);
    const horiz = Math.hypot(d.x, d.z) * maxDistance;
    const reach = d.y > 0 ? Math.max(3, maxDistance * 0.6) : Math.max(3, Math.min(maxDistance, horiz));
    const feet = this.player.location;
    for (let r = reach; r >= 2; r -= 2) {
      const g = this.groundHit(add(feet, add(mul(f, r), v3(0, 3, 0))), 30);
      if (g) return { point: g };
    }
    return { point: { x: feet.x + f.x * 3, y: Math.floor(feet.y), z: feet.z + f.z * 3 } };
  }
  binds = [];
  /** Bind/freeze a target; the bind is released when this spell ends (whatever the reason). */
  bind(target, ticks, o = {}) {
    const b = bind(this.player.id, this.dim, target, ticks, o);
    if (b) this.binds.push(b);
    return b;
  }
  ward(def) {
    const w = addWard({ ...def, ownerId: this.player.id });
    this.wards.push(w);
    return w;
  }
  blocks() {
    if (!this.tempBlocks) this.tempBlocks = new TempBlockSet(this.dim);
    return this.tempBlocks;
  }
  cleanup(dissolveTicks = 12) {
    for (const h of this.subs) if (h.alive) h.cancel("spell ended");
    this.subs.length = 0;
    for (const b of this.binds) endBind(b, true);
    this.binds.length = 0;
    for (const w of this.wards) removeWard(w);
    this.wards.length = 0;
    this.tempBlocks?.clear();
    for (const f of this.adopted) f.dissolve(dissolveTicks);
    this.adopted.length = 0;
    super.cleanup(dissolveTicks);
  }
};

// src/spells/blood/spells.ts
import { EntityDamageCause as EntityDamageCause4, EntityTameableComponent as EntityTameableComponent2, system as system7 } from "@minecraft/server";

// src/spells/types.ts
var SCHOOLS = ["pressure", "ice", "blood", "plasma", "darkness", "prism_light"];
var CODE_PREFIX = { pressure: "P", ice: "I", blood: "B", plasma: "PL", darkness: "D", prism_light: "PR" };
var GRIMOIRE_ITEMS = {
  pressure: "grimoire:pressure",
  ice: "grimoire:ice",
  blood: "grimoire:blood",
  plasma: "grimoire:plasma",
  darkness: "grimoire:darkness",
  prism_light: "grimoire:prism_light"
};
var SCHOOL_NAMES = {
  pressure: "Pressure Grimoire",
  ice: "Ice Grimoire",
  blood: "Blood Grimoire",
  plasma: "Plasma Grimoire",
  darkness: "Darkness Grimoire",
  prism_light: "Prism Light Grimoire"
};
var SCHOOL_COLOR = { pressure: "\xA76", ice: "\xA7b", blood: "\xA7c", plasma: "\xA7d", darkness: "\xA72", prism_light: "\xA7f" };
function schoolOfItem(typeId) {
  if (!typeId) return void 0;
  for (const s of SCHOOLS) if (GRIMOIRE_ITEMS[s] === typeId) return s;
  return void 0;
}
var Fizzle = class extends Error {
  constructor(reason) {
    super(reason);
    this.reason = reason;
  }
  reason;
};

// src/spells/hooks.ts
import { world as world6 } from "@minecraft/server";
var listeners = /* @__PURE__ */ new Set();
var attackListeners = /* @__PURE__ */ new Set();
function onAttack(l) {
  attackListeners.add(l);
  return () => attackListeners.delete(l);
}
function onHurt(l) {
  listeners.add(l);
  return () => listeners.delete(l);
}
function dispatch(e) {
  const src = e.damageSource.damagingEntity;
  if (src && attackListeners.size > 0) {
    for (const l of [...attackListeners]) {
      if (l.attackerId !== src.id) continue;
      try {
        l.fn(e.hurtEntity, e.damage, e.damageSource.cause);
      } catch (err) {
        log.error("attack listener failed", err);
      }
    }
  }
  if (listeners.size === 0) return;
  const id = e.hurtEntity.id;
  for (const l of [...listeners]) {
    if (!l.watch.has(id)) continue;
    try {
      l.fn(e.hurtEntity, e.damage, e.damageSource.cause, e.damageSource.damagingEntity);
    } catch (err) {
      log.error("hurt listener failed", err);
    }
  }
}
function initHooks() {
  world6.afterEvents.entityHurt.subscribe(dispatch);
}

// src/spells/kit.ts
import { Player as Player4 } from "@minecraft/server";
var KB_GAIN = 2.56;
var SCHOOL_COL = {
  pressure: { a: COLORS.orange, b: COLORS.gold },
  ice: { a: COLORS.ice, b: COLORS.white },
  blood: { a: COLORS.crimson, b: COLORS.scarlet },
  plasma: { a: COLORS.violet, b: COLORS.magenta },
  darkness: { a: COLORS.darkgreen, b: COLORS.jade },
  prism_light: { a: COLORS.pearl, b: COLORS.champagne }
};
function drive(e, vel) {
  if (!e.isValid) return;
  try {
    e.applyKnockback({ x: vel.x * KB_GAIN, z: vel.z * KB_GAIN }, vel.y);
  } catch {
  }
}
function freeDistance(dim, from, dir, maxDist) {
  try {
    const hit2 = dim.getBlockFromRay(from, norm(dir), { maxDistance: maxDist, includeLiquidBlocks: false, includePassableBlocks: false });
    if (hit2) return Math.max(0, dist(from, add(hit2.block.location, hit2.faceLocation)));
  } catch {
  }
  return maxDist;
}
function isPassable(dim, l) {
  try {
    const b = dim.getBlock({ x: Math.floor(l.x), y: Math.floor(l.y), z: Math.floor(l.z) });
    if (!b) return false;
    return b.isAir || b.isLiquid || b.typeId.includes("grass") && !b.typeId.includes("block") || b.typeId === "minecraft:snow_layer";
  } catch {
    return false;
  }
}
function safeSpot(dim, p) {
  const base = { x: Math.floor(p.x) + 0.5, y: Math.floor(p.y), z: Math.floor(p.z) + 0.5 };
  for (const dy of [0, 1, -1, 2, -2, 3]) {
    const f = { x: base.x, y: base.y + dy, z: base.z };
    if (!isPassable(dim, f) || !isPassable(dim, add(f, v3(0, 1, 0)))) continue;
    for (let k = 1; k <= 4; k++) {
      if (!isPassable(dim, add(f, v3(0, -k, 0)))) return { x: f.x, y: f.y - k + 1, z: f.z };
    }
  }
  return void 0;
}
function teleportDestination(c, maxDist) {
  const eye = c.eye();
  const dir = c.look();
  const free = freeDistance(c.dim, eye, dir, maxDist);
  for (let d = Math.max(1.5, free - 0.8); d >= 1.5; d -= 0.75) {
    const probe = add(eye, mul(dir, d));
    const s = safeSpot(c.dim, { x: probe.x, y: probe.y - 1.2, z: probe.z });
    if (s && dist(s, c.player.location) > 1.5) return s;
  }
  return void 0;
}
function nearestEnemies(c, center, radius, max) {
  return c.enemies(center, radius).map((e) => [e, dist(bodyCenter(e), center)]).sort((a, b) => a[1] - b[1]).slice(0, max).map(([e]) => e);
}
function shock(c, center, radius, damage, o = {}) {
  const col = o.color ?? SCHOOL_COL[c.spell.school].a;
  const hits = c.blast(center, radius, damage, (e, k) => {
    const d = sub(e.location, center);
    const dir = len(flatNorm(d)) > 0 ? flatNorm(d) : c.dir;
    push(e, o.inward ? mul(dir, -1) : dir, (o.knock ?? 1.2) * (0.5 + k), (o.up ?? 0.35) * (0.6 + k * 0.6));
  }, o.minK);
  c.particle(o.particle ?? "grimoire:ring_h", add(center, v3(0, 0.15, 0)), { color: col, color2: o.color2 ?? SCHOOL_COL[c.spell.school].b, radius: radius * 2.2 * c.area, life: o.ringLife ?? 1 });
  c.particle("grimoire:dust_ring", center, { color: { r: 0.75, g: 0.7, b: 0.62 }, radius: Math.min(4, radius * 0.5), size: 1.2, count: 1 });
  if (o.sound) c.sound(o.sound, center, 1.2, o.pitch ?? 1);
  if (o.shake) c.shake(center, radius * 3, o.shake, 0.5);
  return hits;
}
function* fly(c, o) {
  let pos = o.from;
  let dir = norm(o.dir);
  let travelled = 0;
  const hitIds = /* @__PURE__ */ new Set();
  let hits = 0;
  let step2 = 0;
  while (travelled < o.range) {
    if (o.homing && o.homing.isValid) {
      const want = norm(sub(bodyCenter(o.homing), pos));
      dir = norm(lerp(dir, want, o.homingRate ?? 0.25));
    }
    const stepLen = Math.min(o.speed, o.range - travelled);
    let next = add(pos, mul(dir, stepLen));
    if (o.arc) next = add(next, mul(o.arc, Math.sin(travelled / o.range * Math.PI) * stepLen * 0.2));
    let blocked = false;
    if (o.stopOnBlock !== false) {
      const free = freeDistance(c.dim, pos, sub(next, pos), dist(pos, next) + 0.01);
      if (free < dist(pos, next) - 0.05) {
        next = add(pos, mul(norm(sub(next, pos)), free));
        blocked = true;
      }
    }
    for (const e of c.along(pos, next, o.radius)) {
      if (hitIds.has(e.id)) continue;
      hitIds.add(e.id);
      hits++;
      o.onHit(e, bodyCenter(e));
      if (hits >= o.pierce) {
        o.fx?.move(next);
        o.onEnd?.(bodyCenter(e), false);
        return;
      }
    }
    o.fx?.move(next).aim(sub(next, pos));
    if (o.trail && step2 % (o.trailEvery ?? 1) === 0) c.particle(o.trail, next, { color: o.trailColor, color2: o.trailColor2, size: 1, count: 1 });
    o.onTick?.(next, step2);
    travelled += dist(pos, next);
    pos = next;
    step2++;
    if (blocked) {
      o.onEnd?.(pos, true);
      return;
    }
    yield 1;
  }
  o.onEnd?.(pos, false);
}
function local(p, base, right, up, fwd, yawDeg) {
  const yaw = (yawDeg ?? (p instanceof Player4 ? p.getRotation().y : p.yaw)) * Math.PI / 180;
  const f = { x: -Math.sin(yaw), z: Math.cos(yaw) };
  const r = { x: -f.z, z: f.x };
  return { x: base.x + f.x * fwd + r.x * right, y: base.y + up, z: base.z + f.z * fwd + r.z * right };
}

// src/spells/blood/spells.ts
var CR = COLORS.crimson;
var SC = COLORS.scarlet;
var BG = COLORS.bloodglow;
var BU = COLORS.burgundy;
var RG = COLORS.redgold;
function* stilettoRain(c) {
  const p = c.player;
  const formation = c.fx("grimoire:fx_b_stilettos", p.location, { yaw: p.getRotation().y, phase: 1 });
  c.particle("grimoire:droplet_burst", add(p.location, v3(0, 1.6, 0)), { color: CR, color2: SC, radius: 1.5, count: 2 });
  c.sound("grimoire.blood.form", p.location, 1, 1.1);
  for (let t = 0; t < 12; t++) {
    formation?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
  const aim = c.aim(c.p("range"));
  const volleys = c.p("volleys");
  for (let w = 0; w < volleys; w++) {
    formation?.phase(3 + w);
    const foes = nearestEnemies(c, aim.entity ? bodyCenter(aim.entity) : aim.point, 10, 6);
    for (let k = 0; k < 3; k++) {
      const yaw = p.getRotation().y;
      const from = add(p.location, add(rotY(v3((k - 1) * 0.9, 0, 0.4), yaw), v3(0, 1.6 + w * 0.3, 0)));
      const tgt = foes.length ? foes[(w * 3 + k) % foes.length] : void 0;
      const goal = tgt ? bodyCenter(tgt) : add(aim.point, v3((k - 1) * 1.5, 0, (w - 1) * 1.5));
      const dir = norm(sub(goal, from));
      const cl = c.fx("grimoire:fx_b_stiletto", from, { dir, phase: 1 });
      c.run(fly(c, {
        fx: cl,
        from,
        dir,
        speed: 1.9,
        range: c.p("range") + 4,
        radius: 0.7,
        pierce: 1,
        homing: tgt,
        homingRate: 0.3,
        trail: "grimoire:trail",
        trailColor: CR,
        trailColor2: SC,
        onHit: (e) => {
          c.hit(e, c.p("damage"));
          c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 0.6 });
        },
        onEnd: () => cl?.dissolve(2)
      }), "stiletto");
    }
    c.sound("grimoire.blood.slice", p.location, 1, 1 + w * 0.12);
    for (let t = 0; t < 6; t++) {
      formation?.follow(p).yaw(p.getRotation().y);
      yield 1;
    }
  }
  yield* c.join(60);
}
function* redCourtGuillotine(c) {
  const { point } = c.aimGround(c.p("range"));
  const { yaw } = yawPitchOf(flatNorm(sub(point, c.feet)));
  const g = c.fx("grimoire:fx_b_guillotine", point, { yaw, len: 8.75, phase: 1, size: c.area });
  c.sound("grimoire.blood.form", point, 1.2, 0.8);
  yield 16;
  g?.phase(2);
  for (let t = 0; t < 28; t++) {
    if (t % 4 === 0) c.particle("grimoire:converge", add(point, v3(0, 4.5, 0)), { color: CR, color2: SC, radius: 3, life: 0.5 });
    yield 1;
  }
  g?.phase(3);
  c.sound("grimoire.blood.drop", point, 1.4, 1);
  yield 5;
  g?.phase(4);
  c.shake(point, 24, 0.6, 0.5);
  shock(c, point, c.p("radius"), c.p("damage"), { knock: 0.6, up: 0.3, color: CR, color2: SC, sound: "grimoire.blood.splash", minK: 0.6 });
  c.particle("grimoire:droplet_burst", add(point, v3(0, 1, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  const n = c.p("waves");
  for (let k = 0; k < n; k++) {
    const dir = rotY(v3(0, 0, 1), k * 360 / n + yaw);
    const from = add(point, v3(0, 0.6, 0));
    const cr = c.fx("grimoire:fx_b_crescent", from, { dir, phase: 1, size: 1.1 });
    c.run(fly(c, {
      fx: cr,
      from,
      dir,
      speed: 1,
      range: 10 * c.area,
      radius: 1.4,
      pierce: Infinity,
      stopOnBlock: true,
      onHit: (e) => {
        c.hit(e, c.p("waveDamage"));
        effect(e, "slowness", 30, 1);
      },
      onEnd: () => cr?.dissolve(4)
    }), "crescent");
  }
  yield* c.join(40);
  yield 6;
}
function* sanguineLeviathan(c) {
  const p = c.player;
  const dir = flatNorm(c.dir);
  const right = rotY(dir, 90);
  const L = c.p("length");
  const start2 = c.ground(add(p.location, add(mul(dir, 2), v3(0, 2, 0))), 6);
  const end = add(start2, mul(dir, L));
  const foes = nearestEnemies(c, add(start2, mul(dir, L / 2)), L / 2 + 4, 3);
  let c1 = add(add(start2, mul(dir, L / 3)), mul(right, 6));
  let c2 = add(add(start2, mul(dir, 2 * L / 3)), mul(right, -6));
  if (foes[0]) c1 = lerp(c1, foes[0].location, 0.7);
  if (foes[1]) c2 = lerp(c2, foes[1].location, 0.7);
  const pathAt = (t) => {
    const q = bezier3(start2, c1, c2, end, t);
    return { x: q.x, y: c.ground(add(q, v3(0, 3, 0)), 8).y + 0.8 + Math.sin(t * Math.PI * 5) * 0.9, z: q.z };
  };
  c.fx("grimoire:fx_circle_b", add(start2, v3(0, 0.06, 0)), { size: 2.5, variant: 1, phase: 1 });
  c.particle("grimoire:droplet_burst", add(start2, v3(0, 0.5, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  const nseg = c.p("segments");
  const head = c.fx("grimoire:fx_b_serpent_head", start2, { phase: 1, size: 1.3 * c.area });
  const segs = [];
  for (let i = 0; i < nseg; i++) {
    const f = c.fx(i === nseg - 1 ? "grimoire:fx_b_serpent_tail" : "grimoire:fx_b_serpent_seg", start2, { phase: 1, size: (1.25 - i * 0.04) * c.area });
    if (f) segs.push(f);
  }
  c.sound("grimoire.blood.hiss", start2, 1.3, 1);
  const history = [start2];
  const lastHit = /* @__PURE__ */ new Map();
  const ticks = 50;
  for (let t = 0; t <= ticks; t++) {
    const pos = pathAt(t / ticks);
    const prev = history[history.length - 1];
    history.push(pos);
    head?.move(pos).aim(sub(pos, prev).y === 0 && len(sub(pos, prev)) < 1e-3 ? dir : sub(pos, prev));
    segs.forEach((s, i) => {
      const k = Math.max(0, history.length - 1 - (i + 1) * 2);
      const at = history[k];
      const ahead = history[Math.min(history.length - 1, k + 2)];
      s.move(at).aim(sub(ahead, at).x === 0 && sub(ahead, at).z === 0 ? dir : sub(ahead, at));
    });
    if (t % 2 === 0) {
      for (const body of [pos, ...segs.filter((_, i) => i % 2 === 0).map((s) => s.location)]) {
        for (const e of c.enemies(body, 1.8)) {
          if ((lastHit.get(e.id) ?? -99) > t - 10) continue;
          lastHit.set(e.id, t);
          c.hit(e, c.p("contactDamage"));
          push(e, sub(e.location, body), 0.6, 0.3);
        }
      }
      c.particle("grimoire:droplet_burst", pos, { color: CR, color2: SC, count: 0.3 });
    }
    yield 1;
  }
  head?.phase(3);
  const bitePos = history[history.length - 1];
  c.sound("grimoire.blood.bite", bitePos, 1.2, 0.9);
  yield 5;
  const victim = nearestEnemies(c, bitePos, 4, 1)[0];
  if (victim) {
    c.hit(victim, c.p("biteDamage"), { immediate: true });
    push(victim, dir, 1.2, 0.5);
    c.particle("grimoire:droplet_burst", bodyCenter(victim), { color: CR, color2: SC, radius: 1.5, count: 2 });
  }
  yield 6;
  head?.dissolve(6);
  for (const s of segs) s.dissolve(6);
  const wave = c.fx("grimoire:fx_b_tidal", c.ground(add(bitePos, v3(0, 2, 0)), 6), { yaw: yawPitchOf(dir).yaw, phase: 1, size: 0.3 * c.area });
  c.sound("grimoire.blood.burst", bitePos, 1.4, 1);
  for (let t = 0; t < 12; t++) {
    const front = add(bitePos, mul(dir, 1 + t * 0.8));
    wave?.move(c.ground(add(front, v3(0, 2, 0)), 6));
    if (t % 3 === 0) {
      for (const e of c.enemies(front, 3.5)) {
        if ((lastHit.get(e.id) ?? -99) > 1e3 + t - 6) continue;
        lastHit.set(e.id, 1e3 + t);
        c.hit(e, c.p("waveDamage"));
        push(e, dir, 1.4, 0.45);
      }
      c.particle("grimoire:droplet_burst", add(front, v3(0, 1, 0)), { color: CR, color2: SC, radius: 2, count: 1.5 });
    }
    yield 1;
  }
}
function* thousandBladeCrowns(c) {
  const p = c.player;
  const n = c.p("crowns");
  const aim = c.aim(c.p("range"));
  const center = aim.entity ? { ...aim.entity.location } : c.ground(aim.point, 8);
  const crowns = [];
  for (let i = 0; i < n; i++) {
    const a = i / n * Math.PI * 2;
    crowns.push({ fx: c.fx("grimoire:fx_b_crown", add(p.location, v3(Math.cos(a) * 2.6, 3.2, Math.sin(a) * 2.6)), { phase: 1 }), spot: center });
  }
  c.sound("grimoire.blood.crown", p.location, 1.2, 1);
  yield 14;
  const foes = nearestEnemies(c, center, 12, n);
  crowns.forEach((cr, i) => {
    cr.target = foes.length ? foes[i % foes.length] : void 0;
    const a = i / n * Math.PI * 2;
    cr.spot = cr.target ? cr.target.location : add(center, v3(Math.cos(a) * 4, 0, Math.sin(a) * 4));
  });
  for (let t = 0; t < 14; t++) {
    for (const cr of crowns) {
      const goal = add(cr.target?.isValid ? cr.target.location : cr.spot, v3(0, 2.8 + (cr.target?.isValid ? cr.target.getHeadLocation().y - cr.target.location.y : 1), 0));
      cr.fx?.move(lerp(cr.fx.location, goal, 0.25));
    }
    yield 1;
  }
  for (let s = 0; s < 3; s++) {
    for (const cr of crowns) {
      cr.fx?.pulse();
      const at = cr.target?.isValid ? cr.target.location : cr.spot;
      for (const e of c.enemies(at, 1.8)) c.hit(e, c.p("slashDamage"));
      c.particle("grimoire:spark_burst", add(at, v3(0, 1.2, 0)), { color: SC, color2: BG, radius: 0.8, count: 0.6 });
    }
    c.sound("grimoire.blood.slice", center, 1.2, 0.9 + s * 0.1);
    for (let t = 0; t < 12; t++) {
      for (const cr of crowns) if (cr.target?.isValid) cr.fx?.move(add(cr.target.location, v3(0, cr.target.getHeadLocation().y - cr.target.location.y + 1.2, 0)));
      yield 1;
    }
  }
  const top = add(center, v3(0, 7, 0));
  for (let t = 0; t < 12; t++) {
    for (const cr of crowns) cr.fx?.move(lerp(cr.fx.location, top, 0.3));
    yield 1;
  }
  for (const cr of crowns) cr.fx?.dissolve(4);
  const grand = c.fx("grimoire:fx_b_grand_crown", top, { phase: 1, len: 6, size: c.area });
  c.sound("grimoire.blood.crown", top, 1.6, 0.6);
  c.particle("grimoire:glow_flash", top, { color: BG, size: 5 });
  yield 22;
  grand?.phase(3);
  yield 6;
  c.shake(center, 26, 0.7, 0.5);
  shock(c, center, c.p("finalRadius"), c.p("finalDamage"), { knock: 1.4, up: 0.5, color: SC, color2: RG, sound: "grimoire.blood.burst", minK: 0.5 });
  c.particle("grimoire:spark_burst", add(center, v3(0, 1, 0)), { color: SC, color2: RG, radius: 3, count: 3 });
  yield 14;
}
function* scarletRoseAegis(c) {
  const p = c.player;
  const rose = c.fx("grimoire:fx_b_rose_aegis", p.location, { phase: 1 });
  c.sound("grimoire.blood.bloom", p.location, 1.2, 1);
  const cap = c.p("layerCapacity") * c.power;
  const layers = [cap, cap, cap];
  let broken = 0;
  c.ward({
    label: "rose",
    priority: 30,
    protects: (e) => isAllyOrSelf(p, e) && dist(e.location, p.location) <= 3.2,
    absorb: (info) => {
      let dmg = info.damage;
      while (dmg > 0 && broken < 3) {
        const take = Math.min(dmg, layers[broken]);
        layers[broken] -= take;
        dmg -= take;
        if (layers[broken] <= 1e-3) broken++;
      }
      return dmg;
    },
    react: (info) => {
      rose?.pulse();
      rose?.phase(Math.min(5, 2 + broken));
      c.particle("grimoire:petal_burst", add(info.hurt.location, v3(0, 1.4, 0)), { color: CR, color2: SC, radius: 1.5, count: 1.2 });
      c.particle("grimoire:mist", add(info.hurt.location, v3(0, 1, 0)), { color: CR, color2: BU, radius: 1.2, size: 1, count: 0.6 });
      c.sound("grimoire.blood.absorb", info.hurt.location, 1, 1.1);
    }
  });
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    if (!c.ok) return;
    rose?.follow(p);
    if (t === 18) rose?.phase(2);
    if (t % 25 === 0) c.particle("grimoire:petal_burst", add(p.location, v3(0, 2, 0)), { color: CR, color2: SC, radius: 2, count: 0.4 });
    yield 1;
  }
}
function* royalReprisal(c) {
  const p = c.player;
  const front = () => add(p.location, add(mul(flatNorm(p.getViewDirection()), 1.1), v3(0, 0.2, 0)));
  const fan = c.fx("grimoire:fx_b_fan", front(), { yaw: p.getRotation().y, phase: 1 });
  c.sound("grimoire.blood.form", p.location, 1, 1.2);
  let left = c.p("absorbs");
  const lastCounter = /* @__PURE__ */ new Map();
  c.ward({
    label: "reprisal",
    priority: 22,
    protects: (e) => e.id === p.id && left > 0,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause)) return info.damage;
      left--;
      return 0;
    },
    react: (info, absorbed) => {
      fan?.pulse();
      c.sound("grimoire.blood.absorb", p.location, 1, 0.9);
      const src = info.projectile ? info.attacker ?? void 0 : info.attacker;
      if (!src || !src.isValid || src.id === p.id) return;
      const now = system7.currentTick;
      if ((lastCounter.get(src.id) ?? -99) > now - 10) return;
      lastCounter.set(src.id, now);
      const dmg = Math.max(c.p("lanceDamage"), absorbed * 1.5);
      system7.runTimeout(() => {
        if (!p.isValid || !src.isValid) return;
        for (let k = 0; k < 3; k++) {
          const from = add(front(), add(rotY(v3((k - 1) * 0.8, 0, 0), p.getRotation().y), v3(0, 1.2 + k % 2 * 0.4, 0)));
          const dir = norm(sub(bodyCenter(src), from));
          const l = c.fx("grimoire:fx_b_lance", from, { dir, phase: 1 });
          c.run(fly(c, {
            fx: l,
            from,
            dir,
            speed: 1.8,
            range: 30,
            radius: 0.7,
            pierce: 1,
            homing: src,
            homingRate: 0.4,
            onHit: (e) => {
              c.hit(e, dmg / 3, { kind: "reflect" });
              c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 0.6 });
            },
            onEnd: () => l?.dissolve(2)
          }), "counter");
        }
        c.sound("grimoire.blood.lance", p.location, 1, 1.1);
      }, 4);
    }
  });
  for (let t = 0; t < c.p("duration") * 20 && left > 0; t++) {
    if (!c.ok) return;
    fan?.move(front()).yaw(p.getRotation().y);
    if (t === 12) fan?.phase(2);
    yield 1;
  }
  yield* c.join(30);
}
function veinboundMarionette(c) {
  const a = c.aim(c.p("range"));
  const center0 = a.entity ? a.entity.location : a.point;
  const list = nearestEnemies(c, center0, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to bind in range");
  return (function* () {
    const mid = targets.reduce((acc, e) => add(acc, mul(e.location, 1 / targets.length)), v3(0, 0, 0));
    const ground = c.ground(add(mid, v3(0, 2, 0)), 6);
    const sky = add(ground, v3(0, 6, 0));
    c.fx("grimoire:fx_circle_b", sky, { size: 4, variant: 1, phase: 1 });
    c.sound("grimoire.blood.form", sky, 1.2, 0.9);
    const dur = c.p("duration") * 20;
    const items = targets.map((t) => ({
      t,
      thread: c.fx("grimoire:fx_b_thread", sky, { phase: 1, len: 0.1 }),
      b: c.bind(t, dur + 10, { pull: ground, pullSpeed: 0.07, slowAmp: 6 })
    }));
    for (let s = 0; s < 10; s++) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        const to = add(it.t.location, v3(0, it.t.getHeadLocation().y - it.t.location.y + 0.2, 0));
        it.thread?.aim(sub(to, sky)).length(dist(sky, to) * (s + 1) / 10);
      }
      yield 1;
    }
    c.sound("grimoire.blood.snap", sky, 0.8, 0.6);
    for (let s = 0; s < dur; s++) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        const to = add(it.t.location, v3(0, it.t.getHeadLocation().y - it.t.location.y + 0.2, 0));
        it.thread?.aim(sub(to, sky)).length(dist(sky, to));
        if (s % 20 === 0) {
          c.hit(it.t, c.p("dps"));
          it.thread?.pulse();
        }
      }
      yield 1;
    }
    for (const it of items) {
      endBind(it.b, false);
      it.thread?.dissolve(3);
      if (it.t.isValid) c.particle("grimoire:droplet_burst", bodyCenter(it.t), { color: CR, color2: SC, count: 0.5 });
    }
    c.sound("grimoire.blood.snap", sky, 1.2, 1.2);
    yield 6;
  })();
}
function* crimsonThornGarden(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  c.fx("grimoire:fx_b_roots", add(point, v3(0, 0.04, 0)), { phase: 1, size: R / 9.4 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.08, 0)), { size: R, variant: 1, phase: 1 });
  c.sound("grimoire.blood.form", point, 1.4, 0.7);
  const roses = [];
  for (let k = 0; k < 6; k++) {
    const at = k === 0 ? point : c.ground(add(point, v3(Math.cos(k / 5 * 6.283) * R * 0.62, 3, Math.sin(k / 5 * 6.283) * R * 0.62)), 8);
    roses.push({ fx: c.fx("grimoire:fx_b_rose", at, { phase: 1, size: k === 0 ? 1.2 : 0.85, yaw: k * 60 }), at });
    yield 3;
  }
  c.sound("grimoire.blood.bloom", point, 1.4, 0.9);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        c.hit(e, 1);
      }
    }
    if (t % 40 === 20) {
      for (const e of nearestEnemies(c, point, R, 6)) {
        c.fx("grimoire:fx_b_thorns", e.location, { phase: 1, yaw: t * 37 % 360, size: 0.9 });
        c.particle("grimoire:thorn_burst", e.location, { color: CR, color2: BG, size: 1.2, radius: 1.4, count: 2 });
        c.hit(e, c.p("thornDamage"));
        push(e, v3(0, 0, 0), 0, 0.4);
        effect(e, "slowness", 40, 2);
      }
      c.sound("grimoire.blood.thorn", point, 1.1, 1);
    }
    if (t % 60 === 50) {
      for (const r of roses) {
        r.fx?.pulse();
        c.fx("grimoire:fx_b_wave_ring", add(r.at, v3(0, 0.3, 0)), { phase: 1, size: 1 });
        for (const e of c.enemies(r.at, 4.2)) c.hit(e, c.p("waveDamage"));
      }
      c.sound("grimoire.blood.slice", point, 1.2, 0.8);
    }
    yield 1;
  }
}
function* hematicMaelstrom(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const sea = c.fx("grimoire:fx_b_sea", add(point, v3(0, 0.05, 0)), { phase: 1, size: R / 8 });
  c.sound("grimoire.blood.splash", point, 1.2, 0.7);
  yield 20;
  sea?.phase(3);
  const whirl = c.fx("grimoire:fx_b_whirl", add(point, v3(0, 0.12, 0)), { phase: 1, size: R / 7.5 });
  c.sound("grimoire.blood.whirl", point, 1.4, 1);
  for (let t = 0; t < c.p("pullTicks"); t++) {
    for (const e of c.enemies(point, R + 2)) pullToward(e, point, 0.3);
    if (t % 20 === 0) for (const e of c.enemies(point, R)) c.hit(e, c.p("dps"));
    if (t % 5 === 0) c.particle("grimoire:converge", add(point, v3(0, 0.6, 0)), { color: CR, color2: SC, radius: R, life: 0.8 });
    yield 1;
  }
  whirl?.dissolve(8);
  const pillar = c.fx("grimoire:fx_b_pillar", point, { phase: 1, size: 1.3 * c.area });
  c.sound("grimoire.blood.form", point, 1.4, 0.6);
  yield 18;
  pillar?.phase(3);
  c.shake(point, 24, 0.6, 0.5);
  shock(c, point, R, c.p("burstDamage"), { knock: 0.6, up: 1, color: CR, color2: SC, sound: "grimoire.blood.burst", minK: 0.5 });
  for (let t = 0; t < 40; t++) {
    if (t % 5 === 0) c.particle("grimoire:blood_rain", add(point, v3(0, 2, 0)), { color: CR, color2: SC, radius: R, count: 0.8 });
    yield 1;
  }
}
function bloodstep(c) {
  const dest = teleportDestination(c, c.p("range"));
  if (!dest) throw new Fizzle("No safe place to reform");
  return (function* () {
    const p = c.player;
    const from = p.location;
    for (const y of [0.4, 1, 1.6]) c.particle("grimoire:droplet_burst", add(from, v3(0, y, 0)), { color: CR, color2: SC, radius: 0.6, count: 1 });
    c.fx("grimoire:fx_b_fragments", from, { phase: 1 });
    c.sound("grimoire.blood.step", from, 1, 1);
    yield 3;
    p.tryTeleport(dest, { checkForBlocks: true, keepVelocity: false });
    grantFallImmunity(p.id, 30);
    const reform = c.fx("grimoire:fx_b_fragments", dest, { phase: 1 });
    reform?.phase(3);
    c.fx("grimoire:fx_circle_b", add(dest, v3(0, 0.06, 0)), { size: 1.3, variant: 1, phase: 1 });
    c.particle("grimoire:fragment_burst", add(dest, v3(0, 1, 0)), { color: SC, color2: BG, radius: 0.8, count: 1 });
    c.sound("grimoire.blood.step", dest, 1, 1.3);
    yield 20;
  })();
}
function* arterialCurrent(c) {
  const p = c.player;
  let dir = norm(add(c.dir, v3(0, 0.15, 0)));
  const ribbons = [];
  c.sound("grimoire.blood.flow", p.location, 1.2, 1);
  grantFallImmunity(p.id, 260);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (!c.ok) break;
    dir = norm(lerp(dir, p.getViewDirection(), 0.12));
    let mv = { x: 0, y: 0 };
    try {
      mv = p.inputInfo.getMovementVector();
    } catch {
    }
    const speed = c.p("speed") * (mv.y > 0.3 ? 1.3 : mv.y < -0.3 ? 0.45 : 1);
    const here = add(p.location, v3(0, 0.9, 0));
    if (freeDistance(c.dim, here, dir, 2.5) < 2.2) dir = norm(add(dir, v3(0, 0.6, 0)));
    drive(p, mul(dir, speed));
    grantFallImmunity(p.id, 40);
    if (t % 2 === 0) {
      const at = add(p.location, add(mul(dir, 2.4), v3(0, -0.3, 0)));
      ribbons.push({ fx: c.fx("grimoire:fx_b_ribbon", at, { dir, phase: 1, size: 1.1 }), born: t });
      if (t % 20 === 10) {
        const side = rotY(flatNorm(dir), t % 40 === 10 ? 35 : -35);
        ribbons.push({ fx: c.fx("grimoire:fx_b_ribbon", add(at, mul(side, 1.5)), { dir: side, phase: 1, size: 0.7 }), born: t - 14 });
      }
    }
    for (let i = ribbons.length - 1; i >= 0; i--) {
      if (t - ribbons[i].born > 26 || ribbons.length > 18) {
        const r = ribbons.splice(i, 1)[0];
        if (r.fx) c.particle("grimoire:droplet_burst", r.fx.location, { color: CR, color2: SC, count: 0.3 });
        r.fx?.dissolve(5);
      }
    }
    if (t % 10 === 0) c.sound("grimoire.blood.flow", p.location, 0.5, 1.1);
    yield 1;
  }
  effect(p, "slow_falling", 60, 0);
  grantFallImmunity(p.id, 120);
  for (const r of ribbons) {
    if (r.fx) c.particle("grimoire:droplet_burst", r.fx.location, { color: CR, color2: SC, count: 0.4 });
    r.fx?.dissolve(6);
  }
  yield 6;
}
function act(e, v) {
  try {
    if (e.isValid) e.setProperty("grimoire:act", v);
  } catch {
  }
}
function* royalStag(c) {
  const p = c.player;
  const at = c.ground(add(p.location, add(rotY(v3(2.5, 0, 1), p.getRotation().y), v3(0, 2, 0))), 6);
  c.fx("grimoire:fx_circle_b", add(at, v3(0, 0.06, 0)), { size: 2.6, variant: 2, phase: 1 });
  c.particle("grimoire:droplet_burst", add(at, v3(0, 1.5, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  let stag;
  try {
    stag = c.dim.spawnEntity("grimoire:royal_stag", at, { initialRotation: p.getRotation().y });
  } catch {
    throw new Fizzle("The stag could not form here");
  }
  stag.setDynamicProperty(OWNER_PROP, p.id);
  stag.setDynamicProperty(SESSION_PROP, SESSION);
  stag.addTag("grimoire_summon");
  try {
    stag.getComponent(EntityTameableComponent2.componentId)?.tame(p);
  } catch {
  }
  act(stag, 4);
  c.sound("grimoire.blood.stag", at, 1.4, 1);
  c.onCleanup(() => {
    if (!stag.isValid) return;
    act(stag, 7);
    c.particle("grimoire:droplet_burst", add(stag.location, v3(0, 1.5, 0)), { color: CR, color2: SC, radius: 1.5, count: 2 });
    system7.runTimeout(() => {
      try {
        if (stag.isValid) stag.remove();
      } catch {
      }
    }, 24);
  });
  let lastWave = -999;
  const wave = (why) => {
    if (!stag.isValid || system7.currentTick - lastWave < 60) return;
    lastWave = system7.currentTick;
    act(stag, 3);
    system7.runTimeout(() => act(stag, 0), 20);
    shock(c, p.location, 5, c.p("waveDamage"), { knock: 1.4, up: 0.4, color: CR, color2: SC, sound: "grimoire.blood.burst" });
    effect(p, "absorption", 200, 0);
    void why;
  };
  c.ward({ label: "stag", priority: 1, protects: (e) => e.id === p.id, absorb: (i) => i.damage, react: () => wave("hit") });
  yield 28;
  act(stag, 0);
  const total = c.p("duration") * 20;
  let step2 = 0;
  for (let t = 0; t < total; t++) {
    if (!c.ok || !stag.isValid) break;
    if (dist(stag.location, p.location) > 28) {
      try {
        stag.teleport(add(p.location, v3(1.5, 0.5, 1.5)));
      } catch {
      }
    }
    const v = stag.getVelocity();
    if (Math.hypot(v.x, v.z) > 0.05 && t % 4 === 0) {
      step2++;
      const side = rotY(flatNorm(v), 90);
      const foot = add(stag.location, add(mul(side, step2 % 2 ? 0.35 : -0.35), v3(0, 0.05, 0)));
      c.particle("grimoire:hoofprint", foot, { color: BG, size: 1, dir: flatNorm(v) });
      if (step2 % 2 === 0) c.sound("grimoire.blood.hoof", foot, 0.5, 0.9 + step2 % 4 * 0.05);
    }
    if (t % 100 === 40) {
      const foe = nearestEnemies(c, stag.location, 16, 1)[0];
      if (foe) {
        act(stag, 5);
        c.sound("grimoire.blood.stag", stag.location, 1.1, 1.2);
        yield 20;
        if (!stag.isValid) break;
        act(stag, 6);
        const hitIds = /* @__PURE__ */ new Set();
        for (let s = 0; s < 18 && stag.isValid; s++) {
          const goal = foe.isValid ? foe.location : stag.location;
          const d = sub(goal, stag.location);
          if (len(flatNorm(d)) > 0 && Math.hypot(d.x, d.z) > 1.2) {
            try {
              stag.clearVelocity();
              stag.applyImpulse(add(mul(flatNorm(d), 0.95), v3(0, 0.02, 0)));
            } catch {
            }
          }
          for (const e of c.enemies(stag.location, 1.9)) {
            if (hitIds.has(e.id)) continue;
            hitIds.add(e.id);
            c.hit(e, c.p("chargeDamage"));
            push(e, sub(e.location, stag.location), 1.8, 0.6);
            c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, radius: 1, count: 1 });
            c.sound("grimoire.blood.bite", e.location, 1, 0.8);
          }
          if (s % 3 === 0) c.particle("grimoire:hoofprint", add(stag.location, v3(0, 0.05, 0)), { color: BG, size: 1.2 });
          yield 1;
        }
        act(stag, 0);
      }
    }
    if (t % 80 === 70 && c.enemies(p.location, 5).length > 0) wave("crowd");
    yield 1;
  }
}
function sovereignsPulse(c) {
  const a = c.aim(30);
  const marked = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, 10, c.p("targets"));
  if (a.entity && !marked.find((e) => e.id === a.entity.id)) marked.unshift(a.entity);
  const list = marked.slice(0, c.p("targets"));
  if (!list.length) throw new Fizzle("No enemy to mark");
  return (function* () {
    const sigils2 = /* @__PURE__ */ new Map();
    for (const e of list) sigils2.set(e.id, c.fx("grimoire:fx_b_heart_sigil", add(e.getHeadLocation(), v3(0, 0.9, 0)), { phase: 1 }));
    const links = /* @__PURE__ */ new Map();
    const key2 = (x, y) => x.id < y.id ? `${x.id}|${y.id}` : `${y.id}|${x.id}`;
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) links.set(key2(list[i], list[j]), c.fx("grimoire:fx_b_thread", list[i].location, { phase: 1, len: 0.1 }));
    const alive = () => list.filter((e) => e.isValid);
    const suppress = /* @__PURE__ */ new Map();
    const share = c.p("share");
    const owner = c.player;
    const off = onHurt({
      ownerId: c.ownerId,
      watch: new Set(list.map((e) => e.id)),
      fn: (victim, damage, cause) => {
        const s = suppress.get(victim.id);
        if (s !== void 0 && system7.currentTick - s <= 1 && cause === EntityDamageCause4.magic) {
          suppress.delete(victim.id);
          return;
        }
        const others = alive().filter((o) => o.id !== victim.id);
        if (!others.length || damage <= 0) return;
        system7.run(() => {
          for (const o of others) {
            if (!o.isValid) continue;
            suppress.set(o.id, system7.currentTick);
            try {
              o.applyDamage(damage * share, { cause: EntityDamageCause4.magic, damagingEntity: owner.isValid ? owner : void 0 });
            } catch {
            }
            const l = links.get(key2(victim, o));
            l?.pulse();
            const from = bodyCenter(victim), to = bodyCenter(o);
            for (let k = 1; k <= 4; k++) c.particle("grimoire:heart_pulse", lerp(from, to, k / 5), { color: BG, size: 0.5, life: 0.6 });
          }
          c.sound("grimoire.blood.heart", victim.location, 0.9, 1.2);
        });
      }
    });
    c.onCleanup(off);
    c.sound("grimoire.blood.heart_big", list[0].location, 1.2, 1);
    yield 8;
    for (const e of list) if (e.isValid) c.hit(e, c.p("initialDamage"), { immediate: true });
    const total = c.p("duration") * 20;
    for (let t = 0; t < total; t++) {
      const live2 = alive();
      if (!live2.length) break;
      for (const e of list) {
        const s = sigils2.get(e.id);
        if (!e.isValid) {
          s?.dissolve(4);
          sigils2.delete(e.id);
          continue;
        }
        s?.move(add(e.getHeadLocation(), v3(0, 0.9, 0)));
      }
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const l = links.get(key2(list[i], list[j]));
          if (!l) continue;
          if (!list[i].isValid || !list[j].isValid) {
            l.dissolve(3);
            links.delete(key2(list[i], list[j]));
            continue;
          }
          const from = bodyCenter(list[i]), to = bodyCenter(list[j]);
          l.move(from).aim(sub(to, from)).length(dist(from, to));
        }
      }
      if (t % 20 === 0) c.sound("grimoire.blood.heart", live2[0].location, 0.6, 1);
      yield 1;
    }
  })();
}
function* scarletSea(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const dir = flatNorm(sub(point, c.feet));
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.1, 0)), { size: R, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_b", add(point, add(mul(rotY(dir, 90), R * 0.6), v3(0, 8, 0))), { size: R * 0.35, variant: 1, phase: 1, pitch: 30 });
  c.fx("grimoire:fx_circle_b", add(point, add(mul(rotY(dir, -90), R * 0.6), v3(0, 8, 0))), { size: R * 0.35, variant: 1, phase: 1, pitch: -30 });
  const sea = c.fx("grimoire:fx_b_sea", add(point, v3(0, 0.12, 0)), { phase: 1, size: R / 8 });
  const players = c.dim.getPlayers({ location: point, maxDistance: R + 8 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:scarlet_sea grimoire_b14");
    } catch {
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_b14");
      } catch {
      }
    }
  });
  c.sound("grimoire.blood.whirl", point, 1.6, 0.6);
  const r = rng(system7.currentTick + 5);
  const roses = [];
  for (let k = 0; k < 4; k++) {
    const at = c.ground(add(point, v3(Math.cos(k / 4 * 6.283 + 0.4) * R * 0.55, 3, Math.sin(k / 4 * 6.283 + 0.4) * R * 0.55)), 8);
    roses.push({ fx: c.fx("grimoire:fx_b_rose", at, { phase: 1, size: 1.7, yaw: k * 90 }), at });
  }
  const total = c.p("duration") * 20;
  const pillars = [];
  for (let t = 0; t < total - 60; t++) {
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        c.hit(e, 1);
      }
    }
    if (t % 50 === 10 && pillars.length < 6) {
      const ang = r() * Math.PI * 2, rr = Math.sqrt(r()) * R * 0.8;
      const at = c.ground(add(point, v3(Math.cos(ang) * rr, 3, Math.sin(ang) * rr)), 8);
      pillars.push({ fx: c.fx("grimoire:fx_b_pillar", at, { phase: 1, size: 0.8 }), at, born: t });
      for (const e of c.enemies(at, 2.6)) {
        c.hit(e, 8);
        push(e, v3(0, 0, 0), 0, 0.9);
      }
      c.sound("grimoire.blood.burst", at, 1, 1.2);
    }
    for (const pl of pillars) {
      if (t - pl.born === 60) pl.fx?.phase(3);
    }
    if (t % 80 === 40) {
      for (const rs of roses) {
        rs.fx?.pulse();
        for (const e of c.enemies(rs.at, 6)) effect(e, "slowness", 60, 2);
      }
    }
    if (t % 60 === 30) {
      for (const e of nearestEnemies(c, point, R, 3)) {
        const side = rotY(flatNorm(sub(e.location, point)), 160);
        const at = c.ground(add(e.location, add(mul(side, 2.2), v3(0, 2, 0))), 6);
        const beast = c.fx("grimoire:fx_b_beast", at, { dir: sub(e.location, at), phase: 1, size: 0.75 });
        c.run((function* () {
          yield 12;
          beast?.pulse();
          yield 6;
          if (e.isValid) {
            c.hit(e, c.p("beastDamage"));
            pullToward(e, at, 0.8);
            c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 1 });
          }
          yield 14;
          beast?.dissolve(8);
        })(), "beast");
      }
      c.sound("grimoire.blood.hiss", point, 1.2, 0.8);
    }
    yield 1;
  }
  sea?.phase(3);
  const startPos = add(point, mul(dir, -R));
  const tidal = c.fx("grimoire:fx_b_tidal", c.ground(add(startPos, v3(0, 3, 0)), 8), { yaw: yawPitchOf(dir).yaw, phase: 1, size: R / 13 });
  c.sound("grimoire.blood.storm", point, 1.8, 0.8);
  const hit2 = /* @__PURE__ */ new Set();
  for (let t = 0; t < 40; t++) {
    const front = add(startPos, mul(dir, 2 * R * t / 40));
    tidal?.move(c.ground(add(front, v3(0, 3, 0)), 8));
    for (const e of c.enemies(front, R * 0.6)) {
      if (hit2.has(e.id)) continue;
      const along = (e.location.x - front.x) * dir.x + (e.location.z - front.z) * dir.z;
      if (Math.abs(along) > 2.5) continue;
      hit2.add(e.id);
      c.hit(e, c.p("waveDamage"));
      push(e, dir, 2.4, 0.7);
    }
    if (t % 4 === 0) c.particle("grimoire:droplet_burst", add(front, v3(0, 2, 0)), { color: CR, color2: SC, radius: 3, count: 2 });
    yield 1;
  }
  c.shake(point, R * 2, 0.7, 0.6);
  yield 10;
}
function* crimsonMoonHeart(c) {
  const p = c.player;
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const heartPos = add(point, v3(0, 12, 0));
  const players = c.dim.getPlayers({ location: point, maxDistance: 64 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:crimson_moon grimoire_b15");
    } catch {
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_b15");
      } catch {
      }
    }
  });
  const book = c.fx("grimoire:fx_b_book", add(p.location, v3(0, 2.2, 0)), { phase: 1, yaw: p.getRotation().y });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 22, 0)), { size: R * 1.2, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 16, 0)), { size: R * 0.7, variant: 0, phase: 1, pitch: 18 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.1, 0)), { size: R, variant: 1, phase: 1 });
  c.flash(point, 64, { r: 0.6, g: 0.02, b: 0.06 }, 0.4);
  for (let t = 0; t < 20; t++) {
    book?.move(add(p.location, v3(0, 2.2 + t * 0.08, 0))).yaw(p.getRotation().y);
    yield 1;
  }
  const heart = c.fx("grimoire:fx_b_heart", heartPos, { phase: 1, size: 1.6 * c.area });
  c.sound("grimoire.blood.heart_big", heartPos, 2, 0.8);
  for (let t = 0; t < 70; t++) {
    book?.move(add(p.location, v3(0, 3.8, 0))).yaw(p.getRotation().y);
    if (t % 20 === 10) {
      heart?.phase(2);
      c.sound("grimoire.blood.heart_big", heartPos, 2, 1);
      c.particle("grimoire:ring_h", add(point, v3(0, 0.5, 0)), { color: CR, color2: BG, radius: R * 2.2, life: 1.2 });
      c.particle("grimoire:heart_pulse", heartPos, { color: BG, size: 6, life: 1 });
      for (const e of c.enemies(point, R)) c.hit(e, c.p("pulseDamage"));
      c.shake(point, R * 2, 0.2, 0.3);
    }
    yield 1;
  }
  const ends = [];
  const vessels = [];
  for (let k = 0; k < 8; k++) {
    const end = c.ground(add(point, v3(Math.cos(k / 8 * 6.283) * R * 0.75, 6, Math.sin(k / 8 * 6.283) * R * 0.75)), 14);
    ends.push(end);
    const v = c.fx("grimoire:fx_b_vessel", heartPos, { dir: sub(end, heartPos), len: dist(heartPos, end), phase: 1, size: 1.6 });
    if (v) vessels.push(v);
  }
  c.sound("grimoire.blood.flow", heartPos, 1.6, 0.7);
  yield 12;
  const r = rng(system7.currentTick);
  for (let cycle = 0; cycle < 8; cycle++) {
    const foes = nearestEnemies(c, point, R, 6);
    const kind = cycle % 3;
    for (const e of foes.slice(0, 3)) {
      if (kind === 0) {
        const from = add(ends[Math.floor(r() * ends.length)], v3(0, 1, 0));
        const dir = norm(sub(bodyCenter(e), from));
        const l = c.fx("grimoire:fx_b_lance", from, { dir, phase: 1, size: 1.4 });
        c.run(fly(c, {
          fx: l,
          from,
          dir,
          speed: 2,
          range: R * 2.2,
          radius: 0.8,
          pierce: 2,
          homing: e,
          homingRate: 0.4,
          onHit: (x) => c.hit(x, c.p("attackDamage")),
          onEnd: () => l?.dissolve(2)
        }), "lance");
      } else if (kind === 1) {
        c.fx("grimoire:fx_b_cage", e.location, { phase: 1, size: Math.max(1, (e.getHeadLocation().y - e.location.y) / 1.5) });
        c.bind(e, 40, {});
        c.hit(e, c.p("attackDamage") * 0.8);
      } else {
        const hand = c.fx("grimoire:fx_b_hand", c.ground(add(e.location, v3(0, 2, 0)), 6), { phase: 1, yaw: r() * 360, size: 0.9 });
        c.run((function* () {
          yield 10;
          hand?.phase(2);
          if (e.isValid) {
            c.hit(e, c.p("attackDamage") * 1.4);
            c.bind(e, 30, {});
          }
          yield 20;
          hand?.dissolve(8);
        })(), "hand");
      }
    }
    for (const v of vessels) v.pulse();
    heart?.phase(2);
    c.sound(kind === 0 ? "grimoire.blood.lance" : kind === 1 ? "grimoire.blood.thorn" : "grimoire.blood.splash", point, 1.3, 1);
    yield 15;
  }
  heart?.phase(3);
  for (const v of vessels) v.phase(3);
  c.sound("grimoire.blood.heart", heartPos, 0.4, 0.5);
  yield 24;
  heart?.phase(4);
  c.flash(point, 80, { r: 1, g: 0.1, b: 0.12 }, 0.2);
  c.sound("grimoire.blood.heart_big", heartPos, 2, 0.6);
  c.sound("grimoire.blood.shatter", heartPos, 2, 0.8);
  c.shake(point, R * 3, 1, 0.8);
  shock(c, point, R, c.p("finalDamage"), { knock: 2.2, up: 0.8, color: CR, color2: BG, minK: 0.35 });
  for (let k = 0; k < 3; k++) c.particle("grimoire:fragment_burst", add(heartPos, v3(0, k - 1, 0)), { color: SC, color2: BG, radius: 4 + k * 2, count: 4 });
  book?.dissolve(10);
  for (let t = 0; t < 60; t++) {
    if (t % 4 === 0) c.particle("grimoire:blood_rain", add(point, v3(0, 8, 0)), { color: CR, color2: SC, radius: R, count: 1.2 });
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) c.hit(e, 3);
      c.flash(point, R * 2, { r: 0.8, g: 0.05, b: 0.08 }, 0.02);
      c.sound("grimoire.blood.storm", point, 1.2, 1 + t / 100);
    }
    yield 1;
  }
  for (let k = 0; k < 4; k++) {
    c.particle("grimoire:ring_h", add(point, v3(0, 0.6 + k * 1.5, 0)), { color: RG, color2: COLORS.gold, radius: R * (1 + k * 0.4), life: 1.6 });
    c.sound("grimoire.blood.crown", point, 1, 0.7 + k * 0.15);
    yield 8;
  }
  yield 10;
}

// src/spells/blood/index.ts
var S = "blood";
var BLOOD = [
  {
    code: "B01",
    id: "blood.stiletto_rain",
    school: S,
    name: "Crimson Stiletto Rain",
    cooldown: 7,
    charge: 10,
    enhanceable: true,
    params: { blades: 36, volleys: 3, damage: 4, range: 32 },
    blurb: "Rings of crimson stilettos launch in successive volleys.",
    cast: stilettoRain
  },
  {
    code: "B02",
    id: "blood.red_court_guillotine",
    school: S,
    name: "Guillotine of the Red Court",
    cooldown: 16,
    charge: 14,
    enhanceable: true,
    params: { damage: 20, radius: 3, waveDamage: 8, waves: 6, range: 32 },
    blurb: "Blood threads weave a gothic execution blade that bursts into crescents.",
    cast: redCourtGuillotine
  },
  {
    code: "B03",
    id: "blood.sanguine_leviathan",
    school: S,
    name: "Sanguine Leviathan",
    cooldown: 24,
    charge: 18,
    enhanceable: true,
    params: { length: 30, contactDamage: 5, biteDamage: 18, waveDamage: 10, segments: 10 },
    blurb: "A serpent of blood winds across the field, bites, then crashes as a wave.",
    cast: sanguineLeviathan
  },
  {
    code: "B04",
    id: "blood.thousand_blade_crowns",
    school: S,
    name: "Crown of a Thousand Blades",
    cooldown: 26,
    charge: 18,
    enhanceable: true,
    params: { crowns: 12, slashDamage: 4, finalDamage: 22, finalRadius: 5, range: 30 },
    blurb: "Twelve bladed crowns strike, then merge into one royal crown.",
    cast: thousandBladeCrowns
  },
  {
    code: "B05",
    id: "blood.scarlet_rose_aegis",
    school: S,
    name: "Aegis of the Scarlet Rose",
    cooldown: 25,
    charge: 12,
    enhanceable: true,
    params: { duration: 8, layers: 3, layerCapacity: 8 },
    blurb: "A blooming rose barrier whose outer petals absorb damage.",
    cast: scarletRoseAegis
  },
  {
    code: "B06",
    id: "blood.royal_reprisal",
    school: S,
    name: "Royal Reprisal",
    cooldown: 28,
    charge: 12,
    enhanceable: true,
    params: { duration: 12, absorbs: 5, lanceDamage: 6 },
    blurb: "A fan shield absorbs blows and answers with blood lances.",
    cast: royalReprisal
  },
  {
    code: "B07",
    id: "blood.veinbound_marionette",
    school: S,
    name: "Veinbound Marionette",
    cooldown: 30,
    charge: 16,
    enhanceable: true,
    params: { targets: 5, duration: 6, dps: 2, range: 30, selectRadius: 8 },
    blurb: "Blood threads restrain enemies and pull them together.",
    cast: veinboundMarionette
  },
  {
    code: "B08",
    id: "blood.crimson_thorn_garden",
    school: S,
    name: "Garden of the Crimson Thorns",
    cooldown: 35,
    charge: 20,
    enhanceable: true,
    params: { duration: 12, radius: 9, thornDamage: 4, waveDamage: 5, range: 28 },
    blurb: "Giant roses, roots and thorns overrun the battlefield.",
    cast: crimsonThornGarden
  },
  {
    code: "B09",
    id: "blood.hematic_maelstrom",
    school: S,
    name: "Hematic Maelstrom",
    cooldown: 40,
    charge: 20,
    enhanceable: true,
    params: { radius: 8, pullTicks: 60, dps: 2, burstDamage: 14, range: 32 },
    blurb: "A blood whirlpool drags enemies in, then erupts as a pillar.",
    cast: hematicMaelstrom
  },
  {
    code: "B10",
    id: "blood.bloodstep",
    school: S,
    name: "Bloodstep: Shattered Ruby",
    cooldown: 7,
    charge: 6,
    enhanceable: false,
    params: { range: 12 },
    blurb: "Dissolve into ruby droplets and reform nearby.",
    cast: bloodstep
  },
  {
    code: "B11",
    id: "blood.arterial_current",
    school: S,
    name: "Arterial Current",
    cooldown: 18,
    charge: 12,
    enhanceable: false,
    params: { duration: 10, speed: 0.9 },
    blurb: "Ride a flowing ribbon of crimson liquid through the air.",
    cast: arterialCurrent
  },
  {
    code: "B12",
    id: "blood.royal_stag",
    school: S,
    name: "Crimson Familiar: The Royal Stag",
    cooldown: 55,
    charge: 24,
    enhanceable: true,
    params: { duration: 25, chargeDamage: 14, waveDamage: 8 },
    blurb: "A ruby stag that charges enemies and shields you with blood waves.",
    cast: royalStag
  },
  {
    code: "B13",
    id: "blood.sovereigns_pulse",
    school: S,
    name: "Sovereign's Pulse",
    cooldown: 45,
    charge: 16,
    enhanceable: true,
    params: { duration: 10, targets: 3, share: 0.5, initialDamage: 4 },
    blurb: "Linked heart sigils share the damage each marked enemy takes.",
    cast: sovereignsPulse
  },
  {
    code: "B14",
    id: "blood.scarlet_sea",
    school: S,
    name: "Grand Magic: Scarlet Sea of Lament",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { duration: 20, radius: 16, beastDamage: 10, waveDamage: 25, range: 36 },
    blurb: "A sea of blood with pillars, roses and beasts, ending in a tidal wave.",
    cast: scarletSea
  },
  {
    code: "B15",
    id: "blood.crimson_moon_heart",
    school: S,
    name: "Imperial Edict: Heart of the Crimson Moon",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 24, range: 36, pulseDamage: 4, attackDamage: 8, finalDamage: 40 },
    blurb: "Awakening, the emperor's circulation, and the final heartbeat.",
    cast: crimsonMoonHeart
  }
];

// src/spells/kit2.ts
import { EntityDamageCause as EntityDamageCause5, EntityProjectileComponent, system as system8 } from "@minecraft/server";
var SPECTRUM = [
  COLORS.sp_red,
  COLORS.sp_orange,
  COLORS.sp_yellow,
  COLORS.sp_green,
  COLORS.sp_blue,
  COLORS.sp_indigo,
  COLORS.sp_violet
];
function hostileProjectiles(c, center, radius, skip) {
  const out = [];
  let list = [];
  try {
    list = c.dim.getEntities({ location: center, maxDistance: radius });
  } catch {
    return out;
  }
  for (const e of list) {
    if (skip?.has(e.id)) continue;
    let proj;
    try {
      proj = e.getComponent(EntityProjectileComponent.componentId);
    } catch {
      continue;
    }
    if (!proj) continue;
    const owner = proj.owner;
    if (owner && (owner.id === c.player.id || isAllyOrSelf(c.player, owner))) continue;
    out.push({ e, proj, vel: e.getVelocity() });
  }
  return out;
}
function redirect(inc, dir, speedMul = 1, claim) {
  try {
    const speed = Math.max(0.5, len(inc.vel)) * speedMul;
    inc.e.clearVelocity();
    inc.e.applyImpulse(mul(norm(dir), speed));
    if (claim) inc.proj.owner = claim;
    return true;
  } catch {
    return false;
  }
}
function neutralize(inc) {
  try {
    inc.e.clearVelocity();
    inc.e.remove();
  } catch {
  }
}
function spawnDecoy(c, at) {
  return c.fx("grimoire:decoy", at, {});
}
function lure(mob, decoy) {
  if (!decoy?.ok || !mob.isValid || mob.typeId === "minecraft:player") return;
  try {
    mob.applyDamage(1, { cause: EntityDamageCause5.entityAttack, damagingEntity: decoy.entity });
  } catch {
  }
}
function alliesNear(c, center, radius) {
  return livingNear(c.dim, center, radius).filter((e) => e.id === c.player.id || isAllyOrSelf(c.player, e));
}
var NEGATIVE = ["poison", "wither", "slowness", "weakness", "blindness", "nausea", "mining_fatigue", "hunger", "darkness", "levitation"];
function healAndCleanse(e, amount, cleanse) {
  let restored = 0;
  try {
    const hp = e.getComponent("minecraft:health");
    if (hp && hp.currentValue > 0) {
      const next = Math.min(hp.effectiveMax, hp.currentValue + amount);
      restored = next - hp.currentValue;
      if (restored > 0) hp.setCurrentValue(next);
    }
  } catch {
  }
  if (cleanse) {
    for (const id of NEGATIVE) {
      try {
        e.removeEffect(id);
      } catch {
      }
    }
  }
  return restored;
}
function surfaceRoute(c, from, dir, maxDist, step2 = 0.5, stepUp = 1, stepDown = 3) {
  const f = flatNorm(dir);
  const pts = [];
  let cur = { x: from.x, y: Math.floor(from.y), z: from.z };
  for (let d = step2; d <= maxDist; d += step2) {
    const nx = from.x + f.x * d;
    const nz = from.z + f.z * d;
    let found;
    for (let dy = stepUp; dy >= -stepDown; dy--) {
      const feet = { x: nx, y: cur.y + dy, z: nz };
      const below = { x: nx, y: cur.y + dy - 1, z: nz };
      if (isPassable(c.dim, feet) && isPassable(c.dim, add(feet, v3(0, 1, 0))) && !isPassable(c.dim, below)) {
        found = feet;
        break;
      }
    }
    if (!found) break;
    if (!isPassable(c.dim, { x: nx, y: Math.max(found.y, cur.y) + 1, z: nz })) break;
    cur = found;
    pts.push(found);
  }
  return pts;
}
function segmentClear(c, a, b) {
  const d = dist(a, b);
  const n = Math.max(1, Math.ceil(d * 2));
  for (let i = 1; i <= n; i++) {
    const p = add(a, mul(sub(b, a), i / n));
    if (!isPassable(c.dim, p) || !isPassable(c.dim, add(p, v3(0, 1, 0)))) return false;
  }
  return true;
}
function arcPoint(a, ctrl, b, t) {
  const u = 1 - t;
  return { x: u * u * a.x + 2 * u * t * ctrl.x + t * t * b.x, y: u * u * a.y + 2 * u * t * ctrl.y + t * t * b.y, z: u * u * a.z + 2 * u * t * ctrl.z + t * t * b.z };
}

// src/spells/darkness/spells.ts
var DG = COLORS.darkgreen;
var EM = COLORS.emerald;
var JD = COLORS.jade;
var SHADE = { r: 0.02, g: 0.09, b: 0.05 };
function* dissolveLater(fx, ticks, fade = 10) {
  yield ticks;
  fx?.dissolve(fade);
}
function sheets(c, at, radius = 1, count = 1) {
  c.particle("grimoire:shadow_sheets", at, { color: SHADE, color2: EM, radius, count, size: 1.2 });
}
function primaryTarget(c, range, around = 6) {
  const a = c.aim(range);
  if (a.entity && c.isEnemy(a.entity)) return a.entity;
  return nearestEnemies(c, a.point, around, 1)[0];
}
function* umbralOrigami(c) {
  const n = c.p("sheets");
  const right = rotY(flatNorm(c.dir), 90);
  const a = c.aim(c.p("range"));
  const goal = a.point;
  const folded = [];
  for (let k = 0; k < n; k++) {
    const off = k - (n - 1) / 2;
    const start2 = add(c.origin, add(add(mul(right, off * 1.4), v3(0, 0.6 + Math.abs(off) * 0.25, 0)), mul(c.dir, 1.2)));
    folded.push({ start: start2, fx: c.fx("grimoire:fx_d_sheet", start2, { yaw: c.yaw + off * 20, phase: 1, size: c.area }), off });
    c.sound("grimoire.darkness.fold", start2, 0.6, 1.1 + k * 0.08);
    yield 2;
  }
  yield 6;
  const hits = folded.map(() => /* @__PURE__ */ new Set());
  folded.forEach((s) => s.fx?.phase(2));
  c.sound("grimoire.darkness.release", c.origin, 1, 1.2);
  const T = 12;
  for (let t = 1; t <= T + 4; t++) {
    folded.forEach((s, i) => {
      const ctrl = add(lerp(s.start, goal, 0.5), add(mul(right, s.off * 3.5), v3(0, i % 2 ? 2.5 : -0.5, 0)));
      const k = t / T;
      const p = k <= 1 ? arcPoint(s.start, ctrl, goal, k) : add(goal, mul(norm(sub(goal, ctrl)), (k - 1) * 6));
      const prev = s.fx?.location ?? s.start;
      s.fx?.move(p).aim(sub(p, prev));
      for (const e of c.along(prev, p, 1.2 * c.area)) {
        if (hits[i].has(e.id)) continue;
        hits[i].add(e.id);
        c.hit(e, c.p("damage"));
        sheets(c, bodyCenter(e), 0.6, 0.8);
      }
    });
    yield 1;
  }
  folded.forEach((s) => s.fx?.phase(15));
  yield 10;
}
function* mawOfTheUnseen(c) {
  const target = primaryTarget(c, c.p("range"));
  const base = c.ground(target ? target.location : c.aim(c.p("range")).point, 20);
  const maw = c.fx("grimoire:fx_d_maw", base, { yaw: c.yaw, phase: 1, size: c.area });
  c.particle("grimoire:shadow_fold", add(base, v3(0, 0.3, 0)), { color: SHADE, color2: EM, radius: 2.4, count: 1.5 });
  c.sound("grimoire.darkness.whisper", base, 1.1, 0.8);
  const R = c.p("radius") * c.area;
  const caught = c.enemies(base, R);
  for (const e of caught) c.bind(e, c.p("holdTicks") + 10, { pin: true, slowAmp: 6 });
  yield 12;
  maw?.phase(2);
  yield c.p("holdTicks") - 12;
  maw?.phase(3);
  c.sound("grimoire.darkness.snap", base, 1.4, 0.9);
  c.shake(base, 10, 0.4, 0.3);
  for (const e of c.enemies(base, R + 0.5)) {
    c.hit(e, c.p("damage"));
    effect(e, "slowness", 60, 2);
    sheets(c, bodyCenter(e), 1, 1.2);
  }
  yield 8;
  maw?.phase(15);
  sheets(c, add(base, v3(0, 1, 0)), 2, 2);
  yield 12;
}
function* unwrittenSentence(c) {
  const first = primaryTarget(c, c.p("range"));
  if (!first) throw new Fizzle("No target for the sentence");
  const targets = [first, ...nearestEnemies(c, first.location, 6, 3).filter((e) => e.id !== first.id)].slice(0, 3);
  const marks = /* @__PURE__ */ new Map();
  const right = rotY(flatNorm(c.dir), 90);
  const n = c.p("glyphs");
  const glyphs = [];
  for (let k = 0; k < n; k++) {
    const start2 = add(c.origin, add(add(mul(right, (k - (n - 1) / 2) * 1.5), v3(0, 1.1 + k % 2 * 0.5, 0)), mul(c.dir, 1.5)));
    glyphs.push({ start: start2, fx: c.fx("grimoire:fx_d_glyph", start2, { yaw: c.yaw, variant: k, phase: 1, size: c.area }) });
    c.sound("grimoire.darkness.glyph", start2, 0.8, 0.9 + k * 0.1);
    yield 6;
  }
  for (let k = 0; k < n; k++) {
    const g = glyphs[k];
    const tgt = targets[k % targets.length];
    g.fx?.phase(2);
    for (let t = 1; t <= 8; t++) {
      const to = tgt.isValid ? bodyCenter(tgt) : g.start;
      const p = lerp(g.start, to, t / 8);
      g.fx?.move(p).aim(sub(to, g.start));
      yield 1;
    }
    if (tgt.isValid) {
      c.hit(tgt, c.p("damage"));
      const m = marks.get(tgt.id) ?? { e: tgt, n: 0, fx: void 0 };
      m.n++;
      if (!m.fx) {
        m.fx = g.fx;
        m.fx?.phase(3);
      } else g.fx?.dissolve(6);
      marks.set(tgt.id, m);
      c.particle("grimoire:shadow_fold", bodyCenter(tgt), { color: SHADE, color2: JD, radius: 0.9, count: 0.8 });
    } else g.fx?.dissolve(6);
    for (const m of marks.values()) if (m.e.isValid) m.fx?.follow(m.e, v3(0, bodyHeight(m.e) + 0.6, 0), 0);
  }
  const fin = c.fx("grimoire:fx_d_glyph", add(c.origin, add(mul(c.dir, 2), v3(0, 1.4, 0))), { yaw: c.yaw, variant: 4, phase: 1, size: 1.5 * c.area });
  c.sound("grimoire.darkness.glyph", c.origin, 1.2, 0.6);
  yield 10;
  fin?.phase(2);
  const from = fin?.location ?? c.origin;
  for (let t = 1; t <= 8; t++) {
    const to = first.isValid ? bodyCenter(first) : from;
    fin?.move(lerp(from, to, t / 8));
    for (const m of marks.values()) if (m.e.isValid) m.fx?.follow(m.e, v3(0, bodyHeight(m.e) + 0.6, 0), 0);
    yield 1;
  }
  c.sound("grimoire.darkness.snap", first.location, 1.2, 0.7);
  for (const m of marks.values()) {
    if (m.e.isValid) {
      c.hit(m.e, c.p("finalDamage") * m.n, { immediate: true });
      c.particle("grimoire:shadow_fold", bodyCenter(m.e), { color: SHADE, color2: EM, radius: 1.6, count: 1.6 });
    }
    m.fx?.dissolve(8);
  }
  fin?.dissolve(10);
  yield 10;
}
function* sevenfoldEclipse(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("discs");
  const sky = add(point, v3(0, c.p("height"), 0));
  const discs = [];
  for (let i = 0; i < n; i++) {
    discs.push({
      disc: c.fx("grimoire:fx_d_eclipse", sky, { phase: 1, size: 0.55 * c.area }),
      umbra: c.fx("grimoire:fx_d_umbra", point, { phase: 1, size: 0.55 * c.area }),
      w: 0.05 + i * 0.011,
      ph: i * 0.9,
      ph2: i * 1.7
    });
  }
  c.sound("grimoire.darkness.eclipse", sky, 1.4, 0.8);
  yield 12;
  for (const d of discs) d.disc?.phase(2);
  const dur = c.p("duration") * 20;
  const umbraR = 4.4 * 0.55 * c.area * 1.6;
  for (let t = 0; t < dur; t++) {
    const amp = R * Math.max(0, 1 - t / dur) * 0.8;
    const pos = discs.map((d) => v3(Math.sin(t * d.w + d.ph) * amp, 0, Math.cos(t * d.w * 1.3 + d.ph2) * amp));
    discs.forEach((d, i) => {
      d.disc?.move(add(sky, add(pos[i], v3(0, (i - 3) * 0.3, 0))));
      d.umbra?.move(add(point, pos[i]));
    });
    if (t % 10 === 0) {
      for (const e of c.enemies(point, R + umbraR)) {
        const overlaps = pos.filter((p) => hdist(add(point, p), e.location) < umbraR).length;
        if (overlaps === 0) continue;
        c.hit(e, c.p("damage") * overlaps);
        if (overlaps >= 3) effect(e, "slowness", 20, 2);
      }
    }
    yield 1;
  }
  for (const d of discs) {
    d.disc?.phase(3);
    d.umbra?.phase(3);
  }
  c.sound("grimoire.darkness.thud", point, 1.6, 0.6);
  for (const p of c.dim.getPlayers({ location: point, maxDistance: umbraR + 4 })) {
    try {
      p.camera.fade({ fadeColor: { red: 0.02, green: 0.08, blue: 0.04 }, fadeTime: { fadeInTime: 0.1, holdTime: 0.25, fadeOutTime: 0.6 } });
    } catch {
    }
  }
  for (const e of c.enemies(point, umbraR)) {
    c.hit(e, c.p("fullDamage"), { immediate: true });
    effect(e, "blindness", 50, 0);
    sheets(c, bodyCenter(e), 1.2, 1.4);
  }
  yield 16;
}
function* velvetOfTheHollowKing(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_d_velvet", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.curtain", p.location, 0.9, 1.4);
  c.ward({
    label: "Velvet of the Hollow King",
    priority: 25,
    protects: (e) => e.id === p.id,
    absorb: (info) => PHYSICAL_CAUSES.has(info.cause) ? info.damage * (1 - c.p("reduction")) : info.damage * 0.85,
    react: (info) => {
      fx?.pulse();
      sheets(c, add(info.hurt.location, v3(0, 1, 0)), 0.6, 0.6);
      c.sound("grimoire.darkness.fold", info.hurt.location, 0.8, 1.3);
    }
  });
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
}
function* shadowLatch(c) {
  const p = c.player;
  const lock = c.fx("grimoire:fx_d_lock", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.latch", p.location, 0.7, 1.4);
  let attacker;
  const ward = c.ward({
    label: "Shadow Latch",
    priority: 40,
    protects: (e) => e.id === p.id && !attacker,
    absorb: (info) => {
      if (attacker || info.cause !== "entityAttack" || !info.attacker || info.projectile) return info.damage;
      if (dist(info.attacker.location, p.location) > 5) return info.damage;
      attacker = info.attacker;
      return info.damage * (1 - c.p("reduction"));
    }
  });
  yield 8;
  lock?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok && !attacker; t++) {
    lock?.follow(p, v3(0, 0.05, 0), 0);
    yield 1;
  }
  if (!attacker) return;
  ward.alive = false;
  const a = attacker;
  lock?.dissolve(6);
  const latch = c.fx("grimoire:fx_d_latch", a.location, { yaw: yawPitchOf(sub(a.location, p.location)).yaw, phase: 1, size: Math.max(0.8, bodyHeight(a) / 1.9) });
  c.particle("grimoire:shadow_fold", add(a.location, v3(0, 0.2, 0)), { color: SHADE, color2: EM, radius: 1.4, count: 1 });
  c.bind(a, c.p("holdTicks"), { pin: true, slowAmp: 7 });
  yield 5;
  latch?.phase(2);
  c.sound("grimoire.darkness.latch", a.location, 1.3, 0.8);
  c.hit(a, c.p("damage"));
  yield 6;
  latch?.phase(3);
  yield c.p("holdTicks") - 11;
}
function* curtainfallDivide(c) {
  const fwd = flatNorm(c.dir);
  const side = rotY(fwd, 90);
  const half = c.p("width") * c.area / 2;
  const curtains = [];
  for (let k = 0; k < c.p("curtains"); k++) {
    const at = c.ground(add(c.player.location, mul(fwd, 4 + k * c.p("spacing"))), 8);
    curtains.push({ at, fx: c.fx("grimoire:fx_d_curtain", at, { yaw: c.yaw, phase: 1, size: c.area }) });
    c.sound("grimoire.darkness.curtain", at, 1.1, 0.8 + k * 0.1);
    yield 5;
  }
  yield 10;
  for (const cu of curtains) cu.fx?.phase(2);
  const lastSide = /* @__PURE__ */ new Map();
  const decoys = [];
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 4 === 0) {
      for (const e of c.enemies(c.player.location, 4 + c.p("curtains") * c.p("spacing") + 6)) {
        const sides = curtains.map((cu) => Math.sign(dot(sub(e.location, cu.at), fwd)));
        const prev = lastSide.get(e.id);
        lastSide.set(e.id, sides);
        if (!prev) continue;
        curtains.forEach((cu, i) => {
          if (prev[i] === sides[i] || Math.abs(dot(sub(e.location, cu.at), side)) > half) return;
          effect(e, "blindness", 60, 0);
          effect(e, "weakness", 60, 1);
          effect(e, "slowness", 40, 1);
          sheets(c, bodyCenter(e), 0.8, 0.8);
          const lureAt = c.ground(add(e.location, mul(fwd, sides[i] * 4)), 6);
          const d = spawnDecoy(c, lureAt);
          decoys.push(d);
          lure(e, d);
          c.run(dissolveLater(d, 80, 2), "decoy");
        });
      }
      for (const a of alliesNear(c, c.player.location, 4 + c.p("curtains") * c.p("spacing") + 2)) {
        for (const cu of curtains) {
          const rel = sub(a.location, cu.at);
          if (Math.abs(dot(rel, fwd)) < 1.6 && Math.abs(dot(rel, side)) < half) effect(a, "invisibility", 30, 0);
        }
      }
    }
    yield 1;
  }
}
function mosaicJade(p, i, j) {
  if (p === 0) return i === 3 || i === 4 || j === 3 || j === 4;
  return i === j || i + j === 7 || (i === 0 || i === 7) && (j === 0 || j === 7);
}
function* duskMosaic(c) {
  const { point } = c.aimGround(c.p("range"));
  const center = v3(Math.floor(point.x) + 0.5, point.y, Math.floor(point.z) + 0.5);
  const fx = c.fx("grimoire:fx_d_mosaic", center, { yaw: 0, phase: 1 });
  c.sound("grimoire.darkness.tile", center, 1, 0.8);
  yield 20;
  let pat = 0;
  fx?.phase(2);
  const S7 = 1.25;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t > 0 && t % 50 === 0) {
      pat = 1 - pat;
      fx?.phase(pat === 0 ? 2 : 3);
      c.sound("grimoire.darkness.tile", center, 1.2, pat ? 1.1 : 0.9);
    }
    if (t % 10 === 0 && t % 50 > 18) {
      const cell = (pos) => {
        const i = Math.floor((pos.x - center.x) / S7 + 4);
        const j = Math.floor((pos.z - center.z) / S7 + 4);
        return i >= 0 && i < 8 && j >= 0 && j < 8 && Math.abs(pos.y - center.y) < 2.5 ? [i, j] : void 0;
      };
      for (const e of c.enemies(center, 7)) {
        const ij = cell(e.location);
        if (!ij || mosaicJade(pat, ij[0], ij[1])) continue;
        effect(e, "slowness", 14, c.p("slowAmp"));
        if (t % 20 === 0) c.hit(e, c.p("damage"));
      }
      for (const a of alliesNear(c, center, 7)) {
        const ij = cell(a.location);
        if (ij && mosaicJade(pat, ij[0], ij[1])) effect(a, "speed", 14, 1);
      }
    }
    yield 1;
  }
}
function* censorsSeal(c) {
  const target = primaryTarget(c, c.p("range"));
  if (!target) throw new Fizzle("No target to seal");
  const head = () => add(target.location, v3(0, bodyHeight(target) + 0.7, 0));
  const fx = c.fx("grimoire:fx_d_mask", head(), { yaw: yawPitchOf(sub(c.player.location, target.location)).yaw, phase: 1, size: Math.max(0.8, bodyHeight(target) / 1.8) });
  c.sound("grimoire.darkness.whisper", head(), 1.1, 0.7);
  const isPlayer = target.typeId === "minecraft:player";
  let decoy;
  for (let t = 0; t < c.p("duration") * 20 && target.isValid; t++) {
    fx?.follow(target, v3(0, bodyHeight(target) + 0.7, 0), 0);
    if (t % 20 === 0) {
      effect(target, "weakness", 30, 1);
      effect(target, "slowness", 30, 0);
      if (isPlayer) effect(target, "blindness", 30, 0);
    }
    if (t === 10 || t % 40 === 30) {
      if (!isPlayer) {
        decoy?.dissolve(2);
        const ang = Math.random() * 360;
        const at = c.ground(add(target.location, mul(rotY(v3(0, 0, 1), ang), c.p("decoyDistance"))), 6);
        decoy = spawnDecoy(c, at);
        lure(target, decoy);
        c.particle("grimoire:shadow_fold", add(at, v3(0, 1, 0)), { color: SHADE, color2: EM, radius: 1, count: 0.8 });
      }
      c.particle("grimoire:outline_mark", head(), { color: JD, color2: EM, radius: 0.8, count: 1 });
    }
    yield 1;
  }
  decoy?.dissolve(2);
}
function* silhouetteTraverse(c) {
  const p = c.player;
  const route = surfaceRoute(c, p.location, c.dir, c.p("range") * c.area);
  if (route.length < 4) throw new Fizzle("No surface to travel along");
  const fx = c.fx("grimoire:fx_d_silhouette", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.fold", p.location, 1, 0.8);
  effect(p, "invisibility", 40, 0);
  yield 5;
  fx?.phase(2);
  let idx = 0;
  const step2 = c.p("speed") / 0.5;
  while (idx < route.length - 1 && c.ok) {
    idx = Math.min(route.length - 1, idx + step2);
    const at = route[Math.floor(idx)];
    fx?.move(at);
    try {
      p.teleport(at, { keepVelocity: false });
    } catch {
      break;
    }
    c.particle("grimoire:shadow_print", add(at, v3(0, 0.05, 0)), { color: SHADE, color2: DG, size: 1.4, radius: p.getRotation().y * Math.PI / 180 });
    yield 1;
  }
  fx?.phase(3);
  try {
    p.removeEffect("invisibility");
  } catch {
  }
  grantFallImmunity(p.id, 20);
  c.particle("grimoire:outline_mark", add(p.location, v3(0, 1, 0)), { color: JD, color2: EM, radius: 1, count: 1.2 });
  c.sound("grimoire.darkness.step", p.location, 1, 1);
  yield 10;
}
function* stairwayOfTheUnlitSky(c) {
  const p = c.player;
  const set = c.blocks();
  const steps = [];
  let frontier = { x: Math.floor(p.location.x), z: Math.floor(p.location.z), top: Math.round(p.location.y * 2) / 2 };
  c.sound("grimoire.darkness.step", p.location, 1, 0.8);
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    grantFallImmunity(p.id, 40);
    if (t % 2 === 0) {
      const look = p.getViewDirection();
      const pitch = p.getRotation().x;
      const f = flatNorm(look);
      const dx = Math.abs(f.x) > 0.38 ? Math.sign(f.x) : 0;
      const dz = Math.abs(f.z) > 0.38 ? Math.sign(f.z) : 0;
      let placed = 0;
      while (placed < 2 && hdist(p.location, v3(frontier.x + 0.5, 0, frontier.z + 0.5)) < 2.6 && (dx || dz)) {
        const rise = pitch < -12 ? 0.5 : pitch > 30 ? -0.5 : 0;
        const next = { x: frontier.x + dx, z: frontier.z + dz, top: frontier.top + rise };
        const cellY = Math.ceil(next.top) - 1;
        const type = next.top - cellY <= 0.5 ? "grimoire:shadow_step_low" : "grimoire:shadow_step_high";
        const loc = v3(next.x, cellY, next.z);
        if (set.place(loc, type)) {
          steps.push({ loc, top: next.top });
          const sfx = c.fx("grimoire:fx_d_step", v3(next.x + 0.5, next.top, next.z + 0.5), { yaw: yawPitchOf(f).yaw, phase: 1 });
          c.run(dissolveLater(sfx, 16, 4), "step");
          c.sound("grimoire.darkness.step", loc, 0.6, 1 + rise);
        }
        frontier = next;
        placed++;
      }
      while (steps.length > c.p("keep")) {
        const old = steps.shift();
        set.remove(old.loc);
        const ffx = c.fx("grimoire:fx_d_step", v3(old.loc.x + 0.5, old.top, old.loc.z + 0.5), { phase: 3 });
        c.run(dissolveLater(ffx, 8, 2), "fold");
      }
    }
    yield 1;
  }
  const land = () => {
    if (!p.isValid) return;
    effect(p, "slow_falling", 100, 0);
    grantFallImmunity(p.id, 240);
  };
  c.onCleanup(land);
  land();
  while (steps.length) {
    const old = steps.shift();
    set.remove(old.loc);
    const ffx = c.fx("grimoire:fx_d_step", v3(old.loc.x + 0.5, old.top, old.loc.z + 0.5), { phase: 3 });
    c.run(dissolveLater(ffx, 8, 2), "fold");
    if (steps.length % 2 === 0) c.sound("grimoire.darkness.fold", old.loc, 0.4, 1.3);
    yield 2;
  }
}
function* inklessDoppelganger(c) {
  const p = c.player;
  const hist = [];
  const delay = c.p("delay");
  const fx = c.fx("grimoire:fx_d_double", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.whisper", p.location, 1, 1.2);
  sheets(c, add(p.location, v3(0, 0.2, 0)), 1, 1);
  const attacks = [];
  let tick = 0;
  const off = onAttack({ attackerId: p.id, fn: (v) => attacks.push({ due: tick + delay, victim: v }) });
  c.onCleanup(off);
  let last = p.location;
  for (tick = 0; tick < c.p("duration") * 20 && c.ok; tick++) {
    hist.push({ pos: p.location, yaw: p.getRotation().y });
    if (tick >= 16) {
      const s = hist[Math.max(0, hist.length - 1 - delay)];
      const moved = hdist(s.pos, last);
      last = s.pos;
      fx?.move(s.pos).yaw(s.yaw);
      fx?.phase(moved > 0.04 ? 3 : 2);
      while (attacks.length && attacks[0].due <= tick) {
        const a = attacks.shift();
        fx?.pulse();
        const same = a.victim.isValid && c.isEnemy(a.victim) && hdist(a.victim.location, s.pos) <= c.p("reach") + 2.5 ? a.victim : void 0;
        const victim = same ?? nearestEnemies(c, add(s.pos, v3(0, 1, 0)), c.p("reach"), 1)[0];
        if (victim && same) fx?.move(lerp(s.pos, victim.location, 0.5));
        if (victim) {
          c.hit(victim, c.p("damage"));
          push(victim, sub(victim.location, s.pos), 0.5, 0.2);
          sheets(c, bodyCenter(victim), 0.6, 0.8);
        }
        c.sound("grimoire.darkness.fold", s.pos, 0.8, 0.8);
      }
    }
    if (hist.length > delay + 4) hist.shift();
    yield 1;
  }
}
function* footfallReversal(c) {
  const target = primaryTarget(c, c.p("range"));
  if (!target) throw new Fizzle("No target to track");
  const tracker = c.fx("grimoire:fx_d_tracker", target.location, { phase: 1, size: Math.max(0.8, bodyHeight(target) / 1.9) });
  c.sound("grimoire.darkness.glyph", target.location, 1, 0.6);
  const path = [];
  for (let t = 0; t < c.p("recordTicks") && target.isValid; t++) {
    tracker?.follow(target, v3(0, 0.05, 0), 0);
    if (t % 2 === 0) path.push(target.location);
    if (t % 6 === 0) {
      const yaw = target.getRotation().y;
      c.particle("grimoire:shadow_print", add(target.location, v3(0, 0.05, 0)), { color: SHADE, color2: DG, size: 1.2, radius: yaw * Math.PI / 180 });
    }
    yield 1;
  }
  tracker?.dissolve(10);
  if (path.length < 2) return;
  const n = c.p("constructs");
  const wraiths = [];
  for (let i = 0; i < n; i++) {
    const startIdx = Math.floor((path.length - 1) * (n - i) / n);
    wraiths.push({ idx: startIdx, fx: c.fx("grimoire:fx_d_wraith", path[startIdx], { phase: 1, size: c.area }), hit: /* @__PURE__ */ new Set() });
  }
  c.sound("grimoire.darkness.fold", path[path.length - 1], 1.1, 0.7);
  yield 8;
  for (const w of wraiths) w.fx?.phase(2);
  for (let t = 0; t < 24; t++) {
    for (const w of wraiths) {
      const prev = path[w.idx];
      w.idx = Math.max(0, w.idx - 2);
      const at = path[w.idx];
      w.fx?.move(at).aim(sub(at, prev));
      for (const e of c.enemies(add(at, v3(0, 1, 0)), 1.4)) {
        if (w.hit.has(e.id)) continue;
        w.hit.add(e.id);
        c.hit(e, c.p("damage"));
      }
    }
    yield 1;
  }
  for (const w of wraiths) {
    if (target.isValid && dist(target.location, w.fx?.location ?? target.location) < 12 && !w.hit.has(target.id)) {
      w.fx?.pulse();
      w.fx?.move(lerp(w.fx?.location ?? target.location, target.location, 0.8));
      c.hit(target, c.p("damage"));
      sheets(c, bodyCenter(target), 0.7, 0.8);
      yield 3;
    }
  }
  c.sound("grimoire.darkness.snap", target.isValid ? target.location : path[0], 1, 1.1);
  yield 10;
}
function* courtOfTheUnseen(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("doors");
  const lightDir = flatNorm(sub(point, c.player.location));
  const doors = [];
  for (let k = 0; k < n; k++) {
    const ang = c.yaw + k * (360 / n) + k * 37 % 23 - 11;
    const r = R * (0.75 + k * 13 % 5 * 0.08);
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), r)), 8);
    doors.push({
      ang,
      r,
      at,
      fx: c.fx("grimoire:fx_d_door", at, { yaw: ang + 90, phase: 1, size: c.area }),
      shadow: c.fx("grimoire:fx_d_doorshadow", add(at, v3(0, 0.05, 0)), { dir: lightDir, phase: 1, size: c.area })
    });
    c.sound("grimoire.darkness.thud", at, 0.8, 0.7 + k * 0.05);
    yield 3;
  }
  c.sound("grimoire.darkness.court", point, 1.5, 0.9);
  c.fx("grimoire:fx_circle_d", add(point, v3(0, 0.07, 0)), { size: R, variant: 2, phase: 2 });
  yield 10;
  for (const d of doors) d.fx?.phase(2);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total - 60; t++) {
    if (t % 60 === 59) {
      for (const d of doors) {
        d.ang += 14;
        d.at = c.ground(add(point, mul(rotY(v3(0, 0, 1), d.ang), d.r)), 8);
      }
    }
    for (const d of doors) {
      d.fx?.move(d.at).yaw(d.ang + 90 + Math.sin(t * 0.03 + d.r) * 20);
      d.shadow?.move(add(d.at, v3(0, 0.05, 0)));
    }
    if (t % 10 === 0) {
      const inShadow = [];
      for (const e of c.enemies(point, R + 11)) {
        const shaded = doors.some((d) => {
          const rel = sub(e.location, d.at);
          const along = dot(rel, lightDir);
          return along > 0 && along < 10 * c.area && Math.abs(dot(rel, rotY(lightDir, 90))) < 1.4 * c.area;
        });
        if (shaded) {
          inShadow.push(e);
          effect(e, "slowness", 14, 2);
        }
      }
      if (t % 30 === 0) {
        for (const e of inShadow.slice(0, 6)) {
          const f = c.fx("grimoire:fx_d_fold", c.ground(e.location, 4), { yaw: Math.random() * 360, phase: 1, size: Math.max(0.8, bodyHeight(e) / 1.9) });
          c.run(dissolveLater(f, 14, 8), "fold");
          c.hit(e, c.p("foldDamage"));
          push(e, v3(0, 1, 0), 0, 0.35);
        }
        if (inShadow.length) c.sound("grimoire.darkness.snap", point, 0.9, 1.2);
      }
      for (const a of alliesNear(c, point, R + 3)) {
        if (doors.some((d) => hdist(a.location, d.at) < 2)) effect(a, "resistance", 14, 1);
      }
      for (const d of doors) for (const inc of hostileProjectiles(c, add(d.at, v3(0, 2, 0)), 2.6)) neutralize(inc);
    }
    yield 1;
  }
  for (const d of doors) d.fx?.phase(3);
  for (let t = 0; t < 30; t++) {
    for (const d of doors) {
      const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), d.ang), d.r * (1 - t / 34))), 8);
      d.fx?.move(at).yaw(d.ang + 90);
      d.shadow?.move(add(at, v3(0, 0.05, 0)));
    }
    yield 1;
  }
  for (const d of doors) {
    d.fx?.dissolve(4);
    d.shadow?.dissolve(4);
  }
  const mono = c.fx("grimoire:fx_d_monolith", point, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.darkness.court", point, 1.8, 0.6);
  yield 24;
  mono?.phase(15);
  c.shake(point, R * 3, 0.9, 0.8);
  shock(c, point, R, c.p("finalDamage"), { knock: 0.6, up: 0.1, color: EM, color2: JD, minK: 0.6, particle: "grimoire:ring_h" });
  for (let k = 0; k < 6; k++) sheets(c, add(point, v3((Math.random() - 0.5) * R, 2 + k, (Math.random() - 0.5) * R)), 2, 1.5);
  yield 26;
}
function* worldWithoutAnOutline(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const domain = c.fx("grimoire:fx_d_domain", add(point, v3(0, 0.05, 0)), { yaw: c.yaw, phase: 1, size: R / 20 * 1 });
  c.fx("grimoire:fx_circle_d", add(c.player.location, v3(0, 0.06, 0)), { size: 3, variant: 1, phase: 1 });
  c.sound("grimoire.darkness.edict", point, 2, 0.8);
  const fogged = /* @__PURE__ */ new Set();
  const fogTick = () => {
    for (const pl of c.dim.getPlayers({ location: point, maxDistance: R + 4 })) {
      if (fogged.has(pl.id)) continue;
      fogged.add(pl.id);
      try {
        pl.runCommand("fog @s push grimoire:outline_void grimoire_d15");
      } catch {
      }
    }
  };
  c.onCleanup(() => {
    for (const id of fogged) {
      const pl = c.dim.getPlayers().find((x) => x.id === id);
      try {
        pl?.runCommand("fog @s remove grimoire_d15");
      } catch {
      }
    }
  });
  fogTick();
  const marked = nearestEnemies(c, point, R, c.p("marks"));
  const outlines = marked.map((e) => ({ e, fx: c.fx("grimoire:fx_d_outline", e.location, { phase: 1, size: Math.max(0.6, bodyHeight(e) / 1.9) }) }));
  for (let t = 0; t < 40; t++) {
    for (const o of outlines) if (o.e.isValid) o.fx?.follow(o.e, v3(0, 0, 0), 0);
    if (t % 10 === 0) fogTick();
    yield 1;
  }
  domain?.phase(2);
  const replicas = marked.map((e) => ({ e, fx: c.fx("grimoire:fx_d_replica", e.location, { phase: 1, size: Math.max(0.7, bodyHeight(e) / 1.9) }) }));
  const spirePts = [0, 1, 2].map((k) => c.ground(add(point, mul(rotY(v3(0, 0, 1), c.yaw + k * 120 + 30), R * 0.45)), 10));
  c.sound("grimoire.darkness.whisper", point, 1.6, 0.6);
  for (let t = 0; t < 120 && c.ok; t++) {
    for (const o of outlines) if (o.e.isValid) o.fx?.follow(o.e, v3(0, 0, 0), 0);
    replicas.forEach((r, i) => {
      if (!r.e.isValid) return;
      const away = flatNorm(sub(r.e.location, c.player.location));
      const jitter = Math.floor(t / 4) % 2 ? 0.25 : -0.25;
      r.fx?.move(add(r.e.location, add(mul(away, 1.3), mul(rotY(away, 90), jitter)))).aim(mul(away, -1));
      if (t > 20 && (t + i * 5) % 25 === 0) {
        r.fx?.pulse();
        c.hit(r.e, c.p("replicaDamage"));
        effect(r.e, "slowness", 20, 1);
      }
    });
    if (t === 30 || t === 55 || t === 80) {
      const at = spirePts[(t - 30) / 25];
      const sp = c.fx("grimoire:fx_d_spire", at, { yaw: Math.random() * 360, phase: 1, size: c.area });
      c.run(dissolveLater(sp, 70, 12), "spire");
      for (const e of c.enemies(at, 2.6)) {
        c.hit(e, c.p("replicaDamage") * 1.6);
        push(e, sub(e.location, at), 0.9, 0.5);
      }
      c.sound("grimoire.darkness.fold", at, 1.3, 0.6);
    }
    if (t % 20 === 0) fogTick();
    yield 1;
  }
  for (const r of replicas) r.fx?.dissolve(10);
  const planes = [];
  for (let k = 0; k < 7; k++) {
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), c.yaw + k * (360 / 7)), R + 1)), 10);
    const dir = flatNorm(sub(point, at));
    planes.push({ at, dir, fx: c.fx("grimoire:fx_d_plane", at, { dir, phase: 1, size: c.area * 0.85 }) });
  }
  c.sound("grimoire.darkness.court", point, 1.8, 0.7);
  yield 20;
  for (const pl of planes) pl.fx?.phase(2);
  yield 10;
  const L = 12 * 0.85 * c.area;
  for (const pl of planes) {
    pl.fx?.phase(3);
    yield 6;
    c.sound("grimoire.darkness.thud", add(pl.at, mul(pl.dir, L * 0.5)), 1.6, 0.6);
    c.shake(point, R * 2, 0.6, 0.4);
    const side = rotY(pl.dir, 90);
    for (const e of c.enemies(point, R + 4)) {
      const rel = sub(e.location, pl.at);
      const along = dot(rel, pl.dir);
      if (along < 0 || along > L || Math.abs(dot(rel, side)) > L * 0.5) continue;
      c.hit(e, c.p("planeDamage"), { immediate: true });
      push(e, pl.dir, 0.6, -0.4);
    }
    sheets(c, add(pl.at, add(mul(pl.dir, L * 0.5), v3(0, 0.5, 0))), 3, 2);
    yield 4;
  }
  yield 8;
  for (const pl of planes) pl.fx?.phase(15);
  for (const o of outlines) o.fx?.dissolve(8);
  domain?.phase(15);
  yield 24;
}

// src/spells/darkness/index.ts
var S2 = "darkness";
var DARKNESS = [
  {
    code: "D01",
    id: "darkness.umbral_origami",
    school: S2,
    name: "Umbral Origami",
    cooldown: 7,
    charge: 10,
    enhanceable: true,
    params: { sheets: 5, damage: 6, range: 14 },
    blurb: "Paper-thin shadow sheets fold into blades and cut in from many directions.",
    cast: umbralOrigami
  },
  {
    code: "D02",
    id: "darkness.maw_of_the_unseen",
    school: S2,
    name: "Maw of the Unseen",
    cooldown: 17,
    charge: 14,
    enhanceable: true,
    params: { damage: 22, holdTicks: 24, range: 24, radius: 2.4 },
    blurb: "The shadow beneath the target splits into geometric jaws that hold it, then snap shut.",
    cast: mawOfTheUnseen
  },
  {
    code: "D03",
    id: "darkness.unwritten_sentence",
    school: S2,
    name: "The Unwritten Sentence",
    cooldown: 13,
    charge: 12,
    enhanceable: true,
    params: { glyphs: 4, damage: 5, finalDamage: 6, range: 24 },
    blurb: "Erased glyphs imprint themselves on enemies; the final glyph punishes every mark.",
    cast: unwrittenSentence
  },
  {
    code: "D04",
    id: "darkness.sevenfold_eclipse",
    school: S2,
    name: "Sevenfold Eclipse",
    cooldown: 26,
    charge: 18,
    enhanceable: true,
    params: { discs: 7, radius: 10, height: 9, damage: 2, fullDamage: 20, duration: 5, range: 30 },
    blurb: "Seven eclipse discs drift overhead; their shadows strike where they overlap, hardest at totality.",
    cast: sevenfoldEclipse
  },
  {
    code: "D05",
    id: "darkness.velvet_of_the_hollow_king",
    school: S2,
    name: "Velvet of the Hollow King",
    cooldown: 27,
    charge: 12,
    enhanceable: true,
    params: { duration: 14, reduction: 0.45 },
    blurb: "A weightless shadow cloak that folds into armour plates where you are struck.",
    cast: velvetOfTheHollowKing
  },
  {
    code: "D06",
    id: "darkness.shadow_latch",
    school: S2,
    name: "Shadow Latch",
    cooldown: 32,
    charge: 12,
    enhanceable: true,
    params: { duration: 20, holdTicks: 60, reduction: 0.6, damage: 4 },
    blurb: "The next melee attacker has its shadow pinned and is locked in place by a giant latch.",
    cast: shadowLatch
  },
  {
    code: "D07",
    id: "darkness.curtainfall_divide",
    school: S2,
    name: "Curtainfall Divide",
    cooldown: 35,
    charge: 18,
    enhanceable: true,
    params: { curtains: 3, width: 8, duration: 15, spacing: 4 },
    blurb: "Shadow curtains fall across the field, hiding allies and confusing enemies who cross them.",
    cast: curtainfallDivide
  },
  {
    code: "D08",
    id: "darkness.dusk_mosaic",
    school: S2,
    name: "Dusk Mosaic",
    cooldown: 38,
    charge: 20,
    enhanceable: true,
    params: { duration: 14, slowAmp: 3, damage: 2, range: 24 },
    blurb: "A ground mosaic of flipping plates: dark tiles bog enemies down, jade tiles speed allies.",
    cast: duskMosaic
  },
  {
    code: "D09",
    id: "darkness.censors_seal",
    school: S2,
    name: "Censor's Seal",
    cooldown: 42,
    charge: 18,
    enhanceable: true,
    params: { duration: 10, range: 24, decoyDistance: 5 },
    blurb: "A faceless mask seals the target's sight; its aim drifts toward phantoms of darkness.",
    cast: censorsSeal
  },
  {
    code: "D10",
    id: "darkness.silhouette_traverse",
    school: S2,
    name: "Silhouette Traverse",
    cooldown: 9,
    charge: 6,
    enhanceable: false,
    params: { range: 14, speed: 1.4 },
    blurb: "Flatten into your own shadow, race along the ground and rise again further ahead.",
    cast: silhouetteTraverse
  },
  {
    code: "D11",
    id: "darkness.stairway_of_the_unlit_sky",
    school: S2,
    name: "Stairway of the Unlit Sky",
    cooldown: 22,
    charge: 12,
    enhanceable: false,
    params: { duration: 12, keep: 7 },
    blurb: "Solid shadow steps unfold ahead of you as you climb; look up to rise, down to descend.",
    cast: stairwayOfTheUnlitSky
  },
  {
    code: "D12",
    id: "darkness.inkless_doppelganger",
    school: S2,
    name: "The Inkless Doppelg\xE4nger",
    cooldown: 55,
    charge: 24,
    enhanceable: true,
    params: { duration: 18, delay: 30, damage: 7, reach: 3 },
    blurb: "Your shadow rises as a faceless double that repeats your movement and attacks a moment later.",
    cast: inklessDoppelganger
  },
  {
    code: "D13",
    id: "darkness.footfall_reversal",
    school: S2,
    name: "Footfall Reversal",
    cooldown: 45,
    charge: 18,
    enhanceable: true,
    params: { recordTicks: 60, constructs: 6, damage: 7, range: 24 },
    blurb: "Record a target's footsteps, then send shadow constructs back along its path to strike.",
    cast: footfallReversal
  },
  {
    code: "D14",
    id: "darkness.court_of_the_unseen",
    school: S2,
    name: "Grand Magic: Court of the Unseen",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { doors: 7, radius: 9, duration: 20, foldDamage: 7, finalDamage: 24, range: 24 },
    blurb: "Seven frameless doors of darkness form a court whose shadows slow and strike, then fold into one.",
    cast: courtOfTheUnseen
  },
  {
    code: "D15",
    id: "darkness.world_without_an_outline",
    school: S2,
    name: "Imperial Edict: The World Without an Outline",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 18, range: 36, replicaDamage: 5, planeDamage: 16, marks: 8 },
    blurb: "Outlines vanish, shadows rise against their owners, and seven planes of darkness fold onto the field.",
    cast: worldWithoutAnOutline
  }
];

// src/spells/ice/spells.ts
import { ButtonState, EntityProjectileComponent as EntityProjectileComponent2, EntityTameableComponent as EntityTameableComponent3, InputButton, system as system10, world as world7 } from "@minecraft/server";

// src/core/state.ts
import { system as system9 } from "@minecraft/server";
var PROP = "grimoire:state";
var states = /* @__PURE__ */ new Map();
function stateOf(p) {
  let st = states.get(p.id);
  if (st) return st;
  st = {
    id: p.id,
    name: p.name,
    selected: Object.fromEntries(SCHOOLS.map((k) => [k, 0])),
    readyAt: /* @__PURE__ */ new Map(),
    activeUntilEnd: /* @__PURE__ */ new Set(),
    sneaking: p.isSneaking,
    hudKey: "",
    hudTick: 0,
    messageUntil: 0,
    message: "",
    dirty: false
  };
  try {
    const raw = p.getDynamicProperty(PROP);
    if (typeof raw === "string") {
      const saved = JSON.parse(raw);
      for (const k of SCHOOLS) {
        const v = saved.s?.[k];
        if (typeof v === "number" && v >= 0 && v < 15) st.selected[k] = Math.floor(v);
      }
      const now = system9.currentTick;
      for (const [id, remaining] of Object.entries(saved.c ?? {})) {
        if (typeof remaining === "number" && remaining > 0) st.readyAt.set(id, now + Math.min(remaining, 20 * 600));
      }
    }
  } catch (e) {
    log.warn("could not read saved grimoire state", e);
  }
  states.set(p.id, st);
  return st;
}
function save(p, st) {
  const now = system9.currentTick;
  const c = {};
  for (const [id, t] of st.readyAt) if (t > now) c[id] = t - now;
  const data = { s: st.selected, c };
  try {
    p.setDynamicProperty(PROP, JSON.stringify(data));
    st.dirty = false;
  } catch (e) {
    log.warn("could not save grimoire state", e);
  }
}
function forget(playerId) {
  states.delete(playerId);
}
function remainingTicks(st, spellId) {
  if (st.activeUntilEnd.has(spellId)) return Number.POSITIVE_INFINITY;
  const t = st.readyAt.get(spellId);
  return t === void 0 ? 0 : Math.max(0, t - system9.currentTick);
}
function startCooldown(st, spellId, seconds) {
  st.activeUntilEnd.delete(spellId);
  st.readyAt.set(spellId, system9.currentTick + Math.round(seconds * 20));
  st.dirty = true;
}
function clearCooldowns(st) {
  st.readyAt.clear();
  st.activeUntilEnd.clear();
  st.dirty = true;
}
function flash2(st, msg, ticks = 30) {
  st.message = msg;
  st.messageUntil = system9.currentTick + ticks;
  st.hudKey = "";
}

// src/spells/structures.ts
function mazeColumns(origin, cells, cell, seed, entrances = 2) {
  const r = rng(seed);
  const n = cells;
  const open = /* @__PURE__ */ new Map();
  const seen = /* @__PURE__ */ new Set();
  const key2 = (x, z) => `${x},${z}`;
  const stack = [[Math.floor(r() * n), Math.floor(r() * n)]];
  seen.add(key2(...stack[0]));
  while (stack.length) {
    const [x, z] = stack[stack.length - 1];
    const nb = [[1, 0], [-1, 0], [0, 1], [0, -1]].map(([dx, dz]) => [x + dx, z + dz]).filter(([a, b]) => a >= 0 && b >= 0 && a < n && b < n && !seen.has(key2(a, b)));
    if (!nb.length) {
      stack.pop();
      continue;
    }
    const [nx, nz] = nb[Math.floor(r() * nb.length)];
    open.set(`${Math.min(x, nx)},${Math.min(z, nz)},${nx !== x ? "e" : "s"}`, true);
    seen.add(key2(nx, nz));
    stack.push([nx, nz]);
  }
  for (let i = 0; i < n; i++) {
    const x = Math.floor(r() * (n - 1)), z = Math.floor(r() * n);
    open.set(`${x},${z},e`, true);
  }
  const cols = /* @__PURE__ */ new Map();
  const size = n * cell;
  const add2 = (lx, lz) => {
    const p = { x: Math.floor(origin.x - size / 2 + lx), y: origin.y, z: Math.floor(origin.z - size / 2 + lz) };
    cols.set(`${p.x},${p.z}`, p);
  };
  for (let i = 0; i <= n; i++) {
    for (let j = 0; j <= n; j++) {
      add2(i * cell, j * cell);
      if (i < n && !(j > 0 && j < n && open.get(`${i},${j - 1},s`))) for (let k = 1; k < cell; k++) add2(i * cell + k, j * cell);
      if (j < n && !(i > 0 && i < n && open.get(`${i - 1},${j},e`))) for (let k = 1; k < cell; k++) add2(i * cell, j * cell + k);
    }
  }
  const ent = [Math.floor(r() * n), Math.floor(r() * n)];
  for (let k = 1; k < cell; k++) {
    cols.delete(`${Math.floor(origin.x - size / 2 + ent[0] * cell + k)},${Math.floor(origin.z - size / 2)}`);
    if (entrances > 1) cols.delete(`${Math.floor(origin.x - size / 2 + ent[1] * cell + k)},${Math.floor(origin.z + size / 2)}`);
  }
  return cols;
}
function grounded(c, cols, probeUp = 4) {
  const out = [];
  for (const p of cols) {
    const g = c.ground({ x: p.x + 0.5, y: p.y + probeUp, z: p.z + 0.5 }, probeUp + 8);
    out.push({ x: p.x, y: Math.floor(g.y), z: p.z });
  }
  return out;
}
function* raise(set, cols, height, blockId, perTick = 60, layerDelay = 2) {
  for (let h = 0; h < height; h++) {
    let n = 0;
    for (const p of cols) {
      set.place({ x: p.x, y: p.y + h, z: p.z }, blockId);
      if (++n % perTick === 0) yield 1;
    }
    yield layerDelay;
  }
}
function* lower(set, perTick = 80) {
  const all = set.positions().sort((a, b) => b.y - a.y);
  let n = 0;
  for (const p of all) {
    set.remove(p);
    if (++n % perTick === 0) yield 1;
  }
}

// src/spells/ice/spells.ts
var ICE = COLORS.ice;
var WH = COLORS.white;
var CY = COLORS.cyan;
var SA = COLORS.sapphire;
function freeze(c, e, ticks) {
  c.bind(e, ticks, { shell: "grimoire:fx_i_shell", shellInit: { size: Math.max(0.8, Math.min(2.4, (e.getHeadLocation().y - e.location.y) / 1.6)) } });
  effect(e, "mining_fatigue", ticks, 2);
  c.particle("grimoire:snow_burst", bodyCenter(e), { color: ICE, color2: WH, count: 0.8 });
}
function sovereignLancePrepare(p) {
  const head = p.player.getHeadLocation();
  p.fx("grimoire:fx_i_spear", add(head, v3(0, 1.6, 0)), { dir: p.player.getViewDirection(), phase: 1 });
  p.particle("grimoire:converge", add(head, v3(0, 1.6, 0)), { color: ICE, color2: WH, radius: 3, life: 0.8, count: 2 });
  p.sound("grimoire.ice.form", head, 1, 1);
}
function* sovereignLance(c) {
  const spear = c.adopted.find((f) => f.type === "grimoire:fx_i_spear") ?? c.fx("grimoire:fx_i_spear", add(c.origin, v3(0, 1.6, 0)), { dir: c.dir, phase: 2 });
  if (spear) {
    const i = c.adopted.indexOf(spear);
    if (i >= 0) c.adopted.splice(i, 1);
    c.fxs.push(spear);
  }
  const from = add(c.origin, v3(0, 1.6, 0));
  const a = c.aim(c.p("range"));
  const dir = norm(sub(a.point, from));
  spear?.aim(dir).phase(3);
  c.sound("grimoire.ice.release", from, 1.2, 0.9);
  let end = from;
  yield* fly(c, {
    fx: spear,
    from,
    dir,
    speed: c.p("speed"),
    range: c.p("range"),
    radius: 0.9,
    pierce: c.p("pierce"),
    onHit: (e, at) => {
      c.hit(e, c.p("damage"));
      effect(e, "slowness", 60, 2);
      c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, count: 0.8 });
      c.sound("grimoire.ice.crack", at);
    },
    onTick: (pos, i) => {
      if (i % 2 === 0) c.particle("grimoire:snow_burst", pos, { color: ICE, color2: WH, radius: 0.4, count: 0.4 });
    },
    onEnd: (pos) => {
      end = pos;
    }
  });
  spear?.dissolve(4);
  const ground = c.ground(add(end, v3(0, 1, 0)), 6);
  c.sound("grimoire.ice.impact", ground, 1.3, 1);
  c.shake(ground, 16, 0.35, 0.4);
  const n = c.p("spikes");
  for (let k = 0; k <= n; k++) {
    const at = k === 0 ? ground : c.ground(add(ground, v3(Math.cos(k / n * 6.283) * 2.6 * c.area, 1, Math.sin(k / n * 6.283) * 2.6 * c.area)), 5);
    const sp = c.fx("grimoire:fx_i_spike", at, { yaw: k * 47, size: k === 0 ? 1.3 * c.area : (0.7 + k % 3 * 0.15) * c.area, phase: 1 });
    void sp;
    for (const e of c.enemies(at, c.p("spikeRadius"))) {
      c.hit(e, c.p("spikeDamage") * (k === 0 ? 1 : 0.5));
      push(e, sub(e.location, ground), 0.5, 0.55);
      effect(e, "slowness", 80, 2);
    }
    if (k % 3 === 0) yield 1;
  }
  c.particle("grimoire:shard_burst", add(ground, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 2, count: 3 });
  yield 60;
}
function* borealDragon(c) {
  const p = c.player;
  const anchor = () => add(p.location, add(rotY(v3(0, 0, -1.3), p.getRotation().y), v3(0, 3, 0)));
  const head = c.fx("grimoire:fx_i_dragon", anchor(), { dir: p.getViewDirection(), phase: 1, size: 1.1 * c.area });
  c.sound("grimoire.ice.form", p.location, 1, 0.7);
  for (let t = 0; t < 14; t++) {
    head?.move(anchor()).aim(p.getViewDirection());
    yield 1;
  }
  head?.phase(2);
  c.sound("grimoire.ice.roar", p.location, 1.6, 1);
  c.shake(p.location, 20, 0.3, 0.8);
  for (let t = 0; t < 8; t++) {
    head?.move(anchor()).aim(p.getViewDirection());
    yield 1;
  }
  head?.phase(3);
  const exposure = /* @__PURE__ */ new Map();
  const range = c.p("range") * c.area;
  const cos = Math.cos(c.p("angle") * Math.PI / 180);
  const spikes = [];
  for (let t = 0; t < c.p("duration"); t++) {
    if (!c.ok) return;
    const dir = p.getViewDirection();
    const mouth = add(anchor(), mul(dir, 3.2));
    head?.move(anchor()).aim(dir);
    for (let k = 1; k <= 4; k++) {
      const at = add(mouth, mul(dir, range * k / 4.5));
      c.particle("grimoire:streak_dir", at, { color: ICE, color2: WH, dir, speed: 1, count: 0.5, radius: k * 0.4 });
      if (t % 2 === 0) c.particle("grimoire:snow_burst", at, { color: WH, color2: CY, radius: 0.5 + k * 0.4, count: 0.5 });
    }
    if (t % 6 === 0) c.sound("grimoire.ice.breath", mouth, 0.9, 1);
    if (t % c.p("interval") === 0) {
      for (const e of c.enemies(add(mouth, mul(dir, range / 2)), range / 2 + 2)) {
        const to = sub(bodyCenter(e), mouth);
        if (len(to) > range || dot(norm(to), dir) < cos) continue;
        c.hit(e, c.p("tickDamage"));
        effect(e, "slowness", 40, 2);
        const x = (exposure.get(e.id) ?? 0) + c.p("interval");
        exposure.set(e.id, x);
        if (x >= 40) {
          freeze(c, e, 50);
          exposure.set(e.id, -60);
        }
      }
    }
    if (t % 12 === 6 && spikes.length < 6) {
      const at = c.ground(add(mouth, mul(dir, range * (0.35 + Math.random() * 0.5))), 10);
      const sp = c.fx("grimoire:fx_i_spike", at, { yaw: t * 33, size: 0.55, phase: 1 });
      if (sp) spikes.push(sp);
      for (const e of c.enemies(at, 1.6)) c.hit(e, 2);
    }
    yield 1;
  }
  head?.phase(4);
  yield 8;
}
function* wintersGuillotine(c) {
  const dir = flatNorm(c.dir);
  const L = c.p("length");
  const mid = add(c.feet, mul(dir, 3 + L / 2));
  const ground = c.ground(add(mid, v3(0, 4, 0)), 14);
  const H = 14;
  const { yaw } = yawPitchOf(dir);
  c.fx("grimoire:fx_circle_i", add(ground, v3(0, H + 3.2, 0)), { size: L / 2 + 1, variant: 1, phase: 1 });
  const blade = c.fx("grimoire:fx_i_guillotine", add(ground, v3(0, H, 0)), { yaw, len: H, phase: 1 });
  c.sound("grimoire.ice.form", ground, 1.4, 0.8);
  yield 22;
  blade?.phase(3);
  c.sound("grimoire.ice.fall", add(ground, v3(0, H / 2, 0)), 1.4, 1);
  yield 5;
  blade?.phase(4);
  c.sound("grimoire.ice.impact", ground, 1.6, 0.8);
  c.shake(ground, 30, 0.6, 0.6);
  const right = rotY(dir, 90);
  const half = c.p("width") / 2 * c.area;
  for (const e of c.enemies(ground, L / 2 + half + 1)) {
    const rel = sub(e.location, ground);
    if (Math.abs(dot(rel, dir)) <= L / 2 && Math.abs(dot(rel, right)) <= half) {
      c.hit(e, c.p("damage"));
      freeze(c, e, c.p("freeze"));
    }
  }
  for (let k = -1; k <= 1; k++) {
    const at = add(ground, mul(dir, k * L / 3));
    c.particle("grimoire:shard_burst", add(at, v3(0, 0.5, 0)), { color: ICE, color2: WH, radius: 1.5, count: 2 });
  }
  const fractures = [];
  for (const s of [-0.35, 0.05, 0.4]) fractures.push(add(ground, mul(dir, s * L)));
  for (const at of fractures) c.fx("grimoire:fx_i_fracture", add(at, v3(0, 0.02, 0)), { yaw: Math.random() * 360, size: 0.8 * c.area, phase: 1 });
  yield 10;
  for (const at of fractures) {
    for (const e of c.enemies(at, 5 * c.area)) {
      c.hit(e, c.p("fractureDamage"));
      effect(e, "slowness", 60, 1);
    }
    c.sound("grimoire.ice.crack", at, 1, 0.8);
  }
  yield 40;
  blade?.phase(15);
  yield Math.max(20, c.p("freeze") - 40);
}
function* crystalRain(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const formation = c.fx("grimoire:fx_i_swords", add(point, v3(0, 16, 0)), { phase: 1, size: R / 13 });
  c.fx("grimoire:fx_circle_i", add(point, v3(0, 15.6, 0)), { size: R, variant: 2, phase: 1 });
  c.sound("grimoire.ice.form", point, 1.5, 0.9);
  yield 22;
  const waves = c.p("waves");
  const per = Math.ceil(c.p("clusters") / waves);
  const r = rng(system10.currentTick + 17);
  for (let w = 0; w < waves; w++) {
    formation?.phase(3 + w);
    const foes = nearestEnemies(c, point, R + 2, per);
    for (let k = 0; k < per; k++) {
      const tgt = foes.length ? foes[k % foes.length] : void 0;
      const ang = r() * Math.PI * 2, rr = Math.sqrt(r()) * R;
      const land = tgt ? { ...tgt.location } : c.ground(add(point, v3(Math.cos(ang) * rr, 2, Math.sin(ang) * rr)), 6);
      c.run(volley(c, land, k * 2), "volley");
    }
    c.sound("grimoire.ice.fall", add(point, v3(0, 12, 0)), 1.2, 1.1 + w * 0.1);
    yield 12;
  }
  yield* c.join(60);
}
function* volley(c, land, delay) {
  if (delay) yield delay;
  const top = add(land, v3(0, 15, 0));
  const v = c.fx("grimoire:fx_i_volley", top, { phase: 1, yaw: Math.random() * 360 });
  for (let i = 1; i <= 5; i++) {
    v?.move(lerp(top, land, i / 5));
    yield 1;
  }
  v?.dissolve(3);
  c.particle("grimoire:shard_burst", add(land, v3(0, 0.6, 0)), { color: ICE, color2: WH, radius: 1, count: 1 });
  c.particle("grimoire:ring_h", add(land, v3(0, 0.1, 0)), { color: CY, radius: 4, life: 0.5 });
  for (const e of c.enemies(land, 2.2)) {
    c.hit(e, c.p("damage"));
    effect(e, "slowness", 40, 1);
  }
  c.sound("grimoire.ice.shatter", land, 0.7, 1.2 + Math.random() * 0.3);
}
function* eternalLotus(c) {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  const lotus = c.fx("grimoire:fx_i_lotus", center, { phase: 1, size: R / 4 });
  c.sound("grimoire.ice.chime", center, 1.2, 1);
  const cap = c.p("petalCapacity") * c.power;
  const layers = [8 * cap, 6 * cap, 5 * cap];
  let broken = 0;
  const owner = c.player;
  c.ward({
    label: "lotus",
    priority: 30,
    protects: (e) => isAllyOrSelf(owner, e) && dist(e.location, center) <= R + 0.5,
    absorb: (info) => {
      let dmg = info.damage;
      while (dmg > 0 && broken < 3) {
        const take = Math.min(dmg, layers[broken]);
        layers[broken] -= take;
        dmg -= take;
        if (layers[broken] <= 1e-3) broken++;
      }
      return dmg;
    },
    react: (info) => {
      lotus?.pulse();
      lotus?.phase(Math.min(5, 2 + broken));
      c.particle("grimoire:shard_burst", add(info.hurt.location, v3(0, 1.2, 0)), { color: ICE, color2: WH, count: 1 });
      c.sound(broken >= 3 ? "grimoire.ice.shatter" : "grimoire.ice.crack", info.hurt.location, 1, 1.2);
    }
  });
  yield 20;
  lotus?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    if (t % 30 === 0) c.particle("grimoire:snow_burst", add(center, v3(0, 1.5, 0)), { color: WH, color2: ICE, radius: R * 0.5, count: 0.6 });
    yield 1;
  }
  yield 8;
}
function* frozenThroneMirrors(c) {
  const p = c.player;
  const n = c.p("mirrors");
  const mirrors = [];
  for (let i = 0; i < n; i++) {
    mirrors.push({ fx: c.fx("grimoire:fx_i_mirror", add(p.location, v3(0, 1.4, 0)), { phase: 1 }), charges: c.p("reflects"), angle: i * 360 / n, busyUntil: 0, alive: true });
  }
  c.sound("grimoire.ice.mirror", p.location, 1, 1);
  const shatter = (m) => {
    m.alive = false;
    m.fx?.phase(3);
    const at = m.fx?.location ?? p.location;
    c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, radius: 1.5, count: 2 });
    for (const e of c.enemies(at, 3)) {
      c.hit(e, c.p("shardDamage"));
      effect(e, "slowness", 60, 1);
    }
    c.sound("grimoire.ice.shatter", at, 1, 1);
    const f = m.fx;
    system10.runTimeout(() => f?.dissolve(4), 8);
  };
  c.ward({
    label: "mirrors",
    priority: 25,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause)) return info.damage;
      const m = mirrors.find((x) => x.alive && x.charges > 0);
      if (!m) return info.damage;
      m.charges--;
      return 0;
    },
    react: () => {
      const m = mirrors.find((x) => x.alive && x.charges <= 0);
      if (m) shatter(m);
      for (const x of mirrors) if (x.alive) x.fx?.pulse();
      c.sound("grimoire.ice.reflect", p.location, 1, 1);
    }
  });
  const handled = /* @__PURE__ */ new Set();
  for (let t = 0; t < c.p("duration") * 20 && mirrors.some((m) => m.alive); t++) {
    if (!c.ok) return;
    const now = system10.currentTick;
    const center = add(p.location, v3(0, 1.3, 0));
    for (const e of c.dim.getEntities({ location: center, maxDistance: 12 })) {
      if (handled.has(e.id)) continue;
      const proj = e.getComponent(EntityProjectileComponent2.componentId);
      if (!proj || proj.owner && isAllyOrSelf(p, proj.owner)) continue;
      const vel = e.getVelocity();
      const toMe = sub(center, e.location);
      if (dot(vel, toMe) <= 0) continue;
      const m = mirrors.filter((x) => x.alive && x.charges > 0).sort((a, b) => dist(a.fx?.location ?? center, e.location) - dist(b.fx?.location ?? center, e.location))[0];
      if (!m) break;
      m.target = add(center, mul(norm(sub(e.location, center)), 1.9));
      m.busyUntil = now + 10;
      if (dist(e.location, center) < 3.2) {
        handled.add(e.id);
        const speed = Math.max(0.8, len(vel));
        const back = proj.owner?.isValid ? norm(sub(bodyCenter(proj.owner), e.location)) : norm(sub(e.location, center));
        try {
          e.clearVelocity();
          e.applyImpulse(mul(back, speed * 1.2));
          proj.owner = p;
        } catch {
        }
        m.charges--;
        m.fx?.pulse();
        c.particle("grimoire:ring_dir", m.target, { color: WH, color2: CY, radius: 2.4, dir: norm(sub(e.location, center)) });
        c.sound("grimoire.ice.reflect", m.target, 1, 1.3);
        if (m.charges <= 0) shatter(m);
      }
    }
    mirrors.forEach((m, i) => {
      if (!m.alive) return;
      const a = (m.angle + t * 2) * Math.PI / 180;
      const orbit = add(center, v3(Math.cos(a) * 2.6, 0.2 + Math.sin(t * 0.08 + i) * 0.2, Math.sin(a) * 2.6));
      const goal = m.busyUntil > now && m.target ? m.target : orbit;
      const cur = m.fx?.location ?? goal;
      const next = lerp(cur, goal, 0.45);
      m.fx?.move(next).aim(sub(next, center));
    });
    yield 1;
  }
  for (const m of mirrors) if (m.alive) shatter(m);
  yield 12;
}
function chainsOfNiflheim(c) {
  const a = c.aim(c.p("range"));
  const list = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to bind in range");
  return (function* () {
    const dur = c.p("duration") * 20;
    const items = targets.map((t) => {
      c.fx("grimoire:fx_circle_i", add(t.location, v3(0, 0.06, 0)), { size: 1.6, variant: 1, phase: 1 });
      const b = c.bind(t, dur + 10, { shell: "grimoire:fx_i_chains", shellInit: { size: Math.max(1, Math.min(2.4, (t.getHeadLocation().y - t.location.y) / 1.6)) } });
      return { t, b };
    });
    c.sound("grimoire.ice.chain", items[0].t.location, 1.2, 0.9);
    yield 12;
    for (const it of items) it.b?.shell?.phase(2);
    for (let s = 0; s < dur; s += 20) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        c.hit(it.t, c.p("dps"));
        c.particle("grimoire:snow_burst", bodyCenter(it.t), { color: ICE, color2: WH, radius: 0.6, count: 0.4 });
      }
      if (s % 40 === 0) c.sound("grimoire.ice.freeze", items[0].b?.anchor ?? c.feet, 0.8, 1.1);
      yield 20;
    }
    for (const it of items) endBind(it.b, true);
    c.sound("grimoire.ice.shatter", items[0].b?.anchor ?? c.feet, 1, 1);
    yield 10;
  })();
}
function* paleMoonLabyrinth(c) {
  const { point } = c.aimGround(c.p("range"));
  const center = { x: Math.floor(point.x) + 0.5, y: Math.floor(point.y), z: Math.floor(point.z) + 0.5 };
  const cells = 5, cell = 4, size = cells * cell;
  const set = c.blocks();
  c.fx("grimoire:fx_i_moon", add(center, v3(0, 22, 0)), { size: size / 20, phase: 1 });
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.08, 0)), { size: size * 0.7, variant: 0, phase: 1 });
  for (const [i, j] of [[0, 0], [0, 5], [5, 0], [5, 5], [2, 2], [3, 3], [0, 3], [5, 2]]) {
    const at = c.ground({ x: center.x - size / 2 + i * cell, y: center.y + 4, z: center.z - size / 2 + j * cell }, 10);
    c.fx("grimoire:fx_i_tower", at, { phase: 1, size: 0.62 });
    yield 2;
  }
  c.sound("grimoire.ice.wall", center, 1.3, 0.9);
  let seed = system10.currentTick * 3 + 1;
  let current = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
  yield* raise(set, [...current.values()], 3, "grimoire:frost_wall", 80, 2);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t > 0 && t % (c.p("shiftInterval") * 20) === 0 && set.enabled) {
      seed += 104729;
      const next = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
      for (const [k, p] of current) {
        if (next.has(k)) continue;
        for (let h = 0; h < 3; h++) set.remove({ x: p.x, y: p.y + h, z: p.z });
        if (Math.random() < 0.25) c.particle("grimoire:snow_burst", { x: p.x + 0.5, y: p.y + 1, z: p.z + 0.5 }, { color: ICE, count: 0.3 });
      }
      yield 2;
      yield* raise(set, [...next.values()].filter((p) => !current.has(`${p.x},${p.z}`)), 3, "grimoire:frost_wall", 80, 1);
      current = next;
      c.sound("grimoire.ice.wall", center, 1, 1.1);
    }
    if (t % 20 === 0) {
      for (const e of c.enemies(center, size * 0.75)) {
        const k = (dx, dz) => current.has(`${Math.floor(e.location.x + dx)},${Math.floor(e.location.z + dz)}`);
        if (k(1, 0) || k(-1, 0) || k(0, 1) || k(0, -1)) effect(e, "slowness", 30, 1);
      }
    }
    yield 1;
  }
  yield* lower(set, 100);
}
function* whiteoutDominion(c) {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.08, 0)), { size: R, variant: 0, phase: 1 });
  for (let k = 0; k < 6; k++) {
    const at = c.ground(add(center, v3(Math.cos(k / 6 * 6.283) * R, 3, Math.sin(k / 6 * 6.283) * R)), 8);
    c.fx("grimoire:fx_i_spike", at, { yaw: k * 60, size: 0.8, phase: 1 });
  }
  c.sound("grimoire.ice.blizzard", center, 1.4, 0.9);
  const fogged = /* @__PURE__ */ new Map();
  const fogOf = /* @__PURE__ */ new Map();
  const setFog = (pl, id) => {
    const cur = fogOf.get(pl.id);
    if (cur === id) return;
    try {
      if (cur) pl.runCommand("fog @s remove grimoire_i09");
      if (id) pl.runCommand(`fog @s push ${id} grimoire_i09`);
    } catch {
    }
    if (id) {
      fogOf.set(pl.id, id);
      fogged.set(pl.id, pl);
    } else fogOf.delete(pl.id);
  };
  c.onCleanup(() => {
    for (const pl of fogged.values()) if (pl.isValid) setFog(pl, void 0);
  });
  const r = rng(system10.currentTick);
  const owner = c.player;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 3 === 0) {
      for (let k = 0; k < 3; k++) {
        const ang = r() * Math.PI * 2, rr = 4 + r() * (R - 4);
        c.particle("grimoire:snow_storm", add(center, v3(Math.cos(ang) * rr, 0.5, Math.sin(ang) * rr)), { color: WH, color2: ICE, radius: 3, size: 1.4, count: 0.5 });
      }
    }
    if (t % 20 === 0) {
      for (const pl of c.dim.getPlayers({ location: center, maxDistance: R + 4 })) {
        const inside = dist(pl.location, center) <= R;
        if (pl.id === owner.id) setFog(pl, inside ? "grimoire:whiteout_caster" : void 0);
        else if (inside && c.isEnemy(pl)) {
          setFog(pl, "grimoire:whiteout");
          effect(pl, "blindness", 40, 0);
        } else setFog(pl, void 0);
      }
    }
    if (t % c.p("interval") === 0) {
      for (const e of c.enemies(center, R)) {
        c.hit(e, c.p("damage"));
        effect(e, "slowness", 30, 1);
        c.particle("grimoire:shard_burst", bodyCenter(e), { color: ICE, color2: WH, radius: 0.5, count: 0.3 });
      }
    }
    if (t % 32 === 0) c.sound("grimoire.ice.blizzard", center, 1.1, 0.9 + r() * 0.2);
    yield 1;
  }
}
function frostMirrorTraverse(c) {
  const dest = teleportDestination(c, c.p("range"));
  if (!dest) throw new Fizzle("No safe destination for the mirror");
  return (function* () {
    const p = c.player;
    const dir = flatNorm(c.dir);
    const mA = c.fx("grimoire:fx_i_mirror", add(p.location, add(mul(dir, 1.3), v3(0, 1.1, 0))), { dir: mul(dir, -1), phase: 1, size: 1.25 });
    const mB = c.fx("grimoire:fx_i_mirror", add(dest, add(mul(dir, -0.4), v3(0, 1.1, 0))), { dir, phase: 1, size: 1.25 });
    c.sound("grimoire.ice.mirror", p.location, 1, 1);
    yield 5;
    mA?.phase(4);
    mB?.phase(4);
    yield 4;
    const ok = p.tryTeleport(dest, { checkForBlocks: true, keepVelocity: false });
    if (!ok) {
      flash2(stateOf(p), "\xA77The mirror path was blocked", 30);
    }
    grantFallImmunity(p.id, 30);
    c.sound("grimoire.ice.mirror", dest, 1, 1.4);
    yield 3;
    for (const m of [mA, mB]) {
      m?.phase(3);
      if (m) c.particle("grimoire:shard_burst", m.location, { color: ICE, color2: WH, radius: 1.4, count: 1.6 });
    }
    c.sound("grimoire.ice.shatter", dest, 0.9, 1.3);
    yield 12;
  })();
}
function* winterSeraph(c) {
  const p = c.player;
  const wings = c.fx("grimoire:fx_i_wings", p.location, { yaw: p.getRotation().y, phase: 1, len: 1 });
  c.sound("grimoire.ice.wing", p.location, 1.2, 0.8);
  c.sound("grimoire.ice.summon", p.location, 0.7, 1.4);
  let lastYaw = p.getRotation().y;
  let grounded2 = 0;
  const total = c.p("duration") * 20;
  const speed = c.p("speed");
  for (let t = 0; t < total; t++) {
    if (!c.ok) break;
    const held = (() => {
      try {
        return schoolOfItem(p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex)?.typeId);
      } catch {
        return void 0;
      }
    })();
    if (held !== "ice") {
      flash2(stateOf(p), "\xA7bThe wings fold (Ice Grimoire put away)", 40);
      break;
    }
    const rot = p.getRotation();
    const look = p.getViewDirection();
    let mv = { x: 0, y: 0 };
    let jump = false;
    try {
      mv = p.inputInfo.getMovementVector();
      jump = p.inputInfo.getButtonState(InputButton.Jump) === ButtonState.Pressed;
    } catch {
    }
    const right = rotY(flatNorm(look), 90);
    let vel = add(mul(look, speed * mv.y), mul(right, -speed * 0.7 * mv.x));
    if (jump) vel = add(vel, v3(0, speed * 0.6, 0));
    if (Math.abs(mv.x) + Math.abs(mv.y) < 0.1 && !jump) vel = v3(0, 0.02, 0);
    if (t > 8) drive(p, vel);
    grantFallImmunity(p.id, 60);
    let dy = rot.y - lastYaw;
    while (dy > 180) dy -= 360;
    while (dy < -180) dy += 360;
    lastYaw = rot.y;
    wings?.follow(p, v3(0, 0, 0), 1).yaw(rot.y).length(1 + Math.max(-0.6, Math.min(0.6, dy / 10)));
    if (t === 10) wings?.phase(2);
    if (t % 14 === 0) c.sound("grimoire.ice.wing", p.location, 0.6, 0.9 + Math.random() * 0.2);
    if (t % 3 === 0) c.particle("grimoire:snow_burst", add(p.location, v3(0, 1.3, 0)), { color: WH, color2: ICE, radius: 0.8, count: 0.25 });
    grounded2 = p.isOnGround ? grounded2 + 1 : 0;
    if (t > 40 && grounded2 > 20) break;
    yield 1;
  }
  wings?.phase(3);
  effect(p, "slow_falling", 100, 0);
  grantFallImmunity(p.id, 120);
  for (let t = 0; t < 12; t++) {
    if (p.isValid) wings?.follow(p);
    yield 1;
  }
}
var KNIGHTS = ["grimoire:frost_knight_sword", "grimoire:frost_knight_spear", "grimoire:frost_knight_shield"];
function setAct(e, v) {
  try {
    if (e.isValid) e.setProperty("grimoire:act", v);
  } catch {
  }
}
function* frostLegion(c) {
  const p = c.player;
  const knights = [];
  const offsets = [v3(-2.2, 0, 1.2), v3(2.2, 0, 1.2), v3(0, 0, -2.4)];
  const yaw = p.getRotation().y;
  for (let i = 0; i < 3; i++) {
    const at = c.ground(add(p.location, add(rotY(offsets[i], yaw), v3(0, 2, 0))), 6);
    c.fx("grimoire:fx_circle_i", add(at, v3(0, 0.06, 0)), { size: 1.6, variant: 1, phase: 1 });
    c.particle("grimoire:snow_burst", add(at, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 1.5, count: 2 });
    let k;
    try {
      k = c.dim.spawnEntity(KNIGHTS[i], at, { initialRotation: yaw });
    } catch {
      continue;
    }
    k.setDynamicProperty(OWNER_PROP, p.id);
    k.setDynamicProperty(SESSION_PROP, SESSION);
    k.addTag("grimoire_summon");
    try {
      k.getComponent(EntityTameableComponent3.componentId)?.tame(p);
    } catch {
    }
    setAct(k, 4);
    knights.push(k);
    yield 4;
  }
  c.sound("grimoire.ice.summon", p.location, 1.4, 1);
  c.onCleanup(() => {
    for (const k of knights) {
      if (!k.isValid) continue;
      setAct(k, 7);
      const kk = k;
      system10.runTimeout(() => {
        try {
          if (kk.isValid) kk.remove();
        } catch {
        }
      }, 18);
    }
  });
  const hitSub = world7.afterEvents.entityHitEntity.subscribe((ev) => {
    const d = ev.damagingEntity;
    if (knights.some((k) => k.id === d.id)) {
      setAct(d, 1);
      system10.runTimeout(() => setAct(d, 0), 10);
    }
  });
  c.onCleanup(() => world7.afterEvents.entityHitEntity.unsubscribe(hitSub));
  yield 16;
  for (const k of knights) setAct(k, 0);
  const [sword, spear, shield] = [knights.find((k) => k.typeId === KNIGHTS[0]), knights.find((k) => k.typeId === KNIGHTS[1]), knights.find((k) => k.typeId === KNIGHTS[2])];
  c.ward({
    label: "bulwark",
    priority: 15,
    protects: (e) => e.id === p.id && !!shield && shield.isValid && dist(shield.location, p.location) < 8,
    absorb: (info) => PHYSICAL_CAUSES.has(info.cause) ? info.damage * 0.5 : info.damage,
    react: (info) => {
      if (!shield || !shield.isValid) return;
      setAct(shield, 3);
      system10.runTimeout(() => setAct(shield, 0), 20);
      const a = info.attacker;
      if (a && a.isValid && dist(a.location, shield.location) < 5 && c.isEnemy(a)) {
        c.hit(a, 4);
        push(a, sub(a.location, shield.location), 1.6, 0.4);
        effect(a, "slowness", 40, 2);
        c.particle("grimoire:ring_dir", bodyCenter(a), { color: ICE, color2: WH, radius: 2, dir: norm(sub(a.location, shield.location)) });
      }
    }
  });
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (!c.ok || !knights.some((k) => k.isValid)) break;
    for (const k of knights) {
      if (k.isValid && dist(k.location, p.location) > 28) {
        try {
          k.teleport(add(p.location, v3(1, 0.5, 1)));
        } catch {
        }
      }
    }
    if (sword?.isValid && t % 60 === 30) {
      const foes = c.enemies(sword.location, 3.6);
      if (foes.length) {
        setAct(sword, 2);
        system10.runTimeout(() => setAct(sword, 0), 16);
        for (const e of foes) {
          c.hit(e, 8);
          effect(e, "slowness", 40, 1);
          push(e, sub(e.location, sword.location), 0.9, 0.25);
        }
        c.particle("grimoire:ring_h", add(sword.location, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 8, life: 0.5 });
        c.sound("grimoire.ice.slash", sword.location, 1, 0.9);
      }
    }
    if (spear?.isValid && t % 80 === 50) {
      const foe = nearestEnemies(c, spear.location, 9, 1)[0];
      if (foe) {
        setAct(spear, 2);
        system10.runTimeout(() => setAct(spear, 0), 14);
        const dir = norm(sub(foe.location, spear.location));
        const from = add(spear.location, v3(0, 1.2, 0));
        try {
          spear.applyImpulse(add(mul(flatNorm(dir), 1.3), v3(0, 0.15, 0)));
        } catch {
        }
        for (const e of c.along(from, add(from, mul(dir, 7)), 1)) {
          c.hit(e, 9);
          effect(e, "slowness", 40, 2);
        }
        c.particle("grimoire:streak_dir", from, { color: WH, color2: ICE, dir, count: 1.5 });
        c.sound("grimoire.ice.slash", spear.location, 1, 1.3);
      }
    }
    if (shield?.isValid && t % 4 === 0) {
      for (const e of c.dim.getEntities({ location: p.location, maxDistance: 3.5 })) {
        const proj = e.getComponent(EntityProjectileComponent2.componentId);
        if (proj && !(proj.owner && isAllyOrSelf(p, proj.owner)) && dist(shield.location, p.location) < 8) {
          c.particle("grimoire:shard_burst", e.location, { color: ICE, count: 0.5 });
          try {
            e.remove();
          } catch {
          }
          setAct(shield, 3);
          system10.runTimeout(() => setAct(shield, 0), 14);
        }
      }
    }
    yield 1;
  }
}
function* stillWinterHourglass(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const glass = c.fx("grimoire:fx_i_hourglass", add(point, v3(0, 9, 0)), { phase: 1, size: 1.3 });
  c.fx("grimoire:fx_circle_i", add(point, v3(0, 0.08, 0)), { size: R, variant: 1, phase: 1 });
  c.sound("grimoire.ice.form", point, 1.2, 0.8);
  yield 16;
  glass?.phase(2);
  const cd = c.p("countdown");
  for (let t = 0; t < cd; t++) {
    if (t % 20 === 0) c.sound("grimoire.ice.tick", add(point, v3(0, 9, 0)), 1.2, 1 + t / cd);
    if (t % 5 === 0) {
      c.particle("grimoire:snow_still", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R * 0.6, count: 0.2 });
      for (const e of c.enemies(point, R)) effect(e, "slowness", 20, Math.min(4, Math.floor(t / cd * 4)));
    }
    yield 1;
  }
  glass?.phase(3);
  c.flash(point, R * 2.5, { r: 0.7, g: 0.9, b: 1 }, 0.1);
  c.sound("grimoire.ice.pulse", point, 1.6, 1);
  c.shake(point, R * 3, 0.5, 0.6);
  c.particle("grimoire:ring_h", add(point, v3(0, 0.3, 0)), { color: WH, color2: CY, radius: R * 2.2, life: 1.4 });
  c.particle("grimoire:snow_burst", add(point, v3(0, 2, 0)), { color: WH, color2: ICE, radius: R * 0.6, count: 4 });
  for (const e of c.enemies(point, R)) {
    c.hit(e, c.p("damage"));
    freeze(c, e, c.p("freeze"));
  }
  yield c.p("freeze");
}
function* everlastingCitadel(c) {
  const center = { x: Math.floor(c.feet.x) + 0.5, y: Math.floor(c.feet.y), z: Math.floor(c.feet.z) + 0.5 };
  const R = c.p("radius");
  const set = c.blocks();
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.07, 0)), { size: R + 2, variant: 2, phase: 1 });
  const crown = c.fx("grimoire:fx_i_crown", add(center, v3(0, 14, 0)), { phase: 1, size: 1.1 });
  c.sound("grimoire.ice.summon", center, 1.4, 0.8);
  const towers = [];
  for (let i = 0; i < 4; i++) {
    const a = i / 4 * Math.PI * 2 + Math.PI / 4;
    const at = c.ground({ x: center.x + Math.cos(a) * (R + 1), y: center.y + 4, z: center.z + Math.sin(a) * (R + 1) }, 10);
    towers.push({ fx: c.fx("grimoire:fx_i_tower", at, { phase: 1, size: 1.35 }), at });
    yield 5;
  }
  for (let i = 0; i < 4; i++) {
    const a = i / 4 * Math.PI * 2;
    const at = c.ground({ x: center.x + Math.cos(a) * R, y: center.y + 4, z: center.z + Math.sin(a) * R }, 10);
    c.fx("grimoire:fx_i_arch", at, { yaw: -a * 180 / Math.PI + 90, phase: 1, size: 0.9 });
  }
  const cols = /* @__PURE__ */ new Map();
  for (let s = 0; s < 360; s += 2) {
    const a = s * Math.PI / 180;
    if (s % 90 < 8 || s % 90 > 82) continue;
    const x = Math.floor(center.x + Math.cos(a) * R), z = Math.floor(center.z + Math.sin(a) * R);
    cols.set(`${x},${z}`, { x, y: center.y, z });
  }
  const g = grounded(c, cols.values());
  yield* raise(set, g, 4, "grimoire:frost_wall", 50, 3);
  let n = 0;
  for (const p of g) if (n++ % 2 === 0) set.place({ x: p.x, y: p.y + 4, z: p.z }, "grimoire:frost_wall");
  crown?.phase(2);
  const owner = c.player;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 20 === 0) {
      for (const e of livingNear(c.dim, center, R)) if (isAllyOrSelf(owner, e)) effect(e, "resistance", 30, 1);
    }
    if (t % c.p("interval") === 0 && t > 0) {
      for (const tw of towers) {
        const foe = nearestEnemies(c, tw.at, c.p("range"), 1)[0];
        if (!foe) continue;
        tw.fx?.pulse();
        const from = add(tw.at, v3(0, 7.5, 0));
        const dir = norm(sub(bodyCenter(foe), from));
        const lance = c.fx("grimoire:fx_i_shard", from, { dir, phase: 1, size: 1.2 });
        c.run(fly(c, {
          fx: lance,
          from,
          dir,
          speed: 1.6,
          range: c.p("range") + 8,
          radius: 0.7,
          pierce: 1,
          homing: foe,
          homingRate: 0.35,
          onHit: (e) => {
            c.hit(e, c.p("lanceDamage"));
            effect(e, "slowness", 60, 2);
          },
          onEnd: (at) => {
            lance?.dissolve(2);
            c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, count: 0.8 });
            c.sound("grimoire.ice.crack", at, 0.8, 1.2);
          }
        }), "lance");
      }
      crown?.pulse();
    }
    yield 1;
  }
  crown?.dissolve(18);
  yield* lower(set, 60);
  yield 10;
}
function* theLastWinter(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const players = c.dim.getPlayers({ location: point, maxDistance: 56 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:last_winter grimoire_i15");
    } catch {
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_i15");
      } catch {
      }
    }
  });
  const sky = c.fx("grimoire:fx_circle_i", add(point, v3(0, 28, 0)), { size: R * 1.35, variant: 2, phase: 1 });
  c.flash(point, 60, { r: 0.75, g: 0.88, b: 1 }, 0.3);
  for (let t = 0; t < 60; t++) {
    if (t % 10 === 0) {
      c.particle("grimoire:snow_still", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R, count: 1.5 });
      for (const e of c.enemies(point, R)) effect(e, "slowness", 30, 3);
    }
    yield 1;
  }
  c.sound("grimoire.ice.chime", point, 1.6, 0.6);
  const crown = c.fx("grimoire:fx_i_crown", add(point, v3(0, 20, 0)), { phase: 1, size: 2.4 });
  yield 24;
  crown?.phase(2);
  for (let wave = 0; wave < 4; wave++) {
    const foes = nearestEnemies(c, point, R, 6);
    const spots = foes.length ? foes.map((e) => ({ ...e.location })) : [0, 1, 2].map((k) => c.ground(add(point, v3(Math.cos(k * 2.1 + wave) * R * 0.5, 3, Math.sin(k * 2.1 + wave) * R * 0.5)), 8));
    crown?.pulse();
    for (const s of spots) {
      const from = add(point, v3(0, 18, 0));
      const to = add(s, v3(0, 0.5, 0));
      const dir = norm(sub(to, from));
      c.fx("grimoire:fx_i_beam", from, { dir, len: dist(from, to), phase: 1, size: 0.9 });
      c.particle("grimoire:beam_up", to, { color: WH, color2: CY, radius: 1.5, size: 1.4, count: 1 });
      for (const e of c.enemies(to, 2.5)) {
        c.hit(e, c.p("beamDamage"));
        freeze(c, e, 40);
      }
      if (wave % 2 === 0) {
        for (let k = 0; k < 3; k++) {
          c.fx("grimoire:fx_i_spike", c.ground(add(s, v3(Math.cos(k * 2.09) * 2.2, 2, Math.sin(k * 2.09) * 2.2)), 5), { yaw: k * 120, size: 0.9, phase: 1 });
        }
      }
    }
    c.sound("grimoire.ice.beam", point, 1.4, 1 + wave * 0.1);
    yield 16;
  }
  const fall = 30;
  const moon = c.fx("grimoire:fx_i_moon_crystal", add(point, v3(0, 6 + fall, 0)), { phase: 1, len: fall, size: Math.max(1, R / 16) });
  c.sound("grimoire.ice.descent", point, 2, 1);
  yield 30;
  moon?.phase(3);
  for (let t = 0; t < 40; t++) {
    if (t % 10 === 0) c.shake(point, 60, 0.15 + t / 120, 0.5);
    yield 1;
  }
  moon?.phase(4);
  crown?.dissolve(12);
  sky?.phase(3);
  c.flash(point, 80, { r: 0.85, g: 0.95, b: 1 }, 0.2);
  c.sound("grimoire.ice.pulse", point, 2, 0.7);
  c.sound("grimoire.ice.shatter", point, 2, 0.6);
  for (let k = 0; k < 3; k++) {
    c.particle("grimoire:ring_h", add(point, v3(0, 0.5 + k, 0)), { color: WH, color2: CY, radius: R * (1.2 + k * 0.5), life: 1.5 });
    c.particle("grimoire:shard_burst", add(point, v3(0, 3, 0)), { color: ICE, color2: WH, radius: 4 + k * 2, count: 4 });
  }
  shock(c, point, R, c.p("finalDamage"), { knock: 2, up: 0.7, shake: 1, minK: 0.3, color: WH, color2: CY });
  for (const e of c.enemies(point, R)) freeze(c, e, 80);
  for (let t = 0; t < 100; t++) {
    if (t % 12 === 0) c.particle("grimoire:mist", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R * 0.5, size: 2.5, count: 1.5, life: 2 });
    if (t === 10) {
      for (let k = 0; k < 6; k++) c.fx("grimoire:fx_i_spike", c.ground(add(point, v3(Math.cos(k) * R * 0.6, 3, Math.sin(k) * R * 0.6)), 6), { yaw: k * 60, size: 0.5, phase: 1 });
    }
    yield 1;
  }
}

// src/spells/ice/index.ts
var S3 = "ice";
var ICE2 = [
  {
    code: "I01",
    id: "ice.sovereign_lance",
    school: S3,
    name: "Glacial Sovereign's Lance",
    cooldown: 8,
    charge: 12,
    enhanceable: true,
    params: { damage: 12, spikeDamage: 8, range: 48, speed: 1.8, spikes: 8, spikeRadius: 2.2, pierce: 3 },
    blurb: "A crystalline spear that pierces, then erupts into giant ice spikes.",
    prepare: sovereignLancePrepare,
    cast: sovereignLance
  },
  {
    code: "I02",
    id: "ice.boreal_dragon",
    school: S3,
    name: "Boreal Dragon's Roar",
    cooldown: 20,
    charge: 16,
    enhanceable: true,
    params: { duration: 80, range: 18, angle: 14, tickDamage: 3, interval: 5 },
    blurb: "A crystal dragon head breathes a freezing gale.",
    cast: borealDragon
  },
  {
    code: "I03",
    id: "ice.winters_guillotine",
    school: S3,
    name: "Winter's Guillotine",
    cooldown: 14,
    charge: 14,
    enhanceable: true,
    params: { damage: 18, length: 20, width: 3.2, freeze: 60, fractureDamage: 4 },
    blurb: "An ice blade falls from a sky circle and fractures the ground.",
    cast: wintersGuillotine
  },
  {
    code: "I04",
    id: "ice.crystal_rain",
    school: S3,
    name: "Thousandfold Crystal Rain",
    cooldown: 25,
    charge: 20,
    enhanceable: true,
    params: { swords: 120, waves: 4, clusters: 20, damage: 6, radius: 10, range: 40 },
    blurb: "Concentric rings of crystal swords rain down in waves.",
    cast: crystalRain
  },
  {
    code: "I05",
    id: "ice.eternal_lotus",
    school: S3,
    name: "Lotus of the Eternal Frost",
    cooldown: 28,
    charge: 14,
    enhanceable: true,
    params: { radius: 4, layers: 3, petalCapacity: 2.5, duration: 12 },
    blurb: "A crystal lotus whose petals shatter as they absorb attacks.",
    cast: eternalLotus
  },
  {
    code: "I06",
    id: "ice.frozen_throne_mirror",
    school: S3,
    name: "Mirror of the Frozen Throne",
    cooldown: 32,
    charge: 14,
    enhanceable: true,
    params: { mirrors: 4, reflects: 3, shardDamage: 6, duration: 15 },
    blurb: "Hexagonal mirrors intercept and reflect projectiles.",
    cast: frozenThroneMirrors
  },
  {
    code: "I07",
    id: "ice.chains_of_niflheim",
    school: S3,
    name: "Chains of Niflheim",
    cooldown: 30,
    charge: 16,
    enhanceable: true,
    params: { targets: 4, duration: 7, dps: 2, range: 32, selectRadius: 8 },
    blurb: "Crystal chains bind enemies and freeze their joints.",
    cast: chainsOfNiflheim
  },
  {
    code: "I08",
    id: "ice.pale_moon_labyrinth",
    school: S3,
    name: "Labyrinth of the Pale Moon",
    cooldown: 40,
    charge: 20,
    enhanceable: true,
    params: { duration: 18, size: 10, range: 24, shiftInterval: 5 },
    blurb: "Frozen walls and towers form a shifting labyrinth.",
    cast: paleMoonLabyrinth
  },
  {
    code: "I09",
    id: "ice.whiteout_dominion",
    school: S3,
    name: "Whiteout Dominion",
    cooldown: 45,
    charge: 20,
    enhanceable: true,
    params: { radius: 14, duration: 12, damage: 3, interval: 15 },
    blurb: "A supernatural blizzard that only spares its caster.",
    cast: whiteoutDominion
  },
  {
    code: "I10",
    id: "ice.frost_mirror_traverse",
    school: S3,
    name: "Frost Mirror Traverse",
    cooldown: 8,
    charge: 8,
    enhanceable: false,
    params: { range: 20 },
    blurb: "Step into one mirror and out of another.",
    cast: frostMirrorTraverse
  },
  {
    code: "I11",
    id: "ice.winter_seraph",
    school: S3,
    name: "Wings of the Winter Seraph",
    cooldown: 20,
    charge: 14,
    enhanceable: false,
    cooldownAfterEnd: true,
    params: { duration: 15, speed: 0.75 },
    blurb: "Six crystal wings grant controllable flight. Cooldown starts after landing.",
    cast: winterSeraph
  },
  {
    code: "I12",
    id: "ice.frost_legion",
    school: S3,
    name: "Imperial Frost Legion",
    cooldown: 60,
    charge: 24,
    enhanceable: true,
    params: { duration: 30 },
    blurb: "Summon three crystal knights: longsword, spear and greatshield.",
    cast: frostLegion
  },
  {
    code: "I13",
    id: "ice.still_winter_hourglass",
    school: S3,
    name: "Hourglass of Still Winter",
    cooldown: 50,
    charge: 18,
    enhanceable: true,
    params: { radius: 10, countdown: 80, damage: 10, freeze: 100, range: 36 },
    blurb: "When the hourglass empties, a great pulse freezes all enemies.",
    cast: stillWinterHourglass
  },
  {
    code: "I14",
    id: "ice.everlasting_citadel",
    school: S3,
    name: "Grand Magic: Citadel of the Everlasting Winter",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { radius: 12, duration: 30, lanceDamage: 9, interval: 40, range: 24 },
    blurb: "An imperial ice palace rises; its towers fire ice lances.",
    cast: everlastingCitadel
  },
  {
    code: "I15",
    id: "ice.the_last_winter",
    school: S3,
    name: "Imperial Edict: The Last Winter",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 22, range: 40, beamDamage: 8, finalDamage: 30 },
    blurb: "Silent world, crown of absolute frost, then the final descent.",
    cast: theLastWinter
  }
];

// src/spells/plasma/spells.ts
import { system as system11 } from "@minecraft/server";
var VI = COLORS.violet;
var MG = COLORS.magenta;
var UV = COLORS.ultraviolet;
var IN = COLORS.indigo;
var WH2 = COLORS.whitehot;
function filamentLine(c, a, b, n, color = VI, color2 = MG) {
  for (let i = 0; i <= n; i++) c.particle("grimoire:plasma_trail", lerp(a, b, i / n), { color, color2, size: 1, count: 0.5 });
}
function* coronalLash(c) {
  const hand = () => add(c.eye(), add(mul(c.look(), 0.5), v3(0, -0.45, 0)));
  const whip = c.fx("grimoire:fx_pl_whip", hand(), { yaw: c.yaw, pitch: c.pitch, phase: 1, size: c.area });
  c.sound("grimoire.plasma.hum", hand(), 0.9, 1.3);
  for (let t = 0; t < 10; t++) {
    whip?.move(hand());
    if (t % 3 === 0) c.particle("grimoire:plasma_charge", hand(), { color: VI, color2: MG, size: 1, radius: 1 });
    yield 1;
  }
  whip?.phase(2);
  const reach = c.p("reach") * c.area;
  const sweeps = [
    { ph: 3, a0: -80, a1: 80, axis: "yaw" },
    { ph: 4, a0: 80, a1: -80, axis: "yaw" },
    { ph: 5, a0: -70, a1: 30, axis: "pitch" }
  ];
  for (const s of sweeps) {
    whip?.move(hand()).yaw(c.player.getRotation().y).pitch(c.player.getRotation().x);
    whip?.phase(s.ph);
    c.sound("grimoire.plasma.whip", hand(), 1, 0.9 + s.ph * 0.08);
    const hitIds = /* @__PURE__ */ new Set();
    const baseYaw = c.player.getRotation().y;
    const basePitch = c.player.getRotation().x;
    for (let t = 0; t <= 7; t++) {
      const k = t / 7;
      const ang = s.a0 + (s.a1 - s.a0) * k;
      const yaw = s.axis === "yaw" ? baseYaw + ang : baseYaw;
      const pitch = s.axis === "pitch" ? Math.max(-80, Math.min(80, basePitch + ang)) : basePitch;
      const dir = dirFromYawPitch(yaw, pitch);
      const side = s.axis === "yaw" ? rotY(flatNorm(dir), 90) : v3(0, 1, 0);
      const o = hand();
      for (let d = 1; d <= reach; d += 1) {
        const p = add(add(o, mul(dir, d)), mul(side, Math.sin(d * 0.75 - k * 4) * 0.35 * d * 0.25));
        if (t % 2 === 0 && d % 2 === 0) c.particle("grimoire:plasma_trail", p, { color: d % 4 ? VI : MG, color2: WH2, size: 1.2, count: 0.5, life: 1.6 });
        for (const e of c.enemies(p, c.p("width"))) {
          if (hitIds.has(e.id)) continue;
          hitIds.add(e.id);
          c.hit(e, c.p("damage"));
          push(e, s.axis === "yaw" ? mul(side, Math.sign(s.a1 - s.a0)) : dir, 0.7, s.axis === "pitch" ? -0.2 : 0.25);
          c.particle("grimoire:plasma_arc", bodyCenter(e), { color: MG, color2: WH2, radius: 0.8, count: 1 });
        }
      }
      whip?.move(hand());
      yield 1;
    }
    yield 2;
  }
  whip?.phase(15);
  yield 10;
}
function* helixBorer(c) {
  const a = c.aim(c.p("range"));
  const start2 = add(c.origin, mul(c.dir, 1.6));
  const dir = norm(sub(a.point, start2));
  const fx = c.fx("grimoire:fx_pl_borer", start2, { dir, phase: 1, size: c.area });
  c.sound("grimoire.plasma.drill", start2, 0.9, 0.8);
  yield 8;
  fx?.phase(2);
  let victim;
  let end = start2;
  yield* fly(c, {
    fx,
    from: start2,
    dir,
    speed: c.p("speed"),
    range: c.p("range"),
    radius: 0.9 * c.area,
    pierce: 1,
    homing: a.entity,
    homingRate: 0.3,
    trail: "grimoire:plasma_trail",
    trailColor: VI,
    trailColor2: MG,
    onHit: (e) => victim = e,
    onEnd: (pos) => end = pos
  });
  if (victim?.isValid) {
    fx?.phase(3);
    c.sound("grimoire.plasma.drill", end, 1.3, 1.2);
    for (let i = 0; i < c.p("hits") && victim.isValid; i++) {
      const vc = bodyCenter(victim);
      const back = norm(sub(vc, c.player.location));
      fx?.move(sub(vc, mul(back, 0.7))).aim(back);
      c.hit(victim, c.p("damage"), { immediate: i % 2 === 0 });
      effect(victim, "slowness", 10, 3);
      c.particle("grimoire:plasma_arc", vc, { color: MG, color2: WH2, radius: 0.7, count: 1 });
      yield 5;
    }
    end = victim.isValid ? bodyCenter(victim) : end;
  }
  fx?.phase(4);
  c.sound("grimoire.plasma.crack", end, 1.2, 0.9);
  c.particle("grimoire:plasma_burst", end, { color: VI, color2: WH2, radius: 1.4, count: 1.5 });
  for (const e of c.enemies(end, 3)) if (e.id !== victim?.id) c.hit(e, c.p("fragmentDamage"));
  yield 12;
}
function* prominenceUprising(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const right = rotY(flatNorm(c.dir), 90);
  const fx = c.fx("grimoire:fx_pl_prominence", point, { yaw: c.yaw + 90, phase: 1, size: R / 3.5 });
  c.sound("grimoire.plasma.surge", point, 1.3, 1);
  for (let t = 0; t < 14; t++) {
    for (const sgn of [-1, 1]) c.particle("grimoire:plasma_arc", add(point, add(mul(right, sgn * R), v3(0, 0.3 + t * 0.2, 0))), { color: VI, color2: MG, radius: 0.8, count: 0.6, dir: v3(0, 1, 0) });
    yield 1;
  }
  fx?.phase(2);
  const lifted = c.enemies(point, R);
  for (const e of lifted) {
    effect(e, "levitation", c.p("liftTicks"), 1);
    c.hit(e, c.p("liftDamage"));
  }
  for (let t = 0; t < c.p("liftTicks"); t++) {
    if (t % 5 === 0) {
      for (const e of lifted) if (e.isValid) pullToward(e, add(point, v3(0, 3, 0)), 0.15);
    }
    if (t % 6 === 0) c.particle("grimoire:plasma_arc", add(point, v3(0, 3.5, 0)), { color: MG, color2: WH2, radius: 1.8, count: 1 });
    yield 1;
  }
  fx?.phase(3);
  c.sound("grimoire.plasma.reconnect", point, 1, 1.4);
  yield 6;
  for (const e of lifted) {
    if (!e.isValid) continue;
    try {
      e.removeEffect("levitation");
    } catch {
    }
    drive(e, v3(0, -1.6, 0));
  }
  shock(c, point, R, c.p("damage"), { knock: 1.1, up: 0.2, color: VI, color2: WH2, shake: 0.6, minK: 0.6 });
  c.particle("grimoire:plasma_burst", add(point, v3(0, 0.5, 0)), { color: MG, color2: WH2, radius: 2.4, count: 2 });
  yield 16;
}
function* arcShearCascade(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("membranes");
  const dur = c.p("duration") * 20;
  const paths = [];
  for (let i = 0; i < n; i++) {
    const dir = rotY(v3(0, 0, 1), c.yaw + 45 + i * (180 / n) * 1.6);
    const perp = rotY(dir, 90);
    const off = (i - (n - 1) / 2) * 1.7;
    const a = add(add(point, mul(dir, -R)), mul(perp, off));
    const b = add(add(point, mul(dir, R)), mul(perp, -off * 0.5));
    paths.push({ a, b, hit: /* @__PURE__ */ new Set(), delay: i * 6, fx: c.fx("grimoire:fx_pl_membrane", a, { dir: flatNorm(sub(b, a)), phase: 1, size: c.area }) });
  }
  c.sound("grimoire.plasma.membrane", point, 1.2, 1);
  yield 10;
  for (const p of paths) p.fx?.phase(2);
  const erupted = /* @__PURE__ */ new Set();
  for (let t = 0; t < dur + 6 * n; t++) {
    const pos = paths.map((p) => {
      const k = Math.max(0, Math.min(1, (t - p.delay) / dur));
      return lerp(p.a, p.b, k);
    });
    paths.forEach((p, i) => {
      p.fx?.move(pos[i]).yaw(yawPitchOf(sub(p.b, p.a)).yaw + Math.sin((t + i * 7) * 0.15) * 25);
      const fwd = flatNorm(sub(p.b, p.a));
      const side = rotY(fwd, 90);
      for (const e of c.enemies(pos[i], 2.6)) {
        if (p.hit.has(e.id)) continue;
        const rel = sub(e.location, pos[i]);
        if (Math.abs(dot(rel, side)) < 1.8 * c.area && Math.abs(dot(rel, fwd)) < 0.9) {
          p.hit.add(e.id);
          c.hit(e, c.p("damage"));
          push(e, fwd, 0.6, 0.2);
        }
      }
    });
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const key2 = `${i}:${j}`;
        if (erupted.has(key2) || t < paths[j].delay) continue;
        if (hdist(pos[i], pos[j]) < 2.2) {
          erupted.add(key2);
          const at = c.ground(lerp(pos[i], pos[j], 0.5), 6);
          const fl = c.fx("grimoire:fx_pl_flare", at, { phase: 1, size: 1.2 * c.area });
          c.run(dissolveLater2(fl, 26), "flare");
          c.blast(at, 3, c.p("intersectionDamage"));
          c.particle("grimoire:plasma_burst", add(at, v3(0, 1, 0)), { color: WH2, color2: VI, radius: 1.6, count: 1.5 });
          c.sound("grimoire.plasma.crack", at, 1.2, 0.8);
        }
      }
    yield 1;
  }
  yield 6;
}
function* dissolveLater2(fx, ticks) {
  yield ticks;
  fx?.dissolve(10);
}
function* stellaratorWard(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_stellarator", p.location, { phase: 1, size: c.area });
  c.sound("grimoire.plasma.field", p.location, 1, 1.2);
  c.ward({
    label: "Stellarator Ward",
    priority: 30,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (info.cause === "projectile") return 0;
      return PHYSICAL_CAUSES.has(info.cause) ? info.damage * (1 - c.p("reduction")) : info.damage;
    },
    react: () => fx?.pulse()
  });
  yield 10;
  fx?.phase(2);
  const curving = [];
  const seen = /* @__PURE__ */ new Set();
  const R = c.p("radius") * c.area;
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p, v3(0, 0, 0));
    if (t % 2 === 0) {
      for (const inc of hostileProjectiles(c, p.location, R + 3, seen)) {
        const to = sub(bodyCenter(p), inc.e.location);
        if (dot(inc.vel, to) <= 0) continue;
        seen.add(inc.e.id);
        const spin = Math.random() < 0.5 ? 1 : -1;
        redirect(inc, add(rotY(flatNorm(inc.vel), 80 * spin), v3(0, 0.25, 0)), 0.9, p);
        curving.push({ inc, until: system11.currentTick + 6, spin });
        fx?.pulse();
        c.sound("grimoire.plasma.zap", inc.e.location, 0.8, 1.4);
      }
    }
    for (let i = curving.length - 1; i >= 0; i--) {
      const q = curving[i];
      if (!q.inc.e.isValid) {
        curving.splice(i, 1);
        continue;
      }
      q.inc.vel = q.inc.e.getVelocity();
      redirect(q.inc, rotY(flatNorm(q.inc.vel), 25 * q.spin), 1);
      c.particle("grimoire:plasma_trail", q.inc.e.location, { color: MG, color2: WH2, size: 1, count: 0.5 });
      if (system11.currentTick >= q.until) {
        c.particle("grimoire:plasma_burst", q.inc.e.location, { color: VI, color2: WH2, radius: 0.6, count: 0.6 });
        neutralize(q.inc);
        curving.splice(i, 1);
      }
    }
    yield 1;
  }
}
function* coronaMolt(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_molt", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.plasma.hum", p.location, 0.8, 1.6);
  let triggered;
  const ward = c.ward({
    label: "Corona Molt",
    priority: 60,
    protects: (e) => e.id === p.id && !triggered,
    absorb: (info) => {
      if (triggered || info.damage < c.p("threshold")) return info.damage;
      if (!PHYSICAL_CAUSES.has(info.cause) && info.cause !== "magic") return info.damage;
      triggered = { attacker: info.attacker, at: info.hurt.location };
      return Math.max(0, info.damage - c.p("maxAbsorb") * c.power);
    }
  });
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok && !triggered; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
  if (!triggered) return;
  ward.alive = false;
  const at = triggered.at;
  const away = triggered.attacker?.isValid ? flatNorm(sub(at, triggered.attacker.location)) : flatNorm(mul(c.look(), -1));
  fx?.phase(3);
  fx?.move(add(at, mul(away, -0.4)));
  c.sound("grimoire.plasma.crack", at, 1.3, 0.7);
  c.flash(at, 10, { r: 0.85, g: 0.5, b: 1 }, 0.08);
  c.particle("grimoire:plasma_burst", add(at, v3(0, 1, 0)), { color: MG, color2: WH2, radius: 2.2, count: 2 });
  for (const e of c.enemies(at, c.p("radius"))) {
    c.hit(e, c.p("damage"));
    push(e, sub(e.location, at), 1.3, 0.35);
    effect(e, "slowness", 50, 2);
    effect(e, "weakness", 60, 0);
  }
  yield 18;
}
function* fieldlineHarp(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("anchors");
  const anchors = [];
  for (let i = 0; i < n; i++) {
    const ang = c.yaw + 360 * i / n;
    anchors.push(add(c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), R)), 6), v3(0, 1.1 + i % 2 * 1, 0)));
  }
  for (const a of anchors) {
    c.fx("grimoire:fx_pl_anchor", sub(a, v3(0, 1, 0)), { phase: 1 });
    c.particle("grimoire:plasma_arc", a, { color: VI, color2: MG, radius: 0.6, count: 0.6 });
    yield 2;
  }
  c.sound("grimoire.plasma.hum", point, 1.1, 0.8);
  const pairs = [];
  for (let i = 0; i < n; i++) pairs.push([i, (i + 1) % n]);
  for (let i = 0; i < n / 2; i++) pairs.push([i, i + n / 2]);
  const strings = pairs.map(([i, j]) => {
    const a = anchors[i], b = anchors[j];
    const fx = c.fx("grimoire:fx_pl_string", a, { dir: sub(b, a), len: dist(a, b), phase: 1 });
    return { a, b, fx, last: /* @__PURE__ */ new Map() };
  });
  yield 10;
  for (const s of strings) s.fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 2 === 0) {
      for (const s of strings) {
        for (const e of c.along(s.a, s.b, 0.8)) {
          const last = s.last.get(e.id) ?? -99;
          if (t - last < 20) continue;
          s.last.set(e.id, t);
          s.fx?.pulse();
          c.sound("grimoire.plasma.zap", bodyCenter(e), 0.9, 0.8 + Math.random() * 0.4);
          for (const v of c.along(s.a, s.b, 1.3)) {
            c.hit(v, c.p("damage"));
            effect(v, "slowness", 40, 2);
          }
          filamentLine(c, s.a, s.b, Math.ceil(dist(s.a, s.b)), MG, WH2);
        }
      }
    }
    yield 1;
  }
}
function* polarityOrchestra(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("pylons");
  const pylons = [];
  for (let i = 0; i < n; i++) {
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), c.yaw + 360 * i / n), R)), 6);
    pylons.push({ at, fx: c.fx("grimoire:fx_pl_pylon", at, { phase: 1, size: c.area }) });
    yield 2;
  }
  c.sound("grimoire.plasma.pylon", point, 1.2, 0.8);
  yield 8;
  const patterns = [
    [1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1],
    [1, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 1]
  ];
  let pat = patterns[0];
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 30 === 0) {
      pat = patterns[t / 30 % patterns.length];
      pylons.forEach((p, i) => p.fx?.phase(pat[i % 6] ? 3 : 4));
      c.sound("grimoire.plasma.pylon", point, 1, pat[0] ? 1.2 : 0.8);
      for (const e of c.enemies(point, R + 2)) {
        const atPylon = pylons.some((p, i) => pat[i % 6] && dist(p.at, e.location) < 2.6);
        c.hit(e, c.p("damage") * (atPylon ? 2 : 1));
        c.particle("grimoire:plasma_arc", bodyCenter(e), { color: atPylon ? WH2 : MG, color2: VI, radius: 0.7, count: 0.8 });
      }
    }
    if (t % 4 === 0) {
      for (const e of c.enemies(point, R + 2)) {
        let force = v3(0, 0, 0);
        pylons.forEach((p, i) => {
          const d = sub(add(p.at, v3(0, 1, 0)), e.location);
          const dd = len(d);
          if (dd > 7 || dd < 0.6) return;
          const k = (1 - dd / 7) * (pat[i % 6] ? 1 : -1);
          force = add(force, mul(flatNorm(d), k));
        });
        if (len(force) > 0.05) drive(e, mul(force, c.p("force") * 0.25));
      }
    }
    yield 1;
  }
}
function* staticHorizon(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const plane = add(point, v3(0, c.p("height"), 0));
  const fx = c.fx("grimoire:fx_pl_horizon", plane, { yaw: c.yaw, phase: 1, size: R / 10 });
  c.sound("grimoire.plasma.field", plane, 1.3, 0.7);
  yield 16;
  fx?.phase(2);
  const seen = /* @__PURE__ */ new Set();
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 2 === 0) {
      for (const inc of hostileProjectiles(c, plane, R + 1, seen)) {
        if (hdist(inc.e.location, plane) > R || Math.abs(inc.e.location.y - plane.y) > 3) continue;
        seen.add(inc.e.id);
        const v = flatNorm(inc.vel);
        redirect(inc, add(rotY(v, (Math.random() - 0.5) * 220), v3(0, 0.6, 0)), 0.5, c.player);
        c.particle("grimoire:plasma_arc", inc.e.location, { color: IN, color2: WH2, radius: 0.6, count: 0.6 });
      }
    }
    if (t % 30 === 15) {
      fx?.pulse();
      c.sound("grimoire.plasma.zap", plane, 0.9, 0.6);
      for (const e of c.enemies(point, R)) {
        if (e.location.y > plane.y + 1) continue;
        effect(e, "slowness", 40, 2);
        effect(e, "weakness", 40, 0);
        c.hit(e, c.p("damage"));
        c.particle("grimoire:plasma_trail", bodyCenter(e), { color: IN, color2: VI, size: 1.3, count: 1 });
      }
    }
    yield 1;
  }
}
function* ionSkates(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_skates", p.location, { yaw: c.yaw, phase: 1, len: 1 });
  c.sound("grimoire.plasma.skate", p.location, 1, 1);
  let lastYaw = c.yaw;
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    effect(p, "speed", 25, c.p("speed"));
    grantFallImmunity(p.id, 30);
    const v = p.getVelocity();
    const hs = Math.hypot(v.x, v.z);
    const moveYaw = hs > 0.05 ? yawPitchOf(v3(v.x, 0, v.z)).yaw : p.getRotation().y;
    const dy = (moveYaw - lastYaw + 540) % 360 - 180;
    lastYaw = moveYaw;
    fx?.follow(p, v3(0, 0.02, 0)).yaw(moveYaw).length(1 + Math.min(1.5, hs * 3));
    if (t > 6) fx?.phase(Math.abs(dy) < 3 ? 2 : dy > 0 ? 4 : 3);
    if (hs > 0.08 && t % 2 === 0) c.particle("grimoire:plasma_trail", add(p.location, v3(0, 0.1, 0)), { color: VI, color2: WH2, size: 0.9, count: 0.5, life: 2 });
    if (hs > 0.08 && p.isOnGround && t % 5 === 0) drive(p, v3(v.x / hs * c.p("boost"), 0, v.z / hs * c.p("boost")));
    if (t % 30 === 0 && hs > 0.1) c.sound("grimoire.plasma.skate", p.location, 0.6, 1 + hs);
    yield 1;
  }
}
function* prominenceSling(c) {
  const p = c.player;
  const fwd = flatNorm(c.dir);
  const behind = add(p.location, mul(fwd, -1.4));
  const fx = c.fx("grimoire:fx_pl_sling", behind, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.sling", behind, 1.2, 1);
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < 12 && c.ok; t++) {
    if (t < 6) drive(p, mul(fwd, -0.12));
    c.particle("grimoire:plasma_charge", add(behind, v3(0, 2.2, 0)), { color: VI, color2: MG, radius: 1.5, size: 1 });
    yield 1;
  }
  if (!c.ok) return;
  const look = c.look();
  const launchDir = norm(add(flatNorm(look), v3(0, Math.max(0.25, -look.y * 0 + 0.35), 0)));
  const free = freeDistance(c.dim, c.eye(), launchDir, 14);
  const k = Math.max(0.35, Math.min(1, free / 12));
  fx?.phase(3);
  c.sound("grimoire.plasma.surge", p.location, 1.1, 1.4);
  grantFallImmunity(p.id, 200);
  drive(p, add(mul(flatNorm(look), c.p("power") * 0.5 * k), v3(0, c.p("lift") * k, 0)));
  const tail = c.fx("grimoire:fx_pl_tail", p.location, { yaw: c.yaw, phase: 1 });
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    const v = p.getVelocity();
    tail?.follow(p, v3(0, 0.2, 0));
    if (len(v) > 0.05) tail?.aim(mul(v, -1));
    if (t % 2 === 0) c.particle("grimoire:plasma_trail", add(p.location, v3(0, 0.8, 0)), { color: MG, color2: VI, size: 1.2, count: 1, life: 2 });
    if (t > 8 && p.isOnGround) break;
    yield 1;
  }
  c.particle("grimoire:plasma_burst", p.location, { color: VI, color2: WH2, radius: 1, count: 0.8 });
}
function* auroralManta(c) {
  const p = c.player;
  let pos = add(p.location, v3(0, 4.5, 0));
  const fx = c.fx("grimoire:fx_pl_manta", pos, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.manta", pos, 1.3, 1);
  for (let t = 0; t < 24; t++) {
    if (t % 3 === 0) c.particle("grimoire:plasma_charge", pos, { color: VI, color2: MG, radius: 3, size: 1.5 });
    yield 1;
  }
  fx?.phase(2);
  let orbit = c.yaw;
  let nextDive = 8;
  let nextTail = 30;
  const range = c.p("range");
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    const home = add(p.location, add(mul(rotY(v3(0, 0, 1), orbit), 3.6), v3(0, 4.5, 0)));
    orbit += 3;
    const target = nearestEnemies(c, p.location, range, 1)[0];
    if (target && t >= nextDive) {
      fx?.phase(3);
      c.sound("grimoire.plasma.whip", pos, 1.2, 0.6);
      const from = pos;
      for (let i = 1; i <= 12; i++) {
        const goal = target.isValid ? bodyCenter(target) : from;
        const ctrl = add(lerp(from, goal, 0.5), v3(0, 3.5, 0));
        const np = arcPoint(from, ctrl, goal, i / 12);
        fx?.move(np).aim(sub(np, pos));
        pos = np;
        if (i % 2 === 0) c.particle("grimoire:plasma_trail", pos, { color: VI, color2: MG, size: 1.5, count: 1 });
        yield 1;
      }
      if (target.isValid) {
        c.hit(target, c.p("diveDamage"));
        push(target, sub(target.location, from), 1, 0.45);
        c.particle("grimoire:plasma_burst", bodyCenter(target), { color: MG, color2: WH2, radius: 1.4, count: 1.4 });
        c.sound("grimoire.plasma.crack", pos, 1.1, 1);
      }
      const back = pos;
      for (let i = 1; i <= 12; i++) {
        const goal = add(p.location, v3(0, 4.5, 0));
        const np = arcPoint(back, add(lerp(back, goal, 0.5), v3(0, 4, 0)), goal, i / 12);
        fx?.move(np).aim(sub(np, pos));
        pos = np;
        yield 1;
      }
      fx?.phase(2);
      nextDive = t + 24 + 70;
      nextTail = t + 24 + 30;
      t += 24;
      continue;
    }
    pos = lerp(pos, home, 0.2);
    fx?.move(pos).yaw(orbit + 90).pitch(0);
    if (target && t >= nextTail && dist(pos, bodyCenter(target)) < range) {
      fx?.pulse();
      const tc = bodyCenter(target);
      filamentLine(c, pos, tc, Math.ceil(dist(pos, tc) * 1.5), MG, WH2);
      c.hit(target, c.p("tailDamage"));
      c.sound("grimoire.plasma.zap", tc, 1, 1.1);
      nextTail = t + 40;
    }
    yield 1;
  }
}
function* magneticReconnection(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const right = rotY(flatNorm(c.dir), 90);
  const top = add(point, v3(0, 3, 0));
  const loops = [-1, 1].map(
    (sgn) => c.fx("grimoire:fx_pl_fieldloop", add(top, mul(right, sgn * 6)), { yaw: c.yaw + 90, phase: sgn > 0 ? 2 : 3, size: c.area })
  );
  const xp = c.fx("grimoire:fx_pl_xpoint", add(point, v3(0, 4.2, 0)), { yaw: c.yaw, phase: 1, size: c.area });
  const seal = c.fx("grimoire:fx_circle_pl", add(point, v3(0, 0.06, 0)), { size: R / 1, variant: 1, phase: 1 });
  c.sound("grimoire.plasma.field", top, 1.3, 0.6);
  const delay = c.p("delay");
  for (let t = 0; t < delay; t++) {
    const k = t / delay;
    loops.forEach((l, i) => l?.move(add(top, mul(right, (i ? 1 : -1) * (6 - 4 * k)))));
    if (t === 10) xp?.phase(2);
    if (t % 10 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 14, 1);
        pullToward(e, point, 0.12);
      }
      c.particle("grimoire:plasma_charge", add(point, v3(0, 4.2, 0)), { color: WH2, color2: MG, radius: 2.5, size: 1.5 });
    }
    yield 1;
  }
  xp?.phase(3);
  seal?.phase(3);
  for (const l of loops) l?.phase(4);
  c.sound("grimoire.plasma.reconnect", point, 1.5, 1);
  c.shake(point, 20, 0.7, 0.6);
  c.flash(point, 18, { r: 0.9, g: 0.6, b: 1 }, 0.06);
  shock(c, point, R * 0.6, c.p("damage"), { knock: 1.3, up: 0.45, color: WH2, color2: VI, minK: 0.6 });
  const n = c.p("jets");
  const jetLen = c.p("jetLength") * c.area;
  for (let i = 0; i < n; i++) {
    const dir = norm(add(rotY(v3(0, 0, 1), c.yaw + 360 * i / n + 15), v3(0, -0.12, 0)));
    const from = add(point, v3(0, 1.4, 0));
    const jet = c.fx("grimoire:fx_pl_jet", from, { dir, len: jetLen, phase: 1, size: c.area });
    c.run(dissolveLater2(jet, 18), "jet");
    for (const e of c.along(from, add(from, mul(dir, jetLen)), 1.6)) {
      c.hit(e, c.p("jetDamage"));
      push(e, dir, 1, 0.3);
    }
  }
  yield 24;
}
function* stellaratorCathedral(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const apex = add(point, v3(0, c.p("height"), 0));
  const fx = c.fx("grimoire:fx_pl_cathedral", apex, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.surge", apex, 1.6, 0.6);
  for (let t = 0; t < 40; t++) {
    if (t % 4 === 0) filamentLine(c, add(c.player.location, v3(0, 1.5, 0)), apex, 8, VI, MG);
    yield 1;
  }
  fx?.phase(2);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total - 50; t++) {
    if (t % 20 === 0) {
      for (const e of c.dim.getPlayers({ location: point, maxDistance: c.p("allyRadius") })) {
        if (e.id === c.player.id || !c.isEnemy(e)) effect(e, "resistance", 30, 1);
      }
      c.particle("grimoire:plasma_trail", add(point, v3(0, 0.3, 0)), { color: IN, color2: WH2, size: 2, count: 3, radius: c.p("allyRadius") });
    }
    if (t % c.p("interval") === 0) {
      for (const e of nearestEnemies(c, point, R, c.p("targets"))) {
        const from = add(apex, v3(0, -1.6, 0));
        const to = bodyCenter(e);
        const br = c.fx("grimoire:fx_pl_branch", from, { dir: sub(to, from), len: dist(from, to), phase: 1 });
        c.run(dissolveLater2(br, 10), "branch");
        c.hit(e, c.p("streamDamage"));
        c.particle("grimoire:plasma_arc", to, { color: MG, color2: WH2, radius: 0.8, count: 1 });
      }
      c.sound("grimoire.plasma.zap", apex, 1.2, 0.7);
    }
    yield 1;
  }
  fx?.phase(3);
  c.sound("grimoire.plasma.drill", apex, 1.5, 0.5);
  yield 30;
  const n = c.p("beams");
  for (let i = 0; i < n; i++) {
    const dir = norm(add(rotY(v3(0, 0, 1), c.yaw + 360 * i / n), v3(0, -0.75, 0)));
    const from = add(apex, v3(0, -1, 0));
    const bm = c.fx("grimoire:fx_pl_beam", from, { dir, len: c.p("beamLength"), phase: 1, size: c.area });
    c.run(dissolveLater2(bm, 20), "beam");
    for (const e of c.along(from, add(from, mul(dir, c.p("beamLength"))), 1.8)) c.hit(e, c.p("beamDamage"));
  }
  c.sound("grimoire.plasma.reconnect", point, 1.6, 1.2);
  c.shake(point, 24, 0.8, 0.8);
  c.flash(point, 22, { r: 0.85, g: 0.55, b: 1 }, 0.1);
  yield 20;
}
function* heavenwideReconnection(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const sky = add(point, v3(0, c.p("height"), 0));
  c.sound("grimoire.plasma.surge", c.player.location, 1.6, 0.5);
  c.fx("grimoire:fx_circle_pl", add(c.player.location, v3(0, 0.06, 0)), { size: 3, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_pl", add(point, v3(0, 0.08, 0)), { size: R, variant: 0, phase: 2 });
  for (let t = 0; t < 14; t++) {
    for (let k = 0; k < 3; k++) {
      const off = rotY(v3(0, 0, 1), c.yaw + t * 26 + k * 120);
      c.particle("grimoire:plasma_trail", add(c.player.location, add(mul(off, 1.2), v3(0, 1 + t * 0.8, 0))), { color: k ? VI : MG, color2: WH2, size: 1.6, count: 1, life: 2 });
    }
    yield 1;
  }
  const net = c.fx("grimoire:fx_pl_network", sky, { yaw: c.yaw, phase: 1, size: R / 16 * 1 });
  c.shake(point, 30, 0.4, 1.5);
  yield 44;
  net?.phase(2);
  c.sound("grimoire.plasma.field", point, 1.6, 0.5);
  const junctions = /* @__PURE__ */ new Map();
  for (let t = 0; t < 100 && c.ok; t++) {
    if (t % 20 === 0) {
      for (const e of nearestEnemies(c, point, R, 8)) {
        if (!junctions.has(e.id)) junctions.set(e.id, { e, fx: c.fx("grimoire:fx_pl_junction", add(e.location, v3(0, 3, 0)), { phase: 1, size: c.area }) });
        const from = add(sky, v3((Math.random() - 0.5) * 6, -1, (Math.random() - 0.5) * 6));
        filamentLine(c, from, bodyCenter(e), 10, MG, WH2);
        c.bind(e, 26, { pin: true, slowAmp: 3 });
        c.hit(e, c.p("streamDamage"));
      }
      c.sound("grimoire.plasma.zap", sky, 1.4, 0.6);
    }
    for (const j of junctions.values()) if (j.e.isValid) j.fx?.follow(j.e, v3(0, 3, 0), 0);
    yield 1;
  }
  net?.phase(3);
  yield 14;
  net?.phase(4);
  c.sound("grimoire.plasma.reconnect", point, 2, 0.8);
  c.flash(point, R * 2, { r: 0.9, g: 0.75, b: 1 }, 0.12);
  c.shake(point, R * 3, 1, 1.2);
  for (const j of junctions.values()) {
    j.fx?.pulse();
    if (j.e.isValid) {
      c.hit(j.e, c.p("junctionDamage"), { immediate: true });
      c.particle("grimoire:plasma_burst", bodyCenter(j.e), { color: WH2, color2: MG, radius: 1.8, count: 1.6 });
    }
  }
  const jets = [0, 90, 180, 270].map((a) => ({ a, fx: c.fx("grimoire:fx_pl_sweepjet", add(sky, v3(0, -2, 0)), { yaw: c.yaw + a, pitch: 32, len: R * 1.15, phase: 1, size: c.area }), hit: /* @__PURE__ */ new Set() }));
  for (let t = 0; t < 24; t++) {
    jets.forEach((j, i) => {
      const yaw = c.yaw + j.a + t * 4.5;
      const dir = dirFromYawPitch(yaw, 32);
      j.fx?.yaw(yaw);
      const from = add(sky, v3(0, -2, 0));
      for (const e of c.along(from, add(from, mul(dir, R * 1.15)), 2)) {
        if (j.hit.has(e.id)) continue;
        j.hit.add(e.id);
        c.hit(e, c.p("jetDamage"));
        push(e, flatNorm(dir), 0.8, 0.3);
      }
      if (t % 4 === i) c.particle("grimoire:plasma_burst", c.ground(add(from, mul(dir, R)), 14), { color: VI, color2: WH2, radius: 1.6, count: 1 });
    });
    yield 1;
  }
  for (const j of jets) j.fx?.dissolve(12);
  for (const j of junctions.values()) j.fx?.dissolve(12);
  net?.phase(15);
  for (let t = 0; t < 26; t++) {
    if (t % 3 === 0) c.particle("grimoire:plasma_trail", add(sky, v3((Math.random() - 0.5) * R, (Math.random() - 0.5) * 4, (Math.random() - 0.5) * R)), { color: MG, color2: VI, size: 2, count: 2, life: 2 });
    yield 1;
  }
}

// src/spells/plasma/index.ts
var S4 = "plasma";
var PLASMA = [
  {
    code: "PL01",
    id: "plasma.coronal_lash",
    school: S4,
    name: "Coronal Lash",
    cooldown: 7,
    charge: 10,
    enhanceable: true,
    params: { damage: 7, reach: 8, width: 1.4 },
    blurb: "Three plasma filaments braid into a whip that strikes in three S-curved sweeps.",
    cast: coronalLash
  },
  {
    code: "PL02",
    id: "plasma.helix_borer",
    school: S4,
    name: "Helix Borer",
    cooldown: 12,
    charge: 12,
    enhanceable: true,
    params: { damage: 4, hits: 8, range: 36, speed: 1.4, fragmentDamage: 4 },
    blurb: "Counter-rotating helices around a white-hot core drill repeatedly into one target.",
    cast: helixBorer
  },
  {
    code: "PL03",
    id: "plasma.prominence_uprising",
    school: S4,
    name: "Prominence Uprising",
    cooldown: 19,
    charge: 16,
    enhanceable: true,
    params: { radius: 5, liftTicks: 40, damage: 16, liftDamage: 4, range: 32 },
    blurb: "Twin prominence arches lift enemies inside their formation, then collapse onto them.",
    cast: prominenceUprising
  },
  {
    code: "PL04",
    id: "plasma.arc_shear_cascade",
    school: S4,
    name: "Arc-Shear Cascade",
    cooldown: 24,
    charge: 18,
    enhanceable: true,
    params: { membranes: 4, damage: 6, intersectionDamage: 10, radius: 9, range: 30, duration: 3 },
    blurb: "Folding plasma membranes sweep the field; where two cross, the plasma erupts.",
    cast: arcShearCascade
  },
  {
    code: "PL05",
    id: "plasma.stellarator_ward",
    school: S4,
    name: "Stellarator Ward",
    cooldown: 25,
    charge: 14,
    enhanceable: true,
    params: { duration: 14, radius: 3.2, reduction: 0.35 },
    blurb: "A twisted toroidal confinement field curves incoming projectiles around you.",
    cast: stellaratorWard
  },
  {
    code: "PL06",
    id: "plasma.corona_molt",
    school: S4,
    name: "Corona Molt",
    cooldown: 30,
    charge: 12,
    enhanceable: true,
    params: { duration: 20, threshold: 3, maxAbsorb: 14, radius: 5, damage: 6 },
    blurb: "A plasma skin sheds one strong blow as an expanding afterimage that blasts nearby foes.",
    cast: coronaMolt
  },
  {
    code: "PL07",
    id: "plasma.fieldline_harp",
    school: S4,
    name: "Fieldline Harp",
    cooldown: 29,
    charge: 18,
    enhanceable: true,
    params: { anchors: 6, radius: 6, duration: 12, damage: 6, range: 28 },
    blurb: "Plasma strings between floating anchors resonate and pulse when enemies cross them.",
    cast: fieldlineHarp
  },
  {
    code: "PL08",
    id: "plasma.polarity_orchestra",
    school: S4,
    name: "Polarity Orchestra",
    cooldown: 38,
    charge: 20,
    enhanceable: true,
    params: { pylons: 6, radius: 7, duration: 10, damage: 3, force: 0.7, range: 30 },
    blurb: "Six magnetic pylons switch polarity in rhythm, pulling and pushing enemies between them.",
    cast: polarityOrchestra
  },
  {
    code: "PL09",
    id: "plasma.static_horizon",
    school: S4,
    name: "Static Horizon",
    cooldown: 42,
    charge: 20,
    enhanceable: true,
    params: { radius: 10, duration: 14, height: 2.6, damage: 3, range: 30 },
    blurb: "A low interference membrane scatters projectiles and slows everything beneath it.",
    cast: staticHorizon
  },
  {
    code: "PL10",
    id: "plasma.ion_skates",
    school: S4,
    name: "Ion Skates",
    cooldown: 10,
    charge: 6,
    enhanceable: false,
    params: { duration: 8, speed: 3, boost: 0.35 },
    blurb: "Plasma skates with energy fins: glide fast along the ground for 8 seconds.",
    cast: ionSkates
  },
  {
    code: "PL11",
    id: "plasma.prominence_sling",
    school: S4,
    name: "Prominence Sling",
    cooldown: 18,
    charge: 14,
    enhanceable: false,
    params: { power: 3.2, lift: 1.15, duration: 3 },
    blurb: "A celestial slingshot draws you back and launches you on a long arc.",
    cast: prominenceSling
  },
  {
    code: "PL12",
    id: "plasma.auroral_manta",
    school: S4,
    name: "Living Circuit: The Auroral Manta",
    cooldown: 55,
    charge: 24,
    enhanceable: true,
    params: { duration: 22, diveDamage: 10, tailDamage: 5, range: 16 },
    blurb: "A manta of living plasma circles above you, diving at enemies and lashing with its tail.",
    cast: auroralManta
  },
  {
    code: "PL13",
    id: "plasma.magnetic_reconnection",
    school: S4,
    name: "Magnetic Reconnection",
    cooldown: 45,
    charge: 22,
    enhanceable: true,
    params: { radius: 7, jets: 6, jetLength: 9, damage: 18, jetDamage: 10, range: 32, delay: 50 },
    blurb: "Two opposing field structures meet; their filaments break and reconnect in violent jets.",
    cast: magneticReconnection
  },
  {
    code: "PL14",
    id: "plasma.stellarator_cathedral",
    school: S4,
    name: "Grand Magic: Stellarator Cathedral",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { radius: 12, duration: 20, streamDamage: 8, interval: 25, targets: 4, beams: 6, beamDamage: 18, beamLength: 14, height: 9, range: 24, allyRadius: 5 },
    blurb: "A floating twisted confinement cathedral strikes with branching streams, then fires its beams.",
    cast: stellaratorCathedral
  },
  {
    code: "PL15",
    id: "plasma.heavenwide_reconnection",
    school: S4,
    name: "Imperial Edict: Heavenwide Reconnection",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 16, range: 40, streamDamage: 5, junctionDamage: 14, jetDamage: 16, height: 12 },
    blurb: "The sky becomes a living plasma network that confines, then reconnects in sweeping jets.",
    cast: heavenwideReconnection
  }
];

// src/spells/pressure/spells.ts
import { EntityProjectileComponent as EntityProjectileComponent3, system as system12 } from "@minecraft/server";
var OR = COLORS.orange;
var GD = COLORS.gold;
var WH3 = COLORS.white;
var CU = COLORS.copper;
function* pressureLance(c) {
  const dir = c.dir;
  const start2 = add(c.origin, add(mul(dir, 1.8), v3(0, -0.25, 0)));
  const fx = c.fx("grimoire:fx_p_lance", start2, { dir, phase: 1, size: c.empowered ? 1.35 : 1 });
  c.sound("grimoire.pressure.lance", start2);
  c.particle("grimoire:converge", start2, { color: OR, color2: GD, radius: 2.4, life: 0.35, count: 1.5 });
  yield 6;
  fx?.phase(2);
  c.particle("grimoire:ring_dir", start2, { color: GD, color2: WH3, radius: 3.2, dir });
  c.shake(start2, 8, 0.15, 0.2);
  let end = start2;
  yield* fly(c, {
    fx,
    from: start2,
    dir,
    speed: c.p("speed"),
    range: c.p("range"),
    radius: c.p("radius") * c.area,
    pierce: Infinity,
    onHit: (e, at) => {
      c.hit(e, c.p("damage"));
      push(e, dir, 1.3, 0.3);
      c.particle("grimoire:ring_dir", at, { color: OR, color2: GD, radius: 2.6, dir });
      c.particle("grimoire:spark_burst", at, { color: GD, color2: WH3, radius: 1, count: 1 });
      c.sound("grimoire.pressure.thud", at, 0.9, 1.2);
    },
    onTick: (pos, i) => {
      if (i % 2 === 0) c.particle("grimoire:ring_dir", pos, { color: OR, radius: 1.2 + Math.min(2.5, i * 0.12), dir, life: 1.2 });
      if (i % 3 === 1) c.particle("grimoire:ripple_dir", pos, { color: WH3, radius: 2, dir, life: 1.4 });
    },
    onEnd: (pos) => {
      end = pos;
    }
  });
  fx?.phase(3);
  shock(c, end, c.p("impactRadius"), c.p("impactDamage"), { knock: 1.1, up: 0.35, sound: "grimoire.pressure.boom", shake: 0.35 });
  c.particle("grimoire:ring_dir", end, { color: WH3, color2: OR, radius: 6, dir });
  yield 8;
}
function* atlasPiston(c) {
  const { point } = c.aimGround(c.p("range"));
  const h = c.p("height");
  const R = c.p("radius") * c.area;
  const circle = c.fx("grimoire:fx_circle_p", add(point, v3(0, 0.06, 0)), { size: R, variant: 1, phase: 1 });
  const piston = c.fx("grimoire:fx_p_piston", add(point, v3(0, h, 0)), { len: h, phase: 1, size: c.area });
  c.sound("grimoire.pressure.rise", point, 1.2, 1.2);
  for (let t = 0; t < 26; t++) {
    if (t % 6 === 0) {
      c.particle("grimoire:converge", add(point, v3(0, 1, 0)), { color: OR, color2: GD, radius: R, life: 0.6 });
      for (const e of c.enemies(point, R)) effect(e, "slowness", 30, 1);
    }
    if (t === 20) circle?.phase(3);
    yield 1;
  }
  piston?.phase(3);
  c.sound("grimoire.pressure.whoosh", add(point, v3(0, h / 2, 0)), 1.2, 0.7);
  yield 6;
  piston?.phase(4);
  circle?.pulse();
  shock(c, point, R, c.p("damage"), { knock: 1.6, up: c.p("launch"), sound: "grimoire.pressure.slam", shake: 0.9, minK: 0.55 });
  c.particle("grimoire:glow_flash", add(point, v3(0, 0.5, 0)), { color: GD, size: 6 });
  c.flash(point, 18, { r: 1, g: 0.75, b: 0.4 }, 0.05);
  let inner = R;
  for (let k = 1; k <= 2; k++) {
    yield 6;
    const r = R + (c.p("waveRadius") * c.area - R) * (k / 2);
    c.particle("grimoire:ring_h", add(point, v3(0, 0.2, 0)), { color: OR, color2: WH3, radius: r * 2.2, life: 1.2 });
    c.particle("grimoire:dust_ring", point, { color: { r: 0.7, g: 0.62, b: 0.5 }, radius: r * 0.45, size: 1.5, count: 1.5 });
    for (const e of c.enemies(point, r)) {
      if (dist(e.location, point) < inner - 0.5) continue;
      c.hit(e, c.p("waveDamage"));
      push(e, sub(e.location, point), 1.2, 0.45);
    }
    inner = r;
    c.sound("grimoire.pressure.thud", point, 1, 0.8 - k * 0.1);
  }
  yield 10;
  piston?.phase(5);
  yield 18;
}
function* isobaricSeverance(c) {
  const dir = flatNorm(c.dir);
  const { yaw } = yawPitchOf(dir);
  let pos = add(c.feet, add(mul(dir, 1.5), v3(0, 1, 0)));
  const fx = c.fx("grimoire:fx_p_blade", pos, { yaw, phase: 1, size: c.area });
  c.sound("grimoire.pressure.whoosh", pos, 1.2, 1.3);
  yield 4;
  fx?.phase(2);
  const half = c.p("width") / 2 * c.area;
  const right = rotY(dir, 90);
  const hitIds = /* @__PURE__ */ new Set();
  const eruptions = [];
  let travelled = 0;
  const range = c.p("range");
  let step2 = 0;
  while (travelled < range) {
    const next = add(pos, mul(dir, c.p("speed")));
    if (freeDistance(c.dim, pos, dir, c.p("speed") + 0.2) < c.p("speed") - 0.1) break;
    for (const e of c.enemies(lerp(pos, next, 0.5), half + 2)) {
      if (hitIds.has(e.id)) continue;
      const rel = sub(e.location, pos);
      if (Math.abs(dot(rel, right)) <= half + 0.3 && Math.abs(e.location.y + 0.9 - pos.y) < 2.6 && dot(rel, dir) < c.p("speed") + 0.6) {
        hitIds.add(e.id);
        c.hit(e, c.p("damage"));
        push(e, dir, 0.6, 0.15);
        c.particle("grimoire:spark_burst", bodyCenter(e), { color: OR, color2: WH3, count: 1.2 });
      }
    }
    if (step2 % 2 === 0) {
      for (const s of [-0.66, 0, 0.66]) eruptions.push({ at: c.ground(add(next, mul(right, half * s)), 6), tick: system12.currentTick + c.p("delay") });
    }
    fx?.move(next);
    pos = next;
    travelled += c.p("speed");
    step2++;
    yield* erupt(c, eruptions);
    yield 1;
  }
  fx?.dissolve(8);
  for (let i = 0; i < 30 && eruptions.length; i++) {
    yield* erupt(c, eruptions);
    yield 1;
  }
}
function* erupt(c, list) {
  const now = system12.currentTick;
  for (let i = list.length - 1; i >= 0; i--) {
    if (list[i].tick > now) continue;
    const e = list.splice(i, 1)[0];
    c.particle("grimoire:ring_h", add(e.at, v3(0, 0.15, 0)), { color: OR, color2: GD, radius: 5, life: 0.8 });
    c.particle("grimoire:beam_up", e.at, { color: GD, color2: WH3, radius: 1.2, size: 0.8, count: 0.6 });
    for (const t of c.enemies(e.at, 2.6)) {
      c.hit(t, c.p("delayedDamage"));
      push(t, v3(0, 0, 0), 0, 0.55);
    }
    c.sound("grimoire.pressure.thud", e.at, 0.7, 1.3);
  }
}
function* cataclysmSalvo(c) {
  const p = c.player;
  const wings = c.fx("grimoire:fx_p_salvo", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.pressure.rise", p.location, 0.9, 1.6);
  const aim = c.aimGround(c.p("range"));
  for (let t = 0; t < 16; t++) {
    wings?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
  wings?.phase(3);
  const discs = c.p("discs");
  const volleys = c.p("volleys");
  const perVolley = Math.ceil(discs / volleys);
  const r = rng(system12.currentTick);
  for (let v = 0; v < volleys; v++) {
    const targets = nearestEnemies(c, aim.point, 14, 12);
    for (let k = 0; k < perVolley; k++) {
      const side = k % 2 ? 1 : -1;
      const yawNow = p.getRotation().y;
      const from = local({ yaw: yawNow }, p.location, side * (0.8 + k % 3 * 0.55), 0.8 + v * 0.45 + k % 2 * 0.3, -0.5);
      const tgt = targets.length ? targets[(v * perVolley + k) % targets.length] : void 0;
      const goal = tgt ? bodyCenter(tgt) : add(aim.point, v3((r() - 0.5) * 8, 1, (r() - 0.5) * 8));
      const dir = norm(sub(goal, from));
      const disc = c.fx("grimoire:fx_p_disc", from, { dir, phase: 1 });
      c.run(fly(c, {
        fx: disc,
        from,
        dir,
        speed: 1.7,
        range: c.p("range") + 6,
        radius: 0.8,
        pierce: 1,
        homing: tgt,
        homingRate: 0.3,
        onHit: () => void 0,
        onEnd: (at) => {
          disc?.dissolve(3);
          shock(c, at, c.p("blastRadius"), c.p("damage"), { knock: 0.9, up: 0.35, sound: "grimoire.pressure.disc", pitch: 0.8 + r() * 0.4, ringLife: 0.7 });
          c.particle("grimoire:spark_burst", at, { color: OR, color2: WH3, count: 0.8 });
        }
      }), "disc");
    }
    c.sound("grimoire.pressure.disc", p.location, 1, 1.2);
    for (let t = 0; t < 7; t++) {
      wings?.follow(p).yaw(p.getRotation().y);
      yield 1;
    }
  }
  wings?.phase(2);
  yield* c.join(80);
}
function* aegisOfIsobars(c) {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  const dome = c.fx("grimoire:fx_p_dome", center, { size: R / 5.1, phase: 1 });
  c.sound("grimoire.pressure.hum", center, 1, 0.8);
  const cap = c.p("layerCapacity") * c.power;
  const layers = [cap, cap, cap];
  let broken = 0;
  const owner = c.player;
  c.ward({
    label: "aegis",
    priority: 30,
    protects: (e) => isAllyOrSelf(owner, e) && dist(e.location, center) <= R,
    absorb: (info) => {
      let dmg = info.damage;
      while (dmg > 0 && broken < 3) {
        const take = Math.min(dmg, layers[broken]);
        layers[broken] -= take;
        dmg -= take;
        if (layers[broken] <= 1e-3) broken++;
      }
      return dmg;
    },
    react: (info) => {
      dome?.pulse();
      dome?.phase(Math.min(5, 2 + broken));
      c.sound("grimoire.pressure.thud", info.hurt.location, 0.8, 0.7);
      c.particle("grimoire:ring_h", add(center, v3(0, R * 0.5, 0)), { color: GD, radius: R * 2, life: 0.6 });
    }
  });
  const redirected = /* @__PURE__ */ new Set();
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    if (t % 2 === 0) {
      for (const e of c.dim.getEntities({ location: center, maxDistance: R + 2.5 })) {
        if (redirected.has(e.id)) continue;
        const proj = e.getComponent(EntityProjectileComponent3.componentId);
        if (!proj) continue;
        const owner2 = proj.owner;
        if (owner2 && isAllyOrSelf(owner, owner2)) continue;
        const v = e.getVelocity();
        const out = norm(sub(e.location, center));
        if (dot(v, out) >= 0) continue;
        redirected.add(e.id);
        const speed = Math.max(0.6, len(v));
        const back = owner2?.isValid ? norm(sub(bodyCenter(owner2), e.location)) : out;
        try {
          e.clearVelocity();
          e.applyImpulse(mul(back, speed * 1.1));
          proj.owner = owner;
        } catch {
        }
        c.particle("grimoire:ring_dir", e.location, { color: GD, color2: WH3, radius: 1.6, dir: out });
        c.sound("grimoire.pressure.thud", e.location, 0.6, 1.6);
        dome?.pulse();
      }
    }
    yield 1;
  }
  if (broken >= 3) {
    c.sound("grimoire.pressure.boom", center, 0.8, 1.4);
    yield 8;
  }
}
function* counterpressureMantle(c) {
  const p = c.player;
  const mantle = c.fx("grimoire:fx_p_mantle", p.location, { phase: 1 });
  c.sound("grimoire.pressure.hum", p.location, 0.9, 1.2);
  const lastReflect = /* @__PURE__ */ new Map();
  c.ward({
    label: "mantle",
    priority: 20,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause) || !info.attacker || info.attacker.id === p.id) return info.damage;
      if (dist(info.attacker.location, p.location) > c.p("range")) return info.damage;
      return info.damage * (1 - c.p("reduction"));
    },
    react: (info) => {
      const a = info.attacker;
      if (!a || !a.isValid || relation(p, a) === "self") return;
      const now = system12.currentTick;
      if ((lastReflect.get(a.id) ?? -99) > now - 10) return;
      lastReflect.set(a.id, now);
      mantle?.pulse();
      c.sound("grimoire.pressure.pulse", p.location, 1, 1.4);
      system12.runTimeout(() => {
        if (!p.isValid || !a.isValid) return;
        push(a, sub(a.location, p.location), c.p("knock"), 0.55);
        if (isEnemy(p, a) || a.typeId !== "minecraft:player") c.hit(a, c.p("reflectDamage"), { kind: "reflect" });
        c.particle("grimoire:ring_h", add(p.location, v3(0, 1, 0)), { color: OR, color2: WH3, radius: 7, life: 0.6 });
        c.particle("grimoire:ring_dir", bodyCenter(a), { color: GD, radius: 2.5, dir: norm(sub(a.location, p.location)) });
        for (const e of c.enemies(p.location, 3)) if (e.id !== a.id) push(e, sub(e.location, p.location), 1, 0.3);
        c.sound("grimoire.pressure.boom", p.location, 0.7, 1.5);
      }, 3);
    }
  });
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (!c.ok) return;
    mantle?.follow(p, v3(0, 0, 0)).yaw(p.getRotation().y);
    if (t % 10 === 0) c.particle("grimoire:ripple_h", add(p.location, v3(0, 1.2, 0)), { color: OR, radius: 2.4, life: 0.8 });
    yield 1;
  }
}
function titansVise(c) {
  const a = c.aim(c.p("range"));
  const list = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to trap in range");
  return (function* () {
    const items = targets.map((t) => ({
      t,
      fx: c.fx("grimoire:fx_p_vise", t.location, { phase: 1, size: Math.max(1, Math.min(2.2, (t.getHeadLocation().y - t.location.y) / 1.6)) }),
      b: c.bind(t, c.p("duration") * 20 + 10)
    }));
    let last = { ...items[0].t.location };
    c.sound("grimoire.pressure.grind", last, 1, 0.9);
    yield 10;
    for (const it of items) it.fx?.phase(2);
    const pulses = Math.floor(c.p("duration"));
    for (let k = 0; k < pulses; k++) {
      for (let s = 0; s < 20; s++) {
        for (const it of items) {
          if (!it.t.isValid) continue;
          last = { ...it.t.location };
          it.fx?.move(last);
        }
        yield 1;
      }
      for (const it of items) {
        if (!it.t.isValid) continue;
        it.fx?.pulse();
        c.hit(it.t, c.p("pulseDamage"));
        c.particle("grimoire:ring_h", add(it.t.location, v3(0, 1, 0)), { color: OR, color2: GD, radius: 3.5, life: 0.5 });
        c.particle("grimoire:converge", bodyCenter(it.t), { color: GD, radius: 2.2, life: 0.3 });
      }
      c.sound("grimoire.pressure.grind", last, 0.9, 1 + k * 0.05);
    }
    for (const it of items) {
      it.fx?.phase(3);
      if (it.t.isValid) {
        c.hit(it.t, c.p("finalDamage"), { immediate: true });
        c.particle("grimoire:spark_burst", bodyCenter(it.t), { color: GD, color2: WH3, count: 2 });
      }
      endBind(it.b, false);
    }
    c.sound("grimoire.pressure.slam", last, 0.8, 1.3);
    yield 10;
  })();
}
function* atmosphericLabyrinth(c) {
  const { point } = c.aimGround(c.p("range"));
  const center = { x: Math.floor(point.x) + 0.5, y: Math.floor(point.y), z: Math.floor(point.z) + 0.5 };
  const cells = 4, cell = 4, size = cells * cell;
  const set = c.blocks();
  c.fx("grimoire:fx_circle_p", add(center, v3(0, 0.08, 0)), { size: size * 0.75, variant: 1, phase: 1 });
  const cols = [];
  for (const [i, j] of [[0, 0], [0, 4], [4, 0], [4, 4], [2, 2], [0, 2], [4, 2], [2, 0], [2, 4]]) {
    const at = c.ground({ x: center.x - size / 2 + i * cell, y: center.y + 4, z: center.z - size / 2 + j * cell }, 10);
    const f = c.fx("grimoire:fx_p_column", at, { phase: 1, size: 1 });
    if (f) cols.push(f);
    yield 1;
  }
  c.sound("grimoire.pressure.rise", center, 1.2, 1);
  let seed = system12.currentTick;
  let current = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
  yield* raise(set, [...current.values()], c.p("height"), "grimoire:pressure_barrier", 70, 2);
  const fallback = !set.enabled;
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t > 0 && t % (c.p("shiftInterval") * 20) === 0 && !fallback) {
      seed += 7919;
      const next = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
      for (const [k, p] of current) {
        if (next.has(k)) continue;
        for (let h = 0; h < c.p("height"); h++) set.remove({ x: p.x, y: p.y + h, z: p.z });
        if (Math.random() < 0.3) c.particle("grimoire:ripple_h", { x: p.x + 0.5, y: p.y + 1, z: p.z + 0.5 }, { color: OR, radius: 1.5 });
      }
      yield 2;
      yield* raise(set, [...next.values()].filter((p) => !current.has(`${p.x},${p.z}`)), c.p("height"), "grimoire:pressure_barrier", 70, 1);
      current = next;
      for (const f of cols) f.pulse();
      c.sound("grimoire.pressure.grind", center, 1, 1.2);
    }
    if (fallback && t % 4 === 0) {
      for (const e of c.enemies(center, size * 0.75)) {
        const k = `${Math.floor(e.location.x)},${Math.floor(e.location.z)}`;
        if (current.has(k)) push(e, sub(e.location, center), 0.8, 0.2);
      }
    }
    yield 1;
  }
  yield* lower(set, 90);
}
function* resonanceCage(c) {
  const a = c.aim(c.p("range"));
  const center = a.entity ? add(bodyCenter(a.entity), v3(0, 0.3, 0)) : add(c.ground(a.point, 8), v3(0, c.p("radius") * 0.6, 0));
  const R = c.p("radius") * c.area;
  const cage = c.fx("grimoire:fx_p_cage", center, { phase: 1, size: R / 4.5 });
  c.sound("grimoire.pressure.pulse", center, 1, 0.7);
  yield 12;
  cage?.phase(2);
  const pulses = c.p("pulses");
  for (let k = 0; k < pulses; k++) {
    for (let t = 0; t < c.p("interval"); t++) {
      if (t % 2 === 0) {
        for (const e of c.enemies(center, R + 1.5)) {
          if (dist(bodyCenter(e), center) > R - 0.7) push(e, sub(center, e.location), 0.7, 0.05);
        }
      }
      yield 1;
    }
    cage?.pulse();
    c.sound("grimoire.pressure.pulse", center, 1.1, 0.9 + k * 0.06);
    c.particle("grimoire:converge", center, { color: OR, color2: WH3, radius: R, life: 0.35, count: 2 });
    for (const e of c.enemies(center, R)) {
      c.hit(e, c.p("pulseDamage"));
      pullToward(e, center, 0.6);
      effect(e, "slowness", 30, 2);
      if (e.typeId === "minecraft:player") effect(e, "nausea", 80, 0);
    }
  }
  c.sound("grimoire.pressure.boom", center, 0.9, 1.2);
  yield 6;
}
function* pressureStep(c) {
  const p = c.player;
  let dir = flatNorm(c.dir);
  try {
    const mv = p.inputInfo.getMovementVector();
    if (Math.abs(mv.x) + Math.abs(mv.y) > 0.2) {
      const f = dir, r = rotY(f, 90);
      dir = norm(add(mul(f, mv.y), mul(r, -mv.x)));
    }
  } catch {
  }
  const maxD = c.p("distance");
  const free = Math.min(freeDistance(c.dim, add(p.location, v3(0, 0.3, 0)), dir, maxD + 1), freeDistance(c.dim, add(p.location, v3(0, 1.5, 0)), dir, maxD + 1));
  const d = Math.max(0, free - 0.9);
  const ring = c.fx("grimoire:fx_p_step_ring", add(p.location, v3(0, 0.05, 0)), { phase: 1 });
  c.sound("grimoire.pressure.dash", p.location, 1, 1.1);
  yield 2;
  ring?.phase(3);
  for (const e of c.enemies(p.location, 2.5)) push(e, sub(e.location, p.location), 0.9, 0.3);
  grantFallImmunity(p.id, 50);
  if (d < 0.6) {
    flash2(stateOf(p), "\xA77Pressure Step blocked by terrain", 30);
    yield 4;
    return;
  }
  const ticks = 5;
  const start2 = p.location;
  for (let t = 0; t < ticks; t++) {
    drive(p, { x: dir.x * (d / ticks) * 1.05, y: t === 0 ? 0.12 : 0.02, z: dir.z * (d / ticks) * 1.05 });
    const back = add(p.location, v3(0, 0.9, 0));
    c.particle("grimoire:ring_dir", back, { color: OR, color2: WH3, radius: 1.6 + t * 0.2, dir, life: 1 });
    c.particle("grimoire:ripple_dir", back, { color: WH3, radius: 2.2, dir, life: 1.3 });
    yield 1;
  }
  c.particle("grimoire:streak_dir", add(start2, v3(0, 1, 0)), { color: GD, dir, speed: 1, count: 1.5 });
  yield 4;
}
function skylineRail(c) {
  const p = c.player;
  let dir = c.dir;
  const yp = yawPitchOf(dir);
  if (yp.pitch > -8) dir = norm(add(flatNorm(dir), v3(0, 0.22, 0)));
  const startPos = add(p.location, v3(0, 1, 0));
  const len0 = c.p("length");
  const free = Math.min(
    freeDistance(c.dim, startPos, dir, len0),
    freeDistance(c.dim, add(startPos, v3(0, 0.9, 0)), dir, len0),
    freeDistance(c.dim, add(startPos, v3(0, -0.8, 0)), dir, len0)
  );
  const L = free - 1.6;
  if (L < 4) throw new Fizzle("No room for the Skyline Rail");
  return (function* () {
    const n = Math.max(3, Math.min(c.p("rings"), Math.floor(L / 3.2)));
    const rings = [];
    for (let i = 0; i < n; i++) {
      const at = add(startPos, mul(dir, L * (i + 0.6) / n));
      rings.push({ fx: c.fx("grimoire:fx_p_rail_ring", at, { dir, phase: 1, size: 1 + 0.05 * i }), at, passed: false });
      if (i % 2 === 1) yield 1;
    }
    c.sound("grimoire.pressure.rise", startPos, 0.8, 1.8);
    grantFallImmunity(p.id, 200);
    const speed = c.p("speed");
    const steps = Math.ceil(L / speed) + 4;
    let lastPos = p.location;
    let stuck = 0;
    for (let t = 0; t < steps; t++) {
      if (!c.ok) return;
      const along = Math.min(L, (t + 1) * speed);
      const target = add(startPos, mul(dir, along));
      const here = add(p.location, v3(0, 1, 0));
      const corr = mul(sub(target, here), 0.35);
      drive(p, add(mul(dir, speed), corr));
      for (const r of rings) {
        if (!r.passed && dist(here, r.at) < 2.2) {
          r.passed = true;
          r.fx?.phase(3);
          c.particle("grimoire:ring_dir", r.at, { color: OR, color2: WH3, radius: 4.5, dir });
          c.sound("grimoire.pressure.ring", r.at, 0.9, 1 + rings.indexOf(r) * 0.04);
        }
      }
      if (t % 2 === 0) c.particle("grimoire:streak_dir", here, { color: GD, dir: mul(dir, -1), count: 0.6 });
      stuck = dist(p.location, lastPos) < 0.15 ? stuck + 1 : 0;
      lastPos = p.location;
      if (stuck > 5 && t > 6) break;
      yield 1;
    }
    effect(p, "slow_falling", 60, 0);
    yield 6;
  })();
}
function* barometricOmniscience(c) {
  const p = c.player;
  const R = c.p("radius");
  const sonar = c.fx("grimoire:fx_p_sonar", add(p.location, v3(0, 1, 0)), { size: 1, phase: 1 });
  const ground = c.fx("grimoire:fx_circle_p", add(p.location, v3(0, 0.07, 0)), { size: 2, variant: 0, phase: 1 });
  c.sound("grimoire.pressure.sonar", p.location, 1.2, 1);
  const markers = /* @__PURE__ */ new Map();
  const st = stateOf(p);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (!c.ok) return;
    const k = Math.min(1, t / 40);
    sonar?.follow(p, v3(0, 1, 0)).size(1 + (R - 1) * k);
    ground?.follow(p, v3(0, 0.07, 0)).size(2 + Math.min(16, R) * k);
    if (t % 40 === 0) {
      c.particle("grimoire:ring_h", add(p.location, v3(0, 0.3, 0)), { color: OR, color2: GD, radius: R * 2 * Math.max(0.3, k), life: 2.5 });
      c.sound("grimoire.pressure.sonar", p.location, 0.6, 1.3);
    }
    if (t % 10 === 0) {
      const found = livingNear(c.dim, p.location, R * Math.max(0.15, k)).filter((e) => e.id !== p.id && e.getComponent("minecraft:health"));
      found.sort((a, b) => dist(a.location, p.location) - dist(b.location, p.location));
      const keep = new Set(found.slice(0, c.p("maxMarkers")).map((e) => e.id));
      for (const [id, m] of markers) {
        if (!keep.has(id) || !m.e.isValid) {
          m.fx?.dissolve(4);
          markers.delete(id);
        }
      }
      let hostile = 0, other = 0, players = 0;
      let nearest;
      for (const e of found) {
        const rel = relation(p, e);
        if (e.typeId === "minecraft:player") players++;
        else if (rel === "enemy") {
          hostile++;
          if (!nearest) nearest = e;
        } else other++;
        if (!keep.has(e.id)) continue;
        let m = markers.get(e.id);
        if (!m) {
          m = { e, fx: c.fx("grimoire:fx_p_marker", add(e.getHeadLocation(), v3(0, 0.7, 0)), { phase: 1 }) };
          markers.set(e.id, m);
        }
        const dm = Math.round(dist(e.location, p.location));
        const name = e.typeId === "minecraft:player" ? e.name : e.typeId.replace("minecraft:", "").replace(/_/g, " ");
        try {
          if (m.fx?.entity.isValid) m.fx.entity.nameTag = `${rel === "enemy" ? "\xA7c" : "\xA76"}${name} \xA77${dm}m`;
        } catch {
        }
        const lo = e.location, hi = e.getHeadLocation();
        const w = 0.45;
        for (const [dx, dz] of [[-w, -w], [w, -w], [-w, w], [w, w]]) {
          for (const y of [lo.y + 0.05, hi.y + 0.25]) particle(c.dim, "grimoire:outline_point", { x: lo.x + dx, y, z: lo.z + dz }, { color: GD, size: 1 }, p);
        }
      }
      const dirTxt = nearest ? compass(sub(nearest.location, p.location)) : "";
      flash2(st, `\xA76Barometric sense\xA77: \xA7c${hostile} hostile \xA77\xB7 \xA7e${other} other \xA77\xB7 \xA7b${players} players` + (nearest ? ` \xA77| nearest \xA7c${nearest.typeId.replace("minecraft:", "")} ${Math.round(dist(nearest.location, p.location))}m ${dirTxt}` : ""), 14);
    }
    for (const m of markers.values()) if (m.e.isValid) m.fx?.move(add(m.e.getHeadLocation(), v3(0, 0.7, 0)));
    yield 1;
  }
}
function compass(d) {
  const a = Math.atan2(d.x, -d.z) * 180 / Math.PI;
  const names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return names[(Math.round(a / 45) % 8 + 8) % 8];
}
function* equilibriumTheft(c) {
  const p = c.player;
  const center = p.location;
  const R = c.p("radius");
  const field = c.fx("grimoire:fx_p_field", center, { phase: 1, size: R / 7.5 });
  c.sound("grimoire.pressure.rise", center, 0.9, 2);
  yield 6;
  field?.phase(2);
  for (let t2 = 0; t2 < 36; t2++) {
    if (t2 % 6 === 0) c.particle("grimoire:converge", add(p.location, v3(0, 1.5, 0)), { color: OR, color2: WH3, radius: R, life: 0.6, count: 1.5 });
    if (t2 % 3 === 0) {
      for (const e of c.enemies(center, R)) {
        pullToward(e, center, 0.35);
        effect(e, "slowness", 20, 1);
      }
    }
    yield 1;
  }
  field?.dissolve(6);
  const st = stateOf(p);
  st.empowered = { until: system12.currentTick + c.p("buffSeconds") * 20, source: "equilibrium" };
  st.hudKey = "";
  flash2(st, `\xA76Equilibrium stolen: your next spell is empowered (x1.6, ${c.p("buffSeconds")}s)`, 50);
  const crystal = c.fx("grimoire:fx_p_crystal", add(p.location, v3(0.8, 2.2, 0)), { phase: 1 });
  c.sound("grimoire.pressure.crystal", p.location, 1, 1);
  let t = 0;
  while (st.empowered && st.empowered.until > system12.currentTick) {
    if (!c.ok) return;
    const a = t * 0.08;
    crystal?.move(add(p.location, v3(Math.cos(a) * 0.9, 2.1 + Math.sin(t * 0.15) * 0.1, Math.sin(a) * 0.9)));
    if (t % 40 === 0) c.sound("grimoire.pressure.crystal", p.location, 0.4, 1.2);
    t++;
    yield 1;
  }
  if (st.empowered && st.empowered.until <= system12.currentTick) st.empowered = void 0;
  c.particle("grimoire:spark_burst", add(p.location, v3(0, 2, 0)), { color: GD, color2: WH3, count: 1.5 });
}
function* isobaricCitadel(c) {
  const center = { x: Math.floor(c.feet.x) + 0.5, y: Math.floor(c.feet.y), z: Math.floor(c.feet.z) + 0.5 };
  const R = c.p("radius");
  const set = c.blocks();
  c.fx("grimoire:fx_circle_p", add(center, v3(0, 0.07, 0)), { size: R + 2, variant: 2, phase: 1 });
  const ring = c.fx("grimoire:fx_p_citadel_ring", add(center, v3(0, 9, 0)), { phase: 1, size: R / 9.4 });
  c.sound("grimoire.pressure.rise", center, 1.4, 0.8);
  const columns = [];
  for (let i = 0; i < 8; i++) {
    const ang = i / 8 * Math.PI * 2 + Math.PI / 8;
    const at = c.ground({ x: center.x + Math.cos(ang) * R, y: center.y + 4, z: center.z + Math.sin(ang) * R }, 10);
    columns.push({ fx: c.fx("grimoire:fx_p_column", at, { phase: 1, size: 1.6 }), at });
    yield 4;
  }
  const wall = /* @__PURE__ */ new Map();
  for (let i = 0; i < 8; i++) {
    const a = columns[i].at, b = columns[(i + 1) % 8].at;
    const steps = Math.ceil(hdist(a, b) * 2);
    for (let s = 0; s <= steps; s++) {
      if (i % 2 === 0 && s > steps * 0.38 && s < steps * 0.62) continue;
      const q = lerp(a, b, s / steps);
      wall.set(`${Math.floor(q.x)},${Math.floor(q.z)}`, { x: Math.floor(q.x), y: center.y, z: Math.floor(q.z) });
    }
  }
  yield* raise(set, grounded(c, wall.values()), 4, "grimoire:pressure_barrier", 40, 3);
  ring?.phase(2);
  const owner = c.player;
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t % 20 === 0) {
      for (const e of livingNear(c.dim, center, R)) if (isAllyOrSelf(owner, e)) effect(e, "resistance", 30, 0);
      for (const e of c.dim.getEntities({ location: center, maxDistance: R + 1.5 })) {
        const proj = e.getComponent(EntityProjectileComponent3.componentId);
        if (proj && !(proj.owner && isAllyOrSelf(owner, proj.owner))) {
          c.particle("grimoire:spark_burst", e.location, { color: OR, count: 0.6 });
          try {
            e.remove();
          } catch {
          }
        }
      }
    }
    if (t % c.p("attackInterval") === 0 && t > 0) {
      const foes = nearestEnemies(c, center, c.p("range"), c.p("maxTargets"));
      if (foes.length) {
        ring?.pulse();
        c.sound("grimoire.pressure.boom", center, 0.9, 1.3);
      }
      for (const f of foes) {
        const col = columns.reduce((best, cc) => dist(cc.at, f.location) < dist(best.at, f.location) ? cc : best, columns[0]);
        col.fx?.pulse();
        const from = add(col.at, v3(0, 5.5, 0));
        const to = bodyCenter(f);
        const n = Math.ceil(dist(from, to));
        for (let i = 0; i <= n; i += 2) c.particle("grimoire:ring_dir", lerp(from, to, i / n), { color: OR, color2: WH3, radius: 1.4, dir: norm(sub(to, from)), life: 0.6 });
        c.hit(f, c.p("damage"));
        push(f, sub(f.location, center), 1.6, 0.5);
        c.particle("grimoire:spark_burst", to, { color: GD, count: 1 });
      }
    }
    yield 1;
  }
  ring?.dissolve(20);
  yield* lower(set, 40);
  yield 10;
}
function* thousandAtmospheres(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const sky = c.fx("grimoire:fx_circle_p", add(point, v3(0, 20, 0)), { size: R * 1.05, variant: 2, phase: 1 });
  const ground = c.fx("grimoire:fx_circle_p", add(point, v3(0, 0.1, 0)), { size: R * 0.9, variant: 0, phase: 1 });
  const layers = c.fx("grimoire:fx_p_layers", point, { phase: 1, size: R / 17.5 });
  const fogged = c.dim.getPlayers({ location: point, maxDistance: 48 });
  for (const pl of fogged) {
    try {
      pl.runCommand("fog @s push grimoire:atmosphere grimoire_p15");
    } catch {
    }
  }
  c.onCleanup(() => {
    for (const pl of fogged) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_p15");
      } catch {
      }
    }
  });
  c.sound("grimoire.pressure.rise", point, 1.6, 0.6);
  c.shake(point, 40, 0.15, 3);
  for (let t = 0; t < 60; t++) {
    if (t % 10 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        if (t % 20 === 0) c.hit(e, 2);
      }
      c.particle("grimoire:ripple_h", add(point, v3(0, 6 + t % 30 / 3, 0)), { color: OR, radius: R * 2, life: 2 });
    }
    yield 1;
  }
  sky?.phase(3);
  layers?.phase(3);
  const n = c.p("collapses");
  for (let k = 0; k < n; k++) {
    const r = Math.max(2, R * (1 - k / n));
    c.particle("grimoire:ring_h", add(point, v3(0, 3, 0)), { color: GD, color2: WH3, radius: r * 2.2, life: 0.8 });
    c.particle("grimoire:hex_flash", add(point, v3(0, 3.5, 0)), { color: OR, radius: r * 1.6, life: 1 });
    for (const e of c.enemies(point, r + 1.5)) {
      const d = dist(e.location, point);
      if (d < r - 4) continue;
      c.hit(e, c.p("layerDamage"));
      pullToward(e, point, 0.9);
    }
    c.sound("grimoire.pressure.thud", point, 1.2, 0.6 + k * 0.05);
    c.shake(point, 40, 0.2 + k * 0.03, 0.3);
    yield 6;
  }
  layers?.phase(4);
  c.flash(point, 60, { r: 1, g: 0.85, b: 0.6 }, 0.15);
  c.sound("grimoire.pressure.edict", point, 2, 1);
  for (let f = 0; f < 3; f++) {
    c.fx("grimoire:fx_p_front", point, { phase: 1, size: R / 4 * (0.55 + f * 0.25) });
    shock(c, point, R * (0.6 + f * 0.25), c.p("frontDamage") * (1 - f * 0.3), { knock: 2.2 - f * 0.4, up: 0.9 - f * 0.2, shake: 1 - f * 0.25, minK: 0.4 });
    c.particle("grimoire:glow_flash", add(point, v3(0, 2, 0)), { color: WH3, size: 12 - f * 3 });
    yield 6;
  }
  c.particle("grimoire:spark_burst", add(point, v3(0, 2, 0)), { color: GD, color2: WH3, radius: 4, count: 4 });
  ground?.phase(3);
  yield 20;
  void sky;
}

// src/spells/pressure/index.ts
var S5 = "pressure";
var PRESSURE = [
  {
    code: "P01",
    id: "pressure.lance",
    school: S5,
    name: "Pressure Lance",
    cooldown: 6,
    charge: 8,
    enhanceable: true,
    params: { damage: 14, range: 48, speed: 2.4, radius: 1, impactDamage: 6, impactRadius: 2.5 },
    blurb: "Layered air compressed into a piercing orange-gold lance.",
    cast: pressureLance
  },
  {
    code: "P02",
    id: "pressure.atlas_piston",
    school: S5,
    name: "Atlas Piston",
    cooldown: 18,
    charge: 14,
    enhanceable: true,
    params: { damage: 22, radius: 6, waveDamage: 6, waveRadius: 11, range: 40, height: 14, launch: 1.1 },
    blurb: "A colossal translucent copper piston slams the target area.",
    cast: atlasPiston
  },
  {
    code: "P03",
    id: "pressure.isobaric_severance",
    school: S5,
    name: "Isobaric Severance",
    cooldown: 10,
    charge: 10,
    enhanceable: true,
    params: { damage: 12, delayedDamage: 8, width: 9, range: 32, speed: 1.6, delay: 10 },
    blurb: "A near-invisible cutting plane followed by delayed shockwaves.",
    cast: isobaricSeverance
  },
  {
    code: "P04",
    id: "pressure.cataclysm_salvo",
    school: S5,
    name: "Cataclysm Salvo",
    cooldown: 22,
    charge: 16,
    enhanceable: true,
    params: { discs: 24, damage: 6, blastRadius: 2.5, range: 36, volleys: 4 },
    blurb: "Mechanical wings of pressure rings fire successive disc formations.",
    cast: cataclysmSalvo
  },
  {
    code: "P05",
    id: "pressure.aegis_of_isobars",
    school: S5,
    name: "Aegis of Isobars",
    cooldown: 25,
    charge: 12,
    enhanceable: true,
    params: { radius: 5, layers: 3, layerCapacity: 12, duration: 12 },
    blurb: "A three-layer dome of compressed air that absorbs force and redirects projectiles.",
    cast: aegisOfIsobars
  },
  {
    code: "P06",
    id: "pressure.counterpressure_mantle",
    school: S5,
    name: "Counterpressure Mantle",
    cooldown: 22,
    charge: 10,
    enhanceable: true,
    params: { duration: 15, reduction: 0.6, reflectDamage: 6, range: 6, knock: 2.6 },
    blurb: "A flowing mantle that contracts, then blasts attackers away.",
    cast: counterpressureMantle
  },
  {
    code: "P07",
    id: "pressure.titans_vise",
    school: S5,
    name: "Titan's Vise",
    cooldown: 30,
    charge: 16,
    enhanceable: true,
    params: { targets: 3, pulseDamage: 5, finalDamage: 10, duration: 6, selectRadius: 7, range: 32 },
    blurb: "Hexagonal pressure plates trap and crush up to three enemies.",
    cast: titansVise
  },
  {
    code: "P08",
    id: "pressure.atmospheric_labyrinth",
    school: S5,
    name: "Atmospheric Labyrinth",
    cooldown: 35,
    charge: 20,
    enhanceable: true,
    params: { duration: 15, size: 9, range: 24, height: 3, shiftInterval: 4 },
    blurb: "Columns and shifting barriers of compressed air form a maze.",
    cast: atmosphericLabyrinth
  },
  {
    code: "P09",
    id: "pressure.resonance_cage",
    school: S5,
    name: "Resonance Cage",
    cooldown: 28,
    charge: 14,
    enhanceable: true,
    params: { radius: 4.5, pulseDamage: 6, pulses: 6, interval: 20, range: 30 },
    blurb: "A vibrating spherical cage whose synchronized pulses strike inward.",
    cast: resonanceCage
  },
  {
    code: "P10",
    id: "pressure.pressure_step",
    school: S5,
    name: "Pressure Step",
    cooldown: 5,
    charge: 4,
    enhanceable: false,
    params: { distance: 8 },
    blurb: "A collapsing ring under your feet propels you forward.",
    cast: pressureStep
  },
  {
    code: "P11",
    id: "pressure.skyline_rail",
    school: S5,
    name: "Skyline Pressure Rail",
    cooldown: 14,
    charge: 12,
    enhanceable: false,
    params: { length: 40, speed: 1.6, rings: 10 },
    blurb: "An aerial corridor of rings that hurls you across the sky.",
    cast: skylineRail
  },
  {
    code: "P12",
    id: "pressure.barometric_omniscience",
    school: S5,
    name: "Barometric Omniscience",
    cooldown: 25,
    charge: 12,
    enhanceable: false,
    params: { radius: 48, duration: 15, maxMarkers: 24 },
    blurb: "Pressure waves reveal every living thing nearby.",
    cast: barometricOmniscience
  },
  {
    code: "P13",
    id: "pressure.equilibrium_theft",
    school: S5,
    name: "Equilibrium Theft",
    cooldown: 35,
    charge: 16,
    enhanceable: false,
    params: { radius: 8, buffSeconds: 30 },
    blurb: "Steal the surrounding air into a crystal that empowers your next spell once.",
    cast: equilibriumTheft
  },
  {
    code: "P14",
    id: "pressure.isobaric_citadel",
    school: S5,
    name: "Isobaric Citadel",
    cooldown: 75,
    charge: 30,
    enhanceable: true,
    params: { radius: 9, duration: 30, attackInterval: 30, damage: 10, range: 20, maxTargets: 4 },
    blurb: "A fortress of compressed atmosphere that guards allies and strikes back.",
    cast: isobaricCitadel
  },
  {
    code: "P15",
    id: "pressure.thousand_atmospheres",
    school: S5,
    name: "Imperial Edict: Thousand Atmospheres",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 18, range: 40, layerDamage: 4, collapses: 12, frontDamage: 20 },
    blurb: "Dominion, thousandfold compression, then imperial release.",
    cast: thousandAtmospheres
  }
];

// src/spells/prism_light/spells.ts
var PE = COLORS.pearl;
var CH = COLORS.champagne;
var WT = COLORS.white;
var WHITE_VARIANT = 7;
function* dissolveLater3(fx, ticks, fade = 10) {
  yield ticks;
  fx?.dissolve(fade);
}
function glints(c, at, radius = 1, count = 1) {
  c.particle("grimoire:spectral_glint", at, { radius, count, size: 1.2 });
}
function ray(c, a, b, variant = WHITE_VARIANT, size = 1) {
  const fx = c.fx("grimoire:fx_pr_ray", a, { dir: sub(b, a), len: 0.05, variant, phase: 1, size });
  fx?.length(dist(a, b));
  return fx;
}
function primaryTarget2(c, range, around = 6) {
  const a = c.aim(range);
  if (a.entity && c.isEnemy(a.entity)) return a.entity;
  return nearestEnemies(c, a.point, around, 1)[0];
}
function* sevenfoldVerdict(c) {
  const a = c.aim(c.p("range"));
  const goal = a.entity ? bodyCenter(a.entity) : a.point;
  const at = add(c.origin, add(mul(flatNorm(c.dir), 0.8), v3(0, 1.6, 0)));
  const prism = c.fx("grimoire:fx_pr_prism", at, { dir: sub(goal, at), phase: 1, size: c.area });
  c.sound("grimoire.prism_light.glass", at, 1, 1);
  yield 8;
  prism?.phase(2);
  c.sound("grimoire.prism_light.beam", at, 1, 1);
  yield 8;
  const side = rotY(flatNorm(sub(goal, at)), 90);
  const ribbons = SPECTRUM.map((_, i) => ({
    fx: c.fx("grimoire:fx_pr_ribbon", at, { dir: sub(goal, at), variant: i, phase: 1, size: c.area }),
    ctrl: add(lerp(at, goal, 0.5), add(mul(side, (i - 3) * 3.2), v3(0, i % 2 ? 3 : -1.5, 0))),
    start: 2 + i * 2,
    done: false
  }));
  const T = 12;
  for (let t = 0; t < T + 16; t++) {
    ribbons.forEach((r, i) => {
      if (r.done || t < r.start) return;
      const k = Math.min(1, (t - r.start) / T);
      const p = arcPoint(at, r.ctrl, a.entity?.isValid ? bodyCenter(a.entity) : goal, k);
      const prev = r.fx?.location ?? at;
      r.fx?.move(p).aim(sub(p, prev));
      if (k >= 1) {
        r.done = true;
        for (const e of c.enemies(p, 1.6)) c.hit(e, c.p("damage"));
        c.particle("grimoire:spectral_glint", p, { color: SPECTRUM[i], radius: 0.6, count: 0.6 });
        r.fx?.dissolve(4);
      }
    });
    yield 1;
  }
  const end = a.entity?.isValid ? bodyCenter(a.entity) : goal;
  const star = c.fx("grimoire:fx_pr_star", end, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.prism_light.chime", end, 1.2, 1);
  for (const e of c.enemies(end, c.p("starRadius"))) c.hit(e, c.p("starDamage"));
  glints(c, end, 1.6, 2);
  prism?.dissolve(10);
  c.run(dissolveLater3(star, 14), "star");
  yield 14;
}
function* totalInternalReflection(c) {
  const target = primaryTarget2(c, c.p("range"));
  const goal = target ? bodyCenter(target) : c.aim(c.p("range")).point;
  const r = c.p("radius") * c.area;
  const base = yawPitchOf(sub(c.player.location, goal)).yaw;
  const angles = [35, -70, 110, -150, 175];
  const route = [c.eye()];
  const prisms = [];
  for (let k = 0; k < c.p("prisms"); k++) {
    let placed;
    for (const sgn of [1, -1]) {
      const p = add(goal, add(mul(rotY(v3(0, 0, 1), base + angles[k] * sgn), r), v3(0, 0.4 + k % 2 * 1.2, 0)));
      const prev = route[route.length - 1];
      if (freeDistance(c.dim, prev, sub(p, prev), dist(prev, p)) >= dist(prev, p) - 0.2) {
        placed = p;
        break;
      }
    }
    if (!placed) continue;
    route.push(placed);
    const fx = c.fx("grimoire:fx_pr_tri", sub(placed, v3(0, 0.75, 0)), { yaw: base + k * 40, phase: 1, size: c.area });
    if (fx) prisms.push(fx);
    yield 2;
  }
  route.push(goal);
  c.sound("grimoire.prism_light.glass", goal, 1, 1.2);
  yield 6;
  for (const p of prisms) p.phase(2);
  for (let k = 0; k < route.length - 1; k++) {
    const A = route[k], B = route[k + 1];
    const last = k === route.length - 2;
    const beam = ray(c, A, B, last ? 4 : WHITE_VARIANT, last ? 1.4 : 1);
    c.run(dissolveLater3(beam, 18 - Math.min(10, k * 2), 6), "beam");
    c.sound("grimoire.prism_light.beam", B, 0.7, 1 + k * 0.12);
    for (const e of c.along(A, B, 0.8)) if (!last) c.hit(e, c.p("beamDamage"));
    yield 3;
  }
  if (target?.isValid) {
    c.hit(target, c.p("damage"), { immediate: true });
    glints(c, bodyCenter(target), 1, 1.5);
  }
  for (const p of prisms) {
    p.phase(3);
    glints(c, p.location, 1.2, 1);
  }
  c.sound("grimoire.prism_light.shatter", goal, 1, 1.1);
  yield 12;
}
function* causticBloom(c) {
  const { point } = c.aimGround(c.p("range"));
  const n = c.p("lenses");
  const sets = [];
  for (let k = 0; k < n; k++) {
    const off = mul(rotY(v3(0, 0, 1), c.yaw + k * (360 / n)), c.p("spread"));
    const g = c.ground(add(point, off), 10);
    sets.push({
      pos: g,
      lens: c.fx("grimoire:fx_pr_lens", add(g, v3(0, 9, 0)), { phase: 1, size: c.area }),
      flower: c.fx("grimoire:fx_pr_caustic", add(g, v3(0, 0.05, 0)), { phase: 1, size: c.area })
    });
  }
  c.sound("grimoire.prism_light.hum", point, 1.2, 1);
  yield 12;
  const targets = nearestEnemies(c, point, c.p("spread") + 8, n);
  for (let t = 0; t < 40; t++) {
    sets.forEach((s, k) => {
      const tgt = targets[k % Math.max(1, targets.length)];
      if (tgt?.isValid) s.pos = lerp(s.pos, c.ground(tgt.location, 4), 0.12);
      s.flower?.move(add(s.pos, v3(0, 0.05, 0)));
      s.lens?.move(add(s.pos, v3(0, 9, 0)));
    });
    yield 1;
  }
  for (let k = 0; k < n; k++) {
    const s = sets[k];
    s.flower?.phase(3);
    c.sound("grimoire.prism_light.focus", s.pos, 1, 1 + k * 0.1);
    yield 8;
    c.particle("grimoire:glow_flash", add(s.pos, v3(0, 0.6, 0)), { color: CH, size: 3 });
    c.particle("grimoire:light_motes", s.pos, { color: CH, color2: WT, radius: 1.5, count: 1 });
    for (const e of c.enemies(s.pos, c.p("radius"))) c.hit(e, c.p("damage"));
    s.flower?.dissolve(6);
    yield 4;
  }
  for (const s of sets) s.lens?.dissolve(12);
  yield 10;
}
function* fraunhoferLattice(c) {
  const fwd = flatNorm(c.dir);
  const origin = c.ground(add(c.player.location, mul(fwd, 2.5)), 6);
  const grating = c.fx("grimoire:fx_pr_grating", origin, { yaw: c.yaw, phase: 1, size: 0.6 * c.area });
  c.sound("grimoire.prism_light.sweep", origin, 1.2, 1);
  yield 12;
  const n = c.p("bands");
  const spread = c.p("spread");
  const L = c.p("length") * c.area;
  const variants = [6, 4, 2, WHITE_VARIANT, 3, 1, 0];
  const bands = [];
  for (let k = 0; k < n; k++) {
    bands.push(c.fx("grimoire:fx_pr_band", add(origin, v3(0, 0.05, 0)), { yaw: c.yaw + (k - (n - 1) / 2) * spread, len: L, variant: variants[k % 7], phase: 1 }));
  }
  const dur = c.p("duration") * 20;
  const last = /* @__PURE__ */ new Map();
  for (let t = 0; t < dur; t++) {
    const swing = Math.sin(t / dur * Math.PI * 2) * (c.p("sweep") / 2);
    const baseYaw = c.yaw + swing;
    grating?.yaw(baseYaw);
    bands.forEach((b, k) => b?.yaw(baseYaw + (k - (n - 1) / 2) * spread));
    if (t % 4 === 0) {
      for (const e of c.enemies(add(origin, mul(fwd, L / 2)), L / 2 + 2)) {
        const rel = sub(e.location, origin);
        const d = Math.hypot(rel.x, rel.z);
        if (d > L || d < 0.5) continue;
        const ang = yawPitchOf(rel).yaw;
        const inBand = bands.some((_, k) => {
          const by = baseYaw + (k - (n - 1) / 2) * spread;
          return Math.abs((ang - by + 540) % 360 - 180) < spread * 0.28 + 57 / Math.max(1, d) * 0.6;
        });
        if (!inBand || t - (last.get(e.id) ?? -99) < 10) continue;
        last.set(e.id, t);
        c.hit(e, c.p("damage"));
        glints(c, bodyCenter(e), 0.5, 0.5);
      }
    }
    yield 1;
  }
  for (const b of bands) b?.dissolve(10);
}
function* brewstersVeil(c) {
  const p = c.player;
  const n = c.p("panels");
  const panels = [];
  for (let k = 0; k < n; k++) panels.push(c.fx("grimoire:fx_pr_panel", p.location, { yaw: c.yaw, phase: 1, size: c.area }));
  c.sound("grimoire.prism_light.glass", p.location, 1, 0.9);
  const front = (dir) => dot(flatNorm(dir), flatNorm(p.getViewDirection())) > 0.2;
  c.ward({
    label: "Brewster's Veil",
    priority: 30,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      const src = info.attacker ?? info.projectile;
      if (!src || !front(sub(src.location, p.location))) return info.damage;
      if (info.cause === "projectile") return 0;
      return PHYSICAL_CAUSES.has(info.cause) ? info.damage * (1 - c.p("reduction")) : info.damage;
    },
    react: () => panels[1]?.pulse()
  });
  const seen = /* @__PURE__ */ new Set();
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    const yaw = p.getRotation().y;
    const fwd = flatNorm(p.getViewDirection());
    panels.forEach((fx, k) => {
      const ang = (k - (n - 1) / 2) * 38;
      const pos = add(p.location, mul(rotY(fwd, ang), 1.7));
      fx?.move(pos).yaw(yaw + ang);
    });
    if (t % 2 === 0) {
      for (const inc of hostileProjectiles(c, add(p.location, mul(fwd, 2)), 4, seen)) {
        const to = sub(p.location, inc.e.location);
        if (dot(inc.vel, to) <= 0 || !front(mul(to, -1))) continue;
        seen.add(inc.e.id);
        const side = Math.sign(dot(sub(inc.e.location, p.location), rotY(fwd, 90))) || 1;
        redirect(inc, add(mul(rotY(fwd, 90), side), v3(0, 0.15, 0)), 0.8, p);
        panels[side > 0 ? n - 1 : 0]?.pulse();
        glints(c, inc.e.location, 0.8, 1);
        c.sound("grimoire.prism_light.glass", inc.e.location, 0.7, 1.4);
      }
    }
    yield 1;
  }
}
function* parallaxDisplacement(c) {
  const p = c.player;
  const side = () => rotY(flatNorm(p.getViewDirection()), 90);
  const falsePos = () => add(p.location, mul(side(), c.p("offset")));
  const fx = c.fx("grimoire:fx_pr_rgb", falsePos(), { yaw: c.yaw, phase: 1 });
  const decoy = spawnDecoy(c, falsePos());
  c.sound("grimoire.prism_light.beam", p.location, 0.9, 1.3);
  let hit2;
  const ward = c.ward({
    label: "Parallax Displacement",
    priority: 70,
    protects: (e) => e.id === p.id && !hit2,
    absorb: (info) => {
      if (hit2 || info.damage < 1 || !PHYSICAL_CAUSES.has(info.cause) && info.cause !== "magic") return info.damage;
      hit2 = { from: info.attacker };
      return 0;
    }
  });
  yield 10;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok && !hit2; t++) {
    fx?.move(falsePos()).yaw(p.getRotation().y);
    decoy?.move(falsePos());
    if (t % 40 === 0) for (const e of c.enemies(p.location, 12)) lure(e, decoy);
    yield 1;
  }
  if (!hit2) return;
  ward.alive = false;
  fx?.phase(3);
  c.sound("grimoire.prism_light.shatter", p.location, 1.1, 1);
  glints(c, add(p.location, v3(0, 1, 0)), 1.4, 1.5);
  const away = hit2.from?.isValid ? flatNorm(sub(p.location, hit2.from.location)) : flatNorm(mul(p.getViewDirection(), -1));
  for (const turn of [70, -70, 110, -110, 0]) {
    const dest = safeSpot(c.dim, add(p.location, mul(rotY(away, turn), c.p("hop"))));
    if (dest && segmentClear(c, add(p.location, v3(0, 0.2, 0)), add(dest, v3(0, 0.2, 0)))) {
      try {
        p.teleport(dest, { keepVelocity: false });
      } catch {
      }
      break;
    }
  }
  effect(p, "invisibility", 20, 0);
  yield 12;
}
function* chromaticTurnstile(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("gates");
  const gates = [];
  for (let k = 0; k < n; k++) {
    const ang = c.yaw + k * (360 / n);
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), R)), 8);
    const out = ang + 90 + (k % 2 ? 25 : -25);
    gates.push({ at, out, fx: c.fx("grimoire:fx_pr_gate", at, { yaw: out, variant: k % 7, phase: 1, size: c.area }), last: /* @__PURE__ */ new Map() });
    yield 2;
  }
  c.sound("grimoire.prism_light.hum", point, 1.2, 1.1);
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 2 === 0) {
      for (const g of gates) {
        const dir = rotY(v3(0, 0, 1), g.out);
        const plane = rotY(dir, 90);
        for (const e of c.enemies(g.at, 2.2)) {
          const rel = sub(e.location, g.at);
          if (Math.abs(dot(rel, plane)) > 1.5 * c.area || Math.abs(dot(rel, dir)) > 1.2) continue;
          if (t - (g.last.get(e.id) ?? -99) < 20) continue;
          g.last.set(e.id, t);
          g.fx?.pulse();
          drive(e, add(mul(dir, c.p("force") * 0.5), v3(0, 0.25, 0)));
          effect(e, "slowness", 20, 1);
          c.particle("grimoire:spectral_glint", bodyCenter(e), { color: SPECTRUM[gates.indexOf(g) % 7], radius: 0.6, count: 0.8 });
          c.sound("grimoire.prism_light.glass", e.location, 0.6, 1.3);
        }
      }
    }
    yield 1;
  }
}
function* kaleidoscopeTheater(c) {
  const center = c.player.location;
  const theater = c.fx("grimoire:fx_pr_kaleido", center, { yaw: c.yaw, phase: 1, size: c.p("radius") / 6 * c.area });
  c.sound("grimoire.prism_light.hum", center, 1.3, 0.8);
  yield 18;
  theater?.phase(2);
  const n = c.p("figures");
  const figs = [];
  for (let k = 0; k < n; k++) {
    figs.push({ fx: c.fx("grimoire:fx_pr_figure", center, { yaw: c.yaw, phase: 1 }), decoy: spawnDecoy(c, center), slot: k });
  }
  let rot = c.yaw;
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    rot += 1.2;
    if (t % 40 === 39) {
      theater?.pulse();
      for (const f of figs) {
        f.slot = (f.slot + 2) % n;
        f.fx?.pulse();
      }
      c.sound("grimoire.prism_light.chime", center, 0.8, 1.2);
    }
    figs.forEach((f) => {
      const pos = c.ground(add(center, mul(rotY(v3(0, 0, 1), rot + f.slot * 360 / n), 3.6)), 4);
      f.fx?.move(pos).yaw(c.player.getRotation().y + (f.slot % 2 ? 180 : 0));
      f.decoy?.move(pos);
    });
    if (t % 30 === 5) {
      for (const e of c.enemies(center, c.p("radius") + 8)) {
        const nearest = figs.reduce((a, b) => hdist(a.fx?.location ?? center, e.location) < hdist(b.fx?.location ?? center, e.location) ? a : b);
        lure(e, nearest.decoy);
        if (e.typeId === "minecraft:player") effect(e, "blindness", 30, 0);
      }
    }
    yield 1;
  }
}
function* interferenceTapestry(c) {
  const { point } = c.aimGround(c.p("range"));
  const side = rotY(flatNorm(c.dir), 90);
  const half = c.p("width") * c.area / 2;
  const A = c.ground(add(point, mul(side, -half)), 8);
  const B = c.ground(add(point, mul(side, half)), 8);
  const ea = c.fx("grimoire:fx_pr_emitter", A, { phase: 1, size: c.area });
  const eb = c.fx("grimoire:fx_pr_emitter", B, { phase: 1, size: c.area });
  c.sound("grimoire.prism_light.hum", point, 1.2, 1.3);
  yield 10;
  const tap = c.fx("grimoire:fx_pr_tapestry", A, { dir: sub(B, A), len: dist(A, B), phase: 1, size: c.area });
  const decoys = [spawnDecoy(c, A), spawnDecoy(c, B)];
  yield 10;
  const base = Math.min(A.y, B.y);
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 10 === 0) {
      const shift = t / 20 * 6 % 16;
      const inVeil = (e) => {
        const ab = sub(B, A);
        const k = Math.max(0, Math.min(1, dot(sub(e.location, A), ab) / dot(ab, ab)));
        const nearest = lerp(A, B, k);
        return hdist(e.location, nearest) < 2.4 && e.location.y - base < 4.5;
      };
      const bright = (e) => (((e.location.y + bodyHeight(e) * 0.5 - base) * 16 - shift) % 16 + 16) % 16 < 8;
      for (const e of c.enemies(point, half + 4)) {
        if (!inVeil(e) || !bright(e)) continue;
        effect(e, "weakness", 30, 1);
        if (e.typeId === "minecraft:player") effect(e, "blindness", 30, 0);
        else lure(e, decoys[t % 20 === 0 ? 0 : 1]);
        glints(c, bodyCenter(e), 0.5, 0.5);
      }
      for (const a of alliesNear(c, point, half + 4)) if (inVeil(a) && !bright(a)) effect(a, "invisibility", 24, 0);
    }
    yield 1;
  }
  tap?.dissolve(12);
  ea?.dissolve(12);
  eb?.dissolve(12);
}
function* raylineStride(c) {
  const p = c.player;
  const fwd = flatNorm(c.dir);
  const side = rotY(fwd, 90);
  const feet = p.location;
  const wanted = [add(feet, add(add(mul(fwd, 4), mul(side, 1.4)), v3(0, 0.6, 0))), add(feet, add(add(mul(fwd, 8), mul(side, -1.4)), v3(0, 0.6, 0))), add(feet, mul(fwd, c.p("range")))];
  const route = [feet];
  for (const w of wanted) {
    const s = safeSpot(c.dim, w);
    if (!s || !segmentClear(c, add(route[route.length - 1], v3(0, 0.1, 0)), add(s, v3(0, 0.1, 0)))) break;
    route.push(s);
  }
  if (route.length < 2 || dist(route[route.length - 1], feet) < 3) throw new Fizzle("No clear light path");
  const marks = route.slice(1, -1).map((m) => c.fx("grimoire:fx_pr_waypoint", add(m, v3(0, 1.4, 0)), { phase: 1 }));
  for (let k = 0; k < route.length - 1; k++) {
    const r = ray(c, add(route[k], v3(0, 1, 0)), add(route[k + 1], v3(0, 1, 0)), k === 0 ? WHITE_VARIANT : k * 2);
    c.run(dissolveLater3(r, 16, 6), "path");
  }
  c.sound("grimoire.prism_light.beam", feet, 1, 1.3);
  yield 4;
  grantFallImmunity(p.id, 40);
  let i = 0;
  for (let k = 0; k < route.length - 1; k++) {
    const A = route[k], B = route[k + 1];
    const steps = Math.max(2, Math.ceil(dist(A, B) / 1.3));
    for (let s = 1; s <= steps && c.ok; s++) {
      const at = lerp(A, B, s / steps);
      try {
        p.teleport(at, { keepVelocity: false });
      } catch {
        break;
      }
      if (i++ % 2 === 0) {
        const after = c.fx("grimoire:fx_pr_afterimage", at, { yaw: p.getRotation().y, variant: i % 7, phase: 1 });
        c.run(dissolveLater3(after, 8, 6), "after");
      }
      yield 1;
    }
  }
  glints(c, add(p.location, v3(0, 1, 0)), 1, 1);
  for (const m of marks) m?.dissolve(8);
  yield 6;
}
function* iridescentSail(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pr_sail", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.prism_light.sail", p.location, 1, 1);
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    grantFallImmunity(p.id, 30);
    if (!p.isOnGround) {
      effect(p, "slow_falling", 12, 0);
      if (t % 3 === 0) {
        const look = flatNorm(p.getViewDirection());
        let vy = -0.08;
        try {
          vy = Math.min(-0.06, Math.max(-0.22, p.getVelocity().y));
        } catch {
        }
        drive(p, { ...mul(look, c.p("glide") * 0.6), y: vy });
      }
      if (t % 4 === 0) glints(c, add(p.location, v3(0, 2.4, 0)), 1.2, 0.4);
    }
    if (t === 10) fx?.phase(2);
    yield 1;
  }
}
function* spectralDiagnosis(c) {
  const target = primaryTarget2(c, c.p("range"));
  if (!target) throw new Fizzle("Nothing to analyse");
  const at = add(c.eye(), add(mul(flatNorm(c.dir), 0.6), v3(0, 0.8, 0)));
  const scope = c.fx("grimoire:fx_pr_spectroscope", at, { dir: sub(bodyCenter(target), at), len: 1, phase: 1 });
  c.sound("grimoire.prism_light.scan", at, 1, 1);
  yield 14;
  scope?.phase(2);
  for (let t = 0; t < 20 && target.isValid; t++) {
    const tc = bodyCenter(target);
    scope?.aim(sub(tc, at)).length(dist(at, tc) / 1);
    if (t % 4 === 0) glints(c, tc, 0.6, 0.5);
    yield 1;
  }
  if (!target.isValid) return;
  scope?.phase(3);
  c.sound("grimoire.prism_light.chime", at, 1, 1.4);
  yield 16;
  scope?.dissolve(10);
  const ticks = c.p("duration") * 20;
  markVulnerable(target, c.player.id, c.p("mult"), ticks);
  c.onCleanup(() => clearVulnerable(target.id, c.player.id));
  const mark = c.fx("grimoire:fx_pr_weakpoint", bodyCenter(target), { phase: 1, size: Math.max(0.7, bodyHeight(target) / 1.9) });
  for (let t = 0; t < ticks && target.isValid; t++) {
    mark?.follow(target, v3(0, bodyHeight(target) * 0.6, 0), 0);
    yield 1;
  }
}
function* whitepointBenediction(c) {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pr_benediction", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.prism_light.charge", p.location, 0.8, 1.2);
  for (let t = 0; t < 10; t++) {
    fx?.follow(p);
    yield 1;
  }
  fx?.phase(2);
  c.sound("grimoire.prism_light.hum", p.location, 1, 1.2);
  for (let t = 0; t < 24; t++) {
    fx?.follow(p);
    yield 1;
  }
  fx?.phase(3);
  c.sound("grimoire.prism_light.heal", p.location, 1.2, 1);
  const pulses = c.p("pulses");
  for (let k = 0; k < pulses; k++) {
    for (const a of alliesNear(c, p.location, c.p("radius"))) {
      healAndCleanse(a, c.p("heal") / pulses, k === 0);
      c.particle("grimoire:light_motes", a.location, { color: PE, color2: CH, radius: 0.8, count: 0.8 });
    }
    c.particle("grimoire:glow_flash", add(p.location, v3(0, 1.5, 0)), { color: WT, size: 4 });
    for (let t = 0; t < 10; t++) {
      fx?.follow(p);
      yield 1;
    }
  }
  c.particle("grimoire:glass_sparkle", add(p.location, v3(0, 2, 0)), { radius: 2, count: 2, size: 1 });
  fx?.phase(15);
  yield 10;
}
function* chromaticObservatory(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const apex = add(point, v3(0, c.p("height"), 0));
  const obs = c.fx("grimoire:fx_pr_observatory", apex, { yaw: c.yaw, phase: 1, size: c.area });
  c.fx("grimoire:fx_circle_pr", add(point, v3(0, 0.06, 0)), { size: c.p("allyRadius"), variant: 0, phase: 2 });
  c.sound("grimoire.prism_light.crown", apex, 1.2, 1.2);
  yield 30;
  obs?.phase(2);
  const focals = [];
  for (let k = 0; k < c.p("focals"); k++) {
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), c.yaw + k * 120), R * 0.4)), 10);
    focals.push({ pos: at, fx: c.fx("grimoire:fx_pr_focal", at, { phase: 1, size: c.area }) });
  }
  const total = c.p("duration") * 20;
  for (let t = 0; t < total - 40; t++) {
    const targets = nearestEnemies(c, point, R, focals.length);
    focals.forEach((f, k) => {
      const tgt = targets[k % Math.max(1, targets.length)];
      if (tgt?.isValid) f.pos = lerp(f.pos, c.ground(tgt.location, 4), 0.14);
      f.fx?.move(f.pos);
    });
    if (t % c.p("interval") === c.p("interval") - 1) {
      for (const f of focals) {
        f.fx?.pulse();
        for (const e of c.enemies(f.pos, 2)) c.hit(e, c.p("focalDamage"));
        c.particle("grimoire:glow_flash", add(f.pos, v3(0, 0.5, 0)), { color: CH, size: 3 });
      }
      c.sound("grimoire.prism_light.focus", point, 1, 1.2);
    }
    if (t % 20 === 0) {
      for (const a of alliesNear(c, point, c.p("allyRadius"))) {
        effect(a, "resistance", 30, 1);
        effect(a, "regeneration", 30, 0);
      }
      c.particle("grimoire:light_motes", point, { color: PE, color2: CH, radius: c.p("allyRadius"), count: 1 });
    }
    yield 1;
  }
  obs?.phase(3);
  for (const f of focals) f.fx?.dissolve(6);
  c.sound("grimoire.prism_light.focus", apex, 1.5, 0.8);
  yield 22;
  obs?.phase(4);
  const ill = c.fx("grimoire:fx_pr_illumination", add(point, v3(0, 0.2, 0)), { yaw: c.yaw, phase: 1, size: R / 10 * 1 });
  c.sound("grimoire.prism_light.crown", point, 1.6, 1);
  c.flash(point, R * 2, { r: 1, g: 0.98, b: 0.92 }, 0.12);
  shock(c, point, R, c.p("finalDamage"), { knock: 0.9, up: 0.3, color: WT, color2: CH, minK: 0.55, particle: "grimoire:ring_h" });
  c.run(dissolveLater3(ill, 30, 12), "illumination");
  yield 30;
}
function segIntersect(a, b, c, d) {
  const r = { x: b.x - a.x, z: b.z - a.z };
  const s = { x: d.x - c.x, z: d.z - c.z };
  const den = r.x * s.z - r.z * s.x;
  if (Math.abs(den) < 1e-6) return void 0;
  const t = ((c.x - a.x) * s.z - (c.z - a.z) * s.x) / den;
  const u = ((c.x - a.x) * r.z - (c.z - a.z) * r.x) / den;
  if (t <= 0.05 || t >= 0.95 || u <= 0.05 || u >= 0.95) return void 0;
  return { x: a.x + r.x * t, y: a.y, z: a.z + r.z * t };
}
function* colorlessCoronation(c) {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const H = c.p("height");
  const fogged = /* @__PURE__ */ new Set();
  const fog = () => {
    for (const pl of c.dim.getPlayers({ location: point, maxDistance: R + 6 })) {
      if (fogged.has(pl.id)) continue;
      fogged.add(pl.id);
      try {
        pl.runCommand("fog @s push grimoire:coronation grimoire_pr15");
      } catch {
      }
    }
  };
  c.onCleanup(() => {
    for (const id of fogged) {
      try {
        c.dim.getPlayers().find((x) => x.id === id)?.runCommand("fog @s remove grimoire_pr15");
      } catch {
      }
    }
  });
  fog();
  c.fx("grimoire:fx_circle_pr", add(point, v3(0, 0.06, 0)), { size: R * 0.8, variant: 2, phase: 1 });
  const prisms = [];
  for (let k = 0; k < 7; k++) {
    const at = add(point, add(mul(rotY(v3(0, 0, 1), c.yaw + k * (360 / 7)), R * 0.72), v3(0, H, 0)));
    prisms.push({ at, fx: c.fx("grimoire:fx_pr_colossus", at, { phase: 1, size: c.area }) });
    yield 2;
  }
  const shaft = ray(c, add(point, v3(0, H + 16, 0)), add(point, v3(0, H, 0)), WHITE_VARIANT, 3);
  c.sound("grimoire.prism_light.crown", point, 1.8, 0.7);
  yield 16;
  const curtains = [];
  for (let k = 0; k < 7; k++) {
    const ang = c.yaw + k * (360 / 7) + 25;
    const a = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), R)), 12);
    const b = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), -R * 0.6)), 12);
    curtains.push({ a, b, fx: c.fx("grimoire:fx_pr_curtain", a, { dir: flatNorm(sub(b, a)), variant: k, phase: 1, size: 0.5 * c.area }), hit: /* @__PURE__ */ new Set() });
  }
  for (let t = 0; t < 60; t++) {
    curtains.forEach((cu, k) => {
      const kk = Math.max(0, Math.min(1, (t - k * 3) / 45));
      const pos = lerp(cu.a, cu.b, kk);
      cu.fx?.move(pos);
      for (const e of c.enemies(pos, 3)) {
        if (cu.hit.has(e.id)) continue;
        cu.hit.add(e.id);
        c.hit(e, c.p("curtainDamage"));
        c.particle("grimoire:spectral_glint", bodyCenter(e), { color: SPECTRUM[k], radius: 0.6, count: 0.6 });
      }
    });
    if (t % 10 === 0) fog();
    yield 1;
  }
  for (const cu of curtains) cu.fx?.dissolve(10);
  for (const p of prisms) p.fx?.phase(2);
  c.sound("grimoire.prism_light.sweep", point, 1.6, 0.8);
  for (let wave = 0; wave < 3 && c.ok; wave++) {
    const chords = [];
    for (let k = 0; k < 7; k++) {
      const a = prisms[k].at, b = prisms[(k + 3 + wave) % 7].at;
      chords.push([a, b]);
      const r = ray(c, a, b, k, 1.4);
      c.run(dissolveLater3(r, 24, 6), "chord");
    }
    const crossings = [];
    for (let i = 0; i < 7 && crossings.length < 7; i++)
      for (let j = i + 1; j < 7 && crossings.length < 7; j++) {
        const x = segIntersect(chords[i][0], chords[i][1], chords[j][0], chords[j][1]);
        if (x && crossings.every((q) => hdist(q, x) > 3)) crossings.push(x);
      }
    yield 8;
    for (const x of crossings) {
      const g = c.ground(x, 20);
      const fl = c.fx("grimoire:fx_pr_flower", g, { yaw: Math.random() * 360, phase: 1, size: c.area });
      c.run((function* () {
        yield 12;
        fl?.phase(3);
        yield 10;
        fl?.dissolve(6);
      })(), "flower");
      for (const e of c.enemies(g, 3)) c.hit(e, c.p("bloomDamage"));
      glints(c, add(g, v3(0, 1.5, 0)), 1.6, 1);
    }
    c.sound("grimoire.prism_light.chime", point, 1.3, 0.9 + wave * 0.15);
    fog();
    yield 22;
  }
  for (const p of prisms) p.fx?.phase(3);
  for (const p of prisms) {
    const back = ray(c, p.at, add(point, v3(0, H, 0)), prisms.indexOf(p), 1.2);
    c.run(dissolveLater3(back, 18, 6), "return");
  }
  yield 16;
  const crown = c.fx("grimoire:fx_pr_crown", add(point, v3(0, H, 0)), { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.prism_light.crown", point, 2, 1);
  yield 34;
  crown?.phase(2);
  shaft?.dissolve(10);
  c.sound("grimoire.prism_light.focus", point, 1.8, 0.7);
  yield 20;
  const bloom = c.fx("grimoire:fx_pr_bloom", point, { yaw: c.yaw, phase: 1, size: R / 12 * 1 });
  c.flash(point, R * 2.5, { r: 1, g: 1, b: 1 }, 0.25);
  c.shake(point, R * 3, 0.7, 1);
  shock(c, point, R * 0.65, c.p("finalDamage"), { knock: 1.2, up: 0.5, color: WT, color2: CH, minK: 0.6, particle: "grimoire:ring_h" });
  yield 24;
  bloom?.phase(3);
  crown?.phase(3);
  yield 18;
  for (const p of prisms) p.fx?.dissolve(10);
  c.particle("grimoire:glass_sparkle", add(point, v3(0, H, 0)), { radius: R * 0.5, count: 3, size: 1.4 });
  crown?.dissolve(14);
  bloom?.dissolve(10);
  yield 16;
}

// src/spells/prism_light/index.ts
var S6 = "prism_light";
var PRISM_LIGHT = [
  {
    code: "PR01",
    id: "prism_light.sevenfold_verdict",
    school: S6,
    name: "Sevenfold Verdict",
    cooldown: 7,
    charge: 10,
    enhanceable: true,
    params: { damage: 3, starDamage: 10, starRadius: 3, range: 30 },
    blurb: "A prism splits one white beam into seven ribbons that strike from seven sides, then converge in a star.",
    cast: sevenfoldVerdict
  },
  {
    code: "PR02",
    id: "prism_light.total_internal_reflection",
    school: S6,
    name: "Total Internal Reflection",
    cooldown: 13,
    charge: 12,
    enhanceable: true,
    params: { prisms: 5, radius: 4.5, damage: 14, beamDamage: 3, range: 28 },
    blurb: "A beam zigzags through a ring of prisms and leaves toward the target from an unexpected angle.",
    cast: totalInternalReflection
  },
  {
    code: "PR03",
    id: "prism_light.caustic_bloom",
    school: S6,
    name: "Caustic Bloom",
    cooldown: 19,
    charge: 16,
    enhanceable: true,
    params: { lenses: 3, damage: 9, radius: 2.6, range: 28, spread: 5 },
    blurb: "Giant lenses cast flower-shaped caustics that hunt enemies, then contract into burning focal points.",
    cast: causticBloom
  },
  {
    code: "PR04",
    id: "prism_light.fraunhofer_lattice",
    school: S6,
    name: "Fraunhofer Lattice",
    cooldown: 26,
    charge: 18,
    enhanceable: true,
    params: { bands: 7, damage: 7, length: 14, spread: 9, duration: 5, sweep: 60 },
    blurb: "A diffraction grating fans bright spectral bands across the field; the dark gaps between are safe.",
    cast: fraunhoferLattice
  },
  {
    code: "PR05",
    id: "prism_light.brewsters_veil",
    school: S6,
    name: "Brewster's Veil",
    cooldown: 27,
    charge: 12,
    enhanceable: true,
    params: { duration: 15, panels: 3, reduction: 0.4 },
    blurb: "Polarising panels in front of you turn projectiles aside along their edges.",
    cast: brewstersVeil
  },
  {
    code: "PR06",
    id: "prism_light.parallax_displacement",
    school: S6,
    name: "Parallax Displacement",
    cooldown: 32,
    charge: 12,
    enhanceable: true,
    params: { duration: 20, offset: 1.6, hop: 4 },
    blurb: "Your image splits into red, green and blue at a false position; the first blow shatters it and you slip away.",
    cast: parallaxDisplacement
  },
  {
    code: "PR07",
    id: "prism_light.chromatic_turnstile",
    school: S6,
    name: "Chromatic Turnstile",
    cooldown: 35,
    charge: 18,
    enhanceable: true,
    params: { gates: 7, radius: 8, duration: 15, force: 1.3, range: 26 },
    blurb: "Seven prism gates refract enemies who pass through them along their marked direction.",
    cast: chromaticTurnstile
  },
  {
    code: "PR08",
    id: "prism_light.kaleidoscope_theater",
    school: S6,
    name: "Kaleidoscope Theater",
    cooldown: 40,
    charge: 20,
    enhanceable: true,
    params: { duration: 14, figures: 6, radius: 6 },
    blurb: "A kaleidoscope of mirrors multiplies your image; enemies turn on the reflections.",
    cast: kaleidoscopeTheater
  },
  {
    code: "PR09",
    id: "prism_light.interference_tapestry",
    school: S6,
    name: "Interference Tapestry",
    cooldown: 43,
    charge: 20,
    enhanceable: true,
    params: { width: 14, duration: 15, range: 24 },
    blurb: "Two coherent light fields weave a veil of bright and dark bands: bright blinds, dark conceals.",
    cast: interferenceTapestry
  },
  {
    code: "PR10",
    id: "prism_light.rayline_stride",
    school: S6,
    name: "Rayline Stride",
    cooldown: 9,
    charge: 6,
    enhanceable: false,
    params: { range: 11 },
    blurb: "Two floating prisms bend a light path ahead; you race along it in colour-separated afterimages.",
    cast: raylineStride
  },
  {
    code: "PR11",
    id: "prism_light.iridescent_sail",
    school: S6,
    name: "Iridescent Sail",
    cooldown: 20,
    charge: 12,
    enhanceable: false,
    params: { duration: 15, glide: 0.32 },
    blurb: "An iridescent delta sail lets you glide where you look and fall softly for 15 seconds.",
    cast: iridescentSail
  },
  {
    code: "PR12",
    id: "prism_light.spectral_diagnosis",
    school: S6,
    name: "Spectral Diagnosis",
    cooldown: 48,
    charge: 18,
    enhanceable: false,
    params: { duration: 15, mult: 1.35, range: 28 },
    blurb: "A spectroscope analyses the target and marks a weak point: you and your allies deal more damage to it.",
    cast: spectralDiagnosis
  },
  {
    code: "PR13",
    id: "prism_light.whitepoint_benediction",
    school: S6,
    name: "Whitepoint Benediction",
    cooldown: 55,
    charge: 20,
    enhanceable: false,
    params: { radius: 8, heal: 10, pulses: 3 },
    blurb: "Seven spectral ribbons recombine into white light that heals and cleanses you and nearby allies.",
    cast: whitepointBenediction
  },
  {
    code: "PR14",
    id: "prism_light.chromatic_observatory",
    school: S6,
    name: "Grand Magic: The Chromatic Observatory",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { radius: 12, duration: 20, focalDamage: 9, focals: 3, interval: 30, finalDamage: 26, height: 10, range: 24, allyRadius: 4 },
    blurb: "A floating optical observatory hunts enemies with focal points and ends in one geometric illumination.",
    cast: chromaticObservatory
  },
  {
    code: "PR15",
    id: "prism_light.colorless_coronation",
    school: S6,
    name: "Imperial Edict: The Colorless Coronation",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 16, range: 40, curtainDamage: 8, bloomDamage: 10, finalDamage: 40, height: 14 },
    blurb: "White light is unwoven into seven curtains, refracted across the field, then crowned back into pure white.",
    cast: colorlessCoronation
  }
];

// src/spells/registry.ts
var BY_SCHOOL = {
  pressure: PRESSURE,
  ice: ICE2,
  blood: BLOOD,
  plasma: PLASMA,
  darkness: DARKNESS,
  prism_light: PRISM_LIGHT
};
var BY_ID = /* @__PURE__ */ new Map();
for (const s of SCHOOLS) {
  const list = BY_SCHOOL[s];
  if (list.length !== 15) throw new Error(`${s} grimoire must contain exactly 15 spells, has ${list.length}`);
  list.forEach((sp, i) => {
    if (sp.school !== s) throw new Error(`${sp.code} is registered in the wrong grimoire`);
    const expected = `${CODE_PREFIX[s]}${String(i + 1).padStart(2, "0")}`;
    if (sp.code !== expected) throw new Error(`spell order mismatch: ${sp.code} at position ${expected}`);
    if (BY_ID.has(sp.id)) throw new Error(`duplicate spell id ${sp.id}`);
    BY_ID.set(sp.id, sp);
  });
}
function spellAt(school, index) {
  const list = BY_SCHOOL[school];
  return list[(index % 15 + 15) % 15];
}
function spellById(id) {
  return BY_ID.get(id);
}
function allSpells() {
  return SCHOOLS.flatMap((s) => BY_SCHOOL[s]);
}
function spellsOf(school) {
  return BY_SCHOOL[school];
}

// src/core/hud.ts
import { system as system13 } from "@minecraft/server";
var GLYPH = {
  pressure: "\uE500",
  ice: "\uE501",
  blood: "\uE502",
  plasma: "\uE509",
  darkness: "\uE50A",
  prism_light: "\uE50B",
  barFull: "\uE503",
  barEmpty: "\uE504",
  ready: "\uE505",
  lock: "\uE506",
  star: "\uE507",
  hourglass: "\uE508"
};
function schoolColor(s) {
  return SCHOOL_COLOR[s];
}
function bar(k, n = 10) {
  const full = Math.round(Math.max(0, Math.min(1, k)) * n);
  return GLYPH.barFull.repeat(full) + GLYPH.barEmpty.repeat(n - full);
}
function renderHud(p, st, school) {
  const now = system13.currentTick;
  const idx = st.selected[school];
  const spell = spellAt(school, idx);
  const col = schoolColor(school);
  const num = String(idx + 1).padStart(2, "0");
  const line1 = `${GLYPH[school]} ${col}${SCHOOL_NAMES[school]} \xA78| \xA7f${num}\xA77/15 ${col}\xA7l${spell.name}\xA7r`;
  let line2;
  const prep = st.prep;
  if (prep && prep.school === school) {
    const sp = spellById(prep.spellId) ?? spell;
    const t = now - prep.startTick;
    const k = t / Math.max(1, sp.charge);
    line2 = k >= 1 ? `${GLYPH.ready} \xA7a\xA7lRelease to cast\xA7r \xA77(hold is safe)` : `\xA77Preparing ${col}${bar(k)}`;
  } else {
    const rem = remainingTicks(st, spell.id);
    if (rem === Number.POSITIVE_INFINITY) line2 = `${GLYPH.hourglass} \xA7bActive \xA77(cooldown starts when it ends)`;
    else if (rem > 0) line2 = `${GLYPH.lock} \xA7cCooldown \xA7f${(rem / 20).toFixed(1)}s \xA77/ ${spell.cooldown}s`;
    else line2 = `${GLYPH.ready} \xA7aREADY \xA77\xB7 hold \xA7fUse\xA77 to prepare, release to cast`;
  }
  if (st.empowered && st.empowered.until > now) line2 += ` \xA76${GLYPH.star}Empowered`;
  if (st.messageUntil > now) line2 = st.message;
  const text = `${line1}
${line2}`;
  if (text === st.hudKey && now - st.hudTick < 30) return;
  st.hudKey = text;
  st.hudTick = now;
  try {
    p.onScreenDisplay.setActionBar(text);
  } catch {
  }
}

// src/core/casting.ts
var EMPOWER = 1.6;
function heldSchool(p) {
  try {
    const inv = p.getComponent("minecraft:inventory");
    const slot = p.selectedSlotIndex;
    const item = inv?.container?.getItem(slot);
    const school = schoolOfItem(item?.typeId);
    if (!school || !item) return void 0;
    return { school, item, slot };
  } catch {
    return void 0;
  }
}
var prepScopes = /* @__PURE__ */ new Map();
var sigils = /* @__PURE__ */ new Map();
var RELEASE_COLORS = {
  pressure: [COLORS.orange, COLORS.gold],
  ice: [COLORS.ice, COLORS.white],
  blood: [COLORS.crimson, COLORS.redgold],
  plasma: [COLORS.violet, COLORS.whitehot],
  darkness: [COLORS.emerald, COLORS.jade],
  prism_light: [COLORS.pearl, COLORS.champagne]
};
var SIGIL = {
  pressure: "grimoire:fx_sigil_p",
  ice: "grimoire:fx_sigil_i",
  blood: "grimoire:fx_sigil_b",
  plasma: "grimoire:fx_sigil_pl",
  darkness: "grimoire:fx_sigil_d",
  prism_light: "grimoire:fx_sigil_pr"
};
var CHARGE_COLORS = {
  pressure: COLORS.orange,
  ice: COLORS.ice,
  blood: COLORS.crimson,
  plasma: COLORS.magenta,
  darkness: COLORS.jade,
  prism_light: COLORS.pearl
};
function endSigil(playerId, flare) {
  const s = sigils.get(playerId);
  sigils.delete(playerId);
  if (!s) return;
  if (flare) {
    s.phase(3);
    s.size(2.2);
    system14.runTimeout(() => s.dissolve(8), 5);
  } else s.dissolve(6);
}
function cancelPrep(p, st, reason) {
  if (!st.prep) return;
  st.prep = void 0;
  endSigil(p.id, false);
  const scope = prepScopes.get(p.id);
  prepScopes.delete(p.id);
  scope?.cleanup(6);
  if (reason) {
    flash2(st, `\xA77${reason}`, 30);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.6 });
    } catch {
    }
  }
}
function cancelPreparation(p, reason) {
  cancelPrep(p, stateOf(p), reason);
}
function onSneakEdge(p, sneaking) {
  const st = stateOf(p);
  if (st.sneaking === sneaking) return;
  st.sneaking = sneaking;
  if (!sneaking) return;
  if (st.prep) cancelPrep(p, st, "Preparation cancelled (crouched)");
  const held = heldSchool(p);
  if (!held) return;
  const next = (st.selected[held.school] + 1) % 15;
  st.selected[held.school] = next;
  st.hudKey = "";
  save(p, st);
  const spell = spellAt(held.school, next);
  try {
    p.playSound("grimoire.ui.page", { volume: 0.8, pitch: 0.9 + next % 5 * 0.05 });
  } catch {
  }
  flash2(st, `${schoolColor(held.school)}${spell.code} \xA7f${spell.name}`, 40);
}
function onStartUse(p, item) {
  const school = schoolOfItem(item.typeId);
  if (!school) return;
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, void 0);
  if (p.isSneaking) {
    flash2(st, "\xA7eStand up (stop crouching) to cast", 40);
    return;
  }
  const spell = spellAt(school, st.selected[school]);
  const rem = remainingTicks(st, spell.id);
  if (rem > 0) {
    flash2(st, Number.isFinite(rem) ? `\xA7c${spell.name} \xA77is on cooldown \xA7c${(rem / 20).toFixed(1)}s` : `\xA7c${spell.name} \xA77is still active`, 40);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.5, pitch: 1.2 });
    } catch {
    }
    return;
  }
  st.prep = {
    school,
    spellIndex: st.selected[school],
    spellId: spell.id,
    slot: p.selectedSlotIndex,
    itemType: item.typeId,
    dimensionId: p.dimension.id,
    startTick: system14.currentTick,
    readyAnnounced: false
  };
  st.hudKey = "";
  try {
    p.playAnimation("animation.grimoire.player.channel", { stopExpression: "!query.is_using_item", blendOutTime: 0.2, controller: "grimoire_channel" });
  } catch {
  }
  p.dimension.playSound(`grimoire.${school}.charge`, p.location, { volume: 0.7 });
  endSigil(p.id, false);
  const sig = spawnFx(p, p.dimension, SIGIL[school], { x: p.location.x, y: p.location.y + 0.06, z: p.location.z }, { size: 1.2, variant: 0, phase: 1 });
  if (sig) sigils.set(p.id, sig);
  if (spell.prepare) {
    const scope = new Prep(p, spell);
    prepScopes.set(p.id, scope);
    try {
      spell.prepare(scope);
    } catch (e) {
      log.error(`${spell.code} prepare failed`, e);
    }
  }
}
function prepValid(p, st) {
  const prep = st.prep;
  if (!prep) return "no preparation";
  if (!p.isValid) return "left";
  const hp = p.getComponent(EntityHealthComponent.componentId);
  if (hp && hp.currentValue <= 0) return "Preparation cancelled";
  if (p.dimension.id !== prep.dimensionId) return "Preparation cancelled (dimension changed)";
  if (p.isSneaking) return "Preparation cancelled (crouched)";
  if (p.selectedSlotIndex !== prep.slot) return "Preparation cancelled (item switched)";
  const held = heldSchool(p);
  if (!held || held.item.typeId !== prep.itemType) return "Preparation cancelled (item switched)";
  return void 0;
}
function tickPreparation(p, st) {
  const prep = st.prep;
  if (!prep) return;
  const bad = prepValid(p, st);
  if (bad) {
    cancelPrep(p, st, bad);
    return;
  }
  const spell = spellById(prep.spellId);
  if (!spell) {
    cancelPrep(p, st, void 0);
    return;
  }
  const t = system14.currentTick - prep.startTick;
  const k = Math.min(1, t / Math.max(1, spell.charge));
  const sig = sigils.get(p.id);
  if (sig) {
    sig.move({ x: p.location.x, y: p.location.y + 0.06, z: p.location.z });
    sig.size(1.2 + k * 0.8);
    if (k >= 1 && sig.getPhase() < 2) sig.phase(2);
  }
  if (t % 3 === 0) {
    const head = p.getHeadLocation();
    const dir = p.getViewDirection();
    const at = { x: head.x + dir.x * 0.9, y: head.y - 0.35 + dir.y * 0.9, z: head.z + dir.z * 0.9 };
    const c = CHARGE_COLORS[prep.school];
    particle(p.dimension, `grimoire:${prep.school}_charge`, at, { color: c, size: 0.4 + k * 0.6, radius: 1.4 - k * 0.8 });
  }
  if (t % 20 === 0 && t > 0) {
    try {
      p.dimension.playSound(`grimoire.${prep.school}.charge`, p.location, { volume: 0.35, pitch: 1 + k * 0.4 });
    } catch {
    }
  }
  if (!prep.readyAnnounced && t >= spell.charge) {
    prep.readyAnnounced = true;
    st.hudKey = "";
    try {
      p.playSound("grimoire.ui.ready", { volume: 0.7 });
    } catch {
    }
  }
}
function onReleaseUse(p) {
  const st = stateOf(p);
  const prep = st.prep;
  if (!prep) return;
  const bad = prepValid(p, st);
  if (bad) {
    cancelPrep(p, st, bad);
    return;
  }
  const spell = spellById(prep.spellId);
  st.prep = void 0;
  endSigil(p.id, true);
  const scope = prepScopes.get(p.id);
  prepScopes.delete(p.id);
  if (!spell) {
    scope?.cleanup();
    return;
  }
  const held = system14.currentTick - prep.startTick;
  if (held < spell.charge) {
    scope?.cleanup(6);
    flash2(st, `\xA77Hold longer to prepare \xA7f${spell.name}`, 40);
    try {
      p.playSound("grimoire.ui.fizzle", { volume: 0.6 });
    } catch {
    }
    return;
  }
  activate(p, st, spell, scope);
}
function onStopUse(p) {
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, "Preparation cancelled");
}
function onCompleteUse(p) {
  const st = stateOf(p);
  if (st.prep) cancelPrep(p, st, "Preparation expired (release to cast)");
}
function activate(p, st, spell, scope) {
  const now = system14.currentTick;
  const empowered = spell.enhanceable && !!st.empowered && st.empowered.until > now;
  const ctx = new Cast(p, spell, empowered ? EMPOWER : 1, empowered);
  if (scope) ctx.adopted = scope.adopt();
  scope?.cleanup(6);
  let routine;
  try {
    routine = spell.cast(ctx);
  } catch (e) {
    ctx.cleanup(4);
    if (e instanceof Fizzle) {
      flash2(st, `\xA77${e.reason}`, 50);
      try {
        p.playSound("grimoire.ui.fizzle", { volume: 0.7 });
      } catch {
      }
      return false;
    }
    log.error(`${spell.code} cast failed`, e);
    flash2(st, `\xA7c${spell.name} failed`, 40);
    return false;
  }
  if (empowered) st.empowered = void 0;
  if (spell.cooldownAfterEnd) st.activeUntilEnd.add(spell.id);
  else startCooldown(st, spell.id, spell.cooldown);
  st.hudKey = "";
  save(p, st);
  try {
    p.playAnimation("animation.grimoire.player.release", { blendOutTime: 0.25, controller: "grimoire_release" });
  } catch {
  }
  sound(p.dimension, `grimoire.${spell.school}.release`, p.location, 1, 1);
  const runeAt = { x: p.location.x, y: p.location.y + 1.1, z: p.location.z };
  const [rc1, rc2] = RELEASE_COLORS[spell.school];
  particle(p.dimension, "grimoire:rune_flash", runeAt, { color: rc1, color2: rc2, radius: 1.3, count: 4, size: 1.4 });
  if (empowered) particle(p.dimension, "grimoire:star_burst", runeAt, { color: COLORS.gold, color2: COLORS.white, radius: 1.4, count: 3, size: 1.6 });
  const playerId = p.id;
  const handle = start(routine ?? emptyRoutine(), `${spell.code}:${p.name}`, playerId, 20 * 200);
  ctx.handle = handle;
  handle.onEnd(() => {
    ctx.cleanup();
    if (spell.cooldownAfterEnd) {
      const pl = world8.getEntity(playerId);
      startCooldown(st, spell.id, spell.cooldown);
      if (pl?.isValid) save(pl, st);
    }
  });
  if (empowered) flash2(st, "\xA76Empowered by stolen equilibrium!", 40);
  return true;
}
function* emptyRoutine() {
}

// src/core/diagnostics.ts
import { system as system15, world as world9 } from "@minecraft/server";
function reply(payload) {
  const text = JSON.stringify(payload);
  system15.sendScriptEvent("grimoire:debug_reply", text);
}
function findPlayer(name) {
  return world9.getAllPlayers().find((p) => p.name === name);
}
function initDiagnostics() {
  system15.afterEvents.scriptEventReceive.subscribe(
    (e) => {
      if (e.id === "grimoire:config") {
        const [rule, value] = e.message.trim().split(/\s+/);
        if (rule && value !== void 0) reply({ kind: "config", result: setRule(rule, value) });
        return;
      }
      if (e.id !== "grimoire:debug") return;
      const [cmd, ...rest] = e.message.trim().split(/\s+/);
      const name = rest.join(" ");
      if (cmd === "state") {
        const p = findPlayer(name);
        if (!p) return reply({ kind: "state", name, error: "no such player" });
        const st = stateOf(p);
        const cooldowns = {};
        for (const sp of allSpells()) {
          const r = remainingTicks(st, sp.id);
          if (r > 0) cooldowns[sp.id] = Number.isFinite(r) ? r : -1;
        }
        reply({
          kind: "state",
          name,
          tick: system15.currentTick,
          selected: st.selected,
          cooldowns,
          preparing: st.prep ? { spell: st.prep.spellId, ticks: system15.currentTick - st.prep.startTick } : null,
          empowered: !!st.empowered && st.empowered.until > system15.currentTick
        });
      } else if (cmd === "world") {
        reply({ kind: "world", tick: system15.currentTick, fx: fxCount(), tempBlocks: liveTempBlocks(), routines: activeRoutines().map((r) => r.label) });
      } else if (cmd === "reset") {
        const p = findPlayer(name);
        if (!p) return;
        const st = stateOf(p);
        clearCooldowns(st);
        save(p, st);
        reply({ kind: "reset", name });
      }
    },
    { namespaces: ["grimoire"] }
  );
}

// src/main.ts
system16.beforeEvents.startup.subscribe((ev) => {
  registerBlockComponents(ev);
  const reg = ev.customCommandRegistry;
  reg.registerEnum("grimoire:book", ["pressure", "ice", "blood", "plasma", "darkness", "prism_light", "all"]);
  reg.registerCommand(
    {
      name: "grimoire:getbook",
      description: "Give yourself a Grimoire (pressure, ice, blood, plasma, darkness, prism_light or all).",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [{ name: "grimoire:book", type: CustomCommandParamType.Enum }]
    },
    (origin, book) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player12)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      const which = !book || book === "all" ? SCHOOLS : [book];
      system16.run(() => {
        const inv = p.getComponent("minecraft:inventory")?.container;
        for (const s of which) inv?.addItem(new ItemStack2(GRIMOIRE_ITEMS[s], 1));
      });
      return { status: CustomCommandStatus.Success, message: `Given: ${which.join(", ")}` };
    }
  );
  reg.registerCommand(
    {
      name: "grimoire:config",
      description: "Set a Grimoire rule: pvp, friendlyFire, harmPassiveMobs, temporaryBlocks, damagePvE, damagePvP, cameraEffects.",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [
        { name: "rule", type: CustomCommandParamType.String },
        { name: "value", type: CustomCommandParamType.String }
      ]
    },
    (_o, rule, value) => {
      if (!rule || value === void 0) return { status: CustomCommandStatus.Success, message: JSON.stringify(rules()) };
      let msg = "";
      system16.run(() => {
        msg = setRule(rule, value);
        world10.sendMessage(`\xA76[Grimoire]\xA7r ${msg}`);
      });
      return { status: CustomCommandStatus.Success, message: `Updating ${rule}...` };
    }
  );
  reg.registerCommand(
    {
      name: "grimoire:resetcooldowns",
      description: "Clear your own spell cooldowns (testing aid for operators).",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      cheatsRequired: true
    },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player12)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      system16.run(() => {
        const st = stateOf(p);
        clearCooldowns(st);
        save(p, st);
      });
      return { status: CustomCommandStatus.Success, message: "Cooldowns cleared." };
    }
  );
  reg.registerCommand(
    {
      name: "grimoire:guide",
      description: "List the 15 spells of the Grimoire you are holding (or all books).",
      permissionLevel: CommandPermissionLevel.Any
    },
    (origin) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player12)) return { status: CustomCommandStatus.Failure };
      system16.run(() => showGuide(p));
      return { status: CustomCommandStatus.Success };
    }
  );
});
function showGuide(p) {
  const held = heldSchool(p);
  const schools = held ? [held.school] : SCHOOLS;
  for (const s of schools) {
    const lines = spellsOf(s).map((sp) => `\xA77${sp.code} \xA7f${sp.name} \xA78(${sp.cooldown}s) \xA77- ${sp.blurb}`);
    p.sendMessage([`\xA7l${s.toUpperCase()} GRIMOIRE\xA7r`, ...lines].join("\n"));
  }
  p.sendMessage("\xA7eCrouch\xA77 = next spell \xB7 \xA7eHold Use\xA77 (standing) = prepare \xB7 \xA7eRelease\xA77 = cast. No mana: only cooldowns.");
}
world10.afterEvents.itemStartUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onStartUse(e.source, e.itemStack);
});
world10.afterEvents.itemReleaseUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId) || stateOf(e.source).prep) onReleaseUse(e.source);
});
world10.afterEvents.itemStopUse.subscribe((e) => {
  onStopUse(e.source);
});
world10.afterEvents.itemCompleteUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onCompleteUse(e.source);
});
world10.afterEvents.entityStartSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player12) onSneakEdge(e.entity, true);
  },
  { entityFilter: { type: "minecraft:player" } }
);
world10.afterEvents.entityStopSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player12) onSneakEdge(e.entity, false);
  },
  { entityFilter: { type: "minecraft:player" } }
);
world10.afterEvents.playerSpawn.subscribe((e) => {
  const st = stateOf(e.player);
  st.sneaking = e.player.isSneaking;
  if (e.initialSpawn) {
    system16.runTimeout(() => {
      if (!e.player.isValid) return;
      e.player.sendMessage("\xA76[Grimoire]\xA7r \xA77Hold a Grimoire: \xA7eCrouch\xA77 to select, \xA7eHold Use\xA77 standing to prepare, \xA7eRelease\xA77 to cast. \xA78/grimoire:guide");
    }, 60);
  }
});
function endPlayer(id, reason) {
  cancelOwned(id, reason);
  clearVulnerableOf(id);
  endBindsOf(id);
  removeWardsOf(id);
  removeAllFxOf(id);
}
world10.beforeEvents.playerLeave.subscribe((e) => {
  const p = e.player;
  const id = p.id;
  try {
    const st = stateOf(p);
    st.prep = void 0;
    save(p, st);
  } catch {
  }
  system16.run(() => {
    endPlayer(id, "owner left");
    forget(id);
    lastDimension.delete(id);
  });
});
var lastDimension = /* @__PURE__ */ new Map();
function onDimensionChanged(p) {
  lastDimension.set(p.id, p.dimension.id);
  cancelPreparation(p, "Preparation cancelled (dimension changed)");
  endPlayer(p.id, "dimension changed");
}
world10.afterEvents.playerDimensionChange.subscribe((e) => {
  if (lastDimension.get(e.player.id) !== e.player.dimension.id) onDimensionChanged(e.player);
});
world10.afterEvents.entityDie.subscribe((e) => {
  const d = e.deadEntity;
  if (d instanceof Player12) {
    cancelPreparation(d);
  }
});
world10.afterEvents.entityHurt.subscribe((e) => {
  const victim = e.hurtEntity;
  const attacker = e.damageSource.damagingEntity;
  if (attacker && victim.isValid && (victim.typeId === "minecraft:player" || victim.hasTag("grimoire_summon"))) noteAggressor(victim, attacker);
  if (victim.isValid) vulnerabilityBonus(victim, e.damage, attacker);
});
function sweepStale(e) {
  try {
    const fam = e.getComponent("minecraft:type_family");
    if (!fam) return;
    if ((fam.hasTypeFamily(FX_FAMILY) || fam.hasTypeFamily(SUMMON_FAMILY)) && isStaleConstruct(e)) e.remove();
  } catch {
  }
}
world10.afterEvents.entityLoad.subscribe((e) => sweepStale(e.entity));
world10.afterEvents.entitySpawn.subscribe((e) => {
  if (e.cause === EntityInitializationCause.Loaded) sweepStale(e.entity);
});
world10.afterEvents.worldLoad.subscribe(() => {
  for (const id of ["overworld", "nether", "the_end"]) {
    try {
      for (const e of world10.getDimension(id).getEntities({ families: [FX_FAMILY] })) sweepStale(e);
      for (const e of world10.getDimension(id).getEntities({ families: [SUMMON_FAMILY] })) sweepStale(e);
    } catch {
    }
  }
  log.warn(`loaded: ${allSpells().length} spells, PvP ${rules().pvp ? "on" : "off"}`);
});
initDefense();
initHooks();
initDiagnostics();
system16.runInterval(() => {
  const now = system16.currentTick;
  tickRoutines(now);
  tickBinds(now);
  flushDamage(now);
  for (const p of world10.getAllPlayers()) {
    if (!p.isValid) continue;
    const dimId = p.dimension.id;
    const known = lastDimension.get(p.id);
    if (known === void 0) lastDimension.set(p.id, dimId);
    else if (known !== dimId) onDimensionChanged(p);
    const st = stateOf(p);
    const sneaking = p.isSneaking;
    if (sneaking !== st.sneaking) onSneakEdge(p, sneaking);
    if (st.prep) tickPreparation(p, st);
    if (now % 2 === 0) {
      const held = heldSchool(p);
      if (held) renderHud(p, st, held.school);
    }
    if (st.dirty && now % 100 === 0) save(p, st);
  }
  if (now % 100 === 0) pruneAggressors();
}, 1);
