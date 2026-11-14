import { Entity } from "@minecraft/server";
import { ED06 as C } from "../config/ed06";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { blocksFor } from "../lib/tempblocks";
import {
  V3, add, angleDelta, bezier, clamp, distToSegment, distXZ, dot, flat, fromYaw, len, lerp, mul, norm, right, smooth, sub, up,
  yawOf,
} from "../lib/vec";
import { ArcPath, Frame, Mover } from "./_ed06_motion";

// ================================================================================================
// Mirrors of the asset modules (keep in sync).
// ---- dragon_nature (tools/assets/ed_nature.py)
const NATURE = { actor: "dragon_nature", scale: 2.0 };
const N = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10, depart: 11 };
const N_WALK = 1.5;          // blocks / s of `move`
const N_CYCLE = 64;          // walk cycle (3.2 s)
const N_TURN = 20;           // deg / s of turn_l / turn_r
const N_STEPS = [{ t: 0, x: -3, z: -1.9 }, { t: 16, x: -3, z: 5.5 }, { t: 32, x: 3, z: -1.9 }, { t: 48, x: 3, z: 5.5 }];
const N_T = { arriveLand: 50, power: 52, attackA: 64, attackAHit: 44, attackB: 48, attackBHit: 27, depart: 56 };
const N_SKIN = { normal: 0, bloom: 1 };
const N_SLAM = { x: 3, z: 4.5 };
const STRATA = { rise: 1, hold: 2, part: 3, erupt: 4, crumble: 5 };
const PILLAR = { rise: 1, hold: 2, erupt: 3, crumble: 4 };
const ROOT = { grow: 1, hold: 2, erupt: 3, wither: 4 };
const ROOT_LEN = 6, ROOT_BIND = 21;
// ---- dragon_heat (tools/assets/ed_heat.py)
const HEAT = { actor: "dragon_heat", scale: 1.85 };
const H = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10,
  depart: 11, ignite: 12, charge: 13, skid: 14, pant: 15, cool: 16, roar: 17, walk: 18 };
const H_RUN = 10.02, H_WALK = 3.53, H_TURN = 225;
const H_T = { arriveWalk: 24, ignite: 32, igniteRoar: 22, skid: 14, roar: 28, cool: 24, depart: 40 };
const H_SKIN = { cool: 0, ignited: 1, whitehot: 2 };
const H_HORN = 7.9;          // horn tips ahead of the origin (blocks)
const WALL = { form: 1, part: 3, fade: 4 };
const GLASS = { appear: 1, hold: 2, fade: 3 };
const LANE = { appear: 1, armed: 2, surge: 3, fade: 4 };
// ---- dragon_tide (tools/assets/ed_tide.py)
const TIDE = { actor: "dragon_tide", scale: 2.0 };
const D = { hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9, rest: 10,
  depart: 11, swim: 12, land: 13, roar: 14, attack_c: 15 };
const D_SWIM = 14;
const D_T = { arrive: 20, land: 16, landHit: 5, sweep: 30, sweepHit: [10, 21], flare: 22, flareHit: 9, depart: 32 };
const MASS = { gather: 1, hold: 2, burst: 3, disperse: 4 };
const STREAM = { form: 1, hold: 2, fade: 3 };
const CUR = { form: 1, flow: 2, freeze: 3, spiral: 4, ice: 5, rise: 6, shatter: 7 };
const CUR_R = 4, CUR_SWEEP = 160;
// ---- dragon_air (tools/assets/ed_air.py)
const AIR = { actor: "dragon_air", scale: 1.5 };
const A = { hidden: 0, arrive: 1, idle: 2, move: 3, glide: 4, turn_l: 5, turn_r: 6, roll: 7, stoop: 8, flare: 9, land: 10,
  attack_a: 11, attack_b: 12, power: 13, react: 14, rest: 15, depart: 16, flutter: 17 };
const A_T = { arrive: 48, roll: 20, stoop: 9, land: 20, power: 18, flare: 10, depart: 32 };
const A_BANK = 1.4;          // deg / tick of yaw change that makes the raptor bank
const CLOUD = { form: 1, part: 2, fade: 3 };
// ---- ED06 constructs (tools/assets/ed6_*.py)
const CODEX = { rise: 1, hover: 2, beat: 3, absorb: 4, vanish: 5 };
const EMBLEM = { appear: 1, beat: 2, glow: 3, fade: 4 };
const SPIRIT = { form: 1, hold: 2, stream: 3 };
const FOG_CLEAR = 5;
const HORIZON = { rise: 1, hold: 2, sink: 3 };
const FLORA = { sprout: 1, sway: 2, wither: 3 };
const STONE = { rise: 1, hold: 2, sink: 3, flare: 4 };
const STONE_SKIN = { stone: 0, glass: 1, obsidian: 2 };
const BRIDGE = { form: 1, hold: 2, shatter: 3 };
const BRIDGE_LEN = 12;
const DEBRIS = { lift: 1, orbit: 2, scatter: 3 };
const RING = { rise: 1, hold: 2, quake: 3, burst: 4 };
const RING_SKIN = { frost: 1, glass: 2 };
const RING_R = 6;
const SHELL = { grow: 1, hold: 2, shatter: 3 };
const SHELL_LAYERS = [{ t: 13, r: 2.2 }, { t: 28, r: 3.6 }, { t: 44, r: 5.0 }];
const SPIRAL = { form: 1, spin: 2, burst: 3 };
const BLAST = { blast: 1, hold: 2, fade: 3 };
const LINEAGE = ["nature", "heat", "tide", "air"];

// ================================================================================================
// Timeline (ticks).  I 0-168 heartbeats, II 168-450 arrivals, III 450-740 dominion, IV 740-1070 concord, V 1070-1300.
const BEATS = [48, 80, 112, 144];
const T2 = 168, T3 = 450, T4 = 740, T5 = 1070;
const T_NATURE = T2 + 8, T_HEAT = 232, T_TIDE = 306, T_AIR = 352;

/** Point at (right, forward) blocks from p for a creature facing yaw. */
function local(p: V3, yaw: number, x: number, z: number): V3 {
  const f = fromYaw(yaw);
  return add(add(p, mul(f, z)), mul(right(f), x));
}

/**
 * ED06 - The World Before Names (Extra Ultimate).
 * I   The Four Ancient Heartbeats: the Great Codex rises above the caster, its bronze scales and spine
 *     separate and orbit; four heartbeats light four dragon emblems while a prehistoric world grows in.
 * II  The Sovereigns Awaken: the Nature titanosaur rises out of parting strata, the horned Heat Dragon
 *     charges through a wall of heat shimmer, the sail-backed Tide Dragon swims out of suspended water,
 *     the four-winged Air Dragon descends through the clouds, rolls, stoops and circles above.
 * III The Primordial Dominion: all four act at once in their own lanes - footfall quakes, roots and
 *     pillars; charges between the standing stones vitrifying them; currents and crystalline bridges;
 *     wind-lifted aerial formations and updrafts.
 * IV  The Fourfold Concord: pillars enclose the hostile zone and geological shockwaves run into it;
 *     water currents run through the ring and freeze into layered ice; a spiral of ice and wind carries
 *     everything round; the Heat Dragon's final charge detonates the formation.
 * V   The World Remembers: the dragons rest, cool, retreat to water and land, dissolve into luminous
 *     skeletons and inscriptions that stream back into the Codex; the ancient world fades.
 */
