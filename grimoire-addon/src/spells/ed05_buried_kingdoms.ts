import { Entity } from "@minecraft/server";
import { ED05 as C } from "../config/ed05";
import { defineSpell } from "../core/registry";
import { damage, effect, knockback } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import {
  add, angleDelta, bezier, clamp, dist, distToSegment, distXZ, easeOut, flat, fromYaw, lerp, mul, norm, polar, right, smooth, sub, up,
  V3, yawOf,
} from "../lib/vec";
import { ED5_IMPRINT, ED5_PROPS, ED5_SKEL, ED5_TABLET } from "./_ed05_assets";
import { Path, SLOT, SPECIES, Species, inSector, local, midUp, polarOf, yawLerp } from "./_ed05_kit";

// State tables are generated with the models (tools/assets/ed5_monument.py -> _ed05_assets.ts):
//   tablet   hidden 0, rise 1, stand 2, memorial 3, awaken 4, empty 5, receive 6, formation 7, aim 8, project 9,
//            project_all 10, fracture 11      (skins: 0 dormant, 1 awake, 2 blaze)
//   skeletons (tools/assets/ed5_skeletons.py STATES): own hidden / emerge / return + the living species' animations
const T = ED5_TABLET.states;
const P = ED5_PROPS;
const SK = ED5_SKEL;
const IMP = ED5_IMPRINT.states;

interface Tab { sp: Species; a: Actor; pos: V3; yaw: number; baseY: number }
interface HitOpts {
  once?: Set<string>; from?: V3; kb?: number; kv?: number; slow?: [number, number]; fire?: number; lev?: number;
  test?: (e: Entity) => boolean;
}

/**
 * ED05 - Imperial Edict: The Chronicle of Buried Kingdoms.
 * I   The Buried Testament: draconic inscriptions sink into the earth, four fossil tablets break out of it and orbit
 *     up into a suspended, turning memorial.
 * II  The Fossils That Remember: one by one the reliefs wake, and the skeletons peel out of the stone, grow to full
 *     size and fight with their own anatomy (sauropod slam + neck sweep, carnotaur charges, spinosaur tail and sail
 *     crystal fans, microraptor wingbeat shockwaves), then fold back into their slabs.
 * III The Eternal Imprint: the blazing tablets fan out above the field and project their fossil images as elemental
 *     attacks, one after another and then together, and crack along their strata into luminous fragments.
 */
