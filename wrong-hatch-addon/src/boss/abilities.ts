/**
 * Every ability of The Wrong Hatch, implemented as a timeline (generator)
 * whose key frames come from the shared spec (tools/spec.py), so damage,
 * particles and sounds land exactly on the animation frames.
 *
 * Melee:   Peck / Peck Combo, Wing Guillotine (+ double), Back Scratch, Sickle Sweep
 * Area:    Broodquake (jumpable rings), Molt Storm, Molt Burst, Dawn Flash
 * Ranged:  Egg Mortar (hidden-outcome eggs), Feather Volley, Yolk Beam
 * Mobile:  Rooster Rush (wall stun), Wing Hop, Sky Drop
 * Defence: Shell Fortress (break it or eat the shrapnel)
 * Brood:   Rotten Hatch, Brood Call
 */
import { Player, Vector3 } from "@minecraft/server";
import { COOLDOWN, DMG, FORTRESS, RUSH_STUN } from "../config.js";
import { KEY } from "../generated/spec.js";
import { hit, horizontalWithin, viewersNear } from "../util/combat.js";
import { circle, line, particle, ring, shake, sound } from "../util/fx.js";
import { add, angleDelta, dirYaw, dist, dot, hdist, hnorm, mul, norm, rand, rotY, segDist, sub, v3, yawDir } from "../util/vec.js";
import type { Situation } from "./ai.js";
import { layEgg, spawnChick } from "./brood.js";
import type { BossController, Timeline } from "./controller.js";
import { addHazard, Dart, LobbedEgg, ShockRing } from "./hazards.js";

export interface Ability {
  id: string;
  name: string;
  phases: number[];
  /** 0 = unusable now; higher = more likely. */
  weight(c: BossController, s: Situation): number;
  run(c: BossController, s: Situation): Timeline;
}

// --------------------------------------------------------------------------- helpers

function* faceFor(c: BossController, target: Player, ticks: number, rate = 10): Timeline {
  for (let i = 0; i < ticks; i++) {
    if (target.isValid) c.face(target.location, rate);
    yield 1;
  }
}

/** Players inside a horizontal sector in front of (or around) the boss. */
function inArc(c: BossController, radius: number, halfAngle: number, centerYawOffset = 0): Player[] {
  const yaw = c.yaw() + centerYawOffset;
  return c.players(radius + 3).filter((p) => {
    if (!horizontalWithin(p.location, c.pos(), radius, 4.5)) return false;
    const a = Math.abs(angleDelta(yaw, dirYaw(sub(p.location, c.pos()))));
    return a <= halfAngle || hdist(p.location, c.pos()) < 2.2;
  });
}

function shakeNear(c: BossController, r: number, i: number, s: number): void {
  for (const p of viewersNear(c.dim(), c.pos(), r)) shake(p, i, s);
}

function finish(c: BossController): void {
  c.setAnim("none");
}

/** Push the boss along a direction with block checks (teleport based, deterministic). Returns false when blocked. */
function slide(c: BossController, dir: Vector3, step: number): boolean {
  const dim = c.dim();
  const pos = c.pos();
  for (const h of [0.6, 1.8, 3.0]) {
    try {
      const b = dim.getBlockFromRay(add(pos, v3(0, h, 0)), dir, { maxDistance: 1.6 + step, includePassableBlocks: false, includeLiquidBlocks: false });
      if (b) {
        if (h === 0.6) {
          // try to step up one block
          const up = dim.getBlockFromRay(add(pos, v3(0, 1.6, 0)), dir, { maxDistance: 1.6 + step, includePassableBlocks: false, includeLiquidBlocks: false });
          if (!up) {
            c.entity.teleport(add(pos, v3(dir.x * step, 1.0, dir.z * step)), { rotation: { x: 0, y: dirYaw(dir) } });
            return true;
          }
        }
        return false;
      }
    } catch {
      return false;
    }
  }
  let next = add(pos, v3(dir.x * step, 0, dir.z * step));
  try {
    const below = dim.getBlockFromRay(add(next, v3(0, 0.5, 0)), v3(0, -1, 0), { maxDistance: 1.6, includePassableBlocks: false, includeLiquidBlocks: true });
    if (!below) next = add(next, v3(0, -0.6, 0)); // walk off ledges, gravity does the rest
    c.entity.teleport(next, { rotation: { x: 0, y: dirYaw(dir) } });
  } catch {
    return false;
  }
  return true;
}

function airborne(c: BossController, on: boolean): void {
  if (!c.isBoss()) return;
  try {
    c.entity.triggerEvent(on ? "wh:airborne_on" : "wh:airborne_off");
  } catch {
    // ignore
  }
}

function landing(c: BossController, at: Vector3): Vector3 {
  try {
    const h = c.dim().getBlockFromRay(add(at, v3(0, 2, 0)), v3(0, -1, 0), { maxDistance: 40, includePassableBlocks: false, includeLiquidBlocks: true });
    if (h) return v3(at.x, h.block.location.y + 1, at.z);
  } catch {
    // ignore
  }
  return at;
}

// --------------------------------------------------------------------------- melee

