// Fight simulation for the remastered Legendary & Divine Beings.
// The built scripts run against a strict mock of @minecraft/server; each of the six legends is
// summoned and fought to death by two simulated players. Every id (sound, particle, effect,
// entity, event, property range) is validated by the mock; script warnings fail the run.
//     python3 tools/build.py && node tools/smoke/smoke.mjs
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const BP = path.join(ROOT, "build", "Legends_BP");
const RP = path.join(ROOT, "build", "Legends_RP");
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]));

const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "reference.json"), "utf8"));
const effects = JSON.parse(fs.readFileSync(path.join(ROOT, "tools", "vanilla", "effects.json"), "utf8"));
const particles = [...ref.particles, ...walk(path.join(RP, "particles")).map((f) => JSON.parse(fs.readFileSync(f, "utf8")).particle_effect.description.identifier)];
const entities = {
  "minecraft:item": { families: [], events: [] },
  "minecraft:xp_orb": { families: [], events: [] },
  "minecraft:player": { families: ["player"], events: [], health: 20 },
};
for (const f of walk(path.join(BP, "entities"))) {
  const e = JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:entity"];
  const c = e.components ?? {};
  entities[e.description.identifier] = { families: c["minecraft:type_family"]?.family ?? [], events: Object.keys(e.events ?? {}), health: c["minecraft:health"]?.max, properties: e.description.properties };
}
const items = walk(path.join(BP, "items")).map((f) => JSON.parse(fs.readFileSync(f, "utf8"))["minecraft:item"].description.identifier);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "legends-smoke-"));
fs.writeFileSync(path.join(tmp, "data.json"), JSON.stringify({ effects, particles, sounds: ref.sounds, entities, items, foods: [], cooldowns: [] }));
process.env.TRIBES_MOCK_DATA = path.join(tmp, "data.json");
fs.cpSync(path.join(BP, "scripts"), path.join(tmp, "scripts"), { recursive: true });
fs.writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ type: "module" }));
for (const [pkg, file] of [["server", "mock-server.mjs"], ["server-ui", "mock-server-ui.mjs"]]) {
  const dir = path.join(tmp, "node_modules", "@minecraft", pkg);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(HERE, file), path.join(dir, "index.mjs"));
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: `@minecraft/${pkg}`, type: "module", exports: "./index.mjs" }));
}
const url = (...p) => pathToFileURL(path.join(tmp, ...p)).href;
// deterministic runs: seeded PRNG (mulberry32)
let seed = Number(process.env.SEED ?? 20261031) >>> 0;
Math.random = () => {
  seed = (seed + 0x6d2b79f5) >>> 0;
  let t = seed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const mc = await import(url("node_modules", "@minecraft", "server", "index.mjs"));
const { world, system, Player, __tick, __issues } = mc;
const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));
await import(url("scripts", "main.js"));
const registry = await import(url("scripts", "bosses", "registry.js"));
const being = await import(url("scripts", "bosses", "being.js"));
const data = await import(url("scripts", "generated", "data.js"));

const failures = [];
let passed = 0;
const expect = (c, m) => (c ? passed++ : failures.push(m));
async function tick(n = 1, each) {
  for (let i = 0; i < n; i++) {
    await __tick(1);
    if (each) each(i);
    await new Promise((r) => setImmediate(r));
  }
}
const commands = {};
system.beforeEvents.startup.fire({ customCommandRegistry: { registerEnum() {}, registerCommand(def, cb) { commands[def.name] = cb; } } });
expect(Object.keys(commands).length === 5, "5 custom commands registered");
await tick(2);
const dim = world.getDimension("minecraft:overworld");
const P1 = new Player("Alice", dim, { x: 0, y: 64, z: 0 });
const P2 = new Player("Bob", dim, { x: 6, y: 64, z: 6 });
world.afterEvents.playerSpawn.fire({ player: P1, initialSpawn: true });
await tick(45);
expect(P1.__inv.slots.some((s) => s && s.typeId === "legends:codex"), "codex given on first join");

