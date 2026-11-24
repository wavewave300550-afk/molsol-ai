/**
 * The fight: summoning, entering and leaving the Fractured Mandate (a real
 * custom dimension), the intro, the battle loop, defeat, victory and every
 * edge case around them (deaths, respawns, disconnects, reloads).
 */
import {
  Difficulty, Dimension, EasingType, Entity, EntityDamageCause, GameMode, InputPermissionCategory, ItemStack, Player, system,
  Vector3, world,
} from "@minecraft/server";
import { Arena, arena } from "../arena/arena.js";
import { ACT, ARENA, BOSS, DIM_ID, DMG, ENT, FOG, FX, ITEM, PROP, SND, WORLD_PROP } from "../config.js";
import { particle, playerSound, sound, telegraph } from "../core/fx.js";
import { later, spawnTask, wait } from "../core/tasks.js";
import { add, dist, distXZ, norm, sub, v } from "../core/vec.js";
import { BossHooks, Emperor } from "../boss/emperor.js";
import * as F from "../boss/fragments.js";

export type FightState = "idle" | "preparing" | "intro" | "battle" | "victory" | "ending";

interface ReturnPoint {
  d: string;
  x: number;
  y: number;
  z: number;
  ry: number;
}

const PHASE_NAMES = ["", "I - The Unbroken Court", "II - Kintsugi", "III - The Fractured Mandate"];
const DIFF_MULT: Record<string, number> = {
  [Difficulty.Peaceful]: 0.5,
  [Difficulty.Easy]: 0.65,
  [Difficulty.Normal]: 1.0,
  [Difficulty.Hard]: 1.35,
};

export class FightSession {
  state: FightState = "idle";
  readonly participants = new Set<string>();
  boss?: Emperor;
  A?: Arena;
  private graceUntil = 0;
  private victoryAt = 0;
  private lastBar = 0;
  private summonerId = "";
  private staleCleanup = false;
  private respawnPrompted = new Set<string>();
  private deaths: { loc: Vector3; dim: Dimension; home: Vector3; until: number }[] = [];
  /** Set by the UI module (avoids an import cycle). */
  respawnPrompt?: (p: Player) => void;

  // ------------------------------------------------------------------ helpers

  get active(): boolean {
    return this.state !== "idle";
  }

  inMandate(p: Entity): boolean {
    try {
      return p.dimension.id === this.mandate().id;
    } catch {
      return false;
    }
  }

  mandate(): Dimension {
    return world.getDimension(DIM_ID);
  }

  /** Participants who are in the arena and alive. */
  present(): Player[] {
    const out: Player[] = [];
    for (const p of world.getPlayers()) {
      if (!this.participants.has(p.id) || !this.inMandate(p)) continue;
      try {
        const h = p.getComponent("minecraft:health");
        if (h && h.currentValue <= 0) continue;
        if (p.getGameMode() === GameMode.Spectator) continue;
      } catch {
        continue;
      }
      out.push(p);
    }
    return out;
  }

  inArenaPlayers(): Player[] {
    return world.getPlayers().filter((p) => this.inMandate(p));
  }

  private difficulty(): number {
    try {
      return DIFF_MULT[world.getDifficulty()] ?? 1;
    } catch {
      return 1;
    }
  }

  hurt(p: Player, amount: number, from?: Vector3, push = 0.8, lift = 0.3): void {
    try {
      const opts = this.boss?.valid
        ? { cause: EntityDamageCause.entityAttack, damagingEntity: this.boss.e }
        : { cause: EntityDamageCause.entityAttack };
      p.applyDamage(amount * this.difficulty(), opts);
      if (from && (push !== 0 || lift !== 0)) {
        const d = norm(v(p.location.x - from.x, 0, p.location.z - from.z));
        p.applyKnockback({ x: d.x * push, z: d.z * push }, lift);
      }
    } catch {
      // player left or died this tick
    }
  }

