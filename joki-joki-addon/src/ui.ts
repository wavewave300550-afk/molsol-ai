import { CommandPermissionLevel, Player, system, world } from "@minecraft/server";
import { ActionFormData, ActionFormResponse, FormCancelationReason } from "@minecraft/server-ui";
import { ABILITIES, ABILITY_ORDER, CONTROLS, DP, HEAT, Mode, MODES, WORLD_PVP } from "./config.js";
import { pvpEnabled } from "./core/combat.js";
import { cooldownLeft, selectAbility } from "./casting.js";
import { heatBar } from "./hud.js";
import { setMode } from "./modes.js";
import { giveValve } from "./power.js";
import { isOverheated, isOwner, notice, now, state } from "./state.js";

const ICON = (name: string): string => `textures/joki/ui/${name}`;

/** Show a form, retrying while the player is busy (chat / another screen still closing). */
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

/** The Steam Console: one-tap access to every ability, gear and setting (touch friendly). */
export async function openConsole(p: Player): Promise<void> {
  if (!isOwner(p)) {
    const res = await show(
      p,
      new ActionFormData()
        .title("§l§6Steam Valve")
        .body(
          "§7This valve answers only to someone whose body runs on steam.\n\n" +
            "§fEat the §cJōki Jōki no Mi§f to awaken the Steam Pressure power.\n" +
            "§8Creative inventory, or: /give @s joki:joki_fruit",
        )
        .button("§8Close"),
    );
    void res;
    return;
  }
  const s = state(p);
  const t = now();
  const over = isOverheated(s);
  const spec = MODES[s.mode];
  const entries: Entry[] = [];

  ABILITY_ORDER.forEach((id, i) => {
    const a = ABILITIES[id];
    const left = cooldownLeft(p, id);
    const status = over ? "§4locked" : left > 0 ? `§7${(left / 20).toFixed(1)}s` : "§2ready";
    const heat = Math.round(a.heat * spec.heatMult);
    entries.push({
      label: `${i === s.selected ? "§l" : ""}${id === "redline" ? "§4" : "§0"}${a.name}${i === s.selected ? " §r§6<" : ""}\n§r§8+${heat} heat | ${status}`,
      icon: ICON(id),
      run: () => selectAbility(p, i),
    });
  });

  const gear = (m: Mode, label: string, sub: string) =>
    entries.push({
      label: `${s.mode === m ? "§l" : ""}${MODES[m].color === "§7" ? "§8" : MODES[m].color}${label}${s.mode === m ? " §r§8(active)" : ""}\n§r§8${sub}`,
      icon: ICON(`mode_${m}`),
      run: () => {
        if (over && m !== Mode.Normal) {
          notice(s, "§cOVERHEATED §7- gears locked", 40);
          return;
        }
        if (s.mode === Mode.Redline && m !== Mode.Normal) {
          notice(s, "§4Redline §7runs until it ends or you vent", 40);
          return;
        }
        setMode(p, s, m);
        if (m === Mode.Normal) s.redlineUntil = 0;
      },
    });
  gear(Mode.Heat, "Gear: HEAT", "speed I, strength I, slow cooling");
  gear(Mode.Pressure, "Gear: PRESSURE", "speed II, strength II, x1.35 heat");
  gear(Mode.Normal, "Vent to NORMAL", "drop all gears, fastest cooling");

  entries.push({
    label: `§3Ability HUD: ${s.hudEnabled ? "§2ON" : "§4OFF"}\n§8heat gauge & cooldowns`,
    icon: ICON("hud"),
    run: () => {
      s.hudEnabled = !s.hudEnabled;
      p.setDynamicProperty(DP.hud, s.hudEnabled);
      p.sendMessage(`§7Steam HUD ${s.hudEnabled ? "§aenabled" : "§cdisabled"}§7.`);
    },
  });
  entries.push({ label: "§1Power Guide\n§8what every ability does", icon: ICON("guide"), run: () => guide(p) });
  entries.push({
    label: "§2Summon a new Valve\n§8if yours was lost",
    icon: "textures/items/joki/steam_valve",
    run: () => {
      if (!giveValve(p)) p.sendMessage("§7You already carry a Steam Valve.");
    },
  });
  if (p.commandPermissionLevel >= CommandPermissionLevel.GameDirectors) {
    entries.push({
      label: `§4PvP steam damage: ${pvpEnabled() ? "§2ON" : "§8OFF"}\n§8world rule (operators)`,
      run: () => {
        world.setDynamicProperty(WORLD_PVP, !pvpEnabled());
        world.sendMessage(`§c[Jōki] §7Steam abilities ${pvpEnabled() ? "§ccan now hurt players" : "§ano longer hurt players"}§7.`);
      },
    });
  }

  const status = over
    ? `§4§lOVERHEATED§r §7- locked ${((s.overheatUntil - t) / 20).toFixed(1)}s`
    : `${spec.color}§l${spec.name}§r §7gear${s.heat >= HEAT.warnAt ? " §c§l- CRITICAL" : ""}`;
  const form = new ActionFormData()
    .title("§l§cJōki Jōki §r§8Steam Console")
    .body(
      `${status}\n${heatBar(s.heat, over, t)} §r§f${Math.floor(s.heat)}% \n\n` +
        "§7Tap an ability to §fselect§7 it (it does not fire). Then §fUse§7 the valve to fire.\n" +
        "§8Quick switch: §7Sneak + Use §8= next skill, §7looking up §8= previous, §7looking down §8= this console.",
    );
  for (const e of entries) {
    if (e.icon) form.button(e.label, e.icon);
    else form.button(e.label);
  }
  const res = await show(p, form);
  // the finger that closes the form is often still on the screen: never let it cast
  if (p.isValid) s.castGuardUntil = now() + CONTROLS.castGuard;
  if (!res || res.canceled || res.selection === undefined) return;
  const chosen = entries[res.selection];
  if (chosen) await chosen.run();
}

async function guide(p: Player): Promise<void> {
  const lines = ABILITY_ORDER.map((id) => {
    const a = ABILITIES[id];
    return `${id === "redline" ? "§4" : "§6"}§l${a.name}§r §8(${a.heat} heat, ${(a.cooldown / 20).toFixed(a.cooldown % 20 ? 1 : 0)}s)\n§f${a.description}`;
  }).join("\n\n");
  const gears =
    "§l§7NORMAL§r §8- no buffs, fast cooling. Casting any ability shifts to HEAT.\n" +
    "§l§6HEAT§r §8- speed I, strength I (+3 melee), steam vents, slow cooling.\n" +
    "§l§cPRESSURE§r §8- speed II, strength II, abilities x1.4 power, heat x1.35, heat creeps up.\n" +
    "§l§4REDLINE§r §8- 12s: speed III, strength III, x1.75 power, -40% cooldowns, heat x1.9 and +4/s.\n\n" +
    "§4§lOVERHEAT§r §8at 100 heat: gears drop, every ability locks for 10s, brief slowness. Standing in water cools faster.\n\n" +
    "§l§6CONTROLS§r §8(hold the Steam Valve)\n§7Use §8- fire the selected skill\n§7Sneak + Use §8- next skill (does not fire)\n" +
    "§7Sneak + Use looking up §8- previous skill\n§7Sneak + Use looking down §8- open this console";
  const res = await show(p, new ActionFormData().title("§lSteam Pressure Guide").body(`${gears}\n\n${lines}`).button("§8Back"));
  if (res && !res.canceled) await openConsole(p);
}
