// src/main.ts
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  EntityInitializationCause,
  ItemStack as ItemStack2,
  Player as Player8,
  system as system10,
  world as world9
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
var norm = (a) => {
  const l = len(a);
  return l < 1e-9 ? { x: 0, y: 0, z: 1 } : mul(a, 1 / l);
};
var clamp = (v, lo, hi) => v < lo ? lo : v > hi ? hi : v;
var floor3 = (l) => ({ x: Math.floor(l.x), y: Math.floor(l.y), z: Math.floor(l.z) });
var DEG = Math.PI / 180;
function yawPitchOf(d) {
  const n = norm(d);
  const yaw = Math.atan2(-n.x, n.z) / DEG;
  const pitch = -Math.asin(clamp(n.y, -1, 1)) / DEG;
  return { yaw, pitch };
}
function segDist(p, a, b) {
  const ab = sub(b, a);
  const l2 = dot(ab, ab);
  const t = l2 < 1e-9 ? 0 : clamp(dot(sub(p, a), ab) / l2, 0, 1);
  return { d: dist(p, add(a, mul(ab, t))), t };
}

// src/core/blocks.ts
var TEMP_BLOCK_IDS = ["grimoire:pressure_barrier", "grimoire:frost_wall", "grimoire:blood_thornwall"];
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
import { EntityHealthComponent, system as system8, world as world6 } from "@minecraft/server";

// src/spells/context.ts
import { system as system4 } from "@minecraft/server";

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
function hit(caster, target, amount, opts = {}) {
  if (!target.isValid || amount <= 0) return;
  const casterId = typeof caster === "string" ? caster : caster.id;
  const kind = opts.kind ?? "spell";
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
  redgold: { r: 1, g: 0.5, b: 0.25 }
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
  startTick = system4.currentTick;
  dimensionId;
  handle;
  wards = [];
  tempBlocks;
  /** Constructs handed over from the preparation phase (formation already visible). */
  adopted = [];
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
    try {
      const hit2 = this.dim.getBlockFromRay(add(p, v3(0, 0.5, 0)), v3(0, -1, 0), {
        maxDistance: maxDown + 0.5,
        includeLiquidBlocks: true,
        includePassableBlocks: false
      });
      if (hit2) return { x: p.x, y: hit2.block.location.y + 1, z: p.z };
    } catch {
    }
    return { x: p.x, y: Math.floor(p.y), z: p.z };
  }
  /** Aimed ground point (where area spells land). */
  aimGround(maxDistance) {
    const a = this.aim(maxDistance);
    const base = a.entity ? a.entity.location : a.point;
    return { point: this.ground(base, 30), target: a.entity };
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
    for (const w of this.wards) removeWard(w);
    this.wards.length = 0;
    this.tempBlocks?.clear();
    for (const f of this.adopted) f.dissolve(dissolveTicks);
    this.adopted.length = 0;
    super.cleanup(dissolveTicks);
  }
};

// src/spells/placeholder.ts
function* placeholder(c) {
  const col = c.spell.school === "pressure" ? COLORS.orange : c.spell.school === "ice" ? COLORS.ice : COLORS.crimson;
  c.particle(`grimoire:${c.spell.school}_charge`, c.origin, { color: col, size: 1, radius: 1 });
  yield 1;
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
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
    cast: placeholder
  }
];

