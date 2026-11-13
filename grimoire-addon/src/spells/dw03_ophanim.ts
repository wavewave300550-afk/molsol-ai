import { Entity } from "@minecraft/server";
import { DW03 as C } from "../config/dw03";
import { defineSpell } from "../core/registry";
import { damage, knockback, shove } from "../lib/combat";
import { burst, line, particle, ring, sound } from "../lib/fx";
import { Actor, secs } from "../lib/scene";
import { focus, groundBelow, hostiles, isAlive } from "../lib/targeting";
import {
  V3, add, angleDelta, bezier, clamp, dist, distToSegment, distXZ, flat, fromYaw, lerp, mul, norm, polar, right, sub, up, v,
  yawOf,
} from "../lib/vec";

// Ophanim animation states (tools/assets/dw_ophanim.py STATES)
const S = { hidden: 0, arrive: 1, survey: 2, lock: 3, sweep: 4, verdict: 5, depart: 6 };
// animation lengths (seconds) -- must match T_ARRIVE / T_LOCK / T_VERDICT / T_DEPART in dw_ophanim.py
const A = { arrive: 2.0, lock: 0.6, verdict: 1.1, depart: 1.8 };
/** Verdict animation: the armillary bursts open 0.55 s in. */
const VERDICT_HIT = secs(0.55);
const SKIN_JUDGING = 1;

interface Mark { e: Entity; mark: Actor; hits: number }
interface Route { pts: V3[]; corners: V3[]; cum: number[]; total: number; name: string }

/**
 * DW03 - Ophanim: The Unblinking Judgment.
 * A wheel-within-wheels engine is assembled above the battlefield.  Its eyes open and a rotating
 * sector scan marks every enemy it sees.  The gimbals then whirl into one plane and the wheel runs
 * geometric routes (polygon, star, figure-eight) through the marked enemies at ground level; its
 * rim is a moving blade that strikes whatever it actually passes, each tick.  A last armillary
 * verdict judges the marked, then the wheels fold into a ring of letters and rise away.
 */
