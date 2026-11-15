/**
 * Phase 3 of THE MIGRATING MOUNTAIN.
 *
 *   3A The Last Migration - refolded into a crown, the mountain walks across the cloud sea, held by
 *      four Anchorage Roots that burst up through the disk to grip it; each severed root opens the heart.
 *   3B The Heart Unbound - the mountain falls apart; the Lithic Heart tears free and fights from above
 *      a ring of floating islands, slamming down onto the centre island.
 *
 * Here: the two transitions (the last forms of 07 The Great Unfolding) and the Phase 3 forms of
 * abilities 01, 02, 04, 05 and 06 (03 Geological Shedding works unchanged on the disk and islands).
 */
import { EntityDamageCause, Player } from "@minecraft/server";
import { knock } from "../../core/arena.js";
import { line, particle, quake, shake, sound, title, titleFor } from "../../core/fx.js";
import { tr } from "../../core/lang.js";
import { Co } from "../../core/tasks.js";
import { angleDiffDeg, V3 } from "../../core/vec.js";
import { MM } from "../../gen/mountain.js";
import * as P from "../../gen/palette.js";
import { MMContext } from "./context.js";
import { PROP, PX, SND } from "./ids.js";
import { clearIsland, Island, islandAt, writeIsland } from "./runtime.js";
import { cam, lockPlayers } from "./unfolding.js";

const D = MM.disk;
const HX = MM.heart.x;
const HZ = MM.heart.z;
const RAD = Math.PI / 180;

export const ANCHORS = 4;
/** Radius of the ring the Anchorage Roots grip (the inner ring walkway). */
export const ANCHOR_R = 19;
/** Heart anchor height while it hovers above the centre island, and when it slams down onto it (3B). */
export const HOVER_Y = D.y + 11;
export const SLAM_Y = D.y + 1;

/**
 * Angles of the four roots: the middle of the second ring's arcs, which are walkway in both rib layouts
 * (the arc near 225 deg is cut by the spiral shaft, so that root grips its solid part at 212.5 deg).
 */
const ANCHOR_DEG = [45, 135, 212.5, 315];

/** Where Anchorage Root `k` grips the disk; its model faces the heart (front -Z). */
export function anchorSite(k: number): { pos: V3; yaw: number } {
  const a = ANCHOR_DEG[k] * RAD;
  const pos = { x: HX + Math.cos(a) * ANCHOR_R, y: D.y + 1, z: HZ + Math.sin(a) * ANCHOR_R };
  const yaw = (Math.atan2(-(HX - pos.x), HZ - pos.z) * 180) / Math.PI;
  return { pos, yaw };
}

const TH: Record<string, string> = {
  "a footfall drives a fault across the disk — get off the line!": "ก้าวเท้ากระแทกจนรอยเลื่อนพาดผ่านลาน — ออกจากแนวเส้น!",
  "the march quakes the disk — jump each wave!": "แรงก้าวเดินทำให้ลานสั่น — กระโดดข้ามทุกคลื่น!",
  "the island cracks — get to the other half!": "เกาะกำลังร้าว — ไปอีกครึ่งหนึ่ง!",
  "shockwaves roll across the islands — jump them!": "คลื่นกระแทกวิ่งผ่านเกาะ — กระโดดข้าม!",
  "the heart channels molten mineral — leave the glowing arc!": "หัวใจกำลังส่งแร่หลอมเหลว — ออกจากแนวโค้งที่เรืองแสง!",
  "this island is turning over — jump off it!": "เกาะนี้กำลังพลิกคว่ำ — กระโดดออก!",
  "the heart drags you in — hold your ground, then brace!": "หัวใจกำลังดูดเข้าไป — ยืนให้มั่นแล้วเตรียมรับแรงกระแทก!",
};

function warn(players: Player[], name: string, hint: string): void {
  for (const p of players) title([p], "", `§c⚠ ${name} §7— ${tr(p, hint, TH[hint] ?? hint)}`, 34, 4, 10);
}

function fade(players: Player[], r: number, g: number, b: number): void {
  for (const p of players)
    try {
      p.camera.fade({ fadeColor: { red: r, green: g, blue: b }, fadeTime: { fadeInTime: 0.4, holdTime: 0.5, fadeOutTime: 0.9 } });
    } catch {
      /* ignore */
    }
}

