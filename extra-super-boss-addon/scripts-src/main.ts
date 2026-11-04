/**
 * Extra Super Boss - Boss 1: Leonardo da Vinci (esb:da_vinci)
 *
 * Vanilla AI walks him around and swings the compass (minecraft:behavior.delayed_attack); this script
 * adds the boss fight on top: intro, gear volley, gauntlet quake, Vitruvian judgement, the phase 2
 * transformation at 50% health with the ornithopter dive, and a scripted death.  Visual state reaches the
 * client through the synced properties esb:action and esb:phase, which drive the animation controllers.
 */
import { Entity, EntityDamageCause, EntityInitializationCause, Player, system, world } from "@minecraft/server";
import { beginDying, endAction, forceGround, removeSigil, startAction } from "./abilities.js";
import { think } from "./brain.js";
import { BossState, bosses, event, isBoss, newState, safe, setProp } from "./boss.js";
import { fxTick } from "./fx.js";
import { registerItems } from "./items.js";
import { BOSS_ID } from "./spec.js";

const INTRO_FLAG = "esb:intro_done";

function register(e: Entity, fresh = false): BossState | undefined {
  if (!e.isValid || e.typeId !== BOSS_ID) return undefined;
  const known = bosses.get(e.id);
  if (known) {
    known.entity = e;
    return known;
  }
  const s = newState(e);
  bosses.set(e.id, s);
  const phase = safe(() => e.getProperty("esb:phase"));
  s.phase = phase === 2 ? 2 : 1;
  const action = safe(() => e.getProperty("esb:action"));
  // normalise after a reload: on the ground, free to move, no half-finished action
  event(s, "esb:to_ground");
  s.locked = true;
  for (const [k, v] of [["esb:action", "none"], ["esb:phase", s.phase]] as [string, string | number][]) {
    s.props[k] = "__unset__";
    setProp(s, k, v);
  }
  if (action === "death") {
    beginDying(s);
    return s;
  }
  if (fresh && !safe(() => e.getDynamicProperty(INTRO_FLAG))) {
    safe(() => e.setDynamicProperty(INTRO_FLAG, true));
    s.locked = false; // so startAction really sends esb:lock (a fresh spawn starts in the free group)
    startAction(s, "intro");
    return s;
  }
  s.locked = true;
  endAction(s);
  return s;
}

function scan(): void {
  for (const id of ["overworld", "nether", "the_end"]) {
    const dim = safe(() => world.getDimension(id));
    const list = dim ? safe(() => dim.getEntities({ type: BOSS_ID })) ?? [] : [];
    for (const e of list) register(e);
  }
}

world.afterEvents.entitySpawn.subscribe(({ entity, cause }) => {
  if (entity.typeId === BOSS_ID) register(entity, cause !== EntityInitializationCause.Loaded);
});
world.afterEvents.entityLoad.subscribe(({ entity }) => {
  if (entity.typeId === BOSS_ID) register(entity);
});
world.afterEvents.entityRemove.subscribe(({ removedEntityId }) => {
  const s = bosses.get(removedEntityId);
  if (s) removeSigil(s);
  bosses.delete(removedEntityId);
});
world.afterEvents.entityDie.subscribe(({ deadEntity }) => {
  const s = bosses.get(deadEntity.id);
  if (s) removeSigil(s);
  bosses.delete(deadEntity.id);
});

// whoever hurts him becomes his target; the last player to hit him gets the kill
world.afterEvents.entityHurt.subscribe(({ hurtEntity, damageSource }) => {
  const s = register(hurtEntity);
  const by = damageSource.damagingEntity;
  if (!s || s.dying || !by || !by.isValid || isBoss(by)) return;
  if (by.typeId === "minecraft:player") s.killer = by as Player;
  s.target = by;
}, { entityTypes: [BOSS_ID] });

// a hit that would kill him is cancelled and turned into the death sequence; he cannot be hurt while
// dying, during the intro or while transforming.  (restricted mode: changes are deferred)
world.beforeEvents.entityHurt.subscribe((ev) => {
  const e = ev.hurtEntity;
  const s = bosses.get(e.id);
  if (!s || s.allowKill) return;
  if (s.dying || s.invulnerable) {
    ev.cancel = true;
    return;
  }
  if (ev.damageSource.cause === EntityDamageCause.void) return;
  const hp = safe(() => (e.getComponent("minecraft:health") as unknown as { currentValue: number }).currentValue);
  if (hp !== undefined && ev.damage >= hp) {
    ev.cancel = true;
    const id = e.id;
    const by = ev.damageSource.damagingEntity;
    system.run(() => {
      const st = bosses.get(id) ?? (e.isValid ? register(e) : undefined);
      if (!st) return;
      if (by && by.isValid && by.typeId === "minecraft:player") st.killer = by;
      beginDying(st);
    });
  }
}, { entityFilter: { type: BOSS_ID } });

registerItems();

let ticks = 0;
system.runInterval(() => {
  ticks++;
  fxTick(system.currentTick);
  if (ticks === 1 || ticks % 40 === 0) scan();
  for (const [id, s] of bosses) {
    if (!s.entity.isValid) {
      removeSigil(s);
      bosses.delete(id);
      continue;
    }
    try {
      think(s);
    } catch (err) {
      // never let one bad tick stop the loop: put him back in a safe state
      console.warn(`[Extra Super Boss] ${String(err)}`);
      forceGround(s);
      if (!s.dying) {
        s.run = undefined;
        s.invulnerable = false;
        s.locked = true;
        endAction(s);
      }
    }
  }
}, 1);
