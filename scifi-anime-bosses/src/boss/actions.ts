import { CameraShakeType, EntityDamageCause, Player } from "@minecraft/server";
import { CFG } from "../config.js";
import { ENT } from "../generated/ids.js";
import { COLORS, lineTelegraph, particle, ringTelegraph, shockwave, sound } from "../util/fx.js";
import {
  add, dist, distToSegment, flat, hdist, lerp, mul, norm, pitchOf, rand, sub, V3, yawOf,
} from "../util/vec.js";
import { chest, Cover, groundY, hasLineOfSight, hurt, knock, setProp } from "../util/world.js";
import type { Step, Vesper } from "./controller.js";
import { Drone, Expire, Plate, Scorch, Strike, Wave, Well } from "./minions.js";

// ------------------------------------------------------------------------------------------ helpers

function hold(v: Vesper, alt: number, face?: V3, speed = 0.18, turn?: number): void {
  const p = v.pos;
  v.goal.pos = { x: p.x, y: -1, z: p.z };
  v.goal.alt = alt;
  v.goal.face = face;
  v.goal.speed = speed;
  if (turn !== undefined) v.goal.turn = turn;
}

function predict(p: Player, ticks: number): V3 {
  let vel = { x: 0, y: 0, z: 0 };
  try {
    vel = p.getVelocity();
  } catch {
    /* ignore */
  }
  return { x: p.location.x + vel.x * ticks, y: p.location.y, z: p.location.z + vel.z * ticks };
}

function onGround(v: Vesper, p: V3): V3 {
  return { x: p.x, y: groundY(v.dim, p.x, p.z, p.y, p.y + 3), z: p.z };
}

function actionBar(v: Vesper, text: string): void {
  for (const p of v.players) {
    try {
      p.onScreenDisplay.setActionBar(text);
    } catch {
      /* ignore */
    }
  }
}

// ======================================================================================= PHASE I

/** Litany Lance: the rings assemble into a barrel; a sweeping reactor beam, blocked by cover. */
function* lance(v: Vesper, tgt: Player): Step {
  const c = CFG.lance;
  v.setAct("lance_charge");
  hold(v, CFG.altitudeP1 + 1, tgt.location, 0.12, 3.0);
  sound(v.dim, "lance_charge", v.prow(), 2.0);
  // sweep path across the target, perpendicular to the line of fire
  const from = v.prow();
  const tp = onGround(v, tgt.location);
  const fwd = flat(sub(tp, from));
  const right = { x: -fwd.z, y: 0, z: fwd.x };
  const side = Math.random() < 0.5 ? 1 : -1;
  const half = Math.min(9, Math.max(5, hdist(tp, from) * Math.tan((c.sweepDeg * Math.PI) / 360)));
  const S = onGround(v, add(tp, mul(right, -half * side)));
  const E = onGround(v, add(tp, mul(right, half * side)));
  lineTelegraph(v.dim, S, norm(sub(E, S)), dist(S, E), (c.charge + c.fire) / 20, COLORS.red);
  ringTelegraph(v.dim, S, 1.6, c.charge / 20, COLORS.red, false);
  for (let i = 0; i < c.charge; i++) {
    v.charge = (i + 1) / c.charge;
    v.goal.face = S;
    yield 1;
  }
  v.setAct("lance_fire");
  sound(v.dim, "lance_fire", v.prow(), 2.5);
  let beam;
  try {
    beam = v.dim.spawnEntity(ENT.lance, v.prow());
    beam.setDynamicProperty("sab:owner", v.id);
    v.beamId = beam.id;
  } catch {
    beam = undefined;
  }
  const lastHit = new Map<string, number>();
  try {
    for (let i = 0; i < c.fire; i++) {
      const aim = lerp(S, E, i / (c.fire - 1));
      const origin = v.prow();
      const dir = norm(sub(aim, origin));
      let end = add(origin, mul(dir, c.range));
      let grounded = false;
      try {
        const hit = v.dim.getBlockFromRay(origin, dir, { maxDistance: c.range, includeLiquidBlocks: true, includePassableBlocks: false });
        if (hit) {
          end = add(hit.block.location, hit.faceLocation);
          grounded = true;
        }
      } catch {
        /* ignore */
      }
      const L = dist(origin, end);
      v.goal.face = aim;
      if (beam && beam.isValid) {
        try {
          beam.teleport(origin, { keepVelocity: false });
        } catch {
          /* ignore */
        }
        setProp(beam, "sab:heading", Math.round(yawOf(dir) * 10) / 10);
        setProp(beam, "sab:pitch", Math.round(pitchOf(dir) * 10) / 10);
        setProp(beam, "sab:len", Math.min(64, Math.round(L * 10) / 10));
        setProp(beam, "sab:power", 1);
      }
      if (i % 2 === 0) particle(v.dim, "beam_impact", end);
      if (grounded && i % 6 === 0) v.addMinion(new Scorch(v, end));
      for (const p of v.players) {
        const last = lastHit.get(p.id) ?? -99;
        if (i - last < c.hitEvery) continue;
        if (distToSegment(chest(p), origin, end) < c.radius) {
          lastHit.set(p.id, i);
          hurt(p, c.damage, v.boss);
          try {
            p.setOnFire(c.burn, true);
          } catch {
            /* ignore */
          }
        }
      }
      yield 1;
    }
  } finally {
    if (beam && beam.isValid) {
      // let the beam fade (power is smoothed client-side) before removing it
      setProp(beam, "sab:power", 0);
      v.addMinion(new Expire(beam, 8));
    }
    v.beamId = undefined;
    v.charge = 0;
  }
  yield 20;
}