function effect(players: Player[], id: string, ticks: number, amp = 0): void {
  for (const p of players)
    try {
      p.addEffect(id, ticks, { amplifier: amp, showParticles: false });
    } catch {
      /* ignore */
    }
}

function rmEffect(players: Player[], id: string): void {
  for (const p of players)
    try {
      p.removeEffect(id);
    } catch {
      /* ignore */
    }
}

// ============================================================================ transitions
export interface Phase3Hooks {
  spawnAnchors(): void;
  enterPhase3a(): void;
  shatter(): Co;
  moveHeart(y: number): void;
  removePetals(): void;
  enterPhase3b(): void;
}

/** 07, refolded (Phase 2 -> 3A): the shell rises into a crown, the roots seize the disk, the mountain starts to walk. */
export function* refoldToMigration(ctx: MMContext, hooks: Phase3Hooks): Co {
  const viewers = ctx.audience();
  const centre = { x: HX, y: D.y + 1, z: HZ };
  lockPlayers(viewers, true);
  effect(viewers, "resistance", 400, 4);
  cam(viewers, { x: HX - 50, y: D.y + 32, z: HZ - 56 }, { x: HX, y: D.y + 6, z: HZ }, 0);
  titleFor(viewers, (p) => ["§d07 · THE LAST MIGRATION", tr(p, "§7Its heart failing, the mountain refolds and walks away across the cloud sea.", "§7หัวใจใกล้แตก ภูเขาพับตัวกลับแล้วเดินหนีไปบนทะเลเมฆ")], 80, 10, 20);
  sound(ctx.dim, SND.groan, centre, 1, 0.6);
  sound(ctx.dim, SND.unfold, centre, 1, 0.75);
  ctx.setPetals(4);
  quake(viewers, centre, 1.2, 2.0, 120);
  yield 50;
  cam(viewers, { x: HX + 44, y: D.y + 20, z: HZ - 34 }, { x: HX, y: D.y + 3, z: HZ }, 4);
  ctx.setLegPose(3);
  sound(ctx.dim, SND.rumble, centre, 1, 0.8);
  yield 30;
  hooks.spawnAnchors();
  for (let k = 0; k < ANCHORS; k++) {
    const s = anchorSite(k);
    sound(ctx.dim, SND.rootTear, s.pos, 1, 0.8 + k * 0.08);
    particle(ctx.dim, PX.debris, { x: s.pos.x, y: s.pos.y + 1, z: s.pos.z }, { size: 2.5 });
    particle(ctx.dim, PX.dust, s.pos, { size: 2 });
    quake(viewers, s.pos, 1.4, 0.7, 60);
    yield 12;
  }
  yield 30;
  fade(viewers, 0, 0, 0);
  yield 10;
  hooks.enterPhase3a();
  const players = ctx.audience();
  lockPlayers(players, false);
  titleFor(
    players,
    (p) => [tr(p, "§6PHASE 3", "§6เฟส 3"), tr(p, "§eTHE LAST MIGRATION §7— sever the 4 Anchorage Roots", "§eการอพยพครั้งสุดท้าย §7— ตัดรากยึดเกาะทั้ง 4 ราก")],
    80,
    10,
    20,
  );
}

