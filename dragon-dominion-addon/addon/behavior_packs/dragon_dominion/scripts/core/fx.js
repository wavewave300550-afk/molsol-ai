// Particles, sounds, screen shake and HUD text. Every call is guarded: chunks can unload mid-fight.
import { MolangVariableMap } from "@minecraft/server";
import { safe } from "./util.js";

export function particle(dim, id, loc, vars) {
  safe(() => {
    if (vars) {
      const m = new MolangVariableMap();
      for (const [k, v] of Object.entries(vars)) m.setFloat(k, v);
      dim.spawnParticle(id, loc, m);
    } else dim.spawnParticle(id, loc);
  });
}

export function sound(dim, id, loc, volume = 1, pitch = 1) {
  safe(() => dim.playSound(id, loc, { volume, pitch }));
}

export function shake(players, intensity, seconds) {
  for (const p of players) safe(() => p.runCommand(`camerashake add @s ${intensity.toFixed(2)} ${seconds.toFixed(2)} positional`));
}

export function actionbar(players, text) {
  for (const p of players) safe(() => p.onScreenDisplay.setActionBar(text));
}

export function title(players, main, subtitle) {
  for (const p of players) {
    safe(() => p.onScreenDisplay.setTitle(main, { subtitle, fadeInDuration: 5, stayDuration: 40, fadeOutDuration: 15 }));
  }
}

export function message(players, text) {
  for (const p of players) safe(() => p.sendMessage(text));
}
