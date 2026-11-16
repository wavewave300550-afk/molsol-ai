import { EntityComponentTypes, EntityEquippableComponent, EquipmentSlot, ItemStack, Player } from "@minecraft/server";

export type WeaponType = "rapier" | "zweihander" | "katana";

/** Parameters of the `rww:weapon` custom item component (set by tools/build.py on every item). */
export interface WeaponParams {
  type: WeaponType;
  tier: string;
  /** Total melee damage of the item (1 base + minecraft:damage), used for the Zweihänder sweep. */
  damage: number;
}

export const WEAPON_TYPES: readonly WeaponType[] = ["rapier", "zweihander", "katana"];

/** Gameplay constants — keep in sync with tools/rww/stats.py (validated by tools/validate.py). */
export const RULES = {
  rapier: {
    /** "Stoccata at long measure": thrusts landing at >= this horizontal distance deal bonus damage. */
    measureDistance: 2.5,
    measureBonus: 1.25,
  },
  katana: {
    /** Iai draw-cut: the first strike within this many ticks of drawing the katana. */
    iaiWindowTicks: 20,
    iaiBonus: 1.5,
    /** Minimum ticks between two iai draw-cuts. */
    iaiRechargeTicks: 80,
  },
  zweihander: {
    /** Sweep (montante-style cut through several opponents). */
    sweepRadius: 3.6,
    /** cos(60°): targets within ±60° of the view direction. */
    sweepCone: 0.5,
    sweepDamageFactor: 0.5,
    sweepKnockback: 0.38,
    primaryKnockback: 0.5,
  },
} as const;

export function weaponParams(item: ItemStack | undefined): WeaponParams | undefined {
  if (!item || !item.typeId.startsWith("rww:")) return undefined;
  try {
    const comp = item.getComponent("rww:weapon");
    const params = comp?.customComponentParameters.params as WeaponParams | undefined;
    if (params && WEAPON_TYPES.includes(params.type)) return params;
  } catch {
    // fall through to the identifier
  }
  const type = WEAPON_TYPES.find((t) => item.typeId.endsWith(`_${t}`));
  if (!type) return undefined;
  const tier = item.typeId.slice(4, item.typeId.length - type.length - 1);
  return { type, tier, damage: 0 };
}

export function mainhand(player: Player): ItemStack | undefined {
  try {
    const eq = player.getComponent(EntityComponentTypes.Equippable) as EntityEquippableComponent | undefined;
    return eq?.getEquipment(EquipmentSlot.Mainhand);
  } catch {
    return undefined;
  }
}

export function heldWeapon(player: Player): WeaponParams | undefined {
  return weaponParams(mainhand(player));
}
