import { Entity, EntityDamageCause, EntityTameableComponent, system } from "@minecraft/server";
import type { Cast } from "../context";
import { Fizzle } from "../types";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx, SESSION, SESSION_PROP } from "../../core/fx";
import { OWNER_PROP, bodyCenter, effect, isAllyOrSelf, pullToward, push } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { endBind } from "../../core/status";
import { onHurt } from "../hooks";
import { V3, add, bezier3, dist, flatNorm, len, lerp, mul, norm, rng, rotY, sub, v3, yawPitchOf } from "../../core/vec";
import { drive, fly, freeDistance, nearestEnemies, shock, teleportDestination } from "../kit";

const CR = COLORS.crimson, SC = COLORS.scarlet, BG = COLORS.bloodglow, BU = COLORS.burgundy, RG = COLORS.redgold;

// ------------------------------------------------------------------------------------------ B01
export function* stilettoRain(c: Cast): Routine {
  const p = c.player;
  const formation = c.fx("grimoire:fx_b_stilettos", p.location, { yaw: p.getRotation().y, phase: 1 });
  c.particle("grimoire:droplet_burst", add(p.location, v3(0, 1.6, 0)), { color: CR, color2: SC, radius: 1.5, count: 2 });
  c.sound("grimoire.blood.form", p.location, 1, 1.1);
  for (let t = 0; t < 12; t++) {
    formation?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
  const aim = c.aim(c.p("range"));
  const volleys = c.p("volleys");
  for (let w = 0; w < volleys; w++) {
    formation?.phase(3 + w);
    const foes = nearestEnemies(c, aim.entity ? bodyCenter(aim.entity) : aim.point, 10, 6);
    for (let k = 0; k < 3; k++) {
      const yaw = p.getRotation().y;
      const from = add(p.location, add(rotY(v3((k - 1) * 0.9, 0, 0.4), yaw), v3(0, 1.6 + w * 0.3, 0)));
      const tgt = foes.length ? foes[(w * 3 + k) % foes.length] : undefined;
      const goal = tgt ? bodyCenter(tgt) : add(aim.point, v3((k - 1) * 1.5, 0, (w - 1) * 1.5));
      const dir = norm(sub(goal, from));
      const cl = c.fx("grimoire:fx_b_stiletto", from, { dir, phase: 1 });
      c.run(fly(c, {
        fx: cl, from, dir, speed: 1.9, range: c.p("range") + 4, radius: 0.7, pierce: 1, homing: tgt, homingRate: 0.3,
        trail: "grimoire:trail", trailColor: CR, trailColor2: SC,
        onHit: (e) => {
          c.hit(e, c.p("damage"));
          c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 0.6 });
        },
        onEnd: () => cl?.dissolve(2),
      }), "stiletto");
    }
    c.sound("grimoire.blood.slice", p.location, 1, 1 + w * 0.12);
    for (let t = 0; t < 6; t++) {
      formation?.follow(p).yaw(p.getRotation().y);
      yield 1;
    }
  }
  yield* c.join(60);
}

