import path from "node:path";
import { fileURLToPath } from "node:url";
import { withViewer } from "./render.mjs";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, "out");
const tag = process.argv[2] ?? "cut";
const bin = process.argv[3] ?? "mountain";
await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#6ea6f5", "#eaf3ff"] }));
  await page.evaluate(([b]) => window.preview.voxels(`/out/${b}.bin`, `/out/${b}.json`, { axis: 2, max: 1 }), [bin]);
  await shot(path.join(OUT, `${tag}_z.png`), { eye: [10, 150, 95], target: [0, 148, 0], fov: 55 });
  await page.evaluate(() => window.preview.clear());
  await page.evaluate(([b]) => window.preview.voxels(`/out/${b}.bin`, `/out/${b}.json`, { axis: 0, max: -9 }), [bin]);
  await shot(path.join(OUT, `${tag}_x.png`), { eye: [80, 140, 10], target: [-15, 135, 0], fov: 60 });
});
