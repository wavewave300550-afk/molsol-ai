import {
  Block, Dimension, Direction, Entity, EntityComponentTypes, EntityDamageCause, EquipmentSlot, ItemComponentTypes, ItemStack, Player,
  ProjectileHitBlockAfterEvent, ProjectileHitEntityAfterEvent, Vector3, WeatherType, world,
} from "@minecraft/server";
import { ID, LINE } from "../config.js";
import { pose } from "../core/anim.js";
import { weatherIn } from "../core/env.js";
import { fx, Rgba, segment, shake, sound, soundTo } from "../core/fx.js";
import { container, enchantLevel, heldItem, swapHeld, wear } from "../core/items.js";
import { freshLine, hint, now, PlayerState, ready, remaining, startCd, stateOf } from "../core/state.js";
import { alive, canHurt, centerOf, isBoat, isVehicle, pvpOn, vehicleOf, weightOf } from "../core/targets.js";
import { add, clamp, dist, dot, len, lerp, norm, rand, rightOf, scale, sub, v } from "../core/vec.js";
import { scriptDamage } from "../systems/damage.js";
import { secs } from "./goggles.js";

const SLIPPERY = new Set(["minecraft:ice", "minecraft:packed_ice", "minecraft:blue_ice", "minecraft:frosted_ice", "minecraft:glass",
  "minecraft:tinted_glass", "minecraft:glass_pane", "minecraft:barrier"]);
const HOT = new Set(["minecraft:lava", "minecraft:flowing_lava", "minecraft:fire", "minecraft:soul_fire", "minecraft:magma"]);
const WATER = new Set(["minecraft:water", "minecraft:flowing_water"]);
const DISARM_CANDIDATES = ["bow", "crossbow", "trident", "iron_sword", "golden_sword", "stone_sword", "wooden_sword", "diamond_sword",
  "netherite_sword", "iron_axe", "golden_axe", "stone_axe", "diamond_axe", "iron_shovel", "wooden_spear", "stone_spear", "copper_spear",
  "iron_spear", "golden_spear", "diamond_spear", "netherite_spear"].map((x) => `minecraft:${x}`);

const ents = new Map<string, Entity>();
const keep = (e: Entity): Entity => {
  ents.set(e.id, e);
  return e;
};
const get = (id?: string): Entity | undefined => {
  if (!id) return undefined;
  const e = ents.get(id);
  if (e && alive(e)) return e;
  ents.delete(id);
  return undefined;
};

export function handPos(p: Player): Vector3 {
  const eye = p.getHeadLocation();
  const dir = p.getViewDirection();
  return add(add(add(eye, scale(dir, 0.45)), scale(rightOf(dir), 0.38)), v(0, -0.38, 0));
}

const body = (p: Player): Vector3 => add(p.location, v(0, 1.0, 0));

function normalOf(face: Direction): Vector3 {
  switch (face) {
    case Direction.Up: return v(0, 1, 0);
    case Direction.Down: return v(0, -1, 0);
    case Direction.North: return v(0, 0, -1);
    case Direction.South: return v(0, 0, 1);
    case Direction.East: return v(1, 0, 0);
    default: return v(-1, 0, 0);
  }
}

function addVelocity(p: Player, dv: Vector3): void {
  try {
    const vel = add(p.getVelocity(), dv);
    p.applyKnockback({ x: vel.x, z: vel.z }, vel.y);
  } catch {
    /* ignore */
  }
}

function setVelocity(p: Player, vel: Vector3): void {
  try {
    p.applyKnockback({ x: vel.x, z: vel.z }, vel.y);
  } catch {
    /* ignore */
  }
}

function push(e: Entity, dv: Vector3): void {
  try {
    if (e instanceof Player) addVelocity(e, dv);
    else e.applyImpulse(dv);
  } catch {
    /* some entities cannot be pushed */
  }
}

// ------------------------------------------------------------------ line rendering

function strainColor(strain: number): Rgba {
  const k = clamp(strain, 0, 1);
  if (k < 0.5) return { r: 0.93, g: 0.92 - k * 0.2, b: 0.86 - k * 0.9, a: 0.95 };
  return { r: 1, g: 0.82 - (k - 0.5) * 1.3, b: 0.4 - (k - 0.5) * 0.6, a: 0.95 };
}

function drawLine(dim: Dimension, pts: Vector3[], slack: number, strain: number, glow: boolean): void {
  const color = strainColor(strain);
  for (let i = 0; i + 1 < pts.length; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    const straight = dist(a, b);
    const last = i + 2 === pts.length;
    const sag = last ? clamp(slack * 0.35, 0, 3) : 0.04;
    const n = clamp(Math.ceil(straight / 1.6), 2, 10);
    let prev = a;
    for (let k = 1; k <= n; k++) {
      const t = k / n;
      const q = sub(lerp(a, b, t), v(0, sag * 4 * t * (1 - t), 0));
      segment(dim, "oddworks:line_segment", prev, q, { color, size: 1 });
      prev = q;
    }
    if (glow && sag < 0.3) segment(dim, "oddworks:line_glow", a, b, { size: 1 });
  }
}

