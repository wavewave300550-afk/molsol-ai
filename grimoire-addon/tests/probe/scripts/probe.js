import { world, system, ItemStack, GameMode, BlockPermutation, EasingType } from "@minecraft/server";
import { spawnSimulatedPlayer } from "@minecraft/server-gametest";

const BOOK = { dw: "grimoire:divine_word", dn: "grimoire:dream_nightmare", ed: "grimoire:elemental_dragon" };
const ALL = ["dw01","dw02","dw03","dw04","dw05","dw06","dn01","dn02","dn03","dn04","dn05","dn06","ed01","ed02","ed03","ed04","ed05","ed06"];
const r3 = (n) => Math.round(n * 1000) / 1000;
const out = (o) => console.warn("[probe] " + JSON.stringify(o));
let sim, busy = false, queue = [];
const SEL = { dw: 0, dn: 0, ed: 0 };          // the add-on remembers the selected spell per book and player
const NAME = "T" + (Date.now() % 100000);
let BASE = { x: 0.5, z: 0.5 };

/** Every block (type + states) of the domain around the caster: compared before / during / after a cast. */
function snapshot(dim, cx, cy, cz, r = 24, dy0 = -6, dy1 = 8) {
  const m = new Map();
  for (let x = cx - r; x <= cx + r; x++) for (let z = cz - r; z <= cz + r; z++) for (let y = cy + dy0; y <= cy + dy1; y++) {
    let v = "unloaded";
    try {
      const b = dim.getBlock({ x, y, z });
      if (b) { const st = b.permutation.getAllStates(); v = b.typeId + (Object.keys(st).length ? JSON.stringify(st) : ""); }
    } catch (e) { v = "err"; }
    m.set(`${x},${y},${z}`, v);
  }
  return m;
}
function diff(a, b) {
  let n = 0; const ex = [], kinds = {};
  for (const [k, v] of a) {
    const w = b.get(k);
    if (w === v) continue;
    n++;
    const kk = (w ?? "?").replace("minecraft:", "").replace(/\{.*$/, "");
    kinds[kk] = (kinds[kk] ?? 0) + 1;
    if (ex.length < 6) ex.push([k, v, w]);
  }
  return { n, kinds, ex };
}
/** The engine's answer to the calls ED06's world helpers make, on a simulated player. */
function apiCheck(p) {
  const res = {};
  const tryIt = (k, f) => { try { res[k] = f() ?? "ok"; } catch (e) { res[k] = "ERR " + String(e); } };
  tryIt("fogPush", () => p.fogSettings.push("grimoire:ed6_fog_4", "probe"));
  tryIt("fogTags", () => p.fogSettings.getTags().join("|"));
  tryIt("fogRemove", () => p.fogSettings.remove("probe"));
  tryIt("fogUnknown", () => p.fogSettings.push("grimoire:no_such_fog", "probe"));
  tryIt("fogClean", () => p.fogSettings.remove("probe"));
  tryIt("camSet", () => p.camera.setCamera("minecraft:free", { location: { x: p.location.x, y: p.location.y + 5, z: p.location.z - 4 },
    facingLocation: p.location, easeOptions: { easeTime: 0.5, easeType: EasingType.InOutSine } }));
  tryIt("camClear", () => p.camera.clear());
  tryIt("inputCam", () => p.inputPermissions.isPermissionCategoryEnabled(1));
  for (const id of ["pink_petals", "wildflowers", "leaf_litter"]) {
    tryIt("perm_" + id, () => BlockPermutation.resolve("minecraft:" + id, { growth: 3, "minecraft:cardinal_direction": "south" }).getAllStates());
  }
  tryIt("time", () => [world.getTimeOfDay(), world.getAbsoluteTime(), world.gameRules.doDayLightCycle]);
  return res;
}

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
    if (ev.id === "probe:flatten") {
      // put the superflat profile back round the base (test world only): bedrock, dirt, dirt, grass, air
      const dim = world.getDimension("overworld");
      const r = Number(ev.message || 26), cx = Math.floor(BASE.x), cz = Math.floor(BASE.z);
      let n = 0;
      for (let x = cx - r; x <= cx + r; x++) for (let z = cz - r; z <= cz + r; z++) for (let y = -64; y <= -50; y++) {
        const want = y === -64 ? "minecraft:bedrock" : y < -61 ? "minecraft:dirt" : y === -61 ? "minecraft:grass_block" : "minecraft:air";
        const b = dim.getBlock({ x, y, z });
        if (b && (b.typeId !== want || Object.keys(b.permutation.getAllStates()).length)) { b.setType(want); n++; }
      }
      out({ k: "flatten", n });
    }
    if (ev.id === "probe:durable") {
      // what survives a hard crash next to block changes: an entity's dynamic property, a world dynamic property
      const dim = world.getDimension("overworld");
      const gy = ground(dim, BASE.x, BASE.z);
      const x0 = Math.floor(BASE.x) + 40, z0 = Math.floor(BASE.z) + 2;
      for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) dim.getBlock({ x: x0 + i, y: gy - 1, z: z0 + j }).setType("minecraft:moss_block");
      const e = dim.spawnEntity("probe:keeper", { x: x0 + 0.5, y: gy, z: z0 + 0.5 });
      const stamp = String(Date.now());
      e.setDynamicProperty("ledger", "x".repeat(5000) + stamp);
      e.addTag("probe_ledger");
      world.setDynamicProperty("probe:ledger", stamp);
      out({ k: "durable", stamp, at: [x0, gy - 1, z0] });
    }
    if (ev.id === "probe:durable_check") {
      const dim = world.getDimension("overworld");
      const gy = ground(dim, BASE.x, BASE.z);
      const x0 = Math.floor(BASE.x) + 40, z0 = Math.floor(BASE.z) + 2;
      let moss = 0;
      for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) if (dim.getBlock({ x: x0 + i, y: gy - 1, z: z0 + j })?.typeId === "minecraft:moss_block") moss++;
      const ents = dim.getEntities({ tags: ["probe_ledger"] }).map((e) => [e.id, String(e.getDynamicProperty("ledger") ?? "").slice(5000)]);
      out({ k: "durable_check", moss, ents, world: world.getDynamicProperty("probe:ledger") ?? null });
      if (ev.message === "clean") {
        for (const e of dim.getEntities({ tags: ["probe_ledger"] })) e.remove();
        for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) dim.getBlock({ x: x0 + i, y: gy - 1, z: z0 + j }).setType("minecraft:grass_block");
        world.setDynamicProperty("probe:ledger", undefined);
      }
    }
    if (ev.id === "probe:hash") {
      // every block of the domain round the base: compare before a cast and after a crash + reload
      const dim = world.getDimension("overworld");
      const gy = ground(dim, BASE.x, BASE.z);
      const snap = snapshot(dim, Math.floor(BASE.x), gy, Math.floor(BASE.z));
      let h = 2166136261, unl = 0;
      const kinds = {};
      for (const [k, v] of snap) {
        if (v === "unloaded") unl++;
        const t = v.replace("minecraft:", "").replace(/\{.*$/, "");
        kinds[t] = (kinds[t] ?? 0) + 1;
        for (const c of k + "=" + v + ";") { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
      }
      out({ k: "hash", label: ev.message, h: h.toString(16), cells: snap.size, unloaded: unl, gy, kinds,
        abs: world.getAbsoluteTime(), tod: world.getTimeOfDay(), props: world.getDynamicPropertyIds().filter((k) => k.startsWith("grim:")),
        markers: dim.getEntities({ type: "grimoire:ledger" }).length, constructs: dim.getEntities({ families: ["grimoire_construct"] }).length });
    }
    if (ev.id === "probe:body" || ev.id === "probe:head" || ev.id === "probe:tgt") { const e = ev.sourceEntity; if (e) { ROT[e.id] = ROT[e.id] ?? {}; ROT[e.id][ev.id.slice(6)] = -180 + Number(ev.message) * 22.5 + 11.25; } }
    if (ev.id === "probe:rot") rotTest();
  } catch (e) { out({ k: "err", e: String(e), s: e?.stack }); }
});

