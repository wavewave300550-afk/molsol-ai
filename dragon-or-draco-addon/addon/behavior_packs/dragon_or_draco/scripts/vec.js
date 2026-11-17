export const v3 = (x, y, z) => ({ x, y, z });
export const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a, k) => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a) => Math.sqrt(dot(a, a));
export const hlen = (a) => Math.sqrt(a.x * a.x + a.z * a.z);
export const dist = (a, b) => len(sub(a, b));
export const hdist = (a, b) => hlen(sub(a, b));
export const norm = (a) => {
    const l = len(a);
    return l > 1e-9 ? mul(a, 1 / l) : v3(0, 0, 1);
};
export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const DEG = Math.PI / 180;
/** Minecraft yaw (deg): 0 = facing +Z (south), 90 = facing -X (west). */
export function yawDir(yaw) {
    return v3(-Math.sin(yaw * DEG), 0, Math.cos(yaw * DEG));
}
/** Direction for a yaw and a pitch (deg, + = looking down). */
export function aimDir(yaw, pitch) {
    const c = Math.cos(pitch * DEG);
    return v3(-Math.sin(yaw * DEG) * c, -Math.sin(pitch * DEG), Math.cos(yaw * DEG) * c);
}
export function yawTo(from, to) {
    return Math.atan2(-(to.x - from.x), to.z - from.z) / DEG;
}
export function pitchTo(from, to) {
    const d = sub(to, from);
    return Math.atan2(-d.y, hlen(d)) / DEG;
}
/** Signed smallest difference b - a in degrees (-180..180). */
export function angleDiff(a, b) {
    let d = (b - a) % 360;
    if (d > 180)
        d -= 360;
    if (d < -180)
        d += 360;
    return d;
}
/** Rotate a yaw toward a goal by at most `step` degrees. */
export function turnToward(current, goal, step) {
    const d = angleDiff(current, goal);
    return current + clamp(d, -step, step);
}
/**
 * World position of a point given in the dragon's local frame
 * (fwd = in front, up, left = the dragon's left), for a dragon at `pos` with body yaw `yaw`.
 * Matches tools/kinematics.py: world = pos + Ryaw * (left, up, fwd).
 */
export function localToWorld(pos, yaw, fwd, up, left) {
    const c = Math.cos(yaw * DEG);
    const s = Math.sin(yaw * DEG);
    return v3(pos.x + left * c - fwd * s, pos.y + up, pos.z + left * s + fwd * c);
}
/** Absolute bearing (deg, 0 = straight ahead) of `p` as seen by a dragon at `pos` facing `yaw`. */
export function bearing(pos, yaw, p) {
    return Math.abs(angleDiff(yaw, yawTo(pos, p)));
}