// src/spells/ice/index.ts
var S2 = "ice";
var ICE = [
  {
    code: "I01",
    id: "ice.sovereign_lance",
    school: S2,
    name: "Glacial Sovereign's Lance",
    cooldown: 8,
    charge: 12,
    enhanceable: true,
    params: { damage: 12, spikeDamage: 8, range: 48, speed: 1.8, spikes: 8, spikeRadius: 2.2, pierce: 3 },
    blurb: "A crystalline spear that pierces, then erupts into giant ice spikes.",
    cast: placeholder
  },
  {
    code: "I02",
    id: "ice.boreal_dragon",
    school: S2,
    name: "Boreal Dragon's Roar",
    cooldown: 20,
    charge: 16,
    enhanceable: true,
    params: { duration: 80, range: 18, angle: 14, tickDamage: 3, interval: 5 },
    blurb: "A crystal dragon head breathes a freezing gale.",
    cast: placeholder
  },
  {
    code: "I03",
    id: "ice.winters_guillotine",
    school: S2,
    name: "Winter's Guillotine",
    cooldown: 14,
    charge: 14,
    enhanceable: true,
    params: { damage: 18, length: 20, width: 3.2, freeze: 60, fractureDamage: 4 },
    blurb: "An ice blade falls from a sky circle and fractures the ground.",
    cast: placeholder
  },
  {
    code: "I04",
    id: "ice.crystal_rain",
    school: S2,
    name: "Thousandfold Crystal Rain",
    cooldown: 25,
    charge: 20,
    enhanceable: true,
    params: { swords: 120, waves: 4, clusters: 20, damage: 6, radius: 10, range: 40 },
    blurb: "Concentric rings of crystal swords rain down in waves.",
    cast: placeholder
  },
  {
    code: "I05",
    id: "ice.eternal_lotus",
    school: S2,
    name: "Lotus of the Eternal Frost",
    cooldown: 28,
    charge: 14,
    enhanceable: true,
    params: { radius: 4, layers: 3, petalCapacity: 2.5, duration: 12 },
    blurb: "A crystal lotus whose petals shatter as they absorb attacks.",
    cast: placeholder
  },
  {
    code: "I06",
    id: "ice.frozen_throne_mirror",
    school: S2,
    name: "Mirror of the Frozen Throne",
    cooldown: 32,
    charge: 14,
    enhanceable: true,
    params: { mirrors: 4, reflects: 3, shardDamage: 6, duration: 15 },
    blurb: "Hexagonal mirrors intercept and reflect projectiles.",
    cast: placeholder
  },
  {
    code: "I07",
    id: "ice.chains_of_niflheim",
    school: S2,
    name: "Chains of Niflheim",
    cooldown: 30,
    charge: 16,
    enhanceable: true,
    params: { targets: 4, duration: 7, dps: 2, range: 32, selectRadius: 8 },
    blurb: "Crystal chains bind enemies and freeze their joints.",
    cast: placeholder
  },
  {
    code: "I08",
    id: "ice.pale_moon_labyrinth",
    school: S2,
    name: "Labyrinth of the Pale Moon",
    cooldown: 40,
    charge: 20,
    enhanceable: true,
    params: { duration: 18, size: 10, range: 24, shiftInterval: 5 },
    blurb: "Frozen walls and towers form a shifting labyrinth.",
    cast: placeholder
  },
  {
    code: "I09",
    id: "ice.whiteout_dominion",
    school: S2,
    name: "Whiteout Dominion",
    cooldown: 45,
    charge: 20,
    enhanceable: true,
    params: { radius: 14, duration: 12, damage: 3, interval: 15 },
    blurb: "A supernatural blizzard that only spares its caster.",
    cast: placeholder
  },
  {
    code: "I10",
    id: "ice.frost_mirror_traverse",
    school: S2,
    name: "Frost Mirror Traverse",
    cooldown: 8,
    charge: 8,
    enhanceable: false,
    params: { range: 20 },
    blurb: "Step into one mirror and out of another.",
    cast: placeholder
  },
  {
    code: "I11",
    id: "ice.winter_seraph",
    school: S2,
    name: "Wings of the Winter Seraph",
    cooldown: 20,
    charge: 14,
    enhanceable: false,
    cooldownAfterEnd: true,
    params: { duration: 15, speed: 0.75 },
    blurb: "Six crystal wings grant controllable flight. Cooldown starts after landing.",
    cast: placeholder
  },
  {
    code: "I12",
    id: "ice.frost_legion",
    school: S2,
    name: "Imperial Frost Legion",
    cooldown: 60,
    charge: 24,
    enhanceable: true,
    params: { duration: 30 },
    blurb: "Summon three crystal knights: longsword, spear and greatshield.",
    cast: placeholder
  },
  {
    code: "I13",
    id: "ice.still_winter_hourglass",
    school: S2,
    name: "Hourglass of Still Winter",
    cooldown: 50,
    charge: 18,
    enhanceable: true,
    params: { radius: 10, countdown: 80, damage: 10, freeze: 100, range: 36 },
    blurb: "When the hourglass empties, a great pulse freezes all enemies.",
    cast: placeholder
  },
  {
    code: "I14",
    id: "ice.everlasting_citadel",
    school: S2,
    name: "Grand Magic: Citadel of the Everlasting Winter",
    cooldown: 90,
    charge: 30,
    enhanceable: true,
    params: { radius: 12, duration: 30, lanceDamage: 9, interval: 40, range: 24 },
    blurb: "An imperial ice palace rises; its towers fire ice lances.",
    cast: placeholder
  },
  {
    code: "I15",
    id: "ice.the_last_winter",
    school: S2,
    name: "Imperial Edict: The Last Winter",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 22, range: 40, beamDamage: 8, finalDamage: 30 },
    blurb: "Silent world, crown of absolute frost, then the final descent.",
    cast: placeholder
  }
];

