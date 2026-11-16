import { Entity, EntityDamageCause, Player, Vector3 } from "@minecraft/server";
import { CANE, ID, SIG } from "../config.js";
import { pose, signal } from "../core/anim.js";
import { focusFov, fx, fxFor, Rgba, segment, shake, slashArc, sound, soundTo } from "../core/fx.js";
import { swapHeld, wear } from "../core/items.js";
import { hint, now, PlayerState, ready, remaining, startCd, stateOf } from "../core/state.js";
import { alive, armorOf, canHurt, centerOf, constitutionOf, widthOf } from "../core/targets.js";
import { add, clamp, dist, flat, lerp, norm, pointSegment, rightOf, scale, sub, v } from "../core/vec.js";
import { bleedingStacks, hemorrhage, spray, wound } from "../systems/bleed.js";
import { CutInfo, cutMultiplier, scriptDamage } from "../systems/damage.js";
import { secs } from "./goggles.js";

const DANGER = new Set(["minecraft:lava", "minecraft:flowing_lava", "minecraft:magma", "minecraft:fire", "minecraft:soul_fire",
  "minecraft:cactus", "minecraft:campfire", "minecraft:soul_campfire", "minecraft:sweet_berry_bush", "minecraft:powder_snow",
  "minecraft:wither_rose", "minecraft:pointed_dripstone"]);

const bladePoint = (p: Player): Vector3 => {
  const dir = p.getViewDirection();
  return add(add(add(p.getHeadLocation(), scale(dir, 1.1)), scale(rightOf(dir), 0.35)), v(0, -0.25, 0));
};

// ------------------------------------------------------------------ use events

export function startUse(p: Player, s: PlayerState, item: string): void {
  const c = s.cane;
  if (item === ID.cane) {
    if (!ready(s, "iai")) {
      c.gripping = false;
      return void hint(s, `§fIai§7 - breath not yet steady (${secs(remaining(s, "iai"))})`);
    }
    c.gripping = true;
    c.gripStart = now();
    c.glintShown = false;
    pose(p, "cane_grip", true);
    sound(p.dimension, "oddworks.cane.grip", p.location, 1.0, 0.7);
    focusFov(p, true, 64);
    return;
  }
  // drawn blade
  if (c.notoAt >= 0) return;
  if (p.isSneaking) return noto(p, s);
  if (!ready(s, "deflect")) return void hint(s, `§bDeflect§7 ${secs(remaining(s, "deflect"))}`);
  c.deflectStart = now();
  c.deflectUntil = now() + CANE.deflectWindow;
  c.deflected = false;
  signal(p, SIG.caneDeflect, CANE.deflectWindow);
  pose(p, "deflect");
  sound(p.dimension, "oddworks.cane.swish", p.location, 1.3, 0.6);
}

export function release(p: Player, s: PlayerState, item: string): void {
  const c = s.cane;
  if (item !== ID.cane || !c.gripping) return;
  c.gripping = false;
  focusFov(p, false);
  iai(p, s, now() - c.gripStart);
}

export function stopUse(p: Player, s: PlayerState): void {
  if (s.cane.gripping) {
    s.cane.gripping = false;
    focusFov(p, false);
  }
}

// ------------------------------------------------------------------ per tick while held

export function tickHeld(p: Player, s: PlayerState, item: string, using: boolean): void {
  const c = s.cane;
  const t = now();
  if (item === ID.cane && c.gripping) {
    if (!using) {
      c.gripping = false;
      focusFov(p, false);
      return;
    }
    const held = t - c.gripStart;
    const focus = Math.min(1, held / CANE.gripFull);
    if (held === CANE.perfectFrom) {
      soundTo(p, "oddworks.cane.glint", 1.0, 0.9);
      sound(p.dimension, "oddworks.cane.glint", p.location, 1.0, 0.35);
      fxFor(p, "oddworks:vital_glint", bladePoint(p), { size: 0.8 });
      c.glintShown = true;
    }
    if (held % 10 === 0) fx(p.dimension, "oddworks:focus_ring", add(p.location, v(0, 0.08, 0)));
    const n = Math.round(focus * 8);
    const perfect = held >= CANE.perfectFrom && held <= CANE.perfectTo;
    hint(s, `§fFocus ${perfect ? "§e§l" : "§b"}${"|".repeat(n)}§r§8${"|".repeat(8 - n)}§r ${perfect ? "§e§lNOW!" : held > CANE.perfectTo ? "§7past the glint" : "§7wait for the glint"}`, 4);
    return;
  }
  if (item === ID.caneDrawn) {
    // light stance: the slender blade keeps you quick on your feet
    if (t % 20 === 0) {
      try {
        p.addEffect("speed", 30, { amplifier: 0, showParticles: false });
      } catch {
        /* ignore */
      }
    }
    if (c.deflectStart >= 0 && t > c.deflectUntil) {
      if (!c.deflected) startCd(s, "deflect", CANE.deflectCooldownWhiff);
      c.deflectStart = -100;
    }
    if (c.notoAt >= 0) tickNoto(p, s);
  }
}

