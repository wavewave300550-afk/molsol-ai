import { Dimension, Entity, Player, Vector3 } from "@minecraft/server";
import { DN05 as C } from "../config/dn05";
import { damage, effect, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, sound } from "../lib/fx";
import { Actor, Scene, secs } from "../lib/scene";
import { groundBelow, isAlive } from "../lib/targeting";
import { add, dist, distToSegment, easeIn, flat, lerp, mul, norm, right, smooth, spline, sub, up, yawOf } from "../lib/vec";

// State tables (tools/assets/dn_city_constructs.py *_STATES) and animation lengths in ticks.
export const BAL = { hidden: 0, drop: 1, impact: 2 };
export const STREET = { hidden: 0, appear: 1, roll: 2, crumble: 3 };
export const STAIR = { hidden: 0, descend: 1, stand: 2, retract: 3 };
const DOOR = { hidden: 0, arrive: 1, fly: 2, swoop: 3, depart: 4 };
const WIN = { hidden: 0, arrive: 1, hover: 2, blink: 3, stare: 4, shatter: 5 };
const COR = { hidden: 0, unfold: 1, snap: 2, clamp: 3, fold: 4 };
const SF = { hidden: 0, slam: 1, rest: 2, sink: 3 };
const FR = { hidden: 0, arrive: 1, idle: 2, hop: 3, bite: 4, crumble: 5 };
export const T = {
  stairDown: secs(1.6), stairUp: secs(1.2), balDrop: secs(0.8), balHit: secs(0.9), stAppear: secs(0.6), stCrumble: secs(0.6),
  doorArrive: secs(1.0), doorSwoop: secs(0.8), doorSlam: secs(0.38), doorDepart: secs(0.8),
  winArrive: secs(0.8), winBlink: secs(0.8), winStare: secs(1.0), winFire: secs(0.45), winShatter: secs(0.7),
  corUnfold: secs(1.0), corSnap: secs(0.35), corFold: secs(0.8),
  sfFirst: secs(0.45), sfStep: secs(0.3), sfSink: secs(0.8),
  frArrive: secs(0.8), frHop: secs(0.6), frBite: secs(0.5), frBiteHit: secs(0.27), frCrumble: secs(0.7),
};
/** Model lengths in blocks: corridor 5 x 16 units at scale 1.5; stair chunks 32 units at scale 1.5. */
const CORRIDOR_LEN = (5 * 16 * 1.5) / 16;
const SF_CHUNKS = 5, SF_CHUNK = (32 * 1.5) / 16;

export interface CityCtx {
  scene: Scene;
  caster: Player;
  dim: Dimension;
  center: Vector3;
  /** A sky anchor under the city (district i). */
  sky(i: number): Vector3;
  /** Live hostiles in the target area, nearest to `from` first. */
  foes(from: Vector3): Entity[];
  /** Deterministic fallback ground point inside the area. */
  spot(seed: number): Vector3;
  /** Every hunter registers here so Phase IV can dismiss stragglers. */
  hunters: Set<Actor>;
}

function aimAt(c: CityCtx, from: Vector3, seed: number): { loc: Vector3; e?: Entity } {
  const f = c.foes(from);
  if (f.length) { const e = f[seed % Math.min(f.length, 3)]; return { loc: groundBelow(c.dim, e.location), e }; }
  return { loc: c.spot(seed) };
}

function finish(c: CityCtx, a: Actor, state: number, ticks: number): void {
  if (!a.valid) return;
  a.state(state);
  c.scene.after(ticks, () => { c.scene.despawn(a); c.hunters.delete(a); });
}

