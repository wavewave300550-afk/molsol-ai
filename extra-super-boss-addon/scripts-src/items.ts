import {
  Entity, EntityDamageCause, EntityInventoryComponent, GameMode, ItemStack, Player, system, Vector3, world,
} from "@minecraft/server";
import { BALANCE } from "./balance.js";
import { isBoss, isLiving, now, safe, sec } from "./boss.js";
import { PFX, SND, particle, sound } from "./fx.js";
import { BLUEPRINT_ID, BOSS_ID, CODEX_ID, EDISON_ID, PATENT_ID, SHIV_ID, SIGIL_ID } from "./spec.js";
import { v3, yawTo } from "./vec.js";

const RITUAL_TICKS = 50;
const pendingRituals = new Set<string>();
const codexReady = new Map<string, number>();

function say(p: Player, key: string, withArgs?: string[]): void {
  safe(() => p.sendMessage({ rawtext: [{ translate: key, with: withArgs }] }));
}

function consumeOne(p: Player): void {
  if (safe(() => p.getGameMode()) === GameMode.Creative) return;
  const inv = safe(() => p.getComponent("minecraft:inventory")) as EntityInventoryComponent | undefined;
  const c = inv?.container;
  if (!c) return;
  const slot = p.selectedSlotIndex;
  const it = safe(() => c.getItem(slot)) as ItemStack | undefined;
  if (!it) return;
  if (it.amount > 1) {
    it.amount -= 1;
    safe(() => c.setItem(slot, it));
  } else {
    safe(() => c.setItem(slot, undefined));
  }
}

/** A 3 x 3 x 4 pocket of air standing on solid ground. */
function openGround(p: Player, spot: Vector3): boolean {
  const dim = p.dimension;
  for (let dx = -1; dx <= 1; dx++) {
    for (let dz = -1; dz <= 1; dz++) {
      for (let dy = 0; dy < 4; dy++) {
        const b = safe(() => dim.getBlock(v3(spot.x + dx, spot.y + dy, spot.z + dz)));
        if (!b || !b.isAir) return false;
      }
    }
  }
  return true;
}

interface Ritual {
  boss: string;
  busy: string;
  start: string;
  circle: boolean; // Da Vinci draws a golden sigil; Edison's patent crackles with current
}
const BLUEPRINT: Ritual = { boss: BOSS_ID, busy: "esb.msg.summon_busy", start: "esb.msg.summon", circle: true };
const PATENT: Ritual = { boss: EDISON_ID, busy: "esb.msg.patent_busy", start: "esb.msg.patent", circle: false };

function summon(p: Player, r: Ritual): void {
  const dim = p.dimension;
  const near = safe(() => dim.getEntities({ type: r.boss, location: p.location, maxDistance: 96 })) ?? [];
  if (near.length || pendingRituals.size) {
    say(p, r.busy);
    return;
  }
  const view = p.getViewDirection();
  const h = Math.sqrt(view.x * view.x + view.z * view.z) || 1;
  const fx = Math.floor(p.location.x + (view.x / h) * 6) + 0.5;
  const fz = Math.floor(p.location.z + (view.z / h) * 6) + 0.5;
  const hit = safe(() => dim.getBlockFromRay(v3(fx, p.location.y + 4, fz), v3(0, -1, 0), {
    maxDistance: 12, includeLiquidBlocks: true, includePassableBlocks: false,
  }));
  const spot = v3(fx, hit ? hit.block.location.y + 1 : Math.floor(p.location.y), fz);
  if (!hit || !openGround(p, spot)) {
    say(p, "esb.msg.summon_space");
    return;
  }
  consumeOne(p);
  say(p, r.start);
  const key = `${p.id}:${now()}`;
  pendingRituals.add(key);
  const sigil = r.circle ? safe(() => dim.spawnEntity(SIGIL_ID, v3(spot.x, spot.y + 0.02, spot.z))) : undefined;
  if (sigil) safe(() => sigil.setProperty("esb:radius", 3));
  particle(dim, PFX.pillar, spot);
  sound(dim, r.circle ? SND.charge : SND.fizz, spot, 1.2, 0.8);
  sound(dim, SND.page, spot, 1.0, 0.7);
  if (!r.circle) {
    for (let i = 1; i < RITUAL_TICKS; i += 6) {
      system.runTimeout(() => particle(dim, PFX.telegraph, v3(spot.x, spot.y + 0.1, spot.z), undefined, 0), i);
    }
  }
  system.runTimeout(() => {
    pendingRituals.delete(key);
    if (sigil?.isValid) safe(() => sigil.remove());
    const boss = safe(() => dim.spawnEntity(r.boss, spot));
    if (boss && p.isValid) safe(() => boss.setRotation({ x: 0, y: yawTo(spot, p.location) }));
  }, RITUAL_TICKS);
}

/** Volt Shiv (Edison's drop): sparks on every hit, sometimes an extra jolt that slows. */
function shivHit(p: Player, target: Entity): void {
  const inv = safe(() => p.getComponent("minecraft:inventory")) as EntityInventoryComponent | undefined;
  const it = safe(() => inv?.container?.getItem(p.selectedSlotIndex)) as ItemStack | undefined;
  if (!it || it.typeId !== SHIV_ID || !isLiving(target) || target.id === p.id) return;
  const c = v3(target.location.x, target.location.y + 1, target.location.z);
  particle(p.dimension, PFX.voltSpark, c, undefined, 0);
  if (Math.random() < BALANCE.edison.shiv.proc_chance) {
    system.run(() => {
      if (!target.isValid) return;
      safe(() => target.applyDamage(BALANCE.edison.shiv.bonus_damage, { cause: EntityDamageCause.lightning, damagingEntity: p }));
      if (!isBoss(target)) safe(() => target.addEffect("slowness", 20, { amplifier: 1, showParticles: false }));
      particle(p.dimension, PFX.zap, c, undefined, 1);
      sound(p.dimension, SND.fizz, c, 0.8, 1.6);
    });
  }
}

function useCodex(p: Player): void {
  const t = now();
  const readyAt = codexReady.get(p.id) ?? 0;
  if (t < readyAt) {
    say(p, "esb.msg.codex_cd", [String(Math.ceil((readyAt - t) / 20))]);
    return;
  }
  const dur = sec(BALANCE.codex.duration);
  safe(() => p.addEffect("haste", dur, { amplifier: 1, showParticles: false }));
  safe(() => p.addEffect("speed", dur, { amplifier: 0, showParticles: false }));
  safe(() => p.addEffect("night_vision", dur, { amplifier: 0, showParticles: false }));
  codexReady.set(p.id, t + sec(BALANCE.codex.cooldown));
  sound(p.dimension, SND.levelup, p.location, 0.8, 1.3);
  particle(p.dimension, PFX.pages, v3(p.location.x, p.location.y + 1.2, p.location.z));
  say(p, "esb.msg.codex", [String(BALANCE.codex.duration)]);
}

export function registerItems(): void {
  world.afterEvents.itemUse.subscribe(({ source, itemStack }) => {
    if (!source || source.typeId !== "minecraft:player") return;
    if (itemStack.typeId === BLUEPRINT_ID) summon(source, BLUEPRINT);
    else if (itemStack.typeId === PATENT_ID) summon(source, PATENT);
    else if (itemStack.typeId === CODEX_ID) useCodex(source);
  });
  world.afterEvents.entityHitEntity.subscribe(({ damagingEntity, hitEntity }) => {
    if (damagingEntity?.typeId === "minecraft:player") shivHit(damagingEntity as Player, hitEntity);
  });
}

export const RITUAL_SECONDS = RITUAL_TICKS / 20;