// ------------------------------------------------------------------ skill 1: Iai (drawing cut)

function dashPath(p: Player, maxDist: number): { start: Vector3; end: Vector3; dist: number } {
  const dim = p.dimension;
  const dir = flat(p.getViewDirection());
  const start = p.location;
  let limit = maxDist;
  for (const h of [0.2, 1.0, 1.7]) {
    try {
      const hit = dim.getBlockFromRay(add(start, v(0, h, 0)), dir, { maxDistance: maxDist + 0.5, includePassableBlocks: false, includeLiquidBlocks: false });
      if (hit) limit = Math.min(limit, dist(add(start, v(0, h, 0)), add(hit.block.location, hit.faceLocation)) - 0.45);
    } catch {
      /* ignore */
    }
  }
  let travelled = 0;
  let pos = start;
  for (let d = 0.25; d <= limit; d += 0.25) {
    const next = add(start, scale(dir, d));
    let ground;
    try {
      ground = dim.getBlockBelow(add(next, v(0, 0.3, 0)), { maxDistance: 3.4 });
    } catch {
      ground = undefined;
    }
    if (!ground || DANGER.has(ground.typeId)) break; // never dash off a cliff or into lava / cactus
    try {
      const feet = dim.getBlock(next);
      if (feet && (DANGER.has(feet.typeId) || feet.isLiquid)) break;
    } catch {
      break;
    }
    pos = next;
    travelled = d;
  }
  return { start, end: pos, dist: travelled };
}

function iai(p: Player, s: PlayerState, held: number): void {
  const dim = p.dimension;
  const t = now();
  if (!swapHeld(p, ID.cane, ID.caneDrawn)) return;
  signal(p, SIG.caneDraw, 7);
  sound(dim, "oddworks.cane.draw", p.location, 1.0);
  if (held < 3) {
    // quick draw, no cut
    startCd(s, "iai", 20);
    return void hint(s, "§7Blade drawn", 20);
  }
  const focus = Math.min(1, held / CANE.gripFull);
  const perfect = held >= CANE.perfectFrom && held <= CANE.perfectTo;
  const maxDist = perfect ? CANE.dashPerfect : CANE.dashBase + CANE.dashPerFocus * focus;
  const path = dashPath(p, maxDist);
  const dir = flat(p.getViewDirection());
  if (path.dist > 0.3) {
    try {
      p.teleport(path.end, { keepVelocity: false, checkForBlocks: true });
    } catch {
      /* stay */
    }
  }
  const a = add(path.start, v(0, 1, 0));
  const b = add(path.end, v(0, 1, 0));
  segment(dim, "oddworks:iai_streak", a, b);
  const right = rightOf(dir);
  const mid = lerp(a, b, 0.75);
  slashArc(dim, add(mid, scale(dir, 0.6)), scale(right, -1), dir, 1.6, -0.35 * Math.PI, 0.35 * Math.PI, 8, perfect ? 1.4 : 1.0);
  sound(dim, "oddworks.cane.slash", b, perfect ? 0.85 : 1.05);
  shake(p, perfect ? 0.12 : 0.06, 0.2);
  pose(p, "iai_cut");
  const dmgBase = (CANE.iaiDamageBase + CANE.iaiDamagePerFocus * focus) * (perfect ? 1.5 : 1);
  let cut = 0;
  try {
    const span = dist(a, b) / 2 + 2.5;
    for (const e of dim.getEntities({ location: lerp(a, b, 0.5), maxDistance: span })) {
      if (!canHurt(p, e, true)) continue;
      const ps = pointSegment(centerOf(e), a, add(b, scale(dir, 1.2)));
      if (ps.d > 1.3 + widthOf(e) / 2) continue;
      armorOf(e, t);
      const info = cutMultiplier(p, e, perfect, perfect ? 0.4 : 0);
      scriptDamage(e, dmgBase * info.mult, EntityDamageCause.entityAttack, p);
      afterCut(p, s, e, info, 1 + (perfect ? 2 : 0), norm(sub(centerOf(e), a)));
      cut++;
    }
  } catch {
    /* ignore */
  }
  if (perfect) {
    fx(dim, "oddworks:vital_glint", b, { size: 1.6 });
    sound(dim, "oddworks.cane.glint", b, 0.8, 0.8);
  }
  startCd(s, "iai", perfect ? CANE.iaiCooldownPerfect : CANE.iaiCooldown);
  hint(s, `${perfect ? "§e§lCLEAN DRAW§r " : "§fIai "}§7${cut ? `cut ${cut}` : "cut the air"}`, 40);
}

