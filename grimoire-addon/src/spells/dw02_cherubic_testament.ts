import { Entity, Vector3 } from "@minecraft/server";
import { DW02 as C } from "../config/dw02";
import { CONFIG } from "../config/global";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, knockback, removeWard, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import { add, distXZ, dot, easeIn, flat, lerp, mul, norm, polar, right, sub, up, yawOf, fromYaw } from "../lib/vec";

// Cherubim animation states (tools/assets/dw_cherub.py STATES)
const S = { hidden: 0, arrive: 1, idle: 2, human: 3, ox: 4, oxRetaliate: 5, lion: 6, eagle: 7, verdict: 8, depart: 9 };
// helper actors (dw_cherub.py BLADE_STATES / roar states) and the shared sacred mark (dw_common.py)
const BLADE = { hidden: 0, form: 1, aim: 2, dive: 3, shatter: 4 };
const MARK = { appear: 1, hold: 2, burst: 3 };
// animation timings in seconds, mirrored from dw_cherub.py
const T = {
  arrive: 1.6, humanCast: 1.05, human: 1.6, oxLock: 0.75, ox: 1.0, retBlast: 0.3, retaliate: 1.0,
  lionRoar: 0.95, lion: 1.8, eagleThrust: [1.6, 2.5], eagle: 2.8, depart: 1.8,
  bladeForm: 0.6, bladeShatter: 0.5, roarLife: 1.0,
};

interface Witnessed { e: Entity; mark?: Actor; n: number }

/**
 * DW02 - Cherubic Testament: The Four Living Witnesses.
 * A colossal four-faced Cherubim is assembled from rings of letters.  Its body keeps one heading
 * while the crown of faces turns: the Human writes glyphs that mark enemies, the Ox folds all four
 * wings into a wall that absorbs harm and answers with a shockwave, the Lion roars rings of letters
 * that strike and hurl enemies away, and the Eagle sends feather-blades diving onto the marked.
 */
