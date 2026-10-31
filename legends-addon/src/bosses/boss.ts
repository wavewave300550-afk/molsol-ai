/**
 * Boss = Being + phases, arena, ultimate scheduling, entrance / transition /
 * death sequences and the HP gates that keep phases from being skipped.
 *
 * Damage handling (main.ts, world.beforeEvents.entityHurt):
 *   - invulnerable windows (entrance, transformations, death) cancel damage;
 *   - damage is scaled by takenMul (shields, exhaustion) and party size;
 *   - HP can never drop below the current phase gate, so every phase and its
 *     transformation is always seen, however hard the boss is hit.
 */
import { Entity, EntityDamageCause, ItemStack, Player, Vector3 } from "@minecraft/server";
import { allPlayersNear, fightersNear } from "../core/combat.js";
import { burst, C, flash, sound } from "../core/fx.js";
import { clearProps } from "../core/hazards.js";
import { notify, Pri } from "../core/notice.js";
import { dist, flatDist } from "../core/vec.js";
import { Being, Co, SkillDef } from "./being.js";

export type BossKey = "taotie" | "nidhogg" | "hanuman" | "alicorn" | "tenko" | "logos";

export abstract class Boss extends Being {
  readonly key: BossKey;
  home: Vector3;
  phase = 0;
  dying = false;
  finalBlow = false;
  noPlayers = 0;
  maxFighters = 1;
  ultAt = 0;
  private skillList?: SkillDef[];

  abstract readonly title: string;
  abstract readonly phaseNames: string[];
  abstract readonly ultName: string;
  abstract readonly thresholds: number[];
  abstract readonly defeatText: string;
  readonly ultPhase: number = 3;
  readonly ultCooldown: number = 900;
  readonly arena: number = 44;
  readonly sigil: string = "";

  abstract skills(): SkillDef[];
  abstract entrance(): Co;
  abstract transition(to: number): Co;
  abstract ultimate(): Co;
  abstract idle(): void;

  constructor(entity: Entity, key: BossKey) {
    super(entity);
    this.key = key;
    this.home = { ...entity.location };
  }

  /** Called by the registry right after construction (subclass fields are ready by then). */
  init(adopted: boolean): this {
    const saved = this.entity.getDynamicProperty("legends:home");
    if (typeof saved === "string") {
      try {
        this.home = JSON.parse(saved) as Vector3;
      } catch {
        // keep current location
      }
    } else {
      this.entity.setDynamicProperty("legends:home", JSON.stringify(this.home));
    }
    if (adopted) {
      let ph = 1;
      try {
        ph = Math.max(1, Number(this.entity.getProperty("legends:phase")) || 1);
      } catch {
        ph = 1;
      }
      this.phase = Math.min(ph, this.thresholds.length + 1);
      this.ultAt = this.t + 200;
      this.prop("act", 0);
      this.prop("fx", 0);
    } else {
      this.invuln = true;
      this.start("entrance", this.wrapEntrance());
    }
    this.onInit(adopted);
    return this;
  }

  /** Subclass hook after init (e.g. restore flight / forms for adopted bosses). */
  protected onInit(adopted: boolean): void {}

  // ---------------------------------------------------------------- text (minimal, see notice.ts)
  audience(): Player[] {
    return allPlayersNear(this.dim, this.pos, 72);
  }

  say(text: string, pri: Pri): void {
    notify(this.audience(), text, pri);
  }

  // ---------------------------------------------------------------- damage model
  /** Lowest HP the boss may currently be brought to. */
  gateHp(): number {
    if (this.finalBlow) return 0;
    if (this.phase >= 1 && this.phase <= this.thresholds.length) return this.maxHp * this.thresholds[this.phase - 1];
    return 1;
  }

  partyMul(): number {
    return 1 / Math.min(3, 1 + 0.5 * (this.maxFighters - 1));
  }

  setPhase(n: number): void {
    this.phase = n;
    this.prop("phase", n);
  }

  // ---------------------------------------------------------------- sequences
  private *wrapEntrance(): Co {
    this.invuln = true;
    this.fx(0);
    yield* this.entrance();
    this.setPhase(1);
    this.invuln = false;
    this.rest = 30;
  }

  private *wrapTransition(to: number): Co {
    this.invuln = true;
    this.fx(1);
    this.say(`§c◆ ${this.phaseNames[to] ?? ""}`, Pri.Phase);
    yield* this.transition(to);
    this.setPhase(to);
    this.fx(0);
    this.invuln = false;
    if (to >= this.ultPhase) this.ultAt = this.t + 40;
    this.rest = 20;
  }

  private *wrapUlt(): Co {
    this.say(`§4⚠ ${this.ultName}`, Pri.Ultimate);
    yield* this.ultimate();
    this.ultAt = this.t + this.ultCooldown;
    this.rest = 40;
  }

  /** Hook: return a coroutine to run instead of dying (Hanuman's revival). */
  protected beforeDeath(): Co | undefined {
    return undefined;
  }

  protected deathCo(): Co {
    return this.wrapDeath();
  }

