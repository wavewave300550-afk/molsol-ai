import { Entity, Player, system } from "@minecraft/server";
import { fx } from "../core/fx.js";
import { alive } from "../core/targets.js";
import { add, v } from "../core/vec.js";

interface Dazzle {
  until: number;
  entity: Entity;
  stumble: boolean;
}

const dazzled = new Map<string, Dazzle>();

export function isDazzled(e: Entity): boolean {
  const d = dazzled.get(e.id);
  return !!d && d.until > system.currentTick;
}

export function dazzle(e: Entity, ticks: number, stumble = true): void {
  const t = system.currentTick;
  const cur = dazzled.get(e.id);
  dazzled.set(e.id, { until: Math.max(cur?.until ?? 0, t + ticks), entity: e, stumble });
  try {
    e.addEffect("slowness", ticks, { amplifier: 1, showParticles: false });
    e.addEffect("weakness", ticks, { amplifier: 1, showParticles: false });
    if (e instanceof Player) e.addEffect("blindness", ticks, { amplifier: 0, showParticles: false });
  } catch {
    /* immune */
  }
}

export function tickDazzle(): void {
  const t = system.currentTick;
  for (const [id, d] of dazzled) {
    if (!alive(d.entity) || d.until <= t) {
      dazzled.delete(id);
      continue;
    }
    if ((t + id.length) % 10 !== 0) continue;
    const e = d.entity;
    try {
      fx(e.dimension, "oddworks:dazzle_stars", add(e.getHeadLocation(), v(0, 0.55, 0)), { size: 1 });
      if (d.stumble && !(e instanceof Player) && e.isOnGround) {
        // blinded mobs stumble about
        const a = Math.random() * Math.PI * 2;
        e.applyKnockback({ x: Math.cos(a) * 0.22, z: Math.sin(a) * 0.22 }, 0.1);
      }
    } catch {
      /* ignore */
    }
  }
}

export function clearDazzle(id: string): void {
  dazzled.delete(id);
}