/** The fourth root snaps (3A -> 3B): the mountain falls apart and the heart tears itself free. */
export function* mountainFalls(ctx: MMContext, hooks: Phase3Hooks): Co {
  const viewers = ctx.audience();
  const centre = { x: HX, y: D.y + 1, z: HZ };
  lockPlayers(viewers, true);
  effect(viewers, "resistance", 600, 4);
  effect(viewers, "slow_falling", 600);
  cam(viewers, { x: HX - 42, y: D.y + 28, z: HZ - 44 }, { x: HX, y: D.y + 5, z: HZ }, 0);
  titleFor(viewers, (p) => [tr(p, "§cTHE MOUNTAIN FALLS", "§cภูเขาล้มลง"), tr(p, "§7The Lithic Heart tears itself free!", "§7หัวใจศิลาฉีกตัวออกจากร่าง!")], 70, 10, 20);
  ctx.setLegPose(2);
  ctx.setPetals(3);
  sound(ctx.dim, SND.groan, centre, 1, 0.5);
  sound(ctx.dim, SND.quake, centre, 1, 0.6);
  shake(viewers, 1.4, 3.0);
  yield 30;
  sound(ctx.dim, SND.islandBreak, centre, 1, 0.8);
  yield* hooks.shatter();
  for (let i = 0; i < 200 && ctx.writer.pending > 0; i++) yield 1;
  for (let k = 0; k < 10; k++) {
    const a = ctx.rng() * Math.PI * 2;
    const r = 10 + ctx.rng() * 24;
    particle(ctx.dim, PX.debris, { x: HX + Math.cos(a) * r, y: D.y, z: HZ + Math.sin(a) * r }, { size: 3 });
  }
  hooks.removePetals();
  cam(viewers, { x: HX + 26, y: D.y + 8, z: HZ - 30 }, { x: HX, y: HOVER_Y + 2, z: HZ }, 3);
  sound(ctx.dim, SND.heartRise, centre, 1, 1);
  ctx.heartProp(PROP.phase, 3);
  const y0 = ctx.heart?.location.y ?? MM.heart.y;
  for (let t = 1; t <= 60; t++) {
    const k = t / 60;
    hooks.moveHeart(y0 + (HOVER_Y - y0) * (k * k * (3 - 2 * k)));
    if (t % 10 === 0) particle(ctx.dim, PX.shard, { x: HX, y: y0 + (HOVER_Y - y0) * k + 3, z: HZ }, { size: 1.6 });
    yield 1;
  }
  // everyone onto an island (the islands must be there first)
  const ring = ctx.islands().filter((s) => s.i > 0);
  for (const s of ring.slice(0, Math.max(1, Math.min(ring.length, viewers.length)))) yield* ctx.settleArea(Math.floor(s.cx - s.r), Math.floor(s.cz - s.r), Math.ceil(s.cx + s.r), Math.ceil(s.cz + s.r), 120);
  fade(viewers, 0.9, 0.6, 1);
  yield 8;
  const players = ctx.audience();
  players.forEach((p, i) => {
    const s = ring[i % Math.max(1, ring.length)];
    if (!s) return;
    try {
      p.teleport({ x: s.cx, y: s.top + 1.05, z: s.cz }, { facingLocation: { x: HX, y: HOVER_Y + 3, z: HZ } });
    } catch {
      /* ignore */
    }
  });
  rmEffect(players, "slow_falling");
  hooks.enterPhase3b();
  lockPlayers(players, false);
  titleFor(
    players,
    (p) => [
      tr(p, "§5THE HEART UNBOUND", "§5หัวใจหลุดจากร่าง"),
      tr(p, "§dShoot it while it hovers · strike it when it slams down", "§dยิงตอนมันลอย · ตีตอนมันกระแทกลงมา"),
    ],
    90,
    10,
    20,
  );
}

