// Grimoire 05 - Darkness Magic: folding dark-green planes, occlusion, silhouettes and outlines.
import { Entity } from "@minecraft/server";
import type { Cast } from "../context";
import { Fizzle } from "../types";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx } from "../../core/fx";
import { bodyCenter, bodyHeight, effect, push } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { V3, add, dist, dot, flatNorm, hdist, lerp, mul, norm, rotY, sub, v3, yawPitchOf } from "../../core/vec";
import { nearestEnemies, shock } from "../kit";
import { alliesNear, arcPoint, hostileProjectiles, lure, neutralize, spawnDecoy, surfaceRoute } from "../kit2";
import { onAttack } from "../hooks";

const DG = COLORS.darkgreen, EM = COLORS.emerald, JD = COLORS.jade;
const SHADE = { r: 0.02, g: 0.09, b: 0.05 };

function* dissolveLater(fx: Fx | undefined, ticks: number, fade = 10): Routine {
  yield ticks;
  fx?.dissolve(fade);
}

function sheets(c: Cast, at: V3, radius = 1, count = 1): void {
  c.particle("grimoire:shadow_sheets", at, { color: SHADE, color2: EM, radius, count, size: 1.2 });
}

function primaryTarget(c: Cast, range: number, around = 6): Entity | undefined {
  const a = c.aim(range);
  if (a.entity && c.isEnemy(a.entity)) return a.entity;
  return nearestEnemies(c, a.point, around, 1)[0];
}

