import { Entity } from "@minecraft/server";
import { DW05 as C } from "../config/dw05";
import { CONFIG } from "../config/global";
import { defineSpell } from "../core/registry";
import { addWard, damage, dissolveProjectiles, effect, knockback, removeWard, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import { LIGHT, blocksFor } from "../lib/tempblocks";
import {
  V3, add, angleDelta, bezier, clamp, dist, distToSegment, distXZ, dot, easeIn, flat, fromYaw, lerp, mul, norm, polar, right,
  smooth, sub, up, v, yawOf,
} from "../lib/vec";

// ---- state tables (tools/assets/dw5_throne.py, dw_seraph.py, dw_cherub.py, dw_ophanim.py, dw_common.py)
const GATE = { hidden: 0, manifest: 1, closed: 2, open: 3, opened: 4, close: 5, fold: 6 };
const SEN = { hidden: 0, unfold: 1, idle: 2, gather: 3 };
const THR = { hidden: 0, assemble: 1, idle: 2, declare: 3, unmake: 4 };
const LET = { hidden: 0, ignite: 1, hold: 2, plunge: 3, impact: 4 };
const SER = { hidden: 0, arrive: 1, veiled: 2, unfurl: 3, open: 4, chant1: 5, chant2: 6, chant3: 7, verdict: 8, depart: 9 };
const CHE = { hidden: 0, arrive: 1, idle: 2, human: 3, ox: 4, oxRetaliate: 5, lion: 6, eagle: 7, verdict: 8, depart: 9 };
const OPH = { hidden: 0, arrive: 1, survey: 2, lock: 3, sweep: 4, verdict: 5, depart: 6 };
const BLADE = { form: 1, aim: 2, dive: 3, shatter: 4 };
const MARK = { appear: 1, hold: 2, burst: 3 };
const LETTER_KINDS = 6;

// ---- animation timings in seconds, mirrored from the asset modules
const T = {
  manifest: 1.6, open: { seraph: 1.5, cherub: 2.4, ophan: 1.6 }, close: 1.0, fold: 1.4,
  unfold: 1.6, gather: 1.4, assemble: 3.0, declare: 1.0, unmake: 2.0, ignite: 0.5, impact: 0.6,
  // dw_seraph.py (DW01 lands its verdict 15 ticks after the gesture starts)
  seraph: { arrive: 1.5, unfurl: 1.3, chantLead: [18, 19, 19], depart: 1.6, verdictHitTicks: 15 },
  // dw_cherub.py
  cherub: { arrive: 1.6, human: 1.6, humanCast: 1.05, oxLock: 0.75, ox: 1.0, lion: 1.8, lionRoar: 0.95, eagle: 2.8,
    eagleThrust: [1.6, 2.5], verdictHit: 0.8, depart: 1.8, bladeForm: 0.6, bladeShatter: 0.5, roarLife: 1.0 },
  // dw_ophanim.py
  ophan: { arrive: 2.0, lock: 0.6, verdict: 1.1, verdictHit: 0.55, depart: 1.8 },
};

interface Marked { e: Entity; mark: Actor; n: number }
interface Spot { forward: number; side: number; up: number }
interface Area { at: V3; e?: Entity; sigil?: Actor; letters: number; landed: number }

/**
 * DW05 - Imperial Edict: The Threefold Heavenly Throne.
 * I   The Gates of Heaven: three gates of three architectures are written into the sky and open
 *     low to high while three giant sentences unfold around the region and pronounce its law.
 * II  The Three Witnesses: the Ophanim, the Cherubim and the Seraphim emerge through their own
 *     gates and testify in a round - the wheels scan, mark and sweep; the four faces mark, ward
 *     the allies, roar and send feather-blades; the six wings chant columns onto the marked.
 * III The Throne's Verdict: their inscriptions stream together into an enormous EMPTY throne; the
 *     throne speaks three lines of gigantic letters; the witnesses strike in unison and the letters
 *     descend on every designated hostile area.  The witnesses withdraw through their gates, the
 *     gates fold into lines of text and the throne comes apart into letters.
 */
export default defineSpell("dw05", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, C.focusSnap);
  const tow = flat(sub(center, caster.location));
  const fwd = Math.hypot(tow.x, tow.z) > 2 ? norm(tow) : aim.forward;
  const side = right(fwd);
  const at = (p: Spot): V3 => add(add(up(center, p.up), mul(fwd, p.forward)), mul(side, p.side));
  const view = sub(center, mul(fwd, 6)); // where the ceremony faces: just in front of the caster
  const yawTo = (from: V3, to: V3): number => yawOf(flat(sub(to, from)));
  const lights = blocksFor(scene);
  const marks = new Map<string, Marked>();

  // ------------------------------------------------------------------------------ shared helpers
  function region(max?: number): Entity[] { return hostiles(dim, center, C.regionRadius, caster, max); }
  function liveMarks(): Marked[] { return [...marks.values()].filter((m) => isAlive(m.e)); }
  function cluster(): V3 {
    let pts = liveMarks().map((m) => m.e.location);
    if (!pts.length) pts = region(8).map((e) => e.location);
    if (!pts.length) return center;
    const c = mul(pts.reduce((s, p) => add(s, p), v(0, 0, 0)), 1 / pts.length);
    return groundBelow(dim, v(c.x, center.y + 4, c.z), 24);
  }
  function markEnemy(e: Entity): Marked | undefined {
    if (!isAlive(e)) return undefined;
    const old = marks.get(e.id);
    if (old) return old;
    if (marks.size >= C.maxMarks) return undefined;
    const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: MARK.appear, skin: 0 });
    scene.follow(mark, e, 2.4);
    scene.after(6, () => mark.state(MARK.hold));
    const m = { e, mark, n: 0 };
    marks.set(e.id, m);
    damage(e, C.markDamage, caster);
    return m;
  }
  /** A witness has testified against this enemy: one more petal of its mark lights. */
  function testify(e: Entity): void {
    const m = marks.get(e.id);
    if (m && m.mark.valid) { m.n++; m.mark.skin(Math.min(2, m.n)); }
  }
  function boost(e: Entity, base: number, bonus: number): number { return marks.has(e.id) ? base * bonus : base; }
  function flashOut(a: Actor | undefined, after = 8): void {
    if (!a || !a.valid) return;
    a.state(3);
    scene.after(after, () => scene.despawn(a));
  }

  // ====================================================================================== PHASE I
  const circle = scene.spawn("dw_circle", center, { size: 6, state: 1 });
  scene.at(16, () => circle.state(2));
  sound(dim, "dw5_manifest", up(center, 8), 1.6);
  sound(dim, "dw_circle", center, 1.0);
  lights.place(up(center, 2), LIGHT);
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), 5, 8));

  interface Gate { a: Actor; pos: V3; mouth: V3; yaw: number; t: number; open: number; snd: string; openLen: number }
  function makeGate(id: string, spot: Spot, mouthUp: number, t: number, open: number, snd: string, openLen: number): Gate {
    const pos = at(spot);
    const yaw = yawTo(pos, view);
    return { a: scene.spawn(id, pos, { yaw, state: GATE.hidden }), pos, mouth: up(pos, mouthUp), yaw, t, open, snd, openLen };
  }
  const gO = makeGate("dw5_gate_ophan", C.ophanGate, 0, 0, 50, "dw5_gate_ophan", T.open.ophan);
  const gC = makeGate("dw5_gate_cherub", C.cherubGate, 5.5, 8, 80, "dw5_gate_cherub", T.open.cherub);
  const gS = makeGate("dw5_gate_seraph", C.seraphGate, 9.5, 16, 110, "dw5_gate_seraph", T.open.seraph);
  for (const g of [gO, gC, gS]) {
    scene.at(g.t, () => {
      g.a.state(GATE.manifest);
      line(dim, "dw5_fold", add(g.mouth, mul(right(fromYaw(g.yaw)), -5)), add(g.mouth, mul(right(fromYaw(g.yaw)), 5)), 4);
      sound(dim, "dw_circle", g.mouth, 1.2, 0.8);
    });
    scene.at(g.t + secs(T.manifest), () => g.a.state(GATE.closed));
    scene.at(g.open, () => {
      g.a.state(GATE.open);
      sound(dim, g.snd, g.mouth, 2.0);
      burst(dim, "dw5_gate_dust", g.mouth, 3, 4);
    });
    scene.at(g.open + secs(g.openLen), () => {
      g.a.state(GATE.opened);
      particle(dim, "fx_flash", g.mouth);
      particle(dim, "dw5_gate_rays", g.mouth);
    });
  }
  // the open gates keep breathing light while they stand
  scene.every(12, (el) => {
    for (const g of [gO, gC, gS]) if (scene.tick > g.open + 30 && scene.tick < 560) particle(dim, el % 24 ? "dw5_gate_rays" : "dw_mote", g.mouth);
  }, 60, 640);

  // the three sentences unfold around the region, low to high
  const sentences = C.sentences.map((b, k) =>
    scene.spawn("dw5_sentence", up(center, b.up), { kind: k, size: b.radius / 8, state: SEN.hidden, yaw: yawOf(fwd) + k * 40 }));
  sentences.forEach((s, k) => {
    const t0 = 24 + k * 16;
    scene.at(t0, () => {
      s.state(SEN.unfold);
      sound(dim, "dw5_sentence", up(center, C.sentences[k].up + 1), 1.4, 0.9 + k * 0.12);
      ring(dim, "dw_glyph_rise", up(center, C.sentences[k].up), C.sentences[k].radius, 8, k * 15);
    });
    scene.at(t0 + secs(T.unfold), () => s.state(SEN.idle));
  });
  // the closed sentence is a law: the region is judged and its enemies are weighed down
  scene.at(100, () => {
    sound(dim, "dw5_domain", up(center, 3), 1.6);
    particle(dim, "dw5_domain", up(center, 0.3));
    particle(dim, "fx_shock", up(center, 0.4));
    ring(dim, "dw_glyph_fall", up(center, 6), 7, 8);
    for (const e of region()) {
      damage(e, C.domainDamage, caster);
      effect(e, "slowness", C.domainSlowTicks, C.domainSlowAmp);
      particle(dim, "dw_halo", up(e.location, 1.2));
    }
  });
  for (const t of [120, 220, 320]) scene.at(t, () => sound(dim, "dw5_bed", up(center, 8), 1.2));

  // ====================================================================================== PHASE II
  // ---------------------------------------------------------------- the OPHANIM (low, moving)
  const tO = 130;
  const oStart = add(gO.pos, mul(fwd, 1.5));
  const oStation = at(C.ophanStation);
  let oPos = oStart;
  let oYaw = gO.yaw;
  const oph = scene.spawn("ophanim", oStart, { yaw: oYaw, state: OPH.hidden, skin: 0 });
  scene.at(tO, () => {
    oph.state(OPH.arrive);
    sound(dim, "dw_ophan_arrive", oStart, 1.5);
    particle(dim, "fx_flash", gO.mouth);
  });
  scene.span(tO, tO + secs(T.ophan.arrive), (p) => {
    oPos = bezier(oStart, up(lerp(oStart, oStation, 0.5), 2), oStation, smooth(p));
    oph.move(oPos, oYaw);
  });
  const tSurvey = tO + secs(T.ophan.arrive);
  const tScan = tSurvey + 2;
  const scan0 = yawOf(fwd) + 90;
  scene.at(tSurvey, () => { oph.state(OPH.survey); sound(dim, "dw_ophan_hum", oPos, 0.9, 0.6); particle(dim, "dw_ophan_ping", up(center, 0.2)); });
  let prevAng = scan0;
  scene.every(1, (e) => {
    const ang = scan0 + (360 * (e + 1)) / C.scanTicks;
    const dir = v(Math.cos((ang * Math.PI) / 180), 0, Math.sin((ang * Math.PI) / 180));
    const tip = add(center, mul(dir, C.regionRadius));
    line(dim, "dw_ophan_scan", up(add(center, mul(dir, 2)), 0.25), up(tip, 0.25), 6);
    if (e % 3 === 0) line(dim, "dw_ophan_scan", up(oPos, -1), up(tip, 0.4), 4);
    if (e % 6 === 0) { sound(dim, "dw_ophan_scan", center, 0.9, 0.9 + (e / C.scanTicks) * 0.3); particle(dim, "dw_ophan_ping", up(center, 0.25)); }
    for (const h of region()) {
      const a = (Math.atan2(h.location.z - center.z, h.location.x - center.x) * 180) / Math.PI;
      const d = (((a - prevAng) % 360) + 360) % 360;
      if (d <= ang - prevAng && !marks.has(h.id) && markEnemy(h)) {
        sound(dim, "dw_ophan_mark", h.location, 0.9, 1 + marks.size * 0.04);
        particle(dim, "dw_ophan_eye", up(h.location, 3.4));
        line(dim, "dw_ophan_scan", up(oPos, -1), up(h.location, 1.2), 6);
      }
    }
    prevAng = ang;
  }, tScan, tScan + C.scanTicks);
  scene.at(tScan + C.scanTicks, () => {
    for (const h of region()) if (!marks.has(h.id) && markEnemy(h)) particle(dim, "dw_ophan_eye", up(h.location, 3.4));
  });

  // straight sweeping passes through the marked, each from a new direction
  const tPass0 = tScan + C.scanTicks + 4;
  const passLen = C.lockTicks + C.passTicks;
  for (let k = 0; k < C.passes; k++) {
    const tLock = tPass0 + k * passLen;
    const tRun = tLock + C.lockTicks;
    let a = oPos, b = oPos, dir = fwd;
    let tele: Actor[] = [];
    const hit = new Set<string>();
    scene.at(tLock, () => {
      const c = cluster();
      const base = flat(sub(c, oPos));
      dir = fromYaw((Math.hypot(base.x, base.z) > 1 ? yawOf(base) : yawOf(fwd)) + k * 60);
      let spread = 0;
      for (const m of liveMarks()) spread = Math.max(spread, distXZ(m.e.location, c));
      const half = clamp(spread + 4, C.passHalfMin, C.passHalfMax);
      const ga = groundBelow(dim, up(sub(c, mul(dir, half)), 4), 24), gb = groundBelow(dim, up(add(c, mul(dir, half)), 4), 24);
      a = up(ga, C.sweepAltitude);
      b = up(gb, C.sweepAltitude);
      oph.state(OPH.lock).skin(1);
      sound(dim, "dw_ophan_lock", oPos, 1.2, 1 + k * 0.06);
      tele = [ga, lerp(ga, gb, 0.5), gb].map((p) => scene.spawn("telegraph", p, { kind: 0, size: C.rimHalfWidth + 0.6, state: 1 }));
      const from = oPos, ctrl = up(lerp(oPos, a, 0.5), 4), yawGoal = yawOf(dir);
      scene.span(tLock, tRun, (p) => {
        oPos = bezier(from, ctrl, a, p);
        oYaw += angleDelta(oYaw, yawGoal) * 0.3;
        oph.move(oPos, oYaw);
        if (Math.round(p * 12) % 2 === 0) line(dim, "dw_ophan_route", up(a, 0.3 - C.sweepAltitude), up(b, 0.3 - C.sweepAltitude), 8);
      });
    });
    scene.at(tRun, () => { oph.state(OPH.sweep); sound(dim, "dw_ophan_sweep", oPos, 1.3, 0.95 + k * 0.08); });
    scene.every(1, (e) => {
      oPos = lerp(a, b, (e + 1) / C.passTicks);
      oYaw = yawOf(dir);
      oph.move(oPos, oYaw);
      const ground = up(oPos, -C.sweepAltitude);
      const ca = add(ground, mul(dir, C.rimChord)), cb = add(ground, mul(dir, -C.rimChord));
      for (const t of tele) if (t.valid && distXZ(t.loc, oPos) < C.rimChord * 0.6) flashOut(t);
      particle(dim, "dw_ophan_rim", up(ca, 0.8));
      if (e % 2 === 0) particle(dim, "dw_ophan_sparks", up(ground, 0.3));
      if (e % 10 === 0) sound(dim, "dw_ophan_hum", oPos, 1.0, 0.85 + k * 0.15);
      for (const h of hostiles(dim, oPos, C.rimChord + C.sweepAltitude + 2, caster)) {
        if (hit.has(h.id)) continue;
        const l = h.location;
        if (l.y < ground.y - 1.5 || l.y > ground.y + C.rimHeight) continue;
        if (distToSegment(v(l.x, 0, l.z), v(ca.x, 0, ca.z), v(cb.x, 0, cb.z)) > C.rimHalfWidth) continue;
        const m = marks.get(h.id);
        if (!damage(h, m ? C.passMarkedDamage : C.passDamage, caster)) continue;
        hit.add(h.id);
        const sd = right(dir);
        const sign = (l.x - oPos.x) * sd.x + (l.z - oPos.z) * sd.z >= 0 ? 1 : -1;
        shove(h, mul(sd, sign), C.passKnock, C.passLift);
        particle(dim, "dw_ophan_impact", up(l, 1));
        sound(dim, "dw_ophan_bell", l, 1.0, m ? 1.0 + k * 0.08 : 0.85);
        if (m) testify(h);
      }
    }, tRun, tRun + C.passTicks);
    scene.at(tRun + C.passTicks, () => { for (const t of tele) flashOut(t); });
  }
  const tOphDone = tPass0 + C.passes * passLen;
  scene.at(tOphDone, () => { oph.state(OPH.survey); });

  // ---------------------------------------------------------------- the CHERUBIM (middle level)
  const tC = 160;
  const cStart = up(add(gC.pos, mul(fwd, 1.5)), 1);
  const cStation = at(C.cherubStation);
  let cPos = cStart;
  let cYaw = gC.yaw;
  const cherub = scene.spawn("cherub", cStart, { yaw: cYaw, state: CHE.hidden });
  scene.at(tC, () => { cherub.state(CHE.arrive); sound(dim, "dw_cherub_arrive", gC.mouth, 1.5); particle(dim, "fx_flash", gC.mouth); });
  scene.span(tC, tC + 36, (p) => {
    cPos = bezier(cStart, up(lerp(cStart, cStation, 0.5), 2), cStation, smooth(p));
    cherub.move(cPos, cYaw);
  });
  function cherubFace(goal: number, from: number, ticks = 10): void {
    scene.span(from, from + ticks, () => { cYaw += angleDelta(cYaw, goal) * 0.35; cherub.move(cPos, cYaw); });
  }
  const turn = (): void => sound(dim, "dw_cherub_turn", up(cPos, 10), 1.1);
  // HUMAN: the testament is written on every enemy of the region
  const tHuman = tC + secs(T.cherub.arrive) - 2;
  let testimony: Entity[] = [];
  scene.at(tHuman, () => {
    cherub.state(CHE.human);
    cherubFace(yawTo(cPos, cluster()), scene.tick);
    sound(dim, "dw_cherub_human", up(cPos, 10), 1.4);
    testimony = region(C.maxMarks);
  });
  scene.every(3, (el) => {
    const hand = up(cPos, 12.5);
    particle(dim, "dw_cherub_glyph", hand);
    const p = Math.min(1, el / 14);
    for (const e of testimony) if (isAlive(e)) particle(dim, "dw_cherub_glyph", lerp(hand, up(e.location, 1.6), p));
  }, tHuman + 7, tHuman + secs(T.cherub.humanCast));
  scene.at(tHuman + secs(T.cherub.humanCast), () => {
    testimony.forEach((e, i) => {
      if (!isAlive(e)) return;
      const fresh = !marks.has(e.id);
      if (fresh) markEnemy(e); else testify(e);
      damage(e, C.testamentDamage, caster);
      particle(dim, "dw_halo", up(e.location, 1.2));
      sound(dim, "dw_cherub_glyph", e.location, 0.8, 1 + i * 0.05);
    });
    if (!testimony.length) for (let k = 0; k < 3; k++) particle(dim, "dw_halo", up(polar(center, 3.5, k * 120), 1));
    line(dim, "dw_cherub_glyph", up(cPos, 12.5), up(center, 2), 6);
  });
  // OX: the wing-wall becomes a ward over the caster and the allies, held until the verdict ends
  const tOx = tHuman + secs(T.cherub.human) - 2;
  const tWard = tOx + secs(T.cherub.oxLock);
  const tVerdict = 500;
  scene.at(tOx, () => {
    cherub.state(CHE.ox);
    turn();
    cherubFace(yawTo(cPos, caster.location), scene.tick);
    sound(dim, "dw_cherub_ox", up(cPos, 9), 1.4);
  });
  scene.at(tWard, () => {
    sound(dim, "dw_cherub_shield", caster.location, 1.2);
    burst(dim, "dw_cherub_feather", up(cPos, 6), 3, 6);
    line(dim, "dw_cherub_shield", up(cPos, 6), up(caster.location, 1), 6);
    const ward = addWard({
      scene,
      factor: 1 - C.wardStrength,
      pool: C.wardPool,
      protects: (e) => e.id === caster.id ||
        (e.typeId === "minecraft:player" && !CONFIG.targeting.pvp && distXZ(e.location, caster.location) <= C.wardRadius),
      onAbsorb: (_amount, _attacker, victim) => {
        if (victim.isValid) particle(dim, "dw_cherub_absorb", up(victim.location, 1));
        sound(dim, "dw_cherub_absorb", victim.isValid ? victim.location : caster.location, 0.9);
      },
      onBreak: () => { sound(dim, "dw_cherub_retaliate", caster.location, 0.6, 1.3); particle(dim, "dw_cherub_shatter", up(caster.location, 1)); },
    });
    scene.at(tVerdict + 40, () => removeWard(ward));
  });
  scene.every(10, () => {
    if (!caster.isValid) return;
    particle(dim, "dw_cherub_shield", up(caster.location, 1));
    for (const p of dissolveProjectiles(scene, caster.location, 5)) particle(dim, "dw_cherub_absorb", p);
  }, tWard, tVerdict + 40);
  // LION: a roar of letter-rings driven down at the marked cluster
  const tLion = tOx + secs(T.cherub.ox) + 22;
  const tRoar = tLion + secs(T.cherub.lionRoar);
  let roarFrom = cPos, roarTo = center;
  const cone: Actor[] = [];
  scene.at(tLion, () => {
    cherub.state(CHE.lion);
    turn();
    roarTo = cluster();
    cherubFace(yawTo(cPos, roarTo), scene.tick);
    const g0 = groundBelow(dim, up(cPos, -4), 24);
    for (const f of [0.45, 0.85]) cone.push(scene.spawn("telegraph", lerp(g0, roarTo, f), { kind: 0, size: 2.5 + f * 3, state: 1 }));
  });
  scene.at(tRoar - 4, () => sound(dim, "dw_cherub_lion", up(cPos, 9.5), 1.8));
  const roared = new Set<string>();
  scene.at(tRoar, () => {
    roarFrom = add(up(cPos, 9.5), mul(fromYaw(cYaw), 1.8));
    particle(dim, "dw_cherub_breath", roarFrom);
    particle(dim, "dw_cherub_roar", roarFrom);
    cone.forEach((t) => flashOut(t));
  });
  for (let k = 0; k < 3; k++) {
    const t0 = tRoar + k * 4;
    let ringA: Actor | undefined;
    let travel = 20;
    scene.at(t0, () => {
      const end = up(add(roarTo, mul(norm(flat(sub(roarTo, roarFrom))), 4)), 1.5);
      travel = Math.max(8, Math.round(dist(roarFrom, end) / C.roarSpeed));
      const yaw = yawTo(roarFrom, end);
      ringA = scene.spawn("dw_cherub_roar", roarFrom, { yaw, state: 1 });
      sound(dim, "dw_cherub_ring", roarFrom, 1.0, 0.9 + k * 0.1);
      const from = roarFrom;
      const ground0 = flat(from);
      const dirXZ = norm(flat(sub(end, from)));
      const reach = distXZ(from, end);
      scene.span(t0, t0 + travel, (p, el) => {
        const pos = lerp(from, end, p);
        ringA?.move(pos, yaw);
        if (el % 3 === 0) particle(dim, "dw_cherub_roar", pos);
        if (k > 0) return;
        const front = reach * p;
        for (const e of region()) {
          if (roared.has(e.id)) continue;
          const rel = sub(flat(e.location), ground0);
          const along = dot(rel, dirXZ);
          if (along > front + 0.5 || along < front - 3) continue;
          const lat = Math.hypot(rel.x - dirXZ.x * along, rel.z - dirXZ.z * along);
          if (lat > C.roarHalfWidthNear + (C.roarHalfWidthFar - C.roarHalfWidthNear) * clamp(along / Math.max(reach, 1), 0, 1)) continue;
          roared.add(e.id);
          damage(e, boost(e, C.roarDamage, C.markBonus), caster);
          shove(e, dirXZ, C.roarKnock, C.roarLift);
          particle(dim, "dw_spark", up(e.location, 1));
          testify(e);
        }
      });
      scene.at(t0 + travel, () => { if (ringA) { ring(dim, "dw_glyph_rise", ringA.loc, 2.5, 6); scene.despawn(ringA); } });
    });
  }
  // EAGLE: feather-blades dive onto the marked
  const tEagle = tRoar + 15;
  const dives = T.cherub.eagleThrust.map((s) => tEagle + secs(s));
  scene.at(tEagle, () => {
    cherub.state(CHE.eagle).skin(1);
    turn();
    cherubFace(yawTo(cPos, cluster()), scene.tick);
    burst(dim, "dw_cherub_feather", up(cPos, 9), 4, 6);
  });
  scene.at(tEagle + 10, () => sound(dim, "dw_cherub_eagle", up(cPos, 11), 1.6));
  function bladeTargets(wave: number): { e?: Entity; at: V3 }[] {
    const out: { e?: Entity; at: V3 }[] = [];
    const used = new Set<string>();
    for (const m of liveMarks()) {
      if (out.length >= C.bladesPerWave) break;
      out.push({ e: m.e, at: groundBelow(dim, m.e.location) });
      used.add(m.e.id);
    }
    for (const e of region()) {
      if (out.length >= C.bladesPerWave) break;
      if (!used.has(e.id)) out.push({ e, at: groundBelow(dim, e.location) });
    }
    if (!out.length) { const c = cluster(); [0, 1, 2].forEach((k) => out.push({ at: polar(c, 3 + wave * 2, k * 120 + wave * 60) })); }
    return out;
  }
  function blade(target: { e?: Entity; at: V3 }, diveAt: number, idx: number): void {
    let p0 = target.at;
    const bYaw = cYaw + idx * 47;
    const b = scene.spawn("dw_cherub_blade", up(p0, C.bladeHeight), { yaw: bYaw, state: BLADE.form });
    const sigil = scene.spawn("telegraph", p0, { kind: 0, size: C.bladeRadius, state: 1 });
    sound(dim, "dw_cherub_blade", up(p0, C.bladeHeight), 0.9, 0.95 + idx * 0.04);
    line(dim, "dw_cherub_glyph", up(cPos, 11), up(p0, C.bladeHeight), 5);
    scene.after(secs(T.cherub.bladeForm), () => b.state(BLADE.aim));
    scene.every(1, () => {
      if (target.e && isAlive(target.e)) { p0 = groundBelow(dim, target.e.location); sigil.move(p0); }
      b.move(up(p0, C.bladeHeight), bYaw);
    }, scene.tick + 1, diveAt);
    scene.at(diveAt, () => { b.state(BLADE.dive); sound(dim, "dw_cherub_dive", up(p0, C.bladeHeight * 0.5), 1.0); });
    scene.span(diveAt, diveAt + C.diveTicks, (p) => {
      const pos = up(p0, C.bladeHeight * (1 - easeIn(p)));
      b.move(pos, bYaw);
      particle(dim, "dw_cherub_trail", up(pos, 1.5));
    });
    scene.at(diveAt + C.diveTicks, () => {
      b.move(p0, bYaw).state(BLADE.shatter);
      sigil.state(3);
      sound(dim, "dw_cherub_impact", p0, 1.1);
      particle(dim, "dw_cherub_shatter", up(p0, 0.6));
      particle(dim, "dw_ring", up(p0, 0.2));
      for (const e of hostiles(dim, p0, C.bladeRadius, caster)) {
        if (!damage(e, boost(e, C.bladeDamage, C.bladeMarkBonus), caster)) continue;
        knockback(e, p0, 0.6, 0.3);
        testify(e);
      }
      scene.after(secs(T.cherub.bladeShatter) + 2, () => { scene.despawn(b); scene.despawn(sigil); });
    });
  }
  dives.forEach((diveAt, wave) => {
    scene.at(diveAt - C.bladeWarn, () => bladeTargets(wave).forEach((t, i) => blade(t, diveAt, i + wave * 3)));
  });
  scene.at(tEagle + secs(T.cherub.eagle), () => cherub.state(CHE.idle));

  // ---------------------------------------------------------------- the SERAPHIM (highest)
  const tS = 190;
  const sStart = up(add(gS.pos, mul(fwd, 1.5)), 1.5);
  const sStation = at(C.seraphStation);
  let sPos = sStart;
  const sYaw = yawTo(sStation, view);
  const seraph = scene.spawn("seraph", sStart, { yaw: sYaw, state: SER.hidden });
  scene.at(tS, () => { seraph.state(SER.arrive); sound(dim, "dw_seraph_arrive", gS.mouth, 1.5); particle(dim, "fx_flash", gS.mouth); });
  scene.span(tS, tS + secs(T.seraph.arrive), (p) => {
    sPos = bezier(sStart, up(lerp(sStart, sStation, 0.5), 3), sStation, smooth(p));
    seraph.move(sPos, sYaw);
  });
  scene.at(tS + secs(T.seraph.arrive), () => seraph.state(SER.veiled));
  const tUnfurl = tS + secs(T.seraph.arrive) + 6;
  scene.at(tUnfurl, () => {
    seraph.state(SER.unfurl);
    sound(dim, "dw_unfurl", sPos, 1.2);
    burst(dim, "dw_feather", up(sPos, 7), 6, 8);
  });
  scene.at(tUnfurl + secs(T.seraph.unfurl), () => seraph.state(SER.open));
  const chantAt = [262, 296, 330];
  const chanted = [new Set<string>(), new Set<string>(), new Set<string>()];
  chantAt.forEach((t0, i) => {
    scene.at(t0, () => {
      seraph.state(SER.chant1 + i).skin(1);
      sound(dim, `dw_chant${i + 1}`, sPos, 1.5);
      ring(dim, "dw_glyph_rise", up(sPos, 7), 5, 8, i * 20);
    });
    scene.at(t0 + T.seraph.chantLead[i] - C.columnWarn + 8, () => judge(i));
  });
  function judge(i: number): void {
    const spots: { e?: Entity; loc: V3 }[] = [];
    for (const m of liveMarks()) if (spots.length < C.maxColumns) spots.push({ e: m.e, loc: groundBelow(dim, m.e.location) });
    for (const e of region()) {
      if (spots.length >= C.maxColumns) break;
      if (!marks.has(e.id)) spots.push({ e, loc: groundBelow(dim, e.location) });
    }
    if (!spots.length) { const c = cluster(); [0, 1, 2].forEach((k) => spots.push({ loc: polar(c, 4, k * 120 + 30 + i * 40) })); }
    for (const s of spots) {
      const r = C.columnRadius * (1 + i * 0.1);
      const warn = scene.spawn("telegraph", s.loc, { kind: 0, size: r, state: 1 });
      let p0 = s.loc;
      line(dim, "dw_glyph_fall", up(sPos, 6), up(p0, 8), 4);
      scene.every(1, () => { if (s.e && isAlive(s.e)) { p0 = groundBelow(dim, s.e.location); warn.move(p0); } }, scene.tick, scene.tick + C.columnWarn - 4);
      scene.after(C.columnWarn - 6, () => {
        const col = scene.spawn("dw_column", p0, { kind: i === 1 ? 1 : 0, size: (r / 1.3) * 1.15, state: 1 });
        sound(dim, "dw_column", p0, 1.1, 0.95 + i * 0.08);
        scene.after(10, () => col.state(2));
        scene.after(22, () => col.state(3));
        scene.after(36, () => scene.despawn(col));
      });
      scene.after(C.columnWarn, () => {
        flashOut(warn);
        particle(dim, "dw_ring", up(p0, 0.2));
        particle(dim, "dw_pillar_burst", up(p0, 0.3));
        particle(dim, "dw_spark", up(p0, 1));
        for (const e of hostiles(dim, p0, r, caster)) {
          if (chanted[i].has(e.id)) continue;
          if (!damage(e, C.chantDamage[i], caster)) continue;
          chanted[i].add(e.id);
          if (!marks.has(e.id)) markEnemy(e); else testify(e);
        }
      });
    }
  }
  scene.at(chantAt[2] + 32, () => seraph.state(SER.open));

  // ====================================================================================== PHASE III
  const tIII = 370;
  const thP = at(C.throne);
  const seat = up(thP, 5.6);
  const throne = scene.spawn("dw5_throne", thP, { yaw: yawTo(thP, view), state: THR.hidden });
  const sPost = at(C.seraphPost), cPost = at(C.cherubPost), oPost = at(C.ophanPost);
  scene.at(tIII, () => {
    oph.state(OPH.survey);
    cherub.state(CHE.idle);
    const s0 = sPos, c0 = cPos, o0 = oPos;
    scene.span(tIII, tIII + 30, (p) => {
      const q = smooth(p);
      sPos = bezier(s0, up(lerp(s0, sPost, 0.5), 3), sPost, q); seraph.move(sPos, yawTo(sPost, view));
      cPos = lerp(c0, cPost, q); cYaw += angleDelta(cYaw, yawTo(cPost, view)) * 0.2; cherub.move(cPos, cYaw);
      oPos = bezier(o0, up(lerp(o0, oPost, 0.5), 3), oPost, q); oYaw += angleDelta(oYaw, yawTo(oPost, view)) * 0.2; oph.move(oPos, oYaw);
    });
  });
  // the sentences lift away into the forming throne
  sentences.forEach((s, k) => {
    scene.at(tIII + k * 6, () => { s.state(SEN.gather); sound(dim, "dw5_fold", up(center, C.sentences[k].up), 1.0, 0.9 + k * 0.1); });
    scene.at(tIII + k * 6 + secs(T.gather) + 2, () => scene.despawn(s));
  });
  const tThrone = tIII + 10;
  scene.at(tThrone, () => {
    throne.state(THR.assemble);
    sound(dim, "dw5_throne_form", seat, 2.0);
    seraph.skin(1); cherub.skin(1); oph.skin(1);
    lights.place(up(thP, 7), LIGHT);
  });
  // streams of letters pour from the three witnesses into the throne
  scene.every(2, (el) => {
    const src = [up(sPos, 7), up(cPos, 10), oPos];
    const ph = ((el / 2) % 8) / 8;
    for (const s of src) {
      particle(dim, "dw5_stream", lerp(s, seat, ph));
      particle(dim, "dw5_stream", lerp(s, seat, (ph + 0.5) % 1));
    }
  }, tThrone, tThrone + 50);
  scene.at(tThrone + secs(T.assemble), () => {
    throne.state(THR.idle);
    particle(dim, "dw5_seat_glow", seat);
    burst(dim, "dw_glyph_rise", up(thP, 8), 5, 8);
  });

  // the throne speaks: three lines of gigantic letters light one by one
  const tSpeak = tThrone + secs(T.assemble) + 4;
  scene.at(tSpeak, () => { throne.state(THR.declare); particle(dim, "dw5_seat_glow", seat); });
  const letters: Actor[][] = [];
  const lineBase = add(center, mul(fwd, C.throne.forward - C.lineForward));
  const lYaw = yawTo(lineBase, view);
  C.lineHeights.forEach((h, l) => {
    letters.push([]);
    const t0 = tSpeak + 4 + l * 12;
    scene.at(t0, () => sound(dim, "dw5_speak", up(lineBase, h), 1.8, 1 + l * 0.12));
    for (let j = 0; j < C.lettersPerLine; j++) {
      const off = (j - (C.lettersPerLine - 1) / 2) * C.letterSpacing;
      const p = up(add(lineBase, mul(side, off)), h);
      scene.at(t0 + j * 2, () => {
        const a = scene.spawn("dw5_letter", p, { yaw: lYaw, kind: (l * 5 + j * 2) % LETTER_KINDS, state: LET.ignite });
        letters[l][j] = a;
        particle(dim, "fx_flash", up(p, 2));
        if (j % 2 === 0) sound(dim, "dw5_ignite", p, 1.0, 0.9 + j * 0.06);
        scene.after(secs(T.ignite), () => a.state(LET.hold));
      });
    }
  });

  // the designated hostile areas are sealed while the throne speaks
  const areas: Area[] = [];
  scene.at(tSpeak + 8, () => {
    const pick: Entity[] = [...liveMarks().map((m) => m.e), ...region().filter((e) => !marks.has(e.id))];
    for (const e of pick) {
      if (areas.length >= C.lineHeights.length * C.lettersPerLine) break;
      const g = groundBelow(dim, e.location);
      if (areas.some((a) => distXZ(a.at, g) < C.areaRadius)) continue;
      areas.push({ at: g, e, letters: 0, landed: 0 });
    }
    if (!areas.length) {
      const c = cluster();
      areas.push({ at: c, letters: 0, landed: 0 });
      for (let k = 0; k < 4; k++) areas.push({ at: groundBelow(dim, up(polar(c, 6, k * 90 + 45), 3), 12), letters: 0, landed: 0 });
    }
    for (const a of areas) a.sigil = scene.spawn("telegraph", a.at, { kind: 0, size: C.areaRadius, state: 4 });
    scene.after(40, () => areas.forEach((a) => a.sigil?.state(2)));
  });
  // seals follow their enemy until the verdict is committed
  scene.every(1, () => {
    for (const a of areas) if (a.e && isAlive(a.e)) { a.at = groundBelow(dim, a.e.location); a.sigil?.move(a.at); }
  }, tSpeak + 9, tVerdict - C.plungeTicks);

  // ---- the synchronized verdict: every witness strikes on the same beat
  scene.at(tVerdict - secs(T.cherub.verdictHit), () => { cherub.state(CHE.verdict); sound(dim, "dw_cherub_turn", up(cPos, 10), 1.2); });
  scene.at(tVerdict - T.seraph.verdictHitTicks, () => seraph.state(SER.verdict));
  scene.at(tVerdict - secs(T.ophan.verdictHit), () => { oph.state(OPH.verdict); sound(dim, "dw_ophan_verdict", oPos, 1.4); });
  scene.at(tVerdict - 3, () => sound(dim, "dw5_verdict", up(center, 6), 2.2));
  const struck = new Map<string, number>();
  const bonused = new Set<string>();
  let q = 0;
  for (let l = 0; l < C.lineHeights.length; l++) {
    for (let j = 0; j < C.lettersPerLine; j++, q++) {
      const idx = q;
      const tPl = tVerdict - C.plungeTicks + idx * C.plungeStagger;
      let from = center, target: Area | undefined, a: Actor | undefined;
      scene.at(tPl, () => {
        a = letters[l]?.[j];
        if (!a || !a.valid || !areas.length) return;
        target = areas[idx % areas.length];
        target.letters++;
        from = a.loc;
        a.state(LET.plunge);
        sound(dim, "dw5_letter_fall", from, 1.3, 0.92 + (idx % 5) * 0.05);
      });
      scene.span(tPl, tPl + C.plungeTicks, (p) => {
        if (!a || !target) return;
        const pos = lerp(from, target.at, easeIn(p));
        a.move(pos);
        particle(dim, "dw5_edict_trail", up(pos, 3));
      });
      scene.at(tPl + C.plungeTicks, () => {
        if (!a || !target) return;
        const ar = target, letter = a;
        letter.move(ar.at).state(LET.impact);
        scene.after(secs(T.impact) + 2, () => scene.despawn(letter));
        particle(dim, "dw5_edict_impact", up(ar.at, 0.2));
        particle(dim, "dw5_edict_letters", up(ar.at, 1));
        particle(dim, "dw_pillar_burst", up(ar.at, 0.3));
        particle(dim, "fx_flash", up(ar.at, 1.5));
        for (const e of hostiles(dim, ar.at, C.verdictRadius, caster)) {
          const n = struck.get(e.id) ?? 0;
          if (n >= C.maxLetterHits) continue;
          let dmg = C.verdictDamage;
          if (marks.has(e.id) && !bonused.has(e.id)) { dmg += C.verdictMarkBonus; bonused.add(e.id); }
          if (!damage(e, dmg, caster)) continue;
          struck.set(e.id, n + 1);
          knockback(e, ar.at, C.verdictKnock, C.verdictLift);
        }
        ar.landed++;
        if (ar.landed >= ar.letters) flashOut(ar.sigil);
      });
    }
  }
  // finishing motions of the witnesses land with the first letter
  scene.at(tVerdict, () => {
    // Seraphim: one great verdict column on the first designated area
    const fc = areas.length ? areas[0].at : center;
    const col = scene.spawn("dw_column", fc, { kind: 2, size: 2.6, state: 1 });
    scene.after(10, () => col.state(2));
    scene.after(26, () => col.state(3));
    scene.after(40, () => scene.despawn(col));
    ring(dim, "dw_glyph_fall", up(fc, 7), 3, 8);
    for (const e of hostiles(dim, fc, C.finalColumnRadius, caster)) damage(e, C.finalColumnDamage, caster);
    // Ophanim: every eye judges the marked
    particle(dim, "fx_flash", oPos);
    burst(dim, "dw_ophan_impact", oPos, 3, 4);
    for (const m of liveMarks()) {
      line(dim, "dw_ophan_scan", oPos, up(m.e.location, 1.2), 8);
      damage(m.e, C.gazeDamage, caster);
      particle(dim, "dw_ophan_eye", up(m.e.location, 3.4));
    }
    // Cherubim: the four faces cry out together
    const cg = groundBelow(dim, cPos, 24);
    particle(dim, "dw_cherub_quake", up(cg, 0.2));
    particle(dim, "dw_cherub_roar", up(cPos, 9.5));
    ring(dim, "dw_cherub_feather", up(cPos, 6), 4, 6);
    particle(dim, "fx_shock", up(center, 0.4));
  });
  const tAfter = tVerdict + q * C.plungeStagger + 4;
  scene.at(tAfter, () => {
    for (const m of marks.values()) if (m.mark.valid) { const mk = m.mark; mk.state(MARK.burst); scene.after(8, () => scene.despawn(mk)); }
    for (const a of areas) flashOut(a.sigil);
  });
  scene.at(tVerdict + secs(T.ophan.verdict), () => oph.state(OPH.survey));

  // ---- withdrawal through the gates in reverse order: Seraphim, Cherubim, Ophanim
  const tW = Math.max(540, tAfter + 4);
  scene.at(tW, () => sound(dim, "dw5_withdraw", up(center, 12), 1.8));
  function withdraw(actor: Actor, getPos: () => V3, setPos: (p: V3) => void, g: Gate, start: number, departState: number,
    departLen: number, yawOfMove: () => number): number {
    const into = up(add(g.pos, mul(fwd, 1.5)), g === gO ? 0 : 1.5);
    scene.at(start, () => {
      actor.skin(0);
      const p0 = getPos();
      scene.span(start, start + 20, (p) => { const pos = bezier(p0, up(lerp(p0, into, 0.5), 2), into, smooth(p)); setPos(pos); actor.move(pos, yawOfMove()); });
    });
    const tDep = start + 16;
    scene.at(tDep, () => { actor.state(departState); particle(dim, "fx_flash", g.mouth); burst(dim, "dw_glyph_rise", g.mouth, 2.5, 6); });
    scene.at(tDep + secs(departLen) + 2, () => scene.despawn(actor));
    const tClose = tDep + secs(departLen) - 4;
    scene.at(tClose, () => { g.a.state(GATE.close); sound(dim, "dw5_gate_close", g.mouth, 1.6); });
    scene.at(tClose + secs(T.close), () => {
      g.a.state(GATE.fold);
      sound(dim, "dw5_fold", g.mouth, 1.4);
      particle(dim, "dw5_fold", g.mouth);
    });
    scene.at(tClose + secs(T.close) + secs(T.fold) + 2, () => { burst(dim, "dw_glyph_rise", up(g.mouth, 3), 3, 6); scene.despawn(g.a); });
    return tClose + secs(T.close) + secs(T.fold) + 2;
  }
  withdraw(seraph, () => sPos, (p) => { sPos = p; }, gS, tW, SER.depart, T.seraph.depart, () => yawTo(sPos, view));
  withdraw(cherub, () => cPos, (p) => { cPos = p; }, gC, tW + 16, CHE.depart, T.cherub.depart, () => cYaw);
  const tLastGate = withdraw(oph, () => oPos, (p) => { oPos = p; }, gO, tW + 32, OPH.depart, T.ophan.depart, () => oYaw);

  // ---- the throne comes apart into sacred letters
  const tUnmake = tLastGate - 20;
  scene.at(tUnmake, () => {
    throne.state(THR.unmake);
    sound(dim, "dw5_unmake", seat, 1.8);
    burst(dim, "dw_glyph_rise", up(thP, 6), 6, 10);
  });
  scene.at(tUnmake + 20, () => ring(dim, "dw5_stream", up(thP, 12), 5, 10));
  scene.at(tUnmake + secs(T.unmake) + 2, () => { scene.despawn(throne); circle.state(3); });
  scene.at(tUnmake + secs(T.unmake) + 16, () => scene.despawn(circle));
  scene.endAt(tUnmake + secs(T.unmake) + 22);
});