// ------------------------------------------------------------------ use events

export function startUse(p: Player, s: PlayerState, item: string): void {
  const line = s.line;
  if (item === ID.handline) {
    if (!ready(s, "line")) return void hint(s, `§7Re-tying the hook: ${secs(remaining(s, "line"))}`);
    line.phase = "whirl";
    line.whirlStart = now();
    line.revsDone = 0;
    line.whirlHit.clear();
    line.slot = p.selectedSlotIndex;
    return;
  }
  // line is out
  if (p.isSneaking) return snap(p, s);
  line.reeling = true;
  if (line.phase === "bobber" && line.biteUntil >= now()) {
    const bob = get(line.bobberId);
    if (bob) return landCatch(p, s, bob);
  }
  if (line.phase === "anchored" && !line.yanked) yankBlock(p, s);
}

export function release(p: Player, s: PlayerState, item: string): void {
  if (item === ID.handline && s.line.phase === "whirl") return cast(p, s);
  s.line.reeling = false;
}

export function stopUse(p: Player, s: PlayerState): void {
  s.line.reeling = false;
  if (s.line.phase === "whirl") s.line.phase = "idle";
}

// ------------------------------------------------------------------ skill 1: Overhead Cast

function revTicks(p: Player): number {
  return p.isInWater ? LINE.revTicks / 0.4 : LINE.revTicks;
}

function tickWhirl(p: Player, s: PlayerState): void {
  const line = s.line;
  const t = now();
  const rt = revTicks(p);
  const el = t - line.whirlStart;
  const revs = Math.min(LINE.maxRevs, el / rt);
  if (Math.floor(revs) > line.revsDone && line.revsDone < LINE.maxRevs) {
    line.revsDone = Math.floor(revs);
    sound(p.dimension, "oddworks.line.whirl", p.getHeadLocation(), 0.85 + 0.12 * line.revsDone, 0.8);
  }
  const reach = Math.round(16 * Math.max(0.5, revs));
  hint(s, `§bWhirling ${"§b|".repeat(line.revsDone)}${"§8|".repeat(LINE.maxRevs - line.revsDone)} §7reach ~${reach} blocks`, 4);
  // the weighted line orbiting overhead
  const hub = add(p.getHeadLocation(), v(0, 0.9, 0));
  const a = (el / rt) * Math.PI * 2;
  const R = 1.25;
  const sinker = add(hub, v(Math.cos(a) * R, 0, Math.sin(a) * R));
  fx(p.dimension, "oddworks:whirl_trail", sinker);
  segment(p.dimension, "oddworks:line_segment", hub, sinker, { color: strainColor(0), size: 1 });
  // anything that steps into the circle gets clipped by the lead sinker
  try {
    for (const e of p.dimension.getEntities({ location: sinker, maxDistance: 1.1 })) {
      if (!canHurt(p, e, true)) continue;
      if (line.whirlHit.get(e.id) === line.revsDone) continue;
      line.whirlHit.set(e.id, line.revsDone);
      scriptDamage(e, LINE.whirlDamage, EntityDamageCause.entityAttack, p);
      push(e, add(scale(norm(sub(centerOf(e), hub)), 0.45), v(0, 0.2, 0)));
      sound(p.dimension, "oddworks.line.hook_flesh", sinker, 1.3, 0.6);
    }
  } catch {
    /* ignore */
  }
}

function cast(p: Player, s: PlayerState): void {
  const line = s.line;
  const revs = Math.min(LINE.maxRevs, (now() - line.whirlStart) / revTicks(p));
  let speed = revs < 0.25 ? 0.7 : LINE.speedBase + LINE.speedPerRev * revs;
  if (p.isInWater) speed *= 0.4;
  const dir = p.getViewDirection();
  // launched close to the line of sight so it flies where the crosshair points
  const start = add(add(add(p.getHeadLocation(), scale(dir, 0.8)), scale(rightOf(dir), 0.12)), v(0, -0.12, 0));
  let hook: Entity;
  try {
    hook = keep(p.dimension.spawnEntity(ID.hook, start));
  } catch {
    line.phase = "idle";
    return void hint(s, "§7No room to cast here");
  }
  try {
    const proj = hook.getComponent(EntityComponentTypes.Projectile);
    if (proj) {
      proj.owner = p;
      proj.shoot(scale(dir, speed), { uncertainty: 0 });
    } else hook.applyImpulse(scale(dir, speed));
  } catch {
    hook.applyImpulse(scale(dir, speed));
  }
  const slot = p.selectedSlotIndex;
  Object.assign(line, freshLine(), {
    phase: "flight", hookId: hook.id, castTick: now(), length: dist(handPos(p), start) + 1, slot,
  });
  swapHeld(p, ID.handline, ID.handlineCast, slot);
  sound(p.dimension, "oddworks.line.cast", p.getHeadLocation(), 0.9 + revs * 0.05);
  pose(p, "cast_throw");
  wear(p, LINE.wearCast, slot);
}

