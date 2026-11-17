// npm run validate
// 1) Minecraft Creator Tools validation of addon/ (must report 0 errors)
// 2) cross-reference checks Creator Tools does not do: animation bones / locators vs geometry,
//    UVs inside their texture, power-of-two textures, attachable + client entity wiring,
//    item icons and names.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ADDON = path.join(ROOT, "addon");
const RP = path.join(ADDON, "resource_packs", "grizzly_oath");
const BP = path.join(ADDON, "behavior_packs", "grizzly_oath");
const CT = "@minecraft/creator-tools@0.20.0";

let checks = 0;
const errors = [];
const ok = (cond, msg) => {
  checks++;
  if (!cond) errors.push(msg);
};
const json = (f) => JSON.parse(fs.readFileSync(f, "utf8"));
const files = (dir, ext) =>
  fs.existsSync(dir) ? fs.readdirSync(dir, { recursive: true }).filter((f) => f.endsWith(ext)).map((f) => path.join(dir, f)) : [];

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
const pow2 = (n) => n > 0 && (n & (n - 1)) === 0;

// ---------------------------------------------------------------- 1) Creator Tools
if (!process.argv.includes("--skip-ct")) {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "ct-validate-"));
  let raw = "";
  try {
    raw = execFileSync("npx", ["-y", CT, "validate", "-i", ADDON, "--json", "--force", "-o", out], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch (e) {
    raw = e.stdout ?? "";
  }
  const report = JSON.parse(raw.slice(raw.indexOf("{")));
  console.log(`Creator Tools validate: ${report.errors} error(s), ${report.warnings} warning(s), ${report.recommendations} recommendation(s)`);
  ok(report.errors === 0, `Creator Tools reported ${report.errors} error(s)`);
  fs.rmSync(out, { recursive: true, force: true });
}

// ---------------------------------------------------------------- 2) cross references
const geos = new Map();
const verAtLeast = (v, min) => {
  const a = String(v).split(".").map(Number);
  for (let i = 0; i < min.length; i++) if ((a[i] ?? 0) !== min[i]) return (a[i] ?? 0) > min[i];
  return true;
};
for (const f of files(path.join(RP, "models"), ".json")) {
  const doc = json(f);
  for (const g of doc["minecraft:geometry"]) {
    geos.set(g.description.identifier, g);
    // bone "binding" (held items) is ignored below geometry format 1.16.0: the item is then drawn
    // unattached at the player's feet/eyes instead of in the hand
    if (g.bones.some((b) => b.binding)) ok(verAtLeast(doc.format_version, [1, 16, 0]), `${g.description.identifier}: binding needs format_version >= 1.16.0 (is ${doc.format_version})`);
  }
}
const anims = new Map();
for (const f of files(path.join(RP, "animations"), ".json")) for (const [k, a] of Object.entries(json(f).animations)) anims.set(k, a);
const particles = new Set(files(path.join(RP, "particles"), ".json").map((f) => json(f).particle_effect.description.identifier));
const rcs = new Set();
for (const f of files(path.join(RP, "render_controllers"), ".json")) for (const k of Object.keys(json(f).render_controllers)) rcs.add(k);
const texExists = (t) => fs.existsSync(path.join(RP, `${t}.png`));
const lang = fs.readFileSync(path.join(RP, "texts", "en_US.lang"), "utf8");
const PLAYER_BONES = new Set(["body", "head", "rightArm", "leftArm", "rightLeg", "leftLeg", "rightItem", "leftItem"]);

// textures: power of two
for (const f of files(path.join(RP, "textures"), ".png")) {
  const { w, h } = pngSize(f);
  ok(pow2(w) && pow2(h), `${path.relative(ADDON, f)} is ${w}x${h} (not power of two)`);
}

// geometry: UVs inside the texture, parents exist
for (const [id, g] of geos) {
  const W = g.description.texture_width;
  const H = g.description.texture_height;
  const names = new Set(g.bones.map((b) => b.name));
  for (const b of g.bones) {
    if (b.parent) ok(names.has(b.parent), `${id}: bone ${b.name} parent ${b.parent} missing`);
    for (const c of b.cubes ?? []) {
      for (const [face, f] of Object.entries(c.uv ?? {})) {
        const [u, v] = f.uv;
        const [su, sv] = f.uv_size;
        ok(u >= 0 && v >= 0 && u + su <= W && v + sv <= H, `${id}: ${b.name}.${face} UV outside ${W}x${H}`);
      }
    }
  }
}

function checkAnimBones(animId, geoId, extraBones = new Set()) {
  const a = anims.get(animId);
  ok(!!a, `animation ${animId} missing`);
  if (!a) return;
  const g = geoId ? geos.get(geoId) : undefined;
  const bones = new Set([...(g ? g.bones.map((b) => b.name) : []), ...extraBones]);
  for (const bone of Object.keys(a.bones ?? {})) ok(bones.has(bone), `${animId}: bone ${bone} not in ${geoId ?? "player"}`);
  const locators = new Set(g ? g.bones.flatMap((b) => Object.keys(b.locators ?? {})) : []);
  for (const fx of Object.values(a.particle_effects ?? {}).flat()) ok(locators.has(fx.locator), `${animId}: locator ${fx.locator} missing`);
}

// attachables
for (const f of files(path.join(RP, "attachables"), ".json")) {
  const d = json(f)["minecraft:attachable"].description;
  ok(fs.existsSync(path.join(BP, "items", `${d.identifier.split(":")[1]}.json`)), `attachable ${d.identifier} has no item`);
  const geoId = d.geometry.default;
  const g = geos.get(geoId);
  ok(!!g, `${d.identifier}: geometry ${geoId} missing`);
  ok(g && g.bones.some((b) => b.binding === "q.item_slot_to_bone_name(c.item_slot)"), `${d.identifier}: root bone not bound to the hand`);
  for (const t of Object.values(d.textures)) ok(texExists(t), `${d.identifier}: texture ${t} missing`);
  for (const p of Object.values(d.particle_effects ?? {})) ok(particles.has(p), `${d.identifier}: particle ${p} missing`);
  for (const a of Object.values(d.animations)) checkAnimBones(a, geoId);
  for (const rc of d.render_controllers) ok(rcs.has(rc), `${d.identifier}: render controller ${rc} missing`);
}

// client entities
for (const f of files(path.join(RP, "entity"), ".json")) {
  const d = json(f)["minecraft:client_entity"].description;
  ok(fs.existsSync(path.join(BP, "entities", `${d.identifier.split(":")[1]}.json`)), `${d.identifier}: no behavior entity`);
  ok(geos.has(d.geometry.default), `${d.identifier}: geometry ${d.geometry.default} missing`);
  for (const t of Object.values(d.textures)) ok(texExists(t), `${d.identifier}: texture ${t} missing`);
  for (const a of Object.values(d.animations ?? {})) checkAnimBones(a, d.geometry.default);
  for (const rc of d.render_controllers) ok(rcs.has(rc), `${d.identifier}: render controller ${rc} missing`);
  ok(lang.includes(`entity.${d.identifier}.name=`), `${d.identifier}: no display name`);
}

// player animations (played from script) only touch vanilla player bones
for (const id of anims.keys()) if (id.startsWith("animation.grizzly_oath.player.")) checkAnimBones(id, undefined, PLAYER_BONES);

// items: icon + name
const atlas = json(path.join(RP, "textures", "item_texture.json")).texture_data;
for (const f of files(path.join(BP, "items"), ".json")) {
  const item = json(f)["minecraft:item"];
  const id = item.description.identifier;
  const icon = item.components["minecraft:icon"];
  const key = typeof icon === "string" ? icon : icon?.textures?.default;
  ok(atlas[key] && texExists(atlas[key].textures), `${id}: icon ${key} missing`);
  ok(lang.includes(`item.${id}.name=`), `${id}: no display name`);
}

// scripts compiled
ok(fs.existsSync(path.join(BP, "scripts", "main.js")), "scripts/main.js missing (run npm run compile)");

console.log(`cross-reference checks: ${checks - errors.length}/${checks} passed`);
for (const e of errors) console.log("  ERROR:", e);
process.exit(errors.length ? 1 : 0);
