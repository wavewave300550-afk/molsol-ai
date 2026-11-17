import { Entity, Vector3 } from "@minecraft/server";
import { ED02 as C } from "../config/ed02";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback, shove } from "../lib/combat";
import { burst, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { add, clamp, dot, flat, len, mul, norm, right, sub, up, yawOf } from "../lib/vec";

// ---- Heat Dragon contract (mirror of tools/assets/ed_heat.py: ACTOR, SCALE, STATE_IDS, timing constants)
const ACTOR = "dragon_heat";
export const ED_HEAT_SCALE = 1.85;
const S = {
  hidden: 0, arrive: 1, idle: 2, move: 3, turn_l: 4, turn_r: 5, attack_a: 6, attack_b: 7, power: 8, react: 9,
  rest: 10, depart: 11, ignite: 12, charge: 13, skid: 14, pant: 15, cool: 16, roar: 17, walk: 18,
};
const SKIN = { cool: 0, ignited: 1, whitehot: 2 };
/** Blocks per second that match the foot plants of the run / charge and walk loops. */
const RUN_SPEED = 10.02;
const WALK_SPEED = 3.53;
/** Degrees per second of yaw while turn_l / turn_r play. */
const TURN_RATE = 225;
const T = {
  arriveWalk: secs(1.2), arrive: secs(1.6), ignite: secs(1.6), igniteRoar: secs(1.1), skid: secs(0.7),
  powerOpen: secs(1.0), cool: secs(1.2), depart: secs(2.0),
};
// helper actors
const WALL = { form: 1, hold: 2, part: 3, fade: 4 };
const WAVE = { rise: 1, travel: 2, burst: 3 };
const GLASS = { appear: 1, hold: 2, fade: 3 };
const LANE = { appear: 1, armed: 2, surge: 3, fade: 4 };

/**
 * ED02 - Thermal Tyrant: Furnace of the Carnotaur.
 * A horned Carnotaurus-bodied Heat Dragon stalks out of a wall of heat shimmer beside the caster,
 * ignites (fissures, vents, horns), sprints down a telegraphed lane through the target hitting
 * everything with its horns and body, skids, wheels around, and opens its furnace: a superheated
 * wave runs back along the whole charge route, vitrifying the ground behind it.
 */
export default defineSpell("ed02", ({ caster, scene, aim }) => {
  const dim = scene.dim;

  // ---- lane geometry: from beside/behind the caster, through the focus point and beyond
  let F = focus(caster, aim, 12).center;
  let d0 = flat(sub(F, caster.location));
  if (len(d0) < C.minFocus) {
    F = groundBelow(dim, add(caster.location, mul(aim.forward, C.minFocus + 4)));
    d0 = flat(sub(F, caster.location));
  }
  d0 = norm(len(d0) < 0.01 ? aim.forward : d0);
  const W = groundBelow(dim, add(add(caster.location, mul(d0, -C.laneBack)), mul(right(d0), C.laneSide)));
  const d = norm(flat(sub(F, W)));
  const rv = right(d);
  const yaw = yawOf(d);
  const back = mul(d, -1);
  const chargeDist = clamp(dot(flat(sub(F, W)), d) + C.overshoot, C.chargeMin, C.chargeMax);
  const skidDist = ((RUN_SPEED / 20) * (T.skid - 1)) / 2;
  const lanePoint = (s: number, lat = 0): Vector3 => groundBelow(dim, add(add(W, mul(d, s)), mul(rv, lat)));
  const arriveDist = (WALK_SPEED * T.arriveWalk) / 20;
  const W0 = add(W, mul(d, -arriveDist));

  // dragon kinematics: s = distance of the hips along the lane from W
  let s = -arriveDist;
  let y = groundBelow(dim, W0).y;
  let curYaw = yaw;
  let facing = d;
  let pos: Vector3 = { x: W0.x, y, z: W0.z };
  const place = (yawNow = curYaw): void => {
    const p = add(W, mul(d, s));
    const g = groundBelow(dim, p).y;
    y += clamp(g - y, -0.35, 0.35);
    pos = { x: p.x, y, z: p.z };
    curYaw = yawNow;
    dragon.move(pos, curYaw);
  };
  const chest = (): Vector3 => up(add(pos, mul(facing, 2.2)), 4.6);

  // ---- Stage I: Internal Ignition -- the dragon unfolds out of a heat-shimmer wall
  const wallAt = groundBelow(dim, add(W0, mul(d, C.wallAhead)));
  const wall = scene.spawn("ed_heat_shimmer", wallAt, { yaw, state: WALL.form });
  const dragon = scene.spawn(ACTOR, pos, { yaw, state: S.arrive, skin: SKIN.cool });
  sound(dim, "ed_heat_shimmer", wallAt, 1.1);
  scene.at(10, () => wall.state(WALL.part));
  scene.at(30, () => wall.state(WALL.fade));
  scene.at(44, () => scene.despawn(wall));
  scene.every(4, (e) => {
    particle(dim, "ed_heat_haze", up(add(wallAt, mul(rv, (e % 3) * 2.5 - 2.5)), 1.5));
    particle(dim, "ed_heat_ember", up(wallAt, 3));
  }, 0, 32);
  scene.span(0, T.arriveWalk + 1, (p) => { s = -arriveDist * (1 - p); place(); });

  const tI = T.arrive;
  let lane: Actor | undefined;
  const laneLen = clamp(chargeDist + skidDist + 8.5 - 4, 4, 32);
  scene.at(tI, () => { dragon.state(S.ignite); sound(dim, "ed_heat_ignite", chest(), 1.2); });
  scene.at(tI + 4, () => {
    lane = scene.spawn("ed_heat_lane", lanePoint(4), { yaw, state: LANE.appear });
    lane.prop("len", laneLen);
    sound(dim, "ed_heat_lane", lanePoint(10), 1.0);
  });
  scene.at(tI + 10, () => { dragon.skin(SKIN.ignited); burst(dim, "ed_heat_ember", chest(), 2.2, 4); });
  scene.at(tI + 22, () => lane?.state(LANE.armed));
  scene.at(tI + T.igniteRoar, () => {
    const c = chest();
    particle(dim, "ed_heat_ring", up(pos, 0.3));
    particle(dim, "fx_flash", c);
    ring(dim, "ed_heat_vent", up(pos, 3.5), 2.8, 5);
    for (const e of hostiles(dim, c, C.igniteRadius, caster)) {
      if (damage(e, C.igniteDamage, caster)) knockback(e, pos, C.igniteKnock, 0.35);
    }
  });

  // ---- Stage II: The Carnotaur's Rampage
  const tC = tI + T.ignite;
  type Hit = { horn: number; body: boolean };
  const hits = new Map<string, Hit>();
  let phase: "wait" | "run" | "skid" | "done" = "wait";
  let k = 0;

  function strikes(): void {
    for (const e of hostiles(dim, add(pos, mul(d, 3)), C.scanRadius, caster)) {
      const dy = e.location.y - pos.y;
      if (dy > 7 || dy < -3) continue;
      const rel = flat(sub(e.location, pos));
      const along = dot(rel, d);
      const latS = dot(rel, rv);
      const lat = Math.abs(latS);
      let h = hits.get(e.id);
      if (!h) { h = { horn: -1, body: false }; hits.set(e.id, h); }
      const away = norm(add(mul(rv, latS >= 0 ? 1 : -1), mul(d, 0.45)));
      if (h.horn < 0 && along > C.hornReach - C.hornDepth && along < C.hornReach + 1.5 && lat < C.hornRadius) {
        h.horn = scene.tick;
        if (damage(e, C.hornDamage, caster)) shove(e, away, C.hornKnockH, C.hornKnockV);
        impact(e, 1.0);
      } else if (!h.body && along > -C.bodyBack && along < C.bodyFront && lat < C.bodyRadius &&
        (h.horn < 0 || scene.tick - h.horn >= C.bodyDelay)) {
        h.body = true;
        if (damage(e, C.bodyDamage, caster)) shove(e, away, C.bodyKnockH, C.bodyKnockV);
        impact(e, 0.8);
      }
    }
  }
  function impact(e: Entity, pitch: number): void {
    const at = up(e.location, 1.1);
    particle(dim, "ed_heat_spark", at);
    particle(dim, "ed_heat_ember", at);
    sound(dim, "ed_heat_hit", at, 1.0, pitch);
  }

  scene.at(tC, () => { phase = "run"; dragon.state(S.charge); lane?.state(LANE.armed); });
  scene.every(1, () => {
    if (phase === "run") {
      const f = k < C.accelTicks ? C.startSpeed + ((1 - C.startSpeed) * k) / C.accelTicks : 1;
      k++;
      s = Math.min(chargeDist, s + (RUN_SPEED / 20) * f);
      place();
      strikes();
      if (k % 3 === 0) particle(dim, "ed_heat_haze", up(add(pos, mul(d, -3)), 1.2));
      if (k % 4 === 0) particle(dim, "ed_heat_ember", up(add(pos, mul(d, 1)), 5));
      if (s >= chargeDist) {
        phase = "skid";
        k = 0;
        dragon.state(S.skid);
        particle(dim, "ed_heat_skid", up(add(pos, mul(d, 1)), 0.3));
      }
    } else if (phase === "skid") {
      k++;
      s += (RUN_SPEED / 20) * Math.max(0, 1 - k / T.skid);
      place();
      strikes();
      if (k % 3 === 0) particle(dim, "ed_heat_skid", up(add(pos, mul(d, 1)), 0.3));
      if (k >= T.skid) { phase = "done"; stage3(scene.tick + 1); }
    }
  }, tC, tC + 200);
  scene.endAt(tC + 320); // safety; replaced by the exact end once Stage III is scheduled

  // ---- Stage III: The Furnace Opens
  function burn(e: Entity): void {
    effect(e, "weakness", C.weaknessTicks, 0);
    try { e.setOnFire(C.burnSeconds, true); } catch { /* fire-immune or gone */ }
  }

  function stage3(t0: number): void {
    // powerful whole-body turn, away from the caster's side of the lane
    const turnDir = dot(flat(sub(caster.location, pos)), rv) > 0 ? -1 : 1;
    const turnTicks = Math.round((180 / TURN_RATE) * 20);
    scene.at(t0, () => dragon.state(turnDir > 0 ? S.turn_r : S.turn_l));
    scene.span(t0, t0 + turnTicks, (p) => dragon.move(pos, yaw + turnDir * 180 * p));
    const tP = t0 + turnTicks;
    scene.at(tP, () => {
      curYaw = yaw + turnDir * 180;
      facing = back;
      dragon.state(S.power);
      lane?.state(LANE.surge).skin(1);
      sound(dim, "ed_heat_lane", chest(), 1.2, 1.25);
    });
    scene.at(tP + 8, () => { dragon.skin(SKIN.whitehot); particle(dim, "fx_flash", chest()); });
    scene.every(3, () => particle(dim, "ed_heat_vent", up(pos, 4.2)), tP + 6, tP + T.powerOpen);

    const tR = tP + T.powerOpen;
    const sStart = s - C.waveStartBack;
    const sEnd = Math.min(C.waveStopShort, sStart - 1);
    const step = C.waveSpeed / 20;
    const waveTicks = Math.ceil((sStart - sEnd) / step);
    const waveYaw = yawOf(back);
    let sf = sStart;
    let wave: Actor | undefined;
    let nextGlass = sStart - 1;
    let glassN = 0;
    const waved = new Set<string>();

    function spawnGlass(at: number): void {
      glassN++;
      const g = scene.spawn("ed_heat_glass", lanePoint(at, (glassN % 2 ? 1 : -1) * 0.9), { yaw: glassN * 67, state: GLASS.appear });
      if (glassN % 3 === 1) sound(dim, "ed_heat_glass", g.loc, 0.8, 0.9 + (glassN % 4) * 0.08);
      scene.after(6, () => g.state(GLASS.hold));
      scene.after(C.glassCoolTicks, () => g.skin(1));
      scene.after(C.glassFadeTicks, () => g.state(GLASS.fade));
      scene.after(C.glassFadeTicks + 17, () => scene.despawn(g));
    }

    scene.at(tR, () => {
      const c = chest();
      sound(dim, "ed_heat_wave", c, 1.5);
      particle(dim, "ed_heat_ring", up(pos, 0.3));
      particle(dim, "fx_flash", c);
      burst(dim, "ed_heat_ember", c, 3, 6);
      ring(dim, "ed_heat_steam", up(pos, 1), 3.5, 5);
      for (const e of hostiles(dim, add(pos, mul(back, 2)), C.dischargeRadius, caster)) {
        if (damage(e, C.dischargeDamage, caster)) { knockback(e, pos, C.dischargeKnock, 0.5); burn(e); }
      }
      wave = scene.spawn("ed_heat_wave", lanePoint(sf), { yaw: waveYaw, state: WAVE.rise });
      scene.after(7, () => wave?.state(WAVE.travel));
    });
    scene.every(1, (e) => {
      sf = Math.max(sEnd, sf - step);
      const fp = lanePoint(sf);
      wave?.move(fp, waveYaw);
      if (e % 2 === 0) particle(dim, "ed_heat_wavefront", up(fp, 1.2));
      if (e % 3 === 1) particle(dim, "ed_heat_haze", up(add(fp, mul(d, 1.5)), 0.8));
      while (sf <= nextGlass && nextGlass >= sEnd) { spawnGlass(nextGlass); nextGlass -= C.glassEvery; }
      for (const t of hostiles(dim, fp, C.waveHalfWidth + 2.5, caster)) {
        if (waved.has(t.id) || !isAlive(t)) continue;
        const rel = flat(sub(t.location, W));
        const along = dot(rel, d);
        if (Math.abs(dot(rel, rv)) > C.waveHalfWidth || along < sf - 1 || along > sStart + 2.5) continue;
        waved.add(t.id);
        if (damage(t, C.waveDamage, caster)) { shove(t, back, C.waveKnockH, C.waveKnockV); burn(t); }
        particle(dim, "ed_heat_ember", up(t.location, 1));
      }
    }, tR + 1, tR + 1 + waveTicks);
    scene.at(tR + 1 + waveTicks, () => {
      wave?.state(WAVE.burst);
      particle(dim, "ed_heat_wavefront", up(lanePoint(sEnd), 1));
      const w = wave;
      scene.after(12, () => { if (w) scene.despawn(w); });
    });

    // cooling, heavy breathing, dissolution into cooling slag
    const tCool = tR + Math.max(10, waveTicks - 4);
    scene.at(tCool, () => {
      dragon.state(S.cool).skin(SKIN.ignited);
      lane?.state(LANE.fade);
      ring(dim, "ed_heat_steam", up(pos, 4), 2.5, 4);
    });
    scene.at(tCool + 10, () => { if (lane) scene.despawn(lane); });
    scene.at(tCool + 12, () => dragon.skin(SKIN.cool));
    const tPant = tCool + T.cool;
    scene.at(tPant, () => dragon.state(S.pant));
    const tDep = tPant + C.pantTicks;
    scene.at(tDep, () => { dragon.state(S.depart); particle(dim, "ed_heat_steam", up(pos, 3)); });
    scene.at(tDep + 14, () => burst(dim, "ed_heat_slag", up(pos, 2.5), 2.5, 4));
    scene.at(tDep + 26, () => { burst(dim, "ed_heat_slag", up(pos, 1), 2, 3); particle(dim, "ed_heat_steam", up(pos, 1)); });
    scene.at(tDep + T.depart, () => scene.despawn(dragon));
    scene.endAt(tDep + T.depart + 2);
  }
});
