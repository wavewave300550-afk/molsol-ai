// npm run validate
// 1) Minecraft Creator Tools validation of addon/ (must report 0 errors)
// 2) cross-reference checks Creator Tools does not do (geometry <-> animations <-> controllers <-> client
//    entities <-> scripts <-> lang), plus the geometry rules that made a model invisible on iPhone before.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ADDON = path.join(ROOT, "addon");
const RP = path.join(ADDON, "resource_packs", "extra_super_boss");
const BP = path.join(ADDON, "behavior_packs", "extra_super_boss");
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
    for (const pr of report.projects ?? []) for (const it of pr.items ?? []) {
      if (it.type === "error" || it.type === "testFail") console.log("  CT", it.type + ":", it.message, it.data ?? "", it.path ?? "");
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
ok(bpm.header.name === "Extra Super Boss" && rpm.header.name === "Extra Super Boss", "pack name is 'Extra Super Boss'");
for (const p of [BP, RP]) {
  const icon = path.join(p, "pack_icon.png");
  ok(fs.existsSync(icon) && pngSize(icon).w === pngSize(icon).h, `${path.basename(path.dirname(p))} pack icon (square png)`);
}
// other add-ons in this repository must not collide with these UUIDs
for (const other of ["dragon-or-draco-addon", "grizzly-oath-addon", "tribes-addon"]) {
  for (const f of files(path.join(ROOT, "..", other), "manifest.json")) {
    const m = json(f);
    for (const u of [m.header?.uuid, ...(m.modules ?? []).map((x) => x.uuid)]) ok(!uuids.includes(u), `UUID clash with ${other}`);
  }
}

// compiled scripts: relative imports must carry .js (Bedrock does not resolve bare paths)
const jsFiles = files(path.join(BP, "scripts"), ".js");
for (const f of jsFiles) {
  const src = fs.readFileSync(f, "utf8");
  for (const m of src.matchAll(/from\s+"(\.[^"]+)"/g)) {
    ok(m[1].endsWith(".js") && fs.existsSync(path.join(path.dirname(f), m[1])), `${path.basename(f)} imports ${m[1]}`);
  }
}
const js = jsFiles.map((f) => fs.readFileSync(f, "utf8")).join("\n");

