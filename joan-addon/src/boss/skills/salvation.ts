import { Entity, Player } from "@minecraft/server";
import { COLORS } from "../../config.js";
import { emit, ring, sigil, sound } from "../../core/fx.js";
import { foesNear, hurt, push } from "../../core/targets.js";
import { add, flatDir, hdist, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { bezier, circle, line } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";

/**
 * FALSE SALVATION - a closed loop of road (the halo of judgement) is drawn
 * around the player; its interior will be judged when the countdown ends.
 * The loop branches into three exit roads. Two are true and carry riders to
 * safety. One is false: its mark is an INVERTED lily and it bends back into the
 * loop (Phase II: it delivers the rider to Joan, who waits at its end).
 * Phase I: the loop is low - it can simply be jumped. Phase II: the loop is a
 * tall burning ring, the exits are the only way out.
 */
export function* falseSalvation(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  const c = { ...t.location };
  const R = p2 ? 6.0 : 6.5;
  b.face(c);
  b.anim("false_point");
  const countdown = Math.round((p2 ? 64 : 78) * (b.tel() / (p2 ? 12 : 18)));
  const life = b.tel() + countdown + 20;
  const ring0 = b.groundRoad(circle(c, R, 0, 1, true), {
    kind: "loop", loop: true, speed: 0.36, radius: 0.9, life, form: b.tel(), memory: false, crossings: false,
    band: p2 ? [-0.8, 2.6] : [-0.8, 0.75], restless: 0, switching: false, tag: "halo",
  });
  if (!ring0) {
    b.cooldown("salvation", 60);
    return;
  }
  // three exits, one of them false
  const base = Math.random() * Math.PI * 2;
  const falseIdx = Math.floor(Math.random() * 3);
  const exits: { path: Path; at: V3; isFalse: boolean }[] = [];
  for (let k = 0; k < 3; k++) {
    const a = base + (k * Math.PI * 2) / 3;
    const out = v(Math.cos(a), 0, Math.sin(a));
    const at = add(c, scale(out, R));
    const isFalse = k === falseIdx;
    let pts: V3[];
    if (!isFalse) {
      pts = line(at, add(c, scale(out, R + 9)));
    } else if (p2) {
      // the false road leads to Joan herself
      pts = bezier(at, add(at, scale(out, 4)), add(b.pos, scale(flatDir(b.pos, at), 4)), add(b.pos, scale(flatDir(b.pos, at), 1.4)), 30);
    } else {
      // the false road curls back into the loop
      const back = base + ((k + 0.5) * Math.PI * 2) / 3;
      const re = add(c, scale(v(Math.cos(back), 0, Math.sin(back)), R));
      pts = bezier(at, add(at, scale(out, 5)), add(re, scale(v(Math.cos(back), 0, Math.sin(back)), 5)), re, 30);
    }
    const ex = b.groundRoad(pts, {
      kind: isFalse ? "false" : "exit", speed: 0.5, radius: 0.85, life, form: b.tel(), memory: !isFalse, crossings: false,
      restless: 0, switching: false, falseRoad: isFalse, tag: "exit",
      onEnd: isFalse && p2 ? (e: Entity) => trap(b, e) : undefined,
    });
    if (!ex) continue;
    const sJ = ring0.nearest(at).s;
    b.field.junction(ring0, sJ, ex, 0);
    if (isFalse && !p2) b.field.link(ex, ring0); // the lie: it feeds you back into the halo
    exits.push({ path: ex, at, isFalse });
  }
  sound(b.dim, "joan.bell.toll", c, 1, p2 ? 0.9 : 1.05);
  yield b.tel();
  // countdown: the halo contracts visually, marks are refreshed so they can be read
  const steps = Math.ceil(countdown / 10);
  for (let i = 0; i < steps; i++) {
    const k = i / steps;
    ring(b.dim, c, R * (1 - k * 0.55), R * (1 - (k + 1 / steps) * 0.55), 0.5, p2 ? COLORS.burning : COLORS.roadGold);
    for (const ex of exits) {
      sigil(b.dim, add(ex.at, v(0, 0.1, 0)), 1.8, 0.55, ex.isFalse ? COLORS.false : COLORS.white, ex.isFalse);
    }
    if (i === steps - 2) sound(b.dim, "joan.bell.high", c, 1, 1.3);
    yield 10;
  }
  // JUDGEMENT of the interior
  b.anim("detour_release");
  emit(b.dim, "joan:pillar", c, { h: 9, color: p2 ? COLORS.burningGold : COLORS.white, life: 0.6, size: R * 0.6 });
  b.impactFx(c, R - 0.8, p2 ? COLORS.burningGold : COLORS.roadGold);
  for (const e of foesNear(b.dim, c, R)) {
    if (hdist(e.location, c) > R - 0.6 || Math.abs(e.location.y - c.y) > 3.5) continue;
    hurt(e, p2 ? 12 : 10, b.e);
    push(e, v(0, 0.75, 0));
  }
  b.field.retire(ring0, b.now, 6);
  for (const ex of exits) b.field.retire(ex.path, b.now, 30);
  yield 12;
  b.cooldown("salvation", p2 ? 190 : 250);
}

/** Phase II: the false road delivers its rider to Joan, who strikes on arrival. */
function trap(b: JoanBoss, e: Entity): void {
  if (!e.isValid || hdist(e.location, b.pos) > 4) return;
  b.later(2, () => {
    if (!e.isValid) return;
    b.face(e.location);
    b.anim("melee_sweep");
    b.later(7, () => b.cone(b.pos, flatDir(b.pos, e.location), 4, 70, 9));
  });
}
