import { Player } from "@minecraft/server";
import { TUNING } from "../config.js";
import { fightersNear } from "../core/targets.js";
import { lineClear } from "../core/terrain.js";
import { add, hdist, len, sub, v, V3 } from "../core/vec.js";
import { Path } from "../paths/path.js";
import type { JoanBoss, SkillGen } from "./joan.js";
import { SKILLS, SkillDef } from "./skills/index.js";

/** What Joan has learned about one player during this fight. */
export interface Obs {
  ranged: number; // drawing bows / landing projectiles (decays)
  melee: number; // melee hits on her (decays)
  caught: number; // times a road carried them
  jumps: number; // times they jumped a road
  still: number; // ticks standing still
  kiting: number; // >0 while running away
  drawing: boolean;
  lastPos: V3;
  los: boolean;
  dist: number;
  onRoad?: Path;
  lastJumpCheck: number;
}

export interface Choice {
  def: SkillDef;
  gen: SkillGen;
  combo: boolean;
}

export interface ComboHint {
  skill: string;
  until: number;
  reason: string;
  data?: unknown;
}

export class Brain {
  b: JoanBoss;
  target?: Player;
  obs = new Map<string, Obs>();
  engaged = 1;
  lastThink = 0;
  targetSince = 0;
  combo?: ComboHint;
  forced?: string;
  lastChoice = "";
  bigSkillsInRow = 0;

  constructor(b: JoanBoss) {
    this.b = b;
  }

  obsOf(p: Player): Obs {
    let o = this.obs.get(p.id);
    if (!o) {
      o = { ranged: 0, melee: 0, caught: 0, jumps: 0, still: 0, kiting: 0, drawing: false, lastPos: { ...p.location }, los: true,
        dist: 99, lastJumpCheck: 0 };
      this.obs.set(p.id, o);
    }
    return o;
  }

  // ------------------------------------------------------------------ perception
  observe(now: number): void {
    if (now - this.lastThink < TUNING.thinkInterval) return;
    const dt = Math.max(1, now - this.lastThink);
    this.lastThink = now;
    const b = this.b;
    const fighters = b.fighters();
    for (const p of fightersNear(b.dim, b.pos, 24)) if (!fighters.some((f) => f.id === p.id)) fighters.push(p);
    this.engaged = Math.max(1, fighters.length);
    const head = add(b.pos, v(0, 1.9, 0));
    const ground = b.field.activePaths().filter((p) => !p.o.aerial && p.o.kind !== "ring");
    for (const p of fighters) {
      const o = this.obsOf(p);
      o.ranged *= 0.985;
      o.melee *= 0.98;
      o.jumps *= 0.995;
      o.caught *= 0.997;
      const moved = sub(p.location, o.lastPos);
      const speed = len(v(moved.x, 0, moved.z)) / dt;
      if (speed < 0.03) o.still += dt;
      else o.still = 0;
      const toJoan = sub(b.pos, p.location);
      const away = -(moved.x * toJoan.x + moved.z * toJoan.z) / (len(v(toJoan.x, 0, toJoan.z)) || 1) / dt;
      o.kiting = o.kiting * 0.8 + (away > 0.12 ? 1 : away < -0.05 ? -0.5 : 0) * 0.2 * 5;
      o.lastPos = { ...p.location };
      o.dist = hdist(b.pos, p.location);
      o.los = lineClear(b.dim, head, add(p.location, v(0, 1.5, 0)));
      o.onRoad = b.field.riderPath(p);
      // jumping over roads: airborne right above a ground road without being carried
      if (!p.isOnGround && !o.onRoad && now - o.lastJumpCheck > 20) {
        for (const r of ground) {
          if (!r.inBounds(p.location, 1.2)) continue;
          const n = r.nearest(p.location);
          if (n.dh < 1.4 && n.dy > 0.6 && n.dy < 2.6) {
            o.jumps += 1;
            o.lastJumpCheck = now;
            break;
          }
        }
      }
    }
    this.pickTarget(now, fighters);
  }

