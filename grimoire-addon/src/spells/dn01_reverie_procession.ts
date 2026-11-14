import { Entity, Vector3 } from "@minecraft/server";
import { DN01 as C } from "../config/dn01";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback, shove } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, clamp, dist, distToSegment, distXZ, dot, flat, lerp, mul, norm, right, smooth, spline, sub, up, yawOf } from "../lib/vec";

// Animation states (tools/assets/dn_parade.py *_STATES)
const HORSE = { hidden: 0, arrive: 1, parade: 2, charge: 3, depart: 4 };
const STAG = { hidden: 0, arrive: 1, parade: 2, leapA: 3, leapB: 4, depart: 5 };
const BIRD = { hidden: 0, arrive: 1, glide: 2, swoopA: 3, swoopB: 4, depart: 5 };
const DOLL = { hidden: 0, arrive: 1, float: 2, pulseA: 3, pulseB: 4, depart: 5 };
const ROAD = { hidden: 0, unroll: 1, hold: 2, rollup: 3 };
const MOON = { hidden: 0, rise: 1, sleep: 2, set: 3 };
const MARK = { hidden: 0, appear: 1, hold: 2, flare: 3, vanish: 4 };
/** Animation lengths / key frames in ticks -- must match dn_parade.py. */
const T = {
  roadAnim: 16, moonRise: 28, moonSet: 28, markAppear: 7, markFlare: 8, markVanish: 8,
  horseDepart: 22,
  stagLeap: 22, stagLaunch: 6, stagLand: 17, stagDepart: 24,
  birdSwoop: 24, birdLowFrom: 8, birdLowTo: 16, birdDepart: 24,
  dollPulsePeak: 3, dollDepart: 24,
};
/** Road model length in blocks at size 1 (segments are scaled slightly larger than their spacing so they overlap). */
const ROAD_MODEL_LEN = 3.3;

type Who = "horse" | "stag" | "bird" | "doll";
const ORDER: Who[] = ["horse", "stag", "bird", "doll"];
const ACTOR: Record<Who, string> = { horse: "dn_parade_horse", stag: "dn_parade_stag", bird: "dn_parade_bird", doll: "dn_parade_doll" };

/**
 * DN01 - Reverie Procession: Parade of the Sleeping Moon.
 * An ivory dream-road unrolls through the air from behind the caster, over an arc beneath the
 * Sleeping Moon and down toward the enemies.  A porcelain horse, a mist-glass stag, a curtain-winged
 * bird and a floating star doll parade along it in order, then peel off on their own attack paths:
 * a piercing gallop line, three telegraphed bounds, swooping arcs and a syncopated starburst.
 * Every different creature that strikes the same enemy adds a crescent to its mark and bonus damage;
 * all four make a full moon.
 */
