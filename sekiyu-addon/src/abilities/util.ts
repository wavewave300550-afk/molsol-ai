import { Vector3 } from "@minecraft/server";

/** Minecraft yaw (degrees) that faces horizontal direction d (yaw 0 = +Z). */
export const yawOf = (d: Vector3): number => (Math.atan2(-d.x, d.z) * 180) / Math.PI;
