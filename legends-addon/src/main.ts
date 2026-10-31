/**
 * Legendary & Divine Beings — gameplay entry point.
 *
 * Six god-tier extra bosses (Taotie, Níðhöggr, Hanuman, Alicorn, the Ten-Tailed
 * Fox and The Word of God with its Seraph, Cherub and Ophan), each a scripted
 * multi-phase fight with an ultimate.
 */
import {
  CommandPermissionLevel,
  CustomCommandParamType,
  CustomCommandStatus,
  Player,
  system,
  world,
} from "@minecraft/server";
import { Being, beings } from "./bosses/being.js";
import { Boss, BossKey } from "./bosses/boss.js";
import { Taotie } from "./bosses/taotie.js";
import { adoptOrphans, clearAll, tickBeings } from "./bosses/registry.js";
import { stepShots } from "./core/hazards.js";
import { flushNotices, forget } from "./core/notice.js";
import { runTasks } from "./core/tasks.js";
import { giveItem, SIGILS, summonNow, useSigil } from "./summon.js";
import { openCodex } from "./ui.js";

const CODEX = "legends:codex";
const KEYS: BossKey[] = ["taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos"];

// --------------------------------------------------------------------------- commands

system.beforeEvents.startup.subscribe((ev) => {
  const reg = ev.customCommandRegistry;
  try {
    reg.registerEnum("legends:boss", KEYS);
    reg.registerCommand(
      { name: "legends:codex", description: "Open the Codex of Legends", permissionLevel: CommandPermissionLevel.Any, cheatsRequired: false },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => void openCodex(p));
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      {
        name: "legends:summon",
        description: "Summon a legend in front of you (skips the ritual)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "legends:boss", type: CustomCommandParamType.Enum }],
      },
      (origin, key: string) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          const d = p.getViewDirection();
          summonNow(p.dimension, { x: p.location.x + d.x * 10, y: p.location.y, z: p.location.z + d.z * 10 }, key as BossKey, p.getRotation().y + 180);
        });
        return { status: CustomCommandStatus.Success, message: `Summoning ${key}.` };
      },
    );
    reg.registerCommand(
      {
        name: "legends:phase",
        description: "Force the nearest legend into a phase (testing)",
        permissionLevel: CommandPermissionLevel.GameDirectors,
        cheatsRequired: true,
        mandatoryParameters: [{ name: "phase", type: CustomCommandParamType.Integer }],
      },
      (origin, phase: number) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          const b = nearestBoss(p);
          if (!b) return;
          const target = Math.max(2, Math.min(b.thresholds.length + 1, phase));
          const h = b.entity.getComponent("minecraft:health");
          if (h && target - 2 < b.thresholds.length) h.setCurrentValue(Math.max(1, b.maxHp * b.thresholds[target - 2] + 0.5));
          b.phase = target - 1;
        });
        return { status: CustomCommandStatus.Success };
      },
    );
    reg.registerCommand(
      { name: "legends:clear", description: "Remove every legend, follower and hazard", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      () => {
        system.run(() => clearAll());
        return { status: CustomCommandStatus.Success, message: "Cleared." };
      },
    );
    reg.registerCommand(
      { name: "legends:sigils", description: "Give yourself every sigil (testing)", permissionLevel: CommandPermissionLevel.GameDirectors, cheatsRequired: true },
      (origin) => {
        const p = origin.sourceEntity;
        if (!(p instanceof Player)) return { status: CustomCommandStatus.Failure, message: "Players only." };
        system.run(() => {
          for (const id of Object.keys(SIGILS)) giveItem(p, id);
        });
        return { status: CustomCommandStatus.Success };
      },
    );
  } catch (e) {
    console.warn(`[legends] custom commands unavailable: ${e}`);
  }
});

function nearestBoss(p: Player): Boss | undefined {
  let best: Boss | undefined;
  let bd = 1e9;
  for (const b of beings.values()) {
    if (!(b instanceof Boss) || !b.valid || b.dim.id !== p.dimension.id) continue;
    const d = Math.hypot(b.pos.x - p.location.x, b.pos.z - p.location.z);
    if (d < bd) {
      bd = d;
      best = b;
    }
  }
  return best;
}

// --------------------------------------------------------------------------- items

world.afterEvents.itemUse.subscribe((ev) => {
  const id = ev.itemStack.typeId;
  if (id === CODEX) void openCodex(ev.source);
  else if (SIGILS[id]) system.run(() => useSigil(ev.source, id));
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  if (!ev.initialSpawn) return;
  const p = ev.player;
  if (p.getDynamicProperty("legends:codex_given") === true) return;
  p.setDynamicProperty("legends:codex_given", true);
  system.runTimeout(() => {
    if (p.isValid) giveItem(p, CODEX);
  }, 40);
});

world.beforeEvents.playerLeave.subscribe((ev) => {
  forget(ev.player.id);
});

// --------------------------------------------------------------------------- damage model

world.beforeEvents.entityHurt.subscribe(
  (ev) => {
    const src = ev.damageSource.damagingEntity;
    if (src && src.typeId.startsWith("legends:")) {
      ev.cancel = true; // legends never harm each other
      return;
    }
    const b = beings.get(ev.hurtEntity.id);
    if (!b) return;
    if (b.invuln) {
      ev.cancel = true;
      return;
    }
    let d = ev.damage * b.takenMul;
    if (b instanceof Boss) {
      d *= b.partyMul();
      const floor = b.gateHp();
      if (b.hp - d < floor) d = Math.max(0, b.hp - floor);
      if (d <= 0.001) {
        ev.cancel = true;
        return;
      }
      b.hp -= d;
    }
    ev.damage = d;
    if (src instanceof Player) b.lastAttacker = src;
  },
  { entityFilter: { families: ["legends"] } },
);

world.afterEvents.entityHurt.subscribe(
  (ev) => {
    const b: Being | undefined = beings.get(ev.hurtEntity.id);
    if (!b) return;
    const src = ev.damageSource.damagingEntity;
    b.onDamaged(ev.damage, src instanceof Player ? src : undefined);
  },
  { entityFilter: { families: ["legends"] } },
);

world.afterEvents.entityDie.subscribe((ev) => {
  const killer = ev.damageSource.damagingEntity;
  if (killer && ev.deadEntity instanceof Player) {
    const b = beings.get(killer.id);
    if (b instanceof Taotie) b.heal(b.maxHp * 0.04); // Taotie feeds on the fallen
  }
  const dead = beings.get(ev.deadEntity.id);
  if (dead) dead.dispose();
});

// --------------------------------------------------------------------------- main loop

let tick = 0;
system.runInterval(() => {
  tick++;
  runTasks();
  stepShots();
  tickBeings();
  flushNotices();
  if (tick % 100 === 5) adoptOrphans();
}, 1);
