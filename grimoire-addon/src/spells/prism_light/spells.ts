// Grimoire 06 - Prism Light Magic: refraction, reflection, dispersion, interference and recombination.
import { Entity } from "@minecraft/server";
import type { Cast } from "../context";
import { Fizzle } from "../types";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx } from "../../core/fx";
import { bodyCenter, bodyHeight, clearVulnerable, effect, markVulnerable } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { V3, add, dist, dot, flatNorm, hdist, lerp, mul, norm, rotY, sub, v3, yawPitchOf } from "../../core/vec";
import { drive, freeDistance, nearestEnemies, safeSpot, shock } from "../kit";
import { SPECTRUM, alliesNear, arcPoint, healAndCleanse, hostileProjectiles, lure, redirect, segmentClear, spawnDecoy } from "../kit2";

const PE = COLORS.pearl, CH = COLORS.champagne, WT = COLORS.white;
const WHITE_VARIANT = 7;

function* dissolveLater(fx: Fx | undefined, ticks: number, fade = 10): Routine {
  yield ticks;
  fx?.dissolve(fade);
}

function glints(c: Cast, at: V3, radius = 1, count = 1): void {
  c.particle("grimoire:spectral_glint", at, { radius, count, size: 1.2 });
}

/** A light segment that grows from a to b (the construct's length is smoothed client-side). */
function ray(c: Cast, a: V3, b: V3, variant = WHITE_VARIANT, size = 1): Fx | undefined {
  const fx = c.fx("grimoire:fx_pr_ray", a, { dir: sub(b, a), len: 0.05, variant, phase: 1, size });
  fx?.length(dist(a, b));
  return fx;
}

function primaryTarget(c: Cast, range: number, around = 6): Entity | undefined {
  const a = c.aim(range);
  if (a.entity && c.isEnemy(a.entity)) return a.entity;
  return nearestEnemies(c, a.point, around, 1)[0];
}

// ------------------------------------------------------------------------------------------ PR01
export function* sevenfoldVerdict(c: Cast): Routine {
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
    ctrl: add(lerp(at, goal, 0.5), add(mul(side, (i - 3) * 3.2), v3(0, (i % 2 ? 3 : -1.5), 0))),
    start: 2 + i * 2,
    done: false,
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
  c.run(dissolveLater(star, 14), "star");
  yield 14;
}

