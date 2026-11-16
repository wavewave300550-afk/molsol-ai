import {
  EasingType, EntityDamageCause, HudVisibility, ItemStack, Player, world,
} from "@minecraft/server";
import { CFG } from "../config.js";
import { ITEMS, PHASE } from "../generated/ids.js";
import { afterglow } from "../afterglow.js";
import { COLORS, particle, shockwave, sound } from "../util/fx.js";
import { add, hdist, rand, V3 } from "../util/vec.js";
import { chest, groundY, hasLineOfSight, hurt, knock, spectators } from "../util/world.js";
import type { Step, Vesper } from "./controller.js";
import { Censer, Plate, Seraph, Wave } from "./minions.js";

function lore(v: Vesper, text: string): void {
  for (const p of spectators(v.dim, v.arena, CFG.arenaRange + 16)) {
    try {
      p.sendMessage(`§7§o« ${text} »`);
    } catch {
      /* ignore */
    }
  }
}

function title(v: Vesper, main: string, sub: string, stay = 60): void {
  for (const p of spectators(v.dim, v.arena, CFG.arenaRange + 16)) {
    try {
      p.onScreenDisplay.setTitle(main, { fadeInDuration: 10, stayDuration: stay, fadeOutDuration: 20, subtitle: sub });
    } catch {
      /* ignore */
    }
  }
}

export function cinematicsEnabled(): boolean {
  try {
    return world.getDynamicProperty("sab:cinematics") !== false;
  } catch {
    return true;
  }
}

// ========================================================================================= arrival

export function startArrival(v: Vesper): void {
  v.start("arrive", arrive(v), { interruptible: false });
}

function* arrive(v: Vesper): Step {
  v.invulnerable = true;
  v.setAct("arrive");
  v.goal.pos = { x: v.arena.x, y: -1, z: v.arena.z };
  v.goal.alt = CFG.altitudeP1 + 2;
  v.goal.speed = 0.45;
  v.goal.accel = 0.035;
  sound(v.dim, "arrive", v.arena, 3.0);
  particle(v.dim, "summon_flash", v.pos);
  lore(v, "I heard your hymn across eleven thousand years of static. Kneel, little star.");
  for (let i = 0; i < 120; i++) {
    if (i === 78) title(v, "§fVESPER-0", "§eThe Ship That Learned to Pray");
    if (i % 30 === 0) particle(v.dim, "ring_spark", v.core());
    yield 1;
  }
  v.invulnerable = false;
  v.gcdUntil = v.t + 30;
}

// ======================================================================================= departure

export function startDepart(v: Vesper): void {
  v.departing = true;
  v.start("depart", depart(v), { interruptible: false });
}

function* depart(v: Vesper): Step {
  v.invulnerable = true;
  v.setAct("depart");
  lore(v, "No hymn answers. I return to the dark between the stars.");
  v.goal.pos = { x: v.pos.x, y: v.pos.y + 70, z: v.pos.z };
  v.goal.speed = 0.6;
  v.goal.accel = 0.03;
  yield 100;
  // the summoning was not answered: return the Psalter
  try {
    v.dim.spawnItem(new ItemStack(ITEMS.psalter, 1), add(v.arena, { x: 0, y: 1, z: 0 }));
  } catch {
    /* ignore */
  }
  v.pendingDispose = true;
}

// ========================================================================================= prayer

export function startPrayer(v: Vesper, level: 1 | 2): void {
  v.start(level === 1 ? "vespers" : "requiem", prayer(v, level), {
    interruptible: false,
    cleanup: () => {
      for (const c of v.minions.of<Censer>("censer")) c.shatter();
      for (const s of v.minions.of<Seraph>("seraph")) s.guard = undefined;
      v.invulnerable = false;
      v.prop("sab:censers", v.phase < PHASE.p2);
      v.closeHeart();
    },
  });
}