// ------------------------------------------------------------------ projectile landings

export function onHookHitBlock(ev: ProjectileHitBlockAfterEvent): void {
  if (ev.projectile.typeId !== ID.hook || !(ev.source instanceof Player)) return;
  const p = ev.source;
  const s = stateOf(p);
  const line = s.line;
  if (line.hookId !== ev.projectile.id || line.phase !== "flight") return;
  const hit = ev.getBlockHit();
  const block = hit.block;
  const n = normalOf(hit.face);
  const point = add(add(block.location, hit.faceLocation), scale(n, 0.05));
  const id = block.typeId;
  if (SLIPPERY.has(id)) {
    fx(ev.dimension, "oddworks:hook_spark", point, { count: 6, color: { r: 0.8, g: 0.95, b: 1, a: 1 } });
    sound(ev.dimension, "oddworks.line.hook_block", point, 1.8, 0.7);
    hint(s, "§7The hook skitters off - it can't bite into ice or glass");
    return retract(p, s, true);
  }
  if (id === "minecraft:slime") {
    // bounces back out with most of its speed
    const vel = line.lastHookVel ?? scale(ev.hitVector, 1);
    const refl = scale(sub(vel, scale(n, 2 * dot(vel, n))), 0.8);
    try {
      ev.projectile.remove();
      const hook = keep(ev.dimension.spawnEntity(ID.hook, add(point, scale(n, 0.35))));
      const proj = hook.getComponent(EntityComponentTypes.Projectile);
      if (proj) {
        proj.owner = p;
        proj.shoot(refl, { uncertainty: 0 });
      } else hook.applyImpulse(refl);
      line.hookId = hook.id;
      sound(ev.dimension, "mob.slime.big", point, 1.2);
    } catch {
      retract(p, s, true);
    }
    return;
  }
  if (HOT.has(id)) return burnLine(p, s, point);
  line.phase = "anchored";
  line.anchor = point;
  line.anchorBlock = block.location;
  line.anchorType = id;
  line.sticky = id === "minecraft:honey_block";
  line.bends = [];
  line.length = dist(body(p), point) + 0.3;
  const woody = id.includes("log") || id.includes("planks") || id.includes("wood") || id.includes("leaves");
  fx(ev.dimension, "oddworks:hook_spark", point, { count: woody ? 4 : 7, color: woody ? { r: 0.6, g: 0.42, b: 0.25, a: 1 } : { r: 1, g: 0.75, b: 0.35, a: 1 } });
  hint(s, line.sticky ? "§6Stuck in honey - it won't come loose easily" : "§aHooked fast §7- hold Use to haul yourself in", 50);
}

export function onHookHitEntity(ev: ProjectileHitEntityAfterEvent): void {
  if (ev.projectile.typeId !== ID.hook || !(ev.source instanceof Player)) return;
  const p = ev.source;
  const s = stateOf(p);
  const line = s.line;
  if (line.hookId !== ev.projectile.id || line.phase !== "flight") return;
  const target = ev.getEntityHit().entity;
  if (!target || target.id === p.id) return;
  if (target instanceof Player && !pvpOn()) {
    hint(s, "§7The hook glances off (PvP is off)");
    return retract(p, s, true);
  }
  try {
    ev.projectile.remove();
  } catch {
    /* already destroyed on hit */
  }
  keep(target);
  line.phase = "hooked";
  line.targetId = target.id;
  line.hookId = undefined;
  line.length = dist(body(p), centerOf(target)) + 0.3;
  if (!isVehicle(target) && canHurt(p, target, false)) {
    scriptDamage(target, LINE.hookDamage, EntityDamageCause.entityAttack, p);
  }
  const w = weightOf(target);
  const who = target.typeId.replace("minecraft:", "").replace(/_/g, " ");
  hint(s, `§aHooked ${who} §7(weight ${w.toFixed(1)}) - hold Use to haul`, 60);
}

// ------------------------------------------------------------------ per tick while the line exists