export default defineSpell("dn01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.snap);
  const fwd = aim.forward;
  const side = right(fwd);
  const base = { ...caster.location };

  // ------------------------------------------------------------------ the dream-road path
  const reach = clamp(dot(flat(sub(center, base)), fwd), C.minReach, C.maxReach);
  const endXZ = add(base, mul(fwd, reach - C.endBack));
  const endGround = groundBelow(dim, { x: endXZ.x, y: Math.max(center.y, base.y) + 3, z: endXZ.z });
  const start = up(add(base, mul(fwd, -C.startBehind)), C.startHeight);
  const end = up(endGround, C.endHeight);
  const ctrl: Vector3[] = [start];
  for (const f of [0.25, 0.5, 0.75]) {
    const p = lerp(start, end, f);
    ctrl.push(add(up(p, C.apex * Math.pow(Math.sin(Math.PI * f), 0.8)), mul(side, C.curve * Math.sin(2 * Math.PI * f))));
  }
  ctrl.push(end);
  const N = 96;
  const P: Vector3[] = [];
  const S: number[] = [];
  for (let i = 0; i <= N; i++) {
    P.push(spline(ctrl, i / N));
    S.push(i ? S[i - 1] + dist(P[i], P[i - 1]) : 0);
  }
  const L = S[N];
  /** Point and unit tangent at arc length s along the road. */
  function road(s: number): { p: Vector3; d: Vector3 } {
    const x = clamp(s, 0, L);
    let i = 1;
    while (i < N && S[i] < x) i++;
    const f = (x - S[i - 1]) / Math.max(1e-6, S[i] - S[i - 1]);
    return { p: lerp(P[i - 1], P[i], f), d: norm(sub(P[i], P[i - 1])) };
  }
  const pitch = (d: Vector3): number => (Math.atan2(d.y, Math.hypot(d.x, d.z)) * 180) / Math.PI;
  const tilts = new Map<Actor, number>();
  function setTilt(a: Actor, deg: number): void {
    const v = clamp(Math.round(deg), -55, 55);
    if (tilts.get(a) === v) return;
    tilts.set(a, v);
    a.prop("tilt", v);
  }

  // ------------------------------------------------------------------ schedule (all derived up front)
  const n = clamp(Math.round(L / C.segSpacing), 5, C.maxSegments);
  const spacing = L / n;
  const travel = Math.max(20, Math.ceil((L / C.paradeSpeed) * 20));
  const arrive = C.spawnAt.map((t) => t + C.gateHold + travel + 1);
  const horseRun = Math.max(10, Math.round((C.horseLength / C.horseSpeed) * 20));
  const birdDone = arrive[2] + C.birdSwoops * T.birdSwoop + 1;
  const dollLast = arrive[3] + 1 + C.dollDrift + C.dollPulses[C.dollPulses.length - 1] + 10;
  const stagDone = arrive[1] + C.stagBounds * T.stagLeap + 2;
  const horseDone = arrive[0] + horseRun + 2;
  const tRoll = Math.max(birdDone, dollLast, stagDone, horseDone) + 4;
  const tEnd = tRoll + (n - 1) * C.unrollStep + T.roadAnim + 8;

  // ------------------------------------------------------------------ the road unrolls, the Sleeping Moon rises
  const segs: Actor[] = [];
  const lights = blocksFor(scene);
  sound(dim, "dn_parade_open", start, 1.2);
  for (let i = 0; i < n; i++) {
    const { p, d } = road((i + 0.5) * spacing);
    // gate of banners, moon-arches to pass under, cloud terraces with tiny planets, a moon-arch exit
    const kind = i === 0 ? 2 : i === n - 1 ? 1 : i % 4 === 2 ? 1 : i % 4 === 0 ? (i % 8 === 0 ? 2 : 3) : 0;
    scene.at(2 + i * C.unrollStep, () => {
      const a = scene.spawn("dn_parade_road", p, { yaw: yawOf(d), kind, size: spacing / ROAD_MODEL_LEN, state: ROAD.unroll });
      setTilt(a, pitch(d));
      segs[i] = a;
      particle(dim, "dn_parade_confetti", up(p, 1.2));
      if (i % C.lightEvery === 1) lights.place(up(p, 1.5), LIGHT);
      scene.after(T.roadAnim, () => a.state(ROAD.hold));
    });
  }
  let apexI = 0;
  for (let i = 0; i <= N; i++) if (P[i].y > P[apexI].y) apexI = i;
  const moonAt = add(up(P[apexI], C.moonAbove), mul(side, -1.5));
  let moon: Actor | undefined;
  scene.at(4, () => {
    moon = scene.spawn("dn_parade_moon", moonAt, { yaw: yawOf(sub(base, moonAt)), state: MOON.rise });
    sound(dim, "dn_parade_moon", moonAt, 1.0);
    burst(dim, "dn_parade_trail", moonAt, 3, 8);
  });
  scene.at(4 + T.moonRise, () => moon?.state(MOON.sleep));
  scene.at(8, () => sound(dim, "dn_parade_theme", P[apexI], 1.1));
  scene.every(10, () => particle(dim, "dn_parade_note", up(moonAt, -3)), 30, tRoll);

  // ------------------------------------------------------------------ hit tracking: crescent marks and the stacking bonus
  const hits = new Map<string, { e: Entity; by: Set<Who>; mark?: Actor; full: boolean }>();
  function strike(e: Entity, who: Who, amount: number): void {
    if (!isAlive(e)) return;
    let h = hits.get(e.id);
    if (!h) { h = { e, by: new Set(), full: false }; hits.set(e.id, h); }
    const first = !h.by.has(who);
    const others = h.by.size - (first ? 0 : 1);
    const bonus = C.stackBonus * others * (first ? 1 : C.repeatBonusShare);
    if (!damage(e, amount + bonus, caster)) return;
    h.by.add(who);
    const at = e.location;
    particle(dim, "dn_parade_crescent", up(at, 1.2));
    particle(dim, "dn_parade_groundmoon", up(groundBelow(dim, at), 0.12));
    particle(dim, "dn_parade_shard", up(at, 1.0));
    sound(dim, "dn_parade_hit", at, 0.9, 0.9 + 0.12 * h.by.size);
    if (!first || !isAlive(e)) return;
    const count = h.by.size;
    if (!h.mark || !h.mark.valid) {
      const mk = scene.spawn("dn_parade_mark", up(at, C.markHeight), { state: MARK.appear, skin: count - 1 });
      h.mark = mk;
      scene.follow(mk, e, C.markHeight);
      scene.after(T.markAppear, () => mk.state(MARK.hold));
    } else {
      const mk = h.mark;
      mk.skin(count - 1).state(MARK.flare);
      scene.after(T.markFlare, () => mk.state(MARK.hold));
    }
    if (count === ORDER.length && !h.full) {
      h.full = true;   // full moon: all four creatures struck this enemy
      const hh = h;
      scene.after(4, () => {
        if (!isAlive(hh.e)) return;
        const c = hh.e.location;
        sound(dim, "dn_parade_fullmoon", c, 1.3);
        particle(dim, "fx_flash", up(c, 1.5));
        particle(dim, "dn_parade_pulse", up(groundBelow(dim, c), 0.2));
        ring(dim, "dn_parade_crescent", up(c, 1.5), 1.5, 6);
        damage(hh.e, C.fullMoonBonus, caster);
        for (const o of hostiles(dim, c, C.fullMoonRadius, caster)) if (o.id !== hh.e.id) damage(o, C.fullMoonBonus * 0.5, caster);
      });
    }
  }

  // ------------------------------------------------------------------ the procession along the road
  function parade(who: Who, idx: number, lift: (e: number) => number, sway: number, tiltShare: number, onArrive: (a: Actor) => void): void {
    const t0 = C.spawnAt[idx];
    let a: Actor | undefined;
    scene.at(t0, () => {
      const { p, d } = road(0);
      a = scene.spawn(ACTOR[who], up(p, lift(0)), { yaw: yawOf(d), state: 1 });
      sound(dim, "dn_parade_arrive", p, 0.9, 0.85 + idx * 0.12);
      sound(dim, `dn_parade_voice_${who}`, p, 1.0);   // each creature adds its own voice to the parade motif
      burst(dim, "dn_parade_confetti", up(p, 1.5), 1.2, 3);
    });
    scene.at(t0 + C.gateHold, () => a?.state(2));
    scene.span(t0 + C.gateHold, arrive[idx], (_p, e) => {
      if (!a) return;
      const { p, d } = road((e / travel) * L);
      const off = mul(side, sway * Math.sin(e * 0.15 + idx));
      a.move(add(up(p, lift(e)), off), yawOf(d));
      setTilt(a, pitch(d) * tiltShare);
      if (e % 12 === idx * 3) particle(dim, "dn_parade_note", up(p, 2.8));
    });
    scene.at(arrive[idx], () => {
      if (a && a.valid) { setTilt(a, 0); onArrive(a); }
    });
  }
  parade("horse", 0, () => 0, 0, 0.85, horseCharge);
  parade("stag", 1, () => 0, 0, 0.85, stagBounds);
  parade("bird", 2, (e) => 2.0 + 0.4 * Math.sin(e * 0.2), 0.8, 0.5, birdSwoops);
  parade("doll", 3, (e) => 1.0 + 0.3 * Math.sin(e * 0.13), 0.5, 0, dollDance);

  // ------------------------------------------------------------------ 1. porcelain horse: a straight gallop line through the enemies
  function horseCharge(h: Actor): void {
    const from = h.loc;
    const foes = hostiles(dim, center, C.radius, caster);
    let dir = fwd;
    let best = -1;
    for (const f of foes) {   // the line that tramples the most enemies
      const d = norm(flat(sub(f.location, from)));
      const tip = add(from, mul(d, C.horseLength));
      const cnt = foes.filter((o) => distToSegment({ ...o.location, y: from.y }, from, { ...tip, y: from.y }) < C.horseHitRadius + 0.6).length;
      if (cnt > best) { best = cnt; dir = d; }
    }
    const t0 = scene.tick;
    const yaw = yawOf(dir);
    h.state(HORSE.charge).face(yaw);
    sound(dim, "dn_parade_charge", from, 1.2);
    for (let k = 1; k <= 6; k++) {   // the lane is telegraphed with moons on the ground
      particle(dim, "dn_parade_lane", up(groundBelow(dim, up(add(from, mul(dir, (k * C.horseLength) / 6)), 2)), 0.15));
    }
    const hit = new Set<string>();
    scene.span(t0 + 1, t0 + 1 + horseRun, (p, e) => {
      const xz = add(from, mul(dir, C.horseLength * p));
      const g = groundBelow(dim, { x: xz.x, y: from.y + 1, z: xz.z });
      const pos = { x: xz.x, y: from.y + (g.y - from.y) * Math.min(1, p * 4), z: xz.z };
      h.move(pos, yaw);
      if (e % 3 === 0) particle(dim, "dn_parade_trail", up(pos, 1.6));
      for (const f of hostiles(dim, up(pos, 0.8), C.horseHitRadius + 1.2, caster)) {
        if (hit.has(f.id) || distXZ(f.location, pos) > C.horseHitRadius) continue;
        hit.add(f.id);
        strike(f, "horse", C.horseDamage);
        shove(f, add(dir, mul(norm(flat(sub(f.location, pos))), 0.6)), C.horseKnockback, C.horseLift);
      }
    });
    scene.at(t0 + horseRun + 2, () => {
      h.state(HORSE.depart);
      sound(dim, "dn_parade_depart", h.loc, 0.9, 1.1);
      burst(dim, "dn_parade_shard", up(h.loc, 2), 1, 4);
    });
    scene.at(t0 + horseRun + 2 + T.horseDepart, () => scene.despawn(h));
  }

  // ------------------------------------------------------------------ 2. mist-glass stag: three telegraphed bounding impacts
  function stagBounds(st: Actor): void {
    const t0 = scene.tick;
    const struck = new Set<string>();
    for (let k = 0; k < C.stagBounds; k++) {
      const tk = t0 + k * T.stagLeap;
      scene.at(tk, () => {
        if (!st.valid) return;
        const from = st.loc;
        const all = hostiles(dim, center, C.radius, caster);
        const fresh = all.filter((e) => !struck.has(e.id));
        const pool = fresh.length ? fresh : all;
        pool.sort((a, b) => distXZ(a.location, from) - distXZ(b.location, from));
        const target: Entity | undefined = pool[0];
        let land = target
          ? groundBelow(dim, target.location)
          : groundBelow(dim, up(add(add(from, mul(fwd, C.stagIdleStride)), mul(side, (k % 2 ? -1 : 1) * 2)), 3));
        const warn = scene.spawn("telegraph", land, { kind: 1, size: C.stagRadius, state: 1 });
        st.state(k % 2 ? STAG.leapB : STAG.leapA).face(yawOf(sub(land, from)));
        scene.every(1, () => {   // the landing mark follows its enemy until the stag leaves the ground
          if (target && isAlive(target)) { land = groundBelow(dim, target.location); warn.move(land); }
        }, tk + 1, tk + T.stagLaunch);
        let a0 = from;
        let hop = C.stagHop;
        scene.at(tk + T.stagLaunch, () => {
          a0 = st.loc;
          hop = C.stagHop + C.stagHopPerBlock * distXZ(a0, land);
          sound(dim, "dn_parade_step", a0, 0.8, 1.1);
        });
        scene.span(tk + T.stagLaunch, tk + T.stagLand + 1, (p, e) => {
          const q = lerp(a0, land, p);
          st.move(up(q, hop * 4 * p * (1 - p)), yawOf(flat(sub(land, a0))));
          if (e % 3 === 1) particle(dim, "dn_parade_mistpuff", up(q, hop * 4 * p * (1 - p) + 1.5));
        });
        scene.at(tk + T.stagLand, () => {
          particle(dim, "dn_parade_groundmoon", up(land, 0.15));
          particle(dim, "dn_parade_mistpuff", up(land, 0.3));
          burst(dim, "dn_parade_shard", up(land, 0.8), 1, 3);
          sound(dim, "dn_parade_land", land, 1.1);
          for (const e of hostiles(dim, land, C.stagRadius, caster)) {
            struck.add(e.id);
            strike(e, "stag", C.stagDamage);
            knockback(e, land, 0.5, 0.35);
          }
          warn.state(3);
          scene.after(8, () => scene.despawn(warn));
        });
      });
    }
    const tDep = t0 + C.stagBounds * T.stagLeap + 2;
    scene.at(tDep, () => {
      st.state(STAG.depart);
      sound(dim, "dn_parade_depart", st.loc, 0.9, 0.95);
      burst(dim, "dn_parade_mistpuff", up(st.loc, 2), 1.2, 4);
    });
    scene.at(tDep + T.stagDepart, () => scene.despawn(st));
  }

  // ------------------------------------------------------------------ 3. curtain-winged bird: swooping arcs through several enemies
  function birdSwoops(b: Actor): void {
    const t0 = scene.tick;
    const everHit = new Set<string>();
    for (let k = 0; k < C.birdSwoops; k++) {
      const tk = t0 + k * T.birdSwoop;
      scene.at(tk, () => {
        if (!b.valid) return;
        const p0 = b.loc;
        const foes = hostiles(dim, center, C.radius, caster);
        foes.sort((x, y) => (everHit.has(x.id) ? 1 : 0) - (everHit.has(y.id) ? 1 : 0) || distXZ(x.location, p0) - distXZ(y.location, p0));
        let la: Vector3;
        let lb: Vector3;
        if (foes.length) {
          la = groundBelow(dim, foes[0].location);
          const second = foes.slice(1).find((e) => distXZ(e.location, foes[0].location) <= C.birdPairRange);
          lb = second ? groundBelow(dim, second.location) : groundBelow(dim, up(add(la, mul(norm(flat(sub(la, p0))), 4)), 2));
        } else {   // no enemies: three graceful passes across the field
          la = groundBelow(dim, up(add(center, mul(side, (k - 1) * 3.5)), 3));
          lb = groundBelow(dim, up(add(la, mul(fwd, 4)), 3));
        }
        la = up(la, C.birdSkim);
        lb = up(lb, C.birdSkim);
        const away = distXZ(la, lb) > 0.5 ? norm(flat(sub(lb, la))) : fwd;
        const path = [p0, la, lb, up(add(lb, mul(away, 6)), C.birdAir)];
        b.state(k % 2 ? BIRD.swoopB : BIRD.swoopA);
        sound(dim, "dn_parade_swoop", p0, 1.0);
        const hit = new Set<string>();
        let prev = p0;
        scene.span(tk + 1, tk + T.birdSwoop + 1, (p, e) => {
          const pos = spline(path, p);
          const d = sub(pos, prev);
          prev = pos;
          b.move(pos, yawOf(d.x * d.x + d.z * d.z > 1e-6 ? d : away));
          setTilt(b, pitch(d) * 0.6);
          if (e % 4 === 0) particle(dim, "dn_parade_trail", pos);
          if (e < T.birdLowFrom - 2 || e > T.birdLowTo + 2) return;
          for (const f of hostiles(dim, pos, C.birdHitRadius + 2, caster)) {
            if (hit.has(f.id) || dist(up(f.location, 0.9), pos) > C.birdHitRadius + 0.6) continue;
            hit.add(f.id);
            everHit.add(f.id);
            strike(f, "bird", C.birdDamage);
            shove(f, d, 0.5, 0.3);
          }
        });
      });
    }
    const tDep = t0 + C.birdSwoops * T.birdSwoop + 1;
    scene.at(tDep, () => {
      b.state(BIRD.depart);
      setTilt(b, 0);
      sound(dim, "dn_parade_depart", b.loc, 0.9, 1.25);
    });
    scene.at(tDep + T.birdDepart, () => scene.despawn(b));
  }

  // ------------------------------------------------------------------ 4. star doll: hesitant drift, then a syncopated starburst
  function dollDance(dl: Actor): void {
    const t0 = scene.tick;
    const from = dl.loc;
    const foes = hostiles(dim, center, C.radius, caster, 6);
    let spot = center;
    if (foes.length) {
      let sx = 0;
      let sz = 0;
      for (const f of foes) { sx += f.location.x; sz += f.location.z; }
      spot = groundBelow(dim, { x: sx / foes.length, y: center.y + 3, z: sz / foes.length });
    }
    const hover = up(spot, C.dollHover);
    const warn = scene.spawn("telegraph", spot, { kind: 1, size: C.dollRadius, state: 4 });
    scene.span(t0 + 1, t0 + 1 + C.dollDrift, (p) => {   // stop-go drift in four hesitant steps
      const k = Math.min(3, Math.floor(p * 4));
      const q = Math.min(1, (k + smooth(Math.min(1, (p * 4 - k) * 1.6))) / 4);
      dl.move(lerp(from, hover, q));
    });
    const tp = t0 + 1 + C.dollDrift;
    scene.at(tp, () => warn.state(2));
    const pitches = [1, 1.12, 0.89, 1, 1.26];
    C.dollPulses.forEach((off, k) => {
      scene.at(tp + off, () => {
        dl.state(k % 2 ? DOLL.pulseB : DOLL.pulseA);
        sound(dim, "dn_parade_pulse", hover, 1.0, pitches[k % pitches.length]);
      });
      scene.at(tp + off + T.dollPulsePeak, () => {
        particle(dim, "dn_parade_pulse", up(spot, 0.2));
        ring(dim, "dn_parade_glint", up(spot, 0.8), C.dollRadius * 0.8, 6, k * 30);
        for (const e of hostiles(dim, spot, C.dollRadius, caster)) {
          strike(e, "doll", C.dollDamage);
          effect(e, "slowness", C.dollSlowTicks, C.dollSlowAmp);
        }
      });
    });
    const last = tp + C.dollPulses[C.dollPulses.length - 1] + 10;
    scene.at(last, () => {
      warn.state(3);
      dl.state(DOLL.depart);
      sound(dim, "dn_parade_depart", hover, 0.9, 1.4);
      burst(dim, "dn_parade_trail", hover, 1.2, 6);
    });
    scene.at(last + 8, () => scene.despawn(warn));
    scene.at(last + T.dollDepart, () => scene.despawn(dl));
  }

  // ------------------------------------------------------------------ the parade ends: marks fade, the road rolls itself up, the moon sets
  scene.at(tRoll, () => {
    sound(dim, "dn_parade_rollup", P[apexI], 1.1);
    for (const h of hits.values()) {
      const mk = h.mark;
      if (mk && mk.valid) { mk.state(MARK.vanish); scene.after(T.markVanish, () => scene.despawn(mk)); }
    }
    moon?.state(MOON.set);
    scene.after(T.moonSet, () => { if (moon) scene.despawn(moon); });
  });
  for (let i = 0; i < n; i++) {
    const t = tRoll + (n - 1 - i) * C.unrollStep;   // from the far end back toward the caster
    scene.at(t, () => {
      const a = segs[i];
      if (!a) return;
      a.state(ROAD.rollup);
      particle(dim, "dn_parade_confetti", up(a.loc, 1));
      scene.after(T.roadAnim, () => scene.despawn(a));
    });
  }
  scene.endAt(tEnd);
});
