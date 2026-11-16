import { Block, Dimension, Entity, EntityDamageCause, Player, Vector3, WeatherType, world } from "@minecraft/server";
import { GOGGLES, ID, SIG } from "../config.js";
import { pose, signal } from "../core/anim.js";
import { solarInfo, SolarInfo, sunDirection, sunElevation, surroundings, weatherIn } from "../core/env.js";
import { flash, focusFov, fx, fxOthers, segment, shake, sound, soundTo } from "../core/fx.js";
import { enchantLevel, heldItem, wear } from "../core/items.js";
import { hint, now, PlayerState, ready, remaining, startCd } from "../core/state.js";
import { alive, canHurt, centerOf, inCone } from "../core/targets.js";
import { add, angleBetween, clamp, dist, floor, norm, rand, rightOf, rotY, scale, sub, v } from "../core/vec.js";
import { scriptDamage } from "../systems/damage.js";
import { dazzle } from "../systems/dazzle.js";
import { addFrost, isColdNative, isFireBorn } from "../systems/frost.js";

const BURNS_IN_SUN = new Set(["minecraft:zombie", "minecraft:zombie_villager", "minecraft:zombie_villager_v2", "minecraft:skeleton",
  "minecraft:stray", "minecraft:phantom", "minecraft:drowned", "minecraft:bogged", "minecraft:parched"]);
const FLIERS = new Set(["minecraft:phantom", "minecraft:bat", "minecraft:vex", "minecraft:blaze", "minecraft:ghast",
  "minecraft:parrot", "minecraft:bee", "minecraft:breeze", "minecraft:allay"]);
const LIGHT = "minecraft:light_block_14";

export const secs = (ticks: number): string => `${(ticks / 20).toFixed(1)}s`;

// ------------------------------------------------------------------ light / sun helpers

const sunDogEntities = new Map<string, Entity>();

export function sunDogNear(p: Player, s: PlayerState): boolean {
  const sd = s.sunDog;
  if (!sd) return false;
  const e = sunDogEntities.get(sd.id);
  return !!e && alive(e) && e.dimension.id === p.dimension.id && dist(e.location, p.location) <= GOGGLES.sunDogRadius;
}

export function info(p: Player, s: PlayerState): SolarInfo {
  return solarInfo(p, now(), sunDogNear(p, s));
}

interface SunCheck {
  attempt: boolean; // the player is looking skywards: treat sneak-use as a Sun Dog attempt
  ok: boolean;
  problem?: string;
}

function sunCheck(p: Player): SunCheck {
  const dir = p.getViewDirection();
  if (p.dimension.id !== "minecraft:overworld") return { attempt: false, ok: false };
  const sd = sunDirection();
  const lookingUp = dir.y > 0.3;
  const ang = angleBetween(dir, sd);
  if (!lookingUp && ang > 40) return { attempt: false, ok: false };
  const e = sunElevation();
  if (e <= 0.14) return { attempt: true, ok: false, problem: e <= 0 ? "§9No sun to catch at night" : "§6The sun hangs too low" };
  if (weatherIn(p.dimension.id) !== WeatherType.Clear) return { attempt: true, ok: false, problem: "§7Clouds hide the sun" };
  let sky = 15;
  try {
    sky = p.dimension.getSkyLightLevel(p.getHeadLocation());
  } catch {
    /* ignore */
  }
  if (sky < 14) return { attempt: true, ok: false, problem: "§7Something blocks the sky" };
  if (ang > GOGGLES.sunDogMaxAngle) return { attempt: true, ok: false, problem: "§6Look straight at the sun" };
  return { attempt: true, ok: true };
}

// ------------------------------------------------------------------ use events

