import { Entity, Player } from "@minecraft/server";
import { COLORS, SERAPH } from "../../config.js";
import { emit, sound } from "../../core/fx.js";
import { fightersNear, foesNear, hurt, push } from "../../core/targets.js";
import { lineClear } from "../../core/terrain.js";
import { add, dist, flatDir, hdist, lerp, perpXZ, scale, v, V3 } from "../../core/vec.js";
import { Path } from "../../paths/path.js";
import { bezier, skyArc, tiltedRing } from "../../paths/shapes.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { removeQuietly, setProp, spawnMinion } from "../minions.js";

/**
 * HEAVEN'S DETOUR - Joan whirls the standard overhead and wraps herself in two
 * crossed orbit roads. Projectiles that enter an orbit are carried around her
 * and flung back at the nearest player; melee attackers are swept round and
 * thrown out. Meanwhile she releases Seraph Lights that FLY ALONG pre-drawn
 * detour roads which bend around cover (over walls when the line of sight is
 * blocked). The road is visible before the light leaves, so the landing spot
 * can be read and dodged. Phase II: each detour road splits into two branches
 * and every light divides at the fork.
 */
export function* heavensDetour(b: JoanBoss, t: Player): SkillGen {
  const p2 = b.phase >= 2;
  b.anim("detour_spin");
  sound(b.dim, "joan.choir.light", b.pos, 0.6, p2 ? 0.85 : 1.1);
  const c = add(b.pos, v(0, 1.3, 0));
  const duration = p2 ? 80 : 96;
  const orbits: Path[] = [];
  const aimBack = (e: Entity): V3 | undefined => {
    const ps = fightersNear(b.dim, e.location, 40).sort((a, z) => dist(a.location, e.location) - dist(z.location, e.location));
    return ps[0] ? add(ps[0].location, v(0, 1.2, 0)) : undefined;
  };
  for (const [tilt, yaw] of [[0, 0], [1.05, Math.random() * Math.PI]] as [number, number][]) {
    const o = b.field.add(tiltedRing(c, 2.9, tilt, yaw, tilt === 0), {
      kind: "orbit", owner: b.id, aerial: true, loop: true, speed: 0.55, radius: 1.15, form: 8, life: duration,
      maxRide: 12, fling: 1.6, aim: (e) => aimBack(e), carryPlayers: true, carryMobs: true, carryProjectiles: true,
      memory: false, burning: false, damage: 0, tag: "orbit",
      color: p2 ? COLORS.burningGold : COLORS.white, chevron: COLORS.roadGold,
    }, b.now);
    if (o) orbits.push(o);
  }
  const lights = p2 ? 5 : 3;
  const every = Math.floor((duration - 20) / lights);
  for (let i = 0; i < duration; i++) {
    if (i >= 12 && (i - 12) % every === 0 && Math.floor((i - 12) / every) < lights) {
      const targets = fightersNear(b.dim, b.home, 40);
      const victim = targets.length ? targets[Math.floor(Math.random() * targets.length)] : t;
      if (victim.isValid) launchSeraph(b, victim, p2);
    }
    if (i % 20 === 0) b.face(t.location);
    yield 1;
  }
  b.anim("detour_release");
  for (const o of orbits) b.field.retire(o, b.now, 4);
  yield 12;
  b.cooldown("detour", p2 ? 190 : 250);
}

