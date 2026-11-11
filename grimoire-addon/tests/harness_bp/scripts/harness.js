// Grimoire test harness (dev only). Runs inside Bedrock Dedicated Server with the Beta APIs
// experiment enabled in the *test world only*. It exercises the real add-on through real inputs:
// SimulatedPlayer.isSneaking (crouch), useItemInSlot / stopUsingItem (hold & release Use),
// selectedSlotIndex (item switching), and observes world state + the add-on's diagnostics replies.
import { world, system, ItemStack, GameMode, EntityDamageCause } from "@minecraft/server";
import { spawnSimulatedPlayer } from "@minecraft/server-gametest";
import { SUITES } from "./suites.js";

const out = (obj) => console.warn(`[HARNESS] ${JSON.stringify(obj)}`);
export const wait = (t) => new Promise((r) => system.runTimeout(r, Math.max(1, t)));

const pending = [];
system.afterEvents.scriptEventReceive.subscribe((e) => {
  if (e.id === "grimoire:debug_reply") {
    let data;
    try { data = JSON.parse(e.message); } catch { return; }
    const i = pending.findIndex((p) => p.match(data));
    if (i >= 0) { const [p] = pending.splice(i, 1); p.resolve(data); }
  } else if (e.id === "harness:run") {
    runSuites(e.message.trim().split(/\s+/).filter(Boolean)).catch((err) => out({ fatal: String(err), stack: err?.stack }));
  }
});

export function debug(cmd, match) {
  return new Promise((resolve) => {
    const entry = { match, resolve };
    pending.push(entry);
    system.sendScriptEvent("grimoire:debug", cmd);
    system.runTimeout(() => {
      const i = pending.indexOf(entry);
      if (i >= 0) { pending.splice(i, 1); resolve(null); }
    }, 20);
  });
}
export const state = (name) => debug(`state ${name}`, (d) => d.kind === "state" && d.name === name);
export const worldInfo = () => debug("world", (d) => d.kind === "world");
export const resetCd = (name) => debug(`reset ${name}`, (d) => d.kind === "reset" && d.name === name);

export const dim = () => world.getDimension("overworld");

export function spawnPlayer(name, x, z, mode = GameMode.Survival) {
  const sp = spawnSimulatedPlayer({ dimension: dim(), x: x + 0.5, y: -60, z: z + 0.5 }, name, mode);
  return sp;
}

export function give(sp, slot, id) {
  sp.getComponent("minecraft:inventory").container.setItem(slot, new ItemStack(id, 1));
}

export async function crouch(sp, hold = 3) {
  sp.isSneaking = true;
  await wait(hold);
  sp.isSneaking = false;
  await wait(3);
}

/** Hold Use for `ticks` then release. */
export async function cast(sp, ticks, slot = sp.selectedSlotIndex) {
  sp.useItemInSlot(slot);
  await wait(ticks);
  sp.stopUsingItem();
  await wait(2);
}

/** Select spell index (0-14) on the current grimoire by crouching the needed number of times. */
export async function selectSpell(sp, school, index) {
  const s = await state(sp.name);
  const cur = s?.selected?.[school] ?? 0;
  const presses = (index - cur + 15) % 15;
  for (let i = 0; i < presses; i++) await crouch(sp, 2);
}

export function spawnTargets(center, count, radius, type = "minecraft:husk") {
  const list = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const loc = { x: center.x + Math.cos(a) * radius, y: center.y, z: center.z + Math.sin(a) * radius };
    const e = dim().spawnEntity(type, loc);
    e.addTag("harness_target");
    try { e.addEffect("slowness", 20 * 60, { amplifier: 4, showParticles: false }); } catch {}
    try { e.addEffect("fire_resistance", 20 * 120, { amplifier: 0, showParticles: false }); } catch {}
    list.push(e);
  }
  return list;
}

export function hp(e) {
  try { return e.isValid ? e.getComponent("minecraft:health").currentValue : 0; } catch { return 0; }
}

export function cleanupTargets() {
  for (const e of dim().getEntities({ tags: ["harness_target"] })) { try { e.remove(); } catch {} }
}

export function countFamily(family) {
  return dim().getEntities({ families: [family] }).length;
}

let results = [];
export function check(suite, name, ok, detail) {
  const r = { suite, name, ok: !!ok, detail };
  results.push(r);
  out(r);
  return !!ok;
}

async function runSuites(names) {
  results = [];
  world.gameRules.doMobSpawning = false;
  try { dim().runCommand("time set noon"); } catch {}
  // simulated players do not keep chunks ticking: register ticking areas over the test arenas
  for (const [n, x] of [["gr_a", 16], ["gr_b", 112], ["gr_c", 208]]) {
    try { dim().runCommand(`tickingarea add circle ${x} -60 0 4 ${n} true`); } catch {}
  }
  await wait(40);
  for (const full of names.length ? names : Object.keys(SUITES)) {
    const [n, filt] = full.split(":");
    const suite = SUITES[n];
    if (!suite) { out({ error: `unknown suite ${n}` }); continue; }
    out({ suiteStart: n });
    try {
      await suite({ only: filt ? filt.split(",") : null, out, wait, debug, state, worldInfo, resetCd, dim, spawnPlayer, give, crouch, cast, selectSpell, spawnTargets, hp, cleanupTargets, countFamily, check, GameMode, EntityDamageCause, world, system });
    } catch (err) {
      check(n, "suite crashed", false, `${err} ${err?.stack ?? ""}`);
    }
    out({ suiteEnd: n });
  }
  const failed = results.filter((r) => !r.ok);
  out({ DONE: true, total: results.length, failed: failed.length });
}

system.runTimeout(() => out({ ready: true }), 20);
