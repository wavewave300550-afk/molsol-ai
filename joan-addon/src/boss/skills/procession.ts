import { Entity, Player } from "@minecraft/server";
import { COLORS, ECHO } from "../../config.js";
import { emit, sound } from "../../core/fx.js";
import { foesNear, hurt, push } from "../../core/targets.js";
import { add, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { line } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { removeQuietly, setProp, spawnMinion } from "../minions.js";

/**
 * MARTYR'S PROCESSION - every road Joan wrote earlier in the fight leaves a
 * scar. She kneels, lifts the standard, and the scars wake one after another
 * (gold first, so they can be read). Translucent echoes of Joan march along
 * each re-woken road in the order she once wrote them; they strike whoever
 * they walk through. An echo breaks with a single blow, and its road dies
 * with it. With too few scars she lays a ring of procession roads first.
 * Phase II: burning martyrs, burning roads, pyres where the old roads cross.
 */
export function* martyrsProcession(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  const scars = b.field.scars.slice(-(p2 ? 6 : 5));
  b.field.scars = b.field.scars.filter((s) => !scars.includes(s));
  const routes: V3[][] = scars.map((s) => (s.flow > 0 ? s.pts : s.pts.slice().reverse()));
  if (routes.length < 3) {
    // not enough memories: lay processional spokes around the arena centre
    const c = b.home;
    const n = 4 - routes.length;
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2 + Math.random();
      const p0 = add(c, v(Math.cos(a) * 14, 0, Math.sin(a) * 14));
      const p1 = add(c, v(Math.cos(a + 2.2) * 14, 0, Math.sin(a + 2.2) * 14));
      routes.push(line(p0, p1));
    }
  }
  b.anim("procession_raise");
  sound(b.dim, p2 ? "joan.choir.dark" : "joan.choir.light", b.pos, 0.9, 1);
  yield 24;
  b.anim("procession_hold");
  const roads: Path[] = [];
  const echoes: Entity[] = [];
  let marching = 0;
  try {
    for (const pts of routes) {
      const road = b.groundRoad(pts, {
        kind: "procession", speed: 0.34, radius: 1.0, form: b.tel(1.2), life: 220, memory: false, tag: "procession",
      });
      if (!road) continue;
      roads.push(road);
      const startTick = b.now + b.tel(1.2);
      marching++;
      let echo: Entity | undefined;
      let s = 0;
      const hitSet = new Set<string>();
      b.addTask({
        name: "echo",
        step: (now) => {
          if (now < startTick) return true;
          if (!road.alive) return false;
          if (!echo) {
            echo = b.track(spawnMinion(b.dim, ECHO, road.pointAt(0), b.id));
            if (!echo) return false;
            echoes.push(echo);
            setProp(echo, "joan:fire", p2);
            emit(b.dim, "joan:pillar", road.pointAt(0), { h: 4, color: p2 ? COLORS.burningGold : COLORS.white, life: 0.4, size: 0.4 });
          }
          if (!echo.isValid) {
            // broken by a player: the road it walked dies with it
            b.field.retire(road, now, 4);
            return false;
          }
          s += 0.3;
          const here = road.pointAt(Math.min(s, road.length));
          try {
            echo.teleport(here, { facingLocation: road.pointAt(Math.min(s + 1.5, road.length)) });
          } catch {
            return false;
          }
          for (const f of foesNear(b.dim, add(here, v(0, 1, 0)), 1.4)) {
            if (hitSet.has(f.id)) continue;
            hitSet.add(f.id);
            hurt(f, p2 ? 6 : 5, b.e);
            const d = road.dirAt(s);
            push(f, add(scale(d, 0.7), v(0, 0.35, 0)));
          }
          if (s >= road.length) {
            emit(b.dim, "joan:burst", add(here, v(0, 1, 0)), { color: COLORS.white, size: 0.8 });
            removeQuietly(echo);
            return false;
          }
          return true;
        },
        cleanup: () => {
          marching--;
          removeQuietly(echo);
        },
      });
      yield 14;
    }
    // hold the standard until the procession has passed (bounded)
    for (let i = 0; i < 240 && marching > 0; i += 5) yield 5;
  } finally {
    for (const r of roads) b.field.retire(r, b.now, 10);
    for (const e of echoes) b.untrack(e);
  }
  b.anim("recover");
  yield 14;
  b.cooldown("procession", p2 ? 300 : 400);
}
