/**
 * 07 THE GREAT UNFOLDING — the transition into Phase 2 (and the mid-fight
 * re-bloom), plus the victory sequence.
 */
import { EasingType, Entity, EntityDamageCause, HudVisibility, InputPermissionCategory, Player } from "@minecraft/server";
import { knock } from "../../core/arena.js";
import { particle, quake, shake, sound, title } from "../../core/fx.js";
import { Co } from "../../core/tasks.js";
import { V3 } from "../../core/vec.js";
import { MM } from "../../gen/mountain.js";
import { MMContext } from "./context.js";
import { ANIM, ENT, PROP, PX, SND } from "./ids.js";
import { cutColumns, sectorColumns, placeDisk, writeDisk } from "./runtime.js";

const D = MM.disk;
const HX = MM.heart.x;
const HZ = MM.heart.z;
export const PETALS = 12;

export function petalSite(k: number): { pos: V3; yaw: number; angle: number } {
  const ang = ((15 + (360 / PETALS) * k) * Math.PI) / 180;
  const pos = { x: HX + Math.cos(ang) * MM.A * 0.8, y: MM.disk.y - 3, z: HZ + Math.sin(ang) * MM.B * 0.8 };
  // the model's front (-Z) faces the heart
  const fx = HX - pos.x;
  const fz = HZ - pos.z;
  const yaw = (Math.atan2(-fx, fz) * 180) / Math.PI;
  return { pos, yaw, angle: (ang * 180) / Math.PI };
}

export function spawnPetal(ctx: MMContext, k: number, state: number): Entity | undefined {
  const s = petalSite(k);
  try {
    const e = ctx.dim.spawnEntity(ENT.petal, s.pos, { initialRotation: s.yaw });
    e.setProperty(PROP.petalIndex, k);
    e.setProperty(PROP.petalState, state);
    e.addTag("anatomy_mm");
    return e;
  } catch (err) {
    console.warn(`[anatomy] petal ${k} spawn failed: ${String(err)}`);
    return undefined;
  }
}

/** Rim spots on the outer ring where players land in Phase 2. */
export function ringSpot(i: number, n: number): { pos: V3; facing: V3 } {
  const a = (i / Math.max(1, n)) * Math.PI * 2 + Math.PI * 1.5;
  const r = D.outerR - 1.5;
  return { pos: { x: HX + Math.cos(a) * r, y: D.y + 1.05, z: HZ + Math.sin(a) * r }, facing: { x: HX, y: D.y + 3, z: HZ } };
}

interface Hooks {
  setPhase(p: 2): void;
  addPetal(e: Entity): void;
  setLayout(l: number): void;
  onFinished(): void;
}

function lockPlayers(players: Player[], locked: boolean): void {
  for (const p of players) {
    try {
      p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, !locked);
      p.inputPermissions.setPermissionCategory(InputPermissionCategory.Jump, !locked);
      p.onScreenDisplay.setHudVisibility(locked ? HudVisibility.Hide : HudVisibility.Reset);
      if (!locked) p.camera.clear();
    } catch {
      /* ignore */
    }
  }
}

function cam(players: Player[], at: V3, look: V3, ease: number): void {
  for (const p of players) {
    try {
      p.camera.setCamera("minecraft:free", ease > 0 ? { location: at, facingLocation: look, easeOptions: { easeTime: ease, easeType: EasingType.InOutSine } } : { location: at, facingLocation: look });
    } catch {
      /* ignore */
    }
  }
}