  private pickTarget(now: number, fighters: Player[]): void {
    const cur = this.target;
    const inReach = (p: Player) => hdist(p.location, this.b.home) < TUNING.leashRadius + 6 || hdist(p.location, this.b.pos) < 24;
    const curOk = cur && cur.isValid && fighters.some((f) => f.id === cur.id) && inReach(cur);
    if (curOk && now - this.targetSince < 20 * 15) return;
    let best: Player | undefined;
    let bestScore = -Infinity;
    for (const p of fighters) {
      if (!inReach(p)) continue;
      const o = this.obsOf(p);
      const dmg = this.b.participants.get(p.id) ?? 0;
      const score = 40 / (1 + o.dist) + o.melee * 2 + o.ranged * 1.5 + dmg * 0.04 + (cur && p.id === cur.id ? 3 : 0);
      if (score > bestScore) {
        bestScore = score;
        best = p;
      }
    }
    if (best && (!cur || best.id !== cur.id)) this.targetSince = now;
    this.target = best;
  }

  noteRanged(p: Player, amount: number): void {
    this.obsOf(p).ranged += amount;
  }

  noteMelee(p: Player): void {
    this.obsOf(p).melee += 1;
  }

  noteCaught(p: Player): void {
    this.obsOf(p).caught += 1;
  }

  // ------------------------------------------------------------------ decision
  choose(now: number): Choice | undefined {
    const b = this.b;
    const t = this.target;
    if (!t || !t.isValid) return undefined;
    const o = this.obsOf(t);
    const phase = b.phase >= 2 ? 2 : 1;
    // forced (debug command) skill
    if (this.forced) {
      const def = SKILLS.find((s) => s.name === this.forced);
      this.forced = undefined;
      if (def) return { def, gen: def.run(b, t, undefined), combo: false };
    }
    // a combo prepared by the previous skill skips the global cooldown
    const combo = this.combo;
    this.combo = undefined;
    if (combo && combo.until >= now) {
      const def = SKILLS.find((s) => s.name === combo.skill);
      if (def && def.phases.includes(phase)) {
        b.stats.combos++;
        b.stats.chosen[def.name] = (b.stats.chosen[def.name] ?? 0) + 1;
        return { def, gen: def.run(b, t, combo.data), combo: true };
      }
    }
    if (now < b.gcdUntil) return undefined;
    const options: { def: SkillDef; score: number }[] = [];
    for (const def of SKILLS) {
      if (!def.phases.includes(phase) || !b.ready(def.name) || def.name === "stake") continue;
      let score = def.score(b, t, o, this);
      if (score <= 0) continue;
      if (def.name === this.lastChoice && def.name !== "melee") score *= 0.15;
      if (def.big && this.bigSkillsInRow >= 2) score *= 0.2;
      options.push({ def, score });
    }
    if (!options.length) return undefined;
    options.sort((a, c) => c.score - a.score);
    // weighted pick among the best three keeps her readable but not robotic
    const top = options.slice(0, 3);
    const total = top.reduce((s, x) => s + x.score, 0);
    let r = Math.random() * total;
    let pick = top[0];
    for (const x of top) {
      r -= x.score;
      if (r <= 0) {
        pick = x;
        break;
      }
    }
    this.lastChoice = pick.def.name;
    b.stats.chosen[pick.def.name] = (b.stats.chosen[pick.def.name] ?? 0) + 1;
    this.bigSkillsInRow = pick.def.big ? this.bigSkillsInRow + 1 : 0;
    return { def: pick.def, gen: pick.def.run(b, t, undefined), combo: false };
  }

  /** Prepare a follow-up that runs right after the current skill if still valid. */
  queueCombo(skill: string, reason: string, ticks = 40, data?: unknown): void {
    this.combo = { skill, until: this.b.now + ticks, reason, data };
  }
}
