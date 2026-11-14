import { world, system, ItemStack, GameMode } from "@minecraft/server";
import { spawnSimulatedPlayer } from "@minecraft/server-gametest";

const BOOK = { dw: "grimoire:divine_word", dn: "grimoire:dream_nightmare", ed: "grimoire:elemental_dragon" };
const ALL = ["dw01","dw02","dw03","dw04","dw05","dw06","dn01","dn02","dn03","dn04","dn05","dn06","ed01","ed02","ed03","ed04","ed05","ed06"];
const r3 = (n) => Math.round(n * 1000) / 1000;
const out = (o) => console.warn("[probe] " + JSON.stringify(o));
let sim, busy = false, queue = [];
const SEL = { dw: 0, dn: 0, ed: 0 };          // the add-on remembers the selected spell per book and player
const NAME = "T" + (Date.now() % 100000);
let BASE = { x: 0.5, z: 0.5 };

function ground(dim, x, z) {
  try { const b = dim.getTopmostBlock({ x, z }); return b ? b.location.y + 1 : undefined; } catch (e) { return undefined; }
}

system.afterEvents.scriptEventReceive.subscribe((ev) => {
  try {
    if (ev.id === "probe:base") { const [x, z] = ev.message.split(" ").map(Number); BASE = { x: x + 0.5, z: z + 0.5 }; out({ k: "base", BASE }); }
    if (ev.id === "probe:run") {
      const [what, mode] = ev.message.split(" ");
      for (const id of (what === "all" ? ALL : what.split(","))) queue.push({ id, mode: mode ?? "mobs" });
      pump();
    }
    if (ev.id === "probe:terrain") terrain();
  } catch (e) { out({ k: "err", e: String(e), s: e?.stack }); }
});

function pump() {
  if (busy || !queue.length) { if (!busy) out({ k: "idle" }); return; }
  busy = true;
  const job = queue.shift();
  try { run(job.id, job.mode); } catch (e) { out({ k: "err", id: job.id, e: String(e), s: e?.stack }); busy = false; system.runTimeout(pump, 20); }
}

function terrain() {
  const dim = world.getDimension("overworld");
  const x0 = Math.floor(BASE.x) - 48, z0 = Math.floor(BASE.z) - 40, n = 97;
  let zi = 0;
  const id = system.runInterval(() => {
    const row = [];
    for (let xi = 0; xi < n; xi++) row.push(ground(dim, x0 + xi + 0.5, z0 + zi + 0.5) ?? -999);
    out({ k: "terr", x0, z0, n, zi, row });
    if (++zi >= n) { system.clearRun(id); out({ k: "terr_done" }); }
  }, 1);
}