// src/spells/pressure/index.ts
var S3 = "pressure";
var PRESSURE = [
  {
    code: "P01",
    id: "pressure.lance",
    school: S3,
    name: "Pressure Lance",
    cooldown: 6,
    charge: 8,
    enhanceable: true,
    params: { damage: 14, range: 48, speed: 2.4, radius: 1, impactDamage: 6, impactRadius: 2.5 },
    blurb: "Layered air compressed into a piercing orange-gold lance.",
    cast: placeholder
  },
  {
    code: "P02",
    id: "pressure.atlas_piston",
    school: S3,
    name: "Atlas Piston",
    cooldown: 18,
    charge: 14,
    enhanceable: true,
    params: { damage: 22, radius: 6, waveDamage: 6, waveRadius: 11, range: 40, height: 14, launch: 1.1 },
    blurb: "A colossal translucent copper piston slams the target area.",
    cast: placeholder
  },
  {
    code: "P03",
    id: "pressure.isobaric_severance",
    school: S3,
    name: "Isobaric Severance",
    cooldown: 10,
    charge: 10,
    enhanceable: true,
    params: { damage: 12, delayedDamage: 8, width: 9, range: 32, speed: 1.6, delay: 10 },
    blurb: "A near-invisible cutting plane followed by delayed shockwaves.",
    cast: placeholder
  },
  {
    code: "P04",
    id: "pressure.cataclysm_salvo",
    school: S3,
    name: "Cataclysm Salvo",
    cooldown: 22,
    charge: 16,
    enhanceable: true,
    params: { discs: 24, damage: 6, blastRadius: 2.5, range: 36, volleys: 4 },
    blurb: "Mechanical wings of pressure rings fire successive disc formations.",
    cast: placeholder
  },
  {
    code: "P05",
    id: "pressure.aegis_of_isobars",
    school: S3,
    name: "Aegis of Isobars",
    cooldown: 25,
    charge: 12,
    enhanceable: true,
    params: { radius: 5, layers: 3, layerCapacity: 12, duration: 12 },
    blurb: "A three-layer dome of compressed air that absorbs force and redirects projectiles.",
    cast: placeholder
  },
  {
    code: "P06",
    id: "pressure.counterpressure_mantle",
    school: S3,
    name: "Counterpressure Mantle",
    cooldown: 22,
    charge: 10,
    enhanceable: true,
    params: { duration: 15, reduction: 0.6, reflectDamage: 6, range: 6, knock: 2.6 },
    blurb: "A flowing mantle that contracts, then blasts attackers away.",
    cast: placeholder
  },
  {
    code: "P07",
    id: "pressure.titans_vise",
    school: S3,
    name: "Titan's Vise",
    cooldown: 30,
    charge: 16,
    enhanceable: true,
    params: { targets: 3, pulseDamage: 5, finalDamage: 10, duration: 6, selectRadius: 7, range: 32 },
    blurb: "Hexagonal pressure plates trap and crush up to three enemies.",
    cast: placeholder
  },
  {
    code: "P08",
    id: "pressure.atmospheric_labyrinth",
    school: S3,
    name: "Atmospheric Labyrinth",
    cooldown: 35,
    charge: 20,
    enhanceable: true,
    params: { duration: 15, size: 9, range: 24, height: 3, shiftInterval: 4 },
    blurb: "Columns and shifting barriers of compressed air form a maze.",
    cast: placeholder
  },
  {
    code: "P09",
    id: "pressure.resonance_cage",
    school: S3,
    name: "Resonance Cage",
    cooldown: 28,
    charge: 14,
    enhanceable: true,
    params: { radius: 4.5, pulseDamage: 6, pulses: 6, interval: 20, range: 30 },
    blurb: "A vibrating spherical cage whose synchronized pulses strike inward.",
    cast: placeholder
  },
  {
    code: "P10",
    id: "pressure.pressure_step",
    school: S3,
    name: "Pressure Step",
    cooldown: 5,
    charge: 4,
    enhanceable: false,
    params: { distance: 8 },
    blurb: "A collapsing ring under your feet propels you forward.",
    cast: placeholder
  },
  {
    code: "P11",
    id: "pressure.skyline_rail",
    school: S3,
    name: "Skyline Pressure Rail",
    cooldown: 14,
    charge: 12,
    enhanceable: false,
    params: { length: 40, speed: 1.6, rings: 10 },
    blurb: "An aerial corridor of rings that hurls you across the sky.",
    cast: placeholder
  },
  {
    code: "P12",
    id: "pressure.barometric_omniscience",
    school: S3,
    name: "Barometric Omniscience",
    cooldown: 25,
    charge: 12,
    enhanceable: false,
    params: { radius: 48, duration: 15, maxMarkers: 24 },
    blurb: "Pressure waves reveal every living thing nearby.",
    cast: placeholder
  },
  {
    code: "P13",
    id: "pressure.equilibrium_theft",
    school: S3,
    name: "Equilibrium Theft",
    cooldown: 35,
    charge: 16,
    enhanceable: false,
    params: { radius: 8, buffSeconds: 30 },
    blurb: "Steal the surrounding air into a crystal that empowers your next spell once.",
    cast: placeholder
  },
  {
    code: "P14",
    id: "pressure.isobaric_citadel",
    school: S3,
    name: "Isobaric Citadel",
    cooldown: 75,
    charge: 30,
    enhanceable: true,
    params: { radius: 9, duration: 30, attackInterval: 30, damage: 10, range: 20, maxTargets: 4 },
    blurb: "A fortress of compressed atmosphere that guards allies and strikes back.",
    cast: placeholder
  },
  {
    code: "P15",
    id: "pressure.thousand_atmospheres",
    school: S3,
    name: "Imperial Edict: Thousand Atmospheres",
    cooldown: 180,
    charge: 40,
    enhanceable: true,
    params: { radius: 18, range: 40, layerDamage: 4, collapses: 12, frontDamage: 20 },
    blurb: "Dominion, thousandfold compression, then imperial release.",
    cast: placeholder
  }
];