// ------------------------------------------------------------------------------------------ B02
export function* redCourtGuillotine(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const { yaw } = yawPitchOf(flatNorm(sub(point, c.feet)));
  const g = c.fx("grimoire:fx_b_guillotine", point, { yaw, len: 8.75, phase: 1, size: c.area });
  c.sound("grimoire.blood.form", point, 1.2, 0.8);
  yield 16;
  g?.phase(2);
  for (let t = 0; t < 28; t++) {
    if (t % 4 === 0) c.particle("grimoire:converge", add(point, v3(0, 4.5, 0)), { color: CR, color2: SC, radius: 3, life: 0.5 });
    yield 1;
  }
  g?.phase(3);
  c.sound("grimoire.blood.drop", point, 1.4, 1);
  yield 5;
  g?.phase(4);
  c.shake(point, 24, 0.6, 0.5);
  shock(c, point, c.p("radius"), c.p("damage"), { knock: 0.6, up: 0.3, color: CR, color2: SC, sound: "grimoire.blood.splash", minK: 0.6 });
  c.particle("grimoire:droplet_burst", add(point, v3(0, 1, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  // crescent-shaped crimson cutting waves radiate along the ground
  const n = c.p("waves");
  for (let k = 0; k < n; k++) {
    const dir = rotY(v3(0, 0, 1), (k * 360) / n + yaw);
    const from = add(point, v3(0, 0.6, 0));
    const cr = c.fx("grimoire:fx_b_crescent", from, { dir, phase: 1, size: 1.1 });
    c.run(fly(c, {
      fx: cr, from, dir, speed: 1.0, range: 10 * c.area, radius: 1.4, pierce: Infinity, stopOnBlock: true,
      onHit: (e) => {
        c.hit(e, c.p("waveDamage"));
        effect(e, "slowness", 30, 1);
      },
      onEnd: () => cr?.dissolve(4),
    }), "crescent");
  }
  yield* c.join(40);
  yield 6;
}

// ------------------------------------------------------------------------------------------ B03
export function* sanguineLeviathan(c: Cast): Routine {
  const p = c.player;
  const dir = flatNorm(c.dir);
  const right = rotY(dir, 90);
  const L = c.p("length");
  const start = c.ground(add(p.location, add(mul(dir, 2), v3(0, 2, 0))), 6);
  const end = add(start, mul(dir, L));
  // curved path, bent toward enemies near it
  const foes = nearestEnemies(c, add(start, mul(dir, L / 2)), L / 2 + 4, 3);
  let c1 = add(add(start, mul(dir, L / 3)), mul(right, 6));
  let c2 = add(add(start, mul(dir, (2 * L) / 3)), mul(right, -6));
  if (foes[0]) c1 = lerp(c1, foes[0].location, 0.7);
  if (foes[1]) c2 = lerp(c2, foes[1].location, 0.7);
  const pathAt = (t: number) => {
    const q = bezier3(start, c1, c2, end, t);
    return { x: q.x, y: c.ground(add(q, v3(0, 3, 0)), 8).y + 0.8 + Math.sin(t * Math.PI * 5) * 0.9, z: q.z };
  };
  c.fx("grimoire:fx_circle_b", add(start, v3(0, 0.06, 0)), { size: 2.5, variant: 1, phase: 1 });
  c.particle("grimoire:droplet_burst", add(start, v3(0, 0.5, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  const nseg = c.p("segments");
  const head = c.fx("grimoire:fx_b_serpent_head", start, { phase: 1, size: 1.3 * c.area });
  const segs: Fx[] = [];
  for (let i = 0; i < nseg; i++) {
    const f = c.fx(i === nseg - 1 ? "grimoire:fx_b_serpent_tail" : "grimoire:fx_b_serpent_seg", start, { phase: 1, size: (1.25 - i * 0.04) * c.area });
    if (f) segs.push(f);
  }
  c.sound("grimoire.blood.hiss", start, 1.3, 1);
  const history: V3[] = [start];
  const lastHit = new Map<string, number>();
  const ticks = 50;
  for (let t = 0; t <= ticks; t++) {
    const pos = pathAt(t / ticks);
    const prev = history[history.length - 1];
    history.push(pos);
    head?.move(pos).aim(sub(pos, prev).y === 0 && len(sub(pos, prev)) < 1e-3 ? dir : sub(pos, prev));
    segs.forEach((s, i) => {
      const k = Math.max(0, history.length - 1 - (i + 1) * 2);
      const at = history[k];
      const ahead = history[Math.min(history.length - 1, k + 2)];
      s.move(at).aim(sub(ahead, at).x === 0 && sub(ahead, at).z === 0 ? dir : sub(ahead, at));
    });
    if (t % 2 === 0) {
      for (const body of [pos, ...segs.filter((_, i) => i % 2 === 0).map((s) => s.location)]) {
        for (const e of c.enemies(body, 1.8)) {
          if ((lastHit.get(e.id) ?? -99) > t - 10) continue;
          lastHit.set(e.id, t);
          c.hit(e, c.p("contactDamage"));
          push(e, sub(e.location, body), 0.6, 0.3);
        }
      }
      c.particle("grimoire:droplet_burst", pos, { color: CR, color2: SC, count: 0.3 });
    }
    yield 1;
  }
  // rearing bite
  head?.phase(3);
  const bitePos = history[history.length - 1];
  c.sound("grimoire.blood.bite", bitePos, 1.2, 0.9);
  yield 5;
  const victim = nearestEnemies(c, bitePos, 4, 1)[0];
  if (victim) {
    c.hit(victim, c.p("biteDamage"), { immediate: true });
    push(victim, dir, 1.2, 0.5);
    c.particle("grimoire:droplet_burst", bodyCenter(victim), { color: CR, color2: SC, radius: 1.5, count: 2 });
  }
  yield 6;
  // dissolves into a gigantic crimson wave
  head?.dissolve(6);
  for (const s of segs) s.dissolve(6);
  const wave = c.fx("grimoire:fx_b_tidal", c.ground(add(bitePos, v3(0, 2, 0)), 6), { yaw: yawPitchOf(dir).yaw, phase: 1, size: 0.3 * c.area });
  c.sound("grimoire.blood.burst", bitePos, 1.4, 1);
  for (let t = 0; t < 12; t++) {
    const front = add(bitePos, mul(dir, 1 + t * 0.8));
    wave?.move(c.ground(add(front, v3(0, 2, 0)), 6));
    if (t % 3 === 0) {
      for (const e of c.enemies(front, 3.5)) {
        if ((lastHit.get(e.id) ?? -99) > 1000 + t - 6) continue;
        lastHit.set(e.id, 1000 + t);
        c.hit(e, c.p("waveDamage"));
        push(e, dir, 1.4, 0.45);
      }
      c.particle("grimoire:droplet_burst", add(front, v3(0, 1, 0)), { color: CR, color2: SC, radius: 2, count: 1.5 });
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ B04
export function* thousandBladeCrowns(c: Cast): Routine {
  const p = c.player;
  const n = c.p("crowns");
  const aim = c.aim(c.p("range"));
  const center = aim.entity ? { ...aim.entity.location } : c.ground(aim.point, 8);
  const crowns: { fx?: Fx; target?: Entity; spot: V3 }[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    crowns.push({ fx: c.fx("grimoire:fx_b_crown", add(p.location, v3(Math.cos(a) * 2.6, 3.2, Math.sin(a) * 2.6)), { phase: 1 }), spot: center });
  }
  c.sound("grimoire.blood.crown", p.location, 1.2, 1);
  yield 14;
  const foes = nearestEnemies(c, center, 12, n);
  crowns.forEach((cr, i) => {
    cr.target = foes.length ? foes[i % foes.length] : undefined;
    const a = (i / n) * Math.PI * 2;
    cr.spot = cr.target ? cr.target.location : add(center, v3(Math.cos(a) * 4, 0, Math.sin(a) * 4));
  });
  // spread to the targets
  for (let t = 0; t < 14; t++) {
    for (const cr of crowns) {
      const goal = add(cr.target?.isValid ? cr.target.location : cr.spot, v3(0, 2.8 + (cr.target?.isValid ? cr.target.getHeadLocation().y - cr.target.location.y : 1), 0));
      cr.fx?.move(lerp(cr.fx.location, goal, 0.25));
    }
    yield 1;
  }
  // three cutting attacks each
  for (let s = 0; s < 3; s++) {
    for (const cr of crowns) {
      cr.fx?.pulse();
      const at = cr.target?.isValid ? cr.target.location : cr.spot;
      for (const e of c.enemies(at, 1.8)) c.hit(e, c.p("slashDamage"));
      c.particle("grimoire:spark_burst", add(at, v3(0, 1.2, 0)), { color: SC, color2: BG, radius: 0.8, count: 0.6 });
    }
    c.sound("grimoire.blood.slice", center, 1.2, 0.9 + s * 0.1);
    for (let t = 0; t < 12; t++) {
      for (const cr of crowns) if (cr.target?.isValid) cr.fx?.move(add(cr.target.location, v3(0, cr.target.getHeadLocation().y - cr.target.location.y + 1.2, 0)));
      yield 1;
    }
  }
  // all twelve combine into one enormous royal crown
  const top = add(center, v3(0, 7, 0));
  for (let t = 0; t < 12; t++) {
    for (const cr of crowns) cr.fx?.move(lerp(cr.fx.location, top, 0.3));
    yield 1;
  }
  for (const cr of crowns) cr.fx?.dissolve(4);
  const grand = c.fx("grimoire:fx_b_grand_crown", top, { phase: 1, len: 6, size: c.area });
  c.sound("grimoire.blood.crown", top, 1.6, 0.6);
  c.particle("grimoire:glow_flash", top, { color: BG, size: 5 });
  yield 22;
  grand?.phase(3);
  yield 6;
  c.shake(center, 26, 0.7, 0.5);
  shock(c, center, c.p("finalRadius"), c.p("finalDamage"), { knock: 1.4, up: 0.5, color: SC, color2: RG, sound: "grimoire.blood.burst", minK: 0.5 });
  c.particle("grimoire:spark_burst", add(center, v3(0, 1, 0)), { color: SC, color2: RG, radius: 3, count: 3 });
  yield 14;
}

// ------------------------------------------------------------------------------------------ B05
export function* scarletRoseAegis(c: Cast): Routine {
  const p = c.player;
  const rose = c.fx("grimoire:fx_b_rose_aegis", p.location, { phase: 1 });
  c.sound("grimoire.blood.bloom", p.location, 1.2, 1);
  const cap = c.p("layerCapacity") * c.power;
  const layers = [cap, cap, cap];
  let broken = 0;
  c.ward({
    label: "rose", priority: 30,
    protects: (e) => isAllyOrSelf(p, e) && dist(e.location, p.location) <= 3.2,
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
      rose?.pulse();
      rose?.phase(Math.min(5, 2 + broken));
      c.particle("grimoire:petal_burst", add(info.hurt.location, v3(0, 1.4, 0)), { color: CR, color2: SC, radius: 1.5, count: 1.2 });
      c.particle("grimoire:mist", add(info.hurt.location, v3(0, 1, 0)), { color: CR, color2: BU, radius: 1.2, size: 1, count: 0.6 });
      c.sound("grimoire.blood.absorb", info.hurt.location, 1, 1.1);
    },
  });
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    if (!c.ok) return;
    rose?.follow(p);
    if (t === 18) rose?.phase(2);
    if (t % 25 === 0) c.particle("grimoire:petal_burst", add(p.location, v3(0, 2, 0)), { color: CR, color2: SC, radius: 2, count: 0.4 });
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ B06
export function* royalReprisal(c: Cast): Routine {
  const p = c.player;
  const front = () => add(p.location, add(mul(flatNorm(p.getViewDirection()), 1.1), v3(0, 0.2, 0)));
  const fan = c.fx("grimoire:fx_b_fan", front(), { yaw: p.getRotation().y, phase: 1 });
  c.sound("grimoire.blood.form", p.location, 1, 1.2);
  let left = c.p("absorbs");
  const lastCounter = new Map<string, number>();
  c.ward({
    label: "reprisal", priority: 22,
    protects: (e) => e.id === p.id && left > 0,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause)) return info.damage;
      left--;
      return 0;
    },
    react: (info, absorbed) => {
      fan?.pulse();
      c.sound("grimoire.blood.absorb", p.location, 1, 0.9);
      const src = info.projectile ? (info.attacker ?? undefined) : info.attacker;
      if (!src || !src.isValid || src.id === p.id) return;
      const now = system.currentTick;
      if ((lastCounter.get(src.id) ?? -99) > now - 10) return; // recursion / spam guard
      lastCounter.set(src.id, now);
      const dmg = Math.max(c.p("lanceDamage"), absorbed * 1.5);
      system.runTimeout(() => {
        if (!p.isValid || !src.isValid) return;
        for (let k = 0; k < 3; k++) {
          const from = add(front(), add(rotY(v3((k - 1) * 0.8, 0, 0), p.getRotation().y), v3(0, 1.2 + (k % 2) * 0.4, 0)));
          const dir = norm(sub(bodyCenter(src), from));
          const l = c.fx("grimoire:fx_b_lance", from, { dir, phase: 1 });
          c.run(fly(c, {
            fx: l, from, dir, speed: 1.8, range: 30, radius: 0.7, pierce: 1, homing: src, homingRate: 0.4,
            onHit: (e) => {
              c.hit(e, dmg / 3, { kind: "reflect" });
              c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 0.6 });
            },
            onEnd: () => l?.dissolve(2),
          }), "counter");
        }
        c.sound("grimoire.blood.lance", p.location, 1, 1.1);
      }, 4);
    },
  });
  for (let t = 0; t < c.p("duration") * 20 && left > 0; t++) {
    if (!c.ok) return;
    fan?.move(front()).yaw(p.getRotation().y);
    if (t === 12) fan?.phase(2);
    yield 1;
  }
  yield* c.join(30);
}

// ------------------------------------------------------------------------------------------ B07
export function veinboundMarionette(c: Cast): Routine {
  const a = c.aim(c.p("range"));
  const center0 = a.entity ? a.entity.location : a.point;
  const list = nearestEnemies(c, center0, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity!.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to bind in range");
  return (function* () {
    const mid = targets.reduce((acc, e) => add(acc, mul(e.location, 1 / targets.length)), v3(0, 0, 0));
    const ground = c.ground(add(mid, v3(0, 2, 0)), 6);
    const sky = add(ground, v3(0, 6, 0));
    c.fx("grimoire:fx_circle_b", sky, { size: 4, variant: 1, phase: 1 });
    c.sound("grimoire.blood.form", sky, 1.2, 0.9);
    const dur = c.p("duration") * 20;
    const items = targets.map((t) => ({
      t,
      thread: c.fx("grimoire:fx_b_thread", sky, { phase: 1, len: 0.1 }),
      b: c.bind(t, dur + 10, { pull: ground, pullSpeed: 0.07, slowAmp: 6 }),
    }));
    // threads descend and attach
    for (let s = 0; s < 10; s++) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        const to = add(it.t.location, v3(0, it.t.getHeadLocation().y - it.t.location.y + 0.2, 0));
        it.thread?.aim(sub(to, sky)).length((dist(sky, to) * (s + 1)) / 10);
      }
      yield 1;
    }
    c.sound("grimoire.blood.snap", sky, 0.8, 0.6);
    for (let s = 0; s < dur; s++) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        const to = add(it.t.location, v3(0, it.t.getHeadLocation().y - it.t.location.y + 0.2, 0));
        it.thread?.aim(sub(to, sky)).length(dist(sky, to));
        if (s % 20 === 0) {
          c.hit(it.t, c.p("dps"));
          it.thread?.pulse();
        }
      }
      yield 1;
    }
    for (const it of items) {
      endBind(it.b, false);
      it.thread?.dissolve(3);
      if (it.t.isValid) c.particle("grimoire:droplet_burst", bodyCenter(it.t), { color: CR, color2: SC, count: 0.5 });
    }
    c.sound("grimoire.blood.snap", sky, 1.2, 1.2);
    yield 6;
  })();
}

// ------------------------------------------------------------------------------------------ B08
export function* crimsonThornGarden(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  c.fx("grimoire:fx_b_roots", add(point, v3(0, 0.04, 0)), { phase: 1, size: R / 9.4 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.08, 0)), { size: R, variant: 1, phase: 1 });
  c.sound("grimoire.blood.form", point, 1.4, 0.7);
  const roses: { fx?: Fx; at: V3 }[] = [];
  for (let k = 0; k < 6; k++) {
    const at = k === 0 ? point : c.ground(add(point, v3(Math.cos((k / 5) * 6.283) * R * 0.62, 3, Math.sin((k / 5) * 6.283) * R * 0.62)), 8);
    roses.push({ fx: c.fx("grimoire:fx_b_rose", at, { phase: 1, size: k === 0 ? 1.2 : 0.85, yaw: k * 60 }), at });
    yield 3;
  }
  c.sound("grimoire.blood.bloom", point, 1.4, 0.9);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        c.hit(e, 1);
      }
    }
    if (t % 40 === 20) {
      for (const e of nearestEnemies(c, point, R, 6)) {
        c.fx("grimoire:fx_b_thorns", e.location, { phase: 1, yaw: t * 37 % 360, size: 0.9 });
        c.hit(e, c.p("thornDamage"));
        push(e, v3(0, 0, 0), 0, 0.4);
        effect(e, "slowness", 40, 2);
      }
      c.sound("grimoire.blood.thorn", point, 1.1, 1);
    }
    if (t % 60 === 50) {
      for (const r of roses) {
        r.fx?.pulse();
        c.fx("grimoire:fx_b_wave_ring", add(r.at, v3(0, 0.3, 0)), { phase: 1, size: 1 });
        for (const e of c.enemies(r.at, 4.2)) c.hit(e, c.p("waveDamage"));
      }
      c.sound("grimoire.blood.slice", point, 1.2, 0.8);
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ B09
export function* hematicMaelstrom(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const sea = c.fx("grimoire:fx_b_sea", add(point, v3(0, 0.05, 0)), { phase: 1, size: R / 8 });
  c.sound("grimoire.blood.splash", point, 1.2, 0.7);
  yield 20;
  sea?.phase(3);
  const whirl = c.fx("grimoire:fx_b_whirl", add(point, v3(0, 0.12, 0)), { phase: 1, size: R / 7.5 });
  c.sound("grimoire.blood.whirl", point, 1.4, 1);
  for (let t = 0; t < c.p("pullTicks"); t++) {
    for (const e of c.enemies(point, R + 2)) pullToward(e, point, 0.3);
    if (t % 20 === 0) for (const e of c.enemies(point, R)) c.hit(e, c.p("dps"));
    if (t % 5 === 0) c.particle("grimoire:converge", add(point, v3(0, 0.6, 0)), { color: CR, color2: SC, radius: R, life: 0.8 });
    yield 1;
  }
  whirl?.dissolve(8);
  const pillar = c.fx("grimoire:fx_b_pillar", point, { phase: 1, size: 1.3 * c.area });
  c.sound("grimoire.blood.form", point, 1.4, 0.6);
  yield 18;
  pillar?.phase(3);
  c.shake(point, 24, 0.6, 0.5);
  shock(c, point, R, c.p("burstDamage"), { knock: 0.6, up: 1.0, color: CR, color2: SC, sound: "grimoire.blood.burst", minK: 0.5 });
  for (let t = 0; t < 40; t++) {
    if (t % 5 === 0) c.particle("grimoire:blood_rain", add(point, v3(0, 2, 0)), { color: CR, color2: SC, radius: R, count: 0.8 });
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ B10
export function bloodstep(c: Cast): Routine {
  const dest = teleportDestination(c, c.p("range"));
  if (!dest) throw new Fizzle("No safe place to reform");
  return (function* () {
    const p = c.player;
    const from = p.location;
    // silhouette dissolves into blood droplets and ruby fragments
    for (const y of [0.4, 1.0, 1.6]) c.particle("grimoire:droplet_burst", add(from, v3(0, y, 0)), { color: CR, color2: SC, radius: 0.6, count: 1 });
    c.fx("grimoire:fx_b_fragments", from, { phase: 1 });
    c.sound("grimoire.blood.step", from, 1, 1);
    yield 3;
    p.tryTeleport(dest, { checkForBlocks: true, rotation: p.getRotation(), keepVelocity: false });
    grantFallImmunity(p.id, 30);
    const reform = c.fx("grimoire:fx_b_fragments", dest, { phase: 1 });
    reform?.phase(3);
    c.fx("grimoire:fx_circle_b", add(dest, v3(0, 0.06, 0)), { size: 1.3, variant: 1, phase: 1 });
    c.particle("grimoire:fragment_burst", add(dest, v3(0, 1, 0)), { color: SC, color2: BG, radius: 0.8, count: 1 });
    c.sound("grimoire.blood.step", dest, 1, 1.3);
    yield 20;
  })();
}

// ------------------------------------------------------------------------------------------ B11
export function* arterialCurrent(c: Cast): Routine {
  const p = c.player;
  let dir = norm(add(c.dir, v3(0, 0.15, 0)));
  const ribbons: { fx?: Fx; born: number }[] = [];
  c.sound("grimoire.blood.flow", p.location, 1.2, 1);
  grantFallImmunity(p.id, 260);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (!c.ok) break;
    // the current curves gradually toward where the rider looks
    dir = norm(lerp(dir, p.getViewDirection(), 0.12));
    let mv = { x: 0, y: 0 };
    try {
      mv = p.inputInfo.getMovementVector();
    } catch {
      /* ignore */
    }
    const speed = c.p("speed") * (mv.y > 0.3 ? 1.3 : mv.y < -0.3 ? 0.45 : 1);
    const here = add(p.location, v3(0, 0.9, 0));
    if (freeDistance(c.dim, here, dir, 2.5) < 2.2) dir = norm(add(dir, v3(0, 0.6, 0))); // flow over obstacles
    drive(p, mul(dir, speed));
    grantFallImmunity(p.id, 40);
    if (t % 2 === 0) {
      const at = add(p.location, add(mul(dir, 2.4), v3(0, -0.3, 0)));
      ribbons.push({ fx: c.fx("grimoire:fx_b_ribbon", at, { dir, phase: 1, size: 1.1 }), born: t });
      if (t % 20 === 10) {
        const side = rotY(flatNorm(dir), t % 40 === 10 ? 35 : -35);
        ribbons.push({ fx: c.fx("grimoire:fx_b_ribbon", add(at, mul(side, 1.5)), { dir: side, phase: 1, size: 0.7 }), born: t - 14 });
      }
    }
    for (let i = ribbons.length - 1; i >= 0; i--) {
      if (t - ribbons[i].born > 26 || ribbons.length > 18) {
        const r = ribbons.splice(i, 1)[0];
        if (r.fx) c.particle("grimoire:droplet_burst", r.fx.location, { color: CR, color2: SC, count: 0.3 });
        r.fx?.dissolve(5);
      }
    }
    if (t % 10 === 0) c.sound("grimoire.blood.flow", p.location, 0.5, 1.1);
    yield 1;
  }
  effect(p, "slow_falling", 60, 0);
  grantFallImmunity(p.id, 120);
  for (const r of ribbons) {
    if (r.fx) c.particle("grimoire:droplet_burst", r.fx.location, { color: CR, color2: SC, count: 0.4 });
    r.fx?.dissolve(6);
  }
  yield 6;
}

// ------------------------------------------------------------------------------------------ B12
function act(e: Entity, v: number): void {
  try {
    if (e.isValid) e.setProperty("grimoire:act", v);
  } catch {
    /* ignore */
  }
}

export function* royalStag(c: Cast): Routine {
  const p = c.player;
  const at = c.ground(add(p.location, add(rotY(v3(2.5, 0, 1), p.getRotation().y), v3(0, 2, 0))), 6);
  c.fx("grimoire:fx_circle_b", add(at, v3(0, 0.06, 0)), { size: 2.6, variant: 2, phase: 1 });
  c.particle("grimoire:droplet_burst", add(at, v3(0, 1.5, 0)), { color: CR, color2: SC, radius: 2, count: 3 });
  let stag: Entity;
  try {
    stag = c.dim.spawnEntity("grimoire:royal_stag", at, { initialRotation: p.getRotation().y });
  } catch {
    throw new Fizzle("The stag could not form here");
  }
  stag.setDynamicProperty(OWNER_PROP, p.id);
  stag.setDynamicProperty(SESSION_PROP, SESSION);
  stag.addTag("grimoire_summon");
  try {
    (stag.getComponent(EntityTameableComponent.componentId) as EntityTameableComponent | undefined)?.tame(p);
  } catch {
    /* ignore */
  }
  act(stag, 4);
  c.sound("grimoire.blood.stag", at, 1.4, 1);
  c.onCleanup(() => {
    if (!stag.isValid) return;
    act(stag, 7);
    c.particle("grimoire:droplet_burst", add(stag.location, v3(0, 1.5, 0)), { color: CR, color2: SC, radius: 1.5, count: 2 });
    system.runTimeout(() => {
      try {
        if (stag.isValid) stag.remove();
      } catch {
        /* ignore */
      }
    }, 24);
  });
  // protective blood shockwave when the owner is struck
  let lastWave = -999;
  const wave = (why: string) => {
    if (!stag.isValid || system.currentTick - lastWave < 60) return;
    lastWave = system.currentTick;
    act(stag, 3);
    system.runTimeout(() => act(stag, 0), 20);
    shock(c, p.location, 5, c.p("waveDamage"), { knock: 1.4, up: 0.4, color: CR, color2: SC, sound: "grimoire.blood.burst" });
    effect(p, "absorption", 200, 0);
    void why;
  };
  c.ward({ label: "stag", priority: 1, protects: (e) => e.id === p.id, absorb: (i) => i.damage, react: () => wave("hit") });
  yield 28;
  act(stag, 0);
  const total = c.p("duration") * 20;
  let step = 0;
  for (let t = 0; t < total; t++) {
    if (!c.ok || !stag.isValid) break;
    if (dist(stag.location, p.location) > 28) {
      try {
        stag.teleport(add(p.location, v3(1.5, 0.5, 1.5)));
      } catch {
        /* ignore */
      }
    }
    // glowing crimson hoofprints
    const v = stag.getVelocity();
    if (Math.hypot(v.x, v.z) > 0.05 && t % 4 === 0) {
      step++;
      const side = rotY(flatNorm(v), 90);
      const foot = add(stag.location, add(mul(side, step % 2 ? 0.35 : -0.35), v3(0, 0.05, 0)));
      c.particle("grimoire:hoofprint", foot, { color: BG, size: 1, dir: flatNorm(v) });
    }
    // charge attack every 5 seconds
    if (t % 100 === 40) {
      const foe = nearestEnemies(c, stag.location, 16, 1)[0];
      if (foe) {
        act(stag, 5);
        c.sound("grimoire.blood.stag", stag.location, 1.1, 1.2);
        yield 20;
        if (!stag.isValid) break;
        act(stag, 6);
        const hitIds = new Set<string>();
        for (let s = 0; s < 18 && stag.isValid; s++) {
          const goal = foe.isValid ? foe.location : stag.location;
          const d = sub(goal, stag.location);
          if (len(flatNorm(d)) > 0 && Math.hypot(d.x, d.z) > 1.2) {
            try {
              stag.clearVelocity();
              stag.applyImpulse(add(mul(flatNorm(d), 0.95), v3(0, 0.02, 0)));
            } catch {
              /* ignore */
            }
          }
          for (const e of c.enemies(stag.location, 1.9)) {
            if (hitIds.has(e.id)) continue;
            hitIds.add(e.id);
            c.hit(e, c.p("chargeDamage"));
            push(e, sub(e.location, stag.location), 1.8, 0.6);
            c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, radius: 1, count: 1 });
            c.sound("grimoire.blood.bite", e.location, 1, 0.8);
          }
          if (s % 3 === 0) c.particle("grimoire:hoofprint", add(stag.location, v3(0, 0.05, 0)), { color: BG, size: 1.2 });
          yield 1;
        }
        act(stag, 0);
      }
    }
    // defensive magic when enemies crowd the owner
    if (t % 80 === 70 && c.enemies(p.location, 5).length > 0) wave("crowd");
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ B13
export function sovereignsPulse(c: Cast): Routine {
  const a = c.aim(30);
  const marked = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, 10, c.p("targets"));
  if (a.entity && !marked.find((e) => e.id === a.entity!.id)) marked.unshift(a.entity);
  const list = marked.slice(0, c.p("targets"));
  if (!list.length) throw new Fizzle("No enemy to mark");
  return (function* () {
    const sigils = new Map<string, Fx | undefined>();
    for (const e of list) sigils.set(e.id, c.fx("grimoire:fx_b_heart_sigil", add(e.getHeadLocation(), v3(0, 0.9, 0)), { phase: 1 }));
    const links = new Map<string, Fx | undefined>();
    const key = (x: Entity, y: Entity) => (x.id < y.id ? `${x.id}|${y.id}` : `${y.id}|${x.id}`);
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) links.set(key(list[i], list[j]), c.fx("grimoire:fx_b_thread", list[i].location, { phase: 1, len: 0.1 }));
    const alive = () => list.filter((e) => e.isValid);
    // damage sharing (recursion-proof: transfers are applied directly and suppressed by id + tick)
    const suppress = new Map<string, number>();
    const share = c.p("share");
    const owner = c.player;
    const off = onHurt({
      ownerId: c.ownerId,
      watch: new Set(list.map((e) => e.id)),
      fn: (victim, damage, cause) => {
        const s = suppress.get(victim.id);
        if (s !== undefined && system.currentTick - s <= 1 && cause === EntityDamageCause.magic) {
          suppress.delete(victim.id);
          return;
        }
        const others = alive().filter((o) => o.id !== victim.id);
        if (!others.length || damage <= 0) return;
        system.run(() => {
          for (const o of others) {
            if (!o.isValid) continue;
            suppress.set(o.id, system.currentTick);
            try {
              o.applyDamage(damage * share, { cause: EntityDamageCause.magic, damagingEntity: owner.isValid ? owner : undefined });
            } catch {
              /* ignore */
            }
            const l = links.get(key(victim, o));
            l?.pulse();
            const from = bodyCenter(victim), to = bodyCenter(o);
            for (let k = 1; k <= 4; k++) c.particle("grimoire:heart_pulse", lerp(from, to, k / 5), { color: BG, size: 0.5, life: 0.6 });
          }
          c.sound("grimoire.blood.heart", victim.location, 0.9, 1.2);
        });
      },
    });
    c.onCleanup(off);
    c.sound("grimoire.blood.heart_big", list[0].location, 1.2, 1);
    yield 8;
    for (const e of list) if (e.isValid) c.hit(e, c.p("initialDamage"), { immediate: true });
    const total = c.p("duration") * 20;
    for (let t = 0; t < total; t++) {
      const live = alive();
      if (!live.length) break;
      for (const e of list) {
        const s = sigils.get(e.id);
        if (!e.isValid) {
          s?.dissolve(4);
          sigils.delete(e.id);
          continue;
        }
        s?.move(add(e.getHeadLocation(), v3(0, 0.9, 0)));
      }
      for (let i = 0; i < list.length; i++) {
        for (let j = i + 1; j < list.length; j++) {
          const l = links.get(key(list[i], list[j]));
          if (!l) continue;
          if (!list[i].isValid || !list[j].isValid) {
            l.dissolve(3);
            links.delete(key(list[i], list[j]));
            continue;
          }
          const from = bodyCenter(list[i]), to = bodyCenter(list[j]);
          l.move(from).aim(sub(to, from)).length(dist(from, to));
        }
      }
      if (t % 20 === 0) c.sound("grimoire.blood.heart", live[0].location, 0.6, 1);
      yield 1;
    }
  })();
}