/** Halo Rite: rings fall as jump-rope shockwaves: low (jump) - high (stay down) - low (jump). */
function* rite(v: Vesper): Step {
  const c = CFG.rite;
  const centre = centroid(v);
  v.goal.pos = { x: centre.x, y: -1, z: centre.z };
  v.goal.alt = 9;
  v.goal.speed = 0.4;
  for (let i = 0; i < 40 && hdist(v.pos, centre) > 4; i++) yield 1;
  hold(v, 9);
  v.setAct("rite");
  const plan: [number, boolean][] = [[c.waves[0], false], [c.waves[1], true], [c.waves[2], false]];
  let t = 0;
  for (const [at, high] of plan) {
    const g = v.groundPoint();
    ringTelegraph(v.dim, g, 2.5, 0.5, high ? COLORS.cyan : COLORS.gold, false);
    while (t < at) {
      yield 1;
      t++;
    }
    const origin = v.groundPoint();
    sound(v.dim, high ? "bell_high" : "bell_low", origin, 2.2);
    v.addMinion(new Wave(v, origin, high, c.speed * (v.enraged ? 1.15 : 1), c.maxRadius, c.damage,
      high ? COLORS.cyan : COLORS.gold));
    if (!high) actionBar(v, "§6Low halo — §fJUMP!");
    else actionBar(v, "§bHigh halo — §fstay on the ground!");
  }
  yield 30;
}

/** Event Horizon: a singularity on the target's predicted position. */
function* horizon(v: Vesper, targets: Player[], radius = CFG.horizon.radius): Step {
  v.setAct("horizon");
  hold(v, v.phase >= 2 ? CFG.altitudeP2 + 2 : CFG.altitudeP1, targets[0]?.location, 0.15);
  for (const p of targets) v.addMinion(new Well(v, onGround(v, predict(p, 12)), radius));
  yield 48;
}

/** Choir of Satellites: drones launch from the dorsal spires. */
function* choir(v: Vesper): Step {
  v.setAct("choir");
  hold(v, CFG.altitudeP1 + 2, undefined, 0.12);
  sound(v.dim, "choir", v.pos, 1.5, 1.2);
  yield 18;
  const n = Math.min(5, CFG.choir.drones + Math.floor(Math.max(0, v.players.length - 1) / 2));
  sound(v.dim, "drone_launch", v.pos, 1.5);
  for (let i = 0; i < n; i++) {
    const tip = v.at(0, 190, -50 + i * 24);
    v.addMinion(new Drone(v, tip, i));
  }
  yield 22;
}