// ------------------------------------------------------------------------------------------ PR02
export function* totalInternalReflection(c: Cast): Routine {
  const target = primaryTarget(c, c.p("range"));
  const goal = target ? bodyCenter(target) : c.aim(c.p("range")).point;
  const r = c.p("radius") * c.area;
  const base = yawPitchOf(sub(c.player.location, goal)).yaw;
  const angles = [35, -70, 110, -150, 175];
  const route: V3[] = [c.eye()];
  const prisms: Fx[] = [];
  for (let k = 0; k < c.p("prisms"); k++) {
    let placed: V3 | undefined;
    for (const sgn of [1, -1]) {
      const p = add(goal, add(mul(rotY(v3(0, 0, 1), base + angles[k] * sgn), r), v3(0, 0.4 + (k % 2) * 1.2, 0)));
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
  // the white beam is timed through every reflection, then leaves toward the target
  for (let k = 0; k < route.length - 1; k++) {
    const A = route[k], B = route[k + 1];
    const last = k === route.length - 2;
    const beam = ray(c, A, B, last ? 4 : WHITE_VARIANT, last ? 1.4 : 1);
    c.run(dissolveLater(beam, 18 - Math.min(10, k * 2), 6), "beam");
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

// ------------------------------------------------------------------------------------------ PR03
export function* causticBloom(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const n = c.p("lenses");
  const sets = [];
  for (let k = 0; k < n; k++) {
    const off = mul(rotY(v3(0, 0, 1), c.yaw + k * (360 / n)), c.p("spread"));
    const g = c.ground(add(point, off), 10);
    sets.push({
      pos: g,
      lens: c.fx("grimoire:fx_pr_lens", add(g, v3(0, 9, 0)), { phase: 1, size: c.area }),
      flower: c.fx("grimoire:fx_pr_caustic", add(g, v3(0, 0.05, 0)), { phase: 1, size: c.area }),
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

// ------------------------------------------------------------------------------------------ PR04
export function* fraunhoferLattice(c: Cast): Routine {
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
  const last = new Map<string, number>();
  for (let t = 0; t < dur; t++) {
    const swing = Math.sin((t / dur) * Math.PI * 2) * (c.p("sweep") / 2);
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
          return Math.abs(((ang - by + 540) % 360) - 180) < spread * 0.28 + (57 / Math.max(1, d)) * 0.6;
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

// ------------------------------------------------------------------------------------------ PR05
export function* brewstersVeil(c: Cast): Routine {
  const p = c.player;
  const n = c.p("panels");
  const panels: (Fx | undefined)[] = [];
  for (let k = 0; k < n; k++) panels.push(c.fx("grimoire:fx_pr_panel", p.location, { yaw: c.yaw, phase: 1, size: c.area }));
  c.sound("grimoire.prism_light.glass", p.location, 1, 0.9);
  const front = (dir: V3) => dot(flatNorm(dir), flatNorm(p.getViewDirection())) > 0.2;
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
    react: () => panels[1]?.pulse(),
  });
  const seen = new Set<string>();
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

// ------------------------------------------------------------------------------------------ PR06
export function* parallaxDisplacement(c: Cast): Routine {
  const p = c.player;
  const side = () => rotY(flatNorm(p.getViewDirection()), 90);
  const falsePos = () => add(p.location, mul(side(), c.p("offset")));
  const fx = c.fx("grimoire:fx_pr_rgb", falsePos(), { yaw: c.yaw, phase: 1 });
  const decoy = spawnDecoy(c, falsePos());
  c.sound("grimoire.prism_light.beam", p.location, 0.9, 1.3);
  let hit: { from?: Entity } | undefined;
  const ward = c.ward({
    label: "Parallax Displacement",
    priority: 70,
    protects: (e) => e.id === p.id && !hit,
    absorb: (info) => {
      if (hit || info.damage < 1 || (!PHYSICAL_CAUSES.has(info.cause) && info.cause !== "magic")) return info.damage;
      hit = { from: info.attacker };
      return 0;
    },
  });
  yield 10;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok && !hit; t++) {
    fx?.move(falsePos()).yaw(p.getRotation().y);
    decoy?.move(falsePos());
    if (t % 40 === 0) for (const e of c.enemies(p.location, 12)) lure(e, decoy);
    yield 1;
  }
  if (!hit) return;
  ward.alive = false;
  fx?.phase(3);
  c.sound("grimoire.prism_light.shatter", p.location, 1.1, 1);
  glints(c, add(p.location, v3(0, 1, 0)), 1.4, 1.5);
  const away = hit.from?.isValid ? flatNorm(sub(p.location, hit.from.location)) : flatNorm(mul(p.getViewDirection(), -1));
  for (const turn of [70, -70, 110, -110, 0]) {
    const dest = safeSpot(c.dim, add(p.location, mul(rotY(away, turn), c.p("hop"))));
    if (dest && segmentClear(c, add(p.location, v3(0, 0.2, 0)), add(dest, v3(0, 0.2, 0)))) {
      try {
        p.teleport(dest, { keepVelocity: false });
      } catch {
        /* blocked */
      }
      break;
    }
  }
  effect(p, "invisibility", 20, 0);
  yield 12;
}

// ------------------------------------------------------------------------------------------ PR07
export function* chromaticTurnstile(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("gates");
  const gates = [];
  for (let k = 0; k < n; k++) {
    const ang = c.yaw + k * (360 / n);
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), R)), 8);
    const out = ang + 90 + (k % 2 ? 25 : -25);
    gates.push({ at, out, fx: c.fx("grimoire:fx_pr_gate", at, { yaw: out, variant: k % 7, phase: 1, size: c.area }), last: new Map<string, number>() });
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

// ------------------------------------------------------------------------------------------ PR08
export function* kaleidoscopeTheater(c: Cast): Routine {
  const center = c.player.location;
  const theater = c.fx("grimoire:fx_pr_kaleido", center, { yaw: c.yaw, phase: 1, size: (c.p("radius") / 6) * c.area });
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
      const pos = c.ground(add(center, mul(rotY(v3(0, 0, 1), rot + (f.slot * 360) / n), 3.6)), 4);
      f.fx?.move(pos).yaw(c.player.getRotation().y + (f.slot % 2 ? 180 : 0));
      f.decoy?.move(pos);
    });
    if (t % 30 === 5) {
      for (const e of c.enemies(center, c.p("radius") + 8)) {
        const nearest = figs.reduce((a, b) => (hdist(a.fx?.location ?? center, e.location) < hdist(b.fx?.location ?? center, e.location) ? a : b));
        lure(e, nearest.decoy);
        if (e.typeId === "minecraft:player") effect(e, "blindness", 30, 0);
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PR09
export function* interferenceTapestry(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const side = rotY(flatNorm(c.dir), 90);
  const half = (c.p("width") * c.area) / 2;
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
      const shift = ((t / 20) * 6) % 16;
      const inVeil = (e: Entity) => {
        const ab = sub(B, A);
        const k = Math.max(0, Math.min(1, dot(sub(e.location, A), ab) / dot(ab, ab)));
        const nearest = lerp(A, B, k);
        return hdist(e.location, nearest) < 2.4 && e.location.y - base < 4.5;
      };
      const bright = (e: Entity) => ((((e.location.y + bodyHeight(e) * 0.5 - base) * 16 - shift) % 16) + 16) % 16 < 8;
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

// ------------------------------------------------------------------------------------------ PR10
export function* raylineStride(c: Cast): Routine {
  const p = c.player;
  const fwd = flatNorm(c.dir);
  const side = rotY(fwd, 90);
  const feet = p.location;
  const wanted = [add(feet, add(add(mul(fwd, 4), mul(side, 1.4)), v3(0, 0.6, 0))), add(feet, add(add(mul(fwd, 8), mul(side, -1.4)), v3(0, 0.6, 0))), add(feet, mul(fwd, c.p("range")))];
  const route: V3[] = [feet];
  for (const w of wanted) {
    const s = safeSpot(c.dim, w);
    if (!s || !segmentClear(c, add(route[route.length - 1], v3(0, 0.1, 0)), add(s, v3(0, 0.1, 0)))) break;
    route.push(s);
  }
  if (route.length < 2 || dist(route[route.length - 1], feet) < 3) throw new Fizzle("No clear light path");
  const marks = route.slice(1, -1).map((m) => c.fx("grimoire:fx_pr_waypoint", add(m, v3(0, 1.4, 0)), { phase: 1 }));
  for (let k = 0; k < route.length - 1; k++) {
    const r = ray(c, add(route[k], v3(0, 1, 0)), add(route[k + 1], v3(0, 1, 0)), k === 0 ? WHITE_VARIANT : k * 2);
    c.run(dissolveLater(r, 16, 6), "path");
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
        c.run(dissolveLater(after, 8, 6), "after");
      }
      yield 1;
    }
  }
  glints(c, add(p.location, v3(0, 1, 0)), 1, 1);
  for (const m of marks) m?.dissolve(8);
  yield 6;
}

// ------------------------------------------------------------------------------------------ PR11
export function* iridescentSail(c: Cast): Routine {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pr_sail", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.prism_light.sail", p.location, 1, 1);
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    grantFallImmunity(p.id, 30);
    if (!p.isOnGround) {
      effect(p, "slow_falling", 12, 0);
      if (t % 3 === 0) {
        // a glide, never a hover: the sail keeps a steady sink (knockback sets vertical speed outright, so
        // driving with 0 would hold the caster at one height for the whole duration)
        const look = flatNorm(p.getViewDirection());
        let vy = -0.08;
        try {
          vy = Math.min(-0.06, Math.max(-0.22, p.getVelocity().y));
        } catch {
          /* keep default */
        }
        drive(p, { ...mul(look, c.p("glide") * 0.6), y: vy });
      }
      if (t % 4 === 0) glints(c, add(p.location, v3(0, 2.4, 0)), 1.2, 0.4);
    }
    if (t === 10) fx?.phase(2);
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PR12
export function* spectralDiagnosis(c: Cast): Routine {
  const target = primaryTarget(c, c.p("range"));
  if (!target) throw new Fizzle("Nothing to analyse");
  const at = add(c.eye(), add(mul(flatNorm(c.dir), 0.6), v3(0, 0.8, 0)));
  const scope = c.fx("grimoire:fx_pr_spectroscope", at, { dir: sub(bodyCenter(target), at), len: 1, phase: 1 });
  c.sound("grimoire.prism_light.scan", at, 1, 1);
  yield 14;
  scope?.phase(2);
  for (let t = 0; t < 20 && target.isValid; t++) {
    const tc = bodyCenter(target);
    scope?.aim(sub(tc, at)).length(dist(at, tc) / 1.0);
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

// ------------------------------------------------------------------------------------------ PR13
export function* whitepointBenediction(c: Cast): Routine {
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

// ------------------------------------------------------------------------------------------ PR14
export function* chromaticObservatory(c: Cast): Routine {
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
  const ill = c.fx("grimoire:fx_pr_illumination", add(point, v3(0, 0.2, 0)), { yaw: c.yaw, phase: 1, size: (R / 10) * 1.0 });
  c.sound("grimoire.prism_light.crown", point, 1.6, 1);
  c.flash(point, R * 2, { r: 1, g: 0.98, b: 0.92 }, 0.12);
  shock(c, point, R, c.p("finalDamage"), { knock: 0.9, up: 0.3, color: WT, color2: CH, minK: 0.55, particle: "grimoire:ring_h" });
  c.run(dissolveLater(ill, 30, 12), "illumination");
  yield 30;
}

// ------------------------------------------------------------------------------------------ PR15
function segIntersect(a: V3, b: V3, c: V3, d: V3): V3 | undefined {
  const r = { x: b.x - a.x, z: b.z - a.z };
  const s = { x: d.x - c.x, z: d.z - c.z };
  const den = r.x * s.z - r.z * s.x;
  if (Math.abs(den) < 1e-6) return undefined;
  const t = ((c.x - a.x) * s.z - (c.z - a.z) * s.x) / den;
  const u = ((c.x - a.x) * r.z - (c.z - a.z) * r.x) / den;
  if (t <= 0.05 || t >= 0.95 || u <= 0.05 || u >= 0.95) return undefined;
  return { x: a.x + r.x * t, y: a.y, z: a.z + r.z * t };
}

export function* colorlessCoronation(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const H = c.p("height");
  const fogged = new Set<string>();
  const fog = () => {
    for (const pl of c.dim.getPlayers({ location: point, maxDistance: R + 6 })) {
      if (fogged.has(pl.id)) continue;
      fogged.add(pl.id);
      try {
        pl.runCommand("fog @s push grimoire:coronation grimoire_pr15");
      } catch {
        /* ignore */
      }
    }
  };
  c.onCleanup(() => {
    for (const id of fogged) {
      try {
        c.dim.getPlayers().find((x) => x.id === id)?.runCommand("fog @s remove grimoire_pr15");
      } catch {
        /* left */
      }
    }
  });
  // Phase I - The Unweaving of White
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
    curtains.push({ a, b, fx: c.fx("grimoire:fx_pr_curtain", a, { dir: flatNorm(sub(b, a)), variant: k, phase: 1, size: 0.5 * c.area }), hit: new Set<string>() });
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
  // Phase II - Sevenfold Refraction
  for (const p of prisms) p.fx?.phase(2);
  c.sound("grimoire.prism_light.sweep", point, 1.6, 0.8);
  for (let wave = 0; wave < 3 && c.ok; wave++) {
    const chords: [V3, V3][] = [];
    for (let k = 0; k < 7; k++) {
      const a = prisms[k].at, b = prisms[(k + 3 + wave) % 7].at;
      chords.push([a, b]);
      const r = ray(c, a, b, k, 1.4);
      c.run(dissolveLater(r, 24, 6), "chord");
    }
    const crossings: V3[] = [];
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
  // Phase III - The Colorless Coronation
  for (const p of prisms) p.fx?.phase(3);
  for (const p of prisms) {
    const back = ray(c, p.at, add(point, v3(0, H, 0)), prisms.indexOf(p), 1.2);
    c.run(dissolveLater(back, 18, 6), "return");
  }
  yield 16;
  const crown = c.fx("grimoire:fx_pr_crown", add(point, v3(0, H, 0)), { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.prism_light.crown", point, 2, 1);
  yield 34;
  crown?.phase(2);
  shaft?.dissolve(10);
  c.sound("grimoire.prism_light.focus", point, 1.8, 0.7);
  yield 20;
  const bloom = c.fx("grimoire:fx_pr_bloom", point, { yaw: c.yaw, phase: 1, size: (R / 12) * 1.0 });
  c.flash(point, R * 2.5, { r: 1, g: 1, b: 1 }, 0.25);
  c.shake(point, R * 3, 0.7, 1.0);
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