// ----------------------------------------------------------------------------------- flying doorframe
/** Swoops through enemies: whoever is caught in the doorway is hurt and thrown out the other side. */
export function doorframe(c: CityCtx, i: number, until: number): void {
  const { scene, dim } = c;
  const home = c.sky(i + 1);
  const door = scene.spawn("dn_city_door", home, { state: DOOR.arrive, yaw: yawOf(sub(c.center, home)) });
  c.hunters.add(door);
  sound(dim, "dn_city_door", home, 1.0, 0.8);
  burst(dim, "dn_city_door", up(home, 2), 2, 6);
  let pos = home;
  let t0 = scene.tick + T.doorArrive;
  scene.at(t0, () => door.state(DOOR.fly));
  const passLen = 36;
  for (let p = 0; p < C.doorPasses; p++) {
    const start = t0 + 6 + p * (passLen + 10);
    if (start + passLen > until) break;
    scene.at(start, () => {
      if (!door.valid) return;
      const tgt = aimAt(c, pos, i + p);
      const T0 = up(tgt.loc, 0.1);
      const d = norm(flat(sub(T0, pos)));
      const path = [pos, add(up(T0, 2.5), mul(d, -5)), T0, add(up(T0, 2.0), mul(d, 5)), add(up(T0, 8), mul(d, 9))];
      const yaw = yawOf(d);
      scene.span(start, start + passLen, (q) => { pos = spline(path, q); door.move(pos, yaw); });
      const hitAt = start + Math.round(passLen / 2);
      scene.at(hitAt - T.doorSlam, () => { door.state(DOOR.swoop); sound(dim, "dn_city_door", T0, 1.2); });
      scene.at(hitAt, () => {
        particle(dim, "dn_city_door", up(T0, 1.5));
        particle(dim, "dn_city_dust_n", T0);
        for (const e of c.foes(T0)) {
          if (dist(e.location, T0) > C.doorReach + 0.6) continue;
          damage(e, C.doorDamage, c.caster);
          shove(e, d, C.doorThrowH, C.doorThrowV); // thrown out the far side of the doorway
        }
      });
      scene.at(start + passLen, () => door.state(DOOR.fly));
    });
  }
  scene.at(Math.min(until, t0 + 6 + C.doorPasses * (passLen + 10)), () => finish(c, door, DOOR.depart, T.doorDepart));
}

// ----------------------------------------------------------------------------------- watching window
/** Hovers by a target, blinks, then fires a stare along a line; finally shatters into glass rain. */
export function windowEye(c: CityCtx, i: number, until: number): void {
  const { scene, dim } = c;
  let pos = c.sky(i + 2);
  const win = scene.spawn("dn_city_window", pos, { state: WIN.arrive });
  c.hunters.add(win);
  sound(dim, "dn_city_groan", pos, 0.7, 1.3);
  let t = scene.tick + T.winArrive;
  scene.at(t, () => win.state(WIN.hover));
  const glide = (to: Vector3, from: number, ticks: number, look: () => Vector3) => {
    const a = pos;
    scene.span(from, from + ticks, (q) => { pos = lerp(a, to, smooth(q)); win.move(pos, yawOf(sub(look(), pos))); });
  };
  for (let k = 0; k < C.windowStares; k++) {
    const t1 = t;
    const cycle = 16 + T.winBlink + T.winStare;
    if (t1 + cycle > until - 40) break;
    scene.at(t1, () => {
      const tgt = aimAt(c, pos, i * 2 + k);
      let goal = tgt.loc;
      const side = norm(flat(sub(c.caster.location, goal)));
      const hov = up(add(goal, mul(add(side, mul(right(side), k % 2 ? 1 : -1)), 2.6)), 3.6);
      const look = () => (tgt.e && isAlive(tgt.e) ? tgt.e.location : goal);
      glide(hov, t1, 16, look);
      scene.at(t1 + 16, () => { win.state(WIN.blink); line(dim, "dn_city_eye", pos, up(look(), 1), 4); });
      scene.at(t1 + 16 + T.winBlink, () => { win.state(WIN.stare); sound(dim, "dn_city_stare", pos, 1.0); });
      scene.at(t1 + 16 + T.winBlink + T.winFire, () => {
        if (tgt.e && isAlive(tgt.e)) goal = tgt.e.location;
        const from = pos, dir = norm(sub(up(goal, 1), from));
        const end = add(from, mul(dir, dist(from, goal) + 3));
        line(dim, "dn_city_stare", from, end, 10);
        particle(dim, "dn_city_eye", up(goal, 1));
        for (const e of c.foes(goal)) {
          if (distToSegment(add(e.location, { x: 0, y: 1, z: 0 }), from, end) > C.stareWidth) continue;
          damage(e, C.stareDamage, c.caster);
          effect(e, "slowness", C.stareSlowTicks, 1);
        }
      });
      scene.at(t1 + cycle, () => win.state(WIN.hover));
    });
    t += cycle;
  }
  // final: drift over an enemy and shatter into a rain of glass
  const tEnd = Math.min(t, until - 32);
  scene.at(tEnd, () => {
    const tgt = aimAt(c, pos, i + 7);
    const below = tgt.loc;
    const warn = scene.spawn("telegraph", below, { kind: 1, size: C.glassRadius, state: 1 });
    glide(up(below, 4.5), tEnd, 16, () => below);
    scene.at(tEnd + 16, () => { win.state(WIN.shatter); sound(dim, "dn_city_balcony", below, 0.8, 1.4); });
    scene.at(tEnd + 20, () => {
      warn.state(3);
      burst(dim, "dn_city_glass", up(below, 3.5), 1.5, 5);
      particle(dim, "dn_city_ring", up(below, 0.2));
      for (const e of c.foes(below)) if (dist(e.location, below) <= C.glassRadius) damage(e, C.glassDamage, c.caster);
    });
    scene.at(tEnd + 28, () => scene.despawn(warn));
    scene.at(tEnd + 16 + T.winShatter, () => { scene.despawn(win); c.hunters.delete(win); });
  });
}