const peck: Ability = {
  id: "peck",
  name: "Peck",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist < 6 && s.angle < 75 ? 10 : 0),
  *run(c, s) {
    c.cool("peck", COOLDOWN.peck);
    const combo = c.phase >= 2;
    try {
      c.setAnim(combo ? "peck_combo" : "peck");
      if (!combo) {
        yield* faceFor(c, s.target, KEY.peck.hit, 14);
        strikePeck(c, DMG.peck);
        yield 24 - KEY.peck.hit;
      } else {
        const hits = [KEY.peck_combo.hit1, KEY.peck_combo.hit2, KEY.peck_combo.hit3];
        let t = 0;
        for (let i = 0; i < 3; i++) {
          yield* faceFor(c, s.target, hits[i] - t, 16);
          t = hits[i];
          strikePeck(c, DMG.peckCombo[i]);
        }
        yield 44 - t;
      }
    } finally {
      finish(c);
    }
  },
};

function strikePeck(c: BossController, dmg: number): void {
  const tip = add(c.beak(), mul(c.forward(), 1.6));
  particle(c.dim(), "wh:shell_chip", add(tip, v3(0, -1.5, 0)));
  for (const p of inArc(c, 6.0, 40)) {
    if (segDist(add(p.location, v3(0, 1, 0)), c.chest(), add(tip, v3(0, -1.6, 0))) < 2.4 || hdist(p.location, c.pos()) < 3.4) {
      hit(c.entity, p, dmg, c.dmgMul(), { from: c.pos(), knock: 0.5, lift: 0.25 });
      particle(c.dim(), "wh:feather_burst", p.location);
    }
  }
}

const guillotine: Ability = {
  id: "guillotine",
  name: "Wing Guillotine",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist < 7.5 ? 6 + Math.min(2, s.near.length) : 0),
  *run(c, s) {
    c.cool("guillotine", COOLDOWN.guillotine);
    const double = c.phase >= 2;
    try {
      c.setAnim(double ? "guillotine_double" : "guillotine");
      const dim = c.dim();
      // wind-up: wings rise, a red arc warns where the blades will fall
      for (let t = 0; t < KEY.guillotine.hit; t++) {
        if (t < KEY.guillotine.hit - 4 && s.target.isValid) c.face(s.target.location, 9);
        if (t % 4 === 0) {
          const f = c.forward();
          for (let k = -5; k <= 5; k++) {
            const d = rotY(f, k * 18);
            particle(dim, "wh:warn_dot", add(c.pos(), v3(d.x * 6.5, 0.15, d.z * 6.5)));
          }
        }
        if (t % 5 === 0) particle(dim, "wh:feather_fall", add(c.center(), v3(0, 2, 0)));
        yield 1;
      }
      // the blades fall: front 200 degree arc
      for (const p of inArc(c, 7.2, 100)) hit(c.entity, p, DMG.guillotine, c.dmgMul(), { from: c.pos(), knock: 1.1, lift: 0.35 });
      bladeArc(c, 0, 100);
      shakeNear(c, 16, 0.35, 0.4);
      if (!double) {
        yield 36 - KEY.guillotine.hit;
        return;
      }
      // second swing: full spin catches anyone who dodged behind
      yield KEY.guillotine_double.hit2 - KEY.guillotine.hit;
      for (const p of inArc(c, 7.5, 180)) hit(c.entity, p, DMG.guillotineRear, c.dmgMul(), { from: c.pos(), knock: 1.3, lift: 0.4 });
      bladeArc(c, 0, 180);
      if (c.phase >= 3) {
        // phase III: the swing plants feather blades that burst a moment later
        const f = c.forward();
        const spots: Vector3[] = [];
        for (let k = 0; k < 6; k++) {
          const d = rotY(f, k * 60 + 30);
          spots.push(landing(c, add(c.pos(), v3(d.x * 5, 0, d.z * 5))));
        }
        for (let t = 0; t < 14; t++) {
          if (t % 3 === 0) for (const sp of spots) ring(dim, sp, 1.6, true);
          yield 1;
        }
        for (const sp of spots) {
          particle(dim, "wh:feather_burst", add(sp, v3(0, 0.5, 0)));
          for (const p of c.players(14)) if (dist(p.location, sp) < 1.9) hit(c.entity, p, 7, c.dmgMul(), { from: sp, knock: 0.5, lift: 0.6 });
        }
        sound(dim, "wrong_hatch.guillotine", c.center(), 1.4, 1.3);
        yield 4;
      } else {
        yield 52 - KEY.guillotine_double.hit2;
      }
    } finally {
      finish(c);
    }
  },
};

function bladeArc(c: BossController, offset: number, half: number): void {
  const f = rotY(c.forward(), offset);
  const n = Math.round(half / 12);
  for (let k = -n; k <= n; k++) {
    const d = rotY(f, k * 12);
    particle(c.dim(), "wh:feather_burst", add(c.pos(), v3(d.x * 5, 1.4, d.z * 5)));
  }
}

const backScratch: Ability = {
  id: "back_scratch",
  name: "Back Scratch",
  phases: [1, 2, 3],
  weight: (c, s) => (s.behind.length && c.behindTicks > 10 ? 9 + s.behind.length * 2 : 0),
  *run(c, s) {
    c.cool("back_scratch", COOLDOWN.back_scratch);
    try {
      c.setAnim("back_scratch");
      const dim = c.dim();
      for (let t = 0; t < 30; t++) {
        if (t === 10 || t === KEY.back_scratch.hit) {
          // gravel spray out of the rear 140 degree cone
          const back = rotY(c.forward(), 180);
          for (let k = -3; k <= 3; k++) {
            const d = rotY(back, k * 20);
            for (const r of [2.5, 4.5, 6.5, 8.5]) particle(dim, "wh:dust", add(c.pos(), v3(d.x * r, 0.6 + r * 0.08, d.z * r)));
          }
          sound(dim, "dig.gravel", c.pos(), 1.5, 0.7);
        }
        if (t === KEY.back_scratch.hit) {
          for (const p of inArc(c, 9, 70, 180)) {
            hit(c.entity, p, DMG.backScratch, c.dmgMul(), { from: c.pos(), knock: 0.9, lift: 0.3 });
            try {
              p.addEffect("blindness", 60, { amplifier: 0 });
              p.addEffect("slowness", 50, { amplifier: 1 });
            } catch {
              // ignore
            }
          }
        }
        yield 1;
      }
    } finally {
      finish(c);
    }
    void s;
  },
};