export function* greatUnfolding(ctx: MMContext, hooks: Hooks): Co {
  const viewers = ctx.audience();
  const heartPos = { x: HX, y: (ctx.heart?.location.y ?? 148) + 3, z: HZ };
  // everyone is pulled to the arrival shelf to watch the body open
  for (const p of viewers) {
    try {
      p.camera.fade({ fadeColor: { red: 0.95, green: 0.9, blue: 1 }, fadeTime: { fadeInTime: 0.4, holdTime: 0.6, fadeOutTime: 1.0 } });
    } catch {
      /* ignore */
    }
  }
  yield 10;
  ctx.terrain.resetAll();
  const ar = MM.arrival;
  viewers.forEach((p, i) => {
    try {
      p.teleport({ x: ar.x + Math.cos(i) * 3, y: ar.y + 1.05, z: ar.z + Math.sin(i) * 3 }, { facingLocation: heartPos });
      p.addEffect("resistance", 600, { amplifier: 4, showParticles: false });
    } catch {
      /* ignore */
    }
  });
  lockPlayers(viewers, true);
  cam(viewers, { x: -70, y: 168, z: -108 }, { x: 0, y: 150, z: 0 }, 0);
  title(viewers, "§d07 · THE GREAT UNFOLDING", "§7The resonance is broken. The mountain opens itself.", 70, 10, 20);
  sound(ctx.dim, SND.groan, heartPos, 1, 0.7);
  for (const e of ctx.legs)
    try {
      e.playAnimation(ANIM.legFlinch, { blendOutTime: 0.4 });
    } catch {
      /* ignore */
    }
  shake(viewers, 0.6, 2.0);
  yield 30;
  cam(viewers, { x: -104, y: 192, z: -30 }, { x: 0, y: 150, z: 0 }, 6);
  // let the terrain settle before cutting it open
  for (let i = 0; i < 40 && ctx.writer.pending > 0; i++) yield 1;
  ctx.terrain.enabled = false;

  // peel the shell sector by sector; each sector becomes a petal that swings outward
  const sectors = sectorColumns(PETALS, 0);
  const petals: Entity[] = [];
  for (let k = 0; k < PETALS; k++) {
    const e = spawnPetal(ctx, k, 0);
    if (e) {
      petals.push(e);
      hooks.addPetal(e);
    }
    cutColumns(ctx.dim, ctx.writer, sectors[k]);
    const s = petalSite(k);
    particle(ctx.dim, PX.dust, { x: s.pos.x, y: s.pos.y + 14, z: s.pos.z }, { size: 2.2 });
    particle(ctx.dim, PX.debris, { x: (s.pos.x + HX) / 2, y: s.pos.y + 20, z: (s.pos.z + HZ) / 2 }, { size: 3 });
    if (k % 3 === 0) sound(ctx.dim, SND.unfold, s.pos, 1, 0.8 + k * 0.03);
    else sound(ctx.dim, SND.crack, s.pos, 1, 0.7);
    yield 2;
    if (e?.isValid) e.setProperty(PROP.petalState, 1);
    quake(viewers, s.pos, 1.1, 0.6, 140);
    if (k === 4) cam(viewers, { x: -40, y: 205, z: 86 }, { x: 0, y: 150, z: 0 }, 6);
    yield 8;
  }
  sound(ctx.dim, SND.rumble, heartPos, 1, 0.8);
  // the heart chamber floor reassembles as the Unfolded World
  while (ctx.writer.pending > 0) yield 1;
  placeDisk(ctx.dim, ctx.writer, 0, 2.5);
  hooks.setLayout(0);
  for (const e of ctx.legs) if (e.isValid) e.setProperty(PROP.pose, 1);
  cam(viewers, { x: -22, y: 166, z: -34 }, { x: HX, y: heartPos.y, z: HZ }, 5);
  yield 50;
  if (ctx.heart?.isValid) {
    ctx.heart.setProperty(PROP.phase, 2);
    ctx.heart.setProperty(PROP.open, true);
  }
  particle(ctx.dim, PX.shield, heartPos, { radius: 4 });
  particle(ctx.dim, PX.shard, heartPos, { size: 3 });
  sound(ctx.dim, SND.shatter, heartPos, 1, 1.3);
  sound(ctx.dim, SND.heartbeat, heartPos, 1, 1);
  yield 50;
  if (ctx.heart?.isValid) ctx.heart.setProperty(PROP.open, false);
  sound(ctx.dim, SND.heartClose, heartPos, 1, 1);
  for (const p of viewers)
    try {
      p.camera.fade({ fadeColor: { red: 0, green: 0, blue: 0 }, fadeTime: { fadeInTime: 0.5, holdTime: 0.4, fadeOutTime: 0.8 } });
    } catch {
      /* ignore */
    }
  yield 10;
  hooks.setPhase(2);
  const players = ctx.audience();
  players.forEach((p, i) => {
    const s = ringSpot(i, players.length);
    try {
      p.teleport(s.pos, { facingLocation: s.facing });
    } catch {
      /* ignore */
    }
  });
  lockPlayers(players, false);
  title(players, "§5PHASE 2", "§dTHE UNFOLDED WORLD §7— strike the Lithic Heart when its iris opens", 80, 10, 20);
  hooks.onFinished();
}

