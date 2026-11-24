import { Entity, Player } from "@minecraft/server";
import { COLORS } from "../../config.js";
import { emit, sound } from "../../core/fx.js";
import { add, flatDir, hdist, perpXZ, scale, v } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { line } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { shockRing } from "./trail.js";

/**
 * ROAD OF ORLEANS - the siege road. Joan plants the standard and lays a broad
 * three-lane road through the player. It first marches OUTWARD (her flank is
 * shielded: arrows shot at her are carried away), then - after a red-gold
 * warning - the whole road REVERSES and drags everything back to the road's
 * head where she rips the standard free for the Siege Breaker.
 * Phase II: the centre lane runs against the side lanes and the lanes keep
 * swapping (restless), so the safe lane changes under the player's feet.
 * Arrows riding an inbound lane into her count as a Turned Road (double damage).
 */
export function* roadOfOrleans(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  b.face(t.location);
  const dir = flatDir(b.pos, t.location);
  const side = perpXZ(dir);
  const head = add(b.pos, scale(dir, 1.4));
  const length = Math.min(20, Math.max(12, hdist(b.pos, t.location) + 8));
  b.anim("orleans_plant");
  const outbound = p2 ? 30 : 34;
  const warn = p2 ? 12 : 16;
  const inbound = p2 ? 56 : 64;
  const life = outbound + warn + inbound + 20;
  const lanes: Path[] = [];
  let arrived = false;
  const offsets = [-1.35, 0, 1.35];
  offsets.forEach((off, i) => {
    const a = add(head, scale(side, off));
    const z = add(a, scale(dir, length));
    const lane = b.groundRoad(line(a, z), {
      kind: "road", speed: p2 ? 0.46 : 0.42, radius: 0.72, form: b.tel(1.1), life, tag: "orleans",
      restless: p2 ? 34 : 0,
      onEnd: (e: Entity) => {
        // something arrived at the road's head (inbound): the breaker triggers at once
        if (lane && lane.flow < 0 && e.id !== b.id) arrived = true;
      },
    });
    if (lane) {
      if (p2 && i === 1) lane.flow = -1; // centre lane against the others
      lanes.push(lane);
    }
  });
  if (!lanes.length) {
    b.cooldown("orleans", 80);
    return;
  }
  yield b.tel(1.1);
  b.anim("orleans_hold");
  sound(b.dim, "joan.bell.high", head, 0.8, 1.1);
  yield outbound;
  // everything turns back towards Joan
  for (const lane of lanes) b.field.reverse(lane, warn, b.now);
  sound(b.dim, "joan.bell.toll", head, 1, 1.2);
  yield warn;
  arrived = false;
  for (let i = 0; i < inbound && !arrived; i += 2) {
    if (i % 10 === 0) emit(b.dim, "joan:sigil", add(head, v(0, 0.05, 0)), { size: 5.5, life: 0.5, color: p2 ? COLORS.burningGold : COLORS.roadGold });
    yield 2;
  }
  // SIEGE BREAKER
  b.anim("orleans_breaker");
  b.markImpact(add(head, scale(dir, 1.5)), 6.6, 9, COLORS.warn);
  yield 9;
  const at = add(head, scale(dir, 1.5));
  b.strike(at, 3.3, p2 ? 13 : 11, 0.5, 0.85);
  b.impactFx(at, 3.3, p2 ? COLORS.burningGold : COLORS.roadGold);
  for (const lane of lanes) b.field.retire(lane, b.now, 8);
  yield* shockRing(b, at, 5, 3);
  yield 8;
  b.cooldown("orleans", p2 ? 180 : 230);
}
