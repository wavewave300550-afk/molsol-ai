export const v = (x, y, z) => ({ x, y, z });
export const UP = v(0, 1, 0);
export const add = (a, b) => v(a.x + b.x, a.y + b.y, a.z + b.z);
export const sub = (a, b) => v(a.x - b.x, a.y - b.y, a.z - b.z);
export const mul = (a, s) => v(a.x * s, a.y * s, a.z * s);
export const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a) => Math.hypot(a.x, a.y, a.z);
export const dist = (a, b) => len(sub(a, b));
export const lerp = (a, b, t) => add(a, mul(sub(b, a), t));
export const up = (a, h) => v(a.x, a.y + h, a.z);
export function norm(a) {
    const l = len(a);
    return l < 1e-6 ? v(0, 0, 1) : mul(a, 1 / l);
}
export const cross = (a, b) => v(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
/** Horizontal (y = 0) unit vector of a direction. */
export function flat(a) {
    const f = v(a.x, 0, a.z);
    return len(f) < 1e-4 ? v(0, 0, 1) : norm(f);
}
/** Player's right-hand side for a facing direction (Minecraft: +x east, +z south). */
export const rightOf = (dir) => norm(cross(flat(dir), UP));
export function rotY(a, degrees) {
    const r = (degrees * Math.PI) / 180;
    const c = Math.cos(r);
    const s = Math.sin(r);
    return v(a.x * c - a.z * s, a.y, a.x * s + a.z * c);
}
export function distToSegment(p, a, b) {
    const ab = sub(b, a);
    const l2 = dot(ab, ab);
    if (l2 < 1e-9)
        return dist(p, a);
    const t = Math.max(0, Math.min(1, dot(sub(p, a), ab) / l2));
    return dist(p, add(a, mul(ab, t)));
}