const sickleSweep: Ability = {
  id: "sickle_sweep",
  name: "Sickle Sweep",
  phases: [2, 3],
  weight: (c, s) => (s.behind.length && c.behindTicks > 24 ? 12 : s.near.length >= 3 ? 6 : 0),
  *run(c, s) {
    c.cool("sickle_sweep", COOLDOWN.sickle_sweep);
    try {
      c.setAnim("sickle_sweep");
      const dim = c.dim();
      for (let t = 0; t < 26; t++) {
        if (t < 10 && t % 3 === 0) ring(dim, c.pos(), 6.5, true);
        if (t === KEY.sickle_sweep.hit) {
          for (const p of c.players(8)) {
            if (horizontalWithin(p.location, c.pos(), 6.5, 4)) hit(c.entity, p, DMG.sickleSweep, c.dmgMul(), { from: c.pos(), knock: 1.5, lift: 0.5 });
          }
          circle(dim, c.pos(), 5, "wh:feather_burst", 10, 1.5);
          sound(dim, "wrong_hatch.guillotine", c.center(), 1.4, 0.8);
        }
        yield 1;
      }
    } finally {
      c.behindTicks = 0;
      finish(c);
    }
    void s;
  },
};

// --------------------------------------------------------------------------- area

const broodquake: Ability = {
  id: "broodquake",
  name: "Broodquake",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist < 11 ? 3.5 + Math.min(2, s.near.length) * 1.5 + (s.all.length >= 2 ? 1 : 0) : 0),
  *run(c, s) {
    c.cool("broodquake", COOLDOWN.broodquake);
    const slams = c.phase >= 3 ? 2 : 1;
    try {
      for (let n = 0; n < slams; n++) {
        c.setAnim("none");
        yield 2;
        c.setAnim("broodquake");
        const dim = c.dim();
        for (let t = 0; t < KEY.broodquake.slam; t++) {
          if (t % 4 === 0) {
            ring(dim, c.pos(), 4.5, true);
            particle(dim, "wh:shell_chip", c.pos());
          }
          if (t < 10 && s.target.isValid) c.face(s.target.location, 8);
          yield 1;
        }
        // SLAM
        const at = c.pos();
        particle(dim, "wh:dust", at);
        circle(dim, at, 3, "wh:dust", 14);
        particle(dim, "minecraft:smash_ground_particle_center", at);
        sound(dim, "random.explode", at, 1.5, 0.6);
        sound(dim, "mob.ravager.roar", at, 0.6, 1.6);
        shakeNear(c, 24, 0.6, 0.7);
        for (const p of c.players(6)) {
          if (horizontalWithin(p.location, at, 4.5, 3)) hit(c.entity, p, DMG.broodquakeSlam, c.dmgMul(), { from: at, knock: 1.0, lift: 0.6 });
        }
        // three expanding rings - jump over them
        for (let k = 0; k < 3; k++) {
          addHazard(new ShockRing(c.id, c.entity, dim, at, 4.5 - k * 1.8, 15, 0.5, DMG.broodquakeRing, c.dmgMul()));
        }
        yield 40 - KEY.broodquake.slam;
      }
    } finally {
      finish(c);
    }
  },
};

const moltStorm: Ability = {
  id: "molt_storm",
  name: "Molt Storm",
  phases: [3],
  weight: (c, s) => (s.all.length >= 1 && s.dist < 14 ? 6 + s.far.length : 0),
  *run(c, s) {
    c.cool("molt_storm", COOLDOWN.molt_storm);
    const dim = c.dim();
    try {
      c.setAnim("molt_storm");
      sound(dim, "mob.breeze.whirl", c.center(), 2, 0.6);
      c.announce("§eThe Wrong Hatch whips up a §lMOLT STORM§r§e - run!", undefined, true);
      for (let t = 0; t < 100; t++) {
        const at = c.pos();
        if (t % 2 === 0) {
          for (let k = 0; k < 4; k++) {
            const a = (t * 0.35 + k * Math.PI / 2) % (Math.PI * 2);
            const r = 1.5 + ((t * 0.3 + k * 2) % 10);
            particle(dim, "wh:feather_fall", add(at, v3(Math.sin(a) * r, 0.5 + (k % 3) * 1.4, Math.cos(a) * r)));
          }
        }
        if (t % 10 === 0) ring(dim, at, 3.5, true);
        for (const p of c.players(12)) {
          const d = hdist(p.location, at);
          if (t % 5 === 0 && d > 2.5) {
            const pull = hnorm(sub(at, p.location));
            try {
              p.applyKnockback({ x: pull.x * 0.38, z: pull.z * 0.38 }, 0.02);
            } catch {
              // ignore
            }
          }
          if (t % 10 === 0 && d < 3.5) hit(c.entity, p, DMG.moltStormTick, c.dmgMul(), {});
        }
        if (t % 20 === 0) sound(dim, "wrong_hatch.molt", at, 1.5, 0.8);
        yield 1;
      }
      // finale: outward blast
      particle(dim, "wh:feather_burst", c.center());
      particle(dim, "minecraft:wind_explosion_emitter", c.center());
      sound(dim, "breeze_wind_charge.burst", c.center(), 2, 0.7);
      for (const p of c.players(7)) {
        if (horizontalWithin(p.location, c.pos(), 6, 4)) hit(c.entity, p, DMG.moltStormEnd, c.dmgMul(), { from: c.pos(), knock: 1.8, lift: 0.6 });
      }
      yield 8;
    } finally {
      finish(c);
    }
    void s;
  },
};

