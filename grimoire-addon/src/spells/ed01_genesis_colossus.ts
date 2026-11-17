import { Entity, Vector3 } from "@minecraft/server";
import { ED01 as C } from "../config/ed01";
import { defineSpell } from "../core/registry";
import { damage, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { blocksFor } from "../lib/tempblocks";
import { V3, add, clamp, dist, distToSegment, distXZ, fromYaw, mul, norm, polar, right, sub, up, yawOf } from "../lib/vec";

// ---- mirror of tools/assets/ed_nature.py (keep in sync) -------------------------------------
/** Nature Dragon animation states (ed_nature.STATE_IDS). */
const N = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10, depart: 11 };
const ACTOR = "dragon_nature";
const SCALE = 2.0;
/** Blocks per second the `move` loop is authored for, and its cycle in ticks. */
const WALK_SPEED = 1.5;
const WALK_CYCLE = 64;
/** Footfalls inside one walk cycle: tick, and the striking foot's offset (right, forward) in blocks. */
const STEPS: { t: number; x: number; z: number }[] = [
  { t: 0, x: -3, z: -1.9 }, { t: 16, x: -3, z: 5.5 }, { t: 32, x: 3, z: -1.9 }, { t: 48, x: 3, z: 5.5 }];
const ARRIVE_LAND = 50;   // ticks into `arrive` when the forefeet land
const ATTACK_A_HIT = 44;  // ticks into `attack_a` when the forelimb slam lands
const DEPART_PETRIFY = 14;
const DEPART_LEN = 56;
/** Right forefoot at the slam, relative to the dragon (right, forward) in blocks. */
const SLAM_OFS = { x: 3, z: 4.5 };
const SKIN = { normal: 0, bloom: 1, stone: 2 };
const STRATA = { hidden: 0, rise: 1, hold: 2, part: 3, erupt: 4, crumble: 5 };
const PILLAR = { hidden: 0, rise: 1, hold: 2, erupt: 3, crumble: 4 };
const PILLAR_IMPACT = 12;
const ROOT = { hidden: 0, grow: 1, hold: 2, erupt: 3, wither: 4 };
const ROOT_LEN = 6;       // blocks at size 1
const ROOT_BIND = 21;     // ticks into `grow` when the claw cage closes
// ----------------------------------------------------------------------------------------------

// Timeline (ticks)
const T_ARRIVE = 8;
const T_WALK = 72;
const T_POWER = T_WALK + WALK_CYCLE;     // 136
const T_ROOTS = T_POWER + 10;
const T_PILLARS = T_POWER + 28;
const T_ATTACK = T_POWER + 48;           // 184
const T_HIT = T_ATTACK + ATTACK_A_HIT;   // 228
const T_DEPART = T_HIT + 22;             // 250
const T_END = T_DEPART + DEPART_LEN + 4;

/** Point at (right, forward) blocks from `p` for a creature facing `yaw`. */
function local(p: V3, yaw: number, x: number, z: number): V3 {
  const f = fromYaw(yaw);
  return add(add(p, mul(f, z)), mul(right(f), x));
}

/**
 * ED01 - Genesis Colossus: The Walking Continent.
 * Stage I: strata heave out of the ground, the titanosaur rises neck-first and walks a short arc;
 * every footfall is a geological shockwave.  Stage II: it lifts its head, its back bursts into a
 * forest, roots snake from its footprints to bind enemies and root-bound pillars rise around them.
 * Stage III: it rears, slams a forelimb on the telegraphed spot and every root, pillar and stratum
 * erupts toward the centre.  Then it turns to stone and sinks back into the earth.
 */
