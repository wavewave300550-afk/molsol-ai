/**
 * BOSS 001 - Joan of Arc: The Banner of Divine Paths
 *
 * Entry point: wires world events to the boss encounters, ticks every boss and
 * every player-owned road field, and registers the custom commands.
 */
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  Dimension,
  Entity,
  EntityInitializationCause,
  Player,
  system,
  Vector3,
  world,
} from "@minecraft/server";
import { arenaRing } from "./boss/arena.js";
import { bellRung, crossingPyre, tickBoss, turnedRoad, tutorial } from "./boss/run.js";
import { JoanBoss } from "./boss/joan.js";
import { ownerOf, removeQuietly, shatter, sweepOrphans } from "./boss/minions.js";
import { intro } from "./boss/scenes.js";
import { hitStandard } from "./boss/skills/convergence.js";
import { SKILLS } from "./boss/skills/index.js";
import { strikeWaystone } from "./boss/skills/stake.js";
import { ECHO, ITEM_BANNER, JOAN, MINIONS, SERAPH, STANDARD, WAYSTONE } from "./config.js";
import { resetFxBudget } from "./core/fx.js";
import { isPlayer } from "./core/targets.js";
import { dirOfYaw, dist, scale, add } from "./core/vec.js";
import { SUMMON_ITEMS, tickPlayerFields, useBanner, useSummonItem } from "./rewards.js";

export const bosses = new Map<string, JoanBoss>();
let now = 0;

const DIMENSIONS = ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"];

// --------------------------------------------------------------------------- encounters
function adopt(e: Entity, fresh: boolean): void {
  if (!e.isValid || bosses.has(e.id)) return;
  // helpers she left behind before a chunk unload or reload belong to no running skill any more
  for (const type of MINIONS) {
    try {
      for (const m of e.dimension.getEntities({ type })) if (ownerOf(m) === e.id) removeQuietly(m);
    } catch {
      // ignore
    }
  }
  const b = new JoanBoss(e, now);
  b.field.hooks = {
    onCaptured: (ent, p) => tutorial(b, ent, p),
    onCrossing: (at) => crossingPyre(b, at),
  };
  bosses.set(e.id, b);
  let started = false;
  try {
    started = e.getDynamicProperty("joan:started") === true;
  } catch {
    // ignore
  }
  if (fresh || !started) {
    try {
      e.setDynamicProperty("joan:started", true);
    } catch {
      // ignore
    }
    b.start("intro", intro(b), false);
    return;
  }
  // resumed after a reload or chunk load: back to the fight in the stored phase
  try {
    const home = e.getDynamicProperty("joan:home");
    if (home && typeof home === "object") b.home = home as Vector3;
    const ph = e.getDynamicProperty("joan:phase");
    b.setPhase(ph === 2 ? 2 : 1);
    if (b.phase === 2) e.triggerEvent("joan:darken");
  } catch {
    b.setPhase(1);
  }
  b.mode = "fight";
  b.invulnerable = false;
  b.anim("none");
  arenaRing(b);
}

function bossOf(e: Entity | undefined): JoanBoss | undefined {
  return e ? bosses.get(e.id) : undefined;
}

function bossesNear(at: Vector3, dimId: string, radius: number): JoanBoss[] {
  return [...bosses.values()].filter((b) => b.valid && b.dim.id === dimId && dist(b.pos, at) <= radius);
}

function scanForJoans(): void {
  for (const id of DIMENSIONS) {
    let dim: Dimension;
    try {
      dim = world.getDimension(id);
    } catch {
      continue;
    }
    try {
      for (const e of dim.getEntities({ type: JOAN })) adopt(e, false);
    } catch {
      // ignore
    }
  }
}

// --------------------------------------------------------------------------- main loop
system.runInterval(() => {
  now++;
  resetFxBudget();
  for (const [id, b] of bosses) {
    let alive = false;
    try {
      alive = tickBoss(b, now);
    } catch (err) {
      console.warn(`[joan] boss tick failed: ${err}`);
      alive = b.valid;
    }
    if (!alive) {
      try {
        b.dispose();
      } catch {
        // ignore
      }
      bosses.delete(id);
    }
  }
  tickPlayerFields(now);
  if (now % 400 === 0) {
    scanForJoans();
    sweepOrphans(new Set(bosses.keys()));
  }
}, 1);

// --------------------------------------------------------------------------- world events
world.afterEvents.worldLoad.subscribe(() => {
  sweepOrphans(new Set());
  scanForJoans();
  console.log("[joan] BOSS 001 - Joan of Arc loaded");
});

world.afterEvents.entitySpawn.subscribe((ev) => {
  const e = ev.entity;
  if (!e.isValid || e.typeId !== JOAN) return;
  const fresh = ev.cause !== EntityInitializationCause.Loaded;
  system.run(() => adopt(e, fresh));
});

world.afterEvents.entityLoad.subscribe((ev) => {
  if (ev.entity.isValid && ev.entity.typeId === JOAN) adopt(ev.entity, false);
});

world.beforeEvents.entityHurt.subscribe((ev) => {
  const e = ev.hurtEntity;
  if (e.typeId !== JOAN) return;
  const b = bosses.get(e.id);
  if (!b) return;
  const src = ev.damageSource;
  const dmg = b.filterDamage(ev.damage, src.cause, src.damagingEntity, src.damagingProjectile);
  if (dmg <= 0) ev.cancel = true;
  else ev.damage = dmg;
});

