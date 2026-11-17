import { Entity, Vector3 } from "@minecraft/server";
import { ED03 as C } from "../config/ed03";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { V3, add, clamp, distXZ, dot, easeIn, flat, lerp, mul, norm, polar, right, smooth, sub, up, yawOf } from "../lib/vec";

// ---- mirror of tools/assets/ed_tide.py (ACTOR, SCALE, STATE_IDS, LENGTHS, HITS)
const DRAGON = { actor: "dragon_tide", scale: 2.0 };
const D = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9,
  rest: 10, depart: 11, swim: 12, land: 13, roar: 14, attack_c: 15 };
/** Animation lengths and hit frames in ticks (LENGTHS / HITS in ed_tide.py x 20). */
const T = { arrive: 20, land: 16, landHit: 5, power: 30, sweep: 30, sweepHit: [10, 21], flare: 22, flareHit: 9,
  roar: 28, strike: 34, strikeHit: 18, depart: 32 };
const STREAM = { hidden: 0, form: 1, hold: 2, fade: 3 };
const MASS = { hidden: 0, gather: 1, hold: 2, burst: 3, disperse: 4 };
const CUR = { hidden: 0, form: 1, flow: 2, freeze: 3, spiral: 4, ice: 5, rise: 6, shatter: 7 };
const CROWN = { hidden: 0, assemble: 1, hold: 2, frac1: 3, frac2: 4, frac3: 5 };
const SHARD = { hidden: 0, launch: 1, hit: 2 };
const FROZEN = { hidden: 0, encase: 1, hold: 2, shatter: 3 };
/** Model radii at size 1 (blocks): current arc and crown ring. Current arc sweep in degrees. */
const CUR_R = 4, CROWN_R = 4, CUR_SWEEP = 160;

// ---- timeline (ticks)
const tMass = 4, tArrive = 18, tSwim = tArrive + T.arrive, tLand = 70, tPower = tLand + T.land;
const tSweep = 114, tFlare = tSweep + T.sweep, tFreeze = tFlare + T.flareHit + 2, tSpiral = 174;
const tRoar = 182, tCrown = 188, tRise = 190, tStrike = tRoar + T.roar - 2, tHit = tStrike + T.strikeHit;
const WAVE_GAP = 9;

interface Current { a: Actor; R: number; dir: V3; side: V3; born: number; touched: Set<string> }
interface Frozen { e: Entity; release: () => void; ice: Actor }

/**
 * ED03 - Abyssal Cryotitan: The Frozen Tidal Crown.
 * I   The Rising Deep: water streams spiral into a suspended mass; the sail-backed tide dragon forms inside it,
 *     swims out and spirals down to land beside the enemy group (landing wave shoves them).
 * II  The Cryogenic Sail: the sail crystallises front-to-back; a two-way tail sweep throws four curving currents
 *     around the group that carry enemies along; a sail flare sends a freezing front from the sail and tail
 *     into the currents, which freeze (enemies on them are frozen in place) and twist into spiral ice.
 * III The Frozen Crown: it roars, the spirals rise into a crown of ice around the targets, a telegraphed tail
 *     strike fractures the crown in three inward waves of ice shards, then a finishing burst; the dragon
 *     dissolves back into water.
 */