// ------------------------------------------------------------------ cuts, bleeding and the edge vs armour

function afterCut(p: Player, s: PlayerState, target: Entity, info: CutInfo, woundsWanted: number, dir: Vector3): void {
  if (!alive(target)) return;
  const con = constitutionOf(target);
  const chance = clamp(1 - info.armorPoints / 24, 0.1, 1);
  const opened = wound(target, p, woundsWanted + (info.vital ? 1 : 0), chance);
  const c = centerOf(target);
  if (con.bleed > 0 && opened > 0) {
    spray(target, con.color, 4 + opened * 3, add(dir, v(0, 0.5, 0)), 1);
    s.cane.lastBlood = { r: con.color.r, g: con.color.g, b: con.color.b };
  }
  const glances = con.metal || info.armorFactor < 0.55;
  if (glances || con.bleed === 0) {
    fx(target.dimension, "oddworks:clang_spark", c, { count: glances ? 10 : 5 });
    sound(target.dimension, "oddworks.cane.clang", c, glances ? 0.9 + Math.random() * 0.2 : 1.3, glances ? 0.9 : 0.5);
    if (glances) wear(p, CANE.wearClang);
    hint(s, con.bleed === 0 ? `§7${con.kind}: §8nothing to bleed` : "§7The edge glances off the armour", 30);
  }
  if (info.vital) {
    fx(target.dimension, "oddworks:vital_glint", target.getHeadLocation(), { size: 1 });
    soundTo(p, "oddworks.cane.glint", 1.3, 0.5);
  }
}

/** Damage-pipeline hook: a drawn-blade melee hit landed. */
export function onCut(p: Player, target: Entity, info: CutInfo): void {
  if (!alive(target) || !alive(p)) return;
  armorOf(target, now());
  afterCut(p, stateOf(p), target, info, 1, norm(sub(centerOf(target), p.getHeadLocation())));
}

// ------------------------------------------------------------------ skill 2: Kaeshi (deflect + riposte)

export function deflectWindow(p: Player): { active: boolean; start: number } {
  const c = stateOf(p).cane;
  return { active: c.deflectStart >= 0 && now() <= c.deflectUntil, start: c.deflectStart };
}

export function onDeflect(p: Player, attacker: Entity | undefined, projectile: Entity | undefined, perfect: boolean): void {
  if (!alive(p)) return;
  const s = stateOf(p);
  const c = s.cane;
  c.deflected = true;
  startCd(s, "deflect", CANE.deflectCooldownHit);
  const from = projectile && alive(projectile) ? projectile.location : attacker && alive(attacker) ? centerOf(attacker) : add(p.location, v(0, 1.2, 0));
  const contact = lerp(add(p.location, v(0, 1.3, 0)), from, 0.35);
  fx(p.dimension, "oddworks:deflect_flash", contact);
  fx(p.dimension, "oddworks:clang_spark", contact, { count: perfect ? 16 : 10 });
  sound(p.dimension, "oddworks.cane.deflect", contact, perfect ? 1.15 : 1.0);
  shake(p, 0.08, 0.15);
  if (projectile && alive(projectile)) {
    try {
      projectile.remove(); // cut out of the air
    } catch {
      /* ignore */
    }
  }
  if (attacker && alive(attacker) && !projectile && dist(attacker.location, p.location) < 4.5 && canHurt(p, attacker, false)) {
    armorOf(attacker, now());
    const info = cutMultiplier(p, attacker, true, 0.6);
    scriptDamage(attacker, (CANE.ripostDamage + (perfect ? 3 : 0)) * info.mult, EntityDamageCause.entityAttack, p);
    afterCut(p, s, attacker, info, 2 + (perfect ? 1 : 0), norm(sub(centerOf(attacker), p.location)));
    try {
      const away = flat(sub(attacker.location, p.location));
      attacker.applyKnockback({ x: away.x * 0.5, z: away.z * 0.5 }, 0.25);
      attacker.addEffect("slowness", 20, { amplifier: 2, showParticles: false });
    } catch {
      /* ignore */
    }
    const dir = p.getViewDirection();
    slashArc(p.dimension, add(contact, scale(dir, 0.4)), rightOf(dir), v(0, 1, 0), 0.9, -0.4 * Math.PI, 0.4 * Math.PI, 6, 0.8);
  }
  hint(s, perfect ? "§b§lPERFECT DEFLECT §r§7- riposte" : projectile ? "§bDeflected §7- cut from the air" : "§bDeflected §7- riposte", 40);
}