  title(text: string, sub?: string, stay = 50, who: Player[] = this.inArenaPlayers()): void {
    for (const p of who) {
      try {
        p.onScreenDisplay.setTitle(text, { subtitle: sub ?? "", fadeInDuration: 6, stayDuration: stay, fadeOutDuration: 12 });
      } catch {
        // ignore
      }
    }
  }

  actionbar(text: string): void {
    this.lastBar = system.currentTick;
    for (const p of this.inArenaPlayers()) {
      try {
        p.onScreenDisplay.setActionBar(text);
      } catch {
        // ignore
      }
    }
  }

  private hooks(): BossHooks {
    return {
      players: () => this.present(),
      hurt: (p, a, f, push, lift) => this.hurt(p, a, f, push, lift),
      title: (t, s, stay) => this.title(t, s, stay),
      actionbar: (t) => this.actionbar(t),
      onDefeated: () => this.onBossDefeated(),
      onPhase: (n) => this.onPhase(n),
    };
  }

  // ------------------------------------------------------------------ return points

  private saveReturn(p: Player): void {
    if (this.inMandate(p)) return;
    const rp: ReturnPoint = {
      d: p.dimension.id,
      x: p.location.x,
      y: p.location.y,
      z: p.location.z,
      ry: p.getRotation().y,
    };
    p.setDynamicProperty(WORLD_PROP.returnPoint, JSON.stringify(rp));
  }

  returnPointOf(p: Player): { dim: Dimension; loc: Vector3; ry: number } {
    const raw = p.getDynamicProperty(WORLD_PROP.returnPoint);
    if (typeof raw === "string") {
      try {
        const rp = JSON.parse(raw) as ReturnPoint;
        return { dim: world.getDimension(rp.d), loc: v(rp.x, rp.y, rp.z), ry: rp.ry };
      } catch {
        // fall through
      }
    }
    const sp = p.getSpawnPoint();
    if (sp) return { dim: sp.dimension, loc: v(sp.x + 0.5, sp.y, sp.z + 0.5), ry: 0 };
    const ws = world.getDefaultSpawnLocation();
    return { dim: world.getDimension("overworld"), loc: v(ws.x + 0.5, ws.y > 320 ? 120 : ws.y, ws.z + 0.5), ry: 0 };
  }

  // ------------------------------------------------------------------ entering / leaving

  enter(p: Player, intro: boolean): void {
    const A = this.A;
    if (!A) return;
    // a fighter who fell and comes back keeps the place they first entered from
    const rejoining = this.participants.has(p.id) && p.getDynamicProperty(WORLD_PROP.returnPoint) !== undefined;
    if (!rejoining) this.saveReturn(p);
    this.participants.add(p.id);
    this.respawnPrompted.delete(p.id);
    const k = [...this.participants].indexOf(p.id);
    const spread = (k % 5) - 2;
    const spot = A.standAt(ARENA.arrival.x + spread * 2, ARENA.arrival.z + (k >= 5 ? 2 : 0));
    try {
      p.camera.fade({ fadeColor: { red: 1, green: 0.95, blue: 0.85 }, fadeTime: { fadeInTime: 0.3, holdTime: 0.6, fadeOutTime: 1.6 } });
    } catch {
      // ignore
    }
    later(6, () => {
      if (!p.isValid) return;
      p.teleport(spot, { dimension: A.dim, rotation: { x: 0, y: 180 }, keepVelocity: false });
      p.addEffect("resistance", intro ? 140 : 60, { amplifier: 4, showParticles: false });
      try {
        p.fogSettings.remove(FOG.tag);
        p.fogSettings.push(A.fractured ? FOG.fractured : FOG.mandate, FOG.tag);
      } catch {
        // ignore
      }
      try {
        p.playMusic(SND.music, { loop: true, fade: 2.0, volume: 0.8 });
      } catch {
        // ignore
      }
      if (!intro) {
        p.onScreenDisplay.setTitle("§6The Fractured Mandate", { subtitle: "§7The Emperor awaits", fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 10 });
      }
    });
  }

