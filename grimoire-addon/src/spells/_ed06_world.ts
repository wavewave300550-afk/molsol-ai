import { GroundChange, SurfaceCell } from "../lib/terraform";
import { V3 } from "../lib/vec";
import { Frame, hash01 } from "./_ed06_motion";

/**
 * ED06 - the ancient world around the caster (world level): what the living ground turns into in each
 * habitat, the fog stages, the sunset.  Frame angles: 0 = ahead, +90 = right, +-180 behind.
 *
 *   domain (r < 4.6)          the caster's seal lies on bare moss
 *   meadow (ahead)            moss and podzol, ferns, grass, wildflowers - the open ground the dragons fight on
 *   volcanic field (ahead right, 10+ blocks out)  basalt and blackstone cracked by glowing magma veins
 *   lake shore (ahead left, 10+ blocks out)       mud and moss, ferns on the moss
 *   primeval forest (the sides and behind)        moss, podzol, rooted dirt; ferns, leaf litter, moss carpets,
 *                                                  firefly bushes that glow in the sunset
 */

/** Living-ground radius (blocks) and the four rings the heartbeats wake, inner to outer. */
export const GROUND_R = 22;
export const BANDS: [number, number][] = [[0, 7], [7, 12], [12, 17], [17, GROUND_R + 1]];
/** Fog stage per heartbeat (fogs/ed6_fog_*.json, tools/assets/ed6_atmos.py) and the detonation's ash. */
export const FOGS = ["grimoire:ed6_fog_1", "grimoire:ed6_fog_2", "grimoire:ed6_fog_3", "grimoire:ed6_fog_4"];
export const FOG_ASH = "grimoire:ed6_fog_ash";
/** Golden hour: the time of day the world is held at (12000 = the sun on the horizon). */
export const SUNSET = 12000;

const DOMAIN_R = 4.6;
type Sector = "domain" | "meadow" | "volcanic" | "shore" | "forest";

/** The habitat a ground cell belongs to (edges wander a little so they never read as straight lines). */
export function sectorOf(f: number, r: number, x: number, z: number): Sector {
  const d = Math.hypot(f, r);
  if (d < DOMAIN_R) return "domain";
  const a = (Math.atan2(r, f) * 180) / Math.PI + (hash01(x >> 1, z >> 1) - 0.5) * 16;
  if (d >= 10 + hash01(x, z + 7) * 2 && a >= 22 && a <= 78) return "volcanic";
  if (d >= 10 + hash01(x + 3, z) * 2 && a <= -22 && a >= -80) return "shore";
  if (Math.abs(a) < 100) return "meadow";
  return "forest";
}

/** A thin glowing crack through the volcanic field: magma along a few wandering lines out from the caster. */
function vein(f: number, r: number): boolean {
  const a = (Math.atan2(r, f) * 180) / Math.PI;
  const d = Math.hypot(f, r);
  if (d < 12) return false;
  for (const a0 of [34, 52, 66]) {
    const wob = Math.sin(d * 0.55 + a0) * 2.2;
    if (Math.abs(a - (a0 + wob)) * (Math.PI / 180) * d < 0.62) return true;
  }
  return false;
}

/** The living-ground plan for this cast: what each natural surface cell around the caster becomes. */
export function groundPlan(W: Frame): (c: SurfaceCell) => GroundChange | undefined {
  return (c) => {
    const rx = c.x + 0.5 - W.c.x, rz = c.z + 0.5 - W.c.z;
    const f = rx * W.F.x + rz * W.F.z, r = rx * W.R.x + rz * W.R.z;
    const h = (k: number) => hash01(c.x * 3 + k, c.z * 5 - k);
    const s = sectorOf(f, r, c.x, c.z);
    switch (s) {
      case "domain":
        return { ground: "minecraft:moss_block" };
      case "volcanic": {
        if (vein(f, r)) return { ground: "minecraft:magma" };
        return { ground: h(1) < 0.62 ? "minecraft:basalt" : h(2) < 0.7 ? "minecraft:blackstone" : "minecraft:smooth_basalt" };
      }
      case "shore": {
        const moss = h(3) < 0.35;
        return { ground: moss ? "minecraft:moss_block" : "minecraft:mud", plant: moss && h(4) < 0.5 ? "minecraft:fern" : undefined };
      }
      case "meadow": {
        const ground = h(5) < 0.72 ? "minecraft:moss_block" : "minecraft:podzol";
        const p = h(6);
        const plant = p < 0.22 ? "minecraft:short_grass" : p < 0.36 ? "minecraft:fern"
          : p < 0.43 ? "minecraft:wildflowers" : p < 0.47 ? "minecraft:pink_petals" : undefined;
        return { ground, plant, plantStates: petals(plant, h(7)) };
      }
      default: {
        const g = h(8);
        const ground = g < 0.5 ? "minecraft:moss_block" : g < 0.82 ? "minecraft:podzol" : "minecraft:dirt_with_roots";
        const p = h(9);
        const onMoss = ground === "minecraft:moss_block";
        const plant = p < 0.26 ? "minecraft:fern" : p < 0.4 ? "minecraft:short_grass" : p < 0.5 ? "minecraft:leaf_litter"
          : p < 0.55 && onMoss ? "minecraft:moss_carpet" : p < 0.585 && c.dist > 7 ? "minecraft:firefly_bush" : undefined;
        return { ground, plant, plantStates: petals(plant, h(10)) };
      }
    }
  };
}

/** Full clusters for the multi-part ground covers, turned at random. */
function petals(plant: string | undefined, u: number): Record<string, string | number> | undefined {
  if (plant !== "minecraft:pink_petals" && plant !== "minecraft:wildflowers" && plant !== "minecraft:leaf_litter") return undefined;
  const dirs = ["north", "east", "south", "west"];
  return { growth: 3, "minecraft:cardinal_direction": dirs[Math.floor(u * 4) % 4] };
}

// ---------------------------------------------------------------------------------------------- shot 1
/**
 * Shot 1 (the reveal): the camera pulls back over the caster's left shoulder, cranes up and swings a
 * third of the way round behind them, so the view sweeps across the awakened domain - the lake shore,
 * the moss disc and the seals ahead, the volcanic field - and settles high over the right shoulder.
 * u = 0..1 along the shot; C0 is the caster's feet.
 */
export function shotReveal(W: Frame, C0: V3, u: number): { at: V3; look: V3 } {
  const e = u * u * (3 - 2 * u);
  const ang = -120 - 120 * e;                          // frame angle: left-behind -> behind -> right-behind
  const rad = 6 + 5 * e, h = 2.6 + 9.4 * e;
  const at = W.polar(rad, ang, 0);
  const look = W.p(10 + 12 * e, 0, 0);
  return { at: { x: at.x, y: C0.y + h, z: at.z }, look: { x: look.x, y: C0.y + 1.2 + 1.5 * e, z: look.z } };
}