/** Genuflection: the vessel kneels and vents; its heart is exposed, then a vent burst. */
function* genuflect(v: Vesper): Step {
  const c = CFG.genuflect;
  v.setAct("genuflect");
  hold(v, 1.6, undefined, 0.26, 1.0);
  yield c.descend;
  v.openHeart(CFG.heartMult, 10, CFG.windowCap.genuflect);
  sound(v.dim, "vent", v.core(), 1.6);
  actionBar(v, "§dThe reactor heart is exposed — §fstrike it!");
  const window = Math.round(c.window * (v.players.length > 2 ? 0.85 : 1));
  for (let i = 0; i < window; i++) {
    if (v.heartSated()) break;
    if (i % 20 === 0) particle(v.dim, "heart_sparks", v.core());
    yield 1;
  }
  v.setAct("vent_flare");
  sound(v.dim, "vent", v.core(), 2.0, 1.3);
  ringTelegraph(v.dim, v.groundPoint(), c.burstRadius, c.flare / 20, COLORS.orange);
  yield c.flare;
  const g = v.groundPoint();
  particle(v.dim, "vent_burst", v.core());
  particle(v.dim, "vent_burst", add(g, { x: 0, y: 0.5, z: 0 }));
  shockwave(v.dim, add(g, { x: 0, y: 0.4, z: 0 }), 12, 0.6, COLORS.orange);
  sound(v.dim, "vent_burst", g, 2.0);
  for (const p of v.players) {
    if (hdist(p.location, g) < c.burstRadius && p.location.y - g.y < 7) {
      hurt(p, c.burstDamage, v.boss, EntityDamageCause.fire);
      knock(p, g, 1.2, 0.5);
      try {
        p.setOnFire(2, true);
      } catch {
        /* ignore */
      }
    }
  }
  v.closeHeart();
  v.setAct("idle");
  hold(v, CFG.altitudeP1, undefined, 0.2);
  yield 20;
}

// ====================================================================================== PHASE II

/** Predator Lunge: coil, lock a path, dash through it, then anchor (heart exposed). */
function* lunge(v: Vesper, tgt: Player): Step {
  const c = CFG.lunge;
  v.setAct("lunge_windup");
  hold(v, CFG.altitudeP2, tgt.location, 0.05, 9);
  sound(v.dim, "roar", v.pos, 1.6, 1.25);
  let dir = flat(sub(tgt.location, v.pos));
  const pathLen = c.speed * c.dash * (v.enraged ? 1.2 : 1) + 4;
  lineTelegraph(v.dim, v.groundPoint(), dir, pathLen, c.lockAt / 20, COLORS.magenta);
  for (let i = 0; i < c.windup; i++) {
    if (i < c.lockAt && tgt.isValid) {
      dir = flat(sub(tgt.location, v.pos));
      v.goal.face = tgt.location;
    }
    if (i === c.lockAt) {
      lineTelegraph(v.dim, v.groundPoint(), dir, pathLen, (c.windup - c.lockAt) / 20, COLORS.red);
      v.goal.face = add(v.pos, mul(dir, 20));
    }
    yield 1;
  }
  v.setAct("lunge");
  sound(v.dim, "lunge", v.pos, 2.0);
  const speed = c.speed * (v.enraged ? 1.2 : 1);
  const hit = new Set<string>();
  const start = v.pos;
  v.goal.speed = speed;
  v.goal.accel = 0.6;
  v.goal.turn = 0;
  for (let i = 0; i < c.dash; i++) {
    const p = add(start, mul(dir, speed * (i + 4)));
    v.goal.pos = { x: p.x, y: -1, z: p.z };
    v.goal.alt = CFG.altitudeP2 - 0.5;
    const body = v.at(0, 40, -20);
    for (const pl of v.players) {
      if (hit.has(pl.id)) continue;
      if (hdist(pl.location, body) < c.radius && pl.location.y > body.y - 5 && pl.location.y < body.y + 4) {
        hit.add(pl.id);
        hurt(pl, c.damage, v.boss);
        const side = { x: -dir.z, y: 0, z: dir.x };
        const s = Math.sign((pl.location.x - body.x) * side.x + (pl.location.z - body.z) * side.z) || 1;
        knock(pl, sub(pl.location, add(mul(side, s), mul(dir, 1))), 2.0, 0.6);
      }
    }
    yield 1;
  }
  v.setAct("anchored");
  hold(v, 2.4, undefined, 0.3, 0);
  v.goal.accel = 0.06;
  const g = v.groundPoint();
  sound(v.dim, "talon", g, 2.0, 0.7);
  particle(v.dim, "dust", g);
  shockwave(v.dim, add(g, { x: 0, y: 0.3, z: 0 }), 9, 0.5, COLORS.violet);
  yield 8;
  v.openHeart(CFG.heartMult, 42, CFG.windowCap.anchored);
  actionBar(v, "§dVESPER-0 is anchored — §fits heart is exposed!");
  for (let i = 0; i < c.anchored; i++) {
    if (v.heartSated()) break;
    if (i % 20 === 0) particle(v.dim, "heart_sparks", v.core());
    yield 1;
  }
  v.closeHeart();
  v.setAct("idle");
  hold(v, CFG.altitudeP2, undefined, 0.3);
  yield 12;
}

