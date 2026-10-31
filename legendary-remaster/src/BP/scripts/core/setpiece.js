// 3D set-pieces: decorative props that appear inside skills and ultimates (no collision, no damage).
// Act numbers follow the order of each prop's acts in tools/props.py:
//   spirit_maw 1 gape, 2 snap, 3 fade      runestone 1 rise, 2 pulse, 3 sink
//   golden_lotus 1 bloom, 2 close          sun_halo 1 rise, 2 flare, 3 fade
//   suzu_bell 1 ring, 2 fade               herald_trumpet 1 blast, 2 fade
import { burst, C } from "./fx.js";
import { fire, propAct, removeProp, spawnProp } from "./hazards.js";
import { addTask } from "./tasks.js";
import { dirOfYaw } from "./vec.js";
/** Spawn a set-piece and play its entrance act. */
export function setPiece(dim, type, at, yaw, owner, act = 1) {
    const e = spawnProp(dim, type, at, yaw, owner);
    if (e && act)
        propAct(e, act);
    return e;
}
/** Play act `n` again from the start (drop to 0 for one tick). */
export function replayAct(e, n) {
    if (!e || !e.isValid)
        return;
    propAct(e, 0);
    addTask("replay", () => {
        propAct(e, n);
        return false;
    });
}
/** Play the exit act now and remove the set-piece `ticks` later. */
export function retire(e, act, ticks) {
    if (!e)
        return;
    if (act)
        propAct(e, act);
    addTask("retire", (age) => {
        if (age < ticks && e.isValid)
            return true;
        removeProp(e);
        return false;
    });
}
export function retireAll(list, act, ticks) {
    for (const e of list)
        retire(e, act, ticks);
    list.length = 0;
}
/** Chunks of rock thrown up by a heavy impact; they tumble, fall and break on the ground. */
export function debris(dim, center, n, power = 0.45, owner, col = C.root) {
    for (let i = 0; i < n; i++) {
        const yaw = (i / n) * 360 + Math.random() * 40;
        const d = dirOfYaw(yaw);
        const pos = { x: center.x + d.x * 1.4, y: center.y + 0.8, z: center.z + d.z * 1.4 };
        const e = spawnProp(dim, "debris", pos, yaw, owner);
        if (!e)
            continue;
        const sp = power * (0.6 + Math.random() * 0.7);
        fire({
            dim, pos, vel: { x: d.x * sp, y: 0.42 + Math.random() * 0.4, z: d.z * sp }, life: 34, radius: 0.1, dmg: 0, owner,
            gravity: 0.06, entity: e, ground: true,
            onEnd: (s) => burst(dim, s.pos, col, 8, 3, 0.3, 0.4),
        });
    }
}
/** Play acts at given ages ([[age, act], ...]) and remove the set-piece at `removeAt`. */
export function sequence(e, steps, removeAt) {
    if (!e)
        return;
    addTask("setpiece", (age) => {
        for (const [t, n] of steps)
            if (age === t)
                propAct(e, n);
        if (age < removeAt && e.isValid)
            return true;
        removeProp(e);
        return false;
    });
}