export function onHeavyBlow(p: Player, attacker: Entity): void {
  if (!alive(p) || !alive(attacker)) return;
  const s = stateOf(p);
  s.cane.deflected = true;
  startCd(s, "deflect", CANE.deflectCooldownWhiff);
  const contact = lerp(add(p.location, v(0, 1.3, 0)), centerOf(attacker), 0.35);
  fx(p.dimension, "oddworks:clang_spark", contact, { count: 18 });
  sound(p.dimension, "oddworks.cane.clang", contact, 0.7, 1.0);
  shake(p, 0.2, 0.3);
  wear(p, CANE.wearHeavyBlock);
  try {
    const away = flat(sub(p.location, attacker.location));
    p.applyKnockback({ x: away.x * 0.9, z: away.z * 0.9 }, 0.3);
  } catch {
    /* ignore */
  }
  hint(s, "§cToo heavy to turn aside - the blade chipped", 50);
}

// ------------------------------------------------------------------ skill 3: Noto (chiburi + closing click)

function noto(p: Player, s: PlayerState): void {
  if (!ready(s, "noto")) return void hint(s, `§cNoto§7 ${secs(remaining(s, "noto"))}`);
  s.cane.notoAt = now();
  s.cane.deflectStart = -100;
  signal(p, SIG.caneNoto, CANE.notoTicks);
  pose(p, "noto");
  sound(p.dimension, "oddworks.cane.sheathe", p.location, 1.0);
}

function tickNoto(p: Player, s: PlayerState): void {
  const c = s.cane;
  const k = now() - c.notoAt;
  const dim = p.dimension;
  if (k === 2) {
    // chiburi: a sharp flick throws the blood off the blade
    const color: Rgba = c.lastBlood ? { ...c.lastBlood, a: 1 } : { r: 0.75, g: 0.8, b: 0.85, a: 0.8 };
    const dir = p.getViewDirection();
    fx(dim, "oddworks:blood_drop", bladePoint(p), { color, count: c.lastBlood ? 10 : 4, dir: add(scale(rightOf(dir), 0.8), v(0, -0.3, 0)), speed: 1.4 });
    sound(dim, "oddworks.cane.swish", p.location, 0.8, 0.7);
  }
  if (k === 9) {
    const r = hemorrhage(p);
    if (r.hit > 0) {
      shake(p, 0.1, 0.25);
      hint(s, r.killed > 0 ? `§4Noto §7- ${r.hit} wounds opened, ${r.killed} fell. §fIai§7 is ready.` : `§4Noto §7- ${r.hit} wounds opened at the click`, 60);
      if (r.killed > 0) startCd(s, "iai", 0);
    } else hint(s, "§7Noto - the blade rests", 30);
    c.lastBlood = undefined;
  }
  if (k >= CANE.notoTicks) {
    swapHeld(p, ID.caneDrawn, ID.cane);
    c.notoAt = -1;
    startCd(s, "noto", CANE.notoCooldown);
  }
}

// ------------------------------------------------------------------ HUD

export function caneStatus(s: PlayerState, item: string, bleeding: number): string {
  if (item === ID.cane) {
    if (s.cane.gripping) return "";
    return `${ready(s, "iai") ? "§fIai ready §7(hold Use, release on the glint)" : `§8Iai ${secs(remaining(s, "iai"))}`}`;
  }
  const d = ready(s, "deflect") ? "§bDeflect ready" : `§8Deflect ${secs(remaining(s, "deflect"))}`;
  const n = ready(s, "noto") ? "§cNoto ready" : `§8Noto ${secs(remaining(s, "noto"))}`;
  return `${d} §8| ${n}${bleeding ? ` §8| §4bleeding: ${bleeding}` : ""}`;
}

export { bleedingStacks };