export default defineSpell("dw02", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.focusSnap);
  const left = mul(right(aim.forward), -1);
  const anchor = groundBelow(dim, add(add(caster.location, mul(aim.forward, C.standForward)), mul(left, C.standSide)));
  const toward = flat(sub(center, anchor));
  const fwd = Math.hypot(toward.x, toward.z) > 2 ? norm(toward) : aim.forward;
  const yaw = yawOf(fwd);
  const side = right(fwd); // the Cherubim's own right hand
  const lights = blocksFor(scene);
  const witnessed = new Map<string, Witnessed>();
  const phantoms: Actor[] = [];

  // -------------------------------------------------------------------------------- manifestation
  const circle = scene.spawn("dw_circle", anchor, { size: 2.4, state: 1 });
  const cherub = scene.spawn("cherub", anchor, { yaw, state: S.arrive });
  sound(dim, "dw_cherub_arrive", anchor, 1.3);
  sound(dim, "dw_circle", anchor, 0.8);
  ring(dim, "dw_glyph_rise", up(anchor, 0.5), 3.5, 8);
  scene.at(8, () => circle.state(2));
  scene.at(14, () => { particle(dim, "fx_flash", up(anchor, 7)); burst(dim, "dw_glyph_rise", up(anchor, 5), 3, 8); });
  lights.place(up(anchor, 3), LIGHT);
  const censer = add(up(anchor, 7.6), mul(fwd, -1.5));
  scene.every(6, () => particle(dim, "dw_cherub_ember", censer), 20, 9999);

  const tHuman = secs(T.arrive) - 2;
  const tOx = tHuman + secs(T.human) - 2;
  const tWard = tOx + secs(T.oxLock);
  const tRet = tWard + C.wardTicks;
  const tLion = tRet + secs(T.retaliate) - 2;
  const tRoar = tLion + secs(T.lionRoar);
  const tEagle = tRoar + 15;
  const dives = T.eagleThrust.map((s) => tEagle + secs(s));
  const tDepart = dives[1] + C.diveTicks + 8;

  function turn(): void { sound(dim, "dw_cherub_turn", up(anchor, 10), 1.0); }
  function boost(e: Entity, base: number, bonus: number): number { return witnessed.get(e.id)?.mark ? base * bonus : base; }

  // -------------------------------------------------------------------------------- FIRST - HUMAN
  scene.at(tHuman, () => {
    cherub.state(S.human);
    sound(dim, "dw_cherub_human", up(anchor, 10), 1.3);
  });
  const hand = add(add(up(anchor, 12.5), mul(side, 1.8)), mul(fwd, 0.8));
  let markTargets: Entity[] = [];
  scene.at(tHuman + 6, () => { markTargets = hostiles(dim, center, C.markRadius, caster, C.maxMarks); });
  // the raised hand writes: letters gather at the palm and stream out toward each enemy
  scene.every(3, (el) => {
    particle(dim, "dw_cherub_glyph", hand);
    const p = Math.min(1, el / 14);
    for (const e of markTargets) {
      if (!isAlive(e)) continue;
      const to = up(e.location, 1.6);
      particle(dim, "dw_cherub_glyph", lerp(hand, to, p));
      if (p > 0.3) particle(dim, "dw_cherub_glyph", lerp(hand, to, p - 0.25));
    }
  }, tHuman + 7, tHuman + secs(T.humanCast));
  scene.at(tHuman + secs(T.humanCast), () => {
    const found = markTargets.filter((e) => isAlive(e));
    for (const e of found) {
      const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK.appear, skin: 0 });
      scene.follow(mark, e, 2.4);
      scene.after(6, () => mark.state(MARK.hold));
      witnessed.set(e.id, { e, mark, n: 0 });
      damage(e, C.markDamage, caster);
      particle(dim, "dw_halo", up(e.location, 1.2));
      sound(dim, "dw_cherub_glyph", e.location, 0.8, 1 + witnessed.size * 0.05);
    }
    if (!found.length) {
      // no enemies: the testament is still written - three sigils settle on the ground ahead
      for (let k = 0; k < 3; k++) {
        const at = groundBelow(dim, polar(center, 3.5, k * 120 + yaw));
        phantoms.push(scene.spawn("dw_mark", up(at, 1.4), { state: MARK.appear, skin: 0 }));
        sound(dim, "dw_cherub_glyph", at, 0.7, 0.9 + k * 0.1);
      }
      scene.after(6, () => phantoms.forEach((m) => m.state(MARK.hold)));
    }
    line(dim, "dw_cherub_glyph", hand, up(center, 2), 6);
  });

  // -------------------------------------------------------------------------------- SECOND - OX
  let stored = 0;
  scene.at(tOx, () => {
    cherub.state(S.ox);
    turn();
    sound(dim, "dw_cherub_ox", up(anchor, 9), 1.3);
  });
  scene.at(tWard, () => {
    sound(dim, "dw_cherub_shield", add(up(anchor, 5), mul(fwd, 2)), 1.2);
    burst(dim, "dw_cherub_feather", add(up(anchor, 6), mul(fwd, 2.5)), 2.5, 5);
    particle(dim, "dw_cherub_shield", up(caster.location, 1));
    const ward = addWard({
      scene,
      factor: 1 - C.wardStrength,
      pool: C.wardPool,
      protects: (e) => e.id === caster.id ||
        (e.typeId === "minecraft:player" && !CONFIG.targeting.pvp && distXZ(e.location, anchor) <= C.wardRadius),
      onAbsorb: (amount, attacker, victim) => {
        stored += attacker ? amount : amount * C.envAbsorbShare;
        if (victim.isValid) particle(dim, "dw_cherub_absorb", up(victim.location, 1));
        sound(dim, "dw_cherub_absorb", victim.isValid ? victim.location : anchor, 0.9);
      },
      onBreak: () => {
        sound(dim, "dw_cherub_retaliate", up(anchor, 4), 0.6, 1.3);
        burst(dim, "dw_cherub_shatter", add(up(anchor, 5), mul(fwd, 2.5)), 1.5, 3);
      },
    });
    scene.at(tRet, () => removeWard(ward));
  });
  // the wall dissolves hostile projectiles around the formation and the caster
  scene.every(4, () => {
    const gone = [...dissolveProjectiles(scene, anchor, C.wardRadius), ...dissolveProjectiles(scene, caster.location, 4)];
    for (const p of gone) { stored += C.projectileCharge; particle(dim, "dw_cherub_absorb", p); }
  }, tWard, tRet);
  scene.every(8, (el) => {
    const a = (el * 23) % 120 - 60;
    particle(dim, "dw_cherub_shield", add(up(anchor, 4 + (el % 3)), mul(fromYaw(yaw + a), 3)));
    if (caster.isValid) particle(dim, "dw_cherub_shield", up(caster.location, 1));
  }, tWard, tRet);
  // the retaliation is telegraphed while the wall still holds
  let quakeSigil: Actor | undefined;
  scene.at(tRet - 40, () => { quakeSigil = scene.spawn("telegraph", anchor, { kind: 0, size: C.retaliateRadius, state: 4 }); });
  scene.at(tRet, () => { cherub.state(S.oxRetaliate); });
  scene.at(tRet + secs(T.retBlast), () => {
    const dmg = Math.min(C.retaliateMax, C.retaliateBase + stored * C.retaliateScale);
    sound(dim, "dw_cherub_retaliate", up(anchor, 3), 1.4, stored > 0 ? 0.9 : 1.0);
    particle(dim, "dw_cherub_quake", up(anchor, 0.2));
    particle(dim, "fx_shock", up(anchor, 0.4));
    particle(dim, "dw_cherub_dust", up(anchor, 0.3));
    ring(dim, "dw_cherub_feather", up(anchor, 5), 4, 6);
    if (quakeSigil) { quakeSigil.state(3); const q = quakeSigil; scene.after(8, () => scene.despawn(q)); }
    for (const e of hostiles(dim, anchor, C.retaliateRadius, caster)) {
      damage(e, boost(e, dmg, C.markBonus), caster);
      knockback(e, anchor, C.retaliateKnock, C.retaliateLift);
    }
  });

  // -------------------------------------------------------------------------------- THIRD - LION
  const mouth = add(up(anchor, C.mouthHeight), mul(fwd, C.mouthForward));
  const cone: Actor[] = [];
  scene.at(tLion, () => {
    cherub.state(S.lion);
    turn();
    // the roar is telegraphed along its path while the lion draws breath
    for (const d of [5, 10]) cone.push(scene.spawn("telegraph", groundBelow(dim, add(anchor, mul(fwd, d))), { kind: 0, size: 2 + d * 0.25, state: 1 }));
  });
  scene.at(tRoar - 4, () => sound(dim, "dw_cherub_lion", mouth, 1.6));
  const roared = new Set<string>();
  function inCone(e: Entity): number | undefined {
    const v = flat(sub(e.location, anchor));
    const d = Math.hypot(v.x, v.z);
    const along = dot(v, fwd);
    if (d > C.roarRange || d < 0.01) return undefined;
    if (along / d < Math.cos((C.roarHalfAngle * Math.PI) / 180)) return undefined;
    return along;
  }
  function roarHit(e: Entity): void {
    if (roared.has(e.id)) return;
    roared.add(e.id);
    damage(e, boost(e, C.roarDamage, C.markBonus), caster);
    shove(e, norm(add(fwd, mul(norm(flat(sub(e.location, anchor))), 0.6))), C.roarKnock, C.roarLift);
    particle(dim, "dw_spark", up(e.location, 1));
  }
  scene.at(tRoar, () => {
    particle(dim, "dw_cherub_breath", mouth);
    particle(dim, "dw_cherub_roar", mouth);
    particle(dim, "dw_cherub_dust", anchor);
    cone.forEach((t) => t.state(3));
    scene.after(8, () => cone.forEach((t) => scene.despawn(t)));
    for (const e of hostiles(dim, anchor, C.roarNear, caster)) { roarHit(e); knockback(e, anchor, C.roarKnock, C.roarLift); }
  });
  const travel = Math.round(C.roarRange / C.roarSpeed);
  for (let k = 0; k < 3; k++) {
    const t0 = tRoar + k * C.roarRingGap;
    const end = groundBelow(dim, add(anchor, mul(fwd, C.roarRange)));
    let ringActor: Actor | undefined;
    scene.at(t0, () => {
      ringActor = scene.spawn("dw_cherub_roar", mouth, { yaw, state: 1 });
      sound(dim, "dw_cherub_ring", mouth, 0.9, 0.9 + k * 0.1);
    });
    scene.span(t0, t0 + travel, (p, el) => {
      const pos = lerp(mouth, up(end, 2.5), p);
      ringActor?.move(pos, yaw);
      if (el % 3 === 0) particle(dim, "dw_cherub_roar", pos);
      const front = C.roarSpeed * (el + 1), back = front - C.roarSpeed - 1.2;
      for (const e of hostiles(dim, anchor, C.roarRange + 1, caster)) {
        const along = inCone(e);
        if (along === undefined || along > front || along < back) continue;
        if (k === 0) roarHit(e);
        else shove(e, fwd, C.roarEchoPush, 0.2);
      }
    });
    scene.at(t0 + travel, () => {
      if (ringActor) { ring(dim, "dw_glyph_rise", ringActor.loc, 2.5, 6); scene.despawn(ringActor); }
    });
  }

  // -------------------------------------------------------------------------------- FOURTH - EAGLE
  scene.at(tEagle, () => {
    cherub.state(S.eagle).skin(1); // feathers ignite into blades
    turn();
    burst(dim, "dw_cherub_feather", up(anchor, 9), 4, 6);
  });
  scene.at(tEagle + 10, () => sound(dim, "dw_cherub_eagle", up(anchor, 11), 1.5));

  function waveTargets(wave: number): { e?: Entity; at: Vector3 }[] {
    const out: { e?: Entity; at: Vector3 }[] = [];
    const used = new Set<string>();
    for (const w of witnessed.values()) {
      if (out.length >= C.bladesPerWave) break;
      if (isAlive(w.e)) { out.push({ e: w.e, at: groundBelow(dim, w.e.location) }); used.add(w.e.id); }
    }
    if (wave === 1 || !out.length) {
      for (const e of hostiles(dim, center, C.bladeSearch, caster)) {
        if (out.length >= C.bladesPerWave) break;
        if (!used.has(e.id)) out.push({ e, at: groundBelow(dim, e.location) });
      }
    }
    if (!out.length) {
      // nothing to judge: the blades fall on the written sigils (or a ring ahead)
      const spots = phantoms.length ? phantoms.map((m) => groundBelow(dim, m.loc)) : [0, 1, 2].map((k) => polar(center, 3, k * 120));
      spots.slice(0, wave === 0 ? 3 : 2).forEach((at, k) => out.push({ at: wave ? polar(at, 1.5, k * 90 + 45) : at }));
    }
    return out;
  }

  function blade(target: { e?: Entity; at: Vector3 }, diveAt: number, idx: number): void {
    let at = target.at;
    const bladeYaw = yaw + idx * 47;
    const b = scene.spawn("dw_cherub_blade", up(at, C.bladeHeight), { yaw: bladeYaw, state: BLADE.form });
    const sigil = scene.spawn("telegraph", at, { kind: 0, size: C.bladeRadius, state: 1 });
    sound(dim, "dw_cherub_blade", up(at, C.bladeHeight), 0.9, 0.95 + idx * 0.04);
    particle(dim, "dw_cherub_glyph", up(at, C.bladeHeight));
    scene.after(secs(T.bladeForm), () => b.state(BLADE.aim));
    // blade and sigil track their enemy until the dive is committed
    scene.every(1, () => {
      if (target.e && isAlive(target.e)) { at = groundBelow(dim, target.e.location); sigil.move(at); }
      b.move(up(at, C.bladeHeight), bladeYaw);
    }, scene.tick + 1, diveAt);
    scene.at(diveAt, () => { b.state(BLADE.dive); sound(dim, "dw_cherub_dive", up(at, C.bladeHeight * 0.5), 1.0); });
    scene.span(diveAt, diveAt + C.diveTicks, (p) => {
      const pos = up(at, C.bladeHeight * (1 - easeIn(p)));
      b.move(pos, bladeYaw);
      particle(dim, "dw_cherub_trail", up(pos, 1.5));
    });
    scene.at(diveAt + C.diveTicks, () => {
      b.move(at, bladeYaw).state(BLADE.shatter);
      sigil.state(3);
      sound(dim, "dw_cherub_impact", at, 1.1);
      particle(dim, "dw_cherub_shatter", up(at, 0.6));
      particle(dim, "dw_ring", up(at, 0.2));
      particle(dim, "fx_flash", up(at, 1));
      for (const e of hostiles(dim, at, C.bladeRadius, caster)) {
        const w = witnessed.get(e.id);
        if (!damage(e, boost(e, C.bladeDamage, C.bladeMarkBonus), caster)) continue;
        knockback(e, at, C.bladeKnock, 0.3);
        if (w?.mark?.valid) { w.n++; w.mark.skin(Math.min(2, w.n)); }
      }
      scene.after(secs(T.bladeShatter) + 2, () => { scene.despawn(b); scene.despawn(sigil); });
    });
  }
  dives.forEach((diveAt, wave) => {
    scene.at(diveAt - C.bladeWarn, () => waveTargets(wave).forEach((t, i) => blade(t, diveAt, i + wave * 3)));
  });

  // -------------------------------------------------------------------------------- departure
  scene.at(tDepart, () => {
    cherub.state(S.depart).skin(0);
    circle.state(3);
    sound(dim, "dw_cherub_depart", up(anchor, 8), 1.2);
    ring(dim, "dw_glyph_rise", up(anchor, 2), 3, 8);
    for (const w of witnessed.values()) if (w.mark?.valid) { w.mark.state(MARK.burst); }
    phantoms.forEach((m) => m.state(MARK.burst));
  });
  scene.at(tDepart + 8, () => {
    for (const w of witnessed.values()) if (w.mark) scene.despawn(w.mark);
    phantoms.forEach((m) => scene.despawn(m));
  });
  scene.at(tDepart + 24, () => { burst(dim, "dw_glyph_rise", up(anchor, 12), 3, 8); scene.despawn(circle); });
  scene.endAt(tDepart + secs(T.depart) + 2);
});