export default defineSpell("ed01", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.focusSnap);
  const fwd = aim.forward;
  const fe = norm(add(mul(right(fwd), C.walkAcross), mul(fwd, C.walkAway)));
  const yawEnd = yawOf(fe);
  const yawStart = yawEnd + C.walkTurnDeg;
  const slamAt = { ...center };
  const pEnd = up(local(center, yawEnd, -SLAM_OFS.x, -SLAM_OFS.z), 0);
  pEnd.y = center.y;

  // walk path, integrated backward from the end so the slam lands on the focus
  const step = WALK_SPEED / 20;
  const path: V3[] = new Array(WALK_CYCLE + 1);
  const yaws: number[] = new Array(WALK_CYCLE + 1);
  path[WALK_CYCLE] = pEnd;
  yaws[WALK_CYCLE] = yawEnd;
  for (let i = WALK_CYCLE; i > 0; i--) {
    const h = yawStart + (yawEnd - yawStart) * ((i - 0.5) / WALK_CYCLE);
    path[i - 1] = sub(path[i], mul(fromYaw(h), step));
    yaws[i - 1] = yawStart + (yawEnd - yawStart) * ((i - 1) / WALK_CYCLE);
  }
  const pStart = path[0];
  const tb = blocksFor(scene);
  const footprints: V3[] = [];

  // ================= Stage I: Awakening of the Living Earth
  const sigil = scene.spawn("telegraph", up(pStart, 0.05), { kind: 2, size: 9, state: 1 });
  scene.at(20, () => sigil.state(2));
  scene.at(T_ARRIVE + 52, () => sigil.state(3));
  scene.at(T_ARRIVE + 60, () => scene.despawn(sigil));
  sound(dim, "ed_nature_rumble", pStart, 1.6);
  const strataSpots: [number, number, number][] = [[0, 9, 1.8], [5, 3, 1.6], [-5, 3, 1.6], [5.5, -6, 1.5], [-5.5, -6, 1.5]];
  const strata: { a: Actor; at: V3; size: number }[] = [];
  strataSpots.forEach(([x, z, size], k) => {
    scene.at(k * 3, () => {
      const at = groundBelow(dim, up(local(pStart, yawStart, x, z), 3));
      const a = scene.spawn("ed_nature_strata", at, { yaw: yawOf(sub(at, pStart)) + k * 37, size, state: STRATA.rise });
      strata.push({ a, at, size });
      burst(dim, "ed_nature_dust", up(at, 1), 2.5, 3);
      particle(dim, "ed_nature_rise", at);
      if (k % 2 === 0) sound(dim, "ed_nature_strata", at, 1.2, 0.9 + k * 0.05);
    });
  });
  scene.at(18, () => strata.forEach((s) => s.a.state(STRATA.hold)));

  let dragon: Actor | undefined;
  scene.at(T_ARRIVE, () => {
    dragon = scene.spawn(ACTOR, pStart, { yaw: yawStart, state: N.arrive, skin: SKIN.normal });
    ring(dim, "ed_nature_rock", up(pStart, 0.5), 4, 6);
  });
  // the strata slide apart as the neck breaks through
  scene.at(T_ARRIVE + 20, () => {
    strata.forEach((s) => s.a.state(STRATA.part));
    sound(dim, "ed_nature_strata", pStart, 1.4, 0.8);
  });
  scene.every(6, () => burst(dim, "ed_nature_dust", up(pStart, 1.5), 5, 3), T_ARRIVE, T_ARRIVE + ARRIVE_LAND);
  scene.at(T_ARRIVE + ARRIVE_LAND, () => {
    for (const x of [-3, 3]) {
      const at = groundBelow(dim, up(local(pStart, yawStart, x, 5.5), 3));
      quake(at, 1.7);
      footprints.push(at);
    }
    for (const e of hostiles(dim, local(pStart, yawStart, 0, 5), C.landRadius, caster)) {
      damage(e, C.landDamage, caster);
      knockback(e, pStart, C.stepKnockH * 1.5, C.stepKnockV);
    }
  });

  // slow, heavy walk along the arc; every footfall is a shockwave
  scene.at(T_WALK, () => dragon?.state(N.move));
  scene.every(1, (e) => { dragon?.move(path[Math.min(e, WALK_CYCLE)], yaws[Math.min(e, WALK_CYCLE)]); }, T_WALK, T_POWER + 1);
  for (const s of STEPS) {
    scene.at(T_WALK + s.t, () => {
      const at = groundBelow(dim, up(local(path[s.t], yaws[s.t], s.x, s.z), 3));
      footprints.push(at);
      quake(at, C.stepQuakeSize);
      for (const e of hostiles(dim, at, C.stepRadius, caster)) {
        damage(e, C.stepDamage, caster);
        knockback(e, at, C.stepKnockH, C.stepKnockV);
      }
    });
  }

  function quake(at: V3, size: number): void {
    const q = scene.spawn("ed_nature_quake", up(at, 0.02), { size, state: 1, yaw: (scene.tick * 47) % 360 });
    scene.after(27, () => scene.despawn(q));
    particle(dim, "ed_nature_shock", up(at, 0.15));
    particle(dim, "ed_nature_dust", up(at, 0.4));
    particle(dim, "ed_nature_rock", up(at, 0.3));
    sound(dim, "ed_nature_quake", at, 1.0);
  }

  // ================= Stage II: The Forest Upon Its Back
  const back = up(pEnd, 11);
  scene.at(T_POWER, () => {
    dragon?.state(N.power);
    sound(dim, "ed_nature_grow", back, 1.4);
  });
  scene.at(T_POWER + 20, () => dragon?.skin(SKIN.bloom));
  scene.every(6, (e) => {
    burst(dim, e % 12 === 0 ? "ed_nature_leaf" : "ed_nature_petal", back, 4, 2);
    particle(dim, "ed_nature_pollen", up(back, 2));
  }, T_POWER + 12, T_ATTACK);

  type Bind = { e?: Entity; a: Actor; tip: V3; release?: () => void };
  const binds: Bind[] = [];
  scene.at(T_ROOTS, () => {
    const from = footprints.length ? footprints : [pEnd];
    const nearestPrint = (p: V3) => from.reduce((b, f) => (distXZ(f, p) < distXZ(b, p) ? f : b), from[0]);
    const found = hostiles(dim, center, C.rootRadius, caster, C.maxRoots);
    const goals: { e?: Entity; at: V3 }[] = found.length
      ? found.map((e) => ({ e, at: { ...e.location } }))
      : Array.from({ length: C.idleRoots }, (_, k) => ({ at: polar(center, 3, k * (360 / C.idleRoots) + 20) }));
    goals.forEach((g, k) => {
      scene.after(k * 3, () => {
        const target = g.e && isAlive(g.e) ? { ...g.e.location } : g.at;
        const fp = nearestPrint(target);
        const d = Math.max(0.5, distXZ(fp, target));
        const size = clamp(d / ROOT_LEN, C.rootMinSize, C.rootMaxSize);
        const yaw = yawOf(sub(target, fp));
        const tip = groundBelow(dim, up(add(fp, mul(fromYaw(yaw), ROOT_LEN * size)), 2));
        const a = scene.spawn("ed_nature_root", up(fp, 0.05), { yaw, size, state: ROOT.grow });
        const b: Bind = { e: g.e, a, tip };
        binds.push(b);
        sound(dim, "ed_nature_root", fp, 1.0);
        line(dim, "ed_nature_dust", fp, tip, 3);
        scene.after(ROOT_BIND - 3, () => {
          particle(dim, "ed_nature_spore", up(tip, 1));
          sound(dim, "ed_nature_bind", tip, 1.0);
          if (b.e && isAlive(b.e)) {
            b.release = restrain(scene, b.e, T_HIT - scene.tick + 4, { x: tip.x, y: Math.max(tip.y, b.e.location.y - 0.5), z: tip.z });
          }
        });
        scene.after(26, () => a.state(ROOT.hold));
      });
    });
  });

  type Ring = { c: V3; r: number; pillars: { a: Actor; at: V3; cells: V3[] }[] };
  const rings: Ring[] = [];
  scene.at(T_PILLARS, () => {
    const pool = hostiles(dim, center, C.rootRadius + 2, caster);
    const groups: Entity[][] = [];
    const used = new Set<string>();
    for (const e of pool) {
      if (used.has(e.id) || groups.length >= C.maxRings) continue;
      const g = pool.filter((o) => !used.has(o.id) && dist(o.location, e.location) <= C.groupRadius);
      g.forEach((o) => used.add(o.id));
      groups.push(g);
    }
    const specs = groups.length
      ? groups.map((g) => {
        const c = mul(g.reduce((s, e) => add(s, e.location), { x: 0, y: 0, z: 0 }), 1 / g.length);
        const spread = Math.max(...g.map((e) => distXZ(e.location, c)));
        return { c: groundBelow(dim, up(c, 2)), r: clamp(spread + 2.5, C.ringMin, C.ringMax) };
      })
      : [{ c: center, r: C.ringMin }];
    specs.forEach((sp, gi) => {
      const rg: Ring = { c: sp.c, r: sp.r, pillars: [] };
      rings.push(rg);
      // the first pillar stands on the path of the roots (toward the nearest footprint)
      const fp = footprints.length ? footprints.reduce((b, f) => (distXZ(f, sp.c) < distXZ(b, sp.c) ? f : b)) : pEnd;
      const a0 = (Math.atan2(fp.z - sp.c.z, fp.x - sp.c.x) * 180) / Math.PI;
      for (let k = 0; k < C.pillarsPerRing; k++) {
        scene.after(gi * 4 + k * 3, () => {
          const ang = a0 + (360 * k) / C.pillarsPerRing;
          const at = groundBelow(dim, up(polar(sp.c, sp.r, ang), 3));
          const yaw = yawOf(sub(sp.c, at));
          const a = scene.spawn("ed_nature_pillar", at, { yaw, size: C.pillarSize, state: PILLAR.rise });
          const tan = right(sub(sp.c, at));
          const cells = [at, add(at, tan), sub(at, tan)];
          rg.pillars.push({ a, at, cells });
          particle(dim, "ed_nature_rise", at);
          particle(dim, "ed_nature_dust", up(at, 0.5));
          particle(dim, "ed_nature_rock", up(at, 1));
          sound(dim, "ed_nature_pillar", at, 1.0, 0.92 + k * 0.04);
          scene.after(8, () => cells.forEach((c) => tb.column(c.x, c.y, c.z, C.pillarBarrierHeight)));
          scene.after(16, () => a.state(PILLAR.hold));
          // enemies caught where a pillar rises are thrown inward
          for (const e of hostiles(dim, at, 1.6, caster)) shove(e, sub(sp.c, at), 0.8, 0.4);
        });
      }
    });
  });

  // ================= Stage III: Continental Descent
  let warn: Actor | undefined;
  scene.at(T_ATTACK, () => {
    dragon?.state(N.attack_a);
    warn = scene.spawn("telegraph", up(slamAt, 0.05), { kind: 2, size: C.slamRadius, state: 4 });
    sound(dim, "ed_nature_rumble", slamAt, 1.2, 1.15);
  });
  scene.every(8, () => ring(dim, "ed_nature_mote", up(slamAt, 0.3), C.slamRadius * 0.7, 5, scene.tick * 7), T_ATTACK, T_HIT);

  scene.at(T_HIT, () => {
    warn?.state(3);
    const w = warn;
    scene.after(8, () => { if (w) scene.despawn(w); });
    const qa = scene.spawn("ed_nature_quake", up(slamAt, 0.03), { size: 3.4, state: 1 });
    scene.after(27, () => scene.despawn(qa));
    sound(dim, "ed_nature_slam", slamAt, 2.0);
    particle(dim, "ed_nature_shock_big", up(slamAt, 0.2));
    particle(dim, "fx_flash", up(slamAt, 1));
    burst(dim, "ed_nature_dust", up(slamAt, 1), 4, 6);
    ring(dim, "ed_nature_rock", up(slamAt, 0.5), 3, 6);
    for (const e of hostiles(dim, slamAt, C.slamRadius, caster)) {
      damage(e, C.slamDamage, caster);
      knockback(e, slamAt, C.slamKnockH, C.slamKnockV);
    }
  });

  // strata thrust up again
  scene.at(T_HIT + 2, () => {
    for (const s of strata) {
      s.a.state(STRATA.erupt);
      particle(dim, "ed_nature_rise", s.at);
      particle(dim, "ed_nature_rock", up(s.at, 1));
      for (const e of hostiles(dim, s.at, C.strataRadius * (s.size / 1.6), caster)) {
        damage(e, C.strataDamage, caster);
        knockback(e, s.at, 1.0, 0.7);
      }
    }
    sound(dim, "ed_nature_erupt", pStart, 1.4, 0.8);
  });
  scene.at(T_HIT + 20, () => strata.forEach((s) => s.a.state(STRATA.crumble)));
  scene.at(T_HIT + 44, () => { strata.forEach((s) => scene.despawn(s.a)); });

  // roots tear out of the ground, in order of distance from the slam
  scene.at(T_HIT + 1, () => {
    for (const b of binds) {
      const delay = 3 + Math.min(14, Math.round(dist(b.tip, slamAt) * 0.6));
      scene.after(delay, () => {
        b.release?.();
        b.a.state(ROOT.erupt);
        particle(dim, "ed_nature_splinter", up(b.tip, 1));
        particle(dim, "ed_nature_spore", up(b.tip, 1.2));
        sound(dim, "ed_nature_erupt", b.tip, 1.0, 1.1);
        for (const e of hostiles(dim, b.tip, C.rootEruptRadius, caster)) {
          damage(e, C.rootDamage, caster);
          knockback(e, b.tip, 0.3, C.rootKnockV);
        }
        scene.after(17, () => scene.despawn(b.a));
      });
    }
  });

  // the pillars topple toward their ring centre, then the ring converges
  scene.at(T_HIT + 6, () => {
    rings.forEach((rg, gi) => {
      const crushed = new Set<string>();
      rg.pillars.forEach((p, k) => {
        scene.after(gi * 2 + k * 2, () => {
          p.cells.forEach((c) => tb.removeColumn(c.x, c.y, c.z, C.pillarBarrierHeight));
          p.a.state(PILLAR.erupt);
          sound(dim, "ed_nature_topple", p.at, 1.0, 0.95 + k * 0.03);
          scene.after(PILLAR_IMPACT, () => {
            line(dim, "ed_nature_dust", p.at, rg.c, 3);
            particle(dim, "ed_nature_rock", up(rg.c, 0.6));
            for (const e of hostiles(dim, rg.c, rg.r + 1.5, caster)) {
              if (crushed.has(e.id) || distToSegment(e.location, p.at, rg.c) > C.pillarWidth) continue;
              crushed.add(e.id);
              damage(e, C.pillarDamage, caster);
            }
          });
          scene.after(23, () => scene.despawn(p.a));
        });
      });
      scene.after(gi * 2 + rg.pillars.length * 2 + PILLAR_IMPACT + 2, () => {
        particle(dim, "ed_nature_shock_big", up(rg.c, 0.2));
        burst(dim, "ed_nature_spore", up(rg.c, 1), 2, 4);
        burst(dim, "ed_nature_leaf", up(rg.c, 1.5), 2.5, 3);
        sound(dim, "ed_nature_erupt", rg.c, 1.6, 0.75);
        for (const e of hostiles(dim, rg.c, rg.r + 1, caster)) {
          damage(e, C.convergeDamage, caster);
          knockback(e, rg.c, C.convergeKnockH, C.convergeKnockV);
        }
      });
    });
  });

  // ================= Dissolution: stone, soil, silence
  scene.at(T_DEPART, () => dragon?.state(N.depart));
  scene.at(T_DEPART + DEPART_PETRIFY, () => {
    dragon?.skin(SKIN.stone);
    burst(dim, "ed_nature_dust", back, 5, 4);
  });
  scene.every(8, () => {
    ring(dim, "ed_nature_dust", up(pEnd, 0.4), 6, 5, scene.tick * 11);
    particle(dim, "ed_nature_rock", up(pEnd, 2));
  }, T_DEPART + 20, T_DEPART + DEPART_LEN);
  scene.at(T_DEPART + 22, () => sound(dim, "ed_nature_rumble", pEnd, 1.4, 0.85));
  scene.at(T_DEPART + DEPART_LEN, () => {
    burst(dim, "ed_nature_leaf", up(pEnd, 1), 6, 4);
    if (dragon) scene.despawn(dragon);
  });
  scene.endAt(T_END);
  void SCALE;
});