const moltBurst: Ability = {
  id: "molt_burst",
  name: "Molt Burst",
  phases: [1, 2, 3],
  // reactive: punishes crowding / hugging the boss
  weight: (c, s) => (c.crowdTicks > 220 || s.near.filter((p) => hdist(p.location, c.pos()) < 4).length >= 3 ? 40 : 0),
  *run(c, s) {
    c.cool("molt_burst", COOLDOWN.molt_burst);
    try {
      c.setAnim("molt_burst");
      const dim = c.dim();
      for (let t = 0; t < 16; t++) {
        if (t < KEY.molt_burst.burst) particle(dim, "wh:feather_fall", add(c.center(), v3(rand(-2, 2), rand(-1, 2), rand(-2, 2))));
        if (t === KEY.molt_burst.burst) {
          particle(dim, "wh:feather_burst", c.center());
          particle(dim, "wh:feather_burst", add(c.center(), v3(0, -1.2, 0)));
          for (const p of c.players(6)) {
            if (horizontalWithin(p.location, c.pos(), 5, 4)) hit(c.entity, p, DMG.moltBurst, c.dmgMul(), { from: c.pos(), knock: 1.7, lift: 0.5 });
          }
        }
        yield 1;
      }
    } finally {
      c.crowdTicks = 0;
      finish(c);
    }
    void s;
  },
};

const dawnFlash: Ability = {
  id: "dawn_flash",
  name: "Dawn Flash",
  phases: [2, 3],
  weight: (c, s) => (s.all.length ? 4 + s.far.length * 2 : 0),
  *run(c, s) {
    c.cool("dawn_flash", COOLDOWN.dawn_flash);
    const dim = c.dim();
    try {
      c.setAnim("dawn_flash");
      c.announce("§6The golden core is blazing... §lLOOK AWAY!", undefined, true);
      for (let t = 0; t < 54; t++) {
        if (t === KEY.dawn_flash.pulse1 || t === KEY.dawn_flash.pulse2 || t === KEY.dawn_flash.pulse3) {
          particle(dim, "wh:gold_burst", c.chest());
          ring(dim, c.pos(), 3 + t / 10, false);
        }
        if (t % 3 === 0) particle(dim, "wh:gold_mote", add(c.chest(), v3(rand(-1, 1), rand(-1, 1), rand(-1, 1))));
        if (t === KEY.dawn_flash.flash) {
          particle(dim, "wh:flash", c.chest());
          sound(dim, "wrong_hatch.nova", c.center(), 1.6, 1.8);
          const core = c.chest();
          for (const p of c.players(32)) {
            const eye = p.getHeadLocation();
            const toCore = norm(sub(core, eye));
            const looking = dot(p.getViewDirection(), toCore) > 0.5;
            let visible = true;
            try {
              const b = dim.getBlockFromRay(eye, toCore, { maxDistance: Math.max(0.5, dist(eye, core) - 1), includePassableBlocks: false });
              visible = !b;
            } catch {
              visible = true;
            }
            if (looking && visible) {
              hit(c.entity, p, DMG.flash, c.dmgMul(), {});
              try {
                p.addEffect("blindness", 80, { amplifier: 0 });
                p.addEffect("slowness", 60, { amplifier: 1 });
                p.addEffect("weakness", 100, { amplifier: 0 });
                p.onScreenDisplay.setActionBar("§eYou were blinded by the Dawn Flash!");
              } catch {
                // ignore
              }
            } else {
              try {
                p.onScreenDisplay.setActionBar("§aYou averted your eyes.");
              } catch {
                // ignore
              }
            }
          }
        }
        yield 1;
      }
    } finally {
      finish(c);
    }
    void s;
  },
};

// --------------------------------------------------------------------------- ranged

const eggMortar: Ability = {
  id: "egg_mortar",
  name: "Egg Mortar",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist > 5 && s.dist < 30 ? 6 + s.far.length * 2 : s.all.length >= 2 ? 3 : 0),
  *run(c, s) {
    c.cool("egg_mortar", COOLDOWN.egg_mortar);
    const count = c.phase + 2;
    const keys = [KEY.egg_mortar.egg1, KEY.egg_mortar.egg2, KEY.egg_mortar.egg3, KEY.egg_mortar.egg4];
    try {
      c.setAnim("egg_mortar");
      let t = 0;
      const targets = s.all.length ? s.all : [s.target];
      for (let i = 0; i < count; i++) {
        const fire = keys[Math.min(i, keys.length - 1)] + Math.max(0, i - 3) * 4;
        yield* faceFor(c, s.target, fire - t, 6);
        t = fire;
        const victim = targets[i % targets.length];
        if (!victim.isValid) continue;
        // lead the target a little and scatter
        const v = victim.getVelocity();
        const aim = add(victim.location, v3(v.x * 18 + rand(-2.2, 2.2), 0, v.z * 18 + rand(-2.2, 2.2)));
        const land = landing(c, aim);
        const flight = Math.round(Math.min(34, Math.max(18, dist(c.chest(), land) * 1.4)));
        sound(c.dim(), "mob.chicken.plop", c.chest(), 2, 0.5);
        particle(c.dim(), "wh:gold_burst", c.chest());
        addHazard(new LobbedEgg(c.id, c.entity, c.dim(), c.chest(), land, flight, c.dmgMul(), (at) => {
          layEgg(c, at, c.now, "mortar", 50);
        }, 5 + flight / 6));
      }
      yield Math.max(1, 40 - t);
    } finally {
      finish(c);
    }
  },
};