export default defineSpell("ed03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.snap);
  const fwd = norm(flat(aim.forward));
  const rt = right(fwd);
  const tb = blocksFor(scene);

  // ---- the enemy group and the stage geometry
  const group = hostiles(dim, center, C.radius, caster, C.maxTargets);
  let G: V3 = center;
  if (group.length) {
    let x = 0, z = 0;
    for (const e of group) { x += e.location.x; z += e.location.z; }
    G = groundBelow(dim, { x: x / group.length, y: center.y + 1, z: z / group.length });
  }
  const spread = group.reduce((m, e) => Math.max(m, distXZ(e.location, G)), 0);
  const L = groundBelow(dim, up(add(center, mul(fwd, C.landBeyond)), 2));
  const roomR = Math.max(C.currentMin, distXZ(G, L) - 2.5);
  const Rcur = clamp(spread + C.currentPad, C.currentMin, Math.min(C.currentMax, roomR));
  const Rc = clamp(spread + C.crownPad, C.crownMin, Math.min(C.crownMax, Math.max(C.crownMin, roomR)));
  const yawLand = yawOf(rt); // head to the caster's right; the dragon's right flank faces the caster / enemies

  // spiral swim path: ends at L moving along +rt
  const Q = sub(L, mul(fwd, C.spiralRadius));
  const pathPos = (p: number): V3 => {
    const phi = ((90 + C.spiralSweep * (1 - p)) * Math.PI) / 180;
    const h = add(Q, add(mul(rt, Math.cos(phi) * C.spiralRadius), mul(fwd, Math.sin(phi) * C.spiralRadius)));
    return { x: h.x, y: L.y + C.massHeight * (1 - smooth(p)), z: h.z };
  };
  const pathYaw = (p: number): number => yawOf(flat(sub(pathPos(Math.min(1, p + 0.01)), pathPos(Math.max(0, p - 0.01)))));
  const M = pathPos(0);
  const hip = sub(L, mul(rt, C.hipBack));
  const tailTip = (alphaDeg: number): V3 => {
    const a = (alphaDeg * Math.PI) / 180;
    return up(add(hip, mul(add(mul(rt, -Math.cos(a)), mul(fwd, -Math.sin(a))), C.tailReach)), 1);
  };
  const sailPeak = up(sub(L, mul(rt, 0.9)), 9);

  // =====================================================================================================
  // Stage I - The Rising Deep
  sound(dim, "ed_tide_currents", M, 1.2);
  const streams: { a: Actor; ang: number; dy: number; prev: V3 }[] = [];
  for (let k = 0; k < 5; k++) {
    const ang = k * 72 + 15, dy = -5 + (k % 3) * 2.5;
    const p0 = up(add(M, add(mul(rt, Math.cos((ang * Math.PI) / 180) * 11), mul(fwd, Math.sin((ang * Math.PI) / 180) * 11))), dy);
    const a = scene.spawn("ed_tide_stream", p0, { state: STREAM.form, size: 1.4, yaw: yawOf(sub(M, p0)) });
    streams.push({ a, ang, dy, prev: p0 });
  }
  scene.at(8, () => streams.forEach((s) => s.a.state(STREAM.hold)));
  scene.span(1, 24, (p) => {
    const e = smooth(p);
    for (const s of streams) {
      const ang = ((s.ang + 200 * e) * Math.PI) / 180, r = 11 * (1 - e) + 0.4;
      const pos = up(add(M, add(mul(rt, Math.cos(ang) * r), mul(fwd, Math.sin(ang) * r))), s.dy * (1 - e));
      s.a.move(pos, yawOf(flat(sub(pos, s.prev))));
      s.prev = pos;
    }
  });
  scene.every(6, (el) => { const s = streams[(el / 6) % 5]; particle(dim, "ed_tide_spray", s.prev); }, 2, 24);
  scene.at(22, () => { streams.forEach((s) => s.a.state(STREAM.fade)); burst(dim, "ed_tide_bubble", M, 3, 6); });
  scene.at(27, () => streams.forEach((s) => scene.despawn(s.a)));

  let mass: Actor | undefined;
  scene.at(tMass, () => {
    mass = scene.spawn("ed_tide_mass", M, { state: MASS.gather, size: C.massSize });
    sound(dim, "ed_tide_mass", M, 1.3);
  });
  scene.at(tMass + 20, () => mass?.state(MASS.hold));
  scene.every(5, () => { particle(dim, "ed_tide_bubble", M); particle(dim, "ed_tide_mist", up(M, -4)); }, tMass + 6, 44);

  // the dragon forms inside the mass, swims out through it and spirals down
  const dragon = scene.spawn(DRAGON.actor, M, { state: D.hidden, yaw: pathYaw(0) });
  scene.at(tArrive, () => dragon.state(D.arrive).move(M, pathYaw(0)));
  scene.span(tArrive, tSwim, (p) => { const q = 0.1 * easeIn(p); dragon.move(pathPos(q), pathYaw(q)); });
  scene.at(30, () => { mass?.state(MASS.burst); burst(dim, "ed_tide_splash", M, 4, 6); });
  scene.at(tSwim, () => dragon.state(D.swim));
  scene.span(tSwim, tLand, (p) => { const q = 0.1 + 0.9 * p; dragon.move(pathPos(q), pathYaw(q)); });
  scene.every(4, (el) => particle(dim, "ed_tide_trail", pathPos(0.1 + (0.9 * el) / (tLand - tSwim))), tSwim, tLand);
  scene.at(42, () => { mass?.state(MASS.disperse); sound(dim, "ed_tide_splash", M, 1.2, 0.7); });
  scene.every(4, () => particle(dim, "ed_tide_rain", up(M, -3)), 42, 62);
  scene.at(63, () => { if (mass) scene.despawn(mass); });

  // landing: the wave of its arrival washes the enemies back
  scene.at(tLand, () => dragon.state(D.land).move(L, yawLand));
  scene.at(tLand + T.landHit, () => {
    sound(dim, "ed_tide_splash", L, 1.4, 0.85);
    particle(dim, "ed_tide_frost_ring", up(L, 0.2));
    ring(dim, "ed_tide_splash", up(L, 0.3), 3, 6);
    for (const e of hostiles(dim, L, C.landRadius, caster)) {
      damage(e, C.landDamage, caster);
      knockback(e, L, C.landKnockH, C.landKnockV);
    }
  });

  // =====================================================================================================
  // Stage II - The Cryogenic Sail
  scene.at(tPower, () => {
    dragon.state(D.power).skin(1); // sail crystallises front to back (client frost) and the cryo skin glows
    particle(dim, "ed_tide_mist", sailPeak);
  });
  scene.every(5, (el) => {
    const f = ((el / 5) % 4) / 3;
    particle(dim, "ed_tide_flake", up(sub(L, mul(rt, -1.5 + 3.5 * f)), 7 + f));
  }, tPower + 6, tRoar);
  scene.at(tPower + T.power, () => dragon.state(D.idle));

  const currents: Current[] = [];
  scene.at(tSweep, () => dragon.state(D.attack_a));
  T.sweepHit.forEach((h, w) => scene.at(tSweep + h, () => throwCurrents(w * 2, w === 0 ? 55 : 28)));

  function throwCurrents(k0: number, alpha: number): void {
    const tip = tailTip(alpha);
    let dir = norm(flat(sub(tip, G)));
    if (distXZ(tip, G) < 0.5) dir = mul(fwd, -1);
    sound(dim, "ed_tide_flow", tip, 1.2, 0.95 + k0 * 0.05);
    for (let k = k0; k < k0 + 2; k++) {
      const R = Math.max(C.currentMin * 0.7, Rcur * C.currentScale[k]);
      const kind = k % 2;
      const side = kind === 0 ? right(dir) : mul(right(dir), -1);
      const a = scene.spawn("ed_tide_current", G, { kind, size: R / CUR_R, state: CUR.form, yaw: yawOf(dir) });
      const c: Current = { a, R, dir, side, born: scene.tick, touched: new Set() };
      currents.push(c);
      line(dim, "ed_tide_spray", tip, arcPoint(c, 0, 1), 5);
      scene.after(16, () => a.state(CUR.flow));
    }
  }
  function arcPoint(c: Current, deg: number, dy = 0): V3 {
    const r = (deg * Math.PI) / 180;
    return { x: G.x + c.R * (Math.cos(r) * c.dir.x + Math.sin(r) * c.side.x), y: G.y + dy,
      z: G.z + c.R * (Math.cos(r) * c.dir.z + Math.sin(r) * c.side.z) };
  }
  function arcOf(c: Current, p: V3): { r: number; deg: number } {
    const v = flat(sub(p, G));
    return { r: Math.hypot(v.x, v.z), deg: (Math.atan2(dot(v, c.side), dot(v, c.dir)) * 180) / Math.PI };
  }
  const reach = () => Math.max(Rcur * 1.2, C.currentMin) + C.freezeWidth + 1;

  // water-based displacement: enemies inside a flowing current are carried along it
  scene.every(C.shoveEvery, () => {
    if (!currents.length) return;
    for (const e of hostiles(dim, G, reach(), caster)) {
      for (const c of currents) {
        const extent = Math.min(CUR_SWEEP, (scene.tick - c.born) * 17);
        const { r, deg } = arcOf(c, e.location);
        if (Math.abs(r - c.R) > C.currentWidth || deg < -12 || deg > extent) continue;
        const a = (deg * Math.PI) / 180;
        const tangent = add(mul(c.dir, -Math.sin(a)), mul(c.side, Math.cos(a)));
        const inward = norm(flat(sub(G, e.location)));
        shove(e, add(tangent, mul(inward, (r - c.R) * 0.25)), C.currentShove, 0.06);
        if (!c.touched.has(e.id)) { c.touched.add(e.id); damage(e, C.currentDamage, caster); particle(dim, "ed_tide_spray", e.location); }
        break;
      }
    }
  }, tSweep + T.sweepHit[0], tFreeze + 4);
  scene.every(4, (el) => {
    for (const c of currents) if (scene.tick - c.born > 6) particle(dim, "ed_tide_spray", arcPoint(c, ((el * 37) % CUR_SWEEP), 0.6));
  }, tSweep + T.sweepHit[0] + 4, tFreeze);

  // sail flare: the freezing front leaves the sail and the tail and runs into each current
  scene.at(tFlare, () => dragon.state(D.attack_c));
  scene.at(tFlare + T.flareHit, () => {
    sound(dim, "ed_tide_freeze", G, 1.4);
    burst(dim, "ed_tide_glint", sailPeak, 2, 6);
    const tip = tailTip(10);
    for (const c of currents) {
      line(dim, "ed_tide_frostline", sailPeak, arcPoint(c, 0, 1), 8);
      line(dim, "ed_tide_frostline", tip, arcPoint(c, 0, 0.6), 4);
    }
  });
  scene.at(tFlare + T.flare, () => dragon.state(D.idle));

  const frozen = new Map<string, Frozen>();
  const tShatter = tHit + 2 * WAVE_GAP + C.shardFlight;
  function freeze(e: Entity): void {
    if (frozen.has(e.id) || !isAlive(e)) return;
    damage(e, C.freezeDamage, caster);
    if (!isAlive(e)) return;
    const at = { ...e.location };
    const release = restrain(scene, e, Math.max(10, tShatter - scene.tick + 2), at);
    const ice = scene.spawn("ed_tide_frozen", at, { state: FROZEN.encase });
    scene.after(10, () => ice.state(FROZEN.hold));
    frozen.set(e.id, { e, release, ice });
    particle(dim, "ed_tide_flake", up(at, 1));
    particle(dim, "ed_tide_splinter", up(at, 0.6));
    sound(dim, "ed_tide_shatter", at, 0.6, 1.3);
  }
  scene.at(tFreeze, () => currents.forEach((c) => c.a.state(CUR.freeze)));
  scene.every(1, (el) => {
    const front = 12.5 * el - 10; // freeze anim: segment k ices at 0.08 s * k, front runs from the dragon's side
    for (const c of currents) particle(dim, "ed_tide_frostline", arcPoint(c, clamp(front, 0, CUR_SWEEP), 0.8));
    for (const e of hostiles(dim, G, reach(), caster)) {
      if (frozen.has(e.id)) continue;
      for (const c of currents) {
        const { r, deg } = arcOf(c, e.location);
        if (Math.abs(r - c.R) <= C.freezeWidth && deg >= -15 && deg <= front) { freeze(e); break; }
      }
    }
  }, tFreeze, tFreeze + 18);

  // the frozen currents twist into spiral ice structures that are real obstacles
  const barriers: V3[] = [];
  scene.at(tSpiral, () => {
    sound(dim, "ed_tide_spiral", G, 1.3);
    currents.forEach((c) => c.a.state(CUR.spiral));
    const foes = hostiles(dim, G, reach() + 2, caster);
    for (const c of currents) {
      for (let k = 1; k < 8; k += 2) {
        const p = groundBelow(dim, up(arcPoint(c, (k + 0.5) * (CUR_SWEEP / 8)), 2));
        if (foes.some((e) => distXZ(e.location, p) < 1.4) || distXZ(caster.location, p) < 1.6) continue;
        const x = Math.floor(p.x), y = Math.floor(p.y), z = Math.floor(p.z);
        if (tb.column(x, y, z, C.barrierHeight) > 0) barriers.push({ x, y, z });
        particle(dim, "ed_tide_glint", up(p, 1.5));
      }
    }
  });
  scene.at(tSpiral + 12, () => currents.forEach((c) => c.a.state(CUR.ice)));

  // =====================================================================================================
  // Stage III - The Frozen Crown
  scene.at(tRoar, () => {
    dragon.state(D.roar);
    particle(dim, "ed_tide_frost_ring", up(G, 0.3));
    ring(dim, "ed_tide_mist", up(G, 1), Rc, 6);
  });
  let crown: Actor | undefined;
  scene.at(tCrown, () => {
    crown = scene.spawn("ed_tide_crown", G, { state: CROWN.assemble, size: Rc / CROWN_R });
    sound(dim, "ed_tide_crown", G, 1.5);
    tb.place(up(G, 3), LIGHT);
    ring(dim, "ed_tide_rune", up(G, 2), Rc, 6);
  });
  scene.at(tCrown + 24, () => crown?.state(CROWN.hold));
  scene.at(tRise, () => {
    currents.forEach((c) => { c.a.state(CUR.rise); particle(dim, "ed_tide_glint", arcPoint(c, 80, 3)); });
    for (const b of barriers) tb.removeColumn(b.x, b.y, b.z, C.barrierHeight);
  });
  scene.at(tRise + 16, () => currents.forEach((c) => scene.despawn(c.a)));
  scene.at(tRoar + T.roar, () => dragon.state(D.idle));

  // the telegraphed tail strike
  let warn: Actor | undefined;
  scene.at(tHit - 20, () => { warn = scene.spawn("telegraph", G, { kind: 2, size: Rc + C.finalExtra, state: 1 }); });
  scene.at(tStrike, () => dragon.state(D.attack_b));
  scene.at(tHit, () => {
    warn?.state(2);
    const imp = groundBelow(dim, tailTip(70));
    sound(dim, "ed_tide_impact", imp, 1.5);
    particle(dim, "ed_tide_splash", imp);
    particle(dim, "fx_shock", up(imp, 0.2));
  });

  // the crown fractures in three successive waves; each sends sharp ice toward the enemies
  for (let w = 0; w < 3; w++) {
    scene.at(tHit + w * WAVE_GAP, () => {
      crown?.state(CROWN.frac1 + w);
      sound(dim, "ed_tide_fracture", G, 1.4, 0.9 + w * 0.12);
      ring(dim, "ed_tide_splinter", up(G, 2 + w), Rc, 8, w * 20);
      launchShards(w);
    });
  }
  function launchShards(w: number): void {
    const foes = hostiles(dim, G, Rc + 3, caster, C.maxTargets);
    const goals: { e?: Entity; at: V3; dir: V3 }[] = foes.map((e) => {
      const v = flat(sub(e.location, G));
      return { e, at: e.location, dir: Math.hypot(v.x, v.z) > 0.3 ? norm(v) : fwd };
    });
    if (!goals.length) for (let k = 0; k < 4; k++) {
      const at = polar(G, 1.2, k * 90 + w * 30);
      goals.push({ at, dir: norm(flat(sub(polar(G, 1, k * 90 + w * 30), G))) });
    }
    for (const g of goals) {
      const start = up(add(G, mul(g.dir, Rc)), 2.5 + w * 0.8);
      const target = () => up(g.e && isAlive(g.e) ? g.e.location : g.at, 1);
      const s = scene.spawn("ed_tide_shard", start, { state: SHARD.launch, size: 1.3, yaw: yawOf(sub(target(), start)) });
      scene.span(scene.tick + 1, scene.tick + 1 + C.shardFlight, (p) => {
        const to = target();
        s.move(lerp(start, to, easeIn(p) * 0.85 + p * 0.15), yawOf(flat(sub(to, start))));
      });
      scene.after(C.shardFlight + 1, () => {
        s.state(SHARD.hit);
        const at = target();
        particle(dim, "ed_tide_splinter", at);
        sound(dim, "ed_tide_shatter", at, 0.9, 0.9 + w * 0.15);
        if (g.e && isAlive(g.e)) damage(g.e, C.shardDamage[w], caster);
        for (const e of hostiles(dim, at, 1.4, caster)) if (e !== g.e) damage(e, C.shardDamage[w] * 0.5, caster);
      });
      scene.after(C.shardFlight + 8, () => scene.despawn(s));
    }
  }

  // thaw: encasements shatter with the last wave of shards
  scene.at(tShatter, () => {
    for (const f of frozen.values()) {
      f.release();
      f.ice.state(FROZEN.shatter);
      const ice = f.ice;
      scene.after(8, () => scene.despawn(ice));
      if (isAlive(f.e)) { effect(f.e, "slowness", C.thawSlowTicks, C.thawSlowAmp); particle(dim, "ed_tide_splinter", up(f.e.location, 1)); }
    }
  });

  // the finishing burst of the crown
  const tFinal = tShatter + 6;
  scene.at(tFinal, () => {
    warn?.state(3);
    sound(dim, "ed_tide_finale", G, 1.6);
    particle(dim, "ed_tide_shock", up(G, 0.3));
    particle(dim, "fx_flash", up(G, 2));
    burst(dim, "ed_tide_splinter", up(G, 2), Rc * 0.6, 8);
    ring(dim, "ed_tide_mist", up(G, 0.8), Rc, 8);
    for (const e of hostiles(dim, G, Rc + C.finalExtra, caster)) {
      damage(e, C.finalDamage, caster);
      knockback(e, G, C.finalKnockH, C.finalKnockV);
    }
  });
  scene.at(tFinal + 6, () => { if (crown) scene.despawn(crown); });
  scene.at(tFinal + 8, () => { if (warn) scene.despawn(warn); });

  // departure: the dragon dissolves back into dispersing water
  const tDepart = tFinal + 4;
  scene.at(tDepart, () => dragon.state(D.depart));
  scene.every(6, (el) => particle(dim, "ed_tide_mist", up(sub(L, mul(rt, -2 + el * 0.2)), 2 + el * 0.08)), tDepart + 6, tDepart + T.depart);
  scene.at(tDepart + 20, () => ring(dim, "ed_tide_splash", up(L, 0.3), 3.5, 6));
  scene.at(tDepart + T.depart, () => scene.despawn(dragon));
  scene.endAt(tDepart + T.depart + 4);
});
