/**
 * Abilities 01-06 of THE MIGRATING MOUNTAIN. Each is a coroutine that adapts
 * to the phase: in Phase 1 the living strata of the dorsal surface, cavern and
 * underbelly react; in Phase 2 the unfolded petals, ribs and Lithic Heart do.
 *
 *   01 Continental Fold    02 Lithic Peristalsis   03 Geological Shedding
 *   04 Resonance Network   05 Inverted Strata      06 Mantle Contraction
 *   (07 The Great Unfolding lives in unfolding.ts)
 */
import { Entity, EntityDamageCause, Player } from "@minecraft/server";
import { knock } from "../../core/arena.js";
import { line, particle, quake, sound, title } from "../../core/fx.js";
import { Co } from "../../core/tasks.js";
import { angleDiffDeg, clamp, distXZ, V3 } from "../../core/vec.js";
import { ColFlag, MM } from "../../gen/mountain.js";
import * as P from "../../gen/palette.js";
import { MMContext } from "./context.js";
import { ENT, PROP, PX, SND } from "./ids.js";
import { foldField, patchField, updateWaveBounds, waveField } from "./terrain.js";

export const ABILITY_IDS = [
  "continental_fold",
  "lithic_peristalsis",
  "geological_shedding",
  "resonance_network",
  "inverted_strata",
  "mantle_contraction",
  "great_unfolding",
] as const;
export type AbilityId = (typeof ABILITY_IDS)[number];

export const ABILITY_NAMES: Record<AbilityId, string> = {
  continental_fold: "01 Continental Fold",
  lithic_peristalsis: "02 Lithic Peristalsis",
  geological_shedding: "03 Geological Shedding",
  resonance_network: "04 Resonance Network",
  inverted_strata: "05 Inverted Strata",
  mantle_contraction: "06 Mantle Contraction",
  great_unfolding: "07 The Great Unfolding",
};

const D = MM.disk;
const HX = MM.heart.x;
const HZ = MM.heart.z;
const RAD = Math.PI / 180;

function near(ctx: MMContext, at: V3, r: number): Player[] {
  return ctx.audience().filter((p) => Math.hypot(p.location.x - at.x, p.location.y - at.y, p.location.z - at.z) <= r);
}

function warn(players: Player[], name: string, hint: string): void {
  title(players, "", `§c⚠ ${name} §7— ${hint}`, 34, 4, 10);
}

function surface(ctx: MMContext, x: number, z: number): number {
  return ctx.phase === 2 ? D.y : ctx.terrain.topAt(Math.floor(x), Math.floor(z));
}

function diskRadius(p: V3): number {
  return Math.hypot(p.x - HX, p.z - HZ);
}

function diskAngle(p: V3): number {
  return Math.atan2(p.z - HZ, p.x - HX) / RAD;
}

// ============================================================================ 01 CONTINENTAL FOLD
export function* continentalFold(ctx: MMContext, target: Player): Co {
  if (ctx.phase === 2) {
    yield* petalFold(ctx, target);
    return;
  }
  const t = ctx.terrain;
  const p = target.location;
  // a fault line across the slope, passing close to (not exactly under) the target
  const radial = Math.atan2(p.z, p.x);
  const along = radial + Math.PI / 2 + (ctx.rng() - 0.5) * 0.8;
  const off = 1.5 + ctx.rng() * 2;
  const cx = p.x + Math.cos(radial) * off * (ctx.rng() < 0.5 ? -1 : 1);
  const cz = p.z + Math.sin(radial) * off * (ctx.rng() < 0.5 ? -1 : 1);
  const half = 13 + ctx.rng() * 5;
  const a = { x: cx - Math.cos(along) * half, z: cz - Math.sin(along) * half };
  const b = { x: cx + Math.cos(along) * half, z: cz + Math.sin(along) * half };
  const pts: V3[] = [];
  for (let s = 0; s <= half * 2; s += 1.5) {
    const k = s / (half * 2);
    const x = a.x + (b.x - a.x) * k;
    const z = a.z + (b.z - a.z) * k;
    if (t.isDeformable(Math.floor(x), Math.floor(z))) pts.push({ x, y: t.topAt(Math.floor(x), Math.floor(z)) + 1, z });
  }
  if (pts.length < 6) return;
  const mid = { x: cx, y: surface(ctx, cx, cz) + 1, z: cz };
  warn(near(ctx, mid, 26), "Continental Fold", "the strata buckle along the glowing fault!");
  sound(ctx.dim, SND.crack, mid, 1, 0.8);
  sound(ctx.dim, SND.grind, mid, 1, 0.9);
  for (let k = 0; k < 32; k += 4) {
    for (const q of pts) particle(ctx.dim, PX.fault, q, { life: 0.4 });
    for (let i = 0; i < 4; i++) particle(ctx.dim, PX.crack, pts[Math.floor(ctx.rng() * pts.length)]);
    quake(ctx.audience(), mid, 0.25, 0.25, 26);
    yield 4;
  }
  const f = t.add(foldField(a.x, a.z, b.x, b.z, 6.5));
  const H = ctx.enraged() ? 11 : 9;
  const hit = new Set<string>();
  sound(ctx.dim, SND.quake, mid, 1, 0.75);
  sound(ctx.dim, SND.groan, mid, 1, 1.1);
  for (let k = 1; k <= 24; k++) {
    f.amp = H * (1 - Math.pow(1 - k / 24, 3));
    for (const pl of ctx.combatants()) {
      if (hit.has(pl.id)) continue;
      const d = segDist(pl.location.x, pl.location.z, a.x, a.z, b.x, b.z);
      if (d.d < 2.3 && Math.abs(pl.location.y - surface(ctx, pl.location.x, pl.location.z)) < 5) {
        hit.add(pl.id);
        ctx.hurt(pl, 9, EntityDamageCause.entityAttack);
        const nx = pl.location.x - d.qx;
        const nz = pl.location.z - d.qz;
        knock(pl, nx || 1, nz, 1.2, 0.85);
      }
    }
    if (k % 2 === 0) for (let i = 0; i < 3; i++) particle(ctx.dim, PX.dust, pts[Math.floor(ctx.rng() * pts.length)], { size: 1.4 });
    if (k % 6 === 0) quake(ctx.audience(), mid, 0.8, 0.4, 40);
    yield 1;
  }
  // the fold stands, reshaping the paths
  for (let k = 0; k < 180; k += 20) {
    particle(ctx.dim, PX.debris, pts[Math.floor(ctx.rng() * pts.length)], { size: 1 });
    yield 20;
  }
  sound(ctx.dim, SND.grind, mid, 0.8, 0.7);
  for (let k = 1; k <= 60; k++) {
    f.amp = H * (1 - k / 60);
    yield 1;
  }
  t.remove(f);
}