// src/spells/types.ts
var SCHOOLS = ["pressure", "ice", "blood"];
var GRIMOIRE_ITEMS = {
  pressure: "grimoire:pressure",
  ice: "grimoire:ice",
  blood: "grimoire:blood"
};
var SCHOOL_NAMES = {
  pressure: "Pressure Grimoire",
  ice: "Ice Grimoire",
  blood: "Blood Grimoire"
};
var SCHOOL_COLOR = { pressure: "\xA76", ice: "\xA7b", blood: "\xA7c" };
function schoolOfItem(typeId) {
  switch (typeId) {
    case "grimoire:pressure":
      return "pressure";
    case "grimoire:ice":
      return "ice";
    case "grimoire:blood":
      return "blood";
    default:
      return void 0;
  }
}
var Fizzle = class extends Error {
  constructor(reason) {
    super(reason);
    this.reason = reason;
  }
  reason;
};

// src/spells/registry.ts
var BY_SCHOOL = { pressure: PRESSURE, ice: ICE, blood: BLOOD };
var BY_ID = /* @__PURE__ */ new Map();
for (const s of SCHOOLS) {
  const list = BY_SCHOOL[s];
  if (list.length !== 15) throw new Error(`${s} grimoire must contain exactly 15 spells, has ${list.length}`);
  list.forEach((sp, i) => {
    if (sp.school !== s) throw new Error(`${sp.code} is registered in the wrong grimoire`);
    const expected = `${s[0].toUpperCase()}${String(i + 1).padStart(2, "0")}`;
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
  return [...PRESSURE, ...ICE, ...BLOOD];
}
function spellsOf(school) {
  return BY_SCHOOL[school];
}

// src/core/state.ts
import { system as system5 } from "@minecraft/server";
var PROP = "grimoire:state";
var states = /* @__PURE__ */ new Map();
function stateOf(p) {
  let st = states.get(p.id);
  if (st) return st;
  st = {
    id: p.id,
    name: p.name,
    selected: { pressure: 0, ice: 0, blood: 0 },
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
      for (const k of ["pressure", "ice", "blood"]) {
        const v = saved.s?.[k];
        if (typeof v === "number" && v >= 0 && v < 15) st.selected[k] = Math.floor(v);
      }
      const now = system5.currentTick;
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
  const now = system5.currentTick;
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
  return t === void 0 ? 0 : Math.max(0, t - system5.currentTick);
}
function startCooldown(st, spellId, seconds) {
  st.activeUntilEnd.delete(spellId);
  st.readyAt.set(spellId, system5.currentTick + Math.round(seconds * 20));
  st.dirty = true;
}
function clearCooldowns(st) {
  st.readyAt.clear();
  st.activeUntilEnd.clear();
  st.dirty = true;
}
function flash2(st, msg, ticks = 30) {
  st.message = msg;
  st.messageUntil = system5.currentTick + ticks;
  st.hudKey = "";
}

// src/core/tasks.ts
import { system as system6 } from "@minecraft/server";
var entries = /* @__PURE__ */ new Map();
var nextId = 1;
function start(gen, label, ownerId, maxTicks = 20 * 240) {
  const id = nextId++;
  const entry = {
    gen,
    wake: system6.currentTick,
    ends: [],
    started: system6.currentTick,
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
  step(entry, system6.currentTick);
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

// src/core/hud.ts
import { system as system7 } from "@minecraft/server";
var GLYPH = {
  pressure: "\uE500",
  ice: "\uE501",
  blood: "\uE502",
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
  const now = system7.currentTick;
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
function cancelPrep(p, st, reason) {
  if (!st.prep) return;
  st.prep = void 0;
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
    startTick: system8.currentTick,
    readyAnnounced: false
  };
  st.hudKey = "";
  try {
    p.playAnimation("animation.grimoire.player.channel", { stopExpression: "!query.is_using_item", blendOutTime: 0.2, controller: "grimoire_channel" });
  } catch {
  }
  p.dimension.playSound(`grimoire.${school}.charge`, p.location, { volume: 0.7 });
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
  const t = system8.currentTick - prep.startTick;
  const k = Math.min(1, t / Math.max(1, spell.charge));
  if (t % 3 === 0) {
    const head = p.getHeadLocation();
    const dir = p.getViewDirection();
    const at = { x: head.x + dir.x * 0.9, y: head.y - 0.35 + dir.y * 0.9, z: head.z + dir.z * 0.9 };
    const c = prep.school === "pressure" ? COLORS.orange : prep.school === "ice" ? COLORS.ice : COLORS.crimson;
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
  const scope = prepScopes.get(p.id);
  prepScopes.delete(p.id);
  if (!spell) {
    scope?.cleanup();
    return;
  }
  const held = system8.currentTick - prep.startTick;
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
  const now = system8.currentTick;
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
  world6.getDimension(p.dimension.id);
  const playerId = p.id;
  const handle = start(routine ?? emptyRoutine(), `${spell.code}:${p.name}`, playerId, 20 * 200);
  ctx.handle = handle;
  handle.onEnd(() => {
    ctx.cleanup();
    if (spell.cooldownAfterEnd) {
      const pl = world6.getEntity(playerId);
      startCooldown(st, spell.id, spell.cooldown);
      if (pl?.isValid) save(pl, st);
    }
  });
  if (empowered) flash2(st, "\xA76Empowered by stolen equilibrium!", 40);
  return true;
}
function* emptyRoutine() {
}

// src/spells/hooks.ts
import { world as world7 } from "@minecraft/server";
var listeners = /* @__PURE__ */ new Set();
function dispatch(e) {
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
  world7.afterEvents.entityHurt.subscribe(dispatch);
}

// src/core/diagnostics.ts
import { system as system9, world as world8 } from "@minecraft/server";
function reply(payload) {
  const text = JSON.stringify(payload);
  system9.sendScriptEvent("grimoire:debug_reply", text);
}
function findPlayer(name) {
  return world8.getAllPlayers().find((p) => p.name === name);
}
function initDiagnostics() {
  system9.afterEvents.scriptEventReceive.subscribe(
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
          tick: system9.currentTick,
          selected: st.selected,
          cooldowns,
          preparing: st.prep ? { spell: st.prep.spellId, ticks: system9.currentTick - st.prep.startTick } : null,
          empowered: !!st.empowered && st.empowered.until > system9.currentTick
        });
      } else if (cmd === "world") {
        reply({ kind: "world", tick: system9.currentTick, fx: fxCount(), tempBlocks: liveTempBlocks(), routines: activeRoutines().map((r) => r.label) });
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
system10.beforeEvents.startup.subscribe((ev) => {
  registerBlockComponents(ev);
  const reg = ev.customCommandRegistry;
  reg.registerEnum("grimoire:book", ["pressure", "ice", "blood", "all"]);
  reg.registerCommand(
    {
      name: "grimoire:getbook",
      description: "Give yourself a Grimoire (pressure, ice, blood or all).",
      permissionLevel: CommandPermissionLevel.GameDirectors,
      optionalParameters: [{ name: "grimoire:book", type: CustomCommandParamType.Enum }]
    },
    (origin, book) => {
      const p = origin.sourceEntity;
      if (!(p instanceof Player8)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      const which = !book || book === "all" ? SCHOOLS : [book];
      system10.run(() => {
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
      system10.run(() => {
        msg = setRule(rule, value);
        world9.sendMessage(`\xA76[Grimoire]\xA7r ${msg}`);
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
      if (!(p instanceof Player8)) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
      system10.run(() => {
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
      if (!(p instanceof Player8)) return { status: CustomCommandStatus.Failure };
      system10.run(() => showGuide(p));
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
world9.afterEvents.itemStartUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onStartUse(e.source, e.itemStack);
});
world9.afterEvents.itemReleaseUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId) || stateOf(e.source).prep) onReleaseUse(e.source);
});
world9.afterEvents.itemStopUse.subscribe((e) => {
  onStopUse(e.source);
});
world9.afterEvents.itemCompleteUse.subscribe((e) => {
  if (schoolOfItem(e.itemStack?.typeId)) onCompleteUse(e.source);
});
world9.afterEvents.entityStartSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player8) onSneakEdge(e.entity, true);
  },
  { entityFilter: { type: "minecraft:player" } }
);
world9.afterEvents.entityStopSneaking.subscribe(
  (e) => {
    if (e.entity instanceof Player8) onSneakEdge(e.entity, false);
  },
  { entityFilter: { type: "minecraft:player" } }
);
world9.afterEvents.playerSpawn.subscribe((e) => {
  const st = stateOf(e.player);
  st.sneaking = e.player.isSneaking;
  if (e.initialSpawn) {
    system10.runTimeout(() => {
      if (!e.player.isValid) return;
      e.player.sendMessage("\xA76[Grimoire]\xA7r \xA77Hold a Grimoire: \xA7eCrouch\xA77 to select, \xA7eHold Use\xA77 standing to prepare, \xA7eRelease\xA77 to cast. \xA78/grimoire:guide");
    }, 60);
  }
});
function endPlayer(id, reason) {
  cancelOwned(id, reason);
  removeWardsOf(id);
  removeAllFxOf(id);
}
world9.beforeEvents.playerLeave.subscribe((e) => {
  const p = e.player;
  const id = p.id;
  try {
    const st = stateOf(p);
    st.prep = void 0;
    save(p, st);
  } catch {
  }
  system10.run(() => {
    endPlayer(id, "owner left");
    forget(id);
  });
});
world9.afterEvents.playerDimensionChange.subscribe((e) => {
  cancelPreparation(e.player, "Preparation cancelled (dimension changed)");
});
world9.afterEvents.entityDie.subscribe((e) => {
  const d = e.deadEntity;
  if (d instanceof Player8) {
    cancelPreparation(d);
  }
});
world9.afterEvents.entityHurt.subscribe((e) => {
  const victim = e.hurtEntity;
  const attacker = e.damageSource.damagingEntity;
  if (attacker && victim.isValid && (victim.typeId === "minecraft:player" || victim.hasTag("grimoire_summon"))) noteAggressor(victim, attacker);
});
function sweepStale(e) {
  try {
    const fam = e.getComponent("minecraft:type_family");
    if (!fam) return;
    if ((fam.hasTypeFamily(FX_FAMILY) || fam.hasTypeFamily(SUMMON_FAMILY)) && isStaleConstruct(e)) e.remove();
  } catch {
  }
}
world9.afterEvents.entityLoad.subscribe((e) => sweepStale(e.entity));
world9.afterEvents.entitySpawn.subscribe((e) => {
  if (e.cause === EntityInitializationCause.Loaded) sweepStale(e.entity);
});
world9.afterEvents.worldLoad.subscribe(() => {
  for (const id of ["overworld", "nether", "the_end"]) {
    try {
      for (const e of world9.getDimension(id).getEntities({ families: [FX_FAMILY] })) sweepStale(e);
      for (const e of world9.getDimension(id).getEntities({ families: [SUMMON_FAMILY] })) sweepStale(e);
    } catch {
    }
  }
  log.warn(`loaded: ${allSpells().length} spells, PvP ${rules().pvp ? "on" : "off"}`);
});
initDefense();
initHooks();
initDiagnostics();
system10.runInterval(() => {
  const now = system10.currentTick;
  tickRoutines(now);
  flushDamage(now);
  for (const p of world9.getAllPlayers()) {
    if (!p.isValid) continue;
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
