// Grimoire 04 - Plasma Magic: controlled plasma filaments, magnetic confinement, reconnection.
import { Entity, system } from "@minecraft/server";
import type { Cast } from "../context";
import type { Routine } from "../../core/tasks";
import { COLORS, Fx } from "../../core/fx";
import { bodyCenter, effect, pullToward, push } from "../../core/combat";
import { PHYSICAL_CAUSES, grantFallImmunity } from "../../core/defense";
import { V3, add, dirFromYawPitch, dist, dot, flatNorm, hdist, len, lerp, mul, norm, rotY, sub, v3, yawPitchOf } from "../../core/vec";
import { drive, fly, freeDistance, nearestEnemies, shock } from "../kit";
import { Incoming, arcPoint, hostileProjectiles, neutralize, redirect } from "../kit2";

const VI = COLORS.violet, MG = COLORS.magenta, UV = COLORS.ultraviolet, IN = COLORS.indigo, WH = COLORS.whitehot;

function filamentLine(c: Cast, a: V3, b: V3, n: number, color = VI, color2 = MG): void {
  for (let i = 0; i <= n; i++) c.particle("grimoire:plasma_trail", lerp(a, b, i / n), { color, color2, size: 1, count: 0.5 });
}

// ------------------------------------------------------------------------------------------ PL01
export function* coronalLash(c: Cast): Routine {
  const hand = () => add(c.eye(), add(mul(c.look(), 0.5), v3(0, -0.45, 0)));
  const whip = c.fx("grimoire:fx_pl_whip", hand(), { yaw: c.yaw, pitch: c.pitch, phase: 1, size: c.area });
  c.sound("grimoire.plasma.hum", hand(), 0.9, 1.3);
  for (let t = 0; t < 10; t++) {
    whip?.move(hand());
    if (t % 3 === 0) c.particle("grimoire:plasma_charge", hand(), { color: VI, color2: MG, size: 1, radius: 1 });
    yield 1;
  }
  whip?.phase(2);
  const reach = c.p("reach") * c.area;
  const sweeps = [
    { ph: 3, a0: -80, a1: 80, axis: "yaw" },
    { ph: 4, a0: 80, a1: -80, axis: "yaw" },
    { ph: 5, a0: -70, a1: 30, axis: "pitch" },
  ];
  for (const s of sweeps) {
    whip?.move(hand()).yaw(c.player.getRotation().y).pitch(c.player.getRotation().x);
    whip?.phase(s.ph);
    c.sound("grimoire.plasma.whip", hand(), 1, 0.9 + s.ph * 0.08);
    const hitIds = new Set<string>();
    const baseYaw = c.player.getRotation().y;
    const basePitch = c.player.getRotation().x;
    for (let t = 0; t <= 7; t++) {
      const k = t / 7;
      const ang = s.a0 + (s.a1 - s.a0) * k;
      const yaw = s.axis === "yaw" ? baseYaw + ang : baseYaw;
      const pitch = s.axis === "pitch" ? Math.max(-80, Math.min(80, basePitch + ang)) : basePitch;
      const dir = dirFromYawPitch(yaw, pitch);
      const side = s.axis === "yaw" ? rotY(flatNorm(dir), 90) : v3(0, 1, 0);
      const o = hand();
      for (let d = 1; d <= reach; d += 1) {
        // S-shaped body: the filament lags behind the swing and curls at the tip
        const p = add(add(o, mul(dir, d)), mul(side, Math.sin(d * 0.75 - k * 4) * 0.35 * d * 0.25));
        if (t % 2 === 0 && d % 2 === 0) c.particle("grimoire:plasma_trail", p, { color: d % 4 ? VI : MG, color2: WH, size: 1.2, count: 0.5, life: 1.6 });
        for (const e of c.enemies(p, c.p("width"))) {
          if (hitIds.has(e.id)) continue;
          hitIds.add(e.id);
          c.hit(e, c.p("damage"));
          push(e, s.axis === "yaw" ? mul(side, Math.sign(s.a1 - s.a0)) : dir, 0.7, s.axis === "pitch" ? -0.2 : 0.25);
          c.particle("grimoire:plasma_arc", bodyCenter(e), { color: MG, color2: WH, radius: 0.8, count: 1 });
        }
      }
      whip?.move(hand());
      yield 1;
    }
    yield 2;
  }
  whip?.phase(15);
  yield 10;
}

