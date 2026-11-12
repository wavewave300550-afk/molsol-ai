import { ButtonState, Entity, EntityProjectileComponent, EntityTameableComponent, InputButton, Player, system, world } from "@minecraft/server";
import type { Cast, Prep } from "../context";
import { Fizzle, schoolOfItem } from "../types";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx } from "../../core/fx";
import { OWNER_PROP, bodyCenter, effect, isAllyOrSelf, livingNear, push } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { bind, endBind } from "../../core/status";
import { flash as hudFlash, stateOf } from "../../core/state";
import { SESSION, SESSION_PROP } from "../../core/fx";
import { V3, add, dist, dot, flatNorm, len, lerp, mul, norm, rng, rotY, sub, v3, yawPitchOf } from "../../core/vec";
import { drive, fly, nearestEnemies, shock, teleportDestination } from "../kit";
import { grounded, lower, mazeColumns, raise } from "../structures";

const ICE = COLORS.ice, WH = COLORS.white, CY = COLORS.cyan, SA = COLORS.sapphire;

function freeze(c: Cast, e: Entity, ticks: number): void {
  c.bind(e, ticks, { shell: "grimoire:fx_i_shell", shellInit: { size: Math.max(0.8, Math.min(2.4, (e.getHeadLocation().y - e.location.y) / 1.6)) } });
  effect(e, "mining_fatigue", ticks, 2);
  c.particle("grimoire:snow_burst", bodyCenter(e), { color: ICE, color2: WH, count: 0.8 });
}

// ------------------------------------------------------------------------------------------ I01
export function sovereignLancePrepare(p: Prep): void {
  const head = p.player.getHeadLocation();
  p.fx("grimoire:fx_i_spear", add(head, v3(0, 1.6, 0)), { dir: p.player.getViewDirection(), phase: 1 });
  p.particle("grimoire:converge", add(head, v3(0, 1.6, 0)), { color: ICE, color2: WH, radius: 3, life: 0.8, count: 2 });
  p.sound("grimoire.ice.form", head, 1, 1);
}

export function* sovereignLance(c: Cast): Routine {
  const spear = c.adopted.find((f) => f.type === "grimoire:fx_i_spear") ?? c.fx("grimoire:fx_i_spear", add(c.origin, v3(0, 1.6, 0)), { dir: c.dir, phase: 2 });
  if (spear) {
    const i = c.adopted.indexOf(spear);
    if (i >= 0) c.adopted.splice(i, 1);
    c.fxs.push(spear);
  }
  const from = add(c.origin, v3(0, 1.6, 0));
  const a = c.aim(c.p("range"));
  const dir = norm(sub(a.point, from));
  spear?.aim(dir).phase(3);
  c.sound("grimoire.ice.release", from, 1.2, 0.9);
  let end = from;
  yield* fly(c, {
    fx: spear, from, dir, speed: c.p("speed"), range: c.p("range"), radius: 0.9, pierce: c.p("pierce"),
    onHit: (e, at) => {
      c.hit(e, c.p("damage"));
      effect(e, "slowness", 60, 2);
      c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, count: 0.8 });
      c.sound("grimoire.ice.crack", at);
    },
    onTick: (pos, i) => {
      if (i % 2 === 0) c.particle("grimoire:snow_burst", pos, { color: ICE, color2: WH, radius: 0.4, count: 0.4 });
    },
    onEnd: (pos) => {
      end = pos;
    },
  });
  spear?.dissolve(4);
  // detonation into enormous ice spikes
  const ground = c.ground(add(end, v3(0, 1, 0)), 6);
  c.sound("grimoire.ice.impact", ground, 1.3, 1);
  c.shake(ground, 16, 0.35, 0.4);
  const n = c.p("spikes");
  for (let k = 0; k <= n; k++) {
    const at = k === 0 ? ground : c.ground(add(ground, v3(Math.cos((k / n) * 6.283) * 2.6 * c.area, 1, Math.sin((k / n) * 6.283) * 2.6 * c.area)), 5);
    const sp = c.fx("grimoire:fx_i_spike", at, { yaw: k * 47, size: k === 0 ? 1.3 * c.area : (0.7 + (k % 3) * 0.15) * c.area, phase: 1 });
    void sp;
    for (const e of c.enemies(at, c.p("spikeRadius"))) {
      c.hit(e, c.p("spikeDamage") * (k === 0 ? 1 : 0.5));
      push(e, sub(e.location, ground), 0.5, 0.55);
      effect(e, "slowness", 80, 2);
    }
    if (k % 3 === 0) yield 1;
  }
  c.particle("grimoire:shard_burst", add(ground, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 2, count: 3 });
  yield 60;
}