const ACTS = { taotie: data.TAOTIE_ACTS, nidhogg: data.NIDHOGG_ACTS, hanuman: data.HANUMAN_ACTS, alicorn: data.ALICORN_ACTS, tenko: data.TENKO_ACTS, logos: data.LOGOS_ACTS };
const idToAct = (key, id) => Object.entries(ACTS[key]).find(([, v]) => v.id === id)?.[0];
const aimAt = (p, target) => {
  const dx = target.x - p.location.x;
  const dz = target.z - p.location.z;
  p.__rotation = { x: 0, y: (Math.atan2(-dx, dz) * 180) / Math.PI };
};
const report = [];
const bossHp = (e, f) => {
  const h = e.getComponent("minecraft:health");
  h.setCurrentValue(Math.max(1, h.effectiveMax * f));
};

for (const key of ["taotie", "nidhogg", "hanuman", "alicorn", "tenko", "logos"]) {
  registry.clearAll();
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
  P1.location = { x: 0, y: 64, z: 0 };
  P2.location = { x: 6, y: 64, z: 6 };
  for (const p of [P1, P2]) p.getComponent("minecraft:health").setCurrentValue(20);
  const w0 = warnings.length;
  const i0 = __issues.length;
  commands["legends:summon"]({ sourceEntity: P1 }, key);
  await tick(3);
  const boss = dim.getEntities({ type: `legends:${key}` })[0];
  expect(!!boss, `${key}: summoned`);
  if (!boss) continue;
  let b = registry.bossOf(boss.id);
  expect(!!b, `${key}: controlled`);
  // ---- skill drill: every skill of every phase is forced to run once to completion
  for (let k = 0; k < 400 && b.phase < 1; k++) await tick(1);
  const drilled = [];
  for (const sk of b.skills()) {
    const ph = sk.phases[sk.phases.length - 1];
    b.setPhase(ph);
    if (key === "taotie") { b.flying = ph >= 3; b.prop("fly", ph >= 3 ? 1 : 0); }
    if (key === "nidhogg") {
      b.takeWing(ph === 2);
      if (sk.when && !sk.when()) b.takeWing(!b.flying);
    }
    if (key === "alicorn") {
      b.wings(ph >= 2);
      if (sk.name === "heal") bossHp(boss, 0.45);
      if (sk.name === "prism") b.prisms = [];
    }
    if (key === "logos" && sk.name === "reforge") {
      const s = b.alive("seraph");
      if (s) { s.entity.remove(); s.dispose(); }
    }
    if (sk.name === "tail") {
      // stand behind the wyrm
      const back = { x: boss.location.x - Math.sin((-b.yaw * Math.PI) / 180) * -6, y: 64, z: boss.location.z - Math.cos((b.yaw * Math.PI) / 180) * 6 };
      P1.location = back;
      P2.location = back;
      b.refreshArena();
      b.target = P1;
    }
    if (sk.when && !sk.when()) {
      report.push(`${key.padEnd(8)} drill skipped ${sk.name} (condition)`);
      continue;
    }
    if (sk.name !== "tail") {
      P1.location = { x: boss.location.x + 6, y: 64, z: boss.location.z + 2 };
      P2.location = { x: boss.location.x - 7, y: 64, z: boss.location.z - 3 };
      b.refreshArena();
      b.pickTarget();
    }
    b.interrupt();
    b.start(sk.name, sk.run(b.target ?? P1));
    let n = 0;
    while (b.co && n < 700) {
      await tick(1);
      n++;
      for (const p of [P1, P2]) p.getComponent("minecraft:health").setCurrentValue(20);
    }
    expect(!b.co, `${key}: skill ${sk.name} completes (${n} ticks)`);
    drilled.push(sk.name);
    await tick(10);
  }
  report.push(`${key.padEnd(8)} drilled ${drilled.length} skills: ${drilled.join(",")}`);
  registry.clearAll();
  for (const e of dim.getEntities()) if (!(e instanceof Player)) e.remove();
  await tick(3);
  commands["legends:summon"]({ sourceEntity: P1 }, key);
  await tick(3);
  const fresh = dim.getEntities({ type: `legends:${key}` })[0];
  expect(!!fresh, `${key}: summoned again for the fight`);
  if (!fresh) continue;
  const bossRef = fresh;
  b = registry.bossOf(bossRef.id);
  const acts = new Set();
  const cos = new Set();
  const phases = new Set();
  const props = new Set();
  let ultimates = 0;
  let lastCo = "";
  let choirMax = 0;
  let choirDeathAct = false;
  let veiledSeen = false;
  let markedSeen = false;
  let dingsEaten = 0;
  let maxDings = 0;
  let maxText = 0;
  let texts = new Set();
  let revived = false;
  let t = 0;
  const hurt0 = { p1: P1.__hurtLog.length, p2: P2.__hurtLog.length };
  while (bossRef.isValid && t < 16000) {
    await tick(1, () => {
      t++;
      const bl = bossRef.isValid ? bossRef.location : { x: 0, y: 64, z: 0 };
      const ang = t * 0.02;
      const r1 = t % 900 < 450 ? 5 : 14;
      P1.location = { x: bl.x + Math.cos(ang) * r1, y: 64, z: bl.z + Math.sin(ang) * r1 };
      P1.__vel = { x: -Math.sin(ang) * 0.25, y: 0, z: Math.cos(ang) * 0.25 };
      P2.location = { x: bl.x + 8 + Math.sin(t * 0.013) * 7, y: 64, z: bl.z - 6 + Math.cos(t * 0.017) * 6 };
      P1.__air = t % 37 < 7 ? 4 : 0;               // P1 hops regularly
      P1.isSneaking = t % 50 < 18;                  // and crouches now and then
      aimAt(P1, bl);                                // P1 always faces the boss
      aimAt(P2, { x: 2 * P2.location.x - bl.x, y: 64, z: 2 * P2.location.z - bl.z });   // P2 always looks away
      if (b.coName) cos.add(b.coName);
      if (b.coName === "ultimate" && lastCo !== "ultimate") ultimates++;
      lastCo = b.coName;
      phases.add(b.phase);
      if (bossRef.isValid) {
        const a = bossRef.getProperty("legends:act");
        if (a) acts.add(idToAct(key, a));
      }
      for (const e of dim.getEntities({ families: ["legends_prop"] })) props.add(e.typeId);
      if (key === "taotie") {
        const n = b.dings.filter((d) => d.isValid).length;
        if (n < maxDings && b.coName === "ultimate") dingsEaten += maxDings - n;
        maxDings = b.coName === "ultimate" ? n : Math.max(maxDings, n);
      }
      if (key === "logos") {
        const choir = dim.getEntities({ families: ["legends_choir"] });
        choirMax = Math.max(choirMax, choir.length);
        if (b.veiled > 0) veiledSeen = true;
        if (b.hunted()) markedSeen = true;
        // kill one member of the choir in phase II and watch it play its death
        if (b.phase === 2 && t % 400 === 0) {
          const s = choir.find((c) => c.typeId === "legends:seraph");
          if (s) s.applyDamage(400, { cause: "entityAttack", damagingEntity: P1 });
        }
        for (const c of choir) {
          const cb = being.beings.get(c.id);
          if (cb && cb.dying && c.getProperty("legends:act") === data.SERAPH_ACTS.death.id) choirDeathAct = true;
        }
      }
      // break Hanuman's wind wisps / Alicorn's prisms
      for (const typ of ["legends:wind_wisp", "legends:prism"])
        for (const e of dim.getEntities({ type: typ })) if (t % 6 === 0) e.applyDamage(8, { cause: "entityAttack", damagingEntity: P1 });
      if (key === "hanuman" && b.revived) revived = true;
      for (const p of [P1, P2]) {
        const txt = p.onScreenDisplay.actionbar;
        if (txt) {
          texts.add(txt);
          maxText = Math.max(maxText, txt.replace(/§./g, "").length);
        }
      }
      if (t % 10 === 0 && !b.dying && bossRef.isValid) {
        bossRef.applyDamage(5, { cause: t % 40 === 0 ? "projectile" : "entityAttack", damagingEntity: P1 });
        bossRef.isValid && bossRef.applyDamage(4, { cause: "entityAttack", damagingEntity: P2 });
      }
      for (const p of [P1, P2]) {
        const h = p.getComponent("minecraft:health");
        if (h.currentValue < 6) h.setCurrentValue(20);
      }
    });
  }
  const newWarn = warnings.slice(w0);
  const newIssues = __issues.slice(i0);
  expect(!bossRef.isValid, `${key}: defeated within the time limit (t=${t})`);
  expect(phases.has(3), `${key}: reached phase III`);
  expect(ultimates >= 1, `${key}: used its ultimate`);
  expect(acts.has("death"), `${key}: played its death animation`);
  expect(newWarn.length === 0, `${key}: no script warnings (${newWarn.slice(0, 3).join(" | ")})`);
  expect(newIssues.length === 0, `${key}: no API misuse (${newIssues.slice(0, 3).join(" | ")})`);
  expect(maxText <= 34, `${key}: action-bar text stays short (${maxText})`);
  const remaining = dim.getEntities({ families: ["legends_prop"] }).length;
  await tick(80);
  const lingering = dim.getEntities({ families: ["legends"] }).filter((e) => !(e instanceof Player)).length;
  expect(lingering === 0, `${key}: nothing lingers after the fight (${lingering})`);
  const all = Object.keys(ACTS[key]);
  const missing = all.filter((n) => !acts.has(n));
  const p1hits = P1.__hurtLog.length - hurt0.p1;
  const p2hits = P2.__hurtLog.length - hurt0.p2;
  const extra = { taotie: `dings eaten in ult ${dingsEaten}`, logos: `choir max ${choirMax}, choir death anim ${choirDeathAct}, veil ${veiledSeen}, mark ${markedSeen}`, hanuman: `revived ${revived}` }[key] ?? "";
  if (key === "taotie") expect(dingsEaten >= 1, "taotie: the maw devoured a ding during its ultimate");
  if (key === "logos") {
    expect(choirMax === 3, "logos: the three Choir members fight beside the Word");
    expect(choirDeathAct, "logos: a slain Choir member plays its death animation");
    expect(veiledSeen, "logos: the Seraph veiled the Word");
    expect(markedSeen, "logos: the Ophan marked a player");
  }
  if (key === "nidhogg") expect(props.has("legends:world_tree"), "nidhogg: the World-Tree fell");
  if (key === "hanuman") expect(props.has("legends:crescent"), "hanuman: crescent moons flew");
  if (key === "alicorn") {
    expect(props.has("legends:aurora_steed"), "alicorn: the aurora stampede ran");
    const flashP1 = P1.__hurtLog.slice(hurt0.p1).filter((h) => h.amount === 30).length;
    const flashP2 = P2.__hurtLog.slice(hurt0.p2).filter((h) => h.amount === 30).length;
    expect(flashP1 >= 1 && flashP2 === 0, `alicorn: the dawn struck the player who looked (${flashP1}) and spared the one who turned away (${flashP2})`);
  }
  if (key === "hanuman") {
    const moonP2 = P2.__hurtLog.slice(hurt0.p2).filter((h) => h.amount === 16 && h.cause === "magic").length;
    expect(moonP2 >= 1, `hanuman: a moon pass hit the player who neither jumped nor ducked (${moonP2})`);
  }
  if (key === "tenko") expect(props.has("legends:lantern"), "tenko: the fox-wedding procession marched");
  report.push(`${key.padEnd(8)} t=${String(t).padStart(5)} phases=${[...phases].join("")} ults=${ultimates} acts ${acts.size}/${all.length} (unseen: ${missing.join(",") || "-"}) hits p1=${p1hits} p2=${p2hits} ${extra}\n         skills: ${[...cos].filter(Boolean).join(",")}\n         props: ${[...props].join(",")}\n         texts: ${[...texts].join(" | ")}`);
  void remaining;
}
console.log(report.join("\n"));
console.log(`\n${passed} checks passed, ${failures.length} failed`);
for (const f of failures) console.log("FAIL", f);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(failures.length ? 1 : 0);
