import { Player } from "@minecraft/server";
import { COLORS } from "../../config.js";
import { emit, ring, sound } from "../../core/fx.js";
import { fightersNear, hurt, push } from "../../core/targets.js";
import { add, dist, flatDir, hdist, perpXZ, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { line, loopRoad, skyArc } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";

/**
 * BANNER TRAIL - Joan writes a zig-zag road (gold ink first, so it can be read),
 * then sprints along it dragging the standard. Every leg stays behind her as a
 * current that flows the way she ran, sweeping players into her next move.
 * Phase II: three legs crossing on the player -> a pyre at the crossing.
 */
export function* bannerTrail(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  const start = { ...b.pos };
  const tp = b.predict(t, 10);
  const dir = flatDir(start, tp);
  const side = perpXZ(dir);
  const sgn = Math.random() < 0.5 ? 1 : -1;
  const D = Math.max(6, Math.min(14, hdist(start, tp)));
  const waypoints: V3[] = [start];
  if (!p2) {
    waypoints.push(add(add(start, scale(dir, D * 0.55)), scale(side, 3.6 * sgn)));
    waypoints.push(add(tp, scale(dir, 3.5)));
  } else {
    // three legs whose first and last cross right on the target (Crossroads Judgment)
    waypoints.push(add(tp, add(scale(dir, 3.2), scale(side, 3.2 * sgn))));
    waypoints.push(add(tp, add(scale(dir, 3.2), scale(side, -3.2 * sgn))));
    waypoints.push(add(tp, add(scale(dir, -3.4), scale(side, 3.2 * sgn))));
  }
  b.face(waypoints[1]);
  b.anim("trail_windup");
  const legs: Path[] = [];
  for (let i = 1; i < waypoints.length; i++) {
    const leg = b.groundRoad(line(waypoints[i - 1], waypoints[i]), { kind: "trail", speed: 0.45, form: b.tel(),
      life: p2 ? 130 : 170, radius: 1.0, tag: "trail" });
    if (!leg) break;
    if (legs.length) b.field.link(legs[legs.length - 1], leg);
    legs.push(leg);
  }
  if (!legs.length) {
    b.cooldown("trail", 60);
    return;
  }
  yield b.tel();
  b.anim("trail_dash");
  sound(b.dim, "joan.drag", b.pos, 1, 1);
  for (const leg of legs) {
    yield* b.ride(leg, 0, leg.length, p2 ? 1.15 : 1.0, p2 ? 7 : 6);
  }
  b.anim("recover");
  b.cooldown("trail", p2 ? 120 : 170);
  // combo: if the target is being carried by one of the legs, ride that leg to meet them
  if (t.isValid) {
    const r = b.field.riderPath(t);
    if (r && legs.includes(r)) b.brain.queueCombo("surge", "target is riding her trail", 30, r);
  }
  yield 10;
}

/**
 * PILGRIM'S SURGE - Joan leaps onto a road and rides it at impossible speed.
 * She reuses an existing road that leads towards the player, otherwise she
 * writes a road through the sky that bends down onto the player's predicted
 * position (Phase II: with a loop-de-loop, and up to three surges in a row).
 * Landing is marked by a growing lily; the slam sends out a ground shock ring
 * that can be jumped.
 */
export function* pilgrimsSurge(b: JoanBoss, t: Player, via?: unknown): SkillGen {
  const p2 = b.phase >= 2;
  const chain = p2 && hdist(b.pos, t.location) > 9 ? 2 : 1;
  for (let k = 0; k < chain; k++) {
    if (!t.isValid) break;
    let path: Path | undefined = via instanceof Path && via.isActive ? via : undefined;
    let s0 = 0;
    let s1 = 0;
    if (!path) path = reuseRoad(b, t);
    if (path) b.stats.reused++;
    if (path) {
      const n = path.nearest(b.pos);
      s0 = n.s;
      s1 = path.endS;
      if (Math.abs(s1 - s0) < 3) path = undefined;
    }
    if (!path) {
      const land = b.predict(t, b.tel(1.2) + 8);
      const from = add(b.pos, v(0, 0.2, 0));
      const pts = p2 && Math.random() < 0.6 ? loopRoad(from, land, 2.6) : skyArc(from, land, 5.5 + Math.min(4, hdist(from, land) * 0.15));
      path = b.airRoad(pts, { kind: "arc", speed: 0.6, form: b.tel(1.2), life: p2 ? 90 : 110, radius: 1.2,
        carryPlayers: false, memory: true, crossings: false });
      if (!path) {
        b.cooldown("surge", 40);
        return;
      }
      s0 = 0;
      s1 = path.length;
    }
    const landAt = path.pointAt(s1);
    b.face(path.pointAt(s0 + Math.sign(s1 - s0) * 3));
    b.anim("surge_windup");
    b.markImpact(landAt, 5.5, b.tel(1.2) + Math.round(Math.abs(s1 - s0) / 1.3), p2 ? COLORS.burningGold : COLORS.roadGold);
    yield path.isActive ? 10 : Math.max(8, path.activeAt - b.now);
    b.anim("surge_ride");
    sound(b.dim, "joan.surge", b.pos, 1.2, 1);
    yield* b.ride(path, s0, s1, p2 ? 1.45 : 1.25, 5, true);
    // the slam
    b.anim("surge_slam");
    yield 3;
    const at = { ...b.pos };
    b.strike(at, 2.6, p2 ? 11 : 9, 0.9, 0.5);
    b.impactFx(at, 2.6, p2 ? COLORS.burningGold : COLORS.roadGold);
    yield* shockRing(b, at, p2 ? 7 : 6, p2 ? 5 : 4);
    yield 8;
  }
  b.anim("recover");
  b.cooldown("surge", p2 ? 100 : 140);
  yield 16;
}

/** An existing road of hers that ends near the target and starts near her. */
function reuseRoad(b: JoanBoss, t: Player): Path | undefined {
  let best: Path | undefined;
  let bestScore = Infinity;
  for (const p of b.field.activePaths()) {
    if (p.o.loop || p.o.kind === "spoke" || p.o.kind === "ring" || p.o.kind === "stake") continue;
    const end = p.pointAt(p.endS);
    const startDist = p.nearest(b.pos).d;
    const endDist = dist(end, t.location);
    if (startDist > 10 || endDist > 6 || p.length < 6) continue;
    const score = startDist + endDist * 2;
    if (score < bestScore) {
      bestScore = score;
      best = p;
    }
  }
  return best;
}

/** Expanding ground shock: hits everyone still standing on the ground as it passes (jump to avoid). */
export function* shockRing(b: JoanBoss, at: V3, maxR: number, dmg: number): SkillGen {
  const hitSet = new Set<string>();
  ring(b.dim, at, 0.5, maxR, 0.5, b.phase >= 2 ? COLORS.burning : COLORS.road);
  for (let r = 1.5; r <= maxR; r += 0.9) {
    for (const p of fightersNear(b.dim, at, r + 0.6)) {
      if (hitSet.has(p.id)) continue;
      const d = hdist(p.location, at);
      if (d < r - 1.0 || d > r + 0.6) continue;
      if (!p.isOnGround || Math.abs(p.location.y - at.y) > 1.2) continue;
      hitSet.add(p.id);
      hurt(p, dmg, b.e);
      const away = flatDir(at, p.location);
      push(p, v(away.x * 0.6, 0.35, away.z * 0.6));
    }
    emit(b.dim, "joan:burst", add(at, v(0, 0.2, 0)), { color: COLORS.white, size: 0.4 });
    yield 1;
  }
}