// ------------------------------------------------------------------------------------------ I02
export function* borealDragon(c: Cast): Routine {
  const p = c.player;
  const anchor = () => add(p.location, add(rotY(v3(0, 0, -1.3), p.getRotation().y), v3(0, 3.0, 0)));
  const head = c.fx("grimoire:fx_i_dragon", anchor(), { dir: p.getViewDirection(), phase: 1, size: 1.1 * c.area });
  c.sound("grimoire.ice.form", p.location, 1, 0.7);
  for (let t = 0; t < 14; t++) {
    head?.move(anchor()).aim(p.getViewDirection());
    yield 1;
  }
  head?.phase(2);
  c.sound("grimoire.ice.roar", p.location, 1.6, 1);
  c.shake(p.location, 20, 0.3, 0.8);
  for (let t = 0; t < 8; t++) {
    head?.move(anchor()).aim(p.getViewDirection());
    yield 1;
  }
  head?.phase(3);
  const exposure = new Map<string, number>();
  const range = c.p("range") * c.area;
  const cos = Math.cos((c.p("angle") * Math.PI) / 180);
  const spikes: Fx[] = [];
  for (let t = 0; t < c.p("duration"); t++) {
    if (!c.ok) return;
    const dir = p.getViewDirection();
    const mouth = add(anchor(), mul(dir, 3.2));
    head?.move(anchor()).aim(dir);
    // the breath stream: shards and freezing wind along the cone
    for (let k = 1; k <= 4; k++) {
      const at = add(mouth, mul(dir, (range * k) / 4.5));
      c.particle("grimoire:streak_dir", at, { color: ICE, color2: WH, dir, speed: 1, count: 0.5, radius: k * 0.4 });
      if (t % 2 === 0) c.particle("grimoire:snow_burst", at, { color: WH, color2: CY, radius: 0.5 + k * 0.4, count: 0.5 });
    }
    if (t % 6 === 0) c.sound("grimoire.ice.breath", mouth, 0.9, 1);
    if (t % c.p("interval") === 0) {
      for (const e of c.enemies(add(mouth, mul(dir, range / 2)), range / 2 + 2)) {
        const to = sub(bodyCenter(e), mouth);
        if (len(to) > range || dot(norm(to), dir) < cos) continue;
        c.hit(e, c.p("tickDamage"));
        effect(e, "slowness", 40, 2);
        const x = (exposure.get(e.id) ?? 0) + c.p("interval");
        exposure.set(e.id, x);
        if (x >= 40) {
          freeze(c, e, 50);
          exposure.set(e.id, -60);
        }
      }
    }
    // temporary ice spikes left along the path
    if (t % 12 === 6 && spikes.length < 6) {
      const at = c.ground(add(mouth, mul(dir, range * (0.35 + Math.random() * 0.5))), 10);
      const sp = c.fx("grimoire:fx_i_spike", at, { yaw: t * 33, size: 0.55, phase: 1 });
      if (sp) spikes.push(sp);
      for (const e of c.enemies(at, 1.6)) c.hit(e, 2);
    }
    yield 1;
  }
  head?.phase(4);
  yield 8;
}

// ------------------------------------------------------------------------------------------ I03
export function* wintersGuillotine(c: Cast): Routine {
  const dir = flatNorm(c.dir);
  const L = c.p("length");
  const mid = add(c.feet, mul(dir, 3 + L / 2));
  const ground = c.ground(add(mid, v3(0, 4, 0)), 14);
  const H = 14;
  const { yaw } = yawPitchOf(dir);
  c.fx("grimoire:fx_circle_i", add(ground, v3(0, H + 3.2, 0)), { size: L / 2 + 1, variant: 1, phase: 1 });
  const blade = c.fx("grimoire:fx_i_guillotine", add(ground, v3(0, H, 0)), { yaw, len: H, phase: 1 });
  c.sound("grimoire.ice.form", ground, 1.4, 0.8);
  yield 22;
  blade?.phase(3);
  c.sound("grimoire.ice.fall", add(ground, v3(0, H / 2, 0)), 1.4, 1);
  yield 5;
  blade?.phase(4);
  c.sound("grimoire.ice.impact", ground, 1.6, 0.8);
  c.shake(ground, 30, 0.6, 0.6);
  const right = rotY(dir, 90);
  const half = (c.p("width") / 2) * c.area;
  for (const e of c.enemies(ground, L / 2 + half + 1)) {
    const rel = sub(e.location, ground);
    if (Math.abs(dot(rel, dir)) <= L / 2 && Math.abs(dot(rel, right)) <= half) {
      c.hit(e, c.p("damage"));
      freeze(c, e, c.p("freeze"));
    }
  }
  for (let k = -1; k <= 1; k++) {
    const at = add(ground, mul(dir, (k * L) / 3));
    c.particle("grimoire:shard_burst", add(at, v3(0, 0.5, 0)), { color: ICE, color2: WH, radius: 1.5, count: 2 });
  }
  // branching crystalline fractures spread from the cut
  const fractures: V3[] = [];
  for (const s of [-0.35, 0.05, 0.4]) fractures.push(add(ground, mul(dir, s * L)));
  for (const at of fractures) c.fx("grimoire:fx_i_fracture", add(at, v3(0, 0.02, 0)), { yaw: Math.random() * 360, size: 0.8 * c.area, phase: 1 });
  yield 10;
  for (const at of fractures) {
    for (const e of c.enemies(at, 5 * c.area)) {
      c.hit(e, c.p("fractureDamage"));
      effect(e, "slowness", 60, 1);
    }
    c.sound("grimoire.ice.crack", at, 1, 0.8);
  }
  yield 40;
  blade?.phase(15);
  yield Math.max(20, c.p("freeze") - 40);
}

// ------------------------------------------------------------------------------------------ I04
export function* crystalRain(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const formation = c.fx("grimoire:fx_i_swords", add(point, v3(0, 16, 0)), { phase: 1, size: R / 13 });
  c.fx("grimoire:fx_circle_i", add(point, v3(0, 15.6, 0)), { size: R, variant: 2, phase: 1 });
  c.sound("grimoire.ice.form", point, 1.5, 0.9);
  yield 22;
  const waves = c.p("waves");
  const per = Math.ceil(c.p("clusters") / waves);
  const r = rng(system.currentTick + 17);
  for (let w = 0; w < waves; w++) {
    formation?.phase(3 + w);
    const foes = nearestEnemies(c, point, R + 2, per);
    for (let k = 0; k < per; k++) {
      const tgt = foes.length ? foes[k % foes.length] : undefined;
      const ang = r() * Math.PI * 2, rr = Math.sqrt(r()) * R;
      const land = tgt ? { ...tgt.location } : c.ground(add(point, v3(Math.cos(ang) * rr, 2, Math.sin(ang) * rr)), 6);
      c.run(volley(c, land, k * 2), "volley");
    }
    c.sound("grimoire.ice.fall", add(point, v3(0, 12, 0)), 1.2, 1.1 + w * 0.1);
    yield 12;
  }
  yield* c.join(60);
}