const featherVolley: Ability = {
  id: "feather_volley",
  name: "Feather Volley",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist > 2.5 && s.dist < 32 ? 4 + s.far.length * 3 + (s.dist > 10 ? 4 : 0) : 0),
  *run(c, s) {
    c.cool("feather_volley", COOLDOWN.feather_volley);
    const dim = c.dim();
    try {
      c.setAnim("feather_volley");
      for (let t = 0; t < KEY.feather_volley.fire; t++) {
        if (s.target.isValid) c.face(s.target.location, 10);
        if (t % 3 === 0) particle(dim, "wh:feather_fall", add(c.center(), v3(rand(-2.5, 2.5), rand(-1, 2), rand(-2.5, 2.5))));
        if (t > 8 && t % 2 === 0 && s.target.isValid) line(dim, c.chest(), add(s.target.location, v3(0, 1, 0)), 2.2);
        yield 1;
      }
      const fans = c.phase >= 2 ? 2 : 1;
      for (let f = 0; f < fans; f++) {
        if (!s.target.isValid) break;
        const from = c.chest();
        const aim = norm(sub(add(s.target.location, v3(0, 1.0, 0)), from));
        for (let k = -2; k <= 2; k++) {
          const d = rotY(aim, k * 9 + (f ? 4.5 : 0));
          addHazard(new Dart(c.id, c.entity, dim, from, v3(d.x * Math.sqrt(1 - aim.y * aim.y), aim.y, d.z * Math.sqrt(1 - aim.y * aim.y)), 1.3, DMG.dart, c.dmgMul(), true));
        }
        sound(dim, "wrong_hatch.wing_whoosh", from, 1.5, 1.4);
        if (f + 1 < fans) yield* faceFor(c, s.target, 8, 12);
      }
      if (c.phase >= 3) {
        // radial burst
        const from = add(c.pos(), v3(0, 1.8, 0));
        for (let k = 0; k < 16; k++) {
          const d = yawDir(k * 22.5);
          addHazard(new Dart(c.id, c.entity, dim, add(from, mul(d, 2)), d, 1.0, DMG.dart, c.dmgMul(), true, 28));
        }
      }
      yield 32 - KEY.feather_volley.fire;
    } finally {
      finish(c);
    }
  },
};

const yolkBeam: Ability = {
  id: "yolk_beam",
  name: "Yolk Beam",
  phases: [2, 3],
  weight: (c, s) => (s.dist > 3 && s.dist < 24 ? 5 + s.far.length * 2 + (s.dist > 8 ? 2 : 0) : 0),
  *run(c, s) {
    c.cool("yolk_beam", COOLDOWN.yolk_beam);
    const dim = c.dim();
    let aimYaw = c.yaw();
    try {
      c.setAnim("beam_charge");
      for (let t = 0; t < 28; t++) {
        if (s.target.isValid) c.face(s.target.location, 8);
        aimYaw = c.yaw();
        if (t % 2 === 0) {
          particle(dim, "wh:gold_mote", add(c.chest(), v3(rand(-2, 2), rand(-1.5, 1.5), rand(-2, 2))));
          const d = yawDir(aimYaw);
          line(dim, c.chest(), add(c.chest(), mul(d, 14)), 1.6);
        }
        yield 1;
      }
      c.setAnim("beam_fire");
      sound(dim, "wrong_hatch.beam", c.chest(), 2, 1);
      const duration = c.phase >= 3 ? 64 : 50;
      const turn = c.phase >= 3 ? 2.6 : 2.2;
      const hitAt = new Map<string, number>();
      for (let t = 0; t < duration; t++) {
        if (s.target.isValid) {
          const want = dirYaw(sub(s.target.location, c.pos()));
          aimYaw += Math.max(-turn, Math.min(turn, angleDelta(aimYaw, want)));
          try {
            c.entity.setRotation({ x: 0, y: aimYaw });
          } catch {
            // ignore
          }
        }
        const origin = c.chest();
        const tgtY = s.target.isValid ? s.target.location.y + 1 : origin.y;
        const tgtD = s.target.isValid ? hdist(s.target.location, origin) : 10;
        const pitch = Math.max(-0.5, Math.min(0.3, (tgtY - origin.y) / Math.max(4, tgtD)));
        const dir = norm(add(yawDir(aimYaw), v3(0, pitch, 0)));
        let length = 24;
        try {
          const b = dim.getBlockFromRay(origin, dir, { maxDistance: 24, includePassableBlocks: false });
          if (b) length = Math.max(1, dist(origin, add(b.block.location, b.faceLocation)));
        } catch {
          // ignore
        }
        const end = add(origin, mul(dir, length));
        if (t % 2 === 0) {
          for (let k = 0; k < length; k += 0.9) particle(dim, "wh:beam", add(origin, mul(dir, k)));
          particle(dim, "wh:ember", end);
        }
        if (t % 20 === 0) sound(dim, "wrong_hatch.beam", origin, 1.5, 1);
        for (const p of c.players(26)) {
          if (segDist(add(p.location, v3(0, 0.9, 0)), origin, end) < 1.25 && c.now >= (hitAt.get(p.id) ?? 0)) {
            hitAt.set(p.id, c.now + 5);
            hit(c.entity, p, DMG.beamTick, c.dmgMul(), { fire: 3 });
          }
        }
        yield 1;
      }
    } finally {
      finish(c);
    }
  },
};