export function tickLine(p: Player, s: PlayerState, holdingCast: boolean, using: boolean): void {
  const line = s.line;
  if (line.phase === "whirl") {
    if (using) tickWhirl(p, s);
    else line.phase = "idle";
    return;
  }
  if (line.phase === "idle") return;
  if (!holdingCast) return retract(p, s, false); // switched away: the line is wound back in
  if (line.strain >= LINE.strainBreak) return breakLine(p, s);
  const hand = handPos(p);
  const t = now();
  switch (line.phase) {
    case "flight": {
      const hook = get(line.hookId);
      if (!hook) {
        if (t - line.castTick > 3) retract(p, s, true);
        return;
      }
      const hp = hook.location;
      try {
        line.lastHookVel = hook.getVelocity();
      } catch {
        /* ignore */
      }
      line.length = Math.max(line.length, dist(hand, hp) + 0.5);
      if (line.length > LINE.maxLength) {
        line.length = LINE.maxLength;
        try {
          hook.clearVelocity();
          hook.applyImpulse(scale(norm(sub(hand, hp)), 0.15));
        } catch {
          /* ignore */
        }
        hint(s, "§7The spool runs out at 96 blocks");
      }
      const b = blockAt(p.dimension, hp);
      if (b && WATER.has(b.typeId)) return toBobber(p, s, hook, b);
      if (b && HOT.has(b.typeId)) return burnLine(p, s, hp);
      for (const it of p.dimension.getEntities({ location: hp, maxDistance: 1.0 })) {
        if (it.typeId === "minecraft:item" || it.typeId === "minecraft:xp_orb") {
          keep(it);
          try {
            hook.remove();
          } catch {
            /* ignore */
          }
          line.phase = "snagged";
          line.targetId = it.id;
          line.hookId = undefined;
          hint(s, "§7Snagged something - reeling it in");
          return;
        }
      }
      drawLine(p.dimension, [hand, hp], 0.3, 0, false);
      return;
    }
    case "anchored":
      return tickAnchored(p, s, hand);
    case "hooked":
      return tickHooked(p, s, hand);
    case "snagged":
      return tickSnagged(p, s, hand);
    case "bobber":
      return tickBobber(p, s, hand);
  }
}

function blockAt(dim: Dimension, at: Vector3): Block | undefined {
  try {
    return dim.getBlock(at);
  } catch {
    return undefined;
  }
}

/** Fire, lava or magma touching the line burns straight through it. */
function lineBurns(dim: Dimension, pts: Vector3[]): Vector3 | undefined {
  for (let i = 0; i + 1 < pts.length; i++) {
    const d = dist(pts[i], pts[i + 1]);
    for (let k = 1; k < d; k += 2) {
      const q = lerp(pts[i], pts[i + 1], k / d);
      const b = blockAt(dim, q);
      if (b && HOT.has(b.typeId)) return q;
    }
  }
  return undefined;
}

function rayBlocked(dim: Dimension, a: Vector3, b: Vector3): { point: Vector3; n: Vector3 } | undefined {
  const d = dist(a, b);
  if (d < 0.6) return undefined;
  const dir = norm(sub(b, a));
  try {
    const hit = dim.getBlockFromRay(add(a, scale(dir, 0.3)), dir, { maxDistance: d - 0.6, includePassableBlocks: false, includeLiquidBlocks: false });
    if (!hit) return undefined;
    return { point: add(hit.block.location, hit.faceLocation), n: normalOf(hit.face) };
  } catch {
    return undefined;
  }
}

function tickAnchored(p: Player, s: PlayerState, hand: Vector3): void {
  const line = s.line;
  const anchor = line.anchor;
  if (!anchor) return retract(p, s, true);
  const dim = p.dimension;
  const b = body(p);
  // the line wraps around corners it is pulled across, and unwraps when the way is clear again
  if (line.bends.length) {
    const prev = line.bends.length > 1 ? line.bends[line.bends.length - 2] : anchor;
    if (!rayBlocked(dim, prev, b)) line.bends.pop();
  }
  const pivot0 = line.bends.length ? line.bends[line.bends.length - 1] : anchor;
  const blocked = rayBlocked(dim, pivot0, b);
  if (blocked) {
    if (line.bends.length >= 6) {
      hint(s, "§cThe line tangled around too many corners");
      return breakLine(p, s);
    }
    line.bends.push(add(blocked.point, scale(blocked.n, 0.3)));
  }
  const pts = [anchor, ...line.bends];
  let fixed = 0;
  for (let i = 0; i + 1 < pts.length; i++) fixed += dist(pts[i], pts[i + 1]);
  const pivot = pts[pts.length - 1];
  const vehicle = vehicleOf(p);
  if (line.reeling) line.length = Math.max(fixed + 0.8, line.length - LINE.reelSpeed * (line.strain > 0.6 ? 0.6 : 1));
  else if (p.isSneaking && !vehicle) line.length = Math.min(LINE.maxLength, line.length + LINE.payOutSpeed);
  const allowed = Math.max(0.5, line.length - fixed);
  const r = sub(b, pivot);
  const d = len(r);
  if (d > allowed) {
    const rhat = scale(r, 1 / d);
    if (vehicle && isBoat(vehicle) && alive(vehicle)) {
      // kedging: the hooked shore hauls your boat across the water
      push(vehicle, scale(rhat, -Math.min(0.22, (d - allowed) * 0.25)));
    } else {
      let vel = p.getVelocity();
      const vr = dot(vel, rhat);
      if (vr > 0) vel = sub(vel, scale(rhat, vr));
      vel = sub(vel, scale(rhat, Math.min(0.7, (d - allowed) * 0.45)));
      setVelocity(p, vel);
    }
    line.strain = Math.min(1.2, line.strain + (d - allowed) * 0.02 + (line.reeling ? 0.002 : 0));
    s.cd.set("tether", now() + 10);
  } else line.strain = Math.max(0, line.strain - 0.03);
  if (line.reeling && line.bends.length === 0 && dist(b, anchor) < 1.7) {
    // hauled all the way up: hop over the lip and the hook pops free
    setVelocity(p, v(0, 0.55, 0));
    sound(dim, "oddworks.line.reel", hand, 1.4);
    return retract(p, s, false);
  }
  const burn = lineBurns(dim, [hand, ...pts.slice().reverse()]);
  if (burn) return burnLine(p, s, burn);
  if (line.reeling && now() % 6 === 0) sound(dim, "oddworks.line.reel", hand, 0.9 + Math.random() * 0.2);
  if (line.strain > 0.7 && now() % 10 === 0) sound(dim, "oddworks.line.taut", hand, 0.8 + line.strain * 0.4);
  drawLine(dim, [hand, ...pts.slice().reverse()], Math.max(0, line.length - fixed - d), line.strain, now() % 2 === 0);
}