  private *wrapDeath(): Co {
    this.dying = true;
    this.invuln = true;
    this.fx(1);
    this.say(this.defeatText, Pri.Ultimate);
    const a = this.act("death");
    sound(this.dim, "mob.enderdragon.death", this.pos, 3, 0.8);
    for (let k = 0; k < a.ticks; k += 10) {
      burst(this.dim, { x: this.pos.x, y: this.pos.y + 2, z: this.pos.z }, C.holy, 14, 5, 0.3, 1.2);
      yield 10;
    }
    flash(this.audience(), C.white);
    burst(this.dim, { x: this.pos.x, y: this.pos.y + 2, z: this.pos.z }, C.gold, 40, 9, 0.4, 1.5);
    clearProps(this.id);
    this.finalBlow = true;
    this.invuln = false;
    const killer = this.lastAttacker && this.lastAttacker.isValid ? this.lastAttacker : undefined;
    try {
      if (killer) this.entity.applyDamage(this.hp + 100, { cause: EntityDamageCause.entityAttack, damagingEntity: killer });
      if (this.entity.isValid) this.entity.kill();
    } catch {
      // already gone
    }
  }

  private depart(): void {
    this.say(`§7${this.title} departs…`, Pri.Phase);
    clearProps(this.id);
    if (this.sigil) {
      try {
        this.dim.spawnItem(new ItemStack(this.sigil, 1), this.home);
      } catch {
        // unloaded
      }
    }
    try {
      this.entity.remove();
    } catch {
      // gone
    }
    this.dispose();
  }

  // ---------------------------------------------------------------- main loop
  tick(): void {
    if (!this.valid) {
      this.cleanup();
      return;
    }
    this.t++;
    this.pos = { ...this.entity.location };
    if (this.t % 10 === 0) this.refreshArena();
    if (this.removed) return;
    const h = this.entity.getComponent("minecraft:health");
    if (h) {
      this.hp = h.currentValue;
      this.maxHp = h.effectiveMax;
    }
    if (!this.dying && this.phase >= 1) {
      const busyUlt = this.coName === "ultimate";
      if (this.phase <= this.thresholds.length && this.hp <= this.gateHp() + 0.6 && this.coName !== "transition" && !busyUlt) {
        this.interrupt();
        this.start("transition", this.wrapTransition(this.phase + 1));
      } else if (this.phase > this.thresholds.length && this.hp <= 1.6 && this.coName !== "death" && this.coName !== "revive" && !busyUlt) {
        const alt = this.beforeDeath();
        this.interrupt();
        if (alt) this.start("revive", alt);
        else this.start("death", this.wrapDeath());
      }
    }
    this.pickTarget();
    if (!this.co && !this.dying) {
      if (this.rest > 0) {
        this.rest--;
        this.idle();
      } else {
        this.chooseNext();
      }
    }
    this.stepCo();
    this.onTick();
    this.syncMove();
  }

  /** Per-tick extra behaviour (auras, followers...). */
  protected onTick(): void {}

  protected onCoDone(): void {
    if (this.rest <= 0) this.rest = [0, 30, 24, 18][Math.min(3, this.phase)] ?? 18;
  }

  private refreshArena(): void {
    const near = fightersNear(this.dim, this.home, this.arena + 12);
    const close = fightersNear(this.dim, this.pos, 40);
    const map = new Map<string, Player>();
    for (const p of [...near, ...close]) map.set(p.id, p);
    this.fighters = [...map.values()];
    this.maxFighters = Math.max(this.maxFighters, this.fighters.length);
    if (this.fighters.length === 0 && !this.dying) {
      this.noPlayers += 10;
      if (this.noPlayers >= 1200) this.depart();
    } else {
      this.noPlayers = 0;
    }
  }

  private chooseNext(): void {
    const tgt = this.target;
    if (!tgt) {
      this.idle();
      return;
    }
    if (this.phase >= this.ultPhase && this.t >= this.ultAt) {
      this.start("ultimate", this.wrapUlt());
      return;
    }
    this.skillList ??= this.skills();
    const d = dist(this.pos, tgt.location);
    const ok = this.skillList.filter((s) => s.phases.includes(this.phase) && this.cdReady(s.name) &&
      (s.min === undefined || d >= s.min) && (s.max === undefined || d <= s.max) && (!s.when || s.when()));
    if (!ok.length) {
      this.rest = 6;
      this.idle();
      return;
    }
    let r = Math.random() * ok.reduce((a, s) => a + s.weight, 0);
    let chosen = ok[0];
    for (const s of ok) {
      r -= s.weight;
      if (r <= 0) {
        chosen = s;
        break;
      }
    }
    this.setCd(chosen.name, chosen.cd);
    this.start(chosen.name, chosen.run(tgt));
  }

  /** Is the boss too far from home? (idle movement brings it back) */
  leashed(): boolean {
    return flatDist(this.pos, this.home) > this.arena;
  }

  cleanup(): void {
    clearProps(this.id);
    this.dispose();
  }
}