// --------------------------------------------------------------------------- mobility

function rushVictim(c: BossController, s: Situation): Player | undefined {
  return s.all.find((p) => {
    const d = hdist(p.location, c.pos());
    return d > 8 && d < 22 && p.isValid;
  });
}

const roosterRush: Ability = {
  id: "rooster_rush",
  name: "Rooster Rush",
  phases: [2, 3],
  // charges the target, or punishes a kiting player hanging back at mid range
  weight: (c, s) => (s.dist > 5 && s.dist < 24 ? 8 + s.far.length * 2 : rushVictim(c, s) ? 7 : 0),
  *run(c, s) {
    c.cool("rooster_rush", COOLDOWN.rooster_rush);
    const charges = c.phase >= 3 ? 2 : 1;
    const dim = c.dim();
    try {
      for (let n = 0; n < charges; n++) {
        const tgt = n === 0 ? (s.dist > 5 ? s.target : rushVictim(c, s) ?? s.target) : c.target() ?? s.target;
        if (!tgt || !tgt.isValid) break;
        c.setAnim("none");
        yield 2;
        c.setAnim("rush_windup");
        let dir = hnorm(sub(tgt.location, c.pos()));
        for (let t = 0; t < 30; t++) {
          if (t < 22 && tgt.isValid) {
            c.face(tgt.location, 10);
            dir = yawDir(c.yaw());
          }
          if (t % 3 === 0) {
            line(dim, add(c.pos(), v3(0, 0.2, 0)), add(c.pos(), v3(dir.x * 18, 0.2, dir.z * 18)), 1.5);
            particle(dim, "wh:dust", add(c.pos(), mul(dir, -2)));
          }
          yield 1;
        }
        c.setAnim("rush_charge");
        sound(dim, "mob.ravager.roar", c.center(), 1.5, 1.3);
        const hitIds = new Set<string>();
        let stunned = false;
        for (let t = 0; t < 26; t++) {
          if (!slide(c, dir, 0.78)) {
            stunned = true;
            break;
          }
          if (t % 2 === 0) particle(dim, "wh:dust", c.pos());
          for (const p of c.players(5)) {
            if (hitIds.has(p.id)) continue;
            if (hdist(p.location, add(c.pos(), mul(dir, 1.2))) < 2.6 && Math.abs(p.location.y - c.pos().y) < 4) {
              hitIds.add(p.id);
              const side = rotY(dir, Math.random() < 0.5 ? 70 : -70);
              hit(c.entity, p, DMG.rush, c.dmgMul(), {});
              try {
                p.applyKnockback({ x: (side.x + dir.x) * 1.4, z: (side.z + dir.z) * 1.4 }, 0.6);
              } catch {
                // ignore
              }
            }
          }
          yield 1;
        }
        if (stunned) {
          // smashed into a wall: dazed and vulnerable
          sound(dim, "random.explode", c.center(), 1.2, 0.8);
          sound(dim, "mob.ravager.stun", c.center(), 2, 0.9);
          particle(dim, "wh:shell_burst", add(c.center(), mul(dir, 2)));
          shakeNear(c, 20, 0.5, 0.5);
          c.setAnim("stunned");
          c.exposedUntil = c.now + RUSH_STUN.ticks;
          c.exposedMul = RUSH_STUN.mul;
          c.announce("§aThe Wrong Hatch is dazed!", undefined, true);
          for (let t = 0; t < RUSH_STUN.ticks; t++) {
            if (t % 6 === 0) particle(dim, "wh:stun_star", add(c.pos(), v3(Math.sin(t / 4) * 1.4, 5.3, Math.cos(t / 4) * 1.4)));
            yield 1;
          }
          break;
        }
        c.setAnim("none");
        yield 6;
      }
    } finally {
      finish(c);
    }
  },
};

const wingHop: Ability = {
  id: "wing_hop",
  name: "Wing Hop",
  phases: [1, 2, 3],
  weight: (c, s) => (s.dist > 9 && s.dist < 28 ? 9 : 0),
  *run(c, s) {
    c.cool("wing_hop", COOLDOWN.wing_hop);
    const dim = c.dim();
    try {
      c.setAnim("wing_hop");
      yield* faceFor(c, s.target, KEY.wing_hop.jump, 14);
      const to = s.target.isValid ? s.target.location : c.pos();
      const d = sub(to, c.pos());
      const hd = Math.min(12, Math.max(0, Math.sqrt(d.x * d.x + d.z * d.z) - 3));
      const dir = hnorm(d);
      const start = c.pos();
      const steps = KEY.wing_hop.land - KEY.wing_hop.jump;
      const end = landing(c, add(start, v3(dir.x * hd, 0, dir.z * hd)));
      airborne(c, true);
      for (let t = 1; t <= steps; t++) {
        const k = t / steps;
        const p = add(add(start, mul(sub(end, start), k)), v3(0, 4 * 3.2 * k * (1 - k), 0));
        let free = true;
        try {
          free = !dim.getBlockFromRay(add(c.pos(), v3(0, 1.5, 0)), norm(sub(p, c.pos())), { maxDistance: Math.max(0.2, dist(p, c.pos())) + 1.2, includePassableBlocks: false });
        } catch {
          free = true;
        }
        if (!free) break;
        try {
          c.entity.teleport(p, { rotation: { x: 0, y: dirYaw(dir) } });
        } catch {
          // ignore
        }
        if (t % 2 === 0) particle(dim, "wh:feather_fall", c.center());
        yield 1;
      }
      airborne(c, false);
      const at = c.pos();
      particle(dim, "wh:dust", at);
      circle(dim, at, 2.5, "wh:dust", 12);
      sound(dim, "wrong_hatch.step", at, 2, 0.6);
      for (const p of c.players(5)) if (horizontalWithin(p.location, at, 3.2, 3)) hit(c.entity, p, DMG.wingHopLand, c.dmgMul(), { from: at, knock: 0.9, lift: 0.4 });
      yield 24 - KEY.wing_hop.land;
    } finally {
      airborne(c, false);
      finish(c);
    }
  },
};

