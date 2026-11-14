// Scene recorder (not a test): casts each spell on the mock server and writes a per-tick trace
// of every spell entity, particle, sound and temporary block to tests/.out/trace/<id>.json.
// tools/scene.py turns the traces into pictures.   node tests/run.mjs trace [dw01,dn03]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const IDS = ["dw01", "dw02", "dw03", "dw04", "dw05", "dw06", "dn01", "dn02", "dn03", "dn04", "dn05", "dn06",
  "ed01", "ed02", "ed03", "ed04", "ed05", "ed06"];
const BOOK = { dw: "grimoire:divine_word", dn: "grimoire:dream_nightmare", ed: "grimoire:elemental_dragon" };

export default function ({ mock, arg }) {
  const { world, tick, addPlayer, addMob, ItemStack, reset, constructs, system } = mock;
  const A = world.afterEvents;
  const only = arg ? arg.split(",") : null;
  const out = path.join(here, ".out/trace");
  fs.mkdirSync(out, { recursive: true });
  const r3 = (n) => Math.round(n * 1000) / 1000;
  let rec = null;
  const P = mock.Dimension.prototype;
  const oP = P.spawnParticle, oS = P.playSound, oB = P.setBlockType;
  P.spawnParticle = function (id, loc, v) { if (rec) rec.particles.push([rec.t, id, r3(loc.x), r3(loc.y), r3(loc.z)]); return oP.call(this, id, loc, v); };
  P.playSound = function (id, loc, o) { if (rec) rec.sounds.push([rec.t, id, r3(loc.x), r3(loc.y), r3(loc.z)]); return oS.call(this, id, loc, o); };
  P.setBlockType = function (loc, t) { if (rec) rec.blocks.push([rec.t, Math.floor(loc.x), Math.floor(loc.y), Math.floor(loc.z), typeof t === "string" ? t : t.id]); return oB.call(this, loc, t); };

  // TERRAIN=hills casts on rolling ground with a ledge instead of the flat test world
  const hills = process.env.TERRAIN === "hills";
  const H = (x, z) => 64 + Math.round(2.6 * Math.sin(x / 6.5 + 0.8) + 2.2 * Math.cos(z / 7.5 - 0.4) + (x > 9 && z > 4 ? 3 : 0));
  mock.setTerrain(hills ? H : null);
  const gy = (x, z) => mock.heightAt(x, z);
  for (const id of IDS) {
    if (only && !only.includes(id)) continue;
    reset();
    const pre = id.slice(0, 2), idx = Number(id.slice(2)) - 1;
    const p = addPlayer("Tracer_" + id, { x: 0.5, y: gy(0.5, 0.5), z: 0.5 });
    p.rotation = { x: 12, y: 0 };
    p.hotbar[0] = new ItemStack(BOOK[pre]);
    const mobs = [];
    for (const [x, z] of [[0, 9], [3, 11], [-3, 10], [1.5, 13], [-2, 14], [5, 9]]) mobs.push(addMob("minecraft:zombie", { x: x + 0.5, y: gy(x + 0.5, z + 0.5), z: z + 0.5 }, 5000));
    tick(2);
    for (let i = 0; i < idx; i++) { p.isSneaking = true; tick(1); p.isSneaking = false; tick(1); }
    rec = { id, t: 0, particles: [], sounds: [], blocks: [], actors: {}, mobs: [], caster: [], release: 0 };
    const snap = () => {
      const seen = new Set();
      for (const e of constructs()) {
        seen.add(e.id);
        let a = rec.actors[e.id];
        if (!a) a = rec.actors[e.id] = { type: e.typeId.slice(9), spawn: rec.t, end: -1, f: [] };
        const row = [rec.t, r3(e.location.x), r3(e.location.y), r3(e.location.z), r3(e.rotation.y),
          e.props["grimoire:state"] ?? 0, e.props["grimoire:kind"] ?? 0, e.props["grimoire:size"] ?? 1, e.props["grimoire:skin"] ?? 0];
        const last = a.f[a.f.length - 1];
        if (!last || row.slice(1).some((v, i) => v !== last[i + 1])) a.f.push(row);
      }
      for (const [k, a] of Object.entries(rec.actors)) if (a.end < 0 && !seen.has(k)) a.end = rec.t;
      if (rec.t % 5 === 0) {
        rec.mobs.push([rec.t, ...mobs.map((m) => [r3(m.location.x), r3(m.location.y), r3(m.location.z), m.isValid && m.health > 0 ? 1 : 0])]);
        rec.caster.push([rec.t, r3(p.location.x), r3(p.location.y), r3(p.location.z), p.rotation.y, p.rotation.x]);
      }
    };
    const step = (n) => { for (let i = 0; i < n; i++) { tick(1); rec.t++; snap(); } };
    A.itemStartUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 1 });
    step(30);
    rec.release = rec.t;
    A.itemReleaseUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 1 });
    A.itemStopUse.emit({ source: p, itemStack: p.hotbar[0], useDuration: 0 });
    let saw = false;
    for (let i = 0; i < 3600; i++) {
      step(1);
      const n = constructs().length;
      if (n > 0 && rec.t > rec.release + 2) saw = true;
      if (saw && n === 0 && rec.t > rec.release + 20) break;
    }
    step(10);
    rec.ticks = rec.t;
    if (hills) { rec.terrain = { x0: -48, z0: -40, n: 97, h: [] }; for (let z = -40; z < 57; z++) for (let x = -48; x < 49; x++) rec.terrain.h.push(gy(x, z)); }
    rec.problems = [...mock.problems];
    rec.dmg = mobs.map((m) => Math.round(5000 - m.health));
    const done = rec; rec = null;
    fs.writeFileSync(path.join(out, `${id}${hills ? "_hills" : ""}.json`), JSON.stringify(done));
    console.log(`  trace ${id}: ${done.ticks} ticks, ${Object.keys(done.actors).length} actors, ${done.particles.length} particles, ${done.blocks.length} block edits`);
  }
  P.spawnParticle = oP; P.playSound = oS; P.setBlockType = oB;
  mock.setTerrain(null);
}