function* volley(c: Cast, land: V3, delay: number): Routine {
  if (delay) yield delay;
  const top = add(land, v3(0, 15, 0));
  const v = c.fx("grimoire:fx_i_volley", top, { phase: 1, yaw: Math.random() * 360 });
  for (let i = 1; i <= 5; i++) {
    v?.move(lerp(top, land, i / 5));
    yield 1;
  }
  v?.dissolve(3);
  c.particle("grimoire:shard_burst", add(land, v3(0, 0.6, 0)), { color: ICE, color2: WH, radius: 1, count: 1 });
  c.particle("grimoire:ring_h", add(land, v3(0, 0.1, 0)), { color: CY, radius: 4, life: 0.5 });
  for (const e of c.enemies(land, 2.2)) {
    c.hit(e, c.p("damage"));
    effect(e, "slowness", 40, 1);
  }
  c.sound("grimoire.ice.shatter", land, 0.7, 1.2 + Math.random() * 0.3);
}

// ------------------------------------------------------------------------------------------ I05
export function* eternalLotus(c: Cast): Routine {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  const lotus = c.fx("grimoire:fx_i_lotus", center, { phase: 1, size: R / 4 });
  c.sound("grimoire.ice.chime", center, 1.2, 1);
  const cap = c.p("petalCapacity") * c.power;
  const layers = [8 * cap, 6 * cap, 5 * cap];
  let broken = 0;
  const owner = c.player;
  c.ward({
    label: "lotus", priority: 30,
    protects: (e) => isAllyOrSelf(owner, e) && dist(e.location, center) <= R + 0.5,
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
      lotus?.pulse();
      lotus?.phase(Math.min(5, 2 + broken));
      c.particle("grimoire:shard_burst", add(info.hurt.location, v3(0, 1.2, 0)), { color: ICE, color2: WH, count: 1 });
      c.sound(broken >= 3 ? "grimoire.ice.shatter" : "grimoire.ice.crack", info.hurt.location, 1, 1.2);
    },
  });
  yield 20;
  lotus?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && broken < 3; t++) {
    if (t % 30 === 0) c.particle("grimoire:snow_burst", add(center, v3(0, 1.5, 0)), { color: WH, color2: ICE, radius: R * 0.5, count: 0.6 });
    yield 1;
  }
  yield 8;
}

// ------------------------------------------------------------------------------------------ I06
export function* frozenThroneMirrors(c: Cast): Routine {
  const p = c.player;
  const n = c.p("mirrors");
  const mirrors: { fx?: Fx; charges: number; angle: number; busyUntil: number; target?: V3; alive: boolean }[] = [];
  for (let i = 0; i < n; i++) {
    mirrors.push({ fx: c.fx("grimoire:fx_i_mirror", add(p.location, v3(0, 1.4, 0)), { phase: 1 }), charges: c.p("reflects"), angle: (i * 360) / n, busyUntil: 0, alive: true });
  }
  c.sound("grimoire.ice.mirror", p.location, 1, 1);
  const shatter = (m: (typeof mirrors)[number]) => {
    m.alive = false;
    m.fx?.phase(3);
    const at = m.fx?.location ?? p.location;
    c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, radius: 1.5, count: 2 });
    for (const e of c.enemies(at, 3)) {
      c.hit(e, c.p("shardDamage"));
      effect(e, "slowness", 60, 1);
    }
    c.sound("grimoire.ice.shatter", at, 1, 1);
    const f = m.fx;
    system.runTimeout(() => f?.dissolve(4), 8);
  };
  c.ward({
    label: "mirrors", priority: 25,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (!PHYSICAL_CAUSES.has(info.cause)) return info.damage;
      const m = mirrors.find((x) => x.alive && x.charges > 0);
      if (!m) return info.damage;
      m.charges--;
      return 0;
    },
    react: () => {
      const m = mirrors.find((x) => x.alive && x.charges <= 0);
      if (m) shatter(m);
      for (const x of mirrors) if (x.alive) x.fx?.pulse();
      c.sound("grimoire.ice.reflect", p.location, 1, 1);
    },
  });
  const handled = new Set<string>();
  for (let t = 0; t < c.p("duration") * 20 && mirrors.some((m) => m.alive); t++) {
    if (!c.ok) return;
    const now = system.currentTick;
    const center = add(p.location, v3(0, 1.3, 0));
    // intercept incoming projectiles
    for (const e of c.dim.getEntities({ location: center, maxDistance: 12 })) {
      if (handled.has(e.id)) continue;
      const proj = e.getComponent(EntityProjectileComponent.componentId) as EntityProjectileComponent | undefined;
      if (!proj || (proj.owner && isAllyOrSelf(p, proj.owner))) continue;
      const vel = e.getVelocity();
      const toMe = sub(center, e.location);
      if (dot(vel, toMe) <= 0) continue;
      const m = mirrors.filter((x) => x.alive && x.charges > 0).sort((a, b) => dist(a.fx?.location ?? center, e.location) - dist(b.fx?.location ?? center, e.location))[0];
      if (!m) break;
      m.target = add(center, mul(norm(sub(e.location, center)), 1.9));
      m.busyUntil = now + 10;
      if (dist(e.location, center) < 3.2) {
        handled.add(e.id);
        const speed = Math.max(0.8, len(vel));
        const back = proj.owner?.isValid ? norm(sub(bodyCenter(proj.owner), e.location)) : norm(sub(e.location, center));
        try {
          e.clearVelocity();
          e.applyImpulse(mul(back, speed * 1.2));
          proj.owner = p;
        } catch {
          /* ignore */
        }
        m.charges--;
        m.fx?.pulse();
        c.particle("grimoire:ring_dir", m.target, { color: WH, color2: CY, radius: 2.4, dir: norm(sub(e.location, center)) });
        c.sound("grimoire.ice.reflect", m.target, 1, 1.3);
        if (m.charges <= 0) shatter(m);
      }
    }
    // orbit / intercept positions
    mirrors.forEach((m, i) => {
      if (!m.alive) return;
      const a = ((m.angle + t * 2) * Math.PI) / 180;
      const orbit = add(center, v3(Math.cos(a) * 2.6, 0.2 + Math.sin(t * 0.08 + i) * 0.2, Math.sin(a) * 2.6));
      const goal = m.busyUntil > now && m.target ? m.target : orbit;
      const cur = m.fx?.location ?? goal;
      const next = lerp(cur, goal, 0.45);
      m.fx?.move(next).aim(sub(next, center));
    });
    yield 1;
  }
  for (const m of mirrors) if (m.alive) shatter(m);
  yield 12;
}

