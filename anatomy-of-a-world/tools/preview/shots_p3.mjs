// Phase 3 previews from the simulator's arena snapshots (SIM_SNAPSHOT=1 node tools/sim/run.mjs):
// the Anchorage Root model, The Last Migration (3A) and The Heart Unbound (3B).
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

function poseOf(name, props) {
  if (name === "mm_root_leg") {
    const p = props["anatomy:pose"];
    if (p === 3) return poses.mm_root_leg[props["anatomy:leg_index"] % 2 ? "march_lift" : "march_plant"];
    if (p === 2) return poses.mm_root_leg.splay;
    return poses.mm_root_leg.rest;
  }
  if (name === "mm_petal") return poses.mm_petal[{ 0: "closed", 1: "open", 2: "half", 3: "folded", 4: "raised" }[props["anatomy:petal_state"]] ?? "open"];
  if (name === "mm_lithic_heart") return poses.mm_lithic_heart[props["anatomy:phase"] === 3 ? "unbound" : props["anatomy:open"] ? "open" : "closed"];
  if (name === "mm_anchor_root") return poses.mm_anchor_root.grip;
  return {};
}

async function scene(page, name) {
  const meta = JSON.parse(fs.readFileSync(path.join(OUT, `${name}.json`), "utf8"));
  await page.evaluate(() => window.preview.setup({ width: 1280, height: 800, sky: ["#5e8fdc", "#e2ecfb"], fog: { color: 0xdde8f5, near: 160, far: 520 } }));
  await page.evaluate(() => window.preview.clear());
  await page.evaluate(([b, j]) => window.preview.voxels(b, j), [`/out/${name}.bin`, `/out/${name}.json`]);
  await page.evaluate(() => window.preview.clouds(100, 900, 0.8));
  for (const e of meta.parts) {
    const n = e.typeId.replace("anatomy:", "");
    await page.evaluate(([g, t, p, pos, yaw]) => window.preview.model(g, t, { pose: p, emissiveAlpha: true, yaw, position: pos }), [geo(n), `/rp/textures/entity/anatomy/${n}.png`, poseOf(n, e.props), e.pos, e.yaw]);
  }
  await page.waitForTimeout(800);
  return meta;
}

await withViewer(async (page, shot) => {
  // the Anchorage Root on its own
  await page.evaluate(() => window.preview.setup({ width: 960, height: 720, sky: ["#8fb8f0", "#f1f5fb"] }));
  for (const pose of ["grip", "snap"]) {
    await page.evaluate(() => window.preview.clear());
    await page.evaluate(([g, p]) => window.preview.model(g, `/rp/textures/entity/anatomy/mm_anchor_root.png`, { pose: p, emissiveAlpha: true, yaw: 0 }), [geo("mm_anchor_root"), poses.mm_anchor_root[pose]]);
    await page.waitForTimeout(300);
    await shot(path.join(OUT, `model_mm_anchor_root_${pose}.png`), { eye: [32, 4, -30], target: [0, -9, 5], fov: 55 });
  }
  // Phase 3A: the crown of walls, the marching legs and the four roots
  const a = await scene(page, "p3a");
  const root0 = a.parts.find((e) => e.typeId === "anatomy:mm_anchor_root");
  const heart = a.parts.find((e) => e.typeId === "anatomy:mm_lithic_heart");
  const H = heart.pos;
  await shot(path.join(OUT, "p3a_hero.png"), { eye: [H[0] - 62, 192, H[2] - 74], target: [H[0], 146, H[2]], fov: 55 });
  await shot(path.join(OUT, "p3a_top.png"), { eye: [H[0], 262, H[2] + 1], target: [H[0], 146, H[2]], fov: 55 });
  if (root0) {
    const dx = root0.pos[0] - H[0];
    const dz = root0.pos[2] - H[2];
    const L = Math.hypot(dx, dz);
    const eye = [H[0] + (dx / L) * 9 - (dz / L) * 4, 149.2, H[2] + (dz / L) * 9 + (dx / L) * 4];
    await shot(path.join(OUT, "p3a_root.png"), { eye, target: [root0.pos[0], root0.pos[1] + 1.2, root0.pos[2]], fov: 70 });
  }
  // Phase 3B: nine islands and the hovering heart
  const b = await scene(page, "p3b");
  const hb = b.parts.find((e) => e.typeId === "anatomy:mm_lithic_heart").pos;
  await shot(path.join(OUT, "p3b_hero.png"), { eye: [hb[0] - 56, 178, hb[2] - 66], target: [hb[0], 148, hb[2]], fov: 55 });
  await shot(path.join(OUT, "p3b_top.png"), { eye: [hb[0], 262, hb[2] + 1], target: [hb[0], 146, hb[2]], fov: 55 });
  await shot(path.join(OUT, "p3b_island.png"), { eye: [hb[0] - 21, 149.6, hb[2] - 7], target: [hb[0], hb[1] + 2, hb[2]], fov: 70 });
});
console.log("done");
