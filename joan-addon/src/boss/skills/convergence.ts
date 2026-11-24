import { Entity, Player } from "@minecraft/server";
import { COLORS, STANDARD } from "../../config.js";
import { emit, sound } from "../../core/fx.js";
import { allPlayersNear, foesNear, hurt, push } from "../../core/targets.js";
import { add, dist, flatDir, hdist, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { line } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { spawnMinion } from "../minions.js";

/** Standards planted by Convergence, so hits on them can be routed back to the skill. */
export const standardRoads = new Map<string, { path: Path; boss: JoanBoss; hits: number }>();

/**
 * CONVERGENCE OF THE STANDARD - Joan flings phantom standards around the
 * player. Each one writes a road that flows towards a single convergence
 * point; the roads MERGE there and funnel everything in (projectiles included)
 * for the Standard's Verdict, a pillar of light. Breaking a standard (3 hits)
 * makes its road reverse and fling outward - a learnable escape lane.
 * Phase II: four standards and the convergence point is Joan herself.
 */
export function* convergence(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  const focus: V3 = p2 ? { ...b.pos } : { ...t.location };
  const n = p2 ? 4 : 3;
  const R = 10;
  b.face(t.location);
  b.anim("converge_throw");
  const standards: Entity[] = [];
  const roads: Path[] = [];
  const base = Math.atan2(t.location.z - focus.z, t.location.x - focus.x) + Math.PI / n;
  const throwTimes = [6, 13, 19, 25];
  let thrown = 0;
  try {
    for (let tick = 0; tick < 26; tick++) {
      if (thrown < n && tick === throwTimes[thrown]) {
        const a = base + (thrown * Math.PI * 2) / n;
        let at = add(focus, v(Math.cos(a) * R, 0, Math.sin(a) * R));
        // never plant a standard on top of a player
        for (const p of allPlayersNear(b.dim, at, 2.5)) at = add(at, scale(flatDir(p.location, at), 2.5));
        const st = b.track(spawnMinion(b.dim, STANDARD, at, b.id));
        if (st) {
          standards.push(st);
          const road = b.groundRoad(line(at, focus), {
            kind: "converge", speed: p2 ? 0.48 : 0.42, radius: 1.0, form: b.tel(1.2), life: 140, tag: "converge",
            memory: true,
          });
          if (road) {
            roads.push(road);
            standardRoads.set(st.id, { path: road, boss: b, hits: 0 });
          }
          emit(b.dim, "joan:burst", add(at, v(0, 1.5, 0)), { color: COLORS.road, size: 1 });
          sound(b.dim, "joan.banner.snap", at, 1, 1.2);
        }
        thrown++;
      }
      yield 1;
    }
    b.anim("converge_call");
    const hold = p2 ? 50 : 62;
    for (let i = 0; i < hold; i += 5) {
      emit(b.dim, "joan:sigil", add(focus, v(0, 0.06, 0)), { size: 4 + (i / hold) * 2.5, life: 0.3, color: p2 ? COLORS.burningGold : COLORS.roadGold });
      if (i === hold - 20) {
        emit(b.dim, "joan:pillar", focus, { h: 10, color: COLORS.warn, life: 1.0, size: 0.4 });
        sound(b.dim, "joan.bell.high", focus, 1, 0.9);
      }
      yield 5;
    }
    // STANDARD'S VERDICT
    if (p2) {
      b.anim("melee_plant");
      yield 10;
    }
    emit(b.dim, "joan:pillar", focus, { h: 14, color: p2 ? COLORS.burningGold : COLORS.white, life: 0.8, size: 1.4 });
    b.impactFx(focus, 2.8, p2 ? COLORS.burningGold : COLORS.roadGold);
    for (const e of foesNear(b.dim, focus, 3.0)) {
      if (hdist(e.location, focus) > 2.8) continue;
      hurt(e, p2 ? 12 : 10, b.e);
      push(e, add(scale(flatDir(focus, e.location), 0.5), v(0, 0.9, 0)));
    }
    yield 14;
  } finally {
    for (const r of roads) b.field.retire(r, b.now, 6);
    for (const st of standards) {
      standardRoads.delete(st.id);
      if (st.isValid) emit(b.dim, "joan:burst", add(st.location, v(0, 1.4, 0)), { color: COLORS.road, size: 0.8 });
      b.untrack(st);
    }
  }
  b.cooldown("convergence", p2 ? 200 : 260);
  if (t.isValid && dist(t.location, focus) < 4 && !p2) b.brain.queueCombo("surge", "the target was funnelled in", 20);
}

/** A player struck a phantom standard. Three strikes shatter it and turn its road outward. */
export function hitStandard(st: Entity): void {
  const rec = standardRoads.get(st.id);
  if (!rec) return;
  rec.hits++;
  emit(st.dimension, "joan:burst", add(st.location, v(0, 1.5, 0)), { color: COLORS.white, size: 0.6 });
  if (rec.hits < 3) return;
  standardRoads.delete(st.id);
  const b = rec.boss;
  b.field.reverse(rec.path, 2, b.now);
  rec.path.o.color = COLORS.purified;
  rec.path.o.fling = 2.2;
  sound(st.dimension, "joan.waystone.turn", st.location, 1, 1.2);
  emit(st.dimension, "joan:pillar", st.location, { h: 4, color: COLORS.purified, life: 0.4, size: 0.4 });
  b.untrack(st);
}