export function startUse(p: Player, s: PlayerState): void {
  const g = s.goggles;
  const t = now();
  g.mode = "none";
  if (p.isSneaking) {
    const chk = sunCheck(p);
    if (chk.attempt) {
      if (s.sunDog) return void hint(s, "§6A Sun Dog already follows you");
      if (!ready(s, "sundog")) return void hint(s, `§7The sky needs ${secs(remaining(s, "sundog"))} before another Sun Dog`);
      if (!chk.ok) return void hint(s, chk.problem ?? "");
      g.mode = "sundog";
      g.start = t;
      pose(p, "sun_reach", true);
      sound(p.dimension, "oddworks.goggles.charge", p.getHeadLocation(), 0.6, 0.6);
      return;
    }
    snowblind(p, s);
    g.mode = "spent";
    return;
  }
  if (!ready(s, "beam")) {
    g.mode = "spent";
    return void hint(s, `§bLenses still frosted: ${secs(remaining(s, "beam"))}`);
  }
  g.mode = "charge";
  g.start = t;
  g.charge = 0;
  g.cap = GOGGLES.minCap;
  g.fullSince = -1;
  g.lastChime = 0;
  pose(p, "goggles_adjust");
  focusFov(p, true, 62);
  g.fovOn = true;
}

export function release(p: Player, s: PlayerState): void {
  const g = s.goggles;
  if (g.mode === "charge") {
    if (g.charge >= GOGGLES.minFire) fireBeam(p, s, g.charge);
    else hint(s, "§7Too little light gathered");
  } else if (g.mode === "sundog") {
    hint(s, "§6Hold your gaze on the sun to catch a Sun Dog");
  }
  endUse(p, s);
}

export function endUse(p: Player, s: PlayerState): void {
  const g = s.goggles;
  g.mode = "none";
  g.charge = 0;
  if (g.fovOn) focusFov(p, false);
  g.fovOn = false;
  signal(p, SIG.gogglesFull, 0);
}

// ------------------------------------------------------------------ per-tick while holding the goggles

export function tickHeld(p: Player, s: PlayerState, using: boolean): void {
  // Glare Ward: the slits keep snow-blindness away
  try {
    if (p.getEffect("blindness")) p.removeEffect("blindness");
  } catch {
    /* ignore */
  }
  const g = s.goggles;
  if (!using) {
    if (g.mode === "charge" || g.mode === "sundog") endUse(p, s);
    return;
  }
  if (g.mode === "charge") tickCharge(p, s);
  else if (g.mode === "sundog") tickCapture(p, s);
}