function* prayer(v: Vesper, level: 1 | 2): Step {
  const P = CFG.prayer;
  const dark = level === 2;
  v.invulnerable = true;
  v.setAct("pray");
  v.prop("sab:censers", false);
  v.goal.pos = { x: v.arena.x, y: -1, z: v.arena.z };
  v.goal.alt = 15;
  v.goal.speed = 0.35;
  sound(v.dim, "choir", v.pos, 2.5);
  sound(v.dim, "prayer", v.pos, 2.0);
  if (level === 1) {
    title(v, "§6VESPERS", "§fShatter the censers before the hymn ends!");
    lore(v, "Hear me, Sun beyond the sun. Let these small lights be my offering.");
  } else {
    title(v, "§5REQUIEM", "§fThe rings guard the censers — shatter them!");
    lore(v, "If there is no god beyond the sun, then I will be the sun.");
  }
  const n = (level === 1 ? P.censersP1 : P.censersP2) + (v.players.length >= 3 ? 1 : 0);
  const a0 = Math.random() * 360;
  const censers: Censer[] = [];
  const seraphs = v.minions.of<Seraph>("seraph").filter((s) => s.mode !== 3);
  for (let i = 0; i < n; i++) {
    const a = ((a0 + (360 / n) * i) * Math.PI) / 180;
    const r = rand(12, 17);
    const x = v.arena.x + Math.cos(a) * r;
    const z = v.arena.z + Math.sin(a) * r;
    const to: V3 = { x, y: groundY(v.dim, x, z, v.ground, v.arena.y + 20) + rand(2.5, 4.5), z };
    const from = v.at(0, -31, [-30, -2, 26][i % 3]);
    const c = new Censer(v, from, to, dark);
    censers.push(c);
    v.addMinion(c);
    if (dark && seraphs[i]) seraphs[i].guard = to;
  }
  const duration = level === 1 ? P.durationP1 : P.durationP2;
  let broken = false;
  for (let i = 0; i < duration; i++) {
    const alive = censers.filter((c) => !c.destroyed && c.entity && c.entity.isValid);
    if (!alive.length) {
      broken = true;
      break;
    }
    if (i % 10 === 0) {
      const left = Math.ceil((duration - i) / 20);
      const bar = "▮".repeat(Math.ceil(((duration - i) / duration) * 12)).padEnd(12, "▯");
      for (const p of v.players) {
        try {
          p.onScreenDisplay.setActionBar(`${dark ? "§5" : "§6"}${bar} §f${left}s  §7censers left: §f${alive.length}`);
        } catch {
          /* ignore */
        }
      }
    }
    if (i > 0 && i % P.pulseEvery === 0) {
      const g = v.groundPoint();
      sound(v.dim, "bell_low", g, 2.0, 1.1);
      v.addMinion(new Wave(v, g, false, 0.45, 24, P.pulseDamage, dark ? COLORS.violet : COLORS.gold));
    }
    if (i % 120 === 119) sound(v.dim, "prayer", v.pos, 2.0);
    yield 1;
  }
  for (const s of v.minions.of<Seraph>("seraph")) s.guard = undefined;
  if (broken) {
    sound(v.dim, "prayer_broken", v.pos, 3.0);
    title(v, "§bPRAYER BROKEN", "§fStrike the exposed heart!", 40);
    lore(v, "...silence? Why is it always silence?");
    v.invulnerable = false;
    v.setAct("stunned");
    v.goal.alt = level === 1 ? 1.4 : 1.8;
    v.goal.speed = 0.6;
    v.goal.accel = 0.08;
    yield 22;
    const g = v.groundPoint();
    sound(v.dim, "plate_impact", g, 2.0, 0.6);
    particle(v.dim, "dust", g);
    shockwave(v.dim, add(g, { x: 0, y: 0.3, z: 0 }), 10, 0.6, COLORS.white);
    v.openHeart(CFG.heartMultStunned, level === 1 ? 22 : 30);
    for (let i = 0; i < P.stun; i++) {
      if (i % 20 === 0) particle(v.dim, "heart_sparks", v.core());
      yield 1;
    }
    v.closeHeart();
  } else {
    // Benediction: radiant blast through everything not behind cover
    const core = v.core();
    sound(v.dim, "benediction", core, 3.0);
    particle(v.dim, dark ? "nova_blast" : "holy_blast", core);
    shockwave(v.dim, core, 24, 1.5, dark ? COLORS.violet : COLORS.gold);
    title(v, dark ? "§5FALSE BENEDICTION" : "§6BENEDICTION", "§fthe hymn is complete", 30);
    const covers = v.minions.covers();
    const dmg = level === 1 ? P.benedictionP1 : P.benedictionP2;
    for (const p of v.players) {
      if (hasLineOfSight(v.dim, core, p.getHeadLocation(), covers) || hasLineOfSight(v.dim, core, chest(p), covers)) {
        hurt(p, dmg, v.boss, EntityDamageCause.magic);
        knock(p, core, 1.2, 0.5);
      }
    }
    const remaining = censers.filter((c) => !c.destroyed && c.entity?.isValid).length;
    const hp = v.boss.getComponent("minecraft:health");
    if (hp) {
      try {
        hp.setCurrentValue(Math.min(hp.effectiveMax, hp.currentValue + CFG.maxHealth * P.healPerCenser * remaining));
      } catch {
        /* ignore */
      }
    }
    for (const c of censers) c.shatter();
    yield 30;
  }
  v.invulnerable = false;
  v.prop("sab:censers", level === 1);
}