export default defineSpell("ed06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  // ------------------------------------------------------------------------------------ the domain
  let center = focus(caster, aim, C.snap).center;
  let F = flat(sub(center, caster.location));
  F = norm(len(F) < 0.5 ? aim.forward : F);
  if (distXZ(center, caster.location) < C.minDistance) {
    center = groundBelow(dim, up(add(caster.location, mul(F, C.minDistance)), 6), 24);
  }
  const fr = new Frame(center, F, right(F));
  const gy = (p: V3): number => groundBelow(dim, { x: p.x, y: Math.max(p.y, center.y) + 8, z: p.z }, 30).y;
  const ground = (p: V3): V3 => ({ x: p.x, y: gy(p), z: p.z });
  const yawDeg = (deg: number): number => yawOf(fr.dir(deg));
  const foes = (at: V3, r: number, max?: number): Entity[] => hostiles(dim, at, r, caster, max);
  const tb = blocksFor(scene);
  const burnT = (e: Entity, s: number): void => { try { e.setOnFire(s, true); } catch { /* immune / gone */ } };
  const movers: Mover[] = [];
  scene.every(1, () => { for (const m of movers) m.step(scene.tick); }, 0, T5 + 260);

  // Lanes (frame coordinates, see brief): Nature on the far outer arc, Heat between the standing stones
  // on the right, Tide in a figure-eight through suspended water on the left, Air circling high above.
  const RN = 18;                                   // nature arc radius
  const CH = fr.p(-3, 6.5);                        // heat chord centre
  const CT = fr.p(-2, -9);                         // tide figure-eight centre
  const AIR_R = 13, AIR_H = 22;                    // air circle

  // ================================================================================== Phase I
  const K = up(add(caster.location, mul(F, C.codexAhead)), C.codexHeight);
  const codex = scene.spawn("ed6_codex", K, { yaw: yawOf(F), state: CODEX.rise, skin: 0 });
  sound(dim, "ed6_codex_rise", K, 1.4);
  scene.every(5, () => particle(dim, "ed6_codex_rune", K), 0, 40);
  scene.at(38, () => codex.state(CODEX.hover));
  scene.at(24, () => {
    codex.prop("sep", 1);                        // cover scales and vertebrae separate and orbit
    sound(dim, "ed6_codex_unbind", K, 1.3);
    burst(dim, "ed6_codex_glint", K, 2.5, 5);
  });
  const codexBeat = (): void => { codex.state(CODEX.beat); scene.after(12, () => codex.state(CODEX.hover)); };

  const EM: V3[] = [ground(fr.polar(RN - 3, -22)), ground(fr.polar(9, 90, 0, CH)), ground(CT), ground(fr.polar(7, 180))];
  const emblems: Actor[] = [];
  let level = 0;                                   // atmosphere density 0..4
  let fog: Actor | undefined, horizon: Actor | undefined;
  const flora: Actor[] = [];
  const stones: { a: Actor; at: V3; hotUntil: number; gone?: boolean }[] = [];
  const GROVES: [number, number, number][] = [[145, 22, 0], [165, 21, 1], [183, 24, 2], [215, 19, 0], [245, 18, 3], [290, 22, 1],
    [230, 24, 2], [135, 24, 3]];

  function sprout(at: V3, kind: number, yaw: number): Actor {
    const a = scene.spawn("ed6_flora", at, { kind, yaw, state: FLORA.sprout });
    scene.after(40, () => a.state(FLORA.sway));
    flora.push(a);
    particle(dim, "ed6_pollen_drift", up(at, 2));
    return a;
  }
  function atmosphere(k: number): void {
    if (k === 0) {
      horizon = scene.spawn("ed6_horizon", center, { yaw: yawOf(F), state: HORIZON.rise });
      scene.after(60, () => horizon?.state(HORIZON.hold));
      fog = scene.spawn("ed6_fog", up(center, 0.05), { state: 1 });
    } else fog?.state(k + 1);
    if (k === 1) {
      [45, 135, 225, 315].forEach((a, i) => scene.after(i * 4, () => {
        const at = ground(fr.polar(4.5, a, 0, CH));
        stones.push({ a: scene.spawn("ed6_stone", at, { yaw: a * 7 + 20, state: STONE.rise, skin: STONE_SKIN.stone }), at, hotUntil: 0 });
        sound(dim, "ed6_stone_rise", at, 0.9, 0.9 + i * 0.05);
        particle(dim, "fx_dust", up(at, 0.5));
        scene.after(26, () => stones[stones.length - 1]?.a.state(STONE.hold));
      }));
    }
    for (let j = 0; j < 2; j++) {
      const [ang, r, kind] = GROVES[k * 2 + j];
      scene.after(j * 7, () => {
        const at = ground(fr.polar(r, ang));
        sprout(at, kind, ang * 3 + j * 50);
        sound(dim, "ed6_sprout", at, 0.9, 0.95 + 0.1 * j);
      });
    }
  }

  BEATS.forEach((t, k) => scene.at(t, () => heartbeat(k)));
  function heartbeat(k: number): void {
    const at = EM[k], n = LINEAGE[k];
    level = k + 1;
    sound(dim, `ed6_heart_${n}`, K, 1.2);
    sound(dim, `ed6_heart_${n}`, at, 1.6);
    codexBeat();
    codex.skin(k + 1);                             // a lineage gem lights on the back cover
    const e = scene.spawn("ed6_emblem", up(at, 0.04), { kind: k, size: C.emblemRadius / 2, yaw: yawOf(F), state: EMBLEM.appear });
    emblems[k] = e;
    scene.after(20, () => e.state(EMBLEM.glow));
    for (let j = 0; j < k; j++) {                  // the hearts already awake beat with it
      const o = emblems[j];
      if (!o?.valid) continue;
      o.state(EMBLEM.beat);
      scene.after(16, () => o.state(EMBLEM.glow));
      particle(dim, `ed6_beat_${LINEAGE[j]}`, up(EM[j], 0.2));
    }
    particle(dim, `ed6_beat_${n}`, up(at, 0.2));
    ring(dim, `ed6_rise_${n}`, up(at, 0.3), C.emblemRadius * 0.7, 4, k * 30);
    line(dim, "ed6_codex_rune", K, up(at, 2), 4);
    atmosphere(k);
    for (const f of foes(at, C.emblemRadius + 0.5)) {
      damage(f, C.beatDamage, caster);
      effect(f, "slowness", C.beatSlowTicks, C.beatSlowAmp);
      knockback(f, at, C.beatKnock, 0.3);
    }
  }
  function fadeEmblem(k: number): void {
    const e = emblems[k];
    if (!e?.valid) return;
    e.state(EMBLEM.fade);
    particle(dim, `ed6_beat_${LINEAGE[k]}`, up(EM[k], 0.2));
    scene.after(22, () => scene.despawn(e));
  }

  // the primordial atmosphere: ambience bed and drifting motes, thickening with every heartbeat
  scene.every(100, () => sound(dim, "ed6_ambience", up(center, 3), 0.35 + 0.17 * level), BEATS[0], T5 + 100);
  scene.every(6, (el) => {
    const i = el / 6;
    if (level === 0) return;
    particle(dim, "ed6_spore", ground(fr.polar(3 + ((i * 7) % 17), i * 67, 0)));
    if (i % 2 === 0 && level >= 2) particle(dim, "ed6_ember_mote", up(fr.polar(16 + (i % 5), -40 + ((i * 23) % 80)), 3));
    if (i % 3 === 0 && level >= 3) particle(dim, "ed6_mist", ground(fr.polar(6 + ((i * 11) % 14), i * 41)));
    if (i % 4 === 1 && level >= 4) particle(dim, "ed6_pollen_drift", up(fr.polar(8 + (i % 9), i * 53), 2));
  }, 40, T5 + 120);

  // ================================================================================== the Nature Dragon
  const DTH = ((N_WALK / 20) / RN) * (180 / Math.PI);       // deg of arc per tick of walking
  const nPos = (th: number): V3 => fr.polar(RN, th);
  const nYaw = (th: number): number => yawDeg(th + 90);      // walking with the domain on its right
  let th = -28;
  const N0 = ground(nPos(th));
  const nature = scene.spawn(NATURE.actor, N0, { yaw: nYaw(th), state: N.hidden, skin: N_SKIN.normal });
  const natMv = new Mover(nature, N0, nYaw(th), T_NATURE, gy);
  const footprints: V3[] = [];
  const nWalk = (cycles: number): void => {
    const th0 = th, from = natMv.cursor, ticks = cycles * N_CYCLE;
    natMv.add(ticks, (p) => nPos(th0 + DTH * p * ticks), { yaw: (t) => nYaw(th0 + DTH * clamp(t - from, 0, ticks)), tag: "walk" });
    scene.at(from, () => nature.state(N.move));
    for (let c = 0; c < cycles; c++) {
      for (const s of N_STEPS) {
        const tt = from + c * N_CYCLE + s.t;
        const thAt = th0 + DTH * (c * N_CYCLE + s.t);
        scene.at(tt, () => footfall(ground(local(nPos(thAt), nYaw(thAt), s.x, s.z)), c === 0 && s.t === 0 ? from : -1));
      }
    }
    th = th0 + DTH * ticks;
    scene.at(from + ticks, () => nature.state(N.idle));
  };
  function footfall(at: V3, cycleStart: number): void {
    footprints.push(at);
    if (footprints.length > 12) footprints.shift();
    const q = scene.spawn("ed_nature_quake", up(at, 0.02), { size: 1.4, state: 1, yaw: (scene.tick * 47) % 360 });
    scene.after(27, () => scene.despawn(q));
    particle(dim, "ed_nature_shock", up(at, 0.15));
    particle(dim, "ed_nature_dust", up(at, 0.4));
    sound(dim, "ed_nature_step", at, 1.1);
    for (const e of foes(at, C.stepRadius)) {
      damage(e, C.stepDamage, caster);
      knockback(e, at, C.stepKnockH, C.stepKnockV);
    }
    void cycleStart;
  }
  const nHold = (ticks: number, yaw?: number): void => { natMv.hold(ticks, yaw ?? nYaw(th)); };

  // Phase II: the strata part, the titanosaur rises neck-first, the forest grows on its back
  const strataI: Actor[] = [];
  scene.at(T2, () => {
    sound(dim, "ed_nature_rumble", N0, 1.6);
    [[0, 9, 1.8], [5, 3, 1.6], [-5, 3, 1.6], [0, -7, 1.5]].forEach(([x, z, size], k) => scene.after(k * 3, () => {
      const at = ground(local(N0, nYaw(-28), x, z));
      strataI.push(scene.spawn("ed_nature_strata", at, { yaw: k * 83, size, state: STRATA.rise }));
      burst(dim, "ed_nature_dust", up(at, 1), 2.5, 3);
      if (k % 2 === 0) sound(dim, "ed_nature_strata", at, 1.2, 0.9 + k * 0.05);
    }));
  });
  scene.at(T2 + 18, () => strataI.forEach((s) => s.state(STRATA.hold)));
  scene.at(T_NATURE, () => { nature.state(N.arrive); movers.push(natMv); sound(dim, "ed_nature_call", up(N0, 10), 1.6); });
  scene.at(T_NATURE + 18, () => { strataI.forEach((s) => s.state(STRATA.part)); fadeEmblem(0); });
  scene.at(T_NATURE + N_T.arriveLand, () => {
    for (const x of [-3, 3]) {
      const at = ground(local(N0, nYaw(-28), x, 5.5));
      footprints.push(at);
      const q = scene.spawn("ed_nature_quake", up(at, 0.02), { size: 1.8, state: 1 });
      scene.after(27, () => scene.despawn(q));
      particle(dim, "ed_nature_shock_big", up(at, 0.2));
      sound(dim, "ed_nature_quake", at, 1.3);
    }
    for (const e of foes(local(N0, nYaw(-28), 0, 5), C.natureLandRadius)) {
      damage(e, C.natureLandDamage, caster);
      knockback(e, N0, C.stepKnockH * 1.5, C.stepKnockV);
    }
  });
  scene.at(T_NATURE + 70, () => strataI.forEach((s) => s.state(STRATA.crumble)));
  scene.at(T_NATURE + 92, () => strataI.forEach((s) => scene.despawn(s)));
  const tPow = T_NATURE + 64;
  scene.at(tPow, () => { nature.state(N.power); sound(dim, "ed_nature_grow", up(N0, 11), 1.4); });
  scene.at(tPow + 20, () => nature.skin(N_SKIN.bloom));
  scene.every(8, () => { burst(dim, "ed_nature_leaf", up(N0, 11), 4, 2); particle(dim, "ed_nature_pollen", up(N0, 13)); }, tPow + 10, tPow + 50);
  nHold(tPow + N_T.power - T_NATURE);              // arrive + power in place
  nWalk(1);                                         // heavy steps along its arc
  nHold(T3 - natMv.cursor);

  // Phase III: geological structures and living forest along its path; roots, pillars; a neck lash
  const natStructs: Actor[] = [];
  const T3w = natMv.cursor, th3 = th;
  nWalk(2);
  [0, 1].forEach((c) => scene.at(T3w + c * N_CYCLE + 8, () => {
    const thA = th3 + DTH * (c * N_CYCLE + 8);
    const p = nPos(thA), y = nYaw(thA);
    const out = ground(local(p, y, -6.5, 1));
    const s = scene.spawn("ed_nature_strata", out, { yaw: c * 97 + 40, size: 1.3, state: STRATA.rise });
    natStructs.push(s);
    scene.after(18, () => s.state(STRATA.hold));
    sound(dim, "ed_nature_strata", out, 1.0, 0.95);
    const inn = ground(local(p, y, 6, -1));
    sprout(inn, c, c * 140 + 30);
    sound(dim, "ed6_sprout", inn, 1.0);
    burst(dim, "ed_nature_leaf", up(inn, 2), 2, 3);
  }));
  const thLash = th;
  const tLash = natMv.cursor + 8;
  nHold(8);
  nHold(N_T.attackB);
  scene.at(tLash, () => { nature.state(N.attack_b); sound(dim, "ed_nature_lash", up(natMv.posAt(tLash), 12), 1.3); });
  scene.at(tLash + N_T.attackBHit, () => {
    const p = natMv.posAt(scene.tick), y = nYaw(thLash);
    const hit = ground(local(p, y, 3, 12));
    particle(dim, "ed_nature_shock", up(hit, 0.2));
    burst(dim, "ed_nature_dust", up(hit, 1), 3, 4);
    for (const e of foes(hit, C.lashRadius)) { damage(e, C.lashDamage, caster); knockback(e, p, 1.6, 0.5); }
  });
  scene.at(tLash + N_T.attackB, () => nature.state(N.idle));
  nHold(6);
  nWalk(1);
  nHold(T4 - natMv.cursor);

  // roots from its footprints bind enemies; a root-bound pillar rises beside each of them
  type Bind = { e?: Entity; root: Actor; tip: V3; pillar?: Actor; cells?: V3[] };
  const binds: Bind[] = [];
  scene.at(T3 + 22, () => {
    const from = footprints.length ? footprints : [N0];
    const near = (p: V3): V3 => from.reduce((b, f) => (distXZ(f, p) < distXZ(b, p) ? f : b), from[0]);
    const found = foes(center, C.rootRadius, C.maxRoots);
    const goals: { e?: Entity; at: V3 }[] = found.length ? found.map((e) => ({ e, at: { ...e.location } }))
      : [0, 1, 2].map((k) => ({ at: ground(fr.polar(5, -30 + k * 30)) }));
    goals.forEach((g, k) => scene.after(k * 3, () => {
      const target = g.e && isAlive(g.e) ? { ...g.e.location } : g.at;
      const fp = near(target);
      const size = clamp(Math.max(0.5, distXZ(fp, target)) / ROOT_LEN, 0.45, 2.8);
      const yaw = yawOf(sub(target, fp));
      const tip = ground(add(fp, mul(fromYaw(yaw), ROOT_LEN * size)));
      const root = scene.spawn("ed_nature_root", up(fp, 0.05), { yaw, size, state: ROOT.grow });
      const b: Bind = { e: g.e, root, tip };
      binds.push(b);
      sound(dim, "ed_nature_root", fp, 1.0);
      line(dim, "ed_nature_dust", fp, tip, 3);
      scene.after(ROOT_BIND - 3, () => {
        particle(dim, "ed_nature_spore", up(tip, 1));
        sound(dim, "ed_nature_bind", tip, 1.0);
        if (b.e && isAlive(b.e)) {
          damage(b.e, C.rootDamage, caster);
          restrain(scene, b.e, C.rootHoldTicks, { x: tip.x, y: Math.max(tip.y, b.e.location.y - 0.5), z: tip.z });
        }
      });
      scene.after(26, () => root.state(ROOT.hold));
      // a pillar of strata and roots rises beside the bound enemy, on the side of the Nature Dragon
      scene.after(30, () => {
        const side = norm(flat(sub(fp, tip)));
        const at = ground(add(tip, mul(side, 2.4)));
        const pil = scene.spawn("ed_nature_pillar", at, { yaw: yawOf(sub(tip, at)), size: 0.9, state: PILLAR.rise });
        b.pillar = pil;
        sound(dim, "ed_nature_pillar", at, 1.0);
        particle(dim, "ed_nature_rise", at);
        particle(dim, "ed_nature_rock", up(at, 1));
        for (const e of foes(at, 1.8)) { damage(e, C.pillarDamage, caster); shove(e, sub(tip, at), 0.7, 0.4); }
        scene.after(8, () => { b.cells = [at]; tb.column(Math.floor(at.x), Math.floor(at.y), Math.floor(at.z), C.pillarBarrierHeight); });
        scene.after(16, () => pil.state(PILLAR.hold));
      });
      scene.after(ROOT_BIND + C.rootHoldTicks, () => { root.state(ROOT.wither); scene.after(22, () => scene.despawn(root)); });
    }));
  });
  scene.at(T4 - 24, () => {                        // the old structures crumble before the Concord
    for (const b of binds) {
      if (b.cells) for (const c of b.cells) tb.removeColumn(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), C.pillarBarrierHeight);
      if (b.pillar) { b.pillar.state(PILLAR.crumble); const p = b.pillar; scene.after(20, () => scene.despawn(p)); }
    }
  });

  // ================================================================================== the Heat Dragon
  const ep = (deg: number, r = C.chordRadius): V3 => ground(fr.polar(r, deg, 0, CH));
  const wallAt = EM[1];
  const H0 = ground(fr.polar(C.chordRadius + 3 + 6.5, 90, 0, CH));
  const H1 = ground(fr.polar(C.chordRadius + 3 + 2.3, 90, 0, CH));
  const yawIn = yawDeg(270);
  const heat = scene.spawn(HEAT.actor, H0, { yaw: yawIn, state: H.hidden, skin: H_SKIN.cool });
  const heatMv = new Mover(heat, H0, yawIn, T_HEAT, gy);
  let planYaw = yawIn;
  let hHits = new Set<string>();
  let hDir: V3 = fr.dir(270);
  let hFinal = false, detonated = false;
  let hStart: V3 = H0;
  const glasses: { a: Actor; at: V3; born: number }[] = [];
  let glassNext = 0;

  function hTurn(yawTo: number): void {
    const d = angleDelta(planYaw, yawTo);
    planYaw = yawTo;
    if (Math.abs(d) < 6) return;
    const ticks = Math.max(4, Math.round((Math.abs(d) / H_TURN) * 20));
    const y0 = yawTo - d, t0 = heatMv.cursor;
    scene.at(t0, () => heat.state(d > 0 ? H.turn_r : H.turn_l));
    heatMv.hold(ticks, undefined, "turn");
    heatMv.segs[heatMv.segs.length - 1].yaw = (t: number) => y0 + d * clamp((t - t0) / ticks, 0, 1);
  }
  /** Charge to `to` (skid included); returns the tick the skid ends. */
  function hCharge(to: V3, opts: { lane?: boolean; final?: boolean; run?: boolean } = {}): number {
    const from = { ...heatMv.last };
    const dir = norm(flat(sub(to, from)));
    hTurn(yawOf(dir));
    const D_ = distXZ(from, to);
    const skidD = ((H_RUN / 20) * (H_T.skid - 1)) / 2;
    const runD = Math.max(0.5, D_ - skidD);
    const prof = [0];
    for (let s = 0, k = 0; s < runD; k++) { s = Math.min(runD, s + (H_RUN / 20) * (k < 6 ? 0.45 + (0.55 * k) / 6 : 1)); prof.push(s); }
    const n = prof.length - 1;
    const t0 = heatMv.cursor;
    const yaw = yawOf(dir);
    const runEnd = add(from, mul(dir, runD));
    heatMv.add(n, (p) => {
      const f = p * n, i = Math.min(n - 1, Math.floor(f));
      return add(from, mul(dir, prof[i] + (prof[i + 1] - prof[i]) * (f - i)));
    }, { yaw, tag: opts.run ? "run" : "charge" });
    heatMv.add(H_T.skid, (p) => add(runEnd, mul(dir, skidD * (1 - (1 - p) * (1 - p)))), { yaw, tag: opts.run ? "skidrun" : "skid" });
    const tEnd = heatMv.cursor;
    let lane: Actor | undefined;
    if (opts.lane) {
      scene.at(Math.max(scene.tick, t0 - 16), () => {
        lane = scene.spawn("ed_heat_lane", ground(add(from, mul(dir, 3.5))), { yaw, state: LANE.appear });
        lane.prop("len", clamp(D_ + 2, 4, 40));
        sound(dim, "ed_heat_lane", from, 0.9);
      });
      scene.at(t0, () => lane?.state(opts.final ? LANE.surge : LANE.armed));
      scene.at(tEnd, () => { lane?.state(LANE.fade); const l = lane; scene.after(10, () => { if (l) scene.despawn(l); }); });
    }
    scene.at(t0, () => {
      heat.state(opts.run ? H.move : H.charge);
      hHits = new Set();
      hDir = dir;
      hFinal = !!opts.final;
      hStart = from;
      glassNext = 0;
      if (!opts.run) sound(dim, "ed_heat_roar", up(from, 4), 1.2, 1.05);
    });
    scene.at(t0 + n, () => {
      heat.state(H.skid);
      sound(dim, "ed_heat_skid", runEnd, 1.0);
      particle(dim, "ed_heat_skid", up(runEnd, 0.3));
    });
    return tEnd;
  }

  function heatTick(t: number): void {
    const seg = heatMv.segAt(t);
    if (!seg || !seg.tag || seg.tag === "turn") return;
    const pos = heatMv.posAt(t);
    const moving = seg.tag === "charge" || seg.tag === "skid";
    if (t % 3 === 0) particle(dim, "ed_heat_haze", up(add(pos, mul(hDir, -3)), 1.2));
    if (t % 4 === 0) particle(dim, "ed_heat_ember", up(add(pos, mul(hDir, 1.5)), 4.5));
    // the standing stones it passes turn to glowing glass
    for (const s of stones) {
      if (hFinal && !s.gone && distXZ(s.at, pos) < 3.4) {     // thermal reaction: the glass stone bursts
        s.gone = true;
        s.a.skin(STONE_SKIN.glass).state(STONE.sink);
        sound(dim, "ed6_vitrify", s.at, 1.4, 0.8);
        burst(dim, "ed6_glass_shard", up(s.at, 2), 1.5, 3);
        particle(dim, "ed6_thermal", up(s.at, 1.5));
        for (const e of foes(s.at, C.vitrifyRadius)) { damage(e, C.vitrifyDamage, caster); burnT(e, C.burnSeconds); }
      }
      if (s.gone || t < s.hotUntil || distXZ(s.at, pos) > C.vitrifyReach) continue;
      s.hotUntil = t + 130;
      s.a.skin(STONE_SKIN.glass).state(STONE.flare);
      scene.after(10, () => s.a.state(STONE.hold));
      scene.after(120, () => s.a.skin(STONE_SKIN.obsidian));
      sound(dim, "ed6_vitrify", s.at, 1.1);
      particle(dim, "ed6_sizzle", up(s.at, 2));
      particle(dim, "ed6_glass_shard", up(s.at, 2.5));
      for (const e of foes(s.at, C.vitrifyRadius)) { damage(e, C.vitrifyDamage, caster); burnT(e, C.burnSeconds); }
    }
    if (!moving) return;
    // the ground behind it vitrifies
    const along = dot(sub(pos, hStart), hDir);
    if (seg.tag === "charge" && along >= glassNext) {
      glassNext = along + C.glassEvery;
      const g = scene.spawn("ed_heat_glass", ground(add(pos, mul(right(hDir), (glasses.length % 2 ? 0.8 : -0.8)))),
        { yaw: glasses.length * 67, state: GLASS.appear });
      const rec = { a: g, at: g.loc, born: t };
      glasses.push(rec);
      if (glasses.length % 3 === 1) sound(dim, "ed_heat_glass", rec.at, 0.8);
      scene.after(6, () => g.state(GLASS.hold));
      scene.after(80, () => g.skin(1));
      scene.after(C.glassLifeTicks, () => g.state(GLASS.fade));
      scene.after(C.glassLifeTicks + 17, () => { scene.despawn(g); glasses.splice(glasses.indexOf(rec), 1); });
    }
    // horns and body strike everything in the lane
    const rv = right(hDir);
    for (const e of foes(add(pos, mul(hDir, 3)), 10)) {
      if (hHits.has(e.id)) continue;
      const dy = e.location.y - pos.y;
      if (dy > 7 || dy < -3) continue;
      const rel = flat(sub(e.location, pos));
      const a = dot(rel, hDir), lat = Math.abs(dot(rel, rv));
      const away = norm(add(mul(rv, dot(rel, rv) >= 0 ? 1 : -1), mul(hDir, 0.45)));
      if (a > 2 && a < H_HORN + 1.5 && lat < C.chargeHalfWidth) {
        hHits.add(e.id);
        if (damage(e, hFinal ? C.finalHornDamage : C.hornDamage, caster)) shove(e, away, C.chargeKnockH, C.chargeKnockV);
        burnT(e, C.burnSeconds);
        particle(dim, "ed_heat_spark", up(e.location, 1.1));
        sound(dim, "ed_heat_hit", e.location, 1.0);
      } else if (a > -3 && a <= 2 && lat < C.chargeHalfWidth + 0.6) {
        hHits.add(e.id);
        if (damage(e, C.bodyDamage, caster)) shove(e, away, C.chargeKnockH * 0.8, C.chargeKnockV);
        burnT(e, C.burnSeconds);
        particle(dim, "ed_heat_ember", up(e.location, 1));
      }
    }
    if (hFinal && !detonated && Z && dot(sub(pos, Z.G), Z.L) >= -0.5) detonate();
  }
  scene.every(1, () => heatTick(scene.tick), T_HEAT, T5);
  scene.every(20, () => {                           // vitrified ground keeps burning
    for (const g of glasses) {
      if (scene.tick - g.born > 80) continue;
      for (const e of foes(g.at, C.glassBurnRadius)) { damage(e, C.glassBurnDamage, caster); burnT(e, 1); }
    }
  }, T_HEAT, T5);

  // Phase II: it unfolds behind a wall of shimmering heat, ignites and charges through it
  let wall: Actor | undefined;
  scene.at(T_HEAT - 2, () => {
    wall = scene.spawn("ed_heat_shimmer", wallAt, { yaw: yawIn, state: WALL.form });
    sound(dim, "ed_heat_shimmer", wallAt, 1.2);
  });
  scene.every(4, (e) => {
    particle(dim, "ed_heat_haze", up(add(wallAt, mul(fr.F, (e % 3) * 2.5 - 2.5)), 1.5));
    particle(dim, "ed_heat_ember", up(wallAt, 3));
  }, T_HEAT, T_HEAT + 70);
  scene.at(T_HEAT, () => { heat.state(H.arrive); movers.push(heatMv); });
  heatMv.add(H_T.arriveWalk, (p) => lerp(H0, H1, p), { yaw: yawIn, tag: "walk" });
  heatMv.hold(H_T.ignite + 6 - (H_T.arriveWalk - 24), yawIn);
  const tIgn = T_HEAT + H_T.arriveWalk + 6;
  scene.at(tIgn, () => { heat.state(H.ignite); sound(dim, "ed_heat_ignite", up(H1, 4), 1.3); });
  scene.at(tIgn + 10, () => { heat.skin(H_SKIN.ignited); burst(dim, "ed_heat_ember", up(H1, 4), 2.2, 4); });
  scene.at(tIgn + H_T.igniteRoar, () => {
    particle(dim, "ed_heat_ring", up(H1, 0.3));
    ring(dim, "ed_heat_vent", up(H1, 3.5), 2.8, 5);
    for (const e of foes(H1, 5)) { damage(e, C.bodyDamage, caster); knockback(e, H1, 0.8, 0.35); }
  });
  const tArrEnd = hCharge(ep(270), { lane: true });
  const tArrRun = tIgn + H_T.ignite;
  scene.at(tArrRun - 2, () => { wall?.state(WALL.part); fadeEmblem(1); });
  scene.at(tArrRun + 12, () => { heat.skin(H_SKIN.whitehot); particle(dim, "fx_flash", up(heatMv.posAt(scene.tick), 4)); });   // horns blaze as it runs
  scene.at(tArrRun + 18, () => wall?.state(WALL.fade));
  scene.at(tArrRun + 34, () => { if (wall) scene.despawn(wall); });
  scene.at(tArrEnd, () => { heat.state(H.pant).skin(H_SKIN.ignited); });
  heatMv.hold(T3 - heatMv.cursor);

  // Phase III: charges between the standing stones, back and forth, until the Concord calls it
  let lastEnd = 270;
  function heatPlan(): void {
    if (heatMv.cursor + 80 > T4 - 30) { heatToFinal(); return; }
    let next: number;
    if (lastEnd === 270) {                          // swing round the outside to the near end of the stones
      const pts = [heatMv.last, ep(240, C.chordRadius + 1.8), ep(205, C.chordRadius + 1.5), ep(180)];
      const t0 = heatMv.cursor;
      heatMv.path(pts, H_RUN * 0.8, { tag: "run" });
      scene.at(t0, () => heat.state(H.move));
      lastEnd = 180;
      planYaw = yawOf(sub(ep(180), ep(205, C.chordRadius + 1.5)));
    }
    next = lastEnd === 180 ? 0 : 180;
    const end = hCharge(ep(next), { lane: true });
    lastEnd = next;
    scene.at(end, () => heat.state(H.pant));
    heatMv.hold(6);
    scene.at(heatMv.cursor, heatPlan);
  }
  scene.at(T3, heatPlan);

  // ================================================================================== the Water & Ice Dragon
  const tideY = gy(CT);
  const loop = new ArcPath((u) => {
    const a = u * 2 * Math.PI;
    const p = add(CT, add(mul(fr.F, 9 * Math.sin(a)), mul(fr.R, 4.5 * Math.sin(2 * a))));
    return { x: p.x, y: tideY + 8 + 1.2 * Math.sin(a + 0.6), z: p.z };
  }, 160, true);
  const loopTan = (s: number): number => yawOf(sub(loop.at(s + 0.5), loop.at(s - 0.5)));
  const M0 = loop.at(0);
  const tide = scene.spawn(TIDE.actor, M0, { yaw: loopTan(0), state: D.hidden, skin: 0 });
  const tideMv = new Mover(tide, M0, loopTan(0), T_TIDE);
  const tSwim = T_TIDE + D_T.arrive;
  tideMv.hold(D_T.arrive, loopTan(0));
  const swimSeg = tideMv.add(T4 - tSwim, (p, t) => loop.at((D_SWIM / 20) * (t - tSwim)), { tag: "swim" });
  const tideS = (t: number): number => (D_SWIM / 20) * Math.max(0, t - tSwim);
  void swimSeg;

  // Phase II: water streams spiral into a floating formation; the dragon forms in it and swims out
  let mass: Actor | undefined;
  const streamsIn: { a: Actor; ang: number; prev: V3 }[] = [];
  scene.at(T_TIDE - 18, () => {
    mass = scene.spawn("ed_tide_mass", M0, { state: MASS.gather, size: 1.2 });
    sound(dim, "ed_tide_mass", M0, 1.3);
    sound(dim, "ed_tide_currents", M0, 1.1);
    for (let k = 0; k < 4; k++) {
      const ang = k * 90 + 20;
      const p0 = up(fr.polar(10, ang, 0, M0), -4 + (k % 2) * 3);
      streamsIn.push({ a: scene.spawn("ed_tide_stream", p0, { state: STREAM.form, size: 1.3, yaw: yawOf(sub(M0, p0)) }), ang, prev: p0 });
    }
  });
  scene.at(T_TIDE - 10, () => streamsIn.forEach((s) => s.a.state(STREAM.hold)));
  scene.span(T_TIDE - 17, T_TIDE + 4, (p) => {
    const e = smooth(p);
    for (const s of streamsIn) {
      const pos = up(fr.polar(10 * (1 - e) + 0.4, s.ang + 200 * e, 0, M0), -3 * (1 - e));
      s.a.move(pos, yawOf(flat(sub(pos, s.prev))));
      s.prev = pos;
    }
  });
  scene.at(T_TIDE + 2, () => { streamsIn.forEach((s) => s.a.state(STREAM.fade)); burst(dim, "ed_tide_bubble", M0, 3, 5); });
  scene.at(T_TIDE + 8, () => streamsIn.forEach((s) => scene.despawn(s.a)));
  scene.at(T_TIDE + 2, () => mass?.state(MASS.hold));
  scene.at(T_TIDE, () => { tide.state(D.arrive); movers.push(tideMv); sound(dim, "ed_tide_emerge", M0, 1.3); fadeEmblem(2); });
  scene.at(tSwim, () => { tide.state(D.swim); burst(dim, "ed_tide_splash", M0, 3, 5); });
  // the dorsal sail crystallises progressively while it swims
  for (let k = 1; k <= 10; k++) scene.at(tSwim + k * 7, () => tide.prop("frost", k / 10));
  scene.at(tSwim + 30, () => { tide.skin(1); sound(dim, "ed_tide_freeze", tideMv.posAt(scene.tick), 1.0, 1.2); });
  scene.every(5, () => particle(dim, "ed_tide_flake", up(tideMv.posAt(scene.tick), 6)), tSwim + 10, T4);
  scene.every(9, () => particle(dim, "ed_tide_bubble", M0), T_TIDE, T4);
  // its tail drags the water: two streams follow in its wake, currents run on the ground below
  const wake: Actor[] = [];
  scene.at(tSwim + 20, () => {
    for (const lag of [17, 22]) wake.push(scene.spawn("ed_tide_stream", loop.at(-lag), { state: STREAM.form, size: 1.2 }));
  });
  scene.at(tSwim + 28, () => wake.forEach((w) => w.state(STREAM.hold)));
  scene.every(1, () => {
    const s = tideS(scene.tick);
    [17, 22].forEach((lag, i) => wake[i]?.move(loop.at(s - lag), loopTan(s - lag)));
  }, tSwim + 20, T4);
  scene.at(T4, () => { wake.forEach((w) => w.state(STREAM.fade)); mass?.state(MASS.disperse); });
  scene.at(T4 + 10, () => wake.forEach((w) => scene.despawn(w)));
  scene.at(T4 + 22, () => { if (mass) scene.despawn(mass); });

  const tideHit = new Map<string, number>();
  scene.every(4, () => {                            // the currents it drags shove enemies along its course
    const t = scene.tick, s = tideS(t);
    const p = ground(loop.at(s)), back = ground(loop.at(s - 10));
    const dir = norm(flat(sub(p, back)));
    if (t % 8 === 0) particle(dim, "ed_tide_spray", up(back, 0.5));
    for (const e of foes(lerp(p, back, 0.5), 8)) {
      if (distToSegment(e.location, p, back) > C.currentReach) continue;
      shove(e, dir, C.currentShove, 0.1);
      const last = tideHit.get(e.id) ?? -999;
      if (t - last > 50) { tideHit.set(e.id, t); damage(e, C.currentDamage, caster); particle(dim, "ed_tide_spray", e.location); }
    }
  }, tSwim + 10, T4);

  // Phase III: suspended water at the lobes; crystalline bridges freeze along its course
  const lobes: Actor[] = [];
  scene.at(T3 - 10, () => {
    for (const u of [0.25, 0.75]) {
      const at = loop.at(loop.length * u);
      lobes.push(scene.spawn("ed_tide_mass", at, { state: MASS.gather, size: 0.75 }));
      sound(dim, "ed_tide_mass", at, 0.9, 1.2);
    }
  });
  scene.at(T3 + 10, () => lobes.forEach((l) => l.state(MASS.hold)));
  scene.at(T4 - 6, () => lobes.forEach((l) => l.state(MASS.disperse)));
  scene.at(T4 + 14, () => lobes.forEach((l) => scene.despawn(l)));
  const bridges: Actor[] = [];
  [T3 + 30, T3 + 120, T3 + 205].forEach((t) => scene.at(t, () => {
    const s = tideS(t);
    const a = ground(loop.at(s - 13)), b = ground(loop.at(s));
    const L_ = distXZ(a, b);
    if (L_ < 5) return;
    const br = scene.spawn("ed6_bridge", up(a, 0.1), { yaw: yawOf(sub(b, a)), size: L_ / BRIDGE_LEN, state: BRIDGE.form });
    bridges.push(br);
    sound(dim, "ed6_bridge", lerp(a, b, 0.5), 1.2);
    scene.after(26, () => br.state(BRIDGE.hold));
    scene.after(12, () => {
      line(dim, "ed_tide_flake", up(a, 2), up(b, 2), 4);
      for (const e of foes(lerp(a, b, 0.5), L_ / 2 + C.bridgeWidth)) {
        if (distToSegment(e.location, a, b) > C.bridgeWidth) continue;
        damage(e, C.bridgeDamage, caster);
        effect(e, "slowness", C.bridgeSlowTicks, C.bridgeSlowAmp);
        particle(dim, "ed_tide_splinter", up(e.location, 1));
      }
    });
  }));

  // ================================================================================== the Air Dragon
  const AP = (f: number, r: number, h: number): V3 => fr.p(f, r, h);
  const airStart = AP(-12, -8, 34);
  const air = scene.spawn(AIR.actor, airStart, { yaw: yawOf(sub(AP(-8, 2, 30), airStart)), state: A.hidden });
  const airMv = new Mover(air, airStart, air.yaw, T_AIR);
  const airForce: { from: number; to: number; s: number }[] = [];
  const force = (from: number, ticks: number, s: number): void => { airForce.push({ from, to: from + ticks, s }); };
  let airState: number = A.hidden, airDwell = 0;
  const circlePt = (deg: number, t: number): V3 => fr.polar(AIR_R, deg, AIR_H + 0.9 * Math.sin(t * 0.07));
  const OMEGA = ((16 / 20) / AIR_R) * (180 / Math.PI);        // deg per tick at 16 blocks / s
  function airCircle(deg0: number, ticks: number): void {
    const from = airMv.cursor;
    airMv.add(ticks, (p, t) => circlePt(deg0 + OMEGA * (t - from), t), { tag: "circle" });
  }
  const circleDegAt = (p: V3): number => {
    const r = sub(p, center);
    return (Math.atan2(dot(r, fr.R), dot(r, fr.F)) * 180) / Math.PI;
  };
  /** Leave the circle at tick t (it keeps circling until then); returns the position there. */
  function airBreak(t: number): V3 { airMv.truncate(t); return airMv.last; }

  // Phase II: through the clouds, a barrel roll, a stoop over the stones and a climb into its orbit
  const cloudAt = AP(-6, 1, 30);
  let clouds: Actor[] = [];
  scene.at(T_AIR - 22, () => {
    clouds = [scene.spawn("ed_air_cloud", cloudAt, { yaw: yawOf(F) + 90, size: 1.4, state: CLOUD.form }),
      scene.spawn("ed_air_cloud", AP(-14, -6, 33), { yaw: yawOf(F), size: 0.9, state: CLOUD.form })];
    sound(dim, "ed_air_cloud", cloudAt, 1.4);
    burst(dim, "ed_air_cloud", cloudAt, 5, 5);
  });
  scene.at(T_AIR - 4, () => clouds.forEach((c) => c.state(CLOUD.part)));
  scene.at(T_AIR + 60, () => clouds.forEach((c) => c.state(CLOUD.fade)));
  scene.at(T_AIR + 84, () => clouds.forEach((c) => scene.despawn(c)));
  airMv.add(A_T.arrive, (p) => bezierPath([airStart, AP(-8, 2, 30), AP(-4, 9, 26), AP(3, 10, 23)], p));
  force(T_AIR, A_T.arrive, A.arrive);
  const tRoll = airMv.cursor;
  airMv.add(A_T.roll, (p) => lerp(AP(3, 10, 23), AP(12, 8, 22), p));
  force(tRoll, A_T.roll, A.roll);
  airMv.path([AP(12, 8, 22), AP(14, 3, 22), AP(10, -1, 22), AP(6, -2, 22)], 16);
  const tStoop = airMv.cursor;
  airMv.add(A_T.stoop, (p) => lerp(AP(6, -2, 22), AP(-2, 5, 12.5), p * p));
  force(tStoop, A_T.stoop, A.stoop);
  const tFlap = airMv.cursor;
  airMv.path([AP(-2, 5, 12.5), AP(-6, 8, 16), AP(-10, 6, 21)], 12);
  force(tFlap, airMv.cursor - tFlap, A.move);
  const e0 = circleDegAt(AP(-10, 6, 21));
  airMv.path([AP(-10, 6, 21), circlePt(e0 + 6, airMv.cursor + 6)], 14);
  airCircle(e0 + 6 + OMEGA * 0, 4000);
  scene.at(T_AIR, () => { air.state(A.arrive); airState = A.arrive; movers.push(airMv); sound(dim, "ed_air_call", cloudAt, 1.6); });
  scene.at(T_AIR + 30, () => { fadeEmblem(3); burst(dim, "ed_air_feather", up(airMv.posAt(scene.tick), 1), 2, 4); });
  scene.at(tRoll, () => { sound(dim, "ed_air_flap", airMv.posAt(tRoll), 1.2); burst(dim, "ed_air_feather", up(airMv.posAt(tRoll), 1), 1.5, 3); });
  scene.at(tStoop, () => { sound(dim, "ed_air_dive", airMv.posAt(tStoop), 1.5); particle(dim, "ed_air_boom", up(airMv.posAt(tStoop), 1)); });
  scene.at(tFlap, () => {
    const at = airMv.posAt(tFlap), g = ground(at);
    sound(dim, "ed_air_flare", at, 1.3);
    particle(dim, "ed_air_shock", up(g, 0.3));
    burst(dim, "ed_air_gust", up(g, 0.8), 2.5, 4);
    for (const e of foes(g, C.gustRadius)) { damage(e, C.gustDamage, caster); knockback(e, g, C.gustKnock, 0.45); }
  });

  function airTick(t: number): void {
    const seg = airMv.segAt(t);
    const f = airForce.find((x) => t >= x.from && t < x.to);
    let want: number;
    if (f) want = f.s;
    else if (seg?.tag === "perch" || !seg) want = A.idle;
    else if ((seg.tag === "circle" || seg.tag === "helix") && (t - seg.from) % 96 >= 70 && (t - seg.from) % 96 < 86) want = A.move;
    else {
      const vy = airMv.posAt(t + 1).y - airMv.posAt(t).y;
      want = airMv.yawRate > A_BANK ? A.turn_r : airMv.yawRate < -A_BANK ? A.turn_l : vy > 0.1 ? A.move : A.glide;
    }
    if (want !== airState && (f || t >= airDwell)) { air.state(want); airState = want; airDwell = t + 8; }
    if (t % 3 === 0 && seg && seg.tag !== "perch") particle(dim, "ed_air_trail", airMv.posAt(t));
  }
  scene.every(1, () => airTick(scene.tick), T_AIR + 1, T5 + 200);

  // Phase III: a full-spread beat; its wind lifts rock, leaves and ice into aerial formations
  const debris: { a: Actor; at: V3 }[] = [];
  scene.at(T3 + 20, () => {
    force(scene.tick, A_T.power, A.power);
    air.skin(1);
    sound(dim, "ed_air_call", airMv.posAt(scene.tick), 1.5);
    ring(dim, "ed_air_spark", up(airMv.posAt(scene.tick), 1), 4, 6);
  });
  scene.at(T3 + 30, () => {
    [[8, 150], [5, 80], [7, 40]].forEach(([r, a], k) => scene.after(k * 6, () => {
      const g = ground(fr.polar(r, a));
      const d = scene.spawn("ed6_debris", up(g, 6), { yaw: k * 120, size: 1.0, state: DEBRIS.lift });
      debris.push({ a: d, at: g });
      scene.after(32, () => d.state(DEBRIS.orbit));
      sound(dim, "ed6_debris_lift", g, 1.2, 0.95 + k * 0.05);
      burst(dim, "ed_nature_rock", up(g, 0.5), 2, 3);
      particle(dim, "ed6_updraft", up(g, 0.2));
      line(dim, "ed_air_streak", airMv.posAt(scene.tick), up(g, 9), 5);
    }));
  });
  scene.every(C.updraftEvery, () => {
    for (const d of debris) {
      particle(dim, "ed6_updraft", up(d.at, 0.3));
      particle(dim, "ed_air_gust", up(d.at, 1));
      for (const e of foes(d.at, C.updraftRadius)) {
        damage(e, C.updraftDamage, caster);
        knockback(e, d.at, 0.15, C.updraftLift);
      }
    }
  }, T3 + 70, T4 - 30);
  scene.at(T4 - 26, () => {
    for (const d of debris) {
      d.a.state(DEBRIS.scatter);
      sound(dim, "ed6_debris_fall", d.at, 1.2);
      scene.after(10, () => {
        particle(dim, "ed6_debris_fall", up(d.at, 8));
        particle(dim, "ed_nature_dust", up(d.at, 0.5));
        for (const e of foes(d.at, C.debrisRadius)) { damage(e, C.debrisDamage, caster); knockback(e, d.at, 0.6, 0.3); }
      });
      scene.after(22, () => scene.despawn(d.a));
    }
  });
  scene.at(T3 + 60, () => air.skin(0));

  // ================================================================================== Phase IV: the Fourfold Concord
  type Zone = { G: V3; L: V3; yawL: number; SF: V3; TL: V3; tideYaw: number };
  let Z: Zone | undefined;
  function zone(): Zone {
    if (Z) return Z;
    const found = foes(center, C.zoneSearch);
    let G = center;
    if (found.length) {
      const seed = found[0];
      const grp = found.filter((e) => distXZ(e.location, seed.location) <= 6);
      G = mul(grp.reduce((s, e) => add(s, e.location), { x: 0, y: 0, z: 0 }), 1 / grp.length);
      const off = flat(sub(G, center));
      if (len(off) > C.zoneMaxOffset) G = add(center, mul(norm(off), C.zoneMaxOffset));
    }
    G = ground(G);
    const L = fr.dir(300);
    Z = { G, L, yawL: yawOf(L), SF: ground(add(G, mul(L, -C.finalRunUp))), TL: ground(fr.polar(13, 240, 0, G)), tideYaw: yawDeg(330) };
    return Z;
  }

  // the Heat Dragon's last Phase III run takes it to the head of the final lane
  function heatToFinal(): void {
    const z = zone();
    const from = heatMv.last;
    const a0 = (Math.atan2(dot(sub(from, CH), fr.R), dot(sub(from, CH), fr.F)) * 180) / Math.PI;
    const a1 = (Math.atan2(dot(sub(z.SF, CH), fr.R), dot(sub(z.SF, CH), fr.F)) * 180) / Math.PI;
    const da = angleDelta(a0, a1);
    const pts = [from, ep(a0 + da * 0.33, C.chordRadius + 1.6), ep(a0 + da * 0.7, C.chordRadius + 1.6), z.SF];
    const t0 = heatMv.cursor;
    heatMv.path(pts, H_RUN * 0.8, { tag: "run" });
    scene.at(t0, () => heat.state(H.move));
    const tStop = heatMv.cursor;
    heatMv.hold(H_T.skid, undefined, "skidstop");
    scene.at(tStop, () => { heat.state(H.skid); particle(dim, "ed_heat_skid", up(z.SF, 0.3)); });
    planYaw = yawOf(sub(pts[3], pts[2]));
    hTurn(z.yawL);
    const tWait = heatMv.cursor;
    scene.at(tWait, () => heat.state(H.pant));
    heatMv.hold(Math.max(1, T4 + 256 - heatMv.cursor), z.yawL);
  }

  // ---- the frame of the Concord
  let tele: Actor | undefined;
  let ringA: Actor | undefined;
  const ringCells: V3[] = [];
  scene.at(T4, () => {
    const z = zone();
    tele = scene.spawn("telegraph", up(z.G, 0.05), { kind: 2, size: RING_R + 1, state: 4 });
    sound(dim, "ed6_concord", z.G, 1.6);
    sound(dim, "ed6_heart_all", K, 1.2);
    codexBeat();
    particle(dim, "ed6_concord", up(z.G, 3));
    line(dim, "ed6_codex_rune", K, up(z.G, 3), 5);
  });
  scene.at(T4 + 40, () => tele?.state(2));

  // ---- 1. Geological shockwaves (Nature): it squares its body, raises the ring, slams the earth
  const yN = nYaw(th);
  natMv.hold(20, undefined);
  natMv.segs[natMv.segs.length - 1].yaw = (t: number) => yN + N_TURN * clamp((t - T4) / 20, 0, 1);
  nHold(T5 - natMv.cursor, yN + N_TURN);
  scene.at(T4, () => nature.state(N.turn_r));
  scene.at(T4 + 20, () => nature.state(N.idle));
  scene.at(T4 + 10, () => {
    const z = zone();
    ringA = scene.spawn("ed6_ring", z.G, { yaw: z.yawL, size: C.ringRadius / RING_R, state: RING.rise });
    sound(dim, "ed6_ring_rise", z.G, 1.6);
    sound(dim, "ed_nature_bellow", up(natMv.posAt(scene.tick), 12), 1.5);
    ring(dim, "ed_nature_rise", z.G, C.ringRadius, 8);
    for (const e of foes(z.G, C.ringRadius + 1.5)) {
      const d = distXZ(e.location, z.G);
      if (Math.abs(d - C.ringRadius) < 1.6) shove(e, sub(z.G, e.location), 0.9, 0.35);
    }
  });
  scene.at(T4 + 34, () => {
    const z = zone();
    const doorA = 300, doorB = 120;
    const seen = new Set<string>();
    const n = Math.ceil(2 * Math.PI * C.ringRadius);
    for (let i = 0; i < n; i++) {
      const a = (i * 360) / n;
      if (Math.abs(angleDelta(a, doorA)) < C.doorwayDeg || Math.abs(angleDelta(a, doorB)) < C.doorwayDeg) continue;
      const p = fr.polar(C.ringRadius, a, 0, z.G);
      const c = { x: Math.floor(p.x), y: Math.floor(gy(p)), z: Math.floor(p.z) };
      const key = `${c.x},${c.z}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (tb.column(c.x, c.y, c.z, C.ringBarrierHeight) > 0) ringCells.push(c);
    }
  });
  scene.at(T4 + 42, () => ringA?.state(RING.hold));
  const tSlam = T4 + 30;
  scene.at(tSlam, () => { nature.state(N.attack_a); sound(dim, "ed_nature_rumble", natMv.posAt(tSlam), 1.4, 1.1); });
  scene.at(tSlam + N_T.attackAHit, () => {
    const z = zone();
    const p = ground(natMv.posAt(scene.tick)), y = yN + N_TURN;
    const SL = ground(local(p, y, N_SLAM.x, N_SLAM.z));
    const q = scene.spawn("ed_nature_quake", up(SL, 0.03), { size: 3.2, state: 1 });
    scene.after(27, () => scene.despawn(q));
    sound(dim, "ed_nature_slam", SL, 2.0);
    particle(dim, "ed_nature_shock_big", up(SL, 0.2));
    particle(dim, "fx_flash", up(SL, 1));
    for (const e of foes(SL, C.slamRadius)) { damage(e, C.slamDamage, caster); knockback(e, SL, 1.2, 0.5); }
    // the shockwave runs through the ground into the ring
    const D_ = distXZ(SL, z.G);
    const steps = Math.max(2, Math.floor((D_ - C.ringRadius) / 3));
    const hit = new Set<string>();
    for (let i = 1; i <= steps; i++) {
      scene.after(i * 3, () => {
        const at = ground(lerp(SL, z.G, (i * 3) / D_));
        const qq = scene.spawn("ed_nature_quake", up(at, 0.02), { size: 1.3, state: 1, yaw: i * 61 });
        scene.after(27, () => scene.despawn(qq));
        particle(dim, "ed6_geo_shock", up(at, 0.2));
        particle(dim, "ed_nature_rock", up(at, 0.4));
        if (i % 2) sound(dim, "ed_nature_quake", at, 1.0, 0.9 + i * 0.05);
        for (const e of foes(at, C.quakeRadius)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, C.quakeDamage, caster);
          knockback(e, at, 0.4, 0.45);
        }
      });
    }
    // three pulses from the pillars converge on the enclosed zone
    C.shockPulseDamage.forEach((dmg, k) => scene.after(steps * 3 + 3 + k * 11, () => {
      ringA?.state(RING.quake);
      scene.after(10, () => ringA?.state(RING.hold));
      sound(dim, "ed6_geo_shock", z.G, 1.6, 0.9 + k * 0.1);
      particle(dim, "ed6_geo_shock", up(z.G, 0.25));
      particle(dim, "ed_nature_shock_big", up(z.G, 0.3));
      ring(dim, "ed_nature_rock", up(z.G, 0.5), C.ringRadius * 0.8, 6, k * 20);
      for (const e of foes(z.G, C.ringRadius + 0.5)) {
        damage(e, dmg, caster);
        effect(e, "slowness", C.shockSlowTicks, 1);
        knockback(e, e.location, 0, 0.45);
      }
    }));
  });
  scene.at(tSlam + N_T.attackA, () => nature.state(N.idle));

  // ---- the Tide Dragon leaves its figure-eight and lands beside the ring
  scene.at(T4, () => {
    const z = zone();
    const cur = tideMv.posAt(T4), s = tideS(T4);
    const h = fr.dir(330);
    const app = up(add(z.TL, mul(h, -9)), 4.5);
    tideMv.truncate(T4);
    tideMv.path([cur, add(cur, mul(norm(sub(loop.at(s + 1), loop.at(s - 1))), 4)), app, up(z.TL, 1.6)], D_SWIM, { tag: "swim" });
    const tLand = tideMv.cursor;
    tideMv.hold(T5 + 30 - tideMv.cursor, z.tideYaw);
    const ls = tideMv.segs[tideMv.segs.length - 1];
    ls.at = () => z.TL;
    scene.at(tLand, () => {
      tide.state(D.land);
      sound(dim, "ed_tide_land", z.TL, 1.3);
    });
    scene.at(tLand + D_T.landHit, () => {
      ring(dim, "ed_tide_splash", up(z.TL, 0.3), 3, 6);
      particle(dim, "ed_tide_frost_ring", up(z.TL, 0.2));
      for (const e of foes(z.TL, 4)) { damage(e, C.currentDamage, caster); knockback(e, z.TL, 0.8, 0.3); }
    });
    scene.at(tLand + D_T.land, () => tide.state(D.idle));
  });

  // ---- 2. Moving water and freezing formations (Water & Ice)
  type Current = { a: Actor; R: number; dir: V3; side: V3; born: number; touched: Set<string> };
  const currents: Current[] = [];
  const frozen = new Map<string, () => void>();
  let shell: Actor | undefined;
  const tSweep = T4 + 112;
  scene.at(tSweep, () => { tide.state(D.attack_a); sound(dim, "ed_tide_sweep", zone().TL, 1.3); });
  D_T.sweepHit.forEach((hh, w) => scene.at(tSweep + hh, () => {
    const z = zone();
    const tail = add(z.TL, mul(fr.dir(330), -10));
    let dir = norm(flat(sub(tail, z.G)));
    if (w === 1) dir = mul(dir, -1);
    sound(dim, "ed_tide_flow", tail, 1.2, 0.95 + w * 0.08);
    for (let k = 0; k < 2; k++) {
      const R_ = C.ringRadius * (k === 0 ? 0.78 : 0.5);
      const side = k === 0 ? right(dir) : mul(right(dir), -1);
      const a = scene.spawn("ed_tide_current", z.G, { kind: k, size: R_ / CUR_R, state: CUR.form, yaw: yawOf(dir) });
      currents.push({ a, R: R_, dir, side, born: scene.tick, touched: new Set() });
      line(dim, "ed_tide_spray", up(tail, 1), up(add(z.G, mul(dir, R_)), 1), 5);
      scene.after(16, () => a.state(CUR.flow));
    }
  }));
  scene.every(4, () => {                            // the water carries enemies round the ring
    const z = zone();
    for (const e of foes(z.G, C.ringRadius + 1)) {
      if (frozen.has(e.id)) continue;
      for (const c of currents) {
        const v = flat(sub(e.location, z.G));
        const r = Math.hypot(v.x, v.z);
        const deg = (Math.atan2(dot(v, c.side), dot(v, c.dir)) * 180) / Math.PI;
        if (Math.abs(r - c.R) > 1.4 || deg < -12 || deg > Math.min(CUR_SWEEP, (scene.tick - c.born) * 17)) continue;
        const a = (deg * Math.PI) / 180;
        const tangent = add(mul(c.dir, -Math.sin(a)), mul(c.side, Math.cos(a)));
        shove(e, add(tangent, mul(norm(flat(sub(z.G, e.location))), (r - c.R) * 0.25)), C.concordCurrentShove, 0.06);
        if (!c.touched.has(e.id)) { c.touched.add(e.id); damage(e, C.concordCurrentDamage, caster); particle(dim, "ed_tide_spray", e.location); }
        break;
      }
    }
  }, tSweep + 10, T4 + 165);
  const tFlare = T4 + 148;
  scene.at(tFlare, () => tide.state(D.attack_c));
  scene.at(tFlare + D_T.flareHit, () => {
    const z = zone();
    const sail = up(z.TL, 8);
    sound(dim, "ed_tide_freeze", z.G, 1.5);
    tide.prop("frost", 1);
    burst(dim, "ed_tide_glint", sail, 2, 5);
    for (const c of currents) { line(dim, "ed_tide_frostline", sail, up(add(z.G, mul(c.dir, c.R)), 1), 6); c.a.state(CUR.freeze); }
    shell = scene.spawn("ed6_iceshell", up(z.G, 0.04), { size: C.ringRadius / RING_R, state: SHELL.grow, yaw: z.yawL });
    sound(dim, "ed6_ice_layers", z.G, 1.5);
    ringA?.skin(RING_SKIN.frost);
    SHELL_LAYERS.forEach((ly, i) => scene.after(ly.t, () => {
      particle(dim, "ed6_frost_layer", up(z.G, 0.3 + i * 0.4));
      ring(dim, "ed_tide_flake", up(z.G, 1.5 + i), ly.r * (C.ringRadius / RING_R), 6, i * 25);
      for (const e of foes(z.G, ly.r * (C.ringRadius / RING_R) + 0.8)) {
        if (frozen.has(e.id)) continue;
        damage(e, C.iceLayerDamage, caster);
        if (!isAlive(e)) continue;
        frozen.set(e.id, restrain(scene, e, Math.max(10, T4 + 222 - scene.tick), { ...e.location }));
        particle(dim, "ed_tide_splinter", up(e.location, 0.8));
      }
    }));
  });
  scene.at(tFlare + D_T.flare, () => tide.state(D.idle));
  scene.at(T4 + 190, () => { shell?.state(SHELL.hold); currents.forEach((c) => c.a.state(CUR.ice)); });

  // ---- 3. Spiraling ice and wind (Air): all four feathered surfaces drive a spiral column
  let spiral: Actor | undefined;
  const HELIX_R = 6.5;
  scene.at(T4 + 168, () => {
    const z = zone();
    const p0 = airBreak(T4 + 168);
    const hs = up(fr.polar(HELIX_R, 180, 0, z.G), 18);
    airMv.path([p0, lerp(p0, hs, 0.5), hs], 16);
    const tPow = airMv.cursor;
    airMv.add(A_T.power, (p) => add(hs, mul(fr.dir(90), 1.5 * p)), { yaw: yawDeg(90) });
    force(tPow, A_T.power, A.power);
    scene.at(tPow, () => {
      air.skin(1);
      sound(dim, "ed_air_call", hs, 1.6);
      ring(dim, "ed_air_spark", hs, 3, 6);
      burst(dim, "ed_air_feather", hs, 2, 4);
    });
    const tHx = airMv.cursor;
    const start = add(hs, mul(fr.dir(90), 1.5));
    const ang0 = 180 + (Math.atan2(1.5, HELIX_R) * 180) / Math.PI;
    const hx = (p: number): V3 => up(fr.polar(HELIX_R, ang0 + 540 * p, 0, z.G), 18 - 4 * Math.sin(p * Math.PI) - 1.5 * p);
    airMv.add(2, (p) => lerp(start, hx(0), p));
    airMv.add(64, (p) => hx(p), { tag: "helix" });
    const back = airMv.last;
    const e1 = circleDegAt(back) + 25;
    airMv.path([back, up(lerp(back, circlePt(e1, 0), 0.5), 3), circlePt(e1, airMv.cursor + 30)], 14);
    airCircle(e1, 4000);
    scene.at(tHx, () => sound(dim, "ed_air_vortex", z.G, 1.4));
  });
  scene.at(T4 + 214, () => {
    const z = zone();
    spiral = scene.spawn("ed6_spiral", up(z.G, 0.05), { size: C.ringRadius / RING_R, state: SPIRAL.form });
    sound(dim, "ed6_spiral", z.G, 1.6);
    scene.after(20, () => spiral?.state(SPIRAL.spin));
  });
  scene.at(T4 + 222, () => {                        // the ice shells shatter into the wind
    const z = zone();
    shell?.state(SHELL.shatter);
    currents.forEach((c) => c.a.state(CUR.shatter));
    for (const rel of frozen.values()) rel();
    frozen.clear();
    sound(dim, "ed_tide_fracture", z.G, 1.4);
    burst(dim, "ed_tide_splinter", up(z.G, 2), 3, 6);
    burst(dim, "ed6_spiral_debris", up(z.G, 3), 2.5, 4);
  });
  scene.at(T4 + 236, () => { if (shell) scene.despawn(shell); currents.forEach((c) => scene.despawn(c.a)); currents.length = 0; });
  const spun = new Map<string, number>();
  scene.every(C.spiralEvery, (el) => {
    const z = zone();
    particle(dim, "ed6_spiral_debris", up(z.G, 2 + ((el / C.spiralEvery) % 4) * 3));
    particle(dim, "ed_air_streak", up(fr.polar(C.ringRadius * 0.7, el * 23, 0, z.G), 4));
    for (const e of foes(z.G, C.ringRadius + 0.5)) {
      const n = spun.get(e.id) ?? 0;
      if (n >= 8) continue;
      spun.set(e.id, n + 1);
      damage(e, C.spiralDamage, caster);
      const v = flat(sub(e.location, z.G));
      const tan = norm({ x: -v.z, y: 0, z: v.x });
      shove(e, add(tan, mul(norm(mul(v, -1)), 0.3)), C.spiralShove, C.spiralLift);
    }
  }, T4 + 224, T4 + 282);
  scene.at(T4 + 282, () => {
    const z = zone();
    for (const e of foes(z.G, C.ringRadius + 0.5)) knockback(e, e.location, 0, C.spiralFinalLift);
    particle(dim, "ed6_updraft", up(z.G, 0.3));
  });
  scene.at(T4 + 300, () => air.skin(0));

  // ---- 4. The Heat Dragon's final charge
  scene.at(T4 + 190, () => {
    const z = zone();
    if (distXZ(heatMv.posAt(T4 + 190), z.SF) > 3) return;
    const lane = scene.spawn("ed_heat_lane", ground(add(z.SF, mul(z.L, 3.5))), { yaw: z.yawL, state: LANE.appear });
    lane.prop("len", clamp(C.finalRunUp + 3, 4, 40));
    sound(dim, "ed_heat_lane", z.SF, 1.2, 0.85);
    scene.after(16, () => lane.state(LANE.armed));
    scene.at(T4 + 250, () => {
      lane.state(LANE.surge).skin(1);
      for (const s of stones) {                     // stones on the lane already glow with the coming heat
        if (s.gone || distToSegment(s.at, z.SF, z.G) > 4) continue;
        s.a.skin(STONE_SKIN.glass).state(STONE.flare);
        s.hotUntil = T4 + 400;
        particle(dim, "ed6_sizzle", up(s.at, 2));
      }
    });
    scene.at(T4 + 320, () => lane.state(LANE.fade));
    scene.at(T4 + 332, () => scene.despawn(lane));
  });
  scene.at(T4 + 226, () => { heat.state(H.roar); sound(dim, "ed6_final_charge", up(zone().SF, 4), 1.6); });
  scene.at(T4 + 236, () => { heat.skin(H_SKIN.whitehot); particle(dim, "fx_flash", up(zone().SF, 4)); ring(dim, "ed_heat_vent", up(zone().SF, 3.5), 3, 6); });
  scene.at(T4 + 256, () => {
    const z = zone();
    heatMv.truncate(T4 + 256);
    heatMv.last = { ...heatMv.posAt(T4 + 255) };
    planYaw = z.yawL;
    const end = hCharge(add(z.G, mul(z.L, 1 + ((H_RUN / 20) * (H_T.skid - 1)) / 2)), { final: true });
    scene.at(end, () => heat.state(H.pant));
    heatMv.hold(T5 + 90 - heatMv.cursor, z.yawL);
  });
  function detonate(): void {
    detonated = true;
    const z = zone();
    const G = z.G;
    spiral?.state(SPIRAL.burst);
    tele?.state(3);
    ringA?.skin(RING_SKIN.glass);
    for (const c of ringCells) tb.removeColumn(c.x, c.y, c.z, C.ringBarrierHeight);
    ringCells.length = 0;
    const bl = scene.spawn("ed6_blast", up(G, 0.05), { size: (C.ringRadius + C.detonationExtra) / 6, state: BLAST.blast });
    sound(dim, "ed6_detonation", G, 2.0);
    particle(dim, "ed6_thermal_ring", up(G, 0.3));
    particle(dim, "fx_flash", up(G, 2));
    burst(dim, "ed6_thermal", up(G, 2), 3, 6);
    burst(dim, "ed6_glass_shard", up(G, 2), 4, 4);
    for (const e of foes(G, C.ringRadius + C.detonationExtra)) {
      damage(e, C.detonationDamage, caster);
      knockback(e, G, C.detonationKnockH, C.detonationKnockV);
      burnT(e, C.detonationBurnSeconds);
    }
    scene.after(4, () => { ringA?.state(RING.burst); sound(dim, "ed_nature_erupt", G, 1.6, 0.8); });
    scene.after(26, () => bl.state(BLAST.hold).skin(1));
    scene.after(50, () => bl.state(BLAST.fade));
    scene.after(72, () => { scene.despawn(bl); if (ringA) scene.despawn(ringA); if (spiral) scene.despawn(spiral); if (tele) scene.despawn(tele); });
  }
  scene.at(T4 + 330, () => { if (!detonated && Z) detonate(); });   // safety: the finale always lands

  // ================================================================================== Phase V: The World Remembers
  const spirits: Actor[] = [];
  function remember(k: number, at: V3, yaw: number, size: number, tForm: number, tStream: number): void {
    scene.at(tForm, () => {
      const s = scene.spawn("ed6_spirit", at, { kind: k, yaw, size, state: SPIRIT.form });
      spirits[k] = s;
      sound(dim, "ed6_inscribe", up(at, 4), 1.3, 0.9 + k * 0.06);
      burst(dim, "ed6_bone_dust", up(at, 3), 3, 5);
      scene.after(24, () => s.state(SPIRIT.hold));
    });
    scene.at(tStream, () => {
      const s = spirits[k];
      if (!s?.valid) return;
      s.state(SPIRIT.stream);
      sound(dim, "ed6_stream", up(at, 3), 1.2);
      const ctl = up(lerp(at, K, 0.5), 10);
      scene.span(scene.tick + 1, scene.tick + 28, (p) => {
        s.move(bezier(up(at, 0), ctl, K, smooth(p)), yaw + 200 * p);
        if (Math.round(p * 27) % 4 === 0) particle(dim, "ed6_inscribe", s.loc);
      });
      scene.after(28, () => {
        codex.state(CODEX.absorb);
        sound(dim, "ed6_absorb", K, 1.2, 0.9 + k * 0.08);
        burst(dim, "ed6_codex_glint", K, 2, 4);
        particle(dim, "ed6_codex_rune", K);
        scene.despawn(s);
      });
    });
  }
  scene.at(T5, () => {
    sound(dim, "ed6_hush", center, 1.4);
    codex.prop("open", 1).state(CODEX.absorb);
    sound(dim, "ed6_codex_open", K, 1.2);
  });
  // Nature lowers its enormous head, then sinks back into the earth as a luminous skeleton
  scene.at(T5, () => { nature.state(N.rest); sound(dim, "ed_nature_moan", up(natMv.posAt(T5), 10), 1.3); });
  scene.at(T5 + 60, () => nature.state(N.depart));
  scene.at(T5 + 60 + N_T.depart, () => scene.despawn(nature));
  remember(0, ground(natMv.posAt(T5)), yN + N_TURN, NATURE.scale, T5 + 64, T5 + 124);
  // Heat closes its vents and lets the heat go
  scene.at(T5, () => {
    heat.state(H.cool).skin(H_SKIN.ignited);
    sound(dim, "ed_heat_cool", up(heatMv.last, 3), 1.3);
    ring(dim, "ed_heat_steam", up(heatMv.last, 3), 2.5, 5);
  });
  scene.at(T5 + 12, () => heat.skin(H_SKIN.cool));
  scene.every(6, () => particle(dim, "ed6_sizzle", up(heatMv.last, 3)), T5, T5 + 60);
  scene.at(T5 + H_T.cool, () => heat.state(H.pant));
  scene.at(T5 + 56, () => heat.state(H.rest));
  scene.at(T5 + 78, () => { heat.state(H.depart); sound(dim, "ed_heat_depart", up(heatMv.posAt(scene.tick), 3), 1.2); });
  scene.at(T5 + 78 + H_T.depart, () => scene.despawn(heat));
  scene.at(T5 + 80, () => remember(1, heatMv.posAt(scene.tick), heatMv.lastYaw, HEAT.scale, scene.tick, T5 + 134));
  // Water & Ice retracts its crystal sail and returns to suspended water
  let massV: Actor | undefined;
  scene.at(T5, () => { tide.prop("frost", 0).skin(0); sound(dim, "ed_tide_sail", up(tideMv.last, 6), 1.0); });
  scene.at(T5 + 6, () => {
    const z = zone();
    massV = scene.spawn("ed_tide_mass", up(z.TL, 9), { state: MASS.gather, size: 1.0 });
    sound(dim, "ed_tide_mass", up(z.TL, 9), 1.2);
  });
  scene.at(T5 + 26, () => massV?.state(MASS.hold));
  scene.at(T5 + 30, () => {
    const z = zone();
    tideMv.truncate(T5 + 30);
    tideMv.path([z.TL, up(add(z.TL, mul(fr.dir(330), 3)), 3), up(z.TL, 9)], D_SWIM * 0.8, { tag: "swim" });
    tideMv.hold(200, z.tideYaw);
    tide.state(D.swim);
  });
  scene.at(T5 + 50, () => { tide.state(D.depart); sound(dim, "ed_tide_depart", up(zone().TL, 9), 1.2); });
  scene.at(T5 + 50 + D_T.depart, () => scene.despawn(tide));
  scene.at(T5 + 54, () => remember(2, up(zone().TL, 9), zone().tideYaw, TIDE.scale, scene.tick, T5 + 116));
  scene.at(T5 + 84, () => massV?.state(MASS.disperse));
  scene.at(T5 + 104, () => { if (massV) scene.despawn(massV); });
  // Air makes a controlled landing and folds away
  const PL = ground(fr.polar(9, 150));
  scene.at(T5 + 4, () => {
    const p0 = airBreak(T5 + 4);
    const dirL = fr.dir(60);
    const app = up(add(PL, mul(dirL, -6)), 3.5);
    airMv.path([p0, up(lerp(p0, app, 0.5), 2), app], 14);
    const tF = airMv.cursor;
    airMv.add(A_T.flare, (p) => lerp(app, up(add(PL, mul(dirL, -1.5)), 1.4), p), { yaw: yawOf(dirL) });
    force(tF, A_T.flare, A.flare);
    const tL = airMv.cursor;
    airMv.add(A_T.land, (p) => lerp(up(add(PL, mul(dirL, -1.5)), 1.4), PL, smooth(p)), { yaw: yawOf(dirL) });
    force(tL, A_T.land, A.land);
    airMv.add(300, () => PL, { yaw: yawOf(dirL), tag: "perch" });
    scene.at(tF, () => sound(dim, "ed_air_flare", app, 1.3));
    scene.at(tL + A_T.land - 2, () => { particle(dim, "fx_dust", PL); sound(dim, "ed_air_land", PL, 1.0); });
    scene.at(tL + A_T.land + 14, () => { force(scene.tick, 400, A.depart); sound(dim, "ed_air_depart", up(PL, 2), 1.3); });
    scene.at(tL + A_T.land + 14 + A_T.depart, () => scene.despawn(air));
    scene.at(tL + A_T.land + 18, () => remember(3, PL, yawOf(dirL), AIR.scale, scene.tick, scene.tick + 46));
  });

  // the ancient world returns to the pages
  scene.at(T5 + 36, () => {
    bridges.forEach((b, i) => scene.after(i * 4, () => { b.state(BRIDGE.shatter); sound(dim, "ed_tide_shatter", b.loc, 0.8); }));
    natStructs.forEach((s) => s.state(STRATA.crumble));
  });
  scene.at(T5 + 56, () => { bridges.forEach((b) => scene.despawn(b)); natStructs.forEach((s) => scene.despawn(s)); });
  scene.at(T5 + 16, () => stones.forEach((s, i) => scene.after(i * 5, () => { if (s.gone) return; s.a.state(STONE.sink); particle(dim, "fx_dust", up(s.at, 0.5)); })));
  scene.at(T5 + 56, () => stones.forEach((s) => scene.despawn(s.a)));
  scene.at(T5 + 70, () => flora.forEach((f, i) => scene.after(i * 4, () => { f.state(FLORA.wither); particle(dim, "ed6_pollen_drift", up(f.loc, 2)); })));
  scene.at(T5 + 130, () => flora.forEach((f) => scene.despawn(f)));
  scene.at(T5 + 110, () => { horizon?.state(HORIZON.sink); sound(dim, "ed6_world_fade", center, 1.4); });
  scene.at(T5 + 120, () => fog?.state(FOG_CLEAR));
  scene.at(T5 + 160, () => { if (horizon) scene.despawn(horizon); if (fog) scene.despawn(fog); level = 0; });
  // the Codex gathers its scales and spine, closes and is gone
  scene.at(T5 + 172, () => {
    codex.prop("sep", 0).prop("open", 0).state(CODEX.hover);
    sound(dim, "ed6_codex_close", K, 1.4);
    burst(dim, "ed6_codex_glint", K, 2.5, 6);
  });
  scene.at(T5 + 206, () => { codex.state(CODEX.vanish); burst(dim, "ed6_codex_rune", K, 2, 5); });
  scene.at(T5 + 238, () => scene.despawn(codex));
  scene.endAt(T5 + 242);
});

/** Smooth path through control points (Catmull-Rom via the motion helper's spline). */
function bezierPath(pts: V3[], p: number): V3 {
  const n = pts.length - 1;
  const f = clamp(p, 0, 1) * n, i = Math.min(n - 1, Math.floor(f)), u = f - i;
  const a = pts[Math.max(0, i - 1)], b = pts[i], c = pts[i + 1], d = pts[Math.min(n, i + 2)];
  const k = (x0: number, x1: number, x2: number, x3: number): number =>
    0.5 * (2 * x1 + (-x0 + x2) * u + (2 * x0 - 5 * x1 + 4 * x2 - x3) * u * u + (-x0 + 3 * x1 - 3 * x2 + x3) * u * u * u);
  return { x: k(a.x, b.x, c.x, d.x), y: k(a.y, b.y, c.y, d.y), z: k(a.z, b.z, c.z, d.z) };
}