// ----------------------------------------------------------------------------------- folding corridor
/** Unfolds along the ground until its far door reaches the target, then snaps shut: restraint + damage. */
export function corridor(c: CityCtx, i: number): void {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, i);
  const end = tgt.loc;
  let dir = norm(flat(sub(end, c.caster.location)));
  dir = i % 2 ? right(dir) : mul(right(dir), -1);
  const origin = groundBelow(dim, add(end, mul(dir, -CORRIDOR_LEN)));
  const warn = scene.spawn("telegraph", end, { kind: 1, size: C.corridorCatch * 0.8, state: 1 });
  const cor = scene.spawn("dn_city_corridor", origin, { state: COR.unfold, yaw: yawOf(dir) });
  c.hunters.add(cor);
  sound(dim, "dn_city_corridor", lerp(origin, end, 0.5), 1.2);
  const t0 = scene.tick;
  scene.at(t0 + T.corUnfold, () => {
    cor.state(COR.snap);
    warn.state(3);
    particle(dim, "dn_city_dust_n", end);
    burst(dim, "dn_city_door", up(end, 1.5), 1.2, 4);
    for (const e of c.foes(end)) {
      const inEnd = dist(e.location, end) <= C.corridorCatch;
      const inHall = distToSegment(e.location, origin, end) <= 1.5;
      if (!inEnd && !inHall) continue;
      damage(e, C.corridorDamage, c.caster);
      if (inEnd) restrain(scene, e, C.corridorHold, end); // held inside the closed end room
    }
  });
  scene.at(t0 + T.corUnfold + 8, () => scene.despawn(warn));
  scene.at(t0 + T.corUnfold + T.corSnap, () => cor.state(COR.clamp));
  scene.at(t0 + T.corUnfold + C.corridorHold, () => {
    sound(dim, "dn_city_groan", end, 0.6, 1.4);
    finish(c, cor, COR.fold, T.corFold);
  });
}

