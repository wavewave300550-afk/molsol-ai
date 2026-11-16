/**
 * Real-World Weapons — gameplay script (@minecraft/server 2.11.0, stable APIs only).
 *
 * What the JSON items already do natively (no script needed):
 *   damage, durability, repair, enchanting, attack cooldown (`minecraft:cooldown` type "attack"),
 *   swing duration, reach for the rapier / Zweihänder (`minecraft:piercing_weapon`), swing sounds.
 * What this script adds:
 *   - player animations for the held weapon (AnimationDriver)
 *   - weapon-specific rules: rapier long-measure thrust, katana iai draw-cut,
 *     Zweihänder sweep / heavy knock-back / hefting time (Combat)
 */
import { EntityDamageCause, system, world } from "@minecraft/server";
import { AnimationDriver } from "./animation.js";
import { Combat } from "./combat.js";
import { mainhand, WeaponParams } from "./weapons.js";

const driver = new AnimationDriver();
const combat = new Combat();

system.beforeEvents.startup.subscribe((ev) => {
  ev.itemComponentRegistry.registerCustomComponent("rww:weapon", {
    onHitEntity(e, p) {
      combat.onHitEntity(e, p.params as WeaponParams);
    },
    onBeforeDurabilityDamage(e) {
      combat.onBeforeDurabilityDamage(e);
    },
  });
});

driver.onEquip = (player, weapon) => combat.onEquip(player, weapon, mainhand(player));

world.beforeEvents.entityHurt.subscribe((ev) => combat.onBeforeHurt(ev), {
  allowedDamageCauses: [EntityDamageCause.entityAttack],
});

world.afterEvents.playerSpawn.subscribe((ev) => driver.onSpawn(ev.player, ev.initialSpawn));
world.afterEvents.playerDimensionChange.subscribe((ev) => {
  system.runTimeout(() => ev.player.isValid && driver.onDimensionChange(ev.player), 10);
});
world.beforeEvents.playerLeave.subscribe((ev) => {
  const id = ev.player.id;
  system.run(() => {
    driver.onLeave(id);
    combat.onLeave(id);
  });
});

system.runInterval(() => driver.update(), 2);
system.runInterval(() => driver.updateVisibility(), 40);
