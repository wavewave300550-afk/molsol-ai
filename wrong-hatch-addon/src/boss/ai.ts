/**
 * Attack selection. Each ability scores itself from the situation (range,
 * angle, crowding, players behind / far away, recent burst damage). The AI
 * picks a weighted-random ready ability, avoids repeating itself, and in later
 * phases chains signature combos (e.g. Rooster Rush -> Wing Guillotine).
 */
import { Player } from "@minecraft/server";
import { hdist } from "../util/vec.js";
import { Ability, ABILITIES, abilityById } from "./abilities.js";
import type { BossController } from "./controller.js";

export interface Situation {
  target: Player;
  dist: number;
  angle: number;
  all: Player[];
  near: Player[];
  behind: Player[];
  far: Player[];
  chicks: number;
  recentDamage: number;
}

/** follow-up ability -> condition on the situation after the first one finished */
const COMBOS: Record<string, { next: string; when: (c: BossController, s: Situation) => boolean }[]> = {
  rooster_rush: [{ next: "guillotine", when: (_c, s) => s.dist < 7.5 }, { next: "feather_volley", when: (_c, s) => s.dist >= 7.5 }],
  wing_hop: [{ next: "broodquake", when: (_c, s) => s.dist < 8 }, { next: "peck", when: (_c, s) => s.dist < 6 }],
  sky_drop: [{ next: "molt_burst", when: (_c, s) => s.near.length > 0 }, { next: "egg_mortar", when: (_c, s) => s.dist > 8 }],
  broodquake: [{ next: "egg_mortar", when: (_c, s) => s.dist > 6 }, { next: "guillotine", when: (_c, s) => s.dist < 7 }],
  feather_volley: [{ next: "wing_hop", when: (_c, s) => s.dist > 12 }],
  dawn_flash: [{ next: "rooster_rush", when: (_c, s) => s.dist > 7 }, { next: "peck", when: (_c, s) => s.dist < 6 }],
  shell_fortress: [{ next: "broodquake", when: (_c, s) => s.near.length > 0 }],
};

const COMBO_CHANCE: Record<number, number> = { 1: 0.15, 2: 0.4, 3: 0.7 };

export function chooseAbility(c: BossController, s: Situation): Ability | undefined {
  // 1) planned combo follow-up
  if (c.combo) {
    const a = abilityById(c.combo);
    c.combo = null;
    if (a && a.phases.includes(c.phase) && a.weight(c, s) > 0) return a;
  }
  // 2) weighted choice among ready abilities
  let total = 0;
  const pool: [Ability, number][] = [];
  for (const a of ABILITIES) {
    if (!a.phases.includes(c.phase) || !c.ready(a.id)) continue;
    let w = a.weight(c, s);
    if (w <= 0) continue;
    if (a.id === c.lastAbility) w *= 0.25;
    // anti-starvation: moves that have not been seen for a while become steadily more likely
    const since = c.now - Math.max(c.lastUsed.get(a.id) ?? 0, c.phaseStart);
    w *= 1 + Math.min(2.5, since / 900);
    pool.push([a, w]);
    total += w;
  }
  if (!pool.length) return undefined;
  // close the gap instead of idling when the only options are weak
  let r = Math.random() * total;
  for (const [a, w] of pool) {
    r -= w;
    if (r <= 0) return a;
  }
  return pool[pool.length - 1][0];
}

/** Called when an ability ends: maybe queue a follow-up and shorten the recovery. */
export function planCombo(c: BossController, finished: string): void {
  const options = COMBOS[finished];
  if (!options || Math.random() > COMBO_CHANCE[c.phase]) return;
  const t = c.target();
  if (!t) return;
  const s = c.situation(t);
  for (const o of options) {
    const a = abilityById(o.next);
    if (a && a.phases.includes(c.phase) && o.when(c, s) && a.weight(c, s) > 0) {
      c.combo = o.next;
      c.recoverUntil = c.now + 4;
      return;
    }
  }
  void hdist;
}
