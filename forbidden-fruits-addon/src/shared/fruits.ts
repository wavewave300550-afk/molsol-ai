/**
 * Forbidden Fruits - rules shared by every fruit in the pack.
 * One body can hold one fruit's power: eating a different fruit is refused (the fruit is kept).
 */
import { ItemStack, Player, system, world } from "@minecraft/server";

export interface FruitInfo {
  item: string;
  owner: string;
  name: string;
  color: string;
  element: string;
}

export const FRUITS: FruitInfo[] = [
  { item: "joki:joki_fruit", owner: "joki:owner", name: "Jōki Jōki no Mi", color: "§c", element: "Steam (Paramecia)" },
  { item: "sekiyu:sekiyu_fruit", owner: "sekiyu:owner", name: "Sekiyu Sekiyu no Mi", color: "§6", element: "Petroleum (Logia)" },
];

const WELCOMED = "forbidden:welcomed";

export function fruitOf(p: Player): FruitInfo | undefined {
  try {
    return FRUITS.find((f) => p.getDynamicProperty(f.owner) === true);
  } catch {
    return undefined;
  }
}

/** The *other* fruit power that stops `p` from eating fruit `item`, if any. */
export function blockedBy(p: Player, item: string): FruitInfo | undefined {
  const mine = fruitOf(p);
  return mine && mine.item !== item ? mine : undefined;
}

export function refusal(owned: FruitInfo): string {
  return `§7Your body already holds the power of the ${owned.color}${owned.name}§7. One body can only hold one fruit's power.`;
}

/** Refund a fruit that was eaten despite the guard (should not normally happen). */
export function refund(p: Player, item: string): void {
  try {
    p.getComponent("minecraft:inventory")?.container?.addItem(new ItemStack(item, 1));
  } catch {
    // full inventory
  }
}

world.beforeEvents.itemUse.subscribe((ev) => {
  const fruit = FRUITS.find((f) => f.item === ev.itemStack.typeId);
  if (!fruit) return;
  const owned = blockedBy(ev.source, fruit.item);
  if (!owned) return;
  ev.cancel = true;
  const p = ev.source;
  system.run(() => p.isValid && p.sendMessage(refusal(owned)));
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  const p = ev.player;
  if (!ev.initialSpawn) return;
  system.runTimeout(() => {
    if (!p.isValid || p.getDynamicProperty(WELCOMED) === true || fruitOf(p)) return;
    p.setDynamicProperty(WELCOMED, true);
    p.sendMessage(
      "§l§5Forbidden Fruits§r §7- two fruits, one body each:\n" +
        FRUITS.map((f) => ` ${f.color}${f.name}§7 - ${f.element}: §f/give @s ${f.item}`).join("\n") +
        "\n§8Also in the creative inventory (Equipment). You can only ever eat one of them.",
    );
  }, 20);
});
