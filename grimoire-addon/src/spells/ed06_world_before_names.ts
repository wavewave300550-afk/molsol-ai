import { Entity } from "@minecraft/server";
import { ED06 as C } from "../config/ed06";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback, restrain, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import {
  V3, add, angleDelta, bezier, clamp, distToSegment, distXZ, dot, easeOut, flat, fromYaw, lerp, mul, norm, right, smooth, sub,
  up, yawOf,
} from "../lib/vec";
import { ArcPath, Frame, Mover, hash01 } from "./_ed06_motion";

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
const N_HEAD = { ahead: 16, up: 12.5 };   // head at rest, relative to the origin (blocks)
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
const D_T = { arrive: 20, land: 16, landHit: 5, sweep: 30, sweepHit: [10, 21], flare: 22, flareHit: 9, power: 30, depart: 32 };
const MASS = { gather: 1, hold: 2, burst: 3, disperse: 4 };
const STREAM = { form: 1, hold: 2, fade: 3 };
const CUR = { form: 1, flow: 2, freeze: 3, spiral: 4, ice: 5, rise: 6, shatter: 7 };
const CUR_R = 4, CUR_SWEEP = 160;
// ---- dragon_air (tools/assets/ed_air.py)
const AIR = { actor: "dragon_air", scale: 1.5 };
const A = { hidden: 0, arrive: 1, idle: 2, move: 3, glide: 4, turn_l: 5, turn_r: 6, roll: 7, stoop: 8, flare: 9, land: 10,
  attack_a: 11, attack_b: 12, power: 13, react: 14, rest: 15, depart: 16, flutter: 17 };
const A_T = { arrive: 48, roll: 20, stoop: 12, land: 20, power: 18, flare: 10, depart: 32 };
const A_BANK = 1.4;          // deg / tick of yaw change that makes the raptor bank
const CLOUD = { form: 1, part: 2, fade: 3 };
// ---- ED06 constructs (tools/assets/ed6_*.py)
const CODEX = { rise: 1, hover: 2, beat: 3, absorb: 4, vanish: 5 };
const EMBLEM = { appear: 1, beat: 2, glow: 3, fade: 4 };
const EMBLEM_C = 34 / 16;    // seal centre height per unit of size (blocks); seal radius = 2 * size
const EMBLEM_DOMAIN = 4;     // kind 4: the caster's flat domain seal (radius 2 * size)
const SPIRIT = { form: 1, hold: 2, stream: 3 };
const FOG_CLEAR = 5;
const HORIZON = { rise: 1, hold: 2, sink: 3 };
const FLORA = { sprout: 1, sway: 2, wither: 3 };
const STONE = { rise: 1, hold: 2, sink: 3, flare: 4 };
const STONE_SKIN = { stone: 0, glass: 1, obsidian: 2 };
const BRIDGE = { form: 1, hold: 2, shatter: 3 };
const BRIDGE_LEN = 12;
const DEBRIS = { lift: 1, orbit: 2, scatter: 3 };
const RING = { rise: 1, hold: 2, quake: 3, burst: 4, sink: 5 };
const RING_SKIN = { frost: 1, glass: 2 };
const RING_R = 6;
const SHELL = { grow: 1, hold: 2, shatter: 3 };
const SHELL_LAYERS = [{ t: 13, r: 2.2 }, { t: 28, r: 3.6 }, { t: 44, r: 5.0 }];
const SPIRAL = { form: 1, spin: 2, burst: 3 };
const BLAST = { blast: 1, hold: 2, fade: 3 };
const LINEAGE = ["nature", "heat", "tide", "air"];

// ================================================================================================
// Timeline (ticks).  I 0-140 heartbeats, II 140-390 arrivals, III 390-630 dominion, IV 630-930 concord
// (the final charge detonates at ~908), V 930-1176 the world remembers (58.8 s).
const BEATS = [44, 70, 96, 122];
const T_ALL = 132;
const T2 = 140, T3 = 390, T4 = 630, T5 = 930;
const T_NATURE = 150, T_HEAT = 206, T_TIDE = 262, T_AIR = 304;
const T_SEAL = T5 + 168;
const T_END = T_SEAL + 78;

// ================================================================================================
// The stage, in blocks relative to the caster: f ahead, r to the right, h up.  Nothing big comes within
// ~10 blocks of the caster; every dragon owns a region of the view so all four read at once:
//   Nature - the far back (a 37-block titan walking side-on along f = 42, its waterfall flank toward the caster)
//   Heat   - the right half (a diagonal charge lane between standing stones, cutting through the hostile zone)
//   Water  - the left half, swimming figure-eights through suspended water 3-6 blocks up
//   Air    - the sky above the back of the stage (an ellipse 14-16 blocks up)
// The Codex hangs in the upper part of the view; the hostile zone (the Concord's target) is the enemy
// group, kept 14-24 blocks ahead.
const ST = {
  codexK1: [27, 0, 7.5], codexK2: [42, -18, 14], codexK3: [22, -1, 8],
  emblems: [[42, -5, 2.2], [30, 17, 1.4], [29, -11, 1.6], [34, 5, 1.5]] as [number, number, number][],
  natureLane: 42, natureFrom: -5,
  heatA: [30, 17], heatB: [21, 9.5],
  stones: [[27.5, 10.8], [23.5, 15.7], [20.6, 13.6]] as [number, number][],
  tideC: [29, -11], tideA: 10, tideB: 5, tideH: 4.5,
  airC: [38, 1], airA: 15, airB: 9, airH: 14,
  groves: [[20, -21, 0], [17, 21, 1], [31, -27, 2], [29, 25, 3], [53, -20, 0], [56, 15, 1], [12, -15, 3], [13, 15, 2]] as
    [number, number, number][],
};

/** Point at (right, forward) blocks from p for a creature facing yaw. */
function local(p: V3, yaw: number, x: number, z: number): V3 {
  const f = fromYaw(yaw);
  return add(add(p, mul(f, z)), mul(right(f), x));
}

/**
 * ED06 - The World Before Names (Extra Ultimate).
 * I   The Four Ancient Heartbeats: the Great Codex rises from the caster's side and hangs over the domain like a
 *     sun; its bronze scales and spine separate and orbit; four heartbeats raise four monumental dragon seals
 *     around the domain while a prehistoric world (horizon, mist, giant ferns, standing stones) grows in.
 * II  The Sovereigns Awaken, one region at a time: the Nature titanosaur rises out of parting strata at the far
 *     back, the horned Heat Dragon charges through a wall of heat shimmer on the right, the sail-backed Tide
 *     Dragon forms in floating water on the left, the four-winged Air Dragon descends through the clouds,
 *     rolls, stoops at the enemies and climbs to circle above everything.
 * III The Primordial Dominion: all four act at once in their own regions - footfall quakes, strata and forest
 *     along the titan's path, roots and pillars at the enemies; charges between the standing stones that
 *     vitrify them; figure-eights through suspended water that freeze into crystalline bridges; wind that
 *     lifts rock, leaves and ice into aerial formations over the battlefield.
 * IV  The Fourfold Concord at the hostile zone: geological shockwave and an enclosing amphitheatre of pillars;
 *     currents that run through it and freeze in layers; a spiral of ice and wind; the Heat Dragon's final
 *     charge and thermal detonation (the climax).
 * V   The World Remembers: the dragons rest, cool, retreat to water and land, turn into luminous skeletons
 *     and inscriptions that stream into the Codex one after another; the Codex seals itself with a flash and
 *     a wave of light that returns the land to normal, then glides back to the caster and is gone.
 */