/** Reaping Talons: limbs strike predicted positions in sequence. */
function* talons(v: Vesper): Step {
  const c = CFG.talons;
  v.setAct("talons");
  const n = Math.min(8, c.strikes + Math.max(0, v.players.length - 1));
  let k = 0;
  for (let i = 0; i < n; i++) {
    const pool = v.players.filter((p) => hdist(p.location, v.pos) < 18);
    const tgt = pool.length ? pool[k++ % pool.length] : v.target;
    if (tgt && tgt.isValid) {
      const to = flat(sub(tgt.location, v.pos));
      v.goal.pos = { x: tgt.location.x - to.x * 6, y: -1, z: tgt.location.z - to.z * 6 };
      v.goal.alt = CFG.altitudeP2;
      v.goal.face = tgt.location;
      v.goal.speed = 0.4;
      v.addMinion(new Strike(v, onGround(v, predict(tgt, 16)), c.warn, c.radius, c.damage));
    }
    yield c.interval;
  }
  yield c.warn + 6;
}

/** Black Sun Nova: everything with line of sight to the core is struck; plates and blocks are cover. */
function* nova(v: Vesper): Step {
  const c = CFG.nova;
  v.setAct("nova_charge");
  v.goal.pos = { x: v.arena.x + rand(-4, 4), y: -1, z: v.arena.z + rand(-4, 4) };
  v.goal.alt = 9;
  v.goal.speed = 0.35;
  sound(v.dim, "nova_charge", v.pos, 2.5);
  for (const p of v.players) {
    try {
      p.onScreenDisplay.setTitle("§5THE BLACK SUN SWELLS", { fadeInDuration: 4, stayDuration: 30, fadeOutDuration: 10,
        subtitle: "§fbreak line of sight — hide behind the fallen plates" });
    } catch {
      /* ignore */
    }
  }
  for (let i = 0; i < c.charge; i++) {
    v.charge = (i + 1) / c.charge;
    if (i % 15 === 0) {
      particle(v.dim, "nova_gather", v.core());
      for (const p of v.players) {
        try {
          p.camera.addShake({ type: CameraShakeType.Rotational, intensity: 0.05 + 0.25 * v.charge, duration: 0.8 });
        } catch {
          /* ignore */
        }
      }
    }
    yield 1;
  }
  v.setAct("nova_release");
  v.charge = 0;
  const core = v.core();
  particle(v.dim, "nova_blast", core);
  shockwave(v.dim, core, 22, 1.4, COLORS.violet);
  sound(v.dim, "nova", core, 3.0);
  const plates = v.minions.of<Plate>("plate").filter((p) => p.entity?.isValid && p.landed);
  const covers = plates.map((p) => p.cover());
  const cracked = new Set<number>();
  for (const p of v.players) {
    if (dist(p.location, core) > c.range) continue;
    const onCover = (cv: Cover) => {
      const idx = covers.indexOf(cv);
      if (idx >= 0) cracked.add(idx);
    };
    const visible = hasLineOfSight(v.dim, core, p.getHeadLocation(), covers, onCover) ||
      hasLineOfSight(v.dim, core, chest(p), covers, onCover);
    if (visible) {
      hurt(p, c.damage, v.boss, EntityDamageCause.entityExplosion);
      knock(p, core, 1.1, 0.4);
      try {
        p.addEffect("darkness", 60, { amplifier: 0, showParticles: false });
        p.camera.addShake({ type: CameraShakeType.Positional, intensity: 0.6, duration: 0.6 });
      } catch {
        /* ignore */
      }
    } else {
      try {
        p.onScreenDisplay.setActionBar("§7The black sun's light breaks against your cover.");
      } catch {
        /* ignore */
      }
    }
  }
  for (const idx of cracked) plates[idx]?.crack();
  yield 24;
}

/** Roar: phase II intimidation; a violent shockwave pushes everyone back. */
function* roar(v: Vesper): Step {
  v.setAct("roar");
  hold(v, CFG.altitudeP2 + 1, v.target?.location, 0.1);
  yield 7;
  sound(v.dim, "roar", v.pos, 2.5, 0.9);
  const g = v.groundPoint();
  shockwave(v.dim, add(g, { x: 0, y: 0.4, z: 0 }), 16, 0.9, COLORS.violet);
  for (const p of v.players) {
    if (hdist(p.location, g) < 12) {
      knock(p, g, 1.4, 0.45);
      hurt(p, 4, v.boss);
    }
  }
  yield 33;
}

// ===================================================================================== choosers

type Option = { name: string; weight: number; run: () => void };