// ===================================================================================== transformation

export function startTransform(v: Vesper): void {
  v.start("transform", transform(v), { interruptible: false });
}

function shot(v: Vesper, players: Player[], loc: V3, ease: number): void {
  const core = v.core();
  for (const p of players) {
    try {
      p.camera.setCamera("minecraft:free", { location: loc, facingLocation: core,
        easeOptions: { easeTime: ease, easeType: EasingType.InOutSine } });
    } catch {
      /* ignore */
    }
  }
}

function* transform(v: Vesper): Step {
  const T = CFG.transform;
  v.invulnerable = true;
  v.closeHeart();
  v.setPhase(PHASE.transform);
  v.setAct("idle");
  v.goal.pos = { x: v.pos.x, y: -1, z: v.pos.z };
  v.goal.alt = CFG.altitudeP1;
  v.goal.speed = 0.15;
  v.goal.turn = 1.0;
  for (const d of v.minions.of("drone")) d.dispose();
  for (const o of v.minions.of("orb")) o.dispose();
  sound(v.dim, "transform", v.pos, 3.0);
  lore(v, "Is this what you call the sky? Then let me show you what lives beneath my scripture.");
  const viewers = cinematicsEnabled() ? spectators(v.dim, v.pos, 48) : [];
  for (const p of viewers) {
    v.cinematic.set(p.id, v.t + T.length + 2);
    try {
      p.onScreenDisplay.setHudVisibility(HudVisibility.Hide);
      p.addEffect("resistance", T.length + 40, { amplifier: 4, showParticles: false });
    } catch {
      /* ignore */
    }
  }
  for (let i = 0; i <= T.length; i++) {
    if (i === 0 && viewers.length) shot(v, viewers, v.at(-320, 60, -60), 1.4);
    if (i === 64 && viewers.length) shot(v, viewers, v.at(-170, 10, -300), 1.6);
    if (i === 126 && viewers.length) shot(v, viewers, v.at(260, -30, 140), 1.2);
    if (i === T.ringsAt) {
      v.prop("sab:rings", false);
      sound(v.dim, "seraph_whine", v.pos, 2.5, 0.7);
      const from = [v.at(0, 64, -2), v.at(0, 72, -128), v.at(0, 64, 122)];
      for (let r = 0; r < 3; r++) v.addMinion(new Seraph(v, r, from[r]));
    }
    if (i === T.limbsAt) {
      v.prop("sab:limbs", true);
      v.prop("sab:censers", false);
    }
    if (i === T.platesAt) {
      v.prop("sab:plates", false);
      const n = Math.min(9, T.plates + Math.max(0, v.players.length - 2));
      const a0 = Math.random() * 360;
      for (let k = 0; k < n; k++) {
        const a = ((a0 + (360 / n) * k + rand(-12, 12)) * Math.PI) / 180;
        const r = rand(8, 17);
        const x = v.arena.x + Math.cos(a) * r;
        const z = v.arena.z + Math.sin(a) * r;
        const to = { x, y: groundY(v.dim, x, z, v.ground, v.arena.y + 24), z };
        const side = k % 2 ? -1 : 1;
        const from = v.at(side * 70, 110, -40 + (k % 5) * 22);
        v.addMinion(new Plate(v, { ...from, y: from.y + 6 }, to, k * 3));
      }
    }
    if (i === T.skinAt) {
      v.prop("sab:skin", 1);
      v.moodP2 = true;
      v.refreshMood();
      particle(v.dim, "arrival_flash", v.core());
      for (const p of spectators(v.dim, v.pos, 64)) {
        try {
          p.camera.fade({ fadeColor: { red: 0.55, green: 0.2, blue: 0.85 }, fadeTime: { fadeInTime: 0.1, holdTime: 0.15, fadeOutTime: 0.8 } });
        } catch {
          /* ignore */
        }
      }
    }
    if (i === T.roarAt) title(v, "§5THE FALSE ASCENSION", "§fVESPER-0 sheds its scripture", 50);
    yield 1;
  }
  for (const p of viewers) v.releaseCamera(p);
  v.setPhase(PHASE.p2);
  v.closeHeart();
  v.invulnerable = false;
  v.gcdUntil = v.t + 30;
}

