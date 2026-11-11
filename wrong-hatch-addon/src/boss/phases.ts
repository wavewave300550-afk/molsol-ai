/**
 * Scripted set pieces: the hatching intro, the First Crack (phase I -> II),
 * the Final Hatch brood-shell mechanic (phase II -> III and again at 10 %),
 * and the death sequence with rewards.
 */
import { Entity, ItemStack, Player, Vector3, world } from "@minecraft/server";
import { BOTCHED, DMG, SHELL_ID } from "../config.js";
import { KEY } from "../generated/spec.js";
import { hit, viewersNear } from "../util/combat.js";
import { circle, line, particle, ring, shake, sound } from "../util/fx.js";
import { add, dist, v3 } from "../util/vec.js";
import { clearBrood, spawnChick } from "./brood.js";
import type { BossController, Timeline } from "./controller.js";
import { clearHazards } from "./hazards.js";

function shakeAll(c: BossController, r: number, intensity: number, secs: number): void {
  for (const p of viewersNear(c.dim(), c.pos(), r)) shake(p, intensity, secs);
}

// --------------------------------------------------------------------------- intro

export function* intro(c: BossController): Timeline {
  c.invulnerable = true;
  c.setMove("busy");
  c.setPhase(1);
  c.setAnim("intro");
  const dim = c.dim();
  sound(dim, "wrong_hatch.crack_big", c.center(), 2, 0.8);
  for (let t = 0; t < 60; t++) {
    if (t % 6 === 0) particle(dim, "wh:shell_chip", add(c.pos(), v3(Math.random() * 4 - 2, Math.random() * 3, Math.random() * 4 - 2)));
    if (t % 10 === 0) sound(dim, "wrong_hatch.crack", c.center(), 1.5, 0.7 + t / 100);
    if (t === KEY.intro.roar) {
      particle(dim, "wh:shell_burst", c.center());
      particle(dim, "wh:feather_burst", c.center());
      particle(dim, "wh:gold_burst", c.chest());
      sound(dim, "mob.ravager.roar", c.center(), 2, 0.7);
      shakeAll(c, 32, 0.5, 1.2);
      c.announce("§6§lBOSS 001", "§fThe Wrong Hatch");
    }
    yield 1;
  }
  c.setAnim("none");
  c.invulnerable = false;
  c.recoverUntil = c.now + 20;
}

// --------------------------------------------------------------------------- phase I -> II

export function* phaseCrack(c: BossController): Timeline {
  c.invulnerable = true;
  c.setMove("busy");
  try {
    c.setAnim("none");
    yield 2;
    c.setAnim("crow");
    const dim = c.dim();
    for (let t = 0; t < 50; t++) {
      if (t < 20 && t % 4 === 0) sound(dim, "wrong_hatch.crack", c.center(), 2, 0.6 + t / 40);
      if (t === KEY.crow.shout) {
        c.setPhase(2);
        sound(dim, "wrong_hatch.crack_big", c.center(), 3, 0.7);
        sound(dim, "mob.ravager.roar", c.center(), 2, 0.6);
        particle(dim, "wh:shell_burst", c.center());
        particle(dim, "wh:gold_burst", c.center());
        circle(dim, c.pos(), 4, "wh:dust", 16);
        for (const p of c.players(10)) hit(c.entity, p, DMG.crow, c.dmgMul(), { from: c.pos(), knock: 1.6, lift: 0.6 });
        shakeAll(c, 40, 0.7, 1.5);
        c.announce("§e§lTHE SHELL CRACKS", "§7Phase II: The Crack");
      }
      if (t > KEY.crow.shout && t % 3 === 0) particle(dim, "wh:gold_mote", add(c.center(), v3(Math.random() * 4 - 2, Math.random() * 2, Math.random() * 4 - 2)));
      yield 1;
    }
    // first brood bursts out of the shell
    for (let i = 0; i < 2; i++) spawnChick(c, add(c.pos(), v3(Math.random() * 4 - 2, 0, Math.random() * 4 - 2)));
  } finally {
    c.setAnim("none");
    c.invulnerable = false;
    c.recoverUntil = c.now + 16;
  }
}

// --------------------------------------------------------------------------- Final Hatch

function groundAt(c: BossController, x: number, z: number, y: number): Vector3 | undefined {
  try {
    const hitB = c.dim().getBlockFromRay(v3(x, y + 6, z), v3(0, -1, 0), { maxDistance: 16, includePassableBlocks: false, includeLiquidBlocks: true });
    if (!hitB) return undefined;
    const loc = hitB.block.location;
    return v3(x, loc.y + 1, z);
  } catch {
    return undefined;
  }
}

