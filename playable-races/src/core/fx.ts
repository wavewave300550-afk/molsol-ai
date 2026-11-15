/** Particle and sound helpers. All calls are guarded: VFX must never break gameplay. */
import { Dimension, MolangVariableMap, Player, Vector3, system } from "@minecraft/server";

export type Vars = Record<string, number>;

function molang(vars?: Vars): MolangVariableMap | undefined {
  if (!vars) return undefined;
  const m = new MolangVariableMap();
  for (const [k, v] of Object.entries(vars)) m.setFloat(`variable.${k}`, v);
  return m;
}

export function particle(dim: Dimension, id: string, loc: Vector3, vars?: Vars): void {
  try {
    dim.spawnParticle(id, loc, molang(vars));
  } catch {
    /* chunk unloaded / out of world: ignore */
  }
}

/** Particle only the given player can see (targeting reticles, senses). */
export function privateParticle(p: Player, id: string, loc: Vector3, vars?: Vars): void {
  try {
    p.spawnParticle(id, loc, molang(vars));
  } catch {
    /* ignore */
  }
}

export function sound(dim: Dimension, id: string, loc: Vector3, volume = 1, pitch = 1): void {
  try {
    dim.playSound(id, loc, { volume, pitch });
  } catch {
    /* ignore */
  }
}

export function privateSound(p: Player, id: string, volume = 1, pitch = 1): void {
  try {
    p.playSound(id, { volume, pitch });
  } catch {
    /* ignore */
  }
}

/** Colour helpers for particles that read v.red/v.green/v.blue. */
export const RGB = {
  silver: { red: 0.85, green: 0.88, blue: 1.0 },
  crimson: { red: 1.0, green: 0.16, blue: 0.24 },
  gold: { red: 1.0, green: 0.8, blue: 0.3 },
  green: { red: 0.45, green: 1.0, blue: 0.45 },
  red: { red: 1.0, green: 0.3, blue: 0.3 },
};
export function rgb(c: { red: number; green: number; blue: number }): Vars {
  return { red: c.red, green: c.green, blue: c.blue };
}

/** Play a skeleton pose animation on a player (visible to everyone). */
export function pose(p: Player, anim: string, stopExpression?: string): void {
  const play = () => {
    try {
      if (p.isValid) p.playAnimation(`animation.plrace.pose.${anim}`, stopExpression ? { stopExpression, blendOutTime: 0.15 } : { blendOutTime: 0.15 });
    } catch {
      /* ignore */
    }
  };
  // a stop expression tests the worn form: give the client a moment to receive the new crest
  if (stopExpression) system.runTimeout(play, 3);
  else play();
}