// ----------------------------------------------------------------------------------- descending staircase
/** A stair-flight slams down chunk by chunk along a line through the target. */
export function stairfall(c: CityCtx, i: number): void {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, i + 1);
  const dir = norm(flat(sub(tgt.loc, c.caster.location)));
  const start = groundBelow(dim, add(tgt.loc, mul(dir, -SF_CHUNK * 2.5)));
  const centers = Array.from({ length: SF_CHUNKS }, (_, k) => add(start, mul(dir, SF_CHUNK * (k + 0.5))));
  const warns = centers.map((p) => scene.spawn("telegraph", p, { kind: 1, size: C.stairfallRadius * 0.8, state: 1 }));
  const t0 = scene.tick + 12;
  let sf: Actor | undefined;
  scene.at(t0, () => {
    sf = scene.spawn("dn_city_stairfall", start, { state: SF.slam, yaw: yawOf(dir) });
    c.hunters.add(sf);
    sound(dim, "dn_city_groan", up(start, 6), 0.8, 1.1);
  });
  centers.forEach((p, k) => {
    scene.at(t0 + T.sfFirst + k * T.sfStep, () => {
      warns[k].state(3);
      sound(dim, "dn_city_stairfall", p, 1.0, 1 - k * 0.04);
      particle(dim, "dn_city_dust_n", p);
      particle(dim, "dn_city_ring", up(p, 0.2));
      for (const e of c.foes(p)) {
        if (dist(e.location, p) > C.stairfallRadius) continue;
        damage(e, C.stairfallDamage, c.caster);
        knockback(e, p, 0.6, 0.45);
      }
    });
    scene.at(t0 + T.sfFirst + k * T.sfStep + 8, () => scene.despawn(warns[k]));
  });
  const tRest = t0 + T.sfFirst + SF_CHUNKS * T.sfStep;
  scene.at(tRest, () => sf?.state(SF.rest));
  scene.at(tRest + 16, () => { if (sf) finish(c, sf, SF.sink, T.sfSink); });
}

// ----------------------------------------------------------------------------------- living fragment
/** A roof-and-chimney fragment on baluster legs that hops after enemies and bites. */
export function fragment(c: CityCtx, i: number, until: number): void {
  const { scene, dim } = c;
  let pos = groundBelow(dim, c.spot(i * 3 + 11));
  const fr = scene.spawn("dn_city_fragment", pos, { state: FR.arrive, yaw: yawOf(sub(c.center, pos)) });
  c.hunters.add(fr);
  scene.after(7, () => { particle(dim, "dn_city_dust_n", pos); sound(dim, "dn_city_fragment", pos, 0.9, 0.8); });
  let yaw = 0;
  const step = 15;
  scene.every(step, (el) => {
    if (!fr.valid) return;
    const f = c.foes(pos);
    const target = f.length ? f[i % Math.min(f.length, 2)] : undefined;
    const goal = target ? target.location : c.spot(i * 5 + el);
    const d = sub(goal, pos);
    yaw = yawOf(d);
    if (target && dist(target.location, pos) <= C.biteRange + 0.6) {
      fr.state(FR.bite).face(yaw);
      scene.after(T.frBiteHit, () => {
        sound(dim, "dn_city_bite", pos, 1.0);
        particle(dim, "dn_city_shard", up(pos, 1.2));
        if (isAlive(target) && dist(target.location, pos) <= C.biteRange + 1.0) damage(target, C.biteDamage, c.caster);
      });
    } else {
      const len = Math.min(C.hopDistance, Math.max(0.5, Math.hypot(d.x, d.z) - C.biteRange * 0.7));
      const from = pos;
      const to = groundBelow(dim, add(up(from, 1), mul(norm(flat(d)), len)));
      fr.state(FR.hop);
      scene.span(scene.tick + 2, scene.tick + 11, (q) => {
        pos = up(lerp(from, to, q), Math.sin(q * Math.PI) * 1.1);
        fr.move(pos, yaw);
      });
      scene.after(11, () => { pos = to; particle(dim, "dn_city_dust_n", to); });
    }
    scene.after(T.frHop, () => fr.state(FR.idle));
  }, scene.tick + T.frArrive, until);
  scene.at(until, () => { sound(dim, "dn_city_bite", pos, 0.6, 0.7); finish(c, fr, FR.crumble, T.frCrumble); });
}