/**
 * The boss seals itself and starts to hatch. Brood Shells tethered to the core
 * appear around it: every shell still standing when the countdown ends powers
 * the Hatch Nova. Break them all and the hatch is botched (long stun).
 */
export function* finalHatch(c: BossController, which: 1 | 2): Timeline {
  c.invulnerable = true;
  c.setMove("busy");
  const dim = c.dim();
  const center = c.pos();
  const count = Math.min(6, 3 + (c.hpScale - 1));
  const duration = which === 1 ? 240 : 200;
  try {
    c.setAnim("none");
    yield 2;
    c.setAnim("final_hatch");
    sound(dim, "wrong_hatch.charge", c.center(), 3, 0.6);
    sound(dim, "mob.warden.sonic_charge", c.center(), 2, 0.7);
    c.announce("§c§lFINAL HATCH", "§eBreak the Brood Shells before it hatches!");
    // place the shells
    c.shells = [];
    const off = Math.random() * Math.PI * 2;
    for (let i = 0; i < count; i++) {
      const a = off + (i / count) * Math.PI * 2;
      const r = 8.5;
      const at = groundAt(c, center.x + Math.sin(a) * r, center.z + Math.cos(a) * r, center.y) ?? v3(center.x + Math.sin(a) * r, center.y, center.z + Math.cos(a) * r);
      try {
        const s = dim.spawnEntity(SHELL_ID, at);
        s.triggerEvent(`wh:shell_${Math.max(1, Math.min(4, c.hpScale))}`);
        c.shells.push(s);
        particle(dim, "wh:shell_burst", add(at, v3(0, 1, 0)));
      } catch {
        // ignore
      }
    }
    yield 6;
    for (let t = 0; t < duration; t++) {
      c.hatchCountdown = duration - t;
      const alive = c.shells.filter((s) => s.isValid);
      if (alive.length === 0) break;
      if (t % 4 === 0) {
        for (const s of alive) line(dim, add(s.location, v3(0, 1.2, 0)), c.chest(), 1.3, "wh:gold_mote");
      }
      if (t % 20 === 0) {
        const secs = Math.ceil((duration - t) / 20);
        sound(dim, "wrong_hatch.pulse", c.center(), 2, 0.6 + (1 - (duration - t) / duration) * 0.8);
        c.announce(`§c§lFINAL HATCH §r§e${secs}s §7- §f${alive.length} Brood Shell${alive.length > 1 ? "s" : ""} left`, undefined, true);
      }
      if (t % 10 === 0) particle(dim, "wh:gold_burst", c.chest());
      yield 1;
    }
    c.hatchCountdown = -1;
    const left = c.shells.filter((s) => s.isValid);
    // the hatch is resolved: lift its damage gate now so a botched hatch can really be punished
    if (which === 1) {
      c.fh1 = true;
      c.entity.setDynamicProperty("wh:fh1", true);
    } else {
      c.fh2 = true;
      c.entity.setDynamicProperty("wh:fh2", true);
    }
    if (left.length === 0) {
      // botched hatch
      c.setAnim("stunned");
      sound(dim, "wrong_hatch.crack_big", c.center(), 3, 0.5);
      sound(dim, "mob.ravager.stun", c.center(), 2, 0.8);
      particle(dim, "wh:shell_burst", c.center());
      c.announce("§a§lBOTCHED HATCH!", "§fThe core is exposed - strike now!");
      c.invulnerable = false;
      c.exposedUntil = c.now + BOTCHED.ticks;
      c.exposedMul = BOTCHED.mul;
      for (let t = 0; t < BOTCHED.ticks; t++) {
        if (t % 6 === 0) particle(dim, "wh:stun_star", add(c.pos(), v3(Math.sin(t / 5) * 1.5, 5.4, Math.cos(t / 5) * 1.5)));
        yield 1;
      }
    } else {
      c.setAnim("hatch_nova");
      yield KEY.hatch_nova.nova;
      const dmg = DMG.novaBase + DMG.novaPerShell * left.length;
      particle(dim, "wh:flash", c.center());
      particle(dim, "wh:nova", c.center());
      particle(dim, "minecraft:huge_explosion_emitter", c.center());
      sound(dim, "wrong_hatch.nova", c.center(), 4, 1);
      shakeAll(c, 48, 1.0, 1.8);
      for (const p of c.players(48)) hit(c.entity, p, dmg, c.dmgMul(), { from: c.pos(), knock: 1.2, lift: 0.7 });
      for (const s of left) {
        const at = s.location;
        particle(dim, "wh:shell_burst", add(at, v3(0, 1, 0)));
        spawnChick(c, at, false);
        spawnChick(c, add(at, v3(0.6, 0, 0.4)), which === 2);
        try {
          s.remove();
        } catch {
          // ignore
        }
      }
      c.invulnerable = false;
      yield 20;
    }
    if (which === 1 && c.phase < 3) {
      c.setPhase(3);
      c.announce("§6§lTHE HATCHING", "§7Phase III");
    }
  } finally {
    c.hatchCountdown = -1;
    for (const s of c.shells) {
      if (s.isValid) {
        try {
          s.remove();
        } catch {
          // ignore
        }
      }
    }
    c.shells = [];
    c.setAnim("none");
    c.invulnerable = false;
    c.recoverUntil = c.now + 10;
  }
}

