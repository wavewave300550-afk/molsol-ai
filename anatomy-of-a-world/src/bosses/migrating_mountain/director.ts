/**
 * The mountain's "AI": it reads where the players are (dorsal surface, Organ
 * Cavern, underbelly, Phase 2 disk), what it has used recently and how hurt
 * it is, then picks one main ability at a time. Geological Shedding runs as a
 * secondary barrage alongside, and Phase 2 guarantees regular openings of the
 * Lithic Heart so the fight never stalls.
 */
import { Player } from "@minecraft/server";
import { Co, Task } from "../../core/tasks.js";
import { V3 } from "../../core/vec.js";
import { AbilityId, continentalFold, geologicalShedding, invertedStrata, lithicPeristalsis, mantleContraction, resonanceNetwork } from "./abilities.js";
import { MMContext, Zone } from "./context.js";
import { foldStep, heartPull, islandCrack, islandFlip, marchWave, mineralBeams, slamRings } from "./phase3.js";

interface Option {
  id: AbilityId;
  weight: number;
  run: () => Co;
}

const COOLDOWN: Partial<Record<AbilityId, number>> = {
  continental_fold: 340,
  lithic_peristalsis: 300,
  geological_shedding: 220,
  resonance_network: 360,
  inverted_strata: 420,
  mantle_contraction: 640,
};

export class Director {
  private ready = new Map<AbilityId, number>();
  private main?: Task;
  private secondary?: Task;
  private nextMain = 0;
  private nextSecondary = 0;
  private lastTarget = "";
  lastExposure = 0;
  aggression = 1;
  history: AbilityId[] = [];

  constructor(
    private readonly ctx: MMContext,
    private readonly pockets: () => V3[],
  ) {}

  reset(now: number, delay = 60): void {
    this.main?.cancel();
    this.secondary?.cancel();
    this.main = undefined;
    this.secondary = undefined;
    this.nextMain = now + delay;
    this.nextSecondary = now + delay + 160;
    this.lastExposure = now;
  }

  get busy(): boolean {
    return !!this.main && !this.main.done;
  }

  update(): void {
    const ctx = this.ctx;
    const now = ctx.now;
    const players = ctx.combatants();
    if (!players.length) return;
    if (this.main && this.main.done) {
      this.main = undefined;
      const gap = ctx.phase >= 2 ? (ctx.enraged() ? 26 : 46) : 78;
      this.nextMain = now + Math.round((gap + ctx.rng() * gap * 0.6) / this.aggression);
    }
    // Phase 3B: no new attack while the heart is down on the centre island (that is the players' window)
    if (!this.main && now >= this.nextMain && !ctx.heartSlamming()) this.startMain(players);
    if ((!this.secondary || this.secondary.done) && now >= this.nextSecondary && (this.ready.get("geological_shedding") ?? 0) <= now) {
      const targets = players.filter((p) => {
        const z = ctx.zoneOf(p);
        return z !== "cavern" && z !== "other";
      });
      if (targets.length) {
        this.secondary = ctx.tasks.start("mm:ability:shedding", geologicalShedding(ctx, shuffle(targets, ctx.rng)));
        this.ready.set("geological_shedding", now + Math.round(COOLDOWN.geological_shedding! / this.aggression));
        this.history.push("geological_shedding");
      }
      this.nextSecondary = now + Math.round((ctx.phase >= 2 ? 180 : 260) / this.aggression);
    }
  }

  private startMain(players: Player[]): void {
    const ctx = this.ctx;
    const target = this.pickTarget(players);
    const zone = ctx.zoneOf(target);
    const opts = this.options(target, zone);
    const now = ctx.now;
    let usable = opts.filter((o) => (this.ready.get(o.id) ?? 0) <= now && o.weight > 0);
    // Phase 2 pacing: if the heart has stayed shut too long, force an opening ability
    if (ctx.phase === 2 && now - this.lastExposure > 640) {
      const opening = usable.filter((o) => o.id === "resonance_network" || o.id === "mantle_contraction");
      if (opening.length) usable = opening;
    }
    if (!usable.length) {
      this.nextMain = now + 20;
      return;
    }
    // avoid repeating the previous ability
    const last = this.history[this.history.length - 1];
    if (usable.length > 1) usable = usable.filter((o) => o.id !== last);
    const total = usable.reduce((s, o) => s + o.weight, 0);
    let r = ctx.rng() * total;
    let pick = usable[0];
    for (const o of usable) {
      r -= o.weight;
      if (r <= 0) {
        pick = o;
        break;
      }
    }
    this.main = ctx.tasks.start(`mm:ability:${pick.id}`, pick.run());
    this.ready.set(pick.id, now + Math.round((COOLDOWN[pick.id] ?? 300) / this.aggression));
    this.history.push(pick.id);
    if (this.history.length > 20) this.history.shift();
  }

