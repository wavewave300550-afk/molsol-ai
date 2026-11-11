import { Entity, EntityProjectileComponent, Player, system } from "@minecraft/server";
import type { Cast } from "../context";
import { Fizzle } from "../types";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx, particle } from "../../core/fx";
import { bodyCenter, effect, isAllyOrSelf, isEnemy, livingNear, pullToward, push, relation } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { bind, endBind } from "../../core/status";
import { flash as hudFlash, stateOf } from "../../core/state";
import { V3, add, dist, dot, flatNorm, hdist, len, lerp, mul, norm, rotY, rng, sub, v3, yawPitchOf } from "../../core/vec";
import { drive, fly, freeDistance, local, nearestEnemies, shock } from "../kit";
import { grounded, lower, mazeColumns, raise } from "../structures";

const OR = COLORS.orange, GD = COLORS.gold, WH = COLORS.white, CU = COLORS.copper;

// ------------------------------------------------------------------------------------------ P01
export function* pressureLance(c: Cast): Routine {
  const dir = c.dir;
  const start = add(c.origin, add(mul(dir, 1.8), v3(0, -0.25, 0)));
  const fx = c.fx("grimoire:fx_p_lance", start, { dir, phase: 1, size: c.empowered ? 1.35 : 1 });
  c.sound("grimoire.pressure.lance", start);
  c.particle("grimoire:converge", start, { color: OR, color2: GD, radius: 2.4, life: 0.35, count: 1.5 });
  yield 6;
  fx?.phase(2);
  c.particle("grimoire:ring_dir", start, { color: GD, color2: WH, radius: 3.2, dir });
  c.shake(start, 8, 0.15, 0.2);
  let end = start;
  yield* fly(c, {
    fx, from: start, dir, speed: c.p("speed"), range: c.p("range"), radius: c.p("radius") * c.area, pierce: Infinity,
    onHit: (e, at) => {
      c.hit(e, c.p("damage"));
      push(e, dir, 1.3, 0.3);
      c.particle("grimoire:ring_dir", at, { color: OR, color2: GD, radius: 2.6, dir });
      c.particle("grimoire:spark_burst", at, { color: GD, color2: WH, radius: 1, count: 1 });
      c.sound("grimoire.pressure.thud", at, 0.9, 1.2);
    },
    onTick: (pos, i) => {
      // conical shockwaves widening behind the lance + atmospheric distortion
      if (i % 2 === 0) c.particle("grimoire:ring_dir", pos, { color: OR, radius: 1.2 + Math.min(2.5, i * 0.12), dir, life: 1.2 });
      if (i % 3 === 1) c.particle("grimoire:ripple_dir", pos, { color: WH, radius: 2, dir, life: 1.4 });
    },
    onEnd: (pos) => {
      end = pos;
    },
  });
  fx?.phase(3);
  shock(c, end, c.p("impactRadius"), c.p("impactDamage"), { knock: 1.1, up: 0.35, sound: "grimoire.pressure.boom", shake: 0.35 });
  c.particle("grimoire:ring_dir", end, { color: WH, color2: OR, radius: 6, dir });
  yield 8;
}