// ------------------------------------------------------------------------------------------ D01
export function* umbralOrigami(c: Cast): Routine {
  const n = c.p("sheets");
  const right = rotY(flatNorm(c.dir), 90);
  const a = c.aim(c.p("range"));
  const goal = a.point;
  const folded = [];
  for (let k = 0; k < n; k++) {
    const off = k - (n - 1) / 2;
    const start = add(c.origin, add(add(mul(right, off * 1.4), v3(0, 0.6 + Math.abs(off) * 0.25, 0)), mul(c.dir, 1.2)));
    folded.push({ start, fx: c.fx("grimoire:fx_d_sheet", start, { yaw: c.yaw + off * 20, phase: 1, size: c.area }), off });
    c.sound("grimoire.darkness.fold", start, 0.6, 1.1 + k * 0.08);
    yield 2;
  }
  yield 6;
  const hits = folded.map(() => new Set<string>());
  folded.forEach((s) => s.fx?.phase(2));
  c.sound("grimoire.darkness.release", c.origin, 1, 1.2);
  const T = 12;
  for (let t = 1; t <= T + 4; t++) {
    folded.forEach((s, i) => {
      // every sheet cuts along its own curved approach (left, right, high, low...) and passes through the goal
      const ctrl = add(lerp(s.start, goal, 0.5), add(mul(right, s.off * 3.5), v3(0, (i % 2 ? 2.5 : -0.5), 0)));
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

// ------------------------------------------------------------------------------------------ D02
export function* mawOfTheUnseen(c: Cast): Routine {
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

// ------------------------------------------------------------------------------------------ D03
export function* unwrittenSentence(c: Cast): Routine {
  const first = primaryTarget(c, c.p("range"));
  if (!first) throw new Fizzle("No target for the sentence");
  const targets = [first, ...nearestEnemies(c, first.location, 6, 3).filter((e) => e.id !== first.id)].slice(0, 3);
  const marks = new Map<string, { e: Entity; n: number; fx?: Fx }>();
  const right = rotY(flatNorm(c.dir), 90);
  const n = c.p("glyphs");
  const glyphs: { fx?: Fx; start: V3 }[] = [];
  for (let k = 0; k < n; k++) {
    const start = add(c.origin, add(add(mul(right, (k - (n - 1) / 2) * 1.5), v3(0, 1.1 + (k % 2) * 0.5, 0)), mul(c.dir, 1.5)));
    glyphs.push({ start, fx: c.fx("grimoire:fx_d_glyph", start, { yaw: c.yaw, variant: k, phase: 1, size: c.area }) });
    c.sound("grimoire.darkness.glyph", start, 0.8, 0.9 + k * 0.1);
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
      const m = marks.get(tgt.id) ?? { e: tgt, n: 0, fx: undefined as Fx | undefined };
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
  // the final glyph completes the sentence on every marked target
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

// ------------------------------------------------------------------------------------------ D04
export function* sevenfoldEclipse(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("discs");
  const sky = add(point, v3(0, c.p("height"), 0));
  const discs = [];
  for (let i = 0; i < n; i++) {
    discs.push({
      disc: c.fx("grimoire:fx_d_eclipse", sky, { phase: 1, size: 0.55 * c.area }),
      umbra: c.fx("grimoire:fx_d_umbra", point, { phase: 1, size: 0.55 * c.area }),
      w: 0.05 + i * 0.011, ph: i * 0.9, ph2: i * 1.7,
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
      /* no camera */
    }
  }
  for (const e of c.enemies(point, umbraR)) {
    c.hit(e, c.p("fullDamage"), { immediate: true });
    effect(e, "blindness", 50, 0);
    sheets(c, bodyCenter(e), 1.2, 1.4);
  }
  yield 16;
}

// ------------------------------------------------------------------------------------------ D05
export function* velvetOfTheHollowKing(c: Cast): Routine {
  const p = c.player;
  const fx = c.fx("grimoire:fx_d_velvet", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.curtain", p.location, 0.9, 1.4);
  c.ward({
    label: "Velvet of the Hollow King",
    priority: 25,
    protects: (e) => e.id === p.id,
    absorb: (info) => (PHYSICAL_CAUSES.has(info.cause) ? info.damage * (1 - c.p("reduction")) : info.damage * 0.85),
    react: (info) => {
      fx?.pulse();
      sheets(c, add(info.hurt.location, v3(0, 1, 0)), 0.6, 0.6);
      c.sound("grimoire.darkness.fold", info.hurt.location, 0.8, 1.3);
    },
  });
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ D06
export function* shadowLatch(c: Cast): Routine {
  const p = c.player;
  const lock = c.fx("grimoire:fx_d_lock", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.latch", p.location, 0.7, 1.4);
  let attacker: Entity | undefined;
  const ward = c.ward({
    label: "Shadow Latch",
    priority: 40,
    protects: (e) => e.id === p.id && !attacker,
    absorb: (info) => {
      if (attacker || info.cause !== "entityAttack" || !info.attacker || info.projectile) return info.damage;
      if (dist(info.attacker.location, p.location) > 5) return info.damage;
      attacker = info.attacker;
      return info.damage * (1 - c.p("reduction"));
    },
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

// ------------------------------------------------------------------------------------------ D07
export function* curtainfallDivide(c: Cast): Routine {
  const fwd = flatNorm(c.dir);
  const side = rotY(fwd, 90);
  const half = (c.p("width") * c.area) / 2;
  const curtains = [];
  for (let k = 0; k < c.p("curtains"); k++) {
    const at = c.ground(add(c.player.location, mul(fwd, 4 + k * c.p("spacing"))), 8);
    curtains.push({ at, fx: c.fx("grimoire:fx_d_curtain", at, { yaw: c.yaw, phase: 1, size: c.area }) });
    c.sound("grimoire.darkness.curtain", at, 1.1, 0.8 + k * 0.1);
    yield 5;
  }
  yield 10;
  for (const cu of curtains) cu.fx?.phase(2);
  const lastSide = new Map<string, number[]>();
  const decoys: (Fx | undefined)[] = [];
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 4 === 0) {
      for (const e of c.enemies(c.player.location, 4 + c.p("curtains") * c.p("spacing") + 6)) {
        const sides = curtains.map((cu) => Math.sign(dot(sub(e.location, cu.at), fwd)));
        const prev = lastSide.get(e.id);
        lastSide.set(e.id, sides);
        if (!prev) continue;
        curtains.forEach((cu, i) => {
          if (prev[i] === sides[i] || Math.abs(dot(sub(e.location, cu.at), side)) > half) return;
          // crossed a curtain: sight and aim are disrupted
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

// ------------------------------------------------------------------------------------------ D08
function mosaicJade(p: number, i: number, j: number): boolean {
  if (p === 0) return i === 3 || i === 4 || j === 3 || j === 4;
  return i === j || i + j === 7 || ((i === 0 || i === 7) && (j === 0 || j === 7));
}

export function* duskMosaic(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const center = v3(Math.floor(point.x) + 0.5, point.y, Math.floor(point.z) + 0.5);
  const fx = c.fx("grimoire:fx_d_mosaic", center, { yaw: 0, phase: 1 });
  c.sound("grimoire.darkness.tile", center, 1, 0.8);
  yield 20;
  let pat = 0;
  fx?.phase(2);
  const S = 1.25;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t > 0 && t % 50 === 0) {
      pat = 1 - pat;
      fx?.phase(pat === 0 ? 2 : 3);
      c.sound("grimoire.darkness.tile", center, 1.2, pat ? 1.1 : 0.9);
    }
    if (t % 10 === 0 && t % 50 > 18) {
      const cell = (pos: V3) => {
        const i = Math.floor((pos.x - center.x) / S + 4);
        const j = Math.floor((pos.z - center.z) / S + 4);
        return i >= 0 && i < 8 && j >= 0 && j < 8 && Math.abs(pos.y - center.y) < 2.5 ? [i, j] : undefined;
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

// ------------------------------------------------------------------------------------------ D09
export function* censorsSeal(c: Cast): Routine {
  const target = primaryTarget(c, c.p("range"));
  if (!target) throw new Fizzle("No target to seal");
  const head = () => add(target.location, v3(0, bodyHeight(target) + 0.7, 0));
  const fx = c.fx("grimoire:fx_d_mask", head(), { yaw: yawPitchOf(sub(c.player.location, target.location)).yaw, phase: 1, size: Math.max(0.8, bodyHeight(target) / 1.8) });
  c.sound("grimoire.darkness.whisper", head(), 1.1, 0.7);
  const isPlayer = target.typeId === "minecraft:player";
  let decoy: Fx | undefined;
  for (let t = 0; t < c.p("duration") * 20 && target.isValid; t++) {
    fx?.follow(target, v3(0, bodyHeight(target) + 0.7, 0), 0);
    if (t % 20 === 0) {
      effect(target, "weakness", 30, 1);
      effect(target, "slowness", 30, 0);
      if (isPlayer) effect(target, "blindness", 30, 0);
    }
    if (t === 10 || t % 40 === 30) {
      // the apertures close: the target loses its bearings and turns on a phantom of darkness
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

// ------------------------------------------------------------------------------------------ D10
export function* silhouetteTraverse(c: Cast): Routine {
  const p = c.player;
  const route = surfaceRoute(c, p.location, c.dir, c.p("range") * c.area);
  if (route.length < 4) throw new Fizzle("No surface to travel along");
  const fx = c.fx("grimoire:fx_d_silhouette", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.fold", p.location, 1, 0.8);
  effect(p, "invisibility", 40, 0);
  yield 5;
  fx?.phase(2);
  const rot = p.getRotation();
  let idx = 0;
  const step = c.p("speed") / 0.5;
  while (idx < route.length - 1 && c.ok) {
    idx = Math.min(route.length - 1, idx + step);
    const at = route[Math.floor(idx)];
    fx?.move(at);
    try {
      p.teleport(at, { rotation: rot, keepVelocity: false });
    } catch {
      break;
    }
    c.particle("grimoire:shadow_print", add(at, v3(0, 0.05, 0)), { color: SHADE, color2: DG, size: 1.4, radius: (rot.y * Math.PI) / 180 });
    yield 1;
  }
  fx?.phase(3);
  try {
    p.removeEffect("invisibility");
  } catch {
    /* none */
  }
  grantFallImmunity(p.id, 20);
  c.particle("grimoire:outline_mark", add(p.location, v3(0, 1, 0)), { color: JD, color2: EM, radius: 1, count: 1.2 });
  c.sound("grimoire.darkness.step", p.location, 1, 1);
  yield 10;
}

// ------------------------------------------------------------------------------------------ D11
export function* stairwayOfTheUnlitSky(c: Cast): Routine {
  const p = c.player;
  const set = c.blocks();
  const steps: { loc: V3; top: number }[] = [];
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
        const old = steps.shift()!;
        set.remove(old.loc);
        const ffx = c.fx("grimoire:fx_d_step", v3(old.loc.x + 0.5, old.top, old.loc.z + 0.5), { phase: 3 });
        c.run(dissolveLater(ffx, 8, 2), "fold");
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ D12
export function* inklessDoppelganger(c: Cast): Routine {
  const p = c.player;
  const hist: { pos: V3; yaw: number }[] = [];
  const delay = c.p("delay");
  const fx = c.fx("grimoire:fx_d_double", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.darkness.whisper", p.location, 1, 1.2);
  sheets(c, add(p.location, v3(0, 0.2, 0)), 1, 1);
  const attacks: number[] = [];
  let tick = 0;
  const off = onAttack({ attackerId: p.id, fn: () => attacks.push(tick + delay) });
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
      while (attacks.length && attacks[0] <= tick) {
        attacks.shift();
        fx?.pulse();
        const victim = nearestEnemies(c, add(s.pos, v3(0, 1, 0)), c.p("reach"), 1)[0];
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

// ------------------------------------------------------------------------------------------ D13
export function* footfallReversal(c: Cast): Routine {
  const target = primaryTarget(c, c.p("range"));
  if (!target) throw new Fizzle("No target to track");
  const tracker = c.fx("grimoire:fx_d_tracker", target.location, { phase: 1, size: Math.max(0.8, bodyHeight(target) / 1.9) });
  c.sound("grimoire.darkness.glyph", target.location, 1, 0.6);
  const path: V3[] = [];
  for (let t = 0; t < c.p("recordTicks") && target.isValid; t++) {
    tracker?.follow(target, v3(0, 0.05, 0), 0);
    if (t % 2 === 0) path.push(target.location);
    if (t % 6 === 0) {
      const yaw = target.getRotation().y;
      c.particle("grimoire:shadow_print", add(target.location, v3(0, 0.05, 0)), { color: SHADE, color2: DG, size: 1.2, radius: (yaw * Math.PI) / 180 });
    }
    yield 1;
  }
  tracker?.dissolve(10);
  if (path.length < 2) return;
  const n = c.p("constructs");
  const wraiths = [];
  for (let i = 0; i < n; i++) {
    const startIdx = Math.floor(((path.length - 1) * (n - i)) / n);
    wraiths.push({ idx: startIdx, fx: c.fx("grimoire:fx_d_wraith", path[startIdx], { phase: 1, size: c.area }), hit: new Set<string>() });
  }
  c.sound("grimoire.darkness.fold", path[path.length - 1], 1.1, 0.7);
  yield 8;
  for (const w of wraiths) w.fx?.phase(2);
  // reversed travel: every construct walks the recorded footsteps backwards
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

// ------------------------------------------------------------------------------------------ D14
export function* courtOfTheUnseen(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("doors");
  const lightDir = flatNorm(sub(point, c.player.location));
  const doors: { ang: number; r: number; fx?: Fx; shadow?: Fx; at: V3 }[] = [];
  for (let k = 0; k < n; k++) {
    const ang = c.yaw + k * (360 / n) + ((k * 37) % 23) - 11;
    const r = R * (0.75 + ((k * 13) % 5) * 0.08);
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), r)), 8);
    doors.push({
      ang, r, at,
      fx: c.fx("grimoire:fx_d_door", at, { yaw: ang + 90, phase: 1, size: c.area }),
      shadow: c.fx("grimoire:fx_d_doorshadow", add(at, v3(0, 0.05, 0)), { dir: lightDir, phase: 1, size: c.area }),
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
      const inShadow: Entity[] = [];
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
  // climax: the court folds inward into one construct, then shatters into sinking sheets
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

// ------------------------------------------------------------------------------------------ D15
export function* worldWithoutAnOutline(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  // Phase I - The Vanishing Contours
  const domain = c.fx("grimoire:fx_d_domain", add(point, v3(0, 0.05, 0)), { yaw: c.yaw, phase: 1, size: (R / 20) * 1.0 });
  c.fx("grimoire:fx_circle_d", add(c.player.location, v3(0, 0.06, 0)), { size: 3, variant: 1, phase: 1 });
  c.sound("grimoire.darkness.edict", point, 2, 0.8);
  const fogged = new Set<string>();
  const fogTick = () => {
    for (const pl of c.dim.getPlayers({ location: point, maxDistance: R + 4 })) {
      if (fogged.has(pl.id)) continue;
      fogged.add(pl.id);
      try {
        pl.runCommand("fog @s push grimoire:outline_void grimoire_d15");
      } catch {
        /* ignore */
      }
    }
  };
  c.onCleanup(() => {
    for (const id of fogged) {
      const pl = c.dim.getPlayers().find((x) => x.id === id);
      try {
        pl?.runCommand("fog @s remove grimoire_d15");
      } catch {
        /* left */
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
  // Phase II - Sovereignty of Shadows
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
  // Phase III - The Final Fold
  const planes: { fx?: Fx; at: V3; dir: V3 }[] = [];
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