// ------------------------------------------------------------------------------------------ B14
export function* scarletSea(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const dir = flatNorm(sub(point, c.feet));
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.1, 0)), { size: R, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_b", add(point, add(mul(rotY(dir, 90), R * 0.6), v3(0, 8, 0))), { size: R * 0.35, variant: 1, phase: 1, pitch: 30 });
  c.fx("grimoire:fx_circle_b", add(point, add(mul(rotY(dir, -90), R * 0.6), v3(0, 8, 0))), { size: R * 0.35, variant: 1, phase: 1, pitch: -30 });
  const sea = c.fx("grimoire:fx_b_sea", add(point, v3(0, 0.12, 0)), { phase: 1, size: R / 8 });
  const players = c.dim.getPlayers({ location: point, maxDistance: R + 8 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:scarlet_sea grimoire_b14");
    } catch {
      /* ignore */
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_b14");
      } catch {
        /* ignore */
      }
    }
  });
  c.sound("grimoire.blood.whirl", point, 1.6, 0.6);
  const r = rng(system.currentTick + 5);
  const roses: { fx?: Fx; at: V3 }[] = [];
  for (let k = 0; k < 4; k++) {
    const at = c.ground(add(point, v3(Math.cos((k / 4) * 6.283 + 0.4) * R * 0.55, 3, Math.sin((k / 4) * 6.283 + 0.4) * R * 0.55)), 8);
    roses.push({ fx: c.fx("grimoire:fx_b_rose", at, { phase: 1, size: 1.7, yaw: k * 90 }), at });
  }
  const total = c.p("duration") * 20;
  const pillars: { fx?: Fx; at: V3; born: number }[] = [];
  for (let t = 0; t < total - 60; t++) {
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 30, 1);
        c.hit(e, 1);
      }
    }
    if (t % 50 === 10 && pillars.length < 6) {
      const ang = r() * Math.PI * 2, rr = Math.sqrt(r()) * R * 0.8;
      const at = c.ground(add(point, v3(Math.cos(ang) * rr, 3, Math.sin(ang) * rr)), 8);
      pillars.push({ fx: c.fx("grimoire:fx_b_pillar", at, { phase: 1, size: 0.8 }), at, born: t });
      for (const e of c.enemies(at, 2.6)) {
        c.hit(e, 8);
        push(e, v3(0, 0, 0), 0, 0.9);
      }
      c.sound("grimoire.blood.burst", at, 1, 1.2);
    }
    for (const pl of pillars) {
      if (t - pl.born === 60) pl.fx?.phase(3);
    }
    if (t % 80 === 40) {
      for (const rs of roses) {
        rs.fx?.pulse();
        for (const e of c.enemies(rs.at, 6)) effect(e, "slowness", 60, 2);
      }
    }
    if (t % 60 === 30) {
      // blood waves shaped like monstrous creatures lunge at enemies
      for (const e of nearestEnemies(c, point, R, 3)) {
        const side = rotY(flatNorm(sub(e.location, point)), 160);
        const at = c.ground(add(e.location, add(mul(side, 2.2), v3(0, 2, 0))), 6);
        const beast = c.fx("grimoire:fx_b_beast", at, { dir: sub(e.location, at), phase: 1, size: 0.75 });
        c.run((function* () {
          yield 12;
          beast?.pulse();
          yield 6;
          if (e.isValid) {
            c.hit(e, c.p("beastDamage"));
            pullToward(e, at, 0.8);
            c.particle("grimoire:droplet_burst", bodyCenter(e), { color: CR, color2: SC, count: 1 });
          }
          yield 14;
          beast?.dissolve(8);
        })(), "beast");
      }
      c.sound("grimoire.blood.hiss", point, 1.2, 0.8);
    }
    yield 1;
  }
  // the whole sea gathers into an enormous final tidal wave
  sea?.phase(3);
  const startPos = add(point, mul(dir, -R));
  const tidal = c.fx("grimoire:fx_b_tidal", c.ground(add(startPos, v3(0, 3, 0)), 8), { yaw: yawPitchOf(dir).yaw, phase: 1, size: R / 13 });
  c.sound("grimoire.blood.storm", point, 1.8, 0.8);
  const hit = new Set<string>();
  for (let t = 0; t < 40; t++) {
    const front = add(startPos, mul(dir, (2 * R * t) / 40));
    tidal?.move(c.ground(add(front, v3(0, 3, 0)), 8));
    for (const e of c.enemies(front, R * 0.6)) {
      if (hit.has(e.id)) continue;
      const along = (e.location.x - front.x) * dir.x + (e.location.z - front.z) * dir.z;
      if (Math.abs(along) > 2.5) continue;
      hit.add(e.id);
      c.hit(e, c.p("waveDamage"));
      push(e, dir, 2.4, 0.7);
    }
    if (t % 4 === 0) c.particle("grimoire:droplet_burst", add(front, v3(0, 2, 0)), { color: CR, color2: SC, radius: 3, count: 2 });
    yield 1;
  }
  c.shake(point, R * 2, 0.7, 0.6);
  yield 10;
}

