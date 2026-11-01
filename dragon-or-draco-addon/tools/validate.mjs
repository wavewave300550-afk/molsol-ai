// npm run validate
// 1) Minecraft Creator Tools validation of addon/ (must report 0 errors)
// 2) cross-reference checks Creator Tools does not do (see list below)
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ADDON = path.join(ROOT, "addon");
const RP = path.join(ADDON, "resource_packs", "dragon_or_draco");
const BP = path.join(ADDON, "behavior_packs", "dragon_or_draco");
const CT = "@minecraft/creator-tools@0.20.0";

let checks = 0;
const errors = [];
const ok = (cond, msg) => {
  checks++;
  if (!cond) errors.push(msg);
};
const files = (dir, ext) =>
  fs.existsSync(dir) ? fs.readdirSync(dir, { recursive: true }).filter((f) => f.endsWith(ext)).map((f) => path.join(dir, f)) : [];
const json = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const pngSize = (f) => {
  const b = fs.readFileSync(f);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
};
const pow2 = (n) => n > 0 && (n & (n - 1)) === 0;
const texExists = (t) => fs.existsSync(path.join(RP, `${t}.png`));

// ---------------------------------------------------------------- 0) every JSON parses
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
  if (start < 0) {
    ok(false, "Creator Tools validate produced no JSON report");
  } else {
    const report = JSON.parse(raw.slice(start));
    console.log(`Creator Tools validate: ${report.errors} error(s), ${report.warnings} warning(s), ${report.recommendations ?? 0} recommendation(s)`);
    for (const it of report.items ?? []) {
      if (it.type === "error" || it.level === "error") console.log("  CT error:", JSON.stringify(it).slice(0, 300));
    }
    ok(report.errors === 0, `Creator Tools reported ${report.errors} error(s)`);
  }
  fs.rmSync(out, { recursive: true, force: true });
}

// ---------------------------------------------------------------- 2) manifests
const bpm = json(path.join(BP, "manifest.json"));
const rpm = json(path.join(RP, "manifest.json"));
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const uuids = [bpm.header.uuid, rpm.header.uuid, ...bpm.modules.map((m) => m.uuid), ...rpm.modules.map((m) => m.uuid)];
ok(uuids.every((u) => UUID.test(u)), "manifest UUIDs are valid v4 strings");
ok(new Set(uuids).size === uuids.length, "manifest UUIDs are unique");
ok(bpm.dependencies.some((d) => d.uuid === rpm.header.uuid && String(d.version) === String(rpm.header.version)), "BP depends on the RP (uuid + version)");
const sdep = bpm.dependencies.find((d) => d.module_name === "@minecraft/server");
ok(sdep && String(sdep.version) === "2,11,0", "BP depends on @minecraft/server 2.11.0");
const pkgVer = json(path.join(ROOT, "node_modules", "@minecraft", "server", "package.json")).version;
ok(pkgVer === "2.11.0", `typings are @minecraft/server ${pkgVer}`);
const script = bpm.modules.find((m) => m.type === "script");
ok(script && fs.existsSync(path.join(BP, script.entry)), "script entry exists");
ok(String(bpm.header.min_engine_version) === "1,26,60" && String(rpm.header.min_engine_version) === "1,26,60", "min_engine_version 1.26.60");
ok(bpm.header.name === "Dragon or Draco" && rpm.header.name === "Dragon or Draco", "pack name is exactly 'Dragon or Draco'");
ok(fs.existsSync(path.join(BP, "pack_icon.png")) && fs.existsSync(path.join(RP, "pack_icon.png")), "pack icons present");

// compiled scripts: relative imports must carry .js (Bedrock does not resolve bare paths)
for (const f of files(path.join(BP, "scripts"), ".js")) {
  const src = fs.readFileSync(f, "utf8");
  for (const m of src.matchAll(/from\s+"(\.[^"]+)"/g)) {
    ok(m[1].endsWith(".js") && fs.existsSync(path.join(path.dirname(f), m[1])), `${path.basename(f)} imports ${m[1]}`);
  }
}