function tickHooked(p: Player, s: PlayerState, hand: Vector3): void {
  const line = s.line;
  const target = get(line.targetId);
  if (!target) {
    hint(s, "§7The line went slack");
    return retract(p, s, true);
  }
  const dim = p.dimension;
  if (target.dimension.id !== dim.id) return retract(p, s, true);
  const tc = centerOf(target);
  const b = body(p);
  const d = dist(b, tc);
  if (line.reeling) line.length = Math.max(1.2, line.length - LINE.reelSpeed * 0.8);
  else if (p.isSneaking) line.length = Math.min(LINE.maxLength, line.length + LINE.payOutSpeed);
  const excess = d - line.length;
  const W = weightOf(target);
  const vehicle = vehicleOf(p);
  let S = 2.5;
  const inBoat = !!vehicle && isBoat(vehicle) && alive(vehicle);
  if (inBoat && vehicle) S = 3 + weightOf(vehicle) * 0.5;
  else {
    if (p.isSneaking && p.isOnGround) S *= 1.6;
    if (!p.isOnGround) S *= 0.5;
  }
  if (excess > 0) {
    const share = W >= 50 ? 1 : W / (W + S); // part of the correction taken by the angler
    const toP = norm(sub(b, tc));
    const pullT = Math.min(0.55, excess * (1 - share) * 0.4);
    const pullP = Math.min(0.55, excess * share * 0.4);
    if (pullT > 0.01) push(target, add(scale(toP, pullT), v(0, isBoat(target) ? 0 : 0.06, 0)));
    if (pullP > 0.01) {
      if (inBoat && vehicle) push(vehicle, scale(toP, -pullP));
      else addVelocity(p, scale(toP, -pullP));
    }
    line.strain = Math.min(1.2, line.strain + excess * (W > S ? 0.035 : 0.015) + (line.reeling ? 0.003 : 0));
    if (share > 0.5) s.cd.set("tether", now() + 10);
  } else line.strain = Math.max(0, line.strain - 0.02);
  if (line.reeling && d < 2.2) {
    sound(dim, "oddworks.line.reel", hand, 1.3);
    return retract(p, s, false);
  }
  const burn = lineBurns(dim, [hand, tc]);
  if (burn) return burnLine(p, s, burn);
  if (line.reeling && now() % 6 === 0) sound(dim, "oddworks.line.reel", hand, 0.9 + Math.random() * 0.2);
  if (line.strain > 0.7 && now() % 10 === 0) sound(dim, "oddworks.line.taut", hand, 0.8 + line.strain * 0.4);
  drawLine(dim, [hand, tc], Math.max(0, line.length - d), line.strain, now() % 2 === 0);
}

function tickSnagged(p: Player, s: PlayerState, hand: Vector3): void {
  const it = get(s.line.targetId);
  if (!it) return retract(p, s, false);
  const d = dist(it.location, hand);
  if (d < 1.4) return retract(p, s, false);
  try {
    it.teleport(add(it.location, scale(norm(sub(hand, it.location)), Math.min(d, 0.7))));
  } catch {
    return retract(p, s, false);
  }
  drawLine(p.dimension, [hand, it.location], 0.2, 0, false);
}

// ------------------------------------------------------------------ fishing

function biteDelay(p: Player, s: PlayerState, at: Vector3): number {
  const lure = enchantLevel(heldItem(p), "lure");
  let d = rand(70, 220) * (1 - 0.15 * lure);
  if (weatherIn(p.dimension.id) !== WeatherType.Clear) d *= 0.8;
  try {
    if (p.dimension.getSkyLightLevel(add(at, v(0, 1, 0))) < 10) d *= 1.6;
  } catch {
    /* ignore */
  }
  if (s.line.deep) d *= 0.85;
  return now() + Math.round(d);
}

