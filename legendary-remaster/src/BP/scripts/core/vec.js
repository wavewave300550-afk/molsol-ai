export const v = (x, y, z) => ({ x, y, z });
export const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const scale = (a, k) => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const len = (a) => Math.hypot(a.x, a.y, a.z);
export const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
export const flatDist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
export const lerp = (a, b, t) => ({
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    z: a.z + (b.z - a.z) * t,
});
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
export function norm(a) {
    const l = len(a);
    return l > 1e-6 ? scale(a, 1 / l) : { x: 0, y: 0, z: 1 };
}
/** Horizontal unit direction from a to b (falls back to +Z). */
export function flatDir(a, b) {
    const dx = b.x - a.x;
    const dz = b.z - a.z;
    const l = Math.hypot(dx, dz);
    return l > 1e-6 ? { x: dx / l, y: 0, z: dz / l } : { x: 0, y: 0, z: 1 };
}
/** Minecraft yaw (degrees, 0 = +Z/south, 90 = -X/west) of a horizontal direction. */
export const yawOf = (d) => (Math.atan2(-d.x, d.z) * 180) / Math.PI;
export const dirOfYaw = (yaw) => {
    const r = (yaw * Math.PI) / 180;
    return { x: -Math.sin(r), y: 0, z: Math.cos(r) };
};
export const pitchOf = (d) => (-Math.atan2(d.y, Math.hypot(d.x, d.z)) * 180) / Math.PI;
/** Rotate a horizontal vector by `deg` degrees around +Y (same sense as yaw). */
export function rotY(d, deg) {
    return dirOfYaw(yawOf(d) + deg);
}
export function angleDiff(a, b) {
    let d = (b - a) % 360;
    if (d > 180)
        d -= 360;
    if (d < -180)
        d += 360;
    return d;
}
/** Distance from point p to the segment ab, and the projection parameter t (0..1). */
export function segDist(p, a, b) {
    const ab = sub(b, a);
    const l2 = ab.x * ab.x + ab.y * ab.y + ab.z * ab.z;
    const t = l2 > 1e-9 ? clamp(((p.x - a.x) * ab.x + (p.y - a.y) * ab.y + (p.z - a.z) * ab.z) / l2, 0, 1) : 0;
    return { d: dist(p, add(a, scale(ab, t))), t };
}
/** Horizontal (XZ) distance from p to segment ab. */
export function flatSegDist(p, a, b) {
    return segDist({ x: p.x, y: 0, z: p.z }, { x: a.x, y: 0, z: a.z }, { x: b.x, y: 0, z: b.z });
}
export function randIn(lo, hi) {
    return lo + Math.random() * (hi - lo);
}
export function pick(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}
