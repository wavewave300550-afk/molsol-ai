// Cliff Sigil: summons Gharvok after a short ritual, at a checked spot in front of the player.
import { GameMode, world, system } from "@minecraft/server";
import { CONFIG, GHARVOK_ID, SIGIL_ID } from "./config.js";
import { activeOfType } from "../../core/registry.js";
import { particle, sound } from "../../core/fx.js";
import { footprintClear, groundAt } from "../../core/terrain.js";
import { now, safe, sec } from "../../core/util.js";
import { dirOf, distXZ, yawTo } from "../../core/vec.js";

const NS = "dragon_dominion";
const RITUAL = sec(3);
let ritual; // only one summoning at a time, world-wide
const lastUse = new Map();

function say(p, text) {
  safe(() => p.sendMessage(text));
}

/** First valid spot in front of the player: solid ground, a 7x7 footprint and 6 blocks of headroom. */
export function findSpawnSpot(dim, origin, yaw) {
  const dists = [CONFIG.summon.distance, CONFIG.summon.distance - 3, CONFIG.summon.distance + 3, 8];
  for (const d of dists) {
    for (const off of [0, 25, -25, 50, -50]) {
      const f = dirOf(yaw + off);
      const x = origin.x + f.x * d;
      const z = origin.z + f.z * d;
      const g = groundAt(dim, x, z, origin.y, 4, 8);
      if (g === undefined) continue;
      if (footprintClear(dim, x, g, z, 3, 6)) return { x, y: g, z };
    }
  }
  return undefined;
}

function consumeOne(p) {
  if (safe(() => p.getGameMode()) === GameMode.Creative) return;
  const c = safe(() => p.getComponent("minecraft:inventory").container);
  if (!c) return;
  const slot = p.selectedSlotIndex;
  const it = safe(() => c.getItem(slot));
  if (!it || it.typeId !== SIGIL_ID) return;
  if (it.amount > 1) {
    it.amount -= 1;
    safe(() => c.setItem(slot, it));
  } else safe(() => c.setItem(slot, undefined));
}

export function useSigil(p) {
  const t = now();
  if (t - (lastUse.get(p.id) ?? -9999) < sec(CONFIG.summon.cooldown)) return "cooldown";
  lastUse.set(p.id, t);
  const dim = p.dimension;
  if (ritual) {
    say(p, "§7A summoning is already under way.");
    return "busy";
  }
  // prevent accidental duplicates: one Gharvok answers the sigil at a time
  const alive = activeOfType(GHARVOK_ID).find((c) => c.dim.id === dim.id && c.state !== "DEAD");
  const loaded = alive ?? (safe(() => dim.getEntities({ type: GHARVOK_ID, location: p.location, maxDistance: CONFIG.summon.searchRadius })) ?? [])[0];
  if (loaded) {
    const d = Math.round(distXZ(p.location, alive ? alive.pos() : loaded.location));
    say(p, `§6Gharvok already roams this land §7(${d} blocks away). Defeat it before using another Cliff Sigil.`);
    return "duplicate";
  }
  const spot = findSpawnSpot(dim, p.location, safe(() => p.getRotation().y, 0));
  if (!spot) {
    say(p, "§7The sigil finds no ground here. Stand in an open area (about 7x7 blocks, 6 high) with solid ground ahead.");
    return "no_spot";
  }
  consumeOne(p);
  ritual = { spot, dim, t0: t, yaw: yawTo(spot, p.location), by: p.id };
  say(p, "§6The Cliff Sigil cracks... the ground answers.");
  particle(dim, `${NS}:summon_pillar`, spot);
  sound(dim, "mob.ravager.ambient", spot, 3, 0.5);
  return "ok";
}

function tickRitual() {
  if (!ritual) return;
  const r = ritual;
  const t = now() - r.t0;
  if (t % 10 === 0) {
    particle(r.dim, `${NS}:summon_pillar`, r.spot);
    particle(r.dim, `${NS}:warning_ring`, { x: r.spot.x, y: r.spot.y + 0.15, z: r.spot.z }, { "variable.radius": 3.5 });
  }
  if (t % 20 === 0) sound(r.dim, "mob.ravager.step", r.spot, 3, 0.5);
  if (t < RITUAL) return;
  ritual = undefined;
  const e = safe(() => r.dim.spawnEntity(GHARVOK_ID, r.spot));
  if (!e) return;
  safe(() => e.setRotation({ x: 0, y: r.yaw }));
  particle(r.dim, `${NS}:dust_ring`, r.spot);
  sound(r.dim, "random.explode", r.spot, 1, 0.5);
}

export function initSummon() {
  world.afterEvents.itemUse.subscribe((ev) => {
    if (ev.itemStack?.typeId !== SIGIL_ID) return;
    useSigil(ev.source);
  });
  system.runInterval(tickRitual, 1);
}
