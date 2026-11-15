/**
 * Blood Moon - an add-on controlled lunar event.
 *  Frequency: only on FULL MOON nights. Each full moon rolls `bloodChance`% (default 34%);
 *             a Blood Moon is guaranteed if 3 full moons in a row passed without one.
 *             (Full moons occur every 8 in-game days -> roughly every 24 days on average.)
 *  Duration:  moonrise (time 13000) until dawn (time 23460) of that night, or until the
 *             night is skipped by sleeping / /time.  Operators can start/stop it manually.
 *  Effects:   crimson fog for overworld players (vanilla fog stack, removed afterwards),
 *             Jackalopes awaken (see races/jackalope.ts).  State persists across reloads.
 */
import { MoonPhase, Player, world } from "@minecraft/server";
import { FOG_BLOOD_MOON, FOG_USER, WORLD_BLOODMOON } from "../config.js";
import { isOverworld, timeOfDay } from "../core/env.js";
import { settings } from "../core/settings.js";
import { safeJson, warn } from "../core/util.js";

interface BMState {
  phase: "idle" | "omen" | "active";
  day: number; // world day of the active/announced night
  missed: number; // full moons since the last Blood Moon
  force: boolean; // operator forced the next full moon
  checkedDay: number; // last day the dusk roll happened
  manual: boolean; // started by command (ends at the next dawn)
  sawNight: boolean;
}

let st: BMState | undefined;
const listeners: ((active: boolean) => void)[] = [];

function state(): BMState {
  if (!st) {
    let raw: unknown;
    try {
      raw = world.getDynamicProperty(WORLD_BLOODMOON);
    } catch {
      raw = undefined;
    }
    st = { phase: "idle", day: -1, missed: 0, force: false, checkedDay: -1, manual: false, sawNight: false, ...safeJson<Partial<BMState>>(raw, {}) };
  }
  return st;
}

function persist(): void {
  try {
    world.setDynamicProperty(WORLD_BLOODMOON, JSON.stringify(state()));
  } catch (e) {
    warn("blood moon save failed", e);
  }
}

export function onBloodMoonChange(fn: (active: boolean) => void): void {
  listeners.push(fn);
}

export function bloodMoonActive(): boolean {
  return state().phase === "active";
}

export function bloodMoonStatus(): string {
  const s = state();
  let phase = "idle";
  try {
    phase = MoonPhase[world.getMoonPhase()] ?? "?";
  } catch {
    /* ignore */
  }
  return `Blood Moon: ${s.phase}${s.manual ? " (manual)" : ""}; moon phase ${phase}; full moons since last: ${s.missed}; forced next: ${s.force}; chance ${settings().bloodChance}%`;
}

const isNight = (t: number) => t >= 12542 && t < 23460;

export function bloodMoonTick(): void {
  const s = state();
  const t = timeOfDay();
  let day = 0;
  try {
    day = world.getDay();
  } catch {
    day = 0;
  }
  if (s.phase === "active") {
    if (s.manual) {
      if (isNight(t)) s.sawNight = true;
      if (s.sawNight && !isNight(t)) end("dawn");
      return;
    }
    if (!isNight(t) || day !== s.day) end("dawn");
    return;
  }
  if (s.phase === "omen") {
    if (day !== s.day) {
      s.phase = "idle";
      persist();
    } else if (t >= 13000 && isNight(t)) start(false);
    return;
  }
  // idle: one roll per day at dusk, only on full moons
  if (t >= 12000 && t < 23000 && s.checkedDay !== day) {
    s.checkedDay = day;
    let phase = MoonPhase.NewMoon;
    try {
      phase = world.getMoonPhase();
    } catch {
      /* ignore */
    }
    if (phase === MoonPhase.FullMoon) {
      const roll = s.force || s.missed >= 3 || Math.random() * 100 < settings().bloodChance;
      if (roll) {
        s.phase = "omen";
        s.day = day;
        announce("§4The full moon is rising... red.", "§cSomething stirs in the lunar blood");
        if (t >= 13000) start(false);
      } else s.missed++;
    }
    persist();
  }
}

export function start(manual: boolean): void {
  const s = state();
  s.phase = "active";
  s.manual = manual;
  s.sawNight = isNight(timeOfDay());
  try {
    s.day = world.getDay();
  } catch {
    s.day = 0;
  }
  s.missed = 0;
  s.force = false;
  persist();
  announce("§4§lTHE BLOOD MOON RISES", "§cJackalopes awaken until dawn");
  for (const p of world.getPlayers()) applyFog(p);
  for (const fn of listeners) fn(true);
}

export function end(reason: string): void {
  const s = state();
  if (s.phase === "idle") return;
  const wasActive = s.phase === "active";
  s.phase = "idle";
  s.manual = false;
  persist();
  for (const p of world.getPlayers()) removeFog(p);
  if (wasActive) {
    announce("§7The Blood Moon wanes", reason === "dawn" ? "§8dawn breaks" : "§8the sky clears");
    for (const fn of listeners) fn(false);
  }
}

export function forceNext(): void {
  state().force = true;
  persist();
}

function announce(title: string, sub: string): void {
  for (const p of world.getPlayers()) {
    if (!isOverworld(p)) continue;
    try {
      p.onScreenDisplay.setTitle(title, { subtitle: sub, fadeInDuration: 20, stayDuration: 60, fadeOutDuration: 30 });
      p.playSound("ambient.weather.thunder", { volume: 0.5, pitch: 0.5 });
    } catch {
      /* ignore */
    }
  }
}

/** Push/pop the crimson fog for a player according to the event and their dimension. */
export function applyFog(p: Player): void {
  removeFog(p);
  if (!bloodMoonActive() || !settings().bloodFog || !isOverworld(p)) return;
  try {
    p.runCommand(`fog @s push ${FOG_BLOOD_MOON} ${FOG_USER}`);
  } catch {
    /* ignore */
  }
}

export function removeFog(p: Player): void {
  try {
    p.runCommand(`fog @s remove ${FOG_USER}`);
  } catch {
    /* nothing to remove */
  }
}