// ---------------------------------------------------------------- 3) behavior entities
const bpEntities = new Map(files(path.join(BP, "entities"), ".json").map((f) => {
  const e = json(f)["minecraft:entity"];
  return [e.description.identifier, e];
}));
const boss = bpEntities.get("esb:da_vinci");
ok(!!boss, "esb:da_vinci behavior entity");
ok(boss.description.is_spawnable && boss.description.is_summonable, "spawn egg + /summon enabled");
for (const id of ["esb:brass_gear", "esb:vitruvian_sigil"]) ok(bpEntities.get(id)?.description.is_summonable, `${id} summonable by scripts`);
for (const [id, e] of bpEntities) {
  for (const [name, ev] of Object.entries(e.events ?? {})) {
    for (const g of [...(ev.add?.component_groups ?? []), ...(ev.remove?.component_groups ?? [])]) ok(!!e.component_groups[g], `${id} event ${name}: group ${g} exists`);
  }
}
// every entity event the scripts trigger exists on the boss
for (const m of new Set([...js.matchAll(/["'](esb:(?:lock|unlock|unlock_fast|to_air|to_ground|dying|despawn))["']/g)].map((x) => x[1]))) {
  ok(!!boss.events[m], `script event ${m} exists`);
}
ok(!!boss.components["minecraft:boss"], "boss bar component");
ok(!!boss.components["minecraft:loot"] && fs.existsSync(path.join(BP, boss.components["minecraft:loot"].table)), "loot table exists");
const props = boss.description.properties;
const spec = fs.readFileSync(path.join(ROOT, "scripts-src", "spec.ts"), "utf8");
const actionValues = JSON.parse(spec.match(/ACTION_VALUES = (\[[^\]]*\])/)[1]);
ok(JSON.stringify(props["esb:action"].values) === JSON.stringify(actionValues), "esb:action enum matches the script spec");
ok(props["esb:action"].values.length <= 16, "esb:action has at most 16 values");
// delayed attack (compass slash) lives in both movement groups
for (const g of ["esb:free", "esb:free_fast"]) ok(!!boss.component_groups[g]["minecraft:behavior.delayed_attack"], `${g} has the delayed attack`);

// ---------------------------------------------------------------- 4) geometry, textures, UVs
const geos = new Map();
const geoFile = new Map();
for (const f of files(path.join(RP, "models"), ".json")) {
  const doc = json(f);
  for (const g of doc["minecraft:geometry"]) {
    geos.set(g.description.identifier, g);
    geoFile.set(g.description.identifier, doc.format_version);
  }
}
for (const [id, g] of geos) {
  ok(geoFile.get(id) === "1.12.0", `${id}: geometry format_version 1.12.0`);
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
    for (const [ln, lv] of Object.entries(b.locators ?? {})) {
      ok(Array.isArray(lv) && lv.length === 3 && lv.every((x) => typeof x === "number"), `${id}: locator ${ln} must be a plain [x, y, z] array`);
      ok(!names.has(ln), `${id}: locator ${ln} has the same name as a bone`);
    }
  }
}
for (const f of files(path.join(RP, "textures"), ".png")) {
  const { w, h } = pngSize(f);
  ok(pow2(w) && pow2(h), `${path.relative(ADDON, f)} is ${w}x${h} (not power of two)`);
}
// geometry declares the real texture size (UVs are written in pixels)
const ceFiles = new Map(files(path.join(RP, "entity"), ".json").map((f) => {
  const d = json(f)["minecraft:client_entity"].description;
  return [d.identifier, d];
}));
for (const [id, ce] of ceFiles) {
  ok(bpEntities.has(id), `client entity ${id} has a behavior entity`);
  for (const [k, t] of Object.entries(ce.textures)) ok(texExists(t), `${id}: texture ${k}: ${t}.png missing`);
  for (const [k, g] of Object.entries(ce.geometry)) {
    ok(geos.has(g), `${id}: geometry ${k}: ${g} missing`);
    const tex = path.join(RP, `${(ce.textures[k] ?? ce.textures.default)}.png`);
    if (geos.has(g) && fs.existsSync(tex)) {
      const s = pngSize(tex);
      ok(s.w === geos.get(g).description.texture_width && s.h === geos.get(g).description.texture_height,
        `${id}: ${g} texture size matches the png`);
    }
  }
}
const main = geos.get("geometry.esb.da_vinci");
const allBones = new Set(main.bones.map((b) => b.name));
const locators = new Set(main.bones.flatMap((b) => Object.keys(b.locators ?? {})));
for (const [id, c] of ceFiles) {
  for (const [k, t] of Object.entries(c.textures)) {
    const g = geos.get(c.geometry[k] ?? c.geometry.default);
    const f = path.join(RP, `${t}.png`);
    if (g && fs.existsSync(f)) ok(pngSize(f).w === g.description.texture_width && pngSize(f).h === g.description.texture_height, `${id}: ${k} texture matches the geometry size`);
  }
}
for (const b of ["head", "torso", "arm_l", "gauntlet_l", "ghand_l", "finger_l_1", "finger_l_4", "thumb_l", "arm_r", "hand_r",
  "compass", "leg_l", "shin_r", "foot_l", "cape_tail_l", "cape_tail_r", "hair_tail", "wing_l", "wing_r_tip"]) {
  ok(allBones.has(b), `rig bone ${b} present`);
}

// ---------------------------------------------------------------- 5) animations, controllers, particles
const anims = new Map();
for (const f of files(path.join(RP, "animations"), ".json")) for (const [k, a] of Object.entries(json(f).animations)) anims.set(k, a);
const ctrls = new Map();
for (const f of files(path.join(RP, "animation_controllers"), ".json")) for (const [k, c] of Object.entries(json(f).animation_controllers)) ctrls.set(k, c);
const particles = new Set(files(path.join(RP, "particles"), ".json").map((f) => json(f).particle_effect.description.identifier));
const ce = ceFiles.get("esb:da_vinci");
// animation / controller name -> the entity that owns it ("animation.esb.<short>.x")
const SHORT = { da_vinci: "esb:da_vinci", brass_gear: "esb:brass_gear", vitruvian_sigil: "esb:vitruvian_sigil", edison: "esb:edison",
  dynamo: "esb:dynamo", electric_chair: "esb:electric_chair", volt_bulb: "esb:volt_bulb", sun_bulb: "esb:sun_bulb",
  volt_marker: "esb:volt_marker", arc_bolt: "esb:arc_bolt" };
const ownerOf = (id) => SHORT[id.replace(/^controller\./, "").split(".")[2]];
for (const id of [...anims.keys(), ...ctrls.keys()]) ok(!!ownerOf(id), `${id}: unknown owner`);
const geoOf = (ent) => geos.get(ceFiles.get(ent).geometry.default);
// an entity can render several geometries (the ultimates add a halo / aura layer): animations may use any of them
const geosOf = (ent) => Object.values(ceFiles.get(ent).geometry).map((g) => geos.get(g)).filter(Boolean);
for (const [id, d] of ceFiles) {
  for (const [k, v] of Object.entries(d.animations ?? {})) {
    ok(anims.has(v) || ctrls.has(v), `${id}: animation ${k} -> ${v} missing`);
    ok(ownerOf(v) === id, `${id}: uses ${v} that belongs to another entity`);
  }
  for (const a of d.scripts?.animate ?? []) {
    const k = typeof a === "string" ? a : Object.keys(a)[0];
    ok(k in (d.animations ?? {}), `${id}: animate ${k} not mapped`);
  }
  for (const [k, p] of Object.entries(d.particle_effects ?? {})) ok(particles.has(p), `${id}: particle ${k} -> ${p} missing`);
  // every animation of this entity is mapped (no orphans)
  const mappedHere = new Set(Object.values(d.animations ?? {}));
  for (const aid of anims.keys()) if (ownerOf(aid) === id) ok(mappedHere.has(aid), `animation ${aid} is never mapped (orphan)`);
}
for (const [id, a] of anims) {
  const ent = ownerOf(id);
  if (!ent) continue;
  const owner = ceFiles.get(ent);
  const all = geosOf(ent);
  const bones = new Set(all.flatMap((g) => g.bones.map((b) => b.name)));
  const locs = new Set(all.flatMap((g) => g.bones.flatMap((b) => Object.keys(b.locators ?? {}))));
  for (const bone of Object.keys(a.bones ?? {})) ok(bones.has(bone), `${id}: bone ${bone} not in ${ent}'s geometry`);
  for (const pe of Object.values(a.particle_effects ?? {}).flat()) {
    ok(pe.effect in (owner.particle_effects ?? {}), `${id}: particle key ${pe.effect} not in client entity`);
    ok(locs.has(pe.locator), `${id}: locator ${pe.locator} missing`);
  }
}
// action lengths in the animation files equal the script spec, for both bosses
const specActs = JSON.parse(spec.match(/export const ACTIONS = (\{[\s\S]*?\n\}) as const/)[1]);
const specActsE = JSON.parse(spec.match(/export const EDISON_ACTIONS = (\{[\s\S]*?\n\}) as const/)[1]);
const actionValuesE = JSON.parse(spec.match(/EDISON_ACTION_VALUES = (\[[^\]]*\])/)[1]);
for (const [short, acts] of [["da_vinci", specActs], ["edison", specActsE]]) {
  for (const [k, v] of Object.entries(acts)) {
    ok(anims.get(`animation.esb.${short}.${k}`)?.animation_length === v.length, `${short} animation ${k} is ${v.length}s like the script`);
  }
}
const edisonBP = bpEntities.get("esb:edison");
ok(JSON.stringify(edisonBP.description.properties["esb:action"].values) === JSON.stringify(actionValuesE), "Edison esb:action enum matches the spec");
// Molang property reads: each controller / animation may only read synced properties of its own entity
for (const [id, obj] of [...ctrls.entries(), ...anims.entries()]) {
  const ent = ownerOf(id);
  const eprops = bpEntities.get(ent)?.description.properties ?? {};
  const txt = JSON.stringify(obj);
  for (const m of txt.matchAll(/q\.property\('([^']+)'\)\s*(==|!=)\s*'([^']+)'/g)) {
    const def = eprops[m[1]];
    ok(def && def.client_sync && def.values.includes(m[3]), `${id}: compares ${m[1]} with '${m[3]}' (not a synced enum value of ${ent})`);
  }
  for (const m of txt.matchAll(/q\.property\('([^']+)'\)/g)) ok(eprops[m[1]]?.client_sync, `${id}: reads ${m[1]} which ${ent} does not sync`);
}
for (const [id, d] of ceFiles) {
  const eprops = bpEntities.get(id)?.description.properties ?? {};
  for (const m of JSON.stringify(d.scripts ?? {}).matchAll(/q\.property\('([^']+)'\)/g)) ok(eprops[m[1]]?.client_sync, `${id} client scripts read ${m[1]}`);
}
const rcsAll = new Map();
for (const f of files(path.join(RP, "render_controllers"), ".json")) for (const [k, r] of Object.entries(json(f).render_controllers)) rcsAll.set(k, r);
for (const id of ["esb:edison", "esb:dynamo"]) {
  const rc = rcsAll.get(`controller.render.${id.replace(":", ".")}`);
  ok(rc && JSON.stringify(rc).includes("q.property('esb:phase')") && bpEntities.get(id).description.properties["esb:phase"]?.client_sync,
    `${id}: phase 2 texture switch reads a synced property`);
  ok(texExists(ceFiles.get(id).textures.charged), `${id}: charged texture exists`);
}
// RULE: every boss has an ULTIMATE (action value, animation, controller state, extra render layer, script trigger)
for (const [id, e] of bpEntities) {
  if (!e.components["minecraft:type_family"]?.family.includes("esb_boss")) continue;
  const short = id.split(":")[1];
  ok(e.description.properties["esb:action"].values.includes("ultimate"), `${id}: has an 'ultimate' action`);
  ok(anims.has(`animation.esb.${short}.ultimate`), `${id}: has an ultimate animation`);
  ok(!!ctrls.get(`controller.animation.esb.${short}.action`)?.states.ultimate, `${id}: ultimate controller state`);
  ok((ceFiles.get(id).render_controllers ?? []).some((r) => typeof r === "object" && JSON.stringify(r).includes("'ultimate'")),
    `${id}: an extra render layer shown only during the ultimate`);
  ok(/hp_threshold/.test(js) && new RegExp(`["']ultimate["']`).test(js), `${id}: scripts trigger the ultimate`);
}
// every action value of each boss has a controller state and is set by the scripts
for (const [short, values, ctrl] of [["da_vinci", actionValues, "controller.animation.esb.da_vinci.action"],
  ["edison", actionValuesE, "controller.animation.esb.edison.action"]]) {
  const c = ctrls.get(ctrl);
  for (const v of values) {
    if (v === "none") continue;
    ok(!!c.states[v], `${short} action '${v}' has a controller state`);
    ok(JSON.stringify(c).includes(`q.property('esb:action') == '${v}'`), `${short} action '${v}' has a transition`);
    ok(new RegExp(`["']${v}["']`).test(js), `${short} action '${v}' is set by the scripts`);
  }
}
// controller graphs: reachable, cross-faded, no dead ends
for (const [id, c] of ctrls) {
  const owner = ceFiles.get(ownerOf(id));
  const seen = new Set([c.initial_state ?? "default"]);
  const todo = [...seen];
  while (todo.length) {
    const sn = todo.pop();
    for (const tr of c.states[sn]?.transitions ?? []) for (const dst of Object.keys(tr)) {
      ok(dst in c.states, `${id}.${sn}: transition to unknown state ${dst}`);
      if (!seen.has(dst)) {
        seen.add(dst);
        todo.push(dst);
      }
    }
  }
  for (const [sn, st] of Object.entries(c.states)) {
    ok(seen.has(sn), `${id}: state ${sn} is unreachable`);
    for (const a of st.animations ?? []) ok((typeof a === "string" ? a : Object.keys(a)[0]) in owner.animations, `${id}.${sn}: animation not mapped`);
    ok((st.transitions ?? []).length > 0, `${id}.${sn}: dead-end state`);
  }
}
// particles: every emitter ends on its own; ids used by scripts exist
for (const f of files(path.join(RP, "particles"), ".json")) {
  const c = json(f).particle_effect.components;
  ok(!!(c["minecraft:emitter_lifetime_once"] || c["minecraft:emitter_lifetime_expression"]), `${path.basename(f)}: emitter must end`);
}
const allProps = new Set([...bpEntities.values()].flatMap((e) => Object.keys(e.description.properties ?? {})));
const itemIds = new Set(files(path.join(BP, "items"), ".json").map((f) => json(f)["minecraft:item"].description.identifier));
for (const m of new Set([...js.matchAll(/"(esb:[a-z_]+)"/g)].map((x) => x[1]))) {
  if (bpEntities.has(m) || allProps.has(m) || itemIds.has(m) || m.startsWith("esb:intro") || boss.events[m]) continue;
  ok(particles.has(m), `script id ${m} is not a particle / entity / item / property / event`);
}
for (const b of ["head", "torso", "arm_r", "hand_r", "shiv", "arm_l", "hand_l", "bulb_l", "apron_l", "apron_r", "leg_l", "shin_r", "foot_l"]) {
  ok(new Set(geoOf("esb:edison").bones.map((x) => x.name)).has(b), `Edison rig bone ${b}`);
}
for (const b of ["lever_1", "lever_3", "bulb_1", "bulb_5"]) ok(new Set(geoOf("esb:dynamo").bones.map((x) => x.name)).has(b), `Dynamo bone ${b}`);
const rcs = rcsAll;
for (const [id, d] of ceFiles) for (const r of d.render_controllers) ok(rcs.has(typeof r === "string" ? r : Object.keys(r)[0]), `${id}: render controller missing`);

// ---------------------------------------------------------------- 6) items, loot, names
const atlas = json(path.join(RP, "textures", "item_texture.json")).texture_data;
const items = files(path.join(BP, "items"), ".json").map((f) => json(f)["minecraft:item"]);
for (const it of items) {
  const icon = it.components["minecraft:icon"];
  ok(atlas[icon] && texExists(atlas[icon].textures), `${it.description.identifier}: icon ${icon} registered`);
}
const lang = fs.readFileSync(path.join(RP, "texts", "en_US.lang"), "utf8");
const langKeys = new Set(lang.split("\n").filter((l) => l.includes("=")).map((l) => l.split("=")[0]));
for (const id of bpEntities.keys()) ok(langKeys.has(`entity.${id}.name`), `lang: entity.${id}.name`);
for (const it of items) ok(langKeys.has(it.components["minecraft:display_name"].value), `lang: ${it.description.identifier}`);
for (const m of new Set([...js.matchAll(/"(esb\.(?:msg|title|subtitle)\.[a-z_0-9]+)"/g)].map((x) => x[1]))) ok(langKeys.has(m), `lang key ${m} used by scripts`);
const loot = json(path.join(BP, "loot_tables", "entities", "da_vinci.json"));
ok(loot.pools.some((p) => p.entries.some((e) => e.name === "esb:leonardo_codex")), "codex drops from Da Vinci");
const lootE = json(path.join(BP, "loot_tables", "entities", "edison.json"));
ok(lootE.pools.some((p) => p.entries.some((e) => e.name === "esb:volt_shiv")), "Volt Shiv drops from Edison");
for (const id of ["esb:da_vinci", "esb:edison"]) {
  const c = ceFiles.get(id);
  ok(c.spawn_egg && c.spawn_egg.base_color && c.spawn_egg.overlay_color, `${id}: spawn egg colours`);
  ok(langKeys.has(`item.spawn_egg.entity.${id}.name`), `lang: ${id} spawn egg name`);
  ok(!!bpEntities.get(id).components["minecraft:boss"], `${id}: boss bar`);
}

console.log(`cross-reference checks: ${checks - errors.length}/${checks} passed`);
for (const e of errors) console.log("  ERROR:", e);
process.exit(errors.length ? 1 : 0);