// ------------------------------------------------------------------------------------------ PL02
export function* helixBorer(c: Cast): Routine {
  const a = c.aim(c.p("range"));
  const start = add(c.origin, mul(c.dir, 1.6));
  const dir = norm(sub(a.point, start));
  const fx = c.fx("grimoire:fx_pl_borer", start, { dir, phase: 1, size: c.area });
  c.sound("grimoire.plasma.drill", start, 0.9, 0.8);
  yield 8;
  fx?.phase(2);
  let victim: Entity | undefined;
  let end = start;
  yield* fly(c, {
    fx, from: start, dir, speed: c.p("speed"), range: c.p("range"), radius: 0.9 * c.area, pierce: 1, homing: a.entity, homingRate: 0.3,
    trail: "grimoire:plasma_trail", trailColor: VI, trailColor2: MG,
    onHit: (e) => (victim = e),
    onEnd: (pos) => (end = pos),
  });
  if (victim?.isValid) {
    fx?.phase(3);
    c.sound("grimoire.plasma.drill", end, 1.3, 1.2);
    for (let i = 0; i < c.p("hits") && victim.isValid; i++) {
      const vc = bodyCenter(victim);
      const back = norm(sub(vc, c.player.location));
      fx?.move(sub(vc, mul(back, 0.7))).aim(back);
      c.hit(victim, c.p("damage"), { immediate: i % 2 === 0 });
      effect(victim, "slowness", 10, 3);
      c.particle("grimoire:plasma_arc", vc, { color: MG, color2: WH, radius: 0.7, count: 1 });
      yield 5;
    }
    end = victim.isValid ? bodyCenter(victim) : end;
  }
  fx?.phase(4);
  c.sound("grimoire.plasma.crack", end, 1.2, 0.9);
  c.particle("grimoire:plasma_burst", end, { color: VI, color2: WH, radius: 1.4, count: 1.5 });
  for (const e of c.enemies(end, 3)) if (e.id !== victim?.id) c.hit(e, c.p("fragmentDamage"));
  yield 12;
}

// ------------------------------------------------------------------------------------------ PL03
export function* prominenceUprising(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const right = rotY(flatNorm(c.dir), 90);
  const fx = c.fx("grimoire:fx_pl_prominence", point, { yaw: c.yaw + 90, phase: 1, size: (R / 3.5) });
  c.sound("grimoire.plasma.surge", point, 1.3, 1.0);
  for (let t = 0; t < 14; t++) {
    for (const sgn of [-1, 1]) c.particle("grimoire:plasma_arc", add(point, add(mul(right, sgn * R), v3(0, 0.3 + t * 0.2, 0))), { color: VI, color2: MG, radius: 0.8, count: 0.6, dir: v3(0, 1, 0) });
    yield 1;
  }
  fx?.phase(2);
  const lifted = c.enemies(point, R);
  for (const e of lifted) {
    effect(e, "levitation", c.p("liftTicks"), 1);
    c.hit(e, c.p("liftDamage"));
  }
  for (let t = 0; t < c.p("liftTicks"); t++) {
    if (t % 5 === 0) for (const e of lifted) if (e.isValid) pullToward(e, add(point, v3(0, 3, 0)), 0.15);
    if (t % 6 === 0) c.particle("grimoire:plasma_arc", add(point, v3(0, 3.5, 0)), { color: MG, color2: WH, radius: 1.8, count: 1 });
    yield 1;
  }
  fx?.phase(3);
  c.sound("grimoire.plasma.reconnect", point, 1.0, 1.4);
  yield 6;
  for (const e of lifted) {
    if (!e.isValid) continue;
    try {
      e.removeEffect("levitation");
    } catch {
      /* gone */
    }
    drive(e, v3(0, -1.6, 0));
  }
  shock(c, point, R, c.p("damage"), { knock: 1.1, up: 0.2, color: VI, color2: WH, shake: 0.6, minK: 0.6 });
  c.particle("grimoire:plasma_burst", add(point, v3(0, 0.5, 0)), { color: MG, color2: WH, radius: 2.4, count: 2 });
  yield 16;
}

