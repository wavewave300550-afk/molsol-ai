// npm run validate
// 1) Minecraft Creator Tools validation of addon/ (must report 0 errors)
// 2) cross-reference checks Creator Tools does not do: identifiers, geometry <-> animations <-> controllers <->
//    client entity <-> render controller <-> particles <-> scripts <-> lang, UV bounds, manifests, world safety.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ADDON = path.join(ROOT, "addon");
const RP = path.join(ADDON, "resource_packs", "dragon_dominion");
const BP = path.join(ADDON, "behavior_packs", "dragon_dominion");
const CT = "@minecraft/creator-tools@0.21.0";
const ID = "dragon_dominion:gharvok";

let checks = 0;
const errors = [];
const ok = (cond, msg) => {
  checks++;
  if (!cond) errors.push(msg);
};
const files = (dir, ext) => (fs.existsSync(dir) ? fs.readdirSync(dir, { recursive: true }).filter((f) => f.endsWith(ext)).map((f) => path.join(dir, f)) : []);
const json = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const png = (f) => {
  const b = fs.readFileSync(f);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
};
const pow2 = (n) => n > 0 && (n & (n - 1)) === 0;

// ---------------------------------------------------------------- 0) JSON
for (const f of [...files(BP, ".json"), ...files(RP, ".json")]) {
  let good = true;
  try {
    json(f);
  } catch {
    good = false;
  }
  ok(good, `JSON syntax: ${path.relative(ADDON, f)}`);
}

// ---------------------------------------------------------------- 1) Creator Tools
let ctSummary = "skipped";
if (!process.argv.includes("--skip-ct")) {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "ct-validate-"));
  let raw = "";
  try {
    raw = execFileSync("npx", ["-y", CT, "validate", "-i", ADDON, "--json", "--force", "-o", out],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], maxBuffer: 64 * 1024 * 1024 });
  } catch (e) {
    raw = e.stdout ?? "";
  }
  const start = raw.indexOf("{");
  if (start < 0) ok(false, "Creator Tools validate produced no JSON report");
  else {
    const report = JSON.parse(raw.slice(start));
    ctSummary = `${report.errors} error(s), ${report.warnings} warning(s), ${report.recommendations ?? 0} recommendation(s)`;
    console.log(`Creator Tools validate: ${ctSummary}`);
    for (const pr of report.projects ?? []) for (const it of pr.items ?? []) {
      if (it.type === "error" || it.type === "testFail") console.log("  CT", it.type + ":", it.message, it.data ?? "", it.path ?? "");
      if (process.argv.includes("--warnings") && it.type === "warning") console.log("  CT warning:", it.message, it.data ?? "", it.path ?? "");
    }
    ok(report.errors === 0, `Creator Tools reported ${report.errors} error(s)`);
  }
  fs.rmSync(out, { recursive: true, force: true });
}