// ========================================================================================= unhaloed

/** All three Seraph rings broken at once: VESPER-0 staggers with its heart exposed. */
export function startUnhaloed(v: Vesper): void {
  v.start("unhaloed", unhaloed(v), { cooldown: 600, cleanup: () => v.closeHeart() });
}

function* unhaloed(v: Vesper): Step {
  v.setAct("unhaloed");
  sound(v.dim, "prayer_broken", v.pos, 2.5, 0.8);
  title(v, "§dUNHALOED", "§fits rings are silent — strike the heart!", 40);
  v.goal.pos = { x: v.pos.x, y: -1, z: v.pos.z };
  v.goal.alt = 2.0;
  v.goal.speed = 0.5;
  for (const s of v.minions.of<Seraph>("seraph")) s.dormantUntil += CFG.seraph.unhaloed + 100;
  yield 16;
  v.openHeart(CFG.heartMult, 34);
  for (let i = 0; i < CFG.seraph.unhaloed; i++) {
    if (i % 20 === 0) particle(v.dim, "heart_sparks", v.core());
    yield 1;
  }
  v.closeHeart();
}

// =========================================================================================== death

export function startDeath(v: Vesper): void {
  v.dying = true;
  v.start("death", death(v), { interruptible: false });
}

function* death(v: Vesper): Step {
  v.invulnerable = true;
  v.setPhase(PHASE.dying);
  v.closeHeart();
  for (const s of v.minions.of<Seraph>("seraph")) s.breakRing();
  for (const kind of ["drone", "orb", "censer", "well"]) v.minions.clear(kind);
  for (const id of v.audience) {
    const p = world.getEntity(id);
    if (p && p.typeId === "minecraft:player") {
      try {
        (p as Player).stopMusic();
      } catch {
        /* ignore */
      }
    }
  }
  sound(v.dim, "death", v.pos, 3.0);
  lore(v, "Ah. So this is what the stars hear... when no one answers.");
  v.goal.pos = { x: v.pos.x, y: -1, z: v.pos.z };
  v.goal.alt = 1.5;
  v.goal.speed = 0.07;
  v.goal.turn = 0.4;
  for (let i = 0; i < CFG.death.length; i++) {
    if (i % 20 === 0) particle(v.dim, "stun_sparks", v.core());
    if (i === 120) {
      particle(v.dim, "holy_blast", v.core());
      for (const p of spectators(v.dim, v.pos, 48)) {
        try {
          p.camera.fade({ fadeColor: { red: 1, green: 1, blue: 1 }, fadeTime: { fadeInTime: 0.2, holdTime: 0.3, fadeOutTime: 1.6 } });
        } catch {
          /* ignore */
        }
      }
    }
    yield 1;
  }
  rewards(v);
  title(v, "§fVESPER-0 HAS FALLEN SILENT", "§7its last prayer was for you", 80);
  v.pendingDispose = true;
}