// ------------------------------------------------------------------------------------------ PL04
export function* arcShearCascade(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("membranes");
  const dur = c.p("duration") * 20;
  const paths: { a: V3; b: V3; fx?: Fx; hit: Set<string>; delay: number }[] = [];
  for (let i = 0; i < n; i++) {
    const dir = rotY(v3(0, 0, 1), c.yaw + 45 + i * (180 / n) * 1.6);
    const perp = rotY(dir, 90);
    const off = (i - (n - 1) / 2) * 1.7;
    const a = add(add(point, mul(dir, -R)), mul(perp, off));
    const b = add(add(point, mul(dir, R)), mul(perp, -off * 0.5));
    paths.push({ a, b, hit: new Set(), delay: i * 6, fx: c.fx("grimoire:fx_pl_membrane", a, { dir: flatNorm(sub(b, a)), phase: 1, size: c.area }) });
  }
  c.sound("grimoire.plasma.membrane", point, 1.2, 1);
  yield 10;
  for (const p of paths) p.fx?.phase(2);
  const erupted = new Set<string>();
  for (let t = 0; t < dur + 6 * n; t++) {
    const pos = paths.map((p) => {
      const k = Math.max(0, Math.min(1, (t - p.delay) / dur));
      return lerp(p.a, p.b, k);
    });
    paths.forEach((p, i) => {
      p.fx?.move(pos[i]).yaw(yawPitchOf(sub(p.b, p.a)).yaw + Math.sin((t + i * 7) * 0.15) * 25);
      const fwd = flatNorm(sub(p.b, p.a));
      const side = rotY(fwd, 90);
      for (const e of c.enemies(pos[i], 2.6)) {
        if (p.hit.has(e.id)) continue;
        const rel = sub(e.location, pos[i]);
        if (Math.abs(dot(rel, side)) < 1.8 * c.area && Math.abs(dot(rel, fwd)) < 0.9) {
          p.hit.add(e.id);
          c.hit(e, c.p("damage"));
          push(e, fwd, 0.6, 0.2);
        }
      }
    });
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const key = `${i}:${j}`;
        if (erupted.has(key) || t < paths[j].delay) continue;
        if (hdist(pos[i], pos[j]) < 2.2) {
          erupted.add(key);
          const at = c.ground(lerp(pos[i], pos[j], 0.5), 6);
          const fl = c.fx("grimoire:fx_pl_flare", at, { phase: 1, size: 1.2 * c.area });
          c.run(dissolveLater(fl, 26), "flare");
          c.blast(at, 3, c.p("intersectionDamage"));
          c.particle("grimoire:plasma_burst", add(at, v3(0, 1, 0)), { color: WH, color2: VI, radius: 1.6, count: 1.5 });
          c.sound("grimoire.plasma.crack", at, 1.2, 0.8);
        }
      }
    yield 1;
  }
  yield 6;
}

function* dissolveLater(fx: Fx | undefined, ticks: number): Routine {
  yield ticks;
  fx?.dissolve(10);
}