/** Plan a detour road to the victim and send a Seraph Light along it. */
function launchSeraph(b: JoanBoss, victim: Player, split: boolean): void {
  const from = add(b.pos, v(0, 2.6, 0));
  const to = add(b.predict(victim, 22), v(0, 0.9, 0));
  const blocked = !lineClear(b.dim, from, add(to, v(0, 0.6, 0)));
  const side = perpXZ(flatDir(from, to));
  const bow = (Math.random() < 0.5 ? 1 : -1) * Math.min(6, 2 + hdist(from, to) * 0.25);
  let pts: V3[];
  if (blocked) pts = skyArc(from, to, 6);
  else {
    const mid = lerp(from, to, 0.5);
    pts = bezier(from, add(lerp(from, mid, 0.6), add(scale(side, bow), v(0, 2, 0))),
      add(lerp(mid, to, 0.4), add(scale(side, bow * 0.6), v(0, 1.5, 0))), to, 30);
  }
  const form = Math.max(14, b.tel(0.9));
  const road = b.field.add(pts, {
    kind: "arc", owner: b.id, aerial: true, speed: 0.6, radius: 0.9, form, life: form + 60, carryPlayers: false,
    carryMobs: false, carryProjectiles: true, memory: false, burning: false, damage: 0, tag: "detour",
    color: split ? COLORS.burningGold : COLORS.white, chevron: COLORS.roadGold,
  }, b.now);
  if (!road) return;
  const branches: Path[] = [];
  if (split) {
    // the fork: two branches leave the road at 60% and land left and right of the target
    const sFork = road.length * 0.6;
    const fork = road.pointAt(sFork);
    for (const k of [-1, 1]) {
      const land = add(to, scale(side, k * 3.2));
      const br = b.field.add(bezier(fork, add(fork, scale(road.dirAt(sFork), 2)), add(land, v(0, 2, 0)), land, 20), {
        kind: "arc", owner: b.id, aerial: true, speed: 0.6, radius: 0.9, form, life: form + 60, carryPlayers: false,
        carryMobs: false, carryProjectiles: true, memory: false, burning: false, damage: 0, tag: "detour",
        color: COLORS.burningGold, chevron: COLORS.burningGold,
      }, b.now);
      if (br) branches.push(br);
    }
  }
  b.markImpact(v(to.x, to.y - 0.9, to.z), 2.6, form + 30, split ? COLORS.burningGold : COLORS.roadGold);
  for (const br of branches) {
    const end = br.pointAt(br.length);
    b.markImpact(v(end.x, end.y - 0.9, end.z), 2.6, form + 30, COLORS.burningGold);
  }
  const startAt = b.now + form;
  const fly = (path: Path, s0: number, s1: number, fire: boolean, onFork?: () => void) => {
    let e: Entity | undefined;
    let s = s0;
    let forked = false;
    b.addTask({
      name: "seraph",
      step: (now) => {
        if (now < startAt) return true;
        if (!e) {
          e = b.track(spawnMinion(b.dim, SERAPH, path.pointAt(s0), b.id));
          if (!e) return false;
          setProp(e, "joan:fire", fire);
          sound(b.dim, "joan.seraph.fly", path.pointAt(s0), 0.8, 1);
        }
        if (!e.isValid) return false; // swatted out of the air by a player
        s += 0.62;
        const p = path.pointAt(Math.min(s, s1));
        try {
          e.teleport(p, { facingLocation: path.pointAt(Math.min(s + 1, s1)) });
        } catch {
          return false;
        }
        if (onFork && !forked && s >= path.length * 0.6) {
          forked = true;
          onFork();
          explode(b, e, p, 0, false);
          return false;
        }
        const close = foesNear(b.dim, p, 1.4);
        if (close.length || s >= s1) {
          explode(b, e, p, 4, fire);
          return false;
        }
        return true;
      },
      cleanup: () => removeQuietly(e),
    });
  };
  if (branches.length) {
    fly(road, 0, road.length, true, () => {
      for (const br of branches) {
        let child: Entity | undefined;
        let s = 0;
        b.addTask({
          name: "seraph-branch",
          step: () => {
            if (!child) {
              child = b.track(spawnMinion(b.dim, SERAPH, br.pointAt(0), b.id));
              if (!child) return false;
              setProp(child, "joan:fire", true);
            }
            if (!child.isValid) return false;
            s += 0.62;
            const p = br.pointAt(Math.min(s, br.length));
            try {
              child.teleport(p);
            } catch {
              return false;
            }
            if (foesNear(b.dim, p, 1.4).length || s >= br.length) {
              explode(b, child, p, 4, true);
              return false;
            }
            return true;
          },
          cleanup: () => removeQuietly(child),
        });
      }
    });
  } else fly(road, 0, road.length, false);
}

function explode(b: JoanBoss, e: Entity, p: V3, dmg: number, fire: boolean): void {
  emit(b.dim, "joan:burst", p, { color: fire ? COLORS.burningGold : COLORS.white, size: 0.9 });
  emit(b.dim, "joan:flash", p, { size: 1.6, life: 0.25, color: fire ? COLORS.burning : COLORS.white });
  if (dmg > 0) {
    sound(b.dim, "joan.seraph.burst", p, 1, 1);
    for (const f of foesNear(b.dim, p, 1.6)) {
      hurt(f, dmg, b.e);
      push(f, add(scale(flatDir(p, f.location), 0.4), v(0, 0.3, 0)));
    }
  }
  b.untrack(e);
}
