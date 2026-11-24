import { Player } from "@minecraft/server";
import { COLORS } from "../../config.js";
import { swingArc } from "../../core/fx.js";
import { hurt, push } from "../../core/targets.js";
import { add, flatDir, hdist, norm, scale, sub, v, V3 } from "../../core/vec.js";
import type { JoanBoss, SkillGen } from "../joan.js";

/** Melee with the standard: every swing also writes a short current in its direction. */

type Move = "sweep" | "back" | "thrust" | "plant" | "wrap";

const left = (f: V3): V3 => v(f.z, 0, -f.x);

function arcPoints(c: V3, f: V3, r: number, fromDeg: number, toDeg: number): V3[] {
  const out: V3[] = [];
  const L = left(f);
  for (let i = 0; i <= 14; i++) {
    const a = ((fromDeg + ((toDeg - fromDeg) * i) / 14) * Math.PI) / 180;
    out.push(add(c, add(scale(f, Math.cos(a) * r), scale(L, Math.sin(a) * r))));
  }
  return out;
}

function* sweep(b: JoanBoss, t: Player, backhand: boolean): SkillGen {
  b.face(t.location);
  const f = flatDir(b.pos, t.location);
  b.anim(backhand ? "melee_backsweep" : "melee_sweep");
  yield 7;
  const L = left(f);
  const knock = backhand ? scale(L, -1) : L; // the forehand throws to her left, the backhand to her right
  b.cone(b.pos, f, 3.9, 78, backhand ? 6 : 7, knock);
  const from = backhand ? 75 : -75;
  const to = backhand ? -75 : 75;
  b.groundRoad(arcPoints(b.pos, f, 2.7, from, to), { kind: "spoke", form: 2, life: 34, speed: 0.4, memory: false,
    burning: false, crossings: false, damage: 0 });
  const yaw0 = Math.atan2(f.z, f.x);
  swingArc(b.dim, b.pos, 2.6, yaw0 + (backhand ? 1.3 : -1.3), yaw0 + (backhand ? -1.3 : 1.3), 1.5,
    b.phase >= 2 ? COLORS.burningGold : COLORS.roadGold);
  yield 9;
}

function* thrust(b: JoanBoss, t: Player): SkillGen {
  b.face(t.location);
  const f = flatDir(b.pos, t.location);
  b.anim("melee_thrust");
  yield 9;
  const a = add(b.pos, v(0, 1.2, 0));
  b.lineHit(a, add(a, scale(f, 4.8)), 1.0, 8);
  b.groundRoad([add(b.pos, scale(f, 1)), add(b.pos, scale(f, 7.5))], { kind: "spoke", form: 2, life: 40, speed: 0.5,
    memory: false, burning: false, crossings: false, damage: 0 });
  swingArc(b.dim, b.pos, 3.2, Math.atan2(f.z, f.x) - 0.1, Math.atan2(f.z, f.x) + 0.1, 1.2, COLORS.white);
  yield 8;
}

function* plant(b: JoanBoss, t: Player): SkillGen {
  b.face(t.location);
  const f = flatDir(b.pos, t.location);
  const at = add(b.pos, scale(f, 1.6));
  b.anim("melee_plant");
  b.markImpact(at, 6.2, 10);
  yield 10;
  b.strike(at, 3.0, 9, 0.8, 0.45);
  b.impactFx(at, 3.0);
  for (let k = 0; k < 6; k++) {
    const ang = (k / 6) * Math.PI * 2 + Math.atan2(f.z, f.x);
    const d = v(Math.cos(ang), 0, Math.sin(ang));
    b.groundRoad([add(at, scale(d, 0.8)), add(at, scale(d, 4.6))], { kind: "spoke", form: 1, life: 26, speed: 0.48,
      memory: false, burning: false, crossings: false, damage: 0 });
  }
  yield 12;
}

/** Phase II: the cloth whips out, snares and throws the player onto the nearest road. */
function* wrap(b: JoanBoss, t: Player): SkillGen {
  b.face(t.location);
  const f = flatDir(b.pos, t.location);
  b.anim("melee_wrap");
  yield 10;
  const hit = b.cone(b.pos, f, 4.2, 32, 5, f);
  for (const e of hit) {
    // nearest point of any active ground road
    let best: V3 | undefined;
    let bd = 12;
    for (const p of b.field.activePaths()) {
      if (p.o.aerial || p.o.kind === "ring") continue;
      const n = p.nearest(e.location);
      if (n.d < bd) {
        bd = n.d;
        best = n.c;
      }
    }
    const dest = best ?? add(e.location, scale(f, 6));
    const d = sub(dest, e.location);
    const h = Math.min(1.4, hdist(dest, e.location) * 0.16);
    const dir = norm(v(d.x, 0, d.z));
    push(e, v(dir.x * h, 0.6, dir.z * h));
    hurt(e, 1, b.e);
  }
  yield 14;
}

export function* melee(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  const d0 = hdist(b.pos, t.location);
  let chain: Move[];
  const roads = b.field.activePaths().some((p) => !p.o.aerial && p.o.kind !== "spoke" && p.o.kind !== "ring");
  if (p2 && roads && Math.random() < 0.4) chain = ["wrap", "thrust"];
  else if (d0 > 3.3) chain = ["thrust", "plant"];
  else chain = p2 ? ["sweep", "back", "thrust"] : ["sweep", "back", "plant"];
  for (let i = 0; i < chain.length; i++) {
    if (!t.isValid) break;
    const d = hdist(b.pos, t.location);
    if (i > 0 && d > 5.5) {
      if (d > 7) b.brain.queueCombo("surge", "the target slipped out of the combo", 30);
      break;
    }
    const m = chain[i];
    if (m === "sweep") yield* sweep(b, t, false);
    else if (m === "back") yield* sweep(b, t, true);
    else if (m === "thrust") yield* thrust(b, t);
    else if (m === "plant") yield* plant(b, t);
    else yield* wrap(b, t);
  }
  b.cooldown("melee", p2 ? 26 : 34);
  b.gcdUntil = b.now + (p2 ? 10 : 16);
}