// ============================================================================ 01 Continental Fold
/** 3A: a footfall drives a glowing fault across the disk and a ridge heaves up along it. */
export function* foldStep(ctx: MMContext, target: Player): Co {
  const W = ctx.walkDir;
  const N = { x: -W.z, z: W.x };
  const R = D.outerR;
  const p = target.location;
  const s0 = (p.x - HX) * W.x + (p.z - HZ) * W.z + (ctx.rng() < 0.5 ? -2.5 : 2.5);
  const half = Math.sqrt(Math.max(0, R * R - s0 * s0));
  if (half < 6) return;
  const at = (u: number): V3 => ({ x: HX + W.x * s0 + N.x * u, y: D.y + 1.1, z: HZ + W.z * s0 + N.z * u });
  const a = at(-half);
  const b = at(half);
  const mid = at(0);
  warn(ctx.audience(), "Continental Fold", "a footfall drives a fault across the disk — get off the line!");
  sound(ctx.dim, SND.step, mid, 1, 0.6);
  sound(ctx.dim, SND.crack, mid, 1, 0.8);
  for (let t = 0; t < 36; t += 4) {
    line(ctx.dim, PX.fault, a, b, 2, { life: 0.4 });
    for (let i = 0; i < 3; i++) particle(ctx.dim, PX.crack, at((ctx.rng() * 2 - 1) * half));
    yield 4;
  }
  // the ridge: walkway cells within 1.2 blocks of the line rise 2-3 blocks
  const cells: { x: number; z: number; h: number }[] = [];
  const seen = new Set<string>();
  for (let u = -half; u <= half; u += 0.5)
    for (const off of [-1, -0.5, 0, 0.5, 1]) {
      const x = Math.floor(HX + W.x * (s0 + off) + N.x * u);
      const z = Math.floor(HZ + W.z * (s0 + off) + N.z * u);
      const k = `${x},${z}`;
      if (seen.has(k)) continue;
      seen.add(k);
      if (!ctx.isWalkway(x, z) || Math.hypot(x + 0.5 - HX, z + 0.5 - HZ) < D.periR + 1) continue;
      cells.push({ x, z, h: (x * 5 + z * 3) % 4 === 0 ? 3 : 2 });
    }
  sound(ctx.dim, SND.quake, mid, 1, 0.8);
  const hit = new Set<string>();
  for (const pl of ctx.combatants()) {
    const s = (pl.location.x - HX) * W.x + (pl.location.z - HZ) * W.z;
    if (Math.abs(s - s0) > 1.6 || Math.abs(pl.location.y - (D.y + 1)) > 2.5) continue;
    hit.add(pl.id);
    ctx.hurt(pl, 8, EntityDamageCause.entityAttack);
    const side = s >= s0 ? 1 : -1;
    try {
      pl.teleport({ x: pl.location.x + W.x * side * 2.6, y: D.y + 1.05, z: pl.location.z + W.z * side * 2.6 }, { keepVelocity: false });
    } catch {
      /* ignore */
    }
    knock(pl, W.x * side, W.z * side, 0.9, 0.6);
  }
  const placed: V3[] = [];
  for (const c of cells)
    for (let y = D.y + 1; y <= D.y + c.h; y++) {
      ctx.writer.set(c.x, y, c.z, y === D.y + c.h ? P.MOSSY_COBBLE : ctx.m.strata(c.x, y, c.z));
      placed.push({ x: c.x, y, z: c.z });
    }
  quake(ctx.audience(), mid, 1.6, 0.8, 50);
  for (let i = 0; i < 6; i++) particle(ctx.dim, PX.dust, at((ctx.rng() * 2 - 1) * half), { size: 1.8 });
  yield 150;
  sound(ctx.dim, SND.grind, mid, 0.9, 1.1);
  for (let i = placed.length - 1; i >= 0; i--) {
    ctx.writer.set(placed[i].x, placed[i].y, placed[i].z, P.AIR);
    if (i % 80 === 0) yield 1;
  }
}

/** 3B: an island cracks along a glowing fault and one half drops away for a while. */
export function* islandCrack(ctx: MMContext, target: Player): Co {
  const isl = ctx.islands();
  if (!isl.length) return;
  const s = islandAt(target.location.x, target.location.z, isl) ?? nearestIsland(isl, target.location, true);
  if (!s) return;
  const a = ctx.rng() * Math.PI;
  const n = { x: -Math.sin(a), z: Math.cos(a) };
  const side = ctx.rng() < 0.5 ? 1 : -1;
  const p0 = { x: s.cx - Math.cos(a) * s.r, y: s.top + 1.1, z: s.cz - Math.sin(a) * s.r };
  const p1 = { x: s.cx + Math.cos(a) * s.r, y: s.top + 1.1, z: s.cz + Math.sin(a) * s.r };
  warn(ctx.audience().filter((p) => Math.hypot(p.location.x - s.cx, p.location.z - s.cz) < s.r + 8), "Continental Fold", "the island cracks — get to the other half!");
  sound(ctx.dim, SND.crack, { x: s.cx, y: s.top + 1, z: s.cz }, 1, 0.8);
  for (let t = 0; t < 40; t += 4) {
    line(ctx.dim, PX.fault, p0, p1, 1.2, { life: 0.4 });
    // the half that will drop is marked
    for (let i = 0; i < 3; i++) {
      const r = ctx.rng() * s.r;
      const b = a + (Math.PI / 2) * side + (ctx.rng() - 0.5) * 2.4;
      particle(ctx.dim, PX.crack, { x: s.cx + Math.cos(b) * r, y: s.top + 1, z: s.cz + Math.sin(b) * r });
    }
    yield 4;
  }
  const filter = (x: number, z: number) => ((x + 0.5 - s.cx) * n.x + (z + 0.5 - s.cz) * n.z) * side > 0;
  clearIsland(ctx.writer, s, filter);
  sound(ctx.dim, SND.islandBreak, { x: s.cx, y: s.top, z: s.cz }, 1, 1.1);
  particle(ctx.dim, PX.debris, { x: s.cx, y: s.top - 1, z: s.cz }, { size: 3 });
  yield 160;
  writeIsland(ctx.writer, s, filter);
  sound(ctx.dim, SND.grind, { x: s.cx, y: s.top, z: s.cz }, 0.9, 1.2);
}

