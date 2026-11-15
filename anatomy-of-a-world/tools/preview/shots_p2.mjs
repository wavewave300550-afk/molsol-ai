import path from "node:path";
import { fileURLToPath } from "node:url";
import { withViewer } from "./render.mjs";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, "out");
const tag = process.argv[2] ?? "p2";
await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#5e8fdc", "#e2ecfb"], fog: { color: 0xdde8f5, near: 160, far: 520 } }));
  await page.evaluate(() => window.preview.voxels(`/out/phase2.bin`, `/out/phase2.json`));
  await page.evaluate(() => window.preview.clouds(100, 900, 0.8));
  await page.evaluate(() => window.preview.marker([0.5, 151.5, 0.5], 0xb060ff, 2.5));
  await shot(path.join(OUT, `${tag}_hero.png`), { eye: [-70, 185, -80], target: [0, 146, 0], fov: 55 });
  await shot(path.join(OUT, `${tag}_top.png`), { eye: [0, 260, 1], target: [0, 146, 0], fov: 55 });
  await shot(path.join(OUT, `${tag}_ground.png`), { eye: [-26, 149, -12], target: [0, 150, 0], fov: 70 });
});
