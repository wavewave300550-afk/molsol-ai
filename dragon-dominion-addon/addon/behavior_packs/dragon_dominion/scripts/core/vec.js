// Vector helpers. Minecraft yaw: 0 = facing +Z (south), 90 = facing -X (west).
export const v3 = (x, y, z) => ({ x, y, z });
export const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
export const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
export const distXZ = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
export const RAD = Math.PI / 180;

/** Unit horizontal direction a yaw faces. */
export const dirOf = (yaw) => ({ x: -Math.sin(yaw * RAD), y: 0, z: Math.cos(yaw * RAD) });
/** Yaw that faces from a toward b. */
export const yawTo = (a, b) => Math.atan2(-(b.x - a.x), b.z - a.z) / RAD;
/** Signed difference b - a wrapped to [-180, 180). */
export function angleDiff(a, b) {
  let d = (b - a) % 360;
  if (d >= 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}
/** Rotate yaw `from` toward `to` by at most `step` degrees. */
export function turnToward(from, to, step) {
  const d = angleDiff(from, to);
  if (Math.abs(d) <= step) return to;
  return from + Math.sign(d) * step;
}
/** Point at `fwd` blocks ahead, `right` blocks to the creature's right, `up` above origin. */
export function local(origin, yaw, fwd, right = 0, up = 0) {
  const f = dirOf(yaw);
  const r = { x: -f.z, z: f.x }; // creature's right-hand side when facing f
  return { x: origin.x + f.x * fwd + r.x * right, y: origin.y + up, z: origin.z + f.z * fwd + r.z * right };
}
/** Signed angle (deg) of point p relative to the facing of an entity at o with yaw (0 = dead ahead). */
export const relAngle = (o, yaw, p) => angleDiff(yaw, yawTo(o, p));
