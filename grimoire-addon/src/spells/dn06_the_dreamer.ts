import { Entity, Vector3 } from "@minecraft/server";
import { DN06 as C } from "../config/dn06";
import { defineSpell } from "../core/registry";
import { addWard, damage, drag, effect, heal, knockback, removeWard, restrain, shove, Ward } from "../lib/combat";
import { particle, sound } from "../lib/fx";
import { Actor } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import {
  add, angleDelta, bezier, clamp, distXZ, easeIn, easeOut, fromYaw, lerp, mul, norm, right, smooth, spline, sub, up, yawOf,
} from "../lib/vec";

// ---- animation states (tools/assets/dn_dreamer*.py) -------------------------------------------
const DS = { hidden: 0, manifest: 1, sit: 2, awaken: 3, rise: 4, hover: 5, sweep: 6, cabinet: 7, raise: 8, conjure: 9,
  conduct: 10, fireArms: 11, fireRooms: 12, finale: 13, slam: 14, forget: 15 };
const BED = { arrive: 1, float: 2, occupied: 3, dip: 4, empty: 5, fold: 6, swing: 7, vanish: 8, rest: 9, hang: 10 };
const CODEX = { open: 1, hold: 2, gather: 3, close: 4 };
const ZONE = { bloom: 1, idle: 2, fold: 3, fade: 4, bite: 5 };
const LAMP = { rise: 1, hold: 2, sink: 3 };
const TG = { warn: 1, hold: 2, flash: 3, warnSlow: 4 };

// ---- animation lengths (ticks) and geometry probes (dn_dreamer.py LEN / report(); blocks) -------
const LEN = { manifest: 72, sit: 52, awaken: 30, rise: 60, sweep: 60, cabinet: 40, raise: 40, fireArms: 32,
  fireRooms: 32, finale: 60, slam: 28, forget: 110 };
type RUF = [number, number, number];          // [right, up, forward] from the Dreamer's hips, in its own facing
/** The hips float this high above the stage while the blanket-gown pools on the ground round them. */
const HOVER_LIFT = 0.5;
/** Fingertip while the hand rakes the ground (sweep 1.25 s .. 2.0 s, five even steps). */
const SWEEP_PATH: RUF[] = [[12.99, -0.38, 8.99], [8.46, -0.66, 13.33], [2.73, -0.17, 15.62], [-3.17, -1.06, 14.56],
  [-8.2, -1.17, 11.35]];
const SWEEP_HIT = [25, 40];
const CHEST: RUF = [0, 4.9, 2.4];           // cabinet front (rooms, stairs)
const DOOR: RUF = [0, 9.37, 2.86];          // face-door at rest
const DOOR_FIN: RUF = [0, 7.89, 5.89];      // face-door while it pours out the other world
const BEAM_LAND = 17.17;                    // where the beam meets the ground (forward)
const ARM: RUF = [2.8, 3.29, 9.16];         // forearm arcades at the thrust (mirror for the left)
const PALM_R: RUF = [9.21, 9.34, 3.11];     // dream hand raised
const PALM_L: RUF = [-9.35, 8.97, 2.9];     // nightmare hand raised
const HAND_SLAM: RUF = [2.45, -1.47, 13.31]; // fingertips at the final blow (mirror for the left)
const LIE = { feet: 4.27, crown: 6.63 };    // the sleeper in the bed: feet / crown from its hips (blocks)
// bed (dn_dreamer_bed.py): it turns about the sleeper's hips; its pillow sits up the tilted mattress
const BED_SCALE = 1.4;
const PIVOT = { up: (7.4 * BED_SCALE) / 16, fwd: (11.4 * BED_SCALE) / 16 };
const PILLOW = { r: 22, y: -7.4, z: 63.4 };   // units, from the pivot
const TILT_A = 40;
const SWING_T = 48;                          // dn_dreamer_bed.py SWING_T (2.4 s)
const SWING_A = 58;
const DIP: [number, number][] = [[0, 0], [7, -5], [16, -3], [28, -4.5], [44, -4]];   // bed "dip" root height (ticks, units)
const STEP_LAND = (k: number): number => 8 + Math.round(k * 2.4);   // stairs (dn_dreamer_zones.py): tick each step lands
const STEP = (k: number): number => 0.625 + k * 1.25;               // ... and how far along the spill it lies
const BOOK: RUF = [-1.28, 0.46, 2.19];       // the open codex, from the caster's feet along its facing
const LAMPS = 8;

/**
 * DN06 - The Dreamer Who Never Wakes (Extra Ultimate, ~55 s).  Staged for the caster's own eyes: the bed hangs high
 * and far in the view, the Dreamer stands 34+ blocks ahead in a pool of its own blanket so the whole figure fits the
 * first-person view, strikes land 9-18 blocks ahead, and nothing tall comes nearer the caster than C.clearZone.
 * I  The Bed Above the Sky   - the domain and its lamps rise, the Codex opens low beside the caster and its pages
 *                               unfold into little doors and stairs circling at knee height; the bed drifts in;
 *                               enemies are marked one by one.
 * II The Sleeper Rises       - the Dreamer manifests in the tilted bed section by section, sits up (the bed levels and a
 *                               pillow drops on an enemy), glides down into its pool at full size, turns its head and
 *                               opens its face-door, rakes the ground and spills stairs from its chest.
 * III Dream / Nightmare Zones - both hands rise: dream gardens bloom round the caster and allies, nightmare rooms
 *                               swallow the enemy groups; both run at once.
 * IV The Great Unreality     - zones and bed fold into formations: wheel of doors, window shards, stair drill, bed
 *                               pendulum, room-cubes; finale: light gathers, it bows, the face-door pours its world out
 *                               and slams (the peak), the field settles.
 * V  The Forgotten Morning   - it breaks into drifting panels, everything shrinks into a miniature bedroom that
 *                               settles into the Codex cover; the bed folds away, the lamps sink, the book closes.
 */
