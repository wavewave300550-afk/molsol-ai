import { ED04 as C } from "../config/ed04";
import { defineSpell } from "../core/registry";
import { damage, knockback, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles } from "../lib/targeting";
import {
  V3, add, angleDelta, distXZ, dot, easeOut, flat, lerp, mul, norm, polar, right, smooth, spline, sub, up, yawOf,
} from "../lib/vec";

// ---- mirror of tools/assets/ed_air.py (ACTOR, SCALE, STATE_IDS and animation timings)
const ACTOR = "dragon_air";
export const SCALE = 1.5;
const S = {
  hidden: 0, arrive: 1, idle: 2, move: 3, glide: 4, turn_l: 5, turn_r: 6, roll: 7, stoop: 8, flare: 9, land: 10,
  attack_a: 11, attack_b: 12, power: 13, react: 14, rest: 15, depart: 16, flutter: 17,
};
const ARRIVE_TICKS = 48;       // arrive 2.4 s
const ATTACK_A_HIT = 6;        // attack_a wing-slash lands at 0.3 s
const ATTACK_B_HIT = 7;        // attack_b talon rake lands at 0.35 s
const DEPART_TICKS = 32;       // depart 1.6 s
const BODY_DY = 0.85;          // flight animations ride the body this far above the origin
const RIBBON_LEN = 4.5;        // ed_air_ribbon model length at size 1 (blocks)
const CLOUD = { form: 1, part: 2, fade: 3 };
const RIBBON = { draw: 1, hold: 2, fray: 3 };
const VORTEX = { form: 1, hold: 2, burst: 3 };
const SHOCK = { charge: 1, blast: 2 };

interface Leg { from: number; to: number; at: (p: number) => V3; kind: "arrive" | "pass" | "turn" | "climb" | "hold" | "dive" | "flare" | "land"; idx: number; pilot?: number }
interface Seg { a: V3; b: V3; pass: number; born: number }

/** 2D (XZ) intersection of segments a-b and c-d, or undefined. */
function cross2(a: V3, b: V3, c: V3, d: V3): V3 | undefined {
  const r = { x: b.x - a.x, z: b.z - a.z }, s = { x: d.x - c.x, z: d.z - c.z };
  const den = r.x * s.z - r.z * s.x;
  if (Math.abs(den) < 1e-6) return undefined;
  const t = ((c.x - a.x) * s.z - (c.z - a.z) * s.x) / den;
  const u = ((c.x - a.x) * r.z - (c.z - a.z) * r.x) / den;
  if (t < 0 || t > 1 || u < 0 || u > 1) return undefined;
  return { x: a.x + r.x * t, y: (a.y + c.y) / 2, z: a.z + r.z * t };
}

function pathLen(pts: V3[]): number {
  let L = 0, prev = spline(pts, 0);
  for (let i = 1; i <= 16; i++) { const p = spline(pts, i / 16); L += Math.hypot(p.x - prev.x, p.y - prev.y, p.z - prev.z); prev = p; }
  return L;
}

/**
 * ED04 - Aether Raptor: Symphony of the Four Wings.
 * Clouds part and the four-winged feathered raptor spirals down.  It flies four fast curving passes
 * along a pentagram through the enemy formation, slashing with its wings and talons; every pass
 * leaves a suspended air-current ribbon and wherever two live ribbons cross a wind vortex spins up.
 * Finally it holds a full-spread beat high above, streamlines, and dives across the formation;
 * delayed shockwaves detonate one after another along its route while it flares, lands and
 * dissolves into feathers and wind.
 */