const skyDrop: Ability = {
  id: "sky_drop",
  name: "Sky Drop",
  phases: [3],
  weight: (c, s) => (s.dist > 4 ? 8 + s.far.length * 2 : 5),
  *run(c, s) {
    c.cool("sky_drop", COOLDOWN.sky_drop);
    const dim = c.dim();
    const start = c.pos();
    try {
      airborne(c, true);
      c.setAnim("sky_rise");
      // how high can we go?
      let height = 11;
      try {
        const b = dim.getBlockFromRay(add(start, v3(0, 5, 0)), v3(0, 1, 0), { maxDistance: 12, includePassableBlocks: false });
        if (b) height = Math.max(2, b.block.location.y - start.y - 5.5);
      } catch {
        // ignore
      }
      for (let t = 1; t <= 20; t++) {
        const k = t / 20;
        try {
          c.entity.teleport(add(start, v3(0, height * (1 - (1 - k) * (1 - k)), 0)));
        } catch {
          // ignore
        }
        if (t % 4 === 0) particle(dim, "wh:feather_fall", c.pos());
        yield 1;
      }
      c.setAnim("sky_hover");
      sound(dim, "wrong_hatch.flap", c.center(), 2, 0.9);
      const hoverY = c.pos().y;
      let mark = s.target.isValid ? landing(c, s.target.location) : landing(c, start);
      // track the victim with a marker for 1.5 s, then lock it
      for (let t = 0; t < 44; t++) {
        if (t < 30 && s.target.isValid) {
          const want = landing(c, s.target.location);
          mark = add(mark, mul(sub(want, mark), 0.25));
        }
        if (t % 3 === 0) {
          ring(dim, mark, 4.5, true);
          if (t >= 30) ring(dim, mark, 2.5, true);
        }
        const over = add(mark, v3(0, hoverY - mark.y, 0));
        const cur = c.pos();
        try {
          c.entity.teleport(add(cur, mul(sub(over, cur), 0.12)), { rotation: { x: 0, y: c.yaw() } });
        } catch {
          // ignore
        }
        if (t === 30) sound(dim, "wrong_hatch.crow", c.center(), 2, 0.7);
        yield 1;
      }
      c.setAnim("sky_dive");
      const top = c.pos();
      for (let t = 1; t <= 6; t++) {
        try {
          c.entity.teleport(add(top, mul(sub(mark, top), t / 6)));
        } catch {
          // ignore
        }
        particle(dim, "wh:gold_mote", c.center());
        yield 1;
      }
      airborne(c, false);
      c.setAnim("land_slam");
      const at = c.pos();
      particle(dim, "wh:dust", at);
      particle(dim, "minecraft:smash_ground_particle_center", at);
      particle(dim, "wh:shell_burst", add(at, v3(0, 1, 0)));
      circle(dim, at, 3.5, "wh:dust", 18);
      sound(dim, "random.explode", at, 2, 0.5);
      shakeNear(c, 32, 0.9, 1.0);
      for (const p of c.players(7)) if (horizontalWithin(p.location, at, 4.5, 4)) hit(c.entity, p, DMG.skyDrop, c.dmgMul(), { from: at, knock: 1.4, lift: 0.7 });
      addHazard(new ShockRing(c.id, c.entity, dim, at, 4.5, 12, 0.55, DMG.skyDropRing, c.dmgMul()));
      yield 20;
    } finally {
      airborne(c, false);
      finish(c);
    }
  },
};

// --------------------------------------------------------------------------- defence