export default defineSpell("ed05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.focusSnap);
  const fwd = norm(flat(aim.forward));
  const phiF = polarOf(fwd);
  const at = (s: number): number => secs(s);
  const gnd = (p: V3): V3 => groundBelow(dim, { x: p.x, y: center.y + 6, z: p.z }, 24);
  const dirOf = (deg: number): V3 => ({ x: Math.cos((deg * Math.PI) / 180), y: 0, z: Math.sin((deg * Math.PI) / 180) });
  const tabs: Partial<Record<Species, Tab>> = {};
  const rel = ED5_TABLET.relief;
  const reliefAt = (tb: Tab): V3 => local(tb.pos, tb.yaw, rel[0], rel[1], rel[2]);
  const faceAt = (tb: Tab): V3 => up(tb.pos, ED5_TABLET.height / 2);
  const rSlot = P.memorial.half;
  const theta0 = phiF - C.memorialTurn;
  const slotAngle = (sp: Species, th: number): number => th + 90 * SLOT[sp];
  let ti = 0;

  // ---------------------------------------------------------------- shared helpers
  function hit(c: V3, radius: number, dmg: number, o: HitOpts = {}): number {
    let n = 0;
    for (const e of hostiles(dim, c, radius, caster)) {
      if (o.test && !o.test(e)) continue;
      if (o.once) { if (o.once.has(e.id)) continue; o.once.add(e.id); }
      if (damage(e, dmg, caster)) n++;
      if (o.kb) knockback(e, o.from ?? c, o.kb, o.kv ?? 0.3);
      if (o.slow) effect(e, "slowness", o.slow[0], o.slow[1]);
      if (o.lev) effect(e, "levitation", o.lev, 0);
      if (o.fire) { try { if (e.isValid) e.setOnFire(o.fire, true); } catch { /* fire immune */ } }
    }
    return n;
  }
  function warnAt(p: V3, radius: number, ticks: number, slow = false): void {
    const t = scene.spawn("telegraph", gnd(p), { kind: 2, size: radius, state: slow ? 4 : 1 });
    scene.after(ticks, () => t.state(3));
    scene.after(ticks + 8, () => scene.despawn(t));
  }
  function spikeAt(p: V3, dmg: number, radius: number, lift: number, once: Set<string>, holdS = 1.5, size = 1): void {
    const g = gnd(p);
    const s = scene.spawn(P.spike.actor, g, { yaw: (ti++ * 67) % 360, size, state: P.spike.states.rise });
    sound(dim, "ed5_spike", g, 0.75, 0.88 + (ti % 5) * 0.06);
    particle(dim, "ed5_rock", up(g, 0.4));
    if (ti % 2) particle(dim, "ed5_moss", up(g, 1.2));
    scene.after(4, () => hit(g, radius, dmg, { once, from: g, kb: 0.25, kv: lift }));
    scene.after(secs(holdS), () => s.state(P.spike.states.sink));
    scene.after(secs(holdS + P.spike.sink) + 1, () => scene.despawn(s));
  }
  function iceFan(o: V3, yaw: number, size: number, dmg: number, slow: [number, number], once?: Set<string>, holdS = 1.3): void {
    const g = gnd(o);
    const f = scene.spawn(P.icefan.actor, g, { yaw, size, state: P.icefan.states.burst });
    sound(dim, "ed5_ice", g, 1.0, 1.15 - size * 0.04);
    particle(dim, "ed5_ring_tide", up(g, 0.2));
    burst(dim, "ed5_shard", up(g, 1), 1.2, 3);
    const reach = P.icefan.reach * size + 0.8;
    scene.after(3, () => {
      for (const p of [0.35, 0.7, 1.0]) particle(dim, "ed5_frost", up(local(g, yaw, 0, 0, -reach * p), 1.0));
      hit(g, reach + 1, dmg, {
        once, slow, kb: 0.9, kv: 0.35, from: g,
        test: (e) => inSector(e.location, g, yaw, C.fanHalfAngle, 0, reach),
      });
    });
    scene.after(secs(holdS), () => f.state(P.icefan.states.shatter));
    scene.after(secs(holdS + P.icefan.shatter) + 1, () => scene.despawn(f));
  }
  function gust(p: V3, size: number, dmg: number, radius: number, kb: number, once?: Set<string>, lev = 0): void {
    const g = gnd(p);
    const a = scene.spawn(P.gust.actor, g, { yaw: (ti++ * 53) % 360, size, state: P.gust.states.burst });
    sound(dim, "ed5_gust", g, 0.9, 0.95 + (ti % 4) * 0.05);
    particle(dim, "ed5_ring_air", up(g, 0.3));
    particle(dim, "ed5_wind", up(g, 1.0));
    hit(g, radius, dmg, { once, from: g, kb, kv: 0.45, lev });
    scene.after(secs(P.gust.burst) + 1, () => scene.despawn(a));
  }

  // ================================================================ PHASE I - The Buried Testament
  sound(dim, "ed5_open", caster.location, 1.0);
  burst(dim, "ed5_rune", up(caster.location, 1.4), 1.2, 6);
  scene.every(secs(C.hushEvery), () => sound(dim, "ed5_hush", up(center, 3), 1.0), 0, at(C.endAt - 2));
  scene.every(10, () => particle(dim, "ed5_glow_mote", up(center, 5)), at(2), at(C.fractureAt));
  blocksFor(scene).place(up(center, 1), LIGHT);

  SPECIES.forEach((sp, i) => {
    const site = gnd(polar(center, C.riseRadius, slotAngle(sp, theta0)));
    const t0 = at(C.inscribeAt + i * C.riseStagger);
    scene.at(t0, () => {
      const ins = scene.spawn(P.inscription.actors[sp], site, { state: P.inscription.states.descend, size: 1.0 });
      sound(dim, "ed5_inscribe", site, 0.9, 0.92 + i * 0.06);
      scene.every(5, () => particle(dim, "ed5_rune_fall", up(site, 7)), scene.tick, scene.tick + 30);
      scene.after(secs(P.inscription.descend) + 2, () => scene.despawn(ins));
    });
    scene.at(t0 + at(C.riseDelay), () => {
      const yaw = yawOf(sub(site, center));
      const a = scene.spawn(ED5_TABLET.actors[sp], site, { yaw, state: T.rise, skin: 0 });
      tabs[sp] = { sp, a, pos: site, yaw, baseY: site.y };
      sound(dim, "ed5_rise", site, 1.1, 0.95 + i * 0.04);
      particle(dim, "ed5_crack", up(site, 0.3));
      particle(dim, "ed5_dust", up(site, 0.5));
      scene.after(secs(1.5), () => {
        particle(dim, `ed5_ring_${sp}`, up(site, 0.2));
        burst(dim, "ed5_rock", up(site, 0.6), 2.5, 3);
        particle(dim, "ed5_dust", up(site, 1));
        hit(site, C.riseRadiusHit, C.riseDamage, { kb: C.riseKnock, kv: 0.45 });
      });
      scene.after(secs(ED5_TABLET.len.rise), () => a.state(T.stand));
    });
  });

  // the tablets lift and orbit into the suspended memorial, which slowly turns and halts aligned to the caster
  const tG0 = at(C.gatherAt), tG1 = at(C.gatherAt + C.gatherTime), tHalt = at(C.haltAt);
  const theta = (tk: number): number => theta0 + C.memorialTurn * smooth((tk - tG0) / (tHalt - tG0));
  let memorial: Actor | undefined;
  scene.at(tG0, () => {
    memorial = scene.spawn(P.memorial.actor, up(center, C.memorialHeight), { yaw: yawOf(dirOf(theta0)), state: P.memorial.states.assemble });
    sound(dim, "ed5_grind", up(center, 4), 1.2);
    for (const sp of SPECIES) tabs[sp]?.a.state(T.memorial);
  });
  scene.every(1, (e) => {
    const tk = tG0 + e;
    const th = theta(tk);
    const lin = clamp((tk - tG0) / (tG1 - tG0), 0, 1);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      const a = slotAngle(sp, th);
      const rad = C.riseRadius + (rSlot - C.riseRadius) * smooth(lin);
      const y = tb.baseY + (center.y + C.memorialHeight - tb.baseY) * easeOut(lin);
      tb.pos = { ...polar(center, rad, a), y };
      tb.yaw = yawOf(dirOf(a));
      tb.a.move(tb.pos, tb.yaw);
      if (e % 6 === 0 && lin < 1) particle(dim, "ed5_dust", up(tb.pos, 0.2));
    }
    memorial?.move(up(center, C.memorialHeight), yawOf(dirOf(th)));
  }, tG0, tHalt + 1);
  scene.at(tG1, () => {
    memorial?.state(P.memorial.states.hold);
    sound(dim, "ed5_lock", up(center, 2), 1.4);
    for (const sp of SPECIES) particle(dim, `ed5_ring_${sp}`, up(center, 0.2 + SLOT[sp] * 0.1));
    ring(dim, "ed5_crack", up(center, 0.3), C.lockRadius * 0.6, 8);
    hit(center, C.lockRadius, C.lockDamage, { kb: 0.8, kv: 0.3, slow: [C.lockSlowTicks, C.lockSlowAmp] });
  });

  // ================================================================ PHASE II - The Fossils That Remember
  function outward(sp: Species): V3 { return dirOf(slotAngle(sp, theta0 + C.memorialTurn)); }

  /** The relief wakes, the skeleton peels out of its slab, swings round and lands at `land`. */
  function emerge(sp: Species, land: V3 | undefined, done: (sk: Actor) => void): void {
    const tb = tabs[sp];
    if (!tb) return;
    const s = SK[sp];
    const rc = reliefAt(tb);
    const yaw = tb.yaw + s.yawOff;
    tb.a.state(T.empty);
    const sk = scene.spawn(s.actor, rc, { yaw, state: s.states.emerge });
    sound(dim, "ed5_peel", rc, 1.2);
    burst(dim, `ed5_burst_${sp}`, rc, 1.5, 4);
    particle(dim, "ed5_bonedust", rc);
    const out = outward(sp);
    const t0 = scene.tick;
    if (land) {
      const drift = add(rc, out);
      scene.span(t0, t0 + secs(2.15), (p) => {
        const tt = p * 2.15;
        const pos = tt < 0.7 ? lerp(rc, drift, smooth(tt / 0.7)) : bezier(drift, midUp(drift, land, 3), land, smooth((tt - 0.7) / 1.45));
        sk.move(pos, yaw);
      });
      scene.at(t0 + secs(2.1), () => { particle(dim, "ed5_bonedust", up(land, 0.3)); particle(dim, `ed5_ring_${sp}`, up(land, 0.2)); });
    } else {
      const exit = up(add(rc, mul(out, 5)), 1.5);
      scene.span(t0, t0 + secs(s.emerge), (p) => {
        const tt = p * s.emerge;
        sk.move(tt < 0.5 ? rc : bezier(rc, add(rc, mul(out, 3.5)), exit, smooth((tt - 0.5) / (s.emerge - 0.5))), yaw);
      });
    }
    scene.at(t0 + secs(s.emerge), () => done(sk));
  }

  /** Folds back into the relief (the reverse of emerge) and the tablet receives it. */
  function returnHome(sp: Species, sk: Actor): void {
    const tb = tabs[sp];
    if (!tb) return;
    const s = SK[sp];
    const rc = reliefAt(tb);
    const from = sk.loc;
    const yaw0 = sk.yaw, yaw1 = tb.yaw + s.yawOff;
    const airy = sp === "air";
    sk.state(s.states.return);
    const ctl = midUp(from, rc, airy ? 2 : 6);
    const t0 = scene.tick, n = secs(s.ret);
    const a0 = airy ? 0.1 : 0.45, a1 = airy ? 1.3 : 1.55;
    scene.span(t0, t0 + n, (p) => {
      const tt = p * s.ret;
      sk.move(bezier(from, ctl, rc, smooth((tt - a0) / (a1 - a0))), yawLerp(yaw0, yaw1, smooth(tt / (airy ? 0.9 : 0.6))));
    });
    scene.at(t0 + n, () => {
      tb.a.state(T.receive);
      sound(dim, "ed5_settle", rc, 1.1);
      burst(dim, `ed5_burst_${sp}`, rc, 1.2, 4);
    });
    scene.at(t0 + n + 1, () => scene.despawn(sk));
  }

  function awaken(sp: Species): void {
    const tb = tabs[sp];
    if (!tb) return;
    tb.a.skin(1).state(T.awaken);
    sound(dim, "ed5_awaken", faceAt(tb), 1.2, 0.9 + SLOT[sp] * 0.07);
    burst(dim, `ed5_mote_${sp}`, faceAt(tb), 3, 3);
  }

  for (const sp of SPECIES) {
    const tE = at(C.emergeAt[sp]);
    scene.at(tE - at(C.awakenLead), () => awaken(sp));
    scene.at(tE, () => {
      const tb = tabs[sp];
      if (!tb) return;
      if (sp === "air") { emerge(sp, undefined, (sk) => actAir(sk)); return; }
      const land = gnd(add(center, mul(outward(sp), C.landDistance[sp])));
      const yaw = tb.yaw + SK[sp].yawOff;
      emerge(sp, land, (sk) => {
        if (sp === "nature") actNature(sk, land, yaw);
        else if (sp === "heat") actHeat(sk, land, yaw);
        else actTide(sk, land, yaw);
      });
    });
  }

  // ---- Nature: rear and slam the forelimb (stone spikes along shock lines), then a low neck sweep
  function actNature(sk: Actor, L: V3, yaw: number): void {
    const s = SK.nature, lv = s.living;
    const slamPt = local(L, yaw, 3, 0, -5);
    sk.state(s.states.attack_a);
    warnAt(slamPt, C.slamRadius, secs(lv.hitA), true);
    scene.after(secs(lv.hitA), () => {
      sound(dim, "ed5_slam", slamPt, 1.5);
      particle(dim, "ed5_ring_nature", up(slamPt, 0.2));
      particle(dim, "fx_shock", up(slamPt, 0.3));
      burst(dim, "ed5_rock", up(slamPt, 0.8), 2, 4);
      particle(dim, "ed5_dust", up(slamPt, 0.6));
      hit(slamPt, C.slamRadius, C.slamDamage, { kb: C.slamKnock, kv: 0.5 });
      const foes = hostiles(dim, slamPt, 13, caster, C.slamLines);
      const dirs = foes.map((e) => yawOf(sub(e.location, slamPt)));
      const spread = [0, -38, 38, -70, 70];
      for (let k = 0; dirs.length < C.slamLines; k++) dirs.push(yaw + spread[k % spread.length]);
      const once = new Set<string>();
      dirs.forEach((dy, li) => {
        const d = fromYaw(dy);
        for (let j = 0; j < C.spikesPerLine; j++) {
          const p = add(slamPt, mul(d, C.spikeFirst + j * C.spikeSpacing));
          scene.after(2 + j * 3 + li, () => {
            particle(dim, "ed5_line", up(gnd(p), 0.25));
            spikeAt(p, C.spikeDamage, C.spikeRadius, C.spikeLift, once);
          });
        }
      });
    });
    const tB = secs(lv.attackA) + 2;
    const sweepC = local(L, yaw, 0, 0, -12);
    scene.after(tB, () => { sk.state(s.states.attack_b); warnAt(sweepC, 7, secs(lv.hitB)); });
    scene.after(tB + secs(lv.hitB), () => {
      sound(dim, "ed5_slam", sweepC, 1.0, 1.25);
      const left = mul(right(fromYaw(yaw)), -1);
      const once = new Set<string>();
      hit(L, C.sweepMaxReach + 1, C.sweepDamage, {
        once, kb: C.sweepKnock, kv: 0.4, from: add(sweepC, mul(left, -6)),
        test: (e) => inSector(e.location, L, yaw, C.sweepHalfAngle, C.sweepMinReach, C.sweepMaxReach),
      });
      [60, 25, -10, -45].forEach((a, k) => scene.after(k * 2, () => {
        const p = add(L, mul(fromYaw(yaw + a), 12));
        particle(dim, "ed5_line", up(gnd(p), 0.25));
        spikeAt(p, C.spikeDamage, C.spikeRadius, C.spikeLift, once, 1.2, 0.8);
      }));
    });
    scene.after(tB + secs(lv.attackB) + 2, () => returnHome("nature", sk));
  }

  // ---- Heat: roar, then two telegraphed charges that leave burning trackways
  function actHeat(sk: Actor, L: V3, yaw0: number): void {
    const s = SK.heat, lv = s.living;
    sk.state(s.states.roar);
    const len1 = Math.min(24, 2 * C.laneReach);
    const trail1 = scene.spawn(P.trail.actor, L, { yaw: yaw0, state: P.trail.states.warn });
    trail1.prop("len", len1);
    sound(dim, "ed5_burn", L, 0.6, 0.8);
    scene.after(secs(lv.roar), () => charge(sk, L, yaw0, len1, trail1, (end) => {
      skidTurn(sk, end, yaw0, (pos, yaw1) => {
        const trail2 = scene.spawn(P.trail.actor, pos, { yaw: yaw1, state: P.trail.states.warn });
        const target = add(center, mul(right(fromYaw(yaw0)), C.laneOffset));
        const len2 = Math.min(24, dist(flat(pos), flat(target)) + C.laneReach);
        trail2.prop("len", len2);
        scene.after(secs(lv.turn) + 2, () => charge(sk, pos, yaw1, len2, trail2, (end2) => {
          skidTurn(sk, end2, yaw1, () => returnHome("heat", sk), false);
        }));
      }, true);
    }));
  }
  function charge(sk: Actor, from: V3, yaw: number, length: number, trail: Actor, done: (end: V3) => void): void {
    const s = SK.heat;
    const n = Math.max(4, secs(length / s.living.runSpeed));
    const dir = fromYaw(yaw);
    const end = add(from, mul(dir, length));
    sk.state(s.states.charge);
    trail.state(P.trail.states.burn);
    sound(dim, "ed5_burn", from, 1.0);
    const once = new Set<string>();
    let reached = from;
    const t0 = scene.tick;
    scene.span(t0, t0 + n, (p, e) => {
      const pos = lerp(from, end, p);
      reached = pos;
      sk.move(pos, yaw);
      hit(pos, C.chargeRadius, C.chargeDamage, { once, from: sub(pos, mul(dir, 2)), kb: C.chargeKnock, kv: 0.45 });
      if (e % 2 === 0) particle(dim, "ed5_haze", up(pos, 0.6));
      if (e % 3 === 0) particle(dim, "ed5_ember", up(pos, 2.5));
    });
    scene.every(C.burnEvery, () => {
      const mid = lerp(from, reached, 0.5);
      for (const e of hostiles(dim, mid, dist(from, reached) / 2 + C.burnRadius + 1, caster)) {
        if (distToSegment(e.location, from, reached) > C.burnRadius) continue;
        damage(e, C.burnDamage, caster);
        try { if (e.isValid) e.setOnFire(C.burnFireSeconds, true); } catch { /* immune */ }
      }
      for (const f of [0.2, 0.5, 0.8]) particle(dim, "ed5_haze", up(lerp(from, reached, f), 0.4));
    }, t0 + 2, t0 + n + secs(C.burnSeconds));
    scene.at(t0 + n, () => done(end));
    scene.at(t0 + n + secs(C.burnSeconds), () => trail.state(P.trail.states.fade));
    scene.at(t0 + n + secs(C.burnSeconds + P.trail.fade) + 1, () => scene.despawn(trail));
  }
  function skidTurn(sk: Actor, from: V3, yaw: number, next: (pos: V3, yaw: number) => void, turn: boolean): void {
    const s = SK.heat, lv = s.living;
    const to = add(from, mul(fromYaw(yaw), 2));
    sk.state(s.states.skid);
    sound(dim, "ed5_skid", from, 1.0);
    burst(dim, "ed5_bonedust", up(from, 0.3), 1.2, 3);
    const t0 = scene.tick, n = secs(lv.skid);
    scene.span(t0, t0 + n, (p) => sk.move(lerp(from, to, easeOut(p)), yaw));
    if (!turn) { scene.at(t0 + n, () => next(to, yaw)); return; }
    scene.at(t0 + n, () => {
      const target = add(center, mul(right(fromYaw(yaw)), C.laneOffset));
      const yaw1 = yawOf(sub(target, to));
      const dy = angleDelta(yaw, yaw1);
      sk.state(dy >= 0 ? s.states.turn_r : s.states.turn_l);
      const n2 = secs(lv.turn);
      scene.span(scene.tick, scene.tick + n2, (p) => sk.move(to, yawLerp(yaw, yaw1, p)));
      next(to, yaw1);
    });
  }

  // ---- Tide: tail lash and sail flare throw fans of ice crystals
  function actTide(sk: Actor, L: V3, yaw: number): void {
    const s = SK.tide, lv = s.living;
    const walkTo = add(L, mul(fromYaw(yaw), lv.walkSpeed * C.tideWalk));
    sk.state(s.states.move);
    const t0 = scene.tick, nW = secs(C.tideWalk);
    scene.span(t0, t0 + nW, (p) => sk.move(lerp(L, walkTo, p), yaw));
    const yaw1 = yaw + 90;
    const tTurn = t0 + nW;
    scene.at(tTurn, () => {
      sk.state(s.states.turn_r);
      scene.span(scene.tick, scene.tick + secs(lv.turn), (p) => sk.move(walkTo, yawLerp(yaw, yaw1, smooth(p))));
      // the tail sweeps over the area behind it: warn where the two fans will land
      for (const sx of [2.5, -2.5]) warnAt(fanTarget(walkTo, yaw1, sx), 3.5, secs(lv.turn) + secs(lv.hitsA[0]));
    });
    const tA = tTurn + secs(lv.turn) + 1;
    scene.at(tA, () => sk.state(s.states.attack_a));
    lv.hitsA.forEach((h, k) => scene.at(tA + secs(h), () => {
      const o = local(walkTo, yaw1, k === 0 ? 2.5 : -2.5, 0, 7.5);
      iceFan(o, yawOf(sub(fanTarget(walkTo, yaw1, k === 0 ? 2.5 : -2.5), o)), C.fanSize, C.fanDamage, [C.fanSlowTicks, C.fanSlowAmp]);
    }));
    const tC = tA + secs(lv.attackA) + 2;
    scene.at(tC, () => sk.state(s.states.attack_c));
    scene.at(tC + secs(lv.hitC), () => {
      const once = new Set<string>();
      for (const side of [90, -90]) iceFan(local(walkTo, yaw1, side > 0 ? -1.5 : 1.5, 0, 0), yaw1 + side, C.fanSize, C.flareDamage,
        [C.fanSlowTicks, C.fanSlowAmp], once);
      burst(dim, "ed5_frost", up(walkTo, 5), 2.5, 5);
    });
    const tB = tC + secs(lv.attackC) + 2;
    scene.at(tB, () => sk.state(s.states.attack_b));
    scene.at(tB + secs(lv.hitB), () => {
      const tip = local(walkTo, yaw1, 0, 0, 10);
      iceFan(tip, yaw1 + 180, C.fanSize * 0.8, C.fanDamage, [C.fanSlowTicks, C.fanSlowAmp]);
      particle(dim, "ed5_ring_tide", up(gnd(tip), 0.2));
    });
    scene.at(tB + secs(lv.attackB) + 2, () => returnHome("tide", sk));
  }
  function fanTarget(pos: V3, yaw: number, sx: number): V3 {
    const toC = sub(center, pos);
    return distXZ(pos, center) > 2 ? add(center, mul(right(fromYaw(yaw)), sx * 0.4)) : add(local(pos, yaw, sx, 0, 6), toC);
  }

  // ---- Air: three low sweeps; every downstroke over the field sends a wind shockwave ring
  function actAir(sk: Actor): void {
    const s = SK.air;
    const tb = tabs.air;
    if (!tb) return;
    const out = outward("air");
    const start = sk.loc;
    const psi0 = polarOf(out) + 55;
    const R = C.passRadius, cy = center.y;
    const pts: V3[] = [start];
    for (let k = 0; k < 3; k++) {
      const psi = psi0 + 120 * k;
      pts.push(polar(center, R, psi, C.cruiseHeight));
      pts.push(polar(center, 1.5, psi + 90, C.passHeight));
      pts.push(polar(center, R, psi + 180, C.cruiseHeight - 1));
      if (k < 2) pts.push(polar(center, R * 1.4, psi + 150, C.cruiseHeight + 2));
    }
    const home = add(up(reliefAt(tb), 3), mul(out, 6));
    pts.push(home);
    const path = new Path(pts.map((p) => ({ ...p, y: Math.max(p.y, cy + 2) })));
    const n = secs(path.length / C.flySpeed);
    let state: number = s.states.move, want: number = state, wantN = 0, lastYaw = sk.yaw, ringCd = 6;
    sk.state(state);
    const t0 = scene.tick;
    scene.span(t0, t0 + n, (p, e) => {
      const sPos = p * path.length;
      const pos = path.at(sPos);
      const yaw = yawOf(path.dir(sPos));
      const dy = angleDelta(lastYaw, yaw);
      lastYaw = yaw;
      const near = distXZ(pos, center) < C.ringReach;
      const w = near ? s.states.move : Math.abs(dy) > 2.0 ? (dy > 0 ? s.states.turn_r : s.states.turn_l) : s.states.glide;
      if (w === want) wantN++; else { want = w; wantN = 0; }
      if (want !== state && wantN >= 3) { state = want; sk.state(state); }
      sk.move(pos, yaw);
      if (e % 4 === 0) particle(dim, "ed5_feather", pos);
      if (state === s.states.move && near) {
        if (--ringCd <= 0) { ringCd = secs(s.living.flap); gust(pos, 1.0, C.ringDamage, C.ringRadius, C.ringKnock); }
      } else ringCd = 6;
    });
    scene.at(t0 + n, () => returnHome("air", sk));
  }

  // ================================================================ PHASE III - The Eternal Imprint
  const formation: Partial<Record<Species, { pos: V3; yaw: number }>> = {};
  scene.at(at(C.phase3At), () => {
    if (memorial) {
      memorial.state(P.memorial.states.dissolve);
      const m = memorial;
      scene.after(secs(P.memorial.dissolve) + 1, () => scene.despawn(m));
    }
    sound(dim, "ed5_blaze", up(center, C.memorialHeight + 4), 1.4);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      const fpos = polar(center, C.fanRadius, phiF + C.formationAngle[sp], C.formationHeight[sp]);
      const fyaw = yawOf(sub(center, fpos));
      formation[sp] = { pos: fpos, yaw: fyaw };
      tb.a.skin(2).state(T.formation);
      const from = tb.pos, y0 = tb.yaw, ctl = midUp(from, fpos, 6);
      const t0 = scene.tick, n = secs(C.formationTime);
      scene.span(t0, t0 + n, (p) => {
        tb.pos = bezier(from, ctl, fpos, smooth(p));
        tb.yaw = yawLerp(y0, fyaw, smooth(p));
        tb.a.move(tb.pos, tb.yaw);
      });
      scene.at(t0 + n, () => tb.a.state(T.aim));
      burst(dim, `ed5_mote_${sp}`, faceAt(tb), 3, 3);
    }
  });

  function imprintEffect(sp: Species, imp: V3, yaw: number, size: number, once: Set<string>): void {
    const o = ED5_IMPRINT.outline[sp];
    const toW = (q: readonly number[]): V3 => local(imp, yaw, q[0] * size, 0, q[1] * size);
    if (sp === "nature") {
      o.rim.forEach((q, k) => scene.after(k, () => spikeAt(toW(q), C.p3SpikeDamage, C.p3SpikeRadius, 0.8, once, 1.3, 1.1)));
    } else if (sp === "heat") {
      const pts = [...o.rim, ...o.fill].map(toW);
      scene.every(C.brandEvery, (e) => {
        const seen = new Set<string>();
        for (const e2 of hostiles(dim, imp, 12, caster)) {
          if (seen.has(e2.id) || !pts.some((p) => distXZ(p, e2.location) < C.brandRadius)) continue;
          seen.add(e2.id);
          damage(e2, C.brandDamage, caster);
          try { if (e2.isValid) e2.setOnFire(C.brandFireSeconds, true); } catch { /* immune */ }
        }
        particle(dim, "ed5_ember", up(pts[(e * 3) % pts.length], 0.4));
        particle(dim, "ed5_haze", up(pts[(e * 7 + 5) % pts.length], 0.3));
      }, scene.tick, scene.tick + secs(C.brandSeconds));
      sound(dim, "ed5_burn", imp, 1.2, 0.8);
    } else if (sp === "tide") {
      iceFan(local(imp, yaw, 0, 0, P.icefan.reach * C.p3FanSize * 0.45), yaw, C.p3FanSize, C.p3FanDamage,
        [C.p3FanSlowTicks, C.p3FanSlowAmp], once, 1.4);
      for (const q of o.fill.slice(0, 6)) particle(dim, "ed5_frost", up(toW(q), 0.8));
    } else {
      for (const q of o.rim.slice(0, 4)) gust(toW(q), 1.3, C.galeDamage, C.galeRadius, C.galeKnock, once, C.galeLevitate);
      gust(imp, 1.6, C.galeDamage, C.galeRadius, C.galeKnock, once, C.galeLevitate);
    }
  }

  function projectFrom(sp: Species, tHit: number, imp: V3, yaw: number, all: boolean): void {
    const tW = tHit - at(C.projectWarn);
    let im: Actor | undefined;
    scene.at(tW, () => {
      const tb = tabs[sp];
      if (!tb) return;
      tb.a.state(all ? T.project_all : T.project);
      im = scene.spawn(ED5_IMPRINT.actors[sp], imp, { yaw, size: C.imprintSize, state: IMP.warn });
      if (!all) sound(dim, "ed5_project", up(imp, 2), 1.3, 0.92 + SLOT[sp] * 0.05);
      scene.every(3, () => line(dim, `ed5_ray_${sp}`, faceAt(tb), up(imp, 0.4), all ? 5 : 8), scene.tick, tHit + 4);
    });
    scene.at(tHit, () => {
      im?.state(IMP.brand);
      particle(dim, `ed5_ring_${sp}`, up(imp, 0.3));
      if (!all) imprintEffect(sp, imp, yaw, C.imprintSize, new Set<string>());
    });
    scene.at(tHit + 10, () => im?.state(IMP.pulse));
    const hold = sp === "heat" ? C.brandSeconds : 1.4;
    scene.at(tHit + secs(hold), () => { im?.state(IMP.fade); tabs[sp]?.a.state(T.aim); });
    scene.at(tHit + secs(hold + 0.6) + 1, () => { if (im) scene.despawn(im); });
  }

  for (const sp of SPECIES) {
    scene.at(at(C.projectAt[sp]) - at(C.projectWarn) - 1, () => {
      const f = formation[sp];
      const imp = gnd(f ? add(center, mul(norm(flat(sub(f.pos, center))), 1.5)) : center);
      projectFrom(sp, at(C.projectAt[sp]), imp, f ? f.yaw : 0, false);
    });
  }

  // ---- all four together: the images converge on the centre
  const tAll = at(C.allAt);
  scene.at(tAll - at(C.projectWarn) - 1, () => {
    const g = gnd(center);
    SPECIES.forEach((sp, k) => projectFrom(sp, tAll, g, (formation[sp]?.yaw ?? 0) + k * 12, true));
  });
  scene.at(tAll - secs(0.8), () => sound(dim, "ed5_finale", up(center, 2), 1.6));
  scene.at(tAll, () => {
    const g = gnd(center);
    const once = new Set<string>();
    hit(g, C.finaleRadius, C.finaleDamage, { once, kb: C.finaleKnock, kv: 0.6, slow: [C.p3FanSlowTicks, C.p3FanSlowAmp], fire: 2 });
    const o = ED5_IMPRINT.outline.nature;
    o.rim.slice(0, 8).forEach((q, k) => scene.after(k, () => spikeAt(local(g, phiF, q[0], 0, q[1]), 0, 1, 0.5, once, 1.2, 1.2)));
    iceFan(g, yawOf(fwd), C.p3FanSize * 0.8, 0, [C.p3FanSlowTicks, C.p3FanSlowAmp], once, 1.2);
    for (let k = 0; k < 4; k++) scene.after(3 + k * 2, () => gust(polar(g, 4.5, phiF + 45 + k * 90), 1.4, 0, 4, C.finaleKnock, once));
    burst(dim, "ed5_frag", up(g, 3), 3, 6);
    particle(dim, "fx_flash", up(g, 2));
  });

  // ---- the tablets crack along their strata into luminous fossil fragments that rain and fade
  const tF = at(C.fractureAt);
  scene.at(tF, () => {
    sound(dim, "ed5_fracture", up(center, 10), 1.6);
    for (const sp of SPECIES) {
      const tb = tabs[sp];
      if (!tb) continue;
      tb.a.state(T.fracture);
      burst(dim, "ed5_frag_big", faceAt(tb), 2.5, 4);
      burst(dim, `ed5_burst_${sp}`, faceAt(tb), 2, 4);
    }
  });
  scene.at(tF + 8, () => sound(dim, "ed5_rain", up(center, 6), 1.0));
  scene.every(4, (e) => {
    const a = e * 2.39996, r = 2 + ((e * 7) % 10);
    particle(dim, "ed5_frag", { x: center.x + Math.cos(a) * r, y: center.y + 12, z: center.z + Math.sin(a) * r });
  }, tF + 4, tF + secs(2.4));
  scene.at(tF + secs(ED5_TABLET.len.fracture) + 2, () => {
    for (const sp of SPECIES) { const tb = tabs[sp]; if (tb) scene.despawn(tb.a); }
  });
  scene.endAt(at(C.endAt));
});