// ---------------------------------------------------------------- 3) entity definitions
const bpe = json(path.join(BP, "entities", "red_dragon.json"))["minecraft:entity"];
const ce = json(path.join(RP, "entity", "red_dragon.entity.json"))["minecraft:client_entity"].description;
ok(bpe.description.identifier === "dod:red_dragon" && ce.identifier === "dod:red_dragon", "identifier dod:red_dragon in BP and RP");
ok(bpe.description.is_spawnable && bpe.description.is_summonable, "spawn egg + /summon enabled");
const props = bpe.description.properties;
// events used by the scripts exist and reference existing groups
const js = files(path.join(BP, "scripts"), ".js").map((f) => fs.readFileSync(f, "utf8")).join("\n");
for (const m of new Set([...js.matchAll(/["'](dod:[a-z_]+)["']/g)].map((x) => x[1]))) {
  if (props[m] || m === "dod:red_dragon" || m === "dod:home" || m.startsWith("dod:fire") || m.startsWith("dod:smoke") ||
    m.startsWith("dod:embers") || m.startsWith("dod:claw") || m.startsWith("dod:dust")) continue;
  ok(!!bpe.events[m], `script event ${m} exists in the entity`);
}
for (const [name, ev] of Object.entries(bpe.events)) {
  const specs = ev.randomize ?? [ev];
  for (const sp of specs) for (const g of [...(sp.add?.component_groups ?? []), ...(sp.remove?.component_groups ?? [])]) {
    ok(!!bpe.component_groups[g], `event ${name}: group ${g} exists`);
  }
}
// never two groups that define the same component active together via a single event
const sr = json(path.join(BP, "spawn_rules", "red_dragon.json"))["minecraft:spawn_rules"];
ok(sr.description.identifier === "dod:red_dragon", "spawn rule identifier");
for (const c of sr.conditions) ok(!!bpe.events[c["minecraft:spawn_event"]?.event], "spawn rule event exists");

// ---------------------------------------------------------------- 4) geometry, textures, UVs
const geos = new Map();
for (const f of files(path.join(RP, "models"), ".json")) for (const g of json(f)["minecraft:geometry"]) geos.set(g.description.identifier, g);
for (const [id, g] of geos) {
  const W = g.description.texture_width;
  const H = g.description.texture_height;
  const names = new Set(g.bones.map((b) => b.name));
  ok(names.size === g.bones.length, `${id}: unique bone names`);
  for (const b of g.bones) {
    if (b.parent) ok(names.has(b.parent), `${id}: ${b.name} parent ${b.parent} missing`);
    for (const c of b.cubes ?? []) {
      for (const [face, uv] of Object.entries(c.uv)) {
        const [u, v] = uv.uv;
        const [su, sv] = uv.uv_size;
        ok(u >= 0 && v >= 0 && u + su <= W && v + sv <= H, `${id}: ${b.name}.${face} UV outside ${W}x${H}`);
      }
    }
  }
}
for (const f of files(path.join(RP, "textures"), ".png")) {
  const { w, h } = pngSize(f);
  ok(pow2(w) && pow2(h), `${path.relative(ADDON, f)} is ${w}x${h} (not power of two)`);
}
for (const [k, t] of Object.entries(ce.textures)) ok(texExists(t), `client texture ${k}: ${t}.png missing`);
for (const [k, g] of Object.entries(ce.geometry)) ok(geos.has(g), `client geometry ${k}: ${g} missing`);
const main = geos.get(ce.geometry.default);
const fire = geos.get(ce.geometry.fire);
// the fire geometry must share pivots / rest rotations of its chain with the main skeleton
for (const b of fire.bones) {
  const m = main.bones.find((x) => x.name === b.name);
  if (!m) continue;
  ok(JSON.stringify(m.pivot) === JSON.stringify(b.pivot) && JSON.stringify(m.rotation ?? [0, 0, 0]) === JSON.stringify(b.rotation ?? [0, 0, 0]),
    `fire geometry bone ${b.name} matches the main skeleton`);
}
const allBones = new Set([...main.bones, ...fire.bones].map((b) => b.name));
// geometry hygiene that the game is stricter about than schema tools (an invisible model on
// iPhone was traced to these): plain-array locators whose names never repeat a bone name
for (const [id, g] of geos) {
  const docVer = json(files(path.join(RP, "models"), ".json").find((f) => json(f)["minecraft:geometry"].some((x) => x.description.identifier === id))).format_version;
  ok(docVer === "1.12.0", `${id}: geometry format_version 1.12.0 (is ${docVer})`);
  const boneNames = new Set(g.bones.map((b) => b.name));
  for (const b of g.bones) {
    for (const [ln, lv] of Object.entries(b.locators ?? {})) {
      ok(Array.isArray(lv) && lv.length === 3 && lv.every((v) => typeof v === "number"), `${id}: locator ${ln} must be a plain [x, y, z] array`);
      ok(!boneNames.has(ln), `${id}: locator ${ln} has the same name as a bone`);
    }
  }
}
const locators = new Set(main.bones.flatMap((b) => Object.keys(b.locators ?? {})));
// rig requirements from the brief
const need = ["head", "jaw", "neck_1", "neck_2", "neck_3", "neck_4", "chest", "body", "pelvis", "leg_fl_upper", "leg_fl_lower",
  "foot_fl", "leg_fr_upper", "leg_hl_thigh", "leg_hl_shin", "leg_hl_meta", "foot_hr", "wing_l_upper", "wing_l_fore",
  "wing_l_hand", "wing_l_f1", "wing_l_f4", "wing_r_f2", "wing_l_mem_f1", "wing_r_mem_b", "tail_1", "tail_8"];
for (const b of need) ok(allBones.has(b), `rig bone ${b} present`);

// ---------------------------------------------------------------- 5) animations, controllers, particles, sounds
const anims = new Map();
for (const f of files(path.join(RP, "animations"), ".json")) for (const [k, a] of Object.entries(json(f).animations)) anims.set(k, a);
const ctrls = new Map();
for (const f of files(path.join(RP, "animation_controllers"), ".json")) for (const [k, c] of Object.entries(json(f).animation_controllers)) ctrls.set(k, c);
const particles = new Set(files(path.join(RP, "particles"), ".json").map((f) => json(f).particle_effect.description.identifier));
const soundDefs = json(path.join(RP, "sounds", "sound_definitions.json")).sound_definitions;
for (const [k, v] of Object.entries(ce.animations)) ok(anims.has(v) || ctrls.has(v), `client animation ${k} -> ${v} missing`);
for (const k of ce.scripts.animate.map((x) => (typeof x === "string" ? x : Object.keys(x)[0]))) ok(k in ce.animations, `animate ${k} not mapped`);
for (const [id, a] of anims) {
  for (const bone of Object.keys(a.bones ?? {})) ok(allBones.has(bone), `${id}: bone ${bone} not in the geometry`);
  for (const pe of Object.values(a.particle_effects ?? {}).flat()) {
    ok(pe.effect in ce.particle_effects, `${id}: particle key ${pe.effect} not in client entity`);
    ok(locators.has(pe.locator), `${id}: locator ${pe.locator} missing`);
  }
  for (const se of Object.values(a.sound_effects ?? {}).flat()) ok(se.effect in ce.sound_effects, `${id}: sound key ${se.effect} not in client entity`);
}
for (const [k, p] of Object.entries(ce.particle_effects)) ok(particles.has(p), `client particle ${k} -> ${p} missing`);
for (const [k, s] of Object.entries(ce.sound_effects)) ok(!!soundDefs[s], `client sound ${k} -> ${s} missing`);
// every property/enum value compared in Molang exists
const molang = JSON.stringify([...ctrls.values(), ...anims.values(), ce.render_controllers, ce.scripts]);
for (const m of molang.matchAll(/q\.property\('([^']+)'\)\s*(==|!=)\s*'([^']+)'/g)) {
  const def = props[m[1]];
  ok(def && def.client_sync && def.values.includes(m[3]), `Molang compares ${m[1]} with '${m[3]}' (not a synced enum value)`);
}
for (const m of molang.matchAll(/q\.property\('([^']+)'\)/g)) ok(props[m[1]]?.client_sync, `Molang reads ${m[1]} which is not client_sync`);
for (const [id, c] of ctrls) {
  for (const [sn, st] of Object.entries(c.states)) {
    for (const a of st.animations ?? []) {
      const key = typeof a === "string" ? a : Object.keys(a)[0];
      ok(key in ce.animations, `${id}.${sn}: animation ${key} not in client entity`);
    }
    for (const tr of st.transitions ?? []) for (const dst of Object.keys(tr)) ok(dst in c.states, `${id}.${sn}: transition to ${dst}`);
  }
}
// ---------------------------------------------------------------- 5b) V2 animation system
// every animation in the file is used (no orphan or filler clips): mapped in the client entity and
// played by a controller state
const mapped = new Map(Object.entries(ce.animations).map(([k, v]) => [v, k]));
const played = new Set();
for (const c of ctrls.values()) for (const st of Object.values(c.states)) {
  for (const a of st.animations ?? []) played.add(typeof a === "string" ? a : Object.keys(a)[0]);
}
for (const id of anims.keys()) {
  ok(mapped.has(id), `animation ${id} is not mapped in the client entity (orphan)`);
  ok(played.has(mapped.get(id)), `animation ${id} is never played by a controller state`);
}
// every animation state value the scripts can set has a controller transition that reacts to it
for (const key of ["dod:flight", "dod:action", "dod:idle"]) {
  const def = props[key];
  ok(def && def.type === "enum" && def.client_sync, `${key} is a client-synced enum`);
  for (const v of def.values) {
    if (v === def.default) continue;
    // 'rise' is reached by leaving the rest state (dod:idle != 'rest'), so a client that joins mid-rise
    // keeps standing instead of popping down to the ground first
    const handled = molang.includes(`q.property('${key}') == '${v}'`) ||
      (key === "dod:idle" && v === "rise" && molang.includes("q.property('dod:idle') != 'rest'"));
    ok(handled, `${key} = '${v}' has no controller transition`);
    ok(new RegExp(`["']${v}["']`).test(js), `${key} = '${v}' is never set by the scripts`);
  }
}
// controller graphs: every state reachable, smooth (blend_transition), and nothing can get stuck:
// a state whose animations end must have a way out
for (const [id, c] of ctrls) {
  const seen = new Set([c.initial_state ?? "default"]);
  const todo = [...seen];
  while (todo.length) {
    const sn = todo.pop();
    for (const tr of c.states[sn]?.transitions ?? []) for (const dst of Object.keys(tr)) if (!seen.has(dst)) {
      seen.add(dst);
      todo.push(dst);
    }
  }
  for (const sn of Object.keys(c.states)) ok(seen.has(sn), `${id}: state ${sn} is unreachable`);
  for (const [sn, st] of Object.entries(c.states)) {
    // leaving a state that plays something must cross-fade (empty states hand over to clips that start from rest)
    if ((st.animations ?? []).length) ok(typeof st.blend_transition === "number" && st.blend_transition > 0, `${id}.${sn}: no blend_transition (would snap)`);
    if (sn !== "dead") ok((st.transitions ?? []).length > 0, `${id}.${sn}: dead-end state (could stay stuck)`);
  }
}
// looping clips close their loop (first key == last key, keys at 0 and at animation_length)
for (const [id, a] of anims) {
  if (a.loop !== true) continue;
  for (const [bone, chans] of Object.entries(a.bones ?? {})) for (const [kind, ch] of Object.entries(chans)) {
    if (typeof ch !== "object" || Array.isArray(ch)) continue;
    const ks = Object.keys(ch).sort((x, y) => Number(x) - Number(y));
    const val = (k) => (Array.isArray(ch[k]) ? ch[k] : ch[k].post ?? ch[k].pre);
    const f = val(ks[0]);
    const l = val(ks[ks.length - 1]);
    const closed = Number(ks[0]) < 1e-3 && Math.abs(Number(ks[ks.length - 1]) - a.animation_length) < 1e-3 &&
      f.every((x, i) => typeof x !== "number" || Math.abs(x - l[i]) <= 0.02);
    ok(closed, `${id}: ${bone}.${kind} loop seam is open`);
  }
}
// rig V2 bones (added without changing existing cubes: tools/rig_v2.py asserts that at build time)
for (const b of ["toes_fl", "toes_fr", "toes_hl", "toes_hr", "eyelid_l", "eyelid_r"]) ok(allBones.has(b), `rig V2 bone ${b} present`);
// project identity is preserved across versions
ok(bpm.header.uuid === "e8c0e8b7-eae9-4c52-9bac-763f33ef1fe0" && rpm.header.uuid === "8b9eb730-6d68-4b25-91c3-98c7f103bf03",
  "original pack UUIDs kept");

const rcs = new Map();
for (const f of files(path.join(RP, "render_controllers"), ".json")) for (const [k, r] of Object.entries(json(f).render_controllers)) rcs.set(k, r);
for (const r of ce.render_controllers) ok(rcs.has(typeof r === "string" ? r : Object.keys(r)[0]), `render controller ${JSON.stringify(r)} missing`);
for (const [k, s] of Object.entries(soundDefs)) for (const snd of s.sounds) ok(typeof snd === "object" && snd.name.startsWith("sounds/"), `${k}: sound path ${JSON.stringify(snd)}`);
// script particles / sounds exist
for (const m of new Set([...js.matchAll(/"(dod:(?:fire_[a-z_]+|smoke|embers|claw_slash|dust_ring))"/g)].map((x) => x[1]))) ok(particles.has(m), `script particle ${m} missing`);
for (const m of new Set([...js.matchAll(/"(mob\.dod\.red_dragon\.[a-z_]+)"/g)].map((x) => x[1]))) ok(!!soundDefs[m], `script sound ${m} missing`);
// particles: every emitter is finite
for (const f of files(path.join(RP, "particles"), ".json")) {
  const c = json(f).particle_effect.components;
  ok(!!(c["minecraft:emitter_lifetime_once"] || c["minecraft:emitter_lifetime_expression"]), `${path.basename(f)}: emitter must end on its own`);
}

// ---------------------------------------------------------------- 6) spawn egg + names
const atlas = json(path.join(RP, "textures", "item_texture.json")).texture_data;
ok(atlas[ce.spawn_egg.texture] && texExists(atlas[ce.spawn_egg.texture].textures), "spawn egg texture registered");
for (const langFile of ["en_US.lang"]) {
  const lang = fs.readFileSync(path.join(RP, "texts", langFile), "utf8");
  ok(lang.includes("entity.dod:red_dragon.name="), `${langFile}: entity name`);
  ok(lang.includes("item.spawn_egg.entity.dod:red_dragon.name="), `${langFile}: spawn egg name`);
}

console.log(`cross-reference checks: ${checks - errors.length}/${checks} passed`);
for (const e of errors) console.log("  ERROR:", e);
process.exit(errors.length ? 1 : 0);
