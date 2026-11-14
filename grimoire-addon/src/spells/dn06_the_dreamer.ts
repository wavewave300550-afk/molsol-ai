import { Entity, Vector3 } from "@minecraft/server";
import { DN06 as C } from "../config/dn06";
import { defineSpell } from "../core/registry";
import { addWard, damage, drag, effect, heal, knockback, restrain, shove, Ward, removeWard } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import {
  add, angleDelta, bezier, clamp, dist, distXZ, fromYaw, lerp, mul, norm, polar, right, smooth, spline, sub, up, yawOf,
} from "../lib/vec";

// ---- animation states (tools/assets/dn_dreamer*.py) -------------------------------------------
const DS = { hidden: 0, manifest: 1, sit: 2, awaken: 3, rise: 4, hover: 5, sweep: 6, cabinet: 7, raise: 8, conjure: 9,
  conduct: 10, fireArms: 11, fireRooms: 12, finale: 13, slam: 14, forget: 15 };
const BED = { arrive: 1, float: 2, occupied: 3, dip: 4, empty: 5, fold: 6, swing: 7, vanish: 8 };
const CODEX = { open: 1, hold: 2, gather: 3, close: 4 };
const ZONE = { bloom: 1, idle: 2, fold: 3, fade: 4, bite: 5 };
const TG = { warn: 1, hold: 2, flash: 3, warnSlow: 4 };

// ---- animation lengths and geometry probes (dn_dreamer.py LEN / report(); blocks) -------------
const LEN = { manifest: 90, sit: 60, awaken: 30, rise: 60, sweep: 60, cabinet: 40, raise: 40, fireArms: 32,
  fireRooms: 32, finale: 60, slam: 20, forget: 100 };
/** Dreamer origin (pelvis) relative to the bed's mattress-top origin while lying: forward toward the foot, up. */
const LIE = { fwd: 1.67, up: 1.0 };
/** Fingertip during the sweep hit window (1.25 s .. 2.0 s): [right, up, forward] from the pelvis. */
const SWEEP_PATH: [number, number, number][] = [[11.88, -11.35, 11.29], [8.8, -12.59, 12.67], [2.43, -13.84, 14.05],
  [-4.19, -13.67, 13.78], [-7.61, -12.98, 12.95]];
const SWEEP_HIT = [25, 40];
const CHEST = { up: 7.8, fwd: 5.1 };            // cabinet front while firing rooms
const ARM = { right: 4.2, up: 5.9, fwd: 17.2 };  // forearm arcades at the thrust
const BEAM_LAND = 11.84;                          // where the face-door beam meets the ground (forward)
const BED_PILLOW = { right: 2.75, fwd: -6.5, up: 0.75 };
const BOOK = { right: -0.94, up: 1.5, fwd: 0.81 };
const SWING_T = 48;                               // dn_dreamer_bed.py SWING_T (2.4 s)
const SWING_A = 58;
const STEP_LAND = (k: number) => 8 + Math.round(k * 2.4);   // stairs: tick each step lands after spawn

/**
 * DN06 - The Dreamer Who Never Wakes (Extra Ultimate, ~63 s).
 * I  The Bed Above the Sky   - domain, the Codex opens into paper structures, the bed drifts in, enemies are marked.
 * II The Sleeper Rises       - the Dreamer manifests in the bed, sits up (pillow drops), opens its face-door,
 *                               leaves the bed at colossal size, rakes the ground, spills stairs from its chest.
 * III Dream / Nightmare Zones - right hand seeds healing dream zones by allies, left hand seeds hostile nightmare
 *                               zones on enemy groups; both run at once.
 * IV The Great Unreality     - zones and bed fold into formations: wheel of doors, window shards, stair drill,
 *                               bed pendulum, room-cubes; finale: the face-door pours its world out, then slams.
 * V  The Forgotten Morning   - the Dreamer breaks into panels, everything shrinks into a miniature bedroom that
 *                               settles into the Codex cover; the book closes.
 */
