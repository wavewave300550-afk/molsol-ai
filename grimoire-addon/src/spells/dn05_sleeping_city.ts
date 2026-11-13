import { Entity, Vector3 } from "@minecraft/server";
import { DN05 as C } from "../config/dn05";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, effect, knockback, removeWard, Ward } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { allies, focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { BARRIER, blocksFor } from "../lib/tempblocks";
import { add, dist, easeIn, flat, lerp, mul, norm, polar, right, sub, up, yawOf } from "../lib/vec";
import { balcony, CityCtx, corridor, doorframe, fragment, rollingStreet, STAIR, stairfall, T, windowEye } from "./_dn05_hunters";

// District states (tools/assets/dn_city.py DISTRICT_STATES) -- spire, both quarters and the ring share them.
const D = { hidden: 0, assemble: 1, dream: 2, living: 3, warp: 4, nightmare: 5, collapse: 6 };
const MINI = { hidden: 0, form: 1, idle: 2, charge: 3, release: 4, wink: 5 };
const WAVE = { hidden: 0, expand: 1, fade: 2 };
// Animation lengths (ticks) mirrored from the asset module.
const T_ASM = secs(5.0), T_WARP = secs(2.0), T_COL = secs(3.0);
const T_MINI_FORM = secs(1.2), T_MINI_CHARGE = secs(1.6), T_MINI_WINK = secs(0.6);
const T_WAVE = secs(1.4);
/** dn_city.py WAVE_KEYS: radius fraction of the dream-wave over its expand animation (seconds -> fraction). */
const WAVE_KEYS: [number, number][] = [[0, 0.03], [0.35, 0.42], [0.7, 0.74], [1.0, 0.92], [1.4, 1.0]];
/** Sky-stair geometry: 96 units tall at scale 2 x size; pavilion centre 8 units in front of the foot. */
const STAIR_UNITS = 96, PAVILION_UNITS = 8;

// Phase boundaries (ticks)
const P2 = secs(7), P3 = secs(16), P4 = secs(27);

function waveFrac(sec: number): number {
  for (let i = 1; i < WAVE_KEYS.length; i++) {
    const [t0, v0] = WAVE_KEYS[i - 1], [t1, v1] = WAVE_KEYS[i];
    if (sec <= t1) return v0 + (v1 - v0) * ((sec - t0) / (t1 - t0));
  }
  return 1;
}

/**
 * DN05 - Imperial Edict: The City That Sleeps Above the World.
 * I   Gentle Arrival (0-7 s): a dream city assembles island by island above the field; allies are warded.
 * II  The Streets Begin to Move (7-16 s): districts come alive; sky-stairs descend beside allies as cover;
 *     balconies fall and rolled-up streets roll through enemies.
 * III Nightmare Under the Facade (16-27 s): the city warps; doorframes, window-eyes, folding corridors,
 *     descending stairs and living fragments hunt.
 * IV  The Sleeping Collapse (27-35.5 s): the city folds into a miniature above the Grimoire, which releases
 *     the final dream-wave across the target area and winks out.
 */
export default defineSpell("dn05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.focusSnap);
  const H = C.cityHeight;
  const spirePos = up(center, H);
  const qAngles = [45, 135, 225, 315];
  const qPos = qAngles.map((a, k) => polar(center, C.quarterDistance, a, H + C.quarterLift[k]));
  const anchors = [spirePos, ...qPos];
  const tb = blocksFor(scene);
  const hunters = new Set<Actor>();

  const ctx: CityCtx = {
    scene, caster, dim, center, hunters,
    sky: (i) => up(anchors[((i % anchors.length) + anchors.length) % anchors.length], -3),
    foes: (from) => {
      const f = hostiles(dim, center, C.areaRadius + 6, caster);
      return f.sort((a, b) => dist(a.location, from) - dist(b.location, from));
    },
    spot: (seed) => groundBelow(dim, polar(center, 3 + ((seed * 5.3) % 10), seed * 137.5)),
  };

  // ======================================================== Phase I: The Gentle Arrival
  const districts: { a: Actor; pos: Vector3 }[] = [];
  const spire = scene.spawn("dn_city_spire", spirePos, { state: D.assemble, yaw: 0 });
  districts.push({ a: spire, pos: spirePos });
  sound(dim, "dn_city_arrive", up(center, 6), 1.4);
  qPos.forEach((p, k) => {
    scene.at(8 + k * 8, () => {
      const q = scene.spawn(k % 2 ? "dn_city_quarter_b" : "dn_city_quarter_a", p, { state: D.assemble, yaw: yawOf(sub(spirePos, p)) });
      districts.push({ a: q, pos: p });
      particle(dim, "dn_city_cloud", up(p, -1));
      sound(dim, "dn_city_rise", p, 0.8, 0.95 + k * 0.05);
    });
  });
  let ringA: Actor | undefined;
  scene.at(30, () => {
    ringA = scene.spawn("dn_city_ring", spirePos, { state: D.assemble, yaw: 0 });
    districts.push({ a: ringA, pos: spirePos });
  });
  scene.every(6, (el) => particle(dim, "dn_city_cloud", up(anchors[(el / 6) % anchors.length], -1.5)), 0, secs(3));
  scene.at(secs(1.8), () => sound(dim, "dn_city_rise", spirePos, 1.0));
  // windows light in waves (Phase I, ~3.7-4.6 s into each district's assembly)
  for (let k = 0; k < 5; k++) {
    scene.at(secs(3.7) + k * 9, () => {
      const p = anchors[k % anchors.length];
      sound(dim, "dn_city_window", p, 0.8, 1 + k * 0.04);
      burst(dim, "dn_city_window", up(p, 5), 3, 3);
      particle(dim, "dn_city_chime", up(p, 7));
    });
  }

  // allied defense: partial resistance for the whole spell + regeneration once the city stands
  const allySet = new Set<string>([caster.id]);
  const refreshAllies = () => {
    for (const p of allies(dim, center, C.wardRadius, caster)) allySet.add(p.id);
    for (const p of allies(dim, caster.location, 8, caster)) allySet.add(p.id);
  };
  refreshAllies();
  scene.every(20, refreshAllies, 0, P4 + secs(6));
  const ward: Ward = addWard({
    scene, factor: C.wardFactor,
    protects: (e) => e.typeId === "minecraft:player" && allySet.has(e.id),
    onAbsorb: (_amt, _att, victim) => particle(dim, "dn_city_ward", up(victim.location, 1)),
  });
  scene.at(40, () => {
    refreshAllies();
    sound(dim, "dn_city_ward", caster.location, 1.0);
    for (const p of allies(dim, center, C.wardRadius, caster).concat(isAlive(caster) ? [caster] : [])) {
      effect(p, "regeneration", C.regenTicks, C.regenAmp);
      particle(dim, "dn_city_ward", up(p.location, 1));
    }
  });
  scene.at(P2 - 1, () => districts.forEach((d) => d.a.state(D.dream)));

  // ======================================================== Phase II: The Streets Begin to Move
  scene.at(P2, () => {
    districts.forEach((d) => d.a.state(D.living));
    sound(dim, "dn_city_move", spirePos, 1.4);
  });
  scene.every(secs(3), () => sound(dim, "dn_city_move", anchors[Math.floor(scene.tick / 7) % anchors.length], 1.1, 0.95),
    P2 + secs(3), P3 - 10);
  scene.every(8, (el) => particle(dim, "dn_city_mote", up(anchors[(el / 8) % anchors.length], -4)), P2, P3);

  // sky-stairs descend beside allies: the flight shields them, the pavilion is cover
  const coverWards: Ward[] = [];
  scene.at(P2 + 10, () => {
    const sheltered = allies(dim, center, C.wardRadius, caster).filter((p) => isAlive(p));
    if (!sheltered.some((p) => p.id === caster.id) && isAlive(caster)) sheltered.unshift(caster);
    sheltered.slice(0, C.maxStairs).forEach((ally, k) => {
      let away = norm(flat(sub(ally.location, center)));
      if (dist(flat(ally.location), flat(center)) < 2) away = norm(flat(mul(aim.forward, -1)));
      const size = (H - 2) / 12;
      const unit = (2 * size) / 16;
      const foot = groundBelow(dim, add(ally.location, mul(away, -PAVILION_UNITS * unit)));
      const pav = add(foot, mul(away, PAVILION_UNITS * unit));
      scene.after(k * 6, () => {
        const st = scene.spawn("dn_city_stair", foot, { state: STAIR.descend, size, yaw: yawOf(away) });
        sound(dim, "dn_city_stair", up(foot, 6), 1.1, 1 + k * 0.06);
        scene.after(T.stairDown, () => {
          st.state(STAIR.stand);
          particle(dim, "dn_city_dust", foot);
          ring(dim, "dn_city_ward", up(pav, 0.5), 1.5, 4, k * 30);
          // the lowest flight is a real wall between the ally and the battlefield (open sides, never sealed)
          const side = right(away);
          for (let s = -1; s <= 1; s++) {
            const b = add(add(foot, mul(away, -1.1)), mul(side, s));
            tb.column(Math.floor(b.x), Math.floor(foot.y), Math.floor(b.z), 2, BARRIER);
          }
          for (const s of [-1, 1]) {
            const col = add(foot, mul(side, s * 11 * unit));
            tb.column(Math.floor(col.x), Math.floor(foot.y), Math.floor(col.z), 4, BARRIER);
          }
          coverWards.push(addWard({
            scene, factor: C.coverFactor,
            protects: (e) => e.typeId === "minecraft:player" && allySet.has(e.id) && dist(e.location, pav) <= C.coverRadius,
          }));
          scene.every(10, () => {
            for (const at of dissolveProjectiles(scene, pav, C.coverRadius + 1)) particle(dim, "dn_city_chime", at);
          }, scene.tick, P3 - 30);
        });
        scene.at(P3 - 26, () => {
          st.state(STAIR.retract);
          sound(dim, "dn_city_stair", up(foot, 6), 0.8, 1.2);
          const side = right(away);
          for (let s = -1; s <= 1; s++) {
            const b = add(add(foot, mul(away, -1.1)), mul(side, s));
            tb.removeColumn(Math.floor(b.x), Math.floor(foot.y), Math.floor(b.z), 2);
          }
          for (const s of [-1, 1]) {
            const col = add(foot, mul(side, s * 11 * unit));
            tb.removeColumn(Math.floor(col.x), Math.floor(foot.y), Math.floor(col.z), 4);
          }
        });
        scene.at(P3 - 26 + T.stairUp, () => scene.despawn(st));
      });
    });
  });
  scene.at(P3 - 26, () => coverWards.forEach((w) => removeWard(w)));

  // buildings release architectural attack constructs: falling balconies and rolling streets
  let attack = 0;
  scene.every(C.attackEvery, () => {
    if (attack % 2 === 0) balcony(ctx, attack + 1);
    else rollingStreet(ctx, attack + 2);
    attack++;
  }, P2 + 25, P3 - 45);

  // ======================================================== Phase III: The Nightmare Under the Facade
  scene.at(P3, () => {
    districts.forEach((d) => d.a.state(D.warp).skin(1));
    sound(dim, "dn_city_warp", spirePos, 1.5);
    burst(dim, "dn_city_night", spirePos, 6, 6);
  });
  scene.at(P3 + T_WARP, () => districts.forEach((d) => d.a.state(D.nightmare)));
  scene.every(secs(2.4), (el) => sound(dim, "dn_city_groan", anchors[(el / 48) % anchors.length], 1.0, 0.9),
    P3 + 20, P4 - 10);
  scene.every(9, (el) => particle(dim, "dn_city_cloud_n", up(anchors[(el / 9) % anchors.length], -2)), P3, P4);
  const huntEnd = P4 - 6;
  for (let i = 0; i < C.doorCount; i++) scene.at(P3 + 20 + i * 10, () => doorframe(ctx, i, huntEnd));
  for (let i = 0; i < C.windowCount; i++) scene.at(P3 + 26 + i * 30, () => windowEye(ctx, i, huntEnd));
  for (let i = 0; i < C.fragmentCount; i++) scene.at(P3 + 40 + i * 4, () => fragment(ctx, i, huntEnd - 10));
  scene.at(P3 + 60, () => corridor(ctx, 0));
  scene.at(P3 + 130, () => corridor(ctx, 1));
  scene.at(P3 + 80, () => stairfall(ctx, 0));
  scene.at(P3 + 150, () => stairfall(ctx, 1));

  // ======================================================== Phase IV: The Sleeping Collapse
  const miniAt = (): Vector3 => {
    let f = aim.forward;
    try { const v = caster.getViewDirection(); if (Number.isFinite(v.x) && Math.hypot(v.x, v.z) > 0.05) f = norm(flat(v)); } catch { /* keep */ }
    const base = isAlive(caster) ? caster.location : scene.origin;
    return up(add(add(base, mul(f, 0.9)), mul(right(f), 0.35)), 2.3);
  };
  scene.at(P4, () => {
    for (const h of [...hunters]) { scene.despawn(h); hunters.delete(h); }
    sound(dim, "dn_city_collapse", spirePos, 1.5);
  });
  // fold inward in sequence: ring, quarters, then the spire -- each streams toward the Grimoire
  const order = () => {
    const r = districts.filter((d) => d.a === ringA);
    const q = districts.filter((d) => d.a !== ringA && d.a !== spire);
    return [...r, ...q, ...districts.filter((d) => d.a === spire)];
  };
  scene.at(P4, () => {
    order().forEach((d, k) => {
      const t0 = scene.tick + k * 10;
      scene.at(t0, () => { d.a.state(D.collapse); particle(dim, "dn_city_fold", d.pos); });
      scene.span(t0 + 15, t0 + T_COL, (q) => d.a.move(lerp(d.pos, miniAt(), easeIn(q) * 0.85)));
      scene.at(t0 + T_COL, () => scene.despawn(d.a));
    });
  });
  const tMini = P4 + 60;
  let mini: Actor | undefined;
  scene.at(tMini, () => {
    mini = scene.spawn("dn_city_mini", miniAt(), { state: MINI.form });
    sound(dim, "dn_city_mini", miniAt(), 1.0);
    burst(dim, "dn_city_key", miniAt(), 0.8, 5);
  });
  scene.every(1, () => mini?.move(miniAt()), tMini, tMini + 120);
  scene.at(tMini + T_MINI_FORM, () => mini?.state(MINI.idle));

  // the final dream-wave: telegraphed across the target area, then radiates from the city's footprint
  const tCharge = tMini + T_MINI_FORM + 6;
  const tWave = tCharge + T_MINI_CHARGE;
  let warn: Actor | undefined;
  scene.at(tCharge - 10, () => { warn = scene.spawn("telegraph", center, { kind: 1, size: C.waveRadius, state: 4 }); });
  scene.at(tCharge, () => { mini?.state(MINI.charge); sound(dim, "dn_city_charge", miniAt(), 1.2); });
  scene.every(3, () => line(dim, "dn_city_streak", up(miniAt(), 1.2), up(center, 2), 6), tWave - 12, tWave);
  scene.at(tWave - 7, () => sound(dim, "dn_city_wave", center, 1.6));
  let wave: Actor | undefined;
  let enemiesAtLaunch = 1;
  const struck = new Set<string>();
  scene.at(tWave, () => {
    mini?.state(MINI.release);
    warn?.state(3);
    wave = scene.spawn("dn_city_wave", up(center, 0.1), { state: WAVE.expand, size: C.waveRadius });
    particle(dim, "fx_flash", up(center, 2));
    enemiesAtLaunch = Math.max(1, hostiles(dim, center, C.waveRadius, caster).length);
  });
  scene.at(tWave + 8, () => { if (warn) scene.despawn(warn); });
  scene.span(tWave, tWave + T_WAVE, (_q, el) => {
    const r = C.waveRadius * waveFrac(el / 20);
    if (el % 3 === 0) ring(dim, "dn_city_wave", up(center, 0.5), r, 10, el * 7);
    for (const e of hostiles(dim, center, r + 0.5, caster) as Entity[]) {
      if (struck.has(e.id)) continue;
      struck.add(e.id);
      damage(e, C.waveBase + C.waveConcentrate / enemiesAtLaunch, caster);
      knockback(e, center, C.waveKnockH, C.waveKnockV);
      particle(dim, "dn_city_key", up(e.location, 1));
    }
  });
  scene.at(tWave + T_WAVE, () => wave?.state(WAVE.fade));
  scene.at(tWave + T_WAVE + 10, () => { if (wave) scene.despawn(wave); });
  const tWink = tWave + T_WAVE + 4;
  scene.at(tWink, () => { mini?.state(MINI.wink); sound(dim, "dn_city_wink", miniAt(), 1.0); });
  scene.at(tWink + T_MINI_WINK, () => { burst(dim, "dn_city_chime", miniAt(), 0.5, 3); if (mini) scene.despawn(mini); });
  scene.onEnd(() => removeWard(ward));
  scene.endAt(tWink + T_MINI_WINK + 4);
});
