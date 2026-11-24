import { Player } from "@minecraft/server";
import type { Brain, Obs } from "../brain.js";
import type { JoanBoss, SkillGen } from "../joan.js";
import { convergence } from "./convergence.js";
import { heavensDetour } from "./detour.js";
import { melee } from "./melee.js";
import { roadOfOrleans } from "./orleans.js";
import { martyrsProcession } from "./procession.js";
import { falseSalvation } from "./salvation.js";
import { roadToTheStake } from "./stake.js";
import { bannerTrail, pilgrimsSurge } from "./trail.js";

export interface SkillDef {
  name: string;
  title: string;
  phases: number[];
  big: boolean;
  score(b: JoanBoss, t: Player, o: Obs, brain: Brain): number;
  run(b: JoanBoss, t: Player, data: unknown): SkillGen;
}

const band = (d: number, lo: number, hi: number): number => (d >= lo && d <= hi ? 1 : 0);

/**
 * Utility scores: base desire x situation. The brain removes skills on
 * cooldown, punishes repeats and too many big skills in a row, then picks
 * among the best three (weighted) so the fight is readable but not robotic.
 */
export const SKILLS: SkillDef[] = [
  {
    name: "melee",
    title: "Standard Strikes",
    phases: [1, 2],
    big: false,
    score: (b, t, o) => (o.dist < 4.2 ? 9 + o.melee * 0.5 : o.dist < 5.5 ? 3 : 0),
    run: (b, t) => melee(b, t),
  },
  {
    name: "trail",
    title: "Banner Trail",
    phases: [1, 2],
    big: false,
    score: (b, t, o) =>
      band(o.dist, 4, 17) * (5 + (o.kiting > 1 ? 2 : 0) + (b.field.activePaths().length < 2 ? 1.5 : 0)) + (o.dist < 4 ? 1 : 0),
    run: (b, t) => bannerTrail(b, t),
  },
  {
    name: "surge",
    title: "Pilgrim's Surge",
    phases: [1, 2],
    big: false,
    score: (b, t, o) =>
      (o.dist > 9 ? 5 + Math.min(4, (o.dist - 9) * 0.4) : o.dist > 6 ? 2 : 0.3) + (o.los ? 0 : 4) + (o.onRoad ? 3 : 0) +
      (o.kiting > 1 ? 2 : 0),
    run: (b, t, data) => pilgrimsSurge(b, t, data),
  },
  {
    name: "orleans",
    title: "Road of Orleans",
    phases: [1, 2],
    big: true,
    score: (b, t, o) => band(o.dist, 5, 18) * (4.5 + o.ranged * 1.2 + (o.kiting > 1 ? 1.5 : 0)),
    run: (b, t) => roadOfOrleans(b, t),
  },
  {
    name: "salvation",
    title: "False Salvation",
    phases: [1, 2],
    big: true,
    score: (b, t, o) => band(o.dist, 4, 18) * (4 + (o.still > 40 ? 3 : 0) + (o.caught > 2 ? 1.5 : 0)) + (b.phase >= 2 && o.jumps > 1 ? 2 : 0),
    run: (b, t) => falseSalvation(b, t),
  },
  {
    name: "convergence",
    title: "Convergence of the Standard",
    phases: [1, 2],
    big: true,
    score: (b, t, o, brain) => (o.dist > 7 ? 4 : 1.5) + (brain.engaged > 1 ? 2.5 : 0) + (o.kiting > 1 ? 2 : 0) + o.ranged * 0.6,
    run: (b, t) => convergence(b, t),
  },
  {
    name: "detour",
    title: "Heaven's Detour",
    phases: [1, 2],
    big: true,
    score: (b, t, o) => 1.5 + o.ranged * 2.2 + (o.drawing ? 3 : 0) + (o.los ? 0 : 3.5) + (o.dist > 12 ? 1 : 0),
    run: (b, t) => heavensDetour(b, t),
  },
  {
    name: "procession",
    title: "Martyr's Procession",
    phases: [1, 2],
    big: true,
    score: (b, t, o, brain) => {
      const scars = b.field.scars.length;
      return scars >= 3 ? 2.5 + scars * 0.9 + (brain.engaged > 1 ? 1.5 : 0) : scars >= 1 ? 1 : 0;
    },
    run: (b, t) => martyrsProcession(b, t),
  },
  {
    name: "stake",
    title: "Road to the Stake",
    phases: [2],
    big: true,
    score: () => 0, // triggered by health thresholds, never by utility
    run: (b, t) => roadToTheStake(b, t),
  },
];

export function skillByName(name: string): SkillDef | undefined {
  return SKILLS.find((s) => s.name === name);
}