/** Brood shell destroyed by a player. */
export function onShellBroken(c: BossController, shell: Entity): void {
  const dim = c.dim();
  particle(dim, "wh:shell_burst", add(shell.location, v3(0, 1, 0)));
  particle(dim, "wh:gold_burst", add(shell.location, v3(0, 1, 0)));
  sound(dim, "wrong_hatch.crack_big", shell.location, 2, 1.2);
  // the boss flinches when a tether snaps
  particle(dim, "wh:shell_chip", c.center());
  ring(dim, shell.location, 2, false);
}

// --------------------------------------------------------------------------- death

export function* deathSequence(c: BossController): Timeline {
  c.invulnerable = true;
  c.dying = true;
  c.setMove("busy");
  clearHazards(c.id);
  const dim = c.dim();
  c.setAnim("none");
  yield 2;
  c.setAnim("death");
  c.announce("§6§lTHE WRONG HATCH FALLS", "§7...but something is still moving inside");
  sound(dim, "wrong_hatch.crow", c.center(), 2, 0.4);
  for (let t = 0; t < 100; t++) {
    const k = t / 100;
    if (t % Math.max(2, Math.round(10 - k * 8)) === 0) {
      sound(dim, "wrong_hatch.crack", c.center(), 1.5, 0.6 + k);
      particle(dim, "wh:shell_chip", add(c.center(), v3(Math.random() * 4 - 2, Math.random() * 2 - 1, Math.random() * 4 - 2)));
    }
    if (t % 3 === 0) particle(dim, "wh:gold_mote", add(c.chest(), v3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5)));
    if (t === KEY.death.crack) {
      sound(dim, "wrong_hatch.crack_big", c.center(), 3, 0.6);
      particle(dim, "wh:gold_burst", c.chest());
      shakeAll(c, 32, 0.4, 1.0);
    }
    if (t === KEY.death.burst) {
      const at = c.center();
      particle(dim, "wh:flash", at);
      particle(dim, "wh:nova", at);
      particle(dim, "wh:shell_burst", at);
      particle(dim, "wh:feather_burst", at);
      particle(dim, "minecraft:huge_explosion_emitter", at);
      sound(dim, "wrong_hatch.nova", at, 3, 1.1);
      shakeAll(c, 48, 0.8, 1.2);
    }
    yield 1;
  }
  reward(c);
  c.cleanup(false); // we are the running timeline: do not stop ourselves
  clearBrood(c.id);
  try {
    c.entity.remove();
  } catch {
    // ignore
  }
}

function reward(c: BossController): void {
  const dim = c.dim();
  const at = add(c.pos(), v3(0, 1, 0));
  let looted = false;
  try {
    dim.runCommand(`loot spawn ${at.x.toFixed(2)} ${at.y.toFixed(2)} ${at.z.toFixed(2)} loot "entities/wrong_hatch"`);
    looted = true;
  } catch {
    looted = false;
  }
  if (!looted) {
    const drops: [string, number][] = [
      ["wh:guillotine_pinion", 1], ["wh:hatch_core", 1], ["wh:eggshell_plate", 8], ["wh:golden_yolk", 4], ["minecraft:gold_ingot", 12],
    ];
    for (const [id, n] of drops) {
      try {
        dim.spawnItem(new ItemStack(id, n), at);
      } catch {
        // ignore
      }
    }
  }
  const xp = 160 * Math.max(1, c.hpScale);
  const names: string[] = [];
  for (const p of viewersNear(dim, c.pos(), 64)) {
    if (!(p instanceof Player)) continue;
    if (c.participants.size && !c.participants.has(p.id) && dist(p.location, c.pos()) > 24) continue;
    try {
      p.addExperience(xp);
      names.push(p.name);
    } catch {
      // ignore
    }
  }
  if (names.length) {
    try {
      world.sendMessage(`§6[BOSS 001] §fThe Wrong Hatch was defeated by §e${names.join(", ")}§f!`);
    } catch {
      // ignore
    }
  }
}