function segDist(px: number, pz: number, ax: number, az: number, bx: number, bz: number) {
  const dx = bx - ax;
  const dz = bz - az;
  const l2 = dx * dx + dz * dz || 1;
  const s = clamp(((px - ax) * dx + (pz - az) * dz) / l2, 0, 1);
  const qx = ax + dx * s;
  const qz = az + dz * s;
  return { d: Math.hypot(px - qx, pz - qz), qx, qz };
}

/** Phase 2: a petal of the unfolded shell folds back over its sector of the arena. */
function* petalFold(ctx: MMContext, target: Player): Co {
  const tAng = diskAngle(target.location);
  let best: Entity | undefined;
  let bestD = 999;
  for (const e of ctx.petals) {
    if (!e.isValid) continue;
    const d = Math.abs(angleDiffDeg(diskAngle(e.location), tAng));
    if (d < bestD) {
      bestD = d;
      best = e;
    }
  }
  if (!best) return;
  const petal = best;
  const ang = diskAngle(petal.location);
  const half = 19;
  const at = { x: HX + Math.cos(ang * RAD) * 22, y: D.y + 1, z: HZ + Math.sin(ang * RAD) * 22 };
  warn(near(ctx, at, 40), "Continental Fold", "a petal is folding over its sector — get out!");
  sound(ctx.dim, SND.warn, at, 1, 0.8);
  sound(ctx.dim, SND.grind, petal.location, 1, 0.8);
  for (let k = 0; k < 40; k += 5) {
    for (const s of [-half, half]) {
      const a2 = (ang + s) * RAD;
      line(ctx.dim, PX.fault, { x: HX + Math.cos(a2) * 10, y: D.y + 1.1, z: HZ + Math.sin(a2) * 10 }, { x: HX + Math.cos(a2) * 33, y: D.y + 1.1, z: HZ + Math.sin(a2) * 33 }, 2.5, { life: 0.5 });
    }
    for (let i = 0; i < 6; i++) {
      const r = 12 + ctx.rng() * 20;
      const a2 = (ang + (ctx.rng() - 0.5) * 2 * half) * RAD;
      particle(ctx.dim, PX.crack, { x: HX + Math.cos(a2) * r, y: D.y + 1, z: HZ + Math.sin(a2) * r });
    }
    yield 5;
  }
  petal.setProperty(PROP.petalState, 2);
  yield 18;
  // impact
  sound(ctx.dim, SND.quake, at, 1, 0.7);
  quake(ctx.audience(), at, 2.2, 0.9, 60);
  const rubble: V3[] = [];
  for (let r = 11; r <= 31; r++) {
    for (let a2 = -half; a2 <= half; a2 += 2) {
      const aa = (ang + a2) * RAD;
      const x = Math.floor(HX + Math.cos(aa) * r);
      const z = Math.floor(HZ + Math.sin(aa) * r);
      if (!ctx.isWalkway(x, z)) continue;
      const h = (r * 7 + a2 * 3) % 5 === 0 ? 3 : 2;
      for (let y = D.y + 1; y <= D.y + h; y++) {
        ctx.writer.set(x, y, z, y === D.y + h ? P.MOSSY_COBBLE : ctx.m.strata(x, y, z));
        rubble.push({ x, y, z });
      }
    }
    if (r % 4 === 0) particle(ctx.dim, PX.dust, { x: HX + Math.cos(ang * RAD) * r, y: D.y + 2, z: HZ + Math.sin(ang * RAD) * r }, { size: 2.2 });
  }
  for (const pl of ctx.combatants()) {
    const r = diskRadius(pl.location);
    const d = Math.abs(angleDiffDeg(diskAngle(pl.location), ang));
    if (r > 10 && r < 35 && d < half + 2 && pl.location.y > D.mantleY) {
      ctx.hurt(pl, 12, EntityDamageCause.entityAttack);
      knock(pl, HX - pl.location.x, HZ - pl.location.z, 1.4, 0.6);
    }
  }
  yield 160;
  petal.setProperty(PROP.petalState, 1);
  sound(ctx.dim, SND.grind, petal.location, 0.9, 1.1);
  yield 12;
  for (const q of rubble) ctx.writer.set(q.x, q.y, q.z, P.AIR);
  for (let i = 0; i < 6; i++) particle(ctx.dim, PX.dust, rubble[Math.floor(ctx.rng() * rubble.length)] ?? at, { size: 1.6 });
}