function nearestIsland(isl: Island[], at: V3, ringOnly: boolean): Island | undefined {
  let best: Island | undefined;
  let bd = 1e9;
  for (const s of isl) {
    if (ringOnly && s.i === 0) continue;
    const d = Math.hypot(at.x - s.cx, at.z - s.cz);
    if (d < bd) {
      bd = d;
      best = s;
    }
  }
  return best;
}

// ============================================================================ 02 Lithic Peristalsis
/**
 * 3A: the march - rolling ridges cross the whole disk in the walking direction (the gait itself sends a
 * light one every few steps; as an ability it sends a volley). Jump each crest.
 */
export function* marchWave(ctx: MMContext, fronts: number, damage: number, announce = true): Co {
  const W = ctx.walkDir;
  const N = { x: -W.z, z: W.x };
  const R = D.outerR;
  const centre = { x: HX, y: D.y + 1, z: HZ };
  if (announce) warn(ctx.audience(), "Lithic Peristalsis", "the march quakes the disk — jump each wave!");
  const live: { s: number; hit: Set<string>; placed: V3[] }[] = [];
  let started = 0;
  let t = 0;
  while (started < fronts || live.some((f) => f.s < R + 1)) {
    if (started < fronts && t === started * 22) {
      live.push({ s: -R - 1, hit: new Set(), placed: [] });
      sound(ctx.dim, SND.wave, centre, 1, 0.75 + started * 0.08);
      started++;
    }
    for (const f of live) {
      if (f.s >= R + 1) continue;
      for (const q of f.placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
      f.placed = [];
      f.s += 0.5;
      if (f.s >= R + 1) continue;
      const half = Math.sqrt(Math.max(0, R * R - f.s * f.s));
      const seen = new Set<string>();
      for (let u = -half; u <= half; u += 0.8) {
        const x = Math.floor(HX + W.x * f.s + N.x * u);
        const z = Math.floor(HZ + W.z * f.s + N.z * u);
        const k = `${x},${z}`;
        if (seen.has(k)) continue;
        seen.add(k);
        if (!ctx.isWalkway(x, z) || Math.hypot(x + 0.5 - HX, z + 0.5 - HZ) < D.periR) continue;
        ctx.writer.set(x, D.y + 1, z, (x + z) % 3 === 0 ? P.VEIN_GLOW : P.MUSCLE);
        f.placed.push({ x, y: D.y + 1, z });
      }
      if (t % 4 === 0) {
        const u = (ctx.rng() * 2 - 1) * half;
        particle(ctx.dim, PX.dust, { x: HX + W.x * f.s + N.x * u, y: D.y + 1.5, z: HZ + W.z * f.s + N.z * u }, { size: 0.9 });
      }
      for (const pl of ctx.combatants()) {
        if (f.hit.has(pl.id)) continue;
        const s = (pl.location.x - HX) * W.x + (pl.location.z - HZ) * W.z;
        if (Math.abs(s - f.s) > 0.9 || Math.abs(pl.location.y - (D.y + 1)) > 2) continue;
        f.hit.add(pl.id);
        if (pl.isOnGround) {
          ctx.hurt(pl, damage, EntityDamageCause.entityAttack);
          knock(pl, W.x, W.z, 0.7, 0.45);
        } else pl.onScreenDisplay.setActionBar(tr(pl, "§aYou leapt the wave!", "§aกระโดดข้ามคลื่นได้!"));
      }
    }
    t++;
    yield 1;
  }
  for (const f of live) for (const q of f.placed) ctx.writer.set(q.x, q.y, q.z, P.AIR);
}

/** 3B: shockwave rings from the centre island (the heart's slam; also the ability's form). */
export function* slamRings(ctx: MMContext, rings: number, announce = false): Co {
  const centre = { x: HX, y: D.y + 1, z: HZ };
  if (announce) warn(ctx.audience(), "Lithic Peristalsis", "shockwaves roll across the islands — jump them!");
  const live: { r: number; hit: Set<string> }[] = [];
  let started = 0;
  let t = 0;
  while (started < rings || live.some((w) => w.r < 25)) {
    if (started < rings && t === started * 16) {
      live.push({ r: 3, hit: new Set() });
      sound(ctx.dim, SND.wave, centre, 1, 0.7 + started * 0.1);
      started++;
    }
    for (const w of live) {
      if (w.r >= 25) continue;
      w.r += 0.6;
      if (t % 2 === 0)
        for (let i = 0; i < 18; i++) {
          const a = (i / 18) * Math.PI * 2 + t * 0.02;
          const x = HX + Math.cos(a) * w.r;
          const z = HZ + Math.sin(a) * w.r;
          const s = islandAt(x, z, ctx.islands());
          if (s) particle(ctx.dim, PX.dust, { x, y: s.top + 1.2, z }, { size: 0.7 });
        }
      for (const pl of ctx.combatants()) {
        if (w.hit.has(pl.id)) continue;
        const r = Math.hypot(pl.location.x - HX, pl.location.z - HZ);
        if (Math.abs(r - w.r) > 0.8 || pl.location.y < D.y - 3 || pl.location.y > D.y + 5) continue;
        w.hit.add(pl.id);
        if (pl.isOnGround) {
          ctx.hurt(pl, 6, EntityDamageCause.entityAttack);
          knock(pl, pl.location.x - HX, pl.location.z - HZ, 0.8, 0.4);
        } else pl.onScreenDisplay.setActionBar(tr(pl, "§aYou leapt the shockwave!", "§aกระโดดข้ามคลื่นกระแทกได้!"));
      }
    }
    t++;
    yield 1;
  }
}

// ============================================================================ 04 Resonance Network
/** 3B: the broken network flows through the heart's mineral veins - molten beams sweep across the islands. */
export function* mineralBeams(ctx: MMContext, target: Player): Co {
  const beams = ctx.enraged() ? 3 : 2;
  ctx.heartProp(PROP.charging, true);
  warn(ctx.audience(), "Resonance Network", "the heart channels molten mineral — leave the glowing arc!");
  try {
    for (let b = 0; b < beams; b++) {
      const start = Math.atan2(target.location.z - HZ, target.location.x - HX) / RAD + (ctx.rng() - 0.5) * 50;
      const dir = ctx.rng() < 0.5 ? 1 : -1;
      const sweep = 110;
      const hp = () => ctx.heart?.location ?? { x: HX, y: (ctx.heart ? ctx.heart.location.y : HOVER_Y), z: HZ };
      sound(ctx.dim, SND.beamCharge, hp(), 1, 1);
      for (let t = 0; t < 30; t += 3) {
        for (let a = 0; a <= sweep; a += 10) {
          const ang = (start + dir * a) * RAD;
          for (const r of [9, 15, 21]) {
            const x = HX + Math.cos(ang) * r;
            const z = HZ + Math.sin(ang) * r;
            const s = islandAt(x, z, ctx.islands());
            if (s) particle(ctx.dim, PX.fault, { x, y: s.top + 1.1, z }, { life: 0.35 });
          }
        }
        yield 3;
      }
      sound(ctx.dim, SND.beamFire, hp(), 1, 1);
      const hit = new Set<string>();
      for (let t = 0; t <= 44; t++) {
        const ang = start + dir * sweep * (t / 44);
        const h = hp();
        const from = { x: h.x, y: h.y + 3, z: h.z };
        const to = { x: HX + Math.cos(ang * RAD) * 24, y: D.y + 1, z: HZ + Math.sin(ang * RAD) * 24 };
        if (t % 2 === 0) {
          const v = { x: to.x - from.x, y: to.y - from.y, z: to.z - from.z };
          const L = Math.hypot(v.x, v.y, v.z) || 1;
          line(ctx.dim, PX.mineralBeam, from, to, 2.4, { dir: { x: v.x / L, y: v.y / L, z: v.z / L }, speed: 3 });
        }
        for (const pl of ctx.combatants()) {
          if (hit.has(pl.id)) continue;
          const r = Math.hypot(pl.location.x - HX, pl.location.z - HZ);
          if (r < 2.5 || r > 26 || pl.location.y < D.y - 4) continue;
          const pa = Math.atan2(pl.location.z - HZ, pl.location.x - HX) / RAD;
          if (Math.abs(angleDiffDeg(pa, ang)) > 6) continue;
          hit.add(pl.id);
          ctx.hurt(pl, 7, EntityDamageCause.fire);
          try {
            pl.setOnFire(3, true);
          } catch {
            /* ignore */
          }
        }
        yield 1;
      }
      yield 20;
    }
  } finally {
    ctx.heartProp(PROP.charging, false);
  }
}

// ============================================================================ 05 Inverted Strata
/** 3B: an island's rim glows, then it turns over and is gone for a while. */
export function* islandFlip(ctx: MMContext, target: Player): Co {
  const isl = ctx.islands();
  const under = islandAt(target.location.x, target.location.z, isl);
  const s = under && under.i > 0 ? under : nearestIsland(isl, target.location, true);
  if (!s) return;
  warn(ctx.audience().filter((p) => Math.hypot(p.location.x - s.cx, p.location.z - s.cz) < s.r + 8), "Inverted Strata", "this island is turning over — jump off it!");
  sound(ctx.dim, SND.grind, { x: s.cx, y: s.top + 1, z: s.cz }, 1, 0.8);
  for (let t = 0; t < 44; t += 4) {
    for (let i = 0; i < 14; i++) {
      const a = (i / 14) * Math.PI * 2 + t * 0.05;
      particle(ctx.dim, PX.target, { x: s.cx + Math.cos(a) * (s.r - 0.5), y: s.top + 1.05, z: s.cz + Math.sin(a) * (s.r - 0.5) }, { radius: 0.6, life: 0.4 });
    }
    yield 4;
  }
  clearIsland(ctx.writer, s);
  sound(ctx.dim, SND.islandBreak, { x: s.cx, y: s.top, z: s.cz }, 1, 0.9);
  particle(ctx.dim, PX.debris, { x: s.cx, y: s.top, z: s.cz }, { size: 3.5 });
  quake(ctx.audience(), { x: s.cx, y: s.top, z: s.cz }, 1.0, 0.6, 30);
  yield 120;
  writeIsland(ctx.writer, s);
  sound(ctx.dim, SND.grind, { x: s.cx, y: s.top, z: s.cz }, 0.9, 1.3);
}

// ============================================================================ 06 Mantle Contraction
/** 3B: the heart drags everything toward itself, then throws it back out. */
export function* heartPull(ctx: MMContext): Co {
  const centre = { x: HX, y: D.y + 1, z: HZ };
  warn(ctx.audience(), "Mantle Contraction", "the heart drags you in — hold your ground, then brace!");
  sound(ctx.dim, SND.contract, centre, 1, 0.8);
  for (let t = 0; t < 80; t += 5) {
    for (const pl of ctx.combatants()) {
      const dx = HX - pl.location.x;
      const dz = HZ - pl.location.z;
      if (Math.hypot(dx, dz) < 3) continue;
      knock(pl, dx, dz, 0.3, 0.02);
    }
    for (let i = 0; i < 8; i++) {
      const a = ctx.rng() * Math.PI * 2;
      const r = 6 + ctx.rng() * 18;
      particle(ctx.dim, PX.dust, { x: HX + Math.cos(a) * r, y: D.y + 1.5, z: HZ + Math.sin(a) * r }, { size: 0.8 });
    }
    yield 5;
  }
  sound(ctx.dim, SND.quake, centre, 1, 0.9);
  quake(ctx.audience(), centre, 1.6, 0.6, 40);
  for (const pl of ctx.combatants()) {
    const dx = pl.location.x - HX;
    const dz = pl.location.z - HZ;
    const r = Math.hypot(dx, dz);
    if (r > 30) continue;
    if (r < 6) ctx.hurt(pl, 5, EntityDamageCause.entityAttack);
    knock(pl, dx || 1, dz, 0.9, 0.4);
  }
}