  returnHome(p: Player, why = ""): void {
    const home = this.returnPointOf(p);
    try {
      p.fogSettings.remove(FOG.tag);
    } catch {
      // ignore
    }
    try {
      p.stopMusic();
      p.camera.clear();
      p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, true);
    } catch {
      // ignore
    }
    try {
      p.camera.fade({ fadeColor: { red: 1, green: 0.95, blue: 0.85 }, fadeTime: { fadeInTime: 0.2, holdTime: 0.4, fadeOutTime: 1.2 } });
    } catch {
      // ignore
    }
    if (this.inMandate(p)) {
      try {
        p.teleport(home.loc, { dimension: home.dim, rotation: { x: 0, y: home.ry }, keepVelocity: false });
        p.addEffect("slow_falling", 100, { amplifier: 0, showParticles: false });
      } catch (e) {
        console.warn(`[porcelain] could not return ${p.name}: ${e}`);
      }
    }
    p.setDynamicProperty(WORLD_PROP.returnPoint, undefined);
    this.participants.delete(p.id);
    if (why) p.sendMessage(why);
  }

  // ------------------------------------------------------------------ starting

  async start(summoner: Player, consumeSeal: boolean): Promise<void> {
    if (this.state !== "idle") {
      summoner.sendMessage("§7The Mandate is already broken open. Use the seal again to join the battle.");
      return;
    }
    if (this.inMandate(summoner)) return;
    this.state = "preparing";
    world.setDynamicProperty(WORLD_PROP.fight, true);
    this.participants.clear();
    this.summonerId = summoner.id;
    const party = world.getPlayers().filter((p) => p.dimension.id === summoner.dimension.id && dist(p.location, summoner.location) <= 12);
    if (consumeSeal && !takeSeal(summoner)) {
      this.state = "idle";
      world.setDynamicProperty(WORLD_PROP.fight, false);
      return;
    }
    for (const p of party) {
      this.participants.add(p.id);
      this.saveReturn(p);
      p.onScreenDisplay.setTitle("§6The seal cracks...", { subtitle: "§7The Fractured Mandate unfolds", fadeInDuration: 5, stayDuration: 60, fadeOutDuration: 10 });
      playerSound(p, SND.crack, 1, 0.8);
      playerSound(p, SND.gong, 0.8, 1);
    }
    particle(summoner.dimension, FX.goldBurst, add(summoner.location, v(0, 1, 0)));
    telegraph(summoner.dimension, summoner.location, 3, 3, { red: 1, green: 0.8, blue: 0.3 });

    const A = arena();
    this.A = A;
    const loaded = await A.load();
    if (!loaded) {
      this.abort(summoner, consumeSeal, "§cThe Mandate refused to open (the arena could not be loaded). Your seal is returned.");
      return;
    }
    removeStrays(A.dim);
    await A.build();
    if (this.state !== "preparing") return;
    F.clearAll();
    F.initFragments({
      arena: A,
      players: () => this.present(),
      hurt: (p, a, f, push, lift) => this.hurt(p, a, f, push, lift),
      phase: () => this.boss?.phase ?? 1,
      bossPos: () => (this.boss?.valid ? this.boss.pos : undefined),
    });
    let e: Entity;
    try {
      e = A.dim.spawnEntity(ENT.emperor, A.w(0.5, 3.8, -21.5));
    } catch (err) {
      this.abort(summoner, consumeSeal, `§cThe Emperor could not be summoned: ${err}`);
      return;
    }
    e.setProperty(PROP.phase, 1);
    e.setProperty(PROP.action, ACT.PERCH);
    e.setProperty(PROP.plates, BOSS.plates);
    this.boss = new Emperor(e, A, this.hooks(), 0);
    this.state = "intro";
    for (const id of this.participants) {
      const p = world.getEntity(id);
      if (p instanceof Player) this.enter(p, true);
    }
    spawnTask("fight:intro", this.intro());
  }

  private abort(summoner: Player, refund: boolean, msg: string): void {
    this.state = "idle";
    world.setDynamicProperty(WORLD_PROP.fight, false);
    if (refund && summoner.isValid) giveItem(summoner, new ItemStack(ITEM.seal, 1));
    for (const id of this.participants) {
      const p = world.getEntity(id);
      if (p instanceof Player) p.setDynamicProperty(WORLD_PROP.returnPoint, undefined);
    }
    this.participants.clear();
    summoner.sendMessage(msg);
  }

  private *intro(): Generator<void, void, void> {
    const A = this.A!;
    const boss = this.boss!;
    yield* wait(8);
    const who = (): Player[] => this.inArenaPlayers();
    for (const p of who()) {
      try {
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, false);
        p.camera.setCamera("minecraft:free", { location: A.w(0.5, 5.5, 6), facingLocation: A.w(0.5, 4, -21) });
        p.camera.setCamera("minecraft:free", {
          location: A.w(4.5, 3.2, -9),
          facingLocation: A.w(0.5, 5, -21),
          easeOptions: { easeTime: 4.0, easeType: EasingType.InOutSine },
        });
      } catch {
        // ignore
      }
    }
    this.title("§6§lTHE PORCELAIN EMPEROR", "§7Dragon of the Fractured Mandate", 80);
    sound(A.dim, SND.gong, A.center, 2, 0.8);
    yield* wait(20);
    boss.run("awaken", boss.awaken());
    yield* wait(70);
    for (const p of who()) {
      try {
        p.camera.clear();
        p.inputPermissions.setPermissionCategory(InputPermissionCategory.Movement, true);
      } catch {
        // ignore
      }
    }
    yield* wait(12);
    this.state = "battle";
    this.actionbar("§6Shatter the Emperor - and every shard it sheds.");
    boss.forceSkill("procession");
  }

  // ------------------------------------------------------------------ battle loop

  tick(): void {
    if (this.staleCleanup) {
      this.staleCleanup = false;
      void this.cleanStale();
    }
    if (this.state === "idle" || this.state === "preparing") return;
    const A = this.A;
    if (!A) return;
    const now = system.currentTick;
    if (this.boss && (this.state === "intro" || this.state === "battle")) {
      if (this.boss.valid) this.boss.tick();
      else if (this.state === "battle" && !this.boss.dying) {
        // the Emperor vanished (killed by a command or another add-on)
        this.onBossDefeated(false);
      }
    }
    F.tickFragments();
    A.tick();
    if (now % 4 === 0) this.safetyNet();
    if (now % 10 === 0) {
      for (const p of this.present()) {
        if (A.isGilded(sub(p.location, v(0, 0.5, 0)))) {
          try {
            p.addEffect("slowness", 20, { amplifier: 1, showParticles: false });
          } catch {
            // ignore
          }
        }
      }
    }
    if (now % 20 === 0) {
      if (this.state === "battle") this.presenceCheck();
      if (this.state === "battle" && this.boss && now - this.lastBar > 50) this.hud();
      if (this.state === "victory") this.victoryTick();
    }
    if (this.state === "victory" && now % 5 === 0) this.gateCheck();
  }

  private hud(): void {
    const b = this.boss;
    if (!b) return;
    const shards = F.embeddedCount();
    const vul = b.vulnerable ? "  §c§lEXPOSED" : "";
    const txt = `§6Phase ${PHASE_NAMES[b.phase]}§r  §8|  §eShards in the court: ${shards}${vul}`;
    for (const p of this.inArenaPlayers()) {
      try {
        p.onScreenDisplay.setActionBar(txt);
      } catch {
        // ignore
      }
    }
  }

  private safetyNet(): void {
    const A = this.A!;
    for (const p of this.inArenaPlayers()) {
      if (p.location.y >= A.floorY + ARENA.fallLimit) continue;
      const spot = A.safeSpot(p.location);
      try {
        p.teleport(spot, { keepVelocity: false });
        if (this.state === "battle") {
          p.applyDamage(DMG.fall * this.difficulty(), { cause: EntityDamageCause.void });
          p.addEffect("slowness", 40, { amplifier: 1, showParticles: false });
          p.onScreenDisplay.setTitle(" ", { subtitle: "§6The Mandate casts you back", fadeInDuration: 2, stayDuration: 30, fadeOutDuration: 8 });
        }
        particle(A.dim, FX.goldBurst, add(spot, v(0, 1, 0)));
      } catch {
        // ignore
      }
    }
  }

  private presenceCheck(): void {
    const here = this.present();
    if (here.length || this.boss?.dying) {
      this.graceUntil = 0;
      return;
    }
    const now = system.currentTick;
    if (!this.graceUntil) {
      this.graceUntil = now + 600;
      return;
    }
    if (now >= this.graceUntil) this.defeat();
  }

  private onPhase(n: number): void {
    const A = this.A;
    if (!A) return;
    if (n >= 3) {
      for (const p of this.inArenaPlayers()) {
        try {
          p.fogSettings.remove(FOG.tag);
          p.fogSettings.push(FOG.fractured, FOG.tag);
          p.runCommand("camerashake add @s 0.6 2.5 rotational");
        } catch {
          // ignore
        }
      }
    } else {
      for (const p of this.inArenaPlayers()) {
        try {
          p.runCommand("camerashake add @s 0.4 1.5 rotational");
        } catch {
          // ignore
        }
      }
    }
  }

  // ------------------------------------------------------------------ deaths, respawns, joins

  onPlayerDeath(p: Player): void {
    if (!this.inMandate(p)) return;
    // the Emperor has no use for your belongings: they are sent back to where you entered
    const home = this.returnPointOf(p);
    this.deaths.push({ loc: { ...p.location }, dim: home.dim, home: home.loc, until: system.currentTick + 40 });
    later(3, () => this.returnDrops());
    later(30, () => this.returnDrops());
  }

  /** Every dropped item near a recent death goes to the home of the player who died closest to it. */
  private returnDrops(): void {
    const now = system.currentTick;
    this.deaths = this.deaths.filter((d) => d.until >= now);
    if (!this.deaths.length) return;
    const dim = this.A?.dim ?? this.mandate();
    const seen = new Set<string>();
    for (const d of this.deaths) {
      let ents: Entity[] = [];
      try {
        ents = dim.getEntities({ location: d.loc, maxDistance: 6 });
      } catch {
        continue;
      }
      for (const e of ents) {
        if (seen.has(e.id)) continue;
        seen.add(e.id);
        try {
          if (!e.getComponent("minecraft:item") && e.typeId !== "minecraft:xp_orb") continue;
          let best = d;
          for (const o of this.deaths) if (dist(o.loc, e.location) < dist(best.loc, e.location)) best = o;
          e.teleport(best.home, { dimension: best.dim, keepVelocity: false });
        } catch {
          // ignore
        }
      }
    }
  }

  onPlayerSpawn(p: Player, initial: boolean): void {
    if (this.inMandate(p)) {
      if (!this.active || !this.participants.has(p.id)) {
        // joined a world while standing in a Mandate that is no longer open
        later(10, () => {
          if (p.isValid) this.returnHome(p, "§7The Mandate has closed. You are returned to where you entered.");
        });
      } else if (initial) {
        try {
          p.fogSettings.push(this.A?.fractured ? FOG.fractured : FOG.mandate, FOG.tag);
          p.playMusic(SND.music, { loop: true, fade: 2.0, volume: 0.8 });
        } catch {
          // ignore
        }
      }
      return;
    }
    try {
      p.fogSettings.remove(FOG.tag);
    } catch {
      // ignore
    }
    if (!initial && this.participants.has(p.id) && (this.state === "battle" || this.state === "intro") && !this.respawnPrompted.has(p.id)) {
      this.respawnPrompted.add(p.id);
      try {
        p.stopMusic();
      } catch {
        // ignore
      }
      later(40, () => {
        if (p.isValid) this.respawnPrompt?.(p);
      });
    } else if (!this.active && p.getDynamicProperty(WORLD_PROP.returnPoint) !== undefined) {
      p.setDynamicProperty(WORLD_PROP.returnPoint, undefined);
    }
  }

  join(p: Player): boolean {
    if (this.state !== "battle" && this.state !== "intro") return false;
    if (this.inMandate(p)) return false;
    this.enter(p, false);
    return true;
  }

  // ------------------------------------------------------------------ endings

  defeat(): void {
    if (this.state !== "battle") return;
    this.state = "ending";
    const boss = this.boss;
    if (boss?.valid) {
      boss.interrupt();
      boss.setAction(ACT.REPAIR);
      boss.battle = false;
    }
    for (const id of this.participants) {
      const p = world.getEntity(id);
      if (p instanceof Player) p.sendMessage("§6The Emperor endures. §7The Mandate seals itself until the next seal is broken.");
    }
    if (this.A) sound(this.A.dim, SND.hum, this.A.center, 2, 0.7);
    later(80, () => this.cleanup());
  }

  onBossDefeated(byPlayers = true): void {
    if (this.state !== "battle" && this.state !== "intro") return;
    this.state = "victory";
    this.victoryAt = system.currentTick;
    const A = this.A!;
    world.setDynamicProperty(WORLD_PROP.victories, ((world.getDynamicProperty(WORLD_PROP.victories) as number) ?? 0) + 1);
    F.clearAll();
    A.mend();
    this.title("§6§lTHE MANDATE IS MENDED", "§eWhat was broken is now more beautiful", 90);
    for (const p of this.inArenaPlayers()) {
      try {
        p.fogSettings.remove(FOG.tag);
        p.fogSettings.push(FOG.mended, FOG.tag);
      } catch {
        // ignore
      }
    }
    if (byPlayers) {
      for (const id of this.participants) {
        const p = world.getEntity(id);
        if (p instanceof Player) giveRewards(p);
      }
    }
    particle(A.dim, FX.petals, add(A.center, v(0, 4, 0)));
    later(100, () => {
      this.actionbar("§eWalk through the Moon Gate (south) to return home");
      sound(A.dim, SND.chimeLow, A.w(0.5, 5, 24.5), 1.5, 1.0);
    });
  }

  private victoryTick(): void {
    const A = this.A!;
    const now = system.currentTick;
    particle(A.dim, FX.gateSwirl, A.w(0.5, 5.5, 24.5));
    if (now % 60 === 0) particle(A.dim, FX.petals, add(A.center, v(Math.random() * 20 - 10, 6, Math.random() * 20 - 10)));
    if (now - this.victoryAt > 20 * 120) {
      for (const p of this.inArenaPlayers()) this.returnHome(p, "§7The Mandate closes behind you.");
      this.cleanup();
    } else if (!this.inArenaPlayers().length && now - this.victoryAt > 200) {
      this.cleanup();
    }
  }

  private gateCheck(): void {
    const A = this.A!;
    const gate = A.w(0.5, 5.5, 24.5);
    for (const p of this.inArenaPlayers()) {
      if (distXZ(p.location, gate) < 3.2 && Math.abs(p.location.z - gate.z) < 1.6) {
        this.returnHome(p, "§6You leave the mended Mandate.");
      }
    }
  }

  cleanup(): void {
    const A = this.A;
    for (const p of this.inArenaPlayers()) this.returnHome(p, "§7The Mandate closes.");
    if (this.boss?.valid) {
      try {
        this.boss.e.remove();
      } catch {
        // ignore
      }
    }
    this.boss = undefined;
    F.clearAll();
    if (A) {
      const summoner = world.getEntity(this.summonerId);
      if (summoner instanceof Player) {
        const home = this.returnPointOf(summoner);
        sweepItems(A.dim, A.center, 40, home.dim, home.loc);
      }
      removeStrays(A.dim);
      later(20, () => A.unload());
    }
    for (const id of this.participants) {
      const p = world.getEntity(id);
      if (p instanceof Player && !this.inMandate(p)) p.setDynamicProperty(WORLD_PROP.returnPoint, undefined);
    }
    this.participants.clear();
    this.respawnPrompted.clear();
    this.graceUntil = 0;
    this.state = "idle";
    world.setDynamicProperty(WORLD_PROP.fight, false);
  }

  /** Called on world load: a fight that was running when the world closed is cancelled cleanly. */
  recoverAfterLoad(): void {
    if (world.getDynamicProperty(WORLD_PROP.fight) === true) {
      this.staleCleanup = true;
      world.setDynamicProperty(WORLD_PROP.fight, false);
    }
  }

  private async cleanStale(): Promise<void> {
    const A = arena();
    this.A = A;
    if (await A.load()) {
      removeStrays(A.dim);
      later(40, () => {
        if (this.state === "idle") A.unload();
      });
    }
  }

  // ------------------------------------------------------------------ testing helpers

  forcePhase(n: number): boolean {
    const b = this.boss;
    if (!b?.valid || this.state !== "battle") return false;
    const target = n >= 3 ? BOSS.phase3At - 0.01 : n === 2 ? BOSS.phase2At - 0.01 : 1;
    b.health?.setCurrentValue(Math.max(2, Math.floor(BOSS.maxHp * target)));
    return true;
  }
}