// ------------------------------------------------------------------------------------------ I07
export function chainsOfNiflheim(c: Cast): Routine {
  const a = c.aim(c.p("range"));
  const list = nearestEnemies(c, a.entity ? bodyCenter(a.entity) : a.point, c.p("selectRadius"), c.p("targets"));
  if (a.entity && !list.find((e) => e.id === a.entity!.id)) list.unshift(a.entity);
  const targets = list.slice(0, c.p("targets"));
  if (!targets.length) throw new Fizzle("No enemy to bind in range");
  return (function* () {
    const dur = c.p("duration") * 20;
    const items = targets.map((t) => {
      c.fx("grimoire:fx_circle_i", add(t.location, v3(0, 0.06, 0)), { size: 1.6, variant: 1, phase: 1 });
      const b = c.bind(t, dur + 10, { shell: "grimoire:fx_i_chains", shellInit: { size: Math.max(1, Math.min(2.4, (t.getHeadLocation().y - t.location.y) / 1.6)) } });
      return { t, b };
    });
    c.sound("grimoire.ice.chain", items[0].t.location, 1.2, 0.9);
    yield 12;
    for (const it of items) it.b?.shell?.phase(2);
    for (let s = 0; s < dur; s += 20) {
      for (const it of items) {
        if (!it.t.isValid) continue;
        c.hit(it.t, c.p("dps"));
        c.particle("grimoire:snow_burst", bodyCenter(it.t), { color: ICE, color2: WH, radius: 0.6, count: 0.4 });
      }
      if (s % 40 === 0) c.sound("grimoire.ice.freeze", items[0].b?.anchor ?? c.feet, 0.8, 1.1);
      yield 20;
    }
    for (const it of items) endBind(it.b, true); // movement restored, chains shatter
    c.sound("grimoire.ice.shatter", items[0].b?.anchor ?? c.feet, 1, 1);
    yield 10;
  })();
}

// ------------------------------------------------------------------------------------------ I08
export function* paleMoonLabyrinth(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const center = { x: Math.floor(point.x) + 0.5, y: Math.floor(point.y), z: Math.floor(point.z) + 0.5 };
  const cells = 5, cell = 4, size = cells * cell;
  const set = c.blocks();
  c.fx("grimoire:fx_i_moon", add(center, v3(0, 22, 0)), { size: size / 20, phase: 1 });
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.08, 0)), { size: size * 0.7, variant: 0, phase: 1 });
  for (const [i, j] of [[0, 0], [0, 5], [5, 0], [5, 5], [2, 2], [3, 3], [0, 3], [5, 2]]) {
    const at = c.ground({ x: center.x - size / 2 + i * cell, y: center.y + 4, z: center.z - size / 2 + j * cell }, 10);
    c.fx("grimoire:fx_i_tower", at, { phase: 1, size: 0.62 });
    yield 2;
  }
  c.sound("grimoire.ice.wall", center, 1.3, 0.9);
  let seed = system.currentTick * 3 + 1;
  let current = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
  yield* raise(set, [...current.values()], 3, "grimoire:frost_wall", 80, 2);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (t > 0 && t % (c.p("shiftInterval") * 20) === 0 && set.enabled) {
      seed += 104729;
      const next = new Map(grounded(c, mazeColumns(center, cells, cell, seed).values()).map((p) => [`${p.x},${p.z}`, p]));
      for (const [k, p] of current) {
        if (next.has(k)) continue;
        for (let h = 0; h < 3; h++) set.remove({ x: p.x, y: p.y + h, z: p.z });
        if (Math.random() < 0.25) c.particle("grimoire:snow_burst", { x: p.x + 0.5, y: p.y + 1, z: p.z + 0.5 }, { color: ICE, count: 0.3 });
      }
      yield 2;
      yield* raise(set, [...next.values()].filter((p) => !current.has(`${p.x},${p.z}`)), 3, "grimoire:frost_wall", 80, 1);
      current = next;
      c.sound("grimoire.ice.wall", center, 1, 1.1);
    }
    if (t % 20 === 0) {
      // biting cold next to the frozen walls
      for (const e of c.enemies(center, size * 0.75)) {
        const k = (dx: number, dz: number) => current.has(`${Math.floor(e.location.x + dx)},${Math.floor(e.location.z + dz)}`);
        if (k(1, 0) || k(-1, 0) || k(0, 1) || k(0, -1)) effect(e, "slowness", 30, 1);
      }
    }
    yield 1;
  }
  yield* lower(set, 100);
}