function run(id, mode) {
  const dim = world.getDimension("overworld");
  const pre = id.slice(0, 2), idx = Number(id.slice(2)) - 1;
  const gy = ground(dim, BASE.x, BASE.z);
  if (gy === undefined) throw new Error("base not loaded");
  if (!sim || !sim.isValid) {
    sim = spawnSimulatedPlayer({ dimension: dim, x: BASE.x, y: gy, z: BASE.z }, NAME, GameMode.Creative);
  }
  sim.teleport({ x: BASE.x, y: gy, z: BASE.z }, { rotation: { x: 12, y: 0 } });
  const mobs = [];
  if (mode === "mobs") {
    for (const [x, z] of [[0, 9], [3, 11], [-3, 10], [1.5, 13], [-2, 14], [5, 9]]) {
      const mx = BASE.x + x, mz = BASE.z + z, my = ground(dim, mx, mz) ?? gy;
      try { const m = dim.spawnEntity("minecraft:husk", { x: mx, y: my, z: mz }); m.addTag("probe_mob"); mobs.push(m); } catch (e) { out({ k: "err", e: "mob " + e }); }
    }
  }
  const rec = { id, t: 0, release: 0, last: {}, seen: false, quiet: 0 };
  out({ k: "start", id, mode, base: [BASE.x, gy, BASE.z] });
  const events = [];
  const subs = [
    world.afterEvents.itemStartUse.subscribe((e) => { if (e.source.id === sim.id) out({ k: "ev", t: rec.t, e: "itemStartUse", item: e.itemStack?.typeId, dur: e.useDuration }); }),
    world.afterEvents.itemReleaseUse.subscribe((e) => { if (e.source.id === sim.id) out({ k: "ev", t: rec.t, e: "itemReleaseUse", dur: e.useDuration }); }),
    world.afterEvents.itemStopUse.subscribe((e) => { if (e.source.id === sim.id) out({ k: "ev", t: rec.t, e: "itemStopUse", dur: e.useDuration }); }),
    world.afterEvents.itemUse.subscribe((e) => { if (e.source.id === sim.id) out({ k: "ev", t: rec.t, e: "itemUse" }); }),
  ];
  const unsub = () => { world.afterEvents.itemStartUse.unsubscribe(subs[0]); world.afterEvents.itemReleaseUse.unsubscribe(subs[1]); world.afterEvents.itemStopUse.unsubscribe(subs[2]); world.afterEvents.itemUse.unsubscribe(subs[3]); };
  // schedule the cast through the real input path
  const T0 = 10;                       // settle
  const presses = (idx - SEL[pre] + 6) % 6;
  SEL[pre] = idx;
  const selEnd = T0 + presses * 4;
  const holdAt = selEnd + 6, relAt = holdAt + 30;
  const loop = system.runInterval(() => {
    try {
      rec.t++;
      const t = rec.t;
      if (t === 2) { sim.setItem(new ItemStack(BOOK[pre], 1), 0, true); }
      if (t === 4) { sim.teleport({ x: BASE.x, y: gy, z: BASE.z }, { rotation: { x: 12, y: 0 } }); sim.lookAtLocation({ x: BASE.x, y: gy, z: BASE.z + 7.6 }, "Continuous"); }
      if (t >= T0 && t < selEnd) { const ph = (t - T0) % 4; if (ph === 0) sim.isSneaking = true; if (ph === 2) sim.isSneaking = false; }
      if (t === selEnd) sim.isSneaking = false;
      if (t === holdAt) { const ok = sim.useItemInSlot(0); out({ k: "ev", t, e: "useItemInSlot", ok, rot: sim.getRotation(), view: sim.getViewDirection() }); }
      if (t === relAt) { rec.release = t; sim.stopUsingItem(); out({ k: "ev", t, e: "stopUsingItem" }); }
      // snapshot
      const cur = {};
      let n = 0;
      for (const e of dim.getEntities({ families: ["grimoire_construct"] })) {
        n++;
        const l = e.location, r = e.getRotation();
        const row = [e.typeId.slice(9), r3(l.x), r3(l.y), r3(l.z), r3(r.y), e.getProperty("grimoire:state") ?? 0, e.getProperty("grimoire:kind") ?? 0,
          r3(e.getProperty("grimoire:size") ?? 1), e.getProperty("grimoire:skin") ?? 0];
        const s = row.join(",");
        cur[e.id] = s;
        if (rec.last[e.id] !== s) out({ k: "a", t, i: e.id, r: row });
      }
      for (const i of Object.keys(rec.last)) if (!(i in cur)) out({ k: "x", t, i });
      rec.last = cur;
      if (t % 5 === 0) {
        const pl = sim.location, pr = sim.getRotation();
        out({ k: "p", t, c: [r3(pl.x), r3(pl.y), r3(pl.z), r3(pr.y), r3(pr.x)], m: mobs.map((m) => m.isValid ? [r3(m.location.x), r3(m.location.y), r3(m.location.z), 1] : [0, 0, 0, 0]) });
      }
      if (t > relAt + 2 && n > 0) rec.seen = true;
      rec.quiet = n === 0 ? rec.quiet + 1 : 0;
      const done = (rec.seen && rec.quiet > 30 && t > relAt + 20) || t > relAt + 1700 || (!rec.seen && t > relAt + 120);
      if (done) {
        system.clearRun(loop); unsub();
        let hp = [];
        for (const m of mobs) { try { if (m.isValid) { hp.push(Math.round(m.getComponent("minecraft:health").currentValue)); m.remove(); } else hp.push(-1); } catch { hp.push(-2); } }
        out({ k: "end", id, ticks: t, release: rec.release, seen: rec.seen, hp, cd: sim.getDynamicProperty("grim:cd") });
        try { sim.setDynamicProperty("grim:cd", undefined); sim.setDynamicProperty("grim:sel", undefined); } catch {}
        busy = false;
        system.runTimeout(pump, 40);
      }
    } catch (e) {
      out({ k: "err", id, t: rec.t, e: String(e), s: e?.stack });
      system.clearRun(loop); unsub(); busy = false; system.runTimeout(pump, 40);
    }
  }, 1);
}
out({ k: "loaded" });