function toBobber(p: Player, s: PlayerState, hook: Entity, water: Block): void {
  const line = s.line;
  let top = water;
  for (let i = 0; i < 24; i++) {
    const up = top.above();
    if (!up || !WATER.has(up.typeId)) break;
    top = up;
  }
  const pos = v(hook.location.x, top.location.y + 0.85, hook.location.z);
  try {
    hook.remove();
  } catch {
    /* ignore */
  }
  let bob: Entity;
  try {
    bob = keep(p.dimension.spawnEntity(ID.bobber, pos));
  } catch {
    return retract(p, s, true);
  }
  let depth = 0;
  for (let i = 0; i < 12; i++) {
    const b = blockAt(p.dimension, v(pos.x, top.location.y - i, pos.z));
    if (!b || !WATER.has(b.typeId)) break;
    depth++;
  }
  line.phase = "bobber";
  line.hookId = undefined;
  line.bobberId = bob.id;
  line.deep = depth >= 5 || dist(p.location, pos) >= 24;
  line.nextBite = biteDelay(p, s, pos);
  line.biteUntil = 0;
  sound(p.dimension, "random.splash", pos, 1.1, 0.8);
  fx(p.dimension, "oddworks:bobber_ripple", pos, { size: 1.2 });
  fx(p.dimension, "oddworks:water_spray", pos, { count: 8 });
  hint(s, line.deep ? "§bThe float settles over deep water §e(better catches)" : "§bThe float settles - wait for a bite", 50);
}

function tickBobber(p: Player, s: PlayerState, hand: Vector3): void {
  const line = s.line;
  const bob = get(line.bobberId);
  if (!bob) return retract(p, s, true);
  const t = now();
  const bp = bob.location;
  const d = dist(hand, bp);
  if (line.biteUntil === 0 && t >= line.nextBite) {
    line.biteUntil = t + LINE.biteWindow;
    push(bob, v(0, -0.35, 0));
    fx(p.dimension, "oddworks:water_spray", bp, { count: 12 });
    fx(p.dimension, "oddworks:bobber_ripple", bp, { size: 1.6 });
    sound(p.dimension, "oddworks.line.bite", bp);
    soundTo(p, "oddworks.line.bite", 1.2, 0.6);
    hint(s, "§b§lBITE! §r§bHold Use to reel it in!", LINE.biteWindow);
  } else if (line.biteUntil > 0 && t > line.biteUntil) {
    line.biteUntil = 0;
    line.nextBite = biteDelay(p, s, bp);
    hint(s, "§7...it got away");
  }
  if (t % 40 === 0) fx(p.dimension, "oddworks:bobber_ripple", bp, { size: 0.8 });
  if (line.reeling) {
    push(bob, scale(norm(sub(hand, bp)), 0.18));
    if (d < 2.5) return retract(p, s, false);
  }
  drawLine(p.dimension, [hand, add(bp, v(0, 0.35, 0))], Math.max(0.2, line.length - d), 0, false);
  if (line.length < d) line.length = d;
}

function landCatch(p: Player, s: PlayerState, bob: Entity): void {
  const dim = p.dimension;
  const at = bob.location;
  const item = heldItem(p);
  let loot: ItemStack[] = [];
  try {
    const mgr = world.getLootTableManager();
    const table = mgr.getLootTable(s.line.deep ? "oddworks/handline_deep" : "gameplay/fishing");
    if (table) {
      loot = mgr.generateLootFromTable(table, item) ?? [];
      const luck = enchantLevel(item, "luck_of_the_sea");
      if (Math.random() < 0.12 * luck) loot = loot.concat(mgr.generateLootFromTable(table, item) ?? []);
    }
  } catch {
    /* loot table unavailable */
  }
  if (loot.length === 0) loot = [new ItemStack("minecraft:cod", 1)];
  const names: string[] = [];
  for (const st of loot) {
    try {
      const e = dim.spawnItem(st, add(at, v(0, 0.4, 0)));
      const to = sub(add(p.location, v(0, 1.2, 0)), at);
      e.applyImpulse(add(scale(to, 0.1), v(0, 0.3 + len(to) * 0.03, 0)));
      names.push(st.typeId.replace("minecraft:", "").replace(/_/g, " "));
    } catch {
      /* ignore */
    }
  }
  try {
    dim.spawnXp(p.location, 1 + Math.floor(Math.random() * 5));
  } catch {
    /* ignore */
  }
  fx(dim, "oddworks:water_spray", at, { count: 16 });
  sound(dim, "random.splash", at, 1.0);
  hint(s, `§bCaught: §f${names.join(", ")}`, 60);
  wear(p, 1, s.line.slot);
  retract(p, s, false);
}

// ------------------------------------------------------------------ skill 3: Snap