// ------------------------------------------------------------------------------------------ PL05
export function* stellaratorWard(c: Cast): Routine {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_stellarator", p.location, { phase: 1, size: c.area });
  c.sound("grimoire.plasma.field", p.location, 1, 1.2);
  c.ward({
    label: "Stellarator Ward",
    priority: 30,
    protects: (e) => e.id === p.id,
    absorb: (info) => {
      if (info.cause === "projectile") return 0;
      return PHYSICAL_CAUSES.has(info.cause) ? info.damage * (1 - c.p("reduction")) : info.damage;
    },
    react: () => fx?.pulse(),
  });
  yield 10;
  fx?.phase(2);
  const curving: { inc: Incoming; until: number; spin: number }[] = [];
  const seen = new Set<string>();
  const R = c.p("radius") * c.area;
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    fx?.follow(p, v3(0, 0, 0));
    if (t % 2 === 0) {
      for (const inc of hostileProjectiles(c, p.location, R + 3, seen)) {
        const to = sub(bodyCenter(p), inc.e.location);
        if (dot(inc.vel, to) <= 0) continue;
        seen.add(inc.e.id);
        const spin = Math.random() < 0.5 ? 1 : -1;
        redirect(inc, add(rotY(flatNorm(inc.vel), 80 * spin), v3(0, 0.25, 0)), 0.9, p);
        curving.push({ inc, until: system.currentTick + 6, spin });
        fx?.pulse();
        c.sound("grimoire.plasma.zap", inc.e.location, 0.8, 1.4);
      }
    }
    for (let i = curving.length - 1; i >= 0; i--) {
      const q = curving[i];
      if (!q.inc.e.isValid) {
        curving.splice(i, 1);
        continue;
      }
      q.inc.vel = q.inc.e.getVelocity();
      redirect(q.inc, rotY(flatNorm(q.inc.vel), 25 * q.spin), 1);
      c.particle("grimoire:plasma_trail", q.inc.e.location, { color: MG, color2: WH, size: 1, count: 0.5 });
      if (system.currentTick >= q.until) {
        c.particle("grimoire:plasma_burst", q.inc.e.location, { color: VI, color2: WH, radius: 0.6, count: 0.6 });
        neutralize(q.inc);
        curving.splice(i, 1);
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL06
export function* coronaMolt(c: Cast): Routine {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_molt", p.location, { yaw: c.yaw, phase: 1 });
  c.sound("grimoire.plasma.hum", p.location, 0.8, 1.6);
  let triggered: { attacker?: Entity; at: V3 } | undefined;
  const ward = c.ward({
    label: "Corona Molt",
    priority: 60,
    protects: (e) => e.id === p.id && !triggered,
    absorb: (info) => {
      if (triggered || info.damage < c.p("threshold")) return info.damage;
      if (!PHYSICAL_CAUSES.has(info.cause) && info.cause !== "magic") return info.damage;
      triggered = { attacker: info.attacker, at: info.hurt.location };
      return Math.max(0, info.damage - c.p("maxAbsorb") * c.power);
    },
  });
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20 && c.ok && !triggered; t++) {
    fx?.follow(p).yaw(p.getRotation().y);
    yield 1;
  }
  if (!triggered) return;
  ward.alive = false;
  const at = triggered.at;
  const away = triggered.attacker?.isValid ? flatNorm(sub(at, triggered.attacker.location)) : flatNorm(mul(c.look(), -1));
  fx?.phase(3);
  fx?.move(add(at, mul(away, -0.4)));
  c.sound("grimoire.plasma.crack", at, 1.3, 0.7);
  c.flash(at, 10, { r: 0.85, g: 0.5, b: 1 }, 0.08);
  c.particle("grimoire:plasma_burst", add(at, v3(0, 1, 0)), { color: MG, color2: WH, radius: 2.2, count: 2 });
  for (const e of c.enemies(at, c.p("radius"))) {
    c.hit(e, c.p("damage"));
    push(e, sub(e.location, at), 1.3, 0.35);
    effect(e, "slowness", 50, 2);
    effect(e, "weakness", 60, 0);
  }
  yield 18;
}

// ------------------------------------------------------------------------------------------ PL07
export function* fieldlineHarp(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("anchors");
  const anchors: V3[] = [];
  for (let i = 0; i < n; i++) {
    const ang = c.yaw + (360 * i) / n;
    anchors.push(add(c.ground(add(point, mul(rotY(v3(0, 0, 1), ang), R)), 6), v3(0, 1.1 + (i % 2) * 1.0, 0)));
  }
  for (const a of anchors) {
    c.fx("grimoire:fx_pl_anchor", sub(a, v3(0, 1, 0)), { phase: 1 });
    c.particle("grimoire:plasma_arc", a, { color: VI, color2: MG, radius: 0.6, count: 0.6 });
    yield 2;
  }
  c.sound("grimoire.plasma.hum", point, 1.1, 0.8);
  const pairs: [number, number][] = [];
  for (let i = 0; i < n; i++) pairs.push([i, (i + 1) % n]);
  for (let i = 0; i < n / 2; i++) pairs.push([i, i + n / 2]);
  const strings = pairs.map(([i, j]) => {
    const a = anchors[i], b = anchors[j];
    const fx = c.fx("grimoire:fx_pl_string", a, { dir: sub(b, a), len: dist(a, b), phase: 1 });
    return { a, b, fx, last: new Map<string, number>() };
  });
  yield 10;
  for (const s of strings) s.fx?.phase(2);
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 2 === 0) {
      for (const s of strings) {
        for (const e of c.along(s.a, s.b, 0.8)) {
          const last = s.last.get(e.id) ?? -99;
          if (t - last < 20) continue;
          s.last.set(e.id, t);
          s.fx?.pulse();
          c.sound("grimoire.plasma.zap", bodyCenter(e), 0.9, 0.8 + Math.random() * 0.4);
          for (const v of c.along(s.a, s.b, 1.3)) {
            c.hit(v, c.p("damage"));
            effect(v, "slowness", 40, 2);
          }
          filamentLine(c, s.a, s.b, Math.ceil(dist(s.a, s.b)), MG, WH);
        }
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL08
export function* polarityOrchestra(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const n = c.p("pylons");
  const pylons: { at: V3; fx?: Fx }[] = [];
  for (let i = 0; i < n; i++) {
    const at = c.ground(add(point, mul(rotY(v3(0, 0, 1), c.yaw + (360 * i) / n), R)), 6);
    pylons.push({ at, fx: c.fx("grimoire:fx_pl_pylon", at, { phase: 1, size: c.area }) });
    yield 2;
  }
  c.sound("grimoire.plasma.pylon", point, 1.2, 0.8);
  yield 8;
  const patterns = [
    [1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1],
    [1, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 1],
  ];
  let pat = patterns[0];
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 30 === 0) {
      pat = patterns[(t / 30) % patterns.length];
      pylons.forEach((p, i) => p.fx?.phase(pat[i % 6] ? 3 : 4));
      c.sound("grimoire.plasma.pylon", point, 1, pat[0] ? 1.2 : 0.8);
      pylons.forEach((p, i) => {
        if (!pat[i % 6]) return;
        for (const e of c.enemies(p.at, 2.6)) {
          c.hit(e, c.p("damage"));
          c.particle("grimoire:plasma_arc", bodyCenter(e), { color: MG, color2: WH, radius: 0.7, count: 0.8 });
        }
      });
    }
    if (t % 4 === 0) {
      for (const e of c.enemies(point, R + 2)) {
        let force = v3(0, 0, 0);
        pylons.forEach((p, i) => {
          const d = sub(add(p.at, v3(0, 1, 0)), e.location);
          const dd = len(d);
          if (dd > 7 || dd < 0.6) return;
          const k = (1 - dd / 7) * (pat[i % 6] ? 1 : -1);
          force = add(force, mul(flatNorm(d), k));
        });
        if (len(force) > 0.05) drive(e, mul(force, c.p("force") * 0.25));
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL09
export function* staticHorizon(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const plane = add(point, v3(0, c.p("height"), 0));
  const fx = c.fx("grimoire:fx_pl_horizon", plane, { yaw: c.yaw, phase: 1, size: R / 10 });
  c.sound("grimoire.plasma.field", plane, 1.3, 0.7);
  yield 16;
  fx?.phase(2);
  const seen = new Set<string>();
  for (let t = 0; t < c.p("duration") * 20; t++) {
    if (t % 2 === 0) {
      for (const inc of hostileProjectiles(c, plane, R + 1, seen)) {
        if (hdist(inc.e.location, plane) > R || Math.abs(inc.e.location.y - plane.y) > 3) continue;
        seen.add(inc.e.id);
        const v = flatNorm(inc.vel);
        redirect(inc, add(rotY(v, (Math.random() - 0.5) * 220), v3(0, 0.6, 0)), 0.5, c.player);
        c.particle("grimoire:plasma_arc", inc.e.location, { color: IN, color2: WH, radius: 0.6, count: 0.6 });
      }
    }
    if (t % 30 === 15) {
      fx?.pulse();
      c.sound("grimoire.plasma.zap", plane, 0.9, 0.6);
      for (const e of c.enemies(point, R)) {
        if (e.location.y > plane.y + 1) continue;
        effect(e, "slowness", 40, 2);
        effect(e, "weakness", 40, 0);
        c.hit(e, c.p("damage"));
        c.particle("grimoire:plasma_trail", bodyCenter(e), { color: IN, color2: VI, size: 1.3, count: 1 });
      }
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL10
export function* ionSkates(c: Cast): Routine {
  const p = c.player;
  const fx = c.fx("grimoire:fx_pl_skates", p.location, { yaw: c.yaw, phase: 1, len: 1 });
  c.sound("grimoire.plasma.skate", p.location, 1, 1);
  let lastYaw = c.yaw;
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    effect(p, "speed", 25, c.p("speed"));
    grantFallImmunity(p.id, 30);
    const v = p.getVelocity();
    const hs = Math.hypot(v.x, v.z);
    const moveYaw = hs > 0.05 ? yawPitchOf(v3(v.x, 0, v.z)).yaw : p.getRotation().y;
    const dy = ((moveYaw - lastYaw + 540) % 360) - 180;
    lastYaw = moveYaw;
    fx?.follow(p, v3(0, 0.02, 0)).yaw(moveYaw).length(1 + Math.min(1.5, hs * 3));
    if (t > 6) fx?.phase(Math.abs(dy) < 3 ? 2 : dy > 0 ? 4 : 3);
    if (hs > 0.08 && t % 2 === 0) c.particle("grimoire:plasma_trail", add(p.location, v3(0, 0.1, 0)), { color: VI, color2: WH, size: 0.9, count: 0.5, life: 2 });
    if (hs > 0.08 && p.isOnGround && t % 5 === 0) drive(p, v3((v.x / hs) * c.p("boost"), 0, (v.z / hs) * c.p("boost")));
    if (t % 30 === 0 && hs > 0.1) c.sound("grimoire.plasma.skate", p.location, 0.6, 1 + hs);
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL11
export function* prominenceSling(c: Cast): Routine {
  const p = c.player;
  const fwd = flatNorm(c.dir);
  const behind = add(p.location, mul(fwd, -1.4));
  const fx = c.fx("grimoire:fx_pl_sling", behind, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.sling", behind, 1.2, 1);
  yield 8;
  fx?.phase(2);
  for (let t = 0; t < 12 && c.ok; t++) {
    if (t < 6) drive(p, mul(fwd, -0.12));
    c.particle("grimoire:plasma_charge", add(behind, v3(0, 2.2, 0)), { color: VI, color2: MG, radius: 1.5, size: 1 });
    yield 1;
  }
  if (!c.ok) return;
  const look = c.look();
  const launchDir = norm(add(flatNorm(look), v3(0, Math.max(0.25, -look.y * 0 + 0.35), 0)));
  const free = freeDistance(c.dim, c.eye(), launchDir, 14);
  const k = Math.max(0.35, Math.min(1, free / 12));
  fx?.phase(3);
  c.sound("grimoire.plasma.surge", p.location, 1.1, 1.4);
  grantFallImmunity(p.id, 200);
  drive(p, add(mul(flatNorm(look), c.p("power") * 0.5 * k), v3(0, c.p("lift") * k, 0)));
  const tail = c.fx("grimoire:fx_pl_tail", p.location, { yaw: c.yaw, phase: 1 });
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    const v = p.getVelocity();
    tail?.follow(p, v3(0, 0.2, 0));
    if (len(v) > 0.05) tail?.aim(mul(v, -1));
    if (t % 2 === 0) c.particle("grimoire:plasma_trail", add(p.location, v3(0, 0.8, 0)), { color: MG, color2: VI, size: 1.2, count: 1, life: 2 });
    if (t > 8 && p.isOnGround) break;
    yield 1;
  }
  c.particle("grimoire:plasma_burst", p.location, { color: VI, color2: WH, radius: 1, count: 0.8 });
}

// ------------------------------------------------------------------------------------------ PL12
export function* auroralManta(c: Cast): Routine {
  const p = c.player;
  let pos = add(p.location, v3(0, 4.5, 0));
  const fx = c.fx("grimoire:fx_pl_manta", pos, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.manta", pos, 1.3, 1);
  for (let t = 0; t < 24; t++) {
    if (t % 3 === 0) c.particle("grimoire:plasma_charge", pos, { color: VI, color2: MG, radius: 3, size: 1.5 });
    yield 1;
  }
  fx?.phase(2);
  let orbit = c.yaw;
  let nextDive = 8;
  let nextTail = 30;
  const range = c.p("range");
  for (let t = 0; t < c.p("duration") * 20 && c.ok; t++) {
    const home = add(p.location, add(mul(rotY(v3(0, 0, 1), orbit), 3.6), v3(0, 4.5, 0)));
    orbit += 3;
    const target = nearestEnemies(c, p.location, range, 1)[0];
    if (target && t >= nextDive) {
      // dive: swoop down along a curve onto the target, then climb back
      fx?.phase(3);
      c.sound("grimoire.plasma.whip", pos, 1.2, 0.6);
      const from = pos;
      for (let i = 1; i <= 12; i++) {
        const goal = target.isValid ? bodyCenter(target) : from;
        const ctrl = add(lerp(from, goal, 0.5), v3(0, 3.5, 0));
        const np = arcPoint(from, ctrl, goal, i / 12);
        fx?.move(np).aim(sub(np, pos));
        pos = np;
        if (i % 2 === 0) c.particle("grimoire:plasma_trail", pos, { color: VI, color2: MG, size: 1.5, count: 1 });
        yield 1;
      }
      if (target.isValid) {
        c.hit(target, c.p("diveDamage"));
        push(target, sub(target.location, from), 1.0, 0.45);
        c.particle("grimoire:plasma_burst", bodyCenter(target), { color: MG, color2: WH, radius: 1.4, count: 1.4 });
        c.sound("grimoire.plasma.crack", pos, 1.1, 1);
      }
      const back = pos;
      for (let i = 1; i <= 12; i++) {
        const goal = add(p.location, v3(0, 4.5, 0));
        const np = arcPoint(back, add(lerp(back, goal, 0.5), v3(0, 4, 0)), goal, i / 12);
        fx?.move(np).aim(sub(np, pos));
        pos = np;
        yield 1;
      }
      fx?.phase(2);
      nextDive = t + 24 + 70;
      nextTail = t + 24 + 30;
      t += 24;
      continue;
    }
    pos = lerp(pos, home, 0.2);
    fx?.move(pos).yaw(orbit + 90).pitch(0);
    if (target && t >= nextTail && dist(pos, bodyCenter(target)) < range) {
      fx?.pulse();
      const tc = bodyCenter(target);
      filamentLine(c, pos, tc, Math.ceil(dist(pos, tc) * 1.5), MG, WH);
      c.hit(target, c.p("tailDamage"));
      c.sound("grimoire.plasma.zap", tc, 1, 1.1);
      nextTail = t + 40;
    }
    yield 1;
  }
}

// ------------------------------------------------------------------------------------------ PL13
export function* magneticReconnection(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const right = rotY(flatNorm(c.dir), 90);
  const top = add(point, v3(0, 3, 0));
  const loops = [-1, 1].map((sgn) =>
    c.fx("grimoire:fx_pl_fieldloop", add(top, mul(right, sgn * 6)), { yaw: c.yaw + 90, phase: sgn > 0 ? 2 : 3, size: c.area }),
  );
  const xp = c.fx("grimoire:fx_pl_xpoint", add(point, v3(0, 4.2, 0)), { yaw: c.yaw, phase: 1, size: c.area });
  const seal = c.fx("grimoire:fx_circle_pl", add(point, v3(0, 0.06, 0)), { size: R / 1, variant: 1, phase: 1 });
  c.sound("grimoire.plasma.field", top, 1.3, 0.6);
  const delay = c.p("delay");
  for (let t = 0; t < delay; t++) {
    const k = t / delay;
    loops.forEach((l, i) => l?.move(add(top, mul(right, (i ? 1 : -1) * (6 - 4 * k)))));
    if (t === 10) xp?.phase(2);
    if (t % 10 === 0) {
      for (const e of c.enemies(point, R)) {
        effect(e, "slowness", 14, 1);
        pullToward(e, point, 0.12);
      }
      c.particle("grimoire:plasma_charge", add(point, v3(0, 4.2, 0)), { color: WH, color2: MG, radius: 2.5, size: 1.5 });
    }
    yield 1;
  }
  xp?.phase(3);
  seal?.phase(3);
  for (const l of loops) l?.phase(4);
  c.sound("grimoire.plasma.reconnect", point, 1.5, 1);
  c.shake(point, 20, 0.7, 0.6);
  c.flash(point, 18, { r: 0.9, g: 0.6, b: 1 }, 0.06);
  shock(c, point, R * 0.6, c.p("damage"), { knock: 1.3, up: 0.45, color: WH, color2: VI, minK: 0.6 });
  const n = c.p("jets");
  const jetLen = c.p("jetLength") * c.area;
  for (let i = 0; i < n; i++) {
    const dir = norm(add(rotY(v3(0, 0, 1), c.yaw + (360 * i) / n + 15), v3(0, -0.12, 0)));
    const from = add(point, v3(0, 1.4, 0));
    const jet = c.fx("grimoire:fx_pl_jet", from, { dir, len: jetLen, phase: 1, size: c.area });
    c.run(dissolveLater(jet, 18), "jet");
    for (const e of c.along(from, add(from, mul(dir, jetLen)), 1.6)) {
      c.hit(e, c.p("jetDamage"));
      push(e, dir, 1.0, 0.3);
    }
  }
  yield 24;
}

// ------------------------------------------------------------------------------------------ PL14
export function* stellaratorCathedral(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const apex = add(point, v3(0, c.p("height"), 0));
  const fx = c.fx("grimoire:fx_pl_cathedral", apex, { yaw: c.yaw, phase: 1, size: c.area });
  c.sound("grimoire.plasma.surge", apex, 1.6, 0.6);
  for (let t = 0; t < 40; t++) {
    if (t % 4 === 0) filamentLine(c, add(c.player.location, v3(0, 1.5, 0)), apex, 8, VI, MG);
    yield 1;
  }
  fx?.phase(2);
  const total = c.p("duration") * 20;
  for (let t = 0; t < total - 50; t++) {
    if (t % 20 === 0) {
      for (const e of c.dim.getPlayers({ location: point, maxDistance: c.p("allyRadius") })) {
        if (e.id === c.player.id || !c.isEnemy(e)) effect(e, "resistance", 30, 1);
      }
      c.particle("grimoire:plasma_trail", add(point, v3(0, 0.3, 0)), { color: IN, color2: WH, size: 2, count: 3, radius: c.p("allyRadius") });
    }
    if (t % c.p("interval") === 0) {
      for (const e of nearestEnemies(c, point, R, c.p("targets"))) {
        const from = add(apex, v3(0, -1.6, 0));
        const to = bodyCenter(e);
        const br = c.fx("grimoire:fx_pl_branch", from, { dir: sub(to, from), len: dist(from, to), phase: 1 });
        c.run(dissolveLater(br, 10), "branch");
        c.hit(e, c.p("streamDamage"));
        c.particle("grimoire:plasma_arc", to, { color: MG, color2: WH, radius: 0.8, count: 1 });
      }
      c.sound("grimoire.plasma.zap", apex, 1.2, 0.7);
    }
    yield 1;
  }
  fx?.phase(3);
  c.sound("grimoire.plasma.drill", apex, 1.5, 0.5);
  yield 30;
  const n = c.p("beams");
  for (let i = 0; i < n; i++) {
    const dir = norm(add(rotY(v3(0, 0, 1), c.yaw + (360 * i) / n), v3(0, -0.75, 0)));
    const from = add(apex, v3(0, -1, 0));
    const bm = c.fx("grimoire:fx_pl_beam", from, { dir, len: c.p("beamLength"), phase: 1, size: c.area });
    c.run(dissolveLater(bm, 20), "beam");
    for (const e of c.along(from, add(from, mul(dir, c.p("beamLength"))), 1.8)) c.hit(e, c.p("beamDamage"));
  }
  c.sound("grimoire.plasma.reconnect", point, 1.6, 1.2);
  c.shake(point, 24, 0.8, 0.8);
  c.flash(point, 22, { r: 0.85, g: 0.55, b: 1 }, 0.1);
  yield 20;
}

// ------------------------------------------------------------------------------------------ PL15
export function* heavenwideReconnection(c: Cast): Routine {
  const { point } = c.aimGround(c.p("range"));
  const R = c.p("radius") * c.area;
  const sky = add(point, v3(0, c.p("height"), 0));
  // Phase I - Celestial Field Genesis
  c.sound("grimoire.plasma.surge", c.player.location, 1.6, 0.5);
  c.fx("grimoire:fx_circle_pl", add(c.player.location, v3(0, 0.06, 0)), { size: 3, variant: 2, phase: 1 });
  c.fx("grimoire:fx_circle_pl", add(point, v3(0, 0.08, 0)), { size: R, variant: 0, phase: 2 });
  for (let t = 0; t < 14; t++) {
    for (let k = 0; k < 3; k++) {
      const off = rotY(v3(0, 0, 1), c.yaw + t * 26 + k * 120);
      c.particle("grimoire:plasma_trail", add(c.player.location, add(mul(off, 1.2), v3(0, 1 + t * 0.8, 0))), { color: k ? VI : MG, color2: WH, size: 1.6, count: 1, life: 2 });
    }
    yield 1;
  }
  const net = c.fx("grimoire:fx_pl_network", sky, { yaw: c.yaw, phase: 1, size: (R / 16) * 1.0 });
  c.shake(point, 30, 0.4, 1.5);
  yield 44;
  // Phase II - The Great Confinement
  net?.phase(2);
  c.sound("grimoire.plasma.field", point, 1.6, 0.5);
  const junctions = new Map<string, { fx?: Fx; e: Entity }>();
  for (let t = 0; t < 100 && c.ok; t++) {
    if (t % 20 === 0) {
      for (const e of nearestEnemies(c, point, R, 8)) {
        if (!junctions.has(e.id)) junctions.set(e.id, { e, fx: c.fx("grimoire:fx_pl_junction", add(e.location, v3(0, 3, 0)), { phase: 1, size: c.area }) });
        const from = add(sky, v3((Math.random() - 0.5) * 6, -1, (Math.random() - 0.5) * 6));
        filamentLine(c, from, bodyCenter(e), 10, MG, WH);
        c.bind(e, 26, { pin: true, slowAmp: 3 });
        c.hit(e, c.p("streamDamage"));
      }
      c.sound("grimoire.plasma.zap", sky, 1.4, 0.6);
    }
    for (const j of junctions.values()) if (j.e.isValid) j.fx?.follow(j.e, v3(0, 3, 0), 0);
    yield 1;
  }
  // Phase III - The Grand Reconnection
  net?.phase(3);
  yield 14;
  net?.phase(4);
  c.sound("grimoire.plasma.reconnect", point, 2.0, 0.8);
  c.flash(point, R * 2, { r: 0.9, g: 0.75, b: 1 }, 0.12);
  c.shake(point, R * 3, 1.0, 1.2);
  for (const j of junctions.values()) {
    j.fx?.pulse();
    if (j.e.isValid) {
      c.hit(j.e, c.p("junctionDamage"), { immediate: true });
      c.particle("grimoire:plasma_burst", bodyCenter(j.e), { color: WH, color2: MG, radius: 1.8, count: 1.6 });
    }
  }
  const jets = [0, 90, 180, 270].map((a) => ({ a, fx: c.fx("grimoire:fx_pl_sweepjet", add(sky, v3(0, -2, 0)), { yaw: c.yaw + a, pitch: 32, len: R * 1.15, phase: 1, size: c.area }), hit: new Set<string>() }));
  for (let t = 0; t < 24; t++) {
    jets.forEach((j, i) => {
      const yaw = c.yaw + j.a + t * 4.5;
      const dir = dirFromYawPitch(yaw, 32);
      j.fx?.yaw(yaw);
      const from = add(sky, v3(0, -2, 0));
      for (const e of c.along(from, add(from, mul(dir, R * 1.15)), 2.0)) {
        if (j.hit.has(e.id)) continue;
        j.hit.add(e.id);
        c.hit(e, c.p("jetDamage"));
        push(e, flatNorm(dir), 0.8, 0.3);
      }
      if (t % 4 === i) c.particle("grimoire:plasma_burst", c.ground(add(from, mul(dir, R)), 14), { color: VI, color2: WH, radius: 1.6, count: 1 });
    });
    yield 1;
  }
  for (const j of jets) j.fx?.dissolve(12);
  for (const j of junctions.values()) j.fx?.dissolve(12);
  net?.phase(15);
  for (let t = 0; t < 26; t++) {
    if (t % 3 === 0) c.particle("grimoire:plasma_trail", add(sky, v3((Math.random() - 0.5) * R, (Math.random() - 0.5) * 4, (Math.random() - 0.5) * R)), { color: MG, color2: VI, size: 2, count: 2, life: 2 });
    yield 1;
  }
}

