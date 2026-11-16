import { Dimension, Vector3 } from "@minecraft/server";
import { particle } from "./util/fx.js";

/** The "Dying Star": a short-lived blessing left at VESPER-0's crash site. */
class Afterglow {
  private sites: { dim: Dimension; at: Vector3; left: number }[] = [];

  add(dim: Dimension, at: Vector3, ticks: number): void {
    this.sites.push({ dim, at, left: ticks });
  }

  tick(): void {
    for (const s of this.sites) {
      s.left--;
      if (s.left % 20 !== 0) continue;
      particle(s.dim, "dying_star", { x: s.at.x, y: s.at.y + 1.5, z: s.at.z });
      try {
        for (const p of s.dim.getPlayers({ location: s.at, maxDistance: 16 })) {
          p.addEffect("regeneration", 50, { amplifier: 1, showParticles: true });
        }
      } catch {
        /* unloaded */
      }
    }
    this.sites = this.sites.filter((s) => s.left > 0);
  }
}

export const afterglow = new Afterglow();
