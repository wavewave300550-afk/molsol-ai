// Runs each attack / skill once on the strict mock (same as the smoke test) and records what the
// real scripts emit: particles (with Molang variables), sounds, player animations, spawned
// entities and the player's position every tick.  Output: tools/fx_preview/.scenes.json
// Consumed by tools/fx_preview/render.py to draw storyboards.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const ADDON = path.join(ROOT, "addon");
const SCRIPTS = path.join(ADDON, "behavior_packs", "grizzly_oath", "scripts");
process.env.GO_ADDON = ADDON;
const RUN = path.join(HERE, ".run");
fs.rmSync(RUN, { recursive: true, force: true });
fs.mkdirSync(path.join(RUN, "node_modules", "@minecraft", "server"), { recursive: true });
fs.writeFileSync(path.join(RUN, "package.json"), JSON.stringify({ type: "module" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "package.json"), JSON.stringify({ name: "@minecraft/server", type: "module", main: "index.js" }));
fs.writeFileSync(path.join(RUN, "node_modules", "@minecraft", "server", "index.js"), `export * from ${JSON.stringify(pathToFileURL(path.join(HERE, "..", "smoke", "mock-server.mjs")).href)};`);
for (const f of fs.readdirSync(SCRIPTS)) fs.copyFileSync(path.join(SCRIPTS, f), path.join(RUN, f));
const M = await import(pathToFileURL(path.join(RUN, "node_modules", "@minecraft", "server", "index.js")).href);
await import(pathToFileURL(path.join(RUN, "main.js")).href);

const dim = M.__dims.overworld;
const L = M.__log;
const p = new M.Player("Hugh", { x: 0, y: 64, z: 0 }, dim);
p.inventory.setItem(0, new M.ItemStack("grizzly_oath:grizzlys_oath"));
M.world.afterEvents.worldLoad.fire({});
M.__tick(5);

const scenes = [];
function record(name, setup, act, ticks) {
  for (const e of [...dim.entities]) if (!(e instanceof M.Player)) e.remove();
  p.location = { x: 0, y: 64, z: 0 };
  p.view = { x: 0, y: 0, z: 1 };
  p.yaw = 0;
  p.health = 20;
  const mobs = setup();
  M.__tick(400); // every cooldown ready
  const t0 = M.__now();
  const nP = L.particles.length;
  const nA = L.anims.length;
  const nS = L.spawned.length;
  const track = [];
  act();
  for (let i = 0; i <= ticks; i++) {
    track.push({ t: M.__now() - t0, x: p.location.x, y: p.location.y, z: p.location.z });
    M.__tick(1);
  }
  const rel = (o) => ({ ...o, t: o.tick - t0 });
  scenes.push({
    name,
    mobs: mobs.map((m) => ({ x: m.location.x, z: m.location.z })),
    track,
    particles: L.particles.slice(nP).map((x) => rel({ tick: x.tick, id: x.id.replace("grizzly_oath:", ""), loc: x.loc, vars: x.vars })),
    anims: L.anims.slice(nA).map((a) => ({ t: a.tick - t0, name: a.name })),
    spawned: L.spawned.slice(nS).map((s) => ({ t: s.tick - t0, id: s.entity.typeId, loc: s.entity.location, yaw: s.entity.yaw })),
  });
}
const zombie = (x, z) => new M.Entity("minecraft:zombie", { x, y: 64, z }, dim, { families: ["monster", "mob"] });
const use = () => M.world.afterEvents.itemUse.fire({ source: p, itemStack: p.inventory.getItem(0) });
function select(i) {
  p.setDynamicProperty("grizzly_oath:skill", i);
}

record("Frontier Cleave", () => [zombie(0, 2.2)], () => {
  M.world.afterEvents.playerSwingStart.fire({ player: p, heldItemStack: p.inventory.getItem(0), swingSource: "Attack" });
  M.world.afterEvents.entityHitEntity.fire({ damagingEntity: p, hitEntity: [...dim.entities].find((e) => e.typeId === "minecraft:zombie") });
}, 12);
// skill selection is read from the dynamic property when a player's state is first created, so
// switch with sneak + use like a player would
function switchTo(i) {
  for (let k = 0; k < 4 && p.getDynamicProperty("grizzly_oath:skill") !== i; k++) {
    p.isSneaking = true;
    use();
    p.isSneaking = false;
    M.__tick(8);
  }
}
switchTo(0);
record("Grizzly Rend", () => [zombie(-1, 6), zombie(1.5, 9)], use, 30);
switchTo(1);
record("Relentless Pursuit", () => [zombie(0.5, 8.5), zombie(2.5, 7)], use, 24);
switchTo(2);
record("Unbroken Will", () => [], use, 70);
switchTo(3);
record("Oath of the Grizzly", () => [zombie(-2, 5), zombie(3, 6), zombie(0, 9)], use, 70);
void select;

fs.writeFileSync(path.join(HERE, ".scenes.json"), JSON.stringify(scenes));
fs.rmSync(RUN, { recursive: true, force: true });
console.log(scenes.map((s) => `${s.name}: ${s.particles.length} particles, anims ${s.anims.map((a) => a.name.split(".").pop()).join(",")}, spawned ${s.spawned.length}`).join("\n"));
