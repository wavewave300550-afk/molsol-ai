import { CommandPermissionLevel, Player, system, world } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason } from "@minecraft/server-ui";
import { ABILITIES, ABILITY_ORDER, CONTROLS, DP, Form, WORLD_PVP } from "./config.js";
import { cooldownLeft, selectAbility } from "./casting.js";
import { pvpEnabled } from "./core/combat.js";
import { DAMAGE_RULES, setForm } from "./logia.js";
import { giveCore } from "./power.js";
import { isOwner, notice, now, state } from "./state.js";

const ICON = (name: string): string => `textures/sekiyu/ui/${name}`;

async function show(p: Player, form: ActionFormData, tries = 20): Promise<ActionFormResponse | undefined> {
  for (let i = 0; i < tries; i++) {
    if (!p.isValid) return undefined;
    const res = await form.show(p);
    if (res.canceled && res.cancelationReason === FormCancelationReason.UserBusy) {
      await new Promise<void>((r) => system.runTimeout(() => r(), 5));
      continue;
    }
    return res;
  }
  return undefined;
}

type Entry = { label: string; icon?: string; run: () => void | Promise<void> };

/** The Oil Console: select abilities (never casts), toggle the Logia form, settings. */
export async function openConsole(p: Player): Promise<void> {
  if (!isOwner(p)) {
    await show(p, new ActionFormData().title("§l§6Crude Core").body(
      "§7A dense core of black crude. It answers only to a body made of petroleum.\n\n§fEat the §6Sekiyu Sekiyu no Mi§f to awaken it.\n§8Creative inventory, or: /give @s sekiyu:sekiyu_fruit",
    ).button("§8Close"));
    return;
  }
  const s = state(p);
  const entries: Entry[] = [];
  ABILITY_ORDER.forEach((id, i) => {
    const a = ABILITIES[id];
    const left = cooldownLeft(p, id);
    const status = left > 0 ? `§7${(left / 20).toFixed(1)}s` : "§2ready";
    entries.push({
      label: `${i === s.selected ? "§l" : ""}${id === "inferno" ? "§4" : "§0"}${a.name}${i === s.selected ? " §r§6<" : ""}\n§r§8${(a.cooldown / 20).toFixed(0)}s cooldown | ${status}`,
      icon: ICON(id),
      run: () => selectAbility(p, i),
    });
  });
  const liquid = s.form === Form.Body;
  entries.push({
    label: liquid ? "§1Reform\n§8back to flesh" : "§0Logia: Become Petroleum\n§8same as Petroleum Body",
    icon: ICON("logia"),
    run: () => {
      if (s.sealed) return notice(s, "§bSubmerged - cannot transform", 40);
      if (s.form === Form.Dissolved) return notice(s, "§7Reform first", 30);
      setForm(p, s, liquid ? Form.Human : Form.Body);
    },
  });
  entries.push({
    label: `§3Ability HUD: ${s.hudEnabled ? "§2ON" : "§4OFF"}\n§8form, follow-ups, cooldowns`,
    icon: ICON("hud"),
    run: () => {
      s.hudEnabled = !s.hudEnabled;
      p.setDynamicProperty(DP.hud, s.hudEnabled);
    },
  });
  entries.push({ label: "§1Power Guide\n§8abilities, Logia rules, weaknesses", icon: ICON("guide"), run: () => guide(p) });
  entries.push({
    label: "§2Summon a new Core\n§8if yours was lost",
    icon: "textures/items/sekiyu/crude_core",
    run: () => {
      if (!giveCore(p)) p.sendMessage("§7You already carry a Crude Core.");
    },
  });
  if (p.commandPermissionLevel >= CommandPermissionLevel.GameDirectors) {
    entries.push({
      label: `§4PvP oil damage: ${pvpEnabled() ? "§2ON" : "§8OFF"}\n§8world rule (operators)`,
      run: () => {
        world.setDynamicProperty(WORLD_PVP, !pvpEnabled());
        world.sendMessage(`§6[Sekiyu] §7Petroleum abilities ${pvpEnabled() ? "§ccan now hurt players" : "§ano longer hurt players"}§7.`);
      },
    });
  }
  const formName = s.sealed ? "§bSubmerged" : s.form === Form.Body ? "§8Petroleum Body" : s.form === Form.Dissolved ? "§8Dissolved" : "§6Human";
  const form = new ActionFormData()
    .title("§l§6Sekiyu §r§8Oil Console")
    .body(
      `Form: ${formName}§r\n\n§7Tap an ability to §fselect§7 it (it does not fire). Then §fUse§7 the core to cast it, and §fUse again§7 while it is active to §cignite§7 / reform / afterburn.\n` +
        "§8Quick switch: press Sneak = next ability (looking up = previous). Sneak + Use opens this console.",
    );
  for (const e of entries) {
    if (e.icon) form.button(e.label, e.icon);
    else form.button(e.label);
  }
  const res = await show(p, form);
  if (p.isValid) s.castGuardUntil = now() + CONTROLS.castGuard;
  if (!res || res.canceled || res.selection === undefined) return;
  await entries[res.selection]?.run();
}

async function guide(p: Player): Promise<void> {
  const lines = ABILITY_ORDER.map((id) => {
    const a = ABILITIES[id];
    return `${id === "inferno" ? "§4" : "§6"}§l${a.name}§r §8(${(a.cooldown / 20).toFixed(0)}s)\n§f${a.description}`;
  }).join("\n\n");
  const rules =
    "§l§6LOGIA§r §8- Petroleum Body / Infiltration: these hits pass through you: §7" +
    DAMAGE_RULES.physical.join(", ") +
    "§8. Explosions deal half. In human form one physical hit flows through you every 4s (Flow). Fall damage is halved (none as oil).\n\n" +
    "§l§cWEAKNESSES§r §8- Submerged in water: powers sealed, no Logia defence, forced back to flesh. Tridents, drowned and guardians are sea-forged: they hit you for real and break the oil form. Fire, lava and lightning hurt 60% more while you are oil.\n\n" +
    "§l§6OIL§r §8- Every ability leaves slicks: enemies in them are slowed, fire / lava / burning creatures ignite them, and fire spreads along connected oil. Your own fire never burns you. Nothing is permanent: oil evaporates or burns away. No oil gauge - you never run out.\n\n" +
    "§l§6CONTROLS§r §8- Use: cast. Use again: ignite / reform / afterburn. Press Sneak: next ability (look up = previous). Sneak + Use: this console.";
  const res = await show(p, new ActionFormData().title("§lPetroleum Guide").body(`${rules}\n\n${lines}`).button("§8Back"));
  if (res && !res.canceled) await openConsole(p);
}