export default defineSpell("ed06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  // ------------------------------------------------------------------------------------ the stage
  const C0 = { ...caster.location };
  const F = norm(flat(aim.forward));
  const R = right(F);
  const W = new Frame(C0, F, R);
  const gy = (p: V3): number => groundBelow(dim, { x: p.x, y: Math.max(p.y, C0.y) + 8, z: p.z }, 30).y;
  const ground = (p: V3): V3 => ({ x: p.x, y: gy(p), z: p.z });
  /** Ground point of the stage, h blocks above the terrain. */
  const at = (f: number, r: number, h = 0): V3 => up(ground(W.p(f, r)), h);
  /** A point in the air: h above the caster's ground, never closer than 0.75 h to the terrain below. */
  const sky = (f: number, r: number, h: number): V3 => {
    const p = W.p(f, r);
    return { x: p.x, y: Math.max(C0.y + h, gy(p) + h * 0.75), z: p.z };
  };
  const skyA = (v: number[]): V3 => sky(v[0], v[1], v[2]);
  const awayCaster = (p: V3): number => yawOf(flat(sub(p, C0)));
  const faceCaster = (p: V3): number => yawOf(flat(sub(C0, p)));
  const foes = (p: V3, r: number, max?: number): Entity[] => hostiles(dim, p, r, caster, max);
  const tb = blocksFor(scene);
  const burnT = (e: Entity, s: number): void => { try { e.setOnFire(s, true); } catch { /* immune / gone */ } };
  const movers: Mover[] = [];
  scene.every(1, () => { for (const m of movers) m.step(scene.tick); }, 0, T_END);
  const lights: V3[] = [];
  const light = (p: V3, ticks: number): void => {
    if (!tb.place(p, LIGHT)) return;
    lights.push(p);
    scene.after(ticks, () => tb.remove(p));
  };
  /** A streak of particles travelling along an arc from a to b over `ticks` ticks. */
  function stream(a: V3, b: V3, ticks: number, ids: string[], lift = 3, per = 2): void {
    const ctl = up(lerp(a, b, 0.5), lift);
    for (let i = 0; i < ticks; i++) {
      scene.after(i, () => {
        for (let j = 0; j < per; j++) {
          const u = clamp((i + j / per) / Math.max(1, ticks - 1), 0, 1);
          particle(dim, ids[(i + j) % ids.length], bezier(a, ctl, b, smooth(u)));
        }
      });
    }
  }

  // ------------------------------------------------------------------------------------ the hostile zone
  type Zone = { G: V3; L: V3; yawL: number; SF: V3; TL: V3; tideYaw: number; ringYaw: number };
  let Z: Zone | undefined;
  /** Where the enemies are now (clamped into the stage); the Concord freezes it into `zone()`. */
  function zoneNow(): V3 {
    let found: Entity[] = [];
    try { found = foes(focus(caster, aim, C.snap).center, C.zoneGroup + 4); } catch { found = []; }
    if (!found.length) found = foes(at(C.zoneDefault, 0), C.zoneSearch);
    let f = C.zoneDefault, r = 0;
    if (found.length) {
      const s0 = found[0];
      const grp = found.filter((e) => distXZ(e.location, s0.location) <= C.zoneGroup);
      const m = mul(grp.reduce((s, e) => add(s, e.location), { x: 0, y: 0, z: 0 }), 1 / grp.length);
      const rel = sub(m, C0);
      f = dot(rel, F);
      r = dot(rel, R);
    }
    f = clamp(f, C.zoneMinAhead, C.zoneMaxAhead);
    const rm = f * Math.tan((C.zoneMaxDeg * Math.PI) / 180);
    return at(f, clamp(r, -rm, rm));
  }
  function zone(): Zone {
    if (Z) return Z;
    const G = zoneNow();
    const SF = ground(add(add(G, mul(R, C.finalRunUp * 0.82)), mul(F, C.finalRunUp * 0.4)));
    const L = norm(flat(sub(G, SF)));
    // the ring's low (amphitheatre) side is its -X side: turn it so that side faces the caster
    const yawL = yawOf(L);
    const ringYaw = dot(sub(C0, G), right(L)) < 0 ? yawL : yawL + 180;
    // the Water & Ice Dragon settles on the left, behind the ring, its head toward the zone
    const TL = ground(add(add(G, mul(F, 12)), mul(R, -14)));
    Z = { G, L, yawL, SF, TL, tideYaw: yawOf(sub(G, TL)), ringYaw };
    return Z;
  }

  // ================================================================================== Phase I: the Codex
  const K1 = skyA(ST.codexK1), K2 = skyA(ST.codexK2), K3 = skyA(ST.codexK3);
  const BOOK = up(add(add(C0, mul(F, 0.6)), mul(R, 0.45)), 1.15);      // the Grimoire in the caster's hand
  const codex = scene.spawn("ed6_codex", K1, { yaw: awayCaster(K1), state: CODEX.rise, skin: 0 });
  const cxMv = new Mover(codex, K1, awayCaster(K1), 0);
  cxMv.maxTurn = 6;
  let cxFlip = false;                                  // false: its sealed back cover faces the caster
  const cxYaw = (t: number): number => {
    const p = cxMv.posAt(t);
    return cxFlip ? faceCaster(p) : awayCaster(p);
  };
  const drift = (P: V3, amp = 0.45) => (_p: number, t: number): V3 =>
    add(P, { x: amp * Math.sin(t * 0.045), y: 0.3 * Math.sin(t * 0.07 + 1), z: amp * Math.cos(t * 0.045) });
  movers.push(cxMv);
  cxMv.add(T2 - 16, drift(K1), { yaw: cxYaw });
  cxMv.pathIn([K1, sky(34, -8, 11), K2], 54, { ease: smooth, yaw: cxYaw });
  cxMv.add(T5 - cxMv.cursor, drift(K2, 0.8), { yaw: cxYaw });
  const cxAt = (): V3 => cxMv.posAt(scene.tick);
  sound(dim, "ed6_codex_rise", BOOK, 1.0);
  sound(dim, "ed6_codex_rise", K1, 1.6);
  stream(BOOK, up(K1, 2.2), 16, ["ed6_stream", "ed6_codex_rune", "ed6_codex_glint"], 5, 3);   // the book casts its codex up
  scene.every(2, (e) => particle(dim, e % 4 ? "ed6_codex_glint" : "ed6_codex_rune", up(cxAt(), 1.5 + (e % 3))), 10, 50);
  scene.at(28, () => {
    codex.prop("sep", 1);                              // cover scales and vertebrae separate and orbit
    sound(dim, "ed6_codex_unbind", cxAt(), 1.4);
    burst(dim, "ed6_codex_glint", up(cxAt(), 2), 3.5, 8);
    particle(dim, "ed6_ring_v", up(cxAt(), 2.2));
  });
  scene.at(40, () => codex.state(CODEX.hover));
  const codexBeat = (): void => { codex.state(CODEX.beat); scene.after(12, () => codex.state(CODEX.hover)); };
  const cxCore = (): V3 => up(cxAt(), 2.25);

  // ================================================================================== Phase I: heartbeats, seals, the old world
  const EM = ST.emblems.map(([f, r, s]) => ({ at: at(f, r), size: s, c: at(f, r, EMBLEM_C * s) }));
  const emblems: (Actor | undefined)[] = [];
  let level = 0;                                       // atmosphere density 0..4
  let fog: Actor | undefined, horizon: Actor | undefined;
  const flora: { a: Actor; at: V3 }[] = [];
  const stones: { a: Actor; at: V3; hotUntil: number; gone?: boolean }[] = [];

  function sprout(p: V3, kind: number, yaw: number): void {
    const a = scene.spawn("ed6_flora", p, { kind, yaw, state: FLORA.sprout });
    scene.after(40, () => a.state(FLORA.sway));
    flora.push({ a, at: p });
    burst(dim, "ed6_pollen_drift", up(p, 3), 2.5, 3);
    sound(dim, "ed6_sprout", p, 1.0, 0.9 + (kind % 3) * 0.08);
  }
  function atmosphere(k: number): void {
    if (k === 0) {
      const hc = at(18, 0);
      horizon = scene.spawn("ed6_horizon", hc, { yaw: yawOf(F), state: HORIZON.rise });
      scene.after(60, () => horizon?.state(HORIZON.hold));
      fog = scene.spawn("ed6_fog", up(at(16, 0), 0.05), { state: 1 });
      sound(dim, "ed6_world_fade", hc, 1.0, 0.8);
    } else fog?.state(k + 1);
    if (k === 1) {
      ST.stones.forEach(([f, r], i) => scene.after(i * 5, () => {
        const p = at(f, r);
        stones.push({ a: scene.spawn("ed6_stone", p, { yaw: i * 97 + 20, state: STONE.rise, skin: STONE_SKIN.stone }), at: p, hotUntil: 0 });
        const s = stones[stones.length - 1];
        sound(dim, "ed6_stone_rise", p, 1.0, 0.9 + i * 0.05);
        particle(dim, "fx_dust", up(p, 0.5));
        particle(dim, "ed6_trail_nature", up(p, 0.4));
        scene.after(26, () => s.a.state(STONE.hold));
      }));
    }
    for (let j = 0; j < 2; j++) {
      const [f, r, kind] = ST.groves[k * 2 + j];
      scene.after(4 + j * 7, () => sprout(at(f, r), kind, f * 37 + r * 11));
    }
  }

  // the caster stands in the domain seal: a flat circle in the four lineage colours that every heartbeat pulses
  let domain: Actor | undefined;
  scene.at(16, () => {
    domain = scene.spawn("ed6_emblem", ground(C0), { kind: EMBLEM_DOMAIN, size: 2.3, yaw: yawOf(mul(R, -1)), state: EMBLEM.appear });
    scene.after(24, () => domain?.state(EMBLEM.glow));
    particle(dim, "ed6_wave", up(ground(C0), 0.2));
    ring(dim, "ed6_rune_rise", up(ground(C0), 0.2), 4.4, 8);
    sound(dim, "ed6_codex_unbind", up(C0, 1), 0.7, 0.8);
  });
  const domainBeat = (): void => { domain?.state(EMBLEM.beat); scene.after(16, () => domain?.state(EMBLEM.glow)); };

  BEATS.forEach((t, k) => scene.at(t, () => heartbeat(k)));
  function heartbeat(k: number): void {
    const e = EM[k], n = LINEAGE[k];
    level = k + 1;
    const Kc = cxCore();
    sound(dim, `ed6_heart_${n}`, Kc, 1.2);
    sound(dim, `ed6_heart_${n}`, e.c, 1.8);
    codexBeat();
    domainBeat();
    codex.skin(k + 1);                                 // a lineage gem lights on the back cover
    burst(dim, "ed6_codex_glint", Kc, 2.5, 6);
    // the heartbeat travels from the Codex down to its seal, which swings up out of the ground
    stream(Kc, e.c, 9, ["ed6_stream", "ed6_codex_rune"], 4, 3);
    scene.after(8, () => {
      const em = scene.spawn("ed6_emblem", e.at, { kind: k, size: e.size, yaw: faceCaster(e.at), state: EMBLEM.appear });
      emblems[k] = em;
      scene.after(24, () => em.state(EMBLEM.glow));
      particle(dim, `ed6_flash_${n}`, e.c);
      particle(dim, `ed6_beat_${n}`, up(e.at, 0.2));
      ring(dim, `ed6_rise_${n}`, up(e.at, 0.3), e.size * 2.2, 6, k * 30);
      burst(dim, `ed6_burst_${n}`, e.c, 1.5, 4);
      light(up(e.at, 1.5), T4 - scene.tick);
    });
    for (let j = 0; j < k; j++) {                     // the hearts already awake beat with it
      const o = emblems[j];
      if (!o?.valid) continue;
      o.state(EMBLEM.beat);
      scene.after(16, () => o.state(EMBLEM.glow));
      particle(dim, `ed6_beat_${LINEAGE[j]}`, up(EM[j].at, 0.2));
      particle(dim, `ed6_flash_${LINEAGE[j]}`, EM[j].c);
    }
    atmosphere(k);
    const G = zoneNow();                               // the old world's pulse shakes the domain
    particle(dim, "ed6_geo_shock", up(G, 0.2));
    for (const f of foes(G, C.beatRadius)) {
      damage(f, C.beatDamage, caster);
      effect(f, "slowness", C.beatSlowTicks, C.beatSlowAmp);
      knockback(f, G, C.beatKnock, 0.25);
    }
  }
  scene.every(1, (e) => {                              // runes spiral round the Codex while the hearts beat
    const c = cxCore(), a = (e * 23 * Math.PI) / 180, r = 3.2 + 0.6 * Math.sin(e * 0.3);
    particle(dim, e % 3 ? "ed6_stream" : "ed6_codex_rune", add(c, add(mul(R, Math.cos(a) * r), { x: 0, y: Math.sin(a) * r, z: 0 })));
    if (e % 2 === 0) particle(dim, "ed6_codex_glint", add(c, add(mul(R, Math.cos(a + 3.1) * r * 0.8), { x: 0, y: Math.sin(a + 3.1) * r * 0.8, z: 0 })));
  }, 16, T2 + 20);
  // the domain is complete: all four hearts beat as one
  scene.at(T_ALL, () => {
    const Kc = cxCore();
    sound(dim, "ed6_heart_all", Kc, 1.6);
    codexBeat();
    domainBeat();
    particle(dim, "ed6_ring_v", Kc);
    particle(dim, "ed6_wave", up(at(20, 0), 0.3));
    particle(dim, "ed6_wave", up(at(30, 0), 0.3));
    EM.forEach((e, k) => scene.after(k * 2, () => {
      const o = emblems[k];
      if (!o?.valid) return;
      o.state(EMBLEM.beat);
      scene.after(16, () => o.state(EMBLEM.glow));
      particle(dim, `ed6_flash_${LINEAGE[k]}`, e.c);
      particle(dim, `ed6_beat_${LINEAGE[k]}`, up(e.at, 0.2));
      particle(dim, "ed6_column", up(e.at, 0.3));
      ring(dim, `ed6_rise_${LINEAGE[k]}`, up(e.at, 0.3), e.size * 2, 5, k * 20);
      burst(dim, `ed6_burst_${LINEAGE[k]}`, e.c, 1.5, 4);
      line(dim, "ed6_stream", Kc, e.c, 6);
    }));
  });
  function fadeEmblem(k: number): void {
    const e = emblems[k];
    if (!e?.valid) return;
    emblems[k] = undefined;
    e.state(EMBLEM.fade);
    particle(dim, `ed6_beat_${LINEAGE[k]}`, up(EM[k].at, 0.2));
    burst(dim, "ed6_rune_rise", EM[k].c, 2, 4);
    scene.after(26, () => scene.despawn(e));
  }

  // ---------------------------------------------------------------- the living atmosphere: sound bed + ambient layers
  scene.every(100, () => sound(dim, "ed6_ambience", up(at(14, 0), 2), 0.4 + 0.15 * level), BEATS[0], T5 + 120);
  const ZONE_HEAT = { f: 25, r: 13, w: 7, d: 7 }, ZONE_TIDE = { f: 29, r: -11, w: 11, d: 6 }, ZONE_NAT = { f: 42, r: 2, w: 20, d: 6 };
  const inBox = (b: { f: number; r: number; w: number; d: number }, i: number, s: number, h: number): V3 =>
    at(b.f + (hash01(i, s) * 2 - 1) * b.d, b.r + (hash01(i, s + 1) * 2 - 1) * b.w, h);
  let fading = 1;                                      // 1 until the world starts to return to normal
  scene.every(1, (t) => {
    if (level === 0) return;
    const q = (Math.min(4, level) / 4) * fading;      // 0..1 atmosphere density
    const h = (k: number): number => hash01(t, k);
    // foreground (2-9 blocks): spores and golden motes drift past the caster; mist at their feet
    if (h(1) < q) particle(dim, "ed6_spore", at(2.5 + h(2) * 7, (h(3) - 0.5) * 14, 0.4 + h(4) * 1.8));
    if (h(5) < q) particle(dim, t % 3 ? "ed6_mote" : "ed6_pollen_drift", at(3 + h(6) * 7, (h(7) - 0.5) * 14, 0.8 + h(8) * 2.4));
    if (t % 4 === 0 && h(9) < q) particle(dim, "ed6_mist", at(3 + h(10) * 6, (h(11) - 0.5) * 12, 0.15));
    // the stage (9-32 blocks): motes, pollen, rolling low mist
    for (let j = 0; j < 8; j++) {
      if (h(12 + j) < q) particle(dim, j % 3 === 2 ? "ed6_spore" : j % 2 ? "ed6_mote" : "ed6_pollen_drift",
        at(9 + h(70 + j) * 23, (h(80 + j) - 0.5) * 46, 0.8 + h(90 + j) * 6));
    }
    if (t % 2 === 1 && h(35) < q) particle(dim, "ed6_rune_rise", at(10 + h(36) * 30, (h(37) - 0.5) * 40, 0.3));
    if (t % 2 === 0 && h(28) < q) particle(dim, "ed6_mist", at(9 + h(29) * 38, (h(30) - 0.5) * 52, 0.3));
    // the far field (32-55 blocks)
    if (h(31) < 0.8 * q) particle(dim, "ed6_mote", at(32 + h(32) * 22, (h(33) - 0.5) * 60, 2 + h(34) * 10));
    // each region breathes its own element as its seal wakes
    for (let j = 0; j < 4; j++) {
      const k = 40 + j * 10;
      if (level >= 1) particle(dim, (t + j) % 2 ? "ed6_leaf_fall" : "ed_nature_pollen", inBox(ZONE_NAT, t * 2 + j, k, 3 + h(k + 2) * 9));
      if (level >= 2 && h(k + 3) < q) particle(dim, (t + j) % 3 ? "ed6_ember_mote" : "ed6_haze", inBox(ZONE_HEAT, t * 2 + j, k + 4, 0.4 + h(k + 5) * 4));
      if (level >= 3 && h(k + 6) < q) particle(dim, (t + j) % 3 ? "ed6_droplet" : "ed6_snow", inBox(ZONE_TIDE, t * 2 + j, k + 7, 1.5 + h(k + 8) * 7));
    }
    if (level >= 4 && h(60) < q) particle(dim, t % 3 ? "ed6_wind" : "ed6_mote", sky(24 + h(61) * 26, (h(62) - 0.5) * 46, 10 + h(63) * 8));
    // seals breathe runes; the Codex sheds glints and glyphs
    for (let k = 0; k < 4; k++) if (emblems[k]?.valid && (t + k) % 2 === 0) particle(dim, "ed6_rune_rise", up(EM[k].at, 0.5));
    if (t % 2 === 0) particle(dim, t % 6 === 0 ? "ed6_codex_glint" : "ed6_codex_rune", up(cxAt(), 1.2 + h(64) * 2.5));
  }, 0, T_END - 20);

  // ================================================================================== the Nature Dragon
  // Side-on along the far back of the stage, walking toward +R (its right flank and waterfall face the caster).
  const nYaw0 = yawOf(R);
  const nPos = (r: number): V3 => W.p(ST.natureLane, r);
  let nR = ST.natureFrom;
  const N0 = ground(nPos(nR));
  const nature = scene.spawn(NATURE.actor, N0, { yaw: nYaw0, state: N.hidden, skin: N_SKIN.normal });
  const natMv = new Mover(nature, N0, nYaw0, T_NATURE, gy);
  const footprints: V3[] = [];
  let nWalking = false;
  const DR_ = (N_WALK / 20);                           // blocks per tick of walking
  const nWalk = (cycles: number): void => {
    const r0 = nR, from = natMv.cursor, ticks = cycles * N_CYCLE;
    natMv.add(ticks, (p) => nPos(r0 + DR_ * p * ticks), { yaw: nYaw0, tag: "walk" });
    scene.at(from, () => { nature.state(N.move); nWalking = true; });
    for (let c = 0; c < cycles; c++) {
      for (const s of N_STEPS) {
        const tt = from + c * N_CYCLE + s.t;
        const rAt = r0 + DR_ * (c * N_CYCLE + s.t);
        scene.at(tt, () => footfall(ground(local(nPos(rAt), nYaw0, s.x, s.z))));
      }
    }
    nR = r0 + DR_ * ticks;
    scene.at(from + ticks, () => { nature.state(N.idle); nWalking = false; });
  };
  function footfall(p: V3): void {
    footprints.push(p);
    if (footprints.length > 12) footprints.shift();
    const q = scene.spawn("ed_nature_quake", up(p, 0.02), { size: 1.6, state: 1, yaw: (scene.tick * 47) % 360 });
    scene.after(27, () => scene.despawn(q));
    particle(dim, "ed_nature_shock", up(p, 0.15));
    particle(dim, "ed6_trail_nature", up(p, 0.5));
    particle(dim, "ed6_trail_nature", up(p, 1.2));
    particle(dim, "ed_nature_rock", up(p, 0.4));
    sound(dim, "ed_nature_step", p, 1.4);
    for (const e of foes(p, C.stepRadius)) {
      damage(e, C.stepDamage, caster);
      knockback(e, p, C.stepKnockH, C.stepKnockV);
    }
  }
  const nHold = (ticks: number, yaw?: number): void => { natMv.hold(ticks, yaw ?? nYaw0); };
  const nHead = (): V3 => up(local(natMv.posAt(scene.tick), natMv.lastYaw, 0, N_HEAD.ahead), N_HEAD.up);
  const nBack = (): V3 => up(natMv.posAt(scene.tick), 10);

  // Phase II: the strata part, the titanosaur rises neck-first, the forest grows on its back
  const strataI: Actor[] = [];
  scene.at(T_NATURE - 12, () => {
    sound(dim, "ed_nature_rumble", N0, 2.0);
    [[0, 10, 2.0], [6, 3, 1.8], [-6, 3, 1.7], [0, -8, 1.6]].forEach(([x, z, size], k) => scene.after(k * 3, () => {
      const p = ground(local(N0, nYaw0, x, z));
      strataI.push(scene.spawn("ed_nature_strata", p, { yaw: k * 83, size, state: STRATA.rise }));
      burst(dim, "ed6_trail_nature", up(p, 1), 3, 3);
      particle(dim, "ed_nature_rise", p);
      if (k % 2 === 0) sound(dim, "ed_nature_strata", p, 1.5, 0.9 + k * 0.05);
    }));
  });
  scene.at(T_NATURE + 6, () => strataI.forEach((s) => s.state(STRATA.hold)));
  scene.at(T_NATURE, () => {
    nature.state(N.arrive);
    movers.push(natMv);
    sound(dim, "ed_nature_call", up(N0, 10), 2.0);
    particle(dim, "ed6_flash_nature", up(N0, 3));
  });
  scene.at(T_NATURE + 14, () => fadeEmblem(0));
  scene.at(T_NATURE + 18, () => { strataI.forEach((s) => s.state(STRATA.part)); sound(dim, "ed_nature_erupt", N0, 1.6); });
  scene.every(1, (e) => {                              // earth pours off the rising body
    const p = local(N0, nYaw0, (hash01(e, 40) - 0.5) * 10, (hash01(e, 41) - 0.5) * 24);
    particle(dim, "ed6_trail_nature", up(ground(p), 1 + hash01(e, 42) * 5));
    particle(dim, e % 2 ? "ed_nature_rock" : "ed6_leaf_fall", up(ground(p), 2 + hash01(e, 43) * 6));
  }, T_NATURE + 4, T_NATURE + 56);
  scene.at(T_NATURE + N_T.arriveLand, () => {
    for (const x of [-3, 3]) {
      const p = ground(local(N0, nYaw0, x, 5.5));
      footprints.push(p);
      const q = scene.spawn("ed_nature_quake", up(p, 0.02), { size: 2.2, state: 1 });
      scene.after(27, () => scene.despawn(q));
      particle(dim, "ed_nature_shock_big", up(p, 0.2));
      burst(dim, "ed6_trail_nature", up(p, 1), 2.5, 4);
      sound(dim, "ed_nature_quake", p, 1.8);
    }
    particle(dim, "ed6_wave", up(N0, 0.3));
    for (const e of foes(local(N0, nYaw0, 0, 5), C.natureLandRadius)) {
      damage(e, C.natureLandDamage, caster);
      knockback(e, N0, C.stepKnockH * 1.5, C.stepKnockV);
    }
  });
  scene.at(T_NATURE + 70, () => strataI.forEach((s) => s.state(STRATA.crumble)));
  scene.at(T_NATURE + 94, () => strataI.forEach((s) => scene.despawn(s)));
  const tPow = T_NATURE + 66;
  scene.at(tPow, () => { nature.state(N.power); sound(dim, "ed_nature_grow", nBack(), 1.8); });
  scene.at(tPow + 20, () => { nature.skin(N_SKIN.bloom); particle(dim, "ed6_flash_nature", nBack()); });
  scene.every(6, (e) => {
    burst(dim, "ed_nature_leaf", up(nBack(), 1), 5, 3);
    particle(dim, "ed_nature_pollen", up(nBack(), 3));
    particle(dim, "ed6_leaf_fall", local(nBack(), nYaw0, 0, (hash01(e, 44) - 0.5) * 14));
  }, tPow + 10, tPow + 54);
  nHold(tPow + N_T.power - T_NATURE);                 // arrive + power in place
  nWalk(1);                                           // heavy steps along its lane
  nHold(T3 - natMv.cursor);

  // Phase III: strata and living forest along its path; roots run under the ground to the enemies; a neck lash
  const natStructs: Actor[] = [];
  const T3w = natMv.cursor, r3 = nR;
  nWalk(2);
  [0, 1].forEach((c) => scene.at(T3w + c * N_CYCLE + 10, () => {
    const rr = r3 + DR_ * (c * N_CYCLE + 10);
    const p = nPos(rr);
    const out = ground(local(p, nYaw0, -7.5, 3 + c * 4));           // far side of its path: a strata outcrop
    const s = scene.spawn("ed_nature_strata", out, { yaw: c * 97 + 40, size: 1.5, state: STRATA.rise });
    natStructs.push(s);
    scene.after(18, () => s.state(STRATA.hold));
    sound(dim, "ed_nature_strata", out, 1.4, 0.95);
    burst(dim, "ed6_trail_nature", up(out, 1), 3, 3);
    const inn = ground(local(p, nYaw0, 7, -4 + c * 9));             // near side: a living grove
    sprout(inn, c === 0 ? 0 : 3, c * 140 + 30);
    burst(dim, "ed_nature_leaf", up(inn, 2), 2, 3);
  }));
  const tLash = natMv.cursor + 8;
  nHold(8);
  nHold(N_T.attackB);
  scene.at(tLash, () => { nature.state(N.attack_b); sound(dim, "ed_nature_lash", nHead(), 1.6); });
  scene.at(tLash + N_T.attackBHit, () => {
    const p = natMv.posAt(scene.tick);
    const hit = ground(local(p, nYaw0, 3, 12));
    particle(dim, "ed_nature_shock_big", up(hit, 0.2));
    burst(dim, "ed6_trail_nature", up(hit, 1), 3, 4);
    burst(dim, "ed_nature_leaf", up(hit, 2), 3, 3);
    for (const e of foes(hit, C.lashRadius)) { damage(e, C.lashDamage, caster); knockback(e, p, 1.6, 0.5); }
  });
  scene.at(tLash + N_T.attackB, () => nature.state(N.idle));
  nHold(T4 - natMv.cursor);

  // roots run under the ground from its footprints and break out at the enemies; a pillar rises behind each
  type Bind = { e?: Entity; root: Actor; tip: V3; pillar?: Actor; cells?: V3[] };
  const binds: Bind[] = [];
  scene.at(T3 + 26, () => {
    const from = footprints.length ? footprints.slice(-4) : [N0];
    const found = foes(zoneNow(), C.rootRadius, C.maxRoots);
    const goals: { e?: Entity; at: V3 }[] = found.length ? found.map((e) => ({ e, at: { ...e.location } }))
      : [-4, 0, 4].map((r) => ({ at: at(C.zoneDefault + 1, r) }));
    goals.forEach((g, k) => scene.after(k * 4, () => {
      const target = g.e && isAlive(g.e) ? { ...g.e.location } : g.at;
      const fp = from[k % from.length];
      const dirIn = norm(flat(sub(target, fp)));
      const reach = Math.min(9, Math.max(3, distXZ(fp, target)));
      const start = ground(sub(target, mul(dirIn, reach)));
      // the crack runs from the titan's foot toward the enemy, then the root bursts out of it
      const runT = 16;
      for (let i = 0; i <= runT; i += 2) {
        scene.after(i, () => {
          const q = lerp(fp, start, i / runT);
          particle(dim, "ed6_trail_nature", up(ground(q), 0.4));
          if (i % 4 === 0) particle(dim, "ed_nature_rock", up(ground(q), 0.3));
        });
      }
      scene.after(runT, () => {
        const size = clamp(reach / ROOT_LEN, 0.5, 1.6);
        const yaw = yawOf(sub(target, start));
        const tip = ground(add(start, mul(fromYaw(yaw), ROOT_LEN * size)));
        const root = scene.spawn("ed_nature_root", up(start, 0.05), { yaw, size, state: ROOT.grow });
        const b: Bind = { e: g.e, root, tip };
        binds.push(b);
        sound(dim, "ed_nature_root", start, 1.2);
        particle(dim, "ed_nature_shock", up(start, 0.2));
        scene.after(ROOT_BIND - 3, () => {
          particle(dim, "ed_nature_spore", up(tip, 1));
          particle(dim, "ed6_burst_nature", up(tip, 1));
          sound(dim, "ed_nature_bind", tip, 1.2);
          if (b.e && isAlive(b.e)) {
            damage(b.e, C.rootDamage, caster);
            restrain(scene, b.e, C.rootHoldTicks, { x: tip.x, y: Math.max(tip.y, b.e.location.y - 0.5), z: tip.z });
          }
        });
        scene.after(26, () => root.state(ROOT.hold));
        if (k < C.maxPillars) scene.after(30, () => {   // behind the bound enemy (seen from the caster)
          const side = norm(flat(sub(tip, C0)));
          const p = ground(add(tip, mul(side, 2.6)));
          const pil = scene.spawn("ed_nature_pillar", p, { yaw: yawOf(sub(tip, p)), size: 0.72, state: PILLAR.rise });
          b.pillar = pil;
          sound(dim, "ed_nature_pillar", p, 1.2);
          particle(dim, "ed_nature_rise", p);
          particle(dim, "ed_nature_rock", up(p, 1));
          burst(dim, "ed6_trail_nature", up(p, 0.8), 1.5, 2);
          for (const e of foes(p, 1.8)) { damage(e, C.pillarDamage, caster); shove(e, sub(tip, p), 0.7, 0.4); }
          scene.after(8, () => { b.cells = [p]; tb.column(Math.floor(p.x), Math.floor(p.y), Math.floor(p.z), C.pillarBarrierHeight); });
          scene.after(16, () => pil.state(PILLAR.hold));
        });
        scene.after(ROOT_BIND + C.rootHoldTicks, () => { root.state(ROOT.wither); scene.after(22, () => scene.despawn(root)); });
      });
    }));
  });
  scene.at(T4 - 30, () => {                          // the old structures crumble before the Concord
    binds.forEach((b, i) => scene.after(i * 3, () => {
      if (b.cells) for (const c of b.cells) tb.removeColumn(Math.floor(c.x), Math.floor(c.y), Math.floor(c.z), C.pillarBarrierHeight);
      if (b.pillar) { b.pillar.state(PILLAR.crumble); particle(dim, "ed6_trail_nature", up(b.pillar.loc, 1)); const p = b.pillar; scene.after(20, () => scene.despawn(p)); }
    }));
  });

  // ================================================================================== the Heat Dragon
  const HA = at(ST.heatA[0], ST.heatA[1]), HB = at(ST.heatB[0], ST.heatB[1]);
  const dAB = norm(flat(sub(HB, HA)));
  const wallAt = EM[1].at;                             // the Heat seal stands at the head of its lane
  const H1 = ground(sub(wallAt, mul(dAB, 7)));
  const H0 = ground(sub(H1, mul(dAB, (H_WALK / 20) * H_T.arriveWalk)));
  const yawIn = yawOf(dAB);
  const heat = scene.spawn(HEAT.actor, H0, { yaw: yawIn, state: H.hidden, skin: H_SKIN.cool });
  const heatMv = new Mover(heat, H0, yawIn, T_HEAT, gy);
  let planYaw = yawIn;
  let hHits = new Set<string>();
  let hDir: V3 = dAB;
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
    heatMv.segs[heatMv.segs.length - 1].yaw = (t: number) => y0 + d * smooth((t - t0) / ticks);
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
        sound(dim, "ed_heat_lane", from, 1.1);
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
      if (!opts.run) sound(dim, "ed_heat_roar", up(from, 4), 1.6, 1.05);
    });
    scene.at(t0 + n, () => {
      heat.state(H.skid);
      sound(dim, "ed_heat_skid", runEnd, 1.3);
      particle(dim, "ed_heat_skid", up(runEnd, 0.3));
      burst(dim, "ed6_trail_nature", up(runEnd, 0.6), 1.5, 3);
    });
    return tEnd;
  }

  function heatTick(t: number): void {
    const seg = heatMv.segAt(t);
    if (!seg || !seg.tag || seg.tag === "turn") return;
    const pos = heatMv.posAt(t);
    const moving = seg.tag === "charge" || seg.tag === "skid";
    // the standing stones it passes turn to glowing glass
    for (const s of stones) {
      if (hFinal && !s.gone && distXZ(s.at, pos) < 3.6) {     // thermal reaction: the glass stone bursts
        s.gone = true;
        s.a.skin(STONE_SKIN.glass).state(STONE.sink);
        sound(dim, "ed6_vitrify", s.at, 1.6, 0.8);
        burst(dim, "ed6_glass_shard", up(s.at, 2), 1.5, 3);
        particle(dim, "ed6_thermal", up(s.at, 1.5));
        particle(dim, "ed6_flash_heat", up(s.at, 2));
        for (const e of foes(s.at, C.vitrifyRadius)) { damage(e, C.vitrifyDamage, caster); burnT(e, C.burnSeconds); }
      }
      if (s.gone || t < s.hotUntil || distXZ(s.at, pos) > C.vitrifyReach) continue;
      s.hotUntil = t + 130;
      s.a.skin(STONE_SKIN.glass).state(STONE.flare);
      scene.after(10, () => s.a.state(STONE.hold));
      scene.after(120, () => s.a.skin(STONE_SKIN.obsidian));
      sound(dim, "ed6_vitrify", s.at, 1.3);
      particle(dim, "ed6_sizzle", up(s.at, 2));
      particle(dim, "ed6_glass_shard", up(s.at, 2.5));
      particle(dim, "ed6_flash_heat", up(s.at, 2));
      light(up(s.at, 4), 120);
      for (const e of foes(s.at, C.vitrifyRadius)) { damage(e, C.vitrifyDamage, caster); burnT(e, C.burnSeconds); }
    }
    if (!moving) return;
    if (t % 2 === 0) particle(dim, "ed6_trail_heat", up(add(pos, mul(hDir, -2)), 0.4));
    // the ground behind it vitrifies
    const along = dot(sub(pos, hStart), hDir);
    if (seg.tag === "charge" && along >= glassNext) {
      glassNext = along + C.glassEvery;
      const g = scene.spawn("ed_heat_glass", ground(add(pos, mul(right(hDir), (glasses.length % 2 ? 0.8 : -0.8)))),
        { yaw: glasses.length * 67, state: GLASS.appear });
      const rec = { a: g, at: g.loc, born: t };
      glasses.push(rec);
      if (glasses.length % 3 === 1) sound(dim, "ed_heat_glass", rec.at, 1.0);
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
        particle(dim, "ed6_burst_heat", up(e.location, 1.2));
        sound(dim, "ed_heat_hit", e.location, 1.2);
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
  scene.every(20, () => {                              // vitrified ground keeps burning
    for (const g of glasses) {
      if (scene.tick - g.born > 80) continue;
      for (const e of foes(g.at, C.glassBurnRadius)) { damage(e, C.glassBurnDamage, caster); burnT(e, 1); }
    }
  }, T_HEAT, T5);

  // Phase II: it stalks out behind a wall of shimmering heat, its vents open, it charges through the wall
  let wall: Actor | undefined;
  scene.at(T_HEAT - 4, () => {
    fadeEmblem(1);
    wall = scene.spawn("ed_heat_shimmer", wallAt, { yaw: yawIn, state: WALL.form });
    sound(dim, "ed_heat_shimmer", wallAt, 1.5);
    particle(dim, "ed6_flash_heat", up(wallAt, 3));
  });
  scene.every(1, (e) => {
    particle(dim, e % 4 ? "ed6_haze" : "ed_heat_haze", up(add(wallAt, mul(right(dAB), ((e * 7) % 9) - 4)), 0.5 + (e % 4)));
    particle(dim, e % 2 ? "ed6_ember_mote" : "ed6_trail_heat", up(add(wallAt, mul(right(dAB), ((e * 5) % 9) - 4)), 1 + (e % 5)));
  }, T_HEAT - 4, T_HEAT + 76);
  scene.at(T_HEAT, () => { heat.state(H.arrive); movers.push(heatMv); sound(dim, "ed_heat_snarl", up(H0, 3), 1.4); });
  heatMv.add(H_T.arriveWalk, (p) => lerp(H0, H1, p), { yaw: yawIn, tag: "walk" });
  heatMv.hold(H_T.ignite + 6, yawIn);
  const tIgn = T_HEAT + H_T.arriveWalk + 6;
  scene.at(tIgn, () => { heat.state(H.ignite); sound(dim, "ed_heat_ignite", up(H1, 4), 1.6); });
  scene.at(tIgn + 10, () => { heat.skin(H_SKIN.ignited); burst(dim, "ed6_trail_heat", up(H1, 4), 2.4, 5); });
  scene.at(tIgn + H_T.igniteRoar, () => {
    particle(dim, "ed_heat_ring", up(H1, 0.3));
    particle(dim, "ed6_flash_heat", up(H1, 4));
    ring(dim, "ed_heat_vent", up(H1, 3.5), 2.8, 6);
    for (const e of foes(H1, 5)) { damage(e, C.bodyDamage, caster); knockback(e, H1, 0.8, 0.35); }
  });
  const tArrEnd = hCharge(HB, { lane: true });
  const tArrRun = tIgn + H_T.ignite;
  scene.at(tArrRun - 2, () => wall?.state(WALL.part));
  scene.at(tArrRun + 10, () => { heat.skin(H_SKIN.whitehot); particle(dim, "ed6_flash_heat", up(heatMv.posAt(scene.tick), 4)); });
  scene.at(tArrRun + 18, () => wall?.state(WALL.fade));
  scene.at(tArrRun + 34, () => { if (wall) scene.despawn(wall); });
  scene.at(tArrEnd, () => { heat.state(H.pant).skin(H_SKIN.ignited); });
  heatMv.hold(Math.max(1, T3 - 6 - heatMv.cursor));

  // Phase III: charges back and forth along its lane between the standing stones; once, from the near end of the
  // lane, it roars a superheated wave across the ground into the hostile zone
  let atA = false, chords = 0, waved = false;
  function heatPlan(): void {
    if (heatMv.cursor + 80 > T4 + 30) { heatToFinal(); return; }
    if (!atA && chords >= 2 && !waved) { heatWave(); return; }
    const to = atA ? HB : HA;
    const end = hCharge(to);
    atA = !atA;
    chords++;
    scene.at(end, () => { heat.state(H.pant); particle(dim, "ed_heat_steam", up(heatMv.posAt(scene.tick), 3)); });
    heatMv.hold(10);
    scene.at(heatMv.cursor, heatPlan);
  }
  function heatWave(): void {
    waved = true;
    const from = { ...heatMv.last };
    const G = zoneNow();
    const dir = norm(flat(sub(G, from)));
    hTurn(yawOf(dir));
    const tR = heatMv.cursor;
    heatMv.hold(H_T.roar + 6, yawOf(dir));
    scene.at(tR, () => { heat.state(H.roar); sound(dim, "ed_heat_roar", up(from, 4), 1.8, 0.95); });
    const s0 = ground(add(from, mul(dir, 4))), dist = Math.max(4, distXZ(s0, G) + 2);
    const ticks = Math.round((dist / 9) * 20);
    let wave: Actor | undefined;
    const hitW = new Set<string>();
    scene.at(tR + 12, () => {
      sound(dim, "ed_heat_wave", s0, 1.8);
      particle(dim, "ed6_flash_heat", up(from, 4));
      particle(dim, "ed_heat_ring", up(from, 0.3));
      wave = scene.spawn("ed_heat_wave", s0, { yaw: yawOf(dir), state: 1 });
      scene.after(7, () => wave?.state(2));
    });
    scene.span(tR + 13, tR + 13 + ticks, (p, e) => {
      const fp = ground(add(s0, mul(dir, dist * p)));
      wave?.move(fp, yawOf(dir));
      if (e % 2 === 0) particle(dim, "ed_heat_wavefront", up(fp, 1.2));
      if (e % 2 === 1) particle(dim, "ed6_trail_heat", up(fp, 0.8));
      if (e % 3 === 0) particle(dim, "ed6_haze", up(fp, 0.5));
      for (const t of foes(fp, 4.5)) {
        if (hitW.has(t.id)) continue;
        hitW.add(t.id);
        if (damage(t, C.heatWaveDamage, caster)) { shove(t, dir, 0.9, 0.35); burnT(t, C.burnSeconds); }
        particle(dim, "ed_heat_ember", up(t.location, 1));
      }
    });
    scene.at(tR + 13 + ticks, () => {
      wave?.state(3);
      particle(dim, "ed_heat_wavefront", up(G, 1));
      particle(dim, "ed6_burst_heat", up(G, 1.5));
      const w = wave;
      scene.after(12, () => { if (w) scene.despawn(w); });
    });
    scene.at(heatMv.cursor, () => heat.state(H.pant));
    heatMv.hold(8);
    scene.at(heatMv.cursor, heatPlan);
  }
  scene.at(T3 - 6, () => { heatMv.truncate(T3 - 6); planYaw = heatMv.lastYaw; heatPlan(); });

  // ================================================================================== the Water & Ice Dragon
  const TC = sky(ST.tideC[0], ST.tideC[1], ST.tideH);
  const loop = new ArcPath((u) => {
    const a = u * 2 * Math.PI;
    const p = add(TC, add(mul(R, ST.tideA * Math.sin(a)), mul(F, ST.tideB * Math.sin(2 * a))));
    return { x: p.x, y: TC.y + 1.3 * Math.sin(a + 0.6), z: p.z };
  }, 160, true);
  const loopTan = (s: number): number => yawOf(sub(loop.at(s + 0.5), loop.at(s - 0.5)));
  const M0 = loop.at(0);
  const tide = scene.spawn(TIDE.actor, M0, { yaw: loopTan(0), state: D.hidden, skin: 0 });
  const tideMv = new Mover(tide, M0, loopTan(0), T_TIDE);
  tideMv.maxTurn = 12;
  const tSwim = T_TIDE + D_T.arrive;
  tideMv.hold(D_T.arrive, loopTan(0));
  tideMv.add(T4 - tSwim + 200, (_p, t) => loop.at((D_SWIM / 20) * (t - tSwim)), { tag: "swim" });
  const tideS = (t: number): number => (D_SWIM / 20) * Math.max(0, t - tSwim);

  // Phase II: water streams spiral into a floating formation; the dragon forms in it and swims out
  let mass: Actor | undefined;
  const streamsIn: { a: Actor; ang: number; prev: V3 }[] = [];
  scene.at(T_TIDE - 20, () => {
    fadeEmblem(2);
    mass = scene.spawn("ed_tide_mass", M0, { state: MASS.gather, size: 1.2 });
    sound(dim, "ed_tide_mass", M0, 1.6);
    sound(dim, "ed_tide_currents", M0, 1.3);
    for (let k = 0; k < 4; k++) {
      const ang = k * 90 + 20;
      const p0 = up(W.polar(9, ang, 0, M0), -3 + (k % 2) * 2.5);
      streamsIn.push({ a: scene.spawn("ed_tide_stream", p0, { state: STREAM.form, size: 1.3, yaw: yawOf(sub(M0, p0)) }), ang, prev: p0 });
    }
  });
  scene.at(T_TIDE - 12, () => streamsIn.forEach((s) => s.a.state(STREAM.hold)));
  scene.span(T_TIDE - 19, T_TIDE + 4, (p) => {
    const e = smooth(p);
    for (const s of streamsIn) {
      const pos = up(W.polar(9 * (1 - e) + 0.4, s.ang + 200 * e, 0, M0), -3 * (1 - e));
      s.a.move(pos, yawOf(flat(sub(pos, s.prev))));
      s.prev = pos;
      particle(dim, "ed6_trail_tide", pos);
    }
  });
  scene.at(T_TIDE + 2, () => { streamsIn.forEach((s) => s.a.state(STREAM.fade)); burst(dim, "ed_tide_bubble", M0, 3, 5); });
  scene.at(T_TIDE + 8, () => streamsIn.forEach((s) => scene.despawn(s.a)));
  scene.at(T_TIDE + 2, () => mass?.state(MASS.hold));
  scene.at(T_TIDE, () => {
    tide.state(D.arrive);
    movers.push(tideMv);
    sound(dim, "ed_tide_emerge", M0, 1.6);
    particle(dim, "ed6_flash_tide", M0);
  });
  scene.at(tSwim, () => { tide.state(D.swim); burst(dim, "ed_tide_splash", M0, 3, 6); sound(dim, "ed_tide_roar", M0, 1.4); });
  scene.at(tSwim + 40, () => mass?.state(MASS.disperse));
  scene.at(tSwim + 62, () => { if (mass) scene.despawn(mass); mass = undefined; });
  // the dorsal sail crystallises progressively while it swims
  for (let k = 1; k <= 10; k++) scene.at(tSwim + k * 7, () => tide.prop("frost", k / 10));
  scene.at(tSwim + 30, () => { tide.skin(1); sound(dim, "ed_tide_freeze", tideMv.posAt(scene.tick), 1.3, 1.2); });
  // its tail drags the water: two streams follow in its wake
  const wake: Actor[] = [];
  scene.at(tSwim + 20, () => {
    for (const lag of [16, 21]) wake.push(scene.spawn("ed_tide_stream", loop.at(-lag), { state: STREAM.form, size: 1.2 }));
  });
  scene.at(tSwim + 28, () => wake.forEach((w) => w.state(STREAM.hold)));
  scene.every(1, () => {
    const s = tideS(scene.tick);
    [16, 21].forEach((lag, i) => wake[i]?.move(loop.at(s - lag), loopTan(s - lag)));
  }, tSwim + 20, T4 + 40);
  scene.at(T4 + 40, () => wake.forEach((w) => w.state(STREAM.fade)));
  scene.at(T4 + 50, () => wake.forEach((w) => scene.despawn(w)));

  const tideHit = new Map<string, number>();
  scene.every(4, () => {                               // the currents it drags shove enemies along its course
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
  }, tSwim + 10, T4 + 40);

  // Phase III: suspended water at the lobes; crystalline bridges freeze along its course and one reaches the enemies
  const lobes: Actor[] = [];
  scene.at(T3 - 12, () => {
    for (const u of [0.25, 0.75]) {
      const p = up(loop.at(loop.length * u), 0.5);
      lobes.push(scene.spawn("ed_tide_mass", p, { state: MASS.gather, size: 0.8 }));
      sound(dim, "ed_tide_mass", p, 1.2, 1.2);
    }
  });
  scene.at(T3 + 8, () => lobes.forEach((l) => l.state(MASS.hold)));
  scene.at(T4 + 20, () => lobes.forEach((l) => l.state(MASS.disperse)));
  scene.at(T4 + 40, () => lobes.forEach((l) => scene.despawn(l)));
  const bridges: Actor[] = [];
  function bridge(a: V3, b: V3): Actor | undefined {
    const L_ = distXZ(a, b);
    if (L_ < 5) return undefined;
    const br = scene.spawn("ed6_bridge", up(a, 0.1), { yaw: yawOf(sub(b, a)), size: L_ / BRIDGE_LEN, state: BRIDGE.form });
    bridges.push(br);
    sound(dim, "ed6_bridge", lerp(a, b, 0.5), 1.5);
    line(dim, "ed6_snow", up(a, 2), up(b, 2), 5);
    scene.after(26, () => br.state(BRIDGE.hold));
    scene.after(12, () => {
      line(dim, "ed_tide_frostline", up(a, 3), up(b, 3), 6);
      for (const e of foes(lerp(a, b, 0.5), L_ / 2 + C.bridgeWidth)) {
        if (distToSegment(e.location, a, b) > C.bridgeWidth) continue;
        damage(e, C.bridgeDamage, caster);
        effect(e, "slowness", C.bridgeSlowTicks, C.bridgeSlowAmp);
        particle(dim, "ed_tide_splinter", up(e.location, 1));
      }
    });
    return br;
  }
  [T3 + 24, T3 + 150].forEach((t) => scene.at(t, () => {
    const s = tideS(t);
    bridge(ground(loop.at(s - 14)), ground(loop.at(s)));
  }));
  scene.at(T3 + 90, () => {                            // an arch of ice from the edge of its region to the enemies
    const G = zoneNow(), a = at(23, -10);
    const br = bridge(a, ground(add(G, mul(norm(flat(sub(G, a))), 1.5))));
    sound(dim, "ed_tide_roar", tideMv.posAt(scene.tick), 1.6, 1.1);
    if (!br) return;
    scene.at(T4 - 14, () => {                          // it shatters before the Concord takes the zone
      br.state(BRIDGE.shatter);
      sound(dim, "ed_tide_shatter", br.loc, 1.3);
      burst(dim, "ed6_snow", up(lerp(br.loc, G, 0.5), 3), 3, 4);
      burst(dim, "ed_tide_splinter", up(lerp(br.loc, G, 0.5), 3), 3, 3);
    });
    scene.at(T4 + 4, () => { bridges.splice(bridges.indexOf(br), 1); scene.despawn(br); });
  });

  // ================================================================================== the Air Dragon
  const airC = sky(ST.airC[0], ST.airC[1], ST.airH);
  const ellipse = (deg: number, t: number): V3 => {
    const a = (deg * Math.PI) / 180;
    const p = add(airC, add(mul(R, ST.airA * Math.sin(a)), mul(F, ST.airB * Math.cos(a))));
    return { x: p.x, y: airC.y + 1.0 * Math.sin(t * 0.06), z: p.z };
  };
  const ELLIPSE = new ArcPath((u) => ellipse(u * 360, 0), 96, true);
  const OMEGA = ((16 / 20) / ELLIPSE.length) * 360;    // deg of ellipse parameter per tick at ~16 blocks / s
  const ellDegAt = (p: V3): number => {
    const v = sub(p, airC);
    return (Math.atan2(dot(v, R) / ST.airA, dot(v, F) / ST.airB) * 180) / Math.PI;
  };
  const airStart = sky(52, 14, 26);
  const air = scene.spawn(AIR.actor, airStart, { yaw: yawOf(sub(sky(42, 10, 19), airStart)), state: A.hidden });
  const airMv = new Mover(air, airStart, air.yaw, T_AIR);
  airMv.maxTurn = 12;
  const airForce: { from: number; to: number; s: number }[] = [];
  const force = (from: number, ticks: number, s: number): void => { airForce.push({ from, to: from + ticks, s }); };
  let airState: number = A.hidden, airDwell = 0;
  function airOrbit(deg0: number, ticks: number): void {
    const from = airMv.cursor;
    airMv.add(ticks, (_p, t) => ellipse(deg0 + OMEGA * (t - from), t), { tag: "circle" });
  }
  /** Leave the orbit at tick t (it keeps circling until then); returns the position there. */
  function airBreak(t: number): V3 { airMv.truncate(t); return airMv.last; }

  // Phase II: through the clouds, a barrel roll, a stoop at the enemies, a pull-up gust and a climb into its orbit
  const cloudAt = sky(42, 9, 20);
  let clouds: Actor[] = [];
  scene.at(T_AIR - 24, () => {
    clouds = [scene.spawn("ed_air_cloud", cloudAt, { yaw: yawOf(F) + 90, size: 1.5, state: CLOUD.form }),
      scene.spawn("ed_air_cloud", sky(48, -2, 22), { yaw: yawOf(F), size: 1.1, state: CLOUD.form })];
    sound(dim, "ed_air_cloud", cloudAt, 1.8);
    burst(dim, "ed_air_cloud", cloudAt, 6, 6);
  });
  scene.at(T_AIR - 4, () => { clouds.forEach((c) => c.state(CLOUD.part)); fadeEmblem(3); });
  scene.every(1, (e) => {                              // the cloud bank churns where the sky opens
    particle(dim, e % 3 ? "ed6_wind" : "ed_air_cloud", add(cloudAt, { x: (hash01(e, 70) - 0.5) * 12, y: (hash01(e, 71) - 0.5) * 4, z: (hash01(e, 72) - 0.5) * 12 }));
  }, T_AIR - 24, T_AIR + 66);
  scene.at(T_AIR + 66, () => clouds.forEach((c) => c.state(CLOUD.fade)));
  scene.at(T_AIR + 90, () => clouds.forEach((c) => scene.despawn(c)));
  airMv.add(A_T.arrive, (p) => bezier3([airStart, sky(44, 10, 20), sky(38, 14, 16), sky(33, 11, 14)], smooth(p)));
  force(T_AIR, A_T.arrive, A.arrive);
  const tRoll = airMv.cursor;
  airMv.add(A_T.roll, (p) => lerp(sky(33, 11, 14), sky(29, 4, 13), smooth(p)));
  force(tRoll, A_T.roll, A.roll);
  const tGlide = airMv.cursor;
  let tStoop = 0, tFlap = 0;
  scene.at(tGlide - 2, () => {                         // the stoop is aimed at the enemies as they stand now
    const G = zoneNow();
    const rel = sub(G, C0);
    const gf = dot(rel, F), gr = dot(rel, R);
    airMv.truncate(tGlide);
    airMv.path([sky(29, 4, 13), sky(27, gr * 0.6 - 2, 12), sky(gf + 8, gr - 1, 9.5)], 16);
    tStoop = airMv.cursor;
    const s0 = sky(gf + 8, gr - 1, 9.5), s1 = sky(gf + 2.5, gr, 3.2);
    airMv.add(A_T.stoop, (p) => lerp(s0, s1, p * p));
    force(tStoop, A_T.stoop, A.stoop);
    tFlap = airMv.cursor;
    const e0 = ellDegAt(sky(gf + 12, gr + 8, 14)) + 10;
    airMv.path([s1, sky(gf - 1, gr + 4, 5), sky(gf + 4, gr + 9, 9), sky(gf + 12, gr + 8, 13), ellipse(e0, airMv.cursor + 30)], 12);
    force(tFlap, airMv.cursor - tFlap, A.move);
    airOrbit(e0, 4000);
    scene.at(tStoop, () => { sound(dim, "ed_air_dive", s0, 1.8); particle(dim, "ed_air_boom", s0); particle(dim, "ed6_ring_v", s0); });
    scene.at(tFlap, () => {
      const g = ground(s1);
      sound(dim, "ed_air_flare", s1, 1.6);
      particle(dim, "ed_air_shock", up(g, 0.3));
      particle(dim, "ed6_flash_air", up(g, 2));
      burst(dim, "ed_air_gust", up(g, 0.8), 3, 6);
      burst(dim, "ed_air_feather_burst", up(s1, 1), 1.5, 2);
      for (const e of foes(g, C.gustRadius)) { damage(e, C.gustDamage, caster); knockback(e, g, C.gustKnock, 0.45); }
    });
  });
  scene.at(T_AIR, () => {
    air.state(A.arrive); airState = A.arrive; movers.push(airMv);
    sound(dim, "ed_air_call", cloudAt, 2.0);
    particle(dim, "ed6_flash_air", cloudAt);
  });
  scene.at(T_AIR + 30, () => burst(dim, "ed_air_feather", up(airMv.posAt(scene.tick), 1), 2, 4));
  scene.at(tRoll, () => { sound(dim, "ed_air_flap", airMv.posAt(tRoll), 1.5); burst(dim, "ed_air_feather", up(airMv.posAt(tRoll), 1), 1.5, 3); });

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
  }
  scene.every(1, () => airTick(scene.tick), T_AIR + 1, T_END);

  // Phase III: a full-spread beat high over the stage; its wind lifts rock, leaves and ice into aerial formations
  const debris: { a: Actor; at: V3 }[] = [];
  const AH = sky(30, -2, 15);
  scene.at(T3 + 130, () => {
    const p0 = airBreak(T3 + 130);
    airMv.path([p0, lerp(p0, AH, 0.5), AH], 14);
    const tP = airMv.cursor;
    airMv.add(A_T.power + 10, (p) => add(AH, mul(F, -1.2 * smooth(p))), { yaw: yawOf(mul(F, -1)) });
    force(tP, A_T.power + 10, A.power);
    const back = airMv.last;
    const e1 = ellDegAt(back) + 20;
    airMv.path([back, up(lerp(back, ellipse(e1, 0), 0.5), 1.5), ellipse(e1, airMv.cursor + 24)], 14);
    airOrbit(e1, 4000);
    scene.at(tP, () => {
      air.skin(1);
      sound(dim, "ed_air_call", AH, 1.8);
      ring(dim, "ed_air_spark", AH, 4, 6);
      particle(dim, "ed6_flash_air", AH);
      particle(dim, "ed6_ring_v", AH);
    });
    scene.at(tP + 12, () => {
      const G = zoneNow();
      const spots = [G, at(26, -15), at(25, 13)];
      spots.forEach((g, k) => scene.after(k * 6, () => {
        const d = scene.spawn("ed6_debris", g, { yaw: k * 120, size: k === 0 ? 1.0 : 0.85, state: DEBRIS.lift });
        debris.push({ a: d, at: g });
        scene.after(32, () => d.state(DEBRIS.orbit));
        sound(dim, "ed6_debris_lift", g, 1.5, 0.95 + k * 0.05);
        burst(dim, "ed_nature_rock", up(g, 0.5), 2, 3);
        particle(dim, "ed6_updraft", up(g, 0.2));
        stream(AH, up(g, 6), 8, ["ed6_wind", "ed_air_streak"], 2, 1);
      }));
    });
    scene.at(tP + 36, () => air.skin(0));
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
  }, T3 + 170, T4 - 10);
  scene.every(1, (e) => {
    debris.forEach((d, i) => {
      if ((e + i) % 2) return;
      const a = (e * 37 + i * 120) * Math.PI / 180, r = 2.5 + (e % 3);
      particle(dim, e % 3 ? "ed6_spiral_debris" : "ed6_wind", add(up(d.at, 4 + (e % 6)), { x: Math.cos(a) * r, y: 0, z: Math.sin(a) * r }));
    });
  }, T3 + 150, T4 + 6);
  scene.every(2, (e) => {                              // the dominion's set pieces keep breathing
    lobes.forEach((l, i) => { if ((e / 2 + i) % 2 === 0) particle(dim, e % 4 ? "ed6_droplet" : "ed_tide_mist", add(l.loc, { x: 0, y: -1 + (e % 3), z: 0 })); });
    bridges.forEach((b, i) => { if ((e / 2 + i) % 3 === 0) particle(dim, e % 6 ? "ed6_snow" : "ed_tide_glint", up(b.loc, 2 + (e % 4))); });
    glasses.forEach((g, i) => { if ((e / 2 + i) % 4 === 0) particle(dim, (e + i) % 3 ? "ed6_ember_mote" : "ed6_haze", up(g.at, 0.3)); });
    stones.forEach((st, i) => { if (!st.gone && scene.tick < st.hotUntil && (e / 2 + i) % 2 === 0) particle(dim, "ed6_sizzle", up(st.at, 3)); });
  }, T3 - 10, T4 + 40);
  scene.at(T4 + 4, () => {
    debris.forEach((d, i) => scene.after(i * 4, () => {
      d.a.state(DEBRIS.scatter);
      sound(dim, "ed6_debris_fall", d.at, 1.5);
      scene.after(10, () => {
        particle(dim, "ed6_debris_fall", up(d.at, 8));
        particle(dim, "ed6_trail_nature", up(d.at, 0.5));
        for (const e of foes(d.at, C.debrisRadius)) { damage(e, C.debrisDamage, caster); knockback(e, d.at, 0.6, 0.3); }
      });
      scene.after(22, () => scene.despawn(d.a));
    }));
  });

  // ---------------------------------------------------------------- II -> III: the four sovereigns call as one
  scene.at(T3, () => {
    const pts: [Actor, V3, string, string][] = [
      [nature, nHead(), "ed_nature_call", "nature"], [heat, up(heatMv.posAt(scene.tick), 5), "ed_heat_roar", "heat"],
      [tide, up(tideMv.posAt(scene.tick), 4), "ed_tide_roar", "tide"], [air, up(airMv.posAt(scene.tick), 1), "ed_air_call", "air"]];
    pts.forEach(([a, p, snd, n], k) => {
      if (!a.valid) return;
      scene.after(k * 3, () => {
        sound(dim, snd, p, 1.8);
        particle(dim, `ed6_flash_${n}`, p);
        particle(dim, "ed6_ring_v", p);
        burst(dim, `ed6_burst_${n}`, p, 2, 4);
      });
    });
    sound(dim, "ed6_heart_all", cxCore(), 1.6);
    codexBeat();
    particle(dim, "ed6_wave", up(at(24, 0), 0.3));
    particle(dim, "ed6_ring_v", cxCore());
    for (let k = 0; k < 4; k++) stream(cxCore(), pts[k][1], 10, ["ed6_stream", "ed6_codex_rune"], 4, 2);
  });

  // ---------------------------------------------------------------- leylines of the domain
  const DOMAIN_R = 4.6;
  const leyEnd = (k: number, t: number): V3 | undefined => {
    const a = [nature, heat, tide, air][k];
    const arrived = t >= [T_NATURE + 10, T_HEAT + 4, T_TIDE + 4, T_AIR + 30][k];
    if (!arrived) return emblems[k]?.valid ? EM[k].at : undefined;
    if (!a.valid) return undefined;
    const p = [natMv, heatMv, tideMv, airMv][k].posAt(t);
    return ground(p);
  };
  scene.every(1, (t) => {
    if (t >= T5) return;
    for (let k = 0; k < 4; k++) {
      const end = leyEnd(k, t);
      if (!end) continue;
      const concord = t >= T4 + 10;
      const from = concord ? end : add(C0, mul(norm(flat(sub(end, C0))), DOMAIN_R));
      const to = concord ? zone().G : end;
      const u = (((t * 1.5 + k * 9) % 30) / 30);
      const p = lerp(from, to, concord ? u : u * u);
      particle(dim, `ed6_ley_${LINEAGE[k]}`, up(ground(p), 0.25));
    }
  }, BEATS[0] + 8, T5);

  // ---------------------------------------------------------------- living trails: every creature sheds its element
  scene.every(1, (t) => {
    // Nature: dust under its feet as it walks, leaves falling off its back, pollen round the canopy
    if (nature.valid && t >= T_NATURE + 20 && t < T5 + 96) {
      const p = natMv.posAt(t), y = natMv.lastYaw;
      const st = N_STEPS[t % 4];
      particle(dim, nWalking || t % 2 ? "ed6_trail_nature" : "ed_nature_mote", up(ground(local(p, y, st.x * 1.1, st.z)), 0.3));
      particle(dim, t % 3 ? "ed6_leaf_fall" : "ed_nature_leaf", up(local(p, y, (hash01(t, 60) - 0.5) * 5, (hash01(t, 61) - 0.5) * 16), 9 + hash01(t, 62) * 3));
      particle(dim, t % 2 ? "ed_nature_pollen" : "ed6_mote", up(local(p, y, (hash01(t, 65) - 0.5) * 6, (hash01(t, 63) - 0.4) * 14), 10 + hash01(t, 66) * 3));
    }
    // Heat: embers and heat haze stream off its body, the horns blaze
    if (heat.valid && t >= T_HEAT + 4 && t < T5 + 96) {
      const p = heatMv.posAt(t), y = heatMv.lastYaw;
      const pts = [local(up(p, 5.4), y, 0, H_HORN - 1.5), up(p, 5), local(up(p, 4), y, 0, -5)];
      particle(dim, "ed6_trail_heat", pts[t % 3]);
      particle(dim, "ed6_trail_heat", local(up(p, 3 + (t % 3)), y, (hash01(t, 67) - 0.5) * 2.5, (hash01(t, 68) - 0.4) * 12));
      particle(dim, t % 2 ? "ed6_haze" : "ed6_ember_mote", up(p, 1 + (t % 4)));
      particle(dim, "ed6_ember_mote", local(up(p, 1 + (t % 5)), y, (hash01(t, 75) - 0.5) * 4, (hash01(t, 76) - 0.5) * 14));
      if (t % 6 === 0) particle(dim, "ed_heat_horn", local(up(p, 5.6), y, 0, H_HORN - 1));
    }
    // Water & Ice: water streams from its snout, sail and tail; snow sifts from the frozen sail
    if (tide.valid && t >= T_TIDE && t < T5 + 70) {
      const p = tideMv.posAt(t), y = tideMv.lastYaw;
      const pts = [local(up(p, 3), y, 0, 9), up(p, 6.5), local(up(p, 2.5), y, 0, -12)];
      particle(dim, "ed6_trail_tide", pts[t % 3]);
      particle(dim, "ed6_droplet", local(up(p, 3), y, 0, (hash01(t, 64) - 0.5) * 20));
      particle(dim, t % 3 ? "ed6_trail_tide" : "ed6_snow", local(up(p, 5 + (t % 4)), y, 0, (hash01(t, 69) - 0.5) * 8));
      particle(dim, t % 2 ? "ed6_droplet" : "ed_tide_bubble", local(up(p, 1 + (t % 3)), y, (hash01(t, 77) - 0.5) * 3, (hash01(t, 78) - 0.5) * 22));
    }
    // Air: vapour trails from both wingtips while it flies
    if (air.valid && t > T_AIR + 2 && airState !== A.idle && airState !== A.rest && airState !== A.depart) {
      const p = airMv.posAt(t), y = airMv.lastYaw;
      particle(dim, "ed6_trail_air", local(up(p, 0.9), y, 8, -1));
      particle(dim, "ed6_trail_air", local(up(p, 0.9), y, -8, -1));
      particle(dim, t % 9 === 0 ? "ed_air_feather" : t % 2 ? "ed6_wind" : "ed6_trail_air", local(up(p, 1), y, 0, -4 - (t % 5)));
    }
  }, T_NATURE, T_END);

  // ================================================================================== Phase IV: the Fourfold Concord
  // the Heat Dragon's last run takes it to the head of the final lane; it stalks there until its moment
  function heatToFinal(): void {
    const z = zone();
    const from = heatMv.last;
    const mid = ground(lerp(from, z.SF, 0.5));
    const side = norm(flat(sub(z.SF, from)));
    const pts = [from, add(mid, mul(right(side), 3)), z.SF];
    const t0 = heatMv.cursor;
    planYaw = yawOf(side);
    heatMv.path(pts, H_RUN * 0.7, { tag: "run" });
    scene.at(t0, () => heat.state(H.move));
    const tStop = heatMv.cursor;
    heatMv.hold(H_T.skid, yawOf(sub(pts[2], pts[1])), "skidstop");
    scene.at(tStop, () => { heat.state(H.skid); particle(dim, "ed_heat_skid", up(z.SF, 0.3)); });
    planYaw = yawOf(sub(pts[2], pts[1]));
    // pace across the head of the lane like a caged predator, then square up to the zone
    const P = right(z.L);
    const pa = ground(add(z.SF, mul(P, 3.5))), pb = ground(sub(z.SF, mul(P, 3.5)));
    for (const [a, b] of [[z.SF, pa], [pa, pb], [pb, z.SF]] as [V3, V3][]) {
      hTurn(yawOf(sub(b, a)));
      const ts = heatMv.cursor, n = Math.max(6, Math.round((distXZ(a, b) / H_WALK) * 20));
      heatMv.add(n, (p) => lerp(a, b, smooth(p)), { yaw: yawOf(sub(b, a)), tag: "pace" });
      scene.at(ts, () => { heat.state(H.walk); sound(dim, "ed_heat_snort", up(a, 3), 1.2); });
      if (heatMv.cursor > T4 + 190) break;
    }
    hTurn(z.yawL);
    const tWait = heatMv.cursor;
    scene.at(tWait, () => heat.state(H.pant));
    heatMv.hold(Math.max(1, T4 + 238 - heatMv.cursor), z.yawL);
  }

  // ---- the frame of the Concord
  let tele: Actor | undefined;
  let ringA: Actor | undefined;
  const ringCells: V3[] = [];
  scene.at(T4, () => {
    const z = zone();
    tele = scene.spawn("telegraph", up(z.G, 0.05), { kind: 2, size: C.ringRadius + 1, state: 4 });
    sound(dim, "ed6_concord", z.G, 2.0);
    sound(dim, "ed6_heart_all", cxCore(), 1.6);
    codexBeat();
    particle(dim, "ed6_concord", up(z.G, 3));
    particle(dim, "ed6_column", up(z.G, 0.3));
    particle(dim, "ed6_wave", up(z.G, 0.3));
    burst(dim, "ed6_rune_rise", up(z.G, 0.5), 4, 6);
    particle(dim, "ed6_ring_v", cxCore());
    stream(cxCore(), up(z.G, 2), 12, ["ed6_stream", "ed6_codex_rune"], 5, 3);
    light(up(z.G, 2), T5 + 20 - T4);
  });
  scene.at(T4 + 40, () => tele?.state(2));
  scene.every(1, (e) => {                              // the pillars shed earth; frost smokes off the ice
    const z = zone();
    if (e < 12) return;
    const a = e * 53, r = C.ringRadius + 0.3;
    if (e < 150) particle(dim, e % 2 ? "ed6_trail_nature" : "ed_nature_rock", up(W.polar(r, a, 0, z.G), 1 + (e % 4) * 1.5));
    else if (e < 216) particle(dim, e % 2 ? "ed6_snow" : "ed_tide_mist", up(W.polar(r * (0.4 + (e % 3) * 0.25), a, 0, z.G), 0.5 + (e % 4)));
  }, T4, T4 + 300);
  scene.every(1, (e) => {
    const z = zone();
    const step = e < 90 ? "ed_nature_mote" : e < 200 ? "ed6_trail_tide" : e < 236 ? "ed6_wind" : "ed6_trail_heat";
    for (let j = 0; j < 2; j++) {
      const a = e * 9 + j * 180;
      particle(dim, j ? step : "ed6_stream", up(W.polar(C.ringRadius + 0.8, a, 0, z.G), 0.5 + 0.5 * Math.sin(e * 0.2 + j)));
    }
  }, T4 + 4, T4 + 300);

  // ---- 1. Geological shockwaves (Nature): it turns toward the zone, raises the ring, slams the earth
  const yN = nYaw0, N_TURN_DEG = 30, nTurnT = Math.round((N_TURN_DEG / N_TURN) * 20);   // at its documented turn rate
  natMv.hold(nTurnT, undefined);
  natMv.segs[natMv.segs.length - 1].yaw = (t: number) => yN + N_TURN_DEG * smooth((t - T4) / nTurnT);
  nHold(T5 - natMv.cursor, yN + N_TURN_DEG);
  scene.at(T4, () => { nature.state(N.turn_r); sound(dim, "ed_nature_bellow", nHead(), 2.0); });
  scene.at(T4 + nTurnT, () => nature.state(N.idle));
  scene.at(T4 + 12, () => {
    const z = zone();
    ringA = scene.spawn("ed6_ring", z.G, { yaw: z.ringYaw, size: C.ringRadius / RING_R, state: RING.rise });
    sound(dim, "ed6_ring_rise", z.G, 2.0);
    ring(dim, "ed_nature_rise", z.G, C.ringRadius, 8);
    ring(dim, "ed6_trail_nature", up(z.G, 0.6), C.ringRadius, 8, 22);
    particle(dim, "ed6_geo_shock", up(z.G, 0.2));
    for (const e of foes(z.G, C.ringRadius + 1.5)) {
      const d = distXZ(e.location, z.G);
      if (Math.abs(d - C.ringRadius) < 1.6) shove(e, sub(z.G, e.location), 0.9, 0.35);
    }
  });
  scene.at(T4 + 36, () => {
    const z = zone();
    const seen = new Set<string>();
    const n = Math.ceil(2 * Math.PI * C.ringRadius);
    const doorA = yawToFrame(z.yawL), doorB = doorA + 180;
    for (let i = 0; i < n; i++) {
      const a = (i * 360) / n;
      if (Math.abs(angleDelta(a, doorA)) < C.doorwayDeg || Math.abs(angleDelta(a, doorB)) < C.doorwayDeg) continue;
      const p = W.polar(C.ringRadius, a, 0, z.G);
      const c = { x: Math.floor(p.x), y: Math.floor(gy(p)), z: Math.floor(p.z) };
      const key = `${c.x},${c.z}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (tb.column(c.x, c.y, c.z, C.ringBarrierHeight) > 0) ringCells.push(c);
    }
  });
  scene.at(T4 + 44, () => ringA?.state(RING.hold));
  const tSlam = T4 + 20;
  scene.at(tSlam, () => { nature.state(N.attack_a); sound(dim, "ed_nature_rumble", natMv.posAt(tSlam), 1.8, 1.1); });
  scene.at(tSlam + N_T.attackAHit, () => {
    const z = zone();
    const p = ground(natMv.posAt(scene.tick)), y = yN + N_TURN_DEG;
    const SL = ground(local(p, y, N_SLAM.x, N_SLAM.z));
    const q = scene.spawn("ed_nature_quake", up(SL, 0.03), { size: 3.4, state: 1 });
    scene.after(27, () => scene.despawn(q));
    sound(dim, "ed_nature_slam", SL, 2.4);
    particle(dim, "ed_nature_shock_big", up(SL, 0.2));
    particle(dim, "ed6_wave", up(SL, 0.3));
    particle(dim, "ed6_flash_nature", up(SL, 2));
    burst(dim, "ed6_trail_nature", up(SL, 1), 4, 5);
    for (const e of foes(SL, C.slamRadius)) { damage(e, C.slamDamage, caster); knockback(e, SL, 1.2, 0.5); }
    // the shockwave runs through the ground into the ring
    const D_ = distXZ(SL, z.G);
    const steps = Math.max(2, Math.floor((D_ - C.ringRadius) / 3));
    const hit = new Set<string>();
    for (let i = 1; i <= steps; i++) {
      scene.after(i * 2, () => {
        const pt = ground(lerp(SL, z.G, (i * 3) / D_));
        if (i % 2 === 1) {
          const qq = scene.spawn("ed_nature_quake", up(pt, 0.02), { size: 1.5, state: 1, yaw: i * 61 });
          scene.after(27, () => scene.despawn(qq));
        }
        particle(dim, "ed6_geo_shock", up(pt, 0.2));
        particle(dim, "ed6_trail_nature", up(pt, 0.6));
        particle(dim, "ed_nature_rock", up(pt, 0.4));
        if (i % 2) sound(dim, "ed_nature_quake", pt, 1.3, 0.9 + i * 0.04);
        for (const e of foes(pt, C.quakeRadius)) {
          if (hit.has(e.id)) continue;
          hit.add(e.id);
          damage(e, C.quakeDamage, caster);
          knockback(e, pt, 0.4, 0.45);
        }
      });
    }
    // three pulses from the pillars converge on the enclosed zone
    C.shockPulseDamage.forEach((dmg, k) => scene.after(steps * 2 + 3 + k * 10, () => {
      ringA?.state(RING.quake);
      scene.after(10, () => ringA?.state(RING.hold));
      sound(dim, "ed6_geo_shock", z.G, 2.0, 0.9 + k * 0.1);
      particle(dim, "ed6_geo_shock", up(z.G, 0.25));
      particle(dim, "ed_nature_shock_big", up(z.G, 0.3));
      ring(dim, "ed_nature_rock", up(z.G, 0.5), C.ringRadius * 0.8, 6, k * 20);
      ring(dim, "ed6_trail_nature", up(z.G, 0.4), C.ringRadius * 0.9, 6, k * 20 + 30);
      for (const e of foes(z.G, C.ringRadius + 0.5)) {
        damage(e, dmg, caster);
        effect(e, "slowness", C.shockSlowTicks, 1);
        knockback(e, e.location, 0, 0.45);
      }
    }));
  });
  scene.at(tSlam + N_T.attackA, () => nature.state(N.idle));

  // ---- the Tide Dragon leaves its figure-eight and lands beside the ring (behind it, to the left)
  scene.at(T4 + 40, () => {
    const z = zone();
    const cur = tideMv.posAt(T4 + 40), s = tideS(T4 + 40);
    const app = up(local(z.TL, z.tideYaw, 0, -9), 3.5);
    const tan = norm(sub(loop.at(s + 1), loop.at(s - 1)));
    const lead = add(cur, mul(tan, 7));
    const side = add(lerp(lead, app, 0.5), mul(norm(flat(sub(app, z.G))), 6));
    tideMv.truncate(T4 + 40);
    tideMv.path([cur, lead, up(side, 1.5), app, up(local(z.TL, z.tideYaw, 0, -2.5), 2.2), up(z.TL, 1.4)], D_SWIM * 0.8, { tag: "swim" });
    const tLand = tideMv.cursor;
    tideMv.add(D_T.land, (p) => lerp(up(z.TL, 1.4), z.TL, smooth(p)), { yaw: z.tideYaw });
    tideMv.hold(T5 + 40 - tideMv.cursor, z.tideYaw);
    scene.at(tLand, () => { tide.state(D.land); sound(dim, "ed_tide_land", z.TL, 1.6); });
    scene.at(tLand + D_T.landHit, () => {
      ring(dim, "ed_tide_splash", up(z.TL, 0.3), 3, 6);
      particle(dim, "ed_tide_frost_ring", up(z.TL, 0.2));
      particle(dim, "ed6_flash_tide", up(z.TL, 3));
      for (const e of foes(z.TL, 4)) { damage(e, C.currentDamage, caster); knockback(e, z.TL, 0.8, 0.3); }
    });
    scene.at(tLand + D_T.land, () => tide.state(D.idle));
  });

  // ---- 2. Moving water and freezing formations (Water & Ice)
  type Current = { a: Actor; R: number; dir: V3; side: V3; born: number; touched: Set<string> };
  const currents: Current[] = [];
  const frozen = new Map<string, () => void>();
  let shell: Actor | undefined;
  const tSweep = T4 + 104;
  scene.at(tSweep, () => { tide.state(D.attack_a); sound(dim, "ed_tide_sweep", zone().TL, 1.6); });
  D_T.sweepHit.forEach((hh, w) => scene.at(tSweep + hh, () => {
    const z = zone();
    const tail = up(local(z.TL, z.tideYaw, 0, 8), 2);
    let dir = norm(flat(sub(tail, z.G)));
    if (w === 1) dir = mul(dir, -1);
    sound(dim, "ed_tide_flow", tail, 1.5, 0.95 + w * 0.08);
    particle(dim, "ed6_flash_tide", up(tail, 2));
    for (let k = 0; k < 2; k++) {
      const R_ = C.ringRadius * (k === 0 ? 0.78 : 0.5);
      const side = k === 0 ? right(dir) : mul(right(dir), -1);
      const a = scene.spawn("ed_tide_current", z.G, { kind: k, size: R_ / CUR_R, state: CUR.form, yaw: yawOf(dir) });
      currents.push({ a, R: R_, dir, side, born: scene.tick, touched: new Set() });
      stream(up(tail, 1), up(add(z.G, mul(dir, R_)), 1), 8, ["ed6_trail_tide", "ed_tide_spray"], 2, 2);
      scene.after(16, () => a.state(CUR.flow));
    }
  }));
  scene.every(4, () => {                               // the water carries enemies round the ring
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
  }, tSweep + 10, T4 + 160);
  scene.every(2, (e) => {                              // spray rides the currents round the ring
    const z = zone();
    if (!currents.length) return;
    particle(dim, "ed6_trail_tide", up(W.polar(C.ringRadius * 0.7, e * 23, 0, z.G), 0.6));
  }, tSweep + 12, T4 + 166);
  const tFlare = T4 + 142;
  scene.at(tFlare, () => tide.state(D.attack_c));
  scene.at(tFlare + D_T.flareHit, () => {
    const z = zone();
    const sail = up(z.TL, 9);
    sound(dim, "ed_tide_freeze", z.G, 1.8);
    tide.prop("frost", 1);
    burst(dim, "ed_tide_glint", sail, 2, 5);
    particle(dim, "ed6_flash_tide", sail);
    for (const c of currents) { line(dim, "ed_tide_frostline", sail, up(add(z.G, mul(c.dir, c.R)), 1), 6); c.a.state(CUR.freeze); }
    shell = scene.spawn("ed6_iceshell", up(z.G, 0.04), { size: C.ringRadius / RING_R, state: SHELL.grow, yaw: z.ringYaw });
    sound(dim, "ed6_ice_layers", z.G, 1.8);
    ringA?.skin(RING_SKIN.frost);
    SHELL_LAYERS.forEach((ly, i) => scene.after(ly.t, () => {
      particle(dim, "ed6_frost_layer", up(z.G, 0.3 + i * 0.4));
      ring(dim, "ed6_snow", up(z.G, 1.5 + i), ly.r * (C.ringRadius / RING_R), 6, i * 25);
      ring(dim, "ed_tide_glint", up(z.G, 2 + i), ly.r * (C.ringRadius / RING_R), 4, i * 25 + 40);
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
  scene.at(T4 + 186, () => { shell?.state(SHELL.hold); currents.forEach((c) => c.a.state(CUR.ice)); });

  // ---- 3. Spiraling ice and wind (Air): all four feathered surfaces drive a spiral column
  let spiral: Actor | undefined;
  const HELIX_R = 6;
  scene.at(T4 + 168, () => {
    const z = zone();
    const HC = add(z.G, mul(F, 4.5));
    const p0 = airBreak(T4 + 168);
    const hs = up(W.polar(HELIX_R, 0, 0, HC), 11);
    airMv.path([p0, up(lerp(p0, hs, 0.5), 2), hs], 16);
    const tPw = airMv.cursor;
    airMv.add(A_T.power, (p) => add(hs, mul(R, -1.5 * smooth(p))), { yaw: yawOf(mul(R, -1)) });
    force(tPw, A_T.power, A.power);
    scene.at(tPw, () => {
      air.skin(1);
      sound(dim, "ed_air_call", hs, 2.0);
      ring(dim, "ed_air_spark", hs, 3, 6);
      particle(dim, "ed6_flash_air", hs);
      burst(dim, "ed_air_feather", hs, 2, 4);
    });
    const tHx = airMv.cursor;
    const start = add(hs, mul(R, -1.5));
    const ang0 = (Math.atan2(-1.5, HELIX_R) * 180) / Math.PI;
    const hx = (p: number): V3 => up(W.polar(HELIX_R, ang0 - 540 * p, 0, HC), 11 - 5 * Math.sin(p * Math.PI) - 1.5 * p);
    airMv.add(2, (p) => lerp(start, hx(0), p));
    airMv.add(64, (p) => hx(p), { tag: "helix" });
    const back = airMv.last;
    const e1 = ellDegAt(back) + 25;
    airMv.path([back, up(lerp(back, ellipse(e1, 0), 0.5), 3), ellipse(e1, airMv.cursor + 30)], 14);
    airOrbit(e1, 4000);
    scene.at(tHx, () => sound(dim, "ed_air_vortex", z.G, 1.8));
  });
  scene.at(T4 + 206, () => {
    const z = zone();
    spiral = scene.spawn("ed6_spiral", up(z.G, 0.05), { size: C.ringRadius / RING_R, state: SPIRAL.form });
    sound(dim, "ed6_spiral", z.G, 2.0);
    scene.after(20, () => spiral?.state(SPIRAL.spin));
  });
  scene.at(T4 + 216, () => {                           // the ice shells shatter into the wind
    const z = zone();
    shell?.state(SHELL.shatter);
    currents.forEach((c) => c.a.state(CUR.shatter));
    for (const rel of frozen.values()) rel();
    frozen.clear();
    sound(dim, "ed_tide_fracture", z.G, 1.8);
    burst(dim, "ed_tide_splinter", up(z.G, 2), 3, 6);
    burst(dim, "ed6_spiral_debris", up(z.G, 3), 2.5, 4);
    particle(dim, "ed6_flash_tide", up(z.G, 2));
  });
  scene.at(T4 + 230, () => { if (shell) scene.despawn(shell); currents.forEach((c) => scene.despawn(c.a)); currents.length = 0; });
  const spun = new Map<string, number>();
  scene.every(C.spiralEvery, (el) => {
    const z = zone();
    for (const e of foes(z.G, C.ringRadius + 0.5)) {
      const n = spun.get(e.id) ?? 0;
      if (n >= 8) continue;
      spun.set(e.id, n + 1);
      damage(e, C.spiralDamage, caster);
      const v = flat(sub(e.location, z.G));
      const tan = norm({ x: -v.z, y: 0, z: v.x });
      shove(e, add(tan, mul(norm(mul(v, -1)), 0.3)), C.spiralShove, C.spiralLift);
    }
    void el;
  }, T4 + 218, T4 + 276);
  scene.every(1, (e) => {                              // ice, leaves and dust whirl round the column
    const z = zone();
    const a = e * 31, h = 1 + (e % 9) * 1.2;
    particle(dim, e % 3 === 0 ? "ed6_spiral_debris" : e % 3 === 1 ? "ed6_wind" : "ed6_snow",
      up(W.polar(C.ringRadius * (0.5 + 0.08 * (e % 5)), a, 0, z.G), h));
  }, T4 + 210, T4 + 290);
  scene.at(T4 + 276, () => {
    const z = zone();
    for (const e of foes(z.G, C.ringRadius + 0.5)) knockback(e, e.location, 0, C.spiralFinalLift);
    particle(dim, "ed6_updraft", up(z.G, 0.3));
  });
  scene.at(T4 + 300, () => air.skin(0));

  // ---- 4. The Heat Dragon's final charge - the climax
  scene.at(T4 + 204, () => {
    const z = zone();
    if (distXZ(heatMv.posAt(T4 + 204), z.SF) > 4) return;
    const lane = scene.spawn("ed_heat_lane", ground(add(z.SF, mul(z.L, 3.5))), { yaw: z.yawL, state: LANE.appear });
    lane.prop("len", clamp(C.finalRunUp + 4, 4, 40));
    sound(dim, "ed_heat_lane", z.SF, 1.5, 0.85);
    scene.after(16, () => lane.state(LANE.armed));
    scene.at(T4 + 232, () => {
      lane.state(LANE.surge).skin(1);
      for (const s of stones) {                       // stones on the lane already glow with the coming heat
        if (s.gone || distToSegment(s.at, z.SF, z.G) > 4) continue;
        s.a.skin(STONE_SKIN.glass).state(STONE.flare);
        s.hotUntil = T4 + 400;
        particle(dim, "ed6_sizzle", up(s.at, 2));
      }
    });
    scene.at(T4 + 292, () => lane.state(LANE.fade));
    scene.at(T4 + 304, () => scene.despawn(lane));
  });
  scene.at(T4 + 206, () => sound(dim, "ed6_swell", zone().G, 2.0));        // the build-up: 4 s of rising sound
  scene.every(2, (e) => {                              // heat gathers along the lane, embers stream toward the zone
    const z = zone();
    const u = (e * 0.07) % 1;
    particle(dim, e % 4 === 0 ? "ed6_haze" : "ed6_trail_heat", up(lerp(z.SF, z.G, u), 0.4 + (e % 3) * 0.6));
  }, T4 + 210, T4 + 238);
  scene.at(T4 + 210, () => { heat.state(H.roar); sound(dim, "ed6_final_charge", up(zone().SF, 4), 2.0); });
  scene.at(T4 + 226, () => {
    const z = zone();
    heat.skin(H_SKIN.whitehot);
    particle(dim, "ed6_flash_heat", up(z.SF, 4));
    ring(dim, "ed_heat_vent", up(z.SF, 3.5), 3, 8);
    particle(dim, "ed_heat_ring", up(z.SF, 0.3));
    codexBeat();
  });
  scene.at(T4 + 238, () => {
    const z = zone();
    heatMv.truncate(T4 + 238);
    heatMv.last = { ...heatMv.posAt(T4 + 237) };
    planYaw = z.yawL;
    const end = hCharge(add(z.G, mul(z.L, 1 + ((H_RUN / 20) * (H_T.skid - 1)) / 2)), { final: true });
    scene.at(end, () => heat.state(H.pant));
    heatMv.hold(16, z.yawL);
    // follow-through: it stalks back out of the smoking zone and settles side-on behind it
    const E = { ...heatMv.last }, E2 = ground(add(add(z.G, mul(F, 9)), mul(R, 3)));
    const toE2 = yawOf(sub(E2, E));
    hTurn(toE2);
    const tw = heatMv.cursor, nW = Math.max(8, Math.round((distXZ(E, E2) / H_WALK) * 20));
    heatMv.add(nW, (p) => lerp(E, E2, smooth(p)), { yaw: toE2, tag: "walkback" });
    scene.at(tw, () => { heat.state(H.walk); sound(dim, "ed_heat_snort", up(E, 3), 1.4); });
    hTurn(yawOf(mul(R, -1)));
    scene.at(heatMv.cursor, () => heat.state(H.pant));
    heatMv.hold(Math.max(1, T5 + 300 - heatMv.cursor), yawOf(mul(R, -1)));
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
    sound(dim, "ed6_detonation", G, 3.0);
    sound(dim, "ed_heat_roar", up(G, 3), 2.0, 0.8);
    particle(dim, "ed6_thermal_ring", up(G, 0.3));
    particle(dim, "ed6_wave", up(G, 0.4));
    particle(dim, "fx_flash", up(G, 2));
    particle(dim, "ed6_flash_heat", up(G, 3));
    particle(dim, "ed6_ring_v", up(G, 3));
    particle(dim, "ed6_column", up(G, 0.5));
    burst(dim, "ed6_thermal", up(G, 2), 3, 8);
    burst(dim, "ed6_glass_shard", up(G, 2), 4, 5);
    burst(dim, "ed6_burst_heat", up(G, 3), 3, 5);
    ring(dim, "ed6_trail_heat", up(G, 0.6), C.ringRadius, 8);
    ring(dim, "ed6_sizzle", up(G, 0.4), C.ringRadius * 0.7, 5, 20);
    for (let k = 0; k < 4; k++) particle(dim, `ed6_flash_${LINEAGE[k]}`, up(W.polar(C.ringRadius, k * 90 + 45, 0, G), 3));
    for (const e of foes(G, C.ringRadius + C.detonationExtra)) {
      damage(e, C.detonationDamage, caster);
      knockback(e, G, C.detonationKnockH, C.detonationKnockV);
      burnT(e, C.detonationBurnSeconds);
    }
    scene.after(4, () => { ringA?.state(RING.burst); sound(dim, "ed_nature_erupt", G, 2.0, 0.8); burst(dim, "ed6_trail_nature", up(G, 2), 6, 6); });
    scene.after(6, () => { particle(dim, "ed6_thermal_ring", up(G, 0.5)); burst(dim, "ed6_thermal", up(G, 3), 4, 6); });
    for (let i = 0; i < 6; i++) scene.after(8 + i * 5, () => burst(dim, "ed6_smoke", up(G, 2 + i), 3 + i * 0.6, 3));
    scene.after(26, () => bl.state(BLAST.hold).skin(1));
    scene.after(50, () => bl.state(BLAST.fade));
    scene.after(72, () => { scene.despawn(bl); if (ringA) scene.despawn(ringA); if (spiral) scene.despawn(spiral); if (tele) scene.despawn(tele); });
  }
  scene.at(T4 + 292, () => { if (!detonated && Z) detonate(); });   // safety: the finale always lands

  // ================================================================================== Phase V: The World Remembers
  const spirits: Actor[] = [];
  /** A dragon becomes its luminous skeleton; later the skeleton streams into the Codex. */
  function remember(k: number, at_: () => { p: V3; yaw: number }, size: number, tForm: number, tStream: number): void {
    scene.at(tForm, () => {
      const { p, yaw } = at_();
      const s = scene.spawn("ed6_spirit", p, { kind: k, yaw, size, state: SPIRIT.form });
      spirits[k] = s;
      sound(dim, "ed6_inscribe", up(p, 4), 1.6, 0.9 + k * 0.06);
      burst(dim, "ed6_bone_dust", up(p, 3), 3.5, 6);
      particle(dim, `ed6_flash_${LINEAGE[k]}`, up(p, 3));
      scene.after(24, () => s.state(SPIRIT.hold));
    });
    scene.at(tStream, () => {
      const s = spirits[k];
      if (!s?.valid) return;
      const from = { ...s.loc }, yaw = s.yaw;
      s.state(SPIRIT.stream);
      sound(dim, "ed6_stream", up(from, 3), 1.5);
      const ctl = up(lerp(from, K3, 0.5), 9);
      scene.span(scene.tick + 1, scene.tick + 28, (p, e) => {
        const q = bezier(from, ctl, K3, smooth(p));
        s.move(q, yaw + 200 * smooth(p));
        if (e % 2 === 0) particle(dim, "ed6_stream", up(q, 2));
        if (e % 3 === 0) particle(dim, "ed6_inscribe", up(q, 3));
      });
      scene.after(28, () => {
        codex.state(CODEX.absorb);
        sound(dim, "ed6_absorb", K3, 1.6, 0.9 + k * 0.08);
        burst(dim, "ed6_codex_glint", up(K3, 2), 2.5, 5);
        particle(dim, `ed6_flash_${LINEAGE[k]}`, up(K3, 2.2));
        particle(dim, "ed6_ring_v", up(K3, 2.2));
        scene.despawn(s);
      });
    });
  }
  scene.every(1, (e) => {
    for (let k = 0; k < 4; k++) {
      const sp = spirits[k];
      if (!sp?.valid || (e + k) % 2) continue;
      const len_ = [30, 14, 22, 12][k];
      particle(dim, (e >> 1) % 2 ? "ed6_bone_dust" : "ed6_inscribe",
        local(up(sp.loc, 2 + hash01(e, 90 + k) * 5), sp.yaw, (hash01(e, 94 + k) - 0.5) * 3, (hash01(e, 98 + k) - 0.5) * len_));
    }
  }, T5 + 40, T_SEAL);
  scene.at(T5 + 2, () => {
    particle(dim, "ed6_ring_v", cxCore());
    particle(dim, "ed6_light_wave", up(zone().G, 0.3));
    burst(dim, "ed6_codex_glint", cxCore(), 3, 6);
    codexBeat();
  });
  scene.at(T5, () => {
    sound(dim, "ed6_hush", up(at(16, 0), 2), 2.0);
    cxMv.truncate(T5);
    cxFlip = true;                                     // it turns its pages toward the caster
    cxMv.pathIn([cxMv.last, sky(32, -10, 10.5), K3], 40, { ease: smooth, yaw: cxYaw });
    cxMv.add(T_END - cxMv.cursor, drift(K3, 0.25), { yaw: cxYaw });
    codex.prop("open", 1);
    sound(dim, "ed6_codex_open", K3, 1.6);
  });
  scene.at(T5 + 40, () => codex.state(CODEX.absorb));
  // Air: a controlled landing on the right of the stage, wings folded, then it becomes inscription
  const PL = at(26, 15);
  scene.at(T5 + 2, () => {
    const p0 = airBreak(T5 + 2);
    const dirL = mul(R, -1);
    const app = up(add(PL, mul(dirL, -7)), 3.5);
    airMv.path([p0, up(lerp(p0, app, 0.5), 2), app], 14);
    const tF = airMv.cursor;
    airMv.add(A_T.flare, (p) => lerp(app, up(add(PL, mul(dirL, -1.5)), 1.4), easeOut(p)), { yaw: yawOf(dirL) });
    force(tF, A_T.flare, A.flare);
    const tL = airMv.cursor;
    airMv.add(A_T.land, (p) => lerp(up(add(PL, mul(dirL, -1.5)), 1.4), PL, smooth(p)), { yaw: yawOf(dirL) });
    force(tL, A_T.land, A.land);
    airMv.add(400, () => PL, { yaw: yawOf(dirL), tag: "perch" });
    scene.at(tF, () => sound(dim, "ed_air_flare", app, 1.6));
    scene.at(tL + A_T.land - 2, () => { particle(dim, "fx_dust", PL); particle(dim, "ed_air_shock", up(PL, 0.2)); sound(dim, "ed_air_land", PL, 1.3); });
    scene.at(tL + A_T.land + 8, () => { force(scene.tick, 400, A.rest); });
    const tD = Math.max(tL + A_T.land + 20, T5 + 56);
    scene.at(tD, () => { force(scene.tick, 400, A.depart); sound(dim, "ed_air_depart", up(PL, 2), 1.6); burst(dim, "ed_air_feather_burst", up(PL, 1.5), 2, 3); });
    scene.at(tD + A_T.depart, () => scene.despawn(air));
    remember(3, () => ({ p: PL, yaw: yawOf(dirL) }), AIR.scale, tD + 4, Math.max(T5 + 82, tD + 30));
  });
  // Water & Ice: retracts its crystal sail, rises into suspended water and dissolves into it
  let massV: Actor | undefined;
  scene.at(T5, () => { tide.prop("frost", 0).skin(0); sound(dim, "ed_tide_sail", up(tideMv.last, 6), 1.3); tide.state(D.rest); });
  scene.at(T5 + 10, () => {
    const z = zone();
    massV = scene.spawn("ed_tide_mass", up(z.TL, 6.5), { state: MASS.gather, size: 1.0 });
    sound(dim, "ed_tide_mass", up(z.TL, 6.5), 1.5);
  });
  scene.at(T5 + 30, () => massV?.state(MASS.hold));
  scene.at(T5 + 40, () => {
    const z = zone();
    tideMv.truncate(T5 + 40);
    tideMv.pathIn([z.TL, up(z.TL, 3), up(z.TL, 6.5)], 24, { tag: "swim", ease: smooth, yaw: z.tideYaw });
    tideMv.hold(300, z.tideYaw);
    tide.state(D.swim);
  });
  scene.at(T5 + 64, () => { tide.state(D.depart); sound(dim, "ed_tide_depart", up(zone().TL, 6.5), 1.6); });
  scene.at(T5 + 64 + D_T.depart, () => scene.despawn(tide));
  remember(2, () => ({ p: up(zone().TL, 6.5), yaw: zone().tideYaw }), TIDE.scale, T5 + 68, T5 + 100);
  scene.at(T5 + 112, () => massV?.state(MASS.disperse));
  scene.at(T5 + 134, () => { if (massV) scene.despawn(massV); });
  // Heat: closes its vents, lets the heat go in a long plume of steam, settles, becomes inscription
  scene.at(T5 + 22, () => {
    heat.state(H.cool).skin(H_SKIN.ignited);
    sound(dim, "ed_heat_cool", up(heatMv.last, 3), 1.6);
    ring(dim, "ed_heat_steam", up(heatMv.last, 3), 2.5, 6);
  });
  scene.at(T5 + 34, () => heat.skin(H_SKIN.cool));
  scene.every(4, (e) => particle(dim, e % 8 ? "ed6_sizzle" : "ed_heat_steam", up(heatMv.posAt(scene.tick), 3 + (e % 3))), T5 + 22, T5 + 84);
  scene.at(T5 + 22 + H_T.cool, () => heat.state(H.pant));
  scene.at(T5 + 60, () => heat.state(H.rest));
  scene.at(T5 + 84, () => { heat.state(H.depart); sound(dim, "ed_heat_depart", up(heatMv.posAt(scene.tick), 3), 1.5); });
  scene.at(T5 + 84 + H_T.depart, () => scene.despawn(heat));
  remember(1, () => ({ p: heatMv.posAt(scene.tick), yaw: heatMv.lastYaw }), HEAT.scale, T5 + 88, T5 + 118);
  // Nature: lowers its enormous head, then sinks back into the earth while its skeleton rises out of it
  scene.at(T5, () => { nature.state(N.rest); sound(dim, "ed_nature_moan", nHead(), 1.8); });
  scene.at(T5 + 92, () => nature.state(N.depart));
  scene.at(T5 + 92 + N_T.depart, () => scene.despawn(nature));
  remember(0, () => ({ p: ground(natMv.posAt(scene.tick)), yaw: natMv.lastYaw }), NATURE.scale, T5 + 96, T5 + 136);
  scene.every(3, (e) => {                              // inscription light pours off the dissolving titan
    const p = natMv.posAt(scene.tick);
    particle(dim, e % 2 ? "ed6_bone_dust" : "ed6_rune_rise", local(up(p, 3 + (e % 4) * 2), natMv.lastYaw, (hash01(e, 50) - 0.5) * 6,
      (hash01(e, 51) - 0.5) * 28));
  }, T5 + 92, T5 + 140);

  // the Codex seals itself: the four inscriptions are home (the peak of the ending)
  scene.at(T_SEAL - 26, () => sound(dim, "ed6_swell", K3, 1.2, 1.3));
  scene.every(2, (e) => {                              // the pages draw the last light in
    const a = e * 47, r = 6 - (e % 6) * 0.8;
    particle(dim, e % 3 ? "ed6_stream" : "ed6_codex_rune", add(up(K3, 2.2), { x: Math.cos((a * Math.PI) / 180) * r, y: (e % 5) - 2, z: Math.sin((a * Math.PI) / 180) * r }));
  }, T_SEAL - 24, T_SEAL);
  scene.at(T_SEAL, () => {
    codex.prop("sep", 0).prop("open", 0).state(CODEX.beat);
    scene.after(12, () => codex.state(CODEX.hover));
    codex.skin(4);
    const Kc = up(K3, 2.2);
    sound(dim, "ed6_seal", Kc, 2.4);
    sound(dim, "ed6_codex_close", Kc, 1.8);
    particle(dim, "fx_flash", Kc);
    particle(dim, "ed6_ring_v", Kc);
    particle(dim, "ed6_column", ground(K3));
    burst(dim, "ed6_seal", Kc, 1.0, 3);
    burst(dim, "ed6_codex_glint", Kc, 3, 6);
    for (let k = 0; k < 4; k++) particle(dim, `ed6_flash_${LINEAGE[k]}`, add(Kc, mul(W.dir(k * 90 + 45), 1.6)));
    light(up(K3, 0.5), 60);
  });
  // a wave of light runs out over the land and everything of the old world goes back to sleep behind it
  const restoreAt = (p: V3): number => T_SEAL + 6 + Math.round(distXZ(p, ground(K3)) * 0.9);
  scene.at(T_SEAL + 4, () => {
    sound(dim, "ed6_restore", up(ground(K3), 2), 2.2);
    sound(dim, "ed6_world_fade", up(at(16, 0), 2), 1.8);
    particle(dim, "ed6_light_wave", up(ground(K3), 0.3));
    particle(dim, "ed6_wave", up(ground(K3), 0.4));
  });
  scene.at(T_SEAL + 16, () => particle(dim, "ed6_light_wave", up(ground(K3), 0.3)));
  scene.at(T_SEAL + 4, () => {
    fading = 0.6;
    for (const b of bridges) scene.at(restoreAt(b.loc), () => { b.state(BRIDGE.shatter); sound(dim, "ed_tide_shatter", b.loc, 1.0); burst(dim, "ed6_snow", up(b.loc, 2), 2, 3); });
    for (const s of natStructs) scene.at(restoreAt(s.loc), () => { s.state(STRATA.crumble); particle(dim, "ed6_trail_nature", up(s.loc, 1)); });
    for (const s of stones) scene.at(restoreAt(s.at), () => {
      if (!s.gone) { s.a.state(STONE.sink); particle(dim, "fx_dust", up(s.at, 0.5)); particle(dim, "ed6_rune_rise", up(s.at, 1)); }
    });
    for (const f of flora) scene.at(restoreAt(f.at), () => { f.a.state(FLORA.wither); burst(dim, "ed6_pollen_drift", up(f.at, 2), 2, 2); particle(dim, "ed6_mote", up(f.at, 3)); });
    for (const g of glasses) scene.at(restoreAt(g.at), () => g.a.state(GLASS.fade));
  });
  scene.at(T_SEAL + 26, () => { fading = 0.3; fog?.state(FOG_CLEAR); horizon?.state(HORIZON.sink); });
  scene.at(T_SEAL + 40, () => { domain?.state(EMBLEM.fade); burst(dim, "ed6_rune_rise", up(ground(C0), 0.4), 5, 6); });
  scene.at(T_SEAL + 66, () => { if (domain) scene.despawn(domain); });
  scene.at(T_SEAL + 50, () => { fading = 0.12; });
  scene.at(T_SEAL + 58, () => {
    for (const b of bridges) scene.despawn(b);
    for (const s of natStructs) scene.despawn(s);
    for (const s of stones) scene.despawn(s.a);
    for (const f of flora) scene.despawn(f.a);
  });
  scene.at(T_SEAL + 76, () => { if (horizon) scene.despawn(horizon); if (fog) scene.despawn(fog); });
  // the sealed Codex turns its back cover to the caster again, folds into a mote, and the mote flies home into the book
  scene.at(T_SEAL + 30, () => { cxFlip = false; });
  scene.every(2, (e) => particle(dim, e % 4 ? "ed6_stream" : "ed6_codex_rune", up(cxMv.posAt(scene.tick), 1.6 + (e % 3))), T_SEAL + 20, T_SEAL + 62);
  scene.at(T_SEAL + 44, () => { codex.state(CODEX.vanish); sound(dim, "ed6_absorb", cxAt(), 1.6, 0.8); });
  scene.at(T_SEAL + 62, () => {
    const p = up(cxAt(), 3.2);
    burst(dim, "ed6_codex_glint", p, 1.5, 6);
    particle(dim, "ed6_ring_v", p);
    stream(p, BOOK, 14, ["ed6_stream", "ed6_inscribe", "ed6_codex_glint"], 4, 3);
    sound(dim, "ed6_codex_close", p, 1.6, 1.3);
  });
  scene.at(T_SEAL + 76, () => { sound(dim, "ed6_absorb", BOOK, 0.9, 1.2); burst(dim, "ed6_codex_glint", BOOK, 0.4, 3); });
  scene.at(T_SEAL + 70, () => scene.despawn(codex));
  scene.onEnd(() => { for (const p of lights) tb.remove(p); });
  scene.endAt(T_END);

  /** Frame angle (deg, 0 = F, 90 = R) of a Minecraft yaw. */
  function yawToFrame(yaw: number): number {
    const d = fromYaw(yaw);
    return (Math.atan2(dot(d, R), dot(d, F)) * 180) / Math.PI;
  }
});

/** Smooth path through control points (Catmull-Rom). */
function bezier3(pts: V3[], p: number): V3 {
  const n = pts.length - 1;
  const f = clamp(p, 0, 1) * n, i = Math.min(n - 1, Math.floor(f)), u = f - i;
  const a = pts[Math.max(0, i - 1)], b = pts[i], c = pts[i + 1], d = pts[Math.min(n, i + 2)];
  const k = (x0: number, x1: number, x2: number, x3: number): number =>
    0.5 * (2 * x1 + (-x0 + x2) * u + (2 * x0 - 5 * x1 + 4 * x2 - x3) * u * u + (-x0 + 3 * x1 - 3 * x2 + x3) * u * u * u);
  return { x: k(a.x, b.x, c.x, d.x), y: k(a.y, b.y, c.y, d.y), z: k(a.z, b.z, c.z, d.z) };
}