// ---------------------------------------------------------------- 2) manifests
const bpm = json(path.join(BP, "manifest.json"));
const rpm = json(path.join(RP, "manifest.json"));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const uuids = [bpm.header.uuid, rpm.header.uuid, ...bpm.modules.map((m) => m.uuid), ...rpm.modules.map((m) => m.uuid)];
ok(uuids.every((u) => UUID.test(u)), "manifest UUIDs are valid v4");
ok(new Set(uuids).size === uuids.length, "manifest UUIDs are unique");
ok(bpm.dependencies.some((d) => d.uuid === rpm.header.uuid && String(d.version) === String(rpm.header.version)), "BP depends on the RP (uuid + version)");
const sdep = bpm.dependencies.find((d) => d.module_name === "@minecraft/server");
const typings = json(path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")).version;
ok(sdep && sdep.version === typings && !/beta|rc|preview/.test(typings), `BP uses stable @minecraft/server ${typings}`);
ok(bpm.dependencies.every((d) => !d.module_name || d.module_name === "@minecraft/server"), "no other (beta / experimental) script modules");
const script = bpm.modules.find((m) => m.type === "script");
ok(script && fs.existsSync(path.join(BP, script.entry)), "script entry exists");
ok(String(bpm.header.min_engine_version) === String(rpm.header.min_engine_version), "BP/RP min_engine_version match");
for (const p of [BP, RP]) {
  const icon = path.join(p, "pack_icon.png");
  ok(fs.existsSync(icon) && png(icon).w === png(icon).h, `${path.basename(p)} pack icon (square png)`);
}
for (const other of fs.readdirSync(path.join(ROOT, "..")).filter((d) => d.endsWith("-addon") && d !== path.basename(ROOT))) {
  for (const f of files(path.join(ROOT, "..", other), "manifest.json")) {
    if (f.includes("node_modules")) continue;
    const m = json(f);
    for (const u of [m.header?.uuid, ...(m.modules ?? []).map((x) => x.uuid)]) ok(!uuids.includes(u), `UUID clash with ${other}`);
  }
}

// ---------------------------------------------------------------- 3) scripts
const jsFiles = files(path.join(BP, "scripts"), ".js");
let jsAll = "";
for (const f of jsFiles) {
  const src = fs.readFileSync(f, "utf8");
  jsAll += src + "\n";
  for (const m of src.matchAll(/from\s+"([^"]+)"/g)) {
    if (m[1].startsWith(".")) ok(m[1].endsWith(".js") && fs.existsSync(path.join(path.dirname(f), m[1])), `${path.relative(BP, f)} imports ${m[1]}`);
    else ok(m[1] === "@minecraft/server", `${path.relative(BP, f)} imports only @minecraft/server (${m[1]})`);
  }
}
// world safety: no block edits, no explosions that break terrain, no fire
for (const bad of [/setType\(/, /setPermutation\(/, /fillBlocks\(/, /createExplosion\(/, /\bsetblock\b/i, /runCommand\([^)]*\bfill\b/, /\bsummon\s+minecraft:(tnt|lightning)/]) {
  ok(!bad.test(jsAll), `scripts never modify terrain (${bad})`);
}
const CFG = await import(pathToFileURL(path.join(BP, "scripts", "dragons", "gharvok", "config.js")).href);
const TIM = await import(pathToFileURL(path.join(BP, "scripts", "dragons", "gharvok", "timings.js")).href);
ok(CFG.GHARVOK_ID === ID, "config entity id");
{
  const rig = json(path.join(ROOT, "tools", ".rig.json"));
  const ceScale = Number(json(path.join(RP, "entity", "gharvok.entity.json"))["minecraft:client_entity"].description.scripts.scale);
  const blocks = (u) => (u * ceScale) / 16;
  const g = CFG.CONFIG.geometry;
  ok(Math.abs(g.headForward - blocks(-rig.points.head[2])) < 0.25, `config headForward matches the model (${blocks(-rig.points.head[2]).toFixed(2)})`);
  ok(Math.abs(g.headHeight - blocks(rig.points.head[1])) < 0.25, `config headHeight matches the model (${blocks(rig.points.head[1]).toFixed(2)})`);
  ok(Math.abs(g.mouthForward - blocks(-rig.points.mouth[2])) < 0.25, `config mouthForward matches the model (${blocks(-rig.points.mouth[2]).toFixed(2)})`);
  ok(Math.abs(g.tailBack - blocks(rig.points.tail_tip[2])) < 0.3, `config tailBack matches the model (${blocks(rig.points.tail_tip[2]).toFixed(2)})`);
}

// ---------------------------------------------------------------- 4) behavior entity / items
const bpe = json(path.join(BP, "entities", "gharvok.json"))["minecraft:entity"];
ok(bpe.description.identifier === ID, "BP entity identifier");
ok(bpe.description.is_summonable === true, "summonable (/summon dragon_dominion:gharvok)");
ok(!fs.existsSync(path.join(BP, "spawn_rules")), "no spawn rules: natural spawning disabled");
ok(!!bpe.components["minecraft:boss"], "minecraft:boss (boss bar)");
for (let n = 1; n <= 4; n++) {
  const h = bpe.component_groups[`dragon_dominion:hp_${n}`]?.["minecraft:health"];
  ok(h && h.max === CFG.hpFor(n) && h.value === CFG.hpFor(n), `HP tier ${n} = ${CFG.hpFor(n)}`);
}
for (const [name, ev] of Object.entries(bpe.events)) {
  for (const g of [...(ev.add?.component_groups ?? []), ...(ev.remove?.component_groups ?? [])]) ok(!!bpe.component_groups[g], `event ${name}: group ${g}`);
}
for (const m of jsAll.matchAll(/event\("([a-z_0-9]+)"\)|event\(`([a-z_]+)\$\{/g)) {
  const n = m[1];
  if (n) ok(!!bpe.events[`dragon_dominion:${n}`], `script triggers event dragon_dominion:${n}`);
}
ok([1, 2, 3, 4].every((n) => bpe.events[`dragon_dominion:hp_tier_${n}`]), "hp_tier_1..4 events");
const props = bpe.description.properties;
ok(props["dragon_dominion:anim"].range[1] === Object.keys(TIM.ANIM).length - 1, "anim property range matches the animation codes");
ok(props["dragon_dominion:flight"].range[1] === Object.keys(TIM.FLIGHT).length - 1, "flight property range");
for (const m of jsAll.matchAll(/this\.prop\("([a-z]+)"/g)) ok(!!props[`dragon_dominion:${m[1]}`], `script property dragon_dominion:${m[1]} declared`);
const itemTex = json(path.join(RP, "textures", "item_texture.json")).texture_data;
const langRP = fs.readFileSync(path.join(RP, "texts", "en_US.lang"), "utf8");
ok(langRP.includes(`entity.${ID}.name=`), "entity name in lang");
for (const f of files(path.join(BP, "items"), ".json")) {
  const it = json(f)["minecraft:item"];
  const icon = it.components["minecraft:icon"];
  ok(itemTex[icon] && fs.existsSync(path.join(RP, [itemTex[icon].textures].flat()[0] + ".png")), `${it.description.identifier} icon texture`);
  ok(langRP.includes(`item.${it.description.identifier}.name=`), `${it.description.identifier} name in lang`);
}
ok([CFG.SIGIL_ID, CFG.REWARD_ID].every((i) => fs.existsSync(path.join(BP, "items", i.split(":")[1] + ".json"))), "sigil + reward items exist");

// ---------------------------------------------------------------- 5) client entity, geometry, textures
const ce = json(path.join(RP, "entity", "gharvok.entity.json"))["minecraft:client_entity"].description;
ok(ce.identifier === ID, "client entity identifier matches");
const geoFile = json(path.join(RP, "models", "entity", "gharvok.geo.json"));
const geo = geoFile["minecraft:geometry"][0];
ok(geoFile.format_version === "1.12.0", "geometry format 1.12.0");
ok(ce.geometry.default === geo.description.identifier, "client entity geometry id");
const bones = new Set(geo.bones.map((b) => b.name));
const locators = new Set();
for (const b of geo.bones) {
  if (b.parent) ok(bones.has(b.parent), `bone ${b.name} parent ${b.parent}`);
  for (const [ln, lv] of Object.entries(b.locators ?? {})) {
    locators.add(ln);
    ok(Array.isArray(lv) && lv.length === 3, `locator ${ln} is [x,y,z]`);
    ok(!bones.has(ln), `locator ${ln} does not reuse a bone name`);
  }
}
ok(bones.size === geo.bones.length, "bone names unique");
const TW = geo.description.texture_width;
const TH = geo.description.texture_height;
let uvBad = 0;
let cubes = 0;
for (const b of geo.bones) for (const c of b.cubes ?? []) {
  cubes++;
  for (const [, f] of Object.entries(c.uv)) {
    const [u, v] = f.uv;
    const [w, h] = f.uv_size;
    if (u < 0 || v < 0 || u + w > TW || v + h > TH || w <= 0 || h <= 0) uvBad++;
  }
}
ok(uvBad === 0, `every UV rectangle inside the ${TW}x${TH} texture (${uvBad} bad)`);
for (const [k, t] of Object.entries(ce.textures)) {
  const f = path.join(RP, t + ".png");
  ok(fs.existsSync(f), `texture ${k} exists`);
  if (fs.existsSync(f)) {
    const s = png(f);
    ok(s.w === TW && s.h === TH && pow2(s.w) && pow2(s.h), `texture ${k} is ${TW}x${TH} (power of two)`);
  }
}
// render controller
const rc = json(path.join(RP, "render_controllers", "gharvok.render_controllers.json")).render_controllers;
ok(ce.render_controllers.every((r) => rc[r]), "render controller exists");
for (const r of Object.values(rc)) {
  for (const t of r.arrays.textures["Array.skull"]) ok(!!ce.textures[t.replace("Texture.", "")], `render controller texture ${t}`);
  for (const pv of r.part_visibility) for (const k of Object.keys(pv)) ok(k === "*" || bones.has(k), `part_visibility bone ${k}`);
  ok(Object.keys(ce.materials).includes("default"), "material default");
}

// ---------------------------------------------------------------- 6) animations / controllers
const anims = json(path.join(RP, "animations", "gharvok.animation.json")).animations;
const ctrls = json(path.join(RP, "animation_controllers", "gharvok.animation_controllers.json")).animation_controllers;
for (const [short, full] of Object.entries(ce.animations)) ok(!!anims[full] || !!ctrls[full], `client animation ${short} -> ${full}`);
for (const e of ce.scripts.animate) {
  const n = typeof e === "string" ? e : Object.keys(e)[0];
  ok(!!ce.animations[n], `animate entry ${n}`);
}
for (const [name, a] of Object.entries(anims)) {
  for (const b of Object.keys(a.bones ?? {})) ok(bones.has(b), `${name}: bone ${b} exists`);
  for (const [, p] of Object.entries(a.particle_effects ?? {})) {
    ok(!!ce.particle_effects[p.effect], `${name}: particle ${p.effect} mapped`);
    if (p.locator) ok(locators.has(p.locator), `${name}: locator ${p.locator}`);
  }
  for (const [, s] of Object.entries(a.sound_effects ?? {})) ok(!!ce.sound_effects[s.effect], `${name}: sound ${s.effect} mapped`);
  ok(a.animation_length > 0, `${name}: has a length`);
}
for (const [cname, c] of Object.entries(ctrls)) {
  ok(!!c.states[c.initial_state], `${cname}: initial state`);
  for (const [sname, s] of Object.entries(c.states)) {
    for (const a of s.animations ?? []) {
      const n = typeof a === "string" ? a : Object.keys(a)[0];
      ok(!!ce.animations[n], `${cname}.${sname}: animation ${n}`);
    }
    for (const t of s.transitions ?? []) ok(!!c.states[Object.keys(t)[0]], `${cname}.${sname}: transition target`);
  }
}
const required = ["idle_breathing", "idle_head_scan", "walk", "run", "turn", "jump", "takeoff", "wing_flap", "glide", "landing",
  "roar", "claw_combo", "charge_windup", "charge", "charge_impact", "tail_sweep", "wing_pressure", "cliff_dive", "skullbreaker",
  "hit_reaction", "stagger", "skull_fracture", "exhausted", "death"];
for (const n of required) {
  const a = anims[`animation.dragon_dominion.gharvok.${n}`];
  ok(!!a, `required animation ${n}`);
  if (a) ok(Object.keys(a.bones).length >= 6, `${n} moves several body parts (${Object.keys(a.bones).length} bones)`);
}
// every animation code the scripts can set is reachable in the action controller
const action = ctrls["controller.animation.dragon_dominion.gharvok.action"];
for (const n of Object.keys(TIM.ANIM)) if (n !== "none") ok(!!action.states[n], `action controller state ${n}`);
for (const m of jsAll.matchAll(/anim\("([a-z_]+)"\)/g)) ok(m[1] in TIM.ANIM, `script animation "${m[1]}" has a code`);

// ---------------------------------------------------------------- 7) particles
const particleIds = new Set(files(path.join(RP, "particles"), ".json").map((f) => json(f).particle_effect.description.identifier));
for (const [k, id] of Object.entries(ce.particle_effects)) ok(particleIds.has(id), `client particle ${k} -> ${id}`);
for (const m of jsAll.matchAll(/`\$\{NS\}:([a-z_]+)`/g)) {
  const id = `dragon_dominion:${m[1]}`;
  if (["dragon_dominion:gharvok", "dragon_dominion:cliff_sigil", "dragon_dominion:fractured_crownplate"].includes(id)) continue;
  if (/^dragon_dominion:(home|fight|tier|phase|skull|skull_pts|dying)$/.test(id)) continue;
  ok(particleIds.has(id), `script particle ${id}`);
}
for (const f of files(path.join(RP, "particles"), ".json")) {
  const tex = json(f).particle_effect.description.basic_render_parameters.texture;
  ok(fs.existsSync(path.join(RP, tex + ".png")), `${path.basename(f)} texture`);
}

console.log(`validate: ${checks - errors.length}/${checks} checks passed; ${geo.bones.length} bones, ${cubes} cubes, ` +
  `${Object.keys(anims).length} animations, ${Object.keys(ctrls).length} controllers, ${particleIds.size} particles`);
for (const e of errors) console.log("  FAIL:", e);
fs.writeFileSync(path.join(ROOT, "docs", ".validate.json"), JSON.stringify({ checks, failed: errors, creatorTools: ctSummary }, null, 1));
process.exit(errors.length ? 1 : 0);