function snap(p: Player, s: PlayerState): void {
  const line = s.line;
  if (!ready(s, "snap")) return void hint(s, `§cSnap§7 ready in ${secs(remaining(s, "snap"))}`);
  const hand = handPos(p);
  pose(p, "snap");
  if (line.phase === "hooked") {
    const target = get(line.targetId);
    if (!target) return retract(p, s, true);
    const tc = centerOf(target);
    const W = weightOf(target);
    snapWave(p.dimension, hand, tc);
    sound(p.dimension, "oddworks.line.snap", tc, 1.0, 1.0);
    sound(p.dimension, "oddworks.line.snap", hand, 1.3, 0.5);
    shake(p, 0.1, 0.2);
    if (!isVehicle(target) && canHurt(p, target, false)) {
      scriptDamage(target, 4 + Math.min(4, line.length / 12), EntityDamageCause.entityAttack, p);
    }
    const toP = norm(sub(add(p.location, v(0, 1, 0)), tc));
    if (W < 12) push(target, add(scale(toP, isBoat(target) ? 0.9 : 1.1 / Math.max(1, W * 0.5)), v(0, isBoat(target) ? 0.05 : 0.45, 0)));
    else try {
      target.addEffect("slowness", 30, { amplifier: 3, showParticles: false });
    } catch {
      /* ignore */
    }
    const dis = isVehicle(target) || target instanceof Player ? undefined : disarm(target, p);
    hint(s, dis ? `§cSnap! §7${dis}` : "§cSnap!", 50);
    startCd(s, "snap", LINE.snapCooldown);
    wear(p, LINE.wearSnap, line.slot);
    return retract(p, s, false);
  }
  if (line.phase === "anchored" && line.anchor) {
    if (line.sticky) return void hint(s, "§6The honey holds the hook fast - reel in instead");
    const pivot = line.bends.length ? line.bends[line.bends.length - 1] : line.anchor;
    const dir = norm(sub(pivot, body(p)));
    const taut = clamp(1 - (line.length - dist(body(p), pivot)) / 4, 0.3, 1);
    snapWave(p.dimension, hand, pivot);
    sound(p.dimension, "oddworks.line.snap", hand, 0.8, 0.9);
    setVelocity(p, v(dir.x * 1.6 * taut, Math.max(0.45, dir.y * 1.6 * taut + 0.25), dir.z * 1.6 * taut));
    startCd(s, "snap", LINE.slingCooldown);
    hint(s, "§cSlingshot!", 30);
    return retract(p, s, false);
  }
  sound(p.dimension, "oddworks.line.reel", hand, 1.5);
  retract(p, s, false);
}

function snapWave(dim: Dimension, a: Vector3, b: Vector3): void {
  const n = 6;
  for (let i = 0; i <= n; i++) {
    fx(dim, "oddworks:snap_pulse", lerp(a, b, i / n), { color: { r: 0.85, g: 1, b: 0.95, a: 1 } });
  }
  segment(dim, "oddworks:line_glow", a, b, { size: 2 });
}

/** Knock the weapon out of a mob's hand: half the time it falls (badly worn), otherwise it breaks. */
function disarm(target: Entity, p: Player): string | undefined {
  let held: ItemStack | undefined;
  try {
    const eq = target.getComponent(EntityComponentTypes.Equippable);
    if (eq) {
      held = eq.getEquipment(EquipmentSlot.Mainhand);
      if (held) eq.setEquipment(EquipmentSlot.Mainhand, undefined);
    } else {
      for (const id of DISARM_CANDIDATES) {
        if (target.runCommand(`testfor @s[hasitem={item=${id},location=slot.weapon.mainhand}]`).successCount > 0) {
          held = new ItemStack(id, 1);
          target.runCommand("replaceitem entity @s slot.weapon.mainhand 0 air");
          break;
        }
      }
    }
  } catch {
    return undefined;
  }
  if (!held) return undefined;
  const name = held.typeId.replace("minecraft:", "").replace(/_/g, " ");
  const keepChance = held.typeId === "minecraft:trident" ? 0.25 : 0.5;
  const c = centerOf(target);
  if (Math.random() < keepChance) {
    try {
      const dur = held.getComponent(ItemComponentTypes.Durability);
      if (dur) dur.damage = Math.floor(dur.maxDurability * rand(0.55, 0.85));
      const drop = target.dimension.spawnItem(held, c);
      drop.applyImpulse(add(scale(norm(sub(p.location, c)), 0.35), v(0, 0.3, 0)));
    } catch {
      /* ignore */
    }
    return `${name} yanked loose`;
  }
  fx(target.dimension, "oddworks:clang_spark", c, { count: 10 });
  sound(target.dimension, "random.break", c, 1.0);
  return `${name} snapped`;
}