const shellFortress: Ability = {
  id: "shell_fortress",
  name: "Shell Fortress",
  phases: [1, 2, 3],
  // reactive: triggered by burst damage (and occasionally on its own after phase I starts)
  weight: (c, s) => {
    const burst = s.recentDamage / Math.max(1, c.health()?.effectiveMax ?? 600);
    if (burst > 0.08) return 30;
    return c.hpFrac() < 0.9 ? 1 : 0;
  },
  *run(c, s) {
    c.cool("shell_fortress", COOLDOWN.shell_fortress);
    const dim = c.dim();
    try {
      c.setAnim("fortress_enter");
      sound(dim, "mob.shulker.close", c.center(), 2, 0.5);
      yield 16;
      c.setAnim("fortress_hold");
      c.fortress = { absorbed: 0, threshold: FORTRESS.breakPerScale * c.hpScale, broken: false };
      c.announce("§bShell Fortress! §fCrack it before it bursts!", undefined, true);
      let t = 0;
      for (; t < FORTRESS.duration; t++) {
        const f = c.fortress;
        if (!f) break;
        if (t % 4 === 0) ring(dim, c.pos(), 7, t > FORTRESS.duration - 40);
        if (t % 10 === 0) particle(dim, "wh:shell_chip", c.center());
        if (t % 20 === 0) {
          const pct = Math.min(100, Math.round((f.absorbed / f.threshold) * 100));
          c.announce(`§bShell integrity: §f${100 - pct}%`, undefined, true);
          sound(dim, "wrong_hatch.crack", c.center(), 1, 0.7 + pct / 120);
        }
        if (f.absorbed >= f.threshold) {
          f.broken = true;
          break;
        }
        yield 1;
      }
      const broke = !!c.fortress?.broken;
      c.fortress = null;
      if (broke) {
        sound(dim, "wrong_hatch.crack_big", c.center(), 3, 0.8);
        sound(dim, "mob.ravager.stun", c.center(), 2, 0.9);
        particle(dim, "wh:shell_burst", c.center());
        particle(dim, "wh:gold_burst", c.chest());
        c.announce("§a§lSHELL BROKEN! §fThe Wrong Hatch is exposed!", undefined, true);
        c.setAnim("stunned");
        c.exposedUntil = c.now + FORTRESS.exposedTicks;
        c.exposedMul = FORTRESS.exposedMul;
        for (let k = 0; k < FORTRESS.exposedTicks; k++) {
          if (k % 6 === 0) particle(dim, "wh:stun_star", add(c.pos(), v3(Math.sin(k / 4) * 1.4, 5.3, Math.cos(k / 4) * 1.4)));
          yield 1;
        }
      } else {
        c.setAnim("fortress_burst");
        yield KEY.fortress_burst.burst;
        particle(dim, "wh:shell_burst", c.center());
        particle(dim, "wh:shell_burst", add(c.center(), v3(0, -1, 0)));
        sound(dim, "wrong_hatch.crack_big", c.center(), 3, 1.1);
        sound(dim, "random.explode", c.center(), 1, 1.4);
        for (const p of c.players(8)) if (horizontalWithin(p.location, c.pos(), 7, 4)) hit(c.entity, p, DMG.fortressBurst, c.dmgMul(), { from: c.pos(), knock: 1.2, lift: 0.45 });
        c.healFraction(0.03);
        yield 20 - KEY.fortress_burst.burst;
      }
    } finally {
      c.fortress = null;
      finish(c);
    }
    void s;
  },
};

// --------------------------------------------------------------------------- brood

const rottenHatch: Ability = {
  id: "rotten_hatch",
  name: "Rotten Hatch",
  phases: [2, 3],
  weight: (c, s) => (s.all.length ? 5 + (s.near.length ? 2 : 0) : 0),
  *run(c, s) {
    c.cool("rotten_hatch", COOLDOWN.rotten_hatch);
    const n = c.phase >= 3 ? 5 : 4;
    const keys = [KEY.rotten_hatch.egg1, KEY.rotten_hatch.egg2, KEY.rotten_hatch.egg3, KEY.rotten_hatch.egg4];
    try {
      c.setAnim("rotten_hatch");
      let t = 0;
      const off = Math.random() * 360;
      for (let i = 0; i < n; i++) {
        const at = keys[Math.min(i, 3)] + Math.max(0, i - 3) * 4;
        yield Math.max(1, at - t);
        t = at;
        const d = yawDir(off + (i * 360) / n);
        const r = rand(5, 7.5);
        const spot = landing(c, add(c.pos(), v3(d.x * r, 0, d.z * r)));
        addHazard(new LobbedEgg(c.id, c.entity, c.dim(), add(c.pos(), v3(0, 2, 0)), spot, 12, c.dmgMul(), (p) => {
          layEgg(c, p, c.now, "rotten", 160);
        }, 3));
        sound(c.dim(), "mob.chicken.plop", c.pos(), 2, 0.4);
      }
      yield Math.max(1, 44 - t);
    } finally {
      finish(c);
    }
    void s;
  },
};

const broodCall: Ability = {
  id: "brood_call",
  name: "Brood Call",
  phases: [2, 3],
  weight: (c, s) => (s.chicks < 3 ? 6 + (3 - s.chicks) * 2 : s.chicks < c.chickCap() / 2 ? 3 : 0),
  *run(c, s) {
    c.cool("brood_call", COOLDOWN.brood_call);
    try {
      c.setAnim("brood_call");
      yield KEY.brood_call.spawn;
      const n = 3 + Math.max(0, c.hpScale - 1);
      for (let i = 0; i < n; i++) {
        const d = yawDir(Math.random() * 360);
        spawnChick(c, add(c.pos(), v3(d.x * 2.5, 0.2, d.z * 2.5)), c.phase >= 3 && i === 0);
      }
      particle(c.dim(), "wh:shell_burst", add(c.pos(), v3(0, 1, 0)));
      yield 36 - KEY.brood_call.spawn;
    } finally {
      finish(c);
    }
    void s;
  },
};

export const ABILITIES: Ability[] = [
  peck, guillotine, backScratch, sickleSweep,
  broodquake, moltStorm, moltBurst, dawnFlash,
  eggMortar, featherVolley, yolkBeam,
  roosterRush, wingHop, skyDrop,
  shellFortress, rottenHatch, broodCall,
];

export function abilityById(id: string): Ability | undefined {
  return ABILITIES.find((a) => a.id === id);
}