export default defineSpell("dw03", ({ caster, scene, aim }) => {
  const dim = scene.dim;
  const { center } = focus(caster, aim, 12);
  const hover = up(center, C.hoverHeight);
  const faceCaster = yawOf(sub(caster.location, hover));
  const marks = new Map<string, Mark>();

  // ---- arrival: inscription circle below, the wheels assemble one by one above it
  const circle = scene.spawn("dw_circle", center, { size: 4.5, state: 1 });
  scene.at(16, () => circle.state(2));
  const oph = scene.spawn("ophanim", hover, { yaw: faceCaster, state: S.arrive, skin: 0 });
  let pos = hover;
  let yaw = faceCaster;
  sound(dim, "dw_ophan_arrive", hover, 1.3);
  sound(dim, "dw_circle", center, 0.9);
  scene.at(8, () => burst(dim, "dw_glyph_rise", up(center, 0.5), 4, 6));
  scene.at(secs(1.62), () => burst(dim, "dw_ophan_impact", hover, 3, 4));

  // ---- survey: eyes open, a beam of sight turns sector by sector and every enemy it touches is marked
  const tSurvey = secs(A.arrive);
  const tScan = tSurvey + 4;
  const tScanEnd = tScan + C.scanTicks;
  const scan0 = (aim.yaw + 90) % 360; // the beam starts where the caster looks
  scene.at(tSurvey, () => {
    oph.state(S.survey);
    sound(dim, "dw_ophan_hum", hover, 0.8, 0.6);
    particle(dim, "dw_ophan_ping", up(center, 0.2));
  });
  scene.every(30, () => sound(dim, "dw_ophan_hum", hover, 0.7, 0.62), tSurvey + 30, tScanEnd + 4);
  let prevAngle = scan0;
  scene.every(1, (e) => {
    const ang = scan0 + (360 * (e + 1)) / C.scanTicks;
    const dir = v(Math.cos((ang * Math.PI) / 180), 0, Math.sin((ang * Math.PI) / 180));
    const tip = add(center, mul(dir, C.surveyRadius));
    line(dim, "dw_ophan_scan", up(add(center, mul(dir, 2)), 0.25), up(tip, 0.25), 7);
    if (e % 3 === 0) line(dim, "dw_ophan_scan", up(hover, -1), up(tip, 0.4), 4); // the gaze itself
    const per = Math.max(1, Math.round(C.scanTicks / C.scanSectors));
    if (e % per === 0) {
      sound(dim, "dw_ophan_scan", center, 0.9, 0.9 + (e / C.scanTicks) * 0.3);
      particle(dim, "dw_ophan_ping", up(center, 0.25));
    }
    for (const h of hostiles(dim, center, C.surveyRadius, caster)) {
      const a = (Math.atan2(h.location.z - center.z, h.location.x - center.x) * 180) / Math.PI;
      if (swept(a, prevAngle, ang)) markEnemy(h);
    }
    prevAngle = ang;
  }, tScan, tScanEnd);
  // anything that walked in behind the beam is still seen at the end of the revolution
  scene.at(tScanEnd, () => { for (const h of hostiles(dim, center, C.surveyRadius, caster)) markEnemy(h); });

  function swept(a: number, from: number, to: number): boolean {
    const d = ((a - from) % 360 + 360) % 360;
    return d <= to - from;
  }

  function markEnemy(e: Entity): void {
    if (marks.has(e.id) || marks.size >= C.maxMarks || !isAlive(e)) return;
    const mark = scene.spawn("dw_mark", up(e.location, 2.4), { state: 1, skin: 0 });
    scene.follow(mark, e, 2.4);
    scene.after(6, () => mark.state(2));
    marks.set(e.id, { e, mark, hits: 0 });
    sound(dim, "dw_ophan_mark", e.location, 0.8, 1 + marks.size * 0.04);
    particle(dim, "dw_ophan_eye", up(e.location, 3.4));
    particle(dim, "dw_ophan_ping", up(e.location, 0.2));
    line(dim, "dw_ophan_scan", up(hover, -1), up(e.location, 1.2), 6);
  }

  function liveMarks(): Mark[] {
    return [...marks.values()].filter((m) => isAlive(m.e));
  }

  // ---- routes, recomputed before every pass from the live positions of the marked
  let lastCentre = center;
  function routeFor(k: number): Route {
    const live = liveMarks();
    let P = live.map((m) => flat(m.e.location));
    const c0 = P.length ? mul(P.reduce((s, p) => add(s, p), v(0, 0, 0)), 1 / P.length) : flat(lastCentre);
    const c = v(c0.x, 0, c0.z);
    lastCentre = v(c.x, center.y, c.z);
    if (!P.length) P = [0, 1, 2, 3, 4].map((i) => polar(c, C.noTargetRadius, aim.yaw + 90 + i * 72));
    let far = P[0];
    for (const p of P) if (distXZ(p, c) > distXZ(far, c)) far = p;
    const R = clamp(distXZ(far, c) + 1.5, C.routeMinRadius, C.routeMaxRadius);
    const u = distXZ(far, c) > 0.5 ? norm(flat(sub(far, c))) : fromYaw(aim.yaw);
    const a0 = (Math.atan2(u.z, u.x) * 180) / Math.PI;
    let corners: V3[];
    let name: string;
    const kind = k % 3;
    if (kind === 0) {
      // polygon through the marked themselves (sorted around their centre)
      name = "polygon";
      if (P.length >= 3) {
        corners = [...P].sort((p, q) => Math.atan2(p.z - c.z, p.x - c.x) - Math.atan2(q.z - c.z, q.x - c.x));
      } else if (P.length === 2) {
        const mid = lerp(P[0], P[1], 0.5);
        const side = right(sub(P[1], P[0]));
        corners = [P[0], add(mid, mul(side, R * 0.9)), P[1], add(mid, mul(side, -R * 0.9))];
      } else {
        const q = sub(P[0], mul(u, R));
        corners = [0, 1, 2].map((i) => polar(q, R, a0 + i * 120));
      }
      corners.push(corners[0]);
    } else if (kind === 1) {
      // pentagram around the marked, one point aimed at the farthest of them
      name = "star";
      corners = [0, 2, 4, 1, 3, 0].map((i) => polar(c, R, a0 + i * 72));
    } else {
      // figure-eight along the axis of the marked
      name = "figure-eight";
      const w = right(u);
      corners = [];
      for (let i = 0; i <= 20; i++) {
        const t = (i / 20) * Math.PI * 2;
        corners.push(add(c, add(mul(u, R * Math.sin(t)), mul(w, R * 0.8 * Math.sin(t) * Math.cos(t)))));
      }
    }
    const pts = corners.map((p) => up(groundBelow(dim, v(p.x, center.y + 4, p.z), 24), C.sweepAltitude));
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1], pts[i]));
    const keys = kind === 2 ? [0, 5, 10, 15].map((i) => pts[i]) : pts.slice(0, -1);
    return { pts, corners: keys.map((p) => up(p, -C.sweepAltitude)), cum, total: Math.max(cum[cum.length - 1], 1), name };
  }

  function pointAt(r: Route, s: number): { p: V3; dir: V3 } {
    const d = clamp(s, 0, r.total);
    let i = 1;
    while (i < r.pts.length - 1 && r.cum[i] < d) i++;
    const seg = r.cum[i] - r.cum[i - 1];
    const f = seg > 1e-6 ? (d - r.cum[i - 1]) / seg : 0;
    return { p: lerp(r.pts[i - 1], r.pts[i], f), dir: sub(r.pts[i], r.pts[i - 1]) };
  }

  // ---- passes
  const tPass0 = tScanEnd + 4;
  const passLen = C.lockTicks + C.passTicks;
  for (let k = 0; k < C.passes; k++) {
    const tLock = tPass0 + k * passLen;
    const tRun = tLock + C.lockTicks;
    let route: Route | undefined;
    let tele: Actor[] = [];
    scene.at(tLock, () => {
      route = routeFor(k);
      const r = route;
      oph.state(S.lock).skin(SKIN_JUDGING);
      sound(dim, "dw_ophan_lock", pos, 1.1, 1 + k * 0.06);
      if (k === 0) sound(dim, "dw_ophan_eyes", pos, 0.9, 0.8);
      // telegraph: rings at the corners, a line of light along the whole route
      tele = r.corners.map((p) => scene.spawn("telegraph", p, { kind: 0, size: C.rimHalfWidth + 0.6, state: 1 }));
      // reposition: the wheel rises and drops onto the start of its route
      const from = pos;
      const to = r.pts[0];
      const ctrl = up(lerp(from, to, 0.5), 4);
      const yawTo = yawOf(sub(r.pts[1], r.pts[0]));
      scene.span(tLock, tRun, (p) => {
        pos = bezier(from, ctrl, to, p);
        yaw += angleDelta(yaw, yawTo) * 0.3;
        oph.move(pos, yaw);
      });
      scene.every(1, (e) => {
        for (let i = 1; i < r.pts.length; i++) {
          if ((i + e) % 4 !== 0) continue;
          const a = up(r.pts[i - 1], 0.3 - C.sweepAltitude), b = up(r.pts[i], 0.3 - C.sweepAltitude);
          line(dim, "dw_ophan_route", a, b, Math.min(12, Math.max(2, Math.ceil(dist(a, b) / 1.6))));
        }
      }, tLock, tRun);
    });

    // the run: position, facing and rim damage all come from the same per-tick pose
    const hit = new Set<string>();
    let flashed = 0;
    const strike = (h: Entity, fwd: V3, pass: number): void => {
      const m = marks.get(h.id);
      if (!damage(h, m ? C.markedDamage : C.damage, caster)) return;
      hit.add(h.id);
      const side = right(fwd);
      const sign = (h.location.x - pos.x) * side.x + (h.location.z - pos.z) * side.z >= 0 ? 1 : -1;
      shove(h, mul(side, sign), C.knockback, C.lift);
      particle(dim, "dw_ophan_impact", up(h.location, 1));
      particle(dim, "dw_ophan_sparks", up(h.location, 1));
      sound(dim, "dw_ophan_bell", h.location, 1.0, m ? 1.0 + pass * 0.08 : 0.85);
      if (m) {
        m.hits++;
        m.mark.skin(Math.min(2, m.hits));
        particle(dim, "dw_ophan_eye", up(h.location, 3.4));
      }
    };

    scene.at(tRun, () => {
      oph.state(S.sweep);
      sound(dim, "dw_ophan_sweep", pos, 1.2, 0.95 + k * 0.08);
    });
    scene.every(1, (e) => {
      const r = route;
      if (!r) return;
      const s = ((e + 1) / C.passTicks) * r.total;
      const { p, dir } = pointAt(r, s);
      pos = p;
      yaw += angleDelta(yaw, yawOf(dir)) * 0.45;
      oph.move(pos, yaw);
      const fwd = fromYaw(yaw);
      const ground = up(pos, -C.sweepAltitude);
      const chordA = add(ground, mul(fwd, C.rimChord)), chordB = add(ground, mul(fwd, -C.rimChord));
      // corner telegraphs flash as the rim reaches them
      while (flashed < tele.length && distXZ(tele[flashed].loc, pos) < C.rimChord) {
        const t = tele[flashed++];
        t.state(3);
        scene.after(8, () => scene.despawn(t));
      }
      particle(dim, "dw_ophan_rim", up(chordA, 0.8));
      particle(dim, "dw_ophan_rim", up(ground, 0.4));
      if (e % 2 === 0) particle(dim, "dw_ophan_sparks", up(ground, 0.3));
      if (e % 6 === 0) particle(dim, "dw_ophan_rim", up(pos, C.sweepAltitude - 0.5));
      if (e % 12 === 0) sound(dim, "dw_ophan_hum", pos, 0.9, 0.85 + k * 0.15 + (e / C.passTicks) * 0.25);
      for (const h of hostiles(dim, pos, C.rimChord + C.sweepAltitude + 2, caster)) {
        if (hit.has(h.id)) continue;
        const l = h.location;
        if (l.y < ground.y - 1.5 || l.y > ground.y + C.rimHeight) continue;
        if (distToSegment(v(l.x, 0, l.z), v(chordA.x, 0, chordA.z), v(chordB.x, 0, chordB.z)) > C.rimHalfWidth) continue;
        strike(h, fwd, k);
      }
    }, tRun, tRun + C.passTicks);
    scene.at(tRun + C.passTicks, () => {
      for (const t of tele) if (t.valid) { t.state(3); scene.after(8, () => scene.despawn(t)); }
    });
  }

  // ---- verdict: the gimbals burst open into an armillary sphere above the marked
  const tVerdict = tPass0 + C.passes * passLen;
  scene.at(tVerdict, () => {
    const live = liveMarks();
    const c = live.length ? mul(live.reduce((s, m) => add(s, flat(m.e.location)), v(0, 0, 0)), 1 / live.length) : flat(lastCentre);
    const top = up(groundBelow(dim, v(c.x, center.y + 4, c.z), 24), C.hoverHeight - 2);
    const from = pos;
    oph.state(S.verdict);
    sound(dim, "dw_ophan_verdict", top, 1.4);
    scene.span(tVerdict, tVerdict + VERDICT_HIT, (p) => { pos = lerp(from, top, p * p * (3 - 2 * p)); oph.move(pos, yaw); });
    scene.after(VERDICT_HIT, () => {
      particle(dim, "fx_flash", pos);
      ring(dim, "dw_ophan_letters", up(pos, -2), 3, 6);
      burst(dim, "dw_ophan_impact", pos, 3, 5);
      for (const m of liveMarks()) {
        line(dim, "dw_ophan_scan", pos, up(m.e.location, 1.2), 8);
        damage(m.e, C.verdictDamage, caster);
        particle(dim, "dw_ophan_impact", up(m.e.location, 1.2));
        particle(dim, "dw_ophan_ping", up(m.e.location, 0.2));
        sound(dim, "dw_ophan_bell", m.e.location, 1.0, 1.25);
      }
      for (const h of hostiles(dim, up(pos, -C.hoverHeight + 2), C.verdictPushRadius, caster)) {
        if (!marks.has(h.id)) knockback(h, pos, C.verdictKnockback, 0.5);
      }
      for (const m of marks.values()) {
        if (!m.mark.valid) continue;
        m.mark.state(3);
        const mk = m.mark;
        scene.after(8, () => scene.despawn(mk));
      }
    });
  });

  // ---- departure: wheels separate, fold into a single ring of letters and rise away
  const tDepart = tVerdict + secs(A.verdict) + 2;
  scene.at(tDepart, () => {
    oph.state(S.depart).skin(0);
    circle.state(3);
    sound(dim, "dw_ophan_depart", pos, 1.2);
    ring(dim, "dw_ophan_rim", pos, 4, 6);
  });
  scene.at(tDepart + secs(1.0), () => ring(dim, "dw_ophan_letters", pos, 2.5, 6));
  scene.at(tDepart + secs(1.4), () => { burst(dim, "dw_glyph_rise", up(pos, 2), 3, 6); particle(dim, "fx_flash", up(pos, 2)); });
  scene.endAt(tDepart + secs(A.depart) + 2);
});