// ------------------------------------------------------------------ inventory helpers

export function takeSeal(p: Player): boolean {
  const inv = p.getComponent("minecraft:inventory")?.container;
  if (!inv) return false;
  const sel = p.selectedSlotIndex;
  const order = [sel, ...Array.from({ length: inv.size }, (_, i) => i).filter((i) => i !== sel)];
  for (const i of order) {
    const it = inv.getItem(i);
    if (it?.typeId === ITEM.seal) {
      if (it.amount > 1) {
        it.amount -= 1;
        inv.setItem(i, it);
      } else inv.setItem(i, undefined);
      return true;
    }
  }
  return false;
}

export function giveItem(p: Player, item: ItemStack): void {
  const inv = p.getComponent("minecraft:inventory")?.container;
  const rest = inv ? inv.addItem(item) : item;
  if (rest) p.dimension.spawnItem(rest, p.location);
}

function giveRewards(p: Player): void {
  giveItem(p, new ItemStack(ITEM.heart, 1));
  giveItem(p, new ItemStack(ITEM.shard, 3 + Math.floor(Math.random() * 3)));
  giveItem(p, new ItemStack("minecraft:gold_ingot", 12));
  giveItem(p, new ItemStack("minecraft:diamond", 3));
  try {
    p.addExperience(750);
  } catch {
    // ignore
  }
  p.sendMessage("§6The Porcelain Emperor is mended into peace. §eYou receive the §6Kintsugi Heart§e, Shards of the Mandate, gold, diamonds and experience.");
  p.sendMessage("§7Hold the Kintsugi Heart in your off-hand: when you are badly hurt it mends you with gold.");
}

/** Send dropped items and experience orbs near `center` to another place (dimension-crossing teleport). */
function sweepItems(dim: Dimension, center: Vector3, radius: number, toDim: Dimension, to: Vector3): void {
  let ents: Entity[] = [];
  try {
    ents = dim.getEntities({ location: center, maxDistance: radius });
  } catch {
    return;
  }
  for (const e of ents) {
    try {
      const isDrop = !!e.getComponent("minecraft:item") || e.typeId === "minecraft:xp_orb";
      if (isDrop) e.teleport(to, { dimension: toDim, keepVelocity: false });
    } catch {
      // ignore
    }
  }
}

function removeStrays(dim: Dimension): void {
  for (const id of Object.values(ENT)) {
    try {
      for (const e of dim.getEntities({ type: id })) e.remove();
    } catch {
      // ignore
    }
  }
}

export const fight = new FightSession();