// ------------------------------------------------------------------------------------------ P02
export function* atlasPiston(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const h = c.p("height");
  const R = c.p("radius") * c.area;
  const circle = c.fx("grimoire:fx_circle_p", add(point, v3(0, 0.06, 0)), { size: R, variant: 1, phase: 1 });
  const piston = c.fx("grimoire:fx_p_piston", add(point, v3(0, h, 0)), { len: h, phase: 1, size: c.area });
  c.sound("grimoire.pressure.rise", point, 1.2, 1.2);
  // preparation: rings spin up, pressure builds on the ground (warning + light slow)
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
  // expanding pressure waves
  let inner = R;
  for (let k = 1; k <= 2; k++) {
    yield 6;
    const r = R + (c.p("waveRadius") * c.area - R) * (k / 2);
    c.particle("grimoire:ring_h", add(point, v3(0, 0.2, 0)), { color: OR, color2: WH, radius: r * 2.2, life: 1.2 });
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

// ------------------------------------------------------------------------------------------ P03
export function* isobaricSeverance(c: Cast): Routine {
  const dir = flatNorm(c.dir);
  const { yaw } = yawPitchOf(dir);
  let pos = add(c.feet, add(mul(dir, 1.5), v3(0, 1.0, 0)));
  const fx = c.fx("grimoire:fx_p_blade", pos, { yaw, phase: 1, size: c.area });
  c.sound("grimoire.pressure.whoosh", pos, 1.2, 1.3);
  yield 4;
  fx?.phase(2);
  const half = (c.p("width") / 2) * c.area;
  const right = rotY(dir, 90);
  const hitIds = new Set<string>();
  const eruptions: { at: V3; tick: number }[] = [];
  let travelled = 0;
  const range = c.p("range");
  let step = 0;
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
        c.particle("grimoire:spark_burst", bodyCenter(e), { color: OR, color2: WH, count: 1.2 });
      }
    }
    if (step % 2 === 0) {
      for (const s of [-0.66, 0, 0.66]) eruptions.push({ at: c.ground(add(next, mul(right, half * s)), 6), tick: system.currentTick + c.p("delay") });
    }
    fx?.move(next);
    pos = next;
    travelled += c.p("speed");
    step++;
    yield* erupt(c, eruptions);
    yield 1;
  }
  fx?.dissolve(8);
  for (let i = 0; i < 30 && eruptions.length; i++) {
    yield* erupt(c, eruptions);
    yield 1;
  }
}

function* erupt(c: Cast, list: { at: V3; tick: number }[]): Routine {
  const now = system.currentTick;
  for (let i = list.length - 1; i >= 0; i--) {
    if (list[i].tick > now) continue;
    const e = list.splice(i, 1)[0];
    c.particle("grimoire:ring_h", add(e.at, v3(0, 0.15, 0)), { color: OR, color2: GD, radius: 5, life: 0.8 });
    c.particle("grimoire:beam_up", e.at, { color: GD, color2: WH, radius: 1.2, size: 0.8, count: 0.6 });
    for (const t of c.enemies(e.at, 2.6)) {
      c.hit(t, c.p("delayedDamage"));
      push(t, v3(0, 0, 0), 0, 0.55);
    }
    c.sound("grimoire.pressure.thud", e.at, 0.7, 1.3);
  }
}