export function rewards(v: Vesper): void {
  const site = v.groundPoint();
  const at = add(site, { x: 0, y: 1, z: 0 });
  const R = CFG.rewards;
  const total = [...v.participants.values()].reduce((s, p) => s + p.damage, 0);
  const winners: Player[] = [];
  for (const [id, part] of v.participants) {
    const p = world.getEntity(id);
    if (!p || p.typeId !== "minecraft:player" || p.dimension.id !== v.dim.id) continue;
    if (total > 0 && part.damage < total * 0.03 && hdist(p.location, site) > 40) continue;
    winners.push(p as Player);
  }
  for (const p of winners.slice(0, 6)) {
    let first = true;
    try {
      first = p.getDynamicProperty("sab:halo_awarded") !== true;
      p.setDynamicProperty("sab:halo_awarded", true);
    } catch {
      /* ignore */
    }
    try {
      if (first || Math.random() < 0.25) v.dim.spawnItem(new ItemStack(ITEMS.halo, 1), at);
      v.dim.spawnItem(new ItemStack(ITEMS.alloy, Math.round(rand(R.alloyMin, R.alloyMax))), at);
    } catch {
      /* ignore */
    }
  }
  if (!winners.length) {
    try {
      v.dim.spawnItem(new ItemStack(ITEMS.alloy, R.alloyMin), at);
    } catch {
      /* ignore */
    }
  }
  for (let k = 0; k < 10; k++) {
    try {
      v.dim.spawnXp(add(at, { x: rand(-2, 2), y: 0.5, z: rand(-2, 2) }), Math.round(R.xp / 10));
    } catch {
      /* ignore */
    }
  }
  particle(v.dim, "dying_star", add(site, { x: 0, y: 2, z: 0 }));
  afterglow.add(v.dim, site, R.blessing);
  for (const p of winners) {
    try {
      p.sendMessage("§eThe Dying Star's light mends you. §7(Regeneration near the crash site)");
    } catch {
      /* ignore */
    }
  }
}

// ======================================================================================= resume after reload

export function resumeAfterLoad(v: Vesper): void {
  // transient sequences cannot resume mid-way: settle into the nearest stable state
  if (v.phase === PHASE.transform) {
    v.prop("sab:rings", false);
    v.prop("sab:plates", false);
    v.prop("sab:limbs", true);
    v.prop("sab:censers", false);
    v.prop("sab:skin", 1);
    v.setPhase(PHASE.p2);
  }
  v.invulnerable = false;
  v.prop("sab:shield", false);
  v.setAct("idle");
  if (v.phase >= PHASE.p2) {
    v.moodP2 = true;
    v.prop("sab:censers", false);
    if (!v.minions.of("seraph").length) {
      for (let r = 0; r < 3; r++) v.addMinion(new Seraph(v, r, v.at(0, 64, -2)));
    }
  } else {
    v.prop("sab:censers", true);
  }
  if (v.phase === PHASE.dying) startDeath(v);
}