function tickCharge(p: Player, s: PlayerState): void {
  const g = s.goggles;
  const t = now();
  const inf = info(p, s);
  const item = heldItem(p);
  const rate = GOGGLES.chargePerTick * inf.power * (1 + 0.06 * enchantLevel(item, "power"));
  g.cap = clamp(GOGGLES.minCap + 0.75 * inf.power, GOGGLES.minCap, 1);
  if (g.charge < g.cap) g.charge = Math.min(g.cap, g.charge + rate);
  else g.charge = Math.max(g.cap, g.charge - 0.01);
  const full = g.charge >= g.cap - 1e-6;
  if (full) {
    if (g.fullSince < 0) {
      g.fullSince = t;
      if (g.cap >= 0.999) {
        sound(p.dimension, "oddworks.goggles.full", p.getHeadLocation(), 1.0, 0.8);
        hint(s, "§bFULL CHARGE §7- release!", 30);
      } else {
        hint(s, `§7The lenses hold no more in this light (${Math.round(g.cap * 100)}%)`, 30);
      }
    }
    if (g.cap >= 0.999) signal(p, SIG.gogglesFull, 6);
    if (t - g.fullSince > GOGGLES.overholdTicks) return rimeOver(p, s);
    if (t - g.fullSince > GOGGLES.overholdTicks - 20 && t % 4 === 0) {
      fx(p.dimension, "oddworks:frost_aura", add(p.getHeadLocation(), v(0, -0.2, 0)), { count: 3, size: 0.4 });
      if (t % 8 === 0) soundTo(p, "oddworks.goggles.rime", 1.4, 0.4);
    }
  } else g.fullSince = -1;

  // light being drunk by the slits: motes streaming from the light source into the eyes
  const eye = p.getHeadLocation();
  const view = p.getViewDirection();
  const sink = add(eye, scale(view, 0.35));
  const n = inf.power > 0.15 ? 2 + Math.round(inf.power * 2) : inf.power > 0.04 ? 1 : 0;
  const srcDir = inf.source === "moon" ? scale(sunDirection(), -1) : inf.source === "torch" || inf.source === "dark"
    ? norm(v(rand(-1, 1), rand(0.2, 1), rand(-1, 1))) : sunDirection();
  for (let i = 0; i < n; i++) {
    const from = add(add(eye, scale(srcDir, rand(2.5, 4.5))), v(rand(-0.7, 0.7), rand(-0.4, 0.4), rand(-0.7, 0.7)));
    const d = dist(from, sink);
    fx(p.dimension, "oddworks:sun_mote", from, {
      dir: norm(sub(sink, from)), speed: d / 0.3, life: 0.3,
      size: inf.source === "moon" ? 0.6 : 1,
    });
  }
  if (inf.snowy && t % 3 === 0) {
    // snow reflecting extra light up into the slits
    const env = surroundings(p, t);
    if (env.snow > 0) {
      const gp = add(p.location, v(rand(-3, 3), 0.05, rand(-3, 3)));
      fx(p.dimension, "oddworks:albedo_glint", gp);
      fx(p.dimension, "oddworks:sun_mote", gp, { dir: norm(sub(sink, gp)), speed: dist(gp, sink) / 0.35, life: 0.35, size: 0.8 });
    }
  }
  if (t % 2 === 0) fxOthers(p, "oddworks:slit_glow", add(eye, scale(view, 0.32)), { size: 0.6 + g.charge });
  if (t - g.lastChime >= 12) {
    g.lastChime = t;
    sound(p.dimension, "oddworks.goggles.charge", eye, 0.75 + 0.85 * g.charge, 0.55);
  }
}

function rimeOver(p: Player, s: PlayerState): void {
  const g = s.goggles;
  endUse(p, s);
  g.mode = "spent";
  startCd(s, "beam", GOGGLES.rimeLockout);
  try {
    p.addEffect("slowness", 60, { amplifier: 1, showParticles: false });
  } catch {
    /* ignore */
  }
  fx(p.dimension, "oddworks:frost_mist", p.getHeadLocation(), { count: 6, size: 0.6 });
  sound(p.dimension, "oddworks.goggles.rime", p.getHeadLocation());
  shake(p, 0.08, 0.3);
  hint(s, "§bThe lenses rimed over - the cold bit back", 60);
}

// ------------------------------------------------------------------ skill 1: Glacial Beam