// ------------------------------------------------------------------------------------------ P04
export function* cataclysmSalvo(c: Cast): Routine {
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
  const r = rng(system.currentTick);
  for (let v = 0; v < volleys; v++) {
    const targets = nearestEnemies(c, aim.point, 14, 12);
    for (let k = 0; k < perVolley; k++) {
      const side = k % 2 ? 1 : -1;
      const yawNow = p.getRotation().y;
      const from = local({ yaw: yawNow }, p.location, side * (0.8 + (k % 3) * 0.55), 0.8 + v * 0.45 + (k % 2) * 0.3, -0.5);
      const tgt = targets.length ? targets[(v * perVolley + k) % targets.length] : undefined;
      const goal = tgt ? bodyCenter(tgt) : add(aim.point, v3((r() - 0.5) * 8, 1, (r() - 0.5) * 8));
      const dir = norm(sub(goal, from));
      const disc = c.fx("grimoire:fx_p_disc", from, { dir, phase: 1 });
      c.run(fly(c, {
        fx: disc, from, dir, speed: 1.7, range: c.p("range") + 6, radius: 0.8, pierce: 1, homing: tgt, homingRate: 0.3,
        onHit: () => undefined,
        onEnd: (at) => {
          disc?.dissolve(3);
          shock(c, at, c.p("blastRadius"), c.p("damage"), { knock: 0.9, up: 0.35, sound: "grimoire.pressure.disc", pitch: 0.8 + r() * 0.4, ringLife: 0.7 });
          c.particle("grimoire:spark_burst", at, { color: OR, color2: WH, count: 0.8 });
        },
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

// ------------------------------------------------------------------------------------------ P05
export function* aegisOfIsobars(c: Cast): Routine {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  const dome = c.fx("grimoire:fx_p_dome", center, { size: R / 5.1, phase: 1 });
  c.sound("grimoire.pressure.hum", center, 1, 0.8);
  const cap = c.p("layerCapacity") * c.power;
  const layers = [cap, cap, cap];
  let broken = 0;
  const owner = c.player;
  c.ward({
    label: "aegis", priority: 30,
    protects: (e) => isAllyOrSelf(owner, e) && dist(e.location, center) <= R,
    absorb: (info) => {
      let dmg = info.damage;
      while (dmg > 0 && broken < 3) {
        const take = Math.min(dmg, layers[broken]);
        layers[broken] -= take;
        dmg -= take;
        if (layers[broken] <= 0.001) broken++;
      }
      return dmg;
    },
    react: (info) => {
      dome?.pulse();
      dome?.phase(Math.min(5, 2 + broken));
      c.sound("grimoire.pressure.thud", info.hurt.location, 0.8, 0.7);
      c.particle("grimoire:ring_h", add(center, v3(0, R * 0.5, 0)), { color: GD, radius: R * 2, life: 0.6 });
    },
  });
  const redirected = new Set<string>();
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    // projectiles crossing the dome from outside are turned around (supported: any entity with a projectile component)
    if (t % 2 === 0) {
      for (const e of c.dim.getEntities({ location: center, maxDistance: R + 2.5 })) {
        if (redirected.has(e.id)) continue;
        const proj = e.getComponent(EntityProjectileComponent.componentId) as EntityProjectileComponent | undefined;
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
          /* some projectiles refuse impulses */
        }
        c.particle("grimoire:ring_dir", e.location, { color: GD, color2: WH, radius: 1.6, dir: out });
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

// ------------------------------------------------------------------------------------------ P06
export function* counterpressureMantle(c: Cast): Routine {
  const p = c.player;
  const mantle = c.fx("grimoire:fx_p_mantle", p.location, { phase: 1 });
  c.sound("grimoire.pressure.hum", p.location, 0.9, 1.2);
  const lastReflect = new Map<string, number>();
  c.ward({
    label: "mantle", priority: 20,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause) || !info.attacker || info.attacker.id === p.id) return info.damage;
      if (dist(info.attacker.location, p.location) > c.p("range")) return info.damage;
      return info.damage * (1 - c.p("reduction"));
    },
    react: (info) => {
      const a = info.attacker;
      if (!a || !a.isValid || relation(p, a) === "self") return;
      const now = system.currentTick;
      if ((lastReflect.get(a.id) ?? -99) > now - 10) return; // no rapid ping-pong
      lastReflect.set(a.id, now);
      mantle?.pulse();
      c.sound("grimoire.pressure.pulse", p.location, 1, 1.4);
      system.runTimeout(() => {
        if (!p.isValid || !a.isValid) return;
        push(a, sub(a.location, p.location), c.p("knock"), 0.55);
        if (isEnemy(p, a) || a.typeId !== "minecraft:player") c.hit(a, c.p("reflectDamage"), { kind: "reflect" });
        c.particle("grimoire:ring_h", add(p.location, v3(0, 1, 0)), { color: OR, color2: WH, radius: 7, life: 0.6 });
        c.particle("grimoire:ring_dir", bodyCenter(a), { color: GD, radius: 2.5, dir: norm(sub(a.location, p.location)) });
        for (const e of c.enemies(p.location, 3)) if (e.id !== a.id) push(e, sub(e.location, p.location), 1.0, 0.3);
        c.sound("grimoire.pressure.boom", p.location, 0.7, 1.5);
      }, 3);
    },
  });
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (!c.ok) return;
    mantle?.follow(p, v3(0, 0, 0)).yaw(p.getRotation().y);
    if (t % 10 === 0) c.particle("grimoire:ripple_h", add(p.location, v3(0, 1.2, 0)), { color: OR, radius: 2.4, life: 0.8 });
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ P07
export function titansVise(c: Cast): Routine {
  const a = c.aim(c.p("range"));
  const list = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity!.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to trap in range");
  return (function* () {
    const items = targets.map((t) => ({
      t,
      fx: c.fx("grimoire:fx_p_vise", t.location, { phase: 1, size: Math.max(1, Math.min(2.2, (t.getHeadLocation().y - t.location.y) / 1.6)) }),
      b: c.bind(t, c.p("duration") * 20 + 10),
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
        c.particle("grimoire:spark_burst", bodyCenter(it.t), { color: GD, color2: WH, count: 2 });
      }
      endBind(it.b, false);
    }
    c.sound("grimoire.pressure.slam", last, 0.8, 1.3);
    yield 10;
  })();
}

// ------------------------------------------------------------------------------------------ P08
export function* atmosphericLabyrinth(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const center = { x: Math.floor(point.x) + 0.5, y: Math.floor(point.y), z: Math.floor(point.z) + 0.5 };
  const cells = 4, cell = 4, size = cells * cell;
  const set = c.blocks();
  c.fx("grimoire:fx_circle_p", add(center, v3(0, 0.08, 0)), { size: size * 0.75, variant: 1, phase: 1 });
  const cols: Fx[] = [];
  for (const [i, j] of [[0, 0], [0, 4], [4, 0], [4, 4], [2, 2], [0, 2], [4, 2], [2, 0], [2, 4]]) {
    const at = c.ground({ x: center.x - size / 2 + i * cell, y: center.y + 4, z: center.z - size / 2 + j * cell }, 10);
    const f = c.fx("grimoire:fx_p_column", at, { phase: 1, size: 1 });
    if (f) cols.push(f);
    yield 1;
  }
  c.sound("grimoire.pressure.rise", center, 1.2, 1);
  let seed = system.currentTick;
  let current = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
  yield* raise(set, [...current.values()], c.p("height"), "grimoire:pressure_barrier", 70, 2);
  const fallback = !set.enabled;
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t > 0 && t % (c.p("shiftInterval") * 20) === 0 && !fallback) {
      // barriers reposition: dissolve some walls, raise others (paths change)
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
      // no-block mode: invisible walls still repel enemies crossing the wall lines
      for (const e of c.enemies(center, size * 0.75)) {
        const k = `${Math.floor(e.location.x)},${Math.floor(e.location.z)}`;
        if (current.has(k)) push(e, sub(e.location, center), 0.8, 0.2);
      }
    }
    yield 1;
  }
  yield* lower(set, 90);
}

// ------------------------------------------------------------------------------------------ P09
export function* resonanceCage(c: Cast): Routine {
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
      // trapped: enemies near the cage wall are pushed back inside
      if (t % 2 === 0) {
        for (const e of c.enemies(center, R + 1.5)) {
          if (dist(bodyCenter(e), center) > R - 0.7) push(e, sub(center, e.location), 0.7, 0.05);
        }
      }
      yield 1;
    }
    // synchronized pulse: visuals, audio and damage on the same tick
    cage?.pulse();
    c.sound("grimoire.pressure.pulse", center, 1.1, 0.9 + k * 0.06);
    c.particle("grimoire:converge", center, { color: OR, color2: WH, radius: R, life: 0.35, count: 2 });
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

// ------------------------------------------------------------------------------------------ P10
export function* pressureStep(c: Cast): Routine {
  const p = c.player;
  let dir = flatNorm(c.dir);
  try {
    const mv = p.inputInfo.getMovementVector();
    if (Math.abs(mv.x) + Math.abs(mv.y) > 0.2) {
      const f = dir, r = rotY(f, 90);
      dir = norm(add(mul(f, mv.y), mul(r, -mv.x)));
    }
  } catch {
    /* no input info */
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
    hudFlash(stateOf(p), "§7Pressure Step blocked by terrain", 30);
    yield 4;
    return;
  }
  const ticks = 5;
  const start = p.location;
  for (let t = 0; t < ticks; t++) {
    drive(p, { x: dir.x * (d / ticks) * 1.05, y: t === 0 ? 0.12 : 0.02, z: dir.z * (d / ticks) * 1.05 });
    const back = add(p.location, v3(0, 0.9, 0));
    c.particle("grimoire:ring_dir", back, { color: OR, color2: WH, radius: 1.6 + t * 0.2, dir, life: 1 });
    c.particle("grimoire:ripple_dir", back, { color: WH, radius: 2.2, dir, life: 1.3 });
    yield 1;
  }
  c.particle("grimoire:streak_dir", add(start, v3(0, 1, 0)), { color: GD, dir, speed: 1, count: 1.5 });
  yield 4;
}

// ------------------------------------------------------------------------------------------ P11
export function skylineRail(c: Cast): Routine {
  const p = c.player;
  let dir = c.dir;
  const yp = yawPitchOf(dir);
  if (yp.pitch > -8) dir = norm(add(flatNorm(dir), v3(0, 0.22, 0))); // keep a rising corridor when aiming low
  const startPos = add(p.location, v3(0, 1.0, 0));
  const len0 = c.p("length");
  const free = Math.min(freeDistance(c.dim, startPos, dir, len0), freeDistance(c.dim, add(startPos, v3(0, 0.9, 0)), dir, len0),
    freeDistance(c.dim, add(startPos, v3(0, -0.8, 0)), dir, len0));
  const L = free - 1.6;
  if (L < 4) throw new Fizzle("No room for the Skyline Rail");
  return (function* () {
    const n = Math.max(3, Math.min(c.p("rings"), Math.floor(L / 3.2)));
    const rings: { fx?: Fx; at: V3; passed: boolean }[] = [];
    for (let i = 0; i < n; i++) {
      const at = add(startPos, mul(dir, (L * (i + 0.6)) / n));
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
      const here = add(p.location, v3(0, 1.0, 0));
      const corr = mul(sub(target, here), 0.35);
      drive(p, add(mul(dir, speed), corr));
      for (const r of rings) {
        if (!r.passed && dist(here, r.at) < 2.2) {
          r.passed = true;
          r.fx?.phase(3);
          c.particle("grimoire:ring_dir", r.at, { color: OR, color2: WH, radius: 4.5, dir });
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

// ------------------------------------------------------------------------------------------ P12
export function* barometricOmniscience(c: Cast): Routine {
  const p = c.player;
  const R = c.p("radius");
  const sonar = c.fx("grimoire:fx_p_sonar", add(p.location, v3(0, 1, 0)), { size: 1, phase: 1 });
  const ground = c.fx("grimoire:fx_circle_p", add(p.location, v3(0, 0.07, 0)), { size: 2, variant: 0, phase: 1 });
  c.sound("grimoire.pressure.sonar", p.location, 1.2, 1);
  const markers = new Map<string, { fx?: Fx; e: Entity }>();
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
      let nearest: Entity | undefined;
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
        const name = e.typeId === "minecraft:player" ? (e as Player).name : e.typeId.replace("minecraft:", "").replace(/_/g, " ");
        try {
          if (m.fx?.entity.isValid) m.fx.entity.nameTag = `${rel === "enemy" ? "§c" : "§6"}${name} §7${dm}m`;
        } catch {
          /* ignore */
        }
        // amber outline only the caster sees
        const lo = e.location, hi = e.getHeadLocation();
        const w = 0.45;
        for (const [dx, dz] of [[-w, -w], [w, -w], [-w, w], [w, w]]) {
          for (const y of [lo.y + 0.05, hi.y + 0.25]) particle(c.dim, "grimoire:outline_point", { x: lo.x + dx, y, z: lo.z + dz }, { color: GD, size: 1 }, p);
        }
      }
      const dirTxt = nearest ? compass(sub(nearest.location, p.location)) : "";
      hudFlash(st, `§6Barometric sense§7: §c${hostile} hostile §7· §e${other} other §7· §b${players} players` +
        (nearest ? ` §7| nearest §c${nearest.typeId.replace("minecraft:", "")} ${Math.round(dist(nearest.location, p.location))}m ${dirTxt}` : ""), 14);
    }
    for (const m of markers.values()) if (m.e.isValid) m.fx?.move(add(m.e.getHeadLocation(), v3(0, 0.7, 0)));
    yield 1;
  }
}

function compass(d: V3): string {
  const a = (Math.atan2(d.x, -d.z) * 180) / Math.PI;
  const names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return names[((Math.round(a / 45) % 8) + 8) % 8];
}

// ------------------------------------------------------------------------------------------ P13
export function* equilibriumTheft(c: Cast): Routine {
  const p = c.player;
  const center = p.location;
  const R = c.p("radius");
  const field = c.fx("grimoire:fx_p_field", center, { phase: 1, size: R / 7.5 });
  c.sound("grimoire.pressure.rise", center, 0.9, 2);
  yield 6;
  field?.phase(2);
  for (let t = 0; t < 36; t++) {
    if (t % 6 === 0) c.particle("grimoire:converge", add(p.location, v3(0, 1.5, 0)), { color: OR, color2: WH, radius: R, life: 0.6, count: 1.5 });
    if (t % 3 === 0) {
      for (const e of c.enemies(center, R)) {
        pullToward(e, center, 0.35);
        effect(e, "slowness", 20, 1);
      }
    }
    yield 1;
  }
  field?.dissolve(6);
  const st = stateOf(p);
  st.empowered = { until: system.currentTick + c.p("buffSeconds") * 20, source: "equilibrium" };
  st.hudKey = "";
  hudFlash(st, `§6Equilibrium stolen: your next spell is empowered (x1.6, ${c.p("buffSeconds")}s)`, 50);
  const crystal = c.fx("grimoire:fx_p_crystal", add(p.location, v3(0.8, 2.2, 0)), { phase: 1 });
  c.sound("grimoire.pressure.crystal", p.location, 1, 1);
  let t = 0;
  while (st.empowered && st.empowered.until > system.currentTick) {
    if (!c.ok) return;
    const a = t * 0.08;
    crystal?.move(add(p.location, v3(Math.cos(a) * 0.9, 2.1 + Math.sin(t * 0.15) * 0.1, Math.sin(a) * 0.9)));
    if (t % 40 === 0) c.sound("grimoire.pressure.crystal", p.location, 0.4, 1.2);
    t++;
    yield 1;
  }
  if (st.empowered && st.empowered.until <= system.currentTick) st.empowered = undefined;
  c.particle("grimoire:spark_burst", add(p.location, v3(0, 2, 0)), { color: GD, color2: WH, count: 1.5 });
}

// ------------------------------------------------------------------------------------------ P14
export function* isobaricCitadel(c: Cast): Routine {
  const center = { x: Math.floor(c.feet.x) + 0.5, y: Math.floor(c.feet.y), z: Math.floor(c.feet.z) + 0.5 };
  const R = c.p("radius");
  const set = c.blocks();
  c.fx("grimoire:fx_circle_p", add(center, v3(0, 0.07, 0)), { size: R + 2, variant: 2, phase: 1 });
  const ring = c.fx("grimoire:fx_p_citadel_ring", add(center, v3(0, 9, 0)), { phase: 1, size: R / 9.4 });
  c.sound("grimoire.pressure.rise", center, 1.4, 0.8);
  const columns: { fx?: Fx; at: V3 }[] = [];
  for (let i = 0; i < 8; i++) {
    const ang = (i / 8) * Math.PI * 2 + Math.PI / 8;
    const at = c.ground({ x: center.x + Math.cos(ang) * R, y: center.y + 4, z: center.z + Math.sin(ang) * R }, 10);
    columns.push({ fx: c.fx("grimoire:fx_p_column", at, { phase: 1, size: 1.6 }), at });
    yield 4;
  }
  // walls between columns (octagon), 4 gateways, raised layer by layer
  const wall = new Map<string, V3>();
  for (let i = 0; i < 8; i++) {
    const a = columns[i].at, b = columns[(i + 1) % 8].at;
    const steps = Math.ceil(hdist(a, b) * 2);
    for (let s = 0; s <= steps; s++) {
      if (i % 2 === 0 && s > steps * 0.38 && s < steps * 0.62) continue; // gateway
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
      // incoming projectiles are crushed by the pressure walls
      for (const e of c.dim.getEntities({ location: center, maxDistance: R + 1.5 })) {
        const proj = e.getComponent(EntityProjectileComponent.componentId) as EntityProjectileComponent | undefined;
        if (proj && !(proj.owner && isAllyOrSelf(owner, proj.owner))) {
          c.particle("grimoire:spark_burst", e.location, { color: OR, count: 0.6 });
          try {
            e.remove();
          } catch {
            /* ignore */
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
        const col = columns.reduce((best, cc) => (dist(cc.at, f.location) < dist(best.at, f.location) ? cc : best), columns[0]);
        col.fx?.pulse();
        const from = add(col.at, v3(0, 5.5, 0));
        const to = bodyCenter(f);
        const n = Math.ceil(dist(from, to));
        for (let i = 0; i <= n; i += 2) c.particle("grimoire:ring_dir", lerp(from, to, i / n), { color: OR, color2: WH, radius: 1.4, dir: norm(sub(to, from)), life: 0.6 });
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

// ------------------------------------------------------------------------------------------ P15
export function* thousandAtmospheres(c: Cast): Routine {
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
      /* ignore */
    }
  }
  c.onCleanup(() => {
    for (const pl of fogged) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_p15");
      } catch {
        /* ignore */
      }
    }
  });
  // Phase 1 - Atmospheric Dominion
  c.sound("grimoire.pressure.rise", point, 1.6, 0.6);
  c.shake(point, 40, 0.15, 3);
  for (let t = 0; t < 60; t++) {
    if (t % 10 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        if (t % 20 === 0) c.hit(e, 2);
      }
      c.particle("grimoire:ripple_h", add(point, v3(0, 6 + (t % 30) / 3, 0)), { color: OR, radius: R * 2, life: 2 });
    }
    yield 1;
  }
  sky?.phase(3);
  layers?.phase(3);
  // Phase 2 - Thousandfold Compression: layers collapse one after another (outer first)
  const n = c.p("collapses");
  for (let k = 0; k < n; k++) {
    const r = Math.max(2, R * (1 - k / n));
    c.particle("grimoire:ring_h", add(point, v3(0, 3, 0)), { color: GD, color2: WH, radius: r * 2.2, life: 0.8 });
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
  // Phase 3 - Imperial Release: several expanding fronts, then the final impact
  c.flash(point, 60, { r: 1, g: 0.85, b: 0.6 }, 0.15);
  c.sound("grimoire.pressure.edict", point, 2, 1);
  for (let f = 0; f < 3; f++) {
    c.fx("grimoire:fx_p_front", point, { phase: 1, size: (R / 4) * (0.55 + f * 0.25) });
    shock(c, point, R * (0.6 + f * 0.25), c.p("frontDamage") * (1 - f * 0.3), { knock: 2.2 - f * 0.4, up: 0.9 - f * 0.2, shake: 1.0 - f * 0.25, minK: 0.4 });
    c.particle("grimoire:glow_flash", add(point, v3(0, 2, 0)), { color: WH, size: 12 - f * 3 });
    yield 6;
  }
  c.particle("grimoire:spark_burst", add(point, v3(0, 2, 0)), { color: GD, color2: WH, radius: 4, count: 4 });
  ground?.phase(3);
  yield 20;
  void sky;
}