/** First haul on a lever / door / trapdoor / gate / bell yanks it. */
function yankBlock(p: Player, s: PlayerState): void {
  const line = s.line;
  line.yanked = true;
  if (!line.anchorBlock || !line.anchorType) return;
  const b = blockAt(p.dimension, line.anchorBlock);
  if (!b) return;
  const id = b.typeId;
  try {
    if (id === "minecraft:bell") {
      sound(p.dimension, "block.bell.hit", b.center(), 1.0, 1.0);
      return;
    }
    const toggles = id === "minecraft:lever" || id.endsWith("_door") || id.endsWith("trapdoor") || id.endsWith("fence_gate");
    if (!toggles || id.includes("iron")) return;
    let target = b;
    if (id.endsWith("_door") && b.permutation.getState("upper_block_bit") === true) target = b.below() ?? b;
    const open = target.permutation.getState("open_bit");
    if (typeof open !== "boolean") return;
    target.setPermutation(target.permutation.withState("open_bit", !open));
    sound(p.dimension, id === "minecraft:lever" ? "random.click" : "random.door_open", b.center());
    hint(s, `§aYanked the ${id.replace("minecraft:", "").replace(/_/g, " ")}`, 40);
    retract(p, s, false);
  } catch {
    /* ignore */
  }
}

// ------------------------------------------------------------------ endings

function burnLine(p: Player, s: PlayerState, at: Vector3): void {
  fx(p.dimension, "oddworks:line_burn", at);
  sound(p.dimension, "random.fizz", at, 1.2);
  sound(p.dimension, "oddworks.line.break", handPos(p), 1.2, 0.7);
  hint(s, "§cThe line burned through!", 50);
  startCd(s, "line", LINE.breakCooldown);
  wear(p, LINE.wearBreak, s.line.slot);
  retract(p, s, true);
}

function breakLine(p: Player, s: PlayerState): void {
  const hand = handPos(p);
  sound(p.dimension, "oddworks.line.break", hand);
  fx(p.dimension, "oddworks:snap_pulse", hand, { color: { r: 1, g: 0.3, b: 0.2, a: 1 } });
  shake(p, 0.12, 0.25);
  if (!s.hint || s.hint.until < now()) hint(s, "§cThe line snapped under the strain!", 50);
  startCd(s, "line", LINE.breakCooldown);
  wear(p, LINE.wearBreak, s.line.slot);
  retract(p, s, true);
}

/** Wind the line back: remove hook/float entities and turn the reel back into the ready item. */
export function retract(p: Player | undefined, s: PlayerState, lost: boolean): void {
  const line = s.line;
  for (const id of [line.hookId, line.bobberId]) {
    const e = get(id);
    try {
      e?.remove();
    } catch {
      /* ignore */
    }
  }
  const slot = line.slot;
  Object.assign(line, freshLine());
  if (!p) return;
  const inv = container(p);
  if (inv) {
    let idx = slot >= 0 && inv.getItem(slot)?.typeId === ID.handlineCast ? slot : -1;
    if (idx < 0) for (let i = 0; i < 9; i++) if (inv.getItem(i)?.typeId === ID.handlineCast) idx = i;
    if (idx >= 0) swapHeld(p, ID.handlineCast, ID.handline, idx);
  }
  if (!lost) sound(p.dimension, "oddworks.line.reel", handPos(p), 1.5, 0.6);
  if (ready(s, "line")) startCd(s, "line", 10);
}

export function tethered(p: Player): boolean {
  const s = stateOf(p);
  return (s.cd.get("tether") ?? 0) > now();
}

export function lineStatus(p: Player, s: PlayerState): string {
  const line = s.line;
  const bar = (k: number): string => {
    const n = Math.round(clamp(k, 0, 1) * 6);
    return `${k > 0.7 ? "§c" : k > 0.4 ? "§6" : "§a"}${"|".repeat(n)}§8${"|".repeat(6 - n)}`;
  };
  const snapCd = ready(s, "snap") ? "§cSnap ready" : `§8Snap ${secs(remaining(s, "snap"))}`;
  switch (line.phase) {
    case "flight":
      return `§7Line paying out §f${line.length.toFixed(0)}§7/${LINE.maxLength}`;
    case "anchored":
      return `§aAnchored §7line §f${line.length.toFixed(1)}§7/${LINE.maxLength} ${line.bends.length ? `§8(${line.bends.length} wrap) ` : ""}§7strain ${bar(line.strain)} §r${snapCd}`;
    case "hooked": {
      const t = get(line.targetId);
      return `§aHooked §f${t ? t.typeId.replace("minecraft:", "").replace(/_/g, " ") : "?"} §7strain ${bar(line.strain)} §r${snapCd}`;
    }
    case "bobber":
      return line.biteUntil >= now() ? "§b§lBITE! Reel in!" : `§bFloat out${line.deep ? " §e(deep water)" : ""} §7- waiting for a bite`;
    case "snagged":
      return "§7Reeling in a snag";
    default:
      return ready(s, "line") ? "§bHold Use to whirl, release to cast" : `§7Re-tying the hook ${secs(remaining(s, "line"))}`;
  }
}