// ------------------------------------------------------------------------------------------ I09
export function* whiteoutDominion(c: Cast): Routine {
  const center = c.feet;
  const R = c.p("radius") * c.area;
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.08, 0)), { size: R, variant: 0, phase: 1 });
  for (let k = 0; k < 6; k++) {
    const at = c.ground(add(center, v3(Math.cos((k / 6) * 6.283) * R, 3, Math.sin((k / 6) * 6.283) * R)), 8);
    c.fx("grimoire:fx_i_spike", at, { yaw: k * 60, size: 0.8, phase: 1 });
  }
  c.sound("grimoire.ice.blizzard", center, 1.4, 0.9);
  const fogged = new Map<string, Player>();
  const fogOf = new Map<string, string>();
  const setFog = (pl: Player, id: string | undefined) => {
    const cur = fogOf.get(pl.id);
    if (cur === id) return;
    try {
      if (cur) pl.runCommand("fog @s remove grimoire_i09");
      if (id) pl.runCommand(`fog @s push ${id} grimoire_i09`);
    } catch {
      /* ignore */
    }
    if (id) {
      fogOf.set(pl.id, id);
      fogged.set(pl.id, pl);
    } else fogOf.delete(pl.id);
  };
  c.onCleanup(() => {
    for (const pl of fogged.values()) if (pl.isValid) setFog(pl, undefined);
  });
  const r = rng(system.currentTick);
  const owner = c.player;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 3 === 0) {
      // swirling snow and ice crystals everywhere except the caster's eye of the storm
      for (let k = 0; k < 3; k++) {
        const ang = r() * Math.PI * 2, rr = 4 + r() * (R - 4);
        c.particle("grimoire:snow_storm", add(center, v3(Math.cos(ang) * rr, 0.5, Math.sin(ang) * rr)), { color: WH, color2: ICE, radius: 3, size: 1.4, count: 0.5 });
      }
    }
    if (t % 20 === 0) {
      for (const pl of c.dim.getPlayers({ location: center, maxDistance: R + 4 })) {
        const inside = dist(pl.location, center) <= R;
        if (pl.id === owner.id) setFog(pl, inside ? "grimoire:whiteout_caster" : undefined);
        else if (inside && c.isEnemy(pl)) {
          setFog(pl, "grimoire:whiteout");
          effect(pl, "blindness", 40, 0);
        } else setFog(pl, undefined);
      }
    }
    if (t % c.p("interval") === 0) {
      for (const e of c.enemies(center, R)) {
        c.hit(e, c.p("damage"));
        effect(e, "slowness", 30, 1);
        c.particle("grimoire:shard_burst", bodyCenter(e), { color: ICE, color2: WH, radius: 0.5, count: 0.3 });
      }
    }
    if (t % 32 === 0) c.sound("grimoire.ice.blizzard", center, 1.1, 0.9 + r() * 0.2);
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ I10
export function frostMirrorTraverse(c: Cast): Routine {
  const dest = teleportDestination(c, c.p("range"));
  if (!dest) throw new Fizzle("No safe destination for the mirror");
  return (function* () {
    const p = c.player;
    const dir = flatNorm(c.dir);
    const mA = c.fx("grimoire:fx_i_mirror", add(p.location, add(mul(dir, 1.3), v3(0, 1.1, 0))), { dir: mul(dir, -1), phase: 1, size: 1.25 });
    const mB = c.fx("grimoire:fx_i_mirror", add(dest, add(mul(dir, -0.4), v3(0, 1.1, 0))), { dir, phase: 1, size: 1.25 });
    c.sound("grimoire.ice.mirror", p.location, 1, 1);
    yield 5;
    mA?.phase(4);
    mB?.phase(4);
    yield 4;
    const ok = p.tryTeleport(dest, { checkForBlocks: true, keepVelocity: false });
    if (!ok) {
      hudFlash(stateOf(p), "§7The mirror path was blocked", 30);
    }
    grantFallImmunity(p.id, 30);
    c.sound("grimoire.ice.mirror", dest, 1, 1.4);
    yield 3;
    for (const m of [mA, mB]) {
      m?.phase(3);
      if (m) c.particle("grimoire:shard_burst", m.location, { color: ICE, color2: WH, radius: 1.4, count: 1.6 });
    }
    c.sound("grimoire.ice.shatter", dest, 0.9, 1.3);
    yield 12;
  })();
}