  /** Force a specific ability (test command). */
  force(id: AbilityId, target: Player | undefined): boolean {
    const players = this.ctx.combatants();
    const t = target ?? players[0] ?? this.ctx.audience()[0];
    if (!t) return false;
    const o = this.options(t, this.ctx.zoneOf(t), true).find((x) => x.id === id);
    if (!o) return false;
    this.main?.cancel();
    this.main = this.ctx.tasks.start(`mm:ability:${id}`, o.run());
    this.history.push(id);
    return true;
  }

  private pickTarget(players: Player[]): Player {
    const ctx = this.ctx;
    const pool = players.length > 1 ? players.filter((p) => p.id !== this.lastTarget) : players;
    const t = pool[Math.floor(ctx.rng() * pool.length)];
    this.lastTarget = t.id;
    return t;
  }

  private options(target: Player, zone: Zone, any = false): Option[] {
    const ctx = this.ctx;
    if (ctx.phase === 3) return this.phase3Options(target, any);
    const nodes = ctx.livingNodes();
    const near = (id: string, r: number) => nodes.some((n) => n.site.id === id && Math.hypot(n.entity.location.x - target.location.x, n.entity.location.z - target.location.z) < r);
    const all: Option[] = [
      { id: "continental_fold", weight: 0, run: () => continentalFold(ctx, target) },
      { id: "lithic_peristalsis", weight: 0, run: () => lithicPeristalsis(ctx, target) },
      { id: "geological_shedding", weight: 0, run: () => geologicalShedding(ctx, [target, ...ctx.combatants().filter((p) => p !== target)]) },
      { id: "resonance_network", weight: 0, run: () => resonanceNetwork(ctx, target) },
      { id: "inverted_strata", weight: 0, run: () => invertedStrata(ctx, target) },
      { id: "mantle_contraction", weight: 0, run: () => mantleContraction(ctx, this.pockets()) },
    ];
    const w = (id: AbilityId, v: number) => {
      const o = all.find((x) => x.id === id);
      if (o) o.weight = v;
    };
    if (any) {
      for (const o of all) o.weight = 1;
      return all;
    }
    if (ctx.phase === 1) {
      if (zone === "dorsal" || zone === "arrival") {
        w("continental_fold", 3);
        w("lithic_peristalsis", 3);
        w("inverted_strata", 2.5);
        if (near("dorsal", 34) && nodes.length) w("resonance_network", 2.5);
      } else if (zone === "cavern") {
        w("mantle_contraction", 4);
        if (near("cavern", 30)) w("resonance_network", 2.5);
      } else if (zone === "under") {
        if (near("root", 24)) w("resonance_network", 3);
        w("geological_shedding", 2);
      }
    } else {
      w("continental_fold", 2.5);
      w("lithic_peristalsis", 2.5);
      w("inverted_strata", 2);
      w("resonance_network", 2.5);
      w("mantle_contraction", 2);
      if (zone === "mantle") w("geological_shedding", 2);
    }
    return all;
  }

  /** Phase 3 forms of the abilities: 3A on the walking disk, 3B on the floating islands. */
  private phase3Options(target: Player, any: boolean): Option[] {
    const ctx = this.ctx;
    const others = () => [target, ...ctx.combatants().filter((p) => p !== target)];
    let all: Option[];
    if (ctx.arena() === "islands") {
      all = [
        { id: "continental_fold", weight: 2, run: () => islandCrack(ctx, target) },
        { id: "lithic_peristalsis", weight: 1.5, run: () => slamRings(ctx, 2, true) },
        { id: "geological_shedding", weight: 0, run: () => geologicalShedding(ctx, others()) },
        { id: "resonance_network", weight: 3, run: () => mineralBeams(ctx, target) },
        { id: "inverted_strata", weight: 2, run: () => islandFlip(ctx, target) },
        { id: "mantle_contraction", weight: 1.5, run: () => heartPull(ctx) },
      ];
    } else {
      const anchors = ctx.anchors();
      const dist = (a: { pos: V3 }) => Math.hypot(a.pos.x - target.location.x, a.pos.z - target.location.z);
      const nearest = anchors.length ? anchors.reduce((a, b) => (dist(a) < dist(b) ? a : b)) : undefined;
      all = [
        { id: "continental_fold", weight: 2.5, run: () => foldStep(ctx, target) },
        { id: "lithic_peristalsis", weight: 2.5, run: () => marchWave(ctx, 3, 6) },
        { id: "geological_shedding", weight: 0, run: () => geologicalShedding(ctx, others()) },
        { id: "resonance_network", weight: nearest ? 2.5 : 0, run: () => resonanceNetwork(ctx, target, nearest) },
        { id: "inverted_strata", weight: 2, run: () => invertedStrata(ctx, target) },
        { id: "mantle_contraction", weight: 1.5, run: () => mantleContraction(ctx, []) },
      ];
    }
    if (any) for (const o of all) o.weight = 1;
    return all;
  }
}

function shuffle<T>(a: T[], rng: () => number): T[] {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
}