function fireBeam(p: Player, s: PlayerState, charge: number): void {
  const inf = info(p, s);
  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const dir = p.getViewDirection();
  const item = heldItem(p);
  const potency = clamp(0.6 + 0.4 * inf.power, 0.6, 1.25) * (1 + 0.08 * enchantLevel(item, "power"));
  const range = GOGGLES.rangeBase + GOGGLES.rangePerCharge * charge;
  const start = add(eye, scale(dir, 0.45));
  let end = add(eye, scale(dir, range));
  let blockHit: { block: Block; faceLocation: Vector3 } | undefined;
  try {
    blockHit = dim.getBlockFromRay(start, dir, { maxDistance: range, includeLiquidBlocks: true, includePassableBlocks: false });
  } catch {
    /* ray left the world */
  }
  if (blockHit) end = add(blockHit.block.location, blockHit.faceLocation);
  const beamLen = Math.max(0.5, dist(start, end));
  let hits: Entity[] = [];
  try {
    hits = dim.getEntitiesFromRay(start, dir, { maxDistance: beamLen }).map((h) => h.entity).filter((e) => canHurt(p, e, false));
  } catch {
    /* ignore */
  }
  const pierce = 1 + (charge >= 0.66 ? 1 : 0) + (charge >= 0.95 ? 1 : 0);
  const struck = hits.slice(0, pierce);
  let stopAt = end;
  if (hits.length > pierce) stopAt = centerOf(struck[struck.length - 1]);
  struck.forEach((e, i) => {
    const falloff = Math.pow(0.7, i);
    let dmg = (GOGGLES.damageBase + GOGGLES.damagePerCharge * charge * potency) * falloff;
    if (isFireBorn(e)) dmg *= e.typeId === "minecraft:strider" ? 1.5 : 2;
    if (isColdNative(e)) {
      scriptDamage(e, dmg * 0.25, EntityDamageCause.magic, p);
      fx(dim, "oddworks:frost_mist", centerOf(e), { count: 3, size: 0.6 });
    } else {
      scriptDamage(e, dmg, EntityDamageCause.freezing, p);
      addFrost(e, (GOGGLES.frostBase + GOGGLES.frostPerCharge * charge) * falloff * (inf.hot ? 0.6 : 1), p, inf.hot ? 0.5 : 1);
    }
    fx(dim, "oddworks:frost_burst", centerOf(e), { count: 6 + Math.round(8 * charge) });
    if (e.isInWater) freezeTerrain(dim, e.location, 1.6, charge, true);
  });
  if (blockHit && hits.length <= pierce) {
    freezeTerrain(dim, end, 0.8 + 2.2 * charge, charge, false);
  }
  extinguishAlong(dim, start, stopAt);

  // cryogenic discharge
  const len2 = dist(start, stopAt);
  const size = 0.6 + 0.9 * charge;
  segment(dim, "oddworks:frost_beam", start, stopAt, { size });
  segment(dim, "oddworks:frost_beam_glow", start, stopAt, { size });
  fx(dim, "oddworks:frost_beam_sparkle", start, { dir, len: len2, count: Math.round(len2 * 2.5) });
  fx(dim, "oddworks:rime_ring", add(eye, scale(dir, 0.9)), { dir, size: 0.6 + 0.7 * charge });
  fx(dim, "oddworks:frost_burst", stopAt, { count: 8 + Math.round(16 * charge) });
  fx(dim, "oddworks:frost_mist", stopAt, { count: 4 + Math.round(6 * charge), size: 0.6 + charge });
  sound(dim, "oddworks.goggles.discharge", eye, 1.25 - 0.35 * charge, 1);
  sound(dim, "oddworks.goggles.freeze", stopAt, 1.1 - 0.2 * charge, 0.8);
  shake(p, 0.04 + 0.16 * charge, 0.25);
  flash(p, 0.8, 0.95, 1.0, 0.02, 0, 0.18 + 0.2 * charge);
  startCd(s, "beam", GOGGLES.cooldownBase + GOGGLES.cooldownPerCharge * charge);
  if (s.sunDog && inf.source === "sundog") s.sunDog.light -= 14 + 18 * charge;
  wear(p, GOGGLES.wearBeam);
  hint(s, `§bGlacial Beam §7${Math.round(charge * 100)}%${struck.length ? ` - struck ${struck.length}` : ""}`, 30);
}

function setType(b: Block, id: string): void {
  try {
    b.setType(id);
  } catch {
    /* protected / unloaded */
  }
}