/** Phase 2 at half health: the petals slam shut and the rib layout re-blooms rotated. */
export function* rebloom(ctx: MMContext, hooks: Hooks): Co {
  const centre = { x: HX, y: D.y + 1, z: HZ };
  title(ctx.audience(), "", "§c⚠ The world refolds §7— stay on the heart's rings!", 50, 6, 12);
  sound(ctx.dim, SND.warn, centre, 1, 0.7);
  sound(ctx.dim, SND.groan, centre, 1, 0.9);
  for (let t = 0; t < 60; t += 5) {
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      particle(ctx.dim, PX.safe, { x: HX + Math.cos(a) * 6.5, y: D.y + 1, z: HZ + Math.sin(a) * 6.5 }, { radius: 0.6 });
      particle(ctx.dim, PX.safe, { x: HX + Math.cos(a) * 19, y: D.y + 1, z: HZ + Math.sin(a) * 19 }, { radius: 0.6 });
    }
    yield 5;
  }
  for (const e of ctx.petals) if (e.isValid) e.setProperty(PROP.petalState, 2);
  yield 20;
  sound(ctx.dim, SND.quake, centre, 1, 0.6);
  quake(ctx.audience(), centre, 2.5, 1.0, 80);
  for (const p of ctx.combatants()) {
    const r = Math.hypot(p.location.x - HX, p.location.z - HZ);
    if (r > 24 && p.location.y > D.mantleY) {
      ctx.hurt(p, 10, EntityDamageCause.entityAttack);
      knock(p, HX - p.location.x, HZ - p.location.z, 1.2, 0.5);
    }
  }
  // rewrite the ribs in the rotated layout
  const next = ctx.layout ? 0 : 1;
  writeDisk(ctx.writer, next, (x, y) => y >= D.y - 3);
  hooks.setLayout(next);
  yield 60;
  for (const e of ctx.petals) if (e.isValid) e.setProperty(PROP.petalState, 1);
  sound(ctx.dim, SND.unfold, centre, 1, 1.2);
  ctx.exposeHeart(130);
  hooks.onFinished();
}

export function* victorySequence(ctx: MMContext, onLoot: () => void): Co {
  const h = ctx.heart;
  const at = { x: HX, y: (h?.location.y ?? 148) + 3, z: HZ };
  if (h?.isValid) {
    h.setProperty(PROP.open, true);
    h.setProperty(PROP.dying, true);
  }
  const everyone = ctx.audience();
  title(everyone, "§dTHE MOUNTAIN SETTLES", "§7Specimen 001 — dissected", 90, 10, 30);
  sound(ctx.dim, SND.heartbeat, at, 1, 0.8);
  for (const p of everyone)
    try {
      p.playMusic("anatomy.music.mm_victory", { fade: 1.5, loop: false, volume: 0.9 });
    } catch {
      /* ignore */
    }
  for (let t = 0; t < 60; t += 6) {
    particle(ctx.dim, PX.shard, at, { size: 1.2 + t / 30 });
    shake(everyone, 0.3 + t / 120, 0.4);
    yield 6;
  }
  sound(ctx.dim, SND.shatter, at, 1, 0.9);
  particle(ctx.dim, PX.shard, at, { size: 5 });
  particle(ctx.dim, PX.dust, at, { size: 3 });
  quake(everyone, at, 3, 1.5, 120);
  for (const e of ctx.legs) if (e.isValid) e.setProperty(PROP.pose, 2);
  for (const e of ctx.petals) if (e.isValid) e.setProperty(PROP.petalState, 3);
  yield 30;
  onLoot();
  yield 60;
  if (h?.isValid) h.remove();
}