export default defineSpell("ed04", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.snap);
  const gy = (p: V3): number => groundBelow(dim, up(p, 6), 30).y;
  let toCaster = flat(sub(caster.location, center));
  if (Math.hypot(toCaster.x, toCaster.z) < 0.5) toCaster = mul(aim.forward, -1);
  toCaster = norm(toCaster);
  const baseAng = (Math.atan2(toCaster.z, toCaster.x) * 180) / Math.PI + 36;

  // ------------------------------------------------------------------ flight plan
  const legs: Leg[] = [];
  let cursor = 8;
  const addLeg = (kind: Leg["kind"], ticks: number, at: (p: number) => V3, idx = 0, pilot?: number): Leg => {
    const leg = { from: cursor, to: cursor + Math.max(4, Math.round(ticks)), at, kind, idx, pilot };
    legs.push(leg);
    cursor = leg.to;
    return leg;
  };
  const splineLeg = (kind: Leg["kind"], pts: V3[], speed: number, idx = 0, pilot?: number, ease?: (p: number) => number): Leg =>
    addLeg(kind, (pathLen(pts) / speed) * 20, (p) => spline(pts, ease ? ease(p) : p), idx, pilot);

  // pentagram vertices, flown 0 -> 2 -> 4 -> 1 -> 3 (four chords; three of them cross)
  const verts = [0, 1, 2, 3, 4].map((i) => {
    const p = polar(center, C.passRadius, baseAng + i * 72);
    return { x: p.x, y: gy(p) + C.passHeight, z: p.z };
  });
  const order = [0, 2, 4, 1, 3];
  const passes: V3[][] = [];
  for (let k = 0; k < 4; k++) {
    const a = verts[order[k]], b = verts[order[k + 1]];
    const side = mul(right(sub(b, a)), C.passBend * (k % 2 ? -1 : 1));
    passes.push([a, add(lerp(a, b, 0.33), side), add(lerp(a, b, 0.66), mul(side, -1)), b]);
  }

  // Stage I: spiral descent out of the cloud gap, ending at the first vertex
  const a0 = baseAng;
  const v0 = verts[0];
  const arriveLeg = addLeg("arrive", ARRIVE_TICKS, (p) => {
    const e = smooth(p);
    const ang = a0 - C.spiralTurn * (1 - e);
    const r = C.spiralR0 + (C.passRadius - C.spiralR0) * e;
    const q = polar(center, r, ang);
    return { x: q.x, y: v0.y + (C.descentHeight - C.passHeight) * Math.pow(1 - p, 1.3), z: q.z };
  }, 0, S.arrive);

  // Stage II: passes joined by climbing hairpins (rapid course corrections)
  const passLegs: Leg[] = [];
  for (let k = 0; k < 4; k++) {
    passLegs.push(splineLeg("pass", passes[k], C.passSpeed, k));
    if (k < 3) {
      const P = passes[k][3];
      const dIn = norm(flat(sub(P, spline(passes[k], 0.94))));
      const dOut = norm(flat(sub(spline(passes[k + 1], 0.06), P)));
      const outward = norm(sub(dIn, dOut));
      const hs = C.hairpinSize;
      splineLeg("turn", [P, up(add(P, mul(dIn, hs * 1.4)), C.hairpinLift * 0.7), up(add(P, mul(outward, hs * 2.2)), C.hairpinLift),
        up(sub(P, mul(dOut, hs * 1.4)), C.hairpinLift * 0.6), P], C.turnSpeed, k);
    }
  }

  // Stage III: climb to the hold point, full-spread beat, dive across the formation, flare, land
  const lastP = passes[3][3];
  let diveDir = norm(right(toCaster));
  if (distXZ(sub(center, mul(diveDir, C.holdBack)), lastP) > distXZ(add(center, mul(diveDir, C.holdBack)), lastP)) diveDir = mul(diveDir, -1);
  const g0 = center.y;
  const hold = up(sub(center, mul(diveDir, C.holdBack)), C.holdHeight);
  const lowA = { ...sub(center, mul(diveDir, C.diveLead)), y: gy(sub(center, mul(diveDir, C.diveLead))) + C.passHeight * 0.8 };
  const lowM = { ...center, y: g0 + C.passHeight * 0.8 };
  const lowB = { ...add(center, mul(diveDir, C.diveRun)), y: gy(add(center, mul(diveDir, C.diveRun))) + C.passHeight };
  const flareEnd = up(add(center, mul(diveDir, C.diveRun + 4)), 2.6);
  const landAt = groundBelow(dim, up(add(center, mul(diveDir, C.diveRun + 6)), 6), 30);
  const climbLeg = splineLeg("climb", [lastP, up(lerp(lastP, hold, 0.5), 4), hold], C.climbSpeed);
  const holdLeg = addLeg("hold", C.holdTicks, (p) => add(hold, { x: -diveDir.x * 1.2 * smooth(p), y: 0.8 * Math.sin(p * Math.PI), z: -diveDir.z * 1.2 * smooth(p) }), 0, S.power);
  const holdEnd = holdLeg.at(1);
  const divePts = [holdEnd, lerp(holdEnd, lowA, 0.6), lowA, lowM, lowB];
  const diveLeg = addLeg("dive", C.diveTicks, (p) => spline(divePts, Math.pow(p, 1.45)), 0, S.stoop);
  const flareLeg = addLeg("flare", C.flareTicks, (p) => lerp(lowB, flareEnd, easeOut(p)), 0, S.flare);
  const landLeg = addLeg("land", C.landTicks, (p) => lerp(flareEnd, landAt, smooth(p)), 0, S.land);
  const tFlightEnd = landLeg.to;
  const tDepart = tFlightEnd + C.perchTicks;
  const diveYaw = yawOf(diveDir);

  const posAt = (t: number): V3 => {
    if (t <= legs[0].from) return legs[0].at(0);
    for (const l of legs) if (t < l.to) return l.at((t - l.from) / Math.max(1, l.to - l.from));
    return legs[legs.length - 1].at(1);
  };
  const legAt = (t: number): Leg | undefined => legs.find((l) => t >= l.from && t < l.to);

  // ------------------------------------------------------------------ Stage I: clouds part
  const cloudA = scene.spawn("ed_air_cloud", up(center, C.cloudHeight), { yaw: yawOf(toCaster) + 90, size: 1.4, state: CLOUD.form });
  const cloudB = scene.spawn("ed_air_cloud", up(polar(center, 10, baseAng + 180), C.cloudHeight + 4), { yaw: yawOf(toCaster), size: 0.9, state: CLOUD.form });
  sound(dim, "ed_air_cloud", up(center, C.cloudHeight), 1.4);
  scene.at(2, () => burst(dim, "ed_air_cloud", up(center, C.cloudHeight), 5, 6));
  scene.at(8, () => {
    cloudA.state(CLOUD.part); cloudB.state(CLOUD.part);
    burst(dim, "ed_air_motes", up(center, C.cloudHeight - 3), 3, 3);
  });
  scene.at(arriveLeg.to + 4, () => { cloudA.state(CLOUD.fade); cloudB.state(CLOUD.fade); });
  scene.at(arriveLeg.to + 26, () => { scene.despawn(cloudA); scene.despawn(cloudB); });

  const dragon: Actor = scene.spawn(ACTOR, posAt(8), { yaw: yawOf(sub(posAt(9), posAt(8))), state: S.arrive });
  scene.at(9, () => burst(dim, "ed_air_feather", up(posAt(9), 1), 1.5, 3));
  scene.at(arriveLeg.from + 30, () => burst(dim, "ed_air_feather", up(posAt(scene.tick), 1), 2, 4));

  // ------------------------------------------------------------------ pilot: drives yaw + attitude states
  let cur: number = S.arrive, lockUntil = arriveLeg.to, dwellUntil = 0, yaw = dragon.yaw, dyawF = 0;
  let legIdx = -1;
  const setState = (n: number, lock = 0): void => {
    if (n !== cur) { dragon.state(n); cur = n; dwellUntil = scene.tick + 6; }
    if (lock) lockUntil = scene.tick + lock;
  };

  const passHits: Set<string>[] = [new Set(), new Set(), new Set(), new Set()];
  const diveHits = new Set<string>();
  const segs: Seg[] = [];
  const vortexAt: V3[] = [];
  let anchor: V3 | undefined;

  scene.every(1, () => {
    const t = scene.tick;
    const pos = posAt(t);
    const nxt = posAt(t + 1);
    const d = sub(nxt, pos);
    const leg = legAt(t);
    if (leg && leg.kind !== "flare" && leg.kind !== "land" && Math.hypot(d.x, d.z) > 0.04) {
      const ny = yawOf(d);
      dyawF = dyawF * 0.55 + angleDelta(yaw, ny) * 0.45;
      yaw = ny;
    } else if (leg && (leg.kind === "flare" || leg.kind === "land")) {
      yaw = diveYaw;
      dyawF = 0;
    }
    dragon.move(pos, yaw);
    if (!leg) return;

    // leg entry
    const li = legs.indexOf(leg);
    if (li !== legIdx) {
      legIdx = li;
      onLegStart(leg, pos);
    }
    if (leg.pilot !== undefined) {
      if (t >= lockUntil) setState(leg.pilot);
    } else if (t >= lockUntil && t >= dwellUntil) {
      let want: number = S.glide;
      if (dyawF > C.bankRate) want = S.turn_r;
      else if (dyawF < -C.bankRate) want = S.turn_l;
      else if (d.y > 0.12) want = S.move;
      setState(want);
    }

    if (leg.kind === "pass") passTick(leg, pos, d);
    if (leg.kind === "dive") diveTick(pos);
  }, arriveLeg.from, tFlightEnd);

  function onLegStart(leg: Leg, pos: V3): void {
    if (leg.kind === "pass") {
      const talon = leg.idx % 2 === 1;
      setState(S.glide);
      // re-trigger the one-shot next tick so consecutive passes both play their strike
      scene.after(1, () => setState(talon ? S.attack_b : S.attack_a, 14));
      sound(dim, "ed_air_ribbon", pos, 1.1, 0.9 + leg.idx * 0.07);
      sound(dim, talon ? "ed_air_chirr" : "ed_air_whistle", pos, 1.0, 1.0 + leg.idx * 0.05);
      anchor = { ...pos };
    } else if (leg.kind === "turn") {
      sound(dim, "ed_air_flap", pos, 1.0, 1.1);
      if (leg.idx === 1) setState(S.roll, 18);            // a barrel roll through the middle hairpin
      burst(dim, "ed_air_feather", up(pos, 1), 1.2, 2);
    } else if (leg.kind === "climb") {
      startCadenza();
    } else if (leg.kind === "hold") {
      dragon.skin(1);
      sound(dim, "ed_air_call", pos, 1.6);
      ring(dim, "ed_air_spark", up(pos, 1), 4, 8);
      burst(dim, "ed_air_motes", up(pos, 1), 4, 4);
    } else if (leg.kind === "dive") {
      sound(dim, "ed_air_dive", pos, 1.6);
      particle(dim, "ed_air_boom", up(pos, 1));
      burst(dim, "ed_air_feather", up(pos, 1), 1.5, 3);
    } else if (leg.kind === "flare") {
      sound(dim, "ed_air_flare", pos, 1.3);
      burst(dim, "ed_air_gust", up(pos, 1), 1.0, 3);
      burst(dim, "ed_air_feather", up(pos, 1.5), 2, 5);
    } else if (leg.kind === "land") {
      dragon.skin(0);
      scene.at(leg.to - 4, () => { particle(dim, "fx_dust", landAt); particle(dim, "ed_air_gust", up(landAt, 0.3)); });
    }
  }

  // ------------------------------------------------------------------ Stage II mechanics
  function passTick(leg: Leg, pos: V3, d: V3): void {
    const k = leg.idx;
    // air-current ribbon laid down behind the dragon
    if (anchor && (distXZ(anchor, pos) >= C.ribbonSeg || scene.tick === leg.to - 1)) {
      if (distXZ(anchor, pos) > 1.2) layRibbon(anchor, pos, k);
      anchor = { ...pos };
    }
    // wing slash / talon rake along the path, from the strike frame on
    const hitFrame = k % 2 === 1 ? ATTACK_B_HIT : ATTACK_A_HIT;
    if (scene.tick < leg.from + 1 + hitFrame || (scene.tick - leg.from) % 2) return;
    const side = right(d);
    for (const e of hostiles(dim, pos, C.slashRadius + 2.5, caster)) {
      if (passHits[k].has(e.id)) continue;
      const l = e.location;
      if (distXZ(l, pos) > C.slashRadius || Math.abs(l.y - pos.y) > 4) continue;
      passHits[k].add(e.id);
      if (!damage(e, C.slashDamage, caster)) continue;
      const s = dot(sub(l, pos), side) >= 0 ? 1 : -1;
      shove(e, mul(side, s), C.slashKnockH, C.slashKnockV);
      particle(dim, "ed_air_streak", up(l, 1));
      particle(dim, "ed_air_spark", up(l, 1.2));
      sound(dim, "ed_air_slash", l, 0.9, 0.95 + k * 0.06);
    }
  }

  function layRibbon(a: V3, b: V3, k: number): void {
    const len = distXZ(a, b);
    const mid = up(lerp(a, b, 0.5), BODY_DY);
    const rib = scene.spawn("ed_air_ribbon", mid, { yaw: yawOf(sub(b, a)), size: (len / RIBBON_LEN) * 1.08, state: RIBBON.draw });
    scene.after(10, () => rib.state(RIBBON.hold));
    scene.after(C.ribbonLife, () => rib.state(RIBBON.fray));
    scene.after(C.ribbonLife + 17, () => scene.despawn(rib));
    particle(dim, "ed_air_streak", mid);
    const seg: Seg = { a: { ...a }, b: { ...b }, pass: k, born: scene.tick };
    // designated currents: a vortex spins up wherever this ribbon crosses a still-suspended one
    for (const o of segs) {
      if (o.pass === k || scene.tick - o.born > C.ribbonLife) continue;
      const x = cross2(seg.a, seg.b, o.a, o.b);
      if (!x || vortexAt.length >= C.maxVortices || vortexAt.some((v) => distXZ(v, x) < C.vortexMerge)) continue;
      vortexAt.push(x);
      spawnVortex(x);
    }
    segs.push(seg);
  }

  function spawnVortex(x: V3): void {
    const at = groundBelow(dim, up(x, 4), 20);
    const vx = scene.spawn("ed_air_vortex", at, { size: 1.0, state: VORTEX.form, yaw: Math.random() * 360 });
    sound(dim, "ed_air_vortex", at, 1.3);
    ring(dim, "ed_air_gust", up(at, 0.5), 2.5, 6);
    const on = scene.tick + 8;
    scene.at(on, () => vx.state(VORTEX.hold));
    scene.every(C.vortexEvery, () => {
      particle(dim, "ed_air_streak", up(at, 2));
      for (const e of hostiles(dim, at, C.vortexRadius, caster)) {
        const pull = flat(sub(at, e.location));
        if (Math.hypot(pull.x, pull.z) > 0.6) shove(e, pull, C.vortexPull, 0.12);
        damage(e, C.vortexDamage, caster);
      }
    }, on, on + C.vortexTicks);
    scene.at(on + C.vortexTicks, () => {
      vx.state(VORTEX.burst);
      sound(dim, "ed_air_boom", at, 0.8, 1.3);
      burst(dim, "ed_air_feather_burst", up(at, 2.5), 1.5, 2);
      particle(dim, "ed_air_shock", up(at, 0.3));
      for (const e of hostiles(dim, at, C.vortexRadius + 0.8, caster)) {
        damage(e, C.vortexBurstDamage, caster);
        knockback(e, at, 0.4, C.vortexLaunch);
      }
    });
    scene.at(on + C.vortexTicks + 13, () => scene.despawn(vx));
  }

  // ------------------------------------------------------------------ Stage III mechanics
  const shocks: { at: V3; s: number; tele?: Actor; fired: boolean }[] = [];
  const shockHits = new Map<string, number>();
  const s0 = dot(sub(lowA, center), diveDir), s1 = dot(sub(lowB, center), diveDir);

  function startCadenza(): void {
    // telegraph the dive line on the ground (fills over 2 s)
    for (let i = 0; i < C.shockCount; i++) {
      const f = C.shockCount === 1 ? 0.5 : i / (C.shockCount - 1);
      const s = s0 + (s1 - s0) * (0.1 + 0.85 * f);
      const p = add(center, mul(diveDir, s));
      const at = groundBelow(dim, up(p, 6), 30);
      shocks.push({ at, s, tele: scene.spawn("telegraph", at, { kind: 2, size: C.shockRadius, state: 4 }), fired: false });
    }
    line(dim, "ed_air_motes", up(shocks[0].at, 0.5), up(shocks[shocks.length - 1].at, 0.5), 4);
  }

  let passOrder = 0;
  function diveTick(pos: V3): void {
    const sNow = dot(sub(pos, center), diveDir);
    // shock knots form where the dragon breaks through, detonating later one after another
    for (const sh of shocks) {
      if (sh.fired || sNow < sh.s) continue;
      sh.fired = true;
      const order = passOrder++;
      const knot = scene.spawn("ed_air_shock", sh.at, { yaw: diveYaw, size: 1.4, state: SHOCK.charge });
      particle(dim, "ed_air_boom", up(sh.at, 1.2));
      const tBlast = Math.max(diveLeg.to + 2, scene.tick + C.shockDelay) + order * C.shockStagger;
      scene.at(tBlast - 8, () => sh.tele?.state(2));
      scene.at(tBlast, () => detonate(sh.at, knot, sh.tele));
    }
    // the dive itself strikes everything it grazes
    for (const e of hostiles(dim, pos, C.diveContactRadius + 2, caster)) {
      if (diveHits.has(e.id) || distXZ(e.location, pos) > C.diveContactRadius || Math.abs(e.location.y - pos.y) > 3.5) continue;
      diveHits.add(e.id);
      if (damage(e, C.diveDamage, caster)) {
        knockback(e, pos, C.diveKnockH, C.diveKnockV);
        particle(dim, "ed_air_spark", up(e.location, 1));
      }
    }
    if (scene.tick % 2 === 0) particle(dim, "ed_air_streak", up(pos, BODY_DY));
  }

  function detonate(at: V3, knot: Actor, tele?: Actor): void {
    knot.state(SHOCK.blast);
    if (tele) { tele.state(3); scene.after(8, () => scene.despawn(tele)); }
    scene.after(13, () => scene.despawn(knot));
    sound(dim, "ed_air_boom", at, 1.4);
    particle(dim, "ed_air_shock", up(at, 0.25));
    particle(dim, "ed_air_boom", up(at, 1.5));
    burst(dim, "ed_air_gust", up(at, 0.6), 1.5, 3);
    for (const e of hostiles(dim, at, C.shockRadius, caster)) {
      const n = shockHits.get(e.id) ?? 0;
      if (n >= C.maxShockHits) continue;
      shockHits.set(e.id, n + 1);
      if (!damage(e, C.shockDamage, caster)) continue;
      // outward from the dive line (perpendicular to the route)
      const rel = flat(sub(e.location, at));
      const along = dot(rel, diveDir);
      const out = sub(rel, mul(diveDir, along));
      const dir = Math.hypot(out.x, out.z) > 0.2 ? out : right(diveDir);
      shove(e, dir, C.shockKnockH, C.shockKnockV);
    }
  }

  // ------------------------------------------------------------------ landing, perch and dissolution
  scene.at(tFlightEnd, () => {
    dragon.move(landAt, diveYaw);
    dragon.state(S.idle);
    sound(dim, "ed_air_chirr", landAt, 1.0);
  });
  scene.at(tDepart, () => {
    dragon.state(S.depart);
    sound(dim, "ed_air_depart", up(landAt, 2), 1.3);
  });
  scene.at(tDepart + 10, () => { burst(dim, "ed_air_feather_burst", up(landAt, 3), 2, 3); burst(dim, "ed_air_feather", up(landAt, 3), 3, 4); });
  scene.at(tDepart + 20, () => { burst(dim, "ed_air_cloud", up(landAt, 4), 2, 2); burst(dim, "ed_air_motes", up(landAt, 4), 3, 3); });
  scene.endAt(tDepart + DEPART_TICKS + 4);
});