// ------------------------------------------------------------------------------------------ I11
export function* winterSeraph(c: Cast): Routine {
  const p = c.player;
  const wings = c.fx("grimoire:fx_i_wings", p.location, { yaw: p.getRotation().y, phase: 1, len: 1 });
  c.sound("grimoire.ice.wing", p.location, 1.2, 0.8);
  c.sound("grimoire.ice.summon", p.location, 0.7, 1.4);
  let lastYaw = p.getRotation().y;
  let grounded = 0;
  const total = c.p("duration") * 20;
  const speed = c.p("speed");
  for (let t = 0; t < total; t++) {
    if (!c.ok) break;
    const held = (() => {
      try {
        return schoolOfItem(p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex)?.typeId);
      } catch {
        return undefined;
      }
    })();
    if (held !== "ice") {
      hudFlash(stateOf(p), "§bThe wings fold (Ice Grimoire put away)", 40);
      break;
    }
    const rot = p.getRotation();
    const look = p.getViewDirection();
    let mv = { x: 0, y: 0 };
    let jump = false;
    try {
      mv = p.inputInfo.getMovementVector();
      jump = p.inputInfo.getButtonState(InputButton.Jump) === ButtonState.Pressed;
    } catch {
      /* ignore */
    }
    const right = rotY(flatNorm(look), 90);
    let vel = add(mul(look, speed * mv.y), mul(right, -speed * 0.7 * mv.x));
    if (jump) vel = add(vel, v3(0, speed * 0.6, 0));
    if (Math.abs(mv.x) + Math.abs(mv.y) < 0.1 && !jump) vel = v3(0, 0.02, 0); // hover
    if (t > 8) drive(p, vel);
    grantFallImmunity(p.id, 60);
    let dy = rot.y - lastYaw;
    while (dy > 180) dy -= 360;
    while (dy < -180) dy += 360;
    lastYaw = rot.y;
    wings?.follow(p, v3(0, 0, 0), 1).yaw(rot.y).length(1 + Math.max(-0.6, Math.min(0.6, dy / 10)));
    if (t === 10) wings?.phase(2);
    if (t % 14 === 0) c.sound("grimoire.ice.wing", p.location, 0.6, 0.9 + Math.random() * 0.2);
    if (t % 3 === 0) c.particle("grimoire:snow_burst", add(p.location, v3(0, 1.3, 0)), { color: WH, color2: ICE, radius: 0.8, count: 0.25 });
    grounded = p.isOnGround ? grounded + 1 : 0;
    if (t > 40 && grounded > 20) break; // landed
    yield 1;
  }
  wings?.phase(3);
  effect(p, "slow_falling", 100, 0);
  grantFallImmunity(p.id, 120);
  for (let t = 0; t < 12; t++) {
    if (p.isValid) wings?.follow(p);
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ I12
const KNIGHTS = ["grimoire:frost_knight_sword", "grimoire:frost_knight_spear", "grimoire:frost_knight_shield"];

function setAct(e: Entity, v: number): void {
  try {
    if (e.isValid) e.setProperty("grimoire:act", v);
  } catch {
    /* ignore */
  }
}

export function* frostLegion(c: Cast): Routine {
  const p = c.player;
  const knights: Entity[] = [];
  const offsets = [v3(-2.2, 0, 1.2), v3(2.2, 0, 1.2), v3(0, 0, -2.4)];
  const yaw = p.getRotation().y;
  for (let i = 0; i < 3; i++) {
    const at = c.ground(add(p.location, add(rotY(offsets[i], yaw), v3(0, 2, 0))), 6);
    c.fx("grimoire:fx_circle_i", add(at, v3(0, 0.06, 0)), { size: 1.6, variant: 1, phase: 1 });
    c.particle("grimoire:snow_burst", add(at, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 1.5, count: 2 });
    let k: Entity;
    try {
      k = c.dim.spawnEntity(KNIGHTS[i], at, { initialRotation: yaw });
    } catch {
      continue;
    }
    k.setDynamicProperty(OWNER_PROP, p.id);
    k.setDynamicProperty(SESSION_PROP, SESSION);
    k.addTag("grimoire_summon");
    try {
      (k.getComponent(EntityTameableComponent.componentId) as EntityTameableComponent | undefined)?.tame(p);
    } catch {
      /* ignore */
    }
    setAct(k, 4);
    knights.push(k);
    yield 4;
  }
  c.sound("grimoire.ice.summon", p.location, 1.4, 1);
  c.onCleanup(() => {
    for (const k of knights) {
      if (!k.isValid) continue;
      setAct(k, 7);
      const kk = k;
      system.runTimeout(() => {
        try {
          if (kk.isValid) kk.remove();
        } catch {
          /* ignore */
        }
      }, 18);
    }
  });
  const hitSub = world.afterEvents.entityHitEntity.subscribe((ev) => {
    const d = ev.damagingEntity;
    if (knights.some((k) => k.id === d.id)) {
      setAct(d, 1);
      system.runTimeout(() => setAct(d, 0), 10);
    }
  });
  c.onCleanup(() => world.afterEvents.entityHitEntity.unsubscribe(hitSub));
  yield 16;
  for (const k of knights) setAct(k, 0);
  // Greatshield defender: halves damage dealt to its owner while near and bashes the attacker
  const [sword, spear, shield] = [knights.find((k) => k.typeId === KNIGHTS[0]), knights.find((k) => k.typeId === KNIGHTS[1]), knights.find((k) => k.typeId === KNIGHTS[2])];
  c.ward({
    label: "bulwark", priority: 15,
    protects: (e) => e.id === p.id && !!shield && shield.isValid && dist(shield.location, p.location) < 8,
    absorb: (info) => (PHYSICAL_CAUSES.has(info.cause) ? info.damage * 0.5 : info.damage),
    react: (info) => {
      if (!shield || !shield.isValid) return;
      setAct(shield, 3);
      system.runTimeout(() => setAct(shield, 0), 20);
      const a = info.attacker;
      if (a && a.isValid && dist(a.location, shield.location) < 5 && c.isEnemy(a)) {
        c.hit(a, 4);
        push(a, sub(a.location, shield.location), 1.6, 0.4);
        effect(a, "slowness", 40, 2);
        c.particle("grimoire:ring_dir", bodyCenter(a), { color: ICE, color2: WH, radius: 2, dir: norm(sub(a.location, shield.location)) });
      }
    },
  });
  const total = c.p("duration") * 20;
  for (let t = 0; t < total; t++) {
    if (!c.ok || !knights.some((k) => k.isValid)) break;
    for (const k of knights) {
      if (k.isValid && dist(k.location, p.location) > 28) {
        try {
          k.teleport(add(p.location, v3(1, 0.5, 1)));
        } catch {
          /* ignore */
        }
      }
    }
    // Longsword: frost crescent every 3 s
    if (sword?.isValid && t % 60 === 30) {
      const foes = c.enemies(sword.location, 3.6);
      if (foes.length) {
        setAct(sword, 2);
        system.runTimeout(() => setAct(sword, 0), 16);
        for (const e of foes) {
          c.hit(e, 8);
          effect(e, "slowness", 40, 1);
          push(e, sub(e.location, sword.location), 0.9, 0.25);
        }
        c.particle("grimoire:ring_h", add(sword.location, v3(0, 1, 0)), { color: ICE, color2: WH, radius: 8, life: 0.5 });
        c.sound("grimoire.ice.slash", sword.location, 1, 0.9);
      }
    }
    // Spear: glacial lunge every 4 s
    if (spear?.isValid && t % 80 === 50) {
      const foe = nearestEnemies(c, spear.location, 9, 1)[0];
      if (foe) {
        setAct(spear, 2);
        system.runTimeout(() => setAct(spear, 0), 14);
        const dir = norm(sub(foe.location, spear.location));
        const from = add(spear.location, v3(0, 1.2, 0));
        try {
          spear.applyImpulse(add(mul(flatNorm(dir), 1.3), v3(0, 0.15, 0)));
        } catch {
          /* ignore */
        }
        for (const e of c.along(from, add(from, mul(dir, 7)), 1.0)) {
          c.hit(e, 9);
          effect(e, "slowness", 40, 2);
        }
        c.particle("grimoire:streak_dir", from, { color: WH, color2: ICE, dir, count: 1.5 });
        c.sound("grimoire.ice.slash", spear.location, 1, 1.3);
      }
    }
    // Greatshield: guards the owner, intercepts projectiles close to them
    if (shield?.isValid && t % 4 === 0) {
      for (const e of c.dim.getEntities({ location: p.location, maxDistance: 3.5 })) {
        const proj = e.getComponent(EntityProjectileComponent.componentId) as EntityProjectileComponent | undefined;
        if (proj && !(proj.owner && isAllyOrSelf(p, proj.owner)) && dist(shield.location, p.location) < 8) {
          c.particle("grimoire:shard_burst", e.location, { color: ICE, count: 0.5 });
          try {
            e.remove();
          } catch {
            /* ignore */
          }
          setAct(shield, 3);
          system.runTimeout(() => setAct(shield, 0), 14);
        }
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ I13
export function* stillWinterHourglass(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const glass = c.fx("grimoire:fx_i_hourglass", add(point, v3(0, 9, 0)), { phase: 1, size: 1.3 });
  c.fx("grimoire:fx_circle_i", add(point, v3(0, 0.08, 0)), { size: R, variant: 1, phase: 1 });
  c.sound("grimoire.ice.form", point, 1.2, 0.8);
  yield 16;
  glass?.phase(2);
  const cd = c.p("countdown");
  for (let t = 0; t < cd; t++) {
    if (t % 20 === 0) c.sound("grimoire.ice.tick", add(point, v3(0, 9, 0)), 1.2, 1 + t / cd);
    if (t % 5 === 0) {
      c.particle("grimoire:snow_still", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R * 0.6, count: 0.2 });
      for (const e of c.enemies(point, R)) effect(e, "slowness", 20, Math.min(4, Math.floor((t / cd) * 4)));
    }
    yield 1;
  }
  glass?.phase(3);
  c.flash(point, R * 2.5, { r: 0.7, g: 0.9, b: 1 }, 0.1);
  c.sound("grimoire.ice.pulse", point, 1.6, 1);
  c.shake(point, R * 3, 0.5, 0.6);
  c.particle("grimoire:ring_h", add(point, v3(0, 0.3, 0)), { color: WH, color2: CY, radius: R * 2.2, life: 1.4 });
  c.particle("grimoire:snow_burst", add(point, v3(0, 2, 0)), { color: WH, color2: ICE, radius: R * 0.6, count: 4 });
  for (const e of c.enemies(point, R)) {
    c.hit(e, c.p("damage"));
    freeze(c, e, c.p("freeze"));
  }
  yield c.p("freeze");
}

// ------------------------------------------------------------------------------------------ I14
export function* everlastingCitadel(c: Cast): Routine {
  const center = { x: Math.floor(c.feet.x) + 0.5, y: Math.floor(c.feet.y), z: Math.floor(c.feet.z) + 0.5 };
  const R = c.p("radius");
  const set = c.blocks();
  c.fx("grimoire:fx_circle_i", add(center, v3(0, 0.07, 0)), { size: R + 2, variant: 2, phase: 1 });
  const crown = c.fx("grimoire:fx_i_crown", add(center, v3(0, 14, 0)), { phase: 1, size: 1.1 });
  c.sound("grimoire.ice.summon", center, 1.4, 0.8);
  const towers: { fx?: Fx; at: V3 }[] = [];
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
    const at = c.ground({ x: center.x + Math.cos(a) * (R + 1), y: center.y + 4, z: center.z + Math.sin(a) * (R + 1) }, 10);
    towers.push({ fx: c.fx("grimoire:fx_i_tower", at, { phase: 1, size: 1.35 }), at });
    yield 5;
  }
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2;
    const at = c.ground({ x: center.x + Math.cos(a) * R, y: center.y + 4, z: center.z + Math.sin(a) * R }, 10);
    c.fx("grimoire:fx_i_arch", at, { yaw: (-a * 180) / Math.PI + 90, phase: 1, size: 0.9 });
  }
  // the palace walls form progressively (ring with four arched gates and crenellations)
  const cols = new Map<string, V3>();
  for (let s = 0; s < 360; s += 2) {
    const a = (s * Math.PI) / 180;
    if (s % 90 < 8 || s % 90 > 82) continue; // gates
    const x = Math.floor(center.x + Math.cos(a) * R), z = Math.floor(center.z + Math.sin(a) * R);
    cols.set(`${x},${z}`, { x, y: center.y, z });
  }
  const g = grounded(c, cols.values());
  yield* raise(set, g, 4, "grimoire:frost_wall", 50, 3);
  let n = 0;
  for (const p of g) if (n++ % 2 === 0) set.place({ x: p.x, y: p.y + 4, z: p.z }, "grimoire:frost_wall");
  crown?.phase(2);
  const owner = c.player;
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 20 === 0) for (const e of livingNear(c.dim, center, R)) if (isAllyOrSelf(owner, e)) effect(e, "resistance", 30, 1);
    if (t % c.p("interval") === 0 && t > 0) {
      for (const tw of towers) {
        const foe = nearestEnemies(c, tw.at, c.p("range"), 1)[0];
        if (!foe) continue;
        tw.fx?.pulse();
        const from = add(tw.at, v3(0, 7.5, 0));
        const dir = norm(sub(bodyCenter(foe), from));
        const lance = c.fx("grimoire:fx_i_shard", from, { dir, phase: 1, size: 1.2 });
        c.run(fly(c, {
          fx: lance, from, dir, speed: 1.6, range: c.p("range") + 8, radius: 0.7, pierce: 1, homing: foe, homingRate: 0.35,
          onHit: (e) => {
            c.hit(e, c.p("lanceDamage"));
            effect(e, "slowness", 60, 2);
          },
          onEnd: (at) => {
            lance?.dissolve(2);
            c.particle("grimoire:shard_burst", at, { color: ICE, color2: WH, count: 0.8 });
            c.sound("grimoire.ice.crack", at, 0.8, 1.2);
          },
        }), "lance");
      }
      crown?.pulse();
    }
    yield 1;
  }
  crown?.dissolve(18);
  yield* lower(set, 60);
  yield 10;
}