const ROT = {};
/** Does a script-set rotation reach the body / head yaw the client draws with?  (server-side Molang buckets, 22.5 deg) */
function rotTest() {
  const dim = world.getDimension("overworld");
  const gy = ground(dim, BASE.x, BASE.z) + 3;
  const mk = (type, x, opt) => dim.spawnEntity(type, { x: BASE.x + x, y: gy, z: BASE.z }, opt);
  const A = mk("probe:dummy_follow", 2, { initialRotation: 90 }), B = mk("probe:dummy_plain", 4, { initialRotation: 90 });
  const C = mk("probe:dummy_follow", 6), D = mk("probe:dummy_plain", 8);
  const E = mk("probe:dummy_follow", 10), F = mk("probe:dummy_plain", 12);
  const all = { A_follow_init90: A, B_plain_init90: B, C_follow: C, D_plain: D, E_follow_moving: E, F_plain_moving: F };
  const rep = (label) => { for (const [k, e] of Object.entries(all)) out({ k: "rot", label, who: k, set: r3(e.getRotation().y), body: ROT[e.id]?.body, head: ROT[e.id]?.head, tgt: ROT[e.id]?.tgt }); };
  let t = 0;
  const id = system.runInterval(() => {
    t++;
    if (t === 20) rep("after spawn");
    if (t === 21) { C.teleport(C.location, { rotation: { x: 0, y: -135 } }); D.teleport(D.location, { rotation: { x: 0, y: -135 } }); A.setRotation({ x: 0, y: 0 }); B.setRotation({ x: 0, y: 0 }); }
    if (t === 45) rep("C,D teleport-in-place to -135; A,B setRotation 0");
    if (t === 46) { C.teleport(C.location, { rotation: { x: 0, y: 45 } }); D.teleport(D.location, { rotation: { x: 0, y: 45 } }); }
    if (t === 70) rep("C,D teleport-in-place to 45");
    // E,F: move every tick along +X (travel direction = yaw -90) while facing yaw 90 (backwards)
    if (t >= 71 && t < 131) { for (const e of [E, F]) { const l = e.location; e.teleport({ x: l.x + 0.25, y: l.y, z: l.z }, { rotation: { x: 0, y: 90 } }); } }
    if (t === 100 || t === 130) rep("E,F moving +X while facing 90, t=" + t);
    if (t === 150) rep("E,F stopped");
    if (t === 152) { for (const e of Object.values(all)) e.remove(); system.clearRun(id); out({ k: "rot_done" }); }
  }, 1);
}

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
  const world6 = id === "ed06";
  const bx = Math.floor(BASE.x), bz = Math.floor(BASE.z);
  let before;
  if (world6) {
    out({ k: "api", r: apiCheck(sim) });
    before = snapshot(dim, bx, gy, bz);
    out({ k: "snap", when: "before", cells: before.size, abs: world.getAbsoluteTime() });
  }
  const abs0 = world.getAbsoluteTime();
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
      if (world6 && t % 20 === 0) {
        let fog = "?", inp = "?";
        try { fog = sim.fogSettings.getTags().join("|"); } catch (e) { fog = "ERR " + e; }
        try { inp = [1, 4, 5, 6].map((c) => (sim.inputPermissions.isPermissionCategoryEnabled(c) ? 1 : 0)).join(""); } catch (e) { inp = "ERR " + e; }
        out({ k: "w", t, tod: world.getTimeOfDay(), fog, inp, hp: Math.round(sim.getComponent("minecraft:health")?.currentValue ?? -1) });
      }
      if (world6 && t === relAt + 420) { const d = diff(before, snapshot(dim, bx, gy, bz)); out({ k: "snap", when: "mid", t, n: d.n, kinds: d.kinds, ex: d.ex }); }
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
        if (world6) {
          const d = diff(before, snapshot(dim, bx, gy, bz));
          let fog = "?"; try { fog = sim.fogSettings.getTags().join("|"); } catch (e) { fog = "ERR " + e; }
          out({ k: "snap", when: "after", n: d.n, kinds: d.kinds, ex: d.ex, clockDrift: world.getAbsoluteTime() - abs0 - t,
            fog, ledger: world.getDynamicPropertyIds().filter((k) => k.startsWith("grim:")) });
        }
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
