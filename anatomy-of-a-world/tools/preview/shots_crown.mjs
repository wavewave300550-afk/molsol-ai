// Phase 2 "Unfolded World": disk + petal crown + splayed legs + heart, and the closed dome of petals.
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
const meta = JSON.parse(fs.readFileSync(path.join(OUT, "mountain.json"), "utf8"));
const A = 58, B = 46, DY = 146, HX = 0.5, HZ = 0.5;
const petals = [];
for (let k = 0; k < 12; k++) {
  const ang = ((15 + 30 * k) * Math.PI) / 180;
  const pos = [HX + Math.cos(ang) * A * 0.8, DY + 1.5, HZ + Math.sin(ang) * B * 0.8]; // petal anchor (see petalSite)
  const yaw = (Math.atan2(-(HX - pos[0]), HZ - pos[2]) * 180) / Math.PI;
  petals.push({ pos, yaw });
}
const which = process.argv[2] ?? "open";
await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#5d8ed8", "#e6eefb"], fog: { color: 0xdde8f5, near: 170, far: 560 } }));
  await page.evaluate(([b]) => window.preview.voxels(`/out/${b}.bin`, `/out/${b}.json`), [which === "closed" ? "mountain" : "phase2"]);
  await page.evaluate(() => window.preview.clouds(100, 1000, 0.85));
  for (const p of petals) await page.evaluate(([g, pp, pose]) => window.preview.model(g, "/rp/textures/entity/anatomy/mm_petal.png", { pose, emissiveAlpha: true, yaw: pp.yaw, position: pp.pos }), [geo("mm_petal"), p, which === "closed" ? poses.mm_petal.closed : poses.mm_petal.open]);
  if (which !== "closed") {
    for (const leg of meta.legs) await page.evaluate(([g, l, pose]) => window.preview.model(g, "/rp/textures/entity/anatomy/mm_root_leg.png", { pose, emissiveAlpha: true, yaw: l.yaw, position: [l.pos.x, l.pos.y, l.pos.z] }), [geo("mm_root_leg"), leg, poses.mm_root_leg.splay]);
    await page.evaluate(([g, pose]) => window.preview.model(g, "/rp/textures/entity/anatomy/mm_lithic_heart.png", { pose, emissiveAlpha: true, yaw: 0, position: [0.5, 148.5, 0.5] }), [geo("mm_lithic_heart"), poses.mm_lithic_heart.open]);
  }
  await page.waitForTimeout(800);
  await shot(path.join(OUT, `crown_${which}_hero.png`), { eye: [-95, 196, -120], target: [0, 160, 0], fov: 52 });
  await shot(path.join(OUT, `crown_${which}_player.png`), { eye: [-4, 149.6, -30], target: [0.5, 154, 0.5], fov: 75 });
});
console.log("done");
