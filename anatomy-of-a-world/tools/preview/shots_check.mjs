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
const jobs = JSON.parse(process.argv[2]);
await withViewer(async (page, shot) => {
  await page.evaluate(() => window.preview.setup({ width: 900, height: 700, sky: ["#8fb8f0", "#f1f5fb"] }));
  for (const j of jobs) {
    await page.evaluate(() => window.preview.clear());
    await page.evaluate(([g, n, p, y]) => window.preview.model(g, `/rp/textures/entity/anatomy/${n}.png`, { pose: p, emissiveAlpha: true, yaw: y }), [geo(j.model), j.model, poses[j.model]?.[j.pose] ?? {}, j.yaw ?? 0]);
    if (j.markers) for (const m of j.markers) await page.evaluate((mm) => window.preview.marker(mm, 0xff00ff, 0.3), m);
    await page.waitForTimeout(250);
    await shot(path.join(OUT, `chk_${j.name}.png`), j.cam);
  }
});