export default defineSpell("dn06", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 14);
  const fwd = norm({ x: aim.forward.x, y: 0, z: aim.forward.z });
  const g0 = center.y;
  const lights = blocksFor(scene);
  const faceYaw = yawOf(mul(fwd, -1));             // the bed and the Dreamer face the caster
  const at = (base: Vector3, yaw: number, r: number, u: number, f: number): Vector3 => {
    const fd = fromYaw(yaw), rt = right(fd);
    return { x: base.x + rt.x * r + fd.x * f, y: base.y + u, z: base.z + rt.z * r + fd.z * f };
  };
  const ground = (p: Vector3): Vector3 => groundBelow(dim, { x: p.x, y: Math.max(p.y, g0 + 4), z: p.z }, 50);

  // ---------------------------------------------------------------- marks & targets
  const marks = new Map<string, { e: Entity; a: Actor }>();
  function markNew(limit = C.maxMarks): void {
    for (const e of hostiles(dim, center, C.radius, caster)) {
      if (marks.size >= limit) break;
      if (marks.has(e.id)) continue;
      const a = scene.spawn("dn_dreamer_mark", up(e.location, 2.5), { state: 1 });
      scene.follow(a, e, 2.5);
      scene.after(10, () => a.state(2));
      marks.set(e.id, { e, a });
      sound(dim, "dn_dreamer_mark", e.location, 0.6, 0.9 + marks.size * 0.06);
      particle(dim, "dn_dreamer_moon", up(e.location, 2.5));
      return;   // one at a time: marks land one by one like falling asleep
    }
  }
  function marked(): Entity[] {
    const out: Entity[] = [];
    for (const m of marks.values()) if (isAlive(m.e) && distXZ(m.e.location, center) < C.radius + 6) out.push(m.e);
    if (out.length) return out;
    return hostiles(dim, center, C.radius, caster);
  }
  /** n target points: marked enemies first, otherwise a ring inside the domain (spell works with no enemies). */
  function targets(n: number, spread = 7): { loc: Vector3; e?: Entity }[] {
    const es = marked();
    const out: { loc: Vector3; e?: Entity }[] = [];
    for (let i = 0; i < n; i++) {
      if (es.length) { const e = es[i % es.length]; out.push({ loc: groundBelow(dim, e.location), e }); }
      else out.push({ loc: ground(polar(center, i === 0 ? 0 : spread, i * (360 / Math.max(1, n - 1)) + 20)) });
    }
    return out;
  }
  /** Up to n group centres of the marked enemies (greedy clustering). */
  function groups(n: number): Vector3[] {
    const es = marked();
    const out: Vector3[] = [];
    for (const e of es) {
      if (out.length >= n) break;
      if (out.every((c) => distXZ(c, e.location) > C.zoneRadius * 1.5)) out.push(groundBelow(dim, e.location));
    }
    const base = out.length ? out[0] : center;
    for (let i = out.length; i < n; i++) out.push(ground(polar(base, 7, i * 120 + yawOf(fwd))));
    return out;
  }
  function centroid(): Vector3 {
    const es = marked();
    if (!es.length) return center;
    let s = { x: 0, y: 0, z: 0 };
    for (const e of es) s = add(s, e.location);
    return groundBelow(dim, mul(s, 1 / es.length));
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

  // ================================================================ PHASE I - The Bed Above the Sky (0-150)
  const domain = scene.spawn("dn_dreamer_domain", up(center, 0.05), { size: C.radius / 2, state: 1 });
  scene.at(32, () => domain.state(2));
  lights.place(up(center, 2), LIGHT);
  const codex = scene.spawn("dn_dreamer_codex", caster.location, { yaw: aim.yaw, state: CODEX.open });
  scene.follow(codex, caster, 0);
  scene.at(60, () => codex.state(CODEX.hold));
  sound(dim, "dn_dreamer_book", caster.location, 0.9);
  sound(dim, "dn_dreamer_musicbox", caster.location, 0.8);
  const bedRest = up(add(center, mul(fwd, C.bedBack)), C.bedHeight);
  const bedFrom = up(add(center, mul(fwd, C.bedBack + 18)), C.bedHeight + 14);
  const bedMid = up(add(add(center, mul(fwd, C.bedBack + 6)), mul(right(fwd), 10)), C.bedHeight + 10);
  let bedPos = { ...bedFrom };
  const bed = scene.spawn("dn_dreamer_bed", bedFrom, { yaw: faceYaw, state: BED.arrive });
  sound(dim, "dn_dreamer_bed", bedFrom, 1.0);
  scene.span(0, 50, (p) => { bedPos = bezier(bedFrom, bedMid, bedRest, smooth(p)); bed.move(bedPos, faceYaw); });
  scene.at(50, () => bed.state(BED.float));
  scene.every(8, () => markNew(), 40, 140);
  scene.every(6, (e) => {
    particle(dim, "dn_dreamer_mote", up(polar(center, 6 + (e % 4) * 3, e * 23), 2));
    if (e % 12 === 0) particle(dim, "dn_dreamer_petal", up(bedPos, 3));
  }, 0, 760);
  scene.at(100, () => { burst(dim, "dn_dreamer_star", up(bedPos, 4), 6, 6); sound(dim, "dn_dreamer_breath", bedPos, 0.9); });
  scene.every(40, () => markNew(), 150, 760);      // newcomers are marked as they enter the domain

  // ================================================================ PHASE II - The Sleeper Rises (150-520)
  const T2 = 150;
  const lieAt = (): Vector3 => at(bedPos, faceYaw, 0, LIE.up, LIE.fwd);
  let dreamer = new Actor(undefined, "grimoire:dreamer");
  let dPos = lieAt();
  let dYaw = faceYaw;
  scene.at(T2, () => {
    dPos = lieAt();
    dreamer = scene.spawn("dreamer", dPos, { yaw: faceYaw, state: DS.manifest });
    bed.state(BED.occupied);
    sound(dim, "dn_dreamer_manifest", dPos, 1.2);
    sound(dim, "dn_dreamer_breath", dPos, 1.0, 0.8);
  });
  scene.every(15, (e) => particle(dim, "dn_dreamer_porcelain", at(bedPos, faceYaw, 0, 1.5, 6 - e / 15 * 2.2)), T2, T2 + 90);

  // sits up; the bed takes its weight and a pillow slides off onto an enemy
  const T_SIT = T2 + LEN.manifest;
  scene.at(T_SIT, () => {
    dreamer.state(DS.sit); bed.state(BED.dip);
    sound(dim, "dn_dreamer_groan", dPos, 1.3); sound(dim, "dn_dreamer_inhale", dPos, 1.1);
  });
  scene.span(T_SIT, T_SIT + 20, (p) => dreamer.move(up(lieAt(), -1.25 * smooth(p)), faceYaw));
  const pillowTarget = targets(1)[0];
  let pLand = pillowTarget.loc;
  scene.at(T_SIT + 10, () => {
    pLand = targets(1)[0].loc;
    const w = warn(pLand, C.pillowRadius, true, C.warnLong);
    const from = at(bedPos, faceYaw, BED_PILLOW.right, BED_PILLOW.up - 1.2, BED_PILLOW.fwd);
    const pil = scene.spawn("dn_dreamer_pillow", from, { yaw: faceYaw, state: 1 });
    const top = up(lerp(from, pLand, 0.35), 4);
    scene.span(scene.tick, scene.tick + C.warnLong, (p) => {
      const tgt = pillowTarget.e && isAlive(pillowTarget.e) && p < 0.7 ? groundBelow(dim, pillowTarget.e.location) : pLand;
      pLand = tgt; w.move(up(tgt, 0.05));
      pil.move(bezier(from, top, tgt, p * p));
    });
    scene.after(C.warnLong, () => {
      pil.state(2);
      sound(dim, "dn_dreamer_pillow", pLand, 1.2);
      burst(dim, "dn_dreamer_feather", up(pLand, 1), 2.5, 8);
      particle(dim, "dn_dreamer_dust", up(pLand, 0.3));
      particle(dim, "dn_dreamer_ring", up(pLand, 0.2));
      hitOnce(new Set(), pLand, C.pillowRadius, C.pillowDamage, (e) => knockback(e, pLand, C.pillowKnock, 0.45));
      scene.after(14, () => pil.state(3));
      scene.after(32, () => scene.despawn(pil));
    });
  });

  // awakens: the head turns toward the enemies and the small door in its face opens
  const T_AWAKE = T_SIT + LEN.sit;
  scene.at(T_AWAKE, () => {
    dreamer.state(DS.awaken);
    sound(dim, "dn_dreamer_door", dPos, 1.2);
    sound(dim, "dn_dreamer_hum", dPos, 1.2);
  });
  scene.at(T_AWAKE + 22, () => burst(dim, "dn_dreamer_star", up(dPos, 4), 2, 8));

  // rises out of the bed and grows to its full height
  const T_RISE = T_AWAKE + LEN.awaken;
  const hover = up(add(center, mul(fwd, C.hoverBack)), C.hoverHeight);
  scene.at(T_RISE, () => {
    dreamer.state(DS.rise); bed.state(BED.empty);
    sound(dim, "dn_dreamer_groan", dPos, 1.5, 0.85); sound(dim, "dn_dreamer_inhale", dPos, 1.3, 0.8);
  });
  scene.span(T_RISE + 12, T_RISE + LEN.rise, (p) => {
    const a = up(lieAt(), -1.25);
    dPos = bezier(a, up(lerp(a, hover, 0.5), 5), hover, smooth(p));
    dreamer.move(dPos, faceYaw);
    if (Math.round(p * 48) % 8 === 0) particle(dim, "dn_dreamer_porcelain", up(dPos, 6));
  });
  const T_HOV = T_RISE + LEN.rise;
  scene.at(T_HOV, () => { dPos = hover; dreamer.move(hover, faceYaw).state(DS.hover); });

  // hand sweep across the ground (telegraphed arc, damage + knockback where the hand passes)
  const T_SWEEP = T_HOV + 10;
  const sweepPt = (i: number): Vector3 => { const s = SWEEP_PATH[i]; return at(hover, faceYaw, s[0], s[1], s[2]); };
  scene.at(T_SWEEP - C.warnLong + SWEEP_HIT[0] - 5, () => {
    for (let i = 0; i < SWEEP_PATH.length; i++) warn(ground(sweepPt(i)), C.sweepRadius, true, C.warnLong + 5 + i * 3);
  });
  scene.at(T_SWEEP, () => dreamer.state(DS.sweep));
  scene.at(T_SWEEP + 18, () => sound(dim, "dn_dreamer_sweep", ground(sweepPt(2)), 1.5));
  const swept = new Set<string>();
  scene.span(T_SWEEP + SWEEP_HIT[0], T_SWEEP + SWEEP_HIT[1], (p) => {
    const f = p * (SWEEP_PATH.length - 1);
    const i = Math.min(Math.floor(f), SWEEP_PATH.length - 2);
    const hand = ground(lerp(sweepPt(i), sweepPt(i + 1), f - i));
    const along = norm(sub(sweepPt(i + 1), sweepPt(i)));
    particle(dim, "dn_dreamer_dust", up(hand, 0.3));
    hitOnce(swept, hand, C.sweepRadius, C.sweepDamage, (e) => shove(e, along, C.sweepKnock, 0.5));
  });
  scene.at(T_SWEEP + LEN.sweep, () => dreamer.state(DS.hover));

  // the chest cabinet opens and a staircase spills out across the ground
  const T_CAB = T_SWEEP + LEN.sweep + 4;
  const stairFrom = ground(at(hover, faceYaw, 0, 0, 4));
  let stairDir = fwd;
  scene.at(T_CAB - 6, () => {
    const t = targets(1)[0].loc;
    stairDir = norm({ x: t.x - stairFrom.x, y: 0, z: t.z - stairFrom.z });
    for (let k = 0; k < 10; k += 3) warn(ground(add(stairFrom, mul(stairDir, 0.6 + k * 1.25))), C.stairsRadius, false, 20 + k * 2);
  });
  scene.at(T_CAB, () => { dreamer.state(DS.cabinet); sound(dim, "dn_dreamer_door", up(hover, 8), 1.0, 0.7); });
  scene.at(T_CAB + 10, () => {
    line(dim, "dn_dreamer_trail", at(hover, faceYaw, 0, CHEST.up, CHEST.fwd), up(stairFrom, 4), 6);
    const st = scene.spawn("dn_dreamer_stairs", stairFrom, { yaw: yawOf(stairDir), state: 1 });
    sound(dim, "dn_dreamer_stairs", stairFrom, 1.2);
    const hit = new Set<string>();
    for (let k = 0; k < 10; k++) {
      scene.after(STEP_LAND(k), () => {
        const p = ground(add(stairFrom, mul(stairDir, 0.62 + k * 1.25)));
        if (k % 2 === 0) particle(dim, "dn_dreamer_dust", up(p, 0.2));
        hitOnce(hit, p, C.stairsRadius, C.stairsDamage, (e) => shove(e, stairDir, 0.8, 0.35));
      });
    }
    scene.after(50, () => st.state(2));
    scene.after(72, () => scene.despawn(st));
  });
  scene.at(T_CAB + LEN.cabinet + 8, () => dreamer.state(DS.hover));

  // ================================================================ PHASE III - Dream Zones / Nightmare Zones
  const T3 = T_CAB + LEN.cabinet + 16;
  const dreamZones: { a: Actor; loc: Vector3; kind: number }[] = [];
  const nightZones: { a: Actor; loc: Vector3; kind: number }[] = [];
  let ward: Ward | undefined;
  scene.at(T3, () => {
    dreamer.state(DS.raise).skin(1);          // porcelain splits: the nightmare beneath begins to show
    sound(dim, "dn_dreamer_raise", up(hover, 10), 1.4);
  });
  scene.at(T3 + 25, () => {                    // right hand: dream zones beside allies
    const fr = allies(dim, caster.location, 24, caster);
    const spots: Vector3[] = [];
    if (fr.length > 1) for (const a of fr.slice(0, 3)) spots.push(groundBelow(dim, a.location));
    const cl = groundBelow(dim, caster.location);
    if (!spots.length) spots.push(cl);
    const cy = yawOf(fwd);
    while (spots.length < 3) spots.push(ground(polar(cl, 6, cy + 90 + (spots.length === 1 ? 10 : 160) + 90)));
    const hand = at(hover, faceYaw, -2, 26, 6);
    spots.forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_dream", loc, { kind: i, yaw: faceYaw, state: ZONE.bloom });
      dreamZones.push({ a, loc, kind: i });
      line(dim, "dn_dreamer_trail", hand, up(loc, 3), 8);
      ring(dim, "dn_dreamer_petal", up(loc, 1), C.zoneRadius, 6, i * 30);
      lights.place(up(loc, 2), LIGHT);
      scene.after(30, () => a.state(ZONE.idle));
    });
    sound(dim, "dn_dreamer_bloom", cl, 1.0);
    ward = addWard({
      scene, factor: C.wardFactor, pool: C.wardPool,
      protects: (e) => e.typeId === "minecraft:player" && dreamZones.some((z) => distXZ(z.loc, e.location) <= C.zoneRadius),
      onAbsorb: (_n, _a, v) => particle(dim, "dn_dreamer_ring", up(v.location, 0.2)),
    });
  });
  scene.at(T3 + 35, () => {                    // left hand: nightmare zones on enemy groups
    const hand = at(hover, faceYaw, 2, 26, 6);
    groups(3).forEach((loc, i) => {
      const a = scene.spawn("dn_dreamer_night", loc, { kind: i, yaw: yawOf(sub(hover, loc)), state: ZONE.bloom });
      nightZones.push({ a, loc, kind: i });
      line(dim, "dn_dreamer_ntrail", hand, up(loc, 3), 8);
      particle(dim, "dn_dreamer_smoke", up(loc, 0.5));
      scene.after(30, () => a.state(ZONE.idle));
    });
    sound(dim, "dn_dreamer_emerge", nightZones.length ? nightZones[0].loc : center, 1.2);
  });
  scene.at(T3 + LEN.raise, () => dreamer.state(DS.conjure));
  const ZONE_FROM = T3 + 70, ZONE_TO = T3 + 250;
  scene.every(C.zonePulse, (e) => {            // dream pulses: heal, ward, supportive effect
    for (const z of dreamZones) {
      particle(dim, "dn_dreamer_heal", up(z.loc, 0.5));
      if ((e / C.zonePulse) % 2 === 0) particle(dim, "dn_dreamer_key", up(z.loc, 4));
      for (const p of allies(dim, z.loc, C.zoneRadius, caster)) {
        if (heal(p, C.dreamHeal) > 0) sound(dim, "dn_dreamer_heal", p.location, 0.5, 1 + z.kind * 0.1);
        if (z.kind === 0) effect(p, "regeneration", C.dreamEffectTicks, 0);
        else if (z.kind === 1) { effect(p, "resistance", C.dreamEffectTicks, 0); effect(p, "slow_falling", C.dreamEffectTicks, 0); }
        else { effect(p, "speed", C.dreamEffectTicks, 1); effect(p, "jump_boost", C.dreamEffectTicks, 0); }
      }
    }
    if ((e / C.zonePulse) % 2 === 0 && dreamZones.length) sound(dim, "dn_dreamer_sweet", dreamZones[0].loc, 0.7);
  }, ZONE_FROM, ZONE_TO);
  scene.every(C.zonePulse, (e) => {            // nightmare pulses, interleaved half a pulse later
    const big = (e / C.zonePulse) % 2 === 1;
    for (const z of nightZones) {
      particle(dim, big ? "dn_dreamer_eye" : "dn_dreamer_nring", up(z.loc, big ? 2 : 0.2));
      if (big) { z.a.state(ZONE.bite); scene.after(14, () => z.a.state(ZONE.idle)); sound(dim, "dn_dreamer_bite", z.loc, 0.9); }
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
    if (!big && nightZones.length) sound(dim, "dn_dreamer_sour", nightZones[0].loc, 0.7);
  }, ZONE_FROM + C.zonePulse / 2, ZONE_TO);

  // ================================================================ PHASE IV - The Great Unreality
  const T4 = ZONE_TO + 10;
  scene.at(T4, () => {
    dreamer.state(DS.conduct);
    domain.skin(1);
    for (const m of marks.values()) m.a.skin(1);
    sound(dim, "dn_dreamer_unreality", up(hover, 8), 1.6);
    if (ward) removeWard(ward);
    for (const z of [...dreamZones, ...nightZones]) { z.a.state(ZONE.fold); const a = z.a; scene.after(26, () => scene.despawn(a)); }
    for (const z of dreamZones) lights.remove(up(z.loc, 2));
    bed.state(BED.fold);
  });
  // the bed folds into a cradle and lifts to the start of its pendulum
  const pivot = up(center, C.pendulumLength + 6.5);
  const swingAxis = right(fromYaw(faceYaw));
  const swingPos = (deg: number): Vector3 => {
    const r = (deg * Math.PI) / 180;
    return add(pivot, { x: swingAxis.x * C.pendulumLength * Math.sin(r), y: -C.pendulumLength * Math.cos(r), z: swingAxis.z * C.pendulumLength * Math.sin(r) });
  };
  scene.span(T4, T4 + 70, (p) => { bedPos = lerp(bedRest, swingPos(SWING_A), smooth(p)); bed.move(bedPos, faceYaw); });

  // strike 1: a wheel of doors rolls through the marked enemies
  const T_WHEEL = T4 + 20;
  scene.at(T_WHEEL, () => {
    const start = nightZones.length ? nightZones[nightZones.length - 1].loc : ground(polar(center, 9, yawOf(fwd)));
    const pts = [start, ...targets(3).map((t) => t.loc)];
    const last = pts[pts.length - 1];
    pts.push(ground(add(last, mul(norm(sub(last, pts[pts.length - 2])), 6))));
    let len = 0;
    for (let i = 1; i < pts.length; i++) len += distXZ(pts[i - 1], pts[i]);
    const dur = Math.round(clamp(len / C.wheelSpeed, 40, 90));
    const w = scene.spawn("dn_dreamer_wheel", start, { yaw: yawOf(sub(pts[1], start)), state: 1 });
    for (let i = 1; i < pts.length - 1; i++) warn(pts[i], C.wheelRadius, false, 20 + Math.round((dur * i) / pts.length));
    const hit = new Set<string>();
    scene.after(20, () => { w.state(2); sound(dim, "dn_dreamer_wheel", start, 1.4); });
    let prev = start;
    scene.span(scene.tick + 20, scene.tick + 20 + dur, (p) => {
      const pos = ground(spline(pts, p));
      const dir = sub(pos, prev);
      w.move(pos, Math.abs(dir.x) + Math.abs(dir.z) > 1e-3 ? yawOf(dir) : undefined);
      prev = pos;
      if (Math.round(p * dur) % 6 === 0) particle(dim, "dn_dreamer_door", up(pos, 1.5));
      hitOnce(hit, pos, C.wheelRadius, C.wheelDamage, (e) => shove(e, dir, 1.6, 0.6));
    });
    scene.after(20 + dur, () => { w.state(3); burst(dim, "dn_dreamer_door", up(prev, 3), 2.5, 6); });
    scene.after(40 + dur, () => scene.despawn(w));
  });

  // strike 2: the forearm arcades release window-shards at every mark
  const T_ARMS = T_WHEEL + 50;
  scene.at(T_ARMS - 6, () => {
    const ts = targets(C.shards, 5);
    ts.forEach((t) => warn(t.loc, 1.6, false, 25));
    scene.at(T_ARMS, () => dreamer.state(DS.fireArms));
    scene.at(T_ARMS + 13, () => {
      sound(dim, "dn_dreamer_glass", up(hover, 6), 1.3);
      ts.forEach((t, i) => {
        const from = at(hover, faceYaw, i % 2 ? -ARM.right : ARM.right, ARM.up, ARM.fwd * 0.6);
        const s = scene.spawn("dn_dreamer_shard", from, { yaw: yawOf(sub(t.loc, from)), state: 1 });
        const mid = up(lerp(from, t.loc, 0.5), 3);
        scene.span(scene.tick, scene.tick + 12, (p) => {
          const tg = t.e && isAlive(t.e) ? groundBelow(dim, t.e.location) : t.loc;
          s.move(bezier(from, mid, up(tg, 0.8), p));
          if (p > 0.95) t.loc = tg;
        });
        scene.after(12, () => {
          s.state(2);
          particle(dim, "dn_dreamer_glint", up(t.loc, 1));
          for (const e of hostiles(dim, t.loc, 1.8, caster)) damage(e, C.shardDamage, caster);
          if (i === 0) sound(dim, "dn_dreamer_glass", t.loc, 1.2, 1.15);
        });
        scene.after(22, () => scene.despawn(s));
      });
    });
    scene.at(T_ARMS + LEN.fireArms, () => dreamer.state(DS.conduct));
  });

  // strike 3: the golden stairway twists into a spiral drill above the densest group
  const T_DRILL = T_ARMS + 40;
  scene.at(T_DRILL, () => {
    const tgt = groups(1)[0];
    warn(tgt, C.drillRadius, true, C.warnLong);
    const top = up(tgt, 16);
    const d = scene.spawn("dn_dreamer_drill", top, { yaw: faceYaw, state: 1 });
    line(dim, "dn_dreamer_trail", up(hover, 20), up(top, 10), 6);
    scene.after(20, () => { d.state(3); sound(dim, "dn_dreamer_drill", tgt, 1.4); });
    scene.span(scene.tick + 20, scene.tick + C.warnLong, (p) => d.move(lerp(top, tgt, p * p)));
    scene.after(C.warnLong, () => {
      particle(dim, "dn_dreamer_shock", up(tgt, 0.2));
      particle(dim, "dn_dreamer_dust", up(tgt, 0.3));
      for (const e of hostiles(dim, tgt, C.drillRadius, caster)) {
        damage(e, C.drillDamage, caster);
        effect(e, "slowness", 40, 3);
      }
    });
    scene.every(10, () => {
      for (const e of hostiles(dim, tgt, C.drillRadius, caster)) { damage(e, C.drillTick, caster); drag(e, lerp(e.location, up(tgt, 0.1), 0.3)); }
      particle(dim, "dn_dreamer_porcelain", up(tgt, 1));
    }, scene.tick + C.warnLong + 10, scene.tick + C.warnLong + 31);
    scene.span(scene.tick + C.warnLong, scene.tick + C.warnLong + 30, (p) => d.move(up(tgt, -2.5 * p)));
    scene.after(C.warnLong + 30, () => d.state(4));
    scene.after(C.warnLong + 46, () => scene.despawn(d));
  });

  // strike 4: the bed swings through the enemies like a pendulum
  const T_SWING = T_DRILL + 70;
  scene.at(T_SWING - C.warnLong, () => {
    for (const a of [-30, -10, 10, 30]) warn(ground(swingPos(a)), 3, true, C.warnLong + 10);
  });
  const swung = new Set<string>();
  scene.at(T_SWING, () => { bed.state(BED.swing); sound(dim, "dn_dreamer_pendulum", pivot, 1.6); });
  scene.span(T_SWING, T_SWING + SWING_T, (p) => {
    const th = SWING_A * Math.cos(Math.PI * p);
    bedPos = swingPos(th);
    bed.move(bedPos, faceYaw);
    if (Math.abs(th) < 26) {
      const g = ground(bedPos);
      particle(dim, "dn_dreamer_petal", up(g, 1));
      hitOnce(swung, g, C.pendulumRadius, C.pendulumDamage, (e) => shove(e, mul(swingAxis, -1), 2.0, 0.7));
    }
  });

  // strike 5: the chest cabinet fires its little rooms, which unfold around the enemies
  const T_ROOMS = T_SWING + 14;
  scene.at(T_ROOMS, () => { dreamer.state(DS.fireRooms); sound(dim, "dn_dreamer_door", up(hover, 8), 1.2, 0.6); });
  scene.at(T_ROOMS + 12, () => {
    const from = at(hover, faceYaw, 0, CHEST.up, CHEST.fwd);
    targets(C.rooms, 6).forEach((t, i) => {
      const r = scene.spawn("dn_dreamer_roomcube", from, { yaw: faceYaw + i * 40, state: 1 });
      const top = up(lerp(from, t.loc, 0.5), 4);
      scene.span(scene.tick, scene.tick + 16, (p) => {
        if (t.e && isAlive(t.e) && p < 0.8) t.loc = groundBelow(dim, t.e.location);
        r.move(bezier(from, top, t.loc, p));
      });
      scene.after(16, () => {
        r.state(2);
        sound(dim, "dn_dreamer_room", t.loc, 1.1);
        for (const e of hostiles(dim, t.loc, C.roomRadius, caster)) restrain(scene, e, C.roomHold, { ...e.location });
      });
      scene.after(32, () => {
        r.state(3);
        particle(dim, "dn_dreamer_dust", up(t.loc, 0.3));
        for (const e of hostiles(dim, t.loc, C.roomRadius + 0.5, caster)) damage(e, C.roomDamage, caster);
      });
      scene.after(42, () => r.state(4));
      scene.after(58, () => scene.despawn(r));
    });
  });
  scene.at(T_ROOMS + LEN.fireRooms, () => dreamer.state(DS.conduct));

  // finale: the face-door opens fully and the other world pours out, pulling enemies in, then slams
  const T_FIN = T_ROOMS + LEN.fireRooms + 18;
  let land = ground(at(hover, faceYaw, 0, 0, BEAM_LAND));
  scene.span(T_FIN - 18, T_FIN, (p) => {
    const want = yawOf(sub(centroid(), hover));
    const turn = clamp(angleDelta(faceYaw, want), -C.finaleTurn, C.finaleTurn);
    dYaw = faceYaw + turn * smooth(p);
    dreamer.move(hover, dYaw);
  });
  scene.at(T_FIN, () => {
    land = ground(at(hover, dYaw, 0, 0, BEAM_LAND));
    dreamer.state(DS.finale);
    warn(land, C.beamRadius, true, LEN.finale + 5);
  });
  scene.at(T_FIN + 8, () => sound(dim, "dn_dreamer_beam", land, 1.7));
  scene.every(4, (e) => {
    particle(dim, "dn_dreamer_beam", up(land, 12));
    if (e % 8 === 0) burst(dim, "dn_dreamer_moon", up(land, 2), C.beamRadius * 0.5, 3);
    for (const x of hostiles(dim, land, C.beamRadius, caster)) {
      const d = distXZ(x.location, land);
      if (d > 1.2) {
        const step = mul(norm({ x: land.x - x.location.x, y: 0, z: land.z - x.location.z }), Math.min(C.beamPull * 4, d - 1));
        drag(x, add(x.location, step));
      }
      if (e % 12 === 0) damage(x, C.beamDamage, caster);
    }
  }, T_FIN + 22, T_FIN + LEN.finale);
  const T_SLAM = T_FIN + LEN.finale;
  scene.at(T_SLAM, () => dreamer.state(DS.slam));
  scene.at(T_SLAM + 3, () => {
    sound(dim, "dn_dreamer_final", land, 1.8);
    particle(dim, "dn_dreamer_shock", up(land, 0.2));
    particle(dim, "fx_flash", up(land, 2));
    ring(dim, "dn_dreamer_porcelain", up(land, 1), 4, 6);
    for (const e of hostiles(dim, land, C.finalRadius, caster)) {
      damage(e, C.finalDamage, caster);
      knockback(e, land, C.finalKnock, 0.6);
    }
  });

  // ================================================================ PHASE V - The Forgotten Morning
  const T5 = T_SLAM + LEN.slam + 10;
  const bookAt = (): Vector3 => at(caster.isValid ? caster.location : scene.origin, aim.yaw, BOOK.right, BOOK.up, BOOK.fwd);
  scene.at(T5, () => {
    dreamer.state(DS.forget).skin(0);
    sound(dim, "dn_dreamer_break", up(hover, 8), 1.5);
    bed.state(BED.vanish);
    for (const m of marks.values()) { m.a.state(3); const a = m.a; scene.after(8, () => scene.despawn(a)); }
  });
  scene.every(10, (e) => burst(dim, "dn_dreamer_porcelain", up(hover, 4 + e / 10), 5, 4), T5 + 6, T5 + 70);
  const bedStart = { ...bedPos };
  scene.span(T5, T5 + 50, (p) => bed.move(lerp(bedStart, up(bookAt(), 2), smooth(p)), faceYaw + p * 90));
  scene.at(T5 + 52, () => scene.despawn(bed));
  scene.at(T5 + 10, () => { domain.state(3); codex.state(CODEX.gather); });
  scene.at(T5 + 42, () => scene.despawn(domain));
  scene.at(T5 + 20, () => sound(dim, "dn_dreamer_morning", caster.location, 1.0));
  scene.at(T5 + 30, () => {
    const from = at(hover, faceYaw, 0, CHEST.up, CHEST.fwd * 0.5);
    const room = scene.spawn("dn_dreamer_bedroom", from, { yaw: faceYaw, size: 6, state: 1 });
    scene.after(16, () => room.state(2));
    const mid = up(lerp(from, bookAt(), 0.5), 6);
    scene.span(scene.tick + 20, scene.tick + 70, (p) => {
      room.move(bezier(from, mid, bookAt(), smooth(p))).size(6 + (0.35 - 6) * smooth(p));
      if (Math.round(p * 50) % 10 === 0) particle(dim, "dn_dreamer_mote", room.loc);
    });
    scene.after(70, () => room.state(3));
    scene.after(88, () => scene.despawn(room));
  });
  scene.at(T5 + LEN.forget, () => scene.despawn(dreamer));
  const T_CLOSE = T5 + 104;
  scene.at(T_CLOSE, () => { codex.state(CODEX.close); particle(dim, "dn_dreamer_star", bookAt()); });
  scene.at(T_CLOSE + 23, () => sound(dim, "dn_dreamer_click", bookAt(), 0.8));
  scene.endAt(T_CLOSE + 54);
  void dist;
});