// ------------------------------------------------------------------------------------------ B15
export function* crimsonMoonHeart(c: Cast): Routine {
  const p = c.player;
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const heartPos = add(point, v3(0, 12, 0));
  const players = c.dim.getPlayers({ location: point, maxDistance: 64 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:crimson_moon grimoire_b15");
    } catch {
      /* ignore */
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_b15");
      } catch {
        /* ignore */
      }
    }
  });
  // Phase 1 - The Crimson Awakening
  const book = c.fx("grimoire:fx_b_book", add(p.location, v3(0, 2.2, 0)), { phase: 1, yaw: p.getRotation().y });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 22, 0)), { size: R * 1.2, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 16, 0)), { size: R * 0.7, variant: 0, phase: 1, pitch: 18 });
  c.fx("grimoire:fx_circle_b", add(point, v3(0, 0.1, 0)), { size: R, variant: 1, phase: 1 });
  c.flash(point, 64, { r: 0.6, g: 0.02, b: 0.06 }, 0.4);
  for (let t = 0; t < 20; t++) {
    book?.move(add(p.location, v3(0, 2.2 + t * 0.08, 0))).yaw(p.getRotation().y);
    yield 1;
  }
  const heart = c.fx("grimoire:fx_b_heart", heartPos, { phase: 1, size: 1.6 * c.area });
  c.sound("grimoire.blood.heart_big", heartPos, 2, 0.8);
  for (let t = 0; t < 70; t++) {
    book?.move(add(p.location, v3(0, 3.8, 0))).yaw(p.getRotation().y);
    if (t % 20 === 10) {
      // each heartbeat releases an expanding crimson pulse
      heart?.phase(2);
      c.sound("grimoire.blood.heart_big", heartPos, 2, 1);
      c.particle("grimoire:ring_h", add(point, v3(0, 0.5, 0)), { color: CR, color2: BG, radius: R * 2.2, life: 1.2 });
      c.particle("grimoire:heart_pulse", heartPos, { color: BG, size: 6, life: 1 });
      for (const e of c.enemies(point, R)) c.hit(e, c.p("pulseDamage"));
      c.shake(point, R * 2, 0.2, 0.3);
    }
    yield 1;
  }
  // Phase 2 - The Emperor's Circulation: vessels branch out; lances, thorn cages and liquid hands attack
  const ends: V3[] = [];
  const vessels: Fx[] = [];
  for (let k = 0; k < 8; k++) {
    const end = c.ground(add(point, v3(Math.cos((k / 8) * 6.283) * R * 0.75, 6, Math.sin((k / 8) * 6.283) * R * 0.75)), 14);
    ends.push(end);
    const v = c.fx("grimoire:fx_b_vessel", heartPos, { dir: sub(end, heartPos), len: dist(heartPos, end), phase: 1, size: 1.6 });
    if (v) vessels.push(v);
  }
  c.sound("grimoire.blood.flow", heartPos, 1.6, 0.7);
  yield 12;
  const r = rng(system.currentTick);
  for (let cycle = 0; cycle < 8; cycle++) {
    const foes = nearestEnemies(c, point, R, 6);
    const kind = cycle % 3;
    for (const e of foes.slice(0, 3)) {
      if (kind === 0) {
        const from = add(ends[Math.floor(r() * ends.length)], v3(0, 1, 0));
        const dir = norm(sub(bodyCenter(e), from));
        const l = c.fx("grimoire:fx_b_lance", from, { dir, phase: 1, size: 1.4 });
        c.run(fly(c, {
          fx: l, from, dir, speed: 2.0, range: R * 2.2, radius: 0.8, pierce: 2, homing: e, homingRate: 0.4,
          onHit: (x) => c.hit(x, c.p("attackDamage")),
          onEnd: () => l?.dissolve(2),
        }), "lance");
      } else if (kind === 1) {
        c.fx("grimoire:fx_b_cage", e.location, { phase: 1, size: Math.max(1, (e.getHeadLocation().y - e.location.y) / 1.5) });
        c.bind(e, 40, {});
        c.hit(e, c.p("attackDamage") * 0.8);
      } else {
        const hand = c.fx("grimoire:fx_b_hand", c.ground(add(e.location, v3(0, 2, 0)), 6), { phase: 1, yaw: r() * 360, size: 0.9 });
        c.run((function* () {
          yield 10;
          hand?.phase(2);
          if (e.isValid) {
            c.hit(e, c.p("attackDamage") * 1.4);
            c.bind(e, 30, {});
          }
          yield 20;
          hand?.dissolve(8);
        })(), "hand");
      }
    }
    for (const v of vessels) v.pulse();
    heart?.phase(2);
    c.sound(kind === 0 ? "grimoire.blood.lance" : kind === 1 ? "grimoire.blood.thorn" : "grimoire.blood.splash", point, 1.3, 1);
    yield 15;
  }
  // Phase 3 - The Final Heartbeat
  heart?.phase(3);
  for (const v of vessels) v.phase(3);
  c.sound("grimoire.blood.heart", heartPos, 0.4, 0.5);
  yield 24;
  heart?.phase(4);
  c.flash(point, 80, { r: 1, g: 0.1, b: 0.12 }, 0.2);
  c.sound("grimoire.blood.heart_big", heartPos, 2, 0.6);
  c.sound("grimoire.blood.shatter", heartPos, 2, 0.8);
  c.shake(point, R * 3, 1, 0.8);
  shock(c, point, R, c.p("finalDamage"), { knock: 2.2, up: 0.8, color: CR, color2: BG, minK: 0.35 });
  for (let k = 0; k < 3; k++) c.particle("grimoire:fragment_burst", add(heartPos, v3(0, k - 1, 0)), { color: SC, color2: BG, radius: 4 + k * 2, count: 4 });
  book?.dissolve(10);
  // a gigantic crimson storm descends
  for (let t = 0; t < 60; t++) {
    if (t % 4 === 0) c.particle("grimoire:blood_rain", add(point, v3(0, 8, 0)), { color: CR, color2: SC, radius: R, count: 1.2 });
    if (t % 20 === 0) {
      for (const e of c.enemies(point, R)) c.hit(e, 3);
      c.flash(point, R * 2, { r: 0.8, g: 0.05, b: 0.08 }, 0.02);
      c.sound("grimoire.blood.storm", point, 1.2, 1 + t / 100);
    }
    yield 1;
  }
  // several expanding red-gold rings before the environment is restored
  for (let k = 0; k < 4; k++) {
    c.particle("grimoire:ring_h", add(point, v3(0, 0.6 + k * 1.5, 0)), { color: RG, color2: COLORS.gold, radius: R * (1 + k * 0.4), life: 1.6 });
    c.sound("grimoire.blood.crown", point, 1, 0.7 + k * 0.15);
    yield 8;
  }
  yield 10;
}

