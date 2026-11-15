// Render the generated mountain from the concept sheet's angles.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { withViewer } from "./render.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, "out");
const tag = process.argv[2] ?? "p1";
const bin = process.argv[3] ?? "mountain";
await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#6ea6f5", "#eaf3ff"], fog: { color: 0xdde8f5, near: 160, far: 520 } }));
  await page.evaluate(([b]) => window.preview.voxels(`/out/${b}.bin`, `/out/${b}.json`), [bin]);
  await page.evaluate(() => window.preview.clouds(100, 900, 0.8));
  const c = [0, 140, 0];
  await shot(path.join(OUT, `${tag}_hero.png`), { eye: [-95, 175, -150], target: [0, 140, 0], fov: 50 });
  await shot(path.join(OUT, `${tag}_front.png`), { eye: [190, 150, 0], target: c, fov: 45 });
  await shot(path.join(OUT, `${tag}_side.png`), { eye: [0, 150, -200], target: c, fov: 45 });
  await shot(path.join(OUT, `${tag}_back.png`), { eye: [-190, 150, 0], target: c, fov: 45 });
  await shot(path.join(OUT, `${tag}_top.png`), { eye: [0, 330, 1], target: [0, 140, 0], fov: 50 });
  await shot(path.join(OUT, `${tag}_close.png`), { eye: [-40, 175, -75], target: [-10, 160, -20], fov: 60 });
});
console.log("done");