export default defineSpell("dn06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 14);
  const fwd = norm({ x: aim.forward.x, y: 0, z: aim.forward.z });
  const rt = right(fwd);
  const C0 = { ...caster.location };
  const g0 = C0.y;
  const lights = blocksFor(scene);
  const faceYaw = yawOf(mul(fwd, -1));             // the bed and the Dreamer face the caster
  const at = (base: Vector3, yaw: number, r: number, u: number, f: number): Vector3 => {
    const fd = fromYaw(yaw), rr = right(fd);
    return { x: base.x + rr.x * r + fd.x * f, y: base.y + u, z: base.z + rr.z * r + fd.z * f };
  };
  const atR = (base: Vector3, yaw: number, p: RUF, k = 1): Vector3 => at(base, yaw, p[0] * k, p[1] * k, p[2] * k);
  const rel = (r: number, u: number, f: number): Vector3 => at(C0, aim.yaw, r, u, f);
  const ground = (p: Vector3): Vector3 => groundBelow(dim, { x: p.x, y: Math.max(p.y, g0 + 4), z: p.z }, 50);
  /** Push a ground point out of the caster's clear zone (tall things never stand right next to the caster). */
  const clear = (p: Vector3, minD = C.clearZone): Vector3 => {
    const d = distXZ(p, C0);
    if (d >= minD) return p;
    const dir = d > 0.5 ? norm({ x: p.x - C0.x, y: 0, z: p.z - C0.z }) : fwd;
    return ground({ x: C0.x + dir.x * minD, y: p.y, z: C0.z + dir.z * minD });
  };

  // ---- staging ------------------------------------------------------------------------------------
  const cd = distXZ(C0, center);
  const stageD = clamp(cd + C.stageBeyond, C.stageMin, C.stageMax);
  const stageG = ground(rel(0, 0, stageD));
  const stage = up(stageG, HOVER_LIFT);                       // the Dreamer's hips when it stands in its pool
  const bedD = Math.min(stageD + C.bedBeyond, C.bedMax);
  const bedG = ground(rel(0, 0, bedD));
  const bedRest = { x: bedG.x, y: Math.max(bedG.y, g0 - 2) + C.bedHeight, z: bedG.z };

  // ---- effects helpers -----------------------------------------------------------------------------
  let seed = 7919;
  const rnd = (): number => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const scatter = (c: Vector3, r: number, h0: number, h1: number): Vector3 => {
    const a = rnd() * Math.PI * 2, d = Math.sqrt(rnd()) * r;
    return { x: c.x + Math.cos(a) * d, y: c.y + h0 + rnd() * (h1 - h0), z: c.z + Math.sin(a) * d };
  };
  const fx = (id: string, p: Vector3): void => particle(dim, `dn_dreamer_${id}`, p);
  const sfx = (id: string, p: Vector3, vol = 1, pitch = 1): void => sound(dim, `dn_dreamer_${id}`, p, vol, pitch);
  /** n particles round a point (golden-angle sphere). */
  const puff = (id: string, c: Vector3, r: number, n: number): void => {
    for (let i = 0; i < n; i++) {
      const y = 1 - (2 * (i + 0.5)) / n, rr = Math.sqrt(1 - y * y) * r, a = i * 2.39996;
      fx(id, { x: c.x + Math.cos(a) * rr, y: c.y + y * r, z: c.z + Math.sin(a) * rr });
    }
  };
  /** n particles on a flat ring. */
  const hoop = (id: string, c: Vector3, r: number, n: number, ph = 0): void => {
    for (let i = 0; i < n; i++) {
      const a = ((ph + (360 * i) / n) * Math.PI) / 180;
      fx(id, { x: c.x + Math.cos(a) * r, y: c.y, z: c.z + Math.sin(a) * r });
    }
  };
  const streak = (id: string, a: Vector3, b: Vector3, n: number): void => {
    for (let i = 0; i < n; i++) fx(id, lerp(a, b, n === 1 ? 0.5 : i / (n - 1)));
  };
  /** Ambient layers run every tick in [from, to), except on the ticks kept free for a big burst (hush). */
  const hushed = new Set<number>();
  const hush = (t: number): void => { hushed.add(t); };
  const layer = (from: number, to: number, fn: (e: number) => void): void => {
    scene.every(1, (e) => { if (!hushed.has(scene.tick)) fn(e); }, from, to);
  };
  /** Repeat k times, k may be fractional (the remainder fires on a share of the ticks). */
  const times = (k: number, fn: () => void): void => {
    const n = Math.floor(k) + (rnd() < k - Math.floor(k) ? 1 : 0);
    for (let i = 0; i < n; i++) fn();
  };

  // ---- marks & targets -----------------------------------------------------------------------------
  const marks = new Map<string, { e: Entity; a: Actor }>();
  function markNew(limit = C.maxMarks): void {
    for (const e of hostiles(dim, center, C.radius, caster)) {
      if (marks.size >= limit) break;
      if (marks.has(e.id)) continue;
      const a = scene.spawn("dn_dreamer_mark", up(e.location, 2.6), { state: 1 });
      scene.follow(a, e, 2.6);
      scene.after(10, () => a.state(2));
      marks.set(e.id, { e, a });
      sfx("mark", e.location, 0.6, 0.9 + marks.size * 0.06);
      const top = up(e.location, 2.6);
      fx("moon", top); fx("glow", top);
      streak("thread", up(top, 7), top, 4);
      fx("ring", up(groundBelow(dim, e.location), 0.1));
      return;   // one at a time: marks land one by one like falling asleep
    }
  }
  function marked(): Entity[] {
    const out: Entity[] = [];
    for (const m of marks.values()) if (isAlive(m.e) && distXZ(m.e.location, center) < C.radius + 6) out.push(m.e);
    if (out.length) return out;
    return hostiles(dim, center, C.radius, caster);
  }
  /** n target points: marked enemies first, otherwise spread round the focus (the spell works with no enemies). */
  function targets(n: number, spread = 6): { loc: Vector3; e?: Entity }[] {
    const es = marked();
    const out: { loc: Vector3; e?: Entity }[] = [];
    for (let i = 0; i < n; i++) {
      if (es.length) { const e = es[i % es.length]; out.push({ loc: groundBelow(dim, e.location), e }); }
      else out.push({ loc: clear(ground(at(center, aim.yaw, i === 0 ? 0 : spread * Math.cos(i * 2.1), 0, i === 0 ? 0 : spread * 0.6 * Math.sin(i * 2.1)))) });
    }
    return out;
  }
  /** Up to n group centres of the marked enemies (greedy clustering), kept out of the caster's clear zone. */
  function groups(n: number): Vector3[] {
    const es = marked();
    const out: Vector3[] = [];
    for (const e of es) {
      if (out.length >= n) break;
      const g = clear(groundBelow(dim, e.location), C.clearZone + 0.5);
      if (out.every((c) => distXZ(c, g) > C.zoneRadius * 1.6)) out.push(g);
    }
    const base = out.length ? out[0] : center;
    for (let i = out.length; i < n; i++) out.push(clear(ground(at(base, aim.yaw, (i % 2 ? 1 : -1) * 8, 0, i * 2)), C.clearZone + 0.5));
    return out;
  }
  function centroid(): Vector3 {
    const es = marked();
    if (!es.length) return clear(center);
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return clear(groundBelow(dim, mul(s, 1 / es.length)));
  }
  function warn(loc: Vector3, size: number, slow: boolean, life: number): Actor {
    const t = scene.spawn("telegraph", up(loc, 0.05), { kind: 1, size, state: slow ? TG.warnSlow : TG.warn });
    scene.after(life, () => t.state(TG.flash));
    scene.after(life + 8, () => scene.despawn(t));
    return t;
  }
  function hitOnce(set: Set<string>, loc: Vector3, r: number, dmg: number, after?: (e: Entity) => void): number {
    let n = 0;
    for (const e of hostiles(dim, loc, r, caster)) {
      if (set.has(e.id)) continue;
      set.add(e.id);
      if (damage(e, dmg, caster)) n++;
      after?.(e);
    }
    return n;
  }
  /** Impact accent: dust, a flat ring and sparks where something heavy lands. */
  function impact(p: Vector3, big = false): void {
    fx("dust", up(p, 0.3));
    fx(big ? "dwave" : "ring", up(p, 0.15));
    puff("streak", up(p, 0.8), 0.6, big ? 6 : 3);
    if (big) { fx("flash", up(p, 1.5)); fx("dust", up(p, 0.6)); puff("shardbig", up(p, 1), 1, 4); }
  }

  // ---- timeline (ticks after release) ---------------------------------------------------------------
  const T2 = 130;                                   // II  the sleeper manifests in the bed
  const T_SIT = T2 + LEN.manifest;
  const T_RISE = T_SIT + LEN.sit;
  const T_AWAKE = T_RISE + LEN.rise;
  const T_HOV = T_AWAKE + LEN.awaken;
  const T_SWEEP = T_HOV + 4;
  const T_CAB = T_SWEEP + LEN.sweep + 2;
  const T3 = T_CAB + LEN.cabinet;                   // III both hands rise
  const ZONE_FROM = T3 + 48, ZONE_TO = T3 + 208;
  const T4 = ZONE_TO + 2;                           // IV  the Great Unreality
  const T_WHEEL = T4 + 14, T_ARMS = T4 + 50, T_DRILL = T4 + 86, T_SWING = T4 + 138, T_ROOMS = T4 + 150;
  const T_FIN = T4 + 200;                           //     the face-door finale
  const T_SLAM = T_FIN + LEN.finale;
  const T_PEAK = T_SLAM + 6;
  const T5 = T_SLAM + 24;                           // V   the forgotten morning
  const T_ROOM = T5 + 16, T_CLOSE = T5 + 88;
  const T_END = T_CLOSE + 56;

  // ================================================================ PHASE I - The Bed Above the Sky (0 - T2)
  const domain = scene.spawn("dn_dreamer_domain", up(center, 0.05), { size: C.radius / 2, state: 1 });
  scene.at(32, () => domain.state(2));
  lights.place(up(center, 2), LIGHT);
  lights.place(up(stageG, 3), LIGHT);
  fx("dwave", up(center, 0.15));
  hoop("mote", up(center, 0.4), 6, 12);
  layer(0, 40, (e) => {                       // the domain forms: a ring of light runs out across the ground
    const r = 2 + smooth(e / 39) * C.radius;
    for (let i = 0; i < 7; i++) {
      const a = rnd() * Math.PI * 2;
      fx(i % 3 === 0 ? "sparkle" : "mote", { x: center.x + Math.cos(a) * r, y: center.y + 0.2 + rnd() * 0.6, z: center.z + Math.sin(a) * r });
    }
  });
  // moon lamps rise one by one round the rim of the domain (never right beside the caster)
  const lamps: Actor[] = [];
  const back = (Math.atan2(-fwd.z, -fwd.x) * 180) / Math.PI;
  for (let k = 0; k < LAMPS; k++) {
    const a = ((back + 22.5 + k * 45) * Math.PI) / 180;
    const p = ground({ x: center.x + Math.cos(a) * C.radius * 0.96, y: center.y, z: center.z + Math.sin(a) * C.radius * 0.96 });
    scene.at(8 + k * 4, () => {
      const l = scene.spawn("dn_dreamer_lamp", p, { yaw: yawOf(sub(center, p)), state: LAMP.rise });
      lamps.push(l);
      scene.after(20, () => l.state(LAMP.hold));
      fx("glow", up(p, 6)); fx("ring", up(p, 0.1)); puff("sparkle", up(p, 5.5), 0.8, 4);
    });
  }

  // the Codex opens low beside the caster, ahead-left (it turns with the caster so it stays in that corner)
  let codexYaw = aim.yaw;
  const codex = scene.spawn("dn_dreamer_codex", C0, { yaw: codexYaw, state: CODEX.open });
  scene.every(1, () => {
    if (!caster.isValid) return;
    try { codexYaw = caster.getRotation().y; } catch { /* keep */ }
    codex.move(caster.location, codexYaw);
  }, 1, T_END);
  const bookAt = (): Vector3 => atR(codex.valid ? codex.loc : C0, codexYaw, BOOK);
  scene.at(60, () => codex.state(CODEX.hold));
  sfx("book", C0, 0.9);
  sfx("musicbox", C0, 0.8);
  scene.at(18, () => puff("paper", bookAt(), 0.4, 8));
  scene.at(28, () => { fx("glow", bookAt()); puff("sparkle", bookAt(), 0.6, 6); });

  // the bed drifts in from far away, high to the right, and settles tilted toward the caster
  const bedFrom = rel(18, 26, bedD + 2);           // high up to the right, out of view at first
  const bedMid = rel(11, 18, bedD + 1);
  let bedPos = { ...bedFrom };
  const bed = scene.spawn("dn_dreamer_bed", bedFrom, { yaw: faceYaw, state: BED.arrive });
  sfx("bed", bedRest, 1.1);
  scene.span(0, 60, (p) => { bedPos = bezier(bedFrom, bedMid, bedRest, easeOut(p)); bed.move(bedPos, faceYaw); });
  hush(60);
  scene.at(60, () => {
    bed.state(BED.float);
    puff("star", up(bedPos, 2), 7, 22);
    puff("glow", up(bedPos, 2), 3, 4);
    fx("flash", up(bedPos, 2));
    hoop("feather", up(bedPos, -2), 6, 10);
    sfx("swell", bedPos, 0.9);
  });
  const pivotAt = (): Vector3 => at(bedPos, faceYaw, 0, PIVOT.up, PIVOT.fwd);
  scene.every(6, () => markNew(), 16, 120);
  scene.every(30, () => markNew(), 120, T5);      // newcomers are marked as they enter the domain
  scene.at(100, () => sfx("breath", bedPos, 1.0));

  // ambient I+: motes over the domain, glitter in the sky, the bed shedding petals, feathers and starlight,
  // a thread of light falling from the bed onto the domain, music-box notes and paper drifting from the Codex
  layer(0, T4, () => {
    times(9, () => fx("mote", scatter(center, C.radius * 0.85, 0.2, 2.8)));
    times(3.5, () => fx("sparkle", scatter(center, 18, 2, 11)));
    times(2.5, () => fx("mote", scatter(C0, 4.5, 0.1, 0.7)));     // low motes round the caster's feet
  });
  // a dream wind: petals and feathers blow from the bed across the field toward the caster
  layer(40, T4, () => {
    times(2, () => fx("petal", lerp(scatter(bedPos, 6, -4, 2), scatter(C0, 6, 1, 4), rnd() * 0.85)));
    times(1, () => fx("feather", lerp(scatter(bedPos, 6, -4, 2), scatter(C0, 6, 1, 4), rnd() * 0.85)));
  });
  layer(0, 60, () => {
    times(5, () => fx("star", scatter(bedPos, 4, -2, 2)));
    times(1.5, () => fx("feather", scatter(bedPos, 4, -3, 0)));
    times(1.5, () => fx("petal", scatter(bedPos, 4, -3, 0)));
  });
  layer(60, T4, () => {
    times(6, () => fx("star", scatter(pivotAt(), 9, -5, 7)));
    times(2, () => fx("petal", scatter(bedPos, 8, -6, 0)));
    times(2, () => fx("feather", scatter(bedPos, 8, -6, 0)));
    times(0.5, () => fx("mist", scatter(bedPos, 7, -8, -4)));
  });
  layer(60, T_RISE + 20, () => {
    const top = pivotAt();
    times(5, () => fx("thread", lerp(top, up(center, 1), rnd())));
  });
  layer(10, T2 + 40, () => {
    times(0.4, () => fx("note", add(bookAt(), { x: (rnd() - 0.5) * 0.6, y: 0.3 + rnd() * 0.4, z: (rnd() - 0.5) * 0.6 })));
    times(1.2, () => fx("paper", scatter(C0, 3.8, 0.2, 1.1)));
    times(0.6, () => fx("sparkle", scatter(bookAt(), 0.6, 0, 0.6)));
  });
  // signature I -> II: a column of falling stars onto the bed and a ring of light round it
  scene.at(T2 - 14, () => {
    const p = pivotAt();
    for (let i = 0; i < 8; i++) fx("column", up(p, -3 + i * 1.6));
    sfx("swell", p, 1.1, 0.9);
  });
  hush(T2 - 2);
  scene.at(T2 - 2, () => { const p = pivotAt(); fx("flash", p); hoop("star", p, 9, 26); puff("moon", p, 5, 12); hoop("glow", p, 6, 6); });

  // ================================================================ PHASE II - The Sleeper Rises (T2 - T3)
  let dreamer = new Actor(undefined, "grimoire:dreamer");
  let dPos = pivotAt();
  let dYaw = faceYaw;
  let doorRel: RUF = DOOR;
  const doorAt = (): Vector3 => atR(dPos, dYaw, doorRel);
  /** Turn the Dreamer's head toward a point (its body keeps facing the caster); none looks straight ahead. */
  const look = (p?: Vector3): void => {
    if (!p) { dreamer.prop("look", 0); return; }
    const d = angleDelta(dYaw, yawOf(sub(p, dPos)));
    dreamer.prop("look", clamp(-d, -60, 60));
  };
  scene.at(T2, () => {
    dPos = pivotAt();
    dreamer = scene.spawn("dreamer", dPos, { yaw: faceYaw, state: DS.manifest });
    bed.state(BED.occupied);
    sfx("manifest", dPos, 1.3);
    sfx("breath", dPos, 1.0, 0.8);
  });
  const tiltR = (TILT_A * Math.PI) / 180;
  /** A point along the sleeper lying in the tilted bed: feet (f = 0) down toward the caster, crown (f = 1) up and away. */
  const bodyAlong = (f: number): Vector3 => {
    const fd = fromYaw(faceYaw), s = -LIE.feet + f * (LIE.feet + LIE.crown);
    return add(pivotAt(), { x: -fd.x * Math.cos(tiltR) * s, y: Math.sin(tiltR) * s, z: -fd.z * Math.cos(tiltR) * s });
  };
  // it appears section by section, feet first: porcelain dust and light swirl along its body as each part forms
  layer(T2, T_SIT, (e) => {
    const f = clamp(e / LEN.manifest, 0, 1);
    times(5, () => fx("porcelain", add(bodyAlong(clamp(f + (rnd() - 0.5) * 0.14, 0, 1)), { x: rnd() - 0.5, y: rnd() * 0.8, z: rnd() - 0.5 })));
    times(2, () => fx("sparkle", bodyAlong(rnd() * f)));
    times(1, () => fx("trail", bodyAlong(clamp(f + (rnd() - 0.5) * 0.1, 0, 1))));
    if (e % 12 === 0) { fx("glow", bodyAlong(f)); sfx("mark", bodyAlong(f), 0.35, 1.4 + f * 0.4); }
  });

  // sits up: the bed takes its weight and levels out; a pillow slides off and falls onto an enemy
  const dipAt = (e: number): number => {
    for (let i = 1; i < DIP.length; i++) {
      if (e <= DIP[i][0]) { const [t0, v0] = DIP[i - 1], [t1, v1] = DIP[i]; return v0 + (v1 - v0) * ((e - t0) / (t1 - t0)); }
    }
    return DIP[DIP.length - 1][1];
  };
  scene.at(T_SIT, () => {
    dreamer.state(DS.sit); bed.state(BED.dip);
    sfx("groan", dPos, 1.3); sfx("inhale", dPos, 1.1);
    puff("feather", pivotAt(), 5, 14);
  });
  scene.span(T_SIT, T_RISE + 10, (_p, e) => { dPos = up(pivotAt(), (dipAt(e) * BED_SCALE) / 16); dreamer.move(dPos, faceYaw); });
  layer(T_SIT, T_RISE, () => {
    times(3, () => fx("feather", scatter(bedPos, 6, -4, 1)));
    times(2, () => fx("porcelain", scatter(dPos, 2.5, 0, 5)));
  });
  const pillowTarget = targets(1)[0];
  let pLand = pillowTarget.loc;
  scene.at(T_SIT + 11, () => {
    pLand = clear(targets(1)[0].loc, C.clearZone - 1);
    const w = warn(pLand, C.pillowRadius, true, C.warnLong);
    const a = (-(TILT_A + 3) * Math.PI) / 180;            // the bed's tilt at that moment of the dip
    const yy = PILLOW.y * Math.cos(-a) + PILLOW.z * Math.sin(-a), zz = -PILLOW.y * Math.sin(-a) + PILLOW.z * Math.cos(-a);
    const from = at(pivotAt(), faceYaw, (PILLOW.r * BED_SCALE) / 16, (yy * BED_SCALE) / 16, (-zz * BED_SCALE) / 16);
    const pil = scene.spawn("dn_dreamer_pillow", from, { yaw: faceYaw, state: 1 });
    const top = up(lerp(from, pLand, 0.3), 5);
    sfx("pillow", from, 0.6, 1.3);
    scene.span(scene.tick, scene.tick + C.warnLong, (p) => {
      const tgt = pillowTarget.e && isAlive(pillowTarget.e) && p < 0.7 ? clear(groundBelow(dim, pillowTarget.e.location), C.clearZone - 1) : pLand;
      pLand = tgt; w.move(up(tgt, 0.05));
      const pos = bezier(from, top, tgt, easeIn(p) * 0.6 + p * 0.4);
      pil.move(pos);
      fx("feather", pos); fx("trail", pos);
    });
    scene.after(C.warnLong, () => {
      pil.state(2);
      sfx("pillow", pLand, 1.3);
      impact(pLand, true);
      puff("feather", up(pLand, 1.2), 2.5, 16);
      hitOnce(new Set(), pLand, C.pillowRadius, C.pillowDamage, (e) => knockback(e, pLand, C.pillowKnock, 0.45));
      scene.after(14, () => pil.state(3));
      scene.after(32, () => scene.despawn(pil));
    });
  });

  // rises out of the bed, glides down into its pool and grows to its full height; the bed lifts, relieved
  scene.at(T_RISE, () => {
    dreamer.state(DS.rise); bed.state(BED.empty);
    sfx("groan", dPos, 1.5, 0.85); sfx("inhale", dPos, 1.3, 0.8);
    puff("feather", pivotAt(), 6, 16);
  });
  scene.at(T_RISE + 60, () => bed.state(BED.rest));
  let riseFrom = dPos;
  scene.at(T_RISE + 9, () => { riseFrom = { ...dPos }; });
  scene.span(T_RISE + 10, T_RISE + 56, (p) => {
    const mid = up(lerp(riseFrom, stage, 0.45), 3.5);
    dPos = bezier(riseFrom, mid, stage, smooth(p));
    dreamer.move(dPos, faceYaw);
    times(4, () => fx("porcelain", scatter(dPos, 3, 0, 9)));
    times(2, () => fx("trail", scatter(dPos, 1.5, 3, 9)));
    times(0.5, () => fx("mist", scatter(dPos, 3, 0, 3)));
    times(2, () => fx("feather", scatter(lerp(riseFrom, dPos, rnd()), 2, 0, 3)));
  });
  hush(T_RISE + 52);
  scene.at(T_RISE + 52, () => {                       // it settles into its pool: the blanket spreads with a hush
    impact(stageG, true);
    hoop("pool", up(stageG, 0.15), 3, 8);
    hoop("mist", up(stageG, 0.4), 6, 12, 15);
    hoop("dust", up(stageG, 0.3), 5, 8);
    sfx("land", stageG, 1.4);
  });
  scene.at(T_AWAKE - 1, () => { dPos = stage; });

  // awakens in its pool: the head turns toward the enemies and back, and the small door in its face opens
  scene.at(T_AWAKE, () => {
    dreamer.move(stage, faceYaw).state(DS.awaken);
    sfx("hum", dPos, 1.3);
    look(centroid());
  });
  scene.at(T_AWAKE + 14, () => { sfx("door", doorAt(), 1.3); look(); });
  hush(T_AWAKE + 24);
  scene.at(T_AWAKE + 24, () => {
    const p = doorAt();
    fx("flash", p); fx("glow", p); fx("column", up(p, 2));
    puff("star", p, 1.6, 14); puff("moon", p, 1.3, 6); hoop("glow", p, 1.6, 6);
    sfx("swell", p, 0.9, 1.2);
  });
  // stars and paper moons keep drifting out of the open door from now on
  layer(T_AWAKE + 24, T_FIN, () => {
    times(1.2, () => fx(rnd() < 0.3 ? "moon" : "star", doorAt()));
    times(0.4, () => fx("sparkle", scatter(doorAt(), 0.8, -0.4, 0.4)));
  });
  scene.at(T_HOV, () => dreamer.state(DS.hover));
  // ambient II-IV: twinkles and porcelain dust on the body, mist and ripples on its pool
  layer(T_AWAKE, T5, (e) => {
    times(4, () => fx("sparkle", scatter(dPos, 3.5, 1, 11)));
    times(2, () => fx("porcelain", scatter(dPos, 4, 2, 10)));
    times(0.6, () => fx("pool", scatter(stageG, 5, 0.1, 0.2)));
    times(0.5, () => fx("mist", scatter(stageG, 6.5, 0.2, 1.2)));
    const head = atR(dPos, dYaw, DOOR);                            // glints orbiting its head like moths
    for (let i = 0; i < 2; i++) {
      const a = e * 0.12 + i * Math.PI;
      fx("trail", { x: head.x + Math.cos(a) * 2.6, y: head.y + 0.6 + Math.sin(e * 0.07 + i) * 0.8, z: head.z + Math.sin(a) * 2.6 });
    }
  });

  // the right hand rakes the ground (it lunges forward; telegraphed arc, damage + knockback where the hand passes)
  const lunge = clamp(distXZ(stage, center) - SWEEP_PATH[2][2], 0, C.sweepLunge);
  const sweepBase = (): Vector3 => at(stage, faceYaw, 0, 0, lunge);
  const sweepPt = (i: number): Vector3 => atR(sweepBase(), faceYaw, SWEEP_PATH[i]);
  scene.at(T_SWEEP + SWEEP_HIT[0] - C.warnLong - 2, () => {
    for (let i = 0; i < SWEEP_PATH.length; i++) warn(clear(ground(sweepPt(i))), C.sweepRadius, true, C.warnLong + 4 + i * 3);
    look(ground(sweepPt(0)));
  });
  scene.at(T_SWEEP, () => { dreamer.state(DS.sweep); sfx("groan", dPos, 1.0, 1.1); });
  scene.span(T_SWEEP + 6, T_SWEEP + 24, (p) => { dPos = lerp(stage, sweepBase(), smooth(p)); dreamer.move(dPos, faceYaw); });
  scene.span(T_SWEEP + 44, T_SWEEP + LEN.sweep, (p) => { dPos = lerp(sweepBase(), stage, smooth(p)); dreamer.move(dPos, faceYaw); });
  scene.at(T_SWEEP + 18, () => sfx("sweep", ground(sweepPt(2)), 1.6));
  const swept = new Set<string>();
  scene.span(T_SWEEP + SWEEP_HIT[0], T_SWEEP + SWEEP_HIT[1], (p) => {
    const f = p * (SWEEP_PATH.length - 1);
    const i = Math.min(Math.floor(f), SWEEP_PATH.length - 2);
    const hand = ground(lerp(sweepPt(i), sweepPt(i + 1), f - i));
    const along = norm(sub(sweepPt(i + 1), sweepPt(i)));
    look(hand);
    fx("dust", up(hand, 0.3));
    times(3, () => fx("streak", scatter(hand, 1.5, 0.3, 1.5)));
    times(3, () => fx("petal", scatter(hand, 2, 0.5, 2)));
    times(2, () => fx("porcelain", scatter(hand, 1.5, 0.5, 2)));
    if (Math.round(p * 15) % 3 === 0) fx("ring", up(hand, 0.1));
    hitOnce(swept, hand, C.sweepRadius, C.sweepDamage, (e) => shove(e, along, C.sweepKnock, 0.5));
  });
  scene.at(T_SWEEP + LEN.sweep, () => { dreamer.state(DS.hover); look(); });

  // the chest cabinet opens and a staircase spills out of it, cascading onto an enemy
  let stairDir = mul(fwd, -1);
  let stairFrom = stageG;
  scene.at(T_CAB - 8, () => {
    const t = clear(targets(1)[0].loc, C.clearZone + 2);
    look(t);
    stairDir = norm({ x: t.x - stage.x, y: 0, z: t.z - stage.z });
    stairFrom = ground({ x: t.x - stairDir.x * STEP(9), y: t.y, z: t.z - stairDir.z * STEP(9) });   // its last step lands on the target
    for (let k = 2; k < 10; k += 3) warn(ground(add(stairFrom, mul(stairDir, STEP(k)))), C.stairsRadius, false, 18 + STEP_LAND(k));
  });
  scene.at(T_CAB, () => { dreamer.state(DS.cabinet); sfx("door", atR(dPos, dYaw, CHEST), 1.1, 0.7); });
  scene.at(T_CAB + 10, () => {
    const chest = atR(dPos, dYaw, CHEST);
    streak("trailbig", chest, up(stairFrom, 4), 12);
    fx("flash", chest); puff("glint", chest, 1, 4);
    const st = scene.spawn("dn_dreamer_stairs", stairFrom, { yaw: yawOf(stairDir), state: 1 });
    sfx("stairs", stairFrom, 1.3);
    const hit = new Set<string>();
    for (let k = 0; k < 10; k++) {
      scene.after(STEP_LAND(k), () => {
        const p = ground(add(stairFrom, mul(stairDir, STEP(k))));
        fx("dust", up(p, 0.2)); puff("streak", up(p, 0.4), 0.4, 2);
        if (k % 2 === 0) fx("ring", up(p, 0.1));
        hitOnce(hit, p, C.stairsRadius, C.stairsDamage, (e) => shove(e, stairDir, 0.8, 0.35));
      });
    }
    scene.after(50, () => st.state(2));
    scene.after(72, () => scene.despawn(st));
  });
  layer(T_CAB + 10, T_CAB + 40, () => times(3, () => fx("trail", lerp(atR(dPos, dYaw, CHEST), up(stairFrom, 4), rnd()))));
  scene.at(T_CAB + LEN.cabinet + 2, () => { dreamer.state(DS.hover); look(); });

  // ================================================================ PHASE III - Dream Zones / Nightmare Zones
  const dreamZones: { a: Actor; loc: Vector3; kind: number }[] = [];
  const nightZones: { a: Actor; loc: Vector3; kind: number }[] = [];
  let ward: Ward | undefined;
  const palm = (p: RUF): Vector3 => atR(dPos, dYaw, p);
  scene.at(T3, () => {
    dreamer.state(DS.raise).skin(1);          // porcelain splits: the nightmare beneath begins to show
    sfx("raise", up(dPos, 8), 1.5);
    puff("porcelain", up(dPos, 6), 3, 12);
  });
  hush(T3 + 28);
  scene.at(T3 + 28, () => {                  // signature II -> III: both palms flare, two ring waves roll out
    const r = palm(PALM_R), l = palm(PALM_L);
    fx("flash", r); fx("flash", l); fx("column", up(r, 3)); fx("column", up(l, 3));
    puff("star", r, 2, 14); puff("eye", l, 2, 8); puff("ember", l, 2, 10);
    fx("dwave", up(C0, 0.2)); fx("nwave", up(center, 0.2));
    sfx("swell", up(dPos, 8), 1.2, 0.8);
  });
  scene.at(T3 + 26, () => {                  // right hand: dream zones -- a sanctuary under the caster, gardens beside
    const spots: { loc: Vector3; kind: number }[] = [];
    for (const p of allies(dim, C0, 24, caster)) {
      if (p.id === caster.id || spots.length >= 2) continue;
      const loc = groundBelow(dim, p.location);
      spots.push({ loc, kind: distXZ(loc, C0) < C.clearZone ? 3 : spots.length });
    }
    const flank = (s: number): Vector3 => ground(rel(s * Math.sin((C.dreamFlankAngle * Math.PI) / 180) * C.dreamFlank, 0,
      Math.cos((C.dreamFlankAngle * Math.PI) / 180) * C.dreamFlank));
    if (spots.length < 3) spots.push({ loc: flank(-1), kind: 2 });     // golden stairway to the left
    if (spots.length < 3) spots.push({ loc: flank(1), kind: 0 });      // floating garden to the right
    if (spots.length < 3) spots.push({ loc: ground(rel(0, 0, -C.dreamFlank)), kind: 1 });   // cloud city behind
    const hand = palm(PALM_R);
    const sanct = scene.spawn("dn_dreamer_sanctum", groundBelow(dim, C0), { yaw: aim.yaw, state: ZONE.bloom });
    dreamZones.push({ a: sanct, loc: groundBelow(dim, C0), kind: 3 });
    scene.after(30, () => sanct.state(ZONE.idle));
    hoop("petal", up(C0, 0.6), C.zoneRadius, 10);
    spots.forEach((s, i) => {
      const a = s.kind === 3 ? scene.spawn("dn_dreamer_sanctum", s.loc, { yaw: aim.yaw, state: ZONE.bloom })
        : scene.spawn("dn_dreamer_dream", s.loc, { kind: s.kind, yaw: yawOf(sub(C0, s.loc)), state: ZONE.bloom });
      dreamZones.push({ a, loc: s.loc, kind: s.kind });
      streak("trailbig", hand, up(s.loc, 3), 12);
      hoop("petal", up(s.loc, 1), C.zoneRadius, 8, i * 30);
      fx("dwave", up(s.loc, 0.15)); fx("column", up(s.loc, 4));
      if (s.kind !== 3) lights.place(up(s.loc, 2), LIGHT);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sfx("bloom", C0, 1.0);
    ward = addWard({
      scene, factor: C.wardFactor, pool: C.wardPool,
      protects: (e) => e.typeId === "minecraft:player" && dreamZones.some((z) => distXZ(z.loc, e.location) <= C.zoneRadius),
      onAbsorb: (_n, _a, v) => { fx("ring", up(v.location, 0.2)); fx("glow", up(v.location, 1)); },
    });
  });
  scene.at(T3 + 34, () => {                  // left hand: nightmare zones swallow the enemy groups
    const hand = palm(PALM_L);
    // the tallest nightmare (the upside-down room) goes to the group furthest off the view line, the low living
    // doors to the most central one, so the Dreamer stays visible behind them
    const lat = (p: Vector3): number => Math.abs((p.x - C0.x) * rt.x + (p.z - C0.z) * rt.z);
    const gs = groups(3).sort((a, b) => lat(b) - lat(a));
    gs.forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_night", loc, { kind: i, yaw: yawOf(sub(C0, loc)), state: ZONE.bloom });
      nightZones.push({ a, loc, kind: i });
      streak("ntrail", hand, up(loc, 3), 12);
      fx("nwave", up(loc, 0.15));
      puff("nmist", up(loc, 1), 2.5, 4);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sfx("emerge", nightZones.length ? nightZones[0].loc : center, 1.3);
    look(centroid());
  });
  scene.at(T3 + LEN.raise, () => dreamer.state(DS.conjure));
  // ambient III: blossoms, keys and twinkles in the dream gardens; smoke, embers and eyes in the nightmares;
  // two streams of light flow from the raised palms into the zones while they live
  layer(T3 + 30, T4 + 20, () => {
    for (const z of dreamZones) {
      times(z.kind === 3 ? 2 : 2.5, () => fx("bloom", scatter(z.loc, 3.8, 0.2, z.kind === 3 ? 0.8 : 2.8)));
      times(0.6, () => fx(z.kind === 3 ? "mote" : "key", scatter(z.loc, 3, 0.4, z.kind === 3 ? 1 : 3.5)));
    }
  });
  layer(T3 + 38, T4 + 20, () => {
    for (const z of nightZones) {
      times(2.5, () => fx("ember", scatter(z.loc, 3.8, 0.2, 2.4)));
      times(0.6, () => fx("nmist", scatter(z.loc, 3.6, 0.2, 1.0)));
      times(0.3, () => fx("eye", scatter(z.loc, 3, 1, 3.5)));
    }
  });
  layer(T3 + 30, T4, (e) => {
    const r = palm(PALM_R), l = palm(PALM_L);
    dreamZones.forEach((z, i) => fx("trail", lerp(r, up(z.loc, z.kind === 3 ? 1.5 : 3), ((e * 0.045 + i * 0.37) % 1))));
    nightZones.forEach((z, i) => fx("ntrail", lerp(l, up(z.loc, 3), ((e * 0.045 + i * 0.29) % 1))));
    dreamZones.forEach((z, i) => fx("sparkle", lerp(r, up(z.loc, z.kind === 3 ? 1.5 : 3), ((e * 0.045 + i * 0.37 + 0.5) % 1))));
    nightZones.forEach((z, i) => fx("ember", lerp(l, up(z.loc, 3), ((e * 0.045 + i * 0.29 + 0.5) % 1))));
    times(0.5, () => fx("glow", r)); times(0.5, () => fx("nglow", l));
  });
  scene.every(C.zonePulse, (e) => {            // dream pulses: heal, ward, supportive effect
    const k = e / C.zonePulse;
    for (const z of dreamZones) {
      fx("heal", up(z.loc, 0.5));
      if (k % 2 === 0) { fx("ring", up(z.loc, 0.15)); fx("column", up(z.loc, 4)); }
      for (const p of allies(dim, z.loc, C.zoneRadius, caster)) {
        if (heal(p, C.dreamHeal) > 0) { sfx("heal", p.location, 0.5, 1 + z.kind * 0.1); fx("heal", up(p.location, 1)); }
        if (z.kind === 0 || z.kind === 3) effect(p, "regeneration", C.dreamEffectTicks, 0);
        if (z.kind === 1 || z.kind === 3) { effect(p, "resistance", C.dreamEffectTicks, 0); effect(p, "slow_falling", C.dreamEffectTicks, 0); }
        if (z.kind === 2) { effect(p, "speed", C.dreamEffectTicks, 1); effect(p, "jump_boost", C.dreamEffectTicks, 0); }
      }
    }
    if (k % 2 === 0 && dreamZones.length) sfx("sweet", dreamZones[0].loc, 0.75);
  }, ZONE_FROM, ZONE_TO);
  scene.every(C.zonePulse, (e) => {            // nightmare pulses, interleaved half a pulse later
    const big = (e / C.zonePulse) % 2 === 1;
    for (const z of nightZones) {
      fx(big ? "eye" : "nring", up(z.loc, big ? 2 : 0.2));
      if (big) {
        z.a.state(ZONE.bite); scene.after(14, () => z.a.state(ZONE.idle));
        sfx("bite", z.loc, 0.9);
        fx("nwave", up(z.loc, 0.15)); puff("ember", up(z.loc, 1.5), 2, 8);
      }
      for (const e2 of hostiles(dim, z.loc, C.zoneRadius, caster)) {
        damage(e2, big ? C.biteDamage : C.nightDamage, caster);
        effect(e2, "slowness", C.zonePulse + 10, C.nightSlowAmp);
        effect(e2, "weakness", C.zonePulse * 2, 1);
        if (!big) continue;
        if (z.kind === 0) {                    // upside-down room: gravity flips, they turn around
          effect(e2, "levitation", C.roomLift, 1);
          try { const r = e2.getRotation(); e2.setRotation({ x: r.x, y: r.y + 180 }); } catch { /* ignore */ }
        } else if (z.kind === 1) {             // predatory corridor swallows and holds them
          restrain(scene, e2, C.corridorHold, up(z.loc, 0.1));
        } else {                               // living doors bite and slam them away
          knockback(e2, z.loc, 1.4, 0.4);
        }
      }
    }
    if (!big && nightZones.length) sfx("sour", nightZones[0].loc, 0.75);
  }, ZONE_FROM + C.zonePulse / 2, ZONE_TO);

  // ================================================================ PHASE IV - The Great Unreality
  // the bed folds into a cradle and lifts to the start of its pendulum, over the enemies (set up a tick early)
  let pivot = up(center, C.pendulumLength + 3.5);
  const swingAxis = rt;
  const swingPos = (deg: number): Vector3 => {
    const r = (deg * Math.PI) / 180;
    return add(pivot, { x: swingAxis.x * C.pendulumLength * Math.sin(r), y: -C.pendulumLength * Math.cos(r), z: swingAxis.z * C.pendulumLength * Math.sin(r) });
  };
  let bedFold = bedPos;
  scene.at(T4 - 1, () => {
    const c = centroid();
    const d = Math.max(distXZ(c, C0), C.clearZone + 4);
    const dir = norm({ x: c.x - C0.x, y: 0, z: c.z - C0.z });
    pivot = { x: C0.x + dir.x * d, y: Math.max(c.y, g0) + C.pendulumLength + 3.5, z: C0.z + dir.z * d };
    bedFold = { ...bedPos };
  });
  hush(T4);
  scene.at(T4, () => {
    dreamer.state(DS.conduct);
    domain.skin(1);
    for (const l of lamps) l.skin(1);
    for (const m of marks.values()) m.a.skin(1);
    sfx("unreality", up(dPos, 8), 1.7);
    if (ward) removeWard(ward);
    dreamZones.concat(nightZones).forEach((z, i) => {   // every zone lifts and folds into the formations, one by one
      const dreamy = dreamZones.includes(z);
      scene.after(i * 3, () => {
        z.a.state(ZONE.fold);
        puff(dreamy ? "bloom" : "ember", up(z.loc, 2), 2.5, 8);
        fx(dreamy ? "dwave" : "nwave", up(z.loc, 0.15));
      });
      const a = z.a;
      scene.after(i * 3 + 26, () => scene.despawn(a));
    });
    for (const z of dreamZones) if (z.kind !== 3) lights.remove(up(z.loc, 2));
    bed.state(BED.fold);
    // signature III -> IV: a nightmare shock wave rolls across the domain and the sky flickers
    fx("nwave", up(center, 0.2)); fx("shock", up(center, 0.25)); fx("flash", up(dPos, 6));
    hoop("nmist", up(center, 0.5), 10, 14);
    hoop("glyph", up(center, 2), 8, 12);
  });
  // ambient IV: loose doors, windows and keys drift across the field; nightmare embers rise from the domain
  layer(T4, T_SLAM + 10, () => {
    times(5, () => fx("glyph", scatter(center, 16, 1, 10)));
    times(8, () => fx("ember", scatter(center, C.radius * 0.85, 0.2, 2.2)));
    times(0.7, () => fx("nmist", scatter(center, C.radius * 0.8, 0.2, 1)));
    times(4, () => fx("ember", scatter(dPos, 4, 1, 11)));
    times(3, () => fx("sparkle", scatter(center, 18, 3, 12)));
    times(2, () => fx("porcelain", scatter(center, C.radius * 0.7, 0.2, 1.5)));   // the ground's architecture flakes up
    times(1, () => fx("mote", scatter(C0, 4.5, 0.1, 0.7)));
  });
  scene.span(T4, T_SWING - 4, (p) => {
    const tgt = swingPos(SWING_A);
    bedPos = bezier(bedFold, up(lerp(bedFold, tgt, 0.5), 8), tgt, smooth(p));
    bed.move(bedPos, faceYaw);
    times(2, () => fx("feather", scatter(bedPos, 3, -2, 1)));
  });

  // strike 1: a wheel of doors assembles at one side and rolls across the field through the marked enemies
  scene.at(T_WHEEL, () => {
    const ts = targets(3).map((t) => clear(t.loc, C.clearZone + 1.5));
    const lat = (p: Vector3): number => (p.x - C0.x) * rt.x + (p.z - C0.z) * rt.z;
    ts.sort((a, b) => lat(b) - lat(a));
    const depth = ts.reduce((s, p) => s + distXZ(p, C0), 0) / Math.max(1, ts.length);
    const start = clear(ground(rel(14, 0, depth)), C.clearZone + 1.5);
    const end = clear(ground(rel(-14, 0, depth + 2)), C.clearZone + 1.5);
    const pts = [start, ...ts, end];
    let len = 0;
    for (let i = 1; i < pts.length; i++) len += distXZ(pts[i - 1], pts[i]);
    const dur = Math.round(clamp(len / C.wheelSpeed, 40, 90));
    const w = scene.spawn("dn_dreamer_wheel", start, { yaw: yawOf(sub(pts[1], start)), state: 1 });
    for (let i = 1; i < pts.length - 1; i++) warn(pts[i], C.wheelRadius, false, 20 + Math.round((dur * i) / pts.length));
    puff("glyph", up(start, 3), 3, 12);
    fx("flash", up(start, 3));
    const hit = new Set<string>();
    scene.after(20, () => { w.state(2); sfx("wheel", start, 1.5); });
    let prev = start;
    scene.span(scene.tick + 20, scene.tick + 20 + dur, (p) => {
      const pos = ground(spline(pts, smooth(p) * 0.3 + p * 0.7));
      const dir = sub(pos, prev);
      w.move(pos, Math.abs(dir.x) + Math.abs(dir.z) > 1e-3 ? yawOf(dir) : undefined);
      prev = pos;
      fx("dust", up(pos, 0.3));
      times(2, () => fx("door", scatter(pos, 1.5, 1.5, 5)));
      times(2, () => fx("streak", scatter(pos, 2, 0.3, 1.5)));
      if (Math.round(p * dur) % 4 === 0) fx("ring", up(pos, 0.1));
      look(pos);
      hitOnce(hit, pos, C.wheelRadius, C.wheelDamage, (e) => shove(e, dir, 1.6, 0.6));
    });
    scene.after(20 + dur, () => { w.state(3); puff("door", up(prev, 3), 2.5, 10); impact(prev, true); });
    scene.after(40 + dur, () => scene.despawn(w));
  });

  // strike 2: the forearm arcades thrust and release window-shards at every mark
  scene.at(T_ARMS - 6, () => {
    const ts = targets(C.shards, 5);
    ts.forEach((t) => warn(t.loc, 1.6, false, 25));
    look(centroid());
    scene.at(T_ARMS, () => dreamer.state(DS.fireArms));
    scene.at(T_ARMS + 13, () => {
      sfx("glass", up(dPos, 6), 1.4);
      ts.forEach((t, i) => {
        const from = atR(dPos, dYaw, [i % 2 ? -ARM[0] : ARM[0], ARM[1], ARM[2]]);
        fx("glint", from); fx("glow", from);
        const s = scene.spawn("dn_dreamer_shard", from, { yaw: yawOf(sub(t.loc, from)), state: 1 });
        const mid = up(lerp(from, t.loc, 0.5), 3);
        scene.span(scene.tick, scene.tick + 12, (p) => {
          const tg = t.e && isAlive(t.e) ? groundBelow(dim, t.e.location) : t.loc;
          const pos = bezier(from, mid, up(tg, 0.8), p);
          s.move(pos);
          fx("glint", pos); fx("trail", pos);
          if (p > 0.95) t.loc = tg;
        });
        scene.after(12, () => {
          s.state(2);
          fx("glint", up(t.loc, 1)); puff("shardbig", up(t.loc, 1), 0.6, 4); fx("ring", up(t.loc, 0.1));
          for (const e of hostiles(dim, t.loc, 1.8, caster)) damage(e, C.shardDamage, caster);
          if (i === 0) sfx("glass", t.loc, 1.2, 1.15);
        });
        scene.after(22, () => scene.despawn(s));
      });
    });
    scene.at(T_ARMS + LEN.fireArms, () => dreamer.state(DS.conduct));
  });

  // strike 3: the golden stairway twists into a spiral drill and bores into the densest group
  scene.at(T_DRILL, () => {
    const tgt = groups(1)[0];
    warn(tgt, C.drillRadius, true, C.warnLong);
    look(tgt);
    const top = up(tgt, 9);
    const d = scene.spawn("dn_dreamer_drill", up(top, 4), { yaw: faceYaw, state: 1 });
    streak("trailbig", up(dPos, 10), up(top, 6), 12);
    scene.span(scene.tick, scene.tick + 20, (p) => d.move(lerp(up(top, 4), top, easeOut(p))));
    scene.after(20, () => { d.state(3); sfx("drill", tgt, 1.5); });
    scene.span(scene.tick + 20, scene.tick + C.warnLong, (p) => {
      const pos = lerp(top, tgt, easeIn(p));
      d.move(pos);
      const a = (scene.tick * 37) % 360;
      times(2, () => fx("streak", add(pos, { x: Math.cos((a * Math.PI) / 180) * 2.2, y: 2 + rnd() * 4, z: Math.sin((a * Math.PI) / 180) * 2.2 })));
      times(2, () => fx("sparkle", scatter(pos, 2, 0, 6)));
    });
    scene.after(C.warnLong, () => {
      impact(tgt, true);
      fx("shock", up(tgt, 0.2));
      for (const e of hostiles(dim, tgt, C.drillRadius, caster)) {
        damage(e, C.drillDamage, caster);
        effect(e, "slowness", 40, 3);
      }
    });
    scene.every(10, () => {
      for (const e of hostiles(dim, tgt, C.drillRadius, caster)) { damage(e, C.drillTick, caster); drag(e, lerp(e.location, up(tgt, 0.1), 0.3)); }
      fx("porcelain", up(tgt, 1)); fx("dust", up(tgt, 0.3));
    }, scene.tick + C.warnLong + 10, scene.tick + C.warnLong + 31);
    scene.span(scene.tick + C.warnLong, scene.tick + C.warnLong + 30, (p) => { d.move(up(tgt, -2.5 * p)); times(2, () => fx("dust", scatter(tgt, 2, 0.2, 0.6))); });
    scene.after(C.warnLong + 30, () => d.state(4));
    scene.after(C.warnLong + 46, () => scene.despawn(d));
  });

  // strike 4: the bed swings through the enemies like a pendulum
  scene.at(T_SWING - C.warnLong, () => {
    for (const a of [-30, -10, 10, 30]) warn(clear(ground(swingPos(a))), 3, true, C.warnLong + 10);
  });
  const swung = new Set<string>();
  scene.at(T_SWING, () => { bed.state(BED.swing); sfx("pendulum", pivot, 1.7); look(swingPos(0)); });
  scene.span(T_SWING, T_SWING + SWING_T, (p) => {
    const th = SWING_A * Math.cos(Math.PI * p);
    bedPos = swingPos(th);
    bed.move(bedPos, faceYaw);
    times(2, () => fx("feather", scatter(bedPos, 2, -1, 1)));
    if (Math.abs(th) < 28) {
      const g = ground(bedPos);
      fx("petal", up(g, 1)); fx("dust", up(g, 0.3)); times(2, () => fx("streak", scatter(bedPos, 2, -1, 1)));
      hitOnce(swung, g, C.pendulumRadius, C.pendulumDamage, (e) => shove(e, mul(swingAxis, -1), 2.0, 0.7));
    }
  });
  scene.at(T_SWING + SWING_T, () => bed.state(BED.hang));
  scene.span(T_SWING + SWING_T, T5, (p) => {            // afterwards it drifts back up and away, rocking
    bedPos = lerp(swingPos(-SWING_A), up(lerp(swingPos(-SWING_A), bedRest, 0.6), 2), smooth(p));
    bed.move(bedPos, faceYaw);
  });

  // strike 5: the chest cabinet fires its little rooms, which unfold round the enemies
  scene.at(T_ROOMS, () => { dreamer.state(DS.fireRooms); sfx("door", atR(dPos, dYaw, CHEST), 1.2, 0.6); look(centroid()); });
  scene.at(T_ROOMS + 12, () => {
    const from = atR(dPos, dYaw, CHEST);
    fx("flash", from);
    targets(C.rooms, 6).forEach((t, i) => {
      const r = scene.spawn("dn_dreamer_roomcube", from, { yaw: faceYaw + i * 40, state: 1 });
      const top = up(lerp(from, t.loc, 0.5), 5);
      scene.span(scene.tick, scene.tick + 16, (p) => {
        if (t.e && isAlive(t.e) && p < 0.8) t.loc = clear(groundBelow(dim, t.e.location), C.clearZone - 1);
        const pos = bezier(from, top, t.loc, p);
        r.move(pos);
        fx("trailbig", pos); fx("sparkle", scatter(pos, 1, 0, 1));
      });
      scene.after(16, () => {
        r.state(2);
        sfx("room", t.loc, 1.1);
        impact(t.loc);
        for (const e of hostiles(dim, t.loc, C.roomRadius, caster)) restrain(scene, e, C.roomHold, { ...e.location });
      });
      scene.after(32, () => {
        r.state(3);
        impact(t.loc, true);
        for (const e of hostiles(dim, t.loc, C.roomRadius + 0.5, caster)) damage(e, C.roomDamage, caster);
      });
      scene.after(42, () => r.state(4));
      scene.after(58, () => scene.despawn(r));
    });
  });
  scene.at(T_ROOMS + LEN.fireRooms, () => dreamer.state(DS.conduct));

  // finale build-up: it turns to the main group and glides in so its beam will land on them; light gathers into
  // its face-door and the riser swells
  let land = ground(at(stage, faceYaw, 0, 0, BEAM_LAND));
  let finFrom = stage, finTo = stage;
  scene.at(T_FIN - 25, () => {
    const c = centroid();
    const want = yawOf(sub(c, stage));
    dYaw = faceYaw + clamp(angleDelta(faceYaw, want), -C.finaleTurn, C.finaleTurn);
    const adv = clamp(distXZ(stage, c) - BEAM_LAND, 0, C.finaleAdvance);
    finFrom = { ...dPos };
    finTo = at(stage, dYaw, 0, 0, adv);
    finTo = { x: finTo.x, y: ground(finTo).y + HOVER_LIFT, z: finTo.z };
    dYaw = faceYaw;
  });
  scene.span(T_FIN - 24, T_FIN, (p) => {
    const c = centroid();
    const want = yawOf(sub(c, stage));
    const yaw = faceYaw + clamp(angleDelta(faceYaw, want), -C.finaleTurn, C.finaleTurn) * smooth(p);
    dYaw = yaw;
    dPos = lerp(finFrom, finTo, smooth(p));
    dreamer.move(dPos, dYaw);
    look();
  });
  scene.at(T_FIN - 24, () => sfx("riser", up(dPos, 8), 1.6));
  layer(T_FIN - 24, T_FIN + 22, (e) => {
    times(3 + e / 9, () => fx("gather", doorAt()));
    fx("glow", doorAt());
    times(1, () => fx("gather", atR(dPos, dYaw, PALM_R)));
    times(1, () => fx("sparkle", scatter(dPos, 6, 2, 12)));
  });
  scene.at(T_FIN, () => {
    doorRel = DOOR_FIN;
    land = clear(ground(at(dPos, dYaw, 0, 0, BEAM_LAND)), C.clearZone + 1);
    dreamer.state(DS.finale);
    warn(land, C.beamRadius, true, LEN.finale + 5);
  });
  scene.at(T_FIN + 8, () => sfx("beam", land, 1.8));
  scene.at(T_FIN + 20, () => { fx("flash", doorAt()); fx("dwave", up(land, 0.2)); puff("moon", up(land, 2), 3, 12); });
  // the other world pours out: starlight and paper moons stream down the beam and swirl round the land point
  layer(T_FIN + 22, T_SLAM, (e) => {
    const a = doorAt();
    times(5, () => fx("beam", lerp(a, up(land, 1), rnd())));
    times(2, () => fx("star", lerp(a, up(land, 1), rnd())));
    const ang = e * 0.35;
    for (let i = 0; i < 4; i++) {
      const rr = C.beamRadius * (0.3 + 0.6 * rnd());
      fx(i % 2 === 0 ? "moon" : "star", { x: land.x + Math.cos(ang + i * 1.57) * rr, y: land.y + 0.5 + rnd() * 2, z: land.z + Math.sin(ang + i * 1.57) * rr });
    }
    if (e % 8 === 0) fx("dwave", up(land, 0.15));
    if (e % 4 === 0) fx("column", up(land, 5));
  });
  scene.every(4, (e) => {
    for (const x of hostiles(dim, land, C.beamRadius, caster)) {
      const d = distXZ(x.location, land);
      if (d > 1.2) {
        const step = mul(norm({ x: land.x - x.location.x, y: 0, z: land.z - x.location.z }), Math.min(C.beamPull * 4, d - 1));
        drag(x, add(x.location, step));
      }
      if (e % 12 === 0) damage(x, C.beamDamage, caster);
    }
  }, T_FIN + 22, T_SLAM);
  // the peak: the door slams shut, both hands strike the ground; flash, shock rings, a storm of porcelain and moons
  scene.at(T_SLAM, () => { dreamer.state(DS.slam); sfx("door", doorAt(), 1.4, 0.55); });
  hush(T_PEAK);
  scene.at(T_PEAK, () => {
    sfx("final", land, 2.0);
    sfx("final", C0, 0.7, 0.8);
    fx("flash", up(land, 2)); fx("flash", doorAt());
    particle(dim, "fx_flash", up(land, 2));
    fx("shock", up(land, 0.2)); fx("dwave", up(land, 0.25)); fx("nwave", up(land, 0.3));
    puff("shardbig", up(land, 2), 3, 14);
    puff("moon", up(land, 2.5), 4, 12);
    puff("streak", up(land, 1), 1.5, 12);
    hoop("dust", up(land, 0.3), 4, 10);
    hoop("star", up(land, 0.5), C.finalRadius, 16);
    for (const s of [-1, 1]) impact(atR(dPos, dYaw, [s * HAND_SLAM[0], 0, HAND_SLAM[2]]), true);
    for (const e of hostiles(dim, land, C.finalRadius, caster)) {
      damage(e, C.finalDamage, caster);
      knockback(e, land, C.finalKnock, 0.6);
    }
  });
  scene.at(T_PEAK + 4, () => { fx("shock", up(land, 0.2)); hoop("ring", up(land, 0.15), C.finalRadius * 0.6, 8); });
  scene.at(T_PEAK + 9, () => { fx("dwave", up(land, 0.2)); hoop("mist", up(land, 0.5), 6, 12); });
  // aftermath: dust settling, porcelain flakes and stars drifting down over the field
  layer(T_PEAK + 1, T5 + 40, (e) => {
    times(e < 20 ? 6 : 3, () => fx("shardbig", scatter(land, 7, 2, 10)));
    times(2, () => fx("star", scatter(land, 9, 0.5, 6)));
    times(0.5, () => fx("mist", scatter(land, 7, 0.2, 1.2)));
    times(e < 20 ? 3 : 1, () => fx("dust", scatter(land, 6, 0.2, 0.6)));
  });

  // ================================================================ PHASE V - The Forgotten Morning
  scene.at(T5, () => {
    dreamer.state(DS.forget).skin(0);
    dreamer.prop("look", 0);
    sfx("break", up(dPos, 8), 1.6);
    sfx("after", C0, 1.0);
    bed.state(BED.vanish);
    puff("feather", bedPos, 4, 16);
    let i = 0;
    for (const m of marks.values()) { const a = m.a; scene.after(i * 3, () => a.state(3)); scene.after(i * 3 + 9, () => scene.despawn(a)); i++; }
  });
  layer(T5, T5 + 52, () => { times(3, () => fx("feather", scatter(bedPos, 3, -1, 1))); times(2, () => fx("star", scatter(bedPos, 3, -1, 2))); });
  layer(T5, T5 + 100, (e) => {               // the porcelain panels drift apart and up, glinting
    times(e < 50 ? 5 : 2, () => fx("shardbig", scatter(dPos, 5, 2, 12)));
    times(1.5, () => fx("porcelain", scatter(dPos, 4, 4, 12)));
    times(2, () => fx("sparkle", scatter(dPos, 6, 1, 12)));
  });
  layer(T5, T_END, (e) => {                  // the morning: warm motes rise over the field, fading toward the end
    times(e < 60 ? 10 : e < 100 ? 6 : 3, () => fx("morning", scatter(lerp(C0, center, 0.6), 13, 0.2, 2.8)));
    times(e < 80 ? 2 : 1, () => fx("sparkle", scatter(lerp(C0, center, 0.5), 12, 1, 8)));
    times(e < 60 ? 1.5 : 0.5, () => fx("petal", scatter(lerp(C0, center, 0.5), 10, 2, 6)));
  });
  scene.at(T5 + 52, () => scene.despawn(bed));
  scene.at(T5 + 10, () => { domain.state(3); codex.state(CODEX.gather); });
  scene.at(T5 + 42, () => scene.despawn(domain));
  scene.at(T5 + 14, () => {                  // the lamps sink one after another
    lamps.forEach((l, k) => {
      scene.after(k * 4, () => { l.state(LAMP.sink); fx("glow", up(l.loc, 6)); });
      scene.after(k * 4 + 22, () => scene.despawn(l));
    });
  });
  scene.at(T5 + 24, () => sfx("morning", C0, 1.0));
  scene.at(T_ROOM, () => {                    // the whole dream shrinks into one little bedroom that flies to the book
    const from = atR(dPos, dYaw, CHEST);
    const room = scene.spawn("dn_dreamer_bedroom", from, { yaw: faceYaw, size: 5, state: 1 });
    fx("flash", from); puff("star", from, 3, 12);
    scene.after(16, () => room.state(2));
    const fromSize = 5;
    scene.span(scene.tick + 18, T_CLOSE - 2, (p) => {
      const b = bookAt();
      const mid = add(up(lerp(from, b, 0.55), 7), mul(rt, -4));
      const e = smooth(p);
      room.move(bezier(from, mid, up(b, 0.35), e)).size(fromSize + (0.3 - fromSize) * Math.min(1, e * 1.25));
      times(2, () => fx("trail", room.loc));
      times(1, () => fx("morning", room.loc));
    });
    scene.at(T_CLOSE - 2, () => room.state(3));
    scene.at(T_CLOSE + 16, () => scene.despawn(room));
  });
  scene.at(T5 + LEN.forget, () => scene.despawn(dreamer));
  scene.at(T_CLOSE, () => { codex.state(CODEX.close); const b = bookAt(); fx("glow", b); puff("sparkle", b, 0.5, 8); });
  scene.at(T_CLOSE + 22, () => { sfx("click", bookAt(), 0.8); fx("star", bookAt()); });
  scene.at(T_CLOSE + 40, () => puff("morning", bookAt(), 0.6, 6));
  scene.endAt(T_END);
});