/**
 * Weighted pick with a shuffle-bag: while some ability has not been shown yet this phase, only those are
 * candidates (the whole repertoire appears early in each phase); after that, the last two picks are damped so
 * no pattern loops. Situational weights (range, clustering, live drones) apply throughout.
 */
function choose(v: Vesper, opts: Option[]): (() => void) | undefined {
  let avail = opts.filter((o) => o.weight > 0 && v.ready(o.name));
  if (!avail.length) return undefined;
  const fresh = avail.filter((o) => !v.seen.has(o.name));
  if (fresh.length) avail = fresh;
  const h = v.history;
  for (const o of avail) {
    const at = h.lastIndexOf(o.name);
    if (at >= 0 && at === h.length - 1) o.weight *= 0.2;
    else if (at >= 0 && at === h.length - 2) o.weight *= 0.55;
  }
  let total = avail.reduce((s, o) => s + o.weight, 0);
  let r = Math.random() * total;
  for (const o of avail) {
    r -= o.weight;
    if (r <= 0) return o.run;
  }
  return avail[avail.length - 1].run;
}

function centroid(v: Vesper): V3 {
  if (!v.players.length) return v.arena;
  let x = 0;
  let z = 0;
  for (const p of v.players) {
    x += p.location.x;
    z += p.location.z;
  }
  return { x: x / v.players.length, y: v.arena.y, z: z / v.players.length };
}

const cd = (v: Vesper, n: number) => Math.round(n * (v.enraged ? 0.75 : 1));

export function chooseP1(v: Vesper): (() => void) | undefined {
  const tgt = v.target;
  if (!tgt) return undefined;
  const far = dist(tgt.location, v.pos) > 12;
  const cluster = v.players.filter((p) => hdist(p.location, v.pos) < 22).length;
  const drones = v.minions.of<Drone>("drone").length;
  if (v.t - v.lastVulnerable > CFG.genuflect.forceAfter && v.ready("genuflect")) {
    return () => v.start("genuflect", genuflect(v), { cooldown: 400, cleanup: () => v.closeHeart() });
  }
  return choose(v, [
    { name: "lance", weight: 2.6 + (far ? 1 : 0), run: () => v.start("lance", lance(v, v.pickTarget((p) => dist(p.location, v.pos) * 0.15) ?? tgt), { cooldown: cd(v, CFG.lance.cooldown) }) },
    { name: "rite", weight: 2.4 + (cluster >= 2 ? 1.2 : 0), run: () => v.start("rite", rite(v), { cooldown: cd(v, CFG.rite.cooldown) }) },
    { name: "horizon", weight: 3.0, run: () => v.start("horizon", horizon(v, [tgt]), { cooldown: cd(v, CFG.horizon.cooldown) }) },
    { name: "choir", weight: drones ? 0 : 2.4, run: () => v.start("choir", choir(v), { cooldown: cd(v, CFG.choir.cooldown) }) },
    { name: "genuflect", weight: 0.6, run: () => v.start("genuflect", genuflect(v), { cooldown: 400, cleanup: () => v.closeHeart() }) },
  ]);
}

export function chooseP2(v: Vesper): (() => void) | undefined {
  const tgt = v.target;
  if (!tgt) return undefined;
  const d = dist(tgt.location, v.pos);
  const near = v.players.some((p) => hdist(p.location, v.pos) < 16);
  if ((v.cooldowns.get("nova") ?? 0) + 700 < v.t && v.ready("nova")) {
    return () => v.start("nova", nova(v), { cooldown: cd(v, CFG.nova.cooldown) });
  }
  const others = v.players.filter((p) => p !== tgt);
  return choose(v, [
    { name: "lunge", weight: d > 6 && d < 30 ? 3.2 : 0.6, run: () => v.start("lunge", lunge(v, tgt), { cooldown: cd(v, CFG.lunge.cooldown), cleanup: () => v.closeHeart() }) },
    { name: "talons", weight: near ? 3 : 0.5, run: () => v.start("talons", talons(v), { cooldown: cd(v, CFG.talons.cooldown) }) },
    { name: "nova", weight: 2.2, run: () => v.start("nova", nova(v), { cooldown: cd(v, CFG.nova.cooldown) }) },
    { name: "horizon2", weight: 1.6, run: () => v.start("horizon2", horizon(v, others.length ? [tgt, others[Math.floor(Math.random() * others.length)]] : [tgt], 7), { cooldown: cd(v, 300) }) },
    { name: "roar", weight: 0.7, run: () => v.start("roar", roar(v), { cooldown: 600 }) },
  ]);
}