world.afterEvents.entityHitEntity.subscribe((ev) => {
  const target = ev.hitEntity;
  const src = ev.damagingEntity;
  if (!target.isValid) return;
  if (target.typeId === JOAN && isPlayer(src)) bossOf(target)?.brain.noteMelee(src);
  else if (target.typeId === WAYSTONE) strikeWaystone(target, src);
  else if (target.typeId === STANDARD && isPlayer(src)) hitStandard(target);
  else if ((target.typeId === ECHO || target.typeId === SERAPH) && isPlayer(src)) shatter(target);
});

world.afterEvents.projectileHitEntity.subscribe((ev) => {
  let hit: Entity | undefined;
  try {
    hit = ev.getEntityHit()?.entity;
  } catch {
    return;
  }
  if (!hit || !hit.isValid) return;
  const src = ev.source;
  if (hit.typeId === JOAN) {
    const b = bossOf(hit);
    if (!b) return;
    if (src && isPlayer(src)) b.brain.noteRanged(src, 2);
    turnedRoad(b, src);
  } else if (hit.typeId === WAYSTONE) strikeWaystone(hit, ev.projectile);
  else if (hit.typeId === STANDARD && src && isPlayer(src)) hitStandard(hit);
  else if ((hit.typeId === ECHO || hit.typeId === SERAPH) && src && isPlayer(src)) shatter(hit);
});

const RANGED = /(bow|crossbow|trident)$/;
world.afterEvents.itemStartUse.subscribe((ev) => {
  const id = ev.itemStack?.typeId ?? "";
  if (!RANGED.test(id)) return;
  for (const b of bossesNear(ev.source.location, ev.source.dimension.id, 48)) {
    b.brain.noteRanged(ev.source, 1.2);
    b.brain.obsOf(ev.source).drawing = true;
  }
});

world.afterEvents.itemReleaseUse.subscribe((ev) => {
  for (const b of bossesNear(ev.source.location, ev.source.dimension.id, 48)) b.brain.obsOf(ev.source).drawing = false;
});

function useItem(p: Player, id: string): void {
  if (id === ITEM_BANNER) useBanner(p, now);
  else if (SUMMON_ITEMS.has(id)) useSummonItem(p, id, now);
}

world.afterEvents.itemUse.subscribe((ev) => {
  useItem(ev.source, ev.itemStack.typeId);
});

world.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  if (!ev.isFirstEvent) return;
  const block = ev.block;
  if (block.typeId === "minecraft:bell") {
    for (const b of bossesNear(block.location, ev.player.dimension.id, 40)) if (bellRung(b, ev.player)) break;
    return;
  }
  const id = ev.beforeItemStack?.typeId;
  if (id && (id === ITEM_BANNER || SUMMON_ITEMS.has(id))) useItem(ev.player, id);
});

// --------------------------------------------------------------------------- commands
system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("joan:skill", SKILLS.map((s) => s.name));
    reg.registerCommand(
      { name: "joan:summon", description: "Summon BOSS 001 Joan of Arc in front of you", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          const at = add(p.location, scale(dirOfYaw(p.getRotation().y), 8));
          try {
            p.dimension.spawnEntity(JOAN, at);
          } catch (err) {
            p.sendMessage(`§cCould not summon Joan: ${err}`);
          }
        });
        return { status: CustomCommandStatus.Success, message: "Joan of Arc descends." };
      },
    );
    reg.registerCommand(
      {
        name: "joan:skill",
        description: "Make the nearest Joan use a skill next (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "joan:skill", type: CustomCommandParamType.Enum }],
      },
      (origin, name: string) => {
        const p = origin.sourceEntity;
        if (!p) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
        const b = bossesNear(p.location, p.dimension.id, 96)[0];
        if (!b) return { status: CustomCommandStatus.Failure, message: "No Joan of Arc nearby." };
        system.run(() => {
          if (name === "stake") {
            b.flags.lastUlt = -99999;
            if (b.phase < 2) b.flags.pendingTransition = true;
          }
          b.brain.forced = name;
          b.gcdUntil = 0;
          b.cooldowns.delete(name);
          if (b.action?.interruptible) b.interrupt();
        });
        return { status: CustomCommandStatus.Success, message: `Joan will use ${name}.` };
      },
    );
    reg.registerCommand(
      {
        name: "joan:phase",
        description: "Send the nearest Joan into phase II (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
      },
      (origin) => {
        const p = origin.sourceEntity;
        if (!p) return { status: CustomCommandStatus.Failure, message: "Run this as a player." };
        const b = bossesNear(p.location, p.dimension.id, 96)[0];
        if (!b) return { status: CustomCommandStatus.Failure, message: "No Joan of Arc nearby." };
        system.run(() => {
          if (b.phase === 1) b.flags.pendingTransition = true;
        });
        return { status: CustomCommandStatus.Success, message: "The roads begin to burn." };
      },
    );
    reg.registerCommand(
      { name: "joan:clear", description: "Remove every Joan of Arc and her roads", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      () => {
        system.run(() => {
          for (const b of bosses.values()) {
            b.dispose();
            try {
              b.e.remove();
            } catch {
              // ignore
            }
          }
          bosses.clear();
          sweepOrphans(new Set());
        });
        return { status: CustomCommandStatus.Success, message: "The field is quiet." };
      },
    );
  } catch (err) {
    console.warn(`[joan] custom commands unavailable: ${err}`);
  }
});
