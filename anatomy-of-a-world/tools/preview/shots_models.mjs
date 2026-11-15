// Render each Boss 001 model on its own (several poses), and the assembled creature.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { withViewer } from "./render.mjs";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const OUT = path.join(HERE, "out");
const RP = path.join(ROOT, "build", "packs", "RP");
const poses = JSON.parse(fs.readFileSync(path.join(OUT, "poses.json"), "utf8"));
const geo = (n) => JSON.parse(fs.readFileSync(path.join(RP, "models", "entity", `${n}.geo.json`), "utf8"));
const which = process.argv[2] ?? "all";

const SINGLE = [
  ["mm_root_leg", ["rest", "walk_lift", "stomp_top", "splay"], { eye: [34, 6, -10], target: [0, -9, -9], fov: 55 }],
  ["mm_resonance_node", ["rest", "hang"], { eye: [4.2, 3.6, -4.6], target: [0, 1.6, 0], fov: 45 }],
  ["mm_lithic_heart", ["closed", "open"], { eye: [9, 7, -11], target: [0, 3, 0], fov: 50 }],
  ["mm_strata_slab", ["rest"], { eye: [4, 4, -5], target: [0, 1.4, 0], fov: 45 }],
  ["mm_petal", ["closed", "half", "open", "folded"], { eye: [70, 30, 40], target: [0, 18, 0], fov: 55 }],
  ["mm_strata_plate", ["rest", "wall", "ceiling"], { eye: [10, 9, -12], target: [0, 3, 0], fov: 50 }],
  ["mm_rib_plate", ["rest", "wall"], { eye: [8, 7, -10], target: [0, 2, 0], fov: 50 }],
];

await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 960, height: 720, sky: ["#8fb8f0", "#f1f5fb"] }));
  if (which === "all" || which === "single") {
    for (const [name, list, cam] of SINGLE) {
      for (const pose of list) {
        await page.evaluate(() => window.preview.clear());
        await page.evaluate(([g, n, p]) => window.preview.model(g, `/rp/textures/entity/anatomy/${n}.png`, { pose: p, emissiveAlpha: true, yaw: 0 }), [geo(name), name, poses[name]?.[pose] ?? {}]);
        await page.waitForTimeout(300);
        await shot(path.join(OUT, `model_${name}_${pose}.png`), cam);
      }
    }
  }
  if (which === "all" || which === "scene") {
    await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#6ea6f5", "#eaf3ff"], fog: { color: 0xdde8f5, near: 170, far: 560 } }));
    await page.evaluate(() => window.preview.clear());
    await page.evaluate(() => window.preview.voxels(`/out/mountain.bin`, `/out/mountain.json`));
    await page.evaluate(() => window.preview.clouds(100, 1000, 0.85));
    const meta = JSON.parse(fs.readFileSync(path.join(OUT, "mountain.json"), "utf8"));
    for (const leg of meta.legs) {
      await page.evaluate(([g, l, p]) => window.preview.model(g, `/rp/textures/entity/anatomy/mm_root_leg.png`, { pose: p, emissiveAlpha: true, yaw: l.yaw, position: [l.pos.x, l.pos.y, l.pos.z] }), [geo("mm_root_leg"), leg, leg.index % 2 ? poses.mm_root_leg.walk_lift : poses.mm_root_leg.walk_plant]);
    }
    await page.waitForTimeout(800);
    await shot(path.join(OUT, `scene_hero.png`), { eye: [-95, 168, -150], target: [0, 135, 0], fov: 50 });
    await shot(path.join(OUT, `scene_front.png`), { eye: [190, 140, 0], target: [0, 135, 0], fov: 45 });
    await shot(path.join(OUT, `scene_side.png`), { eye: [10, 140, -205], target: [0, 135, 0], fov: 45 });
    await shot(path.join(OUT, `scene_low.png`), { eye: [-60, 104, -95], target: [0, 128, 0], fov: 60 });
  }
});
console.log("done");