// ============================================================================ 02 LITHIC PERISTALSIS
export function* lithicPeristalsis(ctx: MMContext, target: Player): Co {
  if (ctx.phase === 2) {
    yield* ribPeristalsis(ctx);
    return;
  }
  const t = ctx.terrain;
  const p = target.location;
  // waves start at the rim leg nearest the target and travel across the body through them
  let leg = ctx.m.legs[0];
  let bd = 1e9;
  for (const l of ctx.m.legs) {
    const d = Math.hypot(l.pos.x - p.x, l.pos.z - p.z);
    if (d < bd) {
      bd = d;
      leg = l;
    }
  }
  const ox = leg.pos.x;
  const oz = leg.pos.z;
  let dx = p.x - ox;
  let dz = p.z - oz;
  const l0 = Math.hypot(dx, dz) || 1;
  dx /= l0;
  dz /= l0;
  const legsNear = ctx.legs.filter((e) => e.isValid && Math.hypot(e.location.x - ox, e.location.z - oz) < 40);
  for (const e of legsNear) {
    try {
      e.playAnimation("animation.anatomy.mm_root_leg.stomp", { blendOutTime: 0.3 });
    } catch {
      /* ignore */
    }
  }
  const origin = { x: ox, y: leg.pos.y + 4, z: oz };
  warn(near(ctx, p, 40), "Lithic Peristalsis", "waves of strata roll through — jump them!");
  sound(ctx.dim, SND.rumble, origin, 1, 1);
  yield 22;
  sound(ctx.dim, SND.quake, origin, 1, 0.8);
  quake(ctx.audience(), origin, 1.2, 0.6, 70);
  const waves = ctx.enraged() ? 4 : 3;
  const sigma = 1.5;
  const halfSpan = 20;
  const speed = 0.5;
  const reach = 110;
  const live: { f: ReturnType<typeof waveField>; hit: Set<string>; done: boolean }[] = [];
  let tick = 0;
  let started = 0;
  while (started < waves || live.some((w) => !w.done)) {
    if (started < waves && tick === started * 24) {
      const f = t.add(waveField(ox, oz, dx, dz, 3, sigma, halfSpan));
      f.front = -4;
      updateWaveBounds(f, ox, oz, dx, dz, sigma, halfSpan);
      live.push({ f, hit: new Set(), done: false });
      sound(ctx.dim, SND.wave, origin, 1, 0.9 + started * 0.08);
      started++;
    }
    for (const w of live) {
      if (w.done) continue;
      w.f.front += speed;
      updateWaveBounds(w.f, ox, oz, dx, dz, sigma, halfSpan);
      if (w.f.front > reach) {
        w.done = true;
        t.remove(w.f);
        continue;
      }
      // dust along the crest near players
      for (const pl of ctx.audience()) {
        const rx = pl.location.x - ox;
        const rz = pl.location.z - oz;
        const s = rx * dx + rz * dz;
        if (Math.abs(s - w.f.front) < 14 && tick % 3 === 0) {
          const lat = -rx * dz + rz * dx + (ctx.rng() - 0.5) * 10;
          const qx = ox + dx * w.f.front - dz * lat;
          const qz = oz + dz * w.f.front + dx * lat;
          if (t.isDeformable(Math.floor(qx), Math.floor(qz))) particle(ctx.dim, PX.dust, { x: qx, y: t.topAt(Math.floor(qx), Math.floor(qz)) + 1, z: qz }, { size: 0.9 });
        }
      }
      for (const pl of ctx.combatants()) {
        if (w.hit.has(pl.id)) continue;
        const rx = pl.location.x + 0 - ox;
        const rz = pl.location.z - oz;
        const s = rx * dx + rz * dz;
        const lat = Math.abs(-rx * dz + rz * dx);
        if (lat > halfSpan - 1 || Math.abs(s - w.f.front) > 1.0) continue;
        const top = t.topAt(Math.floor(pl.location.x), Math.floor(pl.location.z));
        if (Math.abs(pl.location.y - (top + 1)) > 3.5) continue;
        w.hit.add(pl.id);
        if (pl.isOnGround) {
          ctx.hurt(pl, 6, EntityDamageCause.entityAttack);
          knock(pl, dx, dz, 0.9, 0.55);
        } else {
          pl.onScreenDisplay.setActionBar("§aYou leapt the wave!");
        }
      }
    }
    tick++;
    yield 1;
  }
}