/** Small helper reused by the Phase II balcony drop (kept here so both phases share timing). */
export function balcony(c: CityCtx, seed: number): void {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, seed);
  let at = tgt.loc;
  const warn = scene.spawn("telegraph", at, { kind: 1, size: C.balconyRadius, state: 1 });
  const sky = c.sky(seed);
  const t0 = scene.tick;
  const bal = scene.spawn("dn_city_balcony", up(sky, -2), { state: BAL.drop, yaw: seed * 77 });
  sound(dim, "dn_city_balcony", at, 1.1);
  scene.every(1, () => { if (tgt.e && isAlive(tgt.e)) { at = groundBelow(dim, tgt.e.location); warn.move(at); } }, t0, t0 + C.balconyWarn - 8);
  const fallFrom = t0 + C.balconyWarn - 16;
  let top = up(sky, -2);
  scene.at(fallFrom, () => { top = bal.loc; });
  scene.span(fallFrom, t0 + C.balconyWarn, (q) => bal.move(lerp(top, at, easeIn(q))));
  scene.at(t0 + C.balconyWarn, () => {
    bal.state(BAL.impact);
    warn.state(3);
    particle(dim, "dn_city_dust", at);
    particle(dim, "dn_city_ring", up(at, 0.2));
    burst(dim, "dn_city_shard", up(at, 1), 1, 3);
    for (const e of c.foes(at)) {
      if (dist(e.location, at) > C.balconyRadius) continue;
      damage(e, C.balconyDamage, c.caster);
      effect(e, "slowness", C.balconySlowTicks, 1);
    }
  });
  scene.at(t0 + C.balconyWarn + 8, () => scene.despawn(warn));
  scene.at(t0 + C.balconyWarn + T.balHit, () => scene.despawn(bal));
}

/** Phase II rolling street: rolls through a target along a telegraphed line, unrolling road behind it. */
export function rollingStreet(c: CityCtx, seed: number): void {
  const { scene, dim } = c;
  const tgt = aimAt(c, c.center, seed);
  const dir = norm(flat(sub(tgt.loc, c.caster.location)));
  const a = groundBelow(dim, add(tgt.loc, mul(dir, -C.streetLength * 0.4)));
  const b = add(a, mul(dir, C.streetLength));
  const warn = scene.spawn("telegraph", a, { kind: 1, size: 1.4, state: 1 });
  scene.every(4, () => line(dim, "dn_city_chime", up(a, 0.3), up(b, 0.3), 7), scene.tick, scene.tick + 20);
  const t0 = scene.tick;
  const yaw = yawOf(dir);
  let st: Actor | undefined;
  scene.at(t0 + 8, () => { st = scene.spawn("dn_city_street", a, { state: STREET.appear, yaw }); });
  const rollTicks = Math.round(C.streetLength / C.streetSpeed);
  const hit = new Set<string>();
  scene.at(t0 + 8 + T.stAppear, () => { st?.state(STREET.roll); warn.state(3); sound(dim, "dn_city_street", a, 1.1); });
  scene.at(t0 + 8 + T.stAppear + 8, () => scene.despawn(warn));
  scene.span(t0 + 8 + T.stAppear, t0 + 8 + T.stAppear + rollTicks, (q) => {
    const p = lerp(a, b, q);
    st?.move(p, yaw);
    for (const e of c.foes(p)) {
      if (hit.has(e.id) || dist(flat(e.location), flat(p)) > C.streetWidth) continue;
      hit.add(e.id);
      damage(e, C.streetDamage, c.caster);
      shove(e, dir, C.streetShove, 0.5);
      particle(dim, "dn_city_dust", e.location);
    }
  });
  scene.at(t0 + 8 + T.stAppear + rollTicks, () => {
    if (!st) return;
    st.state(STREET.crumble);
    particle(dim, "dn_city_dust", b);
    const s = st;
    scene.after(T.stCrumble, () => scene.despawn(s));
  });
}

