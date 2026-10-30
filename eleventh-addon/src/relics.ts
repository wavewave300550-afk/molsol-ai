import { Player, system, Vector3 } from "@minecraft/server";
import { beam, burst, glyphs, mote, sound, stringWave } from "./core/fx.js";
import { chest, healthOf, hurt, victimsOnLine } from "./core/targets.js";
import { add, scale, v } from "./core/vec.js";

/** Trophies dropped by the beings - each grants a fragment of its power. */

export const RELICS = {
  petal: "dim11:folded_petal",
  string: "dim11:string_of_creation",
  eye: "dim11:eye_of_the_axis",
} as const;

const COOLDOWN: Record<string, [string, number]> = {
  [RELICS.petal]: ["dim11_petal", 50],
  [RELICS.string]: ["dim11_string", 30],
  [RELICS.eye]: ["dim11_eye", 1200],
};

interface Mark {
  tick: number;
  pos: Vector3;
  dimId: string;
  hp: number;
}
const trail = new Map<string, Mark[]>();

export function isRelic(id: string): boolean {
  return id in COOLDOWN;
}

function onCooldown(p: Player, id: string): boolean {
  const [cat, ticks] = COOLDOWN[id];
  try {
    if (p.getItemCooldown(cat) > 0) return true;
    p.startItemCooldown(cat, ticks);
  } catch {
    // cooldown API unavailable - fall through
  }
  return false;
}

export function useRelic(p: Player, id: string): void {
  if (onCooldown(p, id)) return;
  const dim = p.dimension;
  const eye = p.getHeadLocation();
  const dir = p.getViewDirection();
  if (id === RELICS.petal) {
    let dist = 12;
    try {
      const hit = p.getBlockFromViewDirection({ maxDistance: 12 });
      if (hit) dist = Math.max(0, Math.hypot(hit.block.location.x + 0.5 - eye.x, hit.block.location.y + 0.5 - eye.y, hit.block.location.z + 0.5 - eye.z) - 1.2);
    } catch {
      // ignore
    }
    const to = add(p.location, scale(dir, dist));
    burst(dim, "violet", chest(p));
    beam(dim, "violet", chest(p), add(to, v(0, 1, 0)), 0.5);
    p.teleport(to, { keepVelocity: false });
    burst(dim, "violet", add(to, v(0, 1, 0)));
    sound(dim, "mob.endermen.portal", to, 1, 1.4);
  } else if (id === RELICS.string) {
    const to = add(eye, scale(dir, 28));
    stringWave(dim, "cyan", eye, to, system.currentTick * 0.8, 0.5);
    sound(dim, "resonate.amethyst_block", eye, 1.5, 1.2);
    for (const e of victimsOnLine(dim, eye, to, 1.2)) {
      if (e.id === p.id || e instanceof Player) continue;
      hurt(e, 10, p);
      burst(dim, "cyan", chest(e));
    }
  } else if (id === RELICS.eye) {
    const list = trail.get(p.id) ?? [];
    const past = list.find((m) => system.currentTick - m.tick <= 100 && m.dimId === dim.id);
    if (!past) {
      p.sendMessage("§6[Eye of the Axis] §7No recorded past to return to yet.");
      return;
    }
    burst(dim, "gold", chest(p));
    beam(dim, "gold", chest(p), add(past.pos, v(0, 1, 0)), 0.5);
    p.teleport(past.pos);
    const h = healthOf(p);
    if (h && past.hp > h.currentValue) h.setCurrentValue(past.hp);
    glyphs(dim, add(past.pos, v(0, 1, 0)));
    sound(dim, "beacon.deactivate", past.pos, 1, 1.6);
    p.sendMessage("§6[Eye of the Axis] §7You step back five seconds along the eleventh axis.");
  }
}

/** Every 10 ticks: record the eye-holder's past, and reveal nearby creatures to them. */
export function tickRelics(players: Player[], tick: number): void {
  for (const p of players) {
    let holds = false;
    for (let i = 0; i < 9 && !holds; i++) {
      holds = p.getComponent("minecraft:inventory")?.container?.getItem(i)?.typeId === RELICS.eye;
    }
    if (!holds) {
      trail.delete(p.id);
      continue;
    }
    const h = healthOf(p);
    const list = trail.get(p.id) ?? [];
    list.push({ tick, pos: { ...p.location }, dimId: p.dimension.id, hp: h ? h.currentValue : 20 });
    while (list.length > 11) list.shift();
    trail.set(p.id, list);
    const held = p.getComponent("minecraft:inventory")?.container?.getItem(p.selectedSlotIndex)?.typeId;
    if (held === RELICS.eye && tick % 20 === 0) {
      for (const e of p.dimension.getEntities({ location: p.location, maxDistance: 32, families: ["monster"] })) {
        try {
          p.spawnParticle("dim11:mote_gold", add(e.location, v(0, 2.4, 0)));
        } catch {
          // ignore
        }
      }
      mote(p.dimension, "gold", add(p.location, v(0, 2.2, 0)));
    }
  }
}