/** Water -> frosted ice (melts back like Frost Walker), lava -> obsidian/cobblestone, fire out. */
function freezeTerrain(dim: Dimension, centerPt: Vector3, r: number, charge: number, aroundEntity: boolean): void {
  const c = floor(centerPt);
  const R = Math.ceil(r);
  let froze = 0;
  for (let dx = -R; dx <= R; dx++) {
    for (let dz = -R; dz <= R; dz++) {
      if (dx * dx + dz * dz > r * r) continue;
      for (let dy = -1; dy <= 1; dy++) {
        if (aroundEntity && dx === 0 && dz === 0 && dy >= 0) continue; // never entomb the target itself
        let b: Block | undefined;
        try {
          b = dim.getBlock({ x: c.x + dx, y: c.y + dy, z: c.z + dz });
        } catch {
          continue;
        }
        if (!b) continue;
        const id = b.typeId;
        const above = b.above();
        const open = !above || above.isAir;
        if (id === "minecraft:water" || id === "minecraft:flowing_water") {
          if (open && b.permutation.getState("liquid_depth") === 0) {
            setType(b, "minecraft:frosted_ice");
            froze++;
          }
        } else if (id === "minecraft:lava" || id === "minecraft:flowing_lava") {
          if (!open) continue;
          const depth = b.permutation.getState("liquid_depth");
          if (depth === 0 && charge >= 0.5) setType(b, "minecraft:obsidian");
          else if (depth !== 0) setType(b, "minecraft:cobblestone");
          else continue;
          froze++;
          fx(dim, "oddworks:frost_mist", b.center(), { count: 2, size: 0.8 });
        } else if (id === "minecraft:fire" || id === "minecraft:soul_fire") {
          setType(b, "minecraft:air");
        } else if (id === "minecraft:campfire" || id === "minecraft:soul_campfire") {
          try {
            b.setPermutation(b.permutation.withState("extinguished", true));
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
  if (froze > 0) {
    sound(dim, "oddworks.goggles.freeze", centerPt, 1.0, 0.9);
    fx(dim, "oddworks:frost_mist", centerPt, { count: Math.min(10, 2 + froze), size: 1.2 });
  }
}

function extinguishAlong(dim: Dimension, a: Vector3, b: Vector3): void {
  const d = dist(a, b);
  const dir = norm(sub(b, a));
  for (let k = 0; k < d; k += 0.75) {
    try {
      const blk = dim.getBlock(add(a, scale(dir, k)));
      if (blk && (blk.typeId === "minecraft:fire" || blk.typeId === "minecraft:soul_fire")) setType(blk, "minecraft:air");
    } catch {
      /* ignore */
    }
  }
}

// ------------------------------------------------------------------ skill 2: Snowblind

function snowblind(p: Player, s: PlayerState): void {
  if (!ready(s, "flash")) return void hint(s, `§fSnowblind§7 recovering: ${secs(remaining(s, "flash"))}`);
  const inf = info(p, s);
  if (inf.power < GOGGLES.flashMinPower) {
    sound(p.dimension, "random.fizz", p.getHeadLocation(), 1.6, 0.4);
    startCd(s, "flash", 20);
    return void hint(s, "§8Too dark: the lenses have no glare to give");
  }
  const k = Math.min(inf.power, 1.6) / 1.6;
  const snowBonus = inf.snowy ? 1.3 : 1;
  const range = (6 + 6 * k) * snowBonus;
  const eye = p.getHeadLocation();
  const dir = p.getViewDirection();
  const ticks = Math.round((2 + 3 * Math.min(inf.power, 1.5) / 1.5) * 20 + (inf.snowy ? 20 : 0));
  const targets = inCone(p, eye, dir, range, GOGGLES.flashHalfAngle, true);
  for (const e of targets) {
    dazzle(e, ticks, !FLIERS.has(e.typeId));
    try {
      if (BURNS_IN_SUN.has(e.typeId)) e.setOnFire(Math.ceil(1 + 3 * k), true);
      if (e.getEffect("invisibility")) e.removeEffect("invisibility");
      if (FLIERS.has(e.typeId)) e.applyKnockback({ x: dir.x * 0.3, z: dir.z * 0.3 }, -0.9);
    } catch {
      /* ignore */
    }
    fx(e.dimension, "oddworks:glare_burst", centerOf(e), { size: 0.5 });
  }
  const face = add(eye, scale(dir, 0.35));
  fxOthers(p, "oddworks:glare_flare", face, { size: 0.8 + 0.6 * k });
  fxOthers(p, "oddworks:glare_burst", face, { size: 0.8 + k });
  fx(p.dimension, "oddworks:glare_cone", add(eye, scale(dir, 0.8)), { dir, count: Math.round(18 + 22 * k) });
  sound(p.dimension, "oddworks.goggles.flash", eye, 1.0 + 0.2 * k);
  pose(p, "glare");
  startCd(s, "flash", GOGGLES.flashCooldown);
  if (s.sunDog && inf.source === "sundog") s.sunDog.light -= 20;
  wear(p, GOGGLES.wearFlash);
  hint(s, targets.length ? `§fSnowblind§7 - ${targets.length} dazzled` : "§fSnowblind§7 - no one caught in the glare", 40);
}

// ------------------------------------------------------------------ skill 3: Sun Dog

function tickCapture(p: Player, s: PlayerState): void {
  const g = s.goggles;
  const t = now();
  const chk = sunCheck(p);
  if (!chk.ok) {
    hint(s, chk.problem ?? "§6You looked away from the sun");
    g.mode = "spent";
    return;
  }
  const eye = p.getHeadLocation();
  const view = p.getViewDirection();
  const progress = (t - g.start) / GOGGLES.sunDogCapture;
  const sunAt = add(eye, scale(sunDirection(), 16));
  if (t % 2 === 0) segment(p.dimension, "oddworks:sun_ray", sunAt, add(eye, scale(view, 0.4)), { size: 0.6 + progress });
  if (t === g.start + 1 || t === g.start + 12) {
    // the 22-degree halo: a ring of ice-crystal light around the sun
    fx(p.dimension, "oddworks:sundog_halo", add(eye, scale(sunDirection(), 12)), { size: 5.6, life: 1.4 });
  }
  hint(s, `§6Catching a Sun Dog... ${Math.round(Math.min(1, progress) * 100)}%`, 6);
  if (progress < 1) return;
  createSunDog(p, s);
  g.mode = "spent";
}

function createSunDog(p: Player, s: PlayerState): void {
  const t = now();
  const env = surroundings(p, t);
  const pos = add(add(p.getHeadLocation(), scale(rightOf(p.getViewDirection()), 1.0)), v(0, 0.5, 0));
  let e: Entity;
  try {
    e = p.dimension.spawnEntity(ID.sunDog, pos);
  } catch {
    return void hint(s, "§7The Sun Dog slipped away");
  }
  sunDogEntities.set(e.id, e);
  s.sunDog = { id: e.id, until: t + (env.snowyBiome || env.snow >= 0.3 ? GOGGLES.sunDogLifeSnow : GOGGLES.sunDogLife), light: 100, dim: p.dimension.id };
  startCd(s, "sundog", GOGGLES.sunDogCooldown);
  fx(p.dimension, "oddworks:glare_burst", pos, { size: 1.4 });
  fx(p.dimension, "oddworks:sundog_halo", pos, { size: 1.4, life: 0.8 });
  sound(p.dimension, "oddworks.goggles.sundog", pos);
  wear(p, GOGGLES.wearSunDog);
  hint(s, "§6A Sun Dog follows you - a pocket of noon", 60);
}

export function tickSunDog(p: Player, s: PlayerState): void {
  const sd = s.sunDog;
  if (!sd) return;
  const t = now();
  const e = sunDogEntities.get(sd.id);
  if (!e || !alive(e) || t > sd.until || sd.light <= 0 || p.dimension.id !== sd.dim || dist(e.location, p.location) > 40) {
    return dismissSunDog(p, s);
  }
  const target = add(add(p.getHeadLocation(), rotY(v(1.15, 0, 0), t * 3)), v(0, 0.55 + Math.sin(t / 9) * 0.12, 0));
  try {
    e.teleport(target);
  } catch {
    /* ignore */
  }
  // real light: a light block follows the Sun Dog through caves and nights
  const lp = floor(target);
  if (!sd.lightPos || lp.x !== sd.lightPos.x || lp.y !== sd.lightPos.y || lp.z !== sd.lightPos.z) {
    clearLight(e.dimension, sd.lightPos);
    sd.lightPos = undefined;
    try {
      const b = e.dimension.getBlock(lp);
      if (b && b.isAir) {
        b.setType(LIGHT);
        sd.lightPos = lp;
        rememberLight(e.dimension.id, lp, true);
      }
    } catch {
      /* ignore */
    }
  }
  if (t % 4 === 0) fx(e.dimension, "oddworks:sundog_spark", target);
  if (t % 20 === 0) {
    // a pocket of noon: undead that fear daylight catch fire near it
    try {
      for (const u of e.dimension.getEntities({ location: target, maxDistance: 3.5, families: ["undead"] })) {
        if (BURNS_IN_SUN.has(u.typeId) && canHurt(p, u, true)) u.setOnFire(3, true);
      }
    } catch {
      /* ignore */
    }
  }
  if (sd.until - t === 60) hint(s, "§6Your Sun Dog is fading...", 40);
}

export function dismissSunDog(p: Player | undefined, s: PlayerState): void {
  const sd = s.sunDog;
  if (!sd) return;
  const e = sunDogEntities.get(sd.id);
  if (e && alive(e)) {
    fx(e.dimension, "oddworks:glare_burst", e.location, { size: 0.9 });
    fx(e.dimension, "oddworks:sundog_spark", e.location);
    if (sd.lightPos) clearLight(e.dimension, sd.lightPos);
    try {
      e.remove();
    } catch {
      /* gone */
    }
  } else if (sd.lightPos && p) {
    clearLight(p.dimension, sd.lightPos);
  }
  sunDogEntities.delete(sd.id);
  s.sunDog = undefined;
  if (p) hint(s, "§7The Sun Dog melts back into the sky", 40);
}

// ------------------------------------------------------------------ light block bookkeeping (survives reloads)

const lights = new Map<string, { d: string; x: number; y: number; z: number }>();

function rememberLight(dimId: string, at: Vector3, on: boolean): void {
  const key = `${dimId}|${at.x}|${at.y}|${at.z}`;
  if (on) lights.set(key, { d: dimId, x: at.x, y: at.y, z: at.z });
  else lights.delete(key);
  try {
    world.setDynamicProperty("oddworks:lights", JSON.stringify([...lights.values()]));
  } catch {
    /* ignore */
  }
}

function clearLight(dim: Dimension, at?: Vector3): void {
  if (!at) return;
  try {
    const b = dim.getBlock(at);
    if (b && b.typeId === LIGHT) b.setType("minecraft:air");
  } catch {
    /* unloaded: cleaned on next startup */
  }
  rememberLight(dim.id, at, false);
}

/** Startup: remove light blocks left behind by a Sun Dog when the world closed. */
export function restoreLights(): void {
  try {
    const raw = world.getDynamicProperty("oddworks:lights");
    if (typeof raw !== "string") return;
    for (const l of JSON.parse(raw) as { d: string; x: number; y: number; z: number }[]) {
      try {
        const b = world.getDimension(l.d).getBlock(l);
        if (b && b.typeId === LIGHT) b.setType("minecraft:air");
      } catch {
        /* chunk unloaded: try again next start */
        lights.set(`${l.d}|${l.x}|${l.y}|${l.z}`, l);
      }
    }
    world.setDynamicProperty("oddworks:lights", JSON.stringify([...lights.values()]));
  } catch {
    /* ignore */
  }
}

export function sunDogStatus(s: PlayerState): string {
  if (s.sunDog) return `§6Sun Dog ${Math.ceil((s.sunDog.until - now()) / 20)}s`;
  return ready(s, "sundog") ? "§6Sun Dog ready" : `§8Sun Dog ${secs(remaining(s, "sundog"))}`;
}
