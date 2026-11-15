export const v3 = (x, y, z) => ({ x, y, z });
export const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
export const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
export const mul = (a, k) => ({ x: a.x * k, y: a.y * k, z: a.z * k });
export const dot = (a, b) => a.x * b.x + a.y * b.y + a.z * b.z;
export const len = (a) => Math.sqrt(dot(a, a));
export const dist = (a, b) => len(sub(a, b));
export const hdist = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
export function norm(a) {
    const l = len(a);
    return l > 1e-6 ? mul(a, 1 / l) : v3(0, 0, 0);
}
export function flat(a) {
    const l = Math.hypot(a.x, a.z);
    return l > 1e-6 ? v3(a.x / l, 0, a.z / l) : v3(0, 0, 1);
}
export function rotY(a, deg) {
    const r = (deg * Math.PI) / 180;
    const c = Math.cos(r);
    const s = Math.sin(r);
    return v3(a.x * c - a.z * s, a.y, a.x * s + a.z * c);
}
export function angleBetween(a, b) {
    const la = len(a);
    const lb = len(b);
    if (la < 1e-6 || lb < 1e-6)
        return 180;
    const c = Math.max(-1, Math.min(1, dot(a, b) / (la * lb)));
    return (Math.acos(c) * 180) / Math.PI;
}
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const center = (b) => v3(b.x + 0.5, b.y, b.z + 0.5);
export const floorV = (a) => v3(Math.floor(a.x), Math.floor(a.y), Math.floor(a.z));
export function secs(ticks) {
    const s = Math.max(0, ticks) / 20;
    return s >= 10 ? `${Math.ceil(s)}s` : `${s.toFixed(1)}s`;
}
export function meter(frac, width = 10, on = "|", off = ".") {
    const n = Math.round(clamp(frac, 0, 1) * width);
    return on.repeat(n) + off.repeat(width - n);
}
export function safeJson(raw, fallback) {
    if (typeof raw !== "string" || raw.length === 0)
        return fallback;
    try {
        const v = JSON.parse(raw);
        return v && typeof v === "object" ? v : fallback;
    }
    catch {
        return fallback;
    }
}
export function warn(msg, err) {
    console.warn(`[plrace] ${msg}${err !== undefined ? `: ${err instanceof Error ? err.message : String(err)}` : ""}`);
}