// ------------------------------------------------------------------------------------------ I15
export function* theLastWinter(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const players = c.dim.getPlayers({ location: point, maxDistance: 56 });
  for (const pl of players) {
    try {
      pl.runCommand("fog @s push grimoire:last_winter grimoire_i15");
    } catch {
      /* ignore */
    }
  }
  c.onCleanup(() => {
    for (const pl of players) {
      try {
        if (pl.isValid) pl.runCommand("fog @s remove grimoire_i15");
      } catch {
        /* ignore */
      }
    }
  });
  // Phase 1 - The Silent World: suspended snow, colossal circle, dramatic stillness (world keeps running)
  const sky = c.fx("grimoire:fx_circle_i", add(point, v3(0, 28, 0)), { size: R * 1.35, variant: 2, phase: 1 });
  c.flash(point, 60, { r: 0.75, g: 0.88, b: 1 }, 0.3);
  for (let t = 0; t < 60; t++) {
    if (t % 10 === 0) {
      c.particle("grimoire:snow_still", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R, count: 1.5 });
      for (const e of c.enemies(point, R)) effect(e, "slowness", 30, 3);
    }
    yield 1;
  }
  c.sound("grimoire.ice.chime", point, 1.6, 0.6);
  // Phase 2 - Crown of Absolute Frost: freezing beams and ice formations around enemies
  const crown = c.fx("grimoire:fx_i_crown", add(point, v3(0, 20, 0)), { phase: 1, size: 2.4 });
  yield 24;
  crown?.phase(2);
  for (let wave = 0; wave < 4; wave++) {
    const foes = nearestEnemies(c, point, R, 6);
    const spots = foes.length ? foes.map((e) => ({ ...e.location })) : [0, 1, 2].map((k) => c.ground(add(point, v3(Math.cos(k * 2.1 + wave) * R * 0.5, 3, Math.sin(k * 2.1 + wave) * R * 0.5)), 8));
    crown?.pulse();
    for (const s of spots) {
      const from = add(point, v3(0, 18, 0));
      const to = add(s, v3(0, 0.5, 0));
      const dir = norm(sub(to, from));
      c.fx("grimoire:fx_i_beam", from, { dir, len: dist(from, to), phase: 1, size: 0.9 }); // fades with the spell
      c.particle("grimoire:beam_up", to, { color: WH, color2: CY, radius: 1.5, size: 1.4, count: 1 });
      for (const e of c.enemies(to, 2.5)) {
        c.hit(e, c.p("beamDamage"));
        freeze(c, e, 40);
      }
      if (wave % 2 === 0) {
        for (let k = 0; k < 3; k++) {
          c.fx("grimoire:fx_i_spike", c.ground(add(s, v3(Math.cos(k * 2.09) * 2.2, 2, Math.sin(k * 2.09) * 2.2)), 5), { yaw: k * 120, size: 0.9, phase: 1 });
        }
      }
    }
    c.sound("grimoire.ice.beam", point, 1.4, 1 + wave * 0.1);
    yield 16;
  }
  // Phase 3 - The Final Descent: a moon-sized hexagonal crystal falls and shatters into a wave of shards
  const fall = 30;
  const moon = c.fx("grimoire:fx_i_moon_crystal", add(point, v3(0, 6 + fall, 0)), { phase: 1, len: fall, size: Math.max(1, R / 16) });
  c.sound("grimoire.ice.descent", point, 2, 1);
  yield 30;
  moon?.phase(3);
  for (let t = 0; t < 40; t++) {
    if (t % 10 === 0) c.shake(point, 60, 0.15 + t / 120, 0.5);
    yield 1;
  }
  moon?.phase(4);
  crown?.dissolve(12);
  sky?.phase(3);
  c.flash(point, 80, { r: 0.85, g: 0.95, b: 1 }, 0.2);
  c.sound("grimoire.ice.pulse", point, 2, 0.7);
  c.sound("grimoire.ice.shatter", point, 2, 0.6);
  for (let k = 0; k < 3; k++) {
    c.particle("grimoire:ring_h", add(point, v3(0, 0.5 + k, 0)), { color: WH, color2: CY, radius: R * (1.2 + k * 0.5), life: 1.5 });
    c.particle("grimoire:shard_burst", add(point, v3(0, 3, 0)), { color: ICE, color2: WH, radius: 4 + k * 2, count: 4 });
  }
  shock(c, point, R, c.p("finalDamage"), { knock: 2.0, up: 0.7, shake: 1, minK: 0.3, color: WH, color2: CY });
  for (const e of c.enemies(point, R)) freeze(c, e, 80);
  // icy mist and fading crystalline debris
  for (let t = 0; t < 100; t++) {
    if (t % 12 === 0) c.particle("grimoire:mist", add(point, v3(0, 1, 0)), { color: WH, color2: ICE, radius: R * 0.5, size: 2.5, count: 1.5, life: 2 });
    if (t === 10) {
      for (let k = 0; k < 6; k++) c.fx("grimoire:fx_i_spike", c.ground(add(point, v3(Math.cos(k) * R * 0.6, 3, Math.sin(k) * R * 0.6)), 6), { yaw: k * 60, size: 0.5, phase: 1 });
    }
    yield 1;
  }
}