/** Phase 2: rings of contraction run inward along the ribs toward the heart. */
function* ribPeristalsis(ctx: MMContext): Co {
  const waves = ctx.enraged() ? 4 : 3;
  const at = { x: HX, y: D.y + 1, z: HZ };
  warn(ctx.audience(), "Lithic Peristalsis", "the ribs ripple inward — jump each wave!");
  for (const e of ctx.legs)
    try {
      e.playAnimation("animation.anatomy.mm_root_leg.stomp", { blendOutTime: 0.3 });
    } catch {
      /* ignore */
    }
  sound(ctx.dim, SND.rumble, at, 1, 1.1);
  yield 20;
  const fronts: { r: number; hit: Set<string>; placed: V3[] }[] = [];
  let started = 0;
  let tick = 0;
  while (started < waves || fronts.some((f) => f.r > D.periR - 1)) {
    if (started < waves && tick === started * 26) {
      fronts.push({ r: D.ribEnd + 1, hit: new Set(), placed: [] });
      sound(ctx.dim, SND.wave, at, 1, 0.85 + started * 0.1);
      started++;
    }
    for (const f of fronts) {
      if (f.r <= D.periR - 1) continue;
      // clear the previous bump, raise the new one
      for (const q of f.placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
      f.placed = [];
      f.r -= 0.42;
      if (f.r <= D.periR - 1) continue;
      const steps = Math.ceil(2 * Math.PI * f.r * 1.2);
      for (let i = 0; i < steps; i++) {
        const a = (i / steps) * Math.PI * 2;
        const x = Math.floor(HX + Math.cos(a) * f.r);
        const z = Math.floor(HZ + Math.sin(a) * f.r);
        if (!ctx.isWalkway(x, z)) continue;
        const k = `${x},${z}`;
        if (f.placed.some((q) => `${q.x},${q.z}` === k)) continue;
        ctx.writer.set(x, D.y + 1, z, (x + z) % 3 === 0 ? P.VEIN_GLOW : P.MUSCLE);
        f.placed.push({ x, y: D.y + 1, z });
      }
      if (tick % 4 === 0) {
        const a = ctx.rng() * Math.PI * 2;
        particle(ctx.dim, PX.dust, { x: HX + Math.cos(a) * f.r, y: D.y + 1.5, z: HZ + Math.sin(a) * f.r }, { size: 0.8 });
      }
      for (const pl of ctx.combatants()) {
        if (f.hit.has(pl.id)) continue;
        if (Math.abs(diskRadius(pl.location) - f.r) > 0.9 || Math.abs(pl.location.y - (D.y + 1)) > 2) continue;
        f.hit.add(pl.id);
        if (pl.isOnGround) {
          ctx.hurt(pl, 7, EntityDamageCause.entityAttack);
          knock(pl, HX - pl.location.x, HZ - pl.location.z, 0.8, 0.5);
        } else pl.onScreenDisplay.setActionBar("§aYou leapt the wave!");
      }
    }
    tick++;
    yield 1;
  }
  for (const f of fronts) for (const q of f.placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
}

// ============================================================================ 03 GEOLOGICAL SHEDDING
export function* geologicalShedding(ctx: MMContext, targets: Player[]): Co {
  const shots: { from: V3; to: V3 }[] = [];
  const extra = ctx.enraged() ? 2 : 1;
  for (const pl of targets.slice(0, ctx.phase === 2 ? 4 : 3)) {
    const vel = pl.getVelocity();
    for (let i = 0; i < 1 + (ctx.rng() < 0.5 ? extra : 0); i++) {
      const tx = pl.location.x + vel.x * 16 + (ctx.rng() - 0.5) * (i ? 6 : 2.5);
      const tz = pl.location.z + vel.z * 16 + (ctx.rng() - 0.5) * (i ? 6 : 2.5);
      const ground = groundBelow(ctx, tx, pl.location.y, tz);
      const to = { x: tx, y: ground + 1, z: tz };
      const from = sheddingSource(ctx, to, pl);
      if (from) shots.push({ from, to });
    }
  }
  if (!shots.length) return;
  warn(
    near(ctx, shots[0].to, 30),
    "Geological Shedding",
    "the rock skin peels away — leave the marked rings!",
  );
  const scars: ReturnType<typeof patchField>[] = [];
  for (const s of shots) {
    particle(ctx.dim, PX.target, s.to, { radius: 3.6, life: 2.0 });
    particle(ctx.dim, PX.crack, s.from);
    particle(ctx.dim, PX.dust, s.from, { size: 1.6 });
    sound(ctx.dim, SND.crack, s.from, 1, 0.9 + ctx.rng() * 0.2);
    if (ctx.phase === 1) {
      const x = Math.floor(s.from.x);
      const z = Math.floor(s.from.z);
      if (ctx.terrain.isDeformable(x, z) && s.from.y > ctx.m.under[ctx.m.col(x, z)] + 3) scars.push(ctx.terrain.add(patchField(x - 2, z - 2, x + 2, z + 2, 1, true)));
    }
  }
  yield 30;
  for (const s of shots) {
    launchSlab(ctx, s.from, s.to);
    sound(ctx.dim, SND.whoosh, s.from, 1, 0.8);
    yield 3;
  }
  // scars regrow after a while
  yield 400;
  for (const f of scars) ctx.terrain.remove(f);
}

function groundBelow(ctx: MMContext, x: number, y: number, z: number): number {
  if (ctx.phase === 2) {
    const r = diskRadius({ x, y, z });
    if (r <= D.outerR + 0.5) return ctx.isWalkway(Math.floor(x), Math.floor(z)) ? D.y : D.mantleY;
  }
  const t = ctx.terrain.topAt(Math.floor(x), Math.floor(z));
  if (t > -32768 && t <= y + 2) return t;
  // inside the cavern / underbelly: use the player's own floor
  return Math.floor(y) - 1;
}

function sheddingSource(ctx: MMContext, to: V3, pl: Player): V3 | undefined {
  if (ctx.phase === 2) {
    const valid = ctx.petals.filter((e) => e.isValid);
    if (!valid.length) return { x: to.x, y: to.y + 28, z: to.z };
    valid.sort((a, b) => distXZ(a.location, to) - distXZ(b.location, to));
    const e = valid[Math.floor(ctx.rng() * Math.min(3, valid.length))];
    const out = Math.atan2(e.location.z - HZ, e.location.x - HX);
    return { x: e.location.x + Math.cos(out) * 10, y: e.location.y + 26 + ctx.rng() * 6, z: e.location.z + Math.sin(out) * 10 };
  }
  const zone = ctx.zoneOf(pl);
  if (zone === "under") {
    const x = Math.floor(to.x);
    const z = Math.floor(to.z);
    if (ctx.m.inCols(x, z) && ctx.m.flags[ctx.m.col(x, z)] & ColFlag.BODY) return { x: to.x, y: ctx.m.under[ctx.m.col(x, z)] - 1.5, z: to.z };
    return undefined;
  }
  if (zone === "cavern") return undefined;
  // highest nearby slope above the target
  let best: V3 | undefined;
  for (let i = 0; i < 14; i++) {
    const a = ctx.rng() * Math.PI * 2;
    const r = 9 + ctx.rng() * 14;
    const x = Math.floor(to.x + Math.cos(a) * r);
    const z = Math.floor(to.z + Math.sin(a) * r);
    if (!ctx.terrain.isDeformable(x, z)) continue;
    const y = ctx.terrain.topAt(x, z);
    if (!best || y > best.y) best = { x: x + 0.5, y: y + 1.5, z: z + 0.5 };
  }
  if (best && best.y < to.y + 3) best.y = to.y + 8;
  return best ?? { x: to.x, y: to.y + 14, z: to.z };
}

function launchSlab(ctx: MMContext, from: V3, to: V3): void {
  let slab: Entity;
  try {
    slab = ctx.dim.spawnEntity(ENT.slab, from);
  } catch {
    return;
  }
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dz = to.z - from.z;
  const horiz = Math.hypot(dx, dz);
  // a high, slow arc: the slab is flung up off the body and comes crashing down on the ring
  const T = Math.round(clamp(26 + horiz * 0.5, 30, 44));
  const g = 0.08;
  const vel = { x: dx / T, y: (dy + 0.5 * g * T * (T + 1)) / T, z: dz / T };
  try {
    const proj = slab.getComponent("minecraft:projectile");
    if (proj) {
      proj.gravity = g;
      if (ctx.heart?.isValid) proj.owner = ctx.heart;
      proj.shoot(vel, { uncertainty: 0 });
    } else slab.applyImpulse(vel);
  } catch {
    try {
      slab.applyImpulse(vel);
    } catch {
      /* ignore */
    }
  }
  ctx.trackSlab(slab, to, ctx.now + T + 24, ctx.phase === 2 ? 11 : 9);
}

// ============================================================================ 04 RESONANCE NETWORK
export function* resonanceNetwork(ctx: MMContext, target: Player): Co {
  let src: V3;
  let srcEnt: Entity | undefined;
  if (ctx.phase === 2) {
    srcEnt = ctx.heart;
    src = { x: HX, y: D.y + 1, z: HZ };
  } else {
    const nodes = ctx.livingNodes();
    if (!nodes.length) return;
    nodes.sort((a, b) => distXZ(a.entity.location, target.location) - distXZ(b.entity.location, target.location));
    srcEnt = nodes[0].entity;
    const site = nodes[0].site;
    src = site.id === "root" ? { x: site.pos.x, y: MM.gallery.y + 1, z: site.pos.z } : { x: site.pos.x, y: site.pos.y, z: site.pos.z };
  }
  if (!srcEnt?.isValid) return;
  srcEnt.setProperty(PROP.charging, true);
  warn(near(ctx, src, 40), "Resonance Network", "rings of resonance — stand in the green gaps!");
  sound(ctx.dim, SND.resonance, src, 1, 1);
  // the network lights up: beams from every living node to the heart
  for (let k = 0; k < 40; k += 5) {
    if (ctx.heart?.isValid) {
      const h = { x: HX, y: ctx.heart.location.y + 3, z: HZ };
      for (const n of ctx.livingNodes()) {
        const from = { x: n.entity.location.x, y: n.entity.location.y + 1.6, z: n.entity.location.z };
        const v = { x: h.x - from.x, y: h.y - from.y, z: h.z - from.z };
        const L = Math.hypot(v.x, v.y, v.z) || 1;
        particle(ctx.dim, PX.beam, from, { dir: { x: v.x / L, y: v.y / L, z: v.z / L }, speed: L / 1.2, life: 1.2 });
      }
    }
    particle(ctx.dim, PX.wave, src, { radius: 6, life: 0.6 });
    yield 5;
  }
  const rings = (ctx.phase === 2 ? 4 : 3) + (ctx.enraged() ? 1 : 0);
  const gap = ctx.phase === 2 ? 38 : 48;
  const speed = ctx.phase === 2 ? 0.46 : 0.4;
  const maxR = ctx.phase === 2 ? D.outerR + 1 : 27;
  const interval = ctx.phase === 2 ? 24 : 28;
  const base = ctx.rng() * 360;
  const active: { r: number; dir: number; hit: Set<string> }[] = [];
  let tick = 0;
  let started = 0;
  while (started < rings || active.some((a) => a.r < maxR)) {
    if (started < rings && tick === started * interval) {
      active.push({ r: 1.2, dir: base + started * 67, hit: new Set() });
      sound(ctx.dim, SND.chime, src, 1, 0.8 + started * 0.12);
      particle(ctx.dim, PX.wave, src, { radius: maxR, life: maxR / (speed * 20) });
      started++;
    }
    for (const a of active) {
      if (a.r >= maxR) continue;
      a.r += speed;
      particle(ctx.dim, PX.ring, src, { radius: a.r, gap, gapDir: a.dir });
      if (tick % 3 === 0)
        for (const g of [a.dir, a.dir + 180]) particle(ctx.dim, PX.safe, { x: src.x + Math.cos(g * RAD) * a.r, y: src.y, z: src.z + Math.sin(g * RAD) * a.r }, { radius: 0.8 });
      for (const pl of ctx.combatants()) {
        if (a.hit.has(pl.id)) continue;
        const d = Math.hypot(pl.location.x - src.x, pl.location.z - src.z);
        if (Math.abs(d - a.r) > 0.85 || Math.abs(pl.location.y - src.y) > 2.8) continue;
        const ang = Math.atan2(pl.location.z - src.z, pl.location.x - src.x) / RAD;
        const inGap = Math.abs(angleDiffDeg(ang, a.dir)) < gap / 2 - 3 || Math.abs(angleDiffDeg(ang, a.dir + 180)) < gap / 2 - 3;
        a.hit.add(pl.id);
        if (inGap) continue;
        ctx.hurt(pl, ctx.phase === 2 ? 8 : 6, EntityDamageCause.magic);
        try {
          pl.addEffect("slowness", 50, { amplifier: 1, showParticles: false });
        } catch {
          /* ignore */
        }
        knock(pl, pl.location.x - src.x, pl.location.z - src.z, 0.6, 0.3);
        particle(ctx.dim, PX.shard, pl.location, { size: 0.6 });
      }
    }
    tick++;
    yield 1;
  }
  if (srcEnt.isValid) srcEnt.setProperty(PROP.charging, false);
  if (ctx.phase === 2) ctx.exposeHeart(170);
}

// ============================================================================ 05 INVERTED STRATA
export function* invertedStrata(ctx: MMContext, target: Player): Co {
  if (ctx.phase === 2) {
    yield* ribFlip(ctx, target);
    return;
  }
  const t = ctx.terrain;
  const p = target.location;
  // find a 5x11 strip near the target; the strata level themselves into a slab before flipping
  let strip: { cx: number; cz: number; alongX: boolean; top: number } | undefined;
  for (let attempt = 0; attempt < 40 && !strip; attempt++) {
    const alongX = ctx.rng() < 0.5;
    const radius = attempt < 12 ? 4 : 10;
    const cx = Math.floor(p.x + (ctx.rng() - 0.5) * radius * 2);
    const cz = Math.floor(p.z + (ctx.rng() - 0.5) * radius * 2);
    const tops: number[] = [];
    let ok = true;
    for (let u = -2; u <= 2 && ok; u++)
      for (let v = -5; v <= 5; v++) {
        const x = alongX ? cx + v : cx + u;
        const z = alongX ? cz + u : cz + v;
        if (!t.isDeformable(x, z)) {
          ok = false;
          break;
        }
        tops.push(t.topAt(x, z));
      }
    if (!ok) continue;
    tops.sort((a, b) => a - b);
    if (tops[tops.length - 1] - tops[0] > 6) continue;
    const h0 = tops[Math.floor(tops.length / 2)];
    // the flipped bed must stay clear of the Organ Cavern roof
    let safe = true;
    for (let u = -2; u <= 2 && safe; u++)
      for (let v = -5; v <= 5; v++) {
        const x = alongX ? cx + v : cx + u;
        const z = alongX ? cz + u : cz + v;
        const ct = ctx.m.caveTop[ctx.m.col(x, z)];
        if (ct > -32768 && h0 - 3 < ct + 3) {
          safe = false;
          break;
        }
      }
    if (safe) strip = { cx, cz, alongX, top: h0 };
  }
  if (!strip) return;
  const s = strip;
  const base = s.top - 2;
  const cells: { x: number; z: number; u: number; v: number }[] = [];
  for (let u = -2; u <= 2; u++) for (let v = -5; v <= 5; v++) cells.push({ x: s.alongX ? s.cx + v : s.cx + u, z: s.alongX ? s.cz + u : s.cz + v, u, v });
  const toWorld = (u: number, v: number) => (s.alongX ? { x: s.cx + v, z: s.cz + u } : { x: s.cx + u, z: s.cz + v });
  const mode: 1 | 2 = ctx.rng() < 0.55 ? 1 : 2;
  const centre = { x: s.cx + 0.5, y: s.top + 1, z: s.cz + 0.5 };
  const x0 = Math.min(...cells.map((c) => c.x));
  const z0 = Math.min(...cells.map((c) => c.z));
  const x1 = Math.max(...cells.map((c) => c.x));
  const z1 = Math.max(...cells.map((c) => c.z));
  const level = t.add({
    x0,
    z0,
    x1,
    z1,
    k: 0,
    bed: false,
    scar: false,
    dh(x: number, z: number): number {
      const target = this.bed ? s.top - 3 : s.top;
      return (target - ctx.m.top[ctx.m.col(x, z)]) * (this.bed ? 1 : this.k);
    },
  } as import("./terrain.js").Field & { k: number; bed: boolean });
  warn(near(ctx, centre, 22), "Inverted Strata", mode === 1 ? "the walkway will stand up as a wall!" : "the walkway will roll over into a ceiling!");
  sound(ctx.dim, SND.grind, centre, 1, 1.2);
  for (let k = 0; k < 28; k += 4) {
    level.k = Math.min(1, (k + 4) / 16);
    for (let v = -5; v <= 5; v += 2) {
      for (const u of [-2.5, 2.5]) {
        const w = toWorld(0, v);
        const q = s.alongX ? { x: w.x + 0.5, z: s.cz + u + 0.5 } : { x: s.cx + u + 0.5, z: w.z + 0.5 };
        particle(ctx.dim, PX.fault, { x: q.x, y: s.top + 1.05, z: q.z }, { life: 0.45 });
      }
    }
    for (const u of [-2, 0, 2])
      for (const v of [-5.5, 5.5]) {
        const q = s.alongX ? { x: s.cx + v + 0.5, z: s.cz + u + 0.5 } : { x: s.cx + u + 0.5, z: s.cz + v + 0.5 };
        particle(ctx.dim, PX.fault, { x: q.x, y: s.top + 1.05, z: q.z }, { life: 0.45 });
      }
    yield 4;
  }
  // the plate tears free
  let plate: Entity | undefined;
  try {
    plate = ctx.dim.spawnEntity(ENT.plate, { x: s.cx + 0.5, y: base, z: s.cz + 0.5 }, { initialRotation: s.alongX ? 90 : 0 });
    plate.setProperty(PROP.variant, 0);
    plate.setProperty(PROP.flip, mode);
  } catch {
    plate = undefined;
  }
  level.bed = true;
  level.scar = true;
  sound(ctx.dim, SND.crack, centre, 1, 0.7);
  sound(ctx.dim, SND.grind, centre, 1, 0.8);
  for (const pl of ctx.combatants()) {
    const inStrip = cells.some((c) => Math.floor(pl.location.x) === c.x && Math.floor(pl.location.z) === c.z) && Math.abs(pl.location.y - (s.top + 1)) < 2.5;
    if (!inStrip) continue;
    ctx.hurt(pl, 7, EntityDamageCause.entityAttack);
    const side = s.alongX ? { x: 0, z: pl.location.z >= s.cz + 0.5 ? 1 : -1 } : { x: pl.location.x >= s.cx + 0.5 ? 1 : -1, z: 0 };
    knock(pl, side.x, side.z, 0.9, 1.0);
  }
  for (let i = 0; i < 6; i++) particle(ctx.dim, PX.dust, { x: centre.x + (ctx.rng() - 0.5) * 6, y: centre.y, z: centre.z + (ctx.rng() - 0.5) * 6 }, { size: 1.5 });
  yield 28;
  // freeze the end pose as real blocks
  const placed: V3[] = [];
  const put = (x: number, y: number, z: number, b: number) => {
    ctx.writer.set(x, y, z, b);
    placed.push({ x, y, z });
  };
  if (mode === 1) {
    for (let u = -1; u <= 1; u++)
      for (let v = -5; v <= 5; v++)
        for (let y = base - 1; y <= base + 3; y++) {
          const w = toWorld(u, v);
          put(w.x, y, w.z, u === -1 ? (y === base + 3 ? P.GRASS : P.MOSS) : u === 1 ? P.MUSCLE : ctx.m.strata(w.x, y, w.z));
        }
  } else {
    for (const c of cells)
      for (let y = base + 6; y <= base + 8; y++) put(c.x, y, c.z, y === base + 6 ? P.GRASS : y === base + 8 ? P.MUSCLE : ctx.m.strata(c.x, y, c.z));
  }
  ctx.writer.flushAll();
  if (plate?.isValid) plate.remove();
  quake(ctx.audience(), centre, 0.9, 0.4, 30);
  sound(ctx.dim, SND.quake, centre, 0.8, 1.2);
  yield ctx.enraged() ? 200 : 280;
  // revert: the plate settles back into the walkway
  for (const q of placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
  ctx.writer.flushAll();
  try {
    plate = ctx.dim.spawnEntity(ENT.plate, { x: s.cx + 0.5, y: base, z: s.cz + 0.5 }, { initialRotation: s.alongX ? 90 : 0 });
    plate.setProperty(PROP.variant, 0);
    plate.setProperty(PROP.flip, mode === 1 ? 3 : 4);
  } catch {
    plate = undefined;
  }
  sound(ctx.dim, SND.grind, centre, 0.8, 1.1);
  yield 22;
  t.remove(level);
  yield 2;
  if (plate?.isValid) plate.remove();
}

/** Phase 2: a rib segment flips into a wall or rolls up into a ceiling, cutting a route. */
function* ribFlip(ctx: MMContext, target: Player): Co {
  const pitch = 360 / D.ribs;
  const offset = ctx.layout ? pitch / 2 : 0;
  const tAng = diskAngle(target.location);
  const k = Math.round((tAng - offset) / pitch);
  const ribAng = (k * pitch + offset) * RAD;
  const r0 = 12;
  const r1 = 20;
  const cells: V3[] = [];
  for (let r = r0; r <= r1; r += 0.5)
    for (let w = -1; w <= 1; w++) {
      const x = Math.floor(HX + Math.cos(ribAng) * r - Math.sin(ribAng) * w);
      const z = Math.floor(HZ + Math.sin(ribAng) * r + Math.cos(ribAng) * w);
      if (!cells.some((c) => c.x === x && c.z === z) && ctx.isWalkway(x, z)) cells.push({ x, y: D.y, z });
    }
  if (cells.length < 6) return;
  const mode: 1 | 2 = ctx.rng() < 0.5 ? 1 : 2;
  const mid = { x: HX + Math.cos(ribAng) * 16, y: D.y + 1, z: HZ + Math.sin(ribAng) * 16 };
  warn(near(ctx, mid, 36), "Inverted Strata", mode === 1 ? "a rib will stand up as a wall!" : "a rib will roll into the ceiling — don't stand on it!");
  sound(ctx.dim, SND.grind, mid, 1, 1.2);
  for (let t = 0; t < 26; t += 4) {
    for (const c of cells) if ((c.x + c.z + t) % 3 === 0) particle(ctx.dim, PX.fault, { x: c.x + 0.5, y: D.y + 1.05, z: c.z + 0.5 }, { life: 0.4 });
    yield 4;
  }
  let plate: Entity | undefined;
  try {
    plate = ctx.dim.spawnEntity(ENT.plate, { x: mid.x, y: D.y - 2, z: mid.z }, { initialRotation: -(ribAng / RAD) + 90 });
    plate.setProperty(PROP.variant, 1);
    plate.setProperty(PROP.flip, mode);
  } catch {
    plate = undefined;
  }
  for (const c of cells) for (let y = D.y - 3; y <= D.y; y++) ctx.writer.set(c.x, y, c.z, P.AIR);
  ctx.writer.flushAll();
  for (const pl of ctx.combatants()) {
    if (!cells.some((c) => Math.floor(pl.location.x) === c.x && Math.floor(pl.location.z) === c.z)) continue;
    ctx.hurt(pl, 7, EntityDamageCause.entityAttack);
    knock(pl, -Math.sin(ribAng), Math.cos(ribAng), 0.7, 1.0);
  }
  sound(ctx.dim, SND.crack, mid, 1, 0.7);
  yield 28;
  const placed: V3[] = [];
  for (const c of cells) {
    const ys = mode === 1 ? [D.y + 1, D.y + 2, D.y + 3] : [D.y + 5, D.y + 6, D.y + 7];
    for (const y of ys) {
      ctx.writer.set(c.x, y, c.z, y === ys[1] ? P.SINEW : P.MUSCLE);
      placed.push({ x: c.x, y, z: c.z });
    }
  }
  ctx.writer.flushAll();
  if (plate?.isValid) plate.remove();
  quake(ctx.audience(), mid, 0.8, 0.4, 40);
  yield ctx.enraged() ? 180 : 240;
  for (const q of placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
  try {
    plate = ctx.dim.spawnEntity(ENT.plate, { x: mid.x, y: D.y - 2, z: mid.z }, { initialRotation: -(ribAng / RAD) + 90 });
    plate.setProperty(PROP.variant, 1);
    plate.setProperty(PROP.flip, mode === 1 ? 3 : 4);
  } catch {
    plate = undefined;
  }
  yield 22;
  for (const c of cells) for (let y = D.y - 3; y <= D.y; y++) ctx.writer.set(c.x, y, c.z, ctx.m.phase2Block(c.x, y, c.z, ctx.layout));
  yield 2;
  if (plate?.isValid) plate.remove();
}

// ============================================================================ 06 MANTLE CONTRACTION
export function* mantleContraction(ctx: MMContext, pockets: V3[]): Co {
  if (ctx.phase === 2) {
    yield* diskContraction(ctx);
    return;
  }
  const cv = MM.cavern;
  const floor = cv.floorY;
  const centre = { x: cv.x, y: floor + 1, z: cv.z };
  const inCave = ctx.combatants().filter((p) => ctx.zoneOf(p) === "cavern");
  warn(inCave.length ? inCave : near(ctx, centre, 30), "Mantle Contraction", "the cavern squeezes shut — get into a glowing pocket!");
  sound(ctx.dim, SND.contract, centre, 1, 0.9);
  sound(ctx.dim, SND.groan, centre, 1, 0.8);
  for (let t = 0; t < 50; t += 5) {
    for (const p of pockets) {
      particle(ctx.dim, PX.pillar, p, { radius: 2.2, life: 0.5 });
      particle(ctx.dim, PX.safe, p, { radius: 2.0 });
    }
    for (let i = 0; i < 6; i++) {
      const a = ctx.rng() * Math.PI * 2;
      particle(ctx.dim, PX.crack, { x: cv.x + Math.cos(a) * cv.rx * 0.95, y: floor + 1 + ctx.rng() * 3, z: cv.z + Math.sin(a) * cv.rz * 0.95 });
    }
    yield 5;
  }
  // columns of the cavern floor ordered by normalised radius
  const cells: { x: number; z: number; q: number }[] = [];
  for (let x = cv.x - cv.rx; x <= cv.x + cv.rx; x++)
    for (let z = cv.z - cv.rz; z <= cv.z + cv.rz; z++) {
      const q = Math.hypot((x + 0.5 - cv.x) / cv.rx, (z + 0.5 - cv.z) / cv.rz);
      if (q > 1.02) continue;
      if (pockets.some((p) => Math.hypot(x + 0.5 - p.x, z + 0.5 - p.z) < 2.4)) continue;
      if (Math.hypot(x + 0.5 - MM.heart.x, z + 0.5 - MM.heart.z) < 7.6) continue; // the heart cradle
      if (ctx.originalBlock(x, floor + 1, z) !== P.AIR) continue;
      cells.push({ x, z, q });
    }
  cells.sort((a, b) => b.q - a.q);
  const H = 5;
  const filled: { x: number; z: number; ys: { y: number; b: number }[] }[] = [];
  let idx = 0;
  const steps = 60;
  for (let t = 1; t <= steps; t++) {
    const front = 1.02 - (t / steps) * 0.9;
    while (idx < cells.length && cells[idx].q >= front) {
      const c = cells[idx++];
      const ys: { y: number; b: number }[] = [];
      for (let y = floor + 1; y <= floor + H; y++) {
        const orig = ctx.originalBlock(c.x, y, c.z);
        if (orig !== P.AIR && orig !== P.KEEP && orig !== P.LIGHT_12) continue;
        ys.push({ y, b: orig === P.KEEP ? P.AIR : orig });
        ctx.writer.set(c.x, y, c.z, (c.x * 7 + y * 3 + c.z) % 9 === 0 ? P.VEIN_GLOW : (c.x + c.z + y) % 3 === 0 ? P.FLESH : P.MUSCLE);
      }
      filled.push({ x: c.x, z: c.z, ys });
      // anyone caught is crushed and squeezed into the nearest pocket
      for (const pl of ctx.combatants()) {
        if (Math.floor(pl.location.x) !== c.x || Math.floor(pl.location.z) !== c.z) continue;
        if (pl.location.y < floor || pl.location.y > floor + H + 1) continue;
        ctx.hurt(pl, 12, EntityDamageCause.entityAttack);
        const pk = pockets.reduce((a, b) => (distXZ(a, pl.location) < distXZ(b, pl.location) ? a : b));
        try {
          pl.teleport({ x: pk.x, y: floor + 1.05, z: pk.z }, { keepVelocity: false });
          pl.addEffect("slowness", 60, { amplifier: 2, showParticles: false });
        } catch {
          /* ignore */
        }
      }
    }
    if (t % 10 === 0) {
      sound(ctx.dim, SND.contract, centre, 0.8, 0.8 + t / steps);
      quake(ctx.audience(), centre, 0.7, 0.5, 30);
    }
    yield 1;
  }
  for (let t = 0; t < 40; t += 10) {
    for (const p of pockets) particle(ctx.dim, PX.safe, p, { radius: 2.0 });
    yield 10;
  }
  sound(ctx.dim, SND.contract, centre, 0.9, 1.3);
  // relax from the inside out
  for (let i = filled.length - 1; i >= 0; i--) {
    const c = filled[i];
    for (const q of c.ys) ctx.writer.set(c.x, q.y, c.z, q.b);
    if (i % 40 === 0) yield 1;
  }
}

/** Phase 2: the disk contracts toward the heart; only the pericardium ring is safe. */
function* diskContraction(ctx: MMContext): Co {
  const centre = { x: HX, y: D.y + 1, z: HZ };
  warn(ctx.audience(), "Mantle Contraction", "the world closes in — reach the heart's ring!");
  sound(ctx.dim, SND.contract, centre, 1, 0.8);
  sound(ctx.dim, SND.groan, centre, 1, 0.9);
  for (let t = 0; t < 60; t += 5) {
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * Math.PI * 2 + t * 0.05;
      particle(ctx.dim, PX.safe, { x: HX + Math.cos(a) * 6.5, y: D.y + 1, z: HZ + Math.sin(a) * 6.5 }, { radius: 0.6 });
    }
    for (let i = 0; i < 8; i++) {
      const a = ctx.rng() * Math.PI * 2;
      particle(ctx.dim, PX.crack, { x: HX + Math.cos(a) * 31, y: D.y + 1, z: HZ + Math.sin(a) * 31 });
    }
    yield 5;
  }
  const cells: { x: number; z: number; r: number }[] = [];
  const R = D.outerR + 1;
  for (let x = Math.floor(HX - R); x <= Math.ceil(HX + R); x++)
    for (let z = Math.floor(HZ - R); z <= Math.ceil(HZ + R); z++) {
      const r = Math.hypot(x + 0.5 - HX, z + 0.5 - HZ);
      if (r > R || r < D.periR) continue;
      if (!ctx.isWalkway(x, z)) continue;
      cells.push({ x, z, r });
    }
  cells.sort((a, b) => b.r - a.r);
  let idx = 0;
  const steps = 80;
  const placed: V3[] = [];
  for (let t = 1; t <= steps; t++) {
    const front = R - (t / steps) * (R - D.periR);
    while (idx < cells.length && cells[idx].r >= front) {
      const c = cells[idx++];
      for (let y = D.y + 1; y <= D.y + 2; y++) {
        ctx.writer.set(c.x, y, c.z, (c.x + y + c.z) % 4 === 0 ? P.FLESH : P.MUSCLE);
        placed.push({ x: c.x, y, z: c.z });
      }
      for (const pl of ctx.combatants()) {
        if (Math.floor(pl.location.x) !== c.x || Math.floor(pl.location.z) !== c.z || Math.abs(pl.location.y - (D.y + 1)) > 2) continue;
        ctx.hurt(pl, 10, EntityDamageCause.entityAttack);
        const a = Math.atan2(pl.location.z - HZ, pl.location.x - HX);
        try {
          pl.teleport({ x: HX + Math.cos(a) * 6.5, y: D.y + 1.05, z: HZ + Math.sin(a) * 6.5 }, { keepVelocity: false });
        } catch {
          /* ignore */
        }
      }
    }
    if (t % 10 === 0) quake(ctx.audience(), centre, 0.8, 0.5, 50);
    yield 1;
  }
  // everyone is pressed against the heart: it opens
  ctx.exposeHeart(180);
  yield 50;
  sound(ctx.dim, SND.contract, centre, 0.9, 1.3);
  for (let i = placed.length - 1; i >= 0; i--) {
    const q = placed[i];
    ctx.writer.set(q.x, q.y, q.z, P.AIR);
    if (i % 60 === 0) yield 1;
  }
}

// ============================================================================ slab impacts (03)
export function slabImpact(ctx: MMContext, at: V3, power: number): void {
  particle(ctx.dim, PX.dust, at, { size: 2.2 });
  particle(ctx.dim, PX.debris, at, { size: 3 });
  sound(ctx.dim, SND.quake, at, 1, 0.9 + ctx.rng() * 0.2);
  quake(ctx.audience(), at, 1.4, 0.5, 26);
  for (const pl of ctx.combatants()) {
    const d = Math.hypot(pl.location.x - at.x, pl.location.y - at.y, pl.location.z - at.z);
    if (d > 3.8) continue;
    ctx.hurt(pl, power * (d < 1.8 ? 1.25 : 1), EntityDamageCause.fallingBlock);
    knock(pl, pl.location.x - at.x || 0.1, pl.location.z - at.z, 0.9, 0.5);
  }
}
